# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""A run must not delete the task images a concurrent run is still using.

Image tags are per task (`programbench/<task>:task_patched`) and therefore shared
by every run on the host, but cleanup is decided per run. One finishing run used
to delete another's images mid-evaluation, which surfaced only much later as
`manifest unknown` on every container start.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

CLEANUP = Path(__file__).resolve().parents[1] / "scripts" / "docker" / "cleanup_programbench_docker.sh"
TASK = "facebook__zstd.1168da0"
IMAGE = "programbench/facebook_1776_zstd.1168da0:task_patched"

STUB = """#!/bin/bash
case "$1" in
  info|ps|buildx) exit 0 ;;
  image)
    case "$2" in
      inspect) exit 0 ;;
      rm) printf '%s\\n' "$3" >>"$FAKE_REMOVED" ;;
    esac ;;
esac
exit 0
"""


def process_start(pid: int) -> str:
    """Field 22 of /proc/pid/stat, read exactly the way the script reads it."""
    return subprocess.run(
        ["awk", "{print $22}", f"/proc/{pid}/stat"], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def cleanup(tmp_path):
    stub = tmp_path / "fakedocker"
    stub.write_text(STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    removed = tmp_path / "removed.txt"
    removed.touch()

    def run(*args: str) -> list[str]:
        subprocess.run(
            ["bash", str(CLEANUP), *args],
            check=True,
            capture_output=True,
            env={**os.environ, "PROGRAMBENCH_DOCKER_EXECUTABLE": str(stub), "FAKE_REMOVED": str(removed)},
        )
        return removed.read_text().split()

    return run


def lease(root: Path, task: str, name: str, pid: int, start: str) -> Path:
    (root / task).mkdir(parents=True, exist_ok=True)
    owner = root / task / f"{name}.owner"
    owner.write_text(f"{pid} {start}\n")
    return owner


def test_live_lease_holder_keeps_the_images_and_its_own_lease(cleanup, tmp_path):
    root = tmp_path / "leases"
    owner = lease(root, TASK, "other-run", os.getpid(), process_start(os.getpid()))
    assert cleanup("--task", TASK, "--lease-root", str(root)) == []
    assert owner.exists()


@pytest.mark.parametrize(("name", "pid", "start"), [
    ("dead-pid", 2**22 - 1, "1"),
    ("recycled-pid", os.getpid(), "999999999"),
])
def test_abandoned_lease_is_pruned_and_the_images_reclaimed(cleanup, tmp_path, name, pid, start):
    """A recycled pid must not pass as its dead owner, so the start time is checked too."""
    root = tmp_path / "leases"
    owner = lease(root, TASK, name, pid, start)
    assert IMAGE in cleanup("--task", TASK, "--lease-root", str(root))
    assert not owner.exists()


def test_sweep_reclaims_only_the_tasks_no_live_run_holds(cleanup, tmp_path):
    root = tmp_path / "leases"
    lease(root, TASK, "crashed-run", 2**22 - 1, "1")
    lease(root, "ogham__dog.721440b", "live-run", os.getpid(), process_start(os.getpid()))
    removed = cleanup("--sweep-leases", str(root))
    assert IMAGE in removed
    assert not any("dog" in image for image in removed)
    assert not (root / TASK).exists() and (root / "ogham__dog.721440b").exists()


def test_cleanup_without_a_lease_root_still_removes_images(cleanup):
    """Standalone invocations and older callers pass no lease root at all."""
    assert IMAGE in cleanup("--task", TASK)
