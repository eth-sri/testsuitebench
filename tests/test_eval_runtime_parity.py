from __future__ import annotations

import re
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "docker"
DOCKERFILE = SCRIPTS / "programbench_image.Dockerfile"
REQUIREMENTS = SCRIPTS / "eval-runtime-requirements.txt"
CONSTRAINTS = SCRIPTS / "pip-constraints.txt"
PROBE = SCRIPTS / "programbench_image_probe.sh"
INSTALL_SCRIPTS = (
    SCRIPTS / "install_codex_cleanroom.sh",
    SCRIPTS / "install_claude_cleanroom.sh",
    SCRIPTS / "install_agent_cleanroom.sh",
    SCRIPTS / "install_task_patched.sh",
)


def requirement_names(text: str) -> set[str]:
    names = set()
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if line:
            names.add(re.split(r"[<>=!~\[]", line)[0].lower())
    return names


def test_every_step_builds_from_one_dockerfile():
    """Solve, test generation and eval must not drift apart again.

    They previously lived in three Dockerfiles that had to be edited together;
    the whole point of the AGENT parameter is that there is now nothing to keep
    in sync. A second Dockerfile reintroduces the drift this replaced.
    """
    for script in INSTALL_SCRIPTS:
        assert "scripts/docker/programbench_image.Dockerfile" in script.read_text()
    assert not list(SCRIPTS.glob("*cleanroom.Dockerfile"))
    assert not (SCRIPTS / "task_patched.Dockerfile").exists()


@pytest.mark.parametrize(("agent",), [("codex",), ("claude",), ("gemini",), ("qwen",), ("deepseek",), ("glm",), ("none",)])
def test_dockerfile_accepts_every_agent_variant(agent: str):
    assert f"      {agent})" in DOCKERFILE.read_text()


def test_grading_image_has_no_agent_cli():
    """AGENT=none is the grader.

    A submitted compile.sh that can invoke codex or claude could write the
    implementation at grading time, so the CLI install must sit behind the case
    arm and never in an unconditional layer.
    """
    text = DOCKERFILE.read_text()
    assert "AGENT=none" in (SCRIPTS / "install_task_patched.sh").read_text()
    before_case = text.split("case \"${AGENT}\"")[0]
    for marker in ("npm install -g", "claude.ai/install.sh"):
        assert marker not in before_case, f"{marker} must be inside the AGENT case"


def test_grading_image_shares_the_agent_runtime_except_the_cli():
    """Node is unconditional: the agent can use it, so the grader must have it too.

    Only the CLI install is gated on AGENT, so the sole difference between the
    solve image and the grader is the codex/claude command.
    """
    text = DOCKERFILE.read_text()
    before_case = text.split("case \"${AGENT}\"")[0]
    assert "apt-get install -y --no-install-recommends nodejs" in before_case
    assert "process.versions.node" in PROBE.read_text()


def test_agent_versions_are_pinned():
    """An unpinned installer makes two rebuilds produce two different agents."""
    text = DOCKERFILE.read_text()
    assert re.search(r"ARG CODEX_VERSION=\d+\.\d+\.\d+", text)
    assert re.search(r"ARG CLAUDE_VERSION=\d+\.\d+\.\d+", text)
    assert re.search(r"ARG GEMINI_VERSION=\d+\.\d+\.\d+", text)
    assert re.search(r"ARG QWEN_VERSION=\d+\.\d+\.\d+", text)
    assert 'bash -s "${CLAUDE_VERSION}"' in text
    assert '"@openai/codex@${CODEX_VERSION}"' in text
    assert '"@google/gemini-cli@${GEMINI_VERSION}"' in text
    assert '"@qwen-code/qwen-code@${QWEN_VERSION}"' in text
    assert re.search(r"claude_version=\$\{PROGRAMBENCH_CLAUDE_VERSION:-\d+\.\d+\.\d+\}",
                     (SCRIPTS / "install_claude_cleanroom.sh").read_text())
    agent_installer = (SCRIPTS / "install_agent_cleanroom.sh").read_text()
    assert re.search(r"gemini_version=\$\{PROGRAMBENCH_GEMINI_VERSION:-\d+\.\d+\.\d+\}", agent_installer)
    assert re.search(r"qwen_version=\$\{PROGRAMBENCH_QWEN_VERSION:-\d+\.\d+\.\d+\}", agent_installer)


def test_requirements_cover_what_generated_run_sh_installs():
    """pip exits non-zero offline only when a requested package is missing.

    These are the packages the reference eval/run.sh scripts install at runtime;
    dropping one silently reintroduces a network dependency at eval time.
    """
    required = {
        "pytest",
        "pytest-xdist",
        "pytest-timeout",
        "pytest-dependency",
        "pytest-rerunfailures",
        "libtmux",
        "pexpect",
        "pyyaml",
        "lxml",
        "beautifulsoup4",
        "pillow",
        "numpy",
        "xattr",
        "piexif",
    }
    assert required <= requirement_names(REQUIREMENTS.read_text())


def test_libtmux_stays_pinned_above_the_pytest_91_breakage():
    assert "libtmux>=0.62.0" in REQUIREMENTS.read_text()
    assert "pytest<9.1" in CONSTRAINTS.read_text()


def test_runtime_constraint_points_at_the_shipped_file():
    """The eval harness re-exports PIP_CONSTRAINT before running run.sh.

    It must point at the constraint the image actually installs, so a runtime
    `pip install -U pytest` resolves against the same bounds during solve and
    during eval, and the bounds must not be restated in constants.py.
    """
    from programbench.constants import PIN_EVAL_PIP_VERSIONS, PIP_CONSTRAINT_PATH

    assert f"COPY scripts/docker/pip-constraints.txt {PIP_CONSTRAINT_PATH}" in DOCKERFILE.read_text()
    assert PIN_EVAL_PIP_VERSIONS == f"export PIP_CONSTRAINT={PIP_CONSTRAINT_PATH}; "
    assert "pytest" not in PIN_EVAL_PIP_VERSIONS


def test_one_rebuild_rule_for_every_variant():
    """The probes decided *whether* to rebuild, and they had drifted apart.

    Each script used to inline its own check, and they covered different property
    sets: only the codex script looked at sccache, only codex and claude at the
    apt lock wrapper. An image cached before one of those layers existed stayed
    "fresh" under one script while another rebuilt it, so the grader silently
    stopped being the image the agent solved in -- the drift the single
    Dockerfile exists to prevent, one level up. The agent CLI is the only
    parameter; everything else must live in the shared helper.
    """
    probe = PROBE.read_text()
    for check in (
        "python3 -m pip install --no-index -q -r /opt/programbench/requirements.txt",
        'test -s \\"\\$PIP_CONSTRAINT\\"',
        "programbench-apt-flock",
        "sccache ${PROGRAMBENCH_SCCACHE_VERSION}",
        "process.versions.node",
    ):
        assert check in probe

    for script in INSTALL_SCRIPTS:
        text = script.read_text()
        assert ". scripts/docker/programbench_image_probe.sh" in text
        assert "programbench_image_is_fresh" in text
        assert "docker run" not in text, f"{script.name} must not carry its own probe"


def test_probe_sccache_pin_matches_the_dockerfile():
    """A probe that accepts a version the image no longer installs never rebuilds."""
    version = re.search(r"ARG SCCACHE_VERSION=(\S+)", DOCKERFILE.read_text()).group(1)
    assert f"PROGRAMBENCH_SCCACHE_VERSION={version}" in PROBE.read_text()


def test_preinstalled_runtime_covers_every_package_the_reference_suites_install():
    """Offline eval only works if nothing a run.sh installs has to be fetched.

    The suites are model-authored and install their dependencies at runtime, so a
    package missing from these two lists makes pip exit non-zero. Under `set -e`
    that aborts run.sh before it writes results.xml and every test in the branch
    is recorded as an error, which is how axodotdev__oranda reported 56% accuracy
    while actually passing 95% of the tests that ran.
    """
    suites = Path(__file__).resolve().parents[1] / "extracted-tests"
    if not suites.is_dir():
        pytest.skip("extracted-tests/ is not present in this checkout")

    shared = requirement_names(REQUIREMENTS.read_text()) | {"pip", "setuptools", "wheel"}
    per_task = {
        script.name[: -len(".sh")]: set(re.findall(r"pip install -q (.+)", script.read_text()))
        for script in (SCRIPTS / "eval_deps").glob("*.sh")
    }

    missing: dict[str, set[str]] = {}
    for run_sh in suites.glob("*/*/eval/run.sh"):
        for line in run_sh.read_text(errors="replace").splitlines():
            line = line.strip()
            if line.startswith(("#", "echo")):
                continue
            match = re.search(r"\bpip3?\s+install\b(.*)", line)
            if not match:
                continue
            for token in re.split(r"[|&;><#]", match.group(1))[0].split():
                if token.startswith("-"):
                    continue
                name = re.split(r"[<>=!~\[]", token)[0].strip().strip("\"'").lower()
                if not name or name.isdigit() or not re.fullmatch(r"[a-z][a-z0-9._-]*", name) or name.endswith(".txt"):
                    continue
                instance = run_sh.parts[-4]
                covered = shared | {
                    pkg for line in per_task.get(instance, set()) for pkg in line.split()
                }
                if name not in covered:
                    missing.setdefault(instance, set()).add(name)

    assert not missing, f"reference suites install packages that are not preinstalled: {missing}"


def test_per_task_eval_dependencies_are_identical_in_every_image():
    """A package must never appear or vanish between writing code and grading it.

    scripts/docker/eval_deps/ is keyed by instance id, so if one builder passes TASK and
    another does not, the agent writes against a runtime the grader does not have
    -- or worse, passes eval using a package it could never have imported while
    solving. These are allowed to be visible to the agent; they are not allowed
    to differ, which is the same reason the runtime lives in one Dockerfile.
    """
    hook = DOCKERFILE.read_text().split("COPY scripts/docker/eval_deps")[1].split("\n\n")[0]
    assert "${TASK}" in hook
    assert '"${AGENT}"' not in hook, "the hook must not be gated on the agent variant"

    for script in INSTALL_SCRIPTS:
        assert '--build-arg "TASK=${task}"' in script.read_text(), f"{script.name} must pass TASK"


@pytest.mark.parametrize(("script",), [(p,) for p in sorted((SCRIPTS / "eval_deps").glob("*.sh"))])
def test_per_task_eval_dependency_script_is_named_for_a_real_instance(script: Path):
    """A typo in the filename is silent: the Dockerfile just never runs it."""
    suites = Path(__file__).resolve().parents[1] / "extracted-tests"
    if not suites.is_dir():
        pytest.skip("extracted-tests/ is not present in this checkout")
    assert (suites / script.name[: -len(".sh")]).is_dir()
    assert script.read_text().startswith("#!/usr/bin/env bash\nset -euo pipefail")
