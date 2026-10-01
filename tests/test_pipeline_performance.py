import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from programbench.eval.test_suite_eval import BinaryTestSuiteResult, TestSuiteEvaluator
from programbench.eval.eval import TestResult

ROOT = Path(__file__).resolve().parents[1]


def test_build_apt_reuses_installed_dependencies_and_refreshes_for_new_packages(tmp_path):
    wrapper = ROOT / 'scripts/construction/build-apt-cache.py'
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    commands = tmp_path / 'commands'
    packages = tmp_path / 'installed'
    packages.write_text('')
    real = bin_dir / 'apt-get'
    real.write_text(f'''#!/bin/sh
printf '%s\\n' "$*" >> '{commands}'
if [ "$1" = install ]; then
  shift
  for arg in "$@"; do
    case "$arg" in -*) ;; *) echo "$arg" >> '{packages}';; esac
  done
fi
''')
    real.chmod(0o755)
    query = bin_dir / 'query'
    query.write_text(f'''#!/usr/bin/env python3
import sys
installed=set(open({str(packages)!r}).read().split())
requested=sys.argv[3:]
for p in requested:
 if p in installed: print(p+' install ok installed')
sys.exit(0 if all(p in installed for p in requested) else 1)
''')
    query.chmod(0o755)
    alias = tmp_path / 'apt-get'
    alias.symlink_to(wrapper)
    env = {**os.environ, 'PROGRAMBENCH_BUILD_APT_CACHE': str(tmp_path/'cache'),
           'PROGRAMBENCH_APT_LOCK_FILE': str(tmp_path/'lock'),
           'PROGRAMBENCH_APT_BIN_DIR': str(bin_dir), 'PROGRAMBENCH_DPKG_QUERY': str(query)}
    def apt(*args):
        return subprocess.run([sys.executable, str(alias), *args], env=env, check=True, capture_output=True)
    apt('update')
    apt('install', '-y', 'one')
    before = commands.read_text()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: (apt('update'), apt('install', '-y', 'one')), range(4)))
    assert commands.read_text() == before
    apt('install', '-y', 'two')
    assert commands.read_text().splitlines()[-2:] == ['update', 'install -y two']
    # Explicit reinstall/version constraints must never be treated as no-ops.
    apt('install', '--reinstall', 'one')
    assert commands.read_text().splitlines()[-1] == 'install --reinstall one'


def test_pytest_exclusions_deselect_before_fixture_execution(tmp_path):
    tests = tmp_path / 'tests'
    tests.mkdir()
    (tests/'test_example.py').write_text('''import pytest
@pytest.fixture
def dangerous():
    raise AssertionError("excluded fixture executed")
@pytest.mark.parametrize("value", [1,2])
def test_excluded(dangerous, value): pass
def test_kept(): pass
''')
    excluded = tmp_path/'excluded.json'
    excluded.write_text(json.dumps(['tests.test_example.test_excluded']))
    env = {**os.environ, 'PROGRAMBENCH_PYTEST_EXCLUSIONS': str(excluded),
           'PYTHONPATH': str(ROOT/'src/programbench/eval'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    result = subprocess.run([sys.executable, '-m', 'pytest', '-p', 'pytest_exclusions', '-q'],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '1 passed, 2 deselected' in result.stdout


def test_binary_checkpoints_validate_inputs_and_do_not_cache_infrastructure_errors(tmp_path):
    evaluator = TestSuiteEvaluator(image_name='example', test_suite_archive=tmp_path,
                                   cache_dir=tmp_path/'cache')
    evaluator._cache_prefix = 'inputs'
    binary = tmp_path/'binary'
    binary.write_text('one')
    calls=[]
    def evaluate(**kwargs):
        calls.append(kwargs)
        return BinaryTestSuiteResult(binary_id=kwargs['binary_id'], role=kwargs['role'],
                                     test_results=[TestResult(name='t',status='passed',extra={})])
    evaluator._run_binary_uncached = evaluate
    kwargs=dict(binary_id='m1',role='candidate',mutant_payload=binary)
    evaluator._run_binary(**kwargs)
    evaluator._run_binary(**kwargs)
    assert len(calls)==1
    binary.write_text('two')
    evaluator._run_binary(**kwargs)
    assert len(calls)==2
    evaluator._cache_prefix='changed-suite-or-image'
    evaluator._run_binary(**kwargs)
    assert len(calls)==3
    evaluator._cache_prefix='failed'
    def fail(**kwargs):
        calls.append(kwargs)
        return BinaryTestSuiteResult(binary_id='m1',role='candidate',error_code='timeout')
    evaluator._run_binary_uncached=fail
    evaluator._run_binary(**kwargs)
    evaluator._run_binary(**kwargs)
    assert len(calls)==5


def test_batched_copy_uses_one_transfer_and_rejects_escape(tmp_path):
    from programbench.container import ContainerEnvironment
    import pytest
    env = ContainerEnvironment.__new__(ContainerEnvironment)
    calls=[]
    def transfer(destination, *, producer):
        names=Path(producer[-1]).read_bytes().split(b'\0')[:-1]
        calls.append((destination,names))
    env._stream_tar_in=transfer
    env.copy_in_many(tmp_path,['repo_1','repo_2'],'/build')
    assert calls==[('/build',[b'repo_1',b'repo_2'])]
    with pytest.raises(ValueError):env.copy_in_many(tmp_path,['../escape'],'/build')


def test_trusted_build_callback_avoids_agent_compilation(monkeypatch):
    from programbench import mutants
    def unexpected(*args,**kwargs):raise AssertionError('compiled inside agent container')
    monkeypatch.setattr(mutants,'_compile_mutant_repositories_in_live_container',unexpected)
    attempts=[]
    def compile_attempt(attempt):
        attempts.append(attempt)
        return {'returncode':0,'log':''}
    reports,_,failure=mutants._repair_mutant_builds(
        object(),instance_id='test',repo_names=['repo_1'],build_jobs=1,build_cpus=1,
        max_repairs=1,timeout=10,codex_command='codex',model='model',reasoning_effort='low',
        json_events=[],events=[],compile_attempt=compile_attempt,
    )
    assert attempts==[0] and failure is None and len(reports)==1


def test_payloads_share_one_binary_concurrency_budget(tmp_path):
    from threading import Lock
    import time
    from programbench.mutants import MutantSpec
    lock = Lock()
    active = 0
    peak = 0

    class Evaluator(TestSuiteEvaluator):
        def execute_binary(self, binary_id, role):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return BinaryTestSuiteResult(binary_id=binary_id, role=role,
                test_results=[TestResult(name='t', status='passed', extra={})])

        def _run_ground_truth(self):
            return self.execute_binary('ground_truth', 'ground_truth')

        def _run_mutant(self, mutant):
            return self.execute_binary(mutant.id, 'candidate')

    with ThreadPoolExecutor(max_workers=3) as binaries, ThreadPoolExecutor(max_workers=3) as branches:
        evaluators = [Evaluator(image_name='example', test_suite_archive=tmp_path,
                     branch_workers=3, execution_pool=binaries,
                     mutants=[MutantSpec(id=f'm{i}', payload='binary') for i in range(4)])
                     for _ in range(3)]
        results = list(branches.map(lambda evaluator: evaluator.run(), evaluators))
    assert peak == 3
    assert all(len(result.binary_results) == 5 for result in results)


def test_cargo_fingerprint_ignores_generated_target_but_tracks_source(tmp_path):
    repo = tmp_path/'repo_1'
    repo.mkdir()
    (repo/'Cargo.toml').write_text('[package]\nname="test"\n')
    (repo/'source').write_text('one')
    (repo/'build.sh').write_text('#!/bin/sh\nmkdir -p target\necho generated > target/object\ncp source executable\n')
    helper = ROOT/'scripts/construction/build_mutant_repos_parallel.sh'
    command = ['bash',str(helper),'--jobs','1','--cpus','1',str(tmp_path)]
    subprocess.run(command,check=True,capture_output=True)
    (repo/'target/object').write_text('changed-generated-artifact')
    reused = subprocess.run(command,check=True,capture_output=True,text=True)
    assert 'outcome=reused' in reused.stdout
    (repo/'source').write_text('two')
    changed = subprocess.run(command,check=True,capture_output=True,text=True)
    assert 'outcome=compiled' in changed.stdout
    assert (repo/'executable').read_text() == 'two'


def test_invalid_reference_preflight_does_not_schedule_mutants(tmp_path, monkeypatch):
    import pytest
    from programbench import mutant_kill_validation as validation
    from programbench.eval.test_suite_eval import TestSuiteEvaluationResult
    scheduled = []
    def evaluate(**kwargs):
        scheduled.append(kwargs.get('mutant_ids'))
        return TestSuiteEvaluationResult(binary_results=[BinaryTestSuiteResult(
            binary_id='ground_truth',role='ground_truth',test_results=[
                TestResult(name='branch/test_bad',status='failure',extra={})])])
    monkeypatch.setattr(validation,'_default_evaluator',evaluate)
    with pytest.raises(RuntimeError,match='skipped-test list'):
        validation._decide_candidate_selection(
            task='example',tests_root=tmp_path,mutants_root=tmp_path,work_dir=tmp_path,
            skipped_tests=None,workers=1,branch_workers=4,cpu_budget=4,
            raw_candidates=[],plan={},ground_truth_dir=None,evaluator=None)
    assert scheduled == [set()]


def test_validation_checkpoints_survive_forced_work_directory_cleanup(tmp_path, monkeypatch):
    import shutil
    from programbench import mutant_kill_validation as validation
    from programbench.eval.test_suite_eval import TestSuiteEvaluationResult
    work = tmp_path / 'work' / 'example'
    tests = tmp_path / 'tests'
    tests.mkdir()
    seen = []

    def evaluate(**kwargs):
        cache = Path(kwargs['evaluation_cache_dir'])
        cache.mkdir(parents=True, exist_ok=True)
        (cache / 'checkpoint').write_text('completed')
        seen.append(cache)
        result = Path(kwargs['output']) / tests.name / 'example' / 'example.test_eval.json'
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_text(TestSuiteEvaluationResult(binary_results=[]).model_dump_json())

    monkeypatch.setattr(validation, 'run_test_suite_eval_batch', evaluate)
    validation._default_evaluator(task='example', attempt=-1, tests_root=tests,
        mutants_root=tmp_path, work_dir=work, workers=1, branch_workers=1)
    shutil.rmtree(work)
    assert (seen[0] / 'checkpoint').read_text() == 'completed'
