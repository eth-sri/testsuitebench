# Clarified specification for `executable`

The required artifact is one directly runnable program named exactly `executable`. It is a non-interactive command-line utility compatible with i3-style 1.0. All paths and command names below are literal unless described otherwise. The files under `assets/` are normative parts of this specification: they provide the exact built-in theme data, color-name table, and representative byte-exact transformations. No repository source, network service, or other data is available to the implementation.

## Spec 1 — Process and I/O contract

`executable` accepts UTF-8 command-line arguments, reads configuration and theme files from the filesystem, and writes UTF-8. It must never prompt or read stdin. Successful informational, theme-application-to-stdout, and theme-extraction results go to stdout. Diagnostics, parser errors, validation failures, reload failures, and save progress go to stderr except for the deliberately stdout-only missing-theme usage shown in Spec 3.

Ordinary success exits 0. Command-line validation and handled operational errors exit 1. Behaviors described below as a panic exit 101 and emit a diagnostic containing the stated text; source line numbers, thread IDs, and backtrace notes are not otherwise significant. All generated text files and stdout results end in `\n`.

The program must handle empty inputs, UTF-8 comments/directives, paths containing spaces or Unicode, configurations of at least 10,000 lines, and at least 1,000 color directives without truncation, hangs, or fixed-size-buffer failures.

## Spec 2 — Command-line vocabulary and parsing

The interface is:

```text
executable [FLAGS] [OPTIONS] [theme]
```

The positional `theme` is optional at parse time but required for application mode. Exactly these case-sensitive switches exist:

- `-h`, `--help`
- `-V`, `--version`
- `-l`, `--list-all`
- `-r`, `--reload`
- `-s`, `--save`
- `-c FILE`, `--config FILE`, and `--config=FILE`
- `-o FILE`, `--output FILE`, and `--output=FILE`
- `-t [FILE]`, `--to-theme [FILE]`; its effective default value is the empty string

Options may precede or follow the theme. `--` ends option recognition, so its following token is positional even when it starts with `-`. Short boolean options may be clustered, such as `-Vl`, `-lr`, and `-rs`. At most one positional value is accepted. Long option names and built-in theme names are case-sensitive. An empty or whitespace-only positional value is not trimmed into another value.

Each of `config`, `output`, and `to-theme` may occur at most once across its short and long forms. Repetition is a parse error. `config` and `output` require a value; `to-theme` is special and may occur without one. Unknown flags and extra positional arguments are parse errors. Parser errors exit 1, write only to stderr, include an `error:` line, a blank line, a `USAGE:` block, another blank line, and `For more information try --help`.

## Spec 3 — Exact help, version, and missing-theme text

`-h` and `--help` exit 0, write nothing to stderr, and produce exactly:

```text
i3-style 1.0
Make your i3 config a bit more stylish

USAGE:
    executable [FLAGS] [OPTIONS] [theme]

FLAGS:
    -h, --help        Prints help information
    -l, --list-all    Print a list of all available themes
    -r, --reload      Apply the theme by reloading the config
    -s, --save        Set the output file to the path of the input file
    -V, --version     Prints version information

OPTIONS:
    -c, --config <file>      The config file the theme should be applied to. Defaults to the default i3 location.
    -o, --output <file>      Apply the theme, attempt to validate the result, and write it to <file>
    -t, --to-theme <file>    Prints an i3-style theme based on the given config suitable for sharing with others
                             [default: ]

ARGS:
    <theme>    The theme to use
```

The closing code fence represents a final newline, not an extra blank line. `-V` and `--version` similarly exit 0, use stdout only, and print exactly `i3-style 1.0\n`.

An invocation that parses successfully but selects application mode without a theme—including no arguments, `-r`, `-s`, `-o FILE`, or `-c FILE`—exits 1, writes nothing to stderr, and prints exactly:

```text
USAGE:
    executable [FLAGS] [OPTIONS] [theme]

Select a theme as the first argument. Use `--list-all` to see the themes.
```

## Spec 4 — Early-mode precedence

Help and version are parser-level short circuits. If both occur, whichever occurs first in the argument sequence wins (`--version --help` prints only the version; `--help --version` prints only help). Either one takes precedence over list mode, theme application, config lookup, and later invalid arguments. This includes help/list in either order: help wins. Version wins over list in either order. In clustered `-Vl` and `-lV`, version wins.

After those parser-level modes, list mode takes precedence over extraction/application and ignores a supplied positional theme, `--`, reload/save flags, and invalid/nonexistent theme names. Thus `--list-all some-theme` and `--list-all -- --nonexistent` simply list themes. `-lr` also lists themes. Extraction mode is selected next whenever `-t`/`--to-theme` occurs. Otherwise application mode is selected.

## Spec 5 — Exact parser diagnostics

The following common parser failures must use these exact messages (including blank lines and final newline):

```text
error: The argument '--config <file>' requires a value but none was supplied

USAGE:
    executable --config <file> --to-theme <file>

For more information try --help
```

For missing `-o`/`--output`, substitute `--output <file>` in the first line and usage line. A repeated value option uses:

```text
error: The argument '--config <file>' was provided more than once, but cannot be used multiple times

USAGE:
    executable --config <file> --to-theme <file>

For more information try --help
```

Again substitute `--output <file>` for output. For repeated `-t`/`--to-theme`, use `--to-theme <file>` in the first line and the usage is only `    executable --to-theme <file>`.

An unknown argument `X` starts with `error: Found argument 'X' which wasn't expected, or isn't valid in this context`. An extra positional argument uses the same form naming that extra token. Its usage synopsis is the general synopsis from Spec 3. These errors go solely to stderr.

## Spec 6 — Exact built-in theme list

`-l` and `--list-all` exit 0, write nothing to stderr, and produce exactly the following, including the initial blank line, 18-character padded name column, order, descriptions, and final newline:

```text

Available themes:

  slate              - Slate theme by Jody Ribton <jody@ribton.me>
  alphare            - A beige theme by Alphare
  ubuntu             - Ubuntu theme by lasers
  flat-gray          - flat gray based theme
  purple             - Purple theme by AAlakkad <http://aalakkad.me>
  archlinux          - Archlinux theme by okraits <http://okraits.de>
  default            - Default theme for i3wm <http://i3wm.org>
  debian             - Debian theme by lasers
  oceanic-next       - Theme by Valentin Weber inspired by voronianski (https://github.com/voronianski/oceanic-next-color-scheme)
  base16-tomorrow    - Base16 Tomorrow, by Chris Kempson (http://chriskempson.com)
  okraits            - A simple theme by okraits <http://okraits.de>
  icelines           - icelines theme by mbfraga
  solarized          - Solarized theme by lasers
  deep-purple        - Inspired by the Purple and Default themes. By jcpst <http://jcpst.com>
  tomorrow-night-80s - Tomorrow Night 80s theme by jmfurlott <http://jmfurlott.com>
  seti               - seti theme by Jody Ribton - based on the seti Atom theme at https://atom.io/themes/seti-ui
  lime               - Lime theme by wei2912 <http://wei2912.github.io>, based on Archlinux theme by okraits <http://okraits.de>
  gruvbox            - Made by freeware-preacher <https://github.com/freeware-preacher> to match gruvbox by morhetz <https://github.com/morhetz>
  mate               - Theme for blending i3 into MATE
```

## Spec 7 — Config selection and ordering

An explicit `-c`/`--config` path always selects that file. Otherwise, both extraction and application search for the first existing path in this exact order:

1. `$HOME/.i3/config`
2. `$HOME/.config/i3/config`

`HOME` controls the first two paths exactly. Missing candidates are skipped, and directories without a `config` file do not count. If none exists, exit 1, write `Could not find i3 config\n` to stderr, and produce no normal result. An absent `HOME` may terminate nonzero rather than falling back gracefully. Relative explicit paths are resolved against the process working directory.

Config selection occurs before application-theme selection. Consequently, when no config can be found, even an empty, Unicode, very long, or nonexistent theme argument produces the config-not-found error rather than a theme error.

## Spec 8 — Config validation

Before reading, extracting, or theming a selected config, execute the harness-provided command `i3 -C -c CONFIG_PATH`. Discard that command's stdout and stderr. This validates the selected input, not the generated themed result. Do it before loading a custom theme and before creating the requested output file.

If `i3` runs but returns nonzero, exit 1 with exactly:

```text
Could not validate config.
Use `i3 -C -c CONFIG_PATH` to see validation errors.
```

If the command cannot be started, exit 1 with no stdout and a single stderr diagnostic of the form `Could not validate config with `i3 -C -c CONFIG_PATH` (is i3 in the PATH?) SYSTEM_ERROR`. It must contain both `Could not validate config` and `is i3 in the PATH?`.

After successful external validation, filesystem read failures are nonzero errors. Compatibility diagnostics for a missing or directory-valued config should contain `panicked at src/writer.rs`, the OS condition (`No such file or directory` or `kind: IsADirectory`), and may exit 101.

## Spec 9 — Theme schema, loading, and color resolution

In application mode, after config validation, interpret the positional theme case-sensitively. First look for an exact built-in name. If absent, use the positional text as a filesystem path (absolute or relative), supporting spaces, symbols, and Unicode.

A theme is a YAML document with optional `meta.description`, `colors`, `window_colors`, and `bar_colors`. `window_colors` recognizes `focused`, `focused_inactive`, `unfocused`, and `urgent`; each recognizes `border`, `background`, `text`, and `indicator`. `bar_colors` recognizes scalar `separator`, `background`, and `statusline`, plus `focused_workspace`, `active_workspace`, `inactive_workspace`, and `urgent_workspace` groups with the same four component names. Unknown metadata, palette entries, top-level fields, groups, and group component fields are ignored.

A recognized component is present only when its YAML node is a string. A non-string node is silently treated as an absent component; it is not a theme validation error. For example, a focused `border: [bad]` contributes no focused border value, so an existing focused line keeps its original border. Resolve each present string by one lookup in the top-level `colors` map: if it exactly names a string palette entry, use that entry's string; otherwise use the component string literally. Preserve the resolved string's spelling and hex case. Both `#RGB` and `#RRGGBB` are accepted for application. Missing sections, groups, fields, and non-string component nodes remain absent rather than receiving defaults at theme-load time.

If a theme name is neither a built-in nor an existing filesystem path, exit 1 with exactly:

```text
Could not open theme: THEME - No such file or directory (os error 2)
 Use `i3-style --list-all` to see the available themes.
```

Other failures while opening a path use the same two-line wrapper with the operating-system error in place of `No such file or directory (os error 2)`. Malformed YAML panics/exits nonzero and stderr contains `Could not parse yaml for theme`. An empty or comment-only YAML file exits 101 with `index out of bounds`.

A nonempty metadata-only document loads, but application exits 101 with `Option::unwrap()` as soon as transformation needs one of its missing sections. In particular, closing an existing bar colors block or closing a bar that needs a colors block requires `bar_colors`; reaching EOF with any recognized client directive still missing requires `window_colors`. Bytes emitted before that panic remain on stdout or in the temporary output.

## Spec 10 — Normative built-in theme data

[`assets/builtin-themes.txt`](assets/builtin-themes.txt) is the complete authoritative resolved application data for all 19 built-ins. It contains consecutive records headed `===== NAME =====`; the header is a delimiter and is not part of the YAML document that follows it. Each component is already resolved to the exact string the built-in supplies, so use it directly without another palette lookup. An omitted group, scalar, or component is absent. Implement every listed resolved value, absent field, description, capitalization, and spelling exactly.

In particular, implementations must not synthesize similar palettes. Exact transformations are exercised for `default`, `solarized`, `slate`, `purple`, `gruvbox`, `archlinux`, `ubuntu`, and `flat-gray`; every other listed built-in must also load and apply as defined. The list output order is Spec 6's record order, not alphabetical order or filesystem order.

## Spec 11 — Line recognition during theme application

Read the config line by line and emit every processed input line with one terminating `\n`; this adds a newline if the source's last line lacked one. For recognition, trim leading/trailing whitespace, then split on literal space characters while removing empty pieces. Preserve the original leading whitespace for rewritten recognized lines. A blank line or a line whose first token starts with `#` is copied unchanged (apart from newline normalization).

Maintain simple booleans `in_bar` and `in_colors`, not a general i3 parser or brace-depth parser. An active line whose first token is `bar` begins a bar. While in a bar, a first token `colors` begins its colors block. The first active `}` closes colors when `in_colors`; otherwise it closes the bar when `in_bar`. Apply this independently to every encountered bar.

Outside recognized color directives, preserve input order, bytes, whitespace, comments, Unicode, bindings, modes, variables, and structural lines. One compatibility quirk is intentional: an active, unrecognized directive inside a `colors` block is dropped, while comments inside that block are preserved. Rewritten color lines retain their leading indentation but normalize spacing between the directive and emitted components; trailing tokens and inline comments are dropped.

## Spec 12 — Existing bar color blocks

Inside a bar `colors` block, recognize the three scalar keys and four workspace keys from Spec 9. For an existing scalar line, output `INDENT + key + " " + value + "\n"`, using the theme scalar when present or its original first value when absent.

For an existing workspace line, use theme values independently for border, background, and text; an absent theme component preserves the original token in that position. If the entire theme group is absent, preserve the whole original line. After the three primary values, emit a fourth value whenever the original line had a text token (as valid lines do) or the theme has `indicator`: use the theme indicator if present, otherwise repeat the original text token. This historical behavior means a three-color workspace line becomes `new-border new-background new-text old-text`, and a subsequent application can change the fourth component again. Do not model it as preserving an arbitrary original fourth token.

At the closing `}` of an existing colors block, insert each theme-provided scalar not already encountered in order `separator`, `background`, `statusline`. Then insert each missing, complete workspace group in order `focused_workspace`, `active_workspace`, `inactive_workspace`, `urgent_workspace`; a group is complete only if border, background, and text are all present. Insertions use the closing brace's leading whitespace twice as indentation. A generated workspace line has a space after its text and, if an indicator exists, one additional space followed by the indicator. Then emit the original closing brace. Encounter tracking resets for the next bar.

## Spec 13 — Bars without color blocks

If a bar closes without an active colors block having been found, insert immediately before its closing brace:

```text
  colors {
    ...
  }
```

The two- and four-space indentation above is fixed, regardless of the bar's original indentation. Inside it, emit available scalars and complete workspace groups in the same orders and formats as Spec 12. Do not add a bar or bar-colors section when the input contains no bar. Commented-out `bar`, `colors`, and color lines remain comments and do not count as found.

Every actual bar is handled, including empty bars, empty colors blocks, mixed complete/partial bars, and many successive bars. A theme with no `bar_colors` may fail if the input structure requires bar insertion or a colors-block close; partial bar themes, however, simply alter/insert the provided scalars and complete groups and preserve or skip the rest as specified.

## Spec 14 — Window/client color directives

Whenever `in_colors` is false, recognize exactly `client.focused`, `client.focused_inactive`, `client.unfocused`, and `client.urgent`. This recognition is independent of `in_bar`: a client directive inside a bar but outside its colors block is rewritten as a window directive and counts as encountered, so it is not appended again at EOF. A client directive inside an active colors block remains an unrecognized colors-block directive and is dropped under Spec 11.

When an existing recognized client directive has a corresponding theme group, rewrite border and background, choosing the theme component when present and otherwise the original positional token. Emit text when either original text or theme text exists, again preferring theme. After text, emit one space; emit an indicator only if the original had one or the theme supplies one, preferring the theme and otherwise the original. Thus a rewritten three-component line under a group with no indicator ends with a trailing space. If the theme group is absent, preserve the original line verbatim.

At EOF, append any missing directives whose theme groups exist, in this fixed order: focused, focused_inactive, unfocused, urgent. For an appended group, absent border/background/text becomes literal `#000000`; append indicator only when supplied. These lines are unindented. Existing directives remain in their original positions, so only missing directives move to EOF. An empty config therefore becomes only the available appended client lines. A theme lacking a window section may fail when missing client lines need to be appended.

The exact minimal input in [`assets/minimal-config.input`](assets/minimal-config.input), the custom theme in [`assets/custom-test-theme.yaml`](assets/custom-test-theme.yaml), and the exact solarized, custom-theme, and alphare outputs in [`assets/minimal-config-solarized.expected`](assets/minimal-config-solarized.expected), [`assets/minimal-config-testtheme.expected`](assets/minimal-config-testtheme.expected), and [`assets/minimal-config-alphare.expected`](assets/minimal-config-alphare.expected) are normative examples of Specs 11–14. Applying alphare to [`assets/missing-config.input`](assets/missing-config.input) produces [`assets/missing-config-alphare.expected`](assets/missing-config-alphare.expected). Applying purple to [`assets/default-config.input`](assets/default-config.input) produces the normative realistic large output [`assets/default-config-purple.expected`](assets/default-config-purple.expected).

## Spec 15 — Output-to-stdout, output files, and save

In application mode, no `-o` and no `-s` means the transformed config is written to stdout and no save progress line is emitted. `-o PATH` writes the identical bytes to `PATH` instead, replacing an existing regular file. `-s` sets the output path to the selected input config, modifying it in place. If both are present, `-o` wins.

For either file-output form, create a directory `i3-style/RUN_ID` beneath the platform temporary directory, where `RUN_ID` is a dynamically generated decimal integer. First write the transformed config to `config-output` there. Then emit `saving config at INPUT to TEMPDIR/config-input\n` to stderr and copy the original input to that `config-input` backup. Finally copy `config-output` onto the selected output path. The integer need not be predictable, but the two displayed paths must be correct.

Do not create missing parent directories for the requested output. Such an output, or a directory-valued output, fails nonzero after the save message with an OS error containing `No such file or directory` or `kind: IsADirectory`; compatibility output may say `panicked at src/main.rs`. A validation or theme-loading failure must not create the requested output. Paths with existing parents, including long paths and spaces, work normally.

## Spec 16 — Reload behavior

After successful transformation/output handling, `-r`/`--reload` executes one harness-provided command with the sole argument `reload`. If environment variable `WAYLAND_DISPLAY` is present, use `swaymsg reload`; otherwise use `i3-msg reload`. Suppress the command's stdout and stderr. The flag is permitted both with file output/save and stdout output, and transformation/output happens before the reload attempt.

Any successfully started reload process counts as success even if its exit status is nonzero. If it cannot be started, exit 1 and write `Could not reload config with swaymsg: SYSTEM_ERROR\n` or `Could not reload config with i3-msg: SYSTEM_ERROR\n`. In stdout mode the already generated config remains on stdout when this happens. Without `-r`, `WAYLAND_DISPLAY` has no effect.

## Spec 17 — Extraction mode and config parsing

`-t FILE` or `--to-theme FILE` extracts a YAML theme from FILE. If its value is absent or the explicit empty string, use `-c` when present; otherwise use Spec 7 discovery. `-o`, `-s`, a positional theme, and reload do not redirect or replace extraction output. Validate the chosen input per Spec 8, then parse it with the same simple trim/literal-space tokenization and `in_bar`/`in_colors` state transitions as application.

Outside bars, collect recognized client directives. Positional tokens map to border, background, text, and optional indicator. Each occurrence replaces its group's border, background, and text. It replaces indicator only when that occurrence has a fourth component; a later three-component occurrence retains an indicator collected from an earlier occurrence of the same directive.

Within bar colors, collect scalar `separator`, `background`, and `statusline`, and workspace groups `focused_workspace`, `inactive_workspace`, and `urgent_workspace` with border, background, and optional text. A later workspace occurrence replaces border and background but replaces text only when text is present, so an omitted optional text retains an earlier value. Deliberately do not recognize `active_workspace` during extraction. Ignore comments, blanks, other directives, and colors outside those locations. Multiple bars update the same accumulated fields under these per-component rules, so later present components win without clearing previously collected optional components.

An empty or colorless valid config succeeds and produces empty maps. Three-component clients succeed without indicator. A recognized line lacking mandatory positional tokens may panic. Extraction accepts mixed hex case but normalizes palette values to uppercase. Short `#RGB` and non-hex recognized component strings fail nonzero while naming the offending uppercase string, for example `got invalid hex string: "#F00"` or `got invalid hex string: "INCOMPLETE"`.

## Spec 18 — Extracted color naming

Build an insertion-ordered palette from extracted values in this exact traversal order: bar separator, background, statusline; focused workspace components; active workspace components; inactive workspace components; urgent workspace components; then focused, focused_inactive, unfocused, and urgent client components. Component order is border, background, text, indicator. Uppercase each value before adding it, and deduplicate identical uppercase hex values.

For each new `#RRGGBB`, choose the nearest entry from [`assets/html-colors.tsv`](assets/html-colors.tsv) using Euclidean distance in ordinary RGB byte space: `sqrt((r-r2)^2 + (g-g2)^2 + (b-b2)^2)`. The TSV row order is authoritative for deterministic nearest-neighbor ties. Use the lowercase name in column one. If that name already belongs to another hex, append `-1`; if occupied, increment to `-2`, and so on. Exact duplicate hexes reuse their first name. This yields names such as `red`, `red-1`, `red-2` for `#FF0000`, `#FF0001`, and `#FF0002` and similarly suffixed names for close green/blue values.

## Spec 19 — Extracted YAML structure and quirks

Serialize extraction as deterministic YAML with this top-level order: `meta`, `colors`, `window_colors`, `bar_colors`. Begin with `---\n`; set `meta.description` to `AUTOMATICALLY GENERATED THEME`; keep palette insertion order; render palette hex strings double-quoted; and make group values unquoted palette-name references. Empty mappings use `{}`.

Within `window_colors`, output present groups in order focused, focused_inactive, unfocused, urgent and present parts in order border, background, text, indicator. Within `bar_colors`, output present scalars in order background, statusline, separator, then groups focused_workspace, active_workspace, urgent_workspace. Deliberately omit `inactive_workspace` from serialized bar groups even though its colors participated in palette creation. This and the failure to parse active workspace are compatibility quirks.

For the normative minimal input, extraction must be byte-for-byte:

```yaml
---
meta:
  description: AUTOMATICALLY GENERATED THEME
colors:
  crimson: "#DC322F"
  darkslategray: "#002B36"
  steelblue: "#268BD2"
  oldlace: "#FDF6E3"
  olive: "#859900"
  dimgray: "#586E75"
  darkgray: "#93A1A1"
  mediumvioletred: "#D33682"
  darkslategray-1: "#073642"
  antiquewhite: "#EEE8D5"
window_colors:
  focused:
    border: olive
    background: olive
    text: oldlace
  focused_inactive:
    border: darkslategray-1
    background: darkslategray-1
    text: antiquewhite
  unfocused:
    border: darkslategray-1
    background: darkslategray-1
    text: darkgray
  urgent:
    border: mediumvioletred
    background: mediumvioletred
    text: oldlace
bar_colors:
  background: darkslategray
  statusline: steelblue
  separator: crimson
  focused_workspace:
    border: oldlace
    background: olive
  urgent_workspace:
    border: mediumvioletred
    background: mediumvioletred
```

The closing code fence represents exactly one final newline. A colorless config produces exactly:

```yaml
---
meta:
  description: AUTOMATICALLY GENERATED THEME
colors: {}
window_colors: {}
bar_colors: {}
```

## Spec 20 — Determinism and compatibility examples

Repeated invocations with the same arguments, file contents, environment, and successful harness commands produce identical stdout/file content; only save-progress temporary paths may vary. Applying different built-ins must use their genuinely different palettes. Applying one theme to output produced by another replaces recognized colors rather than duplicating client directives. Reapplying a theme follows the workspace-fourth-component quirk in Spec 12; it is not required to be byte-idempotent where that quirk changes the line.

Treat the representative assets as byte-exact outcomes, including color case, directive order, indentation, trailing spaces, and final newlines. They supplement the general rules rather than replacing them. No behavior is assigned to the harness-provided `i3`, `i3-msg`, or `swaymsg` commands; `executable` only invokes them as specified.
