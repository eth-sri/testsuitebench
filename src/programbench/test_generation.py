# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Run an agent to generate ProgramBench-compatible test suites."""

from __future__ import annotations

import concurrent.futures
import copy
import json
import logging
import os
import shlex
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import traceback
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from programbench.archive_limits import bounded_archive_command
from programbench.codex import (
    build_codex_shell_command,
    codex_usage_records_from_events,
    sum_codex_usage,
)
from programbench.constants import DOCKER_CPUS, DOCKER_EXECUTABLE, MAX_JUNIT_XML_BYTES, agent_network_args
from programbench.container import ContainerEnvironment
from programbench.reference_isolation import (
    reference_cleanup_command, stage_cleanroom, reference_guard_setup, reference_agent_command,
)
from programbench.utils.instance_filters import filter_instances
from programbench.utils.load_data import load_all_instances

log = logging.getLogger(__name__)

_IMAGE_TAG = "task_cleanroom"

_HIDE_EXECUTABLE_COMMAND = reference_cleanup_command() + "\n" + (
    "rm -f ./executable && "
    "test ! -e ./executable && "
    "printf 'ProgramBench test-generation mode: ./executable is hidden; use documentation only.\\n' "
    "> ./README.programbench-test-generation.txt"
)

_WORKSPACE_BIN_DIR = "/workspace/.programbench-bin"
_WORKSPACE_PATH = f"{_WORKSPACE_BIN_DIR}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

_ENSURE_WORKSPACE_PYTHON_COMMAND = f"""
set -eu
mkdir -p {_WORKSPACE_BIN_DIR}
if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-minimal
    fi
fi
python_bin="$(command -v python3 || command -v python || true)"
if [ -z "$python_bin" ]; then
    printf 'ProgramBench could not make python/python3 available in /workspace.\\n' >&2
    exit 1
fi
ln -sf "$python_bin" {_WORKSPACE_BIN_DIR}/python3
ln -sf "$python_bin" {_WORKSPACE_BIN_DIR}/python
python --version >/dev/null
python3 --version >/dev/null
""".strip()

_PROGRAMBENCH_STREAM_ENVIRONMENT_CLASS = "programbench.test_generation.StreamSeparatedDockerEnvironment"
_SOFT_WARNING_STEP_THRESHOLD = 20
_SOFT_WARNING_TIME_THRESHOLD_SECONDS = 600
_SOFT_WARNING_MESSAGE = (
    "You are running low on the allotted generation budget. Wrap up now: finish the generated "
    "test suite under ./eval, make sure ./eval/run.sh is executable and always writes "
    "./eval/results.xml, sanity-check it if possible, then submit with "
    "`echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`."
)

_STREAM_SEPARATED_OBSERVATION_TEMPLATE = """{% if output.exception_info %}<exception>{{output.exception_info}}</exception>
{% endif %}<returncode>{{output.returncode}}</returncode>
{% if output.stdout is defined or output.stderr is defined %}<stdout>
{{output.stdout | default('')}}</stdout>
<stderr>
{{output.stderr | default('')}}</stderr>{% else %}<output>
{{output.output}}</output>{% endif %}"""

DEFAULT_TEST_CODEX_LOG_DIR = os.environ.get("PROGRAMBENCH_TEST_CODEX_LOG_DIR", "output/test-suites/editlog")


class GenerationPromptMode(str, Enum):
    SPEC_ONLY = "spec-only"
    SPEC_AND_BINARY = "spec-and-binary"


TEST_GENERATION_GOAL_COMMAND = (
    "/goal Follow the full task in codex-goal.md. Keep working until you have created "
    "a comprehensive test suite under /workspace/eval that fully covers the given specification."
)


_CODEX_TEST_GENERATION_SPEC_ONLY = """\
You are creating a test suite.

## Workspace

The workspace contains a program specification.

## Task

Create a comprehensive test suite under `/workspace/eval`.

## Evaluation Design

- The test suite will go through mutation testing. It will be evaluated against fresh workspaces containing the program under test at `/workspace/executable`.
- The specification is available only while authoring the suite.
- Tests must invoke `/workspace/executable`, or compute it robustly relative to `eval`.
- Do not hard-code `./executable` inside tests that run after `run.sh` has changed into `/workspace/eval`.

## Rules

- Cover documented functional behavior thoroughly. The test suite must kill any mutants that go against the spec, while it has to pass any implementation as long as it follows the spec.
- Pay particular attention to explicitly numbered or sectioned requirements in the specification. Cover each documented behavior with at least one meaningful test.
- When creating tests, please break them down into smaller, focused tests rather than writing one huge test function; tests that kill the ground truth are not used when calculating the mutation score.

## Output

- `/workspace/eval/run.sh` must exist and be executable.
- `/workspace/eval/run.sh` must always write valid JUnit XML to `/workspace/eval/results.xml`.
- `/workspace/eval/run.sh` must run the whole generated suite, even after individual test failures.
- The report must have a `<testsuites>` root containing `<testsuite>` elements (or a single `<testsuite>` root) and one named `<testcase>` per test. Represent non-passing outcomes with a nested `<failure>`, `<error>`, or `<skipped>` element.
- For pytest suites, this is achieved simply by running `pytest --junitxml=results.xml` from `/workspace/eval`.
- JUnit XML must escape XML metacharacters and must not contain raw control characters or binary stdout/stderr; encode such output with `repr`, base64, or another XML-safe textual representation.
- When performing parametrized testing, always provide short, descriptive `ids=` values. Never allow large strings, bytes, or object representations to become test IDs.
- Put all helper files, fixtures, scripts, and generated test assets under `/workspace/eval`.
"""

_CODEX_TEST_GENERATION_SPEC_AND_BINARY = """\
You are creating a test suite.

## Workspace

The workspace contains a program specification and a reference executable at `/workspace/executable`.

## Task

Create a comprehensive test suite under `/workspace/eval`.

## Evaluation Design

- The test suite will go through mutation testing. It will be evaluated against fresh workspaces containing the program under test at `/workspace/executable`.
- The specification is available only while authoring the suite.
- Tests must invoke `/workspace/executable`, or compute it robustly relative to `eval`.
- Do not hard-code `./executable` inside tests that run after `run.sh` has changed into `/workspace/eval`.

## Rules

- Cover documented functional behavior thoroughly. The test suite must kill any mutants that go against the spec, while it has to pass any implementation as long as it follows the spec.
- Pay particular attention to explicitly numbered or sectioned requirements in the specification. Cover each documented behavior with at least one meaningful test.
- When creating tests, please break them down into smaller, focused tests rather than writing one huge test function; tests that kill the ground truth are not used when calculating the mutation score.
- Use the reference executable to resolve ambiguous or incomplete details, then write tests that follow its observed behavior. After constructing the test, evaluate it against provided executable to make sure that it accepts ground truth executable.

## Output

- `/workspace/eval/run.sh` must exist and be executable.
- `/workspace/eval/run.sh` must always write valid JUnit XML to `/workspace/eval/results.xml`.
- `/workspace/eval/run.sh` must run the whole generated suite, even after individual test failures.
- The report must have a `<testsuites>` root containing `<testsuite>` elements (or a single `<testsuite>` root) and one named `<testcase>` per test. Represent non-passing outcomes with a nested `<failure>`, `<error>`, or `<skipped>` element.
- For pytest suites, this is achieved simply by running `pytest --junitxml=results.xml` from `/workspace/eval`.
- JUnit XML must escape XML metacharacters and must not contain raw control characters or binary stdout/stderr; encode such output with `repr`, base64, or another XML-safe textual representation.
- When performing parametrized testing, always provide short, descriptive `ids=` values. Never allow large strings, bytes, or object representations to become test IDs.
- Put all helper files, fixtures, scripts, and generated test assets under `/workspace/eval`.
"""


def build_agent_templates(
    mode: GenerationPromptMode = GenerationPromptMode.SPEC_ONLY,
) -> tuple[str, str]:
    prompt = (
        _CODEX_TEST_GENERATION_SPEC_AND_BINARY
        if mode == GenerationPromptMode.SPEC_AND_BINARY
        else _CODEX_TEST_GENERATION_SPEC_ONLY
    )
    return "", prompt


def _build_agent_templates(*, with_executable: bool = False) -> tuple[str, str]:
    mode = GenerationPromptMode.SPEC_AND_BINARY if with_executable else GenerationPromptMode.SPEC_ONLY
    return build_agent_templates(mode=mode)


def _decode_process_stream(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _ensure_workspace_path(env_config: dict) -> None:
    """Prefer ProgramBench-provided workspace tools without overriding caller PATH."""
    env_vars = env_config.setdefault("env", {})
    env_vars.setdefault("PATH", _WORKSPACE_PATH)


def _normalize_agent_config(agent_config: dict) -> dict:
    """Handle legacy mini-swe-agent config aliases before AgentConfig validation."""
    agent_config = dict(agent_config)
    time_limit = agent_config.pop("time_limit", None)
    if time_limit is not None and "wall_time_limit_seconds" not in agent_config:
        agent_config["wall_time_limit_seconds"] = time_limit
    return agent_config


class SoftWarningAgentMixin:
    """Inject a one-time wrap-up warning before the hard agent limits are hit."""

    def __init__(
        self,
        *args,
        soft_warning_step_threshold: int = _SOFT_WARNING_STEP_THRESHOLD,
        soft_warning_time_threshold_seconds: int = _SOFT_WARNING_TIME_THRESHOLD_SECONDS,
        **kwargs,
    ):
        self.soft_warning_step_threshold = soft_warning_step_threshold
        self.soft_warning_time_threshold_seconds = soft_warning_time_threshold_seconds
        self._soft_step_warning_sent = False
        self._soft_time_warning_sent = False
        super().__init__(*args, **kwargs)

    def _remaining_steps(self) -> int | None:
        step_limit = getattr(self.config, "step_limit", 0)
        if step_limit <= 0:
            return None
        return step_limit - self.n_calls

    def _remaining_seconds(self) -> int | None:
        wall_time_limit = getattr(self.config, "wall_time_limit_seconds", 0)
        if wall_time_limit <= 0:
            return None
        return wall_time_limit - int(time.time() - self._start_time)

    def _maybe_add_soft_warning(self) -> None:
        remaining_steps = self._remaining_steps()
        if (
            remaining_steps is not None
            and remaining_steps <= self.soft_warning_step_threshold
            and not self._soft_step_warning_sent
        ):
            self._soft_step_warning_sent = True
            self.add_messages(self.model.format_message(role="user", content=_SOFT_WARNING_MESSAGE))

        remaining_seconds = self._remaining_seconds()
        if (
            remaining_seconds is not None
            and remaining_seconds <= self.soft_warning_time_threshold_seconds
            and not self._soft_time_warning_sent
        ):
            self._soft_time_warning_sent = True
            if not self._soft_step_warning_sent:
                self.add_messages(self.model.format_message(role="user", content=_SOFT_WARNING_MESSAGE))

    def query(self) -> dict:
        self._maybe_add_soft_warning()
        return super().query()


def _soft_warning_agent_class(base_agent_class: type) -> type:
    """Create a ProgramBenchAgent subclass without importing mini-swe-agent at module import time."""

    class SoftWarningProgramBenchAgent(SoftWarningAgentMixin, base_agent_class):
        pass

    return SoftWarningProgramBenchAgent


def _task_cleanroom_image(instance: dict) -> str:
    return f"{instance['image_name']}:{_IMAGE_TAG}"


def _cleanroom_base_image(instance: dict, cleanroom_base_image: str = "") -> str:
    return cleanroom_base_image or _task_cleanroom_image(instance)


class StreamSeparatedDockerEnvironment:
    """mini-swe-agent Docker environment that preserves stdout and stderr."""

    def __init__(self, *args, **kwargs):
        from minisweagent.environments.docker import DockerEnvironment

        self._env = DockerEnvironment(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._env, name)

    def execute(self, action: dict, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        command = action.get("command", "")
        cwd = cwd or self._env.config.cwd
        assert self._env.container_id, "Container not started"

        cmd = [self._env.config.executable, "exec", "-w", cwd]
        for key in self._env.config.forward_env:
            if (value := os.getenv(key)) is not None:
                cmd.extend(["-e", f"{key}={value}"])
        for key, value in self._env.config.env.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend([self._env.container_id, *self._env.config.interpreter, command])

        try:
            result = subprocess.run(
                cmd,
                text=True,
                timeout=timeout or self._env.config.timeout,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output = {
                "output": result.stdout + result.stderr,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "exception_info": "",
            }
            check_output = {**output, "output": result.stdout}
        except Exception as e:
            stdout = _decode_process_stream(getattr(e, "stdout", None) or getattr(e, "output", None))
            stderr = _decode_process_stream(getattr(e, "stderr", None))
            output = {
                "output": stdout + stderr,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": -1,
                "exception_info": f"An error occurred while executing the command: {e}",
                "extra": {"exception_type": type(e).__name__, "exception": str(e)},
            }
            check_output = output
        self._env._check_finished(check_output)
        return output

    def cleanup(self):
        env = getattr(self, "_env", None)
        cleanup = getattr(env, "cleanup", None)
        if cleanup is not None:
            return cleanup()
        return None

    def __del__(self):
        self.cleanup()


@contextmanager
def _temporarily_make_tar_readable(src: Path):
    """Temporarily add owner-read on regular files that host tar cannot read."""
    restored_modes: list[tuple[Path, int]] = []
    try:
        for path in src.rglob("*"):
            try:
                path_stat = path.stat(follow_symlinks=False)
            except OSError:
                continue
            if not stat.S_ISREG(path_stat.st_mode):
                continue
            if os.access(path, os.R_OK):
                continue
            restored_modes.append((path, stat.S_IMODE(path_stat.st_mode)))
            path.chmod(stat.S_IMODE(path_stat.st_mode) | stat.S_IRUSR)
        yield restored_modes
    finally:
        for path, mode in reversed(restored_modes):
            path.chmod(mode)


def _hide_executable(env) -> None:
    """Remove the ground-truth executable from the generation workspace."""
    result = env.execute({"command": _HIDE_EXECUTABLE_COMMAND})
    if result.get("returncode") != 0:
        output = result.get("output", "").strip()
        raise RuntimeError(f"Failed to hide ./executable before test generation: {output}")


def _ensure_workspace_python(env) -> None:
    """Expose python and python3 through /workspace/.programbench-bin."""
    result = env.execute({"command": _ENSURE_WORKSPACE_PYTHON_COMMAND})
    if result.get("returncode") != 0:
        output = result.get("output", "").strip()
        raise RuntimeError(f"Failed to make python/python3 available in /workspace: {output}")


def _copy_cleanroom(env, src: Path, *, dest: str = "/workspace") -> None:
    """Copy a local cleanroom directory into a mini-swe-agent Docker environment."""
    container_id = getattr(env, "container_id", None)
    executable = getattr(getattr(env, "config", None), "executable", None)
    if not container_id or not executable:
        raise RuntimeError("copy_cleanroom requires a Docker environment with container_id")
    if not src.is_dir():
        raise RuntimeError(f"Local cleanroom directory does not exist: {src}")
    env.execute({"command": f"mkdir -p {dest} && find {dest} -mindepth 1 -maxdepth 1 -exec rm -rf {{}} +"})
    with _temporarily_make_tar_readable(src) as restored_modes:
        tar_proc = subprocess.Popen(
            ["tar", "-C", str(src), "-cf", "-", "."],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert tar_proc.stdout is not None
        docker_proc = subprocess.run(
            [executable, "exec", "-i", container_id, "tar", "--no-same-owner", "-xf", "-", "-C", dest],
            stdin=tar_proc.stdout,
            capture_output=True,
            text=False,
        )
        tar_proc.stdout.close()
        tar_stderr = tar_proc.stderr.read().decode(errors="replace") if tar_proc.stderr else ""
        tar_returncode = tar_proc.wait()
    if tar_returncode != 0:
        raise RuntimeError(f"tar cleanroom stream failed: {tar_stderr.strip()}")
    if docker_proc.returncode != 0:
        stderr = docker_proc.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"docker exec tar failed: {stderr}")
    for path, mode in restored_modes:
        rel_path = path.relative_to(src)
        chmod = f"chmod {mode:04o} {shlex.quote(str(Path(dest) / rel_path))}"
        result = env.execute({"command": chmod})
        if result.get("returncode") != 0:
            output = result.get("output", "").strip()
            raise RuntimeError(f"Failed to restore cleanroom mode for {rel_path}: {output}")


def _container_executable(env) -> str | None:
    return getattr(env, "executable", None) or getattr(getattr(env, "config", None), "executable", None)


ARCHIVE_EXCLUDED_DIRS = (".tmp", "tmp", ".pytest-tmp", ".pytest_tmp", ".pytest_cache", "__pycache__")


def _protect_generation_reference(env, *, dict_actions: bool = False) -> None:
    """After trusted setup, demote every agent and postflight command."""
    execute = env.execute
    setup = reference_guard_setup()
    result = execute({"command": setup} if dict_actions else setup)
    if result.get("returncode") != 0:
        raise RuntimeError("Failed to protect reference binary: " + result.get("output", ""))

    def protected_execute(action, *args, **kwargs):
        if isinstance(action, dict):
            action = {**action, "command": reference_agent_command(action.get("command", ""))}
        else:
            action = reference_agent_command(action)
        return execute(action, *args, **kwargs)

    env.execute = protected_execute


def _container_execute(env, command: str) -> dict[str, Any]:
    if isinstance(env, ContainerEnvironment):
        return env.execute(command)
    return env.execute({"command": command})


def _extract_test_suite(archive: Path) -> Path:
    """Refresh the human-readable ``tests_untar`` sibling of an archive."""
    extract_dir = archive.parent / "tests_untar"
    staging_dir = Path(tempfile.mkdtemp(prefix=".tests_untar-", dir=archive.parent))
    staged_contents = staging_dir / "contents"
    staged_contents.mkdir()

    try:
        with tarfile.open(archive, "r:gz") as generated_tests:
            generated_tests.extractall(staged_contents, filter="data")
        shutil.rmtree(extract_dir, ignore_errors=True)
        staged_contents.replace(extract_dir)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    return extract_dir


def _copy_test_suite(env, dest: Path, *, src: str = "/workspace") -> None:
    """Run, validate, then tar+gzip ``eval`` from a Docker environment."""
    container_id = getattr(env, "container_id", None)
    executable = _container_executable(env)
    if not container_id or not executable:
        raise RuntimeError("copy_test_suite requires a Docker environment with container_id")
    dest.parent.mkdir(parents=True, exist_ok=True)
    container_tar = "/tmp/_programbench_tests.tar.gz"
    eval_dir = f"{src}/eval"
    quoted_eval_dir = shlex.quote(eval_dir)
    check = _container_execute(env, f"test -x {shlex.quote(f'{eval_dir}/run.sh')}")
    if check.get("returncode") != 0:
        raise RuntimeError(f"Generated test suite is missing executable {eval_dir}/run.sh")

    # Never accept an XML file left behind by the generating agent. Exercise
    # the packaged entry point and validate the fresh result before archiving.
    run = _container_execute(env, f"cd {quoted_eval_dir} && rm -f results.xml && ./run.sh")
    results_path = f"{eval_dir}/results.xml"
    validation_script = (
        "import pathlib, xml.etree.ElementTree as ET; "
        f"path = pathlib.Path({results_path!r}); "
        f"assert path.stat().st_size <= {MAX_JUNIT_XML_BYTES}, "
        f"f'JUnit XML is {{path.stat().st_size}} bytes; limit is {MAX_JUNIT_XML_BYTES} bytes'; "
        "root = ET.parse(path).getroot(); "
        "root_tag = root.tag.rsplit('}', 1)[-1]; "
        "assert root_tag in {'testsuite', 'testsuites'}, f'not JUnit XML: {root_tag}'; "
        "count = sum(1 for element in root.iter() "
        "if element.tag.rsplit('}', 1)[-1] == 'testcase'); "
        "print(count)"
    )
    validation = _container_execute(env, f"python3 -c {shlex.quote(validation_script)}")
    if validation.get("returncode") != 0:
        run_output = str(run.get("output") or run.get("stderr") or "").strip()
        validation_output = str(
            validation.get("output") or validation.get("stderr") or ""
        ).strip()
        details = "; ".join(
            detail for detail in (
                f"run.sh return code {run.get('returncode')}",
                f"run output: {run_output[-2000:]}" if run_output else "",
                f"validation output: {validation_output[-2000:]}" if validation_output else "",
            ) if detail
        )
        raise RuntimeError(f"Generated test suite did not write valid JUnit XML ({details})")

    # pytest's tmp factory leaves absolute ``…current`` symlinks and scratch dirs
    # inside eval/; tarfile's ``data`` filter rejects them on extraction.
    _container_execute(env, f"cd {quoted_eval_dir} && find . -type l -lname '/*' -delete")
    result = _container_execute(
        env,
        bounded_archive_command(
            ARCHIVE_EXCLUDED_DIRS, workspace=src, archive_path=container_tar, members=("eval",),
        ),
    )
    if result.get("returncode") != 0:
        raise RuntimeError(f"Failed to archive generated tests: {result.get('output', '').strip()}")
    subprocess.run(
        [executable, "cp", f"{container_id}:{container_tar}", str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )
    _extract_test_suite(dest)


def _process_instance(
    instance: dict,
    output_dir: Path,
    config: dict,
    progress_manager,
    cleanroom_dir: Path | None = None,
    cleanroom_base_image: str = "",
    with_executable: bool = False,
) -> None:
    """Process a single instance with mini-swe-agent."""
    from minisweagent.environments import get_environment
    from minisweagent.models import get_model
    from minisweagent.run.benchmarks.programbench import ProgramBenchAgent as BaseProgramBenchAgent
    from minisweagent.utils.log import logger

    iid = instance["instance_id"]
    instance_dir = output_dir / iid
    (instance_dir / f"{iid}.traj.json").unlink(missing_ok=True)

    progress_manager.on_instance_start(iid)
    progress_manager.update_instance_status(iid, "Starting environment")

    inst_config = copy.deepcopy(config)
    env_config = inst_config.setdefault("environment", {})
    if cleanroom_dir is None:
        env_config["image"] = _task_cleanroom_image(instance)
        cleanroom_source = None
    else:
        env_config.setdefault("image", _cleanroom_base_image(instance, cleanroom_base_image))
        cleanroom_source = cleanroom_dir / iid

    agent = None
    exit_status = None
    extra_info: dict = {}

    try:
        model = get_model(config=inst_config.get("model", {}))
        env = get_environment(inst_config.get("environment", {}), default_type="docker")
        if cleanroom_source is not None:
            with tempfile.TemporaryDirectory(prefix="programbench-test-inputs-") as staging:
                staged = stage_cleanroom(cleanroom_source, Path(staging) / "workspace", with_executable=with_executable)
                _copy_cleanroom(env, staged)
        _ensure_workspace_python(env)
        if not with_executable:
            _hide_executable(env)
        env.execute(
            {"command": 'git config user.name "mini-swe-agent" && git config user.email "mini-swe-agent@proton.me"'}
        )

        if with_executable:
            _protect_generation_reference(env, dict_actions=True)

        agent_config = _normalize_agent_config(inst_config.get("agent", {}))
        agent_config["output_path"] = str(instance_dir / f"{iid}.traj.json")
        agent = _soft_warning_agent_class(BaseProgramBenchAgent)(
            model,
            env,
            progress_manager=progress_manager,
            instance_id=iid,
            **agent_config,
        )
        agent.extra_template_vars = {"instance": instance}
        info = agent.run()
        exit_status = info.get("exit_status")
    except Exception as e:
        logger.error(f"Error processing instance {iid}: {e}", exc_info=True)
        exit_status = type(e).__name__
        extra_info = {"traceback": traceback.format_exc(), "exception_str": str(e)}
    finally:
        if agent is not None:
            try:
                _copy_test_suite(agent.env, instance_dir / "tests.tar.gz")
            except Exception as e:
                logger.error(f"Failed to copy generated tests for {iid}: {e}", exc_info=True)
                extra_info["test_suite_copy_error"] = str(e)
            traj_path = instance_dir / f"{iid}.traj.json"
            agent.save(traj_path, {"info": {"exit_status": exit_status, **extra_info}, "instance_id": iid})
            logger.info(f"Saved trajectory to '{traj_path}'")
        progress_manager.on_instance_end(iid, exit_status)


_OFFICIAL_HUGE_BINARY_NAME_NOTE = (
    "\nThe official documentation may refer to the program by its original binary name "
    "(for example, `ast-grep`), but in this benchmark the program is always compiled and "
    "invoked as `/workspace/executable`.\n"
)


def _codex_test_generation_prompt(
    *, with_executable: bool = False, official_huge: bool = False
) -> str:
    prompt = _CODEX_TEST_GENERATION_SPEC_AND_BINARY if with_executable else _CODEX_TEST_GENERATION_SPEC_ONLY
    if official_huge:
        prompt += _OFFICIAL_HUGE_BINARY_NAME_NOTE
    return prompt


def _codex_test_generation_shell_command(
    codex_command: str,
    *,
    model: str = "",
    with_executable: bool = False,
    reasoning_effort: str = "",
    use_goal: bool = False,
) -> str:
    prompt = (
        TEST_GENERATION_GOAL_COMMAND
        if use_goal
        else _codex_test_generation_prompt(with_executable=with_executable)
    )
    return build_codex_shell_command(
        codex_command,
        prompt=prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        diagnostic_action="generate tests",
    )


def _copy_generation_cleanroom_to_container(
    env: ContainerEnvironment,
    cleanroom: Path,
    *,
    with_executable: bool = False,
) -> None:
    if not cleanroom.is_dir():
        raise RuntimeError(f"Local cleanroom directory does not exist: {cleanroom}")
    with tempfile.TemporaryDirectory(prefix="programbench-test-generation-") as tmp_dir:
        staged = stage_cleanroom(cleanroom, Path(tmp_dir) / "workspace", with_executable=with_executable)
        result = env.execute("mkdir -p /workspace && find /workspace -mindepth 1 -maxdepth 1 -exec rm -rf {} +")
        if result.get("returncode") != 0:
            output = result.get("output", "").strip()
            raise RuntimeError(f"failed to initialize workspace: {output}")
        with _temporarily_make_tar_readable(staged):
            env.copy_in(staged, "/workspace")


def _prepare_codex_test_generation_workspace(
    env: ContainerEnvironment,
    *,
    cleanroom: Path | None,
    with_executable: bool = False,
    use_goal: bool = False,
) -> None:
    if cleanroom is not None:
        _copy_generation_cleanroom_to_container(env, cleanroom, with_executable=with_executable)
    if not with_executable:
        result = env.execute(_HIDE_EXECUTABLE_COMMAND)
        if result.get("returncode") != 0:
            output = result.get("output", "").strip()
            raise RuntimeError(f"Failed to hide ./executable before test generation: {output}")

    result = env.execute(_ENSURE_WORKSPACE_PYTHON_COMMAND)
    if result.get("returncode") != 0:
        output = result.get("output", "").strip()
        raise RuntimeError(f"Failed to make python/python3 available in /workspace: {output}")

    if use_goal:
        with tempfile.TemporaryDirectory(prefix="programbench-test-goal-") as tmp_dir:
            goal_path = Path(tmp_dir) / "codex-goal.md"
            goal_path.write_text(_codex_test_generation_prompt(with_executable=with_executable))
            env.copy_in(goal_path, "/workspace/codex-goal.md")



# ghcr.io/openai/codex-universal does not ship the codex CLI, which is why the
# shared default fetches it with `npx -y @openai/codex@...` at runtime. Test
# generation is a benchmark participant and runs behind the egress allowlist
# when one is configured, where that fetch is refused with a 403 from the proxy.
# The cleanroom images pin codex into the image precisely so it does not need
# the network, so prefer the installed binary whenever we are not on the
# stock image.
PREINSTALLED_CODEX_COMMAND = (
    "codex --dangerously-bypass-approvals-and-sandbox exec --cd /workspace --skip-git-repo-check"
)


def _codex_command_for_image(image: str, codex_command: str) -> str:
    from programbench.spec_improvement import DEFAULT_CODEX_COMMAND, DEFAULT_CODEX_IMAGE, NPX_CODEX_COMMAND

    if codex_command:
        return codex_command
    return NPX_CODEX_COMMAND if image == DEFAULT_CODEX_IMAGE else DEFAULT_CODEX_COMMAND


def _select_codex_test_generation_image(
    instance: dict[str, Any],
    *,
    image: str = "",
    cleanroom_base_image: str = "",
    cleanroom: Path | None = None,
) -> str:
    from programbench.spec_improvement import DEFAULT_CODEX_IMAGE

    if image:
        return image
    if cleanroom_base_image:
        return _cleanroom_base_image(instance, cleanroom_base_image)
    if cleanroom is not None:
        return DEFAULT_CODEX_IMAGE
    return _task_cleanroom_image(instance)


def _load_codex_jsonl_events(path: Path) -> list[dict[str, Any]]:
    """Load the filtered Codex JSONL log, ignoring malformed lines."""
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _codex_event_summary_text(item: dict[str, Any]) -> str:
    item_type = str(item.get("type", "item"))
    detail = item.get("command") or item.get("text") or item.get("name")
    if isinstance(detail, str) and detail.strip():
        compact = " ".join(detail.split())
        return f"Codex {item_type}: {compact}"
    return f"Codex {item_type}"


def _codex_events_to_messages(events: list[dict[str, Any]], *, prompt: str) -> list[dict[str, Any]]:
    """Convert Codex completed-item events to a mini-swe-agent-like message list."""
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    for event in events:
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or f"codex_item_{len(messages)}")
        item_type = item.get("type")
        if item_type == "agent_message":
            messages.append({"role": "assistant", "content": item.get("text", ""), "extra": {"codex_event": event}})
        elif item_type == "command_execution":
            command = str(item.get("command", ""))
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": item_id,
                            "type": "function",
                            "function": {"name": "bash", "arguments": json.dumps({"command": command})},
                        }
                    ],
                    "extra": {"codex_event": event},
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item_id,
                    "content": (
                        "<returncode>{}</returncode>\n<output>\n{}</output>".format(
                            item.get("exit_code"), item.get("aggregated_output", "")
                        )
                    ),
                    "extra": {"returncode": item.get("exit_code"), "status": item.get("status")},
                }
            )
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": item.get("text") or _codex_event_summary_text(item),
                    "extra": {"codex_event": event},
                }
            )
    return messages


def _write_codex_test_generation_trajectory(
    *,
    path: Path,
    instance_id: str,
    prompt: str,
    events: list[dict[str, Any]],
    status: dict[str, Any],
    model: str,
    command: str,
    command_prefix: str,
    selected_image: str,
    with_executable: bool,
    cleanroom: Path | None,
    use_goal: bool = False,
) -> None:
    """Save a mini-swe-agent-like trajectory plus raw Codex events."""
    path.parent.mkdir(parents=True, exist_ok=True)
    usage_records = codex_usage_records_from_events(events)
    trajectory = {
        "info": {
            "exit_status": status.get("status"),
            "returncode": status.get("returncode"),
            "exception_info": status.get("exception_info", ""),
            "image": selected_image,
            "model": model,
            "codex_command": command_prefix,
            "codex_shell_command": command,
            "codex_log": status.get("codex_log"),
            "output": status.get("output"),
            "reason": status.get("reason"),
            "with_executable": with_executable,
            "use_goal": use_goal,
            "cleanroom": str(cleanroom) if cleanroom is not None else None,
        },
        "instance_id": instance_id,
        "usage": sum_codex_usage(usage_records),
        "usage_calls": len(usage_records),
        "messages": _codex_events_to_messages(events, prompt=prompt),
        "codex_events": events,
    }
    path.write_text(json.dumps(trajectory, indent=2, ensure_ascii=False) + "\n")


def _write_codex_trajectory(
    *,
    path: Path,
    instance_id: str,
    prompt: str,
    events: list[dict[str, Any]],
    status: dict[str, Any],
    info: dict[str, Any],
) -> None:
    """Save a mini-swe-agent-like trajectory plus raw Codex events."""
    path.parent.mkdir(parents=True, exist_ok=True)
    usage_records = codex_usage_records_from_events(events)
    trajectory = {
        "info": {
            "exit_status": status.get("status"),
            "returncode": status.get("returncode"),
            "exception_info": status.get("exception_info", ""),
            "output": status.get("output"),
            "reason": status.get("reason"),
            **info,
        },
        "instance_id": instance_id,
        "usage": sum_codex_usage(usage_records),
        "usage_calls": len(usage_records),
        "messages": _codex_events_to_messages(events, prompt=prompt),
        "codex_events": events,
        "codex_output": {
            "stdout": status.get("stdout", ""),
            "stderr": status.get("stderr", ""),
        },
    }
    if status.get("codex_json_events") is not None:
        trajectory["codex_json_events"] = status.get("codex_json_events")
    if status.get("invalid_mutants") is not None:
        trajectory["info"]["invalid_mutants"] = status["invalid_mutants"]
    path.write_text(json.dumps(trajectory, indent=2, ensure_ascii=False) + "\n")


def generate_tests_instance(
    *,
    instance: dict[str, Any],
    output: Path,
    redo_existing: bool = False,
    image: str = "",
    cleanroom_dir: Path | None = None,
    cleanroom_base_image: str = "",
    with_executable: bool = False,
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    codex_command: str = "",
    model: str = "",
    reasoning_effort: str = "",
    timeout: int = 3600,
    codex_auth_file: Path | None = None,
    forward_env: list[str] | None = None,
    run_args: list[str] | None = None,
    codex_log_dir: str | Path = DEFAULT_TEST_CODEX_LOG_DIR,
    progress_log_interval: int = 60,
    use_goal: bool = False,
) -> dict[str, Any]:
    from programbench.spec_improvement import (
        DEFAULT_CODEX_COMMAND,
        _copy_codex_auth_to_container,
        _forwarded_env,
        _progress_phase,
        _stream_codex_json_log,
    )

    instance_id = instance["instance_id"]
    instance_dir = output / instance_id
    tests_archive = instance_dir / "tests.tar.gz"
    traj_path = instance_dir / f"{instance_id}.traj.json"
    codex_log = Path(codex_log_dir) / f"{instance_id}.tests.codex.jsonl"
    if tests_archive.exists() and not redo_existing:
        return {
            "instance_id": instance_id,
            "status": "skipped",
            "reason": "tests_archive_exists",
            "output": str(tests_archive),
            "codex_log": str(codex_log) if codex_log.is_file() else None,
            "traj": str(traj_path) if traj_path.is_file() else None,
        }

    cleanroom = cleanroom_dir / instance_id if cleanroom_dir is not None else None
    selected_image = _select_codex_test_generation_image(
        instance,
        image=image,
        cleanroom_base_image=cleanroom_base_image,
        cleanroom=cleanroom,
    )
    # The command depends on the image: only the stock image needs the npx fetch.
    command_prefix = _codex_command_for_image(selected_image, codex_command)
    prompt = _codex_test_generation_prompt(with_executable=with_executable)
    command = _codex_test_generation_shell_command(
        command_prefix,
        model=model,
        with_executable=with_executable,
        reasoning_effort=reasoning_effort,
        use_goal=use_goal,
    )
    env_config = {
        "CODEX_HOME": "/root/.codex",
        "NPM_CONFIG_UPDATE_NOTIFIER": "false",
        "NO_UPDATE_NOTIFIER": "1",
        "PATH": _WORKSPACE_PATH,
        **_forwarded_env(forward_env or []),
    }

    def save_trajectory(status: dict[str, Any], events: list[dict[str, Any]]) -> None:
        _write_codex_test_generation_trajectory(
            path=traj_path,
            instance_id=instance_id,
            prompt=prompt,
            events=events,
            status=status,
            model=model,
            command=command,
            command_prefix=command_prefix,
            selected_image=selected_image,
            with_executable=with_executable,
            cleanroom=cleanroom,
            use_goal=use_goal,
        )

    log.info("%s: generating tests using image %s", instance_id, selected_image)
    with _progress_phase(instance_id, "start container", interval=progress_log_interval):
        env = ContainerEnvironment(
            image=selected_image,
            cwd="/workspace",
            executable=docker_executable,
            timeout=timeout,
            cpus=docker_cpus,
            env=env_config,
            run_args=[*(run_args or []), *agent_network_args()],
        )
    try:
        if codex_auth_file is not None:
            with _progress_phase(instance_id, "install Codex account auth", interval=progress_log_interval):
                _copy_codex_auth_to_container(env, codex_auth_file)

        with _progress_phase(instance_id, "prepare workspace", interval=progress_log_interval):
            _prepare_codex_test_generation_workspace(
                env,
                cleanroom=cleanroom,
                with_executable=with_executable,
                use_goal=use_goal,
            )
        if with_executable:
            _protect_generation_reference(env)
        with _progress_phase(instance_id, "run Codex", interval=progress_log_interval):
            with _stream_codex_json_log(instance_id, codex_log) as output_callback:
                result = env.execute(command, timeout=timeout, output_callback=output_callback)
        log.info("Finished Codex session with status %d", result["returncode"])
        filtered_stdout = codex_log.read_text() if codex_log.is_file() else ""
        result = {
            **result,
            "stdout": filtered_stdout,
            "output": filtered_stdout + result.get("stderr", ""),
        }
        events = _load_codex_jsonl_events(codex_log)
        status = {
            "instance_id": instance_id,
            "status": "ok" if result.get("returncode") == 0 else "codex_failed",
            "returncode": result.get("returncode"),
            "exception_info": result.get("exception_info", ""),
            "image": selected_image,
            "codex_command": command_prefix,
            "codex_log": str(codex_log),
        }
        if result.get("returncode") != 0:
            status["output"] = result.get("output", "")
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status

        try:
            with _progress_phase(instance_id, "copy generated tests", interval=progress_log_interval):
                _copy_test_suite(env, tests_archive)
        except Exception as error:
            status.update(status="no_tests", reason=str(error), output=result.get("output", ""))
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status

        status["output"] = str(tests_archive)
        save_trajectory(status, events)
        status["traj"] = str(traj_path)
        log.info("%s: generated tests at %s", instance_id, tests_archive)
        return status
    finally:
        env.cleanup()


def run_codex_test_generation_batch(
    *,
    output: str | Path = "",
    model: str = "",
    workers: int = 1,
    filter_spec: str = "",
    slice_spec: str = "",
    shuffle: bool = False,
    redo_existing: bool = False,
    image: str = "",
    cleanroom_dir: str | Path = "",
    cleanroom_base_image: str = "",
    with_executable: bool = False,
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    codex_command: str = "",
    reasoning_effort: str = "",
    timeout: int = 3600,
    codex_auth_file: str | Path = "",
    codex_log_dir: str | Path = DEFAULT_TEST_CODEX_LOG_DIR,
    forward_env: list[str] | None = None,
    run_args: list[str] | None = None,
    progress_log_interval: int = 60,
    use_goal: bool = False,
) -> list[dict[str, Any]]:
    output_path = Path(output) if output else Path(f"programbench_test_generation_{int(time.time())}")
    output_path.mkdir(parents=True, exist_ok=True)

    instances = load_all_instances(include_tests=False)
    instances = filter_instances(instances, filter_spec=filter_spec, slice_spec=slice_spec, shuffle=shuffle)
    if not instances:
        log.warning("No instances selected for test generation.")
        return []

    cleanroom_path = Path(cleanroom_dir) if cleanroom_dir else None
    log.info("Generating tests for %d instance(s)", len(instances))
    results: list[dict[str, Any]] = []
    with (
        logging_redirect_tqdm(),
        concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        futures = {
            executor.submit(
                generate_tests_instance,
                instance=instance,
                output=output_path,
                redo_existing=redo_existing,
                image=image,
                cleanroom_dir=cleanroom_path,
                cleanroom_base_image=cleanroom_base_image,
                with_executable=with_executable,
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
                use_goal=use_goal,
            ): instance["instance_id"]
            for instance in instances
        }
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Generating tests",
            ncols=100,
            leave=False,
            disable=None,
        ):
            instance_id = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                log.error("Error generating tests for %s: %s", instance_id, e, exc_info=True)
                results.append({"instance_id": instance_id, "status": type(e).__name__, "error": str(e)})

    return sorted(results, key=lambda r: r["instance_id"])


def run_test_generation_batch(
    *,
    output: str | Path = "",
    model: str | None = None,
    reasoning_effort: str = "",
    config_specs: list[str] | None = None,
    workers: int = 1,
    filter_spec: str = "",
    slice_spec: str = "",
    shuffle: bool = False,
    redo_existing: bool = False,
    model_class: str | None = None,
    environment_class: str | None = None,
    cleanroom_dir: str | Path = "",
    cleanroom_base_image: str = "",
    with_executable: bool = False,
) -> None:
    """Run mini-swe-agent to generate `tests.tar.gz` for selected instances."""
    prompt_mode = GenerationPromptMode.SPEC_AND_BINARY if with_executable else GenerationPromptMode.SPEC_ONLY
    system_template, instance_template = build_agent_templates(mode=prompt_mode)

    try:
        from minisweagent.config import builtin_config_dir, get_config_from_spec
        from minisweagent.run.benchmarks.utils.batch_progress import RunBatchProgressManager
        from minisweagent.utils.log import add_file_handler, logger
        from minisweagent.utils.serialize import UNSET, recursive_merge
        from rich.live import Live
    except ImportError as e:
        raise RuntimeError(
            "Test generation requires mini-swe-agent. Run this command with "
            "`uv run --with mini-swe-agent programbench generate-tests ...`."
        ) from e

    default_config = builtin_config_dir / "benchmarks" / "programbench.yaml"
    output_path = Path(output) if output else Path(f"programbench_test_generation_{int(time.time())}")
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generated test suites will be saved to {output_path}")
    add_file_handler(output_path / "minisweagent.log")

    instances = load_all_instances(include_tests=False)
    instances = filter_instances(instances, filter_spec=filter_spec, slice_spec=slice_spec, shuffle=shuffle)

    if not redo_existing:
        existing = {i["instance_id"] for i in instances if (output_path / i["instance_id"] / "tests.tar.gz").exists()}
        if existing:
            logger.info(f"Skipping {len(existing)} existing instances")
            instances = [i for i in instances if i["instance_id"] not in existing]


    configs = [get_config_from_spec(spec) for spec in (config_specs or [str(default_config)])]
    overrides = {
        "agent": {
            "system_template": system_template,
            "instance_template": instance_template,
        },
        "model": {
            "model_name": model or UNSET,
            "model_class": model_class or UNSET,
            "reasoning_effort": reasoning_effort or UNSET,
            "observation_template": _STREAM_SEPARATED_OBSERVATION_TEMPLATE,
        },
    }
    if environment_class is not None:
        overrides["environment"] = {"environment_class": environment_class}
    configs.append(overrides)
    config = recursive_merge(*configs)
    if environment_class is None:
        env_config = config.setdefault("environment", {})
        if env_config.get("environment_class", "docker") == "docker":
            env_config["environment_class"] = _PROGRAMBENCH_STREAM_ENVIRONMENT_CLASS
        _ensure_workspace_path(env_config)

    cleanroom_path = Path(cleanroom_dir) if cleanroom_dir else None
    progress_manager = RunBatchProgressManager(len(instances), output_path / f"exit_statuses_{int(time.time())}.yaml")

    def process_futures(futures: dict[concurrent.futures.Future, str]) -> None:
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except concurrent.futures.CancelledError:
                pass
            except Exception as e:
                instance_id = futures[future]
                logger.error(f"Error in future for instance {instance_id}: {e}", exc_info=True)
                progress_manager.on_uncaught_exception(instance_id, e)

    with Live(progress_manager.render_group, refresh_per_second=4):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _process_instance,
                    instance,
                    output_path,
                    config,
                    progress_manager,
                    cleanroom_path,
                    cleanroom_base_image,
                    with_executable,
                ): instance[
                    "instance_id"
                ]
                for instance in instances
            }
            try:
                process_futures(futures)
            except KeyboardInterrupt:
                logger.info("Cancelling all pending jobs. Press ^C again to exit immediately.")
                for future in futures:
                    if not future.running() and not future.done():
                        future.cancel()
                process_futures(futures)
