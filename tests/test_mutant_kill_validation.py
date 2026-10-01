import json
import logging
from pathlib import Path

import pytest

from programbench.eval.test_suite_eval import BinaryTestSuiteResult, TestResult, TestSuiteEvaluationResult
from programbench.mutant_kill_validation import (
    _REPAIR_BUILD_SCRIPT,
    _default_repair_runner,
    ensure_mutants_killed,
    mutant_kill_repair_prompt,
)


def _result(
    *, repo_1: str, repo_2: str, ground_truth: str = "passed", test_name: str = "branch/test_behavior",
) -> TestSuiteEvaluationResult:
    if test_name != "branch/test_behavior":
        tests = [test_name]
        ground_results = [TestResult(name=test_name, status=ground_truth, extra={})]
        repo_1_results = [TestResult(name=test_name, status=repo_1, extra={})]
        repo_2_results = [TestResult(name=test_name, status=repo_2, extra={})]
    else:
        tests = ["branch/test_behavior", "branch/test_other"]
        ground_results = [TestResult(name=name, status=ground_truth, extra={}) for name in tests]
        repo_1_results = [
            TestResult(name=tests[0], status=repo_1, extra={}),
            TestResult(name=tests[1], status="passed", extra={}),
        ]
        repo_2_results = [
            TestResult(name=tests[0], status="passed", extra={}),
            TestResult(name=tests[1], status=repo_2, extra={}),
        ]
    return TestSuiteEvaluationResult(binary_results=[
        BinaryTestSuiteResult(
            binary_id="ground_truth", role="ground_truth",
            test_results=ground_results,
        ),
        BinaryTestSuiteResult(
            binary_id="repo_1", role="candidate",
            test_results=repo_1_results,
        ),
        BinaryTestSuiteResult(
            binary_id="repo_2", role="candidate",
            test_results=repo_2_results,
        ),
    ])


def _layout(tmp_path: Path) -> tuple[str, Path, Path, Path, Path]:
    task = "org__repo.123"
    tests_root = tmp_path / "extracted-tests"
    mutants_root = tmp_path / "mutants"
    spec_root = tmp_path / "spec"
    (tests_root / task).mkdir(parents=True)
    (tests_root / task / "test.py").write_text("def test_behavior(): pass\n")
    (spec_root / task).mkdir(parents=True)
    (spec_root / task / "spec.md").write_text("## Spec 1\nPrint the version.\n")
    for mid in ("repo_1", "repo_2"):
        repo = mutants_root / task / mid
        repo.mkdir(parents=True)
        (repo / "source.c").write_text(f"/* {mid} */\n")
        (repo / "executable").write_text("#!/bin/sh\n")
    manifest = {
        "instance_id": task,
        "mutants": [
            {"id": "repo_1", "kind": "wrapper", "target_spec": "Spec 1", "target_test": "branch/test_behavior", "mutation": "wrong version A", "payload": "repo_1/executable"},
            {"id": "repo_2", "kind": "wrapper", "target_spec": "Spec 1", "target_test": "branch/test_other", "mutation": "wrong version B", "payload": "repo_2/executable"},
        ],
    }
    (mutants_root / task / "mutants.json").write_text(json.dumps(manifest))
    (mutants_root / task / "mutant_plan.json").write_text(json.dumps({
        "instance_id": task,
        "assignments": [
            {"mutant_id": "repo_1", "target_spec": "Spec 1", "target_test": "branch/test_behavior"},
            {"mutant_id": "repo_2", "target_spec": "Spec 1", "target_test": "branch/test_other"},
        ],
    }))
    skipped = tmp_path / "skipped-tests"
    skipped.mkdir()
    (skipped / f"{task}.json").write_text(json.dumps({"instance_id": task, "skipped_tests": []}))
    return task, tests_root, mutants_root, spec_root, skipped


def test_ensure_mutants_killed_repairs_only_survivors_and_rechecks(tmp_path: Path) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    evaluations = [
        _result(repo_1="passed", repo_2="failure"),
        _result(repo_1="passed", repo_2="failure"),
        _result(repo_1="failure", repo_2="failure"),
    ]
    repairs = 0

    def repair_runner(prompt: str, workspace: Path):
        nonlocal repairs
        repairs += 1
        assert "repo_1" in prompt
        assert (workspace / "skipped_tests.json").is_file()
        (workspace / "mutants" / "repo_1" / "source.c").write_text("/* stronger */\n")
        (workspace / "mutants" / "repo_1" / "executable").write_text("#!/bin/sh\n")
        return {"returncode": 0}

    report = ensure_mutants_killed(
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=2,
        evaluator=lambda attempt: evaluations[attempt],
        repair_runner=repair_runner,
    )

    assert repairs == 2
    assert report["verified"] is True
    assert report["target_mutation_score"] == 1.0
    assert report["added_skipped_tests"] == []


def test_incremental_evaluation_merges_changed_mutants_with_cached_results(
    tmp_path: Path,
) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    full_result = _result(repo_1="passed", repo_2="failure")
    changed_result = TestSuiteEvaluationResult(binary_results=[
        BinaryTestSuiteResult(
            binary_id="ground_truth", role="ground_truth",
            test_results=[
                TestResult(name="branch/test_behavior", status="passed", extra={}),
                TestResult(name="branch/test_other", status="passed", extra={}),
            ],
        ),
        BinaryTestSuiteResult(
            binary_id="repo_1", role="candidate",
            test_results=[
                TestResult(name="branch/test_behavior", status="failure", extra={}),
                TestResult(name="branch/test_other", status="passed", extra={}),
            ],
        ),
    ])
    evaluations = iter([full_result, changed_result])

    def repair_runner(_prompt: str, workspace: Path):
        (workspace / "mutants" / "repo_1" / "executable").write_text("#!/bin/sh\n")
        return {
            "returncode": 0,
            "changed_ids": ["repo_1"],
            "changed_mutants": {"repo_1": "strengthened"},
            "kept_as_is": {},
        }

    report = ensure_mutants_killed(
        task=task, tests_root=tests_root, mutants_root=mutants_root,
        spec_root=spec_root, work_dir=tmp_path / "work", skipped_tests=skipped,
        max_repair_attempts=1, evaluator=lambda _attempt: next(evaluations),
        repair_runner=repair_runner,
    )

    assert report["verified"] is True
    assert report["attempts"][1]["evaluation_mode"] == "incremental"
    assert report["attempts"][1]["reevaluated_ids"] == ["repo_1"]
    assert report["attempts"][1]["evaluated"] == 2
    assert report["attempts"][1]["kill_sets"] == {
        "repo_1": ["branch/test_behavior"],
        "repo_2": ["branch/test_other"],
    }


def test_iteration_summary_reports_baseline_and_progress(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)

    with caplog.at_level("INFO", logger="programbench.mutant_kill_validation"):
        ensure_mutants_killed(
            task=task, tests_root=tests_root, mutants_root=mutants_root,
            spec_root=spec_root, work_dir=tmp_path / "work", skipped_tests=skipped,
            max_repair_attempts=1,
            evaluator=lambda attempt: _result(
                repo_1="failure" if attempt else "passed", repo_2="failure",
            ),
            repair_runner=lambda _prompt, _workspace: {"returncode": 0},
        )

    assert (
        "Mutant validation iteration 0 for org__repo.123: exact singletons 1/2, "
        "target-killed 1/2, collateral kills 0, remaining 1 (baseline)"
    ) in caplog.messages
    assert (
        "Mutant validation iteration 1 for org__repo.123: exact singletons 2/2, "
        "target-killed 2/2, collateral kills 0, remaining 0 "
        "(change: exact +1, target-killed +1, collateral +0, remaining -1)"
    ) in caplog.messages
    assert any(
        message.startswith(
            "Starting Codex mutant repair request 1/1 for org__repo.123: "
            "1 mutant(s) [repo_1]"
        )
        for message in caplog.messages
    )
    assert any(
        message.startswith(
            "Codex mutant repair request 1/1 for org__repo.123 returned in "
        )
        for message in caplog.messages
    )
    assert (
        "Completed mutant repair request 1/1 for org__repo.123: applied 1 [repo_1], "
        "kept as-is 0 [none]; next step: incremental reference-suite reevaluation"
    ) in caplog.messages


def test_ground_truth_failure_extends_skip_list_without_editing_tests(tmp_path: Path) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    flaky = "branch/eval.tests.test_flaky.test_flaky[param]"
    source = tests_root / task / "test.py"
    original = source.read_text()
    calls = 0

    def evaluator(_attempt: int) -> TestSuiteEvaluationResult:
        nonlocal calls
        calls += 1
        document = json.loads((skipped / f"{task}.json").read_text())
        names = {item["name"] for item in document["skipped_tests"]}
        if "branch/eval.tests.test_flaky.test_flaky" not in names:
            return _result(repo_1="failure", repo_2="failure", ground_truth="failure", test_name=flaky)
        return _result(repo_1="failure", repo_2="failure", test_name="branch/test_behavior")

    report = ensure_mutants_killed(
        prune_failing_tests=True,
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=0,
        evaluator=evaluator,
    )

    assert calls == 2
    assert report["verified"] is True
    assert source.read_text() == original
    document = json.loads((skipped / f"{task}.json").read_text())
    assert [item["name"] for item in document["skipped_tests"]] == [
        "branch/eval.tests.test_flaky.test_flaky"
    ]
    assert report["added_skipped_tests"][0]["reason"] == "our_gt_gold_fail"


def test_ground_truth_test_killing_exactly_half_of_mutants_is_not_skipped(tmp_path: Path) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    report = ensure_mutants_killed(
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=0,
        evaluator=lambda _attempt: _result(repo_1="failure", repo_2="failure"),
    )

    assert report["verified"] is True
    document = json.loads((skipped / f"{task}.json").read_text())
    assert document["skipped_tests"] == []


def test_ground_truth_failure_is_tolerated_without_pruning_by_default(tmp_path: Path) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    calls = 0

    def evaluator(_attempt: int) -> TestSuiteEvaluationResult:
        nonlocal calls
        calls += 1
        result = _result(repo_1="failure", repo_2="failure")
        # The reference fails branch/test_other; the suite must still be used.
        ground_truth = result.binary_results[0]
        ground_truth.test_results[1].status = "failure"
        return result

    report = ensure_mutants_killed(
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=0,
        evaluator=evaluator,
    )

    assert calls == 1
    assert report["added_skipped_tests"] == []
    assert not (skipped / f"{task}.json").exists() or not json.loads(
        (skipped / f"{task}.json").read_text()
    )["skipped_tests"]


def test_ground_truth_tests_killing_more_than_half_are_skipped(tmp_path: Path) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    result = TestSuiteEvaluationResult(binary_results=[
        BinaryTestSuiteResult(
            binary_id="ground_truth", role="ground_truth",
            test_results=[
                TestResult(name="branch/test_behavior", status="passed", extra={}),
                TestResult(name="branch/test_other", status="passed", extra={}),
            ],
        ),
        *[
            BinaryTestSuiteResult(
                binary_id=mutant_id, role="candidate",
                test_results=[
                    TestResult(name="branch/test_behavior", status="failure", extra={}),
                    TestResult(name="branch/test_other", status="failure", extra={}),
                ],
            )
            for mutant_id in ("repo_1", "repo_2")
        ],
    ])

    report = ensure_mutants_killed(
        prune_failing_tests=True,
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=0,
        evaluator=lambda _attempt: result,
    )

    assert report["verified"] is True
    assert report["best_effort_kept_as_is"] == ["repo_1", "repo_2"]
    assert report["attempts"][0]["dominant_kill_skip_update"]["tests"] == [
        "branch/test_behavior", "branch/test_other",
    ]
    assert report["attempts"][0]["dominant_kill_skip_update"]["threshold"] == 0.5
    assert report["attempts"][0]["kill_sets"]["repo_1"] == ["branch/test_behavior", "branch/test_other"]
    document = json.loads((skipped / f"{task}.json").read_text())
    assert document["skipped_tests"] == [
        {"name": "branch/test_behavior", "reasons": [{"id": "our_gt_broad_mutant_kill"}]},
        {"name": "branch/test_other", "reasons": [{"id": "our_gt_broad_mutant_kill"}]},
    ]


def test_failed_repair_consumes_attempt_and_exhaustion_is_best_effort(tmp_path: Path) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    repairs = 0
    evaluations = 0

    def evaluator(_attempt: int):
        nonlocal evaluations
        evaluations += 1
        return _result(repo_1="passed", repo_2="failure")

    def repair_runner(_prompt: str, _workspace: Path):
        nonlocal repairs
        repairs += 1
        return {"returncode": -1, "exception_info": "timed out", "usage_calls": 0}

    report = ensure_mutants_killed(
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=2,
        evaluator=evaluator,
        repair_runner=repair_runner,
    )

    assert repairs == 2
    assert report["verified"] is True
    assert evaluations == 1
    assert [attempt["evaluation_mode"] for attempt in report["attempts"]] == [
        "full", "reused", "reused",
    ]
    assert [attempt["reevaluated_ids"] for attempt in report["attempts"]] == [
        ["repo_1", "repo_2"], [], [],
    ]
    assert report["attempts"][-1]["repair_budget_exhausted"] is True
    assert report["best_effort_kept_as_is"] == ["repo_1"]
    assert all("repair_error" in attempt for attempt in report["attempts"][:-1])


def test_ground_truth_failure_requires_skip_list(tmp_path: Path) -> None:
    task, tests_root, mutants_root, spec_root, _skipped = _layout(tmp_path)
    with pytest.raises(RuntimeError, match="skip.*list"):
        ensure_mutants_killed(
        prune_failing_tests=True,
            task=task,
            tests_root=tests_root,
            mutants_root=mutants_root,
            spec_root=spec_root,
            work_dir=tmp_path / "work",
            evaluator=lambda _attempt: _result(repo_1="passed", repo_2="passed", ground_truth="failure"),
        )


def test_ground_truth_pytest_internal_retries_without_changing_parallelism_or_skip_list(
    tmp_path: Path,
) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    infrastructure_result = _result(
        repo_1="error",
        repo_2="error",
        ground_truth="error",
        test_name="branch/pytest.internal",
    )
    recovered_result = _result(repo_1="failure", repo_2="failure")
    results = iter([infrastructure_result, recovered_result])
    evaluations = 0

    def evaluator(_attempt: int) -> TestSuiteEvaluationResult:
        nonlocal evaluations
        evaluations += 1
        return next(results)

    report = ensure_mutants_killed(
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=0,
        max_infrastructure_retries=2,
        branch_workers=16,
        evaluator=evaluator,
    )

    assert evaluations == 2
    assert report["verified"] is True
    assert report["attempts"][0]["infrastructure_retry"] == {
        "retry": 1,
        "max_retries": 2,
        "failures": ["branch/pytest.internal"],
    }
    assert report["attempts"][1]["evaluation_retry"] == 1
    assert report["added_skipped_tests"] == []
    assert json.loads((skipped / f"{task}.json").read_text())["skipped_tests"] == []


def test_mutant_kill_prompt_preserves_initial_scope() -> None:
    prompt = mutant_kill_repair_prompt(task="org__repo.123", attempt=1, affected_ids=["repo_1"])
    assert "original `target_spec` and `target_test` unchanged" in prompt
    assert "Do not add, remove, rename, or merge mutants" in prompt
    assert "Never modify tests" in prompt
    assert "skipped_tests.json" in prompt
    assert "leave that mutant completely unchanged" in prompt
    assert "repair_outcome.json" in prompt


def test_default_repair_runner_rebuilds_only_changed_mutants(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def run_codex(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        (tmp_path / "repair_outcome.json").write_text(json.dumps({
            "changed_mutants": {"repo_1": "edited"},
            "kept_as_is": {"repo_13": "overlapping immutable tests"},
        }))
        return {"returncode": 0}

    monkeypatch.setattr("programbench.mutant_kill_validation.run_codex_in_container", run_codex)

    result = _default_repair_runner(
        "repair",
        tmp_path,
        affected_ids=["repo_1", "repo_13"],
        model="codex/gpt-test",
        reasoning_effort="high",
        codex_command="codex exec --cd /workspace",
        timeout=10,
        image="programbench/example:task_cleanroom_codex",
    )

    assert result["returncode"] == 0
    assert "repair_outcome.json" in captured["command"]
    assert "shutil.rmtree(repo / \"build\"" in captured["command"]
    assert captured["command"].endswith(" 0 repo_1 repo_13")
    assert result["changed_ids"] == ["repo_1"]
    assert result["kept_as_is"] == {"repo_13": "overlapping immutable tests"}
    assert captured["copy_back_files"] == ["repair_outcome.json"]
    assert captured["image"] == "programbench/example:task_cleanroom_codex"
    assert captured["copy_back_dirs"] == [
        tmp_path / "mutants" / "repo_1",
        tmp_path / "mutants" / "repo_13",
    ]


def test_default_repair_runner_keeps_source_build_dir(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def run_codex(command, **kwargs):
        captured["command"] = command
        (tmp_path / "repair_outcome.json").write_text(json.dumps({"changed_mutants": {"repo_1": "edited"}, "kept_as_is": {}}))
        return {"returncode": 0}

    monkeypatch.setattr("programbench.mutant_kill_validation.run_codex_in_container", run_codex)
    _default_repair_runner(
        "repair", tmp_path, affected_ids=["repo_1"], model="codex/gpt-test", reasoning_effort="high",
        codex_command="codex exec --cd /workspace", timeout=10, image="programbench/example:task_cleanroom_codex",
        keep_build_dir=True,
    )
    assert captured["command"].endswith(" 1 repo_1")


def test_best_effort_no_change_skips_rebuild_and_saves_compact_trajectory(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    result = TestSuiteEvaluationResult(binary_results=[
        BinaryTestSuiteResult(
            binary_id="ground_truth", role="ground_truth",
            test_results=[
                TestResult(name="branch/test_behavior", status="passed", extra={}),
                TestResult(name="branch/test_other", status="passed", extra={}),
            ],
        ),
        *[
            BinaryTestSuiteResult(
                binary_id=mutant_id, role="candidate",
                test_results=[
                    TestResult(
                        name="branch/test_behavior",
                        status="passed" if mutant_id == "repo_1" else "failure",
                        extra={},
                    ),
                    TestResult(
                        name="branch/test_other",
                        status="failure" if mutant_id == "repo_1" else "passed",
                        extra={},
                    ),
                ],
            )
            for mutant_id in ("repo_1", "repo_2")
        ],
    ])
    evaluations = 0

    def evaluator(_attempt: int) -> TestSuiteEvaluationResult:
        nonlocal evaluations
        evaluations += 1
        return result

    raw_event = '{"type":"item.completed","item":{"type":"agent_message","text":"impossible"}}\n'
    caplog.set_level(logging.INFO, logger="programbench.mutant_kill_validation")
    report = ensure_mutants_killed(
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=2,
        evaluator=evaluator,
        repair_runner=lambda _prompt, _workspace: {
            "returncode": 0,
            "stdout": raw_event,
            "changed_ids": [],
            "kept_as_is": {"repo_1": "duplicate behavior", "repo_2": "duplicate behavior"},
        },
    )

    assert evaluations == 1
    assert report["verified"] is True
    assert report["exact_singleton_count"] == 0
    assert report["target_mutation_score"] == 0.0
    assert report["best_effort_kept_as_is"] == ["repo_1", "repo_2"]
    assert report["attempts"][0]["best_effort_without_target_ids"] == ["repo_1", "repo_2"]
    assert (
        "Completed mutant repair request 1/2 for org__repo.123: applied 0 [none], "
        "kept as-is 2 [repo_1, repo_2]; next step: accept best-effort dispositions "
        "without reevaluation"
    ) in caplog.messages
    assert "passed_ground_truth_tests" not in (
        tmp_path / "work" / "repair_required.attempt_1.json"
    ).read_text()
    links = json.loads((tmp_path / "work" / "spec_test_mutant_links.json").read_text())
    assert links["summary"] == {
        "mutants": 2,
        "target_killed": 0,
        "exact_singletons": 0,
        "best_effort_kept_as_is": 2,
    }
    assert [item["status"] for item in links["connections"]] == [
        "best_effort_kept_as_is", "best_effort_kept_as_is",
    ]
    trajectory = tmp_path / "work" / "repair_mutants.attempt_1.traj.json"
    assert trajectory.is_file()
    assert "impossible" in trajectory.read_text()
    validation_report = (tmp_path / "work" / "mutant_kill_validation.json").read_text()
    assert raw_event.strip() not in validation_report


def _single_test_result(test_name: str, *, repo_1: str, repo_2: str) -> TestSuiteEvaluationResult:
    return TestSuiteEvaluationResult(binary_results=[
        BinaryTestSuiteResult(
            binary_id="ground_truth", role="ground_truth",
            test_results=[TestResult(name=test_name, status="passed", extra={})],
        ),
        BinaryTestSuiteResult(
            binary_id="repo_1", role="candidate",
            test_results=[TestResult(name=test_name, status=repo_1, extra={})],
        ),
        BinaryTestSuiteResult(
            binary_id="repo_2", role="candidate",
            test_results=[TestResult(name=test_name, status=repo_2, extra={})],
        ),
    ])


def test_skip_listed_target_test_is_excluded_from_mutation_targets(tmp_path: Path) -> None:
    # Reproduces fasttext in v38: repo_2 targets branch/test_other, which is on the skip
    # list and therefore never appears in the reference evaluation.
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    (skipped / f"{task}.json").write_text(
        json.dumps({
            "instance_id": task,
            "skipped_tests": [{"name": "branch/test_other", "reasons": [{"id": "gold_fail"}]}],
        })
    )

    report = ensure_mutants_killed(
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=0,
        evaluator=lambda _attempt: _single_test_result(
            "branch/test_behavior", repo_1="failure", repo_2="passed"
        ),
    )

    assert report["verified"] is True
    assert report["attempts"][-1]["missing_target_tests"] == []
    assert report["best_effort_reasons"]["repo_2"] == "target test is on the skip list"


def test_ground_truth_failing_target_test_becomes_best_effort_instead_of_missing(
    tmp_path: Path,
) -> None:
    # The validator skips branch/test_other for failing against ground truth, so the mutant
    # targeting it must not then be reported as absent from the reference evaluation.
    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)

    def evaluator(_attempt: int) -> TestSuiteEvaluationResult:
        names = {
            item["name"]
            for item in json.loads((skipped / f"{task}.json").read_text())["skipped_tests"]
        }
        if "branch/test_other" not in names:
            return _result(repo_1="failure", repo_2="failure", ground_truth="failure")
        return _single_test_result("branch/test_behavior", repo_1="failure", repo_2="passed")

    report = ensure_mutants_killed(
        prune_failing_tests=True,
        task=task,
        tests_root=tests_root,
        mutants_root=mutants_root,
        spec_root=spec_root,
        work_dir=tmp_path / "work",
        skipped_tests=skipped,
        max_repair_attempts=0,
        evaluator=evaluator,
    )

    assert report["verified"] is True
    assert report["attempts"][-1]["missing_target_tests"] == []
    assert report["best_effort_reasons"]["repo_2"] == "target test fails against ground truth"


def test_repair_rebuild_clears_stale_executable_before_running_build_sh():
    """Rust build.sh ends in `mv target/release/<bin> executable`.

    cargo re-creates that path as a hardlink to the inode a previous build
    already moved to ./executable, so without this cleanup mv fails with
    "are the same file" and every repair attempt silently accomplishes nothing.
    """
    assert '(repo / "executable").unlink(missing_ok=True)' in _REPAIR_BUILD_SCRIPT
    assert _REPAIR_BUILD_SCRIPT.index("unlink(missing_ok=True)") < _REPAIR_BUILD_SCRIPT.index(
        'subprocess.run(["bash", "build.sh"]'
    )


def test_reference_preflight_skips_mutant_sweep_until_ground_truth_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from programbench import mutant_kill_validation as validation

    task, tests_root, mutants_root, spec_root, skipped = _layout(tmp_path)
    scheduled: list[set[str] | None] = []

    def reference(*, extra: str) -> TestSuiteEvaluationResult:
        return TestSuiteEvaluationResult(binary_results=[BinaryTestSuiteResult(
            binary_id="ground_truth", role="ground_truth",
            test_results=[
                TestResult(name="branch/test_behavior", status="passed", extra={}),
                TestResult(name="branch/test_other", status="passed", extra={}),
                TestResult(name="branch/test_extra", status=extra, extra={}),
            ],
        )])

    def evaluate(**kwargs) -> TestSuiteEvaluationResult:
        scheduled.append(kwargs["mutant_ids"])
        if kwargs["mutant_ids"] == set():
            return reference(extra="failure" if len(scheduled) == 1 else "passed")
        return _result(repo_1="failure", repo_2="failure")

    monkeypatch.setattr(validation, "_default_evaluator", evaluate)
    report = validation.ensure_mutants_killed(
        prune_failing_tests=True,
        task=task, tests_root=tests_root, mutants_root=mutants_root, spec_root=spec_root,
        work_dir=tmp_path / "work", skipped_tests=skipped, max_repair_attempts=0,
    )

    assert scheduled == [set(), set(), None]
    assert report["verified"] is True
    assert [update["tests"] for update in report["added_skipped_tests"]] == [["branch/test_extra"]]
