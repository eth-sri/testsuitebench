#!/usr/bin/env bash

programbench_docker_preflight() {
    local docker_bin="${PROGRAMBENCH_DOCKER_EXECUTABLE:-docker}"
    local output
    local rc

    if ! command -v "${docker_bin}" >/dev/null 2>&1; then
        echo "Docker executable not found: ${docker_bin}" >&2
        echo "Install Docker or set PROGRAMBENCH_DOCKER_EXECUTABLE to the docker-compatible CLI to use." >&2
        return 127
    fi

    output="$("${docker_bin}" info 2>&1)"
    rc=$?
    if [ "${rc}" -ne 0 ]; then
        echo "Docker is not reachable from this shell." >&2
        echo "${output}" >&2
        if [ -n "${DOCKER_HOST:-}" ]; then
            echo "DOCKER_HOST is set to: ${DOCKER_HOST}" >&2
            echo "Unset DOCKER_HOST if you want the default Docker socket, or start the daemon that owns that socket." >&2
        else
            echo "Start Docker, or set DOCKER_HOST to a reachable Docker daemon socket." >&2
        fi
        return "${rc}"
    fi
}
