#!/usr/bin/env bash
set -euo pipefail

task=
source_tests=extracted-tests
output_skipped_tests=
ground_truth_dir=cleanroom/original
ground_truth_root=
build_image=
work_dir=
branch_workers=1
cpu_budget=0
trials=3
force=false

usage() {
    cat <<EOF
Usage: $0 --task TASK --output-skipped-tests DIR --work-dir DIR [options]

Create a run-scoped skip list from canonical ignored_tests, add test functions
that fail on ground truth, and verify that every remaining active test passes.

Options:
  --task TASK                 Task instance id (required)
  --source-tests DIR          Original extracted test root (default: ${source_tests})
  --output-skipped-tests DIR   Output root for <task>.json (required)
  --ground-truth-dir DIR      Ground-truth cleanroom root (default: ${ground_truth_dir})
  --ground-truth-root DIR     Store the compiled binary and test snapshot here
  --build-image IMAGE         Image used to compile the reference source
  --work-dir DIR              Evaluation/report directory (required)
  --branch-workers N          Test branches evaluated concurrently (default: ${branch_workers})
  --cpu-budget N              Total CPU budget divided across active containers; 0 disables budgeting (default: ${cpu_budget})
  --trials N                  Reference runs per attempt; a test failing in any run is skipped (default: ${trials})
  --force                     Replace an existing skipped-test list
  -h, --help                  Show this help
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
        --output-skipped-tests) require_value "$@"; output_skipped_tests=$2; shift 2 ;;
        --ground-truth-dir) require_value "$@"; ground_truth_dir=$2; shift 2 ;;
        --ground-truth-root) require_value "$@"; ground_truth_root=$2; shift 2 ;;
        --build-image) require_value "$@"; build_image=$2; shift 2 ;;
        --work-dir) require_value "$@"; work_dir=$2; shift 2 ;;
        --branch-workers) require_value "$@"; branch_workers=$2; shift 2 ;;
        --cpu-budget) require_value "$@"; cpu_budget=$2; shift 2 ;;
        --trials) require_value "$@"; trials=$2; shift 2 ;;
        --force) force=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [ -z "${task}" ] || [ -z "${output_skipped_tests}" ] || [ -z "${work_dir}" ]; then
    echo "--task, --output-skipped-tests, and --work-dir are required" >&2
    usage >&2
    exit 1
fi
. scripts/docker/docker_preflight.sh
programbench_docker_preflight || exit $?

cmd=(
    uv run python -m programbench.reference_test_preparation
    --task "${task}"
    --source-tests "${source_tests}"
    --output-skipped-tests "${output_skipped_tests}"
    --ground-truth-dir "${ground_truth_dir}"
    --work-dir "${work_dir}"
    --branch-workers "${branch_workers}"
    --cpu-budget "${cpu_budget}"
    --trials "${trials}"
)
if [ -n "${ground_truth_root}" ]; then
    cmd+=(--ground-truth-root "${ground_truth_root}")
fi
if [ -n "${build_image}" ]; then
    cmd+=(--build-image "${build_image}")
fi
if [ "${force}" = true ]; then
    cmd+=(--force)
fi

"${cmd[@]}"
