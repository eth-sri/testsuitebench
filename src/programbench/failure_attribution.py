# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Classify candidate failures against the current specification."""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import tempfile
from functools import partial
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from programbench.classifier_retry import (
    CLASSIFIER_ERROR_SUBREASONS,
    ClassifierBatchUsage,
    retry_classifier_batch,
)
from programbench.codex import build_codex_shell_command, run_codex_in_container
from programbench.constants import agent_network_args, cleanroom_codex_image, eval_network_note
from programbench.spec_improvement import DEFAULT_CODEX_COMMAND
log = logging.getLogger(__name__)

SpecFault = Literal["spec_underspecification", "spec_contradiction"]
FailureFault = Literal["error", "error_infra", "executable", "spec_underspecification", "spec_contradiction", "unknown"]
SPEC_FAULTS = ("spec_underspecification", "spec_contradiction")

MAX_CLASSIFIER_ERROR_FRACTION = 0.2
MAX_CLASSIFIER_ERRORS = 10


def attribution_is_unusable(records: list[Any]) -> bool:
    """Whether so many records broke inside the classifier that the report must be recomputed."""
    broken = sum(record.subreason in CLASSIFIER_ERROR_SUBREASONS for record in records)
    return broken >= MAX_CLASSIFIER_ERRORS and broken / len(records) > MAX_CLASSIFIER_ERROR_FRACTION


def check_attribution_usable(records: list[Any], label: str) -> None:
    """Records carrying these subreasons mean the classifier broke, not that the run is unexplainable.

    They are indistinguishable from genuine `unknown` verdicts downstream, so a polish step would
    silently drop the requirements they cover instead of failing. A few are normal transient retries;
    a large share means the classifier was down and the whole batch is worthless.
    """
    broken = [record for record in records if record.subreason in CLASSIFIER_ERROR_SUBREASONS]
    if not broken:
        return
    detail = (
        f"{label}: {len(broken)}/{len(records)} records failed inside the classifier "
        f"({', '.join(sorted({record.subreason for record in broken}))})"
    )
    if attribution_is_unusable(records):
        raise RuntimeError(f"{detail}; rerun this stage instead of polishing against an incomplete attribution")
    log.warning("%s; continuing because the batch is still mostly classified", detail)


DEFAULT_BATCH_SIZE = 50
DEFAULT_BATCH_WORKERS = 4
DEFAULT_BRANCH_WORKERS = 4
DEFAULT_BRANCH_SIZE = 200
DEFAULT_TIMEOUT = 1800
# A branch job reads every record agentically, so its budget scales with DEFAULT_BRANCH_SIZE.
DEFAULT_BRANCH_TIMEOUT = 7200
DEFAULT_CLASSIFIER_RESULT_PATH = "classifier_result.json"
WORKSPACE = "/workspace"
FAILED_STATUSES = {"failure", "error", "system_error", "not_run"}
SPEC_REFERENCE_PATTERN = re.compile(r"\bSpec [0-9]+\b")
TRACEBACK_LOCATION_PATTERN = re.compile(r"[\w./-]+\.py:[0-9]+")
MIN_VERIFIABLE_QUOTE = 12
_QUOTE_TRANSLATION = str.maketrans(
    {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u00a0": " "}
    | dict.fromkeys(map(ord, "`*_"), None)
)


def root_cause_key(traceback: str) -> str:
    """Failures aborting at the same source locations share one root cause.

    A broken session fixture reaches every dependent test through identical frames, and a
    parametrized case asserts at one line. Classifying each symptom separately spends a
    verdict per test and lets a single judgement be counted as many independent spec faults.
    """
    return "\n".join(dict.fromkeys(TRACEBACK_LOCATION_PATTERN.findall(traceback)))


def group_by_root_cause(cases: list[Any]) -> list[list[Any]]:
    groups: dict[str, list[Any]] = {}
    for case in cases:
        groups.setdefault(root_cause_key(case.traceback) or case.name, []).append(case)
    return list(groups.values())


def spec_text(spec_dir: Path) -> str:
    return " ".join(" ".join(path.read_text().split()) for path in sorted(spec_dir.rglob("*.md")))


def spec_quote_is_verifiable(quote: str, spec: str) -> bool:
    """Whether a claimed specification sentence really occurs in the specification.

    A fabricated quote is the one contradiction failure mode needing no judgement to catch: the
    verdict names a specification sentence, so the sentence is either in the spec or it is not.
    It is asked for in its own field rather than mined out of the rationale, because a rationale
    legitimately also quotes observed reference output, which is not in the spec.
    """
    normalized = normalize_quote_text(quote)
    return len(normalized) >= MIN_VERIFIABLE_QUOTE and normalized in normalize_quote_text(spec)


def normalize_quote_text(text: str) -> str:
    """Canonical form for comparing a classifier's quote with the specification.

    Classifiers drop markdown emphasis and code ticks, straighten curly quotes and dashes, and
    reflow whitespace when they copy a sentence, none of which changes what the sentence says.
    """
    text = text.translate(_QUOTE_TRANSLATION)
    return " ".join(text.split()).casefold()


def record_evidence_is_verifiable(quote: str, traceback: str, min_length: int = MIN_VERIFIABLE_QUOTE) -> bool:
    """Whether text the judge says it copied from a failure record really occurs in that record.

    A verdict pasted from a neighbouring record is the batch failure mode this catches: its
    `failing_assertion` and `candidate_observed` quote a different traceback. Tracebacks
    carry escaped reprs (`\\n`, quotes), which the judge may copy either raw or unescaped,
    so those characters are ignored on both sides.

    `min_length` guards against a quote so short that it is contained by coincidence; callers
    quoting an observation that is legitimately tiny, such as empty output, lower it.
    """
    normalized = normalize_evidence_text(quote)
    return len(normalized) >= min_length and normalized in normalize_evidence_text(traceback)


def normalize_evidence_text(text: str) -> str:
    return "".join(normalize_quote_text(text).split()).translate(dict.fromkeys(map(ord, "\\'\""), None))


def reject_unverified_attributions(
    attributions: dict[int, FailureAttribution], failures: list[FailureCase], spec: str
) -> list[int]:
    """Demote verdicts whose quoted evidence is not in the record or the specification.

    Returns the demoted indices so that exactly those records can be judged once more.
    """
    demoted = []
    for index, attribution in attributions.items():
        if attribution.fault in {"error", "error_infra", "unknown"}:
            continue
        traceback = failures[index].traceback
        # `''` and `b''` are how a judge quotes output the candidate never produced, which is the
        # commonest executable fault; they normalize away to nothing and cannot clear a length floor.
        if not (
            record_evidence_is_verifiable(attribution.failing_assertion, traceback)
            and attribution.candidate_observed.strip()
            and record_evidence_is_verifiable(attribution.candidate_observed, traceback, min_length=0)
        ):
            subreason = "unverified_record_evidence"
        elif attribution.fault == "spec_contradiction" and not spec_quote_is_verifiable(attribution.spec_quote, spec):
            subreason = "unverified_spec_quote"
        else:
            continue
        attributions[index] = attribution.model_copy(
            update={"fault": "unknown", "subreason": subreason, "recommended_action": "manual_review"}
        )
        demoted.append(index)
    return demoted


def extract_relevant_specs(text: str) -> list[str]:
    """Extract ordered, unique numbered specification references from rationale text."""
    return list(dict.fromkeys(SPEC_REFERENCE_PATTERN.findall(text)))


def merge_relevant_specs(existing: list[str], rationale: str) -> list[str]:
    """Preserve seeded links and append specification references justified by a classifier."""
    return list(dict.fromkeys([*existing, *extract_relevant_specs(rationale)]))


def normalize_spec_fault(fault: Any, subreason: Any = "") -> Any:
    """Map the legacy combined spec fault to the closest split fault."""
    if fault != "spec":
        return fault
    if str(subreason) == "spec_contradiction":
        return "spec_contradiction"
    return "spec_underspecification"


def is_spec_fault(fault: Any) -> bool:
    """Return whether a current or legacy fault denotes a specification defect."""
    return fault == "spec" or fault in SPEC_FAULTS


def normalize_spec_summary(summary: Any) -> Any:
    """Normalize a legacy combined spec count without discarding split counts."""
    if not isinstance(summary, dict) or "spec" not in summary:
        return summary
    normalized = dict(summary)
    legacy_count = normalized.pop("spec")
    normalized["spec_underspecification"] = normalized.get("spec_underspecification", 0) + legacy_count
    normalized.setdefault("spec_contradiction", 0)
    return normalized


class FailureCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    name: str
    branch: str = ""
    status: str
    message: str = ""
    traceback: str = ""
    error_code: str = ""
    error_details: str = ""
    relevant_specs: list[str] = Field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.branch}/{self.name}" if self.branch else self.name

class FailureAttribution(BaseModel):
    model_config = ConfigDict(extra="ignore")

    instance_id: str
    name: str
    branch: str = ""
    status: str
    fault: FailureFault
    subreason: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    rationale: str = ""
    recommended_action: str = ""
    failing_assertion: str = ""
    candidate_observed: str = ""
    spec_quote: str = ""
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

class ClassifierUsageReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batches: list[ClassifierBatchUsage] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)

class FailureAttributionReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eval_json: str
    spec_dir: str
    output: str
    test_spec_links: str = ""
    dry_run: bool = False
    summary: dict[str, int]
    classifier_usage: ClassifierUsageReport = Field(default_factory=ClassifierUsageReport)
    failures: list[FailureAttribution]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_summary(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = {**value, "summary": normalize_spec_summary(value.get("summary", {}))}
        return value

def infer_task_from_eval_json(eval_json: Path) -> str:
    name = eval_json.name
    for suffix in (".eval.json", ".test_eval.json"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return eval_json.stem

def resolve_eval_json(source: Path, *, task: str = "") -> Path:
    if source.is_file():
        return source
    if not source.is_dir():
        raise FileNotFoundError(f"Evaluation source does not exist: {source}")

    if task:
        candidates = [
            source / "executable" / task / f"{task}.eval.json",
            source / task / f"{task}.eval.json",
            source / f"{task}.eval.json",
            source / task / f"{task}.test_eval.json",
            source / f"{task}.test_eval.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate

    matches = sorted(source.glob("**/*.eval.json"))
    if not matches:
        matches = sorted(source.glob("**/*.test_eval.json"))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"No .eval.json or .test_eval.json found under {source}")
    raise RuntimeError(f"Multiple eval files found under {source}; pass --task or the eval JSON path directly")

def task_scoped_dir(path: Path, *, task: str) -> Path:
    if task and (path / task).is_dir():
        return path / task
    return path

def infer_spec_dir(source: Path, *, task: str) -> Path:
    if source.is_file():
        raise RuntimeError("--spec-dir is required when SOURCE is an eval JSON file")
    candidates = [
        source / "spec" / task,
        source / "spec",
        source / "spec-root" / task,
        source / "specification" / task,
        source / "specification",
        source / "cleanroom" / task,
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Could not infer spec directory for {task} under {source}; pass --spec-dir")

def default_output_path(source: Path, eval_json: Path) -> Path:
    task = infer_task_from_eval_json(eval_json)
    if source.is_dir():
        return source / "log" / task / "failure_attribution.json"
    return eval_json.with_name(f"{task}.failure_attribution.json")

def load_failure_cases(eval_json: Path, *, binary_id: str = "") -> list[FailureCase]:
    data = json.loads(eval_json.read_text())
    instance_id = infer_task_from_eval_json(eval_json)
    if "test_results" in data:
        branch_errors = data.get("test_branch_errors", {})
        if not isinstance(branch_errors, dict):
            branch_errors = {}
        return [
            _case_from_test_result(
                instance_id,
                item,
                evaluation_errors=branch_errors.get(str(item.get("branch", "")), []),
            )
            for item in data.get("test_results", [])
            if item.get("status") in FAILED_STATUSES
        ]

    failures: list[FailureCase] = []
    for binary in data.get("binary_results", []):
        selected = binary_id and binary.get("binary_id") != binary_id
        default_ground_truth = not binary_id and binary.get("role") != "ground_truth"
        if selected or default_ground_truth:
            continue
        for item in binary.get("test_results", []):
            if item.get("status") in FAILED_STATUSES:
                failures.append(
                    _case_from_test_result(
                        instance_id,
                        item,
                        evaluation_errors=[
                            {
                                "error_code": binary.get("error_code"),
                                "error_details": binary.get("error_details"),
                            }
                        ],
                    )
                )
    return failures

def _test_function_name(name: str) -> str:
    """Collapse parametrized/subtest names to the function stored in link manifests."""
    return re.split(r"\[| \(", name, maxsplit=1)[0].partition("@")[0]


def load_relevant_spec_links(path: Path | None) -> dict[tuple[str, str], list[str]]:
    """Load test-function to specification-section links from a link manifest."""
    if path is None:
        return {}
    if not path.is_file():
        raise FileNotFoundError(f"Test/spec link manifest does not exist: {path}")
    data = json.loads(path.read_text())
    links: dict[tuple[str, str], list[str]] = {}
    for item in data.get("test_functions", []):
        if not isinstance(item, dict):
            continue
        branch = str(item.get("branch", ""))
        name = _test_function_name(str(item.get("name", "")))
        targets = list(dict.fromkeys(
            str(value) for value in item.get("target_specs", []) if str(value)
        ))
        links[(branch, name)] = targets
    return links


def attach_relevant_specs(
    failures: list[FailureCase], links: dict[tuple[str, str], list[str]]
) -> None:
    for failure in failures:
        key = (failure.branch, _test_function_name(failure.name))
        failure.relevant_specs = list(links.get(key, []))


def _case_from_test_result(
    instance_id: str,
    item: dict[str, Any],
    *,
    evaluation_errors: Any = None,
) -> FailureCase:
    extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
    errors = evaluation_errors if isinstance(evaluation_errors, list) else []
    errors = [error for error in errors if isinstance(error, dict)]
    error_codes = [str(extra.get("error_code", ""))]
    error_codes.extend(str(error.get("error_code", "")) for error in errors)
    error_details = [str(extra.get("error_details", ""))]
    error_details.extend(str(error.get("error_details", "")) for error in errors)
    return FailureCase(
        instance_id=instance_id,
        name=str(item.get("name", "")),
        branch=str(item.get("branch", "")),
        status=str(item.get("status", "")),
        message=str(extra.get("message", "")),
        traceback=str(extra.get("text", "")),
        error_code=",".join(dict.fromkeys(value for value in error_codes if value and value != "None")),
        error_details="\n".join(dict.fromkeys(value for value in error_details if value and value != "None")),
    )


# Signatures of a Python package installer that could not reach an index. Every
# one of these is emitted by pip itself, so none can be output of the executable
# under test -- which matters because several tasks (dog, curlie, muffet, pingu,
# bore) legitimately produce DNS and connection diagnostics as tested behavior.
# Generic wording like "Connection refused" or "name resolution" is deliberately
# absent for that reason: a false `error` hides a real defect, so this list is
# tuned for precision and the classifier's own `error` value covers the rest.
INSTALLER_NETWORK_SIGNATURES = (
    "No matching distribution found for",
    "Could not find a version that satisfies the requirement",
    "pip._vendor.urllib3",
    "WARNING: Retrying (Retry(total=",
    "Failed to establish a new connection",
    "ProxyError",
)


def _is_installer_network_failure(failure: FailureCase) -> bool:
    """Whether a reference suite failed only because pip could not reach an index.

    Networking is disabled in the sandbox, so a suite whose run.sh installs a
    package that is not preinstalled aborts before writing results.xml and every
    test in its branch arrives here. That is infrastructure, not evidence about
    the specification or the candidate, and it is recognisable without spending a
    classifier call on it.
    """
    haystack = f"{failure.message}\n{failure.traceback}\n{failure.error_details}"
    return any(signature in haystack for signature in INSTALLER_NETWORK_SIGNATURES)


def _is_evaluation_error(failure: FailureCase) -> bool:
    """Return whether evaluation failed before producing a behavioral result."""
    # A completed assertion failure remains behavioral even if its branch later
    # reports an infrastructure error (for example, a timeout after partial results).
    return failure.status in {"error", "system_error", "not_run"} or _is_installer_network_failure(failure)


def _evaluation_error_attribution(failure: FailureCase) -> FailureAttribution:
    if _is_installer_network_failure(failure) and not failure.error_code:
        return FailureAttribution(
            instance_id=failure.instance_id,
            name=failure.name,
            branch=failure.branch,
            status=failure.status,
            fault="error_infra",
            subreason="offline_package_install",
            confidence=1.0,
            rationale=(
                "The reference suite's run.sh installed a package that is not preinstalled in the "
                "task image, and the sandbox has no network. pip exited non-zero, so the suite "
                "produced no behavioral result for this test."
            ),
            recommended_action="fix_evaluation",
            error_log=failure.traceback,
            relevant_specs=failure.relevant_specs,
        )
    subreason = failure.error_code or f"evaluation_{failure.status}"
    rationale = failure.error_details or failure.message or failure.traceback
    if not rationale:
        rationale = f"The test has evaluation status {failure.status!r} and no behavioral result."
    return FailureAttribution(
        instance_id=failure.instance_id,
        name=failure.name,
        branch=failure.branch,
        status=failure.status,
        fault="error_infra",
        subreason=subreason,
        confidence=1.0,
        rationale=rationale,
        recommended_action="fix_evaluation",
        error_log=failure.traceback,
        relevant_specs=failure.relevant_specs,
    )

def candidate_failure_payload(failure: FailureCase) -> dict[str, Any]:
    """Return only candidate-evaluation evidence for the fixed-suite iteration path."""
    return {
        "instance_id": failure.instance_id,
        "name": failure.name,
        "branch": failure.branch,
        "status": failure.status,
        "message": failure.message,
        "traceback": failure.traceback,
        "relevant_specs": failure.relevant_specs,
    }

def build_candidate_attribution_prompt(*, failure_count: int, branch: str = "") -> str:
    network_note = eval_network_note()
    return f"""\
You are attributing candidate-implementation failures for one ProgramBench task.

## Workspace

- `/workspace/spec/`: the current specification for the task.
- `/workspace/failures.json`: tests of the fixed reference suite that the **candidate** implementation failed, one record each.
    Every record is a candidate failure: the same suite passes on the **reference** implementation.
- `/workspace/reference-tests/`: the fixed reference suite itself, read-only: test sources, conftest fixtures and
    golden files. Read the failing test there when the traceback is truncated or the expectation lives in a fixture.
    Traceback paths are the eval container's: a file quoted under `/workspace/eval/` is staged here at `/workspace/reference-tests/<branch>/eval/`.
- `/workspace/executable`: the **reference** implementation. Run it to check what the real behavior is.

Each record carries the test `name`, `branch`, `status`, the assertion `message`, the pytest
`traceback`, and `relevant_specs` (the specification sections the test was linked to, when known).
Any output quoted inside a traceback is output of the candidate implementation, which the test
invoked as `/workspace/executable`. The fixed suite passes on the reference implementation, so what
a test asserts is the real behavior, and a record always shows the candidate deviating from it.

## Task

There are {failure_count} failures in `failures.json`, all from test branch `{branch or "(unscoped)"}`.
For each failure, determine whether the specification or candidate executable is at fault.

## Classification Criteria

- `executable`: the specification legitimately defines the behavior and the candidate implementation is wrong.
    Recommended action: `ignore`.
- `spec_underspecification`: the specification is missing or ambiguous with respect to the failed behavior.
    Recommended action: `polish_spec`.
- `spec_contradiction`: the specification is misleading or contradictory with respect to the failed behavior.
    Recommended action: `polish_spec`.
- `error`: the failure is an artifact of the environment rather than a judgement about the candidate.
    Recommended action: `ignore`.
- `unknown`: the failure record and specification do not provide enough information.
    Recommended action: `manual_review`.

Choose `spec_underspecification` or `spec_contradiction` only when the failure is clearly due to the specification.
`spec_contradiction` requires a conflict you can show, not one you infer: you must be able to quote the specification sentence that states something different from what the test asserts.
If the specification is merely silent, vague, or less precise than the test expectation, that is `spec_underspecification`.
A test expectation the specification simply fails to mention is never a contradiction.
As long as the most natural interpretation should lead to the tested behavior, it is not spec's fault, but it is the `executable`'s fault, even if the expected behavior is not stated explicitly.

## Rules

- Decide from the record, the specification, and what `/workspace/executable` does when you run it.
  If they leave unclear what the test expected, use `unknown` rather than guessing.
- Judge every record from its own traceback. Tests in one file routinely fail for different reasons
  (one rejects an option, the next refuses to overwrite), so never carry a verdict from one record to
  the next. For each record copy the failing `assert` line into `failing_assertion` and the candidate
  output that made it fail into `candidate_observed`, both verbatim from that record's traceback. A
  verdict whose copied evidence is not found in its own record is rejected and the record is re-judged.
- In a pytest diff, `-` lines are the assert's right operand and `+` lines its left one. A
  `CompletedProcess(...)` repr is the candidate's output. These rules can be different if the test is
  written in other frameworks. Read the whole failing assertion, not only its first clause, and check
  which flag or argument the test actually passed.
- Before emitting `spec_contradiction`, reconstruct the failing invocation from the traceback, run it
  on `/workspace/executable`, and state in the rationale the quoted specification claim, the test
  expectation, and the reference output that confirms the test. Copy the sentence from
  `/workspace/spec/` as it appears. If no such sentence can be quoted, or the invocation cannot be
  run here (it needs the network, a fixture server, or files you cannot reconstruct), then
  the fault is not a contradiction: use `spec_underspecification` when the specification is merely
  silent or vague about the behavior, and `executable` otherwise. Put that sentence in `spec_quote`;
  a contradiction whose `spec_quote` is not a literal substring of the specification is rejected and
  the verdict is discarded, so never paraphrase, trim or reflow it.
- {network_note}
- Preserve each failure's `name` and `branch` exactly so the result can be matched to its input.

## Output

Write `classifier_result.json` containing exactly one JSON object with this shape:

{{
  "failures": [
    {{
      "name": "same failure name from failures.json",
      "branch": "same branch from failures.json",
      "fault": "executable|spec_underspecification|spec_contradiction|error|unknown",
      "subreason": "short_snake_case_reason providing detail beyond fault",
      "confidence": 0.0,
      "rationale": "a few sentences that explicitly name every relevant section as Spec N and cover (i) which specification number provides relevant information, (ii) what the test evaluates in that regard, (iii) why the executable failed, and (iv) why it is classified as executable/spec_underspecification/spec_contradiction/error/unknown",
      "failing_assertion": "the failing assert line, copied verbatim from this record's traceback",
      "candidate_observed": "the candidate output or status that made it fail, copied verbatim from this record's traceback",
      "spec_quote": "for spec_contradiction only: the conflicting sentence copied verbatim from /workspace/spec/, otherwise empty",
      "recommended_action": "ignore|polish_spec|manual_review"
    }}
  ]
}}

## Checkpointing

Persist classifications incrementally to `classifier_result.json` in the workspace.
After each compact group, atomically rewrite that valid JSON object with every completed entry so far.
If time or output budget runs out, leave as many completed entries as possible.

## Final Response

Do not return failures inline. When finished, return only:
{{"output_path": "classifier_result.json"}}
Do not add markdown or other text. The checkpoint file is authoritative.
"""

def classify_failures(
    *,
    eval_json: Path,
    spec_dir: Path,
    output: Path,
    test_spec_links: Path | None = None,
    model: str = "",
    reasoning_effort: str = "",
    codex_command: str = DEFAULT_CODEX_COMMAND,
    timeout: int = DEFAULT_BRANCH_TIMEOUT,
    limit: int = 0,
    batch_size: int = DEFAULT_BRANCH_SIZE,
    branch_workers: int = DEFAULT_BRANCH_WORKERS,
    binary_id: str = "",
    reference_tests_dir: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    runner: Callable[[str], dict[str, Any]] | None = None,
) -> FailureAttributionReport:
    if output.exists() and not force:
        cached = FailureAttributionReport.model_validate_json(output.read_text())
        if not attribution_is_unusable(cached.failures):
            return cached
        log.warning("Recomputing the unusable cached attribution report: %s", output)

    task = infer_task_from_eval_json(eval_json)
    spec_dir = task_scoped_dir(spec_dir, task=task)
    failures = load_failure_cases(eval_json, binary_id=binary_id)
    attach_relevant_specs(failures, load_relevant_spec_links(test_spec_links))
    if limit > 0:
        failures = failures[:limit]
    if branch_workers < 1:
        raise ValueError("branch_workers must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    classified_attributions: dict[int, FailureAttribution] = {
        index: _evaluation_error_attribution(failure)
        for index, failure in enumerate(failures)
        if _is_evaluation_error(failure)
    }
    classifiable_failures = [
        (index, failure)
        for index, failure in enumerate(failures)
        if index not in classified_attributions
    ]
    branch_jobs = _failure_branches(classifiable_failures, batch_size=batch_size)
    run_jobs = partial(
        _run_branch_jobs,
        artifacts_root=output.with_suffix(""),
        spec_dir=spec_dir,
        reference_tests_dir=reference_tests_dir,
        image=cleanroom_codex_image(task),
        model=model,
        reasoning_effort=reasoning_effort,
        codex_command=codex_command,
        timeout=timeout,
        branch_workers=branch_workers,
        runner=runner,
    )

    if dry_run:
        prompt_dir = output.with_suffix("")
        prompt_dir.mkdir(parents=True, exist_ok=True)
        for branch_index, (branch, branch_failures) in enumerate(branch_jobs, start=1):
            branch_dir = prompt_dir / f"branch_{branch_index:04d}"
            branch_dir.mkdir(parents=True, exist_ok=True)
            prompt_path = branch_dir / "classify_failures.prompt.md"
            failures_path = branch_dir / "failures.json"
            prompt_path.write_text(
                build_candidate_attribution_prompt(failure_count=len(branch_failures), branch=branch)
            )
            failures_path.write_text(
                json.dumps([candidate_failure_payload(failure) for _, failure in branch_failures], indent=2)
            )
            for failure_index, failure in branch_failures:
                classified_attributions[failure_index] = _attribution_from_result(
                    failure,
                    {
                        "fault": "unknown",
                        "subreason": "dry_run",
                        "confidence": 0.0,
                        "rationale": f"Prompt written to {prompt_path}; failures written to {failures_path}",
                        "recommended_action": "manual_review",
                    },
                    raw_response="",
                )
        usage_batches: list[ClassifierBatchUsage] = []
    else:
        judged, usage_batches = run_jobs(branch_jobs)
        classified_attributions.update(judged)
        spec = spec_text(spec_dir)
        demoted = reject_unverified_attributions(classified_attributions, failures, spec)
        if demoted:
            log.info("Re-judging %s record(s) whose quoted evidence was not found in the record", len(demoted))
            rejudged, retry_usage = run_jobs(
                _failure_branches([(index, failures[index]) for index in demoted], batch_size=batch_size),
                artifacts_root=output.with_suffix("") / "rejudge",
            )
            usage_batches.extend(retry_usage)
            reject_unverified_attributions(rejudged, failures, spec)
            classified_attributions.update({index: attribution for index, attribution in rejudged.items() if attribution.fault != "unknown"})
            still_unverified = sum(rejudged[index].fault == "unknown" for index in demoted)
            if still_unverified:
                log.warning("%s record(s) remain unknown: the judge could not quote their own traceback or the spec", still_unverified)

    attributions = [classified_attributions[index] for index in range(len(failures))]
    summary = {fault: 0 for fault in ("error", "error_infra", "executable", *SPEC_FAULTS, "unknown")}
    for attribution in attributions:
        summary[attribution.fault] += 1

    report = FailureAttributionReport(
        eval_json=str(eval_json),
        spec_dir=str(spec_dir),
        test_spec_links=str(test_spec_links or ""),
        output=str(output),
        dry_run=dry_run,
        summary=summary,
        classifier_usage=_classifier_usage_report(usage_batches),
        failures=attributions,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2))
    return report


def _codex_usage_from_stdout(stdout: str) -> dict[str, int]:
    records: list[dict[str, int]] = []
    seen: set[tuple[tuple[str, int], ...]] = set()

    def normalize(raw: dict[str, Any]) -> dict[str, int]:
        usage = {key: value for key, value in raw.items() if isinstance(value, int) and not isinstance(value, bool)}
        input_tokens = usage.get("input_tokens", 0)
        cached_input_tokens = usage.get("cached_input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        usage.setdefault("total_tokens", input_tokens + output_tokens)
        usage.setdefault("uncached_input_tokens", max(0, input_tokens - cached_input_tokens))
        usage.setdefault("uncached_input_plus_output_tokens", usage["uncached_input_tokens"] + output_tokens)
        return usage

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if obj.get("type") == "turn.completed" and isinstance(obj.get("usage"), dict):
                usage = normalize(obj["usage"])
                key = tuple(sorted(usage.items()))
                if key not in seen:
                    seen.add(key)
                    records.append(usage)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            walk(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    if not records:
        try:
            walk(json.loads(stdout))
        except json.JSONDecodeError:
            pass
    return _sum_usage(records)

def _sum_usage(usages: list[dict[str, int]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for usage in usages:
        for key, value in usage.items():
            totals[key] = totals.get(key, 0) + value
    return totals

def _classifier_usage_report(batches: list[ClassifierBatchUsage]) -> ClassifierUsageReport:
    return ClassifierUsageReport(batches=batches, totals=_sum_usage([batch.usage for batch in batches]))

def _failure_batches(failures: list[Any], batch_size: int) -> list[list[Any]]:
    """Split generic attribution cases for the mutant-attribution batch workflow.

    Normal failure attribution intentionally uses :func:`_failure_branches` instead.
    Mutant attribution continues to batch heterogeneous generated-test and mutant cases.
    """
    if not failures:
        return []
    if batch_size <= 0:
        return [failures]
    return [failures[index : index + batch_size] for index in range(0, len(failures), batch_size)]

def _failure_branches(
    failures: list[FailureCase] | list[tuple[int, FailureCase]],
    *,
    batch_size: int = DEFAULT_BRANCH_SIZE,
) -> list[tuple[str, list[tuple[int, FailureCase]]]]:
    """Group failures by branch and split each branch into bounded, ordered jobs."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    branches: dict[str, list[tuple[int, FailureCase]]] = {}
    for position, item in enumerate(failures):
        index, failure = item if isinstance(item, tuple) else (position, item)
        branches.setdefault(failure.branch, []).append((index, failure))
    return [
        (branch, branch_failures[start : start + batch_size])
        for branch, branch_failures in branches.items()
        for start in range(0, len(branch_failures), batch_size)
    ]

def _run_branch_jobs(
    branch_jobs: list[tuple[str, list[tuple[int, FailureCase]]]],
    *,
    artifacts_root: Path,
    spec_dir: Path,
    reference_tests_dir: Path | None,
    image: str,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    branch_workers: int,
    runner: Callable[[str], dict[str, Any]] | None,
) -> tuple[dict[int, FailureAttribution], list[ClassifierBatchUsage]]:
    """Judge every branch job concurrently and key the verdicts by failure index."""
    if not branch_jobs:
        return {}, []
    with tempfile.TemporaryDirectory(prefix="programbench-failure-attribution-") as workspace_root_name:
        workspace_root = Path(workspace_root_name)

        def classify(job: tuple[int, tuple[str, list[tuple[int, FailureCase]]]]) -> Any:
            branch_index, (branch, batch) = job
            return _classify_failure_branch(
                batch_index=branch_index,
                branch=branch,
                batch=batch,
                workspace=None if runner is not None else workspace_root / f"branch_{branch_index:04d}",
                artifacts_root=artifacts_root,
                spec_dir=spec_dir,
                reference_tests_dir=reference_tests_dir,
                model=model,
                reasoning_effort=reasoning_effort,
                codex_command=codex_command,
                image=image,
                timeout=timeout,
                runner=runner,
            )

        max_workers = min(branch_workers, len(branch_jobs))
        if max_workers > 1:
            log.info("Classifying %s failure branches with %s workers", len(branch_jobs), max_workers)
        attributions: dict[int, FailureAttribution] = {}
        usage_batches: list[ClassifierBatchUsage] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for batch, batch_attributions, batch_usage in executor.map(classify, enumerate(branch_jobs, start=1)):
                attributions.update({index: attribution for (index, _), attribution in zip(batch, batch_attributions)})
                if batch_usage is not None:
                    usage_batches.append(batch_usage)
    return attributions, usage_batches


def _classify_failure_branch_once(
    *,
    batch_index: int,
    branch: str,
    batch: list[tuple[int, FailureCase]],
    workspace: Path | None,
    artifacts_root: Path,
    spec_dir: Path,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    image: str,
    timeout: int,
    runner: Callable[[str], dict[str, Any]] | None,
    reference_tests_dir: Path | None = None,
) -> tuple[list[FailureAttribution], ClassifierBatchUsage | None]:
    failures = [failure for _, failure in batch]
    prompt = build_candidate_attribution_prompt(failure_count=len(failures), branch=branch)
    if runner is not None:
        result = runner(prompt)
        raw_response = json.dumps(result)
        return _attributions_from_batch_result(failures, result, raw_response=raw_response), None

    if workspace is None:
        raise ValueError("workspace is required when runner is not provided")
    stage_classifier_workspace(
        workspace=workspace, spec_dir=spec_dir, failures=failures, reference_tests_dir=reference_tests_dir
    )
    # The workspace is a temporary directory, so keep the prompt, its input and the
    # agent's verdict beside the report. Retries arrive under sibling workspace names.
    artifacts = artifacts_root / workspace.name
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "classify_failures.prompt.md").write_text(prompt)
    shutil.copy2(workspace / "failures.json", artifacts / "failures.json")
    log.info("Classifying failure branch %r (%s failures)", branch, len(failures))
    result, raw_response, usage = run_codex_classifier(
        prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        codex_command=codex_command,
        image=image,
        timeout=timeout,
        cwd=workspace,
        command_prefix=classifier_setup_prefix(),
    )
    if (workspace / DEFAULT_CLASSIFIER_RESULT_PATH).is_file():
        shutil.copy2(workspace / DEFAULT_CLASSIFIER_RESULT_PATH, artifacts / DEFAULT_CLASSIFIER_RESULT_PATH)
    batch_usage = ClassifierBatchUsage(
        phase="failure_classification",
        batch_index=batch_index,
        branch=branch,
        case_count=len(failures),
        usage=usage,
    )
    return _attributions_from_batch_result(failures, result, raw_response=raw_response), batch_usage


def _classify_failure_branch(
    **kwargs: Any,
) -> tuple[
    list[tuple[int, FailureCase]],
    list[FailureAttribution],
    ClassifierBatchUsage | None,
]:
    attributions, usage = retry_classifier_batch(_classify_failure_branch_once, **kwargs)
    return kwargs["batch"], attributions, usage


def stage_classifier_workspace(
    *,
    workspace: Path,
    spec_dir: Path,
    failures: list[FailureCase],
    reference_tests_dir: Path | None = None,
) -> None:
    shutil.copytree(spec_dir, workspace / "spec", symlinks=True)
    if reference_tests_dir is not None:
        shutil.copytree(
            reference_tests_dir,
            workspace / "reference-tests",
            symlinks=True,
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"),
        )
    (workspace / "failures.json").write_text(
        json.dumps([candidate_failure_payload(failure) for failure in failures], indent=2)
    )


def classifier_setup_prefix() -> str:
    """Leave the agent the staged specification, records, reference suite and reference binary.

    The image also ships a README and the task's git metadata, which can only be mistaken for
    evidence. The reference binary stays: a `spec_contradiction` verdict must be confirmed by
    running the failing invocation on it, which is the check the judge kept getting wrong from
    the record alone (diffs read backwards, wrong flag assumed, candidate bugs excused).
    """
    return (
        f"find {WORKSPACE} -mindepth 1 -maxdepth 1 ! -name spec ! -name failures.json "
        "! -name reference-tests ! -name executable -exec rm -rf {} +; "
    )


def run_codex_classifier(
    prompt: str,
    *,
    image: str,
    model: str,
    reasoning_effort: str,
    codex_command: str,
    timeout: int,
    cwd: Path,
    command_prefix: str = "",
) -> tuple[dict[str, Any], str, dict[str, int]]:
    command = command_prefix + build_codex_shell_command(
        codex_command,
        prompt=prompt,
        model=model.removeprefix("codex/"),
        reasoning_effort=reasoning_effort,
        diagnostic_action="classify failures",
    )
    result = run_codex_in_container(
        command,
        cwd=cwd,
        image=image,
        timeout=timeout,
        copy_back_files=[DEFAULT_CLASSIFIER_RESULT_PATH],
        network_args=agent_network_args(),
    )
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    raw = _last_agent_message(stdout) or stdout
    usage = _codex_usage_from_stdout(stdout)
    if result["returncode"] != 0:
        diagnostic = stderr.strip() or str(result.get("exception_info", "")).strip()
        log.warning("Codex classifier exited with status %s: %s", result["returncode"], diagnostic)
        checkpoint = _load_classifier_sidecar(cwd / DEFAULT_CLASSIFIER_RESULT_PATH)
        if checkpoint is not None:
            log.info(
                "Loaded classifier checkpoint after a non-zero exit: %s",
                DEFAULT_CLASSIFIER_RESULT_PATH,
            )
            return checkpoint, raw, usage
        return (
            {
                "fault": "unknown",
                "subreason": "classifier_failed",
                "confidence": 0.0,
                "rationale": diagnostic or "Codex classifier exited non-zero.",
                "recommended_action": "manual_review",
            },
            raw,
            usage,
        )
    try:
        return _load_classifier_output_path(_parse_classifier_json(raw), cwd=cwd), raw, usage
    except ValueError as error:
        checkpoint = _load_classifier_sidecar(cwd / DEFAULT_CLASSIFIER_RESULT_PATH)
        if checkpoint is not None:
            log.info("Loaded classifier checkpoint after an invalid final response: %s", DEFAULT_CLASSIFIER_RESULT_PATH)
            return checkpoint, raw, usage
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
    failures: list[FailureCase],
    result: dict[str, Any],
    *,
    raw_response: str,
) -> list[FailureAttribution]:
    items = result.get("failures")
    if items is None and "fault" in result and len(failures) == 1:
        items = [result]
    if not isinstance(items, list):
        return [
            _attribution_from_result(
                failure,
                {
                    "fault": "unknown",
                    "subreason": "invalid_batch_result",
                    "confidence": 0.0,
                    "rationale": "Classifier did not return a failures list.",
                    "recommended_action": "manual_review",
                },
                raw_response=raw_response,
            )
            for failure in failures
        ]

    keyed: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and "name" in item:
            keyed[(str(item.get("branch", "")), str(item.get("name", "")))] = item

    attributions: list[FailureAttribution] = []
    for index, failure in enumerate(failures):
        item: Any = items[index] if index < len(items) else None
        if not isinstance(item, dict) or (item.get("name") and item.get("name") != failure.name):
            item = keyed.get((failure.branch, failure.name))
        if not isinstance(item, dict):
            item = {
                "fault": "unknown",
                "subreason": "missing_batch_result",
                "confidence": 0.0,
                "rationale": "Classifier did not return an attribution for this failure.",
                "recommended_action": "manual_review",
            }
        attributions.append(_attribution_from_result(failure, item, raw_response=raw_response))
    return attributions


def _attribution_from_result(failure: FailureCase, result: dict[str, Any], *, raw_response: str) -> FailureAttribution:
    raw_fault = normalize_spec_fault(result.get("fault"), result.get("subreason", ""))
    if raw_fault == "implementation":
        raw_fault = "executable"
    if raw_fault == "test":
        result = {**result, "subreason": "invalid_test_fault", "recommended_action": "manual_review"}
        raw_fault = "unknown"
    fault = raw_fault if raw_fault in {"executable", *SPEC_FAULTS, "error", "unknown"} else "unknown"
    action = result.get("recommended_action")
    if action not in {"ignore", "polish_spec", "manual_review"}:
        action = {
            "executable": "ignore",
            "spec_underspecification": "polish_spec",
            "spec_contradiction": "polish_spec",
            "error": "ignore",
            "unknown": "manual_review",
        }[fault]
    rationale = str(result.get("rationale", ""))
    return FailureAttribution(
        instance_id=failure.instance_id,
        name=failure.name,
        branch=failure.branch,
        status=failure.status,
        fault=fault,
        subreason=str(result.get("subreason", "")),
        confidence=float(result.get("confidence", 0.0) or 0.0),
        rationale=rationale,
        recommended_action=action,
        failing_assertion=str(result.get("failing_assertion", "")),
        candidate_observed=str(result.get("candidate_observed", "")),
        spec_quote=str(result.get("spec_quote", "")),
        error_log=failure.traceback,
        relevant_specs=merge_relevant_specs(failure.relevant_specs, rationale),
        raw_response=raw_response,
    )

def _parse_classifier_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    elif not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            stripped = stripped[start : end + 1]
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ValueError(f"Classifier did not return valid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise ValueError("Classifier JSON must be an object")
    return parsed

def _load_classifier_output_path(result: dict[str, Any], *, cwd: Path, key: str = "failures") -> dict[str, Any]:
    inline = result.get(key)
    if isinstance(inline, list) and inline:
        return result

    output_path = result.get("output_path")
    sidecar_names = [str(output_path)] if output_path else []
    if DEFAULT_CLASSIFIER_RESULT_PATH not in sidecar_names:
        sidecar_names.append(DEFAULT_CLASSIFIER_RESULT_PATH)
    for sidecar_name in sidecar_names:
        sidecar = Path(sidecar_name)
        if not sidecar.is_absolute():
            sidecar = cwd / sidecar
        loaded = _load_classifier_sidecar(sidecar)
        if loaded is not None:
            log.info("Loaded classifier result from output_path: %s", sidecar)
            return loaded
    return result

def _load_classifier_sidecar(sidecar: Path) -> dict[str, Any] | None:
    if not sidecar.is_file():
        return None
    try:
        return _parse_classifier_json(sidecar.read_text(errors="replace"))
    except ValueError as error:
        log.warning("Could not parse classifier checkpoint %s: %s", sidecar, error)
        return None

def _last_agent_message(stdout: str) -> str:
    message = ""
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            message = item["text"]
    return message

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify candidate failures.")
    parser.add_argument("source", type=Path, help="Eval JSON file or iterative output directory")
    parser.add_argument("--task", default="", help="Task instance id; required if SOURCE contains multiple eval files")
    parser.add_argument("--spec-dir", default="", help="Specification directory. Inferred for iterative directories.")
    parser.add_argument("--test-spec-links", type=Path, help="test_spec_links.json used to annotate relevant spec sections")
    parser.add_argument("-o", "--output", default="", help="Output JSON path. Defaults beside SOURCE.")
    parser.add_argument("--model", default="codex/gpt-5.6-luna", help="Codex model used for attribution")
    parser.add_argument("--reasoning-effort", default="high", help="Codex reasoning effort")
    parser.add_argument(
        "--codex-command",
        default=DEFAULT_CODEX_COMMAND,
        help="Codex command prefix. The attribution prompt is appended as the final argument.",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_BRANCH_TIMEOUT, help="Classifier timeout in seconds")
    parser.add_argument("--limit", type=int, default=0, help="Classify at most this many failures; 0 means all")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BRANCH_SIZE,
        help=f"Maximum failures per branch classifier job (default: {DEFAULT_BRANCH_SIZE})",
    )
    parser.add_argument(
        "--branch-workers",
        type=int,
        default=DEFAULT_BRANCH_WORKERS,
        help=f"Classify test branches with this many parallel Codex instances (default: {DEFAULT_BRANCH_WORKERS})",
    )
    parser.add_argument(
        "--binary-id",
        default="",
        help="For .test_eval.json files, classify this binary id. Default is the ground-truth binary.",
    )
    parser.add_argument(
        "--reference-tests-dir",
        type=Path,
        help="Fixed reference-test root; <root>/<task> is staged read-only for the classifier.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Write classifier prompts without calling Codex")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite an existing attribution report")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    eval_json = resolve_eval_json(args.source, task=args.task)
    task = args.task or infer_task_from_eval_json(eval_json)
    spec_dir = task_scoped_dir(Path(args.spec_dir), task=task) if args.spec_dir else infer_spec_dir(args.source, task=task)
    output = Path(args.output) if args.output else default_output_path(args.source, eval_json)

    report = classify_failures(
        eval_json=eval_json,
        spec_dir=spec_dir,
        test_spec_links=args.test_spec_links,
        output=output,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        codex_command=args.codex_command,
        timeout=args.timeout,
        limit=args.limit,
        batch_size=args.batch_size,
        branch_workers=args.branch_workers,
        binary_id=args.binary_id,
        reference_tests_dir=task_scoped_dir(args.reference_tests_dir, task=task) if args.reference_tests_dir else None,
        dry_run=args.dry_run,
        force=args.force,
    )
    print(f"Wrote failure attribution report: {output}")
    print("Failure attribution summary: " + ", ".join(f"{k}={v}" for k, v in sorted(report.summary.items())))
    check_attribution_usable(report.failures, "Failure attribution")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
