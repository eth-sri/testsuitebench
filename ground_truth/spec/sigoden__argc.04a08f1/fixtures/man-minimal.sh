# @cmd Simple command
simple() { :; }

eval "$(argc --argc-eval "$0" "$@")"
