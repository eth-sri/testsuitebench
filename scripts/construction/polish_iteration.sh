#!/usr/bin/env bash
set -euo pipefail

default_model=codex/gpt-5.6-luna
default_reasoning=high
default_task=abishekvashok__cmatrix.5c082c6
default_tests_dir=extracted-tests

model=${default_model}
reasoning=${default_reasoning}
task=${default_task}
tests_dir=${default_tests_dir}
skipped_tests=
iter=
iter_root=
timeout=3600
link_branch_workers=4
batch_size=50
force=false
dry_run=false

usage() {
    cat <<EOF
Usage: $0 --iter N [--task TASK] [--iter-root DIR] [--tests-dir DIR] [--skipped-tests PATH] [--model MODEL] [--reasoning EFFORT] [--timeout SECONDS] [--batch-size N] [--link-branch-workers N] [--dry-run] [--force]

Copies iter_N/spec/<task> -> iter_N+1/spec/<task>. Codex may polish only the
specification using iter_N+1/log/<task>/failure_attribution.json. Fixed reference
tests remain under extracted-tests and are not copied into an iteration directory.

Options:
  --iter N             Current iteration number N; writes iter_N+1 (required)
  --task TASK          Task id (default: ${default_task})
  --iter-root DIR      Iteration root (default: output/iterative)
  --tests-dir DIR      Fixed reference-test root (default: ${default_tests_dir})
  --skipped-tests PATH Run-scoped skipped-test JSON file or directory
  --model MODEL        Codex model to use (default: ${default_model})
  --reasoning EFFORT   Reasoning effort to use (default: ${default_reasoning})
  --timeout SECONDS    Codex timeout in seconds (default: ${timeout})
  --batch-size N       Maximum specification failures per Codex run (default: ${batch_size})
  --link-branch-workers N
                      Compatibility option; linking is no longer rerun
  --dry-run            Copy the spec and write its polish prompt/log without calling Codex
  --force              Overwrite iter_N+1/spec/<task> if present
  -h, --help           Show this help message
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
        --model)
            require_value "$@"
            model="$2"
            shift 2
            ;;
        --reasoning)
            require_value "$@"
            reasoning="$2"
            shift 2
            ;;
        --task)
            require_value "$@"
            task="$2"
            shift 2
            ;;
        --iter)
            require_value "$@"
            iter="$2"
            shift 2
            ;;
        --iter-root)
            require_value "$@"
            iter_root="$2"
            shift 2
            ;;
        --tests-dir)
            require_value "$@"
            tests_dir="$2"
            shift 2
            ;;
        --skipped-tests)
            require_value "$@"
            skipped_tests="$2"
            shift 2
            ;;
        --timeout)
            require_value "$@"
            timeout="$2"
            shift 2
            ;;
        --link-branch-workers)
            require_value "$@"
            link_branch_workers="$2"
            shift 2
            ;;
        --batch-size)
            require_value "$@"
            batch_size="$2"
            shift 2
            ;;
        --dry-run)
            dry_run=true
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

if [ -z "${iter}" ]; then
    echo "--iter is required" >&2
    usage >&2
    exit 1
fi

cmd=(
    uv run python -m programbench.iteration_polish
    --task "${task}"
    --iter "${iter}"
    --tests-dir "${tests_dir}"
    --link-branch-workers "${link_branch_workers}"
    --model "${model}"
    --reasoning "${reasoning}"
    --timeout "${timeout}"
    --batch-size "${batch_size}"
)
if [ -n "${iter_root}" ]; then
    cmd+=(--iter-root "${iter_root}")
fi
if [ -n "${skipped_tests}" ]; then
    cmd+=(--skipped-tests "${skipped_tests}")
fi
if [ "${dry_run}" = true ]; then
    cmd+=(--dry-run)
fi
if [ "${force}" = true ]; then
    cmd+=(--force)
fi

"${cmd[@]}"
