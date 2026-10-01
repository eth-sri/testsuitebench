# Kiro executable specification

The required artifact is a single executable file named `executable`. It implements Kiro 0.4.3, a small, modeless UTF-8 text editor for Unix-like terminal emulators. All paths, text, screen positions, and key effects described below are externally observable requirements. “Line” and “column” positions are one-based when displayed to the user, although an implementation may represent them differently internally.

## Spec 1

`executable` must be directly runnable as a Unix process. Its command-line form is:

```text
executable [options] [FILES...]
```

With no informational option, it must start an interactive full-screen editor on its controlling terminal. Zero file arguments create one unnamed in-memory buffer. Each positional file argument creates one buffer, in argument order, and the first buffer is initially current. A literal `--` ends option parsing; subsequent strings, including strings beginning with `-`, are filenames. A filename of `-` is an ordinary filename, not a request to read standard input. Paths containing spaces, punctuation, or UTF-8 characters are valid.

The TUI requires a terminal. If invoked without a TTY on standard input, with or without positional filenames, it must write an `Error:` line to standard error, write nothing to standard output, and exit with status 1. On Linux the diagnostic must include `Inappropriate ioctl for device` (normally `Error: Inappropriate ioctl for device (os error 25)\n`).

## Spec 2

The supported informational options are `-v`, `--version`, `-h`, and `--help`. `-v` and `--version` print exactly the following UTF-8 bytes to standard output, print nothing to standard error, and exit successfully without starting the TUI:

```text
0.4.3
```

The output has exactly one terminating newline and no prefix or trailing spaces. Version takes precedence over help and positional files when one version option and one help option are both present. Help likewise ignores positional files. Combined short options are accepted, so `-vh` behaves as a version request.

Repeating the same logical option is an error, including mixing its aliases: examples are `--version --version`, `-v --version`, `--help --help`, and `-h --help`. Such errors exit with status 1 and an `Error:` diagnostic on standard error that says the option occurred `more than once`.

Any other option exits with status 1, produces no standard output, and emits a newline-terminated UTF-8 diagnostic on standard error. It must start with `Error:`, contain `Unrecognized option`, identify the option without leading dashes in single quotes (for example `'Z'` and `'nonexistent-flag'`), and recommend `--help`. An attached value on an otherwise recognized valueless option is a different error category: `--version=1.0` exits with status 1, writes nothing to standard output, and writes exactly `Error: Option 'version' does not take an argument. Please see --help for more details\n` to standard error.

## Spec 3

`-h` and `--help` must print the same text, substituting the process's `argv[0]` verbatim in the two marked locations. Thus invocation as `./executable` begins `./executable:`, while invocation by absolute path begins with that absolute path. There is no standard-error output, the exit status is 0, and the blank line after the final option is part of the output (the last text line is followed by two newline bytes).

```text
{argv0}: A tiny UTF-8 terminal text editor

Kiro is a tiny UTF-8 text editor on terminals for Unix-like systems.
Specify file paths to edit as a command argument or run without argument to
start to write a new text.
Help can show up with key mapping Ctrl-?.

Usage:
    {argv0} [options] [FILES...]

Mappings:
    Ctrl-Q                        : Quit
    Ctrl-S                        : Save to file
    Ctrl-O                        : Open text buffer
    Ctrl-X                        : Next text buffer
    Alt-X                         : Previous text buffer
    Ctrl-P or UP                  : Move cursor up
    Ctrl-N or DOWN                : Move cursor down
    Ctrl-F or RIGHT               : Move cursor right
    Ctrl-B or LEFT                : Move cursor left
    Ctrl-A or Alt-LEFT or HOME    : Move cursor to head of line
    Ctrl-E or Alt-RIGHT or END    : Move cursor to end of line
    Ctrl-[ or Ctrl-V or PAGE DOWN : Next page
    Ctrl-] or Alt-V or PAGE UP    : Previous page
    Alt-F or Ctrl-RIGHT           : Move cursor to next word
    Alt-B or Ctrl-LEFT            : Move cursor to previous word
    Alt-N or Ctrl-DOWN            : Move cursor to next paragraph
    Alt-P or Ctrl-UP              : Move cursor to previous paragraph
    Alt-<                         : Move cursor to top of file
    Alt->                         : Move cursor to bottom of file
    Ctrl-H or BACKSPACE           : Delete character
    Ctrl-D or DELETE              : Delete next character
    Ctrl-W                        : Delete a word
    Ctrl-J                        : Delete until head of line
    Ctrl-K                        : Delete until end of line
    Ctrl-U                        : Undo last change
    Ctrl-R                        : Redo last undo change
    Ctrl-G                        : Search text
    Ctrl-M                        : New line
    Ctrl-L                        : Refresh screen
    Ctrl-?                        : Show this help

Options:
    -v, --version       Print version
    -h, --help          Print this help

```

## Spec 4

The editor must enter terminal raw mode, use the terminal's full rectangular screen, accept keypresses without Enter, and repaint promptly. It must leave raw/full-screen mode and restore the terminal on every normal exit and fatal error. A clean, unmodified editor exits with status 0 after one `Ctrl-Q`.

The minimum usable size is 1 column by 3 rows. Starting on a smaller terminal must restore the terminal, exit with status 1, and write exactly:

```text
Error: Screen {width}x{height} is too small. At least 1x3 is necessary in width x height
```

For example, a 10-column by 2-row terminal produces `Error: Screen 10x2 is too small. At least 1x3 is necessary in width x height\n`.

## Spec 5

The screen consists of a text viewport, a reverse-video status bar, and, while a message is present, a final message/prompt row. With a message, the viewport has `height - 2` rows; without a message it expands to `height - 1` rows and the status bar occupies the last row. Every viewport row after the last visible buffer row is displayed as a single `~`. Content is shown without line-number prefixes.

The status bar's left field is:

```text
"{display-name}" - {current-buffer}/{buffer-count}{optional modified marker}
```

The display name is the supplied filename/path, or `[No Name]` for an unnamed buffer. The optional marker is exactly ` (modified)`. The right field is `{language} {cursor-line}/{logical-line-count}`. It is right-aligned, with spaces filling between fields, so the complete visible status row is exactly the terminal width. For example, at width 80 an edited unnamed one-line buffer has:

```text
"[No Name]" - 1/1 (modified)                                           plain 1/1
```

If both fields cannot fit, preserve and clip the left field to the terminal width and omit or clip the right field. The status row is rendered using reverse video (ANSI SGR 7) and terminal colors/styles are reset afterward.

## Spec 6

An initially pristine unnamed buffer displays a centered startup greeting in the viewport:

```text
Kiro editor -- version 0.4.3
```

On an 80x24 terminal it appears after the `~` on viewport row 8 as:

```text
~                         Kiro editor -- version 0.4.3
```

and the other unused viewport rows contain `~`. The initial message row is `Ctrl-? for help`. The greeting is only a startup presentation; it disappears as soon as editing or another view replaces it and does not become buffer text. The initial 80x24 screen is therefore 22 viewport rows, followed by:

```text
"[No Name]" - 1/1                                                      plain 1/1
Ctrl-? for help
```

Messages are clipped to the terminal width. Transient messages may clear after approximately five seconds; when there is no message, reclaim the message row for the viewport as described in Spec 5. Before that timeout, the initial `Ctrl-? for help` message remains visible after ordinary text insertion, cursor-only movement such as `Ctrl-E`, and opening the in-editor help view. Likewise, after Enter completes a successful search, the `Found` message remains visible across an immediately following normal-mode `Ctrl-F` cursor movement. These actions do not clear the message or reclaim its row.

## Spec 7

Existing files are read as UTF-8 without changing their stored contents, including blank lines, leading/trailing spaces, tabs, accented text, CJK text, and ordinary emoji. Display preserves those characters except for the tab presentation defined in Spec 8. A final newline is a terminator and does not create an extra displayed logical line. A nonempty final line without a newline is still a line. A zero-byte existing file has zero logical rows and status position `plain 1/0`; a new unnamed buffer or a named path that does not yet exist has one editable empty row and position `plain 1/1`.

Opening a nonexistent path must not create it until a save occurs. Opening a directory fails with exit status 1 and, on Linux, exactly `Error: Is a directory (os error 21)\n` on standard error. Files with very long lines and files of at least 1,000 lines must load without truncating or corrupting the buffer.

## Spec 8

The editor is modeless: every printable input character is inserted at the current logical cursor, and the cursor advances by one Unicode scalar value. Insertions work at the start, middle, and end of lines and on the editable row of a new buffer. UTF-8 input such as `café`, `こんにちは`, `日本`, `世界`, `犬`, and emoji must remain valid and must be inserted, rendered, searched, deleted, and saved as complete characters rather than byte fragments.

Tab is valid file and keyboard input. Pressing Tab inserts a tab character, and saving preserves that tab in the file. On screen, a tab advances to the next eight-column terminal tab stop rather than occupying one column. For example, entering `a\tb` at the start of a line displays `a       b`, while saving writes the bytes `a\tb\n`. East Asian wide characters and emoji occupy their terminal display width for cursor placement and clipping. Ordinary printable input marks the current buffer modified and removes the startup greeting.

## Spec 9

The following movement aliases must have identical effects:

- Up or `Ctrl-P`: move up one logical line, clamped at the top.
- Down or `Ctrl-N`: move down one logical line. The cursor may occupy the editable row one line past the last stored row.
- Right or `Ctrl-F`: advance one character; at end of a line, move to column 0 of the next line.
- Left or `Ctrl-B`: retreat one character; at column 0, move to the end of the previous line.
- Home or `Ctrl-A`: column 0 of the current line.
- End or `Ctrl-E`: immediately after the last character of the current line.

The xterm Alt-Left sequence `ESC [ 1 ; 3 D` instead has the ordinary Left effect of retreating one character, and Alt-Right `ESC [ 1 ; 3 C` has the ordinary Right effect of advancing one character. Thus Alt-Left from the end of `abc` followed by inserting `X` produces `abXc`, while Alt-Right from the beginning followed by inserting `X` produces `aXbc`.

Vertical movement uses the cursor column reached on the immediately preceding line; it does not retain a separate preferred column after a shorter line clamps the cursor to that line's end. For example, from the end of `abcdef`, moving down through a line containing only `x` and then down onto another `abcdef` leaves the cursor at column 1, so inserting `X` produces `aXbcdef`. Movement itself does not change file contents or set the modified marker. The status bar updates its displayed current logical line, such as `plain 3/4` after moving twice down from line 1 of a four-line file.

## Spec 10

Alt-F and Ctrl-Right perform forward-word movement; Alt-B and Ctrl-Left perform backward-word movement. Either forward alias at the start of `one-two` stops after `one` and before the dash, so inserting `X` there produces `oneX-two`. Across lines, the forward operation consumes the following word rather than stopping at its beginning: Alt-F at the end of the first row in `one\ntwo` lands on the editable third row, so inserting `X` and saving writes `one\ntwo\nX\n`. The boundary handling is not Unicode-word-aware. From the end of `café-犬`, either Alt-B or Ctrl-Left lands before `é`; inserting `X` and saving writes `cafXé-犬\n`.

Alt-N and Ctrl-Down move to the next paragraph, and Alt-P and Ctrl-Up move toward the previous paragraph; blank lines delimit paragraphs. From inside a paragraph, either previous-paragraph alias first moves to the beginning of the current paragraph. Thus, in `a\nb\n\nc\nd\n`, invoking it on line 5 moves to line 4, not line 1. Alt-`<` moves to the first line but does not reset a valid current column to column 0. For example, after Alt-`>` reaches the editable line 31 of `line1\n` through `line30\n`, inserting `X` leaves the cursor at column 1; Alt-`<` then moves to line 1 at column 1, so inserting `Y` produces `lYine1` rather than `Yline1`. Alt-`>` moves to the bottom editable position, which for an N-line file is allowed to be line N+1; for example, a 30-line file may report `plain 31/30`.

Page Down and Ctrl-V perform the next-page operation; Page Up and Alt-V perform the previous-page operation. Despite the mappings printed by the help views, sending the Ctrl-`[`/Escape byte alone has no immediate next-page effect (from line 1 of a 60-line file it remains at `plain 1/60`), but it remains an incomplete input prefix rather than becoming a completed no-op. If Page Down's `ESC [ 6 ~` sequence follows that lone byte, Page Down is not recognized: the printable suffix `[6~` is inserted into the first line, the buffer becomes modified, and the position remains `plain 1/60`. Ctrl-`]` advances rather than moving to the previous page (after an ordinarily recognized Page Down reaches line 44 of that file, Ctrl-`]` reaches the bottom editable position `plain 61/60`). The page size is the current viewport height. Kiro's page operation first places the cursor on the appropriate viewport edge and then moves it by one viewport height, clamping at the top or bottom editable position. Thus on an 80x24 screen with a 22-row viewport, Page Down from line 1 of a sufficiently long file reaches line 44, while Page Up there returns to line 1. On a 30-line file the downward operation reaches editable line 31.

## Spec 11

Enter and `Ctrl-M` split the current line at the cursor. Text before the cursor remains on the current line; text at and after the cursor becomes the next line; the cursor moves to column 0 of that next line. On an empty new buffer this produces two empty logical lines. Repeated Enter presses create repeated empty lines. Every newline insertion marks the buffer modified.

Saving serializes logical rows using Unix LF (`\n`) line endings and appends LF after every stored row. Consequently, saving text `test content` writes `test content\n`; saving `Hello World` followed by Enter and `This is line 2` writes `Hello World\nThis is line 2\n`; and an originally unterminated last line becomes newline-terminated when saved.

## Spec 12

Deletion operates on whole Unicode characters:

- Backspace and `Ctrl-H` delete the character immediately before the cursor. At column 0 of a non-first line they remove the preceding newline, append the current line to the previous line, and leave the cursor at the join.
- Delete and `Ctrl-D` delete the character at the cursor. At end of a non-last line they remove the following newline and append the next line.
- `Ctrl-W` deletes the preceding word but retains the separator immediately before it. For example, at the end of `hello world test` it leaves `hello world `, including the trailing space.
- `Ctrl-J` deletes everything from the start of the current line up to the cursor, retaining the suffix.
- `Ctrl-K` deletes from the cursor through the end of the current line. At a line boundary it may delete the line break/join the following line; clearing the only content leaves a valid editable empty state.

Boundary deletion on an empty buffer is harmless. Successful deletion sets the modified marker and updates line counts and scrolling.

## Spec 13

Every buffer independently tracks a clean point in its edit history rather than recomputing cleanliness from content equality. A text change shows ` (modified)` in that buffer's status field, and a successful save establishes a new clean history point and clears the marker. Undoing to that clean history point clears the marker; redoing away from it restores the marker. Separate inverse edits do not do so merely because their resulting bytes equal the loaded or saved bytes: after loading `abc`, inserting `X` at the end and then pressing Backspace leaves the status marked ` (modified)` even though the content is again `abc`.

`Ctrl-Q` exits immediately if every buffer is unmodified. If any buffer is modified, the first `Ctrl-Q` must keep the process alive and display exactly:

```text
At least one file has unsaved changes! Press ^Q again to quit or ^S to save
```

A second consecutive `Ctrl-Q` exits without saving. A different intervening action cancels this confirmation sequence. The warning considers all open buffers, not only the current buffer.

## Spec 14

`Ctrl-U` undoes the most recent logical editing unit in the current buffer, restoring both content and a usable cursor position. `Ctrl-R` reapplies the next undone unit. Insertions typed as one run form one logical unit across cursor-only movement: typing `hello`, moving left, and inserting `X` can be undone together. Enter or `Ctrl-M` ends the preceding insertion unit and starts a new unit consisting of the inserted newline and text subsequently typed on the new line. Therefore, typing `Line1`, pressing Enter, and immediately undoing leaves `Line1`; typing `first`, Enter, and `second`, then undoing once likewise leaves `first` as a modified one-line buffer. A deletion command is its own logical unit. Undo/redo must work for character insertion, backspace, forward delete, word deletion, line splitting/joining, and Ctrl-J/Ctrl-K deletion.

Undo with no history is a harmless no-op. Redo with no available future leaves content unchanged and displays `Buffer is already newest`. Performing a new edit after undo discards the abandoned redo future. History and cursor state are private to each buffer, and repeated undo/redo cycles must remain stable.

## Spec 15

`Ctrl-S` saves the current buffer. A named buffer is written immediately to its path, even if it was not marked modified, using the serialization in Spec 11. Saving may create a nonexistent named file and must overwrite an existing regular file with current content. The success message is:

```text
{byte-count} bytes written to {path}
```

where the count is the number of UTF-8 bytes actually written, including final newlines. The buffer becomes unmodified and retains the name.

For an unnamed buffer, `Ctrl-S` opens a bottom-row prompt exactly `Save as:  (^G or ESC to cancel)`. Typed UTF-8 text edits the prompt value, Backspace removes a character, and Enter attempts to save to that path. A successful save assigns the path as the buffer name and re-detects syntax from its extension. Ctrl-G cancels this prompt and returns to the unchanged buffer without assigning a name; save cancellation need not display a `Canceled` message. Despite the prompt text, a standalone Escape does not cancel it or redraw: the entered prompt value remains visible and the prompt remains active. While it is active, Ctrl-Q closes the prompt without saving or exiting; a following Ctrl-Q then has its normal global effect.

If writing fails, keep the buffer and its modified contents alive and display `Could not save: {operating-system error}`. A failed first save must leave the buffer unnamed. Saving to `/dev/null/readonly_file.txt` on Linux must display exactly `Could not save: Not a directory (os error 20)`.

## Spec 16

`Ctrl-O` opens the prompt:

```text
Open:  (Empty name for new text buffer, ^G or ESC to cancel)
```

Prompt text accepts arbitrary UTF-8 paths, and Backspace removes the preceding prompt character. Left and Right escape sequences do not reposition the insertion point in this prompt. For example, after typing a path ending in `file.xt`, pressing Left twice, typing `t`, pressing Right twice, typing `z`, and pressing Backspace leaves the value ending in `file.xtt`; Enter therefore opens `file.xtt`. Enter with a nonempty value appends a new buffer for that path and makes it current, loading it if it exists or creating an unsaved in-memory empty buffer if it does not. Enter with an empty value appends a new unnamed empty buffer. The prior buffers, including unsaved edits, cursor positions, histories, and names, remain intact. Ctrl-G cancels the prompt, opens nothing, returns to the original buffer, and displays `Canceled`. A standalone Escape does not cancel an Open prompt: after entering `ignored` and pressing Escape, the prompt remains active and continues to display `Open: ignored`.

`Ctrl-X` selects the next buffer and Alt-X selects the previous buffer. Both operations wrap at the ends of the buffer list. The status shows the one-based current index and total count, for example `1/2` then `2/2`. With only one buffer, either switch key keeps it current and displays exactly `No other buffer is opened`.

## Spec 17

`Ctrl-G` enters incremental search mode in the current buffer. The bottom row has this form, clipped at screen width:

```text
Search: {query} (^F or ^N or RIGHT to forward, ^B or ^P or LEFT to back, ^G or ESC to cancel)
```

The query is editable UTF-8 text. Printable input inserts into it, Backspace removes the previous query character, and a zero-length query remains a live prompt. Each query edit immediately recomputes matches, moves the editor cursor to a match when one exists, scrolls that match into view, and redraws match highlighting before Enter is pressed. Search treats punctuation such as brackets as literal text and handles accented and CJK query text.

All occurrences must be discoverable, including multiple occurrences on a single line and matches beyond the current viewport. While the prompt is active, Ctrl-F, Ctrl-N, and Right select the next occurrence; Ctrl-B, Ctrl-P, and Left select the previous occurrence. Every new press of Ctrl-G opens search with an empty query, even immediately after a completed search; the previous query is not retained.

## Spec 18

Ordinarily, Enter finishes search. If the nonempty query has a match, leave the cursor at the selected match, keep the matching line visible, close the prompt, and display `Found`. The post-SIGWINCH sequence in Spec 24 is an exception both to that result message and to logically finishing search. If the query has no match, preserve the original editor position, close the prompt, and display `Not found`. Enter on an empty query acts as cancellation.

Ctrl-G or Ctrl-Q while the search prompt is active cancels search rather than invoking the normal global meaning of that key. Cancellation restores the pre-search cursor/view, closes the prompt, and displays `Canceled`; in particular Ctrl-Q from search mode must not exit the editor. A standalone Escape does not cancel search. After a search for `target` has selected its match on line 2, pressing Escape leaves the editor alive in the `Search: target` prompt at line 2 rather than restoring line 1. Search and result navigation remain stable on long files. There is a specific zero-row exception: when the current buffer is an existing zero-byte file with status `plain 1/0`, pressing Ctrl-G does not open search. The process panics and exits with status 101. Its terminal output contains a line beginning with `thread 'main'` and ending with `panicked at src/prompt.rs:<error location>:`, followed by the line `index out of bounds: the len is 0 but the index is 0`.

## Spec 19

`Ctrl-?` (the control byte also commonly named Ctrl-underscore) opens an in-editor help view without changing buffer data. At width 80, its viewport begins with these lines, each with seven leading spaces, and continues through as many mappings as fit:

```text
       Ctrl-Q                        : Quit
       Ctrl-S                        : Save to file
       Ctrl-O                        : Open text buffer
       Ctrl-X                        : Next text buffer
       Alt-X                         : Previous text buffer
       Ctrl-P or UP                  : Move cursor up
       Ctrl-N or DOWN                : Move cursor down
       Ctrl-F or RIGHT               : Move cursor right
       Ctrl-B or LEFT                : Move cursor left
       Ctrl-A or Alt-LEFT or HOME    : Move cursor to head of line
       Ctrl-E or Alt-RIGHT or END    : Move cursor to end of line
       Ctrl-[ or Ctrl-V or PAGE DOWN : Next page
       Ctrl-] or Alt-V or PAGE UP    : Previous page
       Alt-F or Ctrl-RIGHT           : Move cursor to next word
       Alt-B or Ctrl-LEFT            : Move cursor to previous word
       Alt-N or Ctrl-DOWN            : Move cursor to next paragraph
       Alt-P or Ctrl-UP              : Move cursor to previous paragraph
       Alt-<                         : Move cursor to top of file
       Alt->                         : Move cursor to bottom of file
       Ctrl-H or BACKSPACE           : Delete character
       Ctrl-D or DELETE              : Delete next character
       Ctrl-W                        : Delete a word
```

The normal status bar, including the current filename, remains at the bottom. A subsequent ordinary key such as `q` dismisses help and restores the prior editor content and cursor without inserting that dismissal key. `Ctrl-L` forces a complete redraw of the normal screen while preserving content, cursor, scroll offsets, current buffer, and modified state.

## Spec 20

The input decoder must recognize common xterm/tmux byte sequences for arrows, Home, End, Delete, Page Up, Page Down, Alt-prefixed characters, and Ctrl-modified arrows. Home variants `ESC [ 1 ~` and `ESC [ 7 ~`, and End variants `ESC [ 4 ~` and `ESC [ 8 ~`, have their normal effects. Delete is `ESC [ 3 ~`, Page Up is `ESC [ 5 ~`, and Page Down is `ESC [ 6 ~`. Ctrl-arrow sequences of the form `ESC [ 1 ; 5 A/B/C/D` implement the aliases in Specs 9 and 10.

Recognized but unmapped modified keys do not change text or terminate the editor; they display `Key '{notation}' not mapped`. Required notations include `C-t`, `C-HOME`, `C-END`, `C-\`, and `C-SPACE`. The tested F7 sequence `ESC [ 1 8 ~`, unknown CSI sequence `ESC [ 9 9 9 ~`, and malformed-modifier sequence `ESC [ 1 ; 9 Q` leave the editor responsive without inserting text. The unbound F1 sequence `ESC O P` is handled differently: its printable suffix `P` is inserted at the cursor. Thus sending it before an initial `a`, then moving to End, inserting `b`, and saving writes `Pab\n`; the editor remains alive.

## Spec 21

Language is selected from the current filename extension and shown in the status bar. Required mappings include `.c` and `.h` to `c`; `.cpp`, `.cc`, and `.hpp` to `c++`; `.rs` to `rust`; `.go` to `go`; `.py` to `python`; `.js` to `javascript`; and `.jl` to `julia`. `.txt`, no extension, and unknown extensions use `plain`. Saving an unnamed buffer under a new extension immediately updates both the language label and highlighting.

Code files must emit ANSI foreground-color sequences around recognized tokens and a foreground reset after them. At minimum highlight:

- C/C++ keywords and definitions such as `struct`, `enum`, `union`, `namespace`, `class`, `template`, and `public`; built-in types such as `int`, `char`, and `void`; `//` and multi-line `/* ... */` comments; quoted strings/characters; decimal, hexadecimal, and floating-point numbers.
- Rust keywords such as `pub`, `impl`, `fn`, `let`, `mut`, and `use`; types such as `i32`, `u64`, `f32`, `bool`, `String`, and `Self`; the special identifier `self`; comments, strings, and numeric literals.
- Python keywords including `import`, `class`, `def`, `if`, `for`, `while`, and `return`.
- JavaScript `class` and `function` and other ordinary language keywords.
- Julia `function` and `end`.
- Go concurrency words `go`, `chan`, `defer`, and `select` and ordinary Go keywords.

Block-comment state must carry across rows and stop after the closing delimiter. A plain or unknown-extension file must not surround words such as `if`, `for`, `while`, or `int` with syntax color escapes.

## Spec 22

The TUI must operate under basic `ansi`, `xterm-color`, `xterm-256color`, `screen`, and true-color-capable environments. It should select true color when `COLORTERM=truecolor`, 256 colors when the terminal advertises 256-color support, and otherwise use 16-color ANSI fallback. Exact palette shades outside the fallback are not significant, but syntax and UI styles must not hide or alter text.

For the 16-color fallback, the observable SGR categories are bright black (`90`) for comments, bright blue (`94`) for keywords, green (`32`) for strings, bright magenta (`95`) for numbers, yellow (`33`) for types, bright yellow (`93`) for defined identifiers, and cyan/bright cyan for special values. In particular, C `struct`, Rust `pub`/`impl`/`fn`/`let`/`mut`, and Julia `function`/`end` are emitted with SGR `94`, not `91`. Apply the combined SGR sequence `39;0` after a colored token. Use reverse video for the status row and reset foreground, background, and attributes after it.

## Spec 23

Lines wider than the viewport are horizontally clipped rather than wrapped into additional screen rows. Moving the cursor to the right must horizontally scroll so the cursor and the relevant part of a line remain visible; moving back to Home restores the view of the line's beginning. Long lines of at least 2,000 characters and multiple long lines must remain editable and navigable without truncation.

Vertical scrolling keeps the cursor visible and supports files of at least 1,000 lines. The viewport shows consecutive logical rows, filling unused rows with `~`; it must not visually wrap long rows or add line-number prefixes. Cursor movement and edits after scrolling must affect the logical line indicated by the status bar.

## Spec 24

Changing the PTY window size and delivering `SIGWINCH` does not itself trigger a redraw: the editor emits no bytes in response and does not immediately recompute or reflow the visible layout. This is also true while a search prompt and nonempty query are active. Internal buffer text, unsaved marker, current logical cursor position, current buffer, and active prompt/query remain editor state across the size change. There is a later-action quirk for an active matching search: after searching for `needle`, resizing from 50x15 to 200x5, and receiving no resize output, pressing Enter redraws without displaying either the search prompt or `Found`, and the matching text remains visible, but search remains logically active. Consequently, the next Ctrl-Q performs search cancellation: it displays `Canceled`, restores the pre-search position, and leaves the process alive. A second Ctrl-Q then exits the clean editor with status 0. Resizing between dimensions such as 50x15, 120x40, 200x50, 200x5, and 30x40 must not by itself crash the editor or discard edits, but the new dimensions do not become visible merely because the resize signal was delivered.

## Spec 25

UTF-8 text files may contain tab, LF, and ordinary printable Unicode scalars. If rendering encounters another control character, terminate cleanly with status 1 and a newline-terminated standard-error diagnostic. For U+0001 the exact diagnostic is:

```text
Error: Invalid character for text is included: '\u{1}'
```

No panic text may be emitted. Tabs must specifically remain accepted. Other operating-system failures use `Error: {OS error}` when fatal during startup, or `Could not save: {OS error}` when a save can be recovered from within the editor.
