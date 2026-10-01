# Clarified specification for `executable`

The required artifact is a directly runnable file named exactly `executable`. It implements the Pastel 0.11.0 command-line interface described below. All text is UTF-8. `ESC` below means the single byte `0x1b`, not the three printable letters.

## Spec 1

Invocation is `executable [GLOBAL OPTIONS] <COMMAND> [COMMAND OPTIONS/ARGUMENTS]`. Successful ordinary commands return status 0. Command-line syntax/enum errors return 2; operational errors found after parsing return 1. Normal results go to stdout, diagnostics go to stderr, and successful non-paint result records normally end in `\n`.

The commands are `color`, `colorblind`, `colorcheck`, `complement`, `darken`, `desaturate`, `distinct`, `format`, `gradient`, `gray`, `lighten`, `list`, `mix`, `paint`, `pick`, `random`, `rotate`, `saturate`, `set`, `sort-by`, `textcolor`, `to-gray`, and `help`. Global options are `-m, --color-mode MODE`, `-f, --force-color`, `--color-picker PICKER`, `-h, --help`, and `-V, --version`. Global options are accepted only before the command. `--mode` is not an alias for `--color-mode`. Command-specific options may occur before or after that command's positional arguments unless `--` has ended option parsing.

The program must comfortably process at least 500 stdin colors, 100 CLI colors, and a 1,000-element gradient within five seconds.

## Spec 2

`--version` and `-V` print exactly `pastel 0.11.0\n` to stdout and succeed. `--help` and `-h` succeed and print a main help page headed `A command-line tool to generate, analyze, convert and manipulate colors`, containing `Usage: executable [OPTIONS] <COMMAND>`, `Commands:`, every command from Spec 1 with a short description, `Options:`, `--color-picker`, `--force-color`, `--color-mode`, `--help`, and `--version`. Under `Commands:`, put one command on each line with two leading spaces and at least two spaces between its name and description; finish that block with a blank line before `Options:`.

The color-picker enum is `gpick`, `xcolor`, `wcolor`, `grabc`, `colorpicker`, `chameleon`, `kcolorchooser`, `zenity`, `yad`, `hyprpicker`, or `gdbus`. The color-mode enum is `24bit`, `8bit`, `off`, or `auto` (default `auto`). Invalid enum values are command-line errors which mention `invalid value`, the option/argument, and `possible values`.

With no command, print the main usage/help and return 2. `help` alone shows main help; `help COMMAND` shows that command's long help. `COMMAND --help` is long help and differs from main help; it contains `Usage: executable COMMAND`. `COMMAND -h` is a shorter summary (and for `color` must be shorter than long help and contain `Print help`). Help goes only to stdout and succeeds. At minimum, `format -h` contains `Convert a color to the given format` and `[possible values:`.

## Spec 3

Unknown commands use clap-style diagnostics. In particular, `executable bogus` returns 2, writes nothing to stdout, and writes exactly:

```text
error: unrecognized subcommand 'bogus'

Usage: executable [OPTIONS] <COMMAND>

For more information, try '--help'.
```

Substituting another unknown token produces the analogous message. Unexpected options, repeated single-use options, and missing required positionals also return 2, go to stderr, show a useful `Usage:` line, and end with the help suggestion. Missing option values likewise return 2 on stderr and end with the help suggestion, but omit the `Usage:` line. Examples of required wording include `unexpected argument`, `a value is required`, `required arguments were not provided`, and `cannot be used multiple times`.

Diagnostics for `random` options use the canonical long option even when the user supplied a short alias. Thus both `random --number` and `random -n` write exactly:

```text
error: a value is required for '--number <count>' but none was supplied

For more information, try '--help'.
```

Repeating `-n` names `'--number <count>'`, and repeating `-s` names `'--strategy <strategy>'`, followed by `cannot be used multiple times`. An invalid format type identifies its positional as `'[type]'`; for example, `format bogus` begins `error: invalid value 'bogus' for '[type]'` and then lists the possible values. When an unrecognized long option has an attached value, the quoted unexpected argument omits that value: `--mode=24bit paint red hello` begins `error: unexpected argument '--mode' found`.

A leading negative positional such as `lighten -0.5 red` is parsed as an option and errors; `lighten -- -0.5 red` accepts it. `random --number -1` returns 2 and begins `error: unexpected argument '-1' found`. `rotate -10` likewise reports the truncated short-option token `error: unexpected argument '-1' found`, then includes exactly `  tip: to pass '-1' as a value, use '-- -1'` before its usage line.

## Spec 4

A color argument accepts these syntaxes:

- A named CSS/X11 color, matched as a complete name (never a partial match).
- Hex RGB/RGBA with optional `#`: exactly 3, 4, 6, or 8 hexadecimal digits. Short digits are doubled. Hex input is case-insensitive.
- `rgb(r,g,b)`, `rgba(r,g,b,a)`, or bare `r,g,b`. RGB items may be decimal numbers or percentages. Space-separated `rgb(255 0 0)` is also valid. The function names `rgb`, `rgba`, `hsl`, `hsla`, `hsv`, and `hsva` are lowercase and therefore `RGB(...)` is invalid.
- `hsl(h,s%,l%)`, `hsla(h,s%,l%,a)`, `hsv(h,s%,v%)`, and `hsva(h,s%,v%,a)`. Alpha may be a 0..1 number or percentage.
- `gray(x)` where a plain number is interpreted on the 0..1 scale (and clamped) or a percentage is interpreted on the 0..100% scale. It creates equal, nearest-integer sRGB channels; thus `gray(0.5)` becomes RGB 128 and displays as HSL lightness 50.2%, while even an out-of-range form such as `gray(50)` is accepted and clamps. The standalone `gray` command has different direct-HSL behavior in Spec 15.
- CIELAB `lab(L,a,b)`, case-insensitive `LAB`, or `CIELab`/`cielab`; and CIELCh `lch(L,C,h)` or case-insensitive `CIELCh`.
- `OkLab(L,a,b)` and `OkLch(L,C,h)`.

Whitespace around comma-separated components is ignored. HSL/HSV hue accepts bare degrees, `deg`, the degree sign `°`, radians (`rad`), gradians (`grad`), and turns (`turn`), and wraps cyclically. Saturation/lightness/value and alpha are clamped to their legal ranges. Numeric RGB components are rounded to the nearest channel and clamped to 0..255; e.g. all-negative RGB becomes black and `rgb(300,400,500)` becomes white. Malformed arity, separators, missing required percent signs, nonnumeric fields, wrong hex lengths, and unknown names are invalid.

Normative parses include:

```text
lightslategray = #778899 = 778899 = 789
              = rgb(119, 136, 153) = 119,136,153
              = hsl(210, 14.3%, 53.3%)
#FF5733       -> hsl(11,100.0%,60.0%)
F57           -> hsl(348,100.0%,66.7%)
#FF5733AA     -> hsla(11,100.0%,60.0%,0.667)
F57A          -> hsla(348,100.0%,66.7%,0.667)
rgb(50%,60%,70%) -> hsl(211,25.1%,60.2%)
hsv(210,22.2%,60.0%) -> hsl(210,14.3%,53.3%)
lab(56,-2,-11) and lch(56,11,259) -> hsl(211,13.9%,53.5%)
OkLab(0.6190,-0.0120,-0.0303) -> hsl(210,14.3%,53.3%)
```

## Spec 5

All commands that take `[color]...` share one input-harvesting rule. With explicit color arguments, process them left-to-right. Each literal `-` consumes exactly one line from stdin at that position; unused later stdin lines are not implicitly appended. With no color arguments, consume every stdin line, including the final line when it has no newline. Strip surrounding whitespace from each stdin line before parsing. A truly zero-byte stdin is a successful empty batch; a blank or whitespace-only line is an attempted empty color and fails. For `mix`, this rule applies specifically to the trailing partner list after its separately required base color, as detailed in Spec 16.

Process and print incrementally. If `red`, then an invalid color, then `blue` are supplied, print red, report the failure, stop, and never process blue. This applies to CLI and stdin batches. Multiple `-` placeholders consume successive lines and preserve their interleaving with CLI arguments.

The special color identifier `pick` requests the external picker described in Spec 29. It is not a CSS color.

## Spec 6

Internally preserve sRGB color plus alpha, and implement conventional conversions accurately enough to give the normative rounded values below. sRGB channels are normalized to 0..1. For relative luminance and CIELAB, linearize a channel `c` as `c/12.92` when `c <= 0.04045`, otherwise `((c+0.055)/1.055)^2.4`. Relative luminance is `Y = 0.2126 Rlin + 0.7152 Glin + 0.0722 Blin`. Brightness is computed on nonlinear sRGB as `0.299 R + 0.587 G + 0.114 B`.

CIELAB uses the standard sRGB-to-XYZ D65 transform and D65 white `(0.95047,1.00000,1.08883)`:

```text
X = .4124564 R + .3575761 G + .1804375 B
Y = .2126729 R + .7151522 G + .0721750 B
Z = .0193339 R + .1191920 G + .9503041 B
f(t) = cbrt(t) if t > 216/24389, otherwise (24389/27*t + 16)/116
L* = 116 f(Y/Yn)-16; a*=500(f(X/Xn)-f(Y/Yn)); b*=200(f(Y/Yn)-f(Z/Zn))
```

LCh is `(L*, sqrt(a²+b²), atan2(b,a) in positive degrees)`. For inverse Lab, set `fy=(L+16)/116`, `fx=fy+a/500`, `fz=fy-b/200`, and invert each `f` by `f^-1(q)=q³` when `q³>216/24389`, otherwise `(116q-16)/(24389/27)`. Multiply by the D65 white, then convert XYZ to linear RGB with:

```text
R =  3.2404542 X - 1.5371385 Y - 0.4985314 Z
G = -0.9692660 X + 1.8760108 Y + 0.0415560 Z
B =  0.0556434 X - 0.2040259 Y + 1.0572252 Z
```

Encode a linear channel `q` as `12.92q` when `q<=0.0031308`, otherwise `1.055*q^(1/2.4)-0.055`, then clamp the displayed sRGB channel to 0..1.

OkLab uses the standard Björn Ottosson transform on linear sRGB:

```text
l=.4122214708R+.5363325363G+.0514459929B
m=.2119034982R+.6806995451G+.1073969566B
s=.0883024619R+.2817188376G+.6299787005B
L=.2104542553cbrt(l)+.7936177850cbrt(m)-.0040720468cbrt(s)
a=1.9779984951cbrt(l)-2.4285922050cbrt(m)+.4505937099cbrt(s)
b=.0259040371cbrt(l)+.7827717662cbrt(m)-.8086757660cbrt(s)
```

The OkLab inverse is:

```text
l' = L + .3963377774a + .2158037573b
m' = L - .1055613458a - .0638541728b
s' = L - .0894841775a - 1.2914855480b
l=l'^3; m=m'^3; s=s'^3
R= 4.0767416621l - 3.3077115913m + .2309699292s
G=-1.2684380046l + 2.6097574011m - .3413193965s
B=-.0041960863l - .7034186147m + 1.7076147010s
```

These are linear RGB and must be encoded/clamped as above. OkLCh is `(L,sqrt(a²+b²),positive atan2(b,a))`, with the usual polar inverse.

For RGB-to-HSL, let `max`, `min`, and `d=max-min` operate on nonlinear normalized RGB. `L=(max+min)/2`; when `d=0`, `S=0,H=0`; otherwise `S=d/(1-|2L-1|)` and hue is 60 times the usual dominant-channel expression (`(G-B)/d mod 6`, `(B-R)/d+2`, or `(R-G)/d+4`). HSL-to-RGB uses `C=(1-|2L-1|)S`, `X=C(1-|((H/60) mod 2)-1|)`, the corresponding one of `(C,X,0)`, `(X,C,0)`, `(0,C,X)`, `(0,X,C)`, `(X,0,C)`, `(C,0,X)`, and adds `m=L-C/2`. For HSV, `V=max`, `S=0` if `V=0` else `d/V`, with the same hue; inverse HSV uses `C=VS`, the same sector/X construction, and `m=V-C`. CMYK uses `K=1-max(R,G,B)`, then `(1-R-K)/(1-K)` etc., with black handled as `(0,0,0,1)`.

## Spec 7

The canonical non-interactive color result is compact HSL, one record per line:

```text
hsl(H,S.S%,L.L%)
hsla(H,S.S%,L.L%,A)       # when alpha is not exactly 1
```

There are no spaces. Hue is nearest integer degrees; S and L have exactly one fractional digit. Alpha is rounded to three decimals and trailing zeroes are removed. Calculated hue is positive. Preserve meaningful HSL coordinates through direct HSL operations even at S=0 or L at an extreme: complementing white is `hsl(180,0.0%,100.0%)`, and lightening red to white retains hue 0 and saturation 100%. Preserve alpha through all transforms and interpolation.

Normative named RGB values used throughout are: `black #000000`, `white #ffffff`, `red #ff0000`, `green #008000`, `lime #00ff00`, `blue #0000ff`, `yellow #ffff00`, `orange #ffa500`, `cyan`/`aqua #00ffff`, `magenta`/`fuchsia #ff00ff`, `navy #000080`, `teal #008080`, `indigo #4b0082`, `violet #ee82ee`, `purple #800080`, `pink #ffc0cb`, `brown #a52a2a`, `gray #808080`, `silver #c0c0c0`, `lightslategray #778899`, `lightblue #add8e6`, `lightgray #d3d3d3`, `darkgray #a9a9a9`, `hotpink #ff69b4`, `lawngreen #7cfc00`, `orchid #da70d6`, `limegreen #32cd32`, `tomato #ff6347`, and `orangered #ff4500`.

## Spec 8

`color [color]...` applies the shared input rule and emits the canonical HSL lines when stdout is not a terminal or color mode is off. Examples:

```text
color red blue green ->
hsl(0,100.0%,50.0%)
hsl(240,100.0%,50.0%)
hsl(120,100.0%,25.1%)

color rgba(255,0,0,0.5) -> hsla(0,100.0%,50.0%,0.5)
```

With an enabled color mode and terminal stdout it instead displays the analysis card in Spec 25. Invalid colors use the runtime diagnostic in Spec 28.

## Spec 9

`format TYPE [color]...` applies the shared input rule and emits exactly one formatted record per color, except raw escape-code types as noted. Supported `TYPE` values are:

`hex`, `rgb`, `rgb-float`, `rgb-r`, `rgb-g`, `rgb-b`, `hsl`, `hsl-hue`, `hsl-saturation`, `hsl-lightness`, `hsv`, `hsv-hue`, `hsv-saturation`, `hsv-value`, `lab`, `lab-a`, `lab-b`, `lch`, `lch-lightness`, `lch-chroma`, `lch-hue`, `oklab`, `oklab-l`, `oklab-a`, `oklab-b`, `oklch`, `oklch-lightness`, `oklch-chroma`, `oklch-hue`, `luminance`, `brightness`, `cmyk`, `name`, `ansi-8bit`, `ansi-8bit-value`, `ansi-8bit-escapecode`, `ansi-24bit`, and `ansi-24bit-escapecode`.

Formatting rules are lowercase `#rrggbb` (append two alpha hex digits if nonopaque); `rgb(R, G, B)` or `rgba(R, G, B, A)`; and `rgb(0.000, 0.000, 0.000)` with three decimals for `rgb-float`. Full HSL/HSV uses spaces and one decimal percentage, e.g. `hsl(210, 14.3%, 53.3%)` and `hsv(210, 22.2%, 60.0%)`. Hue components are integer lines; normalized HSL/HSV S/L/V components use four decimals. Luminance and brightness use three decimals.

Full Lab rounds each component to an integer: `Lab(L, a, b)` and includes `, A` before `)` when transparent. LCh is `LCh(L, C, h)`. Lab/LCh scalar components use two decimals. OkLab and OkLCh spell their names exactly and use four decimals for every component and scalar. CMYK is integer percentages `cmyk(C, M, Y, K)`.

## Spec 10

The following `format` outputs are normative and fix conversion and rounding details:

```text
input red:
hex #ff0000                         rgb rgb(255, 0, 0)
rgb-float rgb(1.000, 0.000, 0.000) hsl hsl(0, 100.0%, 50.0%)
hsv hsv(0, 100.0%, 100.0%)         cmyk cmyk(0, 100, 100, 0)
Lab Lab(53, 80, 67)                LCh LCh(53, 105, 40)
OkLab OkLab(0.6279, 0.2249, 0.1258)
OkLCh OkLCh(0.6279, 0.2577, 29.2232)
luminance 0.213                    brightness 0.299
rgb-r/g/b 255 / 0 / 0              hsl-hue/saturation/lightness 0 / 1.0000 / 0.5000
lab-a/b 80.11 / 67.22              lch-lightness/chroma/hue 53.23 / 104.58 / 40.00
oklab-l/a/b 0.6279 / 0.2249 / 0.1258
```

For `#778899`: RGB is `rgb(119, 136, 153)`, HSL `hsl(210, 14.3%, 53.3%)`, HSV `hsv(210, 22.2%, 60.0%)`, Lab `Lab(56, -2, -11)`, LCh `LCh(56, 11, 259)`, OkLab `OkLab(0.6190, -0.0120, -0.0303)`, OkLCh `OkLCh(0.6190, 0.0326, 248.4067)`, CMYK `cmyk(22, 11, 0, 40)`, rgb-float `rgb(0.467, 0.533, 0.600)`, luminance `0.238`, brightness `0.521`, LCh scalars `55.92`, `11.34`, `258.59`, and name `lightslategray`.

Black Lab is `Lab(0, 0, 0)`; white Lab is `Lab(100, 0, -0)`; `#888888` is `hsl(0,0.0%,53.3%)` and `Lab(57, 0, -0)`. `#FF5733AA` formats as `#ff5733aa`, `rgba(255, 87, 51, 0.667)`, and `Lab(60, 62, 54, 0.667)`.

## Spec 11

`format name` returns the closest name from the same 139-name CSS palette used by `list`, comparing colors perceptually in Lab (CIEDE2000); exact matches retain their canonical lowercase name. Required nearest results are `#ff0000 -> red`, `#ff0001 -> red`, `#778899 -> lightslategray`, `#44cc11 -> limegreen`, and `#ff5733 -> tomato`.

ANSI format behavior is:

```text
format ansi-8bit red             -> printable characters "\\x1b[38;5;196m\n"
format ansi-24bit red            -> printable characters "\\x1b[38;2;255;0;0m\n"
format ansi-8bit-value red       -> "196\n"
format ansi-8bit-escapecode red  -> raw ESC[38;5;196m with no newline
format ansi-24bit-escapecode red -> raw ESC[38;2;255;0;0m with no newline
```

For multiple raw-escapecode colors, concatenate sequences without separators. The 8-bit palette consists of the fixed xterm cube indices 16..231 (levels 0,95,135,175,215,255) plus gray ramp 232..255 (levels 8+10i); choose the perceptually closest entry by CIEDE2000, preferring the lower index on a tie. Thus `#ff8844 -> 209`, `#010101 -> 16`, `#808080 -> 244`, and `#fefefe -> 231`.

## Spec 12

`complement [color]...` rotates each HSL hue by 180 degrees without changing saturation, lightness, or alpha. `rotate DEGREES [color]...` adds an arbitrary floating-point angle and wraps cyclically. Both use shared color input. Examples:

```text
complement red -> hsl(180,100.0%,50.0%)
complement blue green yellow -> hues 60, 300, 240 respectively
rotate 90 red -> hsl(90,100.0%,50.0%)
rotate -- -90 red -> hsl(270,100.0%,50.0%)
rotate 45.5 red -> hsl(46,100.0%,50.0%)
rotate 1000 red -> hsl(280,100.0%,50.0%)
rotate 360 red -> hsl(360,100.0%,50.0%); rotate 720 red -> hsl(0,100.0%,50.0%)
```

## Spec 13

`lighten AMOUNT [color]...` adds `AMOUNT` to HSL lightness; `darken` subtracts it. `saturate AMOUNT` adds to HSL saturation; `desaturate` subtracts it. Amounts are floating point fractions where 0.2 means 20 percentage points. Clamp the result to 0..1. Negative amounts reverse the operation when passed after `--`. Preserve all other HSL components and alpha.

Required examples include red lightened by .2/.05 as lightness 70.0%/55.0%, red darkened by .2 as 30.0%, `lighten -- -0.1 red` as 40.0%, `darken -- -0.1 red` as 60.0%, and amounts 1, 2, or 100 clamping at an endpoint. Saturating `hsl(180,50%,50%)` by .2 gives 70%; desaturating it by .2 gives 30%. Saturating gray by .5 retains hue 0 and gives `hsl(0,50.0%,50.2%)`.

## Spec 14

`to-gray [color]...` creates a neutral sRGB gray that preserves the original relative luminance to 8-bit precision: compute `Y` from Spec 6, apply inverse sRGB companding to `Y`, quantize that result to the nearest 8-bit channel, use that equal channel for R/G/B, and preserve alpha. Canonical required output is:

```text
to-gray red blue green ->
hsl(0,0.0%,49.8%)
hsl(240,0.0%,29.8%)
hsl(120,0.0%,42.7%)
```

The retained hue values above come from the source HSL even though saturation becomes zero. Black and white remain `hsl(0,0.0%,0.0%)` and `hsl(0,0.0%,100.0%)`.

`textcolor [color]...` returns opaque black or white, whichever has the higher WCAG contrast against the background. Equivalently choose black when relative luminance is at least approximately 0.17913, otherwise white. Red, yellow, gray, darkgray, lightgray, and white yield black; navy, blue, and black yield white. Output uses canonical HSL.

## Spec 15

`gray LIGHTNESS` requires exactly one lightness and creates direct HSL `(hue=0,saturation=0,lightness=clamp(value,0,1))`. Separate invocations with 0, .25, .5, .75, and 1 print 0.0%, 25.0%, 50.0%, 75.0%, and 100.0%, respectively, and values outside the range clamp; for example, `gray 5` prints 100.0%. `gray 0.5` is exactly `hsl(0,0.0%,50.0%)\n`, unlike parsing the quantized RGB expression `gray(0.5)`. Additional positional values are rejected: `gray 0 .25 .5 .75 1 5` returns 2, writes no stdout, reports `error: unexpected argument '.25' found`, and shows `Usage: executable gray <lightness>`.

`set PROPERTY VALUE [color]...` replaces one coordinate, applies shared color input, and outputs canonical HSL. Properties are `red`, `green`, `blue` (0..255 sRGB channels); `hsl-hue` (degrees), `hsl-saturation`, `hsl-lightness` (0..1); `lightness`, `lab-a`, `lab-b` (CIELAB, with `lightness` meaning L* on the 0..100 scale); `chroma`, `hue` (CIELCh C and hue); `oklab-l`, `oklab-a`, `oklab-b`; and `alpha`. Conversion back to sRGB clamps gamut. Clamp bounded coordinates; hue coordinates wrap.

Normative results include:

```text
set hsl-hue 180 red       -> hsl(180,100.0%,50.0%)
set hsl-saturation .5 red -> hsl(0,50.0%,50.0%)
set hsl-lightness .7 red  -> hsl(0,100.0%,70.0%)
set red 128 blue          -> hsl(270,100.0%,50.0%)
set red 300 blue          -> hsl(300,100.0%,50.0%)
set alpha .5 red          -> hsla(0,100.0%,50.0%,0.5)
set lightness 80 red      -> hsl(14,100.0%,64.9%)
set lightness 0/1/2 red   -> HSL lightness 17.8%/18.2%/18.6%
set chroma 50 red         -> hsl(12,52.7%,53.5%)
set hue 180 red           -> hsl(167,100.0%,31.6%)
```

The invalid property `saturation` is rejected as a command-line enum error suggesting `hsl-saturation`.

## Spec 16

`mix [OPTIONS] COLOR [COLOR]...` treats the required first color as a base and independently mixes it with every later color, emitting one line per later color. Harvest the trailing `[COLOR]...` as its own shared-input batch: when partner arguments are present, use them and do not append unused stdin, but when no partner argument is present, read every stdin line as a partner. Therefore `mix red` with stdin `blue\ngreen\n` succeeds with:

```text
hsl(320,100.0%,39.6%)
hsl(40,100.0%,31.6%)
```

With zero-byte stdin, one base color is permitted and produces no mixed records. No base color is a syntax error whose stderr is exactly:

```text
error: the following required arguments were not provided:
  <color>

Usage: executable mix <color> [color]...

For more information, try '--help'.
```

Options are `-f, --fraction F` (default .5) and `-s, --colorspace SPACE` (default `Lab`). Spaces are case-sensitive enum values `Lab`, `LCh`, `RGB`, `HSL`, and `OkLab`. Clamp F to 0..1. F is the weight of the first/base color, so F=0 returns the other color and F=1 the base. Interpolate alpha linearly.

RGB interpolates nonlinear sRGB channels and quantizes each interpolated result to nearest 8-bit channels before canonical HSL output (so a 10-point black-to-white RGB gradient has HSL lightness `0.0, 11.0, 22.4, 33.3, 44.3, 55.7, 66.7, 77.6, 89.0, 100.0`). Lab and OkLab interpolate Cartesian components and convert the result back through clamped sRGB. HSL and LCh normally interpolate cylindrical hue along the shortest circular path and linearly interpolate the other components. For HSL, if exactly one endpoint is achromatic, retain the chromatic endpoint's hue rather than interpolating toward the achromatic color's nominal zero hue. Consequently `mix blue black --colorspace HSL` and `mix black blue --colorspace HSL` both produce `hsl(240,50.0%,25.0%)`. Required red/blue midpoints are:

```text
Lab   hsl(320,100.0%,39.6%)    RGB   hsl(300,100.0%,25.1%)
HSL   hsl(300,100.0%,50.0%)    LCh   hsl(329,100.0%,49.2%)
OkLab hsl(283,32.2%,48.0%)
```

Lab fractions .25 and .75 give `hsl(287,100.0%,38.2%)` and `hsl(339,100.0%,45.5%)`. Mixing red with blue, CSS green, and yellow under defaults gives, respectively, hues/lightness `(320,39.6%)`, `(40,31.6%)`, `(38,50.0%)`, all 100% saturated. Equal alpha .5 remains .5.

## Spec 17

`gradient [OPTIONS] COLOR COLOR...` samples a piecewise interpolation through two or more evenly positioned color stops. Options are `-n, --number COUNT` (default 10) and `-s, --colorspace SPACE` with the same values and default as `mix`. Output exactly COUNT canonical HSL records including the first and last stop. For sample position `t=i/(COUNT-1)`, let `u=t*(number_of_stops-1)`, select its adjacent stop interval, and interpolate with local fraction; exact stop positions reproduce the stops. This makes a 3-sample Lab gradient `red green blue` exactly those three colors.

Normative five-sample red-to-blue gradients are:

```text
Lab:   hsl(0,100.0%,50.0%); hsl(339,100.0%,45.5%); hsl(320,100.0%,39.6%); hsl(287,100.0%,38.2%); hsl(240,100.0%,50.0%)
RGB:   hsl(0,100.0%,50.0%); hsl(340,100.0%,37.5%); hsl(300,100.0%,25.1%); hsl(260,100.0%,37.5%); hsl(240,100.0%,50.0%)
HSL:   hues 0,330,300,270,240 with 100.0% saturation and 50.0% lightness
LCh:   hsl(0,100.0%,50.0%); hsl(344,100.0%,50.0%); hsl(329,100.0%,49.2%); hsl(301,100.0%,38.6%); hsl(240,100.0%,50.0%)
OkLab: hsl(0,100.0%,50.0%); hsl(343,52.3%,53.1%); hsl(283,32.2%,48.0%); hsl(244,60.7%,55.1%); hsl(240,100.0%,50.0%)
```

COUNT 0 or 1 is runtime error `[pastel error]: The specified color count must be larger than one\n`. Fewer than two color stops is `[pastel error]: The number of color arguments must be larger than one\n`. A noninteger count uses the number parse error in Spec 28.

## Spec 18

`sort-by [OPTIONS] [ORDER] [color]...` sorts a harvested batch ascending by `hue` (default), `brightness`, `luminance`, `chroma` (CIELCh C), or `random`. When CLI colors are supplied, an explicit first order token distinguishes them; with stdin, order may be omitted and defaults to hue. `-r, --reverse` reverses the result. `-u, --unique` removes equal RGBA colors, including differently spelled equivalents, before output. Random order shuffles. Emit canonical HSL.

Examples: hue sorting red/blue/CSS-green/yellow produces red, yellow, green, blue. Luminance or brightness sorting black/gray/white produces that order. For blue, CSS-green, red, yellow, both brightness and luminance ordering are blue, green, red, yellow. Chroma ordering for green, yellow, red, blue is green, yellow, red, blue. Invalid order is a command-line enum error.

## Spec 19

`list [-s|--sort ORDER]` lists lowercase CSS color names, one per line, sorted by `hue` by default or by `brightness`, `luminance`, `chroma`, or `random`. The four deterministic orders operate on the 139 canonical names. Random order uses a fresh shuffle of the full 148-spelling CSS table, including the additional aliases `cyan`, `magenta`, `grey`, `darkgrey`, `dimgrey`, `lightgrey`, `darkslategrey`, `lightslategrey`, and `slategrey`. Equivalent-color spellings are removed only when they become adjacent in that random ordering, so the result count varies; repeated reference invocations produced 146, 147, and 148 distinct lines. Random output is therefore not a permutation of the 139-name deterministic list. Two successive random runs are overwhelmingly unlikely to match. In non-TTY mode, the complete default hue order is exactly:

```text
black
palevioletred
pink
lightpink
snow
rosybrown
lightcoral
crimson
indianred
mistyrose
brown
salmon
firebrick
maroon
tomato
darkred
red
darksalmon
orangered
coral
lightsalmon
sienna
chocolate
saddlebrown
sandybrown
darkorange
seashell
peru
peachpuff
orange
linen
burlywood
bisque
tan
antiquewhite
navajowhite
darkgoldenrod
blanchedalmond
goldenrod
moccasin
papayawhip
wheat
oldlace
floralwhite
gold
cornsilk
khaki
darkkhaki
olive
yellow
palegoldenrod
lemonchiffon
lightgoldenrodyellow
lightyellow
beige
ivory
olivedrab
yellowgreen
darkolivegreen
greenyellow
chartreuse
lawngreen
darkgreen
green
lime
limegreen
forestgreen
palegreen
lightgreen
darkseagreen
honeydew
springgreen
seagreen
mediumseagreen
mediumspringgreen
mintcream
mediumaquamarine
aquamarine
turquoise
lightseagreen
mediumturquoise
aqua
darkcyan
teal
darkslategray
paleturquoise
darkturquoise
lightcyan
azure
cadetblue
powderblue
lightblue
skyblue
deepskyblue
lightskyblue
aliceblue
slategray
lightslategray
steelblue
lightsteelblue
dodgerblue
cornflowerblue
ghostwhite
lavender
royalblue
darkgray
dimgray
gainsboro
gray
lightgray
silver
white
whitesmoke
darkslateblue
slateblue
mediumslateblue
midnightblue
blue
darkblue
mediumblue
navy
mediumpurple
rebeccapurple
blueviolet
indigo
darkorchid
darkviolet
mediumorchid
thistle
plum
violet
orchid
darkmagenta
fuchsia
purple
mediumvioletred
hotpink
lavenderblush
deeppink
```

The first 20 names for brightness are `black, navy, darkblue, mediumblue, blue, midnightblue, indigo, maroon, darkred, purple, darkmagenta, darkgreen, darkviolet, darkslategray, darkslateblue, green, red, firebrick, rebeccapurple, brown`. For luminance they are `black, navy, darkblue, midnightblue, indigo, mediumblue, maroon, darkred, purple, darkslateblue, darkslategray, blue, darkmagenta, rebeccapurple, darkgreen, saddlebrown, brown, firebrick, darkviolet, blueviolet`. For chroma they are `black, dimgray, gray, darkgray, silver, gainsboro, lightgray, white, whitesmoke, snow, ghostwhite, mintcream, aliceblue, seashell, azure, floralwhite, lavenderblush, linen, ivory, oldlace`.

## Spec 20

In TTY output with an enabled mode, `list` paints each name on its own background. The text payload is one leading space plus the name left-padded on the right to width 24. Append reset and newline. Choose black/white foreground by `textcolor`. In 24-bit mode use `ESC[38;2;FR;FG;FB;48;2;BR;BG;BBm`; in 8-bit mode use the corresponding `38;5` and `48;5` indices. In TTY `off` mode retain the 25-character padded payload but emit no ANSI.

The first 20 background colors, fixing TTY list output, are: black `000000`, palevioletred `db7093`, pink `ffc0cb`, lightpink `ffb6c1`, snow `fffafa`, rosybrown `bc8f8f`, lightcoral `f08080`, crimson `dc143c`, indianred `cd5c5c`, mistyrose `ffe4e1`, brown `a52a2a`, salmon `fa8072`, firebrick `b22222`, maroon `800000`, tomato `ff6347`, darkred `8b0000`, red `ff0000`, darksalmon `e9967a`, orangered `ff4500`, coral `ff7f50`. Their 8-bit background indices are respectively `16,168,217,217,231,138,210,197,167,224,124,210,124,88,203,88,196,173,202,209`; foreground is 16 for light backgrounds and 231 for dark backgrounds.

`list --help` with a 100-column terminal is exactly:

```text
Show a list of available color names

Usage: executable list [OPTIONS]

Options:
  -s, --sort <sort-order>  Sort order [default: hue] [possible values: brightness, luminance, hue,
                           chroma, random]
  -h, --help               Print help
```

`list --sort invalid` returns 2 and writes exactly this stderr:

```text
error: invalid value 'invalid' for '--sort <sort-order>'
  [possible values: brightness, luminance, hue, chroma, random]

For more information, try '--help'.
```

## Spec 21

`random [-n|--number COUNT] [-s|--strategy STRATEGY]` emits COUNT independently random canonical HSL colors, default 10. COUNT may be zero (empty output) and at least 100 must work. Each invocation should draw fresh entropy so repeated invocations are overwhelmingly unlikely to match. Strategies are `vivid` (default; randomized vivid valid colors), `rgb` (uniform random sRGB channels), `gray` (random neutral colors and therefore exactly `,0.0%,`), and `lch_hue` (random hue at fixed reasonable LCh lightness/chroma, converted into gamut).

COUNT must be passed via `-n`/`--number`; a bare positional is unexpected. Missing/repeated options are command-line errors. A noninteger count is runtime error `[pastel error]: Could not parse number 'VALUE'\n`. An invalid strategy is a command-line enum error.

## Spec 22

`distinct [COUNT] [FIXED-COLOR]... [-m|--metric METRIC] [-v|--verbose]` returns COUNT pairwise different canonical HSL colors; COUNT defaults to 10 and must be at least 2. Metrics are the case-sensitive `CIE76` (default Euclidean Lab distance) and `CIEDE2000`. Fixed colors seed the optimized set and count toward the total. The output must remain practical through count 50.

The implementation should generate a visually spread set by maximizing color-distance separation; exact random results are not fixed. If fixed-color count is greater than COUNT, fail with `[pastel error]: The number of fixed colors must be smaller than the total number of colors\n`. Equality is accepted and returns the fixed colors in input order; `distinct 2 red blue` prints canonical red followed by canonical blue and succeeds. Counts 0 or 1 fail with `[pastel error]: The number of colors must be larger than one\n` and a noninteger uses the standard number parse error.

With `-v/--verbose`, colors still go to stdout and progress goes to stderr. Print at least ten progress lines. Each progress line contains one six-digit lowercase RGB hex token for every color in the requested set, followed by one ASCII trailing space. For example, a reference run of `distinct 3 --verbose` included `[      5000] D_mean = 147.73; D_min = 147.14; T = 2.321343 f11917 3524df 21cc0c `; its spaces, numbers, and hex tokens vary, but all three hex tokens are present.

## Spec 23

`colorblind TYPE [color]...` applies shared color input. TYPE is `prot`, `deuter`, or `trit`, simulating complete protanopia, deuteranopia, or tritanopia using a standard LMS dichromacy projection and converting back to clamped sRGB. Preserve alpha and output canonical HSL. These exact primary-color results are normative (CSS `green` means #008000; `lime` means #00ff00):

```text
             red                         blue                         green                       lime                         yellow
prot    hsl(53,100.0%,24.7%)       hsl(239,100.0%,50.0%)       hsl(53,94.0%,26.1%)        hsl(54,100.0%,53.3%)       hsl(59,100.0%,50.8%)
deuter  hsl(54,100.0%,32.7%)       hsl(238,100.0%,50.0%)       hsl(52,70.1%,26.3%)        hsl(52,77.4%,54.9%)        hsl(57,100.0%,53.9%)
trit    hsl(354,100.0%,50.0%)      hsl(178,100.0%,19.6%)       hsl(177,45.8%,32.5%)       (same algorithm)            hsl(16,100.0%,96.3%)
```

Invalid TYPE returns 2 with exactly this shape and valid values:

```text
error: invalid value 'invalid_type' for '<type>'
  [possible values: prot, deuter, trit]

For more information, try '--help'.
```

An empty stdin is a successful empty batch.

## Spec 24

With environment `COLUMNS=100`, `colorblind --help` is exactly:

```text
Convert the given color to how it would look to a person with protanopia, deuteranopia, or
tritanopia 

Example:
  pastel distinct 3 | pastel colorblind deuter

Usage: executable colorblind <type> [color]...

Arguments:
  <type>
          The type of colorblindness that should be simulated (protanopia, deuteranopia, tritanopia)
          
          [possible values: prot, deuter, trit]

  [color]...
          Colors can be specified in many different formats, such as #RRGGBB, RRGGBB, #RGB, 'rgb(…,
          …, …)', 'hsl(…, …, …)', 'gray(…)' or simply by the name of the color. The identifier '-'
          can be used to read a single color from standard input. Also, the special identifier
          'pick' can be used to run an external color picker to choose a color. If no color argument
          is specified, colors will be read from standard input.
          Examples (all of these specify the same color):
            - lightslategray
            - '#778899'
            - 778899
            - 789
            - 'rgb(119, 136, 153)'
            - '119,136,153'
            - 'hsl(210, 14.3%, 53.3%)'
          Alpha transparency is also supported:
            - '#77889980'
            - 'rgba(119, 136, 153, 0.5)'
            - 'hsla(210, 14.3%, 53.3%, 50%)'

Options:
  -h, --help
          Print help (see a summary with '-h')
```

## Spec 25

`paint [OPTIONS] COLOR [text]...` joins text arguments with one ASCII space. With no text arguments, read all stdin bytes as text. `COLOR` may be `-`, consuming one stdin line before text handling, or `default`, meaning do not select a foreground. Options are `-o/--on BG`, `-b/--bold`, `-i/--italic`, `-u/--underline`, and `-n/--no-newline`. Alpha is accepted but ignored by terminals.

In mode `off` (including auto on a non-TTY), output the unstyled text. In 24-bit mode begin with one combined SGR: foreground `38;2;R;G;B`, optional background `48;2;R;G;B`, then style parameters 1, 3, 4 in that order; terminate with `m`. In 8-bit use `38;5;INDEX`/`48;5;INDEX`. After text emit `ESC[0m` if an SGR was opened. Unless `-n`, append one additional `\n` regardless of whether stdin text already ended in newline. Thus stdin `Text from stdin\n` produces two logical newlines, with reset between them in colored mode.

Normative byte strings include:

```text
--color-mode=24bit paint red "Hello World" -> ESC[38;2;255;0;0mHello WorldESC[0m\n
--color-mode=8bit paint red "Hello World"  -> ESC[38;5;196mHello WorldESC[0m\n
--color-mode=24bit paint --on blue red X   -> ESC[38;2;255;0;0;48;2;0;0;255mXESC[0m\n
--color-mode=24bit paint --bold --italic --underline red X
                                                 -> ESC[38;2;255;0;0;1;3;4mXESC[0m\n
```

With `COLUMNS=100`, long help is exactly:

```text
Print colored text using ANSI escape sequences

Usage: executable paint [OPTIONS] <color> [text]...

Arguments:
  <color>    The foreground color. Use '-' to read the color from STDIN.
  [text]...  The text to be printed in color. If no argument is given, the input is read from STDIN.

Options:
  -o, --on <bg-color>  Use the specified background color
  -b, --bold           Print the text in bold face
  -i, --italic         Print the text in italic font
  -u, --underline      Draw a line below the text
  -n, --no-newline     Do not print a trailing newline character
  -h, --help           Print help
```

## Spec 26

Color selection applies to `paint`, TTY `list`, the TTY analysis card, and ordinary `format` output when color is explicitly enabled. `--force-color`/`-f` is an alias for explicit 24-bit mode. Explicit CLI mode wins over automatic detection and over `NO_COLOR`; for example, `NO_COLOR=1 executable --color-mode 8bit paint red X` still emits the 8-bit SGR form. Otherwise `NO_COLOR` disables ANSI, and auto mode emits no ANSI when stdout is not a terminal.

The `PASTEL_COLOR_MODE` environment variable is consulted only when stdout is a terminal. On a terminal, `24bit`, `8bit`, and `off` select that mode and take precedence over `NO_COLOR`; an invalid value fails with `[pastel error]: Unknown PASTEL_COLOR_MODE value (VALUE)\n`. When stdout is not a terminal, the variable is ignored before validation: recognized values do not force color, `NO_COLOR` still yields plain output when both variables are set, and an unrecognized value is not an error. In particular, the non-TTY invocation `PASTEL_COLOR_MODE=bogus executable color red` succeeds with plain `hsl(0,100.0%,50.0%)\n` and empty stderr, while non-TTY `PASTEL_COLOR_MODE=8bit NO_COLOR=1 executable paint red X` succeeds with plain `X\n`.

Ordinary `format` output remains plain in `off` mode and in non-TTY `auto` mode. Explicit 24-bit mode, including `--force-color`, wraps each formatted record with a combined foreground/background swatch SGR, choosing the foreground using `textcolor`; explicit 8-bit mode does the analogous palette conversion. Exact red examples are:

```text
--force-color format hex red          -> ESC[38;2;0;0;0;48;2;255;0;0m#ff0000ESC[0m\n
--color-mode 24bit format hex red     -> ESC[38;2;0;0;0;48;2;255;0;0m#ff0000ESC[0m\n
--color-mode 8bit format hex red      -> ESC[38;5;16;48;5;196m#ff0000ESC[0m\n
```

ANSI SGR construction never inserts separate SGRs between parameters: foreground, background, and styles share one `ESC[` sequence, and reset is exactly `ESC[0m`.

## Spec 27

When `color red` writes to a terminal in 24-bit or 8-bit mode, display a ten-line analysis card. The first and last lines are blank. Ignoring SGR codes, the middle eight lines are exactly 60 characters:

```text
  ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀  Name: red                               
  ▀▀            ▀▀  Hex: #ff0000                            
  ▀▀            ▀▀  RGB: rgb(255, 0, 0)                     
  ▀▀            ▀▀  HSL: hsl(0, 100.0%, 50.0%)              
  ▀▀            ▀▀                                          
  ▀▀            ▀▀  Most similar:                           
  ▀▀            ▀▀         orangered                        
  ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀         tomato                           
```

Every colored character is individually wrapped in a brush SGR followed by `ESC[0m`. The checker frame alternates foreground/background light gray `(240,240,240)` and dark gray `(181,181,181)`, starting light-over-dark; in 8-bit use indices 254 and 249. Each full frame row has 16 `▀`. Each interior row has two checker `▀`, twelve spaces painted with the analyzed color, then two checker `▀`. Red is RGB 255,0,0 / index 196. After the 16-character frame on each of the last two rows, emit three plain spaces, five individually painted swatch spaces, one plain space, and the similar-color name; the swatches are orangered `(255,69,0)`/202 and tomato `(255,99,71)`/203. Use the combined foreground/background brush (`38` and `48` set to the same swatch color). This byte-level construction plus the exact padding above defines the TTY card; a pseudo-terminal wrapper may translate its LFs to CRLF.

## Spec 28

`colorcheck` always emits ANSI (independent of non-TTY auto mode), succeeds, and constructs this fixed diagnostic. Start with blank line, `8-bit mode:\n`, then one line of exactly 30 spaces. Print four identical panel rows. Each row starts with two plain spaces, then three eight-cell panels separated by two plain spaces. Each cell is the byte sequence `ESC[38;5;N;48;5;Nm ESC[0m` (the visible cell is one space); panel indices are 52, 23, and 17. Then print another 30-space line, `24-bit mode:\n`, another 30-space line, and four analogous rows whose cells are `ESC[38;2;R;G;B;48;2;R;G;Bm ESC[0m` for panels `(73,39,50)`, `(16,51,30)`, and `(29,54,90)`. Print a final 30-space line, followed exactly by:

```text
If your terminal emulator supports 24-bit colors, you should see three square color panels in the lower row and the colors should look similar (but slightly different from) the colors in the top row panels.
The panels in the lower row should look like squares that are filled with a uniform color (no stripes or other artifacts).

You can also open https://github.com/sharkdp/pastel/blob/master/doc/colorcheck.md in a browser to compare how the output should look like.
```

Every displayed cell has its own reset, and every described line ends in `\n`. This yields a 6,244-byte UTF-8/ASCII stream.

## Spec 29

`pick [count]` is an interactive color-picker command, and help for it must mention picking a color and the optional count. The special input color `pick` invokes the selected `--color-picker` tool or searches the allowed picker list. The evaluation environment has no such tool; in that case return 1 and print a stderr diagnostic containing `Could not find any external color picker tool`. Do not assign behavior of any external picker executable to this artifact.

## Spec 30

Runtime conversion/parsing failures have exact single-line diagnostics:

```text
[pastel error]: Could not parse color 'VALUE'
[pastel error]: Could not parse number 'VALUE'
```

They return 1. This includes an empty line as color `''`. A truly empty stream, however, is an empty successful batch. Invalid colors such as `#gg0000`, `#00`, `#00000`, `12345`, `1234567`, `123456789`, `rgb(10,0)`, `rgb(a,b,c)`, `hsl(360,100,50)`, `lab(10;20;30)`, `light   blue`, and `blu` must all be rejected using the original token in the message. Invalid UTF-8 arriving on stdin must also terminate nonzero with a diagnostic rather than crash or silently ignore the bytes.

Additional exact runtime messages are those stated in Specs 17 and 22. Syntax-layer enum errors name the offending value and list possible values; examples include invalid format type, sort order, random strategy, distinct metric, colorblind type, global mode, and picker. `paint` without `<color>` and `gradient` without `<color>...` are syntax errors. A missing `paint -o` value names `--on <bg-color>` and, like other missing option values, omits a usage line. Invalid-format and syntax diagnostics must never be written to stdout.
