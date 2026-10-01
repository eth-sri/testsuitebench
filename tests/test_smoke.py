# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging

from typer.testing import CliRunner

from programbench.cli.main import app

runner = CliRunner()


def test_eval_help() -> None:
    result = runner.invoke(app, ["eval", "--help"])
    assert result.exit_code == 0
    assert "sources" in result.output.lower()


def test_eval_logs_completion(monkeypatch, caplog) -> None:
    monkeypatch.setattr("programbench.eval.eval_batch.run_eval_batch", lambda **kwargs: None)
    caplog.set_level(logging.INFO, logger="programbench.eval.eval_batch")

    result = runner.invoke(app, ["eval", "test-output"])

    assert result.exit_code == 0
    assert "Finished eval" in caplog.messages


def test_eval_tests_logs_completion(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "programbench.eval.test_suite_eval_batch.run_test_suite_eval_batch",
        lambda **kwargs: None,
    )
    caplog.set_level(logging.INFO, logger="programbench.eval.test_suite_eval_batch")

    result = runner.invoke(app, ["eval-tests", "test-output"])

    assert result.exit_code == 0
    assert "Finished eval-tests" in caplog.messages


def test_generate_tests_logs_completion(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        "programbench.test_generation.run_codex_test_generation_batch",
        lambda **kwargs: [],
    )
    caplog.set_level(logging.INFO, logger="programbench.test_generation")

    result = runner.invoke(app, ["generate-tests"])

    assert result.exit_code == 0
    assert "Finished generate-tests" in caplog.messages


def test_generate_tests_help_includes_spec_only() -> None:
    result = runner.invoke(app, ["generate-tests", "--help"])

    assert result.exit_code == 0
    assert "--with-executable" in result.output
    assert "--spec-only" in result.output
    assert "--goal" in result.output
    assert "--no-goal" in result.output
    assert "--prompt-format" not in result.output


def test_generation_commands_do_not_expose_prompt_format() -> None:
    for command in ("generate-tests", "improve-spec", "generate-mutants"):
        result = runner.invoke(app, [command, "--help"])

        assert result.exit_code == 0
        assert "--prompt-format" not in result.output


def test_generate_tests_mode_flags_pass_with_executable_value(monkeypatch) -> None:
    captured = []

    def fake_run_codex_test_generation_batch(**kwargs):
        captured.append(kwargs["with_executable"])
        return []

    monkeypatch.setattr(
        "programbench.test_generation.run_codex_test_generation_batch",
        fake_run_codex_test_generation_batch,
    )

    with_binary = runner.invoke(app, ["generate-tests", "--with-executable"])
    spec_only = runner.invoke(app, ["generate-tests", "--spec-only"])

    assert with_binary.exit_code == 0
    assert spec_only.exit_code == 0
    assert captured == [True, False]


def test_generate_tests_goal_flag_passes_use_goal(monkeypatch) -> None:
    captured = []

    def fake_run_codex_test_generation_batch(**kwargs):
        captured.append(kwargs["use_goal"])
        return []

    monkeypatch.setattr(
        "programbench.test_generation.run_codex_test_generation_batch",
        fake_run_codex_test_generation_batch,
    )

    with_goal = runner.invoke(app, ["generate-tests", "--goal"])
    without_goal = runner.invoke(app, ["generate-tests", "--no-goal"])

    assert with_goal.exit_code == 0
    assert without_goal.exit_code == 0
    assert captured == [True, False]


def test_generate_tests_codex_model_strips_backend_prefix(monkeypatch) -> None:
    captured = []

    def fake_run_codex_test_generation_batch(**kwargs):
        captured.append(kwargs)
        return []

    monkeypatch.setattr(
        "programbench.test_generation.run_codex_test_generation_batch",
        fake_run_codex_test_generation_batch,
    )

    result = runner.invoke(
        app,
        [
            "generate-tests",
            "--model",
            "codex/gpt-5.4",
            "--reasoning-effort",
            "high",
        ],
    )

    assert result.exit_code == 0
    assert captured[0]["model"] == "gpt-5.4"
    assert captured[0]["reasoning_effort"] == "high"
    assert "prompt_format" not in captured[0]


def test_generate_tests_openai_model_uses_minisweagent_runner(monkeypatch) -> None:
    captured = []

    def fake_run_test_generation_batch(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(
        "programbench.test_generation.run_test_generation_batch",
        fake_run_test_generation_batch,
    )

    result = runner.invoke(
        app,
        [
            "generate-tests",
            "--model",
            "openai/gpt-5.4-mini",
            "--reasoning-effort",
            "high",
            "--config",
            "mini-programbench-rootless.yaml",
        ],
    )

    assert result.exit_code == 0
    assert captured[0]["model"] == "openai/gpt-5.4-mini"
    assert captured[0]["reasoning_effort"] == "high"
    assert captured[0]["config_specs"] == ["mini-programbench-rootless.yaml"]
    assert "prompt_format" not in captured[0]


def test_improve_spec_codex_model_strips_backend_prefix(monkeypatch) -> None:
    captured = []

    def fake_run_spec_improvement_batch(**kwargs):
        captured.append(kwargs)
        return []

    monkeypatch.setattr(
        "programbench.spec_improvement.run_spec_improvement_batch",
        fake_run_spec_improvement_batch,
    )

    result = runner.invoke(
        app,
        [
            "improve-spec",
            "--model",
            "codex/gpt-5.5",
            "--reasoning-effort",
            "high",
        ],
    )

    assert result.exit_code == 0
    assert captured[0]["model"] == "gpt-5.5"
    assert captured[0]["reasoning_effort"] == "high"
    assert "prompt_format" not in captured[0]


def test_generate_mutants_codex_model_strips_backend_prefix(monkeypatch) -> None:
    captured = []

    def fake_run_mutant_generation_batch(**kwargs):
        captured.append(kwargs)
        return []

    monkeypatch.setattr(
        "programbench.mutants.run_mutant_generation_batch",
        fake_run_mutant_generation_batch,
    )

    result = runner.invoke(
        app,
        [
            "generate-mutants",
            "--model",
            "codex/gpt-5.5",
            "--reasoning-effort",
            "high",
            "--docker-cpus",
            "16",
            "--mutant-build-jobs",
            "8",
            "--test-spec-links",
            "links",
        ],
    )

    assert result.exit_code == 0
    assert captured[0]["model"] == "gpt-5.5"
    assert captured[0]["reasoning_effort"] == "high"
    assert captured[0]["docker_cpus"] == 16
    assert captured[0]["mutant_build_jobs"] == 8
    assert "prompt_format" not in captured[0]
    assert captured[0]["spec_in"] == "cleanroom/semiformal"
    assert captured[0]["test_spec_links"] == "links"


def test_generate_mutants_uses_cleanroom_base_image_env(monkeypatch) -> None:
    captured = []

    def fake_run_mutant_generation_batch(**kwargs):
        captured.append(kwargs)
        return []

    monkeypatch.setenv("PROGRAMBENCH_MUTANT_CLEANROOM_BASE_IMAGE", "programbench/example:task_cleanroom_codex")
    monkeypatch.setattr(
        "programbench.mutants.run_mutant_generation_batch",
        fake_run_mutant_generation_batch,
    )

    result = runner.invoke(app, ["generate-mutants", "--test-spec-links", "links"])

    assert result.exit_code == 0
    assert captured[0]["cleanroom_base_image"] == "programbench/example:task_cleanroom_codex"
