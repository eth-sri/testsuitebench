#!/usr/bin/env bash

# The one rebuild rule for every image built from programbench_image.Dockerfile.
#
# Solve, test generation and eval must run in the same runtime, and these probes
# decide whether an image that already exists is that runtime. When each install
# script carried its own probe they checked different property sets, so an image
# cached before a layer was added stayed "fresh" under one script while another
# rebuilt it -- the drift the single Dockerfile exists to prevent, reintroduced
# one level up. The agent CLI is the only thing allowed to differ, so it is the
# only parameter.

# Must match ARG SCCACHE_VERSION in scripts/docker/programbench_image.Dockerfile.
PROGRAMBENCH_SCCACHE_VERSION=0.10.0

# Usage: programbench_image_is_fresh IMAGE {none|codex|claude|gemini|qwen|deepseek|glm|muse} [AGENT_VERSION]
programbench_image_is_fresh() {
    local image=$1 agent=$2 version=${3:-}
    local check_agent check binary

    case "$agent" in
        none) check_agent='! command -v codex >/dev/null && ! command -v claude >/dev/null && ! command -v gemini >/dev/null && ! command -v qwen >/dev/null && ! command -v dsh >/dev/null && ! command -v zcode >/dev/null' ;;
        muse) check_agent="python3 -c 'import muse_code_openrouter'"; binary=python3 ;;
        codex|claude|gemini|qwen|deepseek|glm) binary=${agent}; [ "$agent" = deepseek ] && binary=dsh; [ "$agent" = glm ] && binary=zcode; check_agent="command -v ${binary} >/dev/null" ;;
        *) echo "AGENT must be one of: none, codex, claude, gemini, qwen, deepseek, glm, muse (got: ${agent})" >&2; return 2 ;;
    esac
    if [ -n "$version" ]; then
        if [ "$agent" = muse ]; then
            check_agent="${check_agent} && python3 -c 'import muse_code_openrouter as m; assert m.__version__ == \"${version}\"'"
        elif [ "$agent" = glm ]; then
            check_agent="${check_agent} && test \"\$(cat /opt/programbench-zcode-version)\" = '${version}'"
        else
            check_agent="${check_agent} && ${binary} --version | grep -Fq '${version}'"
        fi
    fi

    # --no-index makes the pip line a pure "is every requirement already
    # satisfied?" probe: it exits 0 when they all are and non-zero as soon as one
    # is missing or version-bound, without reaching the network.
    check='node -e "process.exit(parseInt(process.versions.node) >= 16 ? 0 : 1)"'
    check="${check} && test \"\$(readlink -f /usr/local/bin/apt)\" = /usr/local/libexec/programbench-apt-flock"
    check="${check} && test \"\$(readlink -f /usr/local/bin/apt-get)\" = /usr/local/libexec/programbench-apt-flock"
    check="${check} && test \"\$(sccache --version)\" = 'sccache ${PROGRAMBENCH_SCCACHE_VERSION}'"
    check="${check} && test -s \"\$PIP_CONSTRAINT\""
    check="${check} && python3 -m pip install --no-index -q -r /opt/programbench/requirements.txt"

    # --entrypoint sh so the probe never depends on what the base image sets.
    docker run --rm --entrypoint sh "$image" -c "${check_agent} && ${check}" >/dev/null 2>&1
}
