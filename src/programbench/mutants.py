# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Generate mutant repositories with Codex in Docker."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import re
import shlex
import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from programbench.codex import build_codex_shell_command
from programbench.constants import (
    BUILD_CACHE_ROOT,
    DOCKER_CPUS,
    DOCKER_EXECUTABLE,
    DOCKER_RUN_ARGS,
    ISOLATED_BUILD_ROOT,
    MUTANT_BUILD_ROOT,
    SOURCE_COPY_EXCLUDES,
)
from programbench.container import ContainerEnvironment
from programbench.mutant_candidate_selection import (
    candidate_assignment_id,
)
from programbench.mutant_storage import (
    compact_mutant_suite,
    deduplicate_mutant_files,
    file_sha256,
    mutant_store_state,
)
from programbench.generated_files import load_generated_files
from programbench.mutant_planning import MUTANT_PLAN_FILENAME, load_and_build_mutant_plan
from programbench.source_build import (
    CLEAR_BUILD_ROOT_SHELL,
    build_cache_args,
    resolve_build_image,
    select_build_branch,
)
from programbench.spec_improvement import (
    DEFAULT_CODEX_AUTH_FILE,
    DEFAULT_CODEX_COMMAND,
    _collect_codex_json_events,
    _copy_codex_auth_to_container,
    _copy_dir_from_container,
    _copy_specification_to_container,
    _forwarded_env,
    _instance_source,
    _progress_phase,
)
from programbench.test_generation import (
    _cleanroom_base_image,
    _write_codex_trajectory,
)
from programbench.utils.instance_filters import filter_instances
from programbench.utils.load_data import load_all_instances
from programbench.utils.mutant_store import resolve_mutants_dir

log = logging.getLogger(__name__)

DEFAULT_MUTANT_CODEX_LOG_DIR = os.environ.get("PROGRAMBENCH_MUTANT_CODEX_LOG_DIR", "output/mutants/editlog")
_MUTANT_PARALLEL_BUILD_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "construction" / "build_mutant_repos_parallel.sh"
_MUTANT_BUILD_ROOT = MUTANT_BUILD_ROOT
_MUTANT_COPY_EXCLUDES = [
    ".git",
    ".venv",
    "executable",
    "target",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
]
MUTANT_MANIFEST_FILENAME = "mutants.json"
MUTANT_GENERATION_GOAL_COMMAND = (
    "/goal Follow the full task in codex-goal.md. Implement exactly the mutant assignments in mutant_plan.json."
)
MUTANT_GENERATION_PROMPT = """\
You are creating a mutant suite.

## Workspace

- `specification/`: contains the task specification. We aim to perform mutation testing to detect executables that violate the specification.
- `repo/`: contains the ground-truth implementation and `build.sh`, which creates an executable binary.
- `reference-tests/`: contains the immutable active reference-test sources used to construct the plan.
- `mutant_plan.json`: the authoritative list of `(target_spec, target_test)` assignments.
- `mutants.json`: a manifest pre-seeded with exactly the planned mutant IDs and targets.

## Task

Create exactly the mutants in `mutant_plan.json`. Each mutant must violate its assigned specification rule in the narrowest way that is expected to make its assigned test fail while every other active reference-test function continues to pass.

## Workflow

1. Read every assignment in `mutant_plan.json` and inspect its exact `target_spec` and `target_test` source.
2. For every assignment, make exactly one copy of `repo/` whose directory name equals `mutant_id`.
3. Modify source code or build inputs so the assigned specification rule is violated specifically at the behavior asserted by `target_test`. Leave a `[MUTATED]` comment identifying that scope.
4. Keep each copied repository `build.sh` compatible with the original repository build contract.
5. After creating all mutants and updating `mutants.json`, stop. The script will compile the repositories after your turn and will resume this same session with a build report if repairs are needed.

## Rules

- The plan is immutable: do not add, remove, rename, merge, or retarget assignments.
- Create every planned repository exactly once and create no unplanned `repo_*` repositories.
- A valid mutant is intended to have the singleton kill set `{target_test}`. Avoid changes that affect other reference tests, unrelated crashes, global timeouts, or broad output corruption.
- Do not detect the test environment, test name, harness process, or fixture inputs merely to force the assigned test to fail.
- Mutate the logic that produces the behavior: do not be based on literal argument, filename, or payload strings copied from `target_test`, and do not post-process a correct result back into a wrong one. A mutant must be a rule a re-implementer could plausibly get wrong across all inputs in its class.
- Include every generated `repo_*` repository exactly once in `/workspace/mutants.json`.
- Avoid exact full error-message assertions unless they are important; exit codes and functional effects are more important.
- Do not create wrapper/proxy executables that delegate to `/workspace/executable`, `./executable`, or another reference executable. Mutants must be self-contained outputs of their repository build, because evaluation installs each candidate as `/workspace/executable`.
- Do not replace `build.sh` with a script whose main purpose is to write a shell wrapper instead of building the mutated implementation.
- Do not compile or run the mutants yourself: do not invoke `build.sh`, `make`, or a parallel-build helper. The script owns compilation so resource limits and logs remain deterministic.

## Output

- Leave every generated mutant in a numbered `repo_*` repository.
- After defining all repositories, edit `/workspace/mutants.json` so its top-level `mutants` array contains one entry per generated mutant.

Here are the entries you have to fill; the rest are pre-seeded:

- `mutation`: required. The behavior summary and the mutation details -- which specification rule is violated, and how the source change violates it.

Leave every other field -- `id`, `assignment_id`, `candidate_index`, `target_spec`, `target_test`, and `target_test_description` -- exactly as seeded. Do not add, remove, or reorder entries.
"""


def mutant_generation_prompt() -> str:
    return MUTANT_GENERATION_PROMPT


class MutantArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: str
    compression: Literal["gzip"] = "gzip"
    path: str
    size: int


class MutantSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["wrapper"] = "wrapper"
    target_spec: str = ""
    target_test: str = ""
    target_test_description: str = ""
    mutation: str = ""
    assignment_id: str = ""
    candidate_index: int = 1
    payload: str
    artifact: MutantArtifact | None = None

    def payload_path(self, instance_root: Path) -> Path:
        return instance_root / self.payload


class MutantSuite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance_id: str
    mutants: list[MutantSpec]


def load_mutant_suite(mutants_dir: str | Path, instance_id: str) -> tuple[Path, MutantSuite] | None:
    """Load mutant executables used by eval-tests, if present.

    Prefer the legacy manifest format when it exists, and otherwise discover
    Codex-generated mutant repositories written as repo_*/executable.
    """
    instance_root = resolve_mutants_dir(str(mutants_dir), instance_id) / instance_id
    manifest_path = instance_root / MUTANT_MANIFEST_FILENAME
    if not manifest_path.exists():
        mutants = [
            MutantSpec(
                id=repo_dir.name,
                payload=f"{repo_dir.name}/executable",
            )
            for repo_dir in sorted(instance_root.glob("repo_*"))
            if re.fullmatch(r"repo_[0-9]+", repo_dir.name) and repo_dir.is_dir() and (repo_dir / "executable").is_file()
        ]
        if not mutants:
            return None
        suite = MutantSuite(instance_id=instance_id, mutants=mutants)
        return instance_root, suite
    data = json.loads(manifest_path.read_text())
    for mutant in data.get("mutants", []):
        for field in ("behavioral_dimension", "mutation_operator", "mutation_location"):
            mutant.pop(field, None)
    suite = MutantSuite.model_validate(data)
    return instance_root, suite


def _canonical_target_spec(value: str) -> str:
    match = re.search(r"\bSpec\s+(\d+)\b", value, flags=re.IGNORECASE)
    if match:
        return f"Spec {int(match.group(1))}"
    return value


def _mutant_repo_sort_key(repo_name: str) -> tuple[int, str]:
    match = re.fullmatch(r"repo_(\d+)", repo_name)
    if match is None:
        return (2**63 - 1, repo_name)
    return (int(match.group(1)), repo_name)


def _normalize_mutant_manifest(
    data: dict[str, Any] | None,
    *,
    instance_id: str,
    repo_names: list[str],
    plan: dict[str, Any],
) -> dict[str, Any]:
    raw_mutants = data.get("mutants", []) if isinstance(data, dict) else []
    raw_by_id = {
        str(item.get("id", "")): item
        for item in raw_mutants
        if isinstance(item, dict) and item.get("id")
    }
    mutants: list[dict[str, str]] = []
    planned_by_id = {str(item["mutant_id"]): item for item in plan.get("assignments", [])}
    for repo_name in sorted(repo_names, key=_mutant_repo_sort_key):
        raw = raw_by_id.get(repo_name, {})
        assignment_id = candidate_assignment_id({"id": repo_name})
        planned = planned_by_id[assignment_id]
        candidate_index = int(raw.get("candidate_index") or (
            repo_name.rpartition("__candidate_")[2] if "__candidate_" in repo_name else 1
        ))
        target_spec = str(planned["target_spec"])
        target_test = str(planned["target_test"])
        mutation = str(raw.get("mutation", "") or "")
        mutants.append(
            {
                "id": repo_name,
                "kind": "wrapper",
                "payload": f"{repo_name}/executable",
                "target_spec": target_spec,
                "target_test": target_test,
                "target_test_description": str(planned["target_test_description"]),
                "mutation": mutation,
                "assignment_id": assignment_id,
                "candidate_index": candidate_index,
            }
        )
    return {"instance_id": instance_id, "mutants": mutants}


def _read_container_mutant_manifest(env: ContainerEnvironment) -> dict[str, Any] | None:
    result = env.execute(f"if [ -f /workspace/{MUTANT_MANIFEST_FILENAME} ]; then cat /workspace/{MUTANT_MANIFEST_FILENAME}; fi")
    if result["returncode"] != 0:
        log.warning("Failed to read container mutant manifest: %s", result["output"].strip())
        return None
    text = (result.get("stdout") or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        log.warning("Ignoring invalid container mutant manifest: %s", exc)
        return None
    if not isinstance(data, dict):
        log.warning("Ignoring container mutant manifest because the top-level JSON value is not an object")
        return None
    return data


def _write_mutant_manifest(
    *,
    target_root: Path,
    instance_id: str,
    repo_names: list[str],
    data: dict[str, Any] | None,
    plan: dict[str, Any],
) -> Path:
    manifest = _normalize_mutant_manifest(
        data, instance_id=instance_id, repo_names=repo_names, plan=plan,
    )
    manifest_path = target_root / MUTANT_MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest_path


def _mutant_codex_shell_command(
    codex_command: str,
    *,
    model: str = "",
    reasoning_effort: str = "",
) -> str:
    return build_codex_shell_command(
        codex_command,
        prompt=MUTANT_GENERATION_GOAL_COMMAND,
        model=model,
        reasoning_effort=reasoning_effort,
        diagnostic_action="generate mutants",
    )


def _mutant_codex_resume_shell_command(
    codex_command: str,
    *,
    session_id: str,
    prompt: str,
    model: str = "",
    reasoning_effort: str = "",
) -> str:
    """Build a non-interactive command that resumes the original Codex thread."""
    parts = shlex.split(codex_command)
    if not parts:
        raise RuntimeError("codex_command must not be empty")
    try:
        exec_index = parts.index("exec")
    except ValueError as error:
        raise RuntimeError("codex_command must contain the `exec` subcommand") from error
    if not {"--dangerously-bypass-approvals-and-sandbox", "--yolo"}.intersection(parts):
        parts.insert(exec_index, "--dangerously-bypass-approvals-and-sandbox")
        exec_index += 1
    # Resume uses the container process cwd and does not accept --cd/-C.
    for cwd_flag in ("--cd", "-C"):
        while cwd_flag in parts:
            flag_index = parts.index(cwd_flag)
            del parts[flag_index : flag_index + 2]
            if flag_index < exec_index:
                exec_index -= 2
    parts.insert(exec_index + 1, "resume")
    if model:
        parts.extend(["--model", model])
    if reasoning_effort:
        parts.extend(["--config", f"model_reasoning_effort={reasoning_effort}"])
    if "--json" not in parts:
        parts.append("--json")
    parts.extend([session_id, prompt])
    return " ".join(shlex.quote(part) for part in parts)


def _codex_thread_id(events: list[dict[str, Any]]) -> str:
    for event in events:
        if event.get("type") == "thread.started" and event.get("thread_id"):
            return str(event["thread_id"])
    return ""


MUTANT_BUILD_REPAIR_PROMPT = """\
The script compiled the mutant repositories after your previous turn and some failed.
Read `/workspace/mutant-build-report.json` and its referenced build log.
Its `failed_repositories` names exactly what to repair, and `log` says why: either the repository did not compile, or it compiled into an executable identical to another mutant's, which means the edit never reached the binary.
Repair only those repositories so that every planned one compiles into a distinct executable.
Do not run build.sh, make, or the parallel build helper yourself; the script will compile again after this turn.
Keep mutant_plan.json and all target assignments unchanged.
"""


def _repo_copy_ignore(_dir: str, names: list[str]) -> list[str]:
    return [name for name in names if name in SOURCE_COPY_EXCLUDES]


_PRECOMPILED_EXECUTABLE_ARTIFACTS = (
    "executable",
    "executable_cov",
    "executable_nocov",
)


def _copy_repo_to_container(
    env: ContainerEnvironment, branch: Path, generated_files: list[str],
) -> None:
    """Copy source to /workspace/repo without tests or precompiled binaries.

    Recorded generated paths are withheld too. build.sh recreates them, so a
    mutation applied to one is discarded before the compiler sees it and the
    agent cannot tell. Withholding them points the agent at the real build input;
    _restore_generated_files puts them back before the mutants are compiled.
    """
    with tempfile.TemporaryDirectory(prefix="programbench-mutant-repo-") as tmp_dir:
        staged_repo = Path(tmp_dir) / "repo"
        shutil.copytree(branch, staged_repo, ignore=_repo_copy_ignore, symlinks=True)
        for name in [*_PRECOMPILED_EXECUTABLE_ARTIFACTS, *generated_files]:
            artifact = staged_repo / name
            if artifact.is_symlink() or artifact.is_file():
                artifact.unlink()
        env.copy_in(staged_repo, "/workspace/repo")


def _restore_generated_files(
    target_root: Path, repo_names: list[str], *, branch: Path, generated_files: list[str],
) -> None:
    """Put the withheld generated paths back so each mutant builds from a complete tree.

    The build's own executable is recorded as generated too, and restoring that
    would hand every mutant the ground-truth binary before it is compiled.
    """
    restorable = [name for name in generated_files if name not in _PRECOMPILED_EXECUTABLE_ARTIFACTS]
    for repo_name in repo_names:
        for name in restorable:
            source = branch / name
            if not source.is_file():
                continue
            destination = target_root / repo_name / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _copy_planned_reference_tests_to_container(
    env: ContainerEnvironment, reference_tests: Path, mutant_plan: dict[str, Any],
) -> None:
    branches = sorted({str(item["target_test_branch"]) for item in mutant_plan["assignments"]})
    with tempfile.TemporaryDirectory(prefix="programbench-mutant-reference-tests-") as tmp_dir:
        staged = Path(tmp_dir) / "reference-tests"
        staged.mkdir()
        tests_manifest = reference_tests / "tests.json"
        if tests_manifest.is_file():
            shutil.copy2(tests_manifest, staged / "tests.json")
        for branch in branches:
            source = reference_tests / branch / "eval"
            if not source.is_dir():
                raise FileNotFoundError(f"Planned reference-test branch has no eval directory: {source}")
            shutil.copytree(source, staged / branch / "eval", symlinks=True)
        env.copy_in(staged, "/workspace/reference-tests")


def _candidate_manifest_seed(plan: dict[str, Any], previous_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    seeded: list[dict[str, Any]] = []
    for assignment in plan["assignments"]:
        mutant_id = str(assignment["mutant_id"])
        previous = previous_by_id.get(mutant_id, {})
        seeded.append({
            "id": mutant_id,
            "assignment_id": mutant_id,
            "candidate_index": 1,
            "target_spec": assignment["target_spec"],
            "target_test": assignment["target_test"],
            "target_test_description": assignment["target_test_description"],
            "mutation": str(previous.get("mutation", "")),
        })
    return sorted(seeded, key=lambda mutant: _mutant_repo_sort_key(str(mutant["id"])))


def _prepare_mutant_workspace(
    env: ContainerEnvironment,
    *,
    specification: Path,
    branch: Path,
    generated_files: list[str],
    reference_tests: Path,
    mutant_plan: dict[str, Any],
    previous_manifest: Path | None = None,
) -> None:
    result = env.execute(
        "rm -rf /workspace/specification /workspace/reference-tests /workspace/repo /workspace/repo_* "
        "/workspace/codex-goal.md /workspace/mutants.json /workspace/mutant_plan.json "
        "&& mkdir -p /workspace"
    )
    if result["returncode"] != 0:
        raise RuntimeError(f"failed to initialize workspace: {result['output'].strip()}")
    _copy_specification_to_container(env, specification)
    _copy_repo_to_container(env, branch, generated_files)
    _copy_planned_reference_tests_to_container(env, reference_tests, mutant_plan)
    with tempfile.TemporaryDirectory(prefix="programbench-mutant-manifest-") as tmp_dir:
        previous_by_id: dict[str, Any] = {}
        if previous_manifest is not None and previous_manifest.is_file():
            previous_data = json.loads(previous_manifest.read_text())
            previous_by_id = {str(item.get("id", "")): item for item in previous_data.get("mutants", [])}
        manifest_path = Path(tmp_dir) / MUTANT_MANIFEST_FILENAME
        manifest_path.write_text(json.dumps({
            "instance_id": mutant_plan["instance_id"],
            "mutants": _candidate_manifest_seed(mutant_plan, previous_by_id),
        }, indent=2) + "\n")
        env.copy_in(manifest_path, f"/workspace/{MUTANT_MANIFEST_FILENAME}")
        plan_path = Path(tmp_dir) / MUTANT_PLAN_FILENAME
        plan_path.write_text(json.dumps(mutant_plan, indent=2, sort_keys=True) + "\n")
        env.copy_in(plan_path, f"/workspace/{MUTANT_PLAN_FILENAME}")
    with tempfile.TemporaryDirectory(prefix="programbench-mutant-goal-") as tmp_dir:
        goal_path = Path(tmp_dir) / "codex-goal.md"
        goal_path.write_text(mutant_generation_prompt())
        env.copy_in(goal_path, "/workspace/codex-goal.md")


def _candidate_instance_dirs(repo_dir: Path) -> list[dict[str, Any]]:
    loaded_by_id = {instance["instance_id"]: instance for instance in load_all_instances(include_tests=False)}
    instances: list[dict[str, Any]] = []
    for path in sorted(repo_dir.iterdir() if repo_dir.is_dir() else []):
        if not path.is_dir():
            continue
        loaded = dict(loaded_by_id.get(path.name, {}))
        loaded["instance_id"] = path.name
        instances.append(loaded)
    return instances


def _test_spec_links_path(root: Path, instance_id: str) -> Path:
    if root.is_file():
        return root
    return root / instance_id / "test_spec_links.json"


def _container_repo_names(env: ContainerEnvironment) -> list[str]:
    command = "find /workspace -maxdepth 1 -type d -name 'repo_*' -printf '%f\n' | sort"
    result = env.execute(command)
    if result["returncode"] != 0:
        raise RuntimeError(f"failed to list generated mutant repositories: {result['output'].strip()}")
    return [
        line.strip()
        for line in result.get("stdout", "").splitlines()
        if re.fullmatch(r"repo_[A-Za-z0-9_.-]+", line.strip())
    ]


def _copy_mutant_repositories_from_container(
    env: ContainerEnvironment,
    *,
    target_root: Path,
    force: bool,
    include_executables: bool = False,
) -> list[str]:
    repo_names = _container_repo_names(env)
    if not repo_names:
        return []

    candidate_root = target_root.with_name(f".{target_root.name}.candidate-{os.getpid()}-{time.time_ns()}")
    shutil.rmtree(candidate_root, ignore_errors=True)
    candidate_root.mkdir(parents=True, exist_ok=True)
    excludes = [
        name
        for name in _MUTANT_COPY_EXCLUDES
        if not (include_executables and name == "executable")
    ]
    try:
        if hasattr(env, "copy_out_dir"):
            env.copy_out_dir("/workspace", candidate_root, excludes=excludes, members=repo_names)
        else:
            for repo_name in repo_names:
                _copy_dir_from_container(
                    env, f"/workspace/{repo_name}", candidate_root / repo_name, excludes=excludes,
                )
        if target_root.exists():
            if not force:
                raise FileExistsError(f"{target_root} already exists; pass --force to overwrite")
            shutil.rmtree(target_root)
        candidate_root.replace(target_root)
        return repo_names
    finally:
        shutil.rmtree(candidate_root, ignore_errors=True)


_MUTANT_FORBIDDEN_EXECUTABLE_REFERENCES = (
    "/workspace/executable",
    "AST_GREP_BASE_EXECUTABLE",
    "BASE_EXECUTABLE",
)


def _ensure_mutant_executables_are_readable(target_root: Path, repo_names: list[str]) -> None:
    """Make generated mutant executables readable so host-side tar can copy them."""
    for repo_name in repo_names:
        executable = target_root / repo_name / "executable"
        if not executable.is_file():
            continue
        mode = executable.stat().st_mode & 0o7777
        executable.chmod(mode | 0o555)


def _mutant_repository_policy_violations(repo_path: Path) -> list[str]:
    """Return policy issues that make a generated mutant unsafe to evaluate."""
    violations: list[str] = []
    for path in (repo_path / "build.sh", repo_path / "executable"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError as exc:
            violations.append(f"{path.name}: cannot read file: {exc}")
            continue
        for marker in _MUTANT_FORBIDDEN_EXECUTABLE_REFERENCES:
            if marker in text:
                violations.append(
                    f"{path.name}: references {marker!r}, which can recurse when the mutant is installed as /workspace/executable"
                )
                break
    return violations


def _no_op_build_repositories(target_root: Path, repo_names: list[str]) -> set[str]:
    """Repositories whose builds are byte-identical, so their mutations changed no build input.

    Distinct mutations cannot compile to the same bytes. Sharing a digest means the
    edits landed on files the build regenerates (or on nothing the build reads).
    """
    by_digest: dict[str, list[str]] = {}
    for repo_name in repo_names:
        executable = target_root / repo_name / "executable"
        if executable.is_file():
            by_digest.setdefault(file_sha256(executable), []).append(repo_name)
    return {name for group in by_digest.values() if len(group) > 1 for name in group}


def _validate_mutant_repositories(
    target_root: Path,
    repo_names: list[str],
    *,
    require_executable: bool = False,
) -> dict[str, list[str]]:
    invalid: dict[str, list[str]] = {}
    for repo_name in repo_names:
        repo_path = target_root / repo_name
        violations = _mutant_repository_policy_violations(repo_path)
        if require_executable and not (repo_path / "executable").is_file():
            violations.append("executable: missing after agent-side build validation")
        if violations:
            invalid[repo_name] = violations
    return invalid


def _log_invalid_mutants(instance_id: str, invalid_mutants: dict[str, list[str]]) -> None:
    """Log every repository policy violation before returning a generic batch status."""
    for repo_name, violations in sorted(invalid_mutants.items()):
        for violation in violations:
            log.error("%s: invalid mutant %s: %s", instance_id, repo_name, violation)


def _mutant_build_output_callback(instance_id: str):
    """Forward concise build counters while retaining the full build log in-container."""
    def callback(_stream_name: str, line: str) -> None:
        if line.startswith("[mutant-build-"):
            log.info("%s: %s", instance_id, line.rstrip())

    return callback


def _copy_repo_list_into_container(env: ContainerEnvironment, repo_names: list[str]) -> str:
    """Stage repo names in a file so build commands stay O(1) in the number of mutants.

    Unrolling per-repo shell into one `docker` argument overruns the kernel's 128 KiB
    MAX_ARG_STRLEN at roughly 150 mutants, which surfaces as `OSError: [Errno 7]`.
    """
    container_path = f"{ISOLATED_BUILD_ROOT}/mutant-repos.txt"
    with tempfile.TemporaryDirectory(prefix="programbench-mutant-repo-list-") as tmp_dir:
        list_path = Path(tmp_dir) / "mutant-repos.txt"
        list_path.write_text("".join(f"{name}\n" for name in repo_names))
        env.copy_in(list_path, container_path)
    return container_path


def _publish_build_report(
    env: ContainerEnvironment, report: dict[str, Any], report_dir: Path | None, attempt: int
) -> None:
    """Stage the report for the repair prompt and retain a host copy per attempt."""
    with tempfile.TemporaryDirectory(prefix="programbench-mutant-build-report-") as tmp_dir:
        report_path = Path(tmp_dir) / "mutant-build-report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        env.copy_in(report_path, "/workspace/mutant-build-report.json")
        if report_dir is not None:
            report_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(report_path, report_dir / f"mutant-build-report-{attempt}.json")


def _compile_mutant_repositories_in_live_container(
    env: ContainerEnvironment,
    *,
    instance_id: str,
    repo_names: list[str],
    build_jobs: int,
    build_cpus: int,
    timeout: int,
    attempt: int,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    """Compile generated sources in the live container and retain a repair report."""
    build_script = f"{ISOLATED_BUILD_ROOT}/build_mutant_repos_parallel.sh"
    quoted_build_root = shlex.quote(_MUTANT_BUILD_ROOT)
    env.copy_in(_MUTANT_PARALLEL_BUILD_SCRIPT, build_script)
    env.copy_in(_MUTANT_PARALLEL_BUILD_SCRIPT.with_name("build-apt-cache.py"), f"{ISOLATED_BUILD_ROOT}/build-apt-cache.py")
    repo_list = shlex.quote(_copy_repo_list_into_container(env, repo_names))
    log_path = f"/workspace/mutant-build-attempt-{attempt}.log"
    # Preserve builds between repairs. Hash the original sources separately,
    # because build.sh can modify staged sources and create additional outputs.
    stage_loop = (
        f"while IFS= read -r repo <&9; do "
        f'source=/workspace/"$repo"; staged={quoted_build_root}/"$repo"; '
        f'source_hash={quoted_build_root}/."$repo".source-hash; '
        'inputs=$(cd "$source" && { '
        "find . -type f ! -path ./executable ! -path ./.programbench-build-cache -print0 "
        "| sort -z | xargs -0 -r sha256sum; "
        "find . ! -path ./executable ! -path ./.programbench-build-cache "
        "-printf '%p %y %m %l\\0' | sort -z; "
        '} | sha256sum); '
        'if [ ! -d "$staged" ] || [ "$inputs" != "$(cat "$source_hash" 2>/dev/null)" ]; then '
        'rm -rf "$staged"; cp -a "$source" "$staged"; '
        'rm -f "$staged"/executable "$staged"/.programbench-build-cache; '
        'printf \'%s\\n\' "$inputs" > "$source_hash"; fi; '
        f"done 9< {repo_list}"
    )
    copy_back_loop = (
        "while IFS= read -r repo <&9; do "
        f'cp -f {quoted_build_root}/"$repo"/executable /workspace/"$repo"/executable; '
        f"done 9< {repo_list}"
    )
    build = env.execute(
        "set -e -o pipefail; "
        + (f"rm -rf {quoted_build_root}; " if attempt == 0 else "")
        + f"mkdir -p {quoted_build_root}; "
        + stage_loop
        + f"; chmod +x {shlex.quote(build_script)}; ("
        + f"{shlex.quote(build_script)} --jobs {build_jobs} --cpus {build_cpus} {quoted_build_root}"
        + (f" && {copy_back_loop}" if repo_names else "")
        + f") 2>&1 | tee {shlex.quote(log_path)}",
        timeout=timeout,
        output_callback=_mutant_build_output_callback(instance_id),
    )
    log_result = env.execute(f"cat {shlex.quote(log_path)}")
    log_text = log_result.get("stdout") or log_result.get("output", "")
    failed_from_log = sorted(
        set(re.findall(r"^\[([^]\n]+)\] build failed", log_text, flags=re.MULTILINE))
    )
    missing = failed_from_log or (list(repo_names) if build.get("returncode") != 0 else [])
    report = {
        "attempt": attempt,
        "returncode": build.get("returncode"),
        "exception_info": build.get("exception_info", ""),
        "log_path": log_path,
        "failed_repositories": missing,
        "log": log_text,
    }
    _publish_build_report(env, report, report_dir, attempt)
    return report


def _repair_mutant_builds(
    env: ContainerEnvironment,
    *,
    instance_id: str,
    repo_names: list[str],
    build_jobs: int,
    build_cpus: int,
    max_repairs: int,
    timeout: int,
    codex_command: str,
    model: str,
    reasoning_effort: str,
    json_events: list[dict[str, Any]],
    events: list[dict[str, Any]],
    compile_attempt: Callable[[int], dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str, dict[str, Any] | None]:
    session_id = _codex_thread_id(json_events)
    reports: list[dict[str, Any]] = []
    for attempt in range(max_repairs + 1):
        if compile_attempt is not None:
            report = compile_attempt(attempt)
        else:
            report = _compile_mutant_repositories_in_live_container(
                env, instance_id=instance_id, repo_names=repo_names,
                build_jobs=build_jobs, build_cpus=build_cpus, timeout=timeout, attempt=attempt,
            )
        reports.append(report)
        if report["returncode"] == 0:
            return reports, session_id, None
        if attempt == max_repairs or not session_id:
            return reports, session_id, {
                "status": "build_failed",
                "reason": (
                    "Mutant compilation still failed after the repair budget"
                    if session_id
                    else "Mutant compilation failed and Codex did not report a resumable thread ID"
                ),
                "output": report["log"],
            }
        resume_command = _mutant_codex_resume_shell_command(
            codex_command,
            session_id=session_id,
            prompt=MUTANT_BUILD_REPAIR_PROMPT,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        with _collect_codex_json_events(instance_id) as repair_output:
            repair = env.execute(
                resume_command, timeout=timeout, output_callback=repair_output["callback"]
            )
        events.extend(repair_output["completed_events"])
        json_events.extend(repair_output["json_events"])
        if repair.get("returncode") != 0:
            return reports, session_id, {
                "status": "codex_failed",
                "reason": "Codex build-repair turn failed",
                "returncode": repair.get("returncode"),
                "exception_info": repair.get("exception_info", ""),
                "output": repair.get("output", ""),
            }
    raise AssertionError("unreachable")


def _rebuild_mutant_repositories_in_container(
    *,
    instance_id: str,
    target_root: Path,
    repo_names: list[str],
    image: str,
    docker_executable: str,
    docker_cpus: int,
    build_jobs: int,
    timeout: int,
    run_args: list[str] | None,
) -> None:
    """Rebuild generated mutant executables in the eval-compatible task image."""
    if not repo_names:
        return
    if build_jobs < 1:
        raise ValueError(f"build_jobs must be positive, got {build_jobs}")

    image = resolve_build_image(image, docker_executable=docker_executable)
    cache_args, cache_env = build_cache_args(instance_id, BUILD_CACHE_ROOT)
    effective_run_args = [*DOCKER_RUN_ARGS, *cache_args, *(run_args or [])]
    env = ContainerEnvironment(
        image=image,
        cwd="/workspace",
        executable=docker_executable,
        timeout=timeout,
        cpus=docker_cpus,
        env=cache_env,
        run_args=effective_run_args,
    )
    try:
        for repo_name in repo_names:
            repo_path = target_root / repo_name
            if not repo_path.is_dir():
                raise RuntimeError(f"generated mutant repository is missing: {repo_path}")

        # The build root is a bind mount shared with the reference build, so it
        # keeps whatever the previous stage left behind.
        reset = env.execute(
            f"{CLEAR_BUILD_ROOT_SHELL} && mkdir -p {shlex.quote(_MUTANT_BUILD_ROOT)}"
        )
        if reset["returncode"] != 0:
            raise RuntimeError("failed to reset mutant rebuild workspace: " + reset["output"].strip())

        build_script = f"{ISOLATED_BUILD_ROOT}/build_mutant_repos_parallel.sh"
        env.copy_in(_MUTANT_PARALLEL_BUILD_SCRIPT, build_script)
        env.copy_in(_MUTANT_PARALLEL_BUILD_SCRIPT.with_name("build-apt-cache.py"), f"{ISOLATED_BUILD_ROOT}/build-apt-cache.py")
        with _progress_phase(instance_id, "stage mutant sources"):
            if hasattr(env, "copy_in_many"):
                env.copy_in_many(target_root, repo_names, _MUTANT_BUILD_ROOT)
            else:
                for repo_name in repo_names:
                    env.copy_in(target_root / repo_name, f"{_MUTANT_BUILD_ROOT}/{repo_name}")

        clean_staged = env.execute(
            "while IFS= read -r repo <&9; do "
            f'rm -f {shlex.quote(_MUTANT_BUILD_ROOT)}/"$repo"/executable '
            f'{shlex.quote(_MUTANT_BUILD_ROOT)}/"$repo"/.programbench-build-cache; '
            f"done 9< {shlex.quote(_copy_repo_list_into_container(env, repo_names))}"
        )
        if clean_staged["returncode"] != 0:
            raise RuntimeError(
                "failed to remove precompiled mutant artifacts: "
                + clean_staged["output"].strip()
            )

        build = env.execute(
            f"chmod +x {shlex.quote(build_script)}; "
            f"{shlex.quote(build_script)} --jobs {build_jobs} --cpus {docker_cpus} "
            f"{shlex.quote(_MUTANT_BUILD_ROOT)}",
            timeout=timeout,
            output_callback=_mutant_build_output_callback(instance_id),
        )
        if build["returncode"] != 0:
            # Nothing compiling at all is a property of the shared source or the
            # build environment, never of an individual mutation. Say so, rather
            # than handing a repair agent N copies of the same failure.
            compiled = [int(count) for count in re.findall(r"compiled=(\d+)", build["output"])]
            if compiled and max(compiled) == 0:
                raise RuntimeError(
                    f"every mutant repository failed to build in {image}: the mutated source or "
                    "the build environment is broken, not individual mutations: "
                    + build["output"].strip()
                )
            raise RuntimeError(
                f"failed to rebuild mutant repositories with {build_jobs} parallel job(s) in {image}: "
                + build["output"].strip()
            )

        for repo_name in repo_names:
            repo_path = target_root / repo_name
            container_repo = f"{_MUTANT_BUILD_ROOT}/{repo_name}"
            env.copy_out_file(f"{container_repo}/executable", repo_path / "executable")

        _ensure_mutant_executables_are_readable(target_root, repo_names)
    finally:
        env.execute(CLEAR_BUILD_ROOT_SHELL)
        env.cleanup()


def build_mutant_executables(
    *,
    instance: dict[str, Any],
    output: Path,
    cleanroom_base_image: str = "",
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    mutant_build_jobs: int = 1,
    timeout: int = 7200,
    run_args: list[str] | None = None,
) -> dict[str, Any]:
    """Compile the sources of a mutant store whose executables never landed.

    Generation writes the plan and manifest before the executables exist, so a
    crash in between leaves a store that resumes as complete while every mutant
    evaluates as missing_mutant_payload. Building is a pure function of the
    repo_N sources and the eval-compatible image, so this recovers such a store
    without rerunning the generation agent.
    """

    instance_id = instance["instance_id"]
    target_root = output / instance_id
    state = mutant_store_state(target_root)
    if state != "unbuilt":
        return {"instance_id": instance_id, "status": "skipped", "reason": state, "output": str(target_root)}

    repo_names = sorted(
        {str(mutant["id"]) for mutant in json.loads((target_root / MUTANT_MANIFEST_FILENAME).read_text())["mutants"]},
        key=_mutant_repo_sort_key,
    )
    log.info(
        "%s: compiling %d unbuilt mutant executable(s) with %d parallel build job(s) and %d CPU(s)",
        instance_id,
        len(repo_names),
        mutant_build_jobs,
        docker_cpus,
    )
    _rebuild_mutant_repositories_in_container(
        instance_id=instance_id,
        target_root=target_root,
        repo_names=repo_names,
        image=_cleanroom_base_image(instance, cleanroom_base_image),
        docker_executable=docker_executable,
        docker_cpus=docker_cpus,
        build_jobs=mutant_build_jobs,
        timeout=timeout,
        run_args=run_args,
    )
    invalid_mutants = _validate_mutant_repositories(target_root, repo_names, require_executable=True)
    if invalid_mutants:
        _log_invalid_mutants(instance_id, invalid_mutants)
        return {
            "instance_id": instance_id,
            "status": "invalid_mutants",
            "reason": "Compiled mutant repositories violate the build/executable policy",
            "output": str(target_root),
            "invalid_mutants": invalid_mutants,
        }

    compact_status = compact_mutant_suite(target_root)
    return {
        "instance_id": instance_id,
        "status": "ok",
        "output": str(target_root),
        "mutant_repositories": repo_names,
        "compact_storage": {**compact_status, **deduplicate_mutant_files(target_root)},
    }


def generate_mutants_instance(
    *,
    instance: dict[str, Any],
    repo_dir: Path,
    spec_in: Path,
    test_spec_links: Path,
    output: Path,
    force: bool = False,
    image: str = "",
    cleanroom_base_image: str = "",
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    mutant_build_jobs: int = 1,
    max_build_repair_attempts: int = 3,
    target_tests_per_spec: int = 6,
    final_mutants_per_spec: int = 2,
    codex_command: str = DEFAULT_CODEX_COMMAND,
    model: str = "",
    reasoning_effort: str = "",
    timeout: int = 14400,
    codex_auth_file: Path | None = None,
    forward_env: list[str] | None = None,
    run_args: list[str] | None = None,
    codex_log_dir: str | Path = DEFAULT_MUTANT_CODEX_LOG_DIR,
    progress_log_interval: int = 60,
    ground_truth_implementation_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate mutant repositories for one instance and return a status record."""
    instance_id = instance["instance_id"]
    target_root = output / instance_id
    traj_path = Path(codex_log_dir) / f"{instance_id}.mutants.traj.json"
    previous_manifest = target_root / MUTANT_MANIFEST_FILENAME
    previous_manifest_in = previous_manifest if previous_manifest.is_file() else None
    if target_root.exists() and not force:
        return {
            "instance_id": instance_id,
            "status": "skipped",
            "reason": "output_exists",
            "output": str(target_root),
            "traj": str(traj_path) if traj_path.is_file() else None,
        }

    source_spec = _instance_source(spec_in, instance_id, label="spec_in")
    source_repo_dir = _instance_source(repo_dir, instance_id, label="repo_dir")
    source_branch = select_build_branch(instance_id, source_repo_dir)
    source_links = _test_spec_links_path(test_spec_links, instance_id)
    generated_files = (
        load_generated_files(ground_truth_implementation_dir / instance_id)
        if ground_truth_implementation_dir is not None else []
    )
    mutant_plan = load_and_build_mutant_plan(
        source_links,
        instance_id=instance_id,
        target_tests_per_spec=target_tests_per_spec,
        final_mutants_per_spec=final_mutants_per_spec,
    )
    prompt = mutant_generation_prompt()
    command = _mutant_codex_shell_command(
        codex_command,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    env_config = {
        "CODEX_HOME": "/root/.codex",
        "NPM_CONFIG_UPDATE_NOTIFIER": "false",
        "NO_UPDATE_NOTIFIER": "1",
        "PROGRAMBENCH_MUTANT_BUILD_JOBS": str(mutant_build_jobs),
        **_forwarded_env(forward_env or []),
    }

    rebuild_image = _cleanroom_base_image(instance, cleanroom_base_image)
    selected_image = image or rebuild_image
    # Repair feedback and retained binaries come from one fresh eval-compatible
    # build, keeping agent-installed state out of the evaluated executables.
    rebuild_needed = True

    def save_trajectory(status: dict[str, Any], events: list[dict[str, Any]]) -> None:
        _write_codex_trajectory(
            path=traj_path,
            instance_id=instance_id,
            prompt=prompt,
            events=events,
            status=status,
            info={
                "task": "generate-mutants",
                "image": selected_image,
                "rebuild_image": rebuild_image,
                "rebuild_skipped": not rebuild_needed,
                "target_tests_per_spec": target_tests_per_spec,
                "final_mutants_per_spec": final_mutants_per_spec,
                "rebuild_cpus": docker_cpus,
                "mutant_build_jobs": mutant_build_jobs,
                "max_build_repair_attempts": max_build_repair_attempts,
                "model": model,
                "codex_command": codex_command,
                "codex_shell_command": command,
                "repo_dir": str(source_repo_dir),
                "branch": source_branch.name,
                "spec_in": str(source_spec),
                "test_spec_links": str(source_links),
                "mutant_plan_complete": mutant_plan["complete"],
                "unmatched_spec_slots": mutant_plan["unmatched_spec_slots"],
                "output_dir": str(target_root),
                "previous_mutants_manifest": str(previous_manifest_in) if previous_manifest_in is not None else None,
                "mutant_repositories": status.get("mutant_repositories"),
            },
        )

    log.info("%s: generating mutants from branch %s using image %s", instance_id, source_branch.name, selected_image)
    with _progress_phase(instance_id, "start container", interval=progress_log_interval):
        env = ContainerEnvironment(
            image=selected_image,
            cwd="/workspace",
            executable=docker_executable,
            timeout=timeout,
            cpus=docker_cpus,
            env=env_config,
            run_args=run_args,
        )
    try:
        if codex_auth_file is not None:
            with _progress_phase(instance_id, "install Codex account auth", interval=progress_log_interval):
                _copy_codex_auth_to_container(env, codex_auth_file)

        with _progress_phase(instance_id, "prepare workspace", interval=progress_log_interval):
            _prepare_mutant_workspace(
                env,
                specification=source_spec,
                branch=source_branch,
                generated_files=generated_files,
                reference_tests=source_repo_dir,
                mutant_plan=mutant_plan,
                previous_manifest=previous_manifest_in,
            )
        with _progress_phase(instance_id, "run Codex", interval=progress_log_interval):
            with _collect_codex_json_events(instance_id) as codex_output:
                result = env.execute(command, timeout=timeout, output_callback=codex_output["callback"])
        raw_stdout = result.get("stdout") or "".join(codex_output["stdout_lines"])
        raw_stderr = result.get("stderr") or "".join(codex_output["stderr_lines"])
        result = {
            **result,
            "stdout": raw_stdout,
            "stderr": raw_stderr,
            "output": result.get("output") or raw_stdout + raw_stderr,
        }
        events = list(codex_output["completed_events"])
        json_events = list(codex_output["json_events"])
        status = {
            "instance_id": instance_id,
            "status": "ok" if result.get("returncode") == 0 else "codex_failed",
            "returncode": result.get("returncode"),
            "exception_info": result.get("exception_info", ""),
            "image": selected_image,
            "rebuild_image": rebuild_image,
            "rebuild_skipped": not rebuild_needed,
            "branch": source_branch.name,
            "codex_command": codex_command,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "codex_json_events": json_events,
        }
        if result.get("returncode") != 0:
            status["output"] = result.get("output", "")
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status

        repo_names_live = _container_repo_names(env)
        if not repo_names_live:
            status.update(
                status="no_mutants",
                reason="Codex exited successfully but did not create repo_1, repo_2, ... directories",
                output=result.get("output", ""),
            )
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status
        def compile_trusted(attempt: int) -> dict[str, Any]:
            # Build feedback comes from the same fresh, eval-compatible image
            # that produces retained binaries. Do not compile every mutant twice.
            with _progress_phase(instance_id, "copy mutant repositories", interval=progress_log_interval):
                copied = _copy_mutant_repositories_from_container(
                    env, target_root=target_root, force=force or attempt > 0,
                    include_executables=False,
                )
            _restore_generated_files(
                target_root, copied, branch=source_branch, generated_files=generated_files,
            )
            _ensure_mutant_executables_are_readable(target_root, copied)
            expected = sorted(str(item["mutant_id"]) for item in mutant_plan["assignments"])
            failures = _validate_mutant_repositories(target_root, copied, require_executable=False)
            report = {
                "attempt": attempt, "returncode": 0, "exception_info": "", "log": "",
                "log_path": f"/workspace/mutant-build-attempt-{attempt}.log",
                "failed_repositories": [],
            }
            try:
                if copied != expected or failures:
                    raise RuntimeError(f"Invalid generated source repositories: {failures or copied}")
                _rebuild_mutant_repositories_in_container(
                    instance_id=instance_id, target_root=target_root, repo_names=copied,
                    image=rebuild_image, docker_executable=docker_executable,
                    docker_cpus=docker_cpus, build_jobs=mutant_build_jobs,
                    timeout=timeout, run_args=run_args,
                )
            except RuntimeError as exc:
                report.update(returncode=1, log=str(exc), failed_repositories=copied)
            else:
                # Ask the agent to fix no-op mutations while repairs remain, but never
                # fail the task over them: the compilation itself succeeded, and
                # candidate selection drops mutants that no test can kill anyway.
                no_op = _no_op_build_repositories(target_root, copied)
                if no_op and attempt < max_build_repair_attempts:
                    report.update(
                        returncode=1,
                        failed_repositories=sorted(no_op),
                        log=(
                            "These repositories compiled, but their executables are "
                            "byte-identical to another mutant's, so the mutation changed "
                            "nothing the build reads. Diff each one against the others to "
                            "find the edit, then mutate the source the build actually "
                            "compiles: the file may be regenerated by build.sh, excluded "
                            "from the build, or behind a disabled #if/#[cfg] branch. A "
                            "changed comment is never a mutation. Affected: "
                            + ", ".join(sorted(no_op))
                        ),
                    )
            with tempfile.TemporaryDirectory() as tmp:
                log_path = Path(tmp) / "build.log"
                log_path.write_text(report["log"])
                env.copy_in(log_path, report["log_path"])
            _publish_build_report(env, report, target_root, attempt)
            return report

        build_attempts, session_id, build_failure = _repair_mutant_builds(
            env,
            instance_id=instance_id,
            repo_names=repo_names_live,
            build_jobs=mutant_build_jobs,
            build_cpus=docker_cpus,
            max_repairs=max_build_repair_attempts,
            timeout=timeout,
            codex_command=codex_command,
            model=model,
            reasoning_effort=reasoning_effort,
            json_events=json_events,
            events=events,
            compile_attempt=compile_trusted,
        )
        remaining_no_op = _no_op_build_repositories(target_root, repo_names_live)
        if remaining_no_op:
            log.warning(
                "%s: %d mutant(s) still build byte-identical executables after the repair "
                "budget; leaving them for candidate selection to drop: %s",
                instance_id, len(remaining_no_op), ", ".join(sorted(remaining_no_op)),
            )
        status["build_attempts"] = build_attempts
        status["codex_session_id"] = session_id or None
        status["codex_json_events"] = json_events
        if build_failure is not None:
            status.update(build_failure, mutant_repositories=repo_names_live)
            if not target_root.exists():
                _copy_mutant_repositories_from_container(
                    env, target_root=target_root, force=force, include_executables=False
                )
            status["generated_sources"] = str(target_root)
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status

        repo_names = repo_names_live
        _ensure_mutant_executables_are_readable(target_root, repo_names)
        if not repo_names:
            status.update(
                status="no_mutants",
                reason="Codex exited successfully but did not create repo_1, repo_2, ... directories",
                output=result.get("output", ""),
            )
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status

        plan_path = target_root / MUTANT_PLAN_FILENAME
        plan_path.write_text(json.dumps(mutant_plan, indent=2, sort_keys=True) + "\n")
        planned_repo_names = sorted(str(item["mutant_id"]) for item in mutant_plan["assignments"])
        if repo_names != planned_repo_names:
            status.update(
                status="invalid_mutant_plan",
                reason="Generated mutant repositories do not exactly match mutant_plan.json",
                output=str(target_root),
                mutant_repositories=repo_names,
                planned_mutant_repositories=planned_repo_names,
                mutant_plan=str(plan_path),
            )
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status

        manifest_data = _read_container_mutant_manifest(env)
        manifest_path = _write_mutant_manifest(
            target_root=target_root,
            instance_id=instance_id,
            repo_names=repo_names,
            data=manifest_data,
            plan=mutant_plan,
        )

        invalid_mutants = _validate_mutant_repositories(
            target_root,
            repo_names,
            require_executable=not rebuild_needed,
        )
        if invalid_mutants:
            _log_invalid_mutants(instance_id, invalid_mutants)
            status.update(
                status="invalid_mutants",
                reason="Generated mutant repositories violate the build/executable policy",
                output=str(target_root),
                mutant_repositories=repo_names,
                invalid_mutants=invalid_mutants,
                mutants_manifest=str(manifest_path),
            )
            save_trajectory(status, events)
            status["traj"] = str(traj_path)
            return status

        if rebuild_needed:
            manifest_path = _write_mutant_manifest(
                target_root=target_root,
                instance_id=instance_id,
                repo_names=repo_names,
                data=manifest_data,
                plan=mutant_plan,
            )
            invalid_mutants = _validate_mutant_repositories(
                target_root,
                repo_names,
                require_executable=True,
            )
            if invalid_mutants:
                _log_invalid_mutants(instance_id, invalid_mutants)
                status.update(
                    status="invalid_mutants",
                    reason="Rebuilt mutant repositories violate the build/executable policy",
                    output=str(target_root),
                    mutant_repositories=repo_names,
                    invalid_mutants=invalid_mutants,
                    mutants_manifest=str(manifest_path),
                )
                save_trajectory(status, events)
                status["traj"] = str(traj_path)
                return status

        compact_status = compact_mutant_suite(target_root)
        dedupe_status = deduplicate_mutant_files(target_root)
        status["compact_storage"] = {**compact_status, **dedupe_status}

        status["output"] = str(target_root)
        status["mutant_repositories"] = repo_names
        status["mutants_manifest"] = str(manifest_path)
        status["mutant_plan"] = str(plan_path)
        status["unmatched_spec_slots"] = mutant_plan["unmatched_spec_slots"]
        save_trajectory(status, events)
        status["traj"] = str(traj_path)
        log.info("%s: generated %d mutant repository(s)", instance_id, len(repo_names))
        return status
    finally:
        env.cleanup()


def run_mutant_generation_batch(
    *,
    repo_dir: str | Path = "extracted-tests",
    spec_in: str | Path = "cleanroom/semiformal",
    test_spec_links: str | Path = "",
    output: str | Path = "output/mutants",
    filter_spec: str = "",
    slice_spec: str = "",
    workers: int = 1,
    force: bool = False,
    image: str = "",
    cleanroom_base_image: str = "",
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    mutant_build_jobs: int = 1,
    max_build_repair_attempts: int = 3,
    target_tests_per_spec: int = 6,
    final_mutants_per_spec: int = 2,
    codex_command: str = DEFAULT_CODEX_COMMAND,
    model: str = "",
    reasoning_effort: str = "",
    timeout: int = 14400,
    codex_auth_file: str | Path = DEFAULT_CODEX_AUTH_FILE,
    codex_log_dir: str | Path = DEFAULT_MUTANT_CODEX_LOG_DIR,
    forward_env: list[str] | None = None,
    run_args: list[str] | None = None,
    progress_log_interval: int = 60,
    ground_truth_implementation_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Generate mutant repositories for selected instances with Codex in Docker."""
    if mutant_build_jobs < 1:
        raise ValueError(f"mutant_build_jobs must be positive, got {mutant_build_jobs}")
    if max_build_repair_attempts < 0:
        raise ValueError(f"max_build_repair_attempts must be non-negative, got {max_build_repair_attempts}")
    if target_tests_per_spec < 1 or final_mutants_per_spec < 1:
        raise ValueError("target_tests_per_spec and final_mutants_per_spec must be positive")
    if final_mutants_per_spec > target_tests_per_spec:
        raise ValueError(
            "final_mutants_per_spec must not exceed target_tests_per_spec"
        )
    if not test_spec_links:
        raise ValueError("test_spec_links is required for rule-based mutant planning")
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    instances = _candidate_instance_dirs(Path(repo_dir))
    instances = filter_instances(instances, filter_spec=filter_spec, slice_spec=slice_spec)
    if not instances:
        log.warning("No instances selected for mutant generation.")
        return []

    log.info("Generating mutants for %d instance(s)", len(instances))
    results: list[dict[str, Any]] = []
    with (
        logging_redirect_tqdm(),
        concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        futures = {
            executor.submit(
                generate_mutants_instance,
                instance=instance,
                repo_dir=Path(repo_dir),
                spec_in=Path(spec_in),
                test_spec_links=Path(test_spec_links),
                output=output_path,
                force=force,
                image=image,
                cleanroom_base_image=cleanroom_base_image,
                docker_executable=docker_executable,
                docker_cpus=docker_cpus,
                mutant_build_jobs=mutant_build_jobs,
                max_build_repair_attempts=max_build_repair_attempts,
                target_tests_per_spec=target_tests_per_spec,
                final_mutants_per_spec=final_mutants_per_spec,
                codex_command=codex_command,
                model=model,
                reasoning_effort=reasoning_effort,
                timeout=timeout,
                codex_auth_file=Path(codex_auth_file).expanduser() if codex_auth_file else None,
                codex_log_dir=Path(codex_log_dir),
                forward_env=forward_env,
                run_args=run_args,
                progress_log_interval=progress_log_interval,
                ground_truth_implementation_dir=ground_truth_implementation_dir,
            ): instance["instance_id"]
            for instance in instances
        }
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Generating mutants",
            ncols=100,
            leave=False,
            disable=None,
        ):
            instance_id = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                log.error("Error generating mutants for %s: %s", instance_id, e, exc_info=True)
                results.append({"instance_id": instance_id, "status": type(e).__name__, "error": str(e)})

    return sorted(results, key=lambda r: r["instance_id"])
