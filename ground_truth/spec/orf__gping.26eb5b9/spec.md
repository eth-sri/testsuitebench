# Clarified specification for `executable`

The required artifact is a single runnable program named exactly `executable`. It is a command-line, terminal-oriented latency grapher compatible with the behavior described below. All text is UTF-8. Unless a section explicitly says otherwise, successful informational invocations exit with status 0, command-line parsing errors exit nonzero (normally 2), ordinary runtime errors exit with status 1, diagnostics go to standard error, and interactive display output goes to the controlling terminal.

## Spec 1

When invoked under its required name, `executable --help` must exit 0, write nothing to standard error, and write exactly the following text to standard output, including indentation, blank lines, trailing spaces on the blank description line below `--simple-graphics`, and the final newline. The program name in the `Usage:` line is the basename used to invoke the program. In particular, invoking a symlink named `renamed-program` changes only that line to `Usage: renamed-program [OPTIONS] [HOSTS_OR_COMMANDS]...`; it does not force the name `executable`. `-h` produces the same help behavior.

```text
Ping, but with a graph.

Usage: executable [OPTIONS] [HOSTS_OR_COMMANDS]...

Arguments:
  [HOSTS_OR_COMMANDS]...  Hosts or IPs to ping, or commands to run if --cmd is provided. Can use cloud shorthands like aws:eu-west-1

Options:
      --cmd
          Graph the execution time for a list of commands rather than pinging hosts
  -n, --watch-interval <WATCH_INTERVAL>
          Watch interval seconds (provide partial seconds like '0.5'). Default for ping is 0.2, default for cmd is 0.5
  -b, --buffer <BUFFER>
          Determines the number of seconds to display in the graph [default: 30]
  -4
          Resolve ping targets to IPv4 address
  -6
          Resolve ping targets to IPv6 address
  -i, --interface <INTERFACE>
          Interface to use when pinging
  -s, --simple-graphics
          
      --vertical-margin <VERTICAL_MARGIN>
          Vertical margin around the graph (top and bottom) [default: 1]
      --horizontal-margin <HORIZONTAL_MARGIN>
          Horizontal margin around the graph (left and right) [default: 0]
  -c, --color <color>
          Assign color to a graph entry.
          
          This option can be defined more than once as a comma separated string, and the
          order which the colors are provided will be matched against the hosts or
          commands passed to gping.
          
          Hexadecimal RGB color codes are accepted in the form of '#RRGGBB' or the
          following color names: 'black', 'red', 'green', 'yellow', 'blue', 'magenta',
          'cyan', 'gray', 'dark-gray', 'light-red', 'light-green', 'light-yellow',
          'light-blue', 'light-magenta', 'light-cyan', and 'white'
      --clear
          Clear the graph from the terminal after closing the program
      --ping-args [<PING_ARGS>...]
          Extra arguments to pass to `ping`. These are platform dependent
  -h, --help
          Print help
  -V, --version
          Print version
```

## Spec 2

`--version` and `-V` are distinct immediate actions. Both exit 0 and write nothing to standard error. The short `-V` form writes exactly one newline-terminated line:

```text
gping 1.20.1
```

The long `--version` form writes exactly these four newline-terminated lines:

```text
gping 1.20.1
commit_hash: d67d2aeb
build_time: 2026-04-17 19:59:37 +00:00
build_env: rustc 1.92.0 (ded5c06cf 2025-12-08),1.92.0-x86_64-unknown-linux-gnu
```

The long form's essential format is a semantic version after `gping `, followed in order by nonempty `commit_hash: `, `build_time: `, and `build_env: ` fields. The short form does not include those three metadata fields.

## Spec 3

The general syntax is `executable [OPTIONS] [HOSTS_OR_COMMANDS]...`. Options may occur before, between, or after positional values. The recognized forms are exactly those documented in the help: `--cmd`; `-n`/`--watch-interval`; `-b`/`--buffer`; `-4`; `-6`; `-i`/`--interface`; `-s`/`--simple-graphics`; `--vertical-margin`; `--horizontal-margin`; `-c`/`--color`; `--clear`; `--ping-args`; `-h`/`--help`; and `-V`/`--version`. Long value options accept both `--option value` and `--option=value`; short value options accept a following value and an attached equals form such as `-n=-1`.

`--` ends option processing. Every later token is positional even if it starts with `-`; for example `-- -n 0.2 a` enters host mode and first attempts to resolve the literal host `-n`. A lone `-` is also a positional hostname. Before `--`, short options may be clustered: `-46` is parsed as both `-4` and `-6`, and a token beginning with `-h` triggers help at that point.

## Spec 4

At least one positional host or command is required after option parsing. This check applies both in ping mode and with `--cmd`. On failure, exit 1 and emit exactly this newline-terminated standard-error text, with no usage block:

```text
Error: At least one host or command must be given (i.e gping google.com). Use --help for a full list of arguments.
```

`--ping-args` accepts zero or more values and greedily consumes all remaining command-line tokens as ping arguments. Thus `executable --ping-args localhost`, as well as an invocation containing options but no positional target, fails with the message above.

## Spec 5

Argument parsing is left-to-right and help/version are immediate actions. `--help` followed by an otherwise-invalid token succeeds and prints normal help because help was encountered first. An unknown option before `--help` remains an error. For example, `--invalid --help` fails, while `--help --invalid` succeeds. Unknown options produce a nonzero exit and a clap-style standard-error diagnostic containing `error: unexpected argument '<TOKEN>' found`, a `Usage:` line, and `For more information, try '--help'.`

If a separated option value begins with `-`, it is normally parsed as another option, not as that option's value. For example `-n -1 a` and `--buffer -1 a` report:

```text
error: unexpected argument '-1' found

  tip: to pass '-1' as a value, use '-- -1'

Usage: executable [OPTIONS] [HOSTS_OR_COMMANDS]...

For more information, try '--help'.
```

Options that take a required value report `a value is required for '<canonical option and metavar>'` when it is absent. Giving `--simple-graphics=1` reports `unexpected value '1' for '--simple-graphics'`.

## Spec 6

`WATCH_INTERVAL` is parsed as a floating-point number of seconds. Its defaults are 0.2 in ping mode and 0.5 in command mode. Zero, very small positive values, ordinary fractional values, integers, and attached negative forms such as `-n=-1` pass syntactic parsing; a separated negative form is subject to Spec 5. Repeating `--watch-interval`/`-n` is an error containing `cannot be used multiple times`. Invalid float diagnostics use these exact forms:

```text
error: invalid value 'abc' for '--watch-interval <WATCH_INTERVAL>': invalid float literal

For more information, try '--help'.
```

For an empty value, replace the reason with `cannot parse float from empty string`. The displayed bad value must reflect the input.

## Spec 7

`BUFFER` is parsed as an unsigned 64-bit integer number of seconds with default 30. Values 0 and 1 and other in-range unsigned integers pass command-line parsing; later conversion of the maximum value during TUI startup behaves as specified in Spec 20. Non-numeric, empty, signed-negative attached, and overflowing values fail parsing. Diagnostics follow these exact examples:

```text
error: invalid value 'abc' for '--buffer <BUFFER>': invalid digit found in string

For more information, try '--help'.
```

```text
error: invalid value '' for '--buffer <BUFFER>': cannot parse integer from empty string

For more information, try '--help'.
```

```text
error: invalid value '999999999999999999999999999' for '--buffer <BUFFER>': number too large to fit in target type

For more information, try '--help'.
```

An attached `--buffer=-1` uses reason `invalid digit found in string`; a separated `-1` is handled as in Spec 5.

## Spec 8

Both margins are unsigned 16-bit integers in the inclusive range 0 through 65535. Defaults are vertical 1 and horizontal 0. Non-numeric input uses `invalid digit found in string`. Out-of-range input uses `<VALUE> is not in 0..=65535`. For example:

```text
error: invalid value '-1' for '--vertical-margin <VERTICAL_MARGIN>': -1 is not in 0..=65535

For more information, try '--help'.
```

The corresponding option name and metavar must be used for horizontal-margin errors. Values `65536` and `999999` are rejected with the same range wording. These are parse-time type bounds; smaller margins are allowed even when the current noninteractive terminal could not display a graph of that size.

## Spec 9

`-4` and `-6` are mutually exclusive. Supplying both, in either order or clustered, fails before host resolution. For `-4 -6`, standard error is exactly:

```text
error: the argument '-4' cannot be used with '-6'

Usage: executable -4 <HOSTS_OR_COMMANDS>...

For more information, try '--help'.
```

`--cmd` is also mutually exclusive with the presence of `--ping-args`. With `--cmd` encountered first, the exact diagnostic is:

```text
error: the argument '--cmd' cannot be used with '--ping-args [<PING_ARGS>...]'

Usage: executable --cmd <HOSTS_OR_COMMANDS>...

For more information, try '--help'.
```

Repeating the single-action `--cmd` flag fails with `the argument '--cmd' cannot be used multiple times`.

## Spec 10

`-c`/`--color` is repeatable. Each occurrence is split only on commas, and the resulting values are concatenated in command-line order. Leading and trailing whitespace around a recognized nonempty color is trimmed, so `--color= red`, `--color=red `, and `--color= red ` all select red. Empty comma components that follow a valid value are skipped: `red,,blue` selects red and blue, and `red,` selects red. In contrast, an entirely empty value, a whitespace-only value, or a leading empty component such as `,red` is invalid.

Color names are ASCII case-insensitive. The accepted names are `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `gray`, `dark-gray`, `light-red`, `light-green`, `light-yellow`, `light-blue`, `light-magenta`, `light-cyan`, and `white`. After surrounding whitespace is trimmed, a custom color is exactly `#` followed by six hexadecimal digits; hexadecimal letter case is irrelevant. Thus `#000000`, `#FFFFFF`, `#ff0000`, and `#AbCdEf` are valid, while `FF0000`, `#FF`, `#12345`, `#GGGGGG`, whitespace-only values, wholly empty values, leading empty comma components, and semicolon-separated strings are invalid.

Validate the retained entries in order and stop at the first invalid entry. On failure, exit 1 and emit exactly this template, including backticks, blank line, indentation, and final newline:

```text
Error: Invalid color code: `<BAD_VALUE>`

Caused by:
    Failed to parse Colors
```

For example, `red;blue` is one invalid value, and `invalid1,invalid2` reports only `invalid1`. More colors than graph entries are harmless. If fewer colors than entries are supplied, remaining entries still receive usable colors; the program must not reject the invocation.

## Spec 11

In ping mode, expand recognized lowercase cloud shorthands before DNS resolution while preserving the original positional order:

- `aws:REGION` becomes `ec2.REGION.amazonaws.com`.
- `gcp:REGION` becomes `storage.REGION.rep.googleapis.com`.
- The special empty shorthand `gcp:` becomes `cloud.google.com`.

`REGION` is not restricted to a predefined list. Split only after the provider prefix: `aws:us-east-1:8080` consequently becomes the invalid hostname `ec2.us-east-1:8080.amazonaws.com`. Provider recognition is case-sensitive. Unrecognized providers, uppercase forms such as `AWS:us-east-1`, missing providers such as `:us-east-1`, and strings without a colon such as `awsregion` remain literal hostnames and go through ordinary resolution. Multiple shortcuts and ordinary targets can be mixed and must retain their input order in the display.

## Spec 12

Ping targets may be DNS names, IPv4 addresses, or IPv6 addresses. Convert each non-ASCII DNS name to its ASCII IDNA/punycode representation before resolving and use that converted name in errors and display. In particular, `тест.example.com` becomes `xn--e1aybc.example.com`, and `日本語ホスト名.test` becomes `xn--zck4a3ct33sqwscyb2w6i.test`. Preserve valid trailing dots, underscores, spaces, colons, and other unusual characters through to the resolver rather than silently rewriting them.

Resolve targets one at a time in input order and fail immediately on the first resolution failure. `-4` filters DNS results to IPv4; `-6` filters them to IPv6. A literal or resolved address of the wrong family fails exactly as `Error: Could not resolve '<TARGET>' to IPv4\n` or `Error: Could not resolve '<TARGET>' to IPv6\n`. Valid numeric addresses do not require DNS. In the TUI, labels have the form `original-or-expanded-name (resolved-address)`; examples are `127.0.0.1 (127.0.0.1)`, `::1 (::1)`, and with `-4`, `localhost (127.0.0.1)`.

## Spec 13

Ordinary resolution failures exit 1 and use this exact standard-error structure, with a final newline:

```text
Error: Resolving <TARGET>

Caused by:
    failed to lookup address information: Name or service not known
```

`<TARGET>` is the post-cloud-expansion and post-IDNA string. This applies to empty strings, malformed numeric-looking addresses, strings containing spaces or punctuation, `...`, a lone `-`, invalid providers, and arbitrarily long names; do not crash or truncate the error. On the GNU/Linux resolver used for evaluation, `xn--e1aybc.example.com` and `test_host.example.com` instead end with `No address associated with hostname`. Failing on a first target such as `host1.invalid` must not mention or resolve later targets.

## Spec 14

Ping mode uses the `ping` programs available through `PATH`; these are supplied by the execution environment and are not part of the artifact. Before monitoring, detect the implementation using its version output. Recognize iputils output such as `ping from iputils ...` or `ping utility, iputils-...`, including output on standard output, and BusyBox output such as `BusyBox v...`, including when it is written to standard error. If the version output contains GNU inetutils, fail nonzero with text containing both `Installed ping is not supported` and `Please use iputils ping, not inetutils`. If it matches no supported implementation, fail nonzero with `Could not detect ping` and include the captured version text.

For iputils, invoke continuous ping with timeout-reporting enabled and pass the configured interval in compact form `-i<SECONDS>`; `-n 0.5` must result in an argument exactly `-i0.5`. `-i`/`--interface` supplies the requested network interface to ping. Every token captured by `--ping-args` is forwarded as an additional ping argument. Use the IPv6-capable `ping6` executable when an IPv6 target requires that platform convention. Start one independent ping process per target.

## Spec 15

Parse the continuous output of supported ping variants line by line. A successful response is any normal data-reply line containing `time=<NUMBER> ms`, including iputils/macOS/BSD/Android forms with `icmp_seq=`, BusyBox forms with `seq=`, hostnames in the reply, and integral or fractional millisecond values. Preserve sufficient fractional precision that extrema such as 14.621, 33.898, 111.525, 110.395, 21.308, 15.769, 19.236, and 19.319 can appear in the displayed statistics.

Recognize `no answer yet for icmp_seq=...` and `Request timeout for icmp_seq ...` as timeout samples. Header/banner lines, summary/statistics lines, `sendto: Network unreachable`, `Host is down`, and `No route to host` do not create latency values and do not terminate monitoring. Successful and timeout events may be interleaved; successful data continues to graph and timeout events accumulate in the `t/o` statistic.

## Spec 16

With `--cmd`, each positional argument is one complete command specification, not one word of a shared command. Split that string on whitespace; use the first token as the executable name and the remaining tokens as its direct argument vector. Do not invoke a shell. Quotation marks have no grouping role, and shell builtins, pipes, redirections, semicolons, and environment-variable expansions are not interpreted. Redirection tokens remain ordinary arguments and do not create the named files; `:` and `exit` are looked up as executable names rather than treated as shell builtins.

Monitor all specified commands independently and concurrently, rerunning each at the configured interval. Measure elapsed wall-clock execution time only for commands that exit successfully; their stdout/stderr content is not the measured value. Failure to spawn a named executable does not immediately terminate the program or print a diagnostic. The full-screen TUI remains active for more than five seconds, showing that command's label and a zero-duration graph such as `0ns`, rather than exiting on the spawn failure. This applies both to an ordinary absent executable such as `definitely-no-such-executable-987654` and to a shell builtin such as `:` that has no corresponding executable.

After lowercase `q` requests shutdown in either of those spawn-failure cases, the terminal is restored, the process exits with status 1, and its output ends with this newline-terminated diagnostic:

```text
Error: No such file or directory (os error 2)
```

A spawned command that exits nonzero produces neither a duration sample nor a timeout sample; it does not stop other commands or the TUI. Thus repeatedly running `false` leaves that entry without `t/o` statistics rather than incrementing a timeout count. A command that succeeds with no output is still a successful timed sample. Very fast commands remain graphable. The full command specification string is used as its display label, subject only to clipping at the terminal boundary.

## Spec 17

`--cmd ""` has a deliberate legacy panic behavior. It exits with status 101 and emits a Rust-style panic to standard error beginning with a blank line and containing exactly these stable lines (the numeric thread id may vary):

```text
thread 'main' (<PID>) panicked at gping/src/main.rs:<error location>:
Must specify a command to watch
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

An empty command is distinct from omitting commands entirely, which uses Spec 4.

## Spec 18

Normal ping and command monitoring require a controlling terminal. When invoked through ordinary captured pipes without a TTY, parsing, color validation, cloud expansion, and DNS resolution happen first; if those stages succeed, terminal initialization may fail. The expected Linux no-TTY diagnostic is exactly `Error: No such device or address (os error 6)\n`, with exit status 1. If spawning a required external `ping` program fails because it is absent, report:

```text
Error: Error spawning ping: No such file or directory (os error 2)

Caused by:
    No such file or directory (os error 2)
```

Do not turn a successful parse followed by one of these runtime errors into a command-line usage error.

## Spec 19

When attached to a sufficiently large pseudo-terminal, enter an updating full-screen text UI. It must begin rendering promptly and remain active until a shutdown condition described in Spec 22. The display contains, for each target or command and in input order, a legend/header that includes its label. Once an entry has successful samples, it includes compact statistics labeled `last`, `min`, `max`, `avg`, `jtr`, `p95`, and `t/o`; successful commands show a zero timeout count as `t/o 0`. A command entry with no successful samples, such as one repeatedly executing `false`, instead shows zero-duration text such as `0ns` and does not display the statistic labels or a `t/o` counter. Multiple entries each have their own visible header. The UI must comfortably support at least four entries.

Below the headers, render a duration graph with a visible vertical axis `│`, lower-left corner `└`, a horizontal axis, duration labels using suitable `ns`, `µs`, or `ms` units, and an x-axis with at least two current-time labels in `HH:MM:SS` form. New ping replies or command results add plotted data and update statistics. For default graphics, actual plotted data uses Unicode Braille characters from U+2800 through U+28FF.

## Spec 20

The buffer controls the graph's displayed time window, not the sampling interval. The difference between the first and last whole-second `HH:MM:SS` labels must approximately match the buffer: 5 seconds gives 4–6 seconds, 10 gives 8–12 seconds, and 60 gives 58–62 seconds, including correct handling across midnight. Buffer 1 still renders at least two time labels and a graph.

The maximum syntactically valid buffer, `--buffer=18446744073709551615`, passes command-line parsing but panics during startup before rendering. It exits with status 101 and emits a Rust panic beginning with a blank line and containing these stable lines (the numeric thread id may vary):

```text
thread 'main' (<PID>) panicked at gping/src/main.rs:138:87:
called `Result::unwrap()` on an `Err` value: OutOfRangeError(())
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

The watch interval controls sampling. In command mode, values such as 0.1 and 2.0 seconds must remain responsive and produce a valid graph. In ping mode it is also passed to ping as specified in Spec 14.

## Spec 21

`--simple-graphics` changes plotted data from Braille to the bullet `•`. A simple-graphics screen must contain `•` after samples arrive and must contain no Braille plot characters, while retaining the normal axes, headers, multiple-entry support, and statistics.

`--vertical-margin N` leaves at least N completely blank terminal rows before rendered content and an analogous bottom margin. With zero, the first content appears on row 0 or 1. `--horizontal-margin N` indents rendered content by N spaces on content lines. Both margins compose. In a normal 120-by-40 test terminal, values such as vertical 2 or 3 and horizontal 1, 3, or 5 must visibly take effect without suppressing the graph.

## Spec 22

Colors are assigned to entry lines in the flattened order from Spec 10. Explicit colors apply to the corresponding hosts or commands; defaults fill unspecified entries and cycle as necessary. Terminal color escape sequences may be stripped by screen capture, so color use must not alter the required visible labels or graph structure.

While command samples or ping output continue to arrive, any of lowercase `q`, the Escape key, or Ctrl-C cleanly terminates monitoring and restores terminal mode. A live ping child that emits an initial finite burst and then remains silent exposes a polling limitation: lowercase `q` is not acted on while the child produces no further output, and the process remains alive for more than three seconds after the key is sent. This is distinct from a continuously producing ping child, for which lowercase `q` terminates cleanly.

`--clear` additionally clears the graph from the terminal on shutdown. Successful termination must stop child ping processes and command-monitoring activity rather than leaving them running.
