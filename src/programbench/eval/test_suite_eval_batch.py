# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Batch evaluation of generated test suites."""

import csv
import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, computed_field
from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from programbench.constants import DOCKER_CPUS, docker_cpus_for_budget
from programbench.eval.test_suite_eval import BinaryTestSuiteResult, TestSuiteEvaluationResult, TestSuiteEvaluator
from programbench.mutants import load_mutant_suite
from programbench.mutation_safeguards import (
    concentrated_tests_from_kill_sets,
    dominant_tests_from_kill_sets,
)
from programbench.skipped_tests import normalize_test_function_names, test_function_name
from programbench.utils.ground_truth_store import resolve_ground_truth_dir
from programbench.utils.instance_filters import filter_instances
from programbench.utils.reference_test_store import resolve_reference_tests_dir

log = logging.getLogger(__name__)


def _mutant_kill_sets(result: TestSuiteEvaluationResult) -> dict[str, list[str]]:
    kill_sets: dict[str, list[str]] = {}
    for binary in result.candidate_results:
        if binary.error_code is not None:
            kill_sets[binary.binary_id] = []
            continue
        kill_sets[binary.binary_id] = sorted(
            {
                test_function_name(name)
                for name in result.candidate_failing_ground_truth_passing_test_names(binary)
            }
        )
    return kill_sets


def _warn_dominant_generated_tests(instance_id: str, result: TestSuiteEvaluationResult) -> None:
    kill_sets = _mutant_kill_sets(result)
    mutant_ids = {binary.binary_id for binary in result.candidate_results}
    broad_tests = dominant_tests_from_kill_sets(kill_sets, mutant_ids=mutant_ids)
    broad_test_names = {item["test"] for item in broad_tests}
    for item in broad_tests:
        log.warning(
            "Generated test function %s for %s kills %d/%d mutants (%.1f%%), "
            "exceeding the 50%% broad-test threshold",
            item["test"], instance_id, item["killed"], item["total_mutants"],
            item["kill_fraction"] * 100,
        )
    for item in concentrated_tests_from_kill_sets(kill_sets, mutant_ids=mutant_ids):
        if item["test"] in broad_test_names:
            continue
        log.warning(
            "Generated test function %s for %s accounts for %d/%d observed "
            "mutant kills (%.1f%%), exceeding the 50%% concentration threshold",
            item["test"],
            instance_id,
            item["killed"],
            item["total_killed_mutants"],
            item["kill_concentration"] * 100,
        )


class _LoggedProgress:
    """Emit compact, thread-safe progress milestones for redirected runs."""

    def __init__(self, *, label: str, total: int, milestones: int = 10) -> None:
        self.label = label
        self.total = total
        self.completed = 0
        if milestones < 1:
            raise ValueError("milestones must be positive")
        self.thresholds = sorted({
            (total * numerator + denominator - 1) // denominator
            for numerator, denominator in [
                (1, 100), (2, 100), (5, 100),
                *((i, milestones) for i in range(1, milestones + 1)),
            ]
            if total > 0
        })
        self.last_completed = 0
        self.started = time.monotonic()
        self.last_logged = self.started
        self.lock = threading.Lock()

    def update(self, n: int = 1) -> None:
        with self.lock:
            self.completed = min(self.total, self.completed + n)
            if not self.thresholds or self.completed < self.thresholds[0]:
                return
            now = time.monotonic()
            elapsed = now - self.started
            rate = self.completed / elapsed if elapsed > 0 else 0.0
            remaining = self.total - self.completed
            eta = remaining / rate if rate > 0 else 0.0
            log.info(
                "%s: %d/%d (%.0f%%), elapsed %.1fs, rate %.2f/s, ETA %.1fs, interval_rate %.2f/s",
                self.label,
                self.completed,
                self.total,
                100 * self.completed / self.total,
                elapsed,
                rate,
                eta,
                (self.completed - self.last_completed) / max(now - self.last_logged, 1e-9),
            )
            self.last_completed = self.completed
            self.last_logged = now
            self.thresholds = [threshold for threshold in self.thresholds if threshold > self.completed]

    def close(self) -> None:
        pass


def _write_eval_json(eval_json: Path, result: TestSuiteEvaluationResult) -> None:
    """Persist a potentially large result without constructing one giant JSON string."""
    temporary = eval_json.with_suffix(f"{eval_json.suffix}.tmp")
    try:
        with temporary.open("w") as f:
            f.write("{\n  \"binary_results\": [")
            for index, binary in enumerate(result.binary_results):
                f.write("," if index else "")
                f.write("\n    ")
                json.dump(binary.model_dump(mode="json"), f, indent=2)
            if result.binary_results:
                f.write("\n  ")
            f.write("],\n  \"ground_truth_trials\": [")
            for index, trial in enumerate(result.ground_truth_trials):
                f.write("," if index else "")
                f.write("\n    ")
                json.dump(trial.model_dump(mode="json"), f, indent=2)
            if result.ground_truth_trials:
                f.write("\n  ")
            f.write("],\n  \"n_assertions\": ")
            json.dump(result.n_assertions, f)
            f.write(",\n  \"error_code\": ")
            json.dump(result.error_code, f)
            f.write(",\n  \"error_details\": ")
            json.dump(result.error_details, f)
            f.write("\n}")
        temporary.replace(eval_json)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _n_test_functions_from_eval_result(result: TestSuiteEvaluationResult) -> int:
    return result.n_test_functions


def _payloads_under_instance_root(instance_root: Path, archive_name: str) -> list[Path]:
    archive = instance_root / archive_name
    if archive.is_file():
        return [archive]
    if (instance_root / "eval" / "run.sh").is_file():
        return [instance_root]
    if not instance_root.is_dir():
        return []
    return [
        child
        for child in sorted(instance_root.iterdir())
        if child.is_dir()
        and child.name != "tests_untar"
        and (child / "eval" / "run.sh").is_file()
    ]


def _find_test_suite_payloads(
    *,
    source_dir: Path,
    instance_id: str,
    archive_name: str,
    tests_dir: str | Path = "",
) -> list[Path]:
    payloads: list[Path] = []
    if tests_dir:
        root = Path(tests_dir)
        payloads.extend(_payloads_under_instance_root(root / instance_id, archive_name))
        if (root / archive_name).is_file():
            payloads.append(root / archive_name)
        payloads.extend(_payloads_under_instance_root(root, archive_name))
    payloads.extend(_payloads_under_instance_root(source_dir / instance_id, archive_name))
    payloads.extend(_payloads_under_instance_root(source_dir, archive_name))

    seen: set[Path] = set()
    unique_payloads: list[Path] = []
    for payload in payloads:
        key = payload.resolve() if payload.exists() else payload
        if key in seen:
            continue
        seen.add(key)
        unique_payloads.append(payload)
    if unique_payloads:
        return unique_payloads
    return [source_dir / instance_id / archive_name]


def _find_test_suite_payload(
    *,
    source_dir: Path,
    instance_id: str,
    archive_name: str,
    tests_dir: str | Path = "",
) -> Path:
    return _find_test_suite_payloads(
        source_dir=source_dir,
        instance_id=instance_id,
        archive_name=archive_name,
        tests_dir=tests_dir,
    )[0]


def _payload_branch_name(payload: Path, instance_id: str, archive_name: str) -> str:
    if payload.is_file() or payload.name == instance_id or payload.name == archive_name:
        return ""
    return payload.name


def _prefixed_test_name(branch_name: str, test_name: str) -> str:
    return f"{branch_name}/{test_name}" if branch_name else test_name


def _filter_ignored_tests(
    result: TestSuiteEvaluationResult,
    ignored_tests: set[str],
) -> TestSuiteEvaluationResult:
    if not ignored_tests:
        return result
    ignored_tests = normalize_test_function_names(ignored_tests)
    return TestSuiteEvaluationResult(
        binary_results=[
            binary.model_copy(
                update={
                    "test_results": [
                        test
                        for test in binary.test_results
                        if test_function_name(test.name) not in ignored_tests
                    ]
                }
            )
            for binary in result.binary_results
        ],
        ground_truth_trials=[
            trial.model_copy(
                update={
                    "test_results": [
                        test
                        for test in trial.test_results
                        if test_function_name(test.name) not in ignored_tests
                    ]
                }
            )
            for trial in result.ground_truth_trials
        ],
        n_assertions=result.n_assertions,
        error_code=result.error_code,
        error_details=result.error_details,
    )


def _filter_ignored_mutants(result: TestSuiteEvaluationResult, ignored_mutants: set[str]) -> TestSuiteEvaluationResult:
    if not ignored_mutants:
        return result
    return result.model_copy(
        update={"binary_results": [binary for binary in result.binary_results if binary.binary_id not in ignored_mutants]}
    )


def _merge_branch_results(branch_results: list[tuple[str, TestSuiteEvaluationResult]]) -> TestSuiteEvaluationResult:
    if len(branch_results) == 1 and not branch_results[0][0]:
        return branch_results[0][1]

    merged_by_binary: dict[str, BinaryTestSuiteResult] = {}
    merged_ground_truth_trials: list[BinaryTestSuiteResult] = []
    n_assertions = 0
    has_assertions = False
    result_errors: list[str] = []
    for branch_name, result in branch_results:
        if result.n_assertions is not None:
            has_assertions = True
            n_assertions += result.n_assertions
        if result.error_code is not None:
            result_errors.append(f"{branch_name}:{result.error_code}")
        for trial_index, trial in enumerate(result._ground_truth_trials()):
            while len(merged_ground_truth_trials) <= trial_index:
                merged_ground_truth_trials.append(
                    BinaryTestSuiteResult(binary_id="ground_truth", role="ground_truth")
                )
            merged_trial = merged_ground_truth_trials[trial_index]
            merged_trial.test_results.extend(
                test.model_copy(update={"name": _prefixed_test_name(branch_name, test.name)})
                for test in trial.test_results
            )
            merged_trial.log.extend({"branch": branch_name, **entry} for entry in trial.log)
            merged_trial.warnings.extend(f"{branch_name}: {warning}" for warning in trial.warnings)
            if trial.error_code is not None:
                branch_error = f"{branch_name}:{trial.error_code}"
                merged_trial.error_code = (
                    branch_error
                    if merged_trial.error_code is None
                    else f"{merged_trial.error_code}; {branch_error}"
                )
                if trial.error_details:
                    detail = f"{branch_name}: {trial.error_details}"
                    merged_trial.error_details = (
                        detail
                        if merged_trial.error_details is None
                        else f"{merged_trial.error_details}\n{detail}"
                    )
        for binary in result.binary_results:
            merged = merged_by_binary.get(binary.binary_id)
            if merged is None:
                merged = BinaryTestSuiteResult(binary_id=binary.binary_id, role=binary.role)
                merged_by_binary[binary.binary_id] = merged
            merged.test_results.extend(
                test.model_copy(update={"name": _prefixed_test_name(branch_name, test.name)})
                for test in binary.test_results
            )
            merged.log.extend({"branch": branch_name, **entry} for entry in binary.log)
            merged.warnings.extend(f"{branch_name}: {warning}" for warning in binary.warnings)
            if binary.error_code is not None:
                branch_error = f"{branch_name}:{binary.error_code}"
                if merged.error_code is None:
                    merged.error_code = branch_error
                elif branch_error not in merged.error_code.split("; "):
                    merged.error_code = f"{merged.error_code}; {branch_error}"
                if binary.error_details:
                    detail = f"{branch_name}: {binary.error_details}"
                    merged.error_details = detail if merged.error_details is None else f"{merged.error_details}\n{detail}"

    return TestSuiteEvaluationResult(
        binary_results=list(merged_by_binary.values()),
        ground_truth_trials=merged_ground_truth_trials,
        n_assertions=n_assertions if has_assertions else None,
        error_code="; ".join(result_errors) if result_errors else None,
    )


def _failure_matrix_csv_path(instance_id: str, eval_json: Path) -> Path:
    return eval_json.with_name(f"{instance_id}.failure_matrix.csv")


def _write_failure_matrix_csv(instance_id: str, result: TestSuiteEvaluationResult, eval_json: Path) -> Path:
    headers, rows, binary_errors = TestSuiteEvaluator._failure_matrix_table(result.binary_results, include_passing=True)
    csv_path = _failure_matrix_csv_path(instance_id, eval_json)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        if headers:
            writer.writerow(headers)
            writer.writerows(rows)
        if binary_errors:
            if headers:
                writer.writerow([])
            writer.writerow(["binary_id", "error_code"])
            for binary in binary_errors:
                writer.writerow([binary.binary_id, binary.error_code or ""])
    return csv_path


class InstanceTestSuiteEvalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    score: float
    n_passed: int
    n_tests: int
    n_assertions: int | None = None
    n_test_functions: int = 0
    ground_truth_passed: bool = False
    error_code: str | None = None
    binary_errors: dict[str, str] = {}
    n_system_errors: int = 0
    n_warnings: int = 0
    n_mutants: int = 0
    n_mutants_killed: int = 0
    validity_rate: float = 0.0
    mutation_score: float | None = None

    @classmethod
    def from_eval_result(cls, instance_id: str, result: TestSuiteEvaluationResult) -> Self:
        warnings = sum(len(binary.warnings) for binary in result.binary_results)
        binary_errors = {
            binary.binary_id: binary.error_code
            for binary in result.binary_results
            if binary.error_code is not None
        }
        return cls(
            instance_id=instance_id,
            score=result.score,
            n_passed=result.n_passed,
            n_tests=len(result),
            n_assertions=result.n_assertions,
            n_test_functions=getattr(result, "n_test_functions", _n_test_functions_from_eval_result(result)),
            ground_truth_passed=result.ground_truth_passed,
            error_code=result.error_code,
            binary_errors=binary_errors,
            n_system_errors=result.n_system_errors,
            n_warnings=warnings,
            n_mutants=result.n_mutants,
            n_mutants_killed=result.n_mutants_killed,
            validity_rate=result.validity_rate,
            mutation_score=result.mutation_score,
        )


class BatchTestSuiteEvalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summaries: list[InstanceTestSuiteEvalSummary]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_instances(self) -> int:
        return len(self.summaries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average_pass_rate(self) -> float:
        if not self.summaries:
            return 0.0
        return sum(s.score for s in self.summaries) / len(self.summaries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def n_ground_truth_passed(self) -> int:
        return sum(s.ground_truth_passed for s in self.summaries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_test_functions(self) -> int:
        return sum(s.n_test_functions for s in self.summaries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average_validity_rate(self) -> float:
        if not self.summaries:
            return 0.0
        return sum(s.validity_rate for s in self.summaries) / len(self.summaries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def average_mutation_score(self) -> float | None:
        mutation_scores = [s.mutation_score for s in self.summaries if s.mutation_score is not None]
        if not mutation_scores:
            return None
        return sum(mutation_scores) / len(mutation_scores)

    def summary(self) -> Group:
        table = Table(title="Generated Test Suite Evaluation Summary", show_lines=False, box=None)
        table.add_column("Instance", style="bold")
        table.add_column("Validity Rate", justify="right")
        table.add_column("Mutation Score", justify="right")
        table.add_column("Tests", justify="right")
        table.add_column("Comment")

        for s in sorted(self.summaries, key=lambda s: s.instance_id):
            score_style = "green" if s.ground_truth_passed else "yellow" if s.score > 0 else "red"
            if s.error_code:
                comment = Text(f"ERROR: {s.error_code}", style="bold red")
            elif s.binary_errors or s.n_system_errors or s.n_warnings:
                parts = []
                if s.binary_errors:
                    parts.append("BINARY: " + ", ".join(f"{b}: {e}" for b, e in s.binary_errors.items()))
                if s.n_system_errors:
                    parts.append(f"SYSTEM: {s.n_system_errors}")
                if s.n_warnings:
                    parts.append(f"WARN: {s.n_warnings}")
                comment = Text("ERRORS: " + "; ".join(parts), style="bold red")
            else:
                comment = Text(f"{s.n_tests} executed generated tests")
            if s.n_mutants:
                comment = Text(f"{s.n_mutants_killed}/{s.n_mutants} mutants killed")
            validity_rate_text = (
                Text("✅", style=score_style)
                if s.validity_rate == 1.0
                else Text(f"{s.validity_rate * 100:.1f}", style=score_style)
            )
            mutation_score_text = (
                Text("-", style=score_style)
                if s.mutation_score is None
                else Text("✅", style=score_style)
                if s.mutation_score == 1.0
                else Text(f"{s.mutation_score * 100:.1f}", style=score_style)
            )
            table.add_row(s.instance_id, validity_rate_text, mutation_score_text, str(s.n_test_functions), comment)

        table.add_section()
        table.add_row(
            "Average",
            Text("✅" if self.average_validity_rate == 1.0 else f"{self.average_validity_rate * 100:.1f}", style="bold"),
            Text(
                "-"
                if self.average_mutation_score is None
                else "✅"
                if self.average_mutation_score == 1.0
                else f"{self.average_mutation_score * 100:.1f}",
                style="bold",
            ),
            Text(str(self.total_test_functions), style="bold"),
            f"{self.n_ground_truth_passed}/{self.total_instances} pass ground truth",
        )
        note = Text(
            "Note: A displayed 100.0 may be rounded. Only ✅ indicates an exact score of 100%.",
            style="dim",
        )
        return Group(table, note)


def _summary_from_existing(
    instance_id: str,
    eval_json: Path,
    *,
    detailed_logs: bool = False,
    ignored_tests: set[str] | None = None,
    ignored_mutants: set[str] | None = None,
    warn_dominant_mutant_kills: bool = True,
) -> InstanceTestSuiteEvalSummary:
    result = TestSuiteEvaluationResult.model_validate_json(eval_json.read_text())
    result = _filter_ignored_tests(result, ignored_tests or set())
    result = _filter_ignored_mutants(result, ignored_mutants or set())
    if warn_dominant_mutant_kills:
        _warn_dominant_generated_tests(instance_id, result)
    if detailed_logs:
        csv_path = _write_failure_matrix_csv(instance_id, result, eval_json)
        log.info("Wrote failure matrix CSV for %s: %s", instance_id, csv_path)
    return InstanceTestSuiteEvalSummary.from_eval_result(instance_id, result)


def _evaluate_instance(
    *,
    instance_id: str,
    instance: dict,
    source_dir: Path,
    target_dir: Path,
    force: bool,
    archive_name: str,
    image_tag: str = "task_patched",
    docker_cpus: int = DOCKER_CPUS,
    cpu_budget: int = 0,
    branch_workers: int = 1,
    tests_dir: str | Path = "",
    ground_truth_dir: str | Path = "",
    reference_tests_dir: str | Path = "extracted-tests",
    mutants_dir: str | Path = "",
    mutant_ids: set[str] | None = None,
    detailed_logs: bool = False,
    reference_trials: int = 1,
    ignored_tests: set[str] | None = None,
    ignored_mutants: set[str] | None = None,
    warn_dominant_mutant_kills: bool = True,
    evaluation_cache_dir: str | Path = "",
) -> InstanceTestSuiteEvalSummary | None:
    instance_started = time.monotonic()
    eval_json = target_dir / instance_id / f"{instance_id}.test_eval.json"
    if eval_json.exists() and not force:
        log.info("Skipping %s (already evaluated, use --force to re-run)", instance_id)
        return _summary_from_existing(
            instance_id,
            eval_json,
            detailed_logs=detailed_logs,
            ignored_tests=ignored_tests,
            ignored_mutants=ignored_mutants,
            warn_dominant_mutant_kills=warn_dominant_mutant_kills,
        )

    test_suite_payloads = _find_test_suite_payloads(
        source_dir=source_dir,
        instance_id=instance_id,
        archive_name=archive_name,
        tests_dir=tests_dir,
    )
    existing_payloads = [payload for payload in test_suite_payloads if payload.exists()]
    if not existing_payloads:
        log.warning("Skipping %s (no generated test suite payload)", instance_id)
        return InstanceTestSuiteEvalSummary(
            instance_id=instance_id,
            score=0.0,
            n_passed=0,
            n_tests=0,
            error_code="no_test_suite",
        )

    try:
        ground_truth_executable = None
        if ground_truth_dir:
            ground_truth_executable = resolve_ground_truth_dir(str(ground_truth_dir), instance_id) / instance_id / "executable"
            if not ground_truth_executable.is_file():
                raise FileNotFoundError(
                    "Ground-truth executable does not exist for "
                    f"{instance_id}: {ground_truth_executable}"
                )
        mutant_suite_info = load_mutant_suite(mutants_dir, instance_id) if mutants_dir else None
        mutants_root = None
        mutants = []
        allocation_mutants = 0
        if mutant_suite_info is not None:
            mutants_root, mutant_suite = mutant_suite_info
            mutants = [mutant for mutant in mutant_suite.mutants if mutant.id not in (ignored_mutants or set())]
            allocation_mutants = len(mutants)
            if mutant_ids is not None:
                mutants = [mutant for mutant in mutants if mutant.id in mutant_ids]
            if mutant_ids != set():
                allocation_mutants = len(mutants)
        mutant_work_units = len(mutants) * len(existing_payloads)
        mutant_progress = (
            tqdm(
                total=mutant_work_units,
                desc=f"{instance_id} mutants",
                ncols=100,
                leave=False,
                disable=None,
            )
            if mutants and sys.stderr.isatty()
            else _LoggedProgress(
                label=f"Mutant evaluation progress for {instance_id}",
                total=mutant_work_units,
            )
            if mutants
            else None
        )
        if allocation_mutants:
            # Reference-only preflight uses the same quota as the subsequent
            # full pass, making its results comparable and checkpoints reusable.
            parallel_units = len(existing_payloads) * (allocation_mutants + reference_trials)
        elif len(existing_payloads) > 1:
            parallel_units = len(existing_payloads)
        else:
            parallel_units = reference_trials
        active_workers = min(branch_workers, max(1, parallel_units))
        allocated_docker_cpus = docker_cpus_for_budget(
            cpu_budget, active_workers, fallback=docker_cpus
        )
        log.info(
            "Effective execution limit for %s: %d binary container(s) total "
            "across all payloads, %d CPU(s) per container, at most %d CPU(s) "
            "allocated (task CPU budget: %d)",
            instance_id,
            active_workers,
            allocated_docker_cpus,
            active_workers * allocated_docker_cpus,
            cpu_budget,
        )

        execution_started = time.monotonic()
        shared_execution_pool = None

        def run_payload(test_suite_payload: Path, *, payload_branch_workers: int) -> tuple[str, TestSuiteEvaluationResult]:
            branch_name = _payload_branch_name(test_suite_payload, instance_id, archive_name)
            if len(existing_payloads) > 1:
                log.debug(
                    "Evaluating %s payload; binary executions use the shared "
                    "%d-container task pool: %s",
                    instance_id,
                    payload_branch_workers,
                    test_suite_payload,
                )
            evaluator = TestSuiteEvaluator(
                image_name=instance["image_name"],
                test_suite_archive=test_suite_payload,
                instance_id=instance_id,
                image_tag=image_tag,
                docker_cpus=allocated_docker_cpus,
                branch_workers=payload_branch_workers,
                mutants_root=mutants_root,
                mutants=mutants,
                ground_truth_executable=ground_truth_executable,
                reference_tests_root=(
                    resolve_reference_tests_dir(reference_tests_dir, instance_id) if reference_tests_dir else None
                ),
                detailed_logs=detailed_logs,
                reference_trials=reference_trials,
                mutant_progress_callback=mutant_progress.update if mutant_progress is not None else None,
                log_run_summary=False,
                ignored_tests={
                    test_function_name(name[len(branch_name) + 1:])
                    for name in (ignored_tests or set())
                    if name.startswith(branch_name + "/")
                },
                execution_pool=shared_execution_pool,
                cache_dir=Path(evaluation_cache_dir) / instance_id if evaluation_cache_dir else None,
            )
            return branch_name, evaluator.run()

        if len(existing_payloads) > 1 and branch_workers > 1:
            # Branch preparation is concurrent; binary execution shares one
            # global budget, including the slow tail of each branch.
            branch_pool_workers = min(branch_workers, len(existing_payloads))
            payload_branch_workers = branch_workers if mutants else 1
            if mutants:
                log.info(
                    "Evaluating %s: %d payload(s), %d mutant(s) per payload; "
                    "%d payload coordinator(s), %d shared binary container(s) total",
                    instance_id,
                    len(existing_payloads),
                    len(mutants),
                    branch_pool_workers,
                    active_workers,
                )
            else:
                log.info(
                    "Evaluating %s: %d payload(s) with %d payload worker(s)",
                    instance_id,
                    len(existing_payloads),
                    branch_pool_workers,
                )
            branch_results_by_index: dict[int, tuple[str, TestSuiteEvaluationResult]] = {}
            # All branches submit binaries to one executor: a slow branch tail
            # no longer leaves CPUs idle before the next payload can start.
            with (
                ThreadPoolExecutor(max_workers=active_workers) as binary_pool,
                ThreadPoolExecutor(max_workers=branch_pool_workers) as branch_pool,
            ):
                shared_execution_pool = binary_pool if mutants else None
                futures = {
                    branch_pool.submit(
                        run_payload,
                        test_suite_payload,
                        payload_branch_workers=payload_branch_workers,
                    ): index
                    for index, test_suite_payload in enumerate(existing_payloads)
                }
                for future in as_completed(futures):
                    branch_results_by_index[futures[future]] = future.result()
            branch_results = [branch_results_by_index[index] for index in range(len(existing_payloads))]
        else:
            if mutants:
                log.info(
                    "Evaluating %s: %d payload(s), %d mutant(s) per payload; "
                    "%d shared binary container(s) total",
                    instance_id,
                    len(existing_payloads),
                    len(mutants),
                    active_workers,
                )
            branch_results = [
                run_payload(test_suite_payload, payload_branch_workers=branch_workers)
                for test_suite_payload in existing_payloads
            ]
        if mutant_progress is not None:
            mutant_progress.close()
        execution_seconds = time.monotonic() - execution_started
        postprocess_started = time.monotonic()
        result = _merge_branch_results(branch_results)
        result = _filter_ignored_tests(result, ignored_tests or set())
        result = _filter_ignored_mutants(result, ignored_mutants or set())
        if warn_dominant_mutant_kills:
            _warn_dominant_generated_tests(instance_id, result)
        (target_dir / instance_id).mkdir(parents=True, exist_ok=True)
        write_started = time.monotonic()
        _write_eval_json(eval_json, result)
        json_write_seconds = time.monotonic() - write_started
        if detailed_logs:
            csv_path = _write_failure_matrix_csv(instance_id, result, eval_json)
            log.info("Wrote failure matrix CSV for %s: %s", instance_id, csv_path)
        summary = InstanceTestSuiteEvalSummary.from_eval_result(instance_id, result)
        log.info(
            "Instance evaluation metrics for %s: source=%s wall=%.3fs payload_execution=%.3fs "
            "postprocess=%.3fs json_write=%.3fs json_bytes=%d payloads=%d mutants=%d "
            "workers=%d cpus_per_container=%d binary_errors=%d",
            instance_id, source_dir, time.monotonic() - instance_started, execution_seconds,
            time.monotonic() - postprocess_started, json_write_seconds, eval_json.stat().st_size,
            len(existing_payloads), len(mutants), active_workers, allocated_docker_cpus,
            len(summary.binary_errors),
        )
        return summary
    except Exception as e:
        if "mutant_progress" in locals() and mutant_progress is not None:
            mutant_progress.close()
        log.error("Error evaluating generated tests for %s: %s", instance_id, e, exc_info=True)
        return InstanceTestSuiteEvalSummary(
            instance_id=instance_id,
            score=0.0,
            n_passed=0,
            n_tests=0,
            error_code=type(e).__name__,
        )


def _summarize_instance(
    *,
    instance_id: str,
    source_dir: Path,
    target_dir: Path,
    archive_name: str,
    tests_dir: str | Path = "",
    mutants_dir: str | Path = "",
    detailed_logs: bool = False,
    ignored_tests: set[str] | None = None,
    ignored_mutants: set[str] | None = None,
    warn_dominant_mutant_kills: bool = True,
) -> InstanceTestSuiteEvalSummary | None:
    eval_json = target_dir / instance_id / f"{instance_id}.test_eval.json"
    if not eval_json.exists():
        log.warning("Skipping %s (no test_eval.json)", instance_id)
        return None
    try:
        return _summary_from_existing(
            instance_id,
            eval_json,
            detailed_logs=detailed_logs,
            ignored_tests=ignored_tests,
            ignored_mutants=ignored_mutants,
            warn_dominant_mutant_kills=warn_dominant_mutant_kills,
        )
    except Exception as e:
        log.error("Error summarizing generated tests for %s: %s", instance_id, e, exc_info=True)
        return InstanceTestSuiteEvalSummary(
            instance_id=instance_id,
            score=0.0,
            n_passed=0,
            n_tests=0,
            error_code=type(e).__name__,
        )


def run_test_suite_eval_batch(
    *,
    sources: list[str | Path],
    force: bool = False,
    filter_spec: str = "",
    slice_spec: str = "",
    workers: int = 1,
    docker_cpus: int = DOCKER_CPUS,
    cpu_budget: int = 0,
    branch_workers: int = 1,
    summarize_only: bool = False,
    image_tag: str = "task_patched",
    output: str | Path = "",
    archive_name: str = "tests.tar.gz",
    tests_dir: str | Path = "",
    ground_truth_dir: str | Path = "",
    reference_tests_dir: str | Path = "extracted-tests",
    mutants_dir: str | Path = "",
    mutant_ids: set[str] | None = None,
    detailed_logs: bool = False,
    reference_trials: int = 1,
    skipped_tests: str | Path = "",
    skipped_mutants: str | Path = "",
    warn_dominant_mutant_kills: bool = True,
    evaluation_cache_dir: str | Path = "",
) -> None:
    from programbench.utils.load_data import get_ignored_tests, load_all_instances
    from programbench.skipped_mutants import load_skipped_mutants
    from programbench.skipped_tests import load_skipped_tests

    all_instances = load_all_instances(include_tests=True)
    log.info("Loaded %d instances", len(all_instances))

    all_instances = filter_instances(
        all_instances,
        filter_spec=filter_spec,
        slice_spec=slice_spec,
    )
    instance_lookup = {inst["instance_id"]: inst for inst in all_instances}
    output_root = Path(output) if output else None

    work_items: list[tuple[Path, Path, str]] = []
    for source in sources:
        source_dir = Path(source)
        target_dir = output_root / source_dir.name if output_root else source_dir
        log.info("Running in test-suite directory mode: %s -> %s", source_dir, target_dir)
        instance_ids = [d.name for d in sorted(source_dir.iterdir()) if d.is_dir()]
        instance_ids = [iid for iid in instance_ids if iid in instance_lookup]
        for iid in instance_ids:
            work_items.append((source_dir, target_dir, iid))

    if not work_items:
        log.warning("No generated test suites to evaluate.")
        return

    log.info(
        "Evaluating generated test suites for %d instances across %d source(s) "
        "with %d instance(s) in parallel, a per-instance limit of %d shared "
        "binary container(s), %d configured CPU(s) per container before budget "
        "adjustment, and a %d CPU task budget per instance",
        len(work_items),
        len(sources),
        workers,
        branch_workers,
        docker_cpus,
        cpu_budget,
    )

    results_by_source: dict[Path, list[InstanceTestSuiteEvalSummary]] = {}
    for source_dir, _, _ in work_items:
        results_by_source.setdefault(source_dir, [])

    with (
        logging_redirect_tqdm(),
        ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        if summarize_only:
            futures = {
                executor.submit(
                    _summarize_instance,
                    instance_id=iid,
                    source_dir=source_dir,
                    target_dir=target_dir,
                    archive_name=archive_name,
                    tests_dir=tests_dir,
                    mutants_dir=mutants_dir,
                    detailed_logs=detailed_logs,
                    ignored_tests=get_ignored_tests(instance_lookup[iid]) | load_skipped_tests(skipped_tests, task=iid),
                    ignored_mutants=load_skipped_mutants(skipped_mutants, task=iid),
                    warn_dominant_mutant_kills=warn_dominant_mutant_kills,
                ): source_dir
                for source_dir, target_dir, iid in work_items
            }
            desc = "Summarizing generated tests"
        else:
            futures = {
                executor.submit(
                    _evaluate_instance,
                    instance_id=iid,
                    instance=instance_lookup[iid],
                    source_dir=source_dir,
                    target_dir=target_dir,
                    force=force,
                    archive_name=archive_name,
                    image_tag=image_tag,
                    docker_cpus=docker_cpus,
                    cpu_budget=cpu_budget,
                    branch_workers=branch_workers,
                    tests_dir=tests_dir,
                    ground_truth_dir=ground_truth_dir,
                    reference_tests_dir=reference_tests_dir,
                    mutants_dir=mutants_dir,
                    mutant_ids=mutant_ids,
                    detailed_logs=detailed_logs,
                    reference_trials=reference_trials,
                    ignored_tests=get_ignored_tests(instance_lookup[iid]) | load_skipped_tests(skipped_tests, task=iid),
                    ignored_mutants=load_skipped_mutants(skipped_mutants, task=iid),
                    warn_dominant_mutant_kills=warn_dominant_mutant_kills,
                    evaluation_cache_dir=evaluation_cache_dir,
                ): source_dir
                for source_dir, target_dir, iid in work_items
            }
            desc = "Evaluating generated tests"
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=desc,
            ncols=100,
            leave=False,
            disable=None,
        ):
            summary = future.result()
            if summary:
                results_by_source[futures[future]].append(summary)

    console = Console()
    for source_dir, summaries in results_by_source.items():
        summaries.sort(key=lambda s: s.instance_id)
        batch = BatchTestSuiteEvalSummary(summaries=summaries)
        console.print()
        if len(sources) > 1:
            console.print(f"[bold]{source_dir}[/bold]")
        console.print(batch.summary())
