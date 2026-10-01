#!/usr/bin/env bash

# @cmd
task_with_args() {
    printf '%s\n' "$@"
}

eval "$(argc --argc-eval "$0" "$@")"
