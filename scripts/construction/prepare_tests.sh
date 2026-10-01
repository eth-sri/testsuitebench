#!/usr/bin/env bash
set -euo pipefail

task=
source_tests=extracted-tests
ground_truth_dir=cleanroom/original
build_image=
output_root=output/prepared-tests
ground_truth_root=ground_truth
branch_workers=16
cpu_budget=32
force=false

usage() {
    cat <<EOF
Usage: $0 --task TASK [--output-root DIR] [--ground-truth-root DIR] [--source-tests DIR] [--ground-truth-dir DIR] [--build-image IMAGE] [--branch-workers N] [--cpu-budget N] [--force]

Prepare and verify a reusable skipped-test list independently of any iteration
root. Existing complete preparation output is reused unless --force is given.

Outputs:
  <ground-truth-root>/skipped-tests/<task>.json
  <ground-truth-root>/implementation/<task>/
  <ground-truth-root>/executable/<task>/executable
  <output-root>/work/<task>/reference_test_preparation.json
EOF
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
        --source-tests) require_value "$@"; source_tests=$2; shift 2 ;;
        --ground-truth-dir) require_value "$@"; ground_truth_dir=$2; shift 2 ;;
        --build-image) require_value "$@"; build_image=$2; shift 2 ;;
        --output-root) require_value "$@"; output_root=$2; shift 2 ;;
        --ground-truth-root) require_value "$@"; ground_truth_root=$2; shift 2 ;;
        --branch-workers) require_value "$@"; branch_workers=$2; shift 2 ;;
        --cpu-budget) require_value "$@"; cpu_budget=$2; shift 2 ;;
        --force) force=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [ -z "${task}" ]; then
    echo "--task is required" >&2
    usage >&2
    exit 1
fi

output_root=${output_root%/}
ground_truth_root=${ground_truth_root%/}
skipped_tests_root="${ground_truth_root}/skipped-tests"
work_dir="${output_root}/work/${task}"
report="${work_dir}/reference_test_preparation.json"
skipped_tests_file="${skipped_tests_root}/${task}.json"
our_implementation="${ground_truth_root}/implementation/${task}"
our_executable="${ground_truth_root}/executable/${task}/executable"
refresh_incomplete=false

if [ "${force}" = false ] && [ -f "${skipped_tests_file}" ] && [ -f "${report}" ] \
    && [ -x "${our_executable}" ] && [ -d "${our_implementation}" ] \
    && [ -d "${source_tests}/${task}" ]; then
    printf 'Reusing prepared tests for %s\n' "${task}"
    printf 'Skipped tests: %s\n' "${skipped_tests_file}"
    printf 'Report: %s\n' "${report}"
    exit 0
fi

# A previous version, interruption, or newly required artifact can leave a
# report/work directory without the complete reusable output. Rebuild only
# this task's preparation state automatically; iteration outputs and their
# checkpoints live elsewhere and remain untouched.
if [ "${force}" = false ] \
    && { [ -d "${work_dir}" ] || [ -f "${skipped_tests_file}" ] \
        || [ -d "${our_implementation}" ] || [ -f "${our_executable}" ]; }; then
    refresh_incomplete=true
    printf 'Refreshing incomplete prepared tests for %s\n' "${task}"
fi

if [ -z "${build_image}" ]; then
    build_image="$(scripts/docker/install_codex_cleanroom.sh --task "${task}" --print-image)"
    scripts/docker/install_codex_cleanroom.sh --task "${task}"
fi

mkdir -p "${skipped_tests_root}" "${work_dir}"
args=(
    bash scripts/construction/prepare_reference_tests.sh
    --task "${task}"
    --source-tests "${source_tests}"
    --output-skipped-tests "${skipped_tests_root}"
    --ground-truth-dir "${ground_truth_dir}"
    --ground-truth-root "${ground_truth_root}"
    --build-image "${build_image}"
    --work-dir "${work_dir}"
    --branch-workers "${branch_workers}"
    --cpu-budget "${cpu_budget}"
)
if [ "${force}" = true ] || [ "${refresh_incomplete}" = true ]; then
    args+=(--force)
fi
"${args[@]}"

if [ ! -f "${skipped_tests_file}" ]; then
    echo "Skipped-test list is missing for ${task}: ${skipped_tests_file}" >&2
    exit 1
fi
if [ ! -f "${report}" ]; then
    echo "Preparation report is missing for ${task}: ${report}" >&2
    exit 1
fi
if [ ! -x "${our_executable}" ] || [ ! -d "${our_implementation}" ] \
    || [ ! -d "${source_tests}/${task}" ]; then
    echo "Reusable ground truth is incomplete for ${task}: ${ground_truth_root}" >&2
    exit 1
fi
