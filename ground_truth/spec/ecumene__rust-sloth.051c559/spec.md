# Sloth executable specification

The required artifact is one executable file named `executable`. It is a small CPU-based 3D rasterizer with a terminal viewer, a one-frame image mode, and a JavaScript animation export. All text is UTF-8. Unless an error is explicitly described otherwise, successful commands exit with status 0 and write nothing to standard error.

The rendering rules below are deliberately exact. Frame output is byte-sensitive, including spaces, escape sequences, newlines, floating-point behavior, and historical command-line quirks.

## Spec 1

The command-line shape is:

```text
executable [root flags/options] <input filename(s)>... [image [image flags/options]]
executable help [image]
```

At least one root positional input is required unless help or version output is requested. With no `image` subcommand, the input is opened in an interactive terminal viewer. With `image`, a finite render is written to standard output.

The root flags/options are `-h`/`--help`, `-V`/`--version`, `-b`, `-x`/`--yaw <x>`, `-y`/`--pitch <y>`, and `-z`/`--roll <z>`. The `image` parser independently defines `--help`, `-V`/`--version`, `-b`, the same three rotation options, required `-w <width>`, optional `-h <height>`, and optional `-j`/`--webify <frame count>`.

Root options belong before `image`; image options belong after it. In particular, root `-h` means help while image `-h` means height. `-w` and `-j` are invalid without `image`, and positional filenames are not accepted after `image`.

## Spec 2

`executable --help` and `executable -h` print the following root help to standard output. The final displayed line is followed by `\n`, and standard error is empty.

```text
Sloth 0.1
Mitchell Hynes. <mshynes@mun.ca>
A toy for rendering 3D objects in the command line

USAGE:
    executable [FLAGS] [OPTIONS] <input filename(s)>... [SUBCOMMAND]

FLAGS:
    -h, --help       Prints help information
    -b               Flags the rasterizer to render without color
    -V, --version    Prints version information

OPTIONS:
    -x, --yaw <x>      Sets the object's static X rotation (in radians)
    -y, --pitch <y>    Sets the object's static Y rotation (in radians)
    -z, --roll <z>     Sets the object's static Z rotation (in radians)

ARGS:
    <input filename(s)>...    Sets the input file to render

SUBCOMMANDS:
    help     Prints this message or the help of the given subcommand(s)
    image    Generates a colorless terminal output as lines of text
```

Help takes precedence over later unrecognized arguments: for example, `--help foo` still succeeds with root help and empty standard error. `executable help` routes to root help. `executable help image` routes to image help content.

## Spec 3

`executable image --help` prints exactly the following bytes to standard output, including the final newline, and no standard error:

```text
executable-image 
Mitchell Hynes <mitchell.hynes@ecumene.xyz>
Generates a colorless terminal output as lines of text

USAGE:
    executable <input filename(s)>... image [FLAGS] [OPTIONS] -w <width>

FLAGS:
        --help       Prints help information
    -b               Flags the rasterizer to render without color
    -V, --version    Prints version information

OPTIONS:
    -j, --webify <frame count>    Generates a portable JS based render of your object for the web
    -h <height>                   Sets the height of the image to generate
    -w <width>                    Sets the width of the image to generate
    -x, --yaw <x>                 Sets the object's static X rotation (in radians)
    -y, --pitch <y>               Sets the object's static Y rotation (in radians)
    -z, --roll <z>                Sets the object's static Z rotation (in radians)
```

`help image` must expose the same description, flags, and options; its automatically generated usage synopsis may reflect the `help image` route. Image help differs from root help.

## Spec 4

`--version` and `-V` at root print exactly `Sloth 0.1\n` and succeed. Ordinary parser errors use a clap-2-style diagnostic on standard error, start with `error:`, contain an uppercase `USAGE:` block, end with `For more information try --help`, and return nonzero.

No arguments report that required arguments were not provided and name `<input filename(s)>...`. Unknown flags report `Found argument '<token>' which wasn't expected, or isn't valid in this context`.

The missing-width usage synopsis depends on how image mode was reached. When a root input was supplied and no webify option was selected, missing image width reports:

```text
error: The following required arguments were not provided:
    -w <width>

USAGE:
    executable image [FLAGS] [OPTIONS] -w <width>

For more information try --help
```

By contrast, `executable image`, with no root input, exits with status 1, leaves standard output empty, and includes the required root positional in the otherwise identical usage line:

```text
error: The following required arguments were not provided:
    -w <width>

USAGE:
    executable <input filename(s)>... image [FLAGS] [OPTIONS] -w <width>

For more information try --help
```

For the missing-width and missing-webify-value cases, once `-j`/`--webify` has been selected, the usage synopsis expands that option instead of showing `[FLAGS] [OPTIONS]`. Thus `<input> image -j 5` without a width exits with status 1, leaves standard output empty, and reports:

```text
error: The following required arguments were not provided:
    -w <width>

USAGE:
    executable image --webify <frame count> -w <width>

For more information try --help
```

A missing value for an option says `The argument '<long option and value name>' requires a value but none was supplied`; thus bare `-j` names `--webify <frame count>` and bare image `-y` names `--pitch <y>`. In particular, bare `-j` after a valid root input and image width exits with status 1, leaves standard output empty, and reports exactly (with a final newline):

```text
error: The argument '--webify <frame count>' requires a value but none was supplied

USAGE:
    executable image --webify <frame count> -w <width>

For more information try --help
```

A negative numeric token supplied separately, such as `-w -1` or `-z -2`, is parsed as an unexpected flag and rejected. An attached value such as `-x=-1.5708` or `--yaw=-1.57` is accepted. `--` stops flag parsing; a following `image` is diagnosed as an unrecognized subcommand, whereas `<valid-input> --` enters the default viewer.

For compatibility with short-option parsing, `-bx` is treated as a short-option cluster involving `-b` and `-x`, not as a distinct option. In the sequence `<file> -bx image -w 10`, parsing eventually rejects `-w` as unexpected.

## Spec 5

Width, height, and frame count use unsigned base-10 integer parsing. Width is mandatory in image mode; omitted height defaults exactly to width. Width and height must fit the platform `usize` range. Nonempty invalid values—including alphabetic text, decimal notation, and exponent notation—produce status 1 with this exact standard-error line:

```text
Error: ParseIntError { kind: InvalidDigit }
```

An explicitly supplied empty string instead uses `Error: ParseIntError { kind: Empty }\n`.

Zero is accepted by the unsigned dimension parser. With width `0` and no explicit height, height also defaults to `0`; rendering either an empty OBJ or an OBJ containing a triangle then succeeds with status 0 and writes no bytes to either standard output or standard error. Values from 1 through at least 100 in either dimension are supported, including 1x1, 1x100, 100x1, 100x80, and 100x100.

Rotations use IEEE-754 single-precision (`f32`) parsing in radians. Invalid nonnumeric rotation text produces status 1 and exactly:

```text
Error: ParseFloatError { kind: Invalid }
```

Large and tiny finite rotations are accepted without explicit normalization; the trigonometric functions naturally make them periodic.

## Spec 6

The root positional is declared as repeatable, but loading has an intentional legacy rule: consult only the first positional value returned by the parser, split that one string on literal ASCII space characters, and load every resulting slice in order. Thus one quoted argument containing `a.obj b.stl` loads both files, duplicates are retained, and heterogeneous files are allowed. If filenames are instead supplied as separate argv positionals, later positional values are syntactically accepted but do not contribute meshes. This behavior must not be replaced with shell parsing, general whitespace splitting, globbing, or filename deduplication.

Each source file may yield multiple meshes; append all meshes from each loaded slice to one queue. Draw queue order is file order, then mesh/model order, then triangle order. A load failure in any consulted slice aborts the entire invocation rather than rendering a partial queue.

An unrecognized word where a subcommand might otherwise appear is treated as another input positional, not as a custom subcommand. Consequently, `<valid-file> fakesubcommand` still attempts interactive mode using the first positional, while a lone extensionless word reaches file loading and fails there.

## Spec 7

Choose a loader solely from the filename extension, case-insensitively. Only `obj` and `stl` are supported. Do not infer format from contents. A missing extension, unknown extension, empty filename, directory, unreadable path, or parse failure is fatal.

Except for the missing-material-library case below, file-loading failures intentionally have panic-style behavior: exit status 101 and write a diagnostic to standard error beginning with a blank line, then a line of the form

```text
thread 'main' (<decimal process/thread id>) panicked at src/inputs.rs:<error location>:
called `Result::unwrap()` on an `Err` value: "filename: [<path>] couldn't load, <category>. <detail>"
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

The categories are `couldn't determine filename extension`, `couldn't parse filename extension`, `unknown filename extension`, `tobj couldnt load/parse OBJ`, `STL load failed`, and `stl_io couldnt parse STL`. Missing OBJ detail is `open file failed`; invalid OBJ vertex numeric data includes `position parse error`; empty/malformed STL detail is `failed to fill whole buffer`. A literal tab in the supplied path is rendered in the diagnostic as the two ASCII characters `\t`, not as a literal tab. The tab remains part of the one filename and is not a separator.

A missing material library referenced by an otherwise readable OBJ is fatal, but it follows a distinct panic path. It exits with status 101, writes nothing to standard output, and writes this form to standard error (including the initial blank line and final newline):

```text

thread 'main' (<decimal process/thread id>) panicked at src/inputs.rs:<error location>:
Expected to have materials.: OpenFileFailed
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

This diagnostic does not contain ``called `Result::unwrap()` on an `Err` value:``, the OBJ filename/path, or the `tobj couldnt load/parse OBJ` category.

## Spec 8

OBJ loading is equivalent to a single-index, triangulating Wavefront loader with these options: triangulate polygon faces into indexed triangles, unify position/normal/texture indices into one index stream, ignore point and line primitives, preserve object/model order and material association, and load `mtllib` paths relative to the OBJ directory. Recognize at least comments, `v`, `vn`, `vt`, `f`, `o`, `g`, `s`, `mtllib`, and `usemtl`; face references may use `v`, `v/vt`, `v//vn`, or `v/vt/vn` forms. A triangle `(a,b,c)` remains in that order; a quad `(a,b,c,d)` becomes `(a,b,c),(a,c,d)`; a longer polygon `(a,b,c,d,...)` becomes the ordered fan `(a,b,c),(a,c,d),...`. Emit a new mesh batch when a material change occurs after accumulated faces, because each batch has one material id. Triangle order affects the depth buffer and must be preserved.

For each indexed triangle, read three XYZ positions as `f32` and turn each into the homogeneous column vector `(x,y,z,1)`. Normals from the file are not used for lighting; face normals are recomputed. Initialize each OBJ mesh bounding box with both minimum and maximum equal to `(0,0,0,1)`, then componentwise expand it with every triangle. Therefore the origin is always included in an OBJ mesh's bounds even if all vertices lie on one side of it.

An empty OBJ is valid and yields a background-only image. An OBJ with no `mtllib` is valid and uses `(1,1,1)` as the triangle RGB value. Malformed numeric vertex data must fail as described above.

## Spec 9

Parse referenced MTL files in declaration order and associate `usemtl` faces with the corresponding material. Only the diffuse `Kd r g b` property affects rendering; ambient `Ka`, specular `Ks`, emission, opacity, illumination model, textures, and material names do not alter shading except that names select the material.

Convert each diffuse channel to a byte with single-precision multiplication followed by truncating, saturating conversion: `u8(Kd * 255.0)`. Do not round or gamma-correct. Examples are `0.5 -> 127`, `0.999 -> 254`, and cube diffuse `(0.640000,0.102425,0.091882) -> (163,26,23)`. Preserve material ordering rather than sorting or deduplicating it.

If per-vertex RGB values are present on OBJ `v` records and a material collection was loaded, each triangle's color is the converted RGB of its first indexed vertex, overriding `Kd`; colors are flat per triangle and are not interpolated. If there is no material collection, retain the default `(1,1,1)` even if vertex-color storage exists. Color never changes as a result of lighting or rotation.

## Spec 10

Support both binary and ASCII STL inputs with standard facet/vertex parsing. Convert each facet to one triangle of homogeneous `f32` positions and ignore stored facet normals and attributes. Every STL triangle has the fixed color `(255,255,0)`.

Initialize an STL mesh bounding-box minimum to `(f32::MAX,f32::MAX,f32::MAX,1)` and maximum to `(f32::MIN,f32::MIN,f32::MIN,1)`, then componentwise expand over facets. (`f32::MIN` here means the most negative finite single-precision value.) Preserve facet order. Empty or truncated STL data is an error, not an empty render.

## Spec 11

All geometry, transformation, normal, edge, depth, and scale calculations use IEEE-754 `f32` with single-precision rounding at each operation. Use four-component column vectors and left-multiply them by 4x4 matrices.

Let parsed image-local rotations be `(x,y,z)`, defaulting independently to zero. Before rendering, add single-precision `PI` (approximately `3.1415927`) to `y`; this mandatory half-turn is part of the default view. Let `sr,cr = sin(x),cos(x)`, `sp,cp = sin(y+PI),cos(y+PI)`, and `sy,cy = sin(z),cos(z)`, all evaluated as `f32`. The upper-left 3x3 part of the homogeneous rotation matrix is exactly:

```text
[ cy*cp,  cy*sp*sr - sy*cr,  cy*sp*cr + sy*sr ]
[ sy*cp,  sy*sp*sr + cy*cr,  sy*sp*cr - cy*sr ]
[   -sp,                cp*sr,                cp*cr ]
```

The last column and last row are `(0,0,0,1)` in the usual homogeneous layout. Equivalently, form the roll-pitch-yaw rotation

```text
R = Rz(z) * Ry(y + PI) * Rx(x)
```

for column vectors, using single-precision sine and cosine. Apply this same `R` to every triangle in every queued mesh. In image mode, rotation options parsed at image scope replace the root rotation tuple, so root rotations are accepted but reset to image defaults if no corresponding option follows `image`. In interactive mode there is no replacement and root rotations initialize the viewer.

## Spec 12

For an image of requested width `W` and height `H`, determine a single scene scale as follows. Start `maximum = 0`. For every queued mesh, update it with `max(maximum, bbox.max.x, bbox.max.y, bbox.max.z)`. Then compute, in `f32`:

```text
scale = min(H, W / 2) / maximum / 2
```

Do not use absolute minima, bounding-box centers, or per-model scaling. The screen transform is:

```text
[ scale,      0,     0, W/4 ]
[     0, -scale,     0, H/2 ]
[     0,      0, scale,   0 ]
[     0,      0,     0,   1 ]
```

where divisions and conversions are `f32`. The complete vertex transform is `screen_transform * R * vertex`. With several loaded meshes, the largest positive maximum determines the shared scale and all meshes remain superimposed at their original origins; there is no layout translation between models.

## Spec 13

In image mode allocate a linear frame buffer of exactly `W*H + H` cells, each initially `(character=' ', rgb=(0,0,0))`. Allocate a depth buffer of `W*H` entries initialized to `f32::MAX`. The extra `H` frame cells and the unusual indexing below are required compatibility behavior, not padding to discard.

For a transformed triangle with vertices `v1,v2,v3`, compute its componentwise AABB. Define:

```text
min_x = usize(ceil(max(aabb.min.x, 1.0)))
min_y = usize(ceil(max(aabb.min.y, 1.0)))
max_x = usize(ceil(min(aabb.max.x * 2.0, W - 1)))
max_y = usize(ceil(min(aabb.max.y,       H - 1)))
```

Loop over half-open integer ranges `y in min_y..max_y`, then `x in min_x..max_x`. The `x*2` write mapping is the terminal-cell aspect correction; do not instead sample every screen column directly.

After processing each scan row of each triangle, if in image mode set frame-buffer cell `y*W + 1` to `('\n',(0,0,0))`. This happens for every iterated triangle row even if no sample passed the inside test. Rows never visited by any triangle retain spaces, so the number and location of literal newlines need not equal `H`. Do not reshape the linear buffer or append conventional row separators.

## Spec 14

Use the signed 2D edge function

```text
orient(a,b,c) = (b.x-a.x)*(c.y-a.y) - (b.y-a.y)*(c.x-a.x)
```

Set `area_recip = 1 / orient(v1,v2,v3)`. At integer sample point `p=(x,y,0,0)`, compute:

```text
w0 = orient(v2,v3,p)
w1 = orient(v3,v1,p)
w2 = orient(v1,v2,p)
```

Accept a sample only if all three weights are `>= 0`; this also supplies winding-based back-face rejection. Recompute the triangle unit normal from `cross(v2-v1, v3-v1)` in XYZ (homogeneous component zero). Compute:

```text
shade = normal.z * area_recip * (w0+w1+w2)
depth = v1.z + area_recip * (w1*(v2.z-v1.z) + w2*(v3.z-v1.z))
id = y*W + x*2
```

Write only when `depth < depth_buffer[id]`; equal depth does not replace the existing sample. On a write, put the identical `(shade-character, triangle-rgb)` in frame cells `id` and `id+1`, but update only `depth_buffer[id]`. Process degenerate triangles without a special drawing fallback; their invalid/zero-area math results in no visible covered pixels under these comparisons.

## Spec 15

Map `shade` to an ASCII character using these inclusive upper thresholds, tested in order:

```text
shade <= .20  '.'
shade <= .30  ':'
shade <= .40  '-'
shade <= .50  '='
shade <= .60  '+'
shade <= .70  '*'
shade <= .80  '#'
shade <= .90  '%'
shade <= 1.0  '@'
otherwise     ' '
```

This is flat face shading based only on transformed normal Z. Negative shades map to `.`, and there is no light vector, perspective division, clipping plane, color modulation, or interpolation.

## Spec 16

Normal colored image output serializes every frame-buffer cell in linear order, including inserted newline cells and all extra `H` cells. A cell `(ch,(r,g,b))` is exactly:

```text
ESC[48;2;25;25;25mESC[38;2;<r>;<g>;<b>m<ch>ESC[49mESC[39m
```

Here `ESC` is byte `0x1b`; the displayed line break in the template is not appended—the only character at that position is `ch`, which may itself be `\n`. Thus each cell uses truecolor foreground, constant dark-gray background `(25,25,25)`, then background reset followed by foreground reset. Do not emit 256-color escapes, combine adjacent runs, omit styling from black spaces/newlines, or add a final newline. For example, an empty 2x1 render is exactly three styled black-space cells.

Root `-b` selects plain mode: concatenate only the character from every frame cell and then append one `\n`, with no ANSI sequences. There is an intentional scope quirk: an `-b` written after `image` is accepted by the image parser but is ignored by output selection, because output selection consults only root `-b`. Such an invocation remains byte-for-byte colored. Root `-b` before `image` selects plain output.

## Spec 17

`-j N` or `--webify N` after `image` produces JavaScript/HTML instead of ANSI output. Emit `let frames = [\n` first. Each frame begins with `` `\n ``. In colored mode, serialize every linear cell as:

```text
<span style="color:rgb(<r>,<g>,<b>)"><ch>
```

Again, the template has no appended newline; `ch` is the sole character after `>`. Intentionally emit no `</span>` tags, no ANSI escapes, no HTML escaping, and no background style. After a nonfinal frame emit ```,\n``; after the final frame emit ```];\n``. Since the oversized buffer ends in background spaces, a normal frame has a literal space immediately before its closing backtick.

For positive `N`, produce exactly `N` frames. The first uses the static image rotation described above. Set the per-frame Y increment to single-precision `2*PI/N`; after flushing a frame, add it to Y before rendering the next, so the animation turns around Y while retaining static X and Z. Frame buffers and depth buffers are cleared between frames. A frame count of zero is a compatibility edge case: succeed and generate exactly one frame rather than no output or an infinite loop. Invalid text is the `ParseIntError` from Spec 5. More frames must produce correspondingly more output, and 50 frames at width 30 must complete within ordinary test timeouts.

As with normal images, image-local `-b` is ignored and therefore still produces RGB spans. If root `-b` selected plain mode, the JavaScript wrapper remains but each frame body uses the raw character buffer plus its plain-mode newline instead of spans.

## Spec 18

Without `image`, run continuously in a real TTY. Obtain the current terminal column/row size `(W,H)`, use a frame buffer of `W*H` cells (no extra `H` cells), a depth buffer of `W*H`, and the same shared scale, transforms, rasterizer, shader, and color encoding. In this mode do not inject frame-buffer newline cells. Before drawing, enable terminal raw mode and hide the cursor. Before every flush, move the cursor to `(0,0)` so terminal wrapping displays the linear cells as a screen. Recompute/clear/redraw repeatedly.

The default animation speed is 1.0 radian per second around Y. Initialize rotations from root options, including the mandatory added `PI`, render a frame, measure elapsed real time for that iteration, then add `elapsed_seconds * 1.0` to Y. The display must update fast enough that snapshots about one second apart differ and valid cube, STL cube, Pikachu, and more complex OBJ models visibly contain substantial runs of the shader characters.

Only lowercase `q` without needing Enter and Ctrl+C are commands. Either restores the cursor, disables raw mode, and exits cleanly with status 0 while leaving the last rendered frame visible. Consume and ignore all other keyboard events—including arrows, function keys, ordinary letters/digits, Enter, Escape, Tab, Backspace, Space, and non-quit control combinations—without pausing, altering state, crashing, or stopping animation. A `q` embedded in a rapid input sequence must still quit.

If interactive mode is invoked without a terminal (for example with stdout/stderr captured by a subprocess), raw-mode initialization fails nonzero and standard error contains `Error:` and `Inappropriate ioctl for device`. Loading and argument validation happen before terminal initialization, so their diagnostics take precedence.
