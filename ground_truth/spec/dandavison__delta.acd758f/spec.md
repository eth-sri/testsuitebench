# Behavioral specification for `executable`

The artifact is one executable file named exactly `executable`. It implements the command-line program commonly presented to users as `delta`, version 0.18.2: a streaming formatter for Git and unified-diff output. All requirements below are observable requirements. “Visible text” means bytes remaining after CSI/OSC terminal escapes are removed. Unless a mode says otherwise, output is UTF-8 and ANSI SGR/OSC sequences are significant.

## Spec 1

### Invocation, streams, and termination

With no positional files, read standard input to EOF, format it, and write the result to standard output. Empty input succeeds with status 0 and produces no output. The process must not require a terminal and must not hang on a closed or empty pipe. Ordinary formatted input succeeds with status 0 and does not write diagnostics.

There may be zero, one, or two positional operands, named `MINUS_FILE` and `PLUS_FILE`. A lone `-` means standard input. One ordinary pathname is accepted and the remaining input still comes from stdin; a missing/nonexistent lone pathname is a silent success if there is no input. Two operands request a direct file comparison as described later. Three operands are a command-line error.

Statuses are: 0 for successful filtering, identical direct-file comparisons, and informational actions; 1 for different direct-file operands and ordinary comparison failures inherited from the comparison program; 2 for CLI/configuration/validation errors; and, for an explicitly run external program, that program’s meaningful nonzero status (for example Git status 128 for a bad revision). Never panic on malformed input, invalid UTF-8, broken pipes, or a missing pager.

## Spec 2

### Version, long help, and short help

`--version` and `-V` print exactly `delta 0.18.2\n` to stdout, nothing to stderr, and exit 0. Version takes precedence even if extra operands follow it.

`--help` prints long help to stdout and exits 0; an accompanying ordinary option such as `--dark` does not prevent help. Its first lines, spelling, capitalization, blank lines, and synopsis are:

```text
A viewer for git and diff output

Usage: delta [OPTIONS] [MINUS_FILE] [PLUS_FILE]

Arguments:
  [MINUS_FILE]
          First file to be compared when delta is being used to diff two
          files.

          `delta file1 file2` is equivalent to `diff -u file1 file2 | delta`.

  [PLUS_FILE]
          Second file to be compared when delta is being used to diff two
          files

Options:
```

The long help ends in a newline and fully documents every option in Specs 3–5. It must contain the description above; the exact synopsis; `Arguments:` and `Options:` on their own lines; both positional names; and at least `--help`, `-h`, `--version`, `--config`, `--features`, `--pager`, `--paging`, `--side-by-side`, `--syntax-theme`, `--show-config`, `--show-themes`, `--show-syntax-themes`, `--generate-completion`, `--no-gitconfig`, `--raw`, `--color-only`, `--dark`, `--light`, and `--true-color`. It also includes explanatory sections named `Git config`, `Features`, `Styles`, `Colors`, `Line Numbers`, and `Support` and ends by directing short-help users to `delta -h`.

`-h` prints a shorter summary to stdout, includes an `Options:` heading and `--show-colors`, is strictly shorter than long help, and contains `see more with '--help'`. Both help forms leave stderr empty.

### Exact long-help contract

At COLUMNS=120, NO_COLOR=1, TERM=dumb, long help is exactly the following block (including its final newline):

```text
A viewer for git and diff output

Usage: delta [OPTIONS] [MINUS_FILE] [PLUS_FILE]

Arguments:
  [MINUS_FILE]
          First file to be compared when delta is being used to diff two
          files.

          `delta file1 file2` is equivalent to `diff -u file1 file2 | delta`.

  [PLUS_FILE]
          Second file to be compared when delta is being used to diff two
          files

Options:
      --blame-code-style <STYLE>
          Style string for the code section of a git blame line.

          By default the code will be syntax-highlighted with the same
          background color as the blame format section of the line (the
          background color is determined by blame-palette). E.g. setting this
          option to 'syntax' will syntax-highlight the code with no
          background color.

      --blame-format <FMT>
          Format string for git blame commit metadata.

          Available placeholders are "{timestamp}", "{author}", and
          "{commit}".

          [default: "{timestamp:<15} {author:<15.14} {commit:<8}"]

      --blame-palette <COLORS>
          Background colors used for git blame lines (space-separated
          string).

          Lines added by the same commit are painted with the same color;
          colors are recycled as needed.

      --blame-separator-format <FMT>
          Separator between the blame format and the code section of a git
          blame line.

          Contains the line number by default. Possible values are "none" to
          disable line numbers or a format string. This may contain one
          "{n:}" placeholder and will display the line number on every line.
          A type may be added after all other format specifiers and can be
          separated by '_': If type is set to 'block' (e.g. "{n:^4_block}")
          the line number will only be shown when a new blame block starts;
          or if it is set to 'every-N' the line will be show with every block
          and every N-th (modulo) line.

          [default: │{n:^4}│]

      --blame-separator-style <STYLE>
          Style string for the blame-separator-format

      --blame-timestamp-format <FMT>
          Format of `git blame` timestamp in raw git output received by delta

          [default: "%Y-%m-%d %H:%M:%S %z"]

      --blame-timestamp-output-format <FMT>
          Format string for git blame timestamp output.

          This string is used for formatting the timestamps in git blame
          output. It must follow the `strftime` format syntax specification.
          If it is not present, the timestamps will be formatted in a
          human-friendly but possibly less accurate form.

          See:
          <https://docs.rs/chrono/latest/chrono/format/strftime/index.html>

      --color-only
          Do not alter the input structurally in any way.

          But color and highlight hunk lines according to your delta
          configuration. This is mainly intended for other tools that use
          delta.

      --config <PATH>
          Load the config file at PATH instead of ~/.gitconfig

          [default: ]

      --commit-decoration-style <STYLE>
          Style string for the commit hash decoration.

          See STYLES section. The style string should contain one of the
          special attributes 'box', 'ul' (underline), 'ol' (overline), or the
          combination 'ul ol'.

          [default: ]

      --commit-regex <REGEX>
          Regular expression used to identify the commit line when parsing
          git output

          [default: "^commit "]

      --commit-style <STYLE>
          Style string for the commit hash line.

          See STYLES section. The style 'omit' can be used to remove the
          commit hash line from the output.

          [default: raw]

      --dark
          Use default colors appropriate for a dark terminal background.

          For more control, see the style options and --syntax-theme.

      --default-language <LANG>
          Default language used for syntax highlighting.

          Used as a fallback when the language cannot be inferred from a
          filename. It will typically make sense to set this in the
          per-repository config file '.git/config'.

          [default: txt]

      --detect-dark-light <DETECT_DARK_LIGHT>
          Detect whether or not the terminal is dark or light by querying for
          its colors.

          Ignored if either `--dark` or `--light` is specified.

          Querying the terminal for its colors requires "exclusive" access
          since delta reads/writes from the terminal and enables/disables raw
          mode. This causes race conditions with pagers such as less when
          they are attached to the same terminal as delta.

          This is usually only an issue when the output is manually piped to
          a pager. For example: `git diff | delta | less`. Otherwise, if
          delta starts the pager itself, then there's no race condition since
          the pager is started *after* the color is detected.

          `auto` tries to account for these situations by testing if the
          output is redirected.

          The `--color-only` option is treated as an indicator that delta is
          used as `interactive.diffFilter`. In this case the color is queried
          from the terminal even though the output is redirected.

          [default: auto]

          Possible values:
          - auto:   Only query the terminal for its colors if the output is
            not redirected
          - always: Always query the terminal for its colors
          - never:  Never query the terminal for its colors

  -@, --diff-args <STRING>
          Extra arguments to pass to `git diff` when using delta to diff two
          files.

          E.g. `delta --diff-args=-U999 file_1 file_2` is equivalent to `git
          diff --no-index --color -U999 file_1 file_2 | delta`.

          If you use process substitution (`delta <(command_1) <(command_2)`)
          and your git version doesn't support it, then delta will fall back
          to `diff` instead of `git diff`.

          [default: ]

      --diff-highlight
          Emulate diff-highlight.

          <https://github.com/git/git/tree/master/contrib/diff-highlight>

      --diff-so-fancy
          Emulate diff-so-fancy.

          <https://github.com/so-fancy/diff-so-fancy>

      --diff-stat-align-width <N>
          Width allocated for file paths in a diff stat section.

          If a relativized file path exceeds this width then the diff stat
          will be misaligned.

          [default: 48]

      --features <FEATURES>
          Names of delta features to activate (space-separated).

          A feature is a named collection of delta options in ~/.gitconfig.
          See FEATURES section. The environment variable DELTA_FEATURES can
          be set to a space-separated list of feature names. If this is
          preceded with a + character, the features from the environment
          variable will be added to those specified in git config. E.g.
          DELTA_FEATURES=+side-by-side can be used to activate side-by-side
          temporarily (use DELTA_FEATURES=+ to go back to just the features
          from git config).

      --file-added-label <STRING>
          Text to display before an added file path.

          Used in the default value of navigate-regex.

          [default: added:]

      --file-copied-label <STRING>
          Text to display before a copied file path

          [default: copied:]

      --file-decoration-style <STYLE>
          Style string for the file decoration.

          See STYLES section. The style string should contain one of the
          special attributes 'box', 'ul' (underline), 'ol' (overline), or the
          combination 'ul ol'.

          [default: "blue ul"]

      --file-modified-label <STRING>
          Text to display before a modified file path.

          Used in the default value of navigate-regex.

          [default: ]

      --file-removed-label <STRING>
          Text to display before a removed file path.

          Used in the default value of navigate-regex.

          [default: removed:]

      --file-renamed-label <STRING>
          Text to display before a renamed file path.

          Used in the default value of navigate-regex.

          [default: renamed:]

      --file-style <STYLE>
          Style string for the file section.

          See STYLES section. The style 'omit' can be used to remove the file
          section from the output.

          [default: blue]

      --file-transformation <SED_CMD>
          Sed-style command transforming file paths for display

      --generate-completion <GENERATE_COMPLETION>
          Print completion file for the given shell

          [possible values: bash, elvish, fish, powershell, zsh]

      --grep-context-line-style <STYLE>
          Style string for non-matching lines of grep output.

          See STYLES section. Defaults to zero-style.

      --grep-file-style <STYLE>
          Style string for file paths in grep output.

          See STYLES section.

          [default: magenta]

      --grep-header-decoration-style <STYLE>
          Style string for the header decoration in grep output.

          Default is "none" when grep-output-type-is "ripgrep", otherwise
          defaults to value of header-decoration-style. See
          hunk-header-decoration-style.

      --grep-header-file-style <STYLE>
          Style string for the file path part of the header in grep output.

          See hunk_header_file_style.

      --grep-line-number-style <STYLE>
          Style string for line numbers in grep output.

          See STYLES section.

          [default: green]

      --grep-output-type <OUTPUT_TYPE>
          Grep output format. Possible values: "ripgrep" - file name printed
          once, followed by matching lines within that file, each preceded by
          a line number. "classic" - file name:line number, followed by
          matching line. Default is "ripgrep" if `rg --json` format is
          detected, otherwise "classic"

          [possible values: ripgrep, classic]

      --grep-match-line-style <STYLE>
          Style string for matching lines of grep output.

          See STYLES section. Defaults to plus-style.

      --grep-match-word-style <STYLE>
          Style string for the matching substrings within a matching line of
          grep output.

          See STYLES section. Defaults to plus-style.

      --grep-separator-symbol <STRING>
          Separator symbol printed after the file path and line number in
          grep output.

          Defaults to ":" for both match and context lines, since many
          terminal emulators recognize constructs like "/path/to/file:7:".
          However, standard grep output uses "-" for context lines: set this
          option to "keep" to keep the original separator symbols.

          [default: :]

      --hunk-header-decoration-style <STYLE>
          Style string for the hunk-header decoration.

          See STYLES section. The style string should contain one of the
          special attributes 'box', 'ul' (underline), 'ol' (overline), or the
          combination 'ul ol'.

          [default: "blue box"]

      --hunk-header-file-style <STYLE>
          Style string for the file path part of the hunk-header.

          See STYLES section. The file path will only be displayed if
          hunk-header-style contains the 'file' special attribute.

          [default: blue]

      --hunk-header-line-number-style <STYLE>
          Style string for the line number part of the hunk-header.

          See STYLES section. The line number will only be displayed if
          hunk-header-style contains the 'line-number' special attribute.

          [default: blue]

      --hunk-header-style <STYLE>
          Style string for the hunk-header.

          See STYLES section. Special attributes 'file' and 'line-number' can
          be used to include the file path, and number of first hunk line, in
          the hunk header. The style 'omit' can be used to remove the hunk
          header section from the output.

          [default: "line-number syntax"]

      --hunk-label <STRING>
          Text to display before a hunk header.

          Used in the default value of navigate-regex.

          [default: ]

      --hyperlinks
          Render commit hashes, file names, and line numbers as hyperlinks.

          Following the hyperlink spec for terminal emulators:
          <https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda>.
          By default, file names and line numbers link to the local file
          using a file URL, whereas commit hashes link to the commit in
          GitHub, if the remote repository is hosted by GitHub. See
          --hyperlinks-file-link-format for full control over the file URLs
          emitted. Hyperlinks are supported by several common terminal
          emulators. To make them work, you must use less version >= 581 with
          the -R flag (or use -r with older less versions, but this will
          break e.g. --navigate). If you use tmux, then you will also need a
          patched fork of tmux (see <https://github.com/dandavison/tmux>).

      --hyperlinks-commit-link-format <FMT>
          Format string for commit hyperlinks (requires --hyperlinks).

          The placeholder "{commit}" will be replaced by the commit hash. For
          example:
          --hyperlinks-commit-link-format='https://mygitrepo/{commit}/'

      --hyperlinks-file-link-format <FMT>
          Format string for file hyperlinks (requires --hyperlinks).

          Placeholders "{path}" and "{line}" will be replaced by the absolute
          file path and the line number; "{host}" with the hostname delta is
          currently running on. The default is to create a hyperlink
          containing a standard file URI with only the filename, which your
          terminal or OS should handle. You can specify any scheme, such as
          "file-line://{path}:{line}" and register an application to handle
          it. See <https://dandavison.github.io/delta/hyperlinks.html> for
          details.

          [default: file://{path}]

      --inline-hint-style <STYLE>
          Style string for short inline hint text.

          This styles certain content added by delta to the original diff
          such as special characters to highlight tabs, and the symbols used
          to indicate wrapped lines. See STYLES section.

          [default: blue]

      --inspect-raw-lines <true|false>
          Kill-switch for --color-moved support.

          Whether to examine ANSI color escape sequences in raw lines
          received from Git and handle lines colored in certain ways
          specially. This is on by default: it is how Delta supports Git's
          --color-moved feature. Set this to "false" to disable this
          behavior.

          [default: true]
          [possible values: true, false]

      --keep-plus-minus-markers
          Prefix added/removed lines with a +/- character, as git does.

          By default, delta does not emit any prefix, so code can be copied
          directly from delta's output.

      --light
          Use default colors appropriate for a light terminal background.

          For more control, see the style options and --syntax-theme.

      --line-buffer-size <N>
          Size of internal line buffer.

          Delta compares the added and removed versions of nearby lines in
          order to detect and highlight changes at the level of individual
          words/tokens. Therefore, nearby lines must be buffered internally
          before they are painted and emitted. Increasing this value might
          improve highlighting of some large diff hunks. However, setting
          this to a high value will adversely affect delta's performance when
          entire files are added/removed.

          [default: 32]

      --line-fill-method <STRING>
          Line-fill method in side-by-side mode.

          How to extend the background color to the end of the line in
          side-by-side mode. Can be ansi (default) or spaces (default if
          output is not to a terminal). Has no effect if --width=variable is
          given.

          [possible values: ansi, spaces]

  -n, --line-numbers
          Display line numbers next to the diff.

          See LINE NUMBERS section.

      --line-numbers-left-format <FMT>
          Format string for the left column of line numbers.

          A typical value would be "{nm:^4}⋮" which means to display the line
          numbers of the minus file (old version), center-aligned, padded to
          a width of 4 characters, followed by a dividing character. See the
          LINE NUMBERS section.

          [default: {nm:^4}⋮]

      --line-numbers-left-style <STYLE>
          Style string for the left column of line numbers.

          See STYLES and LINE NUMBERS sections.

          [default: auto]

      --line-numbers-minus-style <STYLE>
          Style string for line numbers in the old (minus) version of the
          file.

          See STYLES and LINE NUMBERS sections.

          [default: auto]

      --line-numbers-plus-style <STYLE>
          Style string for line numbers in the new (plus) version of the
          file.

          See STYLES and LINE NUMBERS sections.

          [default: auto]

      --line-numbers-right-format <FMT>
          Format string for the right column of line numbers.

          A typical value would be "{np:^4}│ " which means to display the
          line numbers of the plus file (new version), center-aligned, padded
          to a width of 4 characters, followed by a dividing character, and a
          space. See the LINE NUMBERS section.

          [default: {np:^4}│]

      --line-numbers-right-style <STYLE>
          Style string for the right column of line numbers.

          See STYLES and LINE NUMBERS sections.

          [default: auto]

      --line-numbers-zero-style <STYLE>
          Style string for line numbers in unchanged (zero) lines.

          See STYLES and LINE NUMBERS sections.

          [default: auto]

      --list-languages
          List supported languages and associated file extensions

      --list-syntax-themes
          List available syntax-highlighting color themes

      --map-styles <STYLES_MAP>
          Map styles encountered in raw input to desired output styles.

          An example is --map-styles='bold purple => red "#eeeeee", bold cyan
          => syntax "#eeeeee"'

      --max-line-distance <DIST>
          Maximum line pair distance parameter in within-line diff algorithm.

          This parameter is the maximum distance (0.0 - 1.0) between two
          lines for them to be inferred to be homologous. Homologous line
          pairs are highlighted according to the deletion and insertion
          operations transforming one into the other.

          [default: 0.6]

      --max-syntax-highlighting-length <N>
          Stop syntax highlighting lines after this many characters.

          To always highlight entire lines, set to zero - but note that delta
          will be slow on very long lines (e.g. minified .js).

          [default: 400]

      --max-line-length <N>
          Truncate lines longer than this.

          To prevent any truncation, set to zero. When wrapping lines this
          does nothing as it is overwritten to fit at least all visible
          characters, see `--wrap-max-lines`.

          [default: 3000]

      --merge-conflict-begin-symbol <STRING>
          String marking the beginning of a merge conflict region.

          The string will be repeated until it reaches the required length.

          [default: ▼]

      --merge-conflict-end-symbol <STRING>
          String marking the end of a merge conflict region.

          The string will be repeated until it reaches the required length.

          [default: ▲]

      --merge-conflict-ours-diff-header-decoration-style <STYLE>
          Style string for the decoration of the header above the 'ours'
          merge conflict diff.

          This styles the decoration of the header above the diff between the
          ancestral commit and the 'ours' branch. See STYLES section. The
          style string should contain one of the special attributes 'box',
          'ul' (underline), 'ol' (overline), or the combination 'ul ol'.

          [default: box]

      --merge-conflict-ours-diff-header-style <STYLE>
          Style string for the header above the 'ours' branch merge conflict
          diff.

          See STYLES section.

          [default: normal]

      --merge-conflict-theirs-diff-header-decoration-style <STYLE>
          Style string for the decoration of the header above the 'theirs'
          merge conflict diff.

          This styles the decoration of the header above the diff between the
          ancestral commit and 'their' branch.  See STYLES section. The style
          string should contain one of the special attributes 'box', 'ul'
          (underline), 'ol' (overline), or the combination 'ul ol'.

          [default: box]

      --merge-conflict-theirs-diff-header-style <STYLE>
          Style string for the header above the 'theirs' branch merge
          conflict diff.

          This styles the header above the diff between the ancestral commit
          and 'their' branch. See STYLES section.

          [default: normal]

      --minus-empty-line-marker-style <STYLE>
          Style string for removed empty line marker.

          Used only if --minus-style has no background color.

          [default: "normal auto"]

      --minus-emph-style <STYLE>
          Style string for emphasized sections of removed lines.

          See STYLES section.

          [default: "normal auto"]

      --minus-non-emph-style <STYLE>
          Style string for non-emphasized sections of removed lines that have
          an emphasized section.

          See STYLES section.

          [default: minus-style]

      --minus-style <STYLE>
          Style string for removed lines.

          See STYLES section.

          [default: "normal auto"]

      --navigate
          Activate diff navigation.

          Use n to jump forwards and N to jump backwards. To change the file
          labels used see --file-added-label, --file-copied-label,
          --file-modified-label, --file-removed-label, --file-renamed-label.

      --navigate-regex <REGEX>
          Regular expression defining navigation stop points

      --no-gitconfig
          Do not read any settings from git config.

          See GIT CONFIG section.

      --pager <CMD>
          Which pager to use.

          The default pager is `less`. You can also change pager by setting
          the environment variable DELTA_PAGER, or PAGER. This option
          overrides these environment variables.

      --paging <auto|always|never>
          Whether to use a pager when displaying output.

          Options are: auto, always, and never.

          [default: auto]
          [possible values: auto, always, never]

      --parse-ansi
          Display ANSI color escape sequences in human-readable form.

          Example usage: git show --color=always | delta --parse-ansi This
          can be used to help identify input style strings to use with
          map-styles.

      --plus-emph-style <STYLE>
          Style string for emphasized sections of added lines.

          See STYLES section.

          [default: "syntax auto"]

      --plus-empty-line-marker-style <STYLE>
          Style string for added empty line marker.

          Used only if --plus-style has no background color.

          [default: "normal auto"]

      --plus-non-emph-style <STYLE>
          Style string for non-emphasized sections of added lines that have
          an emphasized section.

          See STYLES section.

          [default: plus-style]

      --plus-style <STYLE>
          Style string for added lines.

          See STYLES section.

          [default: "syntax auto"]

      --raw
          Do not alter the input in any way.

          This is mainly intended for testing delta.

      --relative-paths
          Output all file paths relative to the current directory.

          This means that they will resolve correctly when clicked on or used
          in shell commands.

      --right-arrow <STRING>
          Text to display with a changed file path.

          For example, a unified diff heading, a rename, or a chmod.

          [default: "⟶  "]

      --show-colors
          Show available named colors.

          In addition to named colors, arbitrary colors can be specified
          using RGB hex codes. See COLORS section.

      --show-config
          Display the active values for all Delta options.

          Style string options are displayed with foreground and background
          colors. This can be used to experiment with colors by combining
          this option with other options such as --minus-style, --zero-style,
          --plus-style, --light, --dark, etc.

      --show-syntax-themes
          Show example diff for available syntax-highlighting themes.

          If diff output is supplied on standard input then this will be used
          for the demo. For example: `git show | delta --show-syntax-themes`.

      --show-themes
          Show example diff for available delta themes.

          A delta theme is a delta named feature (see --features) that sets
          either `light` or `dark`. See
          <https://github.com/dandavison/delta#custom-color-themes>. If diff
          output is supplied on standard input then this will be used for the
          demo. For example: `git show | delta --show-themes`. By default
          shows dark or light themes only, according to whether delta is in
          dark or light mode (as set by the user or inferred from BAT_THEME).
          To control the themes shown, use --dark or --light, or both, on the
          command line together with this option.

  -s, --side-by-side
          Display diffs in side-by-side layout

      --syntax-theme <SYNTAX_THEME>
          The syntax-highlighting theme to use.

          Use --show-syntax-themes to demo available themes. Defaults to the
          value of the BAT_THEME environment variable, if that contains a
          valid theme name. --syntax-theme=none disables all syntax
          highlighting.

      --tabs <N>
          The number of spaces to replace tab characters with.

          Use --tabs=0 to pass tab characters through directly, but note that
          in that case delta will calculate line widths assuming tabs occupy
          one character's width on the screen: if your terminal renders tabs
          as more than one character wide then delta's output will look
          incorrect.

          [default: 8]

      --true-color <auto|always|never>
          Whether to emit 24-bit ("true color") RGB color codes.

          Options are auto, always, and never. "auto" means that delta will
          emit 24-bit color codes if the environment variable COLORTERM has
          the value "truecolor" or "24bit". If your terminal application (the
          application you use to enter commands at a shell prompt) supports
          24 bit colors, then it probably already sets this environment
          variable, in which case you don't need to do anything.

          [default: auto]
          [possible values: auto, always, never]

      --whitespace-error-style <STYLE>
          Style string for whitespace errors.

          Defaults to color.diff.whitespace if that is set in git config, or
          else 'magenta reverse'.

          [default: "auto auto"]

  -w, --width <N>
          The width of underline/overline decorations.

          Examples: "72" (exactly 72 characters), "-2" (auto-detected
          terminal width minus 2). An expression such as "74-2" is also valid
          (equivalent to 72 but may be useful if the caller has a variable
          holding the value "74"). Use --width=variable to extend decorations
          and background colors to the end of the text only. Otherwise
          background colors extend to the full terminal width.

      --word-diff-regex <REGEX>
          Regular expression defining a 'word' in within-line diff algorithm.

          The regular expression used to decide what a word is for the
          within-line highlight algorithm. For less fine-grained matching
          than the default try --word-diff-regex="\S+"
          --max-line-distance=1.0 (this is more similar to `git
          --word-diff`).

          [default: \w+]

      --wrap-left-symbol <STRING>
          End-of-line wrapped content symbol (left-aligned).

          Symbol added to the end of a line indicating that the content has
          been wrapped onto the next line and continues left-aligned.

          [default: ↵]

      --wrap-max-lines <N>
          How often a line should be wrapped if it does not fit.

          Zero means to never wrap. Any content which does not fit after
          wrapping will be truncated. A value of "unlimited" means a line
          will be wrapped as many times as required.

          [default: 2]

      --wrap-right-percent <PERCENT>
          Threshold for right-aligning wrapped content.

          If the length of the remaining wrapped content, as a percentage of
          width, is less than this quantity it will be right-aligned.
          Otherwise it will be left-aligned.

          [default: 37.0]

      --wrap-right-prefix-symbol <STRING>
          Pre-wrapped content symbol (right-aligned).

          Symbol displayed before right-aligned wrapped content.

          [default: …]

      --wrap-right-symbol <STRING>
          End-of-line wrapped content symbol (right-aligned).

          Symbol added to the end of a line indicating that the content has
          been wrapped onto the next line and continues right-aligned.

          [default: ↴]

      --zero-style <STYLE>
          Style string for unchanged lines.

          See STYLES section.

          [default: "syntax normal"]

      --24-bit-color <auto|always|never>
          Deprecated: use --true-color

          [possible values: auto, always, never]

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version


Git config

  By default, delta takes settings from a section named "delta" in git config
  files, if one is present. The git config file to use for delta options will
  usually be ~/.gitconfig, but delta follows the rules given in
  <https://git-scm.com/docs/git-config#FILES>. Most delta options can be
  given in a git config file, using the usual option names but without the
  initial '--'. An example is

  [delta]
      line-numbers = true
      zero-style = dim syntax


Features

  A feature is a named collection of delta options in git config. An example
  is:

  [delta "my-delta-feature"]
      syntax-theme = Dracula
      plus-style = bold syntax "#002800"

  To activate those options, you would use:

  delta --features my-delta-feature

  A feature name may not contain whitespace. You can activate multiple
  features:

  [delta]
      features = my-highlight-styles-colors-feature my-line-number-styles-feature

  If more than one feature sets the same option, the last one wins.

  If an option is present in the [delta] section, then features are not
  considered at all.

  If you want an option to be fully overridable by a feature and also have a
  non default value when no features are used, then you need to define a
  "default" feature and include it in the main delta configuration.

  For instance:

  [delta]
      feature = default-feature

  [delta "default-feature"]
      width = 123

  At this point, you can override features set in the command line or in the
  environment variables and the "last one wins" rules will apply as expected.


Styles

  All options that have a name like --*-style work the same way. It is very
  similar to how colors/styles are specified in a gitconfig file:
  <https://git-scm.com/docs/git-config#Documentation/git-config.txt-color>

  Here is an example:

  --minus-style 'red bold ul "#ffeeee"'

  That means: For removed lines, set the foreground (text) color to 'red',
  make it bold and underlined, and set the background color to '#ffeeee'.

  See the Colors section below for how to specify a color. In addition to
  real colors, there are 4 special color names: 'auto', 'normal', 'raw', and
  'syntax'.

  Here is an example of using special color names together with a single
  attribute:

  --minus-style 'syntax bold auto'

  That means: For removed lines, syntax-highlight the text, and make it bold,
  and do whatever delta normally does for the background.

  The available attributes are: 'blink', 'bold', 'dim', 'hidden', 'italic',
  'reverse', 'strike', and 'ul' (or 'underline').

  The attribute 'omit' is supported by commit-style, file-style, and
  hunk-header-style, meaning to remove the element entirely from the output.

  A complete description of the style string syntax follows:

  - If the input that delta is receiving already has colors, and you want
    delta to output those colors unchanged, then use the special style string
    'raw'. Otherwise, delta will strip any colors from its input.

  - A style string consists of 0, 1, or 2 colors, together with an arbitrary
    number of style attributes, all separated by spaces.

  - The first color is the foreground (text) color. The second color is the
    background color. Attributes can go in any position.

  - This means that in order to specify a background color you must also
    specify a foreground (text) color.

  - If you want delta to choose one of the colors automatically, then use the
    special color 'auto'. This can be used for both foreground and
    background.

  - If you want the foreground/background color to be your terminal's
    foreground/background color, then use the special color 'normal'.

  - If you want the foreground text to be syntax-highlighted according to its
    language, then use the special foreground color 'syntax'. This can only
    be used for the foreground (text).

  - The minimal style specification is the empty string ''. This means: do
    not apply any colors or styling to the element in question.


Colors

  There are four ways to specify a color (this section applies to foreground
  and background colors within a style string):

  1. CSS color name

     Any of the 140 color names used in CSS:
     <https://www.w3schools.com/colors/colors_groups.asp>

  2. RGB hex code

     An example of using an RGB hex code is:
     --file-style="#0e7c0e"

  3. ANSI color name

     There are 8 ANSI color names:
     black, red, green, yellow, blue, magenta, cyan, white.

     In addition, all of them have a bright form:
     brightblack, brightred, brightgreen, brightyellow, brightblue,
     brightmagenta, brightcyan, brightwhite.

     An example of using an ANSI color name is:
     --file-style="green"

     Unlike RGB hex codes, ANSI color names are just names: you can choose
     the exact color that each name corresponds to in the settings of your
     terminal application (the application you use to enter commands at a
     shell prompt). This means that if you use ANSI color names, and you
     change the color theme used by your terminal, then delta's colors will
     respond automatically, without needing to change the delta command line.

     "purple" is accepted as a synonym for "magenta". Color names and codes
     are case-insensitive.

  4. ANSI color number

     An example of using an ANSI color number is:
     --file-style=28

     There are 256 ANSI color numbers: 0-255. The first 16 are the same as
     the colors described in the "ANSI color name" section above. See
     <https://en.wikipedia.org/wiki/ANSI_escape_code#8-bit>. Specifying
     colors like this is useful if your terminal only supports 256 colors
     (i.e. doesn't support 24-bit color).


Line Numbers

  To display line numbers, use --line-numbers.

  Line numbers are displayed in two columns. Here's what it looks like by
  default:

    1 ⋮  1 │ unchanged line
    2 ⋮    │ removed line
      ⋮  2 │ added line

  In that output, the line numbers for the old (minus) version of the file
  appear in the left column, and the line numbers for the new (plus) version
  of the file appear in the right column. In an unchanged (zero) line, both
  columns contain a line number.

  The following options allow the line number display to be customized:

  --line-numbers-left-format:  Change the contents of the left column
  --line-numbers-right-format: Change the contents of the right column
  --line-numbers-left-style:   Change the style applied to the left column
  --line-numbers-right-style:  Change the style applied to the right column
  --line-numbers-minus-style:  Change the style applied to line numbers in
  minus lines
  --line-numbers-zero-style:   Change the style applied to line numbers in
  unchanged lines
  --line-numbers-plus-style:   Change the style applied to line numbers in
  plus lines

  Options --line-numbers-left-format and --line-numbers-right-format allow
  you to change the contents of the line number columns. Their values are
  arbitrary format strings, which are allowed to contain the placeholders
  {nm} for the line number associated with the old version of the file and
  {np} for the line number associated with the new version of the file. The
  placeholders support a subset of the string formatting syntax documented
  here: <https://doc.rust-lang.org/std/fmt/#formatting-parameters>.
  Specifically, you can use the alignment and width syntax.

  For example, the default value of --line-numbers-left-format is '{nm:^4}⋮'.
  This means that the left column should display the minus line number (nm),
  center-aligned, padded with spaces to a width of 4 characters, followed by
  a unicode dividing-line character (⋮).

  Similarly, the default value of --line-numbers-right-format is '{np:^4}│'.
  This means that the right column should display the plus line number (np),
  center-aligned, padded with spaces to a width of 4 characters, followed by
  a unicode dividing-line character (│).

  Use '<' for left-align, '^' for center-align, and '>' for right-align.


Support

  If something isn't working correctly, or you have a feature request, please
  open an issue at <https://github.com/dandavison/delta/issues>.

  For a short help summary, please use delta -h.
```

## Spec 3

### CLI grammar and validation

Options may precede, follow, or be interleaved with positional operands. Long value options accept both `--name value` and `--name=value`. Boolean options take no value. `-n` is `--line-numbers`, `-s` is `--side-by-side`, `-w` is `--width`, `-@` is `--diff-args`, and `-V` is version. Boolean short flags can be combined, so `-ns` is byte-for-byte equivalent to `-n -s`. `-@=U3` and `-w=100` are accepted. Unlike an ordinary short value option, `-@` also accepts its value glued directly to the option without `=`: the spellings `-@-u`, `-@-U`, `-@-U0`, `-@-U5`, `-@-U7`, `-@U1`, and `-@-ux` all reach direct-comparison processing rather than being rejected by the CLI. In `-@U1`, the supplied value is `U1`, to which Spec 37 adds the missing leading dash. A dash-prefixed value separated from `-@` by whitespace must instead use the equals form or be attached directly to `-@`, because `-@ -U3` parses `-U` as an unexpected option.

`--` ends option parsing. Later dash-prefixed tokens are positional filenames, never help or unknown options. Each single-value option may occur at most once: repetition (including `--width` or `--features`) exits 2 and says it “cannot be used multiple times”, naming the option metavariable. Missing values exit 2 and say that a value is required. Unknown long/short options and surplus positionals exit 2 with an error containing `unexpected argument '<token>' found`, a usage line, and `For more information, try '--help'.` In parser diagnostics the usage program name is the invoked basename, thus normally `Usage: executable [OPTIONS] [MINUS_FILE] [PLUS_FILE]`; normal help deliberately says `delta`.

`--dark` and `--light` are mutually exclusive in normal parsing. Either order exits 2 and mentions both; the theme-preview path uses the exact diagnostic `--light and --dark cannot be used together`. Help/version precedence still applies.

## Spec 4

### Accepted option types

Recognize all options below. An option being accepted means it parses, can be combined with unrelated options, and empty stdin exits 0 unless its documented action produces output.

- Booleans: `--color-only`, `--dark`, `--diff-highlight`, `--diff-so-fancy`, `--hyperlinks`, `--keep-plus-minus-markers`, `--light`, `--line-numbers`, `--list-languages`, `--list-syntax-themes`, `--navigate`, `--no-gitconfig`, `--parse-ansi`, `--raw`, `--relative-paths`, `--show-colors`, `--show-config`, `--show-syntax-themes`, `--show-themes`, and `--side-by-side`.
- Integer-like values: `--tabs`, `--max-line-length`, `--max-syntax-highlighting-length`, `--line-buffer-size`, `--wrap-max-lines`, and `--diff-stat-align-width`. Decimal integers are accepted; zero is valid, including for line-buffer size. Overflow and nonsensical negatives must be handled as validation results, never crashes. `--wrap-max-lines` also accepts `unlimited`.
- Numeric values: `--max-line-distance` accepts floating point, including negative values; `--wrap-right-percent` accepts floating point.
- Enumerations: `--paging` is `auto|always|never`; `--true-color`, deprecated alias `--24-bit-color`, and `--detect-dark-light` are `auto|always|never`; `--grep-output-type` is `ripgrep|classic`; `--inspect-raw-lines` is exactly `true|false`; `--line-fill-method` is `ansi|spaces`; `--generate-completion` is `bash|elvish|fish|powershell|zsh`.
- Free strings: `--features`, `--default-language`, `--commit-regex`, all labels and symbols, blame format options, grep separator, hyperlink formats, line-number formats, `--navigate-regex`, `--word-diff-regex`, `--file-transformation`, and pager command. Preserve spaces, tabs, newlines, quotes, punctuation, and Unicode in these values.
- Styles: every option ending `-style`, including commit/file/hunk/diff-line/line-number/grep/blame/merge-conflict styles, uses Spec 12.

Invalid enumeration values exit 2, show the bad value and the complete possible-value list. For `--inspect-raw-lines=invalid`, the styled or ANSI-stripped diagnostic is `error: invalid value 'invalid' for '--inspect-raw-lines <true|false>'` followed by `[possible values: true, false]` and the help hint. `--paging=invalid` analogously lists `auto, always, never`. A near miss for completion such as `bad` also includes `tip: a similar value exists`.

Parser diagnostics are ANSI-styled when `TERM=xterm-256color` and `NO_COLOR` is absent. For the five observed invalid-value invocations below, stdout is empty, status is 2, and stderr is exactly the indicated byte sequence after replacing each written `ESC` with byte `0x1b` (each block has the displayed final newline):

`--max-line-distance=invalid`:

```text
ESC[1mESC[31merror:ESC[0m invalid value 'ESC[33minvalidESC[0m' for 'ESC[1m--max-line-distance <DIST>ESC[0m': invalid float literal

For more information, try 'ESC[1m--helpESC[0m'.
```

`--inspect-raw-lines=invalid`:

```text
ESC[1mESC[31merror:ESC[0m invalid value 'ESC[33minvalidESC[0m' for 'ESC[1m--inspect-raw-lines <true|false>ESC[0m'
  [possible values: ESC[32mtrueESC[0m, ESC[32mfalseESC[0m]

For more information, try 'ESC[1m--helpESC[0m'.
```

`--line-buffer-size=not_a_number`:

```text
ESC[1mESC[31merror:ESC[0m invalid value 'ESC[33mnot_a_numberESC[0m' for 'ESC[1m--line-buffer-size <N>ESC[0m': invalid digit found in string

For more information, try 'ESC[1m--helpESC[0m'.
```

`--tabs=invalid`:

```text
ESC[1mESC[31merror:ESC[0m invalid value 'ESC[33minvalidESC[0m' for 'ESC[1m--tabs <N>ESC[0m': invalid digit found in string

For more information, try 'ESC[1m--helpESC[0m'.
```

`--paging=invalid`:

```text
ESC[1mESC[31merror:ESC[0m invalid value 'ESC[33minvalidESC[0m' for 'ESC[1m--paging <auto|always|never>ESC[0m'
  [possible values: ESC[32mautoESC[0m, ESC[32malwaysESC[0m, ESC[32mneverESC[0m]

For more information, try 'ESC[1m--helpESC[0m'.
```

## Spec 5

### Numeric width and default settings

`--width` accepts a positive decimal display width, `variable`, a negative terminal offset such as `-2`, or one subtraction expression such as `74-2`/`80-10`. The non-TTY terminal width fallback is 80. A negative argument means terminal width minus its magnitude. A dash-prefixed value must be attached to the option: `--width=-5000`, `-w=-5000`, and `-w-5000` all reach width validation and produce `Invalid value for width: the current terminal width of 80 minus 5000 is negative`. In contrast, the space-separated invocation `--width -5000 --no-gitconfig` never reaches width validation: it exits 2 with parser stderr beginning `error: unexpected argument '-5' found`, followed by the tip `tip: to pass '-5' as a value, use '-- -5'`, usage, and the help hint. Reject other attached text with `Invalid value for width: "VALUE" is not an integer`; reject a subtraction whose result is nonpositive with `Invalid value for width: expression "10-20" is not positive`. Attached long and short width forms have identical validation text.

With git config disabled and a non-TTY output, important defaults are:

```text
commit-style = raw                    file-style = blue
file-decoration-style = blue ul      hunk-header-style = line-number syntax
hunk-header-decoration-style = blue box
minus-style = normal 52               minus-non-emph-style = normal 52
minus-emph-style = normal 124         minus-empty-line-marker-style = normal 52
zero-style = syntax normal
plus-style = syntax 22                plus-non-emph-style = syntax 22
plus-emph-style = syntax 28           plus-empty-line-marker-style = normal 22
grep-file-style = purple              grep-line-number-style = green
whitespace-error-style = reverse purple
blame-palette = #000000 #222222 #444444
true-color = false                    inspect-raw-lines = true
keep-plus-minus-markers = false       line-numbers = false
max-line-distance = 0.6               max-line-length = 3000
max-syntax-highlighting-length = 400  line-buffer-size = 32
diff-stat-align-width = 48            line-fill-method = spaces
navigate = false                      pager = none
paging = auto                         side-by-side = false
syntax-theme = Monokai Extended       width = 80
tabs = 8                              word-diff-regex = \w+
file-added-label = added:             file-modified-label = (empty)
file-removed-label = removed:         file-renamed-label = renamed:
file-copied-label = copied:           hunk-label = (empty)
right-arrow = "⟶  "                  wrap-max-lines = 2
wrap-left-symbol = ↵                  wrap-right-symbol = ↴
wrap-right-prefix-symbol = …          wrap-right-percent = 37.0
```

## Spec 6

### Configuration files and precedence

Unless `--no-gitconfig` is present, read Git-format configuration using normal Git global/local discovery, including `$HOME/.gitconfig`. Delta options come from `[delta]`, with option names lacking the leading `--`. `--config PATH` replaces normal config discovery with that file. A malformed explicitly named file must return nonzero and write a diagnostic containing `failed to read git config` or `failed to parse`.

Apply layers from weakest to strongest: built-in defaults; activated feature sections; the main `[delta]` section; environment overrides; explicit CLI options. Thus CLI `--file-style=blue` defeats config `file-style=omit`, and `--no-gitconfig` ignores a home config completely. Boolean strings in config are parsed as booleans.

A feature is a space-separated named collection stored in `[delta "NAME"]`. Built-in features include at least `raw`, `side-by-side`, and `line-numbers`; custom feature sections may themselves name more features and are expanded recursively without looping. Apply named features in listed order, with the last value winning. A value in the main `[delta]` section takes priority over feature-derived values.

`DELTA_FEATURES` without leading `+` replaces the configured feature list (including an empty value). With leading `+`, append its names to the configured list; `+ ` preserves existing features while adding none. Feature combinations must compose, and later conflicting features win.

## Spec 7

### Input recognition and safe pass-through

Classify a stream incrementally. Recognize Git patches, conventional unified diffs, combined merge diffs, Git log/commit metadata, Git blame, Git/ripgrep results, diff-stat blocks, submodule blocks, binary-file notices, and merge conflicts. Unrecognized text is emitted in original order rather than discarded. Recognition may start after arbitrary preamble text and must reset correctly between concatenated diffs, files, hunks, and commits.

Preserve blank lines, significant spaces/tabs, Unicode, CRLF content (strip orphan carriage returns rather than printing `\r`), `\ No newline at end of file` markers, and code lines beginning with three dashes. Standalone `Binary files A and B differ` and `Files A and B are identical` lines pass through unchanged. A directory-diff line such as `Only in foo: bar` is instead rendered as a file-style structural heading: insert a preceding blank line, paint that text blue with its own reset, then emit a separate blue full-width underline and newline. NUL and malformed UTF-8 must not crash processing; replace undecodable bytes with U+FFFD where textual conversion is necessary, while preserving all remaining content.

Do not truncate or lose data solely because an input is large, a hunk exceeds the line buffer, paths or commit messages are very long, or multiple files are present.

## Spec 8

### Unified/Git diff structure

Recognize file starts from `diff --git a/OLD b/NEW`, conventional `--- OLD`/`+++ NEW` pairs (including timestamps), `/dev/null`, `new file mode`, `deleted file mode`, `old mode`/`new mode`, `rename from`/`rename to`, `copy from`/`copy to`, similarity/index lines, `diff --cc`/`diff --combined`, and no-index diffs. Suppress low-level Git header records in normal display and replace them with one styled file header. Preserve them in raw and color-only modes.

Normal file headers use displayed paths with leading Git `a/` and `b/` removed when a preceding Git header such as `diff --git a/PATH b/PATH` establishes them as Git prefixes. In that case a same-path modification shows `[file-modified-label + space if nonempty]PATH`. A standalone conventional unified `--- OLD`/`+++ NEW` pair does not infer or strip Git prefixes: `--- a/file` followed by `+++ b/file` is displayed as exactly `a/file ⟶   b/file`, even though the suffixes become equal if `a/` and `b/` are removed. This behavior is unchanged by line-number, side-by-side, configured-feature, environment-feature, or CLI-override activation. Other different old/new paths show `OLD ⟶   NEW` using the configurable arrow (the default value includes two trailing spaces, plus the layout separator). Additions show `added: PATH`; removals `removed: PATH`; renames `renamed: OLD ⟶   NEW`; copies `copied: OLD ⟶   NEW`. Exactly one operation header is emitted per file, including metadata-only empty additions. `--file-modified-label comparing:` yields `comparing: OLD` and also shows NEW.

For a non-rename operation, mode changes append `(mode +x)` for 100644→100755, `(mode -x)` for the reverse, or `(mode OLD ⟶   NEW)` for other bit patterns. When rename metadata and mode-change metadata occur in the same file block, the single header shows only the rename; for the observed 100644→100755 case it is exactly `renamed: old.txt ⟶   new.txt`, with no `(mode +x)` suffix. Binary operations identify the path and include `(binary file)` in the visible header. Binary add/remove uses the corresponding label.

## Spec 9

### File paths

Preserve literal `.`, `..`, and repeated `/` path components in displayed paths; do not remove, resolve, or collapse them lexically. Thus paths `./src/../src/./main.rs`, `a/b/c/../../d/./e/../f.rs`, and `b/foo//baz.txt` are displayed with exactly those component strings. Preserve a leading `/` and do not lowercase. Handle paths beginning with `..`, paths ending in dots, backslashes/mixed separators, quoted Git paths containing escaped control characters, embedded spaces or tabs, Unicode/emoji, very long/deep names, and empty components without crashing.

With `--relative-paths`, transform repository-root-relative paths relative to the current subdirectory represented by `GIT_PREFIX`. For example from `src/`, `src/handlers/module.rs` becomes `handlers/module.rs` and `lib/core/util.rs` becomes `../lib/core/util.rs`; from `src/handlers/`, the first becomes `module.rs`. Hyperlink targets still resolve to absolute paths even when link text is relative.

Then apply `--file-transformation SED_CMD` to paths established by Git file metadata. It has form `s<delimiter>pattern<delimiter>replacement<delimiter>flags`, with any consistent delimiter. Use regular expressions, `$1` capture substitutions, `g` (all matches), `i` (case-insensitive), `m`, `s`, `x` (ignore unescaped pattern whitespace/comments), and `U` (swap greed). Only dollar-number syntax interpolates a capture: a replacement containing `\1` preserves those two characters literally. For example, applying `s/v([0-9]+)/version_\1/` to `src_v1/main.rs` produces `src_version_\1/main.rs`, whereas `s/v([0-9]+)/version_$1/` produces `src_version_1/main.rs`. Without `g`, replace only the first match. Empty pattern inserts at the start; `^`/`$` anchors work. Invalid/incomplete commands are silently ignored. When both relative paths and transformation are active on such a Git path, relativize first, then transform.

A standalone conventional `---`/`+++` pair has a different path pipeline: file transformation is not applied. Thus `--- a/foo/./bar/../baz.txt` and `+++ b/foo//baz.txt` remain visibly `a/foo/./bar/../baz.txt ⟶   b/foo//baz.txt` under `--file-transformation=s|foo/|src/|`. If `--relative-paths` is also used with `GIT_PREFIX=src/handlers/`, standalone paths `a/src/handlers/module.rs` and `b/src/handlers/module.rs` become `../../a/src/handlers/module.rs` and `../../b/src/handlers/module.rs`; a simultaneous `s|module|unit|` transformation is still not applied.

## Spec 10

### Hunk parsing and normal layout

Recognize `@@ -a,b +c,d @@ optional fragment` and combined forms with one old range per parent. Maintain old/new counters from those ranges. A context line advances both; removal advances old only; addition advances new only. Combined-diff prefixes may be two or three characters and each parent marker is interpreted independently; mixed prefixes such as ` -`, ` +`, `+-`, `++`, `--`, and `+++` must not confuse state.

In default structural mode, omit literal `@@` syntax and draw a hunk header. With defaults the visible form in the one-digit, no-fragment case is a blank line followed by `───┐`, then `FIRST_NEW_LINE: │`, then `───┘`, all blue; include the syntax-highlighted hunk fragment beside/within this box when present. Make the top and bottom horizontal runs as wide as all middle-row content before the right `│`, including every line-number digit, punctuation, fragment, and surrounding spaces. Thus a middle row visibly beginning `10: │` has four horizontal characters in each run, while `2: line 1 │` has ten. The byte-level painting deliberately does not coalesce adjacent blue components: in the one-digit, no-fragment case the top is `ESC[34m───ESC[0mESC[34m┐ESC[0m\n`, the middle starts `ESC[34mFIRST_NEW_LINEESC[0m: ESC[34m│ESC[0m`, and the bottom is `ESC[34m───ESC[0mESC[34m┘ESC[0m\n`. The file title and its full-width underline are likewise separate reset-terminated blue spans. This reset/component separation remains for ordinary unified hunks, combined hunks with mixed prefixes, one-line and multiple hunks, and hunks containing `\ No newline at end of file`; that marker itself is emitted as an unstyled literal line after the reset and fill span of the changed line. It also remains when line truncation, a syntax-highlighting limit, line numbers, side-by-side layout, hyperlinks, navigation, file transformation, merge-conflict rendering, or paging is enabled; navigation labels can change the horizontal-run length and middle content but not merge a run with its corner. It remains for a patch following commit metadata and for patches generated by two-operand direct comparison, regardless of the selected diff arguments or custom minus/plus colors, backgrounds, or font attributes. `hunk-header-style` special tokens `file` and `line-number` control inclusion of the file and first new line; `omit` removes the header, `raw` prints the raw hunk line, and an empty/`none` style produces the corresponding undecorated form. `--hunk-label` prefixes the header.

Recognize any hunk whose old and new counts are both zero, including `@@ -0,0 +0,0 @@` and `@@ -1,0 +1,0 @@`, without printing a hunk header for it: after its file header/underline there is no `───┐` box and no content. Support one-line hunks, multiple distant hunks, zero-context hunks, huge hunks, and `\ No newline at end of file` without state leakage.

`--line-buffer-size` bounds the changed-line pairing buffer and therefore can affect intra-line emphasis. Zero disables pairing: a removal such as `The quick brown fox` is one background-52 span and the corresponding addition `The quick red fox` is whole-line background 22 with syntax foreground, with no background-124/28 spans around `brown`/`red`. If a consecutive changed block exceeds a positive buffer (for example 33 removals followed by 33 additions at the default size 32), the flushed lines likewise use whole-line styles without homologous-word emphasis. A large enough buffer retains the normal Spec 11 pairing and emphasis. Buffer flushing must not lose, reorder, or otherwise alter visible text.

## Spec 11

### Changed-line matching and intra-line emphasis

Buffer nearby consecutive removals/additions and pair homologous old/new lines using normalized Levenshtein distance. A pair is eligible when distance is at most `--max-line-distance` (default 0.6); match lines to minimize distance while retaining order and supporting unequal counts. Tokenize emphasis with `--word-diff-regex` (default `\w+`) and highlight each insertion/deletion span, including multiple spans and one-character/version-number changes.

Removed whole-line/non-emphasized regions use background 52; removed emphasized spans background 124. Added whole-line/non-emphasized regions use background 22 and syntax foreground; added emphasized spans background 28. Unpaired lines use whole-line style. Context uses syntax highlighting without a colored background. Unless markers are requested, strip the leading `-`, `+`, or context space so output code can be copied. `--keep-plus-minus-markers` retains `-` and `+` at the content start in unified and side-by-side layouts.

Apply `minus-style`, `minus-non-emph-style`, `minus-emph-style`, `plus-style`, `plus-non-emph-style`, `plus-emph-style`, and `zero-style` independently. Empty-line marker option behavior is specified separately in Spec 21. A `raw` line style preserves incoming Git ANSI for that line. `--diff-highlight` and `--diff-so-fancy` are accepted presets for compatible highlighting/layout.

## Spec 12

### Style language and ANSI emission

A style is whitespace-separated, with zero to two colors in encounter order (foreground then background) and any number of attributes in any positions. Empty string means no added style. Attributes and SGR codes are: `bold` 1, `dim` 2, `italic` 3, `ul`/`underline` 4, `blink` 5, `reverse` 7, `hidden` 8, `strike` 9. Combinations preserve every attribute. Canonical SGR generation orders attributes, then background, then foreground (for example bold red on green is `ESC[1;42;31m`) and closes styled spans with `ESC[0m`.

Colors are case-insensitive: ANSI names `black red green yellow blue magenta cyan white` map to indices 0–7/codes 30–37 and 40–47; `purple` is a synonym for magenta. The names `brightblack brightred brightgreen brightyellow brightblue brightmagenta brightcyan brightwhite` map to fixed-palette indices 8–15 and are emitted as `ESC[38;5;Nm` in foreground position or `ESC[48;5;Nm` in background position, not as the short high-intensity codes 90–97 or 100–107. Thus bright red is exactly `ESC[38;5;9m` as a foreground and `ESC[48;5;9m` as a background. Decimal 0–255 selects the fixed palette (`ESC[38;5;Nm` or `ESC[48;5;Nm`); numbers 0–7 are output-equivalent to basic names. `#RRGGBB` selects RGB (`ESC[38;2;R;G;Bm` or `ESC[48;2;R;G;Bm`). Support the standard CSS named-color set. In particular `navy=#000080`, `salmon=#fa8072`, `lightblue=#add8e6`, and `steelblue=#4682b4`; these are RGB colors, not terminal-name aliases.

Special colors/tokens: `normal` uses terminal/default color; `auto` selects the element default; foreground `syntax` retains language syntax foreground; `raw` preserves input escape sequences. `omit` is meaningful for commit/file/hunk elements and suppresses that element. Styles used as decorations additionally accept `box`, `ul`/`underline`, `ol`/`overline`, their combinations, and `none`. `raw` and `syntax` are invalid as decoration geometry tokens. A token that is neither a style word nor a known color is also tried as a Git-config style key. If it cannot be found, exit 2; for `--plus-style=not-a-style`, stdout is empty and stderr is exactly `Style key not found in git config: delta.not-a-style\n`.

`reverse` affects effective foreground/background as terminal reverse video would. Explicit style differences (attribute, foreground, background, or missing versus present color) must lead to observably different ANSI output.

## Spec 13

### True-color and syntax color conversion

`--true-color=always` emits RGB sequences for RGB/theme colors. `never` maps RGB to the nearest xterm-256 color and emits fixed-palette codes. `auto` uses RGB only when `COLORTERM` equals `truecolor` or `24bit`. `--24-bit-color` is an exact deprecated alias. The one element-specific exception is a Git-blame palette: its RGB entries are always emitted as 24-bit background SGR, independently of this setting and `COLORTERM`. For example, `--blame-palette=#010203` gives the metadata, separator-prefix, number, and separator-suffix spans `ESC[48;2;1;2;3m`; the code span contains the same `48;2;1;2;3` background parameters combined with any syntax foreground. This holds under each of `--true-color=auto`, `never`, and `always`.

When an ANSI named/fixed color is imported into syntax styling, preserve its terminal palette identity rather than converting it to an arbitrary RGB: black through white correspond to 0–7, purple/magenta to 5, and numeric N to fixed N. RGB and CSS names carry exact RGB components. Bold, italic, and underline flags compose with syntax styles; a missing explicit foreground retains the syntax/default foreground rather than becoming black.

The built-in `ansi` and `base16` syntax themes encode terminal palette entries rather than RGB values. Palette indices 0–7 must therefore emit basic foreground/background SGR codes 30–37 and 40–47. In `base16-256`, indices above 7 emit `38;5;N` or `48;5;N`. None of these palette-encoded theme colors may be mistaken for RGB merely because of their internal representation.

The default dark palette used in non-true-color output is stable: removed backgrounds 52/124, added backgrounds 22/28, ordinary syntax text commonly 231, context line numbers 238, removed line numbers 88, added line numbers 28, file/hunk decorations ANSI blue, grep files ANSI magenta/purple, and grep numbers ANSI green. In forced true-color mode the four diff backgrounds are removed `#3f0001`, removed emphasis `#901011`, added `#002800`, and added emphasis `#006000`; default Monokai Extended foreground is `#f8f8f2`. Therefore representative combined sequences are `ESC[48;2;144;16;17m`, `ESC[48;2;0;96;0;38;2;248;248;242m`, `ESC[48;2;63;0;1m`, and `ESC[48;2;0;40;0m`. In 256-color mode those become 124, 28, 52, and 22 respectively, while `#f8f8f2` becomes 231. The reference's RGB-to-xterm conversion maps Monokai Extended `#f92672` to fixed index 203, not 197. Consequently a non-true-color Python blob rendered by `git show REV:file.py` begins `def` with `ESC[38;5;203m`, and `return` uses the same index.

## Spec 14

### Syntax highlighting and language selection

Highlight diff content according to the full displayed filename, not merely a basename prefix. At minimum accurately support plain text, Python, Rust, C/C++, shell, Java, JavaScript, JSON, and Makefile syntax, preserving comments, strings, numbers, keywords, punctuation, and Unicode. The default is `Monokai Extended`; common RGB scopes include foreground `#f8f8f2`, comments `#75715e`, strings `#e6db74`, keywords/operators `#f92672`, types/constants/numbers `#ae81ff`, names/functions `#a6e22e`, and declarations/built-ins `#66d9ef`, with bold/italic/underline scope flags retained. Syntax-specific scopes can differ: for the JSON line `{"answer": 123, "ok": true}`, property strings use exactly `#fd971f` (`ESC[38;2;253;151;31m`) and both the number and boolean use `#be84ff` (`ESC[38;2;190;132;255m`). `--syntax-theme none` disables syntax foreground coloring but does not disable diff backgrounds. A recognized extension selects its language. An unknown extension remains plain/default-foreground in diff content even when `--default-language=python` is supplied; in the observed `code.unknown` addition, `def f(): return 42` is one `#f8f8f2` foreground span rather than Python keyword spans.

Expand each tab to the next run of `--tabs` spaces (the tested default behaves as 8 spaces per tab); `--tabs=0` preserves literal tabs and treats each as display width one. Apply this consistently in diffs, side-by-side, grep, and blame.

Stop syntax parsing after `--max-syntax-highlighting-length` visible characters, but continue emitting the line under its surrounding diff style. Zero removes this syntax limit. This is distinct from whole-line truncation.

## Spec 15

### Display width, Unicode, truncation, and wrapping

Compute terminal width on Unicode grapheme clusters: ordinary characters width 1, CJK/fullwidth characters and emoji width 2, combining marks width 0. ANSI CSI/OSC sequences have width 0. Never cut a UTF-8 code point, grapheme, or escape sequence.

`--max-line-length=N` truncates every overlong input line, including raw-mode metadata lines, and appends the styled indicator `→`; zero disables truncation. With the default `inline-hint-style`, the indicator is an independently reset reverse-video span with exact bytes `ESC[7m→ESC[0m`. For example, at length 30 the raw metadata line `diff --git a/test.bin b/test.bin` becomes exactly `diff --git a/test.bin b/test.ESC[7m→ESC[0m\n`. The cutoff is first applied as a byte index and rounded down to the nearest valid UTF-8 boundary; a complete multibyte character ending exactly at that byte cutoff is retained even when it is double-width. Consequently `--raw --max-line-length=5` on `12＃abcdef\n` emits exactly `12＃ESC[7m→ESC[0m\n`, visibly `12＃→`, not `12 →`. Preserve ANSI sequences and active style correctness around truncation. Invalid byte runs are lossily decoded to U+FFFD after the safe boundary is chosen, without corrupting following valid multibyte text. A multibyte character straddling the cutoff is wholly omitted. Exactly-at-limit strings are not truncated.

Side-by-side wrapping uses `wrap-max-lines`; zero truncates rather than wrapping and `unlimited` wraps as often as required. Continuations carry blank line-number fields. Use `↵` when remaining content is left-aligned. If the final remainder occupies less than `wrap-right-percent` of its panel, right-align it, prefix `…`, and mark the preceding segment with `↴`. Respect custom symbols and apply `inline-hint-style`.

## Spec 16

### Color-only and raw modes

`--color-only` makes a one-to-one structural transform: every input line and every non-SGR byte remains in the same order, including `diff --git`, `---`, `+++`, raw hunk headers, commits, binary/submodule lines, and conflict markers. It adds/replaces only coloring on hunk content. It never creates file/hunk decorations, labels, side-by-side structure, or merge-conflict structure. Thus the canonical input

```text
--- a/file.txt
+++ b/file.txt
@@ -1 +1 @@
-old
+new
```

starts byte-for-byte with those three header lines and contains `ESC[48;5;52m-oldESC[0m`. The added line begins exactly `ESC[48;5;22m+ESC[38;5;231mnewESC[0m`: the marker is a background-only span boundary, and the following foreground SGR augments the still-active background rather than combining foreground and background before `+`. Empty input gives empty output; binary Git diffs retain identical visible text. Options such as navigation may parse alongside color-only but do not violate its structural guarantee.

`--raw` activates a built-in style preset; it is not a byte-preserving or no-color mode. The preset sets commit decoration to `none` and commit style to `raw`; file decoration to `none` and file style to `raw`; hunk decoration to `none` and hunk style to `raw`; removal and removal-emphasis styles to basic red; addition and addition-emphasis styles to basic green; context style to `normal`; `keep-plus-minus-markers=true`; and `tabs=0`. Thus a normal Git patch retains its `diff --git`, index, `---`/`+++`, and literal `@@` records, but each changed line is exactly a basic-color span such as `ESC[31m-oldESC[0m\n` or `ESC[32m+newESC[0m\n`. Arbitrary unrecognized preamble before the patch remains present and does not prevent this coloring.

The same raw preset applies independently to every changed line in a combined merge conflict. In particular an added marker line is one complete basic-green span: `++<<<<<<< NAME` is emitted as `ESC[32m++<<<<<<< NAMEESC[0m\n`; the ancestor, separator, and end-marker added lines and added conflict content use the same per-line opening and reset. `--navigate --raw` does not add navigation structure or alter these bytes.

Explicit element options still override the raw preset. In particular `--raw --file-decoration-style='yellow box'` suppresses the low-level Git file records, emits the three-row file box in Spec 17 with yellow geometry and a raw file title, retains the raw `@@` line, and colors the `-`/`+` lines red/green. `--raw --file-decoration-style='yellow none'` instead retains the low-level file records and emits no file box. The generic `--max-line-length` rule in Spec 15 continues to apply. Element-level `raw` styles preserve incoming colors while other elements may remain formatted.

## Spec 17

### File, commit, and hunk decorations

Decorations use Unicode light box drawing by default and heavy characters when the decoration style is bold. `ul` draws `─` below; `ol` above; `ul ol` both. Bold variants use `━`. `box` is a three-sided frame with only a right edge: it has no left corners and no left vertical. Its top row is a horizontal run followed by `┐`, its middle row is the header plus one padding space followed by `│`, and its bottom row is a horizontal run followed by `┘`; bold changes these to `━`, `┓`, `┃`, and `┛`. The top and bottom runs have the same display width as the padded header. A box combined with an underline replaces the lower-right corner with `┴` (or heavy `┻`) and draws the underline extension to its right; corresponding overline combinations use the proper connected right-side corner.

Fixed `--width=N` standalone underlines/overlines occupy exactly N display cells. A box's top and right edge remain content-sized rather than expanding to N. The complete lower row of a box-plus-underline occupies N cells when N is at least the content-sized box width; if N is narrower, it remains content-sized and the extension is empty. `variable` likewise uses only the header/box text width and gives a box-plus-underline no visible extension after `┴`/`┻`. Clamp extensions at zero—never underflow, wrap, or truncate the header solely to fit the decoration. Measure Unicode/emoji by display cells: `源/😀.rs` occupies eight cells, so its box has nine horizontal characters before the right corner because of the padding space. The horizontal run, its right corner/junction, and any extension are separate reset-terminated styled spans; the header text retains its independently reset file style. Even a zero-length box-underline extension is emitted as its own empty style/reset span after the junction. `none`, an empty decoration, or `omit` suppresses geometry as appropriate.

Normal file output begins with a blank line, a blue file title, and its blue underline to configured width. Commit decorations apply only to the recognized commit line, not Author/Date/message lines. Hunk decoration applies only to hunk header. Styles and decorations compose, including raw input styles.

## Spec 18

### Commit metadata

Recognize a commit boundary by `--commit-regex` (default `^commit `). Preserve the full matching line, abbreviated or 40-character SHA, optional decorations, `Merge:` parents, Author lines with or without email, Date, all intervening blank lines, and arbitrarily long/multiline messages. Preserve indentation, tabs, punctuation, HTML-like characters, backslashes, quotes, and Unicode exactly in visible text. Reset cleanly for each commit in multi-commit streams and transition correctly to stat or patch content even with no message.

Default `commit-style=raw` leaves the commit line structurally intact. Custom styles affect that line only. `omit` suppresses only it; Author/Date/message remain. `commit-decoration-style` supports Spec 17. In color-only mode commit metadata stays structurally unchanged.

For ordinarily styled structural elements, remove incoming SGR before applying the configured style so upstream colors do not leak into the result. An element explicitly configured as `raw`, including the default raw commit line, instead retains its incoming SGR bytes and visible text.

## Spec 19

### Line numbers

`--line-numbers` prepends two logical columns in unified view. Old numbers use `{nm}`, new numbers `{np}`. Defaults are `{nm:^4}⋮` and `{np:^4}│`; each default placeholder occupies four cells. The exact visible gutters are `  1 ⋮  1 │` for context, `  2 ⋮    │` for removal, and `    ⋮  2 │` for addition; with ordinary marker stripping, content immediately follows the final `│`. When markers are retained, the content begins with its original input prefix: the hunk starting at old 7/new 9 emits `  7 ⋮  9 │ same`, `  8 ⋮    │-old`, and `    ⋮ 10 │+new`. Start counters from each hunk range and update independently. Handle additions/deletions-only, unequal groups, multiple hunks, six-digit values, and side-by-side layout.

Format placeholders support `{nm}`/`{np}`, optional `<`, `^`, or `>` alignment, width, and arbitrary surrounding literal text. Missing number renders as spaces of the field width. Formats may be empty, contain no placeholder, contain only the placeholder, or be unusually wide. Increase effective fields as necessary for large numbers rather than truncating. Left/right column styles and minus/zero/plus number styles combine: left/right styles govern columns, while line-type styles color the numeric values as configured.

The exact SGR transitions within the gutter are observable and are not coalesced. With all default styles, a context row starting at old/new line 1 begins exactly `ESC[34mESC[38;5;238m  1 ESC[34m⋮ESC[38;5;238m  1 ESC[34m│`; a removal at old line 2 begins `ESC[34mESC[38;5;88m  2 ESC[34m⋮ESC[38;5;28m    ESC[34m│ESC[0m`; and its corresponding addition begins `ESC[34mESC[38;5;88m    ESC[34m⋮ESC[38;5;28m  2 ESC[34m│`. Literal prefix/suffix characters in a custom format use the applicable left/right column style, while the placeholder field switches to the applicable minus/zero/plus number style, then switches back to the column style. When a custom left column ends and the right column begins, reset the left span before opening the right span; reset the right span before the content when its distinct style requires it. Empty formats still produce the renderer's initial column-style SGR transition, but no visible gutter text. These boundaries remain unchanged for large/six-digit fields, additions- or deletions-only, unequal groups, multiple hunks, minimal/placeholder-only/wide formats, odd-width ANSI-fill side-by-side output, and side-by-side wrapping.

In side-by-side, place each relevant number beside its panel, omit old on pure additions and new on pure removals, and leave continuation-line numbers blank. With hyperlinks, each real displayed line number links to that file and exact line.

## Spec 20

### Side-by-side layout

`--side-by-side` implies line-number gutters and divides the configured total width into old and new panels separated by a blue `│`. Pair homologous removal/addition lines on the same row; unpaired removals have a blank right panel, unpaired additions a blank left panel, and context appears in both. Content and backgrounds are padded to panel width using spaces when non-TTY/default `line-fill-method=spaces`, or ANSI erase-to-EOL mechanics when `ansi` is selected. `width=variable` does not fill.

Account for gutter widths, the central divider, ANSI-zero-width sequences, odd total widths, CJK/emoji, tabs, trailing whitespace, empty lines, binary notices, no-newline markers, and custom line-number formats. Retain diff semantics across several hunks and very unbalanced change blocks. Apply intra-line emphasis independently to both paired panels and wrap as Spec 15.

## Spec 21

### Whitespace errors and empty changed lines

Recognize Git whitespace-error styling and textual trailing/introduced whitespace on added lines. Apply `whitespace-error-style`, default magenta reverse (`ESC[7;35m` in an applicable span), to the erroneous whitespace without losing normal plus/emphasis style. Handle errors after ordinary text, edits involving whitespace, all-whitespace additions, and complex whitespace. An added empty line and a one-character non-whitespace line are not automatically whitespace errors. Empty removed/added lines contain no separately painted visible marker, and the `--minus-empty-line-marker-style` / `--plus-empty-line-marker-style` values do not add one. With default main line styles, an empty removal is exactly `ESC[48;5;52mESC[0KESC[0m\n` and an empty addition is `ESC[48;5;22mESC[0KESC[0m\n`; overriding only the marker styles to red and green leaves those bytes unchanged.

When `--inspect-raw-lines=true`, inspect incoming SGR styles to detect Git color-moved/whitespace classifications, and honor `--map-styles` mappings of `INPUT_STYLE => OUTPUT_STYLE`. With false, do not interpret incoming styles semantically. `--keep-plus-minus-markers` still behaves correctly under inspection.

## Spec 22

### Binary files, modes, and submodules

Pass standalone binary notices unchanged. For Git binary patches, render a file operation header and `(binary file)` without trying syntax/intra-line processing; color-only preserves the entire Git block’s visible structure.

Recognize submodules from mode `160000` and hunk lines beginning `-Subproject commit ` / `+Subproject commit `. In structural mode, a minus-prefixed line at the start of a hunk is consumed. Only an optional `-dirty` suffix following exactly 40 lowercase hexadecimal characters establishes a pending old commit. While such a commit is pending, the following plus-prefixed Subproject line is also consumed; if it likewise contains exactly 40 lowercase hexadecimal characters, show the first 12 characters of old SHA, literal `..`, and first 12 of new SHA with old/new styles, stripping `-dirty`. If that pending plus line is malformed, no changed line is emitted.

This produces an intentional one-sided asymmetry. A removed submodule or any minus-only Subproject line emits only the removed/ordinary file heading and underline: it emits no hunk box and no Subproject content line. A new submodule or plus-only line has no pending valid old commit, so it uses the ordinary added-line path and displays a hunk box followed by the full `Subproject commit SHA` content. For a short, nonhex, malformed, or uppercase pair, the invalid minus line is consumed without establishing pending state and the plus line is displayed as an ordinary full-length addition. The ordinary hunk box retains the independently reset run/corner bytes from Spec 10.

`--color-only` bypasses this compaction and retains both full input lines. With default styles its removed line ends `ESC[0mESC[48;5;52mESC[0KESC[0m\n`; its added line ends `ESC[0mESC[48;5;22mESC[0KESC[0m\n`. Interleave regular code diffs normally. Recognize and retain `Submodule PATH OLD..NEW:` log blocks and `Submodule PATH contains untracked content`. Separator width follows `--width`, and side-by-side does not split a compact SHA range incorrectly.

## Spec 23

### Diff-stat blocks

Recognize Git stat lines of the form `PATH | COUNT GRAPH`, binary `PATH | Bin OLD -> NEW bytes`, rename abbreviation (`old => new`), and summary lines such as `3 files changed, 8 insertions(+), 6 deletions(-)`. Preserve count, plus/minus graph, binary wording/arrows, summary grammar, spaces in filenames, leading `.../` abbreviations, and commit-message `---` separator.

Preserve the input's existing separator columns rather than realigning them. In particular, with `--diff-stat-align-width=30`, standalone lines ` src/a.py | 2 +-` and ` very long name.txt | Bin 10 -> 20 bytes` pass through with `|` at zero-based columns 10 and 20 respectively. The option is accepted and defaults to 48, but does not change those observed standalone stat rows; widths smaller than a name use saturating arithmetic rather than crashing. Preserve stat before a following patch and mixed text/binary entries without losing count, graph, or binary fields. Apply relative-path and hyperlink behavior to paths without asserting that it realigns the input separators.

## Spec 24

### Merge conflicts

Inside added lines of a combined/merge diff, recognize a well-ordered conflict beginning `++<<<<<<< NAME`, optional ancestor `++||||||| ANCESTOR`, separator `++=======`, and end `++>>>>>>> NAME`. Require nonempty names and a complete valid order; malformed, nameless, missing-end, or out-of-order markers remain ordinary added lines.

For a three-way conflict, render two ordinary diff comparisons: ancestor→ours and ancestor→theirs, with headers naming the branches and visible `ancestor ⟶` relationship. Surround the region with full-width bars formed by repeating `merge-conflict-begin-symbol` (default `▼`) and `merge-conflict-end-symbol` (default `▲`). Apply independently configurable ours/theirs header styles and box decorations. Trim marker-edge whitespace while preserving internal spaces in names.

For a two-way conflict, show both named sides without requiring an ancestor. Support empty one/both sides, conflict at file start, multiple/sequential conflicts, large/long/unicode content, context before/after, JSON syntax, word-level emphasis, and side-by-side mode. `--raw` and `--color-only` disable this structural rewrite and preserve marker structure. Custom begin/end strings are repeated/truncated by display width.

Conflict rendering does not introduce an alternate ANSI coalescing rule. Its outer file title and underline, any ordinary hunk header before or after a conflict, and the synthesized comparison boxes use the independently reset component boundaries in Specs 10 and 17; side-by-side conflict content uses the gutter and panel transitions in Specs 19–20. This applies equally to three-way, two-way, empty-section, multiple, malformed/pass-through, JSON, long-line, Unicode, and custom-symbol cases.

## Spec 25

### Ripgrep JSON input

Auto-detect newline-delimited ripgrep JSON records. `begin` establishes the file. A formattable `match` or `context` record must provide path, `lines.text`, optional `line_number`, integer `absolute_offset`, and byte-indexed `submatches`; `absolute_offset` is required by deserialization even though it is not displayed. `end` closes the file and `summary` is not displayed. A summary-only/no-match stream produces no output. If a match/context record omits `absolute_offset`, it is not formattable and its original JSON line passes through unchanged, while surrounding recognized `begin`, `end`, and `summary` records are still consumed. Thus the observed incomplete Unicode match stream emits exactly its serialized `match` record and newline, not a file heading or `7:` content line.

Output one magenta file heading per contiguous file section, then green line number plus `:` and syntax-highlighted content. Highlight every exact submatch (including multiple/empty submatches) with match-word style, default added-emphasis background 28, interpreting offsets as UTF-8 byte offsets without corrupting text. Context uses context style. Separate files by a blank line; interleaved/repeated file sections are handled. Insert `--` between separated context blocks where the JSON event structure calls for it, not merely between nonconsecutive match-only lines. Handle missing line numbers, carriage returns, tabs, Unicode, and very long lines.

## Spec 26

### Classic colored grep input

Accept the ANSI output produced by ordinary `grep --color=always -n` and `git grep --color=always -n`. Preserve its record order and visible content, including the match text and line number, and retain meaningful incoming ANSI highlighting rather than printing escape bytes as text. A single-file GNU grep record that contains only `LINE:TEXT` remains in that compact form.

For a Git-grep record `PATH:LINE:TEXT`, preserve the path exactly when it contains hyphens, underscores, or multiple dots (for example `test-file_2.0.txt`); do not mistake those characters for separators. The line number is green and the matched content remains visible. Files that have no matches produce no record, so an empty file is not invented in the output. Preserve UTF-8 content such as Chinese text and emoji. Very long matching lines must complete without a crash and are subject to the default 3000-byte/cell line limit from Specs 5 and 15, while keeping an early path and match visible.

## Spec 27

### Git blame input

Recognize ordinary porcelain-like human blame lines consisting of a commit token (optionally leading `^`), optional old filename, parenthesized author/timestamp/original line number, then code. Nonmatching lines pass through unchanged; mixed valid/invalid streams resume parsing safely.

Render metadata using `--blame-format`, default `{timestamp:<15} {author:<15.14} {commit:<8}`. Placeholders `{timestamp}`, `{author}`, `{commit}` accept left/right/center width and `.precision` truncation; literal-only and empty formats are valid. A placeholder with no explicit alignment is left-aligned and one with no explicit width has width 15. Thus `--blame-format='{author} {commit}'` pads both fields to 15 cells. Parse incoming timestamp with default `%Y-%m-%d %H:%M:%S %z`; when `--blame-timestamp-output-format` is given, emit `strftime` output exactly (dates, date+time, or time-only). Otherwise compare it with the system clock at invocation and emit a rounded human relative-time phrase. For example, on 2026-09-19 each tested January–May 2024 timestamp renders as `2 years ago`, padded to 15 cells by the default format; it is not rendered as the input's absolute timestamp.

Assign a background from `--blame-palette` per commit block, reusing the same color for the same commit and recycling colors for later authors/blocks. Default is `#000000 #222222 #444444`; accept named, fixed, and RGB colors, including a single color. RGB palette colors use the unconditional 24-bit exception in Spec 13, so the default black begins `ESC[48;2;0;0;0m` even when computed true-color is false.

Render `--blame-separator-format` (default `│{n:^4}│`) with `{n}` alignment; when `{n}` has no alignment or width, default to centered width 4. An empty format suppresses all visible separator content; the special value `none` suppresses the number but emits one literal `│`. Paint and reset the metadata, separator prefix, padded number, and separator suffix as four distinct spans even when their effective backgrounds are identical: prefix/suffix use `blame-separator-style` (falling back to the code/metadata style), while the number uses the metadata palette style. For example, with cyan metadata, `--blame-separator-format=' [{n}] '`, and `--blame-separator-style='bold red'`, the separator bytes are `ESC[1;31m [ESC[0mESC[46m  1 ESC[0mESC[1;31m] ESC[0m`. Code is another independently reset span; it uses syntax highlighting on the metadata background by default, while `--blame-code-style=syntax` removes that background and `raw` preserves code. Preserve Unicode, tabs, blank/whitespace code, renamed-file fields, long lines, and correct line numbers.

## Spec 28

### Terminal hyperlinks

When `--hyperlinks` is enabled, wrap link text as OSC 8: `ESC]8;;URL ESC\\ TEXT ESC]8;; ESC\\`. File headers, both sides of renames, binary paths, and actual line numbers may be links. The default file URL expands `file://{path}` using an absolute path. `--hyperlinks-file-link-format` replaces `{path}`, `{line}`, and `{host}`; use the actual old/new file and line for each panel. Spaces in `{path}` remain literal space bytes in the OSC target rather than becoming `%20`; Unicode likewise remains UTF-8, while visible link text stays unchanged.

Hyperlink escapes nest inside the surrounding styled component rather than changing its SGR boundaries. A linked blue file title has byte order `ESC[34m`, OSC-open, title, OSC-close, `ESC[0m`. A linked blue hunk line number has OSC-open, `ESC[34mNUMBERESC[0m`, OSC-close, then the unstyled `: ` and independently painted `ESC[34m│ESC[0m`. Custom targets obey the same ordering, as do line-number and side-by-side modes. For a binary operation, the reference deliberately appends the visible suffix to the default URL as well as to the linked text: in the observed `/workspace` invocation, `image.png (binary file)` links to exactly `file:///workspace/image.png (binary file)`, not merely `file:///workspace/image.png`. In other directories, replace the absolute-directory portion normally.

`--hyperlinks-commit-link-format` expands `{commit}` exactly. Otherwise infer a commit URL from Git remote `origin`: GitHub HTTPS or `git@github.com:` → `https://github.com/PATH/commit/HASH`; GitLab → `https://gitlab.com/PATH/-/commit/HASH`; SourceHut → `https://git.sr.ht/PATH/commit/HASH`; Codeberg → `https://codeberg.org/PATH/commit/HASH`. Remove a trailing `.git`, preserve nested GitLab groups and SourceHut `~user`. Unsupported remotes silently omit the commit link.

Recognize abbreviated hashes of at least 7 lowercase hex characters in commit-oriented text, but require at least one `a`–`f`; all-numeric strings are not commit links. OSC sequences have zero display width and must not disturb decorations, stat alignment, wrapping, or side-by-side panels.

## Spec 29

### Navigation markers and pager search

`--navigate` changes otherwise empty default labels to make search stops: a modified file gets `Δ` and a nonempty rendered hunk gets `•`; added/removed/renamed/copied retain their operation labels. Emit the file stop once per file and a hunk stop for every hunk that produces a hunk header. A both-counts-zero hunk suppressed by Spec 10 emits no `•`; for example `@@ -1,0 +1,0 @@` produces only the `Δ` file heading and underline. Custom label options replace these values; an explicitly empty label suppresses that stop. Preserve arbitrary Unicode, whitespace, tabs, quotes, slashes, `=:-_&;`, and regex metacharacters literally in visible labels.

Construct the pager navigation regular expression deterministically in operation-label order and regex-escape `|()^$\\?+*{}` and other regex syntax inside labels. Exclude empty/whitespace-only effective alternatives as appropriate. Navigation remains aligned with line-number and side-by-side output, and handles commits, stats before diffs, binary/submodule/permission-only files, combined/no-index diffs, spaced/unicode/deep paths, empty additions, no-newline markers, and very large diffs.

When the chosen pager executable’s basename is `less`, create `${XDG_DATA_HOME}/delta/lesshst` (or the platform data-home equivalent) and configure less so `n`/`N` move among the escaped markers. This history-file creation is an observable side effect of navigation with less.

## Spec 30

### Pager behavior

`--paging=never` writes directly to stdout. `always` buffers formatted bytes and sends them to a pager; `auto` pages only when stdout is a TTY, so a captured/non-TTY run writes directly. Pager selection precedence is `--pager`, `DELTA_PAGER`, `BAT_PAGER`, `PAGER`, then `less -R`. Parse a pager string with shell-style quoting and arguments. The selected program’s stdout is the executable’s stdout; preserve every formatted byte, including the reset-delimited component boundaries specified in Specs 10 and 27 and all ANSI/binary-notice bytes. A pass-through pager therefore produces byte-for-byte the same stream as `--paging=never` when selected by the CLI, `DELTA_PAGER`, or `PAGER`; the same is true of the direct-output fallback after a missing pager.

For less, replace unsuitable supplied argument sets with safe ANSI-preserving arguments including `-R`, while respecting navigation setup; do not overwrite a user-provided `LESSUTFCHARDEF`. An empty command, unresolved executable, or spawn failure falls back to direct stdout without losing buffered data. A pager command whose executable is `delta` is a fatal recursion error; stderr must contain `non-terminating recursion` and `delta is not an appropriate value for $PAGER` (the complete message explains that delta is appropriate for `$GIT_PAGER`). CLI pager overrides all environment pagers. Large and multi-file output must not deadlock or truncate.

## Spec 31

### `--parse-ansi`

This action reads stdin and emits a human-readable styled segmentation, one input line at a time. Before each maximal visible text run, output `(STYLE_DESCRIPTION)`; render that description using the style it names, reset, then render the original run under the same style and reset. Plain/reset state is `(normal)`. Examples (where `ESC` is byte 0x1b) are:

```text
input:  ESC[3mItalicESC[0m\n
output: (ESC[3mitalic normalESC[0m)ESC[3mItalicESC[0m\n

input:  Plain ESC[31mRedESC[0m and ESC[1mBoldESC[0m text\n
output: (normal)Plain (ESC[31mredESC[0m)ESC[31mRedESC[0m(normal) and (ESC[1mbold normalESC[0m)ESC[1mBoldESC[0m(normal) text\n
```

Descriptions list attributes then foreground then background. The exact attribute words are `bold`, `dim`, `italic`, `ul`, `blink`, `reverse`, and `strike`; SGR 8 remains active on the rendered run but contributes no attribute word. If there is no explicit foreground, append `normal`, including for an attribute-only style; therefore SGR 2 describes itself as `dim normal`, SGR 8 as `normal`, and SGR 9 as `strike normal`. Basic color names use `purple` for 35; bright names are retained; fixed palette is decimal; RGB is quoted lowercase `"#rrggbb"`. Preserve the effective SGR styling in the rendered text.

Codes within one SGR instruction combine, but a later SGR instruction replaces the complete prior style rather than accumulating with it. Thus `ESC[1;4;31m` describes `bold ul red`, while `ESC[1mESC[4mESC[7mESC[31m` leaves only `red`. Parse `ESC[m` reset, semicolon fixed/RGB forms `38;5;n`, `48;5;n`, `38;2;r;g;b`, `48;2;r;g;b`, and colon forms `38:5:n`, `48:5:n`, `38:2::r:g:b`, `48:2::r:g:b`. Underline subparameters such as `4:1` mean underline. Codes 5 and 6 both canonicalize to SGR 5 and describe `blink normal`. Strip non-SGR CSI (cursor move, erase, save/restore, private cursor show/hide) and OSC (titles and hyperlinks) from visible text. Recover from malformed/incomplete/unknown escapes by skipping the escape and continuing; never crash.

Process by input lines and terminate every processed line with `\n`, even when the final input line was unterminated. A nonempty line containing only reset therefore emits exactly `\n`; completely empty input alone emits empty output.

## Spec 32

### `--show-config`

Exit 0 and print resolved active configuration, including CLI/config/features/environment effects. One setting per line uses four leading spaces, a left-aligned name column, ` = `, then value. Style values are demonstrated with actual ANSI; non-style strings needing clarity are quoted. Reflect changes to settings that this report includes, such as `line-numbers`, `side-by-side`, `navigate`, width, syntax theme, pager, and listed custom styles.

With no discovered configuration, non-TTY stdout, `TERM=xterm-256color`, `COLUMNS=80`, `--no-gitconfig`, and no `NO_COLOR`, the complete output is exactly the following 39 lines, with a final newline and no stderr. Replace each written `ESC` with byte `0x1b`; no other lines are emitted, even though the program has additional accepted settings:

```text
    commit-style                  = raw
    file-style                    = ESC[34mblueESC[0m
    hunk-header-style             = syntax
    minus-style                   = ESC[48;5;52mnormal 52ESC[0m
    minus-non-emph-style          = ESC[48;5;52mnormal 52ESC[0m
    minus-emph-style              = ESC[48;5;124mnormal 124ESC[0m
    minus-empty-line-marker-style = ESC[48;5;52mnormal 52ESC[0m
    zero-style                    = syntax
    plus-style                    = ESC[48;5;22msyntax 22ESC[0m
    plus-non-emph-style           = ESC[48;5;22msyntax 22ESC[0m
    plus-emph-style               = ESC[48;5;28msyntax 28ESC[0m
    plus-empty-line-marker-style  = ESC[48;5;22mnormal 22ESC[0m
    grep-file-style               = ESC[35mpurpleESC[0m
    grep-line-number-style        = ESC[32mgreenESC[0m
    whitespace-error-style        = ESC[7;35mreverse purpleESC[0m
    blame-palette                 = ESC[48;5;16m#000000ESC[0m ESC[48;5;235m#222222ESC[0m ESC[48;5;238m#444444ESC[0m
    true-color                    = false
    file-added-label              = 'added:'
    file-modified-label           = ''
    file-removed-label            = 'removed:'
    file-renamed-label            = 'renamed:'
    right-arrow                   = '⟶  '
    hyperlinks                    = false
    inspect-raw-lines             = true
    keep-plus-minus-markers       = false
    line-numbers                  = false
    max-line-distance             = 0.6
    max-line-length               = 3000
    diff-stat-align-width         = 48
    line-fill-method              = spaces
    navigate                      = false
    navigate-regex                = 
    pager                         = none
    paging                        = auto
    side-by-side                  = false
    syntax-theme                  = Monokai Extended
    width                         = 80
    tabs                          = 8
    word-diff-regex               = '\w+'
```

## Spec 33

### Syntax-theme inventory

`--list-syntax-themes` is deterministic. When stdout is not a TTY, output exactly this tab-separated list and final newline:

```text
dark	1337
dark	Coldark-Cold
dark	Coldark-Dark
dark	DarkNeon
dark	Dracula
dark	Monokai Extended
dark	Monokai Extended Bright
dark	Monokai Extended Origin
dark	Nord
dark	OneHalfDark
dark	Solarized (dark)
dark	Sublime Snazzy
dark	TwoDark
dark	Visual Studio Dark+
dark	ansi
dark	base16
dark	base16-256
dark	gruvbox-dark
dark	zenburn
light	GitHub
light	Monokai Extended Light
light	OneHalfLight
light	Solarized (light)
light	gruvbox-light
```

When stdout is a TTY, output `Light syntax themes:` first with the five light names indented by four spaces, blank line, then `Dark syntax themes:` with the nineteen dark names, blank line, then `Use delta --show-syntax-themes to demo the themes.`. TTY line endings follow the terminal wrapper. There are no duplicates or empty names.

## Spec 34

### Theme demonstrations

`--show-syntax-themes` prints a preview for each selected syntax theme. Each preview has an ANSI-styled title containing `Syntax theme: NAME` and a formatted diff. Empty stdin uses a built-in Rust sample containing `fn`, `print_cube`, and `print_square`; nonempty stdin replaces the sample. `--dark` selects all dark inventory entries, `--light` all light entries; absent either, select the computed terminal color mode. Output includes at least five previews and preserves custom diff content.

`--show-themes` instead discovers named feature sections from normally discovered Git configuration that explicitly set `dark=true` or `light=true`. Its discovery path does not honor a command-line `--config PATH`. Therefore `--show-themes --dark --config PATH`, when PATH is the only place defining dark `zebra`/`Alpha` and light `light-only` sections and normal discovery has none, exits 2 with empty stdout and exactly `No themes found. Please see https://dandavison.github.io/delta/custom-themes.html.\n` on stderr. Themes found through normal discovery are sorted case-insensitively and filtered by requested/computed color mode. Each selected preview title has exact byte layout `\n\nTheme: ESC[1mNAMEESC[0m\n\n`: the visible literal `Theme: ` is unstyled, only the feature name is bold, and the formatted preview follows. Render either nonempty stdin or the built-in sample under that feature.

The `--show-themes` built-in sample is distinct from the Rust sample used by `--show-syntax-themes`. It is a multi-file JavaScript Git commit diff whose visible text begins `commit 7ec4627902020cccd7b3f4fbc63e1b0d6b9798cd`, identifies `src/compiler/codegen/index.js`, `src/core/instance/render-helpers/resolve-scoped-slots.js`, and `test/unit/modules/compiler/codegen.spec.js`, and contains `scopedSlots`. Empty or closed/unreadable stdin falls back to this sample; nonempty stdin replaces it completely. Each preview includes the normal navigation styling used by the theme demonstration. Continue to later themes if a sample is malformed; support Unicode/empty theme names, many themes, huge samples, and NUL without crashing.

If the config contains one or more marked themes but the requested color mode selects none of them—for example only a `dark=true` theme with `--light`, or only a `light=true` theme with `--dark`—exit 0 with both stdout and stderr empty. If the config contains no feature section marked `dark=true` or `light=true` at all, exit 2, write exactly `No themes found. Please see https://dandavison.github.io/delta/custom-themes.html.\n` to stderr, and write no preview.

## Spec 35

### Color and language demonstrations

`--show-colors` exits 0 with ANSI-rich output. Organize standard CSS names into headings including `Blue`, `Red`, and `Green`; show each color name and `#rrggbb` plus a syntax-highlighted code example containing the visible phrase `export function color()`. Include at least 100 examples and at least 50 hex values, including `steelblue`. With `--true-color=always`, demonstrations use RGB sequences.

`--list-languages` exits 0 and lists supported syntax languages in a padded name column followed by comma-separated, green-ANSI extensions. Language entries are sorted by language name in ascending, case-insensitive order; the inventory begins `ActionScript`, `Ada`, `Apache Conf`, `AppleScript`, `ARM Assembly` and ends `Vyper`, `WGSL`, `XML`, `YAML`, `Zig`. In the default non-TTY `COLUMNS=80` environment it contains exactly 173 language entries, wrapped into 188 nonempty newline-terminated physical rows; in particular it must contain more than 50 rows. It includes Python, Rust, JavaScript, C, C++, shell/Bourne Again Shell, ActionScript, Ada, and their usual extensions. Long extension lists wrap under the extension column without changing entry order.

## Spec 36

### Completion generation

`--generate-completion SHELL` is an informational action. Missing shell or any name outside the five-value enumeration exits 2 on stderr. Valid output is nonempty and documents the full option grammar.

- Bash defines `_delta()`, uses `COMPREPLY`, and contains options such as `--show-config`, `--show-colors`, `--line-numbers`, and `--side-by-side`.
- Zsh begins/contains `#compdef`, defines `_delta()`, and uses `_arguments`.
- Fish contains at least twenty `complete -c delta` entries.
- PowerShell includes `using namespace` and `Register-ArgumentCompleter`.
- Elvish includes `use builtin`, `edit:completion:arg-completer`, and `delta` and is longer than 100 characters.

## Spec 37

### Direct comparison and diff arguments

With two file operands, run the harness-provided comparison command as `git diff --no-index --color` where suitable, feed its stdout through this formatter, forward relevant stderr, and return 0 if identical or 1 if different. `/dev/null` denotes an empty side. Identical inputs yield exactly empty stdout. A missing path produces status 1, empty stdout, and exactly `git diff: error: Could not access 'PATH'\n` on stderr; for example `/workspace/executable /dev/null /nonexistent_xyz_123.txt` emits exactly `git diff: error: Could not access '/nonexistent_xyz_123.txt'\n`.

Parse `--diff-args` using shell-word quoting. Empty string means defaults. If its first nonempty token lacks `-`, prefix one (`U5`→`-U5`). Forward multiple/whitespace-separated options such as `-w -U2`. Recognize `-u`, `-U`, `-U N`, and `-UN` as already specifying unified context; otherwise add `-U3`. Values U0/U5/U7 control actual context. Invalid suffixed spellings are accepted by delta's CLI and left for the selected comparison program to reject, rather than producing an `unexpected argument` parser diagnostic. In particular, direct comparison with `-@-ux` produces no stdout, returns 129, and starts stderr with ``git diff: error: unknown switch `x'``; its process-failure line reports exit status 129 and a command containing `git diff --no-index --color -ux --`. An unmatched quote exits 2 and writes exactly `Failed to parse diff args: VALUE: missing closing quote\n`.

For `/dev/fd/*`/process-substitution operands, invoke the harness-provided plain `diff` command because older Git may not support them. Supply unified output, adding `-U3` only if user args did not already specify a valid `-u`/`-U` form. Preserve the comparison program’s status. Thus glued `-@-Ux` does not count as valid context: delta invokes a command containing `diff -U3 -Ux --`, produces no stdout, returns 2, and stderr begins exactly `diff: diff: invalid context length 'x'\ndiff: Try 'diff --help' for more information.\n` before the process-failure line.

## Spec 38

### External `git` and `rg` command routing

After parsing delta options, a positional token `git` or `rg` starts an external command invocation rather than a filename comparison. The external programs are harness-provided when present; the executable’s responsibility is orchestration. Options before the token configure formatting. The selector itself is consumed, but delta prepends its own child arguments before forwarding the remaining tokens: `git config --list` launches `git -c color.ui=always config --list`, and `rg needle .` launches `rg --json needle .`. Capture stdout, format recognized content, pass ordinary output through, forward stderr, and return the child status.

For Git, the inserted `-c color.ui=always` pair always precedes the caller's remaining arguments. A harness child must account for that pair before dispatching on `config`, `show`, an option, or `diff`. With the supplied evidence child, which instead dispatches only on its first argument, every route sees `-c` and takes its status-128 fallback. The observed stderr mappings are: `git config --list` → `git config: fatal: bad revision\n`; `git bad-revision` → `git bad-revision: fatal: bad revision\n`; `git show HEAD:code.py` → `git show: fatal: bad revision\n`; `git --invalid-flag` → `git: fatal: bad revision\n`; and `git diff bad` → `git diff: fatal: bad revision\n`. A child that accepts the inserted pair can provide the normal behaviors: `git show REV:PATH` syntax-highlights the blob by PATH’s language even though it is not a diff; Python source uses the same Python/Monokai rules as Spec 14. Preserve Git fatal status 128 and its meaningful message for an invalid revision. `git config --list` remains readable. For a Git option failure, condense verbose help so `git --invalid-flag` reports `git: unknown option: --invalid-flag` and returns 129. When an invoked `git diff` writes a multiline error, preserve all of it while prefixing the first line with `git diff:`.

For `rg`, always prepend `--json`, even when the remaining arguments already begin with `--json` (that invocation launches `rg --json --json ...`), then feed records to Spec 25. Consequently the supplied evidence child is launched as `rg --json needle .`; its match record lacks required `absolute_offset` and passes through as the exact raw JSON line while its begin/end/summary records are consumed. If `rg` is absent, exit 2 and write `Failed to execute the command "rg": No such file or directory (os error 2)\n`; this applies with no rg args, a pattern, paths, and delta options. An invalid delta option before either command must be rejected by Spec 3 before launching it.

## Spec 39

### Robustness and deterministic bytes

All formatters operate as deterministic state machines: two invocations with equal args, environment, cwd, input, and system-clock value produce identical stdout/stderr. Every emitted styled span is reset and ANSI sequences are never split. Final-newline behavior follows input except informational outputs that explicitly require one and the line-oriented `--parse-ansi` action in Spec 31, which newline-terminates every processed line. Large lines/diffs and many files/themes use bounded buffering where practical but never lose content.

Malformed CSI/OSC, malformed diff headers, incomplete conflicts, malformed submodule hashes, invalid blame lines, unusual paths, and malformed UTF-8 are recoverable data, not fatal errors. Error messages contain no stack trace. Do not create unrelated files; the sole exception required here is the less history file in navigation mode. Do not depend on any repository source or documentation at runtime.

## Spec 40

### Canonical default rendering example

For this non-TTY, no-gitconfig input at width 80:

```text
--- a/file.txt
+++ b/file.txt
@@ -1,3 +1,3 @@
 line one
-line three
+line THREE
 line four
```

normal structural output has these visible lines in this order (ANSI omitted only in this explanatory view):

```text

a/file.txt ⟶   b/file.txt
────────────────────────────────────────────────────────────────────────────────

───┐
1: │
───┘
line one
line three
line THREE
line four
```

The file title/underline and hunk box are ANSI blue. The two raw paths are both shown because this conventional unified input has no preceding `diff --git` header establishing `a/` and `b/` as removable Git prefixes. Context is syntax-styled. `line three` is background 52 with the changed `three` span background 124; `line THREE` is background 22 with `THREE` background 28 and syntax foreground. Background fill reaches width 80 using `ESC[0K` in normal unified output. Every content span ends with `ESC[0m`. This example establishes blank-line placement, suppression of raw unified headers, marker removal, full-width decoration, and the relationship between normal and emphasized styles; Specs 8–24 generalize it to the remaining formats.
