# Clarified specification for `executable`

The required artifact is a Unix command-line program named exactly `executable`. It is a compatibility implementation of the behavior described below. This document and the companion normative `.txt` assets beside it comprise the entire specification; no source tree, network service, test fixture, or external documentation is part of the contract. All byte strings, paths, patterns, and file contents are arbitrary unless a section narrows them. “Print” means write to standard output; diagnostics go to standard error. Programs invoked by `--pre` and decompression programs used by `--search-zip` are environment-provided commands, not functionality that must be embedded in `executable`.

When several options select opposite settings, process them from left to right and let the last applicable option win, except for terminal modes such as help and option-specific precedence stated below. Long options that take values accept both `--name value` and `--name=value`. A short value-taking option accepts a separate value and, where examples below show it, a concatenated value. Unless an output mode says otherwise, every emitted record ends with the input record terminator; for ordinary text this is LF, including when the matching final input line had no LF.

## Spec 1

### Invocation, operands, and status

The search forms are:

```text
executable [OPTIONS] PATTERN [PATH ...]
executable [OPTIONS] -e PATTERN ... [PATH ...]
executable [OPTIONS] -f PATTERNFILE ... [PATH ...]
```

With no `-e/--regexp` or `-f/--file`, the first non-option operand is the pattern and remaining operands are paths. With one or more `-e` or `-f`, every non-option operand is a path and all supplied patterns are ORed. `--` ends option parsing, permitting a pattern beginning with `-`; `-e -foo` does the same. A bare `-` as a path means standard input. With no path, read standard input when it is piped; otherwise recursively search `./`. An explicit regular file is searched directly. An explicit directory is searched recursively.

Subject to the output-mode exceptions stated below, exit 0 if the selected mode succeeds and at least one selected match/result exists; exit 1 for a valid search with no selected match; exit 2 for argument, regex, traversal, I/O, decompression, or subprocess errors. A search may print valid results and still exit 2 if another requested path failed. Quiet mode may return as soon as existence/nonexistence is known. Empty files and empty input normally yield status 1. An explicitly supplied empty directory, or an explicitly supplied directory in which hidden/ignore/type/depth/size filters select no searchable file, is likewise a normal no-match: produce no stdout or stderr and exit 1.

The implicit default-directory case is different. In search mode, when no `PATH` is supplied and traversal of the implicit `./` root searches zero files, stdout is empty, stderr is exactly the following two LF-terminated lines, and status is 2. This applies both to a genuinely empty current directory and when a type or other discovery filter rejects every file:

```text
rg: No files were searched, which means ripgrep probably applied a filter you didn't expect.
Running with --debug will show why files are being skipped.
```

An empty regex is valid and matches every input record, including empty records. An empty pattern source containing no patterns yields no matches and status 1.

Unknown options, missing option values, missing required patterns, nonexistent paths, invalid types/encodings/engines/sorts/colors/sizes, and malformed regexes produce a diagnostic on stderr and status 2. Argument and regex failures detected before searching have no stdout. An unknown flag is exactly `rg: unrecognized flag FLAG` followed by LF. Running with no arguments is exactly `rg: ripgrep requires at least one pattern to execute a search` followed by LF. A missing value for any of `--encoding`, `--max-count`, `-m`, `-e`, `-f`, `--max-filesize`, `--threads`, `-r`, `--max-columns`, `--path-separator`, `--type`, or `-t` is exactly `rg: missing value for flag FLAG: missing argument for option 'FLAG'` followed by LF, preserving the spelling used. A standalone nonexistent operand `/nonexistent/path` produces no stdout and exactly `rg: /nonexistent/path: IO error for operation on /nonexistent/path: No such file or directory (os error 2)` followed by LF on stderr; other paths occupy both path positions in the same layout. Normal no-match searches produce neither stdout nor stderr. `--no-messages` suppresses file-system error messages but does not change status 2.

## Spec 2

### Terminal and non-search modes

`-h` emits concise help to stdout and exits 0. `--help` emits substantially more detailed help to stdout and exits 0. Help wins regardless of its position and does not validate a pattern or access paths. Both begin with a version line and author line of this form, where `HEXREV` is a stable nonempty lowercase hexadecimal revision identifier:

```text
ripgrep 14.1.1 (rev HEXREV)
Andrew Gallant <jamslam@gmail.com>
```

Both contain `USAGE:` and, in this order, the category headings `INPUT OPTIONS:`, `SEARCH OPTIONS:`, `FILTER OPTIONS:`, `OUTPUT OPTIONS:`, `OUTPUT MODES:`, `LOGGING OPTIONS:`, and `OTHER BEHAVIORS:`. The colon is part of each heading. Concise help has more than 50 aligned option lines that begin with exactly two ASCII spaces followed by `-`, and includes the common short/long pairs. Long help is more than three times as long, wraps prose near terminal width, documents negated switches and examples (including `rg -e -foo` or `rg -- -foo`), and contains all options in this specification. Its usage block contains both `rg [OPTIONS] --help` and `rg [OPTIONS] --version`. Its detailed option spellings include `-e PATTERN, --regexp=PATTERN` and `-f PATTERNFILE, --file=PATTERNFILE`. In this output, exactly 1,042 long-help lines begin with eight ASCII spaces, while no concise-help line does.

`-V` prints only the following single LF-terminated line to stdout, writes no stderr, and exits 0, with the same `HEXREV` rule as help:

```text
ripgrep 14.1.1 (rev HEXREV)
```

`--version` prints the following full layout to stdout, writes no stderr, and exits 0:

```text
ripgrep 14.1.1 (rev HEXREV)

features:-pcre2
simd(compile):+SSE2,-SSSE3,-AVX2
simd(runtime):+SSE2,+SSSE3,+AVX2

PCRE2 is not available in this build of ripgrep.
```

Every shown line, including the two empty lines and lowercase `features:`/`simd` labels, is present in that order. For this target PCRE2 is unavailable. `--pcre2-version` writes exactly `PCRE2 is not available in this build of ripgrep.` plus LF to stdout, writes no stderr, and exits 1. This nonzero status is how feature probes determine that look-around tests requiring PCRE2 must not run. `-P/--pcre2` therefore fails with status 2 and a diagnostic mentioning PCRE2.

`--type-list` prints the sorted built-in type table as `name: glob, glob, ...`. Its stdout is byte-for-byte the companion `type-list.txt` file (207 LF-terminated lines), with no stderr, and it exits 0 without requiring a pattern and ignores path operands. Thus `--type-list hello` also exits 0 and begins with the Ada entry. `--files [PATH ...]` lists searchable file paths rather than searching contents, honoring traversal, ignore, glob, type, hidden, symlink, depth, size, and sorting options; it needs no pattern.

## Spec 3

### Pattern sources

`-e/--regexp PATTERN` is repeatable. `-f/--file FILE` is repeatable and reads one pattern per line. Patterns from every `-e` and every file accumulate with OR semantics; neither source replaces another. A final pattern-file line need not have a newline. Pattern whitespace is literal and is not trimmed. Blank lines contribute an empty pattern and therefore select every record. A file consisting solely of newlines likewise selects every record. A completely empty pattern file contributes no pattern. Unlike a BOM in searched input, a UTF-8 BOM at the beginning of a pattern file is not stripped: it remains U+FEFF at the beginning of the first pattern. Thus a pattern file containing BOM + `error` + LF + `warning` + LF, when applied to lines `This is line 1 with error` and `This is line 2 with warning`, selects only `This is line 2 with warning`.

Invalid UTF-8 in a pattern file is an error with status 2 and no stdout. Its diagnostic identifies the 1-based pattern line and the zero-based byte offset of the first invalid byte. For a first line whose bytes begin `FF 62 61 64`, the diagnostic has this exact form, where `PATH` is the displayed pattern-file path:

```text
rg: PATH:1: found invalid UTF-8 in pattern at byte offset 0: \xFFbad (disable Unicode mode and use hex escape sequences to match arbitrary bytes in a pattern, e.g., '(?-u)\xFF')
```

The line ends in LF. For `-f-`, use `<stdin>` in place of `PATH`, not `-`. An absent relative pattern file named `nonexistent.txt` has empty stdout, exits 2, and writes exactly `rg: nonexistent.txt: No such file or directory (os error 2)` plus LF to stderr.

`-f-`/`--file -` reads patterns from stdin. In that case remaining named files can still be searched. A pattern-file operand that is absent or a directory is an error. Pattern files are data inputs and are not implicitly excluded from the search if also reached as a path. Options apply uniformly to command-line and file patterns.

## Spec 4

### Default regular-expression language

The default engine is a Unicode-aware, leftmost-first, non-overlapping regular-expression engine. It supports literals; `.`, alternation `|`, capturing and noncapturing groups; anchors `^` and `$`; ASCII/Unicode character classes and negated/ranged classes; ASCII POSIX bracket classes including `[[:alpha:]]` and `[[:digit:]]`; escapes such as `\n`, `\r`, `\t`, `\xNN`, `\u{...}`, `\d`, `\s`, `\w`, `\b`, `\B`; Unicode properties such as `\p{N}`; greedy and lazy `?`, `*`, `+`, `{n}`, `{n,}`, and `{n,m}`; and inline flags supported by Rust-style regex syntax. Matching preserves original Unicode text and performs no Unicode normalization. On input `abc\n123\n-_\n`, `[[:alpha:]]` emits only `abc` plus LF and `[[:digit:]]` emits only `123` plus LF; each exits 0 with empty stderr.

Malformed constructs fail before searching with status 2 and a diagnostic containing `regex parse error` plus a specific reason. In particular, `(` reports `unclosed group`, `foo[` reports `unclosed character class`, `foo\x` reports `invalid hexadecimal digit`, and a leading repetition such as `*foo` reports `repetition operator missing expression`. Reject unbalanced groups/classes, dangling repetition, reversed ranges, bad/incomplete hex escapes, invalid Unicode properties or inline flags, repetition ranges whose start exceeds their end, and overflowing repetition counts. The default engine rejects numbered/named backreferences, lookahead, lookbehind, and conditional expressions.

The invocations `executable '('`, `executable '\x1'`, and `executable 'a{999999999999}'` each have empty stdout, status 2, and respectively the following exact stderr blocks. Every displayed line, including the final line of each block, ends in LF:

```text
rg: regex parse error:
    (?:()
    ^
error: unclosed group
```

```text
rg: regex parse error:
    (?:\x1)
          ^
error: invalid hexadecimal digit
```

```text
rg: regex parse error:
    (?:a{999999999999})
         ^^^^^^^^^^^^
error: decimal literal invalid
```

The invocation `executable 'foo(?=bar)'` has empty stdout, status 2, and exactly this stderr (including indentation, carets, line breaks, and the wrapper displayed around the supplied pattern):

```text
rg: regex parse error:
    (?:foo(?=bar))
          ^^^
error: look-around, including look-ahead and look-behind, is not supported
```

The invocation `executable '(.)\1'` likewise has empty stdout, status 2, and exactly this stderr. In both blocks, every displayed line, including the last, ends in LF:

```text
rg: regex parse error:
    (?:(.)\1)
          ^^
error: backreferences are not supported
```

For the numbered-backreference spelling used with a named literal group, `executable '(foo)\1'` has the same status/stream behavior and exactly this stderr:

```text
rg: regex parse error:
    (?:(foo)\1)
            ^^
error: backreferences are not supported
```

The negative-lookahead invocation `executable '(?!bar)foo'` likewise produces exactly:

```text
rg: regex parse error:
    (?:(?!bar)foo)
       ^^^
error: look-around, including look-ahead and look-behind, is not supported
```

Other rejected constructs use the same four-line `rg: regex parse error:` layout and the following exact final reason lines for these observed patterns:

```text
a{3,2}         -> error: invalid repetition count range, the start must be <= the end
(?<=foo)bar    -> error: look-around, including look-ahead and look-behind, is not supported
(?<!foo)bar    -> error: look-around, including look-ahead and look-behind, is not supported
(a)?(?(1)b|c)  -> error: unrecognized flag
foo\x           -> error: invalid hexadecimal digit
foo\x1          -> error: invalid hexadecimal digit
[z-a]          -> error: invalid character class range, the start must be <= the end
(?P<123>foo)   -> error: invalid capture group character
foo(?z)bar     -> error: unrecognized flag
```

A named-backreference spelling is parsed as unsupported flag syntax rather than receiving the numbered-backreference reason. In particular, `executable '(?P<word>foo)(?P=word)'` has empty stdout, status 2, and exactly:

```text
rg: regex parse error:
    (?:(?P<word>foo)(?P=word))
                      ^
error: unrecognized flag
```

An empty capture-group name is also a parse error. `executable '(?P<>foo)'` has empty stdout, status 2, and exactly:

```text
rg: regex parse error:
    (?:(?P<>foo))
           ^
error: empty capture group name
```

For the malformed pattern `[invalid`, the complete diagnostic is:

```text
rg: regex parse error:
    (?:[invalid)
       ^
error: unclosed character class
```

Each line in these blocks, including the final line, ends in LF.

Without `-U/--multiline`, a pattern containing a newline even via the escape `\x0a` is rejected before searching. `executable '\x0a' PATH` has empty stdout, status 2, and exactly this stderr, with LF after every displayed line:

```text
rg: the literal "\n" is not allowed in a regex

Consider enabling multiline mode with the --multiline flag (or -U for short).
When multiline mode is enabled, new line characters can be matched.
```

Find successive non-overlapping matches. Thus `aa` occurs once in `aaa` for `-o` and counting. Zero-width regexes must progress safely without looping. Regex size controls `--dfa-size-limit SIZE` and `--regex-size-limit SIZE` accept unsigned decimal bytes with optional uppercase binary `K`, `M`, or `G` multipliers (1024, 1024², 1024³); malformed, empty, lowercase/unknown-suffix, or overflowing sizes are errors. For the observed invalid values, diagnostics are exactly:

```text
rg: error parsing flag --dfa-size-limit: invalid size: invalid format for size '', which should be a non-empty sequence of digits followed by an optional 'K', 'M' or 'G' suffix
rg: error parsing flag --dfa-size-limit: invalid size: invalid format for size '100X', which should be a non-empty sequence of digits followed by an optional 'K', 'M' or 'G' suffix
rg: error parsing flag --regex-size-limit: invalid size: invalid format for size 'abc', which should be a non-empty sequence of digits followed by an optional 'K', 'M' or 'G' suffix
```

The applicable single line is written to stderr with a trailing LF and status 2. Enforce the regex compilation limit with a clean size-limit error; exhausting the DFA cache may fall back to a correct slower strategy instead of changing results.

## Spec 5

### Literal, boundary, case, and inversion modes

`-F/--fixed-strings` treats every pattern literally, so metacharacters including `.[](){}*+?|^$\` lose regex meaning; invalid-looking regex text is accepted. `--no-fixed-strings` restores regex interpretation. `-w/--word-regexp` only accepts matches whose start and end are Unicode word boundaries; punctuation, underscores, and digits follow Unicode regex word rules. `-x/--line-regexp` requires a pattern to cover an entire logical record (excluding its terminator). These modes combine, e.g. fixed literal whole-line matching.

Default matching is case-sensitive. `-i/--ignore-case` enables Unicode-aware case-insensitive matching. `-s/--case-sensitive` forces sensitivity. `-S/--smart-case` is insensitive only when every pattern contains no uppercase literal; an uppercase literal makes the search sensitive. For conflicting case flags, the last wins. `-v/--invert-match` selects records with no match from any pattern; `--no-invert-match` restores normal selection. Inversion combines with case/boundary/literal modes. Inverted output has no concrete match span or column.

## Spec 6

### Multiline, dot, CRLF, and NUL records

Ordinarily patterns cannot cross line terminators and output is line-oriented. `-U/--multiline` allows a match to span multiple records and allows a pattern containing a literal newline. Dot still excludes newline unless `--multiline-dotall` is enabled. `--no-multiline-dotall` restores that exclusion. Report a multiline match as one contiguous matched region beginning at its first line; normal output contains all lines covered by it, `-o` emits the matched text, and vimgrep uses the first line/column. Avoid duplicate/overlapping reports when possible match spans overlap.

`--crlf` treats CRLF as a line terminator for anchors and strips the CR before `$`; output preserves CRLF. `--no-crlf` disables this special treatment. Mixed LF/CRLF input remains searchable. `--null-data` treats NUL rather than LF as the record terminator, writes NUL-terminated result records, and permits embedded LF inside a record. It combines with `-a`, multiline, context, files modes, and matching options. `-0/--null` is different: it places NUL after an emitted file path instead of the usual path field separator (and NUL-terminates filename-only modes); it does not change how input records are split.

## Spec 7

### Search inputs and ordinary line output

Search all explicit paths. Recursively enumerate regular files under directory paths. Reading stdin explicitly with path `-` or implicitly with no path works for both match and no-match cases. Paths discovered from the implicit current-directory root are printed without a leading `./`; for example, in a current directory containing only `sherlock`, `--null --files` writes exactly `sherlock` followed by NUL, not `./sherlock` followed by NUL. In ordinary output, a single explicitly searched file or stdin omits its path by default; multi-file/directory searches show a path. `-H/--with-filename` always shows it; `-I/--no-filename` never does. The last of these wins.

Without headings, each selected record is one output record with enabled fields in this order: path, 1-based line number, 1-based column, zero-based absolute byte offset, displayed text. Match fields use `:` by default. A directory search uses paths consistently relative to the supplied relative root/current directory, while explicit absolute paths remain absolute. Preserve special characters and Unicode in displayed paths. `--path-separator SEP` replaces path separators in displayed paths; it accepts one decoded byte.

For a single file captured through a pipe, default output is just matching lines. For multiple files the default is `path:text`. When a stdin path must be displayed, its label is `<stdin>`. Explicit `-n/--line-number` adds line numbers; `-N/--no-line-number` removes them. `--column` implies line numbers and prints the first match’s 1-based UTF-8 byte column. Tabs count as one byte/position; multibyte characters consume their encoded byte length. `-b/--byte-offset` prints the zero-based byte offset of the record/match from the beginning of the searched (or transformed) content. These fields combine in the order above.

For `--path-separator`, the four-byte arguments `\xZZ` and `\xG9` are not decoded as hex escapes and fail with status 2. Stderr consists of these two lines, substituting the supplied argument on the first:

```text
rg: error parsing flag --path-separator: A path separator must be exactly one byte, but the given separator is 4 bytes: \xZZ
In some shells on Windows '/' is automatically expanded. Use '//' instead.
```

## Spec 8

### Context records and separators

`-A N/--after-context N`, `-B N/--before-context N`, and `-C N/--context N` emit following, preceding, or both kinds of context. Short concatenated forms such as `-A1`, `-B2`, and `-C10` are accepted. Counts are nonnegative decimal integers; negative/noninteger/missing values are errors. At file boundaries output only existing records. Merge touching or overlapping context groups and never duplicate a record. Put a group separator line `--` only between disjoint groups in a file, not at the beginning/end or between merged groups. `--context-separator TEXT` changes it, and `--no-context-separator` suppresses it.

For the observed invalid values, `-A -5` writes exactly `rg: error parsing flag -A: value is not a valid number: invalid digit found in string` plus LF, while `--context abc` writes exactly `rg: error parsing flag --context: value is not a valid number: invalid digit found in string` plus LF. Each has empty stdout and exits 2.

Context records use `-` rather than `:` between enabled metadata fields. They have line numbers when line numbering is enabled but no column. `--field-match-separator TEXT` and `--field-context-separator TEXT` independently replace those field delimiters. Separator values decode `\t`, `\n`, `\r`, and `\xNN`. Match status is based on actual selected records, not context-only records.

## Spec 9

### Headings, pretty mode, and path layout

`--heading` groups ordinary results when a filename would otherwise be displayed: print the path once on its own line, subsequent result/context lines omit path, and put a blank line between nonempty file groups. `--no-heading` selects inline paths. Heading mode does not itself force filename display for a single explicitly searched file. `-p/--pretty` enables forced color, heading mode, and line numbers, but likewise does not force a filename. Thus `--pretty hello sample.txt` begins directly with the colored line-number field and has no `sample.txt` heading; adding `--with-filename` produces the heading. Explicit later options can override pretty's components.

Default output order may vary unless sorting is requested. `--sort path` produces ascending path order and `--sortr path` descending order. Accept sort keys `none`, `path`, `modified`, `accessed`, and `created`; `--sort-files` is the ascending path compatibility alias. Time sorts use the corresponding file timestamp. Sorting works for matching output and `--files`; an invalid key is status 2. `--threads N`/`-jN` accepts nonnegative integers (`0` means automatic), affects execution only, and must not change selected results; sorting may force single-thread behavior. Invalid/negative thread counts are errors. `--mmap` and `--no-mmap` select I/O strategy without changing observable matches.

## Spec 10

### Match extraction and replacement

`-o/--only-matching` emits every non-overlapping match separately, in left-to-right order, instead of its whole record. This includes zero-width matches: on the input `abc` plus LF, `-o '^|$'` emits exactly two empty LF-terminated records (two LF bytes), terminates, and exits 0. Repeat metadata for every emitted occurrence. Combining `-c/--count` with `-o/--only-matching` changes count into an occurrence count, as if `--count-matches` were selected: one line `match match match` produces `3`, and one line `foo bar foo` produces `2`. Without `-o`, `--count` counts selected records unless `--count-matches` is used. In multiline mode an extracted match may contain newlines. In invert mode there are no concrete spans, so ordinary selected records are emitted.

`-r/--replace REPLACEMENT` replaces every non-overlapping match in each selected output record; it never modifies input files. Support `$1`, `$2`, `${1}`, `$name`, and `${name}` capture expansion, `$$` for a literal dollar, empty replacements, Unicode replacement text, and multiple matches. Unmatched/unknown captures expand compatibly without crashing (normally to empty). Replacement is applied before `-o` display: when both are present, emit each replaced match portion. Metadata positions refer to original input. Nonmatching context text is unchanged. A missing replacement value is an argument error.

## Spec 11

### Count, existence, and file-list output modes

`-c/--count` emits the number of selected records per searched file, except that combining it with `-o/--only-matching` makes it count individual occurrences. `--count-matches` likewise emits the number of individual non-overlapping match occurrences; multiple occurrences on one line count separately. With one explicitly searched file, output just the decimal count; with multiple/directory inputs, use `path:count`. By default omit zero-count files. `--include-zero` includes them as `0` but overall status remains 1 if every count is zero. In invert mode count selected nonmatching records; the low-level regex-match statistic remains distinct as described later. `-m N/--max-count N` applies before count output and limits selected records per file; zero emits no selected records.

Both `--max-count abc` and `--max-count -5` have empty stdout, exit 2, and write exactly `rg: error parsing flag --max-count: value is not a valid number: invalid digit found in string` plus LF to stderr.

`-l/--files-with-matches` prints each file containing at least one selected record exactly once and may stop reading it after the first. `--files-without-match` prints each searched nonbinary file containing none. Their output is one path per line (or NUL with `--null`) with no match text. A recursively discovered NUL-containing binary file is a special case for `--files-without-match`: it makes the mode's overall status 0 even though binary suppression emits no filename. For example, in a directory where every ordinary searchable file contains `foo` and a discovered `bin.dat` contains NUL followed by `foo`, `--files-without-match foo DIR` has empty stdout/stderr and status 0; removing `bin.dat` makes the same no-result invocation status 1. `-q/--quiet` emits no normal stdout and returns 0 on a match, 1 on no match, while retaining status 2 for errors. With `--stats`, quiet suppresses match lines but the complete stats block is still printed and the full search is performed. `--stop-on-nonmatch` stops searching a file after its first nonmatching record where applicable. When incompatible output modes repeat, the later selected mode controls output.

## Spec 12

### Vimgrep output

`--vimgrep` implies filename, line number, column, no heading, and one output record per match occurrence. Its no-heading implication takes precedence regardless of option order: neither `--vimgrep --heading` nor `--heading --vimgrep` enables headings. For a relative `sample.txt` containing `hello world\nanother hello line\n`, `--vimgrep --heading hello sample.txt` emits exactly the following and exits 0 with empty stderr:

```text
sample.txt:1:1:hello world
sample.txt:2:9:another hello line
```

Its base format is:

```text
path:line:column:text
```

For two matches on one input line, emit two identical text records with different accurate columns. Columns are 1-based UTF-8 byte positions, are not visual tab stops, and are calculated from untrimmed original text. With `--byte-offset`, format `path:line:column:byte:text`. `--no-filename` removes only the path field; `--no-line-number` removes the line field while retaining the column. `--null` puts a NUL after the path. Match lines keep colon delimiters; context lines are emitted once with dash delimiters and no column. Multiline matches use their first line/column, and the vimgrep text field contains only that first physical line rather than the entire multiline match. For example, `--vimgrep -U 'hello\nworld'` on stdin containing `hello\nworld\n` emits the single physical record `<stdin>:1:1:hello` plus LF. Inverted records lack a meaningful column. Count mode still emits counts rather than match records. Explicit forced color can colorize vimgrep, but its default is plain.

## Spec 13

### Long lines, trimming, and passthrough

`--trim` removes leading Unicode whitespace from displayed match and context text but does not change matching, byte offsets, or columns and does not strip trailing content. `-M N/--max-columns N` limits display of records whose length exceeds N bytes/columns. A long selected line is replaced with `[Omitted long matching line]`. When column-bearing full-line output must represent N occurrences, use `[Omitted long line with N matches]`; for example, `--column` uses that marker once and `--vimgrep` repeats it for each occurrence. Long context uses the corresponding context omission wording. Metadata prefixes remain. Only-matching is an exception: extraction occurs before this length check, so the limit applies independently to each extracted match rather than to its source line. Consequently, `-o --max-columns=5 hit` on `xx hit yy hit zz` plus LF emits exactly `hit\nhit\n`. An extracted match that itself exceeds the limit is replaced individually with `[Omitted long matching line]`.

`--max-columns-preview` changes omission to a fixed prefix preview and appends exactly one ASCII space followed by `[... omitted end of long line]`; it does not extend the prefix to expose a later match and must not emit the entire oversized line. It emits the first N bytes/columns selected by `--max-columns`, then the marker and LF. Thus `--max-columns 10 --max-columns-preview MATCH` on `0123456789MATCHabcdefghij` plus LF emits exactly `0123456789 [... omitted end of long line]` plus LF, omitting `MATCH`. `--passthru` emits every input record in order, using normal formatting/highlighting for selected matches and context-style/plain formatting for other records. It combines with replacement, inversion, multiline, context, and color. `--line-buffered` and `--block-buffered` alter flushing only and must not alter bytes after process completion.

`--max-columns abc` has empty stdout, exits 2, and writes exactly `rg: error parsing flag --max-columns: value is not a valid number: invalid digit found in string` plus LF to stderr.

## Spec 14

### JSON Lines output

`--json` emits UTF-8 JSON objects, exactly one compact object per LF-terminated line, never ANSI color or OSC-8 hyperlinks. Each envelope has string `type` and object `data`. For each file that produces a match/context event, emit `begin`, all ordered events, then `end`; finally emit one `summary`. A no-match search emits only `summary`. Stdin’s path is `<stdin>`. Empty files produce summary only and contribute zero searched bytes; ordinary nonempty searched files contribute searches even when no match.

`begin.data` contains `path`. `match` and `context` data contain `path`, `lines`, `line_number`, `absolute_offset`, and `submatches`. `path`, `lines`, and each submatch’s `match` are data objects: use `{"text": STRING}` for valid UTF-8, otherwise `{"bytes": STANDARD_BASE64}` with padding. `line_number` is an integer unless `-N`, when it is JSON null. `absolute_offset` is the record’s zero-based file byte offset. A submatch has `match`, zero-based `start`, and exclusive `end`; offsets are bytes relative to `lines`, not Unicode scalar indexes. Include every non-overlapping occurrence. Normal context has `submatches: []`; in inverted context, an underlying regex-matching context line includes its concrete submatches. Inverted selected `match` events have no submatches.

`end.data` contains `path`, nullable/integer `binary_offset`, and per-file `stats`. `summary.data` contains `elapsed_total` and aggregate `stats`. Stats objects include elapsed timing, `searches`, `searches_with_match`, `bytes_searched`, `bytes_printed`, `matched_lines`, and `matches`. `matches` counts concrete occurrences, while `matched_lines` counts selected lines (so inverted output can have zero `matches` but positive `matched_lines`). A multiline event’s `lines.text` contains embedded LF, `line_number` is its first line, and its submatch spans the newline. `-o` does not remove full `lines` data. `-m` limits events and bytes searched. Output must always end in LF and every line must parse independently.

## Spec 15

### Human-readable statistics

`--stats` appends a blank-line-separated statistics block to stdout after normal/mode output, including on no-match. Its count labels use the following fixed plural nouns even when `N` is 1:

```text
N matches
N matched lines
N files contained matches
N files searched
N bytes printed
N bytes searched
... seconds spent searching
... seconds
```

Thus a one-match, one-file search says `1 matches`, `1 matched lines`, `1 files contained matches`, and `1 files searched`. Counts aggregate all files/stdin. `matches` is individual concrete occurrences; `matched lines` is unique selected logical lines (all lines participating in a multiline match); files and stdin count as searches. `bytes searched` is actual uncompressed/transcoded/preprocessed bytes consumed and reflects early stopping at max count or binary detection. `bytes printed` counts the complete emitted match/context records, including line-number metadata, separators, and record terminators; it does not count the statistics block or count/filename-only records. For an explicitly named file containing one 110-byte record made from `MATCH`, 104 `x` bytes, and LF, `--stats -n MATCH FILE` reports `112 bytes printed`: the additional two bytes are the `1:` prefix. Stats coexist with count, file-name modes, replacement, context, compression, preprocessor, case/boundary/invert modes, and JSON (where stats live in JSON rather than a text block). `--stats -q` still computes all stats.

## Spec 16

### Color output

`--color WHEN` accepts `never`, `auto`, `always`, or `ansi`; invalid values are errors. `never` emits no ANSI. `auto` colors only when stdout is a suitable terminal and respects conventional color-disabling environment state. `always` and `ansi` force ANSI SGR even when captured. Defaults are path magenta, line number green, match bold red. The exact default match framing is `\x1b[0m\x1b[1m\x1b[31m`, then the matched bytes, then `\x1b[0m`; these are three adjacent opening SGR sequences, not the combined `\x1b[1;31m`. A colored line number is exactly `\x1b[0m\x1b[32m`, the decimal number, `\x1b[0m`, and then the uncolored `:` or `-` delimiter. Here `\x1b` denotes the single ESC byte. Every colored match begins with the initial reset even when it occurs after uncolored text. Group-separator lines and nonmatching context/passthrough text have no SGR bytes. Context lines color metadata but do not highlight nonmatches. Only-match, replacement, heading, pretty, Unicode, and explicit vimgrep color correctly. JSON is never colored.

`--color invalid` has empty stdout, status 2, and exactly `rg: error parsing flag --color: choice 'invalid' is unrecognized` plus LF on stderr.

`--colors SPEC` is repeatable and processed in order. Syntax is `TYPE:ATTRIBUTE:VALUE`, where TYPE is `path`, `line`, `column`, or `match`; ATTRIBUTE is `fg`, `bg`, or `style`; foreground/background values may be standard names, a 0–255 palette index, or `R,G,B` components in decimal/`0xNN`; styles include `bold`, `nobold`, `intense`, `nointense`, `underline`, and `nounderline`. `TYPE:none` clears styling for that type. Later specs override the same attribute while different attributes combine. Emit proper SGR for 8/16-color, `38;5`/`48;5` palettes, and `38;2`/`48;2` truecolor. In particular, `--color always --colors match:fg:red --colors match:style:nobold` removes the default bold style without emitting a redundant SGR 22: each match is framed exactly as `\x1b[0m\x1b[31m`, the matched bytes, and `\x1b[0m`. The following observed invalid specs have empty stdout, status 2, and exactly the corresponding one-line stderr plus LF:

```text
invalid:fg:red              -> rg: error parsing flag --colors: unrecognized output type 'invalid'. Choose from: path, line, column, match.
match:invalid:red           -> rg: error parsing flag --colors: unrecognized spec type 'invalid'. Choose from: fg, bg, style, none.
match:fg:invalidcolor       -> rg: error parsing flag --colors: unrecognized color name 'invalidcolor'. Choose from: black, blue, green, red, cyan, magenta, yellow, white
match:style:invalidstyle    -> rg: error parsing flag --colors: unrecognized style attribute 'invalidstyle'. Choose from: nobold, bold, nointense, intense, nounderline, underline.
match:fg                    -> rg: error parsing flag --colors: invalid color spec format: 'match:fg'. Valid format is '(path|line|column|match):(fg|bg|style):(value)'.
match                       -> rg: error parsing flag --colors: invalid color spec format: 'match'. Valid format is '(path|line|column|match):(fg|bg|style):(value)'.
```

## Spec 17

### OSC-8 hyperlinks

Hyperlinks are enabled by `--hyperlink-format FORMAT` only when color is active and a real filename is displayed. Wrap displayed path text in OSC-8 open `ESC ] 8 ;; URL ESC \\` and close `ESC ] 8 ;; ESC \\`. Never hyperlink stdin, JSON, count-only output, or output without a filename; do hyperlink headings, vimgrep, and filename-only matching lists. URLs use canonical absolute paths (resolve symlinks) and percent-encode spaces and reserved path characters such as `&` and `#`.

Presets: `none` disables; `default` and `file` use `file://{host}{path}`; `vscode` uses `vscode://file{path}:{line}:{column}`; `vscodium` substitutes that scheme; `textmate` uses `txmt://open?url=file://{path}&line={line}&column={column}`; `macvim` uses the analogous `mvim://open?...`; `kitty` uses `file://{host}{path}#{line}`; `grep+` uses `grep+://{path}:{line}`. Missing line/column values default compatibly (line 1 and first match column where needed).

A custom format must begin with a valid `[0-9A-Za-z+.-]+:` scheme, contain `{path}`, and may contain `{host}`, `{path}`, `{line}`, `{column}`, and `{wslprefix}`; `{column}` requires `{line}`. Substitute every occurrence. On non-WSL, `wslprefix` is empty. `{{` and `}}` represent literal braces. Reject unknown/empty variables, unmatched braces, absent path, invalid scheme, and column without line with status 2 and empty stdout. For the following observed invalid formats, stderr is exactly the corresponding single line plus LF:

```text
scheme://{invalid_var}  -> rg: error parsing flag --hyperlink-format: invalid hyperlink format: invalid hyperlink format variable: 'invalid_var', choose from: path, line, column, host, wslprefix
scheme://{line}         -> rg: error parsing flag --hyperlink-format: invalid hyperlink format: the {path} variable is required in a hyperlink format
scheme://{path          -> rg: error parsing flag --hyperlink-format: invalid hyperlink format: unclosed variable: found '{' without a corresponding '}' following it
scheme://{path}:{column} -> rg: error parsing flag --hyperlink-format: invalid hyperlink format: the hyperlink format contains a {column} variable, but no {line} variable is present
scheme://}invalid       -> rg: error parsing flag --hyperlink-format: invalid hyperlink format: unopened variable: found '}' without a corresponding '{' preceding it
scheme://{path}:{}      -> rg: error parsing flag --hyperlink-format: invalid hyperlink format: invalid hyperlink format variable: '', choose from: path, line, column, host, wslprefix
*invalid*:{path}        -> rg: error parsing flag --hyperlink-format: invalid hyperlink format: the hyperlink format must start with a valid URL scheme, i.e., [0-9A-Za-z+-.]+:
{path}                  -> rg: error parsing flag --hyperlink-format: invalid hyperlink format: the hyperlink format must start with a valid URL scheme, i.e., [0-9A-Za-z+-.]+:
```

## Spec 18

### Hidden, binary, and symlink defaults

During recursive traversal, skip hidden entries (a path component beginning `.`) and symlinks by default. NUL-containing binary files are detected and their ordinary content/matches are suppressed by default rather than printed: an ordinary recursive search whose only candidate is such a binary file produces no output and exits 1, while the `--files-without-match` status exception is specified in Spec 11. `-./--hidden` includes hidden entries except ignore rules still apply. `-a/--text` treats NUL-containing data as text and emits its content. `--binary` searches binary input but, after detecting NUL, reports matching files in the form `path: binary file matches (found "\\0" byte around offset N)` (single explicit file may omit the path) rather than dumping binary bytes.

Default mode also searches an explicitly named binary file far enough to detect a match after the first NUL. If such a match exists, emit the binary-match summary rather than the raw record and exit 0. For a single explicit file containing the bytes `abc\0foo\0def`, `executable foo FILE` writes no stderr and exactly this LF-terminated stdout:

```text
binary file matches (found "\0" byte around offset 3)
```

For an explicit file or stdin, binary detection does not retract match records already emitted before the NUL is encountered. With the observed input whose first line is `The Project Gutenberg EBook of A Study In Scarlet, by Arthur Conan Doyle` and whose first detected NUL is around offset 77041, `--no-mmap -n 'Project Gutenberg EBook'` exits 0 and writes exactly this for either an explicitly named single file or stdin:

```text
1:The Project Gutenberg EBook of A Study In Scarlet, by Arthur Conan Doyle
binary file matches (found "\0" byte around offset 77041)
```

Directory searches suppress/summarize binary content compatibly. JSON records detection in `binary_offset`. Although `\xNN` is valid regex syntax, a default-mode regex containing `\x00` is rejected because binary detection makes NUL impossible to match. `executable --no-mmap 'abcdef\x00' -g hay` has empty stdout, exits 2, and writes exactly this stderr:

```text
rg: pattern contains "\0" but it is impossible to match

Consider enabling text mode with the --text flag (or -a for short). Otherwise,
binary detection is enabled and matching a NUL byte is impossible.
```

`-L/--follow` follows file and directory symlinks reached during recursive traversal; by default such discovered links are ignored. A symlink supplied directly as a path operand is followed without `-L`, whether its target is a file or a directory. In particular, an explicitly named directory symlink is traversed and its regular-file descendants are eligible for `--pre`; a successful match exits 0 rather than diagnosing the symlink itself as “not a regular file.” Detect cycles and do not hang or duplicate indefinitely. A followed broken link uses `rg: LINK: No such file or directory (os error 2)` plus LF. A detected loop uses `rg: File system loop found: LINK points to an ancestor ANCESTOR` plus LF. Each is a status-2 traversal error, while readable results from other paths are retained; multiple loops are each reported. `--one-file-system` avoids crossing filesystem boundaries. Concurrent aliases to the same file are handled safely.

## Spec 19

### Ignore files and unrestricted levels

Recursive searches honor `.rgignore`, `.ignore`, and Git ignore sources. Git rules (`.gitignore`, repository `.git/info/exclude`, global excludes) apply when inside a repository; `.ignore` and `.rgignore` apply independently. Nested ignore files are relative to their directory. Support blank/comment lines, escaped comment/negation markers, directory patterns, `/` anchoring, `**`, Windows CRLF, trailing-space rules, and later `!` whitelist overrides. Higher priority is `.rgignore`, then `.ignore`, then Git sources; deeper/later applicable rules override earlier ones. Ignore files themselves and hidden `.git` are not ordinary search targets. Explicitly named files override ignore and hidden filtering.

`--ignore-file FILE` adds rules and is repeatable; absent files error. `--ignore-file-case-insensitive` makes automatically discovered ignore-file rules case-insensitive and `--no-ignore-file-case-insensitive` restores sensitivity. It does not case-fold rules supplied by `--ignore-file`, regardless of whether the toggle appears before or after that option: an added file containing `*.TMP` does not ignore `one.tmp`. `--no-ignore` disables ignore-rule filtering. More selective switches are accepted and disable their source: `--no-ignore-dot`, `--no-ignore-vcs`, `--no-ignore-global`, `--no-ignore-parent`, `--no-ignore-files`, and `--no-ignore-exclude`; `--no-ignore-messages` suppresses ignore parsing diagnostics.

Malformed patterns in discovered ignore files do not abort traversal, but they are diagnosed unless `--no-ignore-messages` is active. For a malformed line, the diagnostic contains `PATH: line N: error parsing glob 'GLOB': REASON`, with the ignore-file path and 1-based line number. For example, a line `[invalid` produces `error parsing glob '[invalid': unclosed character class; missing ']'`; a line `[z-a]` produces `error parsing glob '[z-a]': invalid range; 'z' > 'a'`. Valid later rules, including `!` negations, remain active, readable matches are emitted, and a successful matching search exits 0. When one file has several malformed lines, diagnose them in line order.

`-u/--unrestricted` is cumulative: one use disables ignore rules; two also include hidden paths; three also enable binary searching in the same manner as `--binary`, not text dumping. Compact `-uu` and `-uuu` work. Thus for a discovered file named `binary` containing `x\0\n`, `-uuu x` emits `binary: binary file matches (found "\0" byte around offset 1)` plus LF and does not emit the raw NUL; an explicit later `-a/--text` does emit the raw content. Explicit later enabling/disabling options resolve normally.

## Spec 20

### Glob filtering

`-g/--glob GLOB` is repeatable and filters traversal paths; `--iglob` adds case-insensitive globs and `--glob-case-insensitive` makes subsequent/active globs case-insensitive. A leading unescaped `!` is exclusion. Positive globs are a union; exclusions take precedence. Glob selection takes precedence over type selection where the two would conflict. Globs work in search and `--files` modes and across nested directories.

Support `*` within a component, `?`, `**` across components, bracket classes/ranges/negation, escaped metacharacters, brace alternatives such as `*.{rs,py,c}`, leading `/` anchoring, directory-only patterns, Unicode names, and literal spaces/special characters. `*` does not cross path separators; `**/*.txt` covers all depths. Empty glob behavior is compatible with matching all paths. Reject malformed classes/ranges or overly invalid glob syntax with status 2 rather than hanging. When multiple positive and negative patterns occur, inclusion by any positive is still vetoed by a matching negative.

The malformed glob `[` has empty stdout, exits 2, and writes exactly `rg: error parsing glob '[': unclosed character class; missing ']'` plus LF. The malformed reversed-range glob `[z-a]` likewise has empty stdout, exits 2, and writes exactly `rg: error parsing glob '[z-a]': invalid range; 'z' > 'a'` plus LF. Glob matching is case-sensitive by default: if a directory contains only `README.md` and `readme.MD`, then `--glob readme.md readme DIR` selects no file, emits nothing on either stream, and exits 1.

## Spec 21

### File types

`-t/--type TYPE` selects a named type and is repeatable as a union. `-T/--type-not TYPE` excludes types and is repeatable; exclusions override selections. Compact `-trust`, `-Tpython`, etc. work. Type names are case-sensitive. With a pattern present, `--type nonexistent x` exits 2 with empty stdout and exactly `rg: unrecognized file type: nonexistent` plus LF on stderr; other unknown names replace `nonexistent` in that layout. `all` selects all recognized types; `--type-not=all` leaves only unrecognized files. Type filtering applies to recursive discovery and `--files`, counts, and filename modes, but never rejects an explicitly named regular-file operand.

Required built-ins include: `rust` → `*.rs`; `py` and `python` → `*.py` and `*.pyi`; `ada` → `*.adb` and `*.ads`; `txt` → `*.txt`; `c` → C sources and headers including `*.c` and `*.h`; `cpp` → C++ extensions and headers but not plain `*.c`; and the other text/source types shown by `--type-list`. Multiple types may overlap.

`--type-add 'name:glob'` adds a glob, accumulating across repeats. Type mutations are applied before terminal `--type-list` output: `--type-add 'foo:*.foo' --type-list` exits 0 and includes the sorted table line `foo: *.foo`. This interaction overrides the unmodified built-in-table byte identity stated in Spec 2. `name:include:type1,type2` includes existing definitions. `--type-clear name` removes existing globs so the name can be redefined. Reject a missing name or glob, malformed definition syntax, and unknown includes. Both malformed syntax such as `--type-add invalid` and an empty glob such as `--type-add name:` have empty stdout, status 2, and exactly `rg: invalid definition (format is type:glob, e.g., html:*.html)` plus LF on stderr.

Glob syntax inside an added type is validated only if that type is subsequently selected or otherwise compiled. Merely defining an unused malformed glob succeeds: `--type-add 'bad:[unclosed' content DIR` searches normally, and `--files --type-add 'mine:[z-a]'` performs an ordinary file listing (or exits 1 silently in an empty directory). Selecting the latter with `-tmine` then fails with status 2 and `rg: error parsing glob '[z-a]': invalid range; 'z' > 'a'` plus LF. This lazy type-definition behavior does not change Spec 20's immediate validation of a `-g/--glob` argument. If traversal of an explicitly supplied directory finds no searchable files after type or other discovery filters, emit no diagnostic and exit 1, just as when searchable files contain no match. Thus redefining `py` as `*.notpy` and selecting it in an explicitly supplied directory containing only `test.py` exits 1 silently. In contrast, `-t java MATCH` with no path in a current directory containing no Java file searches zero files and uses the status-2 diagnostic in Spec 1.

## Spec 22

### Depth and size traversal controls

`-d N/--max-depth N` accepts a nonnegative integer and limits recursive descent relative to each root. The compatibility spelling `--maxdepth N` is an exact alias and is not an unknown option; for example, `--maxdepth 2 far` successfully finds a matching file directly under a child directory while excluding the next deeper level. At depth 0 search only an explicit file/no descendants; at depth 1 include files directly under a directory root but not files below its child directories. It combines with symlinks and types without off-by-one traversal. Invalid/negative values are errors. In particular, `--max-depth -1` has empty stdout, exits 2, and writes exactly `rg: error parsing flag --max-depth: value is not a valid number: invalid digit found in string` plus LF. Unlimited traversal supports deeply nested directories without recursion failure.

`--max-filesize SIZE` skips files larger than SIZE when they are discovered during recursive traversal; explicitly named regular-file operands bypass this discovery filter. SIZE is unsigned decimal with optional uppercase binary `K`, `M`, or `G`; plain numbers are bytes. Reject empty values, nondigit prefixes, lowercase/unknown suffixes, and arithmetic overflow. The exact one-line stderr diagnostics (each followed by LF, with status 2) for the observed values are:

```text
rg: error parsing flag --max-filesize: invalid size: invalid format for size '', which should be a non-empty sequence of digits followed by an optional 'K', 'M' or 'G' suffix
rg: error parsing flag --max-filesize: invalid size: invalid format for size 'abc', which should be a non-empty sequence of digits followed by an optional 'K', 'M' or 'G' suffix
rg: error parsing flag --max-filesize: invalid size: invalid format for size 'invalid', which should be a non-empty sequence of digits followed by an optional 'K', 'M' or 'G' suffix
rg: error parsing flag --max-filesize: invalid size: invalid format for size '123T', which should be a non-empty sequence of digits followed by an optional 'K', 'M' or 'G' suffix
rg: error parsing flag --max-filesize: invalid size: invalid integer found in size '99999999999999999999G': number too large to fit in target type
rg: error parsing flag --max-filesize: invalid size: size too big in '18446744073709551615G'
```

Boundary-sized files are handled consistently. Filtering every file out beneath an explicitly supplied directory root is a normal no-match with empty stdout/stderr and status 1; a zero-file implicit-root search uses the behavior in Spec 1.

## Spec 23

### Encodings and Unicode bytes

Patterns and normal output are UTF-8. By default, automatically detect and strip UTF-8 BOM and transcode UTF-16LE/UTF-16BE when a BOM is present. Do not auto-detect BOM-less UTF-16 or UTF-32. `-E/--encoding NAME` transcodes the named input to UTF-8 for searching/output; support aliases for `ascii`, `utf-8`, BOM-aware `utf-16`, `utf-16le`, `utf-16be`, `shift_jis`/`sjis`, `euc-jp`/`eucjp`, `iso-8859-1`, `windows-1252`, and `big5`. When BOM detection is enabled, a BOM’s encoding takes precedence over an explicit conflicting encoding. `-E none`/`--encoding none` disables transcoding and BOM detection, so a leading UTF-8 BOM remains in the searched bytes. In contrast, `--no-encoding` negates an earlier explicit encoding choice and restores the default automatic behavior; it does not select the `none` encoding. Therefore `--no-encoding -o '^hit'` on a file containing UTF-8 BOM + `hit` + LF exits 0 and emits exactly `hit` plus LF, while `-E none -o '^hit'` on the same file exits 1 with empty output. The last option wins. Compact forms such as `-Esjis` work. `--encoding nonexistent` exits 2 with empty stdout and exactly `rg: error parsing flag --encoding: grep config error: unknown encoding: nonexistent` plus LF on stderr.

Case, regex classes, context, line numbers, count, and replacement operate on decoded text. `--unicode` explicitly enables the default Unicode regex mode; `--no-unicode` switches classes, word boundaries, and case folding to byte/ASCII-oriented behavior and permits regex matching without Unicode guarantees. The last toggle wins. Output preserves decoded Unicode. Invalid UTF-8 in searched data must not crash; byte-capable normal search can still find ASCII subsequences, while JSON uses base64 data objects. Encoding does not disable binary NUL detection; `--text` is still required to dump NUL-containing data. Byte offsets and searched-byte statistics refer consistently to the searched/transcoded stream as the relevant mode requires.

## Spec 24

### Compressed inputs

`-z/--search-zip` transparently decompresses files recognized by extension as gzip (`.gz`, `.tgz`), bzip2 (`.bz2`, `.tbz2`), xz (`.xz`, `.txz`), and LZMA (`.lzma`); common brotli/lz4/zstd formats may also be accepted. The corresponding decompressor commands are harness-provided and available. Search decompressed bytes with the same regex, encoding, binary, context, count, only-match, replacement, filename, case, word, stats, and max-count semantics. Report the compressed file’s path, but line/byte positions and `bytes searched` refer to decompressed content. A tarball-like suffix is decompressed as a compressed byte stream, not traversed as an archive.

Without `-z`, or after later `--no-search-zip`, compressed content is not transparently searched. A valid empty compressed file yields no match/status 1. Multi-member gzip is read fully. Recognition is extension based; compressed bytes under an unrelated extension are not automatically decoded. Corrupt/truncated streams, unavailable/failing decompressors, and broken links yield status 2 with stderr diagnostics while other requested files may still produce output.

When a decompressor emits an error for `PATH`, stderr is framed exactly as follows: the first line is `rg: PATH: ` (including the space after the colon), the second line is exactly 79 hyphens, then the decompressor's stderr bytes, then another line of exactly 79 hyphens. Every line, including the final separator, ends in LF. For example, a corrupt `corrupted.gz` for which gzip reports `gzip: corrupted.gz: invalid compressed data--format violated` produces:

```text
rg: corrupted.gz: 
-------------------------------------------------------------------------------
gzip: corrupted.gz: invalid compressed data--format violated
-------------------------------------------------------------------------------
```

The same framing is used for a one-line `not in gzip format` error, a truncated gzip `unexpected end of file` error, the potentially multi-line bzip2 corrupt/truncated diagnostic, and xz `Compressed data is corrupt` or `Unexpected end of input` diagnostics. The decompressor text is preserved between the separators rather than replaced with a synthesized `decompression failed` line. For an explicitly named broken symlink `PATH` ending in `.gz`, `-z needle PATH` emits no stdout and reports `rg: PATH: IO error for operation on PATH: No such file or directory (os error 2)` plus LF. Symlink traversal rules still apply. `--search-zip` takes precedence over and disables `--pre` processing.

## Spec 25

### Preprocessors

`--pre COMMAND` runs an environment-provided command separately for each eligible named file and searches its stdout in place of the file. The file path is appended as an argument and its contents are also available on the child’s stdin, allowing either interface. Interpret COMMAND compatibly as a command line. An empty command or later `--no-pre` disables it. Do not preprocess the main search stdin. Preprocessor output determines line numbers, offsets, matching, binary handling, output, and stats; the displayed path remains the original file.

`--pre-glob GLOB` is repeatable and restricts preprocessing, with the same positive-union/`!`-exclusion behavior as globs; nonselected files are searched directly. Preprocessors can add, remove, transform, or generate large amounts of data and must be drained without deadlock. They combine with JSON, multiline, context, counts, max columns, only-match, filename modes, replacement, case/invert, stats, mmap switches, and followed symlinks. A child that cannot start produces `preprocessor command could not start`; nonzero child status produces `preprocessor command failed` and includes child stderr; both exit 2. Empty child output is a normal no-match. `-z` overrides preprocessing.

## Spec 26

### Configuration environment

If `RIPGREP_CONFIG_PATH` is unset or empty, load nothing. Otherwise read the named UTF-8 file. Each physical line is exactly one argument after trimming surrounding whitespace and CR; there is no shell tokenization or quote processing. Ignore blank lines and lines whose first nonspace character is `#`. Thus `--max-count=1` is valid while one line `--max-count 1` is a single unknown flag. Long lines and Unicode comments are accepted. A line `--` followed by later positional lines may supply the pattern.

Prepend config arguments to command-line arguments, so later CLI options override earlier config options. `--no-config` on the CLI suppresses loading entirely. Relative config paths resolve from process cwd; absolute paths work. If the environment path is absent, unreadable, or a directory, print `failed to read the file specified in RIPGREP_CONFIG_PATH` plus path/system reason, then continue the requested command with defaults rather than failing solely for that reason. Invalid arguments successfully read from a config file are ordinary argument errors.

## Spec 27

### Generated Bash completion

`--generate complete-bash` and `--generate=complete-bash` require no pattern, write only a Bash completion program to stdout, and exit 0. The bytes must equal the companion normative file `completion-bash.txt` in this specification directory. That file defines `_rg()`, initializes `COMPREPLY=()`, handles value-taking options with appropriate choices/file completion, treats short and long options separately, includes all options (including negations, help, and version), and registers `complete -F _rg ... rg`.

## Spec 28

### Generated Fish completion

`--generate complete-fish` and its equals form write exactly `completion-fish.txt` and exit 0. It consists of `complete -c rg ...` declarations for all short/long/negated options, uses `__fish_contains_opt` for opposite switches, distinguishes file values from ordinary values, and embeds the full encoding choices including the comment `# This is impossible to read, but these encodings rarely if ever change`, `{{,us-}ascii,arabic,chinese,cyrillic,greek{,8},hebrew,korean}`, and `utf{,-}8 utf-16{,be,le} unicode-1-1-utf-8`.

## Spec 29

### Generated PowerShell completion

`--generate complete-powershell` and its equals form write exactly `completion-powershell.txt` and exit 0. It imports `System.Management.Automation` and `.Language`, registers a native argument completer for command `rg`, declares `param($wordToComplete, $commandAst, $cursorPosition)`, and creates `CompletionResult` entries for every short, long, and negated option with correctly escaped descriptions.

## Spec 30

### Generated Zsh completion

`--generate complete-zsh` and its equals form write exactly `completion-zsh.txt` and exit 0. It defines `_rg()` and `_rg_encodings()`, contains documented option specifications such as `{-i,--ignore-case}` and `{-E+,--encoding=}`, embeds the full encoding alternatives (no `!ENCODINGS!` placeholder), and includes all major/negated/help/version options.

## Spec 31

### Man-page generation

`--generate man`/`--generate=man` writes a deterministic roff manual larger than 1000 bytes to stdout, no stderr or files, and exits 0. Its first line has the form `.TH RG 1 YYYY-MM-DD "14.1.1 (rev HEXREV)" "User Commands"`, with an ISO date and the same version suffix as `--version`. Include `.SH` sections `NAME`, `SYNOPSIS`, `DESCRIPTION`, `REGEX SYNTAX`, `POSITIONAL ARGUMENTS`, `OPTIONS`, `EXIT STATUS`, `VERSION`, `HOMEPAGE`, and `AUTHORS`. NAME contains `rg \-` and “recursively search.” SYNOPSIS uses `\fBrg\fP` and covers PATTERN, PATH, files, type-list, help, and version forms.

OPTIONS is substantial and divided using `.SS` into the same input/search/filter/output/output-mode/logging categories. Format paired flags like `\fB\-i\fP, \fB\-\-ignore-case\fP`, values with italic `\fI...\fP`, descriptions inside `.RS 4`/`.RE`, escaped option-name hyphens/backslashes, bold cross-references, negation notes, and more than five balanced `.EX`/`.EE` examples. The generated manual contains more than 50 standalone `.sp` directive lines separating option descriptions and their paragraphs. Its discussion of the pattern-file stdin sentinel contains the literal roff `\fB-\fP`, so the OPTIONS section contains the byte substring `\fB-` in addition to escaped option flags.

Long-only flags are rendered without inventing a short form; in particular, the manual contains the exact roff `\fB\-\-auto-hybrid-regex\fP`. It documents preprocessing with the entry `\fB\-\-pre\fP=\fICOMMAND\fP`, followed by `.RS 4`, a multiline description, standalone `.sp` paragraph breaks, and `.RE`. It documents all common flags and contains no unreplaced `!!...!!` markers. VERSION agrees with `--version`’s first-line version suffix.

## Spec 32

### Generate-mode validation and precedence

`--generate KIND` accepts exactly `man`, `complete-bash`, `complete-fish`, `complete-powershell`, and `complete-zsh`. An absent or unknown value exits 2. Specifically, `complete-unknown` and `foobar` have empty stdout and respectively write exactly `rg: error parsing flag --generate: choice 'complete-unknown' is unrecognized` and `rg: error parsing flag --generate: choice 'foobar' is unrecognized`, each plus LF, to stderr. Generation is standalone and requires no pattern. Help and version modes terminate successfully without searching; help wins even when other would-be operands are invalid. `--type-list` likewise ignores path operands. `--files` is operational rather than a pattern search and treats its operands as roots.

## Spec 33

### Debug and trace diagnostics

`--debug` writes at least five diagnostic lines to stderr for an ordinary valid search while leaving search results on stdout. Lines begin `rg: DEBUG|`, followed by a nonempty Rust target/module field, then a source location containing `.rs:NUMBER:` and a message. A DEBUG target is not required to contain `::`; in particular, the glob construction line begins `rg: DEBUG|globset|`, has a Rust source location, and contains `built glob set`. No-match and quiet searches still emit the normal debug sequence, and quiet suppresses stdout only. A missing-pattern invocation is an early exception: `--debug` by itself exits 2 and emits exactly one DEBUG line, beginning `rg: DEBUG|rg::flags::parse|`, followed by the ordinary `rg: ripgrep requires at least one pattern to execute a search` error line.

`--trace` is a strict superset: it includes DEBUG plus at least three lines beginning `rg: TRACE|`, and more diagnostic lines than debug for the same search. Every TRACE line's target/module field contains `::`; for an ordinary literal search, the first TRACE target is `grep_regex::matcher`. Include per-file paths, a `binary detection: BinaryDetection` message per searched file, search-strategy messages containing `searching via memory map` and `searching via slice-by-line strategy`, and regex messages containing `grep_regex` and `final regex:`. Debug and trace obey ordinary left-to-right precedence: the later logging flag wins. Thus `--trace --debug x` emits DEBUG diagnostics and no TRACE line, while `--debug --trace x` emits TRACE lines. `--no-ignore-messages` concerns ignore diagnostics, while `--no-messages` concerns filesystem errors; neither suppresses explicitly requested debug/trace logging.

## Spec 34

### Errors while walking

Traversal must tolerate empty directories, many files/directories, deep trees, special/Unicode names, files disappearing during traversal, unreadable entries, invalid UTF-8 names/rules, and malformed ignore files without crashing or hanging. Report material path errors to stderr and use status 2 while retaining results from readable paths. `--no-messages` suppresses those messages. An explicitly supplied empty directory, hidden-only directory, directory containing only hidden `.git` content, or directory with no searchable file after filters is not a traversal error: it produces no stdout/stderr and exits 1. When that same zero-files condition occurs while searching the implicit `./` root because no path was supplied, use the status-2 diagnostic in Spec 1. An actually searched collection with zero matches exits 1.

Never recursively follow symlink loops. Respect depth at symlink boundaries and filesystem boundaries. Invalid ignore patterns are diagnosed as specified in Spec 19 while remaining valid patterns continue to work. Comments/blank lines/CRLF/large rules and rule negations remain functional even alongside an invalid rule. Permissions can differ when running as root; observable behavior must be based on actual open success rather than mode bits alone.

## Spec 35

### Output robustness and byte accounting

Handle files with no final newline, only newlines, empty records, very long records (well beyond 100 KiB), thousands of matches, very large line numbers, and arbitrary UTF-8 without truncation unless `--max-columns` requests it. Add an output terminator for a selected final unterminated record. Do not add phantom records. Match occurrences are non-overlapping and left-to-right.

Line numbers are 1-based. Absolute byte offsets are 0-based and include all preceding bytes and terminators. Columns are 1-based byte positions within the record. JSON submatch offsets are 0-based half-open byte offsets. All remain accurate with UTF-8, BOMs, CRLF, NUL records, preprocessing, compression, only-matching, trimming, headings, context, replacement, and multiple occurrences. No option may accidentally send diagnostics into stdout formats intended for machine parsing.

## Spec 36

### Option parsing details

Recognize clustered boolean short flags such as `-in`, concatenated value flags such as `-m2`, `-M26`, `-j1`, `-A1`, `-Esjis`, `-trust`, and `-Tpython`, plus separate and equals long values. A dash-prefixed token is parsed as options unless protected by `-e` or `--`; for example `-foo` is parsed as `-f` with value `oo`, so it can fail opening that pattern file. A lone path operand with no explicit pattern is treated as the positional pattern; it is not inferred to be a path.

All integer options validate nonnegative decimal values and reject embedded signs/nondigits where required. For `--max-count not-an-int`, `--max-count=not-an-int`, and `--max-count -1`, stderr is exactly `rg: error parsing flag --max-count: value is not a valid number: invalid digit found in string` plus LF; for `-m not-an-int`, the same diagnostic uses `-m` in place of `--max-count`. Each exits 2 with empty stdout. Value-taking options never silently consume nothing, using the missing-value diagnostic fixed in Spec 1. Specifically validate values for max count, threads, context counts, max depth, max columns, max filesize, encoding, engine, generate, type, sort, separators, colors, pattern files, and replacement. `--engine` accepts `default` and `auto`; `pcre2` fails because this build lacks PCRE2. `--auto-hybrid-regex` is accepted as auto-engine compatibility and `--no-auto-hybrid-regex` restores default; ordinary patterns still search correctly.

## Spec 37

### Built-in filtering interactions

Apply discovery filters before opening/searching content: hidden/ignore/symlink, then glob/type, depth/filesystem, and size, with explicit-file overrides described above. A positive `-g` can select a different extension than `-t`; explicit glob intent wins. Type exclusions and negative globs remain vetoes. `--hidden` does not imply `--no-ignore`; `--no-ignore` does not imply hidden or text. `--text` does not imply hidden/ignore. Repeated `-u` is precisely the combined shortcut, not a separate filtering model.

All relevant filters also apply to `--files`, `-l`, `--files-without-match`, counts, sorted searches, compressed discovery, preprocessing eligibility, and recursive JSON. In ordinary search mode, if no path was supplied and these filters leave zero files beneath the implicit `./` root, emit the exact diagnostic and status specified in Spec 1. Filter configuration must not alter direct stdin searching. Ignore and glob matching uses `/`-style logical path components even when display separators are customized.

## Spec 38

### Output-mode interactions and precedence

Mode options compose where meaningful: context with heading/vimgrep/replacement/trim; count and filename modes with types/globs/compression; stats with every search mode; JSON with search filters/options; color/hyperlinks only with human output. Machine modes suppress incompatible decoration. `--json` uses its event stream regardless of heading/vimgrep field layout. Count modes suppress match/context text. Filename-only modes suppress content. Quiet suppresses all normal output but not requested text stats or diagnostics. Later contradictory toggles restore their named setting except for hard mode implications stated elsewhere, including `--vimgrep` suppressing headings.

Max count is per file, not global, and counts selected records (or occurrences as the active output mode requires). Context after the final admitted match may still be emitted. With multiple patterns, a line is selected once but every non-overlapping concrete match is represented for only-matching, count-matches, vimgrep, JSON submatches, replacement, and stats. Overlapping alternatives follow leftmost-first regex behavior.

## Spec 39

### Required built-in data and environment independence

The executable must carry all option metadata, help text, built-in file-type mappings, encoding labels, generated manual content, and completion behavior needed above. It must not read the repository’s README/GUIDE, test files, golden files, or network at runtime. The companion completion and type-list files beside this document are normative build-time data that may be embedded in the executable; they will not exist beside the evaluated executable. Hostname and current working directory used in hyperlinks are obtained at runtime. Locale, terminal variables, `NO_COLOR`, `RG_COLORS`, and `RIPGREP_CONFIG_PATH` may vary and should affect only the documented areas.

External commands explicitly named by a user through `--pre`, and standard decompression commands selected by `--search-zip`, are assumed supplied by the execution environment. Do not implement or claim the behavior of those commands; invoke them and consume their streams/statuses as specified.

## Spec 40

### Performance and safety envelope

Complete ordinary searches within a few seconds for hundreds of small files, 100–400 KiB lines/files, deep directory structures, compressed samples, and preprocessors emitting at least hundreds of lines. Stream or bound buffering sufficiently to avoid deadlock on child output. Avoid exponential regex behavior in the default engine, recursion-stack failure, integer overflow, invalid-byte decoding crashes, and symlink cycles. `--threads`, mmap selection, sorting, debug logging, JSON serialization, color, and hyperlinks must not change match correctness.

Do not modify searched files or directories. Aside from processes explicitly authorized through `--pre` and decompression, searching is read-only. Generated modes write only stdout. Errors are deterministic enough for the required phrases and exact structured formats, and the process must always terminate with the status rules in Spec 1.
