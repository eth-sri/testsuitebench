# ASCII-diagram converter executable specification

The required artifact is a single file named `executable`. The requirements below are normative. “Exact” means byte-for-byte exact, including whitespace and newlines. The rendering model is intentionally fixed because consumers compare deterministic PNG and SVG output, not merely visual similarity.

## Spec 1

`executable` shall implement the ditaa 0.11 compatibility profile described by this document: it converts monospaced text diagrams to PNG by default, to SVG when requested, and can replace diagrams embedded in HTML. It must be directly runnable as a Unix process and return conventional process exit statuses. The same file must also be a Java class-path archive: the harness may run `java -cp executable FULLY.QUALIFIED.CLASS`. Thus it must contain the Java entry points named in Spec 24 and Spec 25 as well as the normal converter entry point. No companion artifact may be required.

For a successful ordinary conversion, the destination must be nonempty and deterministic. Except for the debug-grid stdout prefix specified in Spec 5, PNG output must begin with `89 50 4e 47 0d 0a 1a 0a`, contain a valid IHDR with positive dimensions, and end in the normal PNG IEND chunk, and SVG output must be well-formed UTF-8 XML. After that prefix, the debug stdout stream contains a valid PNG or SVG payload. Ordinary, large, wide, tall, sparse, nested, overlapping, and densely connected diagrams must finish within 30 seconds; auxiliary Java entry points must finish within their stated limits.

## Spec 2

The command form is:

`executable [OPTIONS] INPFILE [OUTFILE]`

Options may occur before or after positional arguments and are processed in command-line order. Supported options and exact long names are:

- `-A`, `--no-antialias`
- `-b VALUE`, `--background VALUE`
- `-d`, `--debug`
- `-E`, `--no-separation`
- `-e VALUE`, `--encoding VALUE`
- `-h`, `--html`
- `--help`
- `-o`, `--overwrite`
- `-r`, `--round-corners`
- `-S`, `--no-shadows`
- `-s VALUE`, `--scale VALUE`
- `--svg`
- `--svg-font-url VALUE`
- `-T`, `--transparent`
- `-t VALUE`, `--tabs VALUE`
- `-v`, `--verbose`
- `-W`, `--fixed-slope`

PNG is the default regardless of the spelling of an explicitly supplied destination extension; for example, an output named `output.jpg` still contains PNG bytes. `--svg` alone selects SVG and is distinct from `-S`, which means no shadows. Options are independent and order-independent in their rendering effects, except that `--transparent` always overrides the background color.

## Spec 3

With no arguments, or with `--help`, exit 0 and write the following exact text to standard output and nothing to standard error:

```text
usage: java -jar ditaa.jar <INPFILE> [OUTFILE] [-A] [-b <BACKGROUND>] [-d]
       [-E] [-e <ENCODING>] [-h] [--help] [-o] [-r] [-S] [-s <SCALE>]
       [--svg] [--svg-font-url <FONT>] [-T] [-t <TABS>] [-v] [-W]
 -A,--no-antialias              Turns anti-aliasing off.
 -b,--background <BACKGROUND>   The background colour of the image. The
                                format should be a six-digit hexadecimal
                                number (as in HTML, FF0000 for red). Pass
                                an eight-digit hex to define transparency.
                                This is overridden by --transparent.
 -d,--debug                     Renders the debug grid over the resulting
                                image.
 -E,--no-separation             Prevents the separation of common edges of
                                shapes.
 -e,--encoding <ENCODING>       The encoding of the input file.
 -h,--html                      In this case the input is an HTML file.
                                The contents of the <pre
                                class="textdiagram"> tags are rendered as
                                diagrams and saved in the images directory
                                and a new HTML file is produced with the
                                appropriate <img> tags.
    --help                      Prints usage help.
 -o,--overwrite                 If the filename of the destination image
                                already exists, an alternative name is
                                chosen. If the overwrite option is
                                selected, the image file is instead
                                overwriten.
 -r,--round-corners             Causes all corners to be rendered as round
                                corners.
 -S,--no-shadows                Turns off the drop-shadow effect.
 -s,--scale <SCALE>             A natural number that determines the size
                                of the rendered image. The units are
                                fractions of the default size (2.5 renders
                                1.5 times bigger than the default).
    --svg                       Write an SVG image as destination file.
    --svg-font-url <FONT>       SVG font URL.
 -T,--transparent               Causes the diagram to be rendered on a
                                transparent background. Overrides
                                --background.
 -t,--tabs <TABS>               Tabs are normally interpreted as 8 spaces
                                but it is possible to change that using
                                this option. It is not advisable to use
                                tabs in your diagrams.
 -v,--verbose                   Makes ditaa more verbose.
 -W,--fixed-slope               Makes sides of parallelograms and
                                trapezoids fixed slope instead of fixed
                                width.
```

An unknown option is a command-line parse error: exit 2, put a message containing `Unrecognized option` on standard error, and put the usage text on standard output. A missing required option value behaves likewise.

## Spec 4

`-s/--scale` accepts Java-style floating-point text, including fractional values such as `0.5`, `0.8`, `1.5`, `2.0`, `2.5`, `3.5`, `5`, and `10`. Non-numeric input exits 2, writes `Error: For input string: "VALUE"` to standard error, and emits usage on standard output. Very small or nonpositive numeric scales are not validated early: their later Java-compatible failure is observable. At scale `0.1`, a text-bearing input such as `hello` fails during text measurement: it exits 1 with a Java `NullPointerException` stack trace containing `FontMeasurer.getWidthFor` and creates no destination. Scale zero or negative values likewise may fail first in text measurement with `NullPointerException` and `FontMeasurer.getWidthFor`, or, for text-free input, during image creation with a message matching `Width (N) and height (N) cannot be <= 0`. These cases exit 1/nonzero.

`-t/--tabs` accepts an integer without an artificial upper bound; 2, 4, 8, 16, and 100 are valid. Non-numeric input exits 2 with `Error: For input string: "VALUE"` and usage. A negative integer is normalized to zero and succeeds when the input contains no tab.

`-b/--background` accepts exactly six hexadecimal digits as RGB or eight as RRGGBBAA. Letter case is accepted and the original option value is retained in diagnostics. A length other than 6 or 8 exits 2 and writes exactly this error before displaying usage:

`Error: Cannot interpret "VALUE" as background colour. It needs to be a 6- or 8-digit hex number, depending on whether you have transparency or not (same as HTML).`

A six/eight-character value containing a non-hex digit exits 2 with `Error: For input string: "VALUE"` in standard error and usage in standard output. `-e/--encoding` must name a Java-supported character encoding. Unsupported names exit 2 with `Error: ` followed by the encoding name and a newline in standard error; standard output is empty, so this validation failure does not emit usage. For example, `--encoding not-an-encoding` exits 2 with exactly `Error: not-an-encoding\n` on standard error and no standard output.

## Spec 5

Input is read from `INPFILE`, or from standard input when `INPFILE` is `-`. File bytes are initially decoded with the platform default character set even when `--encoding` is supplied. When an encoding is supplied, each already-decoded row is then converted to platform-default bytes and decoded again using the named encoding. On the reference UTF-8 platform, explicit `--encoding UTF-8` therefore preserves UTF-8 text such as `café 漢字 😀`, but `--encoding ISO-8859-1` does not correctly decode an ISO-8859-1 input: the ISO-8859-1 bytes for `café déjà vu` render as `cafï¿½ dï¿½jï¿½ vu`. CRLF and LF are line separators. Unicode text, emoji, accented text, CJK, and Unicode box-drawing glyphs must not crash the converter. Successfully decoded Unicode, including supplementary characters such as 😀, remains literal text. Only the ASCII diagram alphabet has structural meaning, so Unicode box-drawing glyphs are rendered as text rather than silently converted to ASCII boundaries.

A nonexistent ordinary input exits 1 and writes `Error: File PATH does not exist` to standard error. An existing directory supplied as the ordinary input path is reported identically: it exits 1 and writes `Error: File PATH does not exist`. This is unchanged in SVG mode. Other read failures exit 1 with `Error: Cannot open file PATH for reading`. A destination that cannot be opened exits 1 with `Error: Cannot write to file PATH`. For example, `/dev/null/output.png` is reported as the requested rendering path before the write error.

When the output is `-`, suppress the banner, options, input notice, destination notice, timing, and other ordinary progress text. Without `--debug`, `- -` therefore maps stdin directly to a byte-exact PNG; adding `--svg` maps it to byte-exact SVG text. Debug grid output is the exception: with `--debug`, the normalized-grid header and rows are written first to standard output, immediately followed by the PNG bytes or SVG XML. No `Using grid:` label precedes this stdout grid. Thus `hello` rendered by `- - -S --debug` begins exactly `    0123456789\n 0 (         )\n 1 (         )\n 2 (  hello  )\n 3 (         )\n 4 (         )\n`, and only then has the PNG signature.

## Spec 6

If `OUTFILE` is omitted for a real input file, construct it beside that input by removing only the final filename extension and appending `.png`, or `.svg` under `--svg`. Preserve earlier dots, Unicode, spaces, hyphens, underscores, case, long names, and all parent directories. An extensionless input simply gains the extension. PNG and SVG collision namespaces are separate.

Without `--overwrite`, if this automatically selected path exists, choose the first nonexistent `BASE_2.EXT`, `BASE_3.EXT`, and so on through `BASE_100.EXT`. Never overwrite an automatically selected existing file. If every candidate is occupied, retain the compatibility failure: report `Rendering to file: null`, then fail nonzero with a Java `NullPointerException` stack trace mentioning `FileOutputStream.<init>`. An explicitly supplied output path is written directly by normal image mode; alternative numbering applies to automatic names. With `--overwrite`, reuse and replace the base path, change its modification time, and do not create a numbered alternative.

## Spec 7

For a non-stdout ordinary conversion, standard output has this form, including the leading blank line:

```text

ditaa version 0.11, Copyright (C) 2004--2017  Efstathios (Stathis) Sideris

Running with options:
OPTION-LINES
Reading file: INPUT
Rendering to file: OUTPUT
Done in Nsec
```

For stdin, the read line is `Reading standard input`. `N` is elapsed whole seconds. Each specified option is printed on its own line in command-line order, using its long name without leading dashes. Boolean examples are `svg`, `transparent`, `debug`, `verbose`, `overwrite`, `round-corners`, `no-shadows`, `no-antialias`, `no-separation`, and `fixed-slope`; valued examples are `scale = 2.0`, `tabs = 4`, `encoding = UTF-8`, `background = FF0000`, and `svg-font-url = URL`. The banner and `Running with options:` appear even when there are no option lines. `--verbose` does not alter image pixels; its required visible effect is the `verbose` option line.

With `--debug` and a file destination, after the read line print `Using grid:` and the normalized grid. Its header is four spaces followed by `0123456789` repeated `floor(gridWidth/10)+1` times (it is not truncated to grid width). Each row is `II (ROW)`, with a leading space before single-digit row numbers. For a `-` destination, print only that header and those rows before the image/XML as specified in Spec 5, without the read line or `Using grid:` label. Debug mode also overlays a raster grid as specified later.

## Spec 8

Normalize input into a rectangular character grid as follows. Split on LF or CRLF. Remove whitespace-only rows from the bottom but preserve one row for a zero-byte input and for whitespace content represented by an actual row. Expand each tab to the next multiple of the configured tab width; the default is 8. Pad shorter rows on the right to the maximum expanded width. Add exactly two blank columns at the left and right and two blank rows at the top and bottom. This padded grid is what debug output displays and what establishes the canvas. Zero-byte input therefore produces the same deterministic 40-by-70 blank PNG on every run; a space- or tab-only row retains its source width.

There is a compatibility failure before normalization for a nonempty input made solely of one or more LF or CRLF line separators. Such input exits 1, writes no standard output, and writes a Java `IndexOutOfBoundsException: toIndex = 1` stack trace to standard error containing `TextGrid.initialiseWithLines`. It does not produce the zero-byte input's minimal image.

Before recognizing shapes, replace the human color mnemonics described in Spec 15, and replace a bullet marker matching Spec 14. For boundary analysis only, replace a letter or digit lying between two horizontal line cells with `-`, between two vertical line cells with `|`, and at both with `+`. Apply the analogous replacement to point markers that occur on lines. For text analysis, remove recognized arrowheads first, then color codes, boundaries, and recognized markup tags.

## Spec 9

The unscaled logical cell is 10 pixels wide by 14 pixels high. Applying scale `s` uses Java compound-assignment truncation independently: `cellWidth = (int)(10*s)` and `cellHeight = (int)(14*s)`. Canvas width is padded-grid width times cellWidth; canvas height is padded-grid height times cellHeight. All PNG and SVG geometry uses these scaled cell dimensions, so scale 2 exactly doubles both canvas dimensions, scale 0.5 halves them, and scale 10 multiplies them by ten.

A cell center is `(x*cellWidth + cellWidth/2, y*cellHeight + cellHeight/2)` with integer division. Cell-edge points use the corresponding multiples of cellWidth/cellHeight. Thus the three-line input `+----+`, `|    |`, `+----+` has a padded 10-by-7 grid, a 100-by-98 canvas, and its rectangular path corners at `(25,35)`, `(25,63)`, `(75,63)`, `(75,35)` at scale 1.

## Spec 10

Recognize the structural ASCII alphabet contextually with 3-by-3 neighborhood matching:

- horizontal lines are `-` and `=`;
- vertical lines are `|` and `:`;
- corner candidates are `+`, `/`, and backslash;
- arrowheads are `<`, `>`, `^`, `v`, and `V` in a compatible connected-line context, except that an isolated `>` is also recognized as an east arrowhead rather than text;
- `*` is a boundary/intersection candidate and, when embedded in a line, a point marker;
- `~` is a dashed-line indicator but is not by itself an undisputed boundary.

Classification must distinguish sharp and round corners in all four orientations, diagonals, lone diagonals, line starts/ends, horizontal and vertical stubs, T/K/inverse-T/inverse-K junctions, crosses, stars on horizontal/vertical lines, and all eight diagonal/cardinal entry configurations. Out-of-bounds neighbors behave as NUL/non-boundary cells. A plus or slash is structural only when its neighborhood matches a valid connection; otherwise it remains text or a degenerate mark. This context sensitivity is required for dense plus grids, short single segments, incomplete lines, adjacent boxes, nested boxes, mixed diagonals, and text laid over lines.

## Spec 11

Build topology rather than rendering each glyph independently. First project all structural cells to a 3x abstraction grid, split cardinally connected components, flood-fill every region to discover candidate boundaries, scale them back to source cells, remove duplicates, and remove a large closed boundary when its filled area is exactly the union of overlapping smaller closed boundaries. Classify each cell set as open, closed, or mixed.

When closed boundaries coexist with mixed boundaries, subtract closed sets from mixed sets and split the remainder into distinct open paths. When no independent closed boundary exists, trace truly mixed sets from their line ends and split at intersections. Trace long boundaries without recursion limits, including spirals, zigzags, five-way junctions, merge/split networks, dead ends, and multiple disconnected sets. Closed sets become filled polygonal shapes. Open sets become one or more unfilled line paths. One-cell horizontal/vertical sets become short lines unless their source glyph is a dashed marker. Line ends are projected to their cell edge unless locked to an adjacent corner, junction, or arrowhead anchor.

## Spec 12

`+` produces a sharp point. Contextually connected `/` and backslash produce a rounded point: enter at the relevant cell edge, use the cell center as the quadratic control point, and exit at the next relevant cell edge. `--round-corners` treats every corner as round. Closed rounded rectangles, mixed sharp/rounded boundaries, sloped corners, open rounded paths, and round corners attached to arrows must remain connected.

If any horizontal part of a connected shape contains `=`, or any vertical part contains `:`, dashed style spreads through that entire connected shape. Dashed strokes use width `min(cellWidth,cellHeight)/10`, butt caps, round joins, miter limit 0, and equal on/off intervals of `min(cellWidth,cellHeight)/2`. Solid strokes use the same width with round caps and joins. Closed dashed shapes are not filled. `--fixed-slope` affects only IO, trapezoid, and manual-operation geometry as described in Spec 15.

## Spec 13

Render recognized arrowheads as filled black triangles occupying their cell: north has its tip at the top midpoint and base on the bottom edge; south (`v` or `V` only when a vertical line is immediately north) is the inverse; west/east use the analogous horizontal geometry. Connecting paths terminate at the arrowhead center so connected arrowheads remain joined in all four directions and when attached to boxes or dashed paths. The isolated `>` compatibility case from Spec 10 is removed from text and becomes a closed black east-pointing triangle; at scale 1 its SVG path is exactly `M20.0 28.0 L30.0 35.0 L20.0 42.0 z`.

A `*` participating in a horizontal line, vertical line, or crossing is removed from the line topology and redrawn last as a white filled, black outlined circular point marker centered in the cell, diameter `0.7*min(cellWidth,cellHeight)`. This includes a star at an unconnected line end: `*--` produces the open horizontal path and the circular marker centered on the initial star, and produces no literal-star text. Correctly distinguish these stars from ordinary crosses and literal/bullet stars.

## Spec 14

After structural markup is removed, collect remaining adjacent nonblank text into line strings, retaining single spaces that are between characters. As a padding compatibility case, a one-cell input containing only `~` remains literal text but its collected string includes one trailing space; SVG serializes it exactly as `<![CDATA[~ ]]>` and emits no dashed path. Multiple rows whose strings begin/end in the same columns form alignment groups: isolated strings are centered in their own cell span; strings sharing only an end align right; equal shared start/end counts center; otherwise align according to the larger shared count. Vertically center text within its source cell row. Long strings that do not fit are assigned the largest bold logical `Dialog` font that fits their span. The normal font is the largest half-point-sized bold logical `Dialog` font whose ascent does not exceed the scaled cell height. Raster text uses Java2D font metrics and drawing; SVG reports the same integer font size but uses family `Courier` unless a custom SVG font URL is supplied.

The sequence ` o TEXT` or ` * TEXT` is a bullet only when the marker has a blank immediately west and east and an alphanumeric character two cells east. Replace the marker and following blank with a space and U+2022 bullet respectively. Ordinary `o`, `*`, punctuation, numbers, multiline labels, special XML characters, and Unicode remain text. Text inside a shape is black unless the assigned fill is dark, defined as `max(red,green,blue) < 200`, in which case it is white.

## Spec 15

A color code is `cRGB`, where each of R/G/B is one uppercase hexadecimal nibble; expand each nibble by multiplying it by 17. Before this recognition, replace these exact mnemonics: `cGRE` to `c9D9`, `cBLU` to `c55B`, `cPNK` to `cFAA`, `cRED` to `cE32`, `cYEL` to `cFF3`, and `cBLK` to `c000`. A code affects only the smallest closed shape containing the code's first cell and is removed from visible text. Codes outside closed shapes do not color anything. Default shape fill is white and default stroke is black; dark fills cause white text as in Spec 14.

The smallest closed shape containing a recognized tag gets the corresponding type, and the tag is removed from text:

- `{d}`: document rectangle whose bottom is two quadratic waves, with horizontal control offset `bounds.width/6` and vertical offset `bounds.height/8`;
- `{s}`: storage/cylinder with a two-cubic top ellipse, straight sides, and a cubic bottom; top Y control offset is `cellHeight/2`, bottom is `10*cellHeight/14`, and X control offset is `bounds.width/6`;
- `{io}`: parallelogram;
- `{c}`: decision diamond through left, top, right, and bottom midpoints;
- `{mo}`: manual-operation trapezoid with inverted slant;
- `{tr}`: normal trapezoid;
- `{o}`: four-cubic ellipse using kappa `4*(sqrt(2)-1)/3`.

For IO/trapezoid slant, default offset is `cellWidth/2`; under `--fixed-slope` it is `bounds.height/8`. Tags only transform four-corner closed shapes; malformed/unrecognized tags remain ordinary text. The ordinary CLI does not accept a `--config` option and does not automatically activate `config.xml`. This remains true when the working-directory file is a valid shape configuration and its referenced SVG or PNG asset exists: declarations such as `cust` and `custpng` are ignored, their `{cust}` and `{custpng}` tags remain visible text, and configuration attributes such as `border` do not affect the render.

## Spec 16

By default, detect coincident edges of closed shapes and move each participating edge inward by `min(cellWidth,cellHeight)/5`, producing visual separation between adjoining boxes. `--no-separation` disables this movement and leaves common edges coincident. Preserve separate adjacent closed shapes and nested shapes; remove only geometrically duplicate shapes (same integer point set).

Render storage shapes first in descending vertical-center order. Render all remaining shapes largest area first so smaller/nested objects appear on top. Render point markers after all ordinary paths and text after markers. Open connectors remain behind the closed shapes they attach to. These ordering rules govern nested containers, overlapping boundaries, grids of aligned/touching shapes, and colored inner shapes.

## Spec 17

PNG generation is the exact Java2D compatibility rendering of the geometry above. Use an RGB buffered image for an opaque background and ARGB if background alpha is below 255. Fill the whole canvas with the selected background. Enable Java2D shape antialiasing by default. Draw normal/dashed paths with the strokes in Spec 12. Fill non-dashed closed paths before stroking; do not fill open or dashed paths. Filled arrowheads are drawn without a separate visible stroke. Storage shapes receive their special fill/stroke pass before other shapes.

With shadows enabled, for every closed, non-dashed, non-arrow, non-marker, non-custom shape, fill a gray `(150,150,150)` copy translated by `min(cellWidth,cellHeight)/3.333`, then blur the entire image with a 6-by-6 uniform convolution kernel (each weight `1/36`, edge mode “no operation”). Continue the actual shape drawing on that blurred destination. The result is encoded by Java ImageIO's PNG writer with no timestamps or nondeterministic metadata. Repeated renders of identical normalized input and options, including alternate and overwritten files, must have byte-identical PNG content. This exact pipeline, including Java logical fonts and ImageIO encoding, is required because output bytes are compared directly.

## Spec 18

Rendering switches apply independently to PNG:

- `--no-shadows` skips both shadow fills and blur.
- `--no-antialias` selects Java2D antialiasing off for shapes.
- `--debug` additionally draws one-pixel `(170,170,170)` lines at every multiple of cellWidth and cellHeight across the canvas in XOR mode against white.
- `--round-corners`, `--no-separation`, and `--fixed-slope` change geometry as described above.
- `--scale` changes cells, geometry, strokes, fonts, shadow offset, and canvas together; it is not a post-render resize.

The default background is opaque white. Six-digit `--background` keeps RGB mode and exactly sets the corner/background pixel. Eight-digit RRGGBBAA uses ARGB with the stated alpha, such as `(255,0,0,128)` for `FF000080`. `--transparent` sets `(0,0,0,0)`, produces RGBA PNG with many fully transparent background pixels, and overrides any background option regardless of option order. Shapes themselves retain their normal opaque fills.

## Spec 19

SVG is a deterministic serialization of exactly the same diagram geometry, dimensions, ordering, fills, strokes, text positions, scaling, separation, and special shapes. It contains no `viewBox`. The document skeleton and indentation are exact:

```text
<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<svg 
    xmlns='http://www.w3.org/2000/svg'
    width='WIDTH'
    height='HEIGHT'
    shape-rendering='geometricPrecision'
    version='1.0'>
  <defs>
    <filter id='f2' x='0' y='0' width='200%' height='200%'>
      <feOffset result='offOut' in='SourceGraphic' dx='5' dy='5' />
      <feGaussianBlur result='blurOut' in='offOut' stdDeviation='3' />
      <feBlend in='SourceGraphic' in2='blurOut' mode='normal' />
    </filter>
  </defs>
  <g stroke-width='1' stroke-linecap='square' stroke-linejoin='round'>
    ...layers...
  </g>
</svg>
```

The final bytes are the `>` of `</svg>`; no LF or other byte follows the closing tag. The newline after that line in the Markdown code fence above is presentation only.

Under `--no-antialias`, replace `geometricPrecision` with `optimizeSpeed`. The filter definition remains present even when no shadows are rendered. Unless transparent, the first graphics-layer element is `<rect x='0' y='0' width='WIDTH' height='HEIGHT' style='fill: #rrggbb'/>`; alpha is not serialized in that hex. A fully transparent background omits the rectangle entirely.

## Spec 20

SVG paths serialize Java GeneralPath iteration exactly. Use `M`, `L`, `Q`, `C`, and lowercase `z`, Java float decimal spelling, one separating/trailing space after each non-close command, and this normal-path form:

`    <path stroke='#000000' stroke-width='1.0' stroke-linecap='round' stroke-linejoin='round' fill='white' d='COMMANDS' />`

The stroke width is `min(cellWidth,cellHeight)/10` and is serialized using Java float decimal spelling (for scale 1, `1.0`). Dashed paths add `stroke-dasharray='D,D' stroke-miterlimit='0'`, butt cap, and round join, where `D=min(cellWidth,cellHeight)/2` (scale 1 gives `5.0,5.0`). Shadow paths precede ordinary paths and have exactly `stroke='gray' fill='gray' filter='url(#f2)'`. Colors serialize lowercase `#rrggbb`. Text comes last as:

`    <text x='X' y='Y' font-family='Courier' font-size='SIZE' stroke='none' fill='#rrggbb' ><![CDATA[TEXT]]></text>`

Text is wrapped in CDATA and separate input strings create separate `<text>` elements. With `--svg-font-url URL`, insert at the beginning of `<defs>`:

```text
    <style type='text/css'>
      @font-face {
        font-family: Custom;
        src: url('URL');
      }
    </style>
```

and use `font-family='Custom'` on every text element. SVG written to a file and the same SVG written to stdout must be identical.

## Spec 21

`-h/--html` interprets the input as HTML using lenient parsing. Convert only `<pre>` elements whose `class` attribute value is exactly `textdiagram`; leave ordinary `<pre>` and differently classed code blocks unchanged. Preserve doctype, nesting, headings, paragraphs, metadata (including `<meta charset="UTF-8">`), and all other document content. Replace each selected element, including its ASCII contents, with exactly `<img src="URL" />`. Preserve leading/embedded whitespace inside the selected preformatted content when constructing its diagram. Malformed but recoverable HTML must still be processed.

If no output HTML is supplied, place `INPUT_BASENAME_processed.html` beside the input, always reusing that path. If an output is supplied, use it verbatim. Print `Converting HTML file (INPUT -> OUTPUT)... ` followed by `done`, then `Generating diagrams... `, each generated absolute image path prefixed by a tab, and finally a blank line plus `...done`. The ordinary banner/options block precedes these messages.

## Spec 22

HTML-generated images live in an `images` directory next to the output HTML, and `<img src>` uses a relative `images/NAME.EXT` URL. Default extension is `.png`; `--svg` consistently uses `.svg`. If a selected `<pre>` has an `id` attribute, use its value as NAME after replacing every space with an underscore (hyphens and other filename-safe characters remain), even when the value is empty. Thus `id="   "` produces `images/___.png`, while `id=""` produces the hidden file `images/.png` and replacement `<img src="images/.png" />`. Only a missing `id` attribute uses `ditaa_diagram_N`, where N starts at 1 and increments only for auto-named diagrams; every present ID, including empty and whitespace-only IDs, does not consume a number.

If there are no selected diagrams, including an empty HTML document, exit 0 after printing exactly this message fragment and create neither output nor image directory:

`HTML document does not contain any <pre> tags with their class attribute set to "textdiagram". Nothing to do.`

An empty or whitespace-only selected pre is converted successfully: exit 0, emit no standard error, replace it with the corresponding `<img>`, and create its image (using `ditaa_diagram_1.png` for the first auto-named PNG). A missing HTML input reports `Error: cannot read file PATH` on standard error but the top-level process exits 0. If the output HTML already exists and overwrite is off, exit 0 without replacing it and print `Error: File PATH exists. If you would like to overwrite it, please use the --overwrite option.` If an image exists and overwrite is off, still write the converted HTML, preserve the image, and print `Error: Cannot overwrite file images/NAME.EXT, file already exists. Use the --overwrite option if you would like to allow file overwrite.` Continue with other diagrams. `--overwrite` permits both HTML and images to be replaced.

## Spec 23

The converter must preserve compatibility on degenerate and stress inputs: empty files, whitespace-only files, one character, one short horizontal segment, a single structural point, a 2-by-2 box, single-line text, 800-character lines, filenames over 200 characters, dozens of boxes, five levels of nesting, 50-shape grids, dense junctions, disconnected components, and scale factors through 10. Zero-byte and space/tab-only ordinary inputs succeed and produce deterministic valid PNG/SVG; separator-only input has the exact failure specified in Spec 8. A lone structural-looking glyph is handled without an out-of-bounds read, but its contextual classification includes the isolated-`>` and lone-`~` compatibility cases in Specs 10, 13, and 14. Large shapes are not truncated and output dimensions are derived from the full normalized grid. Different input/output filenames, path depth, or alternative-number suffixes must never alter image bytes for identical diagram content and options.

All fixed comparison cases require exact PNG/SVG bytes, not perceptual similarity. Consequently shape discovery order, duplicate elimination, area ordering, font measurement, integer truncation, antialiasing, shadows, text position, serialization whitespace, and encoding are observable parts of this specification.

## Spec 24

The archive must expose `org.stathissideris.ascii2image.text.StringUtils` as a Java main class. Running it with `java -cp executable org.stathissideris.ascii2image.text.StringUtils` exits 0, writes nothing to standard error, and writes exactly:

```text
1 Testing
2  testing
3 _testing
4 Testing
5 Ttesting
C:\Files\test.txt
C:\Files
test
txt
test.txt

test.txt
txt
test
path: 
base: test
 ext: 
```

The utility semantics represented by that demonstration are: substring containment treats an empty fragment as contained; repeating a string zero times returns empty and otherwise concatenates exactly; blank means empty or entirely whitespace; first-to-upper uppercases only the first character; insert-space-at-capitals separates camel/all-cap runs at every uppercase letter while preserving an initially lowercase run; membership checks compare exactly; filename helpers support Windows backslashes, return the final extension after the last dot (empty/no extension as null/empty in printed form), and separate path, base filename, and extension as demonstrated.

## Spec 25

The archive must expose these additional Java main classes:

- `org.stathissideris.ascii2image.core.PerformanceTester`: from its working directory, read `tests/text/ditaa_bug.txt`, construct the normalized grid and diagram 30 times, print `iteration 0` through `iteration 29`, then `Nmsec for 30 iterations on tests/text/ditaa_bug.txt`, where `N` is a decimal integer immediately followed by `msec`, then `Tests completed`; exit 0 and finish within 10 seconds.
- `org.stathissideris.ascii2image.core.ConfigurationParser`: parse `config.xml` from the current directory with a non-validating SAX parser. A valid `<shapes dir="...">` document containing `<shape tag="..." filename="..." stretch="true|false|yes|no" border="..." shadow="..."/>` resolves relative filenames against `dir` or the config directory, accepts the four boolean spellings, and exits 0 with no output. A missing file exits nonzero with a Java stack trace on standard error containing `FileNotFoundException` and `config.xml (No such file or directory)`.
- `org.stathissideris.ascii2image.core.DocBookConverter`: attempt to create SAX driver `org.apache.crimson.parser.XMLReaderImpl`. The artifact must not bundle that driver, so this entry point exits nonzero with `ClassNotFoundException` and `SAX2 driver class org.apache.crimson.parser.XMLReaderImpl not found` on standard error.
- `org.stathissideris.ascii2image.graphics.ImageHandler`: read `sphere.svg` in the current directory, echo its full SVG text to standard output, then attempt SVG rendering through SAX driver `org.apache.xerces.parsers.SAXParser`. The artifact must not bundle that driver, so this entry point exits nonzero with `ClassNotFoundException` and `SAX2 driver class org.apache.xerces.parsers.SAXParser not found` on standard error. The echoed text must retain its XML declaration, `<svg xmlns="http://www.w3.org/2000/svg"...>` root, and contained elements such as `<circle cx="50" cy="50" r="40" fill="blue"/>`.

Configuration parsing is required for its standalone entry point only; as stated in Spec 15, the normal CLI does not expose configuration/custom-shape activation.
