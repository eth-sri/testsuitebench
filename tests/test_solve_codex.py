from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_solve_codex():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "agents" / "solve_codex.py"
    spec = importlib.util.spec_from_file_location("solve_codex", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_with_test_modes_have_expected_prompts():
    solve_codex = load_solve_codex()

    assert "with-test" in solve_codex.VALID_MODES
    assert "with-test-force" in solve_codex.VALID_MODES

    prompt = solve_codex.solve_prompt("with-test")
    force_prompt = solve_codex.solve_prompt("with-test-force")

    assert prompt == solve_codex.CODEX_GOAL_WITH_TEST
    assert prompt.startswith("You are given a program specification and a generated test suite")
    assert "/goal" not in prompt
    assert force_prompt == solve_codex.PROMPT_WITH_TEST
    assert force_prompt == "/goal Follow the full task in codex-goal.md. Keep working until at least 50% of the tests pass.\n"
    assert "generated test suite" in solve_codex.CODEX_GOAL_WITH_TEST
    assert "./run_generated_tests.sh" in solve_codex.CODEX_GOAL_WITH_TEST
    assert "at least 50% pass cannot be reached" in solve_codex.CODEX_GOAL_WITH_TEST
    assert ".programbench-generated-tests" in solve_codex.CODEX_GOAL_WITH_TEST
    assert "not part of the final submission" in solve_codex.CODEX_GOAL_WITH_TEST
    assert "not the final ground-truth evaluation suite" in solve_codex.CODEX_GOAL_WITH_TEST
    assert "fresh grading checkout" in solve_codex.CODEX_GOAL_WITH_TEST


def test_display_event_prints_one_compact_line_per_codex_step():
    solve_codex = load_solve_codex()
    command_event = {
        "type": "item.completed",
        "item": {
            "type": "command_execution",
            "command": "pytest -q",
            "exit_code": 1,
            "aggregated_output": "x" * 5000,
        },
    }
    agent_event = {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}
    file_event = {
        "type": "item.completed",
        "item": {"type": "file_change", "changes": [{"kind": "add", "path": "/workspace/a.c"}]},
    }
    started_event = {"type": "item.started", "item": {"type": "command_execution", "command": "pytest -q"}}
    turn_event = {"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 2}}

    assert solve_codex.display_event(json.dumps(command_event), 80) == "[command] pytest -q (exit 1)\n"
    assert solve_codex.display_event(json.dumps(agent_event), 80) == "done\n"
    assert solve_codex.display_event(json.dumps(file_event), 80) == "[file_change] add /workspace/a.c\n"
    assert solve_codex.display_event(json.dumps(turn_event), 80).startswith("[turn] input=3 cached=0 output=2")
    # Each item is reported once, on completion, and tool output is never echoed.
    assert solve_codex.display_event(json.dumps(started_event), 80) == ""
    long_message = {"type": "item.completed", "item": {"type": "agent_message", "text": "w " * 500}}
    assert len(solve_codex.display_event(json.dumps(long_message), 80)) <= solve_codex.PROGRESS_LINE_LIMIT + 4


def test_display_event_shows_the_whole_error_message():
    solve_codex = load_solve_codex()
    inner = {"type": "invalid_request_error", "message": "The 'gpt-6.1-sol' model is not supported when using Codex with a ChatGPT account. " + "x" * 200 + " Use an API key."}
    event = {"type": "error", "message": json.dumps({"type": "error", "status": 400, "error": inner})}

    line = solve_codex.display_event(json.dumps(event), 80)

    assert line.startswith("[error] The 'gpt-6.1-sol' model is not supported")
    assert line.rstrip().endswith("Use an API key.")


def test_submission_archive_is_bounded_and_partial_archive_is_removed(tmp_path):
    solve_codex = load_solve_codex()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    archive = tmp_path / "submission.tar.gz"
    (workspace / "source.txt").write_text("small source")
    (workspace / "executable").write_bytes(os.urandom(4096))

    command = solve_codex.submission_archive_command(
        ("./executable",),
        workspace=str(workspace),
        archive_path=str(archive),
        limit_bytes=20480,
    )
    result = subprocess.run(["bash", "-c", "set -euo pipefail\n" + command], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    with tarfile.open(archive, "r:gz") as packed:
        assert "./source.txt" in packed.getnames()
        assert "./executable" not in packed.getnames()

    (workspace / "large.bin").write_bytes(b"\0" * 32768)
    result = subprocess.run(["bash", "-c", "set -euo pipefail\n" + command], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Uncompressed archive must be below 20480 bytes" in result.stderr
    assert not archive.exists()

    (workspace / "large.bin").unlink()
    with (workspace / "sparse.bin").open("wb") as sparse:
        sparse.truncate(32768)
    result = subprocess.run(["bash", "-c", command], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Uncompressed archive must be below 20480 bytes" in result.stderr
    assert not archive.exists()


def test_copy_submission_logs_saved_archive(tmp_path, monkeypatch, caplog):
    solve_codex = load_solve_codex()
    submission = tmp_path / "submission.tar.gz"
    monkeypatch.setattr(
        solve_codex.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )

    with caplog.at_level(logging.INFO, logger="programbench.solve_codex"):
        solve_codex.copy_submission("container", submission)

    assert caplog.messages == [f"Saved submission to {submission}"]


def test_default_with_test_suite_archive_preserves_model_namespace():
    solve_codex = load_solve_codex()

    archive = solve_codex.default_test_suite_archive(
        "codex/gpt-5.5",
        "high",
        "abishekvashok__cmatrix.5c082c6",
    )

    assert archive == Path(
        "output/test-suites/codex/gpt-5.5-high-with-executable/"
        "abishekvashok__cmatrix.5c082c6/tests.tar.gz"
    )


def test_with_test_default_output_nests_test_suite_generator():
    solve_codex = load_solve_codex()
    task = "abishekvashok__cmatrix.5c082c6"
    suite = Path("output/test-suites/codex/gpt-5.5-high-with-executable") / task / "tests.tar.gz"
    args = SimpleNamespace(
        output="",
        mode="with-test",
        model="codex/gpt-5.5",
        reasoning="medium",
        task=task,
    )

    assert solve_codex.test_suite_output_label(suite, task) == Path("codex/gpt-5.5-high-with-executable")
    assert solve_codex.output_dir(args, suite) == Path(
        "output/executable/codex/gpt-5.5-medium-with-test/"
        "codex/gpt-5.5-high-with-executable"
    )


def test_explicit_output_does_not_add_test_suite_generator():
    solve_codex = load_solve_codex()
    task = "abishekvashok__cmatrix.5c082c6"
    suite = Path("output/test-suites/codex/gpt-5.5-high-with-executable") / task / "tests.tar.gz"
    args = SimpleNamespace(
        output="custom-out",
        mode="with-test",
        model="codex/gpt-5.5",
        reasoning="medium",
        task=task,
    )

    assert solve_codex.output_dir(args, suite) == Path("custom-out")


def test_resolve_test_suite_source_accepts_archive_or_instance_dir(tmp_path):
    solve_codex = load_solve_codex()
    archive = tmp_path / "tests.tar.gz"
    archive.write_bytes(b"archive")
    args = SimpleNamespace(mode="with-test", test_suite=str(archive), model="codex/gpt", reasoning="high", task="task")

    assert solve_codex.resolve_test_suite_source(args) == archive.resolve()

    instance_dir = tmp_path / "instance"
    instance_dir.mkdir()
    nested_archive = instance_dir / "tests.tar.gz"
    nested_archive.write_bytes(b"archive")
    args.test_suite = str(instance_dir)

    assert solve_codex.resolve_test_suite_source(args) == nested_archive.resolve()


def test_resolve_test_suite_source_accepts_unpacked_suite_or_multi_branch_dir(tmp_path):
    solve_codex = load_solve_codex()
    args = SimpleNamespace(mode="with-test", test_suite="", model="codex/gpt", reasoning="high", task="task")

    unpacked_suite = tmp_path / "single"
    (unpacked_suite / "eval").mkdir(parents=True)
    (unpacked_suite / "eval" / "run.sh").write_text("#!/usr/bin/env bash\n")
    args.test_suite = str(unpacked_suite)

    assert solve_codex.resolve_test_suite_source(args) == unpacked_suite.resolve()

    multi_branch = tmp_path / "branches"
    (multi_branch / "branch-a" / "eval").mkdir(parents=True)
    (multi_branch / "branch-a" / "eval" / "run.sh").write_text("#!/usr/bin/env bash\n")
    (multi_branch / "branch-b" / "eval").mkdir(parents=True)
    (multi_branch / "branch-b" / "eval" / "run.sh").write_text("#!/usr/bin/env bash\n")
    args.test_suite = str(multi_branch)

    assert solve_codex.resolve_test_suite_source(args) == multi_branch.resolve()


def test_resolve_test_suite_source_rejects_wrong_mode(tmp_path):
    solve_codex = load_solve_codex()
    archive = tmp_path / "tests.tar.gz"
    archive.write_bytes(b"archive")
    args = SimpleNamespace(mode="spec-only", test_suite=str(archive), model="codex/gpt", reasoning="high", task="task")

    with pytest.raises(SystemExit, match="only supported with --mode with-test or with-test-force"):
        solve_codex.resolve_test_suite_source(args)


def test_build_docker_args_mounts_test_suite(tmp_path):
    solve_codex = load_solve_codex()
    prompt = tmp_path / "prompt.txt"
    cleanroom = tmp_path / "cleanroom"
    tests = tmp_path / "tests.tar.gz"

    args = solve_codex.build_docker_args("container", prompt, cleanroom, tests)

    assert "-v" in args
    assert f"{tests}:/tmp/programbench_tests.tar.gz:ro" in args



def test_fresh_offline_build_uses_requested_image_without_network_or_codex_credentials(tmp_path, monkeypatch):
    solve_codex = load_solve_codex()
    submission = tmp_path / "submission.tar.gz"
    submission.write_bytes(b"archive")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="built\n", stderr="")

    monkeypatch.setattr(solve_codex.subprocess, "run", fake_run)

    image = "programbench/owner_1776_repo.abc1234:task_cleanroom_codex"
    ok, output = solve_codex.verify_fresh_offline_build(
        submission,
        image,
        docker_cpus=7,
        timeout=123,
    )

    assert ok is True
    assert output == "built"
    command = captured["command"]
    assert command[:2] == [solve_codex.docker(), "run"]
    assert command[command.index("--network") + 1] == "none"
    assert "OPENAI_API_KEY=" in command
    assert "CODEX_HOME=/root/.codex" in command
    assert "/root/.codex:rw,noexec,nosuid,nodev,size=1m" in command
    assert not any("auth.json" in arg for arg in command)
    assert command[command.index("--pull") + 1] == "never"
    assert command[command.index("--cpus") + 1] == "7"
    assert f"{submission.resolve()}:/tmp/programbench-submission.tar.gz:ro" in command
    assert image in command
    assert "./compile.sh" in command[-1]
    assert captured["kwargs"]["timeout"] == 123


def test_fresh_offline_build_reports_compile_failure(tmp_path, monkeypatch):
    solve_codex = load_solve_codex()
    submission = tmp_path / "submission.tar.gz"
    submission.write_bytes(b"archive")
    monkeypatch.setattr(
        solve_codex.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="compile needs a download\n",
        ),
    )

    ok, output = solve_codex.verify_fresh_offline_build(submission, "example:image")

    assert ok is False
    assert output == "compile needs a download"


def test_prepare_test_suite_archive_from_dir_keeps_only_eval_trees(tmp_path):
    solve_codex = load_solve_codex()
    source = tmp_path / "branches"
    (source / "branch-a" / "eval").mkdir(parents=True)
    (source / "branch-a" / "eval" / "run.sh").write_text("#!/usr/bin/env bash\n")
    (source / "branch-a" / "eval" / "tests.py").write_text("pass\n")
    (source / "branch-a" / "cmatrix.c").write_text("leak\n")
    (source / "branch-b" / "eval").mkdir(parents=True)
    (source / "branch-b" / "eval" / "run.sh").write_text("#!/usr/bin/env bash\n")
    (source / "branch-b" / "README.md").write_text("leak\n")

    archive = solve_codex.prepare_test_suite_archive(source, tmp_path)

    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        names = {member.name for member in members}
    assert all(member.uid == 0 and member.gid == 0 for member in members)
    assert "branch-a/eval/run.sh" in names
    assert "branch-a/eval/tests.py" in names
    assert "branch-b/eval/run.sh" in names
    assert "branch-a/cmatrix.c" not in names
    assert "branch-b/README.md" not in names


def test_prepare_test_suite_archive_from_archive_filters_non_eval_members(tmp_path):
    solve_codex = load_solve_codex()
    source_dir = tmp_path / "source"
    (source_dir / "eval").mkdir(parents=True)
    (source_dir / "eval" / "run.sh").write_text("#!/usr/bin/env bash\n")
    (source_dir / "cmatrix.c").write_text("leak\n")
    input_archive = tmp_path / "input.tar.gz"
    with tarfile.open(input_archive, "w:gz") as tar:
        tar.add(source_dir / "eval", arcname="./eval")
        tar.add(source_dir / "cmatrix.c", arcname="./cmatrix.c")

    archive = solve_codex.prepare_test_suite_archive(input_archive, tmp_path / "out")

    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        names = {member.name for member in members}
    assert all(member.uid == 0 and member.gid == 0 for member in members)
    assert "./eval/run.sh" in names
    assert "./cmatrix.c" not in names


def test_build_docker_args_mounts_only_archive(tmp_path):
    solve_codex = load_solve_codex()
    prompt = tmp_path / "prompt.txt"
    cleanroom = tmp_path / "cleanroom"
    tests = tmp_path / "sanitized-tests.tar.gz"

    args = solve_codex.build_docker_args("container", prompt, cleanroom, tests)

    assert f"{tests}:/tmp/programbench_tests.tar.gz:ro" in args
    assert not any("/tmp/programbench_tests_dir" in arg for arg in args)


def test_with_test_container_script_installs_runner_and_hides_reference_binary():
    solve_codex = load_solve_codex()

    script = solve_codex.build_container_script("with-test", "codex exec --cd /workspace", "gpt-test", "high")

    assert "mode=with-test" in script
    assert "--exclude=./executable --exclude=executable" in script
    assert "rm -f /workspace/executable" in script
    assert "tar --no-same-owner -xzf /tmp/programbench_tests.tar.gz" in script
    assert "/workspace/run_generated_tests.sh" in script
    assert "codex_goal=" not in script
    assert "printf '%s' \"$codex_goal\" > /workspace/codex-goal.md" not in script
    assert "max_test_iterations" not in script
    assert "ProgramBench Codex attempt" not in script
    assert "PROGRAMBENCH_RETRY_PROMPT" not in script
    assert "mapfile -d '' run_scripts" in script
    assert "find /workspace/.programbench-generated-tests -path '*/eval/run.sh'" in script
    assert "ln -s /workspace/executable \"$suite_dir/executable\"" in script
    assert "cd \"$suite_dir\" && EXECUTABLE=/workspace/executable bash \"$run_script\"" in script
    assert "--exclude=./.programbench-generated-tests" in script
    assert "--exclude=./run_generated_tests.sh" in script
    assert "--exclude=./codex-goal.md" in script


def test_with_test_force_container_script_writes_goal_markdown():
    solve_codex = load_solve_codex()

    script = solve_codex.build_container_script("with-test-force", "codex exec --cd /workspace", "gpt-test", "high")

    assert "mode=with-test-force" in script
    assert "tar --no-same-owner -xzf /tmp/programbench_tests.tar.gz" in script
    assert "/workspace/run_generated_tests.sh" in script
    assert "codex_goal=" in script
    assert "printf '%s' \"$codex_goal\" > /workspace/codex-goal.md" in script


@pytest.mark.parametrize(("mode",), [("spec-only",), ("with-test",), ("with-test-force",)])
def test_hidden_binary_modes_never_stash_the_reference_binary_in_tmp(mode):
    """The stash in /tmp used to be unconditional, so spec-only sessions could `ls /tmp` the binary."""
    script = load_solve_codex().build_container_script(mode, "", "codex/gpt", "high")
    assert 'rm -f "$reference_executable"' in script
    assert 'if [ "$mode" = "with-executable" ] && [ -e /workspace/executable ]; then' in script
    assert "rm -f /workspace/executable" in script
