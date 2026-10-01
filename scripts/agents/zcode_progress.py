#!/usr/bin/env python3
"""Run ZCode headlessly while reporting its own lifecycle events on stderr.

ZCode's --prompt --json writes only the final JSON to stdout. Its JSONL log
receives model and tool events during the run, so follow that log without
changing stdout or the trajectory format.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


LOG_DIR = Path.home() / ".zcode" / "cli" / "log"
POLL_SECONDS = 0.25
HEARTBEAT_SECONDS = 5 * 60


def progress(event: dict, request_count: int) -> tuple[str, int]:
    name = event.get("event")
    context = event.get("context") or {}
    if name == "model.request.started":
        request_count += 1
        return f"Model request {request_count} started", request_count
    if name == "model.request.completed" and context.get("requestId"):
        duration = event.get("durationMs")
        elapsed = f" ({duration / 1000:.1f}s)" if isinstance(duration, (int, float)) else ""
        return f"Model request {request_count} completed{elapsed}", request_count
    if name in ("tool.call.started", "tool.call.completed", "tool.call.failed"):
        tool = context.get("toolName") or "tool"
        state = name.rsplit(".", 1)[-1]
        return f"Tool {tool} {state}", request_count
    if name in ("model.request.failed", "model.network.failed"):
        parts = [name.replace(".", " ").capitalize()]
        if context.get("statusCode"):
            parts.append(f"HTTP {context['statusCode']}")
        if context.get("reason"):
            parts.append(str(context["reason"]))
        if context.get("attempt"):
            parts.append(f"attempt {context['attempt']}")
        return " — ".join(parts), request_count
    if name in ("turn.completed", "turn.failed"):
        message = "Turn " + name.split(".")[1]
        if name == "turn.failed" and event.get("traceId"):
            message += f" (traceId: {event['traceId']})"
        return message, request_count
    return "", request_count


def main() -> int:
    offsets = {path: path.stat().st_size for path in LOG_DIR.glob("zcode-*.jsonl")}
    pending: dict[Path, bytes] = {}
    child = subprocess.Popen(["zcode", *sys.argv[1:]])
    print("[glm] ZCode started", file=sys.stderr, flush=True)
    started = last_activity = time.monotonic()
    request_count = 0
    while True:
        for path in sorted(LOG_DIR.glob("zcode-*.jsonl")):
            with path.open("rb") as handle:
                handle.seek(offsets.get(path, 0))
                chunk = handle.read()
                offsets[path] = handle.tell()
            if not chunk:
                continue
            lines = (pending.pop(path, b"") + chunk).split(b"\n")
            pending[path] = lines.pop()
            for line in lines:
                try:
                    event = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                message, request_count = progress(event, request_count)
                if message:
                    print(f"[glm] {message}", file=sys.stderr, flush=True)
                    last_activity = time.monotonic()
        if child.poll() is not None:
            return child.returncode
        now = time.monotonic()
        if now - last_activity >= HEARTBEAT_SECONDS:
            print(f"[glm] Still running ({int(now - started)}s elapsed)", file=sys.stderr, flush=True)
            last_activity = now
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
