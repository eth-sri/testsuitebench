#!/usr/bin/env bash
set -euo pipefail

default_model=codex/gpt-5.6-sol
default_reasoning=high
default_task=abishekvashok__cmatrix.5c082c6
default_mode=spec-only
default_base_tag=task_cleanroom
default_tag_suffix=codex
default_stdout_aggregated_output_limit=240
default_timeout=21600
default_docker_cpus=4

model=${default_model}
reasoning=${default_reasoning}
task=${default_task}
mode=${default_mode}
base_tag=${default_base_tag}
tag_suffix=${default_tag_suffix}
stdout_aggregated_output_limit=${default_stdout_aggregated_output_limit}
timeout_seconds=${default_timeout}
docker_cpus=${default_docker_cpus}
output=
cleanroom=
cleanroom_base_image=
test_suite=
codex_command="codex --dangerously-bypass-approvals-and-sandbox exec --cd /workspace --skip-git-repo-check --config tools.web_search=false"

usage() {
    cat <<EOF
Usage: $0 [--model MODEL] [--reasoning EFFORT] [--task TASK] [--mode MODE] [--output DIR] [--cleanroom DIR] [--test-suite PATH]

Run Codex on a ProgramBench solve task.
Output is compatible with: uv run programbench eval <output>

Options:
  --model MODEL        Codex model to use (default: ${default_model})
  --reasoning EFFORT   Reasoning effort to use (default: ${default_reasoning})
  --task TASK          Task filter to use (default: ${default_task})
  --mode MODE          Solve mode: with-executable, spec-only, with-test, or with-test-force (default: ${default_mode})
  --output DIR         Output directory
                       (default: output/executable/<model>-<reasoning>-<mode>;
                       with-test modes nest the test-suite run under this directory)
  --cleanroom DIR      Local cleanroom root. Expected layout: <DIR>/<task>/.
                       Defaults to cleanroom/original for with-executable and
                       cleanroom/semiformal for spec-only and with-test modes.
  --test-suite PATH    Generated tests.tar.gz archive, unpacked suite directory, or multi-branch instance directory for with-test modes
                       (default: output/test-suites/<model>-<reasoning>-with-executable>/<task>/tests.tar.gz)
  --base-tag TAG       Source task cleanroom tag to Codex-enable
                       (default: ${default_base_tag})
  --tag-suffix SUFFIX  Codex image suffix after <base-tag>_ (default: ${default_tag_suffix})
  --cleanroom-base-image IMAGE
                       Prebuilt Codex-enabled task image
                       (default: auto-build <base-tag>_<tag-suffix>)
  --codex-command COMMAND
                       Codex command to run inside the cleanroom
                       (default: ${codex_command})
  --stdout-aggregated-output-limit N
                       Max chars printed for non-JSON Codex passthrough lines
                       (default: ${default_stdout_aggregated_output_limit})
  --timeout SECONDS    Docker run timeout in seconds (default: ${default_timeout})
  --docker-cpus N       CPU cores allotted to the solve container (default: ${default_docker_cpus})
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
        --mode)
            require_value "$@"
            mode="$2"
            shift 2
            ;;
        --output)
            require_value "$@"
            output="$2"
            shift 2
            ;;
        --cleanroom)
            require_value "$@"
            cleanroom="$2"
            shift 2
            ;;
        --test-suite)
            require_value "$@"
            test_suite="$2"
            shift 2
            ;;
        --base-tag)
            require_value "$@"
            base_tag="$2"
            shift 2
            ;;
        --tag-suffix)
            require_value "$@"
            tag_suffix="$2"
            shift 2
            ;;
        --cleanroom-base-image)
            require_value "$@"
            cleanroom_base_image="$2"
            shift 2
            ;;
        --codex-command)
            require_value "$@"
            codex_command="$2"
            shift 2
            ;;
        --stdout-aggregated-output-limit)
            require_value "$@"
            stdout_aggregated_output_limit="$2"
            shift 2
            ;;
        --timeout)
            require_value "$@"
            timeout_seconds="$2"
            shift 2
            ;;
        --docker-cpus)
            require_value "$@"
            docker_cpus="$2"
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

case "${mode}" in
    with-executable)
        default_cleanroom=cleanroom/original
        ;;
    spec-only|with-test|with-test-force)
        default_cleanroom=cleanroom/semiformal
        ;;
    *)
        echo "Unsupported mode: ${mode}" >&2
        usage >&2
        exit 1
        ;;
esac

if [ -z "${cleanroom}" ]; then
    cleanroom=${default_cleanroom}
fi
if [ -z "${output}" ]; then
    output="output/executable/${model}-${reasoning}-${mode}"
    if [ "${mode}" = "with-test" ] || [ "${mode}" = "with-test-force" ]; then
        test_suite_archive=${test_suite:-"output/test-suites/${model}-${reasoning}-with-executable/${task}/tests.tar.gz"}
        test_suite_archive=${test_suite_archive%/}
        if [[ "${test_suite_archive}" != */tests.tar.gz ]]; then
            test_suite_archive="${test_suite_archive}/tests.tar.gz"
        fi
        test_suite_marker="output/test-suites/"
        test_suite_suffix="/${task}/tests.tar.gz"
        test_suite_after_marker=${test_suite_archive#*${test_suite_marker}}
        if [[ "${test_suite_after_marker}" != "${test_suite_archive}" && "${test_suite_after_marker}" == *"${test_suite_suffix}" ]]; then
            test_suite_label=${test_suite_after_marker%${test_suite_suffix}}
        else
            test_suite_instance_dir=${test_suite_archive%/tests.tar.gz}
            if [[ "${test_suite_instance_dir}" == */"${task}" ]]; then
                test_suite_parent=${test_suite_instance_dir%/${task}}
                test_suite_label=${test_suite_parent##*/}
            else
                test_suite_label=${test_suite_instance_dir##*/}
            fi
        fi
        output="${output}/${test_suite_label}"
    fi
fi
archive_dir="${output}/${task}"
extract_dir="${archive_dir}/submission_untar"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
    python_cmd=(python3)
elif command -v uv >/dev/null 2>&1; then
    python_cmd=(uv run python)
else
    echo "python3 or uv is required to run ${script_dir}/solve_codex.py" >&2
    exit 127
fi

cmd=(
    "${python_cmd[@]}"
    "${script_dir}/solve_codex.py"
    --model "${model}"
    --reasoning "${reasoning}"
    --task "${task}"
    --mode "${mode}"
    --output "${output}"
    --cleanroom "${cleanroom}"
    --base-tag "${base_tag}"
    --tag-suffix "${tag_suffix}"
    --codex-command "${codex_command}"
    --stdout-aggregated-output-limit "${stdout_aggregated_output_limit}"
    --timeout "${timeout_seconds}"
    --docker-cpus "${docker_cpus}"
)
if [ -n "${cleanroom_base_image}" ]; then
    cmd+=(--cleanroom-base-image "${cleanroom_base_image}")
fi
if [ -n "${test_suite}" ]; then
    cmd+=(--test-suite "${test_suite}")
fi

set +e
"${cmd[@]}"
run_status=$?
set -e

if [ -f "${archive_dir}/submission.tar.gz" ]; then
    rm -rf "${extract_dir}"
    mkdir -p "${extract_dir}"
    tar -xzf "${archive_dir}/submission.tar.gz" \
        -C "${extract_dir}"
    find "${extract_dir}" -maxdepth 1 -type f
else
    echo "No submission archive found at ${archive_dir}/submission.tar.gz; skipped extraction" >&2
fi

exit "${run_status}"
