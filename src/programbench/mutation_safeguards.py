"""Detect test functions whose mutation reach is suspiciously broad."""

from __future__ import annotations

from typing import Any


DOMINANT_MUTANT_KILL_FRACTION = 0.5
DOMINANT_OBSERVED_KILL_FRACTION = 0.5
DOMINANT_OBSERVED_KILL_MIN_COUNT = 3


def _killed_by_test(
    kill_sets: dict[str, list[str]], mutant_ids: set[str]
) -> dict[str, set[str]]:
    killed_by_test: dict[str, set[str]] = {}
    for mutant_id in mutant_ids:
        for test in kill_sets.get(mutant_id, []):
            killed_by_test.setdefault(test, set()).add(mutant_id)
    return killed_by_test


def dominant_tests_from_kill_sets(
    kill_sets: dict[str, list[str]],
    *,
    mutant_ids: set[str] | None = None,
    threshold: float = DOMINANT_MUTANT_KILL_FRACTION,
) -> list[dict[str, Any]]:
    """Return tests killing strictly more than ``threshold`` of all mutants."""
    ids = set(kill_sets) if mutant_ids is None else set(mutant_ids)
    total = len(ids)
    if total == 0:
        return []
    killed_by_test = _killed_by_test(kill_sets, ids)
    return [
        {
            "test": test,
            "killed_mutants": sorted(killed),
            "killed": len(killed),
            "total_mutants": total,
            "kill_fraction": len(killed) / total,
        }
        for test, killed in sorted(killed_by_test.items())
        if len(killed) / total > threshold
    ]


def concentrated_tests_from_kill_sets(
    kill_sets: dict[str, list[str]],
    *,
    mutant_ids: set[str] | None = None,
    threshold: float = DOMINANT_OBSERVED_KILL_FRACTION,
    min_kills: int = DOMINANT_OBSERVED_KILL_MIN_COUNT,
) -> list[dict[str, Any]]:
    """Return tests responsible for most observed mutant kills.

    ``min_kills`` avoids warnings when only one or two mutants happen to be killed.
    """
    ids = set(kill_sets) if mutant_ids is None else set(mutant_ids)
    observed_ids = {mutant_id for mutant_id in ids if kill_sets.get(mutant_id)}
    total_observed = len(observed_ids)
    if total_observed == 0:
        return []
    killed_by_test = _killed_by_test(kill_sets, observed_ids)
    return [
        {
            "test": test,
            "killed_mutants": sorted(killed),
            "killed": len(killed),
            "total_killed_mutants": total_observed,
            "kill_concentration": len(killed) / total_observed,
        }
        for test, killed in sorted(killed_by_test.items())
        if len(killed) >= min_kills and len(killed) / total_observed > threshold
    ]
