# Clarified executable specification

## Spec 1

The required artifact is a directly runnable command-line program named exactly `executable`. It behaves as a single-command `trdsql`-compatible utility: its non-option arguments form an SQL query, text files named as SQL tables are loaded into a temporary relational database, the SQL is evaluated, and result rows are serialized. There are no subcommands. Unless another destination is selected, successful query data is written to standard output; diagnostics are written to standard error. Ordinary success returns status 0, an input/database/output failure returns status 1, and command-line usage/flag parsing failure returns status 2. A successful non-debug invocation emits nothing on standard error. Every nonempty line-oriented output ends in a newline unless a format definition below explicitly says otherwise.

`-version` must return 0, write exactly `trdsql version devel\n` to standard output, and leave standard error empty. `--version` is also accepted, returns 0, and writes a line beginning `trdsql version` to standard output.

## Spec 2

With `--help`, `-help`, no query, or a single empty query argument, print the following help text exactly to standard error, print nothing to standard output, and return status 2. `--help` takes precedence over otherwise valid flags; an unknown flag accompanying it may still cause status 2 but usage must be shown. The special short flag `-h` prints nonempty help to standard error and returns 0.

```text
trdsql - Execute SQL queries on CSV, LTSV, JSON, YAML and TBLN.

Usage
	trdsql [OPTIONS] [SQL(SELECT...)]

Options:
  -A string           analyze the file but only suggest SQL.
  -a string           analyze the file and suggest SQL.
  -config string      configuration file location.
  -db string          specify db name of the setting.
  -dblist             display db information.
  -debug              debug print.
  -driver string      database driver.  [ mysql | postgres | sqlite3 | sqlite3_ext ]
  -dsn string         database driver specific data source name.
  -help               display usage information.
  -q string           read query from the specified file.
  -t string           read table name from the specified file.
  -version            display version information.

Input Formats:
  -icsv               CSV format for input.
  -ig                 guess format from extension. (default "true")
  -ijson              JSON format for input.
  -iltsv              LTSV format for input.
  -itbln              TBLN format for input.
  -itext              text format for input.
  -iwidth             width specification format for input.
  -iyaml              YAML format for input.

Input options:
  -id string          field delimiter for input. (default ",")
  -ih                 the first line is interpreted as column names(CSV only).
  -ijq string         jq expression string for input(JSON/JSONL only).
  -ilr int            limited number of rows to read. (default 0)
  -inull value        value(string) to convert to null on input.
  -inum               add row number column.
  -ir int             number of rows to preread. (default 1)
  -is int             skip header row. (default 0)

Output Formats:
  -oat                ASCII Table format for output.
  -ocsv               CSV format for output.
  -ojson              JSON format for output.
  -ojsonl             JSON lines format for output.
  -oltsv              LTSV format for output.
  -omd                Markdown format for output.
  -oraw               Raw format for output.
  -otbln              TBLN format for output.
  -ovf                Vertical format for output.
  -oyaml              YAML format for output.

Output options:
  -oaq                enclose all fields in quotes for output.
  -ocrlf              use CRLF for output. End each output line with '\r\n' instead of '\n'.
  -od string          field delimiter for output. (default ",")
  -oh                 output column name as header.
  -onowrap            do not wrap long lines(at/md only).
  -onull value        value(string) to convert from null on output.
  -oq string          quote character for output. (default "\"")
  -out string         output file name.
  -out-without-guess  output without guessing (when using -out).
  -oz string          output compression format. [ gz | bz2 | zstd | lz4 | xz ]

Examples:
  $ trdsql "SELECT c1,c2 FROM test.csv"
  $ trdsql -oltsv "SELECT c1,c2 FROM test.json::.items"
  $ cat test.csv | trdsql -icsv -oltsv "SELECT c1,c2 FROM -"
```

## Spec 3

Recognize all flags displayed in Spec 2, using `-flag value` for valued flags; `-ig=false` is the tested assignment form that disables extension guessing. Boolean flags consume no following token: for example `-ig false` treats `false` as the positional SQL text, which subsequently produces a status-1 SQL syntax error. Integer flags reject non-integers during parsing. A missing value for `-out`, `-ilr`, `-ir`, `-is`, `-driver`, or `-oz` returns 2 and includes `flag needs an argument`; an invalid integer includes `invalid value "VALUE" for flag -FLAG` and `parse error`; an invalid `-ig=VALUE` includes `invalid boolean value "VALUE" for -ig` and `parse error`. Unknown and combined flags return 2, contain `flag provided but not defined: -NAME`, and show usage.

`--` ends option parsing. All remaining arguments are positional even if they begin with `-`. Positional arguments are joined with one space to make the SQL, so `"SELECT * FROM"` and a path supplied as the next process argument work. The input `-- --help` is therefore an SQL comment rather than help; it succeeds silently. Options may occur in any order before positional SQL begins.

## Spec 4

There are three ways to obtain the operation, in this precedence order. If `-t FILE` is present, execute the equivalent of `SELECT * FROM FILE`; this conversion mode takes precedence over `-q` and positional SQL. Otherwise, if `-q FILE` is present, read the complete SQL text from that file and use it instead of positional SQL. Otherwise use the joined positional arguments. A query-file path is resolved from the process working directory, not relative to the query file itself. A missing query file is a status-1 error containing `ERROR: open PATH: no such file or directory`.

SQL may be lower-, upper-, or mixed-case. Preserve the selected column order, aliases, row order produced by SQL, duplicate rows unless SQL removes them, and all result-set column names. `-oh` uses those result names, including aliases and computed-expression names.

## Spec 5

The default engine implements SQLite-compatible SQL for the tested subset. It must evaluate SELECTs without tables (`SELECT 1`, arithmetic such as `SELECT 1+2`, and aliased literals), `*`, qualified `table.*`, explicit columns, string and numeric literals, parentheses, column/table aliases with or without `AS`, arithmetic `+ - * /`, concatenation `||`, and searched `CASE WHEN ... THEN ... ELSE ... END`. Support `CAST(... AS INTEGER|REAL|TEXT)`, preserving signed 64-bit integer precision; SQLite-style overflow must not crash.

Support the scalar functions `UPPER`, `LOWER`, `LENGTH`, `SUBSTR`, `COALESCE`, `NULLIF`, `datetime`, and SQLite JSON functions including `JSON_EXTRACT`. Support `ROW_NUMBER() OVER (ORDER BY ...)`. Date/time results use SQLite formatting, such as `YYYY-MM-DD HH:MM:SS` for `datetime(...)`.

## Spec 6

Implement SQLite comparison and filtering semantics for `=`, `!=`, `<>`, `<`, `<=`, `>`, `>=`, `AND`, `OR`, `IN`, `NOT IN`, `BETWEEN` (inclusive), `NOT BETWEEN`, `LIKE`, `NOT LIKE`, `IS NULL`, and `IS NOT NULL`. LIKE uses SQLite's ordinary ASCII case-insensitive behavior and `%`/`_` wildcards. SQL NULL follows three-valued logic. Empty text remains distinct from SQL NULL unless input null conversion was requested.

Implement `ORDER BY` on one or several expressions, independently honoring `ASC` and `DESC`; `LIMIT n`, `LIMIT n OFFSET m`, and SQLite's `LIMIT m,n` form; and `DISTINCT`. Sorting and comparisons operate on the engine values, so explicit numeric casts give numeric rather than lexical behavior.

## Spec 7

Implement `COUNT(*)`, `COUNT(expr)`, `COUNT(DISTINCT expr)`, `SUM`, `AVG`, `MIN`, and `MAX`, including several aggregates in one SELECT. Aggregates ignore SQL NULL where SQLite does; a grouped or ungrouped `AVG` ignores NULL values. Implement `GROUP BY` on one or more expressions and post-aggregation `HAVING`. Support scalar and correlated-free subqueries in `FROM` and `WHERE`, including nested SELECTs and `IN (SELECT ...)`.

Implement `UNION` with duplicate removal and `UNION ALL` with duplicates retained. A missing table or invalid column in any arm is an error rather than a partial result.

Aggregate numeric values retain their engine value but use the shortest faithful spelling at serialization. In particular, JSON renders an integral-valued `AVG`, `MIN`, or `MAX` as an integer literal (`30`, `4`) rather than adding `.0`, while a nonintegral result such as `2.35` retains its fractional part.

## Spec 8

All distinct file table references in `FROM`, comma joins, explicit `JOIN`/`INNER JOIN`/`LEFT JOIN`/`CROSS JOIN`, and nested subqueries must be imported before evaluation. Support join aliases and `ON` conditions, same-file self joins, cross-format joins, Cartesian products, and left-join NULLs. File names are the temporary table names visible to SQL.

Multiple SQL statements separated by semicolons execute sequentially in one database session and each SELECT is serialized as soon as it succeeds, in statement order. If a later statement fails, output already emitted by earlier SELECTs remains on standard output; for example `SELECT a FROM d.csv; SELECT missing FROM d.csv` on a headered one-row `a` table emits `1\n`, then returns status 1 and reports ``export: no such column: missing [SELECT missing FROM `d.csv`]``. Support UPDATE and DELETE against an imported file table followed by SELECT, so the later SELECT observes the modification. No output is emitted for a non-query statement. Splitting must not treat semicolons inside SQL quoted strings as separators.

## Spec 9

A table token can be a relative path, absolute path, extensionless name, or a path enclosed in SQL double quotes or backticks. Quoting permits spaces, hyphens, and punctuation. A leading `~` is not expanded to the current user's home: the unquoted query `SELECT * FROM ~/home.csv` returns status 1 with `export: near "~": syntax error [SELECT * FROM ~/home.csv]`. Preserve quoted identifiers and correctly distinguish SQL keywords from paths after clauses such as `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT`, and joins. Column names that are SQL keywords or contain spaces, punctuation other than a backtick, percent signs, or Unicode are usable when SQL-quoted. A literal backtick in a CSV header is not escaped during temporary-table creation: importing the header ``select,full name,率,,tick`x`` returns status 1 with ``import: unrecognized token: "` text );"``. Duplicate input column names are rejected with an error containing `duplicate column name: NAME`; blank CSV header fields are assigned safe generated field names such as `f2`.

The table names `-`, `stdin`, and `STDIN` read standard input. Stdin must work with ordinary query, joins where applicable, headers, and explicit input formats. A literal file named with spaces must work when quoted. Missing literal files fail; do not silently create them.

## Spec 10

Unquoted glob metacharacters in a file-table token are expanded. A single glob represents one logical table whose rows are the concatenation of all matching files in lexical path order. With `-ih`, the first matched file's header establishes the schema and is removed; a later matched file's apparent header is treated as an ordinary data row. A no-match glob returns status 1 with no standard output and is diagnosed as a missing table rather than as a syntax error: `SELECT * FROM none/*.csv` produces a timestamped standard-error line ending exactly `export: no such table: none [SELECT * FROM none/*.csv]`. Globs can include compressed and uncompressed files. Separately named files in joins remain separate tables.

## Spec 11

Input format is selected by an explicit input flag when present. Where several explicit input flags conflict, use this fixed preference sufficient for tested cases: CSV takes precedence over JSON. Otherwise, with guessing enabled (the default), repeatedly strip a recognized compression suffix and inspect the remaining case-insensitive extension: `.json` and `.jsonl` select JSON; `.ltsv` selects LTSV; `.yaml` and `.yml` select YAML; `.tbln` selects TBLN; `.tsv` selects CSV with tab delimiter; `.psv` selects CSV with pipe delimiter; and `.text` selects TEXT. Unknown extensions (including ordinary `.txt`) and absent extensions fall back to CSV. `-ig=false` plus an explicit format must use the explicit format.

The flags are `-icsv`, `-ijson`, `-iltsv`, `-iyaml`, `-itbln`, `-iwidth`, and `-itext`. A selected format applies to all files represented by the same logical input option, except ordinary automatic guessing allows separately referenced joined files to have different formats.

## Spec 12

Before parsing content, detect and decompress exactly one input compression layer from magic bytes, not merely the filename. Support gzip (header `1f 8b`), bzip2 (`BZh`), XZ (`fd 37 7a 58 5a 00`), Zstandard frame (`28 b5 2f fd`), and LZ4 frame (`04 22 4d 18`). This applies to files and stdin. Compound names such as `.json.gz`, `.yaml.gz`, and `.tsv.bz2` retain the underlying format inference. A valid compressed stream containing no uncompressed rows fails like the corresponding empty input. Do not recursively decompress: after one layer, nested compressed bytes are passed to the selected reader as data.

Output compression is selected by `-oz`, accepting `gz` or `gzip`, `bz2`, `zstd`, `lz4`, and `xz`, and must produce standard interoperable streams with the magic bytes above. If `-out` has a compression suffix, infer compression from it. An explicit `-oz` overrides the filename. Compression applies to stdout as raw bytes or to the destination file after serialization.

## Spec 13

CSV input follows ordinary RFC-4180-style record parsing: default comma delimiter, double-quoted fields, doubled quotes as an embedded quote, delimiters/newlines inside quoted fields, CRLF/LF/mixed record endings, blank fields, Unicode, very long fields and lines. A record is not truncated at scanner-sized boundaries. Without `-ih`, every record including a header-looking first row is data and columns are named `c1`, `c2`, ... according to the discovered width. With `-ih`, the first non-skipped record supplies exact column names and is not data. Numeric-looking CSV fields remain SQL text until cast.

`-id VALUE` changes CSV input delimiter. Interpret Go-style escapes such as `\t`, `\n`, and `\xNN`; the decoded delimiter must be exactly one character. Literal `;`, `:`, `|`, tab, and space work. An invalid escape produces status 1 with `import: can not get separator: invalid syntax:"VALUE"`; a multi-character delimiter also fails. For a space delimiter, allow leading spaces in records. Rows shorter than the schema are padded with SQL NULL; columns beyond the schema width are ignored. Empty fields that exist in the record remain empty text unless `-inull` applies.

A wholly blank physical CSV line is ignored before header or row handling, including a terminal blank line. It does not become a short all-empty record and therefore cannot create an extra row or aggregate group. A nonblank record containing delimiters and empty fields remains an ordinary record.

## Spec 14

Apply general input options before importing rows. `-is N` discards the first N physical/logical records, before `-ih` chooses a header. It works for CSV, LTSV, TEXT, and WIDTH. If skipping runs past EOF for a nonempty CSV, return 1 and report both `ERROR: skip error EOF` and `import: no rows`. `-ilr N` limits input rows read, before SQL filtering or ordering; zero means unlimited. It combines with row numbering and normally counts data rows after a CSV header. Preserve the observed combined CSV behavior that `-ih -is 2 -ilr 2` on two skipped lines, one header, and three data lines imports all three data lines.

`-ir N` is the schema preread count. Default 1 discovers names/types/width from the first available row. Larger values union sparse JSON/YAML/LTSV keys and discover wider varying rows; values larger than the file are harmless. JSON with `-ir 0` cannot discover names and fails with `import: invalid names`. Header-based CSV still gets names from its header. Preread rows must later appear exactly once as data, in their original order.

## Spec 15

`-inum` prepends an integer row-number field to every imported row. It begins at 1 after skipping, increments before SQL filtering, survives ordering, and is included by `SELECT *`. Its preferred column name is `num`; if that collides with an existing name, choose the first free name in `num0`, `num1`, ... while keeping it the first column. In output headers its chosen name is shown. It works for CSV, JSON, YAML, LTSV, WIDTH, and TEXT and respects `-ilr`. It adds no row to an empty but schema-bearing input.

`-inull STRING` performs exact, case-sensitive, whitespace-sensitive replacement of matching scalar string or byte values with SQL NULL in every input column. An explicitly supplied empty marker converts empty strings. Native JSON/YAML null and empty TBLN cells are SQL NULL even without this option. Ordinary empty CSV/LTSV/TEXT fields are not NULL by default. `-onull STRING` converts actual SQL NULL values to that exact string at serialization; without it, delimited text formats render NULL as an empty field while JSON/YAML/TBLN retain their native rules. Literal strings such as `NULL`, `null`, `(null)`, and `nil` are not special unless exactly selected by `-inull`.

## Spec 16

LTSV input is one record per line, with tab-separated `label:value` fields. Wholly blank physical lines are skipped before record/field parsing, whether internal or terminal; they are not invalid colonless fields and do not count as data rows. A leading ASCII space at the start of a nonblank physical line is stripped before interpreting its first label: the line ` b:space` creates column `b` with value `space`, not a column named ` b`. Split each nonblank field only at its first colon, so later colons and spaces/quotes/ampersands/apostrophes remain part of the value. Labels become column names. A field without a colon is invalid; if it occurs after schema discovery, the status-1 diagnostic ends with `import: bulk read: invalid column`. Tabs embedded in a value consequently begin another field and can cause that error. On duplicate labels within a row, the last value wins. Schema comes from preread rows; absent labels in a row serialize as empty strings, while present empty values are empty strings unless `-inull ""` is requested. `-is`, `-ilr`, `-ir`, `-inum`, and Unicode preservation apply. A zero-byte LTSV file returns status 1 with `import: invalid names`.

## Spec 17

JSON input accepts a top-level array, a single top-level value, and a stream of whitespace/newline-separated top-level JSON values (JSONL). A top-level array of objects normally yields one row per object; a single nonempty object yields one row. Object keys are exact columns and nested objects/arrays are retained as structured cell values. Missing object keys and explicit `null` become SQL NULL. Keys may contain spaces, dots, dashes, quotes, and Unicode. Empty object and empty top-level array cannot establish a schema and fail with `import: invalid names`.

An array of primitive values yields one `c1` row per primitive, with primitive values represented as their text form except NULL. An array whose elements are arrays yields one row per inner array, with the complete inner array in `c1`; do not flatten it into several columns. A primitive single document is one `c1` row. Multiple top-level documents are rows in stream order. Non-null scalar numbers and booleans imported from JSON become lower-case textual SQL values (`1`, `3.14`, `true`) unless retained inside a nested structured cell; SQL casts can turn them back into numeric engine values. When a stream begins with an array as a complete top-level value followed by a differently shaped object, preserve the first array in `c1` and place NULL in `c1` for the incompatible object.

Malformed JSON returns status 1, emits no result, and retains the Go JSON parser's lowercase detail after `import: invalid JSON:`. For example, the document `not json` reports `import: invalid JSON: invalid character 'o' in literal null (expecting 'u')`; JSON-forcing a document beginning `name` reports the corresponding character detail `invalid character 'a' in literal null (expecting 'u')`; an actual newline inside a quoted JSON string reports `import: invalid JSON: invalid character '\n' in string literal`; and an unquoted object key beginning `b` reports `invalid character 'b' looking for beginning of object key string`. These errors propagate unchanged when `-inum` is active. By contrast, a truncated later value in a JSONL stream reports exactly `import: bulk read: unexpected EOF` after the timestamp, without an additional `invalid JSON:` prefix or partial output.

## Spec 18

Support a jq-compatible preprocessing expression either from `-ijq EXPR` or from a table suffix `FILE::EXPR`; the suffix form may quote EXPR with single or double SQL-level quotes. Apply jq before relational schema discovery. Required jq constructs include identity/empty expression, field paths (`.a.b`), array iteration (`.[]`), zero-based indexes (`.[0]`, `.items[1]`), pipelines, `select(...)`, comparisons, object construction/renaming (`{name: .first}`), several comma-separated results, arithmetic updates, optional lookup `?`, `// empty`, and recursive descent `..`. Each emitted object is a row; each emitted scalar is a `c1` row. This preprocessing also works for YAML.

If a jq evaluation emits an array of objects or primitives as one result (for example `.employees`), iterate that array to form rows; a direct object is one row and each directly emitted scalar is a `c1` row. Relational columns obtained from a jq-created object do not have a stable order: repeated executions of `{name: .first, plus: (.n + 1)}` were observed to make `SELECT *` emit both `plus,name` (`3,B`) and `name,plus` (`B,3`) order. Tests that require order must select the fields explicitly. The explicit `-ijq` is appended conceptually to the table name as `FILE::EXPR`, including in analysis output. Syntax/runtime errors must be diagnosed with the expression and `gojq:(EXPR)`, such as `import: unexpected EOF gojq:(.invalid[)` or `expected an array but got: object ... gojq:(.[0])`, and must not crash. Schema discovery occurs after jq preprocessing. Consequently, an expression that emits no results cannot establish names from the source document: `.missing? // empty` followed by `SELECT *` returns status 1, no stdout, and `import: invalid names`.

## Spec 19

YAML input supports a mapping as one row, a sequence of mappings as rows, scalar documents as `c1` rows, arrays as structured `c1` values where appropriate, sparse mappings, deeply nested maps/sequences, multiple `---` documents, anchors and aliases, explicit scalar tags, quoted escapes and special characters, Unicode, integer mapping keys converted to usable string column names, and `!!binary` base64 decoding. Within a double-quoted scalar, physical continuation lines are folded to spaces after indentation is removed: the three physical lines `"line1`, `  line2`, and `  line3"` import as `line1 line2 line3`, while the escape `\t` imports as an actual tab. Valid UTF-8 binary becomes text; invalid UTF-8 bytes are rendered as lower-case hex escapes with a `\x` prefix (for example byte FF becomes `\xff`). An empty mapping key is not converted to a safe column name: importing it fails nonzero when the empty identifier reaches temporary-table insertion, with a diagnostic containing `import: INSERT Prepare:` and `near ",": syntax error`.

Duplicate mapping keys return status 1 with the parser's exact location and excerpt. For the three-line sequence whose first and third mapping keys are both `name`, the diagnostic after the timestamp is `import: invalid YAML: [3:3] mapping key "name" already defined at [1:3]`, followed by the three numbered source lines, `>  3 |   name: Bob`, and a caret under that key. An unterminated double-quoted value reports `invalid YAML: [1:9] could not find end character of double-quoted text`; an unclosed flow sequence reports `invalid YAML: [2:25] sequence end token ']' not found`. Both include the parser's numbered caret excerpt and return 1.

Schema is the union of keys found in preread rows; absent keys become SQL NULL. Top-level columns follow discovered source order, but a mapping retained inside a structured cell is serialized with keys in lexical order, not YAML insertion order. Its CSV text uses JSON-like punctuation with one space after each colon and comma: a nested mapping written with `database` before `cache` therefore serializes as `{"cache": {"enabled": true, "ttl": 3600}, "database": {"host": "localhost", "port": 5432}}`. Structured arrays likewise use comma-space separators, for example `[1, 2, 3]` and `[72, 101, 108, 108, 111]`; recursively nested maps use the same colon-space rule at every depth. CSV quoting then applies normally to the resulting text.

Native null remains NULL, while an explicit empty string remains an empty string. As with JSON, non-null scalar numbers and booleans become textual SQL fields unless retained inside nested structured values; nested values remain nested through JSON/YAML output. jq behavior and the general input controls apply. An empty YAML stream fails during input/schema decoding rather than manufacturing a row.

## Spec 20

TBLN input consists of optional metadata followed by pipe rows. Recognize `; name: | n1 | n2 |` and `; type: | t1 | t2 |`; unrecognized semicolon directives are ignored. Thus `; invalid: x` can occur between valid metadata and data without affecting the row, while a file containing only `; invalid: x` establishes no schema and returns status 1 with `import: invalid names`. If names are absent, generate `c1` through `cN`; if types are absent, default every column to `text`. If both are absent, infer width from data and use generated text columns. Header-only TBLN is a valid zero-row table; a completely empty TBLN file returns status 1 with `import: invalid names`. A data row must match the established column count. After a two-column schema has been established, the three-cell row `| 1 | 2 | 3 |` returns status 1 with no standard output and a timestamped diagnostic ending exactly `import: invalid column num (2!=3) [1 2 3]`; the diagnostic does not contain `bulk read:`, and the row is not shifted or reduced to a generic column-count message.

Strip the one syntactic space just inside each pipe while preserving additional leading/trailing whitespace in cell data. Only a syntactic cell boundary is split: a literal pipe embedded without the surrounding boundary spacing, as in `internal|pipe`, remains part of a single long text value. Empty cells are SQL NULL by default. Backslash sequences in ordinary input remain literal text. `-inull` additionally converts its exact marker. A nonblank line that is neither recognized metadata nor a pipe data row fails with `unsupported line`. Supported input type annotations and aliases are: `int`, `integer`, `smallint`, `int2`, `int4`, `smallserial`, `serial` to integer; `bigint`, `int8`, `bigserial` to 64-bit integer; `numeric`, `decimal`, `float`, `real`, `double precision` to numeric; `bool` to boolean-valued storage whose direct JSON representation is the text `true`/`false`; `timestamp`, `timestamptz`, `date`, and `time` to timestamp-like values; `text`, `string`, `char`, `varchar`, and unknown types to text. A metadata row combining `int`, `text`, `numeric`, `bool`, and `date` is accepted and produces the corresponding native integer, string, number, lower-case boolean text, and midnight-UTC date value.

Preserve negative, zero, large integer, decimal, timestamp, Unicode, long-string, and NULL values. Normalize valid date-only input to midnight UTC (`2023-01-01T00:00:00Z`). Failed `timestamp` and `date` conversion produces `0001-01-01T00:00:00Z`; failed `timestamptz` and `time` conversion instead preserves the original text. Thus a header-like `c1` in a `timestamptz` column remains `c1`, and a header-like `c7` in a `time` column remains `c7`, even though all four annotations map to output type `timestamp`.

## Spec 21

`-itext` reads every physical line as a single text column named `text`; it preserves the complete line, including an empty line, and never splits commas or spaces. A zero-byte text file is a valid zero-row table. `-is`, `-ilr`, `-inum`, exact null replacement, SQL filtering, and aggregates operate normally.

`-iwidth` parses fixed-width, whitespace-separated reports. The first retained line defines exact column names and character start positions; each data line is sliced by those starts, surrounding separator space is removed, and the final column consumes the rest of the line so commands containing spaces remain intact. It must parse `ps`-like headings including `%CPU`/`%MEM`, simple aligned three-column data, Unicode headings, and `dpkg`-like files after skipped preamble lines. Width values are SQL text and may be cast. The general header, skip, preread, row-limit, row-number, NULL, Unicode, query, and output rules apply.

## Spec 22

Keep database result types through serialization. CSV/LTSV/JSON/YAML scalar input begins as text; TBLN typed input and SQL expressions can produce native types. SQL integer expressions and casts serialize as exact base-10 integers, including signed 64-bit limits; REAL/numeric results serialize without artificial thousands separators; SQL NULL remains distinct. JSON/YAML native nested values are stored in a form that can be reconstructed by structured outputs. Booleans read through jq become lower-case text `true`/`false`. String payloads that are valid JSON objects/arrays must be unpacked back to objects/arrays in JSON/YAML output; the YAML writer additionally interprets valid embedded YAML such as `key: value` and `[1, 2, 3]` as a map and list. Never truncate 10,000-character fields, long lines, many columns, or hundreds/thousands of rows.

Numeric serialization uses the shortest faithful decimal spelling across numeric sources, including typed TBLN values and aggregate results: `0.0` is emitted as JSON `0`, `30.0` as `30`, and `4.0` as `4`, while `123.456789` and `-42.5` retain their fractional parts.

For invalid UTF-8 byte cells, text/JSON-safe serialization uses a `\x` followed by lowercase hexadecimal bytes rather than emitting invalid UTF-8 or base64. Preserve valid UTF-8, including accents, CJK, Cyrillic, emoji, and Unicode column names, without ASCII transliteration.

## Spec 23

CSV is the default output and `-ocsv` explicitly selects it. By default it emits no header, separates fields with comma, uses double quote as quote character, uses LF, and writes one record per result row. Quote a field when required by CSV (delimiter, quote, CR, or LF in its content), doubling embedded quote characters. `-oh` prepends one header record. `-od VALUE` changes the delimiter after decoding escape sequences when the decoded value is one character. A multi-character CSV delimiter is accepted rather than rejected but is ignored in favor of the default comma: `-ocsv -od '||' 'SELECT 1,2'` emits `1,2\n`. `-oq VALUE` changes the quoting character and doubles that character inside quoted fields; for a multi-character value only its first character is used, so `-oq xx` encloses `a,b` as `xa,bx`. `-oaq` quotes every header and data field, including numbers. Options combine, so custom delimiter, quote-all, header, and CRLF all apply together. `-ocrlf` changes every CSV record terminator, including the last, to exactly CRLF.

Without `-onull`, SQL NULL is an empty CSV field. With it, use the supplied marker. Empty text also remains an empty field, so only a structured output or SQL predicates can distinguish it from default-rendered NULL. For example, selecting text `1`, `O"range` and `M'elon` with normal quotes yields rows like `1,"O""range"` and `M'elon`; with `-oq '` a value containing apostrophe is enclosed in apostrophes and the apostrophe is doubled.

## Spec 24

`-ojson` emits one pretty-printed JSON array, using two-space indentation and one object per result row. Keys are result column names in result order where that order is deterministic. The exact outer layout is:

```text
[
  {
    "name": "Alice",
    "n": 1,
    "missing": null
  }
]
```

The empty result is exactly `[]\n`. Text is JSON text; numeric SQL results are JSON numbers; SQL NULL is JSON `null`; reconstructed nested objects and arrays remain structured. Escape control characters and quotes correctly and use Go JSON encoder-compatible HTML escaping for characters such as `&`, `<`, and `>` (`\u0026`, `\u003c`, `\u003e`) where encountered. `-onull MARKER` replaces SQL NULL with a JSON string containing MARKER before encoding.

If several output-format booleans are enabled, use a stable format priority rather than merging formats. In particular JSON wins over CSV regardless of whether the pair is written `-ojson -ocsv` or `-ocsv -ojson`.

## Spec 25

`-ojsonl` emits each row as one compact JSON object with no array delimiters or blank lines, followed by LF. For example two text rows are exactly:

```text
{"a":"1","b":"2"}
{"a":"3","b":"4"}
```

Use the same key, type, escaping, nested-value, NULL, and `-onull` rules as JSON. A zero-row result produces zero bytes.

## Spec 26

`-oltsv` emits each row as tab-separated `column:value` pairs in result-column order, with LF. It always includes labels and does not add a separate header. Convert nontext scalars to their ordinary textual representation. NULL is empty after the colon unless `-onull` provides a marker. Preserve ordinary spaces and special characters in values. A zero-row result is empty.

`-oraw` emits values without CSV quoting or escaping, joined by the exact decoded `-od` string (default comma), followed by LF. Unlike CSV, RAW permits multi-character delimiters such as `||`, tabs, and NUL (`\x00`). Embedded newlines remain raw. `-oh` emits an unquoted header with the same delimiter. RAW ignores `-ocrlf` and continues to terminate records with LF; `-oraw -od '\x00' -ocrlf` on values `a` and `b` emits the bytes `a\x00b\n`. NULL is empty or the `-onull` marker. A zero-row result emits zero bytes without `-oh`; with `-oh`, it emits the header even though there are no data rows, so `-oraw -oh 'SELECT 1 x WHERE 0'` emits exactly `x\n`.

## Spec 27

`-oyaml` emits a block-style YAML sequence of mappings, one mapping per row. The first field is written as `- key: value` and later fields as two-space-indented `key: value`; do not emit a document marker. Example:

```text
- name: Alice
  age: 30
  active: true
  missing: null
```

The empty result is exactly `[]\n`. Emit native NULL as `null`, integers/floats/bools as YAML scalars, and nested maps/lists structurally. For each non-NULL textual database value, attempt YAML scalar/structure decoding: unambiguous forms such as `30`, `75000.50`, `true`, `key: value`, and `[1, 2, 3]` therefore become a number, boolean, mapping, or sequence, while an ordinary word remains text; an empty textual field consequently emits as YAML null. With `-onull`, emit the supplied marker as a string value rather than YAML null. Use the reference YAML encoder's quoting: the marker `NULL` is emitted exactly as the double-quoted scalar `"NULL"`, not a single-quoted scalar. Preserve Unicode directly.

## Spec 28

`-otbln` emits no timestamp or creation metadata. It first emits exactly a name definition and a type definition, then data:

```text
; name: | id | name |
; type: | int | text |
| 1 | Alice |
```

There is one space on each side of every value and a final `|`; every line ends LF. The name list is the SQL result column list. TBLN type metadata comes from declared result-column metadata, not from the runtime value. Preserve compatible declared types on a direct TBLN round trip, mapping integer/small integer aliases to `int`, 64-bit integer aliases to `bigint`, float/real/double/numeric/decimal to `numeric`, boolean to `bool`, date/time/timestamp/timestamptz to `timestamp`, and character/string and unknown types to `text`. SQLite expressions and casts do not supply such declared metadata to this writer and are therefore labeled `text`: `SELECT CAST(id AS INTEGER) AS id, note FROM d.csv` over a headered CSV emits `; type: | text | text |`, and even an empty `SELECT CAST(1 AS INTEGER) AS id, 'x' AS note WHERE 0` does the same. A CSV table queried without `-ih` has generated text columns and its header-looking first record is ordinary data.

An empty result still emits the two metadata lines and no data lines. NULL cells are blank unless `-onull` is given. Numeric output uses the shortest faithful decimal spelling (`500.00` becomes `500`, while `1000.50` becomes `1000.5`). Temporal conversion follows Spec 20: failed `timestamp`/`date` values use the zero timestamp, whereas failed `timestamptz`/`time` values remain text. Replace an actual LF inside a TBLN value with the two visible characters `\n`; actual CR and tab characters remain literal bytes in the value rather than becoming `\r` or `\t`. Double every literal pipe inside an output cell: the value `internal|pipe` is serialized as `internal||pipe`. Existing literal backslash sequences remain literal. Preserve Unicode and long content.

## Spec 29

`-oat` emits an ASCII bordered table. Each column's interior width is the maximum displayed width of its heading and cells plus one padding space on each side. Borders use `+` and `-`; rows use `|`. Text cells are left-aligned and numeric cells are right-aligned. The first heading is left-aligned and later headings are centered: in the tested `-onowrap` two-text-column table the first heading is exactly `| name  |`, while the much wider `description` heading is centered in its column; do not right-align the first heading as `|  name |`. Emit a top border, heading row, separator border, every data row, and bottom border. A representative result is:

```text
+-------+-----+
| name  | age |
+-------+-----+
| Alice |  30 |
+-------+-----+
```

`-omd` uses the same widths/alignment but omits the outer top/bottom borders and uses the heading separator as `|-------|-----|`. Every row begins and ends `|`. Escape or otherwise retain embedded pipe content without losing it. By default the table renderer may wrap long cells according to its normal terminal-width behavior; `-onowrap` must keep each complete long cell on one physical row. These table formats inherently show headings; `-oh` is not required.

## Spec 30

`-ovf` emits records vertically. Prefix two spaces, right-align all field names to the longest field-name width, and put ` | ` before the value. Precede every record, numbered from 1, with `---[NN]` where NN is a space-padded width-2 decimal row number, followed by exactly 24 hyphens. For columns `name`, `age`, `city`, `salary`, representative output begins:

```text
---[ 1]------------------------
    name | Alice
     age | 30
    city | New York
  salary | 75000.50
```

Repeat the marker and all fields for each row, preserving row order. A zero-row result emits nothing.

## Spec 31

`-out PATH` sends the complete (possibly compressed) result to PATH, creates/truncates that file, and suppresses standard output. It does not create missing parent directories; an open failure returns 1 and reports `open PATH: no such file or directory`. Unless `-out-without-guess` is present, infer output format from the last recognized non-compression extension anywhere at the end of the basename: `.csv`, `.json`, `.jsonl`, `.ltsv`, `.yaml`/`.yml`, `.tbln`, `.raw`, `.md`, `.at`, or `.vf`. Thus `result.unknown.json` is JSON and `result.ltsv.zst` is zstd-compressed LTSV. Compression suffixes are those in Spec 12.

An inferred output format overrides the default. `-out-without-guess` disables both format inference and implicit changes from an otherwise unknown output name; any explicit output format remains effective, and with none specified the output is CSV. Writing to stdout remains the default when `-out` is absent.

## Spec 32

`-a FILE` is analysis mode. It applies the selected input format/options and, on success, writes: `The table name is FILE.`, `The file type is FORMAT.`, optional format advice, a blank line, a `Data types:` ASCII table with headings `column name` and `type`, a blank line, a `Data samples:` ASCII table containing preread/sample rows, a blank line, `Examples:`, and four suggested invocations. The four SQL patterns are: select all discovered columns; the same with `WHERE first_column = 'first_sample'`; `SELECT first_column, count(first_column) ... GROUP BY first_column`; and select all with `ORDER BY first_column LIMIT 10`. Use comma-space between listed fields. Include currently relevant flags such as `-ih`, `-ir 1`, `-driver postgres`, or `-driver mysql`. The executable token in suggestions is the actual invocation path/name (tests normalize an absolute workspace path to `./executable`).

Analysis sample collection follows the selected reader. A top-level JSON array is decoded as one input document, so its detailed sample table contains every element of that array: the three-row `test.json` sample shows `Orange`, `Melon`, and `Apple` even with the default preread count. For headered line-oriented CSV with `-ir 1`, the sample contains the first data row. Its sample heading follows reference table alignment exactly, for example `| name  | age | city |` (not `|  name | age | city |`).

`-A FILE` emits only those four command lines, with no labels or tables. If header-only input provides names but no sample, detailed analysis prints empty sample borders and `Examples:` with no commands. Quote SQL keyword or non-simple column names in suggested SQL with driver-appropriate identifier quotes; the displayed analysis table escapes backticks as `\``. Simple `[A-Za-z_][A-Za-z0-9_]*` non-keywords are unquoted. A MySQL analysis uses backticks; PostgreSQL-compatible suggestions must carry `-driver postgres`.

## Spec 33

Analysis gives heuristic correction advice without changing the selected parse. When CSV parses as one column and triggers delimiter advice, print `Is the delimiter different?` followed by exactly `Please try again with -id " " or other character.`; the suggestion contains one literal space even when the sample actually contains a tab or semicolon. For the sample `a\tb\n1\t2\n`, those two lines are printed and no LTSV advice is added. For the CSV sample `[{"a":1}]\n`, the reference prints those same delimiter lines followed by `Is it a LTSV file?` and `Please try again with -iltsv.`; it does not print JSON advice. For JSON/YAML where the sole discovered field contains nested objects or arrays, print `Is it for internal objects?` and build the suggested jq path from that actual field name. A sole field named `outer` yields exactly `Please try again with -ijq ".outer".`; if analysis already uses `-ijq .data` and discovers sole field `users`, concatenate them and print exactly `Please try again with -ijq ".data.users".` Existing table suffix and `-ijq` selectors likewise concatenate into the analyzed table name as `FILE::EXPR`.

Analyze failures return 1 and prefix reader/schema errors with a timestamped `ERROR:`, for example `ERROR: no rows`, `ERROR: invalid JSON: ...`, `ERROR: invalid YAML: ...`, or `ERROR: invalid column`. Consistent with Spec 20's directive handling, analyzing a TBLN file containing only `; invalid: x` instead returns 0 and prints TBLN analysis with empty data-type and sample tables. An empty analysis filename and a missing file fail. A completely empty CSV analysis fails; a nonempty one-record CSV without `-ih` can be analyzed as one sample row.

## Spec 34

Configuration is JSON with this shape:

```json
{
  "db": "sdb",
  "database": {
    "sdb": {"driver": "sqlite3", "dsn": ":memory:"},
    "other": {"driver": "postgres", "dsn": "connection text"}
  }
}
```

`-config PATH` explicitly selects it. Otherwise the Unix default path is exactly `$HOME/.config/trdsql/config.json` (do not substitute `XDG_CONFIG_HOME`). `-dblist` returns 0 and writes one `name:driver` line for every configured database; ordering need not be stable. `-db NAME` selects that entry, with top-level `db` as default. Explicit `-driver` and `-dsn` override selected configuration values. If a requested named database is absent, log `ERROR: db[NAME] does not found` but continue using default behavior and permit the query to succeed.

An explicitly selected malformed/nonconforming config is fatal status 1 and includes `ERROR: [PATH]config error: DETAILS`. Preserve the Go JSON parser detail: when a property follows a closed `database` object without a separating comma, the suffix is exactly `config error: invalid character '"' after object key:value pair`. A missing explicitly selected config likewise fails. Supported local drivers are `sqlite3` (default) and `sqlite3_ext`; both must execute the tested SQLite queries. With no configuration and no explicit `-dsn`, the selected driver is `sqlite3` and its DSN string is empty, not `:memory:`; debug prints `driver: sqlite3, dsn: ` and `SELECT 13` still succeeds. A SQLite DSN of `:memory:` uses memory; a filesystem DSN creates/opens that database file. `-dsn :memory:` works without an explicit driver. Unknown driver failure is exactly `connect: sql: unknown driver "NAME" (forgotten import?)` after the timestamp. An unusable SQLite filesystem DSN whose parent does not exist fails at transaction begin with `begin: unable to open database file: no such file or directory`, rather than a shorter `connect:` diagnostic. `mysql` and `postgres` selections must be recognized and attempted rather than reported as unknown, although an unavailable server may cause a connection error.

## Spec 35

`-debug` sends timestamped diagnostic lines to standard error and does not contaminate result stdout. For a query, it identifies the config path attempted (`config found: PATH` when loaded; the default missing path and its `no such file or directory` when absent), lists configured entries as `[driver: name:driver:dsn]` with `>` before the selected one, and reports `driver: DRIVER, dsn: DSN`. It must log the effective query SQL: `-debug 'SELECT 1'` includes a timestamped line ending `SELECT 1`. A file query additionally logs its `CREATE TEMPORARY TABLE`, `INSERT INTO`, and rewritten final `SELECT` statements; for `SELECT * FROM testdata/test.csv`, stderr therefore contains both `CREATE TEMPORARY TABLE` and `SELECT * FROM ` followed by the quoted temporary-table name. `-dblist` returns before those entry/selection diagnostics: with `-debug -config CONFIG -db other -dblist`, stdout still contains `sdb:sqlite3` and `other:sqlite3_ext`, but stderr contains only the timestamped `config found: CONFIG` line and has no `[driver:` or `driver: DRIVER, dsn:` line.

Ordinary runtime errors are timestamped log lines on standard error and return status 1. A failing statement emits no result of its own, but under the sequential multi-statement behavior in Spec 8, stdout from earlier successful statements is not retracted. Input failures generally begin `import:`, analysis failures `ERROR:`, connection failures `connect:` or `begin:`, and SQL/export failures `export:`. A referenced nonexistent file-like table is left for SQLite to diagnose rather than reported as an import-open error: `SELECT * FROM nonexistent_file.csv` ends with exactly `export: no such table: nonexistent_file.csv [SELECT * FROM nonexistent_file.csv]`. The same rule applies inside a UNION, whose diagnostic includes the complete rewritten UNION SQL in brackets.

Other SQL errors include the engine message followed by the effective SQL in brackets, for example `export: no such column: bad [SELECT bad FROM \`file.csv\`]` or `export: near "FRON": syntax error [SELECT * FRON file.csv]`. Detect malformed/incomplete SELECT, duplicate operators, missing tables, invalid columns, malformed JSON/YAML/LTSV/TBLN, permission denial, invalid delimiters/jq, and mid-stream parse errors; never crash or hang.

## Spec 36

Behavior must be data-general rather than keyed to fixture names. It must handle at least thousands of CSV rows, hundreds of JSON rows, at least ten columns, 10,000-character fields, very long SQL/CASE expressions, mixed LF/CRLF, embedded CSV newlines, Unicode in data and identifiers, special punctuation, zero rows, one row, and one column within normal test timeouts. Import all rows exactly once, and make aggregate counts, joins, filters, ordering, and serialization consistent with that imported data. Empty result sets are successful and use the format-specific empty representation; empty inputs are errors except formats that still provide a schema (CSV/TBLN header-only) or TEXT, as defined above.
