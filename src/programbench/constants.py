# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

DOCKER_EXECUTABLE = os.environ.get("PROGRAMBENCH_DOCKER_EXECUTABLE", "docker")
DOCKER_CPUS = int(os.environ.get("PROGRAMBENCH_DOCKER_CPUS", "6"))
DOCKER_RUN_ARGS: list[str] = ["--memory", "60g", "--memory-swap", "60g", "--pids-limit", "2048"]

# Network posture per container role. Deliberately not folded into
# DOCKER_RUN_ARGS: mutant and reference builds share that list and still resolve
# dependencies from the network, so isolating them here would break every build.
#
# Eval (`programbench eval` and `eval-tests`) can run on the bridge network too,
# which is closer to the original ProgramBench eval.
EVAL_NETWORK = os.environ.get("PROGRAMBENCH_EVAL_NETWORK", "none")
EVAL_NETWORK_ARGS: list[str] = ["--network", EVAL_NETWORK] if EVAL_NETWORK else []
# Seconds a test-spawned subprocess may run before the pytest_watchdog plugin kills
# its process tree. Bounds a hanging candidate to one failed test instead of the
# whole branch budget; 0 disables the plugin.
EVAL_SUBPROCESS_TIMEOUT = int(os.environ.get("PROGRAMBENCH_SUBPROCESS_TIMEOUT", "300"))


def eval_network_note() -> str:
    """The sentence judge prompts use to describe the network the executable under test had.

    The judges once hard-coded "networking disabled", and with eval on the bridge network that
    sentence excused every real DNS, proxy and connection failure of the candidate as `error`.
    """
    if EVAL_NETWORK == "none":
        return (
            "The executable was evaluated with networking disabled; a failure whose proximate cause is the "
            "missing network is `error`, never evidence about the specification or the executable."
        )
    return (
        f"The executable was evaluated with network access (docker network `{EVAL_NETWORK}`). DNS, proxy, "
        "connection and HTTP outcomes in a record are its real behavior and are judged like any other "
        "output; only a failure caused by a fixture the test itself failed to provide is `error`."
    )

# Agent containers (solve, test generation) cannot use --network none: the CLI
# agent runs inside the container and needs to reach its model API. They sit on
# a docker network created with --internal, with a dual-homed proxy on it that
# allowlists only the API hosts, so the container gets API access and nothing
# else. scripts/docker/setup_egress_network.sh creates both under these names.
#
# Like EVAL_NETWORK, this fails closed. An unset variable used to mean "open
# internet", which is a silent failure: nothing in a trajectory records that the
# container could reach github, so an agent that read the upstream source it was
# meant to reverse engineer is indistinguishable from one that did not. Set
# PROGRAMBENCH_EGRESS_NETWORK="" to opt a run back out.
EGRESS_NETWORK = os.environ.get("PROGRAMBENCH_EGRESS_NETWORK", "pb-egress")
EGRESS_PROXY = os.environ.get("PROGRAMBENCH_EGRESS_PROXY", "http://pb-proxy:3128")
NO_PROXY_HOSTS = "localhost,127.0.0.1"


def agent_network_args() -> list[str]:
    """Docker args confining an agent container to the egress-filtered network.

    Mirrored by ``agent_network_args`` in scripts/agents/solve_codex.py, which cannot
    import this module; tests/test_agent_network.py asserts the two agree.
    """
    if not EGRESS_NETWORK:
        return []
    args = ["--network", EGRESS_NETWORK]
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        args += ["-e", f"{name}={EGRESS_PROXY}"]
    for name in ("NO_PROXY", "no_proxy"):
        args += ["-e", f"{name}={NO_PROXY_HOSTS}"]
    return args
# Timeouts (seconds) for blocking docker subcommands. Pulls + container start
# can be slow under parallelism, so defaults are generous.
DOCKER_RUN_TIMEOUT = int(os.environ.get("PROGRAMBENCH_DOCKER_RUN_TIMEOUT", "300"))
DOCKER_CP_TIMEOUT = int(os.environ.get("PROGRAMBENCH_DOCKER_CP_TIMEOUT", "300"))
MAX_JUNIT_XML_BYTES = int(os.environ.get("PROGRAMBENCH_MAX_JUNIT_XML_BYTES", str(16 * 1024 * 1024)))
MAX_JUNIT_DIAGNOSTIC_BYTES = int(
    os.environ.get("PROGRAMBENCH_MAX_JUNIT_DIAGNOSTIC_BYTES", str(16 * 1024))
)
MAX_RAW_JUNIT_XML_BYTES = max(
    MAX_JUNIT_XML_BYTES,
    int(os.environ.get("PROGRAMBENCH_MAX_RAW_JUNIT_XML_BYTES", str(256 * 1024 * 1024))),
)

PACKAGE_ROOT = Path(__file__).resolve().parent
# Repository checkout, for the install scripts under scripts/ that are not packaged.
REPO_ROOT = PACKAGE_ROOT.parent.parent
TASKS_DIR = PACKAGE_ROOT / "data" / "tasks"
TEST_BRANCH_CPUS_PATH = PACKAGE_ROOT / "data" / "test_branch_cpus.json"

DOCKER_ORG = os.environ.get("PROGRAMBENCH_DOCKER_ORG", "programbench")

TASK_YAML = "task.yaml"
TESTS_JSON = "tests.json"
WORKSPACE_DIR = "/workspace"
# Build source below /tmp so project-specific metadata baked into /workspace
# (notably .git) cannot affect generated versions or other build discovery.
ISOLATED_BUILD_ROOT = "/tmp/programbench-build"
MUTANT_BUILD_ROOT = f"{ISOLATED_BUILD_ROOT}/mutants"
# Evaluation only round-trips a single `./executable` file across per-branch
# workspace wipes (see Evaluator._stashed_executable in eval.py): it is moved
# out of WORKSPACE_DIR, the workspace is wiped for every test branch, then it
# alone is moved back. A vendored shared library shipped as a WORKSPACE_DIR
# sibling (see reference_test_preparation._BUNDLE_MISSING_LIBRARIES_SHELL)
# would be destroyed by the first wipe. This fixed path outside WORKSPACE_DIR
# survives that cycle the same way the stashed executable does, so the
# executable's RPATH can point here instead of at a sibling directory.
GROUND_TRUTH_LIB_DIR = "/opt/programbench-ground-truth-lib"
# The build directory is baked into compiled binaries (CARGO_MANIFEST_DIR, C's
# __FILE__), so a reference compiled at the build root would differ from every
# mutant systematically. Build it as a sibling of the mutant repositories.
REFERENCE_BUILD_DIR = f"{MUTANT_BUILD_ROOT}/repo_reference"

# eval/run.sh scripts are model-authored and pin no versions, so several install
# pytest unpinned or with --upgrade. pytest 9.1 made "mark applied to a fixture"
# a hard error, which the libtmux plugin trips on load, killing the run before
# collection. pip reads PIP_CONSTRAINT from the environment, so this constrains
# installs inside scripts we do not control.
#
# The file ships in the image: scripts/docker/pip-constraints.txt, installed to this
# path by both task_patched.Dockerfile and codex_cleanroom.Dockerfile, so solve
# and eval resolve runtime installs against the same bounds. Do not write the
# bounds here as well — one copy, in that file.
PIP_CONSTRAINT_PATH = "/opt/programbench/constraints.txt"

# Dependency caches shared by reference and mutant builds. These live on the
# host and are mounted only into build containers, never into one an agent can
# read, so nothing derived from the implementation reaches the cleanroom image.
BUILD_CACHE_ROOT = Path(
    os.environ.get("PROGRAMBENCH_BUILD_CACHE_ROOT", "output/build-cache")
)
# Re-exported rather than relied on from the image ENV so the constraint survives
# a run.sh that resets its environment.
PIN_EVAL_PIP_VERSIONS = f"export PIP_CONSTRAINT={PIP_CONSTRAINT_PATH}; "

# Written into the retained ground-truth implementation by the reference build:
# the newline-delimited paths that ./build.sh creates or rewrites. Mutating any of
# them is a no-op, so the mutant agent is pointed at this list.
GENERATED_FILES_NAME = ".programbench-generated-files"

# Source-tree entries excluded when staging either the retained ground-truth
# implementation or the repository used to generate mutants. Keeping this
# policy shared prevents incidental files from appearing as mutant changes.
SOURCE_COPY_EXCLUDES = frozenset(
    {
        ".git",
        ".gitignore",
        ".venv",
        "eval",
        "node_modules",
        "target",
        "__pycache__",
        ".pytest_cache",
    }
)


def docker_cpus_for_budget(cpu_budget: int, active_workers: int, *, fallback: int = DOCKER_CPUS) -> int:
    """Divide a per-task CPU budget across the workers that can actually run."""
    if cpu_budget <= 0:
        return max(1, fallback)
    return max(1, cpu_budget // max(1, active_workers))


@lru_cache(maxsize=None)
def load_test_branch_cpu_requirements(path: Path = TEST_BRANCH_CPUS_PATH) -> dict[str, Any]:
    """Load and validate fixed per-branch CPU requirements."""
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("default"), int) or data["default"] < 1:
        raise ValueError(f"{path} must define a positive integer default")
    tasks = data.get("tasks")
    if not isinstance(tasks, dict):
        raise ValueError(f"{path} must define a tasks object")
    for task, branches in tasks.items():
        if not isinstance(task, str) or not isinstance(branches, dict):
            raise ValueError(f"{path} has an invalid task entry")
        for branch, cpus in branches.items():
            if not isinstance(branch, str) or not isinstance(cpus, int) or cpus < 1:
                raise ValueError(f"{path} has an invalid CPU requirement for {task}/{branch}")
    return data


def cpus_for_test_branch(instance_id: str, branch: str, *, path: Path = TEST_BRANCH_CPUS_PATH) -> int:
    """Return fixed CPUs for one test branch, falling back to the configured default."""
    data = load_test_branch_cpu_requirements(path)
    tasks = data["tasks"]
    return int(tasks.get(instance_id, {}).get(branch, data["default"]))


HF_REPO_ID = os.environ.get("PROGRAMBENCH_HF_REPO", "programbench/ProgramBench-Tests")
HF_REVISION = os.environ.get("PROGRAMBENCH_HF_REVISION", "main")


def image_name_from_instance_id(instance_id: str) -> str:
    return f"{DOCKER_ORG}/{instance_id.replace('__', '_1776_')}"


def cleanroom_codex_image(instance_id: str) -> str:
    """Task cleanroom image: source removed, reference binary at /workspace/executable."""
    return f"{image_name_from_instance_id(instance_id)}:task_cleanroom_codex"
