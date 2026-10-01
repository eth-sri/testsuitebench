# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Maintain links from the fixed reference suite to the finalized iteration spec."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from programbench.codex import build_codex_shell_command, run_codex_in_container
from programbench.constants import cleanroom_codex_image
from programbench.test_spec_links import (
    TEST_SPEC_LINKS_FILENAME,
    load_reference_test_functions,
    normalize_link_manifest,
    numbered_spec_sections,
    starter_manifest,
)

log = logging.getLogger(__name__)

DEFAULT_LINK_ATTEMPTS = 3

LinkRunner = Callable[[str, Path], dict[str, Any]]
DEFAULT_CODEX_COMMAND = (
    "npx -y @openai/codex@0.158.0 --dangerously-bypass-approvals-and-sandbox "
    "exec --cd /workspace --skip-git-repo-check"
)
DEFAULT_SKIPPED_TESTS = Path("ground_truth/skipped-tests")


def build_reference_test_link_prompt(*, task: str, branch: str) -> str:
    return f"""\
You are linking the fixed reference tests for the task `{task}` to its specification.

## Workspace

- `spec/`: the specification.
- `test/{branch}/`: the immutable reference-test source for this branch.
- `{TEST_SPEC_LINKS_FILENAME}`: every active test function in this branch, seeded with any reusable prior links.

## Task

Inspect each listed test function and update `{TEST_SPEC_LINKS_FILENAME}` so that:
- `target_specs` is a non-empty list of the `Spec N` sections whose behavior the function directly verifies;
- every target is exactly one entry from the manifest's `spec_sections` list;
- `description` is one concise sentence describing the asserted behavior; and
- every existing `id`, `branch`, `name`, and optional `cases` field is preserved exactly once.

## Rules

- Treat the reference tests as immutable and authoritative.
- Do not modify `spec/` or `test/`.
- Map every function in the manifest, including functions whose prior links are already populated.

## Output

Write the complete edited manifest to `{TEST_SPEC_LINKS_FILENAME}`.

## Final Response

When finished, return only:
{{"output_path": "{TEST_SPEC_LINKS_FILENAME}"}}
Do not add markdown or other text. The manifest file is authoritative.
"""


def carry_or_link_reference_tests(
    *,
    task: str,
    spec_dir: Path,
    tests_dir: Path,
    skipped_tests: Path | None = None,
    previous_output: Path,
    output: Path,
    spec_changed: bool,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    branch_workers: int,
    trajectory: Path | None = None,
    dry_run: bool = False,
    runner: LinkRunner | None = None,
    attempts: int = DEFAULT_LINK_ATTEMPTS,
) -> dict[str, Any]:
    """Carry a valid manifest forward, or rebuild it against the finalized spec."""
    task_tests = tests_dir / task if (tests_dir / task).is_dir() else tests_dir
    from programbench.skipped_tests import load_skipped_tests

    excluded = load_skipped_tests(skipped_tests, task=task)
    functions = load_reference_test_functions(task_tests, skipped_tests=excluded)
    valid_specs = numbered_spec_sections(spec_dir)
    previous_manifest: dict[str, Any] | None = None
    previous_valid = False
    if previous_output.is_file():
        try:
            previous_manifest = normalize_link_manifest(
                json.loads(previous_output.read_text()),
                task=task,
                functions=functions,
                valid_specs=valid_specs,
            )
            previous_valid = True
        except (json.JSONDecodeError, ValueError):
            log.info("Existing test/spec links are invalid for the finalized spec; rebuilding them")

    output.parent.mkdir(parents=True, exist_ok=True)
    if not spec_changed and previous_valid and previous_manifest is not None:
        output.write_text(json.dumps(previous_manifest, indent=2, sort_keys=True) + "\n")
        result = {
            "status": "carried_forward",
            "output": str(output),
            "previous_output": str(previous_output),
            "branches": [],
            "usage": {},
            "usage_calls": 0,
        }
        _write_link_trajectory(trajectory, task=task, model=model, reasoning_effort=reasoning_effort, result=result)
        return result

    seed = previous_manifest or {
        **starter_manifest(task=task, functions=functions),
        "spec_sections": valid_specs,
    }
    if dry_run:
        seed = normalize_link_manifest(
            seed,
            task=task,
            functions=functions,
            valid_specs=valid_specs,
            require_complete=False,
        )
        output.write_text(json.dumps(seed, indent=2, sort_keys=True) + "\n")
        result = {
            "status": "mapping_required",
            "output": str(output),
            "previous_output": str(previous_output),
            "branches": [],
            "usage": {},
            "usage_calls": 0,
        }
        _write_link_trajectory(trajectory, task=task, model=model, reasoning_effort=reasoning_effort, result=result)
        return result

    return link_reference_tests_to_spec(
        task=task,
        spec_dir=spec_dir,
        tests_dir=task_tests,
        output=output,
        skipped_tests=excluded,
        model=model,
        reasoning_effort=reasoning_effort,
        codex_command=codex_command,
        timeout=timeout,
        branch_workers=branch_workers,
        trajectory=trajectory,
        seed_manifest=seed,
        runner=runner,
        attempts=attempts,
    )


def link_reference_tests_to_spec(
    *,
    task: str,
    spec_dir: Path,
    tests_dir: Path,
    skipped_tests: set[str] | None = None,
    output: Path,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    branch_workers: int,
    trajectory: Path | None = None,
    seed_manifest: dict[str, Any] | None = None,
    runner: LinkRunner | None = None,
    attempts: int = DEFAULT_LINK_ATTEMPTS,
) -> dict[str, Any]:
    """Map every fixed-test function to the finalized spec, one branch per worker."""
    if branch_workers < 1:
        raise ValueError("branch_workers must be at least 1")
    functions = load_reference_test_functions(tests_dir, skipped_tests=skipped_tests)
    valid_specs = numbered_spec_sections(spec_dir)
    seed = normalize_link_manifest(
        seed_manifest or starter_manifest(task=task, functions=functions),
        task=task,
        functions=functions,
        valid_specs=valid_specs,
        require_complete=False,
    )
    seed_by_id = {item["id"]: item for item in seed["test_functions"]}
    branches: dict[str, list[dict[str, Any]]] = {}
    for function in functions:
        branches.setdefault(str(function.get("branch", "")), []).append(seed_by_id[function["id"]])

    with tempfile.TemporaryDirectory(prefix="programbench-reference-test-linking-") as root_name:
        root = Path(root_name)
        jobs = [
            (index, branch, branch_functions, root / f"branch_{index:04d}")
            for index, (branch, branch_functions) in enumerate(branches.items(), start=1)
        ]
        max_workers = min(branch_workers, len(jobs)) if jobs else 1
        if max_workers > 1:
            log.info("Linking %s reference-test branches with %s workers", len(jobs), max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                executor.map(
                    lambda job: _link_reference_test_branch(
                        task=task,
                        branch_index=job[0],
                        branch=job[1],
                        functions=job[2],
                        valid_specs=valid_specs,
                        workspace=job[3],
                        spec_dir=spec_dir,
                        tests_dir=tests_dir,
                        model=model,
                        reasoning_effort=reasoning_effort,
                        codex_command=codex_command,
                        timeout=timeout,
                        runner=runner,
                        attempts=attempts,
                    ),
                    jobs,
                )
            )

    failed_results = [branch_result for branch_result in results if branch_result.get("error")]
    if failed_results:
        failed = {
            "status": "failed",
            "output": str(output),
            "branches": [
                {
                    key: value
                    for key, value in branch_result.items()
                    if key not in {"test_functions", "codex"}
                }
                for branch_result in results
            ],
            "usage": _sum_usage([branch_result["usage"] for branch_result in results]),
            "usage_calls": sum(
                int(branch_result.get("usage_calls", 0) or 0) for branch_result in results
            ),
        }
        _write_link_trajectory(
            trajectory, task=task, model=model, reasoning_effort=reasoning_effort, result=failed
        )
        raise RuntimeError(str(failed_results[0]["error"]))

    linked_functions = [function for result in results for function in result["test_functions"]]
    manifest = normalize_link_manifest(
        {"test_functions": linked_functions},
        task=task,
        functions=functions,
        valid_specs=valid_specs,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    result = {
        "status": "linked",
        "output": str(output),
        "branches": [
            {
                key: value
                for key, value in branch_result.items()
                if key not in {"test_functions", "codex"}
            }
            for branch_result in results
        ],
        "usage": _sum_usage([branch_result["usage"] for branch_result in results]),
        "usage_calls": sum(
            int(branch_result.get("usage_calls", 0) or 0) for branch_result in results
        ),
    }
    _write_link_trajectory(
        trajectory, task=task, model=model, reasoning_effort=reasoning_effort, result=result
    )
    return result


def _write_link_trajectory(
    trajectory: Path | None,
    *,
    task: str,
    model: str,
    reasoning_effort: str,
    result: dict[str, Any],
) -> None:
    if trajectory is None:
        return
    trajectory.parent.mkdir(parents=True, exist_ok=True)
    trajectory.write_text(
        json.dumps(
            {
                "info": {
                    "task": "link-reference-tests",
                    "status": result["status"],
                    "model": model,
                    "reasoning_effort": reasoning_effort,
                    "output": result["output"],
                },
                "instance_id": task,
                "usage": result.get("usage", {}),
                "usage_calls": result.get("usage_calls", 0),
                "branches": result.get("branches", []),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _link_reference_test_branch(
    *,
    task: str,
    branch_index: int,
    branch: str,
    functions: list[dict[str, Any]],
    valid_specs: list[str],
    workspace: Path,
    spec_dir: Path,
    tests_dir: Path,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    runner: LinkRunner | None,
    attempts: int = DEFAULT_LINK_ATTEMPTS,
) -> dict[str, Any]:
    workspace.mkdir(parents=True)
    shutil.copytree(spec_dir, workspace / "spec", symlinks=True)
    branch_source = tests_dir / branch
    if not branch_source.is_dir():
        raise FileNotFoundError(f"Reference-test branch does not exist: {branch_source}")
    shutil.copytree(branch_source, workspace / "test" / branch, symlinks=True)
    manifest_path = workspace / TEST_SPEC_LINKS_FILENAME
    prompt = build_reference_test_link_prompt(task=task, branch=branch)
    started = time.time()
    usage_batches: list[dict[str, int]] = []
    usage_calls = 0
    error_message = ""

    for attempt in range(1, attempts + 1):
        # Reset the seed so a rejected manifest from a prior attempt cannot leak into this one.
        manifest_path.write_text(
            json.dumps(
                {
                    **starter_manifest(task=task, functions=functions),
                    "spec_sections": valid_specs,
                },
                indent=2,
            )
        )
        if runner is not None:
            raw_manifest = runner(prompt, workspace)
        else:
            result = run_codex_in_container(
                build_codex_shell_command(
                    codex_command,
                    prompt=prompt,
                    model=model.removeprefix("codex/"),
                    reasoning_effort=reasoning_effort,
                    diagnostic_action=f"link reference tests for {branch}",
                ),
                cwd=workspace,
                image=cleanroom_codex_image(task),
                timeout=timeout,
                copy_back_files=[TEST_SPEC_LINKS_FILENAME],
            )
            usage_batches.append(
                {
                    key: value
                    for key, value in (result.get("usage") or {}).items()
                    if isinstance(value, int) and not isinstance(value, bool)
                }
            )
            usage_calls += int(result.get("usage_calls", 0) or 0)
            if result["returncode"] != 0:
                error_message = f"Codex exited {result['returncode']}: {str(result.get('stderr', '')).strip()}"
                log.warning(
                    "Reference-test linking attempt %s/%s failed for branch %r: %s",
                    attempt, attempts, branch, error_message,
                )
                continue
            try:
                raw_manifest = json.loads(manifest_path.read_text())
            except json.JSONDecodeError as error:
                error_message = f"Linker wrote invalid {TEST_SPEC_LINKS_FILENAME}: {error}"
                log.warning(
                    "Reference-test linking attempt %s/%s failed for branch %r: %s",
                    attempt, attempts, branch, error_message,
                )
                continue

        # An incomplete or out-of-range manifest is model nondeterminism, not a fatal input error.
        try:
            linked = normalize_link_manifest(
                raw_manifest,
                task=task,
                functions=functions,
                valid_specs=valid_specs,
            )
        except ValueError as error:
            error_message = str(error)
            log.warning(
                "Reference-test linking attempt %s/%s produced an unusable manifest for branch %r: %s",
                attempt, attempts, branch, error_message,
            )
            continue

        usage = _sum_usage(usage_batches)
        return {
            "branch_index": branch_index,
            "branch": branch,
            "function_count": len(functions),
            "duration_seconds": time.time() - started,
            "attempts": attempt,
            "usage": usage,
            "usage_calls": usage_calls,
            "codex": {"usage": usage, "usage_calls": usage_calls},
            "test_functions": linked["test_functions"],
        }

    usage = _sum_usage(usage_batches)
    return {
        "branch_index": branch_index,
        "branch": branch,
        "function_count": len(functions),
        "duration_seconds": time.time() - started,
        "attempts": attempts,
        "usage": usage,
        "usage_calls": usage_calls,
        "codex": {"usage": usage, "usage_calls": usage_calls},
        "error": (
            f"Reference-test linking failed for branch {branch!r} "
            f"after {attempts} attempt(s): {error_message}"
        ),
        "test_functions": [],
    }


def _sum_usage(usages: list[dict[str, int]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for usage in usages:
        for key, value in usage.items():
            totals[key] = totals.get(key, 0) + value
    return totals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Link every fixed reference test to the finalized specification sections."
    )
    parser.add_argument("--task", required=True, help="Task instance id")
    parser.add_argument("--spec-dir", type=Path, required=True, help="Task-specific specification directory")
    parser.add_argument("--tests-dir", type=Path, required=True, help="Fixed reference-test root")
    parser.add_argument(
        "--skipped-tests",
        type=Path,
        default=DEFAULT_SKIPPED_TESTS,
        help=(
            "Skipped-test JSON file or directory "
            f"(default: {DEFAULT_SKIPPED_TESTS})"
        ),
    )
    parser.add_argument("--output", type=Path, required=True, help=f"Output {TEST_SPEC_LINKS_FILENAME}")
    parser.add_argument("--trajectory", type=Path, help="Codex token-usage trajectory output")
    parser.add_argument("--model", default="codex/gpt-5.6-luna")
    parser.add_argument("--reasoning", default="high")
    parser.add_argument("--codex-command", default=DEFAULT_CODEX_COMMAND)
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--branch-workers", type=int, default=4)
    parser.add_argument(
        "--link-attempts", type=int, default=DEFAULT_LINK_ATTEMPTS,
        help="Per-branch linking attempts before the branch is reported as failed",
    )
    args = parser.parse_args(argv)

    from programbench.skipped_tests import load_skipped_tests

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    task_tests = args.tests_dir / args.task
    result = link_reference_tests_to_spec(
        task=args.task,
        spec_dir=args.spec_dir,
        tests_dir=task_tests if task_tests.is_dir() else args.tests_dir,
        skipped_tests=load_skipped_tests(args.skipped_tests, task=args.task),
        output=args.output,
        trajectory=args.trajectory,
        model=args.model,
        reasoning_effort=args.reasoning,
        codex_command=args.codex_command,
        timeout=args.timeout,
        branch_workers=args.branch_workers,
        attempts=args.link_attempts,
    )
    print(f"Test/spec links: {result['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
