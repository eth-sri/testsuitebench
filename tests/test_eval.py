# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for the evaluation pipeline (data models, XML parsing, batch logic)."""

import json
import logging
import os
import subprocess
import time
import sys
import tarfile
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path

import pytest
from rich.console import Console

from programbench.container import ContainerEnvironment
from programbench.constants import (
    MAX_JUNIT_DIAGNOSTIC_BYTES,
    MAX_JUNIT_XML_BYTES,
    MAX_RAW_JUNIT_XML_BYTES,
    TASKS_DIR,
    cpus_for_test_branch,
    docker_cpus_for_budget,
)
from programbench.eval import pytest_journal
from programbench.eval.eval import (
    Evaluator,
    EvaluationResult,
    TestBranchError,
    TestResult,
    _PartialTestRunError,
    _merge_pytest_journal_xml,
    _parse_pytest_journal,
    _process_branch_xml,
    count_worker_crashes,
    drop_worker_crash_cases,
    parse_test_results,
)
from programbench.eval.eval_batch import (
    BatchEvalSummary,
    InstanceEvalSummary,
    _summary_from_existing,
    get_branches_to_eval,
)
from programbench.eval.junit_diagnostics import truncate_junit_diagnostics, truncate_utf8
from programbench.eval.test_suite_eval import (
    BinaryTestSuiteResult,
    TestSuiteEvaluationResult,
    TestSuiteEvaluator,
    _JUNIT_DIAGNOSTIC_SANITIZER,
    _MAX_RETAINED_LOG_TEXT_CHARS,
    _bounded_retained_value,
    _bounded_test_diagnostic_value,
    discover_reference_support_executables,
    _sanitize_invalid_xml_chars,
    count_assertions,
    count_python_assertions,
)
from programbench.eval.test_suite_eval_batch import (
    BatchTestSuiteEvalSummary,
    InstanceTestSuiteEvalSummary,
    _evaluate_instance,
    _filter_ignored_mutants,
    _filter_ignored_tests,
    _find_test_suite_payloads,
    _merge_branch_results,
    _summarize_instance,
    run_test_suite_eval_batch,
    _write_eval_json,
)
from programbench.test_generation import (
    _ENSURE_WORKSPACE_PYTHON_COMMAND,
    ARCHIVE_EXCLUDED_DIRS,
    _HIDE_EXECUTABLE_COMMAND,
    _PROGRAMBENCH_STREAM_ENVIRONMENT_CLASS,
    _SOFT_WARNING_MESSAGE,
    SoftWarningAgentMixin,
    _normalize_agent_config,
    _STREAM_SEPARATED_OBSERVATION_TEMPLATE,
    TEST_GENERATION_GOAL_COMMAND,
    _WORKSPACE_PATH,
    _cleanroom_base_image,
    _codex_test_generation_prompt,
    _codex_test_generation_shell_command,
    _copy_generation_cleanroom_to_container,
    _copy_cleanroom,
    _copy_test_suite,
    _ensure_workspace_path,
    _ensure_workspace_python,
    _hide_executable,
    generate_tests_instance,
    GenerationPromptMode,
    _build_agent_templates,
    build_agent_templates,
    _task_cleanroom_image,
)
from programbench.constants import PIP_CONSTRAINT_PATH
from programbench.exceptions import EmptyTestResultError, EvalStepError, XmlParseError
from programbench.mutants import (
    _MUTANT_COPY_EXCLUDES,
    MUTANT_GENERATION_GOAL_COMMAND,
    MUTANT_GENERATION_PROMPT,
    MutantSpec,
    _copy_repo_to_container,
    _no_op_build_repositories,
    _restore_generated_files,
    _mutant_codex_resume_shell_command,
    _repair_mutant_builds,
    _mutant_codex_shell_command,
    _validate_mutant_repositories,
    generate_mutants_instance,
    load_mutant_suite,
)
from programbench.spec_improvement import (
    DEFAULT_CODEX_COMMAND,
    DEFAULT_CODEX_IMAGE,
    specification_prompt,
    _copy_codex_auth_to_container,
    _codex_shell_command,
    _prepare_workspace,
    _stream_codex_json_log,
    improve_specification_instance,
)
from programbench.utils.load_data import (
    get_active_branches,
    get_ignored_tests,
    load_all_instances,
)

JUNIT_XML_ALL_PASS = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="2">
    <testcase classname="tests.test_calculator" name="test_addition" time="0.01"/>
    <testcase classname="tests.test_calculator" name="test_subtraction" time="0.02"/>
  </testsuite>
</testsuites>
"""

JUNIT_XML_MIXED = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="1" tests="3">
    <testcase classname="tests.test_calculator" name="test_addition" time="0.01"/>
    <testcase classname="tests.test_calculator" name="test_subtraction" time="0.02">
      <failure message="assert 7 == 8">AssertionError</failure>
    </testcase>
    <testcase classname="tests.test_calculator" name="test_skip" time="0.0">
      <skipped message="reason"/>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_XML_DUP_SAME_KIND = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1">
    <testcase name="pytest.internal" time="0.0">
      <error message="internal error">trace 1</error>
      <error message="internal error">trace 2</error>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_XML_DUP_MIXED_KIND = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1">
    <testcase name="test_mixed" time="0.0">
      <failure message="timeout">subprocess timed out</failure>
      <error message="worker crashed">xdist worker died</error>
    </testcase>
  </testsuite>
</testsuites>
"""

JUNIT_XML_RERUNS = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="5">
    <testcase classname="tests.t" name="test_exhausts_reruns" time="0.1">
      <rerunFailure message="reran">attempt 1</rerunFailure>
    </testcase>
    <testcase classname="tests.t" name="test_exhausts_reruns" time="0.1">
      <rerunFailure message="reran">attempt 2</rerunFailure>
    </testcase>
    <testcase classname="tests.t" name="test_exhausts_reruns" time="0.1">
      <failure message="boom">attempt 3</failure>
    </testcase>
    <testcase classname="tests.t" name="test_flaky_recovers" time="0.1">
      <rerunFailure message="reran">attempt 1</rerunFailure>
    </testcase>
    <testcase classname="tests.t" name="test_flaky_recovers" time="0.1"/>
    <testcase classname="tests.t" name="test_clean" time="0.1"/>
  </testsuite>
</testsuites>
"""

JUNIT_XML_EMPTY_DUPLICATE_RERUNS = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="6">
    <testcase classname="tests.t" name="test_exhausts_reruns" time="0.1"/>
    <testcase classname="tests.t" name="test_exhausts_reruns" time="0.1"/>
    <testcase classname="tests.t" name="test_exhausts_reruns" time="0.1">
      <failure message="boom">attempt 3</failure>
    </testcase>
    <testcase classname="tests.t" name="test_flaky_recovers" time="0.1"/>
    <testcase classname="tests.t" name="test_flaky_recovers" time="0.1"/>
    <testcase classname="tests.t" name="test_clean" time="0.1"/>
  </testsuite>
</testsuites>
"""


class TestParseTestResults:
    def test_all_pass(self):
        result = parse_test_results(JUNIT_XML_ALL_PASS, branch="b1")
        assert len(result) == 2
        assert all(t.status == "passed" for t in result)
        assert all(t.branch == "b1" for t in result)
        assert {t.name for t in result} == {
            "tests.test_calculator.test_addition",
            "tests.test_calculator.test_subtraction",
        }

    def test_mixed_results(self):
        result = parse_test_results(JUNIT_XML_MIXED, branch="b1")
        by_name = {t.name: t for t in result}
        assert by_name["tests.test_calculator.test_addition"].status == "passed"
        assert by_name["tests.test_calculator.test_subtraction"].status == "failure"
        assert by_name["tests.test_calculator.test_skip"].status == "skipped"

    def test_empty_xml_raises(self):
        with pytest.raises(EmptyTestResultError):
            parse_test_results("   ", branch="b1")

    def test_malformed_xml_raises(self):
        with pytest.raises(XmlParseError):
            parse_test_results("<not>valid xml", branch="b1")

    def test_unnamed_testcase_warning_includes_debug_context(self, caplog):
        raw_xml = """\
<testsuites>
  <testsuite name="pytest" tests="1">
    <testcase time="0.1"><error message="worker crashed">details</error></testcase>
  </testsuite>
</testsuites>
"""

        with caplog.at_level(logging.WARNING, logger="programbench.eval.eval"):
            result = parse_test_results(raw_xml, branch="branch-a")

        assert not result.test_results
        assert caplog.messages == [
            "Skipping JUnit testcase without a usable name "
            "(branch='branch-a', suite='pytest', attributes={'time': '0.1'}, "
            "xml='<testcase time=\"0.1\"><error message=\"worker crashed\">details</error>"
            "</testcase>\\n  ')"
        ]

    def test_unnamed_testcase_warning_bounds_xml_snippet(self, caplog):
        raw_xml = (
            '<testsuite name="pytest"><testcase><error>'
            + "x" * 1_000
            + "</error></testcase></testsuite>"
        )

        with caplog.at_level(logging.WARNING, logger="programbench.eval.eval"):
            parse_test_results(raw_xml, branch="branch-a")

        assert len(caplog.messages) == 1
        assert "xml='<testcase><error>" in caplog.messages[0]
        assert "xxx...'" in caplog.messages[0]
        assert len(caplog.messages[0]) < 700

    def test_sanitize_invalid_xml_chars_keeps_junit_parseable(self):
        raw_xml = (
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
            "<testsuite tests=\"1\" failures=\"1\">"
            "<testcase classname=\"tests.cli\" name=\"test_binary_stdout\">"
            "<failure message=\"bad output\">blob.js:1:\x00\x01\x02foo(1)</failure>"
            "</testcase>"
            "</testsuite>"
        )

        result = parse_test_results(_sanitize_invalid_xml_chars(raw_xml), branch="generated")

        assert result.test_results[0].name == "tests.cli.test_binary_stdout"
        assert result.test_results[0].status == "failure"
        assert "\\x00\\x01\\x02" in result.test_results[0].extra["text"]

    def test_duplicate_same_kind_collapses(self):
        result = parse_test_results(JUNIT_XML_DUP_SAME_KIND, branch="b1")
        assert len(result) == 1
        t = result.test_results[0]
        assert t.status == "error"
        assert t.extra["message"] == "internal error"

    def test_rerun_attempts_are_not_scored_as_passes(self):
        result = parse_test_results(JUNIT_XML_RERUNS, branch="b1")
        by_name = {t.name: t for t in result}
        assert len(result) == 3
        assert by_name["tests.t.test_exhausts_reruns"].status == "failure"
        assert by_name["tests.t.test_exhausts_reruns"].extra["reruns"] == 2
        assert by_name["tests.t.test_flaky_recovers"].status == "passed"
        assert by_name["tests.t.test_flaky_recovers"].extra["reruns"] == 1
        assert "reruns" not in by_name["tests.t.test_clean"].extra
        assert result.score == pytest.approx(2 / 3)

    def test_empty_duplicate_reruns_keep_only_final_attempt(self):
        result = parse_test_results(JUNIT_XML_EMPTY_DUPLICATE_RERUNS, branch="b1")
        by_name = {t.name: t for t in result}
        assert len(result) == 3
        assert by_name["tests.t.test_exhausts_reruns"].status == "failure"
        assert by_name["tests.t.test_exhausts_reruns"].extra["reruns"] == 2
        assert by_name["tests.t.test_flaky_recovers"].status == "passed"
        assert by_name["tests.t.test_flaky_recovers"].extra["reruns"] == 1
        assert "reruns" not in by_name["tests.t.test_clean"].extra
        assert result.score == pytest.approx(2 / 3)

    def test_duplicate_mixed_kind_is_system_error(self):
        result = parse_test_results(JUNIT_XML_DUP_MIXED_KIND, branch="b1")
        assert len(result) == 1
        assert result.test_results[0].status == "system_error"
        assert "got 2" in result.test_results[0].extra["error_details"]


class TestPytestJournal:
    @staticmethod
    def _report(when, outcome):
        class Report:
            nodeid = "eval/tests/test_example.py::test_a"
            location = ("eval/tests/test_example.py", 1, "test_a")
            duration = 0.1
            longreprtext = "assertion details"
            wasxfail = None

        report = Report()
        report.when = when
        report.outcome = outcome
        return report

    def test_checkpoints_only_final_rerun_outcome(self, tmp_path, monkeypatch):
        journal = tmp_path / "results.jsonl"
        monkeypatch.setattr(pytest_journal, "_IS_CONTROLLER", True)
        monkeypatch.setattr(pytest_journal, "_JOURNAL_PATH", journal)
        pytest_journal._REPORTS.clear()

        pytest_journal.pytest_runtest_logreport(self._report("setup", "passed"))
        pytest_journal.pytest_runtest_logreport(self._report("call", "rerun"))
        pytest_journal.pytest_runtest_logreport(self._report("teardown", "passed"))
        assert not journal.exists()

        pytest_journal.pytest_runtest_logreport(self._report("setup", "passed"))
        pytest_journal.pytest_runtest_logreport(self._report("call", "passed"))
        pytest_journal.pytest_runtest_logreport(self._report("teardown", "passed"))

        records = _parse_pytest_journal(journal.read_text())
        assert records["eval/tests/test_example.py::test_a"]["outcome"] == "passed"

    def test_completed_nodeids_are_deselected(self, tmp_path, monkeypatch):
        completed = tmp_path / "completed.json"
        completed.write_text(json.dumps(["tests/test_example.py::test_a"]))
        monkeypatch.setattr(pytest_journal, "_COMPLETED_PATH", completed)
        items = [
            type("Item", (), {"nodeid": "tests/test_example.py::test_a"})(),
            type("Item", (), {"nodeid": "tests/test_example.py::test_b"})(),
        ]
        deselected = []

        class Hook:
            def pytest_deselected(self, *, items):
                deselected.extend(item.nodeid for item in items)

        config = type("Config", (), {"hook": Hook()})()

        pytest_journal.pytest_collection_modifyitems(config, items)

        assert [item.nodeid for item in items] == ["tests/test_example.py::test_b"]
        assert deselected == ["tests/test_example.py::test_a"]

    def test_torn_final_journal_record_is_ignored(self):
        first = json.dumps({
            "nodeid": "eval/tests/test_example.py::test_a",
            "phase": "call",
            "outcome": "passed",
        })

        records = _parse_pytest_journal(first + "\n{\"nodeid\":")

        assert set(records) == {"eval/tests/test_example.py::test_a"}

    def test_journal_records_convert_to_normal_junit_names(self):
        records = {
            "eval/tests/test_example.py::TestGroup::test_a[param]": {
                "nodeid": "eval/tests/test_example.py::TestGroup::test_a[param]",
                "phase": "call",
                "outcome": "failed",
                "duration": 1.5,
                "message": "assert false",
            }
        }

        parsed = parse_test_results(_merge_pytest_journal_xml(records), branch="branch-a")

        assert parsed.test_results[0].name == "eval.tests.test_example.TestGroup.test_a[param]"
        assert parsed.test_results[0].status == "failure"

    def test_journal_xml_escapes_xml_illegal_control_characters(self):
        records = {
            "eval/tests/test_example.py::test_binary_\x00output": {
                "nodeid": "eval/tests/test_example.py::test_binary_\x00output",
                "phase": "call",
                "outcome": "failed",
                "message": "binary output: \x01\x02",
            }
        }

        raw_xml = _merge_pytest_journal_xml(records)
        parsed = parse_test_results(raw_xml, branch="branch-a")

        assert parsed.test_results[0].name.endswith("test_binary_\\x00output")
        assert parsed.test_results[0].status == "failure"
        assert "binary output: \\x01\\x02" in parsed.test_results[0].extra["text"]


class TestTimeoutResume:
    @staticmethod
    def _record(nodeid, outcome="passed"):
        return {
            "nodeid": nodeid,
            "phase": "call",
            "outcome": outcome,
            "duration": 0.1,
            "message": "",
        }

    def test_retry_runs_only_unfinished_tests_and_merges_results(self, monkeypatch):
        first_nodeid = "eval/tests/test_example.py::test_a"
        evaluator = Evaluator(
            tests_branches=["branch-a"],
            tests_by_branch={
                "branch-a": [
                    "eval.tests.test_example.test_a",
                    "eval.tests.test_example.test_b",
                ]
            },
            branch_retries=1,
        )
        completed_arguments = []

        def run_branch(branch, image, log_buf, *, serial_pytest=False, completed_nodeids=None, recover_journal=False):
            del branch, image, log_buf, serial_pytest, recover_journal
            completed_arguments.append(set(completed_nodeids or set()))
            if len(completed_arguments) == 1:
                raise _PartialTestRunError(
                    "run_tests_timeout",
                    "timed out",
                    {first_nodeid: self._record(first_nodeid)},
                )
            return (
                "<testsuites><testsuite>"
                "<testcase classname=\"eval.tests.test_example\" name=\"test_b\"/>"
                "</testsuite></testsuites>"
            )

        monkeypatch.setattr(evaluator, "_run_test_branch", run_branch)

        evaluator._evaluate_branch("branch-a", "image")

        assert completed_arguments == [set(), {first_nodeid}]
        assert {result.name: result.status for result in evaluator.result.test_results} == {
            "eval.tests.test_example.test_a": "passed",
            "eval.tests.test_example.test_b": "passed",
        }
        assert evaluator.result.test_branch_errors == {}

    def test_runner_keeps_global_reruns_and_extracts_timeout_journal(self, tmp_path, monkeypatch):
        branch = tmp_path / "branch-a"
        branch.mkdir()
        evaluator = Evaluator(tests_branches=["branch-a"], blob_dir=tmp_path)
        evaluator._has_rerunfailures = True
        commands = []
        copied = []

        class FakeEnv:
            executable = "docker"
            container_id = "container"

            def execute(self, command, timeout=None):
                commands.append(command)
                timed_out = "&& ./eval/run.sh" in command
                return {
                    "output": "",
                    "stdout": "",
                    "stderr": "",
                    "returncode": -1 if timed_out else 0,
                    "exception_info": "Command timed out after 3600s" if timed_out else "",
                }

            def copy_in(self, local_path, container_path):
                copied.append((Path(local_path), container_path))

            def cleanup(self):
                pass

        monkeypatch.setattr(evaluator, "_new_env", lambda *args, **kwargs: FakeEnv())
        for name in (
            "_clean_workspace_for_test_payload",
            "_stash_test_go_module_files_for_test_payload",
            "_restore_go_module_files_for_test_payload",
            "_restore_executable",
            "_prepare_workspace_bin",
        ):
            monkeypatch.setattr(evaluator, name, lambda *args, **kwargs: None)
        record = self._record("eval/tests/test_example.py::test_a")
        monkeypatch.setattr(
            evaluator,
            "_copy_file_from_container",
            lambda **kwargs: json.dumps(record) + "\n",
        )

        with pytest.raises(_PartialTestRunError) as raised:
            evaluator._run_test_branch(
                "branch-a",
                "image",
                [],
                completed_nodeids={"eval/tests/test_example.py::already_done"},
            )

        assert set(raised.value.records) == {"eval/tests/test_example.py::test_a"}
        wipe_command = "rm -rf /workspace/* /workspace/.[!.]*"
        assert wipe_command in commands
        run_command = next(command for command in commands if "&& ./eval/run.sh" in command)
        assert commands.index(wipe_command) < commands.index(run_command)
        assert "--reruns=2 --reruns-delay=1" in run_command
        assert "PYTEST_PLUGINS" in run_command
        assert any(path.name == "pytest_journal.py" for path, _ in copied)
        # PYTEST_PLUGINS imports pytest_journal before collection, so a run.sh
        # that sets `PYTHONPATH=. pytest ...` would otherwise abort the branch.
        pth_command = next(command for command in commands if "programbench-pytest-journal.pth" in command)
        assert "site.getsitepackages()" in pth_command
        assert commands.index(pth_command) < commands.index(run_command)
        assert any(destination.endswith("completed.json") for _, destination in copied)

    def test_exhausted_timeout_preserves_completed_and_marks_only_unfinished(self, monkeypatch):
        first_nodeid = "eval/tests/test_example.py::test_a"
        evaluator = Evaluator(
            tests_branches=["branch-a"],
            tests_by_branch={
                "branch-a": [
                    "eval.tests.test_example.test_a",
                    "eval.tests.test_example.test_b",
                ]
            },
            branch_retries=0,
            check_junit_completeness=False,
        )

        def run_branch(*args, **kwargs):
            raise _PartialTestRunError(
                "run_tests_timeout",
                "timed out",
                {first_nodeid: self._record(first_nodeid)},
            )

        monkeypatch.setattr(evaluator, "_run_test_branch", run_branch)

        evaluator._evaluate_branch("branch-a", "image")

        by_name = {result.name: result for result in evaluator.result.test_results}
        assert by_name["eval.tests.test_example.test_a"].status == "passed"
        assert by_name["eval.tests.test_example.test_b"].status == "not_run"
        assert by_name["eval.tests.test_example.test_b"].extra["error_code"] == "run_tests_timeout"
        assert evaluator.result.test_branch_errors["branch-a"][0].error_code == "run_tests_timeout"

        replayed = Evaluator(
            tests_branches=["branch-a"],
            tests_by_branch=evaluator.tests_by_branch,
            from_existing=evaluator.result,
            check_junit_completeness=False,
        )
        replayed._evaluate_branch("branch-a", "image")
        replayed_by_name = {result.name: result for result in replayed.result.test_results}
        assert replayed_by_name["eval.tests.test_example.test_a"].status == "passed"
        assert replayed_by_name["eval.tests.test_example.test_b"].status == "not_run"
        assert replayed_by_name["eval.tests.test_example.test_b"].extra["error_code"] == "run_tests_timeout"
        assert replayed.result.test_branch_errors["branch-a"][0].error_code == "run_tests_timeout"


class TestProcessBranchXml:
    def test_missing_tests_get_not_run(self):
        tests_by_branch = {
            "b1": [
                "tests.test_calculator.test_addition",
                "tests.test_calculator.test_subtraction",
                "tests.test_calculator.test_missing",
            ]
        }
        results, warnings = _process_branch_xml(JUNIT_XML_ALL_PASS, "b1", tests_by_branch)
        by_name = {r.name: r for r in results}
        assert by_name["tests.test_calculator.test_missing"].status == "not_run"
        assert len(warnings) == 0

    def test_unexpected_tests_warn(self):
        tests_by_branch = {"b1": ["tests.test_calculator.test_addition"]}
        results, warnings = _process_branch_xml(JUNIT_XML_ALL_PASS, "b1", tests_by_branch)
        assert any("not in tests.json" in w for w in warnings)

    def test_completeness_check_can_be_disabled(self):
        tests_by_branch = {
            "b1": [
                "tests.test_calculator.test_addition",
                "tests.test_calculator.test_renamed_old",
            ]
        }
        results, warnings = _process_branch_xml(
            JUNIT_XML_ALL_PASS,
            "b1",
            tests_by_branch,
            check_completeness=False,
        )
        assert warnings == []
        assert {r.name for r in results} == {
            "tests.test_calculator.test_addition",
            "tests.test_calculator.test_subtraction",
        }
        assert all(r.status != "not_run" for r in results)


class TestCountWorkerCrashes:
    XDIST_CRASH_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="2" failures="0" skipped="0" tests="3">
    <testcase classname="t.t1" name="ok" time="0.01"/>
    <testcase classname="t.t1" name="bust" time="0.000">
      <error message="failed on setup with &quot;worker 'gw7' crashed while running 't.t1::bust'&quot;">worker 'gw7' crashed while running 't.t1::bust'</error>
    </testcase>
    <testcase classname="t.t2" name="bust2" time="0.000">
      <error message="failed on setup with &quot;worker 'gw3' crashed while running 't.t2::bust2'&quot;">worker 'gw3' crashed while running 't.t2::bust2'</error>
    </testcase>
  </testsuite>
</testsuites>
"""

    REGULAR_FAILURE_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="0" tests="1">
    <testcase classname="t" name="bad"><failure message="AssertionError">expected 1 got 2</failure></testcase>
  </testsuite>
</testsuites>
"""

    XDIST_INTERNAL_XML = """\
<testsuites><testsuite errors="1" tests="1">
  <testcase classname="pytest" name="internal">
    <error message="internal error">worker_internal_error: WorkerController gw0 crashed in worker_workerfinished</error>
  </testcase>
</testsuite></testsuites>
"""

    @pytest.mark.parametrize(
        ("xml", "expected"),
        [
            ("", 0),
            ("<not xml>", 0),
            (REGULAR_FAILURE_XML, 0),
            (JUNIT_XML_ALL_PASS, 0),
            (XDIST_CRASH_XML, 2),
            (XDIST_INTERNAL_XML, 1),
        ],
    )
    def test_counts(self, xml, expected):
        assert count_worker_crashes(xml) == expected

    def test_drop_worker_crash_cases_keeps_real_results(self):
        kept = parse_test_results(drop_worker_crash_cases(self.XDIST_CRASH_XML), branch="b1")
        assert [(t.name, t.status) for t in kept.test_results] == [("t.t1.ok", "passed")]
        assert parse_test_results(drop_worker_crash_cases(self.XDIST_INTERNAL_XML), branch="b1").test_results == []

    def test_journal_merge_replaces_internal_error_stub(self):
        records = _parse_pytest_journal(
            '{"nodeid": "eval/tests/test_a.py::test_ok", "outcome": "passed", "phase": "call"}\n'
            '{"nodeid": "eval/tests/test_a.py::test_bad[x]", "outcome": "failed", "phase": "call", "message": "boom"}\n'
        )
        merged = _merge_pytest_journal_xml(records, drop_worker_crash_cases(self.XDIST_INTERNAL_XML))
        assert count_worker_crashes(merged) == 0
        assert {(t.name, t.status) for t in parse_test_results(merged, branch="b1").test_results} == {
            ("eval.tests.test_a.test_ok", "passed"),
            ("eval.tests.test_a.test_bad[x]", "failure"),
        }


class TestEvaluationResult:
    def test_score_all_pass(self):
        result = EvaluationResult(
            test_results=[
                TestResult(name="t1", branch="b1", status="passed", extra={}),
                TestResult(name="t2", branch="b1", status="passed", extra={}),
            ]
        )
        assert result.score == 1.0
        assert result.n_resolved == 2

    def test_score_partial(self):
        result = EvaluationResult(
            test_results=[
                TestResult(name="t1", branch="b1", status="passed", extra={}),
                TestResult(name="t2", branch="b1", status="failure", extra={}),
            ]
        )
        assert result.score == 0.5

    def test_score_empty(self):
        assert EvaluationResult().score == 0.0

    def test_without_ignored(self):
        result = EvaluationResult(
            test_results=[
                TestResult(name="t1", branch="b1", status="passed", extra={}),
                TestResult(name="t2", branch="b1", status="failure", extra={}),
            ]
        )
        filtered = result.without_ignored({"b1/t2"})
        assert len(filtered) == 1
        assert filtered.score == 1.0

    def test_for_branches(self):
        result = EvaluationResult(
            test_results=[
                TestResult(name="t1", branch="b1", status="passed", extra={}),
                TestResult(name="t2", branch="b2", status="failure", extra={}),
            ],
            test_branches=["b1", "b2"],
            test_branch_errors={"b2": [TestBranchError(error_code="x", error_details="")]},
        )
        scoped = result.for_branches(["b1"])
        assert len(scoped) == 1
        assert "b2" not in scoped.test_branch_errors


class TestGetBranchesToEval:
    def test_no_existing_returns_all(self, tmp_path):
        assert get_branches_to_eval(
            eval_json=tmp_path / "nonexistent.json",
            all_test_branches=["b1", "b2"],
            tests_by_branch={"b1": ["t1"], "b2": ["t2"]},
            ignored_tests=set(),
        ) == ["b1", "b2"]

    def test_fully_evaluated_returns_empty(self, tmp_path):
        eval_json = tmp_path / "eval.json"
        result = EvaluationResult(
            test_results=[
                TestResult(name="t1", branch="b1", status="passed", extra={}),
            ],
            test_branches=["b1"],
        )
        eval_json.write_text(result.model_dump_json())
        assert (
            get_branches_to_eval(
                eval_json=eval_json,
                all_test_branches=["b1"],
                tests_by_branch={"b1": ["t1"]},
                ignored_tests=set(),
            )
            == []
        )

    def test_branch_with_error_needs_reeval(self, tmp_path):
        eval_json = tmp_path / "eval.json"
        result = EvaluationResult(
            test_results=[],
            test_branches=["b1"],
            test_branch_errors={"b1": [TestBranchError(error_code="fail", error_details="")]},
        )
        eval_json.write_text(result.model_dump_json())
        assert get_branches_to_eval(
            eval_json=eval_json,
            all_test_branches=["b1"],
            tests_by_branch={"b1": ["t1"]},
            ignored_tests=set(),
        ) == ["b1"]

    def test_missing_manifest_tests_do_not_force_reeval_when_completeness_disabled(self, tmp_path):
        eval_json = tmp_path / "eval.json"
        result = EvaluationResult(
            test_results=[TestResult(name="renamed_t1", branch="b1", status="passed", extra={})],
            test_branches=["b1"],
        )
        eval_json.write_text(result.model_dump_json())
        assert get_branches_to_eval(
            eval_json=eval_json,
            all_test_branches=["b1"],
            tests_by_branch={"b1": ["old_t1"]},
            ignored_tests=set(),
            check_junit_completeness=False,
        ) == []


class TestSummaryFromExisting:
    def test_reprocessing_persists_the_ignore_filtered_result(self, tmp_path):
        xml = (
            "<testsuites><testsuite name='pytest'>"
            "<testcase classname='tests.test_cli' name='test_kept'/>"
            "<testcase classname='tests.test_cli' name='test_skipped'>"
            "<failure message='boom'/></testcase>"
            "</testsuite></testsuites>"
        )
        eval_json = tmp_path / "eval.json"
        eval_json.write_text(
            EvaluationResult(
                test_branches=["b1"],
                log=[{"step": "results_read", "branch": "b1", "output": xml, "returncode": 0}],
            ).model_dump_json()
        )

        summary = _summary_from_existing(
            "org__repo.123",
            eval_json,
            {"b1/tests.test_cli.test_skipped"},
            current_branches=["b1"],
            tests_by_branch={"b1": ["tests.test_cli.test_kept", "tests.test_cli.test_skipped"]},
            check_junit_completeness=False,
        )

        assert (summary.n_tests, summary.n_resolved, summary.score) == (1, 1, 1.0)
        assert [t.name for t in EvaluationResult.model_validate_json(eval_json.read_text())] == [
            "tests.test_cli.test_kept"
        ]


class TestInstanceEvalSummary:
    def test_from_eval_result(self):
        result = EvaluationResult(
            test_results=[
                TestResult(name="t1", branch="b1", status="passed", extra={}),
                TestResult(name="t2", branch="b1", status="failure", extra={}),
            ],
            test_branches=["b1"],
        )
        summary = InstanceEvalSummary.from_eval_result("test_instance", result)
        assert summary.score == 0.5
        assert summary.n_resolved == 1
        assert summary.n_tests == 2


class TestBatchEvalSummary:
    def test_average_pass_rate(self):
        batch = BatchEvalSummary(
            summaries=[
                InstanceEvalSummary(instance_id="a", score=1.0, n_resolved=2, n_tests=2),
                InstanceEvalSummary(instance_id="b", score=0.0, n_resolved=0, n_tests=2),
            ]
        )
        assert batch.average_pass_rate == 0.5
        assert batch.total_instances == 2


class TestGeneratedTestSuiteAssertionSummary:
    def test_counts_python_assertions_in_directory(self, tmp_path):
        test_dir = tmp_path / "eval"
        test_dir.mkdir()
        (test_dir / "test_cli.py").write_text(
            "import unittest\n"
            "def test_plain():\n"
            "    assert 1 == 1\n"
            "    assert \"x\"\n"
            "class Example(unittest.TestCase):\n"
            "    def test_method(self):\n"
            "        self.assertEqual(1, 1)\n"
        )

        assert count_python_assertions(tmp_path) == 3

    def test_counts_python_assertions_in_tarball(self, tmp_path):
        payload = tmp_path / "payload" / "eval"
        payload.mkdir(parents=True)
        (payload / "test_cli.py").write_text(
            "def test_one():\n"
            "    assert True\n"
        )
        (payload / "notes.txt").write_text("assert ignored")
        archive = tmp_path / "tests.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(tmp_path / "payload" / "eval", arcname="eval")

        assert count_python_assertions(archive) == 1

    def test_counts_shell_and_perl_assertions_in_directory(self, tmp_path):
        test_dir = tmp_path / "eval"
        test_dir.mkdir()
        (test_dir / "run.sh").write_text(
            "assert_eq() { [ \"$1\" = \"$2\" ]; }\n"
            "assert_eq \"$got\" \"ok\" || return 1\n"
            "[ \"$rc\" -eq 0 ] || return 1\n"
            "grep -q needle out.txt || return 1\n"
            "if [ \"$setup\" = skip ]; then return 0; fi\n"
        )
        (test_dir / "cli.t").write_text(
            "use Test::More;\n"
            "ok($ran, 'ran command');\n"
            "is $stdout, 'ok', 'stdout';\n"
            "cmp_ok($rc, '==', 0, 'exit code');\n"
            "sub helper { ok(1, 'not counted from helper definition line') }\n"
        )

        assert count_assertions(tmp_path) == 6

    def test_counts_shell_assertions_in_tarball(self, tmp_path):
        payload = tmp_path / "payload" / "eval"
        payload.mkdir(parents=True)
        (payload / "run.sh").write_text(
            "assert_contains \"$out\" needle label || return 1\n"
            "test -s output.txt || return 1\n"
        )
        (payload / "results.xml").write_text("<testsuites><testcase name='ignored'/></testsuites>")
        archive = tmp_path / "tests.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(tmp_path / "payload" / "eval", arcname="eval")

        assert count_assertions(archive) == 2

    def test_generated_suite_summary_omits_assertion_count(self):
        batch = BatchTestSuiteEvalSummary(
            summaries=[
                InstanceTestSuiteEvalSummary(
                    instance_id="test_instance",
                    score=1.0,
                    n_passed=2,
                    n_tests=2,
                    n_test_functions=2,
                    ground_truth_passed=True,
                )
            ]
        )
        console = Console(record=True, width=120, color_system=None)

        console.print(batch.summary())
        output = console.export_text()

        assert "Assertions" not in output
        assert " Score " not in output.replace("Mutation Score", "")
        assert "Validity Rate" in output
        assert "Mutation Score" in output
        assert "Tests" in output
        assert "test_instance" in output
        assert "2 executed generated tests" in output

    def test_generated_suite_summary_uses_checkmark_only_for_exact_hundred(self):
        batch = BatchTestSuiteEvalSummary(
            summaries=[
                InstanceTestSuiteEvalSummary(
                    instance_id="exact",
                    score=1.0,
                    n_passed=1,
                    n_tests=1,
                    ground_truth_passed=True,
                    validity_rate=1.0,
                    mutation_score=1.0,
                ),
                InstanceTestSuiteEvalSummary(
                    instance_id="rounded",
                    score=0.999,
                    n_passed=999,
                    n_tests=1000,
                    validity_rate=0.999,
                    mutation_score=0.999,
                ),
            ]
        )
        console = Console(record=True, width=120, color_system=None)

        console.print(batch.summary())
        output = console.export_text()
        exact_row = next(line for line in output.splitlines() if line.strip().startswith("exact"))
        rounded_row = next(line for line in output.splitlines() if line.strip().startswith("rounded"))
        average_row = next(line for line in output.splitlines() if line.strip().startswith("Average"))

        assert exact_row.split()[:3] == ["exact", "✅", "✅"]
        assert rounded_row.split()[:3] == ["rounded", "99.9", "99.9"]
        assert average_row.split()[:3] == ["Average", "100.0", "100.0"]
        assert "A displayed 100.0 may be rounded. Only ✅ indicates an exact score of 100%." in output

        exact_batch = BatchTestSuiteEvalSummary(summaries=[batch.summaries[0]])
        exact_console = Console(record=True, width=120, color_system=None)
        exact_console.print(exact_batch.summary())
        exact_average_row = next(
            line for line in exact_console.export_text().splitlines() if line.strip().startswith("Average")
        )
        assert exact_average_row.split()[:3] == ["Average", "✅", "✅"]


    def test_evaluate_instance_detailed_logs_existing_result_without_force(self, tmp_path, caplog):
        instance_id = "example__tool.abc1234"
        eval_dir = tmp_path / instance_id
        eval_dir.mkdir()
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[TestResult(name="test_one", status="passed", extra={})],
                ),
                BinaryTestSuiteResult(
                    binary_id="mutant_1",
                    role="candidate",
                    test_results=[TestResult(name="test_one", status="failure", extra={})],
                ),
            ]
        )
        (eval_dir / f"{instance_id}.test_eval.json").write_text(result.model_dump_json())
        caplog.set_level(logging.INFO, logger="programbench.eval.test_suite_eval_batch")

        summary = _evaluate_instance(
            instance_id=instance_id,
            instance={"image_name": "programbench/example.abc1234"},
            source_dir=tmp_path,
            target_dir=tmp_path,
            force=False,
            archive_name="tests.tar.gz",
            detailed_logs=True,
        )

        assert summary is not None
        assert summary.n_mutants_killed == 1
        messages = "\n".join(record.getMessage() for record in caplog.records)
        assert "Skipping example__tool.abc1234 (already evaluated, use --force to re-run)" in messages
        assert "Failure matrix:" not in messages
        csv_text = (eval_dir / f"{instance_id}.failure_matrix.csv").read_text()
        assert "test_function,ground_truth,mutant_1" in csv_text
        assert "test_one,.,F" in csv_text

    def test_summarize_instance_detailed_logs_existing_result(self, tmp_path, caplog):
        instance_id = "example__tool.abc1234"
        eval_dir = tmp_path / instance_id
        eval_dir.mkdir()
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[TestResult(name="test_one", status="failure", extra={})],
                ),
                BinaryTestSuiteResult(
                    binary_id="mutant_1",
                    role="candidate",
                    test_results=[TestResult(name="test_one", status="failure", extra={})],
                ),
            ]
        )
        (eval_dir / f"{instance_id}.test_eval.json").write_text(result.model_dump_json())
        caplog.set_level(logging.INFO, logger="programbench.eval.test_suite_eval_batch")

        summary = _summarize_instance(
            instance_id=instance_id,
            source_dir=tmp_path,
            target_dir=tmp_path,
            archive_name="tests.tar.gz",
            detailed_logs=True,
        )

        assert summary is not None
        messages = "\n".join(record.getMessage() for record in caplog.records)
        assert "Failure matrix:" not in messages
        csv_text = (eval_dir / f"{instance_id}.failure_matrix.csv").read_text()
        assert "test_function,ground_truth,mutant_1" in csv_text
        assert "test_one,F,F" in csv_text

    def test_batch_summarize_only_dispatches_without_evaluation_arguments(
        self, tmp_path
    ):
        instance_id = "abishekvashok__cmatrix.5c082c6"
        eval_dir = tmp_path / instance_id
        eval_dir.mkdir()
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        TestResult(name="test_one", status="passed", extra={})
                    ],
                )
            ]
        )
        (eval_dir / f"{instance_id}.test_eval.json").write_text(
            result.model_dump_json()
        )

        run_test_suite_eval_batch(
            sources=[tmp_path],
            summarize_only=True,
            reference_trials=3,
        )

    def test_find_test_suite_payloads_returns_all_branch_directories(self, tmp_path):
        instance_id = "example__tool.abc1234"
        instance_root = tmp_path / instance_id
        for branch_name in ["branch-b", "branch-a"]:
            branch = instance_root / branch_name
            (branch / "eval").mkdir(parents=True)
            (branch / "eval" / "run.sh").write_text("pytest\n")
        (instance_root / "tests_untar" / "eval").mkdir(parents=True)
        (instance_root / "tests_untar" / "eval" / "run.sh").write_text("stale\n")

        payloads = _find_test_suite_payloads(
            source_dir=tmp_path,
            instance_id=instance_id,
            archive_name="tests.tar.gz",
        )

        assert [payload.name for payload in payloads] == ["branch-a", "branch-b"]

    def test_merge_branch_results_prefixes_test_names(self):
        result_a = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[TestResult(name="test_same", status="passed", extra={})],
                ),
            ],
            n_assertions=2,
        )
        result_b = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[TestResult(name="test_same", status="failure", extra={})],
                ),
            ],
            n_assertions=3,
        )

        merged = _merge_branch_results([("branch-a", result_a), ("branch-b", result_b)])

        assert merged.n_test_functions == 2
        assert merged.n_assertions == 5
        assert [t.name for t in merged.binary_results[0].test_results] == [
            "branch-a/test_same",
            "branch-b/test_same",
        ]


    def test_filter_ignored_mutants_drops_candidates_from_mutation_score(self):
        def binary(binary_id, role, status):
            return BinaryTestSuiteResult(
                binary_id=binary_id, role=role, test_results=[TestResult(name="branch-a/test_a", status=status, extra={})],
            )

        result = TestSuiteEvaluationResult(
            binary_results=[
                binary("ground_truth", "ground_truth", "passed"),
                binary("repo_1", "candidate", "failure"),
                binary("repo_2", "candidate", "passed"),
            ]
        )

        assert _filter_ignored_mutants(result, set()) is result
        assert (result.n_mutants, result.n_mutants_killed, result.mutation_score) == (2, 1, 0.5)
        filtered = _filter_ignored_mutants(result, {"repo_2"})
        assert [b.binary_id for b in filtered.binary_results] == ["ground_truth", "repo_1"]
        assert (filtered.n_mutants, filtered.n_mutants_killed, filtered.mutation_score) == (1, 1, 1.0)

    def test_filter_ignored_tests_removes_branch_prefixed_tests_from_all_binaries(self):
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        TestResult(name="branch-a/test_keep", status="passed", extra={}),
                        TestResult(name="branch-a/test_ignore", status="failure", extra={}),
                    ],
                ),
                BinaryTestSuiteResult(
                    binary_id="mutant_1",
                    role="candidate",
                    test_results=[
                        TestResult(name="branch-a/test_keep", status="passed", extra={}),
                        TestResult(name="branch-a/test_ignore", status="failure", extra={}),
                    ],
                ),
            ]
        )

        filtered = _filter_ignored_tests(result, {"branch-a/test_ignore"})

        assert filtered.n_test_functions == 1
        assert filtered.ground_truth_passed
        assert [t.name for binary in filtered.binary_results for t in binary.test_results] == [
            "branch-a/test_keep",
            "branch-a/test_keep",
        ]


    def test_evaluate_instance_reallocates_full_worker_budget_between_mutant_payloads(
        self, tmp_path, monkeypatch, caplog
    ):
        instance_id = "example__tool.abc1234"
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        for branch_name in ["branch-a", "branch-b", "branch-c"]:
            branch = source_dir / instance_id / branch_name
            (branch / "eval").mkdir(parents=True)
            (branch / "eval" / "run.sh").write_text("pytest\n")
        seen_workers = []

        class FakeMutantSuite:
            mutants = [
                MutantSpec(id="m1", payload="m1/executable"),
                MutantSpec(id="m2", payload="m2/executable"),
            ]

        class FakeEvaluator(TestSuiteEvaluator):
            def __init__(self, *, test_suite_archive, branch_workers, mutant_progress_callback=None, **kwargs):
                self.test_suite_archive = test_suite_archive
                self.branch_workers = branch_workers
                self.mutant_progress_callback = mutant_progress_callback

            def run(self):
                seen_workers.append(self.branch_workers)
                for _ in range(2):
                    self.mutant_progress_callback()
                return TestSuiteEvaluationResult(
                    binary_results=[
                        BinaryTestSuiteResult(
                            binary_id="ground_truth",
                            role="ground_truth",
                            test_results=[
                                TestResult(name="test_keep", status="passed", extra={}),
                                TestResult(name="test_ignore", status="failure", extra={}),
                            ],
                        ),
                        BinaryTestSuiteResult(
                            binary_id="mutant_1",
                            role="candidate",
                            test_results=[
                                TestResult(name="test_keep", status="failure", extra={}),
                                TestResult(name="test_ignore", status="failure", extra={}),
                            ],
                        ),
                    ]
                )

        monkeypatch.setattr("programbench.eval.test_suite_eval_batch.TestSuiteEvaluator", FakeEvaluator)
        monkeypatch.setattr("programbench.eval.test_suite_eval_batch.sys.stderr.isatty", lambda: False)
        monkeypatch.setattr(
            "programbench.eval.test_suite_eval_batch.load_mutant_suite",
            lambda mutants_dir, instance_id: (tmp_path, FakeMutantSuite()),
        )
        caplog.set_level(logging.INFO, logger="programbench.eval.test_suite_eval_batch")

        summary = _evaluate_instance(
            instance_id=instance_id,
            instance={"image_name": "programbench/example"},
            source_dir=source_dir,
            target_dir=target_dir,
            force=True,
            archive_name="tests.tar.gz",
            branch_workers=6,
            detailed_logs=True,
            ignored_tests={"branch-a/test_ignore", "branch-b/test_ignore", "branch-c/test_ignore"},
            mutants_dir=tmp_path / "mutants",
        )

        assert summary is not None
        assert summary.n_test_functions == 3
        assert seen_workers == [6, 6, 6]
        messages = [record.getMessage() for record in caplog.records]
        assert messages.count(
            "Evaluating example__tool.abc1234: 3 payload(s), 2 mutant(s) per payload; "
            "3 payload coordinator(s), 6 shared binary container(s) total"
        ) == 1
        assert sum(
            message.startswith("Mutant evaluation progress for example__tool.abc1234:")
            for message in messages
        ) == 6
        assert any(
            message.startswith(
                "Mutant evaluation progress for example__tool.abc1234: 6/6 (100%)"
            )
            for message in messages
        )
        assert all("test payload" not in message for message in messages)
        csv_text = (target_dir / instance_id / f"{instance_id}.failure_matrix.csv").read_text()
        assert "branch-a/test_keep,.,F" in csv_text
        assert "branch-a/test_ignore" not in csv_text


    def test_evaluate_instance_filters_mutants_by_id(self, tmp_path, monkeypatch):
        instance_id = "example__tool.abc1234"
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        payload = source_dir / instance_id
        (payload / "eval").mkdir(parents=True)
        (payload / "eval" / "run.sh").write_text("pytest\n")
        seen_mutants = []
        seen_ground_truth = []
        ground_truth = tmp_path / "ground-truth" / instance_id / "executable"
        ground_truth.parent.mkdir(parents=True)
        ground_truth.write_bytes(b"source-built")

        class FakeMutantSuite:
            mutants = [
                MutantSpec(id="m1", payload="m1/executable"),
                MutantSpec(id="m2", payload="m2/executable"),
            ]

        class FakeEvaluator:
            def __init__(self, *, mutants, ground_truth_executable=None, **_kwargs):
                seen_mutants.extend(mutant.id for mutant in mutants)
                seen_ground_truth.append(ground_truth_executable)

            def run(self):
                return TestSuiteEvaluationResult(binary_results=[
                    BinaryTestSuiteResult(
                        binary_id="ground_truth", role="ground_truth",
                        test_results=[TestResult(name="test_ok", status="passed", extra={})],
                    ),
                    BinaryTestSuiteResult(
                        binary_id="m2", role="candidate",
                        test_results=[TestResult(name="test_ok", status="failure", extra={})],
                    ),
                ])

        monkeypatch.setattr(
            "programbench.eval.test_suite_eval_batch.TestSuiteEvaluator", FakeEvaluator,
        )
        monkeypatch.setattr(
            "programbench.eval.test_suite_eval_batch.load_mutant_suite",
            lambda _mutants_dir, _instance_id: (tmp_path, FakeMutantSuite()),
        )

        summary = _evaluate_instance(
            instance_id=instance_id, instance={"image_name": "programbench/example"},
            source_dir=source_dir, target_dir=target_dir, force=True,
            archive_name="tests.tar.gz", mutants_dir=tmp_path / "mutants",
            ground_truth_dir=tmp_path / "ground-truth",
            mutant_ids={"m1", "m2"},
            ignored_mutants={"m1"},
        )

        assert summary is not None
        assert seen_mutants == ["m2"]
        assert seen_ground_truth == [ground_truth]


def test_run_step_bounds_retained_log_output(tmp_path):
    output = "x" * (_MAX_RETAINED_LOG_TEXT_CHARS + 20)

    class FakeEnvironment:
        def execute(self, command, timeout):
            return {
                "output": output,
                "stdout": output,
                "stderr": output,
                "returncode": 0,
                "exception_info": "",
            }

    evaluator = TestSuiteEvaluator(image_name="image", test_suite_archive=tmp_path)
    retained_log = []

    returned = evaluator._run_step(
        "command",
        env=FakeEnvironment(),
        log_buf=retained_log,
        step_name="large_output",
    )

    assert returned["output"] == output
    assert retained_log[0]["output"].startswith("x" * 100)
    assert retained_log[0]["output"].endswith("x" * 100)
    assert "ProgramBench omitted 20 characters" in retained_log[0]["output"]
    assert "ProgramBench omitted 20 characters" in retained_log[0]["stdout"]
    assert "ProgramBench omitted 20 characters" in retained_log[0]["stderr"]


def test_copy_file_from_container_rejects_oversized_junit_before_reading(
    tmp_path, monkeypatch
):
    evaluator = TestSuiteEvaluator(image_name="image", test_suite_archive=tmp_path)

    class FakeEnvironment:
        executable = "docker"
        container_id = "container"

    def fake_run(args, **kwargs):
        Path(args[-1]).write_bytes(b"x" * 11)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    retained_log = []

    with pytest.raises(EvalStepError, match="results_too_large"):
        evaluator._copy_file_from_container(
            env=FakeEnvironment(),
            log_buf=retained_log,
            container_path="/workspace/eval/results.xml",
            step_name="results_read",
            max_bytes=10,
        )

    assert retained_log[0]["output"].endswith("the limit is 10 bytes")


def test_discovers_reference_support_executables_across_branches(tmp_path):
    instance_id = "example__tool.abc1234"
    first = tmp_path / instance_id / "branch-a"
    second = tmp_path / instance_id / "branch-b"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    helper = b"\x7fELFhelper"
    for path in (first / "helper", second / "helper"):
        path.write_bytes(helper)
        path.chmod(0o755)
    ignored_script = first / "tool.sh"
    ignored_script.write_text("#!/bin/sh\n")
    ignored_script.chmod(0o755)
    reserved = first / "executable"
    reserved.write_bytes(b"\x7fELFmain")
    reserved.chmod(0o755)

    discovered = discover_reference_support_executables(tmp_path, instance_id)

    assert discovered == (first / "helper",)


def test_rejects_conflicting_reference_support_executables(tmp_path):
    instance_id = "example__tool.abc1234"
    for branch, payload in (("branch-a", b"one"), ("branch-b", b"two")):
        path = tmp_path / instance_id / branch / "helper"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"\x7fELF" + payload)
        path.chmod(0o755)

    with pytest.raises(ValueError, match=r"Conflicting reference support executable 'helper'"):
        discover_reference_support_executables(tmp_path, instance_id)


def test_bounds_nested_retained_test_diagnostics():
    output = "x" * (_MAX_RETAINED_LOG_TEXT_CHARS + 20)

    bounded = _bounded_retained_value({"message": [output], "count": 1})

    assert bounded["message"][0].startswith("x" * 100)
    assert bounded["message"][0].endswith("x" * 100)
    assert "ProgramBench omitted 20 characters" in bounded["message"][0]
    assert bounded["count"] == 1


def test_junit_diagnostic_truncation_is_utf8_bounded_and_keeps_head_and_tail():
    value = "HEAD-" + ("λ" * 100) + "-TAIL"

    truncated = truncate_utf8(value, 96)

    assert len(truncated.encode("utf-8")) <= 96
    assert truncated.startswith("HEAD-")
    assert truncated.endswith("-TAIL")
    assert "ProgramBench truncated JUnit diagnostic" in truncated


def test_junit_diagnostic_tree_caps_only_diagnostic_fields():
    root = ET.fromstring(
        "<testsuite name='suite'><testcase name='test_name'>"
        "<failure message='message-message-message'>trace-trace-trace</failure>"
        "<system-out>output-output-output</system-out>"
        "</testcase></testsuite>"
    )

    changed = truncate_junit_diagnostics(root, 16)

    testcase = root.find("testcase")
    failure = testcase.find("failure")
    system_out = testcase.find("system-out")
    assert changed == 3
    assert testcase.attrib["name"] == "test_name"
    assert len(failure.attrib["message"].encode("utf-8")) <= 16
    assert len(failure.text.encode("utf-8")) <= 16
    assert len(system_out.text.encode("utf-8")) <= 16


def test_noop_junit_diagnostic_truncation_preserves_text():
    assert truncate_utf8("short diagnostic", 16) == "short diagnostic"


def test_retained_test_diagnostics_use_junit_cap():
    value = "a" * (MAX_JUNIT_DIAGNOSTIC_BYTES + 100)

    bounded = _bounded_test_diagnostic_value({"message": value, "nested": [value]})

    assert len(bounded["message"].encode("utf-8")) <= MAX_JUNIT_DIAGNOSTIC_BYTES
    assert len(bounded["nested"][0].encode("utf-8")) <= MAX_JUNIT_DIAGNOSTIC_BYTES
    assert bounded["message"].startswith("a" * 100)
    assert bounded["message"].endswith("a" * 100)


def test_write_eval_json_streams_valid_result(tmp_path, monkeypatch):
    result = TestSuiteEvaluationResult(
        binary_results=[
            BinaryTestSuiteResult(
                binary_id="ground_truth",
                test_results=[TestResult(name="test_one", status="passed", extra={})],
                log=[{"output": "diagnostic"}],
            )
        ],
        n_assertions=1,
    )
    eval_json = tmp_path / "result.test_eval.json"
    monkeypatch.setattr(
        TestSuiteEvaluationResult,
        "model_dump_json",
        lambda *args, **kwargs: pytest.fail("aggregate JSON serialization must not be used"),
    )

    _write_eval_json(eval_json, result)

    restored = TestSuiteEvaluationResult.model_validate_json(eval_json.read_text())
    assert restored == result
    assert not eval_json.with_suffix(".json.tmp").exists()


class TestLoadData:
    def test_load_all_instances(self):
        instances = load_all_instances()
        assert len(instances) >= 1
        ids = {inst["instance_id"] for inst in instances}
        assert "testorg__calculator.abc1234" in ids

    def test_get_active_branches(self):
        instances = load_all_instances()
        calc = next(i for i in instances if i["instance_id"] == "testorg__calculator.abc1234")
        assert get_active_branches(calc) == ["33128f6b8600"]

    def test_get_ignored_tests_empty(self):
        instances = load_all_instances()
        calc = next(i for i in instances if i["instance_id"] == "testorg__calculator.abc1234")
        assert get_ignored_tests(calc) == set()

    def test_task_dir_exists(self):
        assert (TASKS_DIR / "testorg__calculator.abc1234" / "task.yaml").exists()
        assert (TASKS_DIR / "testorg__calculator.abc1234" / "tests.json").exists()
        assert (TASKS_DIR / "testorg__calculator.abc1234" / "tests" / "33128f6b8600" / "eval" / "run.sh").exists()


class TestTestSuiteEvaluationResult:
    def test_ground_truth_passed_requires_ground_truth_binary(self):
        assert not TestSuiteEvaluationResult().ground_truth_passed

    def test_ground_truth_passed_requires_at_least_one_test(self):
        result = TestSuiteEvaluationResult(
            binary_results=[BinaryTestSuiteResult(binary_id="ground_truth", role="ground_truth")]
        )
        assert result.score == 0.0
        assert not result.ground_truth_passed

    def test_ground_truth_passed_when_all_generated_tests_pass(self):
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        TestResult(name="t1", branch="generated", status="passed", extra={}),
                        TestResult(name="t2", branch="generated", status="passed", extra={}),
                    ],
                )
            ]
        )
        assert result.score == 1.0
        assert result.ground_truth_passed

    def test_ground_truth_failed_when_any_generated_test_fails(self):
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        TestResult(name="t1", branch="generated", status="passed", extra={}),
                        TestResult(name="t2", branch="generated", status="failure", extra={}),
                    ],
                )
            ]
        )
        assert result.score == 0.5
        assert not result.ground_truth_passed


class TestEvaluatorWorkspaceCleanup:
    def test_evaluation_image_masks_codex_credentials(self, monkeypatch):
        captured = {}

        class FakeContainerEnvironment:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        monkeypatch.setattr("programbench.eval.eval.ContainerEnvironment", FakeContainerEnvironment)
        evaluator = Evaluator(
            tests_branches=[],
            image_name="programbench/example",
            image_tag="task",
            image="programbench/example:task_cleanroom_codex",
        )

        evaluator._new_env(evaluator.image)

        assert evaluator.image == "programbench/example:task_cleanroom_codex"
        assert captured["image"] == evaluator.image
        assert captured["env"]["OPENAI_API_KEY"] == ""
        assert captured["env"]["CODEX_HOME"] == "/root/.codex"
        assert "--tmpfs" in captured["run_args"]
        assert "/root/.codex:rw,noexec,nosuid,nodev,size=1m" in captured["run_args"]

    def test_removes_stale_dependency_dir_for_manifest_payload_without_that_dir(self, tmp_path):
        payload = tmp_path / "payload"
        payload.mkdir()
        (payload / "go.mod").write_text("module example\n")
        calls = []

        class FakeEnv:
            def execute(self, command, timeout=None):
                calls.append((command, timeout))
                return {"output": "", "stdout": "", "stderr": "", "returncode": 0, "exception_info": ""}

        log_buf = []
        evaluator = Evaluator(tests_branches=[])

        evaluator._clean_workspace_for_test_payload(payload, FakeEnv(), log_buf)

        assert calls == [("rm -rf vendor", 60)]
        assert log_buf[0]["step"] == "clean_stale_dependency_dirs"

    def test_keeps_dependency_dir_when_payload_includes_it(self, tmp_path):
        payload = tmp_path / "payload"
        payload.mkdir()
        (payload / "go.mod").write_text("module example\n")
        (payload / "vendor").mkdir()

        class FakeEnv:
            def execute(self, command, timeout=None):  # pragma: no cover - should not be called
                raise AssertionError(command)

        evaluator = Evaluator(tests_branches=[])
        evaluator._clean_workspace_for_test_payload(payload, FakeEnv(), [])

    def test_removes_stale_dependency_dir_for_tarred_manifest_payload(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "go.mod").write_text("module example\n")
        archive = tmp_path / "payload.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(source / "go.mod", arcname="./go.mod")
        calls = []

        class FakeEnv:
            def execute(self, command, timeout=None):
                calls.append((command, timeout))
                return {"output": "", "stdout": "", "stderr": "", "returncode": 0, "exception_info": ""}

        evaluator = Evaluator(tests_branches=[])
        evaluator._clean_workspace_for_test_payload(archive, FakeEnv(), [])

        assert calls == [("rm -rf vendor", 60)]

    def test_restores_candidate_go_module_files_when_payload_overlays_go_mod(self, tmp_path):
        payload = tmp_path / "payload"
        payload.mkdir()
        (payload / "go.mod").write_text("module tests\n")
        calls = []

        class FakeEnv:
            def execute(self, command, timeout=None):
                calls.append((command, timeout))
                return {"output": "", "stdout": "", "stderr": "", "returncode": 0, "exception_info": ""}

        evaluator = Evaluator(tests_branches=[])
        log_buf = []
        evaluator._restore_go_module_files_for_test_payload(payload, FakeEnv(), log_buf)

        assert len(calls) == 1
        command, timeout = calls[0]
        assert timeout == 60
        assert "cp /opt/programbench-stashed-go.mod ./go.mod" in command
        assert "cp /opt/programbench-stashed-go.sum ./go.sum" in command
        assert log_buf[0]["step"] == "restore_go_module_files"

    def test_skips_go_module_restore_when_payload_has_no_go_mod(self, tmp_path):
        payload = tmp_path / "payload"
        payload.mkdir()
        (payload / "eval").mkdir()

        class FakeEnv:
            def execute(self, command, timeout=None):  # pragma: no cover - should not be called
                raise AssertionError(command)

        evaluator = Evaluator(tests_branches=[])
        evaluator._restore_go_module_files_for_test_payload(payload, FakeEnv(), [])

    def test_stashes_overlaid_test_go_module_files_for_helper_builds(self, tmp_path):
        payload = tmp_path / "payload"
        payload.mkdir()
        (payload / "go.mod").write_text("module tests\n")
        calls = []

        class FakeEnv:
            def execute(self, command, timeout=None):
                calls.append((command, timeout))
                return {"output": "", "stdout": "", "stderr": "", "returncode": 0, "exception_info": ""}

        evaluator = Evaluator(tests_branches=[])
        log_buf = []
        evaluator._stash_test_go_module_files_for_test_payload(payload, FakeEnv(), log_buf)

        assert len(calls) == 1
        command, timeout = calls[0]
        assert timeout == 60
        assert "cp ./go.mod .programbench-test-go.mod" in command
        assert "cp ./go.sum .programbench-test-go.sum" in command
        assert log_buf[0]["step"] == "stash_test_go_module_files"

    def test_prepare_workspace_bin_links_root_executables(self):
        calls = []

        class FakeEnv:
            def execute(self, command, timeout=None):
                calls.append((command, timeout))
                return {"output": "", "stdout": "", "stderr": "", "returncode": 0, "exception_info": ""}

        evaluator = Evaluator(tests_branches=[])
        log_buf = []
        evaluator._prepare_workspace_bin(FakeEnv(), log_buf)

        command, timeout = calls[0]
        assert timeout == 60
        assert "mkdir -p .programbench-bin" in command
        assert "[ \"$name\" = compile.sh ] && continue" in command
        assert "ln -sf" in command
        assert "PROGRAMBENCH_GO_WRAPPER" in command
        assert "cp \"$prebuilt\"" in command
        assert ".programbench-test-go.mod" in command
        assert "candidate-go.mod" in command
        assert "exit $status" in command
        assert "cd /workspace" in command
        assert log_buf[0]["step"] == "prepare_workspace_bin"

    def test_stashes_compiled_cmd_auxiliary_executables(self):
        calls = []

        class FakeEnv:
            def execute(self, command, timeout=None):
                calls.append((command, timeout))
                return {"output": "", "stdout": "", "stderr": "", "returncode": 0, "exception_info": ""}

        evaluator = Evaluator(tests_branches=[])
        log_buf = []
        evaluator._stash_auxiliary_executables(FakeEnv(), log_buf)

        command, timeout = calls[0]
        assert timeout == 120
        assert "for f in ./cmd/*/*" in command
        assert '[ "$name" = "$parent" ] || continue' in command
        assert 'cp -f "$f" "/opt/programbench-stashed-aux-bin/$name"' in command
        assert log_buf[0]["step"] == "stash_auxiliary_executables"


class TestContainerEnvironment:
    def test_start_failure_removes_created_container_id(self, monkeypatch):
        calls = []

        def fake_run(cmd, capture_output, text, timeout):
            calls.append(cmd)
            if cmd[:2] == ["docker", "run"]:
                return subprocess.CompletedProcess(cmd, 125, stdout="created-id\n", stderr="quota exceeded")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr("programbench.container.subprocess.run", fake_run)

        with pytest.raises(RuntimeError, match="start container failed"):
            ContainerEnvironment(image="example:image", executable="docker")

        assert calls[1] == ["docker", "rm", "-f", "created-id"]

    def test_start_failure_retries_transient_keyring_error(self, monkeypatch):
        calls = []
        sleeps = []

        def fake_run(cmd, capture_output, text, timeout):
            calls.append(cmd)
            docker_run_count = sum(1 for call in calls if call[:2] == ["docker", "run"])
            if cmd[:2] == ["docker", "run"] and docker_run_count == 1:
                return subprocess.CompletedProcess(
                    cmd,
                    125,
                    stdout="failed-id\n",
                    stderr=(
                        "unable to join session keyring: unable to create session key: "
                        "disk quota exceeded"
                    ),
                )
            if cmd[:2] == ["docker", "run"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="ok-id\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setenv("PROGRAMBENCH_DOCKER_RUN_RETRIES", "1")
        monkeypatch.setenv("PROGRAMBENCH_DOCKER_RUN_RETRY_DELAY", "0.25")
        monkeypatch.setattr("programbench.container.subprocess.run", fake_run)
        monkeypatch.setattr("programbench.container.time.sleep", lambda delay: sleeps.append(delay))

        env = ContainerEnvironment(image="example:image", executable="docker")

        assert env.container_id == "ok-id"
        assert [call[:2] for call in calls].count(["docker", "run"]) == 2
        assert ["docker", "rm", "-f", "failed-id"] in calls
        assert sleeps == [0.25]

    def test_execute_preserves_stdout_and_stderr(self, monkeypatch):
        env = ContainerEnvironment.__new__(ContainerEnvironment)
        env.cwd = "/workspace"
        env.executable = "docker"
        env.container_id = "container-id"
        env.default_timeout = 30

        def fake_run(cmd, stdin, capture_output, text, timeout):
            assert stdin is subprocess.DEVNULL

            class Result:
                stdout = "out\n"
                stderr = "err\n"
                returncode = 7

            return Result()

        monkeypatch.setattr("programbench.container.subprocess.run", fake_run)

        result = env.execute("printf out; printf err >&2")

        assert result["stdout"] == "out\n"
        assert result["stderr"] == "err\n"
        assert result["output"] == "out\nerr\n"
        assert result["returncode"] == 7

    def test_execute_streams_stdout_and_stderr_lines(self, monkeypatch):
        env = ContainerEnvironment.__new__(ContainerEnvironment)
        env.cwd = "/workspace"
        env.executable = "docker"
        env.container_id = "container-id"
        env.default_timeout = 30
        events = []

        class FakeStream:
            def __init__(self, lines):
                self.lines = lines

            def __iter__(self):
                return iter(self.lines)

            def close(self):
                pass

        class FakeProcess:
            stdout = FakeStream(["out one\n", "out two\n"])
            stderr = FakeStream(["err one\n"])

            def wait(self, timeout=None):
                return 3

            def kill(self):
                pass

        monkeypatch.setattr("programbench.container.subprocess.Popen", lambda *args, **kwargs: FakeProcess())

        result = env.execute("command", output_callback=lambda stream, line: events.append((stream, line)))

        assert result["stdout"] == "out one\nout two\n"
        assert result["stderr"] == "err one\n"
        assert result["returncode"] == 3
        assert sorted(events) == sorted(
            [("stdout", "out one\n"), ("stdout", "out two\n"), ("stderr", "err one\n")]
        )

    def test_copy_in_streams_regular_file_without_docker_cp(self, tmp_path, monkeypatch):
        payload = tmp_path / "executable"
        payload.write_text("#!/bin/sh\n")
        env = ContainerEnvironment.__new__(ContainerEnvironment)
        env.executable = "docker"
        env.container_id = "container-id"
        calls = {}

        def fake_stream_tar_in(container_path, *, producer=None, stdin_stream=None, compressed=False):
            calls["stream"] = {
                "container_path": container_path,
                "producer": producer,
                "stdin_stream": stdin_stream,
                "compressed": compressed,
            }

        def fake_run(cmd, capture_output, text, timeout):
            calls["run_cmd"] = cmd

            class Result:
                returncode = 0
                stderr = ""

            return Result()

        monkeypatch.setattr(env, "_stream_tar_in", fake_stream_tar_in)
        monkeypatch.setattr("programbench.container.subprocess.run", fake_run)

        env.copy_in(payload, "/workspace/.programbench-mutant-executable")

        assert calls["stream"]["container_path"].startswith("/tmp/programbench-copy-")
        assert calls["stream"]["producer"] == ["tar", "--sparse", "-h", "-C", str(tmp_path), "-cf", "-", "--", "executable"]
        assert calls["run_cmd"][:5] == ["docker", "exec", "container-id", "bash", "-lc"]
        script = calls["run_cmd"][-1]
        assert "mv -f" in script
        assert "/workspace/.programbench-mutant-executable" in script


class TestCopyCleanroom:
    def test_extract_ignores_archived_owner(self, tmp_path, monkeypatch):
        src = tmp_path / "cleanroom"
        src.mkdir()
        (src / "README.md").write_text("docs")
        calls = {}

        class FakeConfig:
            executable = "docker"

        class FakeEnv:
            container_id = "container-id"
            config = FakeConfig()

            def execute(self, command):
                calls.setdefault("execute", []).append(command)
                return {"returncode": 0, "output": ""}

        class FakePipe:
            def close(self):
                calls["stdout_closed"] = True

        class FakeStderr:
            def read(self):
                return b""

        class FakePopen:
            stdout = FakePipe()
            stderr = FakeStderr()

            def wait(self):
                return 0

        def fake_popen(args, stdout, stderr):
            calls["popen_args"] = args
            return FakePopen()

        def fake_run(args, stdin, capture_output, text):
            calls["run_args"] = args
            calls["stdin"] = stdin

            class Result:
                returncode = 0
                stderr = b""

            return Result()

        monkeypatch.setattr("programbench.test_generation.subprocess.Popen", fake_popen)
        monkeypatch.setattr("programbench.test_generation.subprocess.run", fake_run)

        _copy_cleanroom(FakeEnv(), src)

        assert calls["popen_args"] == ["tar", "-C", str(src), "-cf", "-", "."]
        assert calls["run_args"] == [
            "docker",
            "exec",
            "-i",
            "container-id",
            "tar",
            "--no-same-owner",
            "-xf",
            "-",
            "-C",
            "/workspace",
        ]
        assert calls["stdin"] is FakePopen.stdout
        assert calls["stdout_closed"] is True

    def test_copy_temporarily_makes_execute_only_file_readable(self, tmp_path, monkeypatch):
        src = tmp_path / "cleanroom"
        src.mkdir()
        executable = src / "executable"
        executable.write_bytes(b"#!/bin/sh\n")
        executable.chmod(0o111)
        calls = {"execute": []}

        class FakeConfig:
            executable = "docker"

        class FakeEnv:
            container_id = "container-id"
            config = FakeConfig()

            def execute(self, command):
                calls["execute"].append(command)
                return {"returncode": 0, "output": ""}

        class FakePipe:
            def close(self):
                calls["stdout_closed"] = True

        class FakeStderr:
            def read(self):
                return b""

        class FakePopen:
            stdout = FakePipe()
            stderr = FakeStderr()

            def wait(self):
                return 0

        def fake_access(path, mode):
            return Path(path).name != "executable"

        def fake_popen(args, stdout, stderr):
            calls["mode_during_tar"] = executable.stat().st_mode & 0o777
            return FakePopen()

        def fake_run(args, stdin, capture_output, text):
            class Result:
                returncode = 0
                stderr = b""

            return Result()

        monkeypatch.setattr("programbench.test_generation.os.access", fake_access)
        monkeypatch.setattr("programbench.test_generation.subprocess.Popen", fake_popen)
        monkeypatch.setattr("programbench.test_generation.subprocess.run", fake_run)

        _copy_cleanroom(FakeEnv(), src)

        assert calls["mode_during_tar"] == 0o511
        assert executable.stat().st_mode & 0o777 == 0o111
        assert calls["execute"][-1] == {"command": "chmod 0111 /workspace/executable"}


class TestTestGenerationPrompts:
    def test_prompts_are_documentation_only_during_generation(self):
        system_template, instance_template = _build_agent_templates()
        prompt_text = system_template + instance_template
        assert system_template == ""
        assert "program specification" in prompt_text
        assert "documented functional behavior" in prompt_text
        assert "{generation_mode_guidance}" not in prompt_text
        assert "Run `./executable`" not in prompt_text
        assert "observed behavior" not in prompt_text

    def test_prompt_omits_evaluation_narration(self):
        prompt_text = "".join(_build_agent_templates())
        assert "During evaluation" not in prompt_text
        assert "will be scored later" not in prompt_text
        assert "when evaluation supplies it" not in prompt_text
        assert "run your tests against `./executable`" not in prompt_text

    def test_prompt_default_hides_generation_executable(self):
        prompt_text = "".join(_build_agent_templates())
        assert "program specification" in prompt_text
        assert "reference executable" not in prompt_text
        assert "You may run it" not in prompt_text

    def test_prompt_with_executable_adds_binary_guidance(self):
        prompt_text = "".join(_build_agent_templates(with_executable=True))
        assert "reference executable at `/workspace/executable`" in prompt_text
        assert "observed behavior" in prompt_text
        assert "source of truth" not in prompt_text
        assert "program specification and a reference executable" in prompt_text

    def test_prompt_modes_select_separate_instance_templates(self):
        _, spec_only = build_agent_templates(mode=GenerationPromptMode.SPEC_ONLY)
        _, spec_and_binary = build_agent_templates(mode=GenerationPromptMode.SPEC_AND_BINARY)
        assert "program specification" in spec_only
        assert "reference executable" not in spec_only
        assert "reference executable" in spec_and_binary
        assert "observed behavior" in spec_and_binary

    def test_semiformal_coverage_guidance_is_built_in(self):
        spec_only = _codex_test_generation_prompt()
        spec_and_binary = _codex_test_generation_prompt(with_executable=True)

        for prompt in (spec_only, spec_and_binary):
            assert "explicitly numbered or sectioned requirements" in prompt
            assert "each documented behavior with at least one meaningful test" in prompt
            assert "short, descriptive `ids=` values" in prompt
            assert "Never allow large strings, bytes, or object representations to become test IDs" in prompt
            assert "`<testsuites>` root" in prompt
            assert "one named `<testcase>` per test" in prompt
            assert "`<failure>`, `<error>`, or `<skipped>`" in prompt
            assert "`pytest --junitxml=results.xml`" in prompt

    def test_generation_observation_template_exposes_streams(self):
        assert _PROGRAMBENCH_STREAM_ENVIRONMENT_CLASS == "programbench.test_generation.StreamSeparatedDockerEnvironment"
        assert "<stdout>" in _STREAM_SEPARATED_OBSERVATION_TEMPLATE
        assert "<stderr>" in _STREAM_SEPARATED_OBSERVATION_TEMPLATE
        assert "<output>" in _STREAM_SEPARATED_OBSERVATION_TEMPLATE

    def test_normalize_agent_config_maps_legacy_time_limit(self):
        original = {"step_limit": 100, "time_limit": 1800}
        normalized = _normalize_agent_config(original)

        assert normalized == {"step_limit": 100, "wall_time_limit_seconds": 1800}
        assert original == {"step_limit": 100, "time_limit": 1800}

    def test_normalize_agent_config_keeps_explicit_wall_time_limit(self):
        normalized = _normalize_agent_config({"time_limit": 1800, "wall_time_limit_seconds": 120})

        assert normalized == {"wall_time_limit_seconds": 120}

    def test_soft_warning_agent_adds_step_warning_once(self):
        class Model:
            def format_message(self, role, content):
                return {"role": role, "content": content}

        class BaseAgent:
            def __init__(self, **kwargs):
                self.config = type("Config", (), {"step_limit": 100, "wall_time_limit_seconds": 0})()
                self.n_calls = 80
                self._start_time = 0
                self.model = Model()
                self.messages = []

            def add_messages(self, *messages):
                self.messages.extend(messages)
                return list(messages)

            def query(self):
                return {"role": "assistant"}

        class Agent(SoftWarningAgentMixin, BaseAgent):
            pass

        agent = Agent()
        agent.query()
        agent.query()

        warnings = [m for m in agent.messages if m["role"] == "user"]
        assert len(warnings) == 1
        assert warnings[0]["content"] == _SOFT_WARNING_MESSAGE

    def test_soft_warning_agent_adds_time_warning_once(self, monkeypatch):
        class Model:
            def format_message(self, role, content):
                return {"role": role, "content": content}

        class BaseAgent:
            def __init__(self, **kwargs):
                self.config = type("Config", (), {"step_limit": 0, "wall_time_limit_seconds": 1000})()
                self.n_calls = 0
                self._start_time = 0
                self.model = Model()
                self.messages = []

            def add_messages(self, *messages):
                self.messages.extend(messages)
                return list(messages)

            def query(self):
                return {"role": "assistant"}

        class Agent(SoftWarningAgentMixin, BaseAgent):
            pass

        monkeypatch.setattr("programbench.test_generation.time.time", lambda: 401)
        agent = Agent()
        agent.query()
        agent.query()

        warnings = [m for m in agent.messages if m["role"] == "user"]
        assert len(warnings) == 1
        assert warnings[0]["content"] == _SOFT_WARNING_MESSAGE

    def test_hide_executable_command_removes_generation_binary(self):
        assert "rm -f ./executable" in _HIDE_EXECUTABLE_COMMAND
        assert "test ! -e ./executable" in _HIDE_EXECUTABLE_COMMAND
        assert "use documentation only" in _HIDE_EXECUTABLE_COMMAND

    def test_hide_executable_raises_when_command_fails(self):
        class Env:
            def execute(self, command):
                self.command = command
                return {"returncode": 1, "output": "permission denied"}

        env = Env()
        with pytest.raises(RuntimeError, match="Failed to hide ./executable"):
            _hide_executable(env)
        assert env.command == {"command": _HIDE_EXECUTABLE_COMMAND}

    def test_ensure_workspace_python_command_installs_and_links_python(self):
        command = _ENSURE_WORKSPACE_PYTHON_COMMAND
        assert "apt-get install -y --no-install-recommends python3-minimal" in command
        assert 'ln -sf "$python_bin" /workspace/.programbench-bin/python3' in command
        assert 'ln -sf "$python_bin" /workspace/.programbench-bin/python' in command
        assert "python --version" in command
        assert "python3 --version" in command

    def test_ensure_workspace_python_runs_bootstrap_command(self):
        class Env:
            def execute(self, command):
                self.command = command
                return {"returncode": 0, "output": ""}

        env = Env()
        _ensure_workspace_python(env)
        assert env.command == {"command": _ENSURE_WORKSPACE_PYTHON_COMMAND}

    def test_ensure_workspace_python_raises_when_bootstrap_fails(self):
        class Env:
            def execute(self, command):
                self.command = command
                return {"returncode": 1, "output": "no interpreter"}

        env = Env()
        with pytest.raises(RuntimeError, match="Failed to make python/python3 available"):
            _ensure_workspace_python(env)
        assert env.command == {"command": _ENSURE_WORKSPACE_PYTHON_COMMAND}

    def test_ensure_workspace_path_prefers_programbench_bin(self):
        env_config = {}
        _ensure_workspace_path(env_config)
        assert env_config["env"]["PATH"] == _WORKSPACE_PATH
        assert env_config["env"]["PATH"].startswith("/workspace/.programbench-bin:")

    def test_ensure_workspace_path_preserves_custom_path(self):
        env_config = {"env": {"PATH": "/custom/bin"}}
        _ensure_workspace_path(env_config)
        assert env_config["env"]["PATH"] == "/custom/bin"

    def test_cleanroom_dir_defaults_to_task_cleanroom_image(self):
        instance = {"image_name": "programbench/example.abc1234"}
        assert _task_cleanroom_image(instance) == "programbench/example.abc1234:task_cleanroom"
        assert _cleanroom_base_image(instance) == "programbench/example.abc1234:task_cleanroom"
        assert _cleanroom_base_image(instance, "python:3.12-slim") == "python:3.12-slim"


class TestCodexTestGeneration:
    def test_codex_test_generation_command_uses_direct_prompt_by_default(self):
        command = _codex_test_generation_shell_command("codex exec --cd /workspace", model="gpt-test")

        assert "--dangerously-bypass-approvals-and-sandbox" in command
        assert "--json" in command
        assert "--model gpt-test" in command
        assert "/workspace/eval/run.sh" in command
        assert TEST_GENERATION_GOAL_COMMAND not in command

    def test_codex_test_generation_command_can_use_goal_command(self):
        command = _codex_test_generation_shell_command("codex exec --cd /workspace", model="gpt-test", use_goal=True)

        assert TEST_GENERATION_GOAL_COMMAND in command
        assert "codex-goal.md" in command
        assert "/workspace/eval/run.sh" not in command

    def test_codex_test_generation_command_adds_reasoning_effort(self):
        command = _codex_test_generation_shell_command(
            "codex exec --cd /workspace",
            model="gpt-test",
            reasoning_effort="high",
        )

        assert "--config model_reasoning_effort=high" in command

    def test_codex_test_generation_prompt_with_executable_mentions_reference_binary(self):
        prompt = _codex_test_generation_prompt(with_executable=True)

        assert "program specification and a reference executable" in prompt
        assert "observed" in prompt

    def test_copy_generation_cleanroom_excludes_hidden_artifacts_by_default(self, tmp_path):
        cleanroom = tmp_path / "cleanroom"
        cleanroom.mkdir()
        (cleanroom / "README.md").write_text("spec")
        (cleanroom / "executable").write_text("binary")
        (cleanroom / ".programbench-ground-truth").write_text("secret")
        (cleanroom / ".git").mkdir()
        (cleanroom / ".git" / "HEAD").write_text("ref")
        copied = {}

        class Env:
            def execute(self, command):
                return {"returncode": 0, "output": ""}

            def copy_in(self, local_path, container_path):
                copied["container_path"] = container_path
                copied["files"] = sorted(
                    path.relative_to(local_path).as_posix()
                    for path in local_path.rglob("*")
                    if path.is_file()
                )

        _copy_generation_cleanroom_to_container(Env(), cleanroom)

        assert copied == {"container_path": "/workspace", "files": ["README.md"]}

    def test_copy_generation_cleanroom_can_include_executable(self, tmp_path):
        cleanroom = tmp_path / "cleanroom"
        cleanroom.mkdir()
        (cleanroom / "README.md").write_text("spec")
        (cleanroom / "executable").write_text("binary")
        copied = {}

        class Env:
            def execute(self, command):
                return {"returncode": 0, "output": ""}

            def copy_in(self, local_path, container_path):
                copied["files"] = sorted(
                    path.relative_to(local_path).as_posix()
                    for path in local_path.rglob("*")
                    if path.is_file()
                )

        _copy_generation_cleanroom_to_container(Env(), cleanroom, with_executable=True)

        assert copied["files"] == ["README.md", "executable"]

    def test_generate_tests_instance_runs_codex_and_writes_archive(self, tmp_path, monkeypatch, caplog):
        instance_id = "example__tool.1234567"
        cleanroom = tmp_path / "cleanroom" / instance_id
        cleanroom.mkdir(parents=True)
        (cleanroom / "README.md").write_text("spec")
        envs = []

        class Env:
            executable = "docker"
            container_id = "container"

            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.commands = []
                self.copied = []
                self.cleaned = False
                envs.append(self)

            def execute(self, command, *, timeout=None, output_callback=None):
                self.commands.append(command)
                if output_callback is not None:
                    line = "{\"type\":\"item.completed\",\"item\":{\"id\":\"item_1\",\"type\":\"agent_message\",\"text\":\"done\"}}\n"
                    command_line = "{\"type\":\"item.completed\",\"item\":{\"id\":\"item_2\",\"type\":\"command_execution\",\"command\":\"echo hi\",\"aggregated_output\":\"hi\\n\",\"exit_code\":0,\"status\":\"completed\"}}\n"
                    output_callback("stdout", line)
                    output_callback("stdout", command_line)
                    stdout = line + command_line
                    return {"returncode": 0, "stdout": stdout, "stderr": "", "output": stdout, "exception_info": ""}
                return {"returncode": 0, "stdout": "", "stderr": "", "output": "", "exception_info": ""}

            def copy_in(self, local_path, container_path):
                self.copied.append(container_path)

            def cleanup(self):
                self.cleaned = True

        def fake_copy_test_suite(env, dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("archive")

        monkeypatch.setattr("programbench.test_generation.ContainerEnvironment", Env)
        monkeypatch.setattr("programbench.test_generation._copy_test_suite", fake_copy_test_suite)
        caplog.set_level(logging.INFO, logger="programbench.test_generation")

        result = generate_tests_instance(
            instance={"instance_id": instance_id, "image_name": "programbench/example"},
            output=tmp_path / "out",
            cleanroom_dir=tmp_path / "cleanroom",
            image="codex-image",
            codex_command="codex exec --cd /workspace",
            codex_auth_file=None,
            codex_log_dir=tmp_path / "logs",
            progress_log_interval=0,
            use_goal=True,
        )

        assert result["status"] == "ok"
        assert result["output"] == str(tmp_path / "out" / instance_id / "tests.tar.gz")
        codex_events = [json.loads(line) for line in Path(result["codex_log"]).read_text().splitlines()]
        assert [event["item"]["type"] for event in codex_events] == ["agent_message", "command_execution"]
        assert (tmp_path / "out" / instance_id / "tests.tar.gz").read_text() == "archive"
        assert result["traj"] == str(tmp_path / "out" / instance_id / f"{instance_id}.traj.json")
        trajectory = json.loads(Path(result["traj"]).read_text())
        assert trajectory["info"]["exit_status"] == "ok"
        assert trajectory["info"]["codex_log"] == result["codex_log"]
        assert trajectory["info"]["use_goal"] is True
        assert trajectory["instance_id"] == instance_id
        assert trajectory["codex_events"] == codex_events
        assert [message["role"] for message in trajectory["messages"]] == ["user", "assistant", "assistant", "tool"]
        assert trajectory["messages"][1]["content"] == "done"
        assert trajectory["messages"][2]["tool_calls"][0]["function"]["name"] == "bash"
        assert "<returncode>0</returncode>" in trajectory["messages"][3]["content"]
        assert envs[0].kwargs["image"] == "codex-image"
        assert envs[0].kwargs["env"]["PATH"].startswith("/workspace/.programbench-bin:")
        assert envs[0].cleaned
        assert "/workspace" in envs[0].copied
        assert "Finished Codex session with status 0" in caplog.messages
        assert "/workspace/codex-goal.md" in envs[0].copied
        assert any(TEST_GENERATION_GOAL_COMMAND in command for command in envs[0].commands)

    def test_copy_test_suite_runs_and_validates_fresh_junit_before_archiving(
        self, tmp_path, monkeypatch
    ):
        commands = []

        class Env:
            executable = "docker"
            container_id = "container"

            def execute(self, command):
                command = command["command"] if isinstance(command, dict) else command
                commands.append(command)
                if "./run.sh" in command:
                    return {"returncode": 1, "output": "expected test failures"}
                if "python3 -c" in command:
                    return {"returncode": 0, "output": "12\n"}
                return {"returncode": 0, "output": ""}

        copied = {}

        def fake_run(args, **kwargs):
            copied["args"] = args
            with tarfile.open(args[-1], "w:gz") as archive:
                eval_dir = tmp_path / "generated" / "eval"
                eval_dir.mkdir(parents=True)
                (eval_dir / "run.sh").write_text("#!/bin/sh\n")
                archive.add(eval_dir, arcname="eval")
            return subprocess.CompletedProcess(args, 0, "", "")

        monkeypatch.setattr(subprocess, "run", fake_run)
        _copy_test_suite(Env(), tmp_path / "tests.tar.gz")

        assert "rm -f results.xml && ./run.sh" in commands[1]
        assert "python3 -c" in commands[2]
        assert str(MAX_JUNIT_XML_BYTES) in commands[2]
        assert "find . -type l -lname '/*' -delete" in commands[3]
        assert commands[4].startswith("bash -c")
        assert "1000000000" in commands[4]
        assert "--sparse" not in commands[4]
        assert all(f"--exclude={name}" in commands[4] for name in ARCHIVE_EXCLUDED_DIRS)
        assert copied["args"][:3] == [
            "docker",
            "cp",
            "container:/tmp/_programbench_tests.tar.gz",
        ]
        assert (tmp_path / "tests_untar" / "eval" / "run.sh").is_file()

    def test_copy_test_suite_rejects_missing_or_invalid_junit(self, tmp_path):
        commands = []

        class Env:
            executable = "docker"
            container_id = "container"

            def execute(self, command):
                command = command["command"] if isinstance(command, dict) else command
                commands.append(command)
                if "python3 -c" in command:
                    return {"returncode": 1, "output": "ParseError"}
                return {"returncode": 0, "output": ""}

        with pytest.raises(RuntimeError, match="valid JUnit XML"):
            _copy_test_suite(Env(), tmp_path / "tests.tar.gz")

        assert not any(command.startswith("tar -czf") for command in commands)


class TestContainerStartup:
    def test_container_start_clears_image_entrypoint(self, monkeypatch):
        calls = []

        def fake_run(cmd, capture_output, timeout, text=False):
            calls.append(cmd)

            class Result:
                returncode = 0
                stdout = "container-id\n"
                stderr = ""

            return Result()

        monkeypatch.setattr("programbench.container.subprocess.run", fake_run)

        env = ContainerEnvironment(image="example:image", executable="docker")
        env.cleanup()

        run_cmd = calls[0]
        entrypoint_index = run_cmd.index("--entrypoint")
        assert run_cmd[entrypoint_index + 1] == ""
        assert run_cmd[-3:] == ["example:image", "sleep", "infinity"]


class TestSpecImprovement:
    def test_default_codex_command_uses_the_preinstalled_binary(self):
        """Every image ProgramBench builds pins codex, so the default must not npx.

        Fetching the agent from npmjs.org at runtime fails behind an API-only
        egress allowlist, and leaves the agent version unpinned besides.
        """
        assert DEFAULT_CODEX_COMMAND.startswith(
            "codex --dangerously-bypass-approvals-and-sandbox exec "
        )

    def test_npx_command_remains_for_the_stock_image(self):
        """ghcr.io/openai/codex-universal ships no codex CLI and still needs npx."""
        from programbench.spec_improvement import NPX_CODEX_COMMAND

        assert NPX_CODEX_COMMAND.startswith("npx -y @openai/codex@0.158.0 ")

    def test_codex_command_forces_yolo_before_exec(self):
        command = _codex_shell_command("npx -y @openai/codex exec --cd /workspace")

        assert command.startswith(
            "npx -y @openai/codex --dangerously-bypass-approvals-and-sandbox exec --cd /workspace "
        )

    def test_copy_codex_auth_to_container(self, tmp_path):
        auth_file = tmp_path / "auth.json"
        auth_file.write_text('{"auth_mode":"chatgpt"}')
        calls = []

        class Env:
            def copy_in(self, local_path, container_path):
                calls.append((local_path, container_path))

        _copy_codex_auth_to_container(Env(), auth_file)

        assert calls == [(auth_file, "/root/.codex/auth.json")]

    def test_stream_codex_json_log_is_visible_before_completion(self, tmp_path, caplog):
        log_path = tmp_path / "instance.codex.jsonl"
        caplog.set_level(logging.INFO, logger="programbench.spec_improvement")

        item_completed = '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n'
        turn_completed = '{"type":"turn.completed"}\n'
        with _stream_codex_json_log("example", log_path) as callback:
            callback("stdout", '{"type":"item.started","item":{"type":"agent_message"}}\n')
            assert log_path.read_text() == ""
            callback("stdout", item_completed)
            assert log_path.read_text() == item_completed
            callback("stdout", turn_completed)
            assert log_path.read_text() == item_completed + turn_completed

        messages = [record.getMessage() for record in caplog.records]
        assert "example: Codex item.completed: agent_message - done" in messages
        assert "example: Codex turn.completed" in messages

    def test_codex_command_appends_model_and_prompt(self):
        command = _codex_shell_command("codex exec --cd /workspace", model="gpt-5")

        assert command.startswith(
            "codex --dangerously-bypass-approvals-and-sandbox exec --cd /workspace --model gpt-5 "
        )
        assert "You are given two directories" in command
        assert "specification/" in command
        assert "test-branches/" in command
        assert "--json" in command

    def test_codex_command_appends_reasoning_effort(self):
        command = _codex_shell_command("codex exec --cd /workspace", reasoning_effort="medium")

        assert "--config model_reasoning_effort=medium" in command

    @pytest.mark.parametrize("flag", ["-h", "--help", "-V", "--version"])
    def test_codex_command_rejects_diagnostic_commands(self, flag):
        with pytest.raises(RuntimeError, match="must run an agent command"):
            _codex_shell_command(f"npx -y @openai/codex {flag}")

    def test_prepare_workspace_copies_spec_and_tests_then_removes_non_spec_artifacts(self, tmp_path):
        spec = tmp_path / "spec"
        tests = tmp_path / "tests"
        spec.mkdir()
        tests.mkdir()
        branch = tests / "branch-a"
        (branch / "eval").mkdir(parents=True)
        (branch / "eval" / "run.sh").write_text("pytest")
        (branch / "data").mkdir()
        (branch / "data" / "fixture.txt").write_text("fixture")
        (branch / "summary.txt").write_text("summary")
        (branch / "cmatrix.c").write_text("source checkout")
        (spec / "README.md").write_text("spec")
        (spec / ".git").mkdir()
        (spec / ".git" / "HEAD").write_text("ref: main")
        (spec / "executable").write_text("binary")
        (spec / ".programbench-ground-truth").write_text("hidden")
        calls = []

        class Env:
            def execute(self, command):
                calls.append(("execute", command))
                return {"returncode": 0, "output": ""}

            def copy_in(self, local_path, container_path):
                if container_path == "/workspace/specification":
                    calls.append(("copy_in", sorted(path.name for path in local_path.iterdir()), container_path))
                elif container_path == "/workspace/test-branches":
                    files = sorted(
                        str(path.relative_to(local_path)) for path in local_path.rglob("*") if path.is_file()
                    )
                    calls.append(("copy_in", files, container_path))
                else:
                    calls.append(("copy_in", local_path, container_path))

        _prepare_workspace(Env(), specification=spec, test_branches=tests)

        assert calls[0] == (
            "execute",
            "rm -rf /workspace/specification /workspace/test-branches && mkdir -p /workspace",
        )
        assert calls[1] == ("copy_in", ["README.md"], "/workspace/specification")
        assert calls[2] == (
            "copy_in",
            ["branch-a/data/fixture.txt", "branch-a/eval/run.sh", "branch-a/summary.txt"],
            "/workspace/test-branches",
        )
        assert calls[3][0] == "execute"
        assert "/workspace/specification/.git" in calls[3][1]
        assert "/workspace/specification/executable" in calls[3][1]

    def test_improve_specification_skips_existing_output_without_container(self, tmp_path, monkeypatch):
        instance_id = "example__tool.1234567"
        (tmp_path / "out" / instance_id).mkdir(parents=True)

        def fail_container(*args, **kwargs):
            raise AssertionError("container should not be started")

        monkeypatch.setattr("programbench.spec_improvement.ContainerEnvironment", fail_container)

        result = improve_specification_instance(
            instance={"instance_id": instance_id, "image_name": "programbench/example"},
            testdir=tmp_path / "tests",
            spec_in=tmp_path / "specs",
            spec_out=tmp_path / "out",
            codex_log_dir=tmp_path / "logs",
        )

        assert result == {
            "instance_id": instance_id,
            "status": "skipped",
            "reason": "spec_out_exists",
            "spec_out": str(tmp_path / "out" / instance_id),
            "traj": None,
        }
        assert "spec.md" in specification_prompt()
        assert "## Spec ${i}" in specification_prompt()

    def test_improve_specification_logs_progress_phases(self, tmp_path, monkeypatch, caplog):
        instance_id = "example__tool.1234567"
        (tmp_path / "specs" / instance_id).mkdir(parents=True)
        (tmp_path / "tests" / instance_id).mkdir(parents=True)

        class Env:
            executable = "docker"
            container_id = "container"

            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def execute(self, command, *, timeout=None, output_callback=None):
                result = {
                    "returncode": 0,
                    "output": '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n',
                    "stdout": '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n',
                    "exception_info": "",
                }
                if output_callback is not None:
                    output_callback("stdout", result["stdout"])
                return result

            def copy_in(self, local_path, container_path):
                pass

            def cleanup(self):
                pass

        def fake_copy_out(env, container_path, local_path):
            local_path.mkdir(parents=True)
            (local_path / "spec.md").write_text("improved")

        monkeypatch.setattr("programbench.spec_improvement.ContainerEnvironment", Env)
        monkeypatch.setattr("programbench.spec_improvement._copy_dir_from_container", fake_copy_out)
        caplog.set_level(logging.INFO, logger="programbench.spec_improvement")

        result = improve_specification_instance(
            instance={"instance_id": instance_id, "image_name": "programbench/example"},
            testdir=tmp_path / "tests",
            spec_in=tmp_path / "specs",
            spec_out=tmp_path / "out",
            progress_log_interval=0,
            codex_log_dir=tmp_path / "logs",
        )

        assert result["status"] == "ok"
        assert result["spec_out"] == str(tmp_path / "out" / instance_id)
        assert result["traj"] == str(tmp_path / "logs" / f"{instance_id}.traj.json")
        trajectory = json.loads(Path(result["traj"]).read_text())
        assert trajectory["info"]["task"] == "improve-spec"
        assert trajectory["info"]["exit_status"] == "ok"
        assert trajectory["messages"][1]["content"] == "done"
        assert trajectory["codex_output"]["stdout"] == '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n'
        assert trajectory["codex_json_events"][0]["item"]["text"] == "done"
        messages = [record.getMessage() for record in caplog.records]
        assert f"{instance_id}: start container started" in messages
        assert f"{instance_id}: prepare workspace started" in messages
        assert f"{instance_id}: run Codex started" in messages
        assert any(
            message.startswith(f"{instance_id}: copy improved specification finished in ") for message in messages
        )

    def test_improve_specification_semiformal_outputs_only_spec_md(self, tmp_path, monkeypatch):
        instance_id = "example__tool.1234567"
        source_spec = tmp_path / "specs" / instance_id
        source_spec.mkdir(parents=True)
        (source_spec / "spec.md").write_text("original")
        (tmp_path / "tests" / instance_id).mkdir(parents=True)

        class Env:
            executable = "docker"
            container_id = "container"

            def __init__(self, **kwargs):
                pass

            def execute(self, command, *, timeout=None, output_callback=None):
                result = {
                    "returncode": 0,
                    "output": "{\"type\":\"turn.completed\"}\n",
                    "stdout": "{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"done\"}}\n",
                    "exception_info": "",
                }
                if output_callback is not None:
                    output_callback("stdout", result["stdout"])
                return result

            def copy_in(self, local_path, container_path):
                pass

            def cleanup(self):
                pass

        def fake_copy_out(env, container_path, local_path):
            local_path.mkdir(parents=True)
            (local_path / "spec.md").write_text("## Spec 1\nimproved\n")
            (local_path / "README.md").write_text("leak")
            (local_path / "docs").mkdir()
            (local_path / "docs" / "details.md").write_text("leak")

        monkeypatch.setattr("programbench.spec_improvement.ContainerEnvironment", Env)
        monkeypatch.setattr("programbench.spec_improvement._copy_dir_from_container", fake_copy_out)

        result = improve_specification_instance(
            instance={"instance_id": instance_id, "image_name": "programbench/example"},
            testdir=tmp_path / "tests",
            spec_in=tmp_path / "specs",
            spec_out=tmp_path / "out",
            progress_log_interval=0,
            codex_log_dir=tmp_path / "logs",
        )

        target_spec = tmp_path / "out" / instance_id
        assert result["status"] == "ok"
        output_files = sorted(
            path.relative_to(target_spec).as_posix() for path in target_spec.rglob("*") if path.is_file()
        )
        assert output_files == ["spec.md"]
        assert (target_spec / "spec.md").read_text() == "## Spec 1\nimproved\n"

    def test_improve_specification_writes_trajectory_when_codex_fails(self, tmp_path, monkeypatch):
        instance_id = "example__tool.1234567"
        (tmp_path / "specs" / instance_id).mkdir(parents=True)
        (tmp_path / "tests" / instance_id).mkdir(parents=True)

        class Env:
            executable = "docker"
            container_id = "container"

            def __init__(self, **kwargs):
                pass

            def execute(self, command, *, timeout=None, output_callback=None):
                if "codex" in command:
                    result = {
                        "returncode": 1,
                        "output": '{"type":"item.completed","item":{"type":"error","text":"failed"}}\n',
                        "stdout": '{"type":"item.completed","item":{"type":"error","text":"failed"}}\n',
                        "exception_info": "",
                    }
                    if output_callback is not None:
                        output_callback("stdout", result["stdout"])
                    return result
                return {"returncode": 0, "output": "", "stdout": "", "exception_info": ""}

            def copy_in(self, local_path, container_path):
                pass

            def cleanup(self):
                pass

        monkeypatch.setattr("programbench.spec_improvement.ContainerEnvironment", Env)

        result = improve_specification_instance(
            instance={"instance_id": instance_id, "image_name": "programbench/example"},
            testdir=tmp_path / "tests",
            spec_in=tmp_path / "specs",
            spec_out=tmp_path / "out",
            progress_log_interval=0,
            codex_log_dir=tmp_path / "logs",
        )

        assert result["status"] == "codex_failed"
        trajectory = json.loads(Path(result["traj"]).read_text())
        assert trajectory["info"]["exit_status"] == "codex_failed"
        assert trajectory["messages"][1]["content"] == "failed"
        assert trajectory["codex_output"]["stdout"] == '{"type":"item.completed","item":{"type":"error","text":"failed"}}\n'

    def test_improve_specification_rejects_successful_no_op(self, tmp_path, monkeypatch):
        instance_id = "example__tool.1234567"
        source_spec = tmp_path / "specs" / instance_id
        source_spec.mkdir(parents=True)
        (source_spec / "spec.md").write_text("original")
        (tmp_path / "tests" / instance_id).mkdir(parents=True)
        existing_target = tmp_path / "out" / instance_id
        existing_target.mkdir(parents=True)
        (existing_target / "spec.md").write_text("previous output")

        class Env:
            executable = "docker"
            container_id = "container"

            def __init__(self, **kwargs):
                pass

            def execute(self, command, *, timeout=None, output_callback=None):
                result = {
                    "returncode": 0,
                    "output": '{"type":"turn.completed"}\nCodex help',
                    "stdout": '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n',
                    "exception_info": "",
                }
                if output_callback is not None:
                    output_callback("stdout", result["stdout"])
                return result

            def copy_in(self, local_path, container_path):
                pass

            def cleanup(self):
                pass

        def fake_copy_out(env, container_path, local_path):
            local_path.mkdir(parents=True)
            (local_path / "spec.md").write_text("original")

        monkeypatch.setattr("programbench.spec_improvement.ContainerEnvironment", Env)
        monkeypatch.setattr("programbench.spec_improvement._copy_dir_from_container", fake_copy_out)

        result = improve_specification_instance(
            instance={"instance_id": instance_id, "image_name": "programbench/example"},
            testdir=tmp_path / "tests",
            spec_in=tmp_path / "specs",
            spec_out=tmp_path / "out",
            force=True,
            progress_log_interval=0,
            codex_log_dir=tmp_path / "logs",
        )

        assert result["status"] == "no_changes"
        assert result["output"] == '{"type":"turn.completed"}\nCodex help'
        assert (existing_target / "spec.md").read_text() == "previous output"
        trajectory = json.loads(Path(result["traj"]).read_text())
        assert trajectory["info"]["exit_status"] == "no_changes"
        assert trajectory["codex_output"]["stdout"] == '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n'


class TestMutantPipeline:
    def test_copy_repo_to_container_excludes_eval_directories_and_precompiled_executables(self, tmp_path):
        branch = tmp_path / "branch-a"
        (branch / "src").mkdir(parents=True)
        (branch / "src" / "main.c").write_text("int main(void) { return 0; }\n")
        (branch / "eval").mkdir()
        (branch / "eval" / "run.sh").write_text("pytest\n")
        (branch / "fixtures" / "eval").mkdir(parents=True)
        (branch / "fixtures" / "eval" / "ignored.txt").write_text("ignored\n")
        (branch / "fixtures" / "executable_cov").write_text("fixture\n")
        (branch / "build.sh").write_text("cc src/main.c -o executable\n")
        (branch / "executable_cov").write_text("coverage binary\n")
        (branch / "executable_nocov").write_text("non-coverage binary\n")
        (branch / "executable").symlink_to("executable_cov")
        copied = {}

        class Env:
            def copy_in(self, local_path, container_path):
                copied["container_path"] = container_path
                copied["files"] = sorted(
                    path.relative_to(local_path).as_posix() for path in local_path.rglob("*") if path.is_file()
                )

        _copy_repo_to_container(Env(), branch, [])

        assert copied["container_path"] == "/workspace/repo"
        assert copied["files"] == ["build.sh", "fixtures/executable_cov", "src/main.c"]

    def test_mutant_codex_command_uses_goal_command(self):
        command = _mutant_codex_shell_command("codex exec --cd /workspace", model="gpt-test", reasoning_effort="low")

        assert "--dangerously-bypass-approvals-and-sandbox" in command
        assert "--json" in command
        assert "--model gpt-test" in command
        assert "--config model_reasoning_effort=low" in command
        assert MUTANT_GENERATION_GOAL_COMMAND in command
        assert "exactly the mutant assignments" in command
        assert "codex-goal.md" in command
        assert MUTANT_GENERATION_PROMPT not in command

    def test_mutant_codex_resume_command_keeps_thread(self):
        command = _mutant_codex_resume_shell_command(
            "codex exec --cd /workspace", session_id="thread-123", prompt="repair from report"
        )

        assert "exec resume" in command
        assert "--cd" not in command
        assert "thread-123" in command
        assert "repair from report" in command
        assert "--json" in command

    def test_failed_controlled_build_resumes_same_codex_session(self, monkeypatch):
        reports = iter([
            {"attempt": 0, "returncode": 1, "log": "compile error"},
            {"attempt": 1, "returncode": 0, "log": "ok"},
        ])
        monkeypatch.setattr(
            "programbench.mutants._compile_mutant_repositories_in_live_container",
            lambda *args, **kwargs: next(reports),
        )


        @contextmanager
        def fake_collect(_instance_id):
            yield {
                "callback": lambda *_args: None,
                "completed_events": [],
                "json_events": [],
                "stdout_lines": [],
                "stderr_lines": [],
            }

        monkeypatch.setattr("programbench.mutants._collect_codex_json_events", fake_collect)

        class Env:
            def __init__(self):
                self.commands = []

            def execute(self, command, **_kwargs):
                self.commands.append(command)
                return {"returncode": 0, "stdout": "", "stderr": "", "output": ""}

        env = Env()
        json_events = [{"type": "thread.started", "thread_id": "thread-123"}]
        build_reports, session_id, failure = _repair_mutant_builds(
            env, instance_id="example", repo_names=["repo_1"], build_jobs=1, build_cpus=4,
            max_repairs=2, timeout=60, codex_command="codex exec --cd /workspace",
            model="", reasoning_effort="", json_events=json_events, events=[],
        )

        assert failure is None
        assert session_id == "thread-123"
        assert len(build_reports) == 2
        assert len(env.commands) == 1
        assert "exec resume" in env.commands[0]
        assert "thread-123" in env.commands[0]

    def test_mutant_generation_prompt_bans_executable_wrappers(self):
        assert "Do not create wrapper/proxy executables" in MUTANT_GENERATION_PROMPT
        assert "/workspace/executable" in MUTANT_GENERATION_PROMPT
        assert "self-contained outputs of their repository build" in MUTANT_GENERATION_PROMPT
        assert "singleton kill set" in MUTANT_GENERATION_PROMPT
        assert "mutant_plan.json" in MUTANT_GENERATION_PROMPT
        assert "/workspace/mutants.json" in MUTANT_GENERATION_PROMPT
        assert "pre-seeded" in MUTANT_GENERATION_PROMPT
        assert "edit `/workspace/mutants.json`" in MUTANT_GENERATION_PROMPT
        assert "write `/workspace/mutants.json`" not in MUTANT_GENERATION_PROMPT
        assert "`target_test_description`" in MUTANT_GENERATION_PROMPT
        assert "exactly as seeded" in MUTANT_GENERATION_PROMPT
        assert "`target_spec`" in MUTANT_GENERATION_PROMPT
        assert "`mutation`" in MUTANT_GENERATION_PROMPT
        assert "The script will compile" in MUTANT_GENERATION_PROMPT
        assert "Do not compile or run the mutants yourself" in MUTANT_GENERATION_PROMPT

    def test_validate_mutant_repositories_rejects_workspace_executable_proxy(self, tmp_path):
        instance_root = tmp_path / "example__tool.1234567"
        bad = instance_root / "repo_1"
        good = instance_root / "repo_2"
        bad.mkdir(parents=True)
        good.mkdir(parents=True)
        (bad / "build.sh").write_text("#!/usr/bin/env bash\ncp /workspace/executable executable\n")
        (bad / "executable").write_text("#!/usr/bin/env bash\nBASE_EXECUTABLE=/workspace/executable\nexec \"\" \"\"\n")
        (good / "build.sh").write_text("#!/usr/bin/env bash\ncc src/main.c -o executable\n")
        (good / "executable").write_text("binary bytes are fine\n")

        invalid = _validate_mutant_repositories(instance_root, ["repo_1", "repo_2"])

        assert set(invalid) == {"repo_1"}
        assert any("/workspace/executable" in violation for violation in invalid["repo_1"])

    def test_generated_paths_are_withheld_from_the_agent_and_restored_before_building(self, tmp_path):
        branch = tmp_path / "branch"
        (branch / "src").mkdir(parents=True)
        (branch / "src/shell.c.in").write_text("real build input\n")
        (branch / "shell.c").write_text("generated from shell.c.in\n")
        (branch / "Makefile.in").write_text("template\n")
        (branch / "executable").write_text("ground-truth binary\n")
        generated = ["shell.c", "config.log", "executable"]

        staged = {}

        class Env:
            def copy_in(self, local_path, container_path):
                staged[container_path] = sorted(
                    path.relative_to(local_path).as_posix()
                    for path in Path(local_path).rglob("*")
                    if path.is_file()
                )

        _copy_repo_to_container(Env(), branch, generated)

        # The agent cannot mutate what it cannot see, so it must reach src/shell.c.in.
        assert staged["/workspace/repo"] == ["Makefile.in", "src/shell.c.in"]

        target_root = tmp_path / "mutants"
        for repo_name in ["repo_1", "repo_2"]:
            (target_root / repo_name / "src").mkdir(parents=True)
            (target_root / repo_name / "src/shell.c.in").write_text("mutated build input\n")

        _restore_generated_files(
            target_root, ["repo_1", "repo_2"], branch=branch, generated_files=generated,
        )

        # Restored so each mutant compiles from a complete tree; absent paths stay absent.
        assert (target_root / "repo_1/shell.c").read_text() == "generated from shell.c.in\n"
        assert (target_root / "repo_2/shell.c").read_text() == "generated from shell.c.in\n"
        assert not (target_root / "repo_1/config.log").exists()
        # Never hand a mutant the ground-truth binary it is supposed to build.
        assert not (target_root / "repo_1/executable").exists()
        assert (target_root / "repo_1/src/shell.c.in").read_text() == "mutated build input\n"

    def test_no_op_build_repositories_flags_mutations_that_never_reached_the_binary(self, tmp_path):
        instance_root = tmp_path / "example__tool.1234567"
        for repo_name, executable in [
            ("repo_1", "generated shell.c was rebuilt"),
            ("repo_2", "generated shell.c was rebuilt"),
            ("repo_3", "a real source edit reached the binary"),
        ]:
            repo = instance_root / repo_name
            repo.mkdir(parents=True)
            (repo / "build.sh").write_text("#!/usr/bin/env bash\ncc src/main.c -o executable\n")
            (repo / "executable").write_text(executable)

        assert _no_op_build_repositories(instance_root, ["repo_1", "repo_2", "repo_3"]) == {
            "repo_1", "repo_2",
        }
        # Reported to the build-repair loop, not as a terminal policy violation.
        assert _validate_mutant_repositories(instance_root, ["repo_1", "repo_2", "repo_3"]) == {}

    def test_load_mutant_suite_discovers_generated_repo_executables(self, tmp_path):
        instance_id = "example__tool.1234567"
        instance_root = tmp_path / instance_id
        for repo_name in ["repo_1", "repo_2"]:
            repo = instance_root / repo_name
            repo.mkdir(parents=True)
            executable = repo / "executable"
            executable.write_text("#!/bin/sh\nexit 0\n")
        (instance_root / "repo_notes").mkdir()
        (instance_root / "repo_notes" / "executable").write_text("ignored\n")

        loaded = load_mutant_suite(tmp_path, instance_id)

        assert loaded is not None
        loaded_root, suite = loaded
        assert loaded_root == instance_root
        assert suite.instance_id == instance_id
        assert [(m.id, m.payload) for m in suite.mutants] == [
            ("repo_1", "repo_1/executable"),
            ("repo_2", "repo_2/executable"),
        ]

    def test_load_mutant_suite_reads_manifest_summary_metadata(self, tmp_path):
        instance_id = "example__tool.1234567"
        instance_root = tmp_path / instance_id
        repo = instance_root / "repo_1"
        repo.mkdir(parents=True)
        (repo / "executable").write_text("#!/bin/sh\nexit 0\n")
        (instance_root / "mutants.json").write_text(json.dumps({
            "instance_id": instance_id,
            "mutants": [
                {
                    "id": "repo_1",
                    "kind": "wrapper",
                    "payload": "repo_1/executable",
                    "target_spec": "Spec 1",
                    "mutation": "breaks alpha handling",
                }
            ],
        }))

        loaded = load_mutant_suite(tmp_path, instance_id)

        assert loaded is not None
        _, suite = loaded
        assert suite.mutants[0].target_spec == "Spec 1"
        assert suite.mutants[0].mutation == "breaks alpha handling"


    def test_generate_mutants_instance_runs_codex_and_copies_repos(self, tmp_path, monkeypatch, caplog):
        instance_id = "example__tool.1234567"
        spec = tmp_path / "specs" / instance_id
        spec.mkdir(parents=True)
        (spec / "README.md").write_text("spec\n")
        branch = tmp_path / "repos" / instance_id / "branch-a"
        (branch / "eval").mkdir(parents=True)
        (branch / "eval" / "run.sh").write_text("pytest\n")
        (branch / "src").mkdir()
        (branch / "src" / "main.c").write_text("int main(void) { return 0; }\n")
        (branch / "build.sh").write_text("cc src/main.c -o executable\n")
        links = tmp_path / "links" / instance_id
        links.mkdir(parents=True)
        (links / "test_spec_links.json").write_text(json.dumps({
            "instance_id": instance_id,
            "spec_sections": ["Spec 1", "Spec 2"],
            "test_functions": [
                {"id": "branch-a/test_alpha", "branch": "branch-a", "name": "test_alpha", "description": "alpha", "target_specs": ["Spec 1"]},
                {"id": "branch-a/test_beta", "branch": "branch-a", "name": "test_beta", "description": "beta", "target_specs": ["Spec 2"]},
            ],
        }))
        envs = []
        previous_manifest_payload = json.dumps({"mutants": [{"id": "repo_old", "target_spec": "Old Spec", "mutation": "old mutation"}]}) + "\n"
        previous_manifest = tmp_path / "out" / instance_id / "mutants.json"
        previous_manifest.parent.mkdir(parents=True)
        previous_manifest.write_text(previous_manifest_payload)

        class Env:
            executable = "docker"
            container_id = "container"

            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.commands = []
                self.copied = []
                self.cleaned = False
                envs.append(self)

            def execute(self, command, *, timeout=None, output_callback=None):
                self.commands.append(command)
                if "find /workspace" in command:
                    return {
                        "returncode": 0,
                        "stdout": "repo_1\nrepo_2\n",
                        "output": "",
                        "stderr": "",
                        "exception_info": "",
                    }
                if "mutants.json" in command:
                    manifest = json.dumps({
                        "mutants": [
                            {"id": "repo_1", "target_spec": "Spec 1 - help output", "mutation": "break alpha"},
                            {"id": "repo_2", "target_spec": "## Spec 2: version", "mutation": "invert beta"},
                        ]
                    }) + "\n"
                    return {"returncode": 0, "stdout": manifest, "output": manifest, "stderr": "", "exception_info": ""}
                if output_callback is not None:
                    if "build_mutant_repos_parallel.sh" in command:
                        line = "[mutant-build-progress] completed=2/2 compiled=2 reused=0 failed=0 last=repo_2 outcome=compiled build_duration_second=1.0 cpus_per_build=3\n"
                    else:
                        line = '{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n'
                    output_callback("stdout", line)
                    return {"returncode": 0, "stdout": line, "output": line, "stderr": "", "exception_info": ""}
                return {"returncode": 0, "stdout": "", "output": "", "stderr": "", "exception_info": ""}

            def copy_in(self, local_path, container_path):
                local_path = Path(local_path)
                if local_path.is_file():
                    self.copied.append((container_path, local_path.read_text()))
                    return
                files = sorted(
                    path.relative_to(local_path).as_posix()
                    for path in local_path.rglob("*")
                    if path.is_file()
                )
                self.copied.append((container_path, files))

            def copy_out_file(self, container_path, local_path):
                local_path = Path(local_path)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(f"#!/bin/sh\n# rebuilt from {container_path}\n")

            def cleanup(self):
                self.cleaned = True

        copied_excludes = []

        def fake_copy_out(env, container_path, local_path, *, excludes=None):
            copied_excludes.append(excludes)
            local_path.mkdir(parents=True)
            (local_path / "build.sh").write_text(f"# copied from {container_path}\n")
            # Distinct per repository: identical mutant builds are a policy violation.
            (local_path / "executable").write_text(f"#!/bin/sh\n# {container_path}\nexit 0\n")

        monkeypatch.setattr("programbench.mutants.ContainerEnvironment", Env)
        monkeypatch.setattr("programbench.mutants._copy_dir_from_container", fake_copy_out)

        caplog.set_level(logging.INFO, logger="programbench.mutants")

        result = generate_mutants_instance(
            instance={"instance_id": instance_id, "image_name": "programbench/example"},
            repo_dir=tmp_path / "repos",
            spec_in=tmp_path / "specs",
            test_spec_links=tmp_path / "links",
            output=tmp_path / "out",
            force=True,
            image="codex-image",
            codex_command="codex exec --cd /workspace",
            codex_auth_file=None,
            codex_log_dir=tmp_path / "logs",
            progress_log_interval=0,
            mutant_build_jobs=2,
        )

        assert result["status"] == "ok"
        assert any(
            "[mutant-build-progress] completed=2/2 compiled=2 reused=0 failed=0" in record.message
            for record in caplog.records
        )
        assert not any(
            "rebuild mutant executables still running" in record.message
            for record in caplog.records
        )
        assert result["branch"] == "branch-a"
        assert result["mutant_repositories"] == ["repo_1", "repo_2"]
        assert result["traj"] == str(tmp_path / "logs" / f"{instance_id}.mutants.traj.json")
        assert (tmp_path / "out" / instance_id / "repo_1" / "build.sh").is_file()
        assert (tmp_path / "out" / instance_id / "repo_2" / "build.sh").is_file()
        manifest_path = tmp_path / "out" / instance_id / "mutants.json"
        assert result["mutants_manifest"] == str(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        assert manifest["instance_id"] == instance_id
        assert [(m["id"], m["target_spec"], m["mutation"]) for m in manifest["mutants"]] == [
            ("repo_1", "Spec 1", "break alpha"),
            ("repo_2", "Spec 2", "invert beta"),
        ]
        assert copied_excludes == [_MUTANT_COPY_EXCLUDES, _MUTANT_COPY_EXCLUDES]
        assert result["compact_storage"]["compacted"] == 2
        assert result["compact_storage"]["artifacts"] == 2
        assert envs[0].kwargs["image"] == "codex-image"
        assert envs[1].kwargs["image"] == "programbench/example:task_cleanroom"
        assert envs[0].cleaned
        assert envs[1].cleaned
        assert not any("CARGO_TARGET_DIR=" in command for command in envs[1].commands)
        assert not any("build_mutant_repos_parallel.sh" in command for command in envs[0].commands)
        assert any("/tmp/programbench-build/mutants" in command for command in envs[1].commands)
        assert not any("--cpus 6 /workspace" in command for command in envs[1].commands)
        assert any("build_mutant_repos_parallel.sh --jobs 2 --cpus 6" in command for command in envs[1].commands)
        run_args = envs[1].kwargs["run_args"]
        assert run_args[:6] == [
            "--memory", "60g", "--memory-swap", "60g", "--pids-limit", "2048",
        ]
        # Dependency caches are mounted from the host, never baked into an image.
        assert any(argument.endswith(":/tmp/programbench-sccache") for argument in run_args)
        assert envs[1].kwargs["env"]["PROGRAMBENCH_USE_SCCACHE"] == "1"
        assert ("/workspace/repo", ["build.sh", "src/main.c"]) in envs[0].copied
        assert any(path == "/workspace/mutant_plan.json" for path, _ in envs[0].copied)
        assert ("/workspace/codex-goal.md", MUTANT_GENERATION_PROMPT) in envs[0].copied
        assert any(MUTANT_GENERATION_GOAL_COMMAND in command for command in envs[0].commands)
        trajectory = json.loads(Path(result["traj"]).read_text())
        assert trajectory["info"]["task"] == "generate-mutants"
        assert trajectory["info"]["previous_mutants_manifest"] == str(previous_manifest)
        assert trajectory["info"]["mutant_repositories"] == ["repo_1", "repo_2"]
        assert trajectory["info"]["image"] == "codex-image"
        assert trajectory["info"]["rebuild_image"] == "programbench/example:task_cleanroom"
        assert trajectory["info"]["rebuild_skipped"] is False
        assert trajectory["info"]["rebuild_cpus"] == 6
        assert trajectory["info"]["mutant_build_jobs"] == 2
        assert "mutant_repository_min_count" not in trajectory["info"]
        assert "mutant_repository_max_count" not in trajectory["info"]
        assert trajectory["messages"][1]["content"] == "done"

    def test_generate_mutants_instance_defaults_to_task_cleanroom_and_uses_build_helper(self, tmp_path, monkeypatch):
        instance_id = "example__tool.1234567"
        spec = tmp_path / "specs" / instance_id
        spec.mkdir(parents=True)
        (spec / "README.md").write_text("spec\n")
        branch = tmp_path / "repos" / instance_id / "branch-a"
        branch.mkdir(parents=True)
        (branch / "eval").mkdir()
        (branch / "build.sh").write_text("#!/bin/sh\n")
        links = tmp_path / "links" / instance_id
        links.mkdir(parents=True)
        (links / "test_spec_links.json").write_text(json.dumps({
            "instance_id": instance_id,
            "spec_sections": ["Spec 1"],
            "test_functions": [
                {"id": "branch-a/test_one", "branch": "branch-a", "name": "test_one", "description": "one", "target_specs": ["Spec 1"]},
            ],
        }))
        envs = []

        class Env:
            executable = "docker"
            container_id = "container"

            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.commands = []
                envs.append(self)

            def execute(self, command, *, timeout=None, output_callback=None):
                self.commands.append(command)
                if "find /workspace" in command:
                    return {"returncode": 0, "stdout": "repo_1\n", "output": "", "stderr": "", "exception_info": ""}
                return {"returncode": 0, "stdout": "", "output": "", "stderr": "", "exception_info": ""}

            def copy_in(self, local_path, container_path):
                pass

            def copy_out_file(self, container_path, local_path):
                local_path = Path(local_path)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.unlink(missing_ok=True)
                local_path.write_text("#!/bin/sh\nexit 0\n")

            def cleanup(self):
                pass

        def fake_copy_out(env, container_path, local_path, *, excludes=None):
            assert excludes == _MUTANT_COPY_EXCLUDES
            local_path.mkdir(parents=True)
            executable = local_path / "executable"
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o111)

        monkeypatch.setattr("programbench.mutants.ContainerEnvironment", Env)
        monkeypatch.setattr("programbench.mutants._copy_dir_from_container", fake_copy_out)

        result = generate_mutants_instance(
            instance={"instance_id": instance_id, "image_name": "programbench/example"},
            repo_dir=tmp_path / "repos",
            spec_in=tmp_path / "specs",
            test_spec_links=tmp_path / "links",
            output=tmp_path / "out",
            force=True,
            codex_command="codex exec --cd /workspace",
            codex_auth_file=None,
            codex_log_dir=tmp_path / "logs",
            progress_log_interval=0,
        )

        assert result["status"] == "ok"
        assert result["rebuild_skipped"] is False
        assert not (tmp_path / "out" / instance_id / "repo_1" / "executable").exists()
        assert result["compact_storage"]["compacted"] == 1
        assert len(envs) == 2
        assert all(env.kwargs["image"] == "programbench/example:task_cleanroom" for env in envs)
        assert not any("build_mutant_repos_parallel.sh" in command for command in envs[0].commands)
        assert any("/tmp/programbench-build/mutants" in command for command in envs[1].commands)
        run_args = envs[1].kwargs["run_args"]
        assert run_args[:6] == [
            "--memory", "60g", "--memory-swap", "60g", "--pids-limit", "2048",
        ]
        # Dependency caches are mounted from the host, never baked into an image.
        assert any(argument.endswith(":/tmp/programbench-sccache") for argument in run_args)
        assert envs[1].kwargs["env"]["PROGRAMBENCH_USE_SCCACHE"] == "1"

    def test_test_suite_evaluation_result_reports_mutation_score(self):
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[TestResult(name="test_one", status="passed", extra={})],
                ),
                BinaryTestSuiteResult(
                    binary_id="missing_arg_c",
                    role="candidate",
                    test_results=[TestResult(name="test_one", status="failure", extra={})],
                ),
                BinaryTestSuiteResult(
                    binary_id="changed_arg_v",
                    role="candidate",
                    test_results=[TestResult(name="test_one", status="passed", extra={})],
                ),
            ]
        )

        assert result.ground_truth_passed
        assert result.n_test_functions == 1
        assert result.n_mutants == 2
        assert result.n_mutants_killed == 1
        assert result.mutation_score == 0.5
        assert result.validity_rate == 1.0
        assert result.mutation_score == 0.5

    def test_test_suite_evaluation_mutation_score_ignores_ground_truth_failures(self):
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        TestResult(name="gt_passes", status="passed", extra={}),
                        TestResult(name="gt_fails", status="failure", extra={}),
                    ],
                ),
                BinaryTestSuiteResult(
                    binary_id="only_fails_where_ground_truth_fails",
                    role="candidate",
                    test_results=[
                        TestResult(name="gt_passes", status="passed", extra={}),
                        TestResult(name="gt_fails", status="failure", extra={}),
                    ],
                ),
                BinaryTestSuiteResult(
                    binary_id="fails_where_ground_truth_passes",
                    role="candidate",
                    test_results=[
                        TestResult(name="gt_passes", status="failure", extra={}),
                        TestResult(name="gt_fails", status="failure", extra={}),
                    ],
                ),
            ]
        )

        assert result.ground_truth_passing_test_names == {"gt_passes"}
        assert result.n_mutants == 2
        assert result.n_mutants_killed == 1
        assert result.mutation_score == 0.5
        assert result.mutation_score == 0.5

    def test_candidate_only_internal_test_does_not_reduce_ground_truth_validity_rate(self):
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth", role="ground_truth",
                    test_results=[TestResult(name="real_test", status="passed", extra={})],
                ),
                BinaryTestSuiteResult(
                    binary_id="mutant", role="candidate",
                    test_results=[
                        TestResult(name="real_test", status="passed", extra={}),
                        TestResult(name="pytest.internal", status="error", extra={}),
                    ],
                ),
            ]
        )

        assert result.validity_rate == 1.0
        assert result.ground_truth_passing_test_names == {"real_test"}
        assert result.n_mutants_killed == 0

    @pytest.mark.parametrize(
        ("mutants", "reference_trials", "positions"),
        [
            (54, 3, [9, 28, 47]),
            (54, 1, [27]),
            (0, 3, [0, 1, 2]),
            (1, 1, [1]),
        ],
    )
    def test_execution_order_spaces_reference_trials_through_the_sweep(
        self, tmp_path, mutants, reference_trials, positions
    ):
        evaluator = TestSuiteEvaluator(
            image_name="programbench/example.abc1234",
            test_suite_archive=tmp_path,
            reference_trials=reference_trials,
            mutants_root=tmp_path,
            mutants=[
                MutantSpec(id=f"repo_{index}", payload=f"repo_{index}/executable")
                for index in range(1, mutants + 1)
            ],
        )

        order = evaluator._execution_order()

        assert len(order) == mutants + reference_trials
        assert [index for index, (kind, _) in enumerate(order) if kind == "ground_truth"] == positions
        # Every trial appears exactly once, and the mutants keep their order.
        assert [value for kind, value in order if kind == "ground_truth"] == list(range(reference_trials))
        assert [value.id for kind, value in order if kind == "mutant"] == [
            f"repo_{index}" for index in range(1, mutants + 1)
        ]

    def test_test_suite_evaluator_runs_reference_trials_inside_the_mutant_sweep(self, tmp_path, monkeypatch):
        # The reference trial must see the same host contention as the mutants,
        # or a test that only fails under the sweep's load stays mutation-score-eligible
        # and kills mutants it never detected.
        evaluator = TestSuiteEvaluator(
            image_name="programbench/example.abc1234",
            test_suite_archive=tmp_path,
            mutants_root=tmp_path,
            mutants=[MutantSpec(id=f"m{index}", payload=f"m{index}/executable") for index in (1, 2, 3)],
        )
        calls = []

        def run_ground_truth():
            calls.append("ground_truth")
            return BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[TestResult(name="test_one", status="passed", extra={})],
            )

        def run_mutant(mutant):
            calls.append(mutant.id)
            return BinaryTestSuiteResult(
                binary_id=mutant.id,
                role="candidate",
                test_results=[TestResult(name="test_one", status="failure", extra={})],
            )

        monkeypatch.setattr(evaluator, "_run_ground_truth", run_ground_truth)
        monkeypatch.setattr(evaluator, "_run_mutant", run_mutant)

        result = evaluator.run()

        assert calls == ["m1", "m2", "ground_truth", "m3"]
        assert result.n_mutants_killed == 3

    def test_test_suite_evaluator_parallelizes_references_and_mutants_with_branch_workers(self, tmp_path, monkeypatch, caplog):
        evaluator = TestSuiteEvaluator(
            image_name="programbench/example.abc1234",
            test_suite_archive=tmp_path,
            branch_workers=2,
            reference_trials=2,
            mutants_root=tmp_path,
            mutants=[
                MutantSpec(id="m1", payload="m1/executable"),
                MutantSpec(id="m2", payload="m2/executable"),
            ],
        )
        pool_calls = {}
        progress_updates = []
        evaluator.mutant_progress_callback = lambda: progress_updates.append(1)

        class FakeFuture:
            def __init__(self, value):
                self.value = value

            def result(self):
                return self.value

        class FakePool:
            def __init__(self, max_workers):
                pool_calls["max_workers"] = max_workers
                pool_calls["submitted"] = []

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def submit(self, fn, execution_fn, *args, **kwargs):
                pool_calls["submitted"].append(args[0].id if args else "ground_truth")
                return FakeFuture(fn(execution_fn, *args, **kwargs))

        def fake_as_completed(futures):
            return list(futures)[::-1]

        monkeypatch.setattr(evaluator, "_run_ground_truth", lambda: BinaryTestSuiteResult(
            binary_id="ground_truth",
            role="ground_truth",
            test_results=[TestResult(name="test_one", status="passed", extra={})],
        ))
        monkeypatch.setattr(evaluator, "_run_mutant", lambda mutant: BinaryTestSuiteResult(
            binary_id=mutant.id,
            role="candidate",
            test_results=[TestResult(name="test_one", status="failure", extra={})],
        ))
        monkeypatch.setattr("programbench.eval.test_suite_eval.ThreadPoolExecutor", FakePool)
        monkeypatch.setattr("programbench.eval.test_suite_eval.as_completed", fake_as_completed)
        caplog.set_level(logging.INFO, logger="programbench.eval.test_suite_eval")

        result = evaluator.run()

        assert pool_calls == {
            "max_workers": 2,
            # Each reference trial is submitted -- and so started -- from
            # inside the mutant sweep, not ahead of it.
            "submitted": ["m1", "ground_truth", "m2", "ground_truth"],
        }
        assert len(result.ground_truth_trials) == 2
        assert [r.binary_id for r in result.binary_results] == ["ground_truth", "m1", "m2"]
        assert result.n_mutants_killed == 2
        messages = [record.getMessage() for record in caplog.records]
        assert (
            "programbench/example.abc1234: evaluating 2 reference trial(s) and "
            "2 mutant(s) with 2 worker(s)"
        ) in messages
        assert all("finished" not in message for message in messages)
        assert all("mutant m1 result" not in message for message in messages)
        assert all("mutant m2 result" not in message for message in messages)
        assert progress_updates == [1, 1]

    def test_test_suite_evaluator_runs_mutants_when_ground_truth_fails(self, tmp_path, monkeypatch, caplog):
        evaluator = TestSuiteEvaluator(
            image_name="programbench/example.abc1234",
            test_suite_archive=tmp_path,
            mutants_root=tmp_path,
            mutants=[MutantSpec(id="m1", payload="m1/executable")],
        )
        calls = []

        def run_ground_truth():
            calls.append("ground_truth")
            return BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[TestResult(name="test_one", status="failure", extra={})],
            )

        def run_mutant(mutant):
            calls.append(mutant.id)
            return BinaryTestSuiteResult(
                binary_id=mutant.id,
                role="candidate",
                test_results=[TestResult(name="test_one", status="failure", extra={})],
            )

        monkeypatch.setattr(evaluator, "_run_ground_truth", run_ground_truth)
        monkeypatch.setattr(evaluator, "_run_mutant", run_mutant)
        caplog.set_level(logging.INFO, logger="programbench.eval.test_suite_eval")

        result = evaluator.run()

        assert calls == ["m1", "ground_truth"]
        assert result.n_mutants == 1
        assert result.n_mutants_killed == 0
        assert result.validity_rate == 0.0
        assert result.mutation_score == 0.0
        assert "programbench/example.abc1234: ground truth did not pass; evaluated 1 mutant(s) anyway" in [
            record.getMessage() for record in caplog.records
        ]

    def test_mutation_score_excludes_reference_failures_and_flaky_tests(self):
        stable = TestResult(name="stable", status="passed", extra={})
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        stable,
                        TestResult(name="reference_failure", status="failure", extra={}),
                        TestResult(name="flaky", status="passed", extra={}),
                    ],
                ),
                BinaryTestSuiteResult(
                    binary_id="mutant",
                    role="candidate",
                    test_results=[
                        stable,
                        TestResult(name="reference_failure", status="failure", extra={}),
                        TestResult(name="flaky", status="failure", extra={}),
                    ],
                ),
            ],
            ground_truth_trials=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        stable,
                        TestResult(name="reference_failure", status="failure", extra={}),
                        TestResult(name="flaky", status="passed", extra={}),
                    ],
                ),
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[
                        stable,
                        TestResult(name="reference_failure", status="failure", extra={}),
                        TestResult(name="flaky", status="failure", extra={}),
                    ],
                ),
            ],
        )

        assert result.flaky_test_names == {"flaky"}
        assert result.ground_truth_passing_test_names == {"stable"}
        assert result.n_mutants_killed == 0
        assert result.mutation_score == 0.0

    def test_infrastructure_failed_reference_trial_does_not_make_every_test_flaky(self):
        stable = TestResult(name="stable", status="passed", extra={})
        wrong = TestResult(name="wrong", status="failure", extra={})
        result = TestSuiteEvaluationResult(
            binary_results=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[stable, wrong],
                ),
                BinaryTestSuiteResult(
                    binary_id="mutant",
                    role="candidate",
                    test_results=[
                        TestResult(name="stable", status="failure", extra={}),
                        wrong,
                    ],
                ),
            ],
            ground_truth_trials=[
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    test_results=[stable, wrong],
                ),
                BinaryTestSuiteResult(
                    binary_id="ground_truth",
                    role="ground_truth",
                    error_code="results_size_failed",
                    error_details="oversized JUnit",
                ),
            ],
        )

        assert not result.ground_truth_passed
        assert result.flaky_test_names == set()
        assert result.validity_rate == 0.5
        assert result.ground_truth_passing_test_names == {"stable"}
        assert result.n_mutants_killed == 1
        assert result.mutation_score == 1.0

    def test_run_binary_restores_executable_after_payload_copy(self, tmp_path, monkeypatch):
        payload = tmp_path / "payload"
        (payload / "eval").mkdir(parents=True)
        (payload / "eval" / "run.sh").write_text("#!/usr/bin/env bash\n")
        (payload / "executable").symlink_to("programs/zstd")
        reference_branch = tmp_path / "references" / "example.abc1234" / "branch-a"
        reference_branch.mkdir(parents=True)
        helper = reference_branch / "helper"
        helper.write_bytes(b"\x7fELFhelper")
        helper.chmod(0o755)
        ground_truth = tmp_path / "ground-truth-executable"
        ground_truth.write_bytes(b"source-built")
        ground_truth.chmod(0o755)
        evaluator = TestSuiteEvaluator(
            image_name="programbench/example.abc1234",
            test_suite_archive=payload,
            instance_id="example.abc1234",
            ground_truth_executable=ground_truth,
            reference_tests_root=tmp_path / "references",
        )
        commands = []
        copied = []

        class FakeEnv:
            executable = "docker"
            container_id = "fake-container"

            def execute(self, command, timeout=20):
                commands.append(command)
                return {
                    "output": "",
                    "stdout": "",
                    "stderr": "",
                    "returncode": 0,
                    "exception_info": "",
                }

            def copy_in(self, local_path, container_path):
                copied.append((local_path, container_path))

            def cleanup(self):
                commands.append("cleanup")

        monkeypatch.setattr(evaluator, "_new_env", lambda: FakeEnv())
        monkeypatch.setattr(
            evaluator,
            "_copy_file_from_container",
            lambda **kwargs: JUNIT_XML_ALL_PASS,
        )

        result = evaluator._run_binary(binary_id="ground_truth", role="ground_truth")

        assert result.error_code is None
        assert result.n_passed == 2
        assert copied == [
            (ground_truth, "/workspace/.programbench-ground-truth-executable"),
            (payload, "/workspace/"),
            (helper, "/workspace/.programbench-bin/helper"),
            (Path(pytest_journal.__file__).with_name("pytest_watchdog.py"), "/tmp/programbench-pytest-watchdog/pytest_watchdog.py"),
            (_JUNIT_DIAGNOSTIC_SANITIZER, "/tmp/programbench-junit-diagnostics.py"),
        ]
        install_index = commands.index(
            "rm -f ./executable && mv ./.programbench-ground-truth-executable "
            "./executable && chmod +x ./executable"
        )
        assert install_index < commands.index("test -x ./executable")
        clean_index = commands.index("rm -rf ./eval ./results.xml")
        assert "cp -f ./executable /tmp/programbench-executable-under-test" in commands[clean_index - 1]
        assert "test ! -e /workspace/.programbench-bin/helper" in commands
        assert "chmod +x /workspace/.programbench-bin/helper" in commands
        prepare_bin = next(command for command in commands if "mkdir -p .programbench-bin" in command)
        assert ".programbench-bin/python3" in prepare_bin
        run_tests = next(command for command in commands if "PATH=\"$PWD/.programbench-bin:$PATH\"" in command)
        assert commands.index(prepare_bin) < commands.index(run_tests)
        restore_commands = [command for command in commands if "programbench-executable-under-test ./executable" in command]
        assert restore_commands == [
            "rm -f ./executable && "
            "cp -f /tmp/programbench-executable-under-test ./executable && "
            "chmod +x ./executable"
        ]
        assert commands.index(restore_commands[0]) < commands.index("test -f eval/run.sh")
        sanitize_command = next(
            command for command in commands if "programbench-junit-diagnostics.py" in command
        )
        assert str(MAX_JUNIT_DIAGNOSTIC_BYTES) in sanitize_command
        assert str(MAX_RAW_JUNIT_XML_BYTES) in sanitize_command
        assert commands.index(run_tests) < commands.index(sanitize_command)

        payload_helper = payload / "helper"
        payload_helper.write_bytes(helper.read_bytes())
        payload_helper.chmod(0o755)
        commands.clear()
        copied.clear()

        result = evaluator._run_binary(binary_id="ground_truth", role="ground_truth")

        assert result.error_code is None
        assert copied == [
            (ground_truth, "/workspace/.programbench-ground-truth-executable"),
            (payload, "/workspace/"),
            (helper, "/workspace/.programbench-bin/helper"),
            (Path(pytest_journal.__file__).with_name("pytest_watchdog.py"), "/tmp/programbench-pytest-watchdog/pytest_watchdog.py"),
            (_JUNIT_DIAGNOSTIC_SANITIZER, "/tmp/programbench-junit-diagnostics.py"),
        ]
        assert "test ! -e /workspace/.programbench-bin/helper" in commands
        assert "chmod +x /workspace/.programbench-bin/helper" in commands


    def test_failure_matrix_uses_parent_status_for_subtest_rows(self):
        matrix = TestSuiteEvaluator._failure_matrix([
            BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[TestResult(name="tests.TestCase.test_colors", status="passed", extra={})],
            ),
            BinaryTestSuiteResult(
                binary_id="mutant",
                role="candidate",
                test_results=[
                    TestResult(name="tests.TestCase.test_colors", status="passed", extra={}),
                    TestResult(name="tests.TestCase.test_colors (color=GREEN)", status="failure", extra={}),
                ],
            ),
        ])

        row = next(line for line in matrix.splitlines() if "test_colors (color=GREEN)" in line)
        assert "-" not in row
        assert " ." in row
        assert row.rstrip().endswith("F")
        assert "1 other tests" in matrix

    def test_candidate_outcome_uses_normalized_subtest_denominator(self):
        binary_results = [
            BinaryTestSuiteResult(
                binary_id="ground_truth",
                role="ground_truth",
                test_results=[TestResult(name="tests.TestCase.test_colors", status="passed", extra={})],
            ),
            BinaryTestSuiteResult(
                binary_id="mutant",
                role="candidate",
                test_results=[
                    TestResult(name="tests.TestCase.test_colors", status="passed", extra={}),
                    TestResult(name="tests.TestCase.test_colors (color=GREEN)", status="failure", extra={}),
                ],
            ),
        ]

        assert TestSuiteEvaluator._candidate_outcome(binary_results[1], binary_results) == "killed (1/2 passed)"

    def test_test_suite_evaluator_detailed_logs_failure_matrix(self, tmp_path, monkeypatch, caplog):
        evaluator = TestSuiteEvaluator(
            image_name="programbench/example.abc1234",
            test_suite_archive=tmp_path,
            mutants_root=tmp_path,
            mutants=[MutantSpec(id="m1", payload="m1/executable")],
            detailed_logs=True,
        )

        monkeypatch.setattr(evaluator, "_run_ground_truth", lambda: BinaryTestSuiteResult(
            binary_id="ground_truth",
            role="ground_truth",
            test_results=[
                TestResult(name="test_one", status="passed", extra={}),
                TestResult(name="test_two", status="failure", extra={}),
            ],
        ))
        monkeypatch.setattr(evaluator, "_run_mutant", lambda mutant: BinaryTestSuiteResult(
            binary_id=mutant.id,
            role="candidate",
            test_results=[
                TestResult(name="test_one", status="failure", extra={}),
                TestResult(name="test_two", status="passed", extra={}),
            ],
        ))
        caplog.set_level(logging.DEBUG, logger="programbench.eval.test_suite_eval")

        evaluator.run()

        messages = "\n".join(record.getMessage() for record in caplog.records)
        assert "Failure matrix:" in messages
        assert "test_function" in messages
        assert "ground_truth" in messages
        assert "m1" in messages
        assert "test_one" in messages
        assert "test_two" in messages
        assert "Legend: .=passed F=failure E=error S=system_error K=skipped N=not_run -=missing" in messages


def test_docker_cpus_for_budget_divides_across_active_workers() -> None:
    assert docker_cpus_for_budget(32, 1) == 32
    assert docker_cpus_for_budget(32, 8) == 4
    assert docker_cpus_for_budget(32, 16) == 2
    assert docker_cpus_for_budget(4, 8) == 1
    assert docker_cpus_for_budget(0, 8, fallback=6) == 6


def test_fixed_test_branch_cpu_requirements_use_uniform_default() -> None:
    assert cpus_for_test_branch("unknown__task.0000000", "unknown-branch") == 2
    assert cpus_for_test_branch("ffmpeg__ffmpeg.360a402", "3f244e346e7e") == 2
    assert cpus_for_test_branch("ffmpeg__ffmpeg.360a402", "another-branch") == 2
    assert cpus_for_test_branch("facebook__zstd.1168da0", "ff48618e10b3") == 2
    assert cpus_for_test_branch("facebook__zstd.1168da0", "f7278a893d6d") == 2


def test_evaluator_uses_branch_cpu_requirements_and_caps_to_budget() -> None:
    evaluator = Evaluator(
        tests_branches=["heavy", "normal"],
        docker_cpus=6,
        branch_cpu_requirements={"heavy": 8, "normal": 2},
        cpu_budget=6,
    )

    assert evaluator._branch_cpus("heavy") == 6
    assert evaluator._branch_cpus("normal") == 2
    assert evaluator._branch_cpus("unconfigured") == 6


def test_missing_results_reports_run_failure_even_when_run_sh_exits_zero(
    tmp_path, monkeypatch
):
    """A run.sh that swallows pytest's exit code must not hide a failed run.

    libtmux's pytest plugin fails to load under pytest >= 9.1, which exits 1
    before collection; run.sh wrappers commonly treat 1 as "tests ran and
    failed" and exit 0, leaving no results.xml behind.
    """
    plugin_crash = "Failed: Marks cannot be applied to fixtures."
    evaluator = TestSuiteEvaluator(image_name="image", test_suite_archive=tmp_path)

    class FakeEnv:
        def execute(self, command, timeout=None):
            output = plugin_crash if "./eval/run.sh" in command else ""
            return {"returncode": 0, "output": output, "stdout": output, "stderr": ""}

        def copy_in(self, local_path, container_path):
            pass

        def cleanup(self):
            pass

    monkeypatch.setattr(evaluator, "_new_env", lambda *args, **kwargs: FakeEnv())
    monkeypatch.setattr(
        evaluator,
        "_copy_file_from_container",
        lambda **kwargs: (_ for _ in ()).throw(
            EvalStepError("results_read_failed", "Could not find the file")
        ),
    )

    result = evaluator._run_binary(binary_id="gt", role="ground_truth")

    assert result.error_code == "run_tests_failed_no_results"
    assert plugin_crash in result.error_details


def test_run_tests_pins_pip_so_model_authored_run_sh_cannot_pull_broken_pytest(
    tmp_path, monkeypatch
):
    """eval/run.sh scripts install pytest unpinned; pytest 9.1 breaks plugin load."""
    evaluator = TestSuiteEvaluator(image_name="image", test_suite_archive=tmp_path)
    commands = []

    class FakeEnv:
        def execute(self, command, timeout=None):
            commands.append(command)
            return {"returncode": 0, "output": "", "stdout": "", "stderr": ""}

        def copy_in(self, local_path, container_path):
            pass

        def cleanup(self):
            pass

    monkeypatch.setattr(evaluator, "_new_env", lambda *args, **kwargs: FakeEnv())
    monkeypatch.setattr(
        evaluator, "_copy_file_from_container", lambda **kwargs: "<testsuites/>"
    )
    evaluator._run_binary(binary_id="gt", role="ground_truth")

    run_tests = next(command for command in commands if "./eval/run.sh" in command)
    assert f"export PIP_CONSTRAINT={PIP_CONSTRAINT_PATH}" in run_tests
    assert run_tests.index("PIP_CONSTRAINT") < run_tests.index("./eval/run.sh")


@pytest.mark.parametrize("suite_evaluator", [False, True])
@pytest.mark.parametrize("cpus", [1, 2, 6])
def test_evaluators_bound_openmp_threads(monkeypatch, tmp_path, suite_evaluator, cpus):
    captured = {}

    class FakeContainerEnvironment:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    if suite_evaluator:
        monkeypatch.setattr(
            "programbench.eval.test_suite_eval.ContainerEnvironment", FakeContainerEnvironment
        )
        evaluator = TestSuiteEvaluator(
            image_name="example", test_suite_archive=tmp_path, docker_cpus=cpus
        )
        evaluator._new_env()
    else:
        monkeypatch.setattr("programbench.eval.eval.ContainerEnvironment", FakeContainerEnvironment)
        evaluator = Evaluator(tests_branches=[], image_name="example", docker_cpus=cpus)
        evaluator._new_env(evaluator.image)
        assert captured["env"]["PYTEST_XDIST_AUTO_NUM_WORKERS"] == str(cpus)

    assert captured["cpus"] == cpus
    assert captured["env"]["OMP_NUM_THREADS"] == "1"


def test_pytest_watchdog_kills_hung_subprocess_tree_and_keeps_fast_ones(tmp_path):
    (tmp_path / "test_hang.py").write_text(
        "import subprocess\n"
        "def test_hangs():\n"
        f"    assert subprocess.run(['sh', '-c', 'sleep 60 & echo $! > {tmp_path}/pid; wait'], capture_output=True).returncode == 0\n"
        "def test_fast():\n"
        "    assert subprocess.run(['true'], capture_output=True).returncode == 0\n"
    )
    plugin_dir = Path(pytest_journal.__file__).parent
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "pytest_watchdog", str(tmp_path)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(plugin_dir), "PROGRAMBENCH_SUBPROCESS_TIMEOUT": "1"},
        timeout=60,
    )
    assert time.monotonic() - started < 30
    assert result.returncode == 1 and "1 failed, 1 passed" in result.stdout, result.stdout + result.stderr
    assert "returncode=-9" in result.stdout
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "pid").read_text()), 0)


def test_second_reference_trial_runs_with_a_quarter_of_the_cpu_quota(tmp_path, monkeypatch):
    """Two entr tests raced the watcher and passed three identical trials by luck, then read as
    spec contradictions. One slowed trial widens such windows; the others keep the normal quota.
    """
    from programbench.eval.test_suite_eval import TestSuiteEvaluator

    evaluator = TestSuiteEvaluator(image_name="programbench/example.abc1234", test_suite_archive=tmp_path, docker_cpus=8, reference_trials=3)
    quotas = []
    monkeypatch.setattr(
        evaluator, "_run_binary",
        lambda **kwargs: quotas.append(kwargs["cpus"]) or BinaryTestSuiteResult(binary_id="ground_truth", role="ground_truth"),
    )

    for _ in range(3):
        evaluator._run_ground_truth()

    assert quotas == [None, 2, None]
