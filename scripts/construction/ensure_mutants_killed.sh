#!/usr/bin/env bash
set -euo pipefail

task=
tests_dir=
skipped_tests=
ground_truth_dir=ground_truth/executable
ground_truth_implementation_dir=ground_truth/implementation
mutants_dir=
spec_dir=
work_dir=
model=gpt-5.6-luna
reasoning=max
retry_model=gpt-5.6-sol
retry_reasoning=high
timeout=7200
max_repair_attempts=3
max_infrastructure_retries=2
workers=1
branch_workers=2
cpu_budget=0
cleanroom_base_image=
force=false
prune_failing_tests=false

usage() {
    printf "%s\n" "Usage: $0 --task TASK --tests-dir DIR --skipped-tests PATH --mutants-dir DIR --spec-dir DIR --work-dir DIR [options]" "" "Co-validate reference tests and mutants. The reference suite is fixed by default;" "with --prune-failing-tests, add ground-truth-failing test functions to the shared skip list. Then improve mutant focus within a best-effort repair budget." "" "  --model MODEL / --reasoning EFFORT" "      Agent route for repair attempt 1 (default: ${model} / ${reasoning})." "  --cleanroom-base-image IMAGE" "      Codex-enabled task cleanroom used for repair and rebuild (default: auto-build task_cleanroom_codex)." "  --skipped-tests PATH" "      Run-scoped skip list; only updated with --prune-failing-tests." "  --prune-failing-tests" "      Skip test functions that fail on ground truth or kill over 50% of mutants (default: off, suite is kept as is)." "  --ground-truth-implementation-dir DIR" "      Retained reference sources; a build/ directory there is source, so repaired mutants keep it (default: ${ground_truth_implementation_dir})." "  --retry-model MODEL / --retry-reasoning EFFORT" "      Agent route from repair attempt 2 (default: ${retry_model} / ${retry_reasoning})."
}

require_value() {
    if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        usage >&2
        exit 1
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --task) require_value "$@"; task=$2; shift 2 ;;
        --tests-dir) require_value "$@"; tests_dir=$2; shift 2 ;;
        --skipped-tests) require_value "$@"; skipped_tests=$2; shift 2 ;;
        --ground-truth-dir) require_value "$@"; ground_truth_dir=$2; shift 2 ;;
        --ground-truth-implementation-dir) require_value "$@"; ground_truth_implementation_dir=$2; shift 2 ;;
        --mutants-dir) require_value "$@"; mutants_dir=$2; shift 2 ;;
        --spec-dir) require_value "$@"; spec_dir=$2; shift 2 ;;
        --work-dir) require_value "$@"; work_dir=$2; shift 2 ;;
        --model) require_value "$@"; model=$2; shift 2 ;;
        --reasoning) require_value "$@"; reasoning=$2; shift 2 ;;
        --retry-model) require_value "$@"; retry_model=$2; shift 2 ;;
        --retry-reasoning) require_value "$@"; retry_reasoning=$2; shift 2 ;;
        --timeout) require_value "$@"; timeout=$2; shift 2 ;;
        --max-repair-attempts) require_value "$@"; max_repair_attempts=$2; shift 2 ;;
        --max-infrastructure-retries) require_value "$@"; max_infrastructure_retries=$2; shift 2 ;;
        --workers) require_value "$@"; workers=$2; shift 2 ;;
        --branch-workers) require_value "$@"; branch_workers=$2; shift 2 ;;
        --cpu-budget) require_value "$@"; cpu_budget=$2; shift 2 ;;
        --cleanroom-base-image) require_value "$@"; cleanroom_base_image=$2; shift 2 ;;
        --force) force=true; shift ;;
        --prune-failing-tests) prune_failing_tests=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [ -z "${task}" ] || [ -z "${tests_dir}" ] || [ -z "${skipped_tests}" ] || [ -z "${mutants_dir}" ] || [ -z "${spec_dir}" ] || [ -z "${work_dir}" ]; then
    echo "--task, --tests-dir, --skipped-tests, --mutants-dir, --spec-dir, and --work-dir are required" >&2
    exit 1
fi
if [ ! -x "${ground_truth_dir}/${task}/executable" ]; then
    echo "Prepared ground-truth executable is missing for ${task}: ${ground_truth_dir}/${task}/executable" >&2
    exit 1
fi
if [[ ! "${max_repair_attempts}" =~ ^[0-9]+$ ]]; then
    echo "--max-repair-attempts must be a non-negative integer" >&2
    exit 1
fi
if [[ ! "${max_infrastructure_retries}" =~ ^[0-9]+$ ]]; then
    echo "--max-infrastructure-retries must be a non-negative integer" >&2
    exit 1
fi
for value in "${timeout}" "${workers}" "${branch_workers}"; do
    if [[ ! "${value}" =~ ^[1-9][0-9]*$ ]]; then
        echo "Timeout and worker values must be positive integers" >&2
        exit 1
    fi
done

. scripts/docker/docker_preflight.sh
programbench_docker_preflight || exit 1

if [ -z "${cleanroom_base_image}" ]; then
    cleanroom_base_image="$(scripts/docker/install_codex_cleanroom.sh --task "${task}" --print-image)"
    scripts/docker/install_codex_cleanroom.sh --task "${task}"
else
    echo "Using Codex cleanroom image: ${cleanroom_base_image}"
fi

cmd=(
    uv run python -m programbench.mutant_kill_validation
    --task "${task}"
    --tests-dir "${tests_dir}"
    --skipped-tests "${skipped_tests}"
    --ground-truth-dir "${ground_truth_dir}"
    --ground-truth-implementation-dir "${ground_truth_implementation_dir}"
    --mutants-dir "${mutants_dir}"
    --spec-dir "${spec_dir}"
    --work-dir "${work_dir}"
    --model "${model}"
    --reasoning "${reasoning}"
    --retry-model "${retry_model}"
    --retry-reasoning "${retry_reasoning}"
    --timeout "${timeout}"
    --max-repair-attempts "${max_repair_attempts}"
    --max-infrastructure-retries "${max_infrastructure_retries}"
    --workers "${workers}"
    --branch-workers "${branch_workers}"
    --cpu-budget "${cpu_budget}"
    --repair-image "${cleanroom_base_image}"
)
if [ "${force}" = true ]; then
    cmd+=(--force)
fi
if [ "${prune_failing_tests}" = true ]; then
    cmd+=(--prune-failing-tests)
fi
"${cmd[@]}"
