#!/usr/bin/env python3
"""Write analysis-ready TSV rows from one or more agent evaluation output roots.

The TSV contains scalar metrics and paths to the complete JSON trajectories. A
missing trajectory is emitted as a visible status instead of dropping the run.
With --output, a sibling <stem>_aggregated.tsv summarizes each model and reasoning
level; --model-summary overrides its path. Means exclude missing values.
When multiple roots contain the same task/run, each phase uses the first
successful result in root priority order. If none succeeded, the highest-priority
attempt is retained; not_run is used only when no root attempted the phase.

For resource histogram costs, --pricing-file accepts a JSON object keyed by
model name. Each model needs input, cached_input, and output rates in USD per
million tokens, for example {"my-model": {"input": 1, "cached_input": 0.1,
"output": 4}}.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from multiprocessing import get_context
from pathlib import Path
from statistics import fmean, median
from typing import Any

import ijson

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from programbench.skipped_mutants import load_skipped_mutants
from programbench.skipped_tests import load_skipped_tests, normalize_test_function_names, test_function_name
from programbench.utils.load_data import get_ignored_tests, load_all_instances

_RESULT_STATUS_LINE = re.compile(
    rb"(?m)^ {6}\"status\": \"(passed|skipped|failure|error|system_error|not_run)\""
)

COLUMNS = [
    "Root", "Task", "Run", "Agent", "Model", "Reasoning",
    "Codegen Status", "Testgen Status", "Exec Acc", "Test Validity Rate", "Test Mutation Score", "Wall Time [m]",
    "codegen_messages", "codegen_steps", "codegen_events",
    "codegen_input", "codegen_cached_input", "codegen_output", "codegen_reasoning", "codegen_total_tokens",
    "codegen_calls", "codegen_time", "codegen_trajectory", "codegen_raw_stdout", "codegen_raw_stderr", "codegen_artifact",
    "testgen_messages", "testgen_steps", "testgen_events",
    "testgen_input", "testgen_cached_input", "testgen_output", "testgen_reasoning", "testgen_total_tokens",
    "testgen_calls", "testgen_time", "testgen_trajectory", "testgen_raw_stdout", "testgen_raw_stderr", "testgen_artifact",
    "Agent Time [m]",
]


def agent_kind(info: dict[str, Any]) -> str:
    if "agent" in info:
        return str(info["agent"])
    for key in ("claude", "codex", "gemini", "muse", "qwen", "deepseek", "glm"):
        if f"{key}_command" in info:
            return key
    return ""


# Uncached input, cached input, output. Claude bills cache writes as input;
# OpenAI-style counters include the cached part in input.
def tokens(kind: str, usage: dict[str, Any]) -> tuple[int, int, int] | tuple[str, str, str]:
    if "input_tokens" not in usage:
        return "", "", ""
    if kind in ("claude", "deepseek"):
        return (
            usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0),
            usage.get("cache_read_input_tokens", 0),
            usage.get("output_tokens", 0),
        )
    if kind == "gemini":
        return usage.get("input", usage["input_tokens"]), usage.get("cached", 0), usage.get("output_tokens", 0)
    cached = usage.get("cached_tokens", 0) if kind == "muse" else usage.get(
        "cache_read_input_tokens", usage.get("cached_input_tokens", 0)
    )
    return usage["input_tokens"] - cached, cached, usage.get("output_tokens", 0)


def token_details(kind: str, usage: dict[str, Any]) -> tuple[Any, Any, Any, Any, Any]:
    uncached, cached, output = tokens(kind, usage)
    if uncached == "":
        return "", "", "", "", ""
    reasoning = usage.get("reasoning_output_tokens", usage.get("reasoning_tokens", usage.get("thoughts_tokens", "")))
    total = usage.get("total_tokens")
    if total is None:
        total = int(uncached) + int(cached) + int(output)
    return uncached, cached, output, reasoning, total


def model_name(trajectory: dict[str, Any]) -> str:
    # Claude records an alias (for example "opus"); its init event names the served model.
    init = next((e for e in trajectory.get("claude_json_events", []) if e.get("type") == "system"), {})
    return str(init.get("model") or trajectory.get("info", {}).get("model", ""))


def minutes(seconds: float | str) -> str:
    return f"{float(seconds) / 60:.1f}" if seconds != "" else ""


def step_time(trajectory: dict[str, Any] | None) -> str:
    duration = (trajectory or {}).get("info", {}).get("duration_seconds", "")
    return minutes(duration)


def total_time(root: Path, label: str, task: str) -> str:
    path = root / "timings" / label / f"{task}.seconds"
    if not path.is_file():
        return ""
    # GNU time prefixes failed commands with a diagnostic before the formatted
    # elapsed value. Read the last numeric line so failed runs remain reportable.
    for line in reversed(path.read_text().splitlines()):
        try:
            return minutes(line.strip())
        except ValueError:
            continue
    return ""


def _first_json_item(path: Path, prefix: str, default: Any) -> Any:
    with path.open("rb") as handle:
        return next(ijson.items(handle, prefix), default)


def load_trajectory_summary(path: Path) -> dict[str, Any] | None:
    """Read report fields without materializing complete trajectories."""
    if not path.is_file():
        return None
    info = _first_json_item(path, "info", {})
    usage = _first_json_item(path, "usage", {})
    usage_calls = _first_json_item(path, "usage_calls", "")
    result: dict[str, Any] = {"info": info, "usage": usage, "usage_calls": usage_calls}

    message_count = tool_count = 0
    with path.open("rb") as handle:
        for message in ijson.items(handle, "messages.item"):
            message_count += 1
            calls = message.get("tool_calls", []) if isinstance(message, dict) else []
            tool_count += len(calls) if isinstance(calls, list) else 0
    result["messages"] = [{}] * message_count
    result["_tool_step_count"] = tool_count

    kind = agent_kind(info)
    event_keys = (
        ("claude_json_events",) if kind == "claude"
        else ("codex_events", "codex_json_events") if kind == "codex"
        else ("agent_json_events",)
    )
    event_count_value = 0
    claude_system: dict[str, Any] | None = None
    for key in event_keys:
        with path.open("rb") as handle:
            for event in ijson.items(handle, f"{key}.item"):
                event_count_value += 1
                if key == "claude_json_events" and claude_system is None and event.get("type") == "system":
                    claude_system = {"type": "system", "model": event.get("model", "")}
    result["_event_count"] = event_count_value
    if claude_system:
        result["claude_json_events"] = [claude_system]
    return result


def percent(value: float | None) -> str:
    return "" if value is None else f"{value * 100:.1f}"


def reasoning_name(trajectory: dict[str, Any], label: str) -> str:
    info = trajectory.get("info", {})
    value = info.get("reasoning") or info.get("effort")
    if value:
        return str(value)
    for effort in ("ultra", "xhigh", "medium", "high", "low", "max"):
        if label.endswith(f"_{effort}"):
            return effort
    return ""


def event_count(trajectory: dict[str, Any]) -> int:
    if "_event_count" in trajectory:
        return trajectory["_event_count"]
    return sum(len(value) for key, value in trajectory.items() if key.endswith("events") and isinstance(value, list))


def tool_step_count(trajectory: dict[str, Any]) -> int:
    if "_tool_step_count" in trajectory:
        return trajectory["_tool_step_count"]
    return sum(
        len(message.get("tool_calls", []))
        for message in trajectory.get("messages", [])
        if isinstance(message, dict) and isinstance(message.get("tool_calls", []), list)
    )


def execution_accuracy(path: Path) -> float | None:
    if not path.is_file():
        return None
    passed = total = 0
    if path.stat().st_size:
        overlap = 128
        buffer = b""
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                data = buffer + chunk
                cutoff = max(0, len(data) - overlap)
                for match in _RESULT_STATUS_LINE.finditer(data):
                    if match.start() >= cutoff:
                        break
                    total += 1
                    passed += match.group(1) == b"passed"
                buffer = data[cutoff:]
        for match in _RESULT_STATUS_LINE.finditer(buffer):
            total += 1
            passed += match.group(1) == b"passed"
    if not total:
        # Compact and externally produced JSON may not use the standard two-space indentation.
        with path.open("rb") as handle:
            for status in ijson.items(handle, "test_results.item.status"):
                total += 1
                passed += status == "passed"
    return passed / total if total else 0.0


def _subtest_parent(test_name: str) -> str | None:
    parent, separator, suffix = test_name.rpartition(" (")
    return parent if separator and suffix.endswith(")") else None


def _matrix_status(statuses: dict[str, str], test_name: str) -> str | None:
    status = statuses.get(test_name)
    if status is not None:
        return status
    parent = _subtest_parent(test_name)
    return statuses.get(parent) if parent is not None else None


def _selected_items(path: Path, prefix: str) -> list[Any]:
    with path.open("rb") as handle:
        return list(ijson.items(handle, prefix))


def _binary_summaries(path: Path, prefix: str, ignored_tests: set[str]) -> list[dict[str, Any]]:
    ids = _selected_items(path, f"{prefix}.item.binary_id")
    roles = _selected_items(path, f"{prefix}.item.role")
    errors = _selected_items(path, f"{prefix}.item.error_code")
    test_groups = _selected_items(path, f"{prefix}.item.test_results")
    if not roles:
        roles = ["ground_truth"] * len(ids)
    if not errors:
        errors = [None] * len(ids)
    if not (len(ids) == len(roles) == len(errors) == len(test_groups)):
        with path.open("rb") as handle:
            objects = list(ijson.items(handle, f"{prefix}.item"))
        ids = [binary.get("binary_id", "") for binary in objects]
        roles = [binary.get("role", "ground_truth") for binary in objects]
        errors = [binary.get("error_code") for binary in objects]
        test_groups = [binary.get("test_results", []) for binary in objects]
    result = []
    for binary_id, role, error_code, tests in zip(ids, roles, errors, test_groups, strict=True):
        statuses = {
            str(test.get("name", "")): str(test.get("status", ""))
            for test in tests
            if test_function_name(str(test.get("name", ""))) not in ignored_tests
        }
        result.append({"binary_id": binary_id, "role": role, "error_code": error_code, "tests": statuses})
    return result


def test_suite_metrics(
    path: Path, ignored_tests: set[str], ignored_mutants: set[str]
) -> tuple[float | None, float | None]:
    """Stream the result matrix while discarding its potentially huge logs."""
    if not path.is_file():
        return None, None
    ignored_tests = normalize_test_function_names(ignored_tests)
    binaries = _binary_summaries(path, "binary_results", ignored_tests)
    trials = _binary_summaries(path, "ground_truth_trials", ignored_tests)
    top_errors = _selected_items(path, "error_code")
    top_error = top_errors[0] if top_errors else None

    binaries = [binary for binary in binaries if binary["binary_id"] not in ignored_mutants]
    ground_truth = trials or [binary for binary in binaries if binary["role"] == "ground_truth"]
    usable = [binary for binary in ground_truth if binary["error_code"] is None and binary["tests"]]
    test_names = sorted({name for binary in usable for name in binary["tests"]})
    flaky = {
        name for name in test_names
        if len({_matrix_status(binary["tests"], name) == "passed" for binary in usable}) > 1
    }
    passing = {
        name for name in test_names
        if name not in flaky and all(_matrix_status(binary["tests"], name) == "passed" for binary in usable)
    }
    validity_rate = 0.0 if top_error or not usable or not test_names else len(passing) / len(test_names)
    candidates = [binary for binary in binaries if binary["role"] == "candidate"]
    if not candidates:
        mutation_score = None
    else:
        plain_passing = {name for name in passing if _subtest_parent(name) is None}
        subtest_passing = [(name, _subtest_parent(name)) for name in passing - plain_passing]
        killed = 0
        for binary in candidates:
            passed = {name for name, status in binary["tests"].items() if status == "passed"}
            killed += (
                binary["error_code"] is None
                and (
                    not plain_passing.issubset(passed)
                    or any(name not in passed and parent not in passed for name, parent in subtest_passing)
                )
            )
        mutation_score = killed / len(candidates)
    return validity_rate, mutation_score


@lru_cache(maxsize=None)
def skipped_for_task(skipped_tests: str | None, skipped_mutants: str | None, task: str) -> tuple[set[str], set[str]]:
    return load_skipped_tests(skipped_tests, task=task), load_skipped_mutants(skipped_mutants, task=task)


def phase_fields(
    trajectory: dict[str, Any] | None, path: Path, artifact: Path, exists: bool, kind: str
) -> list[Any]:
    stem = path.with_suffix("")
    raw_stdout = Path(f"{stem}.raw.stdout.jsonl")
    raw_stderr = Path(f"{stem}.raw.stderr.txt")
    paths = [
        str(path) if path.is_file() or exists else "",
        str(raw_stdout) if raw_stdout.is_file() else "",
        str(raw_stderr) if raw_stderr.is_file() else "",
        str(artifact) if artifact.is_file() else "",
    ]
    if trajectory is None:
        return ["", "", "", "", "", "", "", "", "", "", *paths]
    usage = trajectory.get("usage", {})
    calls = trajectory.get("usage_calls", "")
    if isinstance(calls, list):
        calls = len(calls)
    return [
        len(trajectory.get("messages", [])), tool_step_count(trajectory), event_count(trajectory),
        *token_details(kind, usage), calls, step_time(trajectory), *paths,
    ]


def discover_runs(root: Path) -> list[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for phase in ("codegen", "testgen"):
        base = root / phase
        if base.is_dir():
            for label in base.iterdir():
                if label.is_dir():
                    found.update((label.name, task.name) for task in label.iterdir() if task.is_dir())
    timings = root / "timings"
    if timings.is_dir():
        for label in timings.iterdir():
            if label.is_dir():
                found.update((label.name, path.name.removesuffix(".seconds")) for path in label.glob("*.seconds"))
    return sorted(found, key=lambda item: (item[1], item[0]))


def phase_status(trajectory: dict[str, Any] | None, exists: bool, invalid: bool = False) -> str:
    if trajectory is not None:
        return str(trajectory.get("info", {}).get("exit_status", "unknown"))
    if invalid:
        return "trajectory_invalid"
    return "trajectory_missing" if exists else "not_run"


def _read_json_metric(path: Path, reader: Any, *args: Any) -> Any:
    try:
        return reader(path, *args)
    except ijson.JSONError as exc:
        print(f"Warning: incomplete or invalid JSON in {path}: {exc}", file=sys.stderr)
        return None


def _row(
    root: Path, label: str, task: str, skipped_tests: str | None, skipped_mutants: str | None,
    instances: dict[str, dict],
) -> list[Any]:
    solve_dir = root / "codegen" / label / task
    tests_dir = root / "testgen" / label / task
    solve_path = solve_dir / "traj.json"
    tests_path = tests_dir / f"{task}.traj.json"
    solve = _read_json_metric(solve_path, load_trajectory_summary)
    tests = _read_json_metric(tests_path, load_trajectory_summary)
    trajectory = solve or tests or {}
    kind = agent_kind(trajectory.get("info", {}))

    exec_acc = percent(_read_json_metric(solve_dir / f"{task}.eval.json", execution_accuracy))
    registered_tests = get_ignored_tests(instances.get(task, {}))
    skipped_tests_for_task, skipped_mutants_for_task = skipped_for_task(skipped_tests, skipped_mutants, task)
    validity_rate_value, mutation_score_value = _read_json_metric(
        tests_dir / f"{task}.test_eval.json", test_suite_metrics,
        registered_tests | skipped_tests_for_task, skipped_mutants_for_task,
    ) or (None, None)
    validity_rate, mutation_score = percent(validity_rate_value), percent(mutation_score_value)

    solve_time, tests_time = step_time(solve), step_time(tests)
    return [
        str(root), task, label, kind, model_name(trajectory) if trajectory else "",
        reasoning_name(trajectory, label) if trajectory else reasoning_name({}, label),
        phase_status(solve, solve_dir.exists(), solve_path.is_file()),
        phase_status(tests, tests_dir.exists(), tests_path.is_file()),
        exec_acc, validity_rate, mutation_score, total_time(root, label, task),
        *phase_fields(solve, solve_path, solve_dir / "submission.tar.gz", solve_dir.exists(), kind),
        *phase_fields(tests, tests_path, tests_dir / "tests.tar.gz", tests_dir.exists(), kind),
        f"{float(solve_time or 0) + float(tests_time or 0):.1f}" if solve_time or tests_time else "",
    ]


_WORKER_CONTEXT: tuple[Path, str | None, str | None, dict[str, dict]] | None = None


def _init_worker(
    root: Path, skipped_tests: str | None, skipped_mutants: str | None, instances: dict[str, dict]
) -> None:
    global _WORKER_CONTEXT
    _WORKER_CONTEXT = root, skipped_tests, skipped_mutants, instances


def _worker_row(run: tuple[str, str]) -> list[Any]:
    if _WORKER_CONTEXT is None:
        raise RuntimeError("Worker context was not initialized")
    root, skipped_tests, skipped_mutants, instances = _WORKER_CONTEXT
    return _row(root, *run, skipped_tests, skipped_mutants, instances)


def rows(
    root: Path, skipped_tests: str | None, skipped_mutants: str | None, instances: dict[str, dict],
    workers: int = 1,
) -> list[list[Any]]:
    runs = discover_runs(root)
    if workers <= 1:
        return [_row(root, *run, skipped_tests, skipped_mutants, instances) for run in runs]
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=get_context("spawn"), initializer=_init_worker,
        initargs=(root, skipped_tests, skipped_mutants, instances),
    ) as pool:
        return list(pool.map(_worker_row, runs))


def merge_rows_by_root_priority(table: list[list[Any]]) -> list[list[Any]]:
    """Merge duplicate task/run rows, choosing the first successful phase by root priority."""
    status_columns = {
        "codegen": "Codegen Status",
        "testgen": "Testgen Status",
    }
    phase_columns = {
        "codegen": ["Codegen Status", "Exec Acc", *[name for name in COLUMNS if name.startswith("codegen_")]],
        "testgen": [
            "Testgen Status", "Test Validity Rate", "Test Mutation Score",
            *[name for name in COLUMNS if name.startswith("testgen_")],
        ],
    }
    indexes = {name: COLUMNS.index(name) for name in COLUMNS}
    merged: dict[tuple[Any, Any], list[Any]] = {}
    for source in table:
        key = source[indexes["Task"]], source[indexes["Run"]]
        if key not in merged:
            merged[key] = source.copy()
            continue
        target = merged[key]
        for phase, columns in phase_columns.items():
            status_index = indexes[status_columns[phase]]
            target_status = target[status_index]
            source_status = source[status_index]
            if target_status != "ok" and (
                source_status == "ok" or (target_status == "not_run" and source_status != "not_run")
            ):
                for column in columns:
                    target[indexes[column]] = source[indexes[column]]
        for column in ("Agent", "Model", "Reasoning", "Wall Time [m]"):
            index = indexes[column]
            if target[index] == "":
                target[index] = source[index]

    agent_time_index = indexes["Agent Time [m]"]
    phase_time_indexes = [indexes["codegen_time"], indexes["testgen_time"]]
    for row in merged.values():
        phase_times = [row[index] for index in phase_time_indexes if row[index] != ""]
        row[agent_time_index] = f"{sum(float(value) for value in phase_times):.1f}" if phase_times else ""
    return list(merged.values())


def prioritize_rows(table: list[list[Any]]) -> list[list[Any]]:
    """Keep the first row for each task/run, so command-line root order is priority order."""
    indexes = {name: COLUMNS.index(name) for name in ("Task", "Run")}
    prioritized: dict[tuple[Any, Any], list[Any]] = {}
    for row in table:
        key = row[indexes["Task"]], row[indexes["Run"]]
        prioritized.setdefault(key, row)
    return list(prioritized.values())


def phase_cost(row: list[Any], phase: str, prices: dict[str, dict[str, float]]) -> float | None:
    """Estimate dollars from per-million-token rates for this row's model."""
    rates = prices.get(str(row[COLUMNS.index("Model")]))
    if rates is None:
        return None
    fields = ("input", "cached_input", "output")
    counts = [row[COLUMNS.index(f"{phase}_{field}")] for field in fields]
    if any(count == "" for count in counts):
        return None
    return sum(float(count) * rates[field] for field, count in zip(fields, counts, strict=True)) / 1_000_000


def load_prices(path: Path) -> dict[str, dict[str, float]]:
    """Read model rates in USD per million input, cached input, and output tokens."""
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Pricing file must contain a JSON object keyed by model name")
    prices = {}
    for model, rates in data.items():
        if not isinstance(rates, dict) or any(key not in rates for key in ("input", "cached_input", "output")):
            raise ValueError(f"Pricing for {model!r} needs input, cached_input, and output rates")
        prices[model] = {key: float(rates[key]) for key in ("input", "cached_input", "output")}
        if any(rate < 0 for rate in prices[model].values()):
            raise ValueError(f"Pricing for {model!r} cannot be negative")
    return prices


MODEL_HISTOGRAM_COLORS = {
    "gpt": "#b45f06",
    "gemini": "#2369a1",
    "opus": "#39834b",
    "deepseek": "#8856a7",
}


def model_histogram_color(model: str) -> str:
    """Return the model-family color shared by the statistics plots."""
    normalized = model.lower()
    for family, color in MODEL_HISTOGRAM_COLORS.items():
        if family in normalized:
            return color
    return "#777777"


MERGED_DENSITY_RUNS = (
    ("gpt-5.6-sol_medium", "Sol", "#b45f06"),
    ("gemini-3.8-flash_medium", "Gemini", "#2369a1"),
    ("opus_high", "Opus", "#39834b"),
    ("deepseek-deepseek-v4-flash_high", "DeepSeek", "#8856a7"),
)

SCORE_TITLES = {
    "Exec Acc": "Reference Pass Rate",
    "Test Validity Rate": "Validity Rate",
    "Test Mutation Score": "Mutation Score",
}
RESOURCE_LIMITS = {"Cost": (0, 30), "Time": (0, 100), "Steps": (0, 400)}


def density_curve(values: list[float], grid):
    """Estimate a one-dimensional Gaussian kernel density on a shared grid."""
    import numpy as np

    data = np.asarray(values, dtype=float)
    if len(data) < 2 or np.ptp(data) == 0:
        return np.zeros_like(grid)
    bandwidth = 1.06 * np.std(data, ddof=1) * len(data) ** (-0.2)
    if not np.isfinite(bandwidth) or bandwidth <= 0:
        return np.zeros_like(grid)
    offsets = (grid[:, None] - data[None, :]) / bandwidth
    return np.exp(-0.5 * offsets ** 2).mean(axis=1) / (bandwidth * np.sqrt(2 * np.pi))


def write_merged_density(by_run, output_dir: Path, prices, plt) -> None:
    """Overlay the four headline models as density curves in one 3x3 PDF."""
    import numpy as np
    from matplotlib.lines import Line2D

    if not all(run in by_run for run, _, _ in MERGED_DENSITY_RUNS):
        return

    score_metrics = ("Exec Acc", "Test Validity Rate", "Test Mutation Score")
    resource_metrics = (("Cost", "USD"), ("Time", "Minutes"), ("Steps", "Tool calls"))
    figure, axes = plt.subplots(3, 3, figsize=(15, 12), layout="constrained")

    def draw_density(axis, series, title, xlabel, limits=None):
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        all_values = [value for _, _, values in series for value in values]
        if not all_values:
            axis.text(0.5, 0.5, "No data", ha="center", va="center", transform=axis.transAxes)
            axis.set_title(title)
            axis.set_xlabel(xlabel)
            return
        if limits is None:
            lower, upper = min(all_values), max(all_values)
            padding = max((upper - lower) * 0.08, abs(upper) * 0.02, 0.1)
            limits = (max(0, lower - padding), upper + padding)
        grid = np.linspace(*limits, 300)
        for label, color, values in series:
            density = density_curve(values, grid)
            axis.plot(grid, density, color=color, linewidth=2)
            axis.fill_between(grid, density, color=color, alpha=0.08)
            if values:
                axis.axvline(median(values), color=color, linestyle="--", linewidth=1.5)
        axis.set_title(title)
        axis.set_xlabel(xlabel)
        axis.set_xlim(limits)
        axis.set_ylim(bottom=0)
        axis.grid(alpha=0.15)
        axis.set_axisbelow(True)

    for axis, metric in zip(axes[0], score_metrics, strict=True):
        index = COLUMNS.index(metric)
        series = [
            (label, color, [float(row[index]) for row in by_run[run] if row[index] != ""])
            for run, label, color in MERGED_DENSITY_RUNS
        ]
        draw_density(axis, series, SCORE_TITLES[metric], "Score (%)", (0, 100))

    for row_index, phase in enumerate(("codegen", "testgen"), start=1):
        for axis, (metric, xlabel) in zip(axes[row_index], resource_metrics, strict=True):
            series = []
            for run, label, color in MERGED_DENSITY_RUNS:
                if metric == "Cost":
                    values = [cost for row in by_run[run] if (cost := phase_cost(row, phase, prices)) is not None]
                else:
                    index = COLUMNS.index(f"{phase}_{metric.lower()}")
                    values = [float(row[index]) for row in by_run[run] if row[index] != ""]
                series.append((label, color, values))
            draw_density(axis, series, f"{phase.capitalize()} {metric}", xlabel, RESOURCE_LIMITS[metric])

    handles = [Line2D([], [], color=color, linewidth=3, label=label)
               for _, label, color in MERGED_DENSITY_RUNS]
    figure.legend(
        handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.015),
        ncol=4, frameon=False,
    )
    figure.savefig(output_dir / "merged_density.pdf", bbox_inches="tight")
    plt.close(figure)


def ecdf_points(values: list[float], limits: tuple[float, float]):
    """Return exact empirical CDF step points, including the plot limits."""
    import numpy as np

    data = np.sort(np.asarray(values, dtype=float))
    if not len(data):
        return np.array([]), np.array([])
    visible = data[(data > limits[0]) & (data < limits[1])]
    x = np.r_[limits[0], visible, limits[1]]
    y = np.searchsorted(data, x, side="right") / len(data)
    return x, y


def write_merged_cumulative(by_run, output_dir: Path, prices, plt) -> None:
    """Overlay empirical cumulative distributions for the headline models."""
    from matplotlib.lines import Line2D

    if not all(run in by_run for run, _, _ in MERGED_DENSITY_RUNS):
        return

    score_metrics = ("Exec Acc", "Test Validity Rate", "Test Mutation Score")
    resource_metrics = (("Cost", "USD"), ("Time", "Minutes"), ("Steps", "Tool calls"))
    figure, axes = plt.subplots(3, 3, figsize=(18, 13), layout="constrained")

    def draw_cumulative(axis, series, title, xlabel, limits):
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        if not any(values for _, _, values in series):
            axis.text(0.5, 0.5, "No data", ha="center", va="center", transform=axis.transAxes)
        for _, color, values in series:
            if values:
                x, y = ecdf_points(values, limits)
                axis.step(x, y, where="post", color=color, linewidth=2.5)
        axis.set_title(title, fontsize=20)
        axis.set_xlabel(xlabel, fontsize=17)
        axis.set_xlim(limits)
        axis.set_ylim(0, 1)
        axis.set_yticks((0, 0.25, 0.5, 0.75, 1))
        axis.tick_params(labelsize=14)
        axis.grid(alpha=0.15)
        axis.set_axisbelow(True)

    for axis, metric in zip(axes[0], score_metrics, strict=True):
        index = COLUMNS.index(metric)
        series = [
            (label, color, [float(row[index]) for row in by_run[run] if row[index] != ""])
            for run, label, color in MERGED_DENSITY_RUNS
        ]
        draw_cumulative(axis, series, SCORE_TITLES[metric], "Score (%)", (0, 100))

    for row_index, phase in enumerate(("codegen", "testgen"), start=1):
        for axis, (metric, xlabel) in zip(axes[row_index], resource_metrics, strict=True):
            series = []
            for run, label, color in MERGED_DENSITY_RUNS:
                if metric == "Cost":
                    values = [cost for row in by_run[run] if (cost := phase_cost(row, phase, prices)) is not None]
                else:
                    index = COLUMNS.index(f"{phase}_{metric.lower()}")
                    values = [float(row[index]) for row in by_run[run] if row[index] != ""]
                series.append((label, color, values))
            draw_cumulative(axis, series, f"{phase.capitalize()} {metric}", xlabel, RESOURCE_LIMITS[metric])

    for axis in axes[:, 0]:
        axis.set_ylabel("Cumulative fraction of tasks", fontsize=17)
    handles = [Line2D([], [], color=color, linewidth=3, label=label)
               for _, label, color in MERGED_DENSITY_RUNS]
    figure.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.015),
                  ncol=4, frameon=False, fontsize=17)
    figure.savefig(output_dir / "merged_cumulative.pdf", bbox_inches="tight")
    plt.close(figure)


def write_histograms(
    table: list[list[Any]], output_dir: Path, prices: dict[str, dict[str, float]] | None = None
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    prices = prices or {}
    output_dir.mkdir(parents=True, exist_ok=True)
    by_run: dict[str, list[list[Any]]] = defaultdict(list)
    for row in table:
        by_run[str(row[COLUMNS.index("Run")])].append(row)
    score_metrics = ("Exec Acc", "Test Validity Rate", "Test Mutation Score")
    score_bins = list(range(0, 105, 5))
    resource_metrics = (("Cost", "USD"), ("Time", "Minutes"), ("Steps", "Tool calls"))
    typography = {
        "font.family": "Times New Roman",
        "font.size": 16,
        "axes.titlesize": 19,
        "axes.labelsize": 17,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 15,
        "figure.titlesize": 22,
        "pdf.fonttype": 42,
    }
    mean_color = "#222222"
    median_color = "#777777"
    with matplotlib.rc_context(typography):
        for run, run_rows in sorted(by_run.items()):
            models = {str(row[COLUMNS.index("Model")]) for row in run_rows if row[COLUMNS.index("Model")]}
            histogram_color = model_histogram_color(next(iter(models))) if len(models) == 1 else "#777777"
            figure, axes = plt.subplots(3, 3, figsize=(15, 12), layout="constrained")
            for axis, metric in zip(axes[0], score_metrics, strict=True):
                index = COLUMNS.index(metric)
                values = [float(row[index]) for row in run_rows if row[index] != ""]
                if values:
                    axis.hist(values, bins=score_bins, color=histogram_color, edgecolor="white")
                    mean_value, median_value = fmean(values), median(values)
                    axis.axvline(mean_value, color=mean_color, linestyle="--", linewidth=2,
                                 label=f"Mean: {mean_value:.1f}%")
                    axis.axvline(median_value, color=median_color, linestyle=":", linewidth=2,
                                 label=f"Median: {median_value:.1f}%")
                    axis.legend(loc="upper left", frameon=False)
                else:
                    axis.text(0.5, 0.5, "No data", ha="center", va="center", transform=axis.transAxes)
                axis.set_title(f"{SCORE_TITLES[metric]} ($n$={len(values)})")
                axis.set_xlabel("Score (%)")
                axis.set_xlim(0, 100)
                axis.set_ylabel("Tasks")
                axis.grid(axis="y", alpha=0.15)
                axis.set_axisbelow(True)
                axis.spines["top"].set_visible(False)
                axis.spines["right"].set_visible(False)

            for row_index, phase in enumerate(("codegen", "testgen"), start=1):
                for axis, (metric, xlabel) in zip(axes[row_index], resource_metrics, strict=True):
                    if metric == "Cost":
                        values = [cost for row in run_rows if (cost := phase_cost(row, phase, prices)) is not None]
                    else:
                        index = COLUMNS.index(f"{phase}_{metric.lower()}")
                        values = [float(row[index]) for row in run_rows if row[index] != ""]
                    if values:
                        axis.hist(values, bins="auto", color=histogram_color, edgecolor="white")
                        mean_value, median_value = fmean(values), median(values)
                        axis.axvline(mean_value, color=mean_color, linestyle="--", linewidth=2,
                                     label=f"Mean: {mean_value:.3g}")
                        axis.axvline(median_value, color=median_color, linestyle=":", linewidth=2,
                                     label=f"Median: {median_value:.3g}")
                        axis.legend(loc="upper right", frameon=False)
                    else:
                        axis.text(0.5, 0.5, "No data", ha="center", va="center", transform=axis.transAxes)
                    axis.set_title(f"{phase.capitalize()} {metric} ($n$={len(values)})")
                    axis.set_xlabel(xlabel)
                    axis.set_ylabel("Tasks")
                    axis.set_xlim(RESOURCE_LIMITS[metric])
                    axis.grid(axis="y", alpha=0.15)
                    axis.set_axisbelow(True)
                    axis.spines["top"].set_visible(False)
                    axis.spines["right"].set_visible(False)

            figure.suptitle(run)
            filename = re.sub(r"[^A-Za-z0-9._-]+", "_", run).strip("._") or "agent"
            figure.savefig(output_dir / f"{filename}.pdf")
            plt.close(figure)
        write_merged_density(by_run, output_dir, prices, plt)
        write_merged_cumulative(by_run, output_dir, prices, plt)


MODEL_SUMMARY_COLUMNS = (
    "Model", "Reasoning", "VR", "MS", "Cost [$]", "Steps", "Time [m]",
    "RPR", "Cost [$]", "Steps", "Time [m]", "num fully done",
)
MODEL_DISPLAY_NAMES = {
    "gpt-5.6-sol": "GPT 5.6 Sol",
    "gpt-6-astra": "GPT 6 Astra",
    "claude-opus-5": "Opus 5",
    "claude-opus-5-5": "Opus 5.5",
    "claude-sonnet-5-5": "Sonnet 5.5",
    "gpt-6-sol": "GPT 6 Sol",
    "gpt-6-luna": "GPT 6 Luna",
    "gpt-6.1-sol": "GPT 6.1 Sol",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "deepseek/deepseek-v4-flash": "DeepSeek V4 Flash 0423",
    "deepseek/deepseek-v4-flash-0731": "DeepSeek V4 Flash 0731",
    "deepseek-flash": "DeepSeek Flash",
    "z-ai/glm-5.3-flash": "GLM 5.3 Flash",
    "zai/GLM-5.3-Flash": "GLM 5.3 Flash",
    "openrouter/z-ai/glm-5.3-flash": "GLM 5.3 Flash",
    "muse-spark-1.3-contributor": "Muse Spark 1.3",
    "meta/muse-spark-1.3-contributor": "Muse Spark 1.3",
    "gpt-5.6-luna": "GPT 5.6 Luna",
}


def model_summary_rows(table: list[list[Any]], prices: dict[str, dict[str, float]]) -> list[list[str]]:
    """Average each available task metric by model and reasoning level."""
    by_model: dict[tuple[str, str], list[list[Any]]] = defaultdict(list)
    for row in table:
        model = str(row[COLUMNS.index("Model")])
        if model:
            by_model[model, str(row[COLUMNS.index("Reasoning")])].append(row)

    def mean_field(model_rows: list[list[Any]], field: str, digits: int = 1) -> str:
        index = COLUMNS.index(field)
        values = [float(row[index]) for row in model_rows if row[index] != ""]
        return f"{fmean(values):.{digits}f}" if values else "-"

    def mean_cost(model_rows: list[list[Any]], phase: str) -> str:
        values = [cost for row in model_rows if (cost := phase_cost(row, phase, prices)) is not None]
        return f"{fmean(values):.2f}" if values else "-"

    def fully_done_count(model_rows: list[list[Any]]) -> int:
        required = (
            "Exec Acc", "Test Validity Rate", "Test Mutation Score",
            "codegen_steps", "codegen_time", "testgen_steps", "testgen_time",
        )
        return len({
            str(row[COLUMNS.index("Task")])
            for row in model_rows
            if row[COLUMNS.index("Task")]
            and row[COLUMNS.index("Codegen Status")] == "ok"
            and row[COLUMNS.index("Testgen Status")] == "ok"
            and all(row[COLUMNS.index(field)] != "" for field in required)
            and phase_cost(row, "codegen", prices) is not None
            and phase_cost(row, "testgen", prices) is not None
        })

    efforts = ["", "low", "medium", "high", "xhigh", "max", "ultra"]
    ordered_models = sorted(by_model, key=lambda group: (
        list(MODEL_DISPLAY_NAMES).index(group[0]) if group[0] in MODEL_DISPLAY_NAMES else len(MODEL_DISPLAY_NAMES),
        group[0], efforts.index(group[1]) if group[1] in efforts else len(efforts), group[1],
    ))
    result = []
    for model, reasoning in ordered_models:
        rows = by_model[model, reasoning]
        result.append([
            MODEL_DISPLAY_NAMES.get(model, model), reasoning,
            mean_field(rows, "Test Validity Rate"), mean_field(rows, "Test Mutation Score"),
            mean_cost(rows, "testgen"), mean_field(rows, "testgen_steps"), mean_field(rows, "testgen_time"),
            mean_field(rows, "Exec Acc"), mean_cost(rows, "codegen"),
            mean_field(rows, "codegen_steps"), mean_field(rows, "codegen_time"),
            f"{fully_done_count(rows)}/165",
        ])
    return result


def write_model_summary(
    table: list[list[Any]], output: Path, prices: dict[str, dict[str, float]]
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(MODEL_SUMMARY_COLUMNS)
        writer.writerows(model_summary_rows(table, prices))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path, help="Output roots containing codegen/, testgen/ and timings/")
    parser.add_argument("--skipped-tests", default="ground_truth/skipped-tests")
    parser.add_argument("--skipped-mutants", default="ground_truth/skipped-mutants")
    parser.add_argument("--output", type=Path, help="TSV path (default: stdout)")
    parser.add_argument("--histograms", "--histogram", dest="histograms", type=Path, help="Write one nine-panel histogram PDF per run")
    parser.add_argument("--model-summary", type=Path, help="Aggregated TSV path (default with --output: <stem>_aggregated.tsv)")
    parser.add_argument("--pricing-file", type=Path, default="scripts/eval/pricing_2026-09-22.json", help="JSON model rates in USD per million input, cached_input, and output tokens")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1), help="Concurrent file readers (default: up to 4)")
    root_priority = parser.add_mutually_exclusive_group()
    root_priority.add_argument(
        "--merge-roots", dest="merge_roots", action="store_true", default=True,
        help="Use the first successful phase in root priority order (default)",
    )
    root_priority.add_argument(
        "--whole-row-priority", dest="merge_roots", action="store_false",
        help="Keep the entire first matching task/run row instead of filling not-run phases",
    )
    args = parser.parse_args()
    if args.output and args.model_summary is None:
        args.model_summary = args.output.with_name(f"{args.output.stem}_aggregated.tsv")

    instances = {inst["instance_id"]: inst for inst in load_all_instances()}
    table = [
        row
        for root in args.roots
        for row in rows(root, args.skipped_tests, args.skipped_mutants, instances, args.workers)
    ]
    table = merge_rows_by_root_priority(table) if args.merge_roots else prioritize_rows(table)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
    with (args.output.open("w", newline="") if args.output else sys.stdout) as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows(table)
    if args.histograms or args.model_summary:
        prices = load_prices(args.pricing_file) if args.pricing_file else {}
        if args.histograms:
            write_histograms(table, args.histograms, prices)
        if args.model_summary:
            write_model_summary(table, args.model_summary, prices)


if __name__ == "__main__":
    main()
