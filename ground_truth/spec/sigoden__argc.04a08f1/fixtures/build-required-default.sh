#!/usr/bin/env bash

# @option --api-key! <KEY>  API key
# @option --format <FMT> @default json

# @cmd Send request
send() {
    echo "$argc_api_key $argc_format"
}

eval "$(argc --argc-eval "$0" "$@")"
