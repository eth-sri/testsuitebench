## Spec 1

The required artifact is a directly runnable command-line program named exactly `executable`. It implements a bidirectional JSON-to-statements utility whose displayed program name is `gron`.

With no mode-changing option, the program reads one JSON document and emits flattened assignment statements. It uses the first input operand and silently ignores any additional operands. With no operand, or with the operand `-`, input comes from standard input. Any other non-URL operand is a file path. Options may precede the operand.

The following option spellings are required:

- `-u` and `--ungron`: reverse statements into JSON.
- `-v` and `--values`: extract scalar values from assignment statements.
- `-s` and `--stream`: treat each physical input line as a separate JSON document.
- `-j` and `--json`: use the JSON path/value statement representation.
- `-m`: force monochrome output.
- `-c`: force colored output.
- `--no-sort`: disable the normal statement sort.
- `-k`: disable TLS certificate verification for URL input.
- `-x URL` and `--proxy URL`: use an HTTP proxy.
- `--noproxy LIST`: bypass a configured proxy for matching hosts.
- `--version` and `--help` as described below.

Successful transformations return status 0. Every emitted text record, including the last, ends in `\n`.

## Spec 2

In ordinary forward mode, decode any valid JSON value, including a top-level object, array, string, number, Boolean, or null. Emit one statement for the root value and one for every nested value, including containers. The root identifier is always `json`. Assignment syntax is one ASCII space on each side of `=`, followed by a value and a semicolon:

```text
json = {};
json.a = 1;
```

Objects are represented by `{}`, arrays by `[]`, strings by JSON string literals, Booleans by lowercase `true`/`false`, null by `null`, and numbers by their JSON spelling. A container assignment must be present even when the container has children; empty containers therefore still produce one statement.

For example, monochrome transformation of `{"x":{"y":[1,2]},"empty":{}}` is exactly:

```text
json = {};
json.empty = {};
json.x = {};
json.x.y = [];
json.x.y[0] = 1;
json.x.y[1] = 2;
```

Top-level primitives produce a direct root assignment, such as `json = "just a string";`, `json = 42;`, `json = true;`, or `json = null;`.

## Spec 3

Object keys use JavaScript-style path notation. A key may use `.key` only when it is a valid non-reserved JavaScript identifier. Identifiers may begin with `_` or a Unicode identifier letter, may continue with identifier characters, digits, or underscores, and may be arbitrarily long. Thus `_under_scores`, `ಠ_ಠ`, and a 1000-character alphabetic key use dot notation.

All other keys use brackets containing a JSON string literal. This includes the empty key, keys beginning with a digit, numeric-looking keys, keys containing spaces, dots, hyphens, brackets, quotes, backslashes, tabs, emoji when not valid identifier characters, and reserved words including `class`, `function`, `var`, `return`, and `if`. Examples are:

```text
json["123"] = "numeric object key";
json[""] = "empty";
json["has.dot"] = 1;
json["key\"with\"quotes"] = 2;
json["key\\with\\backslashes"] = 3;
json["class"] = 4;
```

Array path components are nonnegative decimal integers in unquoted brackets: `json.users[0].name`. Object keys that happen to contain decimal digits remain strings and must never be confused with array indices.

## Spec 4

JSON strings and bracketed keys are encoded without ASCII-escaping ordinary Unicode: Japanese, Arabic, Cyrillic, CJK, and emoji remain UTF-8. Use standard JSON escapes for quote, backslash, backspace, form feed, newline, carriage return, and tab. Control characters are never placed literally into a one-line assignment. U+2028 and U+2029 are emitted as lowercase `\u2028` and `\u2029` escapes. Forward slash need not be escaped.

Numbers must not be routed through a binary floating-point conversion that changes their text. Preserve valid input number lexemes through forward flattening, including precision and exponent spelling. Required examples include:

```text
json.large = 999999999999.999999;
json.precise = 3.141592653589793;
json.small = 0.0000000001;
json.scientific = 1.23e10;
json.negative_exp = -5.6e-7;
```

The same fidelity applies when statement values are reconstructed into JSON, including large integers, `-0`, and scientific notation.

## Spec 5

By default, all forward statements are deterministically sorted by their rendered left-hand paths. Use lexicographic ordering of path text, except that decimal digits inside actual array-index brackets compare as integers. Digits embedded in identifier names are ordinary text. A path precedes its descendants. This produces all of the following consequences:

- Root precedes every nested path.
- `json.a`, `json.m`, `json.z` are in that order.
- Identifier keys `key0,key1,key10,...,key19,key2,key20,...` use ordinary lexical order.
- Array indices appear `0,1,...,9,10,...,99`, never lexical `0,1,10,...,2` order.
- Dot-notation paths sort before bracket-notation paths at the same prefix because `.` sorts before `[`. For example, `json.two` precedes `json["three-b"]`.
- Container paths precede their descendants.

With `--no-sort`, emit the same complete set of statements and keep every parent container before its children, but object-member order is unspecified and need not be alphabetical. Root remains first, and stream records remain grouped in increasing record-index order.

## Spec 6

In forward `-j`/`--json` mode, replace each textual assignment with a compact JSON array `[path,value]`, one array per output line and with no insignificant spaces. `path` is an array: object components are strings and array components are JSON integers. The root path is empty. Containers remain explicit values.

For input `{"a":1,"nested":{"items":[true,null]}}`, sorted JSON-mode output is exactly:

```text
[[],{}]
[["a"],1]
[["nested"],{}]
[["nested","items"],[]]
[["nested","items",0],true]
[["nested","items",1],null]
```

Consequently `{}` alone produces `[[],{}]\n`, and `[]` alone produces `[[],[]]\n`. Strings and keys preserve Unicode, empty strings, escapes, and exact types. This output must be accepted by reverse mode with `-u -j` and round-trip to the original JSON structure.

## Spec 7

Stream mode (`-s` or `--stream`) treats each physical line as an independent complete JSON document and models the whole input as a top-level array. Emit `json = [];` (or `[[],[]]` in JSON mode) first. For zero-based line/record index N, prefix every statement for that record with array component N. A scalar record is assigned directly to `json[N]`; an object or array record first emits `json[N] = {};` or `json[N] = [];` and then its descendants.

For input `{"a":1}\n{"b":2}\n`, monochrome stream output is exactly:

```text
json = [];
json[0] = {};
json[0].a = 1;
json[1] = {};
json[1].b = 2;
```

With `-s -j`, the same data produces:

```text
[[],[]]
[[0],{}]
[[0,"a"],1]
[[1],{}]
[[1,"b"],2]
```

Stream lines may independently contain objects, arrays, strings, numbers, Booleans, or null. A final line terminator does not create an additional empty record. Truly empty input succeeds and emits only the top-level empty-array statement.

## Spec 8

An empty, spaces-only, or tabs-only physical line inside a nonempty stream is an invalid record. Stop immediately at that line, retain on standard output the root and all completed earlier records, emit no statement for that line or any later line, write `failed to form statements: EOF\n` to standard error, and return 3.

Likewise, stop at the first malformed nonblank JSON line, retaining only earlier output. Prefix the parse diagnostic with `failed to form statements: ` and return 3. For example, a truncated line `{"bad json}` diagnoses `unexpected EOF`; a line beginning `invalid json here` diagnoses `invalid character 'i' looking for beginning of value`.

Trailing JSON whitespace on an otherwise valid line is allowed. Stream mode must accept at least 1000 records, 500,000-byte individual lines, mixed/nested containers, and deep values without truncating the line or losing its record index.

## Spec 9

Values mode (`-v` or `--values`) consumes assignment statements rather than JSON input. Process recognized statements in input order. For each scalar right-hand value, write just the value followed by `\n`: JSON strings are decoded and printed without surrounding quotes; numbers retain their exact spelling; Booleans print `true` or `false`; null prints `null`. Empty strings therefore produce an empty output line, and decoded `\n` inside a string produces a real newline in the output.

Do not output anything for `{}` or `[]` container assignments. Do not output paths, equals signs, semicolons, indices, or string quotes. For example:

```text
Input:                         Output:
json = {};                    
json.a = "hello";             hello
json.b = 42;                  42
json.c = true;                true
json.d = null;                null
```

Array-indexed and deeply nested assignments behave identically. An empty physical input record is fatal in values mode: input consisting of a single newline returns 5 and writes `failed to parse '' as gron statement\n` to standard error. By contrast, nonempty records that cannot be parsed as value-producing assignments are silently ignored. Thus either `noise\n` or `json.a = [;\n` alone returns 0 with empty standard output and standard error.

## Spec 10

Reverse mode (`-u` or `--ungron`) parses ordinary statements of the following form:

```text
json<path> = <JSON-value>;
```

`<path>` is any sequence of valid dot identifiers, quoted JSON-string bracket keys, and nonnegative integer array indices. Values may be every JSON scalar plus the exact empty-container markers `{}` and `[]`. Decode all JSON escape sequences in keys and strings. Statements may be arbitrarily long (at least 100 KB).

Reverse mode also parses JSON path/value records of the form `[path,value]` when `-j` is supplied. A line beginning with `[` is recognized as this syntax for validation even without `-j`. Such a record must be an array of exactly two elements; its first element must be an array; and path elements must be strings or valid nonnegative integer indices.

Zero-byte or whitespace-only input is an error, with the diagnostic specified in Spec 14. By contrast, unrelated nonempty noise lines that do not parse as attempted `json` or JSON-record statements are ignored; this permits grep context separator lines such as `--` and arbitrary noise between valid assignments. A malformed line that begins as a recognizable statement is fatal as described in Spec 14.

## Spec 11

Reconstruct the JSON tree from all parsed paths even when explicit ancestor/container statements have been filtered out. Infer an object for a following string key and an array for a following integer index. Thus the sole statement

```text
json.users[0].email = "alice@example.com";
```

reconstructs:

```json
{
  "users": [
    {
      "email": "alice@example.com"
    }
  ]
}
```

Sparse array assignment extends the array through the requested index and fills every unassigned gap with null. `json = []; json[5] = "value";` reconstructs `[null,null,null,null,null,"value"]` (formatted as specified later). The same inference and padding work inside nested objects and arrays.

Reverse mode must preserve empty-string keys, Unicode keys and values, all JSON scalar types, nested arrays, arrays of objects, objects containing arrays, and structures at least 50 levels deep.

## Spec 12

Merge reverse statements in input order. Repeated scalar assignment to the same exact path is last-value-wins. A later container may replace an earlier scalar at that path and then receive children; for example:

```text
json = {};
json.test = 1;
json.test = {};
json.test.sub = 2;
```

produces `{"test":{"sub":2}}` structurally.

Repeated declarations of the same container type merge rather than clear prior children. Redeclaring an object as `{}` retains its existing members, and redeclaring an array as `[]` retains and can extend existing elements. This permits assignments before and after repeated container declarations to accumulate.

Attempting to merge an established object with an array/non-object container is fatal with `failed to merge statements: cannot merge object with non-object`. Attempting to merge an established array with an object/non-array container is fatal with `failed to merge statements: cannot merge array with non-array`. Both return 5.

## Spec 13

Successful ungron output on a non-colorized stream is conventional pretty JSON: two-space indentation, object keys in deterministic lexicographic order, no ASCII escaping of ordinary Unicode, JSON escapes where required, and one trailing newline. Empty containers may remain on one line. For example:

```text
{
  "bool_false": false,
  "empty_array": [],
  "name": "test",
  "nested": {
    "value": 123
  }
}
```

Arrays use the analogous two-space multi-line layout. Number lexemes such as `9007199254740991`, `0.123456789012345`, `1.5e-5`, `1.23e10`, and `-0` must remain intact in textual output.

Invoking the same executable through a filesystem symlink whose basename is `ungron` automatically enables reverse mode without requiring `-u`. Other behavior is unchanged.

## Spec 14

Use these error statuses and diagnostics:

- Failure to open a local input file returns 1 and writes the operating-system error to standard error; a missing file message must contain `no such file or directory`.
- Failure to turn ordinary or stream JSON into statements returns 3 and writes `failed to form statements: <JSON error>\n`.
- Failure to fetch a URL at the transport layer returns 4 and writes the transport error to standard error.
- Except for the negative JSON-record path-component panic described below, a fatal statement parse, validation, or merge error in ungron mode returns 5 and writes its diagnostic to standard error. Values-mode handling of unparseable records is specified in Spec 9.

Exact forward parse cases are:

```text
input {invalid json} -> failed to form statements: invalid character 'i' looking for beginning of object key string
empty input          -> failed to form statements: EOF
input {"a":1,        -> failed to form statements: unexpected EOF
```

Each diagnostic above ends in `\n`.

Ordinary-statement reverse validation must reject missing semicolons (`statement has no value`), invalid JSON values (for `json.likes = [;`, include ``ungron failed for `json.likes = [;`: invalid value `[` ``), invalid identifiers such as `json.123invalid`, unquoted bracket content such as `json[abc]`, negative indices, overflowing indices, and invalid JSON escapes in quoted keys. These return 5 and respectively include `invalid statement`, `invalid integer key`, or `invalid quoted key` as appropriate. In particular, `json[abc] = "test";` writes exactly ``ungron failed for `json[`: invalid statement\n``. For the tested ordinary negative-index input, the exact diagnostic is also ``ungron failed for `json[`: invalid statement\n``.

For malformed JSON-record statements, these exact results are required:

```text
[["a"], 1, "extra"]       -> invalid JSON layout
["string_not_array", 123] -> invalid JSON layout
```

Each result above returns 5, writes the shown text followed by `\n` to standard error, and writes nothing to standard output.

The JSON-record input `[["a",-1],1]\n` with `-m -u -j` is a special failure case: it returns 2, writes nothing to standard output, and writes a Go panic stack trace to standard error beginning `panic: runtime error: index out of range [-1]\n`.

Zero-byte or whitespace-only reverse input returns 5, writes nothing to standard output, and writes exactly `no statements were parsed\n` to standard error.

`-s` and `-u` are accepted together, regardless of their order or whether their long spellings are used. Reverse mode takes effect: for example, `json = {};\n` supplied to `-s -u` returns 0 and emits `{}` followed by `\n`.

## Spec 15

Color is disabled when standard output is not a terminal unless `-c` is present. It is enabled automatically on a terminal unless `-m` is present. `-m` always produces bytes with no ANSI CSI sequences when color was not forced. If both `-c` and `-m` occur, `-c` takes precedence regardless of option order.

In the escaped examples below, every `\x1b` denotes the single ESC byte, not four printable characters. Forced-color output for `{"test":1}` is exactly:

```text
\x1b[34;1mjson\x1b[0;22m = \x1b[35m{}\x1b[0m;
\x1b[34;1mjson\x1b[0;22m.\x1b[34;1mtest\x1b[0;22m = \x1b[31m1\x1b[0m;
```

Automatic terminal output for `{"a":1,"b":"test"}` follows the same palette and is exactly:

```text
\x1b[34;1mjson\x1b[0;22m = \x1b[35m{}\x1b[0m;
\x1b[34;1mjson\x1b[0;22m.\x1b[34;1ma\x1b[0;22m = \x1b[31m1\x1b[0m;
\x1b[34;1mjson\x1b[0;22m.\x1b[34;1mb\x1b[0;22m = \x1b[33m"test"\x1b[0m;
```

Colorized reverse JSON is compact rather than indented. Terminal ungron output for statements `json = {};`, `json.a = 1;`, and `json.b = "hello";` is exactly this single line plus newline:

```text
\x1b[35m{\x1b[0m\x1b[34;1m"\x1b[0;22m\x1b[34;1ma\x1b[0;22m\x1b[34;1m"\x1b[0;22m\x1b[1m:\x1b[22m\x1b[31m1\x1b[0m\x1b[1m,\x1b[22m\x1b[34;1m"\x1b[0;22m\x1b[34;1mb\x1b[0;22m\x1b[34;1m"\x1b[0;22m\x1b[1m:\x1b[22m\x1b[32m"\x1b[0m\x1b[33mhello\x1b[0m\x1b[32m"\x1b[0m\x1b[35m}\x1b[0m
```

## Spec 16

An input operand is fetched over the network only if it begins with an HTTP or HTTPS scheme. Lowercase `http://` and `https://` are supported, and HTTP scheme recognition is case-insensitive (including `HTTP://`). Other apparent schemes, such as `htp://`, are treated as local file names. HTTP input is transformed exactly like file/stdin input and can be large or nested.

Follow HTTP redirects. Preserve query parameters, strip fragments before sending the request, support `user:pass@host` URL userinfo, and allow long paths/queries. Non-ASCII query characters are not percent-encoded: for a URL whose query ends in `café☕`, the request target contains the raw UTF-8 byte sequences `c3 a9` and `e2 98 95` and contains no percent escapes for those characters.

Do not reject a response solely because its HTTP status is 404 or 500. Consume its body and try to parse it as JSON. Thus a successfully received non-JSON body, including a 404/500 text body, fails as JSON formation with status 3, not as a fetch failure. For example, text beginning with `T` produces a diagnostic containing `invalid character 'T'`.

TLS certificates are verified by default. A certificate that supplies only a legacy Common Name and lacks a valid modern subject alternative name is a fetch failure (4); its diagnostic contains both `tls: failed to verify certificate` and `x509: certificate relies on legacy Common Name field`. `-k` disables certificate verification and allows such HTTPS input.

Use an overall HTTP client timeout of approximately 20 seconds. If response headers have not arrived by then, return 4 before 23 seconds and include both `context deadline exceeded` and `Client.Timeout exceeded while awaiting headers` in standard error. DNS failures and refused connections also return 4; diagnostics must include the requested URL/host and underlying phrases such as `lookup ...: no such host`, `dial tcp HOST:PORT`, and `connection refused`.

## Spec 17

`--proxy URL` and `-x URL` explicitly configure a proxy for HTTP requests. For an HTTP target routed through it, send the absolute target URL in the proxy request so a conventional forwarding proxy can retrieve it. An explicit proxy option overrides the proxy URL from proxy environment variables, but inherited `no_proxy` bypass settings still apply to it. Thus with `--proxy` set to a reachable proxy and `no_proxy=target.invalid`, a request for `http://target.invalid/value` bypasses the explicit proxy; if that host cannot be resolved, the command returns fetch status 4 and the proxy receives no request.

Without an explicit proxy option, honor lowercase `http_proxy` for HTTP targets. Honor lowercase `no_proxy` as a comma-separated bypass list. The explicit `--noproxy LIST` similarly bypasses an explicitly configured proxy. Entries may be exact `host:port` strings or leading-dot suffix patterns; for example `.0.1:8080` matches `127.0.0.1:8080`. A matching entry anywhere in a comma-separated list bypasses the proxy.

If an explicit proxy is unusable, return fetch status 4. For proxy text `not-a-valid-url`, the diagnostic must contain `proxyconnect tcp: dial tcp :0: connect: connection refused`.

## Spec 18

The implementation must be stateless across process invocations and deterministic whenever sorting is enabled. It must support, within ordinary test timeouts, at least all of the following without truncation, stack failure, or hard-coded limits: 1000-element arrays of objects (about 3002 statements), 1000 stream records, 10,000-character JSON-mode values, 100,000-character ungron statement values, 500,000-character stream lines, 1000-character keys, nesting depth 50, and combinations of 50 items each nested 10 levels.

`--version` writes exactly `gron version dev\n` to standard output and exits 0 without reading input.

`--help` exits 0, writes usage/help text to standard error, and does not wait for input. The help must include the phrases `Transform JSON`, `gron [OPTIONS]`, and `--ungron`.
