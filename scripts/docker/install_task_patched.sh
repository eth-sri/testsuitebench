#!/usr/bin/env bash
set -euo pipefail

default_task=abishekvashok__cmatrix.5c082c6

task=${default_task}
print_image=0
force=0

usage() {
    cat <<EOF
Usage: $0 [--task TASK] [--print-image] [--force]

Build the patched evaluation image for a task. The upstream :task image cannot
be changed, so generic tooling fixes are layered on top and evaluation runs
against the result.

Options:
  --task TASK     Task instance ID (default: ${default_task})
  --print-image   Print the output image name and exit
  --force         Rebuild even when the image already satisfies the checks
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
        --print-image) print_image=1; shift ;;
        --force) force=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

image_task=${task/__/_1776_}
# The grading image is built from the cleanroom, not from :task, so eval runs in
# the same environment the agent solved in. :task additionally carries the
# task-specific build dependencies the cleanroom deliberately withholds (for
# cmatrix: libncurses-dev; for heavier tasks, hundreds of MB of toolchain), and
# grading in an environment richer than the one the submission was built in is
# what let an implementation pass eval that could never build under solve.
# Set PROGRAMBENCH_TASK_PATCHED_BASE_TAG=task to restore the old behaviour.
base_tag=${PROGRAMBENCH_TASK_PATCHED_BASE_TAG:-task_cleanroom}
base_image="programbench/${image_task}:${base_tag}"
target_image="programbench/${image_task}:task_patched"

if [ "$print_image" -eq 1 ]; then
    printf '%s\n' "$target_image"
    exit 0
fi

. scripts/docker/programbench_image_probe.sh

if [ "$force" -eq 0 ] && docker image inspect "$target_image" >/dev/null 2>&1; then
    if programbench_image_is_fresh "$target_image" none; then
        echo "Patched task image already exists: ${target_image}"
        exit 0
    fi
    echo "Patched task image does not match the current runtime; rebuilding: ${target_image}"
fi

docker build \
    --build-arg "BASE_IMAGE=${base_image}" \
    --build-arg "AGENT=none" \
    --build-arg "TASK=${task}" \
    -f scripts/docker/programbench_image.Dockerfile \
    -t "$target_image" \
    .

printf 'Built %s\n' "$target_image"
