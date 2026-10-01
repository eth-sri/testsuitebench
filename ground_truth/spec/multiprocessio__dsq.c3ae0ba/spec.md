# Clarified specification for `executable`

## Spec 1

The delivered artifact is a directly runnable command-line program named exactly `executable`. It is a single-purpose SQL-on-data-files utility whose displayed product name is `dsq`. Unless a mode below says otherwise, a successful invocation exits with status 0, writes its result to standard output, and writes nothing to standard error. User, file, data, and SQL errors exit with status 1 (or, where only nonzero is stated, any nonzero status), put the diagnostic on standard error, and do not put a result on standard output. All text is UTF-8 and ordinary noninteractive output ends in exactly one newline. The executable must comfortably count at least 10,000 CSV rows, process 1,000 rows in each supported binary format, return and format at least 100 wide real-world rows, handle 50 columns, and execute long SQL expressions within a few seconds.

## Spec 2

The command syntax is flag-and-positional based; there are no subcommands. Supported flags, which may occur before, among, or after data-file arguments, are:

- `-h`, `--help`
- `-v`, `--version`
- `-p`, `--pretty`
- `-s TYPE`, `--stdin TYPE`
- `-f SQLFILE`, `--file SQLFILE`
- `-c`, `--schema`
- `-D`, `--cache-file`
- `-n`, `--convert-numbers`
- `-i`, `--interactive`
- `--verbose`
- `--no-sqlite-writer`

Words such as `add`, `remove`, `list`, `show`, `query`, `execute`, `run`, `init`, `config`, `help`, and `version` have no special subcommand meaning; as bare positional arguments they are data filenames. Unrecognized flags are likewise treated as filenames rather than rejected as options. `--` is not an end-of-options separator and normally becomes a filename, although a `--help` appearing anywhere, even after `--`, takes precedence and displays help successfully. A final positional argument containing whitespace is recognized as an inline SQL query only when there is an earlier data source. With no earlier source, even query-looking text remains a filename: `executable "SELECT 1"` exits 1 with empty stdout and stderr exactly `Unknown mimetype for file: SELECT 1.\n`. A final token such as `select1` is likewise a filename. A normal form is `executable [flags] FILE... "SELECT ..."`.

## Spec 3

`--help` exits 0, writes nothing to stdout, and writes the following bytes to stderr exactly (including spacing, blank lines, backslash continuation, and one final newline, but no ANSI escapes):

```text
dsq (Version latest) - commandline SQL engine for data files

Usage:  dsq [file...] $query
        dsq $file [query]
        cat $file | dsq -s $filetype [query]
        dsq $file -f $queryfile

dsq is a tool for running SQL on one or more data files. It uses
SQLite's SQL dialect. Files as tables are accessible via "{N}" where N
is the 0-based index of the file in the commandline.

The shorthand "{}" is replaced with "{0}".

Examples:

    # This simply dumps the CSV as JSON
    $ dsq test.csv

    # This dumps the first 10 rows of the parquet file as JSON.
    $ dsq data.parquet "SELECT * FROM {} LIMIT 10"

    # This joins two datasets of differing origin types (CSV and JSON).
    $ dsq testdata/join/users.csv testdata/join/ages.json \
          "select {0}.name, {1}.age from {0} join {1} on {0}.id = {1}.id"

See the repo for more details: https://github.com/multiprocessio/dsq
```

The help contains no commands/subcommands listing. Help wins over otherwise invalid extra arguments. The `-h` form also exits 0 and emits help on stderr containing the `dsq` banner and `Usage:` section; it is the short help form.

## Spec 4

`--version` exits 0, writes nothing to stdout, and writes exactly `dsq latest` followed by one newline to stderr. The `-v` form also exits 0 and emits a short stderr version string containing `dsq` and `latest`, without usage text. In particular, `-v` means version, not verbose.

## Spec 5

Each input source is imported as an SQL table. File sources are numbered in their positional order as `{0}`, `{1}`, and so on; `{}` is an exact shorthand for `{0}`. If stdin is enabled it is the first source (`{0}`), and following files begin at `{1}`. Placeholder occurrences may be used in table-qualified column references, aliases, joins, subqueries, CTEs, and repeated references. Repeating the same physical file as two positional sources creates two independently referenceable tables.

With one ordinary, flat top-level tabular file and no query, the utility performs a direct conversion/dump rather than requiring SQL; its result is equivalent in content to `SELECT * FROM {}`. Direct JSON dumping occurs before the flattening used for SQL import: a top-level array of row objects retains nested objects in those rows. For example, dumping `[{"a.b":1,"a":{"b":2}}]` preserves that same nested JSON content rather than producing two flattened scalar fields. A top-level structured object that is not itself an array, such as a multi-sheet workbook or an object containing nested collections, is likewise dumped as its original object structure when no query is given. Providing no source at all is an error as specified later.

## Spec 6

Default query and tabular-dump output is a JSON array of row objects. It is compact but places each row after the first on a new line: the opening `[` immediately precedes row 1, rows are separated by `,\n`, and `]` plus `\n` closes the value. There are no spaces added around JSON punctuation. An empty result is exactly `[]\n`. For example, selecting only `name` from rows Ted, Marjory, and Micah and ordering by name produces exactly:

```text
[{"name":"Marjory"},
{"name":"Micah"},
{"name":"Ted"}]
```

Strings, numbers, booleans, and SQL NULL are emitted as JSON string, number, boolean, and `null` respectively. Unicode is emitted intact (not corrupted or ASCII-escaped), while quotes, tabs, embedded newlines, and other JSON-sensitive content are correctly escaped. Result row order follows SQL; all selected columns appear with their SQL result names/aliases. Object key order is not semantically significant.

## Spec 7

`-p`/`--pretty` changes row output to an ASCII table and leaves stderr empty. Pretty mode sorts result columns lexicographically by their exact, untrimmed names, independently of SELECT/source order; thus leading-space names sort first and `col10` sorts between `col1` and `col2`. Header whitespace and tabs remain part of the displayed name. It uses `+`, `-`, and `|` borders, one space of horizontal padding, centers headers, left-aligns textual cells, right-aligns numbers and numeric-looking strings, and appends `(1 row)` or `(N rows)` on its own line. All output has a final newline. For the rows `{id: "1", name: "Alice", value: "100"}` through ids 2 and 3/Bob 200/Charlie 300, the exact result is:

```text
+----+---------+-------+
| id |  name   | value |
+----+---------+-------+
|  1 | Alice   |   100 |
|  2 | Bob     |   200 |
|  3 | Charlie |   300 |
+----+---------+-------+
(3 rows)
```

Column content width is capped at 30 display columns. Longer text wraps at word boundaries without truncation; explicit newlines also create continuation lines. Other cells on continuation lines are blank. UTF-8 display width must preserve alignment. Combining pretty and schema selects human-readable pretty-schema mode, not a data table.

## Spec 8

`-c`/`--schema` reports the inferred schema of the eventual result (after applying the query, if any) instead of rows. Without `--pretty`, it writes indented two-space JSON with this recursive vocabulary: an array is `{"kind":"array","array":...}`, an object is `{"kind":"object","object":{field: definition,...}}`, and a scalar is `{"kind":"scalar","scalar":"string|number|boolean"}`. Finer numeric types collapse to `number`. For a CSV with string columns `id`, `name`, and `value`, the exact output is:

```json
{
  "kind": "array",
  "array": {
    "kind": "object",
    "object": {
      "id": {
        "kind": "scalar",
        "scalar": "string"
      },
      "name": {
        "kind": "scalar",
        "scalar": "string"
      },
      "value": {
        "kind": "scalar",
        "scalar": "string"
      }
    }
  }
}
```

For an empty query result, output exactly the same indented form as `{"kind":"array","array":{"kind":"unknown"}}` would have, ending in one newline. Numeric computed/aggregate columns infer as `number`. With `--pretty`, alphabetically sorted object fields use this exact tree style:

```text
Array of
  Object of
    id of
      string
    name of
      string
    value of
      string
```

## Spec 9

CSV uses its first record as exact column names and RFC-4180-style parsing: quoted commas, doubled quote escapes, embedded newlines, empty fields, tabs, Unicode, and long cells are preserved. Header whitespace and tabs are significant and must not be trimmed or normalized. Every CSV field, including numeric-looking and `true`/`false` text, is a string by default; empty fields are empty strings. TSV (`.tsv` and `.tab`) has the same semantics with tab separators. Header-only or empty file input cannot produce an SQL table and a query against it fails with `no such table: t_0`; empty stdin without a query may instead dump `[]`.

## Spec 10

Formats are selected from a file's conventional extension, or from the type supplied for stdin. Required structured-text formats are JSON (`.json`, `application/json`), JSON Lines/NDJSON (`.jsonl`, `.ndjson`, `application/jsonlines`), and YAML (`.yaml`, `.yml`, `application/yaml`). JSON must be a nonempty top-level array of objects when imported as a table; a single object, empty array, or array of primitives is not a queryable table. JSON Lines treats each JSON object as one row and accepts a one-line file. YAML arrays of mappings become rows. These formats preserve native string, number, boolean, and null JSON result types. On SQL import, a JSON numeric token is stored using SQLite's `real` storage class even when its lexical value is integral: for an `age` token of `56`, `TYPEOF(age)` is `real`, and `(age * 2 + 10) / 3 - 5` emits `35.666666666666664`. JSON and JSONL containing equivalent records must yield the same types and row counts.

## Spec 11

Nested objects in row data are recursively flattened for SQL import to scalar columns joined with dots, for example `{"name":"A","location":{"city":"Toronto","address":{"number":1002}}}` becomes columns `name`, `location.city`, and `location.address.number`. Such column names are referenced as SQL quoted identifiers, e.g. `"location.address.number"`. A dot that occurs literally in an input key is not escaped. Consequently, a literal key `a.b` collides with the flattened path produced by nested `{"a":{"b":...}}`; importing `[{"a.b":1,"a":{"b":2}}]` for a query exits 1 with empty stdout and stderr exactly `duplicate column name: a.b\n`. A whole nested object is not a scalar/queryable cell. Nested arrays are serialized as compact JSON strings when imported; SQLite JSON operators can then inspect them. In particular, if column `c` contains `[1,2]`, `c->1` yields the text value `"2"` in JSON output, while selecting `c` returns the string `[1,2]`.

When the array of objects is nested inside a top-level object, a table placeholder can carry an object-only dotted path: `{0, 'data.data'}`, `{0, "data.data"}`, or, for the first source, shorthand `{'data.data'}`/`{"data.data"}`. Single and double path quotes are equivalent. For `{ "data": { "data": [{"id":1}], "data2": [{"id":2}] } }`, the first path selects the id-1 array and the second selects the id-2 array. Paths cannot traverse arrays.

## Spec 12

Spreadsheet support includes `.xlsx` and `.ods`. A single tabular sheet uses the first row as exact string headers, returns spreadsheet booleans as the strings `TRUE`/`FALSE`, and renders date cells consistently as `MM-DD-YY` strings (for example `10-18-21`). Ordinary numeric XLSX and ODS cells are converted to decimal text, not JSON/SQLite numeric values: XLSX numbers 7 and 8 dump as `"7"` and `"8"`, and an ODS float cell with displayed value 2 is returned as `"2"`; `TYPEOF` reports `text` for these imported cells. A workbook with multiple sheets is represented, when dumped without a query, as a JSON object mapping sheet names to arrays of row objects, with numeric cells still represented as strings. A sheet is selected for SQL by the same path syntax, such as `{0, "Sheet2"}`. The supplied multi-sheet style of workbook must expose `Sheet1` and `Sheet2`; selecting Sheet2 must operate on all of its rows (the tested workbook's `COUNT(1)` is 682).

## Spec 13

Parquet input preserves booleans and floating-point values rather than converting everything to strings, and physical INT64 routing/timestamp values are emitted as whole JSON numbers. It must decode the supplied Parquet conventions for unusual column names: encoded spaces remain represented by names such as `PARGO_PREFIX_32Name32`, `Routing32Number323232`, and `Created32At32`. Despite their integral-looking JSON representation, both of those INT64 columns are imported with SQLite storage class `real`: for values `100998` and `1600000998`, `TYPEOF(Routing32Number323232)` and `TYPEOF(Created32At32)` both return `real`. Queries, selection, counting, LIMIT/OFFSET, schema inference, and no-query dumps work as for other tables. The representative dataset size is 1,000 rows.

## Spec 14

Apache ORC (`.orc`, type `orc`) and Avro object-container (`.avro`, type `application/avro`) are queryable and dumpable. ORC without source field metadata exposes columns `_col0`, `_col1`, etc., emits numeric cells as JSON numbers, preserves empty strings distinctly from NULL, and supports at least 1,000 rows plus LIMIT/OFFSET. An ORC LONG is nevertheless imported with SQLite storage class `real`: in the 1,000-row representative layout, `_col1` is the 1-based row id, values 999 and 1000 emit as JSON numbers, and `TYPEOF(_col1)` returns `real`. In that layout `_col0` is an ORC STRING containing `2020-09-13 12:26:40`, which is returned unchanged, and empty union-like textual fields remain `""`. A timestamp-typed ORC value is rendered in UTC RFC 3339 form; the first `_col0` value in the supplied `test_data.orc` is exactly `2016-02-03T07:55:29Z`.

Avro uses schema field names, and fields declared directly as scalar types retain their native values. A selected non-null union branch is instead serialized into a compact JSON string whose outer key is the Avro branch name. Thus a `string` branch whose value is `yes` is returned as the string `{"string":"yes"}`, while a record branch named `long_wrapper` with field `long` is returned as the string `{"long_wrapper":{"long":6759521864920116}}`. A null union branch becomes SQL/JSON null. Queries and schema inference must handle these union fields without failure.

## Spec 15

Logfmt (`.logfmt`, type `text/logfmt`) is parsed one line per row as whitespace-separated `key=value` pairs with quoted-value support. Quotes surrounding values are removed, embedded spaces remain part of the value, and all values are strings. The row schema is the union of keys across lines; a key absent on a line is SQL NULL rather than an omitted query result field. As a concrete contract, lines containing `level=debug ... animal=walrus number=8` and `level=panic ... animal=orca size=9009` must yield those exact string values, and quoted `msg="Started observing beach"` yields `Started observing beach`.

## Spec 16

SQL behavior follows SQLite semantics for the covered subset. It is case-insensitive for SQL keywords and unquoted column-name lookup, while preserving the declared/result column spelling. Double quotes allow identifiers containing spaces, tabs, numeric names, dots, or reserved words. Single quotes create strings and doubled single quotes escape apostrophes. Column aliases with and without `AS`, table aliases, `*`, scalar literals, and selected expressions are supported. WHERE supports `=`, `!=`/`<>`, `<`, `<=`, `>`, `>=`, `IS NULL`, `IS NOT NULL`, AND, OR, NOT, parentheses, LIKE/NOT LIKE (`%` and `_`), GLOB, IN, BETWEEN, and EXISTS. SQLite affinity/coercion behavior applies; CSV text compares lexically unless explicitly cast or number conversion was enabled.

## Spec 17

Expressions support integer/real arithmetic `+ - * / %`, parentheses and normal precedence, and string concatenation with `||`. Required scalar functions are `ABS`, `ROUND` (with optional precision), `LENGTH`, `UPPER`, `LOWER`, `SUBSTR`, `REPLACE`, `TRIM`, `COALESCE`, `IFNULL`, `NULLIF`, `TYPEOF`, `HEX`, `RANDOM`, `DATE`, and `DATETIME`. `CAST(... AS INTEGER|REAL|TEXT)` follows SQLite behavior, including conversion of nonnumeric text to integer zero rather than crashing. CASE supports searched branches, multiple WHEN clauses, ELSE, nesting, expressions, and aggregates. JSON extraction operators/functions used by SQLite must operate on JSON strings.

## Spec 18

Aggregation supports `COUNT(*)`, `COUNT(expr)`, `SUM`, `AVG`, `MIN`, and `MAX`, including several aggregates in one SELECT. GROUP BY accepts one or multiple expressions and works with aliases; HAVING filters grouped aggregate results and may refer to an aggregate alias. Aggregation composes with WHERE, ORDER BY, CASE, joins, nested flattened columns, and stdin. Numeric aggregate results are JSON numbers. Grouping without an aggregate is valid. As a calibration example, ages 88, 56, and 33 have count 3, sum 177, min 33, max 88, and average 59.

## Spec 19

ORDER BY supports one or more expressions, ASC/DESC, aliases, and computed columns. LIMIT supports zero, positive values, and `LIMIT n OFFSET m`; LIMIT 0 returns `[]`, and a negative limit means no upper limit. Bare OFFSET without LIMIT is a syntax error. DISTINCT removes duplicate result rows. Set operations `UNION` (deduplicating), `UNION ALL`, `INTERSECT`, and `EXCEPT` work with repeated references to an imported table and retain SQLite ordering semantics.

## Spec 20

Multi-source SQL supports comma/cross joins, INNER/JOIN, and LEFT JOIN with ON conditions. Tables may come from different formats and may be aliased. Placeholder-qualified identifiers such as `{0}.name` and `{1}.age` must resolve correctly after placeholder rewriting. Cross products, self-joins, two- and three-way joins, and multiple LEFT JOINs work. Ambiguous unqualified columns in a join produce `ambiguous column name: NAME`. A canonical join of CSV users `(1,Ted),(2,Marjory),(3,Micah)` with JSON ages `(1,88),(2,56),(3,33)` returns the three matching names and numeric ages.

## Spec 21

Subqueries work in WHERE/IN/EXISTS, as scalar SELECT expressions, as correlated queries with outer aliases, and nested inside one another. Common table expressions support `WITH`, multiple CTEs, and `WITH RECURSIVE`; a recursive counter from 1 through 5 yields five rows. Window functions include `ROW_NUMBER() OVER (ORDER BY ...)` and `RANK() OVER (...)`. These constructs must compose with aggregate queries, aliases, table placeholders, UNION ALL, joins, and computed ordering.

## Spec 22

In addition to built-in SQLite behavior, provide these tested extensions:

- The binary `REGEXP` operator uses regular-expression matching; `name REGEXP '^M'` matches names beginning with M, and `A.*` matches `Agarrah`.
- Aggregate `mode(value)` returns the most frequent value; on a boolean-like Activated column whose majority is true it returns numeric 1.
- `url_host(url)` extracts the hostname without scheme/path/query; `url_host('https://age.com/x?k=1')` is `age.com`.
- `split_part(text, delimiter, index)` splits text, with a negative index counting from the end; `split_part('age.com', '.', -1)` is `com`.

Unknown functions fail with `no such function: FUNCTION_NAME`.

## Spec 23

`-s TYPE` and `--stdin TYPE` read all standard input as a data source. TYPE accepts the supported extension-style names and MIME names, but it is not validated against only that supported-name set; its value is mandatory. In particular, supplying the bytes `anything` to `--stdin not/a-type` exits 0, writes exactly `"anything"\n` to stdout, and leaves stderr empty. Parsing, types, nesting, SQL, dumping, pretty/schema output, and errors otherwise match file input. CSV/TSV stdin values are strings by default; JSON/JSONL stdin retains native types. Stdin can be used alone or joined with any number of file sources and is always source 0. Empty CSV stdin with no query emits `[]\n`; header-only CSV stdin followed by a table query fails because table `t_0` was not created.

## Spec 24

`-f PATH`/`--file PATH` selects a SQL text file instead of an inline query. It works regardless of whether the flag occurs before or after data sources and combines with stdin and multiple files. Read the entire UTF-8 file, allowing multiline SQL, leading/trailing blank lines, trailing semicolons, and ordinary SQL whitespace, then perform normal placeholder replacement and execution. The query-file path is not a data source. A zero-byte SQL file is rejected rather than treated as a dump. Inline and file queries have identical output and semantics.

## Spec 25

CSV and TSV automatic number conversion is disabled by default. `-n`, `--convert-numbers`, or environment variable `DSQ_CONVERT_NUMBERS=true` enables it during import and during no-query dumps; `DSQ_CONVERT_NUMBERS=false` and an absent variable disable it. Each cell is converted independently: signed decimal integer text becomes a JSON/SQLite integer and decimal numeric text becomes a real; nonnumeric text remains a string. Leading zeros and a leading plus are accepted and normalized: `1`, `+1`, `01`, and `001` become integer 1, while `1.1` and `0001.1` become real 1.1. `0`, `00`, `+0`, `-0` become integer 0; `0.0` and `00.00` become real 0.0. Mixed numeric/text columns are allowed. Telephone numbers, ZIP-like strings with nonnumeric syntax, dates, and digit-containing general text remain strings. Conversion affects SQL affinity and ordering as well as JSON output.

## Spec 26

`DSQ_CONVERT_NUMBERS` controls number conversion as described above. `--no-sqlite-writer` and `DSQ_NO_SQLITE_WRITER=true` select a compatibility import path but must not change query results; the command-line flag still enables the mode if that environment variable is `false`. `--verbose` leaves stdout as the normal result and emits informational logging on stderr containing the literal prefix `[INFO]`.

## Spec 27

`-D`/`--cache-file` computes a content-addressed cache filename for the supplied source set, suppresses data/query output, prints only that path on stdout, and exits 0. The basename contains `dsq-cache-` and ends in `.db`. A successful cache-path invocation also writes exactly `Cache invalid, re-import required.\n` to stderr; this applies to both flag spellings and when `--cache-file` trails a source and inline query. Cache identity depends on source contents rather than just the path: repeated invocations for unchanged bytes print the same path, while invoking the option for the same filename after changing its bytes prints a different path. Each of these invocations emits the same cache-invalid stderr line.

## Spec 28

`-i`/`--interactive` with a file and an actual terminal starts a REPL only when that source content has not already populated its content-addressed cache. On that first import it displays the exact prompt `dsq> `. Each entered SQL line runs with the same placeholder/SQLite semantics and prints a pretty table before prompting again. For example, `SELECT * FROM {} LIMIT 2` shows only the first two rows and ends its table with `(2 rows)`. Empty or whitespace-only lines are silently ignored and re-prompt.

The exact command `exit` prints text containing `bye` and exits 0. Entered queries are persisted in `$HOME/dsq_history` (create the file if necessary). If `--interactive` is invoked with captured/non-TTY stdin, it exits nonzero instead of waiting indefinitely.

If the same source content has already populated the cache, interactive startup attempts to import into the existing table and fails before displaying a prompt or accepting any query. It exits with status 1, the terminal receives exactly `table "t_0" already exists\n` (subject to the terminal's normal newline translation), and `$HOME/dsq_history` is not created. This cached-startup failure takes precedence even when input containing a blank line, a query, and `exit` has already been written to the terminal.

## Spec 29

Argument and input diagnostics are stable:

- No positional arguments and no stdin source: stderr exactly `No input files.\n` and nonzero status. A sole query-looking positional argument is instead classified as a filename as specified in Spec 2.
- `-s`/`--stdin` without its value: exactly `Must specify stdin mimetype.\n`.
- `-f`/`--file` without its value: exactly `Must specify a SQL file.\n`.
- Empty SQL file: exactly `SQL file is empty.\n`.
- Missing SQL file: begins `Error opening sql file: open PATH: no such file or directory`.
- Missing recognized-format input: contains `open PATH: no such file or directory`.
- Unknown extension/type or unknown option-as-filename: `Unknown mimetype for file: PATH.` (the final period is required).
- A validly parsed but non-tabular JSON value, empty JSON array, or array of primitives: contains `Input is not an array of objects: PATH`.
- Invalid JSON syntax includes the underlying parse phrases such as `invalid character` and `looking for beginning of value`.

When several files are missing, report the first positional one. All data sources are validated/imported even if the SQL only references an earlier table.

## Spec 30

SQL execution errors expose concise SQLite-style diagnostics on stderr without a traceback. Required exact messages (before the final newline) include: `incomplete input` for unfinished FROM/WHERE/GROUP BY; `near "FROM": syntax error` for `SELECT FROM WHERE`; `near "INVALID": syntax error` for `INVALID QUERY`; `no such column: NAME`; `no such function: NAME`; `ambiguous column name: id`; and `table sqlite_master may not be dropped` for an attempted `DROP TABLE sqlite_master`. A malformed placeholder fragment such as `select * from {` reports text containing `unrecognized token`. An out-of-range placeholder such as `{1}`, `{5}`, or `{999}` is rewritten to an absent/empty table reference and fails with `no such table:`. Invalid joins, bare OFFSET, malformed quotes, and nonexistent ORDER BY columns also exit 1 with a nonempty SQLite-style message. Valid edge cases remain successful: empty result sets are `[]`, GROUP BY without aggregates works, negative LIMIT returns all rows, self-referential subqueries work, duplicate input tables may form a cross product, and files/queries containing Unicode, embedded CSV newlines, unusual headers, long expressions, or large row counts do not crash.
