# Clarified specification for `executable`

## Spec 1

The delivered artifact is a directly executable file named exactly `executable`. It is a terminal JSON viewer and command-line data processor compatible with the behavior described below. It must accept UTF-8 arguments and input, write ordinary results to standard output, diagnostics to standard error unless a rule below says otherwise, and terminate promptly in non-interactive mode. A successful transformation exits 0. Input, query, and file errors exit 1. Failure to acquire `/dev/tty` when interactive mode is required exits 2 with empty standard output; standard error begins `panic: could not open a new TTY: open /dev/tty: no such device or address\n`. Calls to the query function `exit(n)` use the requested integer exit status.

Only `executable` is supplied by the implementation. Any test-harness helper command, including commands compiled by the harness for exercising library-like behavior, is provided externally and is not a behavior of `executable`.

## Spec 2

The command-line form is:

```text
executable [flags] [file] [query ...]
```

There are no git-style subcommands. Words such as `add`, `list`, or `show` are filenames or query text, never subcommands. Recognized flags may occur before or after other arguments and repeated Boolean flags are harmless. `-r` means `--raw`, `-s` means `--slurp`, and short flags may be combined as `-rs` or `-sr`; those two forms are equivalent. `-h` and `--help` are equivalent, as are `-v`, `-V`, and `--version`.

Help and version both take precedence over normal processing and invalid positional arguments, but neither has an absolute precedence over the other: the first help/version flag in command-line order determines the output. Thus `--help --version` prints help, `--version --help` prints only the version, and `bad-file --version --help` also prints only the version. `--` is not a POSIX end-of-options delimiter: by itself it is query text and causes an `Unexpected token` query error, and later recognized flags are still parsed. Boolean flags do not accept `=value`; forms such as `--raw=1`, `--yaml=1`, `--strict=1`, `--no-inline=1`, `--themes=1`, and `-r=1` are treated as expressions and diagnose `Invalid left-hand side in assignment`.

## Spec 3

`-h` or `--help` exits 0, writes nothing to standard error, and writes exactly the following bytes to standard output, including the initial blank line and final blank line:

```text

  fx 39.2.0
    Terminal JSON viewer

  Usage
    fx data.json
    fx data.json .field
    curl ... | fx

  Flags
    -h, --help            print help
    -v, --version         print version
    --themes              print themes
    --comp <shell>        print completion script
    -r, --raw             treat input as a raw string
    -s, --slurp           read all inputs into an array
    --yaml                parse input as YAML
    --toml                parse input as TOML
    --strict              strict mode
    --no-inline           disable inlining in output
    --game-of-life        play the game of life

  More info
    https://fx.wtf

  Author
    Anton Medvedev <anton@medv.io>

```

## Spec 4

Every version spelling prints exactly `39.2.0\n` on standard output, nothing on standard error, and exits 0. The output is deterministic.

`--themes` exits 0 and prints fourteen theme-preview blocks to standard output. The output includes blocks beginning `export FX_THEME="0"` and `export FX_THEME="1"` and shows JSON-looking examples containing the labels `"string"`, `"number"`, `"boolean"`, `"null"`, and a collapsed/preview label. It also writes exactly fourteen newline bytes (`\n` repeated fourteen times) to standard error, one for each preview block.

`--export-themes` exits 0 and emits valid JSON: a nonempty object with at least ten theme entries, including key `"0"` or `"1"`. Every entry's value is a nonempty array of color-code strings.

## Spec 5

`--comp SHELL` and `--comp=SHELL` print shell setup and exit 0 for `bash`, `zsh`, `fish`, and `powershell`, with no standard error. When repeated, the last `--comp` value wins. Bash output starts with:

```text
complete -o filenames -C fx fx
```

Fish output contains a completion declaration equivalent to:

```text
complete --command fx --arguments '(COMP_FISH=(commandline -cp) fx)'
```

Zsh output is multiline, begins with or contains `#compdef fx`, defines a function named `_fx` (the text `_fx()` is present), contains a `local` declaration, and registers `compdef _fx fx`. Powershell output is a nonempty completion script. An unknown or empty shell value writes exactly `unknown shell type\n` to standard output and exits 0. Supplying `--comp` without an argument exits 2 and diagnoses `flag needs an argument: -comp` (the substrings `needs an argument` and `-comp` must be present).

## Spec 6

The input source depends on terminal state. With a terminal on standard input, the first ordinary argument naming a file is opened as the data source and remaining ordinary arguments are queries; a lone file opens the interactive viewer. When data is piped through standard input, that data is the source and ordinary arguments are queries, even when an argument happens to name an existing file. Consequently, a lone pathname in such a non-terminal invocation can produce a query `SyntaxError` containing the pathname. File inputs use JSON unless `--yaml` or `--toml` is supplied. A missing or unreadable file, a directory used as a file, or invalid/binary input produces a clear nonzero error; a missing-file diagnostic contains its pathname and `no such file or directory` and exits 1.

If piped input contains at least one query, processing is non-interactive. With piped input but no query, normal, raw, YAML, TOML, strict, and no-inline modes attempt to open the viewer through `/dev/tty`; `--slurp` is the exception and prints the slurped array directly. Zero-byte stdin with a query produces no output and exits 0. A single newline supplied to the identity query is a parse error: it exits 1 with empty standard output and begins its standard-error diagnostic with `Unexpected character '\x00' on line 2.`

## Spec 7

Default JSON input is a stream of one or more top-level values. Whitespace and blank lines may separate values, and each value is independently transformed and printed in order. Standard JSON strings, arrays, objects, booleans, null, integers, decimals, negative numbers, and `e`/`E` exponent notation are accepted. Strings decode `\"`, `\\`, `\b`, `\f`, `\n`, `\r`, `\t`, and non-surrogate four-hex-digit `\u` escapes such as `\u2603`. The otherwise valid solidus escape in `"a\/b"` and UTF-16 surrogate-pair escape in `"\ud83d\ude00"` are unsupported: in either default or strict mode, each exercised input exits 2 with no standard output and standard error beginning `panic: invalid syntax\n`. Raw UTF-8 keys and values, empty keys, numeric-looking quoted keys, large inputs, deep nesting (at least 100 levels), hundreds of keys/elements, and long strings must work. Duplicate object keys are accepted with the last value winning while ordinary object insertion order is retained.

Numbers such as `.123`, `1.`, `1e`, and malformed keywords such as `truee` are rejected. Missing commas, missing colons, unterminated strings/arrays/objects, single-quoted JSON strings, and unquoted object keys are rejected. Number values use JavaScript-compatible binary floating-point for computation, but an integer read from input must be printed without gratuitous decimal notation. The integers 9007199254740991, 9007199254740992, and -9007199254740992 are preserved exactly, while still larger integers must remain recognizable in integer or scientific notation rather than crashing.

## Spec 8

Non-strict JSON deliberately accepts trailing commas in arrays and objects, C-style `// line` and `/* block */` comments, and the tokens `NaN`, `-NaN`, `Infinity`, and `-Infinity`. It also accepts `undefined` as a top-level value. These special input values preserve their spellings when printed: in particular, `-NaN` writes `-NaN\n`, and a top-level input `undefined` writes `undefined\n` to standard output, with empty standard error and exit 0. Invalid string escapes need not be recovered in relaxed mode; the specifically exercised `"\g"` case terminates with exit 2 and text containing `panic:`.

Except for the unsupported valid escapes identified in Spec 7, `--strict` accepts RFC-style JSON but rejects trailing commas, comments, invalid escapes, incomplete/invalid Unicode escapes, `undefined`, `NaN`, and infinities with exit 1. A strict trailing comma diagnostic includes `Trailing comma is not allowed in strict mode`; an invalid escape diagnostic includes `Invalid escape` or equivalent `invalid ... escape` wording.

## Spec 9

`--yaml` parses a YAML document into the same data model used for JSON. It supports mappings, nested mappings, sequences, sequences of mappings, flow sequences/maps, single- and double-quoted scalars, plain strings, integers/floats, booleans, nulls, comments, explicit scalar tags, literal (`|`) and folded (`>`) multiline strings, anchors, aliases, and merge keys. Mapping key order and nesting are preserved. Timestamp/date-like YAML scalars may be represented as strings. Multiple `---` documents form a stream; without slurp they are processed in sequence, and with slurp they become array elements. Queries apply to the converted values.

Invalid YAML exits nonzero with a useful location-bearing error. Unlike ordinary parse diagnostics, this YAML parser error is written to standard output and leaves standard error empty. Specifically, input `a: [1, 2\n` with `--yaml .` exits 1 and writes:

```text
[1:4] sequence end token ']' not found
>  1 | a: [1, 2
          ^
```

## Spec 10

`--toml` parses TOML into the common data model. It supports root key/value pairs; basic and literal strings, including multiline strings and escapes; integers in decimal, hexadecimal, octal, and binary forms; floats and scientific notation; booleans; arrays; quoted keys; dotted keys; tables and nested tables; inline tables including nested inline tables; arrays of tables; comments; empty arrays/tables; and date, time, local datetime, and offset datetime values. Date/time values are emitted as strings. Queries apply normally to the converted object. Invalid TOML exits nonzero rather than producing transformed data.

`--yaml` and `--toml` conflict, and either format flag conflicts with raw mode, regardless of argument order or whether raw is written `-r`. The exact one-line diagnostics are respectively:

```text
Error: can't use both --yaml and --toml flags together
Error: can't use --yaml/--toml and --raw flags together
```

Conflict processing exits 1.

## Spec 11

`-r`/`--raw` treats each input line as a string rather than parsing JSON; newline terminators are not part of the strings. A query runs once per line, so raw input `Hello World\nThis is line 2\nLine 3 here\n` with query `.[1]` prints `e`, `h`, and `i` on separate lines. Empty lines are handled without crashing. If raw input is a single unterminated line, it is one string. Raw strings support the same string properties and methods as query-created strings.

`-s`/`--slurp` collects the complete input stream into one array before applying queries. Thus three JSON objects become a three-element array, one JSON value becomes a one-element array, and zero input values becomes `[]`. Raw plus slurp produces an array of line strings, so text such as `123` and `true` remains string data. YAML plus slurp collects YAML documents. Without slurp, an NDJSON query prints one result per record. Blank separator lines do not create JSON values.

## Spec 12

One or more positional query arguments form a left-to-right transformation pipeline. Every input record starts as the current value; query 1 transforms it, then query 2 sees query 1's result, and so on. For example `.products`, `?.price < 100`, `@.name` means select the product array, retain cheap products, then extract names. A query that is itself a function is automatically applied to the current value. Curried helpers are also auto-applied: bare `sort`, `keys`, `reverse`, `flatten`, `filter(predicate)`, `map(mapper)`, `chunk(n)`, and `del(key)` operate on the current value. An explicit arrow query such as `x => x.name` is invoked on the current value. Helper callbacks must use explicit arrow syntax, such as `map(v => v.id)`.

Within every query, `x` and `this` refer to the current value. The identity spellings `.`, `x`, and `this` return it unchanged. A leading-dot method query such as `.map(x => x * 2)` means `this.map(...)`. Multiple input records retain streaming behavior through the full query pipeline.

A leading dot is not implicit callback syntax inside a helper argument. `map(.id)`, `filter(.age >= 18)`, and the standalone-dot form `map(.)` are invalid query syntax: each exits 1 with no standard output and ends its diagnostic with `Unexpected token . `.

## Spec 13

As a top-level query rewrite, path shorthand supports `.name`, `.a.b.c`, `.[0]`, `.items[1].name`, `.matrix[1][0]`, and JavaScript bracket keys such as `.["a.b"]`, `.["a[b]"]`, `.["123"]`, `.["field with spaces"]`, and escaped newline/tab keys. Unicode identifier fields such as `.ключ` also work in that top-level form. Leading-dot shorthand is not a general JavaScript primary expression and cannot be nested in an array literal: `[.[""], .["123"], .ключ, .["a.b"]]` and `[.["line\nkey"], .["tab\tkey"]]` each exit 1 with empty standard output and a diagnostic ending `Unexpected token . `. Ordinary expression notation using the current-value identifier is composable: `[x[""], x["123"], x.ключ, x["a.b"]]` works, as do `x.name`, `this.name`, and `x["field-with-dash"]`. Arrays and strings expose `.length`; objects expose their members and methods.

An absent object member, an arbitrary absent property on a string/number/boolean primitive, or an out-of-range array element produces the JavaScript value `undefined`; it is written as `undefined\n` on standard error, nothing on standard output, and the process still exits 0. Very large indices behave the same. A fractional bracket value is not truncated to an integer array index: `.[1.5]` on `["a","b","c"]` likewise exits 0, writes nothing to standard output, and writes `undefined\n` to standard error. Accessing `.field` directly through null exits 1 and ends its diagnostic with the legacy wording `TypeError: Cannot read property 'field' of undefined`. Unclosed/unopened brackets and doubled dots are syntax errors. The unopened-bracket query `.field]` diagnoses `Unexpected token ]`; doubled-dot diagnostics contain `Unexpected token ILLEGAL`.

## Spec 14

Three concise collection shorthands are required:

- `@.field` maps the current array to each element's field. `@.baz` is equivalent to `map(v => v.baz)`.
- `?.field > value` filters the current array using the expression after `?`; equality and normal expression operators are allowed. The shorthand rewrites only the initial `?.field`. Further field references in a composite predicate must use the current callback value as `x.field`: `?.age >= 18 && x.active === true` works, whereas `?.age >= 18 && .active === true` exits 1 with empty standard output and ends its diagnostic with `Unexpected token . `.
- Empty brackets iterate/flatten one level: `.[]` yields the elements, `.[].name` maps an array of objects to names, `.array[]` expands that property, and paths such as `.[].items[]` or `.[][]` repeatedly flatten nested arrays in encounter order.

These operators return arrays, including `[]` for empty input. The shell-pipeline text `.[] | .a` is not valid query syntax and must produce a caret-marked `Unexpected token` error.

## Spec 15

The query language is a JavaScript-like expression language with normal precedence and JavaScript coercion for the exercised constructs. It supports numeric `+ - * / % **`, unary `+ -`, comparisons `< <= > >=`, loose and strict equality `== != === !==`, short-circuit `&&`, `||`, `!`, nullish coalescing `??`, optional chaining `?.`, ternary `?:`, string concatenation with `+`, bitwise `& | ^ ~ << >> >>>`, the comma and `void` operators, `in`, `instanceof`, `typeof`, property deletion, prefix/postfix increment, and assignment/compound assignment in block bodies. Division by zero produces infinities and `0/0` or invalid numeric conversions produce NaN rather than crashing.

`typeof` returns `number`, `string`, `boolean`, `object`, `function`, or `undefined` with JavaScript conventions, including `typeof null === "object"`. Truthiness follows JavaScript for null, undefined, false, zero, NaN, and empty strings. `Array.isArray` distinguishes arrays from objects. Parentheses determine grouping. Template literals with `${expression}` interpolate values.

## Spec 16

Expressions may construct arrays and objects, including unquoted identifier keys, computed keys (`{[x.key]: x.val}`), concise property names, nested literals, and array/object spread (`...`). `Object.assign({}, ...array)` and `{...object, added: value}` merge in encounter order. Array and object destructuring is supported in arrow parameters and local declarations. Arrow functions accept one or multiple parameters, expression bodies, object-literal bodies in parentheses, and block bodies with `let`, statements, and `return`. Recursion through a locally defined function is supported. Query text may contain multiple statements in a function body.

Runtime calls to undefined identifiers/functions, calling a non-function, or invoking an array/string/number method on the wrong receiver exit 1 and produce an error naming the relevant `ReferenceError` or `TypeError`. `throw new Error("message")` explicitly raises an error, writes an error diagnostic, and exits 1. Syntax errors also exit 1.

## Spec 17

Arrays provide JavaScript-compatible `map`, `filter`, `reduce`, `find`, `findIndex`, `some`, `every`, `forEach`, `includes`, `indexOf`, `lastIndexOf`, `at`, `slice`, `concat`, `join`, `reverse`, `sort`, `flat`, `flatMap`, `fill`, `push`, `pop`, `shift`, `unshift`, `splice`, and `length`. Callback arguments include value and zero-based index. `find` returns the first matching value or undefined, and `findIndex` returns its zero-based index. `some`/`every` return booleans. `reduce` honors its initial accumulator. Negative `at` and slice indices count from the end. Default numeric/string sorting and comparator sorting work; mutating operations exhibit their usual JavaScript return value, while block queries can mutate then return the array.

Examples that define required results include `[1,2,3].map(n=>n*2)` → `[2,4,6]`, `[1,2,3,4].filter(n=>n%2===0)` → `[2,4]`, `[1,2,3,4].reduce((a,b)=>a+b,0)` → `10`, `[3,1,4].sort((a,b)=>b-a)` → `[4,3,1]`, and `"a,b,c".split(",")` → `["a","b","c"]`.

## Spec 18

Strings provide `.length`, character indexing, `charAt`, `charCodeAt`, `concat`, `indexOf`, `lastIndexOf`, `substring`, `substr`, `slice`, `toLowerCase`, `toUpperCase`, `trim`, `trimStart`, `trimEnd`, `repeat`, `padStart`, `padEnd`, `replace`, `replaceAll`, `split`, `startsWith`, `endsWith`, `includes`, `match`, and `search`, with the exercised JavaScript argument and negative-index conventions. For example, `"hello".substring(1,4)`, `.substr(1,3)`, and `.slice(1,-1)` all yield `ell`; `"42".padStart(5,"0")` yields `00042`; and `"hello".charCodeAt(0)` yields 104 while `"A".charCodeAt(0)` yields 65.

Regex literals such as `/[a-z]+/` are accepted by string matching/search. Invalid regex syntax is a query syntax error. Selected or computed string results are printed raw, without surrounding JSON quotes, after decoding escape sequences; internal newlines, tabs, NULs, and Unicode are written as their actual characters.

## Spec 19

Objects provide `hasOwnProperty`; global `Object.keys`, `Object.values`, `Object.entries`, `Object.fromEntries`, and `Object.assign` work and preserve useful insertion order. `Object.freeze` and `Object.seal` accept objects without corrupting them. `JSON.parse` parses a JSON string into a value. `JSON.stringify(value)` returns compact JSON text, and its optional replacer/indent arguments are accepted. Because a returned string is printed raw, `JSON.stringify({a:1})` appears as `{"a":1}` rather than as a doubly quoted string.

Numbers provide `toString`, `toFixed`, `toPrecision`, and `toExponential`. Global `parseInt`, `parseFloat`, `isNaN`, and `isFinite` use JavaScript-like conversions. `Math` supplies at least `abs`, `ceil`, `floor`, `round`, `sqrt`, `pow`, `max`, `min`, `random`, `sin`, `cos`, `PI`, and `E`. Numeric special values retain the output rules in Spec 8. The expression language also supports construction with `new`; specifically, `new Date().getFullYear()` returns the current four-digit year, so its value is greater than 2020.

## Spec 20

The fx collection helpers have the following contracts. Except for the explicitly described scalar/object and array cases below, an inappropriate receiver type exits 1:

- `len(v)` returns array length, JavaScript UTF-16 code-unit string length, or number of object keys. Thus `len("😀é")` is 3. `len(42)` exits 1 and its diagnostic ends `Error: Cannot get length of number`.
- `uniq(array)` removes later duplicate primitive values while preserving first occurrence.
- `sort(array)` and `reverse(array)` return ordered/reversed arrays.
- `keys(objectOrArray)` and `values(objectOrArray)` return enumerable keys/values in order. For arrays, keys are decimal index strings: `keys([10,20])` returns `["0","1"]`, `values([10,20])` returns `[10,20]`, and both helpers return `[]` for `[]`.
- `flatten(array)` flattens exactly one array level.
- `filter(fn)` and `map(fn)` return unary transformers which are automatically applied to the current value. For an array, they filter or map its elements. For any other current value, `map(fn)` applies `fn` once to that value, while `filter(fn)` returns the value unchanged when the predicate is truthy and suppresses it when the predicate is false. Extra arguments are ignored rather than supplying an explicit receiver; for example, with current value `5`, `map(v=>v*2, [1,2])` returns `10`. Consequently raw-mode strings work with `map(x => x.toUpperCase())`, and explicit-looking `map(v=>v, x)` and `filter(v=>true, x)` both return a current `{}` unchanged.
- `sortBy(fn)` stably sorts ascending by a callback result. A property-name string is not a valid selector once sorting requires a comparison: `sortBy('n')` on `[{"n":2},{"n":1}]` exits 1 with `TypeError: Value is not an object: n`. Degenerate arrays do not invoke the selector, however: `sortBy('n')` on `[]` exits 0 and prints `[]\n`, and on `[{"n":2}]` exits 0 and returns that element unchanged.
- `groupBy(fnOrProperty)` returns an object mapping the string form of each group key to an array of matching elements.
- `chunk(n)` partitions an array into consecutive arrays of size `n`, retaining a short final chunk. Applied to `{}`, `chunk(2)` returns `[]` rather than an error.
- `zip(a,b,...)` returns rows of corresponding values, stopping at the shortest input.
- `del(keyOrIndex)` returns a unary function that copies/removes an object key or array element; it may also be explicitly applied as `del(k)(value)`.

## Spec 21

Additional helpers behave as follows:

- `sortKeys(object)` recursively returns objects with lexicographically sorted keys.
- `walk(fn)(value)` or `walk(fn, value)` recursively visits nested arrays/objects and transforms leaf values (and may pass the key as a second callback argument), preserving structure.
- `apply(fn, value)` calls `fn(value)`; `apply(nonFunction)` simply returns that argument unchanged.
- `list(array)` emits each array item as a separate normal result. Non-arrays are errors.
- The special value `skip` suppresses a final streamed result. It is used for conditional filtering such as `x.value > 2 ? x : skip`. It is retained when stored inside an array: the ordinary formatter renders `x.map(v=>v%2 ? v : skip)` on `[1,2,3,4]` with the embedded values as `"skip"`. JSON stringification treats those same embedded values like undefined array elements, however; applying a following `JSON.stringify(x)` produces exactly `[1,null,3,null]\n`.
- `console.log` writes its arguments to standard output separated by spaces. Scalars use readable text, undefined prints `undefined`, and objects use JSON formatting. If the enclosing query also returns a value, that value is emitted after the log output.

## Spec 22

`toBase64(string)` encodes the UTF-8 bytes with standard padded Base64 and returns the encoded string; `fromBase64(string)` reverses it. Empty strings, whitespace, NUL characters, non-ASCII text, and emoji round-trip exactly. For example, `toBase64("hello")` yields `aGVsbG8=` and decoding `SGVsbG8gV29ybGQ=` yields `Hello World`. Invalid Base64 exits 1 and uses the `GoError:` class prefix: `invalid@base64!` ends its diagnostic with `GoError: illegal base64 data at input byte 7`, while `abc!` ends it with `GoError: illegal base64 data at input byte 3`.

`YAML.parse(string)` performs the conversion in Spec 9. `YAML.stringify(value)` and its alias `__yaml_stringify__(value)` use two spaces for nested mappings but indentless block sequences beneath a mapping key. Both stringify spellings return the following text for `{a:1,nested:{b:true},items:[1,2],nothing:null,empty:{}}` (including the final newline):

```text
a: 1
nested:
  b: true
items:
- 1
- 2
nothing: null
empty: {}
```

Despite its name, `__yaml_parse__(string)` does not return the parsed object produced by `YAML.parse`. It returns a newline-terminated JSON-text string representing the parsed YAML value. For example, `__yaml_parse__("b: 2\n")` returns the string `{"b": 2}\n`; its `typeof` is `string`, accessing `.b` produces undefined, and `JSON.stringify(__yaml_parse__("b: 2\n"))` prints `"{\"b\": 2}\n"\n`. Consequently `[YAML.parse("a: 1\n").a,__yaml_parse__("b: 2\n").b]` followed by `JSON.stringify(x)` prints `[1,null]\n`. Mappings use `key: value`, arrays use `- `, null is spelled `null`, and an empty object is `{}`. Returned YAML strings are printed raw; because ordinary scalar output appends its own newline, the stringify invocation above writes two newline bytes after `empty: {}`.

## Spec 23

`exit(n)` immediately ends processing with status `n` and no result output. `save(value)` is only valid when the original source was an actual file. It serializes the supplied value back to that file as formatted data, returns the supplied value for normal result printing, and allows a subsequent read to observe the modification. In particular, on an actual file initially containing `{"a":1}`, the query `v=>{v.a=2;v.b=[3,4];return save(v)}` exits 0, leaves standard error empty, and prints:

```json
{
  "a": 2,
  "b": [ 3, 4 ]
}
```

The saved file instead contains the fully expanded formatted bytes:

```json
{
  "a": 2,
  "b": [
    3,
    4
  ]
}
```

A subsequent file query `.b[1]` exits 0 and prints `4\n`. `save(undefined)` exits 1 and diagnoses `Cannot save undefined`. When input came from stdin, saving exits 1 and explains `specify a file as the first argument to be able to save: fx file.json`. A symbolic-link input file must never be overwritten; saving through it exits nonzero, contains `cannot save to a symbolic link` and the link filename in the diagnostic, and leaves the target unchanged.

## Spec 24

Successful scalar output is one value plus `\n`: strings are unquoted raw text; numbers use a concise decimal/scientific representation; booleans are `true`/`false`; null is `null`; and the special tokens retain their spellings. Objects and arrays are valid UTF-8 JSON followed by `\n`. JSON strings inside containers are double-quoted and escape quotes, backslashes, backspace, form feed, newline, carriage return, tab, and control bytes; printable Unicode is emitted directly.

An undefined value produced by query evaluation is exceptional only in destination: a missing member, the query `undefined`, or `void 5` writes `undefined\n` to standard error and nothing to standard output but exits 0. In contrast, the accepted top-level input token `undefined`, passed through the identity query `.` or `x`, is written as `undefined\n` to standard output with empty standard error. A stream prints each defined result in order, each terminated by a newline. `skip` prints nothing at all.

## Spec 25

Container output uses two spaces per indentation level, a space after each colon, commas after every non-final member, and opening/closing delimiters on their own lines unless a nested-value inlining rule applies. Empty objects and arrays print `{}` and `[]`. Every nonempty top-level array is multiline with one element per line, including a short primitive array: `[1,2,3]` prints exactly:

```json
[
  1,
  2,
  3
]
```

Ordinary nested short primitive arrays can be inline: identity output for `[[1,2],[3,4]]` contains `[ 1, 2 ]` and `[ 3, 4 ]` as its two nested lines. Arrays produced as the rows of `zip`, however, are expanded recursively; `zip(...x)` on `[[1,2,3],["a","b","c"]]` prints each two-element row with its own opening line, one value per line, and closing line. An array of small, short-keyed primitive-only objects prints one element per line with each element inline, for example:

```json
[
  { "x": 1, "y": 2 },
  { "x": 3, "y": 4 }
]
```

Long strings that would make an array line exceed roughly 80 columns, nested object keys longer than about ten characters, objects with four or more string fields or five or more primitive fields, and arrays containing complex nested mixtures are expanded. A long string does not independently force its containing object to expand while the resulting line remains short enough: a top-level array containing the one-key object `{"a":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}` (55 `x` characters) prints exactly:

```json
[
  { "a": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" }
]
```

Nested object values are normally expanded rather than inlined. `--no-inline` disables every nonempty array/object inline optimization recursively, while preserving the same parsed value and indentation.

## Spec 26

Parse diagnostics identify the kind and location of the error and are written to standard error in ordinary CLI mode, with no standard output. They include a source excerpt and a dot/caret location line; for each exact input below, the excerpt is the complete source line. After the caret line they write two newline bytes, leaving a final blank line. Required examples include:

```text
Unexpected character 'j' on line 1.

  {"invalid": json json}
  ............^
```

for `{"invalid": json json}`, and:

```text
Expected object key to be a string, got 'i' on line 1.

  {invalid}
  .^
```

for `{invalid}`. A strict `[1,2,3,]` error is:

```text
Trailing comma is not allowed in strict mode on line 1.

  [1,2,3,]
  ......^
```

For `{"invalid": json}`, the corresponding source and caret lines are exactly `  {"invalid": json}` and `  ............^`. For strict input `{"name": "test", "age": 30,}`, the diagnostic uses that complete source line and `  ..........................^`, rather than a cropped tail.

Other required leading messages are `Unexpected character '\x00' in object on line 1.` for `{"a":1`, `Unexpected end of input in string on line 1.` for `{"bad":"unterminated`, and `Unexpected character '"' in object on line 1.` for `{"a":1 "b":2}`.

Query diagnostics begin with a newline byte, reproduce the query on an indented line, underline the relevant span with carets, leave a blank line, then print the exception. Calling `nonexistent()` therefore produces empty standard output and standard error exactly `\n  nonexistent()\n  ^^^^^^^^^^^^^\n\nReferenceError: nonexistent is not defined\n`. Malformed expressions contain `Unexpected token`, and all exit 1 with no ordinary result.

## Spec 27

Before evaluating queries, load JavaScript configuration snippets from these existing regular files: `.fxrc.js` in the current working directory, `$HOME/.fxrc.js`, and `$XDG_CONFIG_HOME/fx/.fxrc.js` (with the XDG location based on the environment). Definitions from multiple files coexist. A declaration such as `function double(x) { return x * 2; }` becomes callable in queries, so `double(5)` prints 10. Empty files are harmless. No configuration file is required for default operation.

Recognize the environment variables `FX_THEME`, `FX_COLLAPSED`, `FX_LINE_NUMBERS`, `FX_SHOW_SIZE`, `FX_NO_MOUSE`, and `FX_INDENT`. They must never break non-interactive transformations. `FX_SHOW_SIZE` recognizes at least `true`, `yes`, `on`, `1`, and false; `FX_INDENT` accepts a decimal width or a literal indentation string. At least numbered themes `0`, `1`, and `2` and the fire-emoji theme are valid. An invalid value such as `FX_THEME=invalid_theme` exits 1 and writes a diagnostic containing `unknown theme`.

## Spec 28

Interactive mode renders the parsed document as an initially expanded JSON tree. Objects, arrays, empty objects, empty arrays, strings, numbers, booleans, null, Unicode, and nested structures remain visibly recognizable. The bottom status area contains the source filename and a decimal percentage. The viewer works whether data was opened by file or piped while `/dev/tty` is available. `q` leaves the viewer cleanly. Unknown keys do nothing and must not crash it.

The cursor is a logical tree-line selection reflected by a JSON path in the bottom area. From the root, one downward move selects the first member and shows a path such as `.title`. Pressing Enter on that selected scalar opens or focuses a view in which its value remains visible.

## Spec 29

Interactive navigation supports Down/`j` for the next visible tree line and Up/`k` for the previous one, never moving beyond the ends. `g` jumps to the top and `G` to the bottom. Space and `f` page down, `b` pages up, and Ctrl+D/Ctrl+U move down/up by roughly half a page. Navigation works for object and array lines, after collapsing, on an empty object, on data shorter than one page, and under rapid repeated keys. `J` and `K` select the next and previous sibling. `[` goes back in selection history and `]` goes forward; all these actions preserve a valid, visible document.

Pressing `:` opens a bottom command prompt. Escape cancels that prompt and restores the tree.

## Spec 30

On an object or array node, Left/`h` collapses it to compact content visibly marked by `…` or `...`, and Right/`l`/Enter expands it. Repeating collapse on a collapsed node or expand on an expanded node is harmless. `H` recursively collapses the selected subtree and `L` recursively expands it. `E` collapses the entire document, `e` expands the entire document, and digit keys such as `1` and `2` limit visible expansion to that many levels. The cursor remains on a valid visible node after any operation, including rapid alternating collapse and expansion. `FX_COLLAPSED`, `FX_LINE_NUMBERS`, and `FX_SHOW_SIZE` initialize the corresponding collapsed, numbered, and size-display modes without preventing the content from being shown.

## Spec 31

`/` opens a bottom search prompt. Escape cancels it and returns to the document. Submitting an empty search with Enter is harmless, and submitting text that has no matches leaves the application alive and the JSON view available.

## Spec 32

`?` opens an in-application help view containing recognizable help, key, or navigation text. Pressing `q` closes that view and restores the JSON document. The action keys `z` (wrapping), `y` (yank/copy), and `d` (delete action) must be accepted without crashing or corrupting the rendered document. It is sufficient for this contract that after each of these exercised single keystrokes the viewer remains responsive and still shows JSON content.
