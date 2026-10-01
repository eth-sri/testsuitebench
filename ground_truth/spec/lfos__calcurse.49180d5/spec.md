# Clarified specification for `executable`

The required artifact is one directly runnable program named exactly `executable`. It implements the calendar organizer described below. All dates use the proleptic Gregorian calendar and all text is UTF-8. Unless an error is specified, an operation exits with status 0, writes no diagnostic to standard error, and terminates promptly. In output examples, the notation `\t` denotes one literal tab byte. Output always ends in a newline unless explicitly described as empty or as a caller-supplied format with no newline.

The `.ical` files under `assets/` are normative examples of the accepted iCalendar input subset. They are part of this specification, not runtime dependencies.

## Spec 1

The interface is flag-based; words such as `query`, `grep`, `add`, or `event` are not subcommands. With no operation flag and no positional arguments, the program starts interactive mode even when its standard streams are pipes rather than an attached terminal: it emits curses terminal-control output and remains running awaiting interactive input. Otherwise exactly one operation is selected from query (`-Q`/`--query` and its short forms), grep (`-G`/`--grep`), purge (`-P`/`--purge`), import (`-i`/`--import`), export (`-x`/`--export`), garbage collection (`-g`/`--gc`), daemon, status, help, or version.

All ordinary positional arguments are invalid. Multiple operation flags, for example `-Q -G`, are invalid. A positional argument is ignored when a valid `-h` or `--help` is also present, so `query --help` and `--help subcommand` show general help and succeed. Unknown options are still errors even alongside help. `--` ends option parsing; a help option before it still shows help.

Short options accepting mandatory values may use attached or separate values, for example `-d02/25/2011` and `-d 02/25/2011`. The optional arguments of `-r`, `-s`, `-t`, and `-x` are attached: `-r7`, `-t3`, and `-xical`. Long optional arguments use `=`, such as `--range=7`, `--startday=01/01/2020`, and `--export=pcal`. In particular, `-x pcal` is an invalid argument combination rather than a pcal export.

## Spec 2

Both `-h` and `--help` print exactly the following plain text to stdout, print nothing to stderr, and exit 0:

```text
Usage:
calcurse [-D <directory>] [-C <directory>] [-c <calendar file>]
calcurse -Q [--from <date>] [--to <date>] [--days <number>]
calcurse -a | -d <date> | -d <number> | -n | -r[<number>] | -s[<date>] | -t[<number>]
calcurse -h | -v | --status | -G | -P | -g | -i <file> | -x[<format>] | --daemon

Operations in command line mode:
  -Q, --query   Print items in a given query range
  -G, --grep    Grep items from the data files
  -P, --purge   Read items and write them back
Query short forms:
-a, -d <date>|<number>, -n, -r[<number>], -s[<date>], -t<number>

Note that filter, format and day-range options affect input or output:
  --filter-*              Filter items loaded by -Q, -G, -P and -x
  --format-*              Rewrite output from -Q, -G and --dump-imported
  --from <date>           Limit day range of -Q.
  --to <date>             Limit day range of -Q.
  --days <number>         Limit day range of -Q.

  --limit, -l <number>    Limit number of query results
  --search, -S <regexp>   Match regular expression in queries
Consult the man page for details.

Miscellaneous:
  -c, --calendar <file>   The calendar data file to use
  -C, --confdir <dir>     The configuration directory to use
  --daemon                Run notification daemon in the background
  -D, --datadir <dir>     The data directory to use
  -g, --gc                Run the garbage collector
  -h, --help              Show this help text
  -i, --import <file>     Import iCal data from file
  -q, --quiet             Suppress import/export result message
  --read-only             Do not save configuration or data files
  --status                Display status of running instances
  -v, --version           Show version information
  -x, --export[<format>]  Export to stdout in ical (default) or pcal format

For more information, type '?' from within calcurse, or read the manpage.
Submit feature requests and suggestions to <misc@calcurse.org>.
Submit bug reports to <bugs@calcurse.org>.
```

No ANSI escapes are used. Both version flags likewise print exactly:

```text
calcurse 4.8.2 -- text-based organizer

Copyright (c) 2004-2023 calcurse Development Team.
This is free software; see the source for copying conditions.
```

## Spec 3

Command-line validation is eager. Failures exit nonzero (normally 1) and put the explanatory diagnostic on stderr. Unknown options contain `unrecognized option`; a missing short-option value contains `option requires an argument -- 'X'`, and a missing long-option value contains `option '--name' requires an argument`. Unknown options also put this abbreviated guidance on stdout (all four synopsis lines are present):

```text
Usage:
calcurse [-D <directory>] [-C <directory>] [-c <calendar file>]
calcurse -Q [--from <date>] [--to <date>] [--days <number>]
calcurse -a | -d <date> | -d <number> | -n | -r[<number>] | -s[<date>] | -t[<number>]
calcurse -h | -v | --status | -G | -P | -g | -i <file> | -x[<format>] | --daemon
Try `calcurse -h` for more information.
```

Invalid positional/mode combinations contain `invalid argument combination`. Filter, format, and query-range options used without an applicable operation are invalid combinations. `-Q` cannot be combined with another operation. Combining `--to` with `--days` exits 1 and reports `cannot specify a range and an end date`; an end date before a start date reports `end date cannot come before start date`, and `-P --filter-invert` is invalid.

The following validations are required: a zero day range reports `invalid range: 0`; invalid `--input-datefmt` values report `invalid input date format: VALUE`; todo or filter priorities outside their allowed range report `invalid priority: VALUE`; an unknown type reports `invalid filter mask`; an invalid two-date filter range reports `invalid date range: VALUE`; invalid regular expressions report `could not compile regular expression: VALUE`; invalid exports report `invalid export format: VALUE`; malformed date arguments report `invalid date: VALUE`.

Some diagnostics expose the stable 4.8.2 source prefix and must match it where applicable: `args.c: <error location>: invalid filter mask\n`, `args.c: <error location>: invalid priority: abc\n`, `args.c: <error location>: invalid date: invaliddate`, `args.c: <error location>: end date cannot come before start date`, `args.c: <error location>: invalid priority: 99`, `args.c: <error location>: could not compile regular expression: [invalid`, `args.c: <error location>: invalid range: 0`, and `args.c: <error location>: invalid export format: invalid`. A named nonexistent calendar file reports `PATH does not exist`. An inaccessible import file exits 1, produces no normal stdout, and emits `io.c: <error location>: FATAL ERROR: the input file cannot be accessed, Aborting...\n`; this is the observed diagnostic for both `/no/such/file` and `/nonexistent.ics`-style paths.

## Spec 4

Data and configuration are filesystem-backed. The data directory contains `apts`, `todo`, `notes/`, and daemon PID/log files. Import-failure logs are temporary files and are not placed in the data directory; their location is specified in Spec 17. The configuration directory contains `conf` and `keys`. `-D DIR`/`--datadir DIR` chooses the data directory and, unless `-C` is present, also the configuration directory. `-C DIR`/`--confdir DIR` independently overrides configuration lookup. `-c FILE`/`--calendar FILE` selects the appointments/events file and takes precedence over `-D`; a relative FILE is relative to the current working directory.

Without explicit paths, use `$HOME/.calcurse` for both kinds only if that legacy directory exists. Otherwise use `${XDG_DATA_HOME:-$HOME/.local/share}/calcurse` and `${XDG_CONFIG_HOME:-$HOME/.config}/calcurse`. Explicit `-C` overrides `XDG_CONFIG_HOME`.

Normal, non-read-only commands create required directories and empty files as needed. In particular, `-a -D DIR` creates `DIR/apts` and `DIR/conf`, and `-t -D DIR` creates `DIR/todo` and `DIR/conf`. Separating `-D DATA -C CONF` creates data files below DATA and `conf` below CONF. Missing ordinary files are therefore an empty database for those writable commands. `--read-only` suppresses all data/config writes and implicit saving, but it does not synthesize missing input storage: `--read-only -D NONEXISTENT -a` exits 1 with empty stdout and `failed to open appointment file` on stderr, while leaving `NONEXISTENT` absent. Import is the principal write operation; repeated imports append rather than replace.

## Spec 5

The configuration file is UTF-8 `key=value`, one directive per line; blank lines and `#` comments are allowed. Silently accept these keys: `appearance.calendarview`, `appearance.compactpanels`, `appearance.defaultpanel`, `appearance.layout`, `appearance.notifybar`, `appearance.sidebarwidth`, `appearance.theme`, `daemon.enable`, `daemon.log`, `format.inputdate`, `format.notifydate`, `format.notifytime`, `format.outputdate`, `general.autogc`, `general.autosave`, `general.confirmdelete`, `general.confirmquit`, `general.firstdayofweek`, `general.multipledays`, `general.periodicsave`, `general.progressbar`, `general.systemdialogs`, `general.systemevents`, `notification.command`, `notification.notifyall`, and `notification.warning`. Most only affect the interactive presentation and need no additional command-line behavior beyond being accepted. `format.inputdate=1` through `4` has the meaning in Spec 7, `format.outputdate` is a `strftime` pattern, `general.firstdayofweek` affects weekly recurrence, and `daemon.log` affects Spec 20. `--output-datefmt` overrides the configured output format. `--input-datefmt` overrides the configured input format only for command-line date arguments that follow it, as detailed in Spec 7.

A missing configuration file is harmless. Ignore a syntactically formed but unknown option after emitting `unknown user option: "key" (ignored)` to stderr; the value after `=` is omitted from the warning. A nonblank line without `=` is a fatal error containing `invalid configuration directive`; configuration is loaded early enough that this also prevents `-C bad-directory --help` from succeeding.

## Spec 6

The native `apts` file has one item per line. Its canonical forms are:

```text
MM/DD/YYYY [ID] MESSAGE
MM/DD/YYYY [ID] {REPEAT} MESSAGE
MM/DD/YYYY @ HH:MM -> MM/DD/YYYY @ HH:MM|MESSAGE
MM/DD/YYYY @ HH:MM -> MM/DD/YYYY @ HH:MM {REPEAT} |MESSAGE
```

The first two are all-day events; `ID` is a positive decimal event identifier. The last two are appointments and may span midnight or many days. Input accepts either no whitespace or whitespace immediately before the appointment message delimiter. `|` introduces an ordinary appointment message; `!` replaces `|` (rather than preceding it) and introduces a notification-enabled appointment message. Thus `02/23/2013 @ 10:00 -> 02/23/2013 @ 12:00 !Appointment` is valid. A note link is a `>NOTE_NAME` token followed by whitespace and then the `|` or `!` delimiter, as in `... >NOTE_NAME |MESSAGE`. Events likewise permit `>NOTE_NAME` between their structural fields and message. Preserve arbitrary UTF-8, punctuation, spaces, and descriptions of at least 500 characters. Empty descriptions are accepted. The note filename is stored below `notes/` and its file contents are the note.

The native `todo` file has one item per line: `[P] MESSAGE` for open items and `[-P] MESSAGE` for completed items, where `P` is 0 through 9. An optional note link occurs directly after the bracket, as `[3]>NOTE_NAME MESSAGE`. Reading and saving must preserve completion and note links. Priority 1 is highest and 9 lowest; 0 means no priority for an open item.

`-G` and `%(raw)` serialize the canonical native line, including its trailing newline; they do not preserve insignificant input whitespace byte-for-byte. An ordinary appointment's delimiter is normalized to no preceding space (`...10:30|Meeting`), whereas a recurring appointment is normalized to exactly one space between its closing recurrence brace and delimiter (`...{1D} |Meeting`). `%(hash)` is the lowercase hexadecimal SHA-1 of the canonical native line's bytes excluding its terminating newline. Thus the newline emitted by `%(raw)` is not part of the hash input. Hashes are stable across invocations and can be used as exported UIDs.

Malformed native data normally fails with nonzero status. Distinguish and include the phrases `syntax error in the item date`, `illegal date in appointment` (or `date error in appointment`), `syntax error in item time or duration`, `syntax error in item state`, `syntax error in item repetition`, `illegal date in event` (or `date error in event`), `syntax error in item identifier`, `syntax error in item state`, and `no event nor appointment found` as appropriate. Specifically, `01/01/2020 @ 25:00 -> 01/01/2020 @ 26:00|bad` reports `illegal date in appointment`, and `not an item` reports `syntax error in the item date`. The exceptional zero-interval recurrence `01/01/2020 [1] {0D} bad` terminates from signal 8 (SIGFPE), with empty stdout and stderr. Malformed todos include a `syntax error` diagnostic. A zero-byte calendar file is empty, but a whitespace-only calendar beginning with spaces/tab is not: `-G` exits 1 and reports `syntax error in the item date` for line 1.

## Spec 7

Input dates default to format 1 and may be selected by config or `--input-datefmt N`:

- 1: `mm/dd/yyyy`
- 2: `dd/mm/yyyy`
- 3: `yyyy/mm/dd`
- 4: `yyyy-mm-dd`

Command-line date arguments are parsed immediately from left to right using the input format active when each argument is encountered. `--input-datefmt N` therefore must precede a date-valued option such as `-d` to affect that option; it does not retroactively reparse an earlier date. For example, `-d 29/2/2020 --input-datefmt 2` exits 1 with `args.c: <error location>: invalid date: 29/2/2020`, while `--input-datefmt 2 -d 29/2/2020` accepts the leap day. The same ordering rule applies when the initial active format comes from `format.inputdate`: a later CLI switch does not override the configuration for a date already parsed.

One- or two-digit months/days are accepted. Validate real Gregorian dates, leap days, times from `00:00` through `23:59`, and years at least through 9999. Output date headings default to `%D`, namely `MM/DD/YY:`; the two-digit year is the final two digits (`2100` displays `00`, `9999` displays `99`). `--output-datefmt FORMAT` replaces the heading's date portion using `strftime`.

Recognize `today` case-insensitively wherever a command-line date is accepted. Filter dates may append one space and a `HH:MM` time. Date-only start boundaries mean `00:00:00`; event end boundaries mean `23:59:59`.

## Spec 8

`-Q`/`--query` emits matching calendar occurrences by default. It emits todos before those occurrences only when `todo` is explicitly included in `--filter-type`; todo-specific filters such as `--filter-priority`, `--filter-completed`, and `--filter-uncompleted` do not by themselves enable todo output. Its default day range is today. `--from D` alone selects D; `--from A --to Z` includes both endpoints; `--from A --days N` includes A and the following days. Without `--from`, `--to` and `--days` anchor at today. A positive day count is a number of included calendar days, so `--days 3` means three days, not today plus three. Zero is invalid.

`--day DATE` is an accepted single-day query selector and can be used with `-Q`, as in `-Q --day 8/1/2020`. Query short forms compose: `-d DATE -rN` selects an N-day range beginning at DATE, and `-tP -sDATE -rN` emits both the selected todos and the selected calendar range, with the todo section first.

Short forms are semantic aliases:

- `-a`/`--appointment`: today's calendar items only.
- `-d DATE`: calendar items on DATE. `-d N`: N-day calendar range anchored at today.
- `-r[N]`/`--range[=N]`: calendar range beginning today, default one day.
- `-s[DATE]`/`--startday[=DATE]`: calendar items beginning at DATE, default today; it can be combined with `-rN`.
- `-t[N]`/`--todo[=N]`: todos as defined in Spec 10.
- `-n`/`--next`: first appointment starting in the next 24 hours, prefixed by remaining hours/minutes; if none exists, succeed with empty stdout.
- `-S REGEX`/`--search REGEX`: equivalent to `--filter-pattern` when used with a query short form.

`--limit N`/`-l N` limits the number of item results, not headings, for queries; 0 means zero query item results, not unlimited. In particular, `-t -l 0` exits 0 with empty stdout even when open todos exist. Grep accepts this option but does not apply the limit: `-G --limit 2` and `-G --limit 0` still emit every object selected by the filters. Empty result sets succeed and are empty. In particular, an unfiltered `-Q` does not show todos when no calendar occurrence lies in its day range.

## Spec 9

Default calendar output is grouped only under dates having at least one matching occurrence. Events precede appointments. Events on a day are ordered lexicographically by description, not by input order. Appointments are ordered by occurrence start time and then lexicographically by description when starts are equal. Thus same-start imports place `30 minutes` before `5 hours`, and equal-time timezone items place `CET`, `Local time`, then `UTC`. The exact forms are:

```text
MM/DD/YY:
 * EVENT MESSAGE
 - HH:MM -> HH:MM
\tAPPOINTMENT MESSAGE

```

There is one blank line between nonempty day groups. Appointment spans are half-open at their end: an appointment ending exactly at midnight does not occupy the date beginning at that midnight. Print an appointment on every day whose calendar-day interval it overlaps. Use `..:..` for an endpoint outside the displayed day: on a first day whose appointment continues beyond the next midnight, replace the later end; on intermediate days replace both; on the last occupied day replace an earlier start. Thus an appointment from Feb 23 10:00 to Feb 24 12:00 renders `10:00 -> ..:..` on the 23rd and `..:.. -> 12:00` on the 24th. A midnight-to-next-midnight appointment occupies only its start date and displays `00:00 -> 00:00`; it does not use a continuation marker or print on the end date. A zero-duration appointment likewise displays equal start/end times. Date and time calculations remain correct across month/year boundaries, leap years, the 2038 boundary, and DST transitions; recurrence preserves local wall-clock time.

As a canonical example, a day containing event `Socket ghastlier` and an appointment covering the whole day is:

```text
02/25/11:
 * Socket ghastlier
 - ..:.. -> ..:..
\tCovenants useful smoker's
```

## Spec 10

`-t` lists only open todos and prints `to do:\n` followed by `P. MESSAGE\n`. It orders priority 1 through 9 first and no-priority (0) last; descriptions are sorted lexicographically within a priority rather than retaining file order. `-tP`, for P from 1 through 9, selects open todos of that exact priority and uses the same lexical description order. `-t0` selects completed todos of every stored priority and uses the heading `completed tasks:\n`. Completed output prints the absolute priority, for example native `[-5] Done` becomes `5. Done`.

A general query whose `--filter-type` explicitly includes `todo`, and which has neither `--filter-completed` nor `--filter-uncompleted`, includes both open and completed todos. Such a mixed result uses `to do:` and orders open todos first by priority, followed by completed todos by absolute priority. `--filter-priority=P` compares the absolute priority and therefore can match both `[P]` and `[-P]`; adding a completion filter narrows it. `--filter-priority` accepts only 1 through 9, whereas `-t0` has the special completed meaning.

## Spec 11

Filters affect `-Q` and all query short forms, `-G`, `-P`, and `-x`. Multiple filters are ANDed and `--filter-invert` negates their combined result once. `--filter-type` accepts a comma-separated union of `event`, `apt`, `recur-event`, `recur-apt`, and `todo`; `recur` expands to both recurring types and `cal` expands to all four calendar types.

`--filter-pattern REGEX` is a case-sensitive POSIX extended regular-expression search of the full description; it is an unanchored substring match unless the expression supplies anchors. It supports groups, alternation, character classes, and repetition.

Calendar filters are `--filter-start-from`, `--filter-start-to`, `--filter-start-after`, `--filter-start-before`, `--filter-start-range=A,B`, and the analogous six `--filter-end-*` options. `from` and `to` are inclusive; `after` and `before` are strict; range includes both bounds. Start/end filtering does not remove todos unless a type filter does so. For recurring items the criterion is the original item's first start/end, after which all occurrences surviving the query day range may print. Todo filters are `--filter-priority`, `--filter-completed`, and `--filter-uncompleted`.

## Spec 12

Format options are `--format-apt`, `--format-recur-apt`, `--format-event`, `--format-recur-event`, and `--format-todo`; they affect only their named types in queries, grep, and `--dump-imported`. The supplied format is used literally: no separator or newline is added around formatted items. Backslash escapes such as `\n` and `\t` in an argument are interpreted as newline and tab.

Default query formats are ` - %S -> %E\n\t%m\n`, the same for recurring appointments, ` * %m\n` for both event kinds, and `%p. %m\n` for todos. Grep and dump-imported default to `%(raw)`.

Common substitutions are `%m` description, `%n` note filename, `%N` displayed note contents, and `%%` percent. `%N` is not the raw note bytes: each note line is prefixed with a tab and the substitution ends with an additional newline. For a note file containing `note contents\n`, `%n|%N` produces `note1|\tnote contents\n\n`. Todo `%p` is the absolute priority. Appointment `%S`/`%E` are display times with the cross-day `..:..` markers; `%s`/`%e` are Unix epoch seconds; `%d` is the stored duration in seconds (iCalendar sub-minute seconds are discarded as described in Spec 15).

Extended appointment forms are `%(start:FORMAT)`, `%(end:FORMAT)`, and `%(duration:FORMAT)`. Omitting the duration format yields total seconds. Start/end accept `epoch`, `default`, or any `strftime` format. Duration accepts `%d`, `%H`, `%M`, `%S`, optional `-` to suppress two-digit zero padding, and optional `E` to avoid clock-field wrapping. For example a 10:00–11:15 appointment has `%d` equal to `4500`; `%(start:%Y-%m-%d %H:%M)` includes its date and time.

## Spec 13

Native recurrence is inside braces. Its base is a positive interval followed by `D`, `W`, `M`, or `Y`; optional `-> DATE` is an inclusive last date, and `!DATE` entries exclude occurrences. Examples are `{1D}`, `{1W}`, `{1M}`, `{1Y}`, `{3D -> 12/31/2000}`, and `{3D !01/04/2000}`. Daily recurrence advances calendar days, weekly advances seven-day blocks, monthly retains the applicable month-day, and yearly retains month/day. Impossible candidates such as February 30, the 31st in a 30-day month, or February 29 in a non-leap year are skipped rather than adjusted.

The extended native selector tokens used by imported RFC rules are also accepted, but their native grammar is positional. Any `-> DATE` and `!DATE` clauses come immediately after the base recurrence and before selectors. Each selector token contains exactly one integer; repeat the prefix for multiple values. Thus `{1M d-1 m1 m2 m3}` and `{1M -> 03/31/2024 w12}` are syntactically valid, while `{1M d-1 m1,2,3}` and `{1M w12 -> 03/31/2024}` exit 1 with `missing end of recurrence`. `dN` selects day N of a month, with negative N counting backward from month end. `mN` selects month N. `wN` selects weekdays or ordered weekdays: 0 through 6 mean Sunday through Saturday; positive ordered weekday K/day is encoded as `7*K + day`, while a negative order is encoded as `7*K - day` (for example `w12` is first Friday, `w-7` last Sunday, `w-15` second-to-last Monday, and `w141` twentieth Monday). Repeated values of one selector class are ORed and different selector classes are intersected. A native recurring item's stored start date must itself satisfy all of its selectors. Loading `01/01/2024 [1] {1M -> 03/31/2024 w12} First Friday` therefore exits 1 with empty stdout and a diagnostic containing `recurrence error: not on start day (01/01/2024)`, because that Monday is not a first Friday. Weekly interval grouping honors `general.firstdayofweek` (`monday` or `sunday`).

Recurring multi-day appointments repeat the entire duration and use the half-open-day/continuation rules from Spec 9. If multiple instances of the same recurring definition overlap one queried day, render that definition only once for that day, using the most recent applicable instance. For the daily six-day `Third recurrent appointment`, 01/10/2000 therefore contains only its instance beginning at `00:00`, rendered `00:00 -> ..:..`, rather than all still-running earlier instances. Recurrences work over large ranges, preserve time through DST, honor end dates and exceptions, and do not duplicate an occurrence. Recurring events and appointments remain distinct for filtering and formatting.

## Spec 14

`-G` prints every selected object in normalized native data-file representation, normally one line per item. Its fixed type order is todos, recurring events, recurring appointments, ordinary appointments, then ordinary events. Thus for an ordinary event, ordinary appointment, and todos, the todos print first and the appointment precedes the event. Within the todo block, open todos precede completed todos. Open priorities sort 1 through 9 with priority 0 last; completed priorities sort by absolute priority. Descriptions sort lexicographically within the same priority. For example, native todos stored as `[0] Later`, `[-5] Done`, `[1] First` are emitted as `[1] First`, `[0] Later`, `[-5] Done`. Appointment delimiter spacing is normalized by type as specified in Spec 6: no space for an ordinary appointment and one space after the recurrence brace for a recurring appointment. It applies all filters and type-specific custom formats. It does not expand a recurrence into duplicate lines.

`-P` removes all items matching the supplied filters and rewrites the database atomically, producing no normal output. With no filters it removes all items. Todos or other unselected types remain intact. `--read-only` prevents this mutation.

`-g`/`--gc` scans `notes/`, removes files no longer referenced by any calendar/todo item, preserves referenced notes and all todos/data items, and is silent on success. Empty and missing note directories are valid.

## Spec 15

`-i FILE`/`--import FILE` imports iCalendar 2.0. Accept LF or CRLF and unfold folded content lines. Component delimiter names and ordinary item property names are parsed case-insensitively: lowercase `begin:vevent`, `dtstart`, and `summary` are accepted. The header is an exception: its version line must use the uppercase spelling `VERSION:2.0`. Property parameters used to distinguish value types are also case-sensitive; `VALUE=DATE` is accepted, while either `value=DATE` or `VALUE=date` makes that start invalid. Require a `VCALENDAR` wrapper and `VERSION:2.0`. A CRLF input whose eight physical lines use lowercase `version`, `dtstart;value=date`, and `summary` is rejected at its header: it exits 0, writes `Import process report: 0008 lines read\n0 apps / 0 events / 0 todos / 0 skipped\n` to stdout, and writes `ical.c: <error location>: Warning: ical header malformed or wrong version number. Aborting...\n` to stderr. A missing/wrong header is not otherwise a process failure: a three-line `VERSION:1.0` calendar exits 0, leaves stderr empty, and prints the normal `0003 lines read` zero-item report. A filesystem access failure is fatal as specified in Spec 3.

Every valid timed `VEVENT` becomes an appointment; every `VEVENT` whose `DTSTART` has `VALUE=DATE` becomes an event; every `VTODO` becomes a todo. `SUMMARY` is the item message. Support `DTSTART`, `DTEND`, `DURATION`, `RRULE`, `EXDATE`, `DESCRIPTION`, `LOCATION`, `COMMENT`, `PRIORITY`, `STATUS`, `TRANSP`, `UID`, and nested `VALARM`. Property parameters on `DURATION` are accepted and ignored when parsing the value, including a quoted value containing colon, semicolon, and comma such as `DURATION;TESTPARAM="Quoted string with colon(:), semicolon(;) and comma(,)":P1DT9H17M0S`. A missing `DTEND`/`DURATION` means zero duration. With both end and duration, reject the malformed item. Equal timed start/end is accepted. For all-day DTEND, RFC's end is exclusive; represent every covered day. A multi-day all-day input is stored as a daily recurring event through the day before DTEND, so each covered day queries as an event occurrence. It is consequently classified as `recur-event`, not `event`, by `--filter-type`.

iCalendar TEXT unescaping converts `\\n` to newline and `\\,`, `\\;`, and `\\\\` to their literal characters. DESCRIPTION becomes note content. Append `Location: VALUE` and `Comment: VALUE` sections when present, using one space after each colon and separating metadata from prior text with a line containing `-- `. For example the stored note is `First\nSecond\n-- \nLocation: Room 1\nComment: Bring, things\n`; `%N` displays it with the tab indentation described in Spec 12. Create note files under `notes/` named by their SHA-1 content hash. Export emits available note text as DESCRIPTION, subject to the round-trip limitation in Spec 18.

Floating local times, `Z` timestamps, and `TZID` timestamps are all accepted. Calendar display preserves the stated wall-clock fields for this interface (for example the three appointments in `assets/ical-007.ical` all display 11:00–12:00 even under `TZ=America/New_York`). ISO-8601 durations accept weeks, days, hours, minutes, seconds, and combinations such as `P1DT1H1M1S`, `PT5H`, and `PT5H30M10S`; however, seconds are discarded when the native minute-resolution appointment is created. Consequently `%d` reports `90060` for `P1DT1H1M1S` and `19800` for `PT5H30M10S`.

## Spec 16

Import `RRULE` supports `FREQ=DAILY|WEEKLY|MONTHLY|YEARLY`, `INTERVAL`, `COUNT`, `UNTIL`, `WKST`, `BYDAY` including positive/negative ordinals, `BYMONTHDAY` including negatives, and `BYMONTH`. DTSTART is included, BY lists expand/filter candidates in their frequency period, UNTIL is inclusive when an occurrence is not later than it, and EXDATE removes only the matching component's occurrences. For the reference importer, excluded candidates do not consume `COUNT`: generation continues until COUNT non-excluded occurrences remain. A weekly `MO,WE;COUNT=5` rule starting 01/01/2024 with an EXDATE on 01/03 therefore emits five occurrences on January 1, 8, 10, 15, and 17. Invalid candidate dates are ignored. This behavior covers every recurrence in `assets/ical-003.ical`, `assets/ical-014.ical`, and `assets/rfc5545.ical`.

Unsupported frequencies or malformed properties skip that component without corrupting valid components. Required import-log reasons include: `invalid or malformed event start time`, `item start date not defined`, `rrule frequency not supported`, `item priority is invalid`, `malformed summary`, `malformed exceptions`, `exception date, but no recurrence rule`, `malformed description`, `only one location allowed`, `invalid duration`, `invalid end time value type`, `invalid until format`, `invalid exception`, `either end or duration`, `end must be later than start`, and failure to find the end of an item.

## Spec 17

Unless quiet, a completed import prints exactly two report lines:

```text
Import process report: NNNN lines read
A app[s] / E event[s] / T todo[s] / S skipped
```

`NNNN` is the physical input-line count padded to four digits, and singular nouns are used only for count 1. `-q`/`--quiet` suppresses a successful report completely but not errors. With `--dump-imported`, each new object is printed first using grep-style raw defaults or supplied format options, and the two report lines follow all dumped objects. Thus a custom todo dump can produce `T:Dump me\nImport process report: 0007 lines read\n0 apps / 0 events / 1 todo / 0 skipped\n`. Imports persist unless `--read-only`; multiple imports retain earlier objects.

Normative corpus counts are: `ical-001`: 12 lines, 1 app, 0 events, 1 todo; `ical-002`: 28 lines, 5 apps; `ical-003`: 70 lines, 7 apps and 2 events; `ical-005`: 23 lines, 4 events; `ical-006`: 63 lines, 12 apps; `ical-007`: 18 lines, 3 apps; `ical-012`: 89 lines, 6 apps and 6 todos; `ical-014`: 106 lines, 7 apps, 1 event and 6 todos; `ical-015`: 11 lines, 1 app. All have zero skipped.

When at least one component is skipped, return 1, retain valid components, begin stderr with a blank line and `Some items could not be imported.`, and include exactly one `See PATH for details` reference to a created log. `PATH` is a temporary file named `calcurse_log.` followed by a generated suffix, below `$TMPDIR` when that variable is set and below `/tmp` otherwise; it is not below the directory selected by `-D`. For `assets/ical-009.ical`, report 131 lines, `3 apps / 0 events / 1 todo / 20 skipped`, and log each failure with its component and source line. After the log's standard header, the 20 reasons and line numbers are the ones implied by Spec 16 and that input, from `VEVENT [12]: invalid or malformed event start time.` through `VTODO [129]: The ical file seems to be malformed. The end of item was not found.`

## Spec 18

`-x`, `-xical`, `--export`, and `--export=ical` write iCalendar to stdout. Empty export is byte-for-byte:

```text
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//calcurse//NONSGML v4.8.2//EN
END:VCALENDAR
```

Use LF line endings and a trailing LF. Export creates balanced VEVENT/VTODO components. Events use `DTSTART;VALUE=DATE:YYYYMMDD`; appointments use `DTSTART:YYYYMMDDTHHMMSS` plus a normalized `DURATION:P...`; todos use `PRIORITY` and `STATUS:COMPLETED` when completed. Every component has escaped `SUMMARY`; include DESCRIPTION/LOCATION/COMMENT reconstructed from notes where available, recurrence as RRULE/EXDATE, and alarm/notification information when representable. Escape backslash, comma, semicolon, and newline in TEXT values. `--export-uid` adds `UID:` equal to the stable item hash; without it UID is not required.

Filters restrict exported components. Export/import is not fully closed for a recurring all-day event with exceptions. Exporting native `01/15/2024 [1] {1D -> 01/17/2024 !01/16/2024} >n1 Recurring` emits `RRULE:FREQ=DAILY;UNTIL=20240117` and `EXDATE;VALUE=DATE:20240116T000000`; importing that export returns 1, reports one skipped item, and logs `invalid exception`, while valid non-recurring appointments and todos from the same export are imported. The recurring event and its note are absent from the reimported database. In particular an export of only events containing Planning Day on 2024-01-15 and Company Retreat on 2024-01-16 consists of the standard three-line header, these two components, then the footer:

```text
BEGIN:VEVENT
DTSTART;VALUE=DATE:20240115
SUMMARY:Planning Day
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20240116
SUMMARY:Company Retreat
END:VEVENT
```

## Spec 19

`-xpcal` and `--export=pcal` emit pcal text, never VCALENDAR text. The fixed skeleton, including blank lines and the historical spelling `Apoints`, is:

```text
# calcurse pcal export

# =======
# options
# =======
opt -A -K -l -m -F Monday
# Display week number (i.e. 1-52) on every Monday
all monday in all week %w


# =============
# Recur. Events
# =============
# (pcal does not support from..until dates specification

# ======
# Events
# ======


# ==============
# Recur. Apoints
# ==============
# (pcal does not support from..until dates specification

# ============
# Appointments
# ============

#
# Todos
#

```

Insert each category's lines after its heading. Events are `Mon DD  MESSAGE`; appointments are `Mon DD  (HH:MM -> HH:MM) MESSAGE`; open todos are `note all  P. MESSAGE`. Todo lines use the same in-memory ordering as Spec 10: priorities 1 through 9, then 0, with descriptions lexicographically sorted within each priority; they do not preserve todo-file input order. Completed todos are excluded. For example the basic data set produces `Feb 14  Valentine's Day`, `Mar 17  St. Patrick's Day`, `Jan 15  (09:00 -> 10:30) Team Meeting`, and `note all  1. 1 Buy groceries`. Filters may yield a skeleton with only one populated category. Dates are abbreviated English month plus two-digit day; times are 24-hour and contain no AM/PM. Recurring items without a pcal representation leave their category empty rather than corrupting output.

## Spec 20

`--status` is per data directory. With no live instance, print exactly `calcurse is not running\n`. A live background daemon prints exactly `calcurse is running in background (pid N)\n`, where N is its actual process ID.

`--daemon` does not reject a missing `apts` or `conf` in the selected directory. In the observed `--read-only --daemon -D DIR` cases where DIR is an existing directory containing either no files or only an empty `apts`, the invoking process exits 0 with empty stdout and stderr, and no daemon remains live. A `.daemon.pid` can appear transiently during the missing-`apts` startup attempt but is removed when that child terminates. When a daemon does persist successfully, the invoking parent exits 0 silently after detaching it and the daemon writes `.daemon.pid` containing exactly its positive decimal PID and one newline. Separate data directories have isolated PID files/daemons.

SIGUSR1 reloads while keeping the same process alive. SIGINT, SIGTERM, SIGQUIT, and SIGALRM terminate cleanly and remove `.daemon.pid`; a terminated process may briefly remain only as a zombie. With `daemon.log=no`, do not create `daemon.log`. With `daemon.log=yes`, create it and include entries containing `started at` and `sleeping at`; clean shutdown appends `terminated at` and, for SIGINT, `signal 2`.

## Spec 21

Interactive mode is a terminal UI that remains running until quit, renders nonempty output, and identifies the application/calendar interface. It shows an Appointments area for the selected date and following days, a Calendar area, a TODO area, and a status/key bar. It reads and writes the same native files as CLI mode. Key actions come from the loaded `keys` file. With the explicitly present empty `keys` file used by the terminal invocation, a single `q` does not terminate the interface within four seconds, even though the status bar is rendered; do not treat `q` as an unconditional one-keystroke exit. With a normal binding, `q` initiates quit handling. `s` saves and Tab changes the active panel when those actions are bound.

`Ctrl-A` begins adding an item on the selected date. At the start-time prompt, empty input creates an all-day event and proceeds to its description. Otherwise accept `HH:MM` or `HHMM`; then accept an end time in either form, a relative duration `+Nh` or `+N` minutes, or empty input for a punctual appointment. Display ordinary appointments as `HH:MM -> HH:MM`; punctual appointments display their one time without `TIME ->`. Show all-day events before timed appointments and sort timed appointments chronologically. Multiple items on one day coexist.

For deletion in the appointments panel, `d` requests confirmation. Pressing `s` deletes the selected object and another key such as `n` cancels. The most recently created event is selected when entering the panel in the exercised workflow. Save persists additions/deletions in native format.

## Spec 22

`Ctrl-T` in interactive mode prompts for a todo description and then a single priority digit 0–9. It immediately displays the new item; priority 0 has no `0.` display marker and sorts after numbered priorities, while native storage remains `[0] MESSAGE`. Prioritized items display `P. MESSAGE`. Saving creates/updates `todo` with one line per item. Existing open and `[-P]` completed entries both load and remain unchanged by a save. Existing `[P]>NOTE MESSAGE` links and their note files are preserved.

The implementation must tolerate empty databases, hundreds of appointments/todos, overlapping and same-day items, very long and non-ASCII descriptions, CRLF imports, wide date ranges, dates beyond 2038, and concurrent independent invocations. Except for the explicit `{0D}` SIGFPE behavior in Spec 6, malformed-input command-line operations terminate promptly rather than hanging; all ordinary command-line operations complete within a few seconds for the supplied corpus.
