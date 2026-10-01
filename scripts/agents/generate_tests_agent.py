#!/usr/bin/env python3
"""Use a headless coding harness to generate a ProgramBench test suite."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tarfile
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import generate_tests_claude
import solve_agent
from programbench.test_generation import _codex_test_generation_prompt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Use a headless coding agent to generate a ProgramBench-compatible test suite. "
            "Output is compatible with: uv run programbench eval-tests <output>"
        ),
        formatter_class=solve_agent.common.DefaultsFormatter,
    )
    parser.add_argument("--agent", choices=sorted(solve_agent.AGENTS), required=True, help="Agent CLI to run")
    parser.add_argument("--model", default="", help="Model ID exactly as the agent CLI expects it (default: per agent)")
    parser.add_argument("--reasoning", default="high", help="Reasoning effort; recorded for agents without an effort flag")
    parser.add_argument("--task", default=solve_agent.common.DEFAULT_TASK, help="Task instance ID")
    parser.add_argument("--output", default="", help="Output run directory (default: output/test-suites/<agent>)")
    parser.add_argument("--cleanroom", required=True, help="Specification root with layout <cleanroom>/<task>/")
    parser.add_argument("--reference-executable", type=Path, help="Reference executable to provide alongside the spec")
    parser.add_argument("--base-tag", default=solve_agent.common.DEFAULT_BASE_TAG, help="Source task cleanroom tag")
    parser.add_argument("--tag-suffix", default="", help="Agent image tag suffix (default: the agent name)")
    parser.add_argument("--cleanroom-base-image", default="", help="Prebuilt agent-enabled task image")
    parser.add_argument("--agent-command", default="", help="Agent command prefix (default: per agent)")
    parser.add_argument(
        "--stdout-aggregated-output-limit",
        type=int,
        default=solve_agent.common.DEFAULT_STDOUT_PASSTHROUGH_LIMIT,
        help="Max chars printed for non-JSON agent output lines",
    )
    parser.add_argument("--timeout", type=int, default=3600, help="Docker timeout in seconds")
    parser.add_argument("--docker-cpus", type=int, default=4, help="CPU cores allotted to the container")
    args = parser.parse_args()
    args.model = args.model or solve_agent.AGENTS[args.agent].default_model
    args.output = args.output or f"output/test-suites/{args.agent}"
    args.tag_suffix = args.tag_suffix or args.agent
    args.agent_command = args.agent_command or solve_agent.AGENTS[args.agent].command
    return args


def main() -> int:
    solve_agent.common.install_shutdown_handlers()
    args = parse_args()
    agent = solve_agent.AGENTS[args.agent]
    model = args.model
    if args.reference_executable and not args.reference_executable.is_file():
        raise SystemExit(f"Reference executable is missing: {args.reference_executable}")
    cleanroom_source = solve_agent.common.resolve_cleanroom_source(args.cleanroom, args.task)
    assert cleanroom_source is not None
    solve_agent.auth_preflight(agent)
    solve_agent.common.docker_preflight()
    solve_agent.common.agent_network_preflight()
    image = solve_agent.ensure_cleanroom_image(args)

    instance_dir = Path(args.output) / args.task
    instance_dir.mkdir(parents=True, exist_ok=True)
    tests_archive = instance_dir / "tests.tar.gz"
    tests_archive.unlink(missing_ok=True)
    traj = instance_dir / f"{args.task}.traj.json"
    container_task = "".join(c if c.isalnum() else "-" for c in args.task)
    container_name = f"programbench-{args.agent}-tests-{container_task}-{os.getpid()}"
    temp_dir = Path(tempfile.mkdtemp(prefix=f"programbench-{args.agent}-tests-"))
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
        cleanroom_source = solve_agent.common.stage_cleanroom(cleanroom_source, temp_dir / "cleanroom")
        started = time.time()
        docker_args = solve_agent.build_docker_args(
            agent, container_name, prompt_file, cleanroom_source, None, args.docker_cpus, model, args.reasoning
        )
        if args.reference_executable:
            args.reference_executable = solve_agent.common.stage_reference(
                args.reference_executable.resolve(), temp_dir / "reference-executable"
            )
            docker_args += ["-v", f"{args.reference_executable.resolve()}:/tmp/programbench_reference_executable:ro"]
        run_status = solve_agent.run_container(
            args=args,
            image=image,
            docker_args=docker_args,
            container_script=generate_tests_claude.build_container_script(
                solve_agent.command_prefix(agent, args.agent_command, model, args.reasoning),
                "",
                "",
                with_executable=bool(args.reference_executable),
            ),
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
        )
        finished = time.time()
        if run_status == 0 and not generate_tests_claude.copy_tests(container_name, tests_archive):
            run_status = 1
        if tests_archive.is_file():
            extract_dir = instance_dir / "tests_untar"
            shutil.rmtree(extract_dir, ignore_errors=True)
            with tarfile.open(tests_archive, "r:gz") as archive:
                archive.extractall(extract_dir, filter="data")
            print(f"Extracted generated tests to {extract_dir}")
        solve_agent.write_trajectory(
            args=args,
            image=image,
            container_name=container_name,
            artifact=tests_archive,
            traj=traj,
            prompt_file=prompt_file,
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
            run_status=run_status,
        )
        solve_agent.common.record_timing(traj, started, finished)
        if run_status != 0:
            print(f"{args.agent} test-generation run exited with status {run_status}", file=sys.stderr)
        return run_status
    finally:
        solve_agent.common.cleanup(container_name, temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
