from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_summarizer():
    path = Path(__file__).resolve().parents[1] / "scripts" / "eval" / "summarize_agent_runs.py"
    spec = importlib.util.spec_from_file_location("summarize_agent_runs", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["summarize_agent_runs"] = module
    spec.loader.exec_module(module)
    return module


def test_tokens_are_normalized_per_agent_family():
    s = load_summarizer()
    assert s.tokens("claude", {"input_tokens": 10, "cache_creation_input_tokens": 90, "cache_read_input_tokens": 500, "output_tokens": 7}) == (100, 500, 7)
    assert s.tokens("deepseek", {"input_tokens": 10, "cache_creation_input_tokens": 90, "cache_read_input_tokens": 500, "output_tokens": 7}) == (100, 500, 7)
    assert s.tokens("gemini", {"input": 100, "cached": 900, "input_tokens": 1000, "output_tokens": 7}) == (100, 900, 7)
    assert s.tokens("qwen", {"input_tokens": 1000, "cache_read_input_tokens": 800, "output_tokens": 7}) == (200, 800, 7)
    assert s.tokens("codex", {"input_tokens": 1000, "cached_input_tokens": 600, "output_tokens": 7}) == (400, 600, 7)
    assert s.tokens("muse", {"input_tokens": 1000, "cached_tokens": 300, "output_tokens": 7, "reasoning_tokens": 1}) == (700, 300, 7)
    assert s.tokens("muse", {}) == ("", "", "")


def test_rows_combine_trajectories_results_and_timings(tmp_path):
    s = load_summarizer()
    task, label = "x__y.1234567", "gemini-3.8-flash_high"
    solve_dir = tmp_path / "codegen" / label / task
    tests_dir = tmp_path / "testgen" / label / task
    timings_dir = tmp_path / "timings" / label
    for d in (solve_dir, tests_dir, timings_dir):
        d.mkdir(parents=True)
    (solve_dir / "traj.json").write_text(json.dumps({
        "info": {"agent": "gemini", "model": "gemini-3.8-flash", "reasoning": "high", "duration_seconds": 300, "exit_status": "ok"},
        "usage": {"input": 100, "cached": 900, "input_tokens": 1000, "output_tokens": 50, "total_tokens": 1050},
        "usage_calls": 2,
        "messages": [{"role": "assistant", "tool_calls": [{"name": "shell"}]}],
        "agent_json_events": [{}, {}],
    }))
    (solve_dir / f"{task}.eval.json").write_text(json.dumps({"test_results": [
        {"name": "t1", "branch": "b", "status": "passed", "extra": {}},
        {"name": "t2", "branch": "b", "status": "failure", "extra": {}},
    ]}))
    (tests_dir / f"{task}.traj.json").write_text(json.dumps({
        "info": {"agent": "gemini", "model": "gemini-3.8-flash", "reasoning": "high", "duration_seconds": 120, "exit_status": "ok"},
        "usage": {"input": 10, "cached": 20, "input_tokens": 30, "output_tokens": 5},
        "usage_calls": 1, "messages": [], "agent_json_events": [{}],
    }))
    results = lambda ok: [{"name": "g1", "branch": "generated", "status": "passed" if ok else "failure", "extra": {}}]
    (tests_dir / f"{task}.test_eval.json").write_text(json.dumps({"binary_results": [
        {"binary_id": "ground_truth", "role": "ground_truth", "test_results": results(True)},
        {"binary_id": "m1", "role": "candidate", "test_results": results(False)},
        {"binary_id": "m2", "role": "candidate", "test_results": results(True)},
    ]}))
    (timings_dir / f"{task}.seconds").write_text("Command exited with non-zero status 1\n1800.25\n")

    row = s.rows(tmp_path, None, None, {task: {}})[0]
    record = dict(zip(s.COLUMNS, row, strict=True))

    assert record["Task"] == task
    assert record["Run"] == label
    assert record["Agent"] == "gemini"
    assert record["Model"] == "gemini-3.8-flash"
    assert record["Reasoning"] == "high"
    assert record["Codegen Status"] == record["Testgen Status"] == "ok"
    assert (record["Exec Acc"], record["Test Validity Rate"], record["Test Mutation Score"]) == ("50.0", "100.0", "50.0")
    assert record["Wall Time [m]"] == "30.0"
    assert (record["codegen_messages"], record["codegen_steps"], record["codegen_events"]) == (1, 1, 2)
    assert (record["codegen_input"], record["codegen_cached_input"], record["codegen_output"]) == (100, 900, 50)
    assert record["codegen_total_tokens"] == 1050
    assert record["codegen_calls"] == 2
    assert record["codegen_time"] == "5.0"
    assert record["testgen_time"] == "2.0"
    assert record["Agent Time [m]"] == "7.0"
    assert record["codegen_trajectory"].endswith("/traj.json")
    assert record["codegen_raw_stdout"] == ""
    assert len(s.COLUMNS) == len(row)


def test_merge_rows_uses_first_successful_phase_in_root_priority_order():
    s = load_summarizer()

    def row(root, task, run, **fields):
        result = [""] * len(s.COLUMNS)
        values = {"Root": root, "Task": task, "Run": run, **fields}
        for field, value in values.items():
            result[s.COLUMNS.index(field)] = value
        return result

    preferred = row(
        "v6", "task-a", "model_medium",
        **{
            "Agent": "codex", "Model": "new-model", "Reasoning": "medium",
            "Codegen Status": "not_run", "Testgen Status": "failed",
            "Test Validity Rate": "10", "testgen_time": "2.0", "testgen_trajectory": "v6/testgen.json",
        },
    )
    fallback = row(
        "v3", "task-a", "model_medium",
        **{
            "Agent": "codex", "Model": "old-model", "Reasoning": "medium",
            "Codegen Status": "ok", "Testgen Status": "ok", "Exec Acc": "80",
            "Test Validity Rate": "90", "codegen_time": "3.0", "testgen_time": "4.0",
            "codegen_trajectory": "v3/codegen.json", "testgen_trajectory": "v3/testgen.json",
        },
    )
    fallback_only = row(
        "v3", "task-b", "model_medium",
        **{"Codegen Status": "ok", "Testgen Status": "not_run", "Exec Acc": "70"},
    )

    merged = s.merge_rows_by_root_priority([preferred, fallback, fallback_only])
    first = dict(zip(s.COLUMNS, merged[0], strict=True))

    assert len(merged) == 2
    assert first["Root"] == "v6"
    assert first["Model"] == "new-model"
    assert first["Codegen Status"] == "ok"
    assert first["Exec Acc"] == "80"
    assert first["codegen_trajectory"] == "v3/codegen.json"
    assert first["Testgen Status"] == "ok"
    assert first["Test Validity Rate"] == "90"
    assert first["testgen_trajectory"] == "v3/testgen.json"
    assert first["Agent Time [m]"] == "7.0"
    assert merged[1] == fallback_only


def test_prioritize_rows_keeps_entire_first_matching_row():
    s = load_summarizer()

    def row(root, task, run, status):
        result = [""] * len(s.COLUMNS)
        for field, value in {
            "Root": root, "Task": task, "Run": run, "Codegen Status": status,
        }.items():
            result[s.COLUMNS.index(field)] = value
        return result

    v6 = row("v6", "task-a", "model_medium", "failed")
    v4_duplicate = row("v4", "task-a", "model_medium", "ok")
    v4_only = row("v4", "task-b", "model_medium", "ok")
    v3_other_run = row("v3", "task-a", "other_model_medium", "ok")

    assert s.prioritize_rows([v6, v4_duplicate, v4_only, v3_other_run]) == [
        v6, v4_only, v3_other_run,
    ]


def test_pretty_execution_result_uses_all_top_level_statuses(tmp_path):
    s = load_summarizer()
    path = tmp_path / "result.json"
    path.write_text(json.dumps({"test_results": [
        {"name": "a", "status": "passed", "extra": {"status": "failure"}},
        {"name": "b", "status": "failure", "extra": {}},
    ]}, indent=2))

    assert s.execution_accuracy(path) == 0.5


def test_histograms_write_one_nine_panel_pdf_per_run(tmp_path):
    s = load_summarizer()
    row = [""] * len(s.COLUMNS)
    row[s.COLUMNS.index("Run")] = "agent/model_high"
    row[s.COLUMNS.index("Exec Acc")] = "50.0"
    row[s.COLUMNS.index("Test Validity Rate")] = "75.0"
    row[s.COLUMNS.index("Test Mutation Score")] = "25.0"

    s.write_histograms([row], tmp_path)

    document = tmp_path / "agent_model_high.pdf"
    assert document.read_bytes().startswith(b"%PDF-")
    assert list(tmp_path.glob("*.pdf")) == [document]


def test_histogram_labels_and_resource_scales_match_publication_figures():
    s = load_summarizer()

    assert s.SCORE_TITLES == {
        "Exec Acc": "Reference Pass Rate",
        "Test Validity Rate": "Validity Rate",
        "Test Mutation Score": "Mutation Score",
    }
    assert s.RESOURCE_LIMITS == {"Cost": (0, 30), "Time": (0, 100), "Steps": (0, 400)}


def test_histogram_colors_match_stats_model_palette():
    s = load_summarizer()

    assert s.model_histogram_color("gpt-5.6-sol") == "#b45f06"
    assert s.model_histogram_color("gemini-3.8-flash") == "#2369a1"
    assert s.model_histogram_color("claude-opus-5") == "#39834b"
    assert s.model_histogram_color("deepseek/deepseek-v4-flash") == "#8856a7"
    assert s.model_histogram_color("unknown-model") == "#777777"


def test_histograms_add_merged_density_for_headline_models(tmp_path):
    s = load_summarizer()
    table = []
    models = {
        "gpt-5.6-sol_medium": "gpt-5.6-sol",
        "gemini-3.8-flash_medium": "gemini-3.8-flash",
        "opus_high": "claude-opus-5",
        "deepseek-deepseek-v4-flash_high": "deepseek/deepseek-v4-flash",
    }
    for run, model in models.items():
        for score in (40, 60):
            row = [""] * len(s.COLUMNS)
            for field, value in {
                "Run": run, "Model": model,
                "Exec Acc": score, "Test Validity Rate": score + 5, "Test Mutation Score": score - 5,
                "codegen_time": score / 10, "codegen_steps": score,
                "testgen_time": score / 20, "testgen_steps": score / 2,
            }.items():
                row[s.COLUMNS.index(field)] = value
            table.append(row)

    s.write_histograms(table, tmp_path)

    for name in ("merged_density.pdf", "merged_cumulative.pdf"):
        assert (tmp_path / name).read_bytes().startswith(b"%PDF-")


def test_ecdf_points_include_ties_and_respect_plot_limits():
    s = load_summarizer()
    x, y = s.ecdf_points([0, 10, 10, 200], (0, 100))
    assert list(x) == [0, 10, 10, 100]
    assert list(y) == [0.25, 0.75, 0.75, 0.75]


def test_combined_histograms_use_phase_metrics_and_model_prices(tmp_path):
    s = load_summarizer()
    row = [""] * len(s.COLUMNS)
    values = {
        "Run": "agent/model_high", "Model": "model-a",
        "codegen_input": 1_000_000, "codegen_cached_input": 500_000, "codegen_output": 100_000,
        "codegen_time": "5.0", "codegen_steps": 8,
        "testgen_input": 100_000, "testgen_cached_input": 0, "testgen_output": 10_000,
        "testgen_time": "2.0", "testgen_steps": 3,
    }
    for field, value in values.items():
        row[s.COLUMNS.index(field)] = value
    pricing = tmp_path / "prices.json"
    pricing.write_text(json.dumps({"model-a": {"input": 2, "cached_input": 0.5, "output": 10}}))
    prices = s.load_prices(pricing)

    assert s.phase_cost(row, "codegen", prices) == 3.25
    assert s.phase_cost(row, "testgen", prices) == 0.3
    s.write_histograms([row], tmp_path, prices)
    assert (tmp_path / "agent_model_high.pdf").read_bytes().startswith(b"%PDF-")
    assert len(list(tmp_path.glob("*.pdf"))) == 1



def test_model_summary_averages_available_values_and_writes_requested_columns(tmp_path):
    s = load_summarizer()
    def row(**fields):
        result = [""] * len(s.COLUMNS)
        for field, value in fields.items():
            result[s.COLUMNS.index(field)] = value
        return result

    table = [
        row(Model="gpt-5.6-sol", Task="task-a", **{
            "Codegen Status": "ok", "Testgen Status": "ok",
            "Exec Acc": "80", "Test Validity Rate": "90", "Test Mutation Score": "30",
            "codegen_input": 1_000_000, "codegen_cached_input": 0, "codegen_output": 0,
            "codegen_steps": 2, "codegen_time": "4.0",
            "testgen_input": 0, "testgen_cached_input": 0, "testgen_output": 1_000_000,
            "testgen_steps": 3, "testgen_time": "5.0",
        }),
        row(Model="gpt-5.6-sol", Task="task-b", **{
            "Codegen Status": "ok", "Testgen Status": "not_run",
            "Exec Acc": "100", "Test Validity Rate": "", "Test Mutation Score": "50",
            "codegen_input": 3_000_000, "codegen_cached_input": 0, "codegen_output": 0,
            "codegen_steps": 4, "codegen_time": "6.0",
        }),
    ]
    output = tmp_path / "summary.tsv"
    s.write_model_summary(table, output, {"gpt-5.6-sol": {"input": 1, "cached_input": 0.1, "output": 2}})
    lines = output.read_text().splitlines()
    assert lines[0] == "Model\tReasoning\tVR\tMS\tCost [$]\tSteps\tTime [m]\tRPR\tCost [$]\tSteps\tTime [m]\tnum fully done"
    assert lines[1] == "GPT 5.6 Sol\t\t90.0\t40.0\t2.00\t3.0\t5.0\t90.0\t2.00\t3.0\t5.0\t1/165"


def test_missing_trajectory_is_reported_instead_of_dropping_run(tmp_path):
    s = load_summarizer()
    task, label = "x__y.1234567", "gpt-5.6-luna_medium"
    phase = tmp_path / "testgen" / label / task
    phase.mkdir(parents=True)
    (phase / "tests.tar.gz").write_bytes(b"not important")
    (phase / f"{task}.traj.raw.stdout.jsonl").write_text("55\n")

    row = s.rows(tmp_path, None, None, {})[0]
    record = dict(zip(s.COLUMNS, row, strict=True))

    assert record["Task"] == task
    assert record["Codegen Status"] == "not_run"
    assert record["Testgen Status"] == "trajectory_missing"
    assert record["Reasoning"] == "medium"
    assert record["testgen_trajectory"].endswith(f"/{task}.traj.json")
    assert record["testgen_raw_stdout"].endswith(f"/{task}.traj.raw.stdout.jsonl")
    assert record["testgen_artifact"].endswith("/tests.tar.gz")


def test_incomplete_json_keeps_run_and_marks_unavailable_metrics(tmp_path, capsys):
    s = load_summarizer()
    task, label = "x__y.1234567", "gpt-6-astra_medium"
    solve_dir = tmp_path / "codegen" / label / task
    tests_dir = tmp_path / "testgen" / label / task
    solve_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    (solve_dir / "traj.json").write_text('{"info":')
    (solve_dir / f"{task}.eval.json").write_text('{"test_results": [')
    (tests_dir / f"{task}.traj.json").write_text("")
    (tests_dir / f"{task}.test_eval.json").write_text('{"binary_results": [')

    row = s.rows(tmp_path, None, None, {}, workers=1)[0]
    record = dict(zip(s.COLUMNS, row, strict=True))

    assert record["Codegen Status"] == "trajectory_invalid"
    assert record["Testgen Status"] == "trajectory_invalid"
    assert record["Exec Acc"] == record["Test Validity Rate"] == record["Test Mutation Score"] == ""
    assert record["codegen_trajectory"].endswith("/traj.json")
    assert record["testgen_trajectory"].endswith(f"/{task}.traj.json")
    errors = capsys.readouterr().err
    assert "incomplete or invalid JSON" in errors
    assert str(solve_dir / "traj.json") in errors
    assert str(tests_dir / f"{task}.test_eval.json") in errors


def test_model_summary_separates_and_orders_reasoning_levels():
    s = load_summarizer()
    table = []
    for effort, score in [("high", "80"), ("low", "20"), ("high", "100")]:
        row = [""] * len(s.COLUMNS)
        for field, value in {"Model": "gpt-5.6-sol", "Reasoning": effort, "Test Validity Rate": score}.items():
            row[s.COLUMNS.index(field)] = value
        table.append(row)
    summary = s.model_summary_rows(table, {})
    assert [row[:3] for row in summary] == [
        ["GPT 5.6 Sol", "low", "20.0"], ["GPT 5.6 Sol", "high", "90.0"],
    ]


def test_output_automatically_writes_aggregated_sibling(tmp_path, monkeypatch):
    s = load_summarizer()
    output = tmp_path / "wip_score.tsv"
    monkeypatch.setattr(s, "load_all_instances", lambda: [])
    monkeypatch.setattr(s, "rows", lambda *args: [])
    monkeypatch.setattr(s, "load_prices", lambda path: {})
    monkeypatch.setattr(sys, "argv", ["summarize_agent_runs.py", str(tmp_path), "--output", str(output)])
    s.main()
    assert output.is_file()
    assert (tmp_path / "wip_score_aggregated.tsv").read_text().strip() == "\t".join(s.MODEL_SUMMARY_COLUMNS)
