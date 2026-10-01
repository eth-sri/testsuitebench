#!/usr/bin/env bash
# @meta require-tools curl jq

# @cmd Test command
test_cmd() {
    echo "Running test"
}

_argc_before() {
    echo "Before"
}

_argc_after() {
    echo "After"
}

eval "$(argc --argc-eval "$0" "$@")"
