# Serpl executable specification

The required artifact is a single runnable program named exactly `executable`. It is a UTF-8 terminal application for recursively searching and replacing text in a project directory. All behavior below is observable behavior of that artifact; no repository source code or documentation is assumed to exist beside it.

## Spec 1

`executable` has two non-interactive information modes and one interactive mode:

- `executable --help` and `executable -h` print help and terminate successfully without opening a terminal UI.
- `executable --version` and `executable -V` print version/configuration information and terminate successfully without opening a terminal UI.
- Any invocation which is not short-circuited by help or version attempts to start the interactive search-and-replace UI. The project root defaults to the process's current working directory and can be changed with `-p PATH`, `-pPATH`, `-p=PATH`, `--project-root PATH`, or `--project-root=PATH`.

All ordinary informational output is valid UTF-8 on standard output. Argument and startup errors go to standard error. Information modes must be fast and deterministic across repeated and concurrent invocations and must work with minimal environments and regardless of `TERM`, `LANG`, `PWD`, `EDITOR`, `PAGER`, and data-directory environment settings.

## Spec 2

Help output is byte-for-byte the following text, including blank lines, spacing, capitalization, and the final newline:

```text
A simple terminal UI for search and replace, ala VS Code

Usage: executable [OPTIONS]

Options:
  -p, --project-root <PATH>  Path to the project root [default: .]
  -h, --help                 Print help
  -V, --version              Print version
```

The short and long help flags produce identical standard output, exit with status 0, and produce no standard error.

## Spec 3

Version output has exactly five non-trailing lines separated as follows and ends in a newline:

```text
serpl 0.3.4- (YYYY-MM-DD)

Authors: Yassine Bridi <ybridi@gmail.com>

Config directory: CONFIG_DIR
```

`YYYY-MM-DD` is a real, fixed build date represented by four digits, two digits, and two digits. It remains identical on every call to a given executable. `CONFIG_DIR` is resolved as follows:

1. If `SERPL_CONFIG` is set, use its value exactly.
2. Otherwise, if `XDG_CONFIG_HOME` is set, use `XDG_CONFIG_HOME/serpl`.
3. Otherwise, use `HOME/.config/serpl` when `HOME` is available, or a stable platform-appropriate fallback when it is not.

`SERPL_CONFIG` takes precedence over `XDG_CONFIG_HOME`. `SERPL_DATA` and `XDG_DATA_HOME` do not alter the reported configuration directory. The short and long version flags produce identical output, status 0, and no standard error.

## Spec 4

Arguments are case-sensitive, are not prefix-abbreviated, and are processed from left to right. `-V` is version while `-v` is unknown; `--HELP`, `--Version`, and `--hel` are unknown. Help or version short-circuits parsing when encountered: for example, `--help --badflag` prints help successfully, `--version extra-positional` prints version successfully, and `--version -- --badflag` prints version successfully. Conversely, an invalid item before help is an error, so `--badflag --help` does not print help.

An option which needs a value consumes its next token before that token can act as an option. Thus `--project-root --version` is a missing-value error. After a valid project-root value, a later help/version flag can still short-circuit successfully. In a short-option group, `-p` consumes the remainder as its value (`-pV` means project root `V`), while a preceding `h` short-circuits (`-hp /tmp` prints help). `--` ends option parsing; because there are no positional arguments, a token after `--` is rejected unless parsing was already short-circuited.

The project-root option may occur only once, counting short and long spellings as the same option. Its value must not be empty. Literal `~` and `$HOME` text is not expanded by the program. Valid paths may be relative or absolute and may contain spaces, punctuation, repeated dashes, Unicode, numeric-only components, hidden components, trailing slashes, `.` or `..`, and may name a symlink to a directory. Relative paths are interpreted from the process working directory.

## Spec 5

Command-line syntax errors exit with status 2, write nothing to standard output, and use the following error vocabulary and formatting:

```text
error: unexpected argument '--invalid-flag' found

Usage: executable [OPTIONS]

For more information, try '--help'.
```

Only the first invalid argument needs to be reported. The corresponding short-option form names that short option, such as `unexpected argument '-x' found`. A missing or empty project root is:

```text
error: a value is required for '--project-root <PATH>' but none was supplied

For more information, try '--help'.
```

Supplying the option twice is:

```text
error: the argument '--project-root <PATH>' cannot be used multiple times

Usage: executable [OPTIONS]

For more information, try '--help'.
```

Flags which take no value reject equals syntax. For example, `--help=foo` reports `unexpected value 'foo' for '--help' found; no more were expected`, uses `Usage: executable --help`, and gives the same help hint. `--version=bar` behaves analogously with `bar`, `--version`, and `Usage: executable --version`. Every parser error ends with a newline.

For a long option which is a close spelling of a valid option, the parser inserts a suggestion and changes the usage line to that suggested option. These two cases are byte-for-byte:

```text
error: unexpected argument '--Version' found

  tip: a similar argument exists: '--version'

Usage: executable --version

For more information, try '--help'.
```

```text
error: unexpected argument '--hel' found

  tip: a similar argument exists: '--help'

Usage: executable --help

For more information, try '--help'.
```

Both exit with status 2 and write nothing to standard output. `--proj` is a third close-spelling case; it is not accepted as an abbreviation. Its output is byte-for-byte:

```text
error: unexpected argument '--proj' found

  tip: a similar argument exists: '--project-root'

Usage: executable --project-root <PATH>

For more information, try '--help'.
```

It exits with status 2 and writes nothing to standard output. Unknown options other than the three close spellings specified above use the generic form.

## Spec 6

Interactive mode requires a usable terminal but help/version do not. In a pipe or captured non-TTY, a syntactically valid interactive invocation exits with status 1 and reports a graceful error on standard error. After terminal color escapes are removed and the operating-system-specific detail following `0:` is ignored, its shape is exactly:

```text
serpl error: Something went wrong
Error: 
   0:
```

No arguments is a request to start the UI, not an argument error. The same is true for an accepted valid project-root option. A nonexistent root, a regular file used as the root, an inaccessible root, or an unsafe path such as one containing embedded newlines must fail nonzero rather than panic. When an actual terminal is available, even an empty directory starts the UI. If a directory disappears or cannot be searched after startup, the UI remains responsive and presents an empty result set rather than crashing.

## Spec 7

User configuration is optional. The program works with built-in defaults when the configuration directory or file is absent or when the selected file contains an empty top-level object. In interactive mode, an existing zero-byte `config.json5` or one containing invalid syntax is instead a fatal startup error: the program exits nonzero through the normal `serpl error: Something went wrong` report, with a JSON5 parser diagnostic beneath `Error:`. It does not open the UI or fall back to defaults. Help and version still short-circuit configuration loading and succeed with such a file present. User configuration may be supplied as `config.json5`, `config.json`, `config.yaml`, `config.toml`, or `config.ini`, but selection when several coexist is not JSON5-first. For the following observed combinations, the selected file is exact: JSON plus YAML selects `config.yaml`; YAML plus TOML selects `config.toml`; and TOML plus INI selects `config.ini`. With valid `config.json5`, malformed `config.json`, and malformed `config.yaml` all present, `config.json` is selected and startup reports `key must be a string at line 1 column 3 in cfg/config.json`. JSON5 accepts line/block comments and trailing commas. A valid partial user configuration is merged with defaults. Unknown fields, unknown keybinding actions, invalid style values, empty keybinding/style sections, and duplicate entries do not produce a panic or backtrace; key-name parse failures instead have the crash behavior in Spec 8.

Malformed formats do not all share the JSON5 error path. In particular, with valid `config.json` containing `{}` and `config.yaml` containing `: : invalid yaml`, the YAML file is selected and startup exits with status 1, no standard output, and the crash reporter on standard error. After terminal escapes are removed, that report begins `Well, this is embarrassing.` and includes:

```text
The application panicked (crashed).
Message:  internal error: entered unreachable code
```

It neither falls through to JSON nor emits the normal `serpl error: Something went wrong` report for this malformed YAML case. With valid YAML plus malformed TOML, the TOML file is selected and its parse error names `cfg/config.toml`; with valid empty TOML plus malformed INI, the INI file is selected and its parse error names `cfg/config.ini`.

The supported top-level concepts are `keybindings`, `styles`, and optional initial search/replace mode settings. Configuration loading must not change the five-line form of version output.

## Spec 8

The canonical keybinding map uses strings such as `"<Ctrl-c>"` as keys and action names such as `"Quit"` as values. Parsing is case-insensitive for modifier and named-key names. It accepts ordinary single-byte printable ASCII characters, digits, space, hyphen/minus, and these named keys: Esc, Enter, Tab, Backtab, Backspace, Delete, Insert, Home, End, PageUp, PageDown, Left, Right, Up, Down, and F1 through F12. Bare `<` and `>` are exceptions: they are parsed as malformed angle-bracket syntax rather than as single-character keys. A map containing all 94 printable non-space ASCII characters plus 16 Ctrl bindings therefore aborts through the crash reporter; because map traversal order varies, repeated starts report `Unable to parse` for either the `<` or the `>` entry. `Escape` is not an alias for `Esc`: both `<Escape>` and plain `escape` abort interactive startup through the crash reporter with the detail `Unable to parse escape`. A non-ASCII character is likewise not accepted merely because it is one printable character; for example, `Ā` as a binding key aborts startup rather than opening the UI. It accepts Ctrl, Alt, and Shift singly or together in any reasonable order, including forms such as `<Ctrl-Alt-q>`, `<Alt-Ctrl-z>`, `<Shift-Ctrl-s>`, `<Shift-Alt-x>`, and `<ctrl-shift-s>`. It also accepts adjacent multi-key sequences such as `<g><g>`, as well as permissive plain forms such as `ctrl-c`, `alt-q`, `f5`, or `q`. The plain configuration key `shift-tab` does not bind the terminal Backtab sequence `ESC-[Z`: with `shift-tab` mapped to `Quit`, sending that sequence leaves the process running and performs the default reverse pane-focus navigation.

Recognized action names include the defaults used elsewhere in this document plus Quit, ShowHelp/Help, Refresh, Suspend, Resume, Render, Tick, ProcessReplace, LoopOverTabs, and BackLoopOverTabs. Large maps are accepted when all their keys parse. A map of 110 distinct non-ASCII character keys does not; startup aborts on an offending key through the crash reporter. A bad binding never makes `--help` or `--version` fail.

## Spec 9

The only accepted top-level group keys in a nonempty `styles` object are `Normal` and `Input`; either starts the UI when it contains a `text` property. Pane/context keys `Home`, `Search`, `Replace`, and `Preview` are rejected. The loader lowercases the rejected key in its fatal startup detail, such as `enum Mode does not have variant constructor search` or `enum Mode does not have variant constructor replace`. Consequently, a configuration containing the five groups `Home`, `Search`, `Replace`, `Normal`, and `Input` aborts interactive startup instead of ignoring the unsupported groups. Within an accepted group, a style string can contain a foreground, `on` followed by a background, and text modifiers including bold, underline, italic, dim, and reversed.

Color strings are trimmed. The strings `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, and `white`, and `bold black` through `bold white`, are accepted without preventing startup, but setting any one of them as `Normal.text` does not apply its nominal foreground palette index 0 through 15. In every one of these sixteen configurations, the initial frame instead uses only the built-in foreground indices 2, 15, and 4. Indexed-looking values are likewise accepted without preventing startup, but a `Normal.text` value of `color42`, `gray0`, `gray23`, `rgb000`, `rgb555`, or `color7 on color201` does not apply its requested palette index to the rendered UI. For each of those configurations the initial frame still emits only the built-in foreground indices 2, 15, and 4; after selecting a matching file and populating Preview, the additional emitted indices are the built-in 3, 8, and 10, not 42, 232, 255, 16, 231, 7, or background index 201. `bright colorN` is accepted as indexed-looking input. An unknown or malformed color means “no color for this component” and does not prevent UI startup. Common hexadecimal-looking values and unrecognized style properties likewise must not crash the information commands.

## Spec 10

Interactive mode uses a full-screen alternate-screen terminal UI, initially focused on Search. At 80 columns by 24 rows, with terminal styling removed, the initial snapshot is exactly:

```text
╭Search────────[Simple]╮╭Preview───────────────────────────────────────────────╮
│                      ││                                                      │
╰──────────────────────╯│                                                      │
╭Replace───────[Simple]╮│                                                      │
│                      ││                                                      │
╰──────────────────────╯│                                                      │
╭Result List───────────╮│                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
│                      ││                                                      │
╰──────────────────────╯╰──────────────────────────────────────────────────────╯
Help: <Ctrl-b> | Search: <Enter> | Toggle search mode:
```

The left column is 24 cells wide: three rows for Search, three for Replace, and seventeen for Result List. Preview occupies the remaining 56 cells and 23 rows. Row 24 is the context help/status line. Rounded Unicode box characters and the exact pane titles shown above are used. At other terminal sizes, the same panes remain visible and are resized without crashing. Long text is horizontally clipped/scrolled to the available interior width rather than corrupting borders.

## Spec 11

The main focus cycle is Search → Replace → Result List → Search on Tab and the reverse on Backtab/Shift-Tab, including when the result list is empty. Focus changes input routing and the final status line, while colors may additionally show focus:

- Search: `Help: <Ctrl-b> | Search: <Enter> | Toggle search mode:`
- Replace: `Help: <Ctrl-b> | Replace: <C-o> | Toggle replace mode:`
- Result List: `Help: <Ctrl-b> | Open File: <Enter> | Replace File: <r>`
- Preview: `Help: <Ctrl-b> | Back to list: <Enter> | Replace Line:`

Printable UTF-8 input is appended to the focused Search or Replace field. Backspace deletes characters correctly. Ctrl-u clears the active input, after which new text can be entered. Empty, long (at least 200 characters), punctuation-containing, and non-ASCII input must remain safe. The displayed one-line input is a viewport. At 80 columns its 22-cell interior reserves the last cell for the focused cursor, so at most 21 text cells are rendered and the final cell is blank. The viewport follows the end of overlong input: `nonexistent_pattern_xyz` appears as `nexistent_pattern_xyz `, and 200 `a` characters appear as 21 `a` characters followed by one space. Unbound keys, Home/End/Page keys in harmless contexts, and rapid key sequences do not terminate the application.

Ctrl-c and Ctrl-d quit from the main UI, restore the terminal, and return cleanly to the invoking shell. Ctrl-b opens Help from the application. Ctrl-n changes the mode of the currently focused Search or Replace field. Ctrl-o requests replacement across all included results.

## Spec 12

Search is recursive beneath the project root and updates live as the user edits a nonempty Search field; Enter explicitly reruns the same search. Enter on an empty Search field does nothing and leaves results and Preview empty. Each result represents a text file with at least one match. When the project root is the process working directory, the displayed name is relative to that directory, uses `/` between nested components, and is followed by a space and the total number of non-overlapping occurrences in parentheses, for example `subdir/file.txt (3)`. Explicit relative operands have an operand-dependent display quirk. For each spelling `-p root`, `-proot`, `-p=root`, `--project-root root`, and `--project-root=root`, a match in `root/found.txt` is displayed as `found.txt (1)`. The prefix is likewise omitted for literal operands `~`, `$HOME`, and `space ! -- 123`, and for `-p linked` when `linked` is a directory symlink: the operand is searched successfully and the result is `found.txt (1)`. In contrast, when invoked from the containing directory as `-p 123/.hé--_!/`, the match is displayed as `123/.hé--_!/found.txt (1)`; at 80 columns the 22-cell interior shows `123/.hé--_!/found.txt` and clips the count.

All ordinary text file extensions are searched equally. Nested directories at least 20 levels deep, hundreds of files, many results, very long lines, UTF-8 content, and consecutive matches such as `hellohellohello` are supported. Search itself never modifies file bytes. Binary files containing NUL bytes are skipped, version-control metadata such as `.git` is ignored, and directory symlinks/circular symlinks are not recursively followed. `.gitignore` patterns are applied: if it lists `ignored.txt` and `ignored-dir/`, matching files at `ignored.txt` and `ignored-dir/also.txt` are omitted, while an unignored matching file such as `sub/f.zz (2)` still appears. Files beneath `.git` are also omitted. A normal file may still be found when such ignored or unusable entries are present. Read-only files can be searched without mutation.

The result list is populated in search-discovery order rather than being alphabetically resorted by the UI; a rerun may rebuild that order. Paths/counts longer than the 22-cell result interior are clipped on screen but retain their full internal identity.

## Spec 13

Search has this cyclic mode order and these exact labels:

1. `Simple`: literal substring, case-insensitive.
2. `Match Case`: literal substring, case-sensitive.
3. `Match Whole Word`: literal complete words only, case-insensitive.
4. `Match Case Whole Word`: complete words only and case-sensitive for ordinary text, but the query is interpolated without escaping regex metacharacters. Consequently, after three toggles from `Simple`, the header is still `Match Case Whole Word` while `test\d+` is interpreted as a pattern and matches `test123` and `test456`.
5. `Regex`: the query is a regular expression, with its ordinary case-sensitive regex semantics.
6. The next toggle returns to `Simple`.

Changing mode immediately reruns a nonempty query and refreshes counts. “Whole word” uses conventional word boundaries: searching `cat` matches `The cat sat` but not `catalog`, `concatenate`, `scatter`, or `cats`. In Match Case Whole Word, both case and boundary conditions hold for ordinary text, subject to the unescaped-pattern behavior above. Simple mode treats `.`, `$`, `[`, `\`, parentheses, and similar regex metacharacters literally. Regex mode interprets constructs such as `test\d+`. An invalid regex such as `[unclosed` produces an empty list and no crash/dialog.

Mode text is right-aligned in the 24-cell pane header, but the `Search` title has paint priority over an overlapping label. The title overwrites the label's left-hand cells while its remaining suffix stays visible. Thus the second toggle produces exactly `╭Searchatch Whole Word]╮`, and the third produces exactly `╭SearchCase Whole Word]╮`.

## Spec 14

Moving focus to Result List does not select a file automatically. With that pane focused, `j` or Down moves to the next result and `k` or Up moves to the previous result; the first movement from “no selection” selects an endpoint. `g`, `h`, or Left selects the top item; `G`, `l`, or Right selects the bottom item. Navigation remains safe for zero, one, dozens, or hundreds of results, and updates Preview with the reference accumulation behavior in Spec 15. At list boundaries navigation may wrap, but it must never produce an invalid selection.

Pressing `d` removes the selected file from the current result/replacement set; it does not delete the file from disk. Counts and selection are updated, and removing the final item clears both selection and Preview. Repeated searches construct a new set from the filesystem. Pressing `/` while Result List is focused opens a three-row `Search` input overlay at the bottom of the Result List. Typing text such as `beta` does not narrow the list or remove nonmatching entries: with `alpha.txt (1)` and `beta.txt (1)` present, both remain displayed while the overlay contains `beta`. Escape closes the overlay, leaves both result entries present, and keeps the process running.

## Spec 15

Preview is initially empty, and an ordinary first live search leaves it empty because no result is selected. Selecting a file displays its UTF-8 text with line numbers, clipped to the Preview width. Matches are organized as context groups and groups are separated by a line of hyphens across the Preview interior. The selected file may be previewed even while Result List retains focus. Explicitly rerunning a nonempty search with Enter refreshes the search but does not establish a result selection or populate Preview: with `preview.txt (1)` present, Enter leaves Preview empty and Search focused. In the observed mode transition which first makes the query produce results, entering `test\d+` in Simple and toggling three times produces `regexish.txt (2)` under the `Match Case Whole Word` header and automatically displays `   1 test123 test456 TEST789 testx` in Preview while Search remains focused.

Enter on a selected result focuses Preview but does not initially select an active matching line, so focus alone adds no `>` marker. Within Preview, the first `j`/Down selects the first matching line and prefixes it with `>`; a second `j`/Down advances to the next matching line. For a file containing matches on lines 1 and 3, the first `j` produces `>    1 needle first` and the second produces `>    3 needle third`. The status line advertises Enter as the way back to Result List. Empty files, Unicode, long lines, and matches on the first/last line render safely. List navigation has an observable accumulation quirk: after an initial result is selected, `j`/Down or a `G` jump to a different result retains the previous file's context in Preview and also adds the newly selected file's context, separated by the normal hyphen rule. Unique text from both files is therefore visible after that forward move or jump. A following `k`/Up or `g` jump to the top rebuilds Preview for the newly selected result rather than retaining both groups. Deleting or replacing the last remaining match removes stale Preview state.

## Spec 16

Ctrl-b opens a modal help overlay. Its header is:

```text
╭ [1] Global ─ [2] Navigation ───────────────────────────────Press 'q' to close╮
```

The initial Global tab lists these lines verbatim:

```text
 - Ctrl-c: Quit
 - Ctrl-d: Quit
 - Ctrl-b: Help dialog
 - Ctrl-o: Process Replace For All Files
 - Ctrl-n: Loop through search and replace modes
 - Enter: Select/Deselect file
 - d: delete file/delete line from the replace process
 - r: Replace Selected File Or Line
```

The Navigation tab lists:

```text
 - Tab: Loop through panes
 - j/UpArrow: Move up
 - k/DownArrow: Move down
 - h/g/LeftArrow: Move to Top
 - l/G/RightArrow: Move to Bottom
```

At 80×24, the modal occupies complete rows 5 through 19 (one-based): its top border is row 5, one blank row follows, Global content occupies rows 7 through 14, rows 15 through 18 are blank, and its bottom border is row 19. The underlying frame remains visible on rows 1–4 and 20–23. Navigation content instead occupies rows 7–11, with the rest blank through row 18. Every content row has `│`, 78 interior cells padded with spaces, and `│`. Its row-24 status is `Close Help: <Esc> | Next Tab: <Right> | Previous Tab:`. Tab, Right, or `l` advances between help tabs; Left or `h` goes backward; `1` and `2` select the corresponding tab directly. Escape or `q` closes Help and restores the prior application screen/focus.

## Spec 17

Replace has this cyclic mode order and exact labels:

1. `Simple`
2. `Preserve Case`
3. `Delete Line`
4. back to `Simple`

Ctrl-n cycles this list only while Replace is focused. Search mode is independent. Simple replacement replaces every non-overlapping occurrence identified by the current search mode with the replacement string as literal text. Thus replacement text such as `$test` is inserted literally rather than treated as a capture-group expression. Matches at line starts/ends, multiple matches on one line, and matches across files of different extensions all work.

When Delete Line is active, the Replace input row displays the placeholder `[Entire line will be d`, clipped to the pane's 22-cell interior.

Preserve Case uses the case pattern of each matched occurrence: an all-uppercase match yields an uppercase replacement; a match whose first character is uppercase yields a replacement with the first character uppercase and the remainder lowercase; all other matches yield a lowercase replacement. For replacement `item`, `WORD` becomes `ITEM`, `Word` and mixed `WoRd` become `Item`, and `word` becomes `item`.

Delete Line removes every complete line containing one or more selected matches instead of inserting replacement text. It removes only matching lines and retains nonmatching lines in order. Its rewrite drops the final newline: input `keep1\nneedle twice needle\nkeep2\nneedle\nkeep3\n` becomes exactly `keep1\nkeep2\nkeep3`.

## Spec 18

Ctrl-o performs the chosen replacement across every file still included in the current results. In a Git working tree (a project containing `.git`), a nonempty replacement proceeds immediately. All eligible matches in all eligible files are changed, the search is refreshed, match counts decrease, and files with no remaining matches disappear from Result List. Files with no match and empty files remain byte-for-byte unchanged.

The replacement respects the active search semantics. For example, Simple search for lowercase `hello` replaces `Hello`, `HELLO`, and `hello`; Match Case replaces only exact-case occurrences; Match Whole Word leaves occurrences embedded in larger words untouched. Operations preserve unrelated content, UTF-8 validity, and line ordering. Bulk Simple and Preserve Case replacements preserve normal line boundaries; Delete Line has the final-newline behavior specified in Spec 17. A completed operation keeps the TUI responsive.

## Spec 19

Replacement can be scoped interactively:

- With Result List focused and a file selected, `r` replaces all current matches in only that file.
- With Preview focused and an active matching line selected by `j`/Down, `r` replaces matches only on that selected line. Other matching lines remain unchanged. Merely entering Preview does not make its first line active; pressing `r` before the initial `j` leaves the file and displayed count unchanged.

After an actual scoped `r` operation on an active line, the on-disk file, its Preview, and its result count are refreshed. Replacing lines sequentially continues at a remaining match without stale indices: a three-match file reports 3, then 2, then 1, and disappears after the final replacement. First-line and last-line matches have correct one-based selection behavior and no off-by-one errors.

A scoped Preview `r` rewrite drops an existing final newline even in Simple mode. Starting from `needle one\nneedle two\nneedle three\n`, selecting the first line and replacing `needle` with `done` writes exactly `done one\nneedle two\nneedle three`, with no newline after `three`.

The `d` key in Preview requires the same active-line selection. It leaves the underlying file unchanged and removes the selected match from the displayed count, but it does not exclude that line from a later Ctrl-o replacement: after `d` changes `lines.txt (2)` to `lines.txt (1)`, a subsequent bulk operation still replaces both matching lines. If no active line has yet been selected, `d` leaves the count at 2. The `d` key in Result List excludes the selected file as specified earlier; that file-level behavior is different.

## Spec 20

A Ctrl-o all-files replacement sometimes requires a modal `Confirm Dialog`. Scoped file/line actions are not subject to the non-Git bulk warning. While confirmation is active, normal text entry, pane focus changes, and mode changes do not affect the underlying fields or modes; Ctrl-c/Ctrl-d may still quit. There is a redraw quirk: unhandled keys erase the dialog box body from the screen even though the confirmation status line remains. For example, sending `xz` followed by Ctrl-n leaves the Search and Replace text and `[Simple]` mode unchanged, removes the visible warning body, and leaves `Confirm Replace: <Enter> | Cancel Replace: <Esc>, Left:` on row 24; Ctrl-d then exits with status 0.

If replacement text is empty, the warning text is exactly:

```text
Replace text is empty, and replacing with an empty string will remove the
matched text.
```

It explains that the matched text (or lines in Delete Line mode) will be removed. For a nonempty replacement in a project without `.git`, the warning is exactly:

```text
This action will modify the files in this directory.
Are you sure you want to continue?
```

Both show buttons in the order `Continue  Cancel`, with Cancel selected initially, and the status line `Confirm Replace: <Enter> | Cancel Replace: <Esc>, Left:`. At 80×24, both occupy rows 9 through 16. The empty-text box spans all 80 columns; its message is centered on rows 11–12 and its buttons on row 15. The non-Git box is 56 columns wide, centered at columns 13–68 (one-based); its message is centered on rows 11–12 and its buttons on row 15. Underlying pane text remains visible everywhere not overwritten by a modal cell.

The row-9 top border of each warning contains the centered title `Confirm Dialog`: the non-Git border is `╭────────────────────Confirm Dialog────────────────────╮`, and the full-width empty-replacement border is `╭────────────────────────────────Confirm Dialog────────────────────────────────╮`.

Tab, any arrow key, or `h`/`j`/`k`/`l` toggles the selected button. Enter activates the selected button, so immediate Enter cancels and Tab then Enter continues. The `y` key does not confirm either warning. With Cancel initially selected, pressing `y` in either the non-Git warning or the empty-text warning leaves the file unchanged, erases the visible dialog body, and leaves the confirmation status line displayed. Escape or `n` cancels regardless of selection. Cancel closes the dialog, preserves search/replace fields, and changes no file. Confirm closes it and executes the requested operation. Confirming the empty-text warning with Tab then Enter directly performs the empty replacement even when the directory is non-Git; it does not require a second warning.

## Spec 21

The UI is robust to filesystem edge cases during its lifetime:

- Binary files are never displayed as text results or modified.
- Ordinary symlink files are not followed as separate search results, and circular directory links do not hang traversal.
- Read-only files can appear in search results without search changing permissions or contents.
- A file deleted externally after being listed does not crash the next edit/search; stale state is discarded.
- Newline-only and empty files contribute no false matches.
- Unicode in contents, search input, paths, and filenames is decoded/rendered safely.
- Deep relative paths and names containing spaces, quotes, hyphens, and underscores remain addressable; on-screen clipping is visual only.
- Searching a very long line and rapidly updating a query completes within interactive time and leaves the UI responsive.

An invalid or absent root seen from an already-created pseudo-terminal produces the normal frame with an empty list when possible; direct noninteractive startup may instead terminate with the runtime error from Spec 6.

## Spec 22

Terminal lifecycle is clean. Startup draws a nonempty complete frame promptly. Ctrl-c and Ctrl-d terminate the program rather than merely clearing an input, and the alternate screen/cursor state is restored so the shell is usable. Opening and closing overlays does not leave stale overlay text. Terminal resizes trigger a redraw that retains the Search, Replace, Result List, and Preview panes. Repeated navigation, searches, modal interactions, unknown function keys, and rapid input never print panic/backtrace text into the UI.

The UI uses terminal styling for focus, selection, match highlighting, and configured styles, but its textual layout and behavior remain understandable when ANSI styling is stripped. Therefore selection must also be observable through Preview/status changes, not depend solely on color.
