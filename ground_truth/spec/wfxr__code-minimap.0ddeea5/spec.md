## Spec 1

The delivered artifact is a directly runnable program named exactly `executable`. It is a command-line code-minimap generator. Unless a command-line parse error, input/output error, or TTY-without-input condition described below occurs, it exits with status 0. Normal minimap output and informational output go only to standard output. Diagnostics go only to standard error. Captured/nonterminal output must contain no ANSI color or styling escape sequences.

All text emitted by the program is UTF-8. Every successful minimap row ends with `\n`. Informational text and command-completion scripts also end with `\n`. A successful operation writes nothing to standard error.

## Spec 2

The command-line shape is:

```text
executable [OPTIONS] [FILE] [COMMAND]
```

The main options are:

- `-H <HSCALE>` and `--horizontal-scale <HSCALE>`: an IEEE-754-style floating-point horizontal factor, default `1.0`.
- `-V <VSCALE>` and `--vertical-scale <VSCALE>`: a floating-point vertical factor, default `1.0`.
- `--padding <PADDING>`: a nonnegative, machine-sized decimal integer; absent by default.
- `--encoding <ENCODING>`: `utf8-lossy` or `utf8`, default `utf8-lossy`. These two encoding values are accepted case-insensitively.
- `--version` and `-h`/`--help`, with behavior specified below.

Long value options accept either a separate value or `--name=value`. Short scale options accept separate values and forms such as `-H=2.5`. Value-taking short options are not combinable: forms such as `-HV 2`, `-HV2`, and `-VH2` are parse errors. Options may occur before or after `FILE`; for example, both `-H 2 file` and `file -H 2` are valid. Once a subcommand has begun, main options are not accepted after its arguments.

There is at most one `FILE`. The token `-` is a literal filename, not an alias for standard input. `--` ends option parsing, so `executable -- --horizontal-scale` attempts to open a file literally named `--horizontal-scale`.

## Spec 3

When `FILE` is present, open that path and read it as a byte stream. Otherwise, if standard input is not a terminal, read standard input through end-of-file. Closed/empty redirected standard input is valid and produces no output. File input and redirected standard input use the identical decoding and rendering pipeline.

When no file or subcommand is supplied and standard input is a terminal, do not wait for input. Emit this diagnostic and exit 1:

```text
code-minimap: no input file specified (use -h for help)
```

The line ends with `\n` (a pseudo-terminal may present it as CRLF). A no-argument invocation whose standard input is a closed pipe is successful and silent.

## Spec 4

Input is decoded according to `--encoding`:

- `utf8` is strict UTF-8. Invalid input is an I/O failure with exit status 1 and diagnostic `code-minimap: stream did not contain valid UTF-8\n`. Rendering is streaming; data from fully completed earlier frames may already have been written before a later decode failure, although invalid input near the beginning produces no minimap output.
- `utf8-lossy` decodes valid UTF-8 normally and substitutes U+FFFD for invalid byte sequences, following the usual UTF-8 replacement-decoding behavior. It never fails merely because bytes are malformed.

A UTF-8 BOM is not specially removed; it is decoded as U+FEFF and treated like any other non-whitespace character. NUL is likewise a non-whitespace character. Unicode combining marks and multibyte characters are accepted.

Split decoded input at LF. Remove the LF and, when immediately before it, one CR. Do not create an extra input line after a final LF. Thus an empty stream has zero lines, `"a\n"` has one line, and `"\n"` has one empty line. LF and CRLF therefore render identically for corresponding content.

## Spec 5

Convert every decoded input line into a boundary record `(begin,last)`:

1. Positions are zero-based byte offsets in the UTF-8 encoding of the decoded line, not Unicode scalar counts, grapheme counts, or display-cell widths.
2. `begin` is the byte offset of the first character that is not Unicode whitespace, or the maximum unsigned machine integer if there is none.
3. `last` is the byte offset at which the final non-whitespace character begins, or 0 if there is none. Deliberately use the character's starting offset rather than its full UTF-8 byte length.

After the vertical grouping in Spec 6, a record becomes the half-open interval `[begin,last+1)`. Every position in a valid interval is considered occupied, including internal spaces, tabs, and other whitespace. Leading whitespace therefore controls horizontal position while trailing whitespace is ignored. Tabs are not expanded to tab stops; each ASCII tab occupies one byte while locating later content. Use the Unicode `White_Space` classification for deciding whether a decoded character is whitespace.

For example, ASCII `"  abc  "` ultimately becomes `[2,5)`, and `"a b"` becomes `[0,3)`. An all-whitespace logical row becomes the deliberately inverted sentinel interval `[MAX_UNSIGNED,1)`: it contains no positions, but its numeric end of 1 gives the frame enough extent to emit one U+2800 blank cell at default horizontal scale.

## Spec 6

Apply vertical scaling before packing braille rows. Number physical input lines `i = 0,1,2,...`, and compute:

```text
vertical_key(i) = saturating_unsigned_cast(i * vertical_scale)
```

For ordinary finite nonnegative values this is `floor(i * vertical_scale)`. A negative floating result casts to 0. Consecutive physical lines having the same key are coalesced into one logical row by taking the minimum of all `begin` values and maximum of all `last` values, then constructing `[minimum_begin, maximum_last + 1)`. This forms the bounding interval when any line has content and forms `[MAX_UNSIGNED,1)` when every line in the group is whitespace-only. The numeric key itself is then discarded. In particular, gaps between keys do not insert blank rows, so factors greater than or equal to 1 normally do not expand the output height. A zero or negative vertical factor coalesces all input lines into one logical row.

Take the resulting logical rows in order and divide them into frames of four. A final partial frame is completed with empty logical rows. Each nonempty frame produces exactly one output line. Zero physical input lines produce zero frames and no output.

## Spec 7

Apply horizontal scaling independently to both endpoints of every logical-row interval, including the inverted all-whitespace sentinel:

```text
scaled(x) = saturating_unsigned_cast(x * horizontal_scale)
```

For finite nonnegative factors this is truncation toward zero, equivalently `floor`. A negative result casts to 0; overflow clamps to the largest unsigned integer. Consequently, zero and negative horizontal factors turn every interval into `[0,0)` and each existing frame renders as an empty line containing only its terminating newline. Scaling occurs after vertical coalescing, and may collapse a short interval to empty. It may also widen an interval; content is a solid interval, so widening duplicates occupancy rather than resampling individual source characters. At default scale the whitespace sentinel remains inverted with numeric end 1.

The implementation must preserve floating-point behavior for fractional factors such as `0.001`, `0.01`, `0.25`, `0.5`, `0.987`, `1.234`, `1.5`, `2`, `4`, `10`, and `100`; do not first round a factor to an integer.

## Spec 8

Render each four-row frame as a sequence of 2-column by 4-row Unicode braille cells. Let the scaled intervals for logical rows 0 through 3 be `R0` through `R3`. Unused rows in a partial frame are `[0,0)`. The frame width in source columns is `E = max(R0.end, R1.end, R2.end, R3.end)`, using the numeric end even for an inverted whitespace sentinel. For `x = 0,2,4,...` while `x < E`, emit one cell whose dots are set exactly when these positions are contained in the corresponding intervals:

| Logical row | left column `x` | right column `x+1` |
|---|---:|---:|
| 0 | dot 1, value `0x01` | dot 4, value `0x08` |
| 1 | dot 2, value `0x02` | dot 5, value `0x10` |
| 2 | dot 3, value `0x04` | dot 6, value `0x20` |
| 3 | dot 7, value `0x40` | dot 8, value `0x80` |

Add the values of all occupied dots and emit Unicode scalar `U+2800 + value`. This includes U+2800 BRAILLE PATTERN BLANK when a cell lies before indented content. The unpadded row contains exactly `ceil(E/2)` braille scalars and no ASCII trailing spaces. Append `\n` after it.

## Spec 9

`--padding N` sets a minimum output width of `N` Unicode scalar characters per rendered row, after scaling and braille conversion. If a braille row has fewer than `N` scalars, append ASCII spaces until its length is exactly `N`; if it is already at least `N`, do not truncate it or append anything. `--padding 0` is therefore equivalent to no padding. Padding is applied to every existing output row, including a zero-width row caused by horizontal scale 0. Padding does not invent a row for genuinely empty input.

Examples, with `␠` below denoting one ASCII space and every shown row followed by `\n`:

```text
input "a"                                  => ⠁
input "a\n"                                => ⠁
input "\n"                                 => ⠀
input ""                                   => no bytes
input "aaaa\nbbbb\ncccc\ndddd"               => ⣿⣿
input "aaa\n aa\n  a\n   a"                 => ⠙⢇
input "a\n   \nb\n"                          => ⠅
input "a", -H 2                            => ⠉
input "a", --padding 2                     => ⠁␠
input "abc\ndef", -H 0                     => an empty row: only `\n`
```

## Spec 10

The renderer must stream or otherwise support large inputs without fixed line-width or line-count limits. Required cases include a single 100,000-character ASCII line (roughly 50,000 output cells), a 10,000-line file (roughly 2,500 output rows at default scale), 1,000-line inputs, indentation beyond 200 spaces, and scale 100. It must finish these within normal command-line time limits.

If the output consumer closes a pipe early, treat a broken-pipe write as successful termination: exit 0 and do not print a broken-pipe diagnostic. Output already accepted by the pipe remains valid. Other I/O failures use the rules in Spec 14.

## Spec 11

`executable --version` exits 0, writes nothing to standard error, and writes exactly:

```text
code-minimap 0.6.8
```

The line has a final `\n`.

Both `executable --help` and `executable -h` exit 0, write nothing to standard error, and produce the following main help (a final `\n` is required). The same main help takes precedence when other main-level tokens accompany `--help`, including `--help --padding 2` and `bogus --help`.

```text
A high performance code minimap generator

Usage: executable [OPTIONS] [FILE] [COMMAND]

Commands:
  completion
          Generate shell completion file
  help
          Print this message or the help of the given subcommand(s)

Arguments:
  [FILE]
          File to read

Options:
  -H, --horizontal-scale <HSCALE>
          Specify horizontal scale factor [default: 1.0]
  -V, --vertical-scale <VSCALE>
          Specify vertical scale factor [default: 1.0]
      --padding <PADDING>
          Specify padding width
      --encoding <ENCODING>
          Specify input encoding [default: utf8-lossy] [possible values: utf8-lossy, utf8]
      --version
          Print version
  -h, --help
          Print help
```

## Spec 12

The recognized command names at the main command position are `completion` and `help`. A different lone bare token is the `FILE` positional and is opened as a path; it need not produce an “unknown subcommand” parser diagnostic. A second positional token is rejected before opening the first.

`executable help` exits 0 and displays main help containing the `Commands:` section. `executable help completion` exits 0 and displays completion help. `completion --help` routes to completion help, not main help.

Main help must list command names alone on lines indented by two spaces, as shown in Spec 11; consumers parse that layout to discover commands.

## Spec 13

Command-line syntax and conversion failures exit with status 2, put no content on standard output, and emit a plain-text diagnostic to standard error. Diagnostics follow these exact forms where a literal invocation is shown:

```text
$ executable --horizontal-scale=abc
error: invalid value 'abc' for '--horizontal-scale <HSCALE>': invalid float literal

For more information, try '--help'.

$ executable --padding=abc
error: invalid value 'abc' for '--padding <PADDING>': invalid digit found in string

For more information, try '--help'.

$ executable --encoding invalid
error: invalid value 'invalid' for '--encoding <ENCODING>'
  [possible values: utf8-lossy, utf8]

For more information, try '--help'.

$ executable --unknown-flag
error: unexpected argument '--unknown-flag' found

  tip: to pass '--unknown-flag' as a value, use '-- --unknown-flag'

Usage: executable [OPTIONS] [FILE] [COMMAND]

For more information, try '--help'.
```

The `$ executable ...` lines above are labels and are not output. Each diagnostic itself ends in `\n`. Substitute the actual invalid token in the same template. A missing value says that a value is required and identifies the relevant option. A bad float includes `invalid value 'TOKEN'` and `invalid float literal`; a bad integer includes `invalid value 'TOKEN'` and an integer-parse explanation. Invalid encoding diagnostics list the two lowercase possible values.

A negative numeric token supplied separately, such as `--padding -1` or `--vertical-scale -1`, is parsed as an unexpected argument and includes a `tip:` line. `--padding=-1` reaches unsigned-integer conversion and is an invalid-value error. By contrast, `--vertical-scale=-1` and `--horizontal-scale=-1` are accepted floating-point values and render according to Specs 6 and 7.

For a token that joins the two value-taking short-option letters, the first letter is parsed as the option and everything after it in that token is parsed as that option's attached value. The resulting invalid-float diagnostics are exactly:

```text
$ executable -HV 2
error: invalid value 'V' for '--horizontal-scale <HSCALE>': invalid float literal

For more information, try '--help'.

$ executable -HV2
error: invalid value 'V2' for '--horizontal-scale <HSCALE>': invalid float literal

For more information, try '--help'.

$ executable -VH2
error: invalid value 'H2' for '--vertical-scale <VSCALE>': invalid float literal

For more information, try '--help'.
```

An empty-string positional argument is rejected during command-line parsing rather than opened as a filename. `executable ''` exits 2, writes nothing to standard output, and emits exactly:

```text
error: a value is required for '[FILE]' but none was supplied

For more information, try '--help'.
```

For the specifically supplied second positional and negative-padding tokens, the complete diagnostics are:

```text
$ executable - -
error: unexpected argument '-' found

Usage: executable [OPTIONS] [FILE] [COMMAND]

For more information, try '--help'.

$ executable --padding -5 FILE
error: unexpected argument '-5' found

  tip: to pass '-5' as a value, use '-- -5'

Usage: executable [OPTIONS] [FILE] [COMMAND]

For more information, try '--help'.
```

Again, the `$ executable ...` lines are explanatory labels rather than output.

## Spec 14

Runtime input/output failures exit 1. They are written as `code-minimap: DESCRIPTION\n` on standard error. In particular:

```text
missing path:       code-minimap: No such file or directory (os error 2)
directory as file: code-minimap: Is a directory (os error 21)
invalid strict UTF-8: code-minimap: stream did not contain valid UTF-8
```

Do not include the attempted pathname in these messages. A literal `-` and a nonexistent ordinary filename are both actually opened and consequently fail through the operating-system error path. An empty-string argument is instead rejected during command-line parsing as specified in Spec 13. Successful file and stdin rendering has empty standard error.

## Spec 15

`completion` requires exactly one case-sensitive shell value from this ordered set:

```text
bash, elvish, fish, powershell, zsh
```

Each valid invocation exits 0, writes its complete script only to standard output, and writes nothing to standard error. `executable completion --help` and `executable help completion` describe this command; completion help is:

```text
Generate shell completion file

Usage: executable completion <SHELL>

Arguments:
  <SHELL>
          Target shell name [possible values: bash, elvish, fish, powershell, zsh]

Options:
  -h, --help
          Print help
```

It has a final newline and lists no main options. Missing, invalid, uppercase, and extra shell arguments exit 2 with stdout empty. Required literal diagnostics are:

```text
error: the following required arguments were not provided:
  <SHELL>

Usage: executable completion <SHELL>

For more information, try '--help'.
```

```text
error: invalid value 'invalid-shell' for '<SHELL>'
  [possible values: bash, elvish, fish, powershell, zsh]

For more information, try '--help'.
```

For other invalid values replace `invalid-shell` with the supplied spelling. For a second shell, such as `completion bash zsh`, emit:

```text
error: unexpected argument 'zsh' found

Usage: executable completion <SHELL>

For more information, try '--help'.
```

An option after the shell is also unexpected. For `completion bash --version`, emit exactly:

```text
error: unexpected argument '--version' found

  tip: to pass '--version' as a value, use '-- --version'

Usage: executable completion <SHELL>

For more information, try '--help'.
```

## Spec 16

`executable completion bash` emits exactly the following, including indentation and final newline:

```bash
_code-minimap() {
    local i cur prev opts cmd
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    cmd=""
    opts=""

    for i in ${COMP_WORDS[@]}
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="code__minimap"
                ;;
            code__minimap,completion)
                cmd="code__minimap__completion"
                ;;
            code__minimap,help)
                cmd="code__minimap__help"
                ;;
            code__minimap__help,completion)
                cmd="code__minimap__help__completion"
                ;;
            code__minimap__help,help)
                cmd="code__minimap__help__help"
                ;;
            *)
                ;;
        esac
    done

    case "${cmd}" in
        code__minimap)
            opts="-H -V -h --horizontal-scale --vertical-scale --padding --encoding --version --help [FILE] completion help"
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                --horizontal-scale)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -H)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --vertical-scale)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -V)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --padding)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --encoding)
                    COMPREPLY=($(compgen -W "utf8-lossy utf8" -- "${cur}"))
                    return 0
                    ;;
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
        code__minimap__completion)
            opts="-h --help bash elvish fish powershell zsh"
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 2 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
        code__minimap__help)
            opts="completion help"
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 2 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
        code__minimap__help__completion)
            opts=""
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 3 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
        code__minimap__help__help)
            opts=""
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 3 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
    esac
}

if [[ "${BASH_VERSINFO[0]}" -eq 4 && "${BASH_VERSINFO[1]}" -ge 4 || "${BASH_VERSINFO[0]}" -gt 4 ]]; then
    complete -F _code-minimap -o nosort -o bashdefault -o default code-minimap
else
    complete -F _code-minimap -o bashdefault -o default code-minimap
fi
```

## Spec 17

`executable completion elvish` emits exactly the following. The script begins with one blank line (its first byte is `\n`) and also has a final newline:

```elvish

use builtin;
use str;

set edit:completion:arg-completer[code-minimap] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'code-minimap'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'code-minimap'= {
            cand -H 'Specify horizontal scale factor'
            cand --horizontal-scale 'Specify horizontal scale factor'
            cand -V 'Specify vertical scale factor'
            cand --vertical-scale 'Specify vertical scale factor'
            cand --padding 'Specify padding width'
            cand --encoding 'Specify input encoding'
            cand --version 'Print version'
            cand -h 'Print help'
            cand --help 'Print help'
            cand completion 'Generate shell completion file'
            cand help 'Print this message or the help of the given subcommand(s)'
        }
        &'code-minimap;completion'= {
            cand -h 'Print help'
            cand --help 'Print help'
        }
        &'code-minimap;help'= {
            cand completion 'Generate shell completion file'
            cand help 'Print this message or the help of the given subcommand(s)'
        }
        &'code-minimap;help;completion'= {
        }
        &'code-minimap;help;help'= {
        }
    ]
    $completions[$command]
}
```

## Spec 18

`executable completion zsh` emits exactly the following, including its final newline:

```zsh
#compdef code-minimap

autoload -U is-at-least

_code-minimap() {
    typeset -A opt_args
    typeset -a _arguments_options
    local ret=1

    if is-at-least 5.2; then
        _arguments_options=(-s -S -C)
    else
        _arguments_options=(-s -C)
    fi

    local context curcontext="$curcontext" state line
    _arguments "${_arguments_options[@]}" : \
'-H+[Specify horizontal scale factor]:HSCALE:_default' \
'--horizontal-scale=[Specify horizontal scale factor]:HSCALE:_default' \
'-V+[Specify vertical scale factor]:VSCALE:_default' \
'--vertical-scale=[Specify vertical scale factor]:VSCALE:_default' \
'--padding=[Specify padding width]:PADDING:_default' \
'--encoding=[Specify input encoding]:ENCODING:(utf8-lossy utf8)' \
'--version[Print version]' \
'-h[Print help]' \
'--help[Print help]' \
'::file -- File to read:_files' \
":: :_code-minimap_commands" \
"*::: :->code-minimap" \
&& ret=0
    case $state in
    (code-minimap)
        words=($line[2] "${words[@]}")
        (( CURRENT += 1 ))
        curcontext="${curcontext%:*:*}:code-minimap-command-$line[2]:"
        case $line[2] in
            (completion)
_arguments "${_arguments_options[@]}" : \
'-h[Print help]' \
'--help[Print help]' \
':shell -- Target shell name:(bash elvish fish powershell zsh)' \
&& ret=0
;;
(help)
_arguments "${_arguments_options[@]}" : \
":: :_code-minimap__help_commands" \
"*::: :->help" \
&& ret=0

    case $state in
    (help)
        words=($line[1] "${words[@]}")
        (( CURRENT += 1 ))
        curcontext="${curcontext%:*:*}:code-minimap-help-command-$line[1]:"
        case $line[1] in
            (completion)
_arguments "${_arguments_options[@]}" : \
&& ret=0
;;
(help)
_arguments "${_arguments_options[@]}" : \
&& ret=0
;;
        esac
    ;;
esac
;;
        esac
    ;;
esac
}

(( $+functions[_code-minimap_commands] )) ||
_code-minimap_commands() {
    local commands; commands=(
'completion:Generate shell completion file' \
'help:Print this message or the help of the given subcommand(s)' \
    )
    _describe -t commands 'code-minimap commands' commands "$@"
}
(( $+functions[_code-minimap__completion_commands] )) ||
_code-minimap__completion_commands() {
    local commands; commands=()
    _describe -t commands 'code-minimap completion commands' commands "$@"
}
(( $+functions[_code-minimap__help_commands] )) ||
_code-minimap__help_commands() {
    local commands; commands=(
'completion:Generate shell completion file' \
'help:Print this message or the help of the given subcommand(s)' \
    )
    _describe -t commands 'code-minimap help commands' commands "$@"
}
(( $+functions[_code-minimap__help__completion_commands] )) ||
_code-minimap__help__completion_commands() {
    local commands; commands=()
    _describe -t commands 'code-minimap help completion commands' commands "$@"
}
(( $+functions[_code-minimap__help__help_commands] )) ||
_code-minimap__help__help_commands() {
    local commands; commands=()
    _describe -t commands 'code-minimap help help commands' commands "$@"
}

if [ "$funcstack[1]" = "_code-minimap" ]; then
    _code-minimap "$@"
else
    compdef _code-minimap code-minimap
fi
```

## Spec 19

`executable completion fish` emits exactly the following, using literal tab characters for the indentation shown inside the functions and a final newline:

```fish
# Print an optspec for argparse to handle cmd's options that are independent of any subcommand.
function __fish_code_minimap_global_optspecs
	string join \n H/horizontal-scale= V/vertical-scale= padding= encoding= version h/help
end

function __fish_code_minimap_needs_command
	# Figure out if the current invocation already has a command.
	set -l cmd (commandline -opc)
	set -e cmd[1]
	argparse -s (__fish_code_minimap_global_optspecs) -- $cmd 2>/dev/null
	or return
	if set -q argv[1]
		# Also print the command, so this can be used to figure out what it is.
		echo $argv[1]
		return 1
	end
	return 0
end

function __fish_code_minimap_using_subcommand
	set -l cmd (__fish_code_minimap_needs_command)
	test -z "$cmd"
	and return 1
	contains -- $cmd[1] $argv
end

complete -c code-minimap -n "__fish_code_minimap_needs_command" -s H -l horizontal-scale -d 'Specify horizontal scale factor' -r
complete -c code-minimap -n "__fish_code_minimap_needs_command" -s V -l vertical-scale -d 'Specify vertical scale factor' -r
complete -c code-minimap -n "__fish_code_minimap_needs_command" -l padding -d 'Specify padding width' -r
complete -c code-minimap -n "__fish_code_minimap_needs_command" -l encoding -d 'Specify input encoding' -r -f -a "{utf8-lossy\t'',utf8\t''}"
complete -c code-minimap -n "__fish_code_minimap_needs_command" -l version -d 'Print version'
complete -c code-minimap -n "__fish_code_minimap_needs_command" -s h -l help -d 'Print help'
complete -c code-minimap -n "__fish_code_minimap_needs_command" -a "completion" -d 'Generate shell completion file'
complete -c code-minimap -n "__fish_code_minimap_needs_command" -a "help" -d 'Print this message or the help of the given subcommand(s)'
complete -c code-minimap -n "__fish_code_minimap_using_subcommand completion" -s h -l help -d 'Print help'
complete -c code-minimap -n "__fish_code_minimap_using_subcommand help; and not __fish_seen_subcommand_from completion help" -f -a "completion" -d 'Generate shell completion file'
complete -c code-minimap -n "__fish_code_minimap_using_subcommand help; and not __fish_seen_subcommand_from completion help" -f -a "help" -d 'Print this message or the help of the given subcommand(s)'
```

## Spec 20

`executable completion powershell` emits exactly the following. Like the Elvish script, it begins with one blank line and ends with a newline:

```powershell

using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'code-minimap' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'code-minimap'
        for ($i = 1; $i -lt $commandElements.Count; $i++) {
            $element = $commandElements[$i]
            if ($element -isnot [StringConstantExpressionAst] -or
                $element.StringConstantType -ne [StringConstantType]::BareWord -or
                $element.Value.StartsWith('-') -or
                $element.Value -eq $wordToComplete) {
                break
        }
        $element.Value
    }) -join ';'

    $completions = @(switch ($command) {
        'code-minimap' {
            [CompletionResult]::new('-H', '-H ', [CompletionResultType]::ParameterName, 'Specify horizontal scale factor')
            [CompletionResult]::new('--horizontal-scale', '--horizontal-scale', [CompletionResultType]::ParameterName, 'Specify horizontal scale factor')
            [CompletionResult]::new('-V', '-V ', [CompletionResultType]::ParameterName, 'Specify vertical scale factor')
            [CompletionResult]::new('--vertical-scale', '--vertical-scale', [CompletionResultType]::ParameterName, 'Specify vertical scale factor')
            [CompletionResult]::new('--padding', '--padding', [CompletionResultType]::ParameterName, 'Specify padding width')
            [CompletionResult]::new('--encoding', '--encoding', [CompletionResultType]::ParameterName, 'Specify input encoding')
            [CompletionResult]::new('--version', '--version', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('completion', 'completion', [CompletionResultType]::ParameterValue, 'Generate shell completion file')
            [CompletionResult]::new('help', 'help', [CompletionResultType]::ParameterValue, 'Print this message or the help of the given subcommand(s)')
            break
        }
        'code-minimap;completion' {
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'code-minimap;help' {
            [CompletionResult]::new('completion', 'completion', [CompletionResultType]::ParameterValue, 'Generate shell completion file')
            [CompletionResult]::new('help', 'help', [CompletionResultType]::ParameterValue, 'Print this message or the help of the given subcommand(s)')
            break
        }
        'code-minimap;help;completion' {
            break
        }
        'code-minimap;help;help' {
            break
        }
    })

    $completions.Where{ $_.CompletionText -like "$wordToComplete*" } |
        Sort-Object -Property ListItemText
}
```
