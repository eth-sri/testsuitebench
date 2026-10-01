from programbench.mutant_candidate_selection import (
    select_mutant_candidates,
)


def _candidate(candidate_id: str, target_test: str) -> dict[str, object]:
    return {
        "id": candidate_id,
        "assignment_id": candidate_id,
        "target_spec": "Spec 1",
        "target_test": target_test,
    }



def test_selection_prioritizes_singleton_focus() -> None:
    plan = {
        "assignments": [
            {"mutant_id": "repo_1", "target_spec": "Spec 1", "target_test": "test/a"},
            {"mutant_id": "repo_2", "target_spec": "Spec 1", "target_test": "test/b"},
            {"mutant_id": "repo_3", "target_spec": "Spec 1", "target_test": "test/c"},
        ],
        "spec_sections": ["Spec 1"],
        "final_mutants_per_spec": 2,
    }
    candidates = [
        _candidate("repo_1", "test/a"),
        _candidate("repo_2", "test/b"),
        _candidate("repo_3", "test/c"),
    ]
    result = select_mutant_candidates(
        plan=plan,
        candidates=candidates,
        kill_sets={
            "repo_1": ["test/a", "test/x"],
            "repo_2": ["test/b"],
            "repo_3": ["test/c"],
        },
    )

    assert result["selected"] == {"repo_1": "repo_2", "repo_2": "repo_3"}
    assert result["exact_singletons"] == 2
    assert "diversity_satisfied" not in result
