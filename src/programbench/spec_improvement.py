# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Run Codex in Docker to clarify task specifications from generated tests."""

from __future__ import annotations

import concurrent.futures
import contextlib
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from jinja2 import Template

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from programbench.codex import build_codex_shell_command
from programbench.constants import DOCKER_CPUS, DOCKER_EXECUTABLE
from programbench.container import ContainerEnvironment
from programbench.test_generation import (
    _cleanroom_base_image,
    _write_codex_trajectory,
)
from programbench.utils.instance_filters import filter_instances
from programbench.utils.load_data import load_all_instances

log = logging.getLogger(__name__)

DEFAULT_CODEX_IMAGE = os.environ.get("PROGRAMBENCH_CODEX_IMAGE", "ghcr.io/openai/codex-universal:latest")
DEFAULT_CODEX_AUTH_FILE = os.environ.get(
    "PROGRAMBENCH_CODEX_AUTH_FILE",
    str(Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"),
)
DEFAULT_CODEX_LOG_DIR = os.environ.get("PROGRAMBENCH_CODEX_LOG_DIR", "cleanroom/editlog")
# The cleanroom images pin codex into the image, so the default runs the
# installed binary and needs no network. The npx form remains for
# ghcr.io/openai/codex-universal, which ships no codex CLI, but nothing selects
# that image unless PROGRAMBENCH_CODEX_IMAGE asks for it.
NPX_CODEX_COMMAND = (
    "npx -y @openai/codex@0.158.0 --dangerously-bypass-approvals-and-sandbox "
    "exec --cd /workspace --skip-git-repo-check"
)
DEFAULT_CODEX_COMMAND = os.environ.get(
    "PROGRAMBENCH_CODEX_COMMAND",
    "codex --dangerously-bypass-approvals-and-sandbox exec --cd /workspace --skip-git-repo-check",
)

IMPROVE_SPEC_TEMPLATE = Template("""\
You are given two directories and must clarify a task specification.

## Workspace

- `specification/`: contains the current task specification. A program and its compiled executable will be created based solely on this specification.
- `test-branches/`: contains the test suite and, when provided, `skipped_tests.json`. Treat every listed function as absent: it is excluded from evaluation and must not influence the specification.

## Task

Update the contents of `specification/` so that it provides enough information for someone to implement an executable that passes all tests in `test-branches/`, without relying on any information outside the specification.

## Workflow

1. Prepare a new file `spec.md`
2. For each tested behavior, create a section titled `## Spec ${i}`, and thoroughly explain the required behavior to the point where an executable can be created based on the document that can pass the test.

## Rules

- Make sure each section is titled `## Spec ${i}`.
- The spec may have at least {{ min_sections }} sections, and at most {{ max_sections }} sections. Effectively aggregate similar requirements into a single section.
- The spec should be an abstracted description of the expected behaviors, i.e., what will be tested. Do not simply enumerate over all test functions.
- The required artifact that will be made based on the spec is exactly `executable`. If `eval/run.sh` of the test builds another command from repository source, that command has to be harness-provided. Do not assign its behavior to executable, and write the spec as if they are simply provided and available.
- Write a self-contained specification that does not rely on information outside `specification/`.

## Output

Leave the clarified specification in `specification/spec.md`.
""", keep_trailing_newline=True)


def specification_prompt(min_sections: int = 10, max_sections: int = 100) -> str:
    if not 1 <= min_sections <= max_sections:
        raise ValueError("Section limits must satisfy 1 <= min <= max")
    return IMPROVE_SPEC_TEMPLATE.render(min_sections=min_sections, max_sections=max_sections)


@contextlib.contextmanager
def _progress_phase(instance_id: str, phase: str, *, interval: int = 60):
    """Log phase start/end and a heartbeat for long-running operations."""
    start = time.monotonic()
    log.info("%s: %s started", instance_id, phase)

    done = threading.Event()
    thread: threading.Thread | None = None

    if interval > 0:

        def heartbeat() -> None:
            while not done.wait(interval):
                log.info(
                    "%s: %s still running after %.0fs",
                    instance_id,
                    phase,
                    time.monotonic() - start,
                )

        thread = threading.Thread(target=heartbeat, name=f"spec-improve-progress-{instance_id}", daemon=True)
        thread.start()

    try:
        yield
    finally:
        done.set()
        if thread is not None:
            thread.join(timeout=1)
        log.info("%s: %s finished in %.1fs", instance_id, phase, time.monotonic() - start)


def _instance_source(root: Path, instance_id: str, *, label: str) -> Path:
    """Return the instance-specific directory under a root, with a clear error."""
    source = root / instance_id
    if not source.is_dir():
        raise RuntimeError(f"{label} directory does not exist for {instance_id}: {source}")
    return source


_SPEC_COPY_EXCLUDES = {".git", "executable", ".programbench-ground-truth"}


def _copy_specification_to_container(env: ContainerEnvironment, specification: Path) -> None:
    """Copy only specification-relevant files into the container workspace."""
    with tempfile.TemporaryDirectory(prefix="programbench-spec-") as tmp_dir:
        staged_spec = Path(tmp_dir) / "specification"
        shutil.copytree(
            specification,
            staged_spec,
            ignore=lambda _dir, names: [name for name in names if name in _SPEC_COPY_EXCLUDES],
            symlinks=True,
        )
        env.copy_in(staged_spec, "/workspace/specification")


_TEST_BRANCH_ROOT_FILE_NAMES = {"README", "README.md", "run.sh", "stdout.txt", "stderr.txt", "summary.txt"}
_TEST_BRANCH_ROOT_FILE_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml"}
_TEST_BRANCH_FIXTURE_DIRS = {"data", "fixture", "fixtures", "testdata"}


def _copy_test_branch_metadata(source_branch: Path, staged_branch: Path) -> None:
    for item in source_branch.iterdir():
        if not item.is_file():
            continue
        if item.name in _TEST_BRANCH_ROOT_FILE_NAMES or item.suffix in _TEST_BRANCH_ROOT_FILE_SUFFIXES:
            shutil.copy2(item, staged_branch / item.name)


def _copy_test_branches_to_container(env: ContainerEnvironment, test_branches: Path) -> None:
    """Copy generated eval tests without duplicated source checkouts."""
    with tempfile.TemporaryDirectory(prefix="programbench-tests-") as tmp_dir:
        staged_tests = Path(tmp_dir) / "test-branches"
        staged_tests.mkdir()
        for source_branch in sorted(test_branches.iterdir()):
            staged_branch = staged_tests / source_branch.name
            if source_branch.is_file():
                shutil.copy2(source_branch, staged_branch)
                continue

            eval_dir = source_branch / "eval"
            if eval_dir.is_dir():
                staged_branch.mkdir()
                shutil.copytree(eval_dir, staged_branch / "eval", symlinks=True)
                for fixture_name in _TEST_BRANCH_FIXTURE_DIRS:
                    fixture_dir = source_branch / fixture_name
                    if fixture_dir.is_dir():
                        shutil.copytree(fixture_dir, staged_branch / fixture_name, symlinks=True)
                _copy_test_branch_metadata(source_branch, staged_branch)
            else:
                shutil.copytree(source_branch, staged_branch, symlinks=True)

        env.copy_in(staged_tests, "/workspace/test-branches")


def _copy_dir_from_container(
    env: ContainerEnvironment,
    container_path: str,
    local_path: Path,
    *,
    excludes: list[str] | None = None,
) -> None:
    """Copy a container directory to a local path by streaming a tar archive."""
    env.copy_out_dir(container_path, local_path, excludes=excludes)


def _prepare_workspace(env: ContainerEnvironment, *, specification: Path, test_branches: Path) -> None:
    """Stage the spec and tests under the prompt's expected directory names."""
    result = env.execute("rm -rf /workspace/specification /workspace/test-branches && mkdir -p /workspace")
    if result["returncode"] != 0:
        raise RuntimeError(f"failed to initialize workspace: {result['output'].strip()}")
    _copy_specification_to_container(env, specification)
    _copy_test_branches_to_container(env, test_branches)
    result = env.execute(
        "rm -rf /workspace/specification/.git /workspace/specification/executable "
        "/workspace/specification/.programbench-ground-truth"
    )
    if result["returncode"] != 0:
        raise RuntimeError(f"failed to remove non-spec artifacts: {result['output'].strip()}")


def _codex_shell_command(
    codex_command: str,
    *,
    model: str = "",
    reasoning_effort: str = "",
    prompt: str = specification_prompt(),
) -> str:
    return build_codex_shell_command(
        codex_command,
        prompt=prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        diagnostic_action="improve a specification",
    )


def _copy_codex_auth_to_container(env: ContainerEnvironment, auth_file: Path) -> None:
    """Copy a host ChatGPT login cache into the disposable Codex container."""
    if not auth_file.is_file():
        raise RuntimeError(
            f"Codex auth cache does not exist: {auth_file}. "
            "Run `codex login` on the host or pass --codex-auth-file."
        )
    env.copy_in(auth_file, "/root/.codex/auth.json")


def _codex_completed_event(line: str) -> dict[str, Any] | None:
    """Parse one Codex JSONL line, keeping only completed events."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, dict):
        return None
    event_type = event.get("type")
    if not isinstance(event_type, str) or not event_type.endswith(".completed"):
        return None
    return event


def _codex_event_summary(event: dict[str, Any]) -> str:
    """Return a compact human-readable summary of one completed Codex event."""
    event_type = str(event.get("type", "completed"))
    item = event.get("item")
    if not isinstance(item, dict):
        return event_type

    item_type = str(item.get("type", "item"))
    detail = item.get("command") or item.get("text") or item.get("name")
    summary = f"{event_type}: {item_type}"
    if isinstance(detail, str) and detail.strip():
        compact = " ".join(detail.split())
        summary += f" - {compact[:240]}"
    if item.get("status"):
        summary += f" [{item['status']}]"
    return summary


@contextlib.contextmanager
def _stream_codex_json_log(instance_id: str, path: Path):
    """Stream Codex stdout to a host JSONL file while logging event summaries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", buffering=1) as output:
        log.info("%s: streaming completed Codex events to %s", instance_id, path)

        def callback(stream_name: str, line: str) -> None:
            if stream_name == "stdout":
                event = _codex_completed_event(line)
                if event is None:
                    return
                output.write(line)
                output.flush()
                log.info("%s: Codex %s", instance_id, _codex_event_summary(event))
            elif line.strip():
                log.debug("%s: Codex stderr: %s", instance_id, line.rstrip())

        yield callback


@contextlib.contextmanager
def _collect_codex_json_events(instance_id: str):
    """Collect Codex output and parsed events for a single trajectory file."""
    record: dict[str, Any] = {
        "stdout_lines": [],
        "stderr_lines": [],
        "json_events": [],
        "completed_events": [],
    }

    def callback(stream_name: str, line: str) -> None:
        if stream_name == "stdout":
            record["stdout_lines"].append(line)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                return
            if isinstance(event, dict):
                record["json_events"].append(event)
                completed = _codex_completed_event(line)
                if completed is not None:
                    record["completed_events"].append(completed)
                    log.info("%s: Codex %s", instance_id, _codex_event_summary(completed))
        elif stream_name == "stderr":
            record["stderr_lines"].append(line)
            if line.strip():
                log.debug("%s: Codex stderr: %s", instance_id, line.rstrip())

    log.info("%s: collecting Codex output for trajectory", instance_id)
    record["callback"] = callback
    yield record


def _specification_digest(root: Path) -> str:
    """Hash specification paths, contents, symlink targets, and permissions."""
    digest = hashlib.sha256()
    for current_root, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if name not in _SPEC_COPY_EXCLUDES)
        filenames = sorted(name for name in filenames if name not in _SPEC_COPY_EXCLUDES)
        current = Path(current_root)
        for name in [*dirnames, *filenames]:
            path = current / name
            relative = path.relative_to(root).as_posix()
            stat_result = path.lstat()
            digest.update(relative.encode())
            digest.update(f":{stat_result.st_mode & 0o7777:o}:".encode())
            if path.is_symlink():
                digest.update(b"symlink:")
                digest.update(os.readlink(path).encode())
            elif path.is_dir():
                digest.update(b"directory")
            elif path.is_file():
                digest.update(b"file:")
                with path.open("rb") as file:
                    for chunk in iter(lambda: file.read(1024 * 1024), b""):
                        digest.update(chunk)
            else:
                digest.update(b"other")
    return digest.hexdigest()


def _filter_improved_specification_output(root: Path) -> None:
    """Keep only the required semiformal specification document."""
    spec_md = root / "spec.md"
    if not spec_md.is_file():
        raise RuntimeError(f"semiformal spec improvement did not produce required spec.md: {spec_md}")

    with tempfile.TemporaryDirectory(prefix="programbench-semiformal-spec-") as tmp_dir:
        filtered_root = Path(tmp_dir) / "specification"
        filtered_root.mkdir()
        shutil.copy2(spec_md, filtered_root / "spec.md")
        shutil.rmtree(root, ignore_errors=True)
        shutil.copytree(filtered_root, root)


def _forwarded_env(names: list[str]) -> dict[str, str]:
    return {name: value for name in names if (value := os.environ.get(name))}


def improve_specification_instance(
    *,
    instance: dict[str, Any],
    testdir: Path,
    skipped_tests: Path | None = None,
    spec_in: Path,
    spec_out: Path,
    force: bool = False,
    image: str = DEFAULT_CODEX_IMAGE,
    cleanroom_base_image: str = "",
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    codex_command: str = DEFAULT_CODEX_COMMAND,
    model: str = "",
    reasoning_effort: str = "",
    timeout: int = 7200,
    codex_auth_file: Path | None = None,
    forward_env: list[str] | None = None,
    run_args: list[str] | None = None,
    codex_log_dir: str | Path = DEFAULT_CODEX_LOG_DIR,
    progress_log_interval: int = 60,
    min_num_spec_sec: int = 10,
    max_num_spec_sec: int = 100,
) -> dict[str, Any]:
    """Clarify one instance's specification and return a status record."""
    instance_id = instance["instance_id"]
    target_spec = spec_out / instance_id
    traj_path = Path(codex_log_dir) / f"{instance_id}.traj.json"
    if target_spec.exists() and not force:
        return {
            "instance_id": instance_id,
            "status": "skipped",
            "reason": "spec_out_exists",
            "spec_out": str(target_spec),
            "traj": str(traj_path) if traj_path.is_file() else None,
        }

    source_spec = _instance_source(spec_in, instance_id, label="spec_in")
    source_tests = _instance_source(testdir, instance_id, label="testdir")
    prompt = specification_prompt(min_num_spec_sec, max_num_spec_sec)
    command = _codex_shell_command(
        codex_command,
        prompt=prompt,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    env_names = forward_env or []
    env_config = {
        "CODEX_HOME": "/root/.codex",
        "NPM_CONFIG_UPDATE_NOTIFIER": "false",
        "NO_UPDATE_NOTIFIER": "1",
        **_forwarded_env(env_names),
    }

    selected_image = image or _cleanroom_base_image(instance, cleanroom_base_image)

    def save_trajectory(status: dict[str, Any], events: list[dict[str, Any]]) -> None:
        _write_codex_trajectory(
            path=traj_path,
            instance_id=instance_id,
            prompt=prompt,
            events=events,
            status=status,
            info={
                "task": "improve-spec",
                "image": selected_image,
                "model": model,
                "codex_command": codex_command,
                "codex_shell_command": command,
                "spec_in": str(source_spec),
                "testdir": str(source_tests),
                "spec_out": str(target_spec),
            },
        )

    log.info("%s: improving spec using image %s", instance_id, selected_image)
    with _progress_phase(instance_id, "start container", interval=progress_log_interval):
        env = ContainerEnvironment(
            image=selected_image,
            cwd="/workspace",
            executable=docker_executable,
            timeout=timeout,
            cpus=docker_cpus,
            env=env_config,
            run_args=run_args,
        )
    try:
        if codex_auth_file is not None:
            with _progress_phase(instance_id, "install Codex account auth", interval=progress_log_interval):
                _copy_codex_auth_to_container(env, codex_auth_file)

        with _progress_phase(instance_id, "prepare workspace", interval=progress_log_interval):
            _prepare_workspace(env, specification=source_spec, test_branches=source_tests)
            if skipped_tests is not None:
                from programbench.skipped_tests import skipped_tests_path

                env.copy_in(
                    skipped_tests_path(skipped_tests, instance_id),
                    "/workspace/test-branches/skipped_tests.json",
                )
        with _progress_phase(instance_id, "run Codex", interval=progress_log_interval):
            with _collect_codex_json_events(instance_id) as codex_output:
                result = env.execute(command, timeout=timeout, output_callback=codex_output["callback"])
        raw_stdout = result.get("stdout") or "".join(codex_output["stdout_lines"])
        raw_stderr = result.get("stderr") or "".join(codex_output["stderr_lines"])
        result = {
            **result,
            "stdout": raw_stdout,
            "stderr": raw_stderr,
            "output": result.get("output") or raw_stdout + raw_stderr,
        }
        events = list(codex_output["completed_events"])
        json_events = list(codex_output["json_events"])
        status = {
            "instance_id": instance_id,
            "status": "ok" if result.get("returncode") == 0 else "codex_failed",
            "returncode": result.get("returncode"),
            "exception_info": result.get("exception_info", ""),
            "image": selected_image,
            "codex_command": codex_command,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "codex_json_events": json_events,
        }
        if result.get("returncode") != 0:
            status["output"] = result.get("output", "")
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status

        candidate_spec = target_spec.with_name(f".{target_spec.name}.candidate-{os.getpid()}-{time.time_ns()}")
        try:
            with _progress_phase(instance_id, "copy improved specification", interval=progress_log_interval):
                _copy_dir_from_container(env, "/workspace/specification", candidate_spec)
                _filter_improved_specification_output(candidate_spec)
            if _specification_digest(candidate_spec) == _specification_digest(source_spec):
                status.update(
                    status="no_changes",
                    reason=(
                        "Codex exited successfully but did not modify the specification; "
                        "verify --codex-command runs `codex exec`"
                    ),
                    output=result.get("output", ""),
                )
                save_trajectory(status, events)
                status["traj"] = str(traj_path)
                log.warning("%s: Codex completed without changing the specification", instance_id)
                return status

            shutil.rmtree(target_spec, ignore_errors=True)
            candidate_spec.replace(target_spec)
        finally:
            shutil.rmtree(candidate_spec, ignore_errors=True)

        status["spec_out"] = str(target_spec)
        save_trajectory(status, events)
        status["traj"] = str(traj_path)
        log.info("%s: spec improvement completed successfully", instance_id)
        return status
    finally:
        env.cleanup()


def run_spec_improvement_batch(
    *,
    testdir: str | Path = "extracted-tests",
    skipped_tests: str | Path = "",
    spec_in: str | Path = "cleanroom/original",
    output: str | Path = "cleanroom/semiformal",
    filter_spec: str = "",
    slice_spec: str = "",
    workers: int = 1,
    force: bool = False,
    image: str = DEFAULT_CODEX_IMAGE,
    cleanroom_base_image: str = "",
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    codex_command: str = DEFAULT_CODEX_COMMAND,
    model: str = "",
    reasoning_effort: str = "",
    timeout: int = 7200,
    codex_auth_file: str | Path = DEFAULT_CODEX_AUTH_FILE,
    codex_log_dir: str | Path = DEFAULT_CODEX_LOG_DIR,
    forward_env: list[str] | None = None,
    run_args: list[str] | None = None,
    progress_log_interval: int = 60,
    min_num_spec_sec: int = 10,
    max_num_spec_sec: int = 100,
) -> list[dict[str, Any]]:
    """Improve selected specifications with Codex in Docker."""
    specification_prompt(min_num_spec_sec, max_num_spec_sec)
    spec_out_path = Path(output)
    spec_out_path.mkdir(parents=True, exist_ok=True)

    instances = load_all_instances(include_tests=False)
    instances = filter_instances(instances, filter_spec=filter_spec, slice_spec=slice_spec)
    if not instances:
        log.warning("No instances selected for spec improvement.")
        return []

    log.info("Improving specifications for %d instance(s)", len(instances))
    results: list[dict[str, Any]] = []
    with (
        logging_redirect_tqdm(),
        concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        futures = {
            executor.submit(
                improve_specification_instance,
                instance=instance,
                testdir=Path(testdir),
                min_num_spec_sec=min_num_spec_sec,
                max_num_spec_sec=max_num_spec_sec,
                skipped_tests=Path(skipped_tests) if skipped_tests else None,
                spec_in=Path(spec_in),
                spec_out=spec_out_path,
                force=force,
                image=image,
                cleanroom_base_image=cleanroom_base_image,
                docker_executable=docker_executable,
                docker_cpus=docker_cpus,
                codex_command=codex_command,
                model=model,
                reasoning_effort=reasoning_effort,
                timeout=timeout,
                codex_auth_file=Path(codex_auth_file).expanduser() if codex_auth_file else None,
                codex_log_dir=Path(codex_log_dir),
                forward_env=forward_env,
                run_args=run_args,
                progress_log_interval=progress_log_interval,
            ): instance["instance_id"]
            for instance in instances
        }
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Improving specs",
            ncols=100,
            leave=False,
            disable=None,
        ):
            instance_id = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                log.error("Error improving spec for %s: %s", instance_id, e, exc_info=True)
                results.append({"instance_id": instance_id, "status": type(e).__name__, "error": str(e)})

    return sorted(results, key=lambda r: r["instance_id"])


