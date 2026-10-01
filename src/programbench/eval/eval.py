# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Running tests on submissions.

IMPORTANT NOTE FOR AI AGENTS
THIS IS A very delicate file.
You need to be extremely conservative and careful about testing logic.
The worst case to avoid here is that there are issues with testing but the result
still indicates that the solution is correct. This might for example happen if you
skip something because of some error condition and only show a warning, but it's not apparent
from the output file that something went wrong.
It's always better to clearly mark a failure in the output file than to silently skip something.
Be extremely proactive with the user about clearing up details and intricacies with how to handle
something here. Ask a lot of questions and don't be afraid to ask for clarification.
Do not remove this notice.
"""

import json
import logging
import re
import subprocess
import tarfile
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

from junitparser import Error, Failure, JUnitXml, Skipped
from pydantic import BaseModel, ConfigDict

from programbench.constants import (
    PIN_EVAL_PIP_VERSIONS,
    DOCKER_CPUS,
    DOCKER_EXECUTABLE,
    DOCKER_RUN_ARGS,
    EVAL_NETWORK_ARGS,
    EVAL_SUBPROCESS_TIMEOUT,
    WORKSPACE_DIR,
)
from programbench.skipped_tests import normalize_test_function_names, test_function_name
from programbench.container import ContainerEnvironment, remove_image
from programbench.exceptions import EmptyTestResultError, EvalStepError, XmlParseError

log = logging.getLogger(__name__)

# Branch payloads are overlaid onto the compiled workspace. If a payload brings
# its own project manifest but omits generated dependency directories, stale
# directories from the candidate submission can poison test setup. Keep this
# list conservative: only include directories that are recreated from the
# manifest and are known to cause overlay failures when stale.
_STALE_DEPENDENCY_DIRS_BY_MANIFEST: dict[str, tuple[str, ...]] = {
    "go.mod": ("vendor",),
}


_PYTEST_JOURNAL_MODULE = Path(__file__).with_name("pytest_journal.py")
_PYTEST_WATCHDOG_MODULE = Path(__file__).with_name("pytest_watchdog.py")
_PYTEST_SUPPORT_DIR = f"{WORKSPACE_DIR}/.programbench-pytest"
_PYTEST_JOURNAL_PATH = f"{_PYTEST_SUPPORT_DIR}/results.jsonl"
_PYTEST_COMPLETED_PATH = f"{_PYTEST_SUPPORT_DIR}/completed.json"

# XML 1.0 permits tab, newline, carriage return, and the ranges
# U+0020-U+D7FF/U+E000-U+FFFD. ElementTree escapes XML metacharacters but does
# not reject or escape the control characters excluded from those ranges.
_INVALID_XML_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


class _PartialTestRunError(EvalStepError):
    def __init__(self, error_code: str, error_details: str, records: dict[str, dict]):
        super().__init__(error_code, error_details)
        self.records = records


def _parse_pytest_journal(raw: str) -> dict[str, dict]:
    """Parse complete JSONL records, ignoring only a torn final write."""
    records: dict[str, dict] = {}
    lines = raw.splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except (TypeError, ValueError):
            if index == len(lines) - 1:
                break
            raise
        nodeid = record.get("nodeid")
        if isinstance(nodeid, str) and nodeid:
            records[nodeid] = record
    return records


def _xml_safe_char_replacement(match: re.Match[str]) -> str:
    codepoint = ord(match.group(0))
    if codepoint <= 0xFF:
        return f"\\x{codepoint:02x}"
    return f"\\u{codepoint:04x}"


def _sanitize_invalid_xml_chars(raw_xml: str) -> str:
    return _INVALID_XML_CHAR_RE.sub(_xml_safe_char_replacement, raw_xml)


def _pytest_journal_xml(records: dict[str, dict]) -> str:
    """Convert finalized pytest journal records to the JUnit shape used by parsing."""
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", name="programbench-partial")
    for nodeid, record in sorted(records.items()):
        parts = nodeid.split("::")
        module = parts[0]
        if module.endswith(".py"):
            module = module[:-3]
        classname = ".".join([module.replace("/", ".").replace("\\", "."), *parts[1:-1]])
        name = parts[-1]
        attributes = {"name": name}
        if classname:
            attributes["classname"] = classname
        duration = record.get("duration")
        if isinstance(duration, (int, float)):
            attributes["time"] = str(duration)
        case = ET.SubElement(suite, "testcase", attributes)
        outcome = record.get("outcome")
        phase = record.get("phase")
        message = str(record.get("message") or "")
        if outcome == "skipped":
            child = ET.SubElement(
                case,
                "skipped",
                message=message.splitlines()[0] if message else "skipped",
            )
            child.text = message
        elif outcome == "failed":
            tag = "failure" if phase == "call" else "error"
            child = ET.SubElement(
                case,
                tag,
                message=message.splitlines()[0] if message else "failed",
            )
            child.text = message
        elif outcome != "passed":
            child = ET.SubElement(case, "error", message=f"Unknown pytest outcome: {outcome}")
            child.text = message
    suite.set("tests", str(len(records)))
    return _sanitize_invalid_xml_chars(ET.tostring(root, encoding="unicode"))


def _merge_pytest_journal_xml(records: dict[str, dict], raw_xml: str | None = None) -> str:
    """Merge prior finalized checkpoints with a later attempt's JUnit XML."""
    cases: dict[str, ET.Element] = {}

    def add_cases(root: ET.Element) -> None:
        for case in root.iter("testcase"):
            key = f"{case.get('classname', '')}.{case.get('name', '')}"
            cases[key] = case

    add_cases(ET.fromstring(_pytest_journal_xml(records)))
    if raw_xml:
        add_cases(ET.fromstring(raw_xml))
    merged_root = ET.Element("testsuites")
    merged_suite = ET.SubElement(merged_root, "testsuite", name="programbench-resumed")
    for case in cases.values():
        merged_suite.append(case)
    merged_suite.set("tests", str(len(cases)))
    return ET.tostring(merged_root, encoding="unicode")


class TestResult(BaseModel):
    __test__ = False
    model_config = ConfigDict(extra="forbid")

    name: str
    branch: str = ""
    status: Literal["passed", "skipped", "failure", "error", "system_error", "not_run"]
    extra: dict

    @property
    def is_resolved(self) -> bool:
        return self.status == "passed"

    @property
    def full_name(self) -> str:
        return f"{self.branch}/{self.name}" if self.branch else self.name

    def __str__(self) -> str:
        return f"TestResult({self.full_name}, {self.status})"


class TestBranchError(BaseModel):
    __test__ = False
    model_config = ConfigDict(extra="forbid")

    error_code: str
    error_details: str


_WORKER_CRASH_PHRASE = "worker '"  # part of pytest-xdist's "worker 'gwN' crashed while running ..."
_XDIST_INTERNAL_MARKERS = ("worker_internal_error", "WorkerController")


def _is_worker_crash_case(case: ET.Element) -> bool:
    for child in case:
        if child.tag not in ("error", "failure"):
            continue
        message = (child.get("message") or "") + " " + (child.text or "")
        if "worker '" in message and "crashed" in message:
            return True
        if all(marker in message for marker in _XDIST_INTERNAL_MARKERS):
            return True
    return False


def count_worker_crashes(raw_xml: str) -> int:
    """Count testcases whose JUnit error/failure marker matches a pytest-xdist worker crash.

    A crashed-worker testcase has an ``<error>`` (or ``<failure>``) child whose
    message starts with ``failed on setup with "worker 'gwN' crashed ...``,
    or whose body text contains ``worker 'gwN' crashed while running``. We
    parse the XML rather than grep stdout because xdist mixes stdout across
    workers and the structured payload is the only authoritative signal.
    """
    if not raw_xml.strip() or (
        _WORKER_CRASH_PHRASE not in raw_xml
        and not all(marker in raw_xml for marker in _XDIST_INTERNAL_MARKERS)
    ):
        return 0
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return 0
    return sum(_is_worker_crash_case(case) for case in root.iter("testcase"))


def drop_worker_crash_cases(raw_xml: str) -> str:
    """Strip the runner pseudo-tests xdist emits for a crashed worker.

    Only safe once the crashed run's per-test outcomes have been recovered from
    the journal: the pseudo-test then adds no information the real results and
    the ``not_run`` completeness check do not already carry, while its
    unskippable name (``pytest.internal``) blocks every skip-list workflow.
    """
    root = ET.fromstring(raw_xml)
    for parent in root.iter():
        for case in [c for c in parent if c.tag == "testcase" and _is_worker_crash_case(c)]:
            parent.remove(case)
    return ET.tostring(root, encoding="unicode")


def count_testcases(raw_xml: str) -> int:
    """Total <testcase> count in the JUnit XML (0 on parse error / empty input).

    Used to surface variance across retry attempts: even if crashes stay
    non-zero, the testcase count tells us how many tests xdist actually
    managed to dispatch on each attempt.
    """
    if not raw_xml.strip():
        return 0
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return 0
    return sum(1 for _ in root.iter("testcase"))


def _process_branch_xml(
    raw_xml: str,
    branch: str,
    tests_by_branch: dict[str, list[str]],
    instance_id: str = "",
    ignored_tests: set[str] | None = None,
    branch_ignored: bool = False,
    check_completeness: bool = True,
) -> tuple[list[TestResult], list[str]]:
    """Parse JUnit XML for a branch and validate against expected test list.

    Tests whose ``branch/name`` is in *ignored_tests* are excluded from both
    the missing-from-JUnit and not-in-tests.json completeness checks. When
    *branch_ignored* is true, the entire branch is treated as out-of-scope:
    completeness checks are skipped and no warnings are emitted, but parsed
    results are still returned (the caller filters them out later). When
    *check_completeness* is false, parsed results are returned without checking
    them against ``tests.json``.
    """
    parsed = parse_test_results(raw_xml, branch=branch).test_results
    results: list[TestResult] = list(parsed)
    warnings: list[str] = []
    tag = f"[{instance_id}] branch {branch}" if instance_id else f"Branch {branch}"

    if branch_ignored or not check_completeness:
        return results, warnings

    expected = tests_by_branch.get(branch)
    if expected is None:
        log.warning("%s: no expected test list, cannot verify completeness", tag)
        warnings.append(f"{tag}: no expected test list, cannot verify completeness")
        return results, warnings

    ignored_names = {
        test_function_name(n.split("/", 1)[1])
        for n in (ignored_tests or set())
        if n.startswith(f"{branch}/")
    }
    expected_active = [n for n in expected if test_function_name(n) not in ignored_names]
    got = {t.name for t in parsed}
    missing = [name for name in expected_active if name not in got]
    if missing:
        log.warning(
            "%s: %d/%d expected tests missing from JUnit XML",
            tag,
            len(missing),
            len(expected_active),
        )
        results.extend(
            TestResult(
                name=name,
                branch=branch,
                status="not_run",
                extra={"error_code": "missing_from_junit_xml"},
            )
            for name in missing
        )
    unexpected = {name for name in got if test_function_name(name) not in ignored_names} - set(expected)
    if unexpected:
        log.warning(
            "%s: %d test(s) in JUnit XML not in tests.json",
            tag,
            len(unexpected),
        )
        warnings.append(f"{tag}: {len(unexpected)} test(s) in JUnit XML not in tests.json")

    return results, warnings


class EvaluationResult(BaseModel):
    """By default INCLUDES ALL TESTS even those ignored.
    Use the `without_ignored` method to get a copy with only the non-ignored tests.
    """

    model_config = ConfigDict(extra="forbid")

    test_results: list[TestResult] = []
    error_code: str | None = None
    error_details: str | None = None
    log: list[dict] = []
    solution_branch: str | None = None
    test_branches: list[str] = []
    test_branch_errors: dict[str, list[TestBranchError]] = {}
    executable_hash: str | None = None
    warnings: list[str] = []

    @property
    def n_system_errors(self) -> int:
        return sum(t.status == "system_error" for t in self.test_results)

    @property
    def n_resolved(self) -> int:
        return sum(test.is_resolved for test in self.test_results)

    def __len__(self) -> int:
        return len(self.test_results)

    def __iter__(self) -> Iterator[TestResult]:
        return iter(self.test_results)

    @property
    def score(self) -> float:
        if len(self) == 0:
            return 0.0
        return self.n_resolved / len(self)

    def without_ignored(self, ignored_tests: set[str]) -> "EvaluationResult":
        if not ignored_tests:
            return self
        ignored_tests = normalize_test_function_names(ignored_tests)
        return EvaluationResult(
            test_results=[
                t for t in self.test_results
                if f"{t.branch}/{test_function_name(t.name)}" not in ignored_tests
            ],
            error_code=self.error_code,
            error_details=self.error_details,
            log=self.log,
            solution_branch=self.solution_branch,
            test_branches=self.test_branches,
            test_branch_errors=self.test_branch_errors,
            executable_hash=self.executable_hash,
            warnings=self.warnings,
        )

    def for_branches(self, branches: list[str]) -> "EvaluationResult":
        """Return a copy scoped to the given test branches."""
        if sorted(self.test_branches) == sorted(branches):
            return self
        branch_set = set(branches)
        return EvaluationResult(
            test_results=[t for t in self.test_results if t.branch in branch_set],
            error_code=self.error_code,
            error_details=self.error_details,
            log=self.log,
            solution_branch=self.solution_branch,
            test_branches=branches,
            test_branch_errors={b: e for b, e in self.test_branch_errors.items() if b in branch_set},
            executable_hash=self.executable_hash,
            warnings=self.warnings,
        )

    def summarize(self) -> str:
        summary = f"EvaluationResult({self.solution_branch}: {self.score * 100:.0f}={self.n_resolved}/{len(self)}"
        if self.error_code is not None:
            summary += f", error_code={self.error_code}"
        if self.error_details is not None:
            summary += f", error_details={self.error_details}"
        if self.test_branch_errors:
            summary += f", branch_errors={list(self.test_branch_errors)}"
        if self.n_system_errors:
            summary += f", system_errors={self.n_system_errors}"
        if self.warnings:
            summary += f", warnings={len(self.warnings)}"
        summary += ")"
        return summary


class Evaluator:
    """Evaluate a solution by compiling it and running tests in a Docker container.

    Extracts submission.tar.gz into the container workspace, runs compile.sh,
    then runs each test branch's suite.
    """

    _stashed_executable = "/opt/programbench-stashed-executable-do-not-modify"
    _stashed_aux_bin = "/opt/programbench-stashed-aux-bin"
    _stashed_go_mod = "/opt/programbench-stashed-go.mod"
    _stashed_go_sum = "/opt/programbench-stashed-go.sum"
    _test_go_mod = ".programbench-test-go.mod"
    _test_go_sum = ".programbench-test-go.sum"

    def __init__(
        self,
        *,
        tests_branches: list[str],
        tests_by_branch: dict[str, list[str]] | None = None,
        ignored_tests: set[str] | None = None,
        ignored_branches: set[str] | None = None,
        image_name: str = "",
        solution_branch: str = "",
        submission_archive: Path | None = None,
        blob_dir: Path | None = None,
        remove_hashes: list[str] | None = None,
        image_tag: str = "task_patched",
        image: str = "",
        from_existing: EvaluationResult | None = None,
        instance_id: str = "",
        docker_cpus: int = DOCKER_CPUS,
        branch_cpu_requirements: dict[str, int] | None = None,
        cpu_budget: int = 0,
        compile_docker_cpus: int | None = None,
        branch_workers: int = 1,
        branch_retries: int = 1,
        check_junit_completeness: bool = True,
    ):
        self.image_name = image_name
        self.solution_branch = solution_branch
        self.submission_archive = submission_archive
        self.blob_dir = blob_dir
        self.tests_branches = tests_branches
        self.remove_hashes = remove_hashes or []
        self.image_tag = image_tag
        self.image = image or f"{image_name}:{image_tag}"
        self.tests_by_branch = tests_by_branch or {}
        self.ignored_tests = ignored_tests or set()
        self.ignored_branches = ignored_branches or set()
        self.instance_id = instance_id
        self.docker_cpus = docker_cpus
        self.branch_cpu_requirements = branch_cpu_requirements or {}
        self.cpu_budget = max(0, cpu_budget)
        self._available_branch_cpus = self.cpu_budget
        self._cpu_budget_condition = threading.Condition()
        self.compile_docker_cpus = compile_docker_cpus or docker_cpus
        self.branch_workers = max(1, branch_workers)
        self.branch_retries = max(0, branch_retries)
        self.check_junit_completeness = check_junit_completeness
        self._has_rerunfailures = False
        self._log_lock = threading.Lock()
        self._from_existing = from_existing
        if from_existing is not None:
            self._xml_by_branch: dict[str, str] = {
                entry["branch"]: entry["output"]
                for entry in from_existing.log
                if entry.get("step") == "results_read" and entry.get("returncode", -1) == 0 and "branch" in entry
            }
            self.result = EvaluationResult(
                solution_branch=from_existing.solution_branch or solution_branch,
                test_branches=tests_branches,
                log=from_existing.log,
                executable_hash=from_existing.executable_hash,
                test_branch_errors=from_existing.test_branch_errors,
            )
        else:
            self.result = EvaluationResult(
                solution_branch=solution_branch,
                test_branches=tests_branches,
            )

    def _add_branch_error(self, branch: str, error_code: str, error_details: str = "") -> None:
        self.result.test_branch_errors.setdefault(branch, []).append(
            TestBranchError(error_code=error_code, error_details=error_details)
        )

    def _inject_not_run(self, branch: str, error_code: str) -> None:
        tests = self.tests_by_branch.get(branch, [])
        if not tests:
            msg = f"No expected test list for branch {branch}, cannot inject not_run results"
            log.warning(msg)
            if branch not in self.result.test_branch_errors:
                self._add_branch_error(branch, "no_expected_test_list", msg)
            return
        self.result.test_results.extend(
            TestResult(
                name=name,
                branch=branch,
                status="not_run",
                extra={"error_code": error_code},
            )
            for name in tests
        )

    def _run_step(
        self,
        command: str,
        *,
        env: ContainerEnvironment,
        log_buf: list[dict],
        step_name: str,
        accept_failure: bool = False,
        timeout: int = 20,
    ) -> dict:
        log.debug("Running step: %s", command)
        t0 = time.monotonic()
        r = env.execute(command, timeout=timeout)
        wall_time = time.monotonic() - t0
        log_buf.append({"step": step_name, "command": command, "wall_time": wall_time, **r})
        phase_log = log.info if step_name in {"compile", "run_tests"} else log.debug
        phase_log(
            "Evaluation phase instance=%s solution=%s step=%s wall=%.3fs returncode=%s "
            "compile_cpus=%d configured_evaluation_cpus=%d branch_workers=%d",
            self.instance_id, self.result.solution_branch, step_name, wall_time, r["returncode"],
            self.compile_docker_cpus, self.docker_cpus, self.branch_workers,
        )
        if r["returncode"] != 0:
            error_code = f"{step_name}_failed"
            if accept_failure:
                log.debug(
                    "%s (exit %d, accepted): %s",
                    error_code,
                    r["returncode"],
                    r["output"],
                )
            else:
                log.debug("%s (exit %d): %s", error_code, r["returncode"], r["output"])
                raise EvalStepError(error_code, r["output"].strip())
        else:
            log.debug("Output: %s", r["output"])
        return r

    def _copy_file_from_container(
        self,
        *,
        env: ContainerEnvironment,
        log_buf: list[dict],
        container_path: str,
        step_name: str,
        timeout: int = 60,
    ) -> str:
        """Copy a file out of the container via ``docker cp`` and return its contents.

        Bypasses bash so login-shell stderr (``mesg: ttyname failed`` etc.) can't
        pollute the bytes the way ``cat <file>`` would. Logs to ``log_buf`` with
        the same shape as ``_run_step``; on success the entry's ``output`` holds
        the file contents so ``from_existing`` replay keeps working.
        """
        host_tmp = Path(tempfile.mkstemp(suffix=Path(container_path).suffix or ".out")[1])
        cmd_list = [env.executable, "cp", f"{env.container_id}:{container_path}", str(host_tmp)]
        cmd_str = " ".join(cmd_list)
        log.debug("Running step: %s", cmd_str)
        t0 = time.monotonic()
        try:
            try:
                cp = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
                rc = cp.returncode
                err = (cp.stdout + cp.stderr).strip()
            except subprocess.TimeoutExpired:
                rc, err = -1, f"docker cp timed out after {timeout}s"
            wall_time = time.monotonic() - t0
            if rc != 0:
                log_buf.append(
                    {
                        "step": step_name,
                        "command": cmd_str,
                        "wall_time": wall_time,
                        "output": err,
                        "returncode": rc,
                        "exception_info": "",
                    }
                )
                raise EvalStepError(f"{step_name}_failed", err)
            contents = host_tmp.read_text()
            log_buf.append(
                {
                    "step": step_name,
                    "command": cmd_str,
                    "wall_time": wall_time,
                    "output": contents,
                    "returncode": 0,
                    "exception_info": "",
                }
            )
            return contents
        finally:
            host_tmp.unlink(missing_ok=True)

    def _new_env(self, image: str, *, serial_pytest: bool = False, cpus: int | None = None) -> ContainerEnvironment:
        # Baseline xdist hardening that always works (xdist ships with
        # every test image): replace up to N crashed workers per branch so
        # a single OOM doesn't drop the rest of that worker's queue.
        # --reruns is added on top in _run_test_branch when
        # pytest-rerunfailures was successfully installed during compile.
        #
        # Keep `pytest -n auto` aligned with the container CPU allocation.
        # Docker CPU quotas do not necessarily affect Python's os.cpu_count(),
        # so leaving this unset can make xdist use the host's full CPU count.
        # Serial retries continue to force a single worker.
        effective_cpus = cpus or self.docker_cpus
        pytest_workers = 1 if serial_pytest else effective_cpus
        addopts = "--max-worker-restart=4"
        env = {
            "PYTEST_ADDOPTS": addopts,
            "PYTEST_XDIST_AUTO_NUM_WORKERS": str(pytest_workers),
            # Parallelize across tests, avoiding host-sized OpenMP teams inside
            # each test under a much smaller Docker CPU quota.
            "OMP_NUM_THREADS": "1",
            # Evaluation may intentionally use a Codex-enabled image, but it
            # must never inherit credentials or activate an agent session.
            "OPENAI_API_KEY": "",
            "CODEX_HOME": "/root/.codex",
        }
        return ContainerEnvironment(
            image=image,
            cwd=WORKSPACE_DIR,
            executable=DOCKER_EXECUTABLE,
            timeout=600,
            cpus=effective_cpus,
            env=env,
            run_args=[
                *DOCKER_RUN_ARGS,
                *EVAL_NETWORK_ARGS,
                "--init",
                "--tmpfs",
                "/root/.codex:rw,noexec,nosuid,nodev,size=1m",
            ],
        )

    def _branch_cpus(self, branch: str) -> int:
        requested = max(1, self.branch_cpu_requirements.get(branch, self.docker_cpus))
        return min(requested, self.cpu_budget) if self.cpu_budget > 0 else requested

    def _acquire_branch_cpus(self, branch: str) -> int:
        cpus = self._branch_cpus(branch)
        if self.cpu_budget <= 0:
            return cpus
        with self._cpu_budget_condition:
            while cpus > self._available_branch_cpus:
                self._cpu_budget_condition.wait()
            self._available_branch_cpus -= cpus
        return cpus

    def _release_branch_cpus(self, cpus: int) -> None:
        if self.cpu_budget <= 0:
            return
        with self._cpu_budget_condition:
            self._available_branch_cpus += cpus
            self._cpu_budget_condition.notify_all()

    def _remove_hashed_files(self, env: ContainerEnvironment, log_buf: list[dict]) -> None:
        if not self.remove_hashes:
            return
        hashes_pattern = "|".join(self.remove_hashes)
        self._run_step(
            f"find {WORKSPACE_DIR} -type f -exec sha256sum {{}} + 2>/dev/null"
            f' | grep -E "^({hashes_pattern})  " | cut -c67- | xargs -I% rm -fv %',
            env=env,
            log_buf=log_buf,
            step_name="remove_hashed_files",
            accept_failure=True,
        )

    def _compile_executable(self, env: ContainerEnvironment, log_buf: list[dict]) -> None:
        """Wipe workspace, stream submission archive in, run compile.sh."""
        self._run_step(
            f"rm -rf {WORKSPACE_DIR}/* {WORKSPACE_DIR}/.[!.]*",
            env=env,
            log_buf=log_buf,
            step_name="wipe_workspace",
            timeout=300,
        )
        assert self.submission_archive is not None
        env.copy_in_tar(self.submission_archive, f"{WORKSPACE_DIR}/")
        self._remove_hashed_files(env, log_buf)
        # Seed a synthetic git repo if the submission didn't ship one. Build
        # scripts that depend on a working tree (jq submodules, calcurse's
        # autopoint, cargo+vergen, ...) succeed against this synthetic repo.
        # The legacy RevEngBench gold pipeline got this for free via
        # `git clone <upstream>`; here we approximate it locally.
        #
        # Fixed author/committer identity AND dates make the synthetic commit
        # deterministic: same submission tree → same commit SHA across runs.
        # Without this, build scripts that embed the SHA into the binary
        # (vergen for cargo, gitversion-via-make, ...) produce a different
        # executable_hash each run, so otherwise-byte-identical builds fail
        # to match across pipelines.
        self._run_step(
            "if [ ! -d .git ]; then "
            "GIT_AUTHOR_DATE='2000-01-01T00:00:00Z' "
            "GIT_COMMITTER_DATE='2000-01-01T00:00:00Z' "
            "git -c init.defaultBranch=gold init -q && "
            "git -c user.email=gold@local -c user.name=gold "
            "-c commit.gpgsign=false add -A && "
            "GIT_AUTHOR_DATE='2000-01-01T00:00:00Z' "
            "GIT_COMMITTER_DATE='2000-01-01T00:00:00Z' "
            "git -c user.email=gold@local -c user.name=gold "
            "-c commit.gpgsign=false commit -q --allow-empty -m gold; "
            "fi",
            env=env,
            log_buf=log_buf,
            step_name="seed_git",
        )
        self._run_step(
            "chmod +x ./compile.sh && ./compile.sh",
            env=env,
            log_buf=log_buf,
            step_name="compile",
            timeout=900,
        )
        self._run_step(
            f"mv ./executable {self._stashed_executable}",
            env=env,
            log_buf=log_buf,
            step_name="copy_executable",
            timeout=300,
        )
        r = self._run_step(
            f"sha256sum {self._stashed_executable}",
            env=env,
            log_buf=log_buf,
            step_name="hash_executable",
            timeout=300,
        )
        self.result.executable_hash = r["output"].split()[0]
        # Best-effort: install pytest-rerunfailures so per-test reruns can
        # absorb flakes inside a single branch run. Installing during compile
        # bakes it into the committed image so per-branch containers inherit
        # it without re-installing. Failures are accepted (no pip3, no
        # network, ...): we just don't get --reruns and rely on
        # --max-worker-restart + branch_retries.
        rerun_install = self._run_step(
            "pip3 install -q --disable-pip-version-check pytest-rerunfailures",
            env=env,
            log_buf=log_buf,
            step_name="install_rerunfailures",
            accept_failure=True,
            timeout=120,
        )
        self._has_rerunfailures = rerun_install["returncode"] == 0

    def _stash_auxiliary_executables(self, env: ContainerEnvironment, log_buf: list[dict]) -> None:
        """Preserve compiled cmd/<name>/<name> tools before tests overlay source files."""
        self._run_step(
            f"rm -rf {self._stashed_aux_bin} && mkdir -p {self._stashed_aux_bin}; "
            "if [ -d ./cmd ]; then "
            "for f in ./cmd/*/*; do "
            "[ -f \"$f\" ] && [ -x \"$f\" ] || continue; "
            "name=${f##*/}; parent=${f%/*}; parent=${parent##*/}; "
            "[ \"$name\" = \"$parent\" ] || continue; "
            f"cp -f \"$f\" \"{self._stashed_aux_bin}/$name\"; "
            "done; "
            "fi",
            env=env,
            log_buf=log_buf,
            step_name="stash_auxiliary_executables",
            timeout=120,
        )

    def _restore_executable(self, env: ContainerEnvironment, log_buf: list[dict]) -> None:
        if self.result.executable_hash is None:
            raise EvalStepError("no_executable_hash", "Executable hash not found")
        self._run_step(
            f"rm -f ./executable && mv {self._stashed_executable} ./executable && chmod +x ./executable",
            env=env,
            log_buf=log_buf,
            step_name="restore_executable",
            timeout=300,
        )
        r = self._run_step(
            "sha256sum ./executable",
            env=env,
            log_buf=log_buf,
            step_name="verify_executable_hash",
            timeout=300,
        )
        current_hash = r["output"].split()[0]
        if current_hash != self.result.executable_hash:
            raise EvalStepError(
                "executable_hash_mismatch",
                f"expected {self.result.executable_hash}, got {current_hash}",
            )

    def _restore_go_module_files_for_test_payload(
        self, payload: Path, env: ContainerEnvironment, log_buf: list[dict]
    ) -> None:
        if "go.mod" not in self._test_payload_top_level_paths(payload):
            return
        self._run_step(
            f"if [ -f {self._stashed_go_mod} ]; then "
            f"cp {self._stashed_go_mod} ./go.mod; "
            f"if [ -f {self._stashed_go_sum} ]; then cp {self._stashed_go_sum} ./go.sum; else rm -f ./go.sum; fi; "
            "fi",
            env=env,
            log_buf=log_buf,
            step_name="restore_go_module_files",
            timeout=60,
        )

    def _stash_test_go_module_files_for_test_payload(
        self, payload: Path, env: ContainerEnvironment, log_buf: list[dict]
    ) -> None:
        if "go.mod" not in self._test_payload_top_level_paths(payload):
            return
        self._run_step(
            f"cp ./go.mod {self._test_go_mod}; "
            f"if [ -f ./go.sum ]; then cp ./go.sum {self._test_go_sum}; else rm -f {self._test_go_sum}; fi",
            env=env,
            log_buf=log_buf,
            step_name="stash_test_go_module_files",
            timeout=60,
        )

    def _prepare_workspace_bin(self, env: ContainerEnvironment, log_buf: list[dict]) -> None:
        self._run_step(
            "mkdir -p .programbench-bin && "
            "for f in ./*; do "
            "[ -f \"$f\" ] && [ -x \"$f\" ] || continue; "
            "name=${f#./}; "
            "[ \"$name\" = compile.sh ] && continue; "
            "ln -sf \"$PWD/$name\" \".programbench-bin/$name\"; "
            "done; "
            "real_go=$(command -v go || true); "
            "if [ -n \"$real_go\" ]; then "
            "cat > .programbench-bin/go <<'PROGRAMBENCH_GO_WRAPPER'\n"
            "#!/bin/sh\n"
            "real_go=\"__PROGRAMBENCH_REAL_GO__\"\n"
            "if [ \"$1\" = build ] && [ -f /workspace/go.mod ]; then\n"
            "  out=\n"
            "  prev=\n"
            "  for arg in \"$@\"; do\n"
            "    if [ \"$prev\" = -o ]; then out=$arg; prev=; continue; fi\n"
            "    if [ \"$arg\" = -o ]; then prev=-o; continue; fi\n"
            "    case \"$arg\" in\n"
            "      ./cmd/*)\n"
            "        bin=${arg##*/}\n"
            "        prebuilt=/workspace/$bin\n"
            "        if [ -n \"$out\" ] && [ -x \"$prebuilt\" ]; then\n"
            "          case \"$out\" in\n"
            "            /*) out_abs=$out ;;\n"
            "            ./*) out_abs=$PWD/${out#./} ;;\n"
            "            *) out_abs=$PWD/$out ;;\n"
            "          esac\n"
            "          if [ \"$out_abs\" != \"$prebuilt\" ]; then\n"
            "            cp \"$prebuilt\" \"$out\" || exit 1\n"
            "            chmod +x \"$out\"\n"
            "          fi\n"
            "          exit 0\n"
            "        fi\n"
            "        ;;\n"
            "    esac\n"
            "  done\n"
            "fi\n"
            "if [ \"$1\" = build ] && [ -f /workspace/.programbench-test-go.mod ]; then\n"
            "  for arg in \"$@\"; do\n"
            "    case \"$arg\" in\n"
            "      ./cmd/*)\n"
            "        rel=${arg#./}\n"
            "        if [ -e \"$arg\" ] || [ -e \"/workspace/$rel\" ]; then\n"
            "          old_pwd=$PWD\n"
            "          if [ ! -e \"$arg\" ] && [ -e \"/workspace/$rel\" ]; then cd /workspace || exit 1; fi\n"
            "          tmp_dir=$(mktemp -d)\n"
            "          [ -f /workspace/go.mod ] && cp /workspace/go.mod \"$tmp_dir/candidate-go.mod\"\n"
            "          [ -f /workspace/go.sum ] && cp /workspace/go.sum \"$tmp_dir/candidate-go.sum\"\n"
            "          cp /workspace/.programbench-test-go.mod /workspace/go.mod\n"
            "          if [ -f /workspace/.programbench-test-go.sum ]; then cp /workspace/.programbench-test-go.sum /workspace/go.sum; else rm -f /workspace/go.sum; fi\n"
            "          \"$real_go\" \"$@\"\n"
            "          status=$?\n"
            "          if [ -f \"$tmp_dir/candidate-go.mod\" ]; then cp \"$tmp_dir/candidate-go.mod\" /workspace/go.mod; else rm -f /workspace/go.mod; fi\n"
            "          if [ -f \"$tmp_dir/candidate-go.sum\" ]; then cp \"$tmp_dir/candidate-go.sum\" /workspace/go.sum; else rm -f /workspace/go.sum; fi\n"
            "          rm -rf \"$tmp_dir\"\n"
            "          cd \"$old_pwd\" || exit 1\n"
            "          exit $status\n"
            "        fi\n"
            "        ;;\n"
            "    esac\n"
            "  done\n"
            "fi\n"
            "if [ \"$1\" = build ] && [ \"$PWD\" != /workspace ] && [ -f /workspace/go.mod ]; then\n"
            "  for arg in \"$@\"; do\n"
            "    case \"$arg\" in\n"
            "      ./*)\n"
            "        rel=${arg#./}\n"
            "        if [ ! -e \"$arg\" ] && [ -e \"/workspace/$rel\" ]; then\n"
            "          cd /workspace || exit 1\n"
            "          exec \"$real_go\" \"$@\"\n"
            "        fi\n"
            "        ;;\n"
            "    esac\n"
            "  done\n"
            "fi\n"
            "exec \"$real_go\" \"$@\"\n"
            "PROGRAMBENCH_GO_WRAPPER\n"
            "sed -i \"s#__PROGRAMBENCH_REAL_GO__#$real_go#g\" .programbench-bin/go; "
            "chmod +x .programbench-bin/go; "
            "fi",
            env=env,
            log_buf=log_buf,
            step_name="prepare_workspace_bin",
            timeout=60,
        )

    def _get_xml_from_log(self, branch: str) -> str:
        if branch in self._xml_by_branch:
            return self._xml_by_branch[branch]
        errors = self._from_existing.test_branch_errors.get(branch, [])
        if errors:
            self.result.test_branch_errors[branch] = list(errors)
        raise EvalStepError(
            errors[0].error_code if errors else "no_results_in_log",
            errors[0].error_details if errors else "",
        )

    def _test_tar_for_branch(self, branch: str) -> Path:
        if self.blob_dir is None:
            raise EvalStepError("missing_test_blobs", "No test blob directory is configured")
        candidates = [
            self.blob_dir / "tests" / f"{branch}.tar.gz",
            self.blob_dir / f"{branch}.tar.gz",
            self.blob_dir / "tests" / branch,
            self.blob_dir / branch,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise EvalStepError(
            "missing_test_blob",
            f"No test payload for branch {branch} under {self.blob_dir}",
        )

    def _test_payload_top_level_paths(self, payload: Path) -> set[str]:
        if payload.is_dir():
            return {child.name for child in payload.iterdir()}
        names: set[str] = set()
        with tarfile.open(payload, "r:*") as archive:
            for member in archive:
                name = member.name.lstrip("./")
                if name:
                    names.add(name.split("/", 1)[0])
        return names

    def _clean_workspace_for_test_payload(self, payload: Path, env: ContainerEnvironment, log_buf: list[dict]) -> None:
        top_level = self._test_payload_top_level_paths(payload)
        stale_dirs = sorted(
            dep_dir
            for manifest, dep_dirs in _STALE_DEPENDENCY_DIRS_BY_MANIFEST.items()
            if manifest in top_level
            for dep_dir in dep_dirs
            if dep_dir not in top_level
        )
        if not stale_dirs:
            return
        self._run_step(
            "rm -rf " + " ".join(stale_dirs),
            env=env,
            log_buf=log_buf,
            step_name="clean_stale_dependency_dirs",
            accept_failure=True,
            timeout=60,
        )

    def _run_test_branch(
        self,
        branch: str,
        image: str,
        log_buf: list[dict],
        *,
        serial_pytest: bool = False,
        completed_nodeids: set[str] | None = None,
        recover_journal: bool = False,
    ) -> str:
        """Spin up a fresh container from `image`, run one branch's tests, return XML.

        Steps are appended to ``log_buf`` as they run, so a partial log survives
        an EvalStepError raised mid-way (caller still sees what executed).

        When ``serial_pytest`` is True, the container forces xdist to one
        worker via PYTEST_XDIST_AUTO_NUM_WORKERS=1. Used on retry after a
        worker crash so the same OOM/contention pattern doesn't repeat.

        When ``recover_journal`` is True and the run still ends in a worker
        crash, the branch's real outcomes are read back from the incremental
        journal instead of being thrown away with the crashed session.
        """
        branch_cpus = self._acquire_branch_cpus(branch)
        env: ContainerEnvironment | None = None
        try:
            env = self._new_env(image, serial_pytest=serial_pytest, cpus=branch_cpus)
            log_start = len(log_buf)
            # The submission contract exposes only the compiled executable to
            # tests. Candidate sources and build artefacts must not leak into or
            # overwrite the reference-test payload.
            self._run_step(
                f"rm -rf {WORKSPACE_DIR}/* {WORKSPACE_DIR}/.[!.]*",
                env=env,
                log_buf=log_buf,
                step_name="wipe_workspace_for_tests",
                timeout=300,
            )
            test_payload = self._test_tar_for_branch(branch)
            if test_payload.is_dir():
                env.copy_in(test_payload, f"{WORKSPACE_DIR}/")
            else:
                env.copy_in_tar(test_payload, f"{WORKSPACE_DIR}/")
            self._restore_executable(env, log_buf)
            self._prepare_workspace_bin(env, log_buf)
            self._run_step(
                f"rm -rf {_PYTEST_SUPPORT_DIR} && mkdir -p {_PYTEST_SUPPORT_DIR}",
                env=env,
                log_buf=log_buf,
                step_name="prepare_pytest_journal",
                timeout=60,
            )
            env.copy_in(_PYTEST_JOURNAL_MODULE, f"{_PYTEST_SUPPORT_DIR}/pytest_journal.py")
            env.copy_in(_PYTEST_WATCHDOG_MODULE, f"{_PYTEST_SUPPORT_DIR}/pytest_watchdog.py")
            # PYTEST_PLUGINS makes pytest import pytest_journal before it runs a
            # single test, so a run.sh that sets `PYTHONPATH=. pytest ...` (many
            # generated ones do) drops the support dir from sys.path and kills
            # the whole branch with ModuleNotFoundError. A .pth in site-packages
            # is read by `site` at interpreter startup regardless of PYTHONPATH.
            self._run_step(
                "python3 -c \"import site, pathlib; "
                f"[pathlib.Path(d, 'programbench-pytest-journal.pth').write_text('{_PYTEST_SUPPORT_DIR}')"
                ' for d in site.getsitepackages() if pathlib.Path(d).is_dir()]"',
                env=env,
                log_buf=log_buf,
                step_name="install_pytest_journal_path",
                accept_failure=True,
                timeout=60,
            )
            if completed_nodeids:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as completed_file:
                    json.dump(sorted(completed_nodeids), completed_file)
                    completed_file.flush()
                    env.copy_in(Path(completed_file.name), _PYTEST_COMPLETED_PATH)
            self._run_step(
                "rm -f eval/results.xml results.xml",
                env=env,
                log_buf=log_buf,
                step_name="clean_stale_results",
                timeout=120,
            )
            # Rewrite pytest-timeout's `--timeout-method=thread` (default in every
            # generated run.sh we've seen) to `signal`. With `thread`, when a
            # test exceeds its timeout pytest-timeout calls os._exit(1) on the
            # whole worker, which xdist reports as "worker 'gwN' crashed" and
            # silently drops the worker's pre-queued tests. With `signal` it
            # delivers SIGALRM, pytest catches it cleanly, and the test gets a
            # proper `subprocess.TimeoutExpired` failure entry — no worker
            # crash, no queue loss, identical results in parallel and serial.
            self._run_step(
                "test -f eval/run.sh && sed -i 's/--timeout-method=thread/--timeout-method=signal/g' eval/run.sh || true",
                env=env,
                log_buf=log_buf,
                step_name="patch_timeout_method",
                accept_failure=True,
                timeout=10,
            )
            run_cmd = (
                f'export PYTHONPATH="{_PYTEST_SUPPORT_DIR}:$PYTHONPATH"; '
                'export PYTEST_PLUGINS="${PYTEST_PLUGINS:+$PYTEST_PLUGINS,}pytest_journal,pytest_watchdog"; '
                f'export PROGRAMBENCH_SUBPROCESS_TIMEOUT="{EVAL_SUBPROCESS_TIMEOUT}"; '
                f'export PROGRAMBENCH_PYTEST_JOURNAL="{_PYTEST_JOURNAL_PATH}"; '
                f'export PROGRAMBENCH_PYTEST_COMPLETED="{_PYTEST_COMPLETED_PATH}"; '
                + PIN_EVAL_PIP_VERSIONS
                + 'PATH="$PWD/.programbench-bin:$PATH"; chmod +x ./eval/run.sh && ./eval/run.sh'
            )
            if self._has_rerunfailures:
                # Tighten flake recovery inside one run: pytest-rerunfailures
                # retries individual failed tests up to 2x with a 1s delay.
                # Augmenting at exec time (not container creation) lets us
                # re-use the committed image for every branch.
                run_cmd = 'export PYTEST_ADDOPTS="$PYTEST_ADDOPTS --reruns=2 --reruns-delay=1" && ' + run_cmd
            run_result = self._run_step(
                run_cmd,
                env=env,
                log_buf=log_buf,
                step_name="run_tests",
                accept_failure=True,
                timeout=3600,
            )
            if run_result.get("exception_info"):
                details = run_result["exception_info"]
                output = run_result.get("output", "").strip()
                if output:
                    details = f"{details}\n{output}"
                records: dict[str, dict] = {}
                try:
                    journal = self._copy_file_from_container(
                        env=env,
                        log_buf=log_buf,
                        container_path=_PYTEST_JOURNAL_PATH,
                        step_name="partial_results_read",
                        timeout=60,
                    )
                    records = _parse_pytest_journal(journal)
                except (EvalStepError, TypeError, ValueError):
                    log.warning("Could not recover partial pytest results for branch %s", branch)
                raise _PartialTestRunError("run_tests_timeout", details, records)
            try:
                xml = self._copy_file_from_container(
                    env=env,
                    log_buf=log_buf,
                    container_path=f"{WORKSPACE_DIR}/eval/results.xml",
                    step_name="results_read",
                    timeout=60,
                )
            except EvalStepError as e:
                # A missing results.xml means the run failed whatever pytest exited
                # with: a plugin that fails to load exits 1, which run.sh wrappers
                # routinely treat as "tests ran and failed" and mask as success.
                raise EvalStepError(
                    "run_tests_failed_no_results", run_result["output"].strip() or e.error_details
                ) from e
            # An xdist worker that dies mid-session (pytest-timeout's SIGALRM
            # landing inside pytest's own report formatting is the usual cause)
            # takes the controller down with it, and results.xml is left holding
            # nothing but the `pytest.internal` stub — every test the branch had
            # already finished is gone. The journal recorded each of them as it
            # finalized, so rebuild the branch from those records once retrying
            # has stopped paying off; tests that never finalized still surface
            # as `not_run` through the completeness check.
            if recover_journal and count_worker_crashes(xml):
                try:
                    records = _parse_pytest_journal(
                        self._copy_file_from_container(
                            env=env,
                            log_buf=log_buf,
                            container_path=_PYTEST_JOURNAL_PATH,
                            step_name="crash_results_read",
                            timeout=60,
                        )
                    )
                except (EvalStepError, TypeError, ValueError):
                    log.warning("Could not recover crashed pytest results for branch %s", branch)
                    records = {}
                if records:
                    log.info(
                        "Branch %s: recovered %d test(s) from the journal after a worker crash",
                        branch,
                        len(records),
                    )
                    xml = _merge_pytest_journal_xml(records, drop_worker_crash_cases(xml))
            return xml
        finally:
            if env is not None:
                for entry in log_buf[log_start:]:
                    entry.setdefault("branch", branch)
                env.cleanup()
            self._release_branch_cpus(branch_cpus)

    def _evaluate_branch(self, branch: str, image: str) -> None:
        """Run one branch and merge results/log/errors into self.result under the lock.

        On the live path (no ``from_existing``), retries the branch up to
        ``branch_retries`` times after pytest timeouts or pytest-xdist worker
        crashes. Timeout retries run in a fresh container and deselect node IDs
        already finalized in the incremental journal. The best
        attempt (fewest crashes; if tied, the last) is kept.
        """
        tag = f"[{self.instance_id}] branch {branch}" if self.instance_id else f"Branch {branch}"
        local_log: list[dict] = []
        attempts_left = self.branch_retries if self._from_existing is None else 0
        best_xml: str | None = None
        best_crashes = 0
        best_n_tests = 0
        serial_retry = False  # flips on after the first attempt that saw a crash
        attempt_history: list[tuple[int, int]] = []  # (crashes, total testcases) per attempt
        journal_records: dict[str, dict] = {}
        terminal_error: EvalStepError | None = None
        while True:
            attempt_log: list[dict] = []
            try:
                if self._from_existing is not None:
                    raw_xml = self._get_xml_from_log(branch)
                else:
                    raw_xml = self._run_test_branch(
                        branch,
                        image,
                        attempt_log,
                        serial_pytest=serial_retry,
                        completed_nodeids=set(journal_records),
                        recover_journal=attempts_left <= 0,
                    )
            except EvalStepError as e:
                if isinstance(e, _PartialTestRunError) and e.records:
                    previous_count = len(journal_records)
                    journal_records.update(e.records)
                    log.info(
                        "%s: preserved %d finalized test(s) after timeout (%d new)",
                        tag,
                        len(journal_records),
                        len(journal_records) - previous_count,
                    )
                local_log.extend(attempt_log)
                if best_xml is not None:
                    # We already have a usable attempt; add any later timeout checkpoints.
                    raw_xml = _merge_pytest_journal_xml(journal_records, best_xml) if journal_records else best_xml
                    break
                if attempts_left <= 0:
                    log.warning("%s failed (%s), continuing with remaining branches", tag, e.error_code)
                    if journal_records:
                        terminal_error = e
                        raw_xml = _merge_pytest_journal_xml(journal_records)
                        break
                    with self._log_lock:
                        if local_log:
                            self.result.log.extend(local_log)
                        if branch not in self.result.test_branch_errors:
                            self._add_branch_error(branch, e.error_code, e.error_details)
                        self._inject_not_run(branch, e.error_code)
                    return
                log.warning("%s: attempt failed (%s); retrying (%d left)", tag, e.error_code, attempts_left)
                attempts_left -= 1
                continue

            if journal_records:
                raw_xml = _merge_pytest_journal_xml(journal_records, raw_xml)
            local_log.extend(attempt_log)
            crashes = count_worker_crashes(raw_xml)
            n_tests = count_testcases(raw_xml)
            attempt_history.append((crashes, n_tests))
            # "Best" = most non-crashed testcases. This balances both failure
            # modes: parallel mode that keeps a few crashes but reports the
            # full test list (1/131 → 130 useful) usually beats serial mode
            # that has zero crashes but loses tests entirely (0/83 → 83
            # useful). When serial mode does deliver more usable tests
            # (contention cases), it wins on its own merit.
            useful = n_tests - crashes
            if best_xml is None or useful > best_n_tests - best_crashes:
                best_xml = raw_xml
                best_crashes = crashes
                best_n_tests = n_tests
            # Early exit when retries stop producing new information: two
            # consecutive attempts with identical (crashes, n_tests) means
            # the failure is deterministic, not contention-driven, and
            # further retries will just burn time.
            deterministic = len(attempt_history) >= 2 and attempt_history[-1] == attempt_history[-2]
            if crashes == 0 or attempts_left <= 0 or deterministic:
                raw_xml = best_xml
                if len(attempt_history) > 1:
                    seq = ", ".join(f"{c}/{n}" for c, n in attempt_history)
                    if best_crashes == 0:
                        log.info(
                            "%s: recovered after %d retr%s — crashes/tests by attempt: %s",
                            tag,
                            len(attempt_history) - 1,
                            "y" if len(attempt_history) == 2 else "ies",
                            seq,
                        )
                    else:
                        crash_counts = [c for c, _ in attempt_history]
                        n_counts = [n for _, n in attempt_history]
                        useful_counts = [n - c for c, n in attempt_history]
                        early = (
                            " (stopped early — last 2 attempts identical)"
                            if deterministic and attempts_left > 0
                            else ""
                        )
                        log.warning(
                            "%s: did not fully recover after %d retr%s%s — kept best-of-%d "
                            "with %d crashes / %d useful tests (crashes by attempt: %s; "
                            "tests by attempt: %s, useful: %s, min=%d max=%d spread=%d)",
                            tag,
                            len(attempt_history) - 1,
                            "y" if len(attempt_history) == 2 else "ies",
                            early,
                            len(attempt_history),
                            best_crashes,
                            best_n_tests - best_crashes,
                            crash_counts,
                            n_counts,
                            useful_counts,
                            min(n_counts),
                            max(n_counts),
                            max(n_counts) - min(n_counts),
                        )
                break
            log.warning(
                "%s: %d xdist worker crash(es) detected (testcases=%d); retrying serially (%d left)",
                tag,
                crashes,
                n_tests,
                attempts_left,
            )
            serial_retry = True
            attempts_left -= 1
        incomplete_error: EvalStepError | TestBranchError | None = terminal_error
        if incomplete_error is None and self.result.test_branch_errors.get(branch):
            incomplete_error = self.result.test_branch_errors[branch][0]
        if journal_records:
            local_log.append({
                "step": "results_read",
                "command": "merge incremental pytest results",
                "wall_time": 0.0,
                "output": raw_xml,
                "returncode": 0,
                "exception_info": "",
                "branch": branch,
            })
        results, warnings = _process_branch_xml(
            raw_xml,
            branch,
            self.tests_by_branch,
            self.instance_id,
            ignored_tests=self.ignored_tests,
            branch_ignored=branch in self.ignored_branches,
            check_completeness=self.check_junit_completeness or incomplete_error is not None,
        )
        if incomplete_error is not None:
            for result in results:
                if result.status == "not_run" and result.extra.get("error_code") == "missing_from_junit_xml":
                    result.extra["error_code"] = incomplete_error.error_code
        with self._log_lock:
            if local_log:
                self.result.log.extend(local_log)
            if terminal_error is not None and branch not in self.result.test_branch_errors:
                self._add_branch_error(branch, terminal_error.error_code, terminal_error.error_details)
            self.result.test_results.extend(results)
            self.result.warnings.extend(warnings)

    def run(self) -> EvaluationResult:
        """Run the full evaluation pipeline."""
        committed_image: str | None = None
        compile_env: ContainerEnvironment | None = None
        try:
            if self._from_existing is None:
                compile_env = self._new_env(self.image, cpus=self.compile_docker_cpus)
                try:
                    self._compile_executable(compile_env, self.result.log)
                except EvalStepError as e:
                    self.result.error_code = e.error_code
                    self.result.error_details = e.error_details
                    for branch in self.tests_branches:
                        self._inject_not_run(branch, e.error_code)
                    log.debug(self.result.summarize())
                    return self.result
                committed_image = f"programbench-compiled/{self.instance_id or 'instance'}:{uuid.uuid4().hex[:12]}"
                compile_env.commit(committed_image)
                # Tear down compile container; per-branch containers come from the committed image.
                compile_env.cleanup()
                compile_env = None
            elif self._from_existing.error_code:
                self.result.error_code = self._from_existing.error_code
                self.result.error_details = self._from_existing.error_details
                for branch in self.tests_branches:
                    self._inject_not_run(branch, self._from_existing.error_code)
                log.debug(self.result.summarize())
                return self.result

            assert committed_image is not None or self._from_existing is not None
            image_for_branches = committed_image or ""

            if self.branch_workers > 1 and self._from_existing is None:
                with ThreadPoolExecutor(max_workers=self.branch_workers) as pool:
                    futures = {
                        pool.submit(self._evaluate_branch, branch, image_for_branches): branch
                        for branch in self.tests_branches
                    }
                    for future in as_completed(futures):
                        future.result()
            else:
                for branch in self.tests_branches:
                    self._evaluate_branch(branch, image_for_branches)

            log.debug(self.result.summarize())
            return self.result
        finally:
            if compile_env is not None:
                compile_env.cleanup()
            if committed_image is not None:
                remove_image(committed_image, executable=DOCKER_EXECUTABLE)


def parse_test_results(results_xml: str, branch: str = "") -> EvaluationResult:
    """Parse JUnit XML test results into an EvaluationResult."""
    if not results_xml.strip():
        raise EmptyTestResultError(f"Empty test results XML for branch {branch!r}")
    try:
        root = ET.fromstring(results_xml)
    except ET.ParseError as e:
        raise XmlParseError(
            f"Malformed test results XML for branch {branch!r}: {e} "
            f"(len={len(results_xml)}, tail={results_xml[-200:]!r})"
        ) from e
    xml = JUnitXml.fromroot(root)

    # Keep only the final attempt for each logical test. pytest-rerunfailures 16
    # can emit earlier attempts either as <rerunFailure> children or as duplicate,
    # result-free <testcase> elements, depending on the pytest version.
    test_results_by_name: dict[str, TestResult] = {}
    reruns: Counter[str] = Counter()
    for suite in xml:
        for case in suite:
            raw_name = f"{case.classname}.{case.name}" if case.classname else case.name
            if not raw_name:
                case_xml = ET.tostring(case._elem, encoding="unicode")
                if len(case_xml) > 500:
                    case_xml = f"{case_xml[:497]}..."
                log.warning(
                    "Skipping JUnit testcase without a usable name "
                    "(branch=%r, suite=%r, attributes=%r, xml=%r)",
                    branch,
                    suite.name,
                    dict(case._elem.attrib),
                    case_xml,
                )
                continue
            name = raw_name
            # pytest-rerunfailures emits one <testcase> per attempt and marks every
            # attempt but the last with <rerunFailure>. junitparser does not model
            # that tag, so such a case looks result-free and would score as a pass.
            if any(
                child.tag.rsplit("}", 1)[-1].lower().startswith("rerun")
                for child in case._elem
            ):
                reruns[name] += 1
                continue
            if name in test_results_by_name:
                reruns[name] += 1
            extra: dict = {}
            if case.time is not None:
                extra["time"] = case.time

            results = case.result
            if len(results) > 1 and len({type(r) for r in results}) == 1:
                # Multiple result children of the same kind (e.g. pytest emitting
                # the "pytest.internal" pseudo-test with two identical <error>s):
                # collapse to a single result.
                results = [results[0]]
            if not results:
                status = "passed"
            elif len(results) != 1:
                status = "system_error"
                extra["error_details"] = f"Expected 1 result for {name}, got {len(results)}: {results}"
            else:
                result = results[0]
                if isinstance(result, Skipped):
                    status = "skipped"
                elif isinstance(result, Failure):
                    status = "failure"
                elif isinstance(result, Error):
                    status = "error"
                else:
                    status = "system_error"
                    extra["error_details"] = f"Unknown result type for {name}: {type(result).__name__}"
                if hasattr(result, "message") and result.message:
                    extra["message"] = result.message
                if hasattr(result, "text") and result.text:
                    extra["text"] = result.text

            test_results_by_name[name] = TestResult(
                name=name, branch=branch, status=status, extra=extra
            )

    test_results = list(test_results_by_name.values())
    for test in test_results:
        if reruns[test.name]:
            test.extra["reruns"] = reruns[test.name]
    return EvaluationResult(test_results=test_results)
