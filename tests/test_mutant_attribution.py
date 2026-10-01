import json
from pathlib import Path

import pytest

from programbench.eval.test_suite_eval import BinaryTestSuiteResult, TestResult, TestSuiteEvaluationResult
from programbench.failure_attribution import group_by_root_cause
from programbench.mutant_attribution import (
    GeneratedTestAttribution,
    GeneratedTestFailureCase,
    _fan_out_root_causes,
    _reject_unverifiable_contradictions,
    GeneratedTestFailureCase,
    MutantCase,
    _generated_test_attribution_from_result,
    _validate_classifier_item,
    build_generated_test_failure_prompt,
    build_mutant_attribution_prompt,
    classify_mutants,
    load_generated_test_failure_cases,
    load_mutant_cases,
    mutant_payload,
    stage_generated_test_failure_classifier_workspace,
    stage_mutant_classifier_workspace,
)


def test_load_mutant_cases_selects_killed_survived_and_error_mutants(tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.test_eval.json"
    result = TestSuiteEvaluationResult(
        binary_results=[
            BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[
                    TestResult(name="test_one", status="passed", extra={}),
                    TestResult(name="test_two", status="passed", extra={}),
                ],
            ),
            BinaryTestSuiteResult(
                binary_id="repo_1",
                role="candidate",
                test_results=[
                    TestResult(name="test_one", status="passed", extra={}),
                    TestResult(name="test_two", status="passed", extra={}),
                ],
            ),
            BinaryTestSuiteResult(
                binary_id="repo_2",
                role="candidate",
                test_results=[
                    TestResult(name="test_one", status="failure", extra={}),
                    TestResult(name="test_two", status="passed", extra={}),
                ],
            ),
            BinaryTestSuiteResult(binary_id="repo_3", role="candidate", error_code="missing_payload"),
        ]
    )
    eval_json.write_text(result.model_dump_json())

    cases = load_mutant_cases(eval_json, task=task)

    assert [case.mutant_id for case in cases] == ["repo_1", "repo_2", "repo_3"]
    assert cases[0].status == "survived"
    assert cases[0].n_candidate_passing_ground_truth_tests == 2
    assert cases[1].status == "killed"
    assert cases[1].killed_by == ["test_one"]
    assert cases[2].status == "error"
    assert cases[2].error_code == "missing_payload"

    payload = mutant_payload(cases[1])
    assert payload["n_generated_tests_observed"] == 2
    assert payload["n_generated_tests_passing_ground_truth"] == 2
    assert payload["n_generated_tests_passing_both_ground_truth_and_mutant"] == 1
    assert payload["generated_tests_passing_ground_truth_but_failing_mutant"] == ["test_one"]
    assert payload["generated_tests_passing_ground_truth"] == ["test_one", "test_two"]
    assert "n_tests" not in payload
    assert "killed_by" not in payload
    assert "passed_ground_truth_tests" not in payload


def test_load_generated_test_failure_cases_selects_ground_truth_failures(tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.test_eval.json"
    result = TestSuiteEvaluationResult(
        binary_results=[
            BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[
                    TestResult(name="test_ok", status="passed", extra={}),
                    TestResult(
                        name="test_bad",
                        status="failure",
                        extra={"message": "expected foo", "text": "AssertionError"},
                    ),
                ],
            ),
            BinaryTestSuiteResult(
                binary_id="repo_1",
                role="candidate",
                test_results=[TestResult(name="test_ok", status="passed", extra={})],
            ),
        ]
    )
    eval_json.write_text(result.model_dump_json())

    cases = load_generated_test_failure_cases(eval_json, task=task)

    assert len(cases) == 1
    assert cases[0].name == "test_bad"
    assert cases[0].message == "expected foo"



def test_classify_mutants_writes_report_with_stub_runner(tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.test_eval.json"
    result = TestSuiteEvaluationResult(
        binary_results=[
            BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[TestResult(name="test_one", status="passed", extra={})],
            ),
            BinaryTestSuiteResult(
                binary_id="repo_1",
                role="candidate",
                test_results=[TestResult(name="test_one", status="passed", extra={})],
            ),
            BinaryTestSuiteResult(
                binary_id="repo_2",
                role="candidate",
                test_results=[TestResult(name="test_one", status="failure", extra={})],
            ),
            BinaryTestSuiteResult(
                binary_id="repo_3",
                role="candidate",
                error_code="missing_payload",
            ),
        ]
    )
    eval_json.write_text(result.model_dump_json())
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("The program must print foo.")
    tests_dir = tmp_path / "generated" / task
    tests_dir.mkdir(parents=True)
    (tests_dir / "tests.tar.gz").write_bytes(b"not used by stub runner")
    mutants_dir = tmp_path / "mutants"
    mutant_repo = mutants_dir / task / "repo_1"
    mutant_repo.mkdir(parents=True)
    (mutant_repo / "executable").write_text("#!/bin/sh\n")
    (mutants_dir / task / "mutants.json").write_text(json.dumps({
        "instance_id": task,
        "mutants": [{
            "id": "repo_1",
            "target_spec": "Spec 3",
            "target_test": "test_one",
            "mutation": "Change the primary behavior.",
            "payload": "repo_1/executable",
        }],
    }))
    output = tmp_path / "mutant_attribution.json"
    calls = []

    def runner(prompt: str) -> dict[str, object]:
        calls.append(prompt)
        return {
            "mutants": [
                {
                    "mutant_id": "repo_1",
                    "fault": "spec_contradiction",
                    "subreason": "behavior_underspecified",
                    "confidence": 0.8,
                    "rationale": "Spec 3 is the mutant target; Spec 7 also constrains the behavior.",
                    "recommended_action": "polish_spec",
                }
            ]
        }

    report = classify_mutants(
        eval_json=eval_json,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        mutants_dir=mutants_dir,
        output=output,
        force=True,
        runner=runner,
    )

    assert output.is_file()
    assert len(calls) == 1
    assert "mutant_cases.json" in calls[0]
    assert report.test_failure_summary == {"test": 0, "spec_underspecification": 0, "spec_contradiction": 0, "flaky": 0, "error": 0, "error_infra": 0, "unknown": 0}
    assert report.summary == {"test": 0, "spec_underspecification": 0, "spec_contradiction": 1, "unknown": 1}
    assert report.mutant_action_summary == {"polish_spec": 1}
    assert [attribution.mutant_id for attribution in report.mutants] == ["repo_1", "repo_3"]
    assert report.mutants[0].recommended_action == "polish_spec"
    assert report.mutants[0].most_relevant_spec == "Spec 3"
    assert report.mutants[0].other_relevant_specs == ["Spec 7"]
    assert report.mutants[1].fault == "unknown"
    assert report.mutants[1].subreason == "evaluation_error"
    assert report.mutants[1].confidence == 1.0
    stored = json.loads(output.read_text())
    assert "good" not in stored["summary"]
    assert [item["mutant_id"] for item in stored["mutants"]] == ["repo_1", "repo_3"]
    assert stored["mutant_action_summary"]["polish_spec"] == 1
    assert "raw_response" not in stored["mutants"][0]



def test_classify_mutants_reports_generated_tests_that_fail_on_ground_truth(tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.test_eval.json"
    result = TestSuiteEvaluationResult(
        binary_results=[
            BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[
                    TestResult(name="test_bad", status="failure", extra={"message": "wrong output", "text": "AssertionError: expected foo"}),
                ],
            ),
        ]
    )
    eval_json.write_text(result.model_dump_json())
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("The program must print foo.")
    tests_dir = tmp_path / "generated" / task
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_example.py").write_text("def test_bad(): pass\n")
    mutants_dir = tmp_path / "mutants"
    (mutants_dir / task).mkdir(parents=True)
    output = tmp_path / "mutant_attribution.json"
    calls = []

    def runner(prompt: str) -> dict[str, object]:
        calls.append(prompt)
        if "generated_test_failures.json" in prompt:
            return {
                "test_failures": [
                    {
                        "name": "test_bad",
                        "fault": "spec_underspecification",
                        "subreason": "missing_output_rule",
                        "confidence": 0.8,
                        "rationale": "Spec 2 permits the assertion, while Spec 5 leaves its output ambiguous.",
                        "recommended_action": "polish_spec",
                    }
                ]
            }
        return {"mutants": []}

    report = classify_mutants(
        eval_json=eval_json,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        mutants_dir=mutants_dir,
        output=output,
        force=True,
        runner=runner,
    )

    assert len(calls) == 1
    assert "generated_test_failures.json" in calls[0]
    assert report.test_failure_summary == {"test": 0, "spec_underspecification": 1, "spec_contradiction": 0, "flaky": 0, "error": 0, "error_infra": 0, "unknown": 0}
    assert report.test_failures[0].name == "test_bad"
    assert report.test_failures[0].recommended_action == "polish_spec"
    assert report.test_failures[0].error_log == "AssertionError: expected foo"
    assert report.test_failures[0].relevant_specs == ["Spec 2", "Spec 5"]
    assert report.summary == {"test": 0, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 0}
    stored = json.loads(output.read_text())
    assert stored["test_failures"][0]["fault"] == "spec_underspecification"
    assert stored["test_failures"][0]["error_log"] == "AssertionError: expected foo"
    assert "raw_response" not in stored["test_failures"][0]


def test_classify_mutants_persists_classifier_token_usage(monkeypatch, tmp_path: Path) -> None:
    from programbench import mutant_attribution

    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.test_eval.json"
    result = TestSuiteEvaluationResult(
        binary_results=[
            BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[
                    TestResult(name="test_bad", status="failure", extra={"message": "wrong output"}),
                    TestResult(name="test_ok", status="passed", extra={}),
                ],
            ),
            BinaryTestSuiteResult(
                binary_id="repo_1",
                role="candidate",
                test_results=[TestResult(name="test_ok", status="passed", extra={})],
            ),
        ]
    )
    eval_json.write_text(result.model_dump_json())
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("The program must print foo.")
    tests_dir = tmp_path / "generated" / task
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_example.py").write_text("def test_bad(): pass\n\ndef test_ok(): pass\n")
    mutants_dir = tmp_path / "mutants" / task
    mutant_repo = mutants_dir / "repo_1"
    mutant_repo.mkdir(parents=True)
    (mutant_repo / "executable").write_text("#!/bin/sh\n")
    output = tmp_path / "mutant_attribution.json"
    calls = []

    def completed(stdout: str):
        class Completed:
            returncode = 0
            stderr = ""

        Completed.stdout = stdout
        return Completed()

    def run_codex_in_container(*args, **kwargs):
        call_index = len(calls)
        calls.append((args, kwargs))
        if call_index == 0:
            payload = {
                "test_failures": [
                    {
                        "name": "test_bad",
                        "fault": "test",
                        "spec_quote": "The program must print foo.",
                        "subreason": "bad_assertion",
                        "confidence": 0.8,
                        "rationale": "The generated test fails on the reference implementation.",
                        "recommended_action": "ignore",
                    }
                ]
            }
            usage = {
                "input_tokens": 30,
                "cached_input_tokens": 10,
                "output_tokens": 7,
                "reasoning_output_tokens": 2,
            }
        else:
            payload = {
                "mutants": [
                    {
                        "mutant_id": "repo_1",
                        "fault": "good",
                        "subreason": "equivalent_or_acceptable",
                        "confidence": 0.75,
                        "rationale": "The surviving mutant appears acceptable under the spec.",
                        "recommended_action": "ignore",
                    }
                ]
            }
            usage = {
                "input_tokens": 50,
                "cached_input_tokens": 20,
                "output_tokens": 11,
                "reasoning_output_tokens": 4,
            }
        process = completed(
            "\n".join(
                [
                    json.dumps({"type": "turn.completed", "usage": usage}),
                    json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(payload)}}),
                ]
            )
        )
        return {
            "returncode": process.returncode,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }

    monkeypatch.setattr(mutant_attribution, "run_codex_in_container", run_codex_in_container)

    report = classify_mutants(
        eval_json=eval_json,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        mutants_dir=tmp_path / "mutants",
        output=output,
        force=True,
        batch_workers=1,
    )

    assert len(calls) == 2
    # Both classifiers run in the task cleanroom so they can check the real behavior
    # instead of blaming the spec for a generated test that never reached the binary.
    assert {kwargs["image"] for _, kwargs in calls} == {"programbench/org_1776_repo.123:task_cleanroom_codex"}
    assert [batch.phase for batch in report.classifier_usage.batches] == [
        "generated_test_failure_classification",
        "mutant_classification",
    ]
    assert report.classifier_usage.totals["input_tokens"] == 80
    assert report.classifier_usage.totals["output_tokens"] == 18
    assert report.classifier_usage.totals["total_tokens"] == 98
    assert report.classifier_usage.totals["uncached_input_plus_output_tokens"] == 68
    assert report.summary == {"test": 0, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 1}
    assert report.mutants[0].subreason == "invalid_classifier_item"
    assert report.mutants[0].recommended_action == "manual_review"
    stored = json.loads(output.read_text())
    assert stored["classifier_usage"]["batches"][0]["case_count"] == 1
    assert stored["classifier_usage"]["totals"]["reasoning_output_tokens"] == 6


def test_classifier_prompts_point_at_the_ground_truth_executable() -> None:
    failure_prompt = build_generated_test_failure_prompt(failure_count=1)
    assert "/workspace/executable" in failure_prompt
    assert "A failure that never reached the executable is `error`" in failure_prompt
    assert "Before emitting `test`, copy into `spec_quote`" in failure_prompt
    assert "`timing_sensitive`" in failure_prompt and "`replayed_with_fix`" in failure_prompt
    assert "/workspace/executable" in build_mutant_attribution_prompt(mutant_count=1)


def test_stage_generated_test_failure_classifier_workspace_copies_tests(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("spec")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_bad(): pass\n")
    workspace = tmp_path / "workspace"

    stage_generated_test_failure_classifier_workspace(
        workspace=workspace,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        cases=[
            GeneratedTestFailureCase(
                instance_id="org__repo.123",
                name="test_bad",
                status="failure",
                message="wrong output",
            )
        ],
    )

    assert (workspace / "spec" / "spec.md").read_text() == "spec"
    assert (workspace / "test" / "test_example.py").read_text() == "def test_bad(): pass\n"
    failure = json.loads((workspace / "generated_test_failures.json").read_text())[0]
    assert failure["name"] == "test_bad"


def test_stage_mutant_classifier_workspace_copies_relevant_mutants(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("spec")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "note.txt").write_text("tests")
    mutants_dir = tmp_path / "mutants"
    repo = mutants_dir / "repo_1"
    repo.mkdir(parents=True)
    (repo / "source.c").write_text("int main(void) { return 0; }\n")
    workspace = tmp_path / "workspace"

    stage_mutant_classifier_workspace(
        workspace=workspace,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        mutants_dir=mutants_dir,
        cases=[
            MutantCase(
                instance_id="org__repo.123",
                mutant_id="repo_1",
                status="survived",
            )
        ],
    )

    assert (workspace / "spec" / "spec.md").read_text() == "spec"
    assert (workspace / "test" / "note.txt").read_text() == "tests"
    assert (workspace / "mutants" / "repo_1" / "source.c").is_file()
    assert json.loads((workspace / "mutant_cases.json").read_text())[0]["mutant_id"] == "repo_1"


def test_flaky_generated_tests_reduce_validity_rate_and_bypass_attribution(tmp_path: Path) -> None:
    task = "org__repo.123"
    first_trial = BinaryTestSuiteResult(
        binary_id="ground_truth",
        role="ground_truth",
        test_results=[
            TestResult(name="stable", status="passed", extra={}),
            TestResult(name="flaky", status="passed", extra={}),
        ],
    )
    second_trial = BinaryTestSuiteResult(
        binary_id="ground_truth",
        role="ground_truth",
        test_results=[
            TestResult(name="stable", status="passed", extra={}),
            TestResult(name="flaky", status="failure", extra={"message": "intermittent"}),
        ],
    )
    result = TestSuiteEvaluationResult(
        binary_results=[
            first_trial,
            BinaryTestSuiteResult(
                binary_id="repo_1",
                role="candidate",
                test_results=[
                    TestResult(name="stable", status="passed", extra={}),
                    TestResult(name="flaky", status="failure", extra={}),
                ],
            ),
        ],
        ground_truth_trials=[first_trial, second_trial],
    )

    assert result.flaky_test_names == {"flaky"}
    assert result.validity_rate == 0.5
    assert result.ground_truth_passing_test_names == {"stable"}
    assert result.mutation_score == 0.0

    eval_json = tmp_path / f"{task}.test_eval.json"
    eval_json.write_text(result.model_dump_json())
    cases = load_generated_test_failure_cases(eval_json, task=task)
    assert [(case.name, case.status) for case in cases] == [("flaky", "flaky")]

    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("A specification.")
    tests_dir = tmp_path / "generated" / task
    tests_dir.mkdir(parents=True)
    mutants_dir = tmp_path / "mutants" / task
    mutants_dir.mkdir(parents=True)
    calls: list[str] = []

    report = classify_mutants(
        eval_json=eval_json,
        spec_dir=spec_dir,
        tests_dir=tests_dir,
        mutants_dir=mutants_dir,
        output=tmp_path / "attribution.json",
        force=True,
        runner=lambda prompt: calls.append(prompt) or {
            "mutants": [{
                "mutant_id": "repo_1",
                "fault": "test",
                "subreason": "stable_test_coverage",
                "confidence": 1.0,
                "rationale": "No specification change is needed.",
                "recommended_action": "ignore",
            }]
        },
    )

    assert all("generated_test_failures.json" not in prompt for prompt in calls)
    assert report.test_failure_summary == {"test": 0, "spec_underspecification": 0, "spec_contradiction": 0, "flaky": 1, "error": 0, "error_infra": 0, "unknown": 0}
    assert report.test_failures[0].fault == "flaky"
    assert report.test_failures[0].recommended_action == "ignore"


def _retry_batch_kwargs(tmp_path, *, mutant=False, count=4):
    cases = [
        MutantCase(instance_id="org__repo.123", mutant_id=f"repo_{i}", status="survived")
        if mutant else GeneratedTestFailureCase(instance_id="org__repo.123", name=f"test_{i}", status="failure")
        for i in range(count)
    ]
    kwargs = dict(batch_index=1, batch=cases, workspace=tmp_path / "batch",
                  spec_dir=tmp_path / "spec", tests_dir=tmp_path / "tests",
                  model="test", reasoning_effort="high", codex_command="codex exec", timeout=10,
                  image="programbench/org_1776_repo.123:task_cleanroom_codex", runner=None)
    if mutant:
        kwargs["mutants_dir"] = tmp_path / "mutants"
        kwargs["ground_truth"] = None
    return kwargs


def test_malformed_batches_split_and_preserve_usage_and_errors(tmp_path, monkeypatch):
    import programbench.mutant_attribution as module

    for mutant in (False, True):
        staged = {}
        sizes = []
        key = "mutants" if mutant else "test_failures"
        identifier = "mutant_id" if mutant else "name"

        def stage(*, workspace, cases, **kwargs):
            assert workspace not in staged
            staged[workspace] = cases

        def classify(prompt, *, cwd, **kwargs):
            cases = staged[cwd]
            sizes.append(len(cases))
            if len(cases) > 1:
                return {}, "unexpected classifier response", {"input_tokens": 10, "output_tokens": 2}
            result = {key: [{identifier: getattr(cases[0], identifier), "fault": "test"}]}
            return result, json.dumps(result), {"input_tokens": 10, "output_tokens": 2}

        monkeypatch.setattr(module, "stage_mutant_classifier_workspace", stage)
        monkeypatch.setattr(module, "stage_generated_test_failure_classifier_workspace", stage)
        monkeypatch.setattr(module, "run_codex_classifier", classify)
        run = module._classify_mutant_batch if mutant else module._classify_generated_test_failure_batch
        items, usage = run(**_retry_batch_kwargs(tmp_path, mutant=mutant))
        assert sizes == [4, 2, 1, 1, 2, 1, 1]
        assert [getattr(item, identifier) for item in items] == [f"{'repo' if mutant else 'test'}_{i}" for i in range(4)]
        assert all(item.fault == "test" for item in items)
        assert usage.case_count == 4
        assert usage.usage == {"input_tokens": 70, "output_tokens": 14}
        for item in items:
            saved = item.model_dump()
            assert [error["case_count"] for error in saved["classifier_errors"]] == [4, 2]
            assert saved["classifier_errors"][0]["raw_response"] == "unexpected classifier response"


def test_partial_batch_retries_only_missing_case(tmp_path):
    import programbench.mutant_attribution as module

    responses = iter([
        {"test_failures": [{"name": "test_1", "fault": "unknown", "rationale": "Evidence is ambiguous."}]},
        {"test_failures": [{"name": "test_0", "fault": "spec_underspecification"}]},
    ])
    kwargs = _retry_batch_kwargs(tmp_path, count=2)
    kwargs.update(workspace=None, runner=lambda prompt: next(responses))
    items, usage = module._classify_generated_test_failure_batch(**kwargs)
    assert [item.fault for item in items] == ["spec_underspecification", "unknown"]
    assert items[0].classifier_errors[0]["subreason"] == "missing_batch_result"
    assert items[1].classifier_errors == []
    assert usage is None


def test_failed_singletons_stop_and_preserve_original_parse_error(tmp_path, monkeypatch):
    import programbench.mutant_attribution as module

    monkeypatch.setattr(module, "stage_generated_test_failure_classifier_workspace", lambda **kwargs: None)
    calls = []

    def execute(*args, **kwargs):
        calls.append(kwargs["cwd"])
        return {"returncode": 0, "stdout": "not JSON", "stderr": ""}

    monkeypatch.setattr(module, "run_codex_in_container", execute)
    items, _ = module._classify_generated_test_failure_batch(**_retry_batch_kwargs(tmp_path, count=2))
    assert len(calls) == 3
    assert all(item.subreason == "invalid_classifier_json" for item in items)
    assert all("Classifier did not return valid JSON" in item.rationale for item in items)
    assert all(item.classifier_errors[-1]["raw_response"] == "not JSON" for item in items)


def test_invalid_confidence_retries_without_losing_valid_results(tmp_path):
    import programbench.mutant_attribution as module

    responses = iter([
        {"mutants": [{"mutant_id": "repo_0", "fault": "spec_underspecification", "confidence": "nonsense"},
                     {"mutant_id": "repo_1", "fault": "test", "confidence": 1}]},
        {"mutants": [{"mutant_id": "repo_0", "fault": "spec_underspecification", "confidence": 0.8}]},
    ])
    kwargs = _retry_batch_kwargs(tmp_path, mutant=True, count=2)
    kwargs.update(workspace=None, runner=lambda prompt: next(responses))
    items, _ = module._classify_mutant_batch(**kwargs)
    assert [item.fault for item in items] == ["spec_underspecification", "test"]
    assert items[0].confidence == 0.8
    assert items[0].classifier_errors[0]["subreason"] == "invalid_classifier_item"
    assert items[1].classifier_errors == []


def test_generated_test_environment_failures_land_in_error_not_spec_contradiction() -> None:
    """`GeneratedTestFault` had no `error` member while the other two enums did.

    Generated tests that failed only because a remote asset fetch hit the blocked
    proxy therefore had nowhere to go, and were booked as spec contradictions.
    """
    prompt = build_generated_test_failure_prompt(failure_count=1)
    assert "test|error|unknown" in prompt
    assert "Never classify an environment failure as a specification fault" in prompt

    attribution = _generated_test_attribution_from_result(
        GeneratedTestFailureCase(instance_id="org__repo.123", name="test_one", status="failure"),
        {"fault": "error", "subreason": "proxy_blocked_fetch", "confidence": 0.9, "rationale": "Proxy failure."},
        raw_response="{}",
    )
    assert (attribution.fault, attribution.recommended_action) == ("error", "ignore")
    assert _validate_classifier_item({"fault": "error", "confidence": 0.9}, mutant=False)["fault"] == "error"


def test_fixture_cascade_is_classified_once_and_fanned_out() -> None:
    """Nine tests sharing one broken session fixture are one judgement, not nine spec faults.

    Counting each dependent test separately is what turned a single degenerate fasttext
    training fixture into nine independent spec_contradiction records.
    """
    fixture_tb = "conftest.py:50: in sup\n    assert r.returncode == 0\nE   EncounteredNaNError"
    cases = [
        GeneratedTestFailureCase(instance_id="org__repo.abc", name=f"test_{i}", status="failure", traceback=fixture_tb)
        for i in range(3)
    ] + [
        GeneratedTestFailureCase(
            instance_id="org__repo.abc",
            name="test_other",
            status="failure",
            traceback="test_cli.py:12: in test_other\n    assert 1 == 2",
        )
    ]
    groups = group_by_root_cause(cases)
    assert [len(group) for group in groups] == [3, 1]

    verdicts = [
        GeneratedTestAttribution(
            instance_id="org__repo.abc", name="test_0", status="failure", fault="test",
            subreason="degenerate_fixture", rationale="Spec 6 is fine.",
        ),
        GeneratedTestAttribution(
            instance_id="org__repo.abc", name="test_other", status="failure", fault="test",
            subreason="brittle", rationale="Spec 1 is fine.",
        ),
    ]
    fanned = _fan_out_root_causes(groups, verdicts)
    assert [a.name for a in fanned] == ["test_0", "test_1", "test_2", "test_other"]
    assert {a.subreason for a in fanned[:3]} == {"degenerate_fixture"}
    assert "Shared root cause with 2 other" in fanned[1].rationale
    assert "Shared root cause" not in fanned[3].rationale


def test_contradiction_with_a_quote_absent_from_the_spec_is_discarded(tmp_path: Path) -> None:
    """A verdict claiming the spec prescribes wording it never contains is checkable without a model.

    This is the dirble proxy case: the spec says `cannot be used with`, the verdict asserted
    it demanded `cannot be used together`, and the reference matched the spec all along.
    """
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text(
        "## Spec 5\n\nConflict diagnostics include `cannot be used with` and exit 2.\n"
    )
    attributions = [
        GeneratedTestAttribution(
            instance_id="org__repo.abc", name="fabricated", status="failure",
            fault="spec_contradiction", recommended_action="polish_spec",
            spec_quote="Conflict diagnostics must say cannot be used together.",
        ),
        GeneratedTestAttribution(
            instance_id="org__repo.abc", name="verified", status="failure",
            fault="spec_contradiction", recommended_action="polish_spec",
            spec_quote="Conflict diagnostics include `cannot be used with` and exit 2.",
        ),
        GeneratedTestAttribution(
            instance_id="org__repo.abc", name="not_a_contradiction", status="failure",
            fault="spec_underspecification", recommended_action="polish_spec",
        ),
    ]
    _reject_unverifiable_contradictions(attributions, spec_dir)
    assert [(a.fault, a.recommended_action) for a in attributions] == [
        ("unknown", "manual_review"),
        ("spec_contradiction", "polish_spec"),
        ("spec_underspecification", "polish_spec"),
    ]
    assert attributions[0].subreason == "unverified_spec_quote"


def test_generated_test_cases_carry_timing_and_flaky_sibling_context(tmp_path: Path) -> None:
    """Two entr tests raced the watcher exactly like nine siblings the trials had caught as flaky,
    passed three trials by luck, and were then judged as spec contradictions. The judge now sees
    that the test polls with a deadline and how many tests in its file were flaky.
    """
    from programbench.mutant_attribution import annotate_generated_test_cases, generated_test_failure_payload

    tests_dir = tmp_path / "generated" / "org__repo.abc"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_watch.py").write_text(
        "def test_wait(tmp_path):\n    out = wait_for(p, b'run', timeout=4)\n    assert out\n\n"
        "class TestPlain:\n    def test_plain(self):\n        assert run(['-h']).returncode == 1\n"
    )
    cases = [
        GeneratedTestFailureCase(instance_id="org__repo.abc", name="test_watch.test_wait", status="failure"),
        GeneratedTestFailureCase(instance_id="org__repo.abc", name="test_watch.TestPlain.test_plain[x]", status="failure"),
        GeneratedTestFailureCase(instance_id="org__repo.abc", name="test_missing.test_gone", status="failure"),
    ]

    annotated = annotate_generated_test_cases(cases, tests_dir, {"test_watch.test_race", "test_watch.test_other", "test_cli.test_x"})

    assert [(case.timing_sensitive, case.flaky_siblings_in_file) for case in annotated] == [(True, 2), (False, 2), (False, 0)]
    payload = generated_test_failure_payload(annotated[0])
    assert (payload["timing_sensitive"], payload["flaky_siblings_in_file"]) == (True, 2)


def test_test_verdict_without_a_spec_basis_is_rejudged_before_it_can_hide_a_spec_gap(tmp_path: Path) -> None:
    """Ten crowbook tests that omitted a BOOK under --single were booked as test faults although
    no spec sentence says BOOK is required there. A `test` verdict must now quote the sentence the
    test misread; one that cannot is judged again, and stays unknown rather than hiding the gap.
    """
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.test_eval.json"
    trial = BinaryTestSuiteResult(
        binary_id="ground_truth",
        role="ground_truth",
        test_results=[
            TestResult(name="test_cli.test_single_stdin", status="failure", extra={"text": "test_cli.py:5: in test_single_stdin\nE   assert b'<html' in b''"}),
            TestResult(name="test_cli.test_version", status="failure", extra={"text": "test_cli.py:9: in test_version\nE   assert b'1.0' == b'1.1'"}),
        ],
    )
    eval_json.write_text(TestSuiteEvaluationResult(binary_results=[trial], ground_truth_trials=[trial]).model_dump_json())
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 9\nWith `--single`, BOOK is one Markdown document. BOOK may be `-` for stdin.\n## Spec 3\n`--version` prints `1.0`.\n")
    tests_dir = tmp_path / "generated" / task
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_cli.py").write_text("def test_single_stdin(): ...\ndef test_version(): ...\n")
    prompts: list[str] = []

    def runner(prompt: str) -> dict[str, object]:
        if "generated_test_failures.json" not in prompt:
            return {"mutants": []}
        prompts.append(prompt)
        version = {"name": "test_cli.test_version", "fault": "test", "confidence": 0.9, "rationale": "Spec 3 fixes it.",
                   "spec_quote": "`--version` prints `1.0`.", "recommended_action": "ignore"}
        single = {"name": "test_cli.test_single_stdin", "fault": "test", "confidence": 0.9, "rationale": "Spec 9 requires BOOK.",
                  "spec_quote": "BOOK is required under --single.", "recommended_action": "ignore"}
        if len(prompts) == 2:
            single = {**single, "fault": "spec_underspecification", "spec_quote": "", "recommended_action": "polish_spec",
                      "replayed_with_fix": True, "fix_description": "ran with and without BOOK"}
        return {"test_failures": [single, version] if len(prompts) == 1 else [single]}

    report = classify_mutants(
        eval_json=eval_json, spec_dir=spec_dir, tests_dir=tests_dir, mutants_dir=tmp_path / "mutants" / task,
        output=tmp_path / "attribution.json", force=True, runner=runner,
    )

    assert len(prompts) == 2 and "There are 1 generated-test failures" in prompts[1]
    by_name = {attribution.name: attribution for attribution in report.test_failures}
    assert by_name["test_cli.test_version"].fault == "test"
    assert (by_name["test_cli.test_single_stdin"].fault, by_name["test_cli.test_single_stdin"].replayed_with_fix) == ("spec_underspecification", True)
    assert json.loads((tmp_path / "attribution.json").read_text())["test_failures"][0]["fix_description"] == "ran with and without BOOK"


def _both_directions_eval(tmp_path: Path) -> dict[str, Path]:
    """One evaluation carrying both a generated test that fails on ground truth and a survived mutant."""
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.test_eval.json"
    eval_json.write_text(
        TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        TestResult(name="test_good", status="passed", extra={}),
                        TestResult(name="test_bad", status="failure", extra={"message": "wrong", "text": "AssertionError: expected foo"}),
                    ],
                ),
                BinaryTestSuiteResult(
                    binary_id="repo_1",
                    role="candidate",
                    test_results=[TestResult(name="test_good", status="passed", extra={})],
                ),
            ]
        ).model_dump_json()
    )
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("The program must print foo.")
    tests_dir = tmp_path / "generated" / task
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_example.py").write_text("def test_good(): pass\ndef test_bad(): pass\n")
    mutants_dir = tmp_path / "mutants"
    mutant_repo = mutants_dir / task / "repo_1"
    mutant_repo.mkdir(parents=True)
    (mutant_repo / "executable").write_text("#!/bin/sh\n")
    (mutants_dir / task / "mutants.json").write_text(json.dumps({
        "instance_id": task,
        "mutants": [{
            "id": "repo_1",
            "target_spec": "Spec 3",
            "target_test": "test_good",
            "mutation": "Change the primary behavior.",
            "payload": "repo_1/executable",
        }],
    }))
    return {"eval_json": eval_json, "spec_dir": spec_dir, "tests_dir": tests_dir, "mutants_dir": mutants_dir}


def _direction_runner(calls: list[str]):
    def runner(prompt: str) -> dict[str, object]:
        calls.append(prompt)
        if "generated_test_failures.json" in prompt:
            return {"test_failures": [{
                "name": "test_bad",
                "fault": "spec_underspecification",
                "subreason": "missing_output_rule",
                "confidence": 0.8,
                "rationale": "Spec 2 permits the assertion, while Spec 5 leaves its output ambiguous.",
                "recommended_action": "polish_spec",
            }]}
        return {"mutants": [{
            "mutant_id": "repo_1",
            "fault": "spec_contradiction",
            "subreason": "behavior_underspecified",
            "confidence": 0.8,
            "rationale": "Spec 3 is the mutant target.",
            "recommended_action": "polish_spec",
        }]}
    return runner


@pytest.mark.parametrize(
    ("kwargs", "prompt_marker", "test_failure_names", "mutant_ids"),
    [
        ({}, None, ["test_bad"], ["repo_1"]),
        ({"classify_survived_mutants": False}, "generated_test_failures.json", ["test_bad"], []),
        ({"classify_test_failures": False}, "mutant_cases.json", [], ["repo_1"]),
    ],
)
def test_each_direction_can_be_classified_without_paying_for_the_other(
    tmp_path: Path, kwargs: dict, prompt_marker: str | None, test_failure_names: list[str], mutant_ids: list[str]
) -> None:
    calls: list[str] = []
    report = classify_mutants(
        **_both_directions_eval(tmp_path),
        output=tmp_path / "mutant_attribution.json",
        force=True,
        runner=_direction_runner(calls),
        **kwargs,
    )

    # A dropped direction must cost no classifier call at all, which is the whole point of dropping it.
    if prompt_marker is not None:
        assert len(calls) == 1 and prompt_marker in calls[0]
    else:
        assert len(calls) == 2
    assert [failure.name for failure in report.test_failures] == test_failure_names
    assert [mutant.mutant_id for mutant in report.mutants] == mutant_ids
    # The kept direction's counts survive; the dropped one leaves no summary, so nothing downstream
    # can read it as "classified, no faults found".
    assert report.test_failure_summary.get("spec_underspecification", 0) == len(test_failure_names)
    assert report.summary.get("spec_contradiction", 0) == len(mutant_ids)
    assert (report.test_failure_summary == {}) == (not test_failure_names)
    assert (report.summary == {}) == (not mutant_ids)
    stored = json.loads((tmp_path / "mutant_attribution.json").read_text())
    assert [item["mutant_id"] for item in stored["mutants"]] == mutant_ids
