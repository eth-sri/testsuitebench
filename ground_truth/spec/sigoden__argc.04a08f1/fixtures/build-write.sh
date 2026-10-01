#!/usr/bin/env bash
# @cmd Test
test-cmd() {
    echo "test"
}
eval "$(argc --argc-eval "$0" "$@")"
