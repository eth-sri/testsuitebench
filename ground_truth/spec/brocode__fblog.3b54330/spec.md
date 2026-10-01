# Clarified behavioral specification for `executable`

## Spec 1

The deliverable is one runnable program named exactly `executable`. It is a single-command, non-interactive JSON-log viewer; it has no subcommands. Its synopsis is `executable [OPTIONS] [INPUT]`. `INPUT` is optional and defaults to `-`. A missing input or an explicit `-` means read standard input until EOF. Any other positional value is opened as a file and processed as a byte stream. Options may appear before or after the positional input. At most one positional input is accepted. Normal processing, including empty input, exits 0.

Input is processed incrementally and must comfortably handle at least 10,000 records, a single JSON line containing a 1 MiB message, objects with at least 500 fields, arrays with at least 10,000 elements, field names of at least 1,000 characters, and object nesting of at least 100 levels. There must be no arbitrary truncation of messages, prefixes, field names, substitution values, or option expressions.

## Spec 2

The supported public options and aliases are:

- `-a, --additional-value VALUE`, repeatable.
- `--config-file FILE`, single-use.
- `-m, --message-key KEY`, repeatable.
- `--print-lua`, single-use Boolean.
- `-t, --time-key KEY`, repeatable.
- `-l, --level-key KEY`, repeatable.
- `--map-level FROM=TO`, repeatable.
- `-d, --dump-all`, single-use Boolean.
- `-x, --excluded-value VALUE`, repeatable.
- `-p, --with-prefix`, single-use Boolean.
- `-f, --filter EXPR`, single-use.
- `--no-implicit-filter-return-statement`, single-use Boolean.
- `--main-line-format TEMPLATE`, single-use.
- `--additional-value-format TEMPLATE`, single-use.
- `-s, --substitute`, single-use Boolean.
- `-c, --context-key KEY`, single-use.
- `-F, --placeholder-format FORMAT`, single-use.
- `-h, --help` and `-V, --version`.
- A hidden `--generate-completions SHELL` option.

Both `--option value` and `--option=value` forms are accepted for long value-taking options. `-a`, `-m`, `-t`, `-l`, `--map-level`, and `-x` preserve occurrence order. `-a` and `-x` conflict in either order. `-d` may coexist with either. When `-d` and `-a` coexist, dump-all wins and fields are not duplicated. A `--` token ends option parsing and makes the following token the positional input.

## Spec 3

`--version` and `-V` write exactly `fblog 4.17.0\n` to stdout, nothing to stderr, and exit 0.

Help writes the following exact UTF-8 text to stdout, nothing to stderr, and exits 0. The completion option is deliberately hidden from help.

```text
json log viewer

Usage: executable [OPTIONS] [INPUT]

Arguments:
  [INPUT]  Sets the input file to use, otherwise assumes stdin [default: -]

Options:
  -a, --additional-value <additional-value>
          adds additional values
      --config-file <config-file>
          configuration file to load
  -m, --message-key <message-key>
          Adds an additional key to detect the message in the log entry. The first matching key will be assigned to `fblog_message`.
      --print-lua
          Prints lua init expressions. Used for fblog debugging.
  -t, --time-key <time-key>
          Adds an additional key to detect the time in the log entry. The first matching key will be assigned to `fblog_timestamp`.
  -l, --level-key <level-key>
          Adds an additional key to detect the level in the log entry. The first matching key will be assigned to `fblog_level`.
      --map-level <from=to>
          Rewrite the log level from one value to another.
  -d, --dump-all
          dumps all values
  -x, --excluded-value <excluded-value>
          Excludes values (--dump-all is enabled implicitly)
  -p, --with-prefix
          consider all text before opening curly brace as prefix
  -f, --filter <filter>
          lua expression to filter log entries. `message ~= nil and string.find(message, "text.*") ~= nil`
      --no-implicit-filter-return-statement
          if you pass a filter expression 'return' is automatically prepended. Pass this switch to disable the implicit return.
      --main-line-format <main-line-format>
          Formats the main fblog output. All log values can be used. fblog provides sanitized variables starting with `fblog_`.
      --additional-value-format <additional-value-format>
          Formats the additional value fblog output.
  -s, --substitute
          Enable substitution of placeholders in the log messages with their corresponding values from the context.
  -c, --context-key <context-key>
          Use this key as the source of substitutions for the message. Value can either be an array ({1}) or an object ({key}).
  -F, --placeholder-format <placeholder-format>
          The format that should be used for substituting values in the message, where the key is the literal word `key`. Example: [[key]] or ${key}.
  -h, --help
          Print help
  -V, --version
          Print version
```

`-h` also exits 0 and prints the documented title, usage, arguments, and options. Help shows no “Commands”, “SUBCOMMANDS”, or subcommand guidance.

## Spec 4

Command-line parse failures write nothing to stdout, write a clap-style diagnostic to stderr, and exit 2. The diagnostic starts with `error:`, contains a `Usage: executable ...` line as applicable, and ends with `For more information, try '--help'.`. Unknown flags contain `unexpected argument` and the bad token. A missing option operand contains `a value is required`. A second occurrence of a single-use option contains `cannot be used multiple times`. More than one positional input reports the later one as an unexpected argument. The `-a`/`-x` conflict reports both arguments and `cannot be used with`.

When a value-taking option is invoked through one of the short aliases below without an operand, its diagnostic identifies the option by its canonical long spelling and long value placeholder, not by the short spelling:

- `-a` reports `--additional-value <additional-value>`.
- `-m` reports `--message-key <message-key>`.
- `-t` reports `--time-key <time-key>`.
- `-c` reports `--context-key <context-key>`.
- `-x` reports `--excluded-value <excluded-value>`.
- `-l` reports `--level-key <level-key>`.
- `-F` reports `--placeholder-format <placeholder-format>`.

For example, invoking `-a` with no operand produces `error: a value is required for '--additional-value <additional-value>' but none was supplied` as the first stderr line. Invoking bare `--generate-completions` produces the analogous missing-value line followed immediately by two leading spaces and `[possible values: bash, elvish, fish, powershell, zsh]`; it writes nothing to stdout and exits 2.

Each `--map-level` operand is split into a source and destination at `=`. An operand without `=` is rejected at parse time with exit 2. For example, `--map-level NOEQUALHERE` produces exactly:

```text
error: invalid value 'NOEQUALHERE' for '--map-level <from=to>': missing '='

For more information, try '--help'.
```

A bare word such as `help`, `version`, or `list` is an input filename, not a subcommand. If an input file cannot be opened, terminate nonzero (the compatible panic status is 101) and include `Can't open file: PATH` on stderr.

## Spec 5

Configuration is TOML. Unless `--config-file` is supplied, look for `fblog.toml` directly inside the platform user configuration directory; on Linux, use `$XDG_CONFIG_HOME/fblog.toml` when `XDG_CONFIG_HOME` is set, otherwise `$HOME/.config/fblog.toml`. A missing automatically located file is not an error. `--config-file` selects that path instead of the automatic location.

The complete defaults are:

```toml
message_keys = ["short_message", "msg", "message"]
time_keys = ["timestamp", "time", "@timestamp"]
dump_all_exclude = []
always_print_fields = []
level_keys = ["level", "severity", "log.level", "loglevel"]
main_line_format = "{{bold(fixed_size 19 fblog_timestamp)}} {{level_style (uppercase (fixed_size 5 fblog_level))}}:{{#if fblog_prefix}} {{bold(cyan fblog_prefix)}}{{/if}} {{fblog_message}}"
additional_value_format = "{{bold (color_rgb 150 150 150 (min_size 25 key))}}: {{value}}"

[level_map]
```

All fields are optional; omitted fields inherit these defaults, while a supplied array replaces its default array. Supported fields have exactly the types shown above, plus `level_map`, a string-to-string TOML table. `dump_all_exclude` applies whenever dump-all is active. `always_print_fields` is an ordered list of fields printed even without `-a` or `-d`.

CLI key options are tried before the configured key list, in CLI occurrence order. Thus they override a present configured/default key but still fall back to configured keys if the CLI key is absent. CLI templates replace configured templates. CLI mappings merge into the configured map, override equal source keys, and use last-occurrence-wins among CLI mappings.

Malformed TOML, duplicate keys, or wrong types are fatal, use a nonzero/panic status (101), and put a diagnostic containing `Could not parse config file`, the case-sensitive phrase `TOML parse error`, and the underlying TOML reason on stderr. A duplicate-key parse failure includes the lowercase phrase `duplicate key`. Wrong array types mention `invalid type` and `expected a sequence`. An explicit missing/unusable config also includes `Could not load config file`; an explicitly selected malformed config reports the parse failure and ultimately `Could not load config file`.

## Spec 6

Read input as physical lines, accepting LF and CRLF. Process each line independently; do not accumulate multi-line JSON. A final line without a newline is still processed and every emitted main or error line is newline-terminated. Zero bytes of input produce no output. Nonempty whitespace-only lines are invalid lines.

After any prefix handling, accept only a complete JSON object on that physical line. A JSON array, scalar, incomplete object, or malformed JSON is not a log record. Emit it unchanged as:

```text
\x1b[1;38;2;255;135;22m??? >\x1b[0m ORIGINAL_LINE\n
```

Then continue with later lines. Filters do not suppress these passthrough error lines. JSON escapes are decoded normally for successfully parsed values, so embedded newlines, tabs, carriage returns, quotes, backslashes, controls, and all Unicode are preserved in rendered content.

Invalid UTF-8 encountered while reading a line is also nonfatal. Emit:

```text
\x1b[1;31m??? >\x1b[0m Could not read line: stream did not contain valid UTF-8\n
```

and continue when possible. ANSI is emitted even when stdout is captured and even when the `NO_COLOR` environment variable exists.

## Spec 7

Prefix mode is off unless `-p`/`--with-prefix` is present. With it enabled, locate the first `{` in each line. Trim leading and trailing whitespace from everything before it and expose that as `fblog_prefix`; attempt to parse the suffix beginning at that first brace as JSON. Empty/whitespace prefixes become an empty prefix. Prefix text may contain arbitrary punctuation or Unicode and is never truncated.

If there is no `{`, or if the suffix from the first `{` is invalid JSON, treat the entire original line as invalid under Spec 6. Do not search later braces after the first parse fails. Prefix mode does not create a JSON field and the prefix is never part of additional/dump-all fields. Without prefix mode, any text before JSON makes the entire line invalid.

## Spec 8

For display-field selection and key detection, recursively flatten each JSON object. At each object level, visit keys in lexicographically ascending order, independent of their source JSON order. Within each array, visit elements in increasing numeric/source order rather than sorting the rendered paths lexicographically:

- Nested object keys join with the literal separator ` > `; for example `data > user > name`.
- Array indices append directly in brackets. The array held by an object property is zero-based, for example `tags[0]` or `items[0] > id`. If an array element is itself an array, indices within that directly nested array, and within any further directly nested arrays, are one-based. Thus `[[1], [2, 3]]` flattens to `matrix[0][1]`, `matrix[1][1]`, and `matrix[1][2]`; a deeper observed path is `status > d[1][1][1]`.
- Recurse through objects and arrays without a practical shallow-depth limit.
- A scalar object property renders as its natural unquoted text: strings verbatim, integers/finite floats in JSON-style decimal form, and Booleans as lowercase `true`/`false`.
- A null object property is omitted from the flattened map.
- A scalar reached as an array element is rendered as its compact JSON representation, so array strings retain double quotes and array null renders `null`.
- Empty objects and arrays contribute no flattened leaf.
- Keys containing dots remain literal dots; a top-level key `log.level` is distinct from nested `log > level`.

The resulting flattened order follows that recursive traversal: object-key portions are lexicographic, while siblings from one array remain in numeric index order. For example, an array of 13 scalar elements emits `x[0]`, `x[1]`, ..., `x[9]`, `x[10]`, `x[11]`, `x[12]`, not raw string order with `x[10]` after `x[0]`. Integer precision through signed 64-bit values and 2^53−1 is preserved. A positive integer too large for the JSON implementation’s integer range may render through a floating representation; `9999999999999999999999` must render as `1e+22`.

## Spec 9

Derive four synthetic template values for every valid record: `fblog_message`, `fblog_timestamp`, `fblog_level`, and `fblog_prefix`.

For message, time, and level, scan the respective priority list and take the first flattened field whose full display path exactly matches a configured key. Composite values do not match because they have no flattened scalar leaf. Default priorities are those in Spec 5. Missing or null message becomes the empty string; missing/null level becomes the literal lowercase `unknown`; missing/null time becomes the empty string. Scalar values are converted to their display text. Thus default formatting turns missing level into `UNKNO`, but a custom `{{fblog_level}}` sees `unknown`.

The original JSON object is also retained unchanged for templates, filtering, dumping, and substitution. Synthetic processing must not overwrite it. A raw selected level or timestamp displayed via `-a`/`-d` therefore remains raw, even when the main-line synthetic value is mapped or converted.

## Spec 10

Timestamp conversion applies only when the selected timestamp text parses as a signed 64-bit base-10 integer. Independently interpret that integer as Unix seconds and as Unix milliseconds in UTC. If both conversions are representable, choose the resulting instant whose absolute distance from the current time is smaller. If only one is representable, choose it; if neither is, retain the original text. Render a converted instant as RFC 3339 UTC with exactly millisecond precision, for example `1716292213` becomes `2024-05-21T11:50:13.000Z` and `1716292213381` becomes `2024-05-21T11:50:13.381Z`.

This closest-to-now rule intentionally makes `4102444800` use milliseconds (a 1970 date) rather than seconds (2100), and `-946684800` use milliseconds (1969) rather than seconds (1940), for contemporary executions. Zero has the same instant under either interpretation and becomes `1970-01-01T00:00:00.000Z`; `1` chooses seconds and becomes `1970-01-01T00:00:01.000Z`; `-1` chooses milliseconds and becomes `1969-12-31T23:59:59.999Z`. Very large values that are valid only as seconds may produce signed years such as `+10000-...`.

Every noninteger timestamp is passed through unchanged, including RFC3339/ISO8601 strings, timezone offsets, fractional seconds, ordinary text, whitespace, and invalid dates. Boolean time becomes `true`; an object or array time produces no exact flattened match. The default 19-byte `fixed_size` helper is what visually removes a trailing `Z`, fractions, offsets, or later characters; a custom template sees the full unmodified string or full converted `...mmmZ` value.

## Spec 11

Level mapping is an exact, case-sensitive lookup from the raw selected level text to a replacement. Unmapped values are unchanged. Multiple mapping flags accumulate; later definitions of the same source win, and CLI definitions override the same configuration-table source.

Mapping is applied after filter evaluation and only to `fblog_level`. A filter sees the raw original JSON level. Original `level`/custom-level fields shown as additional values remain unmapped. Color selection is based on the mapped synthetic level.

## Spec 12

For each valid record the operation order is: prefix extraction; JSON parsing; construction of the original typed filter environment; filter evaluation; detection of the synthetic fields; timestamp conversion and level mapping for synthetic fields; optional message substitution; main template rendering; then additional-field rendering. A rejected filter record emits neither main nor additional lines. Invalid input bypasses these stages and uses the passthrough line from Spec 6.

Every successful main template render is followed by `\n`. Each successful additional field render is another line immediately below its main line, also followed by `\n`. Preserve embedded control characters inside rendered values rather than replacing them with visible escape notation.

## Spec 13

Default main-line output is exactly the default template from Spec 5. Escape notation below denotes literal bytes:

- Timestamp: left-pad/truncate to a width of 19 UTF-8 bytes as defined for `fixed_size` in Spec 15, then `\x1b[1mTEXT\x1b[0m`.
- One literal space.
- Level: left-pad/truncate to a width of 5 UTF-8 bytes as defined for `fixed_size` in Spec 15, uppercase it, then apply bold level color as one opening SGR sequence and one reset.
- A colon; if prefix is nonempty, a space plus bold(cyan(prefix)); then one space plus the message.

Example:

```text
\x1b[1m2023-01-01T00:00:00\x1b[0m \x1b[1;32m INFO\x1b[0m: hello world\n
```

The level colors, matched case-insensitively after ignoring surrounding spaces, are trace→cyan 36, debug→blue 34, info→green 32, warn/warning→yellow 33, error/err→red 31, and fatal→magenta 35. Every other level, including `unknown` and numeric values, uses bold magenta 35. Helper nesting order matters: direct `{{level_style level}}` colors the full value `warning` yellow, whereas the default template first truncates it to `WARNI`, which is then unknown to `level_style` and therefore magenta. Thus an absent level renders `\x1b[1;35mUNKNO\x1b[0m`, and an absent time renders 19 bold spaces.

The default additional-value line is exactly:

```text
\x1b[1m\x1b[38;2;150;150;150mKEY_LEFT_PADDED_TO_AT_LEAST_25\x1b[0m\x1b[0m: VALUE\n
```

Long keys are never truncated by this default because it uses `min_size`, not `fixed_size`.

## Spec 14

Without `-a`, `-d`, `-x`, or configured `always_print_fields`, emit only the main line. Each `-a NAME` selects a flattened leaf whose name is exactly `NAME`, begins `NAME + " > "`, or begins `NAME + "["`. It must not select an unrelated textual prefix (`-a user` does not select `user_id`). Missing fields are silently skipped. Preserve the order of `-a` occurrences; within a selected subtree, use the recursive object-key/array-index traversal order from Spec 8. In particular, an array selection emits indices in increasing numeric order. Configured `always_print_fields` uses the same matching and is emitted in configured order.

`-d` emits every flattened leaf after the main line in the recursive traversal order from Spec 8, including the original message, level, and time fields. Thus object keys are lexicographic but array siblings are numeric/source ordered. `-x NAME` implicitly enables this same dump-all mode and removes the exactly named flattened leaf; multiple exclusions all apply. Config `dump_all_exclude` supplies persistent exclusions. Excluding a nested path such as `data > metadata > created` removes that leaf. No synthetic fields or extracted prefix are dumped. When dump-all is active it controls selection regardless of `-a` and emits each field once.

Additional templates receive `key` as the flattened display path and `value` as the flattened display text. Main-line mapping, timestamp conversion, and substitution do not alter these raw values.

## Spec 15

Both format options are Handlebars-like templates. Support `{{name}}`, nested paths such as `{{user.name}}`, nested helper calls with parenthesized subexpressions, and `{{#if path}}...{{/if}}`. Original JSON fields are available to the main template with typed nested lookup. Missing values render empty. Synthetic fields from Spec 9 are also available. Do not HTML-escape `<`, `>`, `&`, quotes, or Unicode.

Register these helpers, with exactly these effects:

- `uppercase X`: Unicode/string uppercase of X.
- `fixed_size N X`: measure the UTF-8 byte length. If the value is shorter than N bytes, left-pad with `N - byte_length` ASCII spaces. If it is longer, truncate at byte offset N. Truncation succeeds when N is a UTF-8 character boundary; when it is not, the process panics with status 101 and a diagnostic containing `assertion failed: self.is_char_boundary(new_len)`. For example, `fixed_size 2` applied to `é😊x` produces `é`, while widths 1, 3, 4, and 5 panic; `fixed_size 19` applied to `🕐 10:30:00` adds six leading spaces.
- `min_size N X`: left-pad to N characters when shorter, never truncate.
- `bold X`: `\x1b[1mX\x1b[0m`.
- `red`, `yellow`, `blue`, `purple`, `green`, `cyan`: respectively wrap with SGR 31, 33, 34, 35, 32, or 36 and a final `\x1b[0m`.
- `color_rgb R G B X`: `\x1b[38;2;R;G;BmX\x1b[0m`, accepting inclusive component endpoints 0 and 255.
- `level_style X`: the bold color mapping in Spec 13 and a reset.

Helpers nest literally, retaining every nested opener and reset. For example `{{bold (yellow fblog_level)}}` produces `\x1b[1m\x1b[33mLEVEL\x1b[0m\x1b[0m`. Parenthesized helper syntax is accepted both with and without a space between helper name and `(`, as used in the default templates.

Invalid template syntax is detected before record processing and terminates with a nonzero/panic status. The stderr diagnostic contains `panicked at src/template.rs:<error location>:`, `Template invalid: TemplateError`, the template name (`main_line` for the main template), and one-based line/column information. A helper type error during main rendering is nonfatal and emits to stdout:

```text
\x1b[1;31m??? >\x1b[0m Failed to process line: ERROR_TEXT\n
```

instead of that record’s normal output. An additional-template error leaves the main line intact and emits, once for every selected field:

```text
\x1b[1;31m   ??? >\x1b[0m Failed to process additional value: ERROR_TEXT\n
```

For `{{color_rgb "not" 0 0 fblog_message}}`, the main-render `ERROR_TEXT` is exactly `Error rendering "main_line" line 1, col 1: Helper/Decorator color_rgb param with name r type mismatch for u64`. For `{{min_size "not_a_number" key}}`, each selected field's additional-render `ERROR_TEXT` is exactly `Error rendering "additional_value" line 1, col 1: Helper/Decorator min_size param with name isize type mismatch for u64`.

## Spec 16

Substitution is disabled by default. `-s` enables it; specifying `-c` or `-F` also enables it implicitly. The context key defaults to the top-level key `context`. The placeholder format defaults to `{key}` and must contain the literal substring `key`; otherwise terminate nonzero/panic (compatible status 101) with `Invalid placeholder format: The identifier `key` is missing` on stderr.

Treat the placeholder format as literal text surrounding the occurrence of `key`; regex metacharacters in delimiters are literal. Formats including `{key}`, `{{key}}`, `[key]`, `[[key]]`, `${key}`, `#{key}`, `%key%`, and `%{key}` therefore work. Placeholder names are case-sensitive and consist of ASCII letters, digits, underscore, or hyphen. Replace every occurrence, including duplicates and adjacent placeholders.

For object contexts, use the placeholder name as an exact property key. For array contexts, parse it as a zero-based decimal index (`{0}` is the first element). If the whole context key is absent, leave the entire original message unchanged and unstyled. If context exists but is empty, primitive, has no such key, or an array index is invalid/out of bounds, retain that placeholder text but style its delimiters dim and its key bold red. This missing form for `{missing}` is `\x1b[2m{\x1b[0m\x1b[1;31mmissing\x1b[0m\x1b[2m}\x1b[0m`.

Substitution changes only `fblog_message`; filters and additional/dump fields continue to see the original JSON value.

## Spec 17

Successful substitution values are rendered with type-sensitive ANSI styling:

- String: raw text in bold yellow, `\x1b[1;33mTEXT\x1b[0m`.
- Number: natural JSON number text in bold cyan, `\x1b[1;36mN\x1b[0m`.
- Boolean: lowercase `true` in bold green or `false` in bold red.
- Null: literal `null` in bold.
- Array: dim `[` and `]` and dim `, ` separators; recursively styled elements.
- Object: dim braces and dim `: ` / `, ` separators; keys in non-bold magenta (`\x1b[35mKEY\x1b[0m`), values recursively styled, and keys in lexicographic order.

Arrays and objects use a compact single-line representation without quotes around styled string values. Empty arrays/objects render only their styled delimiters. Nested arrays/objects recurse. Empty string is a successful value and removes the placeholder except for its zero-length styled span; 0 and false are valid, not missing. Unicode and very long values are preserved.

## Spec 18

`-f/--filter` evaluates a Lua expression separately for every valid JSON object. By default execute it as though `return ` were prepended. With `--no-implicit-filter-return-statement`, execute the supplied text as a complete Lua chunk so statements and explicit returns such as `if ... then return true else return false end` work. Lua false and nil reject a record; every other returned value is truthy.

Expose each top-level JSON property as a Lua global, sorted lexicographically by original property name. Sanitize every character that is not an ASCII letter, digit, or underscore to `_`, at every object level (`log.level`→`log_level`, `app-name`→`app_name`). Preserve Lua data types for strings, finite numbers, and Booleans. Convert JSON null to the literal Lua string `"unsupported"`. Convert objects recursively to Lua tables. Convert arrays to one-based Lua sequences; primitive members retain type, while null, object, or array members inside an array become the string `"unsupported"`. Empty object and empty array both become `{}`.

Support normal Lua comparison/arithmetic/truth rules and at least `==`, `~=`, `<`, `<=`, `>`, `>=`, `%`, parentheses, `and`, `or`, `not`, `nil`, `true`, `false`, `tonumber`, and the standard `string.find`, `string.lower`, `string.upper`, and `string.len`. `string.find` uses Lua patterns, including `%d+`, `.*`, and escaped `%-`. Comparisons are case-sensitive. Missing globals are nil. Nested object access uses dots; Lua arrays are one-based.

Filtering occurs on original data before level mapping and substitution. Prefix extraction happens before filtering. Exclusions affect display only and do not remove filter globals.

An invalid filter syntax or runtime/pattern error is nonfatal: suppress that valid record, write one line to stderr beginning `\x1b[31mFailed to apply filter expression\x1b[0m: ` followed by the quoted debug form of the Lua error, and continue. Syntax errors contain `SyntaxError`; malformed patterns preserve messages such as `malformed pattern (missing ']')`. A truthy value such as Lua’s infinity from `1/0` passes.

The debug form includes the parser source location and `incomplete_input` field. In particular, filter text `invalid syntax` produces exactly:

```text
\x1b[31mFailed to apply filter expression\x1b[0m: 'SyntaxError { message: "src/filter.rs:<error location>: <eof> expected near 'syntax'", incomplete_input: false }'\n
```

An unclosed double-quoted string, as in `message == "test`, includes `unfinished string` and produces exactly:

```text
\x1b[31mFailed to apply filter expression\x1b[0m: 'SyntaxError { message: "src/filter.rs:<error location>: unfinished string near <eof>", incomplete_input: true }'\n
```

## Spec 19

When `--print-lua` accompanies filtering, write the generated top-level Lua assignments to stdout immediately before the possible formatted output for each valid record, including records the filter later rejects. Emit one `NAME = VALUE\n` assignment per top-level key in lexicographic order. Formatting is compact:

- strings use double quotes and escape backslash, newline, carriage return, tab, double quote, and single quote as `\\`, `\n`, `\r`, `\t`, `\"`, and `\'`;
- numbers and Booleans are bare;
- null is `"unsupported"`;
- arrays use `{a,b,c}` without spaces;
- objects use `{sanitized_key = value,...}` without spaces after commas but with spaces around `=`.

For example, the record `{"level":"info","message":"test","process":"app"}` prints:

```text
level = "info"
message = "test"
process = "app"
```

before its normal line. An empty array `tags` and empty object `meta` each print `tags = {}` / `meta = {}`. A primitive array prints, for example, `items = {true,false,true}`; an array of object/array/null values prints `items = {"unsupported","unsupported","unsupported"}`.

## Spec 20

`--generate-completions bash`, `zsh`, and `fish` exit 0, write `Generating completion file for SHELL...\n` to stderr, and write a deterministic completion script to stdout. Generated scripts target the installed command name `fblog`, even though the evaluated artifact is named `executable`. They expose the hidden completion option and its shell choices `bash elvish fish powershell zsh`. The exact fish script is:

```fish
complete -c fblog -s a -l additional-value -d 'adds additional values' -r
complete -c fblog -l config-file -d 'configuration file to load' -r
complete -c fblog -l generate-completions -r -f -a "bash\t''
elvish\t''
fish\t''
powershell\t''
zsh\t''"
complete -c fblog -s m -l message-key -d 'Adds an additional key to detect the message in the log entry. The first matching key will be assigned to `fblog_message`.' -r
complete -c fblog -s t -l time-key -d 'Adds an additional key to detect the time in the log entry. The first matching key will be assigned to `fblog_timestamp`.' -r
complete -c fblog -s l -l level-key -d 'Adds an additional key to detect the level in the log entry. The first matching key will be assigned to `fblog_level`.' -r
complete -c fblog -l map-level -d 'Rewrite the log level from one value to another.' -r
complete -c fblog -s x -l excluded-value -d 'Excludes values (--dump-all is enabled implicitly)' -r
complete -c fblog -s f -l filter -d 'lua expression to filter log entries. `message ~= nil and string.find(message, "text.*") ~= nil`' -r
complete -c fblog -l main-line-format -d 'Formats the main fblog output. All log values can be used. fblog provides sanitized variables starting with `fblog_`.' -r
complete -c fblog -l additional-value-format -d 'Formats the additional value fblog output.' -r
complete -c fblog -s c -l context-key -d 'Use this key as the source of substitutions for the message. Value can either be an array ({1}) or an object ({key}).' -r
complete -c fblog -s F -l placeholder-format -d 'The format that should be used for substituting values in the message, where the key is the literal word `key`. Example: [[key]] or ${key}.' -r
complete -c fblog -l print-lua -d 'Prints lua init expressions. Used for fblog debugging.'
complete -c fblog -s d -l dump-all -d 'dumps all values'
complete -c fblog -s p -l with-prefix -d 'consider all text before opening curly brace as prefix'
complete -c fblog -l no-implicit-filter-return-statement -d 'if you pass a filter expression \'return\' is automatically prepended. Pass this switch to disable the implicit return.'
complete -c fblog -s s -l substitute -d 'Enable substitution of placeholders in the log messages with their corresponding values from the context.'
complete -c fblog -s h -l help -d 'Print help'
complete -c fblog -s V -l version -d 'Print version'
```

The exact bash script is:

```bash
_fblog() {
    local i cur prev opts cmd
    COMPREPLY=()
    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
        cur="$2"
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
    fi
    prev="$3"
    cmd=""
    opts=""

    for i in "${COMP_WORDS[@]:0:COMP_CWORD}"
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="fblog"
                ;;
            *)
                ;;
        esac
    done

    case "${cmd}" in
        fblog)
            opts="-a -m -t -l -d -x -p -f -s -c -F -h -V --additional-value --config-file --generate-completions --message-key --print-lua --time-key --level-key --map-level --dump-all --excluded-value --with-prefix --filter --no-implicit-filter-return-statement --main-line-format --additional-value-format --substitute --context-key --placeholder-format --help --version [INPUT]"
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                --additional-value)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -a)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --config-file)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --generate-completions)
                    COMPREPLY=($(compgen -W "bash elvish fish powershell zsh" -- "${cur}"))
                    return 0
                    ;;
                --message-key)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -m)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --time-key)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -t)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --level-key)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -l)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --map-level)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --excluded-value)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -x)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --filter)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -f)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --main-line-format)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --additional-value-format)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --context-key)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -c)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --placeholder-format)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -F)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
    esac
}

if [[ "${BASH_VERSINFO[0]}" -eq 4 && "${BASH_VERSINFO[1]}" -ge 4 || "${BASH_VERSINFO[0]}" -gt 4 ]]; then
    complete -F _fblog -o nosort -o bashdefault -o default fblog
else
    complete -F _fblog -o bashdefault -o default fblog
fi
```

The exact zsh script is:

```zsh
#compdef fblog

autoload -U is-at-least

_fblog() {
    typeset -A opt_args
    typeset -a _arguments_options
    local ret=1

    if is-at-least 5.2; then
        _arguments_options=(-s -S -C)
    else
        _arguments_options=(-s -C)
    fi

    local context curcontext="$curcontext" state line
    _arguments "${_arguments_options[@]}" : \
'(-x --excluded-value)*-a+[adds additional values]: :_default' \
'(-x --excluded-value)*--additional-value=[adds additional values]: :_default' \
'--config-file=[configuration file to load]: :_default' \
'--generate-completions=[]: :(bash elvish fish powershell zsh)' \
'*-m+[Adds an additional key to detect the message in the log entry. The first matching key will be assigned to \`fblog_message\`.]: :_default' \
'*--message-key=[Adds an additional key to detect the message in the log entry. The first matching key will be assigned to \`fblog_message\`.]: :_default' \
'*-t+[Adds an additional key to detect the time in the log entry. The first matching key will be assigned to \`fblog_timestamp\`.]: :_default' \
'*--time-key=[Adds an additional key to detect the time in the log entry. The first matching key will be assigned to \`fblog_timestamp\`.]: :_default' \
'*-l+[Adds an additional key to detect the level in the log entry. The first matching key will be assigned to \`fblog_level\`.]: :_default' \
'*--level-key=[Adds an additional key to detect the level in the log entry. The first matching key will be assigned to \`fblog_level\`.]: :_default' \
'*--map-level=[Rewrite the log level from one value to another.]:from=to:_default' \
'(-a --additional-value)*-x+[Excludes values (--dump-all is enabled implicitly)]: :_default' \
'(-a --additional-value)*--excluded-value=[Excludes values (--dump-all is enabled implicitly)]: :_default' \
'-f+[lua expression to filter log entries. \`message ~= nil and string.find(message, "text.*") ~= nil\`]: :_default' \
'--filter=[lua expression to filter log entries. \`message ~= nil and string.find(message, "text.*") ~= nil\`]: :_default' \
'--main-line-format=[Formats the main fblog output. All log values can be used. fblog provides sanitized variables starting with \`fblog_\`.]: :_default' \
'--additional-value-format=[Formats the additional value fblog output.]: :_default' \
'-c+[Use this key as the source of substitutions for the message. Value can either be an array ({1}) or an object ({key}).]: :_default' \
'--context-key=[Use this key as the source of substitutions for the message. Value can either be an array ({1}) or an object ({key}).]: :_default' \
'-F+[The format that should be used for substituting values in the message, where the key is the literal word \`key\`. Example\: \[\[key\]\] or \${key}.]: :_default' \
'--placeholder-format=[The format that should be used for substituting values in the message, where the key is the literal word \`key\`. Example\: \[\[key\]\] or \${key}.]: :_default' \
'--print-lua[Prints lua init expressions. Used for fblog debugging.]' \
'-d[dumps all values]' \
'--dump-all[dumps all values]' \
'-p[consider all text before opening curly brace as prefix]' \
'--with-prefix[consider all text before opening curly brace as prefix]' \
'--no-implicit-filter-return-statement[if you pass a filter expression '\''return'\'' is automatically prepended. Pass this switch to disable the implicit return.]' \
'-s[Enable substitution of placeholders in the log messages with their corresponding values from the context.]' \
'--substitute[Enable substitution of placeholders in the log messages with their corresponding values from the context.]' \
'-h[Print help]' \
'--help[Print help]' \
'-V[Print version]' \
'--version[Print version]' \
'::INPUT -- Sets the input file to use, otherwise assumes stdin:_files' \
&& ret=0
}

(( $+functions[_fblog_commands] )) ||
_fblog_commands() {
    local commands; commands=()
    _describe -t commands 'fblog commands' commands "$@"
}

if [ "$funcstack[1]" = "_fblog" ]; then
    _fblog "$@"
else
    compdef _fblog fblog
fi
```

All three scripts include their final newline and the indentation and quoting shown.

If the completion option has no shell operand, it is a normal missing-value parse error. Bash, zsh, and fish output must be nontrivial (well over 100 bytes).

## Spec 21

The program is a streaming formatter, not a TUI: it never prompts, waits for terminal interaction, or changes behavior because stdout is/is not a terminal. It must preserve record order and continue after any number of malformed lines, filter failures, or per-record template-render failures. Configuration/input-open/template-registration/placeholder-format errors are startup-fatal; record parse/read/filter/render errors are nonfatal as described above.

All ordinary diagnostics go to stderr; ordinary formatted output, invalid-input passthrough markers, read-error markers, debug assignments, and per-record rendering-error marker lines go to stdout as specified. Do not print logging banners or other incidental output during normal processing.

## Spec 22

The behavior is compositional. In particular:

- `-p -f` parses the JSON suffix, filters its fields, and retains the prefix only for accepted records.
- `-f -d` emits the main line and all raw flattened fields only for accepted records.
- level mapping never changes what a filter sees, but changes the main-line level after acceptance.
- substitution happens only for accepted records and changes only the synthetic message.
- `-s -f -a`, custom templates, custom keys, configured mappings, prefix mode, and field selection may all be combined without disabling one another.
- Missing standard fields never prevent selected additional fields from being displayed.
- Every ordering guarantee from the individual features still applies when features are combined.

These interactions and all text/ANSI byte sequences above are part of the observable interface.
