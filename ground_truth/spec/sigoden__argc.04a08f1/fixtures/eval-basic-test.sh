# @describe A basic test

# @cmd Print a greeting
# @arg name+
hello() { :; }

eval "$(argc --argc-eval "$0" "$@")"
