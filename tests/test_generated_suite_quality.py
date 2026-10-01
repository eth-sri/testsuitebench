import json
from pathlib import Path

import pytest

from programbench.eval.test_suite_eval import BinaryTestSuiteResult, TestResult, TestSuiteEvaluationResult
from programbench.generated_suite_quality import (
    INFRASTRUCTURE_EXIT_CODE,
    REGENERATE_EXIT_CODE,
    crashed_in_test_code,
    main,
    suite_quality,
)


def _eval_json(tmp_path: Path, statuses: list[tuple[str, str]]) -> Path:
    trial = BinaryTestSuiteResult(
        binary_id="ground_truth",
        role="ground_truth",
        test_results=[TestResult(name=name, status="passed" if text == "" else "failure", extra={"text": text}) for name, text in statuses],
    )
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "org__repo.123.test_eval.json"
    path.write_text(TestSuiteEvaluationResult(binary_results=[trial], ground_truth_trials=[trial]).model_dump_json())
    return path


@pytest.mark.parametrize(
    ("traceback", "expected"),
    [
        ("test_x.py:3: in test_x\n    a = r['argv']\nE   TypeError: 'NoneType' object is not subscriptable", True),
        ("test_x.py:9: in test_x\nE   AssertionError: assert 1 == 0", False),
        ("E   FileNotFoundError: [Errno 2] No such file or directory: 'public/funding/index.html'", False),
        ("E   subprocess.CalledProcessError: Command '/workspace/executable --max' returned non-zero exit status 1.", False),
        ("E   AssertionError: assert b'' == b'x'\nE   NameError: name 'output' is not defined", True),
        ("", False),
    ],
)
def test_only_exceptions_raised_by_test_code_count_as_crashes(traceback: str, expected: bool) -> None:
    assert crashed_in_test_code(traceback) is expected


def test_suite_with_a_broken_fixture_is_rejected_but_a_spec_driven_low_pass_rate_is_kept(tmp_path: Path) -> None:
    broken = _eval_json(tmp_path / "broken", [("t0", "")] + [(f"t{i}", "E   TypeError: 'NoneType' object is not subscriptable") for i in range(1, 10)])
    spec_driven = _eval_json(tmp_path / "spec", [("t0", "")] + [(f"t{i}", "E   AssertionError: assert 'foo' in ''") for i in range(1, 4)])

    assert suite_quality(broken)["accept"] is False and suite_quality(broken)["crash_share"] == 0.9
    assert suite_quality(spec_driven) == {
        "eval_json": str(spec_driven), "infrastructure_failure": None, "tests": 4,
        "passing_on_reference": 1, "flaky": 0, "crashed_in_test_code": [], "crash_share": 0.0,
        "crash_share_limit": 0.80, "accept": True,
    }
    report = tmp_path / "quality.json"
    assert main([str(broken), "-o", str(report)]) == REGENERATE_EXIT_CODE
    assert json.loads(report.read_text())["crashed_in_test_code"] == [f"t{i}" for i in range(1, 10)]
    assert main([str(spec_driven)]) == 0


def _broken_eval_json(tmp_path: Path, ground_truth_error: str | None, mutant_error: str | None) -> Path:
    """An evaluation whose containers failed: trials carry an error_code and no test results."""
    binaries = [
        BinaryTestSuiteResult(binary_id="ground_truth", role="ground_truth", error_code=ground_truth_error,
                              error_details="start container failed (rc=125, manifest unknown)"),
        BinaryTestSuiteResult(binary_id="repo_1", role="candidate", error_code=mutant_error,
                              error_details="start container failed (rc=125, manifest unknown)"),
    ]
    if ground_truth_error is None:
        binaries[0].test_results = [TestResult(name="t0", status="passed", extra={"text": ""})]
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "org__repo.123.test_eval.json"
    path.write_text(
        TestSuiteEvaluationResult(binary_results=binaries, ground_truth_trials=[binaries[0]]).model_dump_json()
    )
    return path


def test_an_evaluation_that_never_ran_aborts_instead_of_regenerating(tmp_path: Path) -> None:
    """The zstd case: the task image was deleted mid-run, so every container start failed.

    No per-test evidence is indistinguishable from a suite crashing on import, and the
    regeneration that used to follow spent a full generation before failing identically.
    """
    broken = _broken_eval_json(tmp_path, "RuntimeError", "RuntimeError")
    report = suite_quality(broken)
    assert report["accept"] is False and report["tests"] == 0
    assert "manifest unknown" in report["infrastructure_failure"]
    assert main([str(broken)]) == INFRASTRUCTURE_EXIT_CODE


def test_only_the_mutants_failing_is_still_an_infrastructure_failure(tmp_path: Path) -> None:
    """A usable reference trial with no surviving mutant evidence scores mutation score 0 out of nothing."""
    assert main([str(_broken_eval_json(tmp_path, None, "RuntimeError"))]) == INFRASTRUCTURE_EXIT_CODE


def test_a_suite_that_collected_nothing_is_still_regenerated(tmp_path: Path) -> None:
    """Containers ran and pytest found no tests: that is the suite's fault, so regenerate."""
    assert main([str(_eval_json(tmp_path / "empty", []))]) == REGENERATE_EXIT_CODE
