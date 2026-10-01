"""Cleaning up after one run must not kill the live containers of another.

Evaluation and agent batches start containers without an owner label, so the orphan
sweep that every construction cleanup runs used to treat them as abandoned and
SIGKILL them mid-run (exit status 137 in the unrelated run).
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

CLEANUP = Path(__file__).resolve().parents[1] / "scripts" / "docker" / "cleanup_programbench_docker.sh"

STUB = """#!/bin/bash
# ps -aq --filter label=programbench.managed=true lists the live containers; the
# exited/dead listings are empty.
case "$1" in
  info) exit 0 ;;
  ps)
    case "$*" in
      *label=programbench.managed=true*) printf '%s\\n' unlabeled owned-alive owned-dead ;;
    esac ;;
  inspect)
    id=${@: -1}
    case "$*" in
      *owner-pid*) case "$id" in owned-alive) echo "$FAKE_ALIVE_PID" ;; owned-dead) echo 999999999 ;; esac ;;
      *owner-start*) case "$id" in owned-alive) echo "$FAKE_ALIVE_START" ;; owned-dead) echo 1 ;; esac ;;
    esac ;;
  rm) printf '%s\\n' "${@: -1}" >>"$FAKE_REMOVED" ;;
esac
exit 0
"""


def test_orphan_sweep_removes_only_containers_whose_named_owner_is_gone(tmp_path):
    stub = tmp_path / "fakedocker"
    stub.write_text(STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    removed = tmp_path / "removed.txt"
    removed.touch()
    start = subprocess.run(
        ["awk", "{print $22}", f"/proc/{os.getpid()}/stat"], capture_output=True, text=True, check=True
    ).stdout.strip()

    subprocess.run(
        ["bash", str(CLEANUP), "--task", "owner__repo.1234567"],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "PROGRAMBENCH_DOCKER_EXECUTABLE": str(stub),
            "FAKE_REMOVED": str(removed),
            "FAKE_ALIVE_PID": str(os.getpid()),
            "FAKE_ALIVE_START": start,
        },
    )

    assert removed.read_text().split() == ["owned-dead"]


def test_task_container_removal_spares_containers_of_an_evaluation_batch(tmp_path):
    safe = Path(__file__).resolve().parents[1] / "scripts" / "construction" / "run_iterative_all_safe.sh"
    function = subprocess.run(
        ["sed", "-n", "/^remove_task_containers()/,/^}/p", str(safe)], capture_output=True, text=True, check=True
    ).stdout
    assert function.startswith("remove_task_containers()")
    stub = tmp_path / "fakedocker"
    stub.write_text(
        "#!/bin/bash\n"
        'case "$1" in\n'
        '  image) ;;\n'
        '  ps) printf "%s\\n" construction-container batch-container ;;\n'
        '  inspect) case "${@: -1}" in batch-container) echo some-batch-run ;; esac ;;\n'
        '  rm) printf "%s\\n" "${@: -1}" >>"$FAKE_REMOVED" ;;\n'
        "esac\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    removed = tmp_path / "removed.txt"
    removed.touch()

    subprocess.run(
        ["bash", "-c", f'docker_bin={stub}\n{function}\nremove_task_containers owner__repo.1234567'],
        check=True,
        capture_output=True,
        env={**os.environ, "FAKE_REMOVED": str(removed)},
    )

    assert set(removed.read_text().split()) == {"construction-container"}
