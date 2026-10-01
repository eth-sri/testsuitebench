# Tailspin executable specification

The required artifact is a directly runnable program named exactly `executable`. It is a command-line log highlighter compatible with `tspin` 5.6.0. In the examples below, `ESC` means the single byte `0x1b`; ANSI styles always end with `ESC[0m`.

## Spec 1

`executable` has one optional positional argument, `[FILE]`, and no subcommands. A word such as `add`, `list`, or `show` is therefore a file name, not a command. Options may occur before or after the file. `--` ends option parsing, but does not increase the limit of one positional argument; for example, `-- --nonflag` tries to open a file literally named `--nonflag`, while two positional arguments are a parse error.

The public options are:

- `-f`, `--follow`
- `-p`, `--print`
- `--config-path <CONFIG_PATH>`
- `-e`, `--exec <EXEC>`
- repeatable `--highlight <COLOR_WORD>`
- repeatable and comma-delimited `--enable <ENABLED_HIGHLIGHTERS>`
- repeatable and comma-delimited `--disable <DISABLED_HIGHLIGHTERS>`
- `--disable-builtin-keywords`
- `--pager <PAGER>`
- `-h`, `--help`
- `-V`, `--version`

There are also three hidden completion-generation flags described in Spec 20. Long valued options accept both `--option value` and `--option=value`.

## Spec 2

`--version` and `-V` write exactly `tspin 5.6.0\n` to stdout, write nothing to stderr, and exit 0.

With terminal width 120 columns, `--help` must write exactly the following plain UTF-8 text, including blank lines, indentation, wrapping, and final newline, to stdout; stderr is empty and the exit status is 0. `-h` must at least have the same first description and usage line and document the same interface.

```text
A log file highlighter

Usage: executable [OPTIONS] [FILE]

Arguments:
  [FILE]
          Filepath

Options:
  -f, --follow
          Follow the contents of a file

  -p, --print
          Print the output to stdout

      --config-path <CONFIG_PATH>
          Provide a custom path to a configuration file

  -e, --exec <EXEC>
          Run command and view the output in a pager

      --highlight <COLOR_WORD>
          Highlights in the form color:word1,word2
          
          [possible values: red, green, yellow, blue, magenta, cyan]

      --enable <ENABLED_HIGHLIGHTERS>
          Enable specific highlighters
          
          [possible values: numbers, urls, pointers, dates, paths, quotes, key-value-pairs, uuids,
          ip-addresses, processes, json]

      --disable <DISABLED_HIGHLIGHTERS>
          Disable specific highlighters
          
          [possible values: numbers, urls, pointers, dates, paths, quotes, key-value-pairs, uuids,
          ip-addresses, processes, json]

      --disable-builtin-keywords
          Disable the highlighting of all builtin keyword groups (booleans, nulls, log severities and
          common REST verbs)

      --pager <PAGER>
          Override the default pager command used by tspin. (e.g. `--pager="ov -f [FILE]"`)
          
          [env: TAILSPIN_PAGER=]

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

Help contains no ANSI escapes and no `Commands:` or `Subcommands:` section.

## Spec 3

Command-line syntax failures exit 2, write nothing to stdout, and write a clap-style diagnostic to stderr. An unknown option has this form (substitute the actual option and include already accepted flags in the usage synopsis):

```text
error: unexpected argument '--invalid-flag' found

  tip: to pass '--invalid-flag' as a value, use '-- --invalid-flag'

Usage: executable [OPTIONS] [FILE]

For more information, try '--help'.
```

With `--print --invalid-flag`, the usage line is `Usage: executable --print [FILE]`. Missing values say, for example, `error: a value is required for '--exec <EXEC>' but none was supplied`, followed by a blank line and `For more information, try '--help'.`; use the corresponding labels `<PAGER>`, `<CONFIG_PATH>`, and `<COLOR_WORD>`. The two highlighter-selection options are an exception: a missing `--enable` or `--disable` value inserts the complete possible-values line immediately after the required-value line and before the blank line. Their exact diagnostics are:

```text
error: a value is required for '--enable <ENABLED_HIGHLIGHTERS>' but none was supplied
  [possible values: numbers, urls, pointers, dates, paths, quotes, key-value-pairs, uuids, ip-addresses, processes, json]

For more information, try '--help'.
```

```text
error: a value is required for '--disable <DISABLED_HIGHLIGHTERS>' but none was supplied
  [possible values: numbers, urls, pointers, dates, paths, quotes, key-value-pairs, uuids, ip-addresses, processes, json]

For more information, try '--help'.
```

Boolean switches reject assignments such as `--follow=true` with `unexpected value 'true' for '--follow'`. A second positional reports `unexpected argument '<value>' found`.

The only enable/disable choices are, in this order: `numbers`, `urls`, `pointers`, `dates`, `paths`, `quotes`, `key-value-pairs`, `uuids`, `ip-addresses`, `processes`, `json`. Invalid choices name the option and show `[possible values: ...]`; close misspellings also contain `a similar value exists`. In particular, `--enable nope` exits 2 and, after the possible-values line and a blank line, prints `  tip: a similar value exists: 'pointers'`, then another blank line and the help hint. Supplying any `--enable` together with any `--disable` is a runtime error (exit 1) containing `cannot both enable and disable highlighters`.

For example, the complete invalid-choice diagnostic is:

```text
error: invalid value 'invalid-highlighter' for '--enable <ENABLED_HIGHLIGHTERS>'
  [possible values: numbers, urls, pointers, dates, paths, quotes, key-value-pairs, uuids, ip-addresses, processes, json]

For more information, try '--help'.
```

Use the same format and `<DISABLED_HIGHLIGHTERS>` label for `--disable`. The missing-highlight-value diagnostic is exactly:

```text
error: a value is required for '--highlight <COLOR_WORD>' but none was supplied

For more information, try '--help'.
```

## Spec 4

Input selection has this precedence:

1. A positional file is used and any piped stdin is ignored.
2. A file and `--exec` together are invalid, exit 1, and report `Cannot read from both file and ESC[35m--listen-commandESC[0m`. This also covers file + follow + exec.
3. Noninteractive/piped stdin is selected whenever there is no file, even when `--exec` is also present. It takes precedence over `--exec`: the command is not run, including when its name is nonexistent or its shell command would fail. A pipe implies print mode even without `--print`; `--follow` and `--pager` are ignored for stdin.
4. With no file or piped stdin, `--exec` selects the compatibility command-source behavior in Spec 21.
5. With no file/exec and an interactive terminal as stdin, exit 0 after displaying `Missing filename (ESC[36mtspin --helpESC[0m for help)` followed by a terminal line ending.

`--print` and `-p` send processed text directly to stdout. For stdin, a nonempty final line is emitted with a newline even if its source lacked one. A regular-file read emits only newline-terminated lines and discards an unterminated final line: a file containing only `abc` produces exactly `\n`, while `abc\ndef` produces exactly `abc\n`. This applies regardless of option spelling/order, file-name spelling, file-versus-piped-stdin selection, or pager bypass. Existing tabs, blank lines, repeated trailing newlines, Unicode, NUL bytes, and ordinary punctuation in emitted lines are retained. In a regular file, the carriage return of a CRLF line ending is removed: source bytes `cr\r\n` are emitted as `cr\n`. Empty stdin produces zero bytes. By compatibility convention, an empty regular file produces one newline. A non-following file read terminates immediately.

## Spec 5

Opening a nonexistent file is a runtime error with exit 1, empty stdout, and this stderr shape:

```text
Error:   ⚠ ESC[33m<path>ESC[0m: No such file or directory

```

The supplied spelling of the path appears in the message. A directory instead of a file exits 1 with exactly `Error:   × Path is not a file\n\n`. Broken symlinks are treated as missing files. Paths may contain spaces, arbitrary UTF-8, and lengths near operating-system limits.

Input is processed without practical line-length or file-size truncation: lines of at least 100,000 characters, 10,000-line files, and the bundled multi-hundred-kilobyte example logs must complete promptly; a 10,000-line plain file is expected to finish within two seconds on the evaluation host. If stdout is closed early while a substantial stdin stream is being written, the reference exits 1 and stderr contains a Tokio worker panic with `failed printing to stdout: Broken pipe (os error 32)`, followed by an executable error of the form `Error:   × task <number> panicked with message "failed printing to stdout: Broken pipe (os error 32)"`. Existing ANSI escapes must not cause a crash and their visible text remains. Invalid UTF-8 in a log file is handled without a panic; the reference diagnostic is:

```text
Error:   × Failed to receive initial-read-complete signal
  ╰─▶ channel closed
  help: Ensure the IO task completes correctly and signals initial read
        completion.

```

## Spec 6

Highlighting is a streaming transformation of text. Apart from the explicitly documented date, REST-verb, and JSON whitespace transformations, removing all ANSI SGR sequences from successful print output yields the emitted input text under the regular-file/stdin conventions in Spec 4. Every styled span is `ESC[<codes>m<span>ESC[0m`; do not leave styles open across spans or lines.

All structural groups are enabled by default. `--disable` removes each listed structural group and may be repeated or comma-delimited. `--enable` restricts structural matching to the listed groups and likewise accepts repetitions and comma lists. Repeated identical entries are idempotent. Built-in keywords are controlled independently by `--disable-builtin-keywords`; custom keyword rules continue to work when built-ins are disabled. CLI selection overrides whether a configured structural group runs.

More specific structured matches must win over generic ones so their contents are not subsequently fragmented: custom regex captures, UUIDs, IP addresses, dates/times, URLs, paths, processes, pointers, JSON/key-value structures, quotes, and finally ordinary numbers. Built-in keyword rules take precedence over a custom keyword for the same span. The first custom definition of an otherwise duplicate word wins.

## Spec 7

The default ANSI styles are as follows. SGR numbers are combined with semicolons in attribute-then-color order.

| Element | SGR/style |
|---|---|
| ordinary number | cyan, `36` |
| UUID/IP/pointer digit | italic blue, `3;34` |
| UUID/IP/pointer hex letter | italic magenta, `3;35` |
| UUID dash, IP separator, pointer `x` | red, `31` |
| inserted pointer midpoint separator | dim, `2` |
| date component | magenta, `35` |
| time component | blue, `34` |
| date/time separator | dim, `2` |
| date-to-time separator or literal `Z` zone token | red, `31` |
| path separator `/` | yellow, `33` |
| path segment | green, `32` |
| URL `http` / `https` | dim red `2;31` / dim green `2;32` |
| URL host | dim blue, `2;34` |
| URL path | blue, `34` |
| URL query key/value | magenta `35` / cyan `36` |
| URL query symbols | red, `31` |
| process name/bracket/PID | yellow `33` / red `31` / cyan `36` |
| quote-highlighter span | yellow, `33` |
| key in `key=value` | dim, `2` |
| key/value separator | white, `37` |
| recognized JSON punctuation, quote tokens, and keys | dim, `2` |

Plain text receives no ANSI codes. For example, `Hello null` becomes `Hello ESC[3;31mnullESC[0m\n`, while `Hello world` becomes `Hello world\n`.

## Spec 8

Built-in keyword recognition uses whole-word, case-sensitive matching. The exact built-ins and styles are:

- `true`, `false`, `null`: italic red (`3;31`). Capitalized or uppercase forms are plain.
- `INFO`: white (`37`); `ERROR`: red (`31`); `WARN`: yellow (`33`); `DEBUG` and `SUCCESS`: green (`32`); `TRACE`: dim (`2`). `WARNING`, `FATAL`, and `CRITICAL` are not built-ins.
- `GET`: green background with black foreground (`42;30`); `POST`: yellow background/black (`43;30`); `PUT` and `PATCH`: magenta background/black (`45;30`); `DELETE`: red background/black (`41;30`). `HEAD` and `OPTIONS` are plain.

Each REST verb is padded inside its colored span: input `GET` produces `ESC[42;30m GET ESC[0m`. Word boundaries include whitespace, tabs, newlines, and punctuation. Keywords work inside quotes, JSON, and key/value values. `--disable-builtin-keywords` removes all rules in this section and does not remove structural or custom highlighting.

## Spec 9

Each repeatable `--highlight` value is `COLOR:word1,word2,...`, where `COLOR` is exactly one of `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, mapped to SGR 31–36. The words are literal UTF-8 strings, not regexes; characters such as `[`, `$`, `.`, `_`, `-`, `!`, and `?` are literal. Match all occurrences, using whole-word boundaries so `test` does not match `testing` or `retest`. Matching is case-sensitive: `red:test` matches `test` but leaves `TEST` plain. A punctuation-bearing configured term such as `error!` matches the whole literal term.

Multiple words and flags are merged. The first definition wins when the same word is repeated with different colors; duplicate identical definitions do not nest styles. Built-in rules retain priority (for example, `--highlight green:ERROR` still renders built-in `ERROR` as red), unless built-ins have been disabled.

Malformed values are syntax errors (exit 2). Exact examples are:

```text
error: invalid value 'red' for '--highlight <COLOR_WORD>': Expected format COLOR:word1,word2,... found `red`

For more information, try '--help'.
```

An invalid color says `invalid variant: <color>`. The empty string reports the expected-format error, and bare `:` reports `invalid variant: `. A color followed by an empty list, such as `red:`, is accepted and adds no rule.

## Spec 10

The `numbers` group recognizes unsigned decimal integers and fractions at token boundaries and styles the matched token cyan by default. `0`, `123`, `45.67`, `0.5`, and large/precise decimal values are each one cyan span. A leading sign is preserved but is outside the span: `-42` renders as `-ESC[36m42ESC[0m`, and `+789` as `+ESC[36m789ESC[0m`. A leading decimal point is likewise outside: `.5` renders as `.ESC[36m5ESC[0m`.

ASCII word characters prevent an embedded match, and scientific notation is not recognized as one number. Exactly, `a123b 1e10 -2.5E-7` renders as `a123b 1e10 -ESC[36m2ESC[0m.5E-ESC[36m7ESC[0m`; all visible characters are retained. Hex, octal, and binary-looking text remains intact; a valid pointer may instead consume a hexadecimal form. Disabling `numbers` leaves these tokens completely plain unless they lie inside another active structured match.

For example, `Numbers: 123 456.789 0x1A2B 3.14159` becomes:

```text
Numbers: ESC[36m123ESC[0m ESC[36m456.789ESC[0m 0x1A2B ESC[36m3.14159ESC[0m
```

## Spec 11

The `dates` group recognizes dates such as `YYYY-MM-DD`, `YYYY/MM/DD`, legacy day/month/year or month/day/year forms, times `HH:MM:SS`, optional fractional seconds separated by `.`, `,`, or `:`, and ISO-8601 combinations with `T`, a terminal `Z`, or numeric offsets. Date components are individually styled with the date style; separators are individually styled with the separator style. Time components and fractional seconds use the time style. In a combined timestamp, the joining space or `T` and a terminal literal `Z` use the zone style. The `dates` group applies no styling to a numeric offset: with only `dates` enabled, `2024-01-01T00:00:00+02:30` has its date, `T`, and time styled as above while the complete `+02:30` suffix is plain. If `numbers` is also enabled, its generic rules separately style `02` and `30` cyan, leaving `+` and `:` plain.

Legacy forms are normalized to year-month-day. In particular, input `01-15-2024` is rendered as the visible text `2024-01-15`. A representative default rendering is:

```text
ESC[35m2024ESC[0mESC[2m-ESC[0mESC[35m01ESC[0mESC[2m-ESC[0mESC[35m15ESC[0mESC[31m ESC[0mESC[34m14ESC[0mESC[2m:ESC[0mESC[34m30ESC[0mESC[2m:ESC[0mESC[34m45ESC[0m
```

Time-only forms use the time and separator styles. Syslog month names may remain plain while their numeric day and time portions are highlighted.

## Spec 12

The `urls` group recognizes `http://` and `https://` at line boundaries and within prose. For an ordinary domain without a port it parses and separately styles protocol, host, path, query punctuation, keys, and values; query strings may contain multiple `&`-separated pairs. The complete visible URL is preserved. Even an empty path after a host produces an empty path style/reset pair, as in this exact output:

```text
URLs: ESC[2;32mhttpsESC[0m://ESC[2;34mgithub.comESC[0mESC[34mESC[0m ESC[2;31mhttpESC[0m://ESC[2;34mexample.orgESC[0mESC[34mESC[0m ftp://ftp.test.com
```

An explicit port terminates URL parsing after the hostname. With only `urls` enabled, `http://localhost:8080/a/b?q=one&n=2` becomes `ESC[2;31mhttpESC[0m://ESC[2;34mlocalhostESC[0mESC[34mESC[0m:8080/a/b?q=one&n=2`; the port and everything after it receive no URL style. With all groups enabled, other matchers may style parts of that remainder. A numeric host has a stronger interaction: the earlier IP matcher consumes `0.0.0.0`, so default processing of `http://0.0.0.0:8080` leaves `http://` plain, applies IP styles to the address, leaves `:`, and styles `8080` as an ordinary number.

`ftp://` is not URL-highlighted but is passed through. The `paths` group recognizes absolute `/a/b`, relative `./a` and `../a`, and home-relative `~/a` paths, including extensions and dot files. An absolute path requires at least two segments: the one-segment form `/a` is not a path match and remains entirely plain when no other matcher applies. Style every slash separately and each segment separately. Disabling these groups leaves their text untouched; disabling URLs and paths together must make a standalone URL plain (also disable key-value-pairs if its query must remain wholly plain).

## Spec 13

The `ip-addresses` group recognizes valid IPv4 and IPv6 spellings, including `0.0.0.0`, `255.255.255.255`, `::1`, `fe80::`, full eight-group IPv6, IPv4-mapped IPv6, bracketed IPv6, and optional zone suffixes. IPv4 octets and IPv6 digits use the digit style, hexadecimal letters use the letter style, and `.`/`:` separators use the separator style. Do not treat an invalid IPv4 octet as a valid complete IPv4 address.

The `uuids` group recognizes exactly the case-insensitive hexadecimal `8-4-4-4-12` form. It styles every digit or letter as its own span and each hyphen as its own span. Near misses with an incorrect segment length are not UUID matches (their ordinary numeric parts may still be highlighted).

The `pointers` group recognizes `0x` followed by exactly 8 or 16 hexadecimal digits, case-insensitively. Style `0`, `x`, and each subsequent character separately. For a 16-digit address, insert the configured separator token between the two groups of eight; the default is a dim `•`. Other lengths remain available to generic matching and are not a pointer match.

## Spec 14

The `processes` group recognizes a process-like name followed immediately by a numeric PID in square brackets, such as `systemd[1]`, `nginx[1234]`, and names containing punctuation such as `(udev-worker)[1]`. The name, each bracket, and PID are separately styled. Parenthesized PID forms must remain intact and may receive generic number highlighting.

The `quotes` group defaults to the straight double quote token and styles a token-delimited span, including both tokens. Multiple ordinary spans work, but backslash does not escape the configured token. Thus `one "hello" two "a \"quote\" here" end` renders as `one ESC[33m"hello"ESC[0m two ESC[33m"a \"ESC[0mquote\ESC[33m" here"ESC[0m end`. Built-in matching can also prevent the enclosing quote span: `status="true" error="false"` styles the two keys and equals signs, leaves all four quote characters plain, and applies italic red only to `true` and `false`. Straight single-quoted text is plain under the default theme; changing `quotes_token` in the theme replaces the default token and can instead enable single quotes.

The `key-value-pairs` group recognizes a key made only of ASCII letters, digits, or underscore when it begins the line or follows whitespace and is immediately followed by `=`. The key and equals sign are styled separately; whitespace may follow the equals sign and values are left for other highlighters. It works repeatedly on one line and with boolean, number, empty-string, and punctuation-bearing values. It does not recognize `:`, whitespace before `=`, keys preceded immediately by `[`, `-`, or `,`, or dotted/hyphenated keys. Consequently `Emoji test:`, `Special chars:`, `localhost:5432`, `plugin:`, and `com.desuperior:dsmeta:` remain plain. In `[SessionId=E621, ExperienceId=5CEE]`, `SessionId=` remains plain because `[` precedes it, while `ExperienceId=` is styled because it follows a space.

The `json` group recognizes a line that is any valid JSON value, including an object, array, or bare string. It rewrites recognized JSON to a spaced compact form. For example, the visible text of `{"outer":{"items":[1,true,null,"x"]}}` becomes `{ "outer": { "items": [1, true, null, "x"] } }`. JSON structural punctuation, quote tokens, and keys receive the JSON styles while numbers and built-in booleans/null retain their more specific styles. A bare input `"quoted"` is therefore handled by JSON: only its two quote tokens are dim, its contents are plain, and the same result occurs with `--disable quotes --disable-builtin-keywords` because JSON remains enabled. JSON-like text prefixed by ordinary prose need not activate the JSON parser; quotes and numbers still highlight normally.

## Spec 15

A custom UTF-8 TOML theme is selected by `--config-path`. An explicitly supplied path always takes precedence over any environment/default theme and must be opened and validated even if another valid theme exists. When no explicit path is supplied, a missing default theme is not an error: use built-in defaults. Default locations are `$XDG_CONFIG_HOME/tailspin/theme.toml`, or `$HOME/.config/tailspin/theme.toml` when `XDG_CONFIG_HOME` is unset.

An empty theme is valid and retains every default. Unknown tables and unknown fields are ignored. A theme can partially override any field, with unspecified sections and fields retaining defaults. The supported structural tables and style-valued fields are:

```text
[numbers]         number
[uuids]           number, letter, dash
[quotes]          quotes_token (one-character string), style
[ip_addresses]    number, separator
[dates]           date, time, zone, separator
[paths]           segment, separator
[urls]            http, https, host, path, query_params_key, query_params_value, symbols
[pointers]        number, letter, separator, separator_token, x
[processes]       name, id, bracket
[key_value_pairs] key, separator
[json]            key, quote_token, curly_bracket, square_bracket, comma, colon
```

The singular `[pointer]` and misspelled `[[regexps]]` are not schema tables; as unknown input they may be ignored without error.

## Spec 16

A style is a TOML inline table such as `{ fg = "red", bold = true }`, never a bare string. Foreground colors are `default`, `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, and `bright_black` through `bright_white`. Basic colors map to SGR 30–37 and bright colors to 90–97. The tested modifiers are `bold`, `italic`, `underline`, and `dimmed`; true bold/italic/underline produce SGR prefixes `1`, `3`, and `4`. Compatibility output for a user style with only `fg="yellow", dimmed=true` is `ESC[33m...ESC[0m` (no added `2`).

Examples of field overrides: `[numbers] number={fg="red"}` makes `123` exactly `ESC[31m123ESC[0m`; `[dates] date={fg="green"}` makes each date component green while unspecified separators/times retain defaults; bright red/cyan/white render as 91/96/97.

## Spec 17

Themes may add repeatable keyword groups:

```toml
[[keywords]]
words = ["CRITICAL", "EMERGENCY"]
style = { fg = "red", bold = true }
```

`words` is required but may be an empty or arbitrarily long array. Matching is literal and uses ASCII word boundaries (letters, digits, and underscore are word bytes). Words sharing a style are normalized into lexicographic order, then use leftmost-first matching before the boundary check. A lexicographically earlier prefix can therefore shadow a later longer word even when the prefix itself is rejected for lacking a right boundary: with `words = ["word1", "word2", ..., "word20"]`, input `word1 word5 word10 word15 word20` styles only `word1` and `word5`. Reversing the input-array order does not change this normalized result. Multiple independently styled groups are supported. Built-in keyword precedence still applies: a configured `ERROR` does not replace built-in red `ERROR`. Custom theme keywords remain active under `--disable-builtin-keywords`.

Themes may add repeatable regex rules using the exact table name `[[regexes]]`:

```toml
[[regexes]]
regex = 'Started (.*)\.'
style = { fg = "red" }
```

`regex` is required. Compile all patterns and apply them in declaration order. A pattern with exactly one capture group styles that capture rather than surrounding syntax (`Started service.` becomes `Started ESC[31mserviceESC[0m.`). A pattern with no capture groups or with two or more capture groups styles the whole match. Thus `([A-Z]+)-([0-9]+)(x)?` applied to `ABC-123` produces the single span `ESC[35mABC-123ESC[0m`; it does not style the two participating captures separately. Regex matches take priority over built-in structural matches, so a whole-date custom match can replace component-by-component date styling.

## Spec 18

An explicitly named configuration file that is absent exits 1 and writes exactly `Error:   × could not find the TOML file\n\n`. A non-UTF-8 configuration exits 1 and reports `could not read the TOML file: stream did not contain valid UTF-8` and the same underlying cause. Malformed TOML, wrong field types, missing required `words`/`regex`, and unknown color variants exit 1 with a diagnostic beginning `Error:   × TOML parse error at line <n>, column <n>`, followed by the source line, a caret span, and the parser reason.

For example, `[numbers]\nnumber = "red"` reports “invalid type: string `"red"`, expected struct Style”; a missing keyword list reports “missing field `words`”; an unknown color lists all valid colors in the order in Spec 16. For an inline style's unknown `fg` variant, the reported column is the opening quote of the color value and the caret span covers that quoted value. This complete example is byte-exact:

```text
Error:   × TOML parse error at line 2, column 17
  │   |
  │ 2 | number = { fg = "orange" }
  │   |                 ^^^^^^^^
  │ unknown variant `orange`, expected one of `default`, `black`, `red`,
  │ `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `bright_black`,
  │ `bright_red`, `bright_green`, `bright_yellow`, `bright_blue`,
  │ `bright_magenta`, `bright_cyan`, `bright_white`
  │ 

```

An invalid regex exits 1. For the pattern `(unclosed group`, the complete stderr is:

```text
Error:   × Regex error: regex parse error:
  │     (unclosed group
  │     ^
  │ error: unclosed group
  ╰─▶ regex parse error:
          (unclosed group
          ^
      error: unclosed group
  help: Verify that your regex pattern is valid.

```

Other invalid patterns use this same two-part layout: first the three `│` lines containing the pattern, caret, and reason, then `╰─▶ regex parse error:`, an indented repetition of those three payload lines, the help line, and a final blank line. No input is processed after a configuration error.

Diagnostics use two leading spaces before every `│`/`╰` line and end in a blank line. These canonical cases are byte-exact apart from the displayed source when a different source is supplied:

```text
Error:   × TOML parse error at line 1, column 9
  │   |
  │ 1 | [numbers
  │   |         ^
  │ unclosed table, expected `]`
  │ 

```

```text
Error:   × TOML parse error at line 2, column 10
  │   |
  │ 2 | number = "red"
  │   |          ^^^^^
  │ invalid type: string "red", expected struct Style
  │ 

```

```text
Error:   × TOML parse error at line 1, column 1
  │   |
  │ 1 | [[regexes]]
  │   | ^^^^^^^^^^^
  │ missing field `regex`
  │ 

```

For `[[keywords]]`, the underline has twelve carets and the reason is “missing field `words`”. A `[keywords]` table where a sequence is required similarly reports `invalid type: map, expected a sequence` and underlines the ten-character table header.

## Spec 19

For a regular file without `--print`, write the fully highlighted content to a temporary file whose basename contains `tailspin.temp`, then run a pager. `--pager` has priority over `TAILSPIN_PAGER`, which has priority over the default `less` pager. The default pager must be `less`-compatible, preserve ANSI (`-R` behavior), remain interactive for short and empty files, display `(END)` at the bottom, and support ordinary less navigation including page down, `G` to end, `g` to beginning, and boundary-safe movement. In follow mode it must display appended content and allow the user to interrupt following while remaining in the pager.

A custom pager string is parsed with shell-word quoting into an executable and arguments; it is not itself evaluated as a shell expression. Shell syntax works when explicitly passed through `sh -c`. Replace every occurrence of literal `[FILE]` in every argument with the temporary path. The placeholder is optional (`echo hello` is valid), but the parsed command must contain at least an executable and one argument, so empty string and bare `cat` fail with `Error:   × Could not parse custom pager command`. Capture/forward pager stdout and stderr. A spawn failure reports `Could not run pager` and `No such file or directory`; a nonzero pager status is an executable error and reports `Pager exited with non-zero status: exit status: N`.

The temp file contains ANSI bytes unchanged and all content before the pager starts, so commands such as `head`, `tail`, `grep`, `sed`, `awk`, and `wc -l` observe the complete stream. `--print` always bypasses the pager even if `--pager` or its environment variable is set. Stdin likewise always bypasses it.

## Spec 20

The hidden flags `--generate-bash-completions`, `--generate-fish-completions`, and `--generate-zsh-completions` print deterministic shell completion scripts and exit 0 with empty stderr. Generation takes precedence over input/file validation and all ordinary flags. If multiple generation flags occur, priority is bash, then fish, then zsh. The scripts use the command name `tspin`, include hidden generation flags, and describe the options and choice lists from Specs 1–3.

The exact bash script is:

```bash
_tspin() {
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
                cmd="tspin"
                ;;
            *)
                ;;
        esac
    done

    case "${cmd}" in
        tspin)
            opts="-f -p -e -h -V --follow --print --config-path --exec --highlight --enable --disable --disable-builtin-keywords --pager --generate-bash-completions --generate-fish-completions --generate-zsh-completions --help --version [FILE]"
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                --config-path)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --exec)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -e)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --highlight)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --enable)
                    COMPREPLY=($(compgen -W "numbers urls pointers dates paths quotes key-value-pairs uuids ip-addresses processes json" -- "${cur}"))
                    return 0
                    ;;
                --disable)
                    COMPREPLY=($(compgen -W "numbers urls pointers dates paths quotes key-value-pairs uuids ip-addresses processes json" -- "${cur}"))
                    return 0
                    ;;
                --pager)
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
    complete -F _tspin -o nosort -o bashdefault -o default tspin
else
    complete -F _tspin -o bashdefault -o default tspin
fi
```

The exact fish script is:

```fish
complete -c tspin -l config-path -d 'Provide a custom path to a configuration file' -r -F
complete -c tspin -s e -l exec -d 'Run command and view the output in a pager' -r
complete -c tspin -l highlight -d 'Highlights in the form color:word1,word2' -r
complete -c tspin -l enable -d 'Enable specific highlighters' -r -f -a "numbers\t''
urls\t''
pointers\t''
dates\t''
paths\t''
quotes\t''
key-value-pairs\t''
uuids\t''
ip-addresses\t''
processes\t''
json\t''"
complete -c tspin -l disable -d 'Disable specific highlighters' -r -f -a "numbers\t''
urls\t''
pointers\t''
dates\t''
paths\t''
quotes\t''
key-value-pairs\t''
uuids\t''
ip-addresses\t''
processes\t''
json\t''"
complete -c tspin -l pager -d 'Override the default pager command used by tspin. (e.g. `--pager="ov -f [FILE]"`)' -r
complete -c tspin -s f -l follow -d 'Follow the contents of a file'
complete -c tspin -s p -l print -d 'Print the output to stdout'
complete -c tspin -l disable-builtin-keywords -d 'Disable the highlighting of all builtin keyword groups (booleans, nulls, log severities and common REST verbs)'
complete -c tspin -l generate-bash-completions -d 'Print bash completions to stdout'
complete -c tspin -l generate-fish-completions -d 'Print fish completions to stdout'
complete -c tspin -l generate-zsh-completions -d 'Print zsh completions to stdout'
complete -c tspin -s h -l help -d 'Print help (see more with \'--help\')'
complete -c tspin -s V -l version -d 'Print version'
```

The exact zsh script is:

```zsh
#compdef tspin

autoload -U is-at-least

_tspin() {
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
'--config-path=[Provide a custom path to a configuration file]:CONFIG_PATH:_files' \
'-e+[Run command and view the output in a pager]:EXEC:_default' \
'--exec=[Run command and view the output in a pager]:EXEC:_default' \
'*--highlight=[Highlights in the form color\:word1,word2]:COLOR_WORD:_default' \
'*--enable=[Enable specific highlighters]:ENABLED_HIGHLIGHTERS:(numbers urls pointers dates paths quotes key-value-pairs uuids ip-addresses processes json)' \
'*--disable=[Disable specific highlighters]:DISABLED_HIGHLIGHTERS:(numbers urls pointers dates paths quotes key-value-pairs uuids ip-addresses processes json)' \
'--pager=[Override the default pager command used by tspin. (e.g. \`--pager="ov -f \[FILE\]"\`)]:PAGER:_default' \
'-f[Follow the contents of a file]' \
'--follow[Follow the contents of a file]' \
'-p[Print the output to stdout]' \
'--print[Print the output to stdout]' \
'--disable-builtin-keywords[Disable the highlighting of all builtin keyword groups (booleans, nulls, log severities and common REST verbs)]' \
'--generate-bash-completions[Print bash completions to stdout]' \
'--generate-fish-completions[Print fish completions to stdout]' \
'--generate-zsh-completions[Print zsh completions to stdout]' \
'-h[Print help (see more with '\''--help'\'')]' \
'--help[Print help (see more with '\''--help'\'')]' \
'-V[Print version]' \
'--version[Print version]' \
'::FILE -- Filepath:_files' \
&& ret=0
}

(( $+functions[_tspin_commands] )) ||
_tspin_commands() {
    local commands; commands=()
    _describe -t commands 'tspin commands' commands "$@"
}

if [ "$funcstack[1]" = "_tspin" ]; then
    _tspin "$@"
else
    compdef _tspin tspin
fi
```

Each script ends with a newline.

## Spec 21

With `--follow`/`-f` on a regular file, emit the file's existing newline-terminated content and keep running, polling frequently enough that appended data normally appears within 300 ms. Emit every append in order, including rapid writes and multi-line batches, flush stdout promptly, apply the same structural/built-in/custom rules to initial and appended text, and handle an initially empty file. An initial partial line is not joined to a later append. Starting with `partial` and then appending ` completion\nnext\n` produces visible bytes `\npartial\n completion\nnext\n`: the leading newline is the empty/unterminated initial-read convention, the original partial text and the appended remainder become separate lines, and then `next` follows. SIGTERM may terminate with the signal status; do not turn it into a crash diagnostic. With stdin, follow is ignored and the finite stream exits normally.

`--exec <EXEC>` is an alternative interactive source intended to run a command and show its output through the pager only when no file or piped stdin has been selected. Nonempty piped stdin wins and the command is ignored: piping `piped stdin\n` with `--exec definitely-nonexistent-command` exits 0 with exactly `piped stdin\n` on stdout and empty stderr; the same is true when the exec value is a failing shell command, and also when `--print` is present. With no piped bytes, `--exec` combined with `--print` exits 0 with completely empty stdout and stderr regardless of whether the command is valid, prints multiple lines, or exits nonzero. Without `--print`, an invocation with no piped bytes must at least complete successfully with no executable-generated stderr in a noninteractive environment; in an interactive terminal its output may be shown by the same pager workflow.
