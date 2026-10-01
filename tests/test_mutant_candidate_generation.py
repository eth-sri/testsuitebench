from programbench.mutants import (
    _normalize_mutant_manifest,
    mutant_generation_prompt,
)


def _plan() -> dict[str, object]:
    return {
        "assignments": [
            {
                "mutant_id": "repo_1",
                "target_spec": "Spec 1",
                "target_test": "branch/test_one",
                "target_test_description": "asserts one",
            }
        ]
    }


def test_manifest_keeps_assignment_and_mutation() -> None:
    manifest = _normalize_mutant_manifest(
        {"mutants": [{"id": "repo_1", "mutation": "omit the error"}]},
        instance_id="org__repo.123",
        repo_names=["repo_1"],
        plan=_plan(),
    )

    mutant = manifest["mutants"][0]
    assert mutant["assignment_id"] == "repo_1"
    assert mutant["target_test"] == "branch/test_one"
    assert mutant["mutation"] == "omit the error"
    assert "behavioral_dimension" not in mutant
    assert "mutation_operator" not in mutant
    assert "mutation_location" not in mutant


def test_manifest_is_sorted_by_repo_number() -> None:
    plan = {
        "assignments": [
            {"mutant_id": "repo_10", "target_spec": "Spec 10", "target_test": "test_ten", "target_test_description": "ten"},
            {"mutant_id": "repo_2", "target_spec": "Spec 2", "target_test": "test_two", "target_test_description": "two"},
        ]
    }
    manifest = _normalize_mutant_manifest(
        {"mutants": []},
        instance_id="org__repo.123",
        repo_names=["repo_10", "repo_2"],
        plan=plan,
    )

    assert [mutant["id"] for mutant in manifest["mutants"]] == ["repo_2", "repo_10"]


def test_prompt_describes_one_mutant_per_assignment() -> None:
    prompt = mutant_generation_prompt()
    assert "Create exactly the mutants" in prompt
    assert "exactly one copy" in prompt
    assert "behavioral_dimension" not in prompt
    assert "mutation_operator" not in prompt
    assert "mutation_location" not in prompt
