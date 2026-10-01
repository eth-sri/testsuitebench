# Specification for `executable`

## Spec 1

The delivered artifact is one executable file named exactly `executable`. It is a POSIX command-line benchmarking program compatible with the behavior described below. It accepts options before, after, or between positional benchmark command strings. Each positional argument is one complete benchmark command; multiple positional arguments therefore create multiple benchmarks. Unless a specified error occurs, a successful invocation exits with status 0. Validation, spawn, hook, and non-ignored benchmark failures exit nonzero. Normal benchmark reports go to standard output. Deliberately inherited child output retains its stream: child stdout goes to standard output and child stderr goes to standard error. Diagnostics, errors, and warnings go to standard error.

`executable --version` must exit 0 and print a line containing both `hyperfine` and `1.20.0` (the canonical line is `hyperfine 1.20.0`). Both `--option value` and `--option=value` forms must work where an option takes a value. The short aliases required below must also work.

The execution environment supplies ordinary POSIX programs used as benchmark commands, including `/bin/sh`, `bash`, `echo`, `printf`, `true`, `false`, `sleep`, `cat`, `wc`, `tr`, `tee`, and `python3`. Their behavior is harness-provided; the executable's responsibility is to invoke and measure them correctly.

## Spec 2

The run-count controls are:

- `-r NUM` / `--runs NUM`: perform exactly `NUM` measured runs of every expanded benchmark. Counts of 1, 2, 3, 5, 10, 20, and 100 must be supported. This option overrides automatic count selection rather than merely suggesting a count.
- `--min-runs NUM` and `--max-runs NUM`: bounds on automatic selection. The reported and performed count must be at least the supplied minimum and at most the supplied maximum. Either bound may appear alone; a maximum below the normal default still acts as a cap. When both are present, the count lies in the inclusive interval.
- `--min-benchmarking-time SECONDS`: supplies the target duration used by automatic count selection and must parse as a floating-point number.
- With none of these options, automatically choose repeated runs, normally at least 10 and enough to target approximately three seconds of benchmarking. Account for measured shell-launch overhead when estimating a fast command's run count.

`--runs` is mutually exclusive with each of `--min-runs` and `--max-runs`; a conflict is a nonzero error containing `cannot be used with`. If the minimum exceeds the maximum, emit exactly:

```text
Error: Conflicting requirements for the number of runs (empty range, min is larger than max)
```

Invalid numeric values use the errors in Spec 21. The actual number of measured runs—not warmups—must be shown in the text report and determine the lengths of per-run export arrays.

## Spec 3

`-w NUM` / `--warmup NUM` performs exactly `NUM` warmup invocations for every expanded benchmark before its measured invocations. `--warmup=0` means no warmup and must not select a default. Warmups really execute the command and any per-invocation hooks, and their output is visible when command output is inherited, but warmup durations, exit codes, and memory observations are excluded from reported statistics and exported per-run arrays. Enabling warmups does not add a warmup-status or warmup-completion line to the normal report; its semantic report structure remains the one in Spec 4. Thus `--warmup=2 --runs=3` performs five command invocations but reports `3 runs` and exports three observations.

The executable must measure real elapsed wall-clock time for ordinary invocations. It must also collect child-process user CPU time and system CPU time separately. Waiting commands such as `sleep 0.05` must have a wall mean of at least about 0.045 seconds while user plus system CPU time remains below half of the wall mean. A CPU-bound `python3 -c 'sum(range(100000))'` must report positive user CPU time. Per measured run, record the process's peak memory usage in bytes; for that Python command at least one of three samples must exceed 1,000,000 bytes.

When an intermediate shell is used, measure its empty-command startup overhead and subtract that overhead from measured wall times, clamping negative corrected values to zero. Direct-execution mode is not shell-corrected. Statistical values must be derived from the actual measured observations: mean, median, minimum, maximum, and nonnegative standard deviation, plus average user and system CPU times.

## Spec 4

For a normal, undecorated benchmark, standard output uses this semantic layout (spacing may align columns, but the shown labels and Unicode symbols are required):

```text
Benchmark 1: COMMAND-OR-NAME
  Time (mean ± σ):     MEAN UNIT ± STDDEV UNIT    [User: USER UNIT, System: SYSTEM UNIT]
  Range (min … max):   MIN UNIT … MAX UNIT    N runs
```

There is one sequentially numbered `Benchmark N:` section for every expanded benchmark, in execution order. For two or more measured runs, both `Time (mean ± σ):` and `Range (min … max):` appear, the latter ends in the exact count such as `3 runs`, and the same benchmark's user/system figures appear in square brackets. Long command strings (at least 10,000 characters) must execute without truncation; the report must retain at least their recognizable leading command text.

For exactly one measured run, instead print a decimal-valued line beginning `Time (abs ≡):`, followed by `[User: ..., System: ...]`. Do not print a range line or `Time (mean ± σ):` for that benchmark. Command text in headers and exports preserves the user's exact quotes and backslashes, for example `echo "hello world"` and `echo "line1\nline2"` remain exactly those strings.

Immediately after each benchmark section's final result line, print a separator line consisting of exactly one ASCII space followed by a newline. This separator therefore appears before the next benchmark heading or summary and also after a lone benchmark. A single benchmark has no `Summary`, no `Relative speed comparison`, and no `times faster than` text.

## Spec 5

`--time-unit UNIT` controls human-readable console and table-export units. The only values are `microsecond`, `millisecond`, and `second`, rendered as `µs`, `ms`, and `s`, respectively. All main, deviation, range, user, and system values in a report use the selected unit and the correct conversion from seconds. For `sleep 0.01`, microseconds must be well above 100, milliseconds at least 0.1, and seconds positive. Human-readable seconds use enough decimal precision to display a short sleep as a positive value (normally three decimals); microseconds and milliseconds normally use one decimal.

Without the option, choose an appropriate common display unit from the measured magnitudes: fast operations use `µs` or `ms`, approximately 10 ms sleeps use `ms`, and long durations may use `s`. Markdown, AsciiDoc, and Org tables use this selected or automatically chosen unit in all three timing headers. CSV and JSON ignore this display choice and always store seconds.

## Spec 6

Commands use an intermediate shell by default, equivalent on this POSIX target to `/bin/sh -c COMMAND`. Consequently pipelines, redirects, semicolons, `&&`, command substitution, quoting, and environment-variable expansion retain ordinary shell semantics. A command such as `echo test | tr a-z A-Z | cat` is one benchmark, not several; quoted semicolons remain quoted. The original command string—not a reconstructed representation—is used in headings and exports.

`-S SHELL` / `--shell SHELL` selects another intermediate shell. Parse the `SHELL` expression with shell-like quote handling into an executable and its arguments, so `--shell='bash --norc'` invokes bash with `--norc` and then the shell's command-execution option and benchmark text. An explicitly selected `/bin/sh` and bash must execute successfully.

`-N` and `--shell=none` select direct execution. Each positional command string is independently shell-word-split into an argv vector, respecting quotes, and launched without a shell. Thus `echo 'hello world' argument2` prints `hello world argument2`; `$HOME`, `&&`, `|`, and similar tokens are not expanded or interpreted. For example, `echo test1 && echo test2` invokes one `echo` process with literal arguments. Separate positional strings such as `echo` and `printf test` remain two independently benchmarked commands. A direct spawn of an absent program emits `Error: Failed to run command 'COMMAND':` followed by the operating-system cause and exits nonzero.

An empty shell setting emits exactly `Error: An empty command has been specified for the '--shell <command>' option`. An unmatched quote in a shell expression emits exactly `Error: Failed to parse '--shell <command>' expression as command line: missing closing quote`. Failure to launch `/nonexistent/shell` emits exactly `Error: Could not measure shell execution time. Make sure you can run '/nonexistent/shell -c ""'.`

## Spec 7

`-L NAME VALUES` / `--parameter-list NAME VALUES` declares a string parameter. Split `VALUES` on unescaped commas. `\,` denotes a literal comma and loses the escaping backslash. Other backslashes are retained, including a trailing backslash. Empty components are valid: an empty whole value produces one empty string; `a,b,` produces `a`, `b`, and empty; `,x,y` produces empty, `x`, and `y`. Preserve spaces, Unicode, `$`, semicolons, braces, and all other characters as literal parameter data. Lists of at least 20 values are supported.

`-P NAME MIN MAX` / `--parameter-scan NAME MIN MAX` declares one inclusive ascending numeric range. Integer bounds default to exact step 1. `-D DELTA` / `--parameter-step-size DELTA` supplies the scan step. Generate `MIN + k*DELTA` while it is at most `MAX`; a step larger than the span therefore produces only `MIN`, and equal bounds produce exactly one value. Negative bounds are valid. Decimal arithmetic must be exact decimal arithmetic without binary accumulation errors: `0.1..0.3 step 0.1` is `0.1,0.2,0.3`; `0.0..1.0 step 0.33` is `0.0,0.33,0.66,0.99`; `0.5..1.5 step 0.5` preserves `1.0` formatting. Preserve a sufficient fixed decimal scale based on the inputs.

A decimal bound requires an explicit step, otherwise emit exactly:

```text
Error: A step size is required when the range bounds are floating point numbers. The step size can be specified with the '-D/--parameter-step-size <DELTA>' parameter
```

A reversed range emits `Error: Empty parameter range`; a zero step (including `0.0`) emits `Error: Zero is not a valid parameter step`. Reject a range containing more than 100,000 values with `Error: Parameter range is too large`, while ranges of at most 100,000 are valid. Malformed bounds produce `Error: Error while parsing parameter scan arguments (...)`; specifically `1.5.5` produces exactly `Error: Error while parsing parameter scan arguments (Invalid decimal: two decimal points)`, and nonnumeric input includes `Invalid decimal`.

Parameter scans and parameter lists cannot be mixed in one invocation; this is a nonzero option-conflict error containing `cannot be used with`. Multiple declarations of the same supported kind are allowed, but repeated names are rejected with exactly `Error: Duplicate parameter names: x` (using the duplicate name or names).

## Spec 8

For every parameter assignment, substitute every `{NAME}` occurrence in benchmark commands, custom names, and lifecycle hook strings. Substitution is simultaneous and non-recursive: replacement text is never scanned again. For `foo=[a,{bar}]`, `bar=[baz,quux]`, and `echo {foo} {bar}`, the exact expanded commands are:

```text
echo a baz
echo {bar} baz
echo a quux
echo {bar} quux
```

Unknown placeholders with no declaration remain literal, so `echo {undefined_param}` is valid and is displayed unchanged. Declared values may occur in the executable-name position and all repeated occurrences are replaced. The resulting text is then interpreted according to the selected shell mode; quoting already present in the command remains effective, so `echo 'arg:{val}'` with values `test;whoami` and `$HOME` prints those literal values rather than executing or expanding them.

Expansion is the Cartesian product. The first declared parameter varies fastest and the last declared parameter slowest. With `x=1,2` then `y=a,b`, order is `(1,a),(2,a),(1,b),(2,b)`. Within each complete assignment, positional command templates vary fastest: two templates and `n=1,2` produce `template1(n=1), template2(n=1), template1(n=2), template2(n=2)`. Three two-value parameters therefore produce eight benchmarks in analogous order.

If a declared parameter is unused by the displayed command or custom-name template, append it to the benchmark display as ` (NAME = VALUE)`; e.g. `echo test (x = 1)`. JSON/CSV still contain its parameter value. With `--show-output`, output from both warmup and measured runs is printed; thus one warmup plus one measured `echo` displays the echoed value twice below its header.

## Spec 9

`-n NAME` / `--command-name NAME` changes the display/export name while leaving the actual command executed unchanged. Names preserve spaces, punctuation, Unicode, and parameter substitution. In an unparameterized invocation, supplied names map to the first commands in order; it is valid to name only a prefix and leave later commands displayed by their raw strings. Supplying more names than commands is invalid. Thus debug-mode commands `sleep 1.0`, `sleep 1.0`, `sleep 2.0`, `sleep 1000.0` may receive only the prefix names `A`, `B`, with the final two retaining their raw names.

For a parameterized invocation, a single supplied name is a substitutable template shared across that command's expansions; alternatively, provide exactly one name per fully expanded benchmark. An intermediate count is invalid. For one scan/template producing three benchmarks, two names fail exactly with:

```text
Error: '--command-name' has been specified 2 times. It has to appear exactly once, or exactly 3 times (number of benchmarks)
```

For one unexpanded command, two names fail exactly with `Error: Too many --command-name options: Expected 1 at most`. Wherever a custom name is assigned, it replaces the raw command string in benchmark headings, comparison sections, and the corresponding export `command` field.

`--reference COMMAND` prepends one additional benchmark ahead of all ordinary positional commands, even when identical text also appears among the ordinary commands; duplicates are not coalesced. It receives the same runs, warmups, I/O policy, hooks, parameter processing, timing, and exporting as any other benchmark. In a run with a reference and two commands, headings are numbered reference=1, first command=2, second command=3. `--reference-name NAME` changes only the reference's displayed/exported name and supports parameter substitution.

## Spec 10

The four lifecycle options are `--setup COMMAND`, `--prepare COMMAND`, `--conclude COMMAND`, and `--cleanup COMMAND`. For each expanded benchmark independently, execute this order:

```text
setup once
for each warmup: prepare, benchmark, conclude
for each measured run: prepare, benchmark, conclude
cleanup once
```

Then proceed to the next benchmark and repeat the entire lifecycle. Each hook is independently optional. Hook commands always support the same shell syntax as normal shell commands and receive parameter substitution. A hook can create or modify files for later hooks or the benchmark. A single occurrence of a hook option applies globally to all benchmarks. When a repeatable per-benchmark option such as `--prepare` or `--conclude` appears more than once, it must appear exactly once per expanded benchmark and map in benchmark order. The same one-or-N cardinality rule applies to repeated `--output`. A mismatch for three benchmarks emits exactly, substituting the option name:

```text
Error: The '--prepare' option has to be provided just once or N times, where N=3 is the number of benchmark commands (including a potential reference).
```

The corresponding forms use `--conclude` and `--output` in place of `--prepare`.

Hook output follows the normal suppressed command-output policy unless redirected by the hook itself. Setup and cleanup counts are once per expanded benchmark regardless of measured-run count. Prepare and conclude counts equal `(warmups + measured runs)` per expanded benchmark.

## Spec 11

Lifecycle hook failures are fatal and stop immediately. Do not run the remaining benchmark or later hooks, including cleanup, after setup, prepare, or conclude fails. A cleanup failure occurs only after the benchmark's runs have completed but still makes the invocation fail. Emit one of these exact messages to standard error:

```text
Error: The setup command terminated with a non-zero exit code. Append ' || true' to the command if you are sure that this can be ignored.
Error: The preparation command terminated with a non-zero exit code. Append ' || true' to the command if you are sure that this can be ignored.
Error: The conclusion command terminated with a non-zero exit code. Append ' || true' to the command if you are sure that this can be ignored.
Error: The cleanup command terminated with a non-zero exit code. Append ' || true' to the command if you are sure that this can be ignored.
```

The affected benchmark heading is printed before attempting its setup. For example, if setup fails, only setup has changed external state; prepare, benchmark, and cleanup have not run. If conclude fails on the first run, setup, first prepare, first benchmark, and first conclude have run, but no second cycle or cleanup has run. If cleanup fails after two runs, both complete run cycles precede the cleanup action.

## Spec 12

Benchmark stdin defaults to a null/empty stream so readers immediately see EOF. `--input=null` explicitly selects the same behavior. `--input PATH` opens the given file as stdin for every warmup and measured run and rewinds/reopens it for each invocation. It must work in shell and direct modes. An absent path is rejected before benchmarking with `Error: The file 'PATH' specified as '--input' does not exist`.

The default benchmark stdout/stderr policy suppresses command output. `--show-output` selects the `--output=inherit` policy while retaining the benchmark report: inherit the child's streams separately, so child stdout remains on the executable's stdout and child stderr remains on the executable's stderr. Output appears once for every warmup and measured invocation, and failing-command output must be visible on its corresponding inherited stream before the tool's standard-error diagnostic. An explicit `--style TYPE` cannot be combined with `--show-output`; validation exits with status 2 before benchmarking, writes nothing to standard output, and writes `error: the argument '--style <TYPE>' cannot be used with '--show-output'` to standard error. The direct `--output=inherit` spelling can be combined with an explicit style, including `--style=none`. `--output=null` discards directly. `--output=pipe` drains output through a pipe and discards it, rather than attaching `/dev/null` directly; this prevents child optimizations based on a null output device. Both remain invisible.

Any other `--output` value containing a path component is an output file. Create/truncate it for an invocation and direct the benchmark output there. Repeated runs overwrite rather than append, so after five `echo single` runs the file contains exactly one `single\n`. The policy is orthogonal to shell mode. Multiple `--output` occurrences map one-to-one to benchmarks as described in Spec 10. A bare unrecognized policy such as `invalid_policy` is not treated as a file and emits exactly `Error: Unknown output policy 'invalid_policy'. Use './invalid_policy' to output to a file named 'invalid_policy'.`

For every benchmark invocation set environment variable `HYPERFINE_ITERATION` to the zero-based measured iteration number (`0,1,2,...` for three measured runs), enabling the command to create distinct per-iteration files.

## Spec 13

Without `--ignore-failure`, a benchmark command's first nonzero exit status aborts the invocation. In a shell, an absent command conventionally produces 127. The diagnostic is:

```text
Error: Command terminated with non-zero exit code CODE in the first benchmark run. Use the '-i'/'--ignore-failure' option if you want to ignore this. Alternatively, use the '--show-output' option to debug what went wrong.
```

The substring without `in the first benchmark run` is sufficient for failures after the first run, but it must identify the actual code. A direct-execution spawn error uses the distinct `Failed to run command` error from Spec 6.

`-i` / `--ignore-failure` with no value accepts every nonzero command exit and continues all runs and benchmarks. `--ignore-failure=CODE[,CODE...]` accepts only the listed decimal integer codes; another code remains fatal. For accepted failures, the executable exits 0, reports timing normally, records every actual code in JSON, and writes a standard-error warning containing `Ignoring non-zero exit code`. A malformed list such as `abc` emits exactly `Error: Could not read numeric integer argument to '--ignore-failure': invalid digit found in string`.

## Spec 14

For every benchmark with mean below 5 ms when an intermediate shell is in use, standard error contains this warning text (as one logical line, optional indentation allowed):

```text
Warning: Command took less than 5 ms to complete. Note that the results might be inaccurate because hyperfine can not calibrate the shell startup time much more precise than this limit. You can try to use the `-N`/`--shell=none` option to disable the shell completely.
```

Very fast multi-run commands must emit at least one line beginning `Warning:`. When statistical outliers are detected, an additional warning may say `Statistical outliers were detected` and suggest a quiet system, warmup, or prepare; its occurrence may depend on measurements. Warnings never turn an otherwise successful benchmark into failure.

## Spec 15

When at least two results have usable nonzero means, print a comparison after all benchmark sections. With default `--sort=auto` or explicit `--sort=mean-time`, print:

```text
Summary
  REFERENCE ran
    RATIO ± UNCERTAINTY times faster than OTHER
```

Without `--reference`, REFERENCE is the lowest-mean benchmark and other results are ordered by mean. With `--reference`, it is the prepended reference even if not fastest. If the reference mean is smaller, ratio is `other_mean/reference_mean` and the phrase is `times faster than`; if larger, ratio is `reference_mean/other_mean` and the phrase is `times slower than`. A ratio equal at displayed precision may use `As fast (1.00 ± 0.00) as OTHER`. Ratios and uncertainty use two decimals. Propagate independent mean uncertainty as `ratio * sqrt((stddev_a/a)^2 + (stddev_b/b)^2)`.

`--sort=command` instead prints `Relative speed comparison` followed by one row per benchmark in original execution order. Values are relative to the fastest mean: the fastest row is formatted with `1.00`, while another row resembles `2.00 ±  0.00  sleep 2`. This section must preserve command order. Accepted sort values are exactly `auto`, `command`, and `mean-time`.

Comparison must handle equal, near-zero, high-variance, and widely different results without crashing, NaN exceptions, or division by zero. If a zero mean makes comparison impossible, omit the comparison and optionally emit a note, but retain all individual results and valid exports. With ordinary direct `sleep 0.2`, `0.3`, and `0.4`, measured ordering and ratios should reflect real durations; a 1.0-second sleep must measure more than five times a 0.1-second sleep.

## Spec 16

`--debug-mode` provides deterministic, fast synthetic timing for comparison scenarios. It must not actually wait for `sleep` commands. Interpret a benchmark of the form `sleep NUMBER` as having exact mean duration `NUMBER` seconds, zero timing uncertainty, and successful execution. It must support values as large as 1000.0. Normal headings and comparison output still appear. Therefore:

- `sleep 1.0`, `sleep 2.0`, `sleep 3.0` yields `sleep 1.0 ran`, `2.00 ± 0.00 times faster than sleep 2.0`, and `3.00 ± 0.00 times faster than sleep 3.0`.
- Equal one-second commands named `A` and `B` yield `A ran` and `As fast (1.00 ± 0.00) as B`.
- A reference `sleep 2.0` compared to `sleep 1.0` and `sleep 3.0` yields `2.00 ± 0.00 times slower than sleep 1.0` and `1.50 ± 0.00 times faster than sleep 3.0`.
- Under `--sort=command`, input `sleep 2`, `sleep 1` yields ordered rows containing exactly `2.00 ±  0.00  sleep 2` before `1.00          sleep 1`.

Other reporting, naming, reference, style, and export rules continue to apply in debug mode.

## Spec 17

`--style TYPE` accepts exactly `auto`, `basic`, `full`, `nocolor`, `color`, and `none`.

- `basic` produces static plain text: no ANSI escape sequences, spinner, progress block (`░`/`█`), `ETA`, or erase-line sequence.
- `color` produces the same noninteractive report but with ANSI decoration. It must include bold `\x1b[1m` and green `\x1b[32m` codes and must not include progress elements.
- `nocolor` enables interactive progress effects but never SGR color codes matching `\x1b[digits(;digits)*m`. When run through a pseudo-terminal, output includes at least a spinner glyph (`⠋` or `⠙`), a progress block, or `ETA`; its final static report has the normal structure. Without a terminal its final report remains plain and free of all ANSI sequences.
- `full` enables both progress effects and color, including the bold and green codes, and forces enhanced effects even when terminal autodetection would disable them. In a pseudo-terminal it includes a progress marker.
- `auto` uses interactive effects only when appropriate. Under captured non-TTY execution it behaves like `basic`, with normal results and no `ETA` or progress blocks.
- `none` suppresses all tool-generated normal benchmark headings, timing lines, summaries, and progress output. It does not suppress critical diagnostics, warnings on standard error, benchmark output inherited through `--output=inherit`, or an export deliberately targeted at standard output. As specified in Spec 12, the separate `--show-output` convenience option conflicts with every explicit `--style` value, including `none`.

The final report under every non-`none` style contains the same semantic benchmark data. Styling cannot alter files exported in machine/table formats.

## Spec 18

`--export-json PATH` writes UTF-8 JSON with exactly one top-level key, `results`, whose value is an array in expanded benchmark execution order. Every result contains these exact keys (and `parameters` when applicable):

```text
command, mean, stddev, median, user, system, min, max,
times, exit_codes, memory_usage_byte
```

`command` is the final substituted display/custom name. `mean`, `stddev`, `median`, `user`, `system`, `min`, and `max` are JSON numbers in seconds and nonnegative; with multiple runs `stddev` is a non-null number. `times` contains one nonnegative numeric wall duration in seconds per measured run. `exit_codes` contains the actual integer status from each measured run, including ignored failures. `memory_usage_byte` contains one positive integer byte measurement per measured run when collection is available and must be a list with realistic values for the supplied Python CPU workload. Array lengths exactly equal `--runs`.

For parameterized results, `parameters` is an object mapping every declared parameter name to its exact string value, including empty strings and unused parameters. JSON never converts numeric-looking parameter values to numbers. Display unit selection has no effect on JSON seconds. Quoting and Unicode in command strings must round-trip correctly.

## Spec 19

`--export-csv PATH` writes standards-compliant CSV. Its initial columns, in exact order, are:

```text
command,mean,stddev,median,user,system,min,max
```

Append one `parameter_NAME` column per declared parameter in ascending parameter-name order, independently of declaration order. Thus declarations named `z` and then `a` produce the suffix `parameter_a,parameter_z`. There is exactly one data row per result in expanded execution order. Timing values are parseable nonnegative decimal seconds regardless of `--time-unit`. CSV does not contain `times`, `exit_codes`, or other per-run array columns. Apply normal CSV quoting rules: a command such as `echo "hello,world"` parses back to that exact string and its embedded quotes are doubled in raw CSV.

Validate and create all requested export destinations before running any benchmark. An invalid parent path fails nonzero with `Error: Could not create export file 'PATH': No such file or directory (os error 2)`; an empty path fails with a message containing `Could not create export file`.

## Spec 20

The three table exporters contain exactly five columns in this order: `Command`, `Mean [UNIT]`, `Min [UNIT]`, `Max [UNIT]`, `Relative`. Mean cells contain `mean ± stddev`; the fastest usable result has relative value exactly `1.00`, and slower rows have a distinct value greater than 1 with propagated `±` uncertainty. Table rows follow expanded execution order when `--sort=command` (and ordinarily preserve execution order). Parameter placeholders are already substituted. Human-readable units follow Spec 5.

`--export-markdown PATH` writes exactly a header, divider, and one line per result:

```text
| Command | Mean [ms] | Min [ms] | Max [ms] | Relative |
|:---|---:|---:|---:|---:|
| `sleep 0.01` | 10.8 ± 0.1 | 10.7 | 11.0 | 1.00 |
```

Every line begins and ends with `|`; commands use backticks. Escape each command pipe as `\|`, e.g. `` `echo test \| cat` ``. `PATH` may be `-`, meaning write the final table once to standard output; with `--style=none`, command names then appear only in that table.

`--export-asciidoc PATH` begins with `[cols="<,>,>,>,>"]`, then `|===`, contains header cells such as `| Command`, `| Mean [ms]`, `| Min [ms]`, `| Max [ms]`, `| Relative`, uses backticks around commands, and ends with a second `|===`. It has no Markdown alignment-divider row.

`--export-orgmode PATH` has exactly one header line, one divider, and one line per result. Its header begins `| Command  |  Mean [UNIT] |  Min [UNIT] |  Max [UNIT] |  Relative |`; its divider has five segments and exactly four plus signs, such as `|--+--+--+--+--|`; commands use `=command=` and data first columns end with two spaces before `|`.

All five export flags may be used simultaneously and must each create a nonempty valid file from the same run. Export files are updated after completed benchmarks, so if a later benchmark fails, an already requested table file still exists with its header and every successfully completed earlier benchmark.

## Spec 21

Option/validation diagnostics below are written exactly to standard error, including capitalization and blank lines, and exit nonzero.

No positional command:

```text
error: the following required arguments were not provided:
  <command>...

Usage: executable <command>...

For more information, try '--help'.
```

An empty positional command:

```text
error: a value is required for '<command>...' but none was supplied

For more information, try '--help'.
```

Unknown option example:

```text
error: unexpected argument '--invalid-option' found

  tip: to pass '--invalid-option' as a value, use '-- --invalid-option'

Usage: executable [OPTIONS] <command>...

For more information, try '--help'.
```

Invalid enums use:

```text
error: invalid value 'invalid' for '--time-unit <UNIT>'
  [possible values: microsecond, millisecond, second]

For more information, try '--help'.
```

For `--sort`, replace the option/value line and possible values with `error: invalid value 'invalid' for '--sort <METHOD>'` and `[possible values: auto, command, mean-time]`. For `--style`, use `error: invalid value 'invalid' for '--style <TYPE>'` and `[possible values: auto, basic, full, nocolor, color, none]`. Any other invalid supplied value, such as time unit `nanosecond`, follows the same form and includes that value.

Nonnumeric integral arguments use `Error: Could not read numeric integer argument to '--OPTION': invalid digit found in string`; this is exact for `--runs` and `--warmup`. A nonnumeric minimum benchmarking time emits exactly `Error: Could not read numeric floating point argument to '--min-benchmarking-time': invalid float literal`.

The exact `--runs`/`--min-runs` conflict form is:

```text
error: the argument '--runs <NUM>' cannot be used with '--min-runs <NUM>'

Usage: executable --runs <NUM> <command>...

For more information, try '--help'.
```

The equivalent max-runs conflict must identify `--max-runs` and contain `cannot be used with`.

## Spec 22

Execution and exported observations must be genuine rather than fabricated outside the explicitly synthetic `--debug-mode`. For a successful `echo`, every JSON exit code is 0; for ignored `/bin/false`, all are 1. A `sleep 0.05` mean is close to its real elapsed duration, a CPU workload consumes measurable user time and memory, and distinct long sleeps retain their expected ordering. Times may be zero only after legitimate shell-overhead correction of extremely fast commands; arrays, statistics, headings, run counts, hooks, output files, and external side effects must all correspond to the number and order of actual invocations.

Commands and parameter data are UTF-8 safe. Files are written as UTF-8 text with final newlines where the illustrated formats show them. The implementation must promptly complete the described workloads, including 1,000 one-run parameter benchmarks and 100 runs of `true`, and must reject oversized parameter ranges before executing any benchmark.
