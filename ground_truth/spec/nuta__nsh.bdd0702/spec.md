# Clarified executable specification

The required artifact is a native command-line program named exactly `executable`. It implements the `nsh` shell described below. Commands such as `cat`, `grep`, `wc`, `tr`, `sleep`, `printf`, `/bin/sh`, and other operating-system programs are supplied by the evaluation harness; `executable` only has to locate them, launch them, and connect their arguments, environment, working directory, file descriptors, and exit status as specified here.

Unless a rule below gives a different status, successful operations return status 0 and failed shell builtins return status 1. Output named “stdout” and “stderr” must be written to those distinct byte streams. All shown diagnostic strings include a final newline unless explicitly described otherwise.

## Spec 1

The command-line interface identifies itself as `nsh` version `0.4.2`. `--version` prints exactly `0.4.2\n` to stdout, prints nothing to stderr, and exits 0. `-h` and `--help` print exactly the following text to stdout, nothing to stderr, and exit 0:

```text
nsh 0.4.2
A command-line shell that focuses on performance and productivity.

USAGE:
    executable [FLAGS] [OPTIONS] [FILE]

FLAGS:
    -h, --help       Prints help information
    -l, --login      Behave like a login shell
        --norc       Don't load nshrc
        --version    Print the version

OPTIONS:
    -c <command>        The command to be executed

ARGS:
    <FILE>    The file to be executed
```

The text has one newline after the final line. Argument validation precedes help/version handling: `executable --wat --version --help` exits 1, writes nothing to stdout, and writes exactly the following to stderr instead of displaying help or version output:

```text
error: Found argument '--wat' which wasn't expected, or isn't valid in this context

USAGE:
    executable [FLAGS] [OPTIONS] [FILE]

For more information try --help
```

Among otherwise valid arguments, version takes precedence over `-c` and file execution. If both help and version occur, help wins.

## Spec 2

The accepted execution arguments are `-c COMMAND`, `-c=COMMAND`, one optional positional `FILE`, `-l`/`--login`, and `--norc`. `-lc COMMAND` is accepted as the combined `-l -c COMMAND`. Login mode is accepted in all modes but need not otherwise alter noninteractive execution. `--norc=true` is accepted with the same effect as `--norc`. Options may follow `-c`'s command value, as in `-c 'echo ok' --norc`.

At most one `-c`, one login flag, and one positional file are allowed. When both `-c` and a file are present, the command string is run and the file is ignored. `--` ends option parsing; following tokens are positionals. Without `--`, option parsing continues after a positional file. In particular, `executable --norc FILE --wat` rejects `--wat` before running `FILE`: it exits 1 with no stdout and the unknown-option diagnostic whose usage line is `    executable --norc`. A second ordinary positional is also an excess positional.

An unknown option or excess positional exits 1 and writes a `Found argument ... wasn't expected` diagnostic to stderr. Its `USAGE` line reflects arguments already recognized by the parser instead of always showing the help synopsis. In particular, `executable --norc --wat` exits 1 with exactly:

```text
error: Found argument '--wat' which wasn't expected, or isn't valid in this context

USAGE:
    executable --norc

For more information try --help
```

A missing `-c` value without other options exits 1 with exactly:

```text
error: The argument '-c <command>' requires a value but none was supplied

USAGE:
    executable -c <command>

For more information try --help
```

With `--norc` already recognized, `executable --norc -c` instead uses the line `    executable -c <command> --norc`; the rest of the diagnostic is identical.

Duplicate singleton flags produce status-1 diagnostics with the following observed wording. Repeating `-c` in an otherwise option-free invocation writes:

```text
error: The argument '-c <command>' was provided more than once, but cannot be used multiple times

USAGE:
    executable -c <command>

For more information try --help
```

Repeating `--login` while also supplying `-c COMMAND` writes:

```text
error: The argument '--login' was provided more than once, but cannot be used multiple times

USAGE:
    executable -c <command> --login

For more information try --help
```

## Spec 3

With `-c`, parse and execute the supplied string and return the status of its final executed command; an empty string succeeds silently. With a positional `FILE`, open and parse that file as a shell program regardless of its executable bit or whether it has a shebang. A shebang is just a comment. Empty and comment-only files succeed. In file mode `$0` is the file name exactly as passed. An explicit empty file name or a nonexistent/unopenable file triggers the program's panic handler: it exits 101 and emits no stdout. For a nonexistent file, stderr begins exactly `nsh: panicked at src/main.rs:<error location>:\nfailed to open the file: Os { code: 2, kind: NotFound, message: "No such file or directory" }\n`, continues with a backtrace, and ends with `nsh: Something went wrong. Check out ~/.nsh.log and please file this bug on GitHub: https://github.com/nuta/nsh/issues\n`.

An ordinary command failure does not by itself stop a command string or script: later commands run, and the final command determines the shell status. The `exit` builtin and the `set -e` rule below are exceptions. A syntax error in a `-c` string or file returns 255 and executes none of that source.

With no `-c` and no file, a terminal stdin/stdout starts the interactive editor. If stdout is not a terminal, do not consume or execute piped stdin; write exactly `nsh: warning: stdout is not a tty\n` to stderr, write nothing to stdout, and exit 0.

## Spec 4

Import all inherited environment variables as shell variables without changing their bytes: empty values, values containing `=`, newlines, spaces, quotes, dollar signs, backslashes, and Unicode must remain usable. Do not synthesize `PWD`: when it is absent from the inherited environment, `$PWD` is empty even though the process has a valid working directory; when it is inherited, preserve its value. If the environment does not contain a `PATH` key, create it with exactly `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`. If `PATH` is present, including when its value is empty, preserve it.

Unless `--norc` is given, before the requested command/file or the first interactive prompt, try these two startup scripts in this order:

1. `$HOME/.nshrc`
2. `${XDG_CONFIG_HOME}/nsh/nshrc`, or `$HOME/.config/nsh/nshrc` when `XDG_CONFIG_HOME` is absent

Run both when both exist, so the second can observe and override the first. Their output and state changes are visible to the requested program. Missing files, directories used as those paths, unreadable files, absent `HOME`, and empty files are ignored without failure. Parse an entire rc file before executing any of it: if it is malformed, emit its parse diagnostic, execute none of it, and still continue with the requested command. `--norc` suppresses both files in every mode.

## Spec 5

On startup, initialize a history file at `$HOME/.nsh_history`: create an empty regular file when absent and leave existing contents unchanged. Each valid on-disk history record is one newline-terminated line containing three tab-separated fields, in order: an ASCII decimal Unix timestamp, the working directory, and the command text. For example, `0\t/tmp\techo hi\n` is accepted without a warning, while the bare line `existing\n` is malformed. A malformed existing history line must not prevent startup. The warning reports the malformed record's one-based physical line number. Thus a file containing `0\t/tmp\tok\nbroken\n` lets `echo yes` run and writes exactly `nsh: nsh: warning: failed to parse ~/.nsh_history: at line 2\n` to stderr; a malformed first line instead ends in `at line 1\n`. Existing contents remain unchanged. This initialization also occurs for `-c` execution.

Within an interactive session, commands of at least eight characters are available newest-first through Up-arrow history. Consecutive duplicate command lines count once. Repeated Up walks backward; Down walks forward. Moving Down past the newest entry restores the text that was in the editor before history navigation, including an empty or partially typed line.

## Spec 6

Parse a complete source before executing it. Spaces and tabs separate words; unquoted newlines and `;` separate command lists. Empty input, whitespace, comments, blank lines, and leading/trailing semicolons are accepted. Multiple semicolons separated by whitespace, such as `; ;`, are also accepted, but adjacent `;;` or `;;;` outside `case` syntax are rejected atomically with status 255. Thus ` ; ; # first\n\techo one;;; false; echo two; false` produces no stdout and a line-2 parse diagnostic at the adjacent semicolons. `#` starts a comment outside quotes and runs through the newline. Newlines may occur literally inside quotes.

Support simple commands and assignments; `|`, `&&`, `||`, and postfix `&`; brace groups `{ list; }`; subshells `(list)`; `if`/`elif`/`else`/`fi`; `while`/`do`/`done`; `for name in words; do ...; done`; arithmetic `for ((init; condition; update)); do ...; done`; `case WORD in PATTERN) ... ;; ... esac`; and function definitions `name() { ...; }` and `function name() { ...; }`. These forms can be multiline and nested. Prefix `!` is not a negation operator in this implementation: it is parsed as the command name `!` and normally follows the command-not-found rule.

Reject incomplete quotes, substitutions, groups, functions, pipelines, conditional lists, loops, case arms, and redirections. Also reject the obsolete `$[expression]` arithmetic form. A trailing assignment with no value in a multi-assignment statement, such as `a=1 b=2 c=`, is a parse error; use `c=""` or `c=''` for an empty value. A syntax error emits no partial command output, returns 255, and writes a diagnostic beginning `nsh: parse error:  --> LINE:COLUMN`, followed by the relevant source line, a caret/span, and an indication of the expected grammar item.

## Spec 7

Single quotes preserve characters literally, with one parser defect: a backslash followed by a single quote preserves both bytes and prevents that quote from terminating the span. For example, `printf '<%s>' 'a\'b'` prints `<a\'b>`. Consequently, the source `printf '<%s>\n' 'a $b \' ' ' "x y" ab" cd"ef "" a\ b \* "~"` is rejected atomically with status 255, no stdout, and a diagnostic ending `expected literal_in_single_quoted_span`. Double quotes preserve whitespace as one argument and perform parameter, command, and backtick expansions. Arithmetic expansion inside double quotes instead invokes the panic handler during parsing. For example, `echo "$((1+2))"` exits 101 with no stdout; stderr begins exactly `nsh: panicked at src/parser.rs:<error location>:\ninternal error: entered unreachable code\n`, continues with a backtrace, and ends with the bug-report line from Spec 3. Within double quotes, `\"` and `\$` produce literal quote and dollar characters. Unlike a conventional shell, two source backslashes inside double quotes remain two backslash bytes rather than collapsing to one. In the tested case, passing the double-quoted text `backslash: ` followed by two source backslashes to `echo -e` writes those two backslashes and then a newline. Outside quotes, a backslash makes the next shell metacharacter literal. Adjacent quoted and literal fragments form a word, so `ab" cd"ef` is one argument `ab cdef`. Empty quotes produce an empty argument.

Unquoted wildcard and tilde syntax can expand; quoted or escaped wildcard/tilde characters are literal. Every unquoted parameter-expansion span becomes a distinct argument from adjacent expansion or literal spans, whether its value is undefined, an ordinary defined variable, or a special parameter. Thus, after `x=hello; y=world`, `echo $x$y` prints `hello world`, while `echo "$x$y"` prints `helloworld`; `x=home; echo xdg:$x` prints `xdg: home\n`; and `echo status:$?` after a successful command prints `status: 0\n`. Literal text around an undefined unquoted expansion likewise occupies separate spans; `echo before:$UNDEFINED_VAR:after` prints `before:  :after\n` (two spaces between the colons). Quoted undefined variables expand to an empty part of their containing argument.

## Spec 8

Resolve a command in this order as applicable: aliases at command position, shell functions, builtins, then executable files located using `PATH` (or an explicit path containing `/`). Pass external commands the exact expanded argument vector, exported environment, current directory, stdin/stdout/stderr connections, and signals, and return their status, except for the descriptor-order corruption case below. The harness provides the external commands; do not emulate their internal output.

Preserve this external-argument/redirection defect. For paths `A` and `B`, executing `/bin/sh -c 'echo out; echo err >&2' >A 2>&1; /bin/sh -c 'echo out; echo err >&2' 2>&1 >B` returns 0, writes exactly `err\n` to the shell's stdout and nothing to its stderr, leaves `B` containing exactly `out\n`, and leaves `A` containing exactly `/bin/sh: 1: echo: echo: I/O error\nerr\n`. In the first redirection order, the quoted `-c` argument is therefore not passed intact.

An unknown normal command returns 1 and writes exactly `nsh: command not found \`NAME'\n`. This lookup diagnostic is emitted by the shell itself and bypasses redirections attached to the missing command: `missing 2> err` leaves `err` empty and writes the diagnostic to the shell's stderr. Trying to run a located but non-executable regular file returns 1 and writes `nsh: Failed to exec "PATH" (EACCESS). chmod(1) may help.\n`. Failures do not terminate later `;` commands by default. `true` succeeds silently and `false` returns 1 silently. Neither `:` nor `xkcd` is a builtin; absent a matching executable, each follows the ordinary command-not-found rule. The distinct builtin `xkcd-true-random-number` prints exactly `4\n` and succeeds, including in files and command substitutions.

## Spec 9

For `A && B`, execute `B` only if `A` succeeds. This implementation's `||` is defective: for `A || B`, execute `B` regardless of whether `A` succeeds or fails, and use `B`'s status. Prefix `!` does not negate status; it is an ordinary command name and, when not present on `PATH`, returns 1 with `nsh: command not found \`!'\n`. Consequently, `false && echo no; true || echo no; false || echo yes; true && echo also; ! true || echo negated; ! false && echo inverted` prints `no\nyes\nalso\nnegated\n`, writes the `!` lookup diagnostic twice, and exits 1.

A pipeline starts every stage, connects each stage's stdout to the next stage's stdin, and has the status of its last stage only. Thus a missing first command followed by a successful last command still gives a successful pipeline, though the lookup diagnostic remains on stderr. Downstream external commands determine their own output bytes: `missing_pipe | cat; printf x | cat | grep x` returns 0, writes exactly `x\n` to stdout, and writes exactly `nsh: command not found \`missing_pipe'\n` to stderr. Pipelines must stream concurrently so large/binary input, many stages, and producers larger than a pipe buffer neither deadlock nor truncate. Builtins used in pipelines participate through the same file descriptors.

## Spec 10

Variable names begin with an ASCII letter or underscore and continue with letters, digits, or underscores. `name=value` persists in the current shell; multiple standalone assignments can appear together. Assignment prefixes before an external command are visible to that child. `export name=value` assigns and exports; `export name` exports its current value; multiple operands are accepted. `export` with no operands succeeds and produces no output. Exported changes reach child processes. `unset NAME` removes the variable and its exported status, succeeds for a nonexistent name, and accepts exactly one operand.

Assignments inside a function modify the visible outer variable unless that function declared a local of the same name. `readonly` is not implemented as a builtin. Thus `readonly stable=value` returns 1 with `nsh: command not found \`readonly'\n`, does not assign `stable`, and—unless errexit is active—does not prevent later commands from running.

## Spec 11

Support `$name` and `${name}`. Undefined variables normally expand to empty. The special parameters are:

- `$?`: status of the most recently completed command/list.
- `$$`: the positive decimal process ID of the shell.
- `$!`: positive decimal process ID of the most recently started background job.
- `$0`: the passed script path in file mode, the empty string in `-c` command mode, and a nonempty shell identity in interactive mode.
- `$#`: current function argument count capped at nine, as specified in Spec 23.
- `$1` through `$9`, and braced multi-digit forms such as `${10}`: positional arguments.
- `$*` and `$@`: all current function arguments in order, joined/displayed with spaces in the tested quoted and unquoted uses.

Function calls temporarily replace the positional-argument set and restore it on return. `shift` operates on that set as described later.

## Spec 12

Implement these braced parameter operations, where `word` itself may contain ordinary expansions:

- `${v-word}` uses `word` only when `v` is unset, not when it is set to empty.
- `${v:-word}` has the reference implementation's empty-value defect: it uses `word` only when `v` is unset. When `v` is set to empty, the result is empty, so `v=""; echo "${v:-default}"` prints only a newline.
- `${v:=word}` uses and assigns `word` only when `v` is unset. A variable set to empty is treated as set and remains empty; an existing nonempty value is also unchanged. Thus `unset a; b=''; c=keep; printf '%s:%s:%s|' "${a:=A}" "${b:=B}" "${c:=C}"; echo $a$b$c` returns 0 and writes exactly `A::keep|A  keep\n`.
- The `${v:?message}` operator is not supported, regardless of whether `v` is unset, empty, or nonempty. A source containing it is rejected atomically with status 255 and no stdout. For `unset v; echo before; echo ${v:?custom failure}`, stderr is exactly:

```text
nsh: parse error:  --> 1:31
  |
1 | unset v; echo before; echo ${v:?custom failure}
  |                               ^---
  |
  = expected param_op
```
- `${#v}` gives the UTF-8 byte length of a scalar value and `0` for unset/empty values. Thus `v=雪ab; echo ${#v}` prints `5\n`, not the three-character count. For an array name it measures the byte length of element zero, not the number of elements.

In `set -u` mode, expanding an undefined variable fails immediately with status 1, no command stdout, and `nsh: undefined variable \`NAME'\n`. A defaulting form such as `${NAME:-default}` remains legal and does not trigger this error.

## Spec 13

Parameter pattern replacement uses `${v/pattern/replacement}` for the first match and `${v//pattern/replacement}` for all non-overlapping matches. Omitting the replacement, or supplying an empty replacement, deletes matches. This also works on positional parameters. `?` matches one character and `*` matches any sequence greedily; consecutive `*` characters are equivalent to one. A quoted or escaped `*`/`?` in the pattern is literal, and `\/` denotes a literal slash. In replacement text, one source backslash before an ordinary character is consumed, while a pair of source backslashes produces one literal backslash. Concretely, `FOO=test; printf '<%s>\n' "${FOO/test/\\n}"` (two consecutive source backslashes before `n`) writes the five bytes `<`, backslash, `n`, `>`, newline. No match returns the original value, and replacing `*` in an empty value still returns empty. Global replacement advances through non-overlapping matches: replacing `aa` globally in `aaaaaa` gives three replacements.

Examples: with `v=hello`, `${v/l/L}` is `heLlo` and `${v//l/L}` is `heLLo`; with `v=prefix_middle_suffix`, `${v/_*}` is `prefix` and `${v/*_}` is `suffix`.

## Spec 14

An array assignment has the form `a=(word1 word2 ...)`, including an empty list and quoted/empty elements. `${a[index]}` uses a zero-based index. The index may be an integer literal, variable, or arithmetic expression. `$a` means element zero. A missing or out-of-range element expands to empty. `${#a}` is the length of element zero. Arrays can be local and can be read in loops and substitutions. Preserve the observed indexed-assignment defect for local arrays: after `local a=(one two)`, executing `a[1]=changed` clears the local array, so both `${a[0]}` and `${a[1]}` expand to empty; an outer array shadowed by that local is restored unchanged when the function returns.

## Spec 15

`$(list)` and backticks execute their contents in a substitution context and replace the construct with captured stdout. The captured text is trimmed at both ends, including leading/trailing spaces, and newline characters are removed rather than preserved. Consequently, capturing `printf 'one\ntwo\nthree\n'` and then echoing the quoted variable prints `onetwothree\n`, while capturing `printf '  spaces  \n'` and printing the quoted result in brackets prints `[spaces]\n`. Nesting, pipelines, redirections, assignment values, quoted strings, local declarations, and here-documents may contain command substitutions. A failed command inside a substitution does not by itself terminate the surrounding shell under default options.

Input process substitution `<(list)` starts `list` and expands to a readable path/descriptor whose contents are that command's stdout. Multiple substitutions in one command must work. Output process substitution `>(list)` is not supported and must fail nonzero without executing subsequent assumptions about it.

## Spec 16

Arithmetic expansion `$((expression))` uses signed decimal integers. Undefined or nonnumeric variable values act as zero. Support parentheses; negative integer literals; `+`, `-`, `*`, and integer `/` with ordinary multiplication-before-addition precedence; comparisons `==`, `!=`, `<`, `<=`, `>`, and `>=`, returning `1` for true and `0` for false; and variable assignment inside an expression. Unary minus has an observed defect when applied to a nonliteral operand: its sign is discarded. In particular, `$((-(8/3)))` evaluates to positive `2` and `$((-x))` evaluates to positive `x`, while `$((-8/3))` evaluates to `-2`. Arithmetic values can be assigned, printed, used as array indices, and used in conditions.

`%` is not a remainder operator in this implementation. A `$((...))` construct containing it follows the command-substitution-like parse instead and attempts to execute the enclosed text as a command. Thus `printf '%s' $((-7%3))` returns 0 with no stdout and writes exactly `nsh: command not found \`-7%3'\n` to stderr. Likewise, `echo $((4%0)); echo no` returns 0, writes exactly `\nno\n` to stdout, and writes exactly `nsh: command not found \`4%0'\n` to stderr; it does not terminate the shell.

Postfix `x++` and `x--` update `x` and, in this shell, evaluate to the updated value rather than the old value: starting from 5, `$((x++))` prints 6 and leaves 6; `$((x--))` prints 4 and leaves 4. Division truncates toward zero. Division by zero invokes the panic handler and exits 101; for `echo $((5/0))`, stdout is empty and stderr begins exactly `nsh: panicked at src/eval.rs:<error location>:\nattempt to divide by zero\n`, followed by a backtrace and the final bug-report line described in Spec 3.

Arithmetic `for ((init; condition; update))` evaluates `init` once, runs while the condition is nonzero, and evaluates the update after each normal/continued iteration. None of the three components may be empty. An empty init, condition, or update is rejected atomically with status 255, no stdout, and a parse diagnostic whose expectation is `assign`. In particular, the source `for ((i=0; i<3; i++)); do echo $i; done; j=0; for ((; j<2;)); do echo x$j; j=$((j+1)); done` fails at the second loop's empty init before either loop executes.

## Spec 17

Unquoted path patterns expand against the filesystem: `*` matches zero or more characters, `?` exactly one, and `**` can recursively cross directory levels. Matching includes dotfiles and may return files, directories, names containing spaces or literal brackets, and symlinks. Pattern components can be combined with literal prefixes/suffixes and nested paths. Quote or backslash the wildcard to suppress expansion. Expansion order must be deterministic lexical path order where output comparisons depend on it. An unmatched active glob fails the command with status 1 and writes exactly `nsh: error: no matches\n`.

An unquoted leading `~` expands to `HOME`, including in longer paths, assignment values, `cd`, and redirection targets. A quoted `~` stays literal.

## Spec 18

`case` expands its subject, considers arms in source order, and runs only the first matching arm; `;;` prevents fallthrough. Multiple alternatives in one arm are separated with `|`. `*` and `?` have the same wildcard meanings as pattern replacement, and a final `*` is the default arm. No match is a successful no-op and execution continues after `esac`. Empty subjects and patterns are accepted, but have an asymmetric matching defect: no pattern, including an empty pattern, matches an empty subject, while an empty pattern matches a nonempty subject. Therefore `v=''; case $v in '') echo empty;; esac` succeeds with no output, whereas changing the assignment to `v='x'` prints `empty\n`.

Matching intentionally is not anchored to the whole subject: a literal or wildcard pattern may match a substring. Consequently, in `case abcd in ab) echo first;; abcd) echo second;; esac`, the first arm runs. Preserve this behavior even though other shells usually require a whole-string match.

## Spec 19

Redirections may follow a simple command and apply to builtins, external commands, and pipeline stages. A redirection following a function call is syntactically accepted but ignored: the target is not created, and the function writes through the descriptors it inherited. In an initially empty working directory, `f() { echo function; }; f >fout; echo pipe | cat; cat fout` returns 1, writes exactly `function\npipe\n` to stdout and `cat: fout: No such file or directory\n` to stderr, and does not create `fout`.

A redirection immediately following a brace group is not accepted. The source `f() { echo function; }; f >fout; { echo group; } >gout; printf pipe >pin | cat; cat fout gout pin` is rejected atomically with status 255 and no stdout; stderr is exactly:

```text
nsh: parse error:  --> 1:50
  |
1 | f() { echo function; }; f >fout; { echo group; } >gout; printf pipe >pin | cat; cat fout gout pin
  |                                                  ^---
  |
  = expected EOI, and_or_list_sep, or compound_list_sep
```

A redirection cannot precede its command: a source beginning `>pre echo pre` is rejected atomically with status 255, no stdout, and a column-1 parse diagnostic ending `expected EOI, command, or compound_list_sep`. Support `< file`, `> file` (create/truncate), `>> file` (create/append), `2> file`, `2>> file`, `>&2`, and `2>&1`, subject to the command-lookup diagnostic exception in Spec 8. Descriptor duplication is evaluated in source order, subject to the external-command defect in Spec 8. Redirections occur before command execution; an open failure gives status 1 and the command does not run. If the same output descriptor is redirected more than once, an earlier target is created when absent but is not truncated when it already exists; only the final target receives output. Thus, if `A` initially contains `old`, `echo hi >A >B` returns 0, leaves `A` containing `old`, and leaves `B` containing `hi\n`. Directories and unavailable parent paths fail cleanly. `/dev/null` behaves normally.

Here-documents use `<< DELIMITER`, consume complete following lines through a line equal to the delimiter, preserve ordinary and empty lines, and provide the result on stdin. A delimiter declaration must be followed by body input and a terminating delimiter line: `cat << EOF\n` is rejected atomically with status 255 and no stdout; stderr is exactly `nsh: parse error:  --> 2:1\n  |\n2 | \n  | ^---\n  |\n  = expected word\n`. With an unquoted delimiter, expand parameters and command substitutions, while `\$` remains literal. A quoted delimiter is not accepted: a source reaching `cat <<'Q'` is rejected atomically with status 255, no stdout, and a parse diagnostic whose expectation is `heredoc_marker`. The `<<-` indented form is also not accepted: `cat <<-TAB\n\tbody\n\tTAB` returns 255 with no stdout and a parse diagnostic at the terminating `TAB` line. An ordinary here-document can feed a pipeline and coexist with output redirection.

Two here-documents expose an end-of-source-sensitive defect. The source `cat << EOF1 && cat << EOF2\ncontent1\nEOF1\ncontent2\nEOF2` with no newline after the final `EOF2` triggers the panic handler: it exits 101 with no stdout; stderr begins `nsh: panicked at src/parser.rs:<error location>:\nindex out of bounds: the len is 1 but the index is 1\n` and continues with the standard backtrace and bug-report line. If a newline follows the final `EOF2`, the same source instead exits 255 with no stdout and writes exactly `nsh: parse error:  --> 6:1\n  |\n6 | \n  | ^---\n  |\n  = expected word\n` to stderr. `<&-` must fail nonzero rather than hang.

## Spec 20

Brace groups execute in the current shell: variable, function, export, and directory changes persist afterward. Parenthesized groups execute in an isolated subprocess: their assignments, locals, exports, functions, `cd`, `exit`, and option changes do not alter the parent. Their output and status still participate in lists, pipelines, and background jobs; direct postfix redirection of either group form is rejected as described in Spec 19.

A list followed by `&` starts a job and sets `$!` to its positive decimal process ID, but this implementation blocks before executing the following foreground list. Once the job finishes, it prints the job's output and then a completion announcement before continuing. In particular, `/bin/sh -c 'sleep 0.05; echo child' & printf 'pid:%s\n' $!; wait` returns 0 with no stderr and writes, in order, `child\n`, `[1] Done: /bin/sh -c 'sleep 0.05; echo child'\n`, and then `pid:` followed by the positive decimal `$!` value and a newline. The final `wait` has no remaining job and succeeds silently. A background subshell can itself start and wait for jobs. The implementation must tolerate rapid job completion and must not leak or deadlock on repeated pipelines/background work.

## Spec 21

The `test` builtin and its bracket spelling `[ operands ]` return 0 for true and 1 for false. `[` requires its closing `]`; the missing-closing-bracket invocation `[ x = x` is an exception to the usual failed-builtin status and returns 2, writing exactly `[: missing ‘]’\n` to stderr and nothing to stdout. The quotation marks around `]` are the UTF-8 left and right single quotation marks U+2018 and U+2019, not ASCII apostrophes. Support string `=` and `!=`; integer `-eq`, `-ne`, `-lt`, `-le`, `-gt`, and `-ge`; unary string `-z` and `-n`; file predicates `-e`, `-f`, `-d`, `-r`, `-w`, and `-x`; logical negation `!`; and the tested compound `-a` (and) and `-o` (or) forms. Missing files make the applicable file predicates false.

The `[[ expression ]]` form supports the tested string and integer comparisons, internal `&&`/`||`, and wildcard matching on the right side of `==`/`=` and `!=`. It does not support prefix `!`: a source containing `[[ ! x = y ]]` is rejected atomically with status 255 and no stdout, with a parse diagnostic at `x` whose expectation is `cond_op`. These condition commands integrate with `if`, `while`, and the list operators solely through their exit status.

## Spec 22

`if condition; then body; else body; fi` selects by command status and supports nesting and compound conditions. `while condition; do body; done` reevaluates the condition and stops when it fails. A word-list `for` iterates over each expanded word, including quoted words, command-substitution results, and each glob result; an empty list runs zero times. `continue` advances the innermost loop. Preserve the observed `break` defect: `break` does not exit the loop, and later iterations run until the loop condition fails; the unconsumed break then invokes the panic handler. Specifically, `i=0; while test $i -lt 4; do i=$((i+1)); if test $i -eq 2; then continue; fi; echo $i; break; done` exits 101, writes exactly `1\n3\n4\n` to stdout, and has stderr beginning `nsh: panicked at src/main.rs:<error location>:\nunexpected Break\n`, followed by a backtrace and the final bug-report line from Spec 3.

Preserve a related `return` defect specific to a `while` body. Executing `return` skips the remainder of that iteration, but the `while` loop reevaluates its condition and continues; the return does not propagate out of the function until the loop condition eventually fails. Consequently, `f() { while true; do echo before; return 42; echo bad; done; }; f; echo $?` does not terminate: it repeatedly writes `before\n`, never writes `bad\n`, and never reaches the final `echo`. In a finite `while`, the pending return exits the function after the condition becomes false, with its requested status discarded as described in Spec 23.

Preserve this shell's observed `elif` defect: if the initial `if` condition is false and an `elif` condition succeeds, execute the original first `then` body rather than the `elif` body. For example, `x=10; if test $x -eq 5; then echo five; elif test $x -eq 10; then echo ten; fi` prints `five`.

## Spec 23

Both supported function syntaxes create persistent named functions; a later definition replaces an earlier one. A call supplies its own positional parameters, `$@`, and `$*`, supports nesting and recursion, and returns the last body status when execution reaches the end. Except for the `while`-body defect in Spec 22, an explicit `return [STATUS]` immediately unwinds only that function but discards the requested numeric status: the function call returns 0. Thus `return 42` followed by `echo $?` outside the function prints `0`.

`$#` reports the current function argument count only up to nine: it is the actual count for zero through nine arguments and remains `9` for ten or more. Thus a call with ten arguments reports `9`, even though `${10}` and `$*` still expose the tenth argument, and a call with 300 arguments also reports `9`. After shifting a ten-argument call by two, it reports the remaining count `8`. Function calls restore the caller's positional set afterward.

`local name`, `local name=value`, multiple local declarations, command substitutions, and local arrays create a function-frame binding that shadows and later restores any outer binding. Assignment after the declaration changes the local. `unset` removes the local binding immediately, exposing any outer variable of the same name within the remainder of the function; the outer binding itself is not deleted. `local` at global scope returns 1 and writes exactly `nsh: local variable can only be used in a function\n`.

## Spec 24

`echo` joins arguments with one space. With no arguments it writes one newline. A leading `-n` suppresses the final newline. A leading `-e` enables escapes, and `-ne`/`-en` combine both effects. In escape mode support `\n`, `\t`, and `\e` (byte 0x1b). A doubled backslash is not an escape and remains two backslash bytes; an unknown escape such as `\q` likewise remains the two literal characters. `-E` is not an option: print it as an ordinary argument and do not interpret following escapes. Quoting/expansion occurs before these echo rules.

`pwd` prints the absolute current directory with a newline. It reflects successful `cd` and `popd` calls and can be redirected or piped like any other builtin.

## Spec 25

`cd` with no operand uses `HOME`; it accepts absolute and relative paths, `.`, `..`, trailing slashes, spaces supplied by quoting, and expanded `~`. On success it changes the process working directory but does not update the shell variables `PWD` or `OLDPWD`; each remains at its inherited or explicitly assigned value. In particular, when neither variable is inherited, both remain empty after a successful `cd`.

For `cd -`, the shell records each directory departed from and consumes that finite history in reverse order rather than toggling between two locations. Starting in `BASE`, the sequence `cd A; cd B; cd -; pwd; cd -; pwd` prints `A\nBASE\n`; a third `cd -` silently returns 1 and leaves the directory at `BASE`. With no prior directory, `cd -` likewise silently returns 1. A failed ordinary change returns 1 and writes `nsh: cd: ERROR: \`RESOLVED_PATH'\n`, where `ERROR` is the host error such as `No such file or directory (os error 2)` or `Not a directory (os error 20)`. The displayed path is absolute after resolving a relative operand against the current directory. In particular, `cd absent` from `BASE` writes exactly `nsh: cd: No such file or directory (os error 2): \`BASE/absent'\n`.

`pushd [dir]` accepts at most one directory and does not change directory or validate the target immediately. It replaces one retained destination with the supplied target, interpreted relative to the directory current at a later `popd`, or with the current absolute directory when omitted. Supplying a target also replaces the remembered destination used by the next `cd -`: after `cd DIR1; pushd /tmp; cd -; pwd`, `pwd` prints `/tmp`.

On a successful directory change, `popd` does not remove the retained destination. Therefore, starting in `BASE`, `pushd one; pushd two; popd; pwd; cd ..; popd; pwd` prints `BASE/two\nBASE/two\n`; subsequent successful `popd` calls continue to use `two`. If the target is nonexistent or a file, the failed `popd` does remove it and returns 1 with `nsh: popd: ERROR: \`PATH'\n`, where `ERROR` is the host error described for `cd`; a following `popd` then reports the empty-stack error. Unlike the `cd` diagnostic, `PATH` preserves the stored operand's original relative spelling rather than displaying its absolute resolved path. Thus `pushd absent; popd; popd` returns 1 and writes exactly `nsh: popd: No such file or directory (os error 2): \`absent'\nnsh: popd: directory stack empty\n`. When no destination has ever been retained, `popd` returns 1 with `nsh: popd: directory stack empty\n`.

`pushd --invalid` is parsed as an invalid option rather than as a directory and exits 1 with this stderr, including two newline characters after the final line:

```text
nsh: pushd: error: Found argument '--invalid' which wasn't expected, or isn't valid in this context

USAGE:
    pushd [dir]

For more information try --help

```

An excess operand uses the same layout and substitutes that operand; for `pushd dir1 dir2`, the first line names `dir2`. `popd --invalid` exits 1 with the same two-final-newline layout, but its first line begins `nsh: popd: error:` and its usage line is `    popd`.

## Spec 26

`source FILE` parses and executes a file in the current shell and current directory, so variables/functions/directory changes persist and nested/relative source works. Normal command failures inside it do not prevent later sourced commands; `exit` terminates the caller. A malformed sourced file returns the normal parse error. A missing file returns 1 with exactly `nsh: failed open the file: Os { code: 2, kind: NotFound, message: "No such file or directory" }\n`. Surprisingly, `source` with no operand writes `nsh: source: filename argument required\n` but returns 0.

`eval [words...]` joins its expanded operands into shell source, parses it, and executes it in the current scope. It can set variables, define/run loops, use pipelines, and evaluate source held indirectly in a variable. No operands is a silent success. Its final status propagates; an `exit` inside terminates the shell and a syntax error returns 255.

## Spec 27

`alias` with no operands lists definitions as `name='body'`, one per line; ordering need not be relied on. `alias name='body'` defines or replaces an alias. The invocation `alias badformat` returns 1 and writes exactly:

```text
nsh: alias:  --> 1:1
  |
1 | badformat
  | ^---
  |
  = expected alias
```

At command position, substitute the alias body, then retain the invocation's extra arguments. A dollar-prefixed variable reference in the stored body is not expanded during alias invocation; it becomes a literal argument. Thus `x=value; alias show='echo $x'; show extra` returns 0 and writes exactly `$x extra\n`, not `value extra\n`. Bodies may name builtins, but quote characters inside a body are rejected by the alias parser. Defining `alias say='echo "$x"'` writes this diagnostic to stderr and does not define `say`:

```text
nsh: alias:  --> 1:10
  |
1 | say=echo "$x"
  |          ^---
  |
  = expected EOI
```

Command separators inside a body are not reparsed as shell syntax. In particular, after `alias hi='echo one; echo two'`, invoking `hi extra` writes exactly `one; echo two extra\n`: the semicolon is a literal argument rather than a separator. Multiple definitions work, but alias expansion is only one level: the command name produced by an alias body is not looked up as another alias. Consequently, `x=value; alias show='echo $x'; alias again='show'; again extra` returns 1 with no stdout and writes exactly ``nsh: command not found `show'\n`` to stderr. There is no required `unalias` builtin; if absent it follows the ordinary command-not-found rule.

`rehash` is a silent status-0 no-op. Command lookup nevertheless sees executables created after shell startup through an ordinary fresh `PATH` lookup. Preserve the retained-output-file defect when such an executable is created by a command redirection: the shell keeps the newly written file busy and its immediate execution fails. Specifically, with `DIR` as the sole directory in `PATH`, `/usr/bin/printf '#!/bin/sh\necho new\n' >DIR/newcmd; /bin/chmod +x DIR/newcmd; rehash; newcmd` returns 1, writes nothing to stdout, and writes exactly `nsh: Failed to exec "DIR/newcmd" (ETXTBSY: Text file busy)\n` to stderr, where `DIR/newcmd` is displayed as the absolute path used by the redirection.

## Spec 28

`read` takes exactly one required variable and optional `-p PROMPT`. The option and prompt operand are accepted, but the prompt is not written to either output stream. `read` reads one line from stdin, removes the newline and trailing whitespace, preserves leading and internal whitespace and literal punctuation, then assigns the value. Separate calls consume separate lines. An empty line or immediate EOF returns 1 without assigning the target variable; an existing value is retained. Thus `x=old; read x; printf '<%s>:%s' "$x" "$?"`, given either a single newline or immediate EOF, writes exactly `<old>:1`. Redirection can supply stdin. For example, with input bytes `  lead mid  \nsecond\n`, `read -p 'P> ' a; read b; printf '<%s>|<%s>\n' "$a" "$b"; read c; echo status:$?` returns 0, writes exactly `<  lead mid>|<second>\nstatus: 1\n` to stdout, and writes nothing to stderr. The space in `status: 1` follows the unquoted-expansion-span rule in Spec 7.

With no variable operand, `read` exits 1 and writes the following to stderr, including two newline characters after the final line:

```text
read: error: The following required arguments were not provided:
    <VAR>

USAGE:
    read [OPTIONS] <VAR>

For more information try --help

```

`read --invalid` also exits 1 with the same usage and final blank line, but begins `read: error: Found argument '--invalid' which wasn't expected, or isn't valid in this context`.

`shift [n]` shifts function positional parameters left, defaulting to one; `shift 0` changes nothing. Top-level `shift` with no positional arguments succeeds. Invalid numeric input returns 1 and writes exactly `shift: error: Invalid value for '<n>': invalid digit found in string\n\n` to stderr. `shift --invalid` returns 1 and writes the following, including two final newline characters:

```text
shift: error: Found argument '--invalid' which wasn't expected, or isn't valid in this context

USAGE:
    shift [n]

For more information try --help

```

`shift --version` returns 1, writes exactly `shift 0.4.2` to stdout with no newline, and writes exactly `shift: \n\n` to stderr.

`exit [n]` stops the current shell context. No operand means 0. Numeric values are reduced modulo 256 (`256` gives 0, `257` gives 1, and `-1` gives 255); invalid text gives status 1. Inside a subshell it stops only that subshell.

## Spec 29

`set -e` enables immediate termination after any failed command. In this shell the rule also applies to a failing `if` condition, a failing `while` condition, the left side of `||`, and failures inside functions; therefore such constructs do not rescue or continue after the failure. Pipeline status is still its last stage, so `false | true` does not trigger errexit. `set -u` is the undefined-variable rule in Spec 12. `set -n` enables no-execute mode: do not execute any subsequent command and finish with status 0. Combined option spelling such as `set -eu` is accepted.

`set -x` is not supported. By itself it returns 1, writes no stdout, and writes exactly the following to stderr, including the final blank line:

```text
nsh: set: error: Found argument '-x' which wasn't expected, or isn't valid in this context

USAGE:
    set [FLAGS]

For more information try --help

```

Without errexit, a following command still runs: `set -x; echo visible` returns 0, writes `visible\n` to stdout, and writes the same diagnostic to stderr. Other invalid set options also return nonzero.

`unset` with no operand returns 1 and writes exactly the following to stderr, including two newline characters after the final line:

```text
nsh: unset: error: The following required arguments were not provided:
    <NAME>

USAGE:
    unset <NAME>

For more information try --help

```

An extra operand returns 1 and uses the same usage and two-final-newline layout, beginning `nsh: unset: error: Found argument 'EXTRA' which wasn't expected, or isn't valid in this context`.

## Spec 30

`exec` with no operands is a successful no-op and execution continues. With a command, apply expansions/redirections and replace the current shell process: preserve the current directory and the environment originally inherited by the shell, pass all arguments, preserve the replacement's exact stdout/stderr bytes and status, and never run later shell commands. Unlike normally launched external children (Spec 10), an `exec` replacement does not receive variables newly exported or changed within the shell. Thus `export V=yes; exec /bin/sh -c 'printf %s:$V "$PWD"; exit 8'; echo never`, started in directory `DIR` without inherited `V`, returns 8 and writes exactly `DIR:` with no newline; `echo never` does not run. If replacement fails because the path is absent, exit 127 and write `nsh: exec: ENOENT: No such file or directory\n`; if permission is denied, exit 126 and write `nsh: exec: EACCES: Permission denied\n`.

`jobs` accepts no operands and is silent when no jobs exist. `wait` accepts zero or one job spec. With no operand it waits for all jobs in the current shell context and succeeds silently when there are none. A specific job uses `%N`; a missing `%`, empty suffix, nonnumeric suffix, or negative suffix returns 1 with `nsh: invalid job id \`TEXT'\n` (the diagnostic omits the percent), while an unknown numeric job, including zero, returns 1 with `nsh: no such job \`N'\n`. Once a completed job is announced as `[N] Done: COMMAND`, it is removed before a later specific wait. For example, after `sleep 0.01 &`, allowing it to complete prints `[1] Done: sleep 0.01\n`; a later `wait %1` writes `nsh: no such job \`1'\n`. Waiting for all must not return before job output completes. Multiple job operands are rejected. `fg` and `bg` use the same `%N` validation and return `nsh: no jobs to run\n` when invoked with no available job; valid jobs are resumed or brought to the foreground.

For `wait`, `fg`, `bg`, and `jobs`, `--help` is treated as a builtin parse result on stderr and status 1. `wait --help` writes nothing to stdout and writes exactly this text to stderr:

```text
wait: wait 0.4.2
wait command.

USAGE:
    wait [job_id]

FLAGS:
    -h, --help       Prints help information
    -V, --version    Prints version information

ARGS:
    <job_id>    

```

`wait --version` returns 1, writes exactly `wait 0.4.2` to stdout without a newline, and writes exactly `wait: \n\n` to stderr. For `fg`, `bg`, and `jobs`, retain the generic help result with a `NAME 0.4.2` header, `NAME command.`, usage, `-h/--help`, and `-V/--version`. Each `--version` form returns 1 and writes `NAME 0.4.2` to stdout without a newline. Their exact stderr differs: `fg --version` writes `nsh: fg: \n\n`, `bg --version` writes `bg: \n\n`, and `jobs --version` writes `fg: \n\n`. Unknown flags and excess operands return 1 with the same `Found argument ... wasn't expected` usage layout used by other builtin parsers. Preserve the same historical diagnostic prefixes for those parser errors: `fg` errors start `nsh: fg:`, `bg` errors start `bg:`, and `jobs` parser errors start `fg:`.

## Spec 31

Interactive mode has no banner, but its initial prompt is an ANSI-rendered two-frame redraw rather than plain `DISPLAY_CWD $ ` bytes. At terminal width `W`, startup writes `\x1b[1m\x1b[7m$\x1b[0m`, then exactly `W - 1` ASCII spaces, then `\r\x1b[36m\x1b[1mDISPLAY_CWD $\x1b[0m `. `DISPLAY_CWD` abbreviates the home directory: it is exactly `~` when the current directory equals `$HOME`, and a descendant is displayed as `~/` followed by its path relative to `$HOME`; a current directory outside `$HOME` is displayed as its absolute path. The final visible prompt is therefore a cyan, bold displayed cwd and dollar sign followed by an unstyled space. For example, starting with both `HOME` and the current directory set to the same directory renders `\x1b[36m\x1b[1m~ $\x1b[0m `, and a successful `cd sub` changes a later prompt to `\x1b[36m\x1b[1m~/sub $\x1b[0m `. After Enter, the typed command remains visible, its output follows, and a new styled prompt is shown. Assignments, aliases/functions from rc files, functions defined interactively, and prior command status persist. Empty Enter shows another prompt. Ctrl-D on an empty editor exits.

Parse/execute each submitted line immediately. An incomplete multiline construct is reported as a parse error rather than opening a continuation prompt, and the shell remains interactive afterward. Unknown commands report the normal diagnostic and return to a prompt. The terminal renderer must handle Unicode and resizing/snapshot capture without emitting a startup banner or corrupting the line.

## Spec 32

The interactive editor supports insertion at the cursor, Left/Right, Home or Ctrl-A to the start, End or Ctrl-E to the end, Backspace before the cursor, and Delete under it. Ctrl-W deletes the previous word together with its separating whitespace; Ctrl-K deletes from cursor through end of line. In ordinary editing mode, Ctrl-C cancels and clears the current input without exiting; completion mode has the exception in Spec 33. Ctrl-L clears the viewport and redraws a usable prompt. Unsupported control sequences, random Ctrl combinations, function keys, and repeated Tab presses must neither crash nor terminate the shell.

The editor must produce the edited command, not the keystroke stream: cursor insertion/deletion and recalled-history edits are executed exactly as displayed.

## Spec 33

Tab enters a completion-selection mode. At an empty prompt, show a substantial command list; in command position—including after `|`, `;`, `&&`, after `then` in an unfinished `if`, and inside `$(...)`—offer builtins and executable names from `PATH`, so prefixes such as `ec` include `echo`. In argument position, offer entries in the current directory matching the current prefix, including directories and names containing spaces. Display space-containing candidates with backslash escaping. No-match completion preserves the typed input. Pressing Tab in a still-incomplete `${VAR:=...}` construct must preserve the visible construct and keep the shell responsive.

When many candidates exist, render at least three columns when terminal width permits. Down moves selection; PageDown/PageUp move through pages. Enter inserts the selected candidate and returns to ordinary editing. A standalone Escape cancels completion while preserving the original line. Ctrl-C received while completion is active does not clear that line: it redraws the same nonempty input, so a following Ctrl-D does not exit. To clear such input, completion must first process Escape as a standalone key and return to ordinary editing; a subsequent Ctrl-C then clears it. If Escape and Ctrl-C arrive adjacently as the byte sequence `\x1b\x03`, the editor consumes them without either cancellation or clearing. Thus after any of `true | ec`, `true; ec`, `true && ec`, `if true; then ec`, or `echo $(ec`, sending Tab followed by `\x1b\x03` and Ctrl-D leaves the process running with the original nonempty input. The same adjacent sequence after Tab has inserted `unique\ space` leaves that completed text in the editor, and after no-match completion it preserves the unmatched text. Multiple consecutive Tab operations remain safe.

Parse `LS_COLORS` defensively for directory (`di`), executable (`ex`), extensionless regular-file (`no`), and `*.extension` styles. Recognize SGR components including bold `01`, blink `05`, and foreground colors 31 through 36. Apply the appropriate style in terminal output and reset it afterward. Empty, malformed, or unsupported entries are ignored without a crash. Completion must work without depending on any non-harness service.

## Spec 34

The implementation must be robust for inputs used as stress cases: Unicode variable/string/file names, embedded tabs and newlines, a command line of at least ten thousand characters, many variables and arguments, scripts of roughly a thousand commands, deep nested subshells/functions/loops, long pipelines, multi-megabyte redirected files, and binary pipe data. The `$#` count cap from Spec 23 applies even in many-argument stress cases. Do not impose small fixed buffers, decode arbitrary child output in a way that changes bytes, or deadlock because a producer and consumer are waited sequentially.

Signals and terminal control must leave interactive mode usable after Ctrl-C, and asynchronous children must be reaped. All errors described above must be returned as process status and diagnostics rather than causing an uncontrolled crash, except for the deliberately observed status-101 panic-handler paths for file-open startup failure (Spec 3), arithmetic expansion inside double quotes (Spec 7), division by zero (Spec 16), the no-final-newline two-here-document case (Spec 19), and an unconsumed `break` after its loop condition fails (Spec 22).
