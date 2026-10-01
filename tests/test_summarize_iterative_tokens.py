from __future__ import annotations

import json
import logging
from pathlib import Path

from scripts.construction.summarize_iterative_tokens import collect_agent_routes, collect_usage, summary_rows
from programbench.mutants import _log_invalid_mutants
from programbench.test_generation import _write_codex_trajectory


TASK = "org__repo.1234567"


def _event(input_tokens: int, output_tokens: int) -> dict[str, object]:
    return {
        "type": "turn.completed",
        "usage": {
            "input_tokens": input_tokens,
            "cached_input_tokens": input_tokens // 2,
            "cache_write_input_tokens": 3,
            "output_tokens": output_tokens,
            "reasoning_output_tokens": 2,
        },
    }


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def test_collect_usage_groups_steps_and_does_not_count_trajectory_copies(tmp_path: Path) -> None:
    event = _event(100, 20)
    _write(
        tmp_path / "batch" / "trajectories" / "spec" / f"{TASK}.traj.json",
        {
            "codex_events": [event],
            "codex_json_events": [event],
            "codex_output": {"stdout": json.dumps(event)},
        },
    )
    # Immutable stage snapshots contain a copy of generated-test trajectories;
    # only the canonical generated-test path should be counted.
    generated = {
        "usage": {
            "input_tokens": 200,
            "cached_input_tokens": 50,
            "output_tokens": 30,
        },
        "usage_calls": 1,
        "codex_events": [_event(999, 999)],
    }
    canonical = tmp_path / "iter_1" / "generated-test" / TASK / f"{TASK}.traj.json"
    _write(canonical, generated)
    _write(
        tmp_path / "iter_1" / "stages" / "generated-test-mutant-evaluation" / "generated-test" / TASK / canonical.name,
        generated,
    )

    _write(
        tmp_path / "iter_1" / "log" / TASK / "mutant_attribution.json",
        {
            "classifier_usage": {
                "batches": [
                    {"phase": "generated_test_failure_classification", "usage": _event(400, 50)["usage"]},
                    {"phase": "mutant_classification", "usage": _event(500, 60)["usage"]},
                ]
            }
        },
    )

    totals, calls = collect_usage(tmp_path, {TASK})

    assert calls[(TASK, 0, "improve-spec")] == 1
    assert totals[(TASK, 0, "improve-spec")]["total_tokens"] == 120
    assert totals[(TASK, 0, "improve-spec")]["cache_write_input_tokens"] == 3
    assert calls[(TASK, 1, "generated-test-generation")] == 1
    assert totals[(TASK, 1, "generated-test-generation")]["total_tokens"] == 230
    assert totals[(TASK, 1, "generated-test-failure-classification")]["total_tokens"] == 450
    assert totals[(TASK, 1, "mutant-classification")]["total_tokens"] == 560

    rows = summary_rows(totals, calls)
    grand_total = next(row for row in rows if row["scope"] == "grand_total")
    classifier_total = next(
        row
        for row in rows
        if row["scope"] == "step_total" and row["step"] == "mutant-classification"
    )
    assert classifier_total["iteration"] == "ALL"
    assert classifier_total["total_tokens"] == 560
    assert grand_total["calls"] == 4
    assert grand_total["input_tokens"] == 1200
    assert grand_total["output_tokens"] == 160
    assert grand_total["total_tokens"] == 1360


def test_collect_usage_reads_new_explicit_repair_usage_without_stdout(tmp_path: Path) -> None:
    _write(
        tmp_path / "batch" / "mutant-validation" / "initial" / TASK / "mutant_kill_validation.json",
        {
            "attempts": [{
                "repair": {
                    "returncode": 0,
                    "usage": {"input_tokens": 70, "cached_input_tokens": 20, "output_tokens": 8},
                    "usage_calls": 1,
                }
            }]
        },
    )

    totals, calls = collect_usage(tmp_path, {TASK})

    key = (TASK, 0, "ensure-mutants-killed-repair")
    assert calls[key] == 1
    assert totals[key]["input_tokens"] == 70
    assert totals[key]["output_tokens"] == 8
    assert totals[key]["total_tokens"] == 78


def test_trajectory_writer_records_canonical_usage(tmp_path: Path) -> None:
    path = tmp_path / "traj.json"

    _write_codex_trajectory(
        path=path,
        instance_id=TASK,
        prompt="do the work",
        events=[_event(90, 9)],
        status={
            "status": "invalid_mutants",
            "returncode": 0,
            "invalid_mutants": {"repo_7": ["executable: missing after agent-side build validation"]},
        },
        info={"task": "test"},
    )

    payload = json.loads(path.read_text())
    assert payload["usage_calls"] == 1
    assert payload["usage"]["input_tokens"] == 90
    assert payload["usage"]["output_tokens"] == 9
    assert payload["usage"]["total_tokens"] == 99
    assert payload["info"]["invalid_mutants"] == {
        "repo_7": ["executable: missing after agent-side build validation"]
    }


def test_invalid_mutant_logger_reports_every_reason(caplog) -> None:
    caplog.set_level(logging.ERROR, logger="programbench.mutants")

    _log_invalid_mutants(
        TASK,
        {
            "repo_2": ["executable: missing after agent-side build validation"],
            "repo_1": ["build.sh: references '/workspace/executable'", "metadata is incomplete"],
        },
    )

    assert caplog.messages == [
        f"{TASK}: invalid mutant repo_1: build.sh: references '/workspace/executable'",
        f"{TASK}: invalid mutant repo_1: metadata is incomplete",
        f"{TASK}: invalid mutant repo_2: executable: missing after agent-side build validation",
    ]


def test_summary_rows_follow_pipeline_step_order() -> None:
    keys = [
        (TASK, 1, "generated-test-spec-polish"),
        (TASK, 1, "candidate-spec-polish"),
        (TASK, 1, "candidate-solve"),
        (TASK, 1, "generated-test-generation"),
    ]
    totals = {key: {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2} for key in keys}
    calls = {key: 1 for key in keys}

    rows = [row for row in summary_rows(totals, calls) if row["scope"] == "detail"]

    assert [row["step"] for row in rows] == [
        "candidate-solve",
        "candidate-spec-polish",
        "generated-test-generation",
        "generated-test-spec-polish",
    ]


def test_invocation_routes_are_resolved_per_task(tmp_path: Path) -> None:
    _write(
        tmp_path / "iter_1" / "log" / TASK / "failure_attribution.json",
        {"classifier_usage": {"batches": [{"phase": "failure_classification", "usage": {"input_tokens": 5}}]}},
    )
    run_dir = tmp_path / "batch" / "runs" / "run-a"
    run_dir.mkdir(parents=True)
    (run_dir / "tasks.started.txt").write_text(f"{TASK}\n")
    (run_dir / "agent-routes.tsv").write_text(
        "step\tmodel\treasoning\tretry_model\tretry_reasoning\n"
        "classify_failures\trun-model\thigh\trun-model\thigh\n"
    )

    totals, _ = collect_usage(tmp_path, {TASK})
    routes = collect_agent_routes(tmp_path, {TASK}, totals)

    assert routes[(TASK, 1, "candidate-failure-classification")] == {("run-model", "high")}


def test_summary_rows_include_actual_and_configured_agent_routes(tmp_path: Path) -> None:
    _write(
        tmp_path / "iter_1" / "generated-test" / TASK / f"{TASK}.traj.json",
        {
            "info": {
                "model": "actual-model",
                "codex_shell_command": "codex exec --config model_reasoning_effort=high",
            },
            "usage": {"input_tokens": 10, "output_tokens": 2},
        },
    )
    _write(
        tmp_path / "iter_1" / "log" / TASK / "failure_attribution.json",
        {
            "classifier_usage": {
                "batches": [{"phase": "failure_classification", "usage": {"input_tokens": 5}}]
            }
        },
    )
    route_path = tmp_path / "agent-routes" / f"{TASK}.tsv"
    route_path.parent.mkdir(parents=True)
    route_path.write_text(
        "step\tmodel\treasoning\tretry_model\tretry_reasoning\n"
        "generate_tests\tconfigured-model\tlow\tconfigured-model\tlow\n"
        "classify_failures\tclassifier-model\tmedium\tclassifier-model\tmedium\n"
    )

    totals, calls = collect_usage(tmp_path, {TASK})
    routes = collect_agent_routes(tmp_path, {TASK}, totals)
    rows = summary_rows(totals, calls, routes)

    generated = next(
        row for row in rows if row["scope"] == "detail" and row["step"] == "generated-test-generation"
    )
    classifier = next(
        row
        for row in rows
        if row["scope"] == "detail" and row["step"] == "candidate-failure-classification"
    )
    task_total = next(row for row in rows if row["scope"] == "task_total")
    assert (generated["model"], generated["reasoning"]) == ("actual-model", "high")
    assert (classifier["model"], classifier["reasoning"]) == ("classifier-model", "medium")
    assert task_total["model"] == "actual-model;classifier-model"
    assert task_total["reasoning"] == "high;medium"
