"""Decide which evaluation directions of an iterative run still need to be rerun."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from programbench.eval.test_suite_eval import TestSuiteEvaluationResult
from programbench.failure_attribution import SPEC_FAULTS

METRICS = ("acc", "validity_rate", "mutation_score")
ERROR_FAULTS = ("error", "error_infra")
# A candidate passing nothing yields no spec faults to attribute; mutation score is expected to stay low, so it is not guarded.
GUARDED_METRICS = ("acc", "validity_rate")


def _pct(count: int, total: int) -> float:
    return 0.0 if total == 0 else 100 * count / total


def _spec_count(summary: dict[str, int]) -> int:
    return sum(summary[fault] for fault in SPEC_FAULTS)


def _error_pct(summary: dict[str, int]) -> float:
    # Older reports predate the error_infra label, so only the error labels present are summed.
    return _pct(sum(count for fault, count in summary.items() if fault in ERROR_FAULTS), sum(summary.values()))


def _phase_completed(iteration_dir: Path, task: str, phase: str) -> bool:
    checkpoint = iteration_dir / "stages" / task / "pipeline-checkpoints.tsv"
    return checkpoint.is_file() and any(
        line.split("\t")[:2] == [phase, "completed"] for line in checkpoint.read_text().splitlines()
    )


def iteration_rates(iteration_dir: Path, task: str) -> dict[str, dict[str, float]]:
    """Per direction this iteration finished classifying: its spec-fault percentage, the metric itself and,
    for the directions with a failure classification, the share of classified failures that were errors."""
    rates: dict[str, dict[str, float]] = {}
    log_dir = iteration_dir / "log" / task
    if _phase_completed(iteration_dir, task, "candidate-classify"):
        results = json.loads((iteration_dir / "executable" / task / f"{task}.eval.json").read_text())["test_results"]
        summary = json.loads((log_dir / "failure_attribution.json").read_text())["summary"]
        rates["acc"] = {
            "spec_fault_pct": _pct(_spec_count(summary), len(results)),
            "metric_pct": _pct(sum(item["status"] == "passed" for item in results), len(results)),
            "error_pct": _error_pct(summary),
        }
    if _phase_completed(iteration_dir, task, "generated-test-mutant-classify"):
        report = json.loads((log_dir / "mutant_attribution.json").read_text())
        result = TestSuiteEvaluationResult.model_validate(
            json.loads((iteration_dir / "mutant-eval" / "generated-test" / task / f"{task}.test_eval.json").read_text())
        )
        mutants = result.candidate_results
        # A direction this iteration skipped left no summary behind. Reporting it anyway would
        # read as a flawless direction and latch it converged on the strength of no evidence.
        if report["test_failure_summary"]:
            rates["validity_rate"] = {
                "spec_fault_pct": _pct(_spec_count(report["test_failure_summary"]), result.n_test_functions),
                "metric_pct": _pct(len(result.ground_truth_passing_test_names), result.n_test_functions),
                "error_pct": _error_pct(report["test_failure_summary"]),
            }
        if mutants:
            rates["mutation_score"] = {
                "spec_fault_pct": _pct(
                    sum(mutant["status"] in {"survived", "error"} and mutant["fault"] in SPEC_FAULTS for mutant in report["mutants"]),
                    len(mutants),
                ),
                "metric_pct": _pct(sum(bool(result.candidate_failing_ground_truth_passing_test_names(mutant)) for mutant in mutants), len(mutants)),
            }
    return rates


def direction_converged(rates: dict[str, float], metric: str, threshold_pct: float, min_metric_pct: float) -> bool:
    return rates["spec_fault_pct"] < threshold_pct and (metric not in GUARDED_METRICS or rates["metric_pct"] > min_metric_pct)


def convergence(iter_root: Path, task: str, threshold_pct: float, min_metric_pct: float, max_error_pct: float = 100.0) -> dict[str, Any]:
    """A direction converges once any iteration measured few spec faults (and, for guarded metrics, a
    non-trivial metric); it is never rerun after, so the per-iteration flags only ever latch on.
    Once any direction's classified failures were mostly errors (above max_error_pct), the task as a
    whole stops: every direction latches, since such failures carry no spec evidence worth iterating on."""
    numbers = sorted(int(path.name[5:]) for path in iter_root.glob("iter_*") if path.name[5:].isdigit())
    history = {number: rates for number in numbers if (rates := iteration_rates(iter_root / f"iter_{number}", task))}
    converged = dict.fromkeys(METRICS, False)
    error_stopped = False
    by_iteration: dict[int, dict[str, bool]] = {}
    for number, rates in history.items():
        error_stopped |= any(rates[metric]["error_pct"] > max_error_pct for metric in ("acc", "validity_rate") if metric in rates)
        for metric in METRICS:
            if metric in rates:
                converged[metric] |= direction_converged(rates[metric], metric, threshold_pct, min_metric_pct)
            converged[metric] |= error_stopped
        by_iteration[number] = dict(converged)
    return {
        "task": task,
        "threshold_pct": threshold_pct,
        "min_metric_pct": min_metric_pct,
        "max_error_pct": max_error_pct,
        "rates": history,
        "converged_by_iteration": by_iteration,
        "converged": converged,
        "error_stopped": error_stopped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iter-root", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--threshold", type=float, default=5.0, help="Spec-fault percentage below which a direction has converged")
    parser.add_argument("--min-metric", type=float, default=10.0, help="Accuracy or validity rate a direction must exceed before it can converge; mutation score is not guarded")
    parser.add_argument("--max-error", type=float, default=100.0, help="Error percentage among a direction's classified failures above which the whole task stops")
    parser.add_argument("--output", type=Path, help="Write the full report as JSON here")
    args = parser.parse_args(argv)
    report = convergence(args.iter_root, args.task, args.threshold, args.min_metric, args.max_error)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2))
    print(" ".join(f"{metric}={int(flag)}" for metric, flag in report["converged"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
