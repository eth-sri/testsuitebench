# SQLite 3.54.0 command-line executable specification

The required artifact is one executable file named `executable`. It is a self-contained SQLite-compatible database engine and command-line shell. All behavior below is observable through that process; no server or companion program is involved. Unless a section explicitly permits variation, output bytes, row order, errors, database changes, and process status must match the behavior described here.

## Spec 1

`executable` must be directly runnable on a 64-bit Linux system. Its command form is:

```
executable [OPTIONS] [FILENAME [SQL]]
```

With no filename, it opens a transient in-memory database. `:memory:` explicitly does the same. With a normal filename, it opens that SQLite database, creating it when allowed and necessary. SQL may be supplied as the final argument, as multiple successive command arguments, through standard input, through initialization files, or through `.read`; all statements for one invocation share one connection and shell state. SQL and dot commands may be mixed on standard input. Non-interactive stdout contains query and dot-command results plus any startup informational notice expressly described below; diagnostics go to stderr.

This is specifically the SQLite shell/engine behavior identified as version 3.54.0, source build `2026-04-14 20:02:49 49b3bac482c831f503c7f90c35959e7ea731950e991baba86b2ab95987d2539b`. `-version` and `--version` print a line beginning `3.54.0` and exit successfully. SQL `sqlite_version()` returns `3.54.0`. `.version` prints exactly these three logical lines:

```
SQLite 3.54.0 2026-04-14 20:02:49 49b3bac482c831f503c7f90c35959e7ea731950e991baba86b2ab95987d2539b
zlib version 1.2.11
gcc-11.4.0 (64-bit)
```

`-help`, `--help`, and `.help` expose the supported syntax and options. Command-line help goes to stderr and includes `Usage:`, `OPTIONS`, `FILENAME`, and the available mode flags.

## Spec 2

The build identity is observable. `PRAGMA compile_options;`, in its default list output, must return exactly the following sorted lines and no extras:

```
ATOMIC_INTRINSICS=1
COMPILER=gcc-11.4.0
DEFAULT_AUTOVACUUM
DEFAULT_CACHE_SIZE=-2000
DEFAULT_FILE_FORMAT=4
DEFAULT_JOURNAL_SIZE_LIMIT=-1
DEFAULT_MMAP_SIZE=0
DEFAULT_PAGE_SIZE=4096
DEFAULT_PCACHE_INITSZ=20
DEFAULT_RECURSIVE_TRIGGERS
DEFAULT_SECTOR_SIZE=4096
DEFAULT_SYNCHRONOUS=2
DEFAULT_WAL_AUTOCHECKPOINT=1000
DEFAULT_WAL_SYNCHRONOUS=2
DEFAULT_WORKER_THREADS=0
DIRECT_OVERFLOW_READ
DQS=0
ENABLE_BYTECODE_VTAB
ENABLE_DBPAGE_VTAB
ENABLE_DBSTAT_VTAB
ENABLE_EXPLAIN_COMMENTS
ENABLE_FTS3
ENABLE_FTS4
ENABLE_MATH_FUNCTIONS
ENABLE_OFFSET_SQL_FUNC
ENABLE_PERCENTILE
ENABLE_RTREE
ENABLE_STMTVTAB
ENABLE_UNKNOWN_SQL_FUNCTION
HAVE_ISNAN
MALLOC_SOFT_LIMIT=1024
MAX_ATTACHED=10
MAX_COLUMN=2000
MAX_COMPOUND_SELECT=500
MAX_DEFAULT_PAGE_SIZE=8192
MAX_EXPR_DEPTH=1000
MAX_FUNCTION_ARG=1000
MAX_LENGTH=1000000000
MAX_LIKE_PATTERN_LENGTH=50000
MAX_MMAP_SIZE=0x7fff0000
MAX_PAGE_COUNT=0xfffffffe
MAX_PAGE_SIZE=65536
MAX_SQL_LENGTH=1000000000
MAX_TRIGGER_DEPTH=1000
MAX_VARIABLE_NUMBER=32766
MAX_VDBE_OP=250000000
MAX_WORKER_THREADS=8
MUTEX_PTHREADS
STRICT_SUBTYPE
SYSTEM_MALLOC
TEMP_STORE=1
THREADSAFE=1
```

These options are behavioral requirements: double-quoted string literals are disabled; the listed limits are enforced; FTS3/4, RTree, math, percentile, sqlite_dbpage, dbstat, bytecode, and statement virtual-table functionality is present. Although `DEFAULT_RECURSIVE_TRIGGERS` is present in the compile-option list, this shell connection starts with recursive triggers disabled: a fresh `PRAGMA recursive_triggers;` outputs `0`. FTS5 is absent. The external `csv`, `spellfix1`, `transitive_closure`, `geopoly`, `carray`, `eval`, and `totype` modules/functions are also absent unless loaded from a real library; attempts to use them report the normal `no such module` or `no such function` error naming the requested feature. `.load` itself exists, and missing or invalid shared libraries fail cleanly.

## Spec 3

Command-line option parsing must support short and long spellings used by the shell, including `-batch`, `-bail`, `-cmd COMMAND`, `-column`, `-csv`, `-echo`, `-header`, `-noheader`, `-html`, `-interactive`, `-json`, `-line`, `-list`, `-markdown`, `-quote`, `-table`, `-tabs`, `-ascii`, `-box`, `-stats`, `-zip`, `-A`, `-init FILE`, `-noinit`, `-nullvalue TEXT`, `-separator SEP`, `-newline SEP`, `-readonly`, `-ifexists`, `-safe`, `-nonce TEXT`, `-vfs NAME`, `-mmap N`, `-lookaside SLOT N`, `-pagecache SIZE N`, `-screenwidth N`, `-deserialize`, `-maxsize N`, `-nofollow`, `-pcachetrace`, and `-memtrace`. `--` ends option processing so a following filename beginning with `-` is not parsed as an option. `-column` selects column mode and enables headings even without `-header`: `SELECT 1 as num, 'test' as str;` begins with the heading row `num  str` and its hyphen underline. `-stats` enables the same per-statement report as `.stats on`; the query result is followed by the report beginning `Memory Used:`.

Options are applied in argument order where ordering is meaningful. A mode-selection option resets headings to that mode's default, so `-header -list` and `-header -noheader -list` each print only `1\n` for `SELECT 1 AS answer;`, while `-list -header` prints `answer\n1\n`. Initialization executes before `-cmd` commands and the final SQL. Multiple `-cmd` values execute sequentially and may themselves be dot commands. `-noinit` suppresses user initialization; a named `-init` file is read, and a missing one reports an error but does not prevent later explicitly supplied commands from being processed. In particular, `-init /nonexistent/file.sql :memory: "SELECT 1;"` writes `cannot open: "/nonexistent/file.sql"` to stderr, writes `1` to stdout, and exits 0: failure to open the explicitly named initialization file does not by itself make an otherwise successful invocation fail. `-readonly` permits reads and prevents writes; `-ifexists` refuses a nonexistent database rather than creating it. `-vfs` validates the named VFS. The memory-configuration flags are accepted early enough to configure startup and do not corrupt execution. In particular, `-lookaside 64 32 -pagecache 1024 20 -mmap 0 -screenwidth 80 :memory: "SELECT 123;"` exits 0 and writes the informational line `Page cache size increased to 1296 to accommodate the 272-byte headers` to stdout immediately before `123`. `-safe` blocks unsafe operations such as extension loading, shell execution, arbitrary `.open`, and output redirection. The matching nonce permits the shell’s guarded unsafe escape mechanism.

Unknown options produce stderr containing `unknown option` and the option text and exit status 1. Options requiring an argument diagnose a missing argument. A nonexistent VFS is invalid: `-vfs does-not-exist :memory: "SELECT 1;"` exits 1 and writes `no such VFS: "does-not-exist"` to stderr. A small positive screen width is accepted rather than diagnosed: `-screenwidth 10 :memory: "SELECT 1;"` exits 0, writes `1` to stdout, and writes nothing to stderr.

## Spec 4

The shell accepts complete SQL statements terminated by semicolons. Statements may span lines and may contain semicolons or newlines inside quoted strings, line comments beginning `--`, and block comments. At the shell-input layer, a physical line whose first byte is `#` is also a comment and is ignored in full, even when the remaining text resembles SQL or a test-harness command. Input consisting only of such hash-prefixed lines produces no stdout or stderr and exits 0. Blank lines and comments interspersed with commands are ignored. A final complete statement may be executed at end of input; incomplete syntax, unmatched quotes, unclosed constructs, embedded NUL where prohibited, malformed tokens, excessive nesting, and over-limit statements are diagnosed safely.

Default non-interactive behavior continues after statement errors, executes later statements, and exits nonzero if an error occurred. `.bail on` or `-bail` stops at the first error. `.bail off` restores continuation. `.echo on` or `-echo` prints input commands before their results; off suppresses this. `.changes on` prints per-statement change and total-change counts after statements; off suppresses them. `.timer on` prints run/real timing measurements, and `.timer off` suppresses them. `.timer once` is accepted, exits successfully, and prints a `Run Time: real` line after the next SQL statement only; later statements are not timed unless timing is enabled again. Timing never alters SQL results.

Successful normal execution exits 0. A SQL parse, prepare, run-time, constraint, or database I/O error makes the invocation exit 1 unless `.exit N` explicitly selects another status. Shell-command diagnostics have command-specific status behavior. Each of `.changes invalid`, `.echo invalid`, `.headers invalid`, and `.timer invalid` exits 0 and writes exactly `ERROR: Not a boolean value: "invalid". Assuming "no".` to stderr. `.filectrl invalid` and `.testctrl invalid` also exit 0 and respectively report `Error: unknown file-control: invalid` or `Error: unknown test-control: invalid`, followed by `Use ".filectrl --help" for help` or `Use ".testctrl --help" for help`. `.clone /nonexistent/target.db` exits 0 with `Cannot create output database: unable to open database file`; `.open /nonexistent/dir/test.db` exits 0, reports that it is using a substitute in-memory database, and continues on that database. These diagnostics do not set the invocation's failure status. By contrast, an unknown dot command or a `.read` usage error exits 1. The initialization-file open failure described in Spec 3 is another explicit status-0 exception when later work succeeds. `.exit` and `.quit` stop immediately and execute no following input. `.exit 7` selects process status 7, but `.quit` does not use an argument as an exit status: the input `SELECT 1;\n.quit 7\nSELECT 2;\n` writes exactly `1\n` to stdout, writes nothing to stderr, and exits 0.

## Spec 5

The default output is list mode: one result row per line, columns separated by `|`, no headers, and SQL NULL rendered as the current null string (initially empty). Every emitted row ends in the configured row terminator, initially newline. `.separator COL [ROW]`, `-separator COL`, and `-newline ROW` update these separators; recognized escapes such as `\t`, unit separator, record separator, empty separators, and multicharacter separators work. `.nullvalue TEXT` and `-nullvalue TEXT` set the textual representation of NULL. `.headers on/off`, `-header`, and `-noheader` control column-name rows where the mode supports them.

The following mode contracts are required:

- `list`: raw fields separated by the configured separator. Example `SELECT 1,2,3;` is `1|2|3\n`.
- `tabs`: tab-separated fields and newline-separated rows.
- `ascii`: byte `0x1f` between fields and `0x1e` after every row.
- `csv`: RFC-style CSV, comma and CRLF defaults, double-quote quoting, doubled embedded quotes, and quoting when data contains separator, quote, CR, or LF. Empty text and NULL remain distinguishable according to CSV shell rules and `-nullvalue`.
- `quote`: comma-separated SQL expressions: integers/reals are unquoted, ordinary text is single-quoted with internal quotes doubled, blobs use a lowercase `x` prefix and lowercase hexadecimal digits, and null uses `NULL`. Thus `SELECT X'48656C6C6F';` renders exactly as `x'48656c6c6f'`. Text containing control characters is emitted as a restorable `unistr(...)` expression rather than placing those bytes literally in a quoted string: `SELECT 'line1'||char(10)||'line2','tab'||char(9)||'here';` renders exactly as `unistr('line1\u000aline2'),unistr('tab\u0009here')`. In particular, three rows containing a newline, a tab, and no control character render exactly as:

  ```
  'line1',unistr('Text with\u000anewline')
  'line2',unistr('Text with \u0009 tab')
  'line3','Quote: " and comma: ,'
  ```
- `insert TABLE`: one `INSERT INTO TABLE VALUES(...);` statement per row using SQL literal quoting. The table name argument is honored.

Empty result sets emit nothing except mode-specific framing where that mode defines it. Unicode is emitted as UTF-8 and long fields/large row sets are not truncated.

## Spec 6

Structured display modes must reproduce shell formatting and alignment:

- `column` prints aligned columns. With headers it prints column names and a hyphen underline; widths derive from headings and values unless set by `.width`. Positive widths left-align, negative widths right-align, zero selects automatic width. Narrow columns wrap long content. `.width` with no values resets widths; extra or missing widths are handled per column.
- `table` uses ASCII borders, such as `+---+`, and cells of the form `| a |`; headers are present by default for this mode and `-noheader` removes only the heading row/separator while retaining table borders.
- `box` and `qbox` use UTF-8 box-drawing borders, with `╭` at the upper-left and `╰` at the lower-left. Width, multiline, NULL, and multiple-row alignment are preserved.
- `markdown` emits a header row, `|---|` separator cells, and data rows, correctly handling one or multiple columns and rows.
- `line` prints one `name: value` field per line with names right-aligned to the widest heading and a blank line between records.
- `html` prints uppercase `<TR>`, `<TH>`, and `<TD>` records in shell form and HTML-escapes special data.
- `psql` produces PostgreSQL-style aligned tables.
- `count` prints only the number of result rows.
- `jobject` and `jatom` produce the shell’s JSON-object and JSON-atom representations.

`.mode` with no argument reports the current mode. `.mode MODE` and the corresponding command-line options switch mode for later statements. `.mode --list` is a successful listing operation and emits the line `available modes: ascii box c column count csv html insert jatom jobject json line list markdown off psql qbox quote split table tabs tcl batch tty`. Mode modifiers tested by the shell—`--wrap`, `--wordwrap`, `--charlimit`, `--width`, `--quote`, `--noquote`, `--escape`, `--noescape`, `--tag`, and border control—must affect quoting, wrapping, escaping, truncation, tag display, and borders as their names indicate.

## Spec 7

JSON output mode emits one valid JSON array per SQL statement that returns at least one row. Each row is an object whose keys are result-column names in column order. SQL NULL becomes JSON `null`; integer and real values become JSON numbers; text becomes a correctly escaped JSON string; blobs use the shell’s blob encoding rather than invalid JSON. A statement whose result has zero rows emits nothing (not `[]`). Duplicate or unusual column names, quotes, backslashes, control characters, non-ASCII text, empty strings, negative zero, large integers, and non-finite numeric values follow the 3.54 shell’s valid-JSON conversion rules. Multiple rows remain ordered and occur as separate objects in the array.

Header settings do not insert a separate header row into JSON. In table, box, markdown, column, line, HTML, quote, CSV, tabs, ASCII, and list modes, header and NULL behavior remains mode-correct. In this Linux build, `.crlf on` does not enable CRLF: both `.crlf on` and `.crlf off` write exactly `crlf is OFF` to stderr, and ordinary row terminators remain LF. Consequently `.crlf on`, `SELECT 1;`, `.crlf off`, `SELECT 2;` writes `1\n2\n` to stdout and two `crlf is OFF` lines to stderr. CSV mode retains its own CRLF row convention.

## Spec 8

Output destinations are stateful shell settings. `.output FILE` redirects all subsequent query output until `.output stdout` or an empty reset. `.once FILE` redirects exactly the next output-producing command and then restores stdout, not a destination previously selected by `.output`. Thus after `.output all.txt`, `SELECT 1`, `.once once.txt`, `SELECT 2`, and `SELECT 3`, the files contain `1\n` and `2\n` respectively and stdout receives `3\n`. They create/truncate files as the shell normally does and report unusable paths. `.log FILE`, `.trace FILE`, and their stdout/stderr/off forms route engine logs and expanded SQL traces to the requested destination. `.trace stderr` writes traces to stderr. `.print` writes its arguments separated by single spaces and a newline; with no arguments it writes only a newline.

`.read` accepts a filename only. After a successful `.read commands.sql`, `.read |printf 'SELECT 9;\n'` is rejected with status 1 and stderr `Usage: .read FILE`; the pipe form is not passed to a shell. Safe mode blocks unsafe shell execution and file redirection. `.shell COMMAND...` and `.system COMMAND...` execute the parsed command through the host shell, forward command output, and return control afterward. Their dot-command argument parser consumes backslash escapes before invoking the host shell: the two input lines `.shell printf 'shell-ok\n'` and `.system printf 'system-ok\n'` produce the single byte sequence `shell-oknsystem-okn`, with no line break supplied by either command. Multiword commands, pipes, and shell logic work after this parsing. `.cd DIRECTORY` changes the shell process’s current directory for later file commands; a bad or absent directory is diagnosed. These operations must not reinterpret SQL data as commands.

## Spec 9

When stdin and stdout are terminals, interactive mode prints the 3.54.0 startup banner and uses database-aware default prompts. A transient database uses `SQLite in-memory> `. A file-backed database uses `SQLite FILENAME> `, where `FILENAME` is the displayed basename; opening a path whose basename is `example.db` produces `SQLite example.db> `. After the incomplete input `CREATE TABLE`, the continuation prompt is twelve ASCII spaces followed by `...;> `. `.prompt MAIN CONTINUE` changes prompts. Ctrl-D exits cleanly. Ctrl-C cancels incomplete input and returns to the main prompt without killing the process. `.quit` and `.exit` terminate cleanly. Blank lines and comments do not disturb state.

Interactive commands such as `.show`, `.databases`, `.tables`, `.schema`, `.dump`, `.mode`, `.headers`, `.nullvalue`, `.timer`, `.echo`, `.open`, and `.print` take effect immediately and show the same results as non-interactive operation, apart from prompts/banner. `-batch` suppresses prompts and banner; `-interactive` forces them. The process flushes prompts/output promptly so a controlling pseudo-terminal can interact with it.

## Spec 10

The SQL value system has exactly five storage classes: NULL, INTEGER (signed 64-bit), REAL (IEEE-754 binary64), TEXT (UTF-8 text), and BLOB (arbitrary bytes). Literals include decimal and hexadecimal integers, floating point with exponent, quoted text with doubled quotes, `NULL`, `TRUE`, `FALSE`, `CURRENT_DATE`, `CURRENT_TIME`, `CURRENT_TIMESTAMP`, and blob literals `X'HH...'`; malformed or odd-length blob literals error. A single underscore may separate adjacent digits in a decimal or hexadecimal numeric literal and is ignored when determining its value: `SELECT 500_000, 1_000_000;` returns `500000|1000000`, while `SELECT 0xFF_FF, 0xFF_EF, 0XFF_FF, 0XFF_EF;` returns `65535|65519|65535|65519`. Consequently `SELECT 1 ORDER BY 2_3;` treats `2_3` as ordinal 23, exits 1, and reports `1st ORDER BY term out of range - should be between 1 and 1`. Integer literals that exceed signed 64-bit become REAL when representable or error where the grammar requires an integer. Arithmetic uses integer results where safe, promotes overflowing operations to REAL, implements `/`, `%`, unary signs, bitwise `~ & | << >>`, concatenation `||`, and propagates NULL.

`typeof()` reports `null`, `integer`, `real`, `text`, or `blob`. `CAST` supports INTEGER, REAL, NUMERIC, TEXT, and BLOB conversions, including leading whitespace/signs, exponent text, prefixes, overflow saturation, zero/empty conversions, blobs, and chained casts. Boolean contexts use numeric truth conversion; `IS TRUE`, `IS FALSE`, `IS NOT TRUE`, and `IS NOT FALSE` follow three-valued SQL logic. CASE supports simple and searched forms, lazy branch evaluation, optional ELSE (NULL if absent), mixed result types, nesting, and use everywhere expressions are allowed.

## Spec 11

Column declarations apply SQLite affinity, not rigid SQL types. Declared names map to INTEGER, TEXT, REAL, NUMERIC, or BLOB affinity using the standard substring rules (`INT`; `CHAR/CLOB/TEXT`; `REAL/FLOA/DOUB`; empty/BLOB; otherwise NUMERIC). Affinity is applied on insertion and comparison: well-formed numeric text converts for numeric columns, integral REAL values may be stored as INTEGER, nonconvertible text remains text, and NULL/BLOB remain their classes. Comparison ordering is NULL before numeric before TEXT before BLOB unless a collation changes text comparison. Numeric INTEGER/REAL values compare numerically; storage-class and affinity rules also govern `IN`, `BETWEEN`, joins, grouping, DISTINCT, indexes, compound results, defaults, and updates.

`COLLATE BINARY`, `NOCASE`, and `RTRIM` are supported. BINARY compares bytes; NOCASE folds ASCII letters only (non-ASCII remains byte-sensitive); RTRIM ignores trailing ASCII spaces. Explicit collation has precedence over column/default collation and propagates through comparison expressions according to operand precedence. Collations affect equality, range operators, ORDER BY, GROUP BY, DISTINCT, IN/BETWEEN, min/max, joins, indexes, primary/unique constraints, and foreign-key parent comparison. The shell also registers `uint`, which compares embedded unsigned decimal digit runs numerically (so natural-number ordering is obtained), and a `decimal` collation for arbitrary-precision decimal strings.

## Spec 12

`SELECT` supports result expressions and aliases; `FROM` tables, views, subqueries, table-valued functions, and CTEs; `WHERE`; `GROUP BY`; `HAVING`; window clauses; `ORDER BY`; and `LIMIT/OFFSET`. `*` and qualified `table.*`, quoted identifiers, schema qualification, aliases, ordinal ordering, alias resolution, and ambiguous/unknown-column errors behave consistently. SELECT without FROM produces one row. VALUES clauses work standalone, in CTEs and compound queries, and with many rows/columns.

Predicates include comparisons, `IS`/`IS NOT`, `IS DISTINCT FROM`, NULL tests, `AND`/`OR`/`NOT` with three-valued logic, `BETWEEN`, `IN` lists/subqueries/table-valued functions, `EXISTS`, `LIKE`, `GLOB`, `REGEXP`, and `CASE`. ORDER BY supports expressions, names, ordinals, ASC/DESC, collations, and `NULLS FIRST/LAST`. LIMIT supports `LIMIT n`, `LIMIT n OFFSET m`, and `LIMIT m,n`; zero yields no rows, negative LIMIT means unlimited, and negative OFFSET acts as zero. Results must be correct for empty tables, duplicate data, NULLs, Unicode, large rows, many columns, and deeply nested but in-limit expressions.

## Spec 13

Joins support comma and `CROSS`, `INNER`, `LEFT [OUTER]`, `RIGHT [OUTER]`, `FULL [OUTER]`, and `NATURAL` joins with `ON` or `USING`. Inner joins emit matching combinations; outer joins null-extend the unmatched side(s); CROSS preserves the requested join-order barrier; NATURAL/USING identify same-named columns and emit a single coalesced USING result column in the correct `SELECT *` position. Parenthesized join groups, subqueries, views, aliases, multiple join chains, constant predicates, expression predicates, and joins mixed with aggregates/windows/CTEs are supported.

Name resolution must handle correlated scopes, shadowing, qualified names, USING-column ambiguity, aliases, attached schemas, and nested joins exactly and reject genuinely ambiguous references. Join reordering and index selection may vary internally, but query results—including NULL extension, row multiplicity, affinity/collation, and explicit ORDER BY—must be invariant. Large generated join matrices and unusual combinations of RIGHT/FULL/NATURAL/USING must complete within the test timeout.

A join may have an `ON` clause or a `USING` clause, but not both. In particular, `SELECT count(*) FROM t1, t2 ON (t1.a=t2.a) USING (a);` fails with status 1 and a diagnostic containing `near "USING": syntax error`.

## Spec 14

Aggregates include `count(*)`, `count(expr)`, `sum`, `total`, `avg`, `min`, `max`, `group_concat`, and `string_agg`. They support `DISTINCT`, `FILTER (WHERE ...)`, and aggregate-local `ORDER BY` where syntactically accepted. NULL inputs are ignored except `count(*)`; count of no rows is 0; sum/avg/min/max/group_concat of no non-NULL values are NULL; `total` is `0.0`. Integer `sum` reports integer overflow rather than silently wrapping, while total/avg use floating point. `group_concat` uses comma by default, accepts a custom (including NULL) separator, preserves specified ordering, and handles long/Unicode values.

Grouping supports one or several columns or expressions, collations, aliases where valid, HAVING with or without explicit GROUP BY, aggregates in SELECT/HAVING/ORDER BY, and scalar subqueries in aggregate expressions and filters. Nested aggregate misuse and other illegal aggregate placement produce errors. DISTINCT aggregate semantics deduplicate after affinity/collation and treat NULL correctly.

Percentile support is enabled. `median`, `percentile`, `percentile_cont`, and `percentile_disc` implement their aggregate/window semantics: numeric non-NULL inputs, validated constant percentile arguments and ranges, interpolation for continuous results, discrete selection for discrete results, deterministic ordering, correct empty/singleton results, and errors for nonnumeric or inconsistent percentile arguments. The alternate ordered-set `WITHIN GROUP` grammar is not enabled by the compile configuration and is rejected as syntax rather than silently reinterpreted.

## Spec 15

Compound queries implement `UNION`, `UNION ALL`, `INTERSECT`, and `EXCEPT`. UNION/INTERSECT/EXCEPT deduplicate using result comparison and collation; UNION ALL preserves every input row in left-to-right arm order before any final sorting. Operators associate left-to-right at the same grammar level. All arms must have equal column counts; result names and affinity/collation derive from the compound rules. NULLs compare equal for compound duplicate removal. Final ORDER BY and LIMIT/OFFSET apply to the whole compound unless nested in a subquery.

Compound terms may be SELECTs or VALUES-based queries and may contain joins, aggregates, windows, CTEs, DISTINCT, filters, indexed scans, empty sides, and computed mixed-type expressions. Compound results may themselves be subqueries/views/CTEs. Column-count, circular-reference, and illegal ORDER/LIMIT placement errors are diagnosed.

## Spec 16

Scalar subqueries return their first row’s first column and NULL if empty. Correlated subqueries can reference all legal outer scopes and are reevaluated with the correct outer row. `EXISTS`/`NOT EXISTS` test row existence independent of selected values. `IN (subquery)` and `NOT IN` implement SQL NULL logic: no match plus a NULL on the right produces UNKNOWN. Row-value comparisons and row-value IN support tuples of matching arity, lexicographic comparison, NULL propagation, tuple assignment in UPDATE, composite-index use, and appropriate arity errors.

Derived tables can be joined and aliased. Subqueries are allowed in SELECT, WHERE, HAVING, ORDER BY, CASE, FILTER, UPDATE SET, DELETE predicates, INSERT SELECT, and generated query contexts where legal. Multiple levels of nesting, correlated aggregates, EXISTS over joins, and subqueries containing UNION/INTERSECT/EXCEPT are required. Resolution must neither leak aliases into invalid scopes nor lose legal correlations.

SQLite's SELECT-list-alias extension applies in WHERE and through correlation into a nested scalar subquery. After `CREATE TABLE t1(a); CREATE TABLE x1(x);`, both `SELECT EXISTS(SELECT 1 FROM t1) aaa FROM x1 WHERE aaa AND aaa;` and `SELECT EXISTS(SELECT 1 FROM t1) aaa WHERE (SELECT 1 FROM x1 WHERE aaa AND aaa);` prepare and execute successfully. With both tables empty they emit no rows and exit 0: both occurrences of `aaa` in each WHERE resolve to the relevant SELECT result alias, including from the surrounding SELECT in the nested form.

## Spec 17

Common table expressions support `WITH` and `WITH RECURSIVE`, multiple named CTEs, explicit column lists, `MATERIALIZED` and `NOT MATERIALIZED` hints, nesting, shadowing, and use by SELECT/INSERT/UPDATE/DELETE/RETURNING. Ordinary CTEs may contain joins, aggregates, compounds, or other CTE references.

The `RECURSIVE` keyword is optional even when a CTE refers to itself: `WITH cnt(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM cnt WHERE x<5) SELECT group_concat(x, ',') FROM cnt;` exits 0 and outputs `1,2,3,4,5`. A recursive CTE has anchor and recursive terms and iterates until no new queued rows remain, honoring UNION versus UNION ALL duplicate behavior. It supports counters, factorial/Fibonacci, tree/graph traversal, cycle prevention expressed in SQL, cumulative strings/sums, multiple recursive terms, joins, subqueries, ORDER BY-driven breadth/depth traversal, and LIMIT/OFFSET. Illegal circular references, multiple disallowed self-references, aggregates/windows in forbidden recursive positions, or recursion misuse produce errors rather than hangs. Very deep recursion is bounded by engine resource limits but ordinary generated sequences complete.

The shell connection also registers the deterministic test helper `stmtrand([seed])`. Its pseudo-random sequence restarts for each SQL statement; omitting the seed is equivalent to seed 0, and the optional seed is taken from the first call in that statement. Over the recursive sequence 1 through 30, `stmtrand()%10` and `stmtrand(0)%10` each return, in row order, `4,1,8,3,6,1,4,9,2,1,2,1,0,1,8,1,4,7,6,1,8,7,0,3,0,9,4,5,9,9`. Both `stmtrand(1)%10` and `stmtrand(x)%10` over the same CTE return `3,8,9,4,7,2,3,8,5,2,7,0,3,0,7,2,5,6,1,8,5,6,7,8,7,2,9,6,8,0` because the first `x` is 1 and later arguments do not reseed that statement's generator.

## Spec 18

Window functions support `row_number`, `rank`, `dense_rank`, `percent_rank`, `cume_dist`, `ntile`, `lag`, `lead`, `first_value`, `last_value`, `nth_value`, and aggregate functions used with `OVER`. Windows may be inline or named and may inherit/override a base window as allowed. They support `PARTITION BY`, multi-expression `ORDER BY`, collations, ASC/DESC, and frames of type ROWS, RANGE, or GROUPS with UNBOUNDED, numeric PRECEDING/FOLLOWING, CURRENT ROW, and BETWEEN endpoints.

Peer groups, default frames, NULL ordering, empty/single-row partitions, multiple independent windows, and chained windows are correct. `FILTER` is accepted for aggregate windows but not built-in ranking/value functions where forbidden. `EXCLUDE NO OTHERS`, `CURRENT ROW`, `GROUP`, and `TIES` alter frames correctly. Frame bounds are validated and dynamic/negative/invalid bounds error. Windows work over joins, views, CTEs, subqueries, compounds where legal, and with outer LIMIT. Illegal nesting, placement in WHERE/GROUP BY, alias cycles, and malformed window definitions are rejected. Thousands of varied window queries must remain deterministic and complete promptly.

## Spec 19

Schema definition supports ordinary, TEMP, and schema-qualified `CREATE TABLE`, `CREATE TABLE AS SELECT`, and `IF NOT EXISTS`. Column and table constraints include PRIMARY KEY (single/composite), `INTEGER PRIMARY KEY` rowid aliasing, AUTOINCREMENT, UNIQUE, NOT NULL, CHECK, DEFAULT, COLLATE, and REFERENCES. Identifier quoting, unusual legal type names, duplicate-name detection, reserved words, and `sqlite_schema`/`sqlite_master` records are correct. DROP TABLE/INDEX/VIEW/TRIGGER support `IF EXISTS` and enforce object-type and dependency rules.

When a column default contains both a non-constant expression and an otherwise illegal `RAISE` expression, constant-default validation takes precedence. `CREATE TABLE t1 (a,b DEFAULT(random() NOTNULL IN (RAISE(IGNORE),2,3)));` fails with `default value of column [b] is not constant`, and `CREATE TABLE Table0 (Col0 DEFAULT (RAISE(IGNORE) )  );` fails with `default value of column [Col0] is not constant`; both exit 1 and do not defer the error until an INSERT.

Rowid tables expose interchangeable `rowid`, `_rowid_`, and `oid` unless a declared column shadows a name. Explicit rowids, automatic allocation, negative/large rowids, reuse rules, `last_insert_rowid()`, and INTEGER PRIMARY KEY aliases work. AUTOINCREMENT uses `sqlite_sequence`, prevents reuse, advances across conflict handling as specified, and fails at its maximum. Hidden rowids and schema objects are persistent and indexable.

Temporary objects live in the `temp` schema for one process connection and shadow main objects under normal name-resolution rules. Wide tables up to the configured limit, empty tables, large records, overflow pages, and many indexes are supported.

## Spec 20

`WITHOUT ROWID` tables require a PRIMARY KEY, reject AUTOINCREMENT, make every primary-key component NOT NULL, physically/order logically by the composite key, and expose no rowid aliases. They support integer/text/blob/composite keys, secondary and unique indexes, foreign keys, triggers, replace/upsert, joins, grouping, transactions, and ALTER operations. Duplicate or NULL primary keys fail.

`STRICT` tables accept only declared types `INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB`, and `ANY` (with the engine’s exact conversion allowances), reject unknown type names and values that cannot be losslessly converted, and identify datatype constraint errors. ANY preserves storage class; other types apply strict lossless conversion. STRICT combines with defaults, CHECK, generated columns, foreign keys, indexes, ALTER, and WITHOUT ROWID.

Generated columns may be `VIRTUAL` or `STORED`, use deterministic scalar expressions over earlier/later base/generated columns subject to dependency rules, recompute on base updates, propagate NULL, and can be constrained/indexed. Every table containing generated columns must have at least one non-generated column: `CREATE TABLE t(a INT GENERATED ALWAYS AS (1));` exits 1 with a diagnostic containing `must have at least one non-generated column`. Direct INSERT/UPDATE of a generated column, cycles, nondeterministic functions, aggregates, windows, subqueries, rowid misuse, or illegal primary-key use error. `PRAGMA table_xinfo` exposes hidden/generated status.

## Spec 21

Indexes include ordinary, UNIQUE, multicolumn, descending, covering, partial (`WHERE`), and expression indexes. Expression indexes accept deterministic expressions such as lower, abs, cast, concatenation, CASE, coalesce, substr, length, and JSON extraction; they reject subqueries and nondeterministic functions. Index affinity, collation, sort direction, NULL handling, uniqueness, and partial predicates match table semantics. Automatic indexes, skip scans, bloom filters, min/max/count optimizations, transitive constraints, OR/IN plans, and ordered/covering scans must never alter results.

`REINDEX` rebuilds named indexes, table indexes, or collation-dependent indexes. `ANALYZE` creates/updates persistent `sqlite_stat1` data and affects planning without affecting query answers; deleting or editing supported statistics and reopening the database behaves coherently. The schema table itself is an accepted ANALYZE target: after creating a table and inserting the integer `9223372036854775807`, `ANALYZE sqlite_schema;` exits 0 with no stdout or stderr. `PRAGMA optimize` is accepted. `VACUUM` rebuilds a database without changing logical schema/data, compacts free space, applies pending page-size/auto-vacuum changes, and preserves indexes, triggers, views, foreign-key definitions, schema/user/application versions as defined for those header fields. `VACUUM schema` targets an attached database. `VACUUM INTO file` creates a compact consistent copy and refuses an existing output file; VACUUM inside a transaction errors. `INDEXED BY name` forces a usable named index or errors, while `NOT INDEXED` suppresses table indexes. Schema changes invalidate/reprepare statements correctly within the shell’s sequential execution.

## Spec 22

`EXPLAIN SQL` emits the virtual-machine program with stable columns and enabled explanatory comments. `EXPLAIN QUERY PLAN SQL` emits the plan tree and descriptive details including scans/searches, named/covering/automatic/partial/expression index usage, temporary B-trees for sort/group/distinct where applicable, join order, correlated/scalar subqueries, compounds, CTEs, and views. Exact planner choices must match the specified 3.54.0 build when plan text is displayed.

`.eqp off|on|full|trigger|N` controls automatic plan display; `full` includes bytecode, trigger includes trigger programs, and invalid settings are diagnosed or reset as the shell specifies. `.explain on|off|auto` controls EXPLAIN presentation. `.scanstats` is recognized; if scan-status collection is unavailable in this build it reports the standard warning rather than inventing data. `.stats` reports memory, pager, VM, I/O, and execution counters in the shell’s labels and toggles off cleanly.

## Spec 23

INSERT supports VALUES (single/multirow), DEFAULT VALUES, explicit/reordered column lists, and INSERT SELECT with joins, aggregates, DISTINCT, compounds, CTEs, ordering and limits. UPDATE supports multiple assignments, expression dependencies, row-value assignments, correlated subqueries, optional `FROM` joins, and predicates. DELETE supports predicates and subqueries. All update paths maintain indexes, generated columns, constraints, foreign keys, triggers, rowids, and changes counters atomically.

INSERT, UPDATE, and DELETE support `RETURNING` expressions, aliases, rowid and generated values, and multiple rows in engine-defined order. RETURNING sees the row values produced by the DML and interacts correctly with upsert and triggers; illegal aggregate/window/table references are rejected. Wrong value count, duplicate or unknown target columns, missing tables, and readonly writes produce descriptive errors without partial statement effects except where a conflict algorithm explicitly permits them.

## Spec 24

Conflict algorithms `ROLLBACK`, `ABORT`, `FAIL`, `IGNORE`, and `REPLACE` are accepted on schema constraints and as `INSERT OR ...`/`UPDATE OR ...`. ROLLBACK ends and reverses the transaction, ABORT reverses the failing statement, FAIL retains earlier row changes in that statement, IGNORE skips offending rows, and REPLACE removes conflicting rows then inserts/updates with the associated trigger/foreign-key/rowid behavior. Statement-level policy overrides schema policy where defined.

UPSERT supports `ON CONFLICT` targets naming columns/expressions and optional partial-index predicates, `DO NOTHING`, `DO UPDATE SET`, update WHERE clauses, the `excluded` pseudo-table, multiple conflict clauses, omitted final targets, composite/rowid/expression-index conflicts, subqueries and CASE expressions, multirow inserts, INSERT SELECT, triggers, generated columns, and RETURNING. Only the first matching conflict clause runs for a row. A DO UPDATE constraint failure uses the required abort behavior. `REPLACE INTO` is an alias for INSERT OR REPLACE.

## Spec 25

Transactions implement autocommit plus `BEGIN [DEFERRED|IMMEDIATE|EXCLUSIVE]`, `COMMIT`/`END`, and `ROLLBACK`. DDL and DML are transactional. A normal constraint failure aborts only its statement and leaves the transaction usable unless the selected conflict policy says otherwise. Nested BEGIN and COMMIT/ROLLBACK without an active transaction error. Locks for deferred/immediate/exclusive transactions, busy timeout, readonly access, and concurrent processes preserve isolation and atomicity.

SAVEPOINT names are case-insensitive identifiers and may be quoted, empty, or Unicode. SAVEPOINT outside a transaction starts one. Nested and repeated names are supported; `ROLLBACK TO name` undoes changes after that savepoint while leaving it active, and `RELEASE name` releases it and all nested savepoints. Releasing the outermost savepoint commits only when that SAVEPOINT itself started the transaction. Releasing every savepoint nested inside an explicit `BEGIN` leaves the explicit transaction active. For example, after `BEGIN`, two nested savepoints both named `a`, rollback and release of the inner `a`, and release of the remaining `a`, a subsequent `BEGIN` fails with status 1 and `cannot start a transaction within a transaction`. Full COMMIT releases all; full ROLLBACK discards all. Missing savepoints error. DDL, indexes, views, triggers, foreign-key work, and statement failures all roll back correctly through savepoints.

## Spec 26

Foreign-key enforcement is controlled per connection by `PRAGMA foreign_keys`; it is off initially where shell defaults require and on when requested. Parent keys may be primary or compatible UNIQUE keys and must use correct collation/arity. Child NULL values are allowed under SQL composite-null rules. Immediate constraints fail at statement end; DEFERRABLE INITIALLY DEFERRED constraints may be satisfied before transaction commit. Mismatched schemas report foreign-key mismatch.

Actions `NO ACTION`, `RESTRICT`, `CASCADE`, `SET NULL`, and `SET DEFAULT` work independently for ON DELETE and ON UPDATE, including self-reference, composite keys, multilevel cascades, cycles that are legally deferred, WITHOUT ROWID parents, triggers, replace/upsert, and conflicts with NOT NULL/defaults. `PRAGMA foreign_key_list`, `foreign_key_check`, and table-specific checks report the documented row fields. Foreign keys do not cross attached-schema boundaries; keys within an attached database work.

## Spec 27

Views support explicit/derived column names, joins of all required kinds, aggregates, windows, compounds, CTEs, subqueries, DISTINCT, ORDER/LIMIT, CASE/functions, nested views, TEMP views, and schema persistence. Creation may defer resolution of a missing underlying table, but querying an invalid or circular view errors. DROP VIEW handles `IF EXISTS` and rejects dropping a table as a view or vice versa.

Triggers support BEFORE/AFTER INSERT, UPDATE, UPDATE OF, and DELETE on tables and INSTEAD OF operations on views. `OLD` and `NEW`, WHEN, multiple statements, SELECT/subqueries, `RAISE(IGNORE|ROLLBACK|ABORT|FAIL, message)`, and multiple triggers are supported. Trigger side effects participate in the same transaction/savepoint and maintain constraints, foreign keys, indexes, and changes. TEMP triggers have their proper namespace. Recursive/cascading triggers follow the enabled recursive-trigger setting and depth limit. Rename/drop/ALTER operations update or validate trigger/view dependencies as required.

Expression name resolution precedes the trigger-only-context check for `RAISE` where both errors apply. Thus `CREATE TABLE t5 AS SELECT RAISE(abort,a);` exits 1 with a diagnostic containing `no such column: a`, rather than reporting that `RAISE` was used outside a trigger.

## Spec 28

`ALTER TABLE` supports RENAME TO, RENAME COLUMN, ADD COLUMN, and DROP COLUMN on ordinary, TEMP, attached, STRICT, AUTOINCREMENT, generated-column, and WITHOUT ROWID tables. Renames rewrite the stored SQL and dependent indexes, triggers, views, foreign-key clauses, expressions, and composite keys without changing data. Transaction rollback restores both schema and data.

ADD COLUMN validates duplicate names and restrictions on PRIMARY KEY/UNIQUE, NOT NULL without a non-NULL default, references, CHECK, and generated columns; existing rows read the new default and constraints are validated where required. DROP COLUMN rebuilds the table while preserving remaining data/schema and may remove first, middle, or last nonessential columns. It refuses nonexistent, primary-key, indexed, unique, foreign-key-dependent, generated-expression-dependent, trigger/view-dependent, or otherwise referenced columns. Renaming to an existing or reserved internal object and altering a missing object error without corrupting the schema. Legacy alter-table PRAGMA settings alter dependency rewriting in the standard way.

When DROP COLUMN reparses an index expression that referred to the removed column with a double-quoted token, it preserves the quoted-identifier hint in the diagnostic. For example, after `CREATE TABLE t1(a,b); CREATE INDEX x1 ON t1("b");`, `ALTER TABLE t1 DROP COLUMN b;` exits 1 and reports exactly `error in index x1 after drop column: no such column: "b" - should this be a string literal in single-quotes?`. The same diagnostic applies when `b` was declared as `"b"` or `'b'`, and when the index expression is `"a"||"b"`.

This build also supports constraint editing with `ALTER TABLE table DROP CONSTRAINT name`, `ALTER TABLE table ADD [CONSTRAINT name] CHECK(expr)`, and `ALTER TABLE table ALTER [COLUMN] column SET NOT NULL [ON CONFLICT algorithm]` or `DROP NOT NULL`. These forms rewrite the stored `CREATE TABLE` text without changing the table's rows. Dropping a named CHECK removes that clause and the necessary adjacent comma while retaining other column/table constraints and the original surrounding spelling and spacing: for example, dropping `abc` rewrites `CREATE TABLE t1(a, b CONSTRAINT abc CHECK(t1.a != t1.b) NOT NULL)` to `CREATE TABLE t1(a, b NOT NULL)`. It also handles a named CHECK adjacent to UNIQUE, another CHECK, DEFAULT, COLLATE, REFERENCES, a generated-column clause, comments, or other named constraints. A named UNIQUE is not droppable and reports `constraint may not be dropped: ccc`; an absent name reports `no such constraint: ddd`.

`ALTER ... DROP NOT NULL` removes the column's NOT NULL clause while retaining its other constraints and is a successful no-op when that column has none. For example, `a NOT NULL ON CONFLICT FAIL UNIQUE` becomes `a UNIQUE`. `ALTER ... SET NOT NULL` appends the clause to the selected column, preserves an optional conflict policy, and is a successful no-op if the effective constraint is already present; `ALTER ... SET NOT NULL ON CONFLICT FAIL` produces `a NOT NULL ON CONFLICT FAIL`. Existing rows are validated before SET NOT NULL or ADD CHECK is committed. A preexisting NULL or a row failing a newly added CHECK reports `constraint failed` and leaves the schema unchanged. A successfully added named check is appended as in `CREATE TABLE t1(a, b, c, CONSTRAINT nn CHECK (c!=6))`, and a later violating insert reports `CHECK constraint failed: nn`.

Constraint edits preserve data and compose across repeated edits: setting NOT NULL on columns `a`, `b`, `c`, and `d` transforms `CREATE TABLE t1(a INTEGER PRIMARY KEY, b NOT NULL, c CHECK (c!=555), d)` into `CREATE TABLE t1(a INTEGER PRIMARY KEY NOT NULL, b NOT NULL, c CHECK (c!=555) NOT NULL, d NOT NULL)` without changing existing rows, and dropping those constraints restores `CREATE TABLE t1(a INTEGER PRIMARY KEY, b, c CHECK (c!=555), d)`. Invalid targets are rejected with the identifying text: `no such column: d`, `no such column: rowid`, `no such table: x2`, `no such table: temp.x1`, `constraint abc already exists`, and `no such column: z`. Constraint editing on a view reports `cannot edit constraints of view "v1"`; editing `sqlite_schema` reports `table sqlite_master may not be altered`.

## Spec 29

Database files use the SQLite format-3 on-disk format, beginning with the 16-byte signature `SQLite format 3\0`. Files produced in one invocation reopen in later invocations with all schema, data, indexes, triggers, views, pragmas stored in the header, and transaction effects intact. Page sizes from 512 through 65536, overflow records, freelists, reserved bytes, schema cookies, change counters, text encodings, application ID, and user version are interpreted correctly. Existing databases and copies created by this executable remain mutually readable.

Malformed headers, random/non-database files, truncated pages, inconsistent b-trees/freelists, bad records, corrupt indexes, malformed WAL/journal data, and other corrupt inputs must be detected and diagnosed, never crash, hang, or silently overwrite unrelated files. `PRAGMA integrity_check` and `quick_check` return `ok` on valid databases and useful rows on corrupt ones. `PRAGMA cell_size_check`, secure-delete behavior when selected, and low-level diagnostic virtual tables operate safely.

## Spec 30

Rollback-journal modes `DELETE`, `TRUNCATE`, `PERSIST`, `MEMORY`, `WAL`, and `OFF` and locking modes `NORMAL`/`EXCLUSIVE` follow their durability/locking semantics. The default file journal mode is `delete`; in-memory databases report appropriate memory mode. `PRAGMA synchronous` maps OFF=0, NORMAL=1, FULL=2, EXTRA=3. Atomic commit, statement/subjournals, cache spill, journal-size limit, busy handling, hot-journal recovery, and crashes/failures must leave either the old or committed database, not a partial logical transaction.

The default defensive configuration refuses the tested transition of a file database to journal mode OFF. On a fresh file, this input succeeds but leaves the journal mode at DELETE and emits exactly these two result lines, in order:

```
PRAGMA locking_mode = exclusive;
CREATE TABLE tx(a);
PRAGMA journal_mode = off;
```

```
exclusive
delete
```

WAL mode creates/interprets `-wal` and `-shm`, allows readers with a writer, uses checksums/salts/frame boundaries, checkpoints in PASSIVE/FULL/RESTART/TRUNCATE modes, honors `wal_autocheckpoint`, restarts/reuses logs, recovers after interrupted work, and safely handles readonly or no-shared-memory cases. `.timeout MS` and `PRAGMA busy_timeout` wait approximately as requested for locks before returning `database is locked`. Multiple test processes may operate on separate or shared files; locks, snapshots, mmap, cache flushes, and close behavior must be race-safe.

## Spec 31

Database locations include normal paths, `:memory:`, empty/transient names, named memory databases, and `file:` URIs with supported query parameters such as mode, cache, immutable, vfs, nolock, and related open flags. `-readonly`/URI `mode=ro` never create or write. `-nofollow` rejects prohibited symbolic-link traversal. Directories and inaccessible paths are rejected as database files. `-deserialize` reads a database image into memory subject to `-maxsize` while retaining normal SQL behavior.

`ATTACH [DATABASE] expression AS schema` and DETACH support file and memory databases, case-insensitive aliases, transactions spanning attached files, schema-qualified DDL/DML/queries, cross-database joins/subqueries/CTEs/compounds, and per-schema pragmas. `main` and `temp` cannot be detached; duplicate/missing aliases error; detaching a locked database errors. At most ten attached databases are allowed. `PRAGMA database_list` emits sequence, schema name, and canonical filename. `.databases` uses the shell display instead: for a writable file its line has the form `main: /canonical/path/to/file r/w`, with the colon immediately after the schema name. With a transient main database and two `ATTACH ':memory:' AS mem1`/`mem2` databases, it emits exactly `main: "" r/w`, `mem1: "" r/w`, and `mem2: "" r/w` on separate lines, without sequence columns. Views/triggers and foreign keys obey cross-schema restrictions.

## Spec 32

Core scalar functions include `abs`, `changes`, `total_changes`, `char`, `coalesce`, `concat`, `concat_ws`, `format`, `printf`, `glob`, `hex`, `unhex`, `ifnull`, `iif`, its alias `if`, `instr`, `last_insert_rowid`, `length`, `octet_length`, `like`, `likelihood`, `likely`, `unlikely`, `load_extension`, `lower`, `upper`, `ltrim`, `rtrim`, `trim`, `max`, `min`, `nullif`, `quote`, `random`, `randomblob`, `replace`, `round`, `sign`, `sqlite_compileoption_get`, `sqlite_compileoption_used`, `sqlite_offset`, `sqlite_source_id`, `sqlite_version`, `substr`/`substring`, `typeof`, `unicode`, `unistr`, `unistr_quote`, and `zeroblob`, with variadic arities where defined. `soundex` is not registered: `SELECT soundex('Robert');` exits 1 with a diagnostic containing `no such function: soundex`. The `if` alias has the same conditional and short-circuit semantics as `iif`: `if(NULL,8,99)` and `if(0,8,99)` return `99`, while the two-argument `if(1,'true')` returns `true`.

They implement 3.54 coercion, NULL propagation, Unicode/byte counting distinctions, negative substring indices/lengths, embedded NUL behavior, escaping, format specifiers and flags, deterministic/nondeterministic classification, and errors for wrong arity/type. LIKE is ASCII-case-insensitive by default, supports `%`, `_`, and a one-character ESCAPE; GLOB uses Unix `*`, `?`, and bracket classes and is case-sensitive. `PRAGMA case_sensitive_like` can make LIKE case-sensitive. Pattern limits are enforced. `quote` produces restorable SQL literals and `unistr` interprets its supported backslash Unicode escapes.

## Spec 33

Enabled math functions include `acos`, `acosh`, `asin`, `asinh`, `atan`, `atan2`, `atanh`, `ceil`/`ceiling`, `cos`, `cosh`, `degrees`, `exp`, `floor`, `ln`, `log`, `log10`, `log2`, `mod`, `pi`, `pow`/`power`, `radians`, `sin`, `sinh`, `sqrt`, `tan`, `tanh`, and `trunc`. They coerce numeric values, return NULL for NULL or out-of-domain inputs as the engine specifies, handle infinities/NaN without invalid shell text, and approximate results to binary64 accuracy. `log(x)` is base 10 and the two-argument form uses the requested base. In default list-mode rendering, `SELECT log(100);` outputs exactly `2.0` followed by newline. Division/modulo/sign/round corner cases agree with SQL numeric conversion.

Date/time functions `date`, `time`, `datetime`, `julianday`, `unixepoch`, `strftime`, and `timediff` accept ISO-8601 text, Julian day numbers, Unix timestamps with modifiers, timezone suffixes, fractional seconds, and NULL. Modifiers include signed units, start-of day/month/year, weekday N, unixepoch, julianday, auto, localtime, utc, subsec/subsecond, ceiling, and floor. They handle leap years, century rules, month/year rollover ambiguity, negative/large offsets, chained modifiers, 24-hour wrapping, supported year range, and all supported strftime substitutions including `%%`. `now`, CURRENT_DATE/TIME/TIMESTAMP are consistent within a statement. Invalid dates/modifiers return NULL rather than crash.

## Spec 34

JSON text and JSONB are built into SQL. Constructors and inspectors include `json`, `jsonb`, `json_array`, `jsonb_array`, `json_object`, `jsonb_object`, `json_quote`, `json_valid`, `json_error_position`, `json_type`, `json_array_length`, and extraction operators/functions `json_extract`, `jsonb_extract`, `->`, and `->>`. Mutation includes `json_insert`, `json_replace`, `json_set`, `json_remove`, `json_patch` and JSONB counterparts. Aggregates include `json_group_array`, `json_group_object`, `jsonb_group_array`, and `jsonb_group_object`. Table-valued `json_each` and `json_tree` expose key, value, type, atom, id, parent, fullkey, path, and hidden input/path columns.

JSON paths support `$`, object members (including quoted/special names), zero-based array indices, `[#]`, and `[#-N]`. One-path extraction returns an SQL scalar for JSON strings/numbers/null and JSON text/blob for arrays/objects; multiple paths return a JSON array. Mutators distinguish ordinary SQL text (quoted as a JSON string) from values carrying a JSON subtype. JSON5 input is accepted where 3.54 permits while canonical output is compact JSON. Duplicate keys, Unicode escapes, control characters, deep nesting limits, numeric boundaries, malformed text/JSONB/path errors, and subtype preservation follow the target behavior. JSONB is opaque binary data but all JSON functions accept it and produce equivalent logical results efficiently.

The JSON nesting limit is exactly 1000 array/object levels. `json_valid` returns 1 for the 1000-level array produced by `printf('%.1000c0%.1000c','[',']')` and 0 for its 1001-level counterpart; replacing each opening bracket by `{"a":` and each closing bracket by `}` gives the same 1/0 boundary for objects. `json_valid(NULL)` returns SQL NULL, rendered as an empty field in default list mode. `json_valid(X,Y)` accepts a flags argument: bit `0x01` recognizes canonical JSON text, bit `0x02` recognizes JSON5 text, bit `0x04` recognizes JSONB by its superficial binary signature, and bit `0x08` performs strict JSONB validation. Thus `json_valid('{"a":1}',1)` is 1, `json_valid('{a:1}',1)` is 0, `json_valid('{a:1}',2)` is 1, and `json_valid(jsonb('{"a":1}'),5)` is 1. The deliberately damaged blob `x'4C176113FF'` returns 1 with flag 4 but 0 with flag 8.

Malformed-path diagnostics use this build's exact wording. `SELECT json_extract('{"":8}', '$.');` exits 1 and reports `bad JSON path: '$.'`.

The `id` values of JSON virtual-table rows are part of this version's output. Each of these four forms—`SELECT * FROM JSON_EACH('{"a":1, "b":2}')`, selecting `xyz.*` through an alias, and the corresponding two parenthesized `JSON_EACH(...)` forms—returns exactly:

```
a|1|integer|1|1||$.a|$
b|2|integer|2|5||$.b|$
```

JSON mutation also includes `json_array_insert(JSON,PATH,VALUE,...)`. It inserts immediately before an addressed array element, applies path/value pairs from left to right to the evolving value, and returns compact JSON. On `[1,2,3]`, insertion at `$[0]`, `$[1]`, `$[2]`, and `$[3]` produces `[888,1,2,3]`, `[1,888,2,3]`, `[1,2,888,3]`, and `[1,2,3,888]`; `$[#]` appends. Paths `$[#-1]`, `$[#-2]`, and `$[#-3]` insert before the last, second-last, and first elements respectively, while the out-of-range `$[#-4]` leaves `[1,2,3]` unchanged. Applying `'$[0]',999,'$[0]',888` produces `[888,999,1,2,3]`, while `'$[0]',999,'$[#]',888` produces `[999,1,2,3,888]`.

For object input `{a:[1,2,3]}`, `$.b[0]` creates `{"a":[1,2,3],"b":[888]}` and `$.b.c.d[0]` creates `{"a":[1,2,3],"b":{"c":{"d":[888]}}}`. `$[0]` against that object is a successful no-op. A path that does not address or create an array element is an error: `$.a`, `$.b`, `$.b.c.d[0`, and `$.b.c.d` respectively report `not an array element: '$.a'`, `not an array element: '$.b'`, `not an array element: '$.b.c.d[0'`, and `not an array element: '$.b.c.d'`. In the multi-edit call using `$.b[0]`, `$.a[1]`, and then `$.c`, the last path reports `not an array element: '$.c'` and the call fails.

## Spec 35

Blobs are arbitrary byte strings. Blob literals, `zeroblob`, `randomblob`, hex/unhex, quote, substr, length, octet length, concatenation, cast, equality/order, IN, grouping, DISTINCT, indexes, joins, primary/unique keys, triggers, and JSON shell serialization preserve bytes. Text-versus-blob comparison follows storage-class, affinity, and operator conversion rules; BLOB input to LIKE or GLOB is not an unconditional nonmatch. `SELECT X'3132',typeof(X'3132'),CASE WHEN X'3132' LIKE '12%' THEN 'matches' ELSE 'no_match' END,CASE WHEN X'3132' GLOB '12*' THEN 'matches' ELSE 'no_match' END;` outputs exactly `12|blob|matches|matches`. After storing numeric 0 in a REAL column `t0.c0`, `SELECT CAST(+t0.c0 AS BLOB) LIKE '0.0' FROM t0;` returns `1`, including when an index on `(+c0,c0)` exists. Large blobs use overflow pages and enforce the one-billion-byte length limit without over-allocation or crash.

Shell-added functions include `readfile(path)`, `writefile(path,data[,mode[,mtime]])`, `base64(value)`, `base85(value)`, `is_base85(value)`, `sha1(value)`, `sha1_query(sql)`, `sha3(value[,bits])`, `sha3_query(sql[,bits])`, `sha3_agg(value[,bits])`, `decimal`, `decimal_add`, `decimal_sub`, `decimal_mul`, `decimal_exp(value[,digits])`, `decimal_cmp`, `decimal_sum`, `ieee754`, `ieee754_mantissa`, `ieee754_exponent`, `ieee754_from_blob`, and `lsmode`. They preserve binary/text distinctions, validate arguments, implement supported SHA3 sizes (224/256/384/512), stable query hashing and aggregate hashing, exact decimal string arithmetic/ordering/aggregation and exponential rendering, IEEE-754 decomposition/reconstruction from numbers or blobs, and Unix mode rendering. The shell-added `pow2` function is absent: `SELECT pow2(10);` exits 1 with a diagnostic containing `no such function: pow2`. `sha1_query('SELECT 1')` returns a lower-case 40-hex-character digest, and `sha3_agg` is an aggregate (over the two values `a` and `b`, `hex(sha3_agg(x))` is `92540E8B149F6CDF96334282E7D4436858E59DF5B4F6C023707073AE32DE4EB9`). Decimal arithmetic normalizes scientific-notation operands to ordinary exact decimal text, so `decimal_add('1.2e3','0')` returns `1200`. `decimal_exp` accepts either one argument or a second precision argument; a positive precision requests that many significant digits for rounding. `SELECT decimal_exp('123.456'),decimal_exp('123.456',3);` returns `+1.23456e+02|+1.23e+02`.

`base64(BLOB)` uses the standard alphabet and `=` padding, wraps at 72 encoded characters, and terminates every encoded line, including the last, with LF. Thus `base64(x'000102030405')` is the text `AAECAwQF\n`, a 1054-byte blob encodes to a value of length 1428, and summing `length(base64(randomblob(n)))` for `n` from 1 through 5000 yields `16910656`. Text input decodes to a blob; surrounding whitespace and omitted padding are accepted, so `base64(' AAECAwQ')` decodes to hex `0001020304` and `base64('AAECAw ')` decodes to `00010203`.

`base85(BLOB)` uses, in code-point order, the four characters from `#` through `&` followed by every character from `*` through `z`; it has no padding, wraps at 80 encoded characters, and likewise ends its final line with LF. The vectors for blobs `000102030405`, `0001020304`, and `00010203` are respectively `##/2,#2/\n`, `##/2,#*\n`, and `##/2,\n`. A 1054-byte blob therefore encodes to length 1335. Base85 text decodes the same values with surrounding whitespace accepted. `is_base85` returns 1 only when text consists of that alphabet plus whitespace: the complete alphabet string used above returns 1, while each of `!`, `"`, `'`, `(`, `)`, `{`, `|`, `}`, `~`, and DEL returns 0; NULL returns NULL and non-text input errors. File-writing functions obey safe mode and return the normal byte count or NULL/error behavior.

## Spec 36

Regular expression support registers SQL `regexp(pattern,text)`, `regexpi(pattern,text)`, and the infix `text REGEXP pattern`. It supports literals, `.`, anchors `^`/`$`, bracket classes and negation/ranges, grouping, alternation, quantifiers `* + ? {m,n}`, word/space/digit classes as implemented, escapes including hexadecimal, and Unicode text. Case-insensitive matching by `regexpi` folds ASCII letters, not non-ASCII Unicode letters: `SELECT regexpi('^abc$','ABC'),regexpi('^[a-z]+$','ABC'),regexpi('^äbc$','ÄBC'),regexpi('^é$','É');` outputs exactly `1|1|0|0`. Invalid patterns error cleanly; NULL yields NULL. REGEXP can be used in WHERE, joins, CASE, generated query expressions, and indexes where deterministic rules permit.

The `generate_series` eponymous table-valued function emits inclusive integer sequences with columns/value semantics compatible with `generate_series(start,stop[,step])`. Default and explicit positive/negative steps, descending ranges, incompatible direction yielding no rows, filters, joins, aggregates, and hidden start/stop/step columns are supported. Integer bounds/overflow are safe. Other tabular functions enabled by the build, including pragma table-valued forms, accept equality constraints and expose their declared schemas.

## Spec 37

FTS3 and FTS4 virtual tables are available via `CREATE VIRTUAL TABLE ... USING fts3(...)` and `fts4(...)`. They support multiple columns, implicit/explicit docid, contentless/external-content arrangements used by the tests, languageid, prefix indexes, matchinfo configuration, porter/simple/unicode61 tokenizers available in the build, and INSERT/UPDATE/DELETE/REPLACE/rename/drop/optimize/rebuild/integrity-check control commands.

`MATCH` supports terms, phrases, prefixes, column filters, boolean operators, parentheses where enabled, and NEAR queries with correct case/token/Unicode behavior. Auxiliary functions `snippet`, `offsets`, `matchinfo`, and `optimize` return correct formats and may be used for ranking. Deferred tokens, segment merges, incremental merge, automerge, first-token behavior, ordering, joins, transactions, rollback, shared connections, large documents, and malformed/corrupt FTS shadow data are handled consistently and safely. FTS queries over empty tables emit no rows. FTS4 is required; FTS5 is not.

The shell connection keeps the legacy FTS3 tokenizer mutation interface disabled. A literal-name lookup `SELECT typeof(fts3_tokenizer('simple'));` returns `null`; attempting `SELECT fts3_tokenizer('blah', fts3_tokenizer('simple')) IS NULL;` exits 1 with `fts3tokenize disabled`. FTS shadow tables are protected from user triggers: after creating FTS3 table `z1`, `CREATE TRIGGER z1r1 AFTER DELETE ON z1_content BEGIN DELETE FROM z1; END;` exits 1 with `cannot create triggers on shadow tables` and does not create the trigger.

## Spec 38

RTree virtual tables are available through `rtree` and integer-coordinate `rtree_i32`. They support two through five dimensions, auxiliary `+column` data, insertion/update/delete, rowid uniqueness, joins and subqueries, and indexed overlap/containment predicates using lower/upper coordinate pairs. Floating RTree coordinates use outward-rounded 32-bit float bounds, so boundary and large-coordinate behavior follows that representation; rtree_i32 uses signed 32-bit integer coordinates. Invalid dimension declarations, coordinate ordering, and constraint violations error.

The separate `geopoly` module and its `geopoly_*` functions are not registered in this build: creating a geopoly virtual table fails with `no such module: geopoly`. RTree shadow tables, transactions, savepoints, rename/drop, corruption checks, and query planning remain coherent.

## Spec 39

Diagnostic virtual tables required by the build are available:

- `dbstat` walks database b-trees and reports schema name, object/path, page number/type, cells, payload/unused/mx_payload, page offset, and page size; aggregate mode and per-table filtering work.
- `sqlite_dbpage` exposes raw fixed-size pages by schema and permits the controlled page updates supported by the module, with bounds/schema validation.
- `sqlite_dbdata` and `sqlite_dbptr` are not registered in this build. Querying either as a table exits 1 with no stdout and reports respectively `no such table: sqlite_dbdata` or `no such table: sqlite_dbptr` on stderr.
- `sqlite_stmt` reports currently prepared statements and counters.
- `bytecode(SQL)` and related tables expose VDBE opcodes and subprograms for simple and complex statements.

The `sqlite_dbpage` name is available, but the unrelated bare table name `dbpage` is not and yields `no such table: dbpage`. `.dbinfo`, `.filectrl`, `.vfsinfo`, `.vfslist`, and `.vfsname` expose current database/VFS metadata. For a normal one-table database, `.dbinfo` includes its labels in this order: `database page size:`, `write format:`, `read format:`, `reserved bytes:`, `file change counter:`, `database page count:`, `freelist page count:`, `schema cookie:`, `schema format:`, `default cache size:`, `autovacuum top root:`, `incremental vacuum:`, `text encoding:`, `user version:`, `application id:`, `software version:`, `number of tables:`, `number of indexes:`, `number of triggers:`, `number of views:`, `schema size:`, and `data version`. `.vfslist` is a detailed multi-line report, not merely a list of names: each VFS block begins with a line labeled `vfs.zName`, followed by `vfs.iVersion`, `vfs.szOsFile`, and `vfs.mxPathname`. It lists at least `unix`, `apndvfs`, `memdb`, `unix-excl`, `unix-dotfile`, and `unix-none` in that order. `.dbtotxt`, `.recover`, `.intck`, `.clone`, and `.check` perform their 3.54 shell diagnostic/recovery roles, including empty/clean databases and controlled corruption, without crashing. Test-only or external virtual-table modules not included in Spec 2 remain unavailable and yield normal errors until explicitly loaded. Dynamic extension loading must use the SQLite extension ABI so a supplied `spellfix.so` and `nextchar.so` can register `spellfix1` and `next_char`; spellfix supports its word/language/rank/distance/score/matchlen command columns, edit-cost tables, prefix matching, update/delete/rowid operations, and ordered best-match queries, while `next_char(prefix,table-or-query,column[,where[,collation]])` returns the distinct possible next characters in collation order.

## Spec 40

PRAGMA assignment and query syntax works in bare, parenthesized, schema-qualified, and table-valued forms. Required metadata pragmas include `table_info`, `table_xinfo`, `table_list`, `index_list`, `index_info`, `index_xinfo`, `database_list`, `foreign_key_list`, `foreign_key_check`, `collation_list`, `function_list`, `module_list`, and `pragma_list`, with correct column count/order/flags, generated/hidden columns, autoindex origin (`pk`, `u`, `c`), expression-index cid values, and schema filtering.

Required configuration/header pragmas include `application_id`, `user_version`, `schema_version`, `data_version`, `page_size`, `page_count`, `max_page_count`, `freelist_count`, `cache_size`, `cache_spill`, `default_cache_size`, `mmap_size`, `temp_store`, `encoding`, `auto_vacuum`, `incremental_vacuum`, `journal_mode`, `journal_size_limit`, `locking_mode`, `synchronous`, `wal_autocheckpoint`, `wal_checkpoint`, `read_uncommitted`, `query_only`, `recursive_triggers`, `reverse_unordered_selects`, `trusted_schema`, `secure_delete`, `legacy_alter_table`, `defer_foreign_keys`, `ignore_check_constraints`, `busy_timeout`, `analysis_limit`, `optimize`, `integrity_check`, and `quick_check`. Values persist only for the correct connection/file scope, textual aliases map to numeric values, invalid/unknown pragmas behave as the engine does (unknown pragmas normally return nothing), and changes do not silently violate active-transaction restrictions.

`PRAGMA writable_schema` obeys the shell's default defensive configuration. `PRAGMA writable_schema=1` does not enable schema writes in that configuration and a subsequent query still returns `0`; direct `DELETE` or `UPDATE` of `sqlite_master`/`sqlite_schema` is rejected with status 1 and `table sqlite_master may not be modified`. `PRAGMA writable_schema=RESET` is accepted, disables writable-schema mode, reloads the connection's schema state, and leaves the queried value at `0`; it is valid inside the transaction sequence `PRAGMA schema_version=0; PRAGMA writable_schema=RESET;` and that sequence itself produces no diagnostic.

## Spec 41

Schema/introspection dot commands include `.tables [PATTERN]`, `.indexes [PATTERN]`, `.schema [PATTERN] [--indent]`, `.fullschema [--indent]`, `.databases`, `.dbinfo`, and `.dump [OPTIONS] [PATTERN ...]`. Patterns use the shell’s LIKE/GLOB-style matching. The `.indexes` pattern matches index names themselves: after creating `idx_a` and `idx_b`, `.indexes idx_a` outputs `idx_a`. Listings include appropriate tables, views, virtual tables, shadow tables, and indexes in stable shell order and suppress internal objects where the command normally does. Attached schemas are represented correctly.

`.schema` emits restorable CREATE statements. `.fullschema` also includes statistics. `.dump` emits a restorable SQL transaction containing schema and data, quoting identifiers/text/blobs/NULL exactly, handling generated/virtual/WITHOUT ROWID/STRICT tables, views, triggers and indexes, and accepting table patterns. Ordinary identifiers that do not require quoting remain bare in generated INSERT statements: dumping table `t` produces `INSERT INTO t VALUES(1,'x');`, and `.dump t1` produces `INSERT INTO t1`, not double-quoted table names. `.dump --nosys` is an option rather than a table pattern; it omits system objects while still including ordinary user tables and their data. Empty and nonexistent matches behave normally. `.help [PATTERN]` lists or filters dot-command help; `.help mode` succeeds and its detailed `.mode` help contains the literal mode name `csv`. `.show` reports current echo, eqp, explain, headers, mode, nullvalue, output, separators, stats and width settings.

## Spec 42

`.import` reads CSV, tabs, ASCII separators, or custom column/row separators into a named table. If the table is absent, the first input row supplies column names and later rows become data; duplicate/empty headings are made legal and unique as the shell specifies. If present, all rows append and pass through affinities, STRICT checks, constraints, indexes, and triggers. CSV handles quotes, doubled quotes, commas/newlines inside quoted fields, CRLF/LF/mixed endings, UTF-8 and a leading UTF-8 BOM, empty fields, no final newline, long lines, and large files.

Options include `--csv`, `--ascii`, `--skip N`, `--schema NAME`, `--verbose`, `--escape`, `--qesc CHAR`, and inline/here-document content supported by the 3.54 shell. Too few fields are filled with NULL and too many are ignored with the standard warning behavior. Missing/empty input, bad option arity, target mismatches, and constraint failures produce correct diagnostics and status. `.mode csv` before a plain import selects CSV parsing. Export is achieved by selecting in CSV/tabs/etc. mode or by `.dump`; it round-trips quoted and Unicode data.

## Spec 43

Backup/file-management commands operate on real database images. `.backup [DB] FILE` creates a consistent copy; `.save FILE` saves an in-memory database; `.restore [DB] FILE` replaces the selected database from a valid copy; `.open [OPTIONS] FILE` closes/switches the current connection and creates a file when allowed; `.clone NEWDB` clones a readable database. Invalid targets or sources error and leave the original usable. `.open --readonly`, `--new`, `--nofollow`, `--deserialize`, and related tested forms obey their safety meanings.

The shell archive feature (`.archive`) creates, lists, verbosely lists, inserts/replaces, removes, and extracts ZIP-format SQL archives. Command-line `-A` passes its remaining archive arguments to this feature: `executable ARCHIVE -A --create FILE1 FILE2` creates the archive and exits 0, and the corresponding `--list` operation lists its members. It preserves file content and directory structure, records metadata/mode/mtime as supported, accepts selection patterns, and rejects unsafe extraction paths. The `zipfile` virtual table exposes archive name, mode, mtime, size, raw data, method, and directory behavior and supports SELECT/INSERT/UPDATE/DELETE, transactions, ordering, compression methods, blobs, empty archives, and corruption/error handling. Command-line `-zip ARCHIVE` opens an existing ZIP in shell ZIP mode: `.tables` outputs `zip`, SQL can query `zip` (two members named `hello.txt` and `world.txt` are returned in that `ORDER BY name` order), and `.schema` emits a statement beginning `CREATE VIRTUAL TABLE zip USING zipfile(` with the archive path followed by `/* zip(name,mode,mtime,sz,rawdata,data,method) */;`.

## Spec 44

Advanced shell state includes `.parameter init|set|unset|clear|list`. Parameter names beginning `:`, `@`, `$`, or `?` bind into later SQL. `set` first interprets a legal SQL literal/expression (integer, real, NULL, blob, or quoted text) and otherwise stores text; list shows stable name/value representations. Clear/unset remove bindings. Positional and named parameters not set become NULL under shell binding behavior.

`.connection [close] [N]` creates, lists, switches, and closes multiple independent database connections while retaining their own schema/transaction state and the appropriate shared shell settings. `.dbconfig` lists boolean database configuration switches and can query/toggle names such as foreign-key enablement. `.limit [NAME [VALUE]]` lists current engine limits or adjusts a named limit within hard bounds. `.auth on|off` enables/disables authorizer trace output. `.progress N [--limit M] [--once] [--quiet] [--reset]` installs and controls a progress handler. `.testcase NAME` and `.check` with exact/glob/notglob/here-document/show forms compare captured output and report pass/fail. `.lint fkey-indexes` diagnoses missing child-key indexes. `.expert` analyzes supplied queries and prints useful CREATE INDEX advice or `(no new indexes)` when none is useful. `.sha3sum [--schema] [--sha3-N] [PATTERN]` deterministically hashes selected database content.

## Spec 45

All syntax, planner, storage, shell, and extension behavior above must compose rather than work only in isolation. In particular, tests may create state in one process, reopen it in another, execute many sequential commands against one database, combine joins/CTEs/windows/JSON/FTS/indexes/triggers/foreign keys/upsert/RETURNING, alter schemas inside transactions, inspect the resulting schema or raw pages, and compare exact list-mode stdout. Explicit `ORDER BY` determines output order; without it, the target engine’s stable 3.54 plan order is required wherever shell or planner regression output is checked.

The implementation must be robust under databases with thousands of rows, very wide queries, large text/blob values, many generated join/window combinations, malformed SQL, invalid database files, resource-limit boundaries, concurrent file access, and intentional I/O or constraint failures. It must finish ordinary cases well within five seconds and larger grouped cases within sixty seconds, must not deadlock or leak a child process, and must never crash on a user-level error. Diagnostics must use the SQLite shell style—typically `Parse error near line N: ...`, `Runtime error near line N: ...`, `Error: ...`, or `Usage: ...`—with the relevant object/token and caret/context where produced. Exact errors go to stderr, successful rows to stdout, and database mutations before/after errors obey the transaction, bail, and conflict rules in this specification.
