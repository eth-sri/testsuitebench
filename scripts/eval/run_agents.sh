#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
cd "${repo_root}"

# Each run ID selects a concrete model configuration and independently maps to
# an eval backend. Multiple run IDs may therefore use the same backend.
default_runs="codex-gpt-5.6-luna"
default_jobs=1
default_output_root=output/eval
default_mutants_dir=hf://eth-sri/tsb-mutants
default_ground_truth_dir=hf://eth-sri/tsb-reference_impl
default_reference_tests_dir=hf://eth-sri/tsb-reference_tests
default_tasks_file=

declare -A model=(
    [claude-opus-5]=opus
    [claude-fable]=fable
    [codex-gpt-5.6-sol]=gpt-5.6-sol
    [codex-gpt-5.6-luna]=gpt-5.6-luna
    [codex-gpt-6-astra]=gpt-6-astra
    [gemini-3.8-flash]=gemini-3.8-flash
    [qwen-3.8-flash]=qwen/qwen3.8-flash
    [deepseek-v4-flash-0423]=deepseek/deepseek-v4-flash
    [deepseek-v4-flash-0731]=deepseek/deepseek-v4-flash-0731
    [glm-5.3-flash]=openrouter/z-ai/glm-5.3-flash
    [muse-spark-1.3-contributor]=meta/muse-spark-1.3-contributor
    [claude-opus-5.5]=claude-opus-5-5
    [claude-sonnet-5.5]=claude-sonnet-5-5
    [codex-gpt-6-sol]=gpt-6-sol
    [codex-gpt-6-luna]=gpt-6-luna
    [codex-gpt-6.1-sol]=gpt-6.1-sol
)
declare -A backend=(
    [claude-opus-5]=claude
    [claude-fable]=claude
    [codex-gpt-5.6-sol]=codex
    [codex-gpt-5.6-luna]=codex
    [codex-gpt-6-astra]=codex
    [gemini-3.8-flash]=gemini
    [qwen-3.8-flash]=qwen
    [deepseek-v4-flash-0423]=deepseek
    [deepseek-v4-flash-0731]=deepseek
    [glm-5.3-flash]=glm
    [muse-spark-1.3-contributor]=muse
    [claude-opus-5.5]=claude
    [claude-sonnet-5.5]=claude
    [codex-gpt-6-sol]=codex
    [codex-gpt-6-luna]=codex
    [codex-gpt-6.1-sol]=codex
)

# Effort is part of each run configuration; models sharing a backend need not
# use the same value.
declare -A reasoning=(
    [claude-opus-5]=high
    [claude-fable]=high
    [codex-gpt-5.6-sol]=medium
    [codex-gpt-5.6-luna]=medium
    [codex-gpt-6-astra]=medium
    [gemini-3.8-flash]=medium
    [qwen-3.8-flash]=xhigh
    [deepseek-v4-flash-0423]=high
    [deepseek-v4-flash-0731]=high
    [glm-5.3-flash]=max
    [muse-spark-1.3-contributor]=high
    [claude-opus-5.5]=medium  # https://www.anthropic.com/claude-opus-5-5
    [claude-sonnet-5.5]=medium  # https://www.anthropic.com/claude-opus-5-5
    [codex-gpt-6-sol]=medium
    [codex-gpt-6-luna]=medium
    [codex-gpt-6.1-sol]=medium
)

runs=${default_runs}
jobs=${default_jobs}
output_root=${default_output_root}
mutants_dir=${default_mutants_dir}
ground_truth_dir=${default_ground_truth_dir}
reference_tests_dir=${default_reference_tests_dir}
tasks_file=${default_tasks_file}
tasks=()
dry_run=false
testgen_with_code=false
extra_args=()

usage() {
    cat <<EOF
Usage: $0 [OPTIONS] [-- EVAL_ARGS...]

Run every selected model configuration over the same tasks, JOBS tasks per
configuration in parallel, with all configurations running concurrently.

Options:
  --runs "RUN ..."      Model configurations to run (default: ${default_runs})
  --agents "RUN ..."    Deprecated alias for --runs
  --task TASK           Task instance ID (repeatable)
  --tasks-file FILE     File with one task instance ID per line
  --jobs N              Parallel tasks per configuration (default: ${default_jobs})
  --output-root DIR     Root for codegen/, testgen/, timings/ and logs/ (default: ${default_output_root})
  --mutants-dir DIR     Mutant store, local or hf://REPO_ID[@REVISION] (default: ${default_mutants_dir})
  --ground-truth-dir DIR
                        Ground-truth executables, local or hf://REPO_ID[@REVISION]
                        (default: ${default_ground_truth_dir})
  --reference-tests-dir DIR
                        Reference tests, local or hf://REPO_ID[@REVISION]
                        (default: ${default_reference_tests_dir})
  --backend RUN=BACKEND Set the eval backend for a run (repeatable)
  --model RUN=MODEL     Override a run's model (repeatable)
  --reasoning RUN=R     Override a run's reasoning effort (repeatable)
  --testgen-with-code   Run only test generation with the reference executable
  --dry-run             Print the commands instead of running them
  -h, --help            Show this help message

Everything after -- is passed to every eval script, e.g. -- --classify-errors --regenerate
EOF
}

require_value() {
    if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        usage >&2
        exit 2
    fi
}

# Overrides take RUN=VALUE. A bare value would silently create an unused entry
# and leave the run on its default, so reject it.
require_run_override() {
    local flag=$1 spec=${2-}
    if [[ "${spec}" != *=* || -z "${spec%%=*}" || -z "${spec#*=}" ]]; then
        echo "${flag} expects RUN=VALUE (e.g. ${flag} codex-gpt-5.6-sol=low), got: ${spec:-<missing>}" >&2
        usage >&2
        exit 2
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --runs|--agents) require_value "$@"; runs=$2; shift 2 ;;
        --task) require_value "$@"; tasks+=("$2"); shift 2 ;;
        --tasks-file) require_value "$@"; tasks_file=$2; shift 2 ;;
        --jobs) require_value "$@"; jobs=$2; shift 2 ;;
        --output-root) require_value "$@"; output_root=$2; shift 2 ;;
        --mutants-dir) require_value "$@"; mutants_dir=$2; shift 2 ;;
        --ground-truth-dir) require_value "$@"; ground_truth_dir=$2; shift 2 ;;
        --reference-tests-dir) require_value "$@"; reference_tests_dir=$2; shift 2 ;;
        --backend) require_value "$@"; require_run_override --backend "$2"; backend[${2%%=*}]=${2#*=}; shift 2 ;;
        --model) require_value "$@"; require_run_override --model "$2"; model[${2%%=*}]=${2#*=}; shift 2 ;;
        --reasoning) require_value "$@"; require_run_override --reasoning "$2"; reasoning[${2%%=*}]=${2#*=}; shift 2 ;;
        --testgen-with-code) testgen_with_code=true; shift ;;
        --dry-run) dry_run=true; shift ;;
        --) shift; extra_args=("$@"); break ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ "${testgen_with_code}" = true ]; then
    for arg in "${extra_args[@]}"; do
        if [ "${arg}" = --part ]; then
            echo "--part cannot override --testgen-with-code" >&2
            exit 2
        fi
    done
fi

if [ -n "${tasks_file}" ]; then
    mapfile -t -O "${#tasks[@]}" tasks < <(grep -v '^\s*\(#\|$\)' "${tasks_file}")
fi
if [ "${#tasks[@]}" -eq 0 ]; then
    echo "No tasks given; use --task or --tasks-file" >&2
    exit 2
fi
for run_id in ${runs}; do
    if [ -z "${backend[$run_id]+x}" ] || [ -z "${model[$run_id]+x}" ] || [ -z "${reasoning[$run_id]+x}" ]; then
        echo "Incomplete run configuration: ${run_id}; set --backend, --model, and --reasoning" >&2
        exit 2
    fi
    agent=${backend[$run_id]}
    if [ ! -f "scripts/eval/${agent}_eval.sh" ]; then
        echo "Unknown backend for ${run_id}: ${agent}" >&2
        exit 2
    fi
done

# TASK_WORD is spliced in verbatim after quoting, so the caller passes either
# a %q-quoted task ID or the literal "$1" for xargs.
run_command() {
    local run_id=$1 task_word=$2
    local agent=${backend[$run_id]}
    local label="${model[$run_id]//\//-}_${reasoning[$run_id]}"
    local part=all
    local test_input_args=()
    if [ "${testgen_with_code}" = true ]; then
        label+="_with_code"
        part=test_gen
        test_input_args+=(--test-with-executable)
    fi
    local cmd=(
        /usr/bin/time --output "${output_root}/timings/${label}/__TASK__.seconds" --format %e
        bash "scripts/eval/${agent}_eval.sh"
        --part "${part}" --task __TASK__ "${test_input_args[@]}"
        "--${agent}-model" "${model[$run_id]}"
        "--${agent}-reasoning" "${reasoning[$run_id]}"
        --spec-dir ground_truth/spec
        --mutants-dir "${mutants_dir}"
        --ground-truth-dir "${ground_truth_dir}"
        --reference-tests-dir "${reference_tests_dir}"
        --skipped-tests ground_truth/skipped-tests
        --skipped-mutants ground_truth/skipped-mutants
        --executable-dir "${output_root}/codegen/${label}"
        --generated-tests-dir "${output_root}/testgen/${label}"
        --branch-workers 8 --branch-cpus 2 --docker-cpus 2 --cpu-budget 16
        --workers 1
    )
    case "${run_id}" in
        deepseek-v4-flash-0423|deepseek-v4-flash-0731)
            cmd+=(--log-dir "${output_root}/logs/${run_id}")
            ;;
    esac
    cmd+=("${extra_args[@]}")
    local rendered
    rendered=$(printf '%q ' "${cmd[@]}")
    printf '%s\n' "${rendered//__TASK__/${task_word}}"
}

run_configuration() {
    local run_id=$1
    local run_word command
    printf -v run_word '%q' "${run_id}"
    command=$(run_command "${run_id}" '"$1"')
    printf '%s\n' "${tasks[@]}" | xargs -P "${jobs}" -n 1 bash -c \
        "printf 'Task %s [%s] PID: %d\\n' ${run_word} \"\$1\" \"\$\$\"; exec ${command}" _
}

if [ "${dry_run}" = true ]; then
    for run_id in ${runs}; do
        for task in "${tasks[@]}"; do run_command "${run_id}" "$(printf '%q' "${task}")"; done
    done
    exit 0
fi

# Every container started by this batch carries its unique cleanup scope.
export PROGRAMBENCH_RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
cleanup_batch() {
    local exit_status=$?
    trap - EXIT
    trap '' INT TERM
    if ! python3 "${repo_root}/scripts/docker/cleanup_containers.py" \
        --run-id "${PROGRAMBENCH_RUN_ID}" --parent-pid "$$"; then
        echo "Batch container cleanup failed: ${PROGRAMBENCH_RUN_ID}" >&2
        if [ "${exit_status}" -eq 0 ]; then exit_status=1; fi
    fi
    exit "${exit_status}"
}
trap cleanup_batch EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
printf 'Container cleanup run ID: %s\n' "${PROGRAMBENCH_RUN_ID}"

printf 'Batch PID: %d (kill -TERM %d to stop the whole run)\n' "$$" "$$"

# The default agent network is an internal Docker network whose proxy only
# permits model-provider API hosts. Provision and validate it before launching
# the matrix. Custom networks/proxies remain subject to each agent's fail-closed
# network preflight.
if [ "${PROGRAMBENCH_EGRESS_NETWORK:-pb-egress}" = pb-egress ] \
    && [ "${PROGRAMBENCH_EGRESS_PROXY:-http://pb-proxy:3128}" = http://pb-proxy:3128 ]; then
    bash "${script_dir}/../docker/setup_egress_network.sh"
fi

mkdir -p "${output_root}"
printf 'Running %s tasks x [%s], %s jobs per configuration, outputs under %s/\n' \
    "${#tasks[@]}" "${runs}" "${jobs}" "${output_root}"

declare -A pids=()
for run_id in ${runs}; do
    label="${model[$run_id]//\//-}_${reasoning[$run_id]}"
    if [ "${testgen_with_code}" = true ]; then label+="_with_code"; fi
    mkdir -p "${output_root}/timings/${label}"
    run_configuration "${run_id}" &
    pids[$run_id]=$!
done

status=0
for run_id in ${runs}; do
    if wait "${pids[$run_id]}"; then
        echo "${run_id}: all tasks finished"
    else
        echo "${run_id}: at least one task failed; see ${output_root}/logs/" >&2
        status=1
    fi
done
exit "${status}"
