"""Source-branch selection shared by reference and mutant builds.

The reference executable and the mutants it is compared against must be
compiled from the same branch. When the two paths select independently they
drift, and mutants then differ from the reference for reasons that have nothing
to do with the mutation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from programbench.constants import DOCKER_EXECUTABLE, ISOLATED_BUILD_ROOT

# Tasks whose alphabetically-first branch ships a build.sh that cannot produce
# ./executable: a missing mv, a different feature set, or a typo in the
# destination path. Both build paths must skip to the branch that works.
PREFERRED_BUILD_BRANCHES = {
    "canop__rhit.ae90bcb": "5acb4aa8bf92",
    "rbakbashev__elfcat.52f8cc7": "0b64bd84aa2b",
    "halitechallenge__halite.822cfb6": "1040f6b8a219",
    "canop__broot.d6c798e": "257e8a0c3e58",
    "ggreer__the_silver_searcher.a61f178": "1802d8be2734",
}


def ordered_build_branches(task: str, task_tests: Path) -> list[Path]:
    """Return usable source branches, preferring a known contract-correct one."""
    branches = [
        path
        for path in sorted(task_tests.iterdir())
        if path.is_dir()
        and (path / "build.sh").is_file()
        and (path / "build.sh").read_text(errors="replace").strip()
    ]
    preferred = PREFERRED_BUILD_BRANCHES.get(task)
    if preferred:
        branches.sort(key=lambda path: (path.name != preferred, path.name))
    return branches


def select_build_branch(task: str, task_tests: Path) -> Path:
    """Return the single branch that both reference and mutant builds compile."""
    branches = ordered_build_branches(task, task_tests)
    if not branches:
        raise RuntimeError(
            f"no source branch with a usable build.sh found for {task}: {task_tests}"
        )
    return branches[0]


# Container paths for the host-side caches. Only build containers get these
# mounts; the cleanroom images agents run in are untouched.
_CARGO_REGISTRY_DIR = "/usr/local/cargo/registry"
_SCCACHE_DIR = "/tmp/programbench-sccache"


# The build root is a bind mount, so the mount point itself cannot be removed —
# only its contents. Every build clears it on entry, but a task whose tree is
# left behind keeps hundreds of GB of mutant target/ dirs on the host until that
# task happens to build again, so builds clear it on the way out as well.
CLEAR_BUILD_ROOT_SHELL = (
    f"mkdir -p {ISOLATED_BUILD_ROOT} && "
    f"find {ISOLATED_BUILD_ROOT} -mindepth 1 -maxdepth 1 -exec rm -rf {{}} +"
)


def build_cache_args(task: str, cache_root: Path) -> tuple[list[str], dict[str, str]]:
    """Return docker run args and env sharing dependency caches across builds.

    Every mutant of a task resolves the same locked dependency set as the
    reference, so downloads and dependency object code are identical across
    builds and only the project's own crate changes. The caches are pure
    accelerators: with an empty or absent cache the build is exactly the one
    that runs today, just slower.
    """
    run_args: list[str] = []
    for name, container_path in (
        ("cargo-registry", _CARGO_REGISTRY_DIR),
        ("sccache", _SCCACHE_DIR),
        # Docker here uses fuse-overlayfs, where writes run ~200x slower than the
        # host filesystem. Mutant target/ trees are hundreds of MB each, so the
        # build root has to escape the container's writable layer. Reference and
        # mutant builds share this mount so both compile on the same filesystem.
        ("build-root", ISOLATED_BUILD_ROOT),
    ):
        host_path = (cache_root / task / name).resolve()
        host_path.mkdir(parents=True, exist_ok=True)
        run_args.extend(["-v", f"{host_path}:{container_path}"])
    # sccache runs a server plus a thread per concurrent compile on top of the
    # parallel cargo jobs, which exhausts the default pid limit and makes rustc
    # spawns fail with EAGAIN. Docker takes the last flag, so this raises it for
    # build containers only.
    run_args.extend(["--pids-limit", "16384"])
    return run_args, {
        "SCCACHE_DIR": _SCCACHE_DIR,
        "SCCACHE_IDLE_TIMEOUT": "0",
        "PROGRAMBENCH_USE_SCCACHE": "1",
    }


# Run from inside a build directory, immediately before build.sh. rustc is only
# wrapped when sccache is actually present, so an image without it builds
# normally instead of failing every compile with a missing wrapper.
#
# Compilers record the directory they built in (panic locations, debug info), so
# a reference and a mutant compiled in different directories differ for reasons
# that have nothing to do with the mutation. Mapping every build onto one path
# makes them byte-identical. A build.sh that sets these itself wins, which
# leaves that task exactly as it is today rather than breaking it.
NORMALIZE_BUILD_ENV_SHELL = (
    'if [ "${PROGRAMBENCH_USE_SCCACHE:-}" = 1 ] && command -v sccache >/dev/null 2>&1; then '
    "export RUSTC_WRAPPER=sccache; fi; "
    'export RUSTFLAGS="--remap-path-prefix=$PWD=/build${RUSTFLAGS:+ $RUSTFLAGS}"; '
    'export GOFLAGS="-trimpath${GOFLAGS:+ $GOFLAGS}"; '
)


def resolve_build_image(cleanroom_image: str, *, docker_executable: str = DOCKER_EXECUTABLE) -> str:
    """Prefer the build-only image so task-specific deps stay out of agent images.

    Falls back to the cleanroom image when that image has not been built, so a
    task without pre-installed dependencies behaves exactly as it does today.
    """
    candidate = f"{cleanroom_image.rsplit(':', 1)[0]}:task_mutantbuild"
    inspected = subprocess.run(
        [docker_executable, "image", "inspect", candidate],
        capture_output=True,
    )
    return candidate if inspected.returncode == 0 else cleanroom_image
