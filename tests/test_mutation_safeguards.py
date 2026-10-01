import logging

from programbench.eval.test_suite_eval import (
    BinaryTestSuiteResult,
    TestResult,
    TestSuiteEvaluationResult,
)
from programbench.eval.test_suite_eval_batch import _warn_dominant_generated_tests
from programbench.mutation_safeguards import (
    concentrated_tests_from_kill_sets,
    dominant_tests_from_kill_sets,
)


def test_dominant_threshold_is_strictly_greater_than_half() -> None:
    kill_sets = {
        "repo_1": ["test_half", "test_broad"],
        "repo_2": ["test_half", "test_broad"],
        "repo_3": ["test_broad"],
        "repo_4": [],
    }

    assert dominant_tests_from_kill_sets(kill_sets) == [{
        "test": "test_broad",
        "killed_mutants": ["repo_1", "repo_2", "repo_3"],
        "killed": 3,
        "total_mutants": 4,
        "kill_fraction": 0.75,
    }]


def test_generated_test_warning_names_function_and_kill_rate(caplog) -> None:
    test_names = ["generated/test_broad[param]", "generated/test_narrow"]
    binaries = [BinaryTestSuiteResult(
        binary_id="ground_truth",
        role="ground_truth",
        test_results=[TestResult(name=name, status="passed", extra={}) for name in test_names],
    )]
    for index in range(3):
        binaries.append(BinaryTestSuiteResult(
            binary_id=f"repo_{index + 1}",
            role="candidate",
            test_results=[
                TestResult(
                    name="generated/test_broad[param]",
                    status="failure" if index < 2 else "passed",
                    extra={},
                ),
                TestResult(
                    name="generated/test_narrow",
                    status="failure" if index == 0 else "passed",
                    extra={},
                ),
            ],
        ))

    with caplog.at_level(logging.WARNING, logger="programbench.eval.test_suite_eval_batch"):
        _warn_dominant_generated_tests(
            "org__repo.123",
            TestSuiteEvaluationResult(binary_results=binaries),
        )

    assert len(caplog.messages) == 1
    assert "generated/test_broad" in caplog.messages[0]
    assert "kills 2/3 mutants (66.7%)" in caplog.messages[0]
    assert "exceeding the 50% broad-test threshold" in caplog.messages[0]


def test_observed_kill_concentration_warns_below_broad_threshold(caplog) -> None:
    dominant = "generated/test_multiple_inline_documents_run_in_document_order"
    other = "generated/test_other"
    test_names = [dominant, other]
    binaries = [BinaryTestSuiteResult(
        binary_id="ground_truth",
        role="ground_truth",
        test_results=[TestResult(name=name, status="passed", extra={}) for name in test_names],
    )]
    for index in range(68):
        binaries.append(BinaryTestSuiteResult(
            binary_id=f"repo_{index + 1}",
            role="candidate",
            test_results=[
                TestResult(
                    name=dominant,
                    status="failure" if index < 32 else "passed",
                    extra={},
                ),
                TestResult(
                    name=other,
                    status="failure" if index in {32, 33} else "passed",
                    extra={},
                ),
            ],
        ))

    with caplog.at_level(logging.WARNING, logger="programbench.eval.test_suite_eval_batch"):
        _warn_dominant_generated_tests(
            "ast-grep__ast-grep.dde0fe0",
            TestSuiteEvaluationResult(binary_results=binaries),
        )

    assert len(caplog.messages) == 1
    assert dominant in caplog.messages[0]
    assert "32/34 observed mutant kills (94.1%)" in caplog.messages[0]
    assert "50% concentration threshold" in caplog.messages[0]


def test_observed_kill_concentration_requires_three_kills() -> None:
    kill_sets = {"repo_1": ["test_one"], "repo_2": ["test_one"]}

    assert concentrated_tests_from_kill_sets(kill_sets) == []


def test_generated_test_warning_ignores_failing_ground_truth_parameters(caplog) -> None:
    binaries = [BinaryTestSuiteResult(
        binary_id="ground_truth",
        role="ground_truth",
        test_results=[
            TestResult(name="generated/test_mixed[valid]", status="passed", extra={}),
            TestResult(name="generated/test_mixed[invalid]", status="failure", extra={}),
        ],
    )]
    for index in range(3):
        binaries.append(BinaryTestSuiteResult(
            binary_id=f"repo_{index + 1}",
            role="candidate",
            test_results=[
                TestResult(name="generated/test_mixed[valid]", status="passed", extra={}),
                TestResult(name="generated/test_mixed[invalid]", status="failure", extra={}),
            ],
        ))

    with caplog.at_level(logging.WARNING, logger="programbench.eval.test_suite_eval_batch"):
        _warn_dominant_generated_tests(
            "org__repo.123",
            TestSuiteEvaluationResult(binary_results=binaries),
        )

    assert caplog.messages == []
