# Clarified specification for `executable`

The deliverable is a single executable file named exactly `executable`. It is a terminal program named `jplot`: it reads numeric values from JSON, keeps time-series data for requested fields, and renders one or more graphs using terminal inline-image protocols. All text is UTF-8. Escape sequences below use `ESC` for byte `0x1b` and `BEL` for byte `0x07`.

## Spec 1

`executable` must exist at the top level of the delivered directory and have operating-system execute permission. It must accept command-line arguments directly, without requiring another repository file, build step, interpreter command, configuration file, or network service other than an HTTP endpoint explicitly supplied with `-url`/`--url`.

The public invocation is:

```text
jplot [OPTIONS] FIELD_SPEC [FIELD_SPEC...]
```

Normal configuration/runtime failures exit with status 1. Command-line flag syntax or type errors exit with status 2. Help exits with status 0. Unless a later spec explicitly assigns output to stderr, user-facing runtime failures are written to stdout as `jplot:  ` followed by the error and a newline; stderr is empty.

## Spec 2

Both `-h` and `--help` request the same help behavior and must exit 0. Stdout must be exactly the three bytes `ESC[c`; stderr must be exactly the following text, including capitalization, punctuation, blank lines, tabs, and the final newline. Each visibly indented description line begins with four ASCII spaces followed by one tab character.

```text
Usage: jplot [OPTIONS] FIELD_SPEC [FIELD_SPEC...]:

OPTIONS:
  -interval duration
    	When url is provided, defines the interval between fetches. Note that counter fields are computed based on this interval. (default 1s)
  -rows int
    	Limits the height of the graph output.
  -steps int
    	Number of values to plot. (default 100)
  -url string
    	URL to fetch every second. Read JSON objects from stdin if not specified.

FIELD_SPEC: [<option>[,<option>...]:]path
  option:
    - counter: Computes the difference with the last value. The value must increase monotonically.
    - marker: When the value is none-zero, a vertical line is drawn.
  path:
    JSON field path (eg: field.sub-field).
```

The indentation inside the block is literal: in escaped notation, each option-description line starts with `    \t`, meaning four space bytes and then byte `0x09`. The output must contain that tab byte, not the two characters backslash and `t`. Thus the complete output obtained by concatenating captured stdout and then captured stderr starts with `ESC[cUsage: jplot...` and is 704 bytes long.

If a help flag occurs before a later unknown flag, help takes precedence: for example, `--help --definitely-unknown-flag` still prints help and exits 0. After the option terminator `--`, a token such as `--help` is a positional field specification and must not invoke help.

## Spec 3

The supported global options are `-url`/`--url` (string), `-interval`/`--interval` (duration), `-steps`/`--steps` (signed integer), and `-rows`/`--rows` (signed integer). Each accepts either a separate value or an equals value, such as `-steps 10`, `--steps 10`, `-steps=10`, or `--steps=10`.

Options are parsed only until the first positional field specification. Once the first positional is encountered, every later token is another positional, even if it begins with `-`; for example, `value --not-real` does not report an unknown option and instead reaches the ordinary graphics gate with both tokens treated as field specifications. Repeating an option before the first positional is accepted, with its last value taking effect. `--` also ends option parsing, so all following tokens are positional even when they begin with `-`.

An unknown option is a flag-parser failure: exit 2 and write to stderr an error line followed immediately by the exact help text from Spec 2 (without `ESC[c` in stderr). For example, `--invalid-flag` begins stderr with:

```text
flag provided but not defined: -invalid-flag
Usage: jplot [OPTIONS] FIELD_SPEC [FIELD_SPEC...]:
```

The unknown option is canonicalized to one leading hyphen in that error. A missing option value similarly begins `flag needs an argument: -url` (or `-steps`, `-rows`, or `-interval`) and is followed by the usage text.

Initial terminal detection occurs before these flag errors are returned. In an ordinary captured environment that is not recognized as iTerm2, every unknown-option, missing-value, invalid-duration, invalid-integer, and integer-overflow invocation above writes exactly `ESC[c` to stdout, then exits 2 with its diagnostic and help on stderr. With `TERM_PROGRAM=iTerm.app`, the same parser failures have empty stdout because that environment establishes graphics support without the device-attributes probe. A parser failure does not proceed to data input after this initial terminal detection.

## Spec 4

The default interval is one second. Duration parsing follows Go-style duration syntax: a sequence of decimal number/unit pairs using `ns`, `us`, `µs`, `ms`, `s`, `m`, or `h`, optionally signed and optionally compound. Values exercised as valid include `1ns`, `1us`, `100ms`, `500ms`, `1s`, `2m`, `1h`, `1h30m`, `24h`, `-1s`, `-5s`, `0s`, and the special bare value `0`. A nonzero bare number and unknown units are invalid.

An invalid duration exits 2. Its stderr begins exactly:

```text
invalid value "VALUE" for flag -interval: parse error
```

and continues with the exact help text from Spec 2. For example, this rule applies to `invalid`, `notaduration`, and `2x`.

The interval controls HTTP request frequency only. Graph display has its own approximately one-second refresh cadence.

## Spec 5

`steps` defaults to 100 and is the fixed history capacity per requested series. `rows` defaults to 0; zero means use the terminal's full row count. Signed decimal integers are accepted, including zero and negative values, at the flag-parsing stage. Large in-range positive values such as 999,999,999 for steps and rows are also syntactically valid. Values used in ordinary successful rendering have at least two steps and nonnegative rows; `steps=1` is accepted by flag parsing but has the render-time result specified in Spec 20.

Non-integers such as `abc`, `notanumber`, and `5.5` exit 2 with:

```text
invalid value "VALUE" for flag -steps: parse error
```

or the corresponding `-rows` line, followed by the exact help text. On a 64-bit target, `10000000000000000000` is out of range and the reason is exactly `value out of range` rather than `parse error`.

## Spec 6

Every positional argument describes one graph. Multiple positional arguments produce separate vertically stacked graphs. Within one positional argument, `+` separates fields that are plotted together in that graph. Examples are `a`, `a+b+c`, and separate arguments `a+b`, `c`, `d+e`.

Each plus-separated member has the grammar `[option[,option...]:]path`. The only option names are lowercase, case-sensitive `counter` and `marker`; either may appear alone, both may appear comma-separated in either order, and options are local to that one member. Thus all of these are valid:

```text
value
metrics.cpu.usage
counter:requests
marker:deploy
counter,marker:events
counter:a+marker:b+c
```

There is one legacy spelling: a member beginning exactly `marker:counter:` is treated as if it began `marker,counter:`. No colon is required in a bare path; a bare field named `counter` is just a normal path.

## Spec 7

Field paths are preserved exactly and are not restricted to ASCII identifiers. Dots express nested-object traversal. Components may contain letters, digits, underscores, and hyphens, and tested paths include Unicode, whitespace, very long names, numeric components, and dozens of nesting levels. Parsing must support at least 50 graph arguments and at least 20 plus-separated fields without an artificial small limit. Repeated field paths remain distinct requested series rather than being rejected.

The first colon in a member separates its option-list from its path. Any later colon belongs to the path, except for the exact legacy rewrite in Spec 6. Empty plus-separated path components and an empty path after a valid option are accepted syntactically; they may subsequently fail field extraction. An entirely empty positional argument is likewise a syntactically present graph specification.

## Spec 8

If a colon introduces an option list, every comma-separated option must be exactly `counter` or `marker`. Unknown, empty, uppercase, or whitespace-padded options are invalid. The first invalid option is reported; processing stops before reading input or querying terminal size. Exit 1, stderr empty, and stdout exactly follows this form:

```text
jplot:  Cannot parse spec:  invalid field option: OPTION
```

including the final newline. For `:field`, `OPTION` is empty, leaving two spaces between the final colon and newline. For `invalid1,invalid2:field`, the reported value is `invalid1`. `Counter:field` reports `Counter`; no case folding or whitespace trimming occurs.

## Spec 9

Startup validation occurs in this observable order after successful flag parsing:

1. Detect whether the terminal supports an applicable graphics protocol.
2. If graphics were recognized, reject the exact screen case described in Spec 10.
3. Require at least one positional field specification; otherwise print the help text to stderr and exit 1.
4. Parse all field specifications and report any option error.
5. Select and start the input source, then parse/extract its initial data.
6. Query terminal/window dimensions when a render is due (including a final render after finite stdin reaches EOF).

Consequently, in an ordinary captured non-graphics environment, even no arguments, malformed field syntax, valid piped JSON, or a URL fail at the graphics gate before those later concerns. Conversely, setting `TERM_PROGRAM=iTerm.app` allows later spec, data, and terminal-size errors to be observed.

## Spec 10

The iTerm2 environment is recognized only when `TERM_PROGRAM` is exactly `iTerm.app`, with that case and no added whitespace. Variants such as `iterm.app`, `ITERM.APP`, `iTerm2`, ` iTerm.app`, and `iTerm.app ` are not matches. Arbitrary programs such as `WezTerm`, `vscode`, and `RandomTerminal` are not automatically accepted.

When graphics support is not established, the program writes exactly this to stdout and exits 1 with empty stderr:

```text
ESC[cjplot:  iTerm2, Kitty, or DRCS Sixel graphics required
```

Here `ESC[c` is the literal three-byte device-attributes query/reset sequence. Ordinary `xterm`, `xterm-256color`, `dumb`, `linux`, empty `TERM`, unsupported `TERM_PROGRAM`, and noninteractive Kitty checks all end in this failure unless a live terminal actually answers a supported capability query.

After graphics support has been established through exact iTerm2 detection, `TERM=screen` is rejected with stdout exactly `jplot:  screen and tmux not supported\n` and exit 1. This comparison is exact: `screen-256color` does not select that diagnostic, and `TERM=tmux` is not rejected by this particular check.

## Spec 11

With `TERM_PROGRAM=iTerm.app`, a valid field spec, and piped/redirected stdin, lack of a usable terminal window produces stdout exactly:

```text
jplot:  Cannot get window size:  inappropriate ioctl for device
```

and exits 1. This happens only after finite valid input has been processed. No terminal-size diagnostic is printed when an earlier field-spec or data error occurs.

There are two explicit exceptions to Spec 1's empty-stderr default when stdin, stdout, and stderr are three separate pipes. After a nonempty URL has returned and its initial JSON body has been decoded successfully, scheduled display preparation occurs before the unusable stdout produces the window-size failure above; stderr is exactly `ESC[?25l` with no newline. This also applies when multiple `--url` options were given and the last URL is the successful one; invalid piped stdin remains ignored. Separately, if the stdin reader is still blocked waiting for its first record and SIGTERM starts cleanup, stderr is exactly `ESC[?25l` with no newline. Both paths exit 1 and have exactly the window-size diagnostic above on stdout.

If stdin itself is a TTY, no nonempty URL was supplied, and field specs are present, exit 1 with stdout `jplot:  neither --url nor stdin is provided\n`. An empty `-url ""` counts as no URL and therefore falls back to stdin selection. If graphics support is absent, the graphics error still takes precedence over this source-selection error.

## Spec 12

Without a nonempty URL, redirected stdin is a newline-delimited JSON source. Read and process records in order, one JSON document per scanned line, until EOF. Do not stop after the first valid line. A final record need not end in a newline. Normal JSON whitespace within a record, UTF-8 content, escaped characters, objects and lines within the scanner limit, and at least 1,000 records are handled. Duplicate object keys follow ordinary JSON-decoder behavior, so the last value is used.

The stdin scanner has a 64 KiB token limit. For an LF-terminated record, 65,535 bytes before the LF are accepted, while 65,536 bytes before the LF fail before JSON decoding. The roughly 200 KiB record produced by a `padding` string of 200,000 characters therefore exits 1, leaves stderr empty, and writes exactly:

```text
jplot:  Data source error:  input error: bufio.Scanner: token too long
```

Each line is strict JSON; comments, single-quoted strings, unquoted keys, trailing commas, and incomplete documents are invalid. The first bad record terminates processing rather than being skipped. Empty input reaches EOF successfully with no points and proceeds to the render/window-size stage. Blank physical lines are not JSON records and may terminate with an input error.

## Spec 13

For every JSON record, extract every requested field. A dotted path traverses nested JSON objects component by component. A missing top-level or nested component is an error. Attempting to traverse a primitive or a non-object JSON root is also an error. The extracted leaf must be a JSON number; integers, decimal values, negatives, zero, scientific notation, and finite values across the normal IEEE-754 range are accepted. Strings, booleans, null, objects, and arrays are not coerced to numbers.

Data errors exit 1, go to stdout, and have an empty stderr. Their forms are:

```text
jplot:  Data source error:  input error: JSON_DECODER_ERROR
jplot:  Data source error:  cannot get PATH: DETAIL
jplot:  Data source error:  invalid type PATH: TYPE
```

Required examples include `unexpected end of JSON input` for an incomplete record; `PATH does not exist.` for a missing field; and type names including `string` and `bool`. When traversal cannot continue because the current JSON value is not an object, `COMPONENT` is the component the traversal was about to look up, not the earlier component holding the primitive, and the detail includes the implementation suffix ` map[]`. Consequently, `{"outer":2}` with path `outer.value` reports exactly `value is not an object. map[]`, and primitive root `12` with path `value` reports that same detail. All fields in all graph specifications are validated for every record, so a missing field in any graph fails the whole invocation.

## Spec 14

With a nonempty `-url`/`--url`, ignore stdin and use HTTP GET. Make one request immediately and then another request each configured interval. Continue polling and processing changed responses until an error or shutdown; do not cache the first response. Timing must be close enough that a 300 ms interval produces at least three requests in 1.2 seconds, a 500 ms interval produces two to four requests in 1.3 seconds, and a 100 ms interval produces at least five requests in 0.8 seconds.

Read each complete response body and parse it as one JSON document. HTTP status alone is not treated as the data error: a 404/500 body is still read and JSON-decoded, so an HTML body fails with a JSON decoder error. Response bodies do not need a trailing newline. Nested paths and all field options work with HTTP data just as with stdin.

The HTTP polling interval and the display refresh are independent. In a live iTerm2-like PTY, valid HTTP operation remains running rather than exiting after the first fetch.

## Spec 15

HTTP and response errors use the same stdout-only fatal prefix and exit 1. The following exact forms are required (the requested URL is quoted):

```text
jplot:  Data source error:  input error: Get "not-a-url": unsupported protocol scheme ""
jplot:  Data source error:  input error: Get "http://127.0.0.1:9999/data": dial tcp 127.0.0.1:9999: connect: connection refused
jplot:  Data source error:  input error: unexpected end of JSON input
jplot:  Data source error:  input error: invalid character '<' looking for beginning of value
jplot:  Data source error:  input error: invalid character 'i' looking for beginning of object key string
jplot:  Data source error:  input error: unexpected EOF
jplot:  Data source error:  invalid type value: string
```

A DNS lookup failure must retain the host, resolver address, and `no such host` in the conventional form `Get "URL": dial tcp: lookup HOST on ADDRESS:53: no such host`. A body shorter than its declared Content-Length, and a broken/incomplete chunked body, both report `unexpected EOF`. Do not silently retry a request whose network read, JSON decoding, field lookup, or type validation has failed.

## Spec 16

Each requested non-marker numeric field owns an independent fixed-length history whose capacity is `steps`. Histories begin zero-filled and behave as sliding windows: each new reading appends on the right and drops the oldest value. Duplicate paths in different graph/member positions remain independently addressable series.

A normal field stores its numeric readings. A `counter` field is accepted for integer and floating-point readings and represents change between readings, as stated in help; its first usable sample has no prior delta and must not cause an error. Non-increasing values, resets, zero, and negative readings must be handled without crashing or producing a type/data-source failure. A `marker` field accepts numeric zero, positive, and negative values; it is marker metadata rather than an ordinary plotted curve. Combining `counter` and `marker` on one member is valid.

## Spec 17

Rendering refreshes on an approximately one-second display ticker while input collection continues. When finite stdin reaches EOF before the first display tick, attempt one final render rather than silently producing nothing. Once terminal setup succeeds and every graph is renderable, a continuing HTTP source generates repeated render frames.

When all three standard streams share the graphics-capable PTY, the first display preparation emits standard terminal controls including hide-cursor `ESC[?25l` and save-cursor-position `ESC[s`, reserves the requested output rows (or all terminal rows for `rows=0`), and restores the cursor position around completed frames. A controlling PTY attached only to stdin and stderr is insufficient: if stdout is a separate pipe, the window-size operation fails against stdout before any controls or PNG are emitted. Such a split-stream invocation exits 1, leaves stderr empty, and writes exactly `jplot:  Cannot get window size:  inappropriate ioctl for device\n` to stdout. This applies to continuing HTTP input and to the final-render path for finite stdin.

If an iTerm2 PTY does not answer the required cell-size query, the program waits rather than timing out with a window-size diagnostic. HTTP polling continues during that wait. In the exercised `--interval=1s` invocation, after eight seconds the process is still alive, exactly eight requests have completed, and the output ends with `ESC]1337;ReportCellSizeBEL` with no `Cannot get window size` text.

## Spec 18

For iTerm2 rendering, obtain the terminal character grid with the TTY window-size operation and query cell dimensions by writing:

```text
ESC]1337;ReportCellSizeBEL
```

Accept a response of the form `ESC]1337;ReportCellSize=H;WESC\`, where `H` and `W` are decimal cell height and width in pixels. Compute image width as terminal columns times cell width. If `rows > 0`, image height is that many rows times cell height; if `rows == 0`, use the terminal's full row count. Dimensions must be positive; a 24-by-80 terminal with a `20.0;10.0` response therefore renders 800 pixels wide and, at full height, 480 pixels high.

Encode each complete dashboard frame as a valid PNG, then base64-encode it and write an iTerm2 inline-image OSC sequence to stdout in this form:

```text
ESC]1337;File=preserveAspectRatio=1;width=WIDTHpx;height=HEIGHTpx;inline=1:BASE64_PNGBEL
```

The payload must decode to a substantive PNG, not a placeholder. Rendering a normal 80-column PTY must produce well over 100 bytes of output and must not print a window-size error when the query is answered.

## Spec 19

In an `xterm-kitty` PTY, startup emits the Kitty graphics query `ESC_Gi=1,a=q,t=d,f=24ESC\`. The exercised response `ESC_Gi=1;OKESC\` does not complete capability detection: the program next emits `ESC[c` and remains in terminal detection. During four seconds with `--interval=500ms`, the process remains alive but makes zero HTTP requests; captured output is exactly the Kitty query followed by `ESC[c`. It does not emit `ESC[14t`, a Kitty PNG transmission, or an image-deletion command in that interval.

## Spec 20

One PNG dashboard contains all positional graph specifications stacked vertically within the selected total image height. Plus-separated fields are series in the same chart. Marker members do not become ordinary value curves; nonzero marker samples create vertical event marks. Graph construction supports at least five independently colored series and multiple graphs, subject to the per-graph non-marker requirement below.

Autoscaling handles varying, negative, all-zero, and constant y-value series when the history contains at least two slots. In particular, when a chart's numeric minimum equals its maximum, use a nonzero manual range (the exercised behavior expands it to `minimum - 0.05` through `maximum + 0.05`) so y-axis rendering does not divide by zero or create NaN dimensions. A one-slot history still has zero x-range: `--steps=1` reaches the answered iTerm2 cell-size query, then exits 1 without a PNG and reports `jplot:  cannot render graph: zero x-range delta; there needs to be at least (2) values\n`.

Every individual graph must contain at least one non-marker series. Marker members may accompany an ordinary or counter series, including a flat series, but a marker-only graph is rejected even when other graphs in the dashboard have ordinary series. After the cell-size query is answered, it exits 1 without a PNG and reports `jplot:  cannot render graph: please provide at least one series\n`.

## Spec 21

Handle both SIGINT and SIGTERM while polling/rendering. On either signal, close the active input source and stop future HTTP fetches promptly; after a short allowance for requests already in flight, request counts must stop increasing. In the captured iTerm2 HTTP invocation, sending SIGTERM after 0.3 seconds initiates cleanup and final display preparation; because stdout is not a TTY, the program exits 1 with stdout exactly `jplot:  Cannot get window size:  inappropriate ioctl for device\n` and empty stderr. A clean status-0 exit is not permitted for that invocation. It must not terminate as an unhandled signal crash or deadlock source shutdown. A stdin source must also be safe to close during cleanup. Normal stdin EOF must complete promptly rather than wait forever for another record.

For the distinct all-pipe case where stdin is still blocked before its first record, SIGTERM must complete cleanup promptly with status 1, stdout exactly `jplot:  Cannot get window size:  inappropriate ioctl for device\n`, and stderr exactly `ESC[?25l`, as specified in Spec 11.
