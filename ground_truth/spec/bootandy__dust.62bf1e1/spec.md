# Clarified specification for `executable`

## Spec 1

`executable` is a single-purpose, directly executable command-line disk-usage analyser compatible with Dust 1.2.3. It has no subcommands. Every non-option argument is a filesystem path, including words such as `run`, `scan`, `show`, or `help`. It must work with absolute and relative paths, paths containing spaces or non-ASCII text, a single regular file, one directory, or arbitrarily many paths. With no supplied path it scans `.`. A successful information command or scan exits 0; command-line syntax errors exit 2; fatal scan/input/regular-expression errors exit 1 except for the specifically described missing-ignore-file failure.

Options may precede or follow paths. `--` ends option parsing, so a following `-name` is a path. GNU long `--option=value` syntax and space-separated values are accepted. Boolean short options may be clustered, for example `-pf` means `-p -f`. The executable must finish ordinary scans quickly and must not hang or overflow on deep trees, thousands of entries, or symlink cycles.

## Spec 2

`-V` and `--version` write exactly the following newline-terminated text to stdout, write nothing to stderr, and exit 0:

```text
Dust 1.2.3
```

When it is successfully parsed, `--help` exits 0, writes nothing to stderr, and writes exactly the following newline-terminated long help to stdout. Help does not bypass an earlier parser error: for example, `--not-a-real-option --help --depth` reports the unknown option, writes no stdout, and exits 2.

```text
Like du but more intuitive

Usage: executable [OPTIONS] [PATH]...

Arguments:
  [PATH]...
          Input files or directories

Options:
  -d, --depth <DEPTH>
          Depth to show

  -T, --threads <THREADS>
          Number of threads to use

      --config <FILE>
          Specify a config file to use

  -n, --number-of-lines <NUMBER>
          Number of lines of output to show. (Default is terminal_height - 10)

  -p, --full-paths
          Subdirectories will not have their path shortened

  -X, --ignore-directory <PATH>
          Exclude any file or directory with this path

  -I, --ignore-all-in-file <FILE>
          Exclude any file or directory with a regex matching that listed in this file, the file entries will be added to the ignore regexs provided by --invert_filter

  -L, --dereference-links
          dereference sym links - Treat sym links as directories and go into them

  -x, --limit-filesystem
          Only count the files and directories on the same filesystem as the supplied directory

  -s, --apparent-size
          Use file length instead of blocks

  -r, --reverse
          Print tree upside down (biggest highest)

  -c, --no-colors
          No colors will be printed (Useful for commands like: watch)

  -C, --force-colors
          Force colors print

  -b, --no-percent-bars
          No percent bars or percentages will be displayed

  -B, --bars-on-right
          percent bars moved to right side of screen

  -z, --min-size <MIN_SIZE>
          Minimum size file to include in output

  -R, --screen-reader
          For screen readers. Removes bars. Adds new column: depth level (May want to use -p too for full path)

      --skip-total
          No total row will be displayed

  -f, --filecount
          Directory 'size' is number of child files instead of disk size

  -i, --ignore-hidden
          Do not display hidden files

  -v, --invert-filter <REGEX>
          Exclude filepaths matching this regex. To ignore png files type: -v "\.png$"

  -e, --filter <REGEX>
          Only include filepaths matching this regex. For png files type: -e "\.png$"

  -t, --file-types
          show only these file types

  -w, --terminal-width <WIDTH>
          Specify width of output overriding the auto detection of terminal width

  -P, --no-progress
          Disable the progress indication

      --print-errors
          Print path with errors

  -D, --only-dir
          Only directories will be displayed

  -F, --only-file
          Only files will be displayed. (Finds your largest files)

  -o, --output-format <FORMAT>
          Changes output display size. si will print sizes in powers of 1000. b k m g t kb mb gb tb will print the whole tree in that size

          Possible values:
          - si: SI prefix (powers of 1000)
          - b:  byte (B)
          - k:  kibibyte (KiB)
          - m:  mebibyte (MiB)
          - g:  gibibyte (GiB)
          - t:  tebibyte (TiB)
          - kb: kilobyte (kB)
          - mb: megabyte (MB)
          - gb: gigabyte (GB)
          - tb: terabyte (TB)

  -S, --stack-size <STACK_SIZE>
          Specify memory to use as stack size - use if you see: 'fatal runtime error: stack overflow' (default low memory=1048576, high memory=1073741824)

  -j, --output-json
          Output the directory tree as json to the current directory

  -M, --mtime <MTIME>
          +/-n matches files modified more/less than n days ago , and n matches files modified exactly n days ago, days are rounded down.That is +n => (−∞, curr−(n+1)), n => [curr−(n+1), curr−n), and -n => (𝑐𝑢𝑟𝑟−𝑛, +∞)

  -A, --atime <ATIME>
          just like -mtime, but based on file access time

  -y, --ctime <CTIME>
          just like -mtime, but based on file change time

      --files0-from <FILES0_FROM>
          Read NUL-terminated paths from FILE (use `-` for stdin)

      --files-from <FILES_FROM>
          Read newline-terminated paths from FILE (use `-` for stdin)

      --collapse <COLLAPSE>
          Keep these directories collapsed

  -m, --filetime <FILETIME>
          Directory 'size' is max filetime of child files instead of disk size. while a/c/m for last accessed/changed/modified time

          Possible values:
          - a: last accessed time
          - c: last changed time
          - m: last modified time

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

## Spec 3

When it is successfully parsed, `-h` has the same streams, status, first two lines, usage line, arguments, and option inventory as `--help`, but writes this exact compact, newline-terminated form. Like long help, it does not override an earlier parser error: `--not-a-real-option -h --depth` exits 2 with no stdout.

```text
Like du but more intuitive

Usage: executable [OPTIONS] [PATH]...

Arguments:
  [PATH]...  Input files or directories

Options:
  -d, --depth <DEPTH>              Depth to show
  -T, --threads <THREADS>          Number of threads to use
      --config <FILE>              Specify a config file to use
  -n, --number-of-lines <NUMBER>   Number of lines of output to show. (Default is terminal_height - 10)
  -p, --full-paths                 Subdirectories will not have their path shortened
  -X, --ignore-directory <PATH>    Exclude any file or directory with this path
  -I, --ignore-all-in-file <FILE>  Exclude any file or directory with a regex matching that listed in this file, the file entries will be added to the ignore regexs provided by --invert_filter
  -L, --dereference-links          dereference sym links - Treat sym links as directories and go into them
  -x, --limit-filesystem           Only count the files and directories on the same filesystem as the supplied directory
  -s, --apparent-size              Use file length instead of blocks
  -r, --reverse                    Print tree upside down (biggest highest)
  -c, --no-colors                  No colors will be printed (Useful for commands like: watch)
  -C, --force-colors               Force colors print
  -b, --no-percent-bars            No percent bars or percentages will be displayed
  -B, --bars-on-right              percent bars moved to right side of screen
  -z, --min-size <MIN_SIZE>        Minimum size file to include in output
  -R, --screen-reader              For screen readers. Removes bars. Adds new column: depth level (May want to use -p too for full path)
      --skip-total                 No total row will be displayed
  -f, --filecount                  Directory 'size' is number of child files instead of disk size
  -i, --ignore-hidden              Do not display hidden files
  -v, --invert-filter <REGEX>      Exclude filepaths matching this regex. To ignore png files type: -v "\.png$"
  -e, --filter <REGEX>             Only include filepaths matching this regex. For png files type: -e "\.png$"
  -t, --file-types                 show only these file types
  -w, --terminal-width <WIDTH>     Specify width of output overriding the auto detection of terminal width
  -P, --no-progress                Disable the progress indication
      --print-errors               Print path with errors
  -D, --only-dir                   Only directories will be displayed
  -F, --only-file                  Only files will be displayed. (Finds your largest files)
  -o, --output-format <FORMAT>     Changes output display size. si will print sizes in powers of 1000. b k m g t kb mb gb tb will print the whole tree in that size [possible values: si, b, k, m, g, t, kb, mb, gb, tb]
  -S, --stack-size <STACK_SIZE>    Specify memory to use as stack size - use if you see: 'fatal runtime error: stack overflow' (default low memory=1048576, high memory=1073741824)
  -j, --output-json                Output the directory tree as json to the current directory
  -M, --mtime <MTIME>              +/-n matches files modified more/less than n days ago , and n matches files modified exactly n days ago, days are rounded down.That is +n => (−∞, curr−(n+1)), n => [curr−(n+1), curr−n), and -n => (𝑐𝑢𝑟𝑟−𝑛, +∞)
  -A, --atime <ATIME>              just like -mtime, but based on file access time
  -y, --ctime <CTIME>              just like -mtime, but based on file change time
      --files0-from <FILES0_FROM>  Read NUL-terminated paths from FILE (use `-` for stdin)
      --files-from <FILES_FROM>    Read newline-terminated paths from FILE (use `-` for stdin)
      --collapse <COLLAPSE>        Keep these directories collapsed
  -m, --filetime <FILETIME>        Directory 'size' is max filetime of child files instead of disk size. while a/c/m for last accessed/changed/modified time [possible values: a, c, m]
  -h, --help                       Print help (see more with '--help')
  -V, --version                    Print version
```

## Spec 4

Recognize every short/long option pair shown in help. The following take one value: `-d/--depth`, `-T/--threads`, `--config`, `-n/--number-of-lines`, `-X/--ignore-directory`, `-I/--ignore-all-in-file`, `-z/--min-size`, `-v/--invert-filter`, `-e/--filter`, `-w/--terminal-width`, `-o/--output-format`, `-S/--stack-size`, `-M/--mtime`, `-A/--atime`, `-y/--ctime`, `--files0-from`, `--files-from`, `--collapse`, and `-m/--filetime`. All other documented options are booleans.

`-X`, `-e`, `-v`, and `--collapse` are repeatable and accumulate. Other scalar and boolean options are non-repeatable: spelling aliases count as the same option, and a duplicate is an exit-2 error containing `cannot be used multiple times`. Integer-option parsing accepts unsigned decimal integers (including zero and the maximum in-range value) with an optional leading `+`; for example, `-w +2` is parsed as width 2 rather than rejected as a non-digit. Other non-digits and overflow are exit-2 parser errors. The later runtime failure for a maximum-value time filter is specified in Spec 16. Output-format values are the choices `si,b,k,m,g,t,kb,mb,gb,tb`, matched case-insensitively: for example, `-o SI` is accepted and is equivalent to `-o si`. Filetime values are exactly lowercase `a`, `c`, or `m`.

## Spec 5

Parser failures produce no stdout, write a clap-style diagnostic to stderr, end with `For more information, try '--help'.`, and exit 2. Unknown options report `error: unexpected argument '<arg>' found` and include `tip: to pass '<arg>' as a value, use '-- <arg>'`. A missing value reports `error: a value is required for '--canonical-name <PLACEHOLDER>' but none was supplied`. A bad integer reports, for example, exactly:

```text
error: invalid value 'invalid' for '--depth <DEPTH>': invalid digit found in string

For more information, try '--help'.
```

A bad output format reports the invalid value and a `[possible values: si, b, k, m, g, t, kb, mb, gb, tb]` line. These pairs are mutually exclusive and report that the first canonical argument `cannot be used with` the second: `only-dir/only-file`; `filter/invert-filter`; `file-types/filter`; `file-types/invert-filter`; `file-types/depth`; `file-types/only-dir`; and `files-from/files0-from`. Their diagnostic includes a reduced usage line, then the standard help hint.

## Spec 6

Resolve explicit roots without inventing subcommands. Remove exact duplicate roots and remove a root that is already contained beneath another supplied directory root, preventing double counting. One root is displayed as that root. Two or more independent roots are children of a synthetic root named `(total)`, whose metric is their aggregate. Input supplied through either files-list option is likewise represented under `(total)` when it denotes separate roots. Root resolution is all-or-nothing: if any explicit or listed root is missing, do not render the valid roots; report the missing roots and exit 1 as specified in Spec 23.

The ordinary displayed label is the basename, with the supplied root rendered as `.` when appropriate. When unrelated supplied roots share a basename, distinguish each by appending its immediate parent basename in parentheses rather than by prepending parent components. Thus relative roots `left/same` and `right/same` have JSON names `left/same(left)` and `right/same(right)`; they are not merged. `-p/--full-paths` renders each complete path (absolute when the supplied path is absolute), subject only to terminal-width truncation and the same collision suffix. Paths and JSON names must preserve Unicode and spaces correctly.

## Spec 7

Traverse every directory recursively for accounting, even when display depth or line limits hide descendants. In normal size mode a regular file's value on Unix is its allocated byte count (`st_blocks * 512`), so a tiny nonempty file normally occupies `4096` bytes on the test filesystem. Except for the include-filter behavior in Spec 9, a directory's normal value is its own allocated byte count plus the values of all included descendant files and directories. On the test filesystem this adds one `4096`-byte directory allocation: a directory containing allocated `4096`- and `8192`-byte files is `16384` bytes, and a lone empty directory is retained as `4096` bytes (`4.0K`). A single file root is retained and uses that file's allocation.

With `-s/--apparent-size`, use metadata length (`st_size`) rather than allocated blocks. In this mode include the metadata length of directories as well as files when forming directory totals, matching examples such as a 2-byte file in a directory whose resulting total is 24 bytes. Sparse files therefore differ between normal and apparent-size modes.

## Spec 8

Without `-L`, never follow symbolic links. Retain each symlink, including broken links, as a zero-value leaf and do not issue an error for a broken link discovered this way. With `-L`, dereference links to files and directories and recurse into linked directories, including links outside the initial root. A broken dereferenced link is reported as `No such file or directory: <path>` on stderr; when another valid entry remains, the scan still renders it and exits 0.

This release does not stop directory-link cycles by filesystem identity. It expands a self-link or mutual directory-link cycle by pathname until link/path resolution fails, then aggregates the resulting long paths into the same `No such file or directory:` warning. It nevertheless completes promptly for the observed self-link, mutual-cycle, and 30-link-chain cases. A dereferenced symlink to a regular file uses the target's allocated-size identity and value, but in `--filecount` it remains a zero-count symlink entry. It can therefore claim the target inode and suppress another pathname for that inode while contributing zero files; for example, `foreign -> /proc/version` is a displayed zero-count child under `-L -f`, and `-L -x -f` removes that foreign-device child.

Deduplicate allocated-size/filecount entries globally by device and inode, including hard links and targets reached by multiple roots, and display the lexicographically earliest full pathname as the representative. Consequently `notes.txt` represents a same-directory hard link named `the_link`; with `-L`, `link.txt` represents the same target inode as `target.txt`, and `link1` represents a chain named `link1` through `link20`. In apparent-size mode hard-linked directory entries are counted separately by pathname. Do not deduplicate unrelated same-named items. `-x/--limit-filesystem` does not descend to an entry whose device differs from its root's device, but includes all same-filesystem entries. `-T/--threads N` controls concurrency only: `0` means automatic/default, and every accepted thread count produces the same tree, values, and deterministic ordering. `-S/--stack-size N` adjusts worker stack capacity without changing results.

## Spec 9

`-e/--filter REGEX` includes regular files whose full path matches at least one supplied case-sensitive regular expression. `-v/--invert-filter REGEX` excludes a file whose full path matches at least one supplied expression. It does not apply the expression to directory paths: a pattern matching `/dropdir$` does not exclude `dropdir` or prune its descendants. The supplied scan root itself is always retained. For example, `-f -v e` on a root named `test_dir2` whose only child is named `file` renders a zero-count `test_dir2` row because the child file matches. Retain ancestor directories needed to connect matching files, with totals recomputed from the filtered set. In normal allocated-size mode, an active include filter omits every retained directory's own allocation from these recomputed totals: a root containing one matching `4096`-byte file has value `4096` (`4.0K`), not `8192`, and a retained ancestor directory likewise has only the sum of its matching descendant files. This omission is specific to `-e`; invert filtering retains the normal directory allocations. Thus either kind of expression matching no retained file may still leave a zero-valued root.

Use real regular-expression semantics, including anchors, escaping, alternation, and groups. An invalid command-line expression is detected before traversal, writes a diagnostic containing `Ignoring bad value for regex`, `regex parse error`, and the engine reason, and exits 1. The reason for `(?P<unclosed` is exactly `error: unclosed capture group name`; an unterminated character class reports `unclosed character class`. Every line of every `-I/--ignore-all-in-file FILE` is an additional invert-filter expression, including an empty line. Consequently an empty line is an empty regex and matches every file path; in a root containing `keep.txt`, `drop.log`, and `secret.txt`, a pattern file ending in an additional blank line excludes all three and leaves the retained root at zero. Nonempty valid lines all accumulate; an invalid line is silently skipped while other valid lines remain effective. `-I` patterns and `-v` patterns combine by OR.

## Spec 10

Each `-X/--ignore-directory PATH` excludes an entry and its subtree when either (a) its complete path equals an absolute exclusion, or (b) one complete path component exactly equals a relative exclusion. Do not use substring matching: excluding `data` does not exclude `data_extra` or `subdata`. Multiple exclusions are ORed and names containing punctuation are literal paths, not regexes.

Hidden entries are included by default. `-i/--ignore-hidden` excludes every entry whose basename begins `.`, and does not descend into hidden directories. Exclusions, hidden filtering, include/invert regexes, and time filters all affect both displayed descendants and ancestor totals.

## Spec 11

`-z/--min-size SIZE` hides nodes whose computed metric is less than or equal to the threshold while preserving the supplied root or an ancestor needed for retained descendants. A node must be strictly greater than the threshold to pass: an apparent-size file of exactly 1024 bytes is hidden by each of `-z 1024`, `-z 1K`, and `-z 1KiB`. Parse a bare integer as bytes. A suffix `K` or `M` means the corresponding binary power (1024 or 1024²); explicit `KB`/`MB` forms are decimal powers, and `KiB`/`MiB` forms are binary powers. Suffix matching is case-insensitive. In `--filetime` mode the filter remains active and compares the raw epoch-second metric against the threshold; for example, `-m m -z 999999999999` hides a normally visible current-time child while retaining the root.

`-D/--only-dir` displays directories only but still scans/counts their files. `-F/--only-file` displays every included descendant file as a flat set directly beneath the retained root and hides directory rows. `-d/--depth N` treats each supplied filesystem root as depth 0 and displays its nodes only through depth N: depth 0 is only that supplied root; depth 1 includes its immediate children. A synthetic `(total)` is an additional aggregate row outside this depth count, so `-d 0 one two` displays `one`, `two`, and `(total)`. Hidden descendants still contribute to the displayed boundary directory's aggregate. These display selectors also apply to JSON.

## Spec 12

Order nodes deterministically by metric and then by full name. Internally, children are greatest-first (larger value first, and for equal values lexicographically later name first). JSON exposes that order. The normal textual path tree is a bottom-up/postorder rendering, so visible siblings appear smallest/lexicographically earliest first and the root is last. File-type text has the `(others)` exception specified in Spec 15. `-r/--reverse` changes text to top-down/preorder: root first, then greatest-first descendants, and uses the upside-down connectors described below.

`-n/--number-of-lines N` selects the N most significant non-root entries globally while retaining the directory context required to connect them; the root/total row is additional. Consequently context can make the physical output slightly longer than N. The default N is terminal height minus 10. When terminal height is unavailable, the fallback is exactly 20 non-root selections. Selection is deterministic, and traversal/accounting is never truncated by this option.

## Spec 13

The default adaptive formatter is binary: use `B`, `K`, `M`, `G`, `T` at powers of 1024. Values below 10 units have one decimal (`4096` is `4.0K`); values at least 10 units are rounded to an integer (`12288` is `12K`); zero is `0B`. `-o si` is adaptive powers-of-1000 (`4096` is `4.1K`). Fixed formats divide by their named factor using integer division, truncate the fractional part, and append only `B/K/M/G/T`: `b` is raw bytes plus `B`; `k,m,g,t` use 1024-based factors; `kb,mb,gb,tb` use 1000-based factors. Thus 1510 bytes is `1K` in both `k` and `kb`; 1,510,000, 1,510,000,000, and 1,510,000,000,000 bytes are respectively `1M`, `1G`, and `1T` in both the corresponding binary and decimal fixed formats. For example 4096 is `4096B`, `4K` in `k`, and `4K` in `kb`.

Right-align the metric column to the widest formatted metric in the selected output. Percentages and bars always use the unrounded metric divided by the top-level total, independent of display unit.

## Spec 14

`-f/--filecount` changes the metric to file count. Every included regular file reached beneath a directory is 1, every directory is the recursive sum of those files, empty directories are 0, and directories themselves do not add 1. A supplied root that is itself a regular file is retained with value 0 rather than 1. This also applies to exact file roots read from either files-list form: two listed files appear beneath `(total)` with a total of 0, while a listed directory containing one file plus a listed loose file has total 1. The synthetic total sums these root values. Values are displayed as bare decimal integers, without a unit. Percentages remain relative to the total file count. It combines with only-dir, JSON, depth, and file-types. In JSON, the root of a directory containing six files has size string `"6"`, each descendant file has `"1"`, and leaves have empty children arrays.

## Spec 15

`-t/--file-types` replaces the path tree with a one-level aggregation. Group every included regular file by its final extension including the leading dot (for example `.txt`); use `(no extension)` when there is none. The root is named `(total)`. A group's normal/apparent/count metric is the sum of its members. Preserve this release's filetime compatibility quirk: an ordinary extension group's raw epoch-second values are also summed and the sum is then formatted as a timestamp. Thus two `.txt` mtimes `2023-01-01T12:00:00` and `2023-02-01T13:00:00` produce the group timestamp `2076-02-02T01:00:00`. The `(total)` row uses the maximum of these already-summed type-group values, so a lone `.txt` group gives the same `2076-02-02T01:00:00` total.

The type children use the normal metric/name ordering unless an `(others)` group is created. With `-n N`, output N group rows plus the total. If there are more groups than fit, retain the N-1 greatest groups and combine all remaining groups into `(others)` using sum, or the maximum already-aggregated group value for filetime. In text, `(others)` is always the first group row—even when ordinary bottom-up ordering would put its larger value last—followed by the retained groups in their normal smallest/lexicographically earliest-first order. For equal-size types the retention rule keeps lexicographically later extensions. Text never displays individual filenames in this mode; JSON has `(total)` with group objects as children.

## Spec 16

`-M/--mtime`, `-A/--atime`, and `-y/--ctime` filter using modification, access, and inode-change time respectively. Compute `age` by truncating `now - timestamp` to a whole number of elapsed seconds, and let `day = 86400` seconds. For nonnegative integer `n`: `+n` selects ages greater than `(n+1)*day`; `-n` selects ages less than `n*day`; bare `n` selects ages in `(n*day, (n+1)*day]`. Thus a timestamp set exactly two days before an instant captured less than one second before process start still has truncated age `172800` and matches bare `1`. These are the timestamp intervals printed in help after this whole-second truncation. Combine multiple time filters with AND and apply them to files, then retain/recompute their ancestors. This release does not safely convert the maximum unsigned value: `-M +18446744073709551615` produces no stdout, writes a Rust panic containing `panicked at src/config.rs:<error location>:` followed by `invalid data format`, and exits 101.

`-m/--filetime a|c|m` changes the displayed/sorted metric to the selected timestamp. In text, format every row in local time as `YYYY-MM-DDTHH:MM:SS` with no zone suffix. An ordinary path directory uses the maximum relevant timestamp among itself and its retained descendants. File types instead use the sum/max compatibility rule in Spec 15. JSON has the formatting exception in Spec 21. This mode may be combined with file types. A thread count or output renderer must not change the raw timestamp choice.

## Spec 17

Read TOML configuration as defaults. `--config FILE` selects an explicit file. Without that option, this executable first reads `$HOME/.dust.toml` when it exists and otherwise reads `$HOME/.config/dust/config.toml` when that exists. A custom `$XDG_CONFIG_HOME/dust/config.toml` is not used when it is outside that HOME-relative location. Recognized keys are `depth`, `threads`, `number-of-lines`, `display-full-paths`, `display-apparent-size`, `reverse`, `no-colors`, `force-colors`, `no-bars`, `bars-on-right`, `min-size`, `screen-reader`, `skip-total`, `ignore-hidden`, `only-dir`, `only-file`, `output-format`, and `stack-size`. In particular, the keys `filecount`, `ignore-directories`, `filter`, `invert-filter`, `collapse`, `ignore-all-in-files`, `dereference-links`, `limit-filesystem`, `file-types`, `terminal-width`, `no-progress`, and `filetime` are ignored rather than supplying their corresponding CLI options; other recognized keys in the same file still apply. This means, for example, that configured `number-of-lines = 1` is applied while configured `file-types = true`, `invert-filter = ["hide"]`, and `terminal-width = 60` are not, and configured screen-reader/skip-total settings can apply while the ignored `no-progress = true` still permits the completion clear sequence `"\r \r"` on stderr.

When both configuration booleans `force-colors = true` and `no-colors = true` are present, `force-colors` takes precedence regardless of their order in the file. The scan emits ANSI color sequences even when `NO_COLOR` is present; its output begins with the red foreground sequence `ESC[31m` in the observed one-file case.

An empty or comment-only file whose `.toml` extension identifies its format is valid and silent. For an extensionless explicit file containing either nothing or only a TOML comment, format detection instead fails: scanning still exits 0 with defaults, and stderr is exactly `Ignoring invalid config file '<FILE>': don't know how to parse file\n`, with the selected path substituted for `<FILE>`. CLI scalar values override configured scalar values. A CLI boolean occurrence enables the option and is idempotent with a configured true value: for example config `reverse=true` plus `-r` remains reverse rather than toggling back to normal. A missing explicit config is nonfatal, exits 0 after scanning with defaults, and warns on stderr with text containing `doesn't exists`. Malformed TOML is ignored wholesale, scanning succeeds with defaults, and stderr contains `Ignoring invalid config file`. Options already parsed from the CLI still apply; for example `-f` applied to a top-level regular-file root renders its specified count of `0`.

## Spec 18

Ordinary output is UTF-8, one row per selected node, newline terminated. In normal bottom-up mode use two display cells of indentation per depth, vertical ancestor strokes `│`, leaf/sibling joints `┌──` or `├──`, and a directory joint containing `─┴` when its displayed descendants precede it. A single empty root uses `┌──`; a populated root ends with `┌─┴`. In reverse mode use `└─┬` for a populated root, `├─┬`/`└─┬` for expanded directories, and `├──`/`└──` for leaves. Align the tree/name column by Unicode display width, not UTF-8 byte count.

For example, on the test filesystem a normal two-file directory with `4.0K` and `8.0K` file allocations is `16K` after including its own `4.0K` directory allocation. Without colors it has the structural form (bar widths vary with names/terminal):

```text
4.0K   ┌── aaa.txt  │...│  25%
8.0K   ├── bbb.txt  │...│  50%
 16K ┌─┴ root       │...│ 100%
```

With `-b/--no-percent-bars`, omit the entire bar and percentage columns (including their `│` delimiters), retain sizes and tree connectors, and emit no trailing padding; a row is effectively `<right-aligned metric> <tree-and-name>`. `--skip-total` removes the supplied single-root row or synthetic `(total)` row while retaining descendants and adjusting connector indentation.

## Spec 19

Unless `-b`, screen-reader mode, or filetime mode is active, render a proportional bar after the padded tree/name column as `│<cells>│ <percent>%`; percent is nearest whole percent, width 3, with 100 for a nonzero root and 0 for a zero total. At terminal width 80 the last `%` occupies display column 80. Reserve one trailing space inside the bar and fill `ceil(ratio * (interior_width-1))` cells with `█`, with at least one `█` even at zero. Every remaining cell is an ordinary space: descendant bars do not emit `░`, `▒`, or `▓` ancestry shading. `-B/--bars-on-right` right-aligns the filled cells within the interior; the root still fills from the left.

`-w/--terminal-width WIDTH` overrides terminal detection and drives name truncation and, when they fit, bar length; a width of 60 with short names produces 60-display-column rows and very wide values (for example 1000) produce correspondingly long bars. Truncate overlong labels with `..`. If the widest tree/name column leaves insufficient room for a bar, omit the bar and percentage from every row. In that fallback the truncated long row can occupy the requested width, while shorter rows are not padded to it; with a very long child at width 40, the child is truncated with `..` but the short root row ends immediately after its name. Width 5 must fail nonzero with `Not enough terminal width`; width 10 on a tree must fail nonzero with `Terminal width not wide enough to draw directory tree`.

Color is automatically disabled when stdout is not a terminal or the `NO_COLOR` environment variable is present. `-c` disables all ANSI sequences. `-C` forces ANSI color even through a pipe and includes reset sequences; its palette includes the red foreground sequence `ESC[31m` (`\x1b[31m`) as well as `ESC[0m` resets. Color never changes plain-text content or column widths.

## Spec 20

`-R/--screen-reader` removes every box-drawing and block/shading symbol. It writes four aligned whitespace-separated columns in this order: label, decimal depth, formatted metric, percentage. Example:

```text
file.txt             1 4.0K  50%
root                 0 8.0K 100%
```

Labels are padded to the widest Unicode display width and the metric/percentage columns remain aligned. `-p` supplies full labels in this mode. Normal ordering, reverse choice, filtering, and skip-total still apply.

Each `--collapse PATH` keeps the matching directory row and its fully computed aggregate but removes all of that row's displayed descendants. Match either its exact full path or a basename/component supplied as a relative collapse value. Multiple values accumulate. Unmatched directories remain expanded. In JSON a collapsed directory has an empty `children` array.

## Spec 21

`-j/--output-json` writes exactly one valid JSON value to stdout (surrounding whitespace is harmless) and no tree text. Every node is an object with exactly these keys and types:

```json
{"size":"4.0K","name":"/path/to/node","children":[]}
```

`size` uses the selected size/count formatter and is always a string; `name` is the complete constructed path for path nodes (not merely the basename), preserving whether a relative input produced a relative tree and including the collision suffix from Spec 6; `children` is an array. In filetime mode, JSON passes the raw epoch-second metric through the selected size formatter rather than the timestamp formatter: for example epoch values near 2024 display adaptively as `1.6G`, and the summed two-file type value from Spec 15 displays as `3.1G`. Regular files have no children. Directory nesting is preserved, children are greatest-first by metric/name, and all text is correctly JSON-escaped. A directory with two files has one root object and two file children; an empty directory is still an object with `[]` and its normal allocated size includes the directory allocation. Depth, collapse, filtering, filecount, file-types, min-size, and only-dir apply as in text. Only-file flattens all descendant files into the retained root's `children` array.

Output formats apply inside JSON: an allocated 4096-byte file is `"4096B"` for `-o b`, `"4K"` for `-o kb`, `"4.1K"` for `-o si`, and `"4.0K"` by default. In file-types JSON the root name is `(total)` and children are extensions/`(no extension)`/`(others)` groups.

## Spec 22

`--files-from FILE` reads newline-delimited paths; `--files0-from FILE` reads NUL-delimited paths, allowing newlines and spaces in a NUL-delimited pathname. A value of `-` reads the corresponding encoding from stdin. Ignore a final empty record caused by a terminating delimiter. Scan directories named in a list recursively and scan only the exact files named; do not infer their common parent. Both `--flag FILE` and `--flag=FILE` work.

If stdin or a readable list contains no paths, behavior differs intentionally: an empty named list produces a zero-valued `(total)` row, while empty stdin writes `No files provided, defaulting to current directory` to stderr and scans `.`. If the list source file itself cannot be read, write `Failed to read file:` plus the operating-system reason, fall back to `.`, and exit 0. A missing entry within an otherwise useful list is reported like any missing root and aborts the whole root set: valid listed entries are not rendered and the status is 1.

## Spec 23

Aggregate nonexistent explicit roots into one stderr line:

```text
No such file or directory: path1, path2
```

Every missing path, including punctuation and Unicode, appears once; order may follow traversal rather than argument order. If any root is invalid, stdout is empty and status is 1 even when another root is a valid nonempty file or directory. A path after `--` and a path read from a list follow this all-or-nothing runtime rule. A lone empty directory is normally rendered successfully with its allocated directory value. Discovered broken symlinks without dereference are not missing-root errors; a broken link discovered under `-L` is warned about as described in Spec 8 and does not abort a tree that has valid content.

An unreadable directory is skipped without crashing. Print at most one `Did not have permissions` warning; without `--print-errors` it need not name every path, while with the flag it includes the offending path. A missing `-I/--ignore-all-in-file` file is a hard failure and must include the Rust-compatible panic substrings `panicked at src/main.rs:`, ``called `Result::unwrap()` on an `Err` value``, and `kind: NotFound, message: "No such file or directory"` on stderr.

## Spec 24

Unless `-P/--no-progress` is active, an actual scan emits a transient indexing/progress indication to stderr, even when stdout is redirected; it must never contaminate stdout or JSON. On completion, clear it with the exact byte sequence carriage-return, one ASCII space, carriage-return (`"\r \r"`). Thus a completed warning-free noninteractive scan may have stderr exactly `"\r \r"`, and a missing-path diagnostic begins `"\r \rNo such file or directory: ...\n"`. `-P` suppresses the progress indication and this clearing sequence completely. Help, version, and parser errors never emit progress. Runtime warnings follow the clearing sequence and remain readable.

All results must be deterministic across thread counts, terminate within five seconds for roughly 100 directories and 1000 small files, support very deep nesting without recursion failure, and correctly preserve filenames containing spaces, quotes, apostrophes, dashes, dots, emoji, CJK, Arabic, Greek, and other Unicode. Display alignment uses terminal character width; JSON uses standard escaping. Empty files, empty directories, many equal-size files, very large allocated files, narrow/wide terminals, duplicate names in different parents, and multiple root arguments must all be handled without data loss or crashes.
