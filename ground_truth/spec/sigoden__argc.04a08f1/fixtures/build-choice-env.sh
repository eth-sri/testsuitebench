#!/usr/bin/env bash

# @env LOG_LEVEL! @choice debug info warn error

# @cmd Process logs
process() {
    echo "$LOG_LEVEL"
}

eval "$(argc --argc-eval "$0" "$@")"
