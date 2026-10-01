# Felix executable specification

The required artifact is one executable file named `executable`. It implements Felix 2.16.1, a terminal file manager. Paths, filenames, and command input are UTF-8 during ordinary operation. “Enter”, “Escape”, “Backspace”, arrow names, and control-key names below denote the corresponding terminal key events, not their literal words.

## Spec 1

The executable is a long-running, full-screen terminal application when launched on a valid directory through a terminal. It must work in an ordinary PTY/tmux terminal and redraw promptly after input. With no path argument it uses the process current directory. With one path argument it uses that directory. Relative paths, absolute paths, `.`, `..`, redundant slashes, trailing slashes, spaces, dashes, control characters, non-ASCII text, emoji, and deeply nested paths are accepted whenever the operating system says that the resulting path is an accessible directory. A symbolic link whose target is a directory is also accepted. A literal `~` is not expanded by the program (shell expansion, if any, occurs before invocation).

The application must remain responsive with empty directories, directories containing only hidden entries, at least 10,000 entries, 10 MB files, binary files, unreadable entries, valid and broken symbolic links, and circular symbolic links. An unrecognized key sequence must not crash or terminate the UI.

On Linux, supplying a directory argument containing an operating-system path byte that cannot be decoded as UTF-8 does crash during startup. For example, a path containing byte `0xff` produces no standard output, exits with status 101, and writes a Rust panic to standard error reporting that `Result::unwrap()` received the undecodable path; the path represents that byte as `\xFF`, and the final line is the note about setting `RUST_BACKTRACE=1` to display a backtrace.

## Spec 2

Command-line dispatch depends on argument count and position; this is not a subcommand-style CLI.

- No arguments: launch the TUI in the current directory.
- Exactly one argument: `-h` and `--help` print help; `--init` prints the shell initializer; `-l` and `--log` launch the current directory with logging; every other token is interpreted literally as a path, including unknown option-looking tokens, `-`, `--`, `--version`, `-H`, `-L`, `--INIT`, combined flags such as `-hl`, and forms such as `--log=/tmp`.
- Exactly two arguments: if the first is `-l` or `--log`, launch the second token as a literal path with logging. Thus `-l -h`, `--log --help`, and `--log --init` try to open a path named by the second token. For every other two-token combination, print the standard help text. This includes `--init extra`, `-- --help`, `-- --init`, `path --help`, and `--badflag --help`.
- Three or more arguments: print the standard help text.

There are no subcommands. Words such as `add`, `remove`, `list`, `show`, `edit`, `help`, and `version` are ordinary path strings. Help must never contain a “subcommand” or “Commands:” section, and invalid-path diagnostics must not suggest subcommands.

## Spec 3

Both `-h` and `--help`, and every argument-count case that calls for help, write exactly the following text to standard output, including spelling, capitalization, punctuation, blank lines, indentation, backticks, doubled backslashes, and the final newline. They write nothing to standard error and exit with status 0.

```text
# felix v2.16.1
A simple TUI file manager with vim-like keymapping.

## Usage
`fx` => Show items in the current directory.
`fx <directory path>` => Show items in the path.
Both relative and absolute path available.

## Options
`--help` | `-h`   => Print help.
`--log`  | `-l`   => Launch the app, automatically generating a log file.
`--init`          => Returns a shell script that can be sourcedfor
                     for shell integration.

## Manual
j / <Down>         :Go down.
k / <Up>           :Go up.
<C-d>              :Go down 1/2 page.
<C-u>>             :Go up 1/2 page.
h / <Left>         :Go to the parent directory if exists.
l / <Right> / <CR> :Open item or change directory.
gg                 :Go to the top.
G                  :Go to the bottom.
z<CR>              :Go to the home directory.
z {keyword}<CR>    :Jump to a directory that matches the keyword.
                    (zoxide required)
<C-o>              :Jump backward.
<C-i>              :Jump forward.
i{file name}<CR>   :Create a new empty file.
I{dir name}<CR>    :Create a new empty directory.
o                  :Open item in a new window.
e                  :Unpack archive/compressed file.
dd                 :Delete and yank item.
yy                 :Yank item.
p                  :Put yanked item(s) from register zero
                    in the current directory.
:reg               :Show registers. To hide it, press v.
"ayy               :Yank item to register a.
"add               :Delete and yank item to register a.
"Ayy               :Append item to register a.
"Add               :Delete and append item to register a.
"ap                :Put item(s) from register a.
V                  :Switch to the linewise visual mode.
  - y              :In the visual mode, yank selected item(s).
  - d              :In the visual mode, delete and yank selected item(s).
  - "ay            :In the visual mode, yank items to register a.
  - "ad            :In the visual mode, delete and yank items to register a.
  - "Ay            :In the visual mode, append items to register a.
  - "Ad            :In the visual mode, delete and append items to register a.
  - c              :Rename selected items in default editor.
u                  :Undo put/delete/rename.
<C-r>              :Redo put/delete/rename.
v                  :Toggle whether to show the preview.
s                  :Toggle between vertical / horizontal split in the preview mode.
<Alt-j>
 / <Alt-<Down>>    :Scroll down the preview text.
<Alt-k> 
 / <Alt-<Up>>      :Scroll up the preview text.
<BS>               :Toggle whether to show hidden items.
t                  :Toggle the sort order (name <-> modified time).
c                  :Switch to the rename mode.
/{keyword}         :Search items by a keyword.
n                  :Go forward to the item that matches the keyword.
N                  :Go backward to the item that matches the keyword.
:                  :Switch to the command line.
  - <C-r>a         :In the command line, paste item name in register a.
:cd<CR>            :Go to the home directory.
:cd {path}<CR>     :Go to the path.
:e<CR>             :Reload the current directory.
:config<CR>        :Go to the directory that contains the config file if exists.
:trash<CR>         :Go to the trash directory.
:empty<CR>         :Empty the trash directory.
:h<CR>             :Show help.
:q<CR>             :Exit.
:{command}         :Execute a command e.g. :zip test *.md
<Esc>              :Return to the normal mode.
<C-h>              :Works as Backspace after `i`, `I`, `c`, `/`, `:` and `z`.
ZZ                 :Exit without cd to last working directory
                    (if `match_vim_exit_behavior` is `false`).
ZQ                 :cd into the last working directory and exit
                    (if shell setting is ready and `match_vim_exit_behavior is `false`).

## Preview feature
By default, text files and directories can be previewed.
To preview images, you need to install chafa (>= v1.10.0).
Please see https://hpjansson.org/chafa/

## Configuration

*Both `config.yaml` and `config.yml` work.*

### Linux
config file    : $XDG_CONFIG_HOME/felix/config.yaml(config.yml)
trash directory: $XDG_DATA_HOME/felix/trash
log files      : $XDG_DATA_HOME/felix/log

### macOS
On macOS, felix looks for the config file in the following locations:

1. `$HOME/Library/Application Support/felix/config.yaml(config.yml)`
2. `$HOME/.config/felix/config.yaml`

trash directory: $HOME/Library/Application Support/felix/trash
log files      : $HOME/Library/Application Support/felix/log

### Windows
config file     : $PROFILE\\AppData\\Roaming\\felix\\config.yaml(config.yml)
trash directory : $PROFILE\\AppData\\Local\\felix\\trash
log files       : $PROFILE\\AppData\\Local\\felix\\log

For more details, visit https://github.com/kyoheiu/felix
```

The manual section above is an exact output transcript, including legacy descriptions that do not match every current interaction. It does not override the observed interactive behavior specified below for `z`, `i`, `I`, `:cd`, or `:empty`.

## Spec 4

`--init` as the sole argument writes exactly the following POSIX-shell text to standard output, with a final newline, writes nothing to standard error, and exits 0. The backslashes shown before dollar signs are literal output characters. The emitted text must be valid Bash syntax when evaluated: it selects `$XDG_RUNTIME_DIR/felix`, otherwise `$TMPDIR/felix`, otherwise `/tmp/felix`; creates that directory; removes files older than one minute; defines an `fx()` wrapper which passes all arguments to the real `fx` with `SHELL_PID` set; and after the real program exits, changes to the directory recorded in the per-shell file and removes that file.

```text
# To be eval'ed in the calling shell
  eval "$(
    if [ -n "$XDG_RUNTIME_DIR" ]; then
      runtime_dir="$XDG_RUNTIME_DIR/felix"
    elif [ -n "$TMPDIR" ]; then
      runtime_dir="$TMPDIR/felix"
    else
      runtime_dir=/tmp/felix
    fi

    mkdir -p "$runtime_dir"

    # Clean up leftover LWD files
    find "$runtime_dir" -type f -and -mmin +1 -delete

    cat << EOF
fx() {
  local RUNTIME_DIR="$runtime_dir"
  SHELL_PID=\$\$ command fx "\$@"

  if [ -f "\$RUNTIME_DIR/\$\$" ]; then
    cd "\$(cat "\$RUNTIME_DIR/\$\$")"
    rm "\$RUNTIME_DIR/\$\$"
  fi
}
EOF
  )"
```

## Spec 5

Except for the undecodable operating-system path case in Spec 1, all recognized command-line outcomes, including errors, return process status 0. A nonexistent or dangling path produces a single blank line on standard output and the following two lines on standard error, substituting the original argument verbatim (without canonicalizing or normalizing it):

```text
Invalid path: PATH
`fx -h` shows help.
```

The stderr text ends in a newline. An existing non-directory, including a symlink to a regular file, instead produces:

```text
Path should be directory.
`fx -h` shows help.
```

This existing-non-directory case writes zero bytes to standard output. Its stderr text ends in a newline.

When a valid directory is launched with stdout and stderr captured and without a usable input terminal, the program still writes its initial full-screen ANSI drawing to stdout. It then writes exactly `Failed to initialize input reader\n` to stderr and exits with status 0. The stdout drawing is nonempty and begins by saving the cursor, hiding it, entering the alternate screen, clearing the screen, and drawing the current directory and listing. Path validation happens before this initialization, and logging does not change the captured-stream diagnostic.

## Spec 6

On Linux, configuration is discovered as `config.yaml` or `config.yml` beneath `$XDG_CONFIG_HOME/felix`; if `XDG_CONFIG_HOME` is unset, use `$HOME/.config`. A real TUI launch creates the `felix` directories beneath the effective config directory, effective data directory (`$XDG_DATA_HOME`, else `$HOME/.local/share`), and effective runtime directory (`$XDG_RUNTIME_DIR`, else `$TMPDIR`, else `/tmp`). Merely reporting an argument error must not create a log directory.

The YAML configuration accepts an empty file, a comments-only file, and these optional fields:

- `default`: an editor/command string, falling back to `$EDITOR` when absent;
- `match_vim_exit_behavior`: boolean, default `false`;
- `ignore_case`: boolean controlling search comparison;
- `exec`: mapping from command strings (which may contain arguments) to lists of filename extensions;
- `color`: mapping with `dir_fg`, `file_fg`, `symlink_fg`, and `dirty_fg`. Values may be `Black`, `Red`, `Green`, `Yellow`, `Blue`, `Magenta`, `Cyan`, `White`, `LightBlack`, `LightRed`, `LightGreen`, `LightYellow`, `LightBlue`, `LightMagenta`, `LightCyan`, `LightWhite`, `!Rgb [r, g, b]`, or `!AnsiValue n`, with byte-valued numeric components.

Default colors are LightCyan for directories, LightWhite for files, LightYellow for symlinks, and Red for changed/untracked Git entries.

## Spec 7

Malformed YAML, duplicate keys, wrong field types, and invalid color names do not abort startup. Before continuing with all-default configuration, write these three lines to stderr (the parser detail occupies the second line):

```text
Cannot read the config file properly.
Error: PARSER DETAIL
felix launches with default configuration.
```

For compatibility, the following inputs have these exact parser details:

- `default: nvim\nmalformed yaml: [this is not closed\nignore_case: true\n` → `did not find expected ',' or ']' at line 3 column 12, while parsing a flow sequence at line 2 column 17`.
- `default: nvim\nmatch_vim_exit_behavior: true\nthis is not valid yaml: [\n  missing closing bracket\nignore_case: true\n` → `did not find expected ',' or ']' at line 5 column 12, while parsing a flow sequence at line 3 column 25`.
- `default: /home\nexec:\n  bat: [cat\ncolor:\n  - invalid: structure\n` → `did not find expected ',' or ']' at line 4 column 6, while parsing a flow sequence at line 3 column 8`.
- duplicate `default` fields → `duplicate field` followed by the field name `default` enclosed in backticks.
- `color.dir_fg: InvalidColor` → `color.dir_fg: unknown variant` followed by `InvalidColor` in backticks, then `, expected one of` and the backtick-enclosed list `Black`, `Red`, `Green`, `Yellow`, `Blue`, `Magenta`, `Cyan`, `White`, `LightBlack`, `LightRed`, `LightGreen`, `LightYellow`, `LightBlue`, `LightMagenta`, `LightCyan`, `LightWhite`, `Rgb`, `AnsiValue`, ending ` at line 3 column 11`.
- a tab starting line 2 after `default: /home` → `found a tab character that violates indentation at line 2 column 1, while scanning a plain scalar at line 1 column 10`.
- `default: vim\nignore_case: not a boolean\n` → `ignore_case: invalid type: string "not a boolean", expected a boolean at line 2 column 14`.

After these lines the program proceeds normally, so a launch with captured standard streams additionally ends with `Failed to initialize input reader`.

## Spec 8

With `-l` or `--log`, starting the TUI creates `$XDG_DATA_HOME/felix/log` (or its platform fallback) and at least one regular log file. Logging begins only after argument and path validation. Log normal operations usefully, but do not emit a spurious empty rename record such as `RENAME: []` when rename mode is entered and cancelled without a rename.

If `o` is pressed on a regular file and there is no applicable `exec` mapping, show `No exec configuration` on the message line without crashing or changing directory.

## Spec 9

The normal 80-column by 24-row screen has this structural layout, excluding terminal color escapes:

1. Row 1 is one leading space followed by the current absolute directory.
2. Row 2 is the transient prompt/message line. It is blank normally; prompts and messages also begin with one space.
3. Rows 3 through the row before the footer contain directory entries. The selected row begins `> ` and every other row begins two spaces.
4. The last row is the selected-item footer, beginning with one space. Blank rows fill unused space so the footer remains at the bottom.

Entries are natural-name sorted with directories before nondirectories. Natural sorting places `file2` before `file10`; ordinary names such as `aaa`, `mmm`, `zzz` are alphabetic. The alternate time order places newest first. Hidden dot entries are included initially; Backspace toggles between showing and hiding them without altering the filesystem. A reload re-reads the directory.

At width 80 an entry line is its two-character marker/name field padded so a 16-character local timestamp (`YYYY-MM-DD HH:MM`) ends at column 80. At widths below 28 timestamps are omitted. Entry names are truncated with `...` to fit narrow screens, but the path header is not ellipsized: it is drawn from the left and hard-clipped at the terminal edge. At width 10, for example, `file1.txt` displays as `> file1...`, while a longer path header consists of its leading space and first nine path characters. At width 25, `> abc.txt` has no timestamp; at width 28, `> file1.txt YYYY-MM-DD HH:MM` fits exactly. Width 120 and 200 screens right-align the timestamp at their final column and do not unnecessarily truncate names.

## Spec 10

The footer for a selected regular file is ` POSITION/TOTAL EXT SIZEB MODE`, where `POSITION` is one-based, `EXT` omits the leading dot, `SIZE` is the byte count, and `MODE` is the last three octal permission digits (for example ` 5/18 txt 10B 644`). For an extensionless file omit `EXT`; for a directory report its metadata byte size and mode (for example ` 1/18 40B 755`). A valid symlink footer identifies its target with `linked to:`. A broken symlink remains visible and its footer contains exactly `linked to: (invalid path)`.

An empty directory renders the path, a blank message row, and a lone `>` selection marker, with no item footer. A one-item directory renders `> NAME` and `1/1`; movement commands clamp to that item. The viewport scrolls to keep the selected entry visible. In a 24-row screen it has 21 entry rows between the message row and footer. A 40-by-50 terminal displays all 30 short entries followed by blank filling; large lists correctly show `1/100` at the top and `100/100` at the bottom.

## Spec 11

Both terminal dimensions must be at least 4. If either is 3 or less, restore/leave the terminal cleanly, print exactly `Error: Too small window size` followed by a newline, and exit. A 4-by-4 terminal is valid and shows four clipped rows: clipped path, blank message, one clipped selected entry, and clipped footer. For a temporary path beneath `/tmp` containing three `fileN.txt` entries, its trimmed 4x4 snapshot is exactly `/tm`, a blank line, `> ..`, then `1/3`. All drawing must stay usable at 4x4, 10x10, 25x24, 28x24, 40x50, 80x24, 120x24, and 200x24.

For reference, after dynamic path, time, and size substitution, representative non-preview screens are:

```text
 /some/directory

> file1.txt                                                     YYYY-MM-DD HH:MM
  file2.txt                                                     YYYY-MM-DD HH:MM
  file3.txt                                                     YYYY-MM-DD HH:MM
[blank rows through row 23]
 1/3 txt 5B 644
```

and at 10x10:

```text
 /some/di

> file1...
  file2...
  file3...
[blank rows]
 1/3 txt 5B
```

## Spec 12

Normal-mode navigation is Vim-like. `j` and Down select the next entry; `k` and Up select the previous entry; boundaries clamp rather than wrap. `gg` selects the first entry and `G` selects the final entry. Control-D and Control-U move by half the terminal's total row count, rounded up, rather than by half the number of entry rows. They update both cursor and viewport and clamp at the ends. Thus the step is 12 entries at heights 23 and 24, and 13 entries at height 25; from position 1 in a 24-row terminal, successive Control-D presses select positions 13 and 25, and Control-U returns to 13 and then 1. Multiple consecutive keys must be processed individually and promptly.

`l`, Right, and Enter open the selected item. On a directory (including a symlink to one), they enter it. `h` and Left enter the parent if one exists. When returning to a parent via `h`, select the child directory just left; preserve this cursor memory through several nested levels. Changing directories clears visual selection and resets appropriate viewport/search state.

`z` enters the zoxide keyword prompt; it is not a direct home-directory shortcut. Submitting the empty prompt with Enter leaves the current directory unchanged and clears the prompt.

## Spec 13

Control-O and Control-I (the Tab key) are accepted as backward/forward directory-history keys. When there is no history, each is a no-op with an identical screen and the UI remains responsive.

## Spec 14

Pressing `/` enters a search prompt displayed on row 2 as `/TEXT`. Enter commits it, clears row 2, and moves to the first entry whose filename contains the text. The full list remains present; search does not filter it. The query remains active internally: `n` moves to the next matching entry and `N` to the previous one, scrolling the viewport, but movement clamps at the first and last match rather than cycling. For files `apple.txt`, `banana.txt`, `cherry.txt`, `date.txt`, `elderberry.txt`, `fig.txt`, and `grape.txt`, `/err` selects `cherry.txt` with a blank row 2; `n` selects `elderberry.txt`, a second `n` remains there, and `N` returns to `cherry.txt`.

Search uses case-sensitive comparison by default. Setting `ignore_case: true` in the configuration makes the comparison case-insensitive. Unicode input must be accepted. A committed zero-match search also clears row 2 and leaves the selection where it was. Within the search prompt, Escape cancels the input and Backspace and Control-H delete input characters without corrupting multibyte characters.

## Spec 15

Pressing `i` opens ` New file:` on row 2. Printable input is appended after that prompt, Control-H removes the final input character, and Enter creates an empty regular file named by the edited input, clears row 2, refreshes the listing, and selects the new file. Thus typing `would-be-file`, then Control-H, then Enter displays ` New file: would-be-fil` immediately before submission and creates `would-be-fil`.

Pressing `I` opens ` New directory:` on row 2. Printable input is appended after that prompt, and Enter creates a directory named by the input, clears row 2, refreshes the listing, and selects the new directory. This remains true when the displayed directory already contains an entry and `$EDITOR` is set to `touch`: entering `would-be-dir` creates the directory `would-be-dir`. Escape cancels either creation prompt without creating anything.

Pressing `c` in normal mode prompts `New name: OLDNAME`, initially with the existing name editable. Escape cancels it without changing the selected file. All prompt text is shown on row 2.

## Spec 16

`yy` yanks the selected item into both the unnamed register and register zero without removing it, then shows `1 item yanked.` (tests may accept the same text without the final period). `dd` is a two-key operation: after the first `d`, row 2 shows `d`; Escape cancels it. The second `d` deletes/yanks the selected item and shows `1 item deleted.`. A deleted source disappears immediately.

`p` copies the yanked item(s) into the current directory with contents and hierarchy preserved. Its completion message includes a bracketed elapsed-time suffix after the count, such as `1 item inserted. [0.00s]`; plural insertions use the grammatically plural count with the same suffix. This can restore a deleted item or copy a yanked item into another directory while leaving the original intact. Consecutive deletes replace register zero, so after deleting files 1, 2, and 3, `p` restores file 3.

## Spec 17

A register prefix is `"` followed by a letter. Lowercase and uppercase register sequences, including `"byy` and visual `"Ay`, must be accepted without destabilizing the listing. The unnamed register tracks the latest yank/delete and register zero retains ordinary yanks.

`:reg` displays a register view containing labels such as `""`, `"0`, and `"a` and the stored filenames. Escape or `v` closes the register view. Register operations and their contents must remain correct across directory navigation.

## Spec 18

`V` enters linewise visual mode with the current entry as the anchor. Navigation extends a contiguous inclusive selection. Thus `V`, `j`, `j`, `d` deletes exactly three entries, and `V`, `j`, `j`, `y` yanks exactly three and reports `3 items yanked.`. `G` extends from the anchor to the final item. The cursor marker `>` denotes the active endpoint, the footer position is that endpoint's one-based position, and terminal highlighting distinguishes the entire selected range. On a one-item list, visual movement stays on that item. Escape exits visual mode without operating on files.

Visual `y`/`d` use the unnamed/zero registers, while a preceding lower- or uppercase named-register prefix selects replacement or append behavior. Visual deletion/yanking and named-register forms must operate on every selected item.

## Spec 19

`u` undoes the most recent put, delete, or rename, restoring exact contents and names; Control-R redoes it. Operations form an ordered history, so multiple deletes can be undone one at a time, redone, and followed by new operations without corrupting state. Undoing a delete restores the item; redoing removes it again. UI listing, cursor, registers where applicable, and filesystem state refresh immediately.

`:trash` changes the current directory to the data directory's `felix/Trash` directory, creating it if needed; its path header contains `Trash`.

## Spec 20

`v` toggles preview. With preview off, the normal list spans the width. With preview on, the default vertical split gives the left half to the list and the right half to a preview; the row-1 right heading is `[SELECTED_NAME]`. Text preview lines begin alongside the corresponding left-pane rows. For example an 80-column preview starts approximately as follows:

```text
 /some/directory                       [file.txt]

> file.txt              YYYY-MM-DD HH:MM first line of content
                                         second line
```

`s` alternates between vertical and horizontal preview splits, then back again. In horizontal mode preview content appears on rows below the file list rather than beside the selected filename. Directory previews list their contents. Large text files (at least 5 MB) may be truncated for display but must not freeze or crash the UI. Turning preview off restores the full-width layout.

## Spec 21

Pressing `:` enters command input on row 2. Enter dispatches these commands:

- `:q`: cleanly exits the TUI.
- `:e`: reloads current directory contents, including files created externally after launch.
- `:cd PATH`: an absolute path with a single, space-free operand changes to that directory. A relative operand is resolved against the process working directory from which Felix was launched, not against the directory currently displayed. If it does not exist there, the displayed directory is unchanged and row 2 shows `Path does not exist.`. An unquoted absolute operand containing a space is not accepted by this built-in form: after Enter, the command line clears, row 2 is blank, and the displayed directory remains unchanged. `:cd` without a path changes to `$HOME`.
- `:trash`: behaves as specified above.
- `:empty`: first leaves the trash contents intact and displays `Are you sure to empty the trash directory? (if yes: y)`. A following `y` empties the trash and clears the prompt; a following `n` clears the prompt without emptying it.

Escape cancels command input. `ZZ` is also a clean two-key exit.

## Spec 22

Pressing `e` on the selected file detects its content by magic bytes and unpacks supported data into a sibling whose name is the complete original basename plus `_1` (choose a later numeric suffix if needed). Supported cases are plain tar; gzip-compressed tar; xz-compressed tar; zstd-compressed tar; ZIP entries using stored, deflate, or bzip2 compression; standalone gzip; and standalone xz. Archive forms extract to a directory; standalone gzip/xz produce a regular file, still using the full source basename plus `_1` (for example `archive.txt.xz_1`). Refresh the listing afterward.

Extraction preserves member hierarchy, empty directories, file contents, Unicode and shell-special filenames, legal long names/deep paths, executable and ordinary permission bits, modification times, and symbolic links with their relative targets. It must correctly extract archives with at least 200 files. Tar, tar.xz, tar.zst, gzip, xz, and the three ZIP compression modes are all required.

## Spec 23

Unpacking errors are shown on row 2 without terminating the TUI or modifying the source:

- Content with no recognized archive signature, regardless of extension: `Seems not an archive file.` and no `_1` output.
- A corrupted ZIP beginning with a ZIP signature but lacking its end record: `invalid Zip archive: Could not find EOCD`.
- A zero-byte file passed to this legacy unpack path: `Error: felix panicked`.
- LZW signature bytes `1f 9d`: `Cannot unpack this type: tar(LZW)`.
- LZH signature bytes `1f a0`: `Cannot unpack this type: tar(LZH)`.

The selected filename remains visible along with the error. Detection is based on content rather than a misleading suffix.

## Spec 24

Every filesystem-changing command must affect the real paths supplied at runtime, not merely the screen model. Redrawing must reflect external filesystem changes after `:e`, preserve data exactly through yank/put/delete/undo/redo, and never interpret filenames as shell code. Operations on missing, readonly, invalid, or unsupported targets report a concise message on row 2 and keep the event loop alive. On any exit, restore the terminal from raw/alternate-screen mode so the invoking shell remains usable.
