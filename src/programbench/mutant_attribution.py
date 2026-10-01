# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Classify generated-test failures and immutable-mutant coverage evidence."""

from __future__ import annotations

import argparse
import ast
import json
import logging
import re
import shutil
import tarfile
import tempfile
from collections import Counter
from functools import partial
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from programbench.classifier_retry import ClassifierBatchUsage, retry_classifier_batch
from programbench.codex import build_codex_shell_command, run_codex_in_container
from programbench.constants import cleanroom_codex_image, eval_network_note
from programbench.eval.test_suite_eval import (
    TestSuiteEvaluationResult,
    _effective_test_names,
    _matrix_status,
    _statuses_by_binary,
)
from programbench.failure_attribution import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CLASSIFIER_RESULT_PATH,
    _load_classifier_output_path,
    group_by_root_cause,
    spec_quote_is_verifiable,
    spec_text,
    DEFAULT_BATCH_WORKERS,
    DEFAULT_CODEX_COMMAND,
    FAILED_STATUSES,
    ClassifierUsageReport,
    _classifier_usage_report,
    _codex_usage_from_stdout,
    _failure_batches,
    _last_agent_message,
    _parse_classifier_json,
    INSTALLER_NETWORK_SIGNATURES,
    attribution_is_unusable,
    check_attribution_usable,
    extract_relevant_specs,
    infer_task_from_eval_json,
    normalize_spec_fault,
    normalize_spec_summary,
    SPEC_FAULTS,
    task_scoped_dir,
)
from programbench.mutant_storage import SOURCES_MANIFEST, materialize_mutant_sources
from programbench.mutants import MutantSpec, load_mutant_suite
from programbench.utils.ground_truth_store import resolve_implementation_dir
from programbench.utils.mutant_store import resolve_mutants_dir

log = logging.getLogger(__name__)

# Longer than the candidate classifier's budget: these batches also run the reference
# binary, and a timeout costs a halving-retry cascade rather than one lost batch.
DEFAULT_TIMEOUT = 3600

MutantFault = Literal["test", "spec_underspecification", "spec_contradiction", "unknown"]
GeneratedTestFault = Literal["test", "spec_underspecification", "spec_contradiction", "flaky", "error", "error_infra", "unknown"]


class GeneratedTestFailureCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    name: str
    status: str
    message: str = ""
    traceback: str = ""
    timing_sensitive: bool = False
    flaky_siblings_in_file: int = 0


class GeneratedTestAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    name: str
    status: str
    fault: GeneratedTestFault
    subreason: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str = ""
    spec_quote: str = ""
    replayed_with_fix: bool = False
    fix_description: str = ""
    recommended_action: str = ""
    error_log: str = ""
    relevant_specs: list[str] = Field(default_factory=list)
    raw_response: str = Field(default="", exclude=True)
    classifier_errors: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_spec_fault(cls, value: Any) -> Any:
        if isinstance(value, dict) and value.get("fault") == "spec":
            value = {**value, "fault": normalize_spec_fault(value["fault"], value.get("subreason", ""))}
        return value


class MutantCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    mutant_id: str
    status: Literal["killed", "survived", "error"]
    mutation: str = ""
    target_spec: str = ""
    payload: str = ""
    error_code: str | None = None
    error_details: str | None = None
    n_tests: int = 0
    n_ground_truth_passing_tests: int = 0
    n_candidate_passing_ground_truth_tests: int = 0
    killed_by: list[str] = []
    passed_ground_truth_tests: list[str] = []



class MutantAttribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    mutant_id: str
    status: str
    fault: MutantFault
    subreason: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str = ""
    recommended_action: str = ""
    most_relevant_spec: str = ""
    other_relevant_specs: list[str] = Field(default_factory=list)
    raw_response: str = Field(default="", exclude=True)
    classifier_errors: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_spec_fault(cls, value: Any) -> Any:
        if isinstance(value, dict) and value.get("fault") == "spec":
            value = {**value, "fault": normalize_spec_fault(value["fault"], value.get("subreason", ""))}
        return value


class MutantAttributionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_json: str
    spec_dir: str
    tests_dir: str
    mutants_dir: str
    output: str
    dry_run: bool = False
    summary: dict[str, int]
    mutant_action_summary: dict[str, int] = Field(default_factory=dict)
    test_failure_summary: dict[str, int] = Field(default_factory=dict)
    classifier_usage: ClassifierUsageReport = Field(default_factory=ClassifierUsageReport)
    test_failures: list[GeneratedTestAttribution] = Field(default_factory=list)
    mutants: list[MutantAttribution]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_summaries(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = {
                **value,
                "summary": normalize_spec_summary(value.get("summary", {})),
                "test_failure_summary": normalize_spec_summary(value.get("test_failure_summary", {})),
            }
        return value


def resolve_test_eval_json(source: Path, *, task: str = "") -> Path:
    if source.is_file():
        return source
    if not source.is_dir():
        raise FileNotFoundError(f"Mutation evaluation source does not exist: {source}")
    if task:
        candidates = [
            source / task / f"{task}.test_eval.json",
            source / f"{task}.test_eval.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
    matches = sorted(source.glob("**/*.test_eval.json"))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"No .test_eval.json found under {source}")
    raise RuntimeError(f"Multiple .test_eval.json files found under {source}; pass --task or the JSON path directly")


def default_output_path(source: Path, eval_json: Path) -> Path:
    task = infer_task_from_eval_json(eval_json)
    if source.is_dir():
        return source / "log" / task / "mutant_attribution.json"
    return eval_json.with_name(f"{task}.mutant_attribution.json")


def task_mutants_dir(path: Path, *, task: str) -> Path:
    return path / task if task and (path / task).is_dir() else path


def load_mutant_cases(
    eval_json: Path,
    *,
    mutants_dir: Path | None = None,
    task: str = "",
) -> list[MutantCase]:
    instance_id = task or infer_task_from_eval_json(eval_json)
    result = TestSuiteEvaluationResult.model_validate_json(eval_json.read_text())
    mutant_lookup = _mutant_lookup(mutants_dir, instance_id) if mutants_dir is not None else {}
    test_names = _effective_test_names(result.binary_results)
    statuses_by_binary = _statuses_by_binary(result.binary_results) if result.binary_results else {}
    ground_truth_passing = sorted(result.ground_truth_passing_test_names)
    cases: list[MutantCase] = []

    for candidate in result.candidate_results:
        mutant = mutant_lookup.get(candidate.binary_id)
        if candidate.error_code is not None:
            cases.append(
                MutantCase(
                    instance_id=instance_id,
                    mutant_id=candidate.binary_id,
                    status="error",
                    mutation=mutant.mutation if mutant else "",
                    target_spec=mutant.target_spec if mutant else "",
                    payload=mutant.payload if mutant else "",
                    error_code=candidate.error_code,
                    error_details=candidate.error_details,
                    n_tests=len(test_names),
                    n_ground_truth_passing_tests=len(ground_truth_passing),
                    passed_ground_truth_tests=ground_truth_passing,
                )
            )
            continue

        candidate_statuses = statuses_by_binary.get(candidate.binary_id, {})
        killed_by = [
            test_name
            for test_name in ground_truth_passing
            if _matrix_status(candidate_statuses, test_name) != "passed"
        ]
        candidate_passed = [
            test_name
            for test_name in ground_truth_passing
            if _matrix_status(candidate_statuses, test_name) == "passed"
        ]
        cases.append(
            MutantCase(
                instance_id=instance_id,
                mutant_id=candidate.binary_id,
                status="killed" if killed_by else "survived",
                mutation=mutant.mutation if mutant else "",
                target_spec=mutant.target_spec if mutant else "",
                payload=mutant.payload if mutant else "",
                n_tests=len(test_names),
                n_ground_truth_passing_tests=len(ground_truth_passing),
                n_candidate_passing_ground_truth_tests=len(candidate_passed),
                killed_by=killed_by[:100],
                passed_ground_truth_tests=ground_truth_passing[:100],
            )
        )
    return cases





def load_generated_test_failure_cases(eval_json: Path, *, task: str = "") -> list[GeneratedTestFailureCase]:
    instance_id = task or infer_task_from_eval_json(eval_json)
    result = TestSuiteEvaluationResult.model_validate_json(eval_json.read_text())
    ground_truth_results = result._ground_truth_trials()
    if not ground_truth_results:
        return []

    cases: list[GeneratedTestFailureCase] = []
    for name in sorted(result.flaky_test_names):
        statuses = [
            _matrix_status({test.name: test.status for test in trial.test_results}, name)
            for trial in ground_truth_results
        ]
        first_result = next(
            (test for trial in ground_truth_results for test in trial.test_results if test.name == name),
            None,
        )
        extra = first_result.extra if first_result is not None and isinstance(first_result.extra, dict) else {}
        cases.append(
            GeneratedTestFailureCase(
                instance_id=instance_id,
                name=name,
                status="flaky",
                message="inconsistent reference-trial statuses: " + ", ".join(status or "missing" for status in statuses),
                traceback=str(extra.get("text", "")),
            )
        )

    for test_result in ground_truth_results[0].test_results:
        if test_result.name in result.flaky_test_names or test_result.status not in FAILED_STATUSES:
            continue
        extra = test_result.extra if isinstance(test_result.extra, dict) else {}
        cases.append(
            GeneratedTestFailureCase(
                instance_id=instance_id,
                name=test_result.name,
                status=test_result.status,
                message=str(extra.get("message", "")),
                traceback=str(extra.get("text", "")),
            )
        )
    return cases


def _mutant_lookup(mutants_dir: Path, task: str) -> dict[str, MutantSpec]:
    loaded = load_mutant_suite(mutants_dir, task)
    if loaded is None and mutants_dir.name == task:
        loaded = load_mutant_suite(mutants_dir.parent, task)
    if loaded is None:
        return {}
    _, suite = loaded
    return {mutant.id: mutant for mutant in suite.mutants}


def mutant_payload(case: MutantCase) -> dict[str, Any]:
    return {
        "instance_id": case.instance_id,
        "mutant_id": case.mutant_id,
        "status": case.status,
        "mutation": case.mutation,
        "target_spec": case.target_spec,
        "payload": case.payload,
        "error_code": case.error_code,
        "error_details": case.error_details,
        "n_generated_tests_observed": case.n_tests,
        "n_generated_tests_passing_ground_truth": case.n_ground_truth_passing_tests,
        "n_generated_tests_passing_both_ground_truth_and_mutant": (
            case.n_candidate_passing_ground_truth_tests
        ),
        "generated_tests_passing_ground_truth_but_failing_mutant": case.killed_by,
        "generated_tests_passing_ground_truth": case.passed_ground_truth_tests,
    }





def generated_test_failure_payload(case: GeneratedTestFailureCase) -> dict[str, Any]:
    return {
        "instance_id": case.instance_id,
        "name": case.name,
        "status": case.status,
        "message": case.message,
        "traceback": case.traceback,
        "timing_sensitive": case.timing_sensitive,
        "flaky_siblings_in_file": case.flaky_siblings_in_file,
    }


_TIMING_PATTERN = re.compile(r"\b(sleep|wait_for|wait_until|poll|deadline|timeout|monotonic|perf_counter|select\.select)\b")


def _test_module_and_function(name: str) -> tuple[str, str]:
    parts = re.split(r"\[| \(", name, maxsplit=1)[0].split(".")
    return next((part for part in parts[:-1] if part.startswith("test_")), ""), parts[-1]


def _function_source(tree: ast.Module, function: str, source: str) -> str:
    return "\n".join(
        ast.get_source_segment(source, node) or ""
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function
    )


def annotate_generated_test_cases(
    cases: list[GeneratedTestFailureCase], tests_dir: Path, flaky_names: set[str]
) -> list[GeneratedTestFailureCase]:
    """Attach what the judge cannot see from one traceback: timing dependence and flaky siblings.

    A generated test that polls or sleeps with a fixed deadline can pass every reference trial
    by luck while its twin in the same file was caught flaky; the judge then reads the survivor
    as a specification contradiction. Both facts are cheap to compute here.
    """
    with tempfile.TemporaryDirectory(prefix="programbench-generated-tests-") as extracted_name:
        extracted = Path(extracted_name)
        _copy_tests_for_classifier(tests_dir, extracted / "test")
        sources = {path.stem: path.read_text(errors="replace") for path in extracted.rglob("test_*.py")}
    flaky_modules = Counter(_test_module_and_function(name)[0] for name in flaky_names)
    annotated = []
    for case in cases:
        module, function = _test_module_and_function(case.name)
        source = sources.get(module, "")
        body = _function_source(ast.parse(source), function, source) if source else ""
        annotated.append(
            case.model_copy(
                update={
                    "timing_sensitive": bool(_TIMING_PATTERN.search(body)),
                    "flaky_siblings_in_file": flaky_modules[module],
                }
            )
        )
    return annotated


def build_generated_test_failure_prompt(*, failure_count: int) -> str:
    return f"""\
You are classifying generated tests that failed on the ground-truth executable.

## Workspace

- `/workspace/spec/`: the current specification used to generate the test suite.
- `/workspace/test/`: the Codex-generated test suite produced from `/workspace/spec/`.
- `/workspace/generated_test_failures.json`: generated tests that failed on the ground-truth executable.
- `/workspace/executable`: the ground-truth executable itself. Run it to see what the real behavior is.

## Task

There are {failure_count} generated-test failures in `generated_test_failures.json`.
For each generated-test failure, decide whose fault it is.

## Classification Criteria

- `test`: the generated test exercised the executable but asserted something the specification does not entail: it misread a sentence, demanded an exact incidental value, or depends on timing.
    Recommended action: ignore for spec/mutant polishing.
- `spec_underspecification`: the specification is missing or ambiguous about the behavior, causing the generated test to make an unsupported assumption.
    Recommended action: polish the specification.
- `spec_contradiction`: the specification is misleading or contradicts the reference behavior, causing the generated test to encode the wrong behavior.
    Recommended action: polish the specification.
- `error`: the failure says nothing about the specification or the behavior: the test never reached the executable, its own fixture crashed or was written wrongly (an unexecutable fake tool, a missing input file), or the sandbox interfered.
    {eval_network_note()} A package install that could not reach an index also belongs here.
    Recommended action: ignore for spec/mutant polishing.
- `unknown`: there is not enough information to decide.

Choose `spec_underspecification` or `spec_contradiction` only when the failure is clearly due to the specification.
If the most natural interpretation should not result in this error, it is the `test`'s fault, even if the expected behavior is not stated explicitly.
Never classify an environment failure as a specification fault.

## Rules

- Explore only the relevant specification and generated tests. Do not do broad exploration.
- Run `/workspace/executable` on the failing invocation before deciding. A failure that never reached the executable is `error`; one whose expectation the executable in fact satisfies is `test`.
- Before emitting `spec_contradiction`, copy the misleading specification sentence into `spec_quote`
  exactly as it appears in `/workspace/spec/`, and give the observed reference output that conflicts
  with it in the rationale. A `spec_quote` that is not a literal substring of the specification is
  rejected and the verdict is discarded, so never paraphrase, trim or reflow it.
- Before emitting `test`, copy into `spec_quote` the specification sentence that shows the test's
  expectation is not entailed: the sentence the test misread, or the one that states the behavior the
  reference actually has. The same literal-substring check applies. If no sentence addresses the
  behavior the test assumed, the specification is silent about it: that is `spec_underspecification`,
  not `test`, unless the test's own record shows it never exercised the executable.
- Each record carries `timing_sensitive` (the test sleeps, polls or waits with a fixed deadline) and
  `flaky_siblings_in_file` (tests in the same file that passed and failed across reference trials).
  When both are nonzero and the specification describes the behavior as asynchronous, consolidated or
  best-effort, the failure is a race in the test, not a contradiction: classify it as `test` unless the
  reference fails the invocation deterministically when you replay it.
- You may repair a broken fixture (for example a fake tool with a malformed shebang) to replay the
  test and learn what the reference does. When your verdict rests on such a replay, set
  `replayed_with_fix` to true and describe the repair in `fix_description`; the recorded failure itself
  is then also an `error`, and the spec finding is what the polish step consumes.
- Prefer a specification fault only when clarifying the specification would plausibly prevent this kind of generated test failure. Use "spec_underspecification" for missing or ambiguous guidance and "spec_contradiction" for misleading or contradictory guidance. Prefer "test" when the test asserts behavior not entailed by the spec, exact incidental values, timing-sensitive behavior, or behavior contradicted by the ground truth.

## Output

Return exactly one JSON object with this shape:
{{
  "test_failures": [
    {{
      "name": "same name from generated_test_failures.json",
      "fault": "spec_underspecification|spec_contradiction|test|error|unknown",
      "subreason": "short_snake_case_reason",
      "confidence": 0.0,
      "rationale": "a few sentences that explicitly name every relevant section as Spec N and cover (i) which specification number provides relevant information, (ii) what the test evaluates in that regard, (iii) why the executable fails, and (iv) why it is classified as spec_underspecification/spec_contradiction/test/error/unknown",
      "spec_quote": "for spec_contradiction and test: the sentence copied verbatim from /workspace/spec/, otherwise empty",
      "replayed_with_fix": false,
      "fix_description": "when replayed_with_fix is true: what you repaired to replay the test, otherwise empty",
      "recommended_action": "polish_spec|ignore|manual_review"
    }}
  ]
}}

Return one entry for every case in `generated_test_failures.json`, in the same order.

## Checkpointing

Write the object to `/workspace/classifier_result.json`. Persist incrementally: after each compact
group, atomically rewrite that valid JSON object with every completed entry so far. If time or output
budget runs out, leave as many completed entries as possible.
Every entry needs its own `subreason` and `rationale`; never reuse one verdict across a group.

## Final Response

Do not return the entries inline. When finished, return only:
{{"output_path": "classifier_result.json"}}
Do not add markdown or other text. The checkpoint file is authoritative.
"""


def build_mutant_attribution_prompt(*, mutant_count: int) -> str:
    return f"""\
You are classifying specification clarity and generated-test adequacy using survived immutable mutants.

## Workspace

- `/workspace/spec/`: the current specification for the task.
- `/workspace/test/`: an agent-generated test suite produced from `/workspace/spec/`.
- `/workspace/mutants/`: the relevant mutant repositories or executables.
- `/workspace/mutant_cases.json`: survived mutants to classify.
- `/workspace/executable`: the ground-truth executable. Run it to see what the real behavior is.

## Task

There are {mutant_count} mutant cases in `mutant_cases.json`.
For each mutant case, decide whether the specification needs clarification.

## Evidence Fields

- `n_generated_tests_observed`: all generated tests observed in the evaluation matrix.
- `n_generated_tests_passing_ground_truth`: generated tests accepted as valid because they pass on the ground-truth executable.
- `n_generated_tests_passing_both_ground_truth_and_mutant`: valid generated tests that also pass on this mutant.
- `generated_tests_passing_ground_truth_but_failing_mutant`: valid generated tests that kill this mutant.
- `generated_tests_passing_ground_truth`: the valid generated-test baseline; this is not a list of tests that pass on the mutant.

## Classification Criteria

- `spec_underspecification`: a survived mutant exposes behavior that the specification leaves missing or ambiguous, so future generated suites need clearer instructions.
    Recommended action: polish_spec.
- `spec_contradiction`: a survived mutant exposes behavior for which the specification is misleading or contradicts the reference behavior.
    Recommended action: polish_spec.
- `test`: a survived mutant violates behavior already stated clearly in the specification, so this generated suite is weak or wrong.
    Recommended action: ignore.
- `unknown`: there is not enough information to decide.
    Recommended action: manual_review.


Choose `spec_underspecification` or `spec_contradiction` only when the failure is clearly due to the specification.
If the most natural interpretation should not result in this error, it is the `test`'s fault, even if the expected behavior is not stated explicitly.

## Rules

- Explore only the relevant specification, generated tests, and immutable mutant files. Do not do broad exploration.
- Never recommend changing, rebuilding, removing, strengthening, or narrowing a mutant.


## Output

Return exactly one JSON object with this shape:
{{
  "mutants": [
    {{
      "mutant_id": "same mutant_id from mutant_cases.json",
      "fault": "test|spec_underspecification|spec_contradiction|unknown",
      "subreason": "short_snake_case_reason",
      "confidence": 0.0,
      "rationale": "a few sentences that explicitly name the mutant's target_spec as Spec N, name any other relevant sections as Spec N, and cover (i) which specification number provides relevant information, (ii) what the test evaluates in that regard, (iii) what the scope of the mutant is, (iv) why the mutant survived, and (v) why it is classified as test|spec_underspecification|spec_contradiction|unknown",
      "recommended_action": "ignore|polish_spec|manual_review"
    }}
  ]
}}

Return one entry for every case in `mutant_cases.json`, in the same order.

## Checkpointing

Write the object to `/workspace/classifier_result.json`. Persist incrementally: after each compact
group, atomically rewrite that valid JSON object with every completed entry so far. If time or output
budget runs out, leave as many completed entries as possible.
Every entry needs its own `subreason` and `rationale`; never reuse one verdict across a group.

## Final Response

Do not return the entries inline. When finished, return only:
{{"output_path": "classifier_result.json"}}
Do not add markdown or other text. The checkpoint file is authoritative.
"""


def classify_mutants(
    *,
    eval_json: Path,
    spec_dir: Path,
    tests_dir: Path,
    mutants_dir: Path,
    output: Path,
    ground_truth: Path | None = None,
    model: str = "",
    reasoning_effort: str = "",
    codex_command: str = DEFAULT_CODEX_COMMAND,
    timeout: int = DEFAULT_TIMEOUT,
    limit: int = 0,
    batch_size: int = DEFAULT_BATCH_SIZE,
    batch_workers: int = DEFAULT_BATCH_WORKERS,
    dry_run: bool = False,
    force: bool = False,
    classify_test_failures: bool = True,
    classify_survived_mutants: bool = True,
    runner: Callable[[str], dict[str, Any]] | None = None,
) -> MutantAttributionReport:
    """Classify both evaluation directions into one report.

    The generated-test failures carry the validity rate evidence and the survived mutants carry the
    mutation score evidence; neither reads the other's verdicts, so a caller whose mutation score already converged
    can drop that half and keep paying only for validity rate. The dropped half's records come back
    empty rather than absent, which is what the polisher and the convergence check expect.
    """
    if output.exists() and not force:
        cached = MutantAttributionReport.model_validate_json(output.read_text())
        if not (attribution_is_unusable(cached.test_failures) or attribution_is_unusable(cached.mutants)):
            return cached
        log.warning("Recomputing the unusable cached attribution report: %s", output)
    if batch_size < 0:
        raise ValueError("batch_size must be non-negative")
    if batch_workers < 1:
        raise ValueError("batch_workers must be at least 1")

    task = infer_task_from_eval_json(eval_json)
    spec_dir = task_scoped_dir(spec_dir, task=task)
    tests_dir = task_scoped_dir(tests_dir, task=task)
    image = cleanroom_codex_image(task)
    selected_mutants_dir = task_mutants_dir(mutants_dir, task=task)
    all_test_failure_cases = load_generated_test_failure_cases(eval_json, task=task) if classify_test_failures else []
    flaky_test_cases = [case for case in all_test_failure_cases if case.status == "flaky"]
    offline_install_cases = [
        case
        for case in all_test_failure_cases
        if case.status != "flaky" and _is_installer_network_failure(case)
    ]
    offline_install_names = {case.name for case in offline_install_cases}
    test_failure_cases = [
        case
        for case in all_test_failure_cases
        if case.status != "flaky" and case.name not in offline_install_names
    ]
    cases = load_mutant_cases(eval_json, mutants_dir=mutants_dir, task=task) if classify_survived_mutants else []
    if limit > 0:
        test_failure_cases = test_failure_cases[:limit]
        cases = cases[:limit]

    cases_to_classify = [case for case in cases if case.status == "survived"]
    rule_based_attributions = {
        case.mutant_id: _rule_based_mutant_attribution(case)
        for case in cases
        if case.status == "error"
    }

    flaky_test_attributions = [_flaky_generated_test_attribution(case) for case in flaky_test_cases]
    offline_install_attributions = [
        _offline_install_generated_test_attribution(case) for case in offline_install_cases
    ]

    if test_failure_cases and not dry_run:
        test_failure_cases = annotate_generated_test_cases(
            test_failure_cases, tests_dir, {case.name for case in flaky_test_cases}
        )
    root_cause_groups = group_by_root_cause(test_failure_cases)
    classify = partial(
        _classify_generated_test_failures,
        output=output,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        image=image,
        model=model,
        reasoning_effort=reasoning_effort,
        codex_command=codex_command,
        timeout=timeout,
        batch_size=batch_size,
        batch_workers=batch_workers,
        dry_run=dry_run,
        runner=runner,
    )
    representatives = [group[0] for group in root_cause_groups]
    test_attributions, usage_batches = classify(cases=representatives)
    demoted = _reject_unverifiable_contradictions(test_attributions, spec_dir)
    if demoted and not dry_run:
        log.info("Re-judging %s generated-test verdict(s) whose spec quote was not found", len(demoted))
        rejudged, retry_usage = classify(cases=[case for case in representatives if case.name in demoted])
        usage_batches.extend(retry_usage)
        _reject_unverifiable_contradictions(rejudged, spec_dir)
        verified = {attribution.name: attribution for attribution in rejudged if attribution.fault != "unknown"}
        test_attributions = [verified.get(attribution.name, attribution) for attribution in test_attributions]
    test_attributions = _fan_out_root_causes(root_cause_groups, test_attributions)

    if dry_run:
        prompt_dir = output.with_suffix("")
        prompt_dir.mkdir(parents=True, exist_ok=True)
        attributions = []
        for batch_index, batch in enumerate(_failure_batches(cases_to_classify, batch_size), start=1):
            batch_dir = prompt_dir / f"batch_{batch_index:04d}"
            batch_dir.mkdir(parents=True, exist_ok=True)
            prompt_path = batch_dir / "classify_mutants.prompt.md"
            cases_path = batch_dir / "mutant_cases.json"
            prompt = build_mutant_attribution_prompt(mutant_count=len(batch))
            prompt_path.write_text(prompt)
            cases_path.write_text(json.dumps([mutant_payload(case) for case in batch], indent=2))
            attributions.extend(
                _attribution_from_result(
                    case,
                    {
                        "fault": "unknown",
                        "subreason": "dry_run",
                        "confidence": 0.0,
                        "rationale": f"Prompt written to {prompt_path}; mutant cases written to {cases_path}",
                        "recommended_action": "manual_review",
                    },
                    raw_response="",
                )
                for case in batch
            )
    else:
        batches = _failure_batches(cases_to_classify, batch_size)
        attributions = []
        max_workers = min(batch_workers, len(batches)) if batches else 1
        if runner is None:
            with tempfile.TemporaryDirectory(prefix="programbench-mutant-attribution-") as workspace_root_name:
                workspace_root = Path(workspace_root_name)
                jobs = [
                    (batch_index, batch, workspace_root / f"batch_{batch_index:04d}")
                    for batch_index, batch in enumerate(batches, start=1)
                ]
                if max_workers == 1:
                    for batch_index, batch, workspace in jobs:
                        batch_attributions, batch_usage = _classify_mutant_batch(
                            batch_index=batch_index,
                            batch=batch,
                            workspace=workspace,
                            spec_dir=spec_dir,
                            tests_dir=tests_dir,
                            mutants_dir=selected_mutants_dir,
                            ground_truth=ground_truth,
                            model=model,
                            reasoning_effort=reasoning_effort,
                            codex_command=codex_command,
                            timeout=timeout,
                            image=image,
                            runner=None,
                        )
                        attributions.extend(batch_attributions)
                        if batch_usage is not None:
                            usage_batches.append(batch_usage)
                else:
                    log.info("Classifying %s mutant batches with %s workers", len(jobs), max_workers)
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        for batch_attributions, batch_usage in executor.map(
                            lambda job: _classify_mutant_batch(
                                batch_index=job[0],
                                batch=job[1],
                                workspace=job[2],
                                spec_dir=spec_dir,
                                tests_dir=tests_dir,
                                mutants_dir=selected_mutants_dir,
                                ground_truth=ground_truth,
                                model=model,
                                reasoning_effort=reasoning_effort,
                                codex_command=codex_command,
                                timeout=timeout,
                                image=image,
                                runner=None,
                            ),
                            jobs,
                        ):
                            attributions.extend(batch_attributions)
                            if batch_usage is not None:
                                usage_batches.append(batch_usage)
        else:
            jobs = [(batch_index, batch) for batch_index, batch in enumerate(batches, start=1)]
            if max_workers == 1:
                for batch_index, batch in jobs:
                    batch_attributions, batch_usage = _classify_mutant_batch(
                        batch_index=batch_index,
                        batch=batch,
                        workspace=None,
                        spec_dir=spec_dir,
                        tests_dir=tests_dir,
                        mutants_dir=selected_mutants_dir,
                        ground_truth=ground_truth,
                        model=model,
                        reasoning_effort=reasoning_effort,
                        codex_command=codex_command,
                        timeout=timeout,
                        image=image,
                        runner=runner,
                    )
                    attributions.extend(batch_attributions)
                    if batch_usage is not None:
                        usage_batches.append(batch_usage)
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for batch_attributions, batch_usage in executor.map(
                        lambda job: _classify_mutant_batch(
                            batch_index=job[0],
                            batch=job[1],
                            workspace=None,
                            spec_dir=spec_dir,
                            tests_dir=tests_dir,
                            mutants_dir=selected_mutants_dir,
                            ground_truth=ground_truth,
                            model=model,
                            reasoning_effort=reasoning_effort,
                            codex_command=codex_command,
                            timeout=timeout,
                            image=image,
                            runner=runner,
                        ),
                        jobs,
                    ):
                        attributions.extend(batch_attributions)
                        if batch_usage is not None:
                            usage_batches.append(batch_usage)

    test_attributions = [*flaky_test_attributions, *offline_install_attributions, *test_attributions]

    classified_by_id = {attribution.mutant_id: attribution for attribution in attributions}
    attributions = [
        rule_based_attributions.get(case.mutant_id) or classified_by_id[case.mutant_id]
        for case in cases
        if case.status != "killed"
    ]

    # A direction that was not classified reports nothing, so its counts never read as "no faults found".
    summary = {fault: 0 for fault in ("test", *SPEC_FAULTS, "unknown")} if classify_survived_mutants else {}
    for attribution in attributions:
        summary[attribution.fault] += 1
    mutant_action_summary = _mutant_action_summary(attributions)
    test_failure_summary = (
        {fault: 0 for fault in ("test", *SPEC_FAULTS, "flaky", "error", "error_infra", "unknown")}
        if classify_test_failures
        else {}
    )
    for attribution in test_attributions:
        test_failure_summary[attribution.fault] += 1

    report = MutantAttributionReport(
        eval_json=str(eval_json),
        spec_dir=str(spec_dir),
        tests_dir=str(tests_dir),
        mutants_dir=str(selected_mutants_dir),
        output=str(output),
        dry_run=dry_run,
        summary=summary,
        mutant_action_summary=mutant_action_summary,
        test_failure_summary=test_failure_summary,
        classifier_usage=_classifier_usage_report(usage_batches),
        test_failures=test_attributions,
        mutants=attributions,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2))
    return report





def _is_installer_network_failure(case: GeneratedTestFailureCase) -> bool:
    """Whether a generated test failed only because pip could not reach an index.

    Same infrastructure failure the reference suites hit, and just as cheap to
    recognise here: the generated suite's run.sh installs its dependencies at
    runtime too, and the sandbox has no network.
    """
    haystack = f"{case.message}\n{case.traceback}"
    return any(signature in haystack for signature in INSTALLER_NETWORK_SIGNATURES)


def _offline_install_generated_test_attribution(case: GeneratedTestFailureCase) -> GeneratedTestAttribution:
    return GeneratedTestAttribution(
        instance_id=case.instance_id,
        name=case.name,
        status=case.status,
        fault="error_infra",
        subreason="offline_package_install",
        confidence=1.0,
        rationale=(
            "The generated suite's run.sh installed a package that is not preinstalled in the task "
            "image, and the sandbox has no network, so pip exited non-zero before the test ran."
        ),
        recommended_action="ignore",
        error_log=case.traceback,
    )


def _flaky_generated_test_attribution(case: GeneratedTestFailureCase) -> GeneratedTestAttribution:
    return GeneratedTestAttribution(
        instance_id=case.instance_id,
        name=case.name,
        status="flaky",
        fault="flaky",
        subreason="inconsistent_reference_trials",
        confidence=1.0,
        rationale=(
            "The generated test passed and failed across reference-executable trials, "
            "so it is treated as a wrong test and excluded from mutation mutation score. "
            + case.message
        ),
        recommended_action="ignore",
        error_log=case.traceback,
    )


def _fan_out_root_causes(
    groups: list[list[GeneratedTestFailureCase]],
    representatives: list[GeneratedTestAttribution],
) -> list[GeneratedTestAttribution]:
    """Give every member of a root-cause group its representative's verdict."""
    by_name = {attribution.name: attribution for attribution in representatives}
    fanned: list[GeneratedTestAttribution] = []
    for group in groups:
        verdict = by_name[group[0].name]
        shared = (
            f" Shared root cause with {len(group) - 1} other failing generated test(s); "
            "classified once."
            if len(group) > 1
            else ""
        )
        fanned.extend(
            verdict.model_copy(
                update={
                    "instance_id": case.instance_id,
                    "name": case.name,
                    "status": case.status,
                    "error_log": case.traceback,
                    "rationale": verdict.rationale + shared,
                }
            )
            for case in group
        )
    return fanned


def _reject_unverifiable_contradictions(
    attributions: list[GeneratedTestAttribution],
    spec_dir: Path,
) -> list[str]:
    """Demote a contradiction or test verdict whose quoted specification sentence is not in the specification.

    Returns the names that were demoted so exactly those cases can be judged once more.
    """
    spec = spec_text(spec_dir)
    demoted = []
    for index, attribution in enumerate(attributions):
        if attribution.fault not in {"spec_contradiction", "test"} or spec_quote_is_verifiable(attribution.spec_quote, spec):
            continue
        attributions[index] = attribution.model_copy(
            update={
                "fault": "unknown",
                "subreason": "unverified_spec_quote",
                "recommended_action": "manual_review",
            }
        )
        demoted.append(attribution.name)
    return demoted


def _classify_generated_test_failures(
    *,
    cases: list[GeneratedTestFailureCase],
    output: Path,
    spec_dir: Path,
    tests_dir: Path,
    image: str,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    batch_size: int,
    batch_workers: int,
    dry_run: bool,
    runner: Callable[[str], dict[str, Any]] | None,
) -> tuple[list[GeneratedTestAttribution], list[ClassifierBatchUsage]]:
    if not cases:
        return [], []
    if dry_run:
        prompt_dir = output.with_suffix("") / "generated_test_failures"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        attributions: list[GeneratedTestAttribution] = []
        for batch_index, batch in enumerate(_failure_batches(cases, batch_size), start=1):
            batch_dir = prompt_dir / f"batch_{batch_index:04d}"
            batch_dir.mkdir(parents=True, exist_ok=True)
            prompt_path = batch_dir / "classify_generated_test_failures.prompt.md"
            cases_path = batch_dir / "generated_test_failures.json"
            prompt = build_generated_test_failure_prompt(failure_count=len(batch))
            prompt_path.write_text(prompt)
            cases_path.write_text(json.dumps([generated_test_failure_payload(case) for case in batch], indent=2))
            attributions.extend(
                _generated_test_attribution_from_result(
                    case,
                    {
                        "fault": "unknown",
                        "subreason": "dry_run",
                        "confidence": 0.0,
                        "rationale": f"Prompt written to {prompt_path}; generated-test failures written to {cases_path}",
                        "recommended_action": "manual_review",
                    },
                    raw_response="",
                )
                for case in batch
            )
        return attributions, []

    batches = _failure_batches(cases, batch_size)
    max_workers = min(batch_workers, len(batches)) if batches else 1
    if runner is None:
        with tempfile.TemporaryDirectory(prefix="programbench-generated-test-attribution-") as workspace_root_name:
            workspace_root = Path(workspace_root_name)
            jobs = [
                (batch_index, batch, workspace_root / f"batch_{batch_index:04d}")
                for batch_index, batch in enumerate(batches, start=1)
            ]
            if max_workers == 1:
                attributions = []
                usage_batches = []
                for batch_index, batch, workspace in jobs:
                    batch_attributions, batch_usage = _classify_generated_test_failure_batch(
                        batch_index=batch_index,
                        batch=batch,
                        workspace=workspace,
                        spec_dir=spec_dir,
                        tests_dir=tests_dir,
                        model=model,
                        reasoning_effort=reasoning_effort,
                        codex_command=codex_command,
                        timeout=timeout,
                        image=image,
                        runner=None,
                    )
                    attributions.extend(batch_attributions)
                    if batch_usage is not None:
                        usage_batches.append(batch_usage)
                return attributions, usage_batches
            log.info("Classifying %s generated-test failure batches with %s workers", len(jobs), max_workers)
            attributions = []
            usage_batches = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for batch_attributions, batch_usage in executor.map(
                    lambda job: _classify_generated_test_failure_batch(
                        batch_index=job[0],
                        batch=job[1],
                        workspace=job[2],
                        spec_dir=spec_dir,
                        tests_dir=tests_dir,
                        model=model,
                        reasoning_effort=reasoning_effort,
                        codex_command=codex_command,
                        timeout=timeout,
                        image=image,
                        runner=None,
                    ),
                    jobs,
                ):
                    attributions.extend(batch_attributions)
                    if batch_usage is not None:
                        usage_batches.append(batch_usage)
            return attributions, usage_batches

    jobs = [(batch_index, batch) for batch_index, batch in enumerate(batches, start=1)]
    if max_workers == 1:
        attributions = []
        usage_batches = []
        for batch_index, batch in jobs:
            batch_attributions, batch_usage = _classify_generated_test_failure_batch(
                batch_index=batch_index,
                batch=batch,
                workspace=None,
                spec_dir=spec_dir,
                tests_dir=tests_dir,
                model=model,
                reasoning_effort=reasoning_effort,
                codex_command=codex_command,
                timeout=timeout,
                image=image,
                runner=runner,
            )
            attributions.extend(batch_attributions)
            if batch_usage is not None:
                usage_batches.append(batch_usage)
        return attributions, usage_batches
    attributions = []
    usage_batches = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for batch_attributions, batch_usage in executor.map(
            lambda job: _classify_generated_test_failure_batch(
                batch_index=job[0],
                batch=job[1],
                workspace=None,
                spec_dir=spec_dir,
                tests_dir=tests_dir,
                model=model,
                reasoning_effort=reasoning_effort,
                codex_command=codex_command,
                timeout=timeout,
                image=image,
                runner=runner,
            ),
            jobs,
        ):
            attributions.extend(batch_attributions)
            if batch_usage is not None:
                usage_batches.append(batch_usage)
    return attributions, usage_batches


def _classify_generated_test_failure_batch(
    **kwargs: Any,
) -> tuple[list[GeneratedTestAttribution], ClassifierBatchUsage | None]:
    return retry_classifier_batch(_classify_generated_test_failure_batch_once, **kwargs)


def _classify_mutant_batch(**kwargs: Any) -> tuple[list[MutantAttribution], ClassifierBatchUsage | None]:
    return retry_classifier_batch(_classify_mutant_batch_once, **kwargs)


def _classifier_error(result: dict[str, Any], rationale: str) -> dict[str, Any]:
    # Preserve transport/JSON failures instead of masking them as schema errors.
    if result.get("subreason") in {"classifier_failed", "invalid_classifier_json"}:
        return result
    return {
        "fault": "unknown", "subreason": "invalid_batch_result",
        "confidence": 0.0, "rationale": rationale,
        "recommended_action": "manual_review",
    }


def _validate_classifier_item(item: dict[str, Any], *, mutant: bool) -> dict[str, Any]:
    allowed = {"test", "tests", "spec", *SPEC_FAULTS, "unknown"} if mutant else {"test", "tests", "spec", *SPEC_FAULTS, "error", "unknown"}
    try:
        confidence = float(item.get("confidence", 0.0) or 0.0)
        valid = (
            item.get("fault") in allowed and 0 <= confidence <= 1
            and isinstance(item.get("recommended_action", ""), str)
        )
    except (TypeError, ValueError):
        valid = False
    if valid:
        return item
    return {
        "fault": "unknown", "subreason": "invalid_classifier_item",
        "confidence": 0.0, "rationale": "Classifier returned an invalid fault, confidence, or action type.",
        "recommended_action": "manual_review",
    }


def _classify_generated_test_failure_batch_once(
    *,
    batch_index: int,
    batch: list[GeneratedTestFailureCase],
    workspace: Path | None,
    image: str,
    spec_dir: Path,
    tests_dir: Path,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    runner: Callable[[str], dict[str, Any]] | None,
) -> tuple[list[GeneratedTestAttribution], ClassifierBatchUsage | None]:
    prompt = build_generated_test_failure_prompt(failure_count=len(batch))
    if runner is not None:
        result = runner(prompt)
        raw_response = json.dumps(result)
        return _generated_test_attributions_from_batch_result(batch, result, raw_response=raw_response), None
    if workspace is None:
        raise ValueError("workspace is required when runner is not provided")
    stage_generated_test_failure_classifier_workspace(
        workspace=workspace,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        cases=batch,
    )
    log.info("Classifying generated-test failure batch %s (%s cases)", batch_index, len(batch))
    result, raw_response, usage = run_codex_classifier(
        prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        codex_command=codex_command,
        timeout=timeout,
        cwd=workspace,
        image=image,
        result_key="test_failures",
    )
    batch_usage = ClassifierBatchUsage(
        phase="generated_test_failure_classification",
        batch_index=batch_index,
        case_count=len(batch),
        usage=usage,
    )
    return _generated_test_attributions_from_batch_result(batch, result, raw_response=raw_response), batch_usage


def stage_generated_test_failure_classifier_workspace(
    *,
    workspace: Path,
    spec_dir: Path,
    tests_dir: Path,
    cases: list[GeneratedTestFailureCase],
) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    shutil.copytree(spec_dir, workspace / "spec", symlinks=True)
    _copy_tests_for_classifier(tests_dir, workspace / "test")
    (workspace / "generated_test_failures.json").write_text(
        json.dumps([generated_test_failure_payload(case) for case in cases], indent=2)
    )


def _generated_test_attributions_from_batch_result(
    cases: list[GeneratedTestFailureCase],
    result: dict[str, Any],
    *,
    raw_response: str,
) -> list[GeneratedTestAttribution]:
    items = result.get("test_failures")
    if items is None and "fault" in result and len(cases) == 1:
        items = [result]
    if not isinstance(items, list):
        return [
            _generated_test_attribution_from_result(
                case,
                _classifier_error(result, "Classifier did not return a test_failures list."),
                raw_response=raw_response,
            )
            for case in cases
        ]

    keyed: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and "name" in item:
            keyed[str(item.get("name", ""))] = item

    attributions: list[GeneratedTestAttribution] = []
    for index, case in enumerate(cases):
        item: Any = items[index] if index < len(items) else None
        if not isinstance(item, dict) or (item.get("name") and item.get("name") != case.name):
            item = keyed.get(case.name)
        if not isinstance(item, dict):
            item = {
                "fault": "unknown",
                "subreason": "missing_batch_result",
                "confidence": 0.0,
                "rationale": "Classifier did not return an attribution for this generated-test failure.",
                "recommended_action": "manual_review",
            }
        item = _validate_classifier_item(item, mutant=False)
        attributions.append(_generated_test_attribution_from_result(case, item, raw_response=raw_response))
    return attributions


def _generated_test_attribution_from_result(
    case: GeneratedTestFailureCase,
    result: dict[str, Any],
    *,
    raw_response: str,
) -> GeneratedTestAttribution:
    raw_fault = normalize_spec_fault(result.get("fault"), result.get("subreason", ""))
    if raw_fault == "tests":
        raw_fault = "test"
    fault = raw_fault if raw_fault in {"test", *SPEC_FAULTS, "error", "unknown"} else "unknown"
    action = result.get("recommended_action")
    if action not in {"ignore", "polish_spec", "manual_review"}:
        action = {
            "test": "ignore",
            "spec_underspecification": "polish_spec",
            "spec_contradiction": "polish_spec",
            "error": "ignore",
            "unknown": "manual_review",
        }[fault]
    rationale = str(result.get("rationale", ""))
    return GeneratedTestAttribution(
        instance_id=case.instance_id,
        name=case.name,
        status=case.status,
        fault=fault,
        subreason=str(result.get("subreason", "")),
        confidence=float(result.get("confidence", 0.0) or 0.0),
        rationale=rationale,
        spec_quote=str(result.get("spec_quote", "")),
        replayed_with_fix=bool(result.get("replayed_with_fix", False)),
        fix_description=str(result.get("fix_description", "")),
        recommended_action=action,
        error_log=case.traceback,
        relevant_specs=extract_relevant_specs(rationale),
        raw_response=raw_response,
    )


def _classify_mutant_batch_once(
    *,
    batch_index: int,
    batch: list[MutantCase],
    workspace: Path | None,
    image: str,
    spec_dir: Path,
    tests_dir: Path,
    mutants_dir: Path,
    ground_truth: Path | None,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    runner: Callable[[str], dict[str, Any]] | None,
) -> tuple[list[MutantAttribution], ClassifierBatchUsage | None]:
    prompt = build_mutant_attribution_prompt(mutant_count=len(batch))
    if runner is not None:
        result = runner(prompt)
        raw_response = json.dumps(result)
        return _attributions_from_batch_result(batch, result, raw_response=raw_response), None
    if workspace is None:
        raise ValueError("workspace is required when runner is not provided")
    stage_mutant_classifier_workspace(
        workspace=workspace,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        mutants_dir=mutants_dir,
        cases=batch,
        ground_truth=ground_truth,
    )
    log.info("Classifying mutant batch %s (%s cases)", batch_index, len(batch))
    result, raw_response, usage = run_codex_classifier(
        prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        codex_command=codex_command,
        timeout=timeout,
        cwd=workspace,
        image=image,
        result_key="mutants",
    )
    batch_usage = ClassifierBatchUsage(
        phase="mutant_classification",
        batch_index=batch_index,
        case_count=len(batch),
        usage=usage,
    )
    return _attributions_from_batch_result(batch, result, raw_response=raw_response), batch_usage


def stage_mutant_classifier_workspace(
    *,
    workspace: Path,
    spec_dir: Path,
    tests_dir: Path,
    mutants_dir: Path,
    cases: list[MutantCase],
    ground_truth: Path | None = None,
) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    shutil.copytree(spec_dir, workspace / "spec", symlinks=True)
    _copy_tests_for_classifier(tests_dir, workspace / "test")
    mutants_out = workspace / "mutants"
    mutants_out.mkdir()
    for case in cases:
        _copy_mutant_for_classifier(mutants_dir, case, mutants_out, ground_truth)
    (workspace / "mutant_cases.json").write_text(json.dumps([mutant_payload(case) for case in cases], indent=2))


def _copy_tests_for_classifier(tests_dir: Path, output: Path) -> None:
    shutil.copytree(tests_dir, output, symlinks=True)
    archive = output / "tests.tar.gz"
    if archive.is_file():
        extracted = output / "extracted"
        extracted.mkdir(exist_ok=True)
        with tarfile.open(archive) as tar:
            _safe_extractall(tar, extracted)


def _safe_extractall(tar: tarfile.TarFile, target: Path) -> None:
    target = target.resolve()
    for member in tar.getmembers():
        member_target = (target / member.name).resolve()
        if target != member_target and target not in member_target.parents:
            raise RuntimeError(f"Unsafe path in generated test archive: {member.name}")
    tar.extractall(target)


def _copy_mutant_for_classifier(
    mutants_dir: Path, case: MutantCase, output: Path, ground_truth: Path | None
) -> None:
    target = output / case.mutant_id
    if (mutants_dir / SOURCES_MANIFEST).is_file():
        # A sealed store keeps only the diff from the ground truth, so rebuild the
        # tree the classifier expects rather than degrading it to metadata.json.
        with materialize_mutant_sources(mutants_dir, case.mutant_id, ground_truth) as rebuilt:
            shutil.copytree(rebuilt, target, symlinks=True)
        (target / "metadata.json").write_text(json.dumps(mutant_payload(case), indent=2))
        return
    source = _mutant_source_path(mutants_dir, case)
    if source is not None and source.is_dir():
        shutil.copytree(source, target, symlinks=True)
        return
    target.mkdir()
    if source is not None and source.is_file():
        shutil.copy2(source, target / source.name)
    (target / "metadata.json").write_text(json.dumps(mutant_payload(case), indent=2))


def _mutant_source_path(mutants_dir: Path, case: MutantCase) -> Path | None:
    if case.payload:
        payload = mutants_dir / case.payload
        if payload.exists():
            return payload.parent if payload.is_file() else payload
    direct = mutants_dir / case.mutant_id
    if direct.exists():
        return direct
    repo_match = re.fullmatch(r"repo_[0-9]+", case.mutant_id)
    if repo_match and direct.exists():
        return direct
    return None


def run_codex_classifier(
    prompt: str,
    *,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    cwd: Path,
    image: str,
    result_key: str,
) -> tuple[dict[str, Any], str, dict[str, int]]:
    command = build_codex_shell_command(
        codex_command,
        prompt=prompt,
        model=model.removeprefix("codex/"),
        reasoning_effort=reasoning_effort,
        diagnostic_action="classify mutants",
    )
    result = run_codex_in_container(
        command,
        cwd=cwd,
        timeout=timeout,
        image=image,
        copy_back_files=[DEFAULT_CLASSIFIER_RESULT_PATH],
    )
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    raw = _last_agent_message(stdout) or stdout
    usage = _codex_usage_from_stdout(stdout)
    if result["returncode"] != 0:
        log.warning("Codex mutant classifier exited with status %s: %s", result["returncode"], stderr.strip())
        return (
            {
                "fault": "unknown",
                "subreason": "classifier_failed",
                "confidence": 0.0,
                "rationale": stderr.strip() or "Codex classifier exited non-zero.",
                "recommended_action": "manual_review",
            },
            raw,
            usage,
        )
    try:
        return _load_classifier_output_path(_parse_classifier_json(raw), cwd=cwd, key=result_key), raw, usage
    except ValueError as error:
        return (
            {
                "fault": "unknown",
                "subreason": "invalid_classifier_json",
                "confidence": 0.0,
                "rationale": str(error),
                "recommended_action": "manual_review",
            },
            raw,
            usage,
        )


def _attributions_from_batch_result(
    cases: list[MutantCase],
    result: dict[str, Any],
    *,
    raw_response: str,
) -> list[MutantAttribution]:
    items = result.get("mutants")
    if items is None and "fault" in result and len(cases) == 1:
        items = [result]
    if not isinstance(items, list):
        return [
            _attribution_from_result(
                case,
                _classifier_error(result, "Classifier did not return a mutants list."),
                raw_response=raw_response,
            )
            for case in cases
        ]

    keyed: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and "mutant_id" in item:
            keyed[str(item.get("mutant_id", ""))] = item

    attributions: list[MutantAttribution] = []
    for index, case in enumerate(cases):
        item: Any = items[index] if index < len(items) else None
        if not isinstance(item, dict) or (item.get("mutant_id") and item.get("mutant_id") != case.mutant_id):
            item = keyed.get(case.mutant_id)
        if not isinstance(item, dict):
            item = {
                "fault": "unknown",
                "subreason": "missing_batch_result",
                "confidence": 0.0,
                "rationale": "Classifier did not return an attribution for this mutant.",
                "recommended_action": "manual_review",
            }
        item = _validate_classifier_item(item, mutant=True)
        attributions.append(_attribution_from_result(case, item, raw_response=raw_response))
    return attributions


def _default_mutant_action(case: MutantCase, fault: MutantFault) -> str:
    if fault == "test":
        return "ignore"
    if fault in SPEC_FAULTS:
        return "polish_spec"
    return "manual_review"


def _rule_based_mutant_attribution(case: MutantCase) -> MutantAttribution:
    if case.status == "error":
        error = case.error_code or "unknown evaluation error"
        return _attribution_from_result(
            case,
            {
                "fault": "unknown",
                "subreason": "evaluation_error",
                "confidence": 1.0,
                "rationale": (
                    f"The mutant evaluation failed with {error}. Errored mutants carry the "
                    "evaluation_error subreason and are never sent for model review."
                ),
                "recommended_action": "manual_review",
            },
            raw_response="",
        )
    raise ValueError(f"No rule-based attribution for mutant status: {case.status}")


def _mutant_action_summary(attributions: list[MutantAttribution]) -> dict[str, int]:
    summary = {"polish_spec": 0}
    for attribution in attributions:
        if attribution.fault not in SPEC_FAULTS:
            continue
        summary["polish_spec"] += 1
    return summary


def _attribution_from_result(case: MutantCase, result: dict[str, Any], *, raw_response: str) -> MutantAttribution:
    raw_fault = normalize_spec_fault(result.get("fault"), result.get("subreason", ""))
    if raw_fault == "tests":
        raw_fault = "test"
    fault = raw_fault if raw_fault in {"test", *SPEC_FAULTS, "unknown"} else "unknown"
    action = result.get("recommended_action")
    if action not in {"ignore", "polish_spec", "manual_review"}:
        action = _default_mutant_action(case, fault)
    rationale = str(result.get("rationale", ""))
    mentioned_specs = extract_relevant_specs(rationale)
    most_relevant_spec = case.target_spec or (mentioned_specs[0] if mentioned_specs else "")
    other_relevant_specs = [spec for spec in mentioned_specs if spec != most_relevant_spec]
    return MutantAttribution(
        instance_id=case.instance_id,
        mutant_id=case.mutant_id,
        status=case.status,
        fault=fault,
        subreason=str(result.get("subreason", "")),
        confidence=float(result.get("confidence", 0.0) or 0.0),
        rationale=rationale,
        recommended_action=action,
        most_relevant_spec=most_relevant_spec,
        other_relevant_specs=other_relevant_specs,
        raw_response=raw_response,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify ProgramBench generated-test failures and killed/survived/error mutants.")
    parser.add_argument("source", type=Path, help="Test-eval JSON file or mutation-eval output directory")
    parser.add_argument("--task", default="", help="Task instance id; required if SOURCE contains multiple eval files")
    parser.add_argument("--spec-dir", required=True, help="Specification directory")
    parser.add_argument("--tests-dir", required=True, help="Generated test suite directory")
    parser.add_argument(
        "--mutants-dir",
        required=True,
        help="Mutants directory, or hf://<repo_id>[@revision] to read a HuggingFace-hosted store from the shared cache",
    )
    parser.add_argument(
        "--ground-truth-dir",
        default="",
        help=(
            "Ground-truth implementation directory (conventionally ground_truth/implementation), or "
            "hf://<repo_id>[@revision] to download it. Sealed mutant sources are an overlay on this tree; "
            "defaults to the path recorded when the store was sealed."
        ),
    )
    parser.add_argument("-o", "--output", default="", help="Output JSON path. Defaults beside SOURCE.")
    parser.add_argument("--model", default="codex/gpt-5.6-luna", help="Codex model used for attribution")
    parser.add_argument("--reasoning-effort", default="high", help="Codex reasoning effort")
    parser.add_argument(
        "--codex-command",
        default=DEFAULT_CODEX_COMMAND,
        help="Codex command prefix. The attribution prompt is appended as the final argument.",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Classifier timeout in seconds")
    parser.add_argument("--limit", type=int, default=0, help="Classify at most this many cases; 0 means all")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Cases per batch; 0 means all")
    parser.add_argument("--batch-workers", type=int, default=DEFAULT_BATCH_WORKERS, help="Parallel classifier workers")
    parser.add_argument("--skip-test-failures", action="store_true", help="Do not classify generated-test failures (the validity rate direction)")
    parser.add_argument("--skip-survived-mutants", action="store_true", help="Do not classify survived mutants (the mutation score direction)")
    parser.add_argument("--dry-run", action="store_true", help="Write classifier prompts without calling Codex")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite an existing attribution report")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    eval_json = resolve_test_eval_json(args.source, task=args.task)
    task = infer_task_from_eval_json(eval_json)
    output = Path(args.output) if args.output else default_output_path(args.source, eval_json)
    report = classify_mutants(
        eval_json=eval_json,
        spec_dir=Path(args.spec_dir),
        tests_dir=Path(args.tests_dir),
        mutants_dir=resolve_mutants_dir(args.mutants_dir, task, with_sources=True),
        output=output,
        ground_truth=(
            resolve_implementation_dir(args.ground_truth_dir, task) if args.ground_truth_dir else None
        ),
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        codex_command=args.codex_command,
        timeout=args.timeout,
        limit=args.limit,
        batch_size=args.batch_size,
        batch_workers=args.batch_workers,
        dry_run=args.dry_run,
        force=args.force,
        classify_test_failures=not args.skip_test_failures,
        classify_survived_mutants=not args.skip_survived_mutants,
    )
    print(f"Wrote mutant attribution report: {output}")
    print("Generated-test failure attribution summary: " + ", ".join(f"{k}={v}" for k, v in sorted(report.test_failure_summary.items())))
    print("Mutant attribution summary: " + ", ".join(f"{k}={v}" for k, v in sorted(report.summary.items())))
    print("Mutant action summary: " + ", ".join(f"{k}={v}" for k, v in sorted(report.mutant_action_summary.items())))
    check_attribution_usable(report.test_failures, "Generated-test failure attribution")
    check_attribution_usable(report.mutants, "Mutant attribution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
