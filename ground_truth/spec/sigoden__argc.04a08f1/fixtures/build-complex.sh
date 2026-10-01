#!/usr/bin/env bash
# @describe Complex multi-level command hierarchy
# @meta version 2.5.0
# @meta author complex-tester
# @meta man-section 8

# @cmd Parent command
parent() { echo parent; }

# @cmd Child command
# @option --value <VALUE>
parent::child() { echo "$argc_value"; }

# @cmd Grandchild command
# @arg input!
parent::child::grandchild() { echo "$argc_input"; }

eval "$(argc --argc-eval "$0" "$@")"
