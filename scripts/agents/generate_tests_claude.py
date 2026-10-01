#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Use Claude Code to generate a ProgramBench test suite from a specification."""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import solve_claude
from programbench.archive_limits import bounded_archive_command
from programbench.test_generation import ARCHIVE_EXCLUDED_DIRS, _codex_test_generation_prompt


DEFAULT_OUTPUT = "output/test-suites/claude"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Use Claude Code to generate a ProgramBench-compatible test suite. "
            "Output is compatible with: uv run programbench eval-tests <output>"
        ),
        formatter_class=solve_claude.common.DefaultsFormatter,
    )
    parser.add_argument("--model", default=solve_claude.DEFAULT_MODEL, help="Claude model or alias")
    parser.add_argument("--effort", default=solve_claude.DEFAULT_EFFORT, help="Claude effort level; empty omits it")
    parser.add_argument("--task", default=solve_claude.DEFAULT_TASK, help="Task instance ID")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output run directory")
    parser.add_argument(
        "--cleanroom",
        required=True,
        help="Specification root with layout <cleanroom>/<task>/",
    )
    parser.add_argument("--reference-executable", type=Path, help="Reference executable to provide alongside the spec")
    parser.add_argument("--base-tag", default=solve_claude.DEFAULT_BASE_TAG, help="Source task cleanroom tag")
    parser.add_argument("--tag-suffix", default=solve_claude.DEFAULT_TAG_SUFFIX, help="Claude image tag suffix")
    parser.add_argument("--cleanroom-base-image", default="", help="Prebuilt Claude-enabled task image")
    parser.add_argument(
        "--claude-command",
        default=solve_claude.DEFAULT_CLAUDE_COMMAND,
        help="Claude command prefix",
    )
    parser.add_argument(
        "--stdout-aggregated-output-limit",
        type=int,
        default=solve_claude.DEFAULT_STDOUT_PASSTHROUGH_LIMIT,
        help="Max chars printed for non-JSON Claude output lines",
    )
    parser.add_argument("--timeout", type=int, default=3600, help="Docker timeout in seconds")
    parser.add_argument("--docker-cpus", type=int, default=4, help="CPU cores allotted to the container")
    return parser.parse_args()


def build_container_script(command_prefix: str, model: str, effort: str, *, with_executable: bool = False) -> str:
    validation_script = (
        "import xml.etree.ElementTree as ET; "
        "root = ET.parse('/workspace/eval/results.xml').getroot(); "
        "root_tag = root.tag.rsplit('}', 1)[-1]; "
        "assert root_tag in {'testsuite', 'testsuites'}, f'not JUnit XML: {root_tag}'; "
        "count = sum(1 for element in root.iter() "
        "if element.tag.rsplit('}', 1)[-1] == 'testcase'); "
        "assert count > 0, 'JUnit XML contains no testcases'"
    )
    executable_setup = (
        "install -m 755 /tmp/programbench_reference_executable /workspace/executable"
        if with_executable else "rm -f /workspace/executable\n" + solve_claude.common.reference_cleanup_command()
    )
    script = f"""set -euo pipefail
claude_model={shlex.quote(model)}
effort={shlex.quote(effort)}
find /workspace -mindepth 1 -maxdepth 1 -exec rm -rf {{}} +
tar -C /tmp/programbench_cleanroom --exclude=./executable --exclude=executable -cf - . | tar -C /workspace -xf -
{executable_setup}
prompt=$(cat /tmp/programbench_prompt.txt)
cmd=({command_prefix})
if [ -n "$claude_model" ]; then
    cmd+=(--model "$claude_model")
fi
if [ -n "$effort" ]; then
    cmd+=(--effort "$effort")
fi
cmd+=("$prompt")
"${{cmd[@]}}"
test -x /workspace/eval/run.sh
cd /workspace/eval
rm -f results.xml
set +e
./run.sh >/tmp/programbench_run_sh.log 2>&1
set -e
# Validate the generated JUnit file without mixing postflight text into agent JSONL.
python3 -c {shlex.quote(validation_script)}
# pytest's tmp factory leaves absolute `...current` symlinks in eval/. Python's
# safe tar extractor rejects those links, and none are part of the test suite.
find . -type l -lname '/*' -delete
{bounded_archive_command(ARCHIVE_EXCLUDED_DIRS, workspace="/workspace", archive_path="/tmp/tests.tar.gz", members=("eval",))}
"""

    return solve_claude.common.guard_reference_session(script, enabled=with_executable)


def run_container(
    *,
    args: argparse.Namespace,
    image: str,
    container_name: str,
    prompt_file: Path,
    cleanroom_source: Path,
    raw_stdout: Path,
    raw_stderr: Path,
) -> int:
    docker_args = solve_claude.build_docker_args(
        container_name, prompt_file, cleanroom_source, None, args.docker_cpus
    )
    if args.reference_executable:
        docker_args += ["-v", f"{args.reference_executable.resolve()}:/tmp/programbench_reference_executable:ro"]
    command = [
        "timeout", str(args.timeout), solve_claude.common.docker(), *docker_args,
        image, "bash", "-lc",
        build_container_script(
            args.claude_command, solve_claude.claude_model(args.model), args.effort,
            with_executable=bool(args.reference_executable),
        ),
    ]
    with raw_stdout.open("w", buffering=1) as stdout_file, raw_stderr.open("w") as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=solve_claude.common.repo_root(),
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            stdout_file.write(line)
            stdout_file.flush()
            sys.stdout.write(solve_claude.display_event(line, args.stdout_aggregated_output_limit))
            sys.stdout.flush()
        return process.wait()


def copy_tests(container_name: str, destination: Path) -> bool:
    result = subprocess.run(
        [
            solve_claude.common.docker(),
            "cp",
            f"{container_name}:/tmp/tests.tar.gz",
            str(destination),
        ],
        cwd=solve_claude.common.repo_root(),
    )
    if result.returncode == 0:
        print(f"Saved generated tests to {destination}")
        return True
    print(f"Failed to copy generated tests from {container_name}", file=sys.stderr)
    return False


def write_trajectory(
    *,
    args: argparse.Namespace,
    image: str,
    tests_archive: Path,
    traj: Path,
    prompt_file: Path,
    raw_stdout: Path,
    raw_stderr: Path,
    run_status: int,
) -> None:
    python = solve_claude.common.trajectory_python()
    if not python:
        print("uv and python3 not found; skipped Claude trajectory generation", file=sys.stderr)
        return
    result = subprocess.run(
        [
            *python,
            "scripts/agents/claude_jsonl_to_traj.py",
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
            "ok" if run_status == 0 else "claude_failed",
            "--returncode",
            str(run_status),
            "--model",
            solve_claude.claude_model(args.model),
            "--effort",
            args.effort,
            "--image",
            image,
            "--claude-command",
            args.claude_command,
            "--output",
            str(tests_archive),
        ],
        cwd=solve_claude.common.repo_root(),
    )
    if result.returncode == 0:
        print(f"Saved Claude trajectory to {traj}")
    else:
        print("Failed to write Claude trajectory", file=sys.stderr)


def main() -> int:
    solve_claude.common.install_shutdown_handlers()
    args = parse_args()
    if args.reference_executable and not args.reference_executable.is_file():
        raise SystemExit(f"Reference executable is missing: {args.reference_executable}")
    cleanroom_source = solve_claude.common.resolve_cleanroom_source(args.cleanroom, args.task)
    assert cleanroom_source is not None
    solve_claude.common.docker_preflight()
    solve_claude.common.agent_network_preflight()
    image = solve_claude.ensure_cleanroom_image(args)

    instance_dir = Path(args.output) / args.task
    instance_dir.mkdir(parents=True, exist_ok=True)
    tests_archive = instance_dir / "tests.tar.gz"
    tests_archive.unlink(missing_ok=True)
    traj = instance_dir / f"{args.task}.traj.json"
    container_task = "".join(c if c.isalnum() else "-" for c in args.task)
    container_name = f"programbench-claude-tests-{container_task}-{os.getpid()}"
    temp_dir = Path(tempfile.mkdtemp(prefix="programbench-claude-tests-"))
    prompt_file = temp_dir / "prompt.txt"
    raw_stdout = temp_dir / "stdout.jsonl"
    raw_stderr = temp_dir / "stderr.txt"
    prompt_file.write_text(
        _codex_test_generation_prompt(
            with_executable=bool(args.reference_executable),
            official_huge=Path(args.cleanroom).resolve().name in {"official-huge", "official-huge-pinned"},
        )
    )

    try:
        cleanroom_source = solve_claude.common.stage_cleanroom(cleanroom_source, temp_dir / "cleanroom")
        if args.reference_executable:
            args.reference_executable = solve_claude.common.stage_reference(
                args.reference_executable.resolve(), temp_dir / "reference-executable"
            )
        started = time.time()
        run_status = run_container(
            args=args,
            image=image,
            container_name=container_name,
            prompt_file=prompt_file,
            cleanroom_source=cleanroom_source,
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
        )
        finished = time.time()
        if run_status == 0 and not copy_tests(container_name, tests_archive):
            run_status = 1
        if tests_archive.is_file():
            extract_dir = instance_dir / "tests_untar"
            shutil.rmtree(extract_dir, ignore_errors=True)
            with tarfile.open(tests_archive, "r:gz") as archive:
                archive.extractall(extract_dir, filter="data")
            print(f"Extracted generated tests to {extract_dir}")
        write_trajectory(
            args=args,
            image=image,
            tests_archive=tests_archive,
            traj=traj,
            prompt_file=prompt_file,
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
            run_status=run_status,
        )
        solve_claude.common.record_timing(traj, started, finished)
        if run_status != 0:
            print(f"Claude test-generation run exited with status {run_status}", file=sys.stderr)
        return run_status
    finally:
        solve_claude.common.cleanup(container_name, temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
