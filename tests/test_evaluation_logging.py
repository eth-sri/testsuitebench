import logging
import math

import pytest

from programbench.eval.test_suite_eval_batch import _LoggedProgress
from programbench.eval.test_suite_eval import BinaryTestSuiteResult, TestSuiteEvaluator as Evaluator


@pytest.mark.parametrize("total", [0, 1, 3, 550])
def test_progress_early_milestones_and_no_duplicate_completion(total, caplog):
    caplog.set_level(logging.INFO)
    progress = _LoggedProgress(label="mutants", total=total)
    observed = []
    for completed in range(1, total + 1):
        before = len(caplog.records)
        progress.update()
        if len(caplog.records) > before:
            observed.append(completed)
    expected = sorted({math.ceil(total * p / 100) for p in [1, 2, 5, *range(10, 101, 10)]}) if total else []
    assert observed == expected
    before = len(caplog.records)
    progress.update()
    assert len(caplog.records) == before


def test_progress_jump_logs_once(caplog):
    caplog.set_level(logging.INFO)
    progress = _LoggedProgress(label="mutants", total=550)
    progress.update(55)
    assert len(caplog.records) == 1
    assert "55/550 (10%)" in caplog.text
    assert "interval_rate" in caplog.text


def test_evaluation_metrics_report_errors_and_reset_between_runs(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    evaluator = Evaluator(image_name="test", test_suite_archive=tmp_path)

    def run_reference():
        evaluator._phase_seconds["run_tests"] += 0.01
        return BinaryTestSuiteResult(binary_id="ground_truth", role="ground_truth", error_code="run_tests_timeout")

    monkeypatch.setattr(evaluator, "_run_ground_truth", run_reference)
    evaluator.run()
    evaluator.run()
    metrics = [record.message for record in caplog.records if "evaluation metrics;" in record.message]
    assert len(metrics) == 2
    for message in metrics:
        assert "completed=1 errors=1 cache_hits=0" in message
        assert "peak_active=1" in message
        assert "'run_tests': 0.01" in message
        assert "queue_mean=0.000s queue_max=0.000s" in message
        assert "worker occupancy is not CPU utilization" in message
