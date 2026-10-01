# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the root directory of
# this source tree.

"""Decide whether a generated suite is sound enough to judge the specification with.

A low pass rate on the reference executable is the signal the polish step wants: it says the
specification misled the test author. A suite whose tests crash inside their own code says
nothing about the specification, and one broken fixture can take most of a suite with it (a
fake tool with a malformed shebang disabled 24 of 33 tests in one run). Only the second kind
is grounds for regenerating.

An evaluation that never ran is a third outcome and must not be confused with the second. A
missing image or a dead daemon leaves no per-test evidence at all, which looks exactly like a
suite that crashed on import; regenerating then costs a full generation and fails identically,
so it is reported as an infrastructure failure for the caller to abort on.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from programbench.eval.test_suite_eval import TestSuiteEvaluationResult
from programbench.failure_attribution import FAILED_STATUSES

CRASH_SHARE_LIMIT = 0.80
REGENERATE_EXIT_CODE = 3
INFRASTRUCTURE_EXIT_CODE = 4
# Exceptions a test can only raise from its own code. Assertion failures, process statuses,
# timeouts and missing output files all describe the executable and are deliberately absent.
_TEST_CODE_EXCEPTIONS = re.compile(
    r"^E\s+(?:[\w.]*\.)?(TypeError|AttributeError|NameError|UnboundLocalError|IndexError|"
    r"ImportError|ModuleNotFoundError|SyntaxError|IndentationError|ZeroDivisionError|RecursionError)\b",
    re.MULTILINE,
)


def crashed_in_test_code(traceback: str) -> bool:
    matches = re.findall(r"^E\s+([\w.]*(?:Error|Exception|Exit))\b", traceback, re.MULTILINE)
    return bool(matches) and bool(_TEST_CODE_EXCEPTIONS.search("E   " + matches[-1]))


def infrastructure_failure(result: TestSuiteEvaluationResult) -> str:
    """Why this evaluation judges nothing, or `""` when it really ran.

    A container that never started and a suite that crashes on import both end with no
    per-test evidence, so the absence of evidence cannot tell them apart. The error codes
    can: they are set when the harness failed rather than when a test did.
    """
    if result.error_code:
        return f"evaluation failed: {result.error_code}: {result.error_details}"
    trials = result._ground_truth_trials()
    if not trials:
        return "no ground-truth trial ran"
    if all(trial.error_code for trial in trials):
        return f"every ground-truth trial failed: {trials[0].error_code}: {trials[0].error_details}"
    mutants = [binary for binary in result.binary_results if binary.role != "ground_truth"]
    if mutants and all(binary.error_code for binary in mutants):
        return f"every mutant trial failed: {mutants[0].error_code}: {mutants[0].error_details}"
    return ""


def suite_quality(eval_json: Path) -> dict:
    result = TestSuiteEvaluationResult.model_validate_json(eval_json.read_text())
    failure = infrastructure_failure(result)
    trials = result._usable_ground_truth_trials()
    tests = trials[0].test_results if trials else []
    crashed = sorted(
        test.name
        for test in tests
        if test.status in FAILED_STATUSES and crashed_in_test_code(str((test.extra or {}).get("text", "")))
    )
    crash_share = len(crashed) / len(tests) if tests else 1.0
    return {
        "eval_json": str(eval_json),
        "infrastructure_failure": failure or None,
        "tests": len(tests),
        "passing_on_reference": len(result.ground_truth_passing_test_names),
        "flaky": len(result.flaky_test_names),
        "crashed_in_test_code": crashed,
        "crash_share": round(crash_share, 4),
        "crash_share_limit": CRASH_SHARE_LIMIT,
        "accept": not failure and bool(tests) and crash_share < CRASH_SHARE_LIMIT,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Accept or reject a generated suite from its reference-trial results.")
    parser.add_argument("eval_json", type=Path, help="<task>.test_eval.json written by `programbench eval-tests`")
    parser.add_argument("-o", "--output", type=Path, help="Write the quality report here as JSON")
    args = parser.parse_args(argv)
    report = suite_quality(args.eval_json)
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)
    if report["infrastructure_failure"]:
        return INFRASTRUCTURE_EXIT_CODE
    return 0 if report["accept"] else REGENERATE_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
