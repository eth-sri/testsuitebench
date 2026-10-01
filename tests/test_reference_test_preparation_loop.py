import json
from pathlib import Path

import pytest

from programbench import reference_test_preparation, source_build
from programbench.eval import eval_batch
from programbench.eval.eval import EvaluationResult, TestResult

# The preparation loop fails closed below 90% ground-truth validity rate, so every
# fixture needs enough passing tests for a single failure to stay under 10%.
_PAD = [f"test_pad{i}" for i in range(9)]


def _layout(tmp_path: Path) -> tuple[str, Path, Path, Path]:
    task = "org__repo.123"
    source_root = tmp_path / "extracted-tests"
    source_task = source_root / task
    source_task.mkdir(parents=True)
    (source_task / "tests.py").write_text(
        "def test_ok(): pass\n\ndef test_official(): assert False\n\ndef test_bad(): assert False\n"
        + "".join(f"def {name}(): pass\n" for name in _PAD)
    )
    tasks_dir = tmp_path / "tasks"
    metadata = tasks_dir / task / "tests.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({
        "branches": {
            "branch_a": {
                "tests": ["test_ok", "test_official", "test_bad", *_PAD],
                "ignored_tests": [{"name": "test_official", "reasons": [{"id": "gold_fail"}]}],
            }
        }
    }))
    ground_truth = tmp_path / "ground-truth"
    executable = ground_truth / task / "executable"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n")
    return task, source_root, tasks_dir, ground_truth


def test_prepare_reference_tests_extends_canonical_skip_list_without_editing_sources(tmp_path: Path) -> None:
    task, source_root, tasks_dir, ground_truth = _layout(tmp_path)
    original = (source_root / task / "tests.py").read_text()
    evaluations = 0

    def evaluator(_tests_root: Path, _work_dir: Path) -> EvaluationResult:
        nonlocal evaluations
        evaluations += 1
        return EvaluationResult(
            test_results=[
                TestResult(name="test_ok", branch="branch_a", status="passed", extra={}),
                TestResult(name="test_official", branch="branch_a", status="failure", extra={}),
                TestResult(name="test_bad", branch="branch_a", status="failure", extra={}),
                *(TestResult(name=name, branch="branch_a", status="passed", extra={}) for name in _PAD),
            ],
            test_branches=["branch_a"],
        )

    output = tmp_path / "skipped-tests"
    report = reference_test_preparation.prepare_reference_tests(
        task=task,
        source_root=source_root,
        output_root=output,
        ground_truth_dir=ground_truth,
        ground_truth_root=tmp_path / "ground_truth",
        tasks_dir=tasks_dir,
        work_dir=tmp_path / "work",
        evaluator=evaluator,
        trials=1,
    )

    assert evaluations == 2
    assert report["verified"] is True
    assert report["initial_skipped_tests"] == ["branch_a/test_official"]
    assert report["added_skipped_tests"] == ["branch_a/test_bad"]
    assert report["final_skipped_tests"] == ["branch_a/test_bad", "branch_a/test_official"]
    assert Path(report["ground_truth_executable"]).is_file()
    assert Path(report["reference_tests"]) == source_root / task
    assert Path(report["implementation"]).is_dir()
    assert not (Path(report["ground_truth_root"]) / "reference-tests").exists()
    assert report["build"]["test_fixture_fallback"] is True
    assert (source_root / task / "tests.py").read_text() == original
    document = json.loads((output / f"{task}.json").read_text())
    assert [item["name"] for item in document["skipped_tests"]] == [
        "branch_a/test_bad",
        "branch_a/test_official",
    ]


def test_prepare_reference_tests_skips_flaky_failures_past_two_attempts(tmp_path: Path) -> None:
    task = "org__repo.123"
    source_root = tmp_path / "extracted-tests"
    source_task = source_root / task
    source_task.mkdir(parents=True)
    (source_task / "tests.py").write_text(
        "def test_a(): pass\n\ndef test_b(): pass\n\ndef test_c(): pass\n\ndef test_d(): pass\n"
        + "".join(f"def {name}(): pass\n" for name in _PAD)
    )
    tasks_dir = tmp_path / "tasks"
    metadata = tasks_dir / task / "tests.json"
    metadata.parent.mkdir(parents=True)
    metadata.write_text(
        json.dumps({"branches": {"branch_a": {"tests": ["test_a", "test_b", "test_c", "test_d", *_PAD]}}})
    )
    ground_truth = tmp_path / "ground-truth"
    executable = ground_truth / task / "executable"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n")

    evaluations = 0

    def evaluator(_tests_root: Path, _work_dir: Path) -> EvaluationResult:
        nonlocal evaluations
        evaluations += 1
        # A different test flakes on each of the first three attempts, then all pass.
        flaky = ["test_a", "test_b", "test_c", None][evaluations - 1]
        return EvaluationResult(
            test_results=[
                TestResult(name=name, branch="branch_a", status="failure" if name == flaky else "passed", extra={})
                for name in ("test_a", "test_b", "test_c", "test_d", *_PAD)
            ],
            test_branches=["branch_a"],
        )

    report = reference_test_preparation.prepare_reference_tests(
        task=task,
        source_root=source_root,
        output_root=tmp_path / "skipped-tests",
        ground_truth_dir=ground_truth,
        ground_truth_root=tmp_path / "ground_truth",
        tasks_dir=tasks_dir,
        work_dir=tmp_path / "work",
        evaluator=evaluator,
        trials=1,
    )

    assert evaluations == 4
    assert report["verified"] is True
    assert report["added_skipped_tests"] == ["branch_a/test_a", "branch_a/test_b", "branch_a/test_c"]


def test_prepare_reference_tests_fails_closed_when_most_active_tests_fail(tmp_path: Path) -> None:
    task, source_root, tasks_dir, ground_truth = _layout(tmp_path)

    def evaluator(_tests_root: Path, _work_dir: Path) -> EvaluationResult:
        # test_official is already canonically skipped, leaving test_ok and
        # test_bad active; both failing (100%) must not be skip-listed away.
        return EvaluationResult(
            test_results=[
                TestResult(name="test_ok", branch="branch_a", status="failure", extra={}),
                TestResult(name="test_official", branch="branch_a", status="failure", extra={}),
                TestResult(name="test_bad", branch="branch_a", status="failure", extra={}),
                *(TestResult(name=name, branch="branch_a", status="passed", extra={}) for name in _PAD),
            ],
            test_branches=["branch_a"],
        )

    with pytest.raises(RuntimeError, match="looks like a broken ground-truth build"):
        reference_test_preparation.prepare_reference_tests(
            task=task,
            source_root=source_root,
            output_root=tmp_path / "skipped-tests",
            ground_truth_dir=ground_truth,
            ground_truth_root=tmp_path / "ground_truth",
            tasks_dir=tasks_dir,
            work_dir=tmp_path / "work",
            evaluator=evaluator,
        trials=1,
        )
    document = json.loads((tmp_path / "skipped-tests" / f"{task}.json").read_text())
    assert [item["name"] for item in document["skipped_tests"]] == ["branch_a/test_official"]


def test_prepare_reference_tests_fails_closed_on_system_error(tmp_path: Path) -> None:
    task, source_root, tasks_dir, ground_truth = _layout(tmp_path)
    result = EvaluationResult(
        test_results=[TestResult(name="test_ok", branch="branch_a", status="passed", extra={})],
        test_branches=["branch_a"],
        error_code="evaluation_failed",
    )

    with pytest.raises(RuntimeError, match="branch or system error"):
        reference_test_preparation.prepare_reference_tests(
            task=task,
            source_root=source_root,
            output_root=tmp_path / "skipped-tests",
            ground_truth_dir=ground_truth,
            ground_truth_root=tmp_path / "ground_truth",
            tasks_dir=tasks_dir,
            work_dir=tmp_path / "work",
            evaluator=lambda _tests, _work: result,
        )


def test_default_evaluator_preserves_ground_truth_executable(monkeypatch, tmp_path: Path) -> None:
    task = "org__repo.123"
    ground_truth = tmp_path / "ground-truth"
    executable = ground_truth / task / "executable"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n")
    seen_kwargs = {}

    def fake_run_eval_batch(**kwargs):
        seen_kwargs.update(kwargs)
        instance_dir = Path(kwargs["sources"][0]) / task
        (instance_dir / f"{task}.eval.json").write_text(
            EvaluationResult(test_branches=["branch_a"]).model_dump_json()
        )

    monkeypatch.setattr(reference_test_preparation, "run_eval_batch", fake_run_eval_batch)
    reference_test_preparation._default_evaluator(
        task=task,
        tests_root=tmp_path / "tests",
        ground_truth_dir=ground_truth,
        work_dir=tmp_path / "work",
        skipped_tests=tmp_path / "skipped.json",
    )

    assert seen_kwargs["apply_eval_clean_hashes"] is False
    assert seen_kwargs["skipped_tests"] == tmp_path / "skipped.json"


@pytest.mark.parametrize(
    ("task", "preferred"),
    [
        ("canop__rhit.ae90bcb", "5acb4aa8bf92"),
        ("rbakbashev__elfcat.52f8cc7", "0b64bd84aa2b"),
        ("halitechallenge__halite.822cfb6", "1040f6b8a219"),
        ("canop__broot.d6c798e", "257e8a0c3e58"),
        ("ggreer__the_silver_searcher.a61f178", "1802d8be2734"),
    ],
)
def test_reference_build_prefers_contract_correct_reported_branches(
    tmp_path: Path, task: str, preferred: str,
) -> None:
    task_tests = tmp_path / task
    for branch, script in (("000broken", ""), (preferred, "cargo build\n"), ("zzz", "make\n")):
        path = task_tests / branch
        path.mkdir(parents=True)
        (path / "build.sh").write_text(script)

    branches = source_build.ordered_build_branches(task, task_tests)

    assert [branch.name for branch in branches] == [preferred, "zzz"]


def test_reference_build_falls_back_when_script_does_not_create_root_executable(
    monkeypatch, tmp_path: Path,
) -> None:
    task_tests = tmp_path / "task"
    for branch in ("a_broken", "b_good"):
        path = task_tests / branch
        path.mkdir(parents=True)
        (path / "build.sh").write_text("make\n")
    constructed = 0

    class FakeEnv:
        def __init__(self, **kwargs):
            nonlocal constructed
            assert kwargs["run_args"][:len(reference_test_preparation.DOCKER_RUN_ARGS)] == (
                reference_test_preparation.DOCKER_RUN_ARGS
            )
            if kwargs["run_args"] != reference_test_preparation.DOCKER_RUN_ARGS:
                # The reference binary must build with the same caches as the mutants.
                # The verify-stage container below intentionally omits these.
                assert any(
                    argument.endswith(":/tmp/programbench-sccache")
                    for argument in kwargs["run_args"]
                )
            self.attempt = constructed
            constructed += 1

        def copy_in(self, _source, destination):
            assert destination.startswith(reference_test_preparation.ISOLATED_BUILD_ROOT)

        def execute(self, command, timeout):
            if "-mindepth 1 -maxdepth 1" in command:  # shared build-root cleanup
                return {"returncode": 0, "output": ""}
            if "build.sh" in command:
                assert f"ln -s {reference_test_preparation.REFERENCE_BUILD_DIR} {reference_test_preparation.WORKSPACE_DIR}" in command
                assert f"cd {reference_test_preparation.REFERENCE_BUILD_DIR}" in command
                assert "test -f ./executable" in command
                return {"returncode": 1 if self.attempt == 0 else 0, "output": "build output"}
            if "missing_any" in command:
                return {"returncode": 0, "output": "no missing libraries"}
            return {"returncode": 0, "output": "verified self-contained"}

        def copy_out_file(self, source, destination):
            assert source == f"{reference_test_preparation.REFERENCE_BUILD_DIR}/executable"
            destination.write_bytes(b"ours")

        def copy_out_dir(self, _source, destination):
            destination.mkdir(parents=True, exist_ok=True)

        def cleanup(self):
            pass

    monkeypatch.setattr(reference_test_preparation, "ContainerEnvironment", FakeEnv)
    executable = tmp_path / "out" / "executable"
    executable.parent.mkdir()
    implementation = tmp_path / "implementation"

    result = reference_test_preparation._build_ground_truth(
        task="unknown__task.123",
        task_tests=task_tests,
        executable=executable,
        implementation=implementation,
        image="build-image",
        work_dir=tmp_path,
    )

    assert result["branch"] == "b_good"
    assert [attempt["returncode"] for attempt in result["attempts"]] == [1, 0]
    assert executable.read_bytes() == b"ours"
    assert (implementation / "build.sh").read_text() == "make\n"
    assert not (executable.parent / "lib").exists()


def test_reference_build_aliases_workspace_dir_to_isolated_build_root(
    monkeypatch, tmp_path: Path,
) -> None:
    task_tests = tmp_path / "task"
    (task_tests / "only_branch").mkdir(parents=True)
    (task_tests / "only_branch" / "build.sh").write_text("make\n")
    commands: list[str] = []

    class FakeEnv:
        def __init__(self, **kwargs):
            pass

        def copy_in(self, _source, destination):
            assert destination.startswith(reference_test_preparation.ISOLATED_BUILD_ROOT)

        def execute(self, command, timeout):
            commands.append(command)
            return {"returncode": 0, "output": "ok"}

        def copy_out_file(self, _source, destination):
            destination.write_bytes(b"ours")

        def copy_out_dir(self, _source, destination):
            destination.mkdir(parents=True, exist_ok=True)

        def cleanup(self):
            pass

    monkeypatch.setattr(reference_test_preparation, "ContainerEnvironment", FakeEnv)
    executable = tmp_path / "out" / "executable"
    executable.parent.mkdir()

    reference_test_preparation._build_ground_truth(
        task="unknown__task.123",
        task_tests=task_tests,
        executable=executable,
        implementation=tmp_path / "implementation",
        image="build-image",
        work_dir=tmp_path,
    )

    # The build root is a bind mount shared with the mutant builds, so the
    # reference build must clear it before staging its own source into it, and
    # again on the way out so its tree does not sit on the host until the next
    # build of this task.
    clean_command, build_command, bundle_command, verify_command, final_clean = commands
    assert clean_command == final_clean == reference_test_preparation.CLEAR_BUILD_ROOT_SHELL
    assert "-mindepth 1 -maxdepth 1 -exec rm -rf" in clean_command
    workspace = reference_test_preparation.WORKSPACE_DIR
    root = reference_test_preparation.REFERENCE_BUILD_DIR
    assert build_command.index(f"ln -s {root} {workspace}") < build_command.index(f"cd {root}")
    assert "ldd ./executable" in bundle_command
    # Verification runs in a pristine container and compiles nothing, so it
    # stays at the build root rather than the reference build directory.
    assert "ldd" in verify_command
    assert reference_test_preparation.ISOLATED_BUILD_ROOT in verify_command


def test_reference_build_vendors_missing_shared_library_and_patches_rpath(
    monkeypatch, tmp_path: Path,
) -> None:
    """A binary that dynamically links a library built alongside it (e.g. a CMake
    project's own libfoo.so) loads fine in the build container but fails every
    invocation once only `executable` is shipped to evaluation. The bundling
    step should vendor that library into ./lib and repoint RPATH at $ORIGIN."""
    task_tests = tmp_path / "task"
    (task_tests / "only_branch").mkdir(parents=True)
    (task_tests / "only_branch" / "build.sh").write_text("make\n")

    class FakeEnv:
        def __init__(self, **kwargs):
            self.calls = 0

        def copy_in(self, _source, _destination):
            pass

        def execute(self, command, timeout):
            if "-mindepth 1 -maxdepth 1" in command:  # shared build-root cleanup
                return {"returncode": 0, "output": ""}
            self.calls += 1
            if self.calls == 1:
                return {"returncode": 0, "output": "build output"}
            assert "ldd ./executable" in command
            assert "patchelf" in command
            return {"returncode": 0, "output": "vendored libfoo.so.1 and patched RPATH"}

        def copy_out_file(self, _source, destination):
            destination.write_bytes(b"ours")

        def copy_out_dir(self, _source, destination):
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "libfoo.so.1").write_bytes(b"lib")

        def cleanup(self):
            pass

    monkeypatch.setattr(reference_test_preparation, "ContainerEnvironment", FakeEnv)
    executable = tmp_path / "out" / "executable"
    executable.parent.mkdir()

    result = reference_test_preparation._build_ground_truth(
        task="unknown__task.123",
        task_tests=task_tests,
        executable=executable,
        implementation=tmp_path / "implementation",
        image="build-image",
        work_dir=tmp_path,
    )

    assert result["branch"] == "only_branch"
    assert (executable.parent / "lib" / "libfoo.so.1").read_bytes() == b"lib"


def test_reference_build_falls_back_when_verification_fails_in_pristine_container(
    monkeypatch, tmp_path: Path,
) -> None:
    """A binary can resolve every dependency inside the enriched build
    container (apt packages it just installed, or a vendored library missing
    its own $ORIGIN rpath for a transitive dependency) and still be broken
    everywhere else. The pristine-container re-check must catch that and fall
    back to the next branch instead of shipping the broken pair."""
    task_tests = tmp_path / "task"
    for branch in ("a_looks_fine_but_isnt", "b_actually_self_contained"):
        path = task_tests / branch
        path.mkdir(parents=True)
        (path / "build.sh").write_text("make\n")
    verify_calls = 0

    class FakeEnv:
        def __init__(self, **kwargs):
            pass

        def copy_in(self, _source, _destination):
            pass

        def execute(self, command, timeout):
            if "-mindepth 1 -maxdepth 1" in command:  # shared build-root cleanup
                return {"returncode": 0, "output": ""}
            nonlocal verify_calls
            if "build.sh" in command:
                return {"returncode": 0, "output": "build output"}
            if "missing_any" in command:
                return {"returncode": 0, "output": "no missing libraries"}
            verify_calls += 1
            return {"returncode": 1 if verify_calls == 1 else 0, "output": "not found in pristine container"}

        def copy_out_file(self, _source, destination):
            destination.write_bytes(b"ours")

        def copy_out_dir(self, _source, destination):
            destination.mkdir(parents=True, exist_ok=True)

        def cleanup(self):
            pass

    monkeypatch.setattr(reference_test_preparation, "ContainerEnvironment", FakeEnv)
    executable = tmp_path / "out" / "executable"
    executable.parent.mkdir()

    result = reference_test_preparation._build_ground_truth(
        task="unknown__task.123",
        task_tests=task_tests,
        executable=executable,
        implementation=tmp_path / "implementation",
        image="build-image",
        work_dir=tmp_path,
    )

    assert result["branch"] == "b_actually_self_contained"
    assert result["attempts"][0]["verify_returncode"] == 1
    assert result["attempts"][1]["verify_returncode"] == 0
    assert executable.read_bytes() == b"ours"


def test_reference_build_falls_back_when_missing_library_cannot_be_vendored(
    monkeypatch, tmp_path: Path,
) -> None:
    """A missing library that isn't found anywhere under the build tree is a
    genuine system dependency gap, not something to silently paper over."""
    task_tests = tmp_path / "task"
    for branch in ("a_missing_lib", "b_self_contained"):
        path = task_tests / branch
        path.mkdir(parents=True)
        (path / "build.sh").write_text("make\n")
    constructed = 0

    class FakeEnv:
        def __init__(self, **kwargs):
            nonlocal constructed
            self.attempt = constructed
            constructed += 1
            self.calls = 0

        def copy_in(self, _source, _destination):
            pass

        def execute(self, command, timeout):
            if "-mindepth 1 -maxdepth 1" in command:  # shared build-root cleanup
                return {"returncode": 0, "output": ""}
            self.calls += 1
            if self.calls == 1:
                return {"returncode": 0, "output": "build output"}
            if self.attempt == 0:
                return {"returncode": 1, "output": "cannot locate libfoo.so.1 under the build tree"}
            return {"returncode": 0, "output": "no missing libraries"}

        def copy_out_file(self, _source, destination):
            destination.write_bytes(b"ours")

        def copy_out_dir(self, _source, destination):
            destination.mkdir(parents=True, exist_ok=True)

        def cleanup(self):
            pass

    monkeypatch.setattr(reference_test_preparation, "ContainerEnvironment", FakeEnv)
    executable = tmp_path / "out" / "executable"
    executable.parent.mkdir()

    result = reference_test_preparation._build_ground_truth(
        task="unknown__task.123",
        task_tests=task_tests,
        executable=executable,
        implementation=tmp_path / "implementation",
        image="build-image",
        work_dir=tmp_path,
    )

    assert result["branch"] == "b_self_contained"
    assert "cannot locate" in result["attempts"][0]["output"]


def test_reference_build_persists_per_branch_output_when_all_branches_fail(
    monkeypatch, tmp_path: Path,
) -> None:
    task_tests = tmp_path / "task"
    for branch in ("a_broken", "b_broken"):
        path = task_tests / branch
        path.mkdir(parents=True)
        (path / "build.sh").write_text("make\n")

    class FakeEnv:
        def __init__(self, **kwargs):
            pass

        def copy_in(self, _source, _destination):
            pass

        def execute(self, _command, timeout):
            return {"returncode": 1, "output": "fatal error: vendor/lib.h: No such file or directory"}

        def copy_out_file(self, _source, _destination):
            raise AssertionError("must not be reached when the build fails")

        def cleanup(self):
            pass

    monkeypatch.setattr(reference_test_preparation, "ContainerEnvironment", FakeEnv)
    work_dir = tmp_path / "work"
    work_dir.mkdir()

    with pytest.raises(RuntimeError, match="build_attempts.json"):
        reference_test_preparation._build_ground_truth(
            task="unknown__task.123",
            task_tests=task_tests,
            executable=tmp_path / "out" / "executable",
            implementation=tmp_path / "implementation",
            image="build-image",
            work_dir=work_dir,
        )

    attempts = json.loads((work_dir / "build_attempts.json").read_text())
    assert [attempt["branch"] for attempt in attempts] == ["a_broken", "b_broken"]
    assert all(attempt["returncode"] == 1 for attempt in attempts)
    assert all("vendor/lib.h" in attempt["output"] for attempt in attempts)


def test_candidate_evaluation_still_applies_clean_hashes_by_default(monkeypatch, tmp_path: Path) -> None:
    task = "org__repo.123"
    instance_dir = tmp_path / "submissions" / task
    instance_dir.mkdir(parents=True)
    (instance_dir / "submission.tar.gz").write_bytes(b"submission")
    seen_kwargs = {}

    class FakeEvaluator:
        def __init__(self, **kwargs):
            seen_kwargs.update(kwargs)

        def run(self):
            return EvaluationResult(test_branches=["branch_a"])

    monkeypatch.setattr(eval_batch, "Evaluator", FakeEvaluator)
    eval_batch._evaluate_instance(
        instance_id=task,
        instance={
            "image_name": "programbench/org__repo.123",
            "eval_clean_hashes": ["reference-executable-hash"],
            "branches": {"branch_a": {"tests": []}},
        },
        source_dir=tmp_path / "submissions",
        target_dir=tmp_path / "results",
        force=True,
        tests_dir=tmp_path / "tests",
    )
    assert seen_kwargs["remove_hashes"] == ["reference-executable-hash"]


def test_evaluate_instance_materializes_submission_from_ground_truth_dir(monkeypatch, tmp_path: Path) -> None:
    task = "org__repo.123"
    ground_truth_executable = tmp_path / "ground_truth" / "executable" / task / "executable"
    ground_truth_executable.parent.mkdir(parents=True)
    ground_truth_executable.write_bytes(b"binary")
    ground_truth_executable.chmod(0o755)

    class FakeEvaluator:
        def __init__(self, **kwargs):
            self.submission_archive = kwargs["submission_archive"]

        def run(self):
            return EvaluationResult(test_branches=["branch_a"])

    monkeypatch.setattr(eval_batch, "Evaluator", FakeEvaluator)
    summary = eval_batch._evaluate_instance(
        instance_id=task,
        instance={"image_name": "programbench/org__repo.123", "branches": {"branch_a": {"tests": []}}},
        source_dir=tmp_path / "submissions",
        target_dir=tmp_path / "results",
        force=True,
        tests_dir=tmp_path / "tests",
        ground_truth_dir=tmp_path / "ground_truth" / "executable",
    )

    submission_archive = tmp_path / "submissions" / task / "submission.tar.gz"
    assert submission_archive.is_file()
    assert summary.error_code is None


def test_evaluate_instance_reports_no_submission_when_ground_truth_executable_missing(
    monkeypatch, tmp_path: Path
) -> None:
    task = "org__repo.123"

    class FakeEvaluator:
        def __init__(self, **kwargs):
            raise AssertionError("Evaluator must not run without a submission archive")

    monkeypatch.setattr(eval_batch, "Evaluator", FakeEvaluator)
    summary = eval_batch._evaluate_instance(
        instance_id=task,
        instance={"image_name": "programbench/org__repo.123", "branches": {"branch_a": {"tests": []}}},
        source_dir=tmp_path / "submissions",
        target_dir=tmp_path / "results",
        force=True,
        tests_dir=tmp_path / "tests",
        ground_truth_dir=tmp_path / "ground_truth" / "executable",
    )

    assert summary.error_code == "no_submission"
    assert not (tmp_path / "submissions" / task / "submission.tar.gz").exists()


def test_prepare_reference_tests_fails_closed_on_tests_missing_from_junit_xml(tmp_path: Path) -> None:
    task, source_root, tasks_dir, ground_truth = _layout(tmp_path)

    def evaluator(_tests_root: Path, _work_dir: Path) -> EvaluationResult:
        # A collapsed pytest run reports its unreached tests as not_run next to a
        # pytest.internal row; neither describes a test that can be skip-listed.
        return EvaluationResult(
            test_results=[
                TestResult(name="test_ok", branch="branch_a", status="passed", extra={}),
                TestResult(name="pytest.internal", branch="branch_a", status="error", extra={}),
                TestResult(name="test_bad", branch="branch_a", status="not_run", extra={}),
                *(TestResult(name=name, branch="branch_a", status="passed", extra={}) for name in _PAD),
            ],
            test_branches=["branch_a"],
        )

    with pytest.raises(RuntimeError, match="describe the test runner"):
        reference_test_preparation.prepare_reference_tests(
            task=task,
            source_root=source_root,
            output_root=tmp_path / "skipped-tests",
            ground_truth_dir=ground_truth,
            ground_truth_root=tmp_path / "ground_truth",
            tasks_dir=tasks_dir,
            work_dir=tmp_path / "work",
            evaluator=evaluator,
        trials=1,
        )
    assert json.loads((tmp_path / "work" / "reference_test_preparation.json").read_text())["verified"] is False
    assert not (tmp_path / "skipped-tests" / f"{task}.json").exists() or [
        item["name"] for item in json.loads((tmp_path / "skipped-tests" / f"{task}.json").read_text())["skipped_tests"]
    ] == ["branch_a/test_official"]


def test_a_reference_test_failing_in_any_of_three_trials_is_skipped(tmp_path: Path) -> None:
    """Fixed fixture ports and timing made reference tests fail on the candidate run only; one
    reference pass could not see that. Every attempt now runs the suite three times and a test
    that fails once is retired before it can reach the candidate or the classifier.
    """
    task, source_root, tasks_dir, ground_truth = _layout(tmp_path)
    evaluations = 0

    def evaluator(_tests_root: Path, _work_dir: Path) -> EvaluationResult:
        nonlocal evaluations
        evaluations += 1
        return EvaluationResult(
            test_results=[
                TestResult(name="test_ok", branch="branch_a", status="passed", extra={}),
                TestResult(name="test_official", branch="branch_a", status="failure", extra={}),
                TestResult(name="test_bad", branch="branch_a", status="failure" if evaluations == 2 else "passed", extra={}),
                *(TestResult(name=name, branch="branch_a", status="passed", extra={}) for name in _PAD),
            ],
            test_branches=["branch_a"],
        )

    report = reference_test_preparation.prepare_reference_tests(
        task=task,
        source_root=source_root,
        output_root=tmp_path / "skipped-tests",
        ground_truth_dir=ground_truth,
        ground_truth_root=tmp_path / "ground_truth",
        tasks_dir=tasks_dir,
        work_dir=tmp_path / "work",
        evaluator=evaluator,
    )

    assert evaluations == 6
    assert report["added_skipped_tests"] == ["branch_a/test_bad"]
    assert report["attempts"][0]["trials"] == 3 and report["attempts"][0]["failed_tests"] == ["branch_a/test_bad"]
    assert report["verified"] is True
