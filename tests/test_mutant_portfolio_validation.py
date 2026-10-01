import json

from programbench.eval.test_suite_eval import (
    BinaryTestSuiteResult,
    TestResult,
    TestSuiteEvaluationResult,
)
from programbench.mutant_kill_validation import _select_generated_candidates


def test_candidate_evaluation_prunes_and_reindexes_final_portfolio(tmp_path, caplog) -> None:
    task = "org__repo.123"
    tests_root = tmp_path / "tests"
    task_mutants = tmp_path / "mutants" / task
    tests_root.mkdir()
    (tmp_path / "work").mkdir()
    task_mutants.mkdir(parents=True)
    assignments = [
        {
            "mutant_id": f"repo_{index}",
            "target_spec": "Spec 1",
            "target_test": f"branch/test_{index}",
        }
        for index in range(1, 4)
    ]
    (task_mutants / "mutant_plan.json").write_text(
        json.dumps(
            {
                "instance_id": task,
                "spec_sections": ["Spec 1"],
                "target_tests_per_spec": 3,
                "final_mutants_per_spec": 2,
                "assignments": assignments,
            }
        )
    )
    mutants = []
    for index, assignment in enumerate(assignments, start=1):
        repo = task_mutants / assignment["mutant_id"]
        repo.mkdir()
        (repo / "source.c").write_text(f"candidate {index}")
        (repo / "executable").write_text("#!/bin/sh\n")
        mutants.append(
            {
                "id": assignment["mutant_id"],
                "assignment_id": assignment["mutant_id"],
                "candidate_index": 1,
                "kind": "wrapper",
                "target_spec": "Spec 1",
                "target_test": assignment["target_test"],
                "mutation": f"mutation {index}",
                "payload": f"{assignment['mutant_id']}/executable",
            }
        )
    (task_mutants / "mutants.json").write_text(
        json.dumps({"instance_id": task, "mutants": mutants})
    )

    tests = ["branch/test_1", "branch/test_2", "branch/test_3", "branch/collateral"]
    failures = {
        "repo_1": ["branch/test_1", "branch/collateral"],
        "repo_2": ["branch/test_2", "branch/collateral"],
        "repo_3": ["branch/test_3"],
    }
    binaries = [
        BinaryTestSuiteResult(
            binary_id="ground_truth",
            role="ground_truth",
            test_results=[TestResult(name=name, status="passed", extra={}) for name in tests],
        )
    ]
    for mutant_id, failed in failures.items():
        binaries.append(
            BinaryTestSuiteResult(
                binary_id=mutant_id,
                role="candidate",
                test_results=[
                    TestResult(
                        name=name,
                        status="failure" if name in failed else "passed",
                        extra={},
                    )
                    for name in tests
                ],
            )
        )
    evaluation = TestSuiteEvaluationResult(binary_results=binaries)
    failing_ground_truth = binaries[0].model_copy(
        update={
            "test_results": binaries[0].test_results + [
                TestResult(name="branch/flaky", status="failure", extra={})
            ]
        }
    )
    failing_evaluation = TestSuiteEvaluationResult(
        binary_results=[failing_ground_truth, *binaries[1:]]
    )
    filtered_evaluation = TestSuiteEvaluationResult(binary_results=[
        binary.model_copy(update={
            "test_results": [test for test in binary.test_results if test.name != "branch/collateral"]
        })
        for binary in binaries
    ])
    evaluations = iter([failing_evaluation, evaluation, filtered_evaluation])
    evaluation_attempts = []

    def evaluator(attempt):
        evaluation_attempts.append(attempt)
        return next(evaluations)

    skipped_tests = tmp_path / "skipped-tests"
    skipped_tests.mkdir()
    (skipped_tests / f"{task}.json").write_text(
        json.dumps({"instance_id": task, "skipped_tests": []})
    )

    selection = _select_generated_candidates(
        task=task,
        tests_root=tests_root,
        mutants_root=tmp_path / "mutants",
        work_dir=tmp_path / "work",
        skipped_tests=skipped_tests,
        workers=1,
        branch_workers=1,
        cpu_budget=0,
        evaluator=evaluator,
    )

    assert selection is not None
    assert selection["selected"] == {"repo_1": "repo_1", "repo_2": "repo_2"}
    assert evaluation_attempts == [-1, -1, -1]
    assert "continuing after reevaluation: branch/flaky" in caplog.text
    assert selection["ground_truth_skip_updates"][0] == (
        {
            "reason": "our_gt_gold_fail",
            "phase": "candidate_selection",
            "validity_rate_before": 4 / 5,
            "tests": ["branch/flaky"],
        }
    )
    assert selection["ground_truth_skip_updates"][1]["reason"] == "our_gt_broad_mutant_kill"
    assert selection["ground_truth_skip_updates"][1]["tests"] == ["branch/collateral"]
    assert selection["ground_truth_skip_updates"][1]["test_kill_rates"][0]["killed"] == 2
    skipped = json.loads((skipped_tests / f"{task}.json").read_text())
    assert skipped["skipped_tests"] == [
        {"name": "branch/collateral", "reasons": [{"id": "our_gt_broad_mutant_kill"}]},
        {"name": "branch/flaky", "reasons": [{"id": "our_gt_gold_fail"}]},
    ]
    final = json.loads((task_mutants / "mutants.json").read_text())["mutants"]
    assert [item["id"] for item in final] == ["repo_1", "repo_2"]
    assert [item["assignment_id"] for item in final] == ["repo_1", "repo_2"]
    assert (task_mutants / "repo_1" / "source.c").read_text() == "candidate 1"
    assert (task_mutants / "repo_2" / "source.c").read_text() == "candidate 2"
    assert not (task_mutants / "repo_3").exists()


def test_applied_candidate_selection_is_reused_instead_of_re_decided(tmp_path) -> None:
    task = "org__repo.123"
    tests_root = tmp_path / "tests"
    task_mutants = tmp_path / "mutants" / task
    tests_root.mkdir()
    (tmp_path / "work").mkdir()
    task_mutants.mkdir(parents=True)
    assignments = [
        {"mutant_id": f"repo_{index}", "target_spec": "Spec 1", "target_test": f"branch/test_{index}"}
        for index in range(1, 4)
    ]
    (task_mutants / "mutant_plan.json").write_text(
        json.dumps(
            {
                "instance_id": task,
                "spec_sections": ["Spec 1"],
                "target_tests_per_spec": 3,
                "final_mutants_per_spec": 2,
                "assignments": assignments,
            }
        )
    )
    mutants = []
    for assignment in assignments:
        repo = task_mutants / assignment["mutant_id"]
        repo.mkdir()
        (repo / "executable").write_text("#!/bin/sh\n")
        mutants.append(
            {
                "id": assignment["mutant_id"],
                "assignment_id": assignment["mutant_id"],
                "candidate_index": 1,
                "kind": "wrapper",
                "target_spec": "Spec 1",
                "target_test": assignment["target_test"],
                "mutation": assignment["mutant_id"],
                "payload": f"{assignment['mutant_id']}/executable",
            }
        )
    (task_mutants / "mutants.json").write_text(json.dumps({"instance_id": task, "mutants": mutants}))

    tests = ["branch/test_1", "branch/test_2", "branch/test_3"]
    binaries = [
        BinaryTestSuiteResult(
            binary_id="ground_truth",
            role="ground_truth",
            test_results=[TestResult(name=name, status="passed", extra={}) for name in tests],
        )
    ]
    for index, name in enumerate(tests, start=1):
        binaries.append(
            BinaryTestSuiteResult(
                binary_id=f"repo_{index}",
                role="candidate",
                test_results=[
                    TestResult(name=test, status="failure" if test == name else "passed", extra={})
                    for test in tests
                ],
            )
        )
    evaluation = TestSuiteEvaluationResult(binary_results=binaries)

    arguments = dict(
        task=task,
        tests_root=tests_root,
        mutants_root=tmp_path / "mutants",
        work_dir=tmp_path / "work",
        skipped_tests=None,
        workers=1,
        branch_workers=1,
        cpu_budget=0,
    )
    first = _select_generated_candidates(**arguments, evaluator=lambda attempt: evaluation)
    assert first["selected"] == {"repo_1": "repo_1", "repo_2": "repo_2"}
    assert not (task_mutants / "repo_3").exists()
    assert json.loads((task_mutants / "candidate_selection.json").read_text())["selected"] == first["selected"]

    # The pruned store can no longer be evaluated or matched against the plan,
    # so a rerun must reuse the recorded decision rather than deciding again.
    def refuse(attempt):
        raise AssertionError("candidate evaluation must not rerun after selection was applied")

    second = _select_generated_candidates(**arguments, evaluator=refuse)
    assert second["selected"] == first["selected"]
    assert [item["id"] for item in json.loads((task_mutants / "mutants.json").read_text())["mutants"]] == [
        "repo_1",
        "repo_2",
    ]
