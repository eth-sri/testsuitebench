# Clarified specification for `executable`

The required artifact is one executable file named exactly `executable`. It implements the `walk` terminal filesystem navigator described below. The words “screen” and “render” refer to terminal output produced while attached to a real pseudo-terminal; ANSI styling may be used, but all visible text and filesystem effects described here are required.

## Spec 1

`executable` is a top-level interactive TUI program, not a command with subcommands. Its invocation shape is `executable [flags] [path]`, corresponding to the user-facing name `walk`. If no path is supplied, the starting directory is the process's current working directory. A relative path is resolved relative to that directory. Absolute paths, `.` and `..`, trailing slashes, spaces, Unicode, punctuation, symlinks to directories, and deeply nested paths must work.

The recognized boolean flags are exactly `--icons`, `--dir-only`, `--hide-hidden`, `--preview`, `--with-border`, and `--fuzzy`. They may appear before or after the path and may be combined. The first argument that is not one of these recognized flags (and is not a help/version flag) selects the start path; later positional arguments are ignored for start-path selection. There is no special `--` separator: by itself it is an ordinary positional value. Unrecognized spellings, including unknown `--names`, single-dash long names, `--icons=true`, differently cased names, underscores, and triple-dash names, are ordinary positional values rather than parser errors. No output should call such values “commands” or “subcommands.”

## Spec 2

When used as the first argument, `--version` and `-v` are equivalent, do not require a terminal, exit with status 0, write nothing to stderr, and write exactly:

```text
v1.13.0
```

The newline is part of the output. A version flag is recognized only when it is the first argument. When recognized there, the program prints only the version and does not start the TUI. A later `-v` or `--version`, including one after an ordinary display flag or a path argument, is not handled as a version request; the invocation proceeds toward the interactive TUI. Thus, without a usable controlling terminal, `executable --icons /definitely/not/a/path ignored -v --preview` exits with status 2, writes nothing to stdout, and reports `could not open a new TTY` on stderr.

## Spec 3

`--help` and `-h` are equivalent, do not require a terminal, write nothing to stdout, write the following exact UTF-8 text to stderr, and exit with status 1. The output begins and ends with a newline and has exactly the blank lines shown:

```text

  walk v1.13.0

  Usage: walk [path]

    arrows, hjkl  Move cursor
    enter         Enter directory
    backspace     Exit directory
    space         Toggle preview
    esc, q        Exit with cd
    ctrl+c        Exit without cd
    /             Fuzzy search
    d, delete     Delete file or dir
    y             Copy to clipboard
    .             Hide hidden files
    ?             Show help

  Flags:

    --icons        display icons
    --dir-only     show dirs only
    --hide-hidden  hide hidden files
    --preview      display preview
    --with-border  preview with border
    --fuzzy        fuzzy mode

```

A help flag takes precedence over ordinary display flags, so those do not alter the help. Help describes only this single interactive application; it must not contain a `Commands:` section, the words `subcommand`, `command-specific`, or usage patterns such as `walk <command>`.

## Spec 4

Before handling help, version, or starting the TUI, read and compile `WALK_STATUS_BAR` if that variable is present. Consequently, an invalid expression makes even `--help` or `--version` terminate nonzero instead of producing their normal output. Other malformed or unusual configuration values, including malformed `WALK_OPEN_WITH` entries and arbitrary `WALK_MAIN_COLOR` strings, must not prevent help or version output.

Without help/version, the program must open `/dev/tty` (or an equivalent controlling terminal) for interactive operation. When launched with captured pipes and no usable terminal, it terminates with status 2 and stderr contains `could not open a new TTY`. This applies with no arguments, recognized display flags, unknown flag-like positional values, and extra paths.

## Spec 5

At TUI startup, make the resolved start path the current navigator path, load its immediate children, and select the first visible entry. The current path is the first line of the navigator's own rendering, but startup does not clear pre-existing terminal lines above it. For example, after a shell runs `cd /workspace` and then `/workspace/executable`, a full tmux pane capture retains those shell-command lines and contains the navigator header as the later standalone substring `\n/workspace\n`. Below the header, display child names sorted lexicographically by name without grouping directories ahead of files. Append `/` to entries that can be navigated as directories. Follow a symlink to a directory when Enter is pressed, while retaining the symlink path spelling in the displayed current path. Hidden names (those beginning with `.`) are visible by default. Empty directories and directories emptied by filtering show a rounded box containing `No files`.

Names with spaces, punctuation, very long names, non-ASCII characters, broken symlinks, FIFOs, executables, and large listings must not crash or corrupt the session. A listing with names `aaa_file.txt`, `bbb_dir`, `ccc_file.txt`, `ddd_dir`, and `zzz_symlink` must display them in that order.

## Spec 6

The ordinary listing is responsive to terminal size. Lay entries out top-to-bottom and then left-to-right in as many columns as fit. Each column is wide enough for its longest rendered entry and is separated from the next by at least two spaces. Keep the selected cell visible and highlight it with the configured main color; the highlight is an ANSI style, not extra visible marker text. A short listing therefore appears as one item per line, for example:

```text
/tmp/example
.hidden/
file1.txt
file2.txt
subdir/
```

Do not print trailing blank screen rows as content. When a path or cell must be clipped to fit its allocated pane, clip it to the available display width without splitting UTF-8 characters; retain the useful right-hand end of an overlong path.

## Spec 7

`--dir-only` filters the list to navigable directories and excludes regular files. `--hide-hidden` initially excludes every entry whose basename begins with `.`. The effects compose with one another and all other flags. If filtering removes every entry, render `No files`. At runtime, `.` toggles hidden-name filtering in both directions and immediately refreshes the list; it must be safe when the cursor is at any position. Hidden-only directories are not considered empty unless hidden filtering is active.

## Spec 8

Support cursor movement using both arrow keys and Vim keys: Up/`k`, Down/`j`, Left/`h`, and Right/`l`. Up and Down move within a display column, while Left and Right move between columns while preserving the row when possible. Movement at every boundary is clamped and never crashes. Home goes to the first item and End to the last item. Lowercase `g` jumps to the top of the current column and uppercase `G` to its bottom. Shift+Up and Shift+Down perform those vertical extreme jumps; Shift+Left and Shift+Right go to the leftmost and rightmost columns. Rapid repeated and mixed navigation inputs must leave the TUI responsive.

## Spec 9

Enter enters a selected directory, reloads its children, clears any active search, and places the cursor on the first child. Backspace moves to the parent directory and reloads it. Parent navigation is safe at filesystem root and remains at `/` rather than constructing invalid paths. Repeated entry and parent navigation must work at arbitrary practical depth.

## Spec 10

Pressing `q` or Escape outside a modal search/help state exits normally; `q` writes the navigator's current directory path followed by a newline to stdout, which is the “exit with cd” result consumed by a shell wrapper. Ctrl+C exits immediately. All three forms restore the terminal and terminate promptly. Unbound keys, including ordinary letters or digits when not in fuzzy/search mode, are ignored and must not terminate or corrupt the program.

## Spec 11

Pressing `?` toggles a full-screen help view. Its visible, non-styled content is exactly:

```text
help

    arrows, hjkl  Move cursor
    enter         Enter directory
    backspace     Exit directory
    space         Toggle preview
    esc, q        Exit with cd
    ctrl+c        Exit without cd
    /             Fuzzy search
    d, delete     Delete file or dir
    y             Copy to clipboard
    .             Hide hidden files
    ?             Show help
```

Pressing `?` again restores the prior directory view and selection. Help must remain usable in an otherwise empty directory.

## Spec 12

Pressing `/` enters explicit fuzzy-search mode; pressing `/` again exits it. While it is active, append `/` and the typed query to the current-path header. For example, query `con` in `/tmp/d` displays `/tmp/d/con`. Printable input, including spaces and UTF-8 text delivered by the terminal, extends the query. Backspace removes one query character; Backspace on an empty explicit query exits search mode rather than navigating to the parent.

Search is case-insensitive fuzzy/subsequence matching against entry names. When one or more entries match, show/rank the matches and move selection to the best match; when no entry matches, retain the ordinary listing instead of showing an empty view. Arrow/Vim movement continues to work without changing the query. Enter opens a matched directory and clears both query and search mode.

## Spec 13

`--fuzzy` enables a default fuzzy-input mode in which printable keys can begin a query immediately without first pressing `/`. It otherwise uses the matching and path-header behavior above. When no fuzzy-default query is active, Backspace navigates to the parent normally. Reset a default-fuzzy query and leave search mode approximately two seconds after the most recent typed character; restore the unfiltered listing and bare path header. Explicit `/` search is not subject to this automatic timeout.

## Spec 14

Preview mode is off by default, enabled initially by `--preview`, and toggled at runtime by Space. It splits the available width into a left listing pane and a right preview pane; the header includes the current path on the left and the selected entry name over the preview. Moving the cursor immediately updates the preview. `--with-border` adds a visible box-drawing separator/border between the panes and composes with every other flag. Toggling preview repeatedly must be stable.

The left pane remains navigable, but may clip the beginning of a long path or filenames to fit its width. Preview errors and empty-state notices use rounded boxes made from `╭─╮`, `│ │`, and `╰─╯`.

## Spec 15

For a readable directory selected in preview mode, show its immediate children, sorted and formatted by the same rules as the main listing. For a readable ordinary text or source file, show a bounded prefix of its content; large files (including a 200 KB line) are truncated to what is safe and useful for the pane instead of being read/rendered without limit. Text preview must preserve normal newlines and readable text, including UTF-8 content that fits the terminal. Syntax coloring for common source files is allowed by default, but it must not alter visible text.

If an unreadable, binary, oversized binary, or otherwise unsuitable file cannot be represented as text, show a rounded box containing `No preview available` (or leave the pane safely blank for an OS-level unreadable-file error); never dump arbitrary binary control bytes and never crash. A symlink to a readable file previews the target contents.

## Spec 16

Recognize at least `.png` and `.jpg` as image-preview extensions and decode their bytes.

Scale a valid image down, preserving its aspect ratio, so it fits the preview pane. Render it as colored terminal cells using the lower-half block `▄`, combining two source pixel rows per terminal row; fully transparent pixel pairs may render as spaces. Transparent PNGs and images larger than the pane must render without failure, and a nontrivial valid image must produce multiple rows containing `▄`.

## Spec 17

`--icons` prefixes every displayed entry with an icon and one space; without the flag no icon prefix or its reserved width is present. Icon selection accounts for filesystem type and permissions, with a generic regular-file fallback. Required filesystem-type displays include directory ``, executable ``, generic file ``, FIFO `p`, sticky directory `t`, and a visible icon for symlinks. Ordinary, other-writable, `.git`, and `node_modules` directories all receive a visible prefix and retain their trailing `/`. Symlinks may be followed for effective display behavior, but deleting one must still delete only the link.

## Spec 18

Read these environment settings independently and allow them to coexist:

- `WALK_MAIN_COLOR`: terminal color setting for the current selection; accept named colors, palette numbers, `#RRGGBB`, and arbitrary strings without crashing.
- `WALK_NO_HIGHLIGHT`: accept this preview-highlighting switch, including value `1`, without changing navigation or crashing.
- `WALK_EDITOR`, falling back to `EDITOR`: command used when opening an ordinary file; `WALK_EDITOR` wins when both exist.
- `WALK_OPEN_WITH`: per-extension opening commands.
- `WALK_REMOVE_CMD`: alternate deletion command.
- `WALK_STATUS_BAR`: status expression described below.

None of these settings changes the meaning of command-line filtering/display flags unless expressly stated.

## Spec 19

Parse `WALK_OPEN_WITH` as semicolon-separated mappings of `extension:command`. Permit multiple mappings, surrounding whitespace, commands containing spaces, a trailing separator, empty input, and empty entries. Ignore malformed entries lacking a colon rather than failing startup. Split a valid entry at its first colon so the command portion may contain additional colons. Extension keys are used without a leading dot and matched case-insensitively. When opening a file, a matching per-extension command overrides `WALK_EDITOR`/`EDITOR`; arguments in the configured command are preserved and the selected full path is supplied as its final file operand.

## Spec 20

When `WALK_STATUS_BAR` is absent, the bottom status area is normally empty except for transient operation messages. When present, compile and evaluate its expression against the selected entry whenever selection changes, and render the resulting string as the last visible line. Support string literals with either quote style, `+` string concatenation, integer arithmetic needed for arguments, arrays/pipelines and `join("separator")`, plus variables representing the current directory entry and list of entries.

Provide these callable functions: `Size()`, `Mode()`, `ModTime()`, `Owner()`, `Sprintf(format, arguments...)`, `PadLeft(string, width)`, and `PadRight(string, width)`. Nested calls and combinations must work, including `Size() + " " + Mode()`, `Sprintf("Size: %s | Mode: %s", Size(), Mode())`, and `PadLeft(PadRight("X", 5), 10)`.

## Spec 21

`Size()` reports the selected target's byte size using binary thresholds. Sizes below 1024 are integer bytes, including `0B`, `6B`, and `27B`. Megabyte values use one decimal digit, including `2.0MB`, `5.0MB`, `10.0MB`, and `50.0MB`; use analogous human-readable units for other magnitudes.

`Mode()` reports a ten-character Unix `ls -l` style string for the selected entry, such as `-rw-r--r--`, with the normal leading type character and rwx permission positions.

`Owner()` returns owner and group information as a string. `ModTime()` returns a compact human-readable timestamp; for a current-year entry it has the form `Mon D HH:MM`, with an English three-letter month and no required zero-padding of the day.

## Spec 22

`Sprintf` follows ordinary printf `%s` substitution for all supplied status values. Both `PadLeft(s,n)` and `PadRight(s,n)` must exhibit the compatibility behavior visible in terminal snapshots: if the display width of `s` is less than `n`, prepend spaces until total width is `n`; otherwise return `s` unchanged. Thus `PadRight("test",10)` renders six leading spaces then `test`, `PadLeft("left",15)` renders eleven leading spaces then `left`, and `PadLeft(PadRight("X",5),10)` renders nine leading spaces then `X`.

Invalid status syntax or an unknown function name is a fatal startup error. Exit with status 2 and write a panic-style diagnostic to stderr containing `panic:` and `status_bar.go:<error location>`; syntax errors also identify the unrecognized character, and an empty expression reports `EOF`. For an unknown call, the panic prefix is immediately followed by the unknown-name diagnostic, and the displayed source line begins with ` | `. In particular, `WALK_STATUS_BAR=InvalidFunc()` produces a diagnostic whose first three lines are exactly:

```text
panic: unknown name InvalidFunc (1:1)
 | InvalidFunc()
 | ^
```

The stack trace containing `status_bar.go:<error location>` follows this diagnostic.

## Spec 23

Deletion applies to the selected entry and requires two consecutive `d` presses (the terminal Delete key is an alias). The first press only arms confirmation and produces no `deleted. (u)ndo` message. The second press queues the selected entry for deletion, removes it from the ordinary visible list, and displays `<name> deleted. (u)ndo` in the status area while leaving the filesystem object present for a grace period. After approximately five seconds (and certainly by 6.5 seconds), delete it asynchronously and refresh the view.

Default deletion recursively removes regular files, read-only files, empty or nested directories, hidden files, large files, and symlinks. For a symlink, remove only the link and preserve its target. Multiple confirmed deletions have independent timers and all eventually execute.

## Spec 24

The pending-deletion message advertises `u` as undo. Pressing `u` when there is no pending deletion is a harmless no-op and leaves navigation functional.

If `WALK_REMOVE_CMD` is absent, perform the recursive default deletion. If it is present, invoke its entire value as the deletion program and pass the target's full pathname as exactly one argument; spaces, quotes, and dollar signs in the pathname must not undergo shell expansion or argument splitting. Ignore a nonzero command exit so the TUI does not crash and the target remains. The pending UI message is still shown before the attempt.

## Spec 25

`y` yanks the full path of the selected entry into the application's copy buffer and attempts to copy it to the system clipboard without crashing if no clipboard service exists. `p` uses that buffered basename in the current directory. It must not overwrite an existing destination. If that destination exists, leave it byte-for-byte unchanged and show the exact status message `paste error: file already exists`.

## Spec 26

Startup filesystem errors are rendered inside the TUI rather than hanging. Keep the attempted path as the first line, followed by a rounded error box. For a nonexistent `/nonexistent/path`, the box text is `open /nonexistent/path: no such file or directory`. For a regular file supplied where a directory is required, use the platform error form `readdirent PATH: not a directory`. The box width surrounds the message with one interior space on each side. The session remains responsive to quit keys after rendering the error.

Unreadable directories, broken symlinks, FIFOs, rapid key sequences, very large directories, deep navigation, and empty/filter-empty lists must all fail gracefully: no hang, uncaught exception, malformed UTF-8, or terminal corruption. Filesystem refreshes caused by navigation, filtering, deletion, undo, or paste must preserve a valid in-range selection.
