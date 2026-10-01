#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Run Codex on a ProgramBench solve task."""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any


# Standalone runners use bare python3, without requiring an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "programbench"))
from container_cleanup import container_labels, install_shutdown_handlers, remove_container
from archive_limits import MAX_ARCHIVE_BYTES, bounded_archive_command
from reference_isolation import (reference_cleanup_command, solve_workspace_setup, stage_cleanroom,
    stage_reference, guard_reference_session)


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
log = logging.getLogger("programbench.solve_codex")

DEFAULT_MODEL = "codex/gpt-5.6-sol"
DEFAULT_REASONING = "high"
DEFAULT_TASK = "abishekvashok__cmatrix.5c082c6"
DEFAULT_BASE_TAG = "task_cleanroom"
DEFAULT_TAG_SUFFIX = "codex"
DEFAULT_MODE = "spec-only"
DEFAULT_STDOUT_PASSTHROUGH_LIMIT = 240
DEFAULT_TIMEOUT_SECONDS = 21600
DEFAULT_CODEX_COMMAND = "codex --dangerously-bypass-approvals-and-sandbox exec --cd /workspace --skip-git-repo-check --config tools.web_search=false"
VALID_MODES = ("with-executable", "spec-only", "with-test", "with-test-force")
WITH_TEST_MODES = ("with-test", "with-test-force")
WITH_TEST_SUITE_MODE = "with-executable"

PROMPT_SPEC_ONLY = """\
You are reimplementing a program from its specification.

## Workspace

The workspace contains the program specification.

## Task

Reimplement a new, original codebase from scratch that satisfies the specification and produces the required executable.

## Rules

- You may read bundled documentation and the specification.
- Do not search the internet, clone repositories, or download the original project from package registries.
- Do not run package-manager updates or installs, curl/wget, networked git commands, or any other command that fetches task dependencies.
- Use only tools and dependencies already present when the task starts. Installing something in the live container does not make it available on a fresh grading checkout.

## Output

- Create `./compile.sh`.
- `./compile.sh` must be executable and must build `./executable` in the workspace root on a fresh checkout.
- Only `./executable` is retained when tests run; the rest of the workspace is removed. It must be self-contained and must not depend on sibling files.
"""

PROMPT_WITH_EXECUTABLE = """\
You are reimplementing a program from its specification and reference executable.

## Workspace

The workspace contains the program specification and a reference executable at ./executable.

## Task

Reimplement a new, original codebase from scratch that produces an executable with identical behavior.

## Rules

- You may read bundled documentation and the specification.
- Thoroughly run ./executable with inputs, flags, stdin, and files to observe behavior.
- Do not search the internet, clone repositories, or download the original project from package registries.
- Do not run package-manager updates or installs, curl/wget, networked git commands, or any other command that fetches task dependencies.
- Use only tools and dependencies already present when the task starts. Installing something in the live container does not make it available on a fresh grading checkout.
- Do not decompile ./executable or use objdump, Ghidra, strace, ltrace, or similar binary-analysis/tracing tools on it.

## Output

- Create ./compile.sh.
- ./compile.sh must be executable and must build ./executable in the workspace root on a fresh checkout.
- Only ./executable is retained when tests run; the rest of the workspace is removed. It must be self-contained and must not depend on sibling files such as scripts, data files, or interpreters it launches by path.
"""

PROMPT_WITH_TEST = """\
/goal Follow the full task in codex-goal.md. Keep working until at least 50% of the tests pass.
"""

CODEX_GOAL_WITH_TEST = """\
You are given a program specification and a generated test suite.

## Workspace

- The workspace contains the program specification, bundled documentation, and generated tests.

## Task

Reimplement a new, original codebase from scratch that satisfies the specification and produces the required executable.

## Rules

- You may read bundled documentation, the specification, and the generated tests.
- Keep iterating until at least 50% of the generated tests pass. If at least 50% pass cannot be reached, preserve the best working implementation and report the remaining failures.
- The generated tests are not the final ground-truth evaluation suite; use them as development feedback, not as the only behavior to implement.
- Do not search the internet, clone repositories, or download the original project from package registries.
- Do not run package-manager updates or installs, curl/wget, networked git commands, or any other command that fetches task dependencies.
- Use only tools and dependencies already present when the task starts. Installing something in the live container does not make it available on a fresh grading checkout.
- Do not decompile binaries or use objdump, Ghidra, strace, ltrace, or similar binary-analysis/tracing tools.

## Output

- Create ./compile.sh.
- ./compile.sh must be executable and must build ./executable in the workspace root on a fresh checkout.
- Only ./executable is retained when tests run; the rest of the workspace is removed. It must be self-contained and must not depend on sibling files such as scripts, data files, or interpreters it launches by path.
- Do not make ./compile.sh depend on ./run_generated_tests.sh, .programbench-generated-tests, or any generated-test files; those are temporary development aids and are not part of the final submission.
- Use ./run_generated_tests.sh to run the provided generated test suite against ./executable.
"""


class DefaultsFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def _get_help_string(self, action: argparse.Action) -> str:
        if action.default == "":
            return action.help or ""
        return super()._get_help_string(action)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Codex on the original ProgramBench reverse-engineering task. "
            "Output is compatible with: uv run programbench eval <output>"
        ),
        formatter_class=DefaultsFormatter,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Codex model to use")
    parser.add_argument("--reasoning", default=DEFAULT_REASONING, help="Reasoning effort to use")
    parser.add_argument("--task", default=DEFAULT_TASK, help="Task filter to use")
    parser.add_argument("--output", default="", help="Output directory (default: output/executable/<model>-<reasoning>-<mode>)")
    parser.add_argument("--mode", choices=VALID_MODES, default=DEFAULT_MODE, help="Solve mode")
    parser.add_argument(
        "--test-suite",
        default="",
        help=(
            "Generated test suite archive, unpacked suite directory, or multi-branch instance directory for with-test modes "
            "(default: output/test-suites/<model>-<reasoning>-with-executable>/<task>/tests.tar.gz)"
        ),
    )
    parser.add_argument(
        "--cleanroom",
        default="",
        help="Local cleanroom root. Expected layout: <cleanroom>/<task>/",
    )
    parser.add_argument("--base-tag", default=DEFAULT_BASE_TAG, help="Source task cleanroom tag to Codex-enable")
    parser.add_argument(
        "--tag-suffix",
        default=DEFAULT_TAG_SUFFIX,
        help="Codex image suffix after <base-tag>_",
    )
    parser.add_argument(
        "--cleanroom-base-image",
        default="",
        help="Prebuilt Codex-enabled task image (default: auto-build <base-tag>_<tag-suffix>)",
    )
    parser.add_argument(
        "--codex-command",
        default=DEFAULT_CODEX_COMMAND,
        help="Codex command to run inside the cleanroom",
    )
    parser.add_argument(
        "--stdout-aggregated-output-limit",
        type=int,
        default=DEFAULT_STDOUT_PASSTHROUGH_LIMIT,
        help="Max chars printed for non-JSON Codex passthrough lines",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Docker run timeout in seconds")
    parser.add_argument("--docker-cpus", type=int, default=4, help="CPU cores allotted to the solve container")
    return parser.parse_args()


def codex_model(model: str) -> str:
    return model.removeprefix("codex/")


def default_test_suite_archive(model: str, reasoning: str, task: str) -> Path:
    return Path("output") / "test-suites" / f"{model}-{reasoning}-{WITH_TEST_SUITE_MODE}" / task / "tests.tar.gz"


def is_with_test_mode(mode: str) -> bool:
    return mode in WITH_TEST_MODES


def test_suite_output_label(test_suite_source: Path, task: str) -> Path:
    instance_dir = test_suite_source.parent
    if instance_dir.name != task:
        return Path(test_suite_source.parent.name)

    parts = instance_dir.parts
    for idx in range(len(parts) - 1):
        if parts[idx] == "output" and parts[idx + 1] == "test-suites":
            label_parts = parts[idx + 2 : -1]
            if label_parts:
                return Path(*label_parts)

    return Path(instance_dir.parent.name)


def resolve_test_suite_source(args: argparse.Namespace) -> Path | None:
    if not is_with_test_mode(args.mode):
        if args.test_suite:
            raise SystemExit("--test-suite is only supported with --mode with-test or with-test-force")
        return None

    source = Path(args.test_suite) if args.test_suite else default_test_suite_archive(args.model, args.reasoning, args.task)
    if source.is_dir():
        nested_archive = source / "tests.tar.gz"
        if nested_archive.is_file():
            source = nested_archive
        elif (source / "eval" / "run.sh").is_file() or any(source.glob("*/eval/run.sh")):
            return source.resolve()
        else:
            raise SystemExit(
                "Generated test suite directory must contain tests.tar.gz, "
                "eval/run.sh, or branch subdirectories with eval/run.sh: "
                f"{source}"
            )
    if not source.is_file():
        raise SystemExit(f"Generated test suite archive or directory does not exist: {source}")
    return source.resolve()


def output_dir(args: argparse.Namespace, test_suite_source: Path | None = None) -> Path:
    output = Path(args.output or f"output/executable/{args.model}-{args.reasoning}-{args.mode}")
    if args.output or not is_with_test_mode(args.mode) or test_suite_source is None:
        return output
    return output / test_suite_output_label(test_suite_source, args.task)


def _archive_member_parts(member_name: str) -> tuple[str, ...]:
    return tuple(part for part in PurePosixPath(member_name).parts if part != ".")


def _archive_member_is_eval(member_name: str) -> bool:
    parts = _archive_member_parts(member_name)
    if not parts:
        return False
    if parts[0] == "eval":
        return True
    return len(parts) >= 2 and parts[1] == "eval"


def _archive_member_is_safe(member_name: str) -> bool:
    parts = _archive_member_parts(member_name)
    return bool(parts) and not PurePosixPath(member_name).is_absolute() and ".." not in parts


def _sanitize_tarinfo(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    tarinfo.uid = 0
    tarinfo.gid = 0
    tarinfo.uname = "root"
    tarinfo.gname = "root"
    return tarinfo


def _write_sanitized_archive_from_dir(source: Path, dest: Path) -> None:
    suite_roots = []
    if (source / "eval" / "run.sh").is_file():
        suite_roots.append((source, Path(".")))
    for run_script in sorted(source.glob("*/eval/run.sh")):
        branch_root = run_script.parents[1]
        suite_roots.append((branch_root, Path(branch_root.name)))

    if not suite_roots:
        raise SystemExit(f"Generated test suite directory has no eval/run.sh files: {source}")

    with tarfile.open(dest, "w:gz") as archive:
        for suite_root, arc_root in suite_roots:
            eval_dir = suite_root / "eval"
            arcname = arc_root / "eval" if str(arc_root) != "." else Path("eval")
            archive.add(eval_dir, arcname=str(arcname), recursive=True, filter=_sanitize_tarinfo)


def _write_sanitized_archive_from_archive(source: Path, dest: Path) -> None:
    found_run_sh = False
    with tarfile.open(source, "r:gz") as src_archive, tarfile.open(dest, "w:gz") as dst_archive:
        for member in src_archive.getmembers():
            if not _archive_member_is_safe(member.name) or not _archive_member_is_eval(member.name):
                continue
            if Path(member.name).as_posix().endswith("eval/run.sh") or member.name == "eval/run.sh":
                found_run_sh = True
            sanitized_member = _sanitize_tarinfo(copy.copy(member))
            fileobj = src_archive.extractfile(member) if member.isfile() else None
            dst_archive.addfile(sanitized_member, fileobj)
            if fileobj is not None:
                fileobj.close()
    if not found_run_sh:
        raise SystemExit(f"Generated test suite archive has no eval/run.sh files: {source}")


def prepare_test_suite_archive(test_suite_source: Path | None, temp_dir: Path) -> Path | None:
    if test_suite_source is None:
        return None

    temp_dir.mkdir(parents=True, exist_ok=True)
    dest = temp_dir / "sanitized-tests.tar.gz"
    if test_suite_source.is_dir():
        _write_sanitized_archive_from_dir(test_suite_source, dest)
    else:
        _write_sanitized_archive_from_archive(test_suite_source, dest)
    return dest


def resolve_cleanroom_source(cleanroom: str, task: str) -> Path | None:
    if not cleanroom:
        return None
    source = Path(cleanroom) / task
    if not source.is_dir():
        raise SystemExit(f"Local cleanroom directory does not exist: {source}")
    return source.resolve()


def docker() -> str:
    return os.environ.get("PROGRAMBENCH_DOCKER_EXECUTABLE", "docker")


def docker_preflight() -> None:
    docker_bin = docker()
    if shutil.which(docker_bin) is None:
        print(f"Docker executable not found: {docker_bin}", file=sys.stderr)
        print(
            "Install Docker or set PROGRAMBENCH_DOCKER_EXECUTABLE to the docker-compatible CLI to use.",
            file=sys.stderr,
        )
        raise SystemExit(127)

    result = subprocess.run([docker_bin, "info"], cwd=repo_root(), capture_output=True, text=True)
    if result.returncode == 0:
        return

    print("Docker is not reachable from this shell.", file=sys.stderr)
    print(result.stdout + result.stderr, file=sys.stderr, end="")
    if os.environ.get("DOCKER_HOST"):
        print(f"DOCKER_HOST is set to: {os.environ['DOCKER_HOST']}", file=sys.stderr)
        print(
            "Unset DOCKER_HOST if you want the default Docker socket, or start the daemon that owns that socket.",
            file=sys.stderr,
        )
    else:
        print("Start Docker, or set DOCKER_HOST to a reachable Docker daemon socket.", file=sys.stderr)
    raise SystemExit(result.returncode)


def ensure_cleanroom_image(args: argparse.Namespace) -> str:
    if args.cleanroom_base_image:
        print(f"Using Codex cleanroom image: {args.cleanroom_base_image}")
        return args.cleanroom_base_image

    installer = repo_root() / "scripts" / "docker" / "install_codex_cleanroom.sh"
    common = ["--task", args.task, "--base-tag", args.base_tag, "--tag-suffix", args.tag_suffix]
    image = subprocess.check_output([str(installer), *common, "--print-image"], cwd=repo_root(), text=True).strip()
    subprocess.run([str(installer), *common], cwd=repo_root(), check=True)
    return image


def solve_prompt(mode: str) -> str:
    if mode == "spec-only":
        return PROMPT_SPEC_ONLY
    if mode == "with-test-force":
        return PROMPT_WITH_TEST
    if mode == "with-test":
        return CODEX_GOAL_WITH_TEST

    return PROMPT_WITH_EXECUTABLE


def build_docker_args(
    container_name: str,
    prompt_file: Path,
    cleanroom_source: Path | None,
    test_suite_source: Path | None,
    docker_cpus: int = 20,
) -> list[str]:
    args = [
        "run",
        "--name",
        container_name,
        *container_labels(),
        "--cpus",
        str(docker_cpus),
        "--memory",
        "256g",
        "--memory-swap",
        "256g",
        "--user",
        "0:0",
        "--cap-drop",
        "SYS_PTRACE",
        "-e",
        "PAGER=cat",
        "-e",
        "MANPAGER=cat",
        "-e",
        "LESS=-R",
        "-e",
        "PIP_PROGRESS_BAR=off",
        "-e",
        "TQDM_DISABLE=1",
        "-v",
        f"{prompt_file}:/tmp/programbench_prompt.txt:ro",
        *agent_network_args(),
    ]
    if cleanroom_source is not None:
        args.extend(["-v", f"{cleanroom_source}:/tmp/programbench_cleanroom:ro"])
    if test_suite_source is not None:
        args.extend(["-v", f"{test_suite_source}:/tmp/programbench_tests.tar.gz:ro"])

    kind, auth_file = codex_credential()
    if kind == "login":
        args.extend(["-v", f"{auth_file}:/root/.codex/auth.json:ro"])
    elif kind == "api-key":
        args.extend(["-e", "OPENAI_API_KEY"])
    return args


def codex_auth_file() -> Path:
    default_auth = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "auth.json"
    return Path(os.environ.get("PROGRAMBENCH_CODEX_AUTH_FILE", str(default_auth)))


def codex_credential() -> tuple[str, Path | None]:
    """Pick the one credential the Codex container gets: ``("login", file)``, ``("api-key", None)`` or ``("none", None)``.

    The ``codex login`` file (a ChatGPT subscription by default) wins over ``OPENAI_API_KEY``.
    Giving the container both leaves the choice to the CLI, so the run can bill either one
    without anything saying which. ``PROGRAMBENCH_CODEX_AUTH`` forces a source: ``login``,
    ``api-key``, or ``auto`` (the default).
    """
    mode = os.environ.get("PROGRAMBENCH_CODEX_AUTH", "auto")
    if mode not in ("auto", "login", "api-key"):
        raise SystemExit(f"PROGRAMBENCH_CODEX_AUTH must be auto, login or api-key, got: {mode}")
    auth_file = codex_auth_file()
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    if mode == "login" and not auth_file.is_file():
        raise SystemExit(f"PROGRAMBENCH_CODEX_AUTH=login but there is no login file at {auth_file}; run `codex login`")
    if mode == "api-key" and not has_key:
        raise SystemExit("PROGRAMBENCH_CODEX_AUTH=api-key but OPENAI_API_KEY is not set")
    if mode in ("auto", "login") and auth_file.is_file():
        return "login", auth_file
    if has_key:
        return "api-key", None
    return "none", None


def describe_codex_credential(kind: str, auth_file: Path | None) -> str:
    if kind == "login":
        try:
            auth_mode = json.loads(auth_file.read_text()).get("auth_mode", "unknown")
        except (OSError, ValueError, AttributeError):
            auth_mode = "unknown"
        label = {"chatgpt": "ChatGPT subscription login", "apikey": "API key stored by `codex login`"}.get(
            auth_mode, f"login file (auth_mode: {auth_mode})"
        )
        return f"{label} from {auth_file}; OPENAI_API_KEY is not passed to the container"
    if kind == "api-key":
        return "OPENAI_API_KEY from the environment; no login file is mounted"
    return "none found (no login file and no OPENAI_API_KEY)"



# Mirrors programbench.constants.agent_network_args; this script runs under bare
# python3 and cannot import the package. tests/test_agent_network.py asserts the
# two produce identical args.
def agent_network_args() -> list[str]:
    network = os.environ.get("PROGRAMBENCH_EGRESS_NETWORK", "pb-egress")
    if not network:
        return []
    proxy = os.environ.get("PROGRAMBENCH_EGRESS_PROXY", "http://pb-proxy:3128")
    args = ["--network", network]
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        args += ["-e", f"{name}={proxy}"]
    for name in ("NO_PROXY", "no_proxy"):
        args += ["-e", f"{name}=localhost,127.0.0.1"]
    return args


def agent_network_preflight() -> None:
    """Refuse to launch an agent that would reach the open internet.

    The failure this catches is silent: an unconfined container leaves no trace
    in the trajectory, so a suite written against the upstream source looks like
    one reverse engineered from the binary. Confinement is now the default, so
    reaching here means someone emptied PROGRAMBENCH_EGRESS_NETWORK.
    """
    if agent_network_args():
        return
    if os.environ.get("PROGRAMBENCH_ALLOW_OPEN_NETWORK"):
        print("PROGRAMBENCH_ALLOW_OPEN_NETWORK is set: this agent container gets the open internet.", file=sys.stderr)
        return
    print("PROGRAMBENCH_EGRESS_NETWORK is empty: this agent container would reach the open internet.", file=sys.stderr)
    print("Run scripts/docker/setup_egress_network.sh, or set PROGRAMBENCH_ALLOW_OPEN_NETWORK=1 to accept an unconfined run.", file=sys.stderr)
    raise SystemExit(2)


MAX_SUBMISSION_ARCHIVE_BYTES = MAX_ARCHIVE_BYTES


def submission_archive_command(
    excludes: tuple[str, ...],
    *,
    workspace: str = "/workspace",
    archive_path: str = "/tmp/submission.tar.gz",
    limit_bytes: int = MAX_SUBMISSION_ARCHIVE_BYTES,
) -> str:
    """Bound uncompressed submission contents while tar is writing them."""
    return bounded_archive_command(
        excludes, workspace=workspace, archive_path=archive_path, limit_bytes=limit_bytes,
    )


def build_container_script(mode: str, command_prefix: str, model: str, reasoning: str) -> str:
    goal_markdown_block = ""
    if mode == "with-test-force":
        goal_markdown_block = f"""codex_goal={shlex.quote(CODEX_GOAL_WITH_TEST)}
printf '%s' "$codex_goal" > /workspace/codex-goal.md
"""

    script = f"""set -euo pipefail
mode={shlex.quote(mode)}
codex_model={shlex.quote(model)}
reasoning={shlex.quote(reasoning)}
{solve_workspace_setup(mode)}
if [ "$mode" = "with-test" ] || [ "$mode" = "with-test-force" ]; then
    if [ ! -f /tmp/programbench_tests.tar.gz ]; then
        echo "with-test modes require a generated tests.tar.gz archive or unpacked test directory" >&2
        exit 1
    fi
    rm -rf /workspace/.programbench-generated-tests
    mkdir -p /workspace/.programbench-generated-tests
    tar --no-same-owner -xzf /tmp/programbench_tests.tar.gz -C /workspace/.programbench-generated-tests
    cat > /workspace/run_generated_tests.sh <<'PROGRAMBENCH_RUN_TESTS'
#!/usr/bin/env bash
set -euo pipefail
if [ ! -x /workspace/executable ]; then
    echo "Expected executable at /workspace/executable; run ./compile.sh first" >&2
    exit 1
fi
mapfile -d '' run_scripts < <(find /workspace/.programbench-generated-tests -path '*/eval/run.sh' -type f -print0 | sort -z)
if [ "${{#run_scripts[@]}}" -eq 0 ]; then
    echo "No generated eval/run.sh files found" >&2
    exit 1
fi
overall_status=0
for run_script in "${{run_scripts[@]}}"; do
    suite_dir="${{run_script%/eval/run.sh}}"
    suite_name="${{suite_dir#/workspace/.programbench-generated-tests/}}"
    if [ "$suite_name" = "$suite_dir" ]; then
        suite_name="."
    fi
    rm -f "$suite_dir/executable"
    ln -s /workspace/executable "$suite_dir/executable"
    echo "=== Running generated tests: $suite_name ==="
    if ! (cd "$suite_dir" && EXECUTABLE=/workspace/executable bash "$run_script"); then
        overall_status=1
    fi
done
exit "$overall_status"
PROGRAMBENCH_RUN_TESTS
    chmod +x /workspace/run_generated_tests.sh
fi
{goal_markdown_block}prompt=$(cat /tmp/programbench_prompt.txt)
cmd=({command_prefix})
if [ -n "$codex_model" ]; then
    cmd+=(--model "$codex_model")
fi
if [ -n "$reasoning" ]; then
    cmd+=(--config "model_reasoning_effort=$reasoning")
fi
cmd+=(--json "$prompt")
set +e
"${{cmd[@]}}"
status=$?
set -e
{submission_archive_command(("./executable", "./.programbench-generated-tests", "./run_generated_tests.sh", "./codex-goal.md", "./results.xml"))}
exit "$status"
"""

    return guard_reference_session(script, enabled=mode == "with-executable")


def truncate(value: str, limit: int) -> str:
    if limit < 0 or len(value) <= limit:
        return value
    omitted = len(value) - limit
    return f"{value[:limit]}\n...[truncated {omitted} chars]"


# One compact line per step, matching the other agents: the full JSONL is already
# captured in stdout.jsonl, so this only keeps a long run from looking idle.
PROGRESS_LINE_LIMIT = 160


ERROR_LINE_LIMIT = 1000


def _progress_line(text: str, limit: int = PROGRESS_LINE_LIMIT) -> str:
    text = " ".join(text.split())
    if not text:
        return ""
    return text[:limit] + ("...\n" if len(text) > limit else "\n")


def _error_text(error: object) -> str:
    """The human-readable part of an error event, which Codex often nests as a JSON string."""
    if isinstance(error, str):
        try:
            error = json.loads(error)
        except ValueError:
            return error
    if isinstance(error, dict):
        nested = error.get("error")
        if isinstance(nested, (dict, str)):
            return _error_text(nested)
        return str(error.get("message", error))
    return str(error)


def display_event(line: str, limit: int) -> str:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        event = None
    # The container also prints non-event output on this stream, and a bare number
    # such as the JUnit testcase count parses as JSON, so check for a dict.
    if not isinstance(event, dict):
        return truncate(line.rstrip(), limit) + "\n"
    kind = event.get("type")
    if kind == "turn.completed":
        usage = event.get("usage") or {}
        return _progress_line(
            f"[turn] input={usage.get('input_tokens', 0)} cached={usage.get('cached_input_tokens', 0)} "
            f"output={usage.get('output_tokens', 0)} reasoning={usage.get('reasoning_output_tokens', 0)}"
        )
    if kind in ("turn.failed", "error"):
        # The cause (an unsupported model, a bad credential) is at the end of long messages, so keep them whole.
        error = event.get("error", event.get("message"))
        return _progress_line(f"[error] {_error_text(error)}", ERROR_LINE_LIMIT)
    # Report each item once, when it completes; item.started repeats the command.
    item = event.get("item")
    if kind != "item.completed" or not isinstance(item, dict):
        return ""
    item_type = item.get("type")
    if item_type == "agent_message":
        return _progress_line(item.get("text", ""))
    if item_type == "reasoning":
        return _progress_line(f"[reasoning] {item.get('text', '')}")
    if item_type == "command_execution":
        exit_code = item.get("exit_code")
        status = f" (exit {exit_code})" if exit_code not in (None, 0) else ""
        return _progress_line(f"[command] {item.get('command', '')}{status}")
    if item_type == "file_change":
        changes = ", ".join(f"{c.get('kind')} {c.get('path')}" for c in item.get("changes", []) if isinstance(c, dict))
        return _progress_line(f"[file_change] {changes}")
    if item_type == "mcp_tool_call":
        return _progress_line(f"[{item.get('server', 'mcp')}.{item.get('tool', 'tool')}] {json.dumps(item.get('arguments', {}), ensure_ascii=False)}")
    if item_type == "web_search":
        return _progress_line(f"[web_search] {item.get('query', '')}")
    if item_type == "todo_list":
        return _progress_line("[plan] " + "; ".join(str(t.get("text", "")) for t in item.get("items", []) if isinstance(t, dict)))
    return ""


def run_container(
    *,
    args: argparse.Namespace,
    image: str,
    container_name: str,
    prompt_file: Path,
    cleanroom_source: Path | None,
    test_suite_source: Path | None,
    raw_stdout: Path,
    raw_stderr: Path,
) -> int:
    command = [
        "timeout",
        str(args.timeout),
        docker(),
        *build_docker_args(container_name, prompt_file, cleanroom_source, test_suite_source, args.docker_cpus),
        image,
        "bash",
        "-lc",
        build_container_script(args.mode, args.codex_command, codex_model(args.model), args.reasoning),
    ]

    with raw_stdout.open("w", buffering=1) as stdout_file, raw_stderr.open("w") as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=repo_root(),
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            stdout_file.write(line)
            stdout_file.flush()
            sys.stdout.write(display_event(line, args.stdout_aggregated_output_limit))
            sys.stdout.flush()
        return process.wait()


def copy_submission(container_name: str, submission: Path) -> None:
    result = subprocess.run(
        [docker(), "cp", f"{container_name}:/tmp/submission.tar.gz", str(submission)],
        cwd=repo_root(),
    )
    if result.returncode == 0:
        log.info("Saved submission to %s", submission)
    else:
        log.error("Failed to copy submission archive from %s", container_name)


def cleanroom_base_image(task: str, base_tag: str) -> str:
    image_task = task.replace("__", "_1776_", 1)
    return f"programbench/{image_task}:{base_tag}"


def verify_fresh_offline_build(
    submission: Path,
    image: str,
    *,
    docker_cpus: int = 20,
    timeout: int = 600,
) -> tuple[bool, str]:
    """Build in the solve image with networking and Codex credentials disabled."""
    if not submission.is_file():
        return False, f"submission archive does not exist: {submission}"

    script = "set -euo pipefail\n" + reference_cleanup_command() + "\n" + """
find /workspace -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar --no-same-owner -xzf /tmp/programbench-submission.tar.gz -C /workspace
test -x /workspace/compile.sh
cd /workspace
./compile.sh
test -x /workspace/executable
"""
    command = [
        docker(),
        "run",
        "--rm",
        "--pull",
        "never",
        *container_labels(),
        "--network",
        "none",
        "--env",
        "OPENAI_API_KEY=",
        "--env",
        "CODEX_HOME=/root/.codex",
        "--tmpfs",
        "/root/.codex:rw,noexec,nosuid,nodev,size=1m",
        "--cpus",
        str(docker_cpus),
        "--memory",
        "256g",
        "--memory-swap",
        "256g",
        "--user",
        "0:0",
        "--entrypoint",
        "",
        "-v",
        f"{submission.resolve()}:/tmp/programbench-submission.tar.gz:ro",
        image,
        "bash",
        "-lc",
        script,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=repo_root(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"fresh offline build timed out after {timeout}s"
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        return False, output.strip() or f"fresh offline build exited {result.returncode}"
    return True, output.strip()


def trajectory_python() -> list[str]:
    if shutil.which("uv"):
        return ["uv", "run", "python"]
    if shutil.which("python3"):
        return ["python3"]
    return []


def write_trajectory(
    *,
    args: argparse.Namespace,
    image: str,
    submission: Path,
    traj: Path,
    prompt_file: Path,
    raw_stdout: Path,
    raw_stderr: Path,
    run_status: int,
) -> None:
    python = trajectory_python()
    if not python:
        print("uv and python3 not found; skipped Codex trajectory generation", file=sys.stderr)
        return

    trajectory_status = "ok" if run_status == 0 else "codex_failed"
    result = subprocess.run(
        [
            *python,
            "scripts/agents/codex_jsonl_to_traj.py",
            "--raw-stdout",
            str(raw_stdout),
            "--raw-stderr",
            str(raw_stderr),
            "--traj",
            str(traj),
            "--prompt-file",
            str(prompt_file),
            "--instance-id",
            args.task,
            "--status",
            trajectory_status,
            "--returncode",
            str(run_status),
            "--model",
            codex_model(args.model),
            "--image",
            image,
            "--codex-command",
            args.codex_command,
            "--reasoning",
            args.reasoning,
            "--output",
            str(submission),
        ],
        cwd=repo_root(),
    )
    if result.returncode == 0:
        print(f"Saved Codex trajectory to {traj}")
    else:
        print("Failed to write Codex trajectory", file=sys.stderr)


def record_timing(traj: Path, started: float, finished: float) -> None:
    if not traj.is_file():
        return
    payload = json.loads(traj.read_text())
    payload["info"].update(
        started_at=time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)),
        finished_at=time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(finished)),
        duration_seconds=round(finished - started, 1),
    )
    traj.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def cleanup(container_name: str, temp_dir: Path) -> None:
    remove_container(docker(), container_name)
    shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> int:
    install_shutdown_handlers()
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    args = parse_args()
    test_suite_source = resolve_test_suite_source(args)
    out_dir = output_dir(args, test_suite_source)
    cleanroom_source = resolve_cleanroom_source(args.cleanroom, args.task)

    docker_preflight()
    agent_network_preflight()
    kind, auth_file = codex_credential()
    print(f"[codex] credentials: {describe_codex_credential(kind, auth_file)}", flush=True)
    image = ensure_cleanroom_image(args)

    instance_dir = out_dir / args.task
    instance_dir.mkdir(parents=True, exist_ok=True)
    submission = instance_dir / "submission.tar.gz"
    submission.unlink(missing_ok=True)
    traj = instance_dir / "traj.json"

    container_task = "".join(c if c.isalnum() else "-" for c in args.task)
    container_name = f"programbench-codex-{container_task}-{os.getpid()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="programbench-codex-"))
    prompt_file = temp_dir / "prompt.txt"
    raw_stdout = temp_dir / "stdout.jsonl"
    raw_stderr = temp_dir / "stderr.txt"
    prompt_file.write_text(solve_prompt(args.mode))

    try:
        cleanroom_source = stage_cleanroom(
            cleanroom_source, temp_dir / "cleanroom", with_executable=args.mode == "with-executable"
        )
        sanitized_test_suite = prepare_test_suite_archive(test_suite_source, temp_dir)
        started = time.time()
        run_status = run_container(
            args=args,
            image=image,
            container_name=container_name,
            prompt_file=prompt_file,
            cleanroom_source=cleanroom_source,
            test_suite_source=sanitized_test_suite,
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
        )
        finished = time.time()
        log.info("Finished Codex session with status %d", run_status)
        copy_submission(container_name, submission)
        if run_status == 0:
            build_ok, build_output = verify_fresh_offline_build(
                submission,
                image,
                docker_cpus=args.docker_cpus,
            )
            if not build_ok:
                message = f"Fresh offline build verification failed: {build_output}"
                print(message, file=sys.stderr)
                with raw_stderr.open("a") as stderr_file:
                    stderr_file.write("\n" + message + "\n")
                run_status = 1
        write_trajectory(
            args=args,
            image=image,
            submission=submission,
            traj=traj,
            prompt_file=prompt_file,
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
            run_status=run_status,
        )
        record_timing(traj, started, finished)
        if run_status != 0:
            print(f"Codex run exited with status {run_status}", file=sys.stderr)
        return run_status
    finally:
        cleanup(container_name, temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
