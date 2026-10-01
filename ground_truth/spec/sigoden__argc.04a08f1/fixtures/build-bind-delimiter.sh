#!/usr/bin/env bash

# @option --items* <ITEM> @env ITEMS_LIST @delimiter ,
# @arg tags+ @env TAG_LIST @delimiter :

# @cmd Process
process() {
    printf '%s\n' "${argc_items[@]}" "${argc_tags[@]}"
}

eval "$(argc --argc-eval "$0" "$@")"
