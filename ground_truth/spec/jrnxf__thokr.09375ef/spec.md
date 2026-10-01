# Clarified executable specification

The required artifact is a runnable program named exactly `executable`. It is a
single-mode terminal typing-test application. All behavior below belongs to that
program; terminal-driving helpers used by an evaluator are harness-provided and
are not part of the artifact.

## Spec 1

`executable` is a command-line program named **thokr**, version **0.4.1**, with
the description `sleek typing tui with visualized results and historical
logging`. It has no positional arguments, commands, or subcommands. In
particular, words such as `add`, `remove`, `list`, `show`, `init`, `start`,
`run`, and `help` are invalid positional arguments rather than subcommands.

It supports these single-use options:

| Short | Long | Value | Default |
|---|---|---|---|
| `-f` | `--full-sentences` | unsigned native-size integer | absent |
| `-l` | `--supported-language` | `english`, `english1k`, or `english10k` | `english` |
| `-p` | `--prompt` | arbitrary UTF-8 string, including empty | absent |
| `-s` | `--number-of-secs` | unsigned native-size integer | absent |
| `-w` | `--number-of-words` | unsigned native-size integer | `15` |
| `-h` | `--help` | no value | — |
| `-V` | `--version` | no value | — |

Value options accept a separate argument (`-w 15`, `--number-of-words 15`), a
long-option equals form (`--number-of-words=15`), and an attached short value
(`-w15` or `-w=15`). Options can be supplied in any order and otherwise combine
freely.

## Spec 2

`-h` and `--help` exit successfully, write nothing to standard error, and write
exactly the following UTF-8 text to standard output, including all blank lines,
indentation, wrapping, and the final newline:

```text
thokr 0.4.1
sleek typing tui with visualized results and historical logging

USAGE:
    executable [OPTIONS]

OPTIONS:
    -f, --full-sentences <NUMBER_OF_SENTENCES>
            number of sentences to use in test

    -h, --help
            Print help information

    -l, --supported-language <SUPPORTED_LANGUAGE>
            language to pull words from [default: english] [possible values: english, english1k,
            english10k]

    -p, --prompt <PROMPT>
            custom prompt to use

    -s, --number-of-secs <NUMBER_OF_SECS>
            number of seconds to run test

    -V, --version
            Print version information

    -w, --number-of-words <NUMBER_OF_WORDS>
            number of words to use in test [default: 15]
```

There must be no `COMMANDS:` or `SUBCOMMANDS:` section. Encountering help takes
precedence over later arguments: for example, `--help --definitely-not-a-flag`
prints this help and succeeds, and valid options followed by help do likewise.

## Spec 3

`-V` and `--version` exit successfully, write nothing to standard error, and
write exactly `thokr 0.4.1\n` to standard output. Version may be combined with
otherwise valid options and still produces the version response rather than
starting the TUI.

## Spec 4

Argument parsing is strict and follows the error conventions below. Every parse
error exits with status `2`, emits nothing on standard output, emits the error
on standard error, and ends with `For more information try --help\n`.

For a missing value, use this exact form (substitute the canonical long option
and placeholder):

```text
error: The argument '--number-of-words <NUMBER_OF_WORDS>' requires a value but none was supplied

USAGE:
    executable [OPTIONS]

For more information try --help
```

The canonical pairs are `--full-sentences <NUMBER_OF_SENTENCES>`,
`--supported-language <SUPPORTED_LANGUAGE>`, `--prompt <PROMPT>`,
`--number-of-secs <NUMBER_OF_SECS>`, and
`--number-of-words <NUMBER_OF_WORDS>`. A missing language value additionally
places this tab-indented line immediately after the first line:
`[possible values: english, english1k, english10k]`.

If any single-use option appears twice, reject it using the same layout and the
first line:

```text
error: The argument '--number-of-words <NUMBER_OF_WORDS>' was provided more than once, but cannot be used multiple times
```

Again substitute the appropriate canonical pair.

## Spec 5

The three count values are unsigned integers. Zero is valid, as are large values
that fit the platform's native unsigned integer. Non-numeric input is rejected.
For example, the complete non-numeric word-count error is:

```text
error: Invalid value "abc" for '--number-of-words <NUMBER_OF_WORDS>': invalid digit found in string

For more information try --help
```

The sentence and seconds forms differ only in canonical option and placeholder.
An overflowing word count such as `999999999999999999999` is rejected with
`number too large to fit in target type` in place of `invalid digit found in
string`.

A token beginning with `-` is parsed as an option, not as a negative numeric
value. For example `-w -1` reports exactly:

```text
error: Found argument '-1' which wasn't expected, or isn't valid in this context

	If you tried to supply `-1` as a value rather than a flag, use `-- -1`

USAGE:
    executable [OPTIONS]

For more information try --help
```

Language names are lowercase and case-sensitive. An invalid language uses:

```text
error: "invalid" isn't a valid value for '--supported-language <SUPPORTED_LANGUAGE>'
	[possible values: english, english1k, english10k]

USAGE:
    executable --supported-language <SUPPORTED_LANGUAGE>

For more information try --help
```

For `English`, insert a tab-indented blank-separated suggestion
`Did you mean "english"?` before `USAGE:`.

## Spec 6

Unknown flags and positional arguments are rejected with status `2`. For an
unknown flag `X`, use the first line `error: Found argument 'X' which wasn't
expected, or isn't valid in this context`, then a blank line, then the
tab-indented hint `If you tried to supply \`X\` as a value rather than a flag,
use \`-- X\``, then the standard `USAGE:` block for `executable [OPTIONS]` and
help hint. A positional argument uses the same `Found argument` wording.

The program accepts no positionals even after `--`. Thus `-- --help` and
`-- -w` fail instead of invoking an option. The former error contains `Found
argument '--help'`, `USAGE:`, and the help hint. Value-taking short options do
not form a combinable flag cluster: `-ws 10` is invalid (the parser may consume
`s` as the value of `-w`, but must then reject `10`).

## Spec 7

Argument parsing occurs before terminal validation. After valid non-help,
non-version arguments have parsed, standard input must be a TTY. If it is not,
exit with status `2`, write nothing to standard output, and write exactly this
to standard error:

```text
error: stdin must be a tty

USAGE:
    thokr [OPTIONS]

For more information try --help
```

This applies with no options and with every valid option/value combination,
including zero, empty prompts, Unicode prompts, very large fitting counts, and
equals/attached value syntax. Invalid syntax must report its parse error instead
of this TTY error.

## Spec 8

With a TTY, enter an alternate full-screen terminal buffer, enable raw keyboard
input, and hide the normal shell display. On a normal quit, restore the original
screen, raw-mode state, and cursor and exit with status `0`. Escape quits both
the typing screen and the results screen.

For ASCII prompts, the TUI must remain responsive during typing and timer
updates and must not print panic, fatal, or ordinary error text into the
terminal. Non-ASCII custom prompts instead have the deterministic UTF-8
byte-boundary failure behavior described in Spec 9.

The UI redraws after each handled key, terminal resize, and 100 ms timer tick.
Logical text styles are important: bold green for correct positions, bold red
for incorrect positions, bold+dim for untyped prompt text, bold+dim+underline
for the next character, bold for numeric chart endpoint labels and statistics,
and italic for the results controls. The chart axes, the `wpm` and `seconds`
axis titles, and the Braille chart line have no text attributes or foreground
color applied. ANSI terminals should receive the corresponding SGR styling
(green color index 2 and red color index 1 are accepted by the expected
terminal captures).

## Spec 9

Prompt selection has the following precedence:

1. If `-p/--prompt` is present, use its value after the line-break processing
   below; it overrides sentence count, word count, and language-based
   generation.
2. Otherwise, if `-f/--full-sentences` is present, generate that many English
   sentences; this overrides word count.
3. Otherwise, choose the requested number of distinct words for the selected
   language and join them with one ASCII space.

The default is therefore 15 distinct `english` words. Requests for 1, 5, 25,
100, and 200 words must produce the corresponding count while the vocabulary
has enough entries. Selection is randomized without replacement. If a request
exceeds a vocabulary's available entries, return all available distinct entries
rather than hanging or duplicating. Generated prompts requested again in one
session must normally differ.

`-p` accepts empty strings, long strings, leading/trailing/repeated whitespace,
newlines, tabs, punctuation, digits, emoji, and non-ASCII text such as
`café naïve résumé`; argument parsing does not reject them or validate them
against a vocabulary. Before rendering a custom prompt, split its value into
lines and concatenate those lines with no separator, discarding the line
terminators. Thus `-p $'top\nbottom'` displays the single prompt `topbottom` on
one row, rather than two prompt rows. Multiple and leading/trailing line breaks
are removed the same way; other leading, trailing, and repeated whitespace is
retained.

The renderer is not Unicode-safe: it uses the one-based next-character
position as a UTF-8 byte index, and a non-boundary index causes a Rust panic.
These two cases define the observable failure precisely:

* At 80x24, `-p "界界界"` enters the alternate buffer and then exits with
  status `101` before displaying the prompt. Its terminal output contains these
  lines in order (the decimal thread ID varies):

  ```text
  thread 'main' (<decimal thread ID>) panicked at src/ui.rs:<error location>:
  byte index 1 is not a char boundary; it is inside '界' (bytes 0..3) of `界界界`
  note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
  ```

* At 100x24, `-p "café naïve résumé 🧪"` initially displays that prompt
  centered on row 12, starting in column 41 (one-based). Typing the same text
  reaches the failure after the initial `caf` and exits with status `101`. The
  panic line above is followed by:

  ```text
  byte index 4 is not a char boundary; it is inside 'é' (bytes 3..5) of `café naïve résumé 🧪`
  note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
  ```

## Spec 10

The following 200 words form the complete base `english` vocabulary and a safe
shared subset of `english1k` and `english10k`. Generated word-mode prompts for
all three language choices may be selected entirely from this list; this keeps
the observable behavior self-contained. Preserve spelling and case (`I` is
uppercase):

```text
the be of and a to in he have it that for they I with as not on she at by this
we you do but from or which one would all will there say who make when can more
if no man out other so what time up go about than into could state only new year
some take come these know see use get like then first any work now may such give
over think most even find day also after way many must look before great back
through long where much should well people down own just because good each those
feel seem how high too place little world very still nation hand old life tell
write become here show house both between need mean call develop under last right
move thing general school never same another begin while number part turn real
leave might want point form off child few small since against ask late home
interest large person end open public follow during present without again hold
govern around possible head consider word program problem however lead system set
order eye plan run keep face fact group play stand increase early course change
help line
```

The language variants conceptually represent increasingly large common-English
vocabularies (200, 1,000, and 10,000 words), but only words from the shared set
above are required to be emitted. A larger internal list must not emit malformed
tokens: word-mode tokens are ordinary nonempty words without embedded
whitespace.

## Spec 11

Sentence mode produces readable, randomized English prose. Each requested
sentence starts with an uppercase letter, contains multiple words, ends with a
period, and is separated from the next sentence by normal spacing. One requested
sentence yields exactly one terminal period; three yield exactly three; five
yield at least four visibly parseable sentence boundaries; 20 yield at least 18
periods, more than 500 visible characters, and multiple capitalized sentence
starts. Keep two-sentence prompts short enough to be completely visible and
recoverable in at most three wrapped prompt lines in an 80-column by 24-row
terminal.

A retry preserves the exact generated sentences. A new test regenerates a
different prompt with the same sentence-count mode. The selected language option
must coexist with sentence mode, although only the English sentence structure
above is observable.

Zero words, zero sentences, and an explicitly empty custom prompt describe an
already finished test: show the zero-valued results screen immediately rather
than waiting for input or crashing.

## Spec 12

On the typing screen, display only the optional countdown and the processed
prompt from Spec 9, centered vertically. For terminal width `W`, reserve five
columns on each side, so the content width is `W-10`. A prompt that fits on one
display line and does not encounter the Spec 9 byte-boundary panic is
horizontally centered. If its display width is `P`, its zero-based starting
column is `ceil((W-P)/2)`: when the unused width is odd, the left padding has
one more column than the right padding. A longer prompt is left-aligned at
column 6 (one-based), word-wrapped within `W-10` columns, and wrapping trims
whitespace at a line boundary.

For a prompt that renders successfully, compute prompt height as 1 if its
Unicode display width is at most `W-10`; otherwise use
`ceil(display_width/(W-10)) + 1`. The vertical layout consists of a top region
of `floor((H-prompt_height)/2)` rows, a timer region of 2 rows when timed (0
otherwise), the prompt region, and a corresponding bottom region. The terminal
layout solver clips these regions to the available `H` rows. On an 80x24
untimed one-line prompt, the prompt is therefore on row 12 (one-based). In timed
mode its timer is on row 12 and its prompt on row 14. The entire buffer contains
exactly the terminal's rows, including blank lines.

For example, after removing ANSI styling, an untimed 80x24 screen for `-p "hello
world"` has `hello world` on row 12 with 35 spaces before it and 34 after it.
For `-p "the quick brown fox jumps over the lazy dog and runs through the
forest"`, row 11 begins with five spaces and contains `the quick brown fox jumps
over the lazy dog and runs through the`, and row 12 begins with five spaces and
contains `forest`. After resizing an untimed `-p "resize me"` screen to 120x40,
the prompt is on row 20 with 56 spaces before it and 55 after it.

## Spec 13

For ASCII prompts, typing is position-based. The first character input starts
elapsed-time tracking. Each printable character consumes exactly one next
prompt position regardless of whether it is correct. Render the expected prompt
character—not the incorrect key itself—at every consumed position: green if the
key equaled that expected character, red otherwise. If an expected space is
typed incorrectly, render a red middle dot `·` so the mistake is visible. The
character at the current input position is underlined and dim; all later
characters are dim. Completion occurs as soon as the number of accepted input
characters equals the prompt length, even if every key was wrong. Non-ASCII
custom prompts follow the failure behavior in Spec 9 instead of this successful
typing path.

Backspace before completion removes the most recent accepted character and moves
the current position back by one. Repeated backspace can return to the initial
state. Backspace at position zero is a no-op and leaves the screen byte-for-byte
unchanged. Retyping a removed position recomputes its correctness from the new
key. Backspace has no effect after the test has completed.

For exact ANSI serialization, let `ESC` denote byte `0x1b`. At 80x24, startup
with `-p "cat"` emits exactly the following bytes for alternate-screen entry,
the initial prompt, and cursor hiding:

```text
ESC[?1049hESC[12;40HESC[1mESC[4mESC[2mcESC[24matESC[39mESC[49mESC[0mESC[?25l
```

The renderer updates only changed cells. Starting a separate 80x24 invocation
with `-p "dog"`, the bytes added by typing `d` are exactly:

```text
ESC[12;40HESC[1mESC[38;5;2mdESC[4mESC[2mESC[39moESC[39mESC[49mESC[0mESC[?25l
```

The bytes added by then typing `x` are exactly:

```text
ESC[12;41HESC[1mESC[38;5;1moESC[4mESC[2mESC[39mgESC[39mESC[49mESC[0mESC[?25l
```

This illustrates that an incorrect key colors the expected character (`o` in
the last example), SGR attributes are emitted as separate commands in this
order, unchanged cells need not be re-emitted, and no cursor glyph is inserted
into the text.

## Spec 14

Left Arrow restarts a test from either active or results state: it retains the
exact current prompt and mode but clears input, timing, metrics, and the timer.
Right Arrow starts a new test: it regenerates a prompt according to the original
generation mode and clears the same state. In word-generation mode, successive
new prompts should differ. A timed restart/new test restores the full original
duration and waits for a first character before counting down.

On the results screen, lowercase `r` is equivalent to Left Arrow (retry same
prompt), and lowercase `n` is equivalent to Right Arrow (new generated prompt).
After `n`, even a session originally created with a custom prompt switches to a
fresh word-mode prompt using its original default/explicit word count, rather
than reusing the custom prompt. Other printable input on results does not alter
the completed statistics.

## Spec 15

When `-s N` is present with `N > 0`, show the remaining time centered above the
prompt with exactly one decimal digit, initially `N.0`. Do not show any timer
without `-s`. The countdown does not begin merely because the application has
launched: the first accepted character starts it. Thereafter subtract 0.1 every
100 ms while the test is active and redraw, so ordinary scheduling tolerance is
acceptable but three real seconds must reduce the displayed value by about
three seconds.

End and calculate the test immediately when either the prompt is fully consumed
or remaining time becomes `<= 0.0`. A 1-, 2-, 3-, or 5-second test must therefore
reach results after its duration once typing has begun, even with an incomplete
prompt. Completing early reaches results immediately. Once results are shown,
the timer and screen are frozen. `-s 0` is accepted and starts in the already
finished zero-results state.

## Spec 16

Results are calculated from all currently accepted input positions and their
timestamps. Accuracy is positional:

```text
accuracy = round(100 * correct_positions / accepted_positions)
```

Thus perfect input is 100%; `hellx world` against `hello world` is 91%;
`hxllo wxrld` is 82%; `axcd` against `abcd` is 75%; `hxllo` against `hello` is
80%; and all-wrong input is 0%. Empty/already-finished tests use 0%.

For compatibility with the observed timing behavior, calculate WPM points as
follows. Let `E` be the integer count of elapsed **milliseconds** from the first
keypress to calculation, represented as a floating-point number. For each
correct input, let `t` be its fractional elapsed seconds from the first keypress
and assign it to bucket `b`:

```text
if t == 0:                         b = 1
else if ceil(t) <= floor(E):
    if 0 < t < 1:                 b = 1
    else:                         b = ceil(t)
else:                             b = E
```

Group correct characters by identical `b`, sort buckets numerically, and keep a
cumulative correct count `C`. The graph point for each bucket is
`(b, (60/b) * C/5)`. Overall WPM is the ceiling of the final point, or 0 when
there are no correct characters. IEEE infinity is retained and displayed as
`inf`; this occurs for some completions inside the first millisecond. Otherwise
WPM is displayed without a fractional part (for example `36`, `108`, or `0`).

Standard deviation is the population standard deviation of the per-bucket
correct-character counts, excluding the final bucket. If that leaves no values,
it is 0. Display it with exactly two decimal digits. These definitions ensure
all-wrong input yields `0 wpm   0% acc   0.00 sd`, and a very fast correct
single-character input may yield `inf wpm   100% acc   0.00 sd`.

## Spec 17

The results screen contains a WPM-over-time line chart, a centered statistics
line, and a control legend. With horizontal and vertical margins of 5 columns
and 2 rows, respectively, allocate all flexible interior height to the chart,
then one row to statistics, one blank row, and one row to the legend. The chart
uses a vertical `│` axis, a `└` corner, a horizontal `─` axis, and a
Braille-marker line connecting the WPM points. The axes and Braille markers use
the terminal's default foreground and have no text attributes.

The x-axis title is exactly `seconds`; its bounds are from 1 to the last point's
bucket, with the upper bound forced to at least 1. Its endpoint labels are `1`
and the duration formatted with two decimal digits. The y-axis title is exactly
`wpm`; its bounds are 0 to the rounded highest point, and those two bounds are
the labels. The numeric endpoint labels are bold, while the `seconds` and `wpm`
titles are unstyled. Even an empty data set renders both axes.

The centered stats line is exactly:

```text
{wpm} wpm   {accuracy}% acc   {standard_deviation_to_2dp} sd
```

The entire statistics line is bold.

The left-aligned italic legend in the bottom content row is exactly
`(r)etry / (n)ew / (t)weet / (esc)ape`. It includes `(t)weet` even when
`BROWSER=/bin/false` and neither `DISPLAY` nor `WAYLAND_DISPLAY` is present. The
results screen remains stable over time.

## Spec 18

At 80x24, a one-point finite result with `36` WPM, 100% accuracy, 0 deviation,
and duration clamped to 1 has this layout after stripping ANSI styles. There are
exactly 24 rows; the code block preserves the leading two, intervening, and final
blank rows:

```text


     36│wpm
       │
       │
       │
       │
       │
       │
       │
       │
       │
       │
       │
       │
       │
     0 │                                                            seconds
       └───────────────────────────────────────────────────────────────────
       1                                                               1.00
                           36 wpm   100% acc   0.00 sd

     (r)etry / (n)ew / (t)weet / (esc)ape


```

Axis indentation adapts to the width of the maximum label (`0│wpm` for maximum
0, `inf│wpm` for infinity, `108│wpm` for a three-character maximum). In an
80-column zero result, the stats line is centered as
`0 wpm   0% acc   0.00 sd`. In an infinite result it is centered as
`inf wpm   100% acc   0.00 sd`.

Narrow terminals must not panic. At 30x10, initial prompt `test narrow` is
centered on row 5. Its very-fast perfect result, after stripping styles, is:

```text


     inf│
        └────────────────
        1            1.00
     inf wpm   100% acc

     (r)etry / (n)ew / (t


```

At 20x10, `hi` is centered on row 5 and the correspondingly clipped result is:

```text


     inf│
        └──────
        1   1.0
     inf wpm

     (r)etry /


```

Clipping is at terminal boundaries; it is not an error.

## Spec 19

When a test is calculated after completion or timeout, append one history record
to the platform configuration log. On Linux, if `XDG_CONFIG_HOME` is set to
`D`, the path is exactly `D/thokr/log.csv`; otherwise use the platform's normal
per-user configuration directory (typically `$HOME/.config/thokr/log.csv`).
Create missing parent directories and the file.

The first line of a new file is exactly:

```text
date,num_words,num_secs,elapsed_secs,wpm,accuracy,std_dev
```

It is written only once. Preserve existing content and append one row per newly
calculated test, both across processes and after starting another test in the
same process. Every row is valid CSV with exactly seven fields and no trailing
comma:

1. `date`: a nonempty, human-readable local date/time string (not numeric epoch).
2. `num_words`: the configured word count in word/custom mode; explicit `-w N`
   must record `N`.
3. `num_secs`: empty for untimed tests, otherwise the configured limit with two
   decimal digits (for example `5.00`).
4. `elapsed_secs`: real elapsed seconds with exactly two decimal digits.
5. `wpm`: exactly the rounded value shown on screen, including `inf` if applicable.
6. `accuracy`: the 0–100 rounded percentage shown on screen.
7. `std_dev`: the calculated population deviation with exactly two decimal digits.

Do not create a result row merely for launching and quitting an unfinished test.
Already-finished zero-length prompts may display zero results without requiring
a timing/log calculation.

## Spec 20

The executable must support real PTY/TTY operation under terminal automation:
startup content becomes visible within roughly half a second, individual
keypress redraws within a few tenths of a second, and Escape terminates promptly.
It must handle at least 80x24, 120x30/40, 30x10, and 20x10 terminals. Long
prompts and generated word/sentence text may occupy many wrapped lines but must
not be truncated by an internal string limit or crash due to layout arithmetic.

The state transitions are:

```text
typing --prompt consumed or timer expires--> results
typing --Left--> fresh typing, same prompt
typing --Right--> fresh typing, new prompt
results --r/Left--> fresh typing, same prompt
results --n/Right--> fresh typing, new prompt
typing/results --Escape--> clean exit 0
```

Each fresh typing state resets input, timestamps, graph points, WPM, accuracy,
deviation, and countdown. This state model, the rendering rules above, and the
CSV side effect must work together in one long-running session as well as in
separate invocations.
