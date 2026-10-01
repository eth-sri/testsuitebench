#!/usr/bin/env bash
set -euo pipefail

# Creates the network posture that agent containers default to: an --internal
# network they sit on, plus a dual-homed squid that allowlists only the model
# API hosts. Idempotent, so it is safe to run before every pipeline.
#
# The names must match EGRESS_NETWORK/EGRESS_PROXY in src/programbench/constants.py
# and the mirror in scripts/agents/solve_codex.py; tests/test_agent_network.py asserts
# they still agree.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker_bin="${PROGRAMBENCH_DOCKER_EXECUTABLE:-docker}"
egress_network=pb-egress
uplink_network=pb-uplink
proxy_name=pb-proxy
proxy_image="${PROGRAMBENCH_EGRESS_PROXY_IMAGE:-ubuntu/squid:latest}"
recreate=0

while [ $# -gt 0 ]; do
    case "$1" in
        --recreate) recreate=1 ;;
        *) echo "Unknown option: $1" >&2; exit 64 ;;
    esac
    shift
done

if ! "${docker_bin}" network inspect "${uplink_network}" >/dev/null 2>&1; then
    "${docker_bin}" network create "${uplink_network}" >/dev/null
    echo "Created ${uplink_network}"
fi

if ! "${docker_bin}" network inspect "${egress_network}" >/dev/null 2>&1; then
    "${docker_bin}" network create --internal "${egress_network}" >/dev/null
    echo "Created ${egress_network} (internal)"
fi

if [ "${recreate}" = 1 ]; then
    "${docker_bin}" rm -f "${proxy_name}" >/dev/null 2>&1 || true
fi

if [ -z "$("${docker_bin}" ps -q --filter "name=^${proxy_name}$")" ]; then
    "${docker_bin}" rm -f "${proxy_name}" >/dev/null 2>&1 || true
    "${docker_bin}" run -d \
        --name "${proxy_name}" \
        --restart unless-stopped \
        --network "${egress_network}" \
        -v "${script_dir}/egress-squid.conf:/etc/squid/squid.conf:ro" \
        "${proxy_image}" -N -d1 -f /etc/squid/squid.conf >/dev/null
    "${docker_bin}" network connect "${uplink_network}" "${proxy_name}"
    echo "Started ${proxy_name}"
fi

# A proxy that lost its uplink, or an egress network that is not internal, both
# fail open in ways nothing downstream would notice.
[ "$("${docker_bin}" network inspect "${egress_network}" --format '{{.Internal}}')" = true ] \
    || { echo "${egress_network} is not internal" >&2; exit 1; }
for network in "${egress_network}" "${uplink_network}"; do
    "${docker_bin}" inspect "${proxy_name}" --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}} {{end}}' \
        | grep -qw "${network}" || { echo "${proxy_name} is not on ${network}" >&2; exit 1; }
done

# The config is bind-mounted, but Squid keeps parsed ACLs in memory.
# Reconfigure on every setup so newly pinned provider hosts take effect.
"${docker_bin}" exec "${proxy_name}" squid -k reconfigure -f /etc/squid/squid.conf

echo "Egress ready: agent containers run on ${egress_network} behind http://${proxy_name}:3128"
