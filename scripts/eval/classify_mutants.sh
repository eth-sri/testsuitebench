#!/usr/bin/env bash
set -euo pipefail

default_model=codex/gpt-5.6-luna
default_reasoning=high
default_task=abishekvashok__cmatrix.5c082c6

model=${default_model}
reasoning=${default_reasoning}
task=${default_task}
source=
spec_dir=
tests_dir=
mutants_dir=
ground_truth_dir=
output=
limit=0
batch_size=50
batch_workers=4
force=false
dry_run=false
skip_test_failures=false
skip_survived_mutants=false

usage() {
    cat <<EOF
Usage: $0 SOURCE --spec-dir DIR --tests-dir DIR --mutants-dir DIR [--ground-truth-dir DIR] [--model MODEL] [--reasoning EFFORT] [--task TASK] [--output PATH] [--limit N] [--batch-size N] [--batch-workers N] [--skip-test-failures] [--skip-survived-mutants] [--dry-run] [--force]

Options:
  SOURCE              Test-eval JSON file or mutation-eval output directory
  --model MODEL       Codex model to use (default: ${default_model})
  --reasoning EFFORT  Reasoning effort to use (default: ${default_reasoning})
  --task TASK         Task filter to use (default: ${default_task})
  --spec-dir DIR      Specification directory
  --tests-dir DIR     Generated test suite directory
  --mutants-dir DIR   Mutants directory
  --ground-truth-dir DIR
                      Ground-truth implementation directory, or hf://REPO_ID[@REVISION].
                      Sealed mutant sources are an overlay on this tree; defaults to the
                      path recorded when the store was sealed.
  --output PATH       Attribution report path
  --limit N           Classify at most N generated-test failures and mutants; 0 means all (default: 0)
  --batch-size N      Classify cases in batches of this size; 0 means all at once (default: 50)
  --batch-workers N   Classify case batches with this many parallel Codex instances (default: 4)
  --skip-test-failures
                      Do not classify generated-test failures (the validity rate direction)
  --skip-survived-mutants
                      Do not classify survived mutants (the mutation score direction)
  --dry-run           Write prompts without calling Codex
  --force             Re-classify even if output exists
  -h, --help          Show this help message
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
        --spec-dir|--spec_dir)
            require_value "$@"
            spec_dir="$2"
            shift 2
            ;;
        --tests-dir|--tests_dir)
            require_value "$@"
            tests_dir="$2"
            shift 2
            ;;
        --mutants-dir|--mutants_dir)
            require_value "$@"
            mutants_dir="$2"
            shift 2
            ;;
        --ground-truth-dir|--ground_truth_dir)
            require_value "$@"
            ground_truth_dir="$2"
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
        --batch-workers|--batch_workers)
            require_value "$@"
            batch_workers="$2"
            shift 2
            ;;
        --skip-test-failures)
            skip_test_failures=true
            shift
            ;;
        --skip-survived-mutants)
            skip_survived_mutants=true
            shift
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
        --*)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
        *)
            if [ -n "${source}" ]; then
                echo "Unexpected argument: $1" >&2
                usage >&2
                exit 1
            fi
            source="$1"
            shift
            ;;
    esac
done

if [ -z "${source}" ] || [ -z "${spec_dir}" ] || [ -z "${tests_dir}" ] || [ -z "${mutants_dir}" ]; then
    echo "SOURCE, --spec-dir, --tests-dir, and --mutants-dir are required" >&2
    usage >&2
    exit 1
fi

cmd=(
    uv run python -m programbench.mutant_attribution
    "${source}"
    --task "${task}"
    --model "${model}"
    --reasoning-effort "${reasoning}"
    --spec-dir "${spec_dir}"
    --tests-dir "${tests_dir}"
    --mutants-dir "${mutants_dir}"
    --limit "${limit}"
    --batch-size "${batch_size}"
    --batch-workers "${batch_workers}"
)
if [ -n "${ground_truth_dir}" ]; then
    cmd+=(--ground-truth-dir "${ground_truth_dir}")
fi
if [ -n "${output}" ]; then
    cmd+=(--output "${output}")
fi
if [ "${skip_test_failures}" = true ]; then
    cmd+=(--skip-test-failures)
fi
if [ "${skip_survived_mutants}" = true ]; then
    cmd+=(--skip-survived-mutants)
fi
if [ "${dry_run}" = true ]; then
    cmd+=(--dry-run)
fi
if [ "${force}" = true ]; then
    cmd+=(--force)
fi

"${cmd[@]}"
