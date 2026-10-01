#!/usr/bin/env bash
set -euo pipefail

default_task=abishekvashok__cmatrix.5c082c6

task=${default_task}
base_image=
print_image=0
force=0

usage() {
    cat <<EOF
Usage: $0 [--task TASK] [--base-image IMAGE] [--print-image] [--force]

Build the build-only image used for mutant and reference builds. Task-specific
dependencies live here because no agent runs in this image; the agent-facing
cleanroom must never be built from it.

Options:
  --task TASK          Task instance ID (default: ${default_task})
  --base-image IMAGE   Source image (default: the task's Codex cleanroom)
  --print-image        Print the output image name and exit
  --force              Rebuild even when the image already exists
EOF
}

require_value() {
    if [ "$#" -lt 2 ]; then
        echo "Missing value for $1" >&2
        exit 2
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --task) require_value "$@"; task="$2"; shift 2 ;;
        --base-image) require_value "$@"; base_image="$2"; shift 2 ;;
        --print-image) print_image=1; shift ;;
        --force) force=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

image_task=${task/__/_1776_}
target_image="programbench/${image_task}:task_mutantbuild"

if [ "$print_image" -eq 1 ]; then
    printf '%s\n' "$target_image"
    exit 0
fi

if [ -z "$base_image" ]; then
    base_image="$(scripts/docker/install_codex_cleanroom.sh --task "$task" --print-image)"
    scripts/docker/install_codex_cleanroom.sh --task "$task"
fi

if [ "$force" -eq 0 ] && docker image inspect "$target_image" >/dev/null 2>&1; then
    if [ "$(docker run --rm --entrypoint /usr/local/bin/sccache "$target_image" --version 2>/dev/null)" = "sccache 0.10.0" ]; then
        echo "Mutant build image already exists: ${target_image}"
        exit 0
    fi
    echo "Mutant build image has an outdated compiler cache; rebuilding: ${target_image}"
fi

docker build \
    --build-arg "BASE_IMAGE=${base_image}" \
    --build-arg "TASK=${task}" \
    -f scripts/docker/task_mutantbuild.Dockerfile \
    -t "$target_image" \
    .

printf 'Built %s\n' "$target_image"
