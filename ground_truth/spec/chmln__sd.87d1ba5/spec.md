## Spec 1

The required artifact is one directly executable file named exactly `executable`. It implements a command-line program identified as `sd`, an intuitive find-and-replace CLI. Its command shape is:

```text
executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...
```

There are no subcommands. The first non-option argument is always the find expression, the second is always the replacement, and every remaining positional argument is a file path. Words commonly used as subcommands, including `help`, `version`, `add`, `remove`, `list`, `show`, `get`, `set`, `update`, `delete`, `init`, `clone`, `push`, and `pull`, have no special meaning when supplied as positionals. For example, with standard input `I need help`, `executable help assist` writes `I need assist`.

With no file arguments, the program reads all bytes from standard input, transforms them, and writes the result to standard output. With one or more file arguments, it normally modifies those files in place and produces no standard output. Successful transformations return status 0 and normally write nothing to standard error.

## Spec 2

The accepted options are:

```text
-p, --preview
-F, --fixed-strings
-n, --max-replacements <LIMIT>
-f, --flags <FLAGS>
-h, --help
-V, --version
```

The legacy short option `-s` is also accepted as an alias of `-F`, although it need not be shown in help.

Options may occur before, between, or after the two required positional arguments. Boolean short options may be clustered, so `-pF` and `-Fp` both mean preview plus fixed-string mode. A value-taking short option may have an attached value, so `-fmc` means `-f mc`. The limit accepts all of `-n 1`, `-n=1`, `--max-replacements 1`, and `--max-replacements=1`; flags similarly accept `--flags mc` and `--flags=mc`. An explicitly empty flags value is valid.

The token `--` ends option recognition. All later tokens, even ones beginning with `-`, are positional. Thus all of the following are valid:

```text
executable foo -- -w              # FIND=foo, REPLACE_WITH=-w
executable -- --foo -w            # FIND=--foo, REPLACE_WITH=-w
executable -- -pattern -replace   # FIND=-pattern, REPLACE_WITH=-replace
```

Without `--`, every dash-prefixed token is interpreted as an option or option value rather than as FIND, REPLACE_WITH, or a file. Global help options are recognized even after ordinary positionals. For example, `executable a b --help` shows the main help and succeeds. Help also takes precedence in `executable --help --version` and `executable --help unexpected-arg`. Conversely, in `executable -- --help`, `--help` is FIND, so required-argument validation fails and ordinary help is not printed to stdout.

Each single-occurrence option is rejected if passed more than once. In particular, repeated `-p` and repeated `-f` result in a parse error containing `cannot be used multiple times` or `multiple times`. Repeating letters inside one flags value, such as `-f iii`, is valid and idempotent.

## Spec 3

`--version` and `-V` return status 0, write exactly the following version line to stdout, and write nothing to stderr:

```text
sd 1.0.0
```

The terminating newline is part of the output. Version is an option, not a subcommand.

## Spec 4

`--help` and `-h` return status 0, write help to stdout, and write nothing to stderr. Both outputs contain the product line `sd v1.0.0`, the description `An intuitive find & replace CLI`, and this exact synopsis:

```text
Usage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...
```

Both contain `Arguments:` and `Options:` sections and document FIND, REPLACE_WITH, and optional files. They do not contain a `Commands:` or `Subcommands:` section. Long help documents these exact option labels:

```text
-p, --preview
-F, --fixed-strings
-n, --max-replacements
-f, --flags
-h, --help
-V, --version
```

The preview description includes `human reviewable format`. Fixed-string help includes `Treat FIND and REPLACE_WITH args as literal strings`. The maximum-replacements description includes `[default: 0]`. The flags description includes all of:

```text
c - case-sensitive
e - disable multi-line matching
i - case-insensitive
m - multi-line matching
s - make `.` match newlines
w - match full words only
```

Long help also contains these exact phrases: the FIND argument is described with ``The regexp or string (if using `-F`) to search for``, and the flags option is described with ``Regex flags. May be combined (like `-f mc`).`` Thus the literal terms `regexp` and `Regex flags` are part of the required long-help output.

The short-help output is genuinely more compact (fewer bytes) than long help. Long help describes `-h, --help` with `Print help (see a summary with '-h')`; short help uses `Print help (see more with '--help')`. A suitable layout is the usual compact/expanded command help shown by these requirements; spacing outside the required phrases is not semantically significant.

## Spec 5

Unless `-F`/`--fixed-strings`/legacy `-s` is selected, FIND is a Unicode-aware regular expression. Replacement is global: all non-overlapping, leftmost matches are replaced, including multiple matches on one line and matches on every line. No match is a successful no-op that reproduces the input bytes exactly. An empty replacement deletes matches. Matching an entire input may yield an empty output.

The regular-expression language must include:

- literals, `.`, alternation `|`, grouping `(...)`, and Python-style named groups `(?P<name>...)`;
- character classes and ranges such as `[aeiou]`, `[^aeiou]`, `[a-z]`, and `[a-zA-Z0-9]`;
- `*`, `+`, `?`, exact/ranged repetition such as `{3}` and `{2,3}`, and lazy quantifiers such as `*?`;
- anchors `^` and `$`, word boundaries `\b`, and the shorthands `\d`, `\w`, `\s`, `\D`, `\W`, and `\S`;
- escaped literal metacharacters, including `\$`.

Matching is greedy unless a lazy quantifier is used. For example, replacing `<.*>` in `<a><b>` replaces the entire string once, whereas `<.*?>` replaces the two tags independently. Matches never overlap: replacing `aa` with `X` in `aaaa` gives `XX`. Unicode characters and Unicode case folding are supported. Look-ahead and look-behind are deliberately unsupported, as are backreferences inside FIND such as `(\w)\1`; these are regex errors rather than matches.

Representative mandatory transformations include:

```text
FIND=\d+, REPLACE=N, input="1 22 333"       -> "N N N"
FIND=[aeiou], REPLACE=X, input="hello"       -> "hXllX"
FIND=cat|dog, REPLACE=animal, input="cat dog" -> "animal animal"
FIND=a.*b, REPLACE=X, input="axbyyb"          -> "X"
```

## Spec 6

Default regex matching is case-sensitive, `.` does not match newline, and multiline anchor behavior is enabled. Consequently, lowercase FIND does not imply smart-case matching: replacing `hello` in `Hello HELLO hello` changes only the last word. By default, `^` and `$` match at every line boundary as well as at the input boundaries. For example:

```text
FIND=^line, input="line1\nline2\nline3" -> all three `line` prefixes match
FIND=end$, input="1 end\n2 end\n3 end"   -> all three `end` suffixes match
```

Without the `s` flag, dot never consumes LF; `a.*b` leaves `a\nb` unchanged. CR, LF, and CRLF bytes are otherwise preserved. Multiline `^line` correctly recognizes starts after the LF in CRLF data without normalizing the line endings.

## Spec 7

`-f`/`--flags` takes one string whose characters are processed from left to right. Unknown characters are silently ignored. The recognized characters have these meanings:

- `c`: turn case-insensitive matching off.
- `i`: turn case-insensitive matching on, using Unicode-aware folding.
- `m`: turn multiline `^`/`$` behavior on.
- `e`: turn multiline behavior off, so anchors apply only at whole-input boundaries.
- `s`: make `.` match newline.
- `w`: prepend a Unicode regex word boundary to FIND and append one after it, without grouping FIND first.

In ordinary regex mode, when no `-f` option is supplied, the implicit configuration is `m`. A nonempty `-f` value configures a fresh regex builder whose engine defaults have multiline and dot-all off and case-insensitivity off. Thus `-f s` enables dot-all but, because no `m` was supplied, has whole-input anchor behavior; `-f ms` enables both multiline anchors and dot-all. An explicitly empty value, whether supplied as `--flags=` or as `-f ''`, is accepted but leaves the implicit `m` configuration in effect. Consequently, `--flags= '^line' X` on `line1\nline2` writes `X1\nX2`.

Later `c` or `i` overrides an earlier one: `ic` is case-sensitive and `ci` is case-insensitive. There is one required order-sensitive compatibility behavior for `w`: applying `w` rebuilds the expression with the ungrouped boundary wrapper described above and resets regex-builder switches previously applied in that same flags string. Later characters then apply normally. Therefore:

```text
-f iw, FIND=test, input="Test TEST test" -> "Test TEST X"
-f wi, FIND=test, input="Test TEST test" -> "X X X"
```

Here the replacement is `X`. This `iw`/`wi` asymmetry is intentional observable behavior. Word characters include Unicode letters, digits, and underscore. Thus, for a FIND with no top-level alternation, whole-word `test` does not match inside `testing`, `retest`, or `test_case`, but does match at input edges, adjacent to punctuation, and before a hyphen. Whole-word `123` does not match within `test123` or `123test`.

Because `w` adds the boundaries without grouping, regex alternation retains its normal lower precedence. For example, FIND `test|123` becomes effectively `\btest|123\b`: the first branch has only the leading boundary and the last branch has only the trailing boundary. With replacement `X`, input `test testing retest test_case test-test 123 test123 123test café caféx` therefore produces exactly `X Xing retest X_case X-X X XX 123test café caféx`.

The regex flags still affect matching when FIND has been escaped for fixed-string mode. In particular, `-F -f i TEST replaced` applied to `test TEST Test` produces `replaced replaced replaced`.

## Spec 8

In fixed-string mode (`-F`, `--fixed-strings`, or `-s`), FIND is matched as literal text rather than parsed as regex. Every regex metacharacter is ordinary, including `. * + ? ^ $ ( ) [ ] { } | \`. For example, fixed FIND `a.b` matches `a.b` but not `a0b`, fixed FIND `\n` matches the two bytes backslash-plus-`n`, and fixed FIND `((special[]))` matches exactly that text.

REPLACE_WITH is also fully literal in this mode. Capture syntax and escapes are not processed: `$1fine`, `$$`, `\n`, and `\t` are emitted literally as supplied. For example:

```text
executable -F foo '$1 test'    # foo -> literal "$1 test"
executable -F test '\n'        # each test -> two bytes backslash,n
```

Global replacement, replacement limits, case flags, stdin/file routing, and preview behavior still apply in fixed-string mode.

## Spec 9

Regex-mode REPLACE_WITH supports capture expansion. `$0` denotes the complete match. `$1`, `$2`, and so on denote numbered capture groups; multi-digit numbers such as `$10` and `$99` are parsed as the full number. `$name` denotes a named capture from `(?P<name>...)`. Braced forms `${1}`, `${12}`, and `${name}` are also supported and are the required way to place literal alphanumeric suffix text directly after a numbered reference.

Capture references may be reordered or repeated. Nested captures use their ordinary opening-parenthesis numbering. Examples:

```text
FIND=(\w+) (\w+), REPLACE=$2 $1, input="hello world" -> "world hello"
FIND=((a)(b)), REPLACE=$1-$2-$3, input="ab"            -> "ab-a-b"
FIND=(?P<y>\d{4})-(?P<m>\d{2}), REPLACE=$m/$y        -> captures by name
FIND=(test), REPLACE=${1}abc, input="test"             -> "testabc"
```

A syntactically valid reference to a group that does not exist expands to the empty string. This applies to `$1` when FIND has no capture, `$2` when it has only one, `$10`, `$99`, an unknown `$name`, and `${}`. Unclosed brace-looking text such as `${` and `${1` is literal. `$$` emits one literal dollar; `$$$$` emits two, and `$$1` emits literal `$1`. A lone dollar not forming a valid capture is literal.

## Spec 10

Before compiling or reading input, regex-mode replacement text must be validated for ambiguous numbered capture references. A dollar sign followed by one or more decimal digits and immediately by ASCII identifier letters is rejected, rather than interpreted as a numbered capture plus suffix. Examples include `$1bad`, `$1Call`, `$2invalid`, and `$12abc`. Use of the braced equivalent is accepted.

This is a processing error with status 1, empty stdout, and an exact diagnostic of this form:

```text
error: The numbered capture group `$1` in the replacement text is ambiguous.
hint: Use curly braces to disambiguate it `${1}abc`.
$1abc
 ^^^^
```

The group shown after `capture group` is the complete digit sequence. The suggested text braces only those digits and preserves the following suffix. The context line shows the complete replacement argument. The underline begins under the first digit (not under `$`) and has one caret per digit/suffix character. For example, `$12abc` is underlined with five carets and suggests `${12}abc`. Validation reports the first ambiguity when several exist.

Diagnostic context preserves Unicode characters. For display only, CR, LF, and TAB in the replacement argument are converted respectively to the visible control pictures `␍`, `␊`, and `␉`, so the context for `\r\n\t$1bad\r` contains `␍␊␉`. Caret positioning is by displayed Unicode characters, not UTF-8 byte count.

Fixed-string mode bypasses this validation, so literal `$1fine` is always allowed there.

## Spec 11

Before capture expansion, regex-mode replacement text is unescaped. The following two-character escapes produce one character:

```text
\n  LF (0x0a)
\r  CR (0x0d)
\t  TAB (0x09)
\\  backslash
\'  single quote
\"  double quote
```

`\xHH` converts exactly two hexadecimal digits to the Unicode scalar with that value; `\uHHHH` converts exactly four hexadecimal digits. This includes `\x00` producing a NUL byte, `\x41` and `\u0041` producing `A`, `\xFF` producing Unicode U+00FF encoded as UTF-8, and `\u2764` producing `❤`.

An unsupported escape such as `\q`, `\ `, `\b`, `\v`, or `\f` remains two literal characters. A malformed or incomplete fixed-width escape such as `\xG1`, `\xGG`, `\x4`, `\u00Z1`, `\uZZZZ`, or `\u004` also remains exactly literal. A trailing backslash is preserved. Multiple simple escapes work consecutively, so `a\nb\tc\rd` becomes `a`, LF, `b`, TAB, `c`, CR, `d`.

These transformations apply to the replacement argument only. Backslash sequences already present in input are not decoded; unmatched input is byte-preserved. Fixed-string replacement mode does no unescaping at all.

## Spec 12

The fixed-width hex/Unicode replacement escapes have a tested historical quirk that must be reproduced. After successfully decoding `\xHH` or `\uHHHH`, the decoder discards exactly one immediately following Unicode scalar if one exists. That discarded scalar acts as a separator and does not appear in output. No character is discarded after an invalid/incomplete escape or when the successful escape ends the replacement string.

Mandatory examples are:

```text
raw replacement          decoded replacement
\x41                    A
prefix\x41suffix        prefixAuffix       # the first s is discarded
hello\u263Aworld        hello☺orld         # w is discarded
bar\u00415678           barA678            # 5 is discarded
\xFFend                 ÿnd                # e is discarded
\x41X\x42              AB                  # X is discarded
\u0041X\u0042          AB                  # X is discarded
\x41-\x42              AB                  # - is discarded
\u0041-\u0042          AB                  # - is discarded
\x41\x42\x43           Ax42C               # first escape discards the next backslash
```

This compatibility behavior is required even though a conventional escape decoder would retain the following character.

## Spec 13

An empty regex FIND is valid. It matches at every Unicode scalar boundary, including the start and end. Replacing empty FIND with `X` in `abc` yields exactly `XaXbXcX`. For `test\n`, it yields `XtXeXsXtX\nX`. Zero-width-capable expressions must always advance correctly and never loop forever.

Use standard non-overlapping regex empty-match behavior. Required examples include:

```text
FIND=b*, input="abc\n", REPLACE=X -> "XaXcX\nX"
FIND=a*, input="baaabac\n", REPLACE=X -> "XbXbXcX\nX"
FIND=^, input="test", REPLACE=START: -> "START:test"
```

The executable must also handle empty stdin, very long individual lines (at least 200,000 bytes), tens of thousands of matches, and inputs/files larger than 1 MiB without truncation, hanging, or changing the stated semantics.

## Spec 14

`-n LIMIT`/`--max-replacements LIMIT` limits replacements to the first LIMIT non-overlapping matches in each input source. LIMIT is per source, not shared across files. For stdin there is one source. A value of 0 means unlimited, and 0 is the default. A limit larger than the match count simply replaces all matches and succeeds.

For example, `-n 2` replacing `test` with `X` in `test test test` produces `X X test`. Given two files both containing `a a`, `-n 1` changes each independently to `z a`. The same limits apply in preview mode and fixed-string mode.

LIMIT is parsed as an unsigned 64-bit decimal integer (range 0 through 18446744073709551615). Non-integers, floating-point values, embedded spaces, and values outside that range are parse errors with status 2. An equals-attached negative value such as `--max-replacements=-1` reports it as an invalid unsigned value; a separate `-1` is parsed as an unexpected option. Values such as `999999999` are valid.

## Spec 15

Input and output are byte preserving outside replaced ranges. Do not normalize line endings, add a final newline, remove trailing blank lines, collapse whitespace, or treat NUL as a terminator. LF, CRLF, and lone CR inputs retain their exact convention. Files without a final newline remain without one; files with multiple final or interior newlines retain them.

The program must replace valid textual matches inside otherwise binary data while preserving all surrounding bytes, including NUL and invalid UTF-8 bytes. For example, replacing ASCII `foo` in `00 01 02 66 6f 6f ff fe` changes only `66 6f 6f` to the replacement bytes. It must also correctly match and replace UTF-8 text including accented Latin text, Cyrillic, CJK characters, emoji, right-to-left text, combining marks, and zero-width space without corrupting other code points.

Regex matching itself is Unicode-aware for valid UTF-8. Literal byte sequences and unmatched binary regions pass through unchanged.

## Spec 16

When no files are supplied, stdin is the only source and transformed bytes are always written directly to stdout. `--preview` does not otherwise change stdin behavior: it adds no heading or separator and produces the same transformed stdout as a non-preview stdin run. Empty stdin produces empty stdout. A successful stdin transformation has status 0 and empty stderr.

The program reads stdin to end-of-file; it must not require a terminal and must work when stdin is an empty pipe or closed input stream.

## Spec 17

With one or more file paths and no preview option, each regular file is transformed in place. On complete success, status is 0, stdout and stderr are empty, and every source is processed independently. The number and order of files are unrestricted for tested practical purposes (at least five files and files over 1 MiB).

Writes are atomic replacements: create the replacement in the target's directory and swap it into place, rather than exposing a partially written destination. Preserve the original file permission mode. Files may become empty or change length. Files with no matches retain their bytes. Paths may be absolute or relative to the process working directory and may contain spaces, Unicode, dashes, underscores, and dots.

If a supplied path is a symbolic link, follow it and atomically update its resolved target. The directory entry for the link must remain a symlink. This applies whether the replacement shortens, lengthens, or empties the target.

## Spec 18

Before modifying any file, validate the complete file list. A nonexistent path is invalid. If any path is missing, return status 1, leave every valid file in that invocation untouched, write no stdout, and report:

```text
error: invalid path: PATH
```

where PATH is the first invalid path in argument order. For example, the literal path `/nonexistent/file.txt` gives exactly `error: invalid path: /nonexistent/file.txt` plus a terminating newline. A path after `--` is still a file path once FIND and REPLACE_WITH have already been supplied, so `executable foo bar -- --nonexistent-flag` returns status 1 with `error: invalid path: --nonexistent-flag`.

An empty string supplied in the file-argument position is rejected earlier by command-line parsing rather than reported as an invalid path. For example, invoking `executable foo bar VALID_FILE ''` returns status 2, writes no stdout, leaves `VALID_FILE` untouched, and writes exactly:

```text
error: a value is required for '[FILES]...' but none was supplied

For more information, try '--help'.
```

A directory is not treated recursively or as stdin. Attempting to process a directory returns status 1; on the tested Linux interface its diagnostic is exactly:

```text
error: No such device (os error 19)
```

An atomic output creation/replacement failure returns status 1, writes no stdout, and exposes no partial destination content. Its diagnostic depends on the point of failure. On the tested Linux interface, attempting to replace `Linux` with `CHANGED` in `/proc/version` leaves the file unchanged and writes exactly `error: Input/output error (os error 5)` plus a terminating newline; this diagnostic does not include the path or the aggregate prefix `Failed processing some inputs`. In particular, failure to atomically replace `/etc/hostname` must mention `/etc/hostname` and `failed`.

## Spec 19

With `-p`/`--preview`, never modify any input file. For exactly one file, stdout is exactly that file's transformed bytes with no heading. This is true even when there is no match or when the result is empty.

For two or more files, write every transformed result to stdout in the same order as the file arguments and precede each with this header line:

```text
----- FILE PATH -----
```

PATH is the exact path spelling supplied on the command line (absolute paths remain absolute; relative paths remain relative). Each file gets its own header, including a file with no matches. Content follows its header and retains its transformed byte/newline structure. Multi-file preview therefore resembles:

```text
----- FILE file1.txt -----
first transformed content
----- FILE file2.txt -----
second transformed content
```

Preview honors regex/fixed mode, flags, captures, escapes, and per-file replacement limits. A successful preview returns 0 and has empty stderr.

## Spec 20

Command-line parse and validation errors return status 2, write no transformed stdout, and print clap-style text to stderr. Missing required positionals contains all applicable names and these stable phrases:

```text
error: the following required arguments were not provided:
<FIND>
<REPLACE_WITH>
Usage: executable [OPTIONS] <FIND> <REPLACE_WITH> [FILES]...
For more information, try '--help'.
```

With FIND present, only `<REPLACE_WITH>` is listed. It is also acceptable for the compact usage line in this error to omit `[OPTIONS]`/`[FILES]...`, but it must contain `Usage: executable <FIND> <REPLACE_WITH>`.

An unknown option reports status 2 and includes `error: unexpected argument 'TOKEN' found`. When it could be positional and there is no close recognized-option spelling, also print `tip: to pass 'TOKEN' as a value, use '-- TOKEN'`. This applies to a replacement such as `-w`, an unknown long option, and a separate negative limit `-1`.

Close misspellings instead receive a similarity tip, which replaces the positional-value tip. In particular, `executable find --preveiw` prints `tip: a similar argument exists: '--preview'`, while `executable find --fixed-string` prints `tip: a similar argument exists: '--fixed-strings'`. Both invocations return status 2, write no stdout, and still include their respective `error: unexpected argument 'TOKEN' found` line.

A missing option value reports one of these exact stable lines, as applicable:

```text
error: a value is required for '--max-replacements <LIMIT>'
error: a value is required for '--flags <FLAGS>'
```

An invalid separated or attached limit contains:

```text
error: invalid value 'VALUE' for '--max-replacements <LIMIT>': REASON
```

For alphabetic/negative unsigned values, REASON includes `invalid digit found in string`; overflow includes `too large`. These parse diagnostics may additionally include usage/help lines.

## Spec 21

Regex compilation and replacement-validation failures return status 1, write no transformed stdout, and write diagnostics to stderr. Regex errors begin with `error: invalid regex regex parse error:`, show the offending expression and caret span on indented lines, and end with `error: REASON`. The following cases and exact logical messages are mandatory:

```text
FIND=(
error: invalid regex regex parse error:
    (
    ^
error: unclosed group

FIND=[z-a]
error: invalid regex regex parse error:
    [z-a]
     ^^^
error: invalid character class range, the start must be <= the end

FIND=\k
error: invalid regex regex parse error:
    \k
    ^^
error: unrecognized escape sequence

FIND=(?P<name>test)(?P<name>test)
error: invalid regex regex parse error:
    (?P<name>test)(?P<name>test)
        ^^^^          ^^^^
error: duplicate capture group name

FIND=(?)
error: invalid regex regex parse error:
    (?)
     ^
error: repetition operator missing expression

FIND=**
error: invalid regex regex parse error:
    **
    ^
error: repetition operator missing expression

FIND=(?P<>test)
error: invalid regex regex parse error:
    (?P<>test)
        ^
error: empty capture group name
```

Two further exact cases are:

```text
FIND=(?P<incomplete
error: invalid regex regex parse error:
    (?P<incomplete
                  ^
error: unclosed capture group name

FIND=(\w+) \1
error: invalid regex regex parse error:
    (\w+) \1
          ^^
error: backreferences are not supported
```

A look-around such as `test(?=ing)` or `(?<=test)ing` reports `look-around, including look-ahead and look-behind, is not supported` and includes the supplied pattern. Diagnostics use plain UTF-8 text when output is captured; ANSI styling is not required.

## Spec 22

The executable must not load per-user or per-project configuration. In particular, changing `HOME` and `XDG_CONFIG_HOME` to nonexistent directories must not cause config reads, warnings, changed matching, or failures. All behavior is determined solely by command-line arguments, input bytes, and the named files.

All normal invocations, including malformed regexes and large/pathological but supported inputs, must terminate promptly (within a five-second test timeout on ordinary test hardware). Patterns such as `(a+)+b` on a run of `a` characters must not exhibit catastrophic backtracking.
