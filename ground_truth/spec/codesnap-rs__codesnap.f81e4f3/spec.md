# CodeSnap executable behavior

The required artifact is one executable file named `executable`. It is a non-interactive, single-command command-line program that creates deterministic code snapshots. All requirements below describe externally observable behavior. Paths are interpreted using the process environment and current working directory.

## Spec 1

The executable implements the CodeSnap CLI identity and lifecycle.

- It is invoked directly as `executable [OPTIONS]`; the name shown in diagnostics and help is `codesnap`.
- It has no subcommands. Bare words such as `add`, `remove`, `delete`, `list`, `show`, `get`, `set`, `create`, `update`, `init`, `config`, `help`, and `version` are unexpected positional arguments, not commands.
- Normal help and version requests terminate without loading configuration or rendering.
- `-V` and `--version` write exactly `codesnap-cli 0.13.1\n` to standard output, write nothing to standard error, and exit 0.
- A successful rendering invocation exits 0. Command-line syntax errors exit 2. Handled runtime/configuration/rendering failures exit 1. The color parser is deliberately fail-fast: a color consumed by an active rendering component but not valid causes an uncaught fatal failure (conventionally exit 101). Structurally malformed values report `Invalid hex color: VALUE` on standard error, while a structurally valid-length value containing non-hex digits fails through the distinct integer-parsing panic described in Spec 16. The ignored `--background` compatibility value is not consumed by that parser; see Spec 17.
- The executable must finish ordinary invocations promptly and must never enter a full-screen or interactive terminal UI.

## Spec 2

The option grammar is the following. Options may generally occur in any order. A scalar option may not be supplied twice; duplicate use is a syntax error saying it `cannot be used multiple times`. A duplicate supplied through a short alias, including one packed into a combined-short token, is identified by the option's canonical long form. For example, `-c hi -cs` exits 2 with empty stdout and starts stderr with `error: the argument '--from-code [<Code>]' cannot be used multiple times`. Paths and values containing spaces work when passed as one argument.

| Option | Value and meaning |
|---|---|
| `-f`, `--from-file FILE` | UTF-8 source file input |
| `-c`, `--from-code [CODE]` | Inline source; absent optional value means `-` and reads stdin |
| `-i`, `--from-image [IMAGE]` | PNG input; absent optional value means `-` and reads raw stdin |
| `--from-clipboard` | Read code text from the system clipboard |
| `-o`, `--output OUTPUT` | Required destination |
| `--silent` | Suppress the normal success message |
| `-e`, `--execute VALUE...` | One or more command strings; repeatable/variadic |
| `--skip` | Do not execute values supplied through `--execute` |
| `--range RANGE` | Select source lines |
| `--code-font-family NAME` | Code font family |
| `--code-theme NAME` | Highlight theme |
| `--has-breadcrumbs BOOL` | Explicit `true` or `false`; default false |
| `--has-line-number` | Enable line numbers |
| `--breadcrumbs-separator TEXT` | Path separator displayed in breadcrumbs |
| `--breadcrumbs-font-family NAME` | Accepted breadcrumb font option |
| `--breadcrumbs-color COLOR` | Breadcrumb color |
| `--start-line-number U32` | First displayed line number |
| `--line-number-color COLOR` | Line-number color, default `#495162` |
| `-d`, `--delete-line RANGE...` | Repeatable deleted-line ranges |
| `--delete-line-color COLOR` | Default `#ff6b6b30` |
| `-a`, `--add-line RANGE...` | Repeatable added-line ranges |
| `--add-line-color COLOR` | Default `#2ecc7130` |
| `--highlight-range RANGE` | One convenience highlight range |
| `--relative-highlight-range` | Interpret convenience/add/delete ranges relative to the selected snippet |
| `--highlight-range-color COLOR` | Default `#ffffff10` |
| `--raw-highlight-lines JSON` | Ordered raw highlight definitions |
| `-l`, `--language LANGUAGE` | Explicit syntax name/token |
| `--file-path PATH` | Filename hint for language detection and breadcrumbs; unresolved syntax detection may inspect this path |
| `-w`, `--watermark TEXT` | Watermark text |
| `--watermark-font-family NAME` | Watermark font |
| `--watermark-color COLOR` | Watermark color |
| `--shadow-radius F32` | Window-shadow blur radius |
| `--shadow-color COLOR` | Window-shadow color |
| `--mac-window-bar BOOL` | Explicit `true` or `false` |
| `--has-border` | Enable the standard border; accepted even when the loaded defaults already enable it |
| `--border-color COLOR` | Border color, default `#ffffff30` |
| `--margin-x F32` | Horizontal background margin on each side |
| `--margin-y F32` | Vertical background margin on each side |
| `--title TEXT` | Window title |
| `--scale-factor U8` | Raster scale, default 3 |
| `--title-font-family NAME` | Title font |
| `--title-color COLOR` | Title color |
| `--background COLOR` | Accepted but ignored compatibility value; see Spec 17 |
| `--type TYPE` | `image` (default) or `ascii` |
| `--config FILE` | Explicit JSON configuration |
| `-h`, `--help` | Summary/full help |

`U8` and `U32` are nonnegative base-10 integer types; floats accept ordinary decimal forms. A separate negative-number token, such as the `-1` following `--scale-factor`, is treated as an unexpected option-like argument. `--` stops option recognition, after which tokens are rejected as unexpected positionals. Unknown long or short flags and partial spellings such as `--out` are errors.

## Spec 3

Help output is stable and distinguishes long help from short help. Both forms go only to standard output, end in a newline, and exit 0. `--help` emits the following exact full text:

```text
CLI tools for generating beautiful code snapshots

Usage: codesnap [OPTIONS] --output <OUTPUT>

Options:
  -f, --from-file <FROM_FILE>
          Path to the file to snapshot

  -c, --from-code [<Code>]
          Code snippet for snapshot

  -i, --from-image [<Image>]
          

      --from-clipboard
          

  -o, --output <OUTPUT>
          Output path for the snapshot. Available value:
          
          - clipboard: Copy the snapshot to clipboard - file path: Save the snapshot to the file path
          
          Currently CodeSnap supports SVG format and PNG format If output is directory, CodeSnap will generate a temporary file name to save the snapshot to the directory.

      --silent
          

  -e, --execute <EXECUTE>...
          Executing a command and taking the output as the code snippet

      --skip
          Skip run the command to get output, just take the command as the input

      --range <RANGE>
          You can set the range of the code snippet to display for example, display the 3rd to 5th: 3:5 The syntax is similar to the range in Python or Golang, so basically you can use 3: to represent the 3rd to the end, or use :5 to represent the start to the 5th. This option is useful when you use the `from_file` option as the input, and you just want to display part of the code snippet

      --code-font-family <CODE_FONT_FAMILY>
          Font family for the code snippet

      --code-theme <CODE_THEME>
          Code theme for the code snippet

      --has-breadcrumbs <HAS_BREADCRUMBS>
          Breadcrumbs is a useful and unique feature in CodeSnap, it shows the path of the file so that users can know where the code snippet comes from
          
          [default: false]
          [possible values: true, false]

      --has-line-number
          

      --breadcrumbs-separator <BREADCRUMBS_SEPARATOR>
          Breadcrumbs separator is the character to separate the path in breadcrumbs Default is `/`

      --breadcrumbs-font-family <BREADCRUMBS_FONT_FAMILY>
          Breadcrumbs font family

      --breadcrumbs-color <BREADCRUMBS_COLOR>
          Breadcrumbs font color

      --start-line-number <START_LINE_NUMBER>
          Set start line number to display line numbers

      --line-number-color <LINE_NUMBER_COLOR>
          Line number font color
          
          [default: #495162]

  -d, --delete-line <DELETE_LINE>...
          Delete lines will be marked with a red line

      --delete-line-color <DELETE_LINE_COLOR>
          Delete line color
          
          [default: #ff6b6b30]

  -a, --add-line <ADD_LINE>...
          New lines will be marked with a green line

      --add-line-color <ADD_LINE_COLOR>
          New line color
          
          [default: #2ecc7130]

      --highlight-range <HIGHLIGHT_RANGE>
          Convenient version of `--raw-highlight-lines` option, you can set the highlight range with a simple syntax, for example, highlight the 3rd to 5th lines: 3:5

      --relative-highlight-range
          

      --highlight-range-color <HIGHLIGHT_RANGE_COLOR>
          Highlight color for the highlighted code lines
          
          [default: #ffffff10]

      --raw-highlight-lines <RAW_HIGHLIGHT_LINES>
          CodeSnap allows users to highlight multiple lines with custom highlight color in the code snippet The content of highlight_lines is JSON string, for example highlight the first line and the 3rd to 5th lines: "[ [1, "#ff0000"], [3, 5, "#00ff00"] ]"

  -l, --language <LANGUAGE>
          Set the language of the code snippet, If you using the `file` option, CodeSnap will automatically detect the language from the file extension

      --file-path <FILE_PATH>
          Used to detect the language of the code snippet, if you want to set language manually, use `--language` or `-l` option

  -w, --watermark <WATERMARK>
          Set watermark for the code snippet

      --watermark-font-family <WATERMARK_FONT_FAMILY>
          Watermark font family

      --watermark-color <WATERMARK_COLOR>
          Watermark font color

      --shadow-radius <SHADOW_RADIUS>
          Set window shadow radius

      --shadow-color <SHADOW_COLOR>
          

      --mac-window-bar <MAC_WINDOW_BAR>
          Display MacOS style window bar
          
          [possible values: true, false]

      --has-border
          Display window border

      --border-color <BORDER_COLOR>
          Window border color
          
          [default: #ffffff30]

      --margin-x <MARGIN_X>
          Set horizontal margin of window

      --margin-y <MARGIN_Y>
          Set vertical margin of window

      --title <TITLE>
          Set title of the window

      --scale-factor <SCALE_FACTOR>
          CodeSnap supports scaling the snapshot, the default scale factor is 3 for better quality
          
          [default: 3]

      --title-font-family <TITLE_FONT_FAMILY>
          Title font family

      --title-color <TITLE_COLOR>
          Title font color

      --background <BACKGROUND>
          Set background color of the snapshot

      --type <TYPE>
          [default: image]
          [possible values: ascii, image]

      --config <CONFIG>
          

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

## Spec 4

`-h` emits the following exact, shorter summary and exits 0:

```text
CLI tools for generating beautiful code snapshots

Usage: codesnap [OPTIONS] --output <OUTPUT>

Options:
  -f, --from-file <FROM_FILE>
          Path to the file to snapshot
  -c, --from-code [<Code>]
          Code snippet for snapshot
  -i, --from-image [<Image>]
          
      --from-clipboard
          
  -o, --output <OUTPUT>
          Output path for the snapshot. Available value:
      --silent
          
  -e, --execute <EXECUTE>...
          Executing a command and taking the output as the code snippet
      --skip
          Skip run the command to get output, just take the command as the input
      --range <RANGE>
          You can set the range of the code snippet to display for example, display the 3rd to 5th: 3:5 The syntax is similar to the range in Python or Golang, so basically you can use 3: to represent the 3rd to the end, or use :5 to represent the start to the 5th. This option is useful when you use the `from_file` option as the input, and you just want to display part of the code snippet
      --code-font-family <CODE_FONT_FAMILY>
          Font family for the code snippet
      --code-theme <CODE_THEME>
          Code theme for the code snippet
      --has-breadcrumbs <HAS_BREADCRUMBS>
          Breadcrumbs is a useful and unique feature in CodeSnap, it shows the path of the file so that users can know where the code snippet comes from [default: false] [possible values: true, false]
      --has-line-number
          
      --breadcrumbs-separator <BREADCRUMBS_SEPARATOR>
          Breadcrumbs separator is the character to separate the path in breadcrumbs Default is `/`
      --breadcrumbs-font-family <BREADCRUMBS_FONT_FAMILY>
          Breadcrumbs font family
      --breadcrumbs-color <BREADCRUMBS_COLOR>
          Breadcrumbs font color
      --start-line-number <START_LINE_NUMBER>
          Set start line number to display line numbers
      --line-number-color <LINE_NUMBER_COLOR>
          Line number font color [default: #495162]
  -d, --delete-line <DELETE_LINE>...
          Delete lines will be marked with a red line
      --delete-line-color <DELETE_LINE_COLOR>
          Delete line color [default: #ff6b6b30]
  -a, --add-line <ADD_LINE>...
          New lines will be marked with a green line
      --add-line-color <ADD_LINE_COLOR>
          New line color [default: #2ecc7130]
      --highlight-range <HIGHLIGHT_RANGE>
          Convenient version of `--raw-highlight-lines` option, you can set the highlight range with a simple syntax, for example, highlight the 3rd to 5th lines: 3:5
      --relative-highlight-range
          
      --highlight-range-color <HIGHLIGHT_RANGE_COLOR>
          Highlight color for the highlighted code lines [default: #ffffff10]
      --raw-highlight-lines <RAW_HIGHLIGHT_LINES>
          CodeSnap allows users to highlight multiple lines with custom highlight color in the code snippet The content of highlight_lines is JSON string, for example highlight the first line and the 3rd to 5th lines: "[ [1, "#ff0000"], [3, 5, "#00ff00"] ]"
  -l, --language <LANGUAGE>
          Set the language of the code snippet, If you using the `file` option, CodeSnap will automatically detect the language from the file extension
      --file-path <FILE_PATH>
          Used to detect the language of the code snippet, if you want to set language manually, use `--language` or `-l` option
  -w, --watermark <WATERMARK>
          Set watermark for the code snippet
      --watermark-font-family <WATERMARK_FONT_FAMILY>
          Watermark font family
      --watermark-color <WATERMARK_COLOR>
          Watermark font color
      --shadow-radius <SHADOW_RADIUS>
          Set window shadow radius
      --shadow-color <SHADOW_COLOR>
          
      --mac-window-bar <MAC_WINDOW_BAR>
          Display MacOS style window bar [possible values: true, false]
      --has-border
          Display window border
      --border-color <BORDER_COLOR>
          Window border color [default: #ffffff30]
      --margin-x <MARGIN_X>
          Set horizontal margin of window
      --margin-y <MARGIN_Y>
          Set vertical margin of window
      --title <TITLE>
          Set title of the window
      --scale-factor <SCALE_FACTOR>
          CodeSnap supports scaling the snapshot, the default scale factor is 3 for better quality [default: 3]
      --title-font-family <TITLE_FONT_FAMILY>
          Title font family
      --title-color <TITLE_COLOR>
          Title font color
      --background <BACKGROUND>
          Set background color of the snapshot
      --type <TYPE>
          [default: image] [possible values: ascii, image]
      --config <CONFIG>
          
  -h, --help
          Print help (see more with '--help')
  -V, --version
          Print version
```

## Spec 5

Argument failures use command-line-parser diagnostics on standard error, with no standard output, and exit 2. The primary forms are:

```text
error: the following required arguments were not provided:
  --output <OUTPUT>

Usage: codesnap --output <OUTPUT>

For more information, try '--help'.
```

and, for an unexpected bare argument:

```text
error: unexpected argument 'foo' found

Usage: codesnap [OPTIONS] --output <OUTPUT>

For more information, try '--help'.
```

With other supplied options the usage synopsis may include those applicable options, but diagnostics must retain the phrases checked above. A value-less `-o`/`--output` reports that a value is required and identifies `--output <OUTPUT>`. Invalid `--type` reports the two possible values `ascii` and `image`. Specifically, `--has-breadcrumbs maybe -c x -o out.png` exits 2, writes nothing to stdout, and writes exactly the following to stderr:

```text
error: invalid value 'maybe' for '--has-breadcrumbs <HAS_BREADCRUMBS>'
  [possible values: true, false]

For more information, try '--help'.
```

Invalid numeric text reports its conversion problem. Unknown and misspelled options report `unexpected argument`. Parsing stops on the first relevant syntax error.

The output option is syntactically required even for invocations that will later fail for lack of input. After parsing, an invocation with `-o ...` but no usable input source is a runtime error, not an argument error.

## Spec 6

An otherwise successful non-help/non-version rendering run prepares `$HOME/.config/codesnap/remote_themes`, recursively creating its ancestor directories. This preparation also occurs when `--config` names an explicit configuration; a successful such run against a fresh `HOME` leaves `.config/codesnap/remote_themes` present but does not create `.config/codesnap/config.json`.

Unless `--config` is supplied, the run loads `$HOME/.config/codesnap/config.json`. `XDG_CONFIG_HOME` is deliberately ignored. On the first run for a given `HOME`, the executable writes the exact default JSON below and writes a blue information line to stdout even if `--silent` was requested:

```text
\x1b[34m[INFO]\x1b[0m Automated created config file at "ABSOLUTE_PATH/.config/codesnap/config.json"
```

The path is formatted with double quotes. Existing configuration is read without being rewritten and without this INFO line. Different `HOME` values are isolated.

```json
{
  "print_eggs": false,
  "snapshot_config": {
    "theme": "candy",
    "window": {
      "mac_window_bar": true,
      "shadow": { "radius": 20, "color": "#00000040" },
      "margin": { "x": 82, "y": 82 },
      "border": { "width": 1, "color": "#ffffff30" },
      "title_config": { "color": "#ffffff", "font_family": "Pacifico" },
      "radius": 12
    },
    "code_config": {
      "font_family": "CaskaydiaCove Nerd Font",
      "breadcrumbs": {
        "enable": false,
        "separator": "/",
        "color": "#80848b",
        "font_family": "CaskaydiaCove Nerd Font"
      }
    },
    "watermark": {
      "content": "CodeSnap",
      "font_family": "Pacifico",
      "color": "#ffffff"
    },
    "background": {
      "start": { "x": 0, "y": 0 },
      "end": { "x": "max", "y": 0 },
      "stops": [
        { "position": 0, "color": "#6bcba5" },
        { "position": 1, "color": "#caf4c2" }
      ]
    }
  }
}
```

Whitespace in the created file need not match this compact presentation, but parsed JSON values and structure must match exactly.

## Spec 7

`--config FILE` bypasses discovery and creation of the default `config.json`, but not the `$HOME/.config/codesnap/remote_themes` directory preparation in Spec 6. It reads the named path relative to the current directory unless absolute. Paths containing spaces work. JSON parsing is strict: trailing commas and malformed syntax are rejected; unknown fields at any nesting level are ignored.

The root requires `print_eggs` (Boolean) and `snapshot_config` (object). Within `snapshot_config`, `background` is required. Omitting an entire optional top-level configuration object lets the builder supply its default: theme `candy`; scale factor 3; no extra theme/font folders; no title; line-number color `#495162`; window margin 82/82, title font `CaskaydiaCove Nerd Font` and color `#aca9b2`, border width 1/color `#ffffff30`, mac bar true, shadow radius 20/color `#0000004d`, corner radius 12; code font `CaskaydiaCove Nerd Font` and disabled breadcrumbs with separator `/`, color `#80848b`, and that same font; no watermark; command prompt `❯` with prompt `#F78FB3`, command `#98C379`, quoted-string `#ff0000`, and the code font.

Those builder defaults do not fill missing members of a nested object that is explicitly present in JSON. An explicit `window` object requires `margin`, `title_config`, `border`, `mac_window_bar`, `shadow`, and `radius`; their nested objects respectively require both `x`/`y`, `font_family`/`color`, `width`/`color`, and `radius`/`color`. Thus a `window` containing only `border` or only `radius` fails with ``missing field `margin` ``, while one containing margin, mac-bar, shadow, border, and radius but no title configuration fails with ``missing field `title_config` ``. An explicit `code_config` requires `font_family`; its `breadcrumbs` member may be omitted as a whole, but if present it requires `enable`, `separator`, `color`, and `font_family`. An explicit watermark requires `content`, `font_family`, and `color`, and an explicit command-output configuration requires all of its members. These are handled config failures (stdout, exit 1, no destination), with the parser appending the applicable JSON line and column.

JSON types are not coerced: numeric fields such as radius, margins, and scale must be JSON numbers rather than numeric strings, and a type mismatch is an `[ERROR]` parse failure that creates no output.

Background is either a solid color string or an object `{start, end, stops}`. `start` and `end` each contain `x` and `y`; each coordinate must be a number or the exact string `"max"`, meaning the final raster width/height. Any other string (including `"maximum"` and `"invalid"`) and any Boolean, array, or object coordinate causes the containing untagged `Background` value to fail as a whole. The handled stdout diagnostic contains `[ERROR] data did not match any variant of untagged enum Background` followed by the JSON parser's applicable line and column; it does not expose the inner `DimensionValue` message. A stop is `{ "position": NUMBER, "color": COLOR }`; multiple stops and positions exactly 0 and 1 are supported.

An empty root fails with ``missing field `print_eggs` at line 1 column 2``. A snapshot object containing only a theme fails with `` `background` must be initialized ``. Missing files report `No such file or directory (os error 2)`. Typical strict-parser messages include `key must be a string at line 1 column 3` and `trailing comma at line 5 column 3`.

Configuration scale factor is deserialized permissively, including zero, but the CLI's default `--scale-factor 3` is subsequently applied, so a config-only scale value does not override that CLI default. Three other CLI defaults likewise overwrite config on every run: breadcrumb enablement becomes false unless `--has-breadcrumbs true` is explicit, line-number color becomes `#495162` unless explicitly changed, and border width/color become 1/`#ffffff30` (the parsed `--has-border` compatibility flag is effectively redundant with its true default). Other explicit CLI values take precedence for theme, window margin/mac/shadow values, font, watermark, title, and related styling. The config's editor radius, background, theme/font folders, and unoverridden fields remain effective.

If root `print_eggs` is true, a successful run prints a Ferris-the-crab speech bubble after its normal output. The selected saying may vary, but the art contains `_~^~^~_`, `\) /  o o  \ (/`, `'_   -   _'`, and `/ '-----' \`.

## Spec 8

Code mode chooses `--from-file` before `--from-code`, then `--from-clipboard`. Thus simultaneous `--from-file` and `--from-code` succeeds using the file; multiple source flags are not themselves a conflict error. A nonempty `--execute` list selects command-output mode. Otherwise `--from-image`, when present, selects image mode before any code-mode source; consequently image-plus-code behaves as image input, including propagating an image decode error before the code can be used.

`--from-file` reads the whole file strictly as UTF-8. A nonexistent file fails with the operating-system message. An existing directory fails with `The file path is not a file`. Invalid UTF-8 fails with `stream did not contain valid UTF-8`; embedded NUL bytes in otherwise valid UTF-8 are accepted. Empty files are valid.

`--from-code CODE` uses the argument literally, including empty strings, Unicode, quotes, slashes, and newlines. `--from-code -`, `--from-code` with no value, and short `-c` with no value read stdin to EOF as UTF-8. If that read is requested from an attached terminal rather than a pipe, print help and terminate with argument-error status rather than waiting interactively. Clipboard operations may either succeed or report a clear clipboard/display/Wayland error when the host has no clipboard service.

## Spec 9

Each value collected by `--execute` is a complete shell command string and becomes one command block in the snapshot, in order. On Unix, invoke it as `sh -c COMMAND` and capture its output for the snapshot. With `--skip`, do not invoke any child and use an empty output for each block, while still rendering the literal command header.

Each block displays a `❯` prompt followed by the literal command and then the captured text. The prompt is pink (`#F78FB3`), the first whitespace-delimited command word is bold green (`#98C379`), remaining arguments use normal foreground styling, and output recognizes ordinary ANSI foreground colors. Command text/output use 12.5-pixel type with 20-pixel line height.

## Spec 10

Line range syntax is shared by `--range`, `--highlight-range`, `--add-line`, and `--delete-line`:

- `N` means only line N.
- `A:B` means A through B, inclusive.
- `A:` means A through the last line.
- `:B` means line 1 through B.
- The literal `start:end` means the full source.
- If A is greater than B, swap them.

Line indices are decimal, conceptually one-based, and surrounding whitespace is not trimmed. More than one colon fails with `Invalid range format`; bad numbers fail with `invalid digit found in string`; empty endpoints not covered by the one-sided shorthand (including an empty range string or bare `:`) fail with `cannot parse integer from empty string`.

`--range` applies to code content. Split using text-line semantics (line terminators removed and a final terminator does not create another line), select with start inclusive and end inclusive, and join selected lines with `\n`. Compatibility behavior accepts zero and still produces a valid snapshot. Reversed ranges are normalized before selection.

## Spec 11

Before measuring and drawing code, normalize tabs and indentation into renderable spaces while preserving line structure and internal blank lines. Terminal line endings are not drawn. Empty/whitespace input, a single character, Unicode, special characters, many short lines, and very long individual lines must render without corruption.

Code is rendered with advanced shaping in a bundled `CaskaydiaCove Nerd Font` family (regular, bold, and italic faces), unless `--code-font-family` or config selects another installed/loaded family. Code metrics are font size 12.5 and line height 18 logical pixels. The editor has at least 350 logical pixels of outer width, so very short snippets do not collapse. Layout width follows the widest shaped line, not the first or average line, and expands for long input.

## Spec 12

Syntax highlighting uses a Sublime/TextMate-style syntax set and preserves highlighting state across lines. Detection order is:

1. Explicit `--language`, if present.
2. The actual `--from-file` path; otherwise `--file-path`; otherwise a file path inherited from config content.
3. Plain-text fallback when neither hint identifies a syntax.

Explicit language overrides path detection entirely. A recognized `--file-path` extension can identify syntax without the path existing. For an unknown or absent extension, however, the detector tries to open `--file-path` to inspect its contents before falling back to plain text. Consequently a nonexistent hint such as `name.unknown_extension` causes a handled failure: stdout is `\x1b[31m[ERROR]\x1b[0m No such file name.unknown_extension\n`, stderr is empty, the exit status is 1, and no destination is created. This lookup occurs even for inline `--from-code` and even when breadcrumbs are disabled. An existing readable path whose extension and contents identify no syntax falls back to plain text, while explicit `--language` bypasses the lookup and permits a nonexistent `--file-path`. Required accepted language/file types include Python, JavaScript, Rust, C, C++, Go, Java, Ruby, shell, Markdown, JSON, YAML, PHP, Swift, and TypeScript.

The default `candy` theme supplies both editor background and token foreground/style colors. Theme names are exact and case-sensitive: whitespace is not trimmed, and unknown/empty/Unicode/arbitrary names fail as `Cannot find NAME theme`. `themes_folders` may name directories containing Sublime `.tmTheme` files; a folder that cannot be loaded fails with `Highlight code failed`. `fonts_folders` names additional font directories. Rendering applies theme bold and italic styles; underline-style tokens remain normal-style colored text.

## Spec 13

Line numbers are off unless `--has-line-number` is present. Merely supplying `--start-line-number` does not turn them on. When enabled, the default first number is the first absolute line selected by `--range` (normally 1); an explicit start number replaces it. Show one number per displayed line, right-aligned to the digit width of the largest displayed number. The gutter uses the code font, size 14, line height 18, width `9.05 * digit_count` logical pixels, and 10 pixels of right margin. Its default color is `#495162`; `--line-number-color` overrides it. A custom display start affects labels only, not highlight coordinates.

Breadcrumbs are off by default and controlled by explicit `--has-breadcrumbs true|false`. When enabled and a path is available, display that complete path above the code, replacing every platform path separator with the configured separator (default `/`, with multicharacter and special-character separators allowed). Absolute and deep paths are not shortened. Breadcrumb metrics are size 12, line height 15; width is 8 times the path byte length with a 100-pixel minimum. Use breadcrumb color `#80848b` by default. For compatibility, text drawing uses the code font-family selection; the separately accepted breadcrumb-family option does not change that drawing choice. Breadcrumbs can be enabled for inline code when `--file-path` supplies the displayed path, subject to the language-detection path lookup in Spec 12.

## Spec 14

Convenience highlighting and diff markings draw translucent, full-editor-width rectangular backgrounds aligned to 18-pixel code rows, including the line-number gutter where present.

Without `--relative-highlight-range`, convenience/add/delete coordinates are absolute source line numbers. If `--range A:B` selected a snippet, each requested highlight must start at or after A and end at or before B, then is translated to snippet-relative rows. Violations fail with `The highlight start range should be greater than or equal to A` or `The highlight end range should be less than or equal to B`.

With `--relative-highlight-range`, positive coordinates are one-based positions within the selected snippet. For a selected absolute range A:B, accept an end through `(B - A) + 1`. A larger end is rejected, but its compatibility error says `The highlight end range should be less than or equal to B-A` (for selection 7:11, the reported number is therefore 4 even though relative row 5 is valid). An addition marker must also start at one or later: `--add-line 0` is a handled failure that exits 1, creates no destination, leaves stderr empty, and writes `\x1b[31m[ERROR]\x1b[0m The highlight start range should be greater than or equal to 1\n` to stdout. The renderer clamps a highlight's end to the actual displayed line count.

`--highlight-range` creates one block using `--highlight-range-color` (default `#ffffff10`). Every repeated `--delete-line` entry creates a block using `#ff6b6b30` by default; every repeated `--add-line` entry creates a block using `#2ecc7130` by default. Single lines, closed/open/reversed ranges, and multiple separate entries are supported. Draw in this order: convenience highlight, all deletion entries in argument order, all addition entries in argument order. Thus later translucent blocks composite over earlier overlapping blocks; marking one row both deleted and added is valid.

## Spec 15

`--raw-highlight-lines` is strict JSON with this schema:

```json
[
  [LINE_U32, "#RRGGBB-or-#RRGGBBAA"],
  [START_U32, END_U32, "#RRGGBB-or-#RRGGBBAA"]
]
```

It supports any ordered mixture of single-line and range entries, multiple colors, overlaps, and reversed start/end (normalized during drawing). Preserve array order for compositing. Raw coordinates directly describe displayed rows and bypass convenience range translation/validation; ends are clamped to displayed length. If this option exists it replaces, rather than augments, all `--highlight-range`, add-line, and delete-line definitions. Invalid JSON is a handled runtime error using the strict JSON parser's text. In particular, the invalid token `x` produces `expected value at line 1 column 1`; an unterminated string can produce `EOF while parsing a string at line 1 column 13`.

## Spec 16

Colors consumed by rendering use only `#RRGGBB` and `#RRGGBBAA`; six-digit input implies alpha `ff`, while eight-digit input interprets its last byte as alpha. Hex digit case is accepted. Three-digit shorthand, a missing `#`, the wrong total length, or non-hex digits is invalid. Compatibility validation is lazy: a bad color option may go unnoticed if its component is never drawn, but a bad active line number, title, border, watermark, shadow, or highlight color fails fatally. A missing `#` or wrong total length panics with `Invalid hex color: VALUE` on stderr. A structurally valid-length color containing non-hex digits takes a different panic path: for active line-number color `#gg0000`, the process exits 101 with empty stdout, creates no destination, and stderr contains ``called `Result::unwrap()` on an `Err` value: ParseIntError { kind: InvalidDigit }`` rather than `Invalid hex color: #gg0000`. This validation does not apply to the ignored CLI `--background` value.

The standard code-window frame has these logical defaults from the created config: horizontal and vertical outer margins 82 on each side; editor corner radius 12; 1-pixel `#ffffff30` border; macOS controls enabled; downward shadow offset 21, blur radius 20, color `#00000040`; editor fill from the selected syntax theme. The editor's inner padding is 14 on left/right/bottom and 14 on top when the mac bar is enabled, or 12 on top when disabled.

The mac bar is a row of three radius-6 circles, red `(255,94,87)`, yellow `(255,186,46)`, and green `(43,200,65)`, with 4 logical pixels between circles and 10 pixels below the row. `--mac-window-bar false` removes it. Border, shadow, zero/large shadow radii, asymmetric/zero/large margins, and all combinations compose in the expected back-to-front order: background, blurred shadow, border layers, editor fill, highlights, and text.

Margins materially change canvas dimensions and encoded output size. With the same short snippet, changing both margins from 10 to 200 must make the latter PNG substantially larger (more than 1.5 times the encoded byte count in representative output), while zero margins produce the minimal canvas rather than reverting to defaults.

## Spec 17

`--title TEXT` with nonempty text adds a bold title to code/command window chrome, centered over the complete raster width. It uses font size/line height 10, configured title color/font (created defaults `#ffffff` and `Pacifico`), reserves approximately 6 logical pixels per UTF-8 byte plus 12 pixels height, and supports long, Unicode, emoji, quotes, and markup characters as literal text. It shares the top row with the mac controls. An explicitly empty `--title ""` still activates and reserves the title layout row, so its raster differs from an invocation without `--title`. With the created default configuration, `-c x --mac-window-bar false --scale-factor 1 --silent` produces a 518-by-284 PNG without a title and a 518-by-298 PNG with `--title ""`.

The background behind the framed content comes from JSON configuration. It may be a solid RGBA color or a padded linear gradient. The created default is horizontal from `#6bcba5` at x=0 to `#caf4c2` at the maximum canvas x. Gradient coordinates use logical final canvas dimensions and stops interpolate in order. If both outer margins are zero, no background fill component is drawn.

The CLI parses `--background VALUE` as an accepted compatibility string but never applies or validates it. The loaded JSON background remains in effect whether or not the option is supplied. Thus valid values such as `#ff00ffff` and invalid values such as `fff`, `#fff`, `#12345`, `#123456789`, and `#gg0000` all exit 0 on an otherwise successful invocation, leave stderr empty, and produce exactly the same snapshot bytes as omitting `--background`.

## Spec 18

A watermark is optional in the configuration model, though the auto-created config supplies `CodeSnap`. `--watermark` creates/replaces its text while inheriting unspecified config font/color; when no config watermark exists, defaults are `Pacifico` and `#ffffff`. Explicit watermark font/color override those values. Empty, long, and Unicode watermark strings are accepted; an explicitly empty watermark still reserves watermark layout space.

The watermark is centered below the framed content. Its font size is 11% of final logical canvas width, clamped to 20 through 30, with equal line height, 50 logical pixels above and 22 below. It is completely omitted whenever vertical margin is less than 82, regardless of configured watermark; at margin 82 or more it is rendered. Watermarks work with code and command input and with PNG/SVG output.

## Spec 19

Image input expects PNG bytes. `-i`/`--from-image` without a value (or with `-`) reads stdin as raw bytes. Any other provided `IMAGE` argument is itself converted to its literal UTF-8 bytes and decoded as the PNG payload; it is not opened as a filesystem path. Therefore passing the name of an existing valid PNG, including a path containing spaces, exits 1 with `[ERROR] Invalid PNG signature.`, empty stderr, and no destination. Validation happens before writing the destination.

Invalid input must not create the output file. After stripping ANSI, representative exact stdout errors are `[ERROR] Invalid PNG signature.` for arbitrary non-PNG bytes and `[ERROR] Unexpected end of data before image end.` for empty bytes. A malformed chunk stream reports an `[ERROR]` line containing `chunk appeared before IHDR chunk`. These failures exit 1.

## Spec 20

Snapshot rendering is a deterministic RGBA raster pipeline. Work in logical pixels, allocate a transparent raster whose integer width and height are the final logical layout dimensions multiplied by `--scale-factor`, then scale shapes and text consistently by that factor. Scale 1 is the minimum successful CLI value; zero parses as U8 but final configuration validation fails with `The scale factor must be greater than 1` (wording retained even though 1 is accepted). Factors 2, 3, 5, and 10 are supported; for identical logical content, scale 10 has exactly ten times the PNG IHDR width and height of scale 1.

Text is rasterized, not emitted as SVG text. Use deterministic advanced shaping, embedded Caskaydia Cove Nerd Font regular/bold/italic and Pacifico faces before system fallback, and anti-aliased glyph coverage. Shapes use deterministic premultiplied-alpha compositing; background rectangles use non-antialiased edges. Rounded editor rectangles, shadows, syntax spans, blank lines, wide Unicode, and long lines must all participate in layout. Identical inputs/config/environment produce byte-identical output; different source, relevant range, language, theme, scale, or visual options produce correspondingly different raster data.

Determinism here is a byte-level compatibility requirement, not merely a requirement to produce a visually similar raster. Text shaping, glyph coverage, premultiplied-alpha rounding, blur, PNG filtering/compression, chunk ordering, and the base64 wrapping must reproduce the reference bytes. A substitute renderer or encoder that preserves only dimensions and approximate appearance is not conforming.

The following vectors make that byte-level requirement testable for the margin, highlight, line-number, and breadcrumb combinations. Begin with an already-existing config exactly equal to the auto-created config in Spec 6, so there is no creation message. Define the source values exactly as follows (the blank-looking third line of `CODE` contains four spaces):

```text
CODE = "fn main() {\n    let alpha = 1;\n    \n    let beta = 2;\n    println!(\"{}\", alpha + beta);\n}"
LONG = "line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\nline 8"
```

For each row, invoke `executable SOURCE EXTRA -o out.svg --silent`, substituting the defined source value as one argument and likewise passing each JSON or separator value as one argument. Each invocation exits 0 with empty stdout and stderr. The byte length and SHA-256 are for the complete SVG file, including its embedded PNG; the destination filename itself does not affect the bytes.

| Case | `SOURCE EXTRA` | Bytes | SHA-256 |
|---|---|---:|---|
| custom margins | `-c CODE --margin-x 50 --margin-y 30` | 321595 | `62bd257085901101219eb6eba2aacd4db7df6dc0ec780c6ce8586c12ce77dcc5` |
| vertical margin only | `-c CODE --margin-y 25` | 332379 | `f7badad19e38c67d168a9ad222200692a0b5f35ef647af3e84e3d538dea29916` |
| zero margins | `-c CODE --margin-x 0 --margin-y 0` | 91991 | `1f1af0517efa2e41b84f45e81a4ee01d9e5265e6b5b4bbb59a611622b681c65e` |
| absolute highlight with selected range | `-c LONG --range 3:6 --highlight-range 4:5` | 567719 | `3f760ee92cca75b4c2471cf85fb4b17c8f7fa7b90b86528e72e9b3b6a0f6181d` |
| empty code, no highlight | `-c ""` | 484499 | `f7893a293495396465cc022c27a3deb99577393ef2142c4ee125a6b718977cd5` |
| custom highlight color | `-c CODE --highlight-range 2:3 --highlight-range-color #ff00ff80` | 644751 | `264092e5680ed2349d8e1ed7fe786386647b5817ef7c50a7bbb745a7daddc82b` |
| highlight from start | `-c CODE --highlight-range :3` | 645055 | `a5fd7fb3df7440070d6578dd1a6b20d413cf9c95a8c0f1fb74b66c5059333c31` |
| closed highlight | `-c CODE --highlight-range 2:4` | 645191 | `bc30cf17388be8303e75cb6d10a9717e069af93cfca20062837e37a1e303a367` |
| highlight to end | `-c CODE --highlight-range 3:` | 645043 | `dda0df49d52491775c53033d1f1a9647b1a9619960b9dff78138646d5aaae13c` |
| whitespace-only line highlight | `-c CODE --highlight-range 3` | 645463 | `b1dc5421467db17a2d244605022a8f13a325469b96d654c80489665b7a1f8020` |
| one-row highlight | `-c CODE --highlight-range 2` | 645383 | `e9a6dcd42ca849e5455385c612f25a3a64a3499ac69e60125d03953b8ef4b721` |
| highlight plus delete/add | `-c CODE --highlight-range 1:2 --delete-line 2:3 --add-line 3:4` | 644391 | `7c5dffdbc91b6cdc96b866f87c1253d6d099b262b06a26112bd3b8708040ba97` |
| highlight with line numbers | `-c CODE --has-line-number --highlight-range 2:3` | 659015 | `fe6d000d8c3431e5a9d7ef4b4b531fcb5a72e920115e647290353cac38d3dab9` |
| selected range, custom labels, and highlight | `-c LONG --range 3:6 --has-line-number --start-line-number 40 --highlight-range 4:5` | 579731 | `fb0ec852cd72d4463aa1be1af8580932832c0c14cef170b521e8e3abd2c94fd8` |
| custom labels and highlight | `-c CODE --has-line-number --start-line-number 40 --highlight-range 2:3` | 668319 | `db21f79a114681eb9208570067b22736b7945a4d62594cd4be504e583d609c24` |
| overlapping raw ranges | `-c CODE --raw-highlight-lines [[2,4,"#ff000080"],[3,5,"#0000ff80"]]` | 644031 | `ff6e93ebe58cb5704270b9e98ab6de4eca44c2623a586db314e9067322d10462` |
| mixed raw definitions | `-c CODE --raw-highlight-lines [[1,"#ff000040"],[2,4,"#00ff0080"],[5,"#0000ffff"]]` | 641583 | `73981c8accf10d4759a704f570fbb2572471bce53f58821ec0c4127224853155` |
| multiple raw colors | `-c CODE --raw-highlight-lines [[1,"#ff000080"],[3,"#00ff0080"],[5,"#0000ff80"]]` | 644831 | `e63d51cdf0b6d2def1218323874c5f2c7f45f125077d868bab809e59c9515d75` |
| raw order | `-c CODE --raw-highlight-lines [[2,4,"#ff000080"],[2,4,"#00ff0080"]]` | 644571 | `e8f1edc0d7d4d8fc0770523f43094113f12efc27690e447f8b35ce9a7979d887` |
| raw single-line tuple | `-c CODE --raw-highlight-lines [[2,"#ff00ff80"]]` | 644699 | `108a71e42d6a57ec4ab08d99cc744a62f2f017b681401db07db8f75fca16f609` |
| relative selected-range highlight | `-c LONG --range 3:6 --relative-highlight-range --highlight-range 2:3` | 567719 | `3f760ee92cca75b4c2471cf85fb4b17c8f7fa7b90b86528e72e9b3b6a0f6181d` |
| one-line source highlight | `-c "only line" --highlight-range 1` | 492219 | `78780164633b84ba9c8dc387b9a7acbe0599ff54207a8af9d0be31e8463c31dc` |
| line numbers plus breadcrumbs | `-c CODE --has-line-number --has-breadcrumbs true --file-path src/main.rs` | 686167 | `04e68a26fd5dbef646baffc16ca8c5b0a5e209d20ce47db7585b084037a4d170` |
| absolute breadcrumb path | `-c CODE --has-breadcrumbs true --file-path /workspace/project/src/main.rs` | 689467 | `7d89e9666ab1e4ee4d6b130f7309c1d87870cfdf13fbb4058b615034b840feaf` |
| basic breadcrumbs | `-c CODE --has-breadcrumbs true --file-path src/main.rs` | 672219 | `a053deb1fd2d4c8df55e655bce02fd864f3291c09169b5b960431d4fafa88781` |
| custom breadcrumb color | `-c CODE --has-breadcrumbs true --file-path src/main.rs --breadcrumbs-color #ff00ff` | 672419 | `c447ce99cc7be9cf7b9f240a13d130703ac7c14bb476a6b0d4f6c736a542bdb6` |
| inline-code breadcrumbs | `-c "let value = 1;" --has-breadcrumbs true --file-path src/lib.rs` | 519135 | `e98177224ac9b16d1511ae92c517e00cd037360ebf4e47668d0c2a8c3ad62a5c` |
| long breadcrumb path | `-c CODE --has-breadcrumbs true --file-path very/deep/project/source/components/rendering/main.rs` | 723259 | `782d19932e4ea6cc675ad369a0046ab3b48908621d9d65797a23247d68c1e63a` |
| custom breadcrumb separator | `-c CODE --has-breadcrumbs true --file-path src/components/main.rs --breadcrumbs-separator " > "` | 682027 | `12ddbe3e80a9f8ae6333f486f594daf96bf60875ee2797b159c299385333ae3c` |
| multicharacter breadcrumb separator | `-c CODE --has-breadcrumbs true --file-path src/components/main.rs --breadcrumbs-separator ::` | 682107 | `b97bd42f4787936252167c8580cb45de2c1bc315c6068c84fa9fcc3434987c72` |
| special-character breadcrumb separator | `-c CODE --has-breadcrumbs true --file-path src/components/main.rs --breadcrumbs-separator " → "` | 681971 | `fb545f5e11f5a1e9d2d542f6ac1db241d739c2a9cc374964c5bd711773df7da5` |
| both features disabled | `-c CODE --file-path src/main.rs` | 645519 | `f5747aed4a5ac95d5af4ef93bc46f5f788cb61bf34d48a0e8a1a3a771af2bf8c` |
| custom line-number color | `-c CODE --has-line-number --line-number-color #ff00ff` | 660723 | `1c1c51ae717c1833d9c202a428ad2fcc406c0debad3869d4b096cc9e06827ac3` |
| default line-number color | `-c CODE --has-line-number` | 659463 | `1a7978143e22c7e03ae9705f7957df071feaf827aa9b941873c17f1e029a56c1` |
| ranged line numbers | `-c LONG --range 3:6 --has-line-number` | 575055 | `507c6ab6865989a94f3d2169b74eed3090429e55fba280777d8c1db84010cef9` |
| ranged line numbers with custom start | `-c LONG --range 3:6 --has-line-number --start-line-number 40` | 580279 | `b545decf30f4dc68336ed7bdac79c1201bd4b33f2b4899184109a0e709725d2f` |
| custom line-number start | `-c CODE --has-line-number --start-line-number 40` | 668939 | `9eac30af5e930f5999a92b7c4d68d2589bf81fb2bcffe026a61287bfe25e03f1` |
| start number without line numbers | `-c CODE --start-line-number 40` | 645519 | `f5747aed4a5ac95d5af4ef93bc46f5f788cb61bf34d48a0e8a1a3a771af2bf8c` |

## Spec 21

Destination behavior is selected as follows:

- A path ending case-sensitively in `.png` is overwritten with a valid PNG. The PNG begins with the standard eight-byte signature, has IHDR first with length 13, positive dimensions, and a normal IEND; use 8-bit RGBA-compatible encoding. Existing files are truncated, never appended.
- A path ending in `.svg` is overwritten with exactly `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><image href="data:image/png;base64,BASE64"/></svg>`, with no added newline. `BASE64` decodes to exactly the PNG bytes that the same invocation would write to `.png`.
- A path ending in `.html` is overwritten with exactly `<img src="data:image/png;base64,BASE64" />`, with no added newline, and the decoded bytes are the same PNG.
- `raw` writes those PNG bytes directly to stdout.
- `clipboard` copies an image snapshot, or copies textual ASCII form when `--type ascii`; lack of a usable system clipboard may be reported as an environment error.
- Any other value/extension, including a normal existing directory path with no supported suffix, fails with `Unsupported output format` and creates no file. A missing parent directory or read-only destination fails with its I/O error. Relative paths resolve from cwd; spaces are allowed.

Outputs contain the actual rendered raster rather than a placeholder. At default scale, even a tiny inline-code PNG is over 10,000 bytes, and a representative multiline source snapshot in PNG, SVG, or HTML form is over 100,000 bytes. The same floor also holds at scale 1: with an existing exact Spec 6 config, `executable --from-code x -o s1.png --scale-factor 1 --silent` exits 0 with empty streams and writes exactly 93,371 bytes, has IHDR dimensions 518 by 308, and has SHA-256 `733a148411a281c52785be48e360b71e513ad0a0b0b66008c2da8920360c92a7`. Raw PNG stdout is likewise well over 1,000 bytes. Selecting a small range from a long source substantially reduces output size (for example, six selected lines out of one hundred encode to less than half the full result).

`--type image` is the default. If `--type ascii` is paired with anything other than `-o clipboard`, do no rendering and create no output; write the yellow warning `\x1b[33m[WARN]\x1b[0m ASCII snapshot only supports copying to clipboard\n` and exit 0.

## Spec 22

Human-facing non-parser messages go to stdout and use ANSI SGR even when stdout is captured:

- Info: `\x1b[34m[INFO]\x1b[0m MESSAGE\n`
- Success: `\x1b[32m[SUCCESS]\x1b[0m MESSAGE\n`
- Warning: `\x1b[33m[WARN]\x1b[0m MESSAGE\n`
- Handled error: `\x1b[31m[ERROR]\x1b[0m MESSAGE\n`

A normal saved file reports `Snapshot saved to OUTPUT successful!`; clipboard reports `Snapshot copied to clipboard`; raw reports `Output to stdout`. With `--silent`, suppress the success line for every input mode and destination, but never suppress config-creation info, warnings, parser errors, or runtime errors. A successful silent file render otherwise has empty stdout and stderr.

Runtime failures must occur before creating a new destination wherever practical. Exact handled error text required by common cases is:

```text
No code snippet provided
No such file or directory (os error 2)
The file path is not a file
Invalid range format
invalid digit found in string
cannot parse integer from empty string
Unsupported output format
Cannot find THEME theme
```

All these appear after the red `[ERROR]` prefix and exit 1. Empty source, repeated add/delete markers, overwriting an existing file, Unicode, and NUL characters are not runtime failures.
