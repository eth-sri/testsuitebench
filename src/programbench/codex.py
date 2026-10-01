# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Utilities for building Codex CLI commands."""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any

from programbench.constants import DOCKER_CPUS, DOCKER_EXECUTABLE
from programbench.container import ContainerEnvironment


DEFAULT_CONTAINER_IMAGE = os.environ.get("PROGRAMBENCH_CODEX_IMAGE", "ghcr.io/openai/codex-universal:latest")
DEFAULT_AUTH_FILE = Path(
    os.environ.get(
        "PROGRAMBENCH_CODEX_AUTH_FILE",
        Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json",
    )
)
_WORKSPACE_EXCLUDES = ["*.profraw", "__pycache__", ".pytest_cache"]

CODEX_TOKEN_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
    "uncached_input_tokens",
    "uncached_input_plus_output_tokens",
)


def normalize_codex_usage(raw: dict[str, Any]) -> dict[str, int]:
    """Normalize a Codex usage object and retain every supported token field."""
    usage = {
        key: value
        for key, value in raw.items()
        if key in CODEX_TOKEN_KEYS and isinstance(value, int) and not isinstance(value, bool)
    }
    input_tokens = usage.get("input_tokens", 0)
    cached_tokens = usage.get("cached_input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    usage.setdefault("total_tokens", input_tokens + output_tokens)
    usage.setdefault("uncached_input_tokens", max(0, input_tokens - cached_tokens))
    usage.setdefault("uncached_input_plus_output_tokens", usage["uncached_input_tokens"] + output_tokens)
    return usage


def sum_codex_usage(usages: list[dict[str, int]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for usage in usages:
        for key, value in usage.items():
            totals[key] = totals.get(key, 0) + value
    return totals


def codex_usage_records_from_events(events: list[dict[str, Any]]) -> list[dict[str, int]]:
    """Extract one normalized usage record for each completed Codex turn."""
    return [
        normalize_codex_usage(event["usage"])
        for event in events
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict)
    ]


def codex_usage_records_from_stdout(stdout: str) -> list[dict[str, int]]:
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(event, dict):
            events.append(event)
    return codex_usage_records_from_events(events)


def build_codex_shell_command(
    codex_command: str,
    *,
    prompt: str,
    model: str = "",
    reasoning_effort: str = "",
    diagnostic_action: str,
) -> str:
    parts = shlex.split(codex_command)
    if not parts:
        raise RuntimeError("codex_command must not be empty")
    diagnostic_flags = {"-h", "--help", "-V", "--version"}
    if diagnostic_flags.intersection(parts):
        raise RuntimeError(
            "codex_command must run an agent command such as `codex exec`; "
            f"help and version commands cannot {diagnostic_action}"
        )
    try:
        exec_index = parts.index("exec")
    except ValueError as error:
        raise RuntimeError("codex_command must contain the `exec` subcommand") from error
    yolo_flags = {"--dangerously-bypass-approvals-and-sandbox", "--yolo"}
    if not yolo_flags.intersection(parts):
        parts.insert(exec_index, "--dangerously-bypass-approvals-and-sandbox")
    if model:
        parts.extend(["--model", model])
    if reasoning_effort:
        parts.extend(["--config", f"model_reasoning_effort={reasoning_effort}"])
    # Specifications must be derived from the local test suite and binary, not
    # from upstream documentation the agent could look up. Disabling search also
    # removes a large sink of the per-instance timeout budget.
    if not any(part.startswith("tools.web_search=") for part in parts):
        parts.extend(["--config", "tools.web_search=false"])
    if "--json" not in parts:
        parts.append("--json")
    parts.append(prompt)
    return " ".join(shlex.quote(part) for part in parts)


def run_codex_in_container(
    command: str,
    *,
    cwd: Path,
    timeout: int,
    image: str = DEFAULT_CONTAINER_IMAGE,
    stage_paths: list[Path] | None = None,
    copy_back_files: list[str] | None = None,
    copy_back_dirs: list[Path] | None = None,
    network_args: list[str] | None = None,
) -> dict[str, Any]:
    """Run Codex against a copied workspace and return only selected outputs."""
    env = ContainerEnvironment(
        image=image,
        cwd="/workspace",
        executable=DOCKER_EXECUTABLE,
        timeout=timeout,
        cpus=DOCKER_CPUS,
        env={
            "CODEX_HOME": "/root/.codex",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false",
            "NO_UPDATE_NOTIFIER": "1",
            "LLVM_PROFILE_FILE": "/tmp/programbench-%m-%p.profraw",
        },
        # Unconfined unless the caller says otherwise. Most callers run analysis
        # tooling -- mutant attribution, spec polish, test linking -- that reads
        # results and emits labels, and some still fetch their agent via
        # `npx -y @openai/codex@...` at runtime, which an API-only allowlist
        # rejects with a 403 from the proxy. A caller whose reference runs must
        # match the offline eval, or whose agent must not read upstream sources,
        # passes agent_network_args() and a preinstalled codex command.
        run_args=network_args,
    )
    try:
        if not DEFAULT_AUTH_FILE.is_file():
            raise RuntimeError(
                f"Codex auth cache does not exist: {DEFAULT_AUTH_FILE}. Run `codex login` on the host."
            )
        env.copy_in(DEFAULT_AUTH_FILE, "/root/.codex/auth.json")
        if stage_paths is None:
            env.copy_in(cwd, "/workspace", excludes=_WORKSPACE_EXCLUDES)
        else:
            for local_path in stage_paths:
                relative = local_path.relative_to(cwd)
                env.copy_in(
                    local_path,
                    f"/workspace/{relative.as_posix()}",
                    excludes=_WORKSPACE_EXCLUDES,
                )
        result = env.execute(command, timeout=timeout)
        for relative_name in copy_back_files or []:
            check = env.execute(f"test -f {shlex.quote('/workspace/' + relative_name)}")
            if check["returncode"] == 0:
                env.copy_out_file(f"/workspace/{relative_name}", cwd / relative_name)
        if result["returncode"] == 0:
            for local_path in copy_back_dirs or []:
                relative = local_path.relative_to(cwd)
                env.copy_out_dir(
                    f"/workspace/{relative.as_posix()}",
                    local_path,
                    excludes=_WORKSPACE_EXCLUDES,
                )
        usage_records = codex_usage_records_from_stdout(result.get("stdout") or "")
        return {
            **result,
            "image": image,
            "usage": sum_codex_usage(usage_records),
            "usage_calls": len(usage_records),
        }
    finally:
        env.cleanup()
