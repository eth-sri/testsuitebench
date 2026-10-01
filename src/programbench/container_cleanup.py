"""Bounded Docker cleanup, shared with the bare-Python agent launchers."""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import time

log = logging.getLogger(__name__)
RUN_LABEL = 'programbench.run'


def container_labels() -> list[str]:
    args = ['--label', 'programbench.managed=true']
    if run_id := os.environ.get('PROGRAMBENCH_RUN_ID'):
        args += ['--label', f'{RUN_LABEL}={run_id}']
    return args


def remove_container(executable: str, container: str, *, attempts: int = 3, timeout: int = 30) -> bool:
    """Remove only the named container; treat an already removed one as success."""
    for attempt in range(attempts):
        try:
            result = subprocess.run(
                [executable, 'rm', '-f', container], capture_output=True, text=True, timeout=timeout,
            )
            error = (result.stderr or '').strip()
            if result.returncode == 0 or 'no such container:' in error.lower():
                return True
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = str(exc)
        log.warning('Container cleanup failed for %s (attempt %d/%d): %s',
                    container, attempt + 1, attempts, error)
        if attempt + 1 < attempts:
            time.sleep(1)
    log.error('Container %s remains; retry with %s rm -f %s', container, executable, container)
    return False


def install_shutdown_handlers() -> None:
    """Turn termination into stack unwinding so launchers execute their finally."""
    def terminate(signum, frame):
        # A second TERM must not interrupt cleanup already in progress.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
