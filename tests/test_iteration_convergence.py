import json
from pathlib import Path

import pytest

from programbench.eval.test_suite_eval import BinaryTestSuiteResult, TestResult, TestSuiteEvaluationResult
from programbench.iteration_convergence import convergence, main

TASK = "org__repo.123"


def _checkpoint(iteration_dir: Path, *phases: str) -> None:
    (iteration_dir / "stages" / TASK).mkdir(parents=True, exist_ok=True)
    (iteration_dir / "stages" / TASK / "pipeline-checkpoints.tsv").write_text("".join(f"{phase}\tcompleted\tnow\n" for phase in phases))


def _write_acc(iteration_dir: Path, *, spec_faults: int, total: int, passed: int | None = None, errors: int = 0) -> None:
    log_dir = iteration_dir / "log" / TASK
    log_dir.mkdir(parents=True, exist_ok=True)
    summary = {"error": errors, "error_infra": 0, "executable": 1, "spec_underspecification": spec_faults, "spec_contradiction": 0, "unknown": 0}
    (log_dir / "failure_attribution.json").write_text(json.dumps({"summary": summary, "failures": []}))
    (iteration_dir / "executable" / TASK).mkdir(parents=True)
    passed = total if passed is None else passed
    (iteration_dir / "executable" / TASK / f"{TASK}.eval.json").write_text(
        json.dumps({"test_results": [{"status": "passed"}] * passed + [{"status": "failed"}] * (total - passed)})
    )


def _write_test_direction(iteration_dir: Path, *, test_spec_faults: int, tests: int, mutants: list[dict], errors: int = 0) -> None:
    log_dir = iteration_dir / "log" / TASK
    log_dir.mkdir(parents=True, exist_ok=True)
    summary = {"test": 0, "spec_underspecification": 0, "spec_contradiction": test_spec_faults, "flaky": 0, "error": errors, "error_infra": 0, "unknown": 0}
    (log_dir / "mutant_attribution.json").write_text(json.dumps({"test_failure_summary": summary, "mutants": mutants}))
    names = [f"t{index}" for index in range(tests)]
    result = TestSuiteEvaluationResult(
        binary_results=[
            BinaryTestSuiteResult(binary_id="ground_truth", role="ground_truth", test_results=[TestResult(name=name, status="passed", extra={}) for name in names]),
            *(
                BinaryTestSuiteResult(
                    binary_id=mutant["mutant_id"],
                    role="candidate",
                    test_results=[TestResult(name=name, status="passed" if mutant["status"] == "survived" else "failure", extra={}) for name in names],
                )
                for mutant in mutants
            ),
        ]
    )
    eval_json = iteration_dir / "mutant-eval" / "generated-test" / TASK / f"{TASK}.test_eval.json"
    eval_json.parent.mkdir(parents=True)
    eval_json.write_text(result.model_dump_json())


def test_convergence_latches_per_direction_and_only_reads_completed_classifications(tmp_path: Path) -> None:
    iter_1 = tmp_path / "iter_1"
    _write_acc(iter_1, spec_faults=2, total=100)
    _write_test_direction(
        iter_1,
        test_spec_faults=0,
        tests=50,
        mutants=[{"mutant_id": "repo_1", "status": "survived", "fault": "spec_contradiction"}, {"mutant_id": "repo_2", "status": "killed", "fault": "test"}],
    )
    _checkpoint(iter_1, "candidate-classify", "generated-test-mutant-classify")
    iter_2 = tmp_path / "iter_2"
    _write_acc(iter_2, spec_faults=0, total=100)
    _write_test_direction(iter_2, test_spec_faults=40, tests=50, mutants=[])
    _checkpoint(iter_2, "candidate-classify")

    report = convergence(tmp_path, TASK, 1.0, 10.0)

    assert report["rates"] == {
        1: {
            "acc": {"spec_fault_pct": 2.0, "metric_pct": 100.0, "error_pct": 0.0},
            "validity_rate": {"spec_fault_pct": 0.0, "metric_pct": 100.0, "error_pct": 0.0},
            "mutation_score": {"spec_fault_pct": 50.0, "metric_pct": 50.0},
        },
        2: {"acc": {"spec_fault_pct": 0.0, "metric_pct": 100.0, "error_pct": 0.0}},
    }
    assert report["converged"] == {"acc": True, "validity_rate": True, "mutation_score": False}
    assert report["converged_by_iteration"] == {
        1: {"acc": False, "validity_rate": True, "mutation_score": False},
        2: {"acc": True, "validity_rate": True, "mutation_score": False},
    }
    assert convergence(tmp_path, TASK, 3.0, 10.0)["converged"] == {"acc": True, "validity_rate": True, "mutation_score": False}
    assert convergence(tmp_path / "missing", TASK, 1.0, 10.0)["converged"] == {"acc": False, "validity_rate": False, "mutation_score": False}


def test_only_acc_and_validity_rate_are_guarded_by_a_minimum_metric(tmp_path: Path) -> None:
    """A candidate that passes nothing has every failure attributed to the executable, so zero spec faults mean nothing."""
    _write_acc(tmp_path / "iter_1", spec_faults=0, total=100, passed=10)
    _checkpoint(tmp_path / "iter_1", "candidate-classify")

    _write_test_direction(tmp_path / "iter_1", test_spec_faults=0, tests=20, mutants=[{"mutant_id": "repo_1", "status": "survived", "fault": "test"}] * 20)
    _checkpoint(tmp_path / "iter_1", "candidate-classify", "generated-test-mutant-classify")

    report = convergence(tmp_path, TASK, 5.0, 10.0)

    assert report["rates"][1]["mutation_score"]["metric_pct"] == 0.0
    assert report["converged"] == {"acc": False, "validity_rate": True, "mutation_score": True}
    assert convergence(tmp_path, TASK, 5.0, 9.0)["converged"]["acc"] is True


def test_mostly_error_failures_stop_every_direction_and_latch(tmp_path: Path) -> None:
    """A suite whose failures never reached the executable carries no spec evidence, so the task stops."""
    _write_acc(tmp_path / "iter_1", spec_faults=5, total=100)
    _write_test_direction(tmp_path / "iter_1", test_spec_faults=1, tests=20, mutants=[{"mutant_id": "repo_1", "status": "survived", "fault": "spec_contradiction"}], errors=9)
    _checkpoint(tmp_path / "iter_1", "candidate-classify", "generated-test-mutant-classify")
    _write_acc(tmp_path / "iter_2", spec_faults=5, total=100)
    _checkpoint(tmp_path / "iter_2", "candidate-classify")

    report = convergence(tmp_path, TASK, 1.0, 10.0, 80.0)

    assert report["rates"][1]["validity_rate"]["error_pct"] == 90.0
    assert report["rates"][1]["acc"]["error_pct"] == 0.0
    assert report["error_stopped"] is True
    assert report["converged"] == {"acc": True, "validity_rate": True, "mutation_score": True}
    assert report["converged_by_iteration"] == {1: {"acc": True, "validity_rate": True, "mutation_score": True}, 2: {"acc": True, "validity_rate": True, "mutation_score": True}}
    assert convergence(tmp_path, TASK, 1.0, 10.0, 90.0)["converged"] == {"acc": False, "validity_rate": False, "mutation_score": False}
    assert convergence(tmp_path, TASK, 1.0, 10.0)["error_stopped"] is False
    assert main(["--iter-root", str(tmp_path), "--task", TASK, "--max-error", "80"]) == 0


def test_main_prints_shell_flags_and_writes_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_acc(tmp_path / "iter_1", spec_faults=0, total=10)
    _checkpoint(tmp_path / "iter_1", "candidate-classify")
    output = tmp_path / "iter_2" / "stages" / TASK / "convergence.json"

    assert main(["--iter-root", str(tmp_path), "--task", TASK, "--output", str(output)]) == 0
    assert capsys.readouterr().out == "acc=1 validity_rate=0 mutation_score=0\n"
    assert json.loads(output.read_text())["converged"] == {"acc": True, "validity_rate": False, "mutation_score": False}


def test_a_direction_that_was_not_measured_cannot_latch_converged(tmp_path: Path) -> None:
    """Skipping mutant evaluation leaves no mutation score evidence, and no evidence is not a perfect score."""
    iter_1 = tmp_path / "iter_1"
    _write_acc(iter_1, spec_faults=50, total=100)
    _write_test_direction(iter_1, test_spec_faults=50, tests=50, mutants=[])
    _checkpoint(iter_1, "candidate-classify", "generated-test-mutant-classify")

    report = convergence(tmp_path, TASK, threshold_pct=5.0, min_metric_pct=10.0)

    assert "mutation_score" not in report["rates"][1]
    assert report["converged"] == {"acc": False, "validity_rate": False, "mutation_score": False}


def test_a_skipped_validity_rate_classification_is_absent_rather_than_faultless(tmp_path: Path) -> None:
    iter_1 = tmp_path / "iter_1"
    _write_acc(iter_1, spec_faults=50, total=100)
    _write_test_direction(iter_1, test_spec_faults=0, tests=50, mutants=[{"mutant_id": "repo_1", "status": "survived", "fault": "test"}])
    log_dir = iter_1 / "log" / TASK
    report_path = log_dir / "mutant_attribution.json"
    stored = json.loads(report_path.read_text())
    stored["test_failure_summary"] = {}
    report_path.write_text(json.dumps(stored))
    _checkpoint(iter_1, "candidate-classify", "generated-test-mutant-classify")

    report = convergence(tmp_path, TASK, threshold_pct=5.0, min_metric_pct=10.0)

    # An empty summary must not be read as zero spec faults, which would converge validity rate outright.
    assert "validity_rate" not in report["rates"][1]
    assert report["converged"]["validity_rate"] is False
    # Mutation Score was still measured this iteration and survives on its own.
    assert report["rates"][1]["mutation_score"]["metric_pct"] == 0.0
