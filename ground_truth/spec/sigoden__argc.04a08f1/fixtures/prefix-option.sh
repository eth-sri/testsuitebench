# @option -D-* <VALUE>
main() {
    echo "D: ${argc_D[*]}"
}

eval "$(argc --argc-eval "$0" "$@")"
