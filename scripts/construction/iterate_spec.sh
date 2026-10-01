#!/usr/bin/env bash
set -euo pipefail

default_task=ast-grep__ast-grep.dde0fe0
default_iter_root=output/iterative
default_tests_dir=extracted-tests
default_ground_truth_dir=ground_truth/executable
default_start_iter=0
default_iterations=3
default_workers=1
default_branch_workers=16
default_classify_limit=0
default_classify_branch_workers=4
default_mutant_classify_batch_size=50
default_mutant_classify_batch_workers=4
default_solve_timeout=21600
default_test_timeout=21600
default_cpu_budget=32
default_agent_cpus=6
default_classifier_cpus=2
default_polish_timeout=3600
default_junit_completeness_check=false
default_min_generated_tests=5
default_reference_trials=3
default_solve_attempts=3
default_generate_test_attempts=3
default_suite_regenerations=1

global_model_override=
global_reasoning_override=
task=${default_task}
iter_root=${default_iter_root}
mutants_dir=
tests_dir=${default_tests_dir}
ground_truth_dir=${default_ground_truth_dir}
skipped_tests=
start_iter=${default_start_iter}
iterations=${default_iterations}
workers=${default_workers}
branch_workers=${default_branch_workers}
classify_limit=${default_classify_limit}
classify_branch_workers=${default_classify_branch_workers}
mutant_classify_batch_size=${default_mutant_classify_batch_size}
mutant_classify_batch_workers=${default_mutant_classify_batch_workers}
solve_timeout=${default_solve_timeout}
test_timeout=${default_test_timeout}
cpu_budget=${default_cpu_budget}
agent_cpus=${default_agent_cpus}
classifier_cpus=${default_classifier_cpus}
polish_timeout=${default_polish_timeout}
junit_completeness_check=${default_junit_completeness_check}
min_generated_tests=${default_min_generated_tests}
reference_trials=${default_reference_trials}
solve_attempts=${default_solve_attempts}
generate_test_attempts=${default_generate_test_attempts}
suite_regenerations_max=${default_suite_regenerations}
cleanroom_base_image=
force=false
classify_dry_run=false
polish_dry_run=false
skip_solve=false
skip_eval=false
skip_classify=false
skip_mutant_loop=false
skip_generate_tests=false
skip_mutant_eval=false
skip_mutant_classify=false
skip_validity_classify=false
skip_mutation_score=false
skip_polish=false

. scripts/construction/agent_routes.sh
programbench_agent_routes_reset
programbench_agent_route_register solve_codex gpt-5.6-luna max
programbench_agent_route_register classify_failures gpt-5.6-luna max
programbench_agent_route_register polish_iteration gpt-5.6-sol high
programbench_agent_route_register generate_tests gpt-5.6-luna max
programbench_agent_route_register classify_mutants gpt-5.6-luna max
programbench_agent_route_register polish_generated_test_spec gpt-5.6-sol high

usage() {
    cat <<EOF
Usage: $0 [--task TASK] [--model MODEL] [--reasoning EFFORT] [--iter-root DIR] [--tests-dir DIR] [--ground-truth-dir DIR] [--skipped-tests PATH] [--start-iter N] [--iterations N] [--workers N] [--branch-workers N] [--force]

Run iterative ProgramBench specification improvement with fixed reference tests and mutants.

For each iteration N, this script:
  1. Snapshots S=iter_N/spec and uses fixed T directly from extracted-tests
  2. Runs S -> I′ and evaluates I′ with T
  3. Classifies each I′ failure and updates iter_N/test-spec-links; only missing,
     ambiguous, or misleading S is actionable
  4. Polishes only S into iter_N+1; T remains in extracted-tests
  5. Runs S -> T′, then evaluates T′ with the ground-truth I and the shared mutant suite M
  6. Classifies T′ failures and immutable-mutant outcomes
  7. Polishes only S, carries M unchanged, and preserves the initial T-to-S links

The reference suite T and initialized mutant suite M are never polished, strengthened,
or replaced. M lives once in ITER_ROOT/mutants and is read in place by every
iteration; it is not snapshotted or carried forward, because doing so re-walked and
re-hashed a 1.6M-file tree per iteration to prove an invariant nothing can violate. Generated T′ is iteration evidence only and never becomes the reference suite
for a later iteration.

Every snapshot is stored under iter_N+1/stages/<stage>/ with task-scoped manifests under manifests/<task>.json. Each manifest contains source paths and content hashes. Later in-place polishing
therefore cannot change the meaning of an earlier evaluation report.

Options:
  --task TASK              Task id (default: ${default_task})
  --model MODEL            Override the model for every agent route
  --reasoning EFFORT       Override reasoning effort for every agent route
  --step-model STEP=MODEL  Override one step's model; repeat as needed
  --step-reasoning STEP=EFFORT
                           Override one step's reasoning effort; repeat as needed
  --iter-root DIR          Iteration root (default: ${default_iter_root})
  --tests-dir DIR          Fixed reference test root (default: ${default_tests_dir})
  --ground-truth-dir DIR   Source-built executables (default: ${default_ground_truth_dir})
  --mutants-dir DIR        Shared sealed mutant store (default: ITER_ROOT/mutants)
  --skipped-tests PATH    Run-scoped skipped-test JSON file or directory
  --start-iter N           First current iteration to process (default: ${default_start_iter})
  --iterations N, -n N     Number of iterations to run (default: ${default_iterations})
  --workers N              Number of instances to evaluate in parallel (default: ${default_workers})
  --branch-workers N       Number of test branches to evaluate in parallel (default: ${default_branch_workers})
  --classify-limit N       Classify at most N failures; 0 means all (default: ${default_classify_limit})
  --classify-branch-workers N
                           Classify failure-attribution branches with this many parallel Codex instances (default: ${default_classify_branch_workers})
  --mutant-classify-batch-size N
                           Cases per generated-test/mutant attribution batch (default: ${default_mutant_classify_batch_size})
  --mutant-classify-batch-workers N
                           Parallel generated-test/mutant attribution workers (default: ${default_mutant_classify_batch_workers})
  --cpu-budget N           Per-task CPU budget for compile/evaluation stages (default: ${default_cpu_budget})
  --agent-cpus N           CPU limit for single-agent stages (default: ${default_agent_cpus})
  --classifier-cpus N      CPU limit per parallel classifier (default: ${default_classifier_cpus})
  --solve-timeout SECONDS  Codex solve timeout (default: ${default_solve_timeout})
  --solve-attempts N       Try candidate implementation at most N times when solving or
                           fresh offline build verification fails
                           (default: ${default_solve_attempts})
  --test-timeout SECONDS   Codex generated-test timeout (default: ${default_test_timeout})
  --min-generated-tests N  Retry generation below this JUnit testcase target
                           (default: ${default_min_generated_tests})
  --reference-trials N     Run generated tests against the ground-truth executable N times; inconsistent pass/fail tests are flaky (default: ${default_reference_trials})
  --generate-test-attempts N
                           Try test generation at most N times to meet the minimum
                           (default: ${default_generate_test_attempts})
  --suite-regenerations N  Regenerate a generated suite whose tests mostly crash in their own code at most N times (default: ${default_suite_regenerations})
  --polish-timeout SECONDS Codex polish timeout (default: ${default_polish_timeout})
  --junit-completeness-check
                           Validate JUnit testcase names against tests.json during candidate eval
                           (default: ${default_junit_completeness_check})
  --skip-junit-completeness-check
                           Do not validate JUnit testcase names against tests.json during candidate eval.
                           Useful when fixed tests have collection names not represented in tests.json.
  --cleanroom-base-image IMAGE
                           Prebuilt Codex-enabled task image for solve_codex.sh
  --classify-dry-run       Write attribution prompts without calling Codex
  --polish-dry-run         Copy inputs and write polish prompt without calling Codex
  --dry-run                Enable both --classify-dry-run and --polish-dry-run
  --skip-solve             Do not run the solve phase
  --skip-eval              Do not run the eval phase
  --skip-classify          Do not run the failure attribution phase
  --skip-mutant-loop       Do not run generated-test evaluation or mutant improvement
  --skip-generate-tests    Do not generate the mutation-loop test suite
  --skip-mutant-eval       Do not evaluate the generated suite against mutants
  --skip-mutant-classify   Do not run the generated-test failure and mutant attribution phase
  --skip-validity-classify
                           Classify only survived mutants, not generated-test failures
  --skip-mutation-score            Do not evaluate or classify mutants; the generated suite still runs
                           against ground truth, which validity rate needs and mutation score filters on
  --skip-polish            Do not run the polish phase
  --force                  Re-run/overwrite outputs where supported
  -h, --help               Show this help message
EOF
}

require_value() {
    if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        usage >&2
        exit 1
    fi
}

require_non_negative_int() {
    local name=$1
    local value=$2
    if [[ ! "${value}" =~ ^[0-9]+$ ]]; then
        echo "${name} must be a non-negative integer: ${value}" >&2
        exit 1
    fi
}

require_positive_int() {
    local name=$1
    local value=$2
    require_non_negative_int "${name}" "${value}"
    if [ "${value}" -eq 0 ]; then
        echo "${name} must be greater than zero" >&2
        exit 1
    fi
}

phase() {
    printf '\n==> %s\n' "$*"
}

run_cmd() {
    printf '+'
    printf ' %q' "$@"
    printf '\n'
    "$@"
}

run_cmd_to_file() {
    local output=$1
    shift
    mkdir -p "$(dirname "${output}")"
    printf "+"
    printf " %q" "$@"
    printf " > %q 2>&1\n" "${output}"
    local status=0
    "$@" >"${output}" 2>&1 || status=$?
    if [ "${status}" -ne 0 ]; then
        echo "Command failed with exit code ${status}; captured output: ${output}" >&2
    fi
    return "${status}"
}

iteration_checkpoint_has_phase() {
    local checkpoint_file=$1
    local wanted_phase=$2
    local recorded_phase
    local recorded_status

    [ -f "${checkpoint_file}" ] || return 1
    while IFS=$'\t' read -r recorded_phase recorded_status _; do
        if [ "${recorded_phase}" = "${wanted_phase}" ] && [ "${recorded_status}" = completed ]; then
            return 0
        fi
    done <"${checkpoint_file}"
    return 1
}

record_iteration_checkpoint() {
    local checkpoint_file=$1
    local checkpoint_phase=$2

    if iteration_checkpoint_has_phase "${checkpoint_file}" "${checkpoint_phase}"; then
        return
    fi
    printf '%s\tcompleted\t%s\n' \
        "${checkpoint_phase}" "$(date --iso-8601=seconds)" >>"${checkpoint_file}"
}

run_checkpointed_cmd() {
    local checkpoint_file=$1
    local checkpoint_phase=$2
    shift 2

    if iteration_checkpoint_has_phase "${checkpoint_file}" "${checkpoint_phase}"; then
        phase "Skipping completed phase ${checkpoint_phase}"
        return
    fi
    run_cmd "$@"
    record_iteration_checkpoint "${checkpoint_file}" "${checkpoint_phase}"
}

run_checkpointed_cmd_to_file() {
    local checkpoint_file=$1
    local checkpoint_phase=$2
    local output=$3
    shift 3

    if iteration_checkpoint_has_phase "${checkpoint_file}" "${checkpoint_phase}"; then
        phase "Skipping completed phase ${checkpoint_phase}"
        return
    fi
    run_cmd_to_file "${output}" "$@"
    record_iteration_checkpoint "${checkpoint_file}" "${checkpoint_phase}"
}

snapshot_inputs() {
    local stage_dir=$1
    local snapshot_force=${force}
    shift
    if [ "${1:-}" = --force ]; then
        snapshot_force=true
        shift
    fi
    local snapshot_args=(
        uv run python -m programbench.iteration_inputs
        --stage-dir "${stage_dir}"
        --task "${task}"
    )
    while [ "$#" -gt 0 ]; do
        snapshot_args+=(--input "$1" "$2")
        shift 2
    done
    if [ "${snapshot_force}" = true ]; then
        snapshot_args+=(--force)
    fi
    run_cmd "${snapshot_args[@]}"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --model)
            require_value "$@"
            global_model_override="$2"
            shift 2
            ;;
        --reasoning)
            require_value "$@"
            global_reasoning_override="$2"
            shift 2
            ;;
        --step-model)
            require_value "$@"
            programbench_agent_route_override model "$2"
            shift 2
            ;;
        --step-reasoning)
            require_value "$@"
            programbench_agent_route_override reasoning "$2"
            shift 2
            ;;
        --task)
            require_value "$@"
            task="$2"
            shift 2
            ;;
        --iter-root)
            require_value "$@"
            iter_root="$2"
            shift 2
            ;;
        --mutants-dir)
            require_value "$@"
            mutants_dir="$2"
            shift 2
            ;;
        --tests-dir)
            require_value "$@"
            tests_dir="$2"
            shift 2
            ;;
        --ground-truth-dir)
            require_value "$@"
            ground_truth_dir="$2"
            shift 2
            ;;
        --skipped-tests)
            require_value "$@"
            skipped_tests="$2"
            shift 2
            ;;
        --start-iter)
            require_value "$@"
            start_iter="$2"
            shift 2
            ;;
        --iterations|-n)
            require_value "$@"
            iterations="$2"
            shift 2
            ;;
        --workers)
            require_value "$@"
            workers="$2"
            shift 2
            ;;
        --branch-workers)
            require_value "$@"
            branch_workers="$2"
            shift 2
            ;;
        --classify-limit)
            require_value "$@"
            classify_limit="$2"
            shift 2
            ;;
        --classify-branch-workers)
            require_value "$@"
            classify_branch_workers="$2"
            shift 2
            ;;
        --mutant-classify-batch-size)
            require_value "$@"
            mutant_classify_batch_size="$2"
            shift 2
            ;;
        --mutant-classify-batch-workers)
            require_value "$@"
            mutant_classify_batch_workers="$2"
            shift 2
            ;;
        --cpu-budget)
            require_value "$@"
            cpu_budget="$2"
            shift 2
            ;;
        --agent-cpus)
            require_value "$@"
            agent_cpus="$2"
            shift 2
            ;;
        --classifier-cpus)
            require_value "$@"
            classifier_cpus="$2"
            shift 2
            ;;
        --solve-timeout)
            require_value "$@"
            solve_timeout="$2"
            shift 2
            ;;
        --solve-attempts)
            require_value "$@"
            solve_attempts="$2"
            shift 2
            ;;
        --test-timeout)
            require_value "$@"
            test_timeout="$2"
            shift 2
            ;;
        --min-generated-tests)
            require_value "$@"
            min_generated_tests="$2"
            shift 2
            ;;
        --reference-trials)
            require_value "$@"
            reference_trials="$2"
            shift 2
            ;;
        --suite-regenerations)
            require_value "$@"
            suite_regenerations_max="$2"
            shift 2
            ;;
        --generate-test-attempts)
            require_value "$@"
            generate_test_attempts="$2"
            shift 2
            ;;
        --polish-timeout)
            require_value "$@"
            polish_timeout="$2"
            shift 2
            ;;
        --cleanroom-base-image)
            require_value "$@"
            cleanroom_base_image="$2"
            shift 2
            ;;
        --junit-completeness-check)
            junit_completeness_check=true
            shift
            ;;
        --skip-junit-completeness-check)
            junit_completeness_check=false
            shift
            ;;
        --classify-dry-run)
            classify_dry_run=true
            shift
            ;;
        --polish-dry-run)
            polish_dry_run=true
            shift
            ;;
        --dry-run)
            classify_dry_run=true
            polish_dry_run=true
            shift
            ;;
        --skip-solve)
            skip_solve=true
            shift
            ;;
        --skip-eval)
            skip_eval=true
            shift
            ;;
        --skip-classify)
            skip_classify=true
            shift
            ;;
        --skip-mutant-loop)
            skip_mutant_loop=true
            shift
            ;;
        --skip-generate-tests)
            skip_generate_tests=true
            shift
            ;;
        --skip-mutant-eval)
            skip_mutant_eval=true
            shift
            ;;
        --skip-mutant-classify)
            skip_mutant_classify=true
            shift
            ;;
        --skip-validity-classify)
            skip_validity_classify=true
            shift
            ;;
        --skip-mutation-score)
            skip_mutation_score=true
            shift
            ;;
        --skip-polish)
            skip_polish=true
            shift
            ;;
        --force)
            force=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

require_non_negative_int "--start-iter" "${start_iter}"
require_positive_int "--iterations" "${iterations}"
require_positive_int "--workers" "${workers}"
require_positive_int "--branch-workers" "${branch_workers}"
require_non_negative_int "--classify-limit" "${classify_limit}"
require_positive_int "--classify-branch-workers" "${classify_branch_workers}"
require_non_negative_int "--mutant-classify-batch-size" "${mutant_classify_batch_size}"
require_positive_int "--mutant-classify-batch-workers" "${mutant_classify_batch_workers}"
require_positive_int "--cpu-budget" "${cpu_budget}"
require_positive_int "--agent-cpus" "${agent_cpus}"
require_positive_int "--classifier-cpus" "${classifier_cpus}"
require_positive_int "--solve-timeout" "${solve_timeout}"
require_positive_int "--solve-attempts" "${solve_attempts}"
require_positive_int "--test-timeout" "${test_timeout}"
require_positive_int "--min-generated-tests" "${min_generated_tests}"
require_positive_int "--reference-trials" "${reference_trials}"
require_positive_int "--generate-test-attempts" "${generate_test_attempts}"
require_non_negative_int "--suite-regenerations" "${suite_regenerations_max}"
require_positive_int "--polish-timeout" "${polish_timeout}"
programbench_agent_routes_resolve "${global_model_override}" "${global_reasoning_override}"

iter_root=${iter_root%/}
mutants_dir=${mutants_dir:-${iter_root}/mutants}
mutants_dir=${mutants_dir%/}

iterate_agent_routes_file="${iter_root}/agent-routes/${task}.tsv"
mkdir -p "${iter_root}/agent-routes"
printf 'step\tmodel\treasoning\tretry_model\tretry_reasoning\n' >"${iterate_agent_routes_file}"
programbench_agent_routes_print >>"${iterate_agent_routes_file}"
printf 'Iteration agent routes: %s\n' "${iterate_agent_routes_file}"

for ((offset = 0; offset < iterations; offset++)); do
    iter=$((start_iter + offset))
    next_iter_num=$((iter + 1))
    this_iter="${iter_root}/iter_${iter}"
    next_iter="${iter_root}/iter_${next_iter_num}"
    source_spec="${this_iter}/spec"
    candidate_executable="${next_iter}/executable"
    polished_spec="${next_iter}/spec"
    generated_test_out="${next_iter}/generated-test"

    candidate_stage="${next_iter}/stages/candidate-evaluation"
    candidate_spec="${candidate_stage}/spec"
    generated_test_stage="${next_iter}/stages/generated-test-generation"
    generated_test_spec_snapshot="${generated_test_stage}/spec"
    mutant_eval_stage="${next_iter}/stages/generated-test-mutant-evaluation"
    mutant_eval_test_snapshot="${mutant_eval_stage}/generated-test"
    iteration_checkpoint="${next_iter}/stages/${task}/pipeline-checkpoints.tsv"
    mutant_eval_root="${next_iter}/mutant-eval"
    mutant_eval_source="${mutant_eval_root}/generated-test"

    mkdir -p "$(dirname "${iteration_checkpoint}")"
    if [ "${force}" = true ]; then
        : >"${iteration_checkpoint}"
    fi

    phase "Iteration ${iter} -> ${next_iter_num}"

    if [ ! -d "${source_spec}/${task}" ]; then
        echo "Spec input is missing: ${source_spec}/${task}" >&2
        exit 1
    fi
    if [ ! -d "${tests_dir}/${task}" ]; then
        echo "Fixed reference test input is missing: ${tests_dir}/${task}" >&2
        exit 1
    fi
    if [ "${skip_mutant_loop}" = false ] && [ ! -f "${mutants_dir}/${task}/mutants.json" ]; then
        echo "Mutant input is missing: ${mutants_dir}/${task}/mutants.json" >&2
        echo "Run scripts/construction/run_init.sh to build ITER_ROOT/mutants, or use --skip-mutant-loop." >&2
        exit 1
    fi

    if [ "${skip_solve}" = false ] || [ "${skip_eval}" = false ] || [ "${skip_classify}" = false ]; then
        phase "Snapshotting candidate inputs from iter_${iter}"
        snapshot_inputs "${candidate_stage}" spec "${source_spec}"
    fi

    if [ "${skip_solve}" = false ]; then
        solve_args=(
            bash scripts/agents/solve_codex.sh
            --model "${PROGRAMBENCH_ROUTE_MODEL[solve_codex]}"
            --reasoning "${PROGRAMBENCH_ROUTE_REASONING[solve_codex]}"
            --task "${task}"
            --mode spec-only
            --cleanroom "${candidate_spec}"
            --output "${candidate_executable}"
            --timeout "${solve_timeout}"
            --docker-cpus "${cpu_budget}"
        )
        if [ -n "${cleanroom_base_image}" ]; then
            solve_args+=(--cleanroom-base-image "${cleanroom_base_image}")
        fi
        phase "Solving from immutable input ${candidate_spec}"
        if iteration_checkpoint_has_phase "${iteration_checkpoint}" candidate-solve; then
            phase "Skipping completed phase candidate-solve"
        else
            solve_succeeded=false
            for ((solve_attempt = 1; solve_attempt <= solve_attempts; solve_attempt++)); do
                phase "Candidate-solve attempt ${solve_attempt}/${solve_attempts}"
                if run_cmd "${solve_args[@]}"; then
                    solve_succeeded=true
                    break
                fi

                failed_solve_dir="${candidate_executable}/${task}"
                if [ -f "${failed_solve_dir}/traj.json" ]; then
                    cp "${failed_solve_dir}/traj.json" \
                        "${failed_solve_dir}/traj.attempt_${solve_attempt}.json"
                fi
                if [ -f "${failed_solve_dir}/submission.tar.gz" ]; then
                    cp "${failed_solve_dir}/submission.tar.gz" \
                        "${failed_solve_dir}/submission.attempt_${solve_attempt}.tar.gz"
                fi
                if [ "${solve_attempt}" -lt "${solve_attempts}" ]; then
                    echo "Candidate solve or fresh build verification failed; returning to implementation." >&2
                fi
            done
            if [ "${solve_succeeded}" = false ]; then
                echo "Candidate solve failed after ${solve_attempts} attempts." >&2
                exit 1
            fi
            record_iteration_checkpoint "${iteration_checkpoint}" candidate-solve
        fi
    else
        phase "Skipping solve"
    fi

    if [ "${skip_eval}" = false ]; then
        if [ ! -d "${candidate_executable}/${task}" ]; then
            echo "Executable output is missing: ${candidate_executable}/${task}" >&2
            echo "Run without --skip-solve or provide the expected executable output first." >&2
            exit 1
        fi
        eval_args=(
            uv run programbench eval "${candidate_executable}"
            --tests-dir "${tests_dir}"
            --skipped-tests "${skipped_tests}"
            --filter "${task}"
            --workers "${workers}"
            --branch-workers "${branch_workers}"
            --cpu-budget "${cpu_budget}"
        )
        if [ -n "${cleanroom_base_image}" ]; then
            evaluation_image="${cleanroom_base_image}"
        else
            evaluation_image="$(scripts/docker/install_codex_cleanroom.sh --task "${task}" --print-image)"
        fi
        eval_args+=(--image "${evaluation_image}")
        if [ "${junit_completeness_check}" = true ]; then
            eval_args+=(--junit-completeness-check)
        else
            eval_args+=(--skip-junit-completeness-check)
        fi
        if [ "${force}" = true ]; then
            eval_args+=(--force)
        fi
        phase "Evaluating ${candidate_executable} against fixed reference tests ${tests_dir}"
        candidate_eval_json="${candidate_executable}/${task}/${task}.eval.json"
        if iteration_checkpoint_has_phase "${iteration_checkpoint}" candidate-eval \
            && [ -f "${candidate_eval_json}" ]; then
            phase "Skipping completed phase candidate-eval"
        else
            if iteration_checkpoint_has_phase "${iteration_checkpoint}" candidate-eval; then
                echo "Candidate-eval checkpoint is stale; expected result is missing: ${candidate_eval_json}" >&2
            fi
            run_cmd "${eval_args[@]}"
            if [ ! -f "${candidate_eval_json}" ]; then
                echo "Candidate evaluation did not produce: ${candidate_eval_json}" >&2
                exit 1
            fi
            record_iteration_checkpoint "${iteration_checkpoint}" candidate-eval
        fi
    else
        phase "Skipping eval"
    fi

    if [ "${skip_classify}" = false ]; then
        classify_args=(
            env
            PROGRAMBENCH_DOCKER_CPUS="${classifier_cpus}"
            bash scripts/eval/classify_failures.sh
            --task "${task}"
            --model "${PROGRAMBENCH_ROUTE_MODEL[classify_failures]}"
            --reasoning "${PROGRAMBENCH_ROUTE_REASONING[classify_failures]}"
            --iter-dir "${next_iter}"
            --spec-dir "${candidate_spec}"
            --test-spec-links "${this_iter}/test-spec-links/${task}/test_spec_links.json"
            --reference-tests-dir "${tests_dir}"
            --limit "${classify_limit}"
            --branch-workers "${classify_branch_workers}"
        )
        if [ "${classify_dry_run}" = true ]; then
            classify_args+=(--dry-run)
        fi
        if [ "${force}" = true ]; then
            classify_args+=(--force)
        fi
        phase "Classifying failures for ${next_iter}"
        run_checkpointed_cmd "${iteration_checkpoint}" candidate-classify "${classify_args[@]}"
    else
        phase "Skipping failure classification"
    fi

    if [ "${skip_mutant_loop}" = false ]; then
        # Generated T is authored from the same spec snapshot the candidate saw, so both
        # evaluation directions judge one specification and a single polish consumes both.
        suite_regenerations=0
        mutant_eval_snapshot_force=
        while :; do
        if [ "${skip_generate_tests}" = false ]; then
            generate_test_args=(
                uv run programbench generate-tests
                --model "${PROGRAMBENCH_ROUTE_MODEL[generate_tests]}"
                --reasoning-effort "${PROGRAMBENCH_ROUTE_REASONING[generate_tests]}"
                --filter "${task}"
                --cleanroom-dir "${generated_test_spec_snapshot}"
                --redo-existing
                --spec-only
                --no-goal
                --output "${generated_test_out}"
                --workers "${workers}"
                --timeout "${test_timeout}"
                --docker-cpus "${agent_cpus}"
            )
            if [ -n "${cleanroom_base_image}" ]; then
                generated_test_image="${cleanroom_base_image}"
            else
                generated_test_image="$(scripts/docker/install_codex_cleanroom.sh --task "${task}" --print-image)"
                scripts/docker/install_codex_cleanroom.sh --task "${task}"
            fi
            generate_test_args+=(--cleanroom-base-image "${generated_test_image}")
            phase "Generating tests from immutable input ${generated_test_spec_snapshot}"
            generate_test_log="${generated_test_out}/${task}/generate_tests.log"
            generated_test_archive="${generated_test_out}/${task}/tests.tar.gz"
            generated_test_count=0

            if iteration_checkpoint_has_phase "${iteration_checkpoint}" generated-test-generation \
                && generated_test_count=$(python3 scripts/construction/count_generated_tests.py "${generated_test_archive}") \
                && [ "${generated_test_count}" -ge "${min_generated_tests}" ]; then
                phase "Skipping completed phase generated-test-generation (${generated_test_count} tests)"
            else
                phase "Snapshotting generated-test specification input"
                snapshot_inputs "${generated_test_stage}" --force spec "${source_spec}"
                best_generated_test_archive="${generated_test_out}/${task}/tests.best.tar.gz"
                best_generated_test_count=-1
                rm -f "${best_generated_test_archive}"
                for ((generation_attempt = 1; generation_attempt <= generate_test_attempts; generation_attempt++)); do
                    attempt_log="${generate_test_log}"
                    if [ "${generation_attempt}" -gt 1 ]; then
                        attempt_log="${generated_test_out}/${task}/generate_tests.attempt_${generation_attempt}.log"
                    fi
                    phase "Generated-test attempt ${generation_attempt}/${generate_test_attempts}"
                    rm -f "${generated_test_archive}"
                    generation_command_ok=false
                    if run_cmd_to_file "${attempt_log}" "${generate_test_args[@]}"; then
                        generation_command_ok=true
                    else
                        echo "Generated-test command failed; returning to generate-tests." >&2
                    fi
                    if [ "${generation_command_ok}" = true ] \
                        && generated_test_count=$(python3 scripts/construction/count_generated_tests.py "${generated_test_archive}"); then
                        printf 'Generated suite contains %s JUnit testcases (minimum: %s).\n' \
                            "${generated_test_count}" "${min_generated_tests}"
                        if [ "${generated_test_count}" -gt "${best_generated_test_count}" ]; then
                            cp "${generated_test_archive}" "${best_generated_test_archive}"
                            best_generated_test_count=${generated_test_count}
                        fi
                    else
                        generated_test_count=0
                    fi
                    if [ "${generated_test_count}" -ge "${min_generated_tests}" ]; then
                        break
                    fi
                    if [ "${generation_command_ok}" = true ]; then
                        echo "Generated suite is too small; returning to generate-tests." >&2
                    fi
                done
                if [ "${best_generated_test_count}" -lt 0 ]; then
                    echo "No generated-test attempt produced readable JUnit results." >&2
                    exit 1
                fi
                mv "${best_generated_test_archive}" "${generated_test_archive}"
                generated_test_count=${best_generated_test_count}
                record_iteration_checkpoint "${iteration_checkpoint}" generated-test-generation
            fi
        else
            phase "Skipping generated-test phase"
        fi

        if [ "${skip_mutant_eval}" = false ]; then
            generated_test_archive="${generated_test_out}/${task}/tests.tar.gz"
            if [ ! -f "${generated_test_archive}" ]; then
                echo "Generated test suite is missing: ${generated_test_archive}" >&2
                echo "Run without --skip-generate-tests or provide the expected generated suite first." >&2
                exit 1
            fi
            if ! generated_test_count=$(python3 scripts/construction/count_generated_tests.py "${generated_test_archive}"); then
                echo "Generated test suite does not contain readable JUnit results: ${generated_test_archive}" >&2
                echo "Run without --skip-generate-tests to regenerate it." >&2
                exit 1
            fi
            if [ "${generated_test_count}" -lt "${min_generated_tests}" ]; then
                echo "Generated suite has only ${generated_test_count} tests; continuing to eval-tests." >&2
            fi
            phase "Snapshotting generated-test mutation-evaluation inputs"
            snapshot_inputs "${mutant_eval_stage}" ${mutant_eval_snapshot_force:+--force} \
                generated-test "${generated_test_out}"
            mutant_eval_args=(
                uv run programbench eval-tests "${mutant_eval_test_snapshot}"
                --output "${mutant_eval_root}"
                --ground-truth-dir "${ground_truth_dir}"
                --reference-tests-dir "${tests_dir}"
                --reference-trials "${reference_trials}"
                --filter "${task}"
                --detailed-logs
                --workers "${workers}"
                --branch-workers "${branch_workers}"
                --cpu-budget "${cpu_budget}"
            )
            if [ "${skip_mutation_score}" = false ]; then
                mutant_eval_args+=(--mutants-dir "${mutants_dir}")
            fi
            if [ "${force}" = true ]; then
                mutant_eval_args+=(--force)
            fi
            phase "Evaluating immutable generated tests against immutable mutants"
            run_checkpointed_cmd \
                "${iteration_checkpoint}" generated-test-mutant-eval \
                "${mutant_eval_args[@]}"
        else
            phase "Skipping mutant eval"
        fi

        if [ "${skip_generate_tests}" = true ] || [ "${skip_mutant_eval}" = true ]; then
            break
        fi
        # A suite whose tests crash in their own code (a broken fake tool, a missing fixture)
        # says nothing about the spec; a low pass rate from spec-driven assertions is kept.
        quality_report="${next_iter}/log/${task}/generated_suite_quality.json"
        mkdir -p "$(dirname "${quality_report}")"
        quality_status=0
        uv run python -m programbench.generated_suite_quality \
            "${mutant_eval_source}/${task}/${task}.test_eval.json" --output "${quality_report}" || quality_status=$?
        if [ "${quality_status}" -eq 0 ]; then
            break
        fi
        # INFRASTRUCTURE_EXIT_CODE: the evaluation never ran, so there is no suite to judge
        # and a regeneration would spend a full generation only to fail the same way.
        if [ "${quality_status}" -eq 4 ]; then
            echo "Generated-suite evaluation never ran; see infrastructure_failure in ${quality_report}" >&2
            exit 1
        fi
        if [ "${quality_status}" -ne 3 ]; then
            echo "Generated-suite quality check failed (status ${quality_status}); see ${quality_report}" >&2
            exit 1
        fi
        if [ "${suite_regenerations}" -ge "${suite_regenerations_max}" ]; then
            echo "Generated suite still crashes in its own code after ${suite_regenerations} regeneration(s); continuing with it." >&2
            break
        fi
        suite_regenerations=$((suite_regenerations + 1))
        echo "Generated suite crashes in its own code; regenerating (${suite_regenerations}/${suite_regenerations_max})." >&2
        mv "${generated_test_out}/${task}/tests.tar.gz" "${generated_test_out}/${task}/tests.rejected_${suite_regenerations}.tar.gz"
        rm -rf "${mutant_eval_source}/${task}"
        mutant_eval_snapshot_force=1
        sed -i '/^generated-test-generation\t/d;/^generated-test-mutant-eval\t/d' "${iteration_checkpoint}"
        done

        if [ "${skip_mutant_classify}" = false ]; then
            mutant_eval_json="${mutant_eval_source}/${task}/${task}.test_eval.json"
            if [ ! -f "${mutant_eval_json}" ]; then
                echo "Mutation eval JSON is missing: ${mutant_eval_json}" >&2
                echo "Run without --skip-mutant-eval or provide the expected mutation eval first." >&2
                exit 1
            fi
            mutant_classify_args=(
                env
                PROGRAMBENCH_DOCKER_CPUS="${classifier_cpus}"
                bash scripts/eval/classify_mutants.sh "${mutant_eval_json}"
                --task "${task}"
                --model "${PROGRAMBENCH_ROUTE_MODEL[classify_mutants]}"
                --reasoning "${PROGRAMBENCH_ROUTE_REASONING[classify_mutants]}"
                --spec-dir "${generated_test_spec_snapshot}"
                --tests-dir "${mutant_eval_test_snapshot}"
                --mutants-dir "${mutants_dir}"
                --output "${next_iter}/log/${task}/mutant_attribution.json"
                --limit "${classify_limit}"
                --batch-size "${mutant_classify_batch_size}"
                --batch-workers "${mutant_classify_batch_workers}"
            )
            if [ "${skip_validity_classify}" = true ]; then
                mutant_classify_args+=(--skip-test-failures)
            fi
            if [ "${skip_mutation_score}" = true ]; then
                mutant_classify_args+=(--skip-survived-mutants)
            fi
            if [ "${classify_dry_run}" = true ]; then
                mutant_classify_args+=(--dry-run)
            fi
            if [ "${force}" = true ]; then
                mutant_classify_args+=(--force)
            fi
            phase "Classifying generated-test failures and survived/error mutants for ${next_iter}"
            run_checkpointed_cmd \
                "${iteration_checkpoint}" generated-test-mutant-classify \
                "${mutant_classify_args[@]}"
        else
            phase "Skipping mutant classification"
        fi

    else
        phase "Skipping mutant improvement loop"
    fi

    if [ "${skip_polish}" = false ]; then
        attribution="${next_iter}/log/${task}/failure_attribution.json"
        mutant_attribution="${next_iter}/log/${task}/mutant_attribution.json"
        if [ ! -f "${attribution}" ] && [ ! -f "${mutant_attribution}" ]; then
            echo "No attribution to polish from: ${attribution} or ${mutant_attribution}" >&2
            echo "Run without --skip-classify or --skip-mutant-loop, or create an attribution file first." >&2
            exit 1
        fi
        polish_args=(
            env
            PROGRAMBENCH_DOCKER_CPUS="${agent_cpus}"
            bash scripts/construction/polish_iteration.sh
            --task "${task}"
            --model "${PROGRAMBENCH_ROUTE_MODEL[polish_iteration]}"
            --reasoning "${PROGRAMBENCH_ROUTE_REASONING[polish_iteration]}"
            --iter-root "${iter_root}"
            --iter "${iter}"
            --timeout "${polish_timeout}"
            --tests-dir "${tests_dir}"
            --skipped-tests "${skipped_tests}"
            --link-branch-workers "${classify_branch_workers}"
        )
        if [ "${polish_dry_run}" = true ]; then
            polish_args+=(--dry-run)
        fi
        if [ "${force}" = true ] \
            || { ! iteration_checkpoint_has_phase "${iteration_checkpoint}" spec-polish \
                && [ -d "${polished_spec}/${task}" ]; }; then
            polish_args+=(--force)
        fi
        phase "Polishing the specification and carrying its initial test links into ${next_iter} from reference-test, generated-test and mutant evidence"
        run_checkpointed_cmd "${iteration_checkpoint}" spec-polish "${polish_args[@]}"
    else
        phase "Skipping polish"
    fi

done
