# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Evaluate generated test suites against known-good binaries."""

import ast
import hashlib
import logging
import json
import re
import shlex
import stat
import subprocess
import tarfile
import tempfile
import time
import threading
from collections import defaultdict
import xml.etree.ElementTree as ET
from contextlib import nullcontext
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from programbench.constants import (
    PIN_EVAL_PIP_VERSIONS,
    DOCKER_CPUS,
    DOCKER_EXECUTABLE,
    DOCKER_RUN_ARGS,
    EVAL_NETWORK_ARGS,
    EVAL_SUBPROCESS_TIMEOUT,
    MAX_JUNIT_DIAGNOSTIC_BYTES,
    MAX_JUNIT_XML_BYTES,
    MAX_RAW_JUNIT_XML_BYTES,
    WORKSPACE_DIR,
)
from programbench.container import ContainerEnvironment
from programbench.eval.eval import TestResult, parse_test_results
from programbench.eval.binary_cache import atomic_write, digest_path
from programbench.eval.junit_diagnostics import truncate_utf8
from programbench.exceptions import EvalStepError, XmlParseError
from programbench.mutant_storage import materialize_mutant_payload
from programbench.mutants import MutantSpec

log = logging.getLogger(__name__)

_REFERENCE_SUPPORT_RESERVED_NAMES = {
    "build.sh",
    "compile.sh",
    "executable",
    "executable_cov",
    "executable_nocov",
    "run.sh",
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_reference_support_executables(
    reference_tests_root: Path | None,
    instance_id: str,
) -> tuple[Path, ...]:
    """Find immutable top-level ELF helpers supplied by reference-test branches."""
    if reference_tests_root is None or not instance_id:
        return ()
    instance_root = reference_tests_root / instance_id
    if not instance_root.is_dir():
        return ()

    discovered: dict[str, tuple[str, Path]] = {}
    for branch in sorted(path for path in instance_root.iterdir() if path.is_dir()):
        for path in sorted(branch.iterdir()):
            if path.name in _REFERENCE_SUPPORT_RESERVED_NAMES or path.is_symlink():
                continue
            try:
                mode = path.stat().st_mode
            except OSError:
                continue
            if not stat.S_ISREG(mode) or mode & 0o111 == 0:
                continue
            try:
                with path.open("rb") as source:
                    if source.read(4) != b"\x7fELF":
                        continue
                digest = _file_sha256(path)
            except OSError:
                continue
            previous = discovered.get(path.name)
            if previous is not None and previous[0] != digest:
                raise ValueError(
                    "Conflicting reference support executable "
                    f"{path.name!r} for {instance_id}: {previous[1]} and {path}"
                )
            discovered.setdefault(path.name, (digest, path))
    return tuple(item[1] for item in sorted(discovered.values(), key=lambda item: item[1].name))


_TEXT_TEST_EXTENSIONS = {
    ".bats",
    ".bash",
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".mjs",
    ".php",
    ".pl",
    ".pm",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".t",
    ".ts",
    ".tsx",
    ".zsh",
}
_SKIPPED_ASSERTION_COUNT_FILES = {
    "results.xml",
}
_ASSERTION_CALL_RE = re.compile(
    r"""
    \b(?:
        assert(?:_[A-Za-z0-9_]+)?
        |ASSERT_[A-Z0-9_]+
        |EXPECT_[A-Z0-9_]+
        |assert(?:True|False|Equal|NotEqual|Raises|In|NotIn|Is|IsNot)
    )\s*(?:\(|\s)
    """,
    re.VERBOSE,
)
_RUST_ASSERTION_RE = re.compile(r"\bassert(?:_eq|_ne)?!\s*\(")
_JS_EXPECT_RE = re.compile(r"\bexpect\s*\(.+?\)\s*\.\s*(?:to|not)\b")
_GO_ASSERTION_RE = re.compile(r"\b(?:assert|require)\.[A-Za-z0-9_]+\s*\(")
_NODE_ASSERTION_RE = re.compile(r"\bassert(?:\.[A-Za-z0-9_]+)?\s*\(")
_PERL_TEST_MORE_RE = re.compile(
    r"\b(?:ok|is|isnt|like|unlike|cmp_ok|is_deeply|pass|fail|can_ok|isa_ok|new_ok|use_ok|require_ok)\s*(?:\(|\s)"
)
_SHELL_ASSERT_FUNC_RE = re.compile(r"\bassert(?:_[A-Za-z0-9_]+)?\b")
_SHELL_TEST_COMMAND_RE = re.compile(r"^\s*(?:!?\s*)?(?:\[|\[\[|test\b)")
_SHELL_CHECK_COMMAND_RE = re.compile(r"^\s*(?:!?\s*)?(?:grep\s+-q|diff\b|cmp\b)")
_INVALID_XML_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_MAX_RETAINED_LOG_TEXT_CHARS = 100_000
_JUNIT_DIAGNOSTIC_SANITIZER = Path(__file__).with_name("junit_diagnostics.py")
_CONTAINER_JUNIT_DIAGNOSTIC_SANITIZER = "/tmp/programbench-junit-diagnostics.py"


def _truncate_retained_log_text(value: str) -> str:
    if len(value) <= _MAX_RETAINED_LOG_TEXT_CHARS:
        return value
    retained_at_each_end = _MAX_RETAINED_LOG_TEXT_CHARS // 2
    omitted = len(value) - 2 * retained_at_each_end
    return (
        value[:retained_at_each_end]
        + f"\n... [ProgramBench omitted {omitted} characters from the retained evaluation log] ...\n"
        + value[-retained_at_each_end:]
    )


def _bounded_retained_value(value: object) -> object:
    if isinstance(value, str):
        return _truncate_retained_log_text(value)
    if isinstance(value, dict):
        return {key: _bounded_retained_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_bounded_retained_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_bounded_retained_value(item) for item in value)
    return value


def _bounded_test_diagnostic_value(value: object) -> object:
    if isinstance(value, str):
        return truncate_utf8(value, MAX_JUNIT_DIAGNOSTIC_BYTES)
    if isinstance(value, dict):
        return {key: _bounded_test_diagnostic_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_bounded_test_diagnostic_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_bounded_test_diagnostic_value(item) for item in value)
    return value


def _bounded_log_entry(entry: dict) -> dict:
    return {
        key: _bounded_retained_value(value)
        if key in {"output", "stdout", "stderr", "exception_info"}
        else value
        for key, value in entry.items()
    }


def _xml_safe_char_replacement(match: re.Match[str]) -> str:
    codepoint = ord(match.group(0))
    if codepoint <= 0xFF:
        return f"\\x{codepoint:02x}"
    return f"\\u{codepoint:04x}"


def _sanitize_invalid_xml_chars(raw_xml: str) -> str:
    return _INVALID_XML_CHAR_RE.sub(_xml_safe_char_replacement, raw_xml)


class _PythonAssertionCounter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.count = 0

    def visit_Assert(self, node: ast.Assert) -> None:
        self.count += 1

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"):
            self.count += 1
        self.generic_visit(node)


def _count_python_assertions_in_source(source: str) -> int:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return sum(line.lstrip().startswith("assert ") for line in source.splitlines())
    counter = _PythonAssertionCounter()
    counter.visit(tree)
    return counter.count


def _strip_hash_comment(line: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    for i, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            return line[:i]
    return line


def _logical_shell_segments(line: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"\s*(?:&&|\|\||;)\s*", line) if segment.strip()]


def _count_shell_assertions_in_source(source: str) -> int:
    total = 0
    for raw_line in source.splitlines():
        line = _strip_hash_comment(raw_line).strip()
        if not line or line.startswith(("if ", "elif ", "while ", "for ", "case ")):
            continue
        if re.match(r"^(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*\s*\(\s*\)\s*\{?", line):
            continue
        for segment in _logical_shell_segments(line):
            if re.match(r"^(?:then|else|fi|do|done|return|echo|printf)\b", segment):
                continue
            if _SHELL_ASSERT_FUNC_RE.search(segment):
                total += 1
            elif _SHELL_TEST_COMMAND_RE.search(segment):
                total += 1
            elif _SHELL_CHECK_COMMAND_RE.search(segment):
                total += 1
    return total


def _count_perl_assertions_in_source(source: str) -> int:
    total = 0
    for raw_line in source.splitlines():
        line = _strip_hash_comment(raw_line)
        if re.match(r"^\s*(?:sub|use|require|package)\b", line):
            continue
        total += len(_PERL_TEST_MORE_RE.findall(line))
    return total


def _count_generic_assertions_in_source(source: str) -> int:
    total = 0
    for raw_line in source.splitlines():
        line = _strip_hash_comment(raw_line)
        if re.match(r"^\s*(?:def|class|function|sub|use|import|from|package|#|//)\b", line):
            continue
        total += len(_ASSERTION_CALL_RE.findall(line))
        total += len(_RUST_ASSERTION_RE.findall(line))
        total += len(_JS_EXPECT_RE.findall(line))
        total += len(_GO_ASSERTION_RE.findall(line))
        total += len(_NODE_ASSERTION_RE.findall(line))
    return total


def _count_assertions_in_source(source: str, path_name: str) -> int:
    suffix = Path(path_name).suffix.lower()
    name = Path(path_name).name.lower()
    if suffix == ".py":
        return _count_python_assertions_in_source(source)
    if suffix in {".sh", ".bash", ".bats", ".zsh"} or name == "run.sh":
        return _count_shell_assertions_in_source(source)
    if suffix in {".pl", ".pm", ".t"}:
        return _count_perl_assertions_in_source(source)
    return _count_generic_assertions_in_source(source)


def _is_countable_test_file(path_name: str) -> bool:
    path = Path(path_name)
    name = path.name
    if not name or name in _SKIPPED_ASSERTION_COUNT_FILES:
        return False
    if any(part.startswith(".") for part in path.parts):
        return False
    if path.suffix.lower() in _TEXT_TEST_EXTENSIONS:
        return True
    return name in {"run.sh", "run.bash"} or name.startswith(("test_", "spec_"))


def count_assertions(test_suite_payload: Path) -> int:
    """Count assertion-like checks in a generated test-suite directory or archive."""
    if test_suite_payload.is_dir():
        total = 0
        for path in test_suite_payload.rglob("*"):
            if not path.is_file() or not _is_countable_test_file(str(path.relative_to(test_suite_payload))):
                continue
            try:
                total += _count_assertions_in_source(path.read_text(errors="replace"), path.name)
            except OSError:
                log.warning("Could not read generated test file while counting assertions: %s", path)
        return total

    if not test_suite_payload.is_file():
        return 0

    total = 0
    try:
        with tarfile.open(test_suite_payload, "r:*") as tar:
            for member in tar:
                if not member.isfile() or not _is_countable_test_file(member.name):
                    continue
                fileobj = tar.extractfile(member)
                if fileobj is None:
                    continue
                source = fileobj.read().decode("utf-8", errors="replace")
                total += _count_assertions_in_source(source, member.name)
    except (tarfile.TarError, OSError) as e:
        log.warning("Could not inspect generated test archive while counting assertions: %s", e)
        return 0
    return total


def count_python_assertions(test_suite_payload: Path) -> int:
    """Backward-compatible alias for generated test-suite assertion counting."""
    return count_assertions(test_suite_payload)


class BinaryTestSuiteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binary_id: str
    role: Literal["ground_truth", "candidate"] = "ground_truth"
    test_results: list[TestResult] = []
    error_code: str | None = None
    error_details: str | None = None
    log: list[dict] = []
    warnings: list[str] = []

    @property
    def n_passed(self) -> int:
        return sum(t.status == "passed" for t in self.test_results)

    @property
    def n_system_errors(self) -> int:
        return sum(t.status == "system_error" for t in self.test_results)

    @property
    def n_tests(self) -> int:
        return len(self.test_results)

    @property
    def score(self) -> float:
        if self.error_code or self.n_tests == 0:
            return 0.0
        return self.n_passed / self.n_tests

    @property
    def passed(self) -> bool:
        return self.error_code is None and self.n_tests > 0 and self.n_passed == self.n_tests


def _subtest_parent_name(test_name: str) -> str | None:
    parent, sep, suffix = test_name.rpartition(" (")
    if not sep or not suffix.endswith(")"):
        return None
    return parent


def _matrix_status(statuses: dict[str, str], test_name: str) -> str | None:
    status = statuses.get(test_name)
    if status is not None:
        return status
    parent_name = _subtest_parent_name(test_name)
    if parent_name is None:
        return None
    return statuses.get(parent_name)


def _statuses_by_binary(binary_results: list["BinaryTestSuiteResult"]) -> dict[str, dict[str, str]]:
    return {
        r.binary_id: {t.name: t.status for t in r.test_results}
        for r in binary_results
    }


def _effective_test_names(binary_results: list["BinaryTestSuiteResult"]) -> list[str]:
    return sorted({t.name for r in binary_results for t in r.test_results})


def _effective_pass_count(
    statuses: dict[str, str],
    test_names: list[str],
) -> int:
    return sum(_matrix_status(statuses, test_name) == "passed" for test_name in test_names)


class TestSuiteEvaluationResult(BaseModel):
    __test__ = False
    model_config = ConfigDict(extra="forbid")

    binary_results: list[BinaryTestSuiteResult] = []
    # The first result is also retained in binary_results for compatibility with
    # existing evaluation consumers. Additional trials make nondeterministic
    # generated tests observable without multiplying the mutant matrix.
    ground_truth_trials: list[BinaryTestSuiteResult] = []
    n_assertions: int | None = None
    error_code: str | None = None
    error_details: str | None = None

    def __len__(self) -> int:
        return sum(r.n_tests for r in self.binary_results)

    def __iter__(self) -> Iterator[TestResult]:
        for binary in self.binary_results:
            yield from binary.test_results

    @property
    def n_passed(self) -> int:
        return sum(r.n_passed for r in self.binary_results)

    @property
    def n_system_errors(self) -> int:
        return sum(r.n_system_errors for r in self.binary_results)

    @property
    def score(self) -> float:
        if self.error_code or len(self) == 0:
            return 0.0
        return self.n_passed / len(self)

    @property
    def ground_truth_passed(self) -> bool:
        ground_truth = self._ground_truth_trials()
        return bool(ground_truth) and all(r.passed for r in ground_truth)

    def _ground_truth_trials(self) -> list[BinaryTestSuiteResult]:
        if self.ground_truth_trials:
            return self.ground_truth_trials
        return [r for r in self.binary_results if r.role == "ground_truth"]

    def _usable_ground_truth_trials(self) -> list[BinaryTestSuiteResult]:
        """Trials with actual per-test evidence, excluding infrastructure failures."""

        return [
            trial
            for trial in self._ground_truth_trials()
            if trial.error_code is None and trial.test_results
        ]

    @property
    def flaky_test_names(self) -> set[str]:
        """Tests whose pass/fail result differs between reference trials."""
        trials = self._usable_ground_truth_trials()
        if len(trials) < 2:
            return set()
        test_names = sorted({t.name for trial in trials for t in trial.test_results})
        statuses = [{t.name: t.status for t in trial.test_results} for trial in trials]
        return {
            name
            for name in test_names
            if len({(_matrix_status(trial_statuses, name) == "passed") for trial_statuses in statuses}) > 1
        }

    @property
    def validity_rate(self) -> float:
        ground_truth = self._usable_ground_truth_trials()
        test_names = sorted({t.name for r in ground_truth for t in r.test_results})
        if self.error_code or not ground_truth or not test_names:
            return 0.0
        statuses = [{t.name: t.status for t in trial.test_results} for trial in ground_truth]
        return sum(
            name not in self.flaky_test_names
            and all(_matrix_status(trial_statuses, name) == "passed" for trial_statuses in statuses)
            for name in test_names
        ) / len(test_names)

    @property
    def candidate_results(self) -> list[BinaryTestSuiteResult]:
        return [r for r in self.binary_results if r.role == "candidate"]

    @property
    def n_test_functions(self) -> int:
        ground_truth = self._usable_ground_truth_trials()
        if ground_truth:
            return len({t.name for r in ground_truth for t in r.test_results})
        return len(_effective_test_names(self.binary_results))

    @property
    def n_mutants(self) -> int:
        return len(self.candidate_results)

    @property
    def ground_truth_passing_test_names(self) -> set[str]:
        ground_truth = self._usable_ground_truth_trials()
        if not ground_truth:
            return set()
        test_names = sorted({t.name for r in ground_truth for t in r.test_results})
        statuses = [{t.name: t.status for t in trial.test_results} for trial in ground_truth]
        return {
            test_name
            for test_name in test_names
            if test_name not in self.flaky_test_names
            and all(_matrix_status(trial_statuses, test_name) == "passed" for trial_statuses in statuses)
        }

    def candidate_failing_ground_truth_passing_test_names(
        self,
        result: BinaryTestSuiteResult,
    ) -> set[str]:
        """Return exact valid test cases that fail for a candidate binary."""
        passing_ground_truth_tests = self.ground_truth_passing_test_names
        if result.error_code is not None or not passing_ground_truth_tests:
            return set()
        statuses = _statuses_by_binary(self.binary_results)[result.binary_id]
        return {
            test_name
            for test_name in passing_ground_truth_tests
            if _matrix_status(statuses, test_name) != "passed"
        }

    def _candidate_fails_ground_truth_passing_test(self, result: BinaryTestSuiteResult) -> bool:
        return bool(self.candidate_failing_ground_truth_passing_test_names(result))

    @property
    def n_mutants_killed(self) -> int:
        return sum(self._candidate_fails_ground_truth_passing_test(r) for r in self.candidate_results)

    @property
    def mutation_score(self) -> float | None:
        if self.n_mutants == 0:
            return None
        return self.n_mutants_killed / self.n_mutants

    def summarize(self) -> str:
        summary = f"TestSuiteEvaluationResult(score={self.score * 100:.0f}={self.n_passed}/{len(self)}"
        summary += f", validity_rate={self.validity_rate * 100:.0f}"
        if self.mutation_score is not None:
            summary += f", mutation_score={self.mutation_score * 100:.0f}"
        if self.n_assertions is not None:
            summary += f", assertions={self.n_assertions}"
        if self.error_code is not None:
            summary += f", error_code={self.error_code}"
        if self.error_details is not None:
            summary += f", error_details={self.error_details}"
        summary += ")"
        return summary


class TestSuiteEvaluator:
    """Run an agent-generated test suite against a binary image.

    The generated archive must unpack into a ProgramBench-style test payload:
    ``eval/run.sh`` must exist and produce ``eval/results.xml`` in JUnit XML
    format. The image is expected to contain the ground-truth ``./executable``
    in ``/workspace``.
    """

    def __init__(
        self,
        *,
        image_name: str,
        test_suite_archive: Path,
        instance_id: str = "",
        image_tag: str = "task_patched",
        docker_cpus: int = DOCKER_CPUS,
        branch_workers: int = 1,
        mutants_root: Path | None = None,
        mutants: list[MutantSpec] | None = None,
        ground_truth_executable: Path | None = None,
        reference_tests_root: Path | None = None,
        detailed_logs: bool = False,
        reference_trials: int = 1,
        mutant_progress_callback: Callable[[], None] | None = None,
        log_run_summary: bool = True,
        ignored_tests: set[str] | None = None,
        execution_pool: ThreadPoolExecutor | None = None,
        cache_dir: Path | None = None,
    ):
        self.image_name = image_name
        self.test_suite_archive = test_suite_archive
        self.instance_id = instance_id
        self.image_tag = image_tag
        self.docker_cpus = docker_cpus
        self.branch_workers = max(1, branch_workers)
        self.mutants_root = mutants_root
        self.mutants = list(mutants or [])
        self.ground_truth_executable = ground_truth_executable
        self.reference_support_executables = discover_reference_support_executables(
            reference_tests_root,
            instance_id,
        )
        self.detailed_logs = detailed_logs
        if reference_trials < 1:
            raise ValueError("reference_trials must be at least 1")
        self.reference_trials = reference_trials
        self.mutant_progress_callback = mutant_progress_callback
        self.log_run_summary = log_run_summary
        self.ignored_tests = ignored_tests or set()
        self.execution_pool = execution_pool
        self.cache_dir = cache_dir
        self._cache_prefix: str | None = None
        self._metrics_lock = threading.Lock()
        self._phase_seconds: dict[str, float] = defaultdict(float)
        self._cache_hits = 0
        self._ground_truth_runs = 0

    def _new_env(self, cpus: int | None = None) -> ContainerEnvironment:
        return ContainerEnvironment(
            image=f"{self.image_name}:{self.image_tag}",
            cwd=WORKSPACE_DIR,
            executable=DOCKER_EXECUTABLE,
            timeout=600,
            cpus=cpus or self.docker_cpus,
            # Pytest already uses the CPU budget for concurrent tests. OpenMP
            # otherwise sees host cores and oversubscribes Docker CPU quotas.
            env={"OMP_NUM_THREADS": "1"},
            run_args=[*DOCKER_RUN_ARGS, *EVAL_NETWORK_ARGS, "--init"],
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
        with self._metrics_lock:
            self._phase_seconds[step_name] += wall_time
        log_buf.append(_bounded_log_entry({"step": step_name, "command": command, "wall_time": wall_time, **r}))
        if r["returncode"] != 0 and not accept_failure:
            raise EvalStepError(f"{step_name}_failed", r["output"].strip())
        return r

    def _copy_file_from_container(
        self,
        *,
        env: ContainerEnvironment,
        log_buf: list[dict],
        container_path: str,
        step_name: str,
        timeout: int = 60,
        max_bytes: int | None = None,
    ) -> str:
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
                    _bounded_log_entry({
                        "step": step_name,
                        "command": cmd_str,
                        "wall_time": wall_time,
                        "output": err,
                        "returncode": rc,
                        "exception_info": "",
                    })
                )
                raise EvalStepError(f"{step_name}_failed", err)
            if max_bytes is not None and host_tmp.stat().st_size > max_bytes:
                details = (
                    f"{container_path} is {host_tmp.stat().st_size} bytes; "
                    f"the limit is {max_bytes} bytes"
                )
                log_buf.append(
                    {
                        "step": step_name,
                        "command": cmd_str,
                        "wall_time": wall_time,
                        "output": details,
                        "returncode": 0,
                        "exception_info": "",
                    }
                )
                raise EvalStepError("results_too_large", details)
            contents = host_tmp.read_text()
            log_buf.append(
                _bounded_log_entry({
                    "step": step_name,
                    "command": cmd_str,
                    "wall_time": wall_time,
                    "output": contents,
                    "returncode": 0,
                    "exception_info": "",
                })
            )
            return contents
        finally:
            host_tmp.unlink(missing_ok=True)

    def _count_testcases(self, raw_xml: str) -> int:
        if not raw_xml.strip():
            return 0
        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError:
            return 0
        return sum(1 for _ in root.iter("testcase"))

    def _prepare_cache(self) -> None:
        if self.cache_dir is None:
            return
        try:
            inspected = subprocess.run(
                [DOCKER_EXECUTABLE, "image", "inspect", "--format", "{{.Id}}",
                 f"{self.image_name}:{self.image_tag}"],
                check=True, capture_output=True, text=True, timeout=30,
            )
            inputs = [inspected.stdout.strip(), str(self.docker_cpus),
                      sorted(self.ignored_tests), digest_path(self.test_suite_archive)]
            if self.ground_truth_executable is not None:
                inputs.append(digest_path(self.ground_truth_executable))
            inputs += [(p.name, digest_path(p)) for p in self.reference_support_executables]
            # Invalidate checkpoints when evaluation behavior changes.
            implementation = sorted(Path(__file__).parent.glob("*.py"))
            implementation += [Path(__file__).parents[1] / name for name in ("constants.py", "container.py", "mutant_storage.py")]
            inputs += [(p.name, digest_path(p)) for p in implementation]
            self._cache_prefix = hashlib.sha256(json.dumps(inputs).encode()).hexdigest()
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            log.warning("%s: evaluation checkpoints disabled: %s", self.instance_id, exc)

    def _run_binary(self, *, binary_id: str, role: Literal["ground_truth", "candidate"],
                    mutant_payload: Path | None = None, cpus: int | None = None) -> BinaryTestSuiteResult:
        checkpoint = None
        # Repeated reference trials must remain independent executions.
        if self._cache_prefix and not (role == "ground_truth" and self.reference_trials > 1):
            key = hashlib.sha256(json.dumps([
                self._cache_prefix, binary_id, role,
                digest_path(mutant_payload) if mutant_payload is not None else None,
            ]).encode()).hexdigest()
            checkpoint = self.cache_dir / f"{key}.json"
            try:
                cached = BinaryTestSuiteResult.model_validate_json(checkpoint.read_text())
                if cached.error_code is None and cached.test_results and cached.binary_id == binary_id and cached.role == role:
                    with self._metrics_lock:
                        self._cache_hits += 1
                    log.debug("%s: reused completed evaluation for %s", self.instance_id, binary_id)
                    return cached
            except (OSError, ValueError):
                pass
        result = self._run_binary_uncached(binary_id=binary_id, role=role, mutant_payload=mutant_payload, cpus=cpus)
        if checkpoint is not None and result.error_code is None and result.test_results:
            try:
                atomic_write(checkpoint, result.model_dump_json())
            except OSError as exc:
                log.warning("%s: could not save evaluation checkpoint: %s", self.instance_id, exc)
        return result

    def _run_binary_uncached(
        self,
        *,
        binary_id: str,
        role: Literal["ground_truth", "candidate"],
        mutant_payload: Path | None = None,
        cpus: int | None = None,
    ) -> BinaryTestSuiteResult:
        log_buf: list[dict] = []
        result = BinaryTestSuiteResult(binary_id=binary_id, role=role)
        env = None
        try:
            env = self._new_env(cpus) if cpus else self._new_env()
            if self.ground_truth_executable is not None:
                if not self.ground_truth_executable.is_file():
                    raise RuntimeError(
                        "ground-truth executable does not exist: "
                        f"{self.ground_truth_executable}"
                    )
                env.copy_in(
                    self.ground_truth_executable,
                    f"{WORKSPACE_DIR}/.programbench-ground-truth-executable",
                )
                self._run_step(
                    "rm -f ./executable && "
                    "mv ./.programbench-ground-truth-executable ./executable && "
                    "chmod +x ./executable",
                    env=env,
                    log_buf=log_buf,
                    step_name="install_ground_truth",
                    timeout=120,
                )
            self._run_step(
                "test -x ./executable",
                env=env,
                log_buf=log_buf,
                step_name="check_executable",
                timeout=60,
            )
            if mutant_payload is not None:
                env.copy_in(mutant_payload, f"{WORKSPACE_DIR}/.programbench-mutant-executable")
                self._run_step(
                    "cp ./executable ./.programbench-ground-truth && "
                    "chmod +x ./.programbench-ground-truth && "
                    "rm -f ./executable && "
                    "mv ./.programbench-mutant-executable ./executable && "
                    "chmod +x ./executable",
                    env=env,
                    log_buf=log_buf,
                    step_name="install_mutant",
                    timeout=120,
                )
            self._run_step(
                "cp -f ./executable /tmp/programbench-executable-under-test && "
                "chmod +x /tmp/programbench-executable-under-test",
                env=env,
                log_buf=log_buf,
                step_name="backup_executable",
                timeout=120,
            )
            self._run_step(
                "rm -rf ./eval ./results.xml",
                env=env,
                log_buf=log_buf,
                step_name="clean_workspace",
                timeout=120,
            )
            if self.test_suite_archive.is_dir():
                env.copy_in(self.test_suite_archive, f"{WORKSPACE_DIR}/")
            else:
                env.copy_in_tar(self.test_suite_archive, f"{WORKSPACE_DIR}/")
            self._run_step(
                "mkdir -p .programbench-bin && "
                "python_bin=$(command -v python3 || command -v python || true); "
                "if [ -n \"$python_bin\" ]; then "
                "ln -sf \"$python_bin\" .programbench-bin/python; "
                "ln -sf \"$python_bin\" .programbench-bin/python3; "
                "fi",
                env=env,
                log_buf=log_buf,
                step_name="prepare_workspace_bin",
                timeout=60,
            )
            for support_executable in self.reference_support_executables:
                destination = f"{WORKSPACE_DIR}/.programbench-bin/{support_executable.name}"
                self._run_step(
                    f"test ! -e {shlex.quote(destination)}",
                    env=env,
                    log_buf=log_buf,
                    step_name="check_reference_support_collision",
                    timeout=60,
                )
                env.copy_in(support_executable, destination)
                self._run_step(
                    f"chmod +x {shlex.quote(destination)}",
                    env=env,
                    log_buf=log_buf,
                    step_name="stage_reference_support_executable",
                    timeout=60,
                )
            self._run_step(
                "rm -f ./executable && "
                "cp -f /tmp/programbench-executable-under-test ./executable && "
                "chmod +x ./executable",
                env=env,
                log_buf=log_buf,
                step_name="restore_executable",
                timeout=120,
            )
            self._run_step(
                "test -f eval/run.sh",
                env=env,
                log_buf=log_buf,
                step_name="check_run_sh",
                timeout=60,
            )
            self._run_step(
                "rm -f eval/results.xml results.xml",
                env=env,
                log_buf=log_buf,
                step_name="clean_stale_results",
                timeout=120,
            )

            watchdog = "/tmp/programbench-pytest-watchdog"
            env.copy_in(Path(__file__).with_name("pytest_watchdog.py"), f"{watchdog}/pytest_watchdog.py")
            watchdog_env = (
                f'cp "{watchdog}/pytest_watchdog.py" '
                """"$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"/; """
                f'export PROGRAMBENCH_SUBPROCESS_TIMEOUT="{EVAL_SUBPROCESS_TIMEOUT}"; '
                'export PYTEST_PLUGINS="pytest_watchdog${PYTEST_PLUGINS:+,$PYTEST_PLUGINS}"; '
            )
            # With `--timeout-method=thread` a timed-out test os._exit()s the whole
            # pytest process before results.xml is written, so the failure surfaces
            # as run_tests_failed_no_results and the test can never be attributed
            # or skipped. `signal` turns it into an ordinary per-test failure.
            self._run_step(
                "test -f eval/run.sh && sed -i 's/--timeout-method=thread/--timeout-method=signal/g' eval/run.sh || true",
                env=env,
                log_buf=log_buf,
                step_name="patch_timeout_method",
                accept_failure=True,
                timeout=10,
            )
            exclusion_env = ""
            if self.ignored_tests:
                support = "/tmp/programbench-pytest-exclusions"
                env.copy_in(Path(__file__).with_name("pytest_exclusions.py"), f"{support}/programbench_exclusions.py")
                with tempfile.TemporaryDirectory() as tmp:
                    exclusions = Path(tmp) / "excluded.json"
                    exclusions.write_text(json.dumps(sorted(self.ignored_tests)))
                    env.copy_in(exclusions, f"{support}/excluded.json")
                # run.sh owns its own environment and some scripts assign PYTHONPATH
                # outright (`PYTHONPATH=. pytest ...`), which drops the support dir and
                # leaves PYTEST_PLUGINS naming a module pytest cannot import. Install the
                # plugin on the interpreter's own search path so importing it never
                # depends on an environment variable run.sh may overwrite.
                exclusion_env = (
                    f'cp "{support}/programbench_exclusions.py" '
                    """"$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"/; """
                    f'export PYTHONPATH="{support}${{PYTHONPATH:+:$PYTHONPATH}}"; '
                    f'export PROGRAMBENCH_PYTEST_EXCLUSIONS="{support}/excluded.json"; '
                    'export PYTEST_PLUGINS="programbench_exclusions${PYTEST_PLUGINS:+,$PYTEST_PLUGINS}"; '
                )
            run_result = self._run_step(
                watchdog_env + exclusion_env + PIN_EVAL_PIP_VERSIONS
                + 'PATH="$PWD/.programbench-bin:$PATH"; chmod +x ./eval/run.sh && ./eval/run.sh',
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
                raise EvalStepError("run_tests_timeout", details)
            env.copy_in(_JUNIT_DIAGNOSTIC_SANITIZER, _CONTAINER_JUNIT_DIAGNOSTIC_SANITIZER)
            sanitize_result = self._run_step(
                "if test -f ./eval/results.xml; then "
                "size=$(wc -c < ./eval/results.xml); "
                f"test \"$size\" -le {MAX_RAW_JUNIT_XML_BYTES} || {{ "
                f"printf 'Raw JUnit XML is %s bytes; safety limit is {MAX_RAW_JUNIT_XML_BYTES} bytes\\n' "
                '"$size" >&2; exit 1; }; '
                f"if test \"$size\" -gt {MAX_JUNIT_XML_BYTES}; then "
                f"python3 {_CONTAINER_JUNIT_DIAGNOSTIC_SANITIZER} "
                f"./eval/results.xml {MAX_JUNIT_DIAGNOSTIC_BYTES}; "
                "fi; fi",
                env=env,
                log_buf=log_buf,
                step_name="sanitize_results",
                timeout=120,
            )
            if "truncated" in sanitize_result.get("output", ""):
                result.warnings.append(sanitize_result["output"].strip())
            self._run_step(
                "if test -f ./eval/results.xml; then "
                "size=$(wc -c < ./eval/results.xml); "
                f"test \"$size\" -le {MAX_JUNIT_XML_BYTES} || {{ "
                f"printf 'JUnit XML is %s bytes; limit is {MAX_JUNIT_XML_BYTES} bytes\\n' "
                '"$size" >&2; exit 1; }; fi',
                env=env,
                log_buf=log_buf,
                step_name="results_size",
                timeout=60,
            )
            try:
                raw_xml = self._copy_file_from_container(
                    env=env,
                    log_buf=log_buf,
                    container_path=f"{WORKSPACE_DIR}/eval/results.xml",
                    step_name="results_read",
                    timeout=60,
                    max_bytes=MAX_JUNIT_XML_BYTES,
                )
            except EvalStepError as e:
                # A missing results.xml means the run failed whatever pytest exited
                # with: a plugin that fails to load exits 1, which run.sh wrappers
                # routinely treat as "tests ran and failed" and mask as success.
                raise EvalStepError(
                    "run_tests_failed_no_results", run_result["output"].strip() or e.error_details
                ) from e
            parse_xml = raw_xml
            try:
                parsed = parse_test_results(parse_xml, branch="generated")
            except XmlParseError:
                parse_xml = _sanitize_invalid_xml_chars(raw_xml)
                if parse_xml == raw_xml:
                    raise
                parsed = parse_test_results(parse_xml, branch="generated")
                result.warnings.append(
                    "Generated suite produced JUnit XML with invalid XML characters; "
                    "sanitized them before parsing"
                )
            result.test_results = [
                test.model_copy(update={"extra": _bounded_test_diagnostic_value(test.extra)})
                for test in parsed.test_results
            ]
            if self._count_testcases(parse_xml) == 0:
                result.warnings.append("Generated suite produced zero JUnit testcases")
        except EvalStepError as e:
            result.error_code = e.error_code
            result.error_details = e.error_details
        except RuntimeError as e:
            result.error_code = type(e).__name__
            result.error_details = str(e)
        finally:
            if result.error_details is not None:
                result.error_details = _truncate_retained_log_text(result.error_details)
            result.log = log_buf
            if env is not None:
                env.cleanup()
        return result

    def _run_ground_truth(self) -> BinaryTestSuiteResult:
        """Run one reference trial; the second trial gets a quarter of the CPU quota.

        Generated tests that race the executable (write a watched file the instant its
        first output appears, poll with a fixed deadline) pass three identical trials by
        luck and then read as spec contradictions. Slowing one trial widens those windows.
        """
        with self._metrics_lock:
            trial = self._ground_truth_runs
            self._ground_truth_runs += 1
        cpus = max(1, self.docker_cpus // 4) if trial == 1 else None
        return self._run_binary(binary_id="ground_truth", role="ground_truth", cpus=cpus)

    def _run_mutant(self, mutant: MutantSpec) -> BinaryTestSuiteResult:
        if self.mutants_root is None:
            return BinaryTestSuiteResult(
                binary_id=mutant.id,
                role="candidate",
                error_code="missing_mutants_root",
                error_details="mutants_root was not provided",
            )
        try:
            with materialize_mutant_payload(self.mutants_root, mutant) as payload:
                return self._run_binary(binary_id=mutant.id, role="candidate", mutant_payload=payload)
        except FileNotFoundError as exc:
            return BinaryTestSuiteResult(
                binary_id=mutant.id,
                role="candidate",
                error_code="missing_mutant_payload",
                error_details=str(exc),
            )
        except (OSError, RuntimeError, ValueError) as exc:
            return BinaryTestSuiteResult(
                binary_id=mutant.id,
                role="candidate",
                error_code="invalid_mutant_artifact",
                error_details=str(exc),
            )

    def _log_label(self) -> str:
        return self.instance_id or self.image_name

    @staticmethod
    def _candidate_outcome(
        result: BinaryTestSuiteResult,
        binary_results: list[BinaryTestSuiteResult],
    ) -> str:
        if result.error_code is not None:
            return f"error {result.error_code}"
        test_names = _effective_test_names(binary_results)
        if not test_names:
            return "no tests"
        statuses_by_binary = _statuses_by_binary(binary_results)
        candidate_statuses = statuses_by_binary[result.binary_id]
        n_passed = _effective_pass_count(candidate_statuses, test_names)

        ground_truth = [r for r in binary_results if r.role == "ground_truth"]
        if ground_truth:
            ground_truth_statuses = statuses_by_binary[ground_truth[0].binary_id]
            passing_ground_truth_tests = {
                test_name
                for test_name in test_names
                if _matrix_status(ground_truth_statuses, test_name) == "passed"
            }
            killed = any(_matrix_status(candidate_statuses, test_name) != "passed" for test_name in passing_ground_truth_tests)
        else:
            killed = n_passed < len(test_names)

        if killed:
            return f"killed ({n_passed}/{len(test_names)} passed)"
        return f"survived ({n_passed}/{len(test_names)} passed)"

    @staticmethod
    def _status_marker(status: str | None) -> str:
        return {
            "passed": ".",
            "failure": "F",
            "error": "E",
            "system_error": "S",
            "skipped": "K",
            "not_run": "N",
            None: "-",
        }.get(status, "?")

    @staticmethod
    def _subtest_parent_name(test_name: str) -> str | None:
        parent, sep, suffix = test_name.rpartition(" (")
        if not sep or not suffix.endswith(")"):
            return None
        return parent

    @classmethod
    def _matrix_status(cls, statuses: dict[str, str], test_name: str) -> str | None:
        status = statuses.get(test_name)
        if status is not None:
            return status
        parent_name = cls._subtest_parent_name(test_name)
        if parent_name is None:
            return None
        return statuses.get(parent_name)

    @classmethod
    def _failure_matrix_table(
        cls,
        binary_results: list[BinaryTestSuiteResult],
        *,
        include_passing: bool = False,
    ) -> tuple[list[str], list[list[str]], list[BinaryTestSuiteResult]]:
        if not binary_results:
            return [], [], []

        binary_ids = [r.binary_id for r in binary_results]
        statuses_by_binary = {
            r.binary_id: {t.name: t.status for t in r.test_results}
            for r in binary_results
        }
        all_tests = sorted({t.name for r in binary_results for t in r.test_results})
        failing_tests = sorted(
            {
                t.name
                for r in binary_results
                for t in r.test_results
                if t.status != "passed"
            }
        )
        failing_test_names = set(failing_tests)
        other_tests = [
            test_name
            for test_name in all_tests
            if test_name not in failing_test_names
            and all(
                cls._matrix_status(statuses_by_binary[binary_id], test_name) == "passed"
                for binary_id in binary_ids
            )
        ]

        headers = ["test_function", *binary_ids]
        row_test_names = all_tests if include_passing else failing_tests
        rows = [
            [
                test_name,
                *[
                    cls._status_marker(cls._matrix_status(statuses_by_binary[binary_id], test_name))
                    for binary_id in binary_ids
                ],
            ]
            for test_name in row_test_names
        ]
        if other_tests and not include_passing:
            rows.append([f"{len(other_tests)} other tests", *["." for _ in binary_ids]])
        binary_errors = [r for r in binary_results if r.error_code is not None]
        return headers, rows, binary_errors

    @classmethod
    def _failure_matrix(cls, binary_results: list[BinaryTestSuiteResult]) -> str:
        headers, rows, binary_errors = cls._failure_matrix_table(binary_results)
        if not headers:
            return ""

        legend = "Legend: .=passed F=failure E=error S=system_error K=skipped N=not_run -=missing"
        widths = [len(header) for header in headers]
        for row in rows:
            for i, value in enumerate(row):
                widths[i] = max(widths[i], len(value))

        def fmt(row: list[str]) -> str:
            return "  ".join(value.ljust(widths[i]) for i, value in enumerate(row))

        lines = [
            "Failure matrix:",
            fmt(headers),
            fmt(["-" * width for width in widths]),
            *(fmt(row) for row in rows),
            legend,
        ]
        if binary_errors:
            lines.append(
                "Binary errors: "
                + "; ".join(f"{r.binary_id}={r.error_code}" for r in binary_errors)
            )
        return "\n".join(lines)

    def _execution_order(self) -> list[tuple[str, int | MutantSpec]]:
        """Space the reference trials evenly through the mutant sweep.

        Submission order is start order, so reference trials queued first
        measure the ground truth on a host the mutants never see: the sweep
        is still ramping up. Any test that only fails under the sweep's own
        contention -- a shared kernel limit such as inotify instances, file
        descriptors, or pids -- then stays mutation-score-eligible and "kills"
        mutants it never detected.
        """
        total = self.reference_trials + len(self.mutants)
        trials = {
            (2 * trial_index + 1) * total // (2 * self.reference_trials): trial_index
            for trial_index in range(self.reference_trials)
        }
        mutants = iter(self.mutants)
        return [
            ("ground_truth", trials[position]) if position in trials else ("mutant", next(mutants))
            for position in range(total)
        ]

    def run(self) -> TestSuiteEvaluationResult:
        self._phase_seconds.clear()
        self._cache_hits = 0
        self._ground_truth_runs = 0
        run_started = time.monotonic()
        self._prepare_cache()
        preparation_seconds = time.monotonic() - run_started
        label = self._log_label()
        status_log = log.info if self.log_run_summary else log.debug
        total_executions = self.reference_trials + len(self.mutants)
        execution_workers = min(self.branch_workers, total_executions)
        ground_truth_by_trial: dict[int, BinaryTestSuiteResult] = {}
        mutant_results_by_id: dict[str, BinaryTestSuiteResult] = {}

        durations: list[float] = []
        queue_waits: list[float] = []
        active = peak_active = errors = 0
        execution_started = time.monotonic()

        def measured_run(fn, *args, submitted=None):
            nonlocal active, peak_active, errors
            started = time.monotonic()
            with self._metrics_lock:
                active += 1
                peak_active = max(peak_active, active)
                queue_waits.append(started - submitted if submitted is not None else 0.0)
            failed = True
            try:
                result = fn(*args)
                failed = result.error_code is not None
                return result
            finally:
                duration = time.monotonic() - started
                with self._metrics_lock:
                    active -= 1
                    errors += int(failed)
                    durations.append(duration)
                execution_log = log.warning if failed else log.info if duration >= 60 else log.debug
                execution_log(
                    "%s payload=%s: execution=%s duration=%.3fs failed=%s",
                    label, self.test_suite_archive, getattr(args[0], "id", "ground_truth") if args else "ground_truth",
                    duration, failed,
                )

        log.info(
            "%s payload=%s: evaluation start; binaries=%d workers=%d shared_pool=%s "
            "cpus_per_container=%d cache_preparation=%.3fs; binaries are prebuilt; "
            "run_tests includes any setup/build inside eval/run.sh",
            label, self.test_suite_archive, total_executions, execution_workers,
            self.execution_pool is not None, self.docker_cpus, preparation_seconds,
        )

        if total_executions > 1:
            status_log(
                "%s: evaluating %d reference trial(s) and %d mutant(s) with %d worker(s)",
                label,
                self.reference_trials,
                len(self.mutants),
                execution_workers,
            )

        if self.branch_workers > 1 and total_executions > 1:
            with (nullcontext(self.execution_pool) if self.execution_pool is not None else ThreadPoolExecutor(max_workers=execution_workers)) as pool:
                futures: dict[object, tuple[str, int | MutantSpec]] = {
                    (
                        pool.submit(measured_run, self._run_ground_truth, submitted=time.monotonic())
                        if kind == "ground_truth"
                        else pool.submit(measured_run, self._run_mutant, execution, submitted=time.monotonic())
                    ): (kind, execution)
                    for kind, execution in self._execution_order()
                }
                completed_mutants = 0
                for future in as_completed(futures):
                    kind, execution = futures[future]
                    if kind == "ground_truth":
                        ground_truth_by_trial[int(execution)] = future.result()
                    else:
                        mutant = execution
                        assert isinstance(mutant, MutantSpec)
                        try:
                            result = future.result()
                        except Exception as e:
                            result = BinaryTestSuiteResult(
                                binary_id=mutant.id,
                                role="candidate",
                                error_code=type(e).__name__,
                                error_details=str(e),
                            )
                        mutant_results_by_id[mutant.id] = result
                        if self.mutant_progress_callback is not None:
                            self.mutant_progress_callback()
                        completed_mutants += 1
                        log.debug(
                            "%s: mutant %s finished (%d/%d)",
                            label,
                            mutant.id,
                            completed_mutants,
                            len(self.mutants),
                        )
        else:
            completed = 0
            for kind, execution in self._execution_order():
                if kind == "ground_truth":
                    ground_truth_by_trial[int(execution)] = measured_run(self._run_ground_truth)
                    continue
                mutant = execution
                assert isinstance(mutant, MutantSpec)
                completed += 1
                log.debug("%s: mutant %s started (%d/%d)", label, mutant.id, completed, len(self.mutants))
                try:
                    result = measured_run(self._run_mutant, mutant)
                except Exception as e:
                    result = BinaryTestSuiteResult(
                        binary_id=mutant.id,
                        role="candidate",
                        error_code=type(e).__name__,
                        error_details=str(e),
                    )
                mutant_results_by_id[mutant.id] = result
                if self.mutant_progress_callback is not None:
                    self.mutant_progress_callback()
                log.debug(
                    "%s: mutant %s finished (%d/%d)",
                    label,
                    mutant.id,
                    completed,
                    len(self.mutants),
                )

        execution_wall = time.monotonic() - execution_started
        busy_seconds = sum(durations)
        ordered = sorted(durations)
        log.info(
            "%s payload=%s: evaluation metrics; wall=%.3fs completed=%d errors=%d cache_hits=%d "
            "throughput=%.2f/s worker_seconds=%.3fs avg_active=%.2f peak_active=%d "
            "execution_mean=%.3fs execution_p95=%.3fs execution_max=%.3fs "
            "queue_mean=%.3fs queue_max=%.3fs phases_worker_seconds=%s "
            "other_worker_seconds=%.3fs (materialization/cache/container/copy/parse/cleanup); "
            "worker occupancy is not CPU utilization",
            label, self.test_suite_archive, execution_wall, len(durations), errors, self._cache_hits,
            len(durations) / max(execution_wall, 1e-9), busy_seconds,
            busy_seconds / max(execution_wall, 1e-9), peak_active,
            busy_seconds / max(len(durations), 1), ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)] if ordered else 0,
            max(durations, default=0), sum(queue_waits) / max(len(queue_waits), 1), max(queue_waits, default=0),
            {key: round(value, 3) for key, value in sorted(self._phase_seconds.items())},
            max(0, busy_seconds - sum(self._phase_seconds.values())),
        )

        ground_truth_trials = [
            ground_truth_by_trial[trial_index]
            for trial_index in range(self.reference_trials)
        ]
        binary_results = [
            ground_truth_trials[0],
            *(mutant_results_by_id[mutant.id] for mutant in self.mutants),
        ]
        if not all(trial.passed for trial in ground_truth_trials) and self.mutants:
            status_log("%s: ground truth did not pass; evaluated %d mutant(s) anyway", label, len(self.mutants))
        result = TestSuiteEvaluationResult(
            binary_results=binary_results,
            ground_truth_trials=ground_truth_trials,
            n_assertions=count_assertions(self.test_suite_archive),
        )
        for candidate in result.candidate_results:
            log.debug("%s: mutant %s result: %s", label, candidate.binary_id, self._candidate_outcome(candidate, binary_results))
        matrix = self._failure_matrix(binary_results)
        log.debug("%s:\n%s", label, matrix)
        log.debug(result.summarize())
        return result
