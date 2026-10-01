# `agrind` executable specification

This document is the complete contract for a command-line log processing program named
`executable`.  No other documentation is required.  “Line” below means an input record
terminated by `\n`; a final unterminated line is also a record.  Unless an error is
specified, successful commands exit with status 0.  Every emitted record or table ends
with `\n`.

The language consists of an initial text filter followed by zero or more operators,
separated by `|`:

```text
FILTER [ | OPERATOR ... ]
```

Operators execute strictly from left to right.  Record-producing and aggregate stages
may be freely chained; an aggregate table is itself a stream of records for following
`where`, `fields`, `sort`, `limit`, or another aggregate. Both an aggregate stage and
`sort` switch the stream to “tabular” presentation; later row-wise stages retain that
presentation.

## Spec 1: Command-line interface and input

Invocation is:

```text
executable [OPTIONS] [QUERY]
```

Supported options are `-f FILE`/`--file FILE`, `-o OUTPUT`/`--output OUTPUT`, deprecated
`-m FORMAT`/`--format FORMAT`, `-a DIR`/`--alias-dir DIR`, `--no-alias`, `-h`/`--help`,
and `-V`/`--version`. Options may occur before or after the query. Exactly zero or one
file is allowed. With a file, read it instead of stdin (even if stdin also contains
data); without one, read stdin. A repeated `-f` is a command-line error. Input is read
lossily as UTF-8: invalid byte sequences become U+FFFD, while readable text around them
is preserved. Lines of 100,000 characters and inputs of at least 100,000 records must
work without truncation or unreasonable delay. A positive `limit` does not stop input
reading or let the process terminate before EOF, even after enough rows have passed it.

No query exits nonzero and writes exactly `Error: MissingQuery\n` to stderr. A missing
input file exits 1, writes nothing to stdout, and writes exactly
`Error: Os { code: 2, kind: NotFound, message: "No such file or directory" }\n` to
stderr (the missing path is not included). Repeating `--file` produces the normal CLI
diagnostic beginning
`error: the argument '--file <FILE>' cannot be used multiple times`. Unknown flags are
rejected by the CLI parser and show the offending flag, a value-passing tip, usage, and
the `--help` hint. In particular, `executable --invalid-flag` exits 2 and writes exactly:

```text
error: unexpected argument '--invalid-flag' found

  tip: to pass '--invalid-flag' as a value, use '-- --invalid-flag'

Usage: executable [OPTIONS] [QUERY]

For more information, try '--help'.
```

`--version` prints exactly `ag 0.19.6\n`. `--help` exits 0, writes nothing to stderr,
and writes exactly the following to stdout, including the shown wrapping and blank
lines:

```text
Usage: executable [OPTIONS] [QUERY]

Arguments:
  [QUERY]
          The query

Options:
  -f, --file <FILE>
          Optionally reads from a file instead of Stdin

  -m, --format <FORMAT>
          DEPRECATED. Use -o format=... instead. Provide a Rust std::fmt string to format output

  -o, --output <OUTPUT>
          Set output format. Options: 
          - `json`,
          - `logfmt`
          - `format=<rust format string>` (eg. -o format='{src} => {dst}'
          - `legacy` The original output format, auto aligning [k=v]

  -a, --alias-dir <ALIAS_DIR>
          Specifies an alternative directory to use for aliases. Defaults to `.agrind-aliases` in all parent directories.

      --no-alias
          Disables aliases

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version

For more details + docs, see https://github.com/rcoh/angle-grinder
```

`-h` may be abbreviated help but must include `Usage:` and `QUERY`. Empty input is not
an error. With a non-aggregate query it emits nothing; with an aggregate stage it emits
`No data\n`.

## Spec 2: Records and values

Each input starts as a record containing its raw line. A query having only a filter
prints each matching line after lossy UTF-8 decoding and after removing trailing
whitespace from that record. Thus the input records `"   \n"`, `"\t\n"`, and
`"  \n"` produce exactly `"\n\n\n"`. Parsing operators replace that implicit
presentation with named fields.

Values are: null/None, Boolean, signed integer, floating point, string, UTC/date-time,
duration, array, and object. JSON objects and arrays retain nesting and types. Integral
floating values normalize to integers (`3.0` becomes `3`); `-0` becomes `0`. Calculated
addition or subtraction involving floats retains a float result even when it is
integral (`1.5 + 2.5` renders as `4.00` in legacy output); exact integral results of
multiplication and division normalize to integers. Values compare in this cross-type
rank:

```text
None < Boolean < number (integer and float together) < string
     < date-time < duration < array < object
```

Within a type: `false < true`, numbers compare numerically across integer/float types,
strings compare lexicographically and case-sensitively, dates chronologically, durations
by length, and objects have deterministic ordering. Two arrays do not compare their
elements: they compare equal for sorting purposes, so a stable sort preserves their
input order in both ascending and descending sorts.

Field references use `a`, nested dot access `a.b.c`, and zero-based array access
`a[0]`. Negative indices count from the end (`a[-1]` is last). A literal field name
containing punctuation, quotes, periods, or spaces is written `['name']` or
`["name"]`, for example `["grpc.method"]`, `["start time"]`, and
`nested.["user.name"]`. In aggregate headings preserve that spelling. Accessing a
missing field in an expression is a runtime error. Indexing past either end says
`error: Index N out of range`; indexing a scalar says
`error: Expected array, found VALUE`; dot access on a scalar says
`error: Expected object, found VALUE`. A missing key is exactly
`error: No value for key "NAME"\n`. The deliberate exceptions are field selection
(omit it), aggregate grouping expressions (use a null group key), and aggregate value
expressions (supply no value to that aggregate rather than aborting it), and sort-key
expressions (an absent sort key emits no error and is ordered as detailed in Spec 13).
Function arguments are not exceptions: a missing argument to `isNull`, `isEmpty`,
`isBlank`, or `contains` produces the usual missing-key runtime error and drops that
row.

## Spec 3: Initial text filters

Filters operate on the original complete line, before all pipeline operators.

- `*` and the empty quoted string match every line. Unquoted `true` and `false` are
  ordinary case-insensitive substring terms, not filter constants: on input
  `true\nTRUE story\nfalse\nFALSEhood\nother\n`, filter `true` emits the first two
  records and filter `false` emits the next two.
- An unquoted word/pattern is a case-insensitive substring glob. `*` matches any
  sequence, so `err*input` matches text containing `err`, followed later by `input`.
- A single- or double-quoted phrase is a case-sensitive literal substring. Asterisks
  inside it are literal: `"*STAR*"` only matches lines containing those asterisks.
- Combine filters with uppercase `AND`, `OR`, prefix `NOT`, and parentheses. `NOT`
  binds most tightly, then `AND`, then `OR`; parentheses override precedence.
- Adjacent filter terms separated only by whitespace are an implicit `AND`, with the
  same precedence as explicit `AND`. Thus `db-1 response` keeps only lines containing
  both case-insensitive terms.

Examples: `(error OR warn) AND NOT timeout` keeps error/warn lines other than those
containing timeout; `"ERROR"` does not match lowercase `error`. With no operators,
matching raw lines are output in input order. An unterminated parenthesized filter or
quoted literal is a parse error.

## Spec 4: JSON parsing

`json` parses the raw line as JSON. `json from EXPR` instead evaluates `EXPR` and parses
its string value. Parenthesized syntax such as `json()` is invalid. Each object member
becomes a record field. `json from EXPR` retains every pre-existing field, including
the source field, and adds/replaces members from the parsed object. For example,
`* | logfmt | json from payload` on `payload="{\"x\":7}"` produces the JSON record
`{"payload":"{\"x\":7}","x":7}`. Objects, arrays, strings (including Unicode and
JSON escapes), Booleans, null, signed 64-bit integers, and floats are preserved.
Whitespace around a JSON value is accepted. A root JSON value that is not an object
creates an empty record; thus input `[1,2]` renders as `{}` in JSON output.

A malformed line is dropped, processing continues, the command still succeeds, and
stderr receives one line:

```text
error: Expected JSON, found THE ORIGINAL LINE
```

For example, valid/object, `not valid json`, valid/object produces both valid output
records and `error: Expected JSON, found not valid json\n` on stderr. `json from` with
no expression exits 1 and begins its diagnostic exactly
`error: expecting an expression that supplies a JSON-encoded string`, with a source
annotation on `from` saying `should be followed by an expression`, then ends with
`Error: Failed to parse query`.

JSON numeric conversion follows the executable's signed-integer representation:
`1.7976931348623157e+308` saturates to `9223372036854775807`, very tiny values such as
`2.2250738585072014e-308` normalize to `0`, and `1.23e10` becomes `12300000000`.

## Spec 5: logfmt parsing

`logfmt` parses the raw line; `logfmt from EXPR` parses a field/string expression.
`logfmt()` is invalid. Bare `logfmt from` exits 1 and begins its diagnostic exactly
`error: expecting an expression that supplies a logfmt-serialized string`, with a
source annotation on `from` saying `should be followed by an expression`, then ends
with `Error: Failed to parse query`. Parse whitespace-separated keys and `key=value`
pairs. Double-quoted values may contain spaces and `\"`; remove their surrounding
quotes and decode escapes. Unquoted integers, floats, `true`, and `false` convert to
typed values. Parsing `logfmt from EXPR` retains every pre-existing field, including
the source field, and adds/replaces the parsed fields. Ordinarily, bare words become
keys with null values. Empty assignments follow the tokenizer's adjacency behavior:
at end of line `empty=` and `quoted=""` are retained as empty strings; if immediately
followed by a bare word, that word becomes the assignment's string value, so
`quoted="" bare` produces `{"quoted":"bare"}` and no `bare` field; if followed by
another assignment, the empty assignment is omitted. Thus the adjacent assignments in
`empty= null_val= number=-42.7` leave only `number`.

Examples (JSON output is shown and its keys are sorted):

```text
level=info msg="server started" port=8080
=> {"level":"info","msg":"server started","port":8080}

just plain text no key-value pairs
=> {"just":null,"key-value":null,"no":null,"pairs":null,"plain":null,"text":null}

empty= null_val= number=-42.7
=> {"number":-42.7}
```

Compatibility with the underlying logfmt tokenizer is required for URLs: the input
`spaces="value with spaces" url=https://example.com/path?query=1` yields
`{"https://example.com/path?query":1,"spaces":"value with spaces"}`.

## Spec 6: Pattern and regular-expression parsing

Plain parsing syntax is:

```text
parse "PATTERN" [from EXPR] as field1, field2, ... [nodrop] [noconvert]
```

Single quotes may delimit the pattern too. Every `*` is one capture and the number of
captures must exactly equal the number of output fields. Literal pattern text must
occur in order; nonfinal captures span up to the next literal and the last capture
consumes the remaining match. Pattern whitespace matches any input whitespace, so a
space also matches a tab. By default the source is the raw line. For example
`parse "* *" as level, rest` on `INFO some text here` produces `level=INFO` and
`rest=some text here`; the standard Apache pattern shown in Spec 17 produces all of
its named fields.

Captured text is converted in order to integer, float, or Boolean when possible;
otherwise it remains a string. `noconvert` keeps all captures as strings (important
for values such as `00000`). Without `nodrop`, a nonmatching row is discarded. With
`nodrop`, it remains and the capture fields are null/`None`. Two `from` clauses are an
error. A mismatch reports `Error: Wrong number of patterns for parse. Pattern has N
but M were extracted` (after any detailed parser diagnostic). Missing `as` fields,
an unquoted pattern, and unterminated strings are parse errors.

Regular-expression parsing is:

```text
parse regex "REGEX" [from EXPR] [nodrop] [noconvert]
```

Use Rust-regex-compatible syntax. It searches the source and adds one field for every
named capture such as `(?P<duration>\d+)`; captures are converted just like plain
parse. Optional unmatched groups become null. Every capturing group must be named;
unnamed groups are rejected. Regex syntax is validated before reading input. Regex
mode does not accept `as`. It does accept `noconvert`, with the same meaning as plain
parsing: for example, capture `00042` becomes integer `42` without the flag and string
`"00042"` with it. `from` changes the source and `nodrop` has the same meaning as above.

## Spec 7: Splitting

Syntax is:

```text
split[(SOURCE_EXPR)] [on "SEPARATOR"] [as FIELD]
```

The default separator is `,`. With no source expression, split the raw line and store
the array in `_split`. With a source expression and no `as`, replace that source field;
with `as`, preserve the source and store the array in the named field. The separator
may have multiple characters. Quoted input tokens are kept together and lose their
quotes (`"hello world" foo` split on space starts with `hello world`, then `foo`).
Empty pieces are discarded, including leading, internal, and trailing pieces:
splitting `name..power` on `.` yields `["name","power"]`, `.a.` yields `["a"]`, and
`..` yields `[]`. Array results support positive and negative indexing. `split()` with
no argument exits 1 and reports
`error: this operator takes 1 argument, but 0 were supplied`; its source annotation
says `supplied 0 arguments`, and the diagnostic ends with
`Error: Failed to parse query`. `split on` without a quoted separator is also invalid.

Example:

```text
INFO name.power.over_9000
* | parse "* *" as level, rest | split(rest) on "." as parts
=> [level=INFO] ... [parts=[name, power, over_9000]] ... [rest=name.power.over_9000]
```

## Spec 8: Field selection and calculated fields

All of these select only named fields:

```text
fields a, b
fields only a, b
fields + a, b
```

All of these remove named fields:

```text
fields except a, b
fields - a, b
```

Selection or exclusion applies to ordinary and aggregate records. A selected name that
does not exist is simply absent; it does not add null. If selection or exclusion leaves
an ordinary record with no fields, that record emits nothing (in particular, neither a
blank line nor `[]`/`{}` is printed in legacy or JSON mode). Selecting a nested path
retains its containing root object (for example, selecting `user.name` retains the whole
`user` object).

`EXPRESSION as NAME` evaluates per record, adds/replaces `NAME`, and forwards the row.
All pre-existing fields remain. Names after `as` must be valid field names. A numeric
name, as in `1 as 1`, exits 1 and begins with exactly
`error: expecting a name for the field`; the source help is
`Give the value a name`, and the diagnostic ends with `Error: Failed to parse query`.

## Spec 9: Expressions and type rules

Expressions contain nonnegative integer, string, and Boolean literals, null, field and
array references, function calls, unary `!`, arithmetic `+ - * /`, comparisons
`== != <> < <= > >=`,
logical `and`/`&&` and `or`/`||`, and parentheses. Precedence is conventional:
function/access and unary, multiplication/division, addition/subtraction, comparisons,
AND, OR. Logical operators short-circuit and require Boolean operands. Comparisons use
the value ordering in Spec 2; string equality and ordering are case-sensitive.

The expression lexer does not accept a directly written signed or floating-point
numeric literal. Such values are fully supported when they come from parsed fields or
from calculations, so `abs(x)` on JSON `{"x":-2}` returns 2, `ceil(x)` on
`{"x":2.1}` returns 3, and `abs(0 - 2)` returns 2. In contrast, calculated-field
queries containing `abs(-2)`, `ceil(2.1)`, `floor(2.9)`, `round(2.5)`, `round(-2.5)`,
`toDegrees(3.141592653589793)`, or `atan2(0, -1)` exit 1 with a diagnostic beginning
`error: unhandled input`. `2 == 2 as result` is valid and true, but
`2 == 2.0 as result` exits 1 beginning `error: unrecognized syntax`.

Integer/integer operations normally return integers, including exact division; mixed or
nonintegral arithmetic returns floats. For `+` and `-`, a float operand makes the
result a float even when mathematically integral; for `*` and `/`, an exact integral
result normalizes to an integer. For example, JSON values `1.5` and `2.5` added into
`sum` produce `[sum=4.00]`, while `1.5 * 2` produces `3`.
Numeric-looking strings are coercible in arithmetic and numeric functions; commas may
be stripped for numeric coercion. Division by numeric zero follows IEEE behavior and
renders positive infinity as `inf`. Invalid combinations emit a per-record runtime
error and do not crash. Required diagnostic forms include:

```text
error: Expected numeric operands, found VALUE OP VALUE
error: Expected boolean, found VALUE
error: Expected number, found VALUE
```

Values substituted into the numeric-operands diagnostic use their display form without
adding quotes around strings. For example, evaluating `x * 10` when `x` is the string
`text` writes exactly `error: Expected numeric operands, found text * 10\n` (not
`'text' * 10`).

Date/duration arithmetic supports date minus date = duration, date plus/minus duration
= date, duration plus date = date, duration plus/minus duration = duration,
duration times integer (either order), and duration divided by integer. A date used as
a number converts to Unix epoch milliseconds (for example
`parseDate("2024-01-15T10:30:00Z") * 5` is `8526573000000`). Other unsupported type
combinations are errors. Duration tokens are also literals in general expressions, not
only in `timeslice`: for example, `parseDate("2014-01-05T00:00:00Z") - ts < 2d` is a
valid Boolean expression.

## Spec 10: `where`, `limit`, and pipeline behavior

`where BOOLEAN_EXPRESSION` forwards only rows whose expression is true. A bare Boolean
field and Boolean constants are allowed. `where true` forwards all; `where false`
forwards none. The result must actually be Boolean: numbers, strings, arrays, objects,
durations, and the result of a non-Boolean `if` are errors rather than truthy/falsy.
Missing fields are errors, including when passed to `isNull`; explicit JSON null can be
tested safely as described in Spec 11. Filtering works before or after aggregation. A
statically known non-Boolean condition is rejected before input is read; for example
`where 5` exits 1,
includes `Error: Expected boolean expression, found Int(5)` and suggests
`Perhaps you meant to compare a field to this value?`. A dynamically obtained
non-Boolean value instead produces the per-record runtime error from Spec 9 and the
overall command remains successful.

`limit N` accepts a nonzero integer. Positive N returns the first N records; negative
N returns the last `abs(N)` records, preserving their order. Bare `limit` defaults to
10. A positive limit can emit an accepted row immediately, but it continues reading
and the process remains alive until input EOF. For example, after one line is written
to the still-open stdin of `* | limit 1`, that line appears on stdout but the process
does not exit; after stdin is closed it exits 0 without further output. Zero or a
fractional value is rejected with a parse/type diagnostic. Except for sort, limit
applies at its pipeline position. A `limit` textually after `sort` is pushed in front
of that sort: the limit first selects from the incoming unsorted rows, then that subset
is sorted. For example, parsing `1,3,2` as numbers and applying `sort by n desc | limit
2` produces `3,1`; on `1,3,2,4`, the same pipeline with `limit -2` selects the final
two input rows and produces `4,2`.

Any number of stages may be chained. Except for the documented sort/limit pushdown,
these work as their literal left-to-right meanings imply:

```text
* | json | where status >= 400 | fields status, method | sort by status
* | json | count by status | where _count >= 2 | sort by status | limit 3
* | json | count by status | count
* | json | count by status | sum(_count)
```

## Spec 11: Built-in functions

Function names are case-sensitive and have these meanings:

- One-number functions: `abs`, `acos`, `asin`, `atan`, `cbrt`, `ceil`, `cos`, `cosh`,
  `exp`, `expm1`, `floor`, `log` (natural), `log10`, `log1p`, `round`, `sin`, `sinh`,
  `sqrt`, `tan`, `tanh`, `toDegrees`, `toRadians`. Angles use radians except for the
  explicit conversion functions. They require exactly one numeric/coercible argument;
  applying `round` to a parsed value of 2.5 produces 3 (halfway values round away from
  zero; direct floating-point expression literals are not accepted as noted in Spec 9).
- `atan2(y,x)` and `hypot(x,y)` require exactly two numeric arguments.
- `concat(arg,...)` concatenates the display form of any number of values with no
  separator. Thus `concat("hello", " ", 123, " ", true)` is `hello 123 true`.
- `contains(haystack,needle)` is a case-sensitive substring test and requires two
  strings. A missing field is the ordinary missing-key runtime error, not false.
- `length(x)` requires one argument and returns Unicode character count for a string,
  element count for an array, or member count for an object.
- `substring(s,start[,end])` uses zero-based Unicode character offsets and a half-open
  `[start,end)` range. With no end it continues to the end. Integer-valued floats and
  numeric strings are accepted as offsets. It requires two or three arguments. If end
  is before start, the exact runtime diagnostic is
  `error: The 'substring' function failed with the error: end offset (END) is less than the start offset (START)\n`,
  with the evaluated offsets substituted as unquoted integers. For example,
  `substring(s, 4, 2)` reports `end offset (2) is less than the start offset (4)`.
- `toLowerCase(x)` and `toUpperCase(x)` require one string.
- `parseHex(x)` trims whitespace, accepts upper/lowercase digits and an optional `0x`
  prefix, and returns an integer. Invalid text drops the row and writes exactly
  `error: The 'parseHex' function failed with the error: invalid hex string -- TEXT\n`.
  For example, `notahex` ends the message with `-- notahex` and `not-hex` with
  `-- not-hex`.
- `parseDate(x)` accepts at least RFC3339/ISO timestamps, `YYYY-MM-DD`,
  `Mon DD, YYYY` (for example `Jan 15, 2024`), and `DD/MM/YYYY`. Date-only and
  zone-less forms use UTC. On the input `not-a-date`, it drops the row, exits 0, and
  writes exactly
  `error: The 'parseDate' function failed with the error: UnrecognizedToken("not")\n`.
  Likewise, `parseDate("nonsense")` writes exactly
  `error: The 'parseDate' function failed with the error: UnrecognizedToken("nonsense")\n`.
- `now()` takes no arguments and returns the current UTC time, not a fixed value.
- `num(x)` converts a numeric value/string to a number.
- `isNull(x)` is true for explicit null and false for `0`, false, and `""`.
  `isEmpty(x)` is true for explicit null and the empty string only. `isBlank(x)`
  additionally accepts whitespace-only strings. Numbers and other nonstrings are
  false for `isEmpty`/`isBlank`. A missing field passed to any of these functions emits
  `error: No value for key "NAME"\n` and drops that row. `isNumeric(x)` is true exactly
  when the value/string can be converted to a number.
- `if(condition,when_true,when_false)` requires exactly three arguments, requires a
  Boolean condition, evaluates the selected branch, and may nest. Its wrong-arity
  source annotation states the count as `supplied 1 arguments` or
  `supplied 2 arguments`, as applicable.

Every fixed-arity function validates arity. Its runtime diagnostic is
`error: The 'NAME' function expects N arguments, found M\n` (the parser has a more
detailed exactly-three-arguments diagnostic for malformed `if`). Unknown functions
are parse errors and do not offer spelling suggestions: `lengt(x)` exits 1, writes
nothing to stdout, and writes exactly `Error: Unknown function lengt\n` to stderr.

## Spec 12: Aggregate operators

One aggregate stage contains one or more comma-separated aggregate expressions and an
optional shared grouping clause:

```text
AGG [as NAME], AGG [as NAME], ... [by EXPR, EXPR, ...]
```

Group on the evaluated tuple. Null is a legitimate grouping value and displays as
`None`/JSON `null`. Equal keys appearing nonconsecutively form one group. Output group
columns keep the expression text as their default heading; aggregate aliases replace
only the result heading. Every comma-separated item before `by` must be an aggregate;
a row operator such as `parse` there is rejected as `Not an aggregate operator`, with
close-name suggestions such as `averag` -> `average`. The supported aggregates are:

- `count` counts all rows; `count(condition)` counts rows for which the Boolean
  condition is true. Default result name `_count`.
- `sum(expr)` sums numeric/coercible non-null values and ignores null/non-numeric rows.
  Default `_sum`; an all-null group is 0.
- `average(expr)` and `avg(expr)` calculate numeric mean, ignoring null/non-numeric
  values. Default `_average`; an all-null group is null.
- `min(expr)`/`max(expr)` calculate numeric extrema, ignoring null/non-numeric values.
  Defaults `_min`/`_max`; all-null is null.
- `count_distinct(expr)` counts distinct typed values, including an explicitly present
  null, but skips rows where the expression is missing. Numeric `1` and normalized
  `1.0` are one value while string `"1"` is another. Consequently, values `1`, `1.0`,
  `"1"`, missing, missing produce 2; adding one explicit null makes the result 3.
  Default `_countDistinct`.
- `pN(expr)`, where integer `N` is 1 through 99, ignores null/non-numeric values and
  feeds the remaining values, in stream order, to a CKMS streaming quantile estimator
  configured with error `0.001`; query that estimator at `N / 100`. This is not the
  nearest-rank rule and is an approximate, order-sensitive computation. The column is
  named `pN`. As a self-contained discriminator, feeding the ordered integers 1 through
  2000 into this operator yields `1001` for `p50` and `1899` for `p95`.

Argument-taking aggregates require exactly one parenthesized expression (except
`count`, whose condition is optional). `p0` and percentiles over 99 are parse errors.
Several aggregates can coexist, e.g.
`count, sum(v), min(v), max(v), average(v), p50(v) by category`.

A bare `count_distinct` is rejected before processing. Its diagnostic begins
`error: Expecting an expression to count`, underlines `count_distinct` with the source
annotation `No field argument given`, includes
`help: example: count_distinct(field_to_count)`, and ends
`Error: Failed to parse query`.

An aggregate over no rows has no result rows, including ungrouped `count`, and renders
`No data`. Otherwise ungrouped aggregation emits one row. With no explicit `sort`,
groups are ordered descending by their aggregate-result tuple; ties use ascending group
keys. This explains `info:2` before `error:1`, groups with larger sums/averages first,
and equal-valued numbered groups in ascending order.

## Spec 13: Sorting and running totals

`sort by EXPR[, EXPR ...] [asc|ascending|desc|descending|dsc]` buffers the incoming rows
and compares expressions lexicographically in the listed order. Ascending is default;
`desc`, `descending`, and the compatibility spelling `dsc` reverse it. It works for
ordinary and aggregate records and accepts function or arithmetic expressions such as
`length(name)` and `_sum / _count`. Numeric sorting is numeric, not textual (`2`
precedes `10`); integers and floats mix. Boolean, date, duration, array, object, null,
and mixed-type sorting follows Spec 2. Null sorts first ascending. Arrays all compare
equal to one another, so their original order is retained even for descending sort.
A missing sort-key field is not a runtime error and writes nothing to stderr. Rows
missing that key precede rows having it in both ascending and descending order; rows
that all lack the key retain input order. A sort also switches output to the tabular
form: in default mode, sorted ordinary records use headings/separator/data rows rather
than `[key=value]` cells; in JSON mode they form one array rather than one object per
line.

`total(EXPR) [as NAME]` is a streaming, non-grouped running numeric total. Its default
field is `_total`; each input record is forwarded with the current cumulative value.
For values 1,2,3 the three values are 1,3,6. It works both before and after aggregate
stages but has no `by` form.

## Spec 14: Dates, durations, and timeslice

Date-times created by `parseDate` retain instants and compare chronologically. Legacy
display is `YYYY-MM-DD HH:MM:SS[.fraction] UTC`; JSON uses RFC3339, with a computed UTC
date rendered using `+00:00`. Durations serialize to JSON as ISO-8601 strings; one day
is `"PT86400S"`. Legacy duration display decomposes without spaces, omitting zero units,
using weeks, days, hours, minutes, seconds, milliseconds, and microseconds. Examples:

```text
1 day                                  => 1d
14 days + 3:45:30.123456               => 2w3h45m30s123ms456us
```

Timeslice syntax is:

```text
timeslice(DATE_EXPRESSION) DURATION [as FIELD]
```

It floors each instant to a duration boundary since the Unix epoch and forwards one
row per input row, adding `_timeslice` or the alias. Duration is one or more adjacent
`amount+unit` components with units `ns`, `us`, `ms`, `s`, `m`, `h`, `d`, `w`; e.g.
`100ms`, `5m`, `1h`, and `1h30m`. The duration must be positive. Examples:

```text
2023-01-01T00:05:30Z timeslice 5m   => 2023-01-01 00:05:00 UTC
2023-01-01T00:00:00.123Z, 100ms     => 2023-01-01 00:00:00.100 UTC
2023-01-01T01:45:00Z, 1h30m         => 2023-01-01 01:30:00 UTC
2023-01-01T00:00:00Z, 1w            => 2022-12-29 00:00:00 UTC
```

The weekly result follows epoch-aligned seven-day periods (Thursday boundaries), not
locale weeks. Raw strings/numbers/null/Booleans are not accepted: emit
`error: Expected date, found 'VALUE'.  Use parseDate() to convert a value to a date`.
Zero/negative durations emit
`error: Duration is not valid for timeslice: DurationExceedsLimit`. A parenthesized
timeslice with no duration, such as `timeslice(ts)`, exits 1, writes nothing to stdout,
and writes exactly `Error: Expected a duration for the timeslice (e.g. 1h)\n` to
stderr. A `by` clause is a parse error. A non-parenthesized form such as `timeslice 5m`
exits 1 and begins exactly
`error: expecting a parenthesized argument that supplies the date-time value for the log message`,
then ends with `Error: Failed to parse query`.

## Spec 15: Legacy/default rendering

The default output mode is `legacy`; `-o legacy` is identical. Ordinary parsed records
are one line each, keys in alphabetical order, each as `[key=value]`. Render values as:
null `None`; Booleans lowercase; integers decimal; floats rounded to exactly two digits
after the decimal unless the value normalized to an integer; arrays as
`[item, item, ...]`; objects as `{key:value, key:value}` recursively with sorted keys;
dates/durations per Spec 14. Strings are unquoted and embedded tabs/newlines remain
literal.

Ordinary-record alignment is streaming and stateful; it is not computed over the
complete finite result, and an increase never repads already-emitted rows. Maintain a
width state `W[K]`, initially 0, for every encountered key. Immediately before emitting
each record, for each field compute
`B = max(utf8_byte_length(K), utf8_byte_length(render(value)))`. If `B + 4 > W[K]`, set
`W[K] = B + 8`; otherwise retain the old width. Render `[K=value]` in a field whose
format width is `utf8_byte_length(K) + 3 + W[K]`. Concatenate the fields and trim
leading/trailing whitespace from the complete rendered row, so the final visible cell
has no trailing padding. Width numbers are derived from UTF-8 byte lengths even though
padding is applied by Unicode-character-aware string formatting; this distinction is
observable for non-ASCII values. Missing keys are omitted rather than printed as None.
Examples:

```text
[method=GET]           [size=1234]        [status=200]
[method=POST]          [size=456]         [status=201]

[a=1]
[a=2]        [b=x]
[a=3]        [b=y]        [c=z]
```

Tabular output (created by an aggregate or `sort`) is an aligned table, not bracketed
cells. Sorted ordinary records use their alphabetically ordered field names; aggregate
columns are grouping columns in query order followed by aggregate columns in query
order. Before emitting the table, calculate each column's final `W[K]` by starting at 0
and applying the same update rule above, in row order, to every displayed value:
`B = max(utf8_byte_length(K), utf8_byte_length(render(value)))`, then set
`W[K] = B + 8` only when `B + 4 > W[K]`. Pad the heading and each value to `W[K]`, join
the columns, and trim trailing spaces from header and data rows. The separator contains
one hyphen for every position in the untrimmed joined header, including the final
column's allocation. Thus a one-column `_max` table containing `-3.70` has 13 hyphens,
and a one-column `p90` table containing `156.80` has 14. For example:

```text
level        _count
---------------------------
info         2
error        1
```

Long names and 200-character values are never truncated. Unicode is emitted intact.

## Spec 16: JSON, logfmt, and custom rendering

`-o json`/`--output json` emits compact UTF-8 JSON with no spaces after punctuation.
Ordinary records are one object per line, with recursively preserved values and
alphabetically sorted record keys:

```text
{"active":true,"age":30,"balance":123.45,"name":"Alice"}
```

A tabular result (an aggregate or sorted stream) is instead one JSON array on one line.
Aggregate objects retain column order (group columns first, then aggregates), for
example:

```text
[{"level":"info","_count":2},{"level":"error","_count":1}]
```

Empty nonaggregate JSON output is empty; an empty aggregate is still the textual
`No data\n`. JSON preserves full finite float precision rather than the two-digit legacy
display, plus Booleans, null, arrays, objects, date RFC3339 strings, and ISO duration
strings.

`-o logfmt` emits one record per line, including aggregate rows, with alphabetically
sorted `key=value` pairs separated by one space. It deliberately does not quote or
escape strings containing spaces, quotes, tabs, or newlines. Empty string is `key=`;
null displays as `None`; compound/date/numeric display follows legacy conventions.
Example aggregate output is `_count=2 level=info`.

Custom mode is supplied either as `-o 'format=TEMPLATE'` or deprecated `-m TEMPLATE`.
It emits one line per ordinary or aggregate row. Replace `{field}` with the legacy
display value; a missing field becomes `None`. `{{` and `}}` produce literal braces.
Placeholders also support Rust-style alignment/width such as `{msg:<30}` (left-align in
a 30-character field); apply the same display conversion before padding. All other
text is literal. Example `format=[{src}] -> [{dst}] : {bytes} bytes` produces
`[10.0.0.1] -> [192.168.1.1] : 1024 bytes`. An empty modern output value,
`-o 'format='`, exits 1, writes nothing to stdout, and writes exactly
`Error: InvalidFormatString\n` to stderr. The deprecated option handles its empty value
differently: `-m ''` is a valid empty template, exits 0, writes no stderr, and emits
one otherwise empty newline for each output row. Other malformed formats are rejected.
Supplying both `-m` and `-o` is rejected.

CLI compatibility diagnostics are exact:

```text
Error: Invalid(Expected '}' before end of string)
Error: InvalidOutputMode { choice: "invalid", choices: "legacy, json, logfmt, format" }
Error: CantSupplyBoth
```

The first line is the result for a template with an unmatched opening brace, such as
`-o 'format={missing'`; it exits 1 and writes that line to stderr.

## Spec 17: Aliases

Aliases are named pipeline fragments usable wherever an operator appears. Four built-ins
exist even outside any project directory:

- `apache` parses common logs matching
  `* - * [*] "* * *" * *` as
  `ip,name,timestamp,method,url,protocol,status,contentlength`.
- `nginx` parses combined nginx logs into
  `addr,user,timestamp,method,url,protocol,status,bytes_sent,http_referer,http_user_agent,gzip_ratio`.
- `k8singressnginx` parses ingress-nginx logs into
  `remote_addr,remote_user,timestamp,method,url,protocol,status,body_bytes_sent,http_referer,http_user_agent,request_length,request_time,proxy_upstream_name,proxy_alternative_upstream_name,upstream_addr,upstream_response_length,upstream_response_time,upstream_status,req_id`.
  Square brackets surrounding the two proxy names are removed. Comma-separated upstream
  fields remain strings.
- `testmultioperator` expands to `json | count` (this compatibility alias is public
  despite its name).

The precise layouts for the latter two web formats are:

```text
nginx:
ADDR - USER [TIMESTAMP] "METHOD URL PROTOCOL" STATUS BYTES
  "REFERER" "USER_AGENT" "GZIP_RATIO"

k8singressnginx:
REMOTE_ADDR - REMOTE_USER [TIMESTAMP] "METHOD URL PROTOCOL" STATUS BODY_BYTES
  "REFERER" "USER_AGENT" REQUEST_LENGTH REQUEST_TIME [UPSTREAM_NAME]
  [ALTERNATIVE_UPSTREAM_NAME] UPSTREAM_ADDR UPSTREAM_RESPONSE_LENGTH
  UPSTREAM_RESPONSE_TIME UPSTREAM_STATUS REQUEST_ID
```

User alias files are TOML files with exactly the useful shape:

```toml
keyword = "keyvalue"
template = """
parse "*=*" as key, value
"""
```

The template is a complete pipeline fragment and may contain multiple `|` stages.
Without alias flags, search from the current directory upward for every directory named
`.agrind-aliases`, loading all TOML files found. `--alias-dir DIR` uses that directory
instead. User aliases override built-ins. `--no-alias` disables filesystem/user aliases
but the compiled-in aliases above remain usable. Using it together with `--alias-dir`
exits nonzero with exactly
`Error: CantDisableAndOverride\n`. A nonexistent explicit alias directory exits nonzero
and writes exactly `Error: No such file or directory (os error 2)\n`.

Unreadable files, broken symlinks, invalid TOML, and syntactically invalid templates do
not stop an unrelated valid query. An invalid TOML warning begins exactly
`warning: invalid alias: TOML parse error at line N, column M`; its rich diagnostic
names the alias file. A broken symlink warning begins exactly
`warning: invalid alias: No such file or directory (os error 2)`, followed by a source
location naming the symlink. An invalid template is reported as a query parser
diagnostic without a `warning: invalid alias:` prefix and without naming its alias
file. For example, an otherwise valid invocation that loads an unrelated alias whose
template is exactly `where` still exits 0 and processes its input, while stderr is
exactly:

```text
error: expecting an expression
  |
1 | where
  |      ^
  |
```

An unterminated double quote begins exactly
`error: unterminated double quoted string` and includes the help
`Insert a double quote (") to terminate this string`. An unrecognized alias name is
normally treated as an unknown operator and exits nonzero, including:

```text
error: Expected an operator
  = help: NAME is not a valid operator
Error: Failed to parse query
```

Operator parsing takes precedence when the disabled alias name resembles an operator.
In particular, if a filesystem alias named `mine` is disabled with `--no-alias`, the
query `* | mine` is parsed like an incomplete `min` aggregate rather than reported as
an unknown operator. It exits 1, writes nothing to stdout, and writes exactly:

```text
error: expecting a parenthesized argument that supplies the numeric value to find the minimum of
  |
1 | * | mine
  |        ^
  |
Error: Failed to parse query
```

## Spec 18: Errors, exit status, and stream behavior

Syntax/type-checking occurs before processing where possible. Query parse errors exit 1
and write diagnostics only to stderr. Most grammar errors end with
`Error: Failed to parse query\n`; semantic validations instead end with their own
capitalized `Error:` line as detailed below.
Diagnostics show the source query, a caret/underline at the bad span, and a concise help
line when applicable. Runtime errors are written as lowercase `error: ...\n`; malformed
individual data rows are dropped and processing continues, and these data/runtime errors
normally leave exit status 0.

The following invalid forms and messages are normative (the rich source-span lines may
be inserted between the first and final lines):

```text
where                         error: Expected an expression
where @                       error: expecting an expression
where a >                     error: expecting the right-hand-side of the comparison
where a &&                    error: expecting an operand for 'and' operator
where a ||                    error: expecting an operand for 'or' operator
where a +                     error: expecting an operand for binary operator
trailing |                    error: expecting an expression
unknown operator NAME         help: NAME is not a valid operator
json()                        error: json does not take any parenthesized arguments
logfmt()                      error: logfmt does not take any parenthesized arguments
sum                           error: expecting a parenthesized argument ... sum of
avg/average                   error: expecting a parenthesized argument ... average of
min                           error: expecting a parenthesized argument ... minimum of
max                           error: expecting a parenthesized argument ... maximum of
p95                           error: expecting a parenthesized argument ... percentile of
count_distinct()              error: Expecting a single expression to count
count_distinct(a,b)           error: Expecting a single expression to count
timeslice 5m                  error: expecting a parenthesized argument that supplies the date-time value for the log message
```

For the complete query `* | json | where`, stderr is exactly:

```text
error: Expected an expression
  |
1 | * | json | where
  |            ^^^^^ No condition provided for this 'where'
  |
  = help: Insert an expression whose result determines whether a record should be passed downstream
  = help: example: where duration > 100
Error: Expected an expression
```

For the complete query `* | json |`, stderr is exactly:

```text
error: expecting an expression
  |
1 | * | json |
  |          ^
  |
Error: Failed to parse query
```

For the complete query `* | where @`, stderr is exactly:

```text
error: expecting an expression
  |
1 | * | where @
  |           ^
  |
Error: Failed to parse query
```

The exact limit semantic errors begin and end as follows (with the annotated query and
the two positive/negative-integer help lines between them):

```text
error: Limit must be a non-zero integer, found 0
Error: Limit must be a non-zero integer, found 0

error: Limit must be a non-zero integer, found 5.5
Error: Limit must be a non-zero integer, found 5.5
```

An unknown function is exactly `Error: Unknown function NAME\n`, without a trailing
“Failed to parse query”. A plain-parse wildcard/field count mismatch is exactly
`Error: Wrong number of patterns for parse. Pattern has N but M were extracted\n`.

`count_distinct` diagnostics additionally help with
`example: count_distinct(field_to_count)`; the misspelling `countdistinct` is rejected
as an operator but suggests `count_distinct`. An unterminated function call emits
`error: unterminated function call`, repeats `unterminated function call` at the source
caret, and includes `help: Insert a right parenthesis to terminate this call`.
Argument-taking aggregates may emit their missing-argument diagnostic first. `if` with
other than three arguments reports:

```text
error: the 'if' operator expects exactly 3 arguments, the condition,
       value-if-true, and value-if-false
```

Invalid regex syntax is reported at parse time; an unnamed regex capture reports that
only named captures are supported; regex followed by `as` explains that regex mode does
not support it. Unterminated double/single quoted strings and escaped identifiers are
rejected and suggest inserting the missing terminator. Do not suggest an unrelated
valid operator for an arbitrary unknown operator.

Ordinary records stream one per input row. Aggregate rendering depends on stdout. With
non-TTY stdout, an aggregate prints its table once at end of input. With TTY stdout,
it periodically prints the current aggregate table while input is still being
processed, including repeated unchanged snapshots, and leaves the final table visible
at EOF. Before redrawing, it erases the previous table from bottom to top by emitting
the ANSI sequence `\x1b[2K\x1b[1A` once for each previous table line, then prints the
new header, separator, and rows. This behavior applies to grouped and multi-group
aggregates and to `min` and `max`; a sufficiently long-running TTY aggregate therefore
contains that exact escape sequence and more than one rendered table.
