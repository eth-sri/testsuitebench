# Clarified executable specification

## Spec 1

The required artifact is a directly runnable file named exactly `executable`. It implements a single-purpose command-line JPEG-to-ASCII converter compatible with `jp2a 1.0.8`. Its invocation is:

```text
./executable [ options ] [ file(s) | URL(s) ]
```

There are no subcommands and no command-routing layer. Every positional token, including words such as `add`, `list`, `help`, or `config`, is an input filename or supported URL. A positional token that cannot be opened therefore produces an input error, never an “unknown command” diagnostic. Options may appear before, after, or between inputs. A lone `-` is a positional input meaning standard input; a filename merely containing a hyphen is an ordinary filename.

## Spec 2

Parse arguments from left to right. Recognize these options and aliases:

```text
-h --help                 -V --version
-v --verbose              -d --debug
-b --border               -i --invert
-x --flipx                -y --flipy
-f --term-fit             -z --term-zoom
--term-width              --term-height
--clear                   --color --colors
--fill                    --grayscale
--html                    --html-raw
--html-fill               --html-no-bold
--width=N                 --height=N
--size=WxH
--chars=PALETTE
--red=R                   --green=G --blue=B
--background=dark         --background=light
--html-fontsize=N         --html-title=TITLE
--output=FILE
```

Parameterized long options use the shown `=` spelling. There is no `-o`. Short flags cannot be bundled: for example, `-b -v` consists of two valid flags, while `-bv` is unknown. A bare `--` is also unknown; it is not an end-of-options marker. Missing or wholly nonnumeric parameterized options such as `--width`, `--height`, `--chars`, `--html-fontsize`, `--width=abc`, `--size=abc`, and `--size=10xabc` are unknown options. The integer parsers accept a leading decimal number followed by otherwise invalid suffix bytes: for example, `--width=10junk` is accepted as width 10, `--height=2junk` as height 2, and `--html-fontsize=9junk` as font size 9. `--term-width` and `--term-height` are flags, not value-taking options, and spellings such as `--term-width=10` are unknown.

`--help` and `--version` act immediately when reached, print their output, and exit successfully without requiring an input. Other repeated settings use the last supplied value, except that `--invert` toggles each time. `--color` and `--colors` are identical. `--html-fill` enables the same behavior as `--fill` and additionally writes exactly `warning: --html-fill has changed to --fill\n` to standard error.

## Spec 3

`-V` and `--version` exit 0, write nothing to standard output, and write exactly the following three newline-terminated lines to standard error:

```text
jp2a 1.0.8
Copyright 2006-2016 Christian Stigen Larsen
Distributed under the GNU General Public License (GPL) v2.
```

`-h` and `--help` also exit 0 and write nothing to standard output. Their entire standard-error output is exactly the following, including spacing and a final newline:

```text
jp2a 1.0.8
Copyright 2006-2016 Christian Stigen Larsen
Distributed under the GNU General Public License (GPL) v2.

Usage: jp2a [ options ] [ file(s) | URL(s) ]

Convert files or URLs from JPEG format to ASCII.

OPTIONS
  -                 Read images from standard input.
      --blue=N.N    Set RGB to grayscale conversion weight, default is 0.1145
  -b, --border      Print a border around the output image.
      --chars=...   Select character palette used to paint the image.
                    Leftmost character corresponds to black pixel, right-
                    most to white.  Minimum two characters must be specified.
      --clear       Clears screen before drawing each output image.
      --colors      Use ANSI colors in output.
  -d, --debug       Print additional debug information.
      --fill        When used with --color and/or --html, color each character's
                    background color.
  -x, --flipx       Flip image in X direction.
  -y, --flipy       Flip image in Y direction.
  -f, --term-fit    Use the largest image dimension that fits in your terminal
                    display with correct aspect ratio.
      --term-height Use terminal display height.
      --term-width  Use terminal display width.
  -z, --term-zoom   Use terminal display dimension for output.
      --grayscale   Convert image to grayscale when using --html or --colors
      --green=N.N   Set RGB to grayscale conversion weight, default is 0.5866
      --height=N    Set output height, calculate width from aspect ratio.
  -h, --help        Print program help.
      --html        Produce strict XHTML 1.0 output.
      --html-fill   Same as --fill (will be phased out)
      --html-fontsize=N   Set fontsize to N pt, default is 4.
      --html-no-bold      Do not use bold characters with HTML output
      --html-raw    Output raw HTML codes, i.e. without the <head> section etc.
      --html-title=...  Set HTML output title
  -i, --invert      Invert output image.  Use if your display has a dark
                    background.
      --background=dark   These are just mnemonics whether to use --invert
      --background=light  or not.  If your console has light characters on
                    a dark background, use --background=dark.
      --output=...  Write output to file.
      --red=N.N     Set RGB to grayscale conversion weight, default 0.2989f.
      --size=WxH    Set output width and height.
  -v, --verbose     Verbose output.
  -V, --version     Print program version.
      --width=N     Set output width, calculate height from ratio.

  The default mode is `jp2a --term-fit --background=dark'.
  See the man-page for jp2a for more detailed help text.

Project homepage on https://github.com/cslarsen/jp2a
Report bugs to <csl@csl.name>
```

The help is a flat option list and must not contain headings or guidance for commands or subcommands.

## Spec 4

With no positional inputs, exit 1. Standard output is empty and standard error begins `No files specified.\n\n`, followed immediately by the exact help text from Spec 3. The same applies when only ordinary non-terminating options are supplied.

For any unrecognized option token `S`, exit 1 and write `Unknown option S\n\n` followed by that exact help text to standard error; standard output is empty. Normal success exits 0. All handled errors exit 1 unless a more specific behavior below says otherwise.

## Spec 5

Inputs are processed once each, from left to right, and their complete renderings are concatenated with no separator beyond each rendering's own final newline or markup. Restore the originally requested sizing mode before each input so differently sized JPEGs are independently aspect-fitted. Options themselves are skipped during this processing pass.

Open ordinary inputs as binary files. If an input cannot be opened, write exactly `Can't open PATH\n` to standard error, stop immediately, retain any output already produced for earlier inputs, and exit 1. Unicode and hyphenated paths must work. A lone `-` reads a JPEG byte stream from standard input. File input and one stdin input can be mixed in positional order. Empty stdin is an error rather than an implicit request to wait for another input.

By default output goes to standard output. `--output=-` explicitly selects standard output and must not create a file named `-`. Any other `--output=PATH` opens that path once in binary write/truncate mode before processing inputs, sends all image renderings to it, and leaves standard output empty. It overwrites an existing file and keeps the stream open across multiple inputs. An empty path exits 1 with `Empty output filename.\n`. Failure to create the path exits 1 with exactly `Could not open 'PATH' for writing.\n`; parent directories are not created.

## Spec 6

Support 8-bit baseline or progressive JPEG data as decoded by a conventional IJG/libjpeg-compatible decoder, including one-component grayscale JPEGs and three-component RGB JPEGs. Reject empty data with exactly `Empty input file\n`. If the first two bytes are not a JPEG signature, use the lowercase two-digit byte values in exactly `Not a JPEG file: starts with 0xNN 0xNN\n`; for example, PNG data beginning `89 50` reports `Not a JPEG file: starts with 0x89 0x50`, and `not...` reports `0x6e 0x6f`. A stream containing only `ff d8 ff e0` reports these two lines and exits 1:

```text
Premature end of JPEG file
JPEG datastream contains no image
```

Other malformed JPEG diagnostics may follow standard libjpeg wording, but malformed data must not hang. Reject non-8-bit JPEG sample precision using libjpeg's diagnostic. In particular, a JPEG whose start-of-frame precision byte is 12 exits 1, leaves standard output empty, and writes exactly `Unsupported JPEG data precision 12\n` to standard error.

## Spec 7

The content dimensions are controlled as follows. `--size=WxH` (for example, `--size=30x10`) makes both dimensions exact and disables aspect-ratio calculation. `--width=W` alone fixes content width and derives height. `--height=H` alone fixes content height and derives width. Supplying both width and height makes both exact. Options are order-sensitive: a later `--size` replaces earlier width/height settings; a later width after a size fixes that new width and resumes automatic height calculation; a later height analogously resumes automatic width calculation; repeated size settings use the last size.

For source dimensions `JW` by `JH`, derive a missing dimension using single-precision arithmetic and `round_half_up(q) = int(q + 0.5)`:

```text
derived_height = round_half_up(0.5 * width  * JH / JW)
derived_width  = round_half_up(2.0 * height * JW / JH)
```

The factors compensate for terminal characters being about twice as tall as wide. If a derived height is zero, increment width and recalculate until height is nonzero. If a derived width is zero, increment height and recalculate until width is nonzero. Thus tiny requests still render at least one cell, although an automatically adjusted companion dimension may become larger than the originally supplied value.

Negative standalone dimensions, negative `--size` components, and `--size` with one zero component and one positive component fail before rendering with exactly `Invalid width or height specified\n`. Standalone `--width=0`, standalone `--height=0`, and `--size=0x0` instead enter terminal-dependent sizing before that validation; with `TERM` absent, each exits 1 with empty standard output and exactly `Environment variable TERM not set.\n` on standard error. Widths/heights of 1, extreme shapes such as `200x1` and `2x100`, dimensions such as `300x200`, and `2000x2000` must render. A plain `W` by `H` result contains exactly `H` rows of `W` characters, each terminated by `\n`; two `2000x2000` plain images therefore produce exactly 8,004,000 bytes.

## Spec 8

When no explicit width or height is provided, the default sizing mode is `--term-fit`. An explicit nonzero `--width` or `--height` disables this default terminal fit, even if `--term-fit` also appears, so nonzero explicit sizing does not require `TERM`. The all-zero cases described in Spec 7 are exceptions.

Terminal modes obtain columns `TW` and lines `TH` from the termcap entry named by environment variable `TERM`, honoring `COLUMNS` and `LINES` overrides where the terminal library does. If `TERM` is absent, exit 1 with `Environment variable TERM not set.\n`. If it is empty or unrecognized, exit 1 with `Terminal type 'VALUE' not recognized.\n`. A termcap database access failure reports `Could not access the termcap database.\n`. Produce no standard output on these failures.

Let `B` be 1 with a border and 0 otherwise. `--term-width` sets content width to `TW - 2B` and derives height. `--term-height` sets content height to `TH - 1 - 2B` and derives width. `--term-zoom`/`-z` sets exact content size `(TW - 2B)` by `(TH - 1 - 2B)`, deliberately stretching the image. `--term-fit`/`-f` initially chooses width fitting when `TW <= TH`, otherwise height fitting. It preserves aspect ratio. If a height-based calculation becomes wider than `TW - 2B`, switch to width fitting and recalculate. Borders included, output never exceeds the selected terminal extent.

## Spec 9

Rendering must reproduce the reference's sampling, rather than use an interpolating image resize. Use IEEE-754 single-precision values for its calculations and the `round_half_up` operation from Spec 7.

After the final content size `W` by `H` is known, define:

```text
resize_x = (JW - 1) / W
resize_y = (H - 1) / (JH - 1)
lookup[x] = round_half_up(x * resize_x), for x = 0..W
```

For each decoded source scanline `sy`, calculate `dy = round_half_up(resize_y * sy)`. `last_y` is process-static: it starts at 0 for the first scanline of the first image, but is not reset between input images. Add the scanline to every destination row while `last_y <= dy`, incrementing that destination row's contribution count; after the loop set `last_y = dy`, including when the loop did not execute. For each destination column `x`, average all source pixels from `lookup[x]` through `lookup[x+1]` inclusive, so adjacent horizontal bins deliberately overlap at the boundary. Add that horizontal average to the destination cell. When all source scanlines have been processed, divide each destination row's accumulated cells by its contribution count when that count is greater than one. Clear the cell accumulators and contribution counts for each input image, but retain `last_y`. Consequently, with the 4-by-3 grayscale sample rows `[0,32,96,255]`, `[16,64,128,240]`, and `[8,80,160,224]`, quality-100 JPEG encoding, `--size=4x3`, and `--chars=0123456789ABCDEF`, rendering the file once produces `257B\n268B\n379B\n`, while rendering it twice in one invocation produces `257B\n268B\n379B\n268B\n268B\n379B\n`.

There is a separate degenerate path when a one-image invocation uses a JPEG with source height `JH = 1`. The division in `resize_y` is non-finite and, in this reference build, the sole source scanline is not added to any destination row. The cleared cells therefore remain exactly `Y = R = G = B = 0`, even when the requested output height is greater than one. All subsequent palette, RGB-weight, ANSI, fill, grayscale, and HTML rules consume those zero values; they do not recover the JPEG's original sample. Thus ordinary ANSI classification selects white through the final `0 >= 3*0` rule, forced grayscale below its threshold emits no ANSI sequence, and HTML color values are black.

For a grayscale source, a source sample `g` contributes `g/255`. For RGB, a pixel contributes the weighted luminance described in Spec 10. When color information is enabled, accumulate and normalize red, green, and blue independently as `component/255` using the identical bins and row contribution counts.

## Spec 10

The default palette is exactly the 23-byte string shown here (three leading spaces):

```text
   ...',;:clodxkO0KXNWM
```

Let `C = palette_length - 1` and let normalized sampled luminance be `Y`. In ordinary dark-background state, select `palette[round_half_up(C * Y)]`. In light-background state, select `palette[C - round_half_up(C * Y)]`. Do not interpolate between characters. Every row ends in `\n`.

`--chars=PALETTE` replaces the palette byte-for-byte; spaces, punctuation, and repeated bytes are significant. At least two characters are required, and a 256-byte palette is accepted. A one-character or empty palette exits 1 with exactly `You must specify at least two characters in --chars.\n`. A 257-byte palette overflows the reference's fixed buffer: conversion terminates by `SIGABRT` before rendering, standard output is empty, and standard error is exactly `*** buffer overflow detected ***: terminated\n`. Palettes such as `aa` produce only `a` cells; all-space palettes preserve the exact row widths. For mathematically valid but extreme RGB weights, do not clamp `Y` before palette selection; an out-of-range palette result is treated as a NUL-equivalent cell, and plain C-string-style row output ends at the first such cell. This preserves the intentionally sparse output of extreme weight combinations.

## Spec 11

The internal dark-background/invert state starts enabled. `--background=dark` sets it enabled; `--background=light` sets it disabled. Each `-i` or `--invert` toggles it, so two inversions cancel and option order matters. Despite the option's name, this state reverses only which end of the palette represents a given luminance; it does not invert sampled RGB colors.

`-x`/`--flipx` mirrors content cells left-to-right. `-y`/`--flipy` reverses the destination row order. Both together rotate the content 180 degrees and preserve all content dimensions. In color and HTML modes, a character and its sampled color values move together. Apply flips to content, not to a surrounding border.

## Spec 12

`-b`/`--border` frames each rendered image. For content width `W`, emit `+` followed by `W` hyphens and `+\n`, then each content row as `|` + its `W` cells + `|` plus that mode's row ending, then the identical bottom border. Border symbols are literal and are never palette-mapped, inverted, or ANSI-colored. Explicit dimensions describe content; a border adds two columns and two rows. Terminal modes subtract this space as specified in Spec 8.

`--clear` prefixes every image rendering, before its HTML wrapper or top border, with exactly `ESC [ 2 J ESC [ 0 ; 0 H`, i.e. bytes `\x1b[2J\x1b[0;0H`. With multiple images the sequence occurs before each image.

## Spec 13

`--color` or `--colors` enables per-cell ANSI output. Character selection is unchanged from Spec 10. For every output cell use its normalized `R`, `G`, `B`, and weighted `Y`. Let `t=0.1`, `i=0.9`, and test rules in this exact order:

```text
31 red:     R-t > G and R-t > B
32 green:   G-t > R and G-t > B
33 yellow:  R-t > B and G-t > B and R+G > i
34 blue:    B-t > R and B-t > G and Y < 0.95
35 magenta: R-t > G and B-t > G and R+B > i
36 cyan:    G-t > R and B-t > R and B+G > i
37 white:   R+G+B >= 3*Y
```

Use the first matching ANSI color, or no color if none matches. Independently, set highlight when `Y >= 0.95` and each of `R,G,B` is less than `1/255`. An uncolored, unhighlighted cell is just its character. An uncolored highlighted cell is `ESC[1m` + character + `ESC[0m`. A colored cell is `ESC[Nm` + character + `ESC[0m`. With `--fill`, add 10 to `N`, selecting ANSI background codes 41–47. Each cell resets independently; borders remain uncolored.

For an inherently grayscale JPEG, the stored RGB values are zero while `Y` retains grayscale intensity, and the ordinary ordered rules above still run. A black cell with `Y = 0` therefore satisfies the final white test (`0 >= 3*0`) and is emitted with ANSI code 37 (or 47 with fill). For `0 < Y < 0.95`, none of the color rules matches and the cell is unstyled. At `Y >= 0.95`, the cell is emitted with the bold highlight sequence.

## Spec 14

`--grayscale` itself enables color-capable output and forces grayscale color presentation; it does not change the weighted `Y` used to select the character. In ANSI mode, forced grayscale uses ANSI white (`37`, or `47` with fill) with highlight for cells where `Y >= 0.7`; cells below that threshold are emitted without an ANSI color unless the inherent-grayscale highlight rule from Spec 13 applies. `--colors --grayscale` behaves the same as `--grayscale`. Inversion changes the selected characters but not the RGB/grayscale style values.

## Spec 15

`--html` wraps each image in this exact XHTML skeleton. The actual runtime title, background, optional color line, font size, weight, and rendered content replace the marked descriptions; all literal whitespace shown is significant:

```text
<?xml version='1.0' encoding='ISO-8859-1'?>
<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.0 Strict//EN'  'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'>
<html xmlns='http://www.w3.org/1999/xhtml' lang='en' xml:lang='en'>
<head>
<title>TITLE</title>
<style type='text/css'>
body {
BACKGROUND-LINE
}
.ascii {
   font-family: Courier;
OPTIONAL-COLOR-LINE
   font-size:Npt;
   font-weight: WEIGHT;
}
</style>
</head>
<body>
<div class='ascii'><pre>
CONTENT</pre>
</div>
</body>
</html>
```

The default title is `jp2a converted image`, default runtime font size is 8 (even though the historical help line says 4), and default weight is `bold`. `--html-no-bold` changes it to `normal`. Any signed integer font size, including -5, 0, 1, and 72, is accepted literally. In dark-background state, `BACKGROUND-LINE` is exactly `background-color: black;` with no leading spaces and, when color output is disabled, `OPTIONAL-COLOR-LINE` is `   color: white;`. In light-background state these become `   background-color: white;` and `   color: black;`. When color output is enabled, omit the CSS foreground-color line entirely.

`--html-title=TITLE` inserts the argument bytes literally between the title tags: empty, long, Unicode, quotes, `&`, `<`, and `>` are not escaped or truncated.

## Spec 16

HTML without color output places the same plain ASCII rows (and optional plain border) inside `<pre>`, using ordinary newline bytes. With HTML color enabled, wrap every content character separately. With no fill use exactly:

```text
<span style='color:#rrggbb;'>ENTITY</span>
```

With fill use exactly:

```text
<span style='color:#rrggbb; background-color:#rrggbb;'>ENTITY</span>
```

Hex is lowercase and always six digits. Encode a cell space as `&nbsp;`, `<` as `&lt;`, `>` as `&gt;`, and `&` as `&amp;`; other single-byte palette characters are literal. End each colored HTML row with `<br/>` and no newline. With a border, the literal side bars surround that row's spans before `<br/>`; the plain top and bottom border lines use newline bytes.

For normal color without fill, foreground is `round_half_up(255*R/G/B)`. With fill, background is `round_half_up(255*R/G/B)` and foreground is `round_half_up(255*Y*R/G/B)`. For forced grayscale, or for an inherent grayscale sample identified by `R,G,B < 1/255` and `Y > 1/255`, no-fill foreground is `(round_half_up(255Y),)*3`; fill background is that value and fill foreground is `(round_half_up(127.5Y),)*3`.

`--html-raw` enables HTML mode but suppresses the entire document wrapper. Without color it therefore emits plain ASCII rows with `\n` and no tags. With color it emits only the per-cell spans and `<br/>` row endings. It never emits a doctype, `<html>`, `<head>`, or `<body>` wrapper.

## Spec 17

For RGB JPEGs compute luminance using single-precision lookup contributions:

```text
Y = Rbyte * red_weight/255 + Gbyte * green_weight/255 + Bbyte * blue_weight/255
```

Defaults are red `0.2989`, green `0.5866`, and blue `0.1145`. `--red=`, `--green=`, and `--blue=` parse floating-point values and the last occurrence of each wins. Do not independently restrict signs or magnitudes: combinations such as `-0.5,1.0,0.5` and `100,-50,-49` are valid because they sum to one. Channel-isolation triples such as `1,0,0`, `0,1,0`, and `0,0,1` must use only that channel.

After parsing, use the reference single-precision check `int((red+green+blue) * 10000000.0f) == 10000000`. Otherwise exit 1 with exactly `Weights RED + GREEN + BLUE must equal 1.0\n`. Consequently `0.3333333 + 0.3333333 + 0.3333334` is accepted while the same triple ending in `0.3333335` is rejected. A wholly nonnumeric weight spelling is an unknown option under Spec 4. As with integer parameters, each weight accepts a leading numeric value and ignores a trailing nonnumeric suffix. Thus `--red=1junk`, `--green=1junk`, or `--blue=1junk` parses that channel as 1; with the other two channels at their defaults, the invocation reaches the sum check and exits 1 with the preceding weight diagnostic rather than an unknown-option diagnostic.

## Spec 18

`-v`/`--verbose` begins verbose reporting on standard error but does not complete conversion in this stack-protected reference build. Before a local file, write `File: PATH\n`; before a URL, write `URL: URL\n`. After decoding the header and calculating dimensions, write:

```text
Source width: JW
Source height: JH
Source color components: COMPONENTS
Output width: W
Output height: H
Output palette (L chars): 'PALETTE'
```

During decompression, write progress records as `Decompressing image [BAR]\r`. Before the fatal final update, a source of height `JH` emits `JH-1` such records, corresponding to `k = 2..JH`; each `BAR` is a 54-character field containing `round_half_up(54*k/JH)` leading `#` bytes and trailing dots. The subsequent final update attempts to construct 55 `#` bytes in the fixed progress buffer, triggers its stack protector, and terminates the process with `SIGABRT`. It appends exactly `*** buffer overflow detected ***: terminated\n` immediately after the last carriage return, writes no final progress newline, and produces no rendered bytes on standard output. This failure occurs for local files, HTTP URLs, and `file://` URLs; the appropriate input label and metadata above are emitted first.

`-d`/`--debug` requests transfer diagnostics only for URL downloads. Used alone on a local file, it leaves the rendered output unchanged and standard error empty. Adding it to local verbose mode adds no diagnostic bytes: the input label, metadata, progress, and `SIGABRT` result are identical to verbose mode alone. For an HTTP URL with both debug and verbose enabled, write the `URL:` label first, then the transfer diagnostics, then the decoded-image metadata and progress; the same final overflow terminates the process with empty standard output.

## Spec 19

Recognize URL inputs only for case-sensitive prefixes `ftp://`, `ftps://`, `file://`, `http://`, `https://`, and `tftp://`. Download them as binary streams, follow redirects, and fail HTTP error responses. `file://` must render identically to opening the same JPEG directly. A failed transfer that yields no bytes ultimately exits 1 with `Empty input file\n`. Debug mode may expose the transfer library's diagnostics on standard error. Do not treat other colon-containing positional arguments as subcommands.

## Spec 20

Very large dimensions do not have a uniform safe-allocation failure. In particular, with an 8-by-2 JPEG, `--width=1000000` terminates by `SIGSEGV` during conversion and leaves both standard output and standard error empty; it does not print an allocation diagnostic. A render from `--height=1000000` must exit nonzero; if it exits normally rather than being killed, its diagnostic must contain `Not enough memory`. These large-dimension failure modes do not reject the expressly supported `2000x2000` case.

All combinations are compositional: sizing and sampling occur first; RGB weights determine luminance; inversion selects the palette direction; flips select cell order; color styling travels with each cell; borders surround the transformed content; clear-screen bytes precede everything; HTML or ANSI formatting is then emitted to the chosen output stream. Except for documented verbose/debug/warning/error messages, successful conversion writes nothing to standard error.
