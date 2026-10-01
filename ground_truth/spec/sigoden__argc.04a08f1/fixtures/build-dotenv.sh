#!/usr/bin/env bash
# @meta dotenv .env
# @cmd Test
test_cmd() {
    echo "test"
}
eval "$(argc --argc-eval "$0" "$@")"
