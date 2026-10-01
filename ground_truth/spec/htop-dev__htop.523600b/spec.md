# Clarified specification for `executable`

The required artifact is one directly runnable file named `executable`. It implements a compact htop-like process viewer. All text written to standard output or standard error is UTF-8-compatible byte output. Terms such as “frame,” “meter,” and “process row” are defined below; no other document is needed to interpret this specification.

## Spec 1

The executable has two invocation modes.

When invoked with `-n COUNT`, it runs in finite capture mode: it renders process-view frames to standard output, finishes without needing input, and returns status 0 when all arguments and required environment values are valid. This mode must work even though standard output is a pipe rather than a terminal. Except for the nonfatal configuration-save failures and their standard-error warnings described in Spec 16, a successful finite run writes nothing to standard error.

When invoked without `-n`, help, version, or sort-key help, it runs as an interactive full-screen terminal application. It paints a nonempty screen promptly and remains active to receive keys until the user quits. Spec 20 defines the tested interactions.

## Spec 2

`-h` and `--help` print a substantial usage message to standard output and return 0. The message must be over 500 bytes and contain `htop`, the word `help`, and at least the option names `--help`, `--version`, `--delay`, `--filter`, and `--sort-key`; it must also show `-d` or `--delay`. Repeating help options is harmless.

`-V` and `--version` print a concise version line and return 0. The output contains `htop` and a decimal version matching `DIGITS.DIGITS`, contains no `--help`, and is shorter than 200 bytes.

Help or version is an immediate informational action: if a later argument is invalid, the requested help or version is still printed successfully and the later invalid argument is ignored.

## Spec 3

The supported finite-mode command-line forms are:

- `-n COUNT`
- `-d DELAY`
- `-C` and `--no-color`
- `-U` and `--no-unicode`
- `-M` and `--no-mouse`
- `--no-function-bar`, `--no-meters`, and `--readonly`
- `-t`
- `-s COLUMN` and `--sort-key=COLUMN`
- `-p PID_LIST` and `--pid=PID_LIST`
- `-u`, `-u USER_OR_UID`, and `--user=USER_OR_UID`
- `-F FILTER` and `--filter=FILTER`
- `-H`, `-H SECONDS`, `--highlight-changes`, and `--highlight-changes=SECONDS`

Options may be combined in any order. Duplicate boolean options are accepted. If `-s` or `-d` occurs more than once, the last value wins. `-u` and `-H` have optional values: when their next token begins with `-`, that token is another option and the option uses its default. `-H` consumes a following non-option token as its seconds value.

## Spec 4

Unknown short or long options, malformed options such as `--=value`, and free-standing non-option arguments are errors. They return a nonzero status and produce a nonempty diagnostic, normally on standard error. For the unknown long option invocation `--unknown-option -n 1`, the status is 1, standard output is empty, and standard error contains `unrecognized option` and `--unknown-option`. A positional-argument diagnostic contains `unsupported`, `argv`, or `error`.

The options `-n`, `-d`, `-s`, `-p`, and `-F` require values. Omitting one returns nonzero and writes a diagnostic. An empty command filter, whether passed as `-F ""` or `--filter=`, is also an error whose diagnostic contains `invalid`, `filter`, or `error`.

Non-numeric values for `-n`, `-d`, or a supplied highlight duration are errors; the diagnostic contains `invalid` or `error`. `COUNT` must be a positive integer, so 0 and negative counts return nonzero. In particular, `-n 0 --no-color` returns status 1 with empty standard output and writes exactly `Error: maximum iteration count must be positive.` followed by a newline to standard error.

## Spec 5

`-n COUNT` limits a finite run to COUNT refresh iterations. Counts from 1 through 2,000 are routinely used and must not overflow, hang, or fail. Each iteration emits a complete enough frame that captured output grows across iterations: one ordinary frame exceeds 200 bytes, five frames exceed 300 bytes, and long runs readily exceed 3,000 bytes. Even filtered views with no matching rows retain headers and enough surrounding UI to exceed 50 bytes.

`-d DELAY` accepts a base-10 integer measured in tenths of a second. Values below 1, including 0, are clamped to 1; values above 100 are clamped to 100. A frame is rendered immediately, so a one-iteration run does not wait for the delay. For evaluation, finite capture mode is accelerated and performs no deliberate real-time sleep between captured frames. Thus one iteration completes well under 1.5 seconds, 100 iterations under 4 seconds, and every supported run through 2,000 iterations under 5 seconds; even a five-iteration run with `-d 100` finishes under 5 seconds. Dozens of one- or few-iteration invocations must likewise fit within a five-second test. The parsed delay remains refresh state that would govern interactive timing, but it does not slow finite capture mode.

## Spec 6

A default frame is a terminal-style system/process display. It includes all of the following visible material:

- a CPU meter containing `CPU`, a percentage or decimal number, and bracket/bar punctuation such as `[` or `]`;
- memory and swap meters labeled `Mem` and `Swp` (or unmistakable case variants), with memory units such as `K`, `M`, or `G`;
- `Tasks`, `Load` with a decimal value, and `Uptime` summaries;
- a process header containing `PID`, `USER`, CPU information, memory information, and `Command` or `COMMAND`;
- at least one numeric PID and ordinary process data. On the evaluated Linux environment the unfiltered display includes identifiers such as `root`, `bash`, or `sleep` when such processes exist;
- a bottom function-key bar in the normal mode, with visible `F` key labels.

The process view is refreshed rather than printed as a plain report, so terminal cursor-control sequences are part of captured standard output.

## Spec 7

Normal color mode uses ANSI control sequences beginning with the escape byte, including at least one `ESC [` sequence. `-C`, `--no-color`, or a nonempty `NO_COLOR` environment variable disables color attributes, but not terminal cursor positioning; monochrome captured output may and should still contain an escape byte. A single frame in `NO_COLOR` mode has fewer than 500 `ESC [` occurrences. An empty `NO_COLOR` value is ignored.

`-U` or `--no-unicode` selects ASCII-safe meter/tree graphics while retaining all textual content and terminal control behavior. Locale values `LC_CTYPE=C`, `LC_ALL=C`, and `LC_ALL=en_US.UTF-8` must not prevent a successful finite run.

Terminal types `xterm`, `xterm-256color`, `linux`, and `dumb` are supported in finite mode. An empty `TERM` and the literal unsupported value `unknown` are rejected: with `-n 1`, each returns status 1, writes nothing to standard output, and writes exactly `Error opening terminal: unknown.` followed by a newline to standard error. No terminal-environment case may crash or hang.

## Spec 8

The following display switches are accepted independently and in arbitrary combinations with sorting, filtering, tree mode, delays, and repeated refreshes:

- `--no-meters` omits the meter area but retains a process header and process-view output;
- `--no-function-bar` omits the bottom function-key bar but retains the rest of the display;
- `-M` and `--no-mouse` disable mouse handling without changing the process data;
- `--readonly` disables actions that would change system or process state while retaining monitoring, sorting, filtering, and tree display.

Even with every display-reduction switch combined, a frame remains nonempty and normally exceeds 100 bytes because process information is still shown.

## Spec 9

The viewer obtains a snapshot of running processes and renders rows for the selected processes. A row has a decimal PID, user identity, command/name, state, CPU and memory data, plus any configured fields. It must tolerate processes starting or disappearing between iterations. When a live process whose command is `sleep` is created before invocation, a `-F sleep` view includes the text `sleep`.

These field names are recognized both in configuration `fields=` lists and, where meaningful, as sort columns:

`PID`, `Command`, `STATE`, `PPID`, `PGRP`, `SESSION`, `TTY`, `TPGID`, `MINFLT`, `CMINFLT`, `MAJFLT`, `CMAJFLT`, `UTIME`, `STIME`, `CUTIME`, `CSTIME`, `PRIORITY`, `NICE`, `STARTTIME`, `PROCESSOR`, `M_VIRT`, `M_RESIDENT`, `M_SHARE`, `M_TRS`, `M_DRS`, `M_LRS`, `ST_UID`, `PERCENT_CPU`, `PERCENT_MEM`, `USER`, `TIME`, `NLWP`, `TGID`, `PERCENT_NORM_CPU`, `ELAPSED`, `SCHEDULERPOLICY`, `RCHAR`, `WCHAR`, `SYSCR`, `SYSCW`, `RBYTES`, `WBYTES`, `CNCLWB`, `IO_READ_RATE`, `IO_WRITE_RATE`, `IO_RATE`, `CGROUP`, `CCGROUP`, `CONTAINER`, `ISCONTAINER`, `OOM`, `IO_PRIORITY`, `M_PSS`, `M_SWAP`, `M_PSSWP`, `CTXT`, `SECATTR`, `COMM`, `EXE`, `CWD`, `AUTOGROUP_ID`, `AUTOGROUP_NICE`, and `M_PRIV`.

Unavailable per-process values may be rendered as zero, blank, or `N/A`, but the named field must be accepted and the process view must remain valid.

## Spec 10

`-s COLUMN` sorts the displayed rows by the named field. Every field listed in Spec 9 must be accepted with the exact capitalization shown. Sorting works in repeated runs and in combination with every other supported view option. A second `-s` replaces the first. Unknown names such as `INVALID_KEY_XYZ`, and incorrectly cased names such as `pid`, return nonzero and write a nonempty error diagnostic.

`--sort-key=help` is a special successful action. It prints more than 20 newline-terminated entries, includes at least `PID`, `USER`, `PERCENT_CPU`, `PERCENT_MEM`, `Command`, and `STATE`, and includes descriptions using the word `process`. It exits without entering the viewer.

## Spec 11

`-p PID_LIST` and `--pid=PID_LIST` limit process rows to a comma-separated list of decimal process IDs. Whitespace around entries is tolerated, duplicate IDs are harmless, a trailing empty entry is ignored, and lists of at least 10,000 IDs are supported. For example, passing the comma-separated decimal sequence from 1 through 10000 with `-n 1` returns 0, writes nothing to standard error, and retains the normal process header. Existing requested PIDs are shown; in particular, requesting PID 1 produces a visibly delimited `1` in the process area. A nonexistent or extremely large positive PID is not a command-line error: the viewer returns 0 and displays its normal meters/header with no row for that PID.

PID filtering combines by intersection with user filtering and by intersection with command filtering. It also works with sorting, tree view, highlighting, delays, and display-reduction switches.

## Spec 12

`-u` with no value selects the current effective user. `-u root`, `--user=root`, and `-u 0` select the root account and return 0. A successful root-filtered view contains root process data when available and always retains the complete surrounding UI.

A supplied user is resolved as either an existing user name or a valid numeric UID. Unknown names, negative IDs, mixed alphanumeric pseudo-IDs such as `abc123`, and overflowing numeric IDs such as `999999999999` return nonzero. Their standard-error diagnostic contains `invalid`, `user`, or `error`.

## Spec 13

`-F FILTER` and `--filter=FILTER` filter on the displayed process command. Matching is case-insensitive and treats input as fixed text, not a regular expression. A vertical bar separates alternatives, so `bash|python|sleep` matches a command containing any one of those terms. Spaces inside a term are ordinary characters. Text such as `test.*` is matched literally.

No matches is a successful state: meters, summaries, and column headers are still rendered. Command filtering combines with PID and user filters, sorting, tree mode, highlighting, readonly mode, and repeated iterations.

## Spec 14

`-t` selects tree view. Rows are arranged by parent/child relationship and rendered with visible indentation or branch markers. A sort option without `-t` uses list view; when `-t` and `-s` are both supplied, tree view remains enabled and siblings may be ordered by the selected field. Tree mode works with PID, user, and command filters and all display switches.

Normal and tree views must both produce substantial, nonempty frames, including when only PID 1 is selected or when the selected process has children that appear or disappear.

## Spec 15

`-H` and `--highlight-changes` enable tracking of processes that appear or disappear between refreshes. With no supplied duration, an implementation-defined positive default is used. A supplied nonnegative integer duration, including 0, 1, 5, 50, and 999, is accepted. The supplied negative duration -1 is also accepted: `--highlight-changes=-1 -n 1` returns 0, writes no standard-error diagnostic, and renders a normal finite view. The feature composes with `-d`, tree mode, all supported sorts and filters, readonly mode, ASCII mode, and hidden meters/function bar. It must not cause a finite run to block beyond the limits in Spec 5.

`--drop-capabilities` is not supported. The forms `--drop-capabilities`, `--drop-capabilities=off`, `--drop-capabilities=basic`, and `--drop-capabilities=strict`, each followed by `-n 1`, return status 1 with empty standard output. Standard error identifies the complete supplied token as an `unrecognized option`.

## Spec 16

Configuration is line-oriented `key=value` text. `HTOPRC`, when nonempty, names the exact configuration file to use and takes precedence over other locations. Without it, the executable safely consults `XDG_CONFIG_HOME` and `HOME`; missing or unusable directories are not fatal. With `HTOPRC` empty and both `XDG_CONFIG_HOME` and `HOME` naming nonexistent directories, `-n 1` returns 0 and renders the view, but writes exactly `Cannot save configuration to : No such file or directory` followed by a newline to standard error. An explicit nonexistent path whose parent is unwritable is likewise nonfatal and falls back to defaults; with `HTOPRC=/proc/htop-eval-no-such-dir/htoprc`, `-n 1` returns 0 and writes exactly `Cannot save configuration to /proc/htop-eval-no-such-dir/htoprc: No such file or directory` followed by a newline to standard error.

If `HTOPRC` names a nonexistent file in an existing writable directory, a successful run creates it and leaves nonempty default configuration text. Existing empty files are accepted and remain usable. Repeated runs using the same file succeed. Existing valid content is used; it must not be deleted. Unknown keys, malformed lines, empty files, and an empty `fields=` value are tolerated by ignoring bad data and filling in safe defaults, never by failing the viewer. An invalid-only field list is also nonfatal, but it does not receive default process columns: `fields=NOT_A_REAL_FIELD ALSO_BAD` with `-n 1` returns 0 and writes nothing to standard error, renders the meter area, and omits the process header and process rows.

## Spec 17

The `fields=` value is a whitespace-separated field list using the names in Spec 9. Legacy numeric lists such as `0 48 17 18 38 39 2 46 47 49 1` are also accepted. The listed fields control column choice/order; at minimum a valid requested header such as `PID`, `USER`, `RCHAR`/`IO`, `VIRT`/`RES`, `FLT`, `TIME`, `UID`, `COMM`/`EXE`/`CWD`, `NLWP`/`TGID`, or `Command` is visibly represented. As specified in Spec 16, invalid-only lists do not fall back to the normal columns; they leave the process table without columns or rows while retaining the meter area.

The parser accepts global keys and dot-prefixed per-screen keys for `sort_key`, `sort_direction`, `tree_view`, `tree_sort_direction`, and `all_branches_collapsed`. It also accepts `screen:NAME=FIELD_LIST` blocks followed by dot-prefixed settings. Sort directions `1` and `-1` select opposite ordering directions.

## Spec 18

The following boolean/numeric configuration keys are accepted without making startup fail and affect the corresponding view preference when applicable:

`delay`, `hide_kernel_threads`, `hide_userland_threads`, `shadow_other_users`, `show_thread_names`, `show_program_path`, `highlight_base_name`, `highlight_deleted_exe`, `highlight_megabytes`, `highlight_threads`, `find_comm_in_cmdline`, `strip_exe_from_cmdline`, `show_merged_command`, `detailed_cpu_time`, `cpu_count_from_one`, `show_cpu_usage`, `show_cpu_frequency`, `show_cpu_temperature`, `update_process_names`, `account_guest_in_cpu_meter`, `header_margin`, `highlight_changes`, `highlight_changes_delay_secs`, `tree_view_always_by_pid`, `all_branches_collapsed`, and `shadow_distribution_path_prefix`.

Values 0 and 1 represent false and true. A command-line option overrides a conflicting configuration preference for that invocation. Configurations containing many of these keys at once must still render normally over many finite iterations.

## Spec 19

Meters are configured with `column_meters_0`, `column_meters_1`, and matching `column_meter_modes_0`/`column_meter_modes_1` whitespace-separated lists. Recognized meter names are `CPU`, `CPU(N)` for a numbered CPU, `AllCPUs`, `Memory`, `Swap`, `Tasks`, `LoadAverage`, `Uptime`, `DiskIO`, `NetworkIO`, `FileDescriptors`, `Battery`, `Clock`, `DateTime`, `Hostname`, `SysArch`, and `Systemd`.

Mode numbers are 1 for bar, 2 for text, 3 for graph, and 4 for LED. Mixed modes and multiple columns/meters are accepted. Meter data that the host cannot provide is represented safely, for example by `N/A`; it is not a startup error. A configured display still includes its process header, and useful labels are emitted where space permits: CPU, Memory/Mem, Swap/Swp, Tasks, Load, Uptime, Disk, Network, Battery, FDs, Hostname, architecture, or Systemd. Empty meter lists or missing mode lists are tolerated. `--no-meters` overrides configured meters.

## Spec 20

Interactive mode must operate inside a 120-column by 40-row terminal session. It paints nonempty content within 0.5 seconds and accepts these keys without exiting or blanking the display:

- `F1` or `h`: open a help screen containing `Help` or recognizable function-key help;
- `F2`: open a nonempty setup screen;
- `t`: toggle tree view;
- `/`, followed by typed text: enter incremental command search;
- backslash (`\`), followed by typed text: enter incremental command filtering;
- `F6`: open a nonempty sort-selection screen;
- Up and Down: move the selected process while keeping a nonempty display;
- Escape: cancel/close the current search, filter, help, setup, or sort overlay and return to the main display;
- `q`: close the current overlay if one is active, or quit from the main display. Consequently, sending `q` twice always terminates.

The application must continue to repaint or preserve visible content after sequences such as toggling tree mode, moving Down twice and Up once, opening help, and pressing Escape. It must handle terminal input directly rather than waiting for line-buffered Enter.
