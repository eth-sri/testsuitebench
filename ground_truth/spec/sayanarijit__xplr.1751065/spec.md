# Behavioral specification for `executable`

The required artifact is one executable file named exactly `executable`. It implements the observable command-line and terminal behavior below. All paths are Unix paths, all textual data is UTF-8, and examples use JSON notation for values and YAML notation for application-state dumps. Unless a rule explicitly says otherwise, successful operations exit with status 0 and produce no diagnostic on standard error; validation and parse failures exit with status 1 and put the diagnostic on standard error.

## Spec 1

`executable` is a terminal file explorer named `xplr`, version `1.1.0`. It must work both as a normal subprocess and while attached to a pseudo-terminal. Operations which terminate during argument processing (`--help`, `--version`, `-M`, and `-m`) do not require a terminal. A normal interactive launch opens the current directory and remains alive, repainting when the terminal size or state changes. It must render correctly at least at 80x24 and 120x40 cells.

Interactive operation obtains keyboard input from the controlling terminal, not ordinary standard input (standard input may have been used for path input). If an interactive launch has no controlling terminal, it fails promptly and nonzero; on Linux the diagnostic includes `No such device or address`. ANSI alternate-screen, cursor, color, and clear-screen sequences are allowed. Terminal cleanup must restore the screen/cursor on every quit. Unknown/unbound keys, including F11, F12, and `@`, are ignored without exiting or corrupting the current mode.

## Spec 2

`--version` and `-V` have identical successful behavior: standard output is exactly the following 10 characters plus the final newline, and standard error is empty:

```text
xplr 1.1.0
```

There are no additional blank lines. Recognized mode flags before `--version` are accepted. `--version --` also prints the version. Argument validation is not globally bypassed by version: `--version --invalid` is an error rather than a version request. In contrast, when `--help` occurs before another otherwise recognized early-exit flag, as in `--help --version`, help is printed.

## Spec 3

`--help` and `-h` exit 0, write nothing to standard error, and write exactly this text (including indentation, wrapping, spelling, and one final newline):

```text
xplr 1.1.0
Arijit Basu <hi@arijitbasu.in>
A hackable, minimal, fast TUI file explorer

USAGE:
    xplr [FLAG]... [OPTION]... [PATH] [SELECTION]...

FLAGS:
  -                            Reads new-line (\n) separated paths from stdin
  --                           Denotes the end of command-line flags and options
      --force-focus            Focuses on the given <PATH>, even if it is a directory
  -h, --help                   Prints help information
  -m, --pipe-msg-in            Helps safely passing messages to the active xplr
                                 session, use %%, %s and %q as the placeholders
  -M, --print-msg-in           Like --pipe-msg-in, but prints the message instead of
                                 passing to the active xplr session
      --print-pwd-as-result    Prints the present working directory when quitting
                                 with `PrintResultAndQuit`
      --read-only              Enables read-only mode (config.general.read_only)
      --read0                  Reads paths separated using the null character (\0)
      --write0                 Prints paths separated using the null character (\0)
  -0  --null                   Combines --read0 and --write0
  -V, --version                Prints version information

OPTIONS:
  -c, --config <PATH>             Specifies a custom config file (default is
                                    "$HOME/.config/xplr/init.lua")
  -C, --extra-config <PATH>...    Specifies extra config files to load
      --on-load <MESSAGE>...      Sends messages when xplr loads
      --vroot <PATH>              Treats the specified path as the virtual root

ARGS:
  <PATH>            Path to focus on, or enter if directory, (default is `.`)
  <SELECTION>...    Paths to select, requires <PATH> to be set explicitly
```

Help takes effect when reached before later recognized flags, including in `--on-load Quit --help`, `--vroot /tmp --help`, and `-0 --help`. A token after the end-of-options marker is never help: `-- --help` treats `--help` as a path and fails without printing the `USAGE:` help section.

## Spec 4

Recognized flags and options are `-h/--help`, `-V/--version`, `-m/--pipe-msg-in`, `-M/--print-msg-in`, `-c/--config`, `-C/--extra-config`, `--on-load`, `--vroot`, `--force-focus`, `--print-pwd-as-result`, `--read-only`, `--read0`, `--write0`, `-0/--null`, the special stdin token `-`, and the end-of-options token `--`. Flags may appear before or after the initial path unless `--` has ended option parsing. `-0` and `--null` enable both read0 and write0. The read-only, force-focus, print-PWD, read0, and write0 flags may be combined.

`-c` consumes exactly one path. Repeated `-c` is accepted and the last value is the main config. `-C` consumes one or more consecutive non-flag paths, and repeated occurrences accumulate paths in order. `--on-load` consumes zero or more consecutive message arguments until the next recognized flag; repeated occurrences preserve command-line order. In tested invocations each nonempty `--on-load` normally has one message. A help/version flag following `-C` or `--on-load` is not consumed by it.

`--` ends all flag recognition. Thus `-- --invalid-flag`, `-- -c ...`, `-- --version`, and `-- -- /tmp` attempt to use the first post-marker token as a path. A nonexistent relative token is resolved against the process working directory in its diagnostic.

An unrecognized option errors. For the exact input `--invalid-flag`, standard output is empty and standard error is exactly:

```text
error: invalid argument: "--invalid-flag", try `-- "--invalid-flag"` or `--help`
```

with a final newline. `-x` similarly includes `invalid argument: "-x"`. Missing values include these usage fragments: `usage: xplr -c PATH`, `usage: xplr --config PATH`, `usage: xplr --vroot PATH`, `usage: xplr -M FORMAT [ARGUMENT]...`, `usage: xplr --print-msg-in FORMAT [ARGUMENT]...`, `usage: xplr -m FORMAT [ARGUMENT]...`, and `usage: xplr --pipe-msg-in FORMAT [ARGUMENT]...`. A bare `--extra-config` is nonzero, except that a following early `--help` may terminate successfully. A bare `--on-load` is instead an empty message list and continues to TUI startup; without a controlling terminal it exits 1, writes no standard output, and writes exactly `error: No such device or address (os error 6)` plus a newline to standard error.

## Spec 5

Every supplied path is validated before a `-M`/`-m` request or TUI startup succeeds. The empty string is invalid and its diagnostic contains `empty string passed`. A missing path exits 1 with empty standard output and exactly `error: path doesn't exist: ` followed by the normalized absolute path and a newline on standard error. This applies to the initial path, selections, stdin-provided paths, main config, every extra config, and vroot. For example, initial path `/nonexistent/path/does/not/exist` produces exactly `error: path doesn't exist: /nonexistent/path/does/not/exist` plus a newline, while `-c /nonexistent/config.lua` produces exactly `error: path doesn't exist: /nonexistent/config.lua` plus a newline. A config path that is a directory also fails. A vroot must be an existing directory.

Relative paths are resolved from the process working directory. Normalize repeated `/`, trailing `/` other than root, `.` components, and `..` components. Preserve the literal bytes/characters of actual path components, including leading/trailing spaces, embedded spaces, `$`, quotes, newlines, long names, Japanese text, and emoji. `/` remains `/`. Do not resolve away the spelling of a valid symlink used as the initial path.

With no initial path, use `.`. With an initial directory, the ordinary behavior is to enter it, making its normalized absolute spelling the explorer PWD. With an initial regular file or symlink-to-file, browse its parent and focus that named entry. With an initial symlink-to-directory, enter through the symlink and retain the symlink spelling as PWD. `--force-focus` changes a directory initial path into a focused node: browse its parent rather than entering it. A broken or circular symlink supplied as the initial path fails cleanly.

When a path is explicitly followed by more positional paths, the first is the initial path and the remainder form the initial selection. Directories with no entries, only hidden entries, read-only permissions, deep nesting (at least 20 components), 100 entries, or many file types must initialize without special-case failure.

## Spec 6

The special option token `-` reads additional path arguments from standard input. By default, split on newline bytes. With `--read0` or `-0/--null`, split on NUL bytes. A final delimiter does not create an additional empty path, but an empty field in the middle of newline input is an invalid empty path. Validate every resulting field. Newline mode must support spaces and Unicode; NUL mode must preserve embedded newline bytes in filenames.

Output paths use newline delimiters by default and NUL delimiters with `--write0` or `-0/--null`. This applies to printed result/selection paths and the temporary path-list files exposed to commands. A delimiter follows every emitted path.

## Spec 7

Without `--config`, absence of a user config is not an error; built-in defaults are used. `--config PATH` selects a main Lua config. `-C/--extra-config` loads every named Lua config after the main config, in command-line order, so later assignments can extend or override earlier ones. All named config files must be validated for existence, even when another named file is valid. Paths with spaces or Unicode are supported, and large files and Lua single-line (`--`) and long (`--[[...]]`) comments are accepted.

A loaded operational config is Lua and is evaluated with a preinitialized global `xplr` table. A global `version` string is supported. Versions `1.0.0` and `1.1.0` are compatible with this executable; ordinary Lua reassignment applies, so the last assignment is effective. Configs can read and assign nested fields such as `xplr.config.general.show_hidden`, `read_only`, `enable_mouse`, `enable_recover_mode`, and `paginated_scrolling`, using Lua booleans, strings, numbers, tables, and functions. A minimal `version = "1.1.0"` config is valid. Early help/version processing may succeed with an otherwise minimal comment-only config because no interactive configuration behavior is needed.

## Spec 8

For interactive custom layouts, support the deprecated compatibility form assigned to `xplr.config.layouts.builtin.default`:

```lua
{ CustomContent = { title = STRING, body = BODY } }
```

and honor `xplr.config.general.initial_layout = "default"`. `BODY` may be:

- `StaticParagraph = {render = STRING}`: split the string at newlines.
- `StaticList = {render = {STRING, ...}}`: one item per row.
- `StaticTable = {widths = {{Percentage=N}, ...}, col_spacing=N, render = {{CELL, ...}, ...}}`.
- `DynamicParagraph`, `DynamicList`, or `DynamicTable` with the same structural output but `render` naming a Lua function such as `custom.render_list` in `xplr.fn.custom`.

Dynamic functions receive `ctx` with `ctx.app.pwd`, `ctx.screen_size.width/height`, `ctx.layout_size.width/height`, and zero-based `ctx.scrolltop`. At an 80x24 full-screen custom layout, both sizes are 80x24 and `scrolltop` is 0. Execute normal Lua used by these renderers, including table construction, `..`, `tostring`, and `string.format`.

Custom content occupies the full terminal. Draw a rounded Unicode box exactly 80 columns by 24 rows: a title in the top border (`╭ TITLE ` followed by `─` fill and `╮`), 22 interior rows (`│`, 78 content cells, `│`), then the bottom border. Text begins in the first interior cell and is space padded. Static paragraph content `Hello, World!\nThis is a test paragraph.` under title `Test Title` therefore occupies the first two body rows. A static list preserves `First item`, `Second item`, `Third item with unicode: ✓ ✗ ☀ ★`, and `Fourth item`. Percentage tables preserve rows, use the requested column spacing, and align columns. In particular the 30/30/40, spacing-2 table begins:

```text
╭ Product Table ───────────────────────────────────────────────────────────────╮
│Name                     Price                     Stock                      │
│Widget A                 $19.99                    42                         │
│Widget B                 $29.99                    18                         │
│Gadget C                 $49.99                    7                          │
```

The dynamic examples must render `Current directory: <absolute PWD>` and `Layout size: 80x24`; list rows `Item 1: Screen is 80x24`, `Item 2: Layout is 80x24`, `Item 3: Scroll top is 0`, `Item 4: Dynamic content!`; and a 40/60, spacing-3 table beginning exactly as follows (then blank padded rows and the common bottom border):

```text
╭ Dynamic Table ───────────────────────────────────────────────────────────────╮
│Property                          Value                                       │
│Screen Width                      80                                          │
│Screen Height                     24                                          │
│Layout Width                      80                                          │
│Layout Height                     24                                          │
```

## Spec 9

`-M FORMAT [ARGUMENT]...` and `--print-msg-in ...` parse and normalize one external message without launching the TUI. YAML flow/block syntax and JSON syntax (a YAML subset) are accepted. On success, write the canonical value as compact UTF-8 JSON to standard output, with no spaces added and no trailing newline, and write nothing to standard error. Unit variants serialize as a JSON string; variants with data serialize as a one-key object. Examples, all exact, are:

```text
Quit                                      => "Quit"
ExplorePwd                                => "ExplorePwd"
PrintPwdAndQuit                           => "PrintPwdAndQuit"
Select                                    => "Select"
SelectPath: /path/to/file                 => {"SelectPath":"/path/to/file"}
FocusNextByRelativeIndex: 5               => {"FocusNextByRelativeIndex":5}
FocusByIndex: 999999999                   => {"FocusByIndex":999999999}
SwitchMode: custom_mode                   => {"SwitchMode":"custom_mode"}
SwitchLayoutBuiltin: default              => {"SwitchLayoutBuiltin":"default"}
SetInputBuffer: "test input"              => {"SetInputBuffer":"test input"}
BufferInput: "text"                       => {"BufferInput":"text"}
ChangeDirectory: /tmp                     => {"ChangeDirectory":"/tmp"}
SetVroot: /virtual/root                   => {"SetVroot":"/virtual/root"}
CallLua: custom.function                  => {"CallLua":"custom.function"}
LuaEval: "return 1 + 1"                   => {"LuaEval":"return 1 + 1"}
BashExec0: "echo hello"                   => {"BashExec0":"echo hello"}
Search: pattern                           => {"Search":"pattern"}
SearchRegex: ".*\\.txt$"                  => {"SearchRegex":".*\\.txt$"}
LogInfo: "test message"                   => {"LogInfo":"test message"}
UpdateInputBuffer: GoToStart              => {"UpdateInputBuffer":"GoToStart"}
UpdateInputBuffer: {SetCursor: 5}         => {"UpdateInputBuffer":{"SetCursor":5}}
UpdateInputBuffer: {InsertCharacter: a}   => {"UpdateInputBuffer":{"InsertCharacter":"a"}}
Call0: {command: touch, args: [foo]}      => {"Call0":{"command":"touch","args":["foo"]}}
AddNodeSorter: {sorter: BySize, reverse: true} => {"AddNodeSorter":{"sorter":"BySize","reverse":true}}
AddNodeFilter: {filter: RelativePathDoesContain, input: test} => {"AddNodeFilter":{"filter":"RelativePathDoesContain","input":"test"}}
AddNodeFilterFromInput: RelativePathDoesContain => {"AddNodeFilterFromInput":"RelativePathDoesContain"}
RemoveNodeSorter: BySize                  => {"RemoveNodeSorter":"BySize"}
ToggleNodeFilter: {filter: RelativePathIs, input: test.txt} => {"ToggleNodeFilter":{"filter":"RelativePathIs","input":"test.txt"}}
```

Equivalent JSON input normalizes to the same output. Preserve embedded escaped quotes, decoded `\n` inside strings (re-escaped in the one-line JSON), Unicode characters, regex backslashes, spaces, and punctuation. Also accept and normalize the unit variants `Refresh`, `ClearScreen`, `EnableMouse`, `DisableMouse`, and `ToggleMouse`, and string-valued `LogSuccess`, `LogWarning`, and `LogError`.

## Spec 10

Before message parsing, expand placeholders left-to-right using the positional arguments:

- `%s` inserts the argument text directly into the YAML/JSON template.
- `%q` inserts the argument as a safely quoted YAML string, escaping quotes, backslashes, newlines, Unicode, spaces, and YAML metacharacters so parsing recovers exactly the original string.
- `%%` inserts one literal `%` and consumes no argument.

Every `%s` or `%q` consumes exactly one argument. If a placeholder lacks a value, fail with a diagnostic containing `error: xplr -m: placeholder missing value` and the relevant column. If arguments remain after all placeholders, fail with `error: xplr -m: too many positional values, not enough positional placeholders`. These diagnostics use `xplr -m` even for `-M`.

For example `Call: {command: %s, args: [%s, %s]}` plus `bash`, `-c`, `echo test` yields `{"Call":{"command":"bash","args":["-c","echo test"]}}`; `LogInfo: test %%` yields `{"LogInfo":"test %"}`; and `%q` around `test with 'quotes' and "double"` round-trips that exact string. Expansion can itself produce invalid YAML: `LogInfo: %%` becomes a scalar beginning with `%` and therefore fails with a YAML/error diagnostic.

## Spec 11

Messages are case-sensitive and strongly typed. Empty input fails with `error: expected value at line 1 column 1`. Unknown variants fail with `error: unknown variant \`NAME\`, expected one of ...` and include at least `ExplorePwd`, `ExploreParentsAsync`, `Quit`, and `PrintResultAndQuit` in the expected list. `{Foo: Bar}` reports the unknown variant `Foo` and location `at line 1 column 6`. `explorepwd` is not an alias for `ExplorePwd`. A string-valued message given an integer, such as `{"FocusPath":123}`, reports `invalid type: integer \`123\`, expected a string`; a mapping in place of the string reports `invalid type: map, expected a string`. `FocusByIndex: -1` reports `invalid value: integer \`-1\`, expected usize`. Required object fields, malformed flow mappings/JSON, `LogInfo:` with null, and malformed YAML all fail with empty standard output. The command-call `args` field is an exception: it is optional, while `command` remains required. Thus `Call0: {command: echo}` succeeds and prints exactly `{"Call0":{"command":"echo"}}` with no newline, whereas `Call0: {args: []}` fails with `missing field \`command\``. For the exact malformed input `{"FocusPath": "/path/to/file"`, stderr is exactly `error: xplr -m: yaml: did not find expected ',' or '}' at line 2 column 1, while parsing a flow mapping` plus a newline.

Recognize the following external-message names and their natural argument shapes, so they may be formatted by `-M` and dispatched by `--on-load`: `ExplorePwd`, `ExplorePwdAsync`, `ExploreParentsAsync`, `TryCompletePath`, `ClearScreen`, `Refresh`, `FocusNext`, `FocusNextSelection`, `FocusNextByRelativeIndex`, `FocusNextByRelativeIndexFromInput`, `FocusPrevious`, `FocusPreviousSelection`, `FocusPreviousByRelativeIndex`, `FocusPreviousByRelativeIndexFromInput`, `FocusFirst`, `FocusLast`, `FocusPath`, `FocusPathFromInput`, `FocusByIndex`, `FocusByIndexFromInput`, `FocusByFileName`, `ScrollUp`, `ScrollDown`, `ScrollUpHalf`, `ScrollDownHalf`, `ChangeDirectory`, `Enter`, `Back`, `LastVisitedPath`, `NextVisitedPath`, `PreviousVisitedDeepBranch`, `NextVisitedDeepBranch`, `FollowSymlink`, `SetVroot`, `UnsetVroot`, `ToggleVroot`, `ResetVroot`, `SetInputPrompt`, `UpdateInputBuffer`, `UpdateInputBufferFromKey`, `BufferInput`, `BufferInputFromKey`, `SetInputBuffer`, `RemoveInputBufferLastCharacter`, `RemoveInputBufferLastWord`, `ResetInputBuffer`, `SwitchMode`, `SwitchModeKeepingInputBuffer`, `SwitchModeBuiltin`, `SwitchModeBuiltinKeepingInputBuffer`, `SwitchModeCustom`, `SwitchModeCustomKeepingInputBuffer`, `PopMode`, `PopModeKeepingInputBuffer`, `SwitchLayout`, `SwitchLayoutBuiltin`, `SwitchLayoutCustom`, `Call`, `Call0`, `CallSilently`, `CallSilently0`, `BashExec`, `BashExec0`, `BashExecSilently`, `BashExecSilently0`, `CallLua`, `CallLuaSilently`, `LuaEval`, `LuaEvalSilently`, `Select`, `SelectAll`, `SelectPath`, `UnSelect`, `UnSelectAll`, `UnSelectPath`, `ToggleSelection`, `ToggleSelectAll`, `ToggleSelectionByPath`, `ClearSelection`, `AddNodeFilter`, `RemoveNodeFilter`, `ToggleNodeFilter`, `AddNodeFilterFromInput`, `RemoveNodeFilterFromInput`, `RemoveLastNodeFilter`, `ResetNodeFilters`, `ClearNodeFilters`, `AddNodeSorter`, `RemoveNodeSorter`, `ReverseNodeSorter`, `ToggleNodeSorter`, `ReverseNodeSorters`, `RemoveLastNodeSorter`, `ResetNodeSorters`, `ClearNodeSorters`, `Search`, `SearchFromInput`, `SearchFuzzy`, `SearchFuzzyFromInput`, `SearchFuzzyUnordered`, `SearchFuzzyUnorderedFromInput`, `SearchRegex`, `SearchRegexFromInput`, `SearchRegexUnordered`, `SearchRegexUnorderedFromInput`, `ToggleSearchAlgorithm`, `EnableSearchOrder`, `DisableSearchOrder`, `ToggleSearchOrder`, `AcceptSearch`, `CancelSearch`, `EnableMouse`, `DisableMouse`, `ToggleMouse`, `StartFifo`, `StopFifo`, `ToggleFifo`, `LogInfo`, `LogSuccess`, `LogWarning`, `LogError`, `Debug`, `Quit`, `PrintPwdAndQuit`, `PrintFocusPathAndQuit`, `PrintSelectionAndQuit`, `PrintResultAndQuit`, `PrintAppStateAndQuit`, and `Terminate`. `StopFifo` is a unit variant. `StartFifo` and `ToggleFifo` are string-valued newtype variants, not unit variants: `StartFifo: /tmp/fifo` and `ToggleFifo: /tmp/fifo` print `{"StartFifo":"/tmp/fifo"}` and `{"ToggleFifo":"/tmp/fifo"}` respectively, while either bare name fails with `invalid type: unit variant, expected newtype variant`.

## Spec 12

`-m/--pipe-msg-in` performs the same substitution, parsing, validation, and compact JSON serialization as `-M`. If environment variable `XPLR_PIPE_MSG_IN` is unset, print the canonical JSON followed by one newline to stdout; for example, `-m 'LogInfo: hello'` writes exactly `{"LogInfo":"hello"}\n`. If it is set, its value names an existing writable communication file. The file's first byte is its record delimiter, normally newline or NUL. Append the canonical JSON message followed by that delimiter, leaving existing bytes intact, and emit nothing to stdout or stderr. Multiple invocations append multiple messages. A nonexistent pipe or an unreadable/unwritable pipe fails nonzero with a nonempty diagnostic. If the named file is empty, exit 1 with empty stdout and exactly `error: failed to detect delimmiter` plus a newline on stderr; the reference spells `delimmiter` with two `m` characters.

## Spec 13

After initialization, dispatch `--on-load` messages sequentially before waiting for keyboard input. Parse them using the typed YAML/JSON message rules, with the command-scalar exception in Spec 16. Invalid YAML or an unknown message is a nonzero startup error. A terminating message stops further interactive waiting.

The explorer has an absolute `pwd`, an initial PWD, an ordered visible node list, a zero-based focus index (0 even for an empty list), a path selection, a mode, layout, input buffer, filters, sorters, search state, logs, and visit history. Default visible nodes exclude names beginning with `.` using filter `{filter: RelativePathDoesNotStartWith, input: "."}`. Default sorters are directory-first (`ByCanonicalIsDir`, reverse true), then case-insensitive relative path (`ByIRelativePath`, reverse false), producing stable alphabetical traversal. The first visible node is initially focused.

Navigation is bounded/wrapping as required to remain valid: `FocusFirst`, `FocusLast`, next/previous, relative index, filename, and path update focus; scrolling does not corrupt it. `ChangeDirectory` enters the named existing directory and refreshes nodes. `Enter` enters a focused directory, while `Back` returns to its parent but may not escape a vroot. `SetVroot` sets an existing directory boundary; unset/toggle/reset act on that state. Selection messages select/unselect/toggle focused or named paths, select all visible nodes, or clear selection. Filters and sorters add/remove/toggle/reset/clear their typed entries and immediately refresh ordering. Mode/layout/input/mouse/log messages update their corresponding state without crashing.

## Spec 14

Quit/output messages have these effects:

- `Quit` exits 0 without printing a result.
- `PrintPwdAndQuit` prints the absolute current PWD and exits.
- `PrintFocusPathAndQuit` prints the absolute focused path and exits.
- `PrintSelectionAndQuit` prints selected absolute paths in selection order and exits.
- `PrintResultAndQuit` prints selected paths when selection is nonempty, otherwise the focused path; if `--print-pwd-as-result` was supplied, it instead prints the current PWD. It then exits.
- `Terminate` exits promptly and must not hang.

Use the output delimiter from Spec 6. With one ordinary file in a directory, the default result is that file. Changing directory before `PrintResultAndQuit --print-pwd-as-result` prints the changed directory. Vroot never makes printed paths relative: results remain normalized absolute paths. Selecting `file1.txt` and then printing the result includes its absolute path.

`PrintAppStateAndQuit` exits 0 and prints a UTF-8 YAML document. It must contain a `{` somewhere (flow-style empty mappings are acceptable), and contain at minimum top-level `bin`, `version`, `config`, `pwd`, `initial_pwd`, `vroot`, `directory_buffer`, `selection`, `mode`, `layout`, `input`, `pid`, `session_path`, `pipe`, `explorer_config`, `logs`, and `history`. `directory_buffer` has `parent`, `nodes`, `total`, and `focus`; `explorer_config` has `filters`, `sorters`, and `searcher`. No later prose or terminal frame may follow the document.

## Spec 15

Each node in the application-state YAML contains at least:

```yaml
parent: ABSOLUTE_PARENT
relative_path: NAME
absolute_path: ABSOLUTE_PATH
extension: LAST_SUFFIX_WITHOUT_DOT_OR_EMPTY
is_dir: BOOLEAN
is_file: BOOLEAN
is_symlink: BOOLEAN
is_broken: BOOLEAN
is_readonly: BOOLEAN
mime_essence: STRING
size: INTEGER
human_size: STRING
permissions: {user_read: BOOLEAN, user_write: BOOLEAN, user_execute: BOOLEAN, group_read: BOOLEAN, group_write: BOOLEAN, group_execute: BOOLEAN, other_read: BOOLEAN, other_write: BOOLEAN, other_execute: BOOLEAN, sticky: BOOLEAN, setgid: BOOLEAN, setuid: BOOLEAN}
canonical: MAPPING_OR_NULL
```

Use lstat metadata for the node itself. A symlink's `size` is the byte length of its stored link text, not its target: links containing `target.txt`, `link1`, and `link2` have sizes 10, 5, and 5. Follow an arbitrary finite symlink chain for `canonical`; the mapping describes the final target and includes at least `absolute_path`, `is_file`, and `is_dir`. A regular non-symlink also has a non-null canonical mapping matching itself. A broken intermediate link or cycle sets `is_symlink: true`, `is_broken: true`, both file/dir false, and `canonical: null`. A link resolving to a directory is visibly usable as a directory.

Extension is the portion after the last dot (`file.tar.gz` => `gz`, `file.backup.2024.tar.bz2` => `bz2`); a dotless file has `extension: ''`. MIME essences required are `inode/directory` for directories, `text/plain` for ordinary `.txt`, `application/octet-stream` for `.dat`, and `application/x-sh` for `.sh`; a dotless unknown file may use the empty string. File sizes are exact bytes. Human sizes use decimal SI units and two significant decimal digits as observed: 0 => `0 B`, 1 => `1 B`, 1024 => `1.02 kB`, 1048576 => `1.05 MB`. Preserve special/Unicode names verbatim in YAML values and absolute paths.

## Spec 16

`Call`, `Call0`, `CallSilently`, and `CallSilently0` take `{command: STRING, args: [STRING...]}`, with `args` optional and equivalent to an empty argument list for execution. In `-M` input these fields are strongly typed: `Call: {command: false, args: []}` fails because the command is a YAML boolean. The `--on-load` decoder instead accepts an unquoted scalar in this field as command text. In particular, `--on-load 'Call: {command: false, args: []}'` executes the command named `false`; its nonzero status is ignored, and a following `PrintResultAndQuit` still prints the focused path and exits 0. Execute the command directly with exactly that argv in the current explorer PWD and wait for completion. `BashExec`, `BashExec0`, `BashExecSilently`, and `BashExecSilently0` take a shell string and execute it through Bash with normal pipes, redirects, quoting, substitutions, variable expansion, and stderr behavior. Non-silent calls temporarily leave/redraw the TUI as needed and expose child stdout and stderr to the terminal. Silent calls suppress child terminal output but still perform filesystem effects. `0` variants populate communication path-list files with NUL rather than newline delimiters. Empty argv arrays are valid. A child nonzero status or nonexistent child command is logged/ignored for control flow: subsequent messages still run and the explorer can exit 0. Commands lasting at least one second are awaited.

Before each child command, create/update communication files and export at least these nonempty-or-defined environment variables: `XPLR_FOCUS_PATH`, `XPLR_SESSION_PATH`, `XPLR_PIPE_MSG_IN`, `XPLR_PIPE_SELECTION_OUT`, `XPLR_PIPE_RESULT_OUT`, `XPLR_PIPE_DIRECTORY_NODES_OUT`, `XPLR_PIPE_LOGS_OUT`, `XPLR_PIPE_HISTORY_OUT`, `XPLR_PIPE_GLOBAL_HELP_MENU_OUT`, `XPLR_MODE`, `XPLR_PID`, `XPLR_INITIAL_PWD`, `XPLR_APP_VERSION`, `XPLR_INPUT_BUFFER`, and `XPLR_FOCUS_INDEX`. Also expose `XPLR` as the executable path. The selection-out file contains every selected absolute path and the directory-nodes-out file every visible absolute node path, one record each with the call's delimiter. For three visible files, `wc -l < "$XPLR_PIPE_DIRECTORY_NODES_OUT"` in newline mode reports 3.

After a child exits, read complete records newly written to `XPLR_PIPE_MSG_IN` and dispatch them before the next on-load message. Thus a child writing `Select` followed by the delimiter causes the focused file to be selected before `PrintSelectionAndQuit`.

## Spec 17

The default TUI uses Unicode rounded boxes and has a left 70% column and right 30% column. At 80x24 this means a 56-column left side and 24-column right side, with adjacent borders and no gap. The left side occupies rows 1-3 with `Sort & filter (N)`, rows 4-21 with the directory table, and rows 22-24 with `Input [MODE]` when input is active or `Logs [MODE]` otherwise. `N` is the total number of configured node filters and sorters; the initial one filter and two sorters make the exact title `Sort & filter (3)`, and adding the reverse-size sorter changes it to `Sort & filter (4)`. Search state does not add to this count. The right side occupies rows 1-7 with `Selection` and rows 8-24 with `Help [MODE]`. The first and last row of every panel are rounded borders; its other rows begin and end with `│`. Text which exceeds the interior is clipped, and unused cells are spaces.

The directory panel visibly includes the absolute PWD in its title, the visible count in parentheses, and rows with zero-based index, focus/selection marker, node-type glyph (`ƒ` for a file), name, six compact permission characters, human size, and abbreviated modification date. Its header is ` inde ╭─── path               perm   size  modified` at 56 columns. Default sort/filter text is exactly `rel!^. › [c]dir↑ › [i]rel↓`. The focused node uses `▸[` immediately before `ƒ ` and `]` immediately after the name. A selected nonfocused file row places the tree connector first, then one space, then `{ƒ NAME}`; for example, an ordinary row contains `├ {ƒ file2.txt}` and the last row contains `╰ {ƒ file5.txt}`. Tree connectors are `├` except `╰` for the last visible row. The default screen includes `Help [default]` and `Logs [default]`.

At 120x40, launching in `/workspace` must show `/workspace`, `Help [default]`, and `Logs [default]`. At any supported size `j` or Down moves focus down and visibly changes the frame; `k` or Up moves it up and visibly changes it again. `q` exits to the invoking shell within three seconds. A file initial path is displayed and focused; launching a subdirectory displays its children. `--read-only` still permits navigation and selection. `--force-focus DIR` displays and focuses the directory in its parent.

The default key bindings relevant here are: `j`/Down next, `k`/Up previous, `l`/Right enter, `h`/Left back, `q` quit, Space or `v` toggle selection then move next, `V` select/toggle all, `/` enter fuzzy search, Ctrl-r within search toggles fuzzy/regex, `f` filter mode, `s` sort mode, `:` action mode, `g` go-to mode, Ctrl-w layout mode, and a digit starts number mode and appends to its input. Escape pops the current mode; escaping search cancels the search and restores all nodes.

## Spec 18

Some menu modes replace the entire 80x24 screen with a full-screen help box. Their visible rows and ordering are exact as follows; blank rows fill through row 23 and the bottom border is row 24. Keys and help text occupy the first and second aligned columns.

Action mode (`:`), title `Help [action to]`:

```text
!                                shell
c                                create
e                                open in editor
f1                               global help menu
l                                logs
m                                toggle mouse
p                                edit permissions
q                                quit options
s                                selection operations
v                                vroot
[0-9]                            go to index
```

Go-to mode (`g`), title `Help [go to]`:

```text
f                                follow symlink
f1                               global help menu
g                                top
i                                initial $PWD
p                                path
x                                open in gui
```

Layout mode (Ctrl-w), title `Help [switch layout]`:

```text
1                                default
2                                no help menu
3                                no selection panel
4                                no help or selection
f1                               global help menu
```

Filter mode (`f`) retains the normal panels but changes titles to `Help [filter]` and `Logs [filter]`; its help rows, as clipped by the 24-column panel, are `R          relative pa`, `back       remove last`, `ctrl       reset filte`, `ctrl       clear filte`, `f1         global help`, and `r          relative pa`. Sort mode similarly uses `Help [sort]`/`Logs [sort]` and rows `!          reverse sor`, `C          by created`, `E          by canonica`, `L          by last mod`, `M          by canonica`, `N          by node typ`, `R          by relative`, `S          by size rev`, `back       remove last`, `c          by created`, `ctrl       reset sorte`, `ctrl       clear sorte`, `e          by canonica`, `ente       submit`, `f1         global help`. Escape returns to default mode and headings.

## Spec 19

In layout mode, key `2` selects “no help menu”: the right column is one full-height `Selection` panel, while `Sort & filter`, directory table, and `Logs [default]` remain on the left; `Help [default]` is absent. Key `3` selects “no selection panel”: the right column is one full-height `Help [default]` panel, while the left panels remain; the word `Selection` is absent. The default help panel is a clipped key/help list beginning, in order, with:

```text
(          prev deep b
)          next deep b
.          show hidden
/    ctrl- search
:          action
?    f1    global help
G          go to botto
V    ctrl- select/unse
c          copy to
ctrl       duplicate a
ctrl tab   next visite
ctrl       next select
ctrl       last visite
ctrl       prev select
ctrl       refresh scr
ctrl       clear selec
ctrl       switch layo
d          delete
down j     down
ente       quit with r
f          filter
g          go to
```

With five files `file1.txt` through `file5.txt` of sizes 100 through 500 bytes, `V` shows `Selection (5)`, lists `./file1.txt` through `./file5.txt` in the selection panel, marks file2-file5 with braces while file1 remains focused with brackets, and changes the log title to `Logs [default] {5 sel}`. The order is file1 through file5.

Pressing `s` then uppercase `S` adds the reverse-size sorter identifier, changes the panel title to `Sort & filter (4)`, and makes the sort/filter row exactly `rel!^. › [c]dir↑ › [i]rel↓ › size↑`; the files appear from 100 B through 500 B, with file1 before file5, and mode stays `sort`.

Typing `1`, `0` in default mode enters `number` mode without immediately jumping. It displays `Input [number]` containing `:10`, `Help [number]`, and the help rows `down j     to down`, `ente       to index`, `f1         global help`, `k    up    to up`, `[0-9       input`. For 15 alphabetically ordered `file1.txt` through `file15.txt`, the displayed order follows natural numeric creation/order expected by the explorer fixture: file1, file2, ..., file9, file10, ..., file15, with focus still on index 0 until submission.

## Spec 20

Search mode begins with `/` and fuzzy search. Its prompt is `Input [search]` containing `/PATTERN`. The sort/filter title remains `Sort & filter (3)`: the configured filter/sorter count is unchanged. While search is active, the row suppresses the two default sorter tokens but retains the dotfile-filter token, so its exact text is `rel!^. › fzy:PATTERN↓`. Fuzzy matching is Unicode-aware, case-insensitive, and treats the pattern as an ordered subsequence with gaps. Literal spaces/special characters are supported. Rank best/most direct matches first: for `test`, `testfile.txt` precedes `fuzzy_match_test.txt`. Empty fuzzy search leaves all visible nodes. Escape cancels it, removes the `fzy:` indicator, and restores the original node count.

Within search mode Ctrl-r switches to case-sensitive regular-expression matching without changing the input and the indicator becomes `reg:PATTERN↓`. Support ordinary regex syntax including `.`, escaped dots/brackets, anchors, character classes, `+`, grouping, and alternation. Examples: `.*\.log` yields exactly four names `file1.log`, `file2.log`, `file10.log`, `file100.log`; uppercase `README` does not match lowercase `readme.txt`; `\.txt$` excludes `.md`/`.yaml`; `file[0-9]+\.log` matches all numeric log names; and `\.(yaml|yml)$` matches both config extensions.

For five names apple, banana, cherry, date, elderberry, typing `/ban` displays only `banana.txt`, a count of `(1)`, `fzy:ban↓`, and the prompt `/ban`; apple and cherry are absent. The search help panel is `Help [search]` and, clipped to its width, lists in order: `ctrl       toggle sear`, `ctrl       fuzzy searc`, `ctrl down  down`, `ctrl up    up`, `ctrl       regex searc`, `ctrl       sort (no se`, `ctrl       toggle orde`, `ente       submit`, `esc        cancel`, `f1         global help`, `left       back`, `righ       enter`, `tab        toggle sele`.

## Spec 21

Filesystem refresh and TUI/state output must remain robust for symlink chains and cycles, filenames approaching 255 bytes, paths at least 16 levels deep, names containing quotes/dollar signs/spaces/newlines/Unicode, zero-byte and megabyte files, an empty directory, and at least 100 entries. Hidden entries remain absent from both ordinary display and search unless the default dotfile filter is toggled off. Counts always refer to currently visible nodes.

Modification times are displayed as an abbreviated local date such as `Mon Apr 13`; permissions are rendered compactly from actual mode bits (for example ordinary mode 0644 appears `rw-r--`). Directories and symlinks must never cause recursive traversal merely to render one directory. Any permission, stat, MIME, or child-command failure is handled as a diagnostic/log entry rather than a panic or infinite loop.

## Spec 22

The executable must be responsive to automation: argument-only operations return promptly; on-load sequences ending in a print/quit message terminate without requiring a keystroke; interactive frames become visible within about two seconds; ordinary key transitions settle within a fraction of a second; and quitting completes within three seconds. The controlling-PTY sequence `BashExec: "printf CHILD-OUT; printf CHILD-ERR >&2"` followed by `Quit` is an observed timing-sensitive exception: terminal output contains both `CHILD-OUT` and `CHILD-ERR`, but exact replays have both exited 0 promptly and remained alive until killed. Do not require prompt termination for this sequence. Do not emit debug banners, prompts, progress messages, Python/Rust tracebacks, or unrelated text on stdout/stderr. In pseudo-terminal operation, terminal control bytes may surround TUI output, but requested result/state/child-command content must remain intact and discoverable after ANSI escape removal.
