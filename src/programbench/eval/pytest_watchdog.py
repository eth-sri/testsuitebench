"""Kill subprocesses a test leaves running past ``PROGRAMBENCH_SUBPROCESS_TIMEOUT`` seconds.

A candidate that blocks forever otherwise holds its pytest worker until the branch-level
timeout, which costs the whole budget and turns the hang into an evaluation error instead of a
failed test. The per-test timeout in run.sh does not reliably interrupt a blocked pipe read, so
this watches every ``subprocess.Popen`` started while a test is running and kills its process
tree from a separate thread, after which the blocked read returns and the test fails normally.

``pexpect.spawn`` and ``os.forkpty`` never go through ``Popen``, so children driven over a pty --
the shape an interactive-mode test takes -- are found by walking this process's own descendants
instead.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import pytest

_TIMEOUT = float(os.environ.get("PROGRAMBENCH_SUBPROCESS_TIMEOUT", "0") or 0)
_LOCK = threading.Lock()
_WATCHED: list[tuple[float, subprocess.Popen]] = []
_FIRST_SEEN: dict[int, float] = {}
_IN_TEST = False
_original_init = subprocess.Popen.__init__


def pytest_configure(config: Any) -> None:
    if _TIMEOUT <= 0:
        return
    subprocess.Popen.__init__ = _watched_init  # type: ignore[method-assign]
    threading.Thread(target=_reap, daemon=True, name="programbench-watchdog").start()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: Any, nextitem: Any):
    global _IN_TEST
    _IN_TEST = True
    yield
    _IN_TEST = False


def _watched_init(self: subprocess.Popen, *args: Any, **kwargs: Any) -> None:
    _original_init(self, *args, **kwargs)
    if _IN_TEST:
        with _LOCK:
            _WATCHED.append((time.monotonic() + _TIMEOUT, self))


def _reap() -> None:
    while True:
        time.sleep(0.5)
        now = time.monotonic()
        with _LOCK:
            live = [(deadline, proc) for deadline, proc in _WATCHED if proc.returncode is None]
            expired = [proc for deadline, proc in live if deadline <= now]
            _WATCHED[:] = [(deadline, proc) for deadline, proc in live if deadline > now]
        for proc in expired:
            kill_process_tree(proc.pid)
        for pid in _expired_descendants(now):
            kill_process_tree(pid)


def _expired_descendants(now: float) -> list[int]:
    """Descendants alive longer than the timeout, whatever spawned them.

    Only while a test runs: under xdist the controller's children are its workers, and the
    controller never enters a test, so they are never candidates for killing.
    """
    global _FIRST_SEEN
    if not _IN_TEST:
        _FIRST_SEEN = {}
        return []
    _FIRST_SEEN = {pid: _FIRST_SEEN.get(pid, now) for pid in descendants(os.getpid())}
    return [pid for pid, seen in _FIRST_SEEN.items() if now - seen >= _TIMEOUT]


def descendants(pid: int) -> list[int]:
    children: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
        except OSError:
            continue
        children.setdefault(int(stat.rpartition(")")[2].split()[1]), []).append(int(entry.name))
    found: list[int] = []
    queue = [pid]
    while queue:
        kids = children.get(queue.pop(), [])
        found.extend(kids)
        queue.extend(kids)
    return found


def kill_process_tree(pid: int) -> None:
    # Descendants first so a grandchild holding the test's pipes cannot outlive its parent.
    for target in [*descendants(pid), pid]:
        try:
            os.kill(target, signal.SIGKILL)
        except ProcessLookupError:
            pass
