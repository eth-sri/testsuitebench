# Pipr executable specification

## Spec 1: Required artifact and scope

Provide one executable file named exactly `executable` at the repository root. It is a Unix command-line program and interactive terminal UI for constructing and trying shell pipelines. It must be directly executable.

The program has a traditional flag-only interface. It has no subcommands and must not print errors such as “unknown subcommand”, advertise a `Commands:`/`Subcommands:` section, or interpret words such as `help`, `add`, or `list` as subcommands. Non-option operands do not select another mode. A lone `--` ends option parsing.

The evaluation environment provides any terminal-driving harness used to interact with `executable`; that harness is not part of this artifact.

## Spec 2: Command-line interface

The accepted options are:

| Option | Meaning |
| --- | --- |
| `-d TEXT`, `--default TEXT` | Initial text in the command editor. |
| `-o FILE`, `--out-file FILE` | On exit, overwrite `FILE` with the final command. |
| `--in-file FILE` | Read the initial editor contents from `FILE`. This takes precedence over `--default`, independent of option order. |
| `--config-reference` | Print the default configuration shown below and exit successfully. |
| `-r`, `--raw-mode` | Preserve line breaks when producing the final command. |
| `--no-isolation` | Execute edited commands directly rather than through bubblewrap. |
| `-h`, `--help` | Print help and exit successfully. |

Long value options accept both `--name VALUE` and `--name=VALUE`. Short value options accept a separate value or an attached value (`-dTEXT`, `-oFILE`). An equals sign in a short attached value is data, not syntax: `-d=VALUE` initializes the editor to `=VALUE`, and `-o=out` names the output file `=out`. Short flags may be clustered; for example, `-rh` means `-r -h`, while a value-taking option consumes the remainder of its cluster as its value.

Option values are opaque byte/string arguments, not further parsed as flags. Empty, whitespace-only, numeric, Unicode, control-containing, shell-special, multiline, and very long values are accepted by argument parsing; the TUI's observed mixed-width length boundary is specified in Spec 8. Paths may be relative and may contain spaces, special characters, or Unicode. Do not silently abbreviate or case-fold long option names. Undocumented options such as `--version`, `--verbose`, `--quiet`, `--debug`, and `--config` are invalid.

The value options `--default`, `--out-file`, and `--in-file` may each occur at most once. Repeating one is an error even if `--help` is also present. Repeating simple Boolean flags need not toggle their meaning.

After syntactic validation, action precedence is:

1. `-h`/`--help`, regardless of its position, prints help without reading input files, loading configuration, checking bubblewrap, opening output files, or requiring a terminal.
2. Otherwise, `--config-reference` prints the reference without those runtime checks.
3. Otherwise, normal startup checks isolation before reading `--in-file`, then performs the remaining configuration, file, and terminal work and starts the TUI.

Initial text is converted to editor lines in the same way for `--default` and `--in-file`. One line break at the very end does not create a final empty editor line. Thus a file ending in `echo "line 1"\necho "line 2"\necho "line 3"\n` displays three command rows, not four. Apart from that terminal-line rule, embedded line breaks are retained. Merely loading nonempty initial text does not auto-evaluate it, even when auto-evaluation is enabled.

## Spec 3: Exact help output

Both help forms must exit 0, write nothing to stderr, and emit the same text. `PROGRAM` below is the program name used to invoke the executable (normally `./executable`):

```text
Usage: PROGRAM [options]

Options:
    -d, --default TEXT  text inserted into the textfield on startup
    -o, --out-file FILE write final command to file
        --in-file FILE  read initial command from file
        --config-reference 
                        print out the default configuration file
    -r, --raw-mode      keep linebreaks in finished command when closing
        --no-isolation  disable isolation. This will run the commands directly
                        on your system, without protection. Take care.
    -h, --help          print this help menu
```

There is one terminating newline and no leading blank line.

## Spec 4: Argument errors

Argument syntax errors exit 1 and are written to stderr, with no stdout. Use these newline-terminated forms, where `PROGRAM` is the invocation name:

```text
PROGRAM: Unrecognized option: 'NAME'
PROGRAM: Argument to option 'NAME' missing
PROGRAM: Option 'NAME' given more than once
```

For an unrecognized or missing-argument short option, `NAME` is the single option character. Thus `-help` reports the first unrecognized short character, `e`. For a long option, omit the leading dashes from `NAME`. A repeated value option instead uses its canonical long name regardless of the spelling that caused the duplicate: `default`, `out-file`, or `in-file`. For example, `--help -d a -d=b` exits 1 and writes `PROGRAM: Option 'default' given more than once` followed by a newline to stderr.

Once the isolation check has passed or `--no-isolation` is present, an unreadable or nonexistent input file is a startup error with nonzero status. For a missing Unix path, report:

```text
Error: No such file or directory (os error 2)
```

An output target that is a directory, or whose parent cannot be created/opened, is also a nonzero startup/exit error.

## Spec 5: Isolation and terminal requirements

Normal execution is isolated and requires the `bwrap` program on `PATH`. If it is unavailable, exit 1, write nothing to stderr, and write exactly this newline-terminated message to stdout:

```text
bubblewrap installation not found. Please make sure you have `bwrap` on your path, or supply --no-isolation to disable safe-mode
```

This check precedes opening `--in-file`. Consequently, with `bwrap` absent, `--in-file /tmp/programbench-pipr-nonexistent/nonexistent.txt` reports the bubblewrap message above rather than the missing-file diagnostic.

`--no-isolation` bypasses that check and runs commands directly with the configured evaluation command. Help and configuration-reference output never require bubblewrap.

Interactive mode requires a real terminal. If started with `--no-isolation` while standard input/output is not a usable TTY, fail promptly with a nonzero status rather than hanging or crashing.

## Spec 6: Exact default configuration reference

`--config-reference` exits 0, writes nothing to stderr, and writes exactly the following UTF-8 text to stdout, including the initial and final blank lines. Its last bytes are `less"\n\n`:

```toml

#  ____  _
# |  _ \(_)_ __  _ __       .________.
# | |_) | | '_ \| '__|      |________|
# |  __/| | |_) | |          |_    -|
# |_|   |_| .__/|_|     xX  xXx___x_|
#         |_|
#
# A commandline utility by
# Leon Kowarschick

# finish_hook: Executed once you close pipr, getting the command you constructed piped into stdin.
# finish_hook = "xclip -selection clipboard -in"

# Paranoid history mode writes every sucessfully running command into the history in autoeval mode.
paranoid_history_mode_default = false

autoeval_mode_default = true

history_size = 500
cmdlist_always_show_preview = false
cmd_timeout_millis = 2000

highlighting_enabled = true

eval_environment = ["bash", "-c"]

# Snippets can be used to quickly insert common bits of shell
# use || (two pipes) where you want your cursor to be after insertion
[snippets]
s = " | sed -r 's/||//g'"

[help_viewers]
'm' = "man ??"
'h' = "?? --help | less"

[output_viewers]
'l' = "less"

```

## Spec 7: Configuration and state locations

On interactive startup, load TOML configuration from:

- `$XDG_CONFIG_HOME/pipr/pipr.toml` whenever `XDG_CONFIG_HOME` is set, including when its value is empty;
- otherwise `$HOME/.config/pipr/pipr.toml`.

An empty `XDG_CONFIG_HOME` therefore produces the relative path `pipr/pipr.toml` under the process working directory; it does not fall back to `$HOME/.config`. If the directory or file does not exist, create it. The created file is the configuration-reference text with one of its two final newlines removed: it begins with the same initial blank line and ends in the bytes `less"\n`, with no final blank line.

An existing empty valid configuration is not replaced with the reference values. In particular, it starts with auto-evaluation and paranoid-history mode both off, so the title is `Command`, not `Command [Autoeval]`. Support all scalar/array keys and the three tables shown in the reference. An optional string `finish_hook` is accepted as configuration data and is executed on exit as specified in Spec 13.

The same `pipr` directory holds plain UTF-8 `history` and `bookmarks` files. Missing or empty files represent empty lists and must not prevent startup.

## Spec 8: Interactive display

The TUI must redraw in place, respond promptly to key input, and resize to the terminal. It uses Unicode box-drawing characters. The main view consists of a `Command` box above an `Output` box; when a failed evaluation has stderr to display, the available lower area is split into distinct `Output` and `Stderr` boxes. `Help: F1` appears at the bottom right.

Mode/state labels are appended to the command title in this order when applicable: `[Bookmarked]`, `[Autoeval]`, `[Paranoid]`. The `[Paranoid]` label is applicable only while auto-evaluation is on: F3 can enable paranoid mode internally while auto-evaluation is off, but the title remains `Command`; subsequently pressing F2 reveals `Command [Autoeval] [Paranoid]`. The command box grows for multiline input and the output region gives up the corresponding rows.

The output title has additional state chrome. `Output [+]` means the current editor text has not produced the displayed output. Nonempty text loaded at startup has this marker, as do ordinary edits made while auto-evaluation is off. Ctrl+X is a specific exception: when it clears such text to an empty buffer, it also clears `[+]`, leaving the title `Output`. During an evaluation the suffix is an animated braille spinner; after evaluation completes the title returns to `Output`. F7 away from a pipe is a no-op and does not clear `[+]`.

At 80 columns by 24 rows with a one-row command, while a stderr pane exists, the command box is followed by an `Output` box whose top and bottom borders are terminal rows 5 and 14, then a `Stderr` box whose borders are rows 15 and 23. For the edited command `cat /nonexistent/file.txt`, the first Stderr content row is exactly `cat: /nonexistent/file.txt: No such file or directory`. If a later evaluation has empty stderr, remove the Stderr pane and restore the full-height Output box. In particular, with auto-evaluation on, Ctrl+U after `hello world` clears both the editor and the resulting `bash: line 1: hello: command not found` pane.

At 80 columns by 24 rows, the default empty screen is exactly:

```text

 ┌ Command [Autoeval] ────────────────────────────────────────────────────────┐
 │                                                                            │
 └────────────────────────────────────────────────────────────────────────────┘
 ┌ Output ────────────────────────────────────────────────────────────────────┐
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 │                                                                            │
 └──────────────────────────────────────────────────────────────────Help: F1──┘
```

With auto-evaluation off, the title is simply `Command` even when paranoid mode is enabled internally; with both auto-evaluation and paranoid mode enabled it is `Command [Autoeval] [Paranoid]`. Content begins immediately after the left border. The UI renders normal shell text, tabs, quoting, escaping, CJK text, accents, and emoji for ordinary-sized input.

The reference has a specific long mixed-width boundary: starting it with `--default` equal to `界🙂ab` repeated 1,000 times exits 1 before drawing `Command` and, after leaving the alternate screen, prints these two lines:

```text
panicked at src/ui/mod.rs:<error location>:
assertion failed: self.is_char_boundary(new_len)
```

F1 replaces the main view with a `Help` view, and F1 again returns to the main view. The help text identifies F1 as “Show/hide help”, F2 as “Toggle autoeval”, and documents the interactive bindings described below.

## Spec 9: Command editor and keys

The editor is a multiline Unicode text buffer with a character-boundary-safe cursor.

- Printable input inserts verbatim at the cursor. Left/Right move one Unicode character. At line boundaries they wrap to the previous line’s end or next line’s start; at the beginning/end of the entire buffer they are no-ops.
- Up/Down move between editor lines and clamp the column to the destination line’s length. Home/End and Ctrl+A/Ctrl+E move to the start/end of the current line.
- Backspace and Ctrl+H remove the preceding character. At the start of a non-first line they remove the newline and join the line to its predecessor. Backspace at the start of the buffer is a no-op.
- Delete removes the character under the cursor. At the end of a non-final line it removes the newline and joins the next line. At the end of the buffer it is a no-op. A raw Ctrl+D key event is not a Delete alias: it inserts the lowercase character `d` at the cursor.
- Alt+Enter and Insert split the current line and place the cursor at the start of the new line without explicitly submitting it.
- Ctrl+U and Ctrl+X clear the command buffer. A raw Ctrl+L key event inserts the lowercase character `l` at the cursor; it is not handled as a redraw command.
- Enter evaluates the current command and records a nonempty command in history.
- Escape closes the current overlay/menu; from the main view it exits Pipr.

F2 toggles auto-evaluation and its title label. The configured default is on. F3 toggles paranoid-history mode; when enabled, every successfully auto-evaluated command is eligible for history rather than only explicit submissions. Its title label is visible only when auto-evaluation is on, as specified in Spec 8.

Ctrl+P and Ctrl+N provide direct history navigation in the main editor. Ctrl+P walks from the newest entry toward older entries. Ctrl+N walks toward newer entries, but reaching the newest history position restores the empty post-history buffer instead of loading the newest stored entry. For example, with persisted entries `one`, `two`, and `three`, an initially empty editor shows `three` after one Ctrl+P and `two` after a second Ctrl+P; the following Ctrl+N clears it to empty. From the oldest entry, one Ctrl+N does load the next entry.

## Spec 10: Evaluation

Evaluate commands by appending the command text to the configured `eval_environment` argv; by default this is equivalent to `bash -c COMMAND`. Before evaluation, replace line breaks between editor lines with one ASCII space, just as normal-mode finishing does. Thus splitting `echo line1echo line2` between the two `echo` words evaluates `echo line1 echo line2` and displays `line1 echo line2`. Preserve the process environment and working directory. In `--no-isolation` mode this is direct host execution.

Auto-evaluation starts/restarts evaluation after edits while enabled. A newer evaluation replaces and terminates any still-running older evaluation so stale output cannot be mixed into the new result. The default timeout is `cmd_timeout_millis = 2000`; a timeout is reported in the UI with `Command timed out` and must not freeze the editor.

Show captured stdout in `Output`. Show captured stderr in `Stderr` when the command exits unsuccessfully; stderr from a successful command is discarded. Thus `printf err >&2` exits successfully and leaves no Stderr pane, whereas `printf err >&2; exit 1` displays `err` in one. Successful pipelines and commands such as `echo`, `grep`, `cat`, `ls`, `sed`, and `awk` must behave as they do under the configured shell. A missing command or nonexistent input path is shown as shell stderr without terminating Pipr. Inline shell comments are displayed in the editor but have normal shell semantics, and a line beginning with `#` is omitted from the executed command.

With the default Bash environment, an edited unknown first word is rendered as `bash: line 1: WORD: command not found`. This applies after multiline flattening: `abc\ndef` produces the diagnostic for `abc`, and `line1\nline2` produces it for `line1`. At 80×24 these diagnostics occupy the first content row of the Stderr box described in Spec 8.

The UI remains responsive with ordinary input, rapid key presses, failed commands, empty commands, and output of at least 1,000 lines, subject to the mixed-width startup boundary in Spec 8. With the default 2,000 ms timeout, typing `seq 1 15000` under auto-evaluation eventually produces a Stderr pane containing `Command timed out`; completing that particular command and displaying all 15,000 lines is not the reference behavior.

## Spec 11: History and bookmarks

History and bookmarks use the same plain-text serialization: entries are stored verbatim and separated only by a line containing exactly `---`, represented between entries as `\n---\n`. Multiline entries remain one entry. There is no separator before the first or after the last entry. Preserve Unicode, tabs, whitespace, quotes, backticks, dollar signs, redirects, pipes, and long lines.

History behavior:

- Executing a nonempty command creates the history file if necessary.
- Do not append a command identical to the immediately preceding entry.
- Enforce `history_size` by discarding the oldest entries; the default limit is 500.
- F4 opens a `History` list. It displays entries oldest to newest, renders embedded newlines as ` ↵ `, and initially selects the newest entry with a `>>` prefix.

Ctrl+S toggles the exact current nonempty command as a bookmark and updates `[Bookmarked]`. With an empty editor it is a no-op: no bookmark is created and no label appears. Ctrl+B opens a `Bookmarks` list with the same ordering and display rules. In either list, Up/Down change selection, Enter loads the selected command into the editor and returns to the main view, and Escape cancels. Selecting a bookmark causes `[Bookmarked]` to appear.

With the default `cmdlist_always_show_preview = false`, History and Bookmarks use the same list-only layout at 80 columns by 24 rows, including when the list is empty. The list borders are on terminal rows 2 and 12. Rows 13 through 22 are blank, with no `Preview` box or other lower border, and row 23 contains the unbordered `Help: F1` at the bottom right. A three-entry list uses two spaces for unselected entries and `>>` for the selection. For example, a history containing `echo hello`, `ls -la`, and the multiline entry `grep pattern\nfile.txt` displays the last entry as selected text `>>grep pattern ↵ file.txt` on row 5; it does not separately render the selected entry below the list.

## Spec 12: Snippets, completion, viewers, and caching

Ctrl+V opens a left-side `Open in` selection pane listing configured snippets as `KEY: TEXT`, but with every `||` cursor marker removed from the displayed TEXT. For example, `u = "unicode 雪||"` is displayed as `u: unicode 雪`, and `s = "hello||world"` as `s: helloworld`. Selecting its key inserts the snippet at the editor cursor and closes the pane. Remove every `||` marker from inserted text and place the cursor at the first marker; if no marker exists, place it at the end. This applies to empty, marker-only, multiline, Unicode, whitespace-heavy, quoted, escaped, and very long snippets. Escape closes the pane without changing the command. At 80 columns, this snippet pane uses the same split geometry as the F5 and F6 menus: its box runs from terminal column 2 through column 32 inclusive, and the narrowed Command/Output view begins at column 33.

Tab performs filesystem completion on path-shaped words at the cursor. A bare relative prefix with no slash is ignored even when matching files exist: in a directory containing only `unique name.txt`, Tab leaves `cat uni` unchanged, and with `choice-a` and `choice-b`, it leaves `cat choice-` unchanged without opening Suggestions. If the cursor follows whitespace, completion starts from `./`; multiple matches appear in a `Suggestions` pane as marker-free rows immediately adjacent to the left border, such as the observed `│./xdg`, with no `>>` or two-space selection prefix. Tab advances, Shift+Tab moves backward with wraparound, Enter accepts, and an unrelated key closes the pane and is then handled normally. With no matches, leave the command unchanged and do not open an empty pane. A single absolute directory match is inserted without a trailing slash: `/tm` becomes `/tmp`. Tilde-prefixed paths are supported.

F5 opens configured help-viewer choices for the word under the cursor; when there is no word it is a silent no-op. Help-viewer templates use `??` as the target-word placeholder. F6 opens an `Open in` pane for output viewers (the default entry is `l: less`). At 80 columns, both menus occupy the left 30 columns while a narrowed live Command/Output view remains visible on the right; the menu rows have no `>>` selection prefix. Escape cancels either menu.

F7 acts only when the cursor is on a pipe, caching the output of the command portion through that pipe so later edits can reuse it. Away from a pipe it is a no-op. A failed cache operation is nonfatal and adds a `Stderr` panel containing, for an unknown command, `could not run command to cache: Non-zero exit code: 127`.

## Spec 13: Finishing, output files, and finish hooks

On exit, derive the final command from the current editor contents at that moment:

- first account for the fact that a single terminal line break in initial text was omitted when editor lines were constructed;
- normally, replace each line break that separates editor lines with one ASCII space;
- in `--raw-mode`, preserve line breaks exactly;
- do not otherwise trim, normalize, escape, expand, or add a trailing newline.

For exact examples, normal-mode initial text `  a\n\tb  \n` finishes as `  a \tb  `, and raw-mode initial text `a\nβ\n` finishes as `a\nβ`. The spaces and tab are preserved; only the terminal line break absent from the editor is lost.

A newline embedded inside a logical editor line by snippet insertion is not an editor-line separator and is therefore not flattened in normal mode. With the markerless snippet `m = "a\nb"`, selecting `m`, typing `X` at its end, and exiting without `--raw-mode` produces the exact final bytes `a\nbX`.

If `--out-file FILE` is supplied, create or truncate `FILE` and write exactly those UTF-8 bytes, even for an empty command. Never modify an `--in-file` source merely because it was also used to initialize the editor. Existing output content must be replaced, not appended.

After restoring the terminal, also write the final command to stdout followed by a newline, whether or not `--out-file` is present. For a final command `token`, a PTY observes `token\r\n` after the alternate-screen leave sequence, while the output file contains only the five bytes `token`.

When `finish_hook` is configured, execute it during every normal exit and pipe the exact final-command bytes to its standard input without adding a newline. Run it even when the final command is empty. Shell-special characters in the final command are stdin data, not expanded before delivery: a final command of `echo "hello $USER" | wc -l` reaches the hook as exactly those bytes. A hook that does not read stdin, such as `touch PATH`, is still executed.
