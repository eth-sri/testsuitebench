# Clarified behavioral specification for executable

The required artifact is a single executable file named `executable`. It implements the command-line program and interactive terminal pager described below. All positions and line numbers exposed to users are one-based unless a section explicitly says otherwise. One such exception is the bottom-aligned top position in follow mode, which can be zero or negative when the document has fewer rows than the viewport.

## Spec 1

The program identifies itself as `ov`, a feature-rich terminal pager. It accepts zero or more file operands, reads standard input when there are no operands, and has two presentation paths:

- When standard output is a usable terminal (or a controlling terminal is explicitly forced), it opens a full-screen interactive viewer. Standard input may itself be a pipe; piped input is buffered as a document and still shown interactively when output is a terminal.
- When standard output is redirected or captured, it copies the selected input to standard output and exits rather than emitting terminal-control sequences. This pass-through path is used even when display-oriented flags such as header, line number, wrapping, search highlighting, column mode, ruler, caption, and styles are present. It must preserve the input byte sequence after any input-source decoding described later, including blank lines, tabs, trailing spaces, CRLF, embedded NUL/control bytes, and the presence or absence of the final newline.
- `--force-screen` overrides redirected-output detection and tries to initialize the TUI through `/dev/tty`, except that a `--quit-if-one-screen` input known to fit may take its early pass-through exit before screen initialization. If screen initialization is attempted and `/dev/tty` is unavailable, exit 1 and write exactly `Error: Screen.Init(): open /dev/tty: no such device or address` plus a newline to stderr.

With no operands and immediate EOF on stdin, exit 0 with empty stdout and stderr. Normal successful commands exit 0. Input-open and argument errors exit 1.

## Spec 2

The CLI has no subcommands. Positional words are file names, including words before a later `--help`; a random positional word is never interpreted as a command. A bare `--` ends option parsing, so every later word is a positional file unless exec mode consumes it as a command. Long options may use either `--name=value` or, for non-boolean values, `--name value`. Boolean options accept `=true` and `=false`; without `=`, they mean true and do not consume the next token. Repeated scalar or boolean options use the last value. Combined short booleans such as `-cf`, attached short values such as `-d;` and `-H-1`, and negative signed integer values are accepted.

The defaults are: converter `es`, column delimiter `,`, tab width 8, wrapping on, incremental search on, status line on, ruler 0, horizontal-scroll width `10%`, memory limit -1, file memory limit 100, no fixed header/vertical header, no search/filter, and all other modes off.

## Spec 3

`-h` and `--help` are equivalent, take precedence over ordinary execution when parsed as options, exit 0, write nothing to stderr, end in a newline, contain no ANSI escapes when stdout is not a terminal, and write exactly this text (including spacing):

~~~text
ov is a feature rich pager(such as more/less).
It supports various compressed files(gzip, bzip2, zstd, lz4, and xz).

Usage:
  ov [flags] [FILE]...

Flags:
Short   Long                                    Purpose
  -l, --align                                   align the output columns for better readability
  -C, --alternate-rows                          alternately change the line color
      --caption string                          custom caption
  -i, --case-sensitive                          case-sensitive in search
  -d, --column-delimiter character              column delimiter character (default ",")
  -c, --column-mode                             column mode
      --column-rainbow                          column mode to rainbow
      --column-width                            column mode for width
      --completion string                       generate completion script [bash|zsh|fish|powershell]
      --config file                             config file (default is $XDG_CONFIG_HOME/ov/config.yaml)
      --converter string                        converter [es|raw|align] (default "es")
      --debug                                   debug mode
      --disable-column-cycle                    disable column cycling
      --disable-mouse                           disable mouse support
  -e, --exec                                    command execution result instead of file
  -X, --exit-write                              output the current screen when exiting
  -a, --exit-write-after int                    number after the current lines when exiting
  -b, --exit-write-before int                   number before the current lines when exiting
      --filter string                           filter search pattern
  -A, --follow-all                              follow multiple files and show the most recently updated one
  -f, --follow-mode                             monitor file and display new content as it is written
      --follow-name                             follow mode to monitor by file name
      --follow-section                          section-by-section follow mode
      --force-screen                            display screen even when redirecting output
  -H, --header int                              number of header lines to be displayed constantly
  -Y, --header-column int                       number of columns to display as a vertical header
  -h, --help                                    help for ov
      --help-key                                display key bind information
      --hide-other-section                      hide other section
      --hscroll-width [int|int%|.int]           width to scroll horizontally [int|int%|.int] (default "10%")
      --incsearch[=true|false]                  incremental search (default true)
  -j, --jump-target [int|int%|.int|'section']   jump target [int|int%|.int|'section']
  -n, --line-number                             line number mode
      --list-view-modes                         list available view modes defined in the configuration file
      --memory-limit int                        number of chunks to limit in memory (default -1)
      --memory-limit-file int                   number of chunks to limit in memory for the file (default 100)
  -M, --multi-color strings                     comma separated words(regexp) to color .e.g. "ERROR,WARNING"
      --non-match-filter string                 filter non match search pattern
      --notify-eof int                          notify at the end of the file
      --pattern string                          search pattern
  -p, --plain                                   disable original decoration
  -F, --quit-if-one-screen                      quit if the output fits on one screen
  -r, --raw                                     raw escape sequences without processing
      --regexp-search                           regular expression search
      --ruler int                               display ruler (=0: none, =1: relative, =2: absolute)
      --section-delimiter regexp                regexp for section delimiter .e.g. "^#"
      --section-header                          enable section-delimiter line as Header
      --section-header-num int                  number of section header lines (default 1)
      --section-start int                       section start position
      --set-terminal-title                      set terminal title
      --skip-extract                            skip extracting compressed files
      --skip-lines int                          skip the number of lines
      --smart-case-sensitive                    smart case-sensitive in search
      --status-line[=true|false]                status line (default true)
  -x, --tab-width int                           tab stop width (default 8)
  -v, --version                                 display version information
  -y, --vertical-header int                     number of characters to display as a vertical header
  -m, --view-mode string                        apply predefined settings for a specific mode
  -T, --watch seconds                           watch mode interval(seconds)
  -w, --wrap[=true|false]                       wrap mode (default true)
~~~

## Spec 4

`-v` and `--version` exit 0 and write exactly `ov version dev rev:HEAD` followed by a newline to stdout. They normally write nothing to stderr. `--list-view-modes` writes one mode name per line, always beginning with `general`; without a loaded custom configuration its exact output is `general\n`. With the supplied standard `ov.yaml`, its exact output is `general\nmarkdown\nmysql\npsql\n`. Additional names under a YAML `Mode` mapping are appended, one each, in declaration order.

`--help-key` exits 0 and prints a plain-text key reference. With default bindings its stdout is exactly the following, including tabs before group titles and the final newline:

~~~text
ov is a feature rich pager
 Key                            Action

	General
 [Escape], [q]                  * quit
 [ctrl+c]                       * cancel
 [Q]                            * output screen and quit
 [ctrl+q]                       * set output screen and quit
 [alt+shift+F8]                 * set output original screen and quit
 [ctrl+z]                       * suspend
 [alt+v]                        * edit current document
 [h], [ctrl+F1], [ctrl+alt+c]   * display help screen
 [ctrl+F2], [ctrl+alt+e]        * display log screen
 [ctrl+l]                       * screen sync
 [ctrl+f]                       * follow mode toggle
 [ctrl+a]                       * follow all mode toggle
 [ctrl+F8], [ctrl+alt+r]        * enable/disable mouse
 [S]                            * save buffer to file

	Moving
 [Enter], [Down], [ctrl+n]      * forward by one line
 [Up], [ctrl+p]                 * backward by one line
 [Home]                         * go to top of document
 [End]                          * go to end of document
 [PageDown], [ctrl+v]           * forward by page
 [PageUp], [ctrl+b]             * backward by page
 [ctrl+d]                       * forward a half page
 [ctrl+u]                       * backward a half page
 [left]                         * scroll left
 [right]                        * scroll right
 [ctrl+left]                    * scroll left half screen
 [ctrl+right]                   * scroll right half screen
 [alt+left]                     * scroll left specified width
 [alt+right]                    * scroll right specified width
 [shift+Home]                   * go to beginning of line
 [shift+End]                    * go to end of line
 [g]                            * go to line(input number or `.n` or `n%` allowed)
 [,]                            * go to mark number(input number allowed)

	Sidebar
 [alt+h]                        * show/hide help in sidebar
 [alt+m]                        * show mark list in sidebar
 [alt+l]                        * show document list in sidebar
 [shift+Up]                     * scroll up in sidebar
 [shift+Down]                   * scroll down in sidebar
 [shift+Left]                   * scroll left in sidebar
 [shift+Right]                  * scroll right in sidebar

	Move document
 []]                            * next document
 [[]                            * previous document
 [ctrl+k]                       * close current document
 [K]                            * close all filtered documents

	Mark position
 [m]                            * mark current position
 [M]                            * remove mark current position
 [ctrl+delete]                  * remove all mark
 [>]                            * move to next marked position
 [<]                            * move to previous marked position
 [*]                            * mark by pattern mode

	Search
 [/]                            * forward search mode
 [?]                            * backward search mode
 [n]                            * repeat forward search
 [N]                            * repeat backward search
 [&]                            * filter search mode

	Change display
 [w], [W]                       * wrap/nowrap toggle
 [c]                            * column mode toggle
 [alt+o]                        * column width toggle
 [ctrl+r]                       * column rainbow toggle
 [C]                            * alternate rows of style toggle
 [G]                            * line number toggle
 [ctrl+e]                       * original decoration toggle(plain)
 [alt+f]                        * align columns
 [alt+r]                        * raw output
 [alt+shift+F9]                 * ruler toggle
 [ctrl+F10]                     * status line toggle

	Change Display with Input
 [p], [P]                       * view mode selection
 [d]                            * column delimiter string
 [H]                            * number of header lines
 [ctrl+s]                       * number of skip lines
 [t]                            * TAB width
 [.]                            * multi color highlight
 [j]                            * jump target(`.n` or `n%` or `section` allowed)
 [alt+t]                        * convert type selection
 [y]                            * number of vertical header
 [Y]                            * number of header column

	Column operation
 [F]                            * header column fixed toggle
 [s]                            * shrink column toggle(align mode only)
 [alt+a]                        * right align column toggle(align mode only)

	Section operation
 [alt+d]                        * section delimiter regular expression
 [ctrl+F3], [alt+s]             * section start position
 [space]                        * next section
 [^]                            * previous section
 [9]                            * last section
 [F2]                           * follow section mode toggle
 [F7]                           * number of section header lines
 [alt+-]                        * hide "other" section toggle

	Close and reload
 [ctrl+F9], [ctrl+alt+s]        * close file
 [F5], [ctrl+alt+l]             * reload file
 [F4], [ctrl+alt+w]             * watch mode
 [ctrl+w]                       * set watch interval

	Key binding when typing
 [alt+c]                        * case-sensitive toggle
 [alt+s]                        * smart case-sensitive toggle
 [alt+r]                        * regular expression search toggle
 [alt+i]                        * incremental search toggle
 [!]                            * non-match toggle
 [Up]                           * previous candidate
 [Down]                         * next candidate
 [ctrl+c]                       * copy to clipboard
 [ctrl+v]                       * paste from clipboard

~~~

A custom KeyBind YAML mapping replaces or augments the keys shown for its named action while retaining this layout; multiple keys for one action must all be shown. With `DefaultKeyBind: disable`, omit all default mappings and show only configured keys.

## Spec 5

Unknown flags, missing option arguments, and invalid typed values produce an `Error:` line on stderr and exit 1. Required diagnostics include these substrings exactly:

- `unknown flag: --nonexistent-flag` for an unknown long flag.
- `unknown shorthand flag: 'Z'` for `-Z`.
- `flag needs an argument: --column-delimiter` and similarly for other value flags.
- `invalid argument "foo" for "-H, --header" flag` for a noninteger header.
- `invalid argument "foo" for "-T, --watch" flag` for a nonnumeric watch interval.
- `invalid argument "maybe" for "--incsearch" flag` and `invalid argument "maybe" for "-w, --wrap" flag` for invalid booleans.
- `invalid argument "abc" for "--memory-limit" flag: strconv.ParseInt: parsing "abc": invalid syntax` for that exact case.

An operand that cannot be opened normally produces `Error: open PATH: OPERATING-SYSTEM-ERROR` on stderr and exit 1. Thus missing files mention `no such file or directory`, broken links behave as missing targets, and circular links mention `too many levels of symbolic links`. A directory reaches the redirected copy operation instead: with ordinary captured stdout it exits 1 and writes exactly `Error: write /dev/stdout: copy_file_range: is a directory` plus a newline to stderr. Stop at and report the first failed operand only if no usable document can be opened; if some operands open and others fail, keep the successful documents usable while reporting failures. `--wrap --wrap=false` is valid and leaves wrapping off. Unsupported converter names fall back to `es`. Negative numeric display settings must not crash; negative skip acts as zero, and negative memory limit means unlimited.

## Spec 6

`--completion` accepts only `bash`, `zsh`, `fish`, or `powershell`. Any other value exits 1 and includes `requires one of the arguments bash/zsh/fish/powershell` in stderr. A valid value emits a complete usable shell completion script and exits 0. Its first 30 lines must match the conventional Cobra-generated completion for command `ov`; in particular:

- bash begins `# bash completion for ov                                   -*- shell-script -*-` and defines `__ov_debug`, `__ov_init_completion`, `__ov_index_of_word`, and `__ov_contains_word`.
- zsh begins `#compdef ov`, `compdef _ov ov`, a blank line, then `# zsh completion for ov                                   -*- shell-script -*-`, and defines `__ov_debug` and `_ov()`.
- fish begins `# fish completion for ov                                   -*- shell-script -*-` and defines `function __ov_debug` and `function __ov_perform_completion`.
- PowerShell begins `# powershell completion for ov                                   -*- shell-script -*-`, defines `function __ov_debug`, then `filter __ov_escapeStringWithSpecialChars`, and declares `[scriptblock]${__ovCompleterBlock}`.

The exact required 30-line prefixes are:

~~~bash
# bash completion for ov                                   -*- shell-script -*-

__ov_debug()
{
    if [[ -n ${BASH_COMP_DEBUG_FILE:-} ]]; then
        echo "$*" >> "${BASH_COMP_DEBUG_FILE}"
    fi
}

# Homebrew on Macs have version 1.3 of bash-completion which doesn't include
# _init_completion. This is a very minimal version of that function.
__ov_init_completion()
{
    COMPREPLY=()
    _get_comp_words_by_ref "$@" cur prev words cword
}

__ov_index_of_word()
{
    local w word=$1
    shift
    index=0
    for w in "$@"; do
        [[ $w = "$word" ]] && return
        index=$((index+1))
    done
    index=-1
}

__ov_contains_word()
~~~

~~~zsh
#compdef ov
compdef _ov ov

# zsh completion for ov                                   -*- shell-script -*-

__ov_debug()
{
    local file="$BASH_COMP_DEBUG_FILE"
    if [[ -n ${file} ]]; then
        echo "$*" >> "${file}"
    fi
}

_ov()
{
    local shellCompDirectiveError=1
    local shellCompDirectiveNoSpace=2
    local shellCompDirectiveNoFileComp=4
    local shellCompDirectiveFilterFileExt=8
    local shellCompDirectiveFilterDirs=16
    local shellCompDirectiveKeepOrder=32

    local lastParam lastChar flagPrefix requestComp out directive comp lastComp noSpace keepOrder
    local -a completions

    __ov_debug "\n========= starting completion logic =========="
    __ov_debug "CURRENT: ${CURRENT}, words[*]: ${words[*]}"

    # The user could have moved the cursor backwards on the command-line.
    # We need to trigger completion from the $CURRENT location, so we need
~~~

~~~fish
# fish completion for ov                                   -*- shell-script -*-

function __ov_debug
    set -l file "$BASH_COMP_DEBUG_FILE"
    if test -n "$file"
        echo "$argv" >> $file
    end
end

function __ov_perform_completion
    __ov_debug "Starting __ov_perform_completion"

    # Extract all args except the last one
    set -l args (commandline -opc)
    # Extract the last arg and escape it in case it is a space
    set -l lastArg (string escape -- (commandline -ct))

    __ov_debug "args: $args"
    __ov_debug "last arg: $lastArg"

    # Disable ActiveHelp which is not supported for fish shell
    set -l requestComp "OV_ACTIVE_HELP=0 $args[1] __complete $args[2..-1] $lastArg"

    __ov_debug "Calling $requestComp"
    set -l results (eval $requestComp 2> /dev/null)

    # Some programs may output extra empty lines after the directive.
    # Let's ignore them or else it will break completion.
    # Ref: https://github.com/spf13/cobra/issues/1279
    for line in $results[-1..1]
~~~

~~~powershell
# powershell completion for ov                                   -*- shell-script -*-

function __ov_debug {
    if ($env:BASH_COMP_DEBUG_FILE) {
        "$args" | Out-File -Append -FilePath "$env:BASH_COMP_DEBUG_FILE"
    }
}

filter __ov_escapeStringWithSpecialChars {
    $_ -replace '\s|#|@|\$|;|,|''|\{|\}|\(|\)|"|`|\||<|>|&','`$&'
}

[scriptblock]${__ovCompleterBlock} = {
    param(
            $WordToComplete,
            $CommandAst,
            $CursorPosition
        )

    # Get the current command line and convert into a string
    $Command = $CommandAst.CommandElements
    $Command = "$Command"

    __ov_debug ""
    __ov_debug "========= starting completion logic =========="
    __ov_debug "WordToComplete: $WordToComplete Command: $Command CursorPosition: $CursorPosition"

    # The user could have moved the cursor backwards on the command-line.
    # We need to trigger completion from the $CursorPosition location, so we need
    # to truncate the command-line ($Command) up to the $CursorPosition location.
~~~

## Spec 7

Configuration is YAML. An explicit `--config PATH` has highest priority. Otherwise search `$XDG_CONFIG_HOME/ov/config.yaml` when XDG_CONFIG_HOME is nonempty, then `$HOME/.config/ov/config.yaml`, then the legacy `$HOME/.ov.yaml`. A missing implicit configuration is silently ignored unless debug is active. A missing explicit file, malformed YAML, a type-invalid YAML structure, or an extension from which the type cannot be inferred writes `failed to read config file:` plus the underlying reason to stderr but does not stop commands such as version, help-key, or paging. A malformed YAML diagnostic begins exactly `failed to read config file: While parsing config:` before the YAML parser's detail; an extensionless explicit config reports `Unsupported Config Type`.

The configuration accepts both top-level legacy option names and a `General` mapping, a `Mode` mapping of named view modes, `KeyBind`, `Style`, and `DefaultKeyBind`. Empty and comment-only files are valid. CLI flags override environment, which overrides YAML, which overrides defaults. Environment variables are option names prefixed with `OV_` (for example `OV_DEBUG=false` and `OV_CAPTION`). A true debug setting writes `Using config file: PATH` to stderr for the selected file. `--debug` overrides `OV_DEBUG=false`; conversely that environment setting can disable YAML `Debug: true`.

## Spec 8

A view mode is a named bundle of display settings selected by `-m/--view-mode` or by the configured `ViewMode`. Mode fields use the option-style CamelCase names, including Header, AlternateRows, ColumnMode, LineNumMode, WrapMode, ColumnDelimiter, ColumnRainbow, TabWidth, section settings, and nested Style. CLI flags still take precedence. `general` always exists. Selecting an unknown mode interactively leaves the view intact and reports `view mode not found: NAME`; selecting one at startup falls back safely to general.

## Spec 9

Each file operand is a separate document. Literal paths may be relative or absolute and may contain spaces or begin with a dot. Follow symbolic links. Accept regular files, `/dev/null`, and named pipes/FIFOs. Expand unquoted glob syntax supplied as a single operand (`*`, `?`, and bracket expressions) in lexical path order; an unmatched pattern is treated as its literal path and therefore produces the ordinary missing-file error. The special operand `-` means stdin.

In redirected/noninteractive operation, output only the first document, exactly and completely; this rule also applies to multiple small files with `--quit-if-one-screen`. In interactive operation all successfully opened inputs become navigable documents, initially showing the first.

## Spec 10

Reading is streaming-safe and has no practical line-length or file-length ceiling under the tests: handle at least 150,000 lines, a million-line supplied file, and individual lines of at least 500 KiB. Never drop, duplicate, reorder, split, or truncate logical lines around internal boundaries; a useful internal chunk size is 10,000 lines, with line 10,000 ending the first chunk and 10,001 starting the next. Empty input yields no lines, N newline bytes yield N empty logical lines, and a final unterminated nonempty line remains present without gaining a newline.

`--memory-limit N` controls retained chunks for stdin/non-seekable input; `--memory-limit-file N` independently controls seekable files. Positive small values such as 1 must still permit correct traversal and complete redirected output. Zero and negative values mean unlimited. Limits affect storage only, never externally visible content.

## Spec 11

In the redirected pass-through path, preserve all bytes exactly after decompression policy: tabs are not expanded, ANSI sequences are not stripped, CR and CRLF are not normalized, NUL/DEL/form-feed/backspace and other controls remain present, invalid UTF-8 bytes pass through the subprocess decoding convention, blank lines and trailing whitespace remain, and no final newline is invented. This remains true for `--plain`, `--raw`, `--converter`, tab-width, line-number, wrap, header, section, column, search, filter, multicolor, ruler, and memory flags. Those flags configure the TUI and must parse successfully, but do not rewrite redirected file content.

## Spec 12

For interactive display, decode UTF-8 without crashing; malformed byte sequences render as literal question-mark characters (`?`), not U+FFFD glyphs. For example, interactively displaying the supplied gzip bytes with `--skip-extract` produces the visible row `2kmf  test.txt +I-.?  ?5?;`. Determine cell widths using terminal Unicode width: combining marks attach to the preceding character and consume zero cells, ordinary characters consume one, and CJK/emoji wide characters consume two. Tab expansion advances to the next multiple of TabWidth based on current display column; width 0 removes the tab’s visual spacing. A negative command-line tab width is tolerated and uses safe/raw behavior.

Interpret carriage return, backspace, DEL, NUL, bell, form-feed, and other controls without letting them corrupt terminal state. Backspace moves over the preceding displayed character (including a two-cell character or tab). `X\bX` represents an overstruck/bold X; `_\bX` represents underlined X; a different replacement such as `o\bW` displays W. Controls at the start of a line or repeated controls are safe.

## Spec 13

Interactive file viewing automatically detects compression by magic bytes, not by extension: gzip `1f 8b 08`, bzip2 `42 5a 68`, zstd `28 b5 2f fd`, lz4 `04 22 4d 18`, and xz beginning `fd 37 7a 58 5a 00`. Decode a valid stream and display its decompressed text; this composes with column alignment and every normal viewer feature. A file with a compression-looking suffix but no matching magic, or one shorter than a complete signature, is ordinary uncompressed data. A corrupt stream with a matching header must fail gracefully within the viewer rather than panic or hang, and must not replace its content with a textual decompression-error diagnostic. Display any successfully decoded content produced before the corrupt portion: a valid gzip member for `BE@A@` followed by a corrupt member displays the single row `BE@A@` and reports `(1/1)`. A file consisting of only the complete three-byte gzip signature is treated as recognized but truncated and displays one empty logical row with `(1/1)`, again without an error row. `--skip-extract` disables detection and displays the raw bytes safely.

Redirected pass-through is intentionally different: it copies a compressed input’s raw compressed bytes whether or not the extension/signature is recognized. `--skip-extract` therefore makes no additional byte change there. Memory-limit settings must not change compressed output.

## Spec 14

The interactive viewer owns the terminal, responds within a fraction of a second, restores it on exit, and adapts to its current width and height. It renders exactly one cell row per terminal row. Unless disabled, the last row is the status row; all preceding rows are the content viewport, less any rows reserved by rulers or fixed headers. Clear unused cells. Rows below end-of-file contain `~` in column 1 when the horizontal offset is zero, except for the line-number indentation specified in Spec 23, and are blank when scrolled horizontally.

Render logical lines from the current top position. With wrapping on, split only at the right screen edge (not at words), continue immediately on the next screen row, and account for Unicode cell widths. With wrapping off, render one logical line per row, clipped to the current horizontal window. Never append ellipses. On an 80-by-24 terminal with the 40-line supplied `normal.txt`, the initial top line is 1, three Down presses move the top to logical line 2, one PageDown moves it to logical line 15, and End places line 28 at the top; this follows naturally by counting wrapped screen rows.

## Spec 15

The normal status row consists of an optional mode prefix, the document label, a colon, a transient message, padding, and a right-aligned `(TOP/TOTAL)` position. Preserve the path spelling used to open a file; stdin is labeled `(STDIN)`. In multi-document mode prefix the zero-based document index in brackets, for example `[0]`. Captions replace the document label. The exact position is the top logical line and total logical line count; an empty file reports `(1/0)`. Long left-hand text/messages are clipped so the position remains visible when possible. Every live single-line input prompt also retains this same right-aligned position field on its bottom row; prompt text is padded or clipped before the position rather than replacing it.

Mode prefixes include `(Follow Mode)`, `(Follow All)`, `(Follow Section)`, and `(Watch)`. A startup filter repeats its pattern in both filter and search fields; for example, pattern `blue` produces `filter:blue:search:blue`, while its inverted form produces `filter:!blue:search:!blue`. A failed committed search inserts `not found:` before its pattern, as in the observed `search:not found:notexist`; a successful committed or repeated search returns to the ordinary document label without a `search:` suffix. During text input, the status row is replaced by the relevant prompt even if normal status is disabled, but its position field remains visible. `--status-line=false` removes the normal status row and grants that row to content; Ctrl+F10 toggles it and reports `Status Line hidden` or `Status Line visible` on the temporary bottom row.

## Spec 16

Vertical movement is screen-row aware under wrapping and logical-line aware otherwise:

- Down, Enter, and Ctrl+N advance the navigation point by one displayed row and scroll the viewport only when needed; Up and Ctrl+P retreat similarly. Consequently, on an unwrapped four-line document that already fits wholly in an 80-by-24 viewport, Down leaves the rendered view and `(1/4)` top position unchanged, including after horizontal scrolling.
- PageDown/Ctrl+V and PageUp/Ctrl+B move by one content-page. On a 24-row terminal without extra decorations, successive full pages in a million-line one-row-per-line file start at 1, 24, and 47. PageUp reverses this.
- Ctrl+D and Ctrl+U move half a content page; in that same terminal the starts are 1, 12, and 23.
- Home jumps to the top. End loads through EOF and puts as many final lines as fit; for 1,000 one-row lines at 80 by 24 the top becomes 979, and for one million it becomes 999979.
- Movement clamps at the beginning/end, never exits, and preserves a stable screen.

`q` or Escape in normal mode quits cleanly. Ctrl+C cancels an active input operation rather than killing the process. Unbound keys such as F12 leave the viewer running.

## Spec 17

Wrapping defaults on and `-w/--wrap[=BOOL]` sets it. `w` and `W` toggle it at runtime and report `Set WrapMode false` or `Set WrapMode true`. Horizontal movement has no visible effect while wrapping is on. With wrapping off, Left/Right move the horizontal origin one display column, Ctrl+Left/Ctrl+Right move half the available width, Shift+Home goes to column zero, and Shift+End goes far enough right to show the line end. Alt+Left/Alt+Right move by HScrollWidth, which accepts a nonnegative integer cell count, `N%`, or decimal fraction `.N`; percentages/fractions are of viewport width and default to 10%.

The horizontal origin never becomes negative. It persists across vertical movement. Short lines show blank space at offsets past their ends. Tabs and wide characters are scrolled by display cells without breaking their encoding. In column mode, horizontal movement selects adjacent columns; it cycles first-to-last/last-to-first unless `--disable-column-cycle`, in which case it stays at the boundary and reports `Cannot move column`.

## Spec 18

`g` opens `Goto line:` input. Accept an absolute positive line, a percentage such as `50%`, or a decimal fraction such as `.5`; Enter moves there with range clamping, and `1` returns to the first line. A successful goto reports `Moved to line ` followed by the resulting one-based decimal line; observed exact messages include `Moved to line 5000` and `Moved to line 1`. Invalid text leaves the prompt once submitted and reports `invalid number`. Empty input does nothing; Escape cancels.

`-j/--jump-target` controls where a found/goto target appears in the viewport: positive N means N rows down from the top (1 is top), negative N means upward from the bottom (-1 is bottom), and percentages/fractions identify a proportional viewport row. The keyword `section` aligns the start of the current section and switches section-aware placement on. `j` opens `Jump target line:` with the same accepted forms; committing `section` reports exactly `Set JumpTarget section start`, while out-of-range input reports `Set JumpTarget VALUE: value out of range`.

## Spec 19

`-H/--header N` fixes the first N visible logical lines at the top while the remainder scrolls. The initial/current body position is the first line after the header, and the status position reflects that body position even when it is past EOF: a one-line header-only document with `-H 1` reports `(2/1)`. `--skip-lines N` hides the first N logical lines before choosing headers/body; negative skip is zero. Header count zero disables it, and a count beyond EOF simply fixes all available lines. During scrolling, fixed header rows remain byte-for-byte the same while body rows change. `H` opens `Header length:`; committing a count reports `Set header lines ` followed by that decimal count (exactly `Set header lines 2` for input 2). Ctrl+S opens the skip-line prompt. Submitted nonintegers (including an empty header submission) report respectively `Set header lines: invalid number` and `Set skip lines: invalid number`.

`-y/--vertical-header N` fixes the first N display characters/cells on the left during horizontal scrolling; `y` opens `Vertical header length:`. In column mode, `-Y/--header-column N` instead fixes the first N parsed columns, and `Y` opens `Header column:`; committing a count reports `Set vertical header column ` followed by that decimal count (exactly `Set vertical header column 1` for input 1). F toggles fixing through the currently selected column. Invalid values leave the viewer usable and report `Set vertical header: invalid number` or `Set vertical header column: invalid number`.

## Spec 20

`--section-delimiter REGEXP` marks every logical line matching the regular expression as a section start. Matching excludes newline bytes. The current section runs from its marker through the line before the next marker. `--section-start N` adjusts the vertical screen row at which a section begins; `--section-header` makes the current marker a fixed header, and `--section-header-num N` fixes N section-starting lines. Empty/no-match patterns are safe. Invalid regex entered interactively is rejected without losing the document.

Space jumps to the next section, `^` to the previous, and `9` to the last. With the supplied 10-line `section.txt` and delimiter `^#`, these positions are initially 1, next 3, and last 9. With supplied `section-header.txt`, the next/last relevant start is line 15. At the final/first section, further movement stays put and reports exactly `No more next sections` or `No more previous sections`. Without a configured delimiter, all three keys are harmless no-ops. `--hide-other-section` shows only the current section; Alt+- toggles it and reports `Set HideOtherSection true/false`. F2 toggles follow-section and, when enabled, prefixes the status with `(Follow Section)`. Alt+D prompts `Section delimiter:`, Alt+S or Ctrl+F3 prompts `Section start:`, and F7 prompts for section-header count with the exact label `Section Num:`; invalid numeric input reports the corresponding `invalid number`, and an out-of-range section start reports `value out of range`.

## Spec 21

`-c/--column-mode` parses and selects tabular columns without changing the characters themselves. `-d/--column-delimiter DELIM` defaults to comma and accepts a literal string/character, a literal tab, or a regular expression enclosed in slashes (for example `/\s+/` or `/[,;]/`). CSV quoting is honored, so a delimiter inside a quoted field does not split it. Empty delimiter disables useful splitting safely. Handle empty cells, a single-column file, unequal field counts, and large tables.

`--column-width` discovers fixed columns separated by runs of whitespace and enables column-style navigation. `-l/--align` and `--converter=align` pad each nonfinal field to the maximum display width of that column over the data, retaining empty fields and using the configured delimiter boundaries. Plain `-c` does not align. Long/wide fields wrap or clip by the ordinary viewport rules. `s` toggles shrinking an aligned selected column and Alt+A toggles its right alignment; outside align mode these operations report `not in align mode`. `--column-rainbow` applies successive configured column styles only when columns exist. Runtime keys are c (column), Alt+O (width), Ctrl+R (rainbow), Alt+F (align), and d (`Delimiter:` prompt), with messages `Set ColumnMode BOOL`, `Set ColumnWidth BOOL`, `Set Column Rainbow Mode BOOL`, and `Set align converter`.

## Spec 22

The `es` converter, used by default, parses terminal escape sequences for interactive presentation while retaining only their visible text/cell effects. It recognizes SGR introduced by CSI and supports reset; bold/dim/italic/blink/reverse/invisible/strike/overline; attribute-off codes; standard and bright foreground/background colors; 256-color form `38|48;5;N`; truecolor form `38|48;2;R;G;B`; colon-separated/double-colon variants; underline styles and underline color; and defaults. It recognizes OSC 8 hyperlinks terminated by BEL or ESC-backslash, showing the link label. Cursor movement CSI is ignored as movement, and erase-in-line changes cells/styles safely. ESC-c and supported reset sequences reset state.

Malformed, incomplete, empty-parameter, out-of-range, unknown CSI/OSC/SGR, stray ESC, and embedded/substring sequences must never panic or consume unrelated visible text. `raw` (`-r/--raw` or converter raw) displays escape-sequence characters as literal data rather than interpreting styles. `--plain` (`-p`) keeps `es` text interpretation but suppresses all resulting decoration. Ctrl+E toggles plain with `Set PlainMode BOOL`; Alt+R selects raw; Alt+T opens `Convert:` selection. Empty or cancelled converter input keeps the current converter; Down in the prompt can, for example, render `Convert:raw`.

## Spec 23

Line numbers are enabled by `-n/--line-number` and toggled by G. Prefix each logical line with its one-based decimal number plus one space; wrapped continuations align with the content rather than acquiring new logical numbers. EOF-marker rows are indented to the content column too, so with one-digit line numbers they begin exactly `  ~` rather than `~`. Report `Set LineNumMode BOOL`. `-C/--alternate-rows`, toggled by C, applies the configured Alternate style to alternating logical rows and reports `Set AlternateRows BOOL`. These features compose with headers, columns, wrapping, search, and navigation.

`--ruler N` accepts 0 (off), 1 (relative to horizontal viewport), and 2 (absolute document columns). Values 1 and 2 reserve two top rows: a tens row containing labels at columns 10, 20, ... and a units row repeating `1234567890`. Relative numbering starts at the visible left; absolute numbering reflects the horizontal origin. Alt+Shift+F9 cycles 0 to 1 to 2 to 0.

`--caption TEXT` or `OV_CAPTION` replaces the filename portion of the status label without changing content. `--set-terminal-title` emits an appropriate terminal-title sequence in TUI mode only and otherwise leaves content intact.

## Spec 24

Search operates on visible text after removing ANSI control sequences and accounting for backspace overstrikes. `/` opens forward search and `?` backward search. The prompt begins `(I)/` or `(I)?` when incremental search is enabled. Enter commits; Escape cancels. A fresh forward search includes the current top line as its first candidate; thus, if both lines 1 and 4 contain a literal numeric or symbol-only pattern, committing it from line 1 stays at `(1/4)`. `n` repeats in the forward direction and `N` in reverse, with wraparound at document ends. Place the matching logical line according to JumpTarget and highlight all matched spans, including multiple matches on one line. Empty search is harmless and returns to the unchanged normal view. A successful committed or repeated search clears the prompt/search status and returns to the ordinary label. A committed forward search that finds no match leaves the view at its original position and inserts `search:not found:` before the pattern; searching `notexist` from the initial first line of a three-line document reports `search:not found:notexist` and `(1/3)`.

By default matching is literal and Unicode case-insensitive: punctuation such as `.` and `*` has no wildcard meaning. `--regexp-search` enables regular expressions including anchors, classes, repetitions, alternation, escaped punctuation, and `\d`; a slash-enclosed pattern also requests regex compilation. An invalid regex falls back safely to literal matching. `-i/--case-sensitive` makes matching exact case. `--smart-case-sensitive` is insensitive for all-lowercase patterns and sensitive if the pattern contains uppercase. Case-sensitive takes priority. `--incsearch=false` delays movement until Enter; with it enabled, each typed character immediately advances to the current match. During search input Alt+C, Alt+S, Alt+R, and Alt+I toggle case-sensitive, smart-case, regex, and incremental behavior. Up/Down traverse prior patterns, and backslash can quote `!` so it remains part of the pattern.

## Spec 25

The default key-to-action contract is:

- General: Escape/q quit; Ctrl+C cancel; Q write screen and quit; Ctrl+Q configure before/after and quit; Alt+Shift+F8 select original-output-on-quit; Ctrl+Z suspend; Alt+V edit; h/Ctrl+F1/Ctrl+Alt+C help; Ctrl+F2/Ctrl+Alt+E log; Ctrl+L redraw/sync; Ctrl+F follow; Ctrl+A follow all; Ctrl+F8/Ctrl+Alt+R mouse; S save.
- Moving: Enter/Down/Ctrl+N one row forward; Up/Ctrl+P one row back; Home/End top/bottom; PageDown/Ctrl+V and PageUp/Ctrl+B full page; Ctrl+D/Ctrl+U half page; Left/Right one column; Ctrl+Left/Right half screen; Alt+Left/Right configured width; Shift+Home/End line beginning/end; g goto; comma goto mark number.
- Sidebar: Alt+H help, Alt+M marks, Alt+L documents; Shift+arrows scroll the active sidebar.
- Documents: `]` next, `[` previous, Ctrl+K close current, K close all filter-derived documents.
- Marks: m add current; M remove current; Ctrl+Delete remove all; `>` next, `<` previous; `*` mark by pattern.
- Search: `/` forward, `?` backward, n repeat forward, N repeat backward, `&` filter.
- Display: w/W wrap, c column, Alt+O column-width, Ctrl+R rainbow, C alternate rows, G line numbers, Ctrl+E plain, Alt+F align, Alt+R raw, Alt+Shift+F9 ruler, Ctrl+F10 status.
- Prompted display: p/P view mode, d delimiter, H header, Ctrl+S skip, t tab width, period multicolor, j jump target, Alt+T converter, y vertical header, Y header column.
- Column: F fix through selected column, s shrink, Alt+A right-align.
- Section: Alt+D delimiter, Ctrl+F3/Alt+S start, Space next, caret previous, 9 last, F2 follow-section, F7 header-line count, Alt+minus hide other.
- Control: Ctrl+F9/Ctrl+Alt+S close file; F5/Ctrl+Alt+L reload; F4/Ctrl+Alt+W watch; Ctrl+W watch interval.
- While typing: Alt+C case, Alt+S smart-case, Alt+R regex, Alt+I incremental, `!` invert filter, Up/Down history, Ctrl+C copy, Ctrl+V paste.

Terminals that report Ctrl+H/I/M/J identically to Backspace/Tab/Enter/line-feed may trigger the corresponding ordinary-key behavior. Configured KeyBind actions replace these event mappings consistently in both behavior and help output.

## Spec 26

`--filter REGEXP` creates and initially selects a derived document containing only matching logical lines. `--non-match-filter REGEXP` contains only nonmatching lines. Filtering defaults case-insensitive, observes the case and regex settings, strips ANSI controls for matching, and preserves original complete line text and order in the derived document. An empty filter matches all lines. A startup filter's status includes both filter and synthesized search fields after the document index; for `blue`, the exact fields are `filter:blue:search:blue`, or `filter:!blue:search:!blue` in nonmatching mode.

`&` opens a prompt beginning `&`; typing `!` toggles inversion and changes the prompt label to exactly `Non-match&`. Toggling again restores the ordinary `&` label. Enter creates/selects the derived document. Up/Down access filter history. Filter results are ordinary navigable documents: brackets return to the original or other filters, Ctrl+K closes one, and K closes all filter-derived documents without closing source documents. Filtering and `--quit-if-one-screen` in redirected mode output the original bytes per Spec 11; filtering changes the TUI only.

## Spec 27

`-M/--multi-color` accepts one or more comma-separated regex patterns. The period key opens `Multi color:` input, where patterns are separated by spaces; quoted patterns may contain spaces. Enter stores them and reports `Set multicolor strings [P1 P2 ...]`. Empty input clears or leaves highlighting safely, Escape cancels, and Up/Down cycle candidate history. Default candidates include `ERROR WARNING NOTICE INFO PANIC FATAL LOG` and `error info warn debug`.

Every pattern is independently compiled and all occurrences receive successive styles from the configured MultiColorHighlight palette, cycling if needed. It composes with search, column mode, case sensitivity, ANSI text, and long lines, and never changes redirected output bytes.

## Spec 28

Interactive multiple-document state retains a separate top line, horizontal offset, search/filter state, and marks per document. `]` and `[` cycle forward/back through documents and wrap at the ends. Ctrl+K removes the current document and selects the previous surviving document; when the first document is removed, the new first document is selected. A successful close reports `close ` followed by the now-selected survivor's bracketed index and label; for example, selecting `/tmp/ov-doc1.txt` at index zero produces exactly `close [0]/tmp/ov-doc1.txt`. Attempting to remove the last document leaves it open and reports `only this document`. If opening a set has partial failures, all successfully opened files remain available.

Alt+L toggles a `Files` sidebar listing every document in order with zero-based indices and names and visibly indicating the active one. Alt+H toggles a `Help` sidebar, and Alt+M a `Marks` sidebar. The main content remains visible beside a sidebar. Repeating the same toggle hides it and reports `Sidebar hidden`; opening help reports `Sidebar Help visible`. Shift+Up/Down/Left/Right scroll sidebar content without moving the document.

## Spec 29

`m` marks the current top logical line and reports `Marked to line N`; duplicate marks are not added. `M` removes a mark at the current line and reports removal. Ctrl+Delete clears all marks. `>` goes to the next mark and `<` to the previous, wrapping around; a successful mark jump reports `Moved to line ` followed by its one-based decimal destination (for example, `Moved to line 1`), and with no marks these are no-ops. Comma opens numeric mark selection with the exact prompt `Mark number:`, using zero-based mark index.

`*` prompts for a search pattern and marks every matching line in the entire document, not merely visible lines. The Marks sidebar lists marks in ascending line order with zero-based indices, one-based line numbers, and a preview of line content, and indicates the active mark. Mark styles and selections do not alter the underlying text or exported original output.

## Spec 30

All interactive input modes share an editable single-line field on the bottom row. Printable keys insert at the cursor; Left/Right move it, Delete/Backspace remove text safely, Ctrl+U clears, Enter commits, and Escape cancels without applying partial input. Up/Down cycle that mode’s candidates/history. Empty tab-width, delimiter, multicolor, watch-interval, section-delimiter/start, view-mode, and converter submissions retain/clear safely and close the prompt; an empty header submission is specifically an `invalid number` error. Bad numeric/regex/view-mode values never crash and return to a usable viewer with a short status error.

The exact prompt labels are `(I)/` and `(I)?` for search, `&` for filter, `Goto line:`, `Header length:`, `Header column:`, `Vertical header length:`, `TAB width:`, `Delimiter:`, `Multi color:`, `Jump target line:`, `Section delimiter:`, `Section start:`, `Section Num:`, `Mark number:`, `Watch interval:`, `Convert:`, `(Save)file:`, and `WriteAndQuit Before:After:`. The prompt's current text follows the label directly, and the normal `(TOP/TOTAL)` field remains right-aligned on the same row throughout empty, typed, and history-populated states. Ctrl+Q’s value syntax is `BEFORE:AFTER` such as `10:20`. Numeric prompt input permits zero where sensible (notably tab width), tolerates very large values by clipping display work, and rejects malformed input with `invalid number` or the feature-specific messages described above.

## Spec 31

`-f/--follow-mode` keeps a file or stdin stream open, initially moves to the bottom, polls for appended data, appends it once, and keeps the newest content visible. Ctrl+F toggles it. Status is prefixed `(Follow Mode)`. Bottom alignment is not clamped to one: on an 80-by-24 terminal a one-line file reports `(-20/1)`, and a three-line file reports `(-19/3)`, with `~` rows above the content. Sticky follow pauses auto-scrolling when the user navigates upward and resumes on returning to bottom; a paused state may show `||` and style the pause line. `--follow-name` follows the path rather than only the original descriptor so replacement/rotation can be observed.

`-A/--follow-all` monitors every open file and automatically selects the most recently updated document, with `(Follow All)` status; Ctrl+A toggles it. `--follow-section` follows the newest whole section rather than individual lines and works with F2. All follow modes remain alive after EOF until explicitly quit.

## Spec 32

`-T/--watch SECONDS` enables watch mode at a nonnegative numeric interval; the practical default when toggled by F4 is one second. It periodically reloads the current source, appends a form-feed section boundary between snapshots, enables section-follow behavior, moves to the newest snapshot, and prefixes status `(Watch)`. It notices replacement content as well as appends. F4 toggles watch and Ctrl+W prompts `Watch interval:`. Invalid CLI intervals are argument errors; invalid interactive entries leave the old value.

F5 (or Ctrl+Alt+L) immediately reloads a regular file from disk, retaining a valid/clamped position, and reports `reload file PATH`. Reloading reflects changed, added, and removed lines. The same action in exec mode reruns the command and replaces its stdout/stderr documents.

## Spec 33

Interactive exec mode is enabled with `-e/--exec`. An optional `--` separates pager flags from the command; after it, every token is passed verbatim as argv. In a TTY, for compatibility, operands directly following exec mode are also accepted as the command. Execute with the inherited environment and a pseudo-terminal where available. Capture command stdout and stderr concurrently into two distinct documents whose labels contain argv[0] in parentheses followed by `STDOUT` or `STDERR`, initially select stdout, and allow `]`/`[` switching. Because these are two documents, their normal status labels include indices; observed stdout labels include `[0](/bin/printf)STDOUT:`, `[0](/bin/ls)STDOUT:`, and `[0](/bin/sh)STDOUT:`. Preserve progressive output and content produced before a nonzero exit. A missing command becomes readable stderr content and does not crash the viewer. On the redirected `--exec -- /nonexistent/command` path, it instead exits 1 and writes exactly `Error: open /nonexistent/command: no such file or directory` plus a newline to stderr.

F5 reruns the same command. Combining exec with watch reruns it at each interval; the command must actually execute repeatedly. Shell constructs are interpreted only when the caller explicitly invokes a shell such as `sh -c`; argv itself is not reparsed. In redirected mode, exec without the `--` separator follows normal positional-file/pass-through parsing (and can consequently report `open COMMAND`); exec with no command and stdin remains safe.

## Spec 34

`h`, Ctrl+F1, or Ctrl+Alt+C toggles an internal help document. Its first row is centered text `ov help`, followed by ` Key                            Action`, a blank row, and the same grouped mappings as `--help-key`. At terminal width 80, `ov help` has exactly 24 leading spaces. It is a scrollable 125-line document with status `Help:` and an initial top position `(3/125)` because its first two title rows are fixed. Down/PageDown scroll it; h or Escape returns to the prior document and position.

Ctrl+F2 or Ctrl+Alt+E toggles a live log document. In debug mode it contains operational messages such as `open [0]`; it is labeled `(Follow Mode)Log:` and follows new log entries. Toggling again restores the prior document. Ctrl+L redraws without changing state.

## Spec 35

S saves the full currently buffered original text only for a non-seekable source such as a pipe/stdin document. It opens `(Save)file:`; entering a nonexistent destination creates it with exact source content and reports `saved PATH`. If the path exists, prompt exactly `overwrite? (O)overwrite, (A)Append, (N)cancel:`. O truncates then writes the buffer, A appends it without inserting or deleting bytes, and N/Escape leaves it unchanged and reports `save cancel`. On a regular seekable file, S does not open the prompt and instead reports exactly `Cannot save seekable files`.

Q exits after writing the currently rendered screen. Ctrl+Q first opens `WriteAndQuit Before:After:` and accepts optional integer counts. `--exit-write/-X` requests this behavior on normal exit; `--exit-write-before/-b` and `--exit-write-after/-a` select additional logical lines around the screen’s top, clamped to document bounds. Negative counts are accepted safely. In redirected operation these flags do not restrict content: output remains the complete first input. With zero, excessive, combined, or reordered before/after flags, pass-through is still complete and exact.

## Spec 36

Alt+V edits the current document using command priority `OVEDIT`, configured Editor, `EDITOR`, then a safe default editor. Parse quoted command arguments. Replace unescaped `%f` with the document path and `%d` with the current one-based logical line; `%%f` and `%%d` become literal `%f` and `%d`. If no `%f` occurs, append the file path as the last argument; do not append a duplicate when it does occur.

For stdin/nonseekable documents, first export the buffered content to a temporary path beginning `/tmp/ov-edit-` and pass that path. Restore the terminal while the editor runs, then resume the viewer, reload changed regular-file content, and preserve/clamp the previous position. Editor-not-found or nonzero editor errors are shown as status/log errors without terminating the pager. Arguments containing spaces and shell quoting remain intact.

## Spec 37

Mouse handling is enabled by default and disabled by `--disable-mouse`; Ctrl+F8 or Ctrl+Alt+R toggles it and reports `Disable Mouse`/`Enable Mouse`. Wheel scrolls vertically, Shift+wheel horizontally. A drag selects text respecting tabs and line boundaries; double click selects a word, triple click a line. Selected text is copied through the available clipboard method. Left click sets an anchor; Alt+click or right click extends and copies; a double click with no selection clears the anchor. Disabled mouse input does not corrupt the display.

Ctrl+Z temporarily leaves/restores the full-screen interface. On Unix it suspends so `fg` resumes; when `OV_SUBSHELL` is set it opens a subshell and resumes after `exit`. In either case content and navigation position are preserved. SIGTERM and ordinary quit restore terminal modes promptly.

## Spec 38

Style configuration must be accepted without errors and visibly applied in a color-capable TUI. A style has optional Foreground/Background names or `#RRGGBB`, Reverse, Bold, Blink, Dim, Italic, Underline, UnderlineStyle 0 through 5, and UnderlineColor. Supported named targets include Header, HeaderBorder, LineNumber, SearchHighlight, ColumnHighlight, MarkLine, SectionLine, SectionBorder, MultiColorHighlight, ColumnRainbow, JumpTargetLine, VerticalHeader, VerticalHeaderBorder, Ruler, Alternate, LeftStatus, RightStatus, SelectActive, SelectCopied, and PauseLine. MultiColorHighlight and ColumnRainbow are arrays. Legacy top-level `StyleName` objects remain accepted; modern styles may occur under General.Style or a Mode.Style.

Color/style escape sequences are emitted only to the terminal backend, never into snapshot-visible text or redirected pass-through bytes. Alternate rows, rainbow columns, search spans, marks, fixed headers, and selection can overlap without losing characters.

## Spec 39

These CLI spellings are all required and may be combined in arbitrary order: `-l/--align`, `-C/--alternate-rows`, `--caption`, `-i/--case-sensitive`, `-d/--column-delimiter`, `-c/--column-mode`, `--column-rainbow`, `--column-width`, `--completion`, `--config`, `--converter`, `--debug`, `--disable-column-cycle`, `--disable-mouse`, `-e/--exec`, `-X/--exit-write`, `-a/--exit-write-after`, `-b/--exit-write-before`, `--filter`, `-A/--follow-all`, `-f/--follow-mode`, `--follow-name`, `--follow-section`, `--force-screen`, `-H/--header`, `-Y/--header-column`, `-h/--help`, `--help-key`, `--hide-other-section`, `--hscroll-width`, `--incsearch`, `-j/--jump-target`, `-n/--line-number`, `--list-view-modes`, `--memory-limit`, `--memory-limit-file`, `-M/--multi-color`, `--non-match-filter`, `--notify-eof`, `--pattern`, `-p/--plain`, `-F/--quit-if-one-screen`, `-r/--raw`, `--regexp-search`, `--ruler`, `--section-delimiter`, `--section-header`, `--section-header-num`, `--section-start`, `--set-terminal-title`, `--skip-extract`, `--skip-lines`, `--smart-case-sensitive`, `--status-line`, `-x/--tab-width`, `-v/--version`, `-y/--vertical-header`, `-m/--view-mode`, `-T/--watch`, and `-w/--wrap`.

Every combination must remain compositional and safe. In particular support header+skip, header+column, line-number+wrap, line-number+column, ruler+line-number, pattern+filter, filter+quit-small, multicolor+column, converter+column, compressed+column+align, section+header+hide/follow, and all display flags together. Options irrelevant to redirected output still validate but leave its bytes unchanged.

## Spec 40

`-F/--quit-if-one-screen` checks whether content fits the available TUI viewport. If it fits, do not enter the alternate screen: write that first document exactly to stdout and exit 0. This includes empty, one-line, Unicode, NUL-containing, blank-line, and unterminated inputs. If it does not fit and a terminal is available, remain interactive; when stdout is captured, always use exact pass-through regardless of size.

The implementation must not hang, panic, leak terminal state, or depend on network access for any tested input. It must initialize and react to ordinary keys in under the test timeout, handle concurrent append/reload safely, and tolerate empty data, malformed escapes/regexes/configs, huge dimensions/values, and repeated toggles. All observable messages use stdout only for requested data/help/version/completion/export and stderr for startup/argument/config/open errors; transient interactive diagnostics belong on the status row or log document.
