#!/usr/bin/env bash
set -euo pipefail

default_model=codex/gpt-5.6-luna
default_reasoning=high
default_task=abishekvashok__cmatrix.5c082c6
default_repo_dir=extracted-tests

model=${default_model}
reasoning=${default_reasoning}
task=${default_task}
output_dir=
repo_dir=${default_repo_dir}
spec_in=
test_spec_links=
cleanroom_base_image=
ground_truth_implementation_dir=ground_truth/implementation
docker_cpus=16
mutant_build_jobs=8
target_tests_per_spec=6
final_mutants_per_spec=2
timeout=14400
codex_command="codex exec --cd /workspace --skip-git-repo-check"

usage() {
    cat <<EOF
Usage: $0 [--model MODEL] [--reasoning EFFORT] [--task TASK] [--output DIR] [--repo-dir DIR] [--spec-in DIR] --test-spec-links DIR [--cleanroom-base-image IMAGE] [--docker-cpus N] [--mutant-build-jobs N] [--target-tests-per-spec N] [--final-mutants-per-spec N] [--timeout SECONDS]

Options:
  --model MODEL        Model to use (default: ${default_model})
  --reasoning EFFORT   Reasoning effort to use (default: ${default_reasoning})
  --task TASK          Task filter to use (default: ${default_task})
  --output DIR         Directory where mutant repositories are written
                       (default: output/mutants/semiformal)
  --repo-dir DIR       Directory containing <task>/<branch> repository snapshots
                       (default: ${default_repo_dir})
  --spec-in DIR        Directory containing input specs at <DIR>/<task>
                       (default: cleanroom/semiformal)
  --test-spec-links DIR
                       Directory containing <task>/test_spec_links.json
  --cleanroom-base-image IMAGE
                       Codex-enabled cleanroom image to run mutant generation in
                       (default: auto-build task_cleanroom_codex)
  --docker-cpus N      CPU cores allotted to mutant generation and build containers
                       (default: ${docker_cpus})
  --mutant-build-jobs N
                       Mutant repositories compiled concurrently (default: ${mutant_build_jobs})
  --target-tests-per-spec N  Different target tests per spec (default: ${target_tests_per_spec})
  --final-mutants-per-spec N  Selected mutants retained per spec (default: ${final_mutants_per_spec})
  --timeout SECONDS    Per-instance Codex timeout (default: ${timeout})
  --codex-command COMMAND
                       Codex command to run inside the cleanroom
                       (default: ${codex_command})
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
        --output)
            require_value "$@"
            output_dir="$2"
            shift 2
            ;;
        --repo-dir|--repo_dir)
            require_value "$@"
            repo_dir="$2"
            shift 2
            ;;
        --spec-in|--spec_in)
            require_value "$@"
            spec_in="$2"
            shift 2
            ;;
        --test-spec-links)
            require_value "$@"
            test_spec_links="$2"
            shift 2
            ;;
        --ground-truth-implementation-dir)
            require_value "$@"
            ground_truth_implementation_dir="$2"
            shift 2
            ;;
        --cleanroom-base-image)
            require_value "$@"
            cleanroom_base_image="$2"
            shift 2
            ;;
        --docker-cpus)
            require_value "$@"
            docker_cpus="$2"
            shift 2
            ;;
        --mutant-build-jobs)
            require_value "$@"
            mutant_build_jobs="$2"
            shift 2
            ;;
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
        --timeout)
            require_value "$@"
            timeout="$2"
            shift 2
            ;;
        --codex-command)
            require_value "$@"
            codex_command="$2"
            shift 2
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

if [[ ! "${docker_cpus}" =~ ^[1-9][0-9]*$ ]]; then
    echo "--docker-cpus must be a positive integer: ${docker_cpus}" >&2
    exit 1
fi
if [[ ! "${mutant_build_jobs}" =~ ^[1-9][0-9]*$ ]]; then
    echo "--mutant-build-jobs must be a positive integer: ${mutant_build_jobs}" >&2
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
if [[ ! "${timeout}" =~ ^[1-9][0-9]*$ ]]; then
    echo "--timeout must be a positive integer: ${timeout}" >&2
    exit 1
fi

. scripts/docker/docker_preflight.sh
programbench_docker_preflight || exit $?

[ -n "${output_dir}" ] || output_dir=output/mutants/semiformal
[ -n "${spec_in}" ] || spec_in=cleanroom/semiformal
if [ -z "${test_spec_links}" ]; then
    echo "--test-spec-links is required" >&2
    exit 1
fi

if [ -z "$cleanroom_base_image" ]; then
    cleanroom_base_image="$(scripts/docker/install_codex_cleanroom.sh --task "$task" --print-image)"
    scripts/docker/install_codex_cleanroom.sh --task "$task"
else
    echo "Using Codex cleanroom image: ${cleanroom_base_image}"
fi

cmd=(
    uv run programbench generate-mutants
    --output "${output_dir}"
    --model "${model}"
    --reasoning-effort "${reasoning}"
    --repo_dir "${repo_dir}"
    --spec_in "${spec_in}"
    --test-spec-links "${test_spec_links}"
    --filter "${task}"
    --force
    --codex-command "${codex_command}"
    --docker-cpus "${docker_cpus}"
    --mutant-build-jobs "${mutant_build_jobs}"
    --target-tests-per-spec "${target_tests_per_spec}"
    --final-mutants-per-spec "${final_mutants_per_spec}"
    --timeout "${timeout}"
)

cmd+=(--ground-truth-implementation-dir "$ground_truth_implementation_dir")
if [ -n "$cleanroom_base_image" ]; then
    cmd+=(--cleanroom-base-image "$cleanroom_base_image")
fi

"${cmd[@]}"
