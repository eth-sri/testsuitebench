# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import os
from pathlib import Path

import typer

from programbench.cli.blob import app as blob_app
from programbench.constants import DOCKER_CPUS

app = typer.Typer(
    name="programbench",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(blob_app, name="blob")


@app.callback()
def _callback() -> None:
    """Evaluate whether LM-based SWE-agents can reverse-engineer black-box
    software systems."""


@app.command()
def eval(
    sources: list[str] = typer.Argument(..., help="Path(s) to run directories"),
    workers: int = typer.Option(1, "-w", "--workers", help="Number of instances to evaluate in parallel"),
    branch_workers: int = typer.Option(
        1,
        "-b",
        "--branch-workers",
        help="Number of test branches to run in parallel within an instance "
        "(each branch runs in its own container off the post-compile image).",
    ),
    docker_cpus: int = typer.Option(
        DOCKER_CPUS,
        "--docker-cpus",
        help="Fallback CPU cores for compilation and direct evaluator use. Test branches use "
        "data/test_branch_cpus.json (default 2 CPUs).",
    ),
    branch_cpus: int = typer.Option(
        0,
        "--branch-cpus",
        help="Force this many CPUs per test branch, ignoring data/test_branch_cpus.json. 0 keeps the configured values.",
    ),
    cpu_budget: int = typer.Option(
        0,
        "--cpu-budget",
        help="Total CPU budget for this task. Parallel branch containers are admitted only while "
        "their fixed CPU requirements fit. 0 disables the aggregate limit.",
    ),
    branch_retries: int = typer.Option(
        1,
        "--branch-retries",
        help="On a test branch whose JUnit XML reports a pytest-xdist worker "
        "crash, re-run the branch up to this many times in a fresh container. "
        "The attempt with the fewest crashes wins. Pass 0 to disable.",
    ),
    force: bool = typer.Option(False, "-f", "--force", help="Re-evaluate even if results exist"),
    filter_spec: str = typer.Option("", "--filter", help="Filter instance IDs by regex"),
    slice_spec: str = typer.Option("", "--slice", help="Slice specification (e.g. '0:5')"),
    summarize_only: bool = typer.Option(False, "--summarize-only", help="Skip evaluation; just read existing results"),
    image_tag: str = typer.Option("task_patched", "--image-tag", help="Docker image tag to evaluate"),
    image: str = typer.Option(
        "",
        "--image",
        help="Full Docker image override. Takes precedence over the instance image name and --image-tag.",
    ),
    output: str = typer.Option(
        "",
        "-o",
        "--output",
        help="Write results under this directory instead of in-place. "
        "For each source S, eval.json files land at <output>/<S.name>/<instance_id>/.",
    ),
    tests_dir: str = typer.Option(
        "",
        "--tests-dir",
        help="Load per-branch test archives from this local directory instead of HuggingFace. "
        "Expected layout: <tests-dir>/<instance_id>/tests/<branch>.tar.gz, "
        "<tests-dir>/<instance_id>/<branch>.tar.gz, or extracted branch directories. "
        "Pass hf://<repo_id>[@revision] to download extracted branch directories uploaded with "
        "scripts/dataset/upload_reference_tests_to_hf.py.",
    ),
    ground_truth_dir: str = typer.Option(
        "",
        "--ground-truth-dir",
        help="Evaluate the ground-truth executable at <dir>/<instance_id>/executable for any SOURCES instance "
        "missing submission.tar.gz, by packaging it as one on the fly (a 'gold' self-check). "
        "Pass hf://<repo_id>[@revision] to download it from a HuggingFace dataset uploaded with "
        "scripts/dataset/upload_ground_truth_to_hf.py instead of storing it locally.",
    ),
    skipped_tests: str = typer.Option(
        "",
        "--skipped-tests",
        help="Run-scoped skipped-test JSON file or directory containing <instance_id>.json.",
    ),
    junit_completeness_check: bool = typer.Option(
        True,
        "--junit-completeness-check/--skip-junit-completeness-check",
        help="Validate JUnit testcase names against tests.json. Disable only for iterative debug phases with known stale manifests.",
    ),
) -> None:
    """Evaluate submissions against test suites.

    Accepts one or more paths to run directories containing
    <instance_id>/submission.tar.gz.

    \b
    Examples:
        programbench eval output/run_name
        programbench eval output/run_a output/run_b
        programbench eval output/run_name --workers 4 --force
        programbench eval output/run_name -w 4 -b 2 --docker-cpus 8
        programbench eval output/run_name --filter 'eradman__entr.*'
        programbench eval output/run_name --slice 0:5
        programbench eval output/run_name --summarize-only
        programbench eval ~/gold -o ~/gold-eval-out
        programbench eval ~/gold-eval-out --ground-truth-dir ground_truth/executable
        programbench eval ~/gold-eval-out --ground-truth-dir hf://eth-sri/tsb-reference_impl
    """
    from programbench.eval.eval_batch import run_eval_batch

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    run_eval_batch(
        sources=sources,
        force=force,
        workers=workers,
        branch_workers=branch_workers,
        docker_cpus=docker_cpus,
        branch_cpus=branch_cpus,
        cpu_budget=cpu_budget,
        filter_spec=filter_spec,
        slice_spec=slice_spec,
        summarize_only=summarize_only,
        image_tag=image_tag,
        image=image,
        output=output,
        branch_retries=branch_retries,
        tests_dir=tests_dir,
        ground_truth_dir=ground_truth_dir,
        skipped_tests=skipped_tests,
        check_junit_completeness=junit_completeness_check,
    )
    logging.getLogger("programbench.eval.eval_batch").info("Finished eval")


def _model_backend_and_name(model: str, *, command_name: str) -> tuple[str, str]:
    if not model:
        return "codex", ""
    if model.startswith("codex/"):
        return "codex", model.removeprefix("codex/")
    if model.startswith("openai/"):
        return "openai", model
    if "/" in model:
        raise typer.BadParameter(f"{command_name} model must use codex/gpt-XX or openai/gpt-XX")
    return "codex", model


def _test_generation_backend_and_model(model: str) -> tuple[str, str]:
    return _model_backend_and_name(model, command_name="generate-tests")


def _codex_cli_model(model: str, *, command_name: str) -> str:
    backend, selected_model = _model_backend_and_name(model, command_name=command_name)
    if backend != "codex":
        raise typer.BadParameter(f"{command_name} only supports Codex models; use codex/gpt-XX or gpt-XX")
    return selected_model


@app.command("generate-tests")
def generate_tests(
    workers: int = typer.Option(1, "-w", "--workers", help="Number of instances to run in parallel"),
    filter_spec: str = typer.Option("", "--filter", help="Filter instance IDs by regex"),
    slice_spec: str = typer.Option("", "--slice", help="Slice specification such as 0:5 for first 5 instances"),
    shuffle: bool = typer.Option(False, "--shuffle", help="Shuffle instances"),
    redo_existing: bool = typer.Option(False, "--redo-existing", help="Redo existing instances"),
    output: str = typer.Option("", "-o", "--output", help="Output directory"),
    model: str = typer.Option("", "-m", "--model", help="Model name. Use codex/gpt-XX for Codex or openai/gpt-XX for mini-swe-agent."),
    reasoning_effort: str = typer.Option(
        "",
        "--reasoning-effort",
        help="Optional reasoning effort passed to Codex or mini-swe-agent model configuration.",
    ),
    config_specs: list[str] = typer.Option(
        [],
        "-c",
        "--config",
        help="Accepted for compatibility with earlier mini-swe-agent generation; ignored by Codex generation.",
    ),
    model_class: str | None = typer.Option(
        None,
        "--model-class",
        help="Accepted for compatibility with earlier mini-swe-agent generation; ignored by Codex generation.",
    ),
    environment_class: str | None = typer.Option(
        None,
        "--environment-class",
        help="Accepted for compatibility with earlier mini-swe-agent generation; ignored by Codex generation.",
    ),
    cleanroom_dir: str = typer.Option(
        "",
        "--cleanroom-dir",
        help="Load cleanroom workspace files from this local directory. Expected layout: <cleanroom-dir>/<instance_id>/.",
    ),
    cleanroom_base_image: str = typer.Option(
        "",
        "--cleanroom-base-image",
        help="Use this Docker image when --image is empty. Without --cleanroom-dir, defaults to the task_cleanroom image.",
    ),
    with_executable: bool = typer.Option(
        False,
        "--with-executable/--spec-only",
        help="Choose whether Codex sees /workspace/executable during generation.",
    ),
    use_goal: bool = typer.Option(
        False,
        "--goal/--no-goal",
        help="Use Codex /goal with /workspace/codex-goal.md instead of passing the full prompt directly.",
    ),
    image: str = typer.Option(
        "",
        "--image",
        help="Docker image used to run Codex. With --cleanroom-dir, defaults to PROGRAMBENCH_CODEX_IMAGE or ghcr.io/openai/codex-universal:latest.",
    ),
    codex_command: str = typer.Option(
        "",
        "--codex-command",
        help="Codex command prefix to run inside the container. The test-generation prompt is appended as the final argument.",
    ),
    codex_auth_file: str = typer.Option(
        "",
        "--codex-auth-file",
        help="Host ChatGPT Codex auth.json copied into each disposable container. Defaults to CODEX_HOME/auth.json.",
    ),
    codex_log_dir: str = typer.Option(
        "",
        "--codex-log-dir",
        help="Directory for filtered Codex JSONL logs. Defaults to output/test-suites/editlog.",
    ),
    timeout: int = typer.Option(3600, "--timeout", help="Per-instance Codex timeout in seconds"),
    progress_log_interval: int = typer.Option(
        60,
        "--progress-log-interval",
        help="Seconds between per-instance progress logs while a phase is still running. Pass 0 to disable heartbeat logs.",
    ),
    docker_cpus: int = typer.Option(DOCKER_CPUS, "--docker-cpus", help="CPU cores allotted per docker container"),
    forward_env: list[str] = typer.Option(
        [],
        "--forward-env",
        help="Environment variable name to forward into the container. Repeatable; none are forwarded by default.",
    ),
) -> None:
    """Use Codex in Docker to generate ProgramBench-compatible test suites.

    The output layout is compatible with `programbench eval-tests`: each
    selected instance gets a `tests.tar.gz` archive containing `eval/run.sh`
    and related files.

    \b
    Examples:
        uv run programbench generate-tests -m codex/gpt-5.4 -o output/test-suites/gpt-5.4 --cleanroom-dir cleanroom/semiformal
        uv run programbench generate-tests -m codex/gpt-5.4 --filter abishekvashok__cmatrix --cleanroom-dir cleanroom/semiformal
        uv run programbench generate-tests -m codex/gpt-5.4 --cleanroom-dir cleanroom/semiformal --spec-only
        uv run programbench generate-tests -m codex/gpt-5.4 --cleanroom-dir cleanroom/original --with-executable
        uv run programbench generate-tests -m codex/gpt-5.4 --cleanroom-dir cleanroom/semiformal --goal
    """
    from programbench.spec_improvement import DEFAULT_CODEX_AUTH_FILE, DEFAULT_CODEX_COMMAND
    from programbench.test_generation import DEFAULT_TEST_CODEX_LOG_DIR, run_codex_test_generation_batch, run_test_generation_batch

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    backend, selected_model = _test_generation_backend_and_model(model)
    if backend == "openai":
        run_test_generation_batch(
            output=output,
            model=selected_model,
            reasoning_effort=reasoning_effort,
            config_specs=config_specs,
            workers=workers,
            filter_spec=filter_spec,
            slice_spec=slice_spec,
            shuffle=shuffle,
            redo_existing=redo_existing,
            model_class=model_class,
            environment_class=environment_class,
            cleanroom_dir=cleanroom_dir,
            cleanroom_base_image=cleanroom_base_image,
            with_executable=with_executable,
        )
        logging.getLogger("programbench.test_generation").info("Finished generate-tests")
        return

    results = run_codex_test_generation_batch(
        output=output,
        model=selected_model,
        reasoning_effort=reasoning_effort,
        workers=workers,
        filter_spec=filter_spec,
        slice_spec=slice_spec,
        shuffle=shuffle,
        redo_existing=redo_existing,
        image=image,
        cleanroom_dir=cleanroom_dir,
        cleanroom_base_image=cleanroom_base_image,
        with_executable=with_executable,
        use_goal=use_goal,
        # Passed through empty when unset so test generation can pick the command
        # from the image: the cleanroom images have codex preinstalled, and only
        # the stock codex-universal image needs the npx fetch, which the egress
        # allowlist refuses.
        codex_command=codex_command,
        timeout=timeout,
        codex_auth_file=codex_auth_file or DEFAULT_CODEX_AUTH_FILE,
        codex_log_dir=codex_log_dir or DEFAULT_TEST_CODEX_LOG_DIR,
        progress_log_interval=progress_log_interval,
        docker_cpus=docker_cpus,
        forward_env=forward_env or None,
    )

    if not results:
        typer.echo("No instances selected for test generation.")
        logging.getLogger("programbench.test_generation").info("Finished generate-tests")
        return

    counts: dict[str, int] = {}
    for result in results:
        status = result.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    typer.echo(
        "Test generation summary: "
        + ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    )

    for result in results:
        status = result.get("status")
        instance_id = result.get("instance_id", "<unknown>")
        output_path = result.get("output")
        codex_log = result.get("codex_log")
        traj = result.get("traj")
        if status == "ok":
            typer.echo(f"  ok: {instance_id} -> {output_path} (Codex log: {codex_log}, traj: {traj})")
        elif status == "skipped" and result.get("reason") == "tests_archive_exists":
            typer.echo(
                f"  skipped: {instance_id} already exists at {output_path} "
                "(use --redo-existing to overwrite)"
            )
        elif status != "ok":
            detail = result.get("error") or result.get("reason") or result.get("output") or ""
            typer.echo(f"  {status}: {instance_id} {detail}".rstrip())
            if codex_log:
                typer.echo(f"    Codex log: {codex_log}")
            if traj:
                typer.echo(f"    Trajectory: {traj}")

    failed = [r for r in results if r.get("status") not in {"ok", "skipped"}]
    if failed:
        raise typer.Exit(1)
    logging.getLogger("programbench.test_generation").info("Finished generate-tests")


@app.command("improve-spec")
def improve_spec(
    min_num_spec_sec: int = typer.Option(10, "--min-num-spec-sec", min=1),
    max_num_spec_sec: int = typer.Option(100, "--max-num-spec-sec", min=1),
    output: str = typer.Option(
        "cleanroom/semiformal",
        "-o",
        "--output",
        "--spec_out",
        "--spec-out",
        help="Directory where improved specifications are written as <output>/<instance_id>/.",
    ),
    testdir: str = typer.Option(
        "extracted-tests",
        "--testdir",
        help="Directory containing <instance_id>/ test branch directories or archives.",
    ),
    skipped_tests: str = typer.Option(
        "",
        "--skipped-tests",
        help="Run-scoped skipped-test JSON file or directory containing <instance_id>.json.",
    ),
    spec_in: str = typer.Option(
        "cleanroom/original",
        "--spec_in",
        "--spec-in",
        help="Directory containing input specifications at <spec_in>/<instance_id>/.",
    ),
    workers: int = typer.Option(1, "-w", "--workers", help="Number of instances to improve in parallel"),
    filter_spec: str = typer.Option("", "--filter", help="Filter instance IDs by regex"),
    slice_spec: str = typer.Option("", "--slice", help="Slice specification (e.g. '0:5' for first 5 instances)"),
    force: bool = typer.Option(False, "-f", "--force", help="Overwrite an existing <output>/<instance_id>/"),
    image: str = typer.Option(
        "",
        "--image",
        help="Docker image used to run Codex. Defaults to PROGRAMBENCH_CODEX_IMAGE or ghcr.io/openai/codex-universal:latest.",
    ),
    cleanroom_base_image: str = typer.Option(
        "",
        "--cleanroom-base-image",
        help="Use the task cleanroom image, or this override, when --image is empty.",
    ),
    codex_command: str = typer.Option(
        "",
        "--codex-command",
        help="Codex command prefix to run inside the container. The improvement prompt is appended as the final argument.",
    ),
    codex_auth_file: str = typer.Option(
        "",
        "--codex-auth-file",
        help="Host ChatGPT Codex auth.json copied into each disposable container. Defaults to CODEX_HOME/auth.json.",
    ),
    codex_log_dir: str = typer.Option(
        "",
        "--codex-log-dir",
        help="Directory for Codex trajectory logs. Defaults to cleanroom/editlog.",
    ),
    model: str = typer.Option("", "-m", "--model", help="Optional Codex model name"),
    reasoning_effort: str = typer.Option(
        "",
        "--reasoning-effort",
        help="Optional Codex reasoning effort.",
    ),
    timeout: int = typer.Option(7200, "--timeout", help="Per-instance Codex timeout in seconds"),
    progress_log_interval: int = typer.Option(
        60,
        "--progress-log-interval",
        help="Seconds between per-instance progress logs while a phase is still running. Pass 0 to disable heartbeat logs.",
    ),
    docker_cpus: int = typer.Option(DOCKER_CPUS, "--docker-cpus", help="CPU cores allotted per docker container"),
    forward_env: list[str] = typer.Option(
        [],
        "--forward-env",
        help="Environment variable name to forward into the container. Repeatable; none are forwarded by default.",
    ),
) -> None:
    """Use Codex in Docker to clarify specifications from generated tests.

    The container workspace contains `specification/` copied from
    `<spec_in>/<instance_id>/` and `test-branches/` copied from
    `<testdir>/<instance_id>/`. After Codex exits successfully,
    `specification/` is copied back to `<output>/<instance_id>/`.

    \b
    Example:
        uv run programbench improve-spec --output cleanroom/semiformal --testdir extracted-tests --spec_in cleanroom/original --filter abishekvashok__cmatrix.5c082c6 --force
    """
    from programbench.spec_improvement import (
        DEFAULT_CODEX_AUTH_FILE,
        DEFAULT_CODEX_LOG_DIR,
        DEFAULT_CODEX_COMMAND,
        DEFAULT_CODEX_IMAGE,
        run_spec_improvement_batch,
    )

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    selected_model = _codex_cli_model(model, command_name="improve-spec")

    results = run_spec_improvement_batch(
        min_num_spec_sec=min_num_spec_sec,
        max_num_spec_sec=max_num_spec_sec,
        output=output,
        testdir=testdir,
        skipped_tests=skipped_tests,
        spec_in=spec_in,
        workers=workers,
        filter_spec=filter_spec,
        slice_spec=slice_spec,
        force=force,
        image=image or DEFAULT_CODEX_IMAGE,
        cleanroom_base_image=cleanroom_base_image,
        codex_command=codex_command or DEFAULT_CODEX_COMMAND,
        model=selected_model,
        reasoning_effort=reasoning_effort,
        timeout=timeout,
        codex_auth_file=codex_auth_file or DEFAULT_CODEX_AUTH_FILE,
        codex_log_dir=codex_log_dir or DEFAULT_CODEX_LOG_DIR,
        progress_log_interval=progress_log_interval,
        docker_cpus=docker_cpus,
        forward_env=forward_env or None,
    )

    if not results:
        typer.echo("No instances selected for spec improvement.")
        return

    counts: dict[str, int] = {}
    for result in results:
        status = result.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    typer.echo(
        "Spec improvement summary: "
        + ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    )

    for result in results:
        status = result.get("status")
        instance_id = result.get("instance_id", "<unknown>")
        if status == "ok":
            typer.echo(f"  ok: {instance_id} -> {result.get('spec_out')} (traj: {result.get('traj')})")
        elif status == "skipped" and result.get("reason") == "spec_out_exists":
            typer.echo(f"  skipped: {instance_id} already exists at {result.get('spec_out')} (use --force to overwrite)")
        elif status != "ok":
            detail = result.get("error") or result.get("reason") or result.get("output") or ""
            typer.echo(f"  {status}: {instance_id} {detail}".rstrip())
            if result.get("traj"):
                typer.echo(f"    Trajectory: {result['traj']}")

    failed = [r for r in results if r.get("status") not in {"ok", "skipped"}]
    if failed:
        raise typer.Exit(1)


@app.command("generate-mutants")
def generate_mutants(
    output: str = typer.Option(
        "output/mutants",
        "-o",
        "--output",
        help="Directory where generated mutant repositories are written as <output>/<instance_id>/repo_N/.",
    ),
    repo_dir: str = typer.Option(
        "extracted-tests",
        "--repo_dir",
        "--repo-dir",
        help="Directory containing <instance_id>/<branch>/ repository snapshots.",
    ),
    ground_truth_implementation_dir: Path = typer.Option(
        Path("ground_truth/implementation"),
        "--ground-truth-implementation-dir",
        help="Implementations holding the recorded generated-path manifests to withhold from the agent.",
    ),
    spec_in: str = typer.Option(
        "cleanroom/semiformal",
        "--spec_in",
        "--spec-in",
        help="Directory containing input specifications at <spec_in>/<instance_id>/.",
    ),
    test_spec_links: str = typer.Option(
        ...,
        "--test-spec-links",
        help="Directory containing <instance_id>/test_spec_links.json for rule-based mutant planning.",
    ),
    workers: int = typer.Option(1, "-w", "--workers", help="Number of instances to process in parallel"),
    filter_spec: str = typer.Option("", "--filter", help="Filter instance IDs by regex"),
    slice_spec: str = typer.Option("", "--slice", help="Slice specification (e.g. '0:5' for first 5 instances)"),
    force: bool = typer.Option(False, "-f", "--force", help="Overwrite an existing <output>/<instance_id>/"),
    image: str = typer.Option(
        "",
        "--image",
        help="Docker image used to run Codex. Defaults to the task cleanroom image; if overridden, generated mutants are rebuilt in the cleanroom image.",
    ),
    cleanroom_base_image: str = typer.Option(
        "",
        "--cleanroom-base-image",
        help="Task cleanroom base image override used as the default Codex image and, when --image is overridden, the rebuild image. Defaults to PROGRAMBENCH_MUTANT_CLEANROOM_BASE_IMAGE when set.",
    ),
    codex_command: str = typer.Option(
        "",
        "--codex-command",
        help="Codex command prefix to run inside the container. The mutant-generation prompt is appended as the final argument.",
    ),
    codex_auth_file: str = typer.Option(
        "",
        "--codex-auth-file",
        help="Host ChatGPT Codex auth.json copied into each disposable container. Defaults to CODEX_HOME/auth.json.",
    ),
    codex_log_dir: str = typer.Option(
        "",
        "--codex-log-dir",
        help="Directory for Codex trajectory logs. Defaults to output/mutants/editlog.",
    ),
    model: str = typer.Option("", "-m", "--model", help="Optional Codex model name"),
    reasoning_effort: str = typer.Option(
        "",
        "--reasoning-effort",
        help="Optional Codex reasoning effort.",
    ),
    timeout: int = typer.Option(14400, "--timeout", help="Per-instance Codex timeout in seconds"),
    progress_log_interval: int = typer.Option(
        60,
        "--progress-log-interval",
        help="Seconds between per-instance progress logs while a phase is still running. Pass 0 to disable heartbeat logs.",
    ),
    docker_cpus: int = typer.Option(DOCKER_CPUS, "--docker-cpus", help="CPU cores allotted per docker container"),
    mutant_build_jobs: int = typer.Option(
        1,
        "--mutant-build-jobs",
        min=1,
        help="Number of mutant repositories to compile concurrently during agent validation and host rebuild.",
    ),
    max_build_repair_attempts: int = typer.Option(
        3,
        "--max-build-repair-attempts",
        min=0,
        help="Maximum Codex repair turns after ProgramBench-controlled mutant compilation fails.",
    ),
    target_tests_per_spec: int = typer.Option(
        6,
        "--target-tests-per-spec",
        min=1,
        help="Different target-test functions sampled per specification.",
    ),
    final_mutants_per_spec: int = typer.Option(
        2,
        "--final-mutants-per-spec",
        min=1,
        help="Empirically selected mutants retained per specification.",
    ),
    forward_env: list[str] = typer.Option(
        [],
        "--forward-env",
        help="Environment variable name to forward into the container. Repeatable; none are forwarded by default.",
    ),
) -> None:
    """Use Codex in Docker to create mutant repositories.

    For each selected instance, one branch from `<repo_dir>/<instance_id>/` is
    copied to `/workspace/repo` without any `eval/` directories. The matching
    specification is copied to `/workspace/specification`. Codex creates the configured
    candidate repositories, which are copied back to
    `<output>/<instance_id>/`. The ensure-mutants-killed stage evaluates them and keeps
    the configured final `repo_N` portfolio per specification.

    \b
    Example:
        uv run programbench generate-mutants --output output/mutants --repo_dir extracted-tests --spec_in cleanroom/semiformal --test-spec-links output/iter_0/test-spec-links --filter abishekvashok__cmatrix.5c082c6 --force
    """
    from programbench.mutants import (
        DEFAULT_MUTANT_CODEX_LOG_DIR,
        DEFAULT_CODEX_AUTH_FILE,
        DEFAULT_CODEX_COMMAND,
        run_mutant_generation_batch,
    )

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    selected_model = _codex_cli_model(model, command_name="generate-mutants")
    selected_cleanroom_base_image = cleanroom_base_image or os.environ.get("PROGRAMBENCH_MUTANT_CLEANROOM_BASE_IMAGE", "")

    results = run_mutant_generation_batch(
        output=output,
        repo_dir=repo_dir,
        spec_in=spec_in,
        test_spec_links=test_spec_links,
        workers=workers,
        filter_spec=filter_spec,
        slice_spec=slice_spec,
        force=force,
        image=image,
        cleanroom_base_image=selected_cleanroom_base_image,
        codex_command=codex_command or DEFAULT_CODEX_COMMAND,
        model=selected_model,
        reasoning_effort=reasoning_effort,
        timeout=timeout,
        codex_auth_file=codex_auth_file or DEFAULT_CODEX_AUTH_FILE,
        codex_log_dir=codex_log_dir or DEFAULT_MUTANT_CODEX_LOG_DIR,
        progress_log_interval=progress_log_interval,
        docker_cpus=docker_cpus,
        mutant_build_jobs=mutant_build_jobs,
        max_build_repair_attempts=max_build_repair_attempts,
        target_tests_per_spec=target_tests_per_spec,
        final_mutants_per_spec=final_mutants_per_spec,
        forward_env=forward_env or None,
        ground_truth_implementation_dir=ground_truth_implementation_dir,
    )

    if not results:
        typer.echo("No instances selected for mutant generation.")
        return

    counts: dict[str, int] = {}
    for result in results:
        status = result.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    typer.echo(
        "Mutant generation summary: "
        + ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    )

    for result in results:
        status = result.get("status")
        instance_id = result.get("instance_id", "<unknown>")
        if status == "ok":
            typer.echo(
                f"  ok: {instance_id} -> {result.get('output')} "
                f"({len(result.get('mutant_repositories', []))} repo(s), branch: {result.get('branch')}, "
                f"traj: {result.get('traj')})"
            )
        elif status == "skipped" and result.get("reason") == "output_exists":
            typer.echo(f"  skipped: {instance_id} already exists at {result.get('output')} (use --force to overwrite)")
        elif status != "ok":
            detail = result.get("error") or result.get("reason") or result.get("output") or ""
            typer.echo(f"  {status}: {instance_id} {detail}".rstrip())
            if result.get("traj"):
                typer.echo(f"    Trajectory: {result['traj']}")

    failed = [r for r in results if r.get("status") not in {"ok", "skipped"}]
    if failed:
        raise typer.Exit(1)


@app.command("eval-tests")
def eval_tests(
    sources: list[str] = typer.Argument(..., help="Path(s) to generated test-suite run directories"),
    workers: int = typer.Option(1, "-w", "--workers", help="Number of instances to evaluate in parallel"),
    branch_workers: int = typer.Option(
        1,
        "-b",
        "--mutant-workers",
        "--branch-workers",
        help="Number of mutant binaries to evaluate in parallel within an instance. "
        "Ground truth still runs first; mutants run even when ground truth fails.",
    ),
    docker_cpus: int = typer.Option(
        DOCKER_CPUS,
        "--docker-cpus",
        help="CPU cores allotted per docker container.",
    ),
    cpu_budget: int = typer.Option(
        0,
        "--cpu-budget",
        help="Total CPU budget for this task, divided among active payload/mutant containers. 0 preserves --docker-cpus per container.",
    ),
    force: bool = typer.Option(False, "-f", "--force", help="Re-evaluate even if results exist"),
    filter_spec: str = typer.Option("", "--filter", help="Filter instance IDs by regex"),
    slice_spec: str = typer.Option("", "--slice", help="Slice specification (e.g. '0:5')"),
    summarize_only: bool = typer.Option(False, "--summarize-only", help="Skip evaluation; just read existing results"),
    image_tag: str = typer.Option("task_patched", "--image-tag", help="Docker image tag containing the ground-truth binary"),
    archive_name: str = typer.Option(
        "tests.tar.gz",
        "--archive-name",
        help="Generated test-suite archive name inside each <instance_id>/ directory.",
    ),
    output: str = typer.Option(
        "",
        "-o",
        "--output",
        help="Write results under this directory instead of in-place. "
        "For each source S, test_eval.json files land at <output>/<S.name>/<instance_id>/.",
    ),
    tests_dir: str = typer.Option(
        "",
        "--tests-dir",
        help="Load generated test-suite payloads from this local directory instead of SOURCES. "
        "Expected layout: <tests-dir>/<instance_id>/tests.tar.gz, "
        "<tests-dir>/<instance_id>/eval/run.sh, or branch directories containing eval/run.sh.",
    ),
    ground_truth_dir: str = typer.Option(
        "",
        "--ground-truth-dir",
        help="Override the task image executable with <dir>/<instance_id>/executable for ground-truth and mutant evaluation. "
        "Pass hf://<repo_id>[@revision] to download it from a HuggingFace dataset uploaded with "
        "scripts/dataset/upload_ground_truth_to_hf.py instead of storing it locally.",
    ),
    reference_tests_dir: str = typer.Option(
        "extracted-tests",
        "--reference-tests-dir",
        help="Discover immutable top-level ELF support executables from reference-test branches under this directory. "
        "Pass hf://<repo_id>[@revision] to download them from a HuggingFace dataset uploaded with "
        "scripts/dataset/upload_reference_tests_to_hf.py.",
    ),
    mutants_dir: str = typer.Option(
        "",
        "--mutants-dir",
        help="Load mutants from <mutants-dir>/<instance_id>/mutants.json or repo_N/executable and run generated tests against them after the ground-truth run. "
        "Pass hf://<repo_id>[@revision] to download mutants uploaded with scripts/dataset/upload_mutant_store_to_hf.py instead of storing them locally.",
    ),
    skipped_tests: str = typer.Option(
        "",
        "--skipped-tests",
        help="Run-scoped skipped-test JSON file or directory containing <instance_id>.json.",
    ),
    skipped_mutants: str = typer.Option(
        "",
        "--skipped-mutants",
        help="Run-scoped skipped-mutant JSON file or directory containing <instance_id>.json; listed mutants do not count toward mutation score.",
    ),
    detailed_logs: bool = typer.Option(False, "--detailed-logs", help="Log the per-test failure matrix for each evaluated executable."),
    reference_trials: int = typer.Option(1, "--reference-trials", min=1, help="Run the generated suite against the ground-truth executable this many times; differing pass/fail results are flaky."),
) -> None:
    """Evaluate generated test suites against ProgramBench ground truth.

    Accepts one or more paths to run directories containing
    <instance_id>/tests.tar.gz by default. Each archive must unpack an
    eval/run.sh script, and that script must write JUnit XML to
    eval/results.xml after running tests against ./executable.

    \b
    Examples:
        programbench eval-tests output/test_run
        programbench eval-tests output/test_run --archive-name generated_tests.tar.gz
        programbench eval-tests output/test_run --workers 4 --force
        programbench eval-tests output/test_run -w 4 --mutant-workers 2 --docker-cpus 8
        programbench eval-tests output/test_run --filter 'eradman__entr.*'
        programbench eval-tests output/test_run --tests-dir extracted-tests
        programbench eval-tests ~/generated-tests -o ~/generated-test-eval-out
    """
    from programbench.eval.test_suite_eval_batch import run_test_suite_eval_batch

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    run_test_suite_eval_batch(
        sources=sources,
        force=force,
        workers=workers,
        docker_cpus=docker_cpus,
        cpu_budget=cpu_budget,
        branch_workers=branch_workers,
        filter_spec=filter_spec,
        slice_spec=slice_spec,
        summarize_only=summarize_only,
        image_tag=image_tag,
        output=output,
        archive_name=archive_name,
        tests_dir=tests_dir,
        ground_truth_dir=ground_truth_dir,
        reference_tests_dir=reference_tests_dir,
        mutants_dir=mutants_dir,
        skipped_tests=skipped_tests,
        skipped_mutants=skipped_mutants,
        detailed_logs=detailed_logs,
        reference_trials=reference_trials,
    )
    logging.getLogger("programbench.eval.test_suite_eval_batch").info("Finished eval-tests")


@app.command()
def info(
    run_dir: Path = typer.Argument(..., help="Run directory containing <instance_id>/<instance_id>.eval.json"),
) -> None:
    """Print scores and warnings for an evaluated run directory.

    Eval.json files persist branch errors and warnings recorded during the
    original eval, including for branches that have since been marked
    ``ignored: true``. ``info`` reads each instance's tests.json to drop
    those stale entries before scoring.

    \b
    Examples:
        programbench info ~/gold-eval-9/gold
        programbench info output/run_name
    """
    from rich.console import Console

    from programbench.eval.eval import EvaluationResult
    from programbench.eval.eval_batch import BatchEvalSummary, InstanceEvalSummary
    from programbench.utils.load_data import get_active_branches, get_ignored_tests, load_all_instances

    eval_paths = sorted(run_dir.glob("*/*.eval.json"))
    if not eval_paths:
        raise typer.BadParameter(f"No <iid>/<iid>.eval.json files found under {run_dir}")

    instances = {i["instance_id"]: i for i in load_all_instances(include_tests=True)}

    summaries: list[InstanceEvalSummary] = []
    for p in eval_paths:
        iid = p.parent.name
        result = EvaluationResult.model_validate_json(p.read_text())
        inst = instances.get(iid)
        if inst is not None:
            active = get_active_branches(inst)
            ignored_tests = get_ignored_tests(inst)
            ignored_branches = {b for b in result.test_branches if b not in set(active)}
            result = result.for_branches(active).without_ignored(ignored_tests)
            if ignored_branches:
                result.warnings = [w for w in result.warnings if not any(f"branch {b}" in w for b in ignored_branches)]
        summaries.append(InstanceEvalSummary.from_eval_result(iid, result))

    console = Console()
    console.print(BatchEvalSummary(summaries=summaries).summary())


@app.command("build-mutants")
def build_mutants(
    mutants_dir: Path = typer.Argument(..., help="Mutant store containing <instance_id>/mutants.json"),
    task: str = typer.Option(..., "--task", help="Instance id to build"),
    docker_cpus: int = typer.Option(DOCKER_CPUS, "--docker-cpus", help="CPU cores allotted to the build container"),
    mutant_build_jobs: int = typer.Option(
        1,
        "--mutant-build-jobs",
        min=1,
        help="Number of mutant repositories to compile concurrently.",
    ),
    cleanroom_base_image: str = typer.Option(
        "",
        "--cleanroom-base-image",
        help="Task cleanroom base image override. Defaults to PROGRAMBENCH_MUTANT_CLEANROOM_BASE_IMAGE when set.",
    ),
    timeout: int = typer.Option(7200, "--timeout", help="Build timeout in seconds"),
) -> None:
    """Compile a mutant store left without executables by an interrupted run.

    Generation records its plan and manifest before the executables exist, so a
    crash in between produces a store that resumes as complete while every
    mutant evaluates as missing_mutant_payload. This compiles the repo_N sources
    in the same eval-compatible image the reference build uses, and is a no-op
    for a store whose payloads already resolve.

    \b
    Examples:
        programbench build-mutants output/run/mutants --task abishekvashok__cmatrix.5c082c6
    """
    from programbench.mutants import build_mutant_executables
    from programbench.utils.load_data import load_all_instances

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    result = build_mutant_executables(
        instance=next(
            instance
            for instance in load_all_instances(include_tests=False)
            if instance["instance_id"] == task
        ),
        output=mutants_dir,
        cleanroom_base_image=cleanroom_base_image
        or os.environ.get("PROGRAMBENCH_MUTANT_CLEANROOM_BASE_IMAGE", ""),
        docker_cpus=docker_cpus,
        mutant_build_jobs=mutant_build_jobs,
        timeout=timeout,
    )
    if result["status"] == "skipped":
        print(f"Mutant store for {task} is {result['reason']}; nothing to build")
        return
    if result["status"] != "ok":
        print(f"{result['status']}: {task} {result.get('reason', '')}".rstrip())
        raise typer.Exit(1)
    print(
        f"Built {task}: {len(result['mutant_repositories'])} mutant executable(s), "
        f"{result['compact_storage']['compacted']} compacted"
    )


@app.command("seal-mutants")
def seal_mutants(
    mutants_dir: Path = typer.Argument(..., help="Mutant store containing <instance_id>/mutants.json"),
    task: str = typer.Option(..., "--task", help="Instance id to seal"),
    ground_truth_dir: Path = typer.Option(
        Path("ground_truth/implementation"),
        "--ground-truth-dir",
        help="Ground-truth implementations the repo_N sources are diffed against",
    ),
) -> None:
    """Collapse a generated mutant suite to the information needed to rebuild it.

    Mutant executables move into a compressed content-addressed store and each
    repo_N tree is replaced by its diff against the ground-truth implementation,
    so the suite stops costing a near-complete source copy per mutant. Every
    iteration then shares this one sealed store instead of carrying a copy.

    \b
    Examples:
        programbench seal-mutants output/run/mutants --task abishekvashok__cmatrix.5c082c6
    """
    from programbench.mutant_storage import seal_mutant_store

    status = seal_mutant_store(mutants_dir / task, ground_truth_dir / task)
    print(
        f"Sealed {task}: {status['repos']} repo(s) -> {status['blobs']} source blob(s), "
        f"{status['compacted']} executable(s) compacted"
    )


@app.command("materialize-mutants")
def materialize_mutants(
    mutants_dir: Path = typer.Argument(..., help="Mutant store containing <instance_id>/sources.json"),
    task: str = typer.Option(..., "--task", help="Instance id to materialize"),
    output: Path = typer.Option(
        None,
        "--output",
        help="Write the repo_N trees here instead of unsealing the store in place",
    ),
    ground_truth_dir: Path = typer.Option(
        Path("ground_truth/implementation"),
        "--ground-truth-dir",
        help="Ground-truth implementations the repo_N sources are rebuilt from",
    ),
) -> None:
    """Rebuild the repo_N source trees a sealed mutant store was collapsed into.

    Sealing deletes repo_N, so anything that edits mutant sources -- another
    ensure-mutants-killed pass, manual inspection -- needs them back. Without
    --output the store is unsealed in place and seal-mutants collapses it again;
    a mutant whose tree is already present is left alone either way.

    \b
    Examples:
        programbench materialize-mutants output/run/mutants --task abishekvashok__cmatrix.5c082c6
    """
    import json
    import shutil

    from programbench.mutant_storage import (
        DIGEST_FILE, SOURCE_ARTIFACT_DIR, SOURCES_MANIFEST, materialize_mutant_sources,
    )

    instance_root = mutants_dir / task
    destination = output or instance_root
    materialized = 0
    for mutant_id in json.loads((instance_root / SOURCES_MANIFEST).read_text())["overlays"]:
        if (destination / mutant_id).is_dir():
            continue
        with materialize_mutant_sources(instance_root, mutant_id, ground_truth_dir / task) as repo:
            shutil.copytree(repo, destination / mutant_id, symlinks=True)
        materialized += 1
    if output is None:
        shutil.rmtree(instance_root / SOURCE_ARTIFACT_DIR)
        (instance_root / SOURCES_MANIFEST).unlink()
        (instance_root / DIGEST_FILE).unlink(missing_ok=True)
    print(f"Materialized {task}: {materialized} repo(s) under {destination}")


@app.command("extract-mutant")
def extract_mutant(
    mutants_dir: Path = typer.Argument(..., help="Mutant store containing <instance_id>/mutants.json"),
    task: str = typer.Option(..., "--task", help="Instance id to extract from"),
    mutant: str = typer.Option(..., "--mutant", help="Mutant id to extract, e.g. repo_19"),
    output: Path = typer.Option(
        Path("output/mutant-sandbox"),
        "--output",
        help="Root to write <task>/<mutant> into",
    ),
    ground_truth_dir: Path = typer.Option(
        Path("ground_truth/implementation"),
        "--ground-truth-dir",
        help="Ground-truth implementations the repo_N sources are rebuilt from",
    ),
    sources: bool = typer.Option(
        False, "--sources", help="Also rebuild the repo_N source tree beside the executable"
    ),
) -> None:
    """Unpack one sealed mutant so it can be run by hand.

    materialize-mutants rebuilds every repo_N source tree and never restores the
    compiled artifact. Probing a spec wording against a single mutant needs the
    opposite: that mutant's executable, and its sources only on request.

    \b
    Examples:
        programbench extract-mutant ground_truth/mutants --task nachoparker__dutree.44e877d --mutant repo_49
    """
    import json
    import shutil

    from programbench.mutant_storage import materialize_mutant_payload, materialize_mutant_sources
    from programbench.mutants import load_mutant_suite

    instance_root, suite = load_mutant_suite(mutants_dir, task)
    spec = next(item for item in suite.mutants if item.id == mutant)
    destination = output / task / mutant
    destination.mkdir(parents=True, exist_ok=True)
    with materialize_mutant_payload(instance_root, spec) as payload:
        shutil.copy2(payload, destination / "executable")
    (destination / "mutant.json").write_text(json.dumps(spec.model_dump(), indent=2, sort_keys=True) + "\n")
    if sources:
        with materialize_mutant_sources(instance_root, mutant, ground_truth_dir / task) as repo:
            shutil.copytree(repo, destination / mutant, symlinks=True, dirs_exist_ok=True)
    print(f"Extracted {task}/{mutant} to {destination}")


@app.command("record-generated-files")
def record_generated_files_command(
    task: str = typer.Option(..., "--task", help="Instance id to record"),
    ground_truth_dir: Path = typer.Option(
        Path("ground_truth/implementation"),
        "--ground-truth-dir",
        help="Ground-truth implementations to build",
    ),
    image: str = typer.Option(..., "--image", help="Cleanroom base image the build image derives from"),
    docker_cpus: int = typer.Option(DOCKER_CPUS, "--docker-cpus", help="CPU cores for the build container"),
    force: bool = typer.Option(False, "--force", help="Re-record even when a manifest already exists"),
) -> None:
    """Record which repository paths ./build.sh produces rather than reads.

    Mutating a generated path is a behavioural no-op, because the build
    overwrites the edit. Mutant generation withholds these paths so the agent
    mutates the source they are derived from instead.

    \b
    Examples:
        programbench record-generated-files --task sqlite__sqlite.839433d --image programbench/sqlite_1776_sqlite.839433d:task_cleanroom
    """
    from programbench.generated_files import record_generated_files

    status = record_generated_files(
        task=task,
        implementation=ground_truth_dir / task,
        image=image,
        docker_cpus=docker_cpus,
        force=force,
    )
    print(f"{status['status']} {task}: {status['generated']} generated path(s)")


@app.command("classify-failures")
def classify_failures(
    source: Path = typer.Argument(..., help="Eval JSON file or iterative output directory"),
    task: str = typer.Option("", "--task", help="Task instance id; required when SOURCE contains multiple eval files"),
    spec_dir: str = typer.Option("", "--spec-dir", help="Specification directory. Inferred for iterative directories."),
    test_spec_links: str = typer.Option("", "--test-spec-links", help="test_spec_links.json used to annotate relevant spec sections"),
    output: str = typer.Option("", "-o", "--output", help="Output JSON path. Defaults beside SOURCE."),
    model: str = typer.Option("codex/gpt-5.6-luna", "-m", "--model", help="Codex model used for attribution"),
    reasoning_effort: str = typer.Option("high", "--reasoning-effort", help="Codex reasoning effort"),
    codex_command: str = typer.Option(
        "",
        "--codex-command",
        help="Codex command prefix. The attribution prompt is appended as the final argument.",
    ),
    timeout: int = typer.Option(900, "--timeout", help="Classifier timeout in seconds"),
    limit: int = typer.Option(0, "--limit", help="Classify at most this many failures; 0 means all"),
    branch_workers: int = typer.Option(
        4,
        "--branch-workers",
        help="Classify test branches with this many parallel Codex instances",
    ),
    binary_id: str = typer.Option(
        "",
        "--binary-id",
        help="For .test_eval.json files, classify this binary id. Default is the ground-truth binary.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Write classifier prompts without calling Codex"),
    force: bool = typer.Option(False, "-f", "--force", help="Overwrite an existing attribution report"),
) -> None:
    """Classify candidate failures against the current specification."""
    from programbench.failure_attribution import (
        DEFAULT_BRANCH_WORKERS,
        DEFAULT_CODEX_COMMAND,
        check_attribution_usable,
        classify_failures as run_failure_attribution,
        default_output_path,
        infer_spec_dir,
        infer_task_from_eval_json,
        resolve_eval_json,
    )

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    eval_json = resolve_eval_json(source, task=task)
    selected_task = task or infer_task_from_eval_json(eval_json)
    selected_spec_dir = Path(spec_dir) if spec_dir else infer_spec_dir(source, task=selected_task)
    selected_output = Path(output) if output else default_output_path(source, eval_json)
    selected_model = _codex_cli_model(model, command_name="classify-failures")
    selected_branch_workers = branch_workers if branch_workers != 4 else DEFAULT_BRANCH_WORKERS

    report = run_failure_attribution(
        eval_json=eval_json,
        spec_dir=selected_spec_dir,
        test_spec_links=Path(test_spec_links) if test_spec_links else None,
        output=selected_output,
        model=selected_model,
        reasoning_effort=reasoning_effort,
        codex_command=codex_command or DEFAULT_CODEX_COMMAND,
        timeout=timeout,
        limit=limit,
        branch_workers=selected_branch_workers,
        binary_id=binary_id,
        dry_run=dry_run,
        force=force,
    )
    typer.echo(f"Wrote failure attribution report: {selected_output}")
    typer.echo(
        "Failure attribution summary: "
        + ", ".join(f"{fault}={count}" for fault, count in sorted(report.summary.items()))
    )
    check_attribution_usable(report.failures, "Failure attribution")


@app.command("postfix-spec")
def postfix_spec(
    source: Path = typer.Option(Path("output/debug_iterative_v43_production/iter_0"), "--source", help="Iteration directory holding spec/ and test-spec-links/"),
    output: Path = typer.Option(Path("output/debug_iterative_v43_production/iter_0_postfix"), "-o", "--output", help="Output iteration directory"),
    skipped_tests: Path = typer.Option(Path("ground_truth/skipped-tests"), "--skipped-tests", help="Skipped-test JSON file or directory containing <instance_id>.json"),
    tests_dir: Path = typer.Option(Path("extracted-tests"), "--tests-dir", help="Reference-test root containing <instance_id>/<branch>/eval/"),
    tasks_file: str = typer.Option("ground_truth/valid_task.txt", "--tasks", help="File listing the instance IDs to run, one per line. Pass '' to run every task under --source."),
    filter_spec: str = typer.Option("", "--filter", help="Filter instance IDs by regex"),
    slice_spec: str = typer.Option("", "--slice", help="Slice specification (e.g. '0:5' for first 5 instances)"),
    workers: int = typer.Option(1, "-w", "--workers", help="Number of tasks pruned in parallel"),
    section_workers: int = typer.Option(4, "--section-workers", help="Spec sections pruned in parallel per task"),
    model: str = typer.Option("codex/gpt-5.6-luna", "-m", "--model", help="Codex model used for pruning"),
    reasoning_effort: str = typer.Option("high", "--reasoning-effort", help="Codex reasoning effort"),
    codex_command: str = typer.Option("", "--codex-command", help="Codex command prefix. The prune prompt is appended as the final argument."),
    timeout: int = typer.Option(3600, "--timeout", help="Per-section Codex timeout in seconds"),
    force: bool = typer.Option(False, "-f", "--force", help="Overwrite an existing <output>/spec/<instance_id>/"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Copy the specs and report which sections would be pruned"),
) -> None:
    """Remove specification discussion that only the dropped reference tests exercised.

    Tests skipped as `internet_required`, `our_gt_broad_mutant_kill`, or
    `our_gt_flaky` no longer score, so the requirements written for them are
    dead weight. For every spec section those tests are linked to, one Codex
    session sees that section alone, the source of the dropped tests and of
    the tests the section keeps, and the reference binary, and deletes only
    what the dropped set justified.

    \b
    Example:
        uv run programbench postfix-spec --filter abishekvashok__cmatrix.5c082c6 --force
    """
    from programbench.spec_postfix import DEFAULT_CODEX_COMMAND, run_postfix_batch, summary_lines

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    results = run_postfix_batch(
        source=source,
        output=output,
        skipped_tests=skipped_tests,
        tests_dir=tests_dir,
        tasks_file=Path(tasks_file) if tasks_file else None,
        filter_spec=filter_spec,
        slice_spec=slice_spec,
        workers=workers,
        section_workers=section_workers,
        model=_codex_cli_model(model, command_name="postfix-spec"),
        reasoning_effort=reasoning_effort,
        codex_command=codex_command or DEFAULT_CODEX_COMMAND,
        timeout=timeout,
        force=force,
        dry_run=dry_run,
    )
    if not results:
        typer.echo("No instances selected for spec postfix.")
        return

    for line in summary_lines(results):
        typer.echo(line)
    typer.echo(f"Pruned specifications: {output / 'spec'}")

    if any(result["status"] not in {"ok", "skipped"} for result in results):
        raise typer.Exit(1)
