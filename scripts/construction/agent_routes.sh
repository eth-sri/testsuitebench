#!/usr/bin/env bash

# Shared model/reasoning routing for ProgramBench shell pipelines. Model values
# are intentionally opaque so a future executor/provider layer can reuse the
# same step names and override mechanism.

programbench_agent_routes_reset() {
    unset PROGRAMBENCH_ROUTE_MODEL PROGRAMBENCH_ROUTE_REASONING
    unset PROGRAMBENCH_ROUTE_RETRY_MODEL PROGRAMBENCH_ROUTE_RETRY_REASONING
    unset PROGRAMBENCH_ROUTE_MODEL_OVERRIDE PROGRAMBENCH_ROUTE_REASONING_OVERRIDE
    unset PROGRAMBENCH_ROUTE_RETRY_MODEL_OVERRIDE PROGRAMBENCH_ROUTE_RETRY_REASONING_OVERRIDE
    declare -gA PROGRAMBENCH_ROUTE_MODEL=()
    declare -gA PROGRAMBENCH_ROUTE_REASONING=()
    declare -gA PROGRAMBENCH_ROUTE_RETRY_MODEL=()
    declare -gA PROGRAMBENCH_ROUTE_RETRY_REASONING=()
    declare -gA PROGRAMBENCH_ROUTE_MODEL_OVERRIDE=()
    declare -gA PROGRAMBENCH_ROUTE_REASONING_OVERRIDE=()
    declare -gA PROGRAMBENCH_ROUTE_RETRY_MODEL_OVERRIDE=()
    declare -gA PROGRAMBENCH_ROUTE_RETRY_REASONING_OVERRIDE=()
}

programbench_agent_route_register() {
    local step=$1
    local model=$2
    local reasoning=$3
    local retry_model=${4:-${model}}
    local retry_reasoning=${5:-${reasoning}}

    if [ -z "${step}" ] || [ -z "${model}" ] || [ -z "${reasoning}" ]; then
        echo "Agent route step, model, and reasoning must be non-empty" >&2
        return 1
    fi
    PROGRAMBENCH_ROUTE_MODEL["${step}"]=${model}
    PROGRAMBENCH_ROUTE_REASONING["${step}"]=${reasoning}
    PROGRAMBENCH_ROUTE_RETRY_MODEL["${step}"]=${retry_model}
    PROGRAMBENCH_ROUTE_RETRY_REASONING["${step}"]=${retry_reasoning}
}

programbench_agent_route_override() {
    local field=$1
    local assignment=$2
    local step
    local requested_step
    local value

    if [[ "${assignment}" != *=* ]]; then
        echo "Agent route override must have STEP=VALUE form: ${assignment}" >&2
        return 1
    fi
    requested_step=${assignment%%=*}
    value=${assignment#*=}
    if [ -z "${requested_step}" ] || [ -z "${value}" ]; then
        echo "Agent route override must have non-empty STEP and VALUE: ${assignment}" >&2
        return 1
    fi
    if [[ ! "${requested_step}" =~ ^[a-z0-9_-]+$ ]]; then
        echo "Invalid agent route step: ${requested_step}" >&2
        return 1
    fi
    step=${requested_step//-/_}
    if [[ ! -v "PROGRAMBENCH_ROUTE_MODEL[${step}]" ]]; then
        echo "Unknown agent route step: ${requested_step}" >&2
        return 1
    fi

    case "${field}" in
        model) PROGRAMBENCH_ROUTE_MODEL_OVERRIDE["${step}"]=${value} ;;
        reasoning) PROGRAMBENCH_ROUTE_REASONING_OVERRIDE["${step}"]=${value} ;;
        retry-model) PROGRAMBENCH_ROUTE_RETRY_MODEL_OVERRIDE["${step}"]=${value} ;;
        retry-reasoning) PROGRAMBENCH_ROUTE_RETRY_REASONING_OVERRIDE["${step}"]=${value} ;;
        *)
            echo "Unknown agent route field: ${field}" >&2
            return 1
            ;;
    esac
}

programbench_agent_routes_resolve() {
    local global_model=${1:-}
    local global_reasoning=${2:-}
    local step

    for step in "${!PROGRAMBENCH_ROUTE_MODEL[@]}"; do
        if [ -n "${global_model}" ]; then
            PROGRAMBENCH_ROUTE_MODEL["${step}"]=${global_model}
            PROGRAMBENCH_ROUTE_RETRY_MODEL["${step}"]=${global_model}
        fi
        if [ -n "${global_reasoning}" ]; then
            PROGRAMBENCH_ROUTE_REASONING["${step}"]=${global_reasoning}
            PROGRAMBENCH_ROUTE_RETRY_REASONING["${step}"]=${global_reasoning}
        fi
    done

    for step in "${!PROGRAMBENCH_ROUTE_MODEL_OVERRIDE[@]}"; do
        PROGRAMBENCH_ROUTE_MODEL["${step}"]=${PROGRAMBENCH_ROUTE_MODEL_OVERRIDE["${step}"]}
    done
    for step in "${!PROGRAMBENCH_ROUTE_REASONING_OVERRIDE[@]}"; do
        PROGRAMBENCH_ROUTE_REASONING["${step}"]=${PROGRAMBENCH_ROUTE_REASONING_OVERRIDE["${step}"]}
    done
    for step in "${!PROGRAMBENCH_ROUTE_RETRY_MODEL_OVERRIDE[@]}"; do
        PROGRAMBENCH_ROUTE_RETRY_MODEL["${step}"]=${PROGRAMBENCH_ROUTE_RETRY_MODEL_OVERRIDE["${step}"]}
    done
    for step in "${!PROGRAMBENCH_ROUTE_RETRY_REASONING_OVERRIDE[@]}"; do
        PROGRAMBENCH_ROUTE_RETRY_REASONING["${step}"]=${PROGRAMBENCH_ROUTE_RETRY_REASONING_OVERRIDE["${step}"]}
    done
}

programbench_agent_routes_print() {
    local step
    for step in "${!PROGRAMBENCH_ROUTE_MODEL[@]}"; do
        printf '%s\t%s\t%s\t%s\t%s\n' \
            "${step}" \
            "${PROGRAMBENCH_ROUTE_MODEL["${step}"]}" \
            "${PROGRAMBENCH_ROUTE_REASONING["${step}"]}" \
            "${PROGRAMBENCH_ROUTE_RETRY_MODEL["${step}"]}" \
            "${PROGRAMBENCH_ROUTE_RETRY_REASONING["${step}"]}"
    done | sort
}
