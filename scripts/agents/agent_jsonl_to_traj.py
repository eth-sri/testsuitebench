#!/usr/bin/env python3
"""Convert headless coding harness JSONL output into a ProgramBench trajectory."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_jsonl_to_traj as claude


def tool_call(call_id: str, name: str, arguments: Any) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
            }
        ],
    }


def tool_result(call_id: str, content: Any, is_error: bool) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": claude.block_text(content),
        "extra": {"is_error": is_error},
    }


# muse exec --json records the shell command only inside the tool result text,
# so the tool call carries the name and id but no arguments.
def muse_messages(prompt: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    text = ""
    for event in events:
        payload = event.get("payload", {})
        if event.get("payload_type") == "run.output.delta":
            text += payload["text"]
        elif event.get("payload_type") == "tool.result":
            if text:
                messages.append({"role": "assistant", "content": text})
                text = ""
            # Background-running results do not carry correlation_facts in
            # Muse 1.3.  They are still valid tool results and must not make
            # trajectory conversion (and therefore run accounting) fail.
            facts = payload.get("correlation_facts") or {}
            call_id = payload.get("call_id") or event.get("id", "unknown-tool-call")
            messages.append(tool_call(call_id, facts.get("tool_name", "tool"), {}))
            messages.append(tool_result(call_id, payload.get("text", ""), facts.get("outcome") == "failure"))
    if text:
        messages.append({"role": "assistant", "content": text})
    return messages


def gemini_messages(prompt: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    for event in events:
        if event.get("type") == "message" and event.get("role") == "assistant":
            if messages[-1]["role"] == "assistant" and isinstance(messages[-1]["content"], str):
                messages[-1]["content"] += event["content"]
            else:
                messages.append({"role": "assistant", "content": event["content"]})
        elif event.get("type") == "tool_use":
            messages.append(tool_call(event["tool_id"], event["tool_name"], event["parameters"]))
        elif event.get("type") == "tool_result":
            # Both fields are optional: output only exists for string results, error only on failure.
            error = event.get("error")
            content = event.get("output") or (error["message"] if error else "")
            messages.append(tool_result(event["tool_id"], content, event["status"] == "error"))
    return messages


def gemini_usage(events: list[dict[str, Any]]) -> dict[str, Any]:
    result = next((event for event in reversed(events) if event.get("type") == "result"), {})
    return dict(result.get("stats", {}))


# muse exec --json carries no token counts; its session log records one
# model_completed event per model call.
def muse_usage(session_logs: Path | None) -> dict[str, Any]:
    calls = [
        record["payload"]["event"]["usage"]
        for log in (session_logs.rglob("session.jsonl") if session_logs else [])
        for record in claude.load_events(log)
        if record.get("payload_type") == "runtime.session" and record["payload"].get("event", {}).get("kind") == "model_completed"
    ]
    if not calls:
        return {}
    usage = {key: sum(call[key] for call in calls) for key in ("input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens")}
    return {**usage, "total_tokens": usage["input_tokens"] + usage["output_tokens"], "model_calls": len(calls)}


def deepseek_session_events(session_logs: Path | None) -> list[dict[str, Any]]:
    """The headless DSH profile prints plain text; its full events are zstd JSONL."""
    events: list[dict[str, Any]] = []
    for log in sorted(session_logs.rglob("session.v3.jsonl.zstd") if session_logs and session_logs.exists() else []):
        data = subprocess.run(["zstd", "-dc", str(log)], capture_output=True, text=True, check=True).stdout
        events.extend(json.loads(line) for line in data.splitlines() if line)
    return events


def deepseek_messages(prompt: str, events: list[dict[str, Any]], final_stdout: str = "") -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    for event in events:
        kind = event.get("type")
        data = event.get("data") or {}
        if kind == "assistant/message":
            blocks = data.get("message", {}).get("content", [])
            content = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
            if content:
                messages.append({"role": "assistant", "content": content})
        elif kind == "tool/call":
            arguments = data.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    pass
            messages.append(tool_call(str(data.get("callId", "")), str(data.get("name", "tool")), arguments))
        elif kind == "tool/result":
            blocks = data.get("message", {}).get("content", [])
            for block in blocks:
                if block.get("type") == "tool-result":
                    content = "".join(part.get("text", "") for part in block.get("content", [])
                                      if isinstance(part, dict) and part.get("type") == "text")
                    messages.append(tool_result(str(block.get("toolCallId", "")), content, bool(block.get("isError"))))
    if len(messages) == 1 and final_stdout.strip():
        messages.append({"role": "assistant", "content": final_stdout.strip()})
    return messages


def deepseek_usage(events: list[dict[str, Any]]) -> dict[str, Any]:
    samples = [
        event["data"]["usage"] for event in events
        if event.get("type") == "assistant/message"
        and isinstance(event.get("data", {}).get("usage"), dict)
    ]
    if not samples:
        return {}
    usage = {
        "input_tokens": sum(sample.get("inputTokens", 0) for sample in samples),
        "output_tokens": sum(sample.get("outputTokens", 0) for sample in samples),
        "cache_read_input_tokens": sum(sample.get("cacheReadTokens", 0) for sample in samples),
        "cache_creation_input_tokens": sum(sample.get("cacheWriteTokens", 0) for sample in samples),
        "model_calls": len(samples),
    }
    usage["total_tokens"] = sum(
        sample.get("totalTokens", sample.get("inputTokens", 0) + sample.get("outputTokens", 0)
                   + sample.get("cacheReadTokens", 0) + sample.get("cacheWriteTokens", 0))
        for sample in samples
    )
    return usage


def glm_messages(prompt: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    result = next((event for event in reversed(events) if "response" in event), None)
    if result and isinstance(result.get("response"), str):
        messages.append({"role": "assistant", "content": result["response"]})
    return messages


def glm_usage(events: list[dict[str, Any]]) -> dict[str, Any]:
    result = next((event for event in reversed(events) if "response" in event), {})
    sample = result.get("usage")
    if not isinstance(sample, dict):
        return {}
    return {
        "input_tokens": sample.get("inputTokens", 0),
        "output_tokens": sample.get("outputTokens", 0),
        "total_tokens": sample.get("totalTokens", sample.get("inputTokens", 0) + sample.get("outputTokens", 0)),
        "cache_read_input_tokens": sample.get("cacheReadTokens", 0),
        "cache_creation_input_tokens": sample.get("cacheWriteTokens", 0),
        "reasoning_output_tokens": sample.get("reasoningTokens", 0),
        "model_calls": sample.get("modelRequestCount", result.get("projection", {}).get("turnCount", 1)),
    }


MESSAGES = {"muse": muse_messages, "gemini": gemini_messages, "qwen": claude.trajectory_messages,
            "deepseek": deepseek_messages, "glm": glm_messages}
USAGE = {"gemini": gemini_usage, "qwen": claude.result_usage,
         "deepseek": deepseek_usage, "glm": glm_usage}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=sorted(MESSAGES), required=True)
    parser.add_argument("--raw-stdout", type=Path, required=True)
    parser.add_argument("--raw-stderr", type=Path, required=True)
    parser.add_argument("--traj", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--returncode", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning", default="")
    parser.add_argument("--image", required=True)
    parser.add_argument("--agent-command", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--session-logs", type=Path)
    args = parser.parse_args()

    prompt = args.prompt_file.read_text()
    events = deepseek_session_events(args.session_logs) if args.agent == "deepseek" else claude.load_events(args.raw_stdout)
    usage = muse_usage(args.session_logs) if args.agent == "muse" else USAGE[args.agent](events)
    # Gemini CLI can quietly substitute a model it knows for one it does not.
    if args.agent == "gemini" and usage and args.model not in usage["models"]:
        print(f"WARNING: gemini served {sorted(usage['models'])} instead of {args.model}", file=sys.stderr)
    trajectory = {
        "info": {
            "exit_status": args.status,
            "returncode": args.returncode,
            "exception_info": "",
            "output": args.output,
            "reason": None,
            "image": args.image,
            "agent": args.agent,
            "model": args.model,
            "reasoning": args.reasoning,
            "agent_command": args.agent_command,
            "agent_shell_command": shlex.join([*shlex.split(args.agent_command), prompt]),
        },
        "instance_id": args.instance_id,
        "usage": usage,
        "usage_calls": usage.get("model_calls", 1) if usage else 0,
        "messages": deepseek_messages(prompt, events, args.raw_stdout.read_text(errors="replace"))
        if args.agent == "deepseek" else MESSAGES[args.agent](prompt, events),
        "agent_json_events": events,
        "agent_output": {
            "stdout": args.raw_stdout.read_text(errors="replace"),
            "stderr": args.raw_stderr.read_text(errors="replace"),
        },
    }
    args.traj.write_text(json.dumps(trajectory, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
