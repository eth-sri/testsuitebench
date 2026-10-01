# Executable specification

The required artifact is a single runnable program named exactly `executable`. It implements a `peco`-compatible interactive line filter. Unless a rule below says otherwise, diagnostics go to standard error, selected data goes to standard output, successful completion returns status 0, and setup or validation failure returns status 1. The executable must be self-contained; terminal-driving programs used to exercise it are part of the calling environment, not part of this artifact.

## Spec 1

The command-line form is `executable [options] [FILE]`. It reads newline-delimited records, incrementally filters them in a terminal user interface, and writes the chosen record or records when the user finishes.

It must recognize all of these options:

- `-h`, `--help`
- `--version`
- `--query STRING`
- `--print-query`
- `--rcfile PATH`
- `-b INTEGER`, `--buffer-size INTEGER`
- `--null`
- `--initial-index INTEGER`
- `--initial-filter NAME`
- `--prompt STRING`
- `--layout NAME`
- `--select-1`
- `--exit-0`
- `--select-all`
- `--on-cancel success|error`
- `--selection-prefix STRING`
- `--exec COMMAND`
- `--ansi`
- `--height NUMBER|PERCENT%`

Value options accept either `--name=value` or `--name value`. `-b10`, `-b=10`, and `-b 10` are valid. The compact form consumes every character after `-b` as its value; consequently `-bn` is parsed as buffer-size value `n` and fails integer conversion rather than being reported as an unknown flag. Repeating an option is allowed and the last supplied value wins. Options are recognized even after a positional file name. A standalone `--` is ignored rather than ending option processing, so `-- --version` prints the version. If several positional arguments are present, only the first is used as `FILE`; the rest are ignored.

## Spec 2

`--help` and `-h` print the same plain-text help to standard output and return 0. Help begins with exactly a blank line followed by:

```text
Usage: peco [options] [FILE]

Options:
```

It ends in a newline and contains no ANSI escape sequences. It documents every option in Spec 1. In particular, the descriptions contain these phrases: `show this help message and exit`, `initial value for query`, `path to the settings file`, `print the version and exit`, `number of lines to keep in search buffer`, `expect NUL (\0) as separator for target/output`, `position of the initial index`, `specify the default filter`, `specify the prompt string`, `layout to be used`, `select first item`, `exit immediately`, `select all items`, `specify action on user cancel`, `use a prefix`, `execute command instead of finishing/terminating peco`, `print out the current query`, `enable ANSI color code support`, and `display height`. The buffer-size help entry has no displayed argument metavariable and is exactly `  -b, --buffer-size     number of lines to keep in search buffer`. The layout description names `top-down`, `bottom-up`, and `top-down-query-bottom`. The exec description says that the command is `executed via '/bin/sh -c'` or `'cmd /c'`. Wrapped continuations for the cancel default and selection-prefix default are respectively:

```text
                        default is 'success'. This may change in future versions
                        default is to use colors. This option is experimental
```

Valid options may accompany `--help` without changing this output. Argument parsing still detects an unknown option even when help is present.

`--version` returns 0 and prints one line matching this exact shape:

```text
peco version vMAJOR.MINOR.PATCH (built with goMAJOR.MINOR.PATCH)
```

The peco version must be in the `v0.5.x` series; for example, `peco version v0.5.11 (built with go1.23.2)` is valid. Version processing occurs after syntactic option parsing but before configuration and input setup, so a syntactically valid but nonexistent `--rcfile` does not prevent version output.

## Spec 3

Unknown flags, missing flag arguments, malformed typed values, and invalid enumerated values return 1. An unknown long option `--bogus` is reported as ``unknown flag `bogus'``; an unknown short option `-Z` similarly names `Z`. The unknown-flag line precedes a complete usage/options block, followed by a diagnostic containing `Error: failed to setup peco`. This output is on standard error for ordinary command execution.

A missing value must name the option in the form ``expected argument for flag `--query'``; buffer size uses ``expected argument for flag `-b, --buffer-size'``. If a would-be value begins with `-`, it is treated as an option: for example `--height -5` begins ``expected argument for flag `--height', but got option `-5'``, includes the usage block, and ends with the nested setup diagnostic.

`--initial-index` accepts a syntactically signed decimal integer, including `--initial-index=-1`; a separate negative token may be parsed as another option. A non-integer reports ``invalid argument for flag `--initial-index' (expected int):``. A malformed compact buffer value such as `-bn` begins with ``invalid argument for flag `-b, --buffer-size' (expected int):`` and includes the attempted value in its integer-conversion error. Valid layouts are exactly `top-down`, `bottom-up`, and `top-down-query-bottom`; otherwise report `unknown layout: 'VALUE'`. Valid cancel policies are case-sensitive `success` and `error`; for `--on-cancel invalid-value`, report exactly:

```text
Error: failed to setup peco: failed to apply configuration: invalid --on-cancel value: invalid OnCancel value "invalid-value": must be "success" or "error"
```

Other invalid values use the same nesting with that value substituted. An unknown initial filter is an error ending in `failed to set filter: specified filter was not found`.

## Spec 4

If `FILE` is supplied, input comes from that file. Otherwise, input comes from redirected or piped standard input. If there is no file and standard input is the controlling terminal rather than a supplied stream, exit 1 immediately with:

```text
Error: failed to setup input source: you must supply something to work with via filename or stdin
```

Failure to open a positional file returns 1 and reports:

```text
Error: failed to setup input source: failed to open file for input: open PATH: ...
```

where `PATH` is the first positional argument and the operating-system reason follows it. A zero-byte file is a valid source and can display an empty interactive list unless an immediate-exit option applies.

Split input on LF, CRLF, or mixed line endings. Strip only the record terminator; do not trim record content. An unterminated final record is retained. Empty records, consecutive blank lines, duplicate records, leading/trailing spaces, tabs, punctuation, control characters embedded in a record, Unicode (including emoji, combining marks, right-to-left text, and zero-width characters), and very long records are all valid and retain their content and order. A UTF-8 BOM is tolerated. Invalid UTF-8 must not crash the program; terminal-facing decoded text uses a safe replacement character.

## Spec 5

`-b N`/`--buffer-size N` limits the retained search buffer. With positive `N`, retain the most recently read `N` records in their original order. After a 200-line source has been read completely, `-b 10` therefore exposes lines 191 through 200 in the interactive view. The startup race specific to combining a bounded buffer with `--select-all` is described in Spec 6. If `N` equals or exceeds the number of records, nothing is removed. Zero and negative values mean unlimited. Very large values are accepted.

The configuration property `MaxScanBufferSize` is a number of kilobytes used as the input scanner's maximum record capacity; its default is 256 KiB. Large configured values permit correspondingly long records. Zero or negative values are handled safely and must not make ordinary input crash or hang.

Reading must work for thousands of records and long queries, repeated and concurrent invocations must not share state, and early EOF, signals, or a closed output pipe must be handled without leaving a corrupted terminal.

## Spec 6

Three options affect whether startup finishes without user input. Their checks are not uniformly made against the filtered result set:

- `--select-1` tests the number of source records before applying the initial query/filter. It succeeds and outputs the sole source record when that count is exactly one, even if the initial query does not match it. A query that narrows several source records to one does not trigger the shortcut; with three source records and `--query banana`, interaction is still required.
- `--exit-0`, despite its historical name, returns status 1 with no output when the source is empty. With any input it has no further effect and does not auto-select.
- `--select-all` shortcuts only with an empty initial query; a nonempty `--query`, even one matching the sole input record, enters the normal TUI. With an empty query and an ordinary source that is available at the startup check, it succeeds and outputs all source records in source order; empty input is a successful no-output case. With a positive bounded buffer smaller than a rapidly supplied source, the check races the asynchronous reader: observed runs of a 200-line source with `-b10 --select-all` either enter the TUI or return 0 with an intermediate ten-record moving-window snapshot (for example, lines 25 through 34), rather than necessarily emitting final lines 191 through 200.

When combined, a single source record still lets `--select-1` succeed, while empty input with `--select-1 --exit-0` returns 1. The shortcuts produce only result data, not prompts or terminal-control text. They accept unrelated display options such as layout, height, prompt, selection prefix, and ANSI mode.

## Spec 7

Each input record has a display/search value and an output value. Normally they are identical. `--null` changes a newline record of the form `DISPLAY\0RESULT` so that only `DISPLAY` appears and participates in filtering, while finishing emits `RESULT`. Split only at the first NUL: any further NUL bytes belong to `RESULT`. For example, the single unterminated record `a\0bb\0ccc\0` displays/searches as `a` and emits the bytes `bb\0ccc\0` followed by a newline. If a record has no NUL, its full value is used for both purposes. Empty display or result portions and embedded additional NULs are accepted.

On successful normal completion, output the chosen output values in source order, one per line, always appending `\n` after each value even if the source's final record was unterminated. Do not add other stdout data. With no saved multi-selections, Finish emits the current cursor record; with saved selections, it emits those saved records rather than implicitly adding the cursor record. Cancel emits nothing.

With `--print-query`, a normal Finish or immediate selection writes the exact current query followed by `\n` before any selected output. This includes an empty query, which produces a leading blank line, and preserves spaces, punctuation, backslashes, and Unicode. A no-match normal Finish can therefore still emit the query line. Cancel never prints it.

## Spec 8

The initial query is empty unless `--query` supplies it. A query change re-filters incrementally. Split the query into whitespace-separated terms; repeated spaces create no empty matcher. All positive terms must match the same record (logical AND). A term beginning with one unescaped `-` is negative, and matching it excludes the record. All negative terms are applied as exclusions (logical NOT/OR): a query containing only negative terms starts from all records and removes records matching any negative term.

The spelling `\-foo` means the positive literal term `-foo`. A bare `-` and a double hyphen `--` are positive literal hyphen text, not empty negative expressions. These rules also work with several positive and negative terms. Query parsing preserves the displayed and printed query exactly even though it derives normalized matcher terms.

In literal filters, regexp punctuation such as `.`, `*`, `+`, `?`, `[]`, `{}`, `()`, `|`, `^`, and `$` has no special meaning. Slashes, at signs, quotes, backslashes, tabs, digits, Unicode, and queries longer than any record are processed safely.

## Spec 9

There are six built-in filters in this fixed rotation order:

```text
IgnoreCase -> CaseSensitive -> SmartCase -> IRegexp -> Regexp -> Fuzzy -> IgnoreCase
```

`IgnoreCase` is the default and performs Unicode-aware case-insensitive literal substring matching for every term. `CaseSensitive` performs exact-case literal substring matching. `SmartCase` is case-insensitive if all letters in the complete query are lowercase, but becomes case-sensitive when any uppercase letter is present. Digits and symbols do not independently force case sensitivity.

`--initial-filter NAME` and configuration `InitialFilter` select the starting filter by the exact names above. `peco.RotateFilter`/the default `C-r` advances one position, wraps after Fuzzy, updates the filter name shown in the header, and reruns the query. Starting from any nondefault filter still uses the same circular order, and subsequent query edits retain the current filter. An empty query shows all current-buffer records under every filter.

## Spec 10

`Regexp` treats each positive or negative term as a case-sensitive regular expression using an RE2/Go-like syntax. It supports anchors (`^`, `$`), character classes, `+`, groups, alternation, escapes such as word boundaries, and multiple ANDed terms. `IRegexp` provides the same syntax with case-insensitive matching. `SmartCase` has the case behavior from Spec 9 while retaining literal-term semantics.

An invalid positive or negative regexp is not fatal and does not terminate the UI; that query produces zero results until corrected. Multiple spaces are ignored. Duplicate or overlapping patterns must not corrupt highlighted output. A negative regexp excludes a line if it matches. Literal-filter query punctuation remains quoted rather than being interpreted as regexp syntax.

## Spec 11

`Fuzzy` matches each positive term as an ordered subsequence of Unicode code points: every query character must occur in order but gaps are allowed. A lowercase-only term is case-insensitive; the presence of uppercase makes fuzzy matching case-sensitive. Negative fuzzy terms use the same subsequence principle and exclude their matches. Empty or all-negative fuzzy queries follow Spec 8. With the default `FuzzyLongestSort: false`, matching records retain source order.

With configuration `FuzzyLongestSort: true`, sort matches by fuzzy quality. Favor a stronger/longer contiguous match, then an earlier match start, then a shorter whole record; keep ordering deterministic. Required tie examples include `abcdefghij`, `xabcdefghij`, `xxabcdefghij` for query `abc` in that order, and `abc`, `abcx`, `abcxx` in that order. For query `adg`, the tested ordering begins `abcdefghij`, `abcxxxdefghij`, `ABCDEFGHIJstart`, `abc def ghij scattered`, `a b c d e f g h i j very scattered`, followed by otherwise equivalent matches in increasing prefix position. Matching and ranking operate on Unicode code points rather than UTF-8 bytes.

## Spec 12

When interaction is required, use an ANSI-compatible terminal screen and read keys from the controlling terminal while keeping the supplied file/stdin as the data source. Restore terminal modes and screen state when exiting. Configuration/argument validation and input setup happen before screen initialization. Immediate modes still may initialize and restore the screen when a PTY exists, but their stdout must remain clean.

If a TUI is needed and `TERM` is unset/empty, return 1 with:

```text
Error: failed to initialize screen: failed to create tcell screen: terminal entry not found: term not set
```

If a valid `TERM` is present but `/dev/tty` cannot be opened, return 1 with a diagnostic containing:

```text
Error: failed to initialize screen: failed to initialize tcell screen: open /dev/tty: no such device or address
```

An empty but valid file is renderable in a real terminal as a zero-match screen. `--exit-0` is what turns that case into an immediate status-1 exit.

## Spec 13

The full-screen UI has a query/header row, a results viewport, and a transient message row. With the default 80-column by 25-row terminal, the viewport contains 23 result rows. The header is one terminal row: prompt and query at the left, and the current filter plus pagination right-aligned. Its plain-text shape is:

```text
QUERY>                                                     IgnoreCase [N (P/T)]
```

The default prompt is exactly `QUERY>`. A nonempty query follows it after one space. `N` is the current match count; `P/T` is the one-based current/total page pair. Even zero results display `[0 (1/1)]`. Page capacity is the available result-row count, not a hard-coded record count. For 100 records at 23 per page, pages show `[100 (1/5)]` through `[100 (5/5)]`; page two contains records 24–46. Filtering updates count and page count immediately.

Rows not occupied by results or messages are cleared. The input caret is visibly styled at its Unicode cursor position. Current record, saved records, query text, prompt, matched spans, ANSI spans, and zoom context have distinguishable terminal styles, although capture as plain text still yields the underlying characters. Status messages and pending-key hints appear right-aligned in the final terminal row and later clear. `SuppressStatusMsg: true` suppresses this transient message row's messages.

## Spec 14

Layout controls vertical placement only:

- `top-down` (default): header first, then records in source/result order from the top.
- `bottom-up`: the header is near the bottom, records are bottom-aligned above it, and their visual order is reversed (the first result is closest to the header).
- `top-down-query-bottom`: records remain in normal order from the top while the header is at the bottom.

The transient status row remains at the terminal bottom where applicable. All layouts work with filtered and unfiltered results, short lists, pagination, cursor navigation, custom prompts, and inline mode. `--prompt` overrides the prompt string. Arbitrary empty, whitespace-containing, punctuation-containing, long, and Unicode prompts are accepted. An explicitly empty prompt falls back safely to the default rather than making the interface unusable.

Lines wider than the terminal are clipped, not wrapped into extra result rows. Tabs expand according to terminal tab stops. Wide Unicode characters consume their proper display-cell width, combining/zero-width characters do not create spurious columns, and clipping never splits a displayed character. Erasing or shortening a query/result clears stale characters from the screen.

## Spec 15

The current result cursor starts at zero-based `--initial-index`, default 0. Valid in-range values position the cursor and scroll the viewport enough to show it; index 0 chooses the first record and index `N-1` chooses the last of `N`. Out-of-range positive or negative values are handled safely and never cause an index error or change what `--select-all` emits. With no results, navigation is a no-op.

`SelectDown` and Down/C-n move one result forward; `SelectUp` and Up/C-p move one backward. Moving past the last wraps to the first, and moving above the first wraps to the last. `ScrollPageDown` and Right/Pgdn move by one viewport page, preserving relative cursor position where possible; `ScrollPageUp` and Left/Pgup do the reverse, including page wrap at the ends. In the default 80-by-25 terminal, one Pgdn from `item-00` in a 50-record list selects `item-23`, and three consecutive Pgdn inputs wrap back to `item-00`. Home/`ScrollFirstItem` shows the first item and End/`ScrollLastItem` shows the last. On a one-item or one-page list, page and arrow operations are safe no-ops apart from cursor styling. Cursor and page remain coherent when a filter reduces or restores the list.

## Spec 16

Printable keys insert Unicode code points at the query caret and rerun filtering. Query editing is code-point based:

- `ForwardChar` (default C-f) and `BackwardChar` (C-b) move by one code point and stop at the ends.
- `BeginningOfLine` (C-a) and `EndOfLine` (C-e) move to the query bounds.
- `DeleteForwardChar` (C-d or Delete when bound) removes the code point under the caret.
- `DeleteBackwardChar` (Backspace, BS2, or C-8) removes the preceding code point.
- `KillEndOfLine` (C-k) deletes from the caret through the end.
- `KillBeginningOfLine` (C-u) deletes everything before the caret and moves it to zero.
- `DeleteBackwardWord` (C-w) removes the preceding word together with adjacent separating whitespace.
- `RefreshScreen` (C-l) clears/redraws and reruns the query without changing logical state.
- `ToggleQuery` (C-t) temporarily shows the unfiltered current buffer while saving the query; invoking it again restores and reapplies the saved query.

Deletion and movement at a boundary are no-ops. Middle insertion/deletion and multibyte Unicode behave correctly. The input handler accepts terminal encodings for arrows, Home, End, Delete, Backspace, Page Up/Down, Tab/Backtab, function keys, Escape, Enter, and Ctrl-modified keys.

## Spec 17

Enter invokes `peco.Finish`: return 0 and emit output as in Spec 7. Escape and C-c invoke `peco.Cancel`: restore the terminal, emit no result/query output, and return 0 under the default `OnCancel: success` or 1 under `OnCancel: error`. `--on-cancel` overrides configuration. Cancel while range selection is active may first leave that mode as described in Spec 18; the explicit `CancelRangeMode` action does not terminate the process.

`--exec COMMAND` changes Finish. Instead of terminating, collect the same selected lines that Finish would emit, append their newlines, and provide them to the command's standard input. Execute with `/bin/sh -c COMMAND` on POSIX and `cmd /c COMMAND` on Windows so pipes, redirection, quoting, and environment expansion work. Set these variables for the command: `PECO_QUERY` (exact query), `PECO_FILENAME` (input filename, or empty for stdin), `PECO_LINE_COUNT` (source record count), and `PECO_MATCHED_LINE_COUNT` (the number of selected lines supplied to this command, not the current filtered-result count). Thus finishing on `alpha` with one selected line among two query matches sets the counts to `3` and `1` for a three-record source. After the subprocess exits, redraw and continue interacting; the user must Cancel to leave exec mode. The command may write files or produce its own terminal output.

## Spec 18

Selections are keyed to source records, not merely display text, so duplicate lines remain independently selectable. `ToggleSelection` adds/removes the current record without moving. The default keymap declares C-Space as `ToggleSelectionAndSelectNext`, which toggles then advances when invoked, but an incoming terminal NUL byte (`0x00`, the usual C-Space/C-@ encoding) is ignored by this executable and does not invoke that binding; binding the action to a distinguishable terminal key such as C-v makes it invocable. In particular, NUL, C-n, NUL, Enter over `a`, `b`, `c` emits only `b`; sending NUL twice and Enter over two duplicate rows emits only one `dup`; and sending 100 NUL bytes and Enter emits only `item-000` rather than building 100 saved selections. `SelectAll` saves all current results; `SelectVisible` saves only records on the current viewport page—23 records in the default 80-by-25 full-screen terminal, so a view beginning at `line-00` selects through `line-22`; `SelectNone` clears all saved selections. Removing one item preserves the others. Output iteration is always ascending source order, regardless of selection order or cursor position, and handles at least 100 selections when selection actions are actually invoked.

`ToggleRangeMode` starts an anchor at the current index and selects the inclusive range as navigation moves. A second toggle commits/appends that range. `CancelRangeMode` leaves range mode and resets its anchor while preserving selections already established outside the canceled extension. Range operations remain valid when the anchor is at index zero. With `StickySelection: true`, saved selections persist through query changes; otherwise selections that cease to belong to the current result set may be cleared.

Without `--selection-prefix`, colors/styles indicate the current and saved rows. With prefix `>`, the cursor row is rendered as `> RECORD`, an unselected non-cursor row as `  RECORD`, and a saved non-cursor row as `* RECORD`. More generally, the current row uses the supplied prefix followed by a separating space, non-cursor rows use equal-width padding, and saved non-cursor rows use `*` in the marker column. Prefixes such as `>>>`, `[X] `, `✓ `, empty strings, whitespace, and Unicode are accepted. Configuration `SingleKeyJump.ShowPrefix: true` prefixes visible choices using the repeatable hint sequence `a s d f g h j k l z x c v b n m q w e r t y ...`; `ToggleSingleKeyJump` enables hit-a-hint selection using those keys.

## Spec 19

`--height` selects inline mode at the bottom of the existing terminal without switching permanently to a full-screen alternate buffer, thereby preserving scroll history. An absolute decimal value means that many result rows; two chrome rows (header and status) are added. A percentage is 1–100 percent of total terminal height including chrome. Whitespace around the whole specification is ignored. Clamp the resolved area to the terminal, and enforce at least three total rows (one result plus two chrome), so `--height=1` is usable. Very large absolute values are accepted and clamped.

Reject zero, negative, fractional, malformed, or multiply-percent values such as `0`, `-1`, `1.5`, `abc`, `10x`, `50%%`, `0%`, `-1%`, `50.5%`, and percentages above 100. Required diagnostics include:

```text
Error: failed to setup peco: failed to apply configuration: failed to parse height specification: invalid height specification: "invalid"
Error: failed to setup peco: failed to apply configuration: failed to parse height specification: height must be positive: "0"
Error: failed to setup peco: failed to apply configuration: failed to parse height specification: height percentage must be positive: "0%"
Error: failed to setup peco: failed to apply configuration: failed to parse height specification: height percentage must be positive: "-50%"
Error: failed to setup peco: failed to apply configuration: failed to parse height specification: height percentage must not exceed 100: "101%"
```

Inline navigation, pagination, filtering, selection, initial query/index, ANSI display, custom prompt, and all three layouts behave the same as full screen. For example, five result rows over 50 results yields ten pages; after moving down ten times, the viewport is items 11–15 with page `3/10`.

## Spec 20

Configuration may be strict JSON (`.json`) or YAML (`.yaml` or `.yml`). JSON comments and trailing commas are invalid; YAML comments and ordinary quoted/unquoted scalars are supported. A zero-byte JSON file is invalid JSON, while the empty object `{}` and other minimal valid files use defaults. Unknown top-level keys and nested objects are ignored. Type mismatches in known structured fields are reported rather than panicking.

Choose at most one configuration file, first found in this order:

1. The explicit `--rcfile`; if missing or unreadable, fail rather than falling back.
2. `$XDG_CONFIG_HOME/peco/config.json`, then `config.yaml`, when that environment variable is nonempty.
3. `$HOME/.config/peco/config.json`, then `config.yaml`.
4. For directories in `$XDG_CONFIG_DIRS` from left to right, the first existing `peco/config.json` or `peco/config.yaml`.
5. `$HOME/.peco/config.json`, then `config.yaml`.

No discovered file is not an error. Command-line values override their corresponding file values. A missing explicit file error has the shape `Error: failed to setup peco: failed to setup configuration: failed to read config file: failed to open file PATH: open PATH: ...`. Malformed formats identify `failed to decode JSON` or `failed to decode YAML`. In particular, an unfinished JSON object ending after a property colon reports `... failed to decode JSON: unexpected EOF`, and the malformed JSON text consisting of `{"invalid json` plus a newline reports exactly:

```text
Error: failed to setup peco: failed to setup configuration: failed to read config file: failed to decode JSON: invalid character '\n' in string literal
```

For this malformed YAML:

```yaml
Prompt: "TEST>"
InitialFilter: Fuzzy
  IndentationError: this is bad YAML
```

the diagnostic, including source context, is:

```text
Error: failed to setup peco: failed to setup configuration: failed to read config file: failed to decode YAML: [2:16] mapping value is not allowed in this context
   1 | Prompt: "TEST>"
>  2 | InitialFilter: Fuzzy
   3 |   IndentationError: this is bad YAML
                      ^
```

A top-level invalid layout reports `invalid layout type: VALUE`. If `Keymap` maps an action key to an object instead of a string, report exactly `Error: failed to setup peco: failed to setup configuration: failed to read config file: failed to decode JSON: json: cannot unmarshal object into Go struct field Config.Keymap of type string`.

## Spec 21

Recognized configuration fields and defaults/effects are:

- `Prompt` (`"QUERY>"`), `InitialFilter` (`"IgnoreCase"`), `Layout` (`"top-down"`), `OnCancel` (`"success"`), `SelectionPrefix`, `Height`, and `ANSI` map to the same-named CLI behaviors.
- `FuzzyLongestSort` and `StickySelection` default to false and act as described above.
- `SuppressStatusMsg` defaults to false.
- `MaxScanBufferSize` defaults to 256 (KiB).
- `Keymap`, `Action`, `Style`, `CustomFilter`, and `SingleKeyJump` use the structures in later specs.

`BufferSize` is accepted as the configuration counterpart of `--buffer-size`. Benign extra fields such as `UseCache`, `VerticalAnchor`, and `CycleViews` may be ignored. A JSON `null` for an optional scalar leaves its initialized default unchanged. A value of the wrong non-null type produces a clear decode/configuration error and never a crash.

Invalid known values are errors. Examples include:

```text
Error: failed to setup peco: failed to apply configuration: failed to populate initial filter: failed to set filter: specified filter was not found
Error: failed to setup peco: failed to setup configuration: failed to read config file: invalid layout type: invalid-layout-name
Error: failed to setup peco: failed to setup configuration: failed to read config file: failed to decode JSON: invalid OnCancel value "invalid-value": must be "success" or "error"
```

## Spec 22

`Keymap` is an object mapping key descriptions to action names. Configured bindings override defaults. Mapping a key to the literal string `-` unbinds it. Key descriptions are case-sensitive where shown and include C-a through C-z, C-2 through C-8, C-[, C-], C-~, C-_, C-\\, C-/, C-Space/C-@, F1 through F12, Esc, Tab, Backtab, Enter, Insert, Delete, BS, BS2, Home, End, Pgup, Pgdn, ArrowUp/Down/Left/Right, and mouse buttons. `M-`, `C-`, and `S-` modifiers can be used on supported keys and combined.

Comma-separated names define a multi-key sequence, for example `C-x,C-s` or `F1,F2`; the longest matching sequence wins. While a prefix is pending, show its key name (for example `C-x` or `F1`) in the status row. Completing it invokes the action. If an ordinary key breaks the sequence, abandon the prefix and process that key normally, including inserting a printable character. Escape is an exception: when it breaks a pending sequence, it only clears the prefix and is consumed rather than being reprocessed as `Cancel`; a second Escape is required to cancel. An unbound key may display its name but performs no former default action.

`Action` maps custom names to arrays of built-in or custom action names, executed in array order. This supports combinations such as ToggleSelection followed by SelectNext/SelectDown. Action names are case-sensitive. Missing actions fail during setup; for example:

```text
Error: failed to setup peco: failed to apply configuration: failed to populate keymap: failed to apply key bindings: failed to resolve action name peco.NonExistentAction: could not resolve peco.NonExistentAction: no such action
```

For a custom action `MyAction` whose child is missing, the diagnostic uses one outer `failed to resolve action name` wrapper and then a `could not resolve` leaf; for example, it is exactly:

```text
Error: failed to setup peco: failed to apply configuration: failed to populate keymap: failed to apply key bindings: failed to resolve action name MyAction: could not resolve peco.InvalidAction: no such action
```

Recursive custom actions are detected with a bounded resolution depth, and the diagnostic likewise omits every intermediate traversal wrapper. For a self-recursive `Action1`, it is exactly:

```text
Error: failed to setup peco: failed to apply configuration: failed to populate keymap: failed to apply key bindings: failed to resolve action name Action1: could not resolve Action1: deep recursion
```

Known deprecated aliases `SelectNext`/`SelectPrevious` and `SelectNextPage`/`SelectPreviousPage` still resolve and may display a deprecation message.

## Spec 23

The built-in action names needed by keymaps are case-sensitive and include:

```text
peco.ForwardChar                  peco.BackwardChar
peco.BeginningOfLine              peco.EndOfLine
peco.DeleteForwardChar            peco.DeleteBackwardChar
peco.DeleteBackwardWord           peco.KillBeginningOfLine
peco.KillEndOfLine                peco.RefreshScreen
peco.ScrollPageDown               peco.ScrollPageUp
peco.ScrollFirstItem              peco.ScrollLastItem
peco.SelectUp                     peco.SelectDown
peco.SelectPrevious               peco.SelectNext
peco.ToggleSelection              peco.ToggleSelectionAndSelectNext
peco.SelectNone                   peco.SelectAll
peco.SelectVisible                peco.ToggleRangeMode
peco.CancelRangeMode              peco.ToggleQuery
peco.RotateFilter                 peco.ToggleSingleKeyJump
peco.FreezeResults                peco.UnfreezeResults
peco.ZoomIn                       peco.ZoomOut
peco.Finish                       peco.Cancel
```

The default keymap is: Esc and C-c = Cancel; Enter = Finish; C-f = ForwardChar; C-b = BackwardChar; C-a = BeginningOfLine; C-e = EndOfLine; C-d = DeleteForwardChar; C-k = KillEndOfLine; C-u = KillBeginningOfLine; BS/BS2/C-8 = DeleteBackwardChar; C-w = DeleteBackwardWord; C-g = SelectNone; C-n/Down = SelectDown; C-p/Up = SelectUp; C-r = RotateFilter; C-t = ToggleQuery; C-l = RefreshScreen; C-Space = ToggleSelectionAndSelectNext; Left/Pgup = ScrollPageUp; Right/Pgdn = ScrollPageDown.

## Spec 24

`Style` is an object whose recognized fields are `Basic`, `SavedSelection`, `Selected`, `Query`, `QueryCursor`, `Matched`, `Prompt`, and `Context`. Each value is an array of tokens. Empty arrays are accepted and retain a usable/default style. Recognize:

- foreground: `default`, `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, decimal palette strings `0`–`255`, and `#RRGGBB`;
- background: `on_default`, `on_black`, `on_red`, `on_green`, `on_yellow`, `on_blue`, `on_magenta`, `on_cyan`, `on_white`, `on_0`–`on_255`, and `on_#RRGGBB`;
- attributes: `bold`, `underline`, `reverse`, and background-form `on_bold`.

Attributes combine. If several foreground or several background tokens occur, the last of that category wins. JSON and YAML forms behave identically. Apply Basic to ordinary rows, SavedSelection to saved rows, Selected to the cursor row, Query and QueryCursor to the editor, Matched to matched spans, Prompt to the prompt, and Context to context-only rows.

## Spec 25

With `--ansi` or configuration `ANSI: true`, parse terminal CSI SGR data out of the display/search text while retaining its style spans for terminal rendering and retaining the original record bytes for selected output. Thus `\x1b[31mred\x1b[0m` can be found by query `red`, is rendered red, and is emitted with its original escape sequence. ANSI parsing and `--null` display/result splitting compose correctly.

Support/reset at least SGR 0 (including empty `ESC[m`), bold 1, underline 4, reverse 7, basic foreground 30–37, foreground reset 39, basic background 40–47, background reset 49, bright colors 90–97 and 100–107, 256-color `38;5;N`/`48;5;N`, and truecolor `38;2;R;G;B`/`48;2;R;G;B`. Safely recognize or ignore without leaking parameters into text the faint/italic/blink/conceal/strike attributes 2, 3, 5, 8, and 9; double underline 21; their specific resets 22–29; and framed/encircled/overline 51–53. Multiple parameters and rapidly nested/mixed changes combine in order. Resetting only foreground or background preserves unrelated attributes.

Non-SGR CSI sequences are removed from searchable/display text in ANSI mode. Unknown, malformed, incomplete, boundary-positioned, or empty sequences and invalid color parameters must not crash or hang; continue with usable text, leaving an incomplete tail harmlessly representable. Unicode and invalid UTF-8 intermixed with ANSI are safe. Without ANSI mode, escape sequences do not contribute visible/searchable characters or styling; ordinary visible substrings still match, and result output removes terminal-control sequences while preserving the text content.

## Spec 26

`CustomFilter` is an object keyed by the filter name shown in the UI. Each value has `Cmd` (executable path/name), optional string-array `Args` (default `["$QUERY"]`), and optional positive `BufferThreshold`. Register custom filters after the six built-ins, preserving configuration order for rotation, and allow any number of them. `$QUERY` appearing as an argument or inside an argument is replaced with the exact current query.

When a custom filter has a nonempty query, start `Cmd` directly with the substituted arguments, send the original unaltered current buffer records to its standard input as newline records, and treat its stdout lines—in stdout order—as the complete result set. The external program controls semantics, so grep, case-insensitive grep, inverse grep, awk, sed, and executable script wrappers can all produce different valid results. No match highlighting is required for custom-filter output. An empty query shows the whole current buffer. `BufferThreshold` permits processing in batches of that many records while preserving the same combined result and ordering. A nonexistent/failing command yields zero results for a nonempty query; it must not crash or terminate the interactive process.

## Spec 27

`FreezeResults` snapshots the current nonempty result set as a new base buffer, clears the query, and displays `Results frozen`. Further queries filter only that frozen base. It may be invoked repeatedly for progressive narrowing. `UnfreezeResults` discards every frozen stage, returns to the original source, clears the query, and displays `Results unfrozen`. Attempting to freeze zero results is a no-op with `Nothing to freeze`.

`ZoomIn` is available only from a genuinely filtered result set. It replaces the view with every matched source record plus the three source records before and after each match, merges overlapping context ranges, preserves source order, remembers the pre-zoom cursor/view, and styles context rows. For example, five distributed matches may expand to 17 unique rows. `ZoomOut` restores the exact pre-zoom filtered view and cursor. Zooming an unfiltered view is a no-op with `Nothing to zoom into`; zooming twice says `Already zoomed in`; zooming out when not zoomed says `Not zoomed in`. Freezing while zoomed freezes the expanded context buffer and reports `Results frozen`.
