#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Convert Codex CLI JSONL output into a ProgramBench trajectory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from programbench.codex import build_codex_shell_command
from programbench.spec_improvement import _codex_completed_event
from programbench.test_generation import _write_codex_trajectory


def _load_completed_events(raw_stdout: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with raw_stdout.open(errors="replace") as source:
        for line in source:
            event = _codex_completed_event(line)
            if event is None:
                continue
            events.append(event)
    return events


def _codex_shell_command(command_prefix: str, *, model: str, reasoning: str, prompt: str) -> str:
    return build_codex_shell_command(
        command_prefix,
        prompt=prompt,
        model=model,
        reasoning_effort=reasoning,
        diagnostic_action="write solve trajectory",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-stdout", type=Path, required=True)
    parser.add_argument("--raw-stderr", type=Path, required=True)
    parser.add_argument("--traj", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--returncode", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--codex-command", required=True)
    parser.add_argument("--reasoning", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    prompt = args.prompt_file.read_text()
    events = _load_completed_events(args.raw_stdout)
    raw_stdout = args.raw_stdout.read_text(errors="replace")
    raw_stderr = args.raw_stderr.read_text(errors="replace")
    _write_codex_trajectory(
        path=args.traj,
        instance_id=args.instance_id,
        prompt=prompt,
        events=events,
        status={
            "status": args.status,
            "returncode": args.returncode,
            "exception_info": "",
            "output": args.output,
            "reason": None,
            "stdout": raw_stdout,
            "stderr": raw_stderr,
        },
        info={
            "image": args.image,
            "model": args.model,
            "reasoning": args.reasoning,
            "codex_command": args.codex_command,
            "codex_shell_command": _codex_shell_command(
                args.codex_command,
                model=args.model,
                reasoning=args.reasoning,
                prompt=prompt,
            ),
        },
    )


if __name__ == "__main__":
    main()
