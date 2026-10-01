from programbench.mutant_planning import build_mutant_plan


def _links(specs, links):
    return {
        "instance_id": "org__repo.123",
        "spec_sections": specs,
        "test_functions": [
            {
                "id": test_id,
                "branch": test_id.split("/", 1)[0],
                "name": test_id.split("/", 1)[1],
                "description": f"Checks {test_id}.",
                "target_specs": targets,
            }
            for test_id, targets in links
        ],
    }


def test_plan_assigns_two_unique_tests_per_spec_when_feasible() -> None:
    links = _links(
        ["Spec 1", "Spec 2"],
        [
            ("a/test_1", ["Spec 1"]),
            ("a/test_2", ["Spec 1"]),
            ("b/test_1", ["Spec 2"]),
            ("b/test_2", ["Spec 2"]),
            ("shared/test_both", ["Spec 1", "Spec 2"]),
        ],
    )

    plan = build_mutant_plan(links, instance_id="org__repo.123", mutants_per_spec=2)

    assert plan["complete"] is True
    assert plan["unmatched_spec_slots"] == []
    assert len(plan["assignments"]) == 4
    assert len({item["target_test"] for item in plan["assignments"]}) == 4
    assert [item["target_spec"] for item in plan["assignments"]].count("Spec 1") == 2
    assert [item["target_spec"] for item in plan["assignments"]].count("Spec 2") == 2
    assert all(item["test_degree"] == 1 for item in plan["assignments"])


def test_plan_prioritizes_one_assignment_per_spec_when_capacity_is_tight() -> None:
    links = _links(
        ["Spec 1", "Spec 2", "Spec 3"],
        [
            ("a/test_1", ["Spec 1", "Spec 2"]),
            ("b/test_2", ["Spec 2", "Spec 3"]),
            ("c/test_3", ["Spec 1", "Spec 3"]),
        ],
    )

    plan = build_mutant_plan(links, instance_id="org__repo.123", mutants_per_spec=2)

    assert plan["complete"] is False
    assert len(plan["assignments"]) == 3
    assert {item["target_spec"] for item in plan["assignments"]} == {"Spec 1", "Spec 2", "Spec 3"}
    assert {item["spec_slot"] for item in plan["assignments"]} == {1}
    assert len(plan["unmatched_spec_slots"]) == 3


def test_plan_is_deterministic() -> None:
    links = _links(
        ["Spec 1", "Spec 2"],
        [
            ("b/test_2", ["Spec 1", "Spec 2"]),
            ("a/test_1", ["Spec 1", "Spec 2"]),
        ],
    )

    first = build_mutant_plan(links, instance_id="org__repo.123")
    second = build_mutant_plan(links, instance_id="org__repo.123")

    assert first == second
