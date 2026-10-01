# CMatrix executable specification

The required artifact is a directly runnable file named exactly `executable`. It is a terminal program which presents a Matrix-style animated character rain. The requirements below describe its complete externally observable contract.

## Spec 1

`executable` implements a traditional, top-level Unix short-option interface; it has no subcommands. Invocations such as `add`, `remove`, `list`, `show`, `init`, `help`, `version`, or any other non-option word are not commands. Positional operands are otherwise tolerated and ignored, so if terminal initialization is possible the program proceeds to its animation. A standalone `--` ends option processing, and later words are positional operands.

Short options may be separate or grouped, so forms such as `-a -b`, `-ab`, `-abc`, `-lba`, and `-abnV` are valid. Options which take a value accept either a following argument or an attached value where conventional short-option parsing permits it; for example, both `-u 4` and `-u4` work. Repeating an option is safe. Except for the terminating informational/error cases described below, options can be freely interleaved.

## Spec 2

The following invocations print the canonical help text from Spec 3 to standard output and terminate successfully with status 0:

- `-h`, `-?`, and `--help`;
- any unknown option, including unknown short options such as `-z` or `-Z` and unknown long options such as `--version` or `--nonexistent`;
- a value-taking option which has no value: `-C`, `-u`, `-M`, or `-t` at the end of the option list.

These cases produce no diagnostic on standard error. Help and version options are processed from left to right and terminate processing immediately: for example, `-V -h` prints version information, while `-h -V` prints help. Recognized non-terminating flags may precede either one. Help/version output must not initialize the terminal UI.

## Spec 3

The canonical help output is exactly the following 21 lines, including the single leading space on every line, capitalization, punctuation, line breaks, and one final newline. It contains no terminal-control or ANSI escape sequences.

```text
 Usage: cmatrix -[abBcfhlsmVxk] [-u delay] [-C color] [-t tty] [-M message]
 -a: Asynchronous scroll
 -b: Bold characters on
 -B: All bold characters (overrides -b)
 -c: Use Japanese characters as seen in the original matrix. Requires appropriate fonts
 -f: Force the linux $TERM type to be on
 -l: Linux mode (uses matrix console font)
 -L: Lock mode (can be closed from another terminal)
 -o: Use old-style scrolling
 -h: Print usage and exit
 -n: No bold characters (overrides -b and -B, default)
 -s: "Screensaver" mode, exits on first keystroke
 -x: X window mode, use if your xterm is using mtx.pcf
 -V: Print version information and exit
 -M [message]: Prints your message in the center of the screen. Overrides -L's default message.
 -u delay (0 - 10, default 4): Screen update delay
 -C [color]: Use this color for matrix (default green)
 -r: rainbow mode
 -m: lambda mode
 -k: Characters change while scrolling. (Works without -o opt.)
 -t [tty]: Set tty to use
```

## Spec 4

`-V` prints version information to standard output, produces nothing on standard error, exits with status 0, and does not initialize the UI. It starts with a single leading space and has this three-line shape, with a final newline:

```text
 CMatrix version 2.0 (compiled HH:MM:SS, Mon DD YYYY)
Email: abishekvashok@gmail.com
Web: https://github.com/abishekvashok/cmatrix
```

The text `HH:MM:SS, Mon DD YYYY` denotes a real compile/build timestamp rendered in the conventional C date/time style (for example, `20:15:26, Mar  5 2026`; a one-digit day is space-padded). The invariant fields are the product name `CMatrix`, version `2.0`, the exact email address, and the exact HTTPS project URL. The version output must contain the word `compiled` and must differ from the help text.

## Spec 5

After parsing a normal invocation which does not contain `-l`, the program initializes a terminal-capability-based full-screen interface. The `-l` Linux-font path is the terminating special case specified in Spec 8. Common terminal types including `xterm`, `xterm-256color`, `linux`, `vt100`, `dumb`, and `screen` must not affect help or version output. `-f` selects Linux terminal behavior internally and is accepted regardless of the inherited `TERM` value.

If a normal invocation cannot initialize the terminal because the terminal type is missing or unusable, it must fail promptly with nonzero status and a diagnostic of the form `Error opening terminal: TYPE.` followed by a newline. When no usable type is available, the observable diagnostic is exactly `Error opening terminal: unknown.`. The diagnostic may be written to standard error. Do not reject an invocation merely because its output is captured rather than attached to a physical terminal: with a supported `TERM` such as `xterm`, it must enter the render loop and continue until interrupted.

## Spec 6

On a compatible terminal, the UI switches to the alternate screen, hides the cursor, and begins drawing without requiring input. For an xterm-like terminal the emitted setup stream includes `ESC [?1049h` and `ESC [?25l` without the spaces shown here (that is, byte strings `\x1b[?1049h` and `\x1b[?25l`). On normal or interrupted shutdown it restores terminal state, makes the cursor usable again, and leaves the alternate screen; the xterm-compatible output includes `\x1b[?1049l`.

Except for the terminating `-l` behavior in Spec 8, the process remains running in its render loop rather than exiting by itself. In ordinary, non-locked modes, receipt of an interrupt such as Ctrl-C/SIGINT terminates it promptly after restoring the terminal. Locked mode (`-L`) deliberately ignores SIGINT: after receiving it, the process continues rendering and remains alive for longer than two seconds. This applies both to `-L` alone and to locked mode with either the default or a custom `-M` message.

## Spec 7

The full-screen presentation is a continuously changing Matrix-rain animation, not a static banner. It fills the screen with many non-space glyphs arranged in vertically moving streams, with blank gaps between streams. A typical 80-by-24 or 120-by-40 terminal must show substantially more than a token amount of output within about 300 ms, and captured pane contents must change again within a fraction of a second. Animation continues indefinitely until an applicable exit event.

Glyphs may be randomized on each run. Ordinary mode uses Matrix-like letters, digits, symbols, and/or Japanese-style glyphs, with brighter stream heads and dimmer tails. Every normal option combination which does not contain `-l` must continue to produce a nonempty changing screen; combinations containing `-l` instead follow the deterministic terminating path in Spec 8.

## Spec 8

The boolean display options are accepted both separately and in grouped short-option form:

- `-a` selects asynchronous streams, whose columns advance independently;
- `-o` selects old-style scrolling;
- `-c` selects the original/Japanese character repertoire;
- `-r` selects rainbow coloring;
- `-m` selects lambda mode, using lambda glyphs for the rain;
- `-k` makes already-visible characters change while they scroll;
- `-l` requests Linux-console/font mode;
- `-x` selects X-window font/layout mode;
- `-f` forces Linux terminal handling;
- `-s` selects screensaver input behavior;
- `-L` selects the locked presentation.

The options are syntactically composable. Combinations which do not contain `-l`, such as asynchronous plus bold plus rainbow or color plus update delay, enter the live render loop without an option error.

In this executable, every normal invocation containing `-l` takes a deterministic font-tool conflict path rather than rendering rain. It enters and then cleans up the terminal UI, writes exactly the following one-line diagnostic to standard error (including its leading space and final newline), produces terminal setup/cleanup control bytes on standard output, and exits with status 0:

```text
 Unable to use both "setfont" and "consolechars".
```

This behavior applies to `-l` by itself and when it is grouped with other display flags. In particular, `-lba`, `-ol`, and `-aobBnkcrmlx` all follow this same early-exit path and never begin the animation.

## Spec 9

Character intensity has three modes. The default and `-n` use no random bold highlighting; `-b` enables occasional bold characters; `-B` makes all rain characters bold. `-B` supersedes `-b`, and `-n` supersedes both `-b` and `-B`. Combining or repeating these options must remain valid. When followed by `-V` or `-h`, every such combination terminates with the requested informational output rather than starting the UI.

## Spec 10

`-C COLOR` chooses the base rain color. The accepted names are `green`, `red`, `blue`, `white`, `yellow`, `cyan`, `magenta`, and `black`; matching is case-insensitive, so mixed and upper-case spellings such as `ReD` and `GREEN` are also accepted. Green is the default. Repeated `-C` options are permitted, with the last value becoming the current selection. `-r` may be combined with `-C` and enables varying rainbow colors during rendering.

An unrecognized color, including an empty string, is rejected immediately, before terminal initialization or later options are processed. The program exits with status 0, writes nothing to standard output, and writes exactly this two-line diagnostic to standard error, including leading spaces and the final newline:

```text
 Invalid color selection
 Valid colors are green, red, blue, white, yellow, cyan, magenta and black.
```

Partial names and substrings such as `gre` and `reen`, numeric strings, and unrelated names such as `purple` are invalid.

## Spec 11

`-u DELAY` consumes one argument and controls update speed. The documented useful range is the integer values 0 through 10, inclusive, with default 4; 0 is fastest and larger values slow the update. All eleven documented values must enter the render loop, and attached syntax such as `-u4` is accepted. Repeated update options are safe and the last one controls subsequent rendering.

Delay conversion follows permissive C-style decimal integer parsing: an initial decimal portion is used, so values such as `3.5` behave like 3 and a value with no initial digits behaves like 0. Delay parsing itself must not crash. If a later `-V` or `-h` is encountered, that informational option still prints normally.

## Spec 12

`-M MESSAGE` consumes exactly the next argument as a message. The argument may be empty or may contain spaces, quotes, punctuation, equals signs, tabs, newlines, Unicode, emoji, or thousands of characters without causing a crash. In the UI, a nonempty message is overlaid visibly around the center of the terminal; for example, `-M "TEST MESSAGE"` must leave `TEST` or `MESSAGE` visible in a captured pane while rain continues around it. Text which does not fit may be safely clipped to terminal width.

In locked presentation mode, `-L` supplies a visible default message containing wording such as `Computer locked`; a supplied `-M` is the custom message rather than the default. Message handling must remain compatible with the other display and color options.

## Spec 13

With `-s`, the application is in screensaver mode. It first initializes the alternate screen and begins drawing normally. The first keyboard input then causes prompt termination and terminal restoration, regardless of which character was pressed; both `q` and an arbitrary printable key must work. This shutdown must be quick enough for a controlling terminal to observe that the program has returned within approximately 300 ms.

## Spec 14

In ordinary interactive mode, keyboard input is polled without pausing the animation. The following keys change live settings and must never terminate or corrupt the renderer merely because they are pressed:

- `a` toggles asynchronous scrolling;
- `b`, `B`, and `n` select random-bold, all-bold, and no-bold intensity modes;
- digits `0` through `9` select the corresponding update delay;
- `!`, `@`, `#`, `$`, `%`, `^`, and `&` select red, green, yellow, blue, magenta, cyan, and white, respectively;
- `)` leaves the current base color unchanged and the renderer continues running. In particular, it does not select ANSI black.

These keys may be sent rapidly or in arbitrary sequences. Other unbound input is ignored safely and the changing animation continues.

## Spec 15

`-t TTY` consumes a path naming the terminal device/output to use. The value is accepted as opaque option data rather than being rejected merely because it is not itself a terminal device. Parsing the option does not terminate the program, and it is compatible with informational flags; for example, `-t /dev/null -V` prints version information. With a supported `TERM`, even a normal `-t /dev/null` invocation proceeds into the render loop. If terminal initialization later fails (including in an invocation which names a nonexistent path), it must fail promptly and gracefully with a nonzero status and/or an error diagnostic; it must not crash from invalid memory access.

## Spec 16

All informational and argument-error output is ordinary UTF-8 text. Help and version output go exclusively to standard output; invalid-color and terminal-initialization diagnostics go to standard error. Informational output never contains curses setup/cleanup bytes. The render stream, by contrast, intentionally contains terminal control sequences and drawn character data.

The executable must tolerate rapid startup and interruption, restore terminal settings on every controlled exit path, and avoid emitting messages containing the word `error` during successful initialization of the supported display modes.
