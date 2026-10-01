## Spec 1

The required artifact is a POSIX executable file named exactly `executable`. It implements a single-mode file-event runner: it reads paths from standard input, runs an arbitrary utility, and (unless told to exit after one run) runs that utility again in response to watched-file events. It is not a subcommand-oriented program. The first non-option command-line token is always the utility name, including words such as `add`, `remove`, `list`, `init`, `status`, `commit`, and `help`.

The command-line grammar is:

```text
executable [-acdnprsxz] utility [argument [/_] ...] < filenames
```

All options in the displayed `[-acdnprsxz]` grammar are one-letter options. Separate occurrences and combined forms such as `-n -z`, `-nz`, and `-zn` are equivalent. The help token described below is a special case and is not one of these combinable options. Option processing stops at the first utility token, so option-looking tokens after the utility are utility arguments. A standalone `--` explicitly ends option processing; for example, after `-n -z --`, a following `-n` is an attempted utility name. There are no GNU long options.

## Spec 2

Invoking the executable with `-h` prints help and exits with status 1. The output is deliberately split across the two standard streams. Standard output is exactly:

```text
summary:
    -a  Do not consolidate events
    -c  Clear screen before execution
    -d  Track files added or removed from directories
    -n  Non-interactive mode
    -p  Wait for first event
    -r  Run as a background process, use signal to restart
    -s  Evaluate using a shell
    -x  Format exit status
    -z  Exit after the utility completes
docs:
    man entr
```

Standard error is exactly:

```text
release: 5.7
usage: entr [-acdnprsxz] utility [argument [/_] ...] < filenames
```

Both streams end in a newline. The release and usage lines are the first two nonblank stderr lines. This help shortcut applies only when the first argument after the program name is exactly the standalone token `-h`; once recognized, later arguments are ignored, so `-h -n` has the same help behavior. It does not apply when `h` is clustered or occurs after another option: `-nh`, `-hn`, and `-n -h` all reject `h` as an invalid option, exit 1, leave stdout empty, and emit the invalid-option diagnostic from Spec 3. The help must not describe subcommands or contain a `commands:` section.

## Spec 3

With no utility (whether there are no arguments at all or there are only options such as `-n`), exit 1, write nothing to stdout, and write this three-line diagnostic to stderr:

```text
release: 5.7
usage: entr [-acdnprsxz] utility [argument [/_] ...] < filenames
hint: use -h to display option summary
```

An unsupported short option exits 1. Its first diagnostic field is the program's actual `argv[0]`, preserving any absolute, relative, or custom spelling used to invoke it. Thus invoking the required artifact as `/workspace/executable -q` makes stderr start with `/workspace/executable: invalid option -- 'q'`, followed by the same release, usage, and hint lines. Long options are unsupported: `--help` and other `--word` forms are parsed as an invalid option whose option character is `-`; `/workspace/executable --help` therefore starts stderr with `/workspace/executable: invalid option -- '-'`, followed by the release, usage, and hint. These diagnostics go to stderr. In contrast, a token such as `--help` after the utility is merely a utility argument because option parsing has already stopped.

## Spec 4

The path list is read from standard input as newline-delimited byte strings. The final path is accepted even if EOF occurs without a terminating newline. A line containing no bytes before its newline is ignored, including leading, interspersed, and trailing empty lines. Other whitespace is not trimmed: a line containing spaces or tabs represents a literal whitespace-containing filename and normally produces a stat warning. Spaces, tabs, shell metacharacters, Unicode, and other valid non-newline filename bytes must otherwise be preserved. An embedded NUL, a path longer than the platform permits, or a regular-file path with an appended slash is invalid and must be handled as a failed path rather than causing a crash.

Accept existing regular files regardless of size, contents, extension, or read permission. Empty, binary, large, dot-prefixed, relative, absolute, and long-but-valid paths are supported. Existing directories are also valid input paths, even without `-d`, and files and directories may be mixed. Symlinks, including chains and broken symlinks, are valid input objects. FIFOs and other non-regular, non-directory, non-symlink objects do not count as valid watch inputs.

Duplicate spellings of the same path must not create duplicate watches. Multiple paths identifying the same underlying object, such as hard links, must not cause multiple executions for one underlying event. Lists of at least 200 paths must work.

## Spec 5

For each input path that cannot be inspected, write the following line to stderr and continue processing later input lines:

```text
executable: unable to stat '<path>'
```

Thus every invalid path in a mixed list is reported, while any valid paths remain usable. If at least one valid path remains, the executable continues and may run the utility; warnings do not change a successful one-shot utility status. If no valid watch object remains after input is processed, exit 1 and append exactly:

```text
executable: No regular files to watch
```

No utility is run in that case. Empty stdin and stdin containing only empty lines produce only the `No regular files to watch` line. A nonexistent utility is a different error: after valid input has been accepted, an `execvp`-style failure exits 1 and writes `executable: exec <utility>: No such file or directory` followed by a newline.

## Spec 6

In direct mode (without `-s`), launch the utility using the supplied argument boundaries, searching `PATH` when its name contains no slash and directly supporting absolute or relative utility paths. Preserve the executable's current working directory. Pass through the utility's stdout and stderr to the corresponding streams byte-for-byte, without merging them, adding text, imposing line buffering, or truncating binary or large output. Utilities with no arguments, hundreds of arguments, no output, output without a final newline, at least 100 KiB of output, and delayed completion must all work.

The child inherits the caller's environment, subject to the explicit environment defaults in later sections. The already-consumed filename-list stream must not be supplied to background/restart children as interactive input; such a child must observe EOF (normally via `/dev/null`). Independent concurrent instances of `executable` must not share watch or child state.

## Spec 7

The special argument token `/_` supplies the leading-edge path. Only the first command argument that is exactly `/_` is substituted; a second `/_` remains the literal two-character token, and `_` without the slash is never special. Substitution preserves one argv element even when the pathname contains spaces or metacharacters.

For the initial execution, the leading edge is the first valid input path. For an event-triggered execution, it is the first watched path whose event caused that execution. Use the path spelling supplied on stdin: relative paths remain relative, redundant slashes need not be rewritten, and a symlink input produces the symlink path rather than its target path. The substituted value may occupy any utility-argument position, including a shell program's argv-zero position, and must be refreshed for later event-triggered runs.

## Spec 8

Option `-s` selects shell mode. In this mode there must be exactly one non-option argument: the complete shell command string. More than one argument exits 1 and writes exactly:

```text
executable: -s requires commands to be formatted as a single argument
```

Use the interpreter named by `SHELL`; if `SHELL` is absent, use `/bin/sh`. Invoke it with shell `-c` semantics so quoting, variable and command substitution, pipelines, redirection, semicolons, conditionals, loops, subshells, `&&`, and `||` behave normally. Set the command's shell `$0` to the current leading-edge path. Consequently `cat "$0"` reads the triggering file. The literal text `/_` inside the shell command string is not rewritten; shell mode communicates the path through `$0`. Preserve the shell command's stdout, stderr, and final exit status in the same way as direct execution.

## Spec 9

Unless `-p` is present, run the utility once immediately after options, environment, input paths, and terminal requirements have been validated. After that child completes, remain in the watch loop unless an exit condition applies. A normally exiting or crashing utility does not by itself stop the ordinary watch loop, and later events can launch it again.

Option `-p` postpones this initial execution. With no file or keyboard event, the process remains alive and emits no utility output. The first qualifying event launches the first utility instance. This composes with `-z` and `-r`: `-p -z` waits and then performs one run, while `-p -r` waits and then starts the restart-managed child.

Option `-z` exits as soon as the first launched utility completes, including when combined with `-r`. Return the child's exact normal exit code in the range 0 through 255. If the child was killed by signal number `N`, return `128 + N`; examples include 130 for SIGINT, 131 for SIGQUIT, 137 for SIGKILL, 139 for SIGSEGV, and 143 for SIGTERM. Failure to execute the utility remains the executable's own status 1. Without `-z`, child failure does not become the eventual monitor exit status.

## Spec 10

Monitor every accepted regular file for content writes and truncation, mode/attribute changes, deletion/recreation, and replacement by a new inode at the same pathname. A completed write or chmod triggers an execution. Atomic-save patterns such as write-temporary-then-rename must be detected. If a watched pathname temporarily disappears and is recreated, retain enough pathname state to reopen it and consolidate the delete/recreate sequence into one run. A rename only away from the watched pathname is different: with `-n -p -z`, renaming the file away causes no utility output, does not launch the postponed utility, and terminates the monitor with status 1. Stderr is exactly `executable: cannot open '<supplied-path>': No such file or directory` followed by a newline. The executable must continue watching after ordinary utility completion.

By default, consolidate a burst of related notifications into one execution, including multiple notifications for a single write, rapid writes to one file, simultaneous changes to several watched files, hard-linked watch entries, and bulk rewrites. Wait for each non-restart utility to finish before starting another. Notifications arriving while that utility is running are normally consumed or consolidated rather than queued as multiple later runs.

Option `-a` disables that consolidation: distinct events, including an event received while a utility is running, must cause subsequent executions, while utility instances remain serialized. Spaced individual writes therefore cause individual runs. `-a` has no additional effect together with `-r`.

## Spec 11

By default on Linux, watch a symlink as a directory entry rather than following its target. Modifying only the target must not trigger a run; unlinking and recreating the symlink itself must trigger one. This behavior also permits a broken symlink as an initial valid watch input.

If the `ENTR_FOLLOW_SYMLINK` environment variable is present, resolve symlinks and make their targets the watched objects. Regardless of this setting, `/_` and shell `$0` retain the original input spelling. Symlink handling must not crash when a watched directory contains a symlink or when a multi-link chain resolves to a regular file.

## Spec 12

Option `-d` additionally tracks the parent directories of supplied entries so changes to directory membership can be recognized. Directories themselves may also be supplied. Record each tracked directory's immediate entries; tracking is not recursive. Creating a file several levels below a tracked directory does not count as a change to that directory's own entry set. Files, subdirectories, and symlinks all count as entries.

With one `-d`, ignore entry names beginning with `.` when comparing directory membership. With `-dd` (equivalently two `-d` occurrences), include those hidden entries. Explicitly listed dotfiles remain ordinary valid watches regardless of this counting rule. Empty directories and directories containing many or specially named entries are supported.

When the relevant immediate entry set gains or loses a name in ordinary mode, the filesystem event that recognizes that change launches the utility once, waits for it to finish, and only then terminates monitoring with exit status 2 and a stderr diagnostic containing `directory altered`. Thus an initial invocation followed by such an event produces at least one event-driven invocation before the status-2 exit; this applies when additions include files, subdirectories, or changes in more than one tracked directory. This permits a surrounding caller to regenerate the filename list and restart the executable. Content or attribute changes to explicitly watched regular files remain normal execution events when the tracked entry set has not changed. If a watched directory itself disappears and cannot be reopened, exit 1 with a diagnostic containing `unable to open directory`.

The `-r -d` combination has a different ordering when a directory change is pending. Adding a sibling does not immediately restart the persistent utility. If a later event occurs on the listed file, terminate the old managed group, recognize the changed directory membership, emit the `directory altered` diagnostic, and exit 2 without launching a replacement child. For example, with a utility that appends one byte on each start, the sequence initial start, add sibling, then write the listed file leaves the log at one byte and exits 2.

## Spec 13

Option `-c` writes an ANSI screen-clear prefix to stdout immediately before initial and filesystem-triggered utility invocations. One occurrence writes these seven bytes, in this order:

```text
ESC [ 2 J ESC [ H
```

That is `\x1b[2J\x1b[H`. Two occurrences (`-cc`, `-c -c`) additionally erase scrollback and write `\x1b[2J\x1b[3J\x1b[H`. The prefix appears before any utility output and has no newline of its own. It composes with `-a`, `-d`, `-n`, `-s`, and `-z`.

## Spec 14

Option `-n` is non-interactive mode. It neither opens nor changes a terminal and is suitable when both stdin and output are pipes. A child such as `tty` must report that its stdin is not a TTY. Without `-n`, the executable must open a controlling terminal independently of the filename-list stdin and place it in a mode that can receive single keystrokes without Enter.

If interactive mode is requested but no controlling TTY is available, exit 1 and write exactly this newline-terminated stderr line:

```text
executable: unable to get terminal attributes, use '-n' to run non-interactively
```

In interactive mode, a space byte manually triggers the utility. Repeated spaces after preceding runs complete cause repeated runs; `-p` only suppresses the automatic initial run and does not disable space. With `-r`, space restarts the managed child. A lowercase `q` requests clean termination as though SIGINT were received. Uppercase `Q`, Enter, digits, letters other than lowercase `q`, and other keys do nothing. Keyboard EOF does not terminate an otherwise active watch. Keystrokes/events received during a non-restart child run must not create an unbounded queue.

## Spec 15

Option `-r` manages the utility as a persistent child. Launch it immediately unless `-p` is set. Put each launched child and its descendants in a distinct process group. On a qualifying file event or interactive space, send the configured restart signal to the entire old group, wait until it exits so resources such as sockets are released, reap it without zombies, and only then launch the replacement. A shell script must be able to trap the signal and perform cleanup. If the persistent utility exits by itself, do not relaunch it continuously; wait for a new file or keyboard event.

The default restart signal is SIGTERM. On SIGINT or SIGHUP delivered to the monitor, terminate and reap any managed process group promptly; the signal sent to that group is the configured restart signal, not necessarily the signal received by the monitor. For example, on monitor SIGINT, `ENTR_RESTART_SIGNAL=INT` sends SIGINT to the group, while `ENTR_RESTART_SIGNAL=HUP` sends SIGHUP and does not send SIGTERM. SIGINT and SIGHUP result in a clean monitor status 0. On SIGTERM, perform the same cleanup, restore the default disposition, and terminate by SIGTERM (reported as 143 by a shell, or as signal 15 by a direct process API). In normal non-`-z` operation, SIGINT while postponed or while watching exits 0. No descendant from an old generation may remain running after a restart or monitor shutdown.

Option `-r` is mutually exclusive with any occurrence of `-x`. Reject the combination in either option order with status 1 and exactly:

```text
executable: -r and -x may not be combined
```

## Spec 16

Validate `ENTR_RESTART_SIGNAL` at startup even if `-r` is not present. If the variable is absent, use the default SIGTERM. Before validation, strip one leading uppercase `SIG`; the remainder is also the value shown in any rejection diagnostic. Thus `HUP` and `SIGHUP` are equivalent, rejected `TERM` and `SIGTERM` both print `TERM`, rejected `SIGKILL` prints `KILL`, and lowercase `sigterm` remains unchanged. This tested build accepts the resulting case-sensitive names `HUP`, `INT`, and `QUIT`; these select signals 1, 2, and 3 respectively. In particular, lowercase names, an empty value, numeric `0`, `KILL`, arbitrary names, and `USR1` are rejected. This subset is an observable build quirk even though the error text advertises more names.

On rejection, exit 1 before running the utility, leave stdout empty, and write:

```text
executable: unrecognized signal: <value-after-leading-SIG-is-stripped> <> (HUP, INT, QUIT, TERM, USR1, USR2)
```

If `PAGER` is absent, add `PAGER=/bin/cat` to the environment inherited by utilities. Preserve any existing `PAGER` value unchanged. Preserve all unrelated environment variables.

## Spec 17

If `EV_TRACE` is present, write tracing diagnostics to stderr without disturbing utility stdout or status. At startup include a line of the form `open_max: N`, where `N` is decimal. For a received filesystem event, include a line containing an event index/count, `fflags: 0x` followed by lowercase hexadecimal flags, an object-type marker, a decimal value, and the watched path. In particular, the trace for a changed file must contain both `fflags: 0x` and that file's supplied path. Normal operation and one-shot exit status are unchanged by tracing.

## Spec 18

Option `-x` starts an AWK status filter. In one-shot `-z` operation, the child completion is reported to it. The status record supplied to AWK is one of:

```text
exit <exit-code> <utility-basename>
signal <signal-number> <utility-basename>
```

Use only the basename of a directly executed utility. In shell mode use the basename of the selected shell (for example, `bash` for `/bin/bash`). AWK output goes to stdout after any child stdout; child stderr remains on stderr. With `-z`, status filtering does not alter the propagated child exit or signal-derived status.

Choose the filter path from nonempty `ENTR_STATUS_SCRIPT`. If that variable is absent or empty, use `.entr/status.awk` below the current user's login home directory. If the selected file is missing, create its parent directory as mode 0750 and the file as mode 0640, and preserve paths containing spaces/metacharacters. Once the first utility execution begins, write `entr: created '<path>'` plus a newline to stdout; this pending announcement precedes the first formatted status line. Creating the file does not itself emit the line. In particular, with `-pxx`, create the filter before waiting while leaving stdout empty; if SIGINT terminates the monitor before an event, exit 0 without ever emitting the creation line. If an event instead launches the first utility, emit the line at that time. The new file's exact contents are:

```awk
# http://eradman.com/entrproject/status-filters.html
/^signal/ { print $3, "terminated by signal", $2; }
/^exit/ { print $3, "returned exit code", $2; }
```

Never overwrite or announce an existing filter. Existing scripts are evaluated with ordinary AWK record/field semantics, so their exact printed output replaces the default status sentence.

Two occurrences (`-xx` or `-x -x`) select the platform-compatible AWK invocation needed for functional status formatting. With the supplied Linux `awk`, one `-x` attempts a mode using AWK's `-S` option; because that AWK does not support `-S`, stderr contains the newline-terminated line `awk: not an option: -S` and monitoring aborts with status 0 after the helper dies. There is a timing race in reporting that helper death: stderr can end after the AWK line, or it can additionally contain the newline-terminated line `executable: status process terminated`. Both outcomes occur for the same invocation. A double-`x` one-shot run must instead work and format all normal codes 0–255 and signals, for example:

```text
tool.sh returned exit code 42
tool.sh terminated by signal 15
```

In continuing monitoring mode without `-z`, completion records are not delivered to the double-`x` filter. In particular, `-nxx /bin/sh -c 'exit 6'` remains alive after the initial child exits but writes no record at all; later watched-file events launch further children but likewise produce no status records. A monitor SIGINT then exits cleanly with status 0.
