#!/usr/bin/env bash
set -euo pipefail

iter_root=output/construction
prepared_tests_root=output/prepared-tests
jobs=10
task_cpu_budget=32
agent_cpus=6
classifier_cpus=2
mutant_build_cpus=
mutant_build_jobs=8
mutant_eval_workers=
link_branch_workers=
max_repair_attempts=3
min_num_spec_sec=10
max_num_spec_sec=100
target_tests_per_spec=6
final_mutants_per_spec=2
global_model_override=
global_reasoning_override=
iterations=2
reference_trials=3
dynamic=false
converge_threshold=5
converge_min_metric=20
converge_max_error=80
iterate_options=()
include_existing=false
prune_failing_tests=false
force_prepare_tests=false
list_only=false
run_id=
selected_tasks=()

. scripts/construction/agent_routes.sh
programbench_agent_routes_reset
programbench_agent_route_register improve_spec gpt-5.6-sol high
programbench_agent_route_register link_reference_tests gpt-5.6-sol high
programbench_agent_route_register generate_mutants gpt-5.6-sol high
programbench_agent_route_register ensure_mutants_killed gpt-5.6-sol high gpt-5.6-sol high
programbench_agent_route_register solve_codex gpt-5.6-sol high
programbench_agent_route_register classify_failures gpt-5.6-sol high
programbench_agent_route_register polish_iteration gpt-5.6-sol high
programbench_agent_route_register generate_tests gpt-5.6-sol high
programbench_agent_route_register classify_mutants gpt-5.6-sol high
programbench_agent_route_register polish_generated_test_spec gpt-5.6-sol high

usage() {
    cat <<EOF
Usage: $0 [--task TASK]... [--iter-root DIR] [--run-id ID] [--prepared-tests-root DIR] [--jobs N] [--cpu-budget N] [--mutant-build-jobs N] [--mutant-eval-workers N] [--link-branch-workers N] [--max-repair-attempts N] [--model-name MODEL] [--reasoning-effort EFFORT] [--iterations N] [--dynamic] [--converge-threshold PCT] [--converge-min-metric PCT] [--converge-max-error PCT] [--reference-trials N] [--iterate-option OPT]... [--include-existing] [--prune-failing-tests] [--force-prepare-tests] [--list-only]

Run the complete iterative pipeline for every task in ground_truth/valid_task.txt,
or only the task instances selected with repeatable --task options. Missing
reference tests, ground truth, and cleanrooms are fetched per task by
scripts/dataset/fetch_task_inputs.py.
Before iter_0 initialization, prepare reusable skipped-test data outside
ITER_ROOT, then run initialization, specification iteration, and postprocessing.

Mutants are generated once into ITER_ROOT/mutants and sealed there: each repo_N
tree is replaced by its diff against the ground-truth implementation, and every
iteration reads that one store in place instead of carrying a copy forward.

Options:
  --min-num-spec-sec N  Minimum specification sections (default: 10)
  --max-num-spec-sec N  Maximum specification sections (default: 100)
  --task TASK           Run only this task instance; repeat to select multiple tasks
  --iter-root DIR       Shared iteration root (default: ${iter_root})
  --run-id ID           Invocation metadata directory name (default: timestamp and PID)
  --prepared-tests-root DIR
                        Reusable test-preparation root (default: ${prepared_tests_root})
  --jobs N              Maximum concurrent task pipelines (default: ${jobs})
  --cpu-budget N        Per-task CPU budget for compile and evaluation stages (default: ${task_cpu_budget})
  --mutant-build-cpus N Override the total mutant-build container CPU budget (default: --cpu-budget)
  --mutant-build-jobs N Mutant repositories compiled concurrently per task (default: ${mutant_build_jobs})
  --mutant-eval-workers N Concurrent initial mutant evaluations per task (default: half --cpu-budget, rounded down, minimum 1)
  --link-branch-workers N Reference-test branches linked concurrently per task (default: --cpu-budget divided by --agent-cpus, minimum 1)
  --max-repair-attempts N Maximum mutant repair requests per task (default: ${max_repair_attempts}; 0 disables repairs)
  --target-tests-per-spec N Different target tests per spec (default: ${target_tests_per_spec})
  --final-mutants-per-spec N Selected mutants retained per spec (default: ${final_mutants_per_spec})
  --model-name MODEL    Override the model for every agent route
  --reasoning-effort EFFORT
                        Override reasoning effort for every agent route
  --step-model STEP=MODEL
                        Override one step's model; repeat as needed
  --step-reasoning STEP=EFFORT
                        Override one step's reasoning effort; repeat as needed
  --retry-step-model STEP=MODEL
                        Override a retry-loop model from repair attempt 2
  --retry-step-reasoning STEP=EFFORT
                        Override retry-loop reasoning from repair attempt 2
  --iterations N        Target total iterations from iter_0 (default: ${iterations})
  --dynamic             Run one iteration at a time. Once a direction's spec-fault rate
                        (spec_underspecification + spec_contradiction over its total)
                        fell below --converge-threshold, that direction is never rerun:
                        acc gates solve/eval/classify, validity rate and mutation score together
                        gate the generated-test loop. A task stops when all three
                        converged or --iterations is reached; polish runs from
                        whichever evidence the iteration produced.
  --converge-threshold PCT
                        Spec-fault percentage below which a direction converged (default: ${converge_threshold})
  --converge-min-metric PCT
                        Accuracy or validity rate a direction must exceed before it can converge, so a
                        candidate that passes nothing does not count; mutation score is not guarded (default: ${converge_min_metric})
  --converge-max-error PCT
                        Stop a task once more than PCT of an iteration's classified failures in any
                        direction were errors (test never reached the executable, broken fixture,
                        sandbox); such failures carry no spec evidence (default: ${converge_max_error}; 100 never stops)
  --reference-trials N  Ground-truth trials per generated-suite evaluation; inconsistent tests are flaky (default: ${reference_trials})
  --iterate-option OPT  Forward OPT verbatim to scripts/construction/iterate_spec.sh; repeat as
                        needed (e.g. --iterate-option --skip-solve)
  --include-existing    Restart tasks that already have a directory below ITER_ROOT
  --prune-failing-tests Let mutant validation add reference-failing tests to the skip list
                        (default: off; the reference suite is fixed and failures are tolerated)
  --force-prepare-tests Rebuild reusable skipped-test preparation output
  --list-only           Prepare task lists and print the counts without running tasks
  -h, --help            Show this help

The outer task pool is the concurrency boundary. Internal iteration worker
counts are set to one so --jobs 10 does not multiply into 10 x 16 model calls.
Per-task logs, status files, checkpoints, and initialization trajectories are
shared below ITER_ROOT/batch. Invocation-specific task lists, routes, and token
summaries are written below ITER_ROOT/batch/runs/RUN_ID, allowing concurrent
runs for different task instances to safely share ITER_ROOT. Per-task logs use a zero-based attempt suffix
(TASK_0.log, TASK_1.log, ...) so reruns do not overwrite earlier output.

Failed or interrupted tasks resume automatically from the first stage without
a durable completion checkpoint. Successful tasks below --iterations continue
from their first incomplete iteration, so a run completed with --iterations 2
can later be extended with --iterations 5. Use --include-existing to discard
checkpoints and restart selected existing tasks from initialization. Prepared
test output is still reused unless --force-prepare-tests is supplied.

Agent route steps:
  improve_spec, link_reference_tests, generate_mutants,
  ensure_mutants_killed, solve_codex, classify_failures, polish_iteration,
  generate_tests, classify_mutants, polish_generated_test_spec
EOF
}

require_value() {
    if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        usage >&2
        exit 1
    fi
}

require_positive_int() {
    local name=$1
    local value=$2
    if [[ ! "${value}" =~ ^[1-9][0-9]*$ ]]; then
        echo "${name} must be a positive integer: ${value}" >&2
        exit 1
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --task)
            require_value "$@"
            selected_tasks+=("$2")
            shift 2
            ;;
        --iter-root)
            require_value "$@"
            iter_root=$2
            shift 2
            ;;
        --run-id)
            require_value "$@"
            run_id=$2
            shift 2
            ;;
        --prepared-tests-root)
            require_value "$@"
            prepared_tests_root=$2
            shift 2
            ;;
        --jobs)
            require_value "$@"
            jobs=$2
            shift 2
            ;;
        --cpu-budget)
            require_value "$@"
            task_cpu_budget="$2"
            shift 2
            ;;
        --mutant-build-cpus)
            require_value "$@"
            mutant_build_cpus="$2"
            shift 2
            ;;
        --mutant-build-jobs)
            require_value "$@"
            mutant_build_jobs="$2"
            shift 2
            ;;
        --mutant-eval-workers)
            require_value "$@"
            mutant_eval_workers="$2"
            shift 2
            ;;
        --link-branch-workers)
            require_value "$@"
            link_branch_workers="$2"
            shift 2
            ;;
        --max-repair-attempts) require_value "$@"; max_repair_attempts=$2; shift 2 ;;
        --min-num-spec-sec) require_value "$@"; min_num_spec_sec=$2; shift 2 ;;
        --max-num-spec-sec) require_value "$@"; max_num_spec_sec=$2; shift 2 ;;
        --target-tests-per-spec)
            require_value "$@"
            target_tests_per_spec="$2"
            shift 2
            ;;
        --final-mutants-per-spec)
            require_value "$@"
            final_mutants_per_spec="$2"
            shift 2
            ;;
        --model-name)
            require_value "$@"
            global_model_override=$2
            shift 2
            ;;
        --reasoning-effort)
            require_value "$@"
            global_reasoning_override=$2
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
        --retry-step-model)
            require_value "$@"
            programbench_agent_route_override retry-model "$2"
            shift 2
            ;;
        --retry-step-reasoning)
            require_value "$@"
            programbench_agent_route_override retry-reasoning "$2"
            shift 2
            ;;
        --iterations)
            require_value "$@"
            iterations=$2
            shift 2
            ;;
        --reference-trials)
            require_value "$@"
            reference_trials=$2
            shift 2
            ;;
        --dynamic)
            dynamic=true
            shift
            ;;
        --converge-threshold)
            require_value "$@"
            converge_threshold=$2
            shift 2
            ;;
        --converge-min-metric)
            require_value "$@"
            converge_min_metric=$2
            shift 2
            ;;
        --converge-max-error)
            require_value "$@"
            converge_max_error=$2
            shift 2
            ;;
        --iterate-option)
            require_value "$@"
            iterate_options+=("$2")
            shift 2
            ;;
        --include-existing)
            include_existing=true
            shift
            ;;
        --prune-failing-tests)
            prune_failing_tests=true
            shift
            ;;
        --force-prepare-tests)
            force_prepare_tests=true
            shift
            ;;
        --list-only)
            list_only=true
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

if [[ ! "${max_repair_attempts}" =~ ^[0-9]+$ ]]; then
    echo "--max-repair-attempts must be a non-negative integer: ${max_repair_attempts}" >&2
    exit 1
fi

require_positive_int "--jobs" "${jobs}"
require_positive_int "--cpu-budget" "${task_cpu_budget}"
if [ -z "${mutant_eval_workers}" ]; then
    mutant_eval_workers=$((task_cpu_budget / 2))
    if [ "${mutant_eval_workers}" -lt 1 ]; then mutant_eval_workers=1; fi
fi
require_positive_int "--mutant-eval-workers" "${mutant_eval_workers}"
# One Codex container per branch, each capped at --agent-cpus, so the branch count
# is what keeps this stage inside the same per-task budget as evaluation and builds.
if [ -z "${link_branch_workers}" ]; then
    link_branch_workers=$((task_cpu_budget / agent_cpus))
    if [ "${link_branch_workers}" -lt 1 ]; then link_branch_workers=1; fi
fi
require_positive_int "--link-branch-workers" "${link_branch_workers}"
require_positive_int "--mutant-build-jobs" "${mutant_build_jobs}"
require_positive_int "--target-tests-per-spec" "${target_tests_per_spec}"
require_positive_int "--final-mutants-per-spec" "${final_mutants_per_spec}"
if [ "${final_mutants_per_spec}" -gt "${target_tests_per_spec}" ]; then
    echo "--final-mutants-per-spec must not exceed target-tests-per-spec" >&2
    exit 1
fi
if [[ ! "${min_num_spec_sec}" =~ ^[1-9][0-9]*$ ]] || [[ ! "${max_num_spec_sec}" =~ ^[1-9][0-9]*$ ]] || (( min_num_spec_sec > max_num_spec_sec )); then
    echo "Section limits must satisfy 1 <= min <= max" >&2
    exit 1
fi

if [[ ! "${iterations}" =~ ^[0-9]+$ ]]; then
    echo "--iterations must be a non-negative integer: ${iterations}" >&2
    exit 1
fi
require_positive_int "--reference-trials" "${reference_trials}"
for value in "${converge_threshold}" "${converge_min_metric}" "${converge_max_error}"; do
    if [[ ! "${value}" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo "--converge-threshold, --converge-min-metric and --converge-max-error must be non-negative numbers: ${value}" >&2
        exit 1
    fi
done
if [ -n "${mutant_build_cpus}" ]; then
    require_positive_int "--mutant-build-cpus" "${mutant_build_cpus}"
else
    mutant_build_cpus=${task_cpu_budget}
fi
programbench_agent_routes_resolve "${global_model_override}" "${global_reasoning_override}"

if [ -n "${run_id}" ] && [[ ! "${run_id}" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "--run-id may contain only letters, digits, dots, underscores, and hyphens: ${run_id}" >&2
    exit 1
fi

iteration_options=("${iterate_options[@]}")
init_options=()
if [ "${prune_failing_tests}" = true ]; then
    init_options+=(--prune-failing-tests)
fi
if [ "${include_existing}" = true ]; then
    iteration_options+=(--force)
    init_options+=(--force)
fi

iter_root=${iter_root%/}
prepared_tests_root=${prepared_tests_root%/}
batch_dir="${iter_root}/batch"
if [ -z "${run_id}" ]; then
    run_id="$(date -u +%Y%m%dT%H%M%S.%N)-$$"
fi
run_dir="${batch_dir}/runs/${run_id}"
log_dir="${batch_dir}/logs"
status_dir="${batch_dir}/status"
pid_dir="${batch_dir}/pids"
trajectory_dir="${batch_dir}/trajectories"
# Docker images are named per task, not per run, so this state is deliberately
# shared by every iteration root on the host rather than living under batch_dir.
docker_lease_root="${PROGRAMBENCH_DOCKER_STATE_DIR:-output/.docker-state}/leases"
ground_truth_root=ground_truth
skipped_tests_root="${ground_truth_root}/skipped-tests"
mutant_validation_work_root="${batch_dir}/mutant-validation"
checkpoint_dir="${batch_dir}/checkpoints"
agent_routes_file="${run_dir}/agent-routes.tsv"
all_tasks_file="${run_dir}/tasks.all.txt"
selected_tasks_file="${run_dir}/tasks.selected.txt"
unknown_tasks_file="${run_dir}/tasks.unknown.txt"
unrunnable_tasks_file="${run_dir}/tasks.unrunnable.txt"
runnable_tasks_file="${run_dir}/tasks.runnable.txt"
existing_tasks_file="${run_dir}/tasks.existing.txt"
resumable_tasks_file="${run_dir}/tasks.resumable.txt"
extendable_tasks_file="${run_dir}/tasks.extendable.txt"
continuing_tasks_file="${run_dir}/tasks.continuing.txt"
pending_tasks_file="${run_dir}/tasks.pending.txt"
started_tasks_file="${run_dir}/tasks.started.txt"

mkdir -p \
    "${batch_dir}/runs" \
    "${log_dir}" \
    "${status_dir}" \
    "${pid_dir}" \
    "${checkpoint_dir}" \
    "${trajectory_dir}/spec" \
    "${trajectory_dir}/mutant" \
    "${mutant_validation_work_root}"

if ! mkdir "${run_dir}"; then
    echo "Run metadata directory already exists; choose another --run-id: ${run_dir}" >&2
    exit 1
fi

printf 'Batch PID: %d (kill -TERM -%d to stop the whole run)\n' "$$" "$$"
printf '%s\n' "$$" >"${pid_dir}/batch.pid"

printf 'step\tmodel\treasoning\tretry_model\tretry_reasoning\n' >"${agent_routes_file}"
programbench_agent_routes_print >>"${agent_routes_file}"
: >"${started_tasks_file}"

completed_iterations_for_task() {
    local task=$1
    local completed=0
    local next_iteration=1
    local iteration_checkpoint

    while :; do
        iteration_checkpoint="${iter_root}/iter_${next_iteration}/stages/${task}/pipeline-checkpoints.tsv"
        if [ ! -f "${iteration_checkpoint}" ]; then
            break
        fi
        if ! grep -Eq "^(spec-polish|generated-test-spec-polish|generated-test-mutant-polish)[[:space:]]+completed([[:space:]]|$)" "${iteration_checkpoint}"; then
            break
        fi
        completed=${next_iteration}
        next_iteration=$((next_iteration + 1))
    done

    printf "%d\n" "${completed}"
}

task_convergence() {
    uv run python -m programbench.iteration_convergence \
        --iter-root "${iter_root}" --task "$1" --threshold "${converge_threshold}" --min-metric "${converge_min_metric}" \
        --max-error "${converge_max_error}" "${@:2}"
}

task_converged() {
    [ "${dynamic}" = true ] && [ "$(task_convergence "$1")" = "acc=1 validity_rate=1 mutation_score=1" ]
}

iteration_skip_options() {
    # Maps "acc=A validity_rate=P mutation_score=R" to the iterate_spec.sh phases converged directions no longer need.
    # Validity Rate and mutation score share the generated suite and its evaluation, so only their classifications
    # can be dropped one at a time; the whole loop goes only once both have converged.
    case " $1 " in *" acc=1 "*) printf '%s\n' --skip-solve --skip-eval --skip-classify ;; esac
    case " $1 " in
        *" validity_rate=1 mutation_score=1 "*) printf '%s\n' --skip-mutant-loop ;;
        *" validity_rate=1 "*) printf '%s\n' --skip-validity-classify ;;
        *" mutation_score=1 "*) printf '%s\n' --skip-mutation-score ;;
    esac
}

find src/programbench/data/tasks -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort >"${all_tasks_file}"

: >"${selected_tasks_file}"
: >"${unknown_tasks_file}"
# Without --task, run the benchmark's task list.
sed 's/#.*//; s/[[:space:]]//g; /^$/d' ground_truth/valid_task.txt | sort -u >"${run_dir}/tasks.default.txt"
candidate_tasks_file="${run_dir}/tasks.default.txt"
if [ "${#selected_tasks[@]}" -gt 0 ]; then
    printf '%s\n' "${selected_tasks[@]}" | sort -u >"${selected_tasks_file}"
    comm -23 "${selected_tasks_file}" "${all_tasks_file}" >"${unknown_tasks_file}"
    if [ -s "${unknown_tasks_file}" ]; then
        echo "Unknown task instance(s):" >&2
        sed 's/^/  /' "${unknown_tasks_file}" >&2
        exit 1
    fi
    candidate_tasks_file="${selected_tasks_file}"
fi

: >"${runnable_tasks_file}"
while IFS= read -r task; do
    if [ -f "src/programbench/data/tasks/${task}/tests.json" ]; then
        printf '%s\n' "${task}" >>"${runnable_tasks_file}"
    fi
done <"${candidate_tasks_file}"

comm -23 "${candidate_tasks_file}" "${runnable_tasks_file}" >"${unrunnable_tasks_file}"
if [ "${#selected_tasks[@]}" -gt 0 ] && [ -s "${unrunnable_tasks_file}" ]; then
    echo "Selected task instance(s) are not runnable:" >&2
    sed 's/^/  /' "${unrunnable_tasks_file}" >&2
    echo "Each selected task needs src/programbench/data/tasks/<task>/tests.json." >&2
    exit 1
fi

if [ -d "${iter_root}/iter_0/spec" ]; then
    find "${iter_root}/iter_0/spec" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -u >"${run_dir}/directory-names.txt"
    comm -12 "${runnable_tasks_file}" "${run_dir}/directory-names.txt" >"${existing_tasks_file}"
else
    : >"${existing_tasks_file}"
fi

: >"${resumable_tasks_file}"
while IFS= read -r task; do
    task_status="${status_dir}/${task}.status"
    if [ ! -f "${task_status}" ]; then
        continue
    fi
    IFS=$'\t' read -r state _ <"${task_status}" || true
    case "${state}" in
        failed:*|running)
            printf '%s\n' "${task}" >>"${resumable_tasks_file}"
            ;;
    esac
done <"${existing_tasks_file}"

: >"${extendable_tasks_file}"
while IFS= read -r task; do
    completed_iterations=$(completed_iterations_for_task "${task}")
    if [ "${completed_iterations}" -lt "${iterations}" ] && ! task_converged "${task}"; then
        printf "%s\n" "${task}" >>"${extendable_tasks_file}"
    fi
done <"${existing_tasks_file}"

sort -u "${resumable_tasks_file}" "${extendable_tasks_file}" >"${continuing_tasks_file}"

if [ "${include_existing}" = true ]; then
    cp "${runnable_tasks_file}" "${pending_tasks_file}"
else
    comm -23 "${runnable_tasks_file}" "${existing_tasks_file}" >"${pending_tasks_file}"
    while IFS= read -r task; do
        printf '%s\n' "${task}" >>"${pending_tasks_file}"
    done <"${continuing_tasks_file}"
    sort -u -o "${pending_tasks_file}" "${pending_tasks_file}"
fi

# The set operations above need sorted input for comm, which loses the caller's
# --task order. Restore it so the queue runs in the order the task file lists.
if [ "${#selected_tasks[@]}" -gt 0 ]; then
    awk 'NR==FNR { pending[$0]=1; next } $0 in pending && !seen[$0]++' \
        "${pending_tasks_file}" <(printf '%s\n' "${selected_tasks[@]}") \
        >"${pending_tasks_file}.ordered"
    mv "${pending_tasks_file}.ordered" "${pending_tasks_file}"
fi

all_count=$(wc -l <"${all_tasks_file}")
selected_count=$(wc -l <"${candidate_tasks_file}")
runnable_count=$(wc -l <"${runnable_tasks_file}")
existing_count=$(wc -l <"${existing_tasks_file}")
resumable_count=$(wc -l <"${resumable_tasks_file}")
extendable_count=$(wc -l <"${extendable_tasks_file}")
continuing_count=$(wc -l <"${continuing_tasks_file}")
pending_count=$(wc -l <"${pending_tasks_file}")
skipped_count=$((existing_count - continuing_count))
if [ "${include_existing}" = true ]; then
    skipped_count=0
fi

printf 'Defined tasks: %d\n' "${all_count}"
if [ "${#selected_tasks[@]}" -gt 0 ]; then
    printf 'Selected tasks: %d\n' "${selected_count}"
fi
printf 'Runnable tasks: %d\n' "${runnable_count}"
printf 'Existing resumable tasks: %d\n' "${resumable_count}"
printf 'Existing tasks below iteration target: %d\n' "${extendable_count}"
if [ "${dynamic}" = true ]; then
    printf 'Dynamic mode: directions below %s%% spec faults (metric above %s%%) are not rerun; tasks above %s%% errors stop\n' \
        "${converge_threshold}" "${converge_min_metric}" "${converge_max_error}"
fi
printf 'Existing tasks skipped: %d\n' "${skipped_count}"
printf 'Pending tasks: %d\n' "${pending_count}"
printf 'Task-level concurrency: %d\n' "${jobs}"
printf 'Initial mutant evaluation concurrency: %d per task\n' "${mutant_eval_workers}"
printf 'Reference-test link concurrency: %d branches per task (%d CPUs per agent)\n' \
    "${link_branch_workers}" "${agent_cpus}"
printf 'Mutant build concurrency: %d builds sharing %d CPUs (%d CPUs per build target)\n' \
    "${mutant_build_jobs}" "${mutant_build_cpus}" "$((mutant_build_cpus / mutant_build_jobs))"
printf 'Agent routes: %s\n' "${agent_routes_file}"
printf 'Run metadata: %s\n' "${run_dir}"

summarize_tokens() {
    local summary_args=(
        uv run python scripts/construction/summarize_iterative_tokens.py
        --iter-root "${iter_root}"
        --output "${run_dir}/token_usage.tsv"
        --agent-routes "${agent_routes_file}"
    )
    local summary_task
    while IFS= read -r summary_task; do
        summary_args+=(--task "${summary_task}")
    done <"${runnable_tasks_file}"
    "${summary_args[@]}"
}

if [ "${list_only}" = true ]; then
    exit 0
fi
if [ "${pending_count}" -eq 0 ]; then
    summarize_tokens
    exit 0
fi

export PROGRAMBENCH_CODEX_LOG_DIR="${trajectory_dir}/spec"
export PROGRAMBENCH_MUTANT_CODEX_LOG_DIR="${trajectory_dir}/mutant"

checkpoint_has_stage() {
    local checkpoint_file=$1
    local wanted_stage=$2
    local recorded_stage
    local recorded_status

    [ -f "${checkpoint_file}" ] || return 1
    while IFS=$'\t' read -r recorded_stage recorded_status _; do
        if [ "${recorded_stage}" = "${wanted_stage}" ] && [ "${recorded_status}" = completed ]; then
            return 0
        fi
    done <"${checkpoint_file}"
    return 1
}

record_stage_checkpoint() {
    local checkpoint_file=$1
    local stage=$2
    local source=${3:-command}

    if checkpoint_has_stage "${checkpoint_file}" "${stage}"; then
        return
    fi
    printf '%s\tcompleted\t%s\t%s\n' \
        "${stage}" "$(date --iso-8601=seconds)" "${source}" >>"${checkpoint_file}"
}

known_pipeline_stage() {
    case "$1" in
        prepare-skipped-tests|improve-spec|link-reference-tests|generate-mutants|ensure-mutants-killed|seal-mutants|iterate-spec|postprocess)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

bootstrap_legacy_checkpoints() {
    local task_log=$1
    local task_status=$2
    local checkpoint_file=$3
    local state=
    local completed_count
    local index
    local stage
    local stages=()

    if [ -s "${checkpoint_file}" ] || [ ! -f "${task_log}" ]; then
        return
    fi

    mapfile -t stages < <(sed -n 's/^stage=\([^ ]*\)$/\1/p' "${task_log}")
    if [ "${#stages[@]}" -eq 0 ]; then
        return
    fi

    if [ -f "${task_status}" ]; then
        IFS=$'\t' read -r state _ <"${task_status}" || true
    fi
    completed_count=${#stages[@]}
    if [ "${state}" != ok ]; then
        completed_count=$((completed_count - 1))
    fi

    for ((index = 0; index < completed_count; index++)); do
        stage=${stages[index]}
        if known_pipeline_stage "${stage}"; then
            record_stage_checkpoint "${checkpoint_file}" "${stage}" legacy-log
        fi
    done
}


latest_task_log() {
    local task=$1
    local legacy_log="${log_dir}/${task}.log"
    local candidate
    local suffix
    local latest_log=
    local latest_index=-1

    # Logs created before attempt suffixes were introduced are attempt zero for
    # numbering purposes, but a numbered log is always considered newer.
    if [ -f "${legacy_log}" ]; then
        latest_log=${legacy_log}
        latest_index=0
    fi
    for candidate in "${log_dir}/${task}_"*.log; do
        [ -f "${candidate}" ] || continue
        suffix=${candidate#"${log_dir}/${task}_"}
        suffix=${suffix%.log}
        if [[ "${suffix}" =~ ^[0-9]+$ ]] && [ "${suffix}" -ge "${latest_index}" ]; then
            latest_log=${candidate}
            latest_index=${suffix}
        fi
    done
    printf '%s\n' "${latest_log}"
}

next_task_log() {
    local task=$1
    local legacy_log="${log_dir}/${task}.log"
    local candidate
    local suffix
    local next_index=0

    # Treat an existing unsuffixed log as the first historical attempt. This
    # keeps it intact and starts migrated iteration roots at TASK_1.log.
    if [ -e "${legacy_log}" ]; then
        next_index=1
    fi
    for candidate in "${log_dir}/${task}_"*.log; do
        [ -e "${candidate}" ] || continue
        suffix=${candidate#"${log_dir}/${task}_"}
        suffix=${suffix%.log}
        if [[ "${suffix}" =~ ^[0-9]+$ ]] && [ "${suffix}" -ge "${next_index}" ]; then
            next_index=$((suffix + 1))
        fi
    done
    printf '%s/%s_%d.log\n' "${log_dir}" "${task}" "${next_index}"
}

hold_task_images() {
    # Claim this task's shared Docker images for as long as this subshell runs,
    # so a concurrent run's cleanup leaves them alone. The lease records the pid
    # and its process start time, so a crashed run releases its claim implicitly.
    # BASHPID re-expands to the command substitution's own subshell, so the start
    # time has to be read through a variable holding this shell's pid instead.
    local pid=${BASHPID}
    mkdir -p "${docker_lease_root}/$1"
    printf '%s %s\n' "${pid}" "$(awk '{print $22}' "/proc/${pid}/stat")" \
        >"${docker_lease_root}/$1/${pid}.owner"
}

release_task_images() {
    rm -f "${docker_lease_root}/$1/${BASHPID}.owner"
    rmdir "${docker_lease_root}/$1" 2>/dev/null || true
}

run_task() {
    local task=$1
    local previous_task_log
    local task_log
    local task_status="${status_dir}/${task}.status"
    local checkpoint_file="${checkpoint_dir}/${task}.tsv"
    local started_at
    local started_seconds
    local elapsed_seconds
    local elapsed
    local finished_at
    local completed_iterations
    local remaining_iterations
    local rc=0

    previous_task_log=$(latest_task_log "${task}")
    task_log=$(next_task_log "${task}")

    if [ "${include_existing}" = true ] && [ -d "${iter_root}/iter_0/spec/${task}" ]; then
        : >"${checkpoint_file}"
    elif [ -n "${previous_task_log}" ]; then
        bootstrap_legacy_checkpoints "${previous_task_log}" "${task_status}" "${checkpoint_file}"
    fi

    started_at=$(date --iso-8601=seconds)
    started_seconds=${SECONDS}
    printf '%s\n' "${task}" >>"${started_tasks_file}"
    printf 'running\t%s\t%s\n' "${started_at}" "${task}" >"${task_status}"

    printf '%s\n' "${BASHPID}" >"${pid_dir}/${task}.pid"
    hold_task_images "${task}"
    printf '[start] %s (pid %s; log: %s)\n' "${task}" "${BASHPID}" "${task_log}"

    set +e
    (
        set -e
        printf 'task=%s\nstarted_at=%s\n' "${task}" "${started_at}"
        # Downloads reference tests, ground truth, and the cleanroom unless present.
        printf "stage=fetch-inputs\n"
        uv run python scripts/dataset/fetch_task_inputs.py --task "${task}" --jobs 1
        if [ "${force_prepare_tests}" = false ] \
            && checkpoint_has_stage "${checkpoint_file}" prepare-skipped-tests \
            && [ -f "${skipped_tests_root}/${task}.json" ] \
            && [ -f "${prepared_tests_root}/work/${task}/reference_test_preparation.json" ] \
            && [ -x "${ground_truth_root}/executable/${task}/executable" ] \
            && [ -d "${ground_truth_root}/implementation/${task}" ] \
            && [ -d "extracted-tests/${task}" ]; then
            printf "stage=prepare-skipped-tests status=checkpoint-skip\n"
        else
            # printf "stage=prepare-skipped-tests\n"
            # # prepare_tests.sh evaluates the ground truth in the patched task image,
            # # which run_init.sh would otherwise not build until stage=prepare-images.
            # scripts/docker/install_task_patched.sh --task "${task}"
            # prepare_args=(
            #     bash scripts/construction/prepare_tests.sh
            #     --task "${task}" \
            #     --source-tests extracted-tests \
            #     --ground-truth-dir cleanroom/original \
            #     --output-root "${prepared_tests_root}" \
            #     --branch-workers 16 \
            #     --cpu-budget "${task_cpu_budget}"
            # )
            # if [ "${force_prepare_tests}" = true ]; then
            #     prepare_args+=(--force)
            # fi
            # "${prepare_args[@]}"
            record_stage_checkpoint "${checkpoint_file}" prepare-skipped-tests
        fi

        printf "stage=run-init\n"
        bash scripts/construction/run_init.sh \
            --task "${task}" \
            --iter-root "${iter_root}" \
            --tests-dir extracted-tests \
            --ground-truth-dir "${ground_truth_root}/executable" \
            --ground-truth-implementation-dir "${ground_truth_root}/implementation" \
            --skipped-tests "${skipped_tests_root}" \
            --checkpoint-file "${checkpoint_file}" \
            --mutant-validation-work-root "${mutant_validation_work_root}" \
            --agent-cpus "${agent_cpus}" \
            --cpu-budget "${task_cpu_budget}" \
            --mutant-build-cpus "${mutant_build_cpus}" \
            --mutant-build-jobs "${mutant_build_jobs}" \
            --mutant-eval-workers "${mutant_eval_workers}" \
            --link-branch-workers "${link_branch_workers}" \
            --max-repair-attempts "${max_repair_attempts}" \
            --min-num-spec-sec "${min_num_spec_sec}" \
            --max-num-spec-sec "${max_num_spec_sec}" \
            --target-tests-per-spec "${target_tests_per_spec}" \
            --final-mutants-per-spec "${final_mutants_per_spec}" \
            --step-model "improve_spec=${PROGRAMBENCH_ROUTE_MODEL[improve_spec]}" \
            --step-reasoning "improve_spec=${PROGRAMBENCH_ROUTE_REASONING[improve_spec]}" \
            --step-model "link_reference_tests=${PROGRAMBENCH_ROUTE_MODEL[link_reference_tests]}" \
            --step-reasoning "link_reference_tests=${PROGRAMBENCH_ROUTE_REASONING[link_reference_tests]}" \
            --step-model "generate_mutants=${PROGRAMBENCH_ROUTE_MODEL[generate_mutants]}" \
            --step-reasoning "generate_mutants=${PROGRAMBENCH_ROUTE_REASONING[generate_mutants]}" \
            --step-model "ensure_mutants_killed=${PROGRAMBENCH_ROUTE_MODEL[ensure_mutants_killed]}" \
            --step-reasoning "ensure_mutants_killed=${PROGRAMBENCH_ROUTE_REASONING[ensure_mutants_killed]}" \
            --retry-step-model "ensure_mutants_killed=${PROGRAMBENCH_ROUTE_RETRY_MODEL[ensure_mutants_killed]}" \
            --retry-step-reasoning "ensure_mutants_killed=${PROGRAMBENCH_ROUTE_RETRY_REASONING[ensure_mutants_killed]}" \
            "${init_options[@]}"

        if [ "${include_existing}" = true ]; then
            completed_iterations=0
        else
            completed_iterations=$(completed_iterations_for_task "${task}")
        fi
        remaining_iterations=$((iterations - completed_iterations))

        iterate_args=(
            bash scripts/construction/iterate_spec.sh
            --task "${task}"
            --iter-root "${iter_root}"
            --mutants-dir "${iter_root}/mutants"
            --tests-dir extracted-tests
            --ground-truth-dir "${ground_truth_root}/executable"
            --skipped-tests "${skipped_tests_root}"
            --reference-trials "${reference_trials}"
            --step-model "solve_codex=${PROGRAMBENCH_ROUTE_MODEL[solve_codex]}"
            --step-reasoning "solve_codex=${PROGRAMBENCH_ROUTE_REASONING[solve_codex]}"
            --step-model "classify_failures=${PROGRAMBENCH_ROUTE_MODEL[classify_failures]}"
            --step-reasoning "classify_failures=${PROGRAMBENCH_ROUTE_REASONING[classify_failures]}"
            --step-model "polish_iteration=${PROGRAMBENCH_ROUTE_MODEL[polish_iteration]}"
            --step-reasoning "polish_iteration=${PROGRAMBENCH_ROUTE_REASONING[polish_iteration]}"
            --step-model "generate_tests=${PROGRAMBENCH_ROUTE_MODEL[generate_tests]}"
            --step-reasoning "generate_tests=${PROGRAMBENCH_ROUTE_REASONING[generate_tests]}"
            --step-model "classify_mutants=${PROGRAMBENCH_ROUTE_MODEL[classify_mutants]}"
            --step-reasoning "classify_mutants=${PROGRAMBENCH_ROUTE_REASONING[classify_mutants]}"
            --step-model "polish_generated_test_spec=${PROGRAMBENCH_ROUTE_MODEL[polish_generated_test_spec]}"
            --step-reasoning "polish_generated_test_spec=${PROGRAMBENCH_ROUTE_REASONING[polish_generated_test_spec]}"
            --workers 1
            --branch-workers 16
            --cpu-budget "${task_cpu_budget}"
            --agent-cpus "${agent_cpus}"
            --classifier-cpus "${classifier_cpus}"
            --classify-branch-workers 8
            --mutant-classify-batch-workers 8
            "${iteration_options[@]}"
        )

        if [ "${remaining_iterations}" -le 0 ]; then
            printf "stage=iterate-spec status=target-reached completed=%d target=%d\n" \
                "${completed_iterations}" "${iterations}"
            record_stage_checkpoint "${checkpoint_file}" iterate-spec detected-iterations
        elif [ "${dynamic}" = true ]; then
            for ((iter = completed_iterations; iter < iterations; iter++)); do
                convergence_json="${iter_root}/iter_$((iter + 1))/stages/${task}/convergence.json"
                convergence=$(task_convergence "${task}" --output "${convergence_json}")
                if [ "${convergence}" = "acc=1 validity_rate=1 mutation_score=1" ]; then
                    status=converged
                    grep -q '"error_stopped": true' "${convergence_json}" && status=error-stopped
                    printf "stage=iterate-spec status=%s completed=%d target=%d\n" "${status}" "${iter}" "${iterations}"
                    break
                fi
                mapfile -t skip_options < <(iteration_skip_options "${convergence}")
                printf "stage=iterate-spec start-iter=%d iterations=1 target=%d %s skip=%s\n" \
                    "${iter}" "${iterations}" "${convergence}" "${skip_options[*]:-none}"
                "${iterate_args[@]}" --start-iter "${iter}" --iterations 1 "${skip_options[@]}"
            done
            record_stage_checkpoint "${checkpoint_file}" iterate-spec
        else
            printf "stage=iterate-spec start-iter=%d iterations=%d target=%d\n" \
                "${completed_iterations}" "${remaining_iterations}" "${iterations}"
            "${iterate_args[@]}" --start-iter "${completed_iterations}" --iterations "${remaining_iterations}"
            record_stage_checkpoint "${checkpoint_file}" iterate-spec
        fi

        printf "stage=postprocess\n"
        bash scripts/construction/run_postprocess.sh
    ) >"${task_log}" 2>&1
    rc=$?
    set -e

    rm -f "${pid_dir}/${task}.pid"
    release_task_images "${task}"
    finished_at=$(date --iso-8601=seconds)
    elapsed_seconds=$((SECONDS - started_seconds))
    printf -v elapsed '%dh%dm' "$((elapsed_seconds / 3600))" "$((elapsed_seconds % 3600 / 60))"
    if [ "${rc}" -eq 0 ]; then
        printf 'ok\t%s\t%s\t%s\n' "${started_at}" "${finished_at}" "${task}" >"${task_status}"
        printf '[ok] %s (in %s; log: %s)\n' "${task}" "${elapsed}" "${task_log}"
    else
        printf 'failed:%d\t%s\t%s\t%s\n' "${rc}" "${started_at}" "${finished_at}" "${task}" >"${task_status}"
        printf '[failed:%d] %s (in %s; log: %s)\n' "${rc}" "${task}" "${elapsed}" "${task_log}" >&2
    fi
    return "${rc}"
}

trap 'trap - INT TERM; kill $(jobs -pr) 2>/dev/null || true; wait || true; exit 130' INT TERM

running=0
while IFS= read -r task; do
    run_task "${task}" &
    running=$((running + 1))
    if [ "${running}" -ge "${jobs}" ]; then
        wait -n || true
        running=$((running - 1))
    fi
done <"${pending_tasks_file}"

while [ "${running}" -gt 0 ]; do
    wait -n || true
    running=$((running - 1))
done

ok_count=0
failed_count=0
while IFS= read -r task; do
    task_status="${status_dir}/${task}.status"
    [ -f "${task_status}" ] || continue
    IFS=$'\t' read -r state _ <"${task_status}" || true
    case "${state}" in
        ok) ok_count=$((ok_count + 1)) ;;
        failed:*) failed_count=$((failed_count + 1)) ;;
    esac
done <"${pending_tasks_file}"
printf 'Batch finished: ok=%d failed=%d\n' "${ok_count}" "${failed_count}"

summarize_tokens

if [ "${failed_count}" -gt 0 ]; then
    exit 1
fi
