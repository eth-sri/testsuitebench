# Clarified executable specification

The required artifact is a single executable file named `executable`. It is a command-line FIGlet renderer compatible with the observable behavior of FIGlet 2.2.5 (31 May 2012), including its historical parsing and formatting quirks. Unless a section says otherwise, output comparisons are byte-for-byte: spaces at the ends of rows, leading indentation, row order, and final newlines are significant. The font and control-file data placed in `fonts/` or supplied through command-line paths are runtime inputs; the executable must parse them rather than recognize only a fixed collection of messages.

## Spec 1

`executable` is one option-driven program, not a subcommand dispatcher. It must exist, be executable, terminate without hanging, write rendered FIGures to standard output, and write diagnostics to standard error. Words such as `add`, `help`, `list`, `remove`, and `show` are ordinary message words. There are no long options and no help subcommand. In particular, `--help`, `--version`, `-h`, and `-?` are invalid-option invocations.

Normal successful rendering and information queries return status 0. Invalid options, missing option operands, missing font/control files, and invalid fonts return status 1. A normal successful invocation has empty standard error. An error occurring before rendering has empty standard output.

Auxiliary commands such as `showfigfonts`, when present in a harness, are harness-provided programs. They are not subcommands or additional behaviors of `executable`; they may simply invoke `executable` repeatedly with ordinary options.

## Spec 2

The accepted short options are:

```text
-A -D -E -X -L -R -x -l -c -r -p -n -s -k -S -o -W -t -v -N
-I value  -m value  -w value  -d value  -f value  -C value
```

Short no-operand options may be grouped, for example `-klR`, `-WrR`, `-kc`, and `-kpc`. An option requiring an operand takes the rest of the same argument if present (`-w40`, `-I2`, `-ffoo`) or the next argument otherwise. Consequently, `-wf` means `-w` with the operand `f`. Use GNU/POSIX `getopt`-style option permutation: recognized options can be found even when interspersed with non-option words. Repeated/conflicting state options are processed left to right and the last one wins, except for the explicitly described `-t` behavior.

The public usage synopsis deliberately omits the historical `-A` option and is exactly:

```text
Usage: executable [ -cklnoprstvxDELNRSWX ] [ -d fontdirectory ]
              [ -f fontfile ] [ -m smushmode ] [ -w outputwidth ]
              [ -C controlfile ] [ -I infocode ] [ message ]
```

## Spec 3

After option processing, the presence of any positional argument automatically selects command-line input mode; `-A` selects it even with no positional arguments. In command-line mode standard input is ignored completely. Bytes in each positional argument are consumed literally. When a nonempty argument ends and any further argument exists, consume one ASCII space before examining that next argument. Each empty argument except the last supplies a newline; a final empty argument instead ends input without supplying a character. It does not remove a space already supplied after a preceding nonempty argument. Thus separate arguments `One`, `Two`, `Three` behave like `One Two Three`, while `hello`, empty, `world` behaves like `hello \nworld`: the space after `hello` remains immediately before the newline. A leading empty argument followed by `world` behaves like `\nworld`; a lone empty argument contributes nothing.

Without command-line input mode, consume standard input as a byte stream until EOF. The font and all named control files are opened before input is consumed, so an invocation without a usable default font fails even if stdin is empty. No terminal prompting is performed.

## Spec 4

Defaults are: font directory `/usr/local/share/figlet`, font name `standard`, width 80, font-selected direction, direction-selected justification, normal newline mode, no German substitution, an empty control-file list, and the font's own horizontal layout. `FIGLET_FONTDIR`, when set (including to a nonexistent path), replaces the compiled default directory. A later `-d directory` replaces the environment value. `-f name` selects a font, and the last `-f` wins.

`-w operand` parses its operand with C `atoi` semantics: leading whitespace and a sign are allowed, parsing stops at the first nondigit, and a string with no initial number produces zero. Update the width only when the parsed result is positive; zero and negative values leave the previous width unchanged. `-t` attempts to obtain the column count of `/dev/tty` and updates the width only if that succeeds with a positive value. In a noninteractive test process it therefore normally retains 80. An explicit positive `-w` remains effective if a later `-t` cannot obtain a width. The effective internal line limit is width minus one, except that width 1 has the special behavior in Spec 21.

## Spec 5

`-v` and `-I 0` select the same information response. All options are processed before an information response, so `-I3 -f banner` and `-f banner -I3` both report `banner`; the last `-I` or `-v` determines the response. An information response ignores positional input and stdin, does not open fonts or control files, and creates no files.

The exact `-v`/`-I 0` output is:

```text
FIGlet Copyright (C) 1991-2012 Glenn Chappell, Ian Chai, John Cowan,
Christiaan Keet and Claudio Matsuoka
Internet: <info@figlet.org> Version: 2.2.5, date: 31 May 2012

FIGlet, along with the various FIGlet fonts and documentation, may be
freely copied and distributed.

If you use FIGlet, please send an e-mail message to <info@figlet.org>.

The latest version of FIGlet is available from the web site,
	http://www.figlet.org/

Usage: executable [ -cklnoprstvxDELNRSWX ] [ -d fontdirectory ]
              [ -f fontfile ] [ -m smushmode ] [ -w outputwidth ]
              [ -C controlfile ] [ -I infocode ] [ message ]
```

Every displayed line, including the last, ends in LF. The tab before the URL is one literal tab byte.

## Spec 6

`-I operand` also uses `atoi`. The responses are exactly:

```text
code 1: 20205\n
code 2: <effective font directory>\n
code 3: <selected font name>\n
code 4: <effective positive output width in decimal>\n
code 5: flf2 tlf2\n
```

For code 3, a final `.flf` or `.tlf` suffix is removed case-insensitively when `-f` is parsed; other path/name text is preserved. A positive code other than 0 through 5 exits successfully with no output. `-I abc` is code 0, and `-I 5xyz` is code 5. `-I -1` means normal rendering. Any other negative code also falls through to normal rendering; it will therefore fail on the default font when that font is unavailable.

## Spec 7

Unknown options use the process's original `argv[0]` in the first diagnostic line, then the three-line usage block from Spec 2 using only the basename `executable`. For example, when invoked as `/workspace/executable -Z`, standard error is:

```text
/workspace/executable: invalid option -- 'Z'
Usage: executable [ -cklnoprstvxDELNRSWX ] [ -d fontdirectory ]
              [ -f fontfile ] [ -m smushmode ] [ -w outputwidth ]
              [ -C controlfile ] [ -I infocode ] [ message ]
```

The invalid character reflects the `getopt` parsing of the supplied argument; long-looking options are still rejected by this short-option parser. A recognized option with no operand similarly begins `<argv[0]>: option requires an argument -- '<letter>'`, followed immediately by the same usage block. Both cases return 1 and write nothing to stdout.

`-F` is recognized only to issue this special basename-based error and return 1:

```text
executable: illegal option -- F
Usage: executable [ -cklnoprstvxDELNRSWX ] [ -d fontdirectory ]
              [ -f fontfile ] [ -m smushmode ] [ -w outputwidth ]
              [ -C controlfile ] [ -I infocode ] [ message ]

Because of numerous incompatibilities, the "-F" option has been
removed.  It has been replaced by the "figlist" program, which is now
included in the basic FIGlet package.  "figlist" is also available
from  http://www.figlet.org/under UNIX utilities.
```

## Spec 8

Font and control-file lookup is case-sensitive except for recognizing/removing a supplied suffix. For a requested name without either `/` or `\`, first try `<effective-font-directory>/<name><suffix>`, then `<name><suffix>` relative to the current directory. For a name containing either directory separator, try only that name plus the suffix. A font lookup first uses suffix `.flf`; if absent, it tries `.tlf`. A control lookup uses `.flc`. Supplying the matching suffix explicitly is equivalent because it is stripped before lookup. Font names themselves are not case-folded (`Banner` does not find `banner.flf`).

Failure reports the stripped requested name, not every attempted pathname:

```text
executable: NAME: Unable to open font file
executable: NAME: Unable to open control file
```

These lines end in LF and cause status 1. Control files are opened in their option order before the font, so an unavailable control file is reported first.

## Spec 9

A file may be an ordinary font/control file or a ZIP stream stored under the ordinary `.flf`, `.tlf`, or `.flc` filename. Detect the little-endian local-header signature `PK\x03\x04`, read the local entry containing the font data, and inflate deflate method 8. Normal compression levels, long decompressed data, and archives created by standard ZIP writers must work. The local filename is irrelevant. A valid compressed font renders identically to its uncompressed contents under every layout, width, direction, and justification option.

Encrypted entries, malformed/short local headers, bad signatures, unsupported compression methods, empty archives, or decompressed non-font contents must fail through ordinary font validation, normally as `Not a FIGlet 2 font file`. CRC damage discovered only after useful data has already been consumed must not erase already produced deterministic rendering. Treat a nonqualifying ZIP container as raw file data, which then fails the font magic check.

## Spec 10

An FLF font begins with four-byte magic `flf2`; a TLF font begins with `tlf2`. The fifth byte is a signature/version placeholder, the sixth is the hardblank, followed by whitespace-separated header numbers equivalent to:

```text
magic+placeholder+hardblank height baseline max_length old_layout comment_lines
    [print_direction [full_layout [codetag_count ...]]]
```

The parser requires the hardblank plus `height`, `max_length`, `old_layout`, and `comment_lines`; `baseline` is syntactically consumed but otherwise ignored. The header type must match the file type selected by lookup. Normalize LF, CR, and CRLF line endings. Header text is bounded safely; an overlong header is truncated for parsing and its remainder is skipped. A missing newline/EOF header that cannot yield the required fields is invalid.

Reject bad/wrong magic and nonnumeric or too-short headers with `executable: NAME: Not a FIGlet 2 font file\n`. Reject a declared `max_length` greater than 255 with `executable: NAME: character is too wide\n`. Clamp `height < 1` to 1 and `max_length < 1` to 1. Negative `comment_lines` behaves as zero; otherwise skip exactly that many complete lines. If `print_direction` is absent, use 0 (left-to-right).

## Spec 11

After comments, read exactly `height` rows for each required glyph in this order: codes 32 through 126, then 196, 214, 220, 228, 246, 252, and 223. For every row, remove trailing line-ending/whitespace, take its last remaining character as the row's endmark, remove the entire final run of that endmark, and retain all preceding bytes/characters—including meaningful spaces. EOF or a missing row yields an empty row rather than a crash. The first row's retained length is the glyph width; valid fonts normally use that width on every row.

After the 102 required glyphs, repeatedly parse a code-tag line as a C-style signed integer (`decimal`, leading-zero octal, or `0x` hexadecimal), then read one glyph of `height` rows. Stop extended-glyph loading at the first line whose beginning is not a number. Extended glyphs may use signed 32-bit codes other than -1. Duplicate codes are resolved in favor of the last definition.

Before loading, create an empty missing-glyph entry at code 0. A code-tagged glyph 0 replaces it. When an input code is absent, render glyph 0; if no explicit glyph 0 exists this adds no visible width. This behavior is important for arbitrary Unicode, control values, and malformed byte streams.

## Spec 12

TLF files use the same header, glyph ordering, endmarks, and layout semantics as FLF files, but each glyph row is decoded from UTF-8 to wide characters and output is encoded back to UTF-8. A `.tlf` file with `flf2` magic and a `.flf` file with `tlf2` magic are invalid. Font names without an extension try FLF before TLF. The reported supported-format string is always `flf2 tlf2`.

The executable must handle height-one passthrough fonts (`term`, `mnemonic`), compact fonts (`mini`, `small`), taller/wider fonts (`banner`, `big`, `block`), right-to-left fonts (`ivrit` and custom headers), and Unicode TLF fonts. The files already present under `fonts/` and `assets/` are normative examples and may be used directly, but runtime-provided fonts following the same grammar must also work.

## Spec 13

The old and full layout fields are decoded as follows. If `full_layout` is present, use it. If absent, convert `old_layout`: zero becomes 64 (kerning); a negative value becomes 0 (full width); a positive value becomes `(old_layout & 31) | 128` (controlled smushing, retaining only the five legacy rule bits). In a full layout value, bit 64 selects horizontal kerning by default and bit 128 selects horizontal smushing by default (128 overrides 64). Bits 1, 2, 4, 8, 16, and 32 enable the six horizontal smush rules. Vertical-layout bits may be parsed but this executable does not vertically compose successive input lines.

User overrides are:

```text
-s       discard a previous user override and use the font layout
-k       layout 64, kerning only
-W       layout 0, full width
-o       layout 128, universal overlap/smush
-S       force smushing: start with 128, then bitwise-OR the font layout
-m n     atoi(n); n < -1 => discard override/use font; n == -1 => 0;
         n == 0 => 64; otherwise => (n & 63) | 128
```

Only the last spacing override controls the result. Thus `-m xyz` is kerning, `-m 999999` uses its low six rule bits plus 128, `-m -2` uses the font default, and `-m 144` enables smushing with rule 16.

## Spec 14

Horizontal composition maintains `height` output rows. Full-width mode appends (LTR) or prepends (RTL) every complete glyph row. In kerning or smushing mode, find the largest common horizontal shift that is legal across all rows: leading/trailing ordinary spaces may overlap freely; kerning stops just before two visible/nonblank cells would share a column; smushing may shift one additional column only where the colliding pair is resolved by Spec 15. Hardblanks participate as protected visible cells during fitting. Glyphs whose current or previous width is below 2 cannot smush visible cells.

For exact compatibility, use the following boundary calculation. Let `L` be the current logical width (the length of old row 0), `W` the incoming glyph width (new row 0), and initialize the candidate shift to `W`. For each LTR row, let `linebd` be the index of the last non-space in the old row (begin by examining the NUL position and walk left over NUL/spaces), and let `charbd` be the count of leading spaces in the new row. Set `amt = charbd + L - 1 - linebd`; increment `amt` if the old boundary is empty/space, or if the new boundary exists and the boundary pair can smush. For each RTL row, first cap the candidate at the old row length; let `charbd` be the index of the last non-space in the new row and `linebd` the count of leading spaces in the old row. Set `amt = linebd + W - 1 - charbd` and apply the same empty/merge increment. The permitted shift is the minimum `amt` over all rows.

To compose LTR, for each overlap offset `k`, merge old column `max(0, L-shift+k)` with new column `k`, then append the new row starting at `shift`. To compose RTL, begin with the new row, merge its column `W-shift+k` with old column `k`, then append the old row starting at `shift`. Set logical line length from row 0. Save each successfully added input code for possible word-boundary splitting.

The hardblank is kept internally throughout composition and replaced with an ASCII space only when a row is emitted.

## Spec 15

The cell merge function first returns the other cell if either cell is an ordinary space. With smush bit 128 absent, two visible cells cannot merge. With bit 128 present and none of bits 1–63 selected, universal smushing is used: a visible cell overrides a hardblank; otherwise the later glyph in the user's reading order dominates (right cell in LTR, left cell in RTL).

With controlled smushing, try active rules in this order and return the first result:

1. Bit 32: hardblank + hardblank becomes one hardblank. No other rule merges a hardblank.
2. Bit 1: two identical non-hardblank characters become that character.
3. Bit 2: `_` plus one of `|/\\[]{}()<>` becomes the other character, in either order.
4. Bit 4: use the later class from the hierarchy `|`, `/\\`, `[]`, `{}`, `()`, `<>` when cells come from different classes.
5. Bit 8: opposing pairs `[]`, `][`, `{}`, `}{`, `()`, or `)(` become `|`.
6. Bit 16: `/` then `\\` becomes `|`; `\\` then `/` becomes `Y`; `>` then `<` becomes `X`. `<` then `>` does not merge under this rule.

If no rule applies, the visible cells cannot share a column. These rules must work for punctuation, digits, forced-smush fonts, and both text directions.

## Spec 16

Direction options are `-L` (force left-to-right), `-R` (force right-to-left), and `-X` (return to the font header's default); last wins. LTR adds incoming glyphs to the right. RTL adds them to the left, so the visible character order is reversed while the glyph art itself is not mirrored. Smush dominance and boundary scanning must also be reversed as described above.

Justification options are `-l` (left), `-c` (center), `-r` (right), and `-x` (automatic); last wins. Automatic means left for LTR and right for RTL, resolved only after the final direction/font is known. Explicit justification is independent of direction, so combinations such as left-aligned RTL and right-aligned LTR are valid.

## Spec 17

When emitting a composed block, output exactly `height` rows. Let `len` be the stored row length. If width is greater than 1, truncate `len` to at most `width - 1`, then emit leading spaces according to this exact historical loop, where `J` is 0 for left, 1 for center, and 2 for right:

```text
for i = 1 while (3-J)*i + len + J - 2 < width:
    emit one leading space
```

No right-padding is added. Then emit exactly `len` row characters, changing hardblanks to spaces, followed by one LF. This preserves significant trailing spaces already present in glyph rows. Left output has no alignment prefix; center and right alignment are based on the effective width and on each row's actual stored length, not merely the widest visible row.

## Spec 18

Input is decoded before translation and rendering. With no multibyte-mode control command, use the ISO-2022 state machine in Spec 26, initially equivalent to ASCII in GL and Latin-1 in GR. This is intentionally not automatic UTF-8: raw UTF-8 bytes can therefore map as separate Latin-1/control codes unless a control file selects `u` mode. Do not normalize Unicode, combine accents, infer bidirectional direction, or substitute ASCII approximations. Render whatever code results from byte decoding and control-file mapping; if that code is absent, use glyph 0.

After decoding and all translations, ASCII tab and ASCII space both become one input space. Any other ASCII whitespace recognized by the C locale—including LF, CR, vertical tab, and form feed—becomes a logical newline. Codes 1 through 31 other than newline, and code 127, are ignored after mapping. Code 0 and code 128 are permitted to reach missing-glyph lookup and normally add no visible content. Invalid, high-byte, BOM, emoji, combining, CJK, and other sequences must never crash or hang.

## Spec 19

Normal newline mode (`-n`, the default) treats every logical newline as an instruction to emit the current block immediately, even if it is empty. Thus with the standard six-row font, one newline produces six LF bytes and three newlines produce eighteen. At EOF, emit the current block only when its composed logical width is positive. Consequently, EOF by itself emits nothing, and a final logical line containing input codes but only absent or entirely empty, zero-width glyphs also emits nothing. Once the block has positive logical width, EOF emits it; zero-width glyphs elsewhere in that block do not suppress it. This EOF rule does not alter explicit-newline handling: a logical newline still emits `height` LF-terminated rows when the current width is zero. Multiple empty and whitespace-only lines are not collapsed.

Paragraph mode (`-p`) preprocesses a newline as follows: if the preceding processed character was not an end-of-line whitespace, decode one character of look-ahead. Keep the newline only when that look-ahead is ASCII whitespace; otherwise—including when it is EOF—replace the newline with one space. Push the look-ahead value back so it is processed normally. In practical terms, single newlines inside a paragraph join lines with a space, while blank lines and lines followed by indentation remain paragraph breaks. `-n` after `-p` disables this behavior and vice versa.

## Spec 20

Wrapping is performed while glyphs are composed, not by slicing finished output text. A glyph fits only when `current_logical_width + glyph_width - allowed_shift <= width - 1` and the saved input-code buffer has room. Track the historical word-break state: `0` means no non-space word is pending, `1` means the line ends in a non-space and has no pending break, `2` means a non-space has been followed by one or more spaces, `3` means a non-space follows such a pending break, and `-1` means separators must be absorbed after a forced/direct emission. After successfully adding a non-space, change state to 3 if it was at least 2, otherwise 1; after adding a space, change it to 2 if it was positive, otherwise 0.

If a glyph does not fit:

- Prefer the last run of spaces already in the saved logical line as a word boundary. Rebuild and emit the prefix before that run, discard the separating run, then rebuild the suffix and retry the current character.
- If there is no usable boundary, emit the current block and retry the character on an empty block.
- If the character cannot fit even on an empty block, emit each of its rows directly. In LTR emit/truncate the row prefix; in RTL with width greater than 1 emit the row suffix of length `width - 1`. Then absorb immediately following spaces/newlines as the historical state machine does.
- A space that itself triggers overflow either performs the pending word split or emits the block, and the overflowing separator is absorbed.

More exactly, an overflowing space splits only in state 2, otherwise it emits the whole block, and then enters state -1. An overflowing non-space splits when the state is at least 2, otherwise emits the whole block; it resets state to 1 only when the prior state was 3, else to 0, then retries the same character. In state -1, absorb spaces; absorb one newline and return to state 0; a visible character returns to state 0 and is processed normally. Runs of spaces are otherwise preserved and influence word-boundary choice. This must be deterministic for very long lines (at least 1000 input characters), long unbreakable words, repeated spaces, exact-fit boundaries, and repeated wraps.

## Spec 21

Width 1 is special: every non-space FIGcharacter is emitted in its entirety as its own `height`-row block, without truncation even though the nominal line limit is zero. A following run of spaces or newline separators is absorbed before the next visible character. For widths greater than 1, every emitted row including indentation is at most `width - 1` bytes/characters under ASCII fonts. Very large widths simply avoid wrapping.

The renderer must safely handle narrow widths smaller than a glyph, widths such as 5, 9, 10, 15, 20, 30, 35, 37, 40, 50, 60, 80, 120, 200, 250, 1000, and 10000, and all their combinations with paragraph mode, direction, layout, and justification.

## Spec 22

`-D` enables this fixed pre-control-file translation:

```text
[ -> U+00C4    \\ -> U+00D6    ] -> U+00DC
{ -> U+00E4    |  -> U+00F6    } -> U+00FC    ~ -> U+00DF
```

Only those exact ranges are affected; characters such as `Z`, `^`, `_`, backtick, `z`, letters, digits, and other punctuation remain unchanged. `-E` disables German mode; last wins. German substitution applies equally to stdin and command-line input, before ordinary control-file transformations, and combines independently with font choice, direction, and justification. `-N` does not disable German mode.

## Spec 23

Each `-C name` appends a control file to an ordered list; it does not replace earlier files. `-N` clears the complete list accumulated so far and resets input decoding to its initial ISO-2022 state: G0 ASCII, G1 Latin-1 high half, G2/G3 unassigned, all single-byte, GL=G0, GR=G1. A later `-C` works normally. Reading each listed file automatically begins a new mapping stage, so transformations in later control files can act on results from earlier files.

Control files use the lookup and transparent-deflate handling from Specs 8–9. They may be empty. Ignore blank lines, `#` comment lines, an optional legacy `flc2a` line, unrecognized command lines, malformed `g` lines, and irrelevant trailing text without failing. The filename suffix may be supplied or omitted. A genuinely missing file is fatal as described in Spec 8.

## Spec 24

The control-file translation grammar is:

```text
t SRC DST
t SRC1-SRC2 DST
NUMBER NUMBER
f
b | u | h | j
g {0|1|2|3} {94|96|94x94} [DESIGNATOR]
g {L|R} {0|1|2|3}
```

Whitespace separates fields but is not allowed around the range hyphen. A `t` character is a literal single byte or a backslash form. Backslash escapes are `\a`=7, `\b`=8, `\e`=27, `\f`=12, `\n`=10, `\r`=13, `\t`=9, `\v`=11, and `\\`=92. A backslash followed by `-`, `x`, or a digit starts a signed decimal/octal/hex number; leading `0` means octal and `0x`/`0X` means hexadecimal. Any other escaped character means that character literally, so `\z` means `z`. Numeric parsing accepts a number ending exactly at EOF.

A single/range mapping stores an offset `DST-SRC1` and maps every code in inclusive `SRC1..SRC2` by that offset; the destination range's written endpoint is not needed. A two-number line is a one-code mapping. Negative numbers are valid. Malformed missing characters are treated with the parser's zero-character fallback and must not crash.

## Spec 25

Mapping commands are divided into stages by `f` (freeze) records and by the start of each control file. For one input code, scan a stage in file order, apply only its first matching range, then skip the remainder of that stage. Continue scanning at the next stage, allowing another mapping there. This makes `t A B; t B A` swap A and B within one stage, while `t a-z A-Z; f; t Q ~` allows an original or converted `Q` to become `~` in the second stage. Support many mappings without a small fixed table.

The mode commands are global and logically affect decoding before mappings regardless of their position. The last encountered `b`, `u`, `h`, `j`, or `g` mode choice wins; multiple `g` register definitions coexist. Mode `b` and mode `j` read a second byte after a lead byte in `0x80..0x9F` or `0xE0..0xEF`, producing `(lead << 8) + second`. Mode `h` uses `~{` to enter pair mode, recognizes the historical pair `}~` to leave it, reduces `~~` outside pair mode to one tilde, and discards other outside-pair `~x` sequences. A pair becomes `(first << 8) + second`.

Mode `u` follows the historical FIGlet UTF-8 decoder: ASCII bytes pass directly; lead bytes `C0..DF`, `E0..EF`, `F0..F7`, `F8..FB`, and `FC..FD` consume 1 through 5 more bytes respectively, mask every continuation with `0x3F`, and assemble a code point without modern shortest-form/range validation. A byte below `C0` in the high half, or above `FD`, becomes code 128. Premature EOF is masked in the same historical fashion and must not cause an out-of-bounds read or hang.

## Spec 26

Initial ISO-2022 registers are G0=ASCII (`base 0`, 94-character), G1=Latin-1 high half (`base 0x80`, 96-character), G2/G3 unassigned; GL=G0 and GR=G1. Control `g` commands can preconfigure them. `gN 94 D` sets GN to single-byte base `D << 16`; `gN 96 D` sets it to `(D << 16) | 0x80`; `gN 94x94 D` sets base `D << 16` and marks it double-byte. If the designator is absent its numeric value is zero. Unlike the input escape-sequence aliases below, a literal `B` or `A` in a control-file `g` command retains its byte value when forming the base. Invalid sizes, malformed `94x94`, and invalid register subcommands are skipped safely without crashing. `gL n` and `gR n` select initial GL/GR.

While decoding input, consume these escape/control sequences without rendering them:

```text
SO (0x0E) => GL=G1             SI (0x0F) => GL=G0
ESC n => GL=G2                 ESC o => GL=G3
ESC ~ => GR=G1                 ESC } => GR=G2     ESC | => GR=G3
SS2 (0x8E) or ESC N => use G2 for one decoded character, then restore GL/GR
SS3 (0x8F) or ESC O => use G3 for one decoded character, then restore GL/GR
ESC (D, )D, *D, +D => designate 94-character G0, G1, G2, G3
ESC -D, .D, /D => designate 96-character G1, G2, G3
ESC $D or ESC $(D => designate 94x94 G0
ESC $)D, $*D, $+D => designate 94x94 G1, G2, G3
```

For GL bytes `0x21..0x7E`, return `GN_base | byte`; for GR bytes `0xA0..0xFF`, return `GN_base | (byte & 0x7F)`. If the selected register is double-byte, consume a second byte and return `GN_base | (first << 8) | second`. All bytes outside those ranges pass through unless recognized above. In designations, `B` means base-zero ASCII for a 94 set and `A` means base-zero Latin-1 for a 96 set. A partial escape at EOF terminates safely. Single shifts temporarily set both GL and GR to the selected register and restore both afterward.

## Spec 27

The complete processing order for every decoded input code is: paragraph newline look-ahead; optional German substitution; all staged control mappings; ASCII whitespace/control normalization; glyph lookup; horizontal composition/wrapping; block output. Direction affects composition, and justification affects only emission. This order must remain consistent in combinations such as control-file plus nondefault font, German plus RTL, forced smush plus RTL, paragraph plus center/right alignment, or compressed TLF plus kerning.

The implementation must be memory-safe and deterministic for malformed fonts/control files, missing glyph rows, empty input, very long input, unusual signed code tags, arbitrary byte values, and repeated independent invocations. It must not emit warnings for successfully tolerated inputs. Exact rendered output is determined entirely by the supplied font rows, the decoding/mapping rules, the six smush rules, the wrapping state, and the row-emission formula above.
