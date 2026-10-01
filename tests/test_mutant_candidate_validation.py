import json

from programbench.eval.test_suite_eval import (
    BinaryTestSuiteResult,
    TestResult,
    TestSuiteEvaluationResult,
)
from programbench.mutant_kill_validation import ensure_mutants_killed


def _evaluation(ids_and_failures: dict[str, list[str]]) -> TestSuiteEvaluationResult:
    tests = ["branch/test_a", "branch/test_b", "branch/test_other"]
    binaries = [
        BinaryTestSuiteResult(
            binary_id="ground_truth",
            role="ground_truth",
            test_results=[TestResult(name=name, status="passed", extra={}) for name in tests],
        )
    ]
    for candidate_id, failures in ids_and_failures.items():
        binaries.append(
            BinaryTestSuiteResult(
                binary_id=candidate_id,
                role="candidate",
                test_results=[
                    TestResult(
                        name=name,
                        status="failure" if name in failures else "passed",
                        extra={},
                    )
                    for name in tests
                ],
            )
        )
    return TestSuiteEvaluationResult(binary_results=binaries)


def test_validation_selects_candidates_and_canonicalizes_repositories(tmp_path) -> None:
    task = "org__repo.123"
    tests_root = tmp_path / "tests"
    mutants_root = tmp_path / "mutants"
    spec_root = tmp_path / "spec"
    (tests_root / task).mkdir(parents=True)
    (spec_root / task).mkdir(parents=True)
    (spec_root / task / "spec.md").write_text("## Spec 1\n")
    task_mutants = mutants_root / task
    task_mutants.mkdir(parents=True)
    assignments = [
        {"mutant_id": "repo_1", "target_spec": "Spec 1", "target_test": "branch/test_a"},
        {"mutant_id": "repo_2", "target_spec": "Spec 1", "target_test": "branch/test_b"},
    ]
    (task_mutants / "mutant_plan.json").write_text(
        json.dumps({"instance_id": task, "assignments": assignments})
    )
    candidates = []
    candidate_ids = ["repo_1", "repo_2"]
    for candidate_id in candidate_ids:
        assignment_id = candidate_id
        assignment = next(item for item in assignments if item["mutant_id"] == assignment_id)
        repo = task_mutants / candidate_id
        repo.mkdir()
        (repo / "source.c").write_text(candidate_id)
        (repo / "executable").write_text("#!/bin/sh\n")
        candidates.append(
            {
                "id": candidate_id,
                "kind": "wrapper",
                "assignment_id": assignment_id,
                "candidate_index": 1,
                "target_spec": assignment["target_spec"],
                "target_test": assignment["target_test"],
                "mutation": candidate_id,
                "payload": f"{candidate_id}/executable",
            }
        )
    (task_mutants / "mutants.json").write_text(
        json.dumps({"instance_id": task, "mutants": candidates})
    )

    candidate_result = _evaluation(
        {
            "repo_1": ["branch/test_a"],
            "repo_2": ["branch/test_b"],
        }
    )
    canonical_result = _evaluation(
        {"repo_1": ["branch/test_a"], "repo_2": ["branch/test_b"]}
    )
    report = ensure_mutants_killed(
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        max_repair_attempts=0,
        evaluator=lambda attempt: candidate_result if attempt == -1 else canonical_result,
    )

    assert report["candidate_selection"] is None
    assert (task_mutants / "repo_1" / "source.c").read_text() == "repo_1"
    assert (task_mutants / "repo_2" / "source.c").read_text() == "repo_2"
    assert not list(task_mutants.glob("repo_*__candidate_*"))
    final_manifest = json.loads((task_mutants / "mutants.json").read_text())
    assert [item["id"] for item in final_manifest["mutants"]] == ["repo_1", "repo_2"]
