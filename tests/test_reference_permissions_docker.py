"""Real kernel permission checks; opt in with PROGRAMBENCH_PERMISSION_TEST_IMAGE.

Use an existing task-cleanroom image with Python, setpriv and a C compiler.
No model calls or network access are used.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess

import pytest

from programbench.reference_isolation import reference_guard_setup, stage_reference

IMAGE = os.environ.get('PROGRAMBENCH_PERMISSION_TEST_IMAGE')
pytestmark = pytest.mark.skipif(not IMAGE, reason='set PROGRAMBENCH_PERMISSION_TEST_IMAGE for Docker checks')

ATTACKS = r'''
import errno, os, pathlib, subprocess
p = '/workspace/executable'
assert os.getuid() == 61000
subprocess.run([p, '--version'], check=True, stdout=subprocess.DEVNULL)
for path in (p, '/tmp/programbench_reference_executable', '/tmp/programbench_cleanroom/executable'):
    if not os.path.exists(path): continue
    for action in (lambda: open(path, 'rb'), lambda: os.chmod(path, 0o755),
                   lambda: os.chown(path, os.getuid(), os.getgid())):
        try: action()
        except OSError as error:
            assert error.errno in (errno.EPERM, errno.EACCES, errno.EROFS)
        else: raise AssertionError('reference protection bypassed: ' + path)
    assert subprocess.run(['chmod', '+r', path], capture_output=True).returncode != 0
    assert subprocess.run(['cp', path, '/tmp/stolen'], capture_output=True).returncode != 0
try: os.setuid(0)
except PermissionError: pass
else: raise AssertionError('regained root')
status = pathlib.Path('/proc/self/status').read_text().splitlines()
for name in ('CapEff:', 'CapPrm:', 'CapBnd:', 'CapAmb:'):
    assert int(next(line.split()[1] for line in status if line.startswith(name)), 16) == 0
assert 'NoNewPrivs:\t1' in status
own = pathlib.Path('/workspace/agent-owned')
own.write_text('build file')
os.chmod(own, 0o111)
os.chmod(own, 0o755)
assert own.read_text() == 'build file'
'''


def runner(name):
    path = Path(__file__).resolve().parents[1] / 'scripts/agents' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def docker(script, mounts=()):
    args = ['docker', 'run', '--rm', '--pull', 'never', '--network', 'none',
            '--user', '0:0', '--entrypoint', 'bash']
    for source, dest in mounts:
        args += ['-v', f'{source}:{dest}:ro']
    result = subprocess.run([*args, IMAGE, '-c', script], text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('name', ['solve_codex', 'solve_claude', 'generate_tests_claude'])
def test_full_launcher_protects_binary_and_preserves_builds(tmp_path, name):
    prompt = tmp_path / 'prompt'
    prompt.write_text('permission test')
    cleanroom = tmp_path / 'cleanroom'
    cleanroom.mkdir()
    # Both input mounts must be protected, as well as /workspace/executable.
    stage_reference(Path('/bin/true'), cleanroom / 'executable')
    reference = stage_reference(Path('/bin/true'), tmp_path / 'reference')
    checks = tmp_path / 'checks.py'
    checks.write_text(ATTACKS)
    agent = tmp_path / 'agent'
    agent.write_text('''#!/bin/bash
set -eu
python3 /tmp/checks.py
printf 'int main(void) { return 0; }' > /workspace/main.c
cc /workspace/main.c -o /workspace/mine
/workspace/mine
mkdir -p /workspace/eval
cat > /workspace/eval/run.sh <<'SH'
#!/bin/bash
set -eu
python3 /tmp/checks.py
printf '<testsuite><testcase name="permissions"/></testsuite>' > results.xml
SH
chmod +x /workspace/eval/run.sh
''')
    agent.chmod(0o755)
    module = runner(name)
    if name == 'generate_tests_claude':
        script = module.build_container_script('/tmp/agent', '', '', with_executable=True)
    else:
        script = module.build_container_script('with-executable', '/tmp/agent', '', '')
    docker(script, [(prompt, '/tmp/programbench_prompt.txt'), (agent, '/tmp/agent'),
                    (checks, '/tmp/checks.py'), (cleanroom, '/tmp/programbench_cleanroom'),
                    (reference, '/tmp/programbench_reference_executable')] if name == 'generate_tests_claude' else
           [(prompt, '/tmp/programbench_prompt.txt'), (agent, '/tmp/agent'),
            (checks, '/tmp/checks.py'), (cleanroom, '/tmp/programbench_cleanroom')])


@pytest.mark.parametrize('dict_actions', [False, True])
def test_native_and_mini_swe_commands_are_demoted(dict_actions):
    from programbench.container import ContainerEnvironment
    from programbench.test_generation import _protect_generation_reference

    env = ContainerEnvironment(image=IMAGE, cwd='/workspace', cpus=1,
                               run_args=['--network', 'none', '--user', '0:0'])
    try:
        result = env.execute('cp /bin/true /workspace/executable')
        assert result['returncode'] == 0
        if dict_actions:
            original = env.execute
            env.execute = lambda action, **kwargs: original(action['command'], **kwargs)
        _protect_generation_reference(env, dict_actions=dict_actions)
        command = "python3 - <<'CHECK'\n" + ATTACKS + '\nCHECK'
        for _ in range(2):  # Subsequent commands cannot regain bootstrap privilege.
            result = env.execute({'command': command} if dict_actions else command)
            assert result['returncode'] == 0, result['output']
    finally:
        env.cleanup()


def test_guard_rejects_script_reference():
    # Scripts require read access by their interpreter; do not silently weaken it.
    script = "printf '#!/bin/sh\\nexit 0\\n' > /workspace/executable\n"
    script += 'if (\n' + reference_guard_setup() + '\n); then exit 1; fi'
    docker(script)
