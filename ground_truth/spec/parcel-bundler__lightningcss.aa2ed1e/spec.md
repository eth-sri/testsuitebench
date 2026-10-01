# Clarified specification for `executable`

The required artifact is a directly runnable file named `executable` in the working directory. It is a command-line CSS parser, transformer, compatibility compiler, bundler, CSS-modules compiler, minifier, and source-map generator. All paths and examples below use UTF-8. Unless an error is specified, processing succeeds with status 0 and writes nothing to stderr.

The required compatibility profile is the one identified by the CLI version string `lightningcss 1.0.0-alpha.70`. This name is only a label for the behavior fully described below; an implementation must not assume that repository source, test fixtures, or another command is available at run time.

## Spec 1

`--version` and `-V` print exactly `lightningcss 1.0.0-alpha.70\n` to stdout and exit successfully. `--help` and `-h` stop argument processing successfully only if the parser reaches them before an invalid argument. Thus `executable --help --definitely-invalid` and the corresponding `-h` form print help, but `executable --definitely-invalid --help` exits 2, leaves stdout empty, and reports the unknown argument using the diagnostic in Spec 2. A successful help invocation emits nothing to stderr and prints the following exact UTF-8 text to stdout, including blank lines and the final newline:

```text
lightningcss 1.0.0-alpha.70
Devon Govett <devongovett@gmail.com>
A CSS parser, transformer, and minifier

USAGE:
    executable [OPTIONS] [INPUT_FILE]...

ARGS:
    <INPUT_FILE>...    Target CSS file (default: stdin)

OPTIONS:
        --browserslist
            

        --bundle
            

        --css-modules [<CSS_MODULES>]
            Enable CSS modules in output. If no filename is provided, <output_file>.json will be
            used. If no --output-file is specified, code and exports will be printed to stdout as
            JSON

        --css-modules-dashed-idents
            

        --css-modules-pattern <CSS_MODULES_PATTERN>
            

        --custom-media
            Enable parsing custom media queries

    -d, --output-dir <OUTPUT_DIR>
            Destination directory to output into

        --error-recovery
            

    -h, --help
            Print help information

    -m, --minify
            Minify the output

    -o, --output-file <OUTPUT_FILE>
            Destination file for the output

        --sourcemap
            Enable sourcemap, at <output_file>.map

    -t, --targets <TARGETS>
            

    -V, --version
            Print version information
```

## Spec 2

Recognized options are those shown in the help plus the accepted legacy switch `--nesting`, which is intentionally omitted from the help text. Short and long forms are equivalent. Required-value options are `-o/--output-file`, `-d/--output-dir`, `-t/--targets`, and `--css-modules-pattern`; each accepts a following token or long-option `--name=value` syntax. `--css-modules` has an optional export-file argument and accepts both `--css-modules=FILE` and `--css-modules FILE`; a following non-option is consumed as that optional value, so place an input filename before this form or use `=` when disambiguation is needed. With no following value (including when the next token is another option), it merely enables modules. `--` ends option parsing, so subsequent dash-prefixed tokens are input filenames. Input filenames and options may be interspersed.

An unknown option is a command-line parse error: stdout is empty and stderr uses the conventional form `error: Found argument 'FLAG' which wasn't expected, or isn't valid in this context`, contains `USAGE:`, suggests `For more information try --help`, and, for a dash-prefixed token, advises using `-- FLAG` if it was intended as a value. A missing option value similarly leaves stdout empty and says that the named option `requires a value but none was supplied`, shows its full usage form, and suggests `--help`. Argument errors are nonzero. `--targets` and `--browserslist` are mutually exclusive and the error names both and says they cannot be used together.

## Spec 3

With no input filenames, read all CSS bytes from stdin. With one input filename, read that file. A single input goes to stdout unless `-o/--output-file` or `-d/--output-dir` is present. Stdin and a file containing the same text undergo the same parsing and transformation. Input is required to be valid UTF-8; invalid UTF-8 is a nonzero error such as `Error: Error { kind: InvalidData, message: "stream did not contain valid UTF-8" }\n`. A missing Unix file produces status 1 and `Error: Os { code: 2, kind: NotFound, message: "No such file or directory" }\n` on stderr.

Empty or whitespace-only valid input succeeds. No rules means no serialized CSS bytes; stdout mode still contributes its normal terminating print newline, so ordinary empty pretty output is `\n\n`. The processor must comfortably handle at least 500 rules, thousand-item selector lists, very long selectors and declaration values, deeply nested valid blocks, Unicode, and data URLs within the test timeout.

## Spec 4

`-o FILE`/`--output-file FILE` writes CSS to that file, overwrites an existing file, and leaves stdout empty. If the file's parent directory is absent, the program creates it before writing. For example, `-o missing/out.css` with stdin `a{}` succeeds with status 0, creates both `missing` and `missing/out.css`, and leaves stdout and stderr empty. One extra newline is added when CSS is sent to stdout but not when bytes are written to a file. Thus `a { color: red; }` becomes `a {\n  color: red;\n}\n` in a file and `a {\n  color: red;\n}\n\n` on stdout; with minification the corresponding forms are `a{color:red}` in a file and `a{color:red}\n` on stdout.

Two or more input files require `-d/--output-dir`. Without it, fail with `Cannot output to stdout with multiple inputs. Use --output-dir instead.\n`. Combining multiple inputs with `--output-file` fails with `Cannot use the --output-file option with multiple inputs. Use --output-dir instead.\n`. A write failure is nonzero and reports an `Error` on stderr.

## Spec 5

`-d DIR`/`--output-dir DIR` writes one result per input and creates `DIR` when it does not exist. For example, given an input file `a.css` containing `a{}`, `-d none a.css` succeeds with status 0, creates `none/a.css`, and leaves stdout and stderr empty. Each output uses only the input basename, flattening source subdirectories; normal `.css` names are retained. Nested, absolute, relative, `.` and `..` input paths are accepted. Inputs with the same basename collide according to normal sequential overwrite behavior. Directory mode emits no CSS on stdout. It supports all transformation options, source maps, CSS modules, multiple files, and multiple bundled entry points. Processing of one file must not leak names, sources, or declarations into another.

## Spec 6

Default output is a deterministic canonical pretty printer, not source preservation. It removes ordinary comments and `@charset`, parses typed values, normalizes and may reorder declarations, shortens values even without `--minify`, and emits two-space indentation. A style rule is printed as `selector {`, one declaration per line as two spaces plus `property: value;`, then `}`; top-level rules are separated by one blank line. Nested blocks indent by two more spaces, with the `@font-feature-values` exception in Spec 24. Within a containing style rule or `@scope`, between ordinary sibling rules inside a conditional grouping at-rule such as `@media`, and between steps of a `@keyframes` rule, sibling nested blocks are separated by one blank line. A declaration followed by a nested rule has one blank line between them. Commas, combinators, functions, strings, escapes, semicolons, and at-rule preludes use consistent CSS whitespace.

For example:

```css
.button {
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border-radius: 4px;
}
```

canonicalizes to:

```css
.button {
  color: #fff;
  background-color: #007bff;
  border-radius: 4px;
  padding: 10px 20px;
}
```

Canonical declaration ordering groups related properties while preserving cascade semantics: required prefixed fallbacks precede standard forms; earlier/later overrides and `!important` behavior must remain equivalent; longhands and shorthands are reordered or merged only when safe.

## Spec 7

The parser accepts complete stylesheets and declaration grammars rather than treating CSS as arbitrary text. It recognizes escaped and Unicode identifiers, strings, URLs, numbers, dimensions, percentages, hashes, functions, bracket blocks, comments, custom-property token streams, qualified style rules, nested rules, and known or unknown declarations. It preserves valid unknown/custom syntax where CSS permits it. A leading UTF-8 BOM is accepted but is preserved in serialized output rather than ignored: input bytes `EF BB BF` followed by `.test { color: red; }` produce the same BOM followed by `.test {\n  color: red;\n}\n\n`. CSS-wide values `initial`, `inherit`, `unset`, `revert`, and `revert-layer`, signed and very large values, negative zero, scientific notation, and `!important` are supported.

Without `--error-recovery`, malformed selectors, lexer-level bad strings or escapes, missing colons, unclosed functions, invalid property names, dangling combinators, empty selectors, malformed attribute/pseudo syntax, invalid typed at-rule descriptors, and misplaced `@import`/`@namespace` are fatal and return nonzero, except for the specifically accepted EOF string below. Diagnostics identify the error kind when applicable, the filename (or stdin identity), and zero-based line and column. These exact file cases use the Rust panic path: stdout is empty, the shell status is 134 (SIGABRT; Python `subprocess` reports `-6`), and stderr contains `panicked at` and `called \`Result::unwrap()\` on an \`Err\` value`:

- `.test {\n  123invalid: red;\n  color: blue;\n}` reports `UnexpectedToken(Semicolon)`.
- A declaration split across lines as `.test {\n  content: "\";\n}` reports `UnexpectedToken(BadString("\";"))`.
- `.test {\n  transform: scale(2;\n}` reports `UnexpectedToken(CloseCurlyBracket)`.
- `.test {\n  color red;\n}` reports `UnexpectedToken(Ident("red"))`.
- An empty selector such as `{ color: red; }` reports `SelectorError(EmptySelector)`.

By contrast, the exact stdin bytes `a{content:"unterminated}` succeed with status 0 and empty stderr, treating the closing brace as string content and serializing `a {\n  content: "unterminated}";\n}\n\n`. Fatal target and some typed-value parse failures use the same observable panic form where specified below.

## Spec 8

`--error-recovery` changes recoverable CSS syntax errors into warnings on stderr, continues after multiple errors, serializes the recovered stylesheet, and exits 0. Its recovery unit is not invariably the smallest malformed declaration. For the exact stdin `a{color:red; broken; margin:1px} a, {x:y} b{color:blue}`, it discards both `color:red` and `broken`, retains the following margin and later valid rule, and writes exactly `a {\n  margin: 1px;\n}\n\nb {\n  color: #00f;\n}\n\n` to stdout. Stderr contains `Unexpected end of input` at line 0, column 20 and `Invalid empty selector` at line 0, column 37. Recovery never fabricates a malformed declaration. File-resolution, output-write, bundling-constraint, argument, and invalid-UTF-8 errors remain fatal. Recovery composes with minification, output files, source maps, modules, and targets.

## Spec 9

`-m/--minify` selects compact serialization and semantic size optimization. It removes comments and unnecessary whitespace/semicolons/quotes/zeros, but retains whitespace required to separate tokens and preserves strings, custom-property meaning, URLs, fallback order, `!important`, rule order, selector specificity, and cascade behavior. It merges adjacent compatible rules and duplicate selectors/declaration blocks, removes empty or redundant constructs where safe, and combines longhands into the shortest safe shorthand.

Minified calculation whitespace has a required custom-property exception: division in `calc(var(--spacing) / 2)` retains exactly one space on both sides of `/`. For the `css_vars.css` declarations `--spacing: 20px` and `padding: calc(var(--spacing) / 2)`, the minified output contains exactly `padding:calc(var(--spacing) / 2)`, not `padding:calc(var(--spacing)/2)`.

Representative exact results are `a { color: red; margin: 0px 0px 0px 0px; }` to `a{color:red;margin:0}`, `#ff0000` to `red`, `blue` to `#00f`, `white` to `#fff`, and four equal zero margin components to `margin:0`. Already-minified CSS remains valid and stable. Pretty and minified processing perform the same semantic parsing and target transformations; only optimization choices and layout differ.

Canonical declaration order is deterministic and is not generally source order. Required minified examples include `.dep { width: 100%; height: 50vh; margin: 0; }` becoming `.dep{width:100%;height:50vh;margin:0}` and `.box { display: flex; gap: 1rem; }` becoming `.box{gap:1rem;display:flex}`. For the sequence `display`, `justify-content`, `align-items`, `padding`, `background-color`, and `box-shadow` in a navigation rule, canonical output orders those families as `background-color`, `justify-content`, `align-items`, `padding`, `display`, `box-shadow`. A navigation-list rule orders `gap`, `margin`, `padding`, `list-style`, `display`; a card rule orders `background-color`, `border`, `border-radius`, `margin-bottom`, `padding`, `box-shadow`. The ordering-barrier cases for custom, unknown, and `all` declarations are specified below.

## Spec 10

Numeric/value canonicalization covers integers, decimals, percentages, lengths, angles, times, frequencies, resolutions, flex fractions, viewport units, container-query units, absolute/font/root-relative units, and mixed length-percentage values. Remove a unit from zero where legal, normalize signed zero, omit a leading zero in minified fractions when shorter, round using the reference's magnitude-dependent precision, and choose shorter equivalent units when safe (including time, angle, resolution, and absolute-length conversions). Preserve units where conversion is unsafe or browser support requires them.

Required precision and range examples are:

- In pretty output, `padding: 1.666667%` becomes `padding: 1.66667%`; `height: 123456.789em` becomes `height: 123457em`; `margin: 1e6px` becomes `margin: 1000000px`; and `flex-grow: 123456.789` becomes `flex-grow: 123457`.
- In minified ordinary lengths, `10.123456789px` becomes `10.1235px`, `0.0001px` becomes `.0001px`, and `9999999.99px` becomes `10000000px`.
- In a pretty rule containing `width: 999999999999999999999999px`, `height: 1e308px`, `z-index: 999999999999`, and `opacity: 999`, the output is ordered as `z-index`, `opacity`, `width`, `height` and the respective values are `2147483647`, `999`, `1e24px`, and `3.40282e38px`.
- For a rule containing `width`, `height`, `margin`, and `padding` with percentage or container-query-unit values, canonical order is `width`, `height`, `margin`, `padding`. With `--targets "chrome 105"`, `50cqw`, `100cqh`, `5cqmin 10cqmax`, and `10cqi 20cqb` are retained in that order.

Parse and simplify `calc()`, `min()`, `max()`, `clamp()`, `round()`, `mod()`, and `rem()` expressions: fold compatible constants, identities and nested arithmetic; handle parentheses, multiplication/division, negative and tiny/large/scientific values; retain expressions with variables or incompatible units. Constant `abs()`, `sign()`, `sin()`, `cos()`, and `tan()` calls are folded where the typed property permits that simplification. In the exact minified declarations `width:abs(-10px); height:abs(10px); opacity:sign(-5); z-index:sign(5); flex-grow:sign(0)`, the results are `width:10px`, `height:10px`, `opacity:-1`, unchanged `z-index:sign(5)`, and `flex-grow:0`. `sin(30deg)`, `cos(60deg)`, and `tan(45deg)` used as opacity values become `.5`, `.5`, and `1`. Typed `env()` and `var()` arguments and fallbacks remain intact.

## Spec 11

Color parsing and canonicalization covers named and system colors, `transparent`, `currentColor`, 3/4/6/8-digit hex, legacy comma and modern space/slash `rgb[a]()` and `hsl[a]()`, `hwb()`, `lab()`, `lch()`, `oklab()`, `oklch()`, `color()` spaces (including sRGB, display-p3 and XYZ), relative-color syntax, missing `none` channels, alpha percentages, `color-mix()`, and `light-dark()`. Compute constant colors, clamp channels, normalize case and angles, and choose the shortest equivalent representation. Preserve context-dependent colors.

For targets lacking a color syntax, emit one or more older RGB/hex, display-p3, or Lab-family fallbacks in increasing capability order and retain the modern value when useful. Evaluate constant `color-mix` and relative colors when required. Target boundaries include Safari 15.3 versus 15.4 for OKLCH and Chrome 120 versus 123 for `light-dark()`. Colors work identically inside gradients, shadows, borders, SVG, keyframes, palette rules, custom-property fallbacks, and other typed properties. Alpha channels converted to eight-digit hex use nearest-byte rounding; in particular, `rgba(0, 0, 0, 0.3)` becomes `#0000004d`, including in a box-shadow.

## Spec 12

Image/value syntax includes quoted and unquoted `url()`, empty URLs, fragments, relative/absolute/protocol-relative paths, query strings, special characters, data URIs, multiple images, `image()`, `image-set()`, `cross-fade()`, and gradients. In pretty output, canonical URL and image-string arguments use double quotes. This applies to fragments (`url("#myClip")`), current- and parent-relative paths (`url("./images/bg.png")`, `url("../cursors/pointer.cur")`), root-absolute paths (`url("/images/bg.png")`), protocol and protocol-relative URLs (`url("https://example.com/cursor.cur")`, `url("//example.com/image.png")`), and query/fragment-bearing paths (`url("image.png?v=123&size=large")`, `url("mask.svg#shape")`, and `url("cursor.cur?v=2#pointer")`). Other examples include `image("fallback.png")` and `cross-fade(url("a.png"),url("b.png"),50%)`. The `cross-fade()` spelling has no whitespace after its commas even in pretty output. This also applies to a data URL stored in a custom property, such as `url("data:image/svg+xml;base64,PHN2Zz4=")`. Minified output instead removes quotes when doing so is syntactically safe and shorter. Function parentheses have no padding whitespace, so modern output is `image-set("image.jpg" 1x, "image-2x.jpg" 2x)`, not a form with spaces immediately after `(` or before `)`. Do not alter the bytes or meaning of data URLs or absolute/network URLs. Normal transformation does not rebase relative URL text merely because the input or output is in another directory.

Support `linear-gradient`, `radial-gradient`, `conic-gradient`, all repeating variants, angles/directions, shapes/sizes/positions, hints, negative/multiple/double-position stops, calc/var stops, transparent/current/system/modern colors, and multiple background images. Canonicalize redundant directions and stops. For old targets, generate legacy `-webkit-gradient` or prefixed WebKit/Mozilla/Opera forms and split unsupported double stops, while ordering fallbacks before the standard gradient.

## Spec 13

Selectors support type, universal, class, ID, namespace, nesting `&`, all combinators, comma lists, attribute namespaces/operators/quoted or unquoted values and `i`/`s` flags, escaped and Unicode names, and pseudo-elements/classes. Structural formulas include all `:nth-*` forms, odd/even, signed formulas, and `of <selector-list>`. Functional selectors include `:not`, `:is`, `:where`, `:has`, `:lang`, `:dir`, and vendor/Shadow DOM/view-transition forms. Also accept link, target, input-state, validation, range, focus, fullscreen, autofill, read-only/write, placeholder, scrollbar, selection, marker, backdrop and file-selector pseudos.

Normalize combinator/list whitespace, nth formulas, legacy pseudo-element spelling, safe universal selectors, escaping, and attribute quoting without changing specificity. Minified string serialization uses double quotes when a string contains a literal double quote and escapes that character: `quotes: '"' '"'` becomes `quotes:"\"" "\""`. For old targets, lower or duplicate supported forms such as `:is` to `:-webkit-any`/`:-moz-any`, `:dir` to language/direction fallbacks, and placeholder/fullscreen/autofill/any-link/read-only/selection/file-button/backdrop selectors to required vendor spellings. Invalid selector structure is fatal unless recovery is enabled.

## Spec 14

Recognized top-level and nested at-rules include `@charset`, `@import`, `@namespace`, `@media`, `@supports`, `@container`, `@custom-media`, `@layer`, `@scope`, `@starting-style`, `@view-transition`, `@keyframes` and vendor variants, `@font-face`, `@font-feature-values`, `@font-palette-values`, `@counter-style`, `@property`, `@page` and margin-box rules, `@viewport`, and `@-moz-document`. Preserve valid unknown at-rules and descriptors.

Strip `@charset` when it begins at byte zero; for example, `@charset "utf-8";a{color:red}` succeeds and emits only the rule. A UTF-8 BOM is not stripped: it is preserved before an ordinary first rule. Consequently, the exact stdin bytes BOM + `@charset "utf-8";/*ordinary*/a{color:red}b{color:blue}` do not recognize `@charset` in the byte-zero position. They abort with SIGABRT (shell status 134; subprocess return code -6), empty stdout, and a panic containing `UnexpectedToken(AtKeyword("charset"))` at line 0, column 2. Enforce that imports precede ordinary rules and namespaces occur in their permitted prefix region. Every `@import` URL prelude is canonicalized to a double-quoted string: `url('single-quoted.css')`, `url("double-quoted.css")`, and `url(unquoted.css)` become `"single-quoted.css"`, `"double-quoted.css"`, and `"unquoted.css"`. Canonicalize declarations, empty-block handling, nested formatting, and minified whitespace. Empty constructs may become statements or disappear only according to their semantics (for example, an empty named layer may become a layer statement, while an empty supports block is removable).

## Spec 15

Media queries accept media types and `not`/`only`, comma lists, boolean/discrete/range features, `and`/`or`/`not`, nested parentheses, aspect ratios, resolution units, viewport/device/color/display/scan/update/grid/monochrome/forced-colors/inverted-colors, hover/pointer, preferences, orientation, overflow and other modern features. Canonical output uses range syntax where supported, e.g. `min-width: 10px` becomes `(width >= 10px)`, and simplifies whitespace and zero values. For older targets, lower one-sided and interval comparisons to legacy `min-`/`max-` feature tests, using boolean negation where needed to preserve a strict boundary. In particular, with `--targets=safari 8`, `@media (10px < width <= 20px){a{color:red}}` begins exactly `@media (not (max-width: 10px)) and (max-width: 20px) {`: the strict lower bound is a negated `max-width` test rather than a `min-width` test, and the inclusive upper bound is `max-width`.

`@custom-media --name query` definitions and their uses parse even without a flag. `--custom-media` explicitly enables processing and supports multiple, nested and compound definitions. When it is combined with explicit targets, definitions are removed and references are expanded: a definition `@custom-media --foo print;` followed by `@media (--foo) { .a { color: red; } }`, run with `--custom-media --targets 'last 1 Chrome version'`, serializes as an `@media print` block and does not retain either `--foo` occurrence. Otherwise definitions and references must remain valid, and range syntax receives normal canonicalization.

An empty media-query list is canonicalized to `not all`, so `@media { .empty { color: red; } }` begins `@media not all {` in pretty output.

## Spec 16

Container queries support optional container names, width/height/inline-size/block-size and aspect/orientation features, range and interval syntax, container units, `and`/`or`/`not`, nested conditions, and `style(--property)` queries with or without a value. Support `container-name`, `container-type`, and the `container` shorthand, multiple names, nested containers, containers containing media rules and vice versa, empty/name-only conditions, large values, min/max legacy feature spellings, and minified normalization. In pretty output a ratio's slash has one space on each side, so the feature is serialized as `(aspect-ratio > 16 / 9)`, not `(aspect-ratio > 16/9)`.

Cascade and conditional constructs support named, dotted, nested and anonymous `@layer` statements/blocks; `@supports` declarations, selectors, functions and arbitrary nested boolean conditions; `@scope` with optional start/end selectors; nested `@starting-style`; and view-transition descriptors and selectors. A supports declaration for a vendor-prefixed property receives one additional parentheses pair, e.g. `@supports (-webkit-appearance: none)` becomes `@supports ((-webkit-appearance: none))`. Around a complete boolean supports expression, redundant outer parentheses are removed: `@supports (((display: grid) and (gap: 10px)) or ((display: flex) and (flex-wrap: wrap)))` becomes `@supports ((display: grid) and (gap: 10px)) or ((display: flex) and (flex-wrap: wrap))`. Merge repeated named layers or statements only when semantics permit, and never merge distinct anonymous layers. An ordering statement such as `@layer reset, base, components, utilities;` is removed when the immediately represented named layer blocks subsequently establish that same order. Inside `@view-transition`, retain the recognized `navigation` and `types` descriptors but discard custom-property declarations such as `--custom-duration: 0.5s`.

## Spec 17

CSS nesting is parsed in declarations and nested rules, including `&`, nested selector lists, nested at-rules, and implicit descendant nesting where valid. With modern/no targets, canonical output retains supported nesting. In particular, an explicitly written descendant selector `& .child` remains `& .child`; the serializer does not omit the explicit leading `&` in favor of `.child`. When selected targets lack nesting, flatten it to equivalent selectors, preserving parent selector substitution, pseudo/combinator placement, specificity, conditional blocks, modules renaming, and order. The accepted legacy `--nesting` switch explicitly enables this lowering when used with targets (for example, `--targets=defaults --nesting` must expand `.foo { & > .bar {...} }` to a `.foo > .bar` rule). A nested rule that syntactically requires `&` but omits it is an error. Nesting lowering composes with media-query, color, logical-property, module, bundling, minify, and prefix transformations.

## Spec 18

Typed declaration processing covers the CSS-wide keyword and complete common grammars of backgrounds, borders, sizing, box model, display, positioning, overflow, flex, grid, alignment, fonts, text, lists, tables, columns, generated content/counters/quotes, animation, transition, transforms, filters, masking/clipping, containment, scrolling, UI, SVG presentation, and printing. Unknown properties remain printable rather than being discarded.

Within each family, parse both longhands and shorthands; normalize component order and defaults; combine compatible static longhands; expand a shorthand when required for target lowering; respect intervening declarations and `!important`; remove earlier ordinary declarations that are simply overridden by a later value of the same recognized property; and preserve intentional fallback chains and invalid-but-tokenizable unknown values. Thus `color: red; color: blue; color: green; background: yellow; background: orange` becomes only `color: green; background: orange`, including in pretty output. One-, two-, three-, and four-side compression follows top/right/bottom/left equivalence. As a required exception, adjacent `padding-top`, `padding-right`, `padding-bottom`, and `padding-left` whose respective values are `env(safe-area-inset-top)`, `env(safe-area-inset-right)`, `env(safe-area-inset-bottom)`, and `env(safe-area-inset-left)` remain four longhands rather than becoming `padding`.

Unknown declarations are ordering barriers: `.test { color: red; invalid-property: value; background: blue; }` serializes in that order (with `blue` canonicalized to `#00f`), rather than moving `background` across the unknown declaration. `all` likewise retains its source position relative to important declarations, so `all: initial` remains before following `color: red !important` and `background: blue !important`. Ordinary style rules with no surviving declarations or nested rules are removed in pretty as well as minified output; two empty rules produce no CSS bytes apart from stdout's normal print newlines.

Independent recognized declarations also have deterministic family ordering. The exact mixed ordinary/important sequence `color`, `width`, `margin`, `background !important`, `padding !important`, `display !important` remains in that order in pretty and minified output. `gap` precedes `display` after canonical ordering, including `.grid{gap:10px;display:grid}` inside minified `@supports`. In the respective tested rule bodies, canonical order is `transition` before `animation`, `min-height` before `padding`, `grid-template-columns` before `display`, and `font-family`, `font-size`, `font-style`, `font-weight`, `line-height` in that order.

## Spec 19

Background and border processing includes every background layer component, color/image/position/size/repeat/attachment/origin/clip, edge-offset positions, multiple layers, `background-clip:text`, all side/block/inline borders, styles/widths/colors, elliptical radii, `border-image` source/slice/width/outset/repeat, box shadows, outlines, and current/transparent colors. Normalize shorthands, default values, side equality, zero, calc, percentages and unitless border-image numbers. The canonical background shorthand puts its color first, followed by image, position/size, repeat, attachment, origin, and clip; for example, `url('image.png') center / cover no-repeat fixed padding-box content-box red` becomes `red url("image.png") center / cover no-repeat fixed padding-box content-box`. Preserve cascade order when a shorthand and a side-specific declaration interact. Add legacy prefixes for border radius, shadow, sizing, image and background features at the tested old-browser boundaries.

## Spec 20

Box/layout declarations include width/height and logical/min/max variants; intrinsic `min-content`, `max-content`, `fit-content`, `stretch`/fill-available spellings; margin/padding and logical/scroll variants; box sizing; aspect ratio; object fit/position; display multi-keyword and legacy values; position and inset physical/logical shorthands; float/clear logical values; z-index; overflow x/y/two-value/clip; visibility; containment/content-visibility; columns; tables; resize; scroll behavior, snapping, margins/padding and overscroll.

Lower logical properties to physical declarations for old targets while accounting for direction and preserving value/cascade semantics. Lower two-value overflow, multi-value display, intrinsic sizing, sticky positioning, and other unsupported forms where needed. Optimize equal inset/overflow/side values and retain negative, percentage, calc, auto, mixed-unit, extreme and `!important` cases. Positioning declarations use the observed canonical order: `position`, `top`, `left`; `position`, `bottom`, `right`; and `z-index`, `position` for the respective inputs `.a { position: relative; top: 10px; left: 20px }`, `.b { position: absolute; right: 5%; bottom: 10% }`, and `.c { position: fixed; z-index: 100 }`. When all three are present, `.e { position: sticky; top: 10px; z-index: 100 }` minifies exactly to `.e{z-index:100;position:sticky;top:10px}`. The same ordering rules apply in pretty output.

## Spec 21

Flexbox, grid, gap, and alignment are fully typed. Flex support includes all display modes, direction, wrap/flow, grow/shrink/basis/shorthand, order and item/container alignment. Grid support includes templates, track lists and line names, areas and dot cells, `repeat`, `minmax`, `fit-content`, subgrid, auto tracks/flow, gaps, row/column/area placement, `span`, negative/numeric/Unicode escaped names, and template/grid shorthands.

Alignment supports `align-*`, `justify-*`, `place-content/items/self`, baseline, normal/stretch, start/end/self/flex/left/right/center, space distributions, safe/unsafe overflow positions and legacy values. Merge place/gap/grid shorthands only under their special equality/default rules. For old WebKit 2009 flex and IE 10/11 syntaxes, emit appropriate `-webkit-box-*`, `-webkit-flex-*`, `-ms-flex-*`, and `-ms-grid-*` fallbacks before standard declarations. Do not incorrectly apply container alignment transforms to flex items.

For `justify-items`, the canonical order of the two legacy-position tokens is `legacy` followed by the position. Inputs `left legacy`, `right legacy`, and `center legacy` therefore serialize as `legacy left`, `legacy right`, and `legacy center` respectively, in pretty and minified modes.

Grid track lists use a compact line-name boundary even in pretty output: the first line-name bracket is followed by one space, but each later bracket directly follows the preceding track size. Thus `[header] 100px [content] auto [footer] 50px` becomes `[header] 100px[content] auto[footer] 50px`, and `[first] 100px [line1 line2 line3] 200px [last]` becomes `[first] 100px[line1 line2 line3] 200px[last]`. When both are present, `grid-template-rows` precedes `grid-template-columns`. Compatible `grid-row` and `grid-column` declarations combine to `grid-area`.

A `grid-template` shorthand containing areas is split across aligned continuation lines. The value `"header header" 100px "sidebar content" auto "footer footer" 50px / 200px 1fr` is printed exactly as:

```css
grid-template: "header header" 100px
               "sidebar content"
               "footer footer" 50px
               / 200px 1fr;
```

## Spec 22

Transforms support all 2D/3D translate, scale, rotate, skew, matrix and perspective functions; individual `translate`, `rotate`, and `scale`; transform box/origin/style; perspective origin; and backface visibility. Normalize zero axes, unitless zeros, angles, identities, 2D-detectable matrices, precision and function spellings. A serialized transform function list has no whitespace between adjacent functions even in pretty output: `translateX(10px) rotate(45deg) scale(1.5)` becomes `translateX(10px)rotate(45deg)scale(1.5)`. In minified transform arguments, `scale(0.123456789, 0.987654321)` becomes `scale(.123457,.987654)`, while `matrix(1.123456789, 0, 0, 1.987654321, 10, 20)` becomes `matrix(1.12346,0,0,1.98765,10,20)`; `.001px`, `.0001px`, and `.0001deg` remain at those precisions.

For `matrix3d`, values at and below a few millionths are not blanket-rounded away: `.000001`, `.000004`, and `.000003` remain. Components `1.000001`, `1.000002`, and `1.000003` in an otherwise identity matrix normalize to `1`, but a matrix containing `.99999`, `.00001`, and `-.00001` retains those values. Large scale/translation components `100`, `200`, `300`, `1000`, `2000`, and `3000`, and perspective `-.000001`, are retained. In minified mode, combine, multiply, decompose, or choose matrices/component functions only when shorter and equivalent, preserving order; handle determinant/inverse/transpose-related matrix edge cases and calc/var values conservatively. Emit WebKit/Mozilla/Opera prefixes and prefixed keyframe declarations for the selected target versions.

Filters and visual effects include all filter functions, multiple filters, `filter`, `backdrop-filter`, opacity, box/text shadows, blend modes and isolation. Clip syntax includes legacy `rect()` and basic shapes (`circle`, `ellipse`, `polygon`, `inset` with radius and positions) in `clip-path` and shape properties.

## Spec 23

Animation processing includes `@keyframes` and vendor variants, Unicode/escaped/quoted/reserved names, `from`/`to` and decimal percentages, duplicate/empty steps, timeline range selectors, all animation longhands, the animation shorthand, comma-separated lists, iteration counts, directions, fill modes, play states, timing functions, composition, timelines (`scroll()`/`view()` and dashed names), and range start/end/shorthand. Transition processing likewise supports all longhands/shorthand, multiple/cycled lists, custom-property names, positive/negative delay, seconds/milliseconds, `none`/`all`, and all easing functions.

Canonicalize `from`/`to`, percentages, times, timing equivalents, default components and safe longhand-to-shorthand combinations. Transition defaults are printed explicitly in two required cases: `transition-timing-function: steps(5)` becomes `transition-timing-function: steps(5, end)`, and `transition: ease-in-out` becomes `transition: all ease-in-out`. In the canonical animation shorthand, duration precedes the animation name. This remains true after CSS-module scoping and in minified output: an input shorthand with `fadeIn 1s, slideUp .5s` serializes with `1s` before the generated `fadeIn` name and `.5s` before the generated `slideUp` name. Prefixed and unprefixed animation declarations both use that duration-before-generated-name order. Quote animation names that collide with CSS-wide or shorthand keywords. An animation shorthand resets range-related values as CSS semantics require. Emit prefixed keyframes/properties for old targets and keep prefix order. `!important` inside keyframes is handled according to parser semantics without corrupting other declarations. Independent declarations inside a keyframe step retain source order; in particular, `opacity`, `color`, and `transform`, each marked `!important`, serialize in that order.

## Spec 24

Font/text support includes font family quoting and generic/system families; all font size, weight, stretch, style/oblique range, line-height, variant longhands/shorthand and the `font` shorthand; `@font-face` sources/local/format/tech, display, Unicode ranges and descriptor ranges; every `@font-feature-values` block and integer list; and `@font-palette-values`, base palettes and override colors. Merge compatible duplicate feature-value rules and reject invalid generic palette families or invalid descriptor values unless recovery applies. Safe quotes are removed from a multiword family in the `@font-feature-values` prelude, so `"Font Three"` is emitted as `Font Three`.

Nested blocks inside `@font-feature-values` are a deliberate exception to the general pretty indentation and brace-spacing rules. Their at-keyword begins flush-left, `{` immediately follows the block name, their declarations have two spaces of indentation, and both their closing brace and the enclosing rule's closing brace are flush-left. There are no blank lines between sibling feature blocks. For example:

```css
@font-feature-values Font1 {
@stylistic{
  style1: 1;
  style2: 2;
}
}
```

An empty feature block is correspondingly printed as `@stylistic{` followed immediately on the next line by `}`.

Text includes alignment/last/justify, transform, indent flags, decoration line/style/color/thickness/skip-ink and shorthand, emphasis style/position/color, shadow, spacing, white-space, word/line breaking/wrapping, hyphenation, direction/writing modes/orientation, tab size, overflow, rendering, and text-size adjustment. Canonicalize keyword case, defaults, shorthands and calc values and generate `-webkit-`, `-moz-`, `-ms-`, or `-o-` forms at the tested target boundaries.

## Spec 25

Lists and generated content support all standard and international `list-style-type` keywords, custom counter identifiers and quoted marker strings, `symbols()`, position, image and the `list-style` shorthand, including ambiguity among `none` components. Support `@counter-style`, counter reset/increment/set, `content`, strings, quotes, and system colors. Canonicalize and combine list shorthands/defaults without changing a custom identifier, CSS-module reference, old-browser behavior, or image fallback.

Paged media supports named pages and `:first`, `:left`, `:right`, `:blank` combinations; page selector lists; size keywords, dimensions and orientation; margins; all page margin-box at-rules; content/counters; widows/orphans; legacy page-break and modern break properties.

`@page` has a page-specific stable ordering algorithm rather than the general declaration reordering from Specs 6 and 18. Collect declarations that were interspersed with margin boxes, put all non-`!important` declarations first and all `!important` declarations second, and preserve source order within each group. Then append every margin-box rule in source order. Thus `margin: 1in; @top-left {...} size: A4; @bottom-right {...} orphans: 2` orders the declarations as `margin`, `size`, `orphans`, followed by `@top-left` and `@bottom-right`; `margin-top: 1in; margin-bottom: 2in !important; size: A4 !important; orphans: 2` orders them as `margin-top`, `orphans`, `margin-bottom !important`, `size !important`. Four individual `margin-top`, `margin-right`, `margin-bottom`, and `margin-left` declarations remain four longhands in source order rather than combining into `margin`, including mixed values `2cm`, `1in`, `20mm`, and `.5in`.

Declarations inside a page margin box retain source order while their values are canonicalized. For example, `content`, `font-size`, `color`, `text-align` remain in that order, and `content`, `margin`, `padding`, `border` remain in that order. Pretty output places one blank line between the page's declarations and its first margin box and between each pair of sibling margin boxes; when there are no page declarations, the first margin box immediately follows the opening line. An empty margin box is printed with a whitespace-only line containing four spaces between its braces: `@top-left {\n    \n  }`. Minified output applies the same stable ordering without blank lines; the interspersed example above is exactly `@page{margin:1in;size:A4;orphans:2;@top-left{content:"A"}@bottom-right{content:"B"}}`. For `size: A4`, `margin: 1in !important`, and one top-left box, minified output is exactly `@page{size:A4;margin:1in!important;@top-left{content:"Title"}}`. Duplicate rules and descriptor ordering must otherwise remain semantically correct.

## Spec 26

Masking supports standard and `-webkit-` mask image, mode/source-type, repeat, position, size, origin, clip, composite, multiple layers and shorthand; mask-border source/slice/width/outset/repeat/shorthand; mask type; URL fragments; gradients; geometry boxes; calc, percentages and mixed units. Collapse longhands and elide defaults safely and translate standard mask composite/mode concepts to WebKit spellings where required. Support clip paths and all basic-shape variations. For old Safari/Chrome/Edge targets, emit complete prefixed declarations in fallback-first order.

SVG presentation processing includes fill, stroke, opacity, rules, linecap/join, width/miter/dasharray/dashoffset, markers, interpolation, rendering hints, context-fill/stroke, URL-plus-color fallbacks, modern color fallbacks, CSS-wide values, variables, selectors, media/supports/layers/nesting and keyframes. Normalize numeric precision, zero, dash arrays, URLs and colors without dropping SVG-specific values. In minified adjacent rules, `stroke-width: 0` and `stroke-width: 0px` normalize to the same value and their selectors merge, but an immediately following `stroke-width: 0em` remains a separate rule even though it also serializes as `0`: the exact result is `.zero1,.zero2{stroke-width:0}.zero3{stroke-width:0}`.

## Spec 27

UI and miscellaneous properties include every predefined/custom-image cursor with hotspot coordinates and fallbacks; caret color/shape/shorthand; user-select; accent-color; appearance including legacy vendor values; resize; pointer events; touch/action interaction values; color-scheme; forced-color-adjust; print-color-adjust; will-change; all property; image rendering; object and overflow behavior; and common vendor properties. Parse values case-insensitively where CSS requires it, normalize but do not invent values, and generate target-specific user-select/appearance/caret/color/print prefixes and color fallbacks.

## Spec 28

Custom properties beginning `--` retain their token-stream semantics, including significant internal whitespace when required, empty values, comments, strings, brackets, commas, Unicode/emoji and escaped names, URLs, gradients, filters, transforms, grids, cycles, self references and deep nested fallbacks. In pretty output an entirely empty value is printed as `--empty: ;`; a value containing two whitespace characters remains `--space:  ;`, and significant internal whitespace such as `val   ue` remains unchanged. Leading and trailing whitespace around a nonempty token stream is normalized. `var()` and `env()` accept nested functions, commas, indices, safe-area names, custom dashed names, and fallbacks. Ordinary minification may remove dispensable token whitespace but must never concatenate tokens or alter fallback parsing. Custom properties work inside media/container/supports queries, `@property`, layers, keyframes and every typed shorthand.

Canonicalization still applies inside an untyped custom-property token stream where the tokens are independently recognizable. Remove an optional unary plus from a positive dimension (`+10px` becomes `10px`). Decode unnecessary identifier escapes consistently in both declarations and references (`--prop\-with\-escape` becomes `--prop-with-escape`, and `--\000031st` becomes `--1st`). Canonicalize constant colors: `#ff0000` and `rgb(255, 0, 0)` become `red`, `rgba(0, 0, 255, 0.5)` becomes `#0000ff80`, `hsl(120, 100%, 50%)` becomes `#0f0`, `hwb(180 0% 0%)` becomes `#0ff`, and `2px 2px 4px rgba(0, 0, 0, 0.5)` becomes `2px 2px 4px #00000080`. These conversions also occur with `--minify`; URL quoting follows Spec 12.

Custom-property declarations retain source order and their position relative to ordinary declarations. They are ordering barriers for typed-property reordering: declarations of `--a`, `--b`, and `--c` remain before a later declaration that consumes them with `var()`, including cyclic references, fallbacks, and `calc()` consumers. The same rule preserves a custom value such as `--combined: var(--a) var(--b, fallback) var(--c)` before a following `color: var(--combined)`. Ordinary declarations whose values contain unresolved `var()` calls also retain their source order relative to one another; for example, `width: calc(var(--a) + var(--b))`, `height: calc((var(--a) + var(--b)) / 2)`, and `opacity: calc(var(--c))` serialize in that order.

For `var()` and `env()` calls in pretty output, whitespace surrounding a fallback is normalized to exactly one space after the separating comma and none before `)`. Thus both `var(--undefined,    red   )` and `var(--undefined,red)` become `var(--undefined, red)`. An earlier declaration of a custom property is removed when a later declaration of the same property simply overrides it, including `--size: 10px` followed by `--size: calc(var(--size) * 2)`; the self-referential later declaration remains.

`@property` parses a dashed name and descriptors `syntax`, `inherits`, and `initial-value`. The `syntax` string supports `*`, literal identifiers, angle-bracket component types, `|`, `||`, and `+`/`#` multipliers with canonical whitespace. Component-type names are case-insensitive and serialize lowercase, so `syntax: "<LENGTH>"` becomes `syntax: "<length>"`. It diagnoses empty syntax, unmatched angle brackets, unknown types, illegal/doubled/mixed multipliers, leading/trailing operators and invalid universal combinations.

## Spec 29

`-t QUERY`/`--targets QUERY` accepts case-insensitive Browserslist-style target expressions: comma-separated browser/version items, whitespace around commas, major and major.minor versions, comparison ranges such as `safari >= 8`, coverage queries such as `> 0.5%`/`>= 0.25%`, browser-specific forms such as `last 1 Chrome version`, browserless forms such as `last 2 versions`, and `defaults`. Thus `-t '> 0.5%, last 2 versions'` succeeds. Supported names include Chrome, Firefox, Safari, iOS Safari (`ios_saf`), Edge, IE, Opera, Android browser and Samsung Internet. A comma/valid query list forms a union of compatibility needs. Patch versions such as `chrome 30.1.2`, malformed concatenations such as `chrome58`, absent versions such as bare `abc`, and malformed lists fail.

The exact failure mode for `/workspace/executable --targets abc` is stdout empty, status 134, and a Rust panic on stderr containing `panicked at`, `called \`Result::unwrap()\` on an \`Err\` value`, and `Nom("")`. This invocation must not be replaced by a clean status-1 `Invalid target query` diagnostic.

Targets govern syntax lowering, prefix insertion/removal, and fallback values. Modern targets retain modern syntax and remove unnecessary obsolete prefixes; older targets get every form needed by any selected browser plus the standard declaration when applicable. No explicit targets means the default capability profile and must not gratuitously add legacy prefixes.

## Spec 30

Vendor compatibility is data-driven by browser and version, not a blanket prefixer. It covers `-webkit-`, `-moz-`, `-ms-`, and `-o-` variants for flexbox (including 2009/2012 syntaxes), grid, transforms, transitions, animations/keyframes, gradients, image-set, intrinsic sizing, sticky, appearance, user-select, masking/clip/filter/backdrop, border radius/shadow/box sizing/image, columns, hyphens, text decoration/emphasis/size/align/tab/overflow, writing mode, print color adjustment, and selector pseudos.

Required prefixed forms precede the unprefixed form; existing useful prefixes are deduplicated, obsolete prefixes are removed for modern targets, and declarations that intentionally differ are preserved. Version boundaries matter, including Safari 4–16+, Chrome 4–123+, Firefox 2–103+, IE 6/10/11, old Opera, iOS/Android and Edge. Multi-browser output is the union of required compatible representations, while syntax lowering decisions must remain valid for the least capable selected target.

For `--targets "chrome 100, safari 16, firefox 100"`, a rule containing `tab-size: 4`, `appearance: none`, `user-select: none`, and `text-size-adjust: 100%` serializes in exactly these declaration forms and order: unprefixed `tab-size`, unprefixed `appearance`, `-webkit-user-select` then `user-select`, and `-moz-text-size-adjust` then `text-size-adjust`. It has no prefixed `tab-size` or `appearance`. Separately, `user-select: none` targeted to Firefox 68 emits `-moz-user-select: none` before the standard declaration, while Firefox 69 emits only the standard declaration.

## Spec 31

Compatibility lowering additionally covers modern colors and notation, nesting, logical properties, media ranges, double-position gradients, `clamp`, newer math functions, two-value overflow, place-* alignment, multi-value display, system-ui fallbacks, hex alpha, modern rgb/hsl syntax, `hwb`, `color-mix`, `light-dark`, conic gradients, image-set and selected selectors. Lowering produces equivalent older syntax/declarations, often alongside the original behind appropriate fallback ordering, and must compose when several features occur in one declaration/rule or inside nested media/supports/keyframes.

For a modern target such as `chrome 120`, do not lower supported logical properties, nesting, alignment, or `image-set`. Canonical modern output nevertheless applies normal serialization: `align-items: center; justify-items: center` combines to `place-items: center`; the logical declarations `inset-inline-start`, `inline-size`, `border-start-start-radius`, and `text-align` serialize in the order `text-align`, `border-start-start-radius`, `inline-size`, `inset-inline-start`; and `image-set` uses the unprefixed, unpadded-parenthesis form from Spec 12.

Logical-to-physical lowering covers margin, padding, inset, size, border sides/radii and text alignment. Use the applicable writing direction and emit selectors/declarations required for both directions if necessary. Modern browsers must not receive these expansions. Media interval lowering, colors inside gradients, nesting containing logical values, and flex/grid declarations containing lowered values are all processed recursively.

## Spec 32

`--browserslist` obtains targets from the process environment and current-directory configuration. Highest precedence is `BROWSERSLIST` containing a query. Next, `BROWSERSLIST_CONFIG` names an explicit config file; a missing path is fatal and mentions a panic or `FailedToReadConfig`. Otherwise discover, walking from the current directory as appropriate, files named `browserslist` or `.browserslistrc`, or a `browserslist` field in `package.json`. Accept a string, array, or environment-keyed object/config sections.

Choose a section using `BROWSERSLIST_ENV`, then `NODE_ENV`, then the default section/profile. Plain line files ignore blank/comment lines. Apply resolved targets exactly as `--targets` would. `BROWSERSLIST` overrides discovered `package.json`. In a clean directory with no configuration, use Browserslist defaults. The option remains mutually exclusive with `--targets`.

## Spec 33

`--css-modules` enables local scoping of class and ID selectors and locally scoped custom identifiers. Rename definitions and every matching reference consistently for classes, IDs, keyframes/animation names, grid line and area names, counter styles, container names and view-transition names. `:local`/`:local(...)` forces local scope and `:global`/`:global(...)` preserves global names through compound, comma, pseudo, attribute and nested selectors. Unicode local names remain recognizable within generated names.

The export map is keyed by each original local name. Each value has at least `{ "name": STRING, "composes": ARRAY, "isReferenced": BOOLEAN }`. `name` is the generated identifier; `composes` records local, global, and `from "file"` composition entries without duplicates; `isReferenced` distinguishes identifiers such as referenced keyframes. The nonstandard `composes` declaration is removed from CSS after validation. Reject composition from an ID or complex selector, invalid deprecated `@value`, and other invalid module constructs. Composition from an ID, such as `#foo { composes: bar; }`, leaves stdout empty, exits with status 134, and emits a Rust panic on stderr containing `called \`Result::unwrap()\` on an \`Err\` value` and `InvalidComposesSelector`. Scoping an animation name does not change the animation component order from Spec 23: pretty and minified output place each duration before its generated scoped name. With targets and minification, `.box { display: flex; gap: 1rem; }` likewise emits the scoped rule body `{gap:1rem;display:flex}`.

## Spec 34

The default generated module pattern is `[hash]_[local]`. The hash is a deterministic six-character, URL-safe identifier derived from source identity; prefix a leading underscore if its first character would be a digit. In the compatibility profile defined here, a source named `test.css` has hash `EgL3uq`, so local `foo` is `EgL3uq_foo`; `[name]-[hash]-[local]` yields `test-EgL3uq-foo`. `--css-modules-pattern PATTERN` replaces the default. Supported placeholders are `[name]` (source basename with the final extension removed and internal dots changed to hyphens), `[local]`, and `[hash]`, interspersed with literal text and in any order. `[local]_[hash]` starts each class with its original name; `[hash]` alone gives all locals in the same source file the same filename-derived hash. Unknown placeholders fail with `Error parsing CSS modules pattern: unknown placeholder "[invalid]" at index 0`; an unmatched `[` fails with `Error parsing CSS modules pattern: unclosed brackets at index 0`. Other malformed patterns are likewise nonzero.

`--css-modules-dashed-idents` additionally scopes dashed identifiers, especially custom-property declarations and all `var()` references, consistently. Without it, custom-property spelling is unchanged. Module renaming composes with targets, prefixes, nesting, keyframes, minification, maps, bundling and multiple input files.

## Spec 35

When modules are enabled and CSS is otherwise destined for stdout, stdout is one JSON document with exactly top-level keys `code` and `exports`: `code` is the serialized CSS string including its normal terminal newline and `exports` is the map described above. Do not print raw CSS separately. When CSS is written with `-o`, write only CSS there and write exports to the explicit path supplied as `--css-modules=PATH`, or otherwise to the output CSS path with its extension replaced by `.json` (for example `output.css` produces `output.json`). Directory mode similarly produces `a.css` and `a.json` for `a.css`. Empty module CSS produces `{}` exports. Every destination directory must already exist; module output does not create missing directories. If the CSS output's parent exists but an explicit export path's parent does not, the CSS file is written first, then the command exits 1 with empty stdout and `Error: Os { code: 2, kind: NotFound, message: "No such file or directory" }\n`, without creating the export parent. Keep per-file exports separate.

## Spec 36

`--bundle` resolves local `@import` rules recursively relative to the importing file and replaces them with imported CSS in correct cascade order. Accept quoted strings and `url()` import syntax, `.`/`..` traversal, deep chains, empty/comment-only files, and cycles. Deduplicate a dependency reached repeatedly under equivalent conditions and terminate circular/diamond graphs without duplicating content. Preserve URL text in imported declarations. Network, absolute URL, and data URL imports are not preserved and are never fetched: resolution fails. A missing local import and an import such as `https://example.com/styles.css` both leave stdout empty, exit with status 134, and emit a Rust panic on stderr containing `panicked at`, `called \`Result::unwrap()\` on an \`Err\` value`, `ResolverError`, and `No such file or directory`.

Strip imported `@charset`. An import media condition wraps/combines content in `@media`; `supports(...)` becomes/combines `@supports`; `layer`, `layer(name)`, parent layers and nested layer names become correctly ordered/named `@layer` blocks/statements. Combine inherited and child media/supports conditions with semantic `and`, prepend parent layer names, and preserve orientation and complex boolean conditions. Incompatible media combinations and conflicts among named/anonymous layers or differing conditions for the same dependency are fatal rather than silently changing semantics. Bundling works with output files/directories, targets, nesting, modules, minification and source maps.

## Spec 37

`--sourcemap` requires `--output-file` or `--output-dir`; otherwise command-line validation fails and identifies the missing `OUTPUT_FILE` and `OUTPUT_DIR` alternatives. For every CSS output, create a sibling whose path is the complete CSS output path plus `.map` (for example `out.css.map`). Append a CSS source-map comment that names the generated map path; output-file mode uses the actual map path expected by the CLI.

The map is valid source-map-v3 JSON containing `version: 3`, a nonempty VLQ `mappings` string when there is generated content, arrays `sources`, `sourcesContent`, and `names`, and a `file` value identifying the CSS output basename where present. `sources` and `sourcesContent` have equal lengths, include original source text and paths, handle spaces/special characters and relative paths, and include every contributing file in bundled order. Empty inputs still yield a valid map. Mappings track pretty and minified output, vendor/generated fallbacks and recovered valid CSS. Multiple directory outputs receive independent maps.

## Spec 38

All flags compose in one pipeline: read/resolve inputs; parse with optional recovery; bundle imports; apply modules scoping; resolve targets; lower unsupported syntax and create fallbacks/prefixes; perform canonical typed optimization; serialize pretty or minified; then emit CSS, exports and maps to the selected destinations. Combining `--minify`, targets or browserslist, `--sourcemap`, `--bundle`, `--css-modules`, `--custom-media`, recovery, output-file and output-directory modes must not disable any other selected behavior. For example, bundling and minifying a dependency containing `.dep { width: 100%; height: 50vh; margin: 0; }` yields `.dep{width:100%;height:50vh;margin:0}` in the bundle. Diagnostics stay on stderr, JSON stdout remains valid, and successful file-output commands leave stdout empty.

## Spec 39

The transformation must be deterministic: the same content, source filename, options, target set and environment produce byte-identical CSS, module names/JSON and source maps across runs. It must preserve the rendered meaning and cascade of valid input while canonicalizing it, including declaration override order, prefixed fallback order, selector specificity, rule/import/layer order, custom-property token boundaries, strings/escapes, URL payloads and Unicode. No test-only lookup tables, fixture-name dispatch, dependence on repository files, nondeterministic hashes, network calls, timestamps or machine-specific absolute paths may affect ordinary CSS output.
