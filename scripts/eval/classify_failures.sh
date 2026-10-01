#!/usr/bin/env bash
set -euo pipefail

default_model=codex/gpt-5.6-luna
default_reasoning=high
default_task=abishekvashok__cmatrix.5c082c6
default_iter=0

model=${default_model}
reasoning=${default_reasoning}
task=${default_task}
iter=${default_iter}
iter_dir=
eval_json=
spec_dir=
test_spec_links=
reference_tests_dir=
output=
limit=0
batch_size=200
branch_workers=4
force=false
dry_run=false

usage() {
    cat <<EOF
Usage: $0 [--model MODEL] [--reasoning EFFORT] [--task TASK] [--iter N] [--iter-dir DIR] [--eval-json PATH] [--spec-dir DIR] [--test-spec-links PATH] [--reference-tests-dir DIR] [--output PATH] [--limit N] [--batch-size N] [--branch-workers N] [--dry-run] [--force]

Options:
  --model MODEL        Codex model to use (default: ${default_model})
  --reasoning EFFORT   Reasoning effort to use (default: ${default_reasoning})
  --task TASK          Task filter to use (default: ${default_task})
  --iter N             Iteration number when --iter-dir is omitted (default: ${default_iter})
  --iter-dir DIR       Iteration directory (default: output/iterative/iter_<N>)
  --eval-json PATH     Eval JSON to classify instead of inferring from --iter-dir
  --spec-dir DIR       Specification directory (inferred for iterative directories)
  --test-spec-links PATH
                       test_spec_links.json used to annotate relevant spec sections
  --reference-tests-dir DIR
                       Fixed reference-test root; <DIR>/<task> is staged read-only for the classifier
  --output PATH        Attribution report path (default: <iter-dir>/log/<task>/failure_attribution.json)
  --limit N            Classify at most N failures; 0 means all (default: 0)
  --batch-size N       Maximum failures per branch classifier job (default: 200)
  --branch-workers N   Classify test branches with this many parallel Codex instances (default: 4)
  --dry-run            Write prompts without calling Codex
  --force              Re-classify even if output exists
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
        --iter-dir)
            require_value "$@"
            iter_dir="$2"
            shift 2
            ;;
        --eval-json|--eval_json)
            require_value "$@"
            eval_json="$2"
            shift 2
            ;;
        --spec-dir|--spec_dir)
            require_value "$@"
            spec_dir="$2"
            shift 2
            ;;
        --test-spec-links|--test_spec_links)
            require_value "$@"
            test_spec_links="$2"
            shift 2
            ;;
        --reference-tests-dir|--reference_tests_dir)
            require_value "$@"
            reference_tests_dir="$2"
            shift 2
            ;;
        --output|-o)
            require_value "$@"
            output="$2"
            shift 2
            ;;
        --limit)
            require_value "$@"
            limit="$2"
            shift 2
            ;;
        --batch-size|--batch_size)
            require_value "$@"
            batch_size="$2"
            shift 2
            ;;
        --branch-workers|--branch_workers)
            require_value "$@"
            branch_workers="$2"
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

if [ -z "${iter_dir}" ]; then
    iter_dir="output/iterative/iter_${iter}"
fi

source_arg="${iter_dir}"
if [ -n "${eval_json}" ]; then
    source_arg="${eval_json}"
fi

cmd=(
    uv run python -m programbench.failure_attribution
    "${source_arg}"
    --task "${task}"
    --model "${model}"
    --reasoning-effort "${reasoning}"
    --limit "${limit}"
    --batch-size "${batch_size}"
    --branch-workers "${branch_workers}"
)
if [ -n "${spec_dir}" ]; then
    cmd+=(--spec-dir "${spec_dir}")
fi
if [ -n "${test_spec_links}" ]; then
    cmd+=(--test-spec-links "${test_spec_links}")
fi
if [ -n "${reference_tests_dir}" ]; then
    cmd+=(--reference-tests-dir "${reference_tests_dir}")
fi
if [ -n "${output}" ]; then
    cmd+=(--output "${output}")
fi
if [ "${dry_run}" = true ]; then
    cmd+=(--dry-run)
fi
if [ "${force}" = true ]; then
    cmd+=(--force)
fi

"${cmd[@]}"
