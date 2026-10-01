#!/usr/bin/env bash
set -euo pipefail

task=
iter_root=output/iterative
tests_dir=extracted-tests
ground_truth_dir=ground_truth/executable
ground_truth_implementation_dir=ground_truth/implementation
skipped_tests=
checkpoint_file=
mutant_validation_work_root=
agent_cpus=6
cpu_budget=32
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
force=false
prune_failing_tests=false

. scripts/construction/agent_routes.sh
programbench_agent_routes_reset
programbench_agent_route_register improve_spec gpt-5.6-sol high
programbench_agent_route_register link_reference_tests gpt-5.6-sol high
programbench_agent_route_register generate_mutants gpt-5.6-sol high
programbench_agent_route_register ensure_mutants_killed gpt-5.6-luna max gpt-5.6-sol high

usage() {
    cat <<EOF
Usage: $0 --task TASK [--iter-root DIR] [--tests-dir DIR] [--ground-truth-dir DIR] [--ground-truth-implementation-dir DIR] [--skipped-tests PATH] [options]

Create and validate iter_0 after reusable test preparation. This script owns
the improve-spec, link-reference-tests, generate-mutants, build-mutants,
ensure-mutants-killed, and seal-mutants stages.

Mutants are written once to ITER_ROOT/mutants and sealed there: repo_N trees are
replaced by their diff against the ground-truth implementation, and every
iteration shares that one store rather than carrying a copy per iteration.

Options:
  --min-num-spec-sec N  Minimum specification sections (default: 10)
  --max-num-spec-sec N  Maximum specification sections (default: 100)
  --checkpoint-file PATH       Stage checkpoint file
  --mutant-validation-work-root DIR
  --agent-cpus N
  --cpu-budget N
  --mutant-build-cpus N
  --mutant-build-jobs N
  --mutant-eval-workers N      Initial evaluation workers (default: half --cpu-budget, rounded down, minimum 1)
  --link-branch-workers N      Reference-test branches linked concurrently (default: --cpu-budget divided by --agent-cpus, minimum 1)
  --max-repair-attempts N Maximum mutant repair requests per task (default: ${max_repair_attempts}; 0 disables repairs)
  --target-tests-per-spec N
  --final-mutants-per-spec N
  --model-name MODEL
  --reasoning-effort EFFORT
  --step-model STEP=MODEL
  --step-reasoning STEP=EFFORT
  --retry-step-model STEP=MODEL
  --retry-step-reasoning STEP=EFFORT
  --prune-failing-tests   Let mutant validation add failing reference tests to the skip list (default: off)
  --force
EOF
}

require_value() {
    if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        usage >&2
        exit 1
    fi
}

checkpoint_has_stage() {
    local wanted_stage=$1
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
    local stage=$1
    if checkpoint_has_stage "${stage}"; then
        return
    fi
    printf '%s\tcompleted\t%s\tcommand\n' "${stage}" "$(date --iso-8601=seconds)" >>"${checkpoint_file}"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --task) require_value "$@"; task=$2; shift 2 ;;
        --iter-root) require_value "$@"; iter_root=$2; shift 2 ;;
        --tests-dir) require_value "$@"; tests_dir=$2; shift 2 ;;
        --ground-truth-dir) require_value "$@"; ground_truth_dir=$2; shift 2 ;;
        --ground-truth-implementation-dir) require_value "$@"; ground_truth_implementation_dir=$2; shift 2 ;;
        --skipped-tests) require_value "$@"; skipped_tests=$2; shift 2 ;;
        --checkpoint-file) require_value "$@"; checkpoint_file=$2; shift 2 ;;
        --mutant-validation-work-root) require_value "$@"; mutant_validation_work_root=$2; shift 2 ;;
        --agent-cpus) require_value "$@"; agent_cpus=$2; shift 2 ;;
        --cpu-budget) require_value "$@"; cpu_budget=$2; shift 2 ;;
        --mutant-build-cpus) require_value "$@"; mutant_build_cpus=$2; shift 2 ;;
        --mutant-eval-workers) require_value "$@"; mutant_eval_workers=$2; shift 2 ;;
        --link-branch-workers) require_value "$@"; link_branch_workers=$2; shift 2 ;;
        --mutant-build-jobs) require_value "$@"; mutant_build_jobs=$2; shift 2 ;;
        --max-repair-attempts) require_value "$@"; max_repair_attempts=$2; shift 2 ;;
        --min-num-spec-sec) require_value "$@"; min_num_spec_sec=$2; shift 2 ;;
        --max-num-spec-sec) require_value "$@"; max_num_spec_sec=$2; shift 2 ;;
        --target-tests-per-spec) require_value "$@"; target_tests_per_spec=$2; shift 2 ;;
        --final-mutants-per-spec) require_value "$@"; final_mutants_per_spec=$2; shift 2 ;;
        --model-name) require_value "$@"; global_model_override=$2; shift 2 ;;
        --reasoning-effort) require_value "$@"; global_reasoning_override=$2; shift 2 ;;
        --step-model) require_value "$@"; programbench_agent_route_override model "$2"; shift 2 ;;
        --step-reasoning) require_value "$@"; programbench_agent_route_override reasoning "$2"; shift 2 ;;
        --retry-step-model) require_value "$@"; programbench_agent_route_override retry-model "$2"; shift 2 ;;
        --retry-step-reasoning) require_value "$@"; programbench_agent_route_override retry-reasoning "$2"; shift 2 ;;
        --force) force=true; shift ;;
        --prune-failing-tests) prune_failing_tests=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ ! "${max_repair_attempts}" =~ ^[0-9]+$ ]]; then
    echo "--max-repair-attempts must be a non-negative integer: ${max_repair_attempts}" >&2
    exit 1
fi

if [[ ! "${min_num_spec_sec}" =~ ^[1-9][0-9]*$ ]] || [[ ! "${max_num_spec_sec}" =~ ^[1-9][0-9]*$ ]] || (( min_num_spec_sec > max_num_spec_sec )); then
    echo "Section limits must satisfy 1 <= min <= max" >&2
    exit 1
fi

if [[ ! "${cpu_budget}" =~ ^[1-9][0-9]*$ ]]; then
    echo "--cpu-budget must be a positive integer: ${cpu_budget}" >&2
    exit 1
fi
if [ -z "${mutant_eval_workers}" ]; then
    mutant_eval_workers=$((cpu_budget / 2))
    if [ "${mutant_eval_workers}" -lt 1 ]; then mutant_eval_workers=1; fi
fi
if [[ ! "${mutant_eval_workers}" =~ ^[1-9][0-9]*$ ]]; then
    echo "--mutant-eval-workers must be a positive integer: ${mutant_eval_workers}" >&2
    exit 1
fi
# One Codex container per branch, each capped at --agent-cpus, so the branch count
# is what keeps this stage inside the same per-task budget as evaluation and builds.
if [ -z "${link_branch_workers}" ]; then
    link_branch_workers=$((cpu_budget / agent_cpus))
    if [ "${link_branch_workers}" -lt 1 ]; then link_branch_workers=1; fi
fi
if [[ ! "${link_branch_workers}" =~ ^[1-9][0-9]*$ ]]; then
    echo "--link-branch-workers must be a positive integer: ${link_branch_workers}" >&2
    exit 1
fi

for value in "${target_tests_per_spec}" "${final_mutants_per_spec}"; do
    if [[ ! "${value}" =~ ^[1-9][0-9]*$ ]]; then
        echo "Mutant portfolio controls must be positive integers: ${value}" >&2
        exit 1
    fi
done
if [ "${final_mutants_per_spec}" -gt "${target_tests_per_spec}" ]; then
    echo "--final-mutants-per-spec must not exceed target-tests-per-spec" >&2
    exit 1
fi

if [ -z "${task}" ]; then
    echo "--task is required" >&2
    usage >&2
    exit 1
fi

if [ -z "${skipped_tests}" ]; then
    skipped_tests="ground_truth/skipped-tests"
fi

iter_root=${iter_root%/}
if [ -z "${mutant_build_cpus}" ]; then
    mutant_build_cpus=${cpu_budget}
fi

if [ -z "${checkpoint_file}" ]; then
    checkpoint_file="${iter_root}/batch/checkpoints/${task}.tsv"
fi
if [ -z "${mutant_validation_work_root}" ]; then
    mutant_validation_work_root="${iter_root}/batch/mutant-validation"
fi
mkdir -p "$(dirname "${checkpoint_file}")" "${mutant_validation_work_root}"

if [ ! -f "${skipped_tests}/${task}.json" ] && [ ! -f "${skipped_tests}" ]; then
    echo "Prepared skipped-test list is missing for ${task}: ${skipped_tests}" >&2
    exit 1
fi
if [ ! -d "${ground_truth_implementation_dir}/${task}" ]; then
    echo "Prepared ground-truth implementation is missing for ${task}: ${ground_truth_implementation_dir}/${task}" >&2
    exit 1
fi
if [ ! -x "${ground_truth_dir}/${task}/executable" ]; then
    echo "Prepared ground-truth executable is missing for ${task}: ${ground_truth_dir}/${task}/executable" >&2
    exit 1
fi

programbench_agent_routes_resolve "${global_model_override}" "${global_reasoning_override}"
escaped_task=${task//./\\.}
task_filter="^${escaped_task}$"

export PROGRAMBENCH_CODEX_LOG_DIR="${PROGRAMBENCH_CODEX_LOG_DIR:-${iter_root}/batch/trajectories/spec}"
export PROGRAMBENCH_MUTANT_CODEX_LOG_DIR="${PROGRAMBENCH_MUTANT_CODEX_LOG_DIR:-${iter_root}/batch/trajectories/mutant}"
mkdir -p "${PROGRAMBENCH_CODEX_LOG_DIR}" "${PROGRAMBENCH_MUTANT_CODEX_LOG_DIR}"

# Evaluation runs against the patched task image, and mutant/reference builds
# against the build-only image. Both are cheap layers and no-ops once built.
printf 'stage=prepare-images\n'
scripts/docker/install_task_patched.sh --task "${task}"
scripts/docker/install_task_mutantbuild.sh --task "${task}"

# Which paths build.sh produces rather than reads. Recorded from the retained
# implementation, so this is independent of prepare-skipped-tests and stays
# valid for tasks whose prepared tests are already cached. No-op once recorded.
printf 'stage=record-generated-files\n'
uv run programbench record-generated-files \
    --task "${task}" \
    --ground-truth-dir "${ground_truth_implementation_dir}" \
    --image "$(scripts/docker/install_task_patched.sh --task "${task}" --print-image)" \
    --docker-cpus "${mutant_build_cpus}"

if [ "${force}" = false ] && checkpoint_has_stage improve-spec; then
    printf 'stage=improve-spec status=checkpoint-skip\n'
else
    printf 'stage=improve-spec\n'
    uv run programbench improve-spec \
        --min-num-spec-sec "${min_num_spec_sec}" \
        --max-num-spec-sec "${max_num_spec_sec}" \
        --output "${iter_root}/iter_0/spec" \
        --testdir "${tests_dir}" \
        --skipped-tests "${skipped_tests}" \
        --spec_in cleanroom/original \
        --filter "${task_filter}" \
        --model "${PROGRAMBENCH_ROUTE_MODEL[improve_spec]}" \
        --reasoning-effort "${PROGRAMBENCH_ROUTE_REASONING[improve_spec]}" \
        --docker-cpus "${agent_cpus}" \
        --force
    test -f "${iter_root}/iter_0/spec/${task}/spec.md" || {
        echo "Improved specification is missing for ${task}" >&2
        exit 1
    }
    record_stage_checkpoint improve-spec
fi

initial_test_spec_links="${iter_root}/iter_0/test-spec-links/${task}/test_spec_links.json"
if [ "${force}" = false ] \
    && checkpoint_has_stage link-reference-tests \
    && [ -f "${initial_test_spec_links}" ]; then
    printf 'stage=link-reference-tests status=checkpoint-skip\n'
else
    printf 'stage=link-reference-tests\n'
    PROGRAMBENCH_DOCKER_CPUS="${agent_cpus}" uv run python -m programbench.reference_test_linking \
        --task "${task}" \
        --spec-dir "${iter_root}/iter_0/spec/${task}" \
        --tests-dir "${tests_dir}" \
        --skipped-tests "${skipped_tests}" \
        --output "${initial_test_spec_links}" \
        --trajectory "${iter_root}/iter_0/log/${task}/link_reference_tests.initial.traj.json" \
        --model "${PROGRAMBENCH_ROUTE_MODEL[link_reference_tests]}" \
        --reasoning "${PROGRAMBENCH_ROUTE_REASONING[link_reference_tests]}" \
        --branch-workers "${link_branch_workers}"
    test -f "${initial_test_spec_links}" || {
        echo "Initial test/spec links are missing for ${task}" >&2
        exit 1
    }
    record_stage_checkpoint link-reference-tests
fi

mutants_root="${iter_root}/mutants"
initial_mutant_plan="${mutants_root}/${task}/mutant_plan.json"
if [ "${force}" = false ] \
    && checkpoint_has_stage generate-mutants \
    && [ -f "${initial_mutant_plan}" ]; then
    printf 'stage=generate-mutants status=checkpoint-skip\n'
else
    printf 'stage=generate-mutants\n'
    bash scripts/construction/generate_mutants.sh \
        --task "${task}" \
        --output "${mutants_root}" \
        --repo-dir "${tests_dir}" \
        --ground-truth-implementation-dir "${ground_truth_implementation_dir}" \
        --spec-in "${iter_root}/iter_0/spec" \
        --test-spec-links "${iter_root}/iter_0/test-spec-links" \
        --model "${PROGRAMBENCH_ROUTE_MODEL[generate_mutants]}" \
        --reasoning "${PROGRAMBENCH_ROUTE_REASONING[generate_mutants]}" \
        --docker-cpus "${mutant_build_cpus}" \
        --mutant-build-jobs "${mutant_build_jobs}" \
        --target-tests-per-spec "${target_tests_per_spec}" \
        --final-mutants-per-spec "${final_mutants_per_spec}"
    test -f "${mutants_root}/${task}/mutants.json" || {
        echo "Generated mutant manifest is missing for ${task}" >&2
        exit 1
    }
    record_stage_checkpoint generate-mutants
fi

# Unconditional: this is the readiness check for the store generation left
# behind, and a no-op once every payload resolves. Never checkpointed, so a
# crash between the manifest and the executables cannot resume as complete.
printf 'stage=build-mutants\n'
uv run programbench build-mutants "${mutants_root}" \
    --task "${task}" \
    --docker-cpus "${mutant_build_cpus}" \
    --mutant-build-jobs "${mutant_build_jobs}"

initial_mutant_validation="${mutant_validation_work_root}/initial/${task}/mutant_kill_validation.json"
if [ "${force}" = false ] \
    && checkpoint_has_stage ensure-mutants-killed \
    && [ -f "${initial_mutant_validation}" ] \
    && grep -q '"validation_mode": "best_effort_target_test_singleton"' "${initial_mutant_validation}"; then
    printf 'stage=ensure-mutants-killed status=checkpoint-skip\n'
else
    printf 'stage=ensure-mutants-killed\n'
    ensure_options=()
    if [ "${prune_failing_tests}" = true ]; then ensure_options+=(--prune-failing-tests); fi
    bash scripts/construction/ensure_mutants_killed.sh \
        --task "${task}" \
        --tests-dir "${tests_dir}" \
        --skipped-tests "${skipped_tests}" \
        --ground-truth-dir "${ground_truth_dir}" \
        --ground-truth-implementation-dir "${ground_truth_implementation_dir}" \
        --mutants-dir "${mutants_root}" \
        --spec-dir "${iter_root}/iter_0/spec" \
        --work-dir "${mutant_validation_work_root}/initial/${task}" \
        --workers 1 \
        --branch-workers "${mutant_eval_workers}" \
        --max-repair-attempts "${max_repair_attempts}" \
        --cpu-budget "${cpu_budget}" \
        --model "${PROGRAMBENCH_ROUTE_MODEL[ensure_mutants_killed]}" \
        --reasoning "${PROGRAMBENCH_ROUTE_REASONING[ensure_mutants_killed]}" \
        --retry-model "${PROGRAMBENCH_ROUTE_RETRY_MODEL[ensure_mutants_killed]}" \
        --retry-reasoning "${PROGRAMBENCH_ROUTE_RETRY_REASONING[ensure_mutants_killed]}" \
        "${ensure_options[@]}" \
        --force
    test -f "${initial_mutant_validation}" || {
        echo "Mutant-kill validation report is missing for ${task}" >&2
        exit 1
    }
    record_stage_checkpoint ensure-mutants-killed
fi

if [ "${force}" = false ] \
    && checkpoint_has_stage seal-mutants \
    && [ -f "${mutants_root}/${task}/sources.json" ]; then
    printf 'stage=seal-mutants status=checkpoint-skip\n'
else
    printf 'stage=seal-mutants\n'
    uv run programbench seal-mutants "${mutants_root}" \
        --task "${task}" \
        --ground-truth-dir "${ground_truth_implementation_dir}"
    record_stage_checkpoint seal-mutants
fi
