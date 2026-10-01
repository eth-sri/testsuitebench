"""Empirically select focused, diverse mutants from generated candidates."""

from __future__ import annotations

from collections import defaultdict
from typing import Any



def candidate_assignment_id(candidate: dict[str, Any]) -> str:
    assignment_id = str(candidate.get("assignment_id", "")).strip()
    if assignment_id:
        return assignment_id
    candidate_id = str(candidate.get("id", ""))
    return candidate_id.partition("__candidate_")[0]


def _candidate_metrics(candidate: dict[str, Any], kill_sets: dict[str, list[str]]) -> dict[str, Any]:
    candidate_id = str(candidate["id"])
    target_test = str(candidate["target_test"])
    observed = sorted(set(kill_sets.get(candidate_id, [])))
    collateral = sorted(set(observed) - {target_test})
    return {
        "observed_kill_set": observed,
        "target_killed": target_test in observed,
        "exact_singleton": observed == [target_test],
        "collateral_kills": collateral,
        "collateral_kill_count": len(collateral),
        "killed_by_any_test": bool(observed),
    }


def _scored_candidate(
    candidate: dict[str, Any],
    *,
    metrics: dict[str, Any],
    invalid_candidate_ids: set[str],
    previous: list[dict[str, Any]],
) -> tuple[int, int, int, int, int]:
    new_target = str(candidate["target_test"]) not in {str(item["target_test"]) for item in previous}
    return (
        int(str(candidate["id"]) not in invalid_candidate_ids),
        int(metrics["target_killed"]),
        int(metrics["exact_singleton"]),
        -int(metrics["collateral_kill_count"]),
        int(new_target),
    )


def select_mutant_candidates(
    *,
    plan: dict[str, Any],
    candidates: list[dict[str, Any]],
    kill_sets: dict[str, list[str]],
    invalid_candidate_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Select a focused portfolio, with legacy one-per-assignment behavior for old plans."""
    invalid_candidate_ids = invalid_candidate_ids or set()
    assignments = list(plan.get("assignments", []))
    assignment_by_id = {str(item["mutant_id"]): item for item in assignments}
    by_assignment: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_assignment[candidate_assignment_id(candidate)].append(candidate)
    unexpected = sorted(set(by_assignment) - set(assignment_by_id))
    missing = sorted(set(assignment_by_id) - set(by_assignment))
    if missing or unexpected:
        raise ValueError(f"Candidate assignments do not match the mutant plan: missing={missing}, unexpected={unexpected}")

    # Plans written before portfolio selection retain one winner per assignment.
    portfolio_size = plan.get("final_mutants_per_spec")
    specs = list(plan.get("spec_sections") or dict.fromkeys(str(item["target_spec"]) for item in assignments))
    desired_by_spec = {
        spec: int(portfolio_size) if portfolio_size is not None else sum(
            str(item["target_spec"]) == spec for item in assignments
        )
        for spec in specs
    }
    selected: dict[str, str] = {}
    selections: list[dict[str, Any]] = []
    candidate_evaluations: list[dict[str, Any]] = []
    final_index = 1

    for spec in specs:
        pool = sorted(
            (
                candidate
                for candidate in candidates
                if str(candidate["target_spec"]) == spec
            ),
            key=lambda item: str(item["id"]),
        )
        metrics_by_id = {str(item["id"]): _candidate_metrics(item, kill_sets) for item in pool}
        for candidate in pool:
            candidate_evaluations.append({
                "id": candidate["id"],
                "assignment_id": candidate_assignment_id(candidate),
                "target_spec": candidate["target_spec"],
                "target_test": candidate["target_test"],
                "evaluation_valid": str(candidate["id"]) not in invalid_candidate_ids,
                **metrics_by_id[str(candidate["id"])],
            })

        selected_for_spec: list[dict[str, Any]] = []
        for _ in range(min(desired_by_spec[spec], len(pool))):
            ranked = []
            for candidate in pool:
                metrics = metrics_by_id[str(candidate["id"])]
                score = _scored_candidate(
                    candidate,
                    metrics=metrics,
                    invalid_candidate_ids=invalid_candidate_ids,
                    previous=selected_for_spec,
                )
                ranked.append((score, str(candidate["id"]), candidate, metrics))
            best_score = max(item[0] for item in ranked)
            _score, _candidate_id, winner, winner_metrics = min(
                (item for item in ranked if item[0] == best_score), key=lambda item: item[1]
            )
            final_id = (
                candidate_assignment_id(winner)
                if portfolio_size is None
                else f"repo_{final_index}"
            )
            final_index += 1
            selected[final_id] = str(winner["id"])
            selected_for_spec.append(winner)
            selections.append({
                "final_id": final_id,
                "assignment_id": candidate_assignment_id(winner),
                "target_spec": winner["target_spec"],
                "target_test": winner["target_test"],
                "selected_candidate": winner["id"],
                **winner_metrics,
            })
            pool.remove(winner)

    selected_counts = {spec: sum(item["target_spec"] == spec for item in selections) for spec in specs}
    return {
        "selection_mode": "spec_portfolio_target_singleton_then_collateral_then_target",
        "target_tests_per_spec": plan.get("target_tests_per_spec"),
        "final_mutants_per_spec": portfolio_size,
        "selections": selections,
        "candidate_evaluations": candidate_evaluations,
        "selected": selected,
        "selected_per_spec": selected_counts,
        "unfilled_final_slots": {
            spec: desired_by_spec[spec] - selected_counts[spec]
            for spec in specs
            if selected_counts[spec] < desired_by_spec[spec]
        },
        "target_killed": sum(bool(item["target_killed"]) for item in selections),
        "exact_singletons": sum(bool(item["exact_singleton"]) for item in selections),
    }
