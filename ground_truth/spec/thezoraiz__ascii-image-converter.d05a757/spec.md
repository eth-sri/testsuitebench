# Clarified specification for `executable`

The required artifact is a command-line program named exactly `executable`. It converts raster images to character art. All text described below is UTF-8. Unless a rule explicitly says otherwise, diagnostics and normal output go to standard output and standard error is empty.

## Spec 1

The command-line shape is:

```text
executable [image paths/URLs or the stdin marker -] [flags]
```

Flags may occur before, after, or between operands. The supported flags and aliases are:

- `-h`, `--help`; `-v`, `--version`
- `-C`, `--color`; `--color-bg`
- `-d`, `--dimensions` followed by a comma-separated integer list
- `-W`, `--width` followed by an integer; `-H`, `--height` followed by an integer
- `-m`, `--map` followed by a string
- `-b`, `--braille`; `--threshold` followed by an integer; `--dither`
- `-g`, `--grayscale`; `-c`, `--complex`; `-f`, `--full`; `-n`, `--negative`
- `-x`, `--flipX`; `-y`, `--flipY`
- `-s`, `--save-img` followed by a directory; `--save-txt` followed by a directory; `--save-gif` followed by a directory
- `--save-bg` followed by comma-separated integers; `--font` followed by a path; `--font-color` followed by comma-separated integers
- `--only-save`; `--formats`

Long boolean flags accept an explicit assignment such as `--color=true`. Repeating a scalar flag is legal; the last parsed value may be used. `--` ends flag parsing, so every following token is an input operand even when it begins with `-`.

An unknown flag or a syntactically malformed flag value is a parser error: exit with status 1, identify the offending flag/value, and show usage information. In particular, missing values for `--save-img`, `--save-txt`, `--save-gif`, `--font`, `-m`, and `--map` must include `needs an argument`. A non-integer supplied to width, height, or threshold must include `invalid argument "VALUE"`; threshold errors must identify the `--threshold` flag and include the underlying `strconv.ParseInt` wording. Non-integers in `--font-color` or `--save-bg` similarly identify the flag and include `strconv.Atoi: parsing`. These parser failures are the main class of ordinary errors that use status 1 and may write the detailed usage to standard error.

## Spec 2

`-h` and `--help` exit successfully and produce exactly the following standard output, including indentation, deliberate whitespace-only separator lines, and one final newline. Standard error is empty. The phrase “Further configuration can be managed with flags” is intentional; help must not advertise configuration files or environment variables.

```text
This tool converts images into ascii art and prints them on the terminal.
Further configuration can be managed with flags.

Usage:
  ascii-image-converter [image paths/urls or piped stdin] [flags]

Flags:
  -C, --color             Display ascii art with original colors
                          If 24-bit colors aren't supported, uses 8-bit
                          (Inverts with --negative flag)
                          (Overrides --grayscale and --font-color flags)
                          
      --color-bg          If some color flag is passed, use that color
                          on character background instead of foreground
                          (Inverts with --negative flag)
                          (Only applicable for terminal display)
                          
  -d, --dimensions ints   Set width and height for ascii art in CHARACTER length
                          e.g. -d 60,30 (defaults to terminal height)
                          (Overrides --width and --height flags)
                          
  -W, --width int         Set width for ascii art in CHARACTER length
                          Height is kept to aspect ratio
                          e.g. -W 60
                          
  -H, --height int        Set height for ascii art in CHARACTER length
                          Width is kept to aspect ratio
                          e.g. -H 60
                          
  -m, --map string        Give custom ascii characters to map against
                          Ordered from darkest to lightest
                          e.g. -m " .-+#@" (Quotation marks excluded from map)
                          (Overrides --complex flag)
                          
  -b, --braille           Use braille characters instead of ascii
                          Terminal must support braille patterns properly
                          (Overrides --complex and --map flags)
                          
      --threshold int     Threshold for braille art
                          Value between 0-255 is accepted
                          e.g. --threshold 170
                          (Defaults to 128)
                          
      --dither            Apply dithering on image for braille
                          art conversion
                          (Only applicable with --braille flag)
                          (Negates --threshold flag)
                          
  -g, --grayscale         Display grayscale ascii art
                          (Inverts with --negative flag)
                          (Overrides --font-color flag)
                          
  -c, --complex           Display ascii characters in a larger range
                          May result in higher quality
                          
  -f, --full              Use largest dimensions for ascii art
                          that fill the terminal width
                          (Overrides --dimensions, --width and --height flags)
                          
  -n, --negative          Display ascii art in negative colors
                          
  -x, --flipX             Flip ascii art horizontally
                          
  -y, --flipY             Flip ascii art vertically
                          
  -s, --save-img string   Save ascii art as a .png file
                          Format: <image-name>-ascii-art.png
                          Image will be saved in passed path
                          (pass . for current directory)
                          
      --save-txt string   Save ascii art as a .txt file
                          Format: <image-name>-ascii-art.txt
                          File will be saved in passed path
                          (pass . for current directory)
                          
      --save-gif string   If input is a gif, save it as a .gif file
                          Format: <gif-name>-ascii-art.gif
                          Gif will be saved in passed path
                          (pass . for current directory)
                          
      --save-bg ints      Set background color for --save-img
                          and --save-gif flags
                          Pass an RGBA value
                          e.g. --save-bg 255,255,255,100
                          (Defaults to 0,0,0,100)
                          
      --font string       Set font for --save-img and --save-gif flags
                          Pass file path to font .ttf file
                          e.g. --font ./RobotoMono-Regular.ttf
                          (Defaults to Hack-Regular for ascii and
                           DejaVuSans-Oblique for braille)
                          
      --font-color ints   Set font color for terminal as well as
                          --save-img and --save-gif flags
                          Pass an RGB value
                          e.g. --font-color 0,0,0
                          (Defaults to 255,255,255)
                          
      --only-save         Don't print ascii art on terminal
                          if some saving flag is passed
                          
      --formats           Display supported input formats
                          
  -h, --help              Help for ascii-image-converter
                          
  -v, --version           Version for ascii-image-converter

Copyright © 2021 Zoraiz Hassan <hzoraiz8@gmail.com>
Distributed under the Apache License Version 2.0 (Apache-2.0)
For further details, visit https://github.com/TheZoraiz/ascii-image-converter
```

If a bad flag accompanies `--help`, parsing still fails rather than ignoring the bad flag; the combined output must contain `unknown flag`, `Usage:`, and `Flags:`. After `--`, a token such as `--help` is an input filename and therefore receives the normal file-open diagnostic rather than displaying help.

## Spec 3

`--version` (and `-v`) exits 0, writes a single nonempty line beginning with lowercase `v`, and writes no standard error; `v1.13.1\n` is the canonical value.

`--formats` takes precedence over the missing-input check, exits 0, and emits exactly:

```text
Supported input formats:

JPEG/JPG
PNG
WEBP
BMP
TIFF/TIF
GIF

```

## Spec 4

At least one explicit operand is required; merely having bytes available on stdin is not an input unless the operand `-` is present. With no operand, exit 0 and print exactly:

```text
Error: Need at least 1 input path/url or piped input
Use the -h flag for more info

```

`-` means read all binary data from stdin. It must be the sole input operand; mixing it with any other operand exits 0 and prints `Error: You cannot pass in piped input alongside other inputs` followed by a blank line. If `-` is used while stdin is a terminal/no pipe is connected, print `Error: there is no input being piped to stdin` followed by a blank line. Invalid piped bytes produce `Error: can't decode piped input: image: unknown format` followed by a blank line. PNG, JPEG, BMP, TIFF, WEBP, and GIF data can be supplied through stdin; detection is by content, not a filename.

For a piped static image, saved names use `piped-img`; for a piped GIF, they use `piped-gif`, followed by the normal `-ascii-art` suffix.

## Spec 5

Local operands may be relative paths, absolute paths, or symlinks. Open and decode the referenced bytes; static image format recognition is by content, so a valid PNG with a `.txt` name still converts. Support JPEG/JPG, PNG (including RGBA), BMP, WEBP, TIFF/TIF, and GIF. Large images, 1×1 images, one-pixel-wide/tall images, and extreme aspect ratios must downsample without artificial size limits.

A path beginning exactly with lowercase `http://` or `https://` is fetched. Before fetching, output `Fetching file from url...\r`; after the response body is read, output 26 spaces and `\r` to erase that text. Decode the body regardless of HTTP status. Thus an HTTP error page ultimately produces an image decode error, not a special status-code diagnostic. The basename of the URL supplies any saved filename.

A local open failure is reported as `Error: unable to open file: open PATH: REASON`; a local static decode failure is `Error: can't decode PATH: REASON`. Empty files, directories, text, and corrupt image data are handled this way. A directory operand specifically has the reason `image: unknown format`, not an operating-system “is a directory” read error. Corrupt PNG reasons use the lowercase vocabulary of the reference decoder: depending on the damage they contain `unexpected EOF`, `invalid`, or `unknown format`; do not replace those with a differently capitalized synonym from another decoder. For example, a PNG truncated just after the start of its IHDR chunk reports `unexpected EOF`, while a recognizable PNG with a damaged chunk checksum reports `png: invalid format: invalid checksum`. These conversion errors exit 0 and go to standard output.

Multiple static inputs are processed left-to-right with fresh decoding and resizing for each. Their rendered blocks directly follow one another, each terminated by one newline. A decode/open failure between valid inputs is printed with an additional blank line and processing continues to later inputs. Do not cache image dimensions or decoder state between operands.

## Spec 6

Apply semantic validation before opening any input. Semantic validation errors exit 0, go to standard output, end in a blank line, and stop the invocation. The messages and rules are:

- A nonempty custom map must contain at least two bytes: `Need at least 2 characters for --map flag` (not prefixed by `Error:`). An empty map means “use the default map.”
- `--dimensions` must parse as exactly two integers. Wrong arity prints `Error: requires 2 dimensions, got N`; either value below 1 prints `Error: invalid values for dimensions`.
- Negative width prints `Error: invalid value for width`; negative height similarly uses `height`.
- If both width and height are nonzero, print `Error: both --width and --height can't be set. Use --dimensions instead`.
- `--font-color` must have exactly three integers; otherwise print `Error: --font-color requires 3 values for RGB, got N`. Every channel must be in 0…255 inclusive, otherwise print the intentionally misspelled `Error: RBG values must be between 0 and 255`.
- `--save-bg` must have exactly four integers; otherwise print `Error: --save-bg requires 4 values for RGBA, got N`. Defaults are `0,0,0,100`. RGB is nominally 0…255 and opacity is 0…100. Preserve the legacy behavior: if any of the four values is negative, or any RGB is over 255, or opacity is over 100, print both `Error: RBG values must be between 0 and 255` and `Error: Opacity value must be between 0 and 100`, each on its own line, then one blank line.
- Threshold must be in 0…255 inclusive or print `Error: threshold must be between 0 and 255`. Preserve the command-line defaulting quirk: a parsed value of 0 is subsequently replaced by 128.
- `--dither` without `--braille` prints `Error: image dithering is only reserved for --braille flag`.
- `--only-save` without any of `--save-img`, `--save-txt`, or `--save-gif` prints `Error: you need to supply one of --save-img, --save-txt or --save-gif for using --only-save`.

Zero passed explicitly to `--width` or `--height` is indistinguishable from “not specified” in the legacy behavior and is not caught by semantic validation; the headless-terminal consequence is covered in Spec 20.

## Spec 7

Choose the static character-grid size from the decoded source size `(sourceWidth, sourceHeight)` and aspect ratio `a = sourceWidth/sourceHeight`. All conversions compensate for characters being about twice as tall as they are wide:

- `--dimensions width,height` sets those exact character counts and overrides a lone width or height setting.
- With width `W`, set character width to `W` and height to `floor(0.5 * floor(W/a))`; clamp a zero result to 1.
- With height `H`, set character height to `H` and width to `floor(2 * floor(H*a))`; clamp a zero result to 1.
- With neither explicit dimensions nor a nonzero width/height, use terminal size. Initially use height `terminalHeight-1`, width `floor(2 * floor(height*a))`; if this width is at least the terminal width, instead use width `terminalWidth-1` and height `floor(0.5 * floor(width/a))`.
- `--full` overrides all other sizing controls: width is `terminalWidth-1`, and height is `floor(0.5 * floor(width/a))`.

Integer conversions truncate toward zero. In normal ASCII mode, the selected values are both the resized pixel dimensions and final character-grid dimensions. In braille mode only, multiply the selected width by 2 and height by 4 before resizing; grouping those pixels into 2×4 cells restores the requested character dimensions.

## Spec 8

Resize the decoded image to the pixel dimensions from Spec 7 with separable three-lobed Lanczos resampling, horizontal then vertical when both axes change. This exact resampling matters for gradients, checkerboards, sharp shapes, and edge pixels.

For one destination axis of length `D` from a source length `S`, let `du=S/D`, `scale=max(du,1)`, `radius=ceil(3*scale)`, and destination sample center `fu=(v+0.5)*du-0.5`. Include source indices `u` from `max(0,ceil(fu-radius))` through `min(S-1,floor(fu+radius))`. Give each included sample weight

```text
L((u-fu)/scale), where
L(x) = sinc(x) * sinc(x/3) for |x| < 3, otherwise 0
sinc(0) = 1; sinc(x) = sin(pi*x)/(pi*x)
```

Normalize the weights to sum to one. Resample non-premultiplied RGBA by accumulating `channel * alpha * weight` and `alpha * weight`, dividing accumulated color by accumulated alpha when nonzero, and rounding `value+0.5` down to an integer, clamped to 0…255. Fully transparent results have zero color channels. This gives alpha-aware interpolation.

For each resized pixel, obtain 16-bit alpha-premultiplied `(r,g,b,a)` values, calculate 8-bit grayscale as

```text
gray = (19595*r + 38470*g + 7471*b + 32768) >> 24
```

and use that `gray` as character depth. Retain both the three equal grayscale channels and the alpha-premultiplied RGB channels, each reduced to 8 bits, for coloring/saving. This is the 0.299/0.587/0.114 luminance weighting: pure blue maps darker than pure red, and pure green maps brighter than both. Transparency therefore affects depth rather than being composited over white.

## Spec 9

Normal ASCII mode maps each 8-bit depth to a character. The default table, ordered darkest to lightest, is exactly:

```text
 .:-=+*#%@
```

`--complex` instead selects exactly this 70-character table (the first character is a space):

```text
 .'`^",:;Il!i><~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$
```

A nonempty `--map` replaces either built-in table. Preserve its order, spaces, tabs, punctuation, case, and duplicate characters; do not sort, trim, or deduplicate. `--map` overrides `--complex`, while `--braille` overrides both.

For a table with `N` indexed entries and depth `d`, choose index `floor((d/255)*N)`, except depth 255 explicitly chooses `N-1`. This means each nonfinal bin is half-open and pure white always reaches the last character. The empty map falls back to the built-in table.

Preserve the legacy Unicode-map indexing behavior used by the expected output: iterate the UTF-8 map by Unicode scalar values but use each scalar's starting byte offset as its key; use the number of scalars as `N`; an index with no such key contributes an empty string. Thus ordinary ASCII maps behave naturally, while a map such as `" ░▒▓█"` can yield omitted output positions. UTF-8 characters that are selected must be emitted intact.

## Spec 10

`--negative` reverses the selected ASCII mapping index: after calculating `i`, use `(N-1)-i`. It also inverts every color channel used for terminal or saved-image rendering as `255-channel`. It does not alter geometry. Consequently black maps to the table's final character, white maps to its first, and a gradient's character progression reverses. This applies equally to default, complex, and custom maps and combines with either or both flips.

## Spec 11

Apply geometric transforms after resizing and pixel extraction but before ASCII/braille character selection:

- `--flipX`/`-x` reverses every resized pixel row.
- `--flipY`/`-y` reverses the row order.
- When both are present, perform both, equivalent to a 180-degree rotation for the rectangular pixel grid.

Flips preserve the chosen output dimensions and work with explicit dimensions, aspect-ratio-derived dimensions, normal/complex/custom maps, negative and grayscale processing, and braille. In braille mode the resized dot-pixel grid is flipped before 2×4 cells are encoded; this correctly mirrors dot positions within edge cells rather than merely reversing already-encoded characters.

## Spec 12

`--braille` emits Unicode Braille Pattern characters, one for every 2 columns × 4 rows of the resized pixel grid. Start each cell at U+2800 and add the following bit when that position's character depth is active:

```text
row 0: left 0x01, right 0x08
row 1: left 0x02, right 0x10
row 2: left 0x04, right 0x20
row 3: left 0x40, right 0x80
```

Without `--negative`, a dot is active when `depth >= threshold`. With `--negative`, a dot is active when `depth <= threshold`; terminal/saved color is also inverted as in Spec 10. The default effective threshold is 128. U+2800, although visually blank, must be emitted as the three-byte UTF-8 braille blank rather than an ASCII space. Pure white normally becomes U+28FF and pure black normally becomes U+2800. The top-left dot pixel supplies the displayed/saved color for the whole braille cell.

Braille conversion works for all supported static formats, alpha images, tiny inputs, all sizing flags, flips, negative, grayscale/color, saving, and GIF frames.

## Spec 13

`--dither` is a braille-only preprocessing operation. First resize normally. Make a separate black/white Floyd–Steinberg-dithered copy and use only that copy's resulting black/white grayscale value as character depth; retain RGB and grayscale colors from the undithered resized image.

For deterministic dithering, scan every row left-to-right (not serpentine). Quantize in linear RGB to whichever of black `(0,0,0)` and white `(65535,65535,65535)` has the smaller squared Euclidean distance; ties choose black. Convert each 8-bit sRGB channel `q` through `v=q/255`, then `v/12.92` when `v<=0.04045`, otherwise `((v+0.055)/1.055)^2.4`, multiply by 65535, and round ties to even. Diffuse each linear-channel quantization error with weights 7/16 to `(x+1,y)`, 3/16 to `(x-1,y+1)`, 5/16 to `(x,y+1)`, and 1/16 to `(x+1,y+1)`, discarding out-of-bounds contributions; each updated value is ties-to-even rounded and clamped to 0…65535.

This operation must produce spatially varied braille patterns on gradients and the expected high-frequency patterns on checkerboards.

## Spec 14

Plain output has no ANSI escapes. `--color` colors each character from the resized original RGB value; `--grayscale` colors it with its three equal luminance channels; a nondefault `--font-color R,G,B` colors it with that fixed color. Precedence is `--color` over `--grayscale` and fixed font color, then `--grayscale` over fixed font color. `--color-bg` places whichever chosen color on the terminal background rather than foreground. `--negative` inverts original/grayscale colors, but fixed font color itself is not inverted.

Detect whether the output environment supports truecolor or 256 colors. In the headless captured-output environment, requesting `--color`, `--grayscale`, or a nondefault font color must fail conversion gracefully with status 0, no saved file, and this exact diagnostic line:

```text
Error: your terminal supports neither 24-bit nor 8-bit colors. Other coloring options aren't available
```

Apply the ordinary error framing from Spec 15: without `--only-save` the line is followed by an additional blank line; with `--only-save` it has just its terminating newline.

When `TERM=xterm-256color`, 256-color output is permitted. Each character is independently wrapped in an ANSI color introducer and `ESC[0m` reset; for example black foreground is `ESC[38;5;0mCHAR ESC[0m` (with no extra separator—the apparent space here is the character if `CHAR` is a space). Truecolor-capable terminals analogously use `38;2;R;G;Bm` or `48;2;R;G;Bm`; 256-color backgrounds use `48;5;Nm`. Saved TXT always strips/avoids all ANSI sequences. `--color-bg` affects terminal display only, not bitmap saves.

## Spec 15

For one successfully converted static image, join characters in each row with no separator and rows with `\n`, then append exactly one terminal newline. Do not trim leading/trailing spaces in rows. Standard error remains empty. Consecutive successful images are not separated by an extra blank row.

An ordinary per-image conversion error is printed as `Error: MESSAGE\n\n`, and processing continues with the next static operand. Semantic validation errors likewise use the blank line but abort before conversion. `--only-save` suppresses character art, not save confirmations or error diagnostics.

The process normally exits 0 even for semantic validation, open, decode, unsupported-terminal-color, invalid-font, and invalid-save-path errors. Parser errors exit 1. The explicitly documented legacy panics exit nonzero as described in Spec 20.

## Spec 16

`--save-txt DIRECTORY` writes the uncolored character grid to an existing directory. The filename is the source basename with its final extension removed, followed by `-ascii-art.txt`. For example, `photo.png` becomes `photo-ascii-art.txt`. A URL uses its URL basename; piped input uses the name from Spec 4. `.` means the process's current working directory. A trailing path separator is accepted without changing the result.

TXT rows are separated by `\n` with no final newline. Preserve every space, tab, UTF-8 character, line width, map choice, negative effect, flip, and dimensions. Never include ANSI sequences. Existing files are silently replaced, not appended.

If the directory does not exist, do not create it or the file. Report `Error: can't save file: save path DIRECTORY/ does not exist` and a blank line. When saving succeeds without `--only-save`, also print the normal terminal art but no “Saved” confirmation. With `--only-save`, suppress art and print `Saved FULL_PATH` followed by a newline for each saved file.

## Spec 17

`--save-img DIRECTORY` creates a valid, nonempty PNG named `<base>-ascii-art.png` in an existing directory; the naming, current-directory, URL/stdin, and overwrite rules match TXT. Its missing-directory diagnostic does not match TXT: do not create the directory or output file, and print `Error: can't save file: stat DIRECTORY/: no such file or directory` followed by a blank line. The process exits 0. It may be combined with `--save-txt`, including distinct destination directories; both files must be produced. Static PNG saving occurs before TXT saving, so with `--only-save` its confirmation precedes the TXT confirmation.

Render the exact converted characters, using original per-character colors for `--color`, luminance colors for `--grayscale`, and otherwise `--font-color` (default white). Use a monospaced ASCII-capable default font and a braille-capable default font in braille mode. A deterministic compatible layout is 14 pixels per character horizontally, 28 pixels per row vertically, plus 5 pixels of padding on every side: output dimensions are `(14*columns+10, 28*rows+10)`. Default background is black and fully opaque. `--save-bg R,G,B,opacity` supplies an RGBA color whose opacity percentage is converted to `A = floor(255*opacity/100)`, then drawn through an 8-bit alpha-premultiplied canvas. Consequently the RGB channels can be quantized when `A` is not 255, and at `A = 0` the saved transparent pixel has zero RGB channels regardless of the supplied RGB. More precisely, for each background channel `C`, the premultiplied byte is `P = floor(C*A/255)`; when the PNG is decoded back to straight RGBA, the channel is `0` if `A = 0`, otherwise `floor((P*65535/A)/256)`. Thus `--save-bg 1,2,3,0` yields background RGBA `(0,0,0,0)`, while `--save-bg 11,22,33,50` yields `(10,20,32,127)`. At zero opacity all RGB triples collapse to the same transparent-black background and PNG bytes; for example `1,2,3,0` and `4,5,6,0` produce identical files. At full opacity, `1,2,3,100` and `4,5,6,100` retain their stated RGBA values and produce different PNG bytes. Partial and zero opacity remain valid.

If `--font PATH` is present for a local input, validation follows this order: first open and read the input bytes, then read and parse the font as TrueType, then decode the input image bytes. Therefore a nonexistent input path wins over either a missing or malformed font and produces the ordinary `Error: unable to open file: open PATH: no such file or directory`; once the input has been read successfully, a font error wins over an image decode error. Missing font files produce `Error: unable to open font file: ...`; invalid contents produce `Error: unable to parse font file: freetype: invalid TrueType format`. These are status-0 standard-output errors and no output image is made.

## Spec 18

An input is routed through animated-GIF handling when its local/URL path extension is exactly lowercase `.gif`, or when stdin content detection identifies GIF. Before conversion and unless `--only-save` is present, reject more than one `.gif` operand with exactly:

```text
Error: There are multiple GIFs supplied
Due to the potential looping nature of GIFs, only one GIF per command is supported

```

Similarly reject a `.gif` operand mixed with any non-GIF operand with:

```text
Error: There are other inputs along with GIFs
Due to the potential looping nature of GIFs, non-GIFs must not be supplied alongside

```

Decode all GIF frames. Invalid or truncated data produces `Error: can't decode PATH: REASON`, with recognizable reasons such as `gif: can't recognize format` or `gif: not enough image data`. All frames must have the same rectangle dimensions as the first. If one is a smaller positioned subimage, print one error line containing `PATH contains subimages smaller than default width and height`, a blank line, then `Process aborted because ascii-image-converter doesn't support subimage placement and transparency in GIFs`, followed by a blank line, and exit 0.

Apply the same resizing, maps, complex/braille/dither, negative, color, and flips independently to every frame. Keep frame order and each frame's delay.

## Spec 19

GIF conversion reports progress on standard output. Begin with `Generating ascii art... 0%\r`. After each of `N` frames, report `Generating ascii art... floor(completed/N*100)%\r`; therefore two frames include 50 and 100, five include 20/40/60/80/100, and ten include every 10-percent increment. Completion order may be parallel internally, but the observed suite must see all applicable increments. Clear that status using exactly 30 spaces followed by `\r`.

With `--save-gif DIRECTORY`, validate the destination after generation. A missing directory is not created and produces `Error: can't save file: stat DIRECTORY/: no such file or directory` followed by a blank line and status 0; the generation progress and its 30-space clearing sequence precede this error, but no `Saving gif...` progress is emitted. For a valid destination, report `Saving gif... 0%\r`, the same completed-frame percentages using `Saving gif... `, then exactly 21 spaces and `\r`. Create a valid nonempty animated GIF named `<base>-ascii-art.gif`, print `Saved FULL_PATH\n`, preserve the source frame count, order, delays, and loop metadata, and ensure every saved frame has one common size. When the directory operand is literally `.`, preserve it in this confirmation: for source `single_frame.gif`, print `Saved ./single_frame-ascii-art.gif\n`, not the normalized spelling without `./`. The file must be genuinely animated when the source is. Use a 256-color palette and Floyd–Steinberg palette reduction; files for the tested multi-frame inputs must contain substantive rendered content (not placeholder/empty frames).

For compatible rendering dimensions, let source frame size be `(x,y)` and character grid size `(cw,ch)`. If `cw > 2*ch`, use vertical step `y/ch`, horizontal step half of that, and set the rendered width to `floor(horizontalStep*cw)`. Otherwise use horizontal step `x/cw`, vertical step twice that, and set rendered height to `floor(verticalStep*ch)`. Add 10 pixels to both dimensions for padding. Render characters with the same color/font/background choices as PNG; GIF background alpha is not retained.

`--only-save --save-gif` returns after saving. Without `--only-save`, animate in the terminal by clearing the screen, printing each frame, and waiting its GIF delay in hundredths of a second. A GIF whose loop count is zero loops indefinitely. Absence of a GIF loop extension is treated the same as loop count zero, rather than as one playback: even a one-frame GIF with no loop metadata continues printing that frame indefinitely. Either kind of single-frame infinite GIF must still be running after one second.

## Spec 20

Preserve the tested headless-terminal failure quirks. In a subprocess with no usable terminal dimensions, default sizing can yield an empty resized image. Explicit `-W 0`, explicit `-H 0`, and `--braille --full` on an otherwise valid image must terminate via an index-out-of-range style runtime panic rather than a friendly semantic error. The process status is 2 for the zero-width/zero-height cases, and standard error contains `panic: runtime error: index out of range [0] with length 0`; the braille/full case must at least be nonzero and contain that same phrase.

Likewise, converting a valid image without any size option in that headless environment may panic before producing buffered standard output. This includes a multi-input invocation whose first valid image has no explicit sizing: it exits 2, standard output is empty, and standard error contains `panic: runtime error: index out of range`. These quirks do not apply when `-W`, `-H`, or `-d` provides a usable positive size.

Ordinary conversions of a 5000×5000 input down to width 100 must complete within roughly ten seconds, and all ordinary CLI operations must avoid hangs. The intentional exception is playback of an infinitely looping GIF as described in Spec 19.
