# Behavioral specification for `executable`

## Spec 1

The required artifact is a directly runnable command-line program named exactly `executable`. It implements the behavior of `tuc` version 1.3.0: it cuts an input into fields, characters, bytes, or lines and emits the requested portions. Standard output and standard error are byte streams. Successful data-processing invocations exit 0; argument, validation, I/O, and out-of-bounds failures exit 1 unless a specific panic behavior below applies, in which case any nonzero status is acceptable.

The accepted switches are:

- flags: `-g`/`--greedy-delimiter`, `-p`/`--compress-delimiter`, `-s`/`--only-delimited`, `-V`/`--version`, `-z`/`--zero-terminated`, `-h`/`--help`, `-m`/`--complement`, `-j`/`--join`, `--no-join`, `--json`, and `--no-mmap`;
- valued options: `-f`/`--fields`, `-b`/`--bytes`, `-c`/`--characters`, `-l`/`--lines`, `-d`/`--delimiter`, `-e`/`--regex`, `-r`/`--replace-delimiter`, `-t`/`--trim`, `--fallback-oob`, and `-M`/`--fixed-memory`;
- at most one positional argument, interpreted as an input file path.

Options may occur before or after one another and before or after the file path. Long option values may be separate or use `=`, and a short fields value may be attached: `-f 2`, `-f2`, `--fields 2`, and `--fields=2` are equivalent. A token beginning with `-` that immediately supplies a valued option is its value, not another flag; required cases include field value `-1` and literal delimiter values `-` and `--`.

## Spec 2

`-V` and `--version` write exactly `tuc 1.3.0\n` to stdout, nothing to stderr, and exit 0.

`--help` exits 0 and writes the following exact uncolored UTF-8 text to stdout (including the final newline), with empty stderr:

```text
tuc 1.3.0
Cut text (or bytes) where a delimiter matches, then keep the desired parts.

USAGE:
    tuc [FLAGS] [OPTIONS] < input
    tuc [FLAGS] [OPTIONS] filepath

FLAGS:
    -g, --greedy-delimiter        Match consecutive delimiters as if it was one
    -p, --compress-delimiter      Print only the first delimiter of a sequence
    -s, --only-delimited          Print only lines containing the delimiter
    -V, --version                 Print version information
    -z, --zero-terminated         Line delimiter is NUL (\0), not LF (\n)
    -h, --help                    Print this help and exit
    -m, --complement              Invert fields (e.g. '2' becomes '1,3:')
    -j, --(no-)join               Print selected parts with delimiter in between
    --json                        Print fields as a JSON array of strings
    --no-mmap                     Disable memory mapping

OPTIONS:
    -f, --fields <bounds>         Fields to keep, 1-indexed, comma separated.
                                  Use colon (:) to match a range (inclusive).
                                  Use equal (=) to apply out of bound fallback.
                                  Fields can be negative (-1 is the last field).
                                  [default: 1:]

                                  e.g. cutting the string 'a-b-c-d' on '-'
                                    -f 1     => a
                                    -f 1:    => a-b-c-d
                                    -f 1:3   => a-b-c
                                    -f 3,2   => cb
                                    -f 3,1:2 => ca-b
                                    -f -3:-2 => b-c
                                    -f 1,8=fallback => afallback

                                  To re-apply the delimiter add -j, to replace
                                  it add -r (followed by the new delimiter).

                                  You can also format the output using {} syntax
                                  e.g.
                                    -f '({1}, {2})' => (a, b)

                                  You can escape { and } using {{ and }}.

    -b, --bytes <bounds>          Same as --fields, but it keeps bytes
    -c, --characters <bounds>     Same as --fields, but it keeps characters
    -l, --lines <bounds>          Same as --fields, but it keeps lines
                                  Implies --join. To merge lines, use --no-join
    -d, --delimiter <delimiter>   Delimiter used by --fields to cut the text
                                  [default: \t]
    -e, --regex <some regex>      Use a regular expression as delimiter
    -r, --replace-delimiter <new> Replace the delimiter with the provided text.
                                  Implies --join
    -t, --trim <type>             Trim the delimiter (greedy). Valid values are
                                  (l|L)eft, (r|R)ight, (b|B)oth
        --fallback-oob <fallback> Generic fallback output for any field that
                                  cannot be found (oob stands for out of bound).
                                  It's overridden by any fallback assigned to a
                                  specific field (see -f for help)
    -M, --fixed-memory <size>     Read the input in chunks of <size> kilobytes.
                                  This allows to read lines arbitrarily large.
                                  Works only with single-byte delimiters,
                                  fields in ascending order, -z, -j, -r

Options precedence:
    --trim and --compress-delimiter are applied before --fields or similar

Memory consumption:
    --characters and --fields read and allocate memory one line at a time

    --lines allocate memory one line at a time as long as the requested fields
    are ordered and non-negative (e.g. -l 1,3:4,4,7), otherwise it allocates
    the whole input in memory (it also happens when -p or -m are being used)

    --bytes allocate the whole input in memory

    --fixed-memory will read the input in chunks of <size> kilobytes. This
    allows to read lines arbitrarily large. Works only with single-byte
    delimiters, fields in ascending order, -z, -j, -r

Colors:
    Help is displayed using colors. Colors will be suppressed in the
    following circumstances:
    - when the TERM environment variable is not set or set to "dumb"
    - when the NO_COLOR environment variable is set (regardless of value)
```

`-h` also exits 0, emits no stderr, and displays help beginning with `tuc 1.3.0` and containing the description, `USAGE:`, `FLAGS:`, `OPTIONS:`, `--fields`, and `--delimiter`. The exact uncolored form above is mandatory for `--help` whenever `TERM` is absent or equals `dumb`, or whenever `NO_COLOR` exists with any value. Other `TERM` values may add ANSI styling without changing the words. Help has absolute precedence: if `-h` or `--help` appears anywhere, even among unknown arguments, extra positionals, or after a literal `--`, show help successfully and emit no error.

## Spec 3

An invocation with no command-line arguments shows help/information rather than reading stdin. It exits 0, starts stdout with `tuc`, includes the description and usage information, and emits well over 100 bytes. Printing the full help from Spec 2 is valid. This remains true even if stdin contains data.

If there is at least one processing option, input comes from the sole positional file path when present, otherwise from stdin. A file path takes precedence over supplied stdin data. Empty input (zero bytes) succeeds with zero output. A final record without a terminator is still processed. File and stdin processing must otherwise agree. `--no-mmap` is accepted for either input source and cannot change output.

A nonexistent path fails with exactly `tuc: runtime error. The file "PATH" does not exist\n`; an existing directory fails with exactly `tuc: runtime error. The path "PATH" is not a file\n`. These failures have empty stdout.

## Spec 4

Field and character modes process the input as a sequence of records. The normal record separator is byte LF (`0A`). When a record ends in CRLF, both the LF and the immediately preceding CR are removed before field/character processing. A CR anywhere else is ordinary record content: this includes an embedded CR, the final byte of an unterminated record, and a CR before a NUL separator under `-z`. Every processed result is terminated with one LF, including a final input record that lacked LF. An LF-terminated input does not create an extra record after its last LF. Empty records between consecutive separators are preserved and normally produce an empty output record. A completely empty stream produces none. Thus `-d : -f 2` on `a:x\r\n` emits `x\n`, while the same invocation on the unterminated bytes `a:x\r` emits `x\r\n`.

An empty record is handled by an early empty-record path: it emits only its record terminator without attempting bounds, fallback, format, or JSON conversion. Thus even requesting field 2 from an empty line emits an empty line rather than an out-of-bounds error. `-s` instead skips such a record.

With `-z`/`--zero-terminated`, replace LF by NUL (`00`) for both record parsing and emitted record terminators. LF is then ordinary data. For example, `-z -d _ -f 2` on `hello_world\0foo_bar` emits `world\0bar\0`, and adjacent NULs represent an empty record rather than being collapsed.

## Spec 5

All four selection options use the same bounds language. Positions are 1-based. A positive `n` is position `n`; a negative `-n` counts backward from the current sequence (`-1` is last). A comma-separated list preserves requested order and duplicates. `a:b` is an inclusive range. `a:` runs from `a` through the end and `:b` runs from the first item through `b`. A bare `:` is invalid. Bounds may be mixed, as in `1,-1` or field range `2:-2`; resolve negatives against each record before extracting. Equal-ended ranges select one item. Overlapping ranges retain repetitions rather than being merged.

Field mode has an out-of-bounds exception for a finite range whose start resolves in bounds and whose positive right endpoint exceeds the record width: clip that endpoint to the final field instead of failing. This clipping is applied after trim/compression. For example, `-d , -f 1:100` on `a,b,c` emits `a,b,c\n` with exit 0 and empty stderr. Likewise, `-d - -f 1:7 --trim b -j` on `---a---b---\n` emits `a---b\n` with exit 0 and empty stderr. A range whose start is out of bounds still fails normally; this exception does not redefine the behavior of character or line ranges.

Examples for `a-b-c-d-e` cut on `-` include: `1` => `a`; `3,1,2` => `cab`; `2,2,1` => `bba`; `-1` => `e`; `-3:-1` => `c-d-e`; and `1:3,2:4` => `a-b-cb-c-d` when no separator is inserted between the two range results.

A bounds token may carry a dedicated fallback after `=`, such as `8=fallback`. The same syntax is valid inside a format placeholder, such as `{8=fallback}`. The fallback is output only if that bound cannot be resolved.

## Spec 6

Without `-b`, `-c`, or `-l`, the program is in field mode. `-f`/`--fields` supplies its bounds, defaulting to `1:` when omitted. Its delimiter defaults to one tab byte. `-d`/`--delimiter` selects an arbitrary literal byte string; regex metacharacters have no special meaning to `-d`. Literal delimiters can be ASCII punctuation, backslashes, repeated/similar strings such as `||`, `aa`, `aba`, `abab`, or arbitrarily long, and can be multibyte UTF-8 such as `→`, `••`, `€`, or emoji.

The empty literal delimiter is accepted rather than rejected. It creates empty boundary fields with the record content split between them: on `abc\n`, `-d '' -f 1` emits only `\n`, `-d '' -f 2` emits `a\n`, and `-d '' -f 1:` emits `abc\n`; all three exit 0 with empty stderr.

Find literal occurrences left-to-right and non-overlapping. Each occurrence separates two fields. Thus consecutive occurrences normally create empty fields, including at the beginning and end: `a--b` cut on `-` is `a`, empty, `b`; `,,,` cut on `,` is four empty fields; and `a||b||||c` cut on `||` is `a`, `b`, empty, `c`. Preserve empty fields and arbitrary field bytes exactly. A record containing no delimiter is one field. Field processing supports binary content; splitting is by raw delimiter bytes even though option text itself is UTF-8.

Processing is independent per record, including records of different widths and empty records. No fixed field-count or field-size limit may be imposed at the tested scales (thousands of fields and multi-megabyte records).

## Spec 7

In ordinary field output, each comma-separated bound is an output part. A single position produces that field. A range produces the contiguous source span from its first through last selected field, retaining original delimiter occurrences inside that range. Adjacent output parts are concatenated by default. Consequently, for `a-b-c-d`, `-f 3,2` emits `cb\n`, while `-f 3,1:2` emits `ca-b\n`, and `-f 1:3` emits `a-b-c\n` even without `-j`.

`-j`/`--join` inserts the applicable delimiter between separate output parts. It does not add a delimiter before the first or after the last part. Internal delimiters already belonging to a selected range remain. Examples: `-d - -f 3,2 -j` on `a-b-c-d` emits `c-b\n`; `-d , -f 1,3 -j` emits `a,c\n`; `--no-join` explicitly selects the default concatenating behavior.

`-r NEW`/`--replace-delimiter NEW` implies join. It uses `NEW` between separate selected parts and substitutes `NEW` for every retained internal delimiter in ranges. `NEW` may contain multiple bytes, Unicode, whitespace, or be empty. Thus `-d - -f 1:3 -r ' -> '` emits `a -> b -> c\n`, and `-r ''` emits `abc\n`.

## Spec 8

If a bounds argument contains unescaped brace placeholders, it is a format template rather than a comma list. Literal text is copied and `{bounds}` is replaced using the same single/range extraction rules. Negative positions, ranges, repeated placeholders, and `{bounds=fallback}` work. Examples include `({1}, {2})`, `{-1}/{1}`, and `{1}, {2:4}`; on `a-b-c-d-e`, the last produces `a, b-c-d\n`.

`{{` and `}}` escape one literal brace; escaping is recursive by pairs, so `{{{{nested}}}} {1}` produces `{{nested}} a`. In literal template text, the two-character escapes `\n` and `\t` become LF and tab. Other spaces and Unicode text are preserved. Formatting is applied independently to every field/character record. The normal record terminator is still appended after the expanded template; therefore a template containing `\n` may produce more than one output line per input record.

Merely writing text outside braces makes that text literal. For example, character template `1-{5=MISSING}` on `ab` emits `1-MISSING\n`, not the first character followed by the fallback.

## Spec 9

An unresolved position normally stops processing, exits 1, and writes exactly `Error: Out of bounds: N\n` to stderr, where `N` is the requested signed or unsigned position. Output already written before the failure is not rolled back, and no final record terminator is appended. For example, `-d ' ' -f 1,4` on `a b c\n` leaves stdout `a`; with `-j` it leaves `a ` because the inter-part delimiter is written before resolving field 4. Earlier complete records also remain. The clipped field-range endpoint in Spec 5 is not an unresolved position.

`--fallback-oob VALUE` changes every otherwise-unhandled out-of-bounds reference to literal `VALUE`; `--fallback-oob=` is a present, empty fallback. A bound-specific `=VALUE` takes priority over the global fallback. Fallback text is literal (for example, `3=""` emits two quote bytes). These rules apply to ordinary field/character lists, formats, negative references, and supported fixed-memory field processing. In-bounds references always use the actual value. Byte mode is the exception described in Spec 17: it accepts fallback syntax but does not apply either kind of fallback.

## Spec 10

`-m`/`--complement` complements each comma-separated selection part independently after resolving that part's negative bounds; it does not first union all requested parts. For each part, select every position not covered by that part in source order, then concatenate the per-part complement results in request order. Positions can therefore repeat across results. Contiguous runs within one result retain their internal delimiters, and separate runs follow normal join behavior. For `a-b-c-d`, complementing the single field 2 emits `ac-d\n` without `-j`, `a-c-d\n` with `-j`, and `a|c|d\n` with `-r '|'`.

This per-part rule is observable for lists. On `abcde\n`, `-c 2,4 --complement` emits exactly `acdeabce\n`. On `a-b-c-d-e\n`, `-d - -f 2,4 --complement --json` emits exactly `["a","c","d","e","a","b","c","e"]\n`, one JSON element per position in the resulting per-part sequence. On the same field record, complementing `-1,2:3` emits exactly `a-b-c-dad-e\n`: the complement of `-1` is followed by the complement of `2:3`. Complementing all available positions with a single selection part fails nonzero with `Error: the complement is empty\n`.

## Spec 11

`-g`/`--greedy-delimiter` treats a run of directly adjacent occurrences of the chosen delimiter as one logical split. It removes the empty fields that the run would otherwise create. For an internal run, if original delimiters are being retained or joined, the full original run is retained: with space delimiter, `a  b   c`, bounds `1:3`, `-g -j` emits exactly `a  b   c\n`. With `-p` as well, the run is instead represented once.

Greedy behavior applies to multicharacter delimiters too. For example, delimiter `::` sees `::::` as two adjacent occurrences and `-g` treats them as one split; delimiter `||` with `a||b||||c`, bounds `1:3`, `-g -j` reconstructs `a||b||||c\n`. At a record edge, a delimiter run still creates the normal empty boundary field unless trimming removes it, but joined output retains only one delimiter occurrence for that edge run. Thus `-d :: -f 1,2,3 -g -j` on `::::a::::\n` emits exactly `::a::\n`, not the full leading and trailing runs.

## Spec 12

In field mode, `-p`/`--compress-delimiter` replaces every maximal run of adjacent delimiter occurrences with the first occurrence only before bounds are selected. It therefore both removes intervening empty fields and changes retained/joined text. For example, `-d - -p -f 2` on `foo---bar` emits `bar\n`; the default `1:` on `--foo---bar--` emits `-foo-bar-\n`; an all-delimiter record `----` emits `-\n`. Compression applies independently at leading, internal, and trailing runs and supports fixed multibyte delimiters. In line mode the option is accepted but does not compress adjacent record separators: `-l 1: -p` on `a\n\n\nb\n` emits the unchanged `a\n\n\nb\n`.

`-t MODE`/`--trim MODE` removes maximal delimiter matches only from record boundaries, before splitting and selection. `l` or `L` removes the left run, `r` or `R` the right run, and `b` or `B` both. It does not trim whitespace generally and does not remove internal empty fields. For example, delimiter `-`, `---a--b---c---` becomes `a--b---c`, `a--b---c---`, or `---a--b---c` for modes `b`, `l`, or `r`. If trimming makes a record empty, emit just its record terminator unless `-s` is active, in which case skip it.

Trim and compression occur before bounds, negative-index resolution, complement, formatting, or JSON. Combining them trims edge runs and compresses remaining internal runs. They match the configured literal string or regex, not a generic character class: trimming space delimiters does not remove tabs.

## Spec 13

`-e PATTERN`/`--regex PATTERN` replaces the fixed field delimiter with a regular expression, matched left-to-right with non-overlapping, leftmost-first semantics. Capturing groups only affect matching and do not become fields. The required pattern language includes:

- literal characters and escaped metacharacters such as `\.`, `\*`, `\+`, `\?`, `\(`, `\[`, and `\{`;
- wildcard `.`, anchors `^` and `$`, alternation `|`, and capturing groups `(…)`;
- classes such as `[abc]`, `[0-9]`, and `[^a-z]`;
- `\d`, `\D`, `\W`, `\s`, and `\t`;
- quantifiers `?`, `+`, `{n}`, and `{n,}`.

Patterns operate on UTF-8 records and may match variable-width delimiters. Examples: `[0-9]+` splits `a123b456c` into `a,b,c`; `[,;:]` splits on any listed punctuation; `\s+` treats each whitespace run as a delimiter. Regex delimiters work with greedy matching, trim, only-delimited, complement, negative bounds, fallbacks, formats, files, and multiline input except for the specific crashing combination preserved in Spec 23.

Because an original regex match has no single fixed join token, `-e` combined with explicit `-j` is invalid unless `-r` is also present. Likewise, `-e` with `-p` is invalid unless `-r` is present. With a replacement, retained/internal and inserted separators use that replacement; for example `-e '\\s+' -f 1:3 -r '|'` on `a  b\tc` emits `a|b|c\n`.

## Spec 14

In field mode, `-s`/`--only-delimited` filters records that contain no configured delimiter match, instead of allowing their one field to be selected or to cause an out-of-bounds error. It is evaluated after boundary trimming: a delimiter-only record trimmed to empty is skipped. Records that do contain a delimiter are processed normally, including those beginning/ending with it or consisting solely of delimiters. Output records retain their relative order. With comma delimiter, field 2, and input `abc\na,b\nc,d`, `-s` emits `b\nd\n`.

Character mode does not use the configured delimiter to filter nonempty records under `-s`. For example, `-c 1:2 -d , -s` on `ab\na,b\n` emits `ab\na,\n`: the nondelimited `ab` record is retained. Physically empty character records are still skipped under `-s` as specified by the empty-record rule in Spec 4.

## Spec 15

`--json` changes field or character selection to one compact JSON array per nonempty input record. Each selected individual position is one JSON string; ranges expand to individual elements, and order and duplicates are retained. Thus `-d / --json -f 1,2,1:3` on `a/b/c/d` emits exactly `["a","b","a","b","c"]\n`. A single selection is still a one-element array. All values remain strings, including text resembling numbers, booleans, or null.

Serialization has no spaces after commas, escapes JSON quotes, backslashes, and control characters, and emits valid Unicode directly rather than ASCII `\u` escapes (for example emoji remains UTF-8). Empty fields are empty strings. A physically empty record is a special case: it emits only the record terminator, not `[""]`; a nonempty delimiter-only record still yields the appropriate array of empty strings. Under `-z`, terminate each JSON array with NUL rather than LF.

JSON is compatible with field/character ranges, negative indices, complement, trim, `-s`, fallback, explicit `-j`, and brace expressions made entirely of adjacent placeholders. Such a placeholder-only expression is treated as a JSON selection rather than a literal-output format: `--json -f '{1}'` on `a\n` emits `["a"]\n`, and `-d - --json -f '{1}{2}'` on `a-b\n` emits `["a","b"]\n`. JSON is incompatible with bytes or lines, replacement, `--no-join`, and brace templates containing literal output text; for example `--json -f 'x{1}'` is rejected with the diagnostic in Spec 21.

## Spec 16

`-c BOUNDS`/`--characters BOUNDS` selects Unicode scalar values (code points), not UTF-8 bytes and not extended grapheme clusters, separately within each LF/NUL record. Emoji and composed `é` each count as one; a decomposed base plus combining mark counts as two positions. Accordingly, positions `1:2` from `e` followed by U+030A followed by `café` produce the two-code-point sequence `e`+U+030A and then the record terminator.

Lists, ranges, negative indices, duplicates, reverse ordering, complement, formats, and fallback behave as in field mode, except that character ranges are unpacked into individual character positions. Selected characters normally concatenate; character mode implicitly uses join semantics with an empty separator. `-r` supplies a separator between each selected character position, so `-c 1,2,3 -r -` on `abc` emits `a-b-c\n`. `-d` does not change character indexing. Character processing is per record, so `-c 1:3` on `abc\ndef` emits `abc\ndef\n`; with JSON, that same range becomes three array elements per record.

## Spec 17

`-b BOUNDS`/`--bytes BOUNDS` selects raw bytes from the entire input stream as one sequence. It does not split at LF or NUL, does not validate UTF-8 boundaries, and emits no automatic trailing record terminator. Thus `-b 1:3` on `abc\ndef` emits exactly `abc`, `-b 1:4` on UTF-8 `café` emits `caf` plus the first byte of `é`, and selection can include embedded NUL or invalid bytes. `-d` and `-z` do not subdivide byte mode.

Byte positions support positive/negative indices, inclusive/open ranges, reordered and duplicate selections, and brace-format literals/placeholders. Formatting remains raw and adds no terminator: `-b '{1}:{5}'` on `hello` emits exactly `h:o`. Although byte bounds accept both a bound-specific fallback and `--fallback-oob` syntactically, neither fallback is applied to an out-of-bounds byte. For example, `-b 1,9=X --fallback-oob G` on `abc` exits 1, leaves stdout exactly `a`, and writes exactly `Error: Out of bounds: 9\n` to stderr. `-p` is invalid in byte mode.

## Spec 18

`-l BOUNDS`/`--lines BOUNDS` selects records from the entire input as line units. It uses LF normally and NUL under `-z`. Ordinary ascending positive selections and ranges work: `-l 1,3` on `a\nb\nc\n` emits `a\nc\n`, `-l 2:3` emits `b\nc\n`, `-l :3` selects the first three, and `-l 5:` selects line 5 through EOF. Empty lines count. The mode implies `--join`, meaning selected lines remain separated and the final selected line is terminated even if the source lacked a final terminator. `--no-join` removes separators between selected line parts but still appends one final terminator: `-l 1,3 --no-join` emits `ac\n`.

Preserve the reference's negative-line quirk: the lone bound `-1` selects the entire input rather than only the last line. Thus `-l -1` on `a\nb\nc\n` exits 0 and emits exactly `a\nb\nc\n` with empty stderr. Other tested forward-streaming quirks remain: `-l 3,1` on three lines fails with empty stdout and exactly `Error: Out of bounds: 3\n`; both `-l 2:-2` and `-l 2:-4` on four or five ordinary lines likewise fail on position 2 with that exact error. Do not normalize those cases into successful reordered/mixed-negative selections.

Line format behavior retains implied join between every template component. The required example is `-l '{1}|{2}'` on `line1\nline2\nline3`, which emits exactly `line1\n|\nline2\n`. JSON is unavailable for lines.

## Spec 19

Argument syntax errors are reported on stderr with empty stdout and exit 1. Required exact messages (each followed by `\n`) are:

- nonnumber `X`: ``failed to parse 'X': Not a number `X` ``;
- zero anywhere a position is expected: `failed to parse 'SPEC': Zero is not a valid field` (this includes `0`, `-0`, `1:0`, `{0}`, and `0=fallback`);
- empty bounds: `failed to parse '': UserBoundsList must contain at least one UserBounds`;
- empty comma component in `1,,2`, `1,`, or `,1`: `failed to parse 'SPEC': Field format error: empty field`;
- same-sign reversed ranges such as `3:1` or `-1:-3`: `failed to parse 'SPEC': Field left value cannot be greater than right value`;
- bare colon: an error containing ``Field format error, no numbers next to `:` ``;
- unmatched `{`: `failed to parse '{1': Field format error: missing closing parenthesis`;
- unmatched `}`: `failed to parse '}': Field format error: missing opening parenthesis`;
- malformed `{{1}`: `failed to parse '{{1}': Field format error: missing opening parenthesis`;
- invalid trim `X`: `failed to parse 'X': Valid trim values are (l|L)eft, (r|R)ight, (b|B)oth`.

Integers too large for a signed machine-sized position are “Not a number” errors using the same template. A malformed multi-colon expression such as `1:2:3` also contains `Not a number`. A nonnumeric or negative `-M` value exits 1 with a message beginning `failed to parse`.

A valued option without its value exits 1; its stderr begins `the '-d' option doesn't have an associated value` (or substitutes the exact spelling used, such as `--delimiter` or `-f`).

## Spec 20

Unknown/unconsumed arguments exit 1 with empty stdout and this exact two-line stderr form:

```text
tuc: unexpected arguments: ["ARG1", "ARG2"]
Try 'tuc --help' for more information.
```

Use JSON-like double-quoted argument strings and preserve their order. This covers unknown flags and more than one positional path. A bare `--` is not supported as an option separator and is itself unexpected. The special spelling `-z=foo` is parsed as boolean `-z` plus an unexpected `-=foo`, producing that value in the argument list. Help precedence from Spec 2 overrides all these errors.

Malformed regexes exit 1 with empty stdout. The exact diagnostics for the two required forms are:

```text
tuc: runtime error. The regular expression is malformed. regex parse error:
    [
    ^
error: unclosed character class
```

and

```text
tuc: runtime error. The regular expression is malformed. regex parse error:
    (abc
    ^
error: unclosed group
```

Each ends in LF. Other malformed patterns must similarly mention both that the regular expression is malformed and `regex parse error`.

## Spec 21

Reject incompatible options before processing, with exit 1, empty stdout, and exactly the applicable message plus LF:

- `-j` with `--no-join`: `tuc: runtime error. It's not possible to use --join and --no-join simultaneously`;
- `-r` with `--no-join`: `tuc: runtime error. You can't pass --no-join when using --replace, which implies --join`;
- `--json` with `--no-join`: `tuc: runtime error. Using both --json and --no-join is not permitted`;
- `--json` with `-r`: `tuc: runtime error. The use of --replace with --json is not supported`;
- `--json` with byte or line mode: `tuc: runtime error. --json support is available only for --fields and --characters`;
- `--json` with a brace template containing literal output text: `tuc: runtime error. Cannot format fields when using --json` (a placeholder-only expression such as `{1}` is accepted as specified in Spec 15);
- character mode with `--no-join`: `tuc: runtime error. Since --characters implies --join, you can't pass --no-join`;
- `-p` in byte or character mode: `tuc: runtime error. Delimiters can be compressed only with --fields and --lines`;
- regex plus `-j` without replacement: `tuc: runtime error. Cannot use --regex and --join without --replace-delimiter`;
- regex plus `-p` without replacement: `tuc: runtime error. Cannot use --regex and --compress-delimiter without --replace-delimiter`;
- `-M 0`: `tuc: runtime error. --fixed-memory cannot be 0`.

## Spec 22

`-M SIZE`/`--fixed-memory SIZE` selects chunked field processing, where `SIZE` is a positive integer number of kilobytes. It must work on stdin and files, across chunk boundaries, on records much longer than the chunk, with LF or `-z`, with ordinary no-join output, explicit `-j`, single-byte `-r`, forward inclusive/open ranges, per-bound fallback, and forward-order format placeholders with literal fillers. `--no-mmap` remains behaviorally neutral.

Fixed-memory mode requires field mode; nonnegative strictly forward bounds (no reverse order or duplicate position); a literal delimiter exactly one byte wide; and, if present, a replacement exactly one byte wide. It rejects regex, complement, greedy, compression, JSON, trim, and only-delimited. Most such unsupported combinations fail exactly with `tuc: runtime error. StreamOpt supports solely forward fields, join and single-character delimiters\n`. A multibyte input delimiter instead fails with `tuc: runtime error. Delimiter must be 1 byte wide for FastOpt\n`. Reverse or repeated bounds fail with `tuc: runtime error. Bounds cannot be converted to ForwardBounds\n`.

Preserve one tested fixed-memory output quirk: with explicit `-j`, a first selected forward range beginning after field 1 retains the separator immediately before that range. Thus `-M 1 -d - -f 2,4 -j` on `a-b-c-d-e\n` emits `-b-d\n`, and `-M 1 -d - -f 2:4 -j` emits `-b-c-d\n`. When the first selected item is field 1 there is no leading separator, and without `-j` the same parts concatenate normally.

## Spec 23

Preserve the following tested failure quirks rather than substituting cleaner behavior:

- On input containing both a delimited and a nondelimited record, field processing with `-g -s -j` (for example delimiter space and bounds `1:3`) terminates nonzero and stderr contains both `We didn't use an extract function that counted the number of fields` and `src/cut_str.rs:<error location>`.
- `-e '-+' -t b -s -f '{-1}/{4=NA}'` on `--a--12--b--\nplain\n--x--y--\n` terminates nonzero with empty stdout; stderr contains both `We didn't use an extract function that counted the number of fields` and `src/cut_str.rs:<error location>`.
- `--complement --lines 2` on `a\nb\nc\n` terminates nonzero and stderr contains `panicked` and `cut_str.rs`.

The program must be robust and timely on the tested scale: at least 50,000 records, 10,000 fields in one record, a roughly 2 MB record, raw byte selections of at least 100 KB input, thousands of consecutive delimiters, Unicode/multibyte data, and ordinary file inputs larger than 100 KB. It must not truncate at internal buffer boundaries or impose small arbitrary limits.
