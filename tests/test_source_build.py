import subprocess
from pathlib import Path

import pytest

from programbench.source_build import (
    NORMALIZE_BUILD_ENV_SHELL,
    PREFERRED_BUILD_BRANCHES,
    build_cache_args,
    resolve_build_image,
    select_build_branch,
)


def _branch(task_dir, name, build_sh=None):
    branch = task_dir / name
    (branch / "src").mkdir(parents=True)
    if build_sh is not None:
        (branch / "build.sh").write_text(build_sh)
    return branch


@pytest.mark.parametrize(
    ("task", "branches", "expected"),
    [
        # Alphabetically first branch has no build.sh at all (srgn, zk).
        ("task.abc", {"0aaa": None, "2bbb": "cargo build --release\n"}, "2bbb"),
        # Present but empty build.sh is unusable too.
        ("task.abc", {"0aaa": "   \n", "2bbb": "cargo build --release\n"}, "2bbb"),
        # Both usable: the alphabetically first one wins.
        ("task.abc", {"0aaa": "make\n", "2bbb": "make\n"}, "0aaa"),
    ],
)
def test_selects_first_branch_with_a_usable_build_script(tmp_path, task, branches, expected):
    task_dir = tmp_path / task
    task_dir.mkdir()
    for name, content in branches.items():
        _branch(task_dir, name, content)

    assert select_build_branch(task, task_dir).name == expected


def test_preferred_branch_overrides_alphabetical_order(tmp_path):
    """Reference and mutant builds must both skip branches with broken build.sh."""
    task = "canop__broot.d6c798e"
    task_dir = tmp_path / task
    task_dir.mkdir()
    _branch(task_dir, "0dfff12d5006", 'cargo build --release --features "clipboard"\n')
    _branch(task_dir, PREFERRED_BUILD_BRANCHES[task], "cargo build --release\nmv target/release/broot executable\n")

    selected = select_build_branch(task, task_dir)
    assert selected.name == PREFERRED_BUILD_BRANCHES[task]
    assert "--features" not in (selected / "build.sh").read_text()


def test_raises_when_no_branch_can_build(tmp_path):
    task_dir = tmp_path / "task.abc"
    task_dir.mkdir()
    _branch(task_dir, "0aaa", None)

    with pytest.raises(RuntimeError, match="no source branch with a usable build.sh"):
        select_build_branch("task.abc", task_dir)


def test_build_caches_are_host_side_and_shared_by_both_build_paths(tmp_path):
    """Caches must live on the host so no agent-visible image gains build artifacts."""
    run_args, env = build_cache_args("org__repo.123", tmp_path)

    mounts = dict(
        run_args[index + 1].split(":", 1)
        for index, arg in enumerate(run_args)
        if arg == "-v"
    )
    assert all(Path(host).is_dir() for host in mounts)
    assert all(str(tmp_path) in host for host in mounts)
    assert env["SCCACHE_DIR"] in mounts.values()
    assert env["PROGRAMBENCH_USE_SCCACHE"] == "1"
    # sccache's extra processes exhaust the default pid limit.
    assert run_args[run_args.index("--pids-limit") + 1] == "16384"


def test_sccache_is_only_wrapped_when_the_binary_exists():
    """An image without sccache must build normally, not fail every compile."""
    assert "command -v sccache" in NORMALIZE_BUILD_ENV_SHELL
    assert "export RUSTC_WRAPPER=sccache" in NORMALIZE_BUILD_ENV_SHELL


def test_falls_back_to_the_cleanroom_image_when_no_build_image_exists():
    cleanroom = "programbench/nosuch_1776_task.abc0000:task_cleanroom_codex"

    assert resolve_build_image(cleanroom) == cleanroom


def test_build_image_name_is_derived_without_splitting_a_registry_port(monkeypatch):
    """Agent-facing cleanroom images must never be the base for build-only deps."""
    seen = {}

    def fake_run(args, **kwargs):
        seen["image"] = args[-1]
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert resolve_build_image("registry:5000/pb/task.abc:task_cleanroom_codex") == (
        "registry:5000/pb/task.abc:task_mutantbuild"
    )
    assert seen["image"].endswith(":task_mutantbuild")


def test_reference_and_mutant_builds_normalise_the_same_way():
    """Both build paths must set identical flags or their binaries diverge.

    The build directory is recorded in panic locations and debug info, so a
    reference and a mutant compiled in different directories differ for reasons
    unrelated to the mutation. The mutant path duplicates this snippet in shell,
    so the two copies have to agree.
    """
    mutant_builder = Path("scripts/construction/build_mutant_repos_parallel.sh").read_text()

    for setting in (
        'export RUSTFLAGS="--remap-path-prefix=$PWD=/build${RUSTFLAGS:+ $RUSTFLAGS}"',
        'export GOFLAGS="-trimpath${GOFLAGS:+ $GOFLAGS}"',
        "export RUSTC_WRAPPER=sccache",
    ):
        assert setting in NORMALIZE_BUILD_ENV_SHELL
        if setting.startswith('export RUSTFLAGS='):
            assert 'PROGRAMBENCH_RUST_REMAP_FLAGS:---remap-path-prefix=$PWD=/build' in mutant_builder
        else:
            assert setting in mutant_builder
