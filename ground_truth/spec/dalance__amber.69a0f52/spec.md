# Clarified behavioral specification

## Spec 1

`executable` is the Amber replacement command, identified as `ambr` version `0.6.0`. It is a single-purpose command, not a command dispatcher: words such as `help`, `add`, `remove`, or `list` in positional positions are search keywords, not subcommands. `--version` and `-V` must write exactly `ambr 0.6.0` followed by a newline to standard output, write nothing to standard error, and exit successfully.

## Spec 2

The ordinary invocation grammar is:

```text
executable [FLAGS] [OPTIONS] <KEYWORD> <REPLACEMENT> [PATHS]...
```

`KEYWORD` and `REPLACEMENT` are required positional operands. Zero operands is an error naming both missing operands; one operand is an error naming `REPLACEMENT`. These parsing errors exit with status 1 and are written to standard error. For no operands, the first seven lines must be:

```text
error: The following required arguments were not provided:
    <KEYWORD>
    <REPLACEMENT>

USAGE:
    executable <KEYWORD> <REPLACEMENT> --bin-check-bytes <BYTES> --max-threads <NUM> --mmap-bytes <BYTES> --size-per-thread <BYTES>

```

Supplying two ordinary words is parsed as keyword and replacement and must not produce a missing-argument or unknown-subcommand diagnostic. Any remaining operands are paths; if no path is supplied, the current working directory is the one search root.

## Spec 3

`--help` and `-h` take precedence over normal argument validation, exit 0, and print help to standard output only. Help ends in a newline, contains no ANSI color escapes, and uses the following text and spacing. Replace `THREADS` at runtime by a decimal default worker count equal to the available logical CPU count.

```text
ambr 0.6.0

USAGE:
    executable [FLAGS] [OPTIONS] <KEYWORD> <REPLACEMENT> [PATHS]...

FLAGS:
        --key-from-file        Use file contents of KEYWORD as keyword for search
        --rep-from-file        Use file contents of REPLACEMENT as keyword for replacement
        --verbose              Verbose message
    -r, --regex                Enable regular expression search
        --column               Enable column output
        --row                  Enable row output
        --binary               Enable binary file search
        --statistics           Enable statistics output
        --skipped              Enable skipped file output
        --preserve-time        Enable timestamp preserve
        --no-interactive       Disable interactive replace
        --no-recursive         Disable recursive directory search
        --no-symlink           Disable symbolic link follow
        --no-color             Disable colored output
        --no-file              Disable filename output
        --no-skip-vcs          Disable vcs directory ( .hg/.git/.svn ) skip
        --no-skip-gitignore    Disable .gitignore skip
        --no-fixed-order       Disable output order guarantee
        --no-parent-ignore     Disable .*ignore file search at parent directories
        --tbm                  [Experimental] Enable TBM matcher
        --sse                  [Experimental] Enable SSE 4.2
    -h, --help                 Prints help information
    -V, --version              Prints version information

OPTIONS:
        --max-threads <NUM>          Number of max threads [default: THREADS]
        --size-per-thread <BYTES>    File size per one thread [default: 1048576]
        --bin-check-bytes <BYTES>    Read size for checking binary [default: 256]
        --mmap-bytes <BYTES>         [Experimental] Minimum size for using mmap [default: 1048576]

ARGS:
    <KEYWORD>        Keyword for search
    <REPLACEMENT>    Keyword for replace
    <PATHS>...       Search paths
```

In particular, the help has `FLAGS:`, `OPTIONS:`, and `ARGS:` sections and no `SUBCOMMANDS:` or `COMMANDS:` section.

## Spec 4

Unknown or malformed options are command-line errors with nonzero status and a standard-error diagnostic that quotes the offending token and includes `USAGE:`. The diagnostic form for an unknown option includes `Found argument '--name'` and wording that it was not expected or valid. Option names are case-sensitive: forms such as `--VERBOSE` and `--Verbose`, a single-dash long name such as `-verbose`, and unknown short options such as `-z` are invalid. The specific triple-dash spelling `---verbose` is accepted and has the same effect as `--verbose`; for example, it enables the `Skip (binary)` diagnostic. Bundled short flags are not supported; for example `-rv` is rejected and the error identifies `-v`.

The numeric options `--max-threads`, `--size-per-thread`, `--bin-check-bytes`, and `--mmap-bytes` accept an unsigned decimal integer, in either `--option value` or `--option=value` form. A missing, empty, nonnumeric, negative, or machine-integer-overflowing value is an error. Nonnumeric diagnostics include `Invalid value for '--option <METAVAR>'` and the underlying text `invalid digit found in string`; a negative token is treated as an unexpected flag-like argument; overflow mentions that the number is too large to fit. A non-repeatable option supplied twice is rejected with `was provided more than once`; `-r` and `--regex` count as two occurrences of the same option and are likewise rejected.

## Spec 5

The default behavior is literal, interactive, recursive, symlink-following, colored, filename-printing, fixed-order replacement. It skips VCS directories, obeys `.gitignore` files at or below an explicitly named search root, skips binary files, does not print statistics, and does not print skipped-file diagnostics. The documented flags switch the corresponding behaviors. The explicitly accepted positive controls `--skip-vcs`, `--skip-gitignore`, `--symlink`, and `--fixed-order` request their respective default behaviors. `--no-statistics` disables statistics, and `--no-preserve-time` explicitly requests the default timestamp-updating behavior; command-line controls override any loaded setting. A missing configuration file or malformed TOML must be ignored without a crash and defaults must still work. An invalid `~/.ambr.toml`, for example, must not itself produce visible output during an otherwise silent non-interactive replacement.

## Spec 6

`--key-from-file` means that the positional `KEYWORD` is a file path. A keyword source is decoded as UTF-8 even when `--binary` is active; when it is valid UTF-8, its complete contents are the search pattern. `--rep-from-file` similarly uses the complete contents of a valid-UTF-8 positional `REPLACEMENT` file as replacement data. The two flags may be used together. File content is not replaced by the source filename and is not trimmed; in particular, a valid-UTF-8 replacement file's trailing newlines are inserted verbatim. An empty replacement, whether supplied directly or obtained from a readable empty replacement source, is valid and deletes matches. A directory supplied as the replacement source is read as an empty replacement and succeeds; matches are therefore deleted. Invalid UTF-8 in a replacement source is also converted to an empty replacement rather than preserved or reported: with keyword bytes `00 01` and replacement-source bytes `ff 00` under `--binary`, the two matches in `A 00 01 B 00 01 C` are deleted, producing `ABC`.

Before matching, directly supplied keyword and replacement strings interpret these four escapes: `\n` becomes LF, `\t` becomes TAB, `\r` becomes CR, and `\\` becomes one backslash. Escapes may occur repeatedly among ordinary text, at the end, or in combinations, and order is preserved (`\r\n` and `\n\r` differ). Overlapping sequences are processed so that input bytes `5c 5c 6e` (two backslashes followed by `n`) become `5c 0a` (one backslash followed by LF), not the two bytes for literal `\n`. Thus a direct keyword containing `line1\nline2` can match an actual newline. Valid-UTF-8 keyword content read with `--key-from-file` is used verbatim, including NUL and other control bytes. Invalid UTF-8 is instead classified as an empty keyword source: a two-byte keyword source `00 ff` under `--binary` produces `Error: file is empty @ "path"`, exits 1, and leaves the target unchanged. By contrast, a one-byte NUL keyword source is valid and replaces NUL bytes under `--binary`.

## Spec 7

Without `--regex`/`-r`, search is an exact, case-sensitive byte-string/UTF-8 substring search. Regex metacharacters such as `.`, `*`, `+`, `$`, brackets, and parentheses have no special meaning. Matches need not be whole words. Find every left-to-right non-overlapping occurrence, including adjacent occurrences and occurrences at byte 0 or immediately before EOF. Replacement is performed against the original matches only: replacement text containing the keyword is not searched again. Files with no match are left unchanged. Original surrounding bytes, LF/CRLF or mixed line endings, empty lines, and the presence or absence of a final newline are preserved.

The default matcher, `--tbm`, and `--sse` must produce identical replacement results for the same literal input, including single-byte patterns, repeated-character patterns, adjacent dense matches, long patterns, Unicode patterns, and matches near large-file processing boundaries.

## Spec 8

With `--regex`/`-r`, use Rust-regex-style Unicode regular expressions with multiline mode enabled by default. Required constructs include `.`, escaped metacharacters, `\d`, `\w`, `\s`, character classes and negated/ranged classes, `^` and `$` as per-line anchors, `\b`, greedy and lazy quantifiers (`*`, `+`, `?`, `{n}`, `{n,m}` and their lazy forms), alternation, capturing and noncapturing groups, inline flags such as `(?i)`, and named groups written as either `(?P<name>...)` or `(?<name>...)`. Matching is case-sensitive unless the pattern enables another mode. Dot does not consume LF, while explicit `\n`, `\r`, and `\t` escapes match those controls. Matches may span lines when the expression explicitly does so.

Regex matches are also left-to-right and non-overlapping. Zero-length matches are supported. For example, empty regex on `hello world` produces `XhXeXlXlXoX XwXoXrXlXdX` when replaced with `X`, and `hello|` produces `X XwXoXrXlXdX` on the same input.

## Spec 9

Regex replacement expansion supports the whole match as `$0`, numbered groups as `$1`, `$2`, … and `${1}`, named groups as `$name` and `${name}`, and group numbers of at least two digits (including `$10` and `${11}`). Captures may be reordered, nested, mixed between named and numbered forms, and embedded between literal prefixes/suffixes. `$$` emits a literal dollar sign, so replacement `$$1` emits literal `$1`. Direct replacement escape processing from Spec 6 is applied as well, so `\n\t` inserts an LF and TAB.

Pattern backreferences such as `(word)\1` and look-around such as `(?=...)`/`(?<=...)` are unsupported. A regex that cannot be compiled—including unclosed groups/classes, invalid escapes, an initial repetition operator, unsupported look-around, or pattern backreferences—must not modify files or report matches. When the terminal backend is available, this condition is a silent successful no-match operation rather than a crash.

## Spec 10

`--no-interactive` replaces every match in every selected file without prompting. A successful run exits 0 when the normal terminal backend is available, whether matches exist or not. With neither statistics nor skip reporting enabled, it produces no visible normal output; a no-match run is silent and leaves every file unchanged. Rewrites may grow, shrink, or delete content and must handle a one-byte file, an entirely matching file, long lines, files larger than 2 MiB, at least 400,000 dense matches, at least 100 files, and directories nested at least 20 levels without truncation, missed matches, duplication, deadlock, or corruption.

## Spec 11

Each `PATHS` operand can be a regular file, directory, or symlink. Multiple operands are all processed. Directories are traversed recursively by default, including ordinary hidden files and hidden directories. `--no-recursive` processes only regular files immediately inside each named directory and never enters real or symlinked child directories. Search roots omitted from the command are equivalent to `.` in the current working directory. Empty files are harmless and remain empty. An unreadable file discovered among readable files is skipped without preventing accessible files from being processed.

With fixed ordering enabled by default, results are delivered in stable finder order, which sorts explicit path operands lexicographically by path rather than retaining command-line order. With operands supplied as `zeta`, `alpha`, `middle`, visible results are ordered `alpha`, `middle`, `zeta`. The accepted `--fixed-order` flag explicitly selects this default; `--no-fixed-order` disables it. Tuning concurrency must not change which files or matches are processed or their fixed ordering.

## Spec 12

At every traversal depth, directories named `.git`, `.hg`, `.svn`, or `.bzr` are VCS directories and are skipped by default. `--no-skip-vcs` disables that filter for all four names, independently of `.gitignore` handling. When VCS skipping and `.gitignore` skipping are independently enabled or disabled in any combination, each filter keeps its own meaning. `--no-recursive` still prevents descent even when both ignore filters are disabled.

## Spec 13

By default, `.gitignore` rules are applied during traversal. Implement ordinary Git-ignore matching sufficiently as follows:

- blank lines and comment lines are ignored;
- `*`, `?`, character ranges such as `[0-9]`, and globstar forms such as `/**/file` work;
- a basename pattern such as `*.log` or `dir7/` applies at descendant levels;
- a leading `/` anchors a pattern at the directory containing that ignore file;
- a slash-containing relative pattern such as `dir1/file` is relative to that ignore file rather than matching at arbitrary extra depth;
- a trailing `/` makes a pattern directory-only and causes its descendants to be skipped;
- later `!pattern` negation can re-include a previously ignored path;
- leading spaces or tabs in a non-comment pattern are literal, but a trailing ASCII space is stripped before matching; consequently the pattern `trailing.txt ` does not ignore a file whose name actually ends in a space.

When a nested `.gitignore` is present, inherited rules are not retained in that subtree; the nested file supplies the applicable rule set there. For example, with parent rules `*.tmp` and `!sub/` plus child rule `!keep.tmp`, both `sub/keep.tmp` and `sub/skip.tmp` are processed. An ignore file above an explicitly named directory search root is not consulted by default. `--no-parent-ignore` retains that behavior, while local and descendant ignore files still apply. Thus a parent `*.ban` does not filter an explicitly named child root, but a `.gitignore` inside that root still applies. `--no-skip-gitignore` disables all `.gitignore` filtering. Ignore files themselves may be traversed as ordinary files if their contents happen to match.

## Spec 14

Symbolic links to both files and directories are followed by default. The accepted `--symlink` flag explicitly selects this default. `--no-symlink` skips symbolic links discovered while traversing a directory, but it does not reject a symlink supplied explicitly as a `PATHS` operand: an explicit link to a file is followed, and an explicit link to a directory is entered. Real files independently present in a search tree remain eligible. Broken and circular links must not hang or abort traversal, and other files must continue to be processed. All discovered paths are canonicalized for replacement deduplication: if the same underlying file is named directly and/or through several symlinks, it is rewritten at most once. An explicitly supplied broken symlink produces the visible `Error: No such file or directory (os error 2)` diagnostic naming that link exactly twice. With the terminal backend available, a run whose only explicit target is that broken symlink exits 0 after reporting the errors. A broken link merely encountered during directory traversal may be skipped.

## Spec 15

Binary detection is enabled unless `--binary` is present. A file is binary if any byte in the first `min(file_size, bin_check_bytes)` bytes is in the inclusive range `0x00` through `0x08`. The default inspection length is 256 bytes, and `--bin-check-bytes N` changes it. TAB (`0x09`) alone is text. A binary file is left byte-for-byte unchanged by default. `--binary` bypasses this target-file filter and enables literal replacement while preserving arbitrary unrelated target bytes, including NUL and all byte values 0x00–0xff. It does not bypass the source-file UTF-8 decoding rules in Spec 6. Regex matching still requires valid UTF-8 target data even with `--binary`: a target containing `ff 00 61 62 31 32 63 64 fe` is left unchanged by regex `\d+` rather than changing its ASCII digits.

## Spec 16

Text handling must preserve valid UTF-8. Literal and regex patterns and replacements support two-, three-, and four-byte characters (for example accented Latin text, Japanese/Chinese/Korean, Cyrillic, Arabic, and emoji). A match begins and ends on character boundaries in valid multibyte text, and replacing adjacent ASCII must not damage surrounding multibyte characters. Position output, however, deliberately counts bytes as described in Spec 20. Keywords and replacements of at least 10,000 bytes and long runs of multibyte text are supported without truncation.

## Spec 17

`--max-threads N` controls the maximum matcher worker count; when statistics are requested it is displayed as exactly `N`. Values 1, 2, 4, 8, and 10,000 must be accepted when representable, and large values must not cause resource exhaustion on a small workload. `--size-per-thread N` changes the work-partition threshold. Work split at exact or near thresholds must neither miss nor duplicate matches, including matches near a partition boundary. `--mmap-bytes N` selects the size threshold for a memory-mapped implementation path; it is an optimization only and must not change output or file content. The defaults are those printed in help.

## Spec 18

Modified files normally receive a newer modification timestamp. The accepted `--no-preserve-time` flag explicitly selects this default. With `--preserve-time`, restore the original modification time exactly (allowing only filesystem precision effects) after a successful rewrite, including binary-file rewrites. The option does not prevent content replacement. Files with no matches and empty files are not rewritten. The file remains at the same pathname and replacements are committed as complete content, not as partial visible updates.

## Spec 19

Without `--no-interactive`, present one decision for each left-to-right non-overlapping match. The exact prompt is:

```text
Replace keyword? [Y]es/[n]o/[a]ll/[q]uit: 
```

Read responses as individual terminal characters, so a terminating newline is itself the next response if still applicable. `y`, `Y`, space, CR, or LF accepts the current replacement. `n` or `N` skips it and proceeds. `a` or `A` accepts the current and every remaining match without more prompts. `q` or `Q` exits cleanly with status 0 immediately, without applying the current match or examining later matches/files. Any other character leaves the same match pending and prints the prompt again. A sequence such as `n`, `y`, `a` therefore skips the first match, accepts the second, and accepts all remaining matches. Terminal settings must be restored after every exit path.

## Spec 20

Before each interactive prompt, print a two-line preview of the original complete line and that line with only the current match replaced. Filename output is on by default. Ignoring color, the first-line templates are:

```text
{path}: {line text}                    # default
{path}: {line-number}:{line text}      # --column
{path}: {row-value}:{line text}        # --row
{path}: {line-number}:{row-value}:{line text}  # both
    {line text}                        # --no-file only
{line-number}:  {line text}            # --no-file --column
{row-value}:<padding>{line text}        # --no-file --row
{line-number}:{row-value}:{line text}  # --no-file with both
```

Despite their historical names, `--column` is the 1-based line number. `--row` is a byte-position value. For the first line it equals the match's zero-based absolute byte offset. On later lines it equals `match_absolute_byte_offset - preceding_LF_absolute_byte_offset`; consequently a match at the first byte after an LF is displayed as 1, not 0. Multibyte characters contribute their UTF-8 byte width (for example `keyword` in `café has keyword` has row value 10). With `--no-file --row`, the header consisting of the decimal row value and colon is right-padded with spaces to a width of four characters, without truncation. Thus row values 0, 1, or 6 have two spaces after the colon (`6:  First keyword here`), values 10, 15, or 18 have one (`15: keyword twice keyword`), and value 100 has none.

The second preview line is indented and begins `-> ` followed by the proposed line; its arrow is padded according to the visible header width. With `--no-file` alone or with only one of `--column` and `--row`, there is one leading space before `->`. With `--no-file --column --row`, the number of leading spaces before `->` equals the number of decimal digits in the current row value. Representative required plain previews are:

```text
/tmp/test_column_only.txt: 1:First keyword here
                          -> First REPLACED here
/tmp/test_row_only.txt: 6:Short keyword
                       -> Short REPLACED
/tmp/match_at_start.txt: 1:0:match starts immediately
                          -> REPLACED starts immediately
1:0:match here
 -> REPLACED here
1:10:café has keyword
  -> café has REPLACED
2:1:keyword twice keyword
 -> REPLACED twice keyword
2:15:keyword twice keyword
  -> keyword twice REPLACED
```

Show each occurrence separately even when several matches share a line, with the appropriate original byte position. Do not print filenames when `--no-file` is active.

## Spec 21

Interactive terminal output is colored by default. Use SGR green (`32`) for the filename, cyan (`36`) for separators, arrow and prompt, yellow (`33`) for the matched/replacement span, and white (`37`) for surrounding line text. `--no-color` suppresses these SGR color selections in previews, diagnostics, skip messages, and statistics. On a real pseudo-terminal, emit the terminal cleanup sequence `ESC(B ESC[m` twice on shutdown, including after otherwise silent or `--no-color` runs. With standard output and standard error captured as separate non-TTY pipes under `TERM=xterm`, normal processing instead writes one `ESC(B ESC[m` sequence to each stream on shutdown. The standard-output sequence is present even when there is no other output; the standard-error sequence follows any file-source error, skip diagnostic, or statistics block. Thus “silent” processing elsewhere in this specification excludes these backend cleanup bytes. Help and version never use color.

## Spec 22

`--skipped` and `--verbose` make filtered-path information visible. Emit one diagnostic with the quoted path and these exact labels and alignment:

```text
Skip (binary)    : "path"
Skip (.gitignore): "path"
Skip (vcs file)  : "path"
```

In a non-TTY subprocess these informational diagnostics go to standard error; a PTY may combine them into its captured terminal stream. With color enabled they are cyan. Without either reporting flag, filtering is silent. Normal non-interactive replacements themselves stay silent.

## Spec 23

`--statistics` writes a statistics block to standard error after processing, including zero-match runs and regex runs. A line break immediately precedes the literal `Statistics` header, including with `--no-color` and when `--regex` is also present. With color enabled, SGR cyan (`ESC[36m`) precedes that line break. The block has this structure, where `N` is the configured maximum thread count, exactly one consecutive `MatchNN` line is printed per configured matcher worker (`Match00`, `Match01`, …), and each `busy`/`total` value is a seconds duration such as `0s / 0.000119431s`:

```text
Statistics
  Max threads: N

  Consumed time ( busy / total )
    Find     : busy / total
    Match00  : busy / total
    ...
    Sort     : busy / total
    Replace  : busy / total

```

The ordering, capitalization, indentation, blank lines, and padding shown above are required. For `--max-threads 1`, there is exactly `Match00`; for 4 there are `Match00` through `Match03`. Timings may vary but must be decimal-second strings in the shown form. `--no-color` makes the entire block free of SGR colors. Statistics do not alter replacement results.

## Spec 24

File-source errors occur before target modification, exit 1, and use these exact plain forms when color is disabled:

```text
Error: file not found @ "path"
Error: file is empty @ "path"
```

The first applies when either source operand file does not exist. An empty keyword source, including `/dev/null`, uses the second. A directory or an invalid-UTF-8 file passed to `--key-from-file` is also classified as an empty keyword source, produces the second diagnostic, and exits 1. A directly supplied empty literal keyword is not rejected: normal processing remains running for at least 30 seconds without output or target modification and must be externally terminated. With color, prefix a file-source error with red SGR (`31`). Target path I/O errors name the failing path and do not modify it. An explicitly missing target emits `Error: No such file or directory (os error 2) @ /path` exactly twice before terminal cleanup. An explicit target whose final path component is 300 bytes long produces that same `No such file or directory (os error 2)` diagnostic twice. Other usable targets continue where traversal permits. With the terminal backend available, a run whose only explicit target is missing or has a 300-byte final path component exits 0 after reporting the errors.

## Spec 25

Normal processing initializes a terminal-output backend even in `--no-interactive` mode. With `TERM=xterm`, processing works when output is either a PTY or captured pipes and successful replacement/no-match status is 0. If `TERM` is completely absent, initialization fails: exit 1, emit no normal output, and do not modify targets. With `TERM=dumb` and captured non-TTY output, non-interactive traversal of a directory still applies its replacements, but the process returns status 1 and emits no normal output; parsing, help, version, and the explicit file-source diagnostics above remain available. This environment distinction is part of the executable contract.
