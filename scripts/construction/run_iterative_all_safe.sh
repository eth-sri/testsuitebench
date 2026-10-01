#!/usr/bin/env bash
set -euo pipefail

# Crash-safe supervisor for run_iterative_all.sh. Completed task images are
# removed within one polling interval, and stale runs are swept on startup.
iter_root=output/construction
run_id=
cache_keep_storage=200GB
poll_seconds=5
forwarded=("$@")

for ((index = 0; index < ${#forwarded[@]}; index++)); do
    case "${forwarded[index]}" in
        --iter-root)
            iter_root=${forwarded[index + 1]}
            index=$((index + 1))
            ;;
        --run-id)
            run_id=${forwarded[index + 1]}
            index=$((index + 1))
            ;;
    esac
done

iter_root=${iter_root%/}
if [ -z "${run_id}" ]; then
    run_id="safe-$(date -u +%Y%m%dT%H%M%S.%N)-$$"
    forwarded+=(--run-id "${run_id}")
fi

batch_dir="${iter_root}/batch"
supervisor_dir="${batch_dir}/docker-supervisors"
run_dir="${batch_dir}/runs/${run_id}"
# Task images are shared by every run on the host, so the lease directory and
# the lock serialising their removal live outside any single iteration root.
docker_state_dir=${PROGRAMBENCH_DOCKER_STATE_DIR:-output/.docker-state}
lease_root="${docker_state_dir}/leases"
cleanup_lock="${docker_state_dir}/cleanup.lock"
owner_file="${supervisor_dir}/${run_id}.owner"
cleaned_file="${supervisor_dir}/${run_id}.cleaned"
docker_bin=${PROGRAMBENCH_DOCKER_EXECUTABLE:-docker}
runner_pid=
mkdir -p "${supervisor_dir}"
: >"${cleaned_file}"

owner_is_alive() {
    local owner_pid=$1
    local owner_start=$2
    local live_start
    [[ "${owner_pid}" =~ ^[1-9][0-9]*$ ]] || return 1
    [ -r "/proc/${owner_pid}/stat" ] || return 1
    live_start=$(awk '{print $22}' "/proc/${owner_pid}/stat" 2>/dev/null) || return 1
    [ "${live_start}" = "${owner_start}" ]
}

remove_task_containers() {
    local task=$1
    local image_task=${task/__/_1776_}
    local image_ref
    local container_id
    local batch_run
    local refs=(
        "programbench/${image_task}:task_cleanroom_codex"
        "programbench/${image_task}:task_cleanroom"
        "programbench/${image_task}:task_patched"
        "programbench/${image_task}:task_mutantbuild"
    )
    mapfile -t compiled_refs < <("${docker_bin}" image ls \
        --filter "reference=programbench-compiled/${task}:*" \
        --format '{{.Repository}}:{{.Tag}}' 2>/dev/null)
    refs+=("${compiled_refs[@]}")
    for image_ref in "${refs[@]}"; do
        [ -n "${image_ref}" ] || continue
        mapfile -t container_ids < <("${docker_bin}" ps -aq --filter "ancestor=${image_ref}" 2>/dev/null)
        for container_id in "${container_ids[@]}"; do
            [ -n "${container_id}" ] || continue
            # A container with a run label belongs to an evaluation or agent batch,
            # which removes its own containers; killing it here fails that batch.
            batch_run=$("${docker_bin}" inspect --format '{{ index .Config.Labels "programbench.run" }}' "${container_id}" 2>/dev/null || true)
            [ -z "${batch_run}" ] || continue
            "${docker_bin}" rm -fv "${container_id}" >/dev/null 2>&1 || true
        done
    done
}

task_is_leased() {
    local lease_task=$1
    local owner_file
    local owner_pid
    local owner_start
    for owner_file in "${lease_root}/${lease_task}"/*.owner; do
        [ -f "${owner_file}" ] || continue
        owner_pid=
        owner_start=
        read -r owner_pid owner_start <"${owner_file}" || true
        owner_is_alive "${owner_pid}" "${owner_start}" && return 0
    done
    return 1
}

cleanup_task() {
    local task=$1
    [ -n "${task}" ] || return 0
    # remove_task_containers force-removes containers by image ancestry, which
    # would kill a concurrent run's live evaluation, so it is gated on the lease
    # as well as the image removal that follows it.
    if task_is_leased "${task}"; then
        printf 'Another run still holds %s; its containers and images were kept.\n' "${task}" >&2
        return 0
    fi
    remove_task_containers "${task}"
    bash scripts/docker/cleanup_programbench_docker.sh \
        --task "${task}" \
        --lease-root "${lease_root}" \
        --cache-keep-storage "${cache_keep_storage}" \
        --lock-file "${cleanup_lock}" || true
}

cleanup_started_tasks() {
    local tasks_file=$1
    local task
    [ -f "${tasks_file}" ] || return 0
    while IFS= read -r task; do
        [ -n "${task}" ] || continue
        if ! grep -Fxq "${task}" "${cleaned_file}" 2>/dev/null; then
            cleanup_task "${task}"
            printf '%s\n' "${task}" >>"${cleaned_file}"
        fi
    done <"${tasks_file}"
}

sweep_stale_runs() {
    local stale_owner
    local stale_run_id
    local stale_pid
    local stale_start
    for stale_owner in "${supervisor_dir}"/*.owner; do
        [ -f "${stale_owner}" ] || continue
        read -r stale_pid stale_start <"${stale_owner}" || true
        if owner_is_alive "${stale_pid:-}" "${stale_start:-}"; then
            continue
        fi
        stale_run_id=${stale_owner##*/}
        stale_run_id=${stale_run_id%.owner}
        cleanup_started_tasks "${batch_dir}/runs/${stale_run_id}/tasks.started.txt"
        rm -f "${stale_owner}"
    done
}

cleanup_completed_tasks() {
    local task
    local state
    local started_tasks="${run_dir}/tasks.started.txt"
    [ -f "${started_tasks}" ] || return 0
    while IFS= read -r task; do
        [ -n "${task}" ] || continue
        grep -Fxq "${task}" "${cleaned_file}" 2>/dev/null && continue
        state=
        if [ -f "${batch_dir}/status/${task}.status" ]; then
            IFS=$'\t' read -r state _ <"${batch_dir}/status/${task}.status" || true
        fi
        case "${state}" in
            ok|failed:*)
                cleanup_task "${task}"
                printf '%s\n' "${task}" >>"${cleaned_file}"
                ;;
        esac
    done <"${started_tasks}"
}

finish() {
    local rc=$?
    trap - EXIT INT TERM
    if [ -n "${runner_pid}" ] && kill -0 "${runner_pid}" 2>/dev/null; then
        kill "${runner_pid}" 2>/dev/null || true
        wait "${runner_pid}" 2>/dev/null || true
    fi
    cleanup_started_tasks "${run_dir}/tasks.started.txt"
    rm -f "${owner_file}" "${cleaned_file}"
    exit "${rc}"
}
trap finish EXIT INT TERM

sweep_stale_runs
# Reclaim tasks whose every lease holder died without running its own cleanup.
bash scripts/docker/cleanup_programbench_docker.sh \
    --sweep-leases "${lease_root}" \
    --lock-file "${cleanup_lock}" || true
: >"${cleaned_file}"
printf 'Supervisor PID: %d (kill -TERM -%d to stop the whole run)\n' "$$" "$$"
bash scripts/construction/run_iterative_all.sh "${forwarded[@]}" &
runner_pid=$!
printf 'Runner PID: %d\n' "${runner_pid}"
runner_start=$(awk '{print $22}' "/proc/${runner_pid}/stat")
printf '%s %s\n' "${runner_pid}" "${runner_start}" >"${owner_file}"

while kill -0 "${runner_pid}" 2>/dev/null; do
    cleanup_completed_tasks
    sleep "${poll_seconds}"
done

set +e
wait "${runner_pid}"
runner_rc=$?
set -e
runner_pid=
cleanup_started_tasks "${run_dir}/tasks.started.txt"
rm -f "${owner_file}" "${cleaned_file}"
trap - EXIT INT TERM
exit "${runner_rc}"
