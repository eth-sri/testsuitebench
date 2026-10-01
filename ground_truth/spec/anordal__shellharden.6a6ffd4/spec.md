# Shellharden-compatible executable specification

## Spec 1: Required artifact and purpose

The deliverable is one directly runnable file named `executable`. It is a command-line program compatible with Shellharden 4.3.1: it parses Bash-like shell source, highlights it, previews or applies a deterministic set of safety rewrites, checks whether those rewrites are needed, and can replace files in place.

The program must operate without invoking a shell, formatter, or other command from `PATH`. Configuration comes only from command-line arguments. In particular, `SHELLHARDEN_MODE`, `NO_COLOR`, `CLICOLOR`, and `SHELL` must not select a mode, disable colors, or otherwise change output, and a `.shellhardenrc` file must not override command-line behavior.

## Spec 2: Invocation, operands, and option parsing

The syntax is:

```text
executable [options] [files]
```

Recognized options are `--suggest`, `--syntax`, `--syntax-suggest`, `--transform`, `--check`, `--replace`, `-h`, `--help`, `--version`, and `--`.

Each non-option operand is an input path. An operand that is exactly the empty string means standard input; standard input is not read merely because no paths were supplied. Thus an invocation with no arguments, even if data is available on stdin, exits successfully and emits nothing. If the empty-string operand occurs more than once, the stream is consumed only once, so its content is not duplicated. A literal `-` is not a stdin marker and, before `--`, is an invalid option.

`--` ends option recognition; every subsequent argument, including `-`, `--help`, or another option-looking string, is a literal filename. A bare word such as `transform` is also a filename, not a subcommand. Paths may be absolute or relative and may contain spaces or other ordinary filename characters.

The six mode options are mutually overriding rather than conflicting, but argument processing is forward-only. Each path operand is processed immediately in the mode active when that operand is encountered; a later mode option does not retroactively affect an earlier operand. Thus `--transform FILE` transforms `FILE`, whereas `FILE --transform` renders `FILE` in the default syntax-suggest mode and merely selects transform mode for any later operands. With no preceding mode option, an operand uses `--syntax-suggest`.

`--help` and `-h` emit help when encountered, and `--version` emits the version when encountered. They do not consume or suppress later file operands: for example, `--version FILE` writes `4.3.1\n` and then the default-mode rendering of `FILE`; `--help FILE` similarly writes the help followed by the rendering. An invalid option encountered before help is an error and does not print help.

An unrecognized option, including misspellings, unsupported short flags, `--name=value`, `-long`, and `---long`, writes exactly:

```text
OPTION: No such option.
```

to stderr, emits nothing to stdout, stops normal argument processing, and exits 3.

## Spec 3: Version and exact help

`--version` writes exactly `4.3.1` followed by a newline to stdout and writes nothing to stderr.

Both `-h` and `--help` write the following exact plain-text block to stdout. Indented lines begin with one tab, wrapping and capitalization are significant, there are no ANSI escapes, and the final URL is followed by two newline characters.

```text
Shellharden: The corrective bash syntax highlighter.

Usage:
	shellharden [options] [files]
	cat files | shellharden [options] ''

Shellharden is a syntax highlighter and a tool to semi-automate the rewriting
of scripts to ShellCheck conformance, mainly focused on quoting.

The default mode of operation is like `cat`, but with syntax highlighting in
foreground colors and suggestive changes in background colors.

Options:
	--suggest         Output a colored diff suggesting changes.
	--syntax          Output syntax highlighting with ANSI colors.
	--syntax-suggest  Diff with syntax highlighting (default mode).
	--transform       Output suggested changes.
	--check           No output; exit with 2 if changes are suggested.
	--replace         Replace file contents with suggested changes.
	--                Don't treat further arguments as options.
	-h|--help         Show help text.
	--version         Show version.

The changes suggested by Shellharden inhibits word splitting and indirect
pathname expansion. This will make your script ShellCheck compliant in terms of
quoting. Whether your script will work afterwards is a different question:
If your script was using those features on purpose, it obviously won't anymore!

Every script is possible to write without using word splitting or indirect
pathname expansion, but it may involve doing things differently.
See the accompanying file how_to_do_things_safely_in_bash.md or online:
https://github.com/anordal/shellharden/blob/master/how_to_do_things_safely_in_bash.md

```

Help or version alone exits 0 and uses no stderr.

## Spec 4: Input preservation and parser coverage

Process inputs in operand order. Non-replacement output from multiple files is concatenated directly, with no filename headings or inserted separators. Preserve all source bytes except characters deliberately changed by a transformation or ANSI sequences deliberately added by a display mode. In particular preserve shebangs, comments, inline comments, indentation, tabs, blank lines, final-newline presence, CR/LF line endings, Unicode text, escaped characters, and control characters that are not shell syntax. Empty input produces empty output.

The parser must track shell lexical and nesting context rather than using a context-free text replacement. It must recognize at least:

- ordinary commands, assignments, redirections, pipes, `&&`, `||`, `&`, semicolons, comments, line continuations, and grouped commands;
- single, double, and ANSI-C `$'...'` strings and their escapes;
- `$()` and backtick command substitutions, arithmetic `$((...))`, process substitutions `<(...)` and `>(...)`, and nested combinations of them;
- scalar and array parameter expansions, including nested/default expansions;
- `if`/`elif`/`else`/`fi`, `for`, arithmetic `for`, `select`, `while`, `until`, `case`/`esac`, functions, subshells, `{ ...; }`, `[`/`test`, and `[[ ... ]]`;
- here-documents with quoted or unquoted delimiters and here-strings `<<<`.

Valid glob expressions (`*.txt`), brace expansions (`{1..5}`), redirection syntax, and the literal body of the first pending here-document are not themselves quoted or rewritten. Variables and command substitutions in that first body are left unchanged. Multiple here-document redirectors on one command have a deterministic limitation: only the first body is treated as a here-document body; later bodies are transformed as ordinary command source. In particular:

```text
cat <<'ONE' <<-TWO       -> cat <<'ONE' <<-TWO
$x                          $x
ONE                         ONE
\t$y                        \t"$y"
\tTWO                       \tTWO
```

Variables inside commands within process substitutions are processed normally.

## Spec 5: Output modes

All successful rendering modes preserve the source's newline structure.

- `--transform` writes the fully rewritten source without ANSI escapes.
- `--syntax` writes the original source with syntax foreground/style escapes only; it does not apply or preview rewrites.
- `--suggest` writes the original source plus an inline colored character diff. Unchanged text is plain, deleted original characters are retained with red background, and inserted replacement characters appear with green background.
- `--syntax-suggest` overlays that inline diff on syntax-highlighted source. It is also the default mode.
- `--check` writes nothing. It exits 2 immediately when the first input would change, and 0 if all inputs are already canonical.
- `--replace` applies the bytes produced by the named-file `--transform` path to each named file and normally writes nothing to stdout. As detailed in Spec 9, the named-file and stdin transformation paths have different buffering behavior for an unusually long unbraced variable name.

For an empty-string stdin operand, `--replace` cannot replace a file and instead writes the transformed stdin to stdout.

For the diff, additions use `ESC[0;42m`, removals use `ESC[0;41m`, and a return to unstyled text uses `ESC[m`. For example, where `<ESC>` denotes byte `0x1b`:

```text
input:    echo $foo\n
suggest:  echo <ESC>[0;42m"<ESC>[m$foo<ESC>[0;42m"<ESC>[m\n
transform: echo "$foo"\n
```

Removing unnecessary braces is shown as green inserted quotes and red original braces.

ANSI serialization is byte-minimal at zero-width style boundaries. If one styled span is immediately followed by another styled span, emit the second span's SGR prefix directly; do not insert `ESC[m` between the two prefixes. Emit `ESC[m` when actual following source text is unstyled or when leaving the final styled span. Consequently, default syntax-suggest output for `echo $foo\n` is exactly:

```text
ESC[0;38;2;192;0;128mechoESC[m ESC[0;42m"ESC[0;38;2;63;127;207m$fooESC[0;42m"ESC[m
```

Similarly, suggest output for `echo ${var}\n` is exactly:

```text
echo ESC[0;42m"ESC[m$ESC[0;41m{ESC[mvarESC[0;41m}ESC[0;42m"ESC[m
```

In particular there is no reset between the red removed `}` and the adjacent green inserted `"`. The same direct-transition rule applies after help or version output when a later operand is rendered.

## Spec 6: Syntax-highlighting palette

Use exact SGR sequences beginning with ESC and ending in `m`; reset with `ESC[m`. Contiguous lexical spans receive these styles:

| Shell element | Exact SGR prefix |
| --- | --- |
| reserved/control keywords | `ESC[0;1m` |
| command names | `ESC[0;38;2;192;0;128m` |
| variable/parameter expansions | `ESC[0;38;2;63;127;207m` |
| assignment left-hand names and loop variables | `ESC[0;38;2;0;127;255m` |
| double-quoted strings | `ESC[0;38;2;255;0;0m` |
| single-quoted strings | `ESC[0;38;2;255;204;85m` |
| ANSI-C `$'...'` strings | `ESC[0;38;2;255;128;0m` |
| escape sequences inside quoted strings | `ESC[0;1;38;2;255;0;128m` |
| comments and shebangs | `ESC[0;1;3;38;2;120;144;96m` |
| heredoc introducer, body, and terminator | `ESC[0;38;2;128;32;0m` |
| arithmetic and `[[...]]` structural spans when applicable | `ESC[0;38;2;192;0;192m` |

Embedded expansions temporarily switch directly from the surrounding string style to the variable or nested-command style, then directly back to the enclosing style, with no intervening reset. Escapes inside a double-quoted string use the same direct switches. In `--syntax-suggest`, the foreground style remains active across inserted/deleted characters as appropriate, while the diff background is added; the byte-minimal transition rule in Spec 5 applies.

Some grammar-owned spaces are included in colored spans. In `for i in`, `for` and its following space use the keyword style, `i` uses the loop-variable style, and the space after `i` switches directly back to keyword style; `in` is then unstyled. In `case $1 in`, `case ` uses keyword style, `$1` uses variable style, and ` in` uses keyword style. The `[` command's command-name span includes its following space. These exact examples show the boundaries:

```text
for i in 1 2 3; do
-> ESC[0;1mfor ESC[0;38;2;0;127;255miESC[0;1m ESC[min 1 2 3; ESC[0;1mdoESC[m

case $1 in
-> ESC[0;1mcase ESC[0;38;2;63;127;207m$1ESC[0;1m inESC[m

if [ -f "$file" ]; then
-> ESC[0;1mifESC[m ESC[0;38;2;192;0;128m[ ESC[m-f ESC[0;38;2;255;0;0m"ESC[0;38;2;63;127;207m$fileESC[0;38;2;255;0;0m"ESC[m ]; ESC[0;1mthenESC[m
```

The brown heredoc style is one uninterrupted span from the `<<` introducer through all body line endings and the last character of the terminator. It is reset only after the terminator, before its newline. For example:

```text
cat << 'HEREDOC'\nbody\nHEREDOC\n
-> ESC[0;38;2;192;0;128mcatESC[m ESC[0;38;2;128;32;0m<< 'HEREDOC'\nbody\nHEREDOCESC[m\n
```

For example, `--syntax` on `echo $foo\n` is exactly:

```text
ESC[0;38;2;192;0;128mechoESC[m ESC[0;38;2;63;127;207m$fooESC[m
```

where each displayed `ESC` represents byte `0x1b`, and the line ends in `\n`.

## Spec 7: Core quoting rewrite

In ordinary command-word and argument contexts, protect every unquoted expansion whose result can undergo word splitting or indirect pathname expansion. Add double quotes locally without changing argument boundaries. Adjacent unsafe expansions belonging to one shell word should share quotes when possible; literal path punctuation may be absorbed into or left adjacent to the quoted part according to these canonical examples:

```text
echo $a $b                    -> echo "$a" "$b"
$cmd arg                     -> "$cmd" arg
echo $a$b                    -> echo "$a$b"
echo $dir/$subdir/$file.txt  -> echo "$dir/$subdir/$file".txt
echo path/$file/more         -> echo path/"$file"/more
echo foo$bar                 -> echo foo"$bar"
echo ${foo}                  -> echo "$foo"
echo ${foo}bar               -> echo "${foo}"bar
echo a${b}c                  -> echo a"${b}"c
echo $a"string"              -> echo "${a}string"
echo "$a"$b                  -> echo "$a""$b"
echo $a"literal"$b           -> echo "${a}literal""$b"
```

Already safe quoted expansions remain quoted. A simple braced expansion that is the sole contents of its double-quoted segment is canonicalized from `"${name}"` to `"$name"` when braces are not needed. Braces are preserved when the expansion shares that quoted segment with literal text: `echo "text ${foo} more"` is unchanged. Braces also remain where an identifier-tail character (`A-Z`, `a-z`, `0-9`, or `_`) would otherwise join the variable name, remain for all non-simple parameter operations, and remain on braced positional parameters such as `${0}`. Text in single quotes, escaped dollar signs, empty quoted strings, quoted glob strings, and deliberate unquoted literal globs are unchanged.

When an unsafe expansion is followed later in the same shell word by an existing double-quoted segment, the inserted opening quote coalesces the intervening literal text and that quoted segment. For example:

```text
echo $a/blædi/" " -> echo "$a/blædi/ "
```

At physical EOF, an unquoted simple expansion that needs newly inserted quotes is instead braced, because the parser flushes the still-open expansion scope at EOF:

```text
input bytes:  echo $value
output bytes: echo "${value}"
```

There is no final newline in either byte string in that example. With a following newline or other delimiter, the usual result is `echo "$value"`.

Redirection and here-string operands are ordinary vulnerable word contexts until a here-document redirector is encountered on that command line:

```text
cat < $input > $output   -> cat < "$input" > "$output"
cat <<< $value           -> cat <<< "$value"
```

After a `<<` or `<<-` redirector has been encountered, the remainder of that same command line is passed through without quoting its expansions. Thus:

```text
cat > $output <<EOF  -> cat > "$output" <<EOF
cat <<EOF > $output  -> cat <<EOF > $output
cat <<EOF $arg       -> cat <<EOF $arg
```

The transformation is idempotent: transforming canonical output again makes no changes.

## Spec 8: Contexts where quotes are not added

Do not add quotes merely for expansions in these contexts:

- scalar assignment right-hand sides, including `=`, `+=`, indexed assignments, multiple leading assignments, and assignments handled by `local`, `readonly`, or `export`;
- arithmetic expansion and arithmetic-command contents, including array-index arithmetic;
- the expression and patterns of `case`;
- expressions inside `[[ ... ]]`, so pattern matching remains intact.

Array literal elements are different from scalar assignment RHS values and are protected. Thus:

```text
value=$other                 -> value=$other
local value=$other           -> local value=$other
echo $(( $a + b ))           -> unchanged
[[ $a == *.txt ]]            -> unchanged
case $value in $pattern)     -> expression and pattern unchanged
array=($list)                -> array=("$list")
array=($(list))              -> array=("$(list)")
```

`declare` depends on its option form. A bare `declare value=$other` remains unchanged, but the export form treats the assignment value as a vulnerable word:

```text
declare -x value=$other      -> declare -x value="$other"
```

Commands and substitutions nested inside an exempt outer context ordinarily establish their own contexts: `x=$(cat $file)` becomes `x=$(cat "$file")` even though the outer substitution need not be quoted. A command substitution inside a `${...}` parameter expansion is the exception: its command contents are passed through rather than recursively transformed. This applies whether the parameter expansion remains unquoted as an assignment RHS or is quoted as a vulnerable argument:

```text
x=${outer:-$(cat $file)}
-> x=${outer:-$(cat $file)}

echo ${outer:-${inner:-$(cat $file)}}
-> echo "${outer:-${inner:-$(cat $file)}}"
```

## Spec 9: Parameter and array forms

Recognize identifiers containing letters, digits after the first character, and underscores, including names beginning with or consisting only of underscores. In vulnerable contexts:

- quote single-digit positional parameters `$0` through `$9`;
- quote `$@` as `"$@"` and rewrite `$*` as `"$@"`;
- leave the invariably numeric `$?`, `$#`, `$$`, and `$!` unquoted;
- quote `$-`;
- quote scalar parameter operations `${v:-default}`, `${v:=default}`, `${v:+alternative}`, `${v:?error}`, `${v#pattern}`, `${v##pattern}`, `${v%pattern}`, `${v%%pattern}`, `${v/pat/repl}`, `${v:offset:length}`, `${v^^}`, and `${v,,}` as a whole, preserving nested expansions;
- leave numeric length `${#v}`, indirect/name expansions `${!v}`, `${!prefix@}`, `${!prefix*}`, and array-key expansion `${!array[@]}` unquoted;
- quote array elements, slices, and all-elements expansions: `${a[index]}`, `${a[@]}`, `${a[@]:start:length}`;
- normalize unquoted `${a[*]}` to `"${a[@]}"`.

Already-braced positional parameters retain their braces: `${0}` through `${9}` become `"${0}"` through `"${9}"` in vulnerable contexts, and an already quoted `"${0}"` is unchanged.

Identifier recognition has an observable streaming boundary for unusually long unbraced names. A variable token shorter than 128 bytes is handled normally. Once the token consisting of `$` plus name bytes reaches 128 bytes, output begins `"${`, the first closing `}` is emitted after 127 name bytes, and another `}` is emitted whenever another 128 name bytes are flushed; the final fragment is also followed by `}` before the closing quote. For example, for `echo $` followed by exactly 1000 ASCII `x` bytes and `\n`, the transformed output is:

```text
echo "${ + x*127 + } + (x*128 + })*6 + x*105 + }" + \n
```

Here the `+` notation describes byte concatenation and `x*N` means exactly N literal `x` bytes; the plus signs and counts are not output.

The 8192-byte input-read boundary affects the empty-string stdin operand, but not a named-file operand in the same way. For `echo $` followed by exactly 10,000 ASCII `x` bytes and `\n`:

- `--transform ''` produces fragments of 127 name bytes, then sixty-two 128-byte fragments, then 123 bytes at the 8192-byte read boundary, then fourteen 128-byte fragments, then 22 bytes;
- both `--transform FILE` and `--replace FILE` produce fragments of 127 name bytes, then seventy-seven 128-byte fragments, then 17 bytes.

Every result is 10,089 bytes, but the stdin result first differs from either named-file result at zero-based byte offset 8257, where stdin has the first early `}`. Thus replacement agrees with transformation of the same named-file operand; it does not agree byte-for-byte with transforming the same source through stdin at this boundary.

Array literals and `+=` array literals apply these rules to each element. In the list of a `for` loop, a sole scalar-looking list expansion is treated as the intended array and rewritten to the all-elements form:

```text
for x in $items; do echo $x; done
-> for x in "${items[@]}"; do echo "$x"; done

for x in $a $b; do ...
-> for x in "$a" "$b"; do ...
```

`$*` in such a list becomes `"$@"`. Literal lists, globs, brace expansions, and already correct `"${array[@]}"` are preserved.

## Spec 10: Command substitution and `pwd`

In vulnerable word contexts, quote the entire result of `$()` and recursively transform commands within it:

```text
echo $(date)                 -> echo "$(date)"
echo $(cat $file)            -> echo "$(cat "$file")"
echo $(outer $(inner $x))    -> echo "$(outer "$(inner "$x")")"
```

This recursive command-content transformation does not enter a command substitution embedded within a `${...}` parameter expansion; Spec 8 gives the exact pass-through examples for that context.

An already quoted substitution is not given an extra quote layer, but its contents are still transformed. Preserve multiline and empty substitutions. Process substitution delimiters `<(...)` and `>(...)` are not converted to command substitutions.

Convert an unquoted backtick substitution to `$()` when its result needs protection, including multi-command cases, and quote its result. A simple backtick substitution used as the complete assignment RHS is preserved in backtick form; for example, ``var=`uname -a` `` is unchanged. The `pwd` optimization is the exception: when the complete RHS is exactly `` `pwd` ``, ``dir=`pwd` `` becomes `dir=$PWD`, while an assignment word such as ``dir=`pwd`suffix`` remains unchanged.

Escaped backticks inside a converted outer backtick substitution are retained as escaped literal backtick bytes rather than converted into nested `$()` syntax, while expansions between them are still transformed. The exact result is:

```text
echo `outer \`inner $x\`` -> echo "$(outer \`inner "$x"\`)"
```

Optimize an exact `pwd` substitution—both `` `pwd` `` and `$(pwd)`, but not whitespace variants such as `$( pwd)`—to `$PWD`. Apply normal context, concatenation, and brace rules:

```text
dir=$(pwd)       -> dir=$PWD
echo $(pwd)      -> echo "$PWD"
echo $(pwd)/bin  -> echo "$PWD"/bin
echo $(pwd)extra -> echo "${PWD}"extra
```

## Spec 11: Tests, conditions, and control structures

Apply ordinary quoting within the `[` command and the `test` command, including string/numeric comparisons, file predicates, negation, parentheses, and compound conditions. Leave `[[ ... ]]` expansions unquoted. Preserve the syntactic structure and formatting of `if`/`elif`, loops, functions, case arms, pipes, command groups, and background commands while applying the relevant local context rules.

Normalize a variable or command-substitution operand of unary `-z` or `-n` into an explicit empty-string comparison, even if already quoted:

```text
[ -z $v ]       -> [ "$v" = "" ]
test -n "$v"    -> test "$v" != ""
```

Do not normalize `-z`/`-n` applied only to a literal.

Remove the obsolete matching `x` prefixes from equality tests when both compared words use that protection idiom, for `=`, `==`, and `!=`, and quote the expansion safely:

```text
[ x$foo = xbar ]       -> [ "$foo" = bar ]
[ x$foo$bar != xno ]   -> [ "$foo$bar" != no ]
```

If only one side has the prefix, retain it, as in `[ x$a = y ] -> [ x"$a" = y ]`.

Within `case`, do not quote its selector or patterns, including variable and glob patterns; do quote vulnerable expansions in arm bodies. Nested cases and multiple `|` patterns must work. If `esac` is encountered while an arm lacks its `;;`, insert `;; ` immediately before that `esac`.

## Spec 12: Malformed input and unsupported positional syntax

Detect unexpected EOF while inside an unclosed single/double quote, command substitution, backtick substitution, arithmetic expansion, variable brace, `[[...]]`, heredoc, or nested parenthesized scope, including a lone continuation backslash at EOF. In transform and rendering modes, emit the source/rendered prefix and then append one newline byte to stdout, regardless of whether the source prefix already ended in a newline. Write the following diagnostic directly to stderr, with no leading separator newline:

```text
SOURCE: Unexpected end of file
The file's end was reached without closing all sytactic scopes.
Either, the parser got lost, or the file is truncated or malformed.
```

`SOURCE` is the exact path operand; it is empty for stdin, yielding a line beginning `: Unexpected...`. The spelling `sytactic` is intentionally part of the interface. In normal rendering/transform modes this is exit 1. For example, stdin bytes `echo 'open` produce stdout `echo 'open\n`, while a named file containing `#!/bin/bash\necho "unclosed string\n` produces that complete source plus one additional `\n` on stdout. `--replace` leaves the file byte-for-byte unchanged, emits no stdout, and writes the diagnostic without a leading newline. `--check` reports a parse issue with status 2 and emits nothing at all on either stdout or stderr.

An unbraced multi-digit positional-looking expansion such as `$10`, `$100`, or `$123` is a fatal syntactic pitfall because Bash parses only its first digit as the parameter. Braced `${10}` is valid and is quoted in vulnerable contexts. For input `echo $10\n` from stdin in transform mode, stdout is exactly `echo \n`, status is 1, and stderr is exactly:

```text
: Unsupported syntax: Syntactic pitfall
echo $10
     ^^^
This does not mean what it looks like. You may be forgiven to think that the full string of numerals is the variable name. Only the fist is.

Try this and be shocked: f() { echo "$9" "$10"; }; f a b c d e f g h i j

Here is where braces should be used to disambiguate, e.g. "${10}" vs "${1}0".

Syntactic pitfalls are deemed too dangerous to fix automatically
(the purpose of Shellharden is to fix vulnerable code – code that mostly does what it looks like, as opposed to code that never does what it looks like):
* Fixing what it does would be 100% subtle and might slip through code review unnoticed.
* Fixing its look would make a likely bug look intentional.
```

For a file, prefix the first line with its operand path instead of the empty stdin source. The typo `fist` and the en dash are intentional.

## Spec 13: File errors and batch behavior

An unreadable/nonexistent operand is an input error in every mode, including `--check`. For a missing path, write exactly:

```text
PATH: No such file or directory (os error 2)
```

to stderr and exit 1 after batch processing. Passing a directory similarly reports `PATH: Is a directory (os error 21)`. A directory operand additionally contributes exactly one newline to stdout in transform, syntax, suggest, and syntax-suggest modes; it contributes no stdout in check or replace mode. Do not create a missing file.

Outside `--check`, continue with later operands after a file I/O or per-file parse error. Successfully processed files still produce output or are replaced, and every failing file in a replacement batch is diagnosed; the aggregate status is 1 if any such error occurred. In `--check`, stop at the first change, parse issue, or I/O issue without stdout. A change or parse issue returns 2 silently; an I/O issue writes its normal diagnostic and returns 1.

## Spec 14: In-place replacement

For each real file operand, `--replace` computes precisely the result of `--transform` on that same named-file operand and writes it back only after the entire file parses successfully. This is not a promise that transforming identical bytes through the empty-string stdin operand has identical long-token buffering; Spec 9 specifies that boundary case. Replacement is silent on successful named-file operation. Requirements for replacement are:

- preserve the file's permission/mode bits, including executability;
- follow a symbolic link and update its target without replacing the symlink itself;
- preserve the source's shebang, comments, indentation, tabs, newline convention, and whether it has a final newline;
- support large files and very long lines without truncation;
- make a changed file's modification time advance;
- on a parse failure, do not truncate or partially rewrite the original;
- process all named files in the batch, including files after an error.

Applying replacement repeatedly is safe and yields the same canonical content after the first successful change.

Final-newline absence is preserved, but it also triggers the physical-EOF bracing rule from Spec 7. Replacing a file whose final bytes are `echo $value` writes `echo "${value}"`, with no final newline; replacement remains silent.

## Spec 15: Exit status summary

Status codes are part of the interface:

| Status | Meaning |
| --- | --- |
| `0` | successful help/version/render/transform/replace, or `--check` found no rewrite |
| `1` | file I/O error in any mode, or parsing/replacement error outside check mode |
| `2` | `--check` found a rewrite or parse issue |
| `3` | invalid command-line option |

Except for the documented diagnostics and rendered partial input on parser failure, successful operations keep stderr empty. Check mode always keeps stdout empty. It is silent for changed/unchanged inputs and parse failures, but file I/O failures still write their diagnostic.
