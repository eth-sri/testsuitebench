# `executable` behavioral specification

The required artifact is one runnable program named exactly `executable`. All text described below is UTF-8/ASCII, and every shown space and newline is significant where an output is described as exact.

## Spec 1

`executable` is a command-line byte viewer with three mutually prioritized output modes: sine-function output, source-code array output, and ordinary byte-dump output. A successful invocation exits with status 0 and writes its result to standard output with nothing on standard error. Command-line parsing failures use status 2. Failures discovered while converting numeric options or opening/reading input use status 1 and write only to standard error.

The supported invocation is:

```text
executable [OPTIONS] [INPUTFILE]
```

At most one `INPUTFILE` is accepted. With one, its raw bytes are used and standard input is ignored. With none, raw bytes are read from standard input until EOF. Input is never decoded, normalized, or treated as lines: NULs, invalid UTF-8, CR, LF, and multibyte UTF-8 sequences are all independent bytes. File names may contain spaces, and normal file symlinks are followed.

## Spec 2

These options and only these options are supported:

```text
-c, --cols <columns>
-l, --len <len>
-f, --format <format>
-t, --color <color>
-a, --array <array_format>
-u, --func <func_length>
-p, --places <func_places>
-r, --prefix <prefix>
-h, --help
-V, --version
```

Value-taking short options accept either a separate value (`-c 8`) or an attached value (`-c8`, `-fb`, `-ar`). Long options accept a separate value or `=` syntax (`--cols 8`, `--cols=8`). Options may precede or follow `INPUTFILE`, and mixed short/long forms have identical semantics. `--` ends option recognition, so a following dash-leading token is the input-file name. More than one positional token is an error. Each value-taking option may occur at most once, including repetitions that mix its short and long spelling.

`format` is case-sensitive and is exactly one of `o`, `x`, `X`, and `b`. `array_format` is exactly one of `r`, `c`, `g`, `p`, `k`, `j`, `s`, and `f`. `color` and `prefix` are exactly `0` or `1`. In particular, formats `e`, `E`, and `p`, multi-character names, numeric strings, empty strings, whitespace-padded strings, and every other format value are invalid.

## Spec 3

`-h` and `--help` exit 0, write nothing to standard error, and write the following exact text to standard output, including the two empty lines before `Usage:` and one final newline:

```text
Futuristic take on hexdump, made in Rust.


Usage: executable [OPTIONS] [INPUTFILE]

Arguments:
  [INPUTFILE]  Pass file path as an argument, or input data may be passed via stdin

Options:
  -c, --cols <columns>        Set column length
  -l, --len <len>             Set <len> bytes to read
  -f, --format <format>       Set format of octet: Octal (o), LowerHex (x), UpperHex (X), Binary (b) [possible values: o, x, X, b]
  -t, --color <color>         Set color tint terminal output. 0 to disable, 1 to enable [possible values: 0, 1]
  -a, --array <array_format>  Set source code format output: rust (r), C (c), golang (g), python (p), kotlin (k), java (j), swift (s), fsharp (f) [possible values: r, c, g, p, k, j, s, f]
  -u, --func <func_length>    Set function wave length
  -p, --places <func_places>  Set function wave output decimal places
  -r, --prefix <prefix>       Include prefix in output (e.g. 0x/0b/0o). 0 to disable, 1 to enable [possible values: 0, 1]
  -h, --help                  Print help
  -V, --version               Print version
```

Help takes immediate precedence when encountered before later arguments: for example, `--help --definitely-not-a-flag` still prints help successfully. A `--help` after the `--` separator is an input-file name instead. Help is never colorized.

## Spec 4

`-V` and `--version` exit 0 with empty standard error and exact standard output:

```text
hx 0.7.0
```

There is one final newline. Help and version do not require or read input. When combined with otherwise valid preceding options, either information flag takes precedence over ordinary processing.

## Spec 5

For byte-reading modes, `--len`/`-l` is an unsigned decimal byte limit. Its default is unlimited. A value of 0 also means unlimited. A positive value `L` retains the first `min(L, input size)` bytes, and all declarations, rows, offsets, and byte counts use that retained length. A limit larger than the input is harmless.

`--cols`/`-c` is an unsigned decimal count of bytes per output row. Its default is 10. A value of 0 is normalized to 1 for forming rows, but the original zero is still used by ordinary mode's missing-column padding calculation; Specs 6 and 8 describe the resulting unpadded terminal row. Other representable positive values pass argument parsing, including values such as 1, 32, 1,000, and 999,999. Very wide ordinary rows can subsequently encounter the deterministic padding-format failure in Spec 6. Column width changes row breaks and alignment but never changes which bytes are read. Length limiting happens before rows are formed.

## Spec 6

In ordinary byte-dump mode, each row starts with a lowercase hexadecimal offset formatted as `0x` followed by at least six zero-padded digits, then `: `; for example `0x000000: `, `0x00000a: `, and `0x001000: `. The offset is the zero-based index of the row's first byte, and advances by the effective row width: the configured column count when positive, or 1 when `--cols=0`.

After the address comes a numeric area with one present-byte position per byte in the row, followed by padding for absent columns. A present byte occupies its formatted token followed by one literal space, using the present-byte slot width in Spec 7. Let `C` be the originally supplied column count (or the default 10) and `K` the number of present bytes in this row. For positive `C`, the padding is exactly `5 * (C - K)` literal spaces. It is therefore five spaces per missing column regardless of the selected numeric format or whether prefixes are enabled: missing positions are not widened for octal or binary and are not narrowed when prefixes are disabled. For `C=0`, rows are formed with the effective width 1 but the padding is always zero spaces, including on the terminal empty row. The ASCII preview immediately follows the present tokens and padding, with no additional separator. Each retained byte contributes one preview character: byte values `0x20` through `0x7e` inclusive contribute that ASCII character; every other value contributes `.`. Thus space is preserved as a preview space, while tab, CR, LF, DEL, high bytes, and NUL become dots.

The padding is subject to a deterministic formatting limit. A padding count through 65,535 spaces is written normally. If `5 * (C - K)` exceeds 65,535, the program writes the offending row's address and all its present numeric tokens (including their trailing spaces), but no padding, preview, row-ending newline, subsequent rows, or byte-count footer. It then exits with status 101. Standard error has this exact shape under the default environment, where `ID` is a runtime-assigned decimal identifier and has been observed to differ between processes:

```text

thread 'main' (ID) panicked at src/lib.rs:<error location>:
Formatting argument out of range
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

Each displayed line, including the final line, ends in `\n`; the first line is empty. For example, a one-byte prefixless-hexadecimal row succeeds with `-c13108` because its padding is 65,535 spaces, while the same row with `-c13109` exits 101 after writing exactly `0x000000: 5a ` to standard output.

After all rows of a normally completed dump, write the exact footer `   bytes: N\n`, where `N` is the retained byte count in ordinary decimal. Every completed row ends in `\n`, as does the footer.

## Spec 7

The ordinary-mode numeric token is selected by `-f`/`--format`; the default is `x`. Tokens are fixed-width and are never shortened:

| Value | Meaning | Token for byte 171 with prefixes | Digits without prefix | Slot width with/without prefix |
|---|---|---|---|---|
| `x` | lowercase hexadecimal | `0xab` | `ab` (2 digits) | 5 / 3 |
| `X` | uppercase hexadecimal digits | `0xAB` | `AB` (2 digits) | 5 / 3 |
| `o` | octal | `0o0253` | `0253` (4 digits) | 7 / 5 |
| `b` | binary | `0b10101011` | `10101011` (8 digits) | 11 / 9 |

The slot widths in the table apply only to present bytes and include the required trailing space; absent columns use the five-space padding calculation (and its `--cols=0` exception) specified in Spec 6. `-r 1`/`--prefix 1` enables prefixes and is the default; `-r 0` removes the prefix only from byte tokens. The offset always retains its `0x` prefix. Formatting and prefix selection do not affect offsets, preview characters, row breaks, or the byte count.

## Spec 8

Ordinary mode has an intentional end-row behavior. It always emits a row for the current offset, even when that row has no bytes. Let `E` be the effective row width: `E=C` for a positive configured count `C`, and `E=1` for `C=0`. If retained length `N` is zero or is an exact multiple of `E`, an additional empty row appears at offset `N`. If `N mod E` is nonzero, the final partial row is the last row and no empty row follows it.

For a positive column count, that empty row has five padding spaces per column, even in octal or binary format. With `--cols=0`, the effective row width is one, so an exact-multiple input still produces the additional empty row, but its numeric area has zero padding. For example, the terminal row after the three bytes `69 6c 0a` is exactly `0x000003: \n`.

With defaults, uncolored input bytes `69 6c 0a` produce exactly:

```text
0x000000: 0x69 0x6c 0x0a                                    il.
   bytes: 3
```

Empty input produces exactly 50 spaces after `0x000000: ` (ten empty 5-character hex slots):

```text
0x000000:                                                   
   bytes: 0
```

Ten `X` bytes with the default ten columns demonstrate the extra empty row:

```text
0x000000: 0x58 0x58 0x58 0x58 0x58 0x58 0x58 0x58 0x58 0x58 XXXXXXXXXX
0x00000a:                                                   
   bytes: 10
```

## Spec 9

Color applies only to ordinary byte-dump mode. Explicit `-t 0` disables it and explicit `-t 1` enables it. An explicit value takes precedence over the environment. Without `-t`, color is enabled only when standard output is a terminal and the `NO_COLOR` environment variable is absent; captured or piped output is therefore uncolored by default. The presence of `NO_COLOR`, regardless of its value, disables implicit color. Array, function, help, version, padding, offsets, and byte-count footers are never colored.

When enabled, each numeric byte token and its corresponding single preview character are independently wrapped as:

```text
ESC[38;5;MmTEXTESC[0m
```

Here `ESC` is byte `0x1b`, and palette number `M` equals the byte value except that byte `0x00` uses palette number 22. The separator after a numeric token is outside the escape sequences. ANSI sequences have zero layout width: padding is exactly the same as in uncolored output. For example byte `0x41` is rendered numerically as `\x1b[38;5;65m0x41\x1b[0m` and in the preview as `\x1b[38;5;65mA\x1b[0m`. Removing all `ESC[...m` sequences from a colored result yields the corresponding uncolored result byte-for-byte.

## Spec 10

If `-a`/`--array` is present, source-code array mode replaces the ordinary dump. It writes no offset, ASCII preview, byte-count footer, or ANSI escape sequence. Array values are always lowercase two-digit hexadecimal with `0x` prefixes, regardless of `--format`, `--prefix`, or `--color`; those three otherwise-valid settings are ignored in this mode. `--len` still truncates the data, and the declaration's length is the actual retained byte count. `--cols` still controls body-line wrapping.

Every array body line starts with four spaces. Bytes are separated by `, `, except F# uses `; `. A separator is present after every non-final byte in the overall array, including at the end of an intermediate row. The final byte has no separator except in Go, where every byte, including the final byte, has `, ` after it. The opening declaration, every body line, and the closing delimiter each end in `\n`.

As in ordinary mode, there is an intentional empty-body-row behavior: a four-space empty body line is emitted for empty input and after the last data row whenever a nonempty retained length is an exact multiple of the column count. There is no such extra line after a partial final row.

## Spec 11

Array language `r` is exact Rust syntax:

```text
let ARRAY: [u8; N] = [
    BODY
];
```

Array language `c` is exact C syntax:

```text
unsigned char ARRAY[N] = {
    BODY
};
```

Here and in the remaining array templates, `N` is replaced by the retained decimal byte count and `BODY` represents the body rules from Spec 10. For example, Rust input `74 65 73 74` produces exactly:

```text
let ARRAY: [u8; 4] = [
    0x74, 0x65, 0x73, 0x74
];
```

The Rust and C results must be syntactically valid source when placed in a suitable containing Rust function or C translation unit.

## Spec 12

The other six array-language templates are exact:

| Code | Opening line | Closing line | Literal rule |
|---|---|---|---|
| `g` | `a := [N]byte{` | `}` | normal `0xhh` plus mandatory `, ` even after the final byte |
| `p` | `a = [` | `]` | normal `0xhh` |
| `k` | `val a = byteArrayOf(` | `)` | normal `0xhh` |
| `j` | `byte[] a = new byte[]{` | `};` | normal `0xhh` |
| `s` | `let a: [UInt8] = [` | `]` | normal `0xhh` |
| `f` | `let a = [|` | `|]` | `0xhhuy`, separated by `; ` rather than commas |

For clarity, the same four bytes `74 65 73 74` produce these complete bodies for Go and F#:

```text
a := [4]byte{
    0x74, 0x65, 0x73, 0x74, 
}
```

```text
let a = [|
    0x74uy; 0x65uy; 0x73uy; 0x74uy
|]
```

## Spec 13

If `-u`/`--func` is present, function mode has precedence over both array and ordinary output. Its unsigned decimal argument `N` selects exactly `N` values. For each integer index `y` from 0 through `N-1`, calculate using double-precision floating point:

```text
sin((y / N) * pi / 2)
```

Format every value in fixed-point notation, rounded to exactly `P` digits after the decimal point, where `P` comes from `-p`/`--places` and defaults to 4. `P=0` emits no decimal point. Append a comma immediately after every value, with no spaces. Insert a newline after every tenth value. After the loop, always emit one additional newline. Thus `N=0` outputs exactly one newline, while a positive multiple of ten ends with two newlines. A final non-full group occupies one line and ends with comma-newline.

Examples are exact:

```text
executable -u 5 -p 2
0.00,0.31,0.59,0.81,0.95,
```

```text
executable -u 10 -p 0
0,0,0,0,1,1,1,1,1,1,

```

Function mode ignores input data or an input-file argument and ignores otherwise-valid `--format`, `--array`, `--cols`, `--len`, `--prefix`, and `--color` settings. It never emits ANSI escapes, a byte count, or array/dump syntax. It supports at least 1,000 generated values and precision through at least 10 places.

## Spec 14

Argument-choice validation occurs before any file is opened. Invalid `format`, `array`, `color`, or `prefix` values exit 2, leave standard output empty, and use these exact stderr shapes (substitute the supplied value and the relevant option):

```text
error: invalid value 'VALUE' for '--format <format>'
  [possible values: o, x, X, b]

For more information, try '--help'.
```

```text
error: invalid value 'VALUE' for '--array <array_format>'
  [possible values: r, c, g, p, k, j, s, f]

For more information, try '--help'.
```

For color and prefix, the option labels are respectively `--color <color>` and `--prefix <prefix>`, and the possible-values line is `[possible values: 0, 1]`. An explicitly empty choice value is treated as no value. A missing choice value uses `error: a value is required for '--OPTION <label>' but none was supplied`, followed by its two-space-indented possible-values line, a blank line, and the same help suggestion. Every line, including the last, ends in a newline.

## Spec 15

A missing value for any other value-taking option is also a status-2 parse failure on standard error and identifies the normalized long option, for example `a value is required for '--cols <columns>'`, `a value is required for '--len <len>'`, `a value is required for '--func <func_length>'`, or `a value is required for '--places <func_places>'`.

An unknown option exits 2 and includes `error: unexpected argument 'TOKEN' found`, the line `Usage: executable [OPTIONS] [INPUTFILE]`, and `For more information, try '--help'.` on standard error. An extra positional argument has the same status and `unexpected argument` treatment. A dash-leading value supplied as a separate token, such as the `-1` in `-l -1`, is parsed as an unexpected option rather than as the preceding value. After `--`, however, dash-leading text is positional.

Repeating a value option exits 2 with empty standard output and exact stderr of this form:

```text
error: the argument '--format <format>' cannot be used multiple times

Usage: executable [OPTIONS] [INPUTFILE]

For more information, try '--help'.
```

The normalized labels for the other duplicate errors are exactly those shown in the option list, such as `--cols <columns>` and `--array <array_format>`.

## Spec 16

The arguments of `cols`, `len`, and `func`, and `places` when used by function mode, are converted as nonnegative machine-size unsigned decimal integers after command-line parsing. A nonnumeric or negative attached string is a status-1 failure with empty standard output and these exact two stderr lines, using the appropriate option names:

```text
-c, --cols <integer> expected. ParseIntError { kind: InvalidDigit }
error: invalid digit found in string
```

The analogous first lines begin `-l, --len`, `-u, --func`, or `-p, --places`. A decimal integer too large for the target type likewise exits 1; its first line ends `ParseIntError { kind: PosOverflow }` and its second line is `error: number too large to fit in target type`. The executable is evaluated on a 64-bit platform. No partial normal output is written for these failures.

## Spec 17

Failure to open or read an input file exits 1, produces no standard output, and writes one line to standard error in this shape:

```text
error: OS-ERROR-TEXT
```

The operating-system text is preserved. On the evaluation platform, a nonexistent path therefore gives exactly `error: No such file or directory (os error 2)\n`, and a directory used as a file gives `error: Is a directory (os error 21)\n`. Invalid command choices must be diagnosed before these I/O errors. Supplying a real input file together with data on standard input is not an error; only the file is read.

## Spec 18

Outside the exact ordinary-mode padding-failure condition in Spec 6, the executable handles arbitrary binary input and large streams without corrupting, skipping, duplicating, or sign-extending bytes. This includes the complete byte range, repeated NUL/`0xff` data, files around 255, 256, 4,095, and 4,096 bytes, and streams of at least 5 MiB; a 5 MiB stream with the default ten columns completes with the footer `   bytes: 5242880\n`. Output offsets and the decimal footer remain correct. When a sufficiently wide final partial or empty row does meet Spec 6's condition, the executable deterministically emits the described partial standard output and exits 101. In particular, a large representable `--cols` value does not guarantee successful ordinary output merely because parsing accepted it.

If a downstream pipe closes while any ordinary or array output is being written, treat the resulting broken-pipe condition as successful early termination: exit 0 promptly and write nothing to standard error. This applies with every numeric format, color enabled, prefix disabled, custom columns, length limits, file or standard-input sources, and Rust, C, or Python array output.
