#!/usr/bin/env bash

# @option --token <TOKEN> @env API_TOKEN
# @option --count <NUM> @env MAX_COUNT
# @arg input @env INPUT_FILE

# @cmd Process
process() {
    echo "$argc_token $argc_count $argc_input"
}

eval "$(argc --argc-eval "$0" "$@")"
