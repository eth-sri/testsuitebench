from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load_script(relative: str):
    module_path = SCRIPTS / relative
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve string annotations through sys.modules[module.__name__].
    sys.modules[module_path.stem] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("agent", "reasoning", "expected"),
    [
        ("codex", "xhigh", "--json --model spark --config model_reasoning_effort=xhigh"),
        ("muse", "high", "muse_openrouter_exec.py --model spark --reasoning-effort high"),
        ("gemini", "high", "--output-format stream-json --model spark --prompt"),
        ("qwen", "high", "--model spark"),
        ("deepseek", "high", "dsh --patch /tmp/programbench-dsh.patch.yml --profile headless"),
        ("glm", "max", "zcode_progress.py --json --mode yolo --disallowed-tools WebSearch,WebFetch --prompt"),
    ],
)
def test_command_prefix_places_model_and_effort_before_the_prompt(agent, reasoning, expected):
    """The container script appends only the prompt, so gemini's --prompt must be the last word."""
    solve_agent = load_script("agents/solve_agent.py")
    profile = solve_agent.AGENTS[agent]

    prefix = solve_agent.command_prefix(profile, profile.command, "spark", reasoning)

    assert prefix.endswith(expected)
    script = solve_agent.solve_claude.build_container_script("spec-only", prefix, "", "")
    assert f"cmd=({prefix})" in script
    assert 'cmd+=("$prompt")' in script


def test_every_agent_disables_its_web_tools():
    """Provider-side web tools reach the internet through the allowlisted API host, bypassing the egress proxy."""
    solve_agent = load_script("agents/solve_agent.py")
    guards = {
        "codex": "--config tools.web_search=false",
        "qwen": "--exclude-tools web_fetch,web_search",
    }
    for agent, guard in guards.items():
        assert guard in solve_agent.AGENTS[agent].command, agent
    assert "--disable-web-tools" in (SCRIPTS / "agents/muse_openrouter_exec.py").read_text()
    assert guards["codex"] in solve_agent.common.DEFAULT_CODEX_COMMAND
    assert "--disallowedTools WebSearch,WebFetch" in solve_agent.solve_claude.DEFAULT_CLAUDE_COMMAND
    gemini = solve_agent.AGENTS["gemini"].settings("gemini-3.8-flash", "low")
    assert gemini["tools"]["exclude"] == ["google_web_search", "web_fetch"]
    # Without this flag the CLI rewrites unknown "*flash" IDs to its own flash default.
    assert gemini["experimental"] == {"dynamicModelConfiguration": True}
    assert gemini["modelConfigs"]["customOverrides"] == [
        {"match": {"model": "gemini-3.8-flash"}, "modelConfig": {"generateContentConfig": {"thinkingConfig": {"thinkingLevel": "LOW"}}}}
    ]
    assert solve_agent.AGENTS["gemini"].settings("gemini-3.1-pro-preview", "")["modelConfigs"]["customOverrides"] == []
    assert solve_agent.AGENTS["qwen"].settings("qwen/qwen3.8-flash", "xhigh") == {"model": {"reasoningEffort": "xhigh"}}
    assert solve_agent.AGENTS["qwen"].default_model == "qwen/qwen3.8-flash"
    assert "--auth-type openai" in solve_agent.AGENTS["qwen"].command


def test_docker_args_swap_codex_credentials_for_the_agents_own(tmp_path, monkeypatch):
    solve_agent = load_script("agents/solve_agent.py")
    creds = tmp_path / "oauth_creds.json"
    creds.write_text("{}")
    binary = tmp_path / "muse-bin-1.0.0"
    binary.write_text("")
    monkeypatch.setenv("OPENAI_API_KEY", "for-codex")
    monkeypatch.setenv("GEMINI_API_KEY", "for-gemini")
    gemini = solve_agent.Agent(
        name="gemini", default_model="m", command="gemini", reasoning="", prompt_flag="--prompt",
        credentials={str(creds): "/root/.gemini/oauth_creds.json"}, env=("GEMINI_API_KEY",), auth_env=("GEMINI_API_KEY",), image_agent="gemini",
        settings_path="/root/.gemini/settings.json", settings=lambda model, reasoning: {"model": model, "reasoning": reasoning},
    )
    muse = solve_agent.Agent(
        name="muse", default_model="m", command="python3 /opt/programbench/muse_openrouter_exec.py",
        reasoning="", prompt_flag="", credentials={}, env=("OPENROUTER_API_KEY",),
        auth_env=("OPENROUTER_API_KEY",), image_agent="muse", binary=binary,
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "for-openrouter")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    qwen = solve_agent.Agent(
        name="qwen", default_model="m", command="qwen", reasoning="", prompt_flag="", credentials={}, env=("OPENAI_API_KEY", "OPENAI_BASE_URL"), auth_env=("OPENROUTER_API_KEY",),
        env_values={"OPENAI_API_KEY": "for-openrouter", "OPENAI_BASE_URL": "https://openrouter.ai/api/v1"}, image_agent="qwen",
    )

    gemini_args = solve_agent.build_docker_args(gemini, "c", tmp_path / "prompt", None, None, 4, "g3", "low")
    muse_args = solve_agent.build_docker_args(muse, "c", tmp_path / "prompt", None, None)
    qwen_args = solve_agent.build_docker_args(qwen, "c", tmp_path / "prompt", None, None)

    assert f"{creds}:/root/.gemini/oauth_creds.json:ro" in gemini_args
    assert f"{tmp_path / 'gemini-settings.json'}:/root/.gemini/settings.json" in gemini_args
    assert json.loads((tmp_path / "gemini-settings.json").read_text()) == {"model": "g3", "reasoning": "low"}
    assert "GEMINI_API_KEY" in gemini_args and "OPENAI_API_KEY" not in gemini_args
    assert not any("/root/.codex/auth.json" in arg for arg in gemini_args)
    assert f"{binary}:/usr/local/bin/muse:ro" in muse_args
    assert not any("/root/.config/muse" in arg for arg in muse_args)
    assert "OPENROUTER_API_KEY" in muse_args
    assert any("/opt/programbench/muse_openrouter_exec.py:ro" in arg for arg in muse_args)
    assert "OPENAI_API_KEY" in qwen_args and "OPENAI_BASE_URL" in qwen_args
    assert os.environ["OPENAI_API_KEY"] == "for-openrouter" and os.environ["OPENAI_BASE_URL"] == "https://openrouter.ai/api/v1"
    assert "--network" in gemini_args



def test_muse_openrouter_uses_its_own_harness_and_key(monkeypatch, tmp_path):
    solve_agent = load_script("agents/solve_agent.py")
    muse = solve_agent.AGENTS["muse"]
    assert muse.image_agent == "muse"
    assert muse.default_model == "meta/muse-spark-1.3-contributor"
    assert muse.credentials == {}
    assert muse.auth_env == ("OPENROUTER_API_KEY",)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        solve_agent.auth_preflight(muse)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    assert solve_agent.auth_preflight(muse) is None
    binary = tmp_path / "muse"
    binary.write_bytes(b"")
    replaced = solve_agent.Agent(**{**vars(muse), "binary": binary})
    args = solve_agent.build_docker_args(replaced, "c", tmp_path / "prompt", None, None)
    assert "OPENROUTER_API_KEY" in args
    assert not any("/root/.config/muse/auth.json" in arg for arg in args)
    assert any("/opt/programbench/muse_openrouter_exec.py:ro" in arg for arg in args)

def test_display_event_summarizes_each_agents_stream():
    solve_agent = load_script("agents/solve_agent.py")
    muse_tool = {"payload_type": "tool.result", "payload": {"correlation_facts": {"tool_name": "bash"}, "text": "{\n \"command\": \"ls\"\n}"}}
    muse_tool_without_correlation_facts = {"payload_type": "tool.result", "payload": {"text": "background task completed"}}
    muse_text = {"payload_type": "run.output.delta", "payload": {"text": "DONE"}}
    gemini_tool = {"type": "tool_use", "tool_name": "run_shell_command", "tool_id": "t1", "parameters": {"command": "ls"}}
    qwen_assistant = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}

    assert solve_agent.display_event("muse", json.dumps(muse_tool), 240) == '[bash] { "command": "ls" }\n'
    assert solve_agent.display_event("muse", json.dumps(muse_tool_without_correlation_facts), 240) == "[tool] background task completed\n"
    assert solve_agent.display_event("muse", json.dumps(muse_text), 240) == "DONE\n"
    assert solve_agent.display_event("muse", json.dumps({"payload_type": "task.lifecycle.started", "payload": {}}), 240) == ""
    assert solve_agent.display_event("gemini", json.dumps(gemini_tool), 240) == '[run_shell_command] {"command": "ls"}\n'
    assert solve_agent.display_event("gemini", json.dumps({"type": "init", "model": "g"}), 240) == ""
    assert solve_agent.display_event("qwen", json.dumps(qwen_assistant), 240) == "[Bash] ls\n"
    assert solve_agent.display_event("codex", json.dumps({"type": "item.completed"}), 240) == ""
    assert solve_agent.display_event("gemini", "42\n", 240) == "42\n"


def test_trajectory_messages_follow_the_claude_shape_for_every_agent():
    converter = load_script("agents/agent_jsonl_to_traj.py")
    muse_events = [
        {"payload_type": "run.output.delta", "payload": {"text": "Looking."}},
        {"payload_type": "tool.result", "payload": {"call_id": "call_1", "correlation_facts": {"tool_name": "bash", "outcome": "failure"}, "text": "boom"}},
        {"payload_type": "tool.result", "payload": {"call_id": "call_2", "text": "background task still running"}},
        {"payload_type": "run.terminal.completed", "payload": {"text": "DONE"}},
        {"payload_type": "run.output.delta", "payload": {"text": "DONE"}},
    ]
    gemini_events = [
        {"type": "message", "role": "user", "content": "prompt"},
        {"type": "message", "role": "assistant", "content": "Look"},
        {"type": "message", "role": "assistant", "content": "ing."},
        {"type": "tool_use", "tool_name": "run_shell_command", "tool_id": "t1", "parameters": {"command": "ls"}},
        {"type": "tool_result", "tool_id": "t1", "status": "success", "output": "spec.md"},
        {"type": "tool_use", "tool_name": "write_file", "tool_id": "t2", "parameters": {"file_path": "a"}},
        {"type": "tool_result", "tool_id": "t2", "status": "success"},
        {"type": "tool_use", "tool_name": "run_shell_command", "tool_id": "t3", "parameters": {"command": "false"}},
        {"type": "tool_result", "tool_id": "t3", "status": "error", "error": {"type": "TOOL_EXECUTION_ERROR", "message": "exit 1"}},
        {"type": "result", "status": "success", "stats": {"total_tokens": 30, "input_tokens": 20, "output_tokens": 10, "cached": 5}},
    ]

    muse = converter.muse_messages("prompt", muse_events)
    gemini = converter.gemini_messages("prompt", gemini_events)

    assert [m["role"] for m in muse] == ["user", "assistant", "assistant", "tool", "assistant", "tool", "assistant"]
    assert muse[2]["tool_calls"][0]["function"]["name"] == "bash" and muse[3]["extra"]["is_error"]
    assert muse[4]["tool_calls"][0]["function"]["name"] == "tool"
    assert muse[5]["content"] == "background task still running" and not muse[5]["extra"]["is_error"]
    assert [m["role"] for m in gemini] == ["user", "assistant", "assistant", "tool", "assistant", "tool", "assistant", "tool"]
    assert gemini[5]["content"] == "" and gemini[7] == {"role": "tool", "tool_call_id": "t3", "content": "exit 1", "extra": {"is_error": True}}
    assert gemini[1]["content"] == "Looking."
    assert json.loads(gemini[2]["tool_calls"][0]["function"]["arguments"]) == {"command": "ls"}
    assert gemini[3] == {"role": "tool", "tool_call_id": "t1", "content": "spec.md", "extra": {"is_error": False}}
    assert converter.gemini_usage(gemini_events)["total_tokens"] == 30
    assert converter.muse_usage(None) == {}
    assert converter.MESSAGES["qwen"] is converter.claude.trajectory_messages


def test_solve_and_test_generation_share_one_container_budget():
    """Every agent solves and generates tests on the same CPU count and the same code path."""
    sources = {name: (SCRIPTS / "agents" / name).read_text() for name in (
        "solve_codex.py", "solve_claude.py", "solve_agent.py", "generate_tests_claude.py", "generate_tests_agent.py",
    )}
    for name, source in sources.items():
        assert '"--docker-cpus", type=int, default=4,' in source, name
    assert "default_docker_cpus=4" in (SCRIPTS / "agents" / "solve_codex.sh").read_text()
    codex_eval = (SCRIPTS / "eval" / "codex_eval.sh").read_text()
    assert "scripts/agents/generate_tests_codex.sh" in codex_eval
    assert "programbench generate-tests" not in codex_eval
    # The offline build check must run in the image the agent solved in, not the bare cleanroom.
    assert "cleanroom_base_image(args.task" not in sources["solve_claude.py"]


def test_auth_preflight_fails_before_any_docker_work(monkeypatch, tmp_path):
    solve_agent = load_script("agents/solve_agent.py")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    gemini = solve_agent.Agent(
        name="gemini", default_model="m", command="gemini", reasoning="", prompt_flag="",
        credentials={str(tmp_path / "missing.json"): "/root/.gemini/oauth_creds.json"},
        env=("GEMINI_API_KEY",), auth_env=("GEMINI_API_KEY", "GOOGLE_API_KEY"), image_agent="gemini",
    )

    with pytest.raises(SystemExit, match="GEMINI_API_KEY"):
        solve_agent.auth_preflight(gemini)
    monkeypatch.setenv("GOOGLE_API_KEY", "k")
    assert solve_agent.auth_preflight(gemini) is None


def test_muse_usage_is_summed_from_the_session_log(tmp_path):
    converter = load_script("agents/agent_jsonl_to_traj.py")
    log = tmp_path / "2026" / "09" / "19" / "abc" / "session.jsonl"
    log.parent.mkdir(parents=True)
    completed = lambda i, o, c: {"payload_type": "runtime.session", "payload": {"kind": "run", "event": {"kind": "model_completed", "usage": {"input_tokens": i, "cached_tokens": c, "output_tokens": o, "reasoning_tokens": 1}}}}
    log.write_text("\n".join(json.dumps(r) for r in [
        completed(100, 10, 60), {"payload_type": "runtime.session", "payload": {"kind": "run", "event": {"kind": "goal_usage_attribution"}}}, completed(200, 20, 150), "not json",
    ]))

    assert converter.muse_usage(tmp_path) == {"input_tokens": 300, "cached_tokens": 210, "output_tokens": 30, "reasoning_tokens": 2, "total_tokens": 330, "model_calls": 2}
    assert converter.muse_usage(tmp_path / "empty") == {}


@pytest.mark.parametrize(("agent",), [("claude",), ("codex",), ("muse",), ("gemini",), ("qwen",)])
def test_regenerate_bypasses_the_completed_step_skip(agent):
    """--force only re-evaluates; --regenerate is the switch that reruns the agent phases."""
    script = (SCRIPTS / "eval" / f"{agent}_eval.sh").read_text()
    assert "--regenerate) regenerate=true; force=true; shift ;;" in script
    assert script.count('if [ "${regenerate}" = false ] && python3 scripts/eval/claude_step_complete.py') == 2


def test_official_harness_configs_and_streams(tmp_path, monkeypatch):
    solve_agent = load_script("agents/solve_agent.py")
    converter = load_script("agents/agent_jsonl_to_traj.py")
    prompt = tmp_path / "prompt"
    prompt.write_text("task")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    deepseek = solve_agent.AGENTS["deepseek"]
    solve_agent.auth_preflight(deepseek)
    args = solve_agent.build_docker_args(
        deepseek, "run", prompt, None, None, model="deepseek/deepseek-v4-flash-0731", reasoning="xhigh"
    )
    assert "OPENROUTER_API_KEY" in args
    assert "NODE_USE_ENV_PROXY" in args
    assert deepseek.session_log == "/tmp/programbench-dsh-home/sessions"
    patch = (tmp_path / "dsh.patch.yml").read_text()
    assert "provider: openrouter" in patch
    assert 'model: "deepseek/deepseek-v4-flash-0731"' in patch
    assert "apiKeyEnv: OPENROUTER_API_KEY" in patch
    assert 'reasoning: "xhigh"' in patch
    assert "- id: tool-web\n  disabled: true" in patch
    events = [
        {"type": "assistant/message", "data": {
            "message": {"content": [{"type": "reasoning", "text": "think"}, {"type": "text", "text": "working"}]},
            "usage": {"inputTokens": 10, "outputTokens": 5, "cacheReadTokens": 3, "totalTokens": 18},
        }},
        {"type": "tool/call", "data": {"callId": "c1", "name": "bash", "arguments": '{"command":"pwd"}'}},
        {"type": "tool/result", "data": {"message": {"content": [{
            "type": "tool-result", "toolCallId": "c1", "content": [{"type": "text", "text": "/workspace"}],
            "isError": False,
        }]}}},
        {"type": "assistant/message", "data": {
            "message": {"content": [{"type": "text", "text": "done"}]},
            "usage": {"inputTokens": 4, "outputTokens": 2, "totalTokens": 6},
        }},
    ]
    messages = converter.deepseek_messages("task", events)
    assert messages[1]["content"] == "working"
    assert messages[2]["tool_calls"][0]["function"]["name"] == "bash"
    assert messages[3]["content"] == "/workspace"
    assert messages[4]["content"] == "done"
    assert converter.deepseek_usage(events)["input_tokens"] == 14
    assert converter.deepseek_usage(events)["total_tokens"] == 24
    assert converter.deepseek_messages("task", [], "final")[-1]["content"] == "final"

    config = tmp_path / "host-zcode.json"
    config.write_text(json.dumps({"model": {"main": "other"}, "provider": {"zai": {"kind": "anthropic"}}}))
    monkeypatch.setenv("PROGRAMBENCH_ZCODE_CONFIG", str(config))
    glm = solve_agent.AGENTS["glm"]
    solve_agent.auth_preflight(glm)
    glm_args = solve_agent.build_docker_args(glm, "run", prompt, None, None, model="zai/GLM-5.3-Flash", reasoning="max")
    assert any("/root/.zcode/cli/config.json:ro" in value for value in glm_args)
    assert any("/opt/programbench/zcode_progress.py:ro" in value for value in glm_args)
    mounted = json.loads((tmp_path / "zcode-config.json").read_text())
    assert mounted["model"]["main"] == "zai/GLM-5.3-Flash"
    assert mounted["provider"] == {"zai": {"kind": "anthropic"}}
    assert converter.glm_messages("task", [{"response": "done"}])[-1]["content"] == "done"


def test_glm_uses_openrouter_key_without_host_zcode_config(tmp_path, monkeypatch):
    solve_agent = load_script("agents/solve_agent.py")
    converter = load_script("agents/agent_jsonl_to_traj.py")
    monkeypatch.setattr(solve_agent, "HOME", tmp_path)
    monkeypatch.delenv("PROGRAMBENCH_ZCODE_CONFIG", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    glm = solve_agent.AGENTS["glm"]
    assert glm.default_model == "openrouter/z-ai/glm-5.3-flash"
    solve_agent.auth_preflight(glm)
    prompt = tmp_path / "prompt"
    prompt.write_text("task")
    args = solve_agent.build_docker_args(glm, "run", prompt, None, None, model=glm.default_model, reasoning="max")
    config = json.loads((tmp_path / "zcode-config.json").read_text())
    assert config == {"model": {"main": glm.default_model}, "provider": {"openrouter": {
        "kind": "anthropic",
        "options": {"baseURL": "https://openrouter.ai/api", "apiKey": "test-openrouter-key"},
        "models": {"z-ai/glm-5.3-flash": {}},
    }}}
    assert (tmp_path / "zcode-config.json").stat().st_mode & 0o777 == 0o600
    assert "NODE_USE_ENV_PROXY" in args
    assert converter.glm_usage([{"response": "OK", "usage": {
        "inputTokens": 10, "outputTokens": 2, "totalTokens": 12, "cacheReadTokens": 3,
        "cacheWriteTokens": 1, "reasoningTokens": 4, "modelRequestCount": 2,
    }}]) == {
        "input_tokens": 10, "output_tokens": 2, "total_tokens": 12,
        "cache_read_input_tokens": 3, "cache_creation_input_tokens": 1,
        "reasoning_output_tokens": 4, "model_calls": 2,
    }


def test_zcode_progress_reports_lifecycle_without_log_payloads():
    progress = load_script("agents/zcode_progress.py")
    assert progress.progress({"event": "model.request.started", "context": {"queryId": "secret"}}, 0) == (
        "Model request 1 started", 1
    )
    assert progress.progress({"event": "model.request.completed", "durationMs": 1234,
                              "context": {"requestId": "r1", "baseURL": "secret"}}, 1) == (
        "Model request 1 completed (1.2s)", 1
    )
    assert progress.progress({"event": "tool.call.started", "context": {"toolName": "Bash",
                              "input": {"command": "secret"}}}, 1) == ("Tool Bash started", 1)
    assert progress.progress({"event": "turn.completed", "context": {}}, 1) == ("Turn completed", 1)
    assert progress.progress({"event": "model.network.failed", "context": {
        "statusCode": 429, "reason": "rate_limited", "attempt": 3, "apiKey": "secret"
    }}, 1) == ("Model network failed — HTTP 429 — rate_limited — attempt 3", 1)
    assert progress.progress({"event": "turn.failed", "traceId": "trace-1", "context": {}}, 1) == (
        "Turn failed (traceId: trace-1)", 1
    )
    assert progress.progress({"event": "irrelevant", "context": {"apiKey": "secret"}}, 1) == ("", 1)


def test_codex_gets_exactly_one_credential_and_says_which(tmp_path, monkeypatch, capsys):
    solve_agent = load_script("agents/solve_agent.py")
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({"auth_mode": "chatgpt"}))
    monkeypatch.setenv("PROGRAMBENCH_CODEX_AUTH_FILE", str(auth))
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.delenv("PROGRAMBENCH_CODEX_AUTH", raising=False)
    # The agent table captured CODEX_AUTH at import, so build an Agent for this file.
    codex = solve_agent.Agent(
        name="codex", default_model="m", command="codex", reasoning="", prompt_flag="",
        credentials={str(auth): "/root/.codex/auth.json"}, env=("OPENAI_API_KEY",), auth_env=("OPENAI_API_KEY",),
        image_agent="codex",
    )

    args = solve_agent.build_docker_args(codex, "c", tmp_path / "prompt", None, None)
    assert f"{auth}:/root/.codex/auth.json:ro" in args and "OPENAI_API_KEY" not in args
    solve_agent.auth_preflight(codex)
    assert "ChatGPT subscription login" in capsys.readouterr().out

    monkeypatch.setenv("PROGRAMBENCH_CODEX_AUTH", "api-key")
    args = solve_agent.build_docker_args(codex, "c", tmp_path / "prompt", None, None)
    assert "OPENAI_API_KEY" in args and not any("/root/.codex/auth.json" in a for a in args)
    solve_agent.auth_preflight(codex)
    assert "OPENAI_API_KEY from the environment" in capsys.readouterr().out

    auth.unlink()
    monkeypatch.setenv("PROGRAMBENCH_CODEX_AUTH", "auto")
    args = solve_agent.build_docker_args(codex, "c", tmp_path / "prompt", None, None)
    assert "OPENAI_API_KEY" in args  # no login file: fall back to the key

    monkeypatch.setenv("PROGRAMBENCH_CODEX_AUTH", "login")
    with pytest.raises(SystemExit, match="codex login"):
        solve_agent.build_docker_args(codex, "c", tmp_path / "prompt", None, None)
