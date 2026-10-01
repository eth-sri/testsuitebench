#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Convert Claude Code stream-json output into a ProgramBench trajectory."""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any


def load_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def block_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return json.dumps(content, ensure_ascii=False)
    return "\n".join(
        block.get("text", "") if isinstance(block, dict) else str(block)
        for block in content
    )


def trajectory_messages(prompt: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), list):
            continue
        if event.get("type") == "assistant":
            text_blocks = [
                block["text"]
                for block in message["content"]
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            tool_blocks = [
                block
                for block in message["content"]
                if isinstance(block, dict) and block.get("type") == "tool_use"
            ]
            if text_blocks:
                messages.append({"role": "assistant", "content": "\n".join(text_blocks)})
            if tool_blocks:
                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": block.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                                },
                            }
                            for block in tool_blocks
                        ],
                    }
                )
        elif event.get("type") == "user":
            for block in message["content"]:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": block.get("tool_use_id", ""),
                        "content": block_text(block.get("content", "")),
                        "extra": {"is_error": bool(block.get("is_error", False))},
                    }
                )
    return messages


def result_usage(events: list[dict[str, Any]]) -> dict[str, Any]:
    result = next((event for event in reversed(events) if event.get("type") == "result"), {})
    usage = result.get("usage", {})
    # A killed run has no result event; reporting zeros would look like a real measurement.
    if not isinstance(usage, dict) or not usage:
        return {}
    input_tokens = int(usage.get("input_tokens", 0))
    cached = int(usage.get("cache_read_input_tokens", 0))
    cache_write = int(usage.get("cache_creation_input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    return {
        **usage,
        "cached_input_tokens": cached,
        "cache_write_input_tokens": cache_write,
        "total_tokens": input_tokens + cached + cache_write + output_tokens,
        "uncached_input_tokens": input_tokens,
        "uncached_input_plus_output_tokens": input_tokens + output_tokens,
    }


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
    parser.add_argument("--effort", default="")
    parser.add_argument("--image", required=True)
    parser.add_argument("--claude-command", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    prompt = args.prompt_file.read_text()
    events = load_events(args.raw_stdout)
    command = shlex.join(
        [
            *shlex.split(args.claude_command),
            "--model",
            args.model,
            "--effort",
            args.effort,
            prompt,
        ]
    )
    trajectory = {
        "info": {
            "exit_status": args.status,
            "returncode": args.returncode,
            "exception_info": "",
            "output": args.output,
            "reason": None,
            "image": args.image,
            "model": args.model,
            "effort": args.effort,
            "claude_command": args.claude_command,
            "claude_shell_command": command,
        },
        "instance_id": args.instance_id,
        "usage": result_usage(events),
        "usage_calls": 1 if any(event.get("type") == "result" for event in events) else 0,
        "messages": trajectory_messages(prompt, events),
        "claude_json_events": events,
        "claude_output": {
            "stdout": args.raw_stdout.read_text(errors="replace"),
            "stderr": args.raw_stderr.read_text(errors="replace"),
        },
    }
    args.traj.write_text(json.dumps(trajectory, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
