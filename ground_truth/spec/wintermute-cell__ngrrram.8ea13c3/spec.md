# Specification for 'executable'

'executable' is a local, offline command-line typing-practice program. It parses lesson options and, for a valid invocation, runs an interactive terminal UI (TUI). All text is UTF-8. The requirements below are the complete behavioral contract.

## Spec 1

The deliverable is one file named exactly 'executable' in the repository root. It must be directly executable on Linux and must not require project source files or a build step at evaluation time. It may use ordinary terminal facilities and harness-provided commands, but must not depend on test data, golden files, or network access.

With help or invalid arguments it behaves as a noninteractive CLI. With valid lesson arguments it starts the TUI if attached to a terminal. Output stream placement, status codes, and final newlines below are significant.

## Spec 2

Both '--help' and '-h' exit status 0, write nothing to stderr, and write exactly the following to stdout, including the final newline and without ANSI escapes:

~~~text
Usage: executable [OPTIONS]

Options:
  -n, --n <2|3|4|w|file>  use bi-(2), tri-(3), tetragrams(4), (w)ords or comma separated wordlist file. [default: 2]
  -t, --top <1-200>       use the top X ngrams ordered by usage. [default: 50]
  -c, --combi <1-200>     how many different ngrams to use in a single lesson. [default: 2]
  -r, --rep <number>      how often to repeat *each* different ngram in a lesson. [default: 3]
  -w, --wpm <number>      the wpm threshold at which the lesson is considered a success. [default: 40]
  -a, --acc <0-100>       the accuracy in percent at which the lesson is considered a success. [default: 94]
      --emu-in <layout>   your current keyboard layout. only needed if you want to emulate a different layout. see docs for supported layouts. [default: ]
      --emu-out <layout>  the layout you want to emulate. only needed if you want to emulate a different layout. see docs for supported layouts. [default: ]
      --show-ortho        show keyboard in ortholinear format
      --nokb              pass this flag to disable the keyboard layout display.
      --cat               the most important flag. don't practice alone.
  -h, --help              Print help
~~~

## Spec 3

The value-taking options are '-n'/'--n', '-t'/'--top', '-c'/'--combi', '-r'/'--rep', '-w'/'--wpm', '-a'/'--acc', '--emu-in', and '--emu-out'. Switches are '--show-ortho', '--nokb', and '--cat'. Options can be interleaved and short/long forms mixed. Long values accept '--name value' and '--name=value'. Numeric short options accept '-t 50', '-t50', and '-t=50'.

Each value-taking option is single-use; repeating '--top' is a parse error containing 'cannot be used multiple times'. Switches take no value; '--cat=true' is a parse error containing 'unexpected value 'true' for '--cat' found'. There are no positional arguments. '--' stops option interpretation but does not allow positionals: '-- --help' and '-- -n' report the following token as unexpected.

Encountering help produces Spec 2 immediately. Thus '--help --n 3' succeeds, and a leading '--help' also takes precedence over a later unknown option. Help does not initialize a terminal or require a nonempty wordlist.

## Spec 4

Parser failures exit status 2, write the diagnostic to stderr, and do not start the TUI. Unknown options, including '--version', use this exact shape, substituting the token:

~~~text
error: unexpected argument '--unknown-flag' found

Usage: executable [OPTIONS]

For more information, try '--help'.
~~~

A present option without a value uses this shape:

~~~text
error: a value is required for '--combi <1-200>' but none was supplied

For more information, try '--help'.
~~~

Use the canonical long name and help metavar even if a short form was supplied: '--top <1-200>', '--rep <number>', '--wpm <number>', '--acc <0-100>', '--emu-in <layout>', '--emu-out <layout>', or '--n <2|3|4|w|file>'.

Numeric values are decimal integers only. Nonintegers use this shape, with the corresponding option/metavar:

~~~text
error: invalid value 'abc' for '--top <1-200>': invalid digit found in string

For more information, try '--help'.
~~~

A separated negative such as '--acc -1' is parsed as unexpected argument '-1'. An equals-attached negative such as '--acc=-1' or '--top=-5' reaches range validation.

## Spec 5

Defaults are n=2, top=50, combi=2, rep=3, wpm=40, acc=94, empty input/output layout names, and false for all display switches.

Top, combi, rep, and wpm accept every integer 1 through 200 inclusive. Accuracy accepts 0 through 100 inclusive. Valid endpoints and combinations proceed to TUI initialization. Combi need not be at most top; independently valid values are accepted together.

## Spec 6

After syntactic parsing, a range failure exits status 1 and prints exactly one applicable line to stdout with an ending newline:

~~~text
Invalid argument for top. Use a number between 1 and 200.
Invalid argument for combi. Use a number between 1 and 200.
Invalid argument for rep. Use a number between 1 and 200.
Invalid argument for wpm. Use a number between 1 and 200.
Invalid argument for acc. Use a number between 0 and 100.
~~~

Each line above is an alternative, not a multi-line combined message. Short and long forms behave identically. If several values are invalid, stop after the first in this order: top, combi, rep, wpm, acc, then the emulation-pair rule. For example, '--top 300 --acc 150' reports only top; invalid wpm and acc with all earlier values valid reports only wpm.

## Spec 7

'--emu-in' and '--emu-out' form a pair. Both empty means no emulation. Exactly one nonempty value exits status 1 and writes exactly:

~~~text
You need to specify both emu_in and emu_out.
~~~

If both are supplied, any strings parse. Recognized, case-sensitive names are 'qwerty', 'qwertz', 'azerty', 'dvorak', 'colemak', and 'colemakdh'. An unrecognized or differently cased name silently denotes QWERTY. Two explicitly empty strings behave as defaults. Same-layout and every cross-layout pair work.

## Spec 8

The n selector chooses a source. '2', '3', '4', and 'w' select built-in bigrams, trigrams, tetragrams, and words. Every other nonempty value is a filesystem path, not an invalid enum.

Relative and absolute paths work. If the path is not a readable regular file, exit status 1 and write exactly 'File not found: VALUE\n' to stdout, preserving VALUE. A zero-byte file is acceptable while processing help, but a normal run with it must terminate nonzero instead of entering a usable lesson.

Read custom files as UTF-8. Split entries at commas and line endings; line endings do not remain in entries. Preserve internal spaces and Unicode. Do not apply CSV quote rules. A trailing comma creates an empty entry and must not crash. A file containing only commas displays an empty/whitespace-only lesson while retaining the rest of the UI.

Examples: 'abc,def,ghi\njkl,mno,pqr\nstu,vwx' gives those eight entries; 'hello world,foo bar,test phrase' preserves three phrases; and 'café,naïve,résumé,日本語,中文' preserves five Unicode entries.

## Spec 9

For every source, top restricts the candidate pool to at most its first top entries in source order. The first ten built-in bigrams are exactly:

~~~text
th he in er an re on at en nd
~~~

There must be at least 200 built-in lowercase alphabetic bigrams; subsequent entries can be other common two-letter sequences. The trigram and tetragram sources likewise have at least 200 lowercase alphabetic entries of exactly three and four characters. The built-in word source has at least 200 nonempty lowercase alphabetic words and includes differing lengths.

A lesson makes exactly combi random draws from the restricted pool with replacement: each position is chosen independently, so the same entry can occupy multiple positions and some pool members can be absent even when combi equals or exceeds the pool size. It then repeats that drawn combi-entry sequence rep times in cyclic order, with single spaces between occurrences and a logical trailing space. Defaults display six tokens as three repetitions of a two-draw sequence, such as 'de ou de ou de ou'; the two draws can also be equal. Randomness need not be reproducible, but every token must be from the restricted pool. A pool smaller than combi is not a validation error and continues to supply all combi draws with replacement.

For a file beginning word0000, word0001, and so on, '--top 20' may only produce word0000 through word0019, even in a 1,500-entry file.

## Spec 10

A valid non-help invocation starts an interactive full-screen terminal application. In a pseudo-terminal it draws within 0.5 seconds and keeps processing input. Enter the alternate screen using an escape containing ESC[?1049h, use event-driven input, redraw after changes, and restore the terminal on exit.

With piped stdin or no usable controlling terminal, fail promptly and nonzero rather than hanging. The attempt must either put the alternate-screen escape on stdout or an 'Error:' diagnostic on stderr. Stderr must explain a terminal/device failure and must not contain a semantic validation error. In particular, both '-n w' and '--n w' without a usable terminal exit status 1, write exactly ESC[?1049h (the bytes `\x1b[?1049h`) to stdout, and write exactly the following line to stderr:

~~~text
Error: Os { code: 6, kind: Uncategorized, message: "No such device or address" }
~~~

This applies to all valid modes, numeric endpoints, layout pairs, nonempty custom files, and display-switch combinations.

## Spec 11

The initial TUI is a Unicode box-drawn panel visible in 80-column and larger terminals. Its stable content and order are:

~~~text
╭───────────────────────────────────────────────────────────────── Quit <esc> ╮
│                                  ngrrram!   by winterveil                   │
│─────────────────────────────────────────────────────────────────────────────│
│    Lesson #1                                                  ✔: 0, ✘: 0    │
│─────────────────────────────────────────────────────────────────────────────│
│                                                                             │
│                  <lesson text in its one-row viewport>                    │
│                         <centered typed/error text>                         │
                         <keyboard, unless disabled>
│─────────────────────────────────────────────────────────────────────────────│
│  need >=  40WPM,   avg.   0WPM,   last   0WPM                               │
│  need >=  94% Acc, avg.   0% Acc, last   0% Acc                             │
╰─────────────────────────────────────────────────────────────────────────────╯
~~~

The lesson line is exactly three screen rows after the 'Lesson #N' row, allowing it to be located predictably. At the 80-column evaluation size it is a one-row, 77-column viewport and never wraps. If the complete logical lesson text fits, center it while counting its logical trailing space as part of the centered text. Consequently the 17 visible characters produced by '--top 1' have 29 spaces before them and 31 after them, exactly:

~~~text
│                             th th th th th th                               │
~~~

If the logical lesson is longer than 77 terminal columns, left-align it and display only its first 77 columns; the remainder stays part of the logical typing target but is not displayed. Clipping is by column and can cut an entry rather than stopping at a token boundary. Thus 200 two-character draws expose 26 complete tokens; 200 three-character draws expose 19 complete tokens plus the first character of the twentieth; 200 four-character draws expose 15 complete tokens plus the first two characters of the sixteenth. A 28-token lesson of two-character entries exposes its first 26 tokens, eight-character entries expose eight complete tokens plus the first five characters of the ninth, and three-character entries expose 19 complete tokens plus the first character of the twentieth.

Initially the typed/error row is blank. Numeric fields are right-aligned to width three: WPM 1 appears as 'need >=   1WPM', and accuracy 50 as 'need >=  50% Acc'.

## Spec 12

By default render QWERTY. With emulation render the output layout regardless of input. Exact key rows are:

~~~text
qwerty
q w e r t y u i o p [ ]
a s d f g h j k l ; '
z x c v b n m , . /

qwertz
q w e r t z u i o p ü +
a s d f g h j k l ö ä
y x c v b n m , . -

azerty
a z e r t y u i o p ^ $
q s d f g h j k l m ù
w x c v b n , ; : !

dvorak
' , . p y f g c r l / =
a o e u i d h t n s -
; q j k x b m w v z

colemak
q w f p g j l u y ; [ ]
a r s t d h n e i o '
z x c v b k m , . /

colemakdh
q w f p b j l u y ; [ ]
a r s t g m n e i o '
z x c d v k h , . /
~~~

Each key is lowercase where applicable and occupies a cell formatted '│ x '. The staggered keyboard at an 80-column panel has exactly this geometry (QWERTY labels shown):

~~~text
│             ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐               │
│             │ q │ w │ e │ r │ t │ y │ u │ i │ o │ p │ [ │ ] │               │
│             └┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┘               │
│              │ a │ s │ d │ f │ g │ h │ j │ k │ l │ ; │ ' │                  │
│              └┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┘                  │
│               │ z │ x │ c │ v │ b │ n │ m │ , │ . │ / │                     │
│               └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘                     │
~~~

Substitute only the labels for other layouts. Top, middle, and bottom have 12, 11, and 10 keys, with the latter rows indented one and two extra columns. Border characters and surrounding spaces are exact. The spacebar is implicit and need not be labeled.

## Spec 13

'--show-ortho' produces a rectangular 12-column ortholinear keyboard. Preserve the chosen output layout's keys and pad the middle row with one '△' and bottom row with two. At 80 columns QWERTY is exactly:

~~~text
│             ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐               │
│             │ q │ w │ e │ r │ t │ y │ u │ i │ o │ p │ [ │ ] │               │
│             ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤               │
│             │ a │ s │ d │ f │ g │ h │ j │ k │ l │ ; │ ' │ △ │               │
│             ├───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┼───┤               │
│             │ z │ x │ c │ v │ b │ n │ m │ , │ . │ / │ △ │ △ │               │
│             └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘               │
~~~

Dvorak and the other layouts substitute their Spec 12 keys into the same geometry. '--nokb' takes precedence and suppresses either keyboard form.

## Spec 14

Without emulation, input is used as typed. With emulation, find each typed character's physical position in the flattened emu-in rows from Spec 12 and translate it to the character at that position in emu-out. The target and displayed keyboard use emu-out. QWERTY fallback applies to an unknown name. Equal layouts are identity mappings. Mapping works generically in either direction and between two non-QWERTY layouts.

For a one-character apostrophe lesson with Dvorak output, there is a completion edge case. With '--emu-in qwerty --emu-out dvorak', typing 'q' supplies the mapped apostrophe, but a following space does not finish the lesson: the display remains 'Lesson #1' with '✔: 0, ✘: 0'. The same behavior occurs when the input name is unrecognized and therefore falls back to QWERTY, for example '--emu-in UNKNOWN --emu-out dvorak'.

## Spec 15

'--nokb' removes all keyboard rows but leaves the panel, title, lesson, counters, thresholds, and statistics usable. Its screen has materially fewer box characters than normal. It composes with emulation, ortholinear mode, cat mode, and numeric/lesson options.

'--cat' adds a visible cat beside the keyboard without hiding the lesson or keyboard. At an 80-column terminal with the keyboard enabled, its visible fragments are these, in order; the sixth row crosses the panel separator, the seventh shares the WPM row, and the eighth shares the accuracy row:

~~~text
 /\_/\
>(•༝• )<
 |    \
 || |  )
 ll-l-//
/▔▔▔▔▔▔▔▔||▔▔\
 \\
 V
~~~

At normal size it is right of a keyboard shifted left. With '--cat --nokb' at 80 columns, the shortened panel clips the cat after only these first three visible fragments: '/\_/\' on the WPM row, '>(•༝• )<' on the accuracy row, and '|    \' crossing the bottom border. The remaining cat rows are not visible.

## Spec 16

Timing begins on the first ordinary typed character. Compare each accepted character with the target at that logical position after layout mapping and redraw immediately. Correct target characters stay legible and may be colored. Incorrect accepted characters appear on the separate typed/error row; entering 'xxx' must produce a framed line containing 'xxx'. If an expected space is wrong, show a visible bullet '•' at the target position. A printable character that is absent from the active input keyboard layout is ignored as lesson input: in the default QWERTY mode, entering '?' redraws but does not advance the logical position and does not display '?' on the typed/error row. It must not crash or close the program.

Backspace deletes one character and redraws; deleting all of 'xxx' removes it from the screen. Ctrl-H deletes backward through the current word to the preceding space, preserving that space. Typing can continue afterward and changes the screen.

## Spec 17

Except for the Dvorak-apostrophe emulation edge case in Spec 14, completing the full target, including its logical trailing space, finishes exactly one lesson. Increment 'Lesson #1' to '#2', increment exactly one of ✔ or ✘ so their sum rises by one, generate a new lesson, clear current input, and update last/average statistics. In that edge case, mapped 'q' followed by space leaves the lesson and both counters unchanged.

Accuracy is the integer-truncated percentage of correct counted key events. Each accepted ordinary character is one counted event and is correct exactly when it matches the target at that logical position. A Backspace that deletes an entered character is also a counted correct event, even when the deleted character was wrong. Thus entering wrong 'x', deleting it with Backspace, and then entering the correct 't', 'h', and trailing space produces four correct events out of five and reports '80% Acc'. Compute WPM from elapsed time with each five non-space target characters counting as one word. The timer begins on first input, not initial drawing. Success requires both WPM and accuracy to meet configured thresholds; otherwise count failure. A rapidly completed nonempty lesson has nonzero last/average WPM. Initially all last and average values are zero. Average summarizes completed lessons and last describes the latest.

## Spec 18

Escape exits promptly and cleanly with status 0, restoring terminal mode/screen without requiring a harness to kill it. Ctrl-C also terminates promptly, with either a normal or signal status acceptable, and restores the terminal as far as possible.

All valid features compose: all built-in and nonempty custom sources start; numeric options work together at endpoints; any recognized layout pair starts; and cat, nokb, and ortholinear switches work singly or combined. After startup, a capture contains 'Lesson', lowercase lesson content for nonempty sources, and WPM/accuracy labels, and remains responsive across multiple typing cycles.
