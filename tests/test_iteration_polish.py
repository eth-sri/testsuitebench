import json
import logging
from pathlib import Path

import pytest

from programbench import iteration_polish
from programbench.iteration_polish import flag_candidate_derived_literals, polish_iteration, prepare_polish_jobs, write_directory_diff


def _write_empty_reference_tests(root: Path, task: str) -> Path:
    tests_dir = root / "reference-tests"
    task_tests = tests_dir / task
    task_tests.mkdir(parents=True)
    (task_tests / "tests.json").write_text("{\"branches\": {}}")
    return tests_dir


def test_run_codex_polish_logs_session_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_codex_in_container(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {"image": "codex-image", "returncode": 7}

    monkeypatch.setattr(iteration_polish, "run_codex_in_container", fake_run_codex_in_container)
    caplog.set_level(logging.INFO, logger="programbench.iteration_polish")

    result = iteration_polish.run_codex_polish(
        iter_dir=tmp_path,
        task="org__repo.123",
        model="codex/gpt-test",
        reasoning_effort="high",
        codex_command="codex exec",
        timeout=60,
        prompt="Polish the spec",
        diagnostic_action="test polish",
        stage_paths=[],
        copy_back_paths=[],
    )

    assert result["returncode"] == 7
    assert "Finished Codex session with status 7" in caplog.messages
    # The task cleanroom image carries the reference binary, so polish can observe
    # real behavior instead of declaring the contested detail non-contractual.
    assert calls[0]["image"] == "programbench/org_1776_repo.123:task_cleanroom_codex"


def test_polish_iteration_dry_run_copies_only_previous_spec(tmp_path: Path) -> None:
    task = "org__repo.123"
    iter_root = tmp_path / "iterative"
    this_iter = iter_root / "iter_0"
    next_iter = iter_root / "iter_1"
    spec_file = this_iter / "spec" / task / "spec.md"
    spec_file.parent.mkdir(parents=True)
    spec_file.write_text("## Spec 1\nOld spec.\n")
    links_in = this_iter / "test-spec-links" / task / "test_spec_links.json"
    links_in.parent.mkdir(parents=True)
    links_in.write_text('{"test_functions": []}\n')
    task_log_dir = next_iter / "log" / task
    task_log_dir.mkdir(parents=True)
    (task_log_dir / "failure_attribution.json").write_text(
        json.dumps({"summary": {"spec_underspecification": 1, "spec_contradiction": 0}, "failures": [{"fault": "spec_underspecification"}]})
    )
    tests_dir = _write_empty_reference_tests(tmp_path, task)

    result = polish_iteration(iter_root=iter_root, task=task, iteration=0, tests_dir=tests_dir, dry_run=True, force=True)

    assert (next_iter / "spec" / task / "spec.md").read_text() == "## Spec 1\nOld spec.\n"
    assert not (next_iter / "test").exists()
    assert (task_log_dir / "polish_spec_001.prompt.md").is_file()
    assert not list(task_log_dir.glob("failure_attribution*.actionable.json"))
    prompt = (task_log_dir / "polish_spec_001.prompt.md").read_text()
    assert "complete batch" in prompt
    assert "Inspect every entry" in prompt
    assert (task_log_dir / "spec.diff.patch").is_file()
    assert not (task_log_dir / "test.diff.patch").exists()
    log = json.loads((task_log_dir / "polish_spec.traj.json").read_text())
    assert log["dry_run"] is True
    assert log["spec_diff"] == str(task_log_dir / "spec.diff.patch")
    assert "test_diff" not in log
    assert "test_out" not in log
    assert "actionable_attribution" not in log
    assert [job["name"] for job in log["jobs"]] == ["spec_001"]
    links_out = next_iter / "test-spec-links" / task / "test_spec_links.json"
    assert links_out.is_file()
    assert result["test_spec_links"]["output"] == str(links_out)
    assert result["log"] == str(task_log_dir / "polish_spec.traj.json")


def test_polish_iteration_requires_some_attribution(tmp_path: Path) -> None:
    task = "org__repo.123"
    iter_root = tmp_path / "iterative"
    (iter_root / "iter_0" / "spec" / task).mkdir(parents=True)

    with pytest.raises(FileNotFoundError, match="failure_attribution.json nor mutant_attribution.json"):
        polish_iteration(iter_root=iter_root, task=task, iteration=0, tests_dir=tmp_path / "reference-tests", dry_run=True)


def test_polish_iteration_runs_from_mutant_attribution_alone(tmp_path: Path) -> None:
    """A converged reference-test direction is not rerun, so its attribution is absent."""
    task = "org__repo.123"
    iter_root = tmp_path / "iterative"
    (iter_root / "iter_0" / "spec" / task).mkdir(parents=True)
    (iter_root / "iter_0" / "spec" / task / "spec.md").write_text("## Spec 1\n")
    links_in = iter_root / "iter_0" / "test-spec-links" / task / "test_spec_links.json"
    links_in.parent.mkdir(parents=True)
    links_in.write_text("{}")
    task_log_dir = iter_root / "iter_1" / "log" / task
    task_log_dir.mkdir(parents=True)
    (task_log_dir / "mutant_attribution.json").write_text(json.dumps({
        "test_failures": [{"name": "gen_a", "fault": "spec_underspecification", "error_log": "E"}],
        "mutants": [{"mutant_id": "repo_7", "fault": "spec_contradiction"}, {"mutant_id": "repo_8", "fault": "test"}],
    }))

    result = polish_iteration(iter_root=iter_root, task=task, iteration=0, tests_dir=_write_empty_reference_tests(tmp_path, task), dry_run=True)

    assert result["failure_attribution"] == "" and result["mutant_attribution"].endswith("mutant_attribution.json")
    batch = json.loads((task_log_dir / "failure_attribution.spec_001.json").read_text())
    assert batch["source"] == "" and [record["kind"] for record in batch["failures"]] == ["generated_test", "survived_mutant"]


def test_write_directory_diff_saves_patch(tmp_path: Path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    (before / "spec.md").write_text("old\n")
    (after / "spec.md").write_text("new\n")
    output = tmp_path / "spec.diff.patch"

    write_directory_diff(before=before, after=after, output=output)

    diff = output.read_text()
    assert "-old" in diff
    assert "+new" in diff


def test_prepare_polish_jobs_ignores_reference_test_faults(tmp_path: Path) -> None:
    task = "org__repo.123"
    log_dir = tmp_path / "log" / task
    log_dir.mkdir(parents=True)
    attribution = log_dir / "failure_attribution.json"
    attribution.write_text(
        json.dumps(
            {
                "summary": {"spec_underspecification": 1, "spec_contradiction": 0, "test": 2},
                "failures": [
                    {"fault": "spec_underspecification", "recommended_action": "polish_spec", "name": "spec_case"},
                    {"fault": "test", "branch": "branch_a", "recommended_action": "ignore", "name": "test_case_a"},
                    {"fault": "test", "branch": "branch_b", "recommended_action": "ignore", "name": "test_case_b"},
                ],
            }
        )
    )

    jobs = prepare_polish_jobs(attribution=attribution, task_log_dir=log_dir, task=task)

    assert [(job["kind"], job["branch"]) for job in jobs] == [("spec", "")]
    assert "actionable" not in jobs[0]
    assert not list(log_dir.glob("failure_attribution*.actionable.json"))
    batch = json.loads(Path(jobs[0]["attribution"]).read_text())
    assert [failure["name"] for failure in batch["failures"]] == ["spec_case"]
    prompt = Path(jobs[0]["prompt"]).read_text()
    assert "fixed reference suite" in prompt
    assert "failure_attribution.spec_001.json" in prompt
    assert "do not omit entries" in prompt
    assert "Never create or edit an iteration-local test suite" in prompt
    assert "/workspace/executable" in prompt
    assert "Do not resolve an entry by weakening a requirement" in prompt
    assert not list(log_dir.glob("polish_test_*.prompt.md"))


def test_polish_iteration_uses_attribution_without_copying_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = "org__repo.123"
    iter_root = tmp_path / "iterative"
    this_iter = iter_root / "iter_0"
    next_iter = iter_root / "iter_1"
    spec_file = this_iter / "spec" / task / "spec.md"
    spec_file.parent.mkdir(parents=True)
    spec_file.write_text("## Spec 1\nAmbiguous spec.\n")
    links_in = this_iter / "test-spec-links" / task / "test_spec_links.json"
    links_in.parent.mkdir(parents=True)
    links_in.write_text('{"test_functions": []}\n')
    log_dir = next_iter / "log" / task
    log_dir.mkdir(parents=True)
    (log_dir / "failure_attribution.json").write_text(
        json.dumps({"summary": {"spec_underspecification": 1, "spec_contradiction": 0}, "failures": [{"fault": "spec_underspecification", "name": "test_cli"}]})
    )
    calls: list[dict[str, object]] = []
    tests_dir = _write_empty_reference_tests(tmp_path, task)

    def fake_run_codex_polish(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        (Path(kwargs["copy_back_paths"][0]) / "spec.md").write_text("## Spec 1\nClarified spec.\n")
        return {"returncode": 0}

    monkeypatch.setattr(iteration_polish, "run_codex_polish", fake_run_codex_polish)

    result = polish_iteration(iter_root=iter_root, task=task, iteration=0, tests_dir=tests_dir, force=True)

    assert not (next_iter / "test").exists()
    assert calls[0]["stage_paths"] == [
        next_iter / "spec" / task,
        log_dir / "failure_attribution.spec_001.json",
    ]
    assert calls[0]["copy_back_paths"] == [next_iter / "spec" / task]
    links_out = next_iter / "test-spec-links" / task / "test_spec_links.json"
    assert links_out.read_text() == links_in.read_text()
    assert spec_file.read_text() == "## Spec 1\nAmbiguous spec.\n"
    assert "+Clarified spec." in (log_dir / "spec.diff.patch").read_text()


def test_prepare_polish_jobs_batches_complete_spec_failures_and_skips_executable(tmp_path: Path) -> None:
    task = "org__repo.123"
    log_dir = tmp_path / "log" / task
    log_dir.mkdir(parents=True)
    attribution = log_dir / "failure_attribution.json"
    spec_failures = [
        {
            "fault": "spec_underspecification",
            "name": f"spec_case_{index}",
            "rationale": f"full rationale {index}",
            "recommended_action": "polish_spec",
        }
        for index in range(121)
    ]
    attribution.write_text(
        json.dumps(
            {
                "summary": {"spec_underspecification": 121, "spec_contradiction": 0, "executable": 2, "unknown": 1},
                "failures": [
                    spec_failures[0],
                    {"fault": "executable", "name": "implementation_failure"},
                    *spec_failures[1:],
                    {"fault": "unknown", "name": "unknown_failure"},
                    {"fault": "executable", "name": "second_implementation_failure"},
                ],
            }
        )
    )

    jobs = prepare_polish_jobs(attribution=attribution, task_log_dir=log_dir, task=task)

    assert [job["name"] for job in jobs] == ["spec_001", "spec_002", "spec_003"]
    batches = [json.loads(Path(job["attribution"]).read_text()) for job in jobs]
    assert [batch["batch"]["count"] for batch in batches] == [50, 50, 21]
    assert all(batch["batch"]["total_spec_failures"] == 121 for batch in batches)
    combined = [failure for batch in batches for failure in batch["failures"]]
    assert [{key: value for key, value in failure.items() if key not in {"kind", "evidence_source"}} for failure in combined] == spec_failures
    assert {(failure["kind"], failure["evidence_source"]) for failure in combined} == {("reference_test", "candidate")}


def test_polish_batch_relabels_candidate_output_and_prompt_forbids_copying_it(tmp_path: Path) -> None:
    log_dir = tmp_path / "iter_1" / "log" / "t"
    log_dir.mkdir(parents=True)
    attribution = log_dir / "failure_attribution.json"
    attribution.write_text(json.dumps({"failures": [
        {"name": "a", "fault": "spec_contradiction", "error_log": "E + candidate said X", "rationale": "r"},
    ]}))
    jobs = prepare_polish_jobs(attribution=attribution, task_log_dir=log_dir, task="t")
    batch = json.loads(Path(jobs[0]["attribution"]).read_text())["failures"][0]
    assert batch["candidate_error_log"] == "E + candidate said X" and "error_log" not in batch
    prompt = Path(jobs[0]["prompt"]).read_text()
    assert "quote the CANDIDATE's output" in prompt
    assert "must come from running `/workspace/executable` yourself" in prompt


def test_flag_candidate_derived_literals_reports_only_candidate_only_additions(tmp_path: Path) -> None:
    spec_in, spec_out = tmp_path / "in", tmp_path / "out"
    candidate, reference = tmp_path / "cand", tmp_path / "ref"
    for d in (spec_in, spec_out, candidate, reference):
        d.mkdir()
    (spec_in / "spec.md").write_text("Prints `already there` on exit.")
    (spec_out / "spec.md").write_text(
        "Prints `already there` on exit. Skips with `[INFO] Skipping <folder>/: validator returned 401; use --scan-401`. "
        "Errors say `No regular files to watch`. Also `brand new claim` and `\\documentclass[]{book}`."
    )
    (candidate / "main.py").write_text('print(f"[INFO] Skipping {fs}: validator returned {c}")\nprint("No regular files to watch")')
    (candidate / "spec.md").write_text("`brand new claim`")
    (reference / "test_x.py").write_text('assert "No regular files to watch" in err')
    logs = "E + [INFO] Skipping http://127.0.0.1:1/x/: validator returned 401; use --scan-401\nE + \\documentclass[]{book}"
    assert flag_candidate_derived_literals(
        spec_in=spec_in, spec_out=spec_out, candidate_dir=candidate, reference_dir=reference, candidate_logs=logs
    ) == {
        "added_literals": 4,
        "flagged": ["[INFO] Skipping <folder>/: validator returned 401; use --scan-401", "\\documentclass[]{book}"],
    }


def test_polish_jobs_merge_both_evaluation_directions_and_label_whose_output_each_log_quotes(tmp_path: Path) -> None:
    """One polish pass per iteration reads reference-test, generated-test and mutant evidence
    against the same specification. A reference-test log quotes the candidate; a generated-test
    log quotes the reference, so the two are renamed apart before the polisher sees them.
    """
    from programbench.iteration_polish import spec_fault_records

    log_dir = tmp_path / "log" / "t"
    log_dir.mkdir(parents=True)
    attribution = log_dir / "failure_attribution.json"
    attribution.write_text(json.dumps({"failures": [
        {"name": "ref_a", "fault": "spec_contradiction", "error_log": "E + candidate said X"},
        {"name": "ref_b", "fault": "executable", "error_log": "ignored"},
    ]}))
    mutant_attribution = log_dir / "mutant_attribution.json"
    mutant_attribution.write_text(json.dumps({
        "test_failures": [
            {"name": "gen_a", "fault": "spec_underspecification", "error_log": "E reference printed Y", "spec_quote": ""},
            {"name": "gen_b", "fault": "test", "error_log": "ignored"},
            {"name": "gen_c", "fault": "error", "error_log": "ignored"},
        ],
        "mutants": [
            {"mutant_id": "repo_7", "fault": "spec_contradiction", "mutation": "drops build metadata"},
            {"mutant_id": "repo_8", "fault": "test"},
        ],
    }))

    records = spec_fault_records(attribution, mutant_attribution)

    assert [(r["kind"], r["evidence_source"], r.get("name") or r.get("mutant_id")) for r in records] == [
        ("reference_test", "candidate", "ref_a"),
        ("generated_test", "reference", "gen_a"),
        ("survived_mutant", "mutant", "repo_7"),
    ]
    assert records[0]["candidate_error_log"] == "E + candidate said X" and "error_log" not in records[0]
    assert records[1]["reference_error_log"] == "E reference printed Y" and "error_log" not in records[1]
    jobs = prepare_polish_jobs(attribution=attribution, task_log_dir=log_dir, task="t", mutant_attribution=mutant_attribution)
    batch = json.loads(Path(jobs[0]["attribution"]).read_text())
    assert batch["batch"]["total_spec_failures"] == 3 and batch["mutant_source"] == str(mutant_attribution)
    prompt = Path(jobs[0]["prompt"]).read_text()
    assert "`reference_error_log` quotes the reference's real output, which is the truth" in prompt
    assert "quote the CANDIDATE's output" in prompt and "`kind: \"survived_mutant\"`" in prompt
