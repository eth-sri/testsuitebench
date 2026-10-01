# Clarified specification for `executable`

The required artifact is a directly runnable file named exactly `executable`. It implements the single-purpose POSIX command-looping utility described below. All text is UTF-8. Examples show exact output where stated.

## Spec 1

`executable` is a command-line program, not a subcommand dispatcher. Its invocation shape is:

```text
executable [FLAGS] [OPTIONS] [input]...
```

`input` is the command to run repeatedly. A standalone `--` ends parsing of loop options; every following argument belongs to the command, even if it begins with `-`. The separator is optional. Before a separator, recognized loop options may occur before or after command words. For example, `executable echo hi -n 1` runs `echo hi` once. An otherwise unknown bare word is a command word, not a subcommand name.

The program accepts these flags and aliases:

```text
-D, --error-duration
-h, --help
-l, --only-last
-i, --stdin
    --summary
-C, --until-changes
-f, --until-fail
-S, --until-same
-s, --until-success
-V, --version
```

It accepts these value-taking options and aliases:

```text
-b, --count-by VALUE
-e, --every VALUE
    --for VALUE
-d, --for-duration VALUE
-n, --num VALUE
-o, --offset VALUE
-c, --until-contains VALUE
-r, --until-error VALUE
-m, --until-match VALUE
-t, --until-time VALUE
```

Long options accept either `--name value` or `--name=value`. Short value options accept separate, attached, or equals forms, such as `-n 1`, `-n1`, and `-n=1`. A separate value token that begins with `-` is parsed as an option-like argument rather than as the preceding option's value and is rejected. Supply a negative numeric value with long-option equals syntax (`--num=-1`, `--count-by=-2.0`) or with an attached or equals short form (`-n-1`, `-n=-2.9`, `-b-1.5`, `-b=-1.5`). Boolean short options may be combined with another short option, so `-ln 1` is equivalent to `-l -n 1`.

## Spec 2

`--help` prints exactly the following text to standard output, including the blank lines, spacing, the literal `4ITEM` in the `--for` description, and one final newline. It exits 0 and writes nothing to standard error. `-h` provides the same help. The output contains no ANSI control sequences.

```text
loop 0.6.1
Rich Jones <miserlou@gmail.com>
UNIX's missing `loop` command

USAGE:
    executable [FLAGS] [OPTIONS] [input]...

FLAGS:
    -D, --error-duration    Exit with timeout error code on duration
    -h, --help              Prints help information
    -l, --only-last         Only print the output of the last execution of the command
    -i, --stdin             Read from standard input
        --summary           Provide a summary
    -C, --until-changes     Keep going until the output changes
    -f, --until-fail        Keep going until the command exit status is non-zero
    -S, --until-same        Keep going until the output changes
    -s, --until-success     Keep going until the command exit status is zero
    -V, --version           Prints version information

OPTIONS:
    -b, --count-by <count_by>                Amount to increment the counter by [default: 1]
    -e, --every <every>                      How often to iterate. ex., 5s, 1h1m1s1ms1us [default: 1us]
        --for <ffor>                         A comma-separated list of values, placed into 4ITEM. ex., red,green,blue
    -d, --for-duration <for_duration>        Keep going until the duration has elapsed (example 1m30s)
    -n, --num <num>                          Number of iterations to execute
    -o, --offset <offset>                    Amount to offset the initial counter by [default: 0]
    -c, --until-contains <until_contains>    Keep going until the output contains this string
    -r, --until-error <until_error>          Keep going until the command exit status is the value given
    -m, --until-match <until_match>          Keep going until the output matches this regular expression
    -t, --until-time <until_time>            Keep going until a future time, ex. "2018-04-20 04:20:00" (Times in UTC.)

ARGS:
    <input>...    The command to be looped
```

Help processing is left-to-right: `--help --badflag` succeeds with help, while `--badflag --help` is an unknown-option error rather than help.

## Spec 3

`--version` and `-V` print this exact line to standard output and exit 0:

```text
loop 0.6.1
```

There is no standard-error output. Help and version are global actions; the help text must not contain a `COMMANDS:`, `SUBCOMMANDS:`, or available-subcommands section.

## Spec 4

If parsing succeeds but no command words remain, or if the sole command-position argument is the empty string, print exactly:

```text
No command supplied, exiting.
```

to standard output, write nothing to standard error, and exit 0. This also applies when loop controls such as `--num 1` were supplied without a command. In particular, invoking `executable ''` produces this message once and does not enter the loop.

If a command exists and no finite iteration source or stopping limit is supplied, execute indefinitely until a stopping condition matches or the user interrupts the process. SIGINT must stop it promptly without producing a diagnostic on standard error.

## Spec 5

Construct the command by joining all command-position arguments with single ASCII spaces, then execute that text through a POSIX-compatible shell on every iteration. Thus both `"echo hello"` as one argument and `"echo", "hello"` as two arguments run successfully, and `"echo hi", "foo"` becomes `echo hi foo`. Normal shell behavior is required for environment expansion, quoting embedded in the command text, pipelines, redirections, semicolons, conditionals, command substitution, and arithmetic expansion. Preserve the caller's environment and working directory so commands can access inherited variables and create files relative to that directory.

For each child execution, capture its standard output and standard error and emit both through `executable`'s standard output; child diagnostics must not become diagnostics of `executable`. Before emitting a nonempty iteration result, ensure that it ends in an LF byte: append `\n` when the captured result has no final LF, and do not append another when it already has one. Apart from this final-LF normalization, preserve the complete content, including multiline, long, and Unicode output. An empty result emits nothing. For example, one `printf hello` attempt emits `hello\n`, two `printf x` attempts emit `x\nx\n`, and the captured result `a\n\n` remains `a\n\n`. Normal command output is emitted once per completed iteration in iteration order.

Except for CLI validation failures and the timeout behavior in Spec 13, `executable` exits 0 after its loop finishes, regardless of child exit statuses. A child exiting 1, 42, 127, or 255 does not by itself become the program's exit status.

## Spec 6

`--num N` sets a maximum number of executions. `N` is parsed as a floating-point number. A positive fractional value is truncated toward zero: `--num 2.5` performs two executions. Zero performs zero executions and exits successfully. Negative values also perform zero executions when supplied in an equals form, as required by Spec 1: both `--num=-1` and `-n=-2.9` succeed with zero attempts. In contrast, the separate forms `--num -1` and `--num -2.9` are CLI errors because the negative token is parsed as an unexpected option-like argument. Examples:

```text
executable --num 3 -- 'echo $COUNT'
0
1
2
```

With no other earlier stop condition, a positive integer `N` produces exactly `N` attempts. Large values such as 100, 1,000, or more must work without arbitrary truncation. When multiple finite limits are present, execution ends at the first limit reached; for example, `--num 2 --for-duration 10s` performs only two runs.

## Spec 7

`--for VALUE` supplies `ITEM` values and normally bounds the loop to the number of parsed items. On iteration `i`, expose that item as the child environment variable `ITEM`. Choose the item delimiter as follows:

- If `VALUE` contains commas, split on commas and preserve spaces inside each comma-delimited item. Empty fields are preserved: `a,,c` yields `a`, the empty string, and `c`.
- Otherwise, split a nonempty value only at line boundaries. Spaces and tabs within a line remain part of that one item. Thus `one  two\nthree` produces the two items `one  two` and `three`, while `alpha\nbeta\ngamma` produces three items.
- An empty `VALUE` represents one empty item.

Items may be Unicode and may contain paths, colons, equals signs, or other shell-relevant characters. They are supplied as an environment value; subsequent unquoted `$ITEM` expansion follows ordinary shell rules.

Without `--num`, each item is used once and the list then ends. If explicit `--num N` is smaller than the list, use only the first `N` items. If it is larger, repeat the final item for all remaining iterations. For example:

```text
executable --for a,b --num 4 -- printenv ITEM
a
b
b
b
```

## Spec 8

`--stdin`/`-i` reads standard input as an item source. Also automatically use nonempty piped/non-terminal standard input as an item source when `--stdin` is absent. Each input line is one `ITEM`; remove its line terminator, handle both LF and CRLF, retain embedded spaces and Unicode, preserve empty lines, and keep a final line even if it lacks a trailing newline.

Without `--num`, execute once per input line. With `--num`, stop early if the numeric bound is smaller, or repeat the final input item if the bound exceeds the available line count. Thus input `a\nb\nc\n` with `--num 5` produces items `a,b,c,c,c`. An empty stdin must not cause argument-parsing failure, and an explicit positive `--num` still controls command execution when there are no input items.

## Spec 9

Before each child run, set these environment variables:

- `ACTUALCOUNT`: the zero-based integer attempt index, always formatted as an integer (`0`, `1`, `2`, ...).
- `COUNT`: the configurable numeric counter, equal mathematically to `offset + ACTUALCOUNT * count_by`.

`--offset` defaults to `0`; `--count-by` defaults to `1`. Both parse floating-point syntax and permit positive, negative, zero, very small, very large, and scientific-notation values, subject to Spec 1's syntax rule for negative values. In particular, `--count-by=-2.0` and `-b=-1.5` are accepted, whereas the separate forms `--count-by -2.0` and `-b -1.5` are rejected as unexpected option-like arguments. Offset changes only `COUNT`; `ACTUALCOUNT` always starts at zero. These values compose with list and stdin iteration. For example, `--num 3 --offset 10 --count-by 2` exposes `(COUNT, ACTUALCOUNT)` as `(10,0)`, `(12,1)`, `(14,2)`.

Compute the sequence without visibly accumulating binary floating-point drift: step `0.1` for ten runs must display `0.0` through `0.9`, not a long approximation.

## Spec 10

The displayed precision of `COUNT` is fixed solely by the spelling of `--count-by`, not by `--offset` or by the numeric result. It is the count of decimal digits written after the literal decimal point in the mantissa. Preserve trailing zeros. If there is no literal decimal point, precision is zero, even for scientific notation.

Consequently:

```text
--count-by 1       => 0, 1, 2
--count-by 0.1     => 0.0, 0.1, 0.2
--count-by 0.001   => 0.000, 0.001, 0.002
--count-by 1.50    => 0.00, 1.50, 3.00
--count-by 2.5e1   => 0.0, 25.0, 50.0
--count-by 1e2     => 0, 100, 200
--count-by 1e-3    => 0, 0, 0
```

Support at least nine fixed decimal places (`0.123456789` produces `0.000000000`, `0.123456789`, `0.246913578`). Values are rounded using normal fixed-point formatting. Since offset precision is ignored, the default integer step with offset `0.5` formats successive mathematical values `0.5,1.5,2.5` as `0,2,2`.

## Spec 11

`--every DURATION` controls pacing and defaults to `1us`. Accept integer duration components using at least `us`, `ms`, and `s`, and accept concatenated components such as `100ms500us`, `1s100ms`, and `1s500ms`. Do not accept fractional-unit spelling: `0.5s` is invalid; callers must write `500ms`.

Pacing includes a wait for each scheduled attempt, including the final fixed-count attempt. Therefore three trivial runs with `--every 100ms` take approximately 300 ms, while 100 default-paced trivial runs comfortably complete in under one second. Timing need not be cycle-exact, but must stay within ordinary scheduling tolerance: three 100 ms runs should take about 0.25–0.45 seconds.

## Spec 12

`--for-duration DURATION` bounds total loop time using the same duration grammar as `--every`. A zero duration performs no iterations. A positive duration performs at least one iteration, then continues until the duration expires; with `--every 50ms --for-duration 1s`, approximately 20 iterations (15–25 under scheduler tolerance) should complete and elapsed time should be about one second.

Time spent executing the command and pacing both count toward this limit. A slow command taking roughly 0.5 seconds with `--for-duration 1s` completes two attempts. A numeric limit, an item-source limit, or a matching stop condition may finish the loop before the duration does.

## Spec 13

`--error-duration`/`-D` changes only the result of expiration of `--for-duration`: if that duration is what ends the loop, exit with status 124 after retaining all output already produced. Without `--error-duration`, expiration exits 0. If `--error-duration` is present without `--for-duration`, ignore it and operate normally. If another bound such as `--num` ends first, exit normally rather than 124.

For example, `--for-duration 1ms --every 10ms --error-duration -- true` performs the applicable timed attempt and exits 124.

## Spec 14

`--until-time TIMESTAMP` is an absolute UTC deadline. Check the deadline before executing: a past deadline performs zero iterations and exits 0. A future deadline runs until the current time reaches it, subject to any earlier numeric or conditional limit. A deadline about 500 ms in the future with default pacing must run many iterations and finish close to that deadline.

Accept these UTC forms:

```text
YYYY-MM-DD HH:MM:SS
YYYY-MM-DDTHH:MM:SSZ
YYYY-MM-DDTHH:MM:SS.fractionZ
```

Validate calendar ranges. A timezone-offset suffix such as `+00:00` is not supported even though it is otherwise RFC 3339-like.

## Spec 15

`--until-contains TEXT` performs a case-sensitive, literal substring search over the complete captured output of every iteration. The entire `TEXT` must occur contiguously; separate parts of it cannot match at different positions. It does not interpret regex metacharacters. It checks multiline and Unicode output and matches partial words: `str` matches `substring`, and `[3]` matches `a [3] substring`, but `[3] str` does not match `a [3] substring` because `sub` occurs between `[3] ` and `str`. The matching iteration is executed and emitted, then the loop stops. An empty search text matches the first produced output.

If the text never occurs, run until the active numeric, duration, time, list, or stdin limit. With no such limit, keep running.

## Spec 16

`--until-match REGEX` performs a case-sensitive Unicode regular-expression search independently on each line of a completed iteration's captured output. Line terminators are removed before matching: they cannot satisfy `\s`, and a match cannot span two output lines. Thus `--for 'test,test space,testspace' --until-match 'test\s' -- echo '$ITEM'` emits `test\n` and then `test space\n` before stopping; the LF after the first `test` is not searched. Support the tested regex features: literal escapes, `.`, `^` and `$`, character and negated classes, `\d`, `\s`, `\w`, grouping and noncapturing grouping, alternation, `?`, `*`, `+`, greedy/non-greedy forms, and exact/range quantifiers. Anchors work against each individual line, so `^PATTERN5$` can match an interior line that is exactly `PATTERN5`.

The triggering iteration is included in output. A regex capable of matching the empty string matches the first iteration that contains at least one line, including an empty line represented by an LF. A completely empty captured result contains no lines and therefore does not match: `--num 3 --until-match 'q*' --summary -- true` performs all three attempts. Invalid regex syntax is a nonzero CLI error written to standard error rather than a child execution.

## Spec 17

`--until-changes` compares the complete current captured output byte-for-byte with the immediately preceding iteration. The first iteration establishes a baseline and never triggers this condition. Stop after and include the first later output that differs. If all outputs remain equal, continue to the other active bound.

`--until-same` also stores the complete first iteration as a fixed baseline. It stops after and includes the first later output identical to that first output; it does not compare two later iterations with each other and does not replace the baseline. Consequently, constant output ends after two attempts, but output `first` followed by repeated `repeat` values never satisfies `--until-same` and runs to its other bound. Likewise, if attempt zero emits `text ` and every later attempt emits `text`, `--num 10 --until-same` performs all ten attempts. Comparisons preserve spaces, blank lines, newline counts, empty output, and arbitrarily long output; no whitespace normalization is allowed.

This fixed-baseline rule also explains the finite-list case below: none of the later item outputs equals the first output, so the list is exhausted and the final item is printed.

```text
executable --for=1,2,3,4,5,5,6,7 --until-same --only-last -- 'echo $ITEM'
7
```

The same fixed-baseline behavior applies with `--num`, stdin, and every other item source or bound.

## Spec 18

Exit-status conditions inspect every child status after that attempt completes:

- `--until-success` stops on the first status 0.
- `--until-fail` stops on the first nonzero status.
- If the `--until-error` value parses as a numeric `CODE`, stop on exactly that status, including codes 0, 1, 42, 127, and 255; other nonzero statuses do not trigger it.
- If the value is nonnumeric, stop on the first nonzero status and never on 0. This applies to `any` and to arbitrary strings such as `no-code`; such strings are accepted rather than treated as validation errors.

The triggering attempt and its output are included. If no status matches, continue to the other active bound. Even when such a condition triggers on a failed child, `executable` itself exits 0.

## Spec 19

All active stop conditions and limits compose using logical OR: after each attempt, stop when the first applicable output/status condition matches; before another attempt, stop if a count, source, duration, or absolute-time bound has been reached. No condition disables counters, item iteration, pacing, output control, or summary accounting. If both `--until-changes` and `--until-same` are present, the second comparison necessarily satisfies one of them, so stop after the second attempt. If both a success condition and numeric `--until-error 0` are present, a successful first attempt stops immediately.

An explicit `--num` is always an upper bound even if an until-condition never matches. Conversely, an until-condition may end a very large or unbounded loop early.

## Spec 20

`--only-last` suppresses output from all but the final attempt actually performed. Buffer the complete combined output of each attempt and, when the loop ends, emit only the final attempt's output using the final-LF normalization from Spec 5. This includes all lines of a multiline result. If the last attempt has no output, or if there were zero attempts, emit nothing.

When a condition stops the loop, “last” means the triggering attempt. `--only-last` must not prevent output/status conditions from examining intermediate captured results. It composes with timing, item/stdin sources, counters, and summaries.

## Spec 21

`--summary` appends an exact three-line report to standard output after the final-LF-normalized ordinary output (or after the one retained result under `--only-last`):

```text
Total runs:\tT
Successes:\tS
Failures:\tF
```

Here `T` is the number of attempts actually made, `S` the number whose child status was 0, and `F` the number whose status was nonzero. The displayed separators after each colon are literal tab bytes. When `F > 0`, append a space and every failure status in occurrence order, without deduplication or truncation:

```text
Failures:\t3 (2, 127, 255)
```

Each line ends in `\n`. A zero-run summary is exactly:

```text
Total runs:\t0
Successes:\t0
Failures:\t0
```

Summary statistics cover all attempted iterations, even when `--only-last` hides their output or a stop condition ends execution early.

## Spec 22

CLI and value-validation failures exit nonzero (status 1 is expected for unknown arguments), write diagnostics to standard error, and do not run the command or write normal output. Unknown options must produce text containing all of:

```text
Found argument '--badflag'
USAGE:
For more information try --help
```

Invalid numeric values identify their option. These tested diagnostics are exact, each with a final newline:

```text
error: Invalid value for '--num <num>': invalid float literal
error: Invalid value for '--count-by <count_by>': invalid float literal
error: Invalid value for '--every <every>': expected number at 0
error: Invalid value for '--for-duration <for_duration>': expected number at 0
error: Invalid value for '--every <every>': invalid character at 1
error: Invalid value for '--until-time <until_time>': timestamp format is invalid
error: Invalid value for '--until-time <until_time>': numeric component is out of range
```

The first duration message applies to values such as `invalid`, the second `--for-duration` message to values such as `notvalid`, and the `invalid character at 1` message to `--every 0.5s`. `--until-time` uses “numeric component is out of range” for a structurally timestamp-like value with an invalid calendar component such as month 13, and “timestamp format is invalid” for malformed text or an unsupported offset timezone.

A separately supplied negative duration such as `--every -5s` is parsed as an unexpected option-like argument and the diagnostic contains `Found argument '-5' which wasn't expected`. Invalid `--offset` and other floating-point controls likewise fail and identify the corresponding option. Invalid regex syntax also fails nonzero on standard error.
