import pytest

from programbench.mutant_candidate_selection import select_mutant_candidates
from programbench.mutant_planning import build_mutant_plan


def _links(test_count: int = 6) -> dict[str, object]:
    return {
        "instance_id": "org__repo.123",
        "spec_sections": ["Spec 1"],
        "test_functions": [
            {
                "id": f"branch/test_{index}",
                "branch": "branch",
                "name": f"test_{index}",
                "description": f"Checks behavior {index}.",
                "target_specs": ["Spec 1"],
            }
            for index in range(1, test_count + 1)
        ],
    }


def test_default_plan_samples_six_tests_and_retains_two() -> None:
    plan = build_mutant_plan(_links(), instance_id="org__repo.123")

    assert plan["target_tests_per_spec"] == 6
    assert plan["final_mutants_per_spec"] == 2
    assert len(plan["assignments"]) == 6
    assert len({item["target_test"] for item in plan["assignments"]}) == 6


def test_portfolio_selects_two_best_targets_from_six() -> None:
    plan = build_mutant_plan(_links(), instance_id="org__repo.123")
    candidates = []
    kill_sets = {}
    for index, assignment in enumerate(plan["assignments"], start=1):
        candidate_id = str(assignment["mutant_id"])
        candidates.append(
            {
                "id": candidate_id,
                "assignment_id": assignment["mutant_id"],
                "target_spec": assignment["target_spec"],
                "target_test": assignment["target_test"],
            }
        )
        kill_sets[candidate_id] = [assignment["target_test"]]
        if index <= 4:
            kill_sets[candidate_id].append("branch/collateral")

    result = select_mutant_candidates(plan=plan, candidates=candidates, kill_sets=kill_sets)

    assert result["selected"] == {
        "repo_1": "repo_5",
        "repo_2": "repo_6",
    }
    assert result["selected_per_spec"] == {"Spec 1": 2}
    assert result["exact_singletons"] == 2
    assert len({item["target_test"] for item in result["selections"]}) == 2


def test_final_total_cannot_exceed_target_test_pool() -> None:
    with pytest.raises(ValueError, match="must not exceed"):
        build_mutant_plan(
            _links(),
            instance_id="org__repo.123",
            target_tests_per_spec=2,
            final_mutants_per_spec=3,
        )
