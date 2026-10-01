from pathlib import Path


ROOT = Path(__file__).parents[1]


def script(name: str) -> str:
    return (ROOT / "scripts" / "construction" / name).read_text()


def test_batch_runner_orchestrates_four_scripts_in_order() -> None:
    runner = script("run_iterative_all.sh")

    prepare = runner.index("bash scripts/construction/prepare_tests.sh")
    initialize = runner.index("bash scripts/construction/run_init.sh")
    iterate = runner.index("bash scripts/construction/iterate_spec.sh")
    postprocess = runner.index("bash scripts/construction/run_postprocess.sh")

    assert prepare < initialize < iterate < postprocess
    assert "bash scripts/construction/prepare_reference_tests.sh" not in runner
    assert "uv run programbench improve-spec" not in runner
    assert "bash scripts/construction/generate_mutants.sh" not in runner
    assert "bash scripts/construction/ensure_mutants_killed.sh" not in runner
    assert '[ -f "cleanroom/original/${task}/executable" ]' not in runner


def test_prepare_tests_owns_reusable_skip_preparation_outside_iteration_root() -> None:
    runner = script("run_iterative_all.sh")
    prepare = script("prepare_tests.sh")

    assert "prepared_tests_root=output/prepared-tests" in runner
    assert "ground_truth_root=ground_truth" in runner
    assert 'skipped_tests_root="${ground_truth_root}/skipped-tests"' in runner
    assert 'skipped_tests_root="${iter_root}/skipped-tests"' not in runner
    assert '--output-root "${prepared_tests_root}"' in runner
    assert "bash scripts/construction/prepare_reference_tests.sh" in prepare
    assert "ground_truth_root=ground_truth" in prepare
    assert 'skipped_tests_file="${skipped_tests_root}/${task}.json"' in prepare
    assert 'work_dir="${output_root}/work/${task}"' in prepare
    assert 'our_implementation="${ground_truth_root}/implementation/${task}"' in prepare
    assert 'our_executable="${ground_truth_root}/executable/${task}/executable"' in prepare
    assert runner.count('--ground-truth-dir "${ground_truth_root}/executable"') == 2
    assert '--build-image "${build_image}"' in prepare
    assert "Reusing prepared tests" in prepare
    assert "Refreshing incomplete prepared tests" in prepare
    assert '[ "${force}" = true ] || [ "${refresh_incomplete}" = true ]' in prepare
    assert "iter_root" not in prepare


def test_run_init_owns_all_pre_iteration_stages_in_order() -> None:
    initialize = script("run_init.sh")

    improve = initialize.index("uv run programbench improve-spec")
    link = initialize.index("uv run python -m programbench.reference_test_linking")
    mutants = initialize.index("bash scripts/construction/generate_mutants.sh")
    validate = initialize.index("bash scripts/construction/ensure_mutants_killed.sh")

    assert improve < link < mutants < validate
    assert '--testdir "${tests_dir}"' in initialize
    assert '--repo-dir "${tests_dir}"' in initialize
    assert initialize.count('--skipped-tests "${skipped_tests}"') >= 2
    assert '--ground-truth-dir "${ground_truth_dir}"' in initialize
    assert "bash scripts/construction/prepare_reference_tests.sh" not in initialize
    assert "bash scripts/construction/iterate_spec.sh" not in initialize


def test_initialization_and_iteration_keep_stage_checkpoints() -> None:
    runner = script("run_iterative_all.sh")
    initialize = script("run_init.sh")

    assert 'record_stage_checkpoint "${checkpoint_file}" prepare-skipped-tests' in runner
    for stage in ("improve-spec", "link-reference-tests", "generate-mutants", "ensure-mutants-killed"):
        assert f"checkpoint_has_stage {stage}" in initialize
        assert f"record_stage_checkpoint {stage}" in initialize
    assert 'record_stage_checkpoint "${checkpoint_file}" iterate-spec' in runner
    assert "prepare-reference-tests" not in runner
    assert "prepare-reference-tests" not in initialize


def test_batch_initializer_extends_to_iteration_target_without_replaying() -> None:
    runner = script("run_iterative_all.sh")

    assert "completed_iterations_for_task()" in runner
    assert "generated-test-spec-polish" in runner
    assert "grep -Eq" in runner
    assert "if ! rg -q" not in runner
    assert "tasks.extendable.txt" in runner
    assert "remaining_iterations=" in runner
    assert "--start-iter" in runner
    assert "target-reached" in runner


def test_batch_initializer_retains_routes_concurrency_and_selection() -> None:
    runner = script("run_iterative_all.sh")

    assert "task_cpu_budget=32" in runner
    assert "mutant_build_jobs=8" in runner
    assert 'mutant_build_cpus=${task_cpu_budget}' in runner
    assert 'selected_tasks+=("$2")' in runner
    assert 'candidate_tasks_file="${selected_tasks_file}"' in runner
    assert "programbench_agent_route_register prepare_reference_tests" not in runner
    for step in (
        "improve_spec",
        "link_reference_tests",
        "generate_mutants",
        "ensure_mutants_killed",
        "solve_codex",
        "classify_failures",
        "polish_iteration",
        "generate_tests",
        "classify_mutants",
        "polish_generated_test_spec",
    ):
        assert f"programbench_agent_route_register {step} " in runner


def test_postprocess_is_present_noop_hook() -> None:
    postprocess = script("run_postprocess.sh")

    assert "Reserved for post-iteration processing" in postprocess
    assert "exit 0" in postprocess



def test_batch_runner_keeps_numbered_logs_for_each_attempt() -> None:
    runner = script("run_iterative_all.sh")

    assert "next_task_log()" in runner
    assert "latest_task_log()" in runner
    assert "printf '%s/%s_%d.log" in runner
    assert 'task_log=$(next_task_log "${task}")' in runner
    assert ') >"${task_log}" 2>&1' in runner
    assert 'local task_log="${log_dir}/${task}.log"' not in runner


def test_batch_runner_isolates_invocation_metadata_for_shared_iteration_roots() -> None:
    runner = script("run_iterative_all.sh")

    assert 'run_dir="${batch_dir}/runs/${run_id}"' in runner
    assert 'agent_routes_file="${run_dir}/agent-routes.tsv"' in runner
    assert 'pending_tasks_file="${run_dir}/tasks.pending.txt"' in runner
    assert 'started_tasks_file="${run_dir}/tasks.started.txt"' in runner
    assert '--output "${run_dir}/token_usage.tsv"' in runner
    assert '--task "${summary_task}"' in runner
    assert 'agent_routes_file="${batch_dir}/agent-routes.tsv"' not in runner
    assert 'pending_tasks_file="${batch_dir}/tasks.pending.txt"' not in runner


def test_batch_completion_counts_only_the_current_invocation() -> None:
    runner = script("run_iterative_all.sh")

    assert 'done <"${pending_tasks_file}"' in runner
    assert "rg -l '^ok\\t'" not in runner
