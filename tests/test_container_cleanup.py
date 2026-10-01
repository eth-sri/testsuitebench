from __future__ import annotations

import importlib.util
import signal
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from programbench import container_cleanup as cleanup
from programbench.container import ContainerEnvironment


def load_script():
    path = Path(__file__).resolve().parents[1] / 'scripts/docker/cleanup_containers.py'
    spec = importlib.util.spec_from_file_location('cleanup_script', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cleanup_retries_timeout_and_error(monkeypatch):
    run = Mock(side_effect=[subprocess.TimeoutExpired('docker', 30),
                           subprocess.CompletedProcess([], 1, '', 'daemon unavailable'),
                           subprocess.CompletedProcess([], 0, '', '')])
    monkeypatch.setattr(cleanup.subprocess, 'run', run)
    monkeypatch.setattr(cleanup.time, 'sleep', lambda _: None)
    assert cleanup.remove_container('docker', 'our-container')
    assert run.call_count == 3
    assert all(call.args[0] == ['docker', 'rm', '-f', 'our-container'] for call in run.call_args_list)
    assert all(call.kwargs['timeout'] == 30 for call in run.call_args_list)


def test_already_removed_is_success(monkeypatch):
    run = Mock(return_value=subprocess.CompletedProcess([], 1, '', 'Error: No such container: gone'))
    monkeypatch.setattr(cleanup.subprocess, 'run', run)
    assert cleanup.remove_container('docker', 'gone')
    assert run.call_count == 1


def test_failed_cleanup_is_reported_and_preserves_id(monkeypatch, caplog):
    monkeypatch.setattr(cleanup.subprocess, 'run',
                        Mock(return_value=subprocess.CompletedProcess([], 1, '', 'daemon down')))
    monkeypatch.setattr(cleanup.time, 'sleep', lambda _: None)
    env = ContainerEnvironment.__new__(ContainerEnvironment)
    env.executable = 'docker'
    env.container_id = 'keep-for-retry'
    env.cleanup()
    assert env.container_id == 'keep-for-retry'
    assert 'remains; retry' in caplog.text
    monkeypatch.setattr(cleanup.subprocess, 'run',
                        Mock(return_value=subprocess.CompletedProcess([], 0, '', '')))
    env.cleanup()
    assert env.container_id == ''


def test_run_labels(monkeypatch):
    monkeypatch.setenv('PROGRAMBENCH_RUN_ID', 'batch-one')
    assert cleanup.container_labels() == ['--label', 'programbench.managed=true',
                                         '--label', 'programbench.run=batch-one']


def test_sigterm_runs_finally(tmp_path):
    marker = tmp_path / 'cleaned'
    script = f'''
import os, signal
from programbench.container_cleanup import install_shutdown_handlers
install_shutdown_handlers()
try:
    os.kill(os.getpid(), signal.SIGTERM)
finally:
    open({str(marker)!r}, 'w').write('cleanup ran')
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    assert result.returncode == 128 + signal.SIGTERM
    assert marker.read_text() == 'cleanup ran'


def test_stopped_sweep_never_forces_or_removes_proxy(monkeypatch):
    module = load_script()
    calls = []
    listings = iter(['{"ID":"old","Names":"programbench-old"}\n'
                     '{"ID":"proxy","Names":"pb-proxy"}\n', ''])

    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, next(listings) if cmd[1] == 'ps' else '', '')

    monkeypatch.setattr(module.subprocess, 'run', run)
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    assert module.cleanup('docker', stopped=True)
    assert ['docker', 'rm', 'old'] in calls
    assert not any('proxy' in command for command in calls)
    assert 'status=exited' in calls[0]


def test_batch_sweep_uses_run_label_and_checks_again(monkeypatch):
    module = load_script()
    calls = []
    listings = iter(['{"ID":"leftover","Names":"programbench-one"}\n', ''])

    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, next(listings), '')

    remove = Mock(return_value=True)
    monkeypatch.setattr(module.subprocess, 'run', run)
    monkeypatch.setattr(module, 'remove_container', remove)
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    assert module.cleanup('docker', run_id='batch-one')
    assert all('label=programbench.run=batch-one' in command for command in calls)
    remove.assert_called_once_with('docker', 'leftover')


def test_unscoped_sweep_is_rejected():
    with pytest.raises(ValueError):
        load_script().cleanup('docker')


def test_batch_sigterm_stops_workers_and_sweeps_its_containers(tmp_path):
    import json
    import os
    import shutil
    import time

    root = Path(__file__).resolve().parents[1]
    (tmp_path / 'scripts/eval').mkdir(parents=True)
    (tmp_path / 'scripts/docker').mkdir()
    (tmp_path / 'src/programbench').mkdir(parents=True)
    for source in ('scripts/eval/run_agents.sh', 'scripts/docker/cleanup_containers.py',
                   'src/programbench/container_cleanup.py'):
        shutil.copy(root / source, tmp_path / source)
    (tmp_path / 'scripts/docker/setup_egress_network.sh').write_text('exit 0\n')
    (tmp_path / 'scripts/eval/stub_eval.sh').write_text(
        '#!/bin/bash\n'
        'echo "$PROGRAMBENCH_RUN_ID" > run-id\n'
        'echo $$ > worker-pid\n'
        'sleep 300\n'
    )
    docker = tmp_path / 'docker'
    docker.write_text('''#!/usr/bin/env python3
import json, pathlib, sys
with open('docker-calls', 'a') as f: f.write(json.dumps(sys.argv[1:]) + '\\n')
state = pathlib.Path('removed')
if sys.argv[1] == 'ps' and not state.exists():
    print(json.dumps({'ID': 'batch-container', 'Names': 'programbench-test'}))
elif sys.argv[1] == 'rm':
    state.touch()
''')
    docker.chmod(0o755)
    command = ['bash', 'scripts/eval/run_agents.sh', '--runs', 'stub', '--backend', 'stub=stub',
               '--model', 'stub=model', '--reasoning', 'stub=high', '--task', 'a__b.123']
    process = subprocess.Popen(command, cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env={**os.environ, 'PROGRAMBENCH_DOCKER_EXECUTABLE': str(docker)})
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / 'worker-pid').exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert (tmp_path / 'worker-pid').exists()
        worker_pid = int((tmp_path / 'worker-pid').read_text())
        process.terminate()
        stdout, stderr = process.communicate(timeout=20)
        assert process.returncode == 143, stdout + stderr
        calls = [json.loads(line) for line in (tmp_path / 'docker-calls').read_text().splitlines()]
        run_id = (tmp_path / 'run-id').read_text().strip()
        assert all(f'label=programbench.run={run_id}' in call for call in calls if call[0] == 'ps')
        assert ['rm', '-f', 'batch-container'] in calls
        status = Path(f'/proc/{worker_pid}/status')
        assert not status.exists() or 'State:\tZ' in status.read_text()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
