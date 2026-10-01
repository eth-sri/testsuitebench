#!/usr/bin/env bash
set -uo pipefail

docker_bin=${PROGRAMBENCH_DOCKER_EXECUTABLE:-docker}
task=
lease_root=
sweep_leases=false
cache_keep_storage=
lock_file=

usage() {
    cat <<EOF
Usage: $0 [--task TASK] [--lease-root DIR] [--sweep-leases DIR]
          [--cache-keep-storage SIZE] [--lock-file PATH]

Remove Docker artifacts owned by completed or crashed ProgramBench tasks.
A task's images are never removed while another run still holds a lease on it.
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
        --task) require_value "$@"; task=$2; shift 2 ;;
        --lease-root) require_value "$@"; lease_root=$2; shift 2 ;;
        --sweep-leases) require_value "$@"; lease_root=$2; sweep_leases=true; shift 2 ;;
        --cache-keep-storage) require_value "$@"; cache_keep_storage=$2; shift 2 ;;
        --lock-file) require_value "$@"; lock_file=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ -z "${task}" ] && [ -z "${lease_root}" ] && [ -z "${cache_keep_storage}" ]; then
    usage >&2
    exit 2
fi
if ! command -v "${docker_bin}" >/dev/null 2>&1 || ! "${docker_bin}" info >/dev/null 2>&1; then
    echo "Docker is unavailable; ProgramBench cleanup was skipped." >&2
    exit 0
fi

if [ -n "${lock_file}" ]; then
    mkdir -p "$(dirname "${lock_file}")"
    exec 9>"${lock_file}"
    flock 9
fi

owner_is_alive() {
    local owner_pid=$1
    local owner_start=$2
    local live_start
    [[ "${owner_pid}" =~ ^[1-9][0-9]*$ ]] || return 1
    [ -r "/proc/${owner_pid}/stat" ] || return 1
    live_start=$(awk '{print $22}' "/proc/${owner_pid}/stat" 2>/dev/null) || return 1
    [ -n "${owner_start}" ] && [ "${live_start}" = "${owner_start}" ]
}

cleanup_orphan_containers() {
    local container_id
    local owner_pid
    local owner_start
    local state
    local ids=()
    mapfile -t ids < <("${docker_bin}" ps -aq --filter label=programbench.managed=true 2>/dev/null)
    for container_id in "${ids[@]}"; do
        [ -n "${container_id}" ] || continue
        owner_pid=$("${docker_bin}" inspect --format '{{ index .Config.Labels "programbench.owner-pid" }}' "${container_id}" 2>/dev/null || true)
        owner_start=$("${docker_bin}" inspect --format '{{ index .Config.Labels "programbench.owner-start" }}' "${container_id}" 2>/dev/null || true)
        # No owner label means the container is not provably abandoned: evaluation and
        # agent batches start containers without one and may be running right now.
        # Only a container that names an owner, and whose owner is gone, is an orphan.
        [ -n "${owner_pid}" ] || continue
        if ! owner_is_alive "${owner_pid}" "${owner_start}"; then
            "${docker_bin}" rm -fv "${container_id}" >/dev/null 2>&1 || true
        fi
    done

    # Containers without an owner label are left alone while they run; only
    # terminal states are unambiguously safe to remove.
    for state in exited dead; do
        mapfile -t ids < <("${docker_bin}" ps -aq --filter "status=${state}" --filter name=programbench- 2>/dev/null)
        for container_id in "${ids[@]}"; do
            [ -n "${container_id}" ] || continue
            "${docker_bin}" rm -fv "${container_id}" >/dev/null 2>&1 || true
        done
    done
}

task_is_leased() {
    # Task images are named per task (`programbench/<task>:...`) and therefore
    # shared by every run on this host, while the decision to remove them is
    # made per run. Without this check a finishing run deletes the images a
    # concurrent run is still evaluating against, which surfaces much later as
    # `manifest unknown` on every container start.
    local lease_task=$1
    local owner_file
    local owner_pid
    local owner_start
    [ -n "${lease_root}" ] || return 1
    for owner_file in "${lease_root}/${lease_task}"/*.owner; do
        [ -f "${owner_file}" ] || continue
        owner_pid=
        owner_start=
        read -r owner_pid owner_start <"${owner_file}" || true
        if owner_is_alive "${owner_pid}" "${owner_start}"; then
            return 0
        fi
        rm -f "${owner_file}"
    done
    return 1
}

cleanup_task_images() {
    local cleanup_task=$1
    local image_task=${cleanup_task/__/_1776_}
    local image_ref
    local refs=()
    if task_is_leased "${cleanup_task}"; then
        echo "Another ProgramBench run still holds ${cleanup_task}; its images were kept." >&2
        return 0
    fi
    # :task_cleanroom is the tag that must be pulled from a registry, so it is
    # the one kept: task_cleanroom_codex and task_patched both build from it,
    # and task_mutantbuild builds from task_cleanroom_codex, so every other tag
    # rebuilds without network access. :task is removed rather than kept --
    # nothing has built from it since the grading image was rebased onto the
    # cleanroom, so keeping it costs ~2GB per task and buys nothing.
    for image_ref in \
        "programbench/${image_task}:task_cleanroom_codex" \
        "programbench/${image_task}:task_cleanroom_claude" \
        "programbench/${image_task}:task_cleanroom_gemini" \
        "programbench/${image_task}:task_cleanroom_qwen" \
        "programbench/${image_task}:task_patched" \
        "programbench/${image_task}:task_mutantbuild" \
        "programbench/${image_task}:task"; do
        if "${docker_bin}" image inspect "${image_ref}" >/dev/null 2>&1; then
            "${docker_bin}" image rm "${image_ref}" >/dev/null 2>&1 || true
        fi
    done
    mapfile -t refs < <("${docker_bin}" image ls \
        --filter "reference=programbench-compiled/${cleanup_task}:*" \
        --format '{{.Repository}}:{{.Tag}}' 2>/dev/null)
    for image_ref in "${refs[@]}"; do
        [ -n "${image_ref}" ] || continue
        "${docker_bin}" image rm "${image_ref}" >/dev/null 2>&1 || true
    done
}

cleanup_orphan_containers

if [ "${sweep_leases}" = true ] && [ -d "${lease_root}" ]; then
    for lease_dir in "${lease_root}"/*; do
        [ -d "${lease_dir}" ] || continue
        lease_task=${lease_dir##*/}
        # task_is_leased prunes the owner files of dead runs as it goes, so a
        # task every holder has abandoned reclaims its images here.
        if ! task_is_leased "${lease_task}"; then
            cleanup_task_images "${lease_task}"
            rmdir "${lease_dir}" 2>/dev/null || true
        fi
    done
fi

if [ -n "${task}" ]; then
    cleanup_task_images "${task}"
fi

if [ -n "${cache_keep_storage}" ]; then
    "${docker_bin}" buildx prune --force --max-used-space "${cache_keep_storage}" >/dev/null || true
fi
