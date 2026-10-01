from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def load_script(name: str):
    module_path = Path(__file__).resolve().parents[1] / "scripts" / name
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_claude_defaults_to_spec_only_and_builds_expected_output():
    solve_claude = load_script("agents/solve_claude.py")
    args = SimpleNamespace(
        output="",
        mode="spec-only",
        model="claude/sonnet",
        effort="high",
        task="facebook__zstd.1168da0",
    )

    assert solve_claude.DEFAULT_MODE == "spec-only"
    assert solve_claude.claude_model(args.model) == "sonnet"
    assert solve_claude.output_dir(args) == Path("output/executable/claude/sonnet-high-spec-only")
    assert solve_claude.solve_prompt("spec-only") == solve_claude.common.PROMPT_SPEC_ONLY


def test_claude_docker_args_mount_credentials_and_not_codex_auth(tmp_path, monkeypatch):
    solve_claude = load_script("agents/solve_claude.py")
    credentials = tmp_path / ".credentials.json"
    credentials.write_text("{}")
    monkeypatch.setenv("PROGRAMBENCH_CLAUDE_CREDENTIALS_FILE", str(credentials))
    monkeypatch.setenv("OPENAI_API_KEY", "not-for-claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "for-claude")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "also-not-for-claude")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "overrides-credentials")

    args = solve_claude.build_docker_args(
        "container",
        tmp_path / "prompt",
        tmp_path / "cleanroom",
        None,
    )

    assert f"{credentials}:/tmp/programbench-claude-config/.credentials.json:ro" in args
    assert "ANTHROPIC_API_KEY" not in args
    assert "ANTHROPIC_AUTH_TOKEN" not in args
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in args
    assert "OPENAI_API_KEY" not in args
    assert not any("/root/.codex/auth.json" in arg for arg in args)


def test_oauth_token_is_the_only_claude_credential_by_default(tmp_path, monkeypatch):
    solve_claude = load_script("agents/solve_claude.py")
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / ".credentials.json").write_text("{}")
    monkeypatch.setattr(solve_claude.Path, "home", classmethod(lambda cls: home))
    monkeypatch.delenv("PROGRAMBENCH_CLAUDE_CREDENTIALS_FILE", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stale-key")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "stale-auth")

    args = solve_claude.build_docker_args("container", tmp_path / "prompt", None, None)

    assert "CLAUDE_CODE_OAUTH_TOKEN" in args
    assert "ANTHROPIC_API_KEY" not in args
    assert "ANTHROPIC_AUTH_TOKEN" not in args
    assert not any(".credentials.json" in arg for arg in args)

    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN")
    args = solve_claude.build_docker_args("container", tmp_path / "prompt", None, None)
    assert "ANTHROPIC_API_KEY" in args
    assert not any(".credentials.json" in arg for arg in args)

    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN")
    args = solve_claude.build_docker_args("container", tmp_path / "prompt", None, None)
    assert any(".credentials.json" in arg for arg in args)


def test_selected_claude_credentials_must_exist(tmp_path, monkeypatch):
    solve_claude = load_script("agents/solve_claude.py")
    monkeypatch.setenv("PROGRAMBENCH_CLAUDE_CREDENTIALS_FILE", str(tmp_path / "missing.json"))
    try:
        solve_claude.build_docker_args("container", tmp_path / "prompt", None, None)
    except FileNotFoundError as error:
        assert "Selected Claude credentials file does not exist" in str(error)
    else:
        assert False, "missing selected credentials must fail"


def test_claude_container_script_stages_spec_and_uses_claude_flags():
    solve_claude = load_script("agents/solve_claude.py")

    script = solve_claude.build_container_script(
        "spec-only",
        "claude --dangerously-skip-permissions --print --verbose --output-format stream-json",
        "sonnet",
        "high",
    )

    assert "mode=spec-only" in script
    assert "--exclude=./executable --exclude=executable" in script
    assert 'cmd+=(--model "$claude_model")' in script
    assert 'cmd+=(--effort "$effort")' in script
    assert 'cmd+=("$prompt")' in script
    assert "--config model_reasoning_effort" not in script
    assert "--json" not in script
    assert "--exclude=./executable" in script


def test_claude_trajectory_converts_messages_and_usage(tmp_path):
    converter = load_script("agents/claude_jsonl_to_traj.py")
    events = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Inspecting."},
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "Bash",
                        "input": {"command": "ls"},
                    },
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool-1",
                        "content": "spec.md",
                    }
                ]
            },
        },
        {
            "type": "result",
            "usage": {
                "input_tokens": 10,
                "cache_read_input_tokens": 20,
                "cache_creation_input_tokens": 30,
                "output_tokens": 5,
            },
        },
    ]

    messages = converter.trajectory_messages("prompt", events)

    assert [message["role"] for message in messages] == ["user", "assistant", "assistant", "tool"]
    assert messages[2]["tool_calls"][0]["function"]["name"] == "Bash"
    assert messages[3]["content"] == "spec.md"
    assert converter.result_usage(events)["total_tokens"] == 65

    raw = tmp_path / "events.jsonl"
    raw.write_text("\n".join(json.dumps(event) for event in events) + "\nnot-json\n")
    assert converter.load_events(raw) == events


def test_display_event_summarizes_stream_json_and_passes_through_noise():
    solve_claude = load_script("agents/solve_claude.py")
    assistant = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "thinking", "thinking": "hidden"},
                {"type": "text", "text": "No ncurses headers,\nso I'll do it by hand."},
                {"type": "tool_use", "name": "Bash", "input": {"command": "gcc  -O2   cmatrix.c"}},
                {"type": "tool_use", "name": "Read", "input": {"file_path": "/workspace/spec.md"}},
                {"type": "tool_use", "name": "Bash", "input": {"command": "x" * 400}},
            ]
        },
    }

    assert solve_claude.display_event(json.dumps(assistant), 240).splitlines() == [
        "No ncurses headers, so I'll do it by hand.",
        "[Bash] gcc -O2 cmatrix.c",
        "[Read] /workspace/spec.md",
        ("[Bash] " + "x" * 400)[: solve_claude.PROGRESS_LINE_LIMIT] + "...",
    ]
    # Bookkeeping events carry no message content and must stay silent.
    assert solve_claude.display_event(json.dumps({"type": "system", "subtype": "init", "cwd": "/workspace"}), 240) == ""
    assert solve_claude.display_event(json.dumps({"type": "rate_limit_event", "rate_limit_info": {}}), 240) == ""
    assert solve_claude.display_event("docker: permission denied\n", 240) == "docker: permission denied\n"
