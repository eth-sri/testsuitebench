import json
import threading
import time
from pathlib import Path

import pytest

from programbench import failure_attribution

from programbench.failure_attribution import (
    FailureAttribution,
    FailureCase,
    _attribution_from_result,
    _evaluation_error_attribution,
    _is_evaluation_error,
    _is_installer_network_failure,
    build_candidate_attribution_prompt,
    check_attribution_usable,
    classify_failures,
    default_output_path,
    infer_spec_dir,
    normalize_spec_summary,
    reject_unverified_attributions,
    load_failure_cases,
    resolve_eval_json,
    spec_quote_is_verifiable,
)
from programbench.constants import eval_network_note
from programbench.failure_attribution import (
    stage_classifier_workspace,
)

def test_legacy_spec_summary_normalizes_to_underspecification() -> None:
    assert normalize_spec_summary({"spec": 3, "unknown": 1}) == {
        "spec_underspecification": 3,
        "spec_contradiction": 0,
        "unknown": 1,
    }


def test_load_failure_cases_from_eval_json(tmp_path: Path) -> None:
    eval_json = tmp_path / "task__repo.abc.eval.json"
    eval_json.write_text(
        json.dumps(
            {
                "test_results": [
                    {"name": "tests.test_cli.test_ok", "branch": "b1", "status": "passed", "extra": {}},
                    {
                        "name": "tests.test_cli.test_bad",
                        "branch": "b1",
                        "status": "failure",
                        "extra": {"message": "wrong stdout", "text": "AssertionError"},
                    },
                ]
            }
        )
    )

    failures = load_failure_cases(eval_json)

    assert len(failures) == 1
    assert failures[0].name == "tests.test_cli.test_bad"
    assert failures[0].message == "wrong stdout"

def test_resolve_iteration_paths(tmp_path: Path) -> None:
    task = "org__repo.123"
    iter_dir = tmp_path / "iter_0"
    eval_json = iter_dir / "executable" / task / f"{task}.eval.json"
    eval_json.parent.mkdir(parents=True)
    eval_json.write_text('{"test_results": []}')
    (iter_dir / "spec" / task).mkdir(parents=True)

    assert resolve_eval_json(iter_dir, task=task) == eval_json
    assert infer_spec_dir(iter_dir, task=task) == iter_dir / "spec" / task

def test_default_output_path_uses_log_task_directory(tmp_path: Path) -> None:
    task = "org__repo.123"
    iter_dir = tmp_path / "iter_1"
    iter_dir.mkdir()
    eval_json = iter_dir / "executable" / task / f"{task}.eval.json"

    assert default_output_path(iter_dir, eval_json) == iter_dir / "log" / task / "failure_attribution.json"

def test_candidate_classifier_skips_model_when_there_are_no_failures(tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.eval.json"
    eval_json.write_text("{\"test_results\": []}")
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\nPrint alpha.\n")
    calls = []

    def runner(prompt: str) -> dict[str, object]:
        calls.append(prompt)
        return {"failures": []}

    report = classify_failures(
        eval_json=eval_json,
        spec_dir=spec_dir,
        output=tmp_path / "failure_attribution.json",
        runner=runner,
    )

    assert calls == []
    assert report.failures == []
    assert report.summary == {"error": 0, "error_infra": 0, "executable": 0, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 0}


def test_run_codex_classifier_returns_token_usage(monkeypatch, tmp_path: Path) -> None:
    from programbench import failure_attribution

    class Completed:
        returncode = 0
        stderr = ""
        stdout = "\n".join(
            [
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "ignored"}}),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 100,
                            "cached_input_tokens": 40,
                            "cache_write_input_tokens": 7,
                            "output_tokens": 25,
                            "reasoning_output_tokens": 9,
                        },
                    }
                ),
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "{\"failures\": []}"}}),
            ]
        )

    monkeypatch.setattr(
        failure_attribution,
        "run_codex_in_container",
        lambda *args, **kwargs: {
            "returncode": Completed.returncode,
            "stdout": Completed.stdout,
            "stderr": Completed.stderr,
        },
    )

    result, raw, usage = failure_attribution.run_codex_classifier(
        "classify",
        model="codex/gpt-5.5",
        reasoning_effort="high",
        codex_command="codex exec",
        image="programbench/x_1776_y.abc1234:task_cleanroom_codex",
        timeout=10,
        cwd=tmp_path,
    )

    assert result == {"failures": []}
    assert raw == '{"failures": []}'
    assert usage["input_tokens"] == 100
    assert usage["cached_input_tokens"] == 40
    assert usage["output_tokens"] == 25
    assert usage["total_tokens"] == 125
    assert usage["uncached_input_plus_output_tokens"] == 85

def test_run_codex_classifier_loads_checkpoint_after_truncated_final_response(monkeypatch, tmp_path: Path) -> None:
    from programbench import failure_attribution

    class Completed:
        returncode = 0
        stderr = ""
        stdout = json.dumps(
            {"type": "item.completed", "item": {"type": "agent_message", "text": "truncated final response"}}
        )

    (tmp_path / "classifier_result.json").write_text(
        json.dumps(
            {
                "failures": [
                    {
                        "name": "tests.test_cli.test_case",
                        "branch": "branch-a",
                        "fault": "test",
                    }
                ]
            }
        )
    )
    monkeypatch.setattr(
        failure_attribution,
        "run_codex_in_container",
        lambda *args, **kwargs: {
            "returncode": Completed.returncode,
            "stdout": Completed.stdout,
            "stderr": Completed.stderr,
        },
    )

    result, raw, _ = failure_attribution.run_codex_classifier(
        "classify",
        model="codex/gpt-5.5",
        reasoning_effort="high",
        codex_command="codex exec",
        image="programbench/x_1776_y.abc1234:task_cleanroom_codex",
        timeout=10,
        cwd=tmp_path,
    )

    assert result["failures"][0]["fault"] == "test"
    assert raw == "truncated final response"
    assert "classifier_result.json" in failure_attribution.build_candidate_attribution_prompt(failure_count=1)


def test_run_codex_classifier_loads_checkpoint_after_timeout(monkeypatch, tmp_path: Path, caplog) -> None:
    from programbench import failure_attribution

    checkpoint = {
        "failures": [{
            "name": "tests.test_cli.test_case",
            "branch": "branch-a",
            "fault": "executable",
        }]
    }
    (tmp_path / "classifier_result.json").write_text(json.dumps(checkpoint))
    monkeypatch.setattr(
        failure_attribution,
        "run_codex_in_container",
        lambda *args, **kwargs: {
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "exception_info": "Command timed out after 900s",
        },
    )

    result, raw, usage = failure_attribution.run_codex_classifier(
        "classify",
        model="codex/gpt-5.5",
        reasoning_effort="high",
        codex_command="codex exec",
        image="programbench/x_1776_y.abc1234:task_cleanroom_codex",
        timeout=900,
        cwd=tmp_path,
    )

    assert result == checkpoint
    assert raw == ""
    assert usage == {}
    assert "Codex classifier exited with status -1: Command timed out after 900s" in caplog.text


def test_run_codex_classifier_reports_timeout_without_checkpoint(monkeypatch, tmp_path: Path) -> None:
    from programbench import failure_attribution

    monkeypatch.setattr(
        failure_attribution,
        "run_codex_in_container",
        lambda *args, **kwargs: {
            "returncode": -1,
            "stdout": "",
            "stderr": "",
            "exception_info": "Command timed out after 900s",
        },
    )

    result, _, _ = failure_attribution.run_codex_classifier(
        "classify",
        model="codex/gpt-5.5",
        reasoning_effort="high",
        codex_command="codex exec",
        image="programbench/x_1776_y.abc1234:task_cleanroom_codex",
        timeout=900,
        cwd=tmp_path,
    )

    assert result["subreason"] == "classifier_failed"
    assert result["rationale"] == "Command timed out after 900s"


def test_classify_failures_runs_branches_in_parallel_with_runner(tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.eval.json"
    eval_json.write_text(
        json.dumps(
            {
                "test_results": [
                    {
                        "name": f"tests.test_cli.test_case_{index}",
                        "branch": "branch_a" if index < 2 else "branch_b",
                        "status": "failure",
                        "extra": {"message": "failure", "text": "AssertionError"},
                    }
                    for index in range(4)
                ]
            }
        )
    )
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\nThe program must satisfy the CLI tests.\n")
    output = tmp_path / "failure_attribution.json"
    barrier = threading.Barrier(2)
    lock = threading.Lock()
    active = 0
    max_active = 0

    def runner(prompt: str) -> dict[str, object]:
        nonlocal active, max_active
        branch = "branch_a" if "test branch `branch_a`" in prompt else "branch_b"
        with lock:
            active += 1
            max_active = max(max_active, active)
        barrier.wait(timeout=2)
        time.sleep(0.01)
        with lock:
            active -= 1
        start = 0 if branch == "branch_a" else 2
        return {
            "failures": [
                {
                    "name": f"tests.test_cli.test_case_{index}",
                    "branch": branch,
                    "fault": "executable",
                    "failing_assertion": "AssertionError",
                    "candidate_observed": "AssertionError",
                    "subreason": "parallel_stub",
                    "confidence": 0.8,
                    "rationale": "Stubbed parallel attribution.",
                    "recommended_action": "remove_or_polish_test",
                }
                for index in range(start, start + 2)
            ]
        }

    report = classify_failures(
        eval_json=eval_json,
        spec_dir=spec_dir,
        output=output,
        force=True,
        branch_workers=2,
        runner=runner,
    )

    assert max_active >= 2
    assert len(report.failures) == 4
    assert report.summary == {"error": 0, "error_infra": 0, "executable": 4, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 0}
    assert [failure.name for failure in report.failures] == [
        "tests.test_cli.test_case_0",
        "tests.test_cli.test_case_1",
        "tests.test_cli.test_case_2",
        "tests.test_cli.test_case_3",
    ]


def test_classify_failures_splits_large_branches_into_bounded_ordered_batches(tmp_path: Path) -> None:
    task = "org__repo.123"
    names = [f"tests.test_cli.test_case_{index}" for index in range(5)]
    eval_json = tmp_path / f"{task}.eval.json"
    eval_json.write_text(json.dumps({
        "test_results": [
            {
                "name": name,
                "branch": "large_branch",
                "status": "failure",
                "extra": {"message": "failure", "text": "AssertionError"},
            }
            for name in names
        ]
    }))
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\nThe CLI must work.\n")
    batches = [names[:2], names[2:4], names[4:]]
    calls: list[list[str]] = []

    def runner(_prompt: str) -> dict[str, object]:
        batch = batches[len(calls)]
        calls.append(batch)
        return {"failures": [
            {
                "name": name,
                "branch": "large_branch",
                "fault": "executable",
                "failing_assertion": "AssertionError",
                "candidate_observed": "AssertionError",
                "recommended_action": "remove_or_polish_test",
            }
            for name in batch
        ]}

    report = classify_failures(
        eval_json=eval_json,
        spec_dir=spec_dir,
        output=tmp_path / "failure_attribution.json",
        batch_size=2,
        branch_workers=1,
        runner=runner,
    )

    assert calls == batches
    assert [failure.name for failure in report.failures] == names
    assert report.summary == {"error": 0, "error_infra": 0, "executable": 5, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 0}


def test_evaluation_errors_are_rule_based_and_not_sent_to_classifier(tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.eval.json"
    eval_json.write_text(json.dumps({
        "test_results": [
            {
                "name": "tests.test_cli.test_not_run",
                "branch": "broken_branch",
                "status": "not_run",
                "extra": {"error_code": "run_tests_timeout"},
            },
            {
                "name": "tests.test_cli.test_bad_output",
                "branch": "working_branch",
                "status": "failure",
                "extra": {"message": "wrong stdout", "text": "AssertionError"},
            },
        ],
        "test_branch_errors": {
            "broken_branch": [
                {"error_code": "run_tests_timeout", "error_details": "Command timed out after 3600s"}
            ]
        },
    }))
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("The CLI prints the expected output.\n")
    calls: list[str] = []

    def runner(prompt: str) -> dict[str, object]:
        calls.append(prompt)
        return {"failures": [{
            "name": "tests.test_cli.test_bad_output",
            "branch": "working_branch",
            "fault": "executable",
            "failing_assertion": "AssertionError",
            "candidate_observed": "AssertionError",
            "recommended_action": "ignore",
        }]}

    report = classify_failures(
        eval_json=eval_json,
        spec_dir=spec_dir,
        output=tmp_path / "failure_attribution.json",
        runner=runner,
    )

    assert len(calls) == 1
    assert "test_not_run" not in calls[0]
    assert [failure.fault for failure in report.failures] == ["error_infra", "executable"]
    assert report.failures[0].subreason == "run_tests_timeout"
    assert report.failures[0].recommended_action == "fix_evaluation"
    assert "Command timed out after 3600s" in report.failures[0].rationale
    assert report.summary == {"error": 0, "error_infra": 1, "executable": 1, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 0}


def test_classifier_workspace_stages_only_spec_and_failures(tmp_path: Path) -> None:
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\nAlpha.\n")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    failure = FailureCase(
        instance_id="org__repo.trusted",
        name="tests.test_cli.test_alpha",
        branch="branch_a",
        status="failure",
    )

    stage_classifier_workspace(
        workspace=workspace,
        spec_dir=spec_dir,
        failures=[failure],
    )

    assert (workspace / "spec" / "spec.md").is_file()
    assert json.loads((workspace / "failures.json").read_text())[0]["name"] == failure.name
    assert not (workspace / "test").exists()
    assert not (workspace / "test_spec_links.json").exists()


def test_failure_report_includes_error_log_and_relevant_specs(tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.eval.json"
    eval_json.write_text(json.dumps({
        "test_results": [{
            "name": "tests.test_cli.test_color[red]",
            "branch": "branch_a",
            "status": "failure",
            "extra": {"message": "wrong color", "text": "AssertionError: expected red"},
        }]
    }))
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 2\nRender colors.\n## Spec 5\nValidate colors.\n")
    links = tmp_path / "test_spec_links.json"
    links.write_text(json.dumps({
        "instance_id": task,
        "spec_sections": ["Spec 2", "Spec 5"],
        "test_functions": [{
            "id": "branch_a/tests.test_cli.test_color",
            "branch": "branch_a",
            "name": "tests.test_cli.test_color",
            "target_specs": ["Spec 2", "Spec 5"],
            "description": "Checks color rendering and validation.",
        }],
    }))

    report = classify_failures(
        eval_json=eval_json,
        spec_dir=spec_dir,
        test_spec_links=links,
        output=tmp_path / "failure_attribution.json",
        runner=lambda _prompt: {"failures": [{
            "name": "tests.test_cli.test_color[red]",
            "branch": "branch_a",
            "fault": "spec_underspecification",
            "failing_assertion": "AssertionError",
            "candidate_observed": "AssertionError",
            "rationale": "Spec 7 clarifies validation while Spec 2 describes rendering.",
            "recommended_action": "polish_spec",
        }]},
    )

    assert report.test_spec_links == str(links)
    assert report.failures[0].error_log == "AssertionError: expected red"
    assert report.failures[0].relevant_specs == ["Spec 2", "Spec 5", "Spec 7"]
    persisted = json.loads((tmp_path / "failure_attribution.json").read_text())
    assert persisted["failures"][0]["error_log"] == "AssertionError: expected red"
    assert persisted["failures"][0]["relevant_specs"] == ["Spec 2", "Spec 5", "Spec 7"]


def _attribution(subreason: str) -> FailureAttribution:
    return FailureAttribution(
        instance_id="task__repo.abc", name=f"t_{subreason}", status="failed",
        fault="unknown" if subreason else "spec", subreason=subreason,
    )


@pytest.mark.parametrize(
    ("records", "rejected"),
    [
        ([_attribution("")] * 100, False),
        ([_attribution("classifier_failed")] * 1299, True),
        ([_attribution("invalid_batch_result")] * 142 + [_attribution("")] * 370, True),
        ([_attribution("missing_batch_result")] * 4 + [_attribution("")] * 20, False),
        ([_attribution("missing_batch_result")] * 9 + [_attribution("")] * 5, False),
        ([_attribution("corrupt_mp4_prevents_seeking")] * 50, False),
    ],
)
def test_check_attribution_usable_rejects_only_wholesale_classifier_breakage(
    records: list[FailureAttribution], rejected: bool
) -> None:
    if rejected:
        with pytest.raises(RuntimeError, match="failed inside the classifier"):
            check_attribution_usable(records, "Failure attribution")
    else:
        assert check_attribution_usable(records, "Failure attribution") is None


def test_classify_failures_halves_a_branch_whose_classifier_returned_nothing(tmp_path: Path) -> None:
    task = "org__repo.123"
    names = [f"tests.test_cli.test_case_{index}" for index in range(4)]
    eval_json = tmp_path / f"{task}.eval.json"
    eval_json.write_text(json.dumps({
        "test_results": [
            {
                "name": name,
                "branch": "slow_branch",
                "status": "failure",
                "extra": {"message": "failure", "text": "AssertionError"},
            }
            for name in names
        ]
    }))
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\nThe CLI must work.\n")
    # The full branch times out; each half then comes back cleanly.
    batches = [names, names[:2], names[2:]]
    calls: list[list[str]] = []

    def runner(_prompt: str) -> dict[str, object]:
        batch = batches[len(calls)]
        calls.append(batch)
        if len(calls) == 1:
            return {"fault": "unknown", "subreason": "classifier_failed", "rationale": "timed out"}
        return {"failures": [
            {
                "name": name,
                "branch": "slow_branch",
                "fault": "executable",
                "failing_assertion": "AssertionError",
                "candidate_observed": "AssertionError",
                "recommended_action": "remove_or_polish_test",
            }
            for name in batch
        ]}

    report = classify_failures(
        eval_json=eval_json,
        spec_dir=spec_dir,
        output=tmp_path / "failure_attribution.json",
        runner=runner,
    )

    assert calls == batches
    assert [failure.name for failure in report.failures] == names
    assert report.summary == {"error": 0, "error_infra": 0, "executable": 4, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 0}
    assert [error["subreason"] for failure in report.failures for error in failure.classifier_errors] == [
        "invalid_batch_result"
    ] * 4
    check_attribution_usable(report.failures, "Failure attribution")


def test_classify_failures_recomputes_an_unusable_cached_report(tmp_path: Path) -> None:
    task = "org__repo.123"
    names = [f"tests.test_cli.test_case_{index}" for index in range(20)]
    eval_json = tmp_path / f"{task}.eval.json"
    eval_json.write_text(json.dumps({
        "test_results": [
            {"name": name, "branch": "b1", "status": "failure", "extra": {"message": "failure", "text": "AssertionError"}}
            for name in names
        ]
    }))
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\nThe CLI must work.\n")
    output = tmp_path / "failure_attribution.json"
    # A report left behind by a broken classifier run must not short-circuit the rerun.
    output.write_text(json.dumps({
        "eval_json": str(eval_json),
        "spec_dir": str(spec_dir),
        "output": str(output),
        "summary": {"error": 0, "error_infra": 0, "executable": 0, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 20},
        "failures": [
            {
                "instance_id": task,
                "name": name,
                "branch": "b1",
                "status": "failure",
                "fault": "unknown",
                "subreason": "invalid_batch_result",
            }
            for name in names
        ],
    }))

    def runner(_prompt: str) -> dict[str, object]:
        return {"failures": [
            {"name": name, "branch": "b1", "fault": "executable", "recommended_action": "polish_spec", "failing_assertion": "AssertionError", "candidate_observed": "AssertionError"}
            for name in names
        ]}

    report = classify_failures(
        eval_json=eval_json,
        spec_dir=spec_dir,
        output=output,
        runner=runner,
    )

    assert report.summary == {"error": 0, "error_infra": 0, "executable": 20, "spec_underspecification": 0, "spec_contradiction": 0, "unknown": 0}
    check_attribution_usable(report.failures, "Failure attribution")


def test_environment_failures_are_classifiable_as_error_rather_than_a_spec_fault() -> None:
    """A sandbox with no network must not be read as evidence the spec is wrong.

    Blocked egress made the reference binary abort mid-run, and with no `error`
    value available the classifier had to spend a spec fault on it, which then
    sent the polish step chasing a specification defect that did not exist.
    """
    prompt = build_candidate_attribution_prompt(failure_count=1)
    assert eval_network_note() in prompt
    assert "error|unknown" in prompt

    attribution = _attribution_from_result(
        FailureCase(instance_id="org__repo.123", name="test_one", status="failure"),
        {"fault": "error", "subreason": "proxy_blocked_fetch", "confidence": 0.9, "rationale": "DNS failure."},
        raw_response="{}",
    )
    assert (attribution.fault, attribution.recommended_action) == ("error", "ignore")


def test_spec_contradiction_requires_a_quoted_conflict_not_an_inferred_one() -> None:
    """The classifier compares test text to spec text and nothing else.

    Any expectation the spec failed to mention used to read as a contradiction, which
    is what ratcheted underspecification into contradiction across iterations.
    """
    prompt = build_candidate_attribution_prompt(failure_count=1)
    assert "Decide from the record, the specification, and what `/workspace/executable` does" in prompt
    assert "is never a contradiction" in prompt
    assert "the fault is not a contradiction" in prompt


def test_offline_package_installs_are_resolved_without_spending_a_classifier_call() -> None:
    """A blocked pip index is recognisable from its own output, so the judge never sees it.

    These arrive in bulk -- one per test in an aborted branch -- and every one of
    them would otherwise cost a classifier call to reach a verdict that is already
    certain from the traceback.
    """
    failure = FailureCase(
        instance_id="org__repo.123",
        name="test_one",
        status="failure",
        traceback="ERROR: No matching distribution found for requests",
    )
    attribution = _evaluation_error_attribution(failure)
    assert _is_evaluation_error(failure)
    assert (attribution.fault, attribution.subreason) == ("error_infra", "offline_package_install")


def test_network_tool_diagnostics_are_not_mistaken_for_infrastructure_failures() -> None:
    """dog, curlie, muffet and pingu emit connection errors as the behavior under test.

    Matching generic network wording would silently bury real defects in those
    tasks, so the pre-filter keys only on strings pip itself prints.
    """
    assert not _is_installer_network_failure(
        FailureCase(
            instance_id="org__repo.123",
            name="test_dns_failure_message",
            status="failure",
            traceback="assert 'Temporary failure in name resolution' in result.stderr\nConnection refused",
        )
    )


def test_candidate_attribution_prompt_requires_running_the_reference_for_contradictions() -> None:
    """A contradiction verdict from the record alone was wrong three times out of four: diffs read
    backwards, the wrong flag assumed, candidate bugs excused. The reference binary is in the
    workspace so the claim can be checked by execution, and the prompt says which side of a
    pytest diff is the candidate.
    """
    prompt = build_candidate_attribution_prompt(failure_count=1)
    assert "`/workspace/executable`: the **reference** implementation" in prompt
    assert "reconstruct the failing invocation from the traceback, run it\n  on `/workspace/executable`" in prompt
    assert "`-` lines are the assert's right operand and `+` lines its left one" in prompt
    assert "`CompletedProcess(...)` repr is the candidate's output" in prompt
    assert "/workspace/failures.json" in prompt and "\n- `spec/`" not in prompt
    assert "Put that sentence in `spec_quote`" in prompt


@pytest.mark.parametrize(
    ("network", "phrase"),
    [("none", "networking disabled"), ("bridge", "network access (docker network `bridge`)")],
)
def test_prompt_network_sentence_follows_the_eval_network(monkeypatch, network, phrase) -> None:
    import programbench.constants as constants

    monkeypatch.setattr(constants, "EVAL_NETWORK", network)
    assert phrase in build_candidate_attribution_prompt(failure_count=1)


def test_classifier_workspace_holds_the_staged_spec_records_and_reference_binary(tmp_path: Path) -> None:
    """The cleanroom image ships the reference binary, a README and git metadata in /workspace;
    the setup prefix removes everything but the staged files and the binary.
    """
    from programbench.failure_attribution import classifier_setup_prefix

    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\n")
    workspace = tmp_path / "ws"
    workspace.mkdir()

    stage_classifier_workspace(
        workspace=workspace,
        spec_dir=spec_dir,
        failures=[FailureCase(instance_id="org__repo.abc", name="t", status="failure")],
    )
    assert sorted(path.name for path in workspace.iterdir()) == ["failures.json", "spec"]
    assert classifier_setup_prefix() == (
        "find /workspace -mindepth 1 -maxdepth 1 ! -name spec ! -name failures.json ! -name reference-tests ! -name executable -exec rm -rf {} +; "
    )


def test_classifier_sandbox_is_offline_and_states_that_only_failures_json_is_given(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The candidate was graded with no network, so a reference run that could reach the internet
    would observe behavior the candidate never could. The egress network admits only the model
    API, which also rules out fetching codex with npx at runtime and reading upstream sources.
    """
    from programbench import failure_attribution
    from programbench.constants import agent_network_args
    from programbench.failure_attribution import DEFAULT_CODEX_COMMAND, run_codex_classifier

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        failure_attribution,
        "run_codex_in_container",
        lambda *args, **kwargs: captured.update(kwargs) or {"returncode": 0, "stdout": "", "stderr": ""},
    )
    run_codex_classifier(
        "prompt", image="img", model="", reasoning_effort="", codex_command=DEFAULT_CODEX_COMMAND, timeout=1, cwd=tmp_path
    )
    assert captured["network_args"] == agent_network_args()
    assert DEFAULT_CODEX_COMMAND.startswith("codex ") and "npx" not in DEFAULT_CODEX_COMMAND

    prompt = build_candidate_attribution_prompt(failure_count=1)
    assert "`/workspace/reference-tests/`: the fixed reference suite itself, read-only" in prompt
    assert "Networking is disabled in this sandbox" not in prompt


@pytest.mark.parametrize(
    ("quote", "spec", "expected"),
    [
        (
            "-V and --version both print exactly one newline-terminated string",
            "`-V` and `--version` both print exactly one newline-terminated string matching `oranda X.Y.Z`.",
            True,
        ),
        ("--help and -? select help and exit 0.", "Spec 2. `--help` and `-?` select help and exit `0`.", True),
        ("It writes \u201cnothing\u201d to standard error \u2013 ever", 'It  writes "nothing"\nto standard error - ever', True),
        ("**Never** overwrite an existing destination", "never overwrite an existing destination by default", True),
        ("exit 0.", "`--help` and `-?` select help and exit `0`.", False),
        ("prints Dirble 1.4.2 on --version", "prints nothing on --version", False),
    ],
)
def test_spec_quote_is_verifiable_ignores_markdown_and_typography(quote, spec, expected):
    assert spec_quote_is_verifiable(quote, spec) is expected


def test_verdicts_quoting_evidence_from_another_record_are_rejected_and_rejudged(tmp_path: Path) -> None:
    """One rationale pasted across a whole test file is the batch failure mode: eight zstd records
    were called /dev/null overwrite refusals when their own tracebacks showed an option being
    rejected. Evidence copied from the wrong record is detectable without a model.
    """
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.eval.json"
    tracebacks = {
        "tests.test_adaptive.test_option": "assert result.returncode == 0\nE   stderr='Incorrect parameter: --adapt=min=1,max=10\\n'",
        "tests.test_adaptive.test_dev_null": "assert result.returncode == 0\nE   stderr='/dev/null: destination already exists\\n'",
        "tests.test_adaptive.test_fabricated": "assert result.returncode == 0\nE   stderr='/dev/null: destination already exists\\n'",
    }
    eval_json.write_text(json.dumps({"test_results": [
        {"name": name, "branch": "b1", "status": "failure", "extra": {"message": "m", "text": text}}
        for name, text in tracebacks.items()
    ]}))
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 20\nNever overwrite an existing destination by default.\n")
    prompts: list[str] = []

    def runner(prompt: str) -> dict[str, object]:
        prompts.append(prompt)
        pasted = {
            "fault": "spec_contradiction", "recommended_action": "polish_spec",
            "failing_assertion": "assert result.returncode == 0",
            "candidate_observed": "/dev/null: destination already exists",
            "spec_quote": "Never overwrite an existing destination by default.",
        }
        if len(prompts) == 1:
            return {"failures": [
                {"name": "tests.test_adaptive.test_option", "branch": "b1", **pasted},
                {"name": "tests.test_adaptive.test_dev_null", "branch": "b1", **pasted},
                {"name": "tests.test_adaptive.test_fabricated", "branch": "b1", **pasted, "spec_quote": "Overwriting /dev/null requires -f."},
            ]}
        return {"failures": [
            {"name": "tests.test_adaptive.test_option", "branch": "b1", "fault": "executable", "recommended_action": "ignore",
             "failing_assertion": "assert result.returncode == 0", "candidate_observed": "Incorrect parameter: --adapt=min=1,max=10"},
            {"name": "tests.test_adaptive.test_fabricated", "branch": "b1", **pasted, "spec_quote": "Overwriting /dev/null requires -f."},
        ]}

    report = classify_failures(eval_json=eval_json, spec_dir=spec_dir, output=tmp_path / "out.json", runner=runner)

    assert len(prompts) == 2 and "There are 2 failures" in prompts[1]
    assert [(f.fault, f.subreason) for f in report.failures] == [
        ("executable", ""),
        ("spec_contradiction", ""),
        ("unknown", "unverified_spec_quote"),
    ]
    assert report.failures[0].candidate_observed == "Incorrect parameter: --adapt=min=1,max=10"
    assert report.summary == {"error": 0, "error_infra": 0, "executable": 1, "spec_underspecification": 0, "spec_contradiction": 1, "unknown": 1}


def test_classifier_workspace_stages_the_reference_suite_beside_the_records(tmp_path: Path) -> None:
    """The traceback pytest prints is elided and golden files never appear in it, so fixture
    ports and expected bytes were unjudgeable; the suite is staged read-only next to the records.
    """
    from programbench.failure_attribution import classifier_setup_prefix

    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    (spec_dir / "spec.md").write_text("## Spec 1\n")
    reference = tmp_path / "extracted-tests" / "org__repo.abc"
    (reference / "tests" / "__pycache__").mkdir(parents=True)
    (reference / "tests" / "test_cli.py").write_text("def test_cli(): ...\n")
    (reference / "tests" / "__pycache__" / "test_cli.pyc").write_bytes(b"\x00")
    (reference / "tests" / "expected.golden").write_text("Error : X is not a file \n")
    workspace = tmp_path / "ws"
    workspace.mkdir()

    stage_classifier_workspace(
        workspace=workspace,
        spec_dir=spec_dir,
        failures=[FailureCase(instance_id="org__repo.abc", name="t", status="failure")],
        reference_tests_dir=reference,
    )

    assert sorted(path.name for path in workspace.iterdir()) == ["failures.json", "reference-tests", "spec"]
    assert (workspace / "reference-tests" / "tests" / "expected.golden").read_text().startswith("Error :")
    assert not (workspace / "reference-tests" / "tests" / "__pycache__").exists()
    assert "! -name reference-tests" in classifier_setup_prefix()
def test_classifier_branch_inputs_and_verdict_are_kept_beside_the_report(monkeypatch, tmp_path: Path) -> None:
    task = "org__repo.123"
    eval_json = tmp_path / f"{task}.eval.json"
    eval_json.write_text(json.dumps({"test_results": [
        {"name": "tests.test_cli.test_alpha", "branch": "b1", "status": "failure",
         "extra": {"message": "wrong stdout", "text": "AssertionError"}},
    ]}))
    spec_dir = tmp_path / "spec" / task
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("## Spec 1\nAlpha.\n")
    verdict = {"failures": [{
        "name": "tests.test_cli.test_alpha", "branch": "b1", "fault": "executable",
        "subreason": "wrong_stdout", "confidence": 0.9, "rationale": "Spec 1 defines it.",
        "recommended_action": "ignore", "failing_assertion": "AssertionError",
        "candidate_observed": "AssertionError",
    }]}

    def fake_container(command, *, cwd, **kwargs):
        (cwd / "classifier_result.json").write_text(json.dumps(verdict))
        return {"returncode": 0, "stdout": '{"output_path": "classifier_result.json"}', "stderr": ""}

    monkeypatch.setattr(failure_attribution, "run_codex_in_container", fake_container)
    output = tmp_path / "failure_attribution.json"

    report = classify_failures(eval_json=eval_json, spec_dir=tmp_path / "spec", output=output)

    branch_dir = tmp_path / "failure_attribution" / "branch_0001"
    assert report.failures[0].fault == "executable"
    assert json.loads((branch_dir / "failures.json").read_text())[0]["name"] == "tests.test_cli.test_alpha"
    assert json.loads((branch_dir / "classifier_result.json").read_text()) == verdict
    assert "classify_failures.prompt.md" in [p.name for p in branch_dir.iterdir()]


@pytest.mark.parametrize(
    ("candidate_observed", "expected"),
    [
        ("''", "executable"),
        ("b''", "executable"),
        ("stderr=b''", "executable"),
        ("", "unknown"),
        ("   ", "unknown"),
        ("Incorrect parameter: --adapt", "unknown"),
    ],
)
def test_empty_observed_output_survives_evidence_verification(candidate_observed: str, expected: str) -> None:
    """An observation of nothing is the evidence for the commonest executable fault, so it must not
    be demoted by a length floor, while a fabricated or absent observation still is."""
    failure = FailureCase(
        instance_id="org__repo.123", name="t", branch="b1", status="failure",
        traceback="assert 'bytes' in output\nE   AssertionError: expected verbose output, stderr=b'': \nE   assert 'bytes' in ''",
    )
    attributions = {0: FailureAttribution(
        instance_id="org__repo.123", name="t", branch="b1", status="failure", fault="executable",
        failing_assertion="assert 'bytes' in output", candidate_observed=candidate_observed,
    )}

    assert reject_unverified_attributions(attributions, [failure], "") == ([] if expected == "executable" else [0])
    assert attributions[0].fault == expected
    assert attributions[0].subreason == ("" if expected == "executable" else "unverified_record_evidence")
