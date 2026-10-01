# Clarified executable specification

This document is the complete and normative specification for the required artifact. The artifact is one executable file named exactly `executable`. Any older README, manual page, source-directory placeholder, or license file beside this document is non-normative. All text output is UTF-8. In byte-level examples, `ESC` means the single byte `0x1b`.

## Spec 1

The executable is a command-line byte/hex viewer with invocation:

```text
executable [OPTIONS] [FILE]
```

It must exist as a regular executable file. At most one positional `FILE` is accepted. With a file, read that file as arbitrary bytes; without one, read standard input as arbitrary bytes. `--` ends option parsing, so `executable -- --help` tries to open a file literally named `--help`. A second positional argument is a command-line usage error.

Normal viewing output goes only to stdout and ends with a newline. Successful viewing, help, version, color-table, and completion operations return status 0 with empty stderr. The color table has the explicitly documented trailing-byte exception in Spec 16. File/open/seek/value-validation failures return status 1 and write only stderr. Command-line grammar errors (unknown flags, missing option values, conflicts, too many positionals, invalid enumerated choices) return status 2 and write only stderr.

Files, stdin, FIFOs/named pipes, empty inputs, and large binary inputs must all be handled without text decoding or byte corruption. A directory is not a file and fails as described in Spec 18. A missing file also fails as described there.

## Spec 2

The accepted options and defaults are:

| Option | Meaning and default |
|---|---|
| `-n N`, `--length N` | read at most N bytes; aliases `--bytes`, `-c`, and hidden short alias `-l` |
| `-s N`, `--skip N` | skip N bytes before displaying; default 0 |
| `--block-size SIZE` | multiplier for `block`/`blocks`; default 512 |
| `-v`, `--no-squeezing` | disable repeated-row compression |
| `--color WHEN` | `always` (default), `auto`, `never`, or `force` |
| `--border STYLE` | `unicode` (default), `ascii`, or `none` |
| `-p`, `--plain` | hex-data-only layout shorthand |
| `--no-characters` | hide character cells |
| `-C`, `--characters` | explicitly show character cells (the default) |
| `--character-table FORMAT` | `default` (default), `ascii`, `codepage-1047`, `codepage-437`, or `braille` |
| `--color-scheme FORMAT` | `default` (default) or `gradient` |
| `-P`, `--no-position` | hide the address cell |
| `-o N`, `--display-offset N` | add N to displayed addresses; default 0 |
| `--panels N` | positive decimal count, or `auto` |
| `-g N`, `--group-size N` | one of 1, 2, 4, 8; default 1; alias `--groupsize` |
| `--endianness FORMAT` | `big` (default) or `little` |
| `-e` | exact alias for `--endianness=little` |
| `-b B`, `--base B` | numeric byte display base; default hexadecimal |
| `--terminal-width N` | choose panel count from an explicit decimal terminal width |
| `--print-color-table` | print the reference in Spec 16 and exit |
| `-i`, `--include` | C-include formatting from Spec 14 |
| `--completion SHELL` | completion for bash, elvish, fish, powershell, or zsh |
| `-h` | concise help |
| `--help` | long help |
| `-V`, `--version` | version output |

Both `--option=value` and `--option value` work. Short value options accept both `-n 16` and `-n=16`. Each spelling of length denotes the same logical option but using two spellings in one invocation (for example `--length=32 --bytes=10`, `--length=32 -l=10`, or `--bytes=32 -l=10`) is rejected.

Argument parsing is left-to-right with respect to help and errors. Once `-h` or `--help` is encountered it prints help successfully and ignores all later tokens, including an otherwise unknown flag or missing file. It does not override an error in an earlier token: `executable --definitely-invalid /missing --help` returns 2 with the unexpected-argument diagnostic, whereas `executable --help --definitely-invalid /missing` returns 0 with help on stdout and empty stderr. Version also short-circuits normal input processing. When `--print-color-table` and `--completion` occur together, the color table is printed and completion is not. The long and short help text identifies the program as `executable`, while version deliberately identifies the product as `hexyl`.

## Spec 3

Byte counts for length, skip, display offset, and block size consist of an integer followed immediately by an optional case-insensitive unit. Decimal integers are the default. A `0x` prefix selects hexadecimal. For signed contexts, an optional `+` or `-` must precede `0x`, never follow it. An explicit `+` is accepted for skip. Decimal points, commas, and scientific notation are not numeric syntax; after the initial digit run they are treated as part of an invalid unit.

The complete unit multipliers are:

| suffix (case-insensitive) | multiplier |
|---|---:|
| absent | 1 |
| `kB` | 1,000 |
| `MB` | 1,000,000 |
| `GB` | 1,000,000,000 |
| `TB` | 1,000,000,000,000 |
| `KiB` | 1,024 |
| `MiB` | 1,048,576 |
| `GiB` | 1,073,741,824 |
| `TiB` | 1,099,511,627,776 |
| `block`, `blocks` | the current block size |

Parsing and multiplication are checked signed-64-bit operations. Skip may be negative. Length and display offset reject a parsed negative value with “negative offset specified, but only positive offsets (counts) are accepted in this context”. Block size must be strictly positive, and may not itself use `block` or `blocks` as a unit. A negative decimal block size such as `-1` is rejected as not matching `<pos-integer>[<unit>]`; zero and hexadecimal zero parse and then fail the positive-value check.

The parser must distinguish the tested malformed cases in its diagnostics: empty input; a sign with no following digits; a sign after `0x`; a recognized unit without an integer; an unknown unit; bad/overflowing integer digits; and multiplication overflow. The required phrases and envelopes are in Spec 18. Block-size validation has two direct-error exceptions: zero and hexadecimal-zero use the direct positive-value error, and `--block-size=0x+` uses the direct sign-only error, rather than the general byte-count envelope.

One deliberately observable compatibility quirk must be retained: when a valid, positive `--block-size` is written in hexadecimal (for example `--block-size=0x10`), validation succeeds and the process returns 0 immediately with completely empty stdout and stderr instead of viewing the input.

## Spec 4

Input selection is performed in this order:

1. Open the file, or use stdin.
2. Apply skip.
3. Limit the remaining stream to length, if supplied.
4. Format the selected bytes.

A nonnegative skip consumes exactly that many bytes. On a regular file it may seek directly. On stdin or a FIFO it must read and discard, including for large skips. Skipping to or beyond EOF succeeds and produces the normal “No content” view. A negative skip means start `abs(N)` bytes before the physical end and therefore works only for a seekable regular file. A negative skip larger than the file, or any negative skip on stdin/FIFO, returns 1 with exactly:

```text
Error: Failed to jump to the desired input position. This could be caused by a negative offset that is too large or by an input that is not seek-able (e.g. if the input comes from a pipe).
```

Length is a maximum, never a demand: if it exceeds the remaining input, stop normally at EOF; zero selects no content. Skip and length compose (skip 3, length 5 selects original bytes 3 through 7). The address of the first selected byte is `actual_skip + display_offset`; subsequent rows add their actual byte count. Thus skip 0x10 and display offset 0x20 starts at address `00000030`. Display offset changes labels only, never which bytes are read.

Block size has no visual effect and matters only when `block` or `blocks` occurs in a count. With `--block-size=16 --skip=1block`, 16 bytes are skipped; with `--block-size=8 --length=1block`, 8 bytes are read.

## Spec 5

The display is made of panels. Each hex-data panel represents exactly 8 source bytes, and (unless hidden) each matching character panel represents those same 8 bytes. A row therefore consumes `8 * panel_count` bytes. Selected data is always left-aligned; a skip does not indent to an address boundary.

For a base that uses `d` digits per byte and group size `g`, the visible width of one hex-data cell is:

```text
hex_cell_width = 2 + 8*d + (8/g - 1)
```

The two accounts for one leading and one trailing space. The character-cell width is 8 and the position-cell width is 8. Hexadecimal has `d=2`, so its data-cell widths for group sizes 1, 2, 4, 8 are respectively 25, 21, 19, and 18. Binary has `d=8`; octal and decimal have `d=3`.

An explicit numeric `--panels=N` uses exactly N panels, even if this creates empty panels to the right of the data. With neither `--panels` nor `--terminal-width`, use exactly two panels; this default does not inspect an interactive terminal's width and remains two at a 150-column TTY. Thus captured octal/group-size-8 output also has two panels even though it is 81 columns wide. `--panels=auto` uses the detected terminal width, falling back to 80 when none is available. `--terminal-width=W` uses W. For these two automatic-width options choose:

```text
panel_count = max(1, floor((W - 8) / (hex_cell_width + 9)))
```

with calculations clamped so widths below the minimum still yield one. For default hex/group-1, widths 1 and 60 select 1 panel, 80 selects 2, 150 selects 4, 200 selects 5, and 500 selects 14. Numeric `--panels` and `--terminal-width` conflict even when panels is `auto`; the error is a status-2 grammar error.

Addresses are lowercase hexadecimal, zero-padded to at least 8 digits. Every data row shows the address of its first byte. Hiding the position cell removes the address entirely.

## Spec 6

Each byte is formatted independently at fixed width: binary is 8 bits (`00001010`), octal is 3 lower-case octal digits (`012`), decimal is 3 decimal digits (`010`), and hexadecimal is 2 lower-case hexadecimal digits (`0a`). Base accepts all of these exact aliases:

| base | accepted values |
|---|---|
| binary | `2`, `b`, `bin`, `binary` |
| octal | `8`, `o`, `oct`, `octal` |
| decimal | `10`, `d`, `dec`, `decimal` |
| hexadecimal | `16`, `x`, `hex`, `hexadecimal` |

Within each 8-byte panel, divide bytes into consecutive groups of the requested group size. Concatenate formatted bytes within a group with no separator and put one ASCII space between groups. Big endian keeps source order. Little endian reverses the bytes independently inside every group, including a final partial group; it does not reverse bits or digits within a byte. Endianness has no effect for group size 1. The character cells always retain original source order.

Examples for source bytes `00 01 02 03 04 05 06 07` in hexadecimal are:

```text
g=1:  00 01 02 03 04 05 06 07
g=2:  0001 0203 0405 0607
g=2 little: 0100 0302 0504 0706
g=4:  00010203 04050607
g=8:  0001020304050607
```

The same grouping rule applies in binary, octal, and decimal. For example decimal group size 2 concatenates `000001`; binary group size 4 concatenates 32 digits.

## Spec 7

With Unicode borders, a complete default two-panel line for input `0123456789abcde\n` is exactly:

```text
┌────────┬─────────────────────────┬─────────────────────────┬────────┬────────┐
│00000000│ 30 31 32 33 34 35 36 37 ┊ 38 39 61 62 63 64 65 0a │01234567┊89abcde_│
└────────┴─────────────────────────┴─────────────────────────┴────────┴────────┘
```

Unicode top borders use `┌`, `─`, `┬`, `┐`; bottoms use `└`, `─`, `┴`, `┘`. Data rows begin/end and major cell boundaries use `│`. Boundaries between adjacent hex panels and between adjacent character panels use the thin separator `┊`. Top and bottom boundaries always use `┬`/`┴`, including where a row uses `┊`.

For nonempty input, ASCII borders replace the corresponding characters with `+`, `-`, and `|`, including all internal separators. The empty-input content-row exception is specified in Spec 12. `border=none` omits top and bottom entirely and replaces every would-be row-border/separator character by one ASCII space; it does not trim any padding. Therefore `Hello World` without a border is exactly:

```text
 00000000  48 65 6c 6c 6f 20 57 6f   72 6c 64                 Hello Wo rld      
```

Partial panels are padded on the right to their full cell widths. A 3-byte stdin input `abc` in the default view is exactly:

```text
┌────────┬─────────────────────────┬─────────────────────────┬────────┬────────┐
│00000000│ 61 62 63                ┊                         │abc     ┊        │
└────────┴─────────────────────────┴─────────────────────────┴────────┴────────┘
```

## Spec 8

`--no-characters` removes all character cells but keeps position, hex cells, their padding, and borders. `--no-position` removes only the position cell. `--no-characters --no-position` removes both. Border construction must adapt its number of sections; it must not leave a phantom cell.

`--plain` forces `--no-characters`, `--no-position`, and `--border=none`, and normally disables color. It still respects base, grouping, explicit panel count, skip, and length. Its untrimmed spacing is the border-none spacing generated by the same cell renderer. These outputs are exact:

```text
# XYZ, defaults (the spaces after 5a extend through two 8-byte data panels)
  58 59 5a                                           

# 16 bytes 00..0f, --plain --panels=2
  00 01 02 03 04 05 06 07   08 09 0a 0b 0c 0d 0e 0f  
```

An explicitly requested color mode still applies in plain layout: `--color=always --color-scheme=gradient --plain` is colored. Explicit panel settings also apply. However, plain's character suppression is unconditional: `--plain --characters` and `--characters --plain` both omit character cells. Outside plain mode, `--characters` is accepted as the explicit positive form of the character-panel setting.

## Spec 9

The `default` character table maps each byte as follows:

- `00` → `⋄` (U+22C4).
- Printable ASCII `20` through `7e` → the literal character (including a literal space for `20`).
- Tab `09`, line feed `0a`, form feed `0c`, and carriage return `0d` → `_`.
- Every other byte below `80`, including vertical tab `0b` and DEL `7f`, → `•` (U+2022).
- Bytes `80` through `ff` → `×` (U+00D7).

The `ascii` table maps `20..7e` literally and every other byte to `.`.

The `codepage-437` table is completely defined by the following three concatenated strings. The character at index N is the display for byte N. Each string respectively covers `00..1f`, `20..7f`, and `80..ff`:

```text
⋄☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼
 !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂
ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ﬀ
```

The final character above, for byte `ff`, is the ligature `ﬀ` (U+FB00).

The option named `codepage-1047` uses the following exact ASCII-filtered EBCDIC lookup table. A byte whose table entry is an ASCII graphic displays that graphic, EBCDIC byte `40` displays an ordinary space, and all other entries display `.`. Do not substitute a platform codec or preserve accented Unicode characters. This indexed 16-row table is self-contained; each row contains the 16 mappings beginning at its labeled byte:

```text
00 ................
10 ................
20 ................
30 ................
40  .........$.<(+|
50 &.........!$*);.
60 -/.........,%_>?
70 ..........:#@'=.
80 .abcdefghi.{.(+.
90 .jklmnopqr.}.)..
a0 .~stuvwxyz......
b0 ..........[]...-
c0 {ABCDEFGHI......
d0 }JKLMNOPQR......
e0 ..STUVWXYZ......
f0 0123456789......
```

For example `c8 c5 d3 d3 d6 40 e6 d6 d9 d3 c4` displays `HELLO WORLD`.

## Spec 10

The `braille` table keeps printable ASCII `20..7e` literal and has these special mappings: `00 → ⋄`, `09 → →`, `0a → ↵`, and `0d → ←`. Every other nonprintable byte is mapped to U+2800 plus a bit-permuted byte. Input bits 0 through 7 become Braille-pattern bits `[0, 3, 1, 4, 2, 5, 6, 7]` respectively. Equivalently:

```text
p = ((b & 0x01) << 0) | ((b & 0x02) << 2) |
    ((b & 0x04) >> 1) | ((b & 0x08) << 1) |
    ((b & 0x10) >> 2) |  (b & 0xe0)
character = Unicode scalar U+2800+p
```

Thus bytes `01 02 04 08 10 20 40 80` display `⠁⠈⠂⠐⠄ @⢀`; `0b` displays `⠙`, `0c` displays `⠒`, `7f` displays `⡿`, and `ff` displays `⣿`. Character-table selection affects only character cells. Base, grouping, and endianness affect the numeric cells but never reorder these characters.

## Spec 11

Squeezing is on by default and is disabled by either `-v` or `--no-squeezing`. It compresses a run of one repeated byte that continues beyond a complete source row of `8 * panel_count` bytes. Print the first complete row normally and replace the repeated continuation with one marker row containing `*` in the position-cell location (or at the left edge when position is hidden) and blanks in every other cell. This is not general identical-row deduplication: two or more equal nonuniform rows are printed in full. For example, with `--panels=1`, `1234567812345678` produces two ordinary rows and no marker; with four panels, two rows each made from `DATA1___` repeated four times are likewise both printed. In contrast, 16 `X` bytes with one panel produce a normal row followed by a marker.

When a different row follows, print it with its real address. If a squeezed run reaches EOF on a row boundary, print one additional extent row: with position enabled it is otherwise blank and contains the EOF address; with position disabled it renders as another `*` marker row. Thus a plain or `--no-position` view whose repeated tail reaches EOF has two consecutive `*` rows (one compression marker and one extent marker). Do not otherwise print an EOF/extent row. Partial final rows are rendered normally and are never padding data for comparison.

For 32 `X` bytes (two uniform 16-byte rows) in the default layout the output is exactly:

```text
┌────────┬─────────────────────────┬─────────────────────────┬────────┬────────┐
│00000000│ 58 58 58 58 58 58 58 58 ┊ 58 58 58 58 58 58 58 58 │XXXXXXXX┊XXXXXXXX│
│*       │                         ┊                         │        ┊        │
│00000020│                         ┊                         │        ┊        │
└────────┴─────────────────────────┴─────────────────────────┴────────┴────────┘
```

With no position cell, the marker is `*` followed by enough spaces to fill the first hex cell. With no border, it remains a line whose only non-space character is `*`. In colored output a position-cell marker is exactly `ESC[90m*ESC[39m` followed by seven spaces, and every otherwise empty data/character panel still emits the panel-end reset required by Spec 13. When squeezing is disabled, every data row appears and no `*` occurs.

## Spec 12

If the selected input contains zero bytes (empty input, zero length, or a nonnegative skip reaching/passing EOF), viewing succeeds and places `No content` left-aligned in the first numeric cell. The default exact output is:

```text
┌────────┬─────────────────────────┬─────────────────────────┬────────┬────────┐
│        │ No content              │                         │        │        │
└────────┴─────────────────────────┴─────────────────────────┴────────┴────────┘
```

With position hidden, the first border section is the first 25-column hex cell and the row begins `│ No content`. Empty rendering retains compatibility inconsistencies between the top/bottom borders and the content row. With an explicit numeric panel count, the border honors that count; without one, the empty-input sizing path can select a base-dependent count (binary selects one in the example below). The border honors group size, character visibility, and border style, but calculates each numeric section's width as hexadecimal. The content row uses Unicode `│` separators and exactly two numeric cells (plus two character cells unless hidden), regardless of the border's panel count. These observed combinations are exact:

```text
# --color=never --base=binary --border=unicode
┌────────┬─────────────────────────┬────────┐
│        │ No content              │                         │        │        │
└────────┴─────────────────────────┴────────┘

# --color=never --group-size=8 --panels=3 --border=ascii
+--------+------------------+------------------+------------------+--------+--------+--------+
│        │ No content       │                  │        │        │
+--------+------------------+------------------+------------------+--------+--------+--------+

# --color=never --base=binary --group-size=8 --panels=1 --no-characters --border=ascii
+--------+------------------+
│        │ No content       │                  │
+--------+------------------+
```

Include mode is different: an empty selected stdin slice emits one newline byte, while an empty named file emits the empty C declaration in Spec 15.

## Spec 13

Color output is governed by `--color` and `NO_COLOR`:

- `never`: no `ESC[` sequences.
- `auto`: uncolored for captured/redirected stdout and also uncolored when stdout is an interactive terminal. For example, `--color=auto --panels=1` with `A` on stdin and stdout attached to a PTY returns 0 without any `ESC` byte.
- `always` (also the default): color unless the `NO_COLOR` environment variable exists, regardless of its value.
- `force`: color even if `NO_COLOR` exists and even when stdout is captured.

Borders and separators are not intrinsically colored. The default scheme chooses a foreground from the original byte: null `00` is bright black (`ESC[90m`); printable non-space ASCII is cyan (`ESC[36m`); ASCII whitespace and other ASCII controls are green (`ESC[32m`); non-ASCII is yellow (`ESC[33m`). Addresses are bright black. End a colored region with foreground reset `ESC[39m` (not full reset `ESC[0m`). Numeric cells and character cells are colored independently. Emit a new color sequence only when the effective ANSI color changes, and reset at panel boundaries; consecutive bytes with the same effective color share a run even if they belong to different semantic categories. Thus numeric bytes `09 0b 20` occur under one continuous `ESC[32m` run. A byte retains its category color if numeric endianness moves it.

The six color variables are `HEXYL_COLOR_OFFSET`, `HEXYL_COLOR_ASCII_PRINTABLE`, `HEXYL_COLOR_ASCII_WHITESPACE`, `HEXYL_COLOR_ASCII_OTHER`, `HEXYL_COLOR_NULL`, and `HEXYL_COLOR_NONASCII`. Named values are case-sensitive lowercase standard names `black red green yellow blue magenta cyan white` (codes 30..37), or `bright ` plus one of those lowercase names (codes 90..97); an unrecognized named value leaves the default color in place. Named overrides apply to all six variables, including `HEXYL_COLOR_ASCII_PRINTABLE`: `blue` emits `ESC[34m` and `bright blue` emits `ESC[94m` for a printable byte in both its numeric and character cells. `#RRGGBB` overrides work for all six variables (hexadecimal digits may be mixed case) and emit `ESC[38;2;R;G;Bm`.

The precise colored rendering rule includes spacing and redundant resets. At the start of a row, activate the offset color. If the position cell is visible, render its address in that color and reset before the next separator. If position is hidden, do not perform that reset; consequently a colored border-none/plain row starts with the uncolored outer space, then `ESC[90m`, then the leading space of its first hex cell, then the first byte’s color. Activate the first byte’s color immediately before its digits/character. Spaces between numeric groups remain under the preceding color until the next color escape. Right padding after a partial panel remains under the last byte’s color. At the end of every numeric and character panel emit `ESC[39m`, including an entirely empty panel, before its separator/trailing cell space. This state behavior is necessary for byte-exact colored snapshots.

## Spec 14

The gradient scheme uses true-color foreground escapes of exactly 19 bytes:

```text
ESC [ 3 8 ; 2 ; RRR ; GGG ; BBB m
```

Each component is three zero-padded decimal digits. Let `lerp(a,b,t) = trunc(a + (b-a)*t)`, truncating toward zero. A generated gradient of length L evaluates element index i at `x=i/L` (not `i/(L-1)`). For multiple stops, find adjacent stops whose fractional positions surround x, compute local `t`, and interpolate each channel.

Byte-to-gradient rules are exact:

- `00`: `(100,100,100)`.
- `01..1f`: index `b-1` of length-31 gradient from `(255,0,255)` at 0.0 to `(128,0,255)` at 1.0.
- `20..7e`: index `b-0x20` of length-95 gradient from `(0,128,255)` at 0.0 to `(0,255,128)` at 1.0. Space therefore belongs here, not to a fixed whitespace color.
- `7f`: fixed `(64,128,0)`.
- `80..ff`: index `b-0x80` of length-128, three-stop gradient `(255,0,0,0.0)`, `(255,255,0,0.66)`, `(255,255,255,1.0)`.

Examples: `01 → ESC[38;2;255;000;255m`, `02 → ...250;000;255m`, tab `09 → ...222;000;255m`, space `20 → ...000;128;255m`, `H` (`48`) → `...000;181;201m`, `7f → ...064;128;000m`, `80 → ...255;000;000m`, `90 → ...255;048;000m`, `e0 → ...255;255;067m`, `f0 → ...255;255;161m`, and `ff → ...255;255;249m`. Apply these colors to both numeric and character representations using the state/reset rules of Spec 13.

## Spec 15

Include mode ignores the normal panels, character table, colors, borders, grouping, base, position, and squeezing. It always outputs lower-case two-digit C hex literals, 12 bytes per line, separated by comma-space, with two leading spaces on every data line. All nonfinal data lines end in a comma; the final one does not. Skip and length still select the byte slice. Group size is accepted but does not alter include output. An explicitly requested endianness (including `-e`) conflicts with include mode.

For stdin, output data lines followed by a newline. Four stdin bytes are exactly:

```text
  0x41, 0x42, 0x43, 0x44
```

If skip/length selects no stdin bytes—whether stdin itself is empty, length is zero, or skip is at or beyond EOF—output exactly one newline byte (`\n`).

For a named file, derive an identifier from the basename by replacing every Unicode character that is neither alphanumeric nor underscore with `_`; Unicode alphanumerics are preserved in UTF-8. Thus `a-b.c +é` becomes `a_b_c__é`. Wrap the selected data as:

```text
unsigned char IDENT[] = {
  ...data, up to 12 per line...
};
unsigned int IDENT_len = N;
```

For file `small.txt` containing `Hello`, exact output is:

```text
unsigned char small_txt[] = {
  0x48, 0x65, 0x6c, 0x6c, 0x6f
};
unsigned int small_txt_len = 5;
```

An empty file named `empty.bin` is exactly:

```text
unsigned char empty_bin[] = {

};
unsigned int empty_bin_len = 0;
```

## Spec 16

`-V` and `--version` both output exactly `hexyl 0.16.0\n`. They do not read stdin or a file.

`--print-color-table` outputs the following exact byte sequence, where every displayed `ESC` denotes byte `1b`. There is a newline between the non-ASCII description and the final reset, but there is no byte after the final `m` (in particular, no trailing newline):

```text
hexyl color reference:

ESC[90m⋄ NULL bytes (0x00)
ESC[39mESC[36ma ASCII printable characters (0x20 - 0x7E)
ESC[39mESC[32m_ ASCII whitespace (0x09 - 0x0D, 0x20)
ESC[39mESC[32m• ASCII control characters (except NULL and whitespace)
ESC[39mESC[33m× Non-ASCII bytes (0x80 - 0xFF)
ESC[39m
```

This reference is always colored regardless of redirection. It returns immediately without reading input.

Long help begins with `A command-line hex viewer`, contains `Usage: executable [OPTIONS] [FILE]`, `Arguments:`, and `Options:`, documents every option and default from Spec 2, and ends with a newline. Its normalized wording (all runs of whitespace treated as one space) must be the same as this canonical text and order:

```text
A command-line hex viewer
Usage: executable [OPTIONS] [FILE]
Arguments:
[FILE] The file to display. If no FILE argument is given, read from STDIN
Options:
-n, --length <N> Only read N bytes from the input. The N argument can also include a unit with a decimal prefix (kB, MB, ..) or binary prefix (kiB, MiB, ..), or can be specified using a hex number. The short option '-l' can be used as an alias. Examples: --length=64, --length=4KiB, --length=0xff [aliases: bytes] [short aliases: c]
-s, --skip <N> Skip the first N bytes of the input. The N argument can also include a unit (see `--length` for details). A negative value is valid and will seek from the end of the file.
--block-size <SIZE> Sets the size of the `block` unit to SIZE. Examples: --block-size=1024, --block-size=4kB [default: 512]
-v, --no-squeezing Displays all input data. Otherwise any number of groups of output lines which would be identical to the preceding group of lines, are replaced with a line comprised of a single asterisk
--color <WHEN> When to use colors [default: always] Possible values: - always: Always use colorized output - auto: Only displays colors if the output goes to an interactive terminal - never: Do not use colorized output - force: Override the NO_COLOR environment variable
--border <STYLE> Whether to draw a border [default: unicode] Possible values: - unicode: Draw a border with Unicode characters - ascii: Draw a border with ASCII characters - none: Do not draw a border at all
-p, --plain Display output with --no-characters, --no-position, --border=none, and --color=never
--no-characters Do not show the character panel on the right
-C, --characters Show the character panel on the right. This is the default, unless --no-characters has been specified
--character-table <FORMAT> Defines how bytes are mapped to characters [default: default] Possible values: - default: Show printable ASCII characters as-is, '⋄' for NULL bytes, ' ' for space, '_' for other ASCII whitespace, '•' for other ASCII characters, and '×' for non-ASCII bytes - ascii: Show printable ASCII as-is, ' ' for space, '.' for everything else - codepage-1047: Show printable EBCDIC as-is, ' ' for space, '.' for everything else - codepage-437: Uses code page 437 (for non-ASCII bytes) - braille: Uses braille characters for non-printable bytes
--color-scheme <FORMAT> Defines the color scheme for the characters [default: default] Possible values: - default: Show the default colors: bright black for NULL bytes, green for ASCII space characters and non-printable ASCII, cyan for printable ASCII characters, and yellow for non-ASCII bytes - gradient: Show bright black for NULL bytes, cyan for printable ASCII characters, a gradient from pink to violet for non-printable ASCII characters and a heatmap-like gradient from red to yellow to white for non-ASCII bytes
-P, --no-position Whether to display the position panel on the left
-o, --display-offset <N> Add N bytes to the displayed file position. The N argument can also include a unit (see `--length` for details). A negative value is valid and calculates an offset relative to the end of the file. [default: 0]
--panels <N> Sets the number of hex data panels to be displayed. `--panels=auto` will display the maximum number of hex data panels based on the current terminal width. By default, hexyl will show two panels, unless the terminal is not wide enough for that
-g, --group-size <N> Number of bytes/octets that should be grouped together. You can use the '--endianness' option to control the ordering of the bytes within a group. '--groupsize' can be used as an alias (xxd-compatibility) [default: 1] Possible values: - 1: Grouped together every byte/octet - 2: Grouped together every 2 bytes/octets - 4: Grouped together every 4 bytes/octets - 8: Grouped together every 8 bytes/octets
--endianness <FORMAT> Whether to print out groups in little-endian or big-endian format. This option only has an effect if the '--group-size' is larger than 1. '-e' can be used as an alias for '--endianness=little' [default: big] Possible values: - little: Print out groups in little-endian format - big: Print out groups in big-endian format
-b, --base <B> Sets the base used for the bytes. The possible options are binary, octal, decimal, and hexadecimal [default: hexadecimal]
--terminal-width <N> Sets the number of terminal columns to be displayed. Since the terminal width may not be an evenly divisible by the width per hex data column, this will use the greatest number of hex data panels that can fit in the requested width but still leave some space to the right. Cannot be used with other width-setting options.
--print-color-table Print a table showing how different types of bytes are colored
-i, --include Output in C include file style
--completion <SHELL> Show shell completion for a certain shell [possible values: bash, elvish, fish, powershell, zsh]
-h, --help Print help (see a summary with '-h')
-V, --version Print version
```

`-h` is a shorter, wrapped summary: it must still start with the same description, contain the same Usage/Arguments/Options sections and all option names, be strictly shorter and different from long help, and its help line must say `Print help (see more with '--help')`.

## Spec 17

Completion output may be a fixed generated script, but it must be at least 20 lines, contain `hexyl`, `length`, `skip`, `color`, `help`, and `version`, and begin byte-for-byte (apart from any text appended after the shown prefix) with the corresponding prefix below. Every completion command returns 0 with no stderr and does not read input.

For bash:

```text
_hexyl() {
    local i cur prev opts cmd
    COMPREPLY=()
    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
        cur="$2"
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
    fi
    prev="$3"
    cmd=""
    opts=""

    for i in "${COMP_WORDS[@]:0:COMP_CWORD}"
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="hexyl"
                ;;
            *)
                ;;
```

For zsh:

```text
#compdef hexyl

autoload -U is-at-least

_hexyl() {
    typeset -A opt_args
    typeset -a _arguments_options
    local ret=1

    if is-at-least 5.2; then
        _arguments_options=(-s -S -C)
    else
        _arguments_options=(-s -C)
    fi

    local context curcontext="$curcontext" state line
    _arguments "${_arguments_options[@]}" : \
'-n+[Only read N bytes from the input. The N argument can also include a unit with a decimal prefix (kB, MB, ..) or binary prefix (kiB, MiB, ..), or can be specified using a hex number. The short option '\''-l'\'' can be used as an alias. Examples\: --length=64, --length=4KiB, --length=0xff]:N:_default' \
'-c+[Only read N bytes from the input. The N argument can also include a unit with a decimal prefix (kB, MB, ..) or binary prefix (kiB, MiB, ..), or can be specified using a hex number. The short option '\''-l'\'' can be used as an alias. Examples\: --length=64, --length=4KiB, --length=0xff]:N:_default' \
'--length=[Only read N bytes from the input. The N argument can also include a unit with a decimal prefix (kB, MB, ..) or binary prefix (kiB, MiB, ..), or can be specified using a hex number. The short option '\''-l'\'' can be used as an alias. Examples\: --length=64, --length=4KiB, --length=0xff]:N:_default' \
```

For elvish, the output starts with a blank line, then:

```text
use builtin;
use str;

set edit:completion:arg-completer[hexyl] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'hexyl'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'hexyl'= {
```

For PowerShell, the output starts with a blank line, then:

```text
using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'hexyl' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'hexyl'
        for ($i = 1; $i -lt $commandElements.Count; $i++) {
            $element = $commandElements[$i]
            if ($element -isnot [StringConstantExpressionAst] -or
                $element.StringConstantType -ne [StringConstantType]::BareWord -or
                $element.Value.StartsWith('-') -or
                $element.Value -eq $wordToComplete) {
                break
        }
        $element.Value
    }) -join ';'
```

Fish starts with these exact logical lines (embedded newlines inside double-quoted `-a` arguments are literal newlines):

```text
complete -c hexyl -s n -s c -l length -l bytes -d 'Only read N bytes from the input. The N argument can also include a unit with a decimal prefix (kB, MB, ..) or binary prefix (kiB, MiB, ..), or can be specified using a hex number. The short option \'-l\' can be used as an alias. Examples: --length=64, --length=4KiB, --length=0xff' -r
complete -c hexyl -s s -l skip -d 'Skip the first N bytes of the input. The N argument can also include a unit (see `--length` for details). A negative value is valid and will seek from the end of the file.' -r
complete -c hexyl -l block-size -d 'Sets the size of the `block` unit to SIZE. Examples: --block-size=1024, --block-size=4kB' -r
complete -c hexyl -l color -d 'When to use colors' -r -f -a "always\t'Always use colorized output'
auto\t'Only displays colors if the output goes to an interactive terminal'
never\t'Do not use colorized output'
force\t'Override the NO_COLOR environment variable'"
complete -c hexyl -l border -d 'Whether to draw a border' -r -f -a "unicode\t'Draw a border with Unicode characters'
ascii\t'Draw a border with ASCII characters'
none\t'Do not draw a border at all'"
complete -c hexyl -l character-table -d 'Defines how bytes are mapped to characters' -r -f -a "default\t'Show printable ASCII characters as-is, \'⋄\' for NULL bytes, \' \' for space, \'_\' for other ASCII whitespace, \'•\' for other ASCII characters, and \'×\' for non-ASCII bytes'
ascii\t'Show printable ASCII as-is, \' \' for space, \'.\' for everything else'
codepage-1047\t'Show printable EBCDIC as-is, \' \' for space, \'.\' for everything else'
codepage-437\t'Uses code page 437 (for non-ASCII bytes)'
braille\t'Uses braille characters for non-printable bytes'"
complete -c hexyl -l color-scheme -d 'Defines the color scheme for the characters' -r -f -a "default\t'Show the default colors: bright black for NULL bytes, green for ASCII space characters and non-printable ASCII, cyan for printable ASCII characters, and yellow for non-ASCII bytes'
gradient\t'Show bright black for NULL bytes, cyan for printable ASCII characters, a gradient from pink to violet for non-printable ASCII characters and a heatmap-like gradient from red to yellow to white for non-ASCII bytes'"
complete -c hexyl -s o -l display-offset -d 'Add N bytes to the displayed file position. The N argument can also include a unit (see `--length` for details). A negative value is valid and calculates an offset relative to the end of the file.' -r
complete -c hexyl -l panels -d 'Sets the number of hex data panels to be displayed. `--panels=auto` will display the maximum number of hex data panels based on the current terminal width. By default, hexyl will show two panels, unless the terminal is not wide enough for that' -r
complete -c hexyl -s g -l group-size -d 'Number of bytes/octets that should be grouped together. You can use the \'--endianness\' option to control the ordering of the bytes within a group. \'--groupsize\' can be used as an alias (xxd-compatibility)' -r -f -a "1\t'Grouped together every byte/octet'
```

Continue fish with completion declarations for the remaining group-size choices, endianness, base, terminal-width, include, completion, help, and version. They use `complete -c hexyl`, pair the documented short and long flags, and use the descriptions from Spec 16.

## Spec 18

Error output must be stable and helpful. Unknown flags use the exact status-2 templates:

```text
error: unexpected argument '--invalid-flag' found

  tip: to pass '--invalid-flag' as a value, use '-- --invalid-flag'

Usage: executable [OPTIONS] [FILE]

For more information, try '--help'.
```

Replace the argument literally for a short flag such as `-x`. A missing skip value is exactly:

```text
error: a value is required for '--skip <N>' but none was supplied

For more information, try '--help'.
```

Except for the direct block-size validation errors listed below, invalid byte-count values return 1 with this envelope (substitute option and value):

```text
Error: failed to parse `--skip` arg "abc" as byte count

Caused by:
    "abc" is not of the expected form <pos-integer>[<unit>]
```

Specific causes must contain these exact phrases (the comma punctuation is literal):

- unknown suffix: `invalid unit "xyz"` (so `1.5`, `1,000`, `1e10` report `.5`, `,000`, `e10` respectively);
- empty: `no character data found, did you forget to write it?`;
- sign only: `no digits found after sign, did you forget to write them?`;
- misplaced sign followed by digits, as in `0x+1`: `found '+' sign after hex prefix ("0x"); signs should go before it` (analogous for `-`); `0x+` with no following digit instead uses the sign-only phrase;
- bare known unit: `"kB" is a valid unit, but an integer should come before it`;
- bad/overflowing digits: `failed to parse integer part` followed by the underlying `invalid digit found in string` or `number too large to fit in target type`;
- unit overflow: `count multiplied by the unit overflowed a signed 64-bit integer; are you sure it should be that big?`;
- zero block size: the entire error is the direct one-line `Error: block size argument must be positive\n`, without the byte-count envelope;
- `--block-size=0x+`: the entire error is the direct one-line `Error: no digits found after sign, did you forget to write them?\n`, without the byte-count envelope;
- block-sized block size: `can not use 'block(s)' as a unit to specify block size`.

Invalid bases are status 1 and exactly one line:

```text
Error: The number provided is not a valid base. Valid bases are 2, 8, 10, and 16.
Error: The base provided is not valid. Valid bases are "b", "o", "d", and "x".
```

Use the first for an unsupported all-numeric value and the second for any unsupported string.

Invalid panels written with equals syntax return 1 and use `Error: failed to parse `--panels` arg "VALUE" as unsigned nonzero integer`, followed by a `Caused by:` line containing `invalid digit found in string`, `number would be zero for non-zero type`, or another underlying unsigned parse error. A separated negative panel token is a status-2 unexpected-argument error because it begins with `-`. In particular, `--panels -1` has empty stdout and starts stderr with `error: unexpected argument '-1' found`.

An invalid enumerated choice for color, border, character table, color scheme, group size, endianness, or completion is a status-2 command-line error that names the bad value and prints `possible values` followed by the complete accepted set from Spec 2. In particular group size 3 lists `1, 2, 4, 8`; an invalid color lists at least `always, auto, never, force`; and an invalid completion shell lists bash through zsh. A missing value for `-n` is diagnosed using its canonical name `--length`. A nonnumeric terminal width is rejected rather than ignored.

A missing file is exactly `Error: No such file or directory (os error 2)\n`. A directory is `Error: 'PATH' is a directory.\n`.

Conflicting options are status 2. The essential exact forms are:

```text
error: the argument '--include' cannot be used with '--endianness <FORMAT>'

Usage: executable --include [FILE]

For more information, try '--help'.
```

`-e` replaces `--endianness <FORMAT>` when that alias caused the conflict. Panels versus terminal width names both arguments as `--panels <N>` and `--terminal-width <N>`, says `cannot be used with`, and names first in the diagnostic and usage line whichever conflicting option occurred first. It ends with the same help hint. In particular the snapshot invocation `--color=never --panels=2 --terminal-width=100 FILE` produces:

```text
error: the argument '--panels <N>' cannot be used with '--terminal-width <N>'

Usage: executable --color <WHEN> --panels <N> <FILE>

For more information, try '--help'.
```

The reverse order `--terminal-width=100 --panels=2` with stdin produces exactly:

```text
error: the argument '--terminal-width <N>' cannot be used with '--panels <N>'

Usage: executable --terminal-width <N> [FILE]

For more information, try '--help'.
```

## Spec 19

These additional exact uncolored examples are normative cross-checks for the combined renderer.

Default input bytes `00..1f`, length 32:

```text
┌────────┬─────────────────────────┬─────────────────────────┬────────┬────────┐
│00000000│ 00 01 02 03 04 05 06 07 ┊ 08 09 0a 0b 0c 0d 0e 0f │⋄•••••••┊•__•__••│
│00000010│ 10 11 12 13 14 15 16 17 ┊ 18 19 1a 1b 1c 1d 1e 1f │••••••••┊••••••••│
└────────┴─────────────────────────┴─────────────────────────┴────────┴────────┘
```

The same first 16 bytes with one panel occupy two rows:

```text
┌────────┬─────────────────────────┬────────┐
│00000000│ 00 01 02 03 04 05 06 07 │⋄•••••••│
│00000008│ 08 09 0a 0b 0c 0d 0e 0f │•__•__••│
└────────┴─────────────────────────┴────────┘
```

Binary `ABC` uses one automatically selected panel:

```text
┌────────┬─────────────────────────────────────────────────────────────────────────┬────────┐
│00000000│ 01000001 01000010 01000011                                              │ABC     │
└────────┴─────────────────────────────────────────────────────────────────────────┴────────┘
```

With `--no-characters`, stdin `ABC` is:

```text
┌────────┬─────────────────────────┬─────────────────────────┐
│00000000│ 41 42 43                ┊                         │
└────────┴─────────────────────────┴─────────────────────────┘
```

With `--no-position`, it is:

```text
┌─────────────────────────┬─────────────────────────┬────────┬────────┐
│ 41 42 43                ┊                         │ABC     ┊        │
└─────────────────────────┴─────────────────────────┴────────┴────────┘
```

All rules compose: skip/length determine bytes, display offset determines labels, panel count determines row chunking, base determines digits, grouping/endianness determine numeric byte order, character table determines character glyphs, squeezing operates on original full rows, border/layout determine cells, and color is finally applied by original byte category.
