# @cmd
# @arg value[`_prefix`]
prefix() { :; }

# @cmd
# @arg value[`_filter`]
filter() { :; }

# @cmd
# @arg value[`_suffix`]
suffix() { :; }

# @cmd
# @arg value[`_combined`]
combined() { :; }

# @cmd
# @arg value[`_file_txt`]
file-txt() { :; }

# @cmd
# @arg value[`_long_desc`]
long-desc() { :; }

# @cmd
# @flag --short (Short description)
# @flag --long (This is a very long description that should be truncated because it exceeds the maximum width and we want to ensure the truncation logic works properly with unicode width calculation)
# @flag --no-parens This description has no parentheses and is also very long and should be truncated when it exceeds the fixed limit
descriptions() { :; }

_prefix() {
    echo '__argc_prefix=http://'
    echo '__argc_filter='
    echo 'example.com'
    echo 'github.com'
}

_filter() {
    echo '__argc_filter=filtered_'
    echo 'filtered_value1'
    echo 'filtered_value2'
    echo 'filtered_value3'
}

_suffix() {
    echo '__argc_suffix=.txt'
    echo 'file1'
    echo 'file2'
}

_combined() {
    echo '__argc_prefix=prefix_'
    echo '__argc_suffix=_suffix'
    echo '__argc_filter='
    echo 'middle1'
    echo 'middle2'
}

_file_txt() {
    echo '__argc_value=file:.txt'
}

_long_desc() {
    printf '%s\t%s\n' '--short' '(Short description)'
    printf '%s\t%s\n' '--long' '(This is a very long description that should be truncated because it exceeds the maximum width and we want to ensure the truncation logic works properly with unicode width calculation)'
    printf '%s\t%s\n' '--no-parens' 'This description has no parentheses and is also very long and should be truncated when it exceeds the fixed limit'
}

eval "$(argc --argc-eval "$0" "$@")"
