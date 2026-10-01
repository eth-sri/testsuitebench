# Clarified executable specification

In this document, `ESC` means the single byte `0x1b`. The required artifact is a file named exactly `executable` in the repository root. Byte strings such as `ESC[31m` denote the literal ANSI bytes, not the printed characters `E`, `S`, `C`.

## Spec 1

`executable` is an executable command-line program named `diffr`. It is a filter: except for informational flags and argument errors, it reads all input from standard input and writes the transformed stream to standard output. It takes no file operands and has no subcommands. Positional words such as `help`, `version`, `show`, `config`, a pathname, and subcommand-like aliases are invalid arguments.

With valid options, normal completion has status 0. Empty standard input produces empty standard output and empty standard error, unless `--debug` is active. The implementation must not wait for terminal interaction when input is an empty pipe. A broken output pipe is a successful termination. Other I/O failures print `io error: <description>\n` to standard error and terminate nonzero.

For every successfully processed input, removing the SGR sequences added by this executable must recover the input bytes exactly, except that requested line-number margins are newly inserted and SGR sequences already present inside a recognized hunk are removed as described below. Text, Unicode, punctuation, tabs, blank lines, metadata, and whether the final line has a newline must otherwise be preserved.

## Spec 2

Recognized arguments are:

- `-h` and `--help`;
- `-V` and `--version`;
- repeatable `--colors COLOR_SPEC`;
- `--line-numbers`, optionally followed by one of `compact`, `aligned`, or `fixed`;
- hidden `--large-diff-threshold UNSIGNED_INTEGER`;
- hidden `--debug`.

Arguments are normally processed from left to right. Each of `--colors` and `--large-diff-threshold` always consumes the following argument and reports a missing-argument error if none exists. `--line-numbers` consumes the following argument as its style if one exists; consequently, it should normally be last or be given an explicit style before another option. If it has no following argument, its style is `compact`.

The literal long flag `--help` is exceptional: its presence anywhere in the argument vector takes precedence over every other argument, including invalid words and arguments following `--`. Thus `badarg --help`, `--help --unknown`, and `-- --help` all print long help and succeed. Short `-h` has only ordinary left-to-right precedence. Version also has ordinary precedence: an invalid argument before `--version` fails, while encountering a version flag prints the version and terminates immediately.

## Spec 3

`--help` must exit 0, write nothing to standard error, contain no ANSI sequences, and write exactly the following UTF-8 text to standard output, including indentation, blank lines, the spelling `ouput`, and the final newline:

```text
diffr 0.1.5
Nathan Moreau <nathan.moreau@m4x.org>

diffr adds word-level diff on top of unified diffs.
word-level diff information is displayed using text attributes.

USAGE:
    diffr reads from standard input and writes to standard output.

    Typical usage is for interactive use of diff:
    diff -u <file1> <file2> | diffr
    git show | diffr

OPTIONS:
        --colors <COLOR_SPEC>...
            Configure color settings for console ouput.

            There are four faces to customize:
            +----------------+--------------+----------------+
            |  line prefix   |      +       |       -        |
            +----------------+--------------+----------------+
            | common segment |    added     |    removed     |
            | unique segment | refine-added | refine-removed |
            +----------------+--------------+----------------+

            The customization allows
            - to change the foreground or background color;
            - to set or unset the attributes 'bold', 'intense', 'underline';
            - to clear all attributes.

            Customization is done passing a color_spec argument.
            This flag may be provided multiple times.

            The syntax is the following:

            color_spec = face-name + ':' + attributes
            attributes = attribute
                       | attribute + ':' + attributes
            attribute  = ('foreground' | 'background') + ':' + color
                       | (<empty> | 'no') + font-flag
                       | 'none'
            font-flag  = 'italic'
                       | 'bold'
                       | 'intense'
                       | 'underline'
            color      = 'none'
                       | [0-255]
                       | [0-255] + ',' + [0-255] + ',' + [0-255]
                       | ('black', 'blue', 'green', 'red',
                          'cyan', 'magenta', 'yellow', 'white')

            For example, the color_spec

                'refine-added:background:blue:bold'

            sets the color of unique added segments with
            a blue background, written with a bold font.

        --line-numbers <compact|aligned>
            Display line numbers. Style is optional.
            When style = 'compact', take as little width as possible.
            When style = 'aligned', align to tab stops (useful if tab is used for indentation). [default: compact]

    -h, --help
            Prints help information

    -V, --version
            Prints version information
```

## Spec 4

`-h` prints a shorter help form to standard output, writes nothing to standard error, and exits 0. Its exact text is:

```text
diffr 0.1.5
Nathan Moreau <nathan.moreau@m4x.org>

diffr adds word-level diff on top of unified diffs.
word-level diff information is displayed using text attributes.

USAGE:
    diffr reads from standard input and writes to standard output.

    Typical usage is for interactive use of diff:
    diff -u <file1> <file2> | diffr
    git show | diffr

OPTIONS:
        --colors <COLOR_SPEC>...    Configure color settings.
        --line-numbers              Display line numbers.
    -h, --help                      Prints help information
    -V, --version                   Prints version information
```

Both `-V` and `--version` exit 0, write no standard output, and write exactly `diffr 0.1.5\n` to standard error.

## Spec 5

Unknown flags and positional arguments exit 2, write nothing to standard output, and write this to standard error:

```text
bad argument: '<argument>'
<the complete short-help text from Spec 4>
```

The bad argument is the first unconsumed invalid argument. Do not call it an unknown command or subcommand. A missing value for `--colors` or `--large-diff-threshold` also exits 2, writes nothing to standard output, and writes exactly `option requires an argument: '<option>'\n` to standard error.

Semantic parsing failures exit 255 and write only their one-line diagnostic plus `\n` to standard error. Required diagnostics are:

- bad face: `unexpected face name: got '<value>', expected added|refine-added|removed|refine-removed`
- bad attribute: `unexpected attribute name: got '<value>', expected foreground|background|italic|noitalic|bold|nobold|dimmed|nodimmed|intense|nointense|underline|nounderline|none`
- bad named color: `unexpected color value: unrecognized color name '<value>'. Choose from: black, blue, green, red, cyan, magenta, yellow, white`
- decimal color outside 0 through 255: `unexpected color value: unrecognized ansi256 color number, should be '[0-255]' (or a hex number), but is '<value>'`
- malformed or out-of-range RGB: `unexpected color value: unrecognized RGB color triple, should be '[0-255],[0-255],[0-255]' (or a hex triple), but is '<value>'`
- `foreground` or `background` lacking a following color: `error parsing color: missing color value for face '<face>'`
- bad line-number style: `unexpected line number style: got '<value>', expected aligned|compact|fixed`
- bad threshold: `invalid threshold value: invalid digit found in string`, or, for an overflowing integer, `invalid threshold value: number too large to fit in target type`.

An empty color specification and `:` have an empty bad face. A trailing colon, as in `added:`, has an empty bad attribute. Negative numeric-looking colors such as `-5` are bad named colors. Parsing errors must be handled without crashing even for very long or Unicode arguments.

## Spec 6

A color specification is a colon-separated face followed by zero or more attributes. The exact faces are `added`, `removed`, `refine-added`, and `refine-removed`. A face alone is valid and is a no-op. Attributes are applied left to right to that face's current style:

- `foreground:C` and `background:C` set the indicated color;
- `C` may be one of the eight names `black`, `blue`, `green`, `red`, `cyan`, `magenta`, `yellow`, `white`, a base-10 integer 0..255, an exact three-component decimal `R,G,B` with each component 0..255, or `none` to clear only that color;
- `bold`, `italic`, `underline`, `dimmed`, and `intense` enable their attribute;
- `nobold`, `noitalic`, `nounderline`, `nodimmed`, and `nointense` disable it;
- attribute `none` resets that entire face to an unstyled state.

Repeated specifications accumulate changes. A later assignment to the same property wins; it does not discard unrelated properties. For example, `added:foreground:red`, then `added:foreground:blue`, then `added:bold` leaves the added face blue and bold. Within one specification the same left-to-right rule applies, so `added:bold:italic:nobold` leaves italic enabled and bold disabled.

## Spec 7

The initial styles are:

| Face | Initial style |
|---|---|
| `added` | green foreground |
| `removed` | red foreground |
| `refine-added` | bold, RGB(255,255,255) foreground, green background |
| `refine-removed` | bold, RGB(255,255,255) foreground, red background |

Output is always colored, even when standard output is not a terminal. Each nonempty rendered span is encoded independently as: `ESC[0m`, then zero or more SGR codes for its style, then the span bytes, then `ESC[0m`. If the span ends in LF, the LF is emitted after the final reset. Thus an unstyled line `abc\n` is exactly `ESC[0mabcESC[0m\n`, and adjacent spans contain adjacent reset sequences.

Style codes are emitted in this fixed order: bold `ESC[1m`, dimmed `ESC[2m`, italic `ESC[3m`, underline `ESC[4m`, foreground, then background. Named foreground codes are black 30, red 31, green 32, yellow 33, blue 34, magenta 35, cyan 36, white 37; backgrounds are the corresponding 40..47 codes. ANSI-256 uses `ESC[38;5;Nm` or `ESC[48;5;Nm`. RGB uses `ESC[38;2;R;G;Bm` or `ESC[48;2;R;G;Bm`. `intense` makes a named color use its bright 256-color index: black 8, red 9, green 10, yellow 11, blue 12, magenta 13, cyan 14, and white 15. Disabled attributes emit no enabling code because every span begins with a reset.

## Spec 8

Input is split inclusively at LF bytes. Processing outside a hunk is simple: wrap each complete or final partial input line as one unstyled span according to Spec 7. This applies to ordinary non-diff text and all unified/Git metadata, including `diff --git`, `index`, `---`, `+++`, mode changes, rename/copy information, diff-stat text, and binary-file markers. These lines are never mistaken for changes merely because file headers begin with `---` or `+++`.

A hunk starts at an outside line whose first visible byte is `@`. “Visible” here means after skipping any number of consecutive leading sequences that begin with `ESC[` and extend through the next byte `m`. Leading ordinary spaces are not skipped for hunk recognition, so an outside line such as `  @@ -1 +1 @@` remains ordinary text and a following `+` line also remains ordinary text. The hunk-header line itself is immediately emitted as one unstyled span. Subsequent lines belong to that hunk only while their first visible byte is one of `+`, `-`, space, or backslash. `+` and `-` are changes, space is context, and backslash is a warning such as `\ No newline at end of file`. Any other line ends and flushes the hunk; that line is then reconsidered outside the hunk and may begin the next hunk. End of input also flushes the hunk.

Hunks beginning with `@@`, `@@@`, or more `@` bytes are accepted for content processing. Empty hunks, context-only hunks, addition-only hunks, deletion-only hunks, adjacent hunks, and multiple files/hunks are valid.

## Spec 9

Within a buffered hunk, remove every embedded ANSI sequence that starts with `ESC[` and runs through the next `m`; use both the sanitized bytes and the first post-escape byte for parsing. Outside a hunk, embedded sequences remain part of the input span. Sanitization must not alter any other bytes.

Process data as bytes and preserve valid UTF-8 and invalid/non-text bytes. LF, CRLF, mixed line endings, tabs, control bytes, emoji, combining text, right-to-left text, and a final partial line must not cause a crash or truncation. A warning line beginning with backslash is emitted unstyled, receives no line-number margin, does not advance either line counter, and is excluded from refinement matching.

## Spec 10

For word refinement, make one token sequence from all removed lines in a hunk and another from all added lines in that hunk; context and warning lines are excluded. This deliberately permits matching across consecutive changed lines instead of pairing each removed line with only one added line.

On every changed line, exclude its leading `+`/`-` marker and all immediately following ASCII whitespace from tokenization. Retain those excluded bytes for output. Tokenize the remainder, including its line terminator, by Unicode grapheme boundaries. Classify a grapheme by its first scalar value:

- `Word` if it is alphanumeric or underscore;
- `Spaces` if it is an ASCII space or tab;
- `Other` otherwise.

Merge consecutive `Word` graphemes into one token and consecutive `Spaces` graphemes into one token. Every `Other` grapheme is its own token, even next to another `Other` token. Consequently identifiers such as `modified_param19` stay together; runs of spaces/tabs stay together; punctuation/operators are compared one grapheme at a time; and Unicode/emoji bytes remain intact.

## Spec 11

Compare token identity by exact byte equality. Find a longest common subsequence (equivalently, a shortest insert/delete edit path) between the complete removed and added token sequences. Shared tokens use the base face; all other token regions use the corresponding refined face.

The result must be deterministic for repeated tokens. Use Myers' divide-and-conquer shortest-edit-path tie behavior: on a forward diagonal choose the `k+1` predecessor at the lower boundary or when `V[k-1] < V[k+1]`; otherwise choose `V[k-1]+1`, then extend equal tokens. Traverse backward symmetrically, choosing `k+1` at the lower boundary or when backward `V[k+1] < V[k-1]`; otherwise choose `V[k-1]+1`, then extend equal tokens backward. Recurse in source order around the first overlap. When the edit distance is at most one, split at the first unequal token and retain the equal prefix and suffix.

After obtaining the LCS token values, normalize its embedding independently in each side to minimize fragmentation. Among embeddings of the same LCS, select one having the fewest alternating shared/unshared runs. This can be implemented as breadth-first search over `(next_lcs_index, next_sequence_index)`: enumerate occurrences of the next LCS token in ascending sequence-index order, coalesce the longest immediately equal run at each occurrence, do not revisit a coordinate, and take the first completed embedding (prefer an embedding ending exactly at the sequence end when encountered in that breadth). This normalization is what makes repeated words and line breaks highlight consistently.

## Spec 12

Paint each changed line from left to right. Its marker plus immediately following ASCII whitespace is one base-face span. Then alternate refined-face spans for bytes not covered by normalized shared token ranges and base-face spans for bytes covered by shared ranges. Shared ranges can begin on an earlier changed line and continue on a later one; clip them at each line boundary. A shared newline is still a real span: it produces the style prefix and reset before the LF even though it has no visible text.

Whitespace immediately before a terminating LF is special. If the pending span consists entirely of ASCII whitespace and the next span is exactly LF, paint that pending whitespace with an otherwise empty style having red background (`ESC[41m`) rather than either face. A changed line containing nothing after its marker except whitespace/newline paints the marker with its base face and the remainder with this red-background style. Do not apply this trailing-whitespace rule to a final line lacking LF.

Context lines are emitted as one unstyled span. Completely different changed text is entirely refined after its marker/leading whitespace. Added- or removed-only content is also refined, except for any token matches that exist elsewhere across the same hunk.

## Spec 13

These byte-exact examples define the span framing and refinement. In this section only, let `<0>` mean `ESC[0m`, `<red>` mean `ESC[31m`, `<green>` mean `ESC[32m`, `<ref-red>` mean `ESC[1mESC[38;2;255;255;255mESC[41m`, and `<ref-green>` mean `ESC[1mESC[38;2;255;255;255mESC[42m`. Angle-bracketed names represent bytes and are not themselves output.

For input:

```text
@@ -1 +1 @@
-server_port = 8080
+server_port = 3000
```

the output bytes are:

```text
<0>@@ -1 +1 @@<0>\n
<0><red>-<0><0><red>server_port = <0><0><ref-red>8080<0><0><red><0>\n
<0><green>+<0><0><green>server_port = <0><0><ref-green>3000<0><0><green><0>\n
```

The empty base-face span before each LF above is intentional: the matching newline is a shared token. For the one-line change `-if (x == y) { return true; }` to `+if (x != y) { return false; }`, the removed refined pieces are the second `=` and `true`, while the added refined pieces are `!` and `false`; all remaining text uses the base removed/added face. For `-hello world` to `+hello  world`, the words remain base-faced and the respective one-space/two-space token is refined.

A lone added line `+hello\n` in a hunk with no removed token match is exactly `<0><green>+<0><0><ref-green>hello<0>\n`. A plain outside line `diff --git a/a b/a\n` is exactly `<0>diff --git a/a b/a<0>\n`.

## Spec 14

Line numbers are derived from hunk headers only when `--line-numbers` is enabled. This parser is invoked only after the hunk-recognition rule in Spec 8 succeeds. Parse the already-recognized header as:

1. optional leading ASCII whitespace;
2. one or more `@` bytes;
3. one or more ASCII whitespace bytes;
4. one or more minus ranges, separated by whitespace, keeping the last minus range;
5. one plus range;
6. one or more whitespace bytes and one or more closing `@` bytes.

A range is `-START[,LENGTH]` or `+START[,LENGTH]`; omitted length means 1. Leading SGR sequences may occur anywhere the parser examines and are ignored. Decimal accumulation must be overflow-checked. Standard examples include `@@ -1,3 +1,4 @@`, `@@ -1 +1 @@`, `@@ -0,0 +1 @@`, and combined form `@@@ -1,1 -1,1 +1,1 @@@` (use the last minus range).

The hunk-header text itself is preserved and has no margin. Start each hunk's old and new counters at its parsed starts. Reset both counters from every new hunk header. Removed lines display then increment only the old counter; added lines display then increment only the new counter; context lines display then increment both. Warning lines display neither and increment neither.

## Spec 15

For a hunk, compute a half-width `w` once. Let `digits(0)=0` and otherwise let `digits(n)` be its decimal digit count. Then:

`w = max(digits(old_start + old_length), digits(new_start + new_length), minimum_style_width)`

The minimum is 0 for `compact` and `aligned`, and 3 for `fixed`. The conceptual full margin is `2*w+1` bytes. If either hunk start is zero, suppress the zero side entirely and use only a single `w`-byte column; never print line number 0 for a new or deleted file.

With both columns present, before the original diff line bytes:

- removed line: old number right-aligned to `w`, one space, then `w` spaces;
- added line: `w` spaces, one space, then new number right-aligned to `w`;
- context with equal old/new number: `w` spaces, one space, then the new number right-aligned to `w`;
- context with different numbers: old number right-aligned to `w`, one space, then new number right-aligned to `w`.

The original marker follows immediately; there is no colon or extra delimiter. Because a context diff line itself begins with a space, a visible space follows its margin.

Changed-line margins are styled as independent spans with that line's base face and therefore have reset codes around them. The `+`/`-` marker is a second base-face span. Context margins are raw unstyled bytes without surrounding SGR, while the context line is then one independently reset-framed unstyled span.

## Spec 16

`compact` emits exactly the margin from Spec 15. `aligned` emits that same margin and then appends one literal tab if, and only if, the emitted margin byte length is not divisible by 8. `fixed` is compact behavior with `w` at least 3 and emits no tab. Although `fixed` is omitted from help, it is valid.

After stripping ANSI, this input and compact output illustrate exact spacing:

```text
input:                              compact output:
@@ -1,3 +1,3 @@                     @@ -1,3 +1,3 @@
 hello                               "  1 hello"
-world                               "2  -world"
+universe                            "  2+universe"
 foo                                 "  3 foo"
```

Aligned mode changes those four margins to `"  1\t"`, `"2  \t"`, `"  2\t"`, and `"  3\t"`. Fixed mode changes them to `"      1"`, `"  2    "`, `"      2"`, and `"      3"` before the original line bytes. In a new-file hunk `@@ -0,0 +1,3 @@`, compact added lines begin `1+`, `2+`, `3+`; in a deletion hunk `@@ -1,3 +0,0 @@`, removed lines begin `1-`, `2-`, `3-`.

## Spec 17

`--large-diff-threshold` sets the maximum search depth used for each recursive Myers middle-snake search. The default is 1000. Parse it as a platform-sized unsigned decimal integer (the evaluation platform is 64-bit). Zero is valid and means no cap. For token counts `n` and `m`, an uncapped search considers depths through `(n+m+1)/2` inclusive; a positive threshold caps the number of tried depths to values `0 .. threshold-1`. If no overlap is found under that cap, that subproblem contributes no shared tokens, so its content is refined wholesale. Regardless of threshold, all source bytes are still emitted.

Small positive values, zero, values such as 123/500/999999, and the default must complete successfully. Negative, nondecimal, and overflowing values fail as in Spec 5.

## Spec 18

`--debug` does not alter normal standard output. After all input is processed, it writes a four-line timing report to standard error with these labels in this order:

```text
hunk processing time (ms)
-- compute lcs (ms)
-- optimize lcs (ms)
total processing time (ms)
```

Each line includes a nonnegative integer millisecond value. The first three additionally include a parenthesized percentage such as `(0.000%)`; when total time is zero, a `NaN%` representation is permitted. The labels are right-aligned in a 35-character field, and numeric/ratio fields are right-aligned in 15-character fields. The report is produced even for empty input. It composes with colors, thresholds, line numbers, multiple hunks, and large input; diagnostics never go to standard output.

## Spec 19

The implementation must stream/read arbitrary-sized input safely and finish within ordinary command-test timeouts. It must handle at least: lines tens of thousands of bytes long, thousands of hunks or changed lines, large line starts through at least 100000 and into the millions, all printable ASCII, multilingual UTF-8, combining marks and emoji sequences, embedded NUL/non-UTF-8 bytes, repeated-token patterns, deeply punctuated source/JSON/XML/SQL/URLs, and hunks with many consecutive additions/removals. It must never drop visible content, synthesize unrelated text, panic on malformed diff-like input, or confuse Git metadata and binary markers with hunk changes.
