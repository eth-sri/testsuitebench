#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
cd "${repo_root}"

default_task=abishekvashok__cmatrix.5c082c6
default_version=26
default_iter=5
default_part=all
default_codex_model=codex/gpt-5.6-sol
default_codex_reasoning=high
default_classifier_model=codex/gpt-5.6-sol
default_classifier_reasoning=xhigh
default_workers=1
default_branch_workers=16
default_classify_branch_workers=8
default_batch_size=50
default_batch_workers=4
default_classifier_cpus=2
default_docker_cpus=
default_branch_cpus=
default_cpu_budget=
default_solve_timeout=21600
default_test_timeout=21600

task=${default_task}
version=${default_version}
iter=${default_iter}
part=${default_part}
codex_model=${default_codex_model}
codex_reasoning=${default_codex_reasoning}
classifier_model=${default_classifier_model}
classifier_reasoning=${default_classifier_reasoning}
workers=${default_workers}
branch_workers=${default_branch_workers}
classify_branch_workers=${default_classify_branch_workers}
batch_size=${default_batch_size}
batch_workers=${default_batch_workers}
classifier_cpus=${default_classifier_cpus}
docker_cpus=${default_docker_cpus}
branch_cpus=${default_branch_cpus}
cpu_budget=${default_cpu_budget}
solve_timeout=${default_solve_timeout}
test_timeout=${default_test_timeout}

iter_root=
spec_dir=
mutants_dir=
executable_dir=
generated_tests_dir=
eval_root=
reference_tests_dir=extracted-tests
ground_truth_dir=ground_truth/executable
skipped_tests=
skipped_mutants=
log_dir=
log_to_stdout=false
test_spec_links=
classify=false
force=false
regenerate=false
test_with_executable=false

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Generate and evaluate a Codex implementation, a Codex-generated test suite,
or both against one iteration of an improved ProgramBench specification.
Codex skips error classification unless --classify-errors is supplied.

Mirrors scripts/eval/claude_eval.sh; only the generating agent differs.

Selection:
  --part PART                   all, exec_gen, or test_gen (default: ${default_part})
  --task TASK                  Task instance ID (default: ${default_task})
  --version N                  Iterative-run version used by default paths (default: ${default_version})
  --iter N                     Improved-spec iteration (default: ${default_iter})
  --iter-root DIR              Iteration root (default: output/debug_iterative_v<VERSION>)

Models:
  --codex-model MODEL          Codex model or alias (default: ${default_codex_model})
  --codex-reasoning EFFORT     Codex reasoning effort (default: ${default_codex_reasoning})
  --classifier-model MODEL     Codex classifier model (default: ${default_classifier_model})
  --classifier-reasoning LEVEL Codex classifier effort (default: ${default_classifier_reasoning})

Phases:
  --classify-errors            Run Codex classification of generated-test failures and survived mutants
                               (default: off); --classify is an alias
  --no-classify                Skip Codex classification (default)
  --force                      Re-evaluate/reclassify existing outputs
  --no-force                   Reuse existing evaluation/classification outputs (default)
  --regenerate                 Rerun the agent phases even if a completed trajectory
                               exists (implies --force)
  --test-with-executable        Give test generation the reference executable alongside the spec

Paths:
  --spec-dir DIR               Specification root; contains <TASK>/
  --mutants-dir DIR            Mutant root; contains <TASK>/
  --executable-dir DIR         Codex implementation output root
  --generated-tests-dir DIR    Codex-generated test-suite output root
  --eval-root DIR              Separate test-evaluation output root
                               (default: write results into --generated-tests-dir)
  --reference-tests-dir DIR    Fixed reference tests, local or hf://REPO_ID[@REVISION]
                               (default: extracted-tests)
  --ground-truth-dir DIR       Ground-truth executables (default: ground_truth/executable)
  --skipped-tests PATH         Skipped-test JSON file or directory of <TASK>.json
  --skipped-mutants PATH       Skipped-mutant JSON file or directory of <TASK>.json
  --log-dir DIR                Log directory (default: alongside --executable-dir,
                               e.g. .../codegen/NAME -> .../logs/NAME)
  --stdout                     Log to the terminal instead of a log file
  --test-spec-links PATH       Reference-test/spec links JSON for exec classification

Execution:
  --workers N                  Evaluation instance workers (default: ${default_workers})
  --branch-workers N           Evaluation branch/mutant workers (default: ${default_branch_workers})
  --classify-branch-workers N  Exec classifier workers (default: ${default_classify_branch_workers})
  --batch-size N               Mutant-classification batch size (default: ${default_batch_size})
  --batch-workers N            Mutant-classification workers (default: ${default_batch_workers})
  --classifier-cpus N          CPU limit per classifier (default: ${default_classifier_cpus})
  --docker-cpus N              Evaluation CPUs per container (default: CLI default)
  --branch-cpus N              Force CPUs per test branch in 'programbench eval'
  --cpu-budget N               Total evaluation CPU budget per task (default: unlimited)
  --solve-timeout SECONDS      Codex implementation timeout (default: ${default_solve_timeout})
  --test-timeout SECONDS       Codex test-generation timeout (default: ${default_test_timeout})
  -h, --help                   Show this help message

Examples:
  $0 --part exec_gen --version 26 --iter 5 --force
  $0 --part test_gen --codex-model codex/gpt-5.5 --no-classify
EOF
}

require_value() {
    if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        usage >&2
        exit 2
    fi
}

require_non_negative_int() {
    if ! [[ "$2" =~ ^[0-9]+$ ]]; then
        echo "$1 must be a non-negative integer, got: $2" >&2
        exit 2
    fi
}

require_positive_int() {
    require_non_negative_int "$1" "$2"
    if [ "$2" -eq 0 ]; then
        echo "$1 must be greater than zero" >&2
        exit 2
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --part) require_value "$@"; part=$2; shift 2 ;;
        --task) require_value "$@"; task=$2; shift 2 ;;
        --version) require_value "$@"; version=$2; shift 2 ;;
        --iter) require_value "$@"; iter=$2; shift 2 ;;
        --iter-root) require_value "$@"; iter_root=$2; shift 2 ;;
        --codex-model) require_value "$@"; codex_model=$2; shift 2 ;;
        --codex-reasoning|--codex-effort) require_value "$@"; codex_reasoning=$2; shift 2 ;;
        --classifier-model) require_value "$@"; classifier_model=$2; shift 2 ;;
        --classifier-reasoning) require_value "$@"; classifier_reasoning=$2; shift 2 ;;
        --classify-errors|--classify) classify=true; shift ;;
        --no-classify) classify=false; shift ;;
        --force) force=true; shift ;;
        --no-force) force=false; shift ;;
        --regenerate) regenerate=true; force=true; shift ;;
        --test-with-executable) test_with_executable=true; shift ;;
        --spec-dir) require_value "$@"; spec_dir=$2; shift 2 ;;
        --mutants-dir) require_value "$@"; mutants_dir=$2; shift 2 ;;
        --executable-dir) require_value "$@"; executable_dir=$2; shift 2 ;;
        --generated-tests-dir) require_value "$@"; generated_tests_dir=$2; shift 2 ;;
        --eval-root) require_value "$@"; eval_root=$2; shift 2 ;;
        --reference-tests-dir|--tests-dir) require_value "$@"; reference_tests_dir=$2; shift 2 ;;
        --ground-truth-dir) require_value "$@"; ground_truth_dir=$2; shift 2 ;;
        --test-spec-links) require_value "$@"; test_spec_links=$2; shift 2 ;;
        --workers) require_value "$@"; workers=$2; shift 2 ;;
        --branch-workers) require_value "$@"; branch_workers=$2; shift 2 ;;
        --classify-branch-workers) require_value "$@"; classify_branch_workers=$2; shift 2 ;;
        --batch-size) require_value "$@"; batch_size=$2; shift 2 ;;
        --batch-workers) require_value "$@"; batch_workers=$2; shift 2 ;;
        --classifier-cpus) require_value "$@"; classifier_cpus=$2; shift 2 ;;
        --docker-cpus) require_value "$@"; docker_cpus=$2; shift 2 ;;
        --branch-cpus) require_value "$@"; branch_cpus=$2; shift 2 ;;
        --cpu-budget) require_value "$@"; cpu_budget=$2; shift 2 ;;
        --skipped-tests) require_value "$@"; skipped_tests=$2; shift 2 ;;
        --skipped-mutants) require_value "$@"; skipped_mutants=$2; shift 2 ;;
        --log-dir) require_value "$@"; log_dir=$2; shift 2 ;;
        --stdout) log_to_stdout=true; shift ;;
        --solve-timeout) require_value "$@"; solve_timeout=$2; shift 2 ;;
        --test-timeout) require_value "$@"; test_timeout=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

case "${part}" in
    all|exec_gen|test_gen) ;;
    *) echo "--part must be all, exec_gen, or test_gen; got: ${part}" >&2; exit 2 ;;
esac

require_non_negative_int --version "${version}"
require_non_negative_int --iter "${iter}"
require_positive_int --workers "${workers}"
require_positive_int --branch-workers "${branch_workers}"
require_positive_int --classify-branch-workers "${classify_branch_workers}"
require_non_negative_int --batch-size "${batch_size}"
require_positive_int --batch-workers "${batch_workers}"
require_positive_int --classifier-cpus "${classifier_cpus}"
if [ -n "${docker_cpus}" ]; then require_positive_int --docker-cpus "${docker_cpus}"; fi
if [ -n "${branch_cpus}" ]; then require_positive_int --branch-cpus "${branch_cpus}"; fi
if [ -n "${cpu_budget}" ]; then require_non_negative_int --cpu-budget "${cpu_budget}"; fi
require_positive_int --solve-timeout "${solve_timeout}"
require_positive_int --test-timeout "${test_timeout}"

if [ -z "${iter_root}" ]; then iter_root="output/debug_iterative_v${version}"; fi
if [ -z "${spec_dir}" ]; then spec_dir="${iter_root}/iter_${iter}/spec"; fi
if [ -z "${mutants_dir}" ]; then mutants_dir="${iter_root}/mutants"; fi
if [ -z "${test_spec_links}" ]; then
    test_spec_links="${iter_root}/iter_${iter}/test-spec-links/${task}/test_spec_links.json"
fi

codex_model_name=${codex_model#codex/}
codex_model_arg=${codex_model}
if [[ "${codex_model_arg}" != */* ]]; then codex_model_arg="codex/${codex_model_arg}"; fi
run_label="codex-${codex_model_name//\//-}-v${version}-iter${iter}"
if [ -z "${executable_dir}" ]; then executable_dir="output/executable/${run_label}"; fi
if [ -z "${generated_tests_dir}" ]; then generated_tests_dir="output/generated-test/${run_label}"; fi

# Zero-based attempt suffix, matching run_iterative_all.sh: a rerun never
# overwrites an earlier log, and the highest number is always the latest.
next_task_log() {
    local candidate suffix next_index=0
    if [ -e "${log_dir}/${task}.log" ]; then next_index=1; fi
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

started_at=$(date +%s)
if [ "${log_to_stdout}" = false ]; then
    if [ -z "${log_dir}" ]; then
        log_dir="$(dirname "$(dirname "${executable_dir}")")/logs/$(basename "${executable_dir}")"
    fi
    mkdir -p "${log_dir}"
    log_file=$(next_task_log)
    exec 3>&1
    printf '[start] %s (%s)\n' "${task}" "${log_file}" >&3
    exec >>"${log_file}" 2>&1
else
    printf 'Started %s\n' "$(date -Is)"
fi

finish() {
    local status=$?
    local elapsed=$(( $(date +%s) - started_at ))
    local hours=$((elapsed / 3600))
    local minutes=$(((elapsed % 3600) / 60))
    if [ "${log_to_stdout}" = false ]; then
        local outcome=ok
        if [ "${status}" -ne 0 ]; then outcome=failed; fi
        printf '[%s] %s (%s, %dh%dm)\n' "${outcome}" "${task}" "${log_file}" "${hours}" "${minutes}" >&3
    else
        printf 'Finished %s (total %ds)\n' "$(date -Is)" "${elapsed}"
    fi
}
trap finish EXIT

if [ ! -d "${spec_dir}/${task}" ]; then
    echo "Specification input is missing: ${spec_dir}/${task}" >&2
    exit 1
fi
if { [ "${part}" = all ] || [ "${part}" = test_gen ]; } \
    && [[ "${mutants_dir}" != hf://* ]] && [ ! -d "${mutants_dir}/${task}" ]; then
    echo "Mutant input is missing: ${mutants_dir}/${task}" >&2
    exit 1
fi
if [[ "${reference_tests_dir}" == hf://* ]]; then
    reference_tests_dir="$(uv run python -c 'import sys; from programbench.utils.reference_test_store import resolve_reference_tests_dir; print(resolve_reference_tests_dir(*sys.argv[1:]))' \
        "${reference_tests_dir}" "${task}")"
fi
if [ ! -d "${reference_tests_dir}/${task}" ]; then
    echo "Reference-test input is missing: ${reference_tests_dir}/${task}" >&2
    exit 1
fi
ground_truth_executable="${ground_truth_dir}/${task}/executable"
if [[ "${ground_truth_dir}" == hf://* ]] && { [ "${part}" = all ] || [ "${part}" = test_gen ]; }; then
    ground_truth_executable="$(uv run python -c 'import sys; from programbench.utils.ground_truth_store import resolve_ground_truth_dir; print(resolve_ground_truth_dir(*sys.argv[1:]))' \
        "${ground_truth_dir}" "${task}")/${task}/executable"
fi
if { [ "${part}" = all ] || [ "${part}" = test_gen ]; } \
    && [ ! -f "${ground_truth_executable}" ]; then
    echo "Ground-truth executable is missing: ${ground_truth_executable}" >&2
    exit 1
fi

force_args=()
if [ "${force}" = true ]; then force_args+=(--force); fi

cpu_args=()
if [ -n "${docker_cpus}" ]; then cpu_args+=(--docker-cpus "${docker_cpus}"); fi
if [ -n "${cpu_budget}" ]; then cpu_args+=(--cpu-budget "${cpu_budget}"); fi
generation_cpu_args=()
if [ -n "${docker_cpus}" ]; then generation_cpu_args+=(--docker-cpus "${docker_cpus}"); fi

run() {
    printf '+ [%s]' "$(date +%H:%M:%S)"
    printf ' %q' "$@"
    printf '\n'
    "$@"
}

# claude_step_complete.py is agent-agnostic despite its name: it checks
# info.exit_status and info.returncode, which Codex trajectories also carry.
run_exec_generation() {
    local instance_dir="${executable_dir}/${task}"
    if [ "${regenerate}" = false ] && python3 scripts/eval/claude_step_complete.py \
        --trajectory "${instance_dir}/traj.json" \
        --artifact "${instance_dir}/submission.tar.gz"; then
        echo "Skipping completed Codex implementation generation: ${task}"
    else
        local t0=$(date +%s)
        run bash scripts/agents/solve_codex.sh \
            --task "${task}" --mode spec-only --cleanroom "${spec_dir}" \
            --output "${executable_dir}" --model "${codex_model_arg}" \
            --reasoning "${codex_reasoning}" --timeout "${solve_timeout}" "${generation_cpu_args[@]}"
        printf 'Implementation generation took %ds\n' "$(( $(date +%s) - t0 ))"
    fi

    local eval_args=(
        uv run programbench eval "${executable_dir}"
        --tests-dir "${reference_tests_dir}" --filter "${task}"
        --workers "${workers}" --branch-workers "${branch_workers}"
    )
    eval_args+=("${cpu_args[@]}")
    if [ -n "${branch_cpus}" ]; then eval_args+=(--branch-cpus "${branch_cpus}"); fi
    if [ -n "${skipped_tests}" ]; then eval_args+=(--skipped-tests "${skipped_tests}"); fi
    eval_args+=("${force_args[@]}")
    run "${eval_args[@]}"

    if [ "${classify}" = false ]; then return; fi

    local eval_json="${executable_dir}/${task}/${task}.eval.json"
    if [ ! -f "${eval_json}" ]; then
        echo "Implementation evaluation result is missing: ${eval_json}" >&2
        exit 1
    fi

    local classify_args=(
        bash scripts/eval/classify_failures.sh
        --eval-json "${eval_json}"
        --task "${task}"
        --model "${classifier_model}"
        --reasoning "${classifier_reasoning}"
        --spec-dir "${spec_dir}"
        --output "${executable_dir}/${task}/failure_attribution.json"
        --branch-workers "${classify_branch_workers}"
    )
    if [ -f "${test_spec_links}" ]; then
        classify_args+=(--test-spec-links "${test_spec_links}")
    else
        echo "Warning: test/spec links not found; classifying without them: ${test_spec_links}" >&2
    fi
    classify_args+=("${force_args[@]}")
    run env PROGRAMBENCH_DOCKER_CPUS="${classifier_cpus}" "${classify_args[@]}"
}

run_test_generation() {
    local test_input_args=()
    if [ "${test_with_executable}" = true ]; then
        local reference="${ground_truth_executable}"
        if [ ! -f "$reference" ]; then
            echo "Reference executable is missing: $reference" >&2
            return 1
        fi
        if [ "$(od -An -tx1 -N4 "$reference" | tr -d ' \n')" = "7f454c46" ]; then
            test_input_args+=(--reference-executable "$reference")
        else
            echo "Reference is not ELF for ${task}; generating tests from the spec only." >&2
        fi
    fi
    local instance_dir="${generated_tests_dir}/${task}"
    if [ "${regenerate}" = false ] && python3 scripts/eval/claude_step_complete.py \
        --trajectory "${instance_dir}/${task}.traj.json" \
        --artifact "${instance_dir}/tests.tar.gz"; then
        echo "Skipping completed Codex test generation: ${task}"
    else
        local t0=$(date +%s)
        run bash scripts/agents/generate_tests_codex.sh \
            --task "${task}" --cleanroom "${spec_dir}" "${test_input_args[@]}" \
            --output "${generated_tests_dir}" --model "${codex_model_name}" \
            --reasoning "${codex_reasoning}" --timeout "${test_timeout}" "${generation_cpu_args[@]}"
        printf 'Test generation took %ds\n' "$(( $(date +%s) - t0 ))"
    fi

    local eval_args=(
        uv run programbench eval-tests "${generated_tests_dir}"
        --mutants-dir "${mutants_dir}"
        --ground-truth-dir "${ground_truth_dir}"
        --reference-tests-dir "${reference_tests_dir}" --filter "${task}"
        --detailed-logs --reference-trials 3 --workers "${workers}" --branch-workers "${branch_workers}"
    )
    eval_args+=("${cpu_args[@]}")
    if [ -n "${skipped_tests}" ]; then eval_args+=(--skipped-tests "${skipped_tests}"); fi
    if [ -n "${skipped_mutants}" ]; then eval_args+=(--skipped-mutants "${skipped_mutants}"); fi
    if [ -n "${eval_root}" ]; then
        eval_args+=(--output "${eval_root}")
    fi
    eval_args+=("${force_args[@]}")
    run "${eval_args[@]}"

    if [ "${classify}" = false ]; then return; fi

    local result_dir="${generated_tests_dir}/${task}"
    if [ -n "${eval_root}" ]; then
        local suite_name
        suite_name=$(basename "${generated_tests_dir}")
        result_dir="${eval_root}/${suite_name}/${task}"
    fi
    local eval_json="${result_dir}/${task}.test_eval.json"
    if [ ! -f "${eval_json}" ]; then
        echo "Generated-test evaluation result is missing: ${eval_json}" >&2
        exit 1
    fi

    # A HuggingFace ground truth also carries the implementation sealed mutants overlay.
    local implementation_args=()
    if [[ "${ground_truth_dir}" == hf://* ]]; then implementation_args+=(--ground-truth-dir "${ground_truth_dir}"); fi
    run env PROGRAMBENCH_DOCKER_CPUS="${classifier_cpus}" \
        bash scripts/eval/classify_mutants.sh "${eval_json}" \
        --task "${task}" --model "${classifier_model}" \
        --reasoning "${classifier_reasoning}" --spec-dir "${spec_dir}" \
        --tests-dir "${generated_tests_dir}" --mutants-dir "${mutants_dir}" \
        --output "${result_dir}/mutant_attribution.json" \
        --batch-size "${batch_size}" --batch-workers "${batch_workers}" \
        "${implementation_args[@]}" "${force_args[@]}"
}

# Neither image is usable straight from a registry: :task_patched is built here
# and never published, and :task_cleanroom only ever gets resolved as a buildkit
# FROM, which leaves no local tag for the offline build check to docker run.
ensure_images() {
    local base_image="programbench/${task/__/_1776_}:${PROGRAMBENCH_TASK_PATCHED_BASE_TAG:-task_cleanroom}"
    docker image inspect "${base_image}" >/dev/null 2>&1 || run docker pull "${base_image}"
    run bash scripts/docker/install_task_patched.sh --task "${task}"
}

printf 'Codex evaluation: task=%s part=%s spec=%s force=%s regenerate=%s classify=%s\n' \
    "${task}" "${part}" "${spec_dir}" "${force}" "${regenerate}" "${classify}"

ensure_images

case "${part}" in
    all) run_exec_generation; run_test_generation ;;
    exec_gen) run_exec_generation ;;
    test_gen) run_test_generation ;;
esac
