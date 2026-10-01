import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_DIR = Path("src/programbench/eval").resolve()

# os.forkpty is what pexpect.spawn uses, so this reproduces an interactive-mode test whose
# child never exits without depending on pexpect being installed.
PTY_HANG = """
import os

def test_pty_child_that_never_exits():
    pid, _ = os.forkpty()
    if pid == 0:
        while True:
            os.read(0, 1)
    os.waitpid(pid, 0)
"""

POPEN_HANG = """
import subprocess

def test_popen_child_that_never_exits():
    subprocess.Popen(["sleep", "3600"]).wait()
"""


@pytest.mark.parametrize(
    ("source", "name"),
    [(PTY_HANG, "test_pty_child_that_never_exits"), (POPEN_HANG, "test_popen_child_that_never_exits")],
)
def test_a_child_outliving_the_timeout_is_killed_so_the_session_finishes(tmp_path: Path, source: str, name: str) -> None:
    (tmp_path / f"{name}.py").write_text(source)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "pytest_watchdog", "-p", "no:cacheprovider", "-q"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(PLUGIN_DIR), "PROGRAMBENCH_SUBPROCESS_TIMEOUT": "2"},
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert "1 passed" in result.stdout, result.stdout + result.stderr


def test_descendants_are_left_alone_outside_a_test(tmp_path: Path) -> None:
    """The xdist controller holds its workers as children and never enters a test."""
    sys.path.insert(0, str(PLUGIN_DIR))
    import pytest_watchdog

    child = subprocess.Popen(["sleep", "30"])
    try:
        assert pytest_watchdog._expired_descendants(pytest_watchdog.time.monotonic() + 10_000) == []
        assert child.poll() is None
    finally:
        child.kill()
        child.wait()
