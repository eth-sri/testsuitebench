import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _bash(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_agent_route_precedence_and_retry_overrides() -> None:
    result = _bash(
        ". scripts/construction/agent_routes.sh; "
        "programbench_agent_routes_reset; "
        "programbench_agent_route_register prepare_reference_tests luna xhigh sol high; "
        "programbench_agent_route_register improve_spec sol high; "
        "programbench_agent_route_override model prepare-reference-tests=initial-custom; "
        "programbench_agent_route_override retry-reasoning prepare_reference_tests=max; "
        "programbench_agent_routes_resolve global-model medium; "
        "programbench_agent_routes_print"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "improve_spec\tglobal-model\tmedium\tglobal-model\tmedium",
        "prepare_reference_tests\tinitial-custom\tmedium\tglobal-model\tmax",
    ]


def test_agent_route_rejects_unknown_or_malformed_steps() -> None:
    setup = (
        ". scripts/construction/agent_routes.sh; "
        "programbench_agent_routes_reset; "
        "programbench_agent_route_register valid model high; "
    )
    unknown = _bash(setup + "programbench_agent_route_override model missing=value")
    malformed = _bash(setup + "programbench_agent_route_override model 'bad]name=value'")

    assert unknown.returncode != 0
    assert "Unknown agent route step: missing" in unknown.stderr
    assert malformed.returncode != 0
    assert "Invalid agent route step: bad]name" in malformed.stderr
