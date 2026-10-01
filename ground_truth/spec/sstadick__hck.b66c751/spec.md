# Specification for `executable`

The required artifact is a directly runnable command-line program named exactly `executable`. It is a byte-preserving, line-oriented field extractor in the style of `cut`, with regex delimiters, field reordering, header-based selection, and optional compression. Unless an error is described, successful invocations exit with status 0 and write no diagnostics.

## Spec 1

The command-line shape is:

```text
executable [OPTIONS] [INPUT]...
```

It must accept options before, after, or between positional inputs. With no `INPUT`, read standard input. A positional `-` also means standard input and may appear among file paths; process all positional sources once and in their given order. If one or more file paths are supplied and `-` is not among them, do not also consume standard input. A zero-byte input produces zero output. Multiple inputs are concatenated logically without banners or added separators.

The supported option spellings are:

```text
-o, --output <OUTPUT>
-d, --delimiter <DELIMITER>
-L, --delim-is-literal
-I, --use-input-delim
-D, --output-delimiter <OUTPUT_DELIMITER>
-f, --fields <FIELDS>
-e, --exclude <EXCLUDE>
-E, --exclude-header <EXCLUDE_HEADER>
-F, --header-field <HEADER_FIELD>
-r, --header-is-regex
-z, --try-decompress
-Z, --try-compress
-t, --compression-threads <COMPRESSION_THREADS>
-l, --compression-level <COMPRESSION_LEVEL>
    --no-mmap
    --crlf
-h, --help
-V, --version
```

Field and delimiter options must support the exercised separate and concatenated forms, including `-f 1`, `-f1`, `-f=1`, `--fields 1`, `--fields=1`, `-d,`, and `-Ld,`. Other value options support the ordinary separated form. `-F` and `-E` are repeatable; `-f` is not repeatable.

## Spec 2

`-h` and `--help` print help to standard output. Both forms include the exact synopsis `Usage: executable [OPTIONS] [INPUT]...`, followed by `Arguments:` and `Options:` sections, the `[INPUT]...` placeholder, and text saying input files default to stdin. Every option pair and value placeholder shown in Spec 1 must appear in long help exactly as written there. Long help additionally contains headings `## Selection by headers` and `## Ordering of outputs`, mentions the “output delimiter” and refers to `` `-D` ``, and is longer than short help. In the `Arguments:` section, the positional placeholder and its description occupy the same line, exactly as `[INPUT]...  Input files to parse, defaults to stdin`; the description has no final period.

Help only takes precedence over arguments that follow it. Thus `-h --definitely-invalid` and `--help --definitely-invalid` print the corresponding help and exit 0, but an invalid option encountered first is decisive: both `--definitely-invalid -h` and `--definitely-invalid --help` exit 2, write no stdout, and report `error: unexpected argument '--definitely-invalid' found` on stderr.

`-V` and `--version` print a newline-terminated, nonempty version string to standard output, with no stderr, matching `hck` followed by whitespace and a non-whitespace version identifier (for example `hck 1.2.3` or `hck git:abcdef`). Exact version text is not prescribed.

## Spec 3

Process input as raw bytes, one record at a time. The normal record terminator is LF (`0A`). Remove the terminator before splitting and append one output terminator after processing every input record, including an empty record. Process a final unterminated input record and still terminate its output. Thus `abc` with `-f1` produces `abc\n`, while `\n\n\n` produces three output newlines.

Do not require UTF-8 for field data. Preserve arbitrary bytes, including NUL and invalid UTF-8, exactly when they are part of selected fields. Unicode text and Unicode delimiters must also round-trip without corruption. Do not trim, normalize, quote, escape, or otherwise alter field contents.

With `--crlf`, use CRLF as the input and output record terminator: remove the whole `\r\n` before field processing and emit `\r\n` for each output record. This must preserve byte-for-byte CRLF output on CRLF input. Without `--crlf`, LF input produces LF output; CRLF data must still be handled without failure, and a trailing CR must not contaminate fields that precede it.

## Spec 4

The input delimiter defaults to the regex `\s+`. Consequently runs of spaces, tabs, or mixed whitespace are one separator, and output defaults to tab-separated fields. `-d DELIMITER` replaces the input delimiter while remaining regex syntax unless `-L` is present. Regex splitting is unanchored and global and must support the constructs exercised by these examples: character classes (`[,;]`, `[|-]`, `[0-9]+`, `[[:space:]]+`), alternation, grouping, anchors, `.`, `+`, `{3}`, inline flags such as `(?i)`, and escapes such as `\s`, `\d`, `\t`, and `\.`. Capturing groups do not become fields; only the complete regex match is discarded as the separator.

Examples, with the default tab output:

```text
input a,b;c and -d '[,;]'       -> a<TAB>b<TAB>c
input a,,,b and -d ','          -> a<TAB><TAB><TAB>b
input a,,,b and -d ',+'         -> a<TAB>b
input a  b   c and -d ' +'      -> a<TAB>b<TAB>c
```

An invalid delimiter regex is a runtime error (status 1), reported on stderr with a regex parse diagnostic, the pattern, a caret location, and the underlying reason. For the two directly exercised malformed patterns, the complete diagnostics are:

```text
Error: regex parse error:
    [
    ^
error: unclosed character class
```

and, equivalently for `(`, the final reason is `error: unclosed group`. Degenerate regexes that can match empty text, such as `.*`, must terminate promptly rather than loop forever; selecting field 1 in such a case produces a blank output record.

## Spec 5

With `-L`, `DELIMITER` is one literal byte string rather than regex syntax. It may be a single byte, multiple bytes, a regex metacharacter such as `|`, `.`, or `.*`, spaces, a tab, backslash, or a multibyte Unicode string. Match and discard the entire literal substring. Adjacent delimiters create empty fields; a trailing delimiter creates a final empty field. A delimiter longer than a line or otherwise absent makes the entire line field 1.

Command-line escape notation used for delimiters is decoded where applicable: in particular the two characters `\t` denote a tab for literal input splitting, and `\n` denotes a newline. An actual tab supplied as the argument behaves identically. A literal backslash argument can itself be used as the delimiter.

Empty fields in the middle or at the end are real selectable fields and are represented by adjacent or trailing output separators. A leading delimiter likewise creates an empty field 1, so selecting fields 2 and 4 from `,a,b,c` produces `a<TAB>c`.

There is one legacy fast-path behavior that is externally observable: on the optimized single-byte literal-delimiter path, selecting the leading empty field 1 of a record that begins with the delimiter terminates with status 101, no stdout, and a panic containing `attempted to index slice up to maximum usize`. This applies both when all fields are selected implicitly and when field 1 is explicitly requested. In particular, `-L -d , -f 1,2,4,5` on `,a,b,\n` has that result. The nonexistent field 5 is not the cause: on the same record, `-f 2,4,5` succeeds and emits `a<TAB>\n`. Likewise, the explicit `-f 2,4` case above succeeds because it does not request field 1.

## Spec 6

`-f FIELDS` selects fields by one-based index. `FIELDS` is a comma-separated ordered list whose items are:

- `N`: field N;
- `N-M`: inclusive closed range;
- `-M`: fields 1 through M;
- `N-`: field N through the end of that particular record.

Leading zeroes are allowed (`01` means 1). A closed one-element range such as `2-2` selects field 2. Items and range endpoints are expanded in the order written. If `-f` is absent, behave as `-f 1-`, selecting all fields.

Examples on `a b c d e f` are:

```text
-f 2                 -> b
-f 2-4               -> b<TAB>c<TAB>d
-f -3                -> a<TAB>b<TAB>c
-f 3-                -> c<TAB>d<TAB>e<TAB>f
-f 4-,1-3            -> d<TAB>e<TAB>f<TAB>a<TAB>b<TAB>c
-f 1-2,4,6-          -> a<TAB>b<TAB>d<TAB>f
```

## Spec 7

Field order is significant: never sort an ordinary selection numerically. Expand each requested item in place and preserve the first requested position of each value. Repeated individual fields and overlaps are normally emitted only once. For example:

```text
-f 3,1,2             -> fields 3,1,2
-f 3,3,1,2           -> fields 3,1,2
-f 3,1,3             -> fields 3,1
-f 1-3,2-4           -> fields 1,2,3,4
-f 4-,1,5-8          -> fields 4 through end, then field 1
```

The optimized single-byte literal-delimiter path has three tested legacy overlap quirks. They are exceptions to the normal deduplication rule and must be preserved:

```text
-L with -f 2,2,2             -> field 2 twice
-L with -f 1-2,2-3,3-4       -> fields 1,2,3,3,4
-L with -f 1,2-,4             -> fields 1,2,3,4,4 on a four-field row
```

These exceptions do not apply to the regex/default-delimiter path, where `-f 2,2,2` emits field 2 once. Other directly overlapping pairs still merge normally: `-f 1-3,2-4` emits fields 1 through 4 once, and `-f 1,2,3,4,1,2` emits fields 1 through 4 once even in literal mode.

Exclusion must not disturb this retained ordering. As concrete combined examples, selecting `4-6,1-3` and excluding `3-5` yields `6,1,2`, and selecting `5,3,1` while excluding `3` yields `5,1`.

## Spec 8

Evaluate selections against each record’s actual width; ragged rows are valid. Omit requested indices that do not exist in a row—do not pad them and do not error. Ranges extending beyond the row are clipped. Thus selecting `3-10` from a four-field row emits fields 3 and 4, and `5,100,2` from a ten-field row emits fields 5 then 2.

If a valid, nonempty selection has no existing field in a record, emit an empty record terminator for that input record. For example two lines with only one field each and `-f 2-` produce `\n\n`; selecting field 100 from four input records produces four blank output records. An empty input stream still produces no bytes. Lines containing no delimiter have exactly one field. Empty input lines and whitespace-only lines preserve their line-for-line positions as blank output records.

The program is not CSV-aware: quotes are ordinary bytes and delimiters inside quotes still split. For example selecting literal headers `"name"` and `"address"` from comma-separated quoted text matches those quote-containing byte strings; an embedded comma still starts another field.

## Spec 9

`-e EXCLUDE` uses exactly the numeric grammar from `-f`, but removes matching original input indices. It applies after inclusion and always wins over `-f` and `-F`. If `-e` is present without an inclusion option, inclusion defaults to all fields. Nonexistent excluded indices are harmless. Multiple and overlapping exclusion ranges form their union.

Examples on `a b c d e f` are:

```text
-e 2,4               -> a<TAB>c<TAB>e<TAB>f
-e 3-                 -> a<TAB>b
-f 1-5 -e 3          -> a<TAB>b<TAB>d<TAB>e
-f 3- -e -5          -> f
-f 2-5 -e 3-         -> b
-f 1- -e 3-5         -> a<TAB>b<TAB>f
```

If numeric inclusion and exclusion cancel the entire precomputed selection (for example `-f 4,3 -e 2-5`, `-f 1 -e 1`, or `-e 1-`), succeed with zero output bytes rather than one blank line per record.

## Spec 10

`-F HEADER_FIELD` selects columns by examining the first record as a header, and the selected header record is itself output. Without `-r`, matching is byte-for-byte literal, case-sensitive, and is not trimmed. Spaces, empty names, numeric names, quotes, punctuation, and Unicode are valid literal header names. Every column with the requested name is selected, including duplicate header names. Repeated `-F` arguments establish selection order; `-F city -F name` emits city before name.

For each positional input file, resolve header selectors independently from that file’s first record and output that file’s selected header followed by its records. The same applies to uncompressed stdin. A file containing only a header emits the selected header and succeeds.

If none of the requested inclusion headers match, exit 1 and write a diagnostic containing `No headers matched` to stderr. If some requested literal selectors match but a later one does not, exit 1 with `Header not found: NAME`. Literal `-F '^is_.*$'` does not act as a regex and therefore fails unless that exact header exists.

## Spec 11

With `-r`, every `-F` and `-E` argument is a regex searched anywhere within each header field. Anchors restrict the match normally. One pattern selects every matching column in input order. Multiple inclusion patterns have a legacy ordering that is not simple pattern-argument grouping: for header `aa bx ab by` and data row `1 2 3 4`, `-r -F '^b' -F 'a'` emits `bx<TAB>ab<TAB>by<TAB>aa` and `2<TAB>3<TAB>4<TAB>1`, respectively. Other examples include `-F '^ST.*'` matching both `STAT` and `START`, `-F 'col[13579]$'`, `-F '(?i)NAME'`, and an unanchored `-F id` matching headers that merely contain `id`.

Header regexes are validated during command-line parsing. An invalid header regex such as `[` exits 2 before reading input and reports an error beginning like `error: invalid value '[' for '--header-field <HEADER_FIELD>': regex parse error:`, ending with `For more information, try '--help'.`.

## Spec 12

`-E EXCLUDE_HEADER` resolves columns from the header exactly as `-F` does (literal by default, regex with `-r`) and removes them. It is repeatable, exclusion wins over every inclusion mechanism, and a nonmatching exclusion is a no-op rather than an error. With no explicit `-f` or `-F`, header exclusion starts from all fields in input order. If header exclusions remove all columns, preserve one blank output record per input record (unlike a wholly cancelled numeric selection, which produces zero bytes).

Examples:

```text
name age city / Alice 30 NYC, with -E age
    -> name<TAB>city / Alice<TAB>NYC

USER PID %CPU STAT TIME, with -r -E CPU -E '^ST.*'
    -> USER<TAB>PID<TAB>TIME
```

## Spec 13

Numeric (`-f`) and header (`-F`) inclusions are combined as a union, and duplicate physical columns are output once. Each mechanism has its own requested output order; merge the two ordered groups by output rank. At the same rank, emit lower original input indices first. This produces the required representative behaviors:

```text
header a,b,c,d,e; -f 3 -F b -F a
    -> b,c,a

header USER,PID,CPU; -f 3 -F PID -F USER
    -> PID,CPU,USER

header name,age,city; -f 1,3 -F age
    -> name,age,city

header name,age,city,salary; -f 4,2 -F name
    -> name,age,salary
```

The concrete merge examples above are authoritative, including the last legacy ordering case.

After this merge, remove every index matched by either `-e` or `-E`. Numeric exclusions always refer to original input positions, not positions in the intermediate output. The header row and every data row use the identical resolved column list.

## Spec 14

Join selected fields with an output delimiter and append the record terminator from Spec 3. The default output delimiter is one tab byte. `-D OUTPUT_DELIMITER` replaces it and accepts empty, single-byte, multibyte, Unicode, and newline values. Decode at least `\t`, `\n`, `\r`, and escaped backslash notation; an actual newline argument is also valid. Empty `-D ''` concatenates fields. A newline delimiter puts fields on separate lines in addition to the final record terminator.

`-I` requests reuse of the input delimiter only when `-L` makes that delimiter a concrete literal. For example `-L -d ',' -I -f 1,3` emits `field1,field3`. In regex mode, `-I` is accepted but has no effect, leaving the ordinary output delimiter (normally tab). If both `-I` and `-D` are present in literal mode, using the literal input delimiter is acceptable and should take precedence.

## Spec 15

Output goes to stdout by default. `-o -` explicitly means stdout. Any other `-o PATH` creates or truncates that file, writes all output there, and leaves stdout empty. Parent directories are not created automatically. Newly created files must be owner-readable and owner-writable. Existing files are replaced, not appended.

Failure to create or open an output reports status 1 on stderr, names the path, and includes both `Failed to open PATH for writing` and the operating-system reason such as `No such file or directory`. Passing a directory as the output path also fails.

## Spec 16

With `-z`/`--try-decompress`, transparently decompress inputs before line and field processing. Recognize gzip (`.gz` and gzip stdin), bzip2 (`.bz2`), and xz (`.xz`); these capabilities apply to single or multiple files. The decompressed data must behave exactly like ordinary input. There is no fallback that passes ordinary uncompressed stdin through unchanged. In particular, `-z -f2` with stdin `a b\n` exits 1, writes no stdout, and reports `[<timestamp> ERROR hck] unexpected end of file` on stderr. Invalid gzip input exits 1 with stderr containing `invalid gzip header`.

Compressed stdin supports numeric field selection. Header-based selection on compressed stdin is deliberately unsupported, but inclusion and exclusion differ diagnostically. With `-z -F name` on gzip-compressed stdin whose header is `name age`, exit 101 with no stdout, first warn `Selections based on header fields is not currently supported on STDIN compressed data.`, and then panic with `not implemented: Header selections not supported when piping gzipped stdin`. With `-z -E age` on that same compressed stdin, exit 101 with no stdout and the same panic text, but do not emit the preceding warning.

## Spec 17

With `-Z`/`--try-compress`, gzip-compress the final output, whether its destination is stdout or `-o PATH`. The result must begin with gzip magic bytes and decompress with a conventional gzip reader to exactly the uncompressed output described above. `-Z` on empty stdin exits 0 without stderr and emits a nonempty valid gzip stream that decompresses to zero bytes; it does not emit zero stdout bytes. `-z` and `-Z` may be combined for decompress-process-recompress operation.

`-l` accepts an integer gzip compression level; levels 1, 6, and 9 must work. `-t` accepts a nonnegative machine-sized integer thread count; 0, 1, 2, and 8 must all work. These controls must never change decompressed content. They may be accepted even when compression is not requested.

## Spec 18

Field-list validation happens as an application/runtime error and exits 1. Reject field 0 in either `-f` or `-e` with a stderr line containing `Fields and positions are numbered from 1: 0`. Reject a reversed closed range with `High end of range less than low end of range: 5-2`. Reject empty items, an empty list, nonnumeric items, overflow, leading/trailing commas, doubled commas, and extra dashes (such as `1--5` or `1-2-3`) with `Failed to parse field:` followed by the offending item when available. A lone dash has a precise exception: `-f -` exits 1 with empty stdout, and after timestamp normalization and trimming the exact stderr line is `[TIMESTAMP ERROR hck] Failed to parse field:`—the offending `-` is not printed. These diagnostics use the form `[<timestamp> ERROR hck] MESSAGE`; the timestamp value is not fixed. Runtime failures must not print ordinary data to stderr.

Missing/unreadable input paths exit 1, leave stdout empty if failure occurs before any source is processed, and use the same timestamped error style. When `/nonexistent.csv` is the first input and an existing valid file is the second, the program exits 1 with empty stdout; after timestamp normalization the complete stderr is `[TIMESTAMP ERROR hck] No such file or directory (os error 2)\n`. The diagnostic omits the missing path. Inputs named like options after `--` are positional paths; for example `-- --help` tries to open a file named `--help` rather than showing help.

## Spec 19

Command-line syntax errors exit 2 and write a conventional structured argument-parser error to stderr. Unknown options must include `unexpected argument`. A missing value for `-o`, `-f`, or `-d` must respectively include:

```text
a value is required for '--output <OUTPUT>'
a value is required for '--fields <FIELDS>'
a value is required for '--delimiter <DELIMITER>'
```

Repeating `-f` includes `cannot be used multiple times`. Non-integer `-t notint` includes `invalid value 'notint'`; integer overflow includes `number too large`. Because option-looking tokens are not silently consumed as integer values, `-t -1` exits 2 and includes both `unexpected argument '-1'` and `tip: to pass '-1' as a value`.

## Spec 20

`--no-mmap` is a supported compatibility switch and must not change observable results for stdin, small files, large files, compressed files, field exclusion, or any combination thereof. The executable must handle long fields, lines well beyond normal fixed buffers, thousands of columns, many input files, tens of thousands to roughly a million records, and data sets of at least about 10 MB within ordinary command-line resource limits. It must stream or otherwise avoid truncation, fixed field-count limits, hangs, and regex empty-match loops.
