# Specification: `xsv`-compatible CSV command-line executable

## Spec 1: Required artifact and invocation

Provide one executable program named exactly `executable`. It is invoked as:

```text
./executable <command> [arguments...]
```

The program is a byte-oriented CSV command-line toolkit compatible with the observable behavior of `xsv` 0.13.0. It must implement these commands:

```text
cat count fixlengths flatten fmt frequency headers help index input
join partition reverse sample search select slice sort split stats table
```

Unless a command explicitly creates multiple files, successful results go to standard output. Diagnostics go to standard error. Nonempty textual output ends in a record/line terminator (normally LF). A normal success exits 0 and an invalid invocation, input/output failure, invalid selector, invalid regular expression, or malformed CSV exits 1. A broken output pipe is a successful early termination and must exit 0.

## Spec 2: Top-level CLI behavior

`--version` prints exactly:

```text
0.13.0
```

followed by a newline, on stdout, with exit status 0 and no stderr output.

`--help`, `-h`, and the `help` command succeed and display this main usage message (apart from an immaterial leading/trailing blank line):

```text
Usage:
    xsv <command> [<args>...]
    xsv [options]

Options:
    --list        List all commands available.
    -h, --help    Display this message
    <command> -h  Display the command help message
    --version     Print version info and exit

Commands:
    cat         Concatenate by row or column
    count       Count records
    fixlengths  Makes all records have same length
    flatten     Show one field per line
    fmt         Format CSV output (change field delimiter)
    frequency   Show frequency tables
    headers     Show header names
    help        Show this usage message.
    index       Create CSV index for faster access
    input       Read CSV data with special quoting rules
    join        Join CSV files
    partition   Partition CSV data based on a column value
    sample      Randomly sample CSV data
    reverse     Reverse rows of CSV data
    search      Search CSV data with regexes
    select      Select columns from CSV
    slice       Slice records from CSV
    sort        Sort CSV data
    split       Split CSV data into many files
    stats       Compute basic statistics
    table       Align CSV data into columns
```

`--list` succeeds and writes `Installed commands:` followed by these exact entries:

```text
    cat         Concatenate by row or column
    count       Count records
    fixlengths  Makes all records have same length
    flatten     Show one field per line
    fmt         Format CSV output (change field delimiter)
    frequency   Show frequency tables
    headers     Show header names
    help        Show this usage message.
    index       Create CSV index for faster access
    input       Read CSV data with special quoting rules
    join        Join CSV files
    partition   Partition CSV data based on a column value
    sample      Randomly sample CSV data
    reverse     Reverse rows of CSV data
    search      Search CSV data with regexes
    select      Select columns from CSV
    slice       Slice records from CSV
    sort        Sort CSV data
    split       Split CSV data into many files
    stats       Compute basic statistics
    table       Align CSV data into columns
```

After the final entry, `--list` writes one additional blank line: the complete
byte stream ends with two consecutive LF bytes.

Invoking the program without arguments is also successful, but writes the command chooser to stderr. It starts with:

```text
xsv is a suite of CSV command line utilities.

Please choose one of the following commands:
```

and then prints the same indented command entries shown above. Like `--list`, it
writes one additional blank line after the final entry: stdout is empty, and the
complete stderr byte stream ends with two consecutive LF bytes.

An unknown command exits 1 and reports, on stderr:

```text
Could not match '<command>' with any of the allowed variants: ["cat", "count", "fixlengths", "flatten", "fmt", "frequency", "headers", "help", "index", "input", "join", "partition", "reverse", "sample", "search", "select", "slice", "sort", "split", "stats", "table"]
```

Commands are case-sensitive. If the spelling is an otherwise valid command with uppercase letters, exit 1 with this exact form:

```text
xsv expects commands in lowercase. Did you mean '<lowercase-command>'?
```

Unknown top-level or command flags are errors and must start with `Unknown flag: '<flag>'`, followed by command usage when applicable. Missing required positionals produce `Invalid arguments.` followed by that command's usage. In particular, `cat` requires `rows` or `columns`; `select` requires a selection; `search` requires a regex; `sample` requires a sample size; `join` requires two selections and two inputs; `partition` requires a column and output directory; `split` requires an output directory; and `index` requires a file.

The complete missing-positional diagnostics for `search`, `select`, `join`, and
`cat`, including the blank line, indentation, and secondary help form, are:

```text
Invalid arguments.

Usage:
    xsv search [options] <regex> [<input>]
    xsv search --help
```

```text
Invalid arguments.

Usage:
    xsv select [options] [--] <selection> [<input>]
    xsv select --help
```

```text
Invalid arguments.

Usage:
    xsv join [options] <columns1> <input1> <columns2> <input2>
    xsv join --help
```

```text
Invalid arguments.

Usage:
    xsv cat rows    [options] [<input>...]
    xsv cat columns [options] [<input>...]
    xsv cat --help
```

For example, `xsv select --invalid-flag 1` exits 1 and writes exactly:

```text
Unknown flag: '--invalid-flag'

Usage:
    xsv select [options] [--] <selection> [<input>]
    xsv select --help
```

The commands `cat`, `count`, `headers`, `input`, `reverse`, `search`, `select`, `slice`, `sort`, `stats`, and `table` have useful command-specific `-h`/`--help` output containing `Usage:` and exit 0.

## Spec 3: CSV model

Input is parsed as CSV records, not physical lines. Quoted delimiters, doubled quotes, embedded newlines, empty fields, trailing empty fields, NUL bytes, long fields, Unicode, and invalid UTF-8 bytes must not be corrupted by ordinary record-preserving transformations. `stats` has the lossy presentation exception for invalid-UTF-8 extrema specified in Spec 22. Except for `fixlengths`, ordinary commands enforce a consistent number of fields and report a CSV error for ragged records.

For `frequency`, `stats`, and `sort` in header mode, a completely blank
physical line among the data is skipped before width checking or command
processing. It is neither a zero-field record nor a one-field empty value, and
therefore does not cause a ragged-record error. `frequency --no-nulls` and
`stats --nulls` do not change this rule. To supply an actual one-field empty
value, encode a CSV field, for example as `""`; that record is processed as an
empty field.

The default input delimiter is comma. `-d <char>` and `--delimiter <char>` select another input delimiter. A delimiter must be exactly one ASCII byte; a literal tab and the two-character CLI spelling `\t` both mean a tab byte. Empty, multi-character, or non-ASCII delimiters exit 1 with:

```text
Could not convert '<value>' to a single ASCII character.
```

In the absence of an explicit delimiter, a file whose name ends in `.tsv` or `.tab` is parsed as tab-separated. Stdin has no filename-based detection.

When `-d` or `--delimiter` is the final argument and therefore has no value, exit 1 and begin stderr with:

```text
Expected argument for flag '--delimiter' but reached end of arguments.
```

After that line, print a blank line and the invoking command's normal multiline `Usage:` block.

CSV-producing commands serialize records canonically: comma-separated, minimally double-quoted as required by CSV, doubled internal double quotes, and LF record endings. Thus a non-comma input delimiter affects parsing but normally not the output delimiter. `fmt` is the exception because it controls output format.

Header mode is the default. The first record is the header and is not a data record. `-n` and `--no-headers` make every record data and suppress generated/preserved headers. When the environment variable `XSV_TOGGLE_HEADERS` has the exact value `1`, the effective header setting is inverted: omitting `-n` becomes headerless and supplying `-n` becomes header mode. Other values, including `true`, have no effect. This applies equally to files and stdin.

An omitted optional input and an input spelled `-` mean stdin. Commands accepting multiple inputs may use stdin at most once; for example, `cat rows - -` exits 1 with:

```text
At most one <stdin> input is allowed.
```

Completely empty input is handled without crashing. Depending on the command it yields `0`, empty output, or only an output header as described below. Header-only input has zero data records.

## Spec 4: Output files

For `cat`, `fixlengths`, `fmt`, `frequency`, `input`, `join`, `reverse`, `sample`, `search`, `select`, `slice`, `sort`, `stats`, and `table`, `-o <path>` and `--output <path>` redirect the complete result to that path and leave stdout empty. `--output=<path>` is accepted. In compatibility with the original parser, `-o=out.csv` treats the value as the literal path `=out.csv`. The `index` command also uses `-o` for its binary index destination.

`flatten` is the exception among the display commands: it supports neither
`-o` nor `--output`. Either spelling exits 1, creates no destination, and starts
stderr with `Unknown flag: '-o'` or `Unknown flag: '--output'`, respectively,
followed by a blank line and its `Usage:` block.

The output option may appear before or after positional arguments. When `-o` or `--output` is the final argument and therefore has no value, exit 1 and begin stderr with:

```text
Expected argument for flag '--output' but reached end of arguments.
```

After that line, print a blank line and the invoking command's normal multiline `Usage:` block. File creation/write failures are reported on stderr and exit 1.

## Spec 5: Errors

A missing file error has the form:

```text
failed to open <path>: No such file or directory (os error 2)
```

A structural CSV error includes record/line/byte context when available; for example:

```text
CSV error: record 2 (line: 3, byte: 12): found record with 2 fields, but the previous record has 3 fields
```

Opening an input path that is a directory exits 1 and writes exactly
`Is a directory (os error 21)` followed by LF. A write to `/dev/full` exits 1
and writes exactly `No space left on device (os error 28)` followed by LF.
These underlying operating-system diagnostics are not prefixed by the affected
path.

Options parsed as unsigned 64-bit integers reject non-integers, negative values, and overflow, using a diagnostic of the form:

```text
Could not deserialize '<value>' to u64 for '--option'.
```

## Spec 6: Shared column-selection language

`select`'s positional selection and the `-s`/`--select` options of `search`, `sort`, `frequency`, and `stats`, as well as both join selections, use one selector language.

- Comma separates selectors, and output follows selector order.
- A positive integer is a 1-based column index. `0` and indices past the record width are errors.
- A name selects the first exactly matching header. Names cannot be used in headerless mode.
- Repeated header names can be disambiguated as `name[k]`, where `k` is the zero-based occurrence among headers with that name. Thus `name[0]` is the first and `name[1]` the second.
- An unquoted selector name may contain quote bytes; they are ordinary literal
  name bytes rather than malformed quote syntax. Thus `col""name` selects a
  header whose decoded CSV field is `col""name`.
- A quoted selector name can contain commas, hyphens, or brackets. The first and
  last quote delimit the name, but interior quote bytes are retained one for
  one: unlike CSV field decoding, an interior `""` is **not** collapsed to one
  quote. Thus the CLI selection `"col""""name"` names a header containing four
  quote characters; that header serializes in CSV as `"col""""""""name"`.
  Brackets inside a quoted name are literal.
- `a-b` is an inclusive range whose endpoints may independently be an index, name, or indexed name. Reverse ranges are valid and reverse the selected column order.
- `-b` ranges from the first column through `b`; `a-` ranges from `a` through the last column; bare `-` selects every column. Use the CLI marker `--` before a dash-leading selection when necessary.
- Multiple ranges and single selectors may be mixed, and normal selections preserve repeated columns. For example, `1-3,5,2` emits columns 1, 2, 3, 5, 2.
- A leading `!` selects the complement in original column order. For example, `!2-3` selects every column except 2 and 3. A bare `!` selects no columns and serializes each input record as an empty CSV record (`""`).
- An empty selection string means all columns.

In headerless mode, a blank physical record is a zero-column record. Selecting
all its columns with bare `-` succeeds but emits no bytes for that record (in
particular, it does not emit an LF-only empty record).

Selector errors are fatal. Required diagnostics include these forms:

```text
Selector index 0 is out of bounds. Index must be >= 1 and <= <width>.
Selector name '<name>' does not exist as a named header in the given CSV data.
Cannot use names ('<name>') in selection with --no-headers set.
Selector index '<k>' for name '<name>' is out of bounds. Must be >= 0 and <= <last>.
Unclosed quote, missing closing ...
Unclosed index bracket, missing closing ].
Could not convert '<text>' to an integer: ...
Expected end of field but got '<char>' instead
```

## Spec 7: `count`

```text
xsv count [options] [<input>]
```

Print the number of data records as a base-10 integer plus newline. In header mode the header is excluded; in headerless mode every record is counted. Empty and header-only inputs print `0`. A malformed ragged CSV is an error rather than a physical-line count. An available valid index may supply the count, but it must not change the result.

## Spec 8: `headers`

```text
xsv headers [options] [<input>...]
```

For one input, print one header per line, numbered from 1 and padded for alignment. For two columns the exact form is:

```text
1   first
2   second
```

`-j`/`--just-names` omits indices and prints names one per line. Supplying multiple inputs also prints bare names, input by input, preserving duplicates and file order. `--intersect` emits each distinct name encountered across the inputs once, in first-encounter order (despite the option's historical name). Empty input produces no output. Empty and duplicate header names remain visible entries.

## Spec 9: `select`

```text
xsv select [options] [--] <selection> [<input>]
```

Emit only the selected columns, including the correspondingly selected header in header mode. It supports the complete selection language in section 4, file or stdin input, custom input delimiters, and output redirection.

## Spec 10: `slice`

```text
xsv slice [options] [<input>]
```

Slice data records by zero-based record position. Preserve the header in header mode regardless of the selected data range.

- `-s`/`--start N`: first record, default 0.
- `-e`/`--end N`: exclusive end; with no start, returns `[0,N)`.
- `-l`/`--len N`: take at most N records from the start. `--len 0` emits only the header in header mode and nothing in headerless mode.
- `-i`/`--index N`: emit exactly data record N.

With no range flags, emit all records. A start beyond EOF yields only the header when scanning an unindexed file. `--end` and `--len` are mutually exclusive; supplying both exits 1 with exactly:

```text
--end and --len cannot be used at the same time.
```

`--index` cannot be combined with `--start`, `--end`, or `--len`; any such combination exits 1 with exactly:

```text
--index cannot be used with --start, --end or --len
```

If start exceeds end, exit 1 with:

```text
The end of the range (<end>) must be greater than or
equal to the start of the range (<start>).
```

An indexed single-record lookup outside the data range exits 1 and reports `invalid record index N (there are M records)`.

## Spec 11: `search`

```text
xsv search [options] <regex> [<input>]
```

Compile a Rust-regex-compatible byte regular expression and test it independently against each field in the search selection (all columns by default). Emit the complete original row when any selected field matches. Do not project the output to the selected search fields. Preserve the header even if no data rows match; in headerless mode, no matches means empty output.

`-i`/`--ignore-case` makes the regex case-insensitive. `-v`/`--invert-match` emits rows for which no selected field matches. The options compose, including combined `-vi`. Anchors, alternation, repetition, character classes, word boundaries, and escaped metacharacters work. Matching is case-sensitive by default, applies inside parsed multiline fields, and an expression such as `^$` matches an empty field. An invalid expression exits 1 with a useful regex parse diagnostic. For example, pattern `(?P<invalid` produces this stderr text:

```text
Syntax(
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
regex parse error:
    (?P<invalid
               ^
error: unclosed capture group name
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
)
```

## Spec 12: `sort`

```text
xsv sort [options] [<input>]
```

Sort data rows by the selected tuple, using the first column by default, while preserving the header. Default ordering is ascending bytewise lexicographic ordering; numeric-looking strings are still lexical unless numeric mode is requested. Multiple selected columns are compared in selection order. Equal keys retain deterministic reference-compatible ordering.

`-N`/`--numeric` parses sort keys as floating-point values. Integers, decimals, and negative values compare numerically. Empty and non-numeric keys sort before numeric keys in ascending mode. `-R`/`--reverse` reverses the comparison for string or numeric sorting. These flags may be supplied independently. A nonexistent selected column is an error. Supplying a duplicate boolean option such as `--reverse --reverse` is an invalid invocation.

A bare blank physical line is skipped as specified in Spec 3; it does not
produce an empty sort key. A quoted empty field (`""`) is an actual empty key
and is retained and sorted before non-numeric and numeric keys in ascending
numeric mode.

## Spec 13: `reverse`

```text
xsv reverse [options] [<input>]
```

Emit all data records in reverse order. Preserve the header at the beginning in header mode; reverse every record in headerless mode. Empty input is empty, header-only input returns the header, and a single data row is unchanged. Stdin and indexed or ordinary files have identical observable output.

## Spec 14: `cat`

```text
xsv cat rows    [options] [<input>...]
xsv cat columns [options] [<input>...]
```

With no inputs, use stdin. More than one stdin occurrence is an error.

`cat rows` emits records from inputs in argument order. In header mode, emit the first input's header only and consume/discard headers from subsequent inputs. If the first input is completely empty, it contributes no header; later headers are still consumed, so concatenating an empty first file and a populated second file emits only the second file's data. In headerless mode concatenate every record. Incompatible record widths cause a CSV error, possibly after valid earlier output (including the incompatible record) has already been written. In particular, when a second input consists of header `d,e,f` followed by `4,5`, after a first input `a,b,c` followed by `1,2,3`, the command exits 1, stdout contains only `a,b,c\n1,2,3\n`, and stderr is exactly `CSV error: record 1 (line: 2, byte: 6): found record with 2 fields, but the previous record has 3 fields` followed by LF.

`cat columns` horizontally concatenates corresponding records in input order, including concatenating headers in header mode. Without `-p`/`--pad`, stop when the shortest input ends. With `--pad`, continue to the longest input and add the correct number of empty fields for each exhausted input.

## Spec 15: `join`

```text
xsv join [options] <columns1> <input1> <columns2> <input2>
```

Selections on the two sides must contain the same number of columns. Otherwise exit 1 with:

```text
Column selections must have the same number of columns, but found column selections with <n1> and <n2> columns.
```

With no join-type flag, perform an inner join. Exactly one of these may be used:

- `--left`: left outer join.
- `--right`: right outer join.
- `--full`: full outer join.
- `--cross`: Cartesian product; selection values do not constrain matches.

Supplying more than one exits 1 with `Please pick exactly one join operation.`

Output columns are every column from input 1 followed by every column from input 2; duplicate header names are retained. In header mode, output this combined header even when there are no matches. In headerless mode, use numeric selectors and emit no header.

For inner/left/full joins, traverse left rows in input order and emit matching right rows in their input order. Duplicate keys produce every matching pair. Left-unmatched rows are followed by one empty field for every right column. A full join then appends unmatched right rows, padded on the left. A right join is right-driven: preserve right-row/key order and emit matching left rows before padded right-only rows.

A composite key matches only when every selected component matches. Key components have surrounding whitespace trimmed for comparison but retain their original spelling in output. Matching is case-sensitive by default. `--no-case` compares valid text keys case-insensitively. Rows with an empty component do not match by default; `--nulls` permits empty keys on both sides to match. Invalid UTF-8 key data must not crash the program and does not spuriously match valid text. Under `--no-case`, byte-identical invalid-UTF-8 keys on the two sides do match each other and their original bytes are preserved in the joined output; for example, singleton byte `0xFF` matches singleton byte `0xFF`.

## Spec 16: `fixlengths`

```text
xsv fixlengths [options] [<input>]
```

Read ragged CSV permissively and make every record the same width. With `-l`/`--length N`, truncate longer records and append empty fields to shorter ones so every output record has exactly N fields. N must be greater than zero; zero exits 1 with `Length must be greater than 0.`

Without `--length`, make a first pass over a seekable file to find the maximum effective record width, not counting trailing empty fields, then normalize all records to that width. Because auto-detection requires two passes, stdin without `--length` exits 1 with:

```text
<stdin> cannot be used in this command. Please specify a file path.
```

## Spec 17: `flatten`

```text
xsv flatten [options] [<input>]
```

Print one field per line as an aligned label/value pair. Labels are header names in header mode and zero-based numeric labels in headerless mode. The label column is padded so values align. For example:

```text
name  Alice
age   30
city  NYC
#
name  Bob
age   25
city  LA
```

The default separator between records is `#`, printed on its own line and never after the final record. `-s`/`--separator TEXT` replaces it; an empty separator joins adjacent record blocks without an extra separator line.

The label column has a minimum display width of two characters. Its actual width is the larger of two and the longest label's full display width, and exactly two spaces are added after that width before the value. Consequently a one-character label is followed by three spaces, while the four-character label `name` in the example above is followed by two.

`-c`/`--condense N` changes any **value** longer than N characters to its first N Unicode scalar characters followed by `...`; valid UTF-8 is never cut mid-character. Invalid UTF-8 is truncated safely by byte instead of crashing. It does not condense labels: label alignment continues to use every label's full, uncondensed width. For example, `flatten -c 10` on header `description` retains that complete label while a value `A very long description text` becomes `A very lon...`. Header-only and empty inputs produce no flattened records.

## Spec 18: `table`

```text
xsv table [options] [<input>]
```

Render CSV as an aligned plain-text table, one record per line and no delimiter characters between ordinary fields. Each non-final column is padded to the larger of its maximum displayed width and the configured minimum width, then receives the configured inter-column padding. The default minimum width is two and the default padding is two. Thus a non-final column containing only one-character cells has three spaces after each cell. For example:

```text
name     age  city
Alice    30   NYC
Bob      25   LA
Charlie  35   Boston
```

`-w`/`--width N` sets that minimum display width and `-p`/`--pad N` sets inter-column padding. `-c`/`--condense N` applies the same Unicode-safe `N` characters plus `...` rule as `flatten` before alignment. Values needing CSV quoting, such as a field containing quotes, remain validly quoted/escaped in the displayed cell. Empty input is empty; header-only input displays its header.

## Spec 19: `fmt`

```text
xsv fmt [options] [<input>]
```

Parse normal CSV using the common input delimiter and rewrite it with controlled output syntax.

- `-t`/`--out-delimiter CHAR` selects one ASCII output delimiter; default comma.
- `--crlf` uses CRLF after every record instead of LF.
- `--quote CHAR` changes the output quote character.
- `--escape CHAR` changes quote escaping from doubled quotes to the requested escape character where needed.
- `--quote-always` quotes every field, including headers.
- `--ascii` uses byte `0x1F` (unit separator) between fields and byte `0x1E` (record separator) after every record, including the last.

Output quoting is semantic: if the output delimiter occurs inside a field, that field is quoted with the configured quote character. For example, choosing `h` as delimiter quotes fields such as `h1` and `ghijkl`.

## Spec 20: `input`

```text
xsv input [options] [<input>]
```

Read delimited data with nonstandard input quoting and rewrite it as canonical comma CSV.

- `--quote CHAR` sets the input quote character, including single quote.
- `--escape CHAR` sets an explicit input escape character, including backslash.
- `--no-quoting` treats quote bytes literally instead of as CSV syntax.
- The common `-d` option can be combined with these settings.

The output always uses ordinary canonical double-quoted CSV unless changed by a later pipeline command.

## Spec 21: `frequency`

```text
xsv frequency [options] [<input>]
```

For each selected column (all columns by default), count byte-exact field values and emit CSV with this header:

```text
field,value,count
```

In header mode `field` is the header name. In headerless mode it is a **1-based output position after selection** (`1`, `2`, ...), not the original physical-column position, and the physical first record participates as data. Thus `frequency -n -s 2` analyzes physical column 2 but labels its frequency rows `1`.

Empty values are counted and displayed as `(NULL)` by default. A literal field whose bytes are `(NULL)` is a distinct counted value even though it has the same rendered label. `--no-nulls` excludes only genuinely empty fields.

A completely blank physical line is skipped as specified in Spec 3 and is not
a genuinely empty field for either default counting or `--no-nulls`.

Within each field, output is ranked by count descending by default. `-a`/`--asc` ranks least frequent first. `-l`/`--limit N` retains at most N values **per field** after applying that direction; the default limit is 10, while limit 0 disables limiting. Ties follow the deterministic legacy byte-map order and must not be replaced with an assumed alphabetical tie-breaker.

`-s`/`--select` selects analyzed columns. Selecting no columns emits only `field,value,count`. `-j`/`--jobs N` may parallelize indexed input but must produce the same counts and valid ordering; job counts larger than the number of rows and indexed header-only files are valid.

## Spec 22: `stats`

```text
xsv stats [options] [<input>]
```

Emit one CSV row per selected input field. The default schema is exactly:

```text
field,type,sum,min,max,min_length,max_length,mean,stddev
```

Optional columns are appended in this order when requested:

- `--median` appends `median`.
- `--mode` appends `mode`.
- `--cardinality` appends `cardinality`.
- `--everything` enables all three, in the order `median,mode,cardinality`.

`-s`/`--select` chooses fields. In header mode `field` is the header. In headerless mode the first physical record is data, and `field` labels are **zero-based output positions after selection** (`0`, `1`, ...), not original physical-column positions. Thus `stats -n -s 2` analyzes the second physical field but labels its row `0`; selecting `2,1` labels those rows `0` and `1` in that order. `-j`/`--jobs N` may process a valid indexed file in parallel, but must be byte-for-byte equivalent to sequential statistics. High job counts and empty indexed input are valid.

Type inference and base columns behave as follows:

- A field with no data records has type `NULL`; all base statistic cells are
  empty. With all optional columns enabled, its median is empty, mode is `N/A`,
  and cardinality is `0`.
- A field with one or more data records whose values are all empty also has type
  `NULL`, but its `min_length` and `max_length` are both `0`; its other base
  statistic cells are empty. With all optional columns enabled, its median and
  mode are empty and its cardinality is `1`.
- If every nonempty value parses as signed 64-bit integer, type is `Integer`.
- Otherwise, if every nonempty value parses as IEEE-754 floating point, type is `Float`.
- Otherwise valid UTF-8 gives type `Unicode`; invalid UTF-8 gives `Unknown`.
- Encountering a float promotes Integer to Float; encountering valid nonnumeric text promotes a numeric type to Unicode.
- `min` and `max` compare numerically for numeric types and bytewise lexicographically for text/unknown types. Empty fields are excluded from min/max. For `Unknown`, comparison uses the raw bytes, but the selected extrema are converted to UTF-8 lossily when written to the stats CSV. In particular, for singleton values `0xFF` and `0xFE`, the type is `Unknown`, both displayed extrema are the UTF-8 replacement character (bytes `EF BF BD`), and both reported lengths remain `1`.
- `min_length` and `max_length` are byte lengths of the raw field values and do include empty values, so a column containing an empty value has minimum length 0. Multibyte Unicode therefore counts by UTF-8 bytes.
- `sum`, `mean`, and `stddev` are present only for numeric types. Standard deviation is population standard deviation. One numeric value has stddev 0. Floating sums are accumulated from left to right in input-record order.
- By default empty numeric cells are excluded from the mean/stddev population. `--nulls` treats them as numeric zero and includes them in the denominator; it does not change min, max, or lengths. A skipped blank physical line is not an empty numeric cell and does not enter this population.
- Integer summation uses signed 64-bit wrapping semantics. Numeric calculations follow IEEE-754 behavior, including `NaN`, `inf`, and `-inf`. Finite floats use the shortest decimal form that round-trips to the computed binary value and omit a redundant `.0`.
- Median is numeric only; for an even count it is the average of the two middle values.
- Mean and variance use an order-sensitive online update, not a two-pass calculation or a sum-of-squares shortcut. Starting with `n = 0`, `mean = 0`, and `variance = 0`, for each included numeric value `x` in input-record order, save `oldmean = mean` and `prevq = variance * n`, increment `n`, then set `mean += (x - oldmean) / n` and `variance = (prevq + (x - oldmean) * (x - mean)) / n`. Emit `sqrt(variance)` as stddev. With `--nulls`, an included empty cell supplies `x = 0` to this update.
- For non-NULL fields, mode is emitted only when one value has a unique greatest frequency and that frequency is greater than one. If no value repeats or two or more values tie for greatest frequency, print `N/A`. NULL-field behavior is the distinct all-empty/no-data behavior stated above.
- Cardinality is the number of distinct raw values.

For example, values `1,2,3` have sum `6`, mean `2`, and stddev `0.816496580927726`; values `1,2,3,4` have median `2.5`.

## Spec 23: `sample`

```text
xsv sample [options] <sample-size> [<input>]
```

Choose the requested number of distinct data records without replacement and preserve the header in header mode. Headerless mode includes the physical first row in the population and emits no header. If the request is at least the population size, emit all rows in original order. Header-only input emits its header; completely empty input emits nothing.

Without an index, use reservoir sampling with memory proportional to the requested size. With a valid index, random-access sampling is used when the request is strictly less than 10% of the population; otherwise use reservoir sampling. Output order is the reference algorithm's sample/reservoir order, not sorted input order.

`--seed U64` uses the legacy `xsv` deterministic seeded generator on the
reservoir-sampling path. Seed zero is a real seed, not a request for
nondeterminism. Omitting the option uses fresh randomness. In seeded reservoir
mode, encode the U64 in little-endian order in the first eight bytes of a
32-byte seed whose other bytes are zero, use that to initialize the HC-128
generator, and use unbiased rejection sampling for each bounded integer draw.
Reservoir sampling first stores the first `k` data rows in slots `0..k`; for
each later zero-based row position `i`, draw uniformly from `0..=i` and replace
that reservoir slot only when the draw is below `k`.

The indexed random-access path does not apply `--seed`: it uses fresh
randomness to perform a reverse Fisher-Yates shuffle of all zero-based row
indices, then emits the first `k` indexed rows in shuffled order. Thus this
path is nondeterministic even when a seed is supplied, and repeated identical
invocations can produce different samples. The sampled records are still
distinct.

The following vectors define required seeded compatibility for a header plus data rows numbered 1 through 10:

```text
seed 42,  size 5  => 8, 7, 3, 10, 5
seed 123, size 3  => 6, 5, 9
seed 0,   size 3  => 1, 6, 5
```

For a five-row unindexed population numbered 1 through 5, seed 42 and size 2
produce rows `5,2`. Repeating a command with the same seed is byte-for-byte
deterministic on the reservoir path, but not on the indexed random-access path
described above.

For an unindexed population numbered 1 through 30, seed 0 and size 15 produce rows in this order:

```text
1, 2, 22, 4, 5, 25, 26, 8, 30, 18, 16, 12, 29, 27, 15
```

For that same unindexed population, seed 42 and size 20 produce:

```text
24, 2, 3, 22, 5, 6, 7, 23, 26, 25, 29, 12, 13, 14, 30, 16, 17, 18, 19, 20
```

With a valid index on that 30-row population, seed 42 and size 4 (which takes the reservoir path) produce:

```text
15, 13, 7, 30
```

## Spec 24: `index`

```text
xsv index [options] <input>
```

Create a binary random-access index. By default its path is the input path plus `.idx`; `-o`/`--output` chooses another path. Stdin is not accepted. If the CSV contains `R` physical CSV records (including the header record, when present), the index consists of `R` unsigned 64-bit big-endian starting byte offsets, one for each parsed record, followed by the unsigned 64-bit big-endian value `R`. Its size is therefore exactly `8 * (R + 1)` bytes (for example, 31 physical records produce a 256-byte index). The index must contain enough record-offset information for indexed `count`, `slice`, `sample`, `frequency`, `stats`, and `split` workflows. Their indexed behavior is described in the corresponding command sections, including the indexed random-access `sample` behavior and indexed header-only `split` behavior.

An index records every physical CSV record so the consumer can correctly reinterpret the same file in header or headerless mode. Staleness is detected from the CSV and index files' modification timestamps with one-second resolution. Indexed use exits 1 only when the CSV's modification time is at least one full second newer than the index's modification time, with:

```text
The CSV file was modified after the index file. Please re-create the index.
```

A rewrite less than one second after index creation is therefore accepted and
the stale index is used. For example, after indexing the two-record file
`h\na\n`, immediately replacing it with `h\na\nb\n` and invoking `count`
prints `1` followed by LF, rather than detecting the added record.

## Spec 25: `split`

```text
xsv split [options] <outdir> [<input>]
```

Create `outdir` when it is absent, or reuse it when it is already a directory, and divide data into consecutive chunks of `-s`/`--size N` data records. A pre-existing directory is valid even when it contains other files, and its unrelated contents are not cleared. The default size is 500. N must be greater than zero; zero exits 1 and writes exactly `--size must be greater than 0.` followed by LF to stderr. An omitted input means stdin.

In header mode, copy the header into every output file; headers do not count against chunk size. In headerless mode, every physical record counts and no header is inserted. Preserve record order and every parsed field, including quoted commas, quotes, embedded newlines, tabs, and backslashes. On the unindexed path, a header-only input creates `0.csv` containing just the header. When a valid index is present, a header-only input instead creates or reuses the output directory but creates no chunk file; this is also the behavior with `--jobs 0`. Do not create a spurious final empty chunk when a nonempty population divides evenly.

Default filenames are `<offset>.csv`, where offset is the zero-based data-record start of that chunk: with size 3 they are `0.csv`, `3.csv`, `6.csv`, and so on. `--filename TEMPLATE` replaces the name by substituting the same offset for exactly one `{}`. A template with zero or multiple `{}` placeholders exits 1 with:

```text
The --filename argument must contain one '{}'.
```

`-j`/`--jobs N` permits indexed parallel splitting without changing file contents or boundaries; `--jobs 0` means automatic CPU selection. Directory-creation errors are fatal and report the OS error.

## Spec 26: `partition`

```text
xsv partition [options] <column> <outdir> [<input>]
```

Create `outdir` when it is absent, or reuse it when it is already a directory, and route each row to the file corresponding to its value in one selected column. A pre-existing directory is valid even when it contains other files (including the input file itself), and its unrelated contents are not cleared. Exactly one column must be selected; otherwise exit 1 with `can only partition on one column`. Rows keep input order within each output file.

In header mode every partition file starts with the original header. `--drop` removes the partition column from both header and rows. In headerless mode, use a numeric selector, treat the first physical row as data, and emit no header; `--drop` still removes the chosen field.

The default filename is `<sanitized-value>.csv`. Before naming, `-p`/`--prefix-length N` truncates a longer value to its first N characters; an equal-length or shorter value remains intact, and the original untruncated value remains in CSV data. Sanitization retains only ASCII alphanumeric characters (`A`-`Z`, `a`-`z`, and `0`-`9`) and underscore; it removes punctuation such as `-`, `@`, and `.`, as well as non-ASCII letters and digits. An empty result becomes `empty`. Thus partitioning value `雪山川` with `--prefix-length 2` creates `empty.csv`, while preserving the complete value `雪山川` in that file's CSV row. Distinct values that sanitize to the same name must never overwrite or merge: allocate `<name>.csv`, then `<name>_1.csv`, `<name>_2.csv`, and so on in encounter order.

`--filename TEMPLATE` supplies a relative template containing exactly one `{}`, replaced by the sanitized partition name. It may include subdirectories such as `{}/data.csv`, which must be created beneath `outdir`. The same exact-one-placeholder validation and error text used by `split` applies.

## Spec 27: Scale and fidelity requirements

Behavior is defined over parsed records and raw field bytes, not by simplistic line splitting or UTF-8-only string handling. Commands must comfortably handle at least tens of thousands of rows, 513 columns, kilobyte-scale fields, joins of several thousand rows per side, and multi-stage Unix pipelines within ordinary command-line time limits. No command may silently truncate, deduplicate, reorder, or normalize data except where its semantics above explicitly require it.
