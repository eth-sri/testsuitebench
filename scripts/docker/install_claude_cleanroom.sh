#!/usr/bin/env bash
set -euo pipefail

default_task=abishekvashok__cmatrix.5c082c6
default_base_tag=task_cleanroom
default_tag_suffix=claude
# Pinned so two rebuilds months apart produce the same agent.
claude_version=${PROGRAMBENCH_CLAUDE_VERSION:-2.1.280}

task=${default_task}
base_tag=${default_base_tag}
base_image=
tag_suffix=${default_tag_suffix}
pull_base=0
print_image=0
force=0

usage() {
    cat <<EOF
Usage: $0 [--task TASK] [--base-tag TAG] [--base-image IMAGE] [--tag-suffix SUFFIX] [--pull-base] [--print-image] [--force]

Build a Claude Code-enabled task cleanroom image.

Options:
  --task TASK          Task instance ID (default: ${default_task})
  --base-tag TAG       Source image tag for the task cleanroom (default: ${default_base_tag})
  --base-image IMAGE   Full source image override
  --tag-suffix SUFFIX  Output tag suffix after <base-tag>_ (default: ${default_tag_suffix})
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

. scripts/docker/docker_preflight.sh
. scripts/docker/programbench_image_probe.sh
programbench_docker_preflight || exit $?

image_task=${task/__/_1776_}
if [ -z "$base_image" ]; then
    base_image="programbench/${image_task}:${base_tag}"
fi
target_image="programbench/${image_task}:${base_tag}_${tag_suffix}"

if [ "$print_image" -eq 1 ]; then
    printf '%s\n' "$target_image"
    exit 0
fi

if [ "$force" -eq 0 ] && docker image inspect "$target_image" >/dev/null 2>&1; then
    if programbench_image_is_fresh "$target_image" claude "$claude_version"; then
        echo "Claude Code cleanroom already exists: ${target_image}"
        exit 0
    fi
    echo "Claude Code cleanroom exists but does not match the current runtime; rebuilding: ${target_image}"
fi

if [ "$pull_base" -eq 1 ]; then
    docker pull "$base_image"
fi

docker build \
    --build-arg "BASE_IMAGE=${base_image}" \
    --build-arg "AGENT=claude" \
    --build-arg "TASK=${task}" \
    --build-arg "CLAUDE_VERSION=${claude_version}" \
    -f scripts/docker/programbench_image.Dockerfile \
    -t "$target_image" \
    .

echo "Built ${target_image}"
