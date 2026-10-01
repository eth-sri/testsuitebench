#!/usr/bin/env bash
set -euo pipefail

default_task=abishekvashok__cmatrix.5c082c6
default_base_tag=task_cleanroom
# Pinned so two rebuilds months apart produce the same agent.
gemini_version=${PROGRAMBENCH_GEMINI_VERSION:-0.60.0}
qwen_version=${PROGRAMBENCH_QWEN_VERSION:-0.24.0}
deepseek_version=${PROGRAMBENCH_DEEPSEEK_VERSION:-0.1.5-rc.3}
zcode_version=${PROGRAMBENCH_ZCODE_VERSION:-3.14.3}
muse_adapter_version=${PROGRAMBENCH_MUSE_ADAPTER_VERSION:-0.3.2}

agent=
task=${default_task}
base_tag=${default_base_tag}
base_image=
tag_suffix=
pull_base=0
print_image=0
force=0

usage() {
    cat <<EOF
Usage: $0 --agent AGENT [--task TASK] [--base-tag TAG] [--base-image IMAGE] [--tag-suffix SUFFIX] [--pull-base] [--print-image] [--force]

Build a task cleanroom image with the selected agent harness installed.
Muse Code itself is bind-mounted; the Muse image contains its OpenRouter adapter.

Options:
  --agent AGENT        gemini, qwen, deepseek, glm, or muse (required)
  --task TASK          Task instance ID (default: ${default_task})
  --base-tag TAG       Source image tag for the task cleanroom (default: ${default_base_tag})
  --base-image IMAGE   Full source image override
  --tag-suffix SUFFIX  Output tag suffix after <base-tag>_ (default: the agent name)
  --pull-base          Pull the source image before building
  --print-image        Print the target image name and exit
  --force              Rebuild even if the target image already exists
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
        --agent) require_value "$@"; agent="$2"; shift 2 ;;
        --task) require_value "$@"; task="$2"; shift 2 ;;
        --base-tag) require_value "$@"; base_tag="$2"; shift 2 ;;
        --base-image) require_value "$@"; base_image="$2"; shift 2 ;;
        --tag-suffix) require_value "$@"; tag_suffix="$2"; shift 2 ;;
        --pull-base) pull_base=1; shift ;;
        --print-image) print_image=1; shift ;;
        --force) force=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

case "$agent" in
    gemini) agent_version=${gemini_version} ;;
    qwen) agent_version=${qwen_version} ;;
    deepseek) agent_version=${deepseek_version} ;;
    glm) agent_version=${zcode_version} ;;
    muse) agent_version=${muse_adapter_version} ;;
    *) echo "--agent must be gemini, qwen, deepseek, glm, or muse (got: ${agent})" >&2; usage >&2; exit 1 ;;
esac
tag_suffix=${tag_suffix:-${agent}}

image_task=${task/__/_1776_}
if [ -z "$base_image" ]; then
    base_image="programbench/${image_task}:${base_tag}"
fi
target_image="programbench/${image_task}:${base_tag}_${tag_suffix}"

if [ "$print_image" -eq 1 ]; then
    printf '%s\n' "$target_image"
    exit 0
fi

. scripts/docker/docker_preflight.sh
. scripts/docker/programbench_image_probe.sh
programbench_docker_preflight || exit $?

if [ "$force" -eq 0 ] && docker image inspect "$target_image" >/dev/null 2>&1; then
    if programbench_image_is_fresh "$target_image" "$agent" "$agent_version"; then
        echo "${agent} cleanroom already exists: ${target_image}"
        exit 0
    fi
    echo "${agent} cleanroom exists but does not match the current runtime; rebuilding: ${target_image}"
fi

if [ "$pull_base" -eq 1 ]; then
    docker pull "$base_image"
fi

docker build \
    --build-arg "BASE_IMAGE=${base_image}" \
    --build-arg "AGENT=${agent}" \
    --build-arg "TASK=${task}" \
    --build-arg "GEMINI_VERSION=${gemini_version}" \
    --build-arg "QWEN_VERSION=${qwen_version}" \
    --build-arg "DEEPSEEK_VERSION=${deepseek_version}" \
    --build-arg "ZCODE_VERSION=${zcode_version}" \
    --build-arg "MUSE_ADAPTER_VERSION=${muse_adapter_version}" \
    -f scripts/docker/programbench_image.Dockerfile \
    -t "$target_image" \
    .

echo "Built ${target_image}"
