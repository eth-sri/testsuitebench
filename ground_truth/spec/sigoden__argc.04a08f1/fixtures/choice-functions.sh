# @cmd
# @arg environment![`_choice_env`]
# @option --region[`_choice_region`]
deploy() { :; }

_choice_env() {
    echo dev
    echo prod
}

_choice_region() {
    echo us-east-1
    echo us-west-2
}

eval "$(argc --argc-eval "$0" "$@")"
