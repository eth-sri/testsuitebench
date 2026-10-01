# Clarified specification for `executable`

The required artifact is one executable file named exactly `executable`. It is a command-line program compatible with the behavior described below. All output is UTF-8. Unless a rule explicitly says otherwise, normal results are written to standard output, diagnostics are written to standard error, and every emitted line ends in `\n`.

The input format is the newline-delimited JSON event stream produced by `go test -json`. In the descriptions below, “visible width” excludes ANSI escape sequences and uses terminal character width rather than UTF-8 byte count. Requirements for rendering are normative: spacing, punctuation, borders, and final newlines are significant.

## Spec 1

The executable must support these options:

- Boolean options: `-h`, `--help`, `-v`, `--version`, `-all`, `-pass`, `-skip`, `-notests`, `-smallscreen`, `-nocolor`, `-follow`, `-follow-verbose`, `-include-timestamp`, `-progress`, and the legacy option `-noborders`.
- String-valued options: `-file`, `-sort`, `-format`, `-follow-output`, `-compare`, and `-trimpath`.
- Integer-valued option: `-slow`.

Both `-name value` and `-name=value` forms work for valued options. A flag may also use two leading hyphens. Repeated valued options are allowed and the last parsed value wins. Boolean options support the conventional `-flag=true` and `-flag=false` forms. A separate token after a Boolean flag is positional rather than its Boolean value. As with Go’s standard `flag` parser, the first positional token stops further flag parsing and the remaining positional tokens are ignored. `--` explicitly has the same stop-parsing effect, so tokens after it never act as flags. Combined short flags such as `-vnocolor` are not supported.

Unknown flags and syntactically invalid integer values are command-line parse errors: write the Go-style error and usage text to standard error and exit 2. For example, `-unknown` or `--unknown` includes `flag provided but not defined: -unknown`; `-file` without a value includes `flag needs an argument: -file`; and `-slow abc` includes `invalid value "abc" for flag -slow`. Each such diagnostic also includes `Usage:`. A help option followed by an invalid option may therefore produce parse-error usage rather than normal help, but it must still contain `Usage:`. Help-like tokens after `--` are positional and do not request help.

The accepted `-sort` values are case-sensitive `name`, `elapsed`, and `cover`, with default `name`. The accepted `-format` values are case-sensitive `basic`, `plain`, and `markdown`, with default `basic`. These two values are validated after command-line parsing. An invalid value writes exactly one of the following to standard error, produces no normal output, and exits 0:

```text
invalid option:"VALUE". The -sort flag must be one of: name, elapsed or cover
```

```text
invalid option:"VALUE". The -format flag must be one of: basic, plain or markdown
```

`-slow` accepts any syntactically valid signed integer. Zero means unlimited; a limit larger than the number of available tests simply displays all of them.

## Spec 2

`-h` and `--help` exit 0, write nothing to standard error, and write exactly this text to standard output:

```text
Usage:
    go test ./... -json | tparse [options...]
    go test [packages...] -json | tparse [options...]
    go test [packages...] -json > pkgs.out ; tparse [options...] -file pkgs.out

Options:
    -h                 Show help.
    -v                 Show version.
    -all               Display table event for pass and skip. (Failed items always displayed)
    -pass              Display table for passed tests.
    -skip              Display table for skipped tests.
    -notests           Display packages containing no test files or empty test files.
    -smallscreen       Split subtest names vertically to fit on smaller screens.
    -slow              Number of slowest tests to display. Default is 0, display all.
    -sort              Sort table output by attribute [name, elapsed, cover]. Default is name.
    -nocolor           Disable all colors. (NO_COLOR also supported)
    -format            The output format for tables [basic, plain, markdown]. Default is basic.
    -file              Read test output from a file.
    -follow            Follow raw output from go test to stdout.
    -follow-output     Write raw output from go test to a file (takes precedence over -follow).
    -include-timestamp Include timestamps in follow output. 
    -progress          Print a single summary line for each package. Useful for long running test suites.
    -compare           Compare against a previous test output file. (experimental)
    -trimpath          Remove path prefix from package names in output, simplifying their display.
```

There is a terminating newline after the final line. The accepted compatibility options `-follow-verbose` and `-noborders` are intentionally not listed in help.

`-v` and `--version` exit 0, write nothing to standard error, and write exactly:

```text
tparse version: (devel)
```

Help and version do not require input.

## Spec 3

With `-file PATH`, read the event stream from that file; otherwise read standard input. File input takes precedence over standard input. Paths containing spaces are ordinary paths in either valued-option syntax.

If `PATH` cannot be opened, exit 1, write nothing to standard output, and write an operating-system-style diagnostic to standard error beginning with `open PATH:` (for a missing file it must include text equivalent to `no such file or directory`).

When no `-file` is supplied and standard input is not a pipe, exit 1 and write this diagnostic to standard error:

```text
stdin must be a pipe, or use -file to open a go test output file
```

When the selected input is empty, whitespace-only, plain text, malformed JSON only, or otherwise contains no parsable Go test event, exit 1, write nothing to standard output, and write exactly:

```text
no parsable events: Make sure to run go test with -json flag
```

Valid Unicode is preserved, but input is read with a bounded line scanner. In particular, a single valid JSON event line whose package name is `例.测试/` followed by 70,000 `x` characters and `/終` exceeds that bound: exit 1, write nothing to standard output, and write exactly `received scanning error: bufio.Scanner: token too long\n` to standard error.

## Spec 4

Each nonblank input line is independently decoded as one JSON object with the following relevant fields:

```text
Time     RFC3339/RFC3339Nano timestamp string
Action   event kind string
Package  Go import path string
Test     test name string; absent on package-level events
Elapsed  seconds as a JSON number; may be absent
Output   raw textual output; normally includes its own newline
ImportPath  nonempty on Go 1.24 build events
FailedBuild package identifier reported on a build-related final event
```

Recognize ordinary test actions `start`, `run`, `pause`, `cont`, `output`, `pass`, `fail`, `skip`, and `bench`. Syntactically valid Go 1.24 `build-output` and `build-fail` objects are accepted as input, but they do not create a package or test result; their channel behavior and the resulting empty-package outcome are specified in Specs 7 and 19. `start` and harmless unknown actions may be ignored, but must not make an otherwise valid stream fail. Events for concurrently running packages may be interleaved; state must be keyed by the full package name and, where applicable, full test name.

A terminal `pass`, `fail`, or `skip` event with a nonempty `Test` creates or completes one test result. Its status is the last such action after that test’s events are ordered by `Time`, and its elapsed value is the largest `Elapsed` on any of its events. Parent tests and slash-separated subtests are separate results and are all counted. A package-level `pass` or `fail` event without `Test` supplies the package status and package elapsed time. A bare package-level `skip` is instead processed as a skipped test having an empty test name; unless no-test output has already classified the package as described in Spec 6, its rendered summary therefore has blank status and package cells, elapsed `0.00s`, counts `0` pass, `0` fail, `1` skip, and exit status 0. Package output and test output must be retained as needed for follow, failure, panic, race, coverage, cached, and no-test handling.

Before the first valid JSON event, tolerate and skip at most 50 non-JSON lines (and, when following, echo them with a newline). Once a valid event has been seen, any later malformed line is a parsing error; more than 50 leading malformed lines is also an error. If end-of-input arrives without a valid event, use the no-parsable-events behavior in Spec 3. A JSON object counts as syntactically parsable even when some optional fields are absent.

## Spec 5

Build one summary record per distinct full package name, except for the bare package-level `skip` rendering anomaly specified in Spec 4. For an ordinary package, the record contains:

- status `PASS` or `FAIL` from its terminal package event. That package event is authoritative: failed test results still contribute to the failure count and diagnostics, but do not override a terminal package `pass`;
- elapsed time from its terminal package event, not the sum of test elapsed values;
- the package name;
- coverage if found;
- counts of all terminal test-level `pass`, `fail`, and `skip` events.

Counting includes both parent tests and subtests. For example, if `TestMain/subtest1` passes, `TestMain/subtest2` fails, and parent `TestMain` fails, counts are pass 1, fail 2, skip 0.

Extract coverage from package output containing `coverage: N% of statements`, preserving one decimal place such as `60.5%` or `100.0%`. Display `--` when coverage is absent. Detect package output ending in `(cached)` and display literal `(cached)` instead of a numeric package elapsed time. An otherwise passing cached package remains `PASS`.

If a package explicitly reports coverage, has exactly 0.0% coverage, and has no pass/fail/skip test results at all, omit that package from the summary; this handles Go’s synthetic zero-coverage/no-test output.

Package elapsed values are displayed with exactly two decimals and an `s`, such as `0.00s`, `3.77s`, or `10.80s`. Individual test elapsed values use exactly two decimals without an `s`, such as `0.00`, `0.17`, or `3.49`.

## Spec 6

A package with output of the form `?   \tPACKAGE\t[no test files]\n` is a no-test package. Its summary representation has status `NOTEST`, elapsed `0.00s`, count cells `--`, and a two-line package cell: its package name followed by `[no test files]`.

The superficially similar package output `?   \tPACKAGE\t[no tests to run]\n` is not a no-test marker. When followed by a package-level `pass` with elapsed 0, it is omitted from the rendered output and produces an ordinary `PASS` summary row with elapsed `0.00s` and pass/fail/skip counts `0`/`0`/`0`.

When an input contains both tested packages and no-test packages, no-test packages are omitted from the final summary unless `-notests` is present. When the input consists only of a no-test package, it is still displayed even without `-notests`. No-test packages never make the command fail.

For example, a colored basic row is structurally:

```text
│ NOTEST │  0.00s  │ example.com/notest │  --   │  --  │  --  │  --  │
│        │         │ [no test files]     │       │      │      │      │
```

with `NOTEST` colored yellow unless color is disabled.

## Spec 7

The final process outcome is independent of display-selection flags:

- Exit 0 if every terminal package result is `pass` or the input represents only skipped/no-test results, except for the passing data-race case below. A terminal package `pass` also controls the exit status when some counted test results are `fail`.
- Exit 1 if any terminal package result is `fail`, if a panic or data race is detected, or for the input/file errors described above.
- Exit 2 for command-line parse errors and for a recognized leading traditional build/setup-failure marker when the input also contains a parsable JSON event.

A data-race marker does not override later displayed terminal results, but it does determine the process status. Output containing `WARNING: DATA RACE` is omitted from the formatted result whether the associated terminal results pass or fail. When the test and package both terminate with `pass`, the summary remains `PASS` with the ordinary counts, but the process exits 1. When they fail, the ordinary failure heading and `FAIL` summary remain; any embedded failure marker is handled as detailed in Spec 18. Panics make the result fail. Display flags, formats, follow mode, progress mode, sorting, slow filtering, and path trimming do not mask an otherwise failing terminal package, panic, or data-race result.

Go 1.24-style events having nonempty `ImportPath` are not added as test events; any such `Output` is forwarded verbatim to standard error, while `build-fail` does not itself set exit status 2. If the stream contains only these build events, no summary is written, the process exits 1, and standard error ends with `found no go test packages\n` after any forwarded build output.

Also recognize a leading traditional non-JSON line matching `FAIL PACKAGE [build failed]` or `FAIL PACKAGE [setup failed]` when it precedes a parsable package-level JSON `fail` event for the same package. This combination produces a build/setup result with status `FAIL`, the elapsed value from that package-level JSON event, coverage/counts `--`, and exit 2. For example, JSON elapsed `0.4` is displayed as `0.40s` for both markers. The second physical line of its package cell is literal `[]` for both input markers; neither original marker text is reproduced. The traditional line alone creates no result: it exits 1 with no standard output and the exact no-parsable-events diagnostic from Spec 3.

## Spec 8

Normal output has this logical order:

1. selected follow output, in event order;
2. progress lines, in package-completion order;
3. an optional detailed test table;
4. failure, panic, and race detail sections;
5. the package summary table.

Progress is naturally emitted when each applicable terminal package-level `pass` or `fail` event is encountered, so when combined with follow it follows that package’s raw output. Package-level `skip` is the non-emitting exception specified in Spec 21. The final summary is always last. The package summary is present for every successfully parsed stream, regardless of `-pass`, `-skip`, `-all`, `-notests`, `-follow`, or `-progress`. Do not emit an empty detailed-test table when no selected tests exist.

By default, passed and skipped test names are not printed. Failures and panics still get their detail sections, followed by the summary.

## Spec 9

Detailed-test selection works as follows:

- `-pass` selects passed tests.
- `-skip` selects skipped tests.
- `-all` selects both and is equivalent to `-pass -skip`.
- If any of those selection modes produces a detailed table, failed tests are included in that table too, regardless of which selector was used.
- Without all three selectors, there is no detailed table, even though failure detail sections are still shown.

Thus `-pass` on mixed input shows pass and fail rows but not skip rows; `-skip` shows skip and fail rows but not pass rows; and `-all` shows pass, skip, and fail rows. Selection of a failed table row does not itself add the test name or its attached terminal-event `Output` to the failure-details section; detail retention follows Spec 17. A `-skip` request on an all-pass input produces only the package summary because there are no selected rows. Do not create detailed rows for panic packages or packages classified as no-test/no-test-files, because they do not have a sensible ordinary test table.

Within each package, collect passed tests in first-test-encounter order and then apply Go's standard-library unstable `sort.Slice` with the sole comparison `left elapsed > right elapsed`. There is no secondary comparison for equal elapsed values, and the unstable permutation produced by that algorithm is contractual rather than encounter-order or lexical tie-breaking. For example, on the reference `fmt` stream, the displayed prefix is `TestScanInts` at `0.04`, `TestIsSpace` at `0.01`, `TestSprintf` at `0.00`, then `TestFmtInterface` at `0.00`. The same resulting row sequence is used by basic, plain, and Markdown formats and with color enabled or disabled. Displayed skipped tests then follow in encounter order, followed by failed tests in encounter order. Package groups use the package ordering from Spec 10. In basic and plain formats a completely blank table row separates adjacent package groups.

## Spec 10

`-sort` controls package-group and ordinary summary-row order:

- `name` (the default): ascending, case-sensitive lexical package name.
- `elapsed`: descending package elapsed time.
- `cover`: descending numeric coverage percentage.

The same sorted package sequence feeds the detailed table, failure sections, and summary. Panic and build/setup rows are emitted into the summary before ordinary package rows; ordinary rows retain their selected sorted order, followed by any displayed no-test rows. Test rows inside each package follow Spec 9. Sorting must be deterministic. Special characters, dots, underscores, hyphens, slashes, mixed case, cached results, and equal values must not cause errors.

`-slow N`, when `N > 0`, retains only the `N` slowest passed tests in each package. It is per-package, not global. It does not consume or suppress selected skipped tests, and it does not suppress failed tests. `-slow 0` and negative values mean no limit. For example, pass times 5.00, 3.00, 1.50, 1.00, and 0.30 with `-slow 3` display the first three, while summary counts still report all five.

## Spec 11

`-trimpath PREFIX` changes package names used in the basic/plain detailed table and in every form of the final summary. It does not change raw follow text, progress lines, package identity, the full package name printed in failure/panic headings, or the Markdown detailed-package heading.

For an explicit nonempty prefix, perform a literal, case-sensitive string-prefix removal on each matching package. Do not require a path-component boundary and do not remove a following slash that was not part of the supplied prefix. Consequently:

- `github.com/user/myapp/` removed from `github.com/user/myapp/cmd/server` yields `cmd/server`;
- `github.com/user/myapp` yields `/cmd/server`;
- `github.com/user` removed from `github.com/username/repo` yields `name/repo`;
- nonmatching packages remain unchanged.

An empty value is a no-op. Special characters are literal rather than regular-expression syntax. Do not merge distinct packages merely because trimming gives similar leaf names.

For `-trimpath auto`, do nothing when fewer than two distinct packages exist. Otherwise find their longest common character prefix, then shorten it to the last complete directory prefix ending in `/`; remove that prefix from every package. If no nonempty common directory prefix exists, do nothing. For example, the common directory prefix of `github.com/org/repo`, `github.com/org/repo/pkg`, and `github.com/org/repo/pkg/internal` is `github.com/org/`, yielding `repo`, `repo/pkg`, and `repo/pkg/internal`.

## Spec 12

`-smallscreen` applies two presentation transformations after explicit path trimming. First compute the automatic common directory prefix described in Spec 11 from the full package set, even when `-trimpath` is not `auto`.

- Only a slash-separated test name longer than 32 bytes is made multiline: keep the first component on the first line and place each subsequent component on its own line prefixed by one space and `/`. Example: a sufficiently long `TestParent/seed/long-case` becomes physical cell lines `TestParent`, ` /seed`, ` /long-case`; other cells of continuation lines are blank. If one subtest component itself exceeds 32 bytes, output successive 30-byte chunks followed by ` …`, then continue the same component on a new line prefixed by two spaces.
- If the common directory prefix is nonempty, remove it from the already explicitly-trimmed display name when it still matches, remove leading slashes, and apply the same multiline shortening with a 16-byte threshold in detailed-table package cells and a 32-byte threshold in summary package cells. If the common prefix is empty, display only the path’s leaf component. In that leaf-mode, if the leaf matches a semantic-import version component `v` plus digits, retain the previous component too: `github.com/org/repo/helper/v3` displays as `helper/v3`.

Without `-smallscreen`, slash-separated test names remain on one line and full untrimmed package names remain visible. Very long names must be accommodated by table width rather than silently truncated.

## Spec 13

The default/basic table renderer uses Unicode rounded borders. For columns with content-widths `w1...wn`, where each width is the maximum visible width of the header and every physical cell line, each rendered segment is `wi + 2` characters wide. Headers and the Status, Elapsed, Cover, Pass, Fail, and Skip data cells are centered; when centered padding is odd, put the extra space on the right. Test-name and package-name data cells are left-aligned with one leading space and all remaining padding on the right. Ignore ANSI bytes when calculating width. Use:

```text
╭────┬────╮   top border
│ .. │ .. │   rows
├────┼────┤   one separator after the header
╰────┴────╯   bottom border
```

There is no separator between ordinary data rows. Multiline cells produce multiple physical rows. A blank package-group separator is a normal all-blank physical row. The detailed table columns are exactly `Status`, `Elapsed`, `Test`, `Package`; the summary columns are exactly `Status`, `Elapsed`, `Package`, `Cover`, `Pass`, `Fail`, `Skip`.

Here is an exact no-color basic summary for a passing package named `strings`, package elapsed 3.77, two passed tests, no failures or skips, and no coverage:

```text
╭────────┬─────────┬─────────┬───────┬──────┬──────┬──────╮
│ Status │ Elapsed │ Package │ Cover │ Pass │ Fail │ Skip │
├────────┼─────────┼─────────┼───────┼──────┼──────┼──────┤
│  PASS  │  3.77s  │ strings │  --   │  2   │  0   │  0   │
╰────────┴─────────┴─────────┴───────┴──────┴──────┴──────╯
```

Tables are adjacent when one immediately follows another; do not insert a blank line between the detailed table’s bottom border and the next diagnostic heading or summary table.

## Spec 14

`-format plain` uses the same values, widths, alignment, row order, and multiline behavior as basic format, but has no box-drawing borders. For each physical row, replace the left and right borders and every internal vertical border with one space. Emit the header row, then one entirely blank row of the same width, then data rows. The exact no-color equivalent of the example in Spec 13 is:

```text
  Status   Elapsed   Package   Cover   Pass   Fail   Skip  
                                                           
   PASS     3.77s    strings    --      2      0      0    
```

The compatibility option `-noborders` selects plain format only when `-format` was not explicitly supplied. An explicit `-format`, wherever it occurs, takes precedence; for example, `-noborders -format markdown` is Markdown.

The failure/panic diagnostic heading is not a table and therefore keeps its heavy box in plain mode. Only tabular material loses borders.

## Spec 15

`-format markdown` renders the summary as a GitHub-style pipe table. Determine each column’s maximum visible content width, apply the same per-column alignment as basic format, add one literal space on both sides of each cell, and use a separator cell of hyphens filling the complete padded cell width. The exact no-color output for the Spec 13 example is:

```text
| Status | Elapsed | Package | Cover | Pass | Fail | Skip |
|--------|---------|---------|-------|------|------|------|
|  PASS  |  3.77s  | strings |  --   |  2   |  0   |  0   |
```

With color enabled, Markdown uses symbols rather than ANSI in status cells: `🟢 PASS`, `🔴 FAIL`, and `🟡 SKIP`; Markdown status-column width and separator width account for the symbol’s terminal display width. With `-nocolor` or `NO_COLOR`, omit those symbols and use plain centered status words.

For each package having selected detailed-test rows, Markdown replaces the four-column global detail table with a per-package structure. The heading is exactly ``## 📦 Package **`FULL_PACKAGE`**`` (the package icon and check mark below remain even in no-color mode), followed by a blank line and this material; repeat for each package in selected package order:

```text
Tests: ✓ P passed | S skipped | F failed

<details>

<summary>Click for test summary</summary>

| Status  | Elapsed | Test |
|---------|---------|------|
| 🟢 PASS |  0.20   | Name |
</details>

```

The table widths expand to the real values. Counts in the sentence are the package’s full counts, not counts after `-slow`. If a positive slow limit hides some passed tests, add `↓ Slowest N passed tests shown (of P)` on the immediately following line. Preserve the blank lines shown, and leave one additional blank line before the final Markdown summary. In no-color mode only the status emoji are omitted; the unconditional package icon `📦`, count check mark `✓`, and optional down arrow remain.

## Spec 16

Color is enabled by default even when standard output is captured rather than attached to a terminal. `-nocolor`, or the presence of a `NO_COLOR` environment variable even if its value is empty, disables every ANSI escape sequence. Disabling color changes no non-color text, ordering, or basic/plain geometry. Width calculations always ignore escape sequences.

When color is enabled in basic or plain output, wrap status words as follows:

```text
PASS    \x1b[92mPASS\x1b[0m
FAIL    \x1b[91mFAIL\x1b[0m
SKIP    \x1b[93mSKIP\x1b[0m
NOTEST  \x1b[93mNOTEST\x1b[0m
```

For passing packages, coverage greater than or equal to 80% is bright green (`92`), coverage greater than 50% but less than 80% is bright yellow (`93`), and positive coverage through exactly 50% is bright red (`91`). Zero coverage and coverage on a failing package are left uncolored. Markdown never ANSI-colors coverage and uses the emoji convention from Spec 15 for status.

## Spec 17

Every package containing failed test results gets a diagnostic section before the summary, even when its authoritative terminal package event is `pass`. Use the full, untrimmed package name. In basic and plain modes, the action word in the heading comes from that terminal package event, so contradictory input can produce a `PASS  package: ...` heading, a `PASS` summary row, nonzero failed-test count, and exit 0. The visible basic/plain heading is a heavy box whose interior for an ordinary failed package is exactly three spaces, `FAIL`, two spaces, `package: `, the package, and three spaces:

```text
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   FAIL  package: example.com/testpkg   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

--- FAIL: TestFail1 (0.10s)

    test.go:20: assertion failed

```

The heavy border uses `\x1b[38;5;103m...\x1b[0m` around each border or border fragment when color is enabled. The heading’s `FAIL` is bright red (nested resets are acceptable only in the canonical sequence produced by applying the status style inside the border style). Each `--- FAIL: Test (N.NNs)` marker is red `\x1b[31m...\x1b[0m`. With color disabled the example is literal as shown.

For every failed test, preserve retained diagnostic text from separate `output` actions, including multiline assertion messages, file/line references, stack traces, Unicode, and nested pass/skip result lines, except for data-race report text discarded as specified in Spec 18. An `Output` field attached directly to a terminal `fail` action is not retained for this section; if that was the test's only diagnostic text, the package heading is still rendered but its body is empty. `=== RUN`, `=== PAUSE`, and `=== CONT` output events are discarded during normal parsing. Move the entire retained `output` action containing a line with `--- FAIL: ` to the top of that test’s rendered block; do not duplicate that line. Lines following the marker in the same action therefore remain immediately after it, ahead of output from earlier actions. For example, separate actions containing `before\n` and then `      --- FAIL: Top/Sub (0.20s)\nafter\n` render the dedented marker, then `after`, a blank line, and then `before`. If Go indented such a fail line, halve the number of leading spaces before `--- FAIL:` using integer division.

In basic/plain failure material, retain non-marker leading indentation and logical blank lines, but render each retained output action as a padded multiline cell: right-pad every physical line to that action’s maximum visible line width, and render a logical blank line as an all-space line of that width. Thus for `--- FAIL: T (0.1s)\n\n    文件.go:2: λ != 終\n        nested\n`, the marker, blank line, and `nested` line receive trailing space padding while the Unicode and leading indentation are retained. Show all failed tests that have retained detail; do not truncate after the first. Sort failure-detail tests lexically by full test name so parents and children group together. Separate tests whose top-level name (text before the first `/`) differs with a horizontal `─` rule of the renderer’s default non-TTY width (96 columns); do not separate members of the same parent/subtest group. In default colored basic/plain output, render this divider faint (`\x1b[2m` before it and `\x1b[0m` after it).

In Markdown, as in basic/plain mode, take the diagnostic heading's action word from the authoritative terminal package event. For a terminal `fail`, replace the heavy heading by `## 🔴 FAIL • FULL_PACKAGE`, or `## FAIL • FULL_PACKAGE` with no color. For a terminal `pass` despite a failed test result, the heading is `## PASS • FULL_PACKAGE` both with color enabled and with no color; it has no status symbol. Then put the complete failure material beginning with `--- FAIL:` in one fenced code block. The exact shape is: heading, blank line, a line containing three backticks, the failure marker, a blank line when diagnostics follow, the retained diagnostics, one additional blank line, a line containing three backticks, two newline characters, and then the Markdown summary table. For a diagnostic ending `test.go:20: assertion failed\n`, the resulting suffix is `test.go:20: assertion failed\n\n```\n\n` before the summary table.

## Spec 18

Detect a panic when retained output begins with `panic: `, or contains `runtime error:` without also containing `as expected`. A panic gets a dedicated section and must not be reduced to an ordinary assertion failure. In basic/plain mode its heading is a heavy box with visible interior:

```text
   PANIC  package: FULL_PACKAGE • FULL_TEST   
```

Preserve the panic message, `[recovered]` text, goroutine dump, function names, source paths, offsets, package-level `FAIL ...` line, and line order. Before rendering, expand every tab in panic text to four literal spaces; thus input `FAIL\tpanic/pkg\t0.1s` is rendered as `FAIL    panic/pkg    0.1s`, and a leading tab on a source-path line becomes four leading spaces. Do not discard a long stack trace. The non-TTY renderer width is 96 columns; long panic text wraps to that width and shorter panic lines are padded as required by the panic panel renderer.

The summary status for that package is `PANIC`; when meaningful test counts and package elapsed are unavailable, show elapsed `0.00s` and `--` for Pass/Fail/Skip. The process exits 1. In Markdown, use a `## 🔴 PANIC • FULL_PACKAGE • FULL_TEST` heading, omitting the red symbol in no-color mode, but do not use a fence or a blank line after the heading. The heading and each panic-text line are right-padded to 96 visible columns, followed by one 96-column all-space line and then the Markdown summary. For no-color panic text `panic: x\ntrace line\n`, output begins with the padded `## PANIC • panic/pkg • TestBoom` line, the padded `panic: x` line, the padded `trace line` line, and the all-space line.

Data races are detected by `WARNING: DATA RACE`. Omit the race report from formatted diagnostic output whether the associated test/package result fails or passes. For a failing test, still render its ordinary failure section and summary; a `--- FAIL:` line at the end of the race-report output still supplies the displayed failure marker. Concretely, for one output action containing `WARNING: DATA RACE\nRead at 0x00 by goroutine 8:\n    race.go:5\nFound 1 data race(s)\n--- FAIL: T (0.1s)\n`, followed by test- and package-level `fail` events, no race-report line appears and the no-color basic failure body is only `       --- FAIL: T (0.1s)\n`. When later test and package events both say `pass`, omit the race report, retain the displayed passing result, and exit 1 as specified in Spec 7.

## Spec 19

`-follow` reconstructs ordinary non-JSON `go test` output from `Output` fields and writes it before formatted results. Preserve retained strings byte-for-byte and in input-event order. Nonverbose follow deliberately filters noisy framework lines after trimming surrounding whitespace for the filter comparison: omit lines beginning `=== RUN`, `=== PAUSE`, `=== CONT`, `=== PASS`, or `=== SKIP`, and omit per-test `--- PASS:` and `--- SKIP:` lines. Do not filter `--- FAIL:` or `=== FAIL` lines, and retain standalone package `PASS` and `FAIL` lines. Keep actual log/diagnostic lines, `? ... [no test files]`, coverage lines, and final `ok  \tPACKAGE\t...` or package failure lines. For a typical passing `fmt` stream, the followed portion is exactly:

```text
    fmt_test.go:1457: skipping; GOMAXPROCS>1
ok  	fmt	0.143s
```

`-follow-verbose` implies follow and instead emits every ordinary `Output` string, in order, including all run/pause/continue/pass/fail markers, race and panic output, package PASS/FAIL lines, coverage, and no-test markers. It must preserve the execution hierarchy and ordering of parallel subtests. Build-event output selected for follow also appears there before it is independently forwarded to standard error as required by Spec 7. A stream containing only `build-output` and `build-fail` therefore writes the build output to both standard output and standard error, then appends `found no go test packages\n` to standard error and exits 1 without a summary.

After either form of follow output, still print detailed tables if requested, failure/panic details, and the final summary. This can intentionally repeat failure information in verbose raw output and in the later formatted failure section.

## Spec 20

`-follow-output PATH` sends the followed raw output to a file instead of standard output. It implies follow, truncates or creates the target with ordinary user-readable/user-writable permissions, flushes and closes it before process exit, and uses the same nonverbose filtering as `-follow` unless `-follow-verbose` is also selected. Formatted test details, diagnostics, progress, and summary remain on standard output.

When both `-follow` and `-follow-output` are present, the file takes precedence: raw lines occur only in the file and are not duplicated on standard output. Re-running against the same path replaces it with the complete deterministic content.

If the output file cannot be created, write the operating-system open error (for example `open /: is a directory`) to standard error, produce no normal processing output, and exit 0.

With `-include-timestamp`, prefix every emitted `Output` field—normally one physical line—whether sent to stdout or a follow-output file with the corresponding event’s `Time`, formatted to RFC3339 whole-second precision, followed by one space. If a single field contains embedded newlines, the prefix occurs once at the start of that field. Do not timestamp tables, progress lines, failure sections, or summaries. For example:

```text
2024-06-20T21:08:33-04:00     fmt_test.go:1457: skipping; GOMAXPROCS>1
2024-06-20T21:08:33-04:00 ok  	fmt	0.143s
```

## Spec 21

`-progress` emits one compact line for every terminal package-level `pass` or `fail` event, in event order, in addition to the final summary. A package-level `skip` event is not a progress trigger, including when preceding output classified the package as no-test; in that case output begins directly with the summary table. It always uses the full untrimmed package name. Its format is:

```text
[STATUS]\t     N.NNs\tPACKAGE
```

The status is normally `PASS` or `FAIL` and follows the color rules in Spec 16; the elapsed value has exactly two decimals and is right-aligned in a field of visible width 10. For example, the colored bytes for a passing package are:

```text
[\x1b[92mPASS\x1b[0m]\t     0.14s\tfmt
```

With `-nocolor` this is `[PASS]\t     0.14s\tfmt\n` and contains no escape bytes. Failed packages produce `[FAIL]...` and preserve the failing exit code. When a package previously recognized as having no tests reaches a package-level `pass` event, that event's progress line uses yellow `SKIP` and appends exactly ` [no test files]` after its package name. A package-level `skip` still emits no progress line. When combined with follow, the raw lines precede the applicable progress line, and the final package table remains last.

## Spec 22

`-compare PREVIOUS_FILE` is an experimental additive mode. Parse the selected current input normally and also parse `PREVIOUS_FILE` using the same package and coverage rules. The current run remains the source of statuses, counts, elapsed values, failure details, and exit status. For a current package having coverage, render `CURRENT% (DELTA%)` when the previous stream has the same full package name: `DELTA` has one decimal, receives a leading `+` only when positive, and is current minus previous. If the previous stream lacks that package, render `CURRENT% (-)`. Packages without current coverage remain `--`. A valid comparison does not suppress packages or turn a passing current run into a failure.

Comparison composes with file input and all ordinary formatting options. The comparison-file argument is mandatory at flag-parse time.

## Spec 23

The following exact examples consolidate the most important byte-level formatting rules.

For input describing two passing tests in package `strings`, package elapsed 3.77, and no coverage, `-nocolor -format plain` must output exactly:

```text
  Status   Elapsed   Package   Cover   Pass   Fail   Skip  
                                                           
   PASS     3.77s    strings    --      2      0      0    
```

The same input with `-nocolor -format markdown` must output exactly:

```text
| Status | Elapsed | Package | Cover | Pass | Fail | Skip |
|--------|---------|---------|-------|------|------|------|
|  PASS  |  3.77s  | strings |  --   |  2   |  0   |  0   |
```

For one package `mypackage` with five passing tests (`TestBeta` 5.00, `TestDelta` 3.00, `TestAlpha` 1.50, `TestEcho` 1.00, `TestCharlie` 0.30), package elapsed 10.80, `-all -slow 3 -nocolor` has this exact structure and ordering:

```text
╭────────┬─────────┬───────────┬───────────╮
│ Status │ Elapsed │   Test    │  Package  │
├────────┼─────────┼───────────┼───────────┤
│  PASS  │  5.00   │ TestBeta  │ mypackage │
│  PASS  │  3.00   │ TestDelta │ mypackage │
│  PASS  │  1.50   │ TestAlpha │ mypackage │
╰────────┴─────────┴───────────┴───────────╯
╭────────┬─────────┬───────────┬───────┬──────┬──────┬──────╮
│ Status │ Elapsed │  Package  │ Cover │ Pass │ Fail │ Skip │
├────────┼─────────┼───────────┼───────┼──────┼──────┼──────┤
│  PASS  │ 10.80s  │ mypackage │  --   │  5   │  0   │  0   │
╰────────┴─────────┴───────────┴───────┴──────┴──────┴──────╯
```

These examples all end with exactly one newline and have no output on standard error.
