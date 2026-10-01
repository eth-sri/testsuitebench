# Clarified specification for `executable`

## Spec 1

The required artifact is one runnable file named exactly `executable` at the workspace root. It is a UTF-8 command-line program implementing Melody 0.20.0: a small language that compiles readable pattern declarations to a single ECMAScript-style regular-expression string. It must work regardless of its current working directory and must not load implicit configuration from `HOME`, `XDG_CONFIG_HOME`, `.melodyrc`, or similar locations.

Unless a later section specifies an error, successful operations exit with status 0. All ordinary text is UTF-8. Compilation must comfortably handle at least 1,000-character literals, patterns producing more than 1 KiB of output, 100-way alternations, twenty nested groups, large input/test files of at least 20 KiB, and repetition counts at least as large as 999,999.

## Spec 2

The command syntax is:

```text
executable [OPTIONS] [INPUT_FILE_PATH]
```

It accepts at most one source path. The options and aliases are:

```text
-o, --output OUTPUT_FILE_PATH
-n, --no-color
-r, --repl
    --generate-completions SHELL
-t, --test STRING
-f, --test-file TEST_FILE
-h, --help
-V, --version
```

Options may precede or follow the source path. `--` ends option parsing; thus `executable -- --help` tries to read a source file literally named `--help`. A value-taking option may not consume the `--` marker as its value. Options that are defined once, such as `--test`, may not be repeated.

`--output`, `--repl`, `--generate-completions`, `--test`, and `--test-file` are output/action modes. `--test` conflicts with `--test-file` and `--output`; `--test-file` conflicts with `--output`; completion generation and REPL likewise do not combine with compilation-output/test modes. Argument syntax/conflict failures exit 2, write nothing to stdout, and use the argument-error behavior in Spec 28.

## Spec 3

`--help` exits 0 and writes nothing to stderr. In an uncolored invocation it writes exactly the following, including its final newline. `-h` is its successful short form and displays the same usage, arguments, and option documentation. When color is enabled, the visible text after stripping ANSI SGR sequences is still exactly this text; Spec 30 defines the styling exception.

```text
A CLI wrapping the Melody language compiler

Usage: executable [OPTIONS] [INPUT_FILE_PATH]

Arguments:
  [INPUT_FILE_PATH]  Read from a file
                     Use '-' and or pipe input to read from stdin

Options:
  -o, --output <OUTPUT_FILE_PATH>           Write to a file
  -n, --no-color                            Print output with no color
  -r, --repl                                Start the Melody REPL
      --generate-completions <completions>  Outputs completions for the selected shell
                                            To use, write the output to the appropriate location for your shell
  -t, --test <test>                         Test the compiled regex against a string
  -f, --test-file <test-file>               Test the compiled regex against the contents of a file
  -h, --help                                Print help
  -V, --version                             Print version
```

`-V` and `--version` exit 0, write nothing to stderr, and write exactly `melody_cli 0.20.0\n` to stdout.

## Spec 4

Source acquisition follows these rules:

- A non-`-` positional path is opened and decoded as UTF-8. Its extension is irrelevant; `.mdy`, `.melody`, `.mel`, `.txt`, and extensionless paths are all treated alike.
- A positional `-` means read the complete source from stdin.
- With no positional path, read the complete source from stdin when stdin is not a terminal. This includes an empty pipe/EOF.
- Empty, whitespace-only, and comments-only sources are valid and compile to the empty regex.
- If no path is supplied (or `-` is supplied) while stdin is a terminal, do not wait for keyboard source input; use the no-input behavior in Spec 31.
- A nonexistent path, a directory, unreadable bytes, or invalid UTF-8 is a source-read failure as specified in Spec 29.

Read all input before compiling. Source content and file paths may contain Unicode.

## Spec 5

In normal compile mode, concatenate every emitted fragment into one regex without separators or formatting whitespace. On success:

- Without `--output`, stdout is the regex followed by exactly one newline; stderr is empty. Therefore an empty program writes just `\n`.
- With `-o PATH`/`--output PATH`, create or completely overwrite `PATH` with exactly the regex bytes, with no final newline and no ANSI escapes; stdout and stderr are empty.
- Do not create missing parent directories. Long regexes remain one physical output line except that regex escape sequences such as the two characters `\` and `n` remain part of that line.

For example, source `"#"; some of <word>;` produces `#\w+`, and source `5 to 10 of "a"; <space>; option of "b"; 2 of <digit>; either { "foo"; "bar"; "baz"; }` produces `a{5,10} b?\d{2}(?:foo|bar|baz)`.

## Spec 6

Outside quoted or raw literals, spaces, tabs, carriage returns, and newlines are insignificant. An atomic statement ends in `;`. Block constructs end at their closing `}` and need no semicolon. Any number of statements may occur on one line or across lines.

A `//` comment is recognized only when `//` is the first non-whitespace text on its source line; ignore it through the end of that line. It is not a trailing-comment form: for example, `"a";//tail` is a syntax error at line 1, column 5, the first `/`. Ignore `/* ... */` across any number of lines, including when it directly follows a statement. Comment text emits nothing. An unterminated block comment is a syntax error. Empty programs and empty raw expressions are allowed.

At the root and in ordinary block bodies, statements preserve source order and their regex fragments are concatenated. Thus `"a"; "b"; <digit>;` becomes `ab\d`. No optimizer may merge ranges, flatten explicitly nested groups, remove explicit quantifier forms, or deduplicate captures.

## Spec 7

Single-quoted and double-quoted strings are literal pattern text. Strip their delimiters, unescape the delimiter when preceded by backslash, and regex-escape every literal occurrence of:

```text
[ ] ( ) { } * + ? | ^ $ . \
```

Characters such as `/`, `-`, `_`, `#`, `@`, `=`, `:`, and ordinary Unicode remain unchanged. The two quote styles otherwise behave alike. Examples:

```text
"[](){}*+?|^$.";  ->  \[\]\(\)\{\}\*\+\?\|\^\$\.
'hello \'quoted\''; -> hello 'quoted'
"hello \"quoted\""; -> hello "quoted"
"\\"; -> \\
```

Recognized escaped control/unicode sequences such as `\n`, `\t`, `\r`, and `\u0041` remain regex escape sequences in the output rather than becoming literal source line breaks or being double-escaped. For example, `2 of "\n";` becomes `\n{2}`. An actual UTF-8 literal such as `"café 😀 مرحبا 日本語";` preserves those characters and their order. The empty literal `"";` is valid and emits nothing. Invalid escapes (for example `"\x";` without required digits) and unterminated strings are syntax errors.

## Spec 8

A raw regex is delimited by backticks and followed by `;`, for example `` `[a-z]+`; ``. Its contents pass through without literal escaping. It may be empty and may contain non-backslash regex constructs such as `[a-z]+` or `(?=[a-z])`. Within raw content, backslash is accepted only in the sequence `\``; that sequence emits a literal backtick and does not close the raw expression. A bare backslash or any other backslash sequence is rejected as a syntax error. Thus raw content cannot be used to spell escapes such as `\d`, and `` `\d+`; `` is invalid. An unterminated raw expression is also a syntax error.

Raw fragments compose normally inside captures, alternations, assertions, and variables. Examples:

```text
capture { `[a-z]+`; }          -> ([a-z]+)
either { `[0-9]+`; "text"; }   -> (?:[0-9]+|text)
3 of `[abc]`;                  -> [abc]{3}
lazy 2 to 4 of `[a-z]+`;       -> (?:[a-z]+){2,4}?
`a\`b`;                        -> a`b
```

## Spec 9

A character range is `START to END;`, where each endpoint is one unquoted character. Emit `[START-END]`, retaining the requested endpoints even when equal. This includes letters, digits, and punctuation: `a to z;` -> `[a-z]`, `0 to 9;` -> `[0-9]`, `! to /;` -> `[!-/]`, and `A to A;` -> `[A-A]`. `not START to END;` emits `[^START-END]`. Sequential ranges remain separate.

The distinct negative character-class form is `not CLASS_CONTENT;`, where the non-whitespace class content is copied between `[^` and `]`. Examples are `not abc123;` -> `[^abc123]`, `not a_b_c;` -> `[^a_b_c]`, and `not @#$%^&*;` -> `[^@#$%^&*]`. This form is a single consuming atom and can appear in groups, alternations, and quantifiers. `not "quoted";` is not this form and is invalid.

## Spec 10

Built-in angle-bracket symbols have these exact regex expansions:

| Melody | Positive output | `not` output |
|---|---|---|
| `<start>` | `^` | invalid: `negative start not allowed` |
| `<end>` | `$` | invalid: `negative end not allowed` |
| `<char>` | `.` | invalid: `negative char not allowed` |
| `<whitespace>` | `\s` | `\S` |
| `<newline>` | `\n` | `[^\n]` |
| `<tab>` | `\t` | `[^\t]` |
| `<return>` | `\r` | `[^\r]` |
| `<feed>` | `\f` | `[^\f]` |
| `<null>` | `\0` | `[^\0]` |
| `<digit>` | `\d` | `\D` |
| `<word>` | `\w` | `\W` |
| `<vertical>` | `\v` | `[^\v]` |
| `<alphabetic>` | `[a-zA-Z]` | `[^a-zA-Z]` |
| `<alphanumeric>` | `[a-zA-Z0-9]` | `[^a-zA-Z0-9]` |
| `<space>` | one literal ASCII space | `[^ ]` |
| `<boundary>` | `\b` | `\B` |
| `<backspace>` | `[\b]` | `[^\b]` |

Unknown unqualified names fail with `Error: usage of an unrecognized symbol\n`. A name containing `::` in any namespace other than `category` fails with `Error: usage of an unrecognized symbol namespace\n`.

## Spec 11

Unicode general-category symbols use `<category::NAME>` and emit `\p{CODE}`. Prefixing `not` emits `\P{CODE}`. The complete supported map is:

| NAME | CODE | NAME | CODE |
|---|---|---|---|
| `cased_letter` | `L&` | `close_punctuation` | `Pe` |
| `connector_punctuation` | `Pc` | `control` | `Cc` |
| `currency_symbol` | `Sc` | `dash_punctuation` | `Pd` |
| `decimal_digit_number` | `Nd` | `enclosing_mark` | `Me` |
| `final_punctuation` | `Pf` | `format` | `Cf` |
| `initial_punctuation` | `Pi` | `letter_number` | `Nl` |
| `letter` | `L` | `line_separator` | `Zl` |
| `lowercase_letter` | `Ll` | `mark` | `M` |
| `math_symbol` | `Sm` | `modifier_letter` | `Lm` |
| `modifier_symbol` | `Sk` | `non_spacing_mark` | `Mn` |
| `number` | `N` | `open_punctuation` | `Ps` |
| `other_letter` | `Lo` | `other_number` | `No` |
| `other_punctuation` | `Po` | `other_symbol` | `So` |
| `other` | `C` | `paragraph_separator` | `Zp` |
| `private_use` | `Co` | `punctuation` | `P` |
| `separator` | `Z` | `space_separator` | `Zs` |
| `spacing_combining_mark` | `Mc` | `surrogate` | `Cs` |
| `symbol` | `S` | `titlecase_letter` | `Lt` |
| `unassigned` | `Cn` | `uppercase_letter` | `Lu` |

These are directly quantifiable: `5 of <category::letter>;` -> `\p{L}{5}`, and `3 of not <category::number>;` -> `\P{N}{3}`. An unknown category fails with `Error: usage of an unrecognized unicode category\n`.

## Spec 12

There are three recursive group forms:

```text
match { STATEMENTS }              -> (?:CONCATENATED_BODY)
capture { STATEMENTS }            -> (CONCATENATED_BODY)
capture IDENTIFIER { STATEMENTS } -> (?<IDENTIFIER>CONCATENATED_BODY)
```

Identifiers are case-sensitive, begin with a letter or underscore, and may continue with letters or underscores. Digits are not accepted anywhere in an identifier: `capture Exact_Name2 { "x"; }` is a syntax error at the `2`, with expectation `block`. Preserve accepted names exactly. `match` never accepts a name. Captures nest without flattening; for example `capture outer { match { capture inner { either { "x"; "y"; } } } }` becomes `(?<outer>(?:(?<inner>(?:x|y))))`.

`either { ... }` treats each direct body statement as one alternative in order, and emits one noncapturing alternation `(?:ALT1|ALT2|...)`. To make a multi-statement alternative, wrap it in `match`; the `match` group's own noncapturing wrapper is preserved inside the alternation. Preserve nested `either` wrappers. Examples:

```text
either { "a"; "b"; "c"; }                     -> (?:a|b|c)
either { match { "a"; "b"; } "c"; }            -> (?:(?:ab)|c)
either { either { "a"; "b"; } "c"; }           -> (?:(?:a|b)|c)
either { capture a { "a"; } capture b { "b"; } } -> (?:(?<a>a)|(?<b>b))
```

## Spec 13

Assertions are recursive blocks with concatenated bodies:

```text
ahead { ... }      -> (?=...)
not ahead { ... }  -> (?!...)
behind { ... }     -> (?<=...)
not behind { ... } -> (?<!...)
```

They may contain literals, symbols, ranges, groups, variable invocations, quantifiers, and nested assertions. For example `ahead { some of "a"; <digit>; }` -> `(?=a+\d)`, and `ahead { behind { "x"; } }` -> `(?=(?<=x))`. Only the keywords `ahead` and `behind` are valid assertion types.

Assertions themselves cannot be the target of a quantifier. Both positive and negative cases fail with `Error: unexpected assertion in quantifier\n`.

## Spec 14

Quantifiers precede exactly one target expression and preserve their source form:

| Melody prefix | Regex suffix |
|---|---|
| `N of` | `{N}` |
| `MIN to MAX of` | `{MIN,MAX}` |
| `over N of` | `{N+1,}` |
| `some of` | `+` |
| `any of` | `*` |
| `option of` | `?` |

`lazy` may precede any of these and appends a further `?`: `lazy some of "a";` -> `a+?`, `lazy any of "a";` -> `a*?`, `lazy option of "a";` -> `a??`, `lazy 5 of "a";` -> `a{5}?`, `lazy over 5 of "a";` -> `a{6,}?`, and `lazy 5 to 6 of "a";` -> `a{5,6}?`.

Counts are unsigned decimal integers. Zero is legal (`0 of "a";` -> `a{0}`), one is not simplified (`a{1}`), equal bounded counts remain bounded (`7 to 7` -> `{7,7}`), and `0 to 5` remains `{0,5}`. A bounded minimum greater than its maximum is invalid. `over` must be incrementable; overflow while calculating `N+1` fails with text containing `could not parse an amount`.

## Spec 15

Quantifier scope and grouping are structural:

- Direct single regex atoms receive the suffix directly: `"A"` -> `A{5}`, `<digit>` -> `\d{5}`, `a to z` -> `[a-z]+`, `not abc` -> `[^abc]+`, and `<alphabetic>` -> `[a-zA-Z]+`.
- A multi-character quoted literal is wrapped before repetition: `3 of "abc";` -> `(?:abc){3}`. A multi-character escaped sequence representing one regex atom, such as `\n`, stays direct: `\n{2}`.
- A raw fragment that is exactly one atom/class stays direct (`[abc]{3}`); a compound raw fragment is wrapped (`(?:[a-z]+){2,4}?`).
- `match`, `either`, and `capture` already provide their required grouping; put the quantifier after that group without adding or moving parentheses. Thus `some of capture { "a"; }` -> `(a)+`, while `capture { some of "a"; }` -> `(a+)`.

Nested quantifiers are syntactically invalid. `<start>` and `<end>` are zero-width special symbols and cannot be quantified; fail with `Error: unexpected special symbol in quantifier\n`. `<boundary>` is quantifiable despite also being zero-width, using the ordinary suffix rules: `any of <boundary>;` emits `\b*`, `some of <boundary>;` emits `\b+`, and `2 of <boundary>;` emits `\b{2}`. A direct variable invocation cannot be quantified; fail with `Error: unexpected variable invocation in quantifier\n`. A variable declaration used as the target fails with `Error: unexpected skipped node in quantifier\n`.

`lazy` is a modifier for one of the six quantifier prefixes, not an independent quantifier. Therefore `lazy "a";` is a syntax error, as are repeated modifiers such as `lazy lazy some of "a";`.

## Spec 16

Variables are declared and invoked as follows:

```text
let .NAME = { STATEMENTS }
.NAME;
```

A declaration compiles its body at that point, stores the resulting fragment, and emits nothing. An invocation emits the stored fragment verbatim. Names follow the identifier rules from Spec 12. Definitions are processed in source order, can reference already defined variables, can contain any otherwise legal construct, and may be invoked repeatedly at the root or within groups, alternations, or assertions.

Redefinition is allowed and affects only later invocations. For example:

```text
let .x = { "first"; } .x;
let .x = { "second"; } .x;
```

emits `firstsecond`. An invocation before a definition fails with `Error: usage of an uninitialized variable\n`. Directly quantifying `.NAME` is invalid even though a definition may itself contain quantified content.

## Spec 17

The compiler must preserve explicit structure in arbitrary combinations. Representative exact results are:

```text
3 of match { 5 of "A"; 0 to 9; }
-> (?:A{5}[0-9]){3}

capture email { some of a to z; "@"; some of a to z; "."; 2 to 4 of a to z; }
-> (?<email>[a-z]+@[a-z]+\.[a-z]{2,4})

some of capture { either { "a"; "b"; } }
-> ((?:a|b))+

lazy some of either { capture first { "a"; } capture second { "b"; } }
-> (?:(?<first>a)|(?<second>b))+?

capture outer { 2 of match { capture inner { "x"; } } }
-> (?<outer>(?:(?<inner>x)){2})

some of not 0 to 9; any of not a to z;
-> [^0-9]+[^a-z]*
```

No whitespace from source formatting appears in output unless it came from a quoted literal or `<space>`.

## Spec 18

After syntactic parsing, semantic/compiler failures exit 65, write nothing to stdout, and write exactly one plain line to stderr (plus `\n`) unless colors are enabled. Required messages are:

```text
Error: usage of an invalid quantifier range
Error: usage of an unrecognized symbol
Error: usage of an unrecognized symbol namespace
Error: usage of an unrecognized unicode category
Error: usage of an uninitialized variable
Error: negative start not allowed
Error: negative end not allowed
Error: negative char not allowed
Error: unexpected special symbol in quantifier
Error: unexpected assertion in quantifier
Error: unexpected variable invocation in quantifier
Error: unexpected skipped node in quantifier
```

Only the first detected error is reported. In particular, invalid source must be rejected before trying test mode, writing an output file, or reporting a match.

## Spec 19

Syntax errors exit 65, leave stdout empty, and write a deterministic annotated diagnostic to stderr. In plain mode its shape is exactly:

```text
Error:  --> LINE:COLUMN
  |
LINE | complete offending source line
  | COLUMN_PADDING^---
  |
  = expected EXPECTATION
```

`COLUMN_PADDING` is the number of display spaces needed to place `^` under the reported 1-based column. Preserve Unicode source in the displayed line. Report the first syntax failure. The following cases define required positions and expectation phrases:

| Source condition | Position | `EXPECTATION` |
|---|---:|---|
| a lone `"`, an unterminated quoted/raw literal, `-1 of "a";`, or `abc of "x";` | 1:1 | `root` |
| `some of` at EOF | 1:8 | `literal, raw, not, range, group_declaration, assertion_declaration, variable_declaration, or variable_invocation` |
| `5 of` at EOF | 1:5 | same phrase as the preceding row |
| `some of some of "a";` | 1:9 | same phrase as the preceding row |
| `lazy lazy some of "a";` | 1:6 | `amount, some, any, option, or over` |
| `over abc of "a";` | 1:6 | `amount` |
| `capture 123 { "a"; }` | 1:9 | `block or identifier` |
| `match NAME { "a"; }` | 1:7 | `block` |
| `either NAME { "a"; }` | 1:8 | `block` |
| `capture test {` at EOF | 1:15 | `literal, raw, not, range, quantifier_quantity, group_declaration, assertion_declaration, variable_declaration, or variable_invocation` |
| `match {` at EOF | 1:8 | same phrase as the preceding row |
| `either {` at EOF | 1:9 | same phrase as the preceding row |
| `not "x";` | quote column | `amount, class_content, or assertion_type` |
| `some of <word>` with its required semicolon missing | 1:9 | `literal, not, range, group_declaration, assertion_declaration, or variable_declaration` |
| `5 of "x"` with its required semicolon missing | 1:6 | `group_declaration, assertion_declaration, or variable_declaration` |

At an unexpected EOF inside a multiline block, report the EOF position even when the final source line is blank. For the exact source `match {\n  "a";\n\n`, report line 3, column 1, display an empty line 3, and use the same expectation as the unclosed-block rows. Text that cannot begin any root construct reports position 1:1 with expectation `root`; the displayed offending line is preserved in full.

For example, `match test { "a"; }` must produce exactly:

```text
Error:  --> 1:7
  |
1 | match test { "a"; }
  |       ^---
  |
  = expected block
```

## Spec 20

`-t STRING`/`--test STRING` compiles the Melody source, constructs a Unicode-capable ECMAScript-style regex from the result, and performs an unanchored search for any match in `STRING`. It does not require the entire string to match unless the source uses `<start>` and `<end>`. Hence `"hello";` matches `hello world`, `2 to 4 of "a";` matches the first four characters of `aaaaa`, and `option of "a";` matches even a string containing only `b` via a zero-length match.

Regex shorthand behavior is ECMAScript-like: `\w` is ASCII letters/digits/underscore (so `#ümlaut` does not match `#\w+`), `\d` matches digits, `.` does not consume a newline, assertions have normal lookaround semantics, and Unicode property escapes use the `\p{...}`/`\P{...}` forms from Spec 11. Newlines and tabs in the test string are real characters and are searchable by `\n` and `\t`.

A match and a non-match are both successful operations and exit 0.

## Spec 21

Plain `--test` reporting is exactly one stdout line and no stderr:

```text
'PREVIEW' matched
'PREVIEW' did not match
```

Surround the preview in literal single quotes without escaping its contents. Count Unicode scalar characters, not UTF-8 bytes. If the input has at most 10 characters, show all of it. If it has more than 10, show its first 10 characters followed by `...`. Thus 10 `a` characters are shown without dots; 11 are `aaaaaaaaaa...`; `hello world` is `hello worl...`; and an empty string is shown as `''`. Embedded newlines remain embedded in this display and count toward ten.

`-f PATH`/`--test-file PATH` reads the complete UTF-8 contents and applies the same unanchored search. Its report displays the path, never a content preview:

```text
PATH matched
PATH did not match
```

This also exits 0 for a non-match and works for empty, multiline, Unicode, and large files.

## Spec 22

Completion generation accepts only the case-sensitive names `bash`, `zsh`, `fish`, `elvish`, and `powershell`. It needs no source input. A supported name exits 0, writes the shell script specified in Specs 23–27 to stdout, and writes nothing to stderr.

Any other spelling also exits 0 but writes nothing to stdout and writes exactly, substituting the supplied spelling:

```text
Unknown or unsupported shell: 'SHELL'
Try one of: 'bash', 'zsh', 'fish', 'elvish', 'powershell'

```

The final blank line is significant: the stderr text ends in two newline characters.

## Spec 23

For `--generate-completions bash`, stdout is exactly:

```bash
_melody() {
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
                cmd="melody"
                ;;
            *)
                ;;
        esac
    done

    case "${cmd}" in
        melody)
            opts="-o -n -r -t -f -h -V --output --no-color --repl --generate-completions --test --test-file --help --version [INPUT_FILE_PATH]"
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                --output)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -o)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --generate-completions)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --test)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -t)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --test-file)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -f)
                    COMPREPLY=($(compgen -f "${cur}"))
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
    complete -F _melody -o nosort -o bashdefault -o default melody
else
    complete -F _melody -o bashdefault -o default melody
fi
```

There is exactly one newline after `fi`.

## Spec 24

For `--generate-completions zsh`, stdout is exactly:

```zsh
#compdef melody

autoload -U is-at-least

_melody() {
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
'-o+[Write to a file]:OUTPUT_FILE_PATH:_default' \
'--output=[Write to a file]:OUTPUT_FILE_PATH:_default' \
'(-o --output -r --repl)--generate-completions=[Outputs completions for the selected shell To use, write the output to the appropriate location for your shell]:completions:_default' \
'(--generate-completions -r --repl -o --output)-t+[Test the compiled regex against a string]:test:_default' \
'(--generate-completions -r --repl -o --output)--test=[Test the compiled regex against a string]:test:_default' \
'(--generate-completions -r --repl -o --output -t --test)-f+[Test the compiled regex against the contents of a file]:test-file:_default' \
'(--generate-completions -r --repl -o --output -t --test)--test-file=[Test the compiled regex against the contents of a file]:test-file:_default' \
'-n[Print output with no color]' \
'--no-color[Print output with no color]' \
'-r[Start the Melody REPL]' \
'--repl[Start the Melody REPL]' \
'-h[Print help]' \
'--help[Print help]' \
'-V[Print version]' \
'--version[Print version]' \
'::input -- Read from a file
Use '\''-'\'' and or pipe input to read from stdin:_default' \
&& ret=0
}

(( $+functions[_melody_commands] )) ||
_melody_commands() {
    local commands; commands=()
    _describe -t commands 'melody commands' commands "$@"
}

if [ "$funcstack[1]" = "_melody" ]; then
    _melody "$@"
else
    compdef _melody melody
fi
```

There is exactly one newline after `fi`.

## Spec 25

For `--generate-completions fish`, stdout is exactly:

```fish
complete -c melody -s o -l output -d 'Write to a file' -r
complete -c melody -l generate-completions -d 'Outputs completions for the selected shell To use, write the output to the appropriate location for your shell' -r
complete -c melody -s t -l test -d 'Test the compiled regex against a string' -r
complete -c melody -s f -l test-file -d 'Test the compiled regex against the contents of a file' -r
complete -c melody -s n -l no-color -d 'Print output with no color'
complete -c melody -s r -l repl -d 'Start the Melody REPL'
complete -c melody -s h -l help -d 'Print help'
complete -c melody -s V -l version -d 'Print version'
```

There is exactly one final newline.

## Spec 26

For `--generate-completions elvish`, stdout begins with a newline and is exactly:

```elvish

use builtin;
use str;

set edit:completion:arg-completer[melody] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'melody'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'melody'= {
            cand -o 'Write to a file'
            cand --output 'Write to a file'
            cand --generate-completions 'Outputs completions for the selected shell To use, write the output to the appropriate location for your shell'
            cand -t 'Test the compiled regex against a string'
            cand --test 'Test the compiled regex against a string'
            cand -f 'Test the compiled regex against the contents of a file'
            cand --test-file 'Test the compiled regex against the contents of a file'
            cand -n 'Print output with no color'
            cand --no-color 'Print output with no color'
            cand -r 'Start the Melody REPL'
            cand --repl 'Start the Melody REPL'
            cand -h 'Print help'
            cand --help 'Print help'
            cand -V 'Print version'
            cand --version 'Print version'
        }
    ]
    $completions[$command]
}
```

There is exactly one newline after `}`.

## Spec 27

For `--generate-completions powershell`, stdout begins with a newline and is exactly:

```powershell

using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'melody' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'melody'
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
        'melody' {
            [CompletionResult]::new('-o', '-o', [CompletionResultType]::ParameterName, 'Write to a file')
            [CompletionResult]::new('--output', '--output', [CompletionResultType]::ParameterName, 'Write to a file')
            [CompletionResult]::new('--generate-completions', '--generate-completions', [CompletionResultType]::ParameterName, 'Outputs completions for the selected shell To use, write the output to the appropriate location for your shell')
            [CompletionResult]::new('-t', '-t', [CompletionResultType]::ParameterName, 'Test the compiled regex against a string')
            [CompletionResult]::new('--test', '--test', [CompletionResultType]::ParameterName, 'Test the compiled regex against a string')
            [CompletionResult]::new('-f', '-f', [CompletionResultType]::ParameterName, 'Test the compiled regex against the contents of a file')
            [CompletionResult]::new('--test-file', '--test-file', [CompletionResultType]::ParameterName, 'Test the compiled regex against the contents of a file')
            [CompletionResult]::new('-n', '-n', [CompletionResultType]::ParameterName, 'Print output with no color')
            [CompletionResult]::new('--no-color', '--no-color', [CompletionResultType]::ParameterName, 'Print output with no color')
            [CompletionResult]::new('-r', '-r', [CompletionResultType]::ParameterName, 'Start the Melody REPL')
            [CompletionResult]::new('--repl', '--repl', [CompletionResultType]::ParameterName, 'Start the Melody REPL')
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

There is exactly one newline after `}`.

## Spec 28

Command-line parsing errors use clap-style plain diagnostics on stderr and exit 2. The canonical unknown-option form is exactly:

```text
error: unexpected argument '--invalid-flag' found

  tip: to pass '--invalid-flag' as a value, use '-- --invalid-flag'

Usage: executable [OPTIONS] [INPUT_FILE_PATH]

For more information, try '--help'.
```

There is one final newline. Substitute the actual option for other unknown options. A second positional input similarly reports it as an unexpected argument and includes `Usage: executable`.

A missing value reports a line containing the option's canonical signature, for example:

```text
a value is required for '--output <OUTPUT_FILE_PATH>' but none was supplied
a value is required for '--test <test>' but none was supplied
```

A repeated `-t`/`--test` reports that `--test <test>` `cannot be used multiple times`. Conflicts report both canonical arguments and `cannot be used with`, including these phrases when applicable:

```text
the argument '--test <test>' cannot be used with '--test-file <test-file>'
the argument '--output <OUTPUT_FILE_PATH>' cannot be used with '--test <test>'
```

Help and version are successful action flags when used normally. After `--`, strings resembling options are positional values instead.

## Spec 29

Runtime I/O errors are plain `Error:` messages on stderr with empty stdout:

- A source input path that cannot be read as a UTF-8 regular file exits 65 and writes `Error: unable read file at path PATH\n`.
- A test-file path that cannot be read exits 74 and writes `Error: unable read file at path PATH\n`.
- An output path that cannot be created or overwritten exits 74 and writes `Error: PATH\n`.

Do not create missing parent directories. Examples include directories passed as source files, `/nonexistent/file.mdy`, `/nonexistent/test.txt`, `/nonexistent/dir/output.txt`, and read-only special files such as `/proc/version`. Successful file output must create a missing final file and replace, rather than append to, an existing one.

## Spec 30

Color is presentation only. Never put ANSI escapes into an output file, version text, or generated completions. Help text is plain when captured normally, but `CLICOLOR_FORCE=1` styles captured help: `Usage:`, `Arguments:`, and `Options:` are bold and underlined using `\x1b[1m\x1b[4m`, and option spellings are bold. Without forced color, stdout/stderr captured by a pipe are otherwise plain, except for the REPL-validation case specified in Spec 31. When the relevant output stream is a terminal:

- A compiled regex is wrapped in bright blue `\x1b[94m` and reset with `\x1b[0m`.
- A matched status is bright green `\x1b[92m`; a did-not-match status and errors are bright red `\x1b[91m`; reset with `\x1b[0m`.
- The text content after removing ANSI SGR sequences is exactly the plain output described elsewhere.

`-n`/`--no-color` suppresses all ANSI escapes on both stdout and stderr, even on a terminal and even when forced. A nonempty `CLICOLOR_FORCE` (in particular `CLICOLOR_FORCE=1`) enables color even when output is captured. If both `CLICOLOR_FORCE=1` and `NO_COLOR=1` are present, forced color wins. `NO_COLOR=1` without a force disables color.

## Spec 31

With no source path and terminal stdin, normal mode exits 66. The two informational lines are written to stderr, exactly:

```text
No input file supplied and no input piped
Try adding a path argument: 'melody ./file.mdy'
```

Stdout begins with one newline and then contains the help text from Spec 3, except that its usage line is exactly `Usage: melody_cli [OPTIONS] [INPUT_FILE_PATH]` (the fixed internal program name is significant in this one path). Stdout ends with the help text's final newline. When stdout and stderr refer to the same terminal, their combined visible order is therefore the two informational lines, a blank line, and then the help. In the default terminal presentation the two informational lines are bright blue and reset before the help text. `--no-color` makes both streams plain but does not change this separation. No source read is attempted.

REPL mode (`-r`/`--repl`) requires both stdin and stdout to be terminals. If either is piped/captured, exit 64, leave stdout empty, and in plain presentation write exactly:

```text
Error: repl argument supplied with piped input or output
```

with a final newline. This validation applies even when `--` or a trailing `-` is also present. Color selection for this particular diagnostic follows stdout's terminal status: when stdin and stderr are pipes but stdout is a terminal, stderr is `\x1b[91mError: repl argument supplied with piped input or output\x1b[0m\n` even though stderr itself is captured. `--no-color` suppresses those escapes.

## Spec 32

On a real terminal, `-r`/`--repl` starts an interactive line-oriented REPL and initially displays exactly this plain content, followed by a prompt:

```text
Melody REPL v0.20.0

Commands:

- :u, :undo - undo the latest line
- :r, :redo - redo the latest undo
- :c, :clear - clear all REPL history and previous input
- :s, :source - print all previously entered lines
- :e, :exit - exit the REPL

~ 
```

The prompt is `~ ` and input is echoed normally by the terminal. `:e` and `:exit` terminate promptly with status 0 and restore the terminal. The REPL must function correctly in a normal 120-by-40 tmux pseudo-terminal.

Submitting a nonempty non-command line tentatively appends that entire line to the source history, compiles all retained lines joined with newlines, and displays the current regex followed by a blank line and a new prompt. Submitting an empty line leaves history unchanged and recompiles/displays the current regex; with no history it displays the empty regex presentation without failing.

## Spec 33

REPL history commands have short and long forms and are exact, case-sensitive commands:

- `:s`/`:source`: if history is nonempty, display `source`, then each retained line as `N LINE` with 1-based numbering, then a blank line/prompt. If empty, display `no lines to print`.
- `:u`/`:undo`: move the most recent retained line to a redo stack, display `undo`, and display the regex recompiled from the remaining history when nonempty. With empty history display `nothing to undo`.
- `:r`/`:redo`: restore the most recently undone line, display `redo`, then display the recompiled regex. With an empty redo stack display `nothing to redo`.
- `:c`/`:clear`: clear both history stacks and any pending editor input, display `clear`, and leave the REPL at a fresh prompt. Clearing refers to that editable/history state, not wholesale erasure of the terminal transcript: the welcome banner and unrelated successful command/output transcript from before the command remain visible. When removing previously displayed error text from the active terminal view, it must likewise preserve or redraw the banner and the non-error transcript. The long form has exactly the same display behavior.

Entering a new valid source line after an undo clears the redo stack. Therefore a subsequent redo says `nothing to redo`. If compilation of a tentative line fails, show its diagnostic, remove that line from history, and leave earlier valid lines and their redo state usable. For an error on a second tentative line, diagnostics use line 2.

Any other colon command displays `Error: unrecognized command ":COMMAND"`, followed by a blank line and prompt, without changing history.

## Spec 34

The interactive REPL uses colors regardless of the plain snapshots described above:

- Compiled regex and printed source-line content use bright blue `\x1b[94m`.
- Successful command labels `source`, `undo`, `redo`, and `clear` use bright green `\x1b[92m`.
- Source line numbers use the dim SGR attribute `\x1b[2m`.
- `nothing to undo`, `nothing to redo`, `no lines to print`, compiler/parser errors, `Error:`, and `unrecognized command` use bright red `\x1b[91m`.
- In an unrecognized-command report, the quoted command itself uses bright blue `\x1b[94m` and is followed by the full SGR reset `\x1b[0m`.

For example, after entering `16 of "na";`, the visible plain sequence is:

```text
~ 16 of "na";
(?:na){16}

~ 
```

After `:s`, it continues with `source\n1 16 of "na";\n\n~ `. Invalid source such as `5 of "x"` (missing `;`) displays the annotated error and is not listed by a following `:s`.

## Spec 35

The following end-to-end examples are normative checks on the language composition and output protocol:

```text
Source:
/* comment */
5 of 'A\'';
match { capture test { "x"; "y"; } }
`[abc]`;
either { "a\""; "b"; <char>; }
some of "a";

Regex:
(?:A'){5}(?:(?<test>xy))[abc](?:a"|b|.)a+
```

```text
Source:
<start>;
capture first { some of <digit>; }
"-";
capture second { some of <digit>; }
<end>;

Regex:
^(?<first>\d+)-(?<second>\d+)$
```

The regex appears with one final newline on stdout, without one in `--output` files, and is replaced by the appropriate match-report line in either test mode. All success paths keep stderr empty.
