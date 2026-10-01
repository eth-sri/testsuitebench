# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

"""Record which repository paths ``build.sh`` produces rather than reads.

A mutation applied to a generated path compiles cleanly and changes nothing: the
build overwrites it before the compiler ever sees the edit. That is invisible to
the mutant agent, which spends the whole slot on a behavioural no-op. Recording
the set once per task lets mutant generation withhold those paths instead.

This runs on the retained ground-truth implementation, so it is independent of
reference-test preparation and stays valid for tasks whose prepared tests are
already cached.
"""

from __future__ import annotations

import logging
from pathlib import Path

from programbench.constants import (
    DOCKER_CPUS,
    DOCKER_EXECUTABLE,
    DOCKER_RUN_ARGS,
    GENERATED_FILES_NAME,
    REFERENCE_BUILD_DIR,
    WORKSPACE_DIR,
    BUILD_CACHE_ROOT,
)
from programbench.container import ContainerEnvironment
from programbench.mutant_storage import SKIPPED_SOURCE_DIRS, SKIPPED_SOURCE_SUFFIXES
from programbench.source_build import (
    CLEAR_BUILD_ROOT_SHELL,
    NORMALIZE_BUILD_ENV_SHELL,
    build_cache_args,
    resolve_build_image,
)

log = logging.getLogger(__name__)

# Build output is already excluded from mutant repositories, so recording it would
# bury the paths that matter: broot's first run recorded 3238 target/** entries and
# one real one. Prune exactly what the mutant store refuses to track.
# -name, not -path: tracked_sources rejects these directories at any depth.
_PRUNE = " ".join(
    f"-name '{directory}' -type d -prune -o" for directory in sorted(SKIPPED_SOURCE_DIRS)
) + " " + " ".join(
    f"-name '*{suffix}' -prune -o" for suffix in sorted(SKIPPED_SOURCE_SUFFIXES)
)

# mtime, not content: a generator that rewrites a file with byte-identical bytes
# (sqlite regenerating shell.c from src/shell.c.in) still discards a mutation.
_SNAPSHOT = f"find . {_PRUNE} -type f -printf '%p\\t%s\\t%T@\\n' | sort"
RECORD_GENERATED_FILES_SHELL = (
    f"{_SNAPSHOT} > /tmp/programbench-pre && "
    "chmod +x ./build.sh && ./build.sh && test -f ./executable && "
    f"{_SNAPSHOT} > /tmp/programbench-post && "
    "comm -13 /tmp/programbench-pre /tmp/programbench-post | cut -f1 | sed 's|^\\./||' "
    f"> {GENERATED_FILES_NAME}"
)


def load_generated_files(implementation: Path) -> list[str]:
    """Return the recorded generated paths, or nothing when none were recorded."""
    manifest = implementation / GENERATED_FILES_NAME
    if not manifest.is_file():
        return []
    return [line for line in manifest.read_text().splitlines() if line.strip()]


def record_generated_files(
    *,
    task: str,
    implementation: Path,
    image: str,
    docker_executable: str = DOCKER_EXECUTABLE,
    docker_cpus: int = DOCKER_CPUS,
    timeout: int = 1800,
    force: bool = False,
) -> dict[str, object]:
    """Build the retained implementation once and record what the build produced.

    Best effort: a task whose build no longer reproduces is left without a manifest
    rather than failed, since the recording only ever withholds paths from the agent.
    """
    manifest = implementation / GENERATED_FILES_NAME
    if manifest.is_file() and not force:
        return {"task": task, "status": "cached", "generated": len(load_generated_files(implementation))}

    cache_args, cache_env = build_cache_args(task, BUILD_CACHE_ROOT)
    env = ContainerEnvironment(
        image=resolve_build_image(image, docker_executable=docker_executable),
        cwd=WORKSPACE_DIR,
        executable=docker_executable,
        timeout=timeout,
        cpus=docker_cpus,
        env=cache_env,
        run_args=[*DOCKER_RUN_ARGS, *cache_args],
    )
    try:
        env.execute(CLEAR_BUILD_ROOT_SHELL, timeout=timeout)
        env.copy_in(implementation, REFERENCE_BUILD_DIR)
        # build.sh scripts hardcode WORKSPACE_DIR, so alias it exactly as the
        # reference build does rather than building somewhere they cannot see.
        result = env.execute(
            f"rm -rf {WORKSPACE_DIR} && ln -s {REFERENCE_BUILD_DIR} {WORKSPACE_DIR} && "
            f"cd {REFERENCE_BUILD_DIR} && " + NORMALIZE_BUILD_ENV_SHELL + RECORD_GENERATED_FILES_SHELL,
            timeout=timeout,
        )
        if result.get("returncode") != 0:
            # Best effort by design. Some build.sh scripts are not hermetic
            # (`go get -u ./...` resolves to whatever upstream published today), so
            # they can fail long after the retained executable was built from them.
            # Without a manifest nothing is withheld and generation behaves as before,
            # which is strictly better than failing a task that would otherwise run.
            log.warning(
                "%s: recording generated files failed, continuing without a manifest: %s",
                task, (result.get("output") or "")[-2000:],
            )
            return {"task": task, "status": "unavailable", "generated": 0}
        env.copy_out_file(f"{REFERENCE_BUILD_DIR}/{GENERATED_FILES_NAME}", manifest)
    finally:
        env.execute(CLEAR_BUILD_ROOT_SHELL, timeout=timeout)
        env.cleanup()

    generated = load_generated_files(implementation)
    log.info("%s: recorded %d generated path(s) in %s", task, len(generated), manifest)
    return {"task": task, "status": "recorded", "generated": len(generated)}
