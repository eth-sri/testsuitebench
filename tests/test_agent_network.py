from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import pytest

import programbench.constants


def load_solve_codex():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "agents" / "solve_codex.py"
    spec = importlib.util.spec_from_file_location("solve_codex", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("network", "proxy"),
    [("", ""), ("pb-egress", "http://proxy:3128"), ("pb-egress", "")],
)
def test_solve_script_mirrors_the_package_network_args(network, proxy, monkeypatch):
    """solve_codex.py runs under bare python3 and cannot import programbench.

    It therefore carries its own copy of the egress args. A drift between the two
    would confine test generation but leave the solve container on the open
    network, which is exactly the hole the proxy is meant to close.
    """
    monkeypatch.setenv("PROGRAMBENCH_EGRESS_NETWORK", network)
    monkeypatch.setenv("PROGRAMBENCH_EGRESS_PROXY", proxy)
    constants = importlib.reload(programbench.constants)

    assert load_solve_codex().agent_network_args() == constants.agent_network_args()


def test_agent_containers_are_confined_by_default(monkeypatch):
    """A forgotten export must not hand the agent the open internet.

    It did once: a test-generation run cloned the upstream repo of the program it
    was reverse engineering and wrote its suite from the source. Nothing in the
    trajectory recorded that, so the suite looked legitimate. Defaulting to the
    egress network makes the mistake loud (docker fails on a missing network)
    instead of silent.
    """
    monkeypatch.delenv("PROGRAMBENCH_EGRESS_NETWORK", raising=False)
    monkeypatch.delenv("PROGRAMBENCH_EGRESS_PROXY", raising=False)
    args = importlib.reload(programbench.constants).agent_network_args()

    assert args[:2] == ["--network", "pb-egress"]
    assert sum("http://pb-proxy:3128" in arg for arg in args) == 4
    assert load_solve_codex().agent_network_args() == args


def test_opting_out_still_works(monkeypatch):
    """The escape hatch stays, but it now has to be typed."""
    monkeypatch.setenv("PROGRAMBENCH_EGRESS_NETWORK", "")
    assert importlib.reload(programbench.constants).agent_network_args() == []


def test_preflight_blocks_an_unconfined_agent_launch(monkeypatch):
    """Belt and braces for the default: the entrypoints refuse to start.

    Someone debugging with PROGRAMBENCH_EGRESS_NETWORK="" in their shell would
    otherwise burn a multi-hour run producing a contaminated artifact.
    """
    monkeypatch.setenv("PROGRAMBENCH_EGRESS_NETWORK", "")
    monkeypatch.delenv("PROGRAMBENCH_ALLOW_OPEN_NETWORK", raising=False)
    preflight = load_solve_codex().agent_network_preflight

    with pytest.raises(SystemExit):
        preflight()

    monkeypatch.setenv("PROGRAMBENCH_ALLOW_OPEN_NETWORK", "1")
    assert preflight() is None


def test_every_agent_entrypoint_runs_the_preflight():
    """solve_claude and generate_tests_claude reuse solve_codex's docker args.

    An entrypoint that forgets the call keeps the fail-closed default but loses
    the diagnostic, which is the whole point of the guard.
    """
    scripts = Path(__file__).resolve().parents[1] / "scripts" / "agents"
    for name in ("solve_codex.py", "solve_claude.py", "generate_tests_claude.py", "solve_agent.py", "generate_tests_agent.py"):
        source = (scripts / name).read_text()
        assert "agent_network_preflight()" in source, name
        assert source.index("agent_network_preflight()") < source.index("ensure_cleanroom_image(args)"), name


def test_setup_script_provisions_exactly_what_the_defaults_name():
    """The defaults are only fail-closed if something creates what they name.

    A rename on either side leaves docker failing with "network not found" on
    every agent launch, so the two are pinned together here.
    """
    setup = (Path(__file__).resolve().parents[1] / "scripts" / "docker" / "setup_egress_network.sh").read_text()
    constants = importlib.reload(programbench.constants)

    assert f"egress_network={constants.EGRESS_NETWORK}" in setup
    assert f"proxy_name={constants.EGRESS_PROXY.removeprefix('http://').removesuffix(':3128')}" in setup
    assert "network create --internal" in setup


def test_the_proxy_allowlist_covers_the_api_hosts_and_nothing_broad():
    """squid is the only thing standing between the agent and github."""
    config = (Path(__file__).resolve().parents[1] / "scripts" / "docker" / "egress-squid.conf").read_text()
    allowlist = next(line for line in config.splitlines() if line.startswith("acl agent_api"))

    assert allowlist.split()[3:] == [
        ".openai.com", ".chatgpt.com", ".anthropic.com",
        ".googleapis.com", "openrouter.ai",
        "api.z.ai", "zcode.z.ai",
    ]
    assert "http_access deny all" in config


def test_eval_is_offline_by_default_and_tells_the_judges_so(monkeypatch):
    """Eval and eval-tests grade with networking disabled, and the judge prompt must say so.

    The two have to move together. A judge told the candidate was offline while it actually
    reached the network excuses its real DNS and connection behavior as `error`; a judge told
    it had network access while it did not reads every environment failure as evidence about
    the specification. Granting access stays an explicit environment variable.
    """
    monkeypatch.delenv("PROGRAMBENCH_EVAL_NETWORK", raising=False)
    constants = importlib.reload(programbench.constants)
    assert constants.EVAL_NETWORK_ARGS == ["--network", "none"]
    assert "networking disabled" in constants.eval_network_note()

    monkeypatch.setenv("PROGRAMBENCH_EVAL_NETWORK", "bridge")
    constants = importlib.reload(programbench.constants)
    assert constants.EVAL_NETWORK_ARGS == ["--network", "bridge"]
    assert "network access (docker network `bridge`)" in constants.eval_network_note()

    # An empty value drops the flag entirely, which is docker's own default, not isolation.
    monkeypatch.setenv("PROGRAMBENCH_EVAL_NETWORK", "")
    assert importlib.reload(programbench.constants).EVAL_NETWORK_ARGS == []


def test_builds_keep_network_access(monkeypatch):
    """Mutant and reference builds resolve dependencies from the network.

    They share DOCKER_RUN_ARGS with eval, so isolation must not live there.
    """
    constants = importlib.reload(programbench.constants)
    assert "--network" not in constants.DOCKER_RUN_ARGS


@pytest.fixture(autouse=True)
def _restore_constants():
    yield
    importlib.reload(programbench.constants)


def test_analysis_tooling_is_unconfined_unless_a_caller_opts_in():
    """run_codex_in_container stays unconfined by default: callers that still run
    `npx -y @openai/codex@...` fetch the agent from npmjs.org at runtime, which an
    API-only allowlist refuses with a 403. Failure attribution opts in with the
    preinstalled codex so its reference runs see the same offline world the
    candidate was graded in; an npx caller must never opt in.
    """
    import inspect

    from programbench import codex, failure_attribution

    assert inspect.signature(codex.run_codex_in_container).parameters["network_args"].default is None
    assert "npx" not in failure_attribution.DEFAULT_CODEX_COMMAND
    root = Path(__file__).resolve().parents[1] / "src" / "programbench"
    assert "network_args=agent_network_args()" in (root / "failure_attribution.py").read_text()
    for module in root.glob("*.py"):
        source = module.read_text()
        if "npx -y @openai/codex" in source:
            assert "network_args=" not in source, module.name


def test_generation_uses_the_preinstalled_codex_off_the_stock_image():
    """Test generation IS confined, so it must not fetch codex at runtime.

    The cleanroom images pin codex into the image for exactly this reason; only
    ghcr.io/openai/codex-universal, which ships no codex CLI, needs the npx form.
    """
    from programbench.spec_improvement import DEFAULT_CODEX_IMAGE
    from programbench.test_generation import PREINSTALLED_CODEX_COMMAND, _codex_command_for_image

    cleanroom_image = "programbench/x_1776_y.abc1234:task_cleanroom_codex"
    assert _codex_command_for_image(cleanroom_image, "") == PREINSTALLED_CODEX_COMMAND
    assert "npx" not in _codex_command_for_image(cleanroom_image, "")
    assert "npx" in _codex_command_for_image(DEFAULT_CODEX_IMAGE, "")
    assert _codex_command_for_image(cleanroom_image, "custom cmd") == "custom cmd"


def test_cli_does_not_preresolve_the_codex_command(monkeypatch, tmp_path):
    """The CLI must pass codex_command through empty when the user omits it.

    Resolving the npx default at the CLI layer made it look like an explicit
    override, so the image-aware choice below it never ran and test generation
    still tried to fetch codex from npmjs.org behind the egress allowlist.
    """
    from typer.testing import CliRunner

    import programbench.test_generation as tg
    from programbench.cli.main import app

    captured = {}

    def fake_batch(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(tg, "run_codex_test_generation_batch", fake_batch)
    result = CliRunner().invoke(
        app,
        [
            "generate-tests",
            "--model", "gpt-5.6-luna",
            "--filter", "abishekvashok__cmatrix",
            "--cleanroom-dir", str(tmp_path),
            "--cleanroom-base-image", "programbench/x_1776_y.abc1234:task_cleanroom_codex",
            "--output", str(tmp_path / "out"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert captured["codex_command"] == ""


def test_default_codex_command_uses_the_preinstalled_binary():
    """Every image ProgramBench builds pins codex, so the default must not npx.

    The npx form stays only for ghcr.io/openai/codex-universal, which ships no
    codex CLI and is now selected only if PROGRAMBENCH_CODEX_IMAGE asks for it.
    """
    from programbench.spec_improvement import DEFAULT_CODEX_COMMAND, NPX_CODEX_COMMAND

    assert DEFAULT_CODEX_COMMAND.startswith("codex ")
    assert "npx" not in DEFAULT_CODEX_COMMAND
    assert NPX_CODEX_COMMAND.startswith("npx ")


def test_every_codex_call_site_names_its_image():
    """A call site that omits image= silently falls back to codex-universal.

    That image has no codex binary, so with the preinstalled default command it
    would fail with "codex: not found" rather than anything diagnostic.
    """
    import ast

    root = Path(__file__).resolve().parents[1] / "src" / "programbench"
    for module in root.glob("*.py"):
        tree = ast.parse(module.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "run_codex_in_container":
                assert "image" in [kw.arg for kw in node.keywords], f"{module.name}:{node.lineno}"
