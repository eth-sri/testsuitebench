import pytest

from programbench.codex import build_codex_shell_command


def _command(**kwargs):
    return build_codex_shell_command(
        kwargs.pop("codex_command", "codex exec"),
        prompt="write the spec",
        diagnostic_action="improve the spec",
        **kwargs,
    )


def test_web_search_is_disabled_so_specs_come_from_the_local_suite():
    command = _command(model="gpt-5.6", reasoning_effort="high")

    assert "--config tools.web_search=false" in command
    assert "--model gpt-5.6" in command
    assert command.endswith("'write the spec'")


def test_explicit_web_search_setting_is_not_overridden():
    command = _command(codex_command="codex exec --config tools.web_search=true")

    assert "tools.web_search=true" in command
    assert "tools.web_search=false" not in command


@pytest.mark.parametrize("bad", ["codex --help", "codex exec --version", ""])
def test_rejects_commands_that_cannot_run_an_agent(bad):
    with pytest.raises(RuntimeError):
        _command(codex_command=bad)


def test_completed_event_parser_ignores_valid_json_scalars():
    from programbench.spec_improvement import _codex_completed_event

    assert _codex_completed_event("55") is None
    assert _codex_completed_event('"postflight output"') is None
    assert _codex_completed_event('{"type":"turn.completed"}') == {"type": "turn.completed"}
