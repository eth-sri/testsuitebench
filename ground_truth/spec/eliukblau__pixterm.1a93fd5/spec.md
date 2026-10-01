# Clarified PIXterm executable specification

In this document, `ESC` means the single byte `0x1b`. All ordinary text output is
UTF-8. The required artifact is one executable file named exactly `executable`.

## Spec 1

`executable` is a command-line image renderer compatible with PIXterm 1.3.2. Its
normal invocation is:

```text
executable [options] image/url
```

It decodes one local image or one HTTP(S) image, scales it to a terminal-oriented
pixel grid, and writes true-color ANSI text to standard output. Normal rendering
exits 0. Command-line usage errors exit 2. Image, filesystem, terminal-query, and
network errors exit 1. It must not emit diagnostic, warning, or debug text on a
successful non-TTY render.

Supported decoders are JPEG, PNG, GIF, BMP, TIFF, and WebP. For an animated GIF,
render only its first frame. Files may have spaces in their names, may be relative
paths, and may be symbolic links.

## Spec 2

Recognize these options (a single or double leading hyphen is accepted):

- `-h`, `-help`, `--help`: help
- `-version`: version information
- `-credits`: credits
- `-d UINT`: dithering mode, default 0
- `-go`: generate Go statements instead of emitting live ANSI escapes
- `-m COLOR`: matte color, default `000000`
- `-nobg`: suppress ANSI background colors in dithering modes
- `-s UINT`: scale method, default 0
- `-tc UINT`: terminal columns; 0 means auto/default
- `-tr UINT`: terminal rows; 0 means auto/default

For value-taking options, both `-d 1` and `-d=1` forms work. Numeric values use
Go's unsigned base-0 integer syntax, equivalent to `strconv.ParseUint` with base 0
and a 64-bit size, rather than decimal-only syntax. In particular, `0x1` is
accepted as 1, a leading `0` selects octal so `024` is accepted as 20, and `080`
is invalid.
Missing values, syntactically invalid integers, negative numbers, unknown options,
`d` outside 0..2, `s` outside 0..2, and nonzero `tc` or `tr` below 2 are usage
errors: print the exact help from Spec 3 to stdout, print nothing to stderr, and
exit 2. A literal `--` ends option parsing.

Parsing has the traditional Go `flag` behavior: it stops at the first positional
argument. That first positional argument is the image; all later arguments,
including option-looking arguments, are ignored. Thus options intended to take
effect must precede the image. If no positional argument remains, print help and
exit 2. Help encountered during option parsing prints help and exits 0; an unknown
option encountered before help still exits 2. Information flags take precedence
over image opening. If both version and credits were parsed, version wins.

## Spec 3

The help variants must write exactly the following text to stdout and exit 0, with
no stderr. It ends in a newline. In this block, each literal `<TAB>` denotes one
U+0009 tab byte and is not printed as the angle-bracketed word.

```text
   ___  _____  ____
  / _ \/  _/ |/_/ /____ ______ _      Made with love by Eliuk Blau
 / ___// /_>  </ __/ -_) __/  ' \ https://github.com/eliukblau/pixterm
/_/  /___/_/|_|\__/\__/_/ /_/_/_/                1.3.2

USAGE:

  executable [options] image/url

  Supported image formats: JPEG, PNG, GIF, BMP, TIFF, WebP.
  Supported URL protocols: HTTP, HTTPS.

OPTIONS:

  -credits
    <TAB>show some love to contributors <3
  -d mode
    <TAB>dithering mode:
    <TAB>   0 - no dithering (default)
    <TAB>   1 - with blocks
    <TAB>   2 - with chars
  -go
    <TAB>output Go code to 'fmt.Print()' the image
  -m color
    <TAB>matte color for transparency or background
    <TAB>(optional, hex format, default: 000000)
  -nobg
    <TAB>disable background color
    <TAB>(optional, only in dithering mode, ignores matte color)
  -s method
    <TAB>scale method:
    <TAB>   0 - resize (default)
    <TAB>   1 - fill
    <TAB>   2 - fit
  -tc columns
    <TAB>terminal columns (optional, >=2; when piping, default: 80)
  -tr rows
    <TAB>terminal rows (optional, >=2; when piping, default: 24)
  -version
    <TAB>show PIXterm version
  -help
<TAB>prints this message :D LOL

```

The four-line banner at the start, followed by two newline bytes, is called the
plain logo below.

## Spec 4

`-version` and `--version` write exactly `1.3.2\n` to stdout and exit 0, without
requiring or opening an image. They do not include the logo or write stderr.

In non-TTY output, `-credits`/`--credits` writes the plain logo and then exactly:

```text
CONTRIBUTORS:

  > @disq - https://github.com/disq
      + Original code for image transparency support.

  > @timob - https://github.com/timob
      + Fix for ANSIpixel type: use 8bit color component for output.

  > @HongjiangHuang - https://github.com/HongjiangHuang
      + Original code for image download support.

  > @brutestack - https://github.com/brutestack
      + Color support for Windows (Command Prompt & PowerShell).
      + Original code for disable background color in dithering mode.
      + Original code for output Go code to 'fmt.Print()' the image.

  > @diamondburned - https://github.com/diamondburned
      + NewFromImage() & NewScaledFromImage() for ANSImage API.

  > @MichaelMure - https://github.com/MichaelMure
      + More conventional 'go.mod' file at repository.

  > @Calinou - https://github.com/Calinou
      + Use HTTPS URLs everywhere.
      + Other awesome contributions.

  > @danirod - https://github.com/danirod
  > @Xpktro - https://github.com/Xpktro
      + Moral support.

```

There is one blank line between the logo and `CONTRIBUTORS:`. The block above has
its shown final newline.

## Spec 5

When stdout is a TTY, credits replace the plain logo with a fixed true-color ANSI
icon, then append the same contributor text from Spec 4. This fixed byte stream is
normatively supplied here so the visual asset needs no external source. Base64
decode the following text and decompress it as a standard gzip stream; the result
is the complete raw stdout captured through an ordinary PTY with LF-to-CRLF output
translation (13,691 bytes, 44 CRLF pairs, SHA-256
`eb944fa385b190a67cbb2ffdd889b304e91c2884a0747ad67839e123b7c36d01`):

```text
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
oT8v3pZF3o2snjEjwMBtb/4f1w/h23s1AAA=
```

The program itself writes LF; the PTY output translation accounts for the CRLF in
the supplied payload. Replacing every CRLF pair in that capture with LF produces
13,647 bytes with SHA-256
`52b8ba77f4279c259f3fcc6f2d15eafff57d2ff4f61bb4d8494661e568c3310a`.
TTY credits exit 0 and write no stderr.

## Spec 6

Terminal detection is based on **stdout**, not stdin. When stdout is not a TTY,
the detected size is 80 columns by 24 rows. When stdout is a TTY, query its actual
column and row count; a query failure is a runtime error.

Let `C` initially be the detected columns and `R` the detected rows. If `tc != 0`,
replace `C` with `tc`. Row handling deliberately preserves a compatibility quirk:

- if `tr == 0`, set internal `R = detectedRows - 1`;
- if `tr != 0`, set internal `R = tr + 1`.

Consequently a piped default classic render has 80 columns and 22 visible output
lines, while explicit `-tr N` normally has exactly N visible lines. `-tc 0` and
`-tr 0` request these detected/default values rather than being validation errors.

## Spec 7

The input is treated as a URL only when it begins, case-sensitively, with the
regular expression `^https?://`. Fetch it with an ordinary HTTP GET supporting
HTTP and HTTPS, explicit ports, IPv4 addresses, query strings, fragments, path
normalization, and redirects. A fragment is not sent to the server. Accept image
data only for status `200 OK`; every other HTTP status is the runtime error
`ANSImage: image download failed`. A 200 response is decoded by content, not by
its Content-Type or filename extension.

Anything not matching that prefix is opened as a local path. The executable never
loads image bytes from stdin.

## Spec 8

Every runtime or matte-validation error first writes the plain logo to stdout.
It then writes one stderr line of this form and exits with the indicated code:

```text
[PIXTERM ERROR] YYYY/MM/DD HH:MM:SS MESSAGE
```

Use the current local time and a trailing newline. Matte validation errors exit 2;
all other errors here exit 1. Preserve useful underlying error text. Required cases
include:

- absent file: `open PATH: no such file or directory`;
- empty file, ordinary non-image data, or directory input: `image: unknown format`;
- the supplied corrupt PNG-header fixture: `unexpected EOF`;
- a truncated PNG: text including `png: invalid format: not enough pixel data`;
- non-200 HTTP response: `ANSImage: image download failed`;
- malformed `http://`: text including `no Host in request URL`;
- DNS/TLS/connection errors: preserve the requested URL/host and the system reason,
  including `no such host`, `Get "https://`, or `connect: connection refused` as
  applicable.

Errors must be handled without a panic, hang, traceback, or partial render.

## Spec 9

`-m` takes a case-insensitive hexadecimal color without a leading `#`. The empty
value is replaced with `000000` (black). Parsing then matches
`colorful.Hex("#" + value)` from `github.com/lucasb-eyer/go-colorful` v1.2.0,
including that version's scanning quirks:

- Exactly three hex digits are RGB shorthand whose nibbles are expanded to full
  bytes. Thus `bad` is valid and means `BBAADD`.
- For other lengths, three hexadecimal fields of width at most two are scanned
  greedily into R, G, and B. Five initial hex digits suffice: `12345` becomes
  `(0x12,0x34,0x05)`. A sixth hex digit completes B; after three fields have been
  read, remaining characters are ignored, so `1234567` becomes
  `(0x12,0x34,0x56)`.

The scan is valid only when all three fields were assigned without a scan error.
Consequently, for example, four hex digits, non-hex input such as `gg0000`, and a
user-supplied leading `#` are invalid. Invalid text causes the Spec 8 exit-2 error
with:

```text
matte color : VALUE is not a hex-color
```

Because `bad` is valid shorthand, `-m bad` proceeds as an ordinary successful
render; on a TTY it therefore uses the home-and-clear prefix and final LF from
Spec 19 rather than the error path.

Decode first, scale while retaining straight-alpha RGBA, and then composite every
scaled pixel source-over an opaque matte. This ordering matters at translucent
edges. For exact 8-bit compatibility, the reference operation is an opaque RGBA
destination filled with matte followed by Go `image/draw.Draw` using `draw.Over`.
For an NRGBA source channel `s`, alpha byte `a8`, and matte byte `d`, its integer
operation is:

```text
sa = a8 * 257
sp = s * sa / 255
A  = (65535 - sa) * 257
out = uint8((d*A/65535 + sp) >> 8)
```

Apply that independently to R, G, and B. Thus fully transparent pixels become
matte pixels and opaque pixels retain their decoded color.

## Spec 10

Choose the scale target from the internal `(C,R)` in Spec 6:

- no dithering (`d=0`): target width `C`, target height `2*R` pixels;
- either dithering mode: target width `4*C`, target height `8*R` pixels.

Scale mode 0 (“resize”) resizes to exactly that target, independently changing
width and height and therefore not preserving aspect ratio.

Scale mode 1 (“fill”) preserves aspect ratio, completely covers the target, then
center-crops to the exact target. For reference compatibility, if both original
source dimensions are at least 100, crop before resizing: compare source and target
aspect ratios; crop the longer dimension to the target ratio, round the crop size
as `floor(max(1, size)+0.5)`, center it using integer division, then resize. If
either source dimension is below 100, resize first to cover: constrain width when
`sourceAspect < targetAspect`, otherwise constrain height; compute the other size
with round-to-nearest `floor(x+0.5)`, and center-crop afterward.

Scale mode 2 (“fit”) preserves aspect ratio and produces no padding. If the source
already fits in both maximum target dimensions, do not upscale it. Otherwise, if
`sourceAspect > targetAspect`, use target width and compute height as
`int(width/sourceAspect)` (truncate); else use target height and compute width as
`int(height*sourceAspect)` (truncate). Resize to those dimensions. Fit output may
therefore have fewer rows or columns than requested.

## Spec 11

All resizing is separable three-lobed Lanczos, horizontal pass followed by vertical
pass when both dimensions change. This algorithm is normative for byte-exact color
results. For one axis with source size `S` and destination size `D`:

```text
du = S / D
scale = max(du, 1)
radius = ceil(3 * scale)
sourceCenter(v) = (v + 0.5)*du - 0.5
sinc(x) = 1                         if x == 0
          sin(pi*x)/(pi*x)          otherwise
kernel(x) = sinc(abs(x))*sinc(abs(x)/3) if abs(x) < 3, else 0
```

For destination coordinate `v`, consider integer source coordinates from
`max(0, ceil(center-radius))` through `min(S-1, floor(center+radius))`. Give source
coordinate `u` weight `kernel((u-center)/scale)`, discard zero weights, and divide
all weights by their sum.

Resample straight-alpha NRGBA as follows. For every contributor, let
`aw = alphaByte * weight`; accumulate `redByte*aw`, `greenByte*aw`,
`blueByte*aw`, and `aw`. If accumulated alpha is nonzero, output each color as
`clamp(round(colorSum/alphaSum))` and alpha as
`clamp(round(alphaSum))`. Here round is `floor(x+0.5)` and clamp limits to 0..255.
When preserving one dimension from a zero argument, round its calculated size with
`floor(x+0.5)` and a minimum of one.

A direct conformance implementation may use Go's standard image decoders together
with `github.com/disintegration/imaging` version `v1.6.2` and its `Lanczos`,
`Resize`, `Fill(..., Center, ...)`, and `Fit` operations. BMP/TIFF/WebP decoding
must match `golang.org/x/image` version `v0.20.0`; the color conversion behavior
corresponds to `github.com/lucasb-eyer/go-colorful` version `v1.2.0`.

## Spec 12

After scaling and matte composition, classic mode (`d=0`) makes one terminal cell
from an upper and lower pixel at the same x coordinate. It deliberately omits the
first scaled pair for compatibility. First discard an odd final scaled pixel row,
then for pairs `(y=2,3), (4,5), ...` emit one output row. For every column emit,
without separators:

```text
ESC[48;2;UR;UG;UBmESC[38;2;LR;LG;LBm▄
```

`U` is the upper pixel and `L` the lower pixel. `▄` is U+2584. End each output row
with `ESC[0m\n`. Every cell repeats both complete color escapes even when adjacent
colors are identical. `-nobg` has no effect in classic mode.

For a scaled image height `H`, classic output has `floor(H/2)-1` rows (when that is
positive) and exactly the scaled image width in cells. This omitted-pair rule is
why explicit target height `2*(tr+1)` produces `tr` rows, default piped height 46
produces 22 rows, and fit mode can yield substantially fewer rows.

## Spec 13

As a byte-precise classic-mode example, a 2x2 RGB PNG whose rows are
`[(255,0,0),(0,255,0)]` and `[(0,0,255),(255,255,255)]`, invoked as
`-tc 4 -tr 4 IMAGE`, emits the following four logical lines. Replace each `ESC`
token with byte 0x1b and append the shown `\n` byte after each line:

```text
ESC[48;2;255;0;0mESC[38;2;208;0;47m▄ESC[48;2;196;59;0mESC[38;2;171;59;47m▄ESC[48;2;59;196;0mESC[38;2;84;196;47m▄ESC[48;2;0;255;0mESC[38;2;47;255;47m▄ESC[0m\n
ESC[48;2;155;0;100mESC[38;2;100;0;155m▄ESC[48;2;142;59;100mESC[38;2;113;59;155m▄ESC[48;2;113;196;100mESC[38;2;142;196;155m▄ESC[48;2;100;255;100mESC[38;2;155;255;155m▄ESC[0m\n
ESC[48;2;47;0;208mESC[38;2;0;0;255m▄ESC[48;2;84;59;208mESC[38;2;59;59;255m▄ESC[48;2;171;196;208mESC[38;2;196;196;255m▄ESC[48;2;208;255;208mESC[38;2;255;255;255m▄ESC[0m\n
ESC[48;2;0;0;255mESC[38;2;0;0;255m▄ESC[48;2;39;59;255mESC[38;2;25;59;255m▄ESC[48;2;216;196;255mESC[38;2;230;196;255m▄ESC[48;2;255;255;255mESC[38;2;255;255;255m▄ESC[0m\n
```

There are no spaces or extra bytes between the displayed components.

## Spec 14

In dithering modes, partition the scaled and composited image into non-overlapping
blocks of 4 pixels wide by 8 pixels high. Ignore incomplete pixels at the right or
bottom. Each block becomes one terminal cell. For all 32 pixels, average R, G, and
B separately and round each as `floor(mean+0.5)`.

For each source pixel define HSV brightness/value as
`max(R,G,B)/255` (using its composited 8-bit RGB). Average the 32 values, multiply
by 255, and round with `floor(x+0.5)` to obtain an integer brightness 0..255.

The coarse grid is `floor(scaledWidth/4)` by `floor(scaledHeight/8)`. Deliberately
omit its final row, rendering rows 0 through height-2. End every rendered row with
`ESC[0m\n`. This yields exactly `tr` rows for the usual explicit dither target.

## Spec 15

For block dithering (`d=1`), choose a glyph using strict greater-than thresholds:

```text
brightness 0..48    -> space
brightness 49..100  -> ░  U+2591 LIGHT SHADE
brightness 101..152 -> ▒  U+2592 MEDIUM SHADE
brightness 153..204 -> ▓  U+2593 DARK SHADE
brightness 205..255 -> █  U+2588 FULL BLOCK
```

Unless `-nobg` is active, every cell is exactly:

```text
ESC[48;2;MR;MG;MBmESC[38;2;R;G;BmGLYPH
```

`M` is the chosen matte and `(R,G,B)` is the rounded block average. Repeat both
escapes for every cell, including spaces and repeated colors.

## Spec 16

For character dithering (`d=2`), use this strict threshold mapping:

```text
brightness 0..23    -> space
brightness 24..46   -> .
brightness 47..69   -> :
brightness 70..92   -> ;
brightness 93..115  -> +
brightness 116..138 -> =
brightness 139..161 -> x
brightness 162..184 -> X
brightness 185..207 -> $
brightness 208..230 -> &
brightness 231..255 -> #
```

Use the same per-cell ANSI prefix and row reset as block dithering. The glyph data
in this mode is ASCII only; no Unicode block or shade character appears.

## Spec 17

`-nobg` suppresses the complete `ESC[48;2;MR;MG;MBm` prefix from every cell in
dithering modes 1 and 2. It leaves the foreground `ESC[38;2;R;G;Bm`, glyph, reset,
and newlines intact. It neither changes classic output nor makes `-m` invalid.

Matte still participates in alpha compositing before block averaging; `-nobg`
only suppresses the emitted ANSI background escape. For opaque images, changing
matte cannot affect foreground values. For transparent images, it can.

All options can be combined, and their semantic result is independent of option
order as long as every option precedes the positional image.

## Spec 18

With `-go`, perform exactly the same image processing, dimensions, colors, glyphs,
and row omission, but output one independent Go statement per rendered terminal
row. Replace every live `ESC` byte with the four literal characters `\033` and the
row's final live newline with the two literal characters `\n`, then wrap the whole
row as:

```text
fmt.Print("ROW_CONTENT")
```

The statement itself ends with a real LF byte. Use `fmt.Print`, never `fmt.Printf`.
There are no actual ESC bytes inside this output, and there are no actual newlines
inside a quoted Go string. Unicode glyphs such as `▄` and `█` remain literal UTF-8
in the Go string. Each string ends in literal `\033[0m\n`. `-nobg` suppresses
escaped `\033[48;2;...` prefixes under the same rules as live output.

## Spec 19

For ordinary rendering when stdout is a TTY, write `ESC[HESC[2J` immediately
before the rendered image to home the cursor and clear the display. After all
rendered rows (or generated Go statements), write one additional LF. Do not do
either of these things when stdout is not a TTY. Help and errors use the plain logo
regardless of TTY; only credits select the special TTY icon from Spec 5.

## Spec 20

The executable has no configuration-file or environment-variable interface. It
must not read `.pixtermrc`, XDG configuration paths, or similar files. Variables
such as `HOME`, `XDG_CONFIG_HOME`, `NO_COLOR`, and `TERM` must not change help,
validation, colors, defaults, or rendering. Only operating-system facilities that
are intrinsic to the requested operation—stdout TTY status and size, filesystem,
clock for error timestamps, DNS, proxy/TLS/network behavior—may affect results.

Rendering is deterministic for the same decoded image, arguments, stdout mode and
terminal dimensions. It must handle dimensions at least as large as 300 columns by
500 rows without truncation, overflow, or unreasonable delay. Every successful
non-TTY output row is valid UTF-8 and ends with a reset followed by LF.
