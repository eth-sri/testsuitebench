#!/usr/bin/env python3
"""Run a headless coding harness on a ProgramBench solve task."""

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
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import solve_claude
import solve_codex as common


@dataclass(frozen=True)
class Agent:
    name: str
    default_model: str
    command: str
    reasoning: str  # format template for the effort flag, "" when the CLI has none
    prompt_flag: str
    credentials: dict[str, str]
    env: tuple[str, ...]
    auth_env: tuple[str, ...]  # one of these, or a credential file, must be present
    image_agent: str
    binary: Path | None = None
    env_values: dict[str, str] = field(default_factory=dict)  # exported before the passthrough
    session_log: str = ""  # container dir copied out after the run for usage and trajectory events
    settings_path: str = ""
    settings: Callable[[str, str], dict] | None = None  # (model, reasoning) -> settings.json
    model_flag: bool = True


HOME = Path.home()
HEARTBEAT_SECONDS = 5 * 60
MUSE_VERSION = os.environ.get("PROGRAMBENCH_MUSE_VERSION", "1.3.0-R3401.1")
CODEX_AUTH = os.environ.get(
    "PROGRAMBENCH_CODEX_AUTH_FILE", str(Path(os.environ.get("CODEX_HOME", str(HOME / ".codex"))) / "auth.json")
)
# Every command below disables the agent's own web tools: those run on the
# provider side and would otherwise reach the internet through the API host
# the egress proxy has to allow.
AGENTS = {
    "codex": Agent(
        name="codex",
        default_model="gpt-5.6-sol",
        command="codex --dangerously-bypass-approvals-and-sandbox exec --cd /workspace --skip-git-repo-check --config tools.web_search=false --json",
        reasoning="--config model_reasoning_effort={}",
        prompt_flag="",
        credentials={CODEX_AUTH: "/root/.codex/auth.json"},
        env=("OPENAI_API_KEY",),
        auth_env=("OPENAI_API_KEY",),
        image_agent="codex",
    ),
    # Muse Code is bind-mounted; a pinned local adapter lets it use OpenRouter.
    "muse": Agent(
        name="muse",
        default_model="meta/muse-spark-1.3-contributor",
        command="python3 /opt/programbench/muse_openrouter_exec.py",
        reasoning="--reasoning-effort {}",
        prompt_flag="",
        credentials={},
        env=("OPENROUTER_API_KEY",),
        auth_env=("OPENROUTER_API_KEY",),
        image_agent="muse",
        binary=Path(os.environ.get("PROGRAMBENCH_MUSE_BINARY", str(HOME / ".local/bin" / f"muse-bin-{MUSE_VERSION}"))),
        session_log="/root/.local/share/muse/sessions",
    ),
    # Gemini CLI has no effort flag; the thinking level is a per-model override
    # in settings.json, and so is the tool exclusion. Its default model
    # resolution also rewrites any "*flash" ID it does not know to its own flash
    # default (gemini-3.5-flash at 0.60.0); the dynamic-configuration path
    # passes unknown IDs through unchanged, so it is switched on.
    "gemini": Agent(
        name="gemini",
        default_model="gemini-3.8-flash",
        command="gemini --yolo --skip-trust --output-format stream-json",
        reasoning="",
        prompt_flag="--prompt",
        credentials={str(HOME / ".gemini/oauth_creds.json"): "/root/.gemini/oauth_creds.json"},
        env=("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_GCA", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"),
        auth_env=("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_GENAI_USE_GCA"),
        image_agent="gemini",
        settings_path="/root/.gemini/settings.json",
        settings=lambda model, reasoning: {
            "tools": {"exclude": ["google_web_search", "web_fetch"]},
            "experimental": {"dynamicModelConfiguration": True},
            "modelConfigs": {
                "customOverrides": [
                    {
                        "match": {"model": model},
                        "modelConfig": {"generateContentConfig": {"thinkingConfig": {"thinkingLevel": reasoning.upper()}}},
                    }
                ]
                if reasoning
                else []
            },
        },
    ),
    # Qwen Code talks to OpenRouter through its OpenAI-compatible auth; the
    # model ID is the OpenRouter slug and the reasoning effort goes through
    # settings.json, which Qwen Code forwards as OpenRouter's reasoning.effort.
    "qwen": Agent(
        name="qwen",
        default_model="qwen/qwen3.8-flash",
        command="qwen --yolo --output-format stream-json --exclude-tools web_fetch,web_search --auth-type openai",
        reasoning="",
        prompt_flag="",
        credentials={},
        env=("OPENAI_API_KEY", "OPENAI_BASE_URL"),
        auth_env=("OPENROUTER_API_KEY",),
        env_values={
            "OPENAI_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
            "OPENAI_BASE_URL": os.environ.get("PROGRAMBENCH_QWEN_BASE_URL", "https://openrouter.ai/api/v1"),
        },
        image_agent="qwen",
        settings_path="/root/.qwen/settings.json",
        settings=lambda model, reasoning: {
            "model": {
                **({"reasoningEffort": reasoning} if reasoning else {}),
                # "generationConfig": {
                #     "timeout": int(os.environ.get("PROGRAMBENCH_QWEN_API_TIMEOUT_MS", "600000")),
                # },
            },
        },
    ),
    "deepseek": Agent(
        name="deepseek",
        default_model="deepseek/deepseek-v4-flash-0731",
        command="dsh --patch /tmp/programbench-dsh.patch.yml --profile headless",
        reasoning="",
        prompt_flag="",
        credentials={},
        env=("OPENROUTER_API_KEY", "NODE_USE_ENV_PROXY"),
        auth_env=("OPENROUTER_API_KEY",),
        image_agent="deepseek",
        env_values={"NODE_USE_ENV_PROXY": "1"},
        session_log="/tmp/programbench-dsh-home/sessions",
        model_flag=False,
    ),
    "glm": Agent(
        name="glm",
        default_model="openrouter/z-ai/glm-5.3-flash",
        command="python3 /opt/programbench/zcode_progress.py --json --mode yolo --disallowed-tools WebSearch,WebFetch --prompt",
        reasoning="",
        prompt_flag="",
        credentials={},
        env=("NODE_USE_ENV_PROXY",),
        auth_env=("OPENROUTER_API_KEY",),
        env_values={"NODE_USE_ENV_PROXY": "1"},
        image_agent="glm",
        model_flag=False,
    ),
}
INSTALLERS = {
    "none": ("install_task_patched.sh", []),
    "codex": ("install_codex_cleanroom.sh", []),
    "claude": ("install_claude_cleanroom.sh", []),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a headless coding agent on a ProgramBench solve task. "
            "Output is compatible with: uv run programbench eval <output>"
        ),
        formatter_class=common.DefaultsFormatter,
    )
    parser.add_argument("--agent", choices=sorted(AGENTS), required=True, help="Agent CLI to run")
    parser.add_argument("--model", default="", help="Model ID exactly as the agent CLI expects it (default: per agent)")
    parser.add_argument("--reasoning", default="high", help="Reasoning effort; recorded for agents without an effort control")
    parser.add_argument("--task", default=common.DEFAULT_TASK, help="Task instance ID")
    parser.add_argument("--output", default="", help="Output directory (default: output/executable/<model>-<reasoning>-<mode>)")
    parser.add_argument("--mode", choices=common.VALID_MODES, default=solve_claude.DEFAULT_MODE, help="Solve mode")
    parser.add_argument("--test-suite", default="", help="Generated test suite for with-test modes")
    parser.add_argument("--cleanroom", default="", help="Local cleanroom root. Expected layout: <cleanroom>/<task>/")
    parser.add_argument("--base-tag", default=common.DEFAULT_BASE_TAG, help="Source task cleanroom tag")
    parser.add_argument("--tag-suffix", default="", help="Agent image tag suffix (default: the agent name)")
    parser.add_argument("--cleanroom-base-image", default="", help="Prebuilt agent-enabled task image")
    parser.add_argument("--agent-command", default="", help="Agent command prefix (default: per agent)")
    parser.add_argument(
        "--stdout-aggregated-output-limit",
        type=int,
        default=common.DEFAULT_STDOUT_PASSTHROUGH_LIMIT,
        help="Max chars printed for non-JSON agent output lines",
    )
    parser.add_argument("--timeout", type=int, default=common.DEFAULT_TIMEOUT_SECONDS, help="Docker timeout in seconds")
    parser.add_argument("--docker-cpus", type=int, default=4, help="CPU cores allotted to the container")
    args = parser.parse_args()
    args.model = args.model or AGENTS[args.agent].default_model
    args.tag_suffix = args.tag_suffix or args.agent
    args.agent_command = args.agent_command or AGENTS[args.agent].command
    return args


# The prompt is the last argument of the container command, so the model and
# effort flags go into the prefix rather than being appended after it.
def command_prefix(agent: Agent, command: str, model: str, reasoning: str) -> str:
    words = shlex.split(command)
    if agent.model_flag:
        words += ["--model", model]
    if agent.reasoning and reasoning:
        words += shlex.split(agent.reasoning.format(reasoning))
    if agent.prompt_flag:
        words.append(agent.prompt_flag)
    return shlex.join(words)


# Fail before the image build and the container run, not inside the agent.
def auth_preflight(agent: Agent) -> None:
    if agent.name == "glm":
        config = Path(os.environ.get("PROGRAMBENCH_ZCODE_CONFIG", str(HOME / ".zcode/cli/config.json")))
        if config.is_file() or (not os.environ.get("PROGRAMBENCH_ZCODE_CONFIG") and os.environ.get("OPENROUTER_API_KEY")):
            return
        raise SystemExit("glm needs OPENROUTER_API_KEY or an authenticated ZCode config at " + str(config))
    if agent.name == "codex":
        kind, auth_file = common.codex_credential()
        print(f"[codex] credentials: {common.describe_codex_credential(kind, auth_file)}", flush=True)
        if kind != "none":
            return
    elif any(os.environ.get(name) for name in agent.auth_env) or any(Path(host).is_file() for host in agent.credentials):
        return
    needed = ", ".join([*agent.auth_env, *agent.credentials])
    raise SystemExit(f"{agent.name} has no credentials: export one of {needed} in this shell")


def ensure_cleanroom_image(args: argparse.Namespace) -> str:
    if args.cleanroom_base_image:
        print(f"Using {args.agent} cleanroom image: {args.cleanroom_base_image}")
        return args.cleanroom_base_image

    image_agent = AGENTS[args.agent].image_agent
    installer, options = INSTALLERS.get(image_agent, ("install_agent_cleanroom.sh", ["--agent", image_agent]))
    options = [*options, "--task", args.task]
    if image_agent != "none":
        options += ["--base-tag", args.base_tag, "--tag-suffix", args.tag_suffix]
    installer = common.repo_root() / "scripts" / "docker" / installer
    image = subprocess.check_output([str(installer), *options, "--print-image"], cwd=common.repo_root(), text=True).strip()
    subprocess.run([str(installer), *options], cwd=common.repo_root(), check=True)
    return image


def build_docker_args(
    agent: Agent,
    container_name: str,
    prompt_file: Path,
    cleanroom_source: Path | None,
    test_suite_source: Path | None,
    docker_cpus: int = 4,
    model: str = "",
    reasoning: str = "",
) -> list[str]:
    args = common.build_docker_args(container_name, prompt_file, cleanroom_source, test_suite_source, docker_cpus)
    # Codex credentials never belong in another agent's container.
    for marker in (":/root/.codex/auth.json:ro", "OPENAI_API_KEY"):
        while any(value.endswith(marker) for value in args):
            index = next(i for i, value in enumerate(args) if value.endswith(marker))
            del args[index - 1 : index + 1]
    credentials, env_names = agent.credentials, agent.env
    if agent.name == "codex":
        # Exactly one of the login file and OPENAI_API_KEY reaches the container.
        kind, _ = common.codex_credential()
        credentials = credentials if kind == "login" else {}
        env_names = env_names if kind == "api-key" else ()
    for host, container in credentials.items():
        if Path(host).is_file():
            args += ["-v", f"{Path(host).resolve()}:{container}:ro"]
    if agent.binary is not None:
        if not agent.binary.is_file():
            raise SystemExit(f"Agent binary does not exist: {agent.binary}")
        args += ["-v", f"{agent.binary.resolve()}:/usr/local/bin/{agent.name}:ro"]
    if agent.name == "muse":
        launcher = Path(__file__).with_name("muse_openrouter_exec.py")
        args += ["-v", f"{launcher}:/opt/programbench/muse_openrouter_exec.py:ro"]
    if agent.settings is not None:
        settings_file = prompt_file.parent / f"{agent.name}-settings.json"
        settings_file.write_text(json.dumps(agent.settings(model, reasoning), indent=2) + "\n")
        args += ["-v", f"{settings_file}:{agent.settings_path}"]
    if agent.name == "deepseek":
        patch = prompt_file.parent / "dsh.patch.yml"
        patch.write_text(
            "- id: agent-default-model\n"
            "  config:\n"
            "    provider: openrouter\n"
            f"    model: {json.dumps(model)}\n"
            "- id: llm-pi-ai\n"
            "  config:\n"
            "    providers:\n"
            "      openrouter:\n"
            "        apiKeyEnv: OPENROUTER_API_KEY\n"
            "        api: openai-completions\n"
            "        baseURL: https://openrouter.ai/api/v1\n"
            f"        reasoning: {json.dumps(reasoning or 'high')}\n"
            "        models:\n"
            f"          - id: {json.dumps(model)}\n"
            "            contextWindow: 1048576\n"
            "            reasoningEfforts:\n"
            "              high: high\n"
            "              xhigh: xhigh\n"
            "- id: plugin-package-inventory-deepseek\n"
            "  disabled: true\n"
            "- id: web-search-deepseek\n"
            "  disabled: true\n"
            "- id: web-fetch-http\n"
            "  disabled: true\n"
            "- id: tool-web\n"
            "  disabled: true\n"
        )
        args += ["-v", f"{patch}:/tmp/programbench-dsh.patch.yml:ro"]
        args += ["-e", "DSH_HOME=/tmp/programbench-dsh-home"]
    if agent.name == "glm":
        launcher = Path(__file__).with_name("zcode_progress.py")
        args += ["-v", f"{launcher}:/opt/programbench/zcode_progress.py:ro"]
        if reasoning and reasoning != "max":
            raise SystemExit("ZCode does not expose a headless reasoning-effort control; use --reasoning max")
        source = Path(os.environ.get("PROGRAMBENCH_ZCODE_CONFIG", str(HOME / ".zcode/cli/config.json")))
        if source.is_file():
            config = json.loads(source.read_text())
            config.setdefault("model", {})["main"] = model
        else:
            key = os.environ.get("OPENROUTER_API_KEY")
            if not key:
                raise SystemExit("glm needs OPENROUTER_API_KEY or an authenticated ZCode config at " + str(source))
            if not model.startswith("openrouter/"):
                raise SystemExit("GLM OpenRouter models must use the openrouter/<provider>/<model> ZCode ID")
            upstream_model = model.removeprefix("openrouter/")
            config = {
                "model": {"main": model},
                "provider": {"openrouter": {
                    "kind": "anthropic",
                    "options": {"baseURL": "https://openrouter.ai/api", "apiKey": key},
                    "models": {upstream_model: {}},
                }},
            }
        target = prompt_file.parent / "zcode-config.json"
        target.write_text(json.dumps(config) + "\n")
        target.chmod(0o600)
        args += ["-v", f"{target}:/root/.zcode/cli/config.json:ro"]
    # Values stay off the docker command line: -e NAME reads them from this process's environment.
    os.environ.update({name: value for name, value in agent.env_values.items() if value})
    for name in env_names:
        if os.environ.get(name):
            args += ["-e", name]
    return args


def display_event(agent_name: str, line: str, limit: int) -> str:
    if agent_name == "qwen":
        return solve_claude.display_event(line, limit)
    if agent_name == "codex":
        return common.display_event(line, limit)
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        event = None
    if not isinstance(event, dict):
        return common.truncate(line.rstrip(), limit) + "\n"
    summary = ""
    if agent_name == "muse":
        payload = event.get("payload", {})
        if event.get("payload_type") == "run.output.delta":
            summary = payload["text"]
        elif event.get("payload_type") == "tool.result":
            correlation_facts = payload.get("correlation_facts")
            tool_name = correlation_facts.get("tool_name", "tool") if isinstance(correlation_facts, dict) else "tool"
            summary = f"[{tool_name}] {payload.get('text', '')}"
    elif agent_name == "deepseek" and event.get("type") == "text":
        summary = event.get("text", "")
    elif agent_name == "deepseek" and event.get("type") == "tool_call":
        summary = f"[{event.get('tool', 'tool')}] {json.dumps(event.get('input', {}), ensure_ascii=False)}"
    elif agent_name == "glm" and "response" in event:
        summary = event.get("response", "")
    elif event.get("type") == "message" and event.get("role") == "assistant":
        summary = event["content"]
    elif event.get("type") == "tool_use":
        summary = f"[{event['tool_name']}] {json.dumps(event['parameters'], ensure_ascii=False)}"
    summary = " ".join(summary.split())
    if not summary:
        return ""
    return summary[: solve_claude.PROGRESS_LINE_LIMIT] + ("...\n" if len(summary) > solve_claude.PROGRESS_LINE_LIMIT else "\n")


def run_container(
    *,
    args: argparse.Namespace,
    image: str,
    docker_args: list[str],
    container_script: str,
    raw_stdout: Path,
    raw_stderr: Path,
) -> int:
    command = ["timeout", str(args.timeout), common.docker(), *docker_args, image, "bash", "-lc", container_script]
    live_progress = args.agent in ("deepseek", "glm")
    with raw_stdout.open("w", buffering=1) as stdout_file, raw_stderr.open("w", buffering=1) as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=common.repo_root(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if live_progress else stderr_file,
            text=True,
            errors="replace",
        )
        last_activity = time.monotonic()
        stopped = threading.Event()
        stderr_thread = None
        heartbeat_thread = None
        if live_progress:
            print(f"[{args.agent}] Harness started", flush=True)
            assert process.stderr is not None

            def relay_stderr() -> None:
                nonlocal last_activity
                for line in process.stderr:
                    stderr_file.write(line)
                    if args.agent == "glm" and line.startswith("ZCode Built-in "):
                        continue
                    if args.agent == "glm" and line.startswith("[glm] "):
                        sys.stdout.write(line)
                    else:
                        sys.stdout.write(f"[{args.agent}] {line}")
                    sys.stdout.flush()
                    last_activity = time.monotonic()

            stderr_thread = threading.Thread(target=relay_stderr, daemon=True)
            stderr_thread.start()

            if args.agent == "deepseek":
                def heartbeat() -> None:
                    nonlocal last_activity
                    started = time.monotonic()
                    while not stopped.wait(1):
                        now = time.monotonic()
                        if now - last_activity >= HEARTBEAT_SECONDS:
                            print(f"[deepseek] Still running ({int(now - started)}s elapsed)", flush=True)
                            last_activity = now

                heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
                heartbeat_thread.start()
        assert process.stdout is not None
        for line in process.stdout:
            stdout_file.write(line)
            stdout_file.flush()
            sys.stdout.write(display_event(args.agent, line, args.stdout_aggregated_output_limit))
            sys.stdout.flush()
            last_activity = time.monotonic()
        result = process.wait()
        if stderr_thread is not None:
            stderr_thread.join()
        stopped.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join()
        return result


def write_trajectory(
    *,
    args: argparse.Namespace,
    image: str,
    container_name: str,
    artifact: Path,
    traj: Path,
    prompt_file: Path,
    raw_stdout: Path,
    raw_stderr: Path,
    run_status: int,
) -> None:
    python = common.trajectory_python()
    if not python:
        print(f"uv and python3 not found; skipped {args.agent} trajectory generation", file=sys.stderr)
        return
    model = args.model
    agent = AGENTS[args.agent]
    # Codex keeps its existing trajectory format so solve and test-gen runs stay comparable.
    if args.agent == "codex":
        converter = ["scripts/agents/codex_jsonl_to_traj.py", "--codex-command", args.agent_command]
    else:
        converter = [
            "scripts/agents/agent_jsonl_to_traj.py",
            "--agent", args.agent,
            "--agent-command", command_prefix(agent, args.agent_command, model, args.reasoning),
        ]
    if agent.session_log:
        session_logs = raw_stdout.parent / "sessions"
        subprocess.run([common.docker(), "cp", f"{container_name}:{agent.session_log}", str(session_logs)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        converter += ["--session-logs", str(session_logs)]
    if args.agent == "glm" and run_status != 0:
        # ZCode's CLI often reports only "Turn execution failed" on stderr.
        # Its structured diagnostics remain in the container until cleanup.
        diagnostics = traj.parent / f"zcode_logs_{int(time.time())}"
        copied = subprocess.run(
            [common.docker(), "cp", f"{container_name}:/root/.zcode/cli/log", str(diagnostics)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if copied.returncode == 0:
            print(f"Saved ZCode failure diagnostics to {diagnostics}", flush=True)
    result = subprocess.run(
        [
            *python,
            *converter,
            "--raw-stdout", str(raw_stdout),
            "--raw-stderr", str(raw_stderr),
            "--traj", str(traj),
            "--prompt-file", str(prompt_file),
            "--instance-id", args.task,
            "--status", "ok" if run_status == 0 else f"{args.agent}_failed",
            "--returncode", str(run_status),
            "--model", model,
            "--reasoning", args.reasoning,
            "--image", image,
            "--output", str(artifact),
        ],
        cwd=common.repo_root(),
    )
    if result.returncode == 0:
        print(f"Saved {args.agent} trajectory to {traj}")
        return
    # The temp dir is removed on exit; keep the raw stream so a converter bug costs a re-run of
    # the converter, not of the agent.
    kept = traj.with_name(traj.name.removesuffix(".json") + ".raw.stdout.jsonl")
    shutil.copy(raw_stdout, kept)
    shutil.copy(raw_stderr, kept.with_name(kept.name.replace(".stdout.jsonl", ".stderr.txt")))
    print(f"Failed to write {args.agent} trajectory; raw output kept at {kept}", file=sys.stderr)


def main() -> int:
    common.install_shutdown_handlers()
    logging.basicConfig(level=logging.INFO, format=common.LOG_FORMAT)
    args = parse_args()
    agent = AGENTS[args.agent]
    model = args.model
    test_suite_source = common.resolve_test_suite_source(args)
    out_dir = common.output_dir(args, test_suite_source)
    cleanroom_source = common.resolve_cleanroom_source(args.cleanroom, args.task)

    auth_preflight(agent)
    common.docker_preflight()
    common.agent_network_preflight()
    image = ensure_cleanroom_image(args)

    instance_dir = out_dir / args.task
    instance_dir.mkdir(parents=True, exist_ok=True)
    submission = instance_dir / "submission.tar.gz"
    submission.unlink(missing_ok=True)
    traj = instance_dir / "traj.json"
    container_task = "".join(c if c.isalnum() else "-" for c in args.task)
    container_name = f"programbench-{args.agent}-{container_task}-{os.getpid()}"
    temp_dir = Path(tempfile.mkdtemp(prefix=f"programbench-{args.agent}-"))
    prompt_file = temp_dir / "prompt.txt"
    raw_stdout = temp_dir / "stdout.jsonl"
    raw_stderr = temp_dir / "stderr.txt"
    prompt_file.write_text(solve_claude.solve_prompt(args.mode))

    try:
        cleanroom_source = common.stage_cleanroom(
            cleanroom_source, temp_dir / "cleanroom", with_executable=args.mode == "with-executable"
        )
        sanitized_test_suite = common.prepare_test_suite_archive(test_suite_source, temp_dir)
        started = time.time()
        run_status = run_container(
            args=args,
            image=image,
            docker_args=build_docker_args(
                agent, container_name, prompt_file, cleanroom_source, sanitized_test_suite, args.docker_cpus, model, args.reasoning
            ),
            container_script=solve_claude.build_container_script(
                args.mode, command_prefix(agent, args.agent_command, model, args.reasoning), "", ""
            ),
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
        )
        finished = time.time()
        common.copy_submission(container_name, submission)
        if submission.is_file():
            extract_dir = instance_dir / "submission_untar"
            shutil.rmtree(extract_dir, ignore_errors=True)
            try:
                with tarfile.open(submission, "r:gz") as archive:
                    archive.extractall(extract_dir, filter="data")
            except tarfile.TarError as error:
                shutil.rmtree(extract_dir, ignore_errors=True)
                message = f"Submission archive validation failed: {error}"
                print(message, file=sys.stderr)
                with raw_stderr.open("a") as stderr_file:
                    stderr_file.write("\n" + message + "\n")
                run_status = 1
            else:
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
            container_name=container_name,
            artifact=submission,
            traj=traj,
            prompt_file=prompt_file,
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
            run_status=run_status,
        )
        common.record_timing(traj, started, finished)
        if run_status != 0:
            print(f"{args.agent} run exited with status {run_status}", file=sys.stderr)
        return run_status
    finally:
        common.cleanup(container_name, temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
