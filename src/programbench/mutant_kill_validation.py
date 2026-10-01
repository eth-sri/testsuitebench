# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""Co-validate reference tests and improve mutant focus on a best-effort budget."""

from __future__ import annotations

import argparse
import json
import logging
import re
import shlex
import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from programbench.codex import build_codex_shell_command, run_codex_in_container
from programbench.constants import image_name_from_instance_id
from programbench.eval.test_suite_eval import TestSuiteEvaluationResult
from programbench.eval.test_suite_eval_batch import run_test_suite_eval_batch
from programbench.iteration_polish import (
    DEFAULT_CODEX_COMMAND, DEFAULT_MODEL, DEFAULT_REASONING, DEFAULT_TIMEOUT, write_directory_diff,
)
from programbench.mutant_attribution import load_mutant_cases
from programbench.mutant_candidate_selection import select_mutant_candidates
from programbench.mutation_safeguards import dominant_tests_from_kill_sets
from programbench.mutant_storage import compact_mutant_suite, deduplicate_mutant_files
from programbench.mutants import load_mutant_suite
from programbench.skipped_tests import add_skipped_tests, load_skipped_tests, skipped_tests_path
from programbench.test_generation import _write_codex_trajectory

log = logging.getLogger(__name__)
Evaluator = Callable[[int], TestSuiteEvaluationResult]
RepairRunner = Callable[[str, Path], dict[str, Any]]
DEFAULT_MAX_INFRASTRUCTURE_RETRIES = 2


SELECTION_FILENAME = "candidate_selection.json"


def _test_function_name(name: str) -> str:
    return re.split(r"\[| \(", name, maxsplit=1)[0].partition("@")[0]

def _ground_truth_test_statuses(result: TestSuiteEvaluationResult) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for binary in result.binary_results:
        if binary.role != "ground_truth":
            continue
        for test in binary.test_results:
            name = _test_function_name(test.name)
            if name not in statuses or test.status != "passed":
                statuses[name] = test.status
    return statuses


def _ground_truth_infrastructure_failures(result: TestSuiteEvaluationResult) -> list[str]:
    """Return ground-truth failures that describe the test runner, not a test.

    Pytest can emit ``pytest.internal`` when an xdist/execnet worker connection
    dies without producing the usual ``worker 'gwN' crashed`` marker. That
    pseudo-test cannot be added to the function-level skip list and should be
    retried as infrastructure instead.
    """
    failures: list[str] = []
    if result.error_code is not None:
        failures.append(f"evaluation:{result.error_code}")
    for binary in result.binary_results:
        if binary.role != "ground_truth":
            continue
        if binary.error_code is not None:
            failures.append(f"{binary.binary_id}:{binary.error_code}")
        for test in binary.test_results:
            name = _test_function_name(test.name)
            if test.status == "system_error" or name.rsplit("/", 1)[-1] == "pytest.internal":
                failures.append(name)
    return sorted(set(failures))


def _mutant_kill_sets(result: TestSuiteEvaluationResult) -> dict[str, list[str]]:
    ground_truth = _ground_truth_test_statuses(result)
    passing_ground_truth = {name for name, status in ground_truth.items() if status == "passed"}
    kill_sets: dict[str, list[str]] = {}
    for binary in result.binary_results:
        if binary.role != "candidate" or binary.error_code is not None:
            continue
        statuses: dict[str, str] = {}
        for test in binary.test_results:
            name = _test_function_name(test.name)
            if name not in statuses or test.status != "passed":
                statuses[name] = test.status
        kill_sets[binary.binary_id] = sorted(
            name
            for name in passing_ground_truth
            if statuses.get(name) is not None and statuses[name] != "passed"
        )
    return kill_sets


def _log_iteration_summary(
    *,
    task: str,
    record: dict[str, Any],
    total_mutants: int,
    previous: dict[str, Any] | None,
) -> None:
    if previous is None:
        change = "baseline"
    else:
        change = (
            "change: exact {exact:+d}, target-killed {target:+d}, "
            "collateral {collateral:+d}, remaining {remaining:+d}"
        ).format(
            exact=record["killed"] - previous["killed"],
            target=record["target_killed"] - previous["target_killed"],
            collateral=record["collateral_kills"] - previous["collateral_kills"],
            remaining=len(record["requires_repair"]) - len(previous["requires_repair"]),
        )
    log.info(
        "Mutant validation iteration %d for %s: exact singletons %d/%d, "
        "target-killed %d/%d, collateral kills %d, remaining %d (%s)",
        record["attempt"], task,
        record["killed"], total_mutants,
        record["target_killed"], total_mutants,
        record["collateral_kills"], len(record["requires_repair"]), change,
    )


def mutant_kill_repair_prompt(*, task: str, attempt: int, affected_ids: list[str]) -> str:
    ids = ", ".join(affected_ids)
    return f"""\
You are repairing mutants for `{task}` after fixed-reference-suite mutation evaluation (attempt {attempt}).

## Workspace

- `specification/`: the current task specification.
- `reference-tests/`: the immutable extracted test sources.
- `skipped_tests.json`: functions excluded from the fixed reference suite; do not use them as repair evidence.
- `repair_required.json`: the repair evidence.
- `mutants/`: only the affected repositories: {ids}.

## Task

Try your best to make every listed mutant fail its assigned `target_test` while minimizing failures of other active tests and retaining its initial scope. An exact singleton kill set is desirable, but it is not required.

## Rules

- Modify only repositories already present under `mutants/`.
- Keep every mutant ID and its original `target_spec` and `target_test` unchanged. Do not add, remove, rename, or merge mutants.
- Preserve the behavioral topic of each original mutation. Strengthen or simplify how that same behavior is violated; do not switch to a different spec behavior merely because another test is easy to fail.
- For every edited mutant, the assigned `target_test` must fail. Aim for every other active reference-test function to pass.
- Prefer the smallest source-level change that creates a focused, deterministic violation in the original scope.
- Inspect only relevant reference tests. Never modify tests, the specification, or `repair_required.json`; host-side copyback excludes them.
- Rebuild each edited repository with its existing `build.sh` and leave a self-contained readable `executable`.
- Do not create wrapper/proxy executables, delegate to a reference executable, detect the test environment, key behavior on test names, or introduce unrelated crashes/timeouts.
- If the original change is invalid, replace it with a valid focused violation of the same `target_spec`.
- Some immutable tests may exercise indistinguishable behavior. If further focus would require detecting the test harness or violating these rules, leave that mutant completely unchanged and explain why in `repair_outcome.json`.

## Output

- Leave each repaired mutant in its existing repository under `mutants/`.
- Map each mutant ID to the strengthened violation in its retained scope.
- Write `repair_outcome.json` with two objects: `changed_mutants`, mapping each edited mutant ID to a concise summary, and `kept_as_is`, mapping each unedited mutant ID to the reason further focus is impractical. Every listed mutant ID must occur in exactly one object. This file is authoritative.
"""


def _suite_scope(mutants_root: Path, task: str) -> dict[str, dict[str, str]]:
    loaded = load_mutant_suite(mutants_root, task)
    if loaded is None:
        raise RuntimeError(f"No mutant suite found for {task}: {mutants_root / task}")
    _, suite = loaded
    if not suite.mutants:
        raise RuntimeError(f"Mutant suite is empty for {task}: {mutants_root / task}")
    scope = {
        m.id: {
            "target_spec": m.target_spec,
            "assignment_id": m.assignment_id or m.id,
            "target_test": m.target_test,
            "mutation": m.mutation,
            "payload": m.payload,
        }
        for m in suite.mutants
    }
    missing_targets = sorted(mutant_id for mutant_id, item in scope.items() if not item["target_test"])
    if missing_targets:
        raise RuntimeError(f"Mutants are missing planned target_test values: {missing_targets}")
    plan_path = mutants_root / task / "mutant_plan.json"
    if not plan_path.is_file():
        raise RuntimeError(f"Mutant plan is missing for {task}: {plan_path}")
    plan = json.loads(plan_path.read_text())
    planned = {
        str(item["mutant_id"]): {
            "target_spec": str(item["target_spec"]),
            "target_test": str(item["target_test"]),
        }
        for item in plan.get("assignments", [])
    }
    planned_tests = [item["target_test"] for item in planned.values()]
    if len(set(planned_tests)) != len(planned_tests):
        raise RuntimeError("Mutant plan assigns the same target_test to more than one mutant")
    for mutant_id, item in scope.items():
        assignment_id = str(item["assignment_id"])
        expected = planned.get(assignment_id)
        actual = {"target_spec": item["target_spec"], "target_test": item["target_test"]}
        if expected != actual:
            raise RuntimeError(
                f"Mutant {mutant_id} does not match planned assignment {assignment_id}"
            )
    return scope


def _default_evaluator(
    *, task: str, attempt: int, tests_root: Path, mutants_root: Path, work_dir: Path,
    workers: int, branch_workers: int, ground_truth_dir: Path | None = None,
    skipped_tests: Path | None = None, cpu_budget: int = 0,
    mutant_ids: set[str] | None = None,
) -> TestSuiteEvaluationResult:
    output_root = work_dir / "evaluation" / f"attempt_{attempt}"
    shutil.rmtree(output_root, ignore_errors=True)
    run_test_suite_eval_batch(
        sources=[tests_root], output=output_root, tests_dir=tests_root, mutants_dir=mutants_root,
        ground_truth_dir=ground_truth_dir or "",
        filter_spec=f"^{re.escape(task)}$", workers=workers, branch_workers=branch_workers, cpu_budget=cpu_budget, force=True, detailed_logs=True,
        mutant_ids=mutant_ids,
        skipped_tests=skipped_tests or "",
        warn_dominant_mutant_kills=False,
        evaluation_cache_dir=work_dir.parent / ".binary-evaluation-cache" / task,
    )
    eval_json = output_root / tests_root.name / task / f"{task}.test_eval.json"
    if not eval_json.is_file():
        raise RuntimeError(f"Mutation evaluation did not produce {eval_json}")
    return TestSuiteEvaluationResult.model_validate_json(eval_json.read_text())


def _reference_ok(result: TestSuiteEvaluationResult, *, prune_failing_tests: bool = False) -> bool:
    """Whether the reference suite is usable as evidence.

    Pruning requires a 100% passing suite. Otherwise the suite is fixed, so
    tests failing on ground truth are tolerated (and never count as kills);
    only evaluation or infrastructure failures make it unusable.
    """
    if prune_failing_tests:
        return result.ground_truth_passed and result.error_code is None and result.validity_rate == 1.0
    return (
        result.error_code is None
        and not _ground_truth_infrastructure_failures(result)
        and bool(_ground_truth_test_statuses(result))
    )


def _merge_incremental_evaluation(
    cached: TestSuiteEvaluationResult,
    fresh: TestSuiteEvaluationResult,
    *,
    reevaluated_ids: set[str],
) -> TestSuiteEvaluationResult:
    """Merge fresh mutant results into the last validated full-suite result.

    Ground-truth results and top-level status always come from the fresh run.
    Cached entries for requested IDs are removed even if the fresh result is
    missing, allowing the normal missing-mutant validation to catch the error.
    """
    fresh_ground_truth = [
        binary for binary in fresh.binary_results if binary.role == "ground_truth"
    ]
    fresh_candidates = {
        binary.binary_id: binary
        for binary in fresh.binary_results
        if binary.role == "candidate"
    }
    merged_candidates = {
        binary.binary_id: binary
        for binary in cached.binary_results
        if binary.role == "candidate" and binary.binary_id not in reevaluated_ids
    }
    merged_candidates.update(fresh_candidates)

    cached_order = [
        binary.binary_id
        for binary in cached.binary_results
        if binary.role == "candidate"
    ]
    fresh_order = [
        binary.binary_id
        for binary in fresh.binary_results
        if binary.role == "candidate"
    ]
    candidate_order = list(dict.fromkeys(cached_order + fresh_order))
    return fresh.model_copy(update={
        "binary_results": fresh_ground_truth + [
            merged_candidates[mutant_id]
            for mutant_id in candidate_order
            if mutant_id in merged_candidates
        ],
    })


def _default_repair_runner(
    prompt: str,
    workspace: Path,
    *,
    affected_ids: list[str],
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    image: str,
    keep_build_dir: bool = False,
) -> dict[str, Any]:
    agent_command = build_codex_shell_command(
        codex_command, prompt=prompt, model=model.removeprefix("codex/"), reasoning_effort=reasoning_effort,
        diagnostic_action="repair surviving mutants within their original scope",
    )
    build_changed = _REPAIR_BUILD_SCRIPT
    command = f"({agent_command}) && python3 -c {shlex.quote(build_changed)} {int(keep_build_dir)} " + " ".join(
        shlex.quote(mutant_id) for mutant_id in affected_ids
    )
    result = run_codex_in_container(
        command, cwd=workspace, timeout=timeout,
        image=image,
        copy_back_files=["repair_outcome.json"],
        copy_back_dirs=[workspace / "mutants" / mutant_id for mutant_id in affected_ids],
    )
    if int(result.get("returncode", 1)) == 0:
        outcome = json.loads((workspace / "repair_outcome.json").read_text())
        result["changed_mutants"] = outcome["changed_mutants"]
        result["changed_ids"] = sorted(outcome["changed_mutants"])
        result["kept_as_is"] = outcome["kept_as_is"]
    return result


def _repair_codex_events(result: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in str(result.get("stdout", "")).splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


# Rebuild script for repaired mutants, run inside the repair container. argv[1] is
# 1 when the ground-truth tree itself has a build/ directory (lz4's Makefile
# includes build/make/*.make, bat's Cargo build script is build/main.rs), so it is
# source and must survive; otherwise it is a stale out-of-tree build to discard.
_REPAIR_BUILD_SCRIPT = r'''
import json
import pathlib
import shutil
import subprocess
import sys

keep_build_dir = sys.argv[1] == "1"
expected = set(sys.argv[2:])
outcome_path = pathlib.Path("/workspace/repair_outcome.json")
if not outcome_path.is_file():
    raise SystemExit("repair agent did not write repair_outcome.json")
outcome = json.loads(outcome_path.read_text())
changed = outcome.get("changed_mutants")
kept = outcome.get("kept_as_is")
if not isinstance(changed, dict) or not isinstance(kept, dict):
    raise SystemExit("repair_outcome.json must contain changed_mutants and kept_as_is objects")
changed_ids = set(changed)
kept_ids = set(kept)
if changed_ids & kept_ids or changed_ids | kept_ids != expected:
    raise SystemExit("repair_outcome.json must classify every affected mutant exactly once")
for mutant_id in sorted(changed_ids):
    repo = pathlib.Path("/workspace/mutants") / mutant_id
    if not keep_build_dir:
        shutil.rmtree(repo / "build", ignore_errors=True)
    # Same cleanup the canonical mutant build does. A stale ./executable is the
    # inode cargo re-creates as target/release/<bin>, so build.sh scripts ending
    # in `mv target/release/<bin> executable` fail with "are the same file".
    (repo / "executable").unlink(missing_ok=True)
    (repo / ".programbench-build-cache").unlink(missing_ok=True)
    subprocess.run(["bash", "build.sh"], cwd=repo, check=True)
    executable = repo / "executable"
    if not executable.is_file():
        raise SystemExit(f"repaired mutant has no executable: {mutant_id}")
    executable.chmod(executable.stat().st_mode | 0o044)
'''


def _compact_repair_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result[key]
        for key in (
            "returncode", "exception_info", "image", "usage", "usage_calls",
            "changed_ids", "kept_as_is",
        )
        if key in result
    }


def _repair_evaluation_payload(case: Any) -> dict[str, Any]:
    payload = case.model_dump(mode="json")
    payload.pop("passed_ground_truth_tests", None)
    return payload


def _mutant_sort_key(mutant_id: str) -> tuple[int, int | str]:
    match = re.fullmatch(r"repo_(\d+)", mutant_id)
    return (0, int(match.group(1))) if match else (1, mutant_id)


def _write_spec_test_mutant_links(
    *,
    path: Path,
    task: str,
    scope: dict[str, dict[str, str]],
    attempts: list[dict[str, Any]],
    best_effort_reasons: dict[str, str],
    repair_summaries: dict[str, str],
    verified: bool,
) -> None:
    final = attempts[-1] if attempts else {}
    exact_ids = set(final.get("killed_ids") or [])
    target_killed_ids = set(final.get("target_killed_ids") or [])
    kill_sets = final.get("kill_sets") or {}
    connections = []
    for mutant_id in sorted(scope, key=_mutant_sort_key):
        item = scope[mutant_id]
        observed = list(kill_sets.get(mutant_id) or [])
        target_test = item["target_test"]
        if mutant_id in exact_ids:
            status = "exact_singleton"
        elif mutant_id in best_effort_reasons:
            status = "best_effort_kept_as_is"
        else:
            status = "unresolved"
        connections.append({
            "mutant_id": mutant_id,
            "target_spec": item["target_spec"],
            "target_test": target_test,
            "initial_mutation": item["mutation"],
            "final_mutation_summary": repair_summaries.get(mutant_id, item["mutation"]),
            "status": status,
            "target_killed": mutant_id in target_killed_ids,
            "exact_singleton": mutant_id in exact_ids,
            "observed_kill_count": len(observed),
            "collateral_kill_count": len(set(observed) - {target_test}),
            "best_effort_reason": best_effort_reasons.get(mutant_id),
        })
    path.write_text(json.dumps({
        "task": task,
        "validation_mode": "best_effort_target_test_singleton",
        "verified": verified,
        "summary": {
            "mutants": len(scope),
            "target_killed": len(target_killed_ids),
            "exact_singletons": len(exact_ids),
            "best_effort_kept_as_is": len(best_effort_reasons),
        },
        "connections": connections,
    }, indent=2) + "\n")



def _repair_reference_suite(
    result: TestSuiteEvaluationResult, *, task: str, skipped_tests: Path | None,
    evaluate: Callable[[], TestSuiteEvaluationResult], updates: list[dict[str, Any]],
    prune_failing_tests: bool = False,
) -> TestSuiteEvaluationResult:
    """Skip ground-truth-failing tests until the reference suite passes fully.

    Without ``prune_failing_tests`` the suite is left as is; only
    infrastructure failures are raised.
    """
    while not _reference_ok(result, prune_failing_tests=prune_failing_tests):
        infrastructure_failures = _ground_truth_infrastructure_failures(result)
        if infrastructure_failures:
            raise RuntimeError(
                "Candidate selection ground-truth evaluation had infrastructure failure(s): "
                + ", ".join(infrastructure_failures)
            )
        statuses = _ground_truth_test_statuses(result)
        non_passing_tests = sorted(
            name for name, status in statuses.items() if status != "passed"
        )
        if result.error_code is not None or not statuses or not non_passing_tests:
            raise RuntimeError(
                "Candidate selection requires a 100% passing ground-truth reference suite, "
                "but the failures cannot be represented as test functions"
            )
        if skipped_tests is None:
            raise RuntimeError(
                "Candidate selection requires a skipped-test list to record "
                "ground-truth-failing test functions"
            )
        added = add_skipped_tests(skipped_tests, task=task, names=set(non_passing_tests))
        if not added:
            raise RuntimeError(
                "Candidate selection ground-truth tests remain below 100% after "
                "applying the skipped-test list"
            )
        updates.append({
            "reason": "our_gt_gold_fail",
            "phase": "candidate_selection",
            "validity_rate_before": result.validity_rate,
            "tests": added,
        })
        log.warning(
            "Added candidate-selection ground-truth-failing test function(s) to "
            "the skip list for %s and continuing after reevaluation: %s",
            task, ", ".join(added),
        )
        result = evaluate()
    return result


def _decide_candidate_selection(
    *, task: str, tests_root: Path, mutants_root: Path, work_dir: Path,
    skipped_tests: Path | None, workers: int, branch_workers: int, cpu_budget: int,
    raw_candidates: list[dict[str, Any]], plan: dict[str, Any],
    ground_truth_dir: Path | None, evaluator: Evaluator | None,
    prune_failing_tests: bool = False,
) -> dict[str, Any]:
    """Evaluate every generated candidate and pick the portfolio to keep."""

    def evaluate_candidates() -> TestSuiteEvaluationResult:
        if evaluator is not None:
            return evaluator(-1)
        options = dict(
            task=task, attempt=-1, tests_root=tests_root, mutants_root=mutants_root,
            work_dir=work_dir, workers=workers, branch_workers=branch_workers,
            ground_truth_dir=ground_truth_dir, skipped_tests=skipped_tests, cpu_budget=cpu_budget,
        )
        # Fix invalid reference suites before scheduling thousands of mutants.
        # The full pass reuses these reference checkpoints once preflight passes.
        reference = _default_evaluator(**options, mutant_ids=set())
        return (
            reference if not _reference_ok(reference, prune_failing_tests=prune_failing_tests)
            else _default_evaluator(**options)
        )

    ground_truth_skip_updates: list[dict[str, Any]] = []
    result = _repair_reference_suite(
        evaluate_candidates(), task=task, skipped_tests=skipped_tests,
        evaluate=evaluate_candidates, updates=ground_truth_skip_updates,
        prune_failing_tests=prune_failing_tests,
    )
    while prune_failing_tests:
        dominant = dominant_tests_from_kill_sets(
            _mutant_kill_sets(result),
            mutant_ids={str(item["id"]) for item in raw_candidates},
        )
        already_skipped = load_skipped_tests(skipped_tests, task=task) if skipped_tests else set()
        dominant = [item for item in dominant if item["test"] not in already_skipped]
        if not dominant:
            break
        if skipped_tests is None:
            raise RuntimeError(
                "Candidate selection requires a skipped-test list to exclude "
                "test functions that kill more than 50% of mutants"
            )
        added = add_skipped_tests(
            skipped_tests,
            task=task,
            names={item["test"] for item in dominant},
            reason="our_gt_broad_mutant_kill",
        )
        update = {
            "reason": "our_gt_broad_mutant_kill",
            "phase": "candidate_selection",
            "threshold": 0.5,
            "tests": added,
            "test_kill_rates": dominant,
        }
        ground_truth_skip_updates.append(update)
        log.warning(
            "Added test function(s) killing more than 50%% of candidate mutants "
            "to the skip list for %s: %s",
            task, ", ".join(added),
        )
        result = _repair_reference_suite(
            evaluate_candidates(), task=task, skipped_tests=skipped_tests,
            evaluate=evaluate_candidates, updates=ground_truth_skip_updates,
            prune_failing_tests=prune_failing_tests,
        )
    evaluated_ids = {binary.binary_id for binary in result.candidate_results}
    invalid_candidate_ids = {
        binary.binary_id for binary in result.candidate_results if binary.error_code is not None
    } | {str(item["id"]) for item in raw_candidates} - evaluated_ids
    selection = select_mutant_candidates(
        plan=plan, candidates=raw_candidates, kill_sets=_mutant_kill_sets(result),
        invalid_candidate_ids=invalid_candidate_ids,
    )
    selection["ground_truth_skip_updates"] = ground_truth_skip_updates
    selection["candidate_evaluation"] = str(work_dir / "evaluation" / "attempt_-1")
    return selection


def _apply_candidate_selection(
    *, task: str, task_mutants: Path, manifest_path: Path,
    selection: dict[str, Any], raw_candidates: list[dict[str, Any]], plan: dict[str, Any],
) -> None:
    """Prune the store down to the selected portfolio and renumber it.

    Every step is skipped when its result is already on disk, so a run
    interrupted part-way through the renames finishes the same transition
    instead of re-deciding it against a store it has already pruned.
    """

    raw_by_id = {str(item["id"]): item for item in raw_candidates}
    for final_id, candidate_id in selection["selected"].items():
        staged = task_mutants / f".{final_id}.selected"
        if staged.is_dir():
            continue
        source = task_mutants / candidate_id
        if not source.is_dir():
            raise FileNotFoundError(f"Selected candidate repository is missing: {source}")
        staged.unlink(missing_ok=True)
        source.rename(staged)
    for candidate in raw_candidates:
        candidate_dir = task_mutants / str(candidate["id"])
        if candidate_dir.is_dir():
            shutil.rmtree(candidate_dir)
    for final_id in selection["selected"]:
        staged = task_mutants / f".{final_id}.selected"
        if staged.is_dir():
            shutil.rmtree(task_mutants / final_id, ignore_errors=True)
            staged.rename(task_mutants / final_id)

    assignments = {str(item["mutant_id"]): item for item in plan["assignments"]}
    final_mutants = []
    for final_id, candidate_id in selection["selected"].items():
        winner = dict(raw_by_id[candidate_id])
        assignment_id = str(winner["assignment_id"])
        winner.update(
            id=final_id, assignment_id=assignment_id,
            target_spec=assignments[assignment_id]["target_spec"],
            target_test=assignments[assignment_id]["target_test"],
            payload=f"{final_id}/executable",
        )
        final_mutants.append(winner)
    final_mutants.sort(key=lambda item: _mutant_sort_key(str(item["id"])))
    manifest_path.write_text(json.dumps({"instance_id": task, "mutants": final_mutants}, indent=2) + "\n")
    compact_mutant_suite(task_mutants)


def _select_generated_candidates(
    *, task: str, tests_root: Path, mutants_root: Path, work_dir: Path,
    skipped_tests: Path | None, workers: int, branch_workers: int, cpu_budget: int,
    ground_truth_dir: Path | None = None, evaluator: Evaluator | None = None,
    prune_failing_tests: bool = False,
) -> dict[str, Any] | None:
    task_mutants = mutants_root / task
    manifest_path = task_mutants / "mutants.json"
    manifest = json.loads(manifest_path.read_text())
    raw_candidates = list(manifest.get("mutants", []))
    plan = json.loads((task_mutants / "mutant_plan.json").read_text())
    is_portfolio = "final_mutants_per_spec" in plan
    if not is_portfolio and not any(
        "__candidate_" in str(item.get("id", "")) for item in raw_candidates
    ):
        return None

    # Selection deletes the candidates it rejects, so it can never be re-decided
    # against the store it already pruned. The decision is therefore recorded
    # beside the store it describes -- not in work_dir, which every rerun wipes
    # with --force -- before any repository is touched.
    decision_path = task_mutants / SELECTION_FILENAME
    decision = json.loads(decision_path.read_text()) if decision_path.is_file() else None
    if decision is not None and {str(item["id"]) for item in raw_candidates} == set(decision["selected"]):
        log.info("%s: reusing the candidate selection already applied to the store", task)
        decision["report"] = str(decision_path)
        return decision

    if decision is None:
        decision = _decide_candidate_selection(
            task=task, tests_root=tests_root, mutants_root=mutants_root, work_dir=work_dir,
            skipped_tests=skipped_tests, workers=workers, branch_workers=branch_workers,
            cpu_budget=cpu_budget, raw_candidates=raw_candidates, plan=plan,
            ground_truth_dir=ground_truth_dir, evaluator=evaluator,
            prune_failing_tests=prune_failing_tests,
        )
        decision_path.write_text(json.dumps(decision, indent=2) + "\n")
    else:
        log.info("%s: re-applying a recorded candidate selection left half-applied", task)

    _apply_candidate_selection(
        task=task, task_mutants=task_mutants, manifest_path=manifest_path,
        selection=decision, raw_candidates=raw_candidates, plan=plan,
    )
    selection_path = work_dir / "candidate_selection.json"
    selection_path.write_text(json.dumps(decision, indent=2) + "\n")
    decision["report"] = str(selection_path)
    return decision



def ensure_mutants_killed(
    *, task: str, tests_root: Path, mutants_root: Path, spec_root: Path, work_dir: Path,
    model: str = DEFAULT_MODEL, reasoning_effort: str = DEFAULT_REASONING,
    retry_model: str | None = None, retry_reasoning_effort: str | None = None,
    codex_command: str = DEFAULT_CODEX_COMMAND, timeout: int = DEFAULT_TIMEOUT,
    max_repair_attempts: int = 3, max_infrastructure_retries: int = DEFAULT_MAX_INFRASTRUCTURE_RETRIES,
    workers: int = 1, branch_workers: int = 2, cpu_budget: int = 0, force: bool = False,
    skipped_tests: Path | None = None,
    ground_truth_dir: Path | None = None,
    ground_truth_implementation_dir: Path | None = None,
    repair_image: str = "",
    prune_failing_tests: bool = False,
    evaluator: Evaluator | None = None, repair_runner: RepairRunner | None = None,
) -> dict[str, Any]:
    """Record ground-truth failures in the skip list and repair mutants to 100%."""
    if max_repair_attempts < 0:
        raise ValueError("max_repair_attempts must be non-negative")
    if max_infrastructure_retries < 0:
        raise ValueError("max_infrastructure_retries must be non-negative")
    if workers < 1 or branch_workers < 1:
        raise ValueError("workers and branch_workers must be positive")
    task_tests, task_mutants, task_spec = tests_root / task, mutants_root / task, spec_root / task
    keep_build_dir = ground_truth_implementation_dir is not None and (ground_truth_implementation_dir / task / "build").is_dir()
    selected_repair_image = repair_image or f"{image_name_from_instance_id(task)}:task_cleanroom_codex"
    for label, path in (("reference tests", task_tests), ("mutants", task_mutants), ("specification", task_spec)):
        if not path.is_dir():
            raise FileNotFoundError(f"{label} directory does not exist for {task}: {path}")
    if ground_truth_dir is not None:
        ground_truth_executable = ground_truth_dir / task / "executable"
        if not ground_truth_executable.is_file():
            raise FileNotFoundError(
                f"ground-truth executable does not exist for {task}: {ground_truth_executable}"
            )
    if work_dir.exists() and force:
        shutil.rmtree(work_dir)
    elif work_dir.exists() and any(work_dir.iterdir()):
        raise FileExistsError(f"Mutant validation work directory exists: {work_dir} (use --force)")
    work_dir.mkdir(parents=True, exist_ok=True)

    candidate_selection = _select_generated_candidates(
        task=task, tests_root=tests_root, mutants_root=mutants_root, work_dir=work_dir,
        skipped_tests=skipped_tests, workers=workers, branch_workers=branch_workers,
        cpu_budget=cpu_budget, ground_truth_dir=ground_truth_dir,
        evaluator=evaluator, prune_failing_tests=prune_failing_tests,
    )
    initial_scope = _suite_scope(mutants_root, task)
    expected_ids = set(initial_scope)
    attempts: list[dict[str, Any]] = []
    added_skipped_tests: list[dict[str, Any]] = []
    best_effort_ids: set[str] = set()
    best_effort_reasons: dict[str, str] = {}
    excluded_target_tests: set[str] = set()

    def exclude_target_tests(tests: set[str], reason: str) -> None:
        """A skipped test never runs, so mutants targeting it can never be killed.

        They stay in the suite as best-effort instead of being reported as missing
        from the reference evaluation.
        """
        excluded_target_tests.update(tests)
        for mutant_id, item in initial_scope.items():
            if item["target_test"] in tests:
                best_effort_ids.add(mutant_id)
                best_effort_reasons.setdefault(mutant_id, reason)

    exclude_target_tests(
        load_skipped_tests(skipped_tests, task=task), "target test is on the skip list"
    )
    exclude_target_tests(
        {
            test
            for update in (candidate_selection or {}).get("ground_truth_skip_updates", [])
            if update.get("reason") == "our_gt_broad_mutant_kill"
            for test in update.get("tests", [])
        },
        "target test excluded for killing more than 50% of mutants",
    )
    repair_summaries: dict[str, str] = {}
    report_path = work_dir / "mutant_kill_validation.json"
    diff_path = work_dir / "mutants.diff.patch"
    links_path = work_dir / "spec_test_mutant_links.json"
    validated_result: TestSuiteEvaluationResult | None = None
    validated_eval_path: Path | None = None
    pending_changed_ids: set[str] | None = None

    with tempfile.TemporaryDirectory(prefix="programbench-mutants-before-kill-validation-") as before_name:
        mutants_before = Path(before_name) / task
        shutil.copytree(task_mutants, mutants_before, symlinks=True)

        def persist(*, verified: bool, error: str | None = None) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "task": task, "tests": str(task_tests), "mutants": str(task_mutants), "specification": str(task_spec),
                "validation_mode": "best_effort_target_test_singleton",
                "candidate_selection": candidate_selection,
                "initial_scope": initial_scope, "final_scope": _suite_scope(mutants_root, task),
                "max_repair_attempts": max_repair_attempts, "attempts": attempts,
                "agent_routes": {
                    "initial": {"model": model, "reasoning_effort": reasoning_effort, "image": selected_repair_image},
                    "retry": {
                        "model": retry_model or model,
                        "reasoning_effort": retry_reasoning_effort or reasoning_effort,
                        "from_repair_attempt": 2,
                        "image": selected_repair_image,
                    },
                },
                "skipped_tests": str(skipped_tests) if skipped_tests is not None else None,
                "added_skipped_tests": added_skipped_tests,
                "validity_rate": attempts[-1]["ground_truth_validity_rate"] if attempts else 0.0,
                "mutation_score": attempts[-1]["satisfied"] / len(expected_ids) if attempts else 0.0,
                "target_mutation_score": attempts[-1]["target_killed"] / len(expected_ids) if attempts else 0.0,
                "exact_singleton_count": attempts[-1]["killed"] if attempts else 0,
                "exact_singleton_score": attempts[-1]["killed"] / len(expected_ids) if attempts else 0.0,
                "best_effort_kept_as_is": sorted(best_effort_ids),
                "best_effort_reasons": best_effort_reasons,
                "verified": verified, "mutant_diff": str(diff_path),
                "spec_test_mutant_links": str(links_path),
            }
            if error is not None:
                payload["error"] = error
            write_directory_diff(before=mutants_before, after=task_mutants, output=diff_path)
            _write_spec_test_mutant_links(
                path=links_path,
                task=task,
                scope=initial_scope,
                attempts=attempts,
                best_effort_reasons=best_effort_reasons,
                repair_summaries=repair_summaries,
                verified=verified,
            )
            report_path.write_text(json.dumps(payload, indent=2))
            return {**payload, "report": str(report_path)}

        for attempt in range(max_repair_attempts + 1):
            evaluation_retry = 0
            infrastructure_retries = 0
            while True:
                evaluation_reused = (
                    pending_changed_ids == set()
                    and validated_result is not None
                    and validated_eval_path is not None
                )
                reevaluated_ids = (
                    set(expected_ids) if pending_changed_ids is None
                    else set(pending_changed_ids)
                )
                if evaluation_reused:
                    result = validated_result
                    eval_path = validated_eval_path
                    log.info(
                        "Reusing mutant evaluation for %s attempt %d because the "
                        "previous repair changed no mutants",
                        task, attempt,
                    )
                else:
                    options = dict(
                        task=task, attempt=attempt, tests_root=tests_root, mutants_root=mutants_root,
                        work_dir=work_dir, workers=workers, branch_workers=branch_workers,
                        ground_truth_dir=ground_truth_dir, skipped_tests=skipped_tests, cpu_budget=cpu_budget,
                    )
                    if evaluator is not None:
                        fresh_result = evaluator(attempt)
                    else:
                        # A failing reference suite invalidates every mutant result, so
                        # settle it before scheduling the sweep; the full pass reuses the
                        # reference checkpoints this preflight just wrote.
                        fresh_result = _default_evaluator(**options, mutant_ids=set())
                        if _reference_ok(fresh_result, prune_failing_tests=prune_failing_tests):
                            fresh_result = _default_evaluator(
                                **options,
                                mutant_ids=None if pending_changed_ids is None else reevaluated_ids,
                            )
                    result = (
                        _merge_incremental_evaluation(
                            validated_result, fresh_result, reevaluated_ids=reevaluated_ids,
                        )
                        if pending_changed_ids is not None and validated_result is not None
                        and _reference_ok(fresh_result, prune_failing_tests=prune_failing_tests)
                        else fresh_result
                    )
                    retry_suffix = f".retry_{evaluation_retry}" if evaluation_retry else ""
                    eval_path = work_dir / f"ground_truth_mutants.attempt_{attempt}{retry_suffix}.test_eval.json"
                    eval_path.write_text(result.model_dump_json(indent=2))
                cases = load_mutant_cases(eval_path, mutants_dir=mutants_root, task=task)
                by_id = {case.mutant_id: case for case in cases}
                missing = sorted(expected_ids - set(by_id))
                unexpected = sorted(set(by_id) - expected_ids)
                kill_sets = _mutant_kill_sets(result)
                target_killed_ids = sorted(
                    mid
                    for mid in expected_ids
                    if initial_scope[mid]["target_test"] in kill_sets.get(mid, [])
                )
                killed_ids = sorted(
                    mid
                    for mid in expected_ids
                    if kill_sets.get(mid) == [initial_scope[mid]["target_test"]]
                )
                collateral_kills = sum(
                    len(set(kill_sets.get(mid, [])) - {initial_scope[mid]["target_test"]})
                    for mid in expected_ids
                )
                best_effort_satisfied_ids = sorted(best_effort_ids)
                affected_ids = sorted(
                    mid for mid in expected_ids
                    if mid not in by_id
                    or by_id[mid].status in {"survived", "error"}
                    or (mid not in killed_ids and mid not in best_effort_satisfied_ids)
                )
                ground_truth_ok = bool(
                    bool(len(result))
                    and _reference_ok(result, prune_failing_tests=prune_failing_tests)
                )
                statuses = _ground_truth_test_statuses(result)
                infrastructure_failures = _ground_truth_infrastructure_failures(result)
                ground_truth_validity_rate = result.validity_rate
                record: dict[str, Any] = {
                    "attempt": attempt, "evaluation_retry": evaluation_retry, "eval_json": str(eval_path),
                    "evaluation_mode": (
                        "reused" if evaluation_reused
                        else "incremental" if pending_changed_ids is not None
                        else "full"
                    ),
                    "reevaluated_ids": [] if evaluation_reused else sorted(reevaluated_ids),
                    "ground_truth_passed": result.ground_truth_passed,
                    "ground_truth_ok": ground_truth_ok, "evaluation_error": result.error_code,
                    "ground_truth_validity_rate": ground_truth_validity_rate,
                    "ground_truth_infrastructure_failures": infrastructure_failures,
                    "evaluated": len(cases), "killed": len(killed_ids), "killed_ids": killed_ids,
                    "target_killed": len(target_killed_ids), "target_killed_ids": target_killed_ids,
                    "collateral_kills": collateral_kills,
                    "best_effort_satisfied_ids": best_effort_satisfied_ids,
                    "best_effort_without_target_ids": sorted(best_effort_ids - set(target_killed_ids)),
                    "satisfied": len(set(killed_ids) | set(best_effort_satisfied_ids)),
                    "kill_sets": kill_sets,
                    "requires_repair": affected_ids, "missing": missing, "unexpected": unexpected,
                    "cases": [case.model_dump(mode="json") for case in cases if case.status != "killed"],
                }
                attempts.append(record)

                if ground_truth_ok and prune_failing_tests:
                    dominant = dominant_tests_from_kill_sets(
                        kill_sets,
                        mutant_ids=expected_ids,
                    )
                    already_skipped = load_skipped_tests(skipped_tests, task=task) if skipped_tests else set()
                    dominant = [item for item in dominant if item["test"] not in already_skipped]
                    if dominant:
                        if skipped_tests is None:
                            error = (
                                "A skipped-test list is required to exclude test functions "
                                "that kill more than 50% of mutants"
                            )
                            persist(verified=False, error=error)
                            raise RuntimeError(f"{error}; see {report_path}")
                        added = add_skipped_tests(
                            skipped_tests,
                            task=task,
                            names={item["test"] for item in dominant},
                            reason="our_gt_broad_mutant_kill",
                        )
                        update = {
                            "reason": "our_gt_broad_mutant_kill",
                            "after_attempt": attempt,
                            "evaluation_retry": evaluation_retry,
                            "threshold": 0.5,
                            "tests": added,
                            "test_kill_rates": dominant,
                            "source_eval_json": str(eval_path),
                        }
                        record["dominant_kill_skip_update"] = update
                        added_skipped_tests.append(update)
                        exclude_target_tests(
                            set(added), "target test excluded for killing more than 50% of mutants"
                        )
                        log.warning(
                            "Added test function(s) killing more than 50%% of mutants "
                            "to the skip list for %s: %s",
                            task, ", ".join(added),
                        )
                        validated_result = None
                        validated_eval_path = None
                        pending_changed_ids = None
                        evaluation_retry += 1
                        continue

                missing_target_tests = sorted(
                    {
                        item["target_test"]
                        for item in initial_scope.values()
                        if item["target_test"] not in excluded_target_tests
                    } - set(statuses)
                )
                record["missing_target_tests"] = missing_target_tests
                if ground_truth_ok and missing_target_tests:
                    error = f"Planned target tests are absent from reference evaluation: {missing_target_tests}"
                    persist(verified=False, error=error)
                    raise RuntimeError(f"{error}; see {report_path}")

                if ground_truth_ok:
                    previous_iteration = next(
                        (
                            item for item in reversed(attempts[:-1])
                            if item["attempt"] < attempt and item["ground_truth_ok"]
                        ),
                        None,
                    )
                    _log_iteration_summary(
                        task=task,
                        record=record,
                        total_mutants=len(expected_ids),
                        previous=previous_iteration,
                    )
                    validated_result = result
                    validated_eval_path = eval_path
                    pending_changed_ids = None
                    break

                if infrastructure_failures:
                    if infrastructure_retries < max_infrastructure_retries:
                        infrastructure_retries += 1
                        record["infrastructure_retry"] = {
                            "retry": infrastructure_retries,
                            "max_retries": max_infrastructure_retries,
                            "failures": infrastructure_failures,
                        }
                        log.warning(
                            "Ground-truth evaluation for %s had infrastructure failure(s): %s; "
                            "retrying with unchanged parallelism (%d/%d)",
                            task, ", ".join(infrastructure_failures),
                            infrastructure_retries, max_infrastructure_retries,
                        )
                        evaluation_retry += 1
                        continue
                    error = (
                        "Reference evaluation infrastructure remained unstable after "
                        f"{max_infrastructure_retries} retry attempt(s): "
                        + ", ".join(infrastructure_failures)
                        + "; mutants were not repaired"
                    )
                    persist(verified=False, error=error)
                    raise RuntimeError(f"{error}; see {report_path}")

                non_passing_tests = sorted(
                    name for name, status in statuses.items() if status != "passed"
                )
                if result.error_code is not None or not statuses or not non_passing_tests:
                    error = (
                        "Reference tests are below 100% ground-truth validity rate, but the "
                        "failures cannot be represented as test functions"
                    ) + "; mutants were not repaired"
                    persist(verified=False, error=error)
                    raise RuntimeError(f"{error}; see {report_path}")
                if skipped_tests is None:
                    error = "A skipped-test list is required to record ground-truth failures"
                    persist(verified=False, error=error)
                    raise RuntimeError(f"{error}; see {report_path}")

                added = add_skipped_tests(
                    skipped_tests, task=task, names=set(non_passing_tests),
                )
                record["ground_truth_skip_update"] = {
                    "reason": "our_gt_gold_fail",
                    "after_attempt": attempt,
                    "evaluation_retry": evaluation_retry,
                    "validity_rate_before": ground_truth_validity_rate,
                    "tests": added,
                    "source_eval_json": str(eval_path),
                }
                if added:
                    added_skipped_tests.append(record["ground_truth_skip_update"])
                    exclude_target_tests(set(added), "target test fails against ground truth")
                    log.warning(
                        "Added ground-truth-failing test function(s) to the skip list for %s: %s",
                        task, ", ".join(added),
                    )
                    evaluation_retry += 1
                    continue

                error = (
                    "Reference tests remain below 100% ground-truth validity rate after "
                    "applying the skipped-test list; mutants were not repaired"
                )
                persist(verified=False, error=error)
                raise RuntimeError(f"{error}; see {report_path}")

            if ground_truth_ok and not affected_ids and not unexpected:
                compact_status = compact_mutant_suite(task_mutants)
                dedupe_status = deduplicate_mutant_files(task_mutants, mutants_before)
                record["compact_storage"] = {**compact_status, **dedupe_status}
                if _suite_scope(mutants_root, task) != initial_scope:
                    error = "Mutant IDs or manifest scope changed during kill validation"
                    persist(verified=False, error=error)
                    raise RuntimeError(f"{error}; see {report_path}")
                return persist(verified=True)
            if unexpected:
                error = f"Mutation evaluation returned unexpected mutant IDs: {unexpected}"
                persist(verified=False, error=error)
                raise RuntimeError(f"{error}; see {report_path}")
            if attempt == max_repair_attempts:
                break

            required = {
                "task": task, "attempt": attempt + 1,
                "instructions": "Make each mutant fail its unchanged original target_test within target_spec while minimizing collateral failures.",
                "mutants": [{
                    "mutant_id": mid, "original_scope": initial_scope[mid],
                    "expected_kill_set": [initial_scope[mid]["target_test"]],
                    "observed_kill_set": kill_sets.get(mid, []),
                    "evaluation": _repair_evaluation_payload(by_id[mid]) if mid in by_id else {"status": "missing"},
                } for mid in affected_ids],
            }
            evidence = work_dir / f"repair_required.attempt_{attempt + 1}.json"
            evidence.write_text(json.dumps(required, indent=2))
            prompt = mutant_kill_repair_prompt(task=task, attempt=attempt + 1, affected_ids=affected_ids)
            prompt_path = work_dir / f"repair_mutants.attempt_{attempt + 1}.prompt.md"
            prompt_path.write_text(prompt)

            with tempfile.TemporaryDirectory(prefix="programbench-mutant-kill-repair-") as workspace_name:
                workspace = Path(workspace_name)
                shutil.copytree(task_spec, workspace / "specification", symlinks=True)
                shutil.copytree(task_tests, workspace / "reference-tests", symlinks=True)
                if skipped_tests is not None:
                    shutil.copy2(skipped_tests_path(skipped_tests, task), workspace / "skipped_tests.json")
                (workspace / "mutants").mkdir()
                for mid in affected_ids:
                    shutil.copytree(task_mutants / mid, workspace / "mutants" / mid, symlinks=True)
                (workspace / "repair_required.json").write_text(json.dumps(required, indent=2))
                repair_attempt = attempt + 1
                active_model = (retry_model or model) if repair_attempt >= 2 else model
                active_reasoning = (
                    (retry_reasoning_effort or reasoning_effort)
                    if repair_attempt >= 2
                    else reasoning_effort
                )
                record["repair_route"] = {
                    "model": active_model,
                    "reasoning_effort": active_reasoning,
                    "image": selected_repair_image,
                }
                trajectory_path = work_dir / f"repair_mutants.attempt_{attempt + 1}.traj.json"
                log.info(
                    "Starting Codex mutant repair request %d/%d for %s: %d mutant(s) [%s]; "
                    "model=%s, reasoning=%s, evidence=%s, trajectory=%s",
                    attempt + 1,
                    max_repair_attempts,
                    task,
                    len(affected_ids),
                    ", ".join(affected_ids),
                    active_model,
                    active_reasoning,
                    evidence,
                    trajectory_path,
                )
                repair_started = time.monotonic()
                repair = repair_runner(prompt, workspace) if repair_runner is not None else _default_repair_runner(
                    prompt, workspace, affected_ids=affected_ids, model=active_model,
                    reasoning_effort=active_reasoning,
                    codex_command=codex_command, timeout=timeout, image=selected_repair_image,
                    keep_build_dir=keep_build_dir,
                )
                _write_codex_trajectory(
                    path=trajectory_path,
                    instance_id=task,
                    prompt=prompt,
                    events=_repair_codex_events(repair),
                    status=repair,
                    info={
                        "task": "repair-mutants",
                        "attempt": attempt + 1,
                        "model": active_model,
                        "reasoning_effort": active_reasoning,
                        "image": selected_repair_image,
                        "affected_ids": affected_ids,
                    },
                )
                repair_elapsed = time.monotonic() - repair_started
                log.info(
                    "Codex mutant repair request %d/%d for %s returned in %.1fs "
                    "with return code %s; saved trajectory=%s",
                    attempt + 1,
                    max_repair_attempts,
                    task,
                    repair_elapsed,
                    repair.get("returncode", 1),
                    trajectory_path,
                )
                record.update(
                    repair=_compact_repair_result(repair),
                    repair_trajectory=str(trajectory_path),
                    repair_prompt=str(prompt_path),
                    repair_required=str(evidence),
                )
                if int(repair.get("returncode", 1)) != 0:
                    detail = str(repair.get("exception_info") or repair.get("stderr") or "").strip()
                    if len(detail) > 2000:
                        detail = detail[-2000:]
                    error = f"Mutant repair attempt {attempt + 1} failed with return code {repair.get('returncode', 1)}"
                    if detail:
                        error += f": {detail}"
                    error += f"; see {trajectory_path}"
                    record["repair_error"] = error
                    log.warning("%s; continuing within the best-effort repair budget", error)
                    pending_changed_ids = set()
                    continue
                changed_ids = sorted(str(mid) for mid in repair.get("changed_ids", affected_ids))
                kept_as_is = {
                    str(mid): str(reason)
                    for mid, reason in dict(repair.get("kept_as_is") or {}).items()
                }
                if set(changed_ids) & set(kept_as_is) or set(changed_ids) | set(kept_as_is) != set(affected_ids):
                    error = "Repair outcome must classify every affected mutant exactly once"
                    persist(verified=False, error=error)
                    raise RuntimeError(f"{error}; see {trajectory_path}")
                best_effort_ids.update(kept_as_is)
                best_effort_reasons.update(kept_as_is)
                outcome_path = work_dir / f"repair_outcome.attempt_{attempt + 1}.json"
                changed_mutants = {
                    str(mid): str(summary)
                    for mid, summary in dict(repair.get("changed_mutants") or {}).items()
                }
                repair_summaries.update(changed_mutants)
                outcome_path.write_text(json.dumps({
                    "changed_mutants": changed_mutants or {mid: "edited" for mid in changed_ids},
                    "kept_as_is": kept_as_is,
                }, indent=2) + "\n")
                record["repair_outcome"] = str(outcome_path)
                record["best_effort_satisfied_ids"] = sorted(best_effort_ids)
                record["best_effort_without_target_ids"] = sorted(best_effort_ids - set(target_killed_ids))
                record["satisfied"] = len(set(killed_ids) | best_effort_ids)
                for mid in changed_ids:
                    repaired = workspace / "mutants" / mid
                    if not (repaired / "executable").is_file():
                        error = f"Repaired mutant has no executable: {mid}"
                        persist(verified=False, error=error)
                        raise RuntimeError(f"{error}; see {report_path}")
                    shutil.rmtree(task_mutants / mid)
                    shutil.copytree(repaired, task_mutants / mid, symlinks=True)
                compact_status = compact_mutant_suite(task_mutants)
                dedupe_status = deduplicate_mutant_files(task_mutants, mutants_before)
                record["compact_storage"] = {**compact_status, **dedupe_status}
                next_step = (
                    "incremental reference-suite reevaluation"
                    if changed_ids
                    else "accept best-effort dispositions without reevaluation"
                )
                log.info(
                    "Completed mutant repair request %d/%d for %s: applied %d [%s], "
                    "kept as-is %d [%s]; next step: %s",
                    attempt + 1,
                    max_repair_attempts,
                    task,
                    len(changed_ids),
                    ", ".join(changed_ids) or "none",
                    len(kept_as_is),
                    ", ".join(sorted(kept_as_is)) or "none",
                    next_step,
                )
                if not changed_ids:
                    return persist(verified=True)
                pending_changed_ids = set(changed_ids)

        remaining_ids = set(attempts[-1]["requires_repair"])
        for mutant_id in remaining_ids:
            best_effort_reasons.setdefault(
                mutant_id,
                f"Exact singleton kill set was not achieved within {max_repair_attempts} repair attempt(s).",
            )
        best_effort_ids.update(remaining_ids)
        attempts[-1]["best_effort_satisfied_ids"] = sorted(best_effort_ids)
        attempts[-1]["best_effort_without_target_ids"] = sorted(
            best_effort_ids - set(attempts[-1]["target_killed_ids"])
        )
        attempts[-1]["satisfied"] = len(
            set(attempts[-1]["killed_ids"]) | best_effort_ids
        )
        attempts[-1]["repair_budget_exhausted"] = bool(remaining_ids)
        compact_status = compact_mutant_suite(task_mutants)
        dedupe_status = deduplicate_mutant_files(task_mutants, mutants_before)
        attempts[-1]["compact_storage"] = {**compact_status, **dedupe_status}
        if _suite_scope(mutants_root, task) != initial_scope:
            error = "Mutant IDs or manifest scope changed during kill validation"
            persist(verified=False, error=error)
            raise RuntimeError(f"{error}; see {report_path}")
        return persist(verified=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ground truth and improve mutant focus within a best-effort repair budget.")
    parser.add_argument("--task", required=True)
    parser.add_argument("--tests-dir", type=Path, required=True)
    parser.add_argument("--skipped-tests", type=Path, required=True)
    parser.add_argument("--ground-truth-dir", type=Path, required=True)
    parser.add_argument("--ground-truth-implementation-dir", type=Path)
    parser.add_argument("--mutants-dir", type=Path, required=True)
    parser.add_argument("--spec-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING)
    parser.add_argument("--retry-model")
    parser.add_argument("--retry-reasoning")
    parser.add_argument("--codex-command", default=DEFAULT_CODEX_COMMAND)
    parser.add_argument(
        "--repair-image",
        default="",
        help="Codex-enabled task cleanroom image used to edit and rebuild repaired mutants.",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-repair-attempts", type=int, default=3)
    parser.add_argument(
        "--max-infrastructure-retries", type=int,
        default=DEFAULT_MAX_INFRASTRUCTURE_RETRIES,
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--branch-workers", type=int, default=2)
    parser.add_argument("--cpu-budget", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--prune-failing-tests", action="store_true",
        help="Add ground-truth-failing and broadly-killing test functions to the skip list "
        "(default: keep the reference suite fixed).",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    report = ensure_mutants_killed(
        task=args.task, tests_root=args.tests_dir, mutants_root=args.mutants_dir, spec_root=args.spec_dir,
        work_dir=args.work_dir, model=args.model, reasoning_effort=args.reasoning,
        retry_model=args.retry_model, retry_reasoning_effort=args.retry_reasoning,
        codex_command=args.codex_command, repair_image=args.repair_image,
        timeout=args.timeout, max_repair_attempts=args.max_repair_attempts,
        max_infrastructure_retries=args.max_infrastructure_retries, workers=args.workers,
        branch_workers=args.branch_workers, cpu_budget=args.cpu_budget, force=args.force,
        skipped_tests=args.skipped_tests, ground_truth_dir=args.ground_truth_dir,
        ground_truth_implementation_dir=args.ground_truth_implementation_dir,
        prune_failing_tests=args.prune_failing_tests,
    )
    print(f"Validity Rate: {report["validity_rate"] * 100:.0f}%")
    print(f"Mutation Score: {report["mutation_score"] * 100:.0f}%")
    print(f"Mutants: {report["mutants"]}")
    print(f"Mutant diff: {report["mutant_diff"]}")
    print(f"Report: {report["report"]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
