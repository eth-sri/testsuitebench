#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Run Claude Code on a ProgramBench solve task."""

from __future__ import annotations

import argparse
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import solve_codex as common


DEFAULT_MODEL = "claude/sonnet"
DEFAULT_EFFORT = "high"
DEFAULT_TASK = common.DEFAULT_TASK
DEFAULT_BASE_TAG = common.DEFAULT_BASE_TAG
DEFAULT_TAG_SUFFIX = "claude"
DEFAULT_MODE = "spec-only"
DEFAULT_TIMEOUT_SECONDS = common.DEFAULT_TIMEOUT_SECONDS
DEFAULT_STDOUT_PASSTHROUGH_LIMIT = common.DEFAULT_STDOUT_PASSTHROUGH_LIMIT
DEFAULT_CLAUDE_COMMAND = (
    "claude --dangerously-skip-permissions --print --verbose "
    "--output-format stream-json --no-session-persistence "
    "--disallowedTools WebSearch,WebFetch"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Claude Code on a ProgramBench solve task. "
            "Output is compatible with: uv run programbench eval <output>"
        ),
        formatter_class=common.DefaultsFormatter,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Claude model or alias to use")
    parser.add_argument("--effort", default=DEFAULT_EFFORT, help="Claude effort level")
    parser.add_argument("--task", default=DEFAULT_TASK, help="Task instance ID")
    parser.add_argument(
        "--output",
        default="",
        help="Output directory (default: output/executable/<model>-<effort>-<mode>)",
    )
    parser.add_argument("--mode", choices=common.VALID_MODES, default=DEFAULT_MODE, help="Solve mode")
    parser.add_argument("--test-suite", default="", help="Generated test suite for with-test modes")
    parser.add_argument(
        "--cleanroom",
        default="",
        help="Local cleanroom root. Expected layout: <cleanroom>/<task>/",
    )
    parser.add_argument("--base-tag", default=DEFAULT_BASE_TAG, help="Source task cleanroom tag")
    parser.add_argument("--tag-suffix", default=DEFAULT_TAG_SUFFIX, help="Claude image tag suffix")
    parser.add_argument("--cleanroom-base-image", default="", help="Prebuilt Claude-enabled task image")
    parser.add_argument("--claude-command", default=DEFAULT_CLAUDE_COMMAND, help="Claude command prefix")
    parser.add_argument(
        "--stdout-aggregated-output-limit",
        type=int,
        default=DEFAULT_STDOUT_PASSTHROUGH_LIMIT,
        help="Max chars printed for non-JSON Claude output lines",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Docker timeout in seconds")
    parser.add_argument("--docker-cpus", type=int, default=4, help="CPU cores allotted to the container")
    return parser.parse_args()


def claude_model(model: str) -> str:
    return model.removeprefix("claude/")


def output_dir(args: argparse.Namespace, test_suite_source: Path | None = None) -> Path:
    if args.output:
        return Path(args.output)
    output = Path("output") / "executable" / f"{args.model}-{args.effort}-{args.mode}"
    if common.is_with_test_mode(args.mode) and test_suite_source is not None:
        return output / common.test_suite_output_label(test_suite_source, args.task)
    return output


def resolve_test_suite_source(args: argparse.Namespace) -> Path | None:
    compatible_args = argparse.Namespace(**vars(args), reasoning=args.effort)
    return common.resolve_test_suite_source(compatible_args)


def solve_prompt(mode: str) -> str:
    if mode == "spec-only":
        return common.PROMPT_SPEC_ONLY
    if common.is_with_test_mode(mode):
        return common.CODEX_GOAL_WITH_TEST
    return common.PROMPT_WITH_EXECUTABLE


def ensure_cleanroom_image(args: argparse.Namespace) -> str:
    if args.cleanroom_base_image:
        print(f"Using Claude Code cleanroom image: {args.cleanroom_base_image}")
        return args.cleanroom_base_image

    installer = common.repo_root() / "scripts" / "docker" / "install_claude_cleanroom.sh"
    options = ["--task", args.task, "--base-tag", args.base_tag, "--tag-suffix", args.tag_suffix]
    image = subprocess.check_output([str(installer), *options, "--print-image"], cwd=common.repo_root(), text=True).strip()
    subprocess.run([str(installer), *options], cwd=common.repo_root(), check=True)
    return image


def build_docker_args(
    container_name: str,
    prompt_file: Path,
    cleanroom_source: Path | None,
    test_suite_source: Path | None,
    docker_cpus: int = 20,
) -> list[str]:
    args = common.build_docker_args(
        container_name,
        prompt_file,
        cleanroom_source,
        test_suite_source,
        docker_cpus,
    )
    codex_auth_mount = next(
        (index for index, value in enumerate(args) if value.endswith(":/root/.codex/auth.json:ro")),
        None,
    )
    if codex_auth_mount is not None:
        del args[codex_auth_mount - 1 : codex_auth_mount + 1]
    while "OPENAI_API_KEY" in args:
        index = args.index("OPENAI_API_KEY")
        del args[index - 1 : index + 1]

    selected_credentials = os.environ.get("PROGRAMBENCH_CLAUDE_CREDENTIALS_FILE")
    credentials = (
        Path(selected_credentials)
        if selected_credentials
        else Path.home() / ".claude" / ".credentials.json"
    )
    if selected_credentials and not credentials.is_file():
        raise FileNotFoundError(f"Selected Claude credentials file does not exist: {credentials}")
    # Precedence: an explicitly selected credentials file, then CLAUDE_CODE_OAUTH_TOKEN,
    # then ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN, then the default ~/.claude login.
    # Only the first one found goes into the container, so a stale lower-priority
    # credential can never be the one that is silently used.
    use_oauth_token = bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) and not selected_credentials
    use_api_key = (
        bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
        and not selected_credentials
        and not use_oauth_token
    )
    if selected_credentials:
        source = f"selected credentials file {credentials}"
    elif use_oauth_token:
        source = "CLAUDE_CODE_OAUTH_TOKEN"
    elif os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        source = "ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN"
    elif credentials.is_file():
        source = f"login file {credentials}"
    else:
        source = "none found"
    print(f"[claude] credentials: {source}", flush=True)
    if credentials.is_file() and not use_oauth_token and not use_api_key:
        args.extend(["-v", f"{credentials}:/tmp/programbench-claude-config/.credentials.json:ro"])

    # Explicit file selection must also select the authentication source. Claude
    # otherwise prefers these inherited environment credentials over the mount.
    for name in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
    ):
        if selected_credentials and name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"):
            continue
        if use_oauth_token and name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            continue
        if os.environ.get(name):
            args.extend(["-e", name])
    return args


def build_container_script(mode: str, command_prefix: str, model: str, effort: str) -> str:
    script = f"""set -euo pipefail
mode={shlex.quote(mode)}
claude_model={shlex.quote(model)}
effort={shlex.quote(effort)}
{common.solve_workspace_setup(mode)}
if [ "$mode" = "with-test" ] || [ "$mode" = "with-test-force" ]; then
    if [ ! -f /tmp/programbench_tests.tar.gz ]; then
        echo "with-test modes require a generated test suite" >&2
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
    rm -f "$suite_dir/executable"
    ln -s /workspace/executable "$suite_dir/executable"
    if ! (cd "$suite_dir" && EXECUTABLE=/workspace/executable bash "$run_script"); then
        overall_status=1
    fi
done
exit "$overall_status"
PROGRAMBENCH_RUN_TESTS
    chmod +x /workspace/run_generated_tests.sh
fi
prompt=$(cat /tmp/programbench_prompt.txt)
cmd=({command_prefix})
if [ -n "$claude_model" ]; then
    cmd+=(--model "$claude_model")
fi
if [ -n "$effort" ]; then
    cmd+=(--effort "$effort")
fi
cmd+=("$prompt")
set +e
"${{cmd[@]}}"
status=$?
set -e
{common.submission_archive_command(("./executable", "./.programbench-generated-tests", "./run_generated_tests.sh", "./results.xml"))}
exit "$status"
"""

    return common.guard_reference_session(script, enabled=mode == "with-executable")


# One compact line per assistant message and tool call. The full stream-json is
# already captured in stdout.jsonl; this only exists so a multi-hour solve shows
# a pulse instead of a blank terminal.
PROGRESS_LINE_LIMIT = 160


def display_event(line: str, limit: int) -> str:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        event = None
    # The container also prints non-event output on this stream (run.sh, and the
    # bare testcase count from the JUnit validation step). A line like "42" parses
    # as JSON but is not an event, so isinstance must be checked, not just decode.
    if not isinstance(event, dict):
        return common.truncate(line.rstrip(), limit) + "\n"
    message = event.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), list):
        return ""
    progress = ""
    for block in message["content"]:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            summary = " ".join(block["text"].split())
        elif block.get("type") == "tool_use":
            argument = block["input"].get("command") or block["input"].get("file_path") or block["input"].get("pattern") or ""
            summary = f"[{block['name']}] {' '.join(str(argument).split())}".rstrip()
        else:
            continue
        if summary:
            progress += summary[:PROGRESS_LINE_LIMIT] + ("...\n" if len(summary) > PROGRESS_LINE_LIMIT else "\n")
    return progress


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
        common.docker(),
        *build_docker_args(container_name, prompt_file, cleanroom_source, test_suite_source, args.docker_cpus),
        image,
        "bash",
        "-lc",
        build_container_script(args.mode, args.claude_command, claude_model(args.model), args.effort),
    ]
    with raw_stdout.open("w", buffering=1) as stdout_file, raw_stderr.open("w") as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=common.repo_root(),
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
    python = common.trajectory_python()
    if not python:
        print("uv and python3 not found; skipped Claude trajectory generation", file=sys.stderr)
        return
    result = subprocess.run(
        [
            *python,
            "scripts/agents/claude_jsonl_to_traj.py",
            "--raw-stdout", str(raw_stdout),
            "--raw-stderr", str(raw_stderr),
            "--traj", str(traj),
            "--prompt-file", str(prompt_file),
            "--instance-id", args.task,
            "--status", "ok" if run_status == 0 else "claude_failed",
            "--returncode", str(run_status),
            "--model", claude_model(args.model),
            "--effort", args.effort,
            "--image", image,
            "--claude-command", args.claude_command,
            "--output", str(submission),
        ],
        cwd=common.repo_root(),
    )
    if result.returncode == 0:
        print(f"Saved Claude trajectory to {traj}")
    else:
        print("Failed to write Claude trajectory", file=sys.stderr)


def main() -> int:
    common.install_shutdown_handlers()
    logging.basicConfig(level=logging.INFO, format=common.LOG_FORMAT)
    args = parse_args()
    test_suite_source = resolve_test_suite_source(args)
    out_dir = output_dir(args, test_suite_source)
    cleanroom_source = common.resolve_cleanroom_source(args.cleanroom, args.task)

    common.docker_preflight()
    common.agent_network_preflight()
    image = ensure_cleanroom_image(args)

    instance_dir = out_dir / args.task
    instance_dir.mkdir(parents=True, exist_ok=True)
    submission = instance_dir / "submission.tar.gz"
    submission.unlink(missing_ok=True)
    traj = instance_dir / "traj.json"
    container_task = "".join(c if c.isalnum() else "-" for c in args.task)
    container_name = f"programbench-claude-{container_task}-{os.getpid()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="programbench-claude-"))
    prompt_file = temp_dir / "prompt.txt"
    raw_stdout = temp_dir / "stdout.jsonl"
    raw_stderr = temp_dir / "stderr.txt"
    prompt_file.write_text(solve_prompt(args.mode))

    try:
        cleanroom_source = common.stage_cleanroom(
            cleanroom_source, temp_dir / "cleanroom", with_executable=args.mode == "with-executable"
        )
        sanitized_test_suite = common.prepare_test_suite_archive(test_suite_source, temp_dir)
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
        common.copy_submission(container_name, submission)
        if submission.is_file():
            extract_dir = instance_dir / "submission_untar"
            shutil.rmtree(extract_dir, ignore_errors=True)
            with tarfile.open(submission, "r:gz") as archive:
                archive.extractall(extract_dir, filter="data")
            print(f"Extracted submission to {extract_dir}")
        if run_status == 0:
            build_ok, build_output = common.verify_fresh_offline_build(submission, image, docker_cpus=args.docker_cpus)
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
        common.record_timing(traj, started, finished)
        if run_status != 0:
            print(f"Claude run exited with status {run_status}", file=sys.stderr)
        return run_status
    finally:
        common.cleanup(container_name, temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
