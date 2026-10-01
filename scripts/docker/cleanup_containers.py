#!/usr/bin/env python3
"""Remove one batch's containers, or stopped ProgramBench leftovers."""
from __future__ import annotations

import argparse
import ctypes
import errno
import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src/programbench'))
from container_cleanup import RUN_LABEL, remove_container


_SYS_PIDFD_SEND_SIGNAL = 424
_SYS_PIDFD_OPEN = 434


def _raise_errno() -> None:
    err = ctypes.get_errno()
    if err == errno.ESRCH:
        raise ProcessLookupError(err, os.strerror(err))
    raise OSError(err, os.strerror(err))


def _pidfd_open(pid: int) -> int:
    """os.pidfd_open, via the raw syscall for Python builds compiled without it."""
    if hasattr(os, 'pidfd_open'):
        return os.pidfd_open(pid)
    fd = ctypes.CDLL(None, use_errno=True).syscall(_SYS_PIDFD_OPEN, pid, 0)
    if fd < 0:
        _raise_errno()
    return fd


def _pidfd_send_signal(fd: int, sig: int) -> None:
    if hasattr(signal, 'pidfd_send_signal'):
        signal.pidfd_send_signal(fd, sig)
    elif ctypes.CDLL(None, use_errno=True).syscall(_SYS_PIDFD_SEND_SIGNAL, fd, sig, None, 0) < 0:
        _raise_errno()


def terminate_descendants(parent: int) -> None:
    """Stop a batch's host workers before sweeping its labeled containers."""
    children: dict[int, list[int]] = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            status = (entry / 'status').read_text()
            ppid = int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
            children.setdefault(ppid, []).append(int(entry.name))
        except (OSError, StopIteration, ValueError):
            continue
    pending = list(children.get(parent, []))
    handles = []
    try:
        while pending:
            pid = pending.pop()
            pending.extend(children.get(pid, []))
            try:
                handles.append(_pidfd_open(pid))
            except ProcessLookupError:
                continue
        for fd in handles:
            try:
                _pidfd_send_signal(fd, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if handles:
            time.sleep(3)
        for fd in handles:
            try:
                _pidfd_send_signal(fd, signal.SIGKILL)
            except ProcessLookupError:
                pass
    finally:
        for fd in handles:
            os.close(fd)


def cleanup(executable: str, *, run_id: str = '', stopped: bool = False) -> bool:
    if not run_id and not stopped:
        raise ValueError('A run ID or stopped-only scope is required')
    cmd = [executable, 'ps', '-a', '--format', '{{json .}}']
    if run_id:
        cmd += ['--filter', f'label={RUN_LABEL}={run_id}']
    else:
        cmd += ['--filter', 'status=exited', '--filter', 'status=created', '--filter', 'status=dead']
    # A final sweep catches a docker run request that was in flight on shutdown.
    for sweep in range(4):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise RuntimeError(result.stderr.strip())
            rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
            logging.error('Cannot list containers for cleanup: %s', exc)
            if sweep < 3:
                time.sleep(1)
                continue
            return False
        targets = [row for row in rows if run_id or row.get('Names', '').startswith('programbench-')]
        if not targets and sweep > 0:
            return True
        if sweep == 3:
            break
        # Do not short-circuit: attempt every container even if one removal fails.
        for row in targets:
            if stopped:
                # No force: if a stopped container restarts after listing, preserve it.
                try:
                    result = subprocess.run([executable, 'rm', row['ID']], capture_output=True, text=True, timeout=30)
                    if result.returncode and 'no such container:' not in result.stderr.lower():
                        logging.warning('Could not remove %s: %s', row['ID'], result.stderr.strip())
                except (OSError, subprocess.TimeoutExpired) as exc:
                    logging.warning('Could not remove %s: %s', row['ID'], exc)
            else:
                remove_container(executable, row['ID'])
        time.sleep(1)
    logging.error('Container cleanup did not converge; rerun scripts/docker/cleanup_containers.py')
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument('--run-id')
    scope.add_argument('--stopped', action='store_true')
    parser.add_argument('--parent-pid', type=int)
    args = parser.parse_args()
    if args.parent_pid:
        if args.parent_pid != os.getppid() or not args.run_id:
            parser.error('--parent-pid must be the calling batch and requires --run-id')
        terminate_descendants(args.parent_pid)
    executable = os.environ.get('PROGRAMBENCH_DOCKER_EXECUTABLE', 'docker')
    return 0 if cleanup(executable, run_id=args.run_id or '', stopped=args.stopped) else 1


if __name__ == '__main__':
    raise SystemExit(main())
