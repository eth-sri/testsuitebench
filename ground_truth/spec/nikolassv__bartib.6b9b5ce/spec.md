# Clarified specification for `executable`

The required artifact is one runnable command-line program named exactly `executable`. It is a minute-precision plaintext time tracker whose user-facing product name and version are `bartib 1.1.0`. Unless a rule below says otherwise, successful commands exit 0, write normal output to standard output, and write nothing to standard error. Command-line usage errors and operating-system failures exit 1 and are written to standard error.

In examples, `ESC` means the single byte `0x1b`, `NBSP` means Unicode U+00A0, and “now” means the host's current local date and time. All files and output are UTF-8.

## Spec 1

The command-line shape is:

```text
executable [GLOBAL OPTIONS] <SUBCOMMAND> [SUBCOMMAND OPTIONS]
```

The only global data option is `-f <FILE>`. It must occur before the subcommand and may occur only once. The log path is selected from `-f`, otherwise from the `BARTIB_FILE` environment variable; the explicit flag has precedence. An unset `BARTIB_FILE` is unavailable. By contrast, a present but empty `BARTIB_FILE` selects the empty string as the path. A command that needs a log but has no selected path fails with exactly:

```text
Error: Please specify a file with your activity log either as -f option or as BARTIB_FILE environment variable
```

The line is newline-terminated. Relative paths are resolved from the process working directory. Spaces, punctuation, and Unicode in paths are ordinary filename characters. A missing log is created by `start` if its parent exists; read-oriented commands do not create it. They fail with this stderr form and exit 1:

```text
Error: Could not read from file: PATH

Caused by:
    No such file or directory (os error 2)
```

Consequently, a read-oriented command with `BARTIB_FILE` set to the empty string exits 1 with empty stdout and the same diagnostic with an empty `PATH` position:

```text
Error: Could not read from file: 

Caused by:
    No such file or directory (os error 2)
```

If `start` cannot create the file because its parent does not exist, it prints its normal `Started activity: ...` confirmation to stdout *before* attempting the write, then exits 1 and writes:

```text
Error: Could not write to file: PATH

Caused by:
    No such file or directory (os error 2)
```

The file is not created.

Help and version operations do not require a log. `-f` after a subcommand is not global and is rejected as an unexpected argument. Unknown flags, extra positionals, a second subcommand, uppercase command names, the empty command name, and aliases such as `ls`, `rm`, `mv`, and `cp` are rejected.

## Spec 2

`executable --help`, `executable -h`, and `executable help` exit 0 and print exactly the following to stdout, including the final newline. Running with no arguments prints the same text to stderr, prints nothing to stdout, and exits 1.

```text
bartib 1.1.0
Nikolas Schmidt-Voigt <nikolas.schmidt-voigt@posteo.de>
A simple timetracker

USAGE:
    executable [OPTIONS] <SUBCOMMAND>

FLAGS:
    -h, --help       Prints help information
    -V, --version    Prints version information

OPTIONS:
    -f <FILE>        the file in which bartib tracks all the activities [env: BARTIB_FILE=]

SUBCOMMANDS:
    cancel      cancels all currently running activities
    change      changes the current activity
    check       checks file and reports parsing errors
    continue    continues a previous activity
    current     lists all currently running activities
    edit        opens the activity log in an editor
    help        Prints this message or the help of the given subcommand(s)
    last        displays the descriptions and projects of recent activities
    list        list recent activities
    projects    list all projects
    report      reports duration of tracked activities
    sanity      checks sanity of bartib log
    search      search for existing descriptions and projects
    start       starts a new activity
    status      shows current status and time reports for today, current week, and current month
    stop        stops all currently running activities

To get help for a specific subcommand, run `bartib [SUBCOMMAND] --help`.
To get started, view the `start` help with `bartib start --help`
```

`executable --version` and `executable -V` print exactly `bartib 1.1.0\n` and exit 0. If top-level help and version flags are both present, the first one controls the result: `executable --version --help` prints only `bartib 1.1.0\n`, while `executable --help --version` prints the full help above.

An ordinary unknown argument uses the clap-style diagnostic below on stderr and exits 1 (substitute the actual token and the applicable usage line):

```text
error: Found argument 'TOKEN' which wasn't expected, or isn't valid in this context

USAGE:
    USAGE-LINE

For more information try --help
```

For example, the top-level usage line is `executable [OPTIONS] <SUBCOMMAND>` and the list usage line is `executable list [FLAGS] [OPTIONS]`. A misspelled `--verbose` diagnostic additionally suggests `--version`. After a top-level `--` separator, `--help` is interpreted as a subcommand and rejected with text containing `The subcommand '--help' wasn't recognized`, the usage, and the help hint.

Supplying two `-f` options without a subcommand, as in `executable -f A -f B`, exits 1, writes nothing to stdout, and writes the complete top-level help block above to stderr. It does not emit a duplicate-argument diagnostic.

## Spec 3

Every real subcommand supports both `-h` and `--help`; `help NAME` produces the same command-specific help. The first line is `executable-NAME ` with one trailing ASCII space before the newline, followed by the description. The normative schemas and wording are:

```text
executable-start 
starts a new activity

USAGE:
    executable start [OPTIONS] --description <DESCRIPTION> --project <PROJECT>

FLAGS:
    -h, --help    Prints help information

OPTIONS:
    -d, --description <DESCRIPTION>    the description of the new activity
    -p, --project <PROJECT>            the project to which the new activity belongs
    -t, --time <TIME>                  the time for changing the activity status (HH:MM)
```

```text
executable-stop 
stops all currently running activities

USAGE:
    executable stop [OPTIONS]

FLAGS:
    -h, --help    Prints help information

OPTIONS:
    -t, --time <TIME>    the time for changing the activity status (HH:MM)
```

```text
executable-change 
changes the current activity

USAGE:
    executable change [OPTIONS]

FLAGS:
    -h, --help    Prints help information

OPTIONS:
    -d, --description <DESCRIPTION>    the description of the new activity
    -p, --project <PROJECT>            the project to which the new activity belongs
    -t, --time <TIME>                  the time for changing the activity status (HH:MM)
```

```text
executable-continue 
continues a previous activity

USAGE:
    executable continue [OPTIONS] [NUMBER]

FLAGS:
    -h, --help    Prints help information

OPTIONS:
    -d, --description <DESCRIPTION>    the description of the new activity
    -p, --project <PROJECT>            the project to which the new activity belongs
    -t, --time <TIME>                  the time for changing the activity status (HH:MM)

ARGS:
    <NUMBER>    the number of the activity to continue (see subcommand `last`) [default: 0]
```

The `list` help is:

```text
executable-list 
list recent activities

USAGE:
    executable list [FLAGS] [OPTIONS]

FLAGS:
        --current_week    show activities of the current week
    -h, --help            Prints help information
        --last_week       show activities of the last week
        --no_grouping     do not group activities by date in list
        --today           show activities of the current day
        --yesterday       show yesterdays' activities

OPTIONS:
    -d, --date <DATE>          show activities of a certain date only
        --from <FROM_DATE>     begin of date range (inclusive)
    -n, --number <NUMBER>      maximum number of activities to display
    -p, --project <PROJECT>    do list activities for this project only
        --round <round>        rounds the start and end time to the nearest duration. Durations can be in minutes or
                               hours. E.g. 15m or 4h
        --to <TO_DATE>         end of date range (inclusive)
```

The `report` help is identical in layout but has description `reports duration of tracked activities`, usage `executable report [FLAGS] [OPTIONS]`, no number/no-grouping options, and the project wording `do report activities for this project only`:

```text
FLAGS:
        --current_week    show activities of the current week
    -h, --help            Prints help information
        --last_week       show activities of the last week
        --today           show activities of the current day
        --yesterday       show yesterdays' activities

OPTIONS:
    -d, --date <DATE>          show activities of a certain date only
        --from <FROM_DATE>     begin of date range (inclusive)
    -p, --project <PROJECT>    do report activities for this project only
        --round <round>        rounds the start and end time to the nearest duration. Durations can be in minutes or
                               hours. E.g. 15m or 4h
        --to <TO_DATE>         end of date range (inclusive)
```

The remaining command interfaces are normative as follows:

```text
cancel:   executable cancel
          cancels all currently running activities
check:    executable check
          checks file and reports parsing errors
current:  executable current
          lists all currently running activities
sanity:   executable sanity
          checks sanity of bartib log

last:     executable last [OPTIONS]
          -n, --number <NUMBER>    maximum number of lines to display [default: 10]

projects: executable projects [FLAGS]
          -c, --current      prints currently running projects only
          -n, --no-quotes    prints projects without quotes

search:   executable search <SEARCH_TERM>
          <SEARCH_TERM>    the search term [default: '']

status:   executable status [OPTIONS]
          -p, --project <PROJECT>    show status for this project only

edit:     executable edit [OPTIONS]
          -e <editor>        the command to start your preferred text editor [env: EDITOR=]
```

Each help page has the same blank-line structure as the full examples, contains a `FLAGS:` section, and is final-newline terminated. Whitespace within a flag row is command-specific rather than a universal four-space delimiter. In particular, the `list` help row is `    -h, --help            Prints help information`, exactly as shown in its full schema above. Simple commands have no `OPTIONS:` section. `help --help` is itself rejected; `help help` succeeds and shows a page headed `executable-help`.

## Spec 4

The activity log contains one activity per physical line in the canonical format:

```text
START [ - END] | PROJECT | DESCRIPTION
```

`START` and `END` use `YYYY-MM-DD HH:MM`. Reading also accepts `YYYY-MM-DD HH:MM:SS`, with a seconds component from `00` through `60` inclusive; `61` is invalid. Each accepted second-bearing timestamp is independently normalized before filtering, display, or explicit `--round` processing. Ordinary seconds values from `00` through `59` are also normalized before duration calculation: they are rounded to the nearest whole minute, with an exact `:30` midpoint rounding upward. Thus `09:00:29` becomes `09:00`, while `09:00:30` and `09:00:59` become `09:01`. The accepted leap-second value `:60` is exceptional: for display it does not carry into the next minute, so `09:00:60` displays as `09:00`, but its different treatment in duration calculation is specified in Spec 6. Each second-bearing timestamp also emits this exact two-line block to stderr, once per timestamp and in parse order, even when the command succeeds:

```text
WARNING: Bartib log encountered timestamps with minute precision.
This version of Bartib has been compiled with second precision
```

For example, a completed activity whose start and end both include seconds emits the block twice; a running activity with only its start in that form emits it once. Absence of ` - END` means the activity is running. A description may be empty, and a line containing only `TIMESTAMP | PROJECT` is accepted as having an empty description. Project and description are trimmed when read from a hand-written file, while internal spaces remain unchanged. Leading/trailing whitespace around timestamps and separators is ignored. CRLF is accepted.

The delimiter is an unescaped `|`. Within project or description, serialization first replaces `\` by `\\`, then `|` by `\|`. Parsing performs the inverse, so `test project\| 1` becomes `test project| 1` and `test\\description` becomes `test\description`. Quotes, tabs, punctuation, emoji, and all other Unicode are literal data. Extra unescaped pipe-separated material after the description is ignored. Consequently, literal pipes must be escaped to round-trip.

New activities are appended in file order and end with `\n`. Mutating commands preserve the order and parsed values of valid activities they do not logically affect, but a rewrite can canonicalize those records rather than preserve their original bytes, as detailed for `cancel` and `change`. Canonical examples are:

```text
2021-10-29 08:00 | Important Project | Urgent Task X
2021-10-29 08:00 - 2021-10-29 08:43 | Important Project | Urgent Task X
2021-10-29 08:00 |  | 
2021-10-29 08:00 | Project\|A | Description with \\ and \| characters
```

There is no field-length limit in the tested range (at least 1000 characters). Empty strings and whitespace-only strings supplied through `-p` or `-d` are valid and are preserved when written. A literal newline supplied inside a field is also accepted and therefore creates a physical newline in the file; no special newline escaping is performed.

## Spec 5

When normal commands encounter a physical line they cannot parse, they continue using all valid lines and print, on stdout and in source order:

```text
Warning: Ignoring line N. Please see `bartib check` for further information
```

Every blank or whitespace-only physical line is treated this way by normal readers, including when all physical lines in the file are whitespace-only. For example, a two-line whitespace-only file produces the warnings for lines 1 and 2 before the display command's empty-result message. Only an actually zero-byte file behaves as an empty activity set without line warnings. `check` has its own treatment of blank lines, specified later.

Dates are real Gregorian dates; invalid month/day combinations and non-leap-year February 29 are invalid. Timestamps must have hours 0–23, minutes 0–59, and, when present, seconds 0–60 as specified in Spec 4. A malformed structural line and a structurally plausible line with a malformed timestamp are distinct error classes for `check`.

## Spec 6

All generated timestamps use local time, truncated to whole minutes and formatted with zero-padded fields. `-t/--time` accepts `H:M`, `HH:M`, `H:MM`, or `HH:MM`, normalizes it to `HH:MM`, and combines it with today's local date. Thus `9:00` becomes `09:00` and `10:5` becomes `10:05`. A supplied stop time earlier than the start time is allowed and stored on the same current local date.

An invalid `--time` does not fail the command. It prints this warning to stdout and treats the option as absent:

```text
Can not parse "VALUE" as time. Argument for -t/--time is ignored (REASON)
```

`REASON` is `input is out of range` for numeric values outside valid ranges. A wholly lexical failure such as `noon` uses `input contains invalid characters`, but a valid prefix followed by junk uses `trailing input`; in particular, `1:2x` produces:

```text
Can not parse "1:2x" as time. Argument for -t/--time is ignored (trailing input)
```

For start, stop, and continue, an absent/ignored time means current local time. For change it means leave the existing start time unchanged.

Durations are computed as end minus start; a running activity uses now as its end. Negative, zero, and positive sub-minute durations all display as `<1m`; for example, stopping a 10:00 activity at 09:00 stores the negative interval but reports `(<1m)`. Otherwise discard fractional seconds and display durations below an hour as a two-digit minute count (`01m`, `05m`, `43m`), and durations of at least an hour as `Hh MMm`. Hours are not capped at 24. Ordinary second-bearing log timestamps are normalized as specified in Spec 4 before this subtraction, so 09:00:00–09:00:59 displays as `01m`. A `:60` endpoint is the exception: duration arithmetic treats it as the following whole-minute boundary even though its displayed hour and minute do not carry. Consequently, 10:00:59–10:01:60 displays both endpoints as `10:01` but displays duration `01m`; likewise, 10:00:00–10:00:60 displays both endpoints as `10:00` but displays duration `01m`. Equality of the displayed endpoints therefore does not by itself imply a zero duration.

`--round Nm` and `--round Nh` round each start and end timestamp independently to the nearest N-minute or N-hour boundary measured from local midnight; exact midpoints round upward. Duration is recomputed from the rounded endpoints. Examples: with 15m, 09:12–10:23 becomes 09:15–10:30; with 1h it becomes 09:00–10:00; with 5m it becomes 09:10–10:25. Exact boundaries remain unchanged. A syntactically invalid round value is silently ignored.

## Spec 7

`start -p PROJECT -d DESCRIPTION [-t TIME]` requires both options to occur, although their values may be empty. Long `--project=...` and `--description=...` forms are supported. Missing required values are command-line errors. For example, a missing project produces exactly:

```text
error: The following required arguments were not provided:
    --project <PROJECT>

USAGE:
    executable start [OPTIONS] --description <DESCRIPTION> --project <PROJECT>

For more information try --help
```

Before appending the new running activity, start stops every existing running activity at the selected start time. Stop confirmations occur first, in file order, followed by the start confirmation. The new record has no end timestamp. The confirmation is exactly:

```text
Started activity: "DESCRIPTION" (PROJECT) at YYYY-MM-DD HH:MM
```

For example, starting `Task 2` at 10:00 while `Task 1` from 09:00 is running prints:

```text
Stopped activity: "Task 1" (P1) started at YYYY-MM-DD 09:00 (1h 00m)
Started activity: "Task 2" (P2) at YYYY-MM-DD 10:00
```

## Spec 8

`stop [-t TIME]` completes every running activity using the chosen end timestamp. It preserves already completed entries and emits one line per stopped entry, in file order:

```text
Stopped activity: "DESCRIPTION" (PROJECT) started at START (DURATION)
```

`START` is the full `YYYY-MM-DD HH:MM`. Calling stop when nothing is running succeeds, produces no output, and makes no file change. Repeated stop calls do not add or alter end times.

`cancel` deletes every running activity rather than recording an end. Completed entries retain their parsed values and remain in the same order, but they are not byte-equivalent: cancel rewrites the file and removes trailing whitespace from their physical lines. For example, a surviving line ending in `| done  \n` is written back as `| done\n`. It prints one line per removed activity, in file order:

```text
Canceled activity: "DESCRIPTION" (PROJECT) started at START
```

Calling cancel when nothing is running exits 0 without stdout or stderr, but it still rewrites the parsed log in canonical form. For example, a completed-only file containing `2020-01-01 00:00 - 2020-01-01 00:01 | P | done  \r\n` is rewritten as `2020-01-01 00:00 - 2020-01-01 00:01 | P | done\n`: the trailing spaces are removed and CRLF is normalized to LF even though no activity was canceled.

## Spec 9

`change [-p PROJECT] [-d DESCRIPTION] [-t TIME]` updates every running activity, preserving each omitted field. An explicitly supplied empty field is different from an omitted option and replaces the field with empty text. `-t` replaces the start timestamp with today's date and that time. Completed activities are not changed, and file order is preserved. Each changed activity produces:

```text
Changed activity: "DESCRIPTION" (PROJECT) started at START
```

When no activity is running, change exits 0 and prints nothing, but it still rewrites the parsed log in canonical form rather than preserving its bytes. For example, the completed line `2020-01-01 00:00 - 2020-01-01 00:01 | P | D  \n` is rewritten as `2020-01-01 00:00 - 2020-01-01 00:01 | P | D\n`, removing the two trailing spaces.

## Spec 10

Historical task identity is the exact, case-sensitive pair `(description, project)`. Here “newest” is determined by the activity start timestamp, not by physical/logical position in the file. Build the recent-task sequence from activities in descending chronological start order, retaining only the chronologically newest occurrence of each distinct pair. Index 0 is the chronologically newest distinct pair, index 1 the next newest, and so on. Thus deliberately scrambling physical lines does not override their timestamp order.

`continue [NUMBER] [-p PROJECT] [-d DESCRIPTION] [-t TIME]` defaults NUMBER to 0, selects that recent pair, applies any field overrides, stops all currently running activities at the new activity's chosen start time, and appends the selected pair as a new running activity. Stop confirmations precede the normal start confirmation. Explicit `0` behaves like omission.

If there is no history, exit 1 with stderr `Error: No activity has been started before.\n`. With `K` distinct historical pairs, indexes `0` through `K-1` select them as described above. The boundary index `K` is also accepted and repeats the oldest pair (the same pair selected by `K-1`); for example, with one distinct pair, both `continue 0` and `continue 1` select it. Only a requested index greater than `K` exits 1 with `Error: Less than NUMBER distinct activities have been logged yet\n`. A negative positional is parsed as an unexpected flag and rejected by the CLI.

`last [-n NUMBER]` displays the newest N distinct pairs, with default 10. Invalid nonnumeric N prints `Can not parse "VALUE" as number. Argument for -n/--number is ignored\n`, then uses 10. N=0 or an empty history prints `No activities have been tracked yet\n`. If fewer than N exist, show all.

The displayed selected pairs are ordered oldest-to-newest, but their labels descend toward the latest: for pairs A, B, C in chronological order the rows are `[2] A`, `[1] B`, `[0] C`. Output is a table with columns ` # `, `Description`, `Project`, a leading blank line, underlined headers, and a trailing blank line. The index column does not wrap; Description and Project do. Its column sizing, wrapping, and padding use the scalar-count/display-width algorithm detailed for tables in Spec 12. In particular, an emoji counts as one Unicode scalar when choosing a natural width and when adding NBSP padding, even though the wrapping step treats it as a wide displayed character. A wide final emoji can therefore be moved to a continuation line, so the logical field is preserved across table lines but need not occur as one contiguous substring in stdout. For example, ignoring ANSI/padding:

```text

 #  Description Project
[2] Task A      ProjectA
[1] Task B      ProjectB
[0] Task C      ProjectC

```

## Spec 11

`list` and `report` share these filters:

- `-d/--date DATE`: activities whose start date equals DATE.
- `--from DATE`: start date on or after DATE.
- `--to DATE`: start date on or before DATE.
- `--today`: start date is today's local date.
- `--yesterday`: start date is yesterday.
- `--current_week`: start date is from Monday of the current week through today.
- `--last_week`: start date is from Monday through Sunday of the preceding week.
- `-p/--project PATTERN`: exact project match unless glob metacharacters are used; `*` matches zero or more characters and `?` one character. Project matching is case-sensitive and anchored to the entire project name.

The shortcut period flags are mutually exclusive (for example `--today --yesterday` is a CLI error containing `cannot be used with` and both option names). The single-date option `--date` is mutually exclusive with each range option, `--from` and `--to`, for both `list` and `report`. The two range bounds may be used together; otherwise-compatible filters combine by intersection. Date/range membership is determined from the activity's start date; an activity that started before midnight is not selected for the next day merely because it ends after midnight. Range boundaries are inclusive, either bound may be omitted, equal bounds select one day, and an inverted range returns an empty result.

Dates accept non-zero-padded month/day components and normalize logically. Invalid dates are ignored after printing:

```text
Can not parse "VALUE" as date. Argument for -d/--date is ignored (REASON)
```

The filters are applied before a list limit. `list -n N` selects the final N matching activities by file position, then displays those selected activities in original file order. N=0 is empty; an oversized N shows all. A nonnumeric N uses no limit after the same number-warning form described for `last`.

## Spec 12

`list [filters] [-n NUMBER] [--round DURATION] [--no_grouping]` prints every selected activity; it does not deduplicate. With no results, output exactly `No activity to display\n` and no header.

The normal table columns are `Started`, `Stopped`, `Description`, `Project`, `Duration`. Started, Stopped, and Duration do not wrap; Description and Project do. Headers are underlined with `ESC[4m...ESC[0m` separately around each header cell.

Table layout intentionally uses two different notions of width. Compute each column width as the largest count of Unicode scalar values (`char` values, not terminal display cells) among its heading and unwrapped cells. Then wrap every cell to that numeric width using Unicode display widths and Unicode line-break opportunities, breaking overlong words when necessary. Finally, pad each rendered fragment according to its Unicode-scalar count with NBSP, separate cells with one ASCII space, and leave one final ASCII space on every physical table line. This mismatch is observable: emoji and CJK characters count as one when column widths and padding are calculated but usually consume two units during wrapping, so they can wrap even when their scalar count fits the column. Wrapped continuation lines contain all-NBSP blank cells in columns with no corresponding fragment.

By default, activities are grouped by their start date. The output begins with `\n`, the header row, `\n\n`, then one bold `ESC[1mYYYY-MM-DD\tDAY_TOTALESC[0m` line per date and its rows, with a blank line between date groups and after the final group. Group rows show `HH:MM` starts. A same-day end is `HH:MM`; a cross-day end is full `YYYY-MM-DD HH:MM` and the row is yellow. Yellow is applied independently to every cell fragment as `ESC[33mCELL_WITH_NBSP_PADDINGESC[0m`; each one-ASCII-space separator and the final ASCII space are outside the colored spans. A running activity uses `-` as stopped text, uses its current elapsed duration, and applies green in the same per-cell manner with `ESC[32m`. Day totals sum displayed/rounded activity durations.

`--no_grouping` suppresses date headings and makes Started `YYYY-MM-DD HH:MM`. A single-day selector (`--date`, `--today`, or `--yesterday`) also suppresses date headings but shows only `HH:MM` in Started. In all ungrouped modes there is exactly one newline between the header and first row.

A normative five-row, single-date/no-grouping example is below. The visible alignment uses NBSP padding and ANSI underlines as just specified:

```text

Started Stopped Description        Project                Duration 
08:00   08:43   Urgent Task X      Important Project      43m      
08:51   10:13   Urgent Task X      Important Project      1h 22m   
10:13   10:35   More Urgent Task Y Just Another Project B 22m      
10:53   11:45   Simple Task Z      Less Important Project 52m      
11:45   12:34   Boring Task XY     Internal Project C     49m      

```

Zero duration is `<1m`. One minute is `01m`; exact hours include `00m`. Activities with identical times remain separate and retain file order.

## Spec 13

`report [filters] [--round DURATION]` aggregates selected durations first by exact project and then by exact description within that project. Running activities use now as their end. Projects and descriptions are case-sensitive, are not merged merely because names are similar, and are sorted lexicographically; repeated identical descriptions within one project are summed. The grand total sums project totals.

Rendering uses a common label width equal to the longest project name, four-space-indented description, or `Total`. Each label is extended with `.` to that width; if already exactly the width it gets no dot. A space follows, then the duration right-aligned to the maximum duration width. Project and Total lines are bold (`ESC[1m...ESC[0m`); description lines are not. Output starts with a blank line, has a blank line after every project block and after Total, and always includes Total. An empty result is:

```text

ESC[1mTotal <1mESC[0m

```

For this input:

```text
2021-10-29 08:00 - 2021-10-29 08:43 | Important Project | Urgent Task X
2021-10-29 08:51 - 2021-10-29 10:13 | Important Project | Urgent Task X
2021-10-29 10:13 - 2021-10-29 10:35 | Just Another Project B | More Urgent Task Y
```

the visible report (replace bold markers with ANSI) is:

```text

Important Project..... 2h 05m
    Urgent Task X..... 2h 05m

Just Another Project B    22m
    More Urgent Task Y    22m

Total................. 2h 27m

```

Date filtering is by start date, so a 23:00–01:00 activity starting the preceding day contributes nothing to a report for the end date. The implicit input normalization in Spec 4 occurs even without `--round`: 04:00:01–04:10:00 becomes 04:00–04:10 and contributes `10m`. Explicit rounding then affects those normalized per-activity endpoints before aggregation; with `--round 8h`, both endpoints in that example become 08:00 and contribute `<1m`.

## Spec 14

`projects [-c/--current] [-n/--no-quotes]` obtains exact unique project strings, sorts them in ascending case-sensitive Unicode lexicographic order, and writes one per line. By default every line is surrounded by an additional pair of literal double quotes; existing quote characters in a name are not escaped, so project text `"ProjectA"` displays as `""ProjectA""`. `--no-quotes` suppresses only the added outer pair. `--current` restricts the set to projects of running activities. Flags can be combined as `-cn`. Empty results produce no output.

For example, the distinct names `projecta`, `ProjectA`, `PROJECTA`, and `ProjectB` print:

```text
"PROJECTA"
"ProjectA"
"ProjectB"
"projecta"
```

## Spec 15

`search [SEARCH_TERM]` searches the same exact distinct `(description, project)` sequence used by `last`. Matching is case-insensitive and succeeds when either field matches. The term is treated as a glob embedded in `*...*`, so ordinary text is a substring search, `*` matches any sequence, and `?` matches one character. An explicitly supplied empty argument therefore matches everything. If the positional is omitted, its literal default is `''`, which normally matches nothing. More than one positional is a CLI error.

Search retains the global recent-task indexes and displays matching rows in descending index order (which is chronological among distinct pairs). For ten chronological pairs the first has index 9 and the newest index 0. A result table uses the same ` # `, `Description`, `Project` table and ANSI/NBSP formatting as `last`. No matches, including an empty file or omitted term, prints exactly:

```text
No matching activities found
```

Search must preserve quoted and Unicode content and handle at least 1000 activities and 500-character queries comfortably (the tested 1000-row search must finish in under one second).

## Spec 16

`current` selects only activities without end timestamps and preserves their physical file order; it does not sort them. With none, output exactly:

```text
No Activity is currently running
```

Otherwise it emits a table beginning with a blank line, with columns `Started At`, `Description`, `Project`, `Duration`. Started At is `YYYY-MM-DD HH:MM`, and Duration is now minus start. Headers, NBSP padding, wrapping, separators, and final spacing follow the list table rules. Completed activities never appear. A visible example is:

```text

Started At       Description Project  Duration 
2026-04-12 10:00 Task 1      ProjectA 5h 49m   
2026-04-12 11:00 Task 2      ProjectB 4h 49m   

```

## Spec 17

`status [-p PROJECT]` is a read-only summary. It has a NOW line followed by `Today`, `Current week`, and `Current month`. Without a filter its title says `Status for ALL projects`; with a filter it says `Status for project: PROJECT`. Project filtering is exact here. NOW shows only the first matching running activity in file order. In the all-project view it is `DESCRIPTION on PROJECT ...... DURATION`; in a project-filtered view it omits `on PROJECT`. If none matches, it says `NO Activity`.

Period totals select activities by start date and then sum each selected activity's entire duration; intervals are not clipped at period boundaries. Today selects starts on today's local date, Current week selects starts from Monday of the current week through today, and Current month selects starts from the first day of the current month through today. A running activity uses now as its end only after this start-date selection. Thus an activity started yesterday contributes nothing to Today even though it is still running after midnight, while it contributes its entire duration since yesterday's start to Current week and Current month when yesterday lies in those periods. An activity started 70 days ago is excluded from all three totals, leaving each displayed as `<1m`, even while NOW displays its full running duration. Apply the project filter to NOW and all totals. Multiple selected activities with the same project all contribute.

Ignoring ANSI, the exact empty-all-project layout is:

```text

 ======= Status for ALL projects  ======= 

  NOW:  NO Activity

  Today......................... <1m
  Current week.................. <1m
  Current month................. <1m

```

The output ends with that blank line. The exact visible filtered title line is ` ======= Status for project: NAME ======= `: there is exactly one ASCII space between the project value (including an empty value) and the opening `=` of the closing frame. Thus empty NAME produces ` ======= Status for project:  ======= `. This differs from the all-project line, which has two spaces between `projects` and the closing frame because its italic `projects ` fragment itself ends in a space. Dot counts keep the three period labels/durations aligned as shown. Actual output applies dim (`ESC[2m`), italic (`ESC[3m`), bold (`ESC[1m`), and green (`ESC[32m`) styling: the title frame and NOW punctuation are dim, prose is italic, the selected name and durations are bold, and the running description is bold green. ANSI reset sequences occur between styled fragments. Status does not mutate the file, and running `current` before or after it yields identical current output.

## Spec 18

`check` validates every physical line independently and always exits 0 when the file can be read, even when parse errors exist. An empty file succeeds with exactly:

```text
All lines in the file have been successfully parsed as activities.
```

The same success applies when every nonempty line is valid. A seconds value of `60` is valid under Spec 4 and is not reported as a parse error, although parsing it still emits the Spec 4 precision warning to stderr. Unlike ordinary display reads, blank physical lines within a nonempty file count as malformed. On errors, print:

```text
Found K line(s) with parsing errors

ORIGINAL INVALID LINE
  -> ERROR KIND (Line: N)

ORIGINAL INVALID LINE
  -> ERROR KIND (Line: N)
```

There is one blank line between entries and a final newline. For a blank line, the original-line portion is itself blank, producing the corresponding extra blank line. `ERROR KIND` is `could not parse activity` for a structurally unrecognizable line, and `could not parse date or time of activity` when timestamp-shaped content has an invalid date/time. Report every bad line in physical order using one-based line numbers; do not print valid lines. Empty descriptions, a timestamp plus project with omitted description, escaped pipes/backslashes, trailing whitespace, CRLF, long fields, special characters, and Unicode are valid.

Failure to read the file uses the file error from Spec 1 and exit 1.

## Spec 19

`sanity` operates on successfully parsed activities, sorts completed activities chronologically by start for analysis, and reports logical issues without changing the file. Merely being physically out of chronological order is valid. Running activities, including multiple running entries, are not errors. Zero-duration and exactly adjacent completed activities are valid.

For each completed activity whose end is before its start, print:

```text
Activity has negative duration
DESCRIPTION (Started: START, Ended: END, Line: N)

```

For every completed activity whose start is earlier than the end of an earlier chronological activity, print:

```text
Activity started before another activity ended
DESCRIPTION (Started: START, Ended: END, Line: N)

```

Equal start times overlap; a start exactly equal to the prior end does not. Report all overlaps rather than stopping at the first. Reports follow the chronological activity traversal rather than being grouped globally by issue class. For each activity, emit all applicable headings followed by one shared detail line and blank line; when that activity has both issues, `Activity has negative duration` precedes `Activity started before another activity ended`. Consequently, an overlap report for an earlier activity can precede both headings for a later negative-duration activity. `N` remains the original one-based file line. If there are no issues, output exactly `No unusual activities.\n`. Finding issues still exits 0.

## Spec 20

`edit [-e EDITOR]` invokes an external program directly, with the selected activity-file path as its one and only argument. The editor executable is selected from `-e`, otherwise from `EDITOR`; `-e` wins. Do not invoke a shell and do not split an editor value containing spaces into a command plus arguments. The child inherits stdin, stdout, and stderr so `-e cat` reproduces the file bytes on stdout and `-e echo` prints the selected path.

If neither editor source is set, exit 1 with `Error: editor command is missing\n`. Specifying `-e` more than once is a CLI error. Failure to spawn the executable exits 1 and reports the bare OS failure, for example `Error: No such file or directory (os error 2)\n`. An explicitly empty value, `edit -e ""`, deterministically produces that exact ENOENT message (not a permission-denied error). Once the child is successfully spawned, the parent command exits 0 even if the child itself reports a missing activity file or exits nonzero. The program must wait for the editor to finish, allowing it to modify the log in place, and must not pre-read, create, truncate, rewrite, chmod, or otherwise transform the file. Empty and large files, running-activity text, special characters, Unicode paths, and files in nonexistent directories are simply passed through to the editor.

Two `-e` occurrences specifically produce this stderr and exit 1:

```text
error: The argument '-e <editor>' was provided more than once, but cannot be used multiple times

USAGE:
    executable edit -e <editor>

For more information try --help
```

All log-processing commands must handle at least 5,000 activities within the command timeout; report aggregation should be linear or near-linear in the number of records.
