# @cmd First command
cmd1() { :; }

# @cmd Second command
cmd2() { :; }

# @cmd Options command
# @flag --verbose Enable verbose output
# @option --output <FILE> Output file
opts() { :; }

eval "$(argc --argc-eval "$0" "$@")"
