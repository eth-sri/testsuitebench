# Clarified specification for `executable`

The required artifact is one executable file named `executable`. It is a command-line ASCII/Unicode diagram to SVG converter. The requirements below are the complete behavioral contract; no project source code, sample repository, or network service is part of the contract.

## Spec 1

`executable` must be directly runnable as a native program or executable script and must accept UTF-8 command-line arguments, files, and standard input. A normal single-diagram conversion must finish with status 0, write no diagnostics to standard error, and emit a complete, well-formed UTF-8 SVG document. It must handle empty diagrams, hundreds of columns, hundreds of drawing fragments, at least 200 text items, at least 30 rows, and batches of at least ten files without truncation, crashes, or fixed-size-buffer failures.

The converter implements the deterministic behavior described below. In particular, whitespace, coordinates, class ordering, child ordering, and explicit closing tags are significant because consumers may compare the generated SVG byte-for-byte.

## Spec 2

The top-level command-line interface identifies itself as version `svgbob 0.7.6`. Both `-h` and `--help` exit 0 and print help to standard output; both `-V` and `--version` exit 0 and print the version. The exact long-help output is:

```text
svgbob 0.7.6
SvgBobRus is an ascii to svg converter

USAGE:
    executable [FLAGS] [OPTIONS] [input] [SUBCOMMAND]

FLAGS:
    -h, --help       Prints help information
    -s               parse an inline string
    -V, --version    Prints version information

OPTIONS:
        --background <background>        backdrop background will be filled with this color (default: 'white')
        --fill-color <fill-color>        solid shapes will be filled with this color (default: 'black')
        --font-family <font-family>      text will be rendered with this font (default: 'arial')
        --font-size <font-size>          text will be rendered with this font size (default: 14)
    -o, --output <output>                where to write svg output [default: STDOUT]
        --scale <scale>                  scale the entire svg (dimensions, font size, stroke width) by this factor
                                         (default: 1)
        --stroke-color <stroke-color>    stroke color for all lines (default: 'black')
        --stroke-width <stroke-width>    stroke width for all lines (default: 2)

ARGS:
    <input>    svgbob text file or inline string to parse [default: STDIN]

SUBCOMMANDS:
    build    Batch convert files to svg.
    help     Prints this message or the help of the given subcommand(s)
```

The version output is exactly `svgbob 0.7.6\n`.

## Spec 3

There are three mutually exclusive input modes for a single conversion:

- With no positional `input`, read all bytes through EOF from standard input and decode them as UTF-8.
- With a positional `input` and no `-s`, treat it as a file path and read the entire file.
- With `-s`, treat the positional `input` itself as diagram text. In this mode every two-character sequence backslash + lowercase `n` is replaced by an actual line feed before parsing. Literal line feeds already present in the argument also work.

File input, stdin input, and inline input must produce identical SVG for identical diagram strings. A nonexistent input file exits 1 and writes a line of the form `Failed to open input file PATH: OS-ERROR` to standard error; the text must include the path and, for the usual missing-file case, `No such file or directory`.

Split lines in a CR/LF-aware way: LF, CRLF, and mixtures of the two produce the same row structure and a carriage return is never rendered. A final line terminator and any number of extra final blank lines do not enlarge the canvas. Empty rows between nonempty rows remain real rows and therefore preserve vertical spacing.

## Spec 4

Without `-o`/`--output`, write the pretty SVG to standard output followed by exactly one line feed. With either output option, write the same SVG bytes to the named file without an added final line feed, write nothing to standard output, and exit 0. Existing files may be replaced. Input and output options may appear together and styling options may be combined with either input mode.

If the output cannot be created or written, exit 2 and write `Failed to write to output file PATH: OS-ERROR\n` to standard error. Do not leave ordinary success messages on standard error.

## Spec 5

The following single-conversion settings are supported and are interpolated verbatim into the CSS described later:

- `--background COLOR`, default `white`;
- `--fill-color COLOR`, default `black`;
- `--stroke-color COLOR`, default `black`;
- `--stroke-width NUMBER`, default `2`, parsed as a floating-point number;
- `--font-family TEXT`, default `Iosevka Fixed, monospace` (the help text's reference to Arial is only historical wording);
- `--font-size INTEGER`, default `14`, parsed as an unsigned integer and emitted with `px`;
- `--scale NUMBER`, default `1`, parsed as a floating-point multiplier.

Values such as named colors, `transparent`, three- and six-digit hex colors, and `rgb(...)` are not validated as colors; preserve them literally. Font families may contain spaces. Accept at least font sizes 8–48, stroke widths 1–50, and scales `0.1`, `0.25`, `0.5`, `1`, `1.5`, `2`, `3`, and `5`.

An invalid numeric value exits 1 and writes `Illegal value for argument NAME: PARSE-ERROR\n` to standard error. For example, a bad integer font size uses the parse detail `invalid digit found in string`. Scaling multiplies canvas dimensions and every geometry/text coordinate and geometric radius. It deliberately does not change the numeric CSS `font-size` or `stroke-width` declarations.

## Spec 6

The `build` subcommand batch-converts files. Its help and version invocations exit 0. Their exact output is respectively:

```text
executable-build 0.0.1
Batch convert files to svg.

USAGE:
    executable build [OPTIONS]

FLAGS:
    -h, --help       Prints help information
    -V, --version    Prints version information

OPTIONS:
    -i, --input <input>      set input file pattern like: *.bob or dir/*.bob
    -o, --outdir <outdir>    set dir of svg files
```

and `executable-build 0.0.1\n`.

For ordinary batch execution, `-i`/`--input` has no effective default: omitting it supplies an empty input path. Consequently, `executable build` exits 1, writes exactly `[Error]: No such dir name is  !\n` to standard output and nothing to standard error, and converts no files even when the current directory contains `.bob` files. When supplied, the input option may name a directory, a wildcard-like path such as `dir/*.bob`, or one explicit filename. Determine the input directory as the directory itself when it is a directory, otherwise its parent. Determine the selected extension from the input path, defaulting to `bob` if there is none. Scan only immediate regular files in that directory and convert every file whose final extension exactly equals the selected extension. Thus `*.txt` converts text files too, while `*.bob` ignores `.txt` and `.md`; an explicit `specific.bob` still selects all `.bob` files in its parent directory. Do not recurse.

Replace only the selected file's final extension with `.svg`, preserving the rest of its basename, so `my.file.v2.bob` becomes `my.file.v2.svg`. By default put outputs beside the inputs. With `-o`/`--outdir`, put them in that directory and recursively create missing directory components. Existing directories and unrelated files must remain intact; writing beside the inputs must not alter the source files.

Before each conversion print `INPUT_PATH => OUTPUT_PATH\n` to stdout. If nothing matches, print nothing. Batch-generated SVG files contain the normal default-settings SVG without a final line feed. A missing input directory prints `[Error]: No such dir name is DIRECTORY !\n` to stdout. Compatibility requirement: after any ordinary `build` invocation—including a successful conversion, no matches, or a reported error—the process exits with status 1.

## Spec 7

Model the diagram as terminal cells. A logical cell is 1 unit wide and 2 units high. The default geometry scale is 8 pixels per logical unit, so a terminal column is 8 px and a terminal row is 16 px. The CLI scale factor `f` changes the geometry scale to `S = 8f`.

Within each cell `(column c, row r)`, use a 4-by-8 subdivision grid. Local x coordinates are multiples of `1/4` from 0 through 1 and local y coordinates are multiples of `1/4` from 0 through 2. The commonly used named points are:

```text
          x=0   .25   .50   .75  1.0
y=0       A     B     C     D     E
y=.5      F     G     H     I     J
y=1       K     L     M     N     O
y=1.5     P     Q     R     S     T
y=2       U     V     W     X     Y
```

A local point `(x,y)` in cell `(c,r)` becomes pixels `((c+x)S, (2r+y)S)`. Text starts at local point Q, giving `(8c+2, 16r+12)` at default scale.

Canvas bounds are based on the greatest column and row containing a non-whitespace, non-null, non-quoted character before any recognition is performed. If these are `max_col` and `max_row`, width is `S(max_col+2)` and height is `2S(max_row+2)`. If there is no such cell, behave as if both maxima were 0, producing 16×32 by default. Leading spaces therefore move content and enlarge width; trailing spaces/tabs and whitespace-only input do not. Longer rows and more non-final rows enlarge the corresponding dimension. Render width and height as shortest decimal numbers, omitting `.0` for integral results.

## Spec 8

Parse Unicode by display width, not UTF-8 byte length. Each ordinary character occupies one cell. A terminal-wide character such as a CJK ideograph, Korean/Japanese character, or emoji occupies two columns: reserve a non-rendering placeholder in its second column so following content has the correct x position. Never emit that placeholder. Preserve the original wide character in its text element.

Rows may have unrelated lengths and storage must grow dynamically. Ignore whitespace as drawable content, while retaining its effect on the coordinates of later characters and retaining interior blank rows. Tabs count as whitespace cells at their literal character positions; no visible text node is created for them. Trailing whitespace never creates bounds or SVG elements.

## Spec 9

Every result uses the following outer order: opening `<svg>`, `<style>`, `<defs>`, backdrop `<rect>`, recognized ungrouped fragments, then any `<g>` groups, then `</svg>`. The opening tag is exactly:

```text
<svg xmlns="http://www.w3.org/2000/svg" width="W" height="H" class="svgbob">
```

Use two spaces per nesting level. All SVG elements, including empty ones, use explicit paired closing tags, never XML self-closing syntax. The backdrop is exactly:

```text
  <rect class="backdrop" x="0" y="0" width="W" height="H"></rect>
```

The document has precisely one opening and one closing `svg` tag. XML-special content must be escaped. The in-memory/rendered SVG has no terminal newline; the normal stdout path adds the newline as described in Spec 4.

## Spec 10

The `<style>` child must contain this exact base stylesheet and whitespace. Replace the five uppercase placeholders with current setting values. `STROKE_WIDTH` uses shortest float formatting and `FONT_SIZE` is the integer followed by `px`.

```css
.svgbob line, .svgbob path, .svgbob circle, .svgbob rect, .svgbob polygon {
  stroke: STROKE_COLOR;
  stroke-width: STROKE_WIDTH;
  stroke-opacity: 1;
  fill-opacity: 1;
  stroke-linecap: round;
  stroke-linejoin: miter;
}

.svgbob text {
  white-space: pre;
  fill: STROKE_COLOR;
  font-family: FONT_FAMILY;
  font-size: FONT_SIZEpx;
}

.svgbob rect.backdrop {
  stroke: none;
  fill: BACKGROUND;
}

.svgbob .broken {
  stroke-dasharray: 8;
}

.svgbob .filled {
  fill: FILL_COLOR;
}

.svgbob .bg_filled {
  fill: BACKGROUND;
  stroke-width: 1;
}

.svgbob .nofill {
  fill: BACKGROUND;
}

.svgbob .end_marked_arrow {
  marker-end: url(#arrow);
}

.svgbob .start_marked_arrow {
  marker-start: url(#arrow);
}

.svgbob .end_marked_diamond {
  marker-end: url(#diamond);
}

.svgbob .start_marked_diamond {
  marker-start: url(#diamond);
}

.svgbob .end_marked_circle {
  marker-end: url(#circle);
}

.svgbob .start_marked_circle {
  marker-start: url(#circle);
}

.svgbob .end_marked_open_circle {
  marker-end: url(#open_circle);
}

.svgbob .start_marked_open_circle {
  marker-start: url(#open_circle);
}

.svgbob .end_marked_big_open_circle {
  marker-end: url(#big_open_circle);
}

.svgbob .start_marked_big_open_circle {
  marker-start: url(#big_open_circle);
}
```

The opening serialization is `  <style>` immediately followed by the first selector (no newline after the opening tag). With no custom legend CSS, insert one additional newline after the final base rule and then `</style>` on that same position, yielding a blank line immediately before `</style>`. With custom CSS, add a blank line after the base rules, append the custom rules exactly as described in Spec 23, and put `</style>` immediately after the last custom rule's closing brace.

## Spec 11

Immediately after the style, emit this exact marker definition subtree, regardless of whether the diagram uses markers:

```xml
  <defs>
    <marker id="arrow" viewBox="-2 -2 8 8" refX="4" refY="2" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <polygon points="0,0 0,4 4,2 0,0"></polygon>
    </marker>
    <marker id="diamond" viewBox="-2 -2 8 8" refX="4" refY="2" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <polygon points="0,2 2,0 4,2 2,4 0,2"></polygon>
    </marker>
    <marker id="circle" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <circle cx="4" cy="4" r="2" class="filled"></circle>
    </marker>
    <marker id="open_circle" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <circle cx="4" cy="4" r="2" class="bg_filled"></circle>
    </marker>
    <marker id="big_open_circle" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <circle cx="4" cy="4" r="3" class="bg_filled"></circle>
    </marker>
  </defs>
```

## Spec 12

Serialize recognized primitives with attributes in these exact orders:

```text
<line x1="X1" y1="Y1" x2="X2" y2="Y2" class="solid"></line>
<line x1="X1" y1="Y1" x2="X2" y2="Y2" class="broken"></line>
<rect x="X" y="Y" width="W" height="H" class="solid nofill" rx="R"></rect>
<circle cx="CX" cy="CY" r="R" class="nofill"></circle>
<circle cx="CX" cy="CY" r="R" class="filled"></circle>
<path d="M X1,Y1 A R,R 0,MAJOR,SWEEP X2,Y2" class="nofill"></path>
<polygon points="X1,Y1 X2,Y2 ..." class="filled"></polygon>
<text x="X" y="Y" >CONTENT</text>
```

Filled or broken rectangles use `filled` instead of `nofill` and/or `broken` instead of `solid`, in the order line-style then fill-style. Marker lines retain `solid`/`broken` first and append `start_marked_KIND` then `end_marked_KIND`. Custom classes are appended after built-in classes. Rectangles always have `rx`, using `0` for sharp corners. Arc rotation is always 0; ordinary arcs use major flag 0, while a recognized long/three-quarter arc may use 1. Numeric attributes use shortest decimal formatting.

Merge touching collinear ordinary line fragments recursively into one line, propagating `broken` if either piece is broken. Marker extraction is a later compatibility boundary: do not merge the resulting marker-bearing line with adjacent or overlapping connector fragments unless a specific formation says otherwise; Spec 18 gives the exact endpoint cases. Do not merge separated collinear pieces or perpendicular pieces. Sort stable output geometrically by left bound, then top bound, then right bound, then bottom bound; for identical bounds use this type rank: line, marker line, circle, arc, polygon, rectangle, text. Thus like items are ordered left-to-right first and top-to-bottom second. For example, `hello world\nagain` emits its text elements in this order: `<text x="2" y="12" >hello</text>`, `<text x="2" y="28" >again</text>`, then `<text x="50" y="12" >world</text>`. Connected fragments that cannot be promoted to one shape are emitted together inside `<g>` in the same deterministic order. Nested shapes and overlapping shapes remain independently visible.

## Spec 13

Ordinary non-drawing characters form text. Merge immediately horizontally adjacent text characters on the same row into one `<text>` node; a space or drawing fragment breaks a text span, so multi-word phrases normally become one text node per word. Vertically adjacent words stay separate. Render each span at Q of its first cell: default `(8c+2,16r+12)`. This preserves blank-row spacing, indentation, labels inside or outside shapes, text beside arrows, aligned boxes, single characters, long lines, numeric strings, email addresses, and arbitrary UTF-8.

Escape text as follows: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`, `'` → `&#39;`, and `"` → `&quot;`. Do not double-escape. Characters that have a drawing meaning are still text when their required geometric context is absent; for example a standalone uppercase `V` and isolated `o`, `O`, `*`, and `.` remain text. This fallback does not apply to the unquoted hyphen and slash cases described in Spec 14 merely because they occur within otherwise alphabetic text.

Double-quoted runs are an explicit literal escape. Remove the surrounding quotes and render everything inside as one literal text span, even drawing characters and spaces. Backslash-quote inside the run does not terminate it and is preserved in its literal form. Compatibility quirk: quoted runs are removed before canvas bounds are computed, so a diagram made only of quoted strings keeps the minimal 16×32 canvas even though its text coordinates may lie outside it. The quotes themselves are not rendered.

## Spec 14

The ASCII drawing alphabet is `- ~ | ! : + X * # o O _ . , ' ’ ` / \ ( ) V v ^ > < =`. Shape, junction, endpoint, and arrow recognition is context-sensitive, but an unquoted `-` or `/` contributes its line geometry even when embedded in prose. Use neighboring cells as required by each recognizer; diagonal proximity by itself does not make every endpoint glyph connected.

Core line behavior in local coordinates is:

- `-` is a solid K–O horizontal segment and adjacent segments merge.
- `~` is the broken K–O equivalent.
- `_` is a solid U–Y bottom-edge segment.
- `=` is two solid horizontal segments at y=.75 and y=1.25 (and adjacent `=` cells merge into two parallel lines).
- `|` is a solid C–W vertical segment; adjacent rows merge.
- A `!` or `:` cell becomes a broken C–W vertical segment when it has a straight vertical `!`, `:`, or `|` cell immediately above or below it; touching a half-cell vertical spoke supplied by `+` does not trigger this recognition. Adjacent segments merge recursively and the result is broken if any constituent is broken. Thus `!\n!`, `:\n:`, `!\n|`, `|\n!`, `!\n:`, and `:\n!` each produce one broken vertical line from `(4,0)` to `(4,32)`. A lone `!` or `:` without such a neighboring straight vertical cell remains text, including the one-row sides between `+` corners described in Spec 15.
- `/` is E–U and `\` is A–Y. Runs in diagonally neighboring cells merge into a continuous diagonal. At a following vertical or horizontal connector, clip/split them at the shared M or boundary point so there is no gap.
- `+` joins whichever strong line directions reach it: left K–M, right M–O, up C–M, down M–W, and the corresponding A/E/U/Y diagonal spokes. It may be a corner, T-junction, cross, or eight-direction junction.
- `X` supplies the two full diagonals and, when reached by orthogonal neighbors, corresponding spokes.

Drawing takes precedence over a possible textual interpretation when the character is geometrically connected. In addition, an unquoted hyphen or slash is still a stroke when embedded in ordinary text: `opt-in` emits text `opt`, the solid line `<line x1="24" y1="8" x2="32" y2="8" class="solid"></line>`, and text `in`; `/usr/bin` emits a solid E–U line in each slash cell and the text spans `usr` and `bin`. By contrast, plus signs in prose and standalone arrow-like letters remain text when no drawing connection exists. Dense grids, shared edges/vertices, close fragments, and overlapping connections must be resolved from actual endpoints rather than merely from character identity.

## Spec 15

Promote four connected axis-aligned boundary lines into one rectangle when they form exactly two parallel pairs joined by perpendicular corners. ASCII `+-----+` / `|     |` / `+-----+` and Unicode equivalents therefore become a `<rect>`, not four lines. If the top-left and bottom-right corner cells are `(c1,r1)` and `(c2,r2)`, the default sharp rectangle starts at `(8c1+4,16r1+8)`, ends at `(8c2+4,16r2+8)`, is `class="solid nofill"`, and has `rx="0"`.

Use `.-----.` with vertical sides and `'-----'` (or compatible comma/backtick curved corners) for rounded rectangles. Four right-angle arc corners plus their four connecting lines promote to one rectangle with the common radius; the usual one-cell corner radius is logical .5, hence `rx="4"` by default. Unicode `╭ ╮ ╰ ╯` works the same way. If any boundary constituent of a boundary that is actually promoted is broken, the promoted rectangle is `broken`; otherwise its outline is solid. For example, `+~~~+\n|   |\n+~~~+` promotes to `<rect x="4" y="8" width="32" height="32" class="broken nofill" rx="0"></rect>`. Filled hash cells are handled separately as described in Spec 20 and are not inferred from an outlined rectangle.

A one-cell-high apparent broken vertical side is not promoted. The exact input `+~~~+\n!   !\n+~~~+` has no non-backdrop `<rect>`. It emits `<text x="2" y="28" >!</text>` and `<text x="34" y="28" >!</text>`, followed by two groups. The first group contains, in order, the broken line `(4,8)–(36,8)` and solid lines `(4,8)–(4,16)` and `(36,8)–(36,16)`. The second contains, in order, solid line `(4,32)–(4,40)`, broken line `(4,40)–(36,40)`, and solid line `(36,32)–(36,40)`.

Recognize multiple, nested, overlapping, very wide, very tall, one-cell/minimal, and differently sized rectangles independently. Directly adjacent boxes are a compatibility exception. The input `+---++---+\n|   ||   |\n+---++---+` produces no `<rect>` elements; it produces one `<g>` containing, in order, the merged top line `(4,8)–(76,8)`, vertical lines at x coordinates 4, 36, 44, and 76 from y=8 to y=40, and the merged bottom line `(4,40)–(76,40)`. Nested boxes such as `+---------+\n| +-----+ |\n| |     | |\n| +-----+ |\n+---------+` do promote independently to two rectangles. A grid or irregular network containing more than the four sides of one rectangle likewise remains a `<g>` of lines where promotion would incorrectly erase internal/shared edges. Filled regions made from orthogonally connected `#` cells are filled rectangles rather than text.

## Spec 16

Periods, commas, apostrophes, typographic apostrophes, backticks, parentheses, slashes, and backslashes form curved corners when connected:

- `.` provides rounded top corners, `,` a top-left curved transition, `'`/`’` bottom transitions, and backtick a bottom-left transition.
- `(` and `)` normally render left and right arc sides respectively. Between horizontal neighbors they may instead continue a line; between vertical neighbors they form the curved side.
- A curved cell combines an SVG `A` path and any short tangent line needed to reach adjacent cell boundaries. Small common corners have radius `.5S`; larger ASCII formations use radii determined by their circle quadrant.
- Four compatible right-angle arcs are promoted to the rounded rectangle of Spec 15. Unclosed curves remain explicit `<path>` elements, possibly grouped with tangent `<line>` elements.

Support quarter, half, three-quarter, narrow, wide, nested, and mixed sharp/rounded arc arrangements. Arc sweep direction must match the visible glyph: top-left, top-right, bottom-left, and bottom-right curves bend into their respective quadrants. Never emit NaN, negative coordinates for ordinary nonnegative input positions, or absurd coordinates for long/steep diagonals.

## Spec 17

Recognize arrowheads only when connected in the indicated direction. `>` reached from the left, `<` reached from the right, `^` reached from below, and `v` or `V` reached from above emit filled triangular polygons. Standalone `V` is text. The basic default arrowhead polygons within a cell are:

- right: F–O–P, giving `x,y-4`, `x+8,y`, `x,y+4` around the line endpoint;
- left: J–K–T;
- down: F–J–W, giving `x-4,y`, `x+4,y`, `x,y+12` in the standard vertical case;
- up: P–C–T.

ASCII arrowhead recognition is orthogonal; diagonal adjacency alone does not rotate or skew a head. In particular, this input:

```text
\
 >
```

emits `<line x1="0" y1="0" x2="8" y2="16" class="solid"></line>` followed by visible text `&gt;` at `(10,28)`, with no polygon. Support the four orthogonal directions, opposite pairs, four-way junctions, repeated arrowheads, bidirectional arrows such as `<---->`, short/minimal arrows, long arrows, vertical arrows, parallel arrows, crossed orthogonal arrows, and arrows between or pointing at shapes. Preserve both the line and its recognized head(s); ordinary heads serialize as `polygon class="filled"` in geometric order.

## Spec 18

Endpoint glyphs connected to a line have marker semantics:

- `*` is a small filled circle; `o` is a small open circle; `O` is a larger open circle.
- On orthogonal connections, `#` is a filled square-like endpoint; on diagonal connections it is a diamond endpoint.
- These glyphs can produce marker-bearing line fragments at either end of a horizontal or vertical connector and in mixed combinations.

Marker extraction does not normalize every endpoint and connector into one line. The following default-scale outputs are exact, including element order and line direction:

| Input | Drawing lines after the backdrop |
|---|---|
| `*---` | `(4,8)–(4,8)` with `class="solid end_marked_circle"`; then `(8,8)–(32,8)` with `class="solid"` |
| `---*` | `(0,8)–(28,8)` with `class="solid end_marked_circle"`; then `(24,8)–(28,8)` with `class="solid"` |
| `o---` | `(16,8)–(4,8)` with `class="solid end_marked_open_circle"`; then `(16,8)–(32,8)` with `class="solid"` |
| `O---` | `(16,8)–(4,8)` with `class="solid end_marked_big_open_circle"`; then `(16,8)–(32,8)` with `class="solid"` |
| `---o` | `(0,8)–(28,8)` with `class="solid end_marked_open_circle"` |
| `---O` | `(0,8)–(28,8)` with `class="solid end_marked_big_open_circle"` |
| `o---*` | `(16,8)–(4,8)` with `class="solid end_marked_open_circle"`; then `(16,8)–(36,8)` with `class="solid end_marked_circle"`; then `(32,8)–(36,8)` with `class="solid"` |

Vertical orientation follows the same serialized direction rather than visual top-to-bottom order. For `o\n|\n|`, first emit the upward line `(4,12)–(4,8)` with `class="solid end_marked_open_circle"`, then the unmarked line `(4,16)–(4,48)`. Thus the visually top endpoint is the `end` of the first line, not its `start`. Filled circles select `circle`; a small open circle selects `open_circle`; a larger one selects `big_open_circle`. Other unmerged configurations emit their explicit circle, rect, diamond, or arrow polygon and connecting line. Empty or whitespace-only input must never create spurious markers, while marker definitions in `<defs>` are always present.

## Spec 19

Recognize the following complete open-circle ASCII templates as single `<circle class="nofill">` elements. The shown center and radius are default pixel values relative to the template's top-left cell; all three values and any placement offset are multiplied by CLI scale `f`.

```text
C0 (center 8,8; radius 4)       C1 (center 12,8; radius 8)
()                              (_)

C2 (center 16,24; radius 12)    C3 (center 20,24; radius 16)
 __                              ,-.
(__)                            (   )
                                 `-'

C4 (center 24,24; radius 20)    C5 (center 28,40; radius 24)
 .--.                              _
(    )                           .' '.
 `--'                           (     )
                                 `._.'

C6 (center 32,40; radius 28)    C7 (center 36,40; radius 32)
   __                              ___
 ,'  '.                          ,'   '.
(      )                        (       )
 `.__.'                          `.   .'
                                   `-'

C8 (center 36,48; radius 36)    C9 (center 40,48; radius 40)
   ___                             ____
 ,'   `.                          ,'    `.
/       \                        /        \
\       /                        \        /
 `.___.'                          `.____.'

C10 (center 48,56; radius 44)   C11 (center 52,56; radius 48)
    ____                            _____
  .'    `.                        ,'     `.
 /        \                      /         \
(          )                    (           )
 \        /                      \         /
  `.____.'                        `._____.'

C12 (center 56,64; radius 52)
    ______
  ,'      `.
 /          \
|            |
|            |
 \          /
  `.______.'
```

Spaces shown inside and before boundary glyphs are part of each formation. Equivalently, implementations may pattern-match the normalized non-space boundary cells and use radii `.5, 1, 1.5, ... 6.5` logical units.

Detect multiple templates independently when stacked, side-by-side, in a grid, nested in a box, partly overlapping, or connected by lines/arrows. Keep text inside a circle as later visible text. A circle at column offset 8 shifts cx by 64 px. For example `()` is `(cx,cy,r)=(8,8,4)` normally, `(4,4,2)` at scale .5, `(16,16,8)` at scale 2, and `(24,24,12)` at scale 3. A C3 circle becomes `(60,72,48)` at scale 3.

## Spec 20

Filled and polygonal ASCII diagrams must retain their topology. `/`, `\`, `_`, `-`, `+`, `X`, and their curved-corner variants can form triangles, diamonds, pentagons, hexagons, octagons, trapezoids, parallelograms, kites, stars, concave shapes, L-shapes, zigzags, and other irregular closed or open outlines. Render arbitrary outlines as merged line/path fragments in a `<g>` unless they match a promoted primitive. Do not invent a fill for an outline.

Connected `#` indicates solid fill only through horizontal or vertical adjacency. On such adjacency, each `#` contributes a default-pixel `<rect>` at local F–T—an 8×8 rect positioned 4 px below its row's top—with `class="solid filled" rx="0"`; it also contributes the short connector spokes needed to join `#` cells above or below. Do not coalesce a raster-like block, triangle, or diamond of orthogonally connected hashes into one large shape: preserve the multiple small filled rects, which visibly form the region. Mere diagonal adjacency is not a hash connection: `# \n #` emits two visible `#` text elements at `(2,12)` and `(10,28)`, with no rectangle or polygon. Two horizontally adjacent stars are another compatibility special case: `**` emits only `<line x1="4" y1="8" x2="12" y2="8" class="solid"></line>`, with no circle elements. Stars attached to other connectors follow Spec 18. Unicode filled triangles and diamonds are filled polygons. Preserve separate vertices and alternating slopes in concave, star, large-many-vertex, mixed, and overlapping shapes. Degenerate or very small patterns must still produce valid positive or zero-sized primitives as dictated by their endpoints and must not crash.

## Spec 21

Support these Unicode single-line and geometric glyphs using the local point notation from Spec 7:

| Glyphs | Fragments |
|---|---|
| `‾`, `¯` | solid A–E horizontal line |
| `─`, `–`, `—` | solid K–O horizontal line |
| `┄` | broken K–O line |
| `│` | solid C–W vertical line |
| `╎`, `┊`, `┆` | broken C–W line |
| `╲` | solid A–Y diagonal |
| `╱` | solid E–U diagonal |
| `╳` | both A–Y and E–U |
| `┼` | C–W plus K–O |
| `┌`, `┐`, `┘`, `└` | center-to-right/down, left/down, up/left, and up/right corner pairs |
| `├`, `┤`, `┬`, `┴` | complete vertical/horizontal T junctions |
| `╭`, `╮`, `╰`, `╯` | radius-.5 curved corner plus tangent segment |
| `◜`, `◝`, `◟`, `◞` | radius-1 quadrant arc plus center vertical tangent |
| `▏`, `▕` | vertical B–V and D–X respectively |
| `□` | open small square outline using A–E, D–X, Y–U, B–V |
| `▪` | filled rectangle from F to T |
| `◆` | filled K–H–O–R–K diamond |
| `○`, `●` | radius-.5 circle centered M, open and filled respectively |
| `▲`/`▴`, `▼`/`▾`, `◀`/`◂`/`◄`, `▶`/`▸`/`►` | filled up, down, left, and right arrow polygons |
| `∠` | E–U plus U–Y |
| `⋀` | U–C plus C–Y |

Adjacent compatible Unicode fragments merge exactly like ASCII fragments. Thus `┌─┐/│ │/└─┘` promotes to one sharp rect; `╭─╮/│ │/╰─╯` promotes to one rounded rect. `◇`, `◉`, and `◎` have no special primitive in this contract and remain text when encountered.

## Spec 22

Support Unicode double and mixed box drawing. `═` produces parallel K–O and P–T horizontal lines; `║` produces parallel B–V and D–X vertical lines. The corners `╔╗╚╝`, T junctions `╦╩╠╣`, and crossing `╬` connect the appropriate pairs of these parallel tracks. A closed `╔═╗/║ ║/╚═╝` becomes two concentric `solid nofill` rectangles. A double-line grid retains every internal track and produces multiple rectangles/lines.

Mixed junctions `╒ ╕ ╘ ╛` combine a centered single vertical track with two horizontal tracks; `╓ ╖ ╙ ╜` combine a centered single horizontal track with two vertical tracks. Also support `╞ ╡ ╤ ╥ ╢ ╟ ╧ ╨ ╪ ╫` as the corresponding mixed T/cross variants. Lines sharing endpoints merge per track without collapsing two parallel tracks into one. Mixed Unicode/ASCII diagrams, rounded borders containing `○`/`●`/`◆`, and dense single/double grids must remain valid and spatially aligned.

## Spec 23

A styling legend begins at the first exact substring `# Legend:`. Once recognized, the legend and everything following it are excluded from diagram bounds and drawing. The header may have horizontal whitespace around `#` and after the colon but must end in a newline.

Each following valid definition is `IDENT [spaces] = [spaces] {RAW_CSS}`. `IDENT` must begin with an ASCII letter or underscore and continue with ASCII letters, digits, or underscores. `RAW_CSS` is every character up to the next brace and may contain spaces, tabs, line feeds, missing semicolons, commas, parentheses, long values, gradients, filters, transforms, clip paths, animations, and other arbitrary CSS; preserve it byte-for-byte. Nested braces are unsupported. Parse definitions in order until the first invalid definition. If the first is invalid, or the legend is empty or begins with a CSS comment, accept zero definitions without failing conversion. Always discard the entire legend tail. Preserve duplicate definitions so normal CSS cascade order applies, preserve case, preserve unused definitions, and support at least twelve entries and long identifiers/values.

For every parsed pair append this exact custom rule, separating rules by one line feed:

```text
.svgbob .IDENT{ RAW_CSS }
```

The one space after `{` and before `}` is added by the converter in addition to whitespace already in `RAW_CSS`. Examples: `box1={fill:red;}` becomes `.svgbob .box1{ fill:red; }`; `box2  =  {  fill: green;  }` retains the two leading/trailing spaces inside the braces in addition to the wrapper spaces. Definitions beginning with a digit or containing `-` or `.` terminate the valid prefix and are omitted.

## Spec 24

Inside a rectangle, circle, or polygon that has actually been promoted to a single shape primitive, a text span that is exactly `{IDENT}` or `{IDENT1,IDENT2,...}` is a class marker rather than visible text. For shape markers, `IDENT` must begin with an ASCII letter and continue with ASCII letters or digits; unlike legend-definition identifiers in Spec 23, it cannot contain an underscore. There is no whitespace around commas. Apply every class from a valid span to the smallest/deepest promoted enclosing shape, append them after its built-in classes, and remove that span. Multiple valid marker spans add multiple classes in encounter order, and comma-separated classes do likewise; for example `{a} {b}` and `{a,b}` both append `a b`. A class need not be defined in a legend, and the same class may be reused by multiple promoted shapes. Apply markers independently to promoted nested inner and outer shapes and to supported non-rectangle primitives.

A visually closed boundary that remains a `<g>` of fragments is not a shape for marker association: its marker text stays visible. This is why, in a rounded box with an outgoing connector merged into its boundary, `{w}` can remain a `<text>` element even though other independently promoted boxes in the same diagram receive class `w` and lose their markers. `{}`, `{with space}`, `{99red}`, and spans containing drawing characters such as hyphens or underscores do not parse as class markers and remain ordinary visible text/fragments. In particular, `{my_2}` becomes text `{my`, a solid underscore line, and text `2}`. A comma-separated span is all-or-nothing: `{a,B_2}` applies neither class and becomes text `{a,B`, a solid underscore line, and text `2}`. Legend identifiers such as `my_2` remain valid for CSS: the definition `my_2={fill:red;}` emits `.svgbob .my_2{ fill:red; }`; this does not make `{my_2}` a valid shape marker. If legend parsing yields no CSS, otherwise valid markers still become element classes. Malformed legend content never removes already parsed shape classes and never causes a nonzero exit.

## Spec 25

The empty/default serialization is the definitive boilerplate check. For empty input on stdout, the output must be exactly the following plus one final line feed:

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="16" height="32" class="svgbob">
  <style>.svgbob line, .svgbob path, .svgbob circle, .svgbob rect, .svgbob polygon {
  stroke: black;
  stroke-width: 2;
  stroke-opacity: 1;
  fill-opacity: 1;
  stroke-linecap: round;
  stroke-linejoin: miter;
}

.svgbob text {
  white-space: pre;
  fill: black;
  font-family: Iosevka Fixed, monospace;
  font-size: 14px;
}

.svgbob rect.backdrop {
  stroke: none;
  fill: white;
}

.svgbob .broken {
  stroke-dasharray: 8;
}

.svgbob .filled {
  fill: black;
}

.svgbob .bg_filled {
  fill: white;
  stroke-width: 1;
}

.svgbob .nofill {
  fill: white;
}

.svgbob .end_marked_arrow {
  marker-end: url(#arrow);
}

.svgbob .start_marked_arrow {
  marker-start: url(#arrow);
}

.svgbob .end_marked_diamond {
  marker-end: url(#diamond);
}

.svgbob .start_marked_diamond {
  marker-start: url(#diamond);
}

.svgbob .end_marked_circle {
  marker-end: url(#circle);
}

.svgbob .start_marked_circle {
  marker-start: url(#circle);
}

.svgbob .end_marked_open_circle {
  marker-end: url(#open_circle);
}

.svgbob .start_marked_open_circle {
  marker-start: url(#open_circle);
}

.svgbob .end_marked_big_open_circle {
  marker-end: url(#big_open_circle);
}

.svgbob .start_marked_big_open_circle {
  marker-start: url(#big_open_circle);
}

</style>
  <defs>
    <marker id="arrow" viewBox="-2 -2 8 8" refX="4" refY="2" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <polygon points="0,0 0,4 4,2 0,0"></polygon>
    </marker>
    <marker id="diamond" viewBox="-2 -2 8 8" refX="4" refY="2" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <polygon points="0,2 2,0 4,2 2,4 0,2"></polygon>
    </marker>
    <marker id="circle" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <circle cx="4" cy="4" r="2" class="filled"></circle>
    </marker>
    <marker id="open_circle" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <circle cx="4" cy="4" r="2" class="bg_filled"></circle>
    </marker>
    <marker id="big_open_circle" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <circle cx="4" cy="4" r="3" class="bg_filled"></circle>
    </marker>
  </defs>
  <rect class="backdrop" x="0" y="0" width="16" height="32"></rect>
</svg>
```

As coordinate sanity checks at default scale: input `A` adds `  <text x="2" y="12" >A</text>` to the 16×32 shell; input `---` has width 32 and adds one solid line from `(0,8)` to `(24,8)`; input `+-----+\n|     |\n+-----+` has a 64×64 canvas and one rect at `x=4 y=8 width=48 height=32 rx=0`; replacing the four corner glyphs with `.` on top and `'` on bottom changes only `rx` to 4. These examples also define the expected padding and coordinate convention.

## Spec 26

Complex behavior is compositional: perform recognition over the whole grid, merge touching fragments recursively, promote eligible complete circles and rectangles without consuming unrelated enclosed text, emit endpoint-marker fragments, associate class tags with the deepest promoted enclosing shape, and finally sort/serialize. This must work for circuits, architecture diagrams, flowcharts, large grids, multiple aligned boxes, mixed ASCII and Unicode, circles connected to boxes or arrows, shared edges, dense intersections, near-overlaps, and steep/long diagonals, subject to the explicit compatibility cases above.

Ambiguous or malformed diagram syntax must degrade to visible text or lower-level line/path fragments rather than crash. Preserve every unrelated label. Do not add warnings. Every successful conversion—including empty, whitespace-only, malformed legends, dense diagrams, and files with final newlines—must remain valid XML with the mandatory style, definitions, backdrop, and finite coordinates.
