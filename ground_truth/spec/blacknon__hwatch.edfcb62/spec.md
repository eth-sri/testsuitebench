# Clarified executable specification

The required artifact is a runnable file named exactly `executable`. It implements a terminal command watcher compatible with hwatch 0.3.19. In the notation below, `ESC` means the single byte `0x1b`, and timestamps use the process's local time.

## Spec 1

`executable` has one command-line interface, not a hierarchy of subcommands. Its form is `executable [OPTIONS] [command]...`. Every positional token belongs to the external command to monitor; words such as `add`, `list`, or `remove` have no special dispatch meaning. The file must be directly executable on a Linux/POSIX system and must work regardless of its current working directory.

With no command, no usable command recovered from a log, and neither help nor version requested, exit with status 2 and report `error: command not specified and logfile is empty.` followed by a usage/help hint. The explicit exception is declining the existing-empty-log prompt, which exits as specified in Spec 15 without this error. Ordinary parse/validation errors go to stderr. Help and version go only to stdout and exit 0.

## Spec 2

`-V` and `--version` must print exactly `hwatch 0.3.19\n` to stdout, with empty stderr and status 0.

`-h` and `--help` are equivalent. If the parser reaches either flag before an error and before positional command collection begins, it exits 0, writes nothing to stderr, ends in one newline, and prints exactly the text below. Help does not retroactively override an earlier validation failure: `--interval bad --help` exits 2 with the invalid-float error. Once positional command collection has begun, a later `-h` or `--help` is command text rather than a help request. In particular, `executable --unknown-before-help --interval bad --help` treats the first token as the command and, in a non-TTY invocation, exits 0 with empty stdout and stderr rather than printing help.

```text
A modern alternative to the watch command, records the differences in execution results and can check this differences at after.

Usage: executable [OPTIONS] [command]...

Arguments:
  [command]...  

Options:
  -b, --batch                         output execution results to stdout
  -B, --beep                          beep if command has a change result
      --border                        Surround each pane with a border frame
      --with-scrollbar                When the border option is enabled, display scrollbar on the right side of watch pane.
      --mouse                         enable mouse wheel support. With this option, copying text with your terminal may be harder. Try holding the Shift key.
  -c, --color                         interpret ANSI color and style sequences
  -r, --reverse                       display text upside down.
  -C, --compress                      Compress data in memory. Note: If the output of the command is small, you may not get the desired effect.
  -t, --no-title                      hide the UI on start. Use `t` to toggle it.
      --enable-summary-char           collect character-level diff count in summary.
  -N, --line-number                   show line number
      --no-help-banner                hide the "Display help with h key" message
      --no-summary                    disable the calculation for summary that is running behind the scenes, and disable the summary function in the first place.
  -x, --exec                          Run the command directly, not through the shell. Much like the `-x` option of the watch command.
  -O, --diff-output-only              Display only the lines with differences during `line` diff and `word` diff.
  -A, --aftercommand <after_command>  Executes the specified command if the output changes. Information about changes is stored in json format in environment variable ${HWATCH_DATA}.
  -l, --logfile [<logfile>]           logging file. if a log file is already used, its contents will be read and executed.
  -s, --shell <shell_command>         shell to use at runtime. can also insert the command to the location specified by {COMMAND}. [default: "sh -c"]
  -n, --interval <interval>           seconds to wait between updates [default: 2]
      --precise                       Attempt to run as close to the interval as possible, regardless of how long the command takes to run
  -L, --limit <limit>                 Set the number of history records to keep. only work in watch mode. Set `0` for unlimited recording. (default: 5000) [default: 5000]
      --tab-size <tab_size>           Specifying tab display size [default: 4]
  -d, --differences [<differences>]   highlight changes between updates [possible values: none, watch, line, word]
  -o, --output [<output>]             Select command output. [default: output] [possible values: output, stdout, stderr]
  -K, --keymap <keymap>               Add keymap
  -h, --help                          Print help
  -V, --version                       Print version
```

## Spec 3

Recognize all options shown in the help text, both short and long forms. Boolean short options may be grouped, for example `-bc`, `-bcr`, and `-bcrC`. Value options accept a separate value and long options accept `--name=value`. `-K` and `-A` are repeatable; all other boolean flags reject duplicate occurrences with parse status 2 and wording containing `cannot be used multiple times`. For repeatable after-command values, only the first value is executed. Multiple keymaps all accumulate.

The defaults are: interactive mode, interval `2.0` seconds, shell `sh -c`, history limit 5000, tab size 4, combined output, no diff, wrapping on, history pane visible and focused, title/header visible, and the other boolean modes off. A bare `-d`/`--differences` defaults to `watch` when no following non-option token is available as its optional value. A bare `-o`/`--output` does not similarly recover the default: when it is immediately followed by `--`, startup exits 101 with empty stdout and a Rust panic on stderr containing ``called `Option::unwrap()` on a `None` value``. This applies to both `-o -- 'printf x'` and `--output -- 'printf x'`. A following non-option token is consumed and validated as the option value even when it is not a valid enum. Thus `-b -n 0.03 -d -o 'printf bare'` exits 2 with `error: invalid value 'printf bare' for '--output [<output>]'` rather than running `printf bare`. `-l`/`--logfile` may be supplied without a path and must not prevent execution; use `--` after a bare log option to prevent the command from being consumed as the optional path. A bare log option activates no logfile: `-l -- 'printf defaultlog'` and `--logfile -- 'printf defaultlog'` execute the command and emit `defaultlog` in batch mode, but create no file in the current directory.

Once positional command collection begins, every remaining token is command text, including tokens such as `-e` that resemble options. An option-looking value that occurs where the first command token is allowed is likewise command text rather than an unknown-option parser failure. Thus, in batch mode a command such as `--unknown` is repeatedly handed to the shell and its shell error is captured. When such a token is the only command in noninteractive/non-TTY invocation, terminal setup may finish silently with status 0; it must not emit an `unexpected argument` parse error. `--` explicitly ends option recognition.

## Spec 4

Validate option values before starting the watcher. Parser validation failures exit 2 and use clap-style stderr. Required-value errors contain `a value is required for '--shell`, `--aftercommand`, or `--keymap` as applicable. The interval is an ordinary floating-point number; malformed input such as `abc` produces:

```text
error: invalid value 'abc' for '--interval <interval>': invalid float literal

For more information, try '--help'.
```

The limit is an unsigned 32-bit integer (`0..=4294967295`) and tab size an unsigned 16-bit integer (`0..=65535`). Non-digits report `invalid digit found in string`; out-of-range values report, for example, `-1 is not in 0..=4294967295`. Valid diff values are `none`, `watch`, `line`, and `word`; valid output values are `output`, `stdout`, and `stderr`. Invalid enum errors name the option and print the possible values. `-O/--diff-output-only` without an explicit differences option exits 2, writes nothing to stdout, and writes exactly:

```text
error: the following required arguments were not provided:
  --differences [<differences>]

Usage: executable --differences [<differences>] --diff-output-only [command]...

For more information, try '--help'.
```

An interval below 0.001 seconds is clamped to 0.001. Zero is accepted. For compatibility, a negative floating interval can parse but the execution worker then reports a panic containing `cannot convert float seconds to Duration: value is negative`; the main watcher remains alive until externally stopped.

## Spec 5

Before parsing the real argument vector, read `HWATCH` from the environment. If nonempty, split it on ASCII whitespace and inject those tokens as default arguments before the real CLI tokens. This supports defaults such as `--batch -n 0.1` or `--no-title --color --no-help-banner`. Later CLI values win for value-bearing settings such as interval. Repeating a non-repeatable boolean once in `HWATCH` and once on the CLI is still a duplicate and exits 2. An empty or absent `HWATCH` has no effect.

The watched process inherits the executable's environment, current directory, and normal PATH lookup. This includes arbitrary user environment variables and `HOME`/`PATH` visibility.

## Spec 6

After successful setup, execute the watched command immediately, then continue indefinitely. The ordinary schedule waits the configured interval after an execution before starting the next execution. `--precise` instead targets fixed wall-clock interval boundaries, subtracting command runtime so that starts remain approximately one interval apart. Fractional intervals are supported; timing should be close enough that a 0.5-second precise interval remains roughly within 0.45–0.60 seconds under light load.

A failed child command, missing program, empty output, or nonzero exit does not stop the watch loop. The loop remains responsive to SIGINT/SIGTERM and interactive quit. It must not deadlock on slow children, rapid changes, output with thousands of lines, a single very long line, or many short lines.

## Spec 7

By default, form the watched command by joining positional tokens with single spaces and run that resulting command string through the configured shell. The default is behaviorally equivalent to `sh -c <joined-command>`, so pipes, redirects, quotes, globbing, arithmetic expansion, variable expansion, command substitution, and shell syntax work. Captured command output does not go directly to the executable's stderr.

`-s/--shell` supplies a shell command string. Split it into its executable/arguments. If it contains the literal `{COMMAND}`, substitute the joined watched command at that position; otherwise append the watched command as the shell's final command argument. For example, `-s 'bash -c' 'echo $BASH_VERSION'` runs under bash, while `-s 'bash -c "echo before; {COMMAND}; echo after"' 'echo middle'` produces `before`, `middle`, `after` in that order.

With `-x/--exec`, do not invoke a shell to launch the child. Before launching it, however, join the positional tokens with single spaces and parse that joined string with shell-word quoting/tokenization to obtain the executable and argv. Original CLI argument boundaries are therefore not preserved when a token itself contains an unquoted space. No shell expansion is performed: operators, `$((...))`, `$VAR`, `*`, and metacharacters remain literal after tokenization. For example,

```text
-b -x /usr/bin/printf '%s|%s|%s|%s' '$HOME' '*' '$((2+3))' 'a b'
```

renders `$HOME|*|$((2+3))|ab|||`: the final `a b` token becomes two child arguments and `printf` reuses its format for the extra `b`. Likewise, in `-x python3 -c "import os;os.write(1,b'good\xfftail')"`, `-c` remains a child argument but the space-containing source token is split, so Python receives only `import` as its `-c` source rather than the original token. A missing direct executable is rendered as `No such file or directory (os error 2)` and the watch loop continues.

## Spec 8

For every run, capture stdout and stderr separately using fallible UTF-8 string reads. Valid UTF-8, including Unicode, and ASCII control bytes are accepted. An invalid UTF-8 byte is not replaced or otherwise tolerated: reading a captured stream that contains byte `0xff` exits the watcher with status 101 and reports a Rust panic containing ``called `Result::unwrap()` on an `Err` value: Error { kind: InvalidData, message: "stream did not contain valid UTF-8" }``. Define three selectable views for successfully decoded results:

- `output`: stdout and stderr chunks concatenated in capture-arrival order, preserving each individual stream's internal byte order;
- `stdout`: stdout only;
- `stderr`: stderr only.

The selected view controls the watch pane and batch payload. It also controls which changes make a history item visible when the mode is changed interactively. Capture arrival is scheduling-dependent: the same command can produce `OUTERR` on one execution and `ERROUT` on another even when it writes `OUT` only to stdout and `ERR` only to stderr. This change in the stored combined `output` is a history change and can therefore cause repeated records even while a `stdout`-only or `stderr`-only batch payload stays identical. A successful child has `status: true`; any nonzero exit or launch failure has `status: false`. For successfully decoded output, preserve empty lines, leading/trailing spaces, carriage returns, tabs in batch output, Unicode, emoji, combining/accents, wide characters, and ASCII controls. A child error is part of the selected/captured payload, not a reason for the watcher itself to exit.

## Spec 9

`-b/--batch` disables terminal UI and writes changed records to stdout. Each emitted record has exactly this framing, where the final `\n` shown after the payload is one newline byte appended unconditionally by the watcher:

```text
ESC[38;5;240m=====[YYYY-MM-DD HH:MM:SS.mmm]=========================ESC[0m\n
<rendered selected output>\n
```

The timestamp has exactly millisecond precision. The gray ANSI codes on the separator are always emitted, even without `--color`. Do not first normalize the rendered payload to end in a newline. Instead, preserve it exactly and then append one newline: an unterminated `hello` becomes `hello\n`, an already terminated `a\n` becomes `a\n\n`, and an empty payload becomes one `\n`. A following record header begins immediately after that appended newline. Even a first empty result emits its header and that one payload newline.

The initial execution is compared against an empty sentinel and is normally emitted. Later executions are emitted only when the full result relevant to history changes; identical static results do not repeatedly print, although the command continues running. Changing output produces one framed block per change. `--limit` limits in-memory history, not the number of executions or the number of JSON log lines, so batch mode never exits merely because the limit is reached.

## Spec 10

Maintain chronological execution-result history. A result contains timestamp, joined command, success status, combined output, stdout, and stderr. Store only results that differ from the prior result. The default memory limit is 5000 retained records; a positive limit discards oldest in-memory records as new ones arrive, while 0 means unlimited. `-C/--compress` changes only the internal representation of retained text and must be completely transparent in batch output, TUI output, logs, diffs, hooks, and all option combinations.

Change detection must account for content and failure/success changes. It must handle transitions from empty to content, content to empty, insertions only, deletions only, identical runs, whitespace-only changes, and changes in either stdout or stderr.

## Spec 11

Diff rendering compares the selected result with its chronological predecessor:

- `none` renders the current output unchanged.
- `watch` renders the current output and wraps each changed character cell in reverse-video SGR (`ESC[7m`); the first result therefore marks all its characters. Compatibility rendering emits `ESC[7m`, the changed character, and `ESC[7m` for each individual changed character, then an `ESC[0m` reset at the end of a changed run. ANSI escape sequences participate in this character-wise processing rather than being copied as indivisible units. For example, the first-result command `printf '\033[31mR\033[0m'` renders exactly `ESC[ESC[3ESC[31ESC[31mESC[7mRESC[7mESC[ESC[0ESC[0mESC[0m` before the batch newline. If old and new lines have unequal character counts, compare through the longer count and use U+0020 ordinary ASCII space as the visual padding cell; changing `abc` to `a` renders the two missing cells as two individually reverse-video ASCII spaces.
- `line` performs an ordered line diff. Unchanged lines begin with three spaces. Deleted old lines are prefixed `ESC[31m-  ESC[0m` and colored red; inserted new lines are prefixed `ESC[32m+  ESC[0m` and colored green. On the first result every line is an insertion.
- `word` uses the same line-level add/delete structure, then emphasizes only changed word/character spans inside paired removed/added lines with white-on-red (`ESC[41;37m`) and white-on-green (`ESC[42;37m`) backgrounds. Unchanged parts retain the surrounding red/green line color.

Use resets so formatting cannot bleed into following lines or records. Diffs must remain correct for blank lines, Unicode, tabs, very long common prefixes, wholly different results, ANSI-bearing input, and reverse display. `-O/--diff-output-only`, valid only with line or word mode, removes all unchanged lines after the first and leaves changed deletion/addition pairs. Without `-O`, unchanged context stays visible.

## Spec 12

`-N/--line-number` prefixes every logical rendered line, starting at 1. In batch mode the normal/unchanged prefix is `<padding>ESC[38;5;240m<number>ESC[0mESC[38;5;240m | ESC[0m`: only the decimal digits are inside the first gray SGR span, and any spaces needed for right alignment are emitted before that `ESC`. Thus a ten-line view prefixes line 1 with ` ESC[38;5;240m1ESC[0mESC[38;5;240m | ESC[0m` and line 10 with `ESC[38;5;240m10ESC[0mESC[38;5;240m | ESC[0m`. With `--color` and a `line` diff, the number and ` | ` prefixes are mandatory truecolor prefixes: inserted lines use `ESC[38;2;56;119;120m<number>ESC[0mESC[38;2;56;119;120m | ESC[0m`, deleted lines use `ESC[38;2;118;0;0m<number>ESC[0mESC[38;2;118;0;0m | ESC[0m`, and unchanged lines retain the normal gray prefix. Width is right-aligned to the decimal width of the largest line number in the current view. Treat a trailing newline as creating a final empty logical line, so it can receive a number.

`-r/--reverse` reverses logical output-line order, not characters and not UI/header text. The trailing empty logical line from newline-terminated output moves to the beginning. Line numbering remains associated with the displayed/diff lines. In the TUI, `--tab-size N` expands tabs to the next N-column tab stop; at the beginning of a line a tab inserts N spaces, and after one visible character tab size 4 inserts three. A tab size of 0 removes tab characters without inserting spaces. Position calculations must account for line-number columns, ANSI sequences as zero-width, Unicode display width, and tabs at viewport boundaries. Batch mode preserves tab bytes while still accepting the option.

## Spec 13

Batch mode preserves command ANSI/control sequences byte-for-byte in nondiff payloads whether or not `-c` is present. This includes SGR reset, bold/dim and reset 22, italic/reset 23, single or double underline/reset 24, slow/rapid blink/reset 25, inverse/reset 27, invisible/reset 28, strike/reset 29, default foreground/background 39/49, 8/16-color codes, 256-color forms `38;5;n`/`48;5;n`, truecolor forms `38;2;r;g;b`/`48;2;r;g;b`, font codes, repeated resets, malformed/unknown SGR, cursor/clear sequences, and carriage returns.

That byte preservation begins after the child has produced its captured output; it does not undo `--exec` argument reconstruction or a child's own format-string processing. In particular, when the positional argument passed to `-x /usr/bin/printf` is the literal Python-style text `b'\x1b[0m...\x07END'`, shell-word tokenization removes the quote characters but retains the leading `b`, and `printf` interprets the backslash escapes. The nondiff batch payload therefore begins `bESC[0m` and ends `BELEND\n`, both with and without `--color`.

`--color` enables interpretation of those sequences into terminal styles in the TUI. It must not remove visible text. Toggling color off strips their styling effect but leaves text; toggling back on restores interpretation. Diff computation includes SGR bytes when deciding whether results differ. A style-only transition from `ESC[31mXESC[0m` to `ESC[32mXESC[0m` is rendered by `line` mode as a deleted red `X` line followed by an inserted green `X` line, not as one unchanged line. Line-diff output applies the watcher's own red/green styling around that content. Rendering and searching must use terminal column width for CJK/wide characters and emoji rather than byte length.

In a non-color TUI watch-diff view, input escape sequences are represented as literal visible sequence text rather than applied as terminal color. Consecutive empty logical lines must remain distinct in the TUI; an implementation may place U+200B in an otherwise empty rendered line to keep the terminal widget from collapsing it.

## Spec 14

`-B/--beep` emits ASCII BEL (`0x07`) followed by a newline whenever a new changed history record is accepted. The first non-sentinel result counts as a change. Do not beep repeatedly for identical results. The bell follows that record's payload in batch output and composes with diff, color, and compression.

`-A/--aftercommand COMMAND` runs the first supplied hook through the shell whenever the same change condition occurs. Hook stdout/stderr are inherited so visible hook output can appear in the executable's captured output stream. Set `HWATCH_DATA` in the hook environment to a single valid JSON object with exactly the top-level keys `before_result` and `after_result`. Each value is a result object containing at least `timestamp`, `command`, `status`, `output`, `stdout`, and `stderr`; the before side is the previous result/sentinel and after side the newly accepted result. Hook failure does not stop monitoring.

## Spec 15

`-l/--logfile [PATH]` persists history as UTF-8 JSON Lines: one compact JSON object per line, with keys `timestamp`, `command`, `status`, `output`, `stdout`, and `stderr`. A newly created file begins with the sentinel:

```json
{"timestamp":"","command":"","status":true,"output":"","stdout":"","stderr":""}
```

Append each changed execution result; do not truncate prior valid entries and do not prune log lines when the in-memory limit is reached. Actual timestamps use `YYYY-MM-DD HH:MM:SS.mmm` or a more precise compatible suffix. Preserve terminating newlines inside JSON string values. The command field contains the joined command string. Logs must remain valid with Unicode and control output that is valid UTF-8, failed commands, compression, summaries, diffs, and output modes. If a newly created log is used by `-bC --no-summary --enable-summary-char` and the child writes valid UTF-8 followed by byte `0xff`, the logfile is initialized with the sentinel but no result line is appended. Stdout contains the batch separator through its newline but no payload, stderr reports the invalid-UTF-8 panic described in Spec 8, and the process exits with status 101.

If the parent directory does not exist, exit 2 with empty stdout and exactly this stderr (substituting the parent path):

```text
error: directory "<parent>" is not exists.

Usage: hwatch [OPTIONS] [command]...

For more information, try '--help'.
```

Existing valid logs are loaded as initial history. If no command was supplied, inspect only the final loaded result and use its `command` field; do not scan backward for an earlier nonempty command. If that final command is empty, the batch watcher remains alive without executing the earlier command, produces no stdout or stderr, and appends no result. For an existing empty file, write exactly `Log to the same file? (Y/n) ` to stdout without a newline and report `file "<path>" is exists and empty.\n` on stderr. If the user answers `n`, exit 1 immediately; do not additionally emit the missing-command error. `--no-summary` disables summary calculation; `--enable-summary-char` additionally calculates character insertion/deletion/equality counts without changing the six required log fields or normal output.

## Spec 16

Without `--batch`, run a full-screen terminal UI that refreshes on each execution and resize. The history pane remains 25 columns wide while the watch pane receives the remaining width. At 80 columns, watch content occupies columns 0–53, column 54 is the blank or drawn divider, and history occupies columns 55–79. After resizing to 100 columns the divider is at zero-based column 74, and at 120 columns it is at column 94.

The default unbordered 80-column screen begins conceptually as:

```text
Every     5.000:echo Hello World Display help with h key! YYYY-MM-DD HH:MM:SS.mmm
                     [Number] [Color] [Reverse] [Output] [History] [None      ]
Hello World                                            >>latest
                                                         YYYY-MM-DD HH:MM:SS.mmm
```

The first header line contains `Every`, the interval formatted to three decimals in a fixed field, `:`, the joined command, the help banner, and current timestamp, clipped to terminal width. The second line is the current search input (if any), followed/right-aligned by `[Number] [Color] [Reverse]`, the selected output label (`[Output]`, `[Stdout]`, or `[Stderr]`), focused pane (`[History]` or padded `[Watch  ]`), and padded diff mode (`[None      ]`, `[Watch     ]`, `[Line      ]`, `[Word      ]`). Mode words remain present as labels; terminal styling indicates boolean on/off states.

The output pane begins below the two header rows. The history pane starts with the pseudo-item `latest`, followed by newest-to-oldest timestamps. Prefix the selected history row with `>>` and unselected rows with two spaces. Selecting `latest` continuously displays the current result; selecting a timestamp displays that saved result and its appropriate predecessor diff.

## Spec 17

`-t/--no-title` starts with both header rows hidden and expands content upward; `t` toggles them later. `--no-help-banner` removes only `Display help with h key!`. `--border` draws a horizontal separator below the header and a vertical separator between watch/history using Unicode `─`, `│`, and `┬`; `b` toggles this. `--with-scrollbar` draws a proportional right-side watch scrollbar using `█` when borders are enabled and content overflows; it is independently toggleable and harmless without overflow. `--mouse` enables corresponding mouse scrolling/click handling.

Wrapping is on by default: long logical lines continue on subsequent viewport rows. When off they are clipped at the right edge and can be horizontally scrolled. Line numbers, ANSI styling, wide characters, borders, and scrollbar columns all reduce the usable width correctly. All visual flags can be combined and must persist across subsequent command executions.

## Spec 18

Initial keyboard focus is the history pane. `Tab` toggles focus; BackTab is ignored and leaves the current focus unchanged. Left focuses watch and Right focuses history idempotently. The focus label in the second header row updates immediately.

In the watch pane, Up/Down scroll one display row, PageUp/PageDown scroll one viewport page, Home jumps to the top, and End jumps to the bottom. Alt+Left/Alt+Right scroll horizontally one step; Shift+Alt+Left/Right jump to the horizontal beginning/end. Clamp every movement safely. With an 80x24, two-header-row, unbordered view, one PageDown from the first line starts around logical line 22, and End on 100 newline-terminated lines exposes the final viewport including its trailing empty line.

In the history pane, Down moves from `latest` toward older records and Up moves toward newer/latest; PageUp/PageDown move by a visible page, Home returns to `latest`, and End selects the oldest retained record. The selection marker and watch content update together. Scrolling the watch pane does not lose history selection, pausing does not lose focus, and all boundary operations are idempotent.

## Spec 19

Default normal-mode keys include:

- `h`: toggle the help modal; `q`: open the exit confirmation; uppercase `Q` may force an immediate quit.
- `c`, `n`, `r`, `b`, `w`, `m`: toggle color interpretation, line numbers, reverse-line order, borders, wrapping, and mouse support.
- `d`: cycle None -> Watch -> Line -> Word -> None; `0`, `1`, `2`, `3` select those modes directly.
- `o`: cycle Output -> Stdout -> Stderr -> Output; F1, F2, F3 select Stdout, Stderr, Output directly.
- `O`: toggle diff-only display; `t`: toggle header; Backspace: toggle history pane; `S`: toggle history summaries.
- `p`: pause/resume execution. Space is ignored in normal mode, including while paused. While paused the first header contains `Every` and `Paused`, no new child runs occur, and navigation remains usable.
- `+` and `-`: increase/decrease interval by 0.5 seconds, never below a positive usable value.
- Ctrl+N and Ctrl+P: move to the next/previous active search match, wrapping at the ends.

Each toggle updates its header label/rendering immediately, toggles back cleanly, composes with all other modes, and persists across refreshes.

## Spec 20

`/` enters case-sensitive literal search/filter input and displays `/` plus typed text at the start of header row two. `*` similarly enters regex mode and displays `*PATTERN`. Support normal printable input, punctuation/special characters, Backspace editing, and Enter to apply. While search input is active, a bare Escape is ignored and leaves both the input mode and typed text intact; Ctrl-C clears the typed text back to the bare `/` or `*` prompt but leaves input mode active. An empty submitted filter behaves as no filter. Invalid regular expressions are rejected without crashing or replacing the last valid state.

An applied search highlights occurrences in the watch pane without removing nonmatching watch lines; literal matching is case-sensitive (`fox` does not match `Fox`). Ctrl+N/Ctrl+P select and scroll to successive/previous matches with wraparound. The same filter restricts timestamped history records whose selected output does not match, but never removes the `latest` pseudo-item: applying `/definitely-absent` to a first result containing only `searchable` leaves `>>latest` visible. Escape outside input clears an active filter and restores all retained history. Filters persist as new executions arrive and work with ANSI text, line numbers, wrapping, all diff modes, and special/Unicode patterns.

## Spec 21

The help modal is centered over, but does not erase, the underlying UI. It uses a Unicode single-line box titled `[help]` and lists current key bindings in pairs such as `- [up] key :` then an indented `Move up`. Its initial page begins with the exact lowercase labels `[up]`, `[down]`, `[alt-right]`, `[shift-alt-right]`, `[alt-left]`, `[shift-alt-left]`, and `[pageup]`. Later pages include PageDown, Home, End, Tab (`Toggle forcus window`), Left (`Forcus watch pane`), Right (`Forcus history pane`), q (`Quit hwatch`), and the remaining toggles/search/mouse bindings. Up/Down scroll one help line, PageUp/PageDown one modal page, Home/End jump to boundaries, and positions clamp. `h` or Ctrl-C dismisses it and restores the prior screen; a bare Escape is ignored and leaves the modal open.

Pressing `q` in normal mode opens a centered double-line box titled `[exit]` containing exactly the visible phrases `Exit hwatch?`, `Press 'Y' or 'Q'  : Quit.`, and `Press 'N' or 'Esc': Stay.`. Despite those uppercase letters in the visible prompt, only lowercase `y` or lowercase `q` confirms and exits with status 0; lowercase `n` or Escape cancels and returns unchanged. Uppercase `Y`, `Q`, and `N` are ignored and leave the process and exit dialog open. Pressing `h` from this dialog transitions to the help modal.

## Spec 22

`-K/--keymap` takes exactly one `key=action` mapping per occurrence and adds it to, rather than replacing, defaults. Exactly one equals sign is required and neither side may be empty. On any invalid key, modifier, mouse event, action, or malformed mapping, print exactly `Failed to parse keymap.\n` to stderr and exit 1.

Accept individual printable characters including uppercase; named `space`, `enter`, `esc`, `tab`, `backtab`, `plus`, `minus`/`hyphen`, `equal`, `ins`, `del`, navigation keys, and F1 through F12 (but not F13). Accept `ctrl`, `alt`, `shift`, `super`, `hyper`, and `meta` modifiers, including multiple hyphen-separated modifiers in any tested order. Accept mouse names including `mouse-scroll_up`, `mouse-scroll_down`, `mouse-scroll_left`, `mouse-scroll_right`, `mouse-button_down_left`, `mouse-button_down_right`, `mouse-button_up_left`, and `mouse-button_up_right`.

At minimum accept and dispatch these action names: `none`, `help`, `quit`, `force_cancel`, `toggle_pause`, `page_up`, `toggle_diff_mode`, `set_diff_mode_line`, `set_output_mode_stderr`, `watch_pane_up`, `watch_pane_down`, `watch_pane_page_up`, `history_pane_up`, `scroll_horizontal_home`, `scroll_horizontal_end`, `forcus_watch_pane`, `toggle_view_header_pane`, `toggle_border`, and `toggle_scroll_bar`. Other actions shown in the built-in help should follow the same underscore naming scheme. For example, `-K x=quit` makes `x` open the quit dialog, `-K z=help` opens help, and the original `q` binding still works.

## Spec 23

All modes must remain robust when combined: batch/color/line numbers/reverse/diffs/output filtering/hooks/beep/logging/compression/precise timing, and the corresponding interactive toggles, must not disable one another except where explicitly stated. Handle commands with no trailing newline, empty or whitespace-only output, CR and BEL controls, quotes and spaces, JSON-looking text, shell pipelines/redirections, nonzero exits, stderr-only output, mixed streams, Unicode command arguments, malformed byte sequences, thousands of lines, and very long lines without crashing or truncating the underlying captured result.

When stdout is not a terminal and interactive mode cannot initialize, fail gracefully without dumping terminal-control diagnostics; the compatibility behavior for an option-looking positional command invoked alone is status 0 with empty stdout/stderr. In batch mode, stdout is flushed after every framed record so partial output is observable before a timeout or termination.
