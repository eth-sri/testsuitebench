# Behavioral specification for `executable`

The required artifact is one executable file named exactly `executable`. It implements the Unix terminal file manager described below. All paths are byte-preserving filesystem paths except where UTF-8 display is explicitly discussed. “Terminal” means a real terminal or pseudo-terminal capable of receiving individual key presses and ANSI/curses screen updates.

## Spec 1

`executable` is a standalone Unix command-line program whose application name is `nnn`, version 5.2. It has no subcommands: words such as `add`, `remove`, `list`, `init`, and `status` are positional paths, never command names. It must be executable directly as `./executable` and must not need repository source files at run time.

With neither a terminating informational option nor usable terminal input, normal browsing startup fails promptly rather than hanging. In particular, once a valid invocation has reached browsing, if standard input is non-terminal and supplies no path data (EOF/empty input), it exits with status 1 and writes exactly `0 entries\n` to stderr. This is the same in ordinary browsing and picker mode, for an empty or populated starting directory, and with recognized nonconflicting startup switches that proceed to browsing. Picker-mode stdout is empty. Ordinary browsing stdout is also empty unless `-x` is active; in that case `-x` writes exactly the seven bytes `\x1b[23;0t` to stdout before the same status-1 exit and stderr diagnostic. With a terminal, it initializes an interactive full-screen file browser and remains alive until a quit action. It must work under common `TERM` values such as `xterm` and `xterm-256color` and must restore the terminal on exit.

## Spec 2

`-h` prints the following text byte-for-byte to stdout, including its final newline, prints nothing to stderr, and exits 0:

```text
usage: nnn [OPTIONS] [PATH]

The unorthodox terminal file manager.

positional args:
  PATH   start dir/file [default: .]

optional args:
 -a      auto NNN_FIFO
 -A      no dir auto-enter during filter
 -b key  open bookmark key (trumps -s/S)
 -B      use bsdtar for archives
 -c      cli-only NNN_OPENER (trumps -e)
 -C      8-color scheme
 -d      detail mode
 -D      dirs in context color
 -e      text in $VISUAL/$EDITOR/vi
 -E      internal edits in EDITOR
 -f      use history file
 -F val  fifo mode [0:preview 1:explore]
 -g      regex filters
 -H      show hidden files
 -i      show current file info
 -J      no auto-advance on selection
 -K      detect key collision and exit
 -l val  set scroll lines
 -n      type-to-nav mode
 -N      use native prompt
 -o      open files only on Enter
 -p file selection file [-:stdout]
 -P key  run plugin key
 -Q      no quit confirmation
 -r      use advcpmv patched cp, mv
 -R      no rollover at edges
 -s name load session by name
 -S      persistent session
 -t secs timeout to lock
 -T key  sort order [a/d/e/r/s/t/v]
 -u      use selection (no prompt)
 -U      show user and group
 -V      show version
 -x      notis, selection sync, xterm title
 -z      in order fuzzy filters
 -0      null separator in picker mode
 -h      show help

v5.2
BSD 2-Clause
https://github.com/jarun/nnn
```

The output deliberately describes options, not commands or subcommands. When `-h` is encountered during command-line scanning it terminates scanning immediately: for example `-h -V` and `-h -X` produce the help above successfully. An earlier invalid option still wins. A token `-h` appearing after `--` is a path, not help. `--help` is not supported.

## Spec 3

`-V` prints exactly `5.2\n` to stdout, nothing to stderr, and exits 0. It is likewise terminating at the point encountered: `-V -h`, `-V -X`, or `-V PATH` print only the version, while an invalid option before `-V` is reported. The version output is unaffected by valid configuration variables and ordinary flags. It also terminates before an unknown `NNN_ORDER` sort key can cause any error: for example, with `NNN_ORDER=x:/tmp`, `-V` still exits 0 with exactly `5.2\n` on stdout and empty stderr.

`-K` performs the built-in key-binding collision check and exits immediately. With the bindings in this specification there is no collision, so it exits 0 silently, even if a path or otherwise compatible flags follow it.

## Spec 4

Options use traditional `getopt`-style short-option parsing. Boolean options may be clustered. The options `b`, `F`, `l`, `p`, `P`, `s`, `t`, and `T` require a value, accepted as the next token or directly attached to the option (for example `-F1`). When one lacks a value, exit 1; stdout is the complete help text from Spec 2, and stderr is exactly `ARGV0: option requires an argument -- 'X'\n`, with the exact string used to invoke the program in place of `ARGV0` and the relevant option letter in place of `X`. Thus invocation as `/workspace/executable -b` produces `/workspace/executable: option requires an argument -- 'b'\n`, while invocation as `./executable -b` produces `./executable: option requires an argument -- 'b'\n`. The same invocation-dependent prefix applies to all eight required-value options.

An unknown short option exits 1, writes exactly `ARGV0: invalid option -- 'X'\n` to stderr using the same invocation-dependent `ARGV0`, and writes the complete help text to stdout. For an unsupported long option beginning `--`, the reported invalid character is `-`; `/workspace/executable --invalid` and `/workspace/executable --help` therefore produce `/workspace/executable: invalid option -- '-'\n`. Stop on the first parse error: `/workspace/executable -X -h` and `/workspace/executable -X -Y` both report `/workspace/executable: invalid option -- 'X'\n`. `--` itself ends option parsing, and all later tokens—including dash-prefixed tokens—are positional paths. Multiple positional tokens are accepted without a usage error, but only the first one controls the initial location; later positional tokens are ignored. They do not form an input-path list. Thus, if the first token names a file, the program browses that file's parent and shows every normally visible entry there, not merely the positional arguments.

The filter choices `-g` and `-z` are mutually exclusive. If both are enabled, in either order and whether one came from the environment, exit exactly 1 with empty stdout and stderr. `-F` applies the native integer conversion and accepts conversion results `0` and `1`. Consequently `-F -1`, `-F 2`, and `-F 999` exit 1 with empty stdout and stderr, while `-F garbage` converts to preview mode `0` and proceeds to browsing; without terminal input that latter invocation exits 1 with empty stdout and `0 entries\n` on stderr. The documented `-T` sort arguments are `a d e r s t v` and the uppercase reverse forms `A D E S T V`, but the command-line parser does not reject an unrecognized or empty argument. In particular, each of `-T x`, `-T 0`, `-T q`, and `-T ''` proceeds to normal browsing; with empty nonterminal input each exits 1 with empty stdout and exactly `0 entries\n` on stderr. Every repeated `-T` occurrence is applied, including an unrecognized one: `-T v -T x` clears the earlier version sort and browses in the default lexical order (`a1`, `a10`, `a2`) with no `V` indicator. Numeric-looking arguments to `-l` and `-t` must never overflow or crash; zero, negative, nonnumeric, and very large strings are handled as the native 5.2 parser handles integer conversion, without being mistaken for unknown options.

## Spec 5

The command-line switches have these startup effects and can be freely combined unless a conflict is stated:

- `-a`: create and use an automatically named temporary FIFO and remove that automatic FIFO on exit.
- `-A`: disable automatic entry into a directory when a filter has a unique directory match.
- `-b KEY`: immediately open the bookmark mapped to the case-sensitive one-character key; this takes precedence over `-s` and `-S`.
- `-B`: use `bsdtar` rather than the default archive helper.
- `-c`: treat `NNN_OPENER` as a terminal/CLI opener; it takes precedence over `-e`.
- `-C`: use the eight-color scheme, coloring directories by context and disabling per-file 256-color classes.
- `-d`: start in detail/disk-usage display mode.
- `-D`: display directories using the active context color when file colors are configured.
- `-e`: configure the editor preference as `VISUAL`, otherwise `EDITOR`, otherwise `vi`. On the observed ordinary `.txt` opening path, the flag does not make Enter invoke that editor; the exact Enter and explicit-`e` behavior is in Spec 20.
- `-E`: use `EDITOR` for internal undetached edits.
- `-f`: enable persistent prompt/history storage.
- `-F 0`: FIFO preview notification mode; `-F 1`: FIFO explorer mode.
- `-g`: use regular-expression filters; `-z`: use order-preserving fuzzy filters.
- `-H`: include dot-prefixed entries initially.
- `-i`: expose extra current-file information.
- `-J`: selecting an item does not automatically move to the next entry.
- `-l VALUE`: set mouse-wheel scroll distance.
- `-n`: begin in type-to-nav/continuous-filter mode.
- `-N`: use the terminal's native prompt input mode.
- `-o`: navigation keys only enter directories; regular files open only on Enter.
- `-Q`: do not ask for confirmation before quitting when several contexts are active.
- `-r`: use advanced `cp`/`mv` progress behavior where available.
- `-R`: disable cursor wraparound at the top and bottom.
- `-S`: select persistent automatic-session startup. With no explicit path it attempts to open session `@`; if that session does not exist, the terminal is cleared and the final row reads exactly `open failed`, although the process remains alive. With an explicit path, that path is browsed instead; the save behavior is specified in Spec 23.
- `-t VALUE`: after that many idle seconds invoke the configured locker.
- `-u`: when an operation could use either the hovered item or existing selection, use the selection without prompting.
- `-U`: append owner and group names to file information.
- `-x`: enable operation notifications, selection synchronization hooks, and a non-picker xterm title.
- `-0`: use NUL rather than newline between picker output paths.

All of these recognized switches other than the absent-automatic-session case of `-S` initialize normally in a terminal, individually and in large combinations. A combination containing `-S` likewise clears the browser and shows `open failed` when automatic session `@` is absent. `-c` with `-e`, `-b` with session options, and display/filter/session options together remain syntactically valid combinations with the precedence above.

## Spec 6

The initial location defaults to the process current working directory. An explicit path may be absolute or relative and may contain spaces, quotes, shell metacharacters, Unicode, `.`/`..`, repeated or trailing slashes, and a leading `~`; resolve relative paths against the actual current directory and expand `~` using `HOME`. Strip a leading `file://` before local-path processing, including for `/` and dotfiles. Preserve legitimate path spelling where an exit file is expected, rather than gratuitously resolving all symlinks.

An existing directory is browsed. An existing regular file or symlink-to-file starts in its parent directory with that basename as the current entry. A symlink-to-directory can be browsed. Broken symlinks and circular/self-referential links must not recurse forever. With usable terminal input, if a nonexistent path ends in one or more `/`, recursively create it as directories and browse the result. Otherwise treat the last component as a requested new file: create missing parent directories, browse the parent, and prompt to create that basename. These creation steps occur only after terminal initialization. With empty nonterminal input, startup instead exits as in Spec 1 before creating anything: a trailing-slash target remains absent, and a requested-file target's missing parents also remain absent. A hidden target or hidden directory remains addressable regardless of the default hidden-file display. In noninteractive execution, nonexistent or unusable starting paths fail promptly and report zero entries rather than crashing.

## Spec 7

When standard input is not a terminal and contains data, interpret it as a NUL-separated list of paths. LF is ordinary path data, not an alternative separator. For example, the byte stream `.hidden\nfolder\ninvalid\n` is treated as one invalid pathname and produces an empty temporary list rather than three candidates. This nonempty-but-invalid case is not the empty-input behavior from Spec 1. Under `TERM=xterm-256color`, with those three individual names present in the current directory, it exits 1 with empty stderr after writing exactly the following 144 terminal-initialization/restoration bytes to stdout: `\x1b[?1049h\x1b[22;0;0t\x1b[1;24r\x1b(B\x1b[m\x1b[4l\x1b[?7h\x1b[?1h\x1b=\x1b[?1006;1000h\x1b[?25l\x1b[39;49m\x1b[?1006;1000l\x1b[39;49m\x1b(B\x1b[m\x1b[24;1H\x1b[?12l\x1b[?25h\x1b[?1049l\x1b[23;0;0t\r\x1b[?1l\x1b>`. NUL-delimited paths may include spaces, special characters, Unicode, dotfiles, directories, and very long names. Absolute paths are retained. A relative path supplied by itself is resolved against the actual current directory, but relative entries are not retained correctly when mixed with an absolute entry. Specifically, when the current directory is named `cwd` and contains `relative-é`, and an existing absolute input has basename `absolute name`, supplying the absolute input followed by `relative-é` produces a two-entry temporary listing containing `cwd/` and `absolute name@`, not `relative-é@`; its status line begins `1/2`. Ignore invalid NUL-delimited paths while retaining valid ones, tolerate empty input and mixed validity, and cap resource use at 16,384 paths or 64 MiB.

Present an input list through a temporary listing of symlinks while actions target the original objects. Following a listed symlink with Right/`l` visits its target; Enter opens/selects the symlink itself; `-` returns to the list. A supplied input list has priority over session startup. It can be filtered, navigated, and combined with picker mode.

## Spec 8

`-p DEST` enables picker mode. Before entering the UI, validate the destination. `DEST=-` means stdout and must never create a file named `-`. Any pre-existing destination file is unlinked at startup. If the destination parent does not exist, exit 1 with empty stdout and stderr `<label>: No such file or directory\n`; the leading decimal value is part of this build's diagnostic. An inaccessible or non-directory parent also causes status 1. Do not create an empty destination merely because picker mode started.

Space/`+` toggles an item in the cross-directory selection. Enter on a regular file immediately returns that single path when no explicit multi-selection is being finalized; directories remain navigable, and directories may also be selected with Space. On successful picker exit, write selected absolute paths in selection order. The default format is one path followed by `\n` per entry; with `-0`, every path is followed/separated by `\0` and no newline is introduced. Preserve UTF-8 names, spaces, quotes, and metacharacters exactly, and output symlink paths rather than resolved targets. `-p -` writes the same byte sequence to stdout. No selection produces no selection artifact and a failure/zero-entry result as described in Spec 1.

## Spec 9

The terminal UI is a one-column, full-screen interface. On a conventional 80-by-24 screen it has this stable logical layout:

1. The top line starts `1 2 3 4 5 6 7 8 ` and then shows the current directory. The current context is visually reversed, other active contexts underlined, and inactive contexts plain. Long paths are left-truncated/compacted to fit without corrupting multibyte text.
2. One blank line follows the header.
3. Entries occupy one row each, with the viewport scrolling as needed. Normal mode shows a one-character selection column and the decorated filename. Detail mode instead prefixes the current row with `>` and renders `YYYY-MM-DD HH:MM`, three octal permission digits, a right-aligned human-readable size/type marker, two spaces, and the decorated name. Terminal attributes may implement highlighting but snapshots must retain the described printable characters and spacing.
4. The final screen row is the status line. It begins `CURRENT/TOTAL`; for an empty view it is `0/0`. It then shows active state indicators, selection count (for example `+3`), the current entry's timestamp, symbolic mode such as `drwxr-xr-x`, optionally `user:group`, its human-readable size/type marker, and its extension (such as `.txt`) where applicable.

The current path, entry count, cursor index, current metadata, mode indicators, and selection count update immediately after every action. At most the viewport rows are shown; off-screen content is indicated, and the letter/control/page navigation bindings in Spec 13 select and scroll to the correct entries. Terminal resizes and redraws must not leave stale text.

## Spec 10

Directory enumeration excludes `.` and `..`. Dot-prefixed names are hidden by default and included under `-H` or after the `.` toggle; status includes `H` while enabled. Always group directories before nondirectories. Within each group the default comparison is case-sensitive lexical filename order, distinct from the case-insensitive natural/version order selected by `-T v`. Numeric portions are lexical in the default order: under `LC_ALL=C.UTF-8`, `A1`, `A10`, `A2`, `a1`, `a10`, `a2` appear in that order, and a file group containing `B2`, `a1`, and `b10` appears in exactly that order. Sorting and display must support thousands of files and Unicode without invalid memory access.

Decorate types in both compact and detail listings: directories end `/`, symbolic links end `@` (a symlink to a directory may display `@/`), executable regular files end `*`, FIFOs end `|`, and sockets and device/special files receive their standard distinct type treatment. Broken links remain visible and marked. No suffix is added to an ordinary regular file. Selection replaces the leading blank with `+`.

## Spec 11

The status and detail metadata come from the filesystem and refresh after changes. Timestamps use local `YYYY-MM-DD HH:MM` in 24-hour form. The detail column uses octal permission bits (`644`, `755`, etc.); the status uses full symbolic mode including type and special bits. `-U` appends `user:group` after symbolic permissions. Display the hovered file's extension including the leading dot, or nothing for a name with no extension.

Sizes use powers of 1024 with units `B K M G T P E Z Y`, retaining useful single-decimal precision for aggregates: examples are `0B`, `24B`, `612B`, `1.2K` for 1234 bytes, `3.5K` for 3579 bytes, `100K`, and `5M`. In detail mode symlink and FIFO size cells use `@` and `|`. Status always describes the current entry even when compact mode hides per-entry columns. Empty directories render a valid blank listing and `0/0`.

`f`/Ctrl-F opens a paged detailed-stat view for the hovered object, containing at least its exact name, type, mode, owner, timestamps, and byte size; a key press returns to the unchanged browser. `?` similarly presents the interactive key/configuration help through `PAGER`. `-i` makes the additional current-file information continuously available in the info area instead.

## Spec 12

Sorting always preserves the directory-first grouping. `-T` and the interactive sort menu support:

- `a`: apparent recursive disk usage;
- `d`: allocated-block recursive disk usage;
- `e`: extension, ascending;
- `s`: size, descending;
- `t`: selected time field, newest first;
- `v`: case-insensitive version/natural filename order;
- `r`: reverse the active order.

Uppercase sort keys reverse their lowercase default except `r`. In particular, with files `a1`, `a2`, and `a10`, `-T V` displays `a10`, `a2`, `a1` and shows the contiguous status indicators `RV`. The usage modes do not put standalone `A` or `D` indicators in the status line. Apparent usage is identified by the aggregate label `au:`, and allocated disk usage by `du:`. Other status indicators are `E` for extension, `S` for size, `M` for modification-time order (or the appropriate selected access/change time indication), `V` for version, and `R` for reversed order. The interactive `t`/Ctrl-T menu accepts a sort key; repeated Ctrl-T cycles filename, size, and time order. `T` chooses access, metadata-change, or modification time. Equal keys fall back deterministically to filename order.

In usage modes recursively total directory contents. Do not follow symbolic links; do not double-count the same inode through hard links. Empty and deeply nested directories are valid. Allocated and apparent modes differ for sparse files. Toggling the active usage/detail mode off restores the compact listing and ordinary ordering state.

## Spec 13

Navigation bindings are:

- Up or `k`: previous entry; Down or `j`: next entry.
- Left or `h`: parent; Right or `l`: enter the selected directory (or navigate to a symlink target as appropriate); Enter opens the selected entry.
- PageUp/Ctrl-U and PageDown/Ctrl-D move by a page/half-page as appropriate and scroll the viewport.
- `g`/Ctrl-A goes to the first entry; `G`/Ctrl-E goes to the last. In a three-entry listing, the named Home and End key sequences emitted by `tmux send-keys` under the `xterm-256color` PTY used here are both interpreted as the `~` action: each visits `HOME` rather than selecting a listing endpoint. Named End also visits `HOME` with `-R` and in a 60-entry listing longer than one viewport.
- Apostrophe opens the exact prompt `first file (')/char?`; it does not move immediately. At that prompt, a second apostrophe selects the first nondirectory entry, while another character selects the first entry beginning with that character. For `adir/`, `bfile`, `cfile`, apostrophe followed by apostrophe selects `bfile` at `2/3`, and apostrophe followed by `c` selects `cfile` at `3/3`.
- `J` shows relative offsets and the prompt `jump (+n/-n/n):`; a valid absolute or signed relative number moves accordingly, while Escape cancels.
- `~` visits `HOME`; backtick visits `/`; `@` visits the launch directory; `-` swaps with the previous/marked directory.
- `,` marks the current directory for later `-`; Ctrl-L rereads and redraws without otherwise changing state.

By default moving beyond the last entry wraps to the first and moving above the first wraps to the last. `-R` clamps at the edges. Entering and leaving directories should restore a sensible cursor on the directory just left. Navigation works through deep trees, symlinked directories, empty/unreadable directories, and large listings. The lone Left-arrow behavior is required even when alternative vim keys are unused.

## Spec 14

There are eight independent contexts. Number keys `1` through `8` visit or create the corresponding context. A newly created context copies the current context's state; thereafter each retains its own directory, cursor, filter, sort mode, and selection view. Tab cycles forward only through active contexts; Shift-Tab cycles in reverse or creates another context when possible. The header always advertises all eight context numbers and visually distinguishes current, other active, and inactive contexts.

`q` quits the current context; if it is the only context it exits the program. With multiple active contexts, ordinary quit may confirm unless `-Q` is set. Ctrl-Q does not quit this build: in a single context it leaves the process alive, writes no exit status, and leaves the displayed browser state unchanged; after ordinary `q` has closed one of two contexts, Ctrl-Q likewise leaves the process alive and writes no exit status. Ctrl-G performs quit-and-change-directory. Uppercase `Q` always exits with status 1. In picker mode it first emits any nonempty selection in the configured picker format, and it also writes the configured `NNN_TMPFILE`; these artifacts do not change its status to success. Context switching must not lose global cross-directory selections.

## Spec 15

`/` opens the live filter prompt. Ordinary string filtering is case-insensitive substring matching by default. At the empty prompt, `:` toggles case sensitivity and `/` cycles string (`str`), fuzzy (`fzy`), regular-expression (`reg`), then string mode, reflected in the status/prompt. Escape leaves the prompt without crashing; Backspace removes one input character and recomputes; Ctrl-L clears/toggles the last filter. Empty filters and empty directories are valid.

`-n` starts type-to-nav so ordinary typed characters immediately filter without first pressing `/`, and navigation into directories continues in filter mode. A unique matching directory is entered automatically unless `-A` is active. `-g` uses regular expressions supporting anchors, character classes, escapes, and quantifiers; invalid patterns are handled without termination. `-z` uses fuzzy matching: every query character must occur in order, not necessarily contiguously; spaces, underscore, and hyphen are normalized equivalently. Filtering supports UTF-8 queries and filenames and hundreds of entries. Examples: `apl` matches `apple.txt`; `aet` can match `apple.txt` and `artichoke.txt` but not `tea.txt`; `^test`, `\.txt$`, `[td]`, and `.*[0-9]` have their normal regex meanings.

## Spec 16

Selection is global across directories and contexts. Space or `+` toggles the hovered item; by default a new selection advances the cursor, while `-J` leaves it in place. `m` starts/stops range selection, `a` selects every currently listed item (including directories), and `A` inverts selection in the current listing. Selected rows have a leading `+`; status has `+N`. Toggling a selected item removes it and decrements the count. Selection order is deterministic and is preserved when exported.

Store selected absolute paths in the configured shared selection file. Copy does not clear it; successful move or removal does. `E` edits the selection through `EDITOR`, one absolute path per line, and remains usable with no in-memory selection by reading the selection file. `S` displays the aggregate size of visible selected items: normal mode counts a directory entry itself, while disk-usage mode recursively counts directory contents. With no selection show exactly `0B`.

## Spec 17

The filesystem-operation keys operate on the selection (or, after the normal hovered-versus-selection prompt, the hovered item): `p`/Ctrl-P copies to the current directory, `v`/Ctrl-V moves there, `x`/Ctrl-X uses configured trash/removal, and `X` performs recursive permanent removal. For a prompted removal, `s` chooses the selection, then `y` confirms and `n` cancels. Cancellation changes nothing.

Copy and move support one or many files and recursive directory trees; preserve bytes, UTF-8 names, symlinks as symlinks, hierarchy, and permission bits. Copy leaves sources and selection intact. Move removes sources and retains exact content at the destination. Delete removes empty and nonempty directories recursively after confirmation. Handle empty and large files and names with spaces, punctuation, and Unicode. A name collision must prompt rather than silently replace an existing object.

Ctrl-R renames the hovered item using an editable prompt prefilled with its current name. Ctrl-U clears prompt text. Empty input or Escape cancels. A new Unicode or special-character name preserves content. A slash in entered text is a path separator and creates/navigates the requested hierarchy rather than becoming a literal filename character. Renaming to an existing name requires explicit overwrite confirmation.

## Spec 18

`n` prompts for a new object type, including at least `f` for a regular file and `d` for a directory, and then prompts for `path/name`. Create parent directories when the supplied name contains slashes. Empty input and Escape cancel. New files are empty and are created with mode 0600 (subject only to a more restrictive umask); new directories are mode 0755 subject to umask. Names can contain spaces and Unicode. If a file exists, display an `overwrite?` confirmation: `n` preserves it exactly, while `y` truncates/recreates it as an empty file. Refresh the listing after success.

`*` toggles executability. If no execute bit is present, add execute bits consistently (for example a 0600 file becomes 0711 in this build); if executable, remove execute bits while preserving read/write bits. It applies reliably to consecutive files and directories and updates the `*` marker and metadata immediately.

## Spec 19

`r` performs batch rename. If both a selection and current-directory entries are possible, prompt for `s` (selection) or `c` (current directory). Write the chosen original names one per line to a temporary file, invoke `EDITOR` on it, and map each edited line position back to the original entry. Apply the resulting renames atomically enough to avoid content loss. An unmodified editor file is a no-op. Preserve Unicode and file content.

`w`/Ctrl-W performs copy-as or move-as: prompt for `c` or `m`, open the same kind of editable name list in `EDITOR`, then copy or move every selected entry under the edited destination names. Copy-as retains originals; move-as removes them. Multiple selections are supported, and no editor changes means no destructive change.

## Spec 20

`!` (or Ctrl-]) suspends the UI and starts `SHELL` in the browser's current directory, with `PWD`, `PATH`, and other environment state inherited and the special variable `nnn` set to the hovered filename. On shell exit, resume the same browser directory and cursor and refresh filesystem changes. Repeated shell launches work.

`]` opens a persistent one-line shell command loop in the current directory. Its prompt is exactly `>>> `. Execute metacharacters, redirections, pipelines, `&&`, globs, and commands through the configured shell. After each submitted command, display exactly `'Enter' to continue`; Enter dismisses that pause and returns to another `>>> ` prompt rather than to the browser. Submitting an empty command at that next prompt exits the command loop, restores the browser, and refreshes filesystem changes. A failed command reports failure but does not terminate the browser. A `cd` inside a child command does not change the browser's directory: after `cd /`, dismissing the pause and then submitting an empty command restores the original browser directory.

`=` displays an `app:` prompt and launches the entered application/command for the hovered item; empty input cancels. `o`/Ctrl-O first prompts with `open with:`. After an application is entered it displays exactly `['g'ui]/'c'li?`; the user must then choose `g` or `c` before the application is launched for the selected/hovered path. The `c` choice passes a path containing spaces as one exact argument. With no applicable entry it is blocked rather than invoking an arbitrary command. Enter on a nonempty ordinary file uses `NNN_OPENER` when configured, otherwise the platform desktop opener, and `-c` makes the custom opener terminal-attached. `-e` does not redirect the observed ordinary `.txt` case to an editor: with a lone nonempty `document.txt`, `-e`, and executable scripts configured for both `VISUAL` and `EDITOR`, Enter leaves the browser screen unchanged and invokes neither script. In the same setup, the explicit `e` binding invokes `VISUAL` with the absolute path to `document.txt` and does not invoke `EDITOR`. In the `-c -e` combination, `-c` wins for a nonempty file. A zero-byte regular file is a special case: Enter invokes neither custom opener nor editor and displays exactly `empty! edit/open with`. `>` exports the current visible file list to a newline-delimited temporary file in display order and opens `EDITOR`; it must not reorder or collapse special filenames.

## Spec 21

`z` creates an archive from the selected or hovered entries. When a selection exists, it first displays exactly `'c'urrent/'s'el?`; `c` chooses the hovered current entry and `s` chooses the selection. Only after that choice does it display `archive [path/]name:` and accept the destination archive name. Typing an archive name at the source-choice prompt does not create an archive. Empty destination input or Escape cancels. Support at least tar/gzip archives and, through the selected archive helper, names with spaces, long filenames, directories (including empty ones), and multiple members. Preserve file content and hierarchy. If the destination already exists, ask for confirmation and overwrite only on `y`.

Opening a recognized archive offers archive operations. Extraction prompts for a destination; `.` means the current directory, an explicit path is created/used, and empty input or Escape cancels. Extract `.tar.gz` and `.zip` content with correct nested files. `NNN_ARCHIVE` is a regular-expression pattern matched against archive filenames, not a literal extension or delimiter-separated list; regular-expression alternation with `|` is supported. For example, `NNN_ARCHIVE=\.(foo|bar)$` recognizes `bundle.foo` as an archive. `NNN_ARCHMNT` selects the optional mount helper; `-B` chooses `bsdtar` semantics.

## Spec 22

Bookmarks supplied in `NNN_BMS` use `KEY:PATH` pairs separated by semicolons. Keys are one character and case-sensitive; paths may contain spaces, `~`, and ordinary colon/path syntax. An empty variable means no bookmarks. A nonempty malformed pair without a colon is a startup error. `b`/Ctrl-_ opens a bookmark prompt, accepts its key, and visits the mapped directory; an invalid key or broken target reports/ignores it without crashing and leaves the browser usable. Visiting a bookmark through this in-UI prompt sets the old location as the previous directory for `-`.

Once usable terminal startup reaches bookmark validation, a multi-character startup bookmark argument is a fatal validation error rather than an unknown-bookmark lookup: `-b ab` exits 1 before browsing, writes nothing to stdout, and writes exactly `invalid key\n` to stderr. Empty nonterminal input is detected earlier than this validation or any filesystem-bookmark lookup. Thus nonterminal `-b ab` when `NNN_BMS` maps `a` to the current directory, and nonterminal `-b broken_test` when the configuration bookmark named `broken_test` is a symlink to a nonexistent target, both exit 1 with empty stdout and exactly `0 entries\n` on stderr.

`B` creates a symlinked bookmark for the current location in the configuration bookmark directory. `,` is the separate in-memory mark operation. A startup `-b KEY` directly opens the configured bookmark, with bookmark/list input taking precedence over sessions. Unlike visiting through the in-UI bookmark prompt, startup `-b KEY` does not record the process launch directory as the previous directory. If no other previous directory has been established, pressing `-` immediately after startup leaves the browser in the bookmarked directory and displays exactly `not set` on the final row.

## Spec 23

Sessions store all active contexts, directories, cursor/hover state, filters, sort/display settings, and enough selection state to restore work. Session files live under `${XDG_CONFIG_HOME:-$HOME/.config}/nnn/sessions`; `@` is the automatic session. `s` opens the session manager; choosing `s` there prompts for and saves a case-preserving name, while the corresponding load choice restores a named session. `-s NAME` loads that session on startup. Names may contain safe punctuation such as hyphens and underscores and long valid components; overlong names are rejected or safely bounded, never overflowed.

Saving creates or replaces the named file; loading restores the directory and selected cursor. Multiple names remain distinct. Loading a nonexistent/corrupt named session leaves the program in the requested/current directory rather than crashing. Automatic `-S` startup differs according to whether a positional path is present. With no path and no existing `@`, startup shows `open failed`; quitting normally with `q` then creates `sessions/@`. With `-S PATH`, the explicit directory is browsed and `q` exits 0, but it creates only the `nnn/sessions` directory and does not create `sessions/@`. A runtime load first saves the previous working state to the automatic session.

## Spec 24

Configuration is entirely via environment variables and files below `${XDG_CONFIG_HOME:-$HOME/.config}/nnn`. If `XDG_CONFIG_HOME` is explicitly set, it must already exist and be accessible when configuration/picker setup requires it; otherwise startup fails. `HOME`, `PWD`, `TMPDIR`, `TERM`, `SHELL`, `PAGER`, `VISUAL`, and `EDITOR` are consumed safely when present, empty, invalid, or pointing to unavailable commands. For editing, `VISUAL` has precedence over `EDITOR`, then `vi`; external command absence reports failure and returns to the UI.

`NNN_OPTS` is a compact string of independently processed option letters, processed as startup options before CLI options; it needs no leading dash and does not use the command line's attached-value syntax. Letters such as `F`, `T`, and `s` are accepted individually, but they do not consume following characters as values. Thus `F1` fails on the separately processed `1`, `Tv` fails on `v`, and `sname` fails on `m`; `NNN_OPTS=F1`, `NNN_OPTS=Tv`, `NNN_OPTS=sname`, and `NNN_OPTS=F1Tvsname`, even when followed by CLI `-V`, each exit 1 with the complete help text from Spec 2 on stdout and empty stderr. Other unknown environment letters behave the same; specifically, `NNN_OPTS=Y ./executable -V` has empty stderr. Conflicts such as environment `g` plus CLI `z` fail before help/version can short-circuit. An empty value is harmless, and combinations such as `HdR` are accepted. CLI options may add to or override nonconflicting environment choices.

Recognize these optional variables without spurious argument errors: `NNN_OPENER`, `NNN_COLORS`, `NNN_FCOLORS`, `NNN_ARCHIVE`, `NNN_ARCHMNT`, `NNN_SEL`, `NNN_FIFO`, `NNN_LOCKER`, `NNN_TMPFILE`, `NNN_MCLICK`, `NNN_TRASH`, `NNN_PIPE`, `NNN_SSHFS`, `NNN_RCLONE`, `NNN_INCLUDE_HIDDEN`, `NNN_PREFER_SELECTION`, `NNN_LIST`, `NNNLVL`, and `NO_COLOR`. `NNN_SEL` accepts either an absolute or relative custom shared-selection path. A relative value is resolved against the process working directory: with `NNN_SEL=relative-selection`, startup succeeds, and selecting `item` creates `./relative-selection` containing the absolute path to `item` with no trailing newline or NUL. `NO_COLOR` disables ANSI colors unless explicit color configuration overrides it.

## Spec 25

`NNN_COLORS` supplies per-context colors either as up to eight `0`–`7` digits, as `#` followed by pairs of xterm-256 hex values, or both forms separated by `;`; malformed color text is ignored/falls back rather than breaking `-h`/`-V`. `NNN_FCOLORS` is a sequence of hex byte pairs for, in order, block device, character device, directory, executable, regular file, hard link, symlink, missing/details, orphan link, FIFO, socket, and unknown/zero-byte file. Short valid sequences configure the available prefix and fall back for the rest. `-C` forces the eight-color behavior; `-D` uses context color for directories.

`NNN_ORDER` is a semicolon-separated set of `SORTKEY:ABSOLUTE_DIRECTORY` rules and chooses directory-specific sort mode. A rule whose sort key is unknown, such as `x`, is ignored rather than treated as a startup error; even when its directory matches the starting directory, browsing continues in the default order. As specified in Spec 3, such a rule also does not preempt terminating `-V`. `NNN_MCLICK` accepts a single key or control notation such as `^X`. `NNN_TRASH` is either a command or the special values `1`/`2`. Empty optional strings must not fail startup unless their variable's grammar explicitly requires a mapping.

## Spec 26

`NNN_PLUG` contains at most 100 case-sensitive `KEY:ACTION` pairs separated by semicolons. Reject malformed nonempty pairs, empty keys, and empty actions without crashing. A normal action names an executable plugin; resolve an unqualified plugin in the configured plugin directory or execute an explicit path. `-P KEY` runs a configured plugin at startup; `;` followed by a key and Alt-key invocation run it interactively. Missing mappings, nonexistent files, non-executable scripts, and nonzero exits are recoverable errors.

Before plugin execution set the working directory to the current browser directory, set `nnn` to the hovered filename, and expose `NNN_SEL`/the shared selection. An action prefixed `-` suppresses the post-plugin refresh. An action prefixed `!` is a shell command. The modifiers `&` and `|` after `!` mean detached/background GUI execution and captured/paged output respectively; shell pipes, redirection, quoting, and special characters remain functional. Commands can create files and read the current selected filename, and the UI refreshes when appropriate. A startup `-P` shell action can finish its filesystem work before the browser is repainted: after `-P x` with `NNN_PLUG=x:!touch plugin-created`, the file is created in the browser directory and the terminal displays exactly `'Enter' to continue`. Pressing Enter dismisses this pause, returns to the browser, and the refreshed listing contains `plugin-created`.

## Spec 27

If `NNN_FIFO` names a FIFO, create it during usable terminal initialization if absent as an actual named pipe with mode 0600, without deleting a user-specified FIFO on exit; reuse an existing writable FIFO. Empty nonterminal input exits with the Spec 1 result before this creation step, so an absent user FIFO remains absent. With a reader connected, immediately notify the initial hovered entry and notify every later hover/navigation change. Each message is exactly the relevant absolute path plus one LF byte—no quoting, metadata, CR, or extra whitespace. Send the symlink path under the cursor rather than its target, and preserve spaces and deep path components. An empty directory sends no bogus path.

Readerless user-FIFO operation does not block this build. With `NNN_FIFO` naming a newly created FIFO and no reader connected, the browser creates and retains the mode-0600 FIFO, renders normally, and after `j`, `k`, and `q` exits promptly with status 0 without waiting for a reader. FIFO handling with a reader must survive disconnect/reconnect and `EPIPE`, and must retain rapid navigation events in order as far as pipe capacity allows. Preview mode (`-F 0`) and explorer mode (`-F 1`) use their respective event semantics; invalid numeric modes fail before terminal initialization as detailed in Spec 4. `-a` overrides a supplied FIFO with an automatically managed temporary FIFO and exports its path to children. Parent directories must already exist; invalid/unwritable FIFO paths fail gracefully. Close FIFO descriptors on a completed exit.

## Spec 28

The browser must re-read filesystem state on Ctrl-L and after returning from commands or operations. It may also watch for changes, but an explicit refresh is authoritative. External file creation, deletion, rename, directory creation, symlink retargeting, and chmod must update names, counts, type suffixes, permissions, and selection/cursor position without stale rows. Refreshing an unchanged directory leaves the visible state unchanged.

Handle empty directories, 10,000-entry directories, 255-byte filenames, long paths near platform limits, deeply nested trees, readonly/unreadable/unsearchable directories, broken/circular symlinks, zero-byte and sparse files, special permission bits, pipes/sockets/devices, Unicode from multiple scripts, and punctuation-heavy names. Never follow a loop indefinitely or crash on a concurrently vanished entry. Keep navigation responsive and clamp/reposition the cursor if its entry disappears.

On SIGTERM or SIGHUP while in the TUI, restore terminal state and exit gracefully rather than segfaulting or emitting a signal-derived crash status.

## Spec 29

Regular `q` without shell-integration configuration exits without writing a change-directory file. Ctrl-G “quit-and-cd” exits and writes the current directory through `NNN_TMPFILE`; uppercase `Q` also completes the configured quit/picker result and must honor `NNN_TMPFILE`. When `NNN_TMPFILE` is set, expand a leading `~` in its filename and enable always-write-on-exit behavior expected for shell integration: replace any previous content rather than append, and encode a command beginning `cd ` followed by a safely single-quoted current path. The command must work for spaces, quotes, metacharacters, nested paths, and empty directories. Use an absolute path without a trailing slash except for root. Preserve the browser's directory-symlink spelling rather than resolving it: when the explicit starting path is a directory symlink, quitting writes the absolute spelling of that symlink in the `cd` command and does not substitute the target path.

Quitting from picker mode first finalizes picker output. Quitting after child shells, plugins, editors, failed commands, cancelled prompts, multiple contexts, or filesystem errors must still clean temporary files/FIFOs owned by the process, leave user files untouched except for confirmed operations, and return a deterministic success/failure status.
