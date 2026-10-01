#!/usr/bin/env bash

# @cmd Default command (default)
default_cmd() {
    echo "Default called"
}

# @cmd Other command
other() {
    echo "Other called"
}

eval "$(argc --argc-eval "$0" "$@")"
