# Clarified executable specification

The required artifact is a regular executable file named `executable`. It is a terminal-oriented nonsense-activity generator compatible with the behavior below. All text is UTF-8. Unless a section says otherwise, normal output goes to stdout, diagnostic parse errors go to stderr, successful commands return 0, and parse errors return a nonzero status. Blocks introduced as exact output end with one newline and permit no extra stdout/stderr text.

## Spec 1

The command-line interface is named `executable` for usage/error rendering, while its product name is `genact`. It accepts:

- `-l`, `--list-modules`
- repeatable `-m MODULES`, `--modules MODULES`
- `-s SPEED_FACTOR`, `--speed-factor SPEED_FACTOR` (default `1`)
- `-i INSTANT_PRINT_LINES`, `--instant-print-lines INSTANT_PRINT_LINES` (default `0`)
- `--inhibit`
- `--exit-after-time EXIT_AFTER_TIME`
- `--exit-after-modules EXIT_AFTER_MODULES`
- `--print-completions SHELL`
- `--print-manpage`
- `-h`, `--help`
- `-V`, `--version`

The only accepted module names, in canonical order, are: `ansible`, `bootlog`, `botnet`, `bruteforce`, `cargo`, `cc`, `composer`, `cryptomining`, `docker_build`, `docker_image_rm`, `download`, `julia`, `kernel_compile`, `memdump`, `mkinitcpio`, `rkhunter`, `simcity`, `terraform`, `uv`, `weblog`, and `wpt`. A comma-separated value is one value and is not split. Repeating `--modules` is the way to supply several modules, and repeated identical values are legal and are not an error.

## Spec 2

`--version` and `-V` produce exactly:

```text
genact 1.5.1
```

`--list-modules` and `-l` produce exactly the following. This action takes precedence over a valid `--modules` selection and still lists all modules.

```text
Available modules:
  ansible
  bootlog
  botnet
  bruteforce
  cargo
  cc
  composer
  cryptomining
  docker_build
  docker_image_rm
  download
  julia
  kernel_compile
  memdump
  mkinitcpio
  rkhunter
  simcity
  terraform
  uv
  weblog
  wpt
```

## Spec 3

Help is sensitive to the `COLUMNS` environment variable. With `COLUMNS=80`, `--help` and `-h` produce exactly:

```text
A nonsense activity generator

Usage: executable [OPTIONS]

Options:
  -l, --list-modules
          List available modules
  -m, --modules <MODULES>
          Run only these modules [possible values: ansible, bootlog, botnet,
          bruteforce, cargo, cc, composer, cryptomining, docker_build,
          docker_image_rm, download, julia, kernel_compile, memdump, mkinitcpio,
          rkhunter, simcity, terraform, uv, weblog, wpt]
  -s, --speed-factor <SPEED_FACTOR>
          Global speed factor [default: 1]
  -i, --instant-print-lines <INSTANT_PRINT_LINES>
          Instantly print this many lines [default: 0]
      --inhibit
          Keep the computer awake and the display on while genact is running
      --exit-after-time <EXIT_AFTER_TIME>
          Exit after running for this long (format example: 2h10min)
      --exit-after-modules <EXIT_AFTER_MODULES>
          Exit after running this many modules
      --print-completions <shell>
          Generate completion file for a shell [possible values: bash, elvish,
          fish, powershell, zsh]
      --print-manpage
          Generate man page
  -h, --help
          Print help
  -V, --version
          Print version
```

With `COLUMNS=120`, `--help` produces exactly:

```text
A nonsense activity generator

Usage: executable [OPTIONS]

Options:
  -l, --list-modules
          List available modules
  -m, --modules <MODULES>
          Run only these modules [possible values: ansible, bootlog, botnet, bruteforce, cargo, cc, composer,
          cryptomining, docker_build, docker_image_rm, download, julia, kernel_compile, memdump, mkinitcpio, rkhunter,
          simcity, terraform, uv, weblog, wpt]
  -s, --speed-factor <SPEED_FACTOR>
          Global speed factor [default: 1]
  -i, --instant-print-lines <INSTANT_PRINT_LINES>
          Instantly print this many lines [default: 0]
      --inhibit
          Keep the computer awake and the display on while genact is running
      --exit-after-time <EXIT_AFTER_TIME>
          Exit after running for this long (format example: 2h10min)
      --exit-after-modules <EXIT_AFTER_MODULES>
          Exit after running this many modules
      --print-completions <shell>
          Generate completion file for a shell [possible values: bash, elvish, fish, powershell, zsh]
      --print-manpage
          Generate man page
  -h, --help
          Print help
  -V, --version
          Print version
```

## Spec 4

`SPEED_FACTOR` is a floating-point multiplier for output speed. Values greater than or equal to `0.01` are accepted, including fractional values such as `0.1` and `0.5`, ordinary large values such as `10000`, and `999999999`; values below `0.01` are rejected. Increasing it must materially reduce per-line delays without overflow or division-by-zero behavior. In particular, `cc` at factor 5 emits more than 20 lines during a one-second run, at factor 100 emits more than 100 lines during 500 ms, and at very large factors completes a full 100-plus-line run within a few seconds.

`INSTANT_PRINT_LINES` is an unsigned decimal integer. Zero and values as large as `999999999` are valid. The first N generated output lines across module activity are written and flushed without their normal delay. Thus 50 lines must be observable within about 0.1 seconds even at speed factor `0.01`; asking for more immediate lines than a module produces is harmless.

`EXIT_AFTER_MODULES` is a positive decimal integer. It counts completed module invocations, not distinct selected module definitions. One means one invocation; duplicate selections remain legal. Once a requested exit condition is met, print `Saving work to disk...` and return 0. With multiple selected modules, choose invocations from the supplied pool repeatedly. In a 20-invocation run whose pool is `cargo` and `cc`, both occur, cargo contributes more than 20 lines containing `Downloading`, `Compiling`, or `Finished`, `cc` contributes more than 100 lines containing `gcc -c`, and total output exceeds 100 lines.

`EXIT_AFTER_TIME` accepts nonnegative human-duration strings, including `0s`, `10ms`, `100ms`, `200ms`, `500ms`, `1s`, and `2s` (and compound forms such as `2h10min`). `0s` exits in under one second and still prints the save message. A nonzero time limit is cooperative and does not preempt an in-progress module delay. In particular, each of these slow-`cc` invocations is still running after one second, has not printed the save message, and has produced the stated number of compile lines at that point:

- `-m cc --speed-factor 0.01 --exit-after-time 500ms`: one line;
- `-m cc --speed-factor 0.01 --exit-after-time 100ms --exit-after-modules 999999999`: one line;
- `-m cc -s 0.01 -i 50 --exit-after-time 100ms`: 51 lines;
- `-m cc -s 0.01 --exit-after-time 100ms`: one line.

Thus a time limit becoming due during the module does not imply prompt process termination, and adding a later module-count limit does not make it preempt the current delay. When a module does observe the time limit, it may emit a partial sequence and any module-specific completion line identified below before the common save message.

## Spec 5

Invalid command lines return nonzero and print exactly the relevant diagnostic below to stderr. No diagnostic is printed to stdout. The literal value is substituted only where stated.

For `--speed-factor 0`, `0.005`, or another numeric value below `0.01`:

```text
error: invalid value 'VALUE' for '--speed-factor <SPEED_FACTOR>': Speed factor must be larger than 0.01

For more information, try '--help'.
```

For `--speed-factor abc`:

```text
error: invalid value 'abc' for '--speed-factor <SPEED_FACTOR>': invalid float literal

For more information, try '--help'.
```

For a negative value token such as `--speed-factor -5`, `--instant-print-lines -1`, `--exit-after-modules -1`, or `--exit-after-time -5s`, the diagnostic treats the leading numeric portion as the unexpected argument. The block below is exact for the speed and time examples; replace `-5` with `-1` for either integer-option example:

```text
error: unexpected argument '-5' found

Usage: executable [OPTIONS]

For more information, try '--help'.
```

For `--exit-after-modules 0`:

```text
error: invalid value '0' for '--exit-after-modules <EXIT_AFTER_MODULES>': Must be larger than 0

For more information, try '--help'.
```

For `--exit-after-modules xyz`:

```text
error: invalid value 'xyz' for '--exit-after-modules <EXIT_AFTER_MODULES>': invalid digit found in string

For more information, try '--help'.
```

For `--instant-print-lines abc`:

```text
error: invalid value 'abc' for '--instant-print-lines <INSTANT_PRINT_LINES>': invalid digit found in string

For more information, try '--help'.
```

For `--exit-after-time invalid` or `notaduration`, substitute that input for `VALUE`:

```text
error: invalid value 'VALUE' for '--exit-after-time <EXIT_AFTER_TIME>': expected number at 0

For more information, try '--help'.
```

For an unknown option such as `--unknown-flag`:

```text
error: unexpected argument '--unknown-flag' found

Usage: executable [OPTIONS]

For more information, try '--help'.
```

## Spec 6

Missing option values use these exact stderr forms:

`--speed-factor` alone:

```text
error: a value is required for '--speed-factor <SPEED_FACTOR>' but none was supplied

For more information, try '--help'.
```

`--exit-after-time` alone:

```text
error: a value is required for '--exit-after-time <EXIT_AFTER_TIME>' but none was supplied

For more information, try '--help'.
```

`--print-completions` alone:

```text
error: a value is required for '--print-completions <shell>' but none was supplied
  [possible values: bash, elvish, fish, powershell, zsh]

For more information, try '--help'.
```

`--modules` alone and `--modules ""` both produce:

```text
error: a value is required for '--modules <MODULES>' but none was supplied
  [possible values: ansible, bootlog, botnet, bruteforce, cargo, cc, composer, cryptomining, docker_build, docker_image_rm, download, julia, kernel_compile, memdump, mkinitcpio, rkhunter, simcity, terraform, uv, weblog, wpt]

For more information, try '--help'.
```

An invalid module value `VALUE` produces:

```text
error: invalid value 'VALUE' for '--modules <MODULES>'
  [possible values: ansible, bootlog, botnet, bruteforce, cargo, cc, composer, cryptomining, docker_build, docker_image_rm, download, julia, kernel_compile, memdump, mkinitcpio, rkhunter, simcity, terraform, uv, weblog, wpt]

For more information, try '--help'.
```

If any one of several repeated module values is invalid, reject the whole command using that value. For the particular invalid value `kernel_compile,does_not_exist`, insert this extra paragraph between the possible-values line and the final help paragraph:

```text
  tip: a similar value exists: 'kernel_compile'
```

The invalid completion shell `tcsh` returns status 2 and produces no stdout and exactly this stderr, including the suggestion paragraph:

```text
error: invalid value 'tcsh' for '--print-completions <shell>'
  [possible values: bash, elvish, fish, powershell, zsh]

  tip: a similar value exists: 'zsh'

For more information, try '--help'.
```

## Spec 7

`--print-manpage` returns 0 and prints exactly this roff document:

```roff
.ie \n(.g .ds Aq \(aq
.el .ds Aq '
.TH genact 1  "genact 1.5.1" 
.SH NAME
genact \- A nonsense activity generator
.SH SYNOPSIS
\fBgenact\fR [\fB\-l\fR|\fB\-\-list\-modules\fR] [\fB\-m\fR|\fB\-\-modules\fR] [\fB\-s\fR|\fB\-\-speed\-factor\fR] [\fB\-i\fR|\fB\-\-instant\-print\-lines\fR] [\fB\-\-inhibit\fR] [\fB\-\-exit\-after\-time\fR] [\fB\-\-exit\-after\-modules\fR] [\fB\-\-print\-completions\fR] [\fB\-\-print\-manpage\fR] [\fB\-h\fR|\fB\-\-help\fR] [\fB\-V\fR|\fB\-\-version\fR] 
.SH DESCRIPTION
A nonsense activity generator
.SH OPTIONS
.TP
\fB\-l\fR, \fB\-\-list\-modules\fR
List available modules
.TP
\fB\-m\fR, \fB\-\-modules\fR \fI<MODULES>\fR
Run only these modules
.br

.br
\fIPossible values:\fR
.RS 14
.IP \(bu 2
ansible
.IP \(bu 2
bootlog
.IP \(bu 2
botnet
.IP \(bu 2
bruteforce
.IP \(bu 2
cargo
.IP \(bu 2
cc
.IP \(bu 2
composer
.IP \(bu 2
cryptomining
.IP \(bu 2
docker_build
.IP \(bu 2
docker_image_rm
.IP \(bu 2
download
.IP \(bu 2
julia
.IP \(bu 2
kernel_compile
.IP \(bu 2
memdump
.IP \(bu 2
mkinitcpio
.IP \(bu 2
rkhunter
.IP \(bu 2
simcity
.IP \(bu 2
terraform
.IP \(bu 2
uv
.IP \(bu 2
weblog
.IP \(bu 2
wpt
.RE
.TP
\fB\-s\fR, \fB\-\-speed\-factor\fR \fI<SPEED_FACTOR>\fR [default: 1]
Global speed factor
.TP
\fB\-i\fR, \fB\-\-instant\-print\-lines\fR \fI<INSTANT_PRINT_LINES>\fR [default: 0]
Instantly print this many lines
.TP
\fB\-\-inhibit\fR
Keep the computer awake and the display on while genact is running
.TP
\fB\-\-exit\-after\-time\fR \fI<EXIT_AFTER_TIME>\fR
Exit after running for this long (format example: 2h10min)
.TP
\fB\-\-exit\-after\-modules\fR \fI<EXIT_AFTER_MODULES>\fR
Exit after running this many modules
.TP
\fB\-\-print\-completions\fR \fI<shell>\fR
Generate completion file for a shell
.br

.br
\fIPossible values:\fR
.RS 14
.IP \(bu 2
bash
.IP \(bu 2
elvish
.IP \(bu 2
fish
.IP \(bu 2
powershell
.IP \(bu 2
zsh
.RE
.TP
\fB\-\-print\-manpage\fR
Generate man page
.TP
\fB\-h\fR, \fB\-\-help\fR
Print help
.TP
\fB\-V\fR, \fB\-\-version\fR
Print version
.SH VERSION
v1.5.1
.SH AUTHORS
Sven\-Hendrik Haase <svenstaro@gmail.com>
```

## Spec 8

`--print-completions bash` returns 0 and prints exactly:

```bash
_genact() {
    local i cur prev opts cmd
    COMPREPLY=()
    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
        cur="$2"
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
    fi
    prev="$3"
    cmd=""
    opts=""

    for i in "${COMP_WORDS[@]:0:COMP_CWORD}"
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="genact"
                ;;
            *)
                ;;
        esac
    done

    case "${cmd}" in
        genact)
            opts="-l -m -s -i -h -V --list-modules --modules --speed-factor --instant-print-lines --inhibit --exit-after-time --exit-after-modules --print-completions --print-manpage --help --version"
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                --modules)
                    COMPREPLY=($(compgen -W "ansible bootlog botnet bruteforce cargo cc composer cryptomining docker_build docker_image_rm download julia kernel_compile memdump mkinitcpio rkhunter simcity terraform uv weblog wpt" -- "${cur}"))
                    return 0
                    ;;
                -m)
                    COMPREPLY=($(compgen -W "ansible bootlog botnet bruteforce cargo cc composer cryptomining docker_build docker_image_rm download julia kernel_compile memdump mkinitcpio rkhunter simcity terraform uv weblog wpt" -- "${cur}"))
                    return 0
                    ;;
                --speed-factor)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -s)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --instant-print-lines)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -i)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --exit-after-time)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --exit-after-modules)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --print-completions)
                    COMPREPLY=($(compgen -W "bash elvish fish powershell zsh" -- "${cur}"))
                    return 0
                    ;;
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
    complete -F _genact -o nosort -o bashdefault -o default genact
else
    complete -F _genact -o bashdefault -o default genact
fi
```

## Spec 9

`--print-completions zsh` returns 0 and prints exactly:

```zsh
#compdef genact

autoload -U is-at-least

_genact() {
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
'*-m+[Run only these modules]:MODULES:(ansible bootlog botnet bruteforce cargo cc composer cryptomining docker_build docker_image_rm download julia kernel_compile memdump mkinitcpio rkhunter simcity terraform uv weblog wpt)' \
'*--modules=[Run only these modules]:MODULES:(ansible bootlog botnet bruteforce cargo cc composer cryptomining docker_build docker_image_rm download julia kernel_compile memdump mkinitcpio rkhunter simcity terraform uv weblog wpt)' \
'-s+[Global speed factor]:SPEED_FACTOR:_default' \
'--speed-factor=[Global speed factor]:SPEED_FACTOR:_default' \
'-i+[Instantly print this many lines]:INSTANT_PRINT_LINES:_default' \
'--instant-print-lines=[Instantly print this many lines]:INSTANT_PRINT_LINES:_default' \
'--exit-after-time=[Exit after running for this long (format example\: 2h10min)]:EXIT_AFTER_TIME:_default' \
'--exit-after-modules=[Exit after running this many modules]:EXIT_AFTER_MODULES:_default' \
'--print-completions=[Generate completion file for a shell]:shell:(bash elvish fish powershell zsh)' \
'-l[List available modules]' \
'--list-modules[List available modules]' \
'--inhibit[Keep the computer awake and the display on while genact is running]' \
'--print-manpage[Generate man page]' \
'-h[Print help]' \
'--help[Print help]' \
'-V[Print version]' \
'--version[Print version]' \
&& ret=0
}

(( $+functions[_genact_commands] )) ||
_genact_commands() {
    local commands; commands=()
    _describe -t commands 'genact commands' commands "$@"
}

if [ "$funcstack[1]" = "_genact" ]; then
    _genact "$@"
else
    compdef _genact genact
fi
```

## Spec 10

`--print-completions fish` returns 0 and prints exactly:

```fish
complete -c genact -s m -l modules -d 'Run only these modules' -r -f -a "ansible\t''
bootlog\t''
botnet\t''
bruteforce\t''
cargo\t''
cc\t''
composer\t''
cryptomining\t''
docker_build\t''
docker_image_rm\t''
download\t''
julia\t''
kernel_compile\t''
memdump\t''
mkinitcpio\t''
rkhunter\t''
simcity\t''
terraform\t''
uv\t''
weblog\t''
wpt\t''"
complete -c genact -s s -l speed-factor -d 'Global speed factor' -r
complete -c genact -s i -l instant-print-lines -d 'Instantly print this many lines' -r
complete -c genact -l exit-after-time -d 'Exit after running for this long (format example: 2h10min)' -r
complete -c genact -l exit-after-modules -d 'Exit after running this many modules' -r
complete -c genact -l print-completions -d 'Generate completion file for a shell' -r -f -a "bash\t''
elvish\t''
fish\t''
powershell\t''
zsh\t''"
complete -c genact -s l -l list-modules -d 'List available modules'
complete -c genact -l inhibit -d 'Keep the computer awake and the display on while genact is running'
complete -c genact -l print-manpage -d 'Generate man page'
complete -c genact -s h -l help -d 'Print help'
complete -c genact -s V -l version -d 'Print version'
```

## Spec 11

`--print-completions elvish` has a leading blank line, then exactly:

```elvish
use builtin;
use str;

set edit:completion:arg-completer[genact] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'genact'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'genact'= {
            cand -m 'Run only these modules'
            cand --modules 'Run only these modules'
            cand -s 'Global speed factor'
            cand --speed-factor 'Global speed factor'
            cand -i 'Instantly print this many lines'
            cand --instant-print-lines 'Instantly print this many lines'
            cand --exit-after-time 'Exit after running for this long (format example: 2h10min)'
            cand --exit-after-modules 'Exit after running this many modules'
            cand --print-completions 'Generate completion file for a shell'
            cand -l 'List available modules'
            cand --list-modules 'List available modules'
            cand --inhibit 'Keep the computer awake and the display on while genact is running'
            cand --print-manpage 'Generate man page'
            cand -h 'Print help'
            cand --help 'Print help'
            cand -V 'Print version'
            cand --version 'Print version'
        }
    ]
    $completions[$command]
}
```

## Spec 12

`--print-completions powershell` has a leading blank line, then exactly:

```powershell
using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'genact' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'genact'
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
        'genact' {
            [CompletionResult]::new('-m', '-m', [CompletionResultType]::ParameterName, 'Run only these modules')
            [CompletionResult]::new('--modules', '--modules', [CompletionResultType]::ParameterName, 'Run only these modules')
            [CompletionResult]::new('-s', '-s', [CompletionResultType]::ParameterName, 'Global speed factor')
            [CompletionResult]::new('--speed-factor', '--speed-factor', [CompletionResultType]::ParameterName, 'Global speed factor')
            [CompletionResult]::new('-i', '-i', [CompletionResultType]::ParameterName, 'Instantly print this many lines')
            [CompletionResult]::new('--instant-print-lines', '--instant-print-lines', [CompletionResultType]::ParameterName, 'Instantly print this many lines')
            [CompletionResult]::new('--exit-after-time', '--exit-after-time', [CompletionResultType]::ParameterName, 'Exit after running for this long (format example: 2h10min)')
            [CompletionResult]::new('--exit-after-modules', '--exit-after-modules', [CompletionResultType]::ParameterName, 'Exit after running this many modules')
            [CompletionResult]::new('--print-completions', '--print-completions', [CompletionResultType]::ParameterName, 'Generate completion file for a shell')
            [CompletionResult]::new('-l', '-l', [CompletionResultType]::ParameterName, 'List available modules')
            [CompletionResult]::new('--list-modules', '--list-modules', [CompletionResultType]::ParameterName, 'List available modules')
            [CompletionResult]::new('--inhibit', '--inhibit', [CompletionResultType]::ParameterName, 'Keep the computer awake and the display on while genact is running')
            [CompletionResult]::new('--print-manpage', '--print-manpage', [CompletionResultType]::ParameterName, 'Generate man page')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('-V', '-V ', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('--version', '--version', [CompletionResultType]::ParameterName, 'Print version')
            break
        }
    })

    $completions.Where{ $_.CompletionText -like "$wordToComplete*" } |
        Sort-Object -Property ListItemText
}
```

## Spec 13

Activity output is flushed progressively rather than held until process exit. Progress displays may use carriage returns and ANSI control sequences, but their meaningful text remains observable in terminal snapshots. Keep lines containing critical regex-visible records reasonably short so an 80-column terminal does not split tokens.

Most modules also work when stdout is captured through a pipe, but `download` and `docker_build` are terminal-width-dependent exceptions. With captured stdout, `download` writes no activity and exits with status 101 after writing this panic to stderr:

```text

thread 'main' (THREAD_ID) panicked at src/io.rs:<error location>:
Couldn't get terminal width. Is an interactive terminal attached?
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

`THREAD_ID` is a decimal runtime thread identifier. With `--inhibit`, the warning specified below is written to stdout before the same `download` panic and status 101. A captured `docker_build` run can first emit Docker progress and then fail through the same terminal-width panic with status 101; one observed run reached `Step 3/32` before doing so. These two modules therefore must be exercised through a terminal/PTY when successful module output is required, rather than through a captured stdout pipe.

On `--inhibit`, attempt to keep the machine/display awake before module output. In the Linux headless evaluation environment this attempt must fail harmlessly and write this line to stdout before continuing normally:

```text
WARN: failed to set up idle inhibition: system: I/O error: No such file or directory (os error 2)
```

This behavior applies to at least `bootlog`, `memdump`, `download`, `weblog`, `cargo`, `botnet`, `cryptomining`, `docker_image_rm`, `rkhunter`, `simcity`, and `terraform`. For pipe-safe modules the inhibition failure does not change the successful exit status. For captured `download`, the warning itself is harmless, but the subsequent terminal-width panic determines status 101 as described above.

## Spec 14

The `cc` module emits at least 100 compile-command lines in a complete run. Every compile line starts with either `gcc -c ` or `clang -c `, contains exactly one ` -c ` and exactly one ` -o `, and ends in a `.o` output path. Each of the first 30 lines includes at least one include option rooted in a kernel-style directory (`-Idrivers/`, `-Iarch/`, `-Isound/`, `-Inet/`, `-Ifs/`, `-Ikernel/`, `-Ilib/`, `-Isecurity/`, or `-Itools/`) and the output after ` -o ` begins with one of those directory names. Include substantial directory variety: visible `.o` references must cover at least three matches among `drivers/`, `sound/`, `net/`, `fs/`, `lib/`, `kernel/`, and `tools/`. A safe example is `gcc -c drivers/net/ethernet/example.c -Idrivers/net -Iinclude -o drivers/net/ethernet/example.o`.

The first compile line is emitted and flushed before any normal delay, so even factor `0.01` yields recognizable output before a five-second capture timeout. At speed 10 or more, a complete run has at least 50 nonempty lines; at extreme factors it has between 101 and 9,999 total lines. After the requested module/time exit, append the common save message.

## Spec 15

The `bootlog` module outputs between 50 and 200 boot-log records per complete run (at least 20 must remain visible), uses ANSI SGR formatting such as bold (`ESC[1m`), red (`ESC[31m`), and reset (`ESC[0m`), and includes at least three of `ACPI`, `CPU`, `kernel`, `zone`, `memory`, `PCI`, and `IRQ`. PTY output also contains at least five `0x` hexadecimal addresses and at least two boot terms from `BIOS`, `ACPI`, `CPU`, `PCI`, `IOAPIC`, `mem`, `zone`, `pages`, `kernel`, `IRQ`, `USB`, `SCSI`, `Detected`, `MHz`, and `enabled`.

Boot records are sampled from a larger randomized source rather than from a fixed canonical subset. Consecutive reference runs began with different records—`NMI watchdog: Enabled. Permanently consumes one hw-PMU counter.` and `Console: colour dummy device 80x25`—and the first run continued with records such as `Reserving Intel graphics memory at 0x00000000ae000000-0x00000000afffffff` and `ACPI: LAPIC_NMI (acpi_id[0x01] high edge lint[0x1])`. Accordingly, the run must satisfy the count, formatting, address, and boot-term requirements above, but its first 50 records need not match a closed list of exact messages.

At speed factor 100, the run finishes within 12 seconds and produces more than 500 bytes, then the save message.

## Spec 16

The `memdump` module prints at least 50 hexdump records (50–200 is the intended range). Each record is exactly structurally equivalent to:

```text
0000000000001000  41 42 43 44 45 46 47 48  49 4a 4b 4c 4d 4e 4f 50  |ABCDEFGHIJKLMNOP|
```

Addresses are 16 lowercase hexadecimal digits followed by two spaces, start on a 16-byte boundary, and increase by exactly `0x10` between consecutive records. The data portion has 16 lowercase two-digit hex bytes: eight byte-and-space groups, an extra separator space, then eight more byte-and-space groups. The final ASCII column is exactly 16 characters between `|` delimiters, mapping bytes `0x21`–`0x7e` to their characters and all other bytes, including the space byte `0x20`, to `.`, with letters or digits visible in at least one record. At least ten valid records and at least 160 parsed byte tokens must be observable in a terminal snapshot, followed by the save message.

## Spec 17

When run through a terminal/PTY, the `download` module completes at least 2, normally 3–10, distinct files. File names use a word/hyphen stem and one of: `gif`, `mkv`, `webm`, `mp4`, `html`, `php`, `md`, `png`, `jpg`, `opus`, `ogg`, `mp3`, `flac`, `iso`, `zip`, `rar`, `tar.gz`, `tar.bz2`, `tar.xz`, `tar.zstd`, `deb`, `rpm`, or `exe`. It visibly updates progress and leaves completed records containing all of:

- a file name;
- `100%[================` (with a closing `]`, and at least five consecutive `=` characters);
- a positive transfer speed using `B/s`, `KiB/s`, `MiB/s`, or a larger analogous unit, with the numeric value immediately adjacent to the unit (for example, `39.25MiB/s`, with no intervening whitespace) and at least one specifically in `MiB/s`;
- a lowercase ETA such as `eta 0s` or `eta 1s`.

At least two lines contain `100%`, and the final terminal screen contains the save message. Complete quickly enough at speed factor 50 to be stable within five seconds.

## Spec 18

The `weblog` module prints at least ten Apache/nginx combined-access-style records before saving. Each has this field shape on one logical line:

```text
IP - - [date-text] "GET /path/to/file.ext HTTP/1.0" STATUS BYTES "referrer" "user-agent"
```

`IP` is syntactically valid lowercase IPv4 or IPv6 text (IPv4 octets are 0–255); `STATUS` is one of 200, 201, 400, 401, 403, 404, 500, 502, or 503; `BYTES` is decimal; paths start with `/`, and at least five paths have a filename extension. Each final quoted user-agent is nonempty and at least five of the first twenty contain one of `Mozilla`, `Chrome`, `Safari`, `Firefox`, `Opera`, `MSIE`, or `Edge`. Finish with the save message.

## Spec 19

The `cargo` module selects at least ten distinct crate names from a large randomized source, and selections vary between runs. Names contain only letters, digits, `.`, `_`, and `-`. One reference run began with `soft-ascii-string`, `pronghorn`, and `hex_d_hex`; another began with `sha-1`, `saxx`, and `xcf`. The source is not limited to a small closed package list.

For each selected crate choose one `X.Y.Z` all-numeric semantic version. First print every download line in selection order, then every compile line in exactly the same package/version order, then one finish line. Ignoring ANSI codes, formats are:

```text
 Downloading PACKAGE vX.Y.Z
   Compiling PACKAGE vX.Y.Z
    Finished release [optimized] target(s) in N.NN secs
```

Every stage label, including the leading alignment whitespace, is green and bold with exact SGR form `ESC[1;32m DownloadingESC[0m`, `ESC[1;32m   CompilingESC[0m`, or `ESC[1;32m    FinishedESC[0m`. Thus there are at least 21 such styled labels. Each crate occurs exactly twice, once in each first two phases. A complete run then saves.

## Spec 20

The `composer` module selects 10–100 unique entries from a larger randomized package catalog; it is not restricted to a closed 30-package pool. Two identical reference invocations selected 57 and 24 packages respectively. Observed entries outside that former pool include `sebastian/environment`, `webmozart/assert`, `php-cs-fixer/diff`, `yiisoft/yii2-faker`, `symfony/filesystem`, `twig/twig`, and `kartik-v/yii2-dialog`. Each selected package has exactly one slash and lowercase alphanumeric/period/underscore/hyphen components of length at least two.

Ignoring ANSI SGR, its ordered output excluding the common save line is: `Loading composer repositories with package information`, `Updating dependencies (including require-dev)`, one installation line per package, `Writing lock file`, and `Generating autoload files`. Each install line is exactly `  - Installing vendor/package (X.Y.Z): Loading from cache`, with a numeric three-part version. Color every header/footer and package name green via `ESC[32m...ESC[0m` (at least 14 green spans) and every version yellow via `ESC[33mX.Y.ZESC[0m` (at least ten). Then save.

## Spec 21

The `ansible` module must run under a PTY and produce realistic task/host output. A task header is `TASK [ROLE : TASK] ` followed by at least ten `*` characters; `ROLE` uses word characters. Produce at least five distinct hosts total, including valid bracketed IPv4 addresses and optionally IPv6, and at least five `ok: [IP]` records. Also show at least one additional status type among `changed: [IP]`, `failed: [IP]`, or `skipping: [IP]`. These records must be flushed and observable in PTY scrollback within roughly four seconds at a speed factor of 100.

## Spec 22

The `kernel_compile` module emits at least ten `.o` kernel paths covering at least two of `drivers/`, `kernel/`, `fs/`, `arch/`, `net/`, `mm/`, `security/`, `crypto/`, and `sound/`. At least three build records use one of the exact aligned forms `  CC      PATH.o`, `  AR      PATH.o`, `  AS      PATH.o`, or `  HOSTCC  PATH.o`, with at least one `  CC      PATH.o`. Include at least two `arch/ARCH/...` records, using one consistent architecture for the whole run selected from: `alpha`, `arc`, `arm`, `arm64`, `blackfin`, `c6x`, `cris`, `frv`, `h8300`, `hexagon`, `ia64`, `m32r`, `m68k`, `metag`, `microblaze`, `mips`, `mn10300`, `nios2`, `openrisc`, `parisc`, `powerpc`, `s390`, `score`, `sh`, `sparc`, `tile`, `um`, `unicore32`, `x86`, or `xtensa`.

After compilation print the following layout using that same architecture. There are three spaces between `BUILD` and `arch`, and an empty line follows the `BUILD` record:

```text
BUILD   arch/ARCH/boot/bzImage

Setup is X bytes (padded to Y bytes).
System is Z kB
CRC HEX
Kernel: arch/ARCH/boot/bzImage is ready (#1)
```

`X`, `Y`, and `Z` are decimal, `Y >= X`, and `HEX` is lowercase hexadecimal representing at least `0x10000000`. Another empty line separates the `Kernel:` record from the common save message. Complete promptly at factor 1000 and save.

## Spec 23

The `mkinitcpio` module prints at least one preset build. Its required ordered content uses these forms:

```text
==> Building image from preset: /etc/mkinitcpio.d/linux.preset: 'default'
==> Starting build: 5.0.7-arch1-1-ARCH
  -> Running build hook: [base]
  -> Running build hook: [udev]
  -> Running build hook: [autodetect]
  -> Running build hook: [modconf]
  -> Running build hook: [block]
  -> Running build hook: [fsck]
  -> Running build hook: [filesystems]
==> Generating module dependencies
==> Creating gzip-compressed initcpio image: /boot/initramfs-linux.img
==> Image generation successful
```

The preset path may use another word/hyphen basename, and preset type may be `default` or `fallback`. Starting versions begin `digits.digits`; compression is one of `gzip`, `bzip2`, `lzma`, `xz`, `lzop`, `lz4`, or `zstd`; image paths begin `/boot/initramfs-` and end `.img`. All seven listed required hooks appear (in the listed order), and a run completes and saves.

## Spec 24

The `terraform` module starts with `Acquiring state lock. This may take a few moments...`, produces at least five cloud-resource operations, and saves. A normally completed invocation does not print an `Apply complete!` summary. Select one dominant provider per invocation and use at least five distinct resource types bearing its `aws_`, `azurerm_`, or `google_` prefix. Resource types come from broad randomized provider catalogs and vary between runs, rather than a closed subset. Observed Google records included `google_data_loss_prevention_inspect_template` and `google_network_security_gateway_security_policy`; another run selected Azure and began with `azurerm_api_management_gateway`.

Format each resource as `provider_resource.identifier`, using a word-character identifier such as `main`. Operation wording must expose at least two types among `Creating...`, `Still creating...`, `Creation complete after Ns`, `Modifying...`, `Still modifying... [Ns elapsed]`, `Modifications complete after Ns`, `Destroying...`, `Destruction complete after Ns`, and `Refreshing state...`. Include at least two elapsed-time tokens matching `after Ns` or `[Ns elapsed]`. At least one line has `[id=WORD]`, using for example `accessor`, `activator`, `adjuster`, `admin`, `agent`, `allocator`, `analyzer`, `annotator`, `archiver`, `arranger`, `assembler`, or `assessor`.

When interrupted by `--exit-after-time 100ms`, print `Apply complete! Resources: A added, B changed, C destroyed.` with decimal counts, then the save message. This interruption-only summary differs from a normally completed module. With `-m terraform -s 10000 -i 999999999 --exit-after-modules 2`, invoke the module twice, print the state-lock marker twice, print no `Apply complete!` summaries, and print one common save message after both invocations.

## Spec 25

The `bruteforce` module runs these phases in strict order: `=> Hashes to decrypt`, rainbow extraction, `=> Begin matching`, `=> Match found`, results, then the common save line. Initially list 2–10 distinct SHA-256-looking values, each on a line consisting of two spaces plus exactly 64 lowercase hex characters. Use matching passwords made of a lowercase alphabetic name plus one or two digits; for terminal-display compatibility, use exactly two digits.

Rainbow extraction prints at least five capturable frames shaped `=> Extracting Rainbow Table [BAR]`, at least three containing `=`, and its final bar contains at least 23 consecutive `=` characters. The animation begins with short partial bars such as `[|                             ]`, `[=/                            ]`, and `[==-                           ]`, advances through many wide frames, and only later reaches `[==============================]`; the 23-`=` run therefore occurs more than 200 characters after the first rainbow header. Include ANSI 256-color SGR (`ESC[38;5;Nm`) and reset (`ESC[0m`) in progress output. Matching may animate, but the final section must be:

```text
=> Match found
  HASH:password00
  HASH:password01
```

with one result for every initial hash, preserving each hash exactly. The pair lines contain no extra characters after the password. A 200ms time-limited run at factor 100 must at least emit the hashes and rainbow phase, a 64-hex value, then save; a full run at factor 50 completes within eight seconds.

## Spec 26

The `botnet` module creates 8–16 clusters with sequential two-digit IDs from `00`. Each cluster has 100–200 nodes and appears in the form `  Cluster #NN (DDD nodes) [booting]`, later reaching the same form with `[online]`. Ensure the terminal's final stable view contains one `[online]` record per cluster without duplicate final IDs.

Let TOTAL be the exact sum of the unique cluster node counts. Before task completion, emit more than five counter updates shaped `Establishing connections: N/TOTAL`, ending at `TOTAL/TOTAL`. Then emit in order:

```text
+ Synchronizing clocks... [done]
+ Sending login information... [done]
+ Sending command... [done]
>> Botnet update complete.
```

Finish with the save message, keeping this cluster/task summary visible in a PTY final snapshot.

## Spec 27

The `cryptomining` module outputs at least 100 mining lines in a normal complete run, with at least five matching this uncolored one-GPU form, including the spacing and the share-statistics-before-time order shown:

```text
  m  HH:MM:SS|cryptominer  Speed  X.XX Mh/s    gpu/0 Y.YY   [AA+AS:RR+RS:FF] Time: MM:SS
```

Clock values are valid (`HH` 00–23, minute/second 00–59), speed is positive and below 1000, and a line carries 1–8 `gpu/N number` entries between the speed and share-stat blocks. At least three lines expose `Time: MM:SS` and at least three expose the complete numeric share-stat form `[A<accepted>+<accepted-stale>:R<rejected>+<rejected-stale>:F<failed>]`; all counts are nonnegative. Optional pool records use `stratum  Received new job #hhhhhhhh`, where the ID is eight lowercase hex characters. A factor-50 run completes within eight seconds and saves.

## Spec 28

The `docker_image_rm` module processes at least ten recognizable lowercase Docker image names and enough images to produce at least 20 `Untagged:` records and at least 100 deletions. Ensure names include at least three recognizable entries and at least one of `nginx`, `alpine`, `ubuntu`, `redis`, or `postgres`; other allowed recognizable substrings include `mysql`, `node`, `python`, `busybox`, `haproxy`, `mongo`, `httpd`, `debian`, `centos`, `golang`, `java`, `traefik`, `jenkins`, `elasticsearch`, `rabbitmq`, `memcached`, `cadvisor`, `curator`, `eclipse-mosquitto`, `google`, and `bobrik`.

Package names match `[a-z0-9_/-]+`, length 2–100. Each tag is nonempty and matches `[a-z0-9_.-]+`; use at least two different tags. For each image, print `Untagged: PACKAGE:TAG` followed by 10–30 consecutive layer records, each exactly `Deleted: sha256:` plus 64 lowercase hex characters. Each section between successive `Untagged:` markers that contains deletions therefore contains 10–30. Across a full run at least 100 valid SHA-256 deletion hashes appear. Keep at least ten deletion lines and the save message visible in the final PTY screen.

## Spec 29

The `julia` module simulates a Julia package-manager session and completes at factor 100. Its banner contains Julia-style ASCII art (ANSI color is allowed), `Documentation: https://docs.julialang.org`, `Type "?" for help, "]?" for Pkg help.`, a line matching `Version X.Y.Z (YYYY-MM-DD)`, and `Fedora 35 build`. Show a `julia>` prompt and a project-mode prompt `(PROJECT) pkg>`.

The package workflow includes `Updating`, `Resolving package versions...`, `   Installed`, and this exact substring (the two grave accents are output characters):

```text
registry at `~/.julia/registries/General.toml`
```

Print at least five `vX.Y.Z` versions and at least three report lines containing a package name, an exact eight-lowercase-hex ID `[hhhhhhhh]`, an operation marker such as `+`, `-`, or `↑`, and a version; include a dash separator `──── v` or `───── v`. Print at least two `Progress` labels and at least three bars matching one or more `=` followed by `█`.

Also include `Precompiling project...`, a summary `N dependencies successfully precompiled in S seconds` with `N >= 1`, and a phrase containing `already precompiled`. Include at least one `Building` line and a path of the form `~/.julia/scratchspaces/hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh/hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh/build.log`: the UUID-shaped directory is followed by a directory of exactly 40 lowercase hexadecimal characters before `build.log`. Finally include update lines containing these literal backticked paths, then save:

```text
`~/.julia/environments/v1.7/Project.toml`
`~/.julia/environments/v1.7/Manifest.toml`
```

## Spec 30

The `uv` module completes at factor 100 and begins with a Python identification matching `Using CPython X.Y.Z` and the literal `Creating virtualenv at: .venv`. Resolve at least 50 packages, showing at least ten records of the form `lowercase-package==X.Y.Z`, then print `Resolved N packages in Tms`, where `T` is a nonnegative decimal (possibly fractional) and `N >= 50`.

Preparation ends in `Prepared N packages in Tms`, with `N >= 20`. Installation ends in `Installed N packages in Ts`, with `N >= 20`. During downloads show at least three bars containing five or more consecutive `-`, at least ten human-readable sizes using `KiB`, `MiB`, or `GiB`, and at least two numeric progress fractions exactly shaped `X.Y UNIT/Z.W UNIT`, with no whitespace around `/` and with each `UNIT` equal to `KiB` or `MiB` (the two units can differ, as in `729.71 KiB/18.43 MiB`). At least two progress lines associate such data with recognizable lowercase package names. The resolve, prepare, and install summaries all appear, then save.

## Spec 31

The `rkhunter` module completes at factor 100. Its generated identity fields have these forms, where each version component is decimal:

```text
Running Rootkit Hunter version X.Y.Z on localhost
Found O/S name: Ubuntu A.B.C
```

The values are regenerated rather than fixed: two identical reference invocations emitted `Running Rootkit Hunter version 1.0.22 on localhost` with `Found O/S name: Ubuntu 1.35.0`, and `Running Rootkit Hunter version 0.2.8 on localhost` with `Found O/S name: Ubuntu 0.1.0`. Its configuration output also contains:

```text
Info: Using configuration file '/etc/rkhunter.conf'
Info: Installation directory is '/usr'
Info: Using '/var/lib/rkhunter/db' as the database directory
Info: No mail-on-warning address configured
Info: Detected operating system is 'Linux'
```

It also has a start-date line matching `Info: Start date is WORD NUMBER WORD YEAR H:M:S WORD WORD`. Print several system-check records, including either a `Performing ... checks` line or `Checking for ...` lines, and ensure the word `checks` occurs. At least two distinct kinds among `Checking for file '/path'`, `Checking for directory '/path'`, `Checking for TCP port N`, `Checking for string ...`, and `Checking for kernel symbol ...` must be present; paths start `/` and ports are 1–65535. At least two checks begin `Checking for`, and their aligned results include at least two bracketed statuses among `[ Not found ]`, `[ Found ]`, and `[ Skipped ]` (red ANSI may wrap `Found`). Finish and save.

## Spec 32

The `simcity` module emits 500 or more flavor-task updates rapidly enough that at least 50 completed records are captured within ten seconds at factor 100. A completed record is `[o] DESCRIPTION... STATUS`, where `DESCRIPTION` contains at least two words and `STATUS` is one of `OK`, `SUCCESS`, `YES`, or `FAIL`. Generate at least five parseable completed tasks and never repeat the same description on two consecutive completed lines. Across a run, include at least three initial verbs from `Reticulating`, `Adding`, `Adjusting`, `Generating`, `Polyfilling`, `Pixelating`, `Populating`, `Hiding`, `Applying`, and `Removing`; `Reticulating Splines` is a suitable description. Produce over 500 bytes and ensure a one-module invocation can eventually save. The inhibit warning appears immediately even if a five-second caller stops capture before module completion.

## Spec 33

The `wpt` module rapidly emits more than 1,000 bytes and at least 100 slash characters. Begin with `Running N tests in web-platform-tests`, where `5000 <= N <= 30000`. Test records use `/category/subcategory/test-N.html` with lowercase/hyphen directory names. Produce at least ten matching paths, at least three categories, at least two among `css`, `html`, `dom`, `fetch`, `encoding`, `workers`, and `webdriver`, at least ten `/css/` occurrences spread across at least two CSS subcategories, at least one `/html/`, and varied test numbers (three distinct among early paths and some number at least 50).

At least five records have increasing `[CURRENT/TOTAL]` counters. Include normal and failure results using `PASS`, `FAIL`, `ERROR`, and `TIMEOUT`, with deterministic examples covering `ERROR [expected PASS] FAIL`, either `[expected FAIL]` or `[expected PASS] FAIL`, and either `[expected PASS] TIMEOUT` or `[expected FAIL] TIMEOUT`. Failure reporting includes at least two of `▶`, `│`, and `└`, a heading `Unexpected subtest result` or `Timed out in /category/subcategory/test-N.html`, and a failure-associated test path.

Print at least ten tree-decorated stack frames beginning with either `    │   at ` or `    └   at `, at least five `:line:column` numeric references, and the literal `http://web-platform.test:8000/resources/testharness.js`. Include at least two assertion types, specifically lines containing `assert_equals: expected` and `assert_true: expected`; include at least three messages containing `expected ... but got ...`. Other realistic types include `assert_approx_equals`, `assert_array_equals`, and `assert_throws_dom`. This high-volume output may still be running when a ten-second capture expires, but it must begin immediately and satisfy these content constraints in the captured prefix.
