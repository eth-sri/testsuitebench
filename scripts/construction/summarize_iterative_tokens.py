#!/usr/bin/env python3
"""Summarize iterative Codex token usage by task, iteration, and pipeline step."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from programbench.codex import (
    CODEX_TOKEN_KEYS,
    codex_usage_records_from_events,
    codex_usage_records_from_stdout,
    normalize_codex_usage,
)


TOKEN_KEYS = CODEX_TOKEN_KEYS
GroupKey = tuple[str, int, str]
AgentRoute = tuple[str, str]

CLASSIFIER_STEPS = {
    "failure_classification": "candidate-failure-classification",
    "generated_test_failure_classification": "generated-test-failure-classification",
    "mutant_classification": "mutant-classification",
}

STEP_ORDER = (
    "improve-spec",
    "link-reference-tests",
    "generate-mutants",
    "ensure-mutants-killed-repair",
    "candidate-solve",
    "candidate-failure-classification",
    "candidate-spec-polish",
    "generated-test-generation",
    "generated-test-failure-classification",
    "mutant-classification",
    "generated-test-spec-polish",
    "ground-truth-test-improvement",
)
STEP_RANK = {step: index for index, step in enumerate(STEP_ORDER)}

# Names in agent-routes TSV files differ from the presentation names used by
# this report. Multiple report steps can intentionally share one agent route.
STEP_AGENT_ROUTE = {
    "improve-spec": "improve_spec",
    "link-reference-tests": "link_reference_tests",
    "generate-mutants": "generate_mutants",
    "ensure-mutants-killed-repair": "ensure_mutants_killed",
    "candidate-solve": "solve_codex",
    "candidate-failure-classification": "classify_failures",
    "candidate-spec-polish": "polish_iteration",
    "generated-test-generation": "generate_tests",
    "generated-test-failure-classification": "classify_mutants",
    "mutant-classification": "classify_mutants",
    "generated-test-spec-polish": "polish_generated_test_spec",
    "ground-truth-test-improvement": "polish_iteration",
}


def normalized_usage(raw: dict[str, Any]) -> dict[str, int]:
    """Backward-compatible alias used by callers and older tests."""
    return normalize_codex_usage(raw)


def json_lines_usage(value: str) -> Iterable[dict[str, int]]:
    yield from codex_usage_records_from_stdout(value)


def add_usage(target: dict[str, int], usage: dict[str, int]) -> None:
    for key, value in usage.items():
        target[key] += value


def task_from_path(path: Path, known_tasks: set[str]) -> str | None:
    for part in path.parts:
        if part in known_tasks:
            return part
    name = path.name
    for task in known_tasks:
        if name.startswith(task + "."):
            return task
    return None


def iteration_from_path(path: Path) -> int:
    for part in path.parts:
        match = re.fullmatch(r"iter_(\d+)", part)
        if match:
            return int(match.group(1))
    return 0


def canonical_trajectories(iter_root: Path) -> Iterable[Path]:
    """Yield each real Codex trajectory once, excluding immutable stage copies."""
    batch_trajectories = iter_root / "batch" / "trajectories"
    if batch_trajectories.is_dir():
        yield from sorted(batch_trajectories.rglob("*.json"))
    for iteration in sorted(iter_root.glob("iter_*")):
        if not iteration.is_dir():
            continue
        yield from sorted((iteration / "executable").glob("*/traj.json"))
        yield from sorted((iteration / "generated-test").glob("*/*.traj.json"))
        yield from sorted((iteration / "log").glob("*/*.traj.json"))


def trajectory_step(path: Path) -> str | None:
    value = path.as_posix()
    if "/batch/trajectories/spec/" in value:
        return "improve-spec"
    if path.name.startswith("link_reference_tests.") and path.name.endswith(".traj.json"):
        return "link-reference-tests"
    if "/batch/trajectories/mutant/" in value:
        return "generate-mutants"
    if "/executable/" in value and path.name == "traj.json":
        return "candidate-solve"
    if "/generated-test/" in value and path.name.endswith(".traj.json"):
        return "generated-test-generation"
    return {
        "polish_spec.traj.json": "candidate-spec-polish",
        "polish_spec_mutants.traj.json": "generated-test-spec-polish",
        "polish_spec_generated_tests.traj.json": "generated-test-spec-polish",
        "improve_ground_truth_tests.traj.json": "ground-truth-test-improvement",
    }.get(path.name)


def step_sort_key(step: str) -> tuple[int, str]:
    return STEP_RANK.get(step, len(STEP_RANK)), step


def result_usage(result: dict[str, Any]) -> list[tuple[int, dict[str, int]]]:
    """Read an explicitly recorded result, falling back to its legacy JSONL."""
    raw_usage = result.get("usage")
    if isinstance(raw_usage, dict) and raw_usage:
        calls = result.get("usage_calls", 1)
        calls = calls if isinstance(calls, int) and not isinstance(calls, bool) and calls > 0 else 1
        return [(calls, normalized_usage(raw_usage))]
    stdout = result.get("stdout", "")
    if isinstance(stdout, str):
        return [(1, usage) for usage in json_lines_usage(stdout)]
    return []


def nested_codex_results(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        codex = value.get("codex")
        if isinstance(codex, dict):
            yield codex
        for key, child in value.items():
            if key != "codex":
                yield from nested_codex_results(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_codex_results(child)


def trajectory_usage(payload: dict[str, Any]) -> list[tuple[int, dict[str, int]]]:
    """Use one canonical field instead of recursively counting duplicate events."""
    explicit = result_usage(payload)
    if explicit:
        return explicit

    events = payload.get("codex_events")
    if not isinstance(events, list):
        events = payload.get("codex_json_events")
    if isinstance(events, list):
        records = codex_usage_records_from_events([event for event in events if isinstance(event, dict)])
        if records:
            return [(1, usage) for usage in records]

    records: list[tuple[int, dict[str, int]]] = []
    for result in nested_codex_results(payload):
        records.extend(result_usage(result))
    return records


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def payload_agent_route(payload: dict[str, Any]) -> AgentRoute | None:
    """Read the actual agent route embedded in a Codex trajectory, if present."""
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    model = info.get("model")
    if not isinstance(model, str) or not model:
        return None
    reasoning = info.get("reasoning_effort", info.get("reasoning"))
    if not isinstance(reasoning, str) or not reasoning:
        command = info.get("codex_shell_command", "")
        match = re.search(r"(?:^|\s)model_reasoning_effort=([^\s'\"]+)", command) if isinstance(command, str) else None
        reasoning = match.group(1) if match else ""
    return model, reasoning


def load_agent_route_file(path: Path) -> dict[str, tuple[AgentRoute, AgentRoute]]:
    """Load initial and retry routes keyed by the pipeline's internal step name."""
    try:
        with path.open(newline="") as stream:
            rows = csv.DictReader(stream, dialect="excel-tab")
            routes = {}
            for row in rows:
                step = row.get("step", "")
                model = row.get("model", "")
                reasoning = row.get("reasoning", "")
                if not step or not model:
                    continue
                retry_model = row.get("retry_model", "") or model
                retry_reasoning = row.get("retry_reasoning", "") or reasoning
                routes[step] = ((model, reasoning), (retry_model, retry_reasoning))
            return routes
    except OSError:
        return {}


def collect_agent_routes(
    iter_root: Path,
    known_tasks: set[str],
    totals: dict[GroupKey, dict[str, int]],
    agent_routes_file: Path | None = None,
) -> dict[GroupKey, set[AgentRoute]]:
    """Resolve model/reasoning metadata for every token-usage group.

    Resolved route files cover classifiers, whose reports only store usage.
    Embedded trajectory metadata and per-attempt repair metadata take
    precedence because they describe what actually ran.
    """
    batch_routes = load_agent_route_file(iter_root / "batch" / "agent-routes.tsv")
    invocation_routes = load_agent_route_file(agent_routes_file) if agent_routes_file else {}
    run_task_routes: dict[str, dict[str, tuple[AgentRoute, AgentRoute]]] = {}
    for run_dir in sorted((iter_root / "batch" / "runs").glob("*")):
        routes = load_agent_route_file(run_dir / "agent-routes.tsv")
        if not routes:
            continue
        try:
            tasks = (run_dir / "tasks.started.txt").read_text().splitlines()
        except OSError:
            continue
        for task in tasks:
            if task in known_tasks:
                run_task_routes[task] = routes
    task_routes = {
        path.stem: load_agent_route_file(path)
        for path in sorted((iter_root / "agent-routes").glob("*.tsv"))
        if path.stem in known_tasks
    }
    routes: dict[GroupKey, set[AgentRoute]] = defaultdict(set)

    for key in totals:
        task, _, step = key
        route_name = STEP_AGENT_ROUTE.get(step)
        configured = (
            task_routes.get(task, {}).get(route_name)
            or invocation_routes.get(route_name)
            or run_task_routes.get(task, {}).get(route_name)
            or batch_routes.get(route_name)
        )
        if configured:
            routes[key].add(configured[0])

    for path in canonical_trajectories(iter_root):
        task = task_from_path(path, known_tasks)
        step = trajectory_step(path)
        payload = load_json(path)
        if task is None or step is None or payload is None:
            continue
        route = payload_agent_route(payload)
        key = (task, iteration_from_path(path), step)
        if route and key in totals:
            routes[key] = {route}

    for path in sorted(iter_root.glob("batch/mutant-validation/initial/*/mutant_kill_validation.json")):
        task = task_from_path(path, known_tasks)
        payload = load_json(path)
        if task is None or payload is None:
            continue
        key = (task, 0, "ensure-mutants-killed-repair")
        actual_routes = set()
        for attempt in payload.get("attempts", []):
            if not isinstance(attempt, dict) or not isinstance(attempt.get("repair"), dict):
                continue
            route = attempt.get("repair_route")
            if isinstance(route, dict):
                model = route.get("model")
                reasoning = route.get("reasoning_effort", route.get("reasoning", ""))
                if isinstance(model, str) and model:
                    actual_routes.add((model, reasoning if isinstance(reasoning, str) else ""))
        if actual_routes and key in totals:
            routes[key] = actual_routes

    return routes


def record_usage(
    totals: dict[GroupKey, dict[str, int]],
    calls: dict[GroupKey, int],
    *,
    task: str,
    iteration: int,
    step: str,
    usage: dict[str, int],
    call_count: int = 1,
) -> None:
    key = (task, iteration, step)
    add_usage(totals[key], usage)
    calls[key] += call_count


def collect_usage(iter_root: Path, known_tasks: set[str]) -> tuple[dict[GroupKey, dict[str, int]], dict[GroupKey, int]]:
    totals: dict[GroupKey, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    calls: dict[GroupKey, int] = defaultdict(int)

    for path in canonical_trajectories(iter_root):
        task = task_from_path(path, known_tasks)
        step = trajectory_step(path)
        payload = load_json(path)
        if task is None or step is None or payload is None:
            continue
        for call_count, usage in trajectory_usage(payload):
            record_usage(
                totals,
                calls,
                task=task,
                iteration=iteration_from_path(path),
                step=step,
                usage=usage,
                call_count=call_count,
            )

    repair_reports = (
        ("batch/mutant-validation/initial/*/mutant_kill_validation.json", "ensure-mutants-killed-repair"),
    )
    for pattern, step in repair_reports:
        for path in sorted(iter_root.glob(pattern)):
            task = task_from_path(path, known_tasks)
            payload = load_json(path)
            if task is None or payload is None:
                continue
            for attempt in payload.get("attempts", []):
                if not isinstance(attempt, dict) or not isinstance(attempt.get("repair"), dict):
                    continue
                for call_count, usage in result_usage(attempt["repair"]):
                    record_usage(
                        totals,
                        calls,
                        task=task,
                        iteration=0,
                        step=step,
                        usage=usage,
                        call_count=call_count,
                    )

    for report_name in ("failure_attribution.json", "mutant_attribution.json"):
        for path in sorted(iter_root.glob(f"iter_*/log/*/{report_name}")):
            task = task_from_path(path, known_tasks)
            payload = load_json(path)
            if task is None or payload is None:
                continue
            usage_report = payload.get("classifier_usage", {})
            batches = usage_report.get("batches", []) if isinstance(usage_report, dict) else []
            for batch in batches:
                if not isinstance(batch, dict) or not isinstance(batch.get("usage"), dict):
                    continue
                phase = str(batch.get("phase", "classifier"))
                record_usage(
                    totals,
                    calls,
                    task=task,
                    iteration=iteration_from_path(path),
                    step=CLASSIFIER_STEPS.get(phase, phase.replace("_", "-")),
                    usage=normalized_usage(batch["usage"]),
                )

    return totals, calls


def usage_row(
    *,
    scope: str,
    task: str,
    iteration: int | str,
    step: str,
    calls: int,
    usage: dict[str, int],
    routes: set[AgentRoute] | None = None,
) -> dict[str, Any]:
    known_routes = routes or set()
    return {
        "scope": scope,
        "task": task,
        "iteration": iteration,
        "step": step,
        "model": ";".join(sorted({model for model, _ in known_routes})),
        "reasoning": ";".join(sorted({reasoning for _, reasoning in known_routes if reasoning})),
        "calls": calls,
        **{key: usage.get(key, 0) for key in TOKEN_KEYS},
    }


def summary_rows(
    totals: dict[GroupKey, dict[str, int]],
    calls: dict[GroupKey, int],
    routes: dict[GroupKey, set[AgentRoute]] | None = None,
) -> list[dict[str, Any]]:
    routes = routes or {}
    rows = [
        usage_row(
            scope="detail",
            task=task,
            iteration=iteration,
            step=step,
            calls=calls[(task, iteration, step)],
            usage=usage,
            routes=routes.get((task, iteration, step)),
        )
        for (task, iteration, step), usage in sorted(
            totals.items(), key=lambda item: (item[0][0], item[0][1], step_sort_key(item[0][2]))
        )
    ]

    step_totals: dict[tuple[int, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    step_calls: dict[tuple[int, str], int] = defaultdict(int)
    step_routes: dict[tuple[int, str], set[AgentRoute]] = defaultdict(set)
    pipeline_step_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pipeline_step_calls: dict[str, int] = defaultdict(int)
    pipeline_step_routes: dict[str, set[AgentRoute]] = defaultdict(set)
    task_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    task_calls: dict[str, int] = defaultdict(int)
    task_routes: dict[str, set[AgentRoute]] = defaultdict(set)
    grand_total: dict[str, int] = defaultdict(int)
    grand_calls = 0
    grand_routes: set[AgentRoute] = set()
    for (task, iteration, step), usage in totals.items():
        call_count = calls[(task, iteration, step)]
        add_usage(step_totals[(iteration, step)], usage)
        step_calls[(iteration, step)] += call_count
        step_routes[(iteration, step)].update(routes.get((task, iteration, step), set()))
        add_usage(pipeline_step_totals[step], usage)
        pipeline_step_calls[step] += call_count
        pipeline_step_routes[step].update(routes.get((task, iteration, step), set()))
        add_usage(task_totals[task], usage)
        task_calls[task] += call_count
        task_routes[task].update(routes.get((task, iteration, step), set()))
        add_usage(grand_total, usage)
        grand_calls += call_count
        grand_routes.update(routes.get((task, iteration, step), set()))

    for (iteration, step), usage in sorted(
        step_totals.items(), key=lambda item: (item[0][0], step_sort_key(item[0][1]))
    ):
        rows.append(usage_row(
            scope="iteration_step_total", task="ALL", iteration=iteration, step=step,
            calls=step_calls[(iteration, step)], usage=usage,
            routes=step_routes[(iteration, step)],
        ))
    for step, usage in sorted(pipeline_step_totals.items(), key=lambda item: step_sort_key(item[0])):
        rows.append(usage_row(
            scope="step_total", task="ALL", iteration="ALL", step=step,
            calls=pipeline_step_calls[step], usage=usage,
            routes=pipeline_step_routes[step],
        ))
    for task, usage in sorted(task_totals.items()):
        rows.append(usage_row(
            scope="task_total", task=task, iteration="ALL", step="ALL",
            calls=task_calls[task], usage=usage,
            routes=task_routes[task],
        ))
    rows.append(usage_row(
        scope="grand_total", task="ALL", iteration="ALL", step="ALL",
        calls=grand_calls, usage=grand_total,
        routes=grand_routes,
    ))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iter-root", type=Path, default=Path("output/debug_iterative_v9"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--task", action="append", dest="tasks")
    parser.add_argument("--agent-routes", type=Path)
    args = parser.parse_args()

    task_root = Path("src/programbench/data/tasks")
    known_tasks = {path.name for path in task_root.iterdir() if path.is_dir()}
    if args.tasks:
        unknown_tasks = set(args.tasks) - known_tasks
        if unknown_tasks:
            parser.error(f"unknown task(s): {', '.join(sorted(unknown_tasks))}")
        known_tasks = set(args.tasks)
    totals, calls = collect_usage(args.iter_root, known_tasks)
    routes = collect_agent_routes(args.iter_root, known_tasks, totals, args.agent_routes)
    rows = summary_rows(totals, calls, routes)
    fieldnames = ["scope", "task", "iteration", "step", "model", "reasoning", "calls", *TOKEN_KEYS]

    destination = args.output
    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        stream = destination.open("w", newline="")
    else:
        import sys

        stream = sys.stdout
    try:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, dialect="excel-tab")
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if destination:
            stream.close()

    if destination:
        detail_count = sum(row["scope"] == "detail" for row in rows)
        print(f"Wrote {detail_count} task/step token-usage row(s) to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
