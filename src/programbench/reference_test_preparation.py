# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Prepare a fail-closed skipped-test list before iterative improvement starts."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from programbench.constants import (
    BUILD_CACHE_ROOT,
    DOCKER_CPUS,
    DOCKER_EXECUTABLE,
    DOCKER_RUN_ARGS,
    GROUND_TRUTH_LIB_DIR,
    ISOLATED_BUILD_ROOT,
    REFERENCE_BUILD_DIR,
    SOURCE_COPY_EXCLUDES,
    TASKS_DIR,
    WORKSPACE_DIR,
    image_name_from_instance_id,
)
from programbench.container import ContainerEnvironment
from programbench.eval.eval import EvaluationResult
from programbench.eval.eval_batch import run_eval_batch
from programbench.skipped_tests import (
    add_skipped_tests,
    initialize_skipped_tests,
    load_skipped_tests,
    skipped_tests_path,
)
from programbench.source_build import (
    NORMALIZE_BUILD_ENV_SHELL,
    CLEAR_BUILD_ROOT_SHELL,
    build_cache_args,
    ordered_build_branches,
    resolve_build_image,
)
from programbench.utils.ground_truth_store import write_ground_truth_submission_archive

log = logging.getLogger(__name__)

Evaluator = Callable[[Path, Path], EvaluationResult]

# Known contract-correct build branches are tried first. Other non-empty
# branches remain fallbacks, so this is not a closed task allowlist.
_PRECOMPILED_NAMES = {"executable", "executable_cov", "executable_nocov"}

_MIN_GROUND_TRUTH_VALIDITY_RATE = 0.9
DEFAULT_TRIALS = 3

# The submission archive ships `executable` plus any `lib/` sibling we vendor
# here, but evaluation only round-trips the bare executable file across
# per-branch workspace wipes (Evaluator._stashed_executable in eval.py): a
# `lib/` sibling in WORKSPACE_DIR would be destroyed by the first wipe, so
# $ORIGIN-relative to wherever the executable currently sits can't work. The
# executable's RPATH instead points at GROUND_TRUTH_LIB_DIR, a fixed path
# outside WORKSPACE_DIR that the generated compile.sh populates once and that
# survives every later wipe, same as the stashed executable itself.
#
# A binary can depend on a library that currently resolves fine in the build
# container — via an apt package build.sh installed, or via an RPATH the
# build itself set to its own transient build directory (e.g. a CMake
# project's libfoo.so) — but that resolution doesn't survive: apt packages
# aren't part of the base image, and the transient build directory doesn't
# exist once only `executable` ships. Checking `ldd` for "not found" right
# after the build is blind to both, because the build container still has
# whatever provided the resolution. So unconditionally vendor every
# non-libc/gcc runtime dependency `ldd` reports — wherever it currently
# resolves from, "not found" or not. A dependency this can't locate at all
# (nothing under the build tree, no resolved path from ldd) still fails the
# branch, same as before.
# Staged under a reserved name, never ./lib: a repository can already own a
# directory called lib (statix vendors its own `lib` crate there), and merging
# vendored .so files into it ships the crate's sources to evaluation, where
# compile.sh's `cp ./lib/*` then fails on the subdirectory.
_VENDORED_LIB_DIR = ".programbench-vendored-lib"
_BUNDLE_MISSING_LIBRARIES_SHELL = f"""
mkdir -p ./{_VENDORED_LIB_DIR}
missing_any=0
while read -r name arrow path _rest; do
  case "$name" in /*) continue ;; esac
  echo "$name" | grep -qE '^(linux-vdso\\.so|libc\\.so|libm\\.so|libpthread\\.so|libdl\\.so|librt\\.so|libgcc_s\\.so|libstdc\\+\\+\\.so)' && continue
  [ "$arrow" != "=>" ] && continue
  if [ "$path" = "not" ]; then
    real=$(find {ISOLATED_BUILD_ROOT} -name "$name" -print -quit)
  else
    real="$path"
  fi
  if [ -z "$real" ] || [ ! -f "$real" ]; then
    echo "cannot locate $name"
    missing_any=1
    continue
  fi
  cp -L "$real" "./{_VENDORED_LIB_DIR}/$name" || missing_any=1
done <<EOF
$(ldd ./executable 2>/dev/null)
EOF
[ "$missing_any" -eq 1 ] && exit 1
[ -z "$(ls -A ./{_VENDORED_LIB_DIR} 2>/dev/null)" ] && exit 0
command -v patchelf >/dev/null 2>&1 || {{ apt-get update -qq >/dev/null 2>&1; apt-get install -y -qq patchelf >/dev/null 2>&1; }} || exit 1
rpath=$(patchelf --print-rpath ./executable 2>/dev/null)
patchelf --set-rpath "{GROUND_TRUTH_LIB_DIR}:\\$ORIGIN/lib${{rpath:+:$rpath}}" ./executable || exit 1
# RUNPATH (patchelf's default) doesn't apply to a library's own transitive
# dependencies, only to the object that directly carries it. A vendored
# libfoo.so that itself links libbar.so needs its own $ORIGIN too, so it finds
# libbar.so as a sibling wherever this whole staging directory ends up (either
# GROUND_TRUTH_LIB_DIR at evaluation, or the retained ./lib sibling when
# inspected directly, e.g. by _verify_executable_is_self_contained).
for vendored in ./{_VENDORED_LIB_DIR}/*; do
  patchelf --set-rpath '$ORIGIN' "$vendored" 2>/dev/null || true
done
ldd ./executable | grep -q 'not found' && exit 1 || exit 0
""".strip()


def _stage_build_source(branch: Path, target: Path) -> None:
    shutil.copytree(
        branch,
        target,
        symlinks=True,
        ignore=lambda _directory, names: [name for name in names if name in SOURCE_COPY_EXCLUDES],
    )
    for name in _PRECOMPILED_NAMES:
        artifact = target / name
        if artifact.is_file() or artifact.is_symlink():
            artifact.unlink()


def _verify_executable_is_self_contained(
    *,
    image: str,
    executable: Path,
    lib_dir: Path,
    docker_executable: str,
    docker_cpus: int,
    timeout: int,
) -> dict[str, Any]:
    """Re-check the extracted executable from a pristine container instance.

    The build container has had build.sh's own apt-get installs and ldconfig
    refreshes applied, so a library that only resolves because of those (or a
    vendored library missing its own $ORIGIN rpath for its transitive deps)
    can look fine there and still be missing wherever evaluation actually
    runs. Only a container that never ran build.sh tells the truth. Vendored
    libraries land at GROUND_TRUTH_LIB_DIR, matching where the generated
    compile.sh places them at evaluation time (see _BUNDLE_MISSING_LIBRARIES_SHELL).
    """
    env = ContainerEnvironment(
        image=image,
        cwd="/workspace",
        executable=docker_executable,
        timeout=timeout,
        cpus=docker_cpus,
        run_args=DOCKER_RUN_ARGS,
    )
    try:
        env.copy_in(executable, f"{ISOLATED_BUILD_ROOT}/executable")
        if lib_dir.is_dir():
            env.copy_in(lib_dir, GROUND_TRUTH_LIB_DIR)
        return env.execute(
            f"chmod +x {ISOLATED_BUILD_ROOT}/executable && "
            f"ldd {ISOLATED_BUILD_ROOT}/executable | grep -q 'not found' && exit 1 || exit 0",
            timeout=timeout,
        )
    finally:
        env.cleanup()


def _build_ground_truth(
    *,
    task: str,
    task_tests: Path,
    executable: Path,
    implementation: Path,
    image: str,
    work_dir: Path,
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    timeout: int = 1800,
) -> dict[str, Any]:
    """Retain and compile the first usable reference source branch."""
    branches = ordered_build_branches(task, task_tests)
    if not branches:
        raise RuntimeError(f"No non-empty reference build scripts found for {task}: {task_tests}")

    attempts: list[dict[str, Any]] = []
    for branch in branches:
        env: ContainerEnvironment | None = None
        try:
            if implementation.exists():
                shutil.rmtree(implementation)
            _stage_build_source(branch, implementation)
            cache_args, cache_env = build_cache_args(task, BUILD_CACHE_ROOT)
            resolved_image = resolve_build_image(image, docker_executable=docker_executable)
            env = ContainerEnvironment(
                image=resolved_image,
                cwd="/workspace",
                executable=docker_executable,
                timeout=timeout,
                cpus=docker_cpus,
                env=cache_env,
                run_args=[*DOCKER_RUN_ARGS, *cache_args],
            )
            env.execute(CLEAR_BUILD_ROOT_SHELL, timeout=timeout)
            env.copy_in(implementation, REFERENCE_BUILD_DIR)
            # Reference build.sh scripts predate the isolated build root and hardcode
            # WORKSPACE_DIR as the source tree's absolute location. Alias it to the
            # isolated root rather than building there directly, so this stays on the
            # same build root as mutants without reference builds silently operating
            # on an empty WORKSPACE_DIR.
            result = env.execute(
                f"rm -rf {WORKSPACE_DIR} && ln -s {REFERENCE_BUILD_DIR} {WORKSPACE_DIR} && "
                f"cd {REFERENCE_BUILD_DIR} && " + NORMALIZE_BUILD_ENV_SHELL +
                "chmod +x ./build.sh && ./build.sh && test -f ./executable",
                timeout=timeout,
            )
            if result.get("returncode") == 0:
                bundle = env.execute(
                    f"cd {REFERENCE_BUILD_DIR} && {_BUNDLE_MISSING_LIBRARIES_SHELL}",
                    timeout=timeout,
                )
                result = {
                    "returncode": bundle.get("returncode"),
                    "output": (result.get("output") or "") + (bundle.get("output") or ""),
                }
            attempts.append({
                "branch": branch.name,
                "returncode": result.get("returncode"),
                "output": (result.get("output") or "")[-20000:],
            })
            if result.get("returncode") != 0:
                continue
            env.copy_out_file(f"{REFERENCE_BUILD_DIR}/executable", executable)
            executable.chmod(executable.stat().st_mode | 0o111)
            lib_dir = executable.parent / "lib"
            env.copy_out_dir(f"{REFERENCE_BUILD_DIR}/{_VENDORED_LIB_DIR}", lib_dir)
            if not any(lib_dir.iterdir()):
                shutil.rmtree(lib_dir)
            verify = _verify_executable_is_self_contained(
                image=resolved_image,
                executable=executable,
                lib_dir=lib_dir,
                docker_executable=docker_executable,
                docker_cpus=docker_cpus,
                timeout=timeout,
            )
            attempts[-1]["verify_returncode"] = verify.get("returncode")
            attempts[-1]["verify_output"] = (verify.get("output") or "")[-2000:]
            if verify.get("returncode") != 0:
                executable.unlink(missing_ok=True)
                shutil.rmtree(lib_dir, ignore_errors=True)
                continue
            return {
                "image": image,
                "branch": branch.name,
                "executable": str(executable),
                "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "attempts": attempts,
            }
        except (OSError, RuntimeError) as error:
            attempts.append({"branch": branch.name, "error": str(error)})
        finally:
            if env is not None:
                env.execute(CLEAR_BUILD_ROOT_SHELL, timeout=timeout)
                env.cleanup()

    attempted = ", ".join(item["branch"] for item in attempts)
    build_attempts_path = work_dir / "build_attempts.json"
    build_attempts_path.write_text(json.dumps(attempts, indent=2))
    raise RuntimeError(
        f"No reference branch produced a root-level executable for {task}; attempted: {attempted}; "
        f"see {build_attempts_path} for per-branch build output"
    )


def _prepare_reusable_ground_truth(
    *,
    task: str,
    source_root: Path,
    destination: Path,
    build_image: str,
    work_dir: Path,
    supplied_executable: Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    """Save a source-built reference binary and reuse the extracted tests."""
    executable_root = destination / "executable"
    executable = executable_root / task / "executable"
    implementation = destination / "implementation" / task
    if executable.parent.exists():
        shutil.rmtree(executable.parent)
    if implementation.exists():
        shutil.rmtree(implementation)
    executable.parent.mkdir(parents=True)
    if supplied_executable is not None:
        _stage_build_source(source_root / task, implementation)
        shutil.copy2(supplied_executable, executable)
        executable.chmod(executable.stat().st_mode | 0o111)
        build = {
            "image": None,
            "branch": None,
            "executable": str(executable),
            "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "attempts": [],
            "test_fixture_fallback": True,
        }
    else:
        build = _build_ground_truth(
            task=task,
            task_tests=source_root / task,
            executable=executable,
            implementation=implementation,
            image=build_image,
            work_dir=work_dir,
        )
    return executable_root, source_root, build

def _clean_test_name(name: str) -> str:
    clean = re.split(r"\[| \(", name, maxsplit=1)[0]
    return clean.partition("@")[0]

def _default_evaluator(*, task: str, tests_root: Path, ground_truth_dir: Path, work_dir: Path, skipped_tests: Path | None = None, branch_workers: int = 1, cpu_budget: int = 0) -> EvaluationResult:
    submission_root = work_dir / "ground-truth-submission"
    instance_dir = submission_root / task
    instance_dir.mkdir(parents=True, exist_ok=True)
    write_ground_truth_submission_archive(ground_truth_dir / task / "executable", instance_dir / "submission.tar.gz")
    run_eval_batch(
        sources=[submission_root],
        force=True,
        filter_spec=f"^{re.escape(task)}$",
        workers=1,
        branch_workers=branch_workers,
        cpu_budget=cpu_budget,
        tests_dir=tests_root,
        skipped_tests=skipped_tests or "",
        check_junit_completeness=True,
        # This archive contains the reference executable itself. Candidate
        # cleanup hashes would otherwise delete it before compile.sh runs.
        apply_eval_clean_hashes=False,
    )
    eval_json = instance_dir / f"{task}.eval.json"
    if not eval_json.is_file():
        raise RuntimeError(f"Ground-truth evaluation did not produce {eval_json}")
    return EvaluationResult.model_validate_json(eval_json.read_text())

def prepare_reference_tests(
    *,
    task: str,
    source_root: Path,
    output_root: Path,
    ground_truth_dir: Path,
    ground_truth_root: Path | None = None,
    build_image: str = "",
    tasks_dir: Path = TASKS_DIR,
    work_dir: Path,
    branch_workers: int = 1,
    cpu_budget: int = 0,
    trials: int = DEFAULT_TRIALS,
    force: bool = False,
    evaluator: Evaluator | None = None,
) -> dict[str, Any]:
    """Build and verify the run-scoped skip list without modifying test sources.

    Every attempt runs the suite ``trials`` times: a reference test that fails in any
    trial is nondeterministic (fixed fixture ports, timing) and is skip-listed, so it
    can never reach the candidate or the failure classifier as a behavioral failure.
    """
    task_tests = source_root / task
    if not task_tests.is_dir():
        raise FileNotFoundError(f"Reference test task does not exist: {task_tests}")
    provided_ground_truth_executable = ground_truth_dir / task / "executable"
    if work_dir.exists() and force:
        shutil.rmtree(work_dir)
    elif work_dir.exists() and any(work_dir.iterdir()):
        raise FileExistsError(f"Reference-test work directory exists: {work_dir} (use --force)")
    work_dir.mkdir(parents=True, exist_ok=True)

    reusable_root = ground_truth_root or Path("ground_truth")
    # Evaluator injection is used by unit tests and external callers that own
    # evaluation. Preserve that seam without requiring Docker; production
    # always compiles from a reference branch.
    supplied_executable = provided_ground_truth_executable if evaluator is not None else None
    if supplied_executable is not None and not supplied_executable.is_file():
        raise FileNotFoundError(f"Ground-truth executable does not exist: {supplied_executable}")
    executable_root, reference_tests_root, build = _prepare_reusable_ground_truth(
        task=task,
        source_root=source_root,
        destination=reusable_root,
        build_image=build_image or f"{image_name_from_instance_id(task)}:task_cleanroom_codex",
        work_dir=work_dir,
        supplied_executable=supplied_executable,
    )
    ground_truth_executable = executable_root / task / "executable"

    initialize_skipped_tests(task=task, output=output_root, tasks_dir=tasks_dir, force=force)
    skip_path = skipped_tests_path(output_root, task)
    initial_skipped = load_skipped_tests(skip_path, task=task)
    attempts: list[dict[str, Any]] = []
    added_tests: list[str] = []
    report_path = work_dir / "reference_test_preparation.json"

    def evaluate() -> EvaluationResult:
        if evaluator is not None:
            return evaluator(source_root, work_dir)
        return _default_evaluator(
            task=task,
            tests_root=reference_tests_root,
            ground_truth_dir=executable_root,
            work_dir=work_dir,
            skipped_tests=skip_path,
            branch_workers=branch_workers,
            cpu_budget=cpu_budget,
        )

    def persist(*, verified: bool, error: str | None = None) -> dict[str, Any]:
        final_skipped = load_skipped_tests(skip_path, task=task)
        payload: dict[str, Any] = {
            "task": task,
            "tests": str(task_tests),
            "ground_truth_executable": str(ground_truth_executable),
            "reference_tests": str(reference_tests_root / task),
            "ground_truth_root": str(reusable_root),
            "implementation": str(reusable_root / "implementation" / task),
            "build": build,
            "skipped_tests": str(skip_path),
            "initial_skipped_tests": sorted(initial_skipped),
            "added_skipped_tests": sorted(set(added_tests)),
            "final_skipped_tests": sorted(final_skipped),
            "attempts": attempts,
            "final_pass_rate": 1.0 if verified else 0.0,
            "verified": verified,
        }
        if error is not None:
            payload["error"] = error
        report_path.write_text(json.dumps(payload, indent=2) + "\n")
        return {**payload, "report": str(report_path)}

    attempt = 0
    while True:
        skipped_now = load_skipped_tests(skip_path, task=task)
        actives = [evaluate().without_ignored(skipped_now) for _ in range(trials)]
        active = actives[0]
        eval_path = work_dir / f"ground_truth.attempt_{attempt}.eval.json"
        eval_path.write_text(active.model_dump_json(indent=2))
        failures = sorted({
            f"{test.branch}/{_clean_test_name(test.name)}"
            for trial in actives
            for test in trial.test_results
            if test.status != "passed"
        })
        attempts.append({
            "attempt": attempt,
            "eval_json": str(eval_path),
            "total": len(active),
            "passed": sum(test.status == "passed" for test in active.test_results),
            "validity_rate": active.score,
            "trials": trials,
            "failed_tests": failures,
            "error_code": active.error_code,
            "test_branch_errors": {
                branch: [error.model_dump() for error in errors]
                for branch, errors in active.test_branch_errors.items()
            },
        })
        if active.error_code or active.test_branch_errors:
            error = "Reference evaluation has a branch or system error that cannot be represented as skipped tests"
            persist(verified=False, error=error)
            raise RuntimeError(f"{error}; see {report_path}")
        # A collapsed run reports its unreached tests as not_run rather than as
        # failures, so skip-listing them would retire tests that never ran.
        infrastructure = sorted({
            f"{test.branch}/{test.name}"
            for test in active.test_results
            if test.status in ("system_error", "not_run") or test.name == "pytest.internal"
        })
        if infrastructure:
            error = (
                f"{len(infrastructure)} reference result(s) describe the test runner, not a test "
                f"(first: {infrastructure[0]}); these cannot be resolved by skip-listing failures"
            )
            persist(verified=False, error=error)
            raise RuntimeError(f"{error}; see {report_path}")
        if not failures:
            if not len(active):
                error = "Reference evaluation has no active test functions after applying the skip list"
                persist(verified=False, error=error)
                raise RuntimeError(f"{error}; see {report_path}")
            return persist(verified=True)
        if active.score < _MIN_GROUND_TRUTH_VALIDITY_RATE:
            error = (
                f"ground-truth validity rate {active.score:.1%} is below "
                f"{_MIN_GROUND_TRUTH_VALIDITY_RATE:.0%} ({len(active) - active.n_resolved}/{len(active)} "
                "active tests failed in one attempt); this looks like a broken ground-truth "
                "build, not flaky tests, so it cannot be resolved by skip-listing individual failures"
            )
            persist(verified=False, error=error)
            raise RuntimeError(f"{error}; see {report_path}")
        newly_added = add_skipped_tests(skip_path, task=task, names=set(failures))
        attempts[-1]["added_skipped_tests"] = newly_added
        added_tests.extend(newly_added)
        if not newly_added:
            error = "Reference failures could not be added to the skipped-test list"
            persist(verified=False, error=error)
            raise RuntimeError(f"{error}; see {report_path}")
        attempt += 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a run-scoped skipped-test list and verify the active tests against ground truth."
    )
    parser.add_argument("--task", required=True)
    parser.add_argument("--source-tests", type=Path, default=Path("extracted-tests"))
    parser.add_argument("--output-skipped-tests", type=Path, required=True)
    parser.add_argument("--ground-truth-dir", type=Path, default=Path("cleanroom/original"))
    parser.add_argument("--ground-truth-root", type=Path)
    parser.add_argument("--build-image", default="")
    parser.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--branch-workers", type=int, default=1)
    parser.add_argument("--cpu-budget", type=int, default=0)
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS, help="Reference runs per attempt; a test failing in any run is skipped")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    report = prepare_reference_tests(
        task=args.task,
        source_root=args.source_tests,
        output_root=args.output_skipped_tests,
        ground_truth_dir=args.ground_truth_dir,
        ground_truth_root=args.ground_truth_root,
        build_image=args.build_image,
        tasks_dir=args.tasks_dir,
        work_dir=args.work_dir,
        branch_workers=args.branch_workers,
        cpu_budget=args.cpu_budget,
        trials=args.trials,
        force=args.force,
    )
    print(f"Skipped tests: {report['skipped_tests']}")
    print(f"Newly skipped: {len(report['added_skipped_tests'])}")
    print(f"Verified pass rate: {report['final_pass_rate'] * 100:.0f}%")
    print(f"Report: {report['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
