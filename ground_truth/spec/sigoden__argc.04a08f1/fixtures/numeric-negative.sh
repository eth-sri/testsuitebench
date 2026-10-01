# @arg count!
main() {
    echo "count: $argc_count"
}

eval "$(argc --argc-eval "$0" "$@")"
