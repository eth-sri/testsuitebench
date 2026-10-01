from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dry_run(*args: str) -> list[str]:
    result = subprocess.run(
        ["bash", "scripts/eval/run_agents.sh", "--dry-run", "--task", "a__b.1234567", "--task", "c__d.1234567", *args],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return result.stdout.splitlines()


def test_default_configurations_get_their_effort_and_identical_eval_flags():
    lines = dry_run(
        "--runs",
        "claude-opus-5 claude-fable codex-gpt-5.6-sol codex-gpt-5.6-luna "
        "codex-gpt-6-astra claude-opus-5.5 claude-sonnet-5.5 codex-gpt-6-sol codex-gpt-6-luna codex-gpt-6.1-sol gemini-3.8-flash qwen-3.8-flash "
        "deepseek-v4-flash-0731 glm-5.3-flash muse-spark-1.3-contributor",
        "--", "--no-classify", "--regenerate",
    )

    assert len(lines) == 30
    expected = {
        "--claude-model opus --claude-reasoning high",
        "--claude-model claude-opus-5-5 --claude-reasoning high",
        "--claude-model claude-sonnet-5-5 --claude-reasoning high",
        "--codex-model gpt-6-sol --codex-reasoning medium",
        "--codex-model gpt-6-luna --codex-reasoning medium",
        "--codex-model gpt-6.1-sol --codex-reasoning medium",
        "--claude-model fable --claude-reasoning high",
        "--codex-model gpt-5.6-sol --codex-reasoning medium",
        "--codex-model gpt-5.6-luna --codex-reasoning medium",
        "--codex-model gpt-6-astra --codex-reasoning medium",
        "--gemini-model gemini-3.8-flash --gemini-reasoning medium",
        "--qwen-model qwen/qwen3.8-flash --qwen-reasoning xhigh",
        "--deepseek-model deepseek/deepseek-v4-flash-0731 --deepseek-reasoning high",
        "--glm-model openrouter/z-ai/glm-5.3-flash --glm-reasoning max",
        "--muse-model meta/muse-spark-1.3-contributor --muse-reasoning high",
    }
    assert all(any(fragment in line for line in lines) for fragment in expected)
    assert all("--skipped-mutants ground_truth/skipped-mutants" in line and line.endswith("--no-classify --regenerate ") for line in lines)
    assert "output/eval/codegen/qwen-qwen3.8-flash_xhigh" in next(line for line in lines if "qwen_eval" in line)





def test_with_code_runner_only_generates_tests_with_reference_executable():
    result = subprocess.run(
        ["bash", "scripts/eval/run_agents_with_code.sh", "--dry-run",
         "--runs", "claude-opus-5 codex-gpt-5.6-sol deepseek-v4-flash-0423",
         "--task", "a__b.1234567", "--", "--no-classify"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    lines = result.stdout.splitlines()
    assert len(lines) == 3
    assert all("--part test_gen" in line and "--test-with-executable" in line for line in lines)
    assert all("--part all" not in line and "--part exec_gen" not in line for line in lines)
    assert all("output/eval_with_code/testgen/" in line for line in lines)
    assert all("_with_code/" in line for line in lines)


def test_deepseek_checkpoints_have_separate_explicit_log_dirs():
    lines = dry_run("--runs", "deepseek-v4-flash-0423 deepseek-v4-flash-0731", "--output-root", "output/checkpoints")
    assert len(lines) == 4
    for run_id, model in (
        ("deepseek-v4-flash-0423", "deepseek/deepseek-v4-flash"),
        ("deepseek-v4-flash-0731", "deepseek/deepseek-v4-flash-0731"),
    ):
        matching = [line for line in lines if f"--deepseek-model {model} " in line]
        assert len(matching) == 2
        assert all(f"--log-dir output/checkpoints/logs/{run_id} " in line for line in matching)


def test_direct_deepseek_eval_uses_checkpoint_log_dir(tmp_path):
    task = "missing__task.0000000"
    for checkpoint, model in (
        ("0423", "deepseek/deepseek-v4-flash"),
        ("0731", "deepseek/deepseek-v4-flash-0731"),
    ):
        result = subprocess.run(
            [
                "bash", "scripts/eval/deepseek_eval.sh",
                "--task", task,
                "--deepseek-model", model,
                "--spec-dir", str(tmp_path / "spec"),
                "--reference-tests-dir", str(tmp_path / "tests"),
                "--executable-dir", str(tmp_path / "codegen" / "model"),
                "--generated-tests-dir", str(tmp_path / "testgen" / "model"),
            ],
            cwd=ROOT, capture_output=True, text=True,
        )
        log_file = tmp_path / "logs" / f"deepseek-v4-flash-{checkpoint}" / f"{task}_0.log"
        assert result.returncode == 1
        assert result.stdout.splitlines()[0] == f"[start] {task} ({log_file})"
        assert "Specification input is missing" in log_file.read_text()


def test_every_agent_evaluation_uses_three_reference_trials():
    for agent in ("claude", "codex", "gemini", "muse", "qwen", "deepseek", "glm"):
        script = (ROOT / "scripts" / "eval" / f"{agent}_eval.sh").read_text()
        assert "--detailed-logs --reference-trials 3 --workers" in script


def test_overrides_and_agent_selection():
    lines = dry_run(
        "--runs", "muse-spark-1.3-contributor codex-gpt-5.6-sol",
        "--reasoning", "muse-spark-1.3-contributor=ultra",
        "--model", "muse-spark-1.3-contributor=spark-2",
        "--jobs", "5",
    )

    assert len(lines) == 4
    assert all("--muse-model spark-2 --muse-reasoning ultra" in line for line in lines if "muse_eval" in line)
    assert all("--codex-model gpt-5.6-sol --codex-reasoning medium" in line for line in lines if "codex_eval" in line)


def test_multiple_model_configurations_can_share_one_backend():
    lines = dry_run(
        "--runs", "codex-gpt-5.6-sol codex-gpt-5-astra",
        "--backend", "codex-gpt-5-astra=codex",
        "--model", "codex-gpt-5-astra=gpt-5-astra",
        "--reasoning", "codex-gpt-5-astra=high",
    )

    assert len(lines) == 4
    assert all("scripts/eval/codex_eval.sh" in line for line in lines)
    assert sum("--codex-model gpt-5.6-sol --codex-reasoning medium" in line for line in lines) == 2
    assert sum("--codex-model gpt-5-astra --codex-reasoning high" in line for line in lines) == 2


def test_eval_runner_reports_task_lifecycle_around_its_log(tmp_path):
    task = "missing__task.0000000"
    log_dir = tmp_path / "logs"
    result = subprocess.run(
        [
            "bash", "scripts/eval/codex_eval.sh",
            "--task", task,
            "--spec-dir", str(tmp_path / "spec"),
            "--reference-tests-dir", str(tmp_path / "tests"),
            "--executable-dir", str(tmp_path / "codegen" / "model"),
            "--generated-tests-dir", str(tmp_path / "testgen" / "model"),
            "--log-dir", str(log_dir),
        ],
        cwd=ROOT, capture_output=True, text=True,
    )

    log_file = log_dir / f"{task}_0.log"
    assert result.returncode == 1
    assert result.stderr == ""
    assert result.stdout.splitlines()[0] == f"[start] {task} ({log_file})"
    assert re.fullmatch(rf"\[failed\] {re.escape(task)} \({re.escape(str(log_file))}, \d+h\d+m\)", result.stdout.splitlines()[1])
    assert "Specification input is missing" in log_file.read_text()


def test_run_path_passes_each_task_to_the_eval_script(tmp_path):
    """The xargs hand-off once substituted a literal {} for every task; exercise the real path with a stub agent."""
    import shutil

    (tmp_path / "scripts" / "eval").mkdir(parents=True)
    (tmp_path / "scripts" / "docker").mkdir()
    shutil.copy(ROOT / "scripts" / "eval" / "run_agents.sh", tmp_path / "scripts" / "eval" / "run_agents.sh")
    (tmp_path / "scripts" / "eval" / "stub_eval.sh").write_text('#!/usr/bin/env bash\necho "$@" >> "$0.calls"\n')
    (tmp_path / "scripts" / "docker" / "setup_egress_network.sh").write_text('#!/usr/bin/env bash\nexit 0\n')
    (tmp_path / "scripts" / "docker" / "cleanup_containers.py").write_text("# Stub cleanup for the task-dispatch test.\n")
    subprocess.run(
        ["bash", "scripts/eval/run_agents.sh", "--runs", "stub-model", "--backend", "stub-model=stub",
         "--model", "stub-model=m", "--reasoning", "stub-model=r", "--task", "a__b.1234567",
         "--task", "c__d.1234567", "--jobs", "2", "--", "--no-classify"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )

    calls = sorted((tmp_path / "scripts" / "eval" / "stub_eval.sh.calls").read_text().splitlines())
    assert [c.split()[3] for c in calls] == ["a__b.1234567", "c__d.1234567"]
    assert all("--stub-model m --stub-reasoning r" in c and c.endswith("--no-classify") for c in calls)
    timings = tmp_path / "output" / "eval" / "timings" / "m_r"
    assert {p.name for p in timings.iterdir()} == {"a__b.1234567.seconds", "c__d.1234567.seconds"}
    assert all(float(p.read_text()) >= 0 for p in timings.iterdir())


def test_generation_receives_the_same_cpu_limit_as_evaluation():
    for agent in ("claude", "codex", "gemini", "muse", "qwen", "deepseek", "glm"):
        script = (ROOT / "scripts" / "eval" / f"{agent}_eval.sh").read_text()
        assert 'generation_cpu_args+=(--docker-cpus "${docker_cpus}")' in script
        assert script.count('"${generation_cpu_args[@]}"') == 2


def test_standard_run_provisions_restricted_egress():
    script = (ROOT / "scripts" / "eval" / "run_agents.sh").read_text()
    assert 'bash "${script_dir}/../docker/setup_egress_network.sh"' in script
