# Rhit executable behavioral specification

The required artifact is a Unix-runnable file named exactly `executable`. It implements the `rhit` 2.0.4 command described below. All text is UTF-8. Unless a rule says otherwise, successful commands exit 0, command-line parsing errors exit 2, runtime/data errors exit 1, normal results go to stdout, and diagnostics go to stderr.

## Spec 1

`executable` is a single-command nginx access-log analyzer. Its invocation is `executable [options] [FILES]`; it has no subcommand grammar. Every non-option argument is a file or directory path. Options may precede or follow paths, multiple paths are accepted, and `--` ends option parsing (so a later option-looking token is a path). The file must have its executable permission set and must finish ordinary test inputs in a few seconds.

## Spec 2

Recognize this option surface (only `--help`, `--version`, `--color`, `--no-name-check`, and `--silent-load` lack the listed short form):

| short | long | value / meaning |
|---|---|---|
| | `--help` | print help and stop |
| | `--version` | print version and stop |
| | `--color` | `auto`, `yes`, or `no`; default `auto` |
| `-k` | `--key` | sorting/histogram key `hits` or `bytes`; default `hits` |
| `-l` | `--length` | unsigned decimal detail level; default 1 |
| `-f` | `--fields` | field expression |
| `-c` | `--changes` | enable trends/change tables |
| `-d` | `--date` | date or date-time filter |
| `-i` | `--ip` | remote-address string expression |
| `-m` | `--method` | HTTP-method filter |
| `-p` | `--path` | path string expression |
| `-r` | `--referer` | referer string expression (the spelling is intentionally `referer`) |
| `-s` | `--status` | status filter |
| `-t` | `--time` | time-of-day filter |
| `-a` | `--all` | include resource paths in path tables |
| | `--no-name-check` | disable directory filename filtering |
| `-o` | `--output` | `tables`, `csv`, `json`, or `raw`; default `tables` |
| | `--silent-load` | suppress loading/progress output |

Both `--option value` and `--option=value` work. Lowercase output shorthands are `t` and `tbl` for tables, `c` for CSV, `j` for JSON, and `r` for raw. `-k b`/`bytes` selects bytes and `-k h`/`hits` selects hits. Short flags may be clustered according to clap-style parsing: `-cl 1` means `-c -l 1`, while `-lc 1` makes `c` the attached value of `-l` and is therefore an error. The key and method options may not be supplied more than once. Repeated `-k`/`--key` produces exit 2 and a diagnostic containing `the argument '--key <KEY>' cannot be used multiple times`; repeated `-m`/`--method` does the same with the exact phrase `the argument '--method <METHOD>' cannot be used multiple times`.

## Spec 3

`--version` writes exactly `rhit 2.0.4\n` to stdout, nothing to stderr, and exits 0. `--help` takes precedence over other options such as `--output json`, writes the width- and environment-sensitive help display defined in Spec 24, writes nothing to stderr, and exits 0. `-h` is not a help alias: it exits 2, leaves stdout empty, and its ANSI-capable stderr contains `unexpected argument '-h'` and `Usage:`. Help is deliberately styled even when `--color no` is supplied.

## Spec 4

Unknown options exit 2, leave stdout empty, and identify the exact option in stderr with `error: unexpected argument '<option>' found`, followed by a tip and a `Usage:` line. When no known option is offered as similar, the tip is `tip: to pass '<option>' as a value, use '-- <option>'`; this is the behavior for `-z` and `--quux`, whose usage line is `Usage: executable [OPTIONS] [FILES]...`. When a known option is offered as similar, that suggestion replaces the pass-as-value tip and the usage line is specialized to the suggested option. Specifically, `--wat` has stderr exactly `error: unexpected argument '--wat' found\n\n  tip: a similar argument exists: '--path'\n\nUsage: executable --path <PATH> [FILES]...\n`. Missing option values exit 2 and say `a value is required for '--color <color>'`, `a value is required for '--output <OUTPUT>'`, `a value is required for '--key <KEY>'`, or the analogous flag/value name. Invalid `--color` reports the invalid value and possible values `auto`, `yes`, `no`. Invalid key text reports `error: invalid value 'VALUE' for '--key <KEY>': unrecognized key "VALUE"`. Invalid output text is a special case with no usage suffix: for `--output invalid`, stderr is exactly `error: invalid value 'invalid' for '--output <OUTPUT>': unrecognized output "invalid"\n`. Nonnegative invalid length text, and a negative value attached with `=`, report against `--length <LENGTH>` with `invalid digit found in string`; `--length=-1` has that diagnostic. In contrast, the two-token form `--length -1` treats `-1` as a new option-like argument and reports `error: unexpected argument '-1' found`, with the tip `tip: to pass '-1' as a value, use '-- -1'`. An invalid field expression `xyz` reports `error: invalid value 'xyz' for '--fields <FIELDS>': unrecognized field start 'x'`. These parse errors end with no analysis.

## Spec 5

Each positional path may be a regular file, symlink to a file, or directory. With no paths, use `/var/log/nginx`; if absent, stderr must contain, in this order, `No nginx log found at default location, do you have nginx set up?`, `If necessary, provide the path to the log file(s) as argument.`, and `Error: PathNotFound("/var/log/nginx")`. An explicitly missing path `P` produces exactly `Error: PathNotFound("P")\n` on stderr and exit 1.

Recurse through directories. Normally consider only files whose basename contains the standard access-log name `access.log` (including rotated/compressed forms such as `access.log.1`, `good_access.log`, and `access.log.gz`); do not read unrelated names such as `other.txt` or `custom.log`. `--no-name-check` considers all regular files encountered. An explicitly named regular file bypasses the name check. Aggregate all accepted files and all repeated path arguments without deduplicating them.

## Spec 6

Plain files are UTF-8 text. Files with a `.gz` suffix are gzip-decoded. Invalid UTF-8 is fatal with `Error: Io(Error { kind: InvalidData, message: "stream did not contain valid UTF-8" })`. A sufficiently long nongzip payload is fatal with `Error: Io(Custom { kind: InvalidInput, error: "invalid gzip header" })`, but the eight-byte payload `not gzip` ends while the decoder is still reading its header and produces exactly `Error: Io(Kind(UnexpectedEof))\n`. Follow symlinks.

To decide whether a candidate is a log, inspect at most its first three physical lines for a parseable log timestamp/entry. One or two initial short, logrotate, or malformed lines may be skipped; if the first valid entry would be the fourth line, reject that file. Once a file is accepted, skip malformed/non-log lines anywhere in it and continue processing valid lines. Empty files and rejected candidates are ignored when other valid files exist. If no usable log file/entry remains, exit 1 with exactly `Error: NoLogFileFound\n`. A corrupted selected gzip remains fatal rather than being silently ignored.

Without `--silent-load`, loading progress is written only to stderr. It includes ANSI clear-line `ESC[2K`, the word `read`, and after completion `I've read 1 file` or `I've read N files`. With `--silent-load`, stderr is empty on success and stdout is byte-for-byte the same final result it would otherwise have been.

## Spec 7

Parse nginx combined/common access lines with this usual logical form:

`REMOTE - - [TIMESTAMP] "REQUEST" STATUS BYTES "REFERER" "USER_AGENT" [ignored trailing quoted fields]`

The parser is more permissive before the timestamp than that usual form suggests. `REMOTE` is the text before the first ASCII space and is preserved as arbitrary text; it may be IPv4, IPv6, `-`, or any other token. The parser then scans forward to the first bracketed timestamp and ignores all intervening text, rather than requiring that text to be exactly `- -`. For example, this accepted line:

```text
2021-01-22T10:00:00.000Z 192.168.1.1 - - [22/Jan/2021:10:00:00 +0000] "GET /test HTTP/1.1" 200 100 "-" "Mozilla"
```

has remote address `2021-01-22T10:00:00.000Z` and date/time `2021/01/22,10:00:00`; the `192.168.1.1 - -` text is ignored. The request quotes remain required, but the referer position is found by scanning quoted fields rather than by requiring a quote immediately after `BYTES`. In particular, `192.0.2.1 - - [22/Jan/2021:01:47:05 +0000] "GET / HTTP/1.1" 200 1 - "a"` is accepted and exports referer `a`: the unquoted `-` is skipped and the next quoted field is taken as the referer. `STATUS` is an unsigned 16-bit decimal and is retained for export as a decimal string. `BYTES` is an unsigned 64-bit decimal. Missing required fields, bad request delimiters, nonnumeric/negative/overflowing status or bytes, or invalid date/time components make that line malformed. Zero bytes are valid. Extra fields after user agent are allowed.

Split the quoted request on every literal ASCII space. If it has at least two tokens, the first token determines the method and the second token alone is the target; all later tokens, including the conventional HTTP version, are ignored. Consequently, `"GET /path/with spaces HTTP/1.1"` has method `GET` and path `/path/with`, and remains a normal record. If the request has only one token, its method category is `none` and that token itself is the target without any added slash: `"broken"` exports method `none` and path `broken`. Recognize at least `GET`, `POST`, `HEAD`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`, `CONNECT`, and `TRACE` exactly and case-sensitively. Any other first token in a request having at least two tokens is represented as `other`. Preserve escaped byte-looking text such as `\x00` as characters rather than interpreting it.

## Spec 8

Normalize a parsed target to the path before the first `?`; query parameters never appear in CSV/JSON path values, path filtering, or path aggregation. Preserve all other path and referer Unicode and punctuation, including percent encoding, commas, semicolons, spaces inside a quoted referer, backslashes, very long values, `/`, and the literal referer `-`. Raw mode is the sole exception: it outputs the original physical line, including its original query string and spelling.

Records retain encounter order: command-line file order, then the traversal order used to discover files, then line order within each file. CSV, JSON, and raw exports must not reorder records. Tables group records irrespective of input order.

## Spec 9

Accept timestamps independently per line in both forms:

- common log form `DD/Mon/YYYY:HH:MM:SS` with optional ignored text after the seconds, and case-sensitive English `Jan` through `Dec`;
- ISO form `YYYY-MM-DDTHH:MM:SS+HHMM`, `YYYY-MM-DDTHH:MM:SS-HH:MM`, and equivalent numeric timezone spelling used by nginx.

Timezone text is ignored rather than validated or used to convert the wall-clock date/time. In common-log timestamps, `22/Jan/2021:01:47:05 BAD`, `22/Jan/2021:01:47:05 `, and `22/Jan/2021:01:47:05` are all accepted and export the same date and time as a numeric-zone spelling. Export date as zero-padded `YYYY/MM/DD` and time as `HH:MM:SS`. Months must be 1–12, days 1–31, hours 0–23, minutes/seconds 0–59; leap-day input such as 2020-02-29 is accepted. An invalid date/time component makes only that log line malformed, so an all-invalid file ultimately yields `NoLogFileFound` rather than a component-specific error.

## Spec 10

`--date` accepts a precise calendar selector, a unary comparison/negation, or an inclusive range. Component separators may be `/`, spaces, or the date/time `T`/space style demonstrated here:

- `2021`, `2021/02`, `2021/02/15` select the entire year, month, or day;
- `2021/02/15 11`, `2021/02/15 11:30`, `2021/02/15 11:30:45` select exactly 11:00:00, 11:30:00, or 11:30:45;
- space-token forms `2021 1 22 11`, `2021 1 22 11 30`, and `2021 1 22 11 30 45` have the same exact semantics;
- `>X` and `<X` are strict; for a date-only X they exclude the whole boundary date, while for a date-time they compare to the exact second;
- `!X` supports a full calendar date and excludes that day, or supports a full date-time and excludes that exact instant. The reduced-precision forms `!2021` and `!2021/02` are not expanded to a year/month exclusion: both exit 1 with `Error: DateTime(IntExpected(ParseIntError { kind: PosOverflow }))`;
- `A-B` (spaces around the range hyphen are optional) is inclusive. Date-only endpoints cover their whole endpoint days; date-time endpoints include both exact seconds. Ranges work across months, years, and midnight and may be a single day.

If all loaded records have one unique year, a missing year may be inferred: `02/15` means that year's February 15. If they also have one unique month, `15` means that year/month/day. Prefix whitespace after `>`, `<`, or `!` is allowed. Invalid filter month/day errors are exact: `Error: DateTime(InvalidMonth(N))` or `Error: DateTime(InvalidDay(N))`. The text `invalid` yields `Error: DateTime(IntExpected(ParseIntError { kind: Empty }))`. These are runtime exit-1 errors.

## Spec 11

`--time` compares the parsed local time of day. It accepts strict `>T`/`<T` and inclusive `A-B`, where each T may be `HH:MM` or `HH:MM:SS`; omitted seconds mean `:00`. A bare time without a comparison operator or range is not an exact selector: both `11:30` and `11:30:00` exit 1 with exactly `Error: TimeFilter(InvalidFormat)\n`. A normal range includes both boundaries. If A is later than B, it wraps across midnight and matches `time >= A OR time <= B`; thus `22:00-04:00` includes 22:15, 23:45, 00:30, 01:15, 03:45, and 04:00. Date and time filters are ANDed. Invalid general syntax yields `Error: TimeFilter(InvalidFormat)`. Because a bare value never reaches component parsing, bare `25:00` and `12:60` also produce that generic error; comparator forms such as `>25:00` and `>12:60` instead produce `Error: TimeFilter(TimeParse(InvalidHour(25)))` and `Error: TimeFilter(TimeParse(InvalidMinute(60)))`.

## Spec 12

`--path`, `--referer`, and `--ip` use the same case-sensitive regular-expression expression language. A bare atom is an unanchored Rust-regex-style search, so `blog` means “contains blog”, while `^/login$`, `.`, `*`, `+`, `\\d`, `\\b`, grouping inside an atom, and character classes have regex meaning. IP input is not validated as an address; exact text, prefixes, IPv6 fragments, regex, and `-` are all legitimate patterns.

There are two expression syntaxes:

- if commas occur, split on commas, trim surrounding whitespace from every atom, and AND all atoms; a leading `!` negates its atom. Thus `api, page` uses regex atoms `api` and `page`, and matches both `api page` and `api_page`. Empty comma tokens are errors;
- otherwise, when separated as expression tokens, prefix `!` is NOT, `&` is AND, `|` is OR, and whitespace-delimited `(` `)` group expressions. NOT binds tightest; `&` and `|` have equal precedence and associate from left to right. Thus `red | blue & apple` is grouped as `( red | blue ) & apple`, whereas `red | ( blue & apple )` uses the explicit grouping. Repeated NOT works. Parentheses attached to an atom, such as `(/api)`, remain regex syntax rather than boolean grouping.

Support deep nesting and long OR chains. Different option types are ANDed. An empty pattern is accepted syntactically but has no expression result and therefore rejects every candidate. Each attempted match also writes `unexpected lack of expr result on "VALUE"\n` to stdout, with `VALUE` rendered as a debug-quoted normalized field value. Thus an eight-record JSON invocation with `--path ''` prints eight such lines in encounter order and then the empty JSON array from Spec 17. Preserve the parser's unusual unmatched-opening behavior: `( /api` is accepted and behaves like the bare `/api` atom (the unmatched leading opener is ignored), rather than producing an invalid-regex or invalid-pattern error. Invalid regex errors contain `Error: StrFilter(InvalidRegex(Syntax(`, a tilde-delimited `regex parse error:` block, the offending expression and caret, and the regex engine's `error:` reason. An unclosed `[` reason is exactly `error: unclosed character class`; the malformed named group `(?P<invalid)` uses exactly `error: invalid capture group character`. Expression errors use exactly `Error: StrFilter(InvalidPattern("PATTERN", "REASON"))\n`, where tested reasons include `empty token`, `unexpected '&'`, `unexpected '|'`, `unexpected opening parenthesis`, and `unexpected closing parenthesis`. The closing-parenthesis case has an additional stdout side effect: `--path 'a )'` dumps a debug representation beginning `expr: BeTree {` to stdout before writing `Error: StrFilter(InvalidPattern("a )", "unexpected closing parenthesis"))\n` to stderr and exiting 1.

## Spec 13

`--method X` compares the method category case-sensitively; leading `!` negates. The special values `none` and `other` select those parsed categories. An unrecognized filter word such as lowercase `get` selects category `other`, rather than case-folding to `GET`. At most one method option is accepted.

`--status` is a comma-separated include/exclude language. An item is a decimal code, an inclusive numeric range such as `300-399`, or a class `1xx` through `5xx`; prefix `!` excludes that item and surrounding item whitespace is allowed. Positive items are ORed; if there are no positives the initial set is all statuses. Every negative is a veto. Thus `2xx,405-512` is a union, `4xx,!404` is 400–499 except 404, `200,!200` matches nothing, and overlapping items never duplicate a record. A reverse range such as `200-100` matches nothing. A syntactically valid absent code such as 999 simply gives an empty result. Non-numeric text produces `Error: StatusFilter(ParseInt(ParseIntError { kind: InvalidDigit }))` and exit 1.

## Spec 14

Apply all supplied filter kinds with logical AND to every output mode. An empty filtered result is successful. In tables mode, first print the unfiltered summary, then one diagnostic block per active filter, using its original pattern. For example status 200 on a 33,468-hit/405M input begins:

```text
33,468 hits and 405M from 2021/01/22 to 2021/01/22
Filtering by status on pattern 200 removed 20.87% 
of total lines
 ==> hits: 26,484, bytes sent: 393M
```

Use analogous phrases `Filtering by remote address on pattern ...`, `Filtering by method on pattern ...`, `Filtering by path on pattern ...`, `Filtering by referer on pattern ...`, date, and time. Every filter's removed percentage uses the original unfiltered record count as its denominator, even though a later filter is evaluated only for records that passed earlier filters; print it with two decimals. For example, if an IP filter leaves three records out of 33,468 and a subsequent referer filter removes two of those three, the second diagnostic says `removed 0.01% of total lines`, not `66.67%`. Print all filter prose first and then exactly one resulting hit/byte line for the final combined result; do not print an intermediate `==> hits:` line after each filter. A filter-description line that fits the output width has no trailing space: the complete line `Filtering by date on pattern 2024/01/05-2024/01/08 removed 50.00% of total lines` ends immediately after `lines`. CSV/JSON/raw modes emit only their data, never summaries or filter diagnostics.

## Spec 15

Raw output emits each accepted and filtered record's original input bytes/text plus its original line terminator. It adds no header, prefix, sorting, normalization, extra whitespace, or blank line. A single newline-terminated input record produces exactly one trailing newline, not two. Invalid/non-log lines are not emitted. Filtering is evaluated on parsed normalized fields even though the retained original line is printed.

## Spec 16

CSV always begins with exactly:

```text
date,time,remote address,method,path,status,bytes sent,referer
```

and includes that header even for zero matches. Each record is one newline-terminated row in encounter order. Columns are exactly the eight named fields in that order. Date/time are normalized as above, remote address and method are preserved/category formatted, status and bytes are bare decimal values, and path and referer are always double-quoted. Apply standard CSV quote doubling inside quoted values. Do not pad fields or place spaces around commas. A record example is:

```text
2021/01/22,01:47:05,192.168.1.1,GET,"/test",200,100,"-"
```

## Spec 17

JSON is a pretty-printed flat array in encounter order. Empty output is exactly two lines, `[` then `]`, i.e. the byte string `[\n]\n`. Each object has exactly these keys in exactly this order and types: string `date`, string `time`, string `remote_addr`, string `method`, string normalized `path`, string `status`, integer `bytes_sent`, string `referer`. Use two-space indentation, one key per line, `: ` after keys, commas after all nonfinal properties/objects, and a final newline. Unicode is emitted directly. The serializer does not double input backslashes: for a physical target containing the literal characters `GET /literal\x00tail HTTP/1.1`, the path line contains the single-backslash bytes `"path": "/literal\x00tail"`. Consequently that particular output is not valid JSON (`\x` is not a JSON escape), despite the JSON-shaped format. Exact ordinary singleton shape:

```json
[
  {
    "date": "2021/01/22",
    "time": "01:47:05",
    "remote_addr": "192.168.1.1",
    "method": "GET",
    "path": "/test",
    "status": "200",
    "bytes_sent": 100,
    "referer": "-"
  }
]
```

## Spec 18

Tables always start with `<H> hits and <B> from YYYY/MM/DD to YYYY/MM/DD`, where H is the unfiltered count with comma grouping and B is the unfiltered total bytes in compact form. Default fields, in order, are `date,status,ref,path`. The all-fields order is `date,time,method,status,ip,ref,path`. Full field names (including plurals where natural) and initials `d,t,m,s,i,r,p` are accepted; `a`/`all` means all fields.

An expression with no leading algebraic sign replaces the defaults and preserves its stated order (`path,method` prints path then method). Comma and `+` can separate fields. A leading `+` starts from defaults and appends absent fields; `-` removes. Algebra may continue, e.g. `+ip-path`, `+ip+time+method`, `all-ip-time`, `a-p`, `all+date`. Adding an already selected field removes its earlier occurrence and appends it, so `+p` moves path to the end. Empty `--fields=` is valid and prints only the summary line and final newline, with no table glyphs.

## Spec 19

For each selected categorical field, group by exact displayed value and compute hit count, sum of bytes, and percentage `100 * group_hits / all currently filtered hits`. Sort descending on the chosen key (`hits` by default, aggregate bytes for `--key bytes`). Ties may be in hash/encounter order. Status rows show all distinct numeric statuses; method values include standard names plus `none` and `other`; IP, referer, and path retain exact Unicode. For the referer table only, omit the direct-traffic sentinel `-` entirely. The sentinel is still retained in exports and is filterable. Although the option, export key, and filter spelling is `referer`, the categorical table's value-column header is exactly `referrer`, and its section caption is `referrers`. If all records have referer `-`, its exact section is:

```text
0 referrers. 
┌───┬────────┬────┬───┬─────┐
│ # │referrer│hits│ % │bytes│
├───┼────────┼────┼───┼─────┤
└───┴────────┴────┴───┴─────┘
```

Tables use Unicode box drawing `┌┐└┘├┤┬┴┼│─`, never ASCII `+`. Row numbers begin at 1. Categorical header alignment is: centered `#`, left-aligned value-column label, then centered `hits`, `%`, and `bytes`; body text is left aligned and body numbers are right aligned. The IP value-column header is exactly `IP address` in both ordinary and trend tables; for example its trend header begins `│ # │IP address│hits│bytes│`. Thus sufficiently wide status and referer headers contain `│ # │status│ hits │  %  │bytes│` and `│ # │referrer`. Percentage is one decimal plus `%`, hit counts use comma grouping, and zero bytes print `0`. Long cell content wraps into continuation rows with an empty row-number cell and blank numeric cells. Categorical table lines and their prose captions use up to 80 visible terminal columns; use natural content width when it is narrower. Width and wrapping use terminal display columns, not UTF-8 byte counts, so wide Unicode is measured by its displayed width. In particular, the value `https://café.example.org/日本語` fits contiguously in the natural-width value column; do not split `日本語` merely by counting its UTF-8 bytes. Give the variable text-value column the remaining width after borders and the compact numeric columns, and allow even numeric/header cells to wrap if needed. Centering with an odd number of spare columns puts the smaller share on the left and the larger share on the right. There is no blank line between the summary, captions, or tables. Section names are exactly `N HTTP status codes.`, `N methods.`, `N remote IP addresses.`, `N referrers.`, and `N paths (excluding resources like images, css, etc.).`; append ` K most frequent:` when truncating. Singular grammar is intentionally not corrected (`1 hits`, `1 HTTP status codes`, `1 paths`).

## Spec 20

Human-readable byte/key labels use SI powers (K=1,000, M=1,000,000, G=1,000,000,000), rounded for display: values below 10,000 remain plain integers; otherwise use one decimal when the scaled value is below 10 and an integer when it is 10 or more (examples: 9.1M, 11K, 405M, 3.2G). Histogram maxima use similarly compact labels (`33K`, `405M`).

The date table has columns `date`, `hits`, `bytes`, and a 20-character horizontal bar scaled to the largest selected-key daily value. It has one row per encountered date run and does not synthesize absent calendar dates: input containing records only on 2024/01/01 and 2024/01/03 prints those two rows and omits 2024/01/02. Its first three headers are centered; date body cells are left aligned and hit/byte body cells are right aligned. For example, a one-day 6-hit table's header is exactly `│   date   │hits│bytes│0                  6│`, while a 33,468-hit table uses `│   date   │ hits │bytes│0                33K│` because the hits column is wider.

The time table always has 24 rows, labeled 0 through 23, including zero hours, and the same 20-cell bar. Its `hour`, `hits`, and `bytes` headers are centered. Hour body cells are left aligned, byte cells are right aligned, but—unlike other numeric body cells—time-table hit counts are centered. For a four-character hits column, a count of one is therefore rendered as `│0   │ 1  │`, not `│0   │   1│`; when the hits column is five characters wide its header begins `│hour│hits │bytes│`. Render bars with eighth-block resolution using spaces and `▏▎▍▌▋▊▉█`; a maximum is 20 `█` characters. The right edge of a histogram header is the maximum selected-key value and its left edge is `0`.

## Spec 21

At detail length 0, status is a compact four-column table headed `HTTP status codes:` with class columns 2xx, 3xx, 4xx, 5xx and percentages (1xx is folded with 5xx by the original classification behavior, so the canonical sample percentages are exactly `79.1%,14.9%,1.2%,4.8%`). At length 1 or above, show individual status rows. Status/method tables are otherwise not truncated.

For large categorical tables, row limits depend on length. The tested mappings are: length 0 => 3 IPs, 5 referers, 10 paths; length 1 => 5 IPs, 10 referers, 50 paths; length 3 => 60 referers and 150 paths. Higher levels increase limits, length 6 and very large values show all available rows. Values above 6 are accepted and effectively cap at all rows. When the distinct value count does not exceed the limit, omit `K most frequent:` and show everything.

By default path tables exclude a target if and only if its normalized path ends case-sensitively with one of these ten suffixes: `.png`, `.css`, `.svg`, `.jpg`, `.jpeg`, `.gif`, `.ico`, `.js`, `.woff2`, or `.webp`. This is a closed set: `.map`, `.bmp`, `.tiff`, `.woff`, `.ttf`, `.eot`, `.mp3`, `.mp4`, `.webm`, and uppercase `.PNG` are not excluded. On the canonical `test-data/access.log`, this rule produces `286 paths (excluding resources like images, css, etc.)`; `--all` produces `619 paths.`. The exclusion affects only path tables/trends, not input records, filtering, raw/CSV/JSON, hit totals, or percentages. `--all` removes it and also removes the caption's “excluding resources” phrase.

## Spec 22

With `--color no`, analysis/table output has no ANSI escapes. With `--color yes`, style the table result with ANSI SGR escapes. When `NO_COLOR` is absent, this includes 256-color sequences such as `ESC[38;5;204m`; when `NO_COLOR=1` is present, forced styling still emits sequences such as `ESC[m`, `ESC[1m`, and `ESC[0m`, but no `ESC[38;5;` sequence. Stripping SGR escapes yields the byte-for-byte `--color no` output in either environment. `auto` is the default and chooses styling based on whether output is interactive. Color never changes visible characters, grouping, ordering, or values.

The following plain no-color examples are normative for layout:

```text
6 hits and 3.2G from 2021/01/22 to 2021/01/22
3 paths (excluding resources like images, css, etc.). 
┌───┬───────┬────┬─────┬─────┐
│ # │path   │hits│  %  │bytes│
├───┼───────┼────┼─────┼─────┤
│  1│/huge  │   3│50.0%│ 3.2G│
│  2│/big   │   2│33.3%│ 2.1M│
│  3│/medium│   1│16.7%│ 1024│
└───┴───────┴────┴─────┴─────┘
```

```text
33,468 hits and 405M from 2021/01/22 to 2021/01/22
HTTP status codes:
┌─────┬─────┬────┬────┐
│ 2xx │ 3xx │4xx │5xx │
├─────┼─────┼────┼────┤
│79.1%│14.9%│1.2%│4.8%│
└─────┴─────┴────┴────┘
```

## Spec 23

`--changes` enables per-date-bucket histograms and trend columns for dynamic fields (path, referer, IP; status/method may display daily context but do not get more/less captions). A new date bucket is created whenever the parsed date differs from the immediately preceding accepted record's date; this is encounter-order run grouping, not a count of distinct dates or the inclusive calendar span. Fewer than four such buckets produces the normal table without `days` or `trend`; four enables those columns. Consequently, records encountered in date runs January 1, January 2, January 1, January 3 enable a header containing `│ # │path    │hits│bytes│days│trend│` even though the summary is only `from 2024/01/01 to 2024/01/03`, while three contiguous date runs do not. Use no more than the most recent 20 date buckets in a row's `days` histogram. Each bucket is one character from ` ▁▂▃▄▅▆▇`, scaled against that row's maximum bucket count: zero is a space and a row maximum is `▇`.

The tail period is the final two displayed date buckets and the reference period is all preceding displayed buckets. First compute a global normalization factor from all unfiltered records using the chosen key: `global reference sum / global tail sum`. For each row, compute its `reference` and `tail` sums using that key, multiply its tail by the global factor, and compute signed trend strength as `1000 * (normalized_tail - reference) / (reference + normalized_tail)` (handle a zero denominator as stable). Strength from -200 through 200 is blank; magnitude above 200 through 500 is one arrow, above 500 through 900 is two, and above 900 is three, using `➚` or `➘` in a five-character `trend` column. Examples are blank, `  ➚  `, ` ➚ ➚`, and `➚ ➚ ➚` (analogous downward arrows). Regardless of computed strength, render the trend cell blank for a group with 9 or fewer total hits. In an observed eight-bucket case, `/up` with counts `1,1,0,0,0,0,2,1` therefore had five hits and a blank trend cell, while `/down` with counts `2,2,2,2,2,2,0,1` had 13 hits and rendered ` ➘ ➘ `.

The main field table remains sorted by the requested key and includes `days` and `trend`. When enough nonstable candidates exist, append `More popular <field caption>` and `Less popular <field caption>` tables after it; these rank trend direction and use total-key amount as a tie breaker (positive equal trends favor larger totals; nonpositive ties reverse). Apply date filtering before choosing the trend window. A canonical eight-day result is:

```text
64 hits and 66K from 2024/01/01 to 2024/01/08
3 paths (excluding resources like images, css, etc.)
┌───┬────────┬────┬─────┬────────┬─────┐
│ # │path    │hits│bytes│  days  │trend│
├───┼────────┼────┼─────┼────────┼─────┤
│  1│/falling│  30│  31K│▇▇▇▇▇▇  │➘ ➘ ➘│
│  2│/rising │  26│  27K│▁▁▁▁▁▁▇▇│ ➚ ➚ │
│  3│/stable │   8│ 8192│▇▇▇▇▇▇▇▇│     │
└───┴────────┴────┴─────┴────────┴─────┘
More popular paths (excluding resources like images, css, etc.)
┌───┬────────┬────┬─────┬────────┬─────┐
│ # │path    │hits│bytes│  days  │trend│
├───┼────────┼────┼─────┼────────┼─────┤
│  1│/rising │  26│  27K│▁▁▁▁▁▁▇▇│ ➚ ➚ │
│  2│/falling│  30│  31K│▇▇▇▇▇▇  │➘ ➘ ➘│
└───┴────────┴────┴─────┴────────┴─────┘
Less popular paths (excluding resources like images, css, etc.)
┌───┬────────┬────┬─────┬────────┬─────┐
│ # │path    │hits│bytes│  days  │trend│
├───┼────────┼────┼─────┼────────┼─────┤
│  1│/falling│  30│  31K│▇▇▇▇▇▇  │➘ ➘ ➘│
│  2│/rising │  26│  27K│▁▁▁▁▁▁▇▇│ ➚ ➚ │
└───┴────────┴────┴─────┴────────┴─────┘
```

Terminal stdout receives the same finite table rendering as non-TTY stdout; there is no interactive help overlay or keyboard-command loop. In a 120x40 pseudo-terminal the executable prints the table and exits. Sending `?` after the initial output produces no additional bytes, and neither Escape nor `q` is required to terminate it.

## Spec 24

Help is rendered as a styled Unicode table whose wrapping and escape parameters depend on the output environment. `COLUMNS` controls the available width (80 columns when no width is supplied), and `NO_COLOR` controls whether the SGR sequences carry 256-color parameters; `--color no` does not override this help-specific styling. At 80 columns, long option names wrap within the eight-column `long` cell: `--referer` appears as `--refere` followed by `r` on the next row, and `--silent-load` as `--silent` followed by `-load`. Consumers must not require either full option name to occur as one contiguous byte substring.

Help output is deterministic once those environment variables are fixed. Every successful help invocation writes nothing to stderr and ends stdout with exactly two LF bytes (there is no third trailing LF). In the ordinary non-TTY, 80-column no-color environment, the explicit invocation `env -u COLUMNS TERM=dumb NO_COLOR=1 executable --help` produces exactly 6,682 stdout bytes with SHA-256 `1f60d5b3bb3258fed00a2c7f43666600f8b06038dbd756d9e65f3463356a35f3`. With the same environment, `executable --output json --color no --help` produces the identical 6,682 bytes. The 11,724-byte literal below belongs only to its stated 50-column colored environment and must not be used as the expected output of either of these 80-column invocations.

After stripping SGR sequences, both colored and `NO_COLOR=1` output at 80 columns have exactly 4,742 bytes with SHA-256 `f00a349a90b07962e2514857a59e1d080c0ed37c7aa081e94b98aec4969bc88c`. The introduction begins exactly as follows (including the 35 spaces before `rhit`):

```text
                                   rhit 2.0.4

Rhit analyzes your nginx logs.

Complete documentation at https://dystroy.org/rhit

Usage:  rhit [options] [FILES]
```

The help table includes every option from Spec 2. In particular, its complete 80-column, SGR-stripped method-through-time filter segment is exactly:

```text
│ -m  │--method│METHOD │HTTP method to filter by. Make it negative with a !.   │
│     │        │       │(eg: -m PUT or -m !DELETE or -m none or -m other)      │
│ -p  │--path  │ PATH  │Pattern for path filtering (eg: -p broot or -p '^/\d+' │
│     │        │       │or -p 'miaou | blog')                                  │
│ -r  │--refere│REFERER│Referrer filter                                        │
│     │r       │       │                                                       │
│ -s  │--status│STATUS │Comma separated list of statuses or status ranges to   │
│     │        │       │filter by (eg: -s 514 or -s 4xx,5xx, or                │
│     │        │       │-s 310-340,400-450 or -s 5xx,!502)                     │
│ -t  │--time  │ TIME  │Filter the time of the day, in the logs' timezone (eg: │
│     │        │       │-t '>19:30' to get evening hits)                       │
```

The base64 block below is the exact stdout only for the observed environment `COLUMNS=50`, `TERM=xterm-256color`, with `NO_COLOR` absent. In that environment it is produced by both `--help` and `--output json --color no --help`, contains 11,724 bytes, has SHA-256 `027de84399e5d6ef8f7a81f6f2507876406e4791396f4bd597c906c1d49254c9`, and ends with two newline bytes. At 80 columns with `NO_COLOR` absent, the observed output instead contains 9,820 bytes; at 80 columns with `NO_COLOR=1`, it contains 6,682 bytes. In all cases the displayed program name is `rhit`, not the filesystem name `executable`.

```base64
ICAgICAgICAgICAgICAgICAgICAbWzM4OzU7MjA0bRtbMW0bWzRtcmhpdBtbMG0bWzM4OzU7MjA0bRtbMW0bWzRtIBtbMG0bWzM4OzU7MjA0bRtbMW0bWzRt
Mi4wLjQbWzBtCgobWzM4OzU7MjA0bRtbMW1SaGl0G1swbSBhbmFseXplcyB5b3VyIG5naW54IGxvZ3MuCgpDb21wbGV0ZSBkb2N1bWVudGF0aW9uIGF0IBtb
NG1odHRwczovL2R5c3Ryb3kub3JnL3JoaXQbWzBtCgobWzM4OzU7MjA0bRtbMW1Vc2FnZTogG1swbSAbWzQ4OzU7MjM1bRtbMzg7NTsyNDltcmhpdBtbNDlt
G1szOW0bWzQ4OzU7MjM1bRtbMzg7NTsyNDltIFtvcHRpb25zXRtbNDltG1szOW0bWzQ4OzU7MjM1bRtbMzg7NTsyNDltIFtGSUxFU10bWzQ5bRtbMzltCgob
WzM4OzU7MjQwbeKAohtbMzltIBtbNDg7NTsyMzVtG1szODs1OzI0OW1GSUxFUxtbNDltG1szOW0gOiBUaGUgbG9nIGZpbGUgb3IgZm9sZGVyIHRvIGFuYWx5
emUuIEl0IAogIG5vdCBwcm92aWRlZCwgbG9ncyB3aWxsIGJlIG9wZW5lZCBhdCB0aGVpciAKICBzdGFuZGFyZCBsb2NhdGlvbgoKG1szODs1OzIwNG0bWzFt
T3B0aW9uczobWzBtChtbMzg7NTsyMzlt4pSMG1szOW0bWzM4OzU7MjM5beKUgOKUgOKUgOKUgBtbMzltG1szODs1OzIzOW3ilKwbWzM5bRtbMzg7NTsyMzlt
4pSA4pSA4pSA4pSA4pSA4pSAG1szOW0bWzM4OzU7MjM5beKUrBtbMzltG1szODs1OzIzOW3ilIDilIDilIDilIAbWzM5bRtbMzg7NTsyMzlt4pSsG1szOW0b
WzM4OzU7MjM5beKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU
gOKUgOKUgOKUgOKUgBtbMzltG1szODs1OzIzOW3ilJAbWzM5bQobWzM4OzU7MjM5beKUghtbMzltc2hvchtbMzg7NTsyMzlt4pSCG1szOW0gbG9uZyAbWzM4
OzU7MjM5beKUghtbMzltdmFsdRtbMzg7NTsyMzlt4pSCG1szOW1kZXNjcmlwdGlvbiAgICAgICAgICAgICAgICAgICAgG1szODs1OzIzOW3ilIIbWzM5bQob
WzM4OzU7MjM5beKUghtbMzltIHQgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgICAbWzM4OzU7MjM5beKUghtbMzltIGUgIBtbMzg7NTsyMzlt4pSCG1szOW0g
ICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUnBtbMzltG1szODs1OzIzOW3ilIDilIDilIDi
lIAbWzM5bRtbMzg7NTsyMzlt4pS8G1szOW0bWzM4OzU7MjM5beKUgOKUgOKUgOKUgOKUgOKUgBtbMzltG1szODs1OzIzOW3ilLwbWzM5bRtbMzg7NTsyMzlt
4pSA4pSA4pSA4pSAG1szOW0bWzM4OzU7MjM5beKUvBtbMzltG1szODs1OzIzOW3ilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi
lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAbWzM5bRtbMzg7NTsyMzlt4pSkG1szOW0KG1szODs1OzIzOW3ilIIb
WzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltLS1oZWxwG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltUHJpbnQgaGVscCBpbmZv
cm1hdGlvbiAgICAgICAgIBtbMzg7NTsyMzlt4pSCG1szOW0KG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltLS12ZXJzG1szODs1
OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltUHJpbnQgdGhlIHZlcnNpb24gICAgICAgICAgICAgIBtbMzg7NTsyMzlt4pSCG1szOW0KG1sz
ODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltaW9uICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltICAg
ICAgICAgICAgICAgICAgICAgICAgICAgICAgIBtbMzg7NTsyMzlt4pSCG1szOW0KG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzlt
LS1jb2xvG1szODs1OzIzOW3ilIIbWzM5bWNvbG8bWzM4OzU7MjM5beKUghtbMzltV2hldGhlciB0byBoYXZlIHN0eWxlcyBhbmQgICAgIBtbMzg7NTsyMzlt
4pSCG1szOW0KG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltciAgICAgG1szODs1OzIzOW3ilIIbWzM5bSByICAbWzM4OzU7MjM5
beKUghtbMzltY29sb3JzICAgICAgICAgICAgICAgICAgICAgICAgIBtbMzg7NTsyMzlt4pSCG1szOW0KG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7
MjM5beKUghtbMzltICAgICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltIFBvc3NpYmxlIHZhbHVlczogWxtbNDg7NTsyMzVt
G1szODs1OzI0OW1hdXRvG1s0OW0bWzM5bSwgG1s0ODs1OzIzNW0bWzM4OzU7MjQ5bXllcxtbNDltG1szOW0sICAbWzM4OzU7MjM5beKUghtbMzltChtbMzg7
NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bRtbNDg7
NTsyMzVtG1szODs1OzI0OW1ubxtbNDltG1szOW1dICAgICAgICAgICAgICAgICAgICAgICAgICAgIBtbMzg7NTsyMzlt4pSCG1szOW0KG1szODs1OzIzOW3i
lIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltICAgICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltIERlZmF1bHQ6IBtb
NDg7NTsyMzVtG1szODs1OzI0OW1hdXRvG1s0OW0bWzM5bSAgICAgICAgICAgICAgICAgG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzlt
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
ODs1OzI0OW0tcCBicm9vdBtbNDltG1szOW0gb3IgG1s0ODs1OzIzNW0bWzM4OzU7MjQ5bS1wICdeL1xkKycbWzQ5bRtbMzltIG9yICAgICAgG1szODs1OzIz
OW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgICAbWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsy
Mzlt4pSCG1szOW0bWzQ4OzU7MjM1bRtbMzg7NTsyNDltLXAgJ21pYW91IHwgYmxvZycbWzQ5bRtbMzltKSAgICAgICAgICAgICAbWzM4OzU7MjM5beKUghtb
MzltChtbMzg7NTsyMzlt4pSCG1szOW0gLXIgG1szODs1OzIzOW3ilIIbWzM5bS0tcmVmZRtbMzg7NTsyMzlt4pSCG1szOW1SRUZFG1szODs1OzIzOW3ilIIb
WzM5bVJlZmVycmVyIGZpbHRlciAgICAgICAgICAgICAgICAbWzM4OzU7MjM5beKUghtbMzltChtbMzg7NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3i
lIIbWzM5bXJlciAgIBtbMzg7NTsyMzlt4pSCG1szOW1SRVIgG1szODs1OzIzOW3ilIIbWzM5bSAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAbWzM4
OzU7MjM5beKUghtbMzltChtbMzg7NTsyMzlt4pSCG1szOW0gLXMgG1szODs1OzIzOW3ilIIbWzM5bS0tc3RhdBtbMzg7NTsyMzlt4pSCG1szOW1TVEFUG1sz
ODs1OzIzOW3ilIIbWzM5bUNvbW1hIHNlcGFyYXRlZCBsaXN0IG9mICAgICAgICAbWzM4OzU7MjM5beKUghtbMzltChtbMzg7NTsyMzlt4pSCG1szOW0gICAg
G1szODs1OzIzOW3ilIIbWzM5bXVzICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gVVMgG1szODs1OzIzOW3ilIIbWzM5bXN0YXR1c2VzIG9yIHN0YXR1cyByYW5n
ZXMgdG8gICAbWzM4OzU7MjM5beKUghtbMzltChtbMzg7NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAgIBtbMzg7NTsyMzlt4pSC
G1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bWZpbHRlciBieSAoZWc6IBtbNDg7NTsyMzVtG1szODs1OzI0OW0tcyA1MTQbWzQ5bRtbMzltIG9yICAgICAg
IBtbMzg7NTsyMzlt4pSCG1szOW0KG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltICAgICAgG1szODs1OzIzOW3ilIIbWzM5bSAg
ICAbWzM4OzU7MjM5beKUghtbMzltG1s0ODs1OzIzNW0bWzM4OzU7MjQ5bS1zIDR4eCw1eHgbWzQ5bRtbMzltLCBvciAgICAgICAgICAgICAgICAgG1szODs1
OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgICAbWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7
NTsyMzlt4pSCG1szOW0bWzQ4OzU7MjM1bRtbMzg7NTsyNDltLXMgMzEwLTM0MCw0MDAtNDUwG1s0OW0bWzM5bSBvciAgICAgICAgICAbWzM4OzU7MjM5beKU
ghtbMzltChtbMzg7NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3i
lIIbWzM5bRtbNDg7NTsyMzVtG1szODs1OzI0OW0tcyA1eHgsITUwMhtbNDltG1szOW0pICAgICAgICAgICAgICAgICAgIBtbMzg7NTsyMzlt4pSCG1szOW0K
G1szODs1OzIzOW3ilIIbWzM5bSAtdCAbWzM4OzU7MjM5beKUghtbMzltLS10aW1lG1szODs1OzIzOW3ilIIbWzM5bVRJTUUbWzM4OzU7MjM5beKUghtbMzlt
RmlsdGVyIHRoZSB0aW1lIG9mIHRoZSBkYXksIGluIBtbMzg7NTsyMzlt4pSCG1szOW0KG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtb
MzltICAgICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltdGhlIGxvZ3MnIHRpbWV6b25lIChlZzogICAgICAgIBtbMzg7NTsy
Mzlt4pSCG1szOW0KG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltICAgICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7
MjM5beKUghtbMzltG1s0ODs1OzIzNW0bWzM4OzU7MjQ5bS10ICc+MTk6MzAnG1s0OW0bWzM5bSB0byBnZXQgZXZlbmluZyAgICAgG1szODs1OzIzOW3ilIIb
WzM5bQobWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgICAbWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSC
G1szOW1oaXRzKSAgICAgICAgICAgICAgICAgICAgICAgICAgG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltIC1hIBtbMzg7NTsyMzlt
4pSCG1szOW0tLWFsbCAbWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW1TaG93IGFsbCBwYXRocywgaW5jbHVkaW5nICAgICAgG1sz
ODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgICAbWzM4OzU7MjM5beKUghtbMzltICAgIBtb
Mzg7NTsyMzlt4pSCG1szOW1yZXNvdXJjZXMgICAgICAgICAgICAgICAgICAgICAgG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltICAg
IBtbMzg7NTsyMzlt4pSCG1szOW0tLW5vLW4bWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW1UcnkgdG8gb3BlbiBhbGwgZmlsZXMs
IHdoYXRldmVyG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW1hbWUtY2gbWzM4OzU7MjM5beKU
ghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW10aGVpciBuYW1lcyAgICAgICAgICAgICAgICAgICAgG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5
beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW1lY2sgICAbWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgICAgICAg
ICAgICAgICAgICAgICAgICAgICAgG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltIC1vIBtbMzg7NTsyMzlt4pSCG1szOW0tLW91dHAb
WzM4OzU7MjM5beKUghtbMzltT1VUUBtbMzg7NTsyMzlt4pSCG1szOW1PdXRwdXQ6IGJ5IGRlZmF1bHQgcHJldHR5ICAgICAgG1szODs1OzIzOW3ilIIbWzM5
bQobWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW11dCAgICAbWzM4OzU7MjM5beKUghtbMzltIFVUIBtbMzg7NTsyMzlt4pSCG1sz
OW1zdW1tYXJ5IHRhYmxlcyBidXQgeW91IGNhbiBhbHNvG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSC
G1szOW0gICAgICAbWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW1vdXRwdXQgbG9nIGxpbmVzIGFzIBtbNDg7NTsyMzVtG1szODs1
OzI0OW1jc3YbWzQ5bRtbMzltLCAbWzQ4OzU7MjM1bRtbMzg7NTsyNDltanNvbhtbNDltG1szOW0sIBtbMzg7NTsyMzlt4pSCG1szOW0KG1szODs1OzIzOW3i
lIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltICAgICAgG1szODs1OzIzOW3ilIIbWzM5bSAgICAbWzM4OzU7MjM5beKUghtbMzltb3IgG1s0ODs1OzIz
NW0bWzM4OzU7MjQ5bXJhdxtbNDltG1szOW0gKGFzIHRoZXkgYXBwZWFyIGluIHRoZSAgG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzlt
ICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgICAbWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW1sb2cgZmlsZXMpICAgICAgICAg
ICAgICAgICAgICAgG1szODs1OzIzOW3ilIIbWzM5bQobWzM4OzU7MjM5beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gICAgICAbWzM4OzU7MjM5
beKUghtbMzltICAgIBtbMzg7NTsyMzlt4pSCG1szOW0gRGVmYXVsdDogG1s0ODs1OzIzNW0bWzM4OzU7MjQ5bXRhYmxlcxtbNDltG1szOW0gICAgICAgICAg
ICAgICAbWzM4OzU7MjM5beKUghtbMzltChtbMzg7NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bS0tc2lsZRtbMzg7NTsyMzlt4pSCG1sz
OW0gICAgG1szODs1OzIzOW3ilIIbWzM5bURvbid0IHByaW50IGFueXRoaW5nIGR1cmluZyAgICAbWzM4OzU7MjM5beKUghtbMzltChtbMzg7NTsyMzlt4pSC
G1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bW50LWxvYRtbMzg7NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bWxvYWQ6IG5vIHByb2dy
ZXNzIGJhciBvciBmaWxlICAbWzM4OzU7MjM5beKUghtbMzltChtbMzg7NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bWQgICAgIBtbMzg7
NTsyMzlt4pSCG1szOW0gICAgG1szODs1OzIzOW3ilIIbWzM5bWxpc3QgICAgICAgICAgICAgICAgICAgICAgICAgICAbWzM4OzU7MjM5beKUghtbMzltChtb
Mzg7NTsyMzlt4pSUG1szOW0bWzM4OzU7MjM5beKUgOKUgOKUgOKUgBtbMzltG1szODs1OzIzOW3ilLQbWzM5bRtbMzg7NTsyMzlt4pSA4pSA4pSA4pSA4pSA
4pSAG1szOW0bWzM4OzU7MjM5beKUtBtbMzltG1szODs1OzIzOW3ilIDilIDilIDilIAbWzM5bRtbMzg7NTsyMzlt4pS0G1szOW0bWzM4OzU7MjM5beKUgOKU
gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgBtb
MzltG1szODs1OzIzOW3ilJgbWzM5bQoK
```
