# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""Plan fair, non-overlapping spec-to-test mutant assignments."""

from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MUTANT_PLAN_FILENAME = "mutant_plan.json"


@dataclass
class _Edge:
    to: int
    reverse: int
    capacity: int
    cost: int
    initial_capacity: int


def _add_edge(graph: list[list[_Edge]], source: int, target: int, capacity: int, cost: int) -> _Edge:
    forward = _Edge(target, len(graph[target]), capacity, cost, capacity)
    reverse = _Edge(source, len(graph[source]), 0, -cost, 0)
    graph[source].append(forward)
    graph[target].append(reverse)
    return forward


def _min_cost_flow(graph: list[list[_Edge]], source: int, sink: int, amount: int) -> tuple[int, int]:
    """Return fixed-cardinality min-cost flow using successive shortest paths."""
    size = len(graph)
    potential = [0] * size
    flow = 0
    cost = 0
    while flow < amount:
        distance = [10**30] * size
        previous_node = [-1] * size
        previous_edge = [-1] * size
        distance[source] = 0
        queue: list[tuple[int, int]] = [(0, source)]
        while queue:
            current_distance, node = heapq.heappop(queue)
            if current_distance != distance[node]:
                continue
            for edge_index, edge in enumerate(graph[node]):
                if edge.capacity <= 0:
                    continue
                candidate = current_distance + edge.cost + potential[node] - potential[edge.to]
                if candidate < distance[edge.to]:
                    distance[edge.to] = candidate
                    previous_node[edge.to] = node
                    previous_edge[edge.to] = edge_index
                    heapq.heappush(queue, (candidate, edge.to))
        if distance[sink] == 10**30:
            break
        for node, value in enumerate(distance):
            if value < 10**30:
                potential[node] += value
        increment = amount - flow
        node = sink
        while node != source:
            parent = previous_node[node]
            if parent < 0:
                increment = 0
                break
            edge = graph[parent][previous_edge[node]]
            increment = min(increment, edge.capacity)
            node = parent
        if increment == 0:
            break
        node = sink
        while node != source:
            parent = previous_node[node]
            edge = graph[parent][previous_edge[node]]
            edge.capacity -= increment
            graph[node][edge.reverse].capacity += increment
            cost += increment * edge.cost
            node = parent
        flow += increment
    return flow, cost


def build_mutant_plan(
    links: dict[str, Any], *, instance_id: str, target_tests_per_spec: int = 6,
    final_mutants_per_spec: int = 2,
    mutants_per_spec: int | None = None,
) -> dict[str, Any]:
    """Build a lexicographically fair min-cost b-matching over spec-test links."""
    if mutants_per_spec is not None:
        target_tests_per_spec = mutants_per_spec
        final_mutants_per_spec = mutants_per_spec
    for name, value in (
        ("target_tests_per_spec", target_tests_per_spec),
        ("final_mutants_per_spec", final_mutants_per_spec),
    ):
        if value < 1:
            raise ValueError(f"{name} must be positive")
    if final_mutants_per_spec > target_tests_per_spec:
        raise ValueError(
            "final_mutants_per_spec must not exceed "
            "target_tests_per_spec"
        )
    if links.get("instance_id") != instance_id:
        raise ValueError(
            f"Test/spec link instance_id {links.get('instance_id')!r} does not match {instance_id!r}"
        )
    specs = [str(value) for value in links.get("spec_sections") or []]
    if not specs:
        raise ValueError("Test/spec links contain no spec_sections")
    tests = sorted(
        (
            {
                "id": str(item.get("id", "")),
                "branch": str(item.get("branch", "")),
                "name": str(item.get("name", "")),
                "description": str(item.get("description", "")),
                "target_specs": [str(value) for value in item.get("target_specs") or []],
            }
            for item in links.get("test_functions") or []
            if isinstance(item, dict) and item.get("id")
        ),
        key=lambda item: item["id"],
    )
    spec_set = set(specs)
    for test in tests:
        unknown = sorted(set(test["target_specs"]) - spec_set)
        if unknown:
            raise ValueError(f"Test {test['id']} links to unknown specs: {unknown}")

    tests_by_spec = {
        spec: [test for test in tests if spec in test["target_specs"]]
        for spec in specs
    }
    test_degree = {test["id"]: len(test["target_specs"]) for test in tests}
    spec_degree = {spec: len(tests_by_spec[spec]) for spec in specs}
    slots = [(spec, slot) for slot in range(1, target_tests_per_spec + 1) for spec in specs]

    source = 0
    slot_offset = 1
    test_offset = slot_offset + len(slots)
    sink = test_offset + len(tests)
    graph: list[list[_Edge]] = [[] for _ in range(sink + 1)]
    test_nodes = {test["id"]: test_offset + index for index, test in enumerate(tests)}
    test_rank = {test["id"]: index for index, test in enumerate(tests)}
    slot_count = max(1, len(slots))
    max_ambiguity_cost = max(1, len(specs) * (len(tests) + 1) + max(0, len(tests) - 1))
    lower_tier_total = slot_count * (max_ambiguity_cost + len(tests))
    unmatched_cost_by_slot: dict[int, int] = {}
    for slot in range(target_tests_per_spec, 0, -1):
        penalty = lower_tier_total + 1
        unmatched_cost_by_slot[slot] = penalty
        lower_tier_total = slot_count * (penalty + max_ambiguity_cost + len(tests))
    assignment_edges: dict[tuple[str, int, str], _Edge] = {}

    for slot_index, (spec, slot) in enumerate(slots):
        slot_node = slot_offset + slot_index
        _add_edge(graph, source, slot_node, 1, 0)
        unmatched_cost = unmatched_cost_by_slot[slot]
        # Among equally fair plans, preserve scarce specs by making their unmatched slots costlier.
        unmatched_cost += max(0, len(tests) - spec_degree[spec])
        _add_edge(graph, slot_node, sink, 1, unmatched_cost)
        for test in tests_by_spec[spec]:
            ambiguity_cost = test_degree[test["id"]] * (len(tests) + 1) + test_rank[test["id"]]
            edge = _add_edge(graph, slot_node, test_nodes[test["id"]], 1, ambiguity_cost)
            assignment_edges[(spec, slot, test["id"])] = edge
    for test in tests:
        _add_edge(graph, test_nodes[test["id"]], sink, 1, 0)

    flow, objective_cost = _min_cost_flow(graph, source, sink, len(slots))
    if flow != len(slots):
        raise RuntimeError(f"Could route only {flow}/{len(slots)} mutant-plan slots")

    test_by_id = {test["id"]: test for test in tests}
    selected: list[tuple[str, int, dict[str, Any]]] = []
    unmatched: list[dict[str, Any]] = []
    for spec, slot in slots:
        chosen = [
            test_by_id[test_id]
            for test_id in sorted(test["id"] for test in tests_by_spec[spec])
            if assignment_edges[(spec, slot, test_id)].capacity == 0
            and assignment_edges[(spec, slot, test_id)].initial_capacity == 1
        ]
        if chosen:
            selected.append((spec, slot, chosen[0]))
        else:
            unmatched.append({"target_spec": spec, "slot": slot, "spec_degree": spec_degree[spec]})

    selected.sort(key=lambda item: (specs.index(item[0]), item[1], item[2]["id"]))
    assignments = []
    for index, (spec, slot, test) in enumerate(selected, start=1):
        assignments.append(
            {
                "mutant_id": f"repo_{index}",
                "target_spec": spec,
                "target_test": test["id"],
                "target_test_branch": test["branch"],
                "target_test_name": test["name"],
                "target_test_description": test["description"],
                "spec_slot": slot,
                "spec_degree": spec_degree[spec],
                "test_degree": test_degree[test["id"]],
            }
        )
    return {
        "instance_id": instance_id,
        "target_tests_per_spec": target_tests_per_spec,
        "final_mutants_per_spec": final_mutants_per_spec,
        "objective": [
            "maximize specs with a first mutant",
            "maximize specs with a second mutant",
            "prefer tests linked to fewer specs",
            "break remaining ties by test id",
        ],
        "spec_sections": specs,
        "assignments": assignments,
        "unmatched_spec_slots": unmatched,
        "complete": not unmatched,
        "objective_cost": objective_cost,
    }


def load_and_build_mutant_plan(
    links_path: Path, *, instance_id: str, target_tests_per_spec: int = 6,
    final_mutants_per_spec: int = 2,
) -> dict[str, Any]:
    if not links_path.is_file():
        raise FileNotFoundError(f"Test/spec links do not exist: {links_path}")
    return build_mutant_plan(
        json.loads(links_path.read_text()),
        instance_id=instance_id,
        target_tests_per_spec=target_tests_per_spec,
        final_mutants_per_spec=final_mutants_per_spec,
    )
