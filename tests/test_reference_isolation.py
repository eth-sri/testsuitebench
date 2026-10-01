from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from programbench.reference_isolation import reference_cleanup_command, stage_cleanroom
from programbench.test_generation import _prepare_codex_test_generation_workspace


def load_runner(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / "agents" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def remap(script, root):
    return script.replace("/tmp/", str(root / "tmp") + "/").replace("/workspace", str(root / "workspace"))


def run_setup(script, root):
    return subprocess.run(["bash", "-euc", remap(script, root)], cwd=root / "workspace", capture_output=True, text=True)


def seed_references(root):
    paths = [
        "workspace/executable", "workspace/executable_cov", "workspace/executable_nocov",
        "workspace/.programbench-ground-truth", "workspace/.programbench-ground-truth-executable",
        "workspace/.programbench-mutant-executable", "workspace/.git/objects/reference",
        "tmp/programbench_reference_executable", "tmp/programbench_reference_executable.bak",
        "tmp/_inject_exe/executable", "tmp/programbench-executable-under-test",
    ]
    for name in paths:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("REFERENCE ANSWER")
        p.chmod(0o111)
    return [root / name for name in paths]


@pytest.mark.parametrize("runner", ["solve_codex", "solve_claude"])
@pytest.mark.parametrize("mode", ["spec-only", "with-test", "with-test-force"])
@pytest.mark.parametrize("mounted_cleanroom", [False, True])
def test_solve_removes_all_reference_copies_before_agent(tmp_path, runner, mode, mounted_cleanroom):
    refs = seed_references(tmp_path)
    if mounted_cleanroom:
        source = tmp_path / "tmp/programbench_cleanroom"
        source.mkdir()
        (source / "spec.md").write_text("SPEC")
    else:
        (tmp_path / "workspace/spec.md").write_text("SPEC")
    script = load_runner(runner).build_container_script(mode, "unused-agent", "model", "high")
    setup = script.split("# Reference isolation complete.", 1)[0]
    result = run_setup(setup, tmp_path)
    assert result.returncode == 0, result.stderr
    assert all(not path.exists() for path in refs)
    assert (tmp_path / "workspace/spec.md").read_text() == "SPEC"


@pytest.mark.parametrize("runner", ["solve_codex", "solve_claude"])
@pytest.mark.parametrize("mounted_cleanroom", [False, True])
def test_solve_explicit_binary_mode_preserves_reference(tmp_path, runner, mounted_cleanroom):
    seed_references(tmp_path)
    (tmp_path / "workspace/executable").chmod(0o755)
    if mounted_cleanroom:
        source = tmp_path / "tmp/programbench_cleanroom"
        source.mkdir()
        (source / "spec.md").write_text("SPEC")
    script = load_runner(runner).build_container_script("with-executable", "unused-agent", "model", "high")
    result = run_setup(script.split("# Reference isolation complete.", 1)[0], tmp_path)
    assert result.returncode == 0, result.stderr
    p = tmp_path / "workspace/executable"
    p.chmod(0o755)
    assert p.read_text() == "REFERENCE ANSWER"


def test_staging_removes_references_history_and_aliases_without_changing_input(tmp_path):
    source = tmp_path / "original"
    source.mkdir()
    (source / "spec.md").write_text("SPEC")
    binary = source / "executable"
    binary.write_bytes(b"REFERENCE")
    binary.chmod(0o111)
    (source / ".git").mkdir()
    (source / ".git/answer").write_text("REFERENCE")
    (source / "executable_cov").write_text("REFERENCE")
    (source / "programbench_reference_executable.bak").write_text("REFERENCE")
    os.link(binary, source / "renamed-answer")
    (source / "answer-link").symlink_to("executable")
    (source / "outside").symlink_to("/tmp/programbench_reference_executable")
    (source / "history-link").symlink_to(".git")
    (source / "spec-link").symlink_to("spec.md")
    dest = stage_cleanroom(source, tmp_path / "staged")
    assert sorted(p.name for p in dest.iterdir()) == ["spec-link", "spec.md"]
    assert (dest / "spec-link").read_text() == "SPEC"
    assert binary.stat().st_mode & 0o777 == 0o111
    assert (source / ".git/answer").exists()


def test_explicit_staging_keeps_execute_only_binary(tmp_path):
    source = tmp_path / "original"
    source.mkdir()
    binary = source / "executable"
    binary.write_bytes(b"REFERENCE")
    binary.chmod(0o111)
    dest = stage_cleanroom(source, tmp_path / "staged", with_executable=True)
    assert binary.stat().st_mode & 0o777 == 0o111
    assert (dest / "executable").stat().st_mode & 0o777 == 0o111
    (dest / "executable").chmod(0o755)
    assert (dest / "executable").read_bytes() == b"REFERENCE"


@pytest.mark.parametrize("with_executable", [False, True])
def test_external_testgen_cleans_stale_references_unless_explicit(tmp_path, with_executable):
    refs = seed_references(tmp_path)
    # An explicitly mounted reference has readable permissions.
    (tmp_path / "tmp/programbench_reference_executable").chmod(0o755)
    source = tmp_path / "tmp/programbench_cleanroom"
    source.mkdir()
    (source / "spec.md").write_text("SPEC")
    script = load_runner("generate_tests_claude").build_container_script(
        "unused-agent", "", "", with_executable=with_executable
    )
    setup = script.split("prompt=$(cat", 1)[0].split("/usr/bin/python3", 1)[0]
    result = run_setup(setup, tmp_path)
    assert result.returncode == 0, result.stderr
    if with_executable:
        assert (tmp_path / "workspace/executable").read_text() == "REFERENCE ANSWER"
    else:
        assert all(not path.exists() for path in refs)


@pytest.mark.parametrize("with_cleanroom", [False, True])
@pytest.mark.parametrize("with_executable", [False, True])
def test_native_testgen_cleanup_runs_even_with_local_cleanroom(tmp_path, with_cleanroom, with_executable):
    refs = seed_references(tmp_path)
    source = None
    if with_cleanroom:
        source = tmp_path / "input"
        source.mkdir()
        (source / "spec.md").write_text("SPEC")
        (source / "executable").write_text("REFERENCE ANSWER")

    class Env:
        def execute(self, command):
            # Python toolchain setup is unrelated and would target host paths.
            if "python_bin=" in command:
                return {"returncode": 0, "output": ""}
            result = run_setup(command, tmp_path)
            return {"returncode": result.returncode, "output": result.stderr}

        def copy_in(self, local_path, container_path):
            shutil.copytree(local_path, tmp_path / "workspace", dirs_exist_ok=True)

    _prepare_codex_test_generation_workspace(Env(), cleanroom=source, with_executable=with_executable)
    if with_executable:
        assert (tmp_path / "workspace/executable").exists()
    else:
        assert all(not path.exists() for path in refs)


def test_cleanup_fails_closed_when_reference_cannot_be_removed(tmp_path):
    seed_references(tmp_path)
    # Simulate an undeletable bind mount: rm returns successfully without
    # removing anything. The postcondition must still prevent agent startup.
    result = run_setup("rm() { :; }\n" + reference_cleanup_command() + "\ntouch agent-started", tmp_path)
    assert result.returncode != 0
    assert "Reference isolation failed" in result.stderr
    assert not (tmp_path / "workspace/agent-started").exists()


def test_codex_requires_explicit_opt_in_for_binary_mode():
    assert load_runner("solve_codex").DEFAULT_MODE == "spec-only"


def test_binary_staging_removes_aliases_and_makes_readable_input_execute_only(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    binary = source / 'executable'
    binary.write_bytes(b'ELF placeholder')
    binary.chmod(0o755)
    os.link(binary, source / 'copy')
    (source / 'link').symlink_to('executable')
    (source / 'nested').mkdir()
    (source / 'nested/executable').write_bytes(b'other reference')
    dest = stage_cleanroom(source, tmp_path / 'dest', with_executable=True)
    assert (dest / 'executable').stat().st_mode & 0o777 == 0o111
    assert binary.stat().st_mode & 0o777 == 0o755
    assert not (dest / 'copy').exists()
    assert not (dest / 'link').exists()
    assert not (dest / 'nested/executable').exists()


@pytest.mark.parametrize('dict_actions', [False, True])
def test_native_reference_guard_wraps_every_subsequent_command(dict_actions):
    from programbench.test_generation import _protect_generation_reference

    class Env:
        def __init__(self):
            self.commands = []

        def execute(self, command, **kwargs):
            self.commands.append(command)
            return {'returncode': 0, 'output': ''}

    env = Env()
    _protect_generation_reference(env, dict_actions=dict_actions)
    for command in ('agent', './eval/run.sh'):
        env.execute({'command': command} if dict_actions else command)
    assert len(env.commands) == 3
    for action in env.commands[1:]:
        command = action['command'] if dict_actions else action
        assert command.startswith('/usr/bin/setpriv --reuid=61000')
        assert '--bounding-set=-all' in command
        assert '--no-new-privs' in command


def test_native_reference_guard_failure_prevents_startup():
    from programbench.test_generation import _protect_generation_reference

    class Env:
        def execute(self, command):
            return {'returncode': 1, 'output': 'unsafe mount'}

    with pytest.raises(RuntimeError, match='Failed to protect reference binary'):
        _protect_generation_reference(Env())
