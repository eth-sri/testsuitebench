from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "construction" / "iterate_spec.sh"


def test_iteration_pipeline_uses_fixed_tests_directly_and_snapshots_other_inputs() -> None:
    script = SCRIPT.read_text()

    assert "candidate_stage=\"${next_iter}/stages/candidate-evaluation\"" in script
    assert "--cleanroom \"${candidate_spec}\"" in script
    assert "--tests-dir \"${tests_dir}\"" in script
    assert "snapshot_inputs \"${candidate_stage}\" spec \"${source_spec}\"" in script
    assert "candidate_test=" not in script

    assert "generated_test_stage=\"${next_iter}/stages/generated-test-generation\"" in script
    assert "--cleanroom-dir \"${generated_test_spec_snapshot}\"" in script
    assert 'snapshot_inputs "${generated_test_stage}" --force spec "${source_spec}"' in script
    assert 'snapshot_inputs "${generated_test_stage}" --force spec "${polished_spec}"' not in script

    assert "mutant_eval_stage=\"${next_iter}/stages/generated-test-mutant-evaluation\"" in script
    assert "eval-tests \"${mutant_eval_test_snapshot}\"" in script
    assert "--spec-dir \"${generated_test_spec_snapshot}\"" in script
    assert "--tests-dir \"${mutant_eval_test_snapshot}\"" in script
    # The sealed store is shared and read in place, never snapshotted per iteration.
    assert "--mutants-dir \"${mutants_dir}\"" in script
    assert "mutant_eval_mutant_snapshot" not in script
    assert 'mutants_dir=${mutants_dir:-${iter_root}/mutants}' in script
    assert "--ground-truth-dir \"${ground_truth_dir}\"" in script
    assert "Polishing only the spec against immutable mutants" not in script
    assert "scripts/construction/polish_mutants.sh" not in script
    assert "from reference-test, generated-test and mutant evidence" in script


def test_iteration_pipeline_never_copies_reference_tests() -> None:
    script = SCRIPT.read_text()
    classify_block = script.split("classify_args=(", 1)[1].split("        )", 1)[0]

    assert "--assume-ground-truth-valid" not in script
    assert '--tests-dir "${tests_dir}"' not in classify_block
    assert '--reference-tests-dir "${tests_dir}"' in classify_block
    assert "--test-spec-links-output" not in classify_block
    assert '--test-spec-links "${this_iter}/test-spec-links/${task}/test_spec_links.json"' in classify_block
    polish_block = script.split("polish_args=(", 1)[1].split("        )", 1)[0]
    assert '--tests-dir "${tests_dir}"' in polish_block
    assert '--link-branch-workers "${classify_branch_workers}"' in polish_block

    assert "Polishing the specification and carrying its initial test links" in script
    assert "default_tests_dir=extracted-tests" in script
    assert "source_test=" not in script
    assert "${this_iter}/test/" not in script
    assert "${next_iter}/test/" not in script
    assert "snapshot_inputs \"${candidate_stage}\" spec \"${source_spec}\" test" not in script
    assert "scripts/construction/improve_ground_truth_tests.sh" not in script
    assert "ground-truth-mutant-evaluation" not in script
    assert "--skip-ground-truth-test-improvement" not in script
    assert "--skip-ground-truth-mutant-eval" not in script
    assert "Generated T" in script
    assert "never becomes the reference suite" in script


def test_iteration_pipeline_updates_test_spec_links_after_polish() -> None:
    script = SCRIPT.read_text()

    classify = script.index("scripts/eval/classify_failures.sh")
    mutant_classify = script.index("scripts/eval/classify_mutants.sh")
    polish = script.index("scripts/construction/polish_iteration.sh")
    # One polish per iteration, after both evaluation directions were classified against one spec.
    assert classify < mutant_classify < polish
    assert script.count("scripts/construction/polish_iteration.sh") == 1
    classify_block = script.split("classify_args=(", 1)[1].split("        )", 1)[0]
    polish_block = script.split("polish_args=(", 1)[1].split("        )", 1)[0]
    assert "--test-spec-links-output" not in classify_block
    assert '--tests-dir "${tests_dir}"' in polish_block
    assert "scripts/link_reference_tests_to_spec.sh" not in script
    assert "mutant_polish_args=(" not in script


def test_iteration_pipeline_checkpoints_each_expensive_phase() -> None:
    script = SCRIPT.read_text()

    assert 'iteration_checkpoint="${next_iter}/stages/${task}/pipeline-checkpoints.tsv"' in script
    assert 'if [ "${force}" = true ]; then\n        : >"${iteration_checkpoint}"' in script
    for phase in (
        "candidate-solve",
        "candidate-eval",
        "candidate-classify",
        "spec-polish",
        "generated-test-generation",
        "generated-test-mutant-eval",
        "generated-test-mutant-classify",
    ):
        assert phase in script
    assert "generated-test-spec-polish" not in script

    assert 'phase "Skipping completed phase ${checkpoint_phase}"' in script
    assert 'record_iteration_checkpoint "${checkpoint_file}" "${checkpoint_phase}"' in script


def test_candidate_eval_checkpoint_requires_the_task_eval_artifact() -> None:
    script = SCRIPT.read_text()

    assert 'candidate_eval_json="${candidate_executable}/${task}/${task}.eval.json"' in script
    assert '&& [ -f "${candidate_eval_json}" ]; then' in script
    assert "Candidate-eval checkpoint is stale; expected result is missing" in script
    assert "Candidate evaluation did not produce" in script


def test_iteration_pipeline_routes_each_agent_step_independently() -> None:
    script = SCRIPT.read_text()
    expected_defaults = {
        "solve_codex": "gpt-5.6-luna max",
        "classify_failures": "gpt-5.6-luna max",
        "polish_iteration": "gpt-5.6-sol high",
        "generate_tests": "gpt-5.6-luna max",
        "classify_mutants": "gpt-5.6-luna max",
        "polish_generated_test_spec": "gpt-5.6-sol high",
    }
    for step, route in expected_defaults.items():
        assert f"programbench_agent_route_register {step} {route}" in script
        # The second polish is folded into polish_iteration; its route stays registered so the
        # batch runner's --step-model for it is still accepted.
        used = step != "polish_generated_test_spec"
        assert (f"PROGRAMBENCH_ROUTE_MODEL[{step}]" in script) is used
        assert (f"PROGRAMBENCH_ROUTE_REASONING[{step}]" in script) is used
    assert "--step-model)" in script
    assert "--step-reasoning)" in script
    assert 'iterate_agent_routes_file="${iter_root}/agent-routes/${task}.tsv"' in script


def test_iteration_pipeline_applies_per_stage_cpu_policy() -> None:
    script = SCRIPT.read_text()

    assert "default_cpu_budget=32" in script
    assert '--docker-cpus "${cpu_budget}"' in script
    assert script.count('--cpu-budget "${cpu_budget}"') == 2
    assert 'PROGRAMBENCH_DOCKER_CPUS="${classifier_cpus}"' in script
    assert 'PROGRAMBENCH_DOCKER_CPUS="${agent_cpus}"' in script
    assert '--docker-cpus "${agent_cpus}"' in script


def test_iteration_pipeline_keeps_best_generated_test_suite() -> None:
    script = SCRIPT.read_text()

    assert "default_min_generated_tests=5" in script
    assert "default_reference_trials=3" in script
    assert '--reference-trials "${reference_trials}"' in script
    assert "default_generate_test_attempts=3" in script
    assert '--min-generated-tests)' in script
    assert '--generate-test-attempts)' in script
    assert 'python3 scripts/construction/count_generated_tests.py "${generated_test_archive}"' in script
    assert 'generation_attempt <= generate_test_attempts' in script
    assert "returning to generate-tests" in script
    assert 'cp "${generated_test_archive}" "${best_generated_test_archive}"' in script
    assert 'mv "${best_generated_test_archive}" "${generated_test_archive}"' in script
    assert "continuing to eval-tests" in script
    assert "Refusing to run eval-tests with an undersized suite" not in script
    assert 'if run_cmd_to_file "${attempt_log}" "${generate_test_args[@]}"; then' in script
    assert "Generated-test command failed; returning to generate-tests." in script
    checkpoint_check = script.index(
        'if iteration_checkpoint_has_phase "${iteration_checkpoint}" generated-test-generation'
    )
    generated_snapshot = script.index(
        'snapshot_inputs "${generated_test_stage}" --force spec "${source_spec}"'
    )
    assert checkpoint_check < generated_snapshot

    count_check = script.rindex('if [ "${generated_test_count}" -lt "${min_generated_tests}" ]')
    eval_tests = script.index('uv run programbench eval-tests')
    assert count_check < eval_tests


def test_iteration_pipeline_retries_failed_candidate_implementation() -> None:
    script = SCRIPT.read_text()

    assert "default_solve_attempts=3" in script
    assert '--solve-attempts)' in script
    assert 'solve_attempt <= solve_attempts' in script
    assert 'if run_cmd "${solve_args[@]}"; then' in script
    assert "Candidate solve or fresh build verification failed; returning to implementation." in script
    assert 'record_iteration_checkpoint "${iteration_checkpoint}" candidate-solve' in script
    assert 'traj.attempt_${solve_attempt}.json' in script
    assert 'submission.attempt_${solve_attempt}.tar.gz' in script
    assert '! iteration_checkpoint_has_phase "${iteration_checkpoint}" spec-polish' in script


def test_candidate_evaluation_uses_solver_image() -> None:
    script = SCRIPT.read_text()

    assert 'evaluation_image="${cleanroom_base_image}"' in script
    assert 'scripts/docker/install_codex_cleanroom.sh --task "${task}" --print-image' in script
    assert 'eval_args+=(--image "${evaluation_image}")' in script


def test_generated_test_authoring_uses_task_codex_cleanroom_image() -> None:
    script = SCRIPT.read_text()

    assert 'generated_test_image="${cleanroom_base_image}"' in script
    assert 'scripts/docker/install_codex_cleanroom.sh --task "${task}"' in script
    assert 'generate_test_args+=(--cleanroom-base-image "${generated_test_image}")' in script


def test_generated_suite_that_crashes_in_its_own_code_is_regenerated_once_before_polish() -> None:
    script = SCRIPT.read_text()

    assert "default_suite_regenerations=1" in script
    assert "--suite-regenerations)" in script
    assert "uv run python -m programbench.generated_suite_quality" in script
    assert 'if [ "${quality_status}" -ne 3 ]; then' in script
    assert 'tests.rejected_${suite_regenerations}.tar.gz' in script
    assert "sed -i '/^generated-test-generation\\t/d;/^generated-test-mutant-eval\\t/d'" in script
    gate = script.index("programbench.generated_suite_quality")
    assert script.index("scripts/eval/classify_mutants.sh") > gate > script.index("uv run programbench eval-tests")
