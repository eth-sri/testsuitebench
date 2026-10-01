# Specification for `executable`

The required artifact is one directly runnable file named `executable`. It is a Unix command-line disk-usage analyzer compatible with the interface described below. All paths and sizes used in examples are illustrative unless an exact rendering is explicitly stated. The process must work from arbitrary current working directories and must not depend on repository source, helper programs, or data outside this specification.

## Spec 1

`executable` is a UTF-8-capable command-line program. It writes ordinary reports and generated completion scripts to standard output, argument diagnostics and traversal statistics to standard error, and exits promptly (ordinary small invocations should finish well within five seconds). Every nonempty textual output ends in a newline unless the interactive terminal owns the screen. Input is filesystem paths, not data from standard input; ordinary operation must not require or interpret stdin.

The three meaningful exit statuses are:

- `0` after help, version, completion generation, or a scan with no I/O failures;
- `1` if command parsing succeeded but setup, terminal initialization, logging, or at least one filesystem operation failed; and
- `2` for command-line syntax or value errors.

An I/O failure for one root must not prevent the other roots from being measured and printed.

## Spec 2

The top-level syntax is conceptually:

```text
dua [GLOBAL-FLAGS] [GLOBAL-OPTIONS] [SUBCOMMAND] [INPUT]...
```

The recognized subcommands are `interactive` (alias `i`), `aggregate` (alias `a`), `completions`, and `help`. With no explicit subcommand, all positional tokens are input paths and the program performs aggregate mode. Thus an unknown bare word such as `does-not-exist` is a path, not an unknown subcommand. `help` alone prints long top-level help; `help aggregate`, `help interactive`, and `help completions` print the corresponding subcommand help.

Top-level options, which occur before an explicit subcommand, are:

```text
-t, --threads <THREADS>          unsigned integer, default 0
-f, --format <FORMAT>            metric|binary|bytes|gb|gib|mb|mib, default binary
-A, --apparent-size              boolean
-l, --count-hard-links           boolean
-x, --stay-on-filesystem         boolean
-i, --ignore-dirs <PATH>         repeatable; defaults are /proc,/dev,/sys,/run
    --log-file <PATH>             append debug logging to this file
-h, --help
-V, --version
```

`aggregate` accepts `--stats`, `--no-sort`, `--no-total`, `-h`, `--help`, followed by zero or more paths. `interactive` accepts `-e`/`--no-entry-check`, `-h`, `--help`, followed by zero or more paths. `completions` accepts exactly one shell value and its help option.

## Spec 3

Command parsing is case-sensitive for option names and subcommand names. The values of `--format` are ASCII-case-insensitive: for example, `bytes`, `BYTES`, `GB`, `GiB`, `MB`, and `MiB` are accepted and select their corresponding canonical formats. Completion shell values remain case-sensitive. Both `--option value` and `--option=value` forms are accepted for global value options; the short forms accept a separate value. `--` ends option recognition, so every later token is a path even when it begins with `-`. A path containing whitespace, quotes, Unicode, `$`, `#`, `@`, or other shell-special characters is kept as the single argument delivered by the operating system and printed without corruption.

Global options after an explicit subcommand are rejected with status 2 (for example, `aggregate --format bytes file` and `aggregate --threads 2`). Likewise, subcommand-only options before the subcommand are rejected. A top-level `--help` or `--version` takes precedence and succeeds even if later options would otherwise be invalid; subcommand help similarly takes precedence over later tokens, so `aggregate --help --format bytes` displays aggregate help successfully.

Repeating the scalar `--threads` or `--format` option is a status-2 error containing `cannot be used multiple times`. Repeating `--ignore-dirs` is valid and adds paths. Boolean short options may be separate; support for concatenated short options is not required. A token following `--threads` that is negative, fractional, empty, or nonnumeric is invalid. In the space-separated negative case, such as `--threads -1`, the parser treats `-1` as an unexpected argument rather than as the option's value. Zero means automatic processor selection and is valid; positive values select that worker count without changing results.

## Spec 4

All parse errors go to stderr, start or contain `error:`, return status 2, and include a `--help` hint. Diagnostics must identify the offending option/value. In particular, use these stable phrases where applicable:

```text
unexpected argument '--NAME' found
a value is required for '--threads <THREADS>'
invalid value 'VALUE' for '--threads <THREADS>'
a value is required for '--format <FORMAT>'
invalid value 'VALUE' for '--format <FORMAT>'
[possible values: metric, binary, bytes, gb, gib, mb, mib]
the following required arguments were not provided:
  <SHELL>
invalid value 'VALUE' for '<SHELL>'
[possible values: bash, elvish, fish, powershell, zsh]
```

The `--format` possible-values line immediately follows its invalid-value line. For `--threads -1`, use the following diagnostic instead of the stable invalid-value phrase above:

```text
error: unexpected argument '-1' found

  tip: to pass '-1' as a value, use '-- -1'

Usage: dua [FLAGS] [OPTIONS] [SUBCOMMAND] [INPUT]...

For more information, try '--help'.
```

An unknown aggregate option additionally mentions that a similar argument exists when appropriate. Extra completion arguments are reported as `unexpected argument 'ARG' found`. Missing values for `--ignore-dirs` and `--log-file` identify that option and say that a value is required. No parse error is written to stdout.

## Spec 5

Top-level long help (`--help`) must be exactly the following UTF-8 text, including blank lines, indentation, and final newline:

```text
A tool to learn about disk usage, fast!

Usage: dua [FLAGS] [OPTIONS] [SUBCOMMAND] [INPUT]...

Commands:
  interactive  Launch the terminal user interface [aliases: i]
  aggregate    Aggregate the consumed space of one or more directories or files [aliases: a]
  completions  Generate shell completions
  help         Print this message or the help of the given subcommand(s)

Arguments:
  [INPUT]...
          One or more input files or directories. If unset, we will use all entries in the current working directory

Options:
  -t, --threads <THREADS>
          The amount of threads to use. Defaults to 0, indicating the amount of logical processors. Set to 1 to use only a single thread
          
          [default: 0]

  -f, --format <FORMAT>
          The format with which to print byte counts
          
          [default: binary]
          [possible values: metric, binary, bytes, gb, gib, mb, mib]

  -A, --apparent-size
          Display apparent size instead of disk usage

  -l, --count-hard-links
          Count hard-linked files each time they are seen

  -x, --stay-on-filesystem
          If set, we will not cross filesystems or traverse mount points

  -i, --ignore-dirs <IGNORE_DIRS>
          One or more absolute directories to ignore. Note that these are not ignored if they are passed as input path.
          
          Hence, they will only be ignored if they are eventually reached as part of the traversal.
          
          [default: /proc /dev /sys /run]

      --log-file <LOG_FILE>
          Write a log file with debug information, including panics

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

## Spec 6

Top-level short help (`-h`) must be exactly:

```text
A tool to learn about disk usage, fast!

Usage: dua [FLAGS] [OPTIONS] [SUBCOMMAND] [INPUT]...

Commands:
  interactive  Launch the terminal user interface [aliases: i]
  aggregate    Aggregate the consumed space of one or more directories or files [aliases: a]
  completions  Generate shell completions
  help         Print this message or the help of the given subcommand(s)

Arguments:
  [INPUT]...  One or more input files or directories. If unset, we will use all entries in the current working directory

Options:
  -t, --threads <THREADS>          The amount of threads to use. Defaults to 0, indicating the amount of logical processors. Set to 1 to use only a single thread [default: 0]
  -f, --format <FORMAT>            The format with which to print byte counts [default: binary] [possible values: metric, binary, bytes, gb, gib, mb, mib]
  -A, --apparent-size              Display apparent size instead of disk usage
  -l, --count-hard-links           Count hard-linked files each time they are seen
  -x, --stay-on-filesystem         If set, we will not cross filesystems or traverse mount points
  -i, --ignore-dirs <IGNORE_DIRS>  One or more absolute directories to ignore. Note that these are not ignored if they are passed as input path [default: /proc /dev /sys /run]
      --log-file <LOG_FILE>        Write a log file with debug information, including panics
  -h, --help                       Print help (see more with '--help')
  -V, --version                    Print version
```

Both help forms write nothing to stderr and return 0.

## Spec 7

Subcommand help is exact. The program name in these pages is literally `executable`, even if invoked through an absolute path or alias.

`interactive --help` (and `i --help`):

```text
Launch the terminal user interface

Usage: executable interactive [OPTIONS] [INPUT]...

Arguments:
  [INPUT]...  One or more input files or directories. If unset, we will use all entries in the current working directory

Options:
  -e, --no-entry-check  Do not check entries for presence when listing a directory to avoid slugging performance on slow filesystems
  -h, --help            Print help
```

`aggregate --help` (and `a --help`):

```text
Aggregate the consumed space of one or more directories or files

Usage: executable aggregate [OPTIONS] [INPUT]...

Arguments:
  [INPUT]...  One or more input files or directories. If unset, we will use all entries in the current working directory

Options:
      --stats     If set, print additional statistics about the file traversal to stderr
      --no-sort   If set, paths will be printed in their order of occurrence on the command-line. Otherwise they are sorted by their size in bytes, ascending
      --no-total  If set, no total column will be computed for multiple inputs
  -h, --help      Print help
```

`completions --help`:

```text
Generate shell completions

Usage: executable completions <SHELL>

Arguments:
  <SHELL>  The shell to generate a completions-script for [possible values: bash, elvish, fish, powershell, zsh]

Options:
  -h, --help  Print help
```

Each block has one final newline, no stderr, and status 0.

## Spec 8

`--version` and `-V` produce identical stdout `dua 2.32.2\n`, no stderr, and status 0. It also takes precedence over later ordinary flags; for example, `--version --format BAD` still produces exactly that successful version output.

## Spec 9

Aggregate input expansion follows these rules:

- With no input paths, enumerate the immediate entries of the current working directory. Hidden entries are included; symlinks in this implicit listing are omitted.
- With exactly one input that names a directory, behave as though that directory became the working directory and its immediate entries were the inputs. Display only their basenames. A lone empty directory consequently produces empty stdout (but statistics, if requested, still go to stderr).
- A single non-directory input is itself the one displayed row.
- With two or more explicit inputs, do not expand them for display. Produce one row per given argument, retain duplicates as separate rows, and display the original argument spelling (relative/absolute form, `./`, and trailing slash included).

Directories displayed as rows are measured recursively, but their descendants are not separate rows. The lone-directory expansion is why `aggregate /tmp/tree` lists `tree`'s children while `aggregate /tmp/tree /tmp/other` lists the two root arguments themselves.

## Spec 10

Default size means allocated disk space. For a regular file on Unix, use `st_blocks * 512` bytes; do not use filesystem block size or round `st_size` yourself. Thus a typical nonempty small file with eight 512-byte blocks is 4096 bytes, a zero-length or fully sparse file with zero blocks is zero, and a file allocated 26 blocks is 13312 bytes. With `-A`/`--apparent-size`, use the regular file's logical `st_size` instead.

A directory's size includes the selected size of the directory inode itself plus the selected sizes of eligible descendants, recursively. Under default sizing, directory metadata uses `st_blocks * 512`; under apparent sizing it uses the directory's logical `st_size`. Thus an apparent-size directory whose own metadata is 4096 bytes and which contains a 5-byte file measures 4101 bytes, and an empty directory can be nonzero. The original container used only to perform lone-directory expansion is not a displayed row and its own metadata is not added to the total; displayed child directories do include theirs.

Named pipes, Unix sockets, device nodes, and other non-regular special entries other than symbolic links measure zero and must not be opened or blocked upon. Symbolic-link accounting is specified in Spec 11. Traverse deep (at least 50 levels) and wide (at least 1000 entries) trees safely, including every directory's metadata in the result. Preserve all legal UTF-8 names, including emoji, CJK, Arabic, spaces, quotes, apostrophes, dollar signs, and 255-byte names.

## Spec 11

Do not follow symbolic links discovered while enumerating or recursively walking a directory, and do not let cycles recurse. A recursively discovered link contributes its own selected inode size to the containing directory but never the target's contents. Symlinks in the implicit/current-directory listing are omitted. An explicitly supplied broken link (including a link chain or cycle whose target cannot be resolved) becomes a zero-size row with one I/O error when failed rows are rendered. Continue with other roots. An explicitly supplied valid symlink is not resolved as its target: its row measures the link inode itself (`st_blocks * 512` normally, link-text `st_size` with apparent sizing). Consequently, supplying both a target and a symlink to it counts the target and the link as two distinct rows.

By default, track multiply-linked regular files (those whose link count is greater than one) by `(device, inode)` over the entire invocation. The first encountered hard link contributes its normal size and later occurrences of that inode contribute zero. Sorting still puts those zero rows first. An ordinary regular file with link count one is not put into this deduplication set: duplicate arguments and overlapping roots can therefore count that file independently each time. With `-l`/`--count-hard-links`, every occurrence contributes independently. For three explicit links to one one-block file, byte format is respectively `0`, `0`, `4096`, total `4096` by default, and three `4096` rows totaling `12288` with `-l`; by contrast, the explicit sequence `./b a ./b` for ordinary one-link files of apparent sizes 2 and 1 produces `2`, `1`, and `2` under `--no-sort`.

## Spec 12

`--ignore-dirs PATH` may occur more than once and repeated occurrences accumulate. Canonicalize its values. Default ignored paths are `/proc`, `/dev`, `/sys`, and `/run`. If an ignored directory is reached during recursive traversal, retain the directory row if it is an immediate displayed entry, count the directory's own metadata size, and do not enter it. For example, an ignored directory whose apparent metadata size is 4096 bytes is a 4096-byte row even though its descendants contribute nothing. An ignored path supplied directly as the sole directory argument is not ignored: its immediate children are still listed and measured. `--stay-on-filesystem` prevents descending into an entry whose device ID differs from the traversal root's device; it otherwise does not alter results.

Thread count changes only concurrency. Results, totals, hard-link accounting, formatting, and requested no-sort ordering must be consistent for `--threads 0`, `1`, and larger positive values.

## Spec 13

Before size sorting, explicit roots are in command-line order, while entries produced by the no-input or lone-directory expansion are ordered lexically by their displayed names (hidden names participate normally). Unless `--no-sort` is present, stably sort those rows by raw byte size ascending. Equal-size explicit roots therefore retain command-line order, while equal-size expanded entries retain lexical order. Rendered I/O-error rows have size zero and therefore precede nonzero rows. With `--no-sort`, explicit successful roots occur exactly in command-line order and expanded entries still occur in lexical order; failed-root omission in this mode is specified in Spec 14. The `total` row always follows all rendered individual rows.

Print `total` only when the effective displayed input list contains at least two entries. It is the sum of the successful displayed roots, including duplicate ordinary arguments (subject to the multiply-linked-file deduplication in Spec 11); failed roots contribute zero and their errors are still summarized even when their individual rows are omitted. `--no-total` suppresses it. A sole file never has a total row. A current directory with multiple entries does. Multiple error roots also have a total row even when all sizes are zero.

## Spec 14

Every aggregate row is:

```text
GREEN formatted-size RESET SPACE [CYAN path RESET | plain-file-name] [two spaces error-summary] NEWLINE
```

where `GREEN` is exactly ESC`[32m`, `RESET` is ESC`[39m`, and directory paths, successful non-regular special-file paths such as FIFOs and Unix sockets, and rendered failed paths use exactly ESC`[36m` ... ESC`[39m`. Regular-file names, successful valid-symbolic-link paths, and `total` are uncolored. ANSI codes are emitted even when stdout is captured or piped.

The size text (including its left padding) is inside green. The human-readable core forms include `0   B`, `4.00 KiB`, `50.00 KB`, `0.20 MB`, and `0.20 MiB`. In `bytes` mode, right-align the integer plus ` b` to 12 characters: `         0 b`, `      4096 b`, `     12345 b`. Other modes may left-pad sufficiently to align their size columns; stripping leading padding must yield exactly the values defined in Spec 15.

Without `--no-sort`, render each failed root as a zero-size cyan row and append `  <1 IO Error>`. With `--no-sort`, omit individual failed-root rows entirely, while continuing to render successful roots in command-line order. In both modes, a total aggregates all failures and uses `  <N IO Errors>` for `N != 1`, singular for one. Thus two missing roots under `--no-sort` produce only `0 b total  <2 IO Errors>`, while a missing root followed by a 5-byte valid root produces the valid row and `5 b total  <1 IO Error>`. For example, without `--no-sort`, after removing ANSI:

```text
0   B /nonexistent1  <1 IO Error>
0   B /nonexistent2  <1 IO Error>
0   B total  <2 IO Errors>
```

Errors are part of stdout, not stderr, and make the final status 1.

## Spec 15

Size-format conversion uses raw integer bytes and round-to-nearest display with two fractional digits:

- `bytes`: exact integer and lowercase `b`.
- `binary` (default): adaptive base 1024, units `B`, `KiB`, `MiB`, `GiB`, `TiB`; zero is `0   B`, while scaled values use two decimals. Advance to the next unit only when the byte count is strictly greater than the next power of 1024, not when it is equal.
- `metric`: adaptive base 1000, units `B`, `KB`, `MB`, `GB`, `TB`; zero is `0  B`, while scaled values use two decimals. Advance to the next unit only when the byte count is strictly greater than the next power of 1000, not when it is equal.
- `gb`: bytes / 1,000,000,000, always two decimals and `GB`.
- `gib`: bytes / 1,073,741,824, always two decimals and `GiB`.
- `mb`: bytes / 1,000,000, always two decimals and `MB`.
- `mib`: bytes / 1,048,576, always two decimals and `MiB`.

Examples under apparent-size mode are exact after ANSI removal and trimming outer whitespace:

```text
12345 b PATH
50.00 KB PATH                 # 50000 bytes, metric
4.88 KiB PATH                 # 5000 bytes, binary
0.20 MB PATH                  # 200000 bytes, mb
0.20 MiB PATH                 # 209715 bytes, mib
0.20 GB PATH                  # 200000000 bytes, gb
0.20 GiB PATH                 # 214748365 bytes, gib
0   B PATH                    # zero bytes, binary
0  B PATH                     # zero bytes, metric
0.00 MB PATH                  # zero bytes, mb
0.00 MiB PATH                 # zero bytes, mib
0.00 GB PATH                  # zero bytes, gb
0.00 GiB PATH                 # zero bytes, gib
```

At exact adaptive boundaries, the lower unit remains in use: binary renders 1024 bytes as `1024   B`, 1048576 as `1024.00 KiB`, 1073741824 as `1024.00 MiB`, and 1099511627776 as `1024.00 GiB`; metric similarly renders 1000 as `1000  B`, 1000000 as `1000.00 KB`, 1000000000 as `1000.00 MB`, and 1000000000000 as `1000.00 GB`.

Apply one chosen format to every row including total. Statistics always report raw integer bytes.

## Spec 16

With aggregate `--stats`, write exactly one Rust-debug-style line to stderr after traversal:

```text
Statistics { entries_traversed: N, smallest_file_in_bytes: MIN, largest_file_in_bytes: MAX }
```

`N` is the number of eligible filesystem entries actually visited across effective roots, counting regular files and directories but not the synthetic total or original container directory used only for lone-directory expansion. `MIN` and `MAX` are the minimum and maximum selected byte measures of all visited entries, including each directory's own metadata measure; with apparent-size, regular files use logical size and directories use the directory measure described in Spec 10. For three direct files of lengths 1, 500, and 5000 under apparent-size, output `N=3`, `MIN=1`, `MAX=5000`. For a container holding a 1-byte file plus a nested directory with 4096 bytes of metadata and a 3-byte child, output `N=3`, `MIN=1`, `MAX=4096`. With no entries, all three values are zero. The line is written even for empty input and can accompany status 1. Normal rows remain solely on stdout.

## Spec 17

`completions SHELL` supports, case-sensitively, `bash`, `elvish`, `fish`, `powershell`, and `zsh`, returns 0, writes no stderr, and emits the exact script bytes encoded below. Decode each Base64 payload with the standard Base64 alphabet; the decoded bytes, including their final newline, are the entire stdout for that shell. No external generator or template is part of the contract.

### `bash` payload

```base64
X2R1YSgpIHsKICAgIGxvY2FsIGkgY3VyIHByZXYgb3B0cyBjbWQKICAgIENPTVBSRVBMWT0oKQog
ICAgaWYgW1sgIiR7QkFTSF9WRVJTSU5GT1swXX0iIC1nZSA0IF1dOyB0aGVuCiAgICAgICAgY3Vy
PSIkMiIKICAgIGVsc2UKICAgICAgICBjdXI9IiR7Q09NUF9XT1JEU1tDT01QX0NXT1JEXX0iCiAg
ICBmaQogICAgcHJldj0iJDMiCiAgICBjbWQ9IiIKICAgIG9wdHM9IiIKCiAgICBmb3IgaSBpbiAi
JHtDT01QX1dPUkRTW0BdOjA6Q09NUF9DV09SRH0iCiAgICBkbwogICAgICAgIGNhc2UgIiR7Y21k
fSwke2l9IiBpbgogICAgICAgICAgICAiLCQxIikKICAgICAgICAgICAgICAgIGNtZD0iZHVhIgog
ICAgICAgICAgICAgICAgOzsKICAgICAgICAgICAgZHVhLGEpCiAgICAgICAgICAgICAgICBjbWQ9
ImR1YV9fYWdncmVnYXRlIgogICAgICAgICAgICAgICAgOzsKICAgICAgICAgICAgZHVhLGFnZ3Jl
Z2F0ZSkKICAgICAgICAgICAgICAgIGNtZD0iZHVhX19hZ2dyZWdhdGUiCiAgICAgICAgICAgICAg
ICA7OwogICAgICAgICAgICBkdWEsY29tcGxldGlvbnMpCiAgICAgICAgICAgICAgICBjbWQ9ImR1
YV9fY29tcGxldGlvbnMiCiAgICAgICAgICAgICAgICA7OwogICAgICAgICAgICBkdWEsaGVscCkK
ICAgICAgICAgICAgICAgIGNtZD0iZHVhX19oZWxwIgogICAgICAgICAgICAgICAgOzsKICAgICAg
ICAgICAgZHVhLGkpCiAgICAgICAgICAgICAgICBjbWQ9ImR1YV9faW50ZXJhY3RpdmUiCiAgICAg
ICAgICAgICAgICA7OwogICAgICAgICAgICBkdWEsaW50ZXJhY3RpdmUpCiAgICAgICAgICAgICAg
ICBjbWQ9ImR1YV9faW50ZXJhY3RpdmUiCiAgICAgICAgICAgICAgICA7OwogICAgICAgICAgICBk
dWFfX2hlbHAsYWdncmVnYXRlKQogICAgICAgICAgICAgICAgY21kPSJkdWFfX2hlbHBfX2FnZ3Jl
Z2F0ZSIKICAgICAgICAgICAgICAgIDs7CiAgICAgICAgICAgIGR1YV9faGVscCxjb21wbGV0aW9u
cykKICAgICAgICAgICAgICAgIGNtZD0iZHVhX19oZWxwX19jb21wbGV0aW9ucyIKICAgICAgICAg
ICAgICAgIDs7CiAgICAgICAgICAgIGR1YV9faGVscCxoZWxwKQogICAgICAgICAgICAgICAgY21k
PSJkdWFfX2hlbHBfX2hlbHAiCiAgICAgICAgICAgICAgICA7OwogICAgICAgICAgICBkdWFfX2hl
bHAsaW50ZXJhY3RpdmUpCiAgICAgICAgICAgICAgICBjbWQ9ImR1YV9faGVscF9faW50ZXJhY3Rp
dmUiCiAgICAgICAgICAgICAgICA7OwogICAgICAgICAgICAqKQogICAgICAgICAgICAgICAgOzsK
ICAgICAgICBlc2FjCiAgICBkb25lCgogICAgY2FzZSAiJHtjbWR9IiBpbgogICAgICAgIGR1YSkK
ICAgICAgICAgICAgb3B0cz0iLXQgLWYgLUEgLWwgLXggLWkgLWggLVYgLS10aHJlYWRzIC0tZm9y
bWF0IC0tYXBwYXJlbnQtc2l6ZSAtLWNvdW50LWhhcmQtbGlua3MgLS1zdGF5LW9uLWZpbGVzeXN0
ZW0gLS1pZ25vcmUtZGlycyAtLWxvZy1maWxlIC0taGVscCAtLXZlcnNpb24gW0lOUFVUXS4uLiBp
bnRlcmFjdGl2ZSBpIGFnZ3JlZ2F0ZSBhIGNvbXBsZXRpb25zIGhlbHAiCiAgICAgICAgICAgIGlm
IFtbICR7Y3VyfSA9PSAtKiB8fCAke0NPTVBfQ1dPUkR9IC1lcSAxIF1dIDsgdGhlbgogICAgICAg
ICAgICAgICAgQ09NUFJFUExZPSggJChjb21wZ2VuIC1XICIke29wdHN9IiAtLSAiJHtjdXJ9Iikg
KQogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgZmkKICAgICAgICAgICAgY2Fz
ZSAiJHtwcmV2fSIgaW4KICAgICAgICAgICAgICAgIC0tdGhyZWFkcykKICAgICAgICAgICAgICAg
ICAgICBDT01QUkVQTFk9KCQoY29tcGdlbiAtZiAiJHtjdXJ9IikpCiAgICAgICAgICAgICAgICAg
ICAgcmV0dXJuIDAKICAgICAgICAgICAgICAgICAgICA7OwogICAgICAgICAgICAgICAgLXQpCiAg
ICAgICAgICAgICAgICAgICAgQ09NUFJFUExZPSgkKGNvbXBnZW4gLWYgIiR7Y3VyfSIpKQogICAg
ICAgICAgICAgICAgICAgIHJldHVybiAwCiAgICAgICAgICAgICAgICAgICAgOzsKICAgICAgICAg
ICAgICAgIC0tZm9ybWF0KQogICAgICAgICAgICAgICAgICAgIENPTVBSRVBMWT0oJChjb21wZ2Vu
IC1XICJtZXRyaWMgYmluYXJ5IGJ5dGVzIGdiIGdpYiBtYiBtaWIiIC0tICIke2N1cn0iKSkKICAg
ICAgICAgICAgICAgICAgICByZXR1cm4gMAogICAgICAgICAgICAgICAgICAgIDs7CiAgICAgICAg
ICAgICAgICAtZikKICAgICAgICAgICAgICAgICAgICBDT01QUkVQTFk9KCQoY29tcGdlbiAtVyAi
bWV0cmljIGJpbmFyeSBieXRlcyBnYiBnaWIgbWIgbWliIiAtLSAiJHtjdXJ9IikpCiAgICAgICAg
ICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgICAgICAgICA7OwogICAgICAgICAgICAg
ICAgLS1pZ25vcmUtZGlycykKICAgICAgICAgICAgICAgICAgICBDT01QUkVQTFk9KCQoY29tcGdl
biAtZiAiJHtjdXJ9IikpCiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAg
ICAgICAgICA7OwogICAgICAgICAgICAgICAgLWkpCiAgICAgICAgICAgICAgICAgICAgQ09NUFJF
UExZPSgkKGNvbXBnZW4gLWYgIiR7Y3VyfSIpKQogICAgICAgICAgICAgICAgICAgIHJldHVybiAw
CiAgICAgICAgICAgICAgICAgICAgOzsKICAgICAgICAgICAgICAgIC0tbG9nLWZpbGUpCiAgICAg
ICAgICAgICAgICAgICAgQ09NUFJFUExZPSgkKGNvbXBnZW4gLWYgIiR7Y3VyfSIpKQogICAgICAg
ICAgICAgICAgICAgIHJldHVybiAwCiAgICAgICAgICAgICAgICAgICAgOzsKICAgICAgICAgICAg
ICAgICopCiAgICAgICAgICAgICAgICAgICAgQ09NUFJFUExZPSgpCiAgICAgICAgICAgICAgICAg
ICAgOzsKICAgICAgICAgICAgZXNhYwogICAgICAgICAgICBDT01QUkVQTFk9KCAkKGNvbXBnZW4g
LVcgIiR7b3B0c30iIC0tICIke2N1cn0iKSApCiAgICAgICAgICAgIHJldHVybiAwCiAgICAgICAg
ICAgIDs7CiAgICAgICAgZHVhX19hZ2dyZWdhdGUpCiAgICAgICAgICAgIG9wdHM9Ii1oIC0tc3Rh
dHMgLS1uby1zb3J0IC0tbm8tdG90YWwgLS1oZWxwIFtJTlBVVF0uLi4iCiAgICAgICAgICAgIGlm
IFtbICR7Y3VyfSA9PSAtKiB8fCAke0NPTVBfQ1dPUkR9IC1lcSAyIF1dIDsgdGhlbgogICAgICAg
ICAgICAgICAgQ09NUFJFUExZPSggJChjb21wZ2VuIC1XICIke29wdHN9IiAtLSAiJHtjdXJ9Iikg
KQogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgZmkKICAgICAgICAgICAgY2Fz
ZSAiJHtwcmV2fSIgaW4KICAgICAgICAgICAgICAgICopCiAgICAgICAgICAgICAgICAgICAgQ09N
UFJFUExZPSgpCiAgICAgICAgICAgICAgICAgICAgOzsKICAgICAgICAgICAgZXNhYwogICAgICAg
ICAgICBDT01QUkVQTFk9KCAkKGNvbXBnZW4gLVcgIiR7b3B0c30iIC0tICIke2N1cn0iKSApCiAg
ICAgICAgICAgIHJldHVybiAwCiAgICAgICAgICAgIDs7CiAgICAgICAgZHVhX19jb21wbGV0aW9u
cykKICAgICAgICAgICAgb3B0cz0iLWggLS1oZWxwIGJhc2ggZWx2aXNoIGZpc2ggcG93ZXJzaGVs
bCB6c2giCiAgICAgICAgICAgIGlmIFtbICR7Y3VyfSA9PSAtKiB8fCAke0NPTVBfQ1dPUkR9IC1l
cSAyIF1dIDsgdGhlbgogICAgICAgICAgICAgICAgQ09NUFJFUExZPSggJChjb21wZ2VuIC1XICIk
e29wdHN9IiAtLSAiJHtjdXJ9IikgKQogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAg
ICAgZmkKICAgICAgICAgICAgY2FzZSAiJHtwcmV2fSIgaW4KICAgICAgICAgICAgICAgICopCiAg
ICAgICAgICAgICAgICAgICAgQ09NUFJFUExZPSgpCiAgICAgICAgICAgICAgICAgICAgOzsKICAg
ICAgICAgICAgZXNhYwogICAgICAgICAgICBDT01QUkVQTFk9KCAkKGNvbXBnZW4gLVcgIiR7b3B0
c30iIC0tICIke2N1cn0iKSApCiAgICAgICAgICAgIHJldHVybiAwCiAgICAgICAgICAgIDs7CiAg
ICAgICAgZHVhX19oZWxwKQogICAgICAgICAgICBvcHRzPSJpbnRlcmFjdGl2ZSBhZ2dyZWdhdGUg
Y29tcGxldGlvbnMgaGVscCIKICAgICAgICAgICAgaWYgW1sgJHtjdXJ9ID09IC0qIHx8ICR7Q09N
UF9DV09SRH0gLWVxIDIgXV0gOyB0aGVuCiAgICAgICAgICAgICAgICBDT01QUkVQTFk9KCAkKGNv
bXBnZW4gLVcgIiR7b3B0c30iIC0tICIke2N1cn0iKSApCiAgICAgICAgICAgICAgICByZXR1cm4g
MAogICAgICAgICAgICBmaQogICAgICAgICAgICBjYXNlICIke3ByZXZ9IiBpbgogICAgICAgICAg
ICAgICAgKikKICAgICAgICAgICAgICAgICAgICBDT01QUkVQTFk9KCkKICAgICAgICAgICAgICAg
ICAgICA7OwogICAgICAgICAgICBlc2FjCiAgICAgICAgICAgIENPTVBSRVBMWT0oICQoY29tcGdl
biAtVyAiJHtvcHRzfSIgLS0gIiR7Y3VyfSIpICkKICAgICAgICAgICAgcmV0dXJuIDAKICAgICAg
ICAgICAgOzsKICAgICAgICBkdWFfX2hlbHBfX2FnZ3JlZ2F0ZSkKICAgICAgICAgICAgb3B0cz0i
IgogICAgICAgICAgICBpZiBbWyAke2N1cn0gPT0gLSogfHwgJHtDT01QX0NXT1JEfSAtZXEgMyBd
XSA7IHRoZW4KICAgICAgICAgICAgICAgIENPTVBSRVBMWT0oICQoY29tcGdlbiAtVyAiJHtvcHRz
fSIgLS0gIiR7Y3VyfSIpICkKICAgICAgICAgICAgICAgIHJldHVybiAwCiAgICAgICAgICAgIGZp
CiAgICAgICAgICAgIGNhc2UgIiR7cHJldn0iIGluCiAgICAgICAgICAgICAgICAqKQogICAgICAg
ICAgICAgICAgICAgIENPTVBSRVBMWT0oKQogICAgICAgICAgICAgICAgICAgIDs7CiAgICAgICAg
ICAgIGVzYWMKICAgICAgICAgICAgQ09NUFJFUExZPSggJChjb21wZ2VuIC1XICIke29wdHN9IiAt
LSAiJHtjdXJ9IikgKQogICAgICAgICAgICByZXR1cm4gMAogICAgICAgICAgICA7OwogICAgICAg
IGR1YV9faGVscF9fY29tcGxldGlvbnMpCiAgICAgICAgICAgIG9wdHM9IiIKICAgICAgICAgICAg
aWYgW1sgJHtjdXJ9ID09IC0qIHx8ICR7Q09NUF9DV09SRH0gLWVxIDMgXV0gOyB0aGVuCiAgICAg
ICAgICAgICAgICBDT01QUkVQTFk9KCAkKGNvbXBnZW4gLVcgIiR7b3B0c30iIC0tICIke2N1cn0i
KSApCiAgICAgICAgICAgICAgICByZXR1cm4gMAogICAgICAgICAgICBmaQogICAgICAgICAgICBj
YXNlICIke3ByZXZ9IiBpbgogICAgICAgICAgICAgICAgKikKICAgICAgICAgICAgICAgICAgICBD
T01QUkVQTFk9KCkKICAgICAgICAgICAgICAgICAgICA7OwogICAgICAgICAgICBlc2FjCiAgICAg
ICAgICAgIENPTVBSRVBMWT0oICQoY29tcGdlbiAtVyAiJHtvcHRzfSIgLS0gIiR7Y3VyfSIpICkK
ICAgICAgICAgICAgcmV0dXJuIDAKICAgICAgICAgICAgOzsKICAgICAgICBkdWFfX2hlbHBfX2hl
bHApCiAgICAgICAgICAgIG9wdHM9IiIKICAgICAgICAgICAgaWYgW1sgJHtjdXJ9ID09IC0qIHx8
ICR7Q09NUF9DV09SRH0gLWVxIDMgXV0gOyB0aGVuCiAgICAgICAgICAgICAgICBDT01QUkVQTFk9
KCAkKGNvbXBnZW4gLVcgIiR7b3B0c30iIC0tICIke2N1cn0iKSApCiAgICAgICAgICAgICAgICBy
ZXR1cm4gMAogICAgICAgICAgICBmaQogICAgICAgICAgICBjYXNlICIke3ByZXZ9IiBpbgogICAg
ICAgICAgICAgICAgKikKICAgICAgICAgICAgICAgICAgICBDT01QUkVQTFk9KCkKICAgICAgICAg
ICAgICAgICAgICA7OwogICAgICAgICAgICBlc2FjCiAgICAgICAgICAgIENPTVBSRVBMWT0oICQo
Y29tcGdlbiAtVyAiJHtvcHRzfSIgLS0gIiR7Y3VyfSIpICkKICAgICAgICAgICAgcmV0dXJuIDAK
ICAgICAgICAgICAgOzsKICAgICAgICBkdWFfX2hlbHBfX2ludGVyYWN0aXZlKQogICAgICAgICAg
ICBvcHRzPSIiCiAgICAgICAgICAgIGlmIFtbICR7Y3VyfSA9PSAtKiB8fCAke0NPTVBfQ1dPUkR9
IC1lcSAzIF1dIDsgdGhlbgogICAgICAgICAgICAgICAgQ09NUFJFUExZPSggJChjb21wZ2VuIC1X
ICIke29wdHN9IiAtLSAiJHtjdXJ9IikgKQogICAgICAgICAgICAgICAgcmV0dXJuIDAKICAgICAg
ICAgICAgZmkKICAgICAgICAgICAgY2FzZSAiJHtwcmV2fSIgaW4KICAgICAgICAgICAgICAgICop
CiAgICAgICAgICAgICAgICAgICAgQ09NUFJFUExZPSgpCiAgICAgICAgICAgICAgICAgICAgOzsK
ICAgICAgICAgICAgZXNhYwogICAgICAgICAgICBDT01QUkVQTFk9KCAkKGNvbXBnZW4gLVcgIiR7
b3B0c30iIC0tICIke2N1cn0iKSApCiAgICAgICAgICAgIHJldHVybiAwCiAgICAgICAgICAgIDs7
CiAgICAgICAgZHVhX19pbnRlcmFjdGl2ZSkKICAgICAgICAgICAgb3B0cz0iLWUgLWggLS1uby1l
bnRyeS1jaGVjayAtLWhlbHAgW0lOUFVUXS4uLiIKICAgICAgICAgICAgaWYgW1sgJHtjdXJ9ID09
IC0qIHx8ICR7Q09NUF9DV09SRH0gLWVxIDIgXV0gOyB0aGVuCiAgICAgICAgICAgICAgICBDT01Q
UkVQTFk9KCAkKGNvbXBnZW4gLVcgIiR7b3B0c30iIC0tICIke2N1cn0iKSApCiAgICAgICAgICAg
ICAgICByZXR1cm4gMAogICAgICAgICAgICBmaQogICAgICAgICAgICBjYXNlICIke3ByZXZ9IiBp
bgogICAgICAgICAgICAgICAgKikKICAgICAgICAgICAgICAgICAgICBDT01QUkVQTFk9KCkKICAg
ICAgICAgICAgICAgICAgICA7OwogICAgICAgICAgICBlc2FjCiAgICAgICAgICAgIENPTVBSRVBM
WT0oICQoY29tcGdlbiAtVyAiJHtvcHRzfSIgLS0gIiR7Y3VyfSIpICkKICAgICAgICAgICAgcmV0
dXJuIDAKICAgICAgICAgICAgOzsKICAgIGVzYWMKfQoKaWYgW1sgIiR7QkFTSF9WRVJTSU5GT1sw
XX0iIC1lcSA0ICYmICIke0JBU0hfVkVSU0lORk9bMV19IiAtZ2UgNCB8fCAiJHtCQVNIX1ZFUlNJ
TkZPWzBdfSIgLWd0IDQgXV07IHRoZW4KICAgIGNvbXBsZXRlIC1GIF9kdWEgLW8gbm9zb3J0IC1v
IGJhc2hkZWZhdWx0IC1vIGRlZmF1bHQgZHVhCmVsc2UKICAgIGNvbXBsZXRlIC1GIF9kdWEgLW8g
YmFzaGRlZmF1bHQgLW8gZGVmYXVsdCBkdWEKZmkK
```

### `elvish` payload

```base64
CnVzZSBidWlsdGluOwp1c2Ugc3RyOwoKc2V0IGVkaXQ6Y29tcGxldGlvbjphcmctY29tcGxldGVy
W2R1YV0gPSB7fEB3b3Jkc3wKICAgIGZuIHNwYWNlcyB7fG58CiAgICAgICAgYnVpbHRpbjpyZXBl
YXQgJG4gJyAnIHwgc3RyOmpvaW4gJycKICAgIH0KICAgIGZuIGNhbmQge3x0ZXh0IGRlc2N8CiAg
ICAgICAgZWRpdDpjb21wbGV4LWNhbmRpZGF0ZSAkdGV4dCAmZGlzcGxheT0kdGV4dCcgJyhzcGFj
ZXMgKC0gMTQgKHdjc3dpZHRoICR0ZXh0KSkpJGRlc2MKICAgIH0KICAgIHZhciBjb21tYW5kID0g
J2R1YScKICAgIGZvciB3b3JkICR3b3Jkc1sxLi4tMV0gewogICAgICAgIGlmIChzdHI6aGFzLXBy
ZWZpeCAkd29yZCAnLScpIHsKICAgICAgICAgICAgYnJlYWsKICAgICAgICB9CiAgICAgICAgc2V0
IGNvbW1hbmQgPSAkY29tbWFuZCc7JyR3b3JkCiAgICB9CiAgICB2YXIgY29tcGxldGlvbnMgPSBb
CiAgICAgICAgJidkdWEnPSB7CiAgICAgICAgICAgIGNhbmQgLXQgJ1RoZSBhbW91bnQgb2YgdGhy
ZWFkcyB0byB1c2UuIERlZmF1bHRzIHRvIDAsIGluZGljYXRpbmcgdGhlIGFtb3VudCBvZiBsb2dp
Y2FsIHByb2Nlc3NvcnMuIFNldCB0byAxIHRvIHVzZSBvbmx5IGEgc2luZ2xlIHRocmVhZCcKICAg
ICAgICAgICAgY2FuZCAtLXRocmVhZHMgJ1RoZSBhbW91bnQgb2YgdGhyZWFkcyB0byB1c2UuIERl
ZmF1bHRzIHRvIDAsIGluZGljYXRpbmcgdGhlIGFtb3VudCBvZiBsb2dpY2FsIHByb2Nlc3NvcnMu
IFNldCB0byAxIHRvIHVzZSBvbmx5IGEgc2luZ2xlIHRocmVhZCcKICAgICAgICAgICAgY2FuZCAt
ZiAnVGhlIGZvcm1hdCB3aXRoIHdoaWNoIHRvIHByaW50IGJ5dGUgY291bnRzJwogICAgICAgICAg
ICBjYW5kIC0tZm9ybWF0ICdUaGUgZm9ybWF0IHdpdGggd2hpY2ggdG8gcHJpbnQgYnl0ZSBjb3Vu
dHMnCiAgICAgICAgICAgIGNhbmQgLWkgJ09uZSBvciBtb3JlIGFic29sdXRlIGRpcmVjdG9yaWVz
IHRvIGlnbm9yZS4gTm90ZSB0aGF0IHRoZXNlIGFyZSBub3QgaWdub3JlZCBpZiB0aGV5IGFyZSBw
YXNzZWQgYXMgaW5wdXQgcGF0aCcKICAgICAgICAgICAgY2FuZCAtLWlnbm9yZS1kaXJzICdPbmUg
b3IgbW9yZSBhYnNvbHV0ZSBkaXJlY3RvcmllcyB0byBpZ25vcmUuIE5vdGUgdGhhdCB0aGVzZSBh
cmUgbm90IGlnbm9yZWQgaWYgdGhleSBhcmUgcGFzc2VkIGFzIGlucHV0IHBhdGgnCiAgICAgICAg
ICAgIGNhbmQgLS1sb2ctZmlsZSAnV3JpdGUgYSBsb2cgZmlsZSB3aXRoIGRlYnVnIGluZm9ybWF0
aW9uLCBpbmNsdWRpbmcgcGFuaWNzJwogICAgICAgICAgICBjYW5kIC1BICdEaXNwbGF5IGFwcGFy
ZW50IHNpemUgaW5zdGVhZCBvZiBkaXNrIHVzYWdlJwogICAgICAgICAgICBjYW5kIC0tYXBwYXJl
bnQtc2l6ZSAnRGlzcGxheSBhcHBhcmVudCBzaXplIGluc3RlYWQgb2YgZGlzayB1c2FnZScKICAg
ICAgICAgICAgY2FuZCAtbCAnQ291bnQgaGFyZC1saW5rZWQgZmlsZXMgZWFjaCB0aW1lIHRoZXkg
YXJlIHNlZW4nCiAgICAgICAgICAgIGNhbmQgLS1jb3VudC1oYXJkLWxpbmtzICdDb3VudCBoYXJk
LWxpbmtlZCBmaWxlcyBlYWNoIHRpbWUgdGhleSBhcmUgc2VlbicKICAgICAgICAgICAgY2FuZCAt
eCAnSWYgc2V0LCB3ZSB3aWxsIG5vdCBjcm9zcyBmaWxlc3lzdGVtcyBvciB0cmF2ZXJzZSBtb3Vu
dCBwb2ludHMnCiAgICAgICAgICAgIGNhbmQgLS1zdGF5LW9uLWZpbGVzeXN0ZW0gJ0lmIHNldCwg
d2Ugd2lsbCBub3QgY3Jvc3MgZmlsZXN5c3RlbXMgb3IgdHJhdmVyc2UgbW91bnQgcG9pbnRzJwog
ICAgICAgICAgICBjYW5kIC1oICdQcmludCBoZWxwIChzZWUgbW9yZSB3aXRoICcnLS1oZWxwJycp
JwogICAgICAgICAgICBjYW5kIC0taGVscCAnUHJpbnQgaGVscCAoc2VlIG1vcmUgd2l0aCAnJy0t
aGVscCcnKScKICAgICAgICAgICAgY2FuZCAtViAnUHJpbnQgdmVyc2lvbicKICAgICAgICAgICAg
Y2FuZCAtLXZlcnNpb24gJ1ByaW50IHZlcnNpb24nCiAgICAgICAgICAgIGNhbmQgaW50ZXJhY3Rp
dmUgJ0xhdW5jaCB0aGUgdGVybWluYWwgdXNlciBpbnRlcmZhY2UnCiAgICAgICAgICAgIGNhbmQg
aSAnTGF1bmNoIHRoZSB0ZXJtaW5hbCB1c2VyIGludGVyZmFjZScKICAgICAgICAgICAgY2FuZCBh
Z2dyZWdhdGUgJ0FnZ3JlZ2F0ZSB0aGUgY29uc3VtZWQgc3BhY2Ugb2Ygb25lIG9yIG1vcmUgZGly
ZWN0b3JpZXMgb3IgZmlsZXMnCiAgICAgICAgICAgIGNhbmQgYSAnQWdncmVnYXRlIHRoZSBjb25z
dW1lZCBzcGFjZSBvZiBvbmUgb3IgbW9yZSBkaXJlY3RvcmllcyBvciBmaWxlcycKICAgICAgICAg
ICAgY2FuZCBjb21wbGV0aW9ucyAnR2VuZXJhdGUgc2hlbGwgY29tcGxldGlvbnMnCiAgICAgICAg
ICAgIGNhbmQgaGVscCAnUHJpbnQgdGhpcyBtZXNzYWdlIG9yIHRoZSBoZWxwIG9mIHRoZSBnaXZl
biBzdWJjb21tYW5kKHMpJwogICAgICAgIH0KICAgICAgICAmJ2R1YTtpbnRlcmFjdGl2ZSc9IHsK
ICAgICAgICAgICAgY2FuZCAtZSAnRG8gbm90IGNoZWNrIGVudHJpZXMgZm9yIHByZXNlbmNlIHdo
ZW4gbGlzdGluZyBhIGRpcmVjdG9yeSB0byBhdm9pZCBzbHVnZ2luZyBwZXJmb3JtYW5jZSBvbiBz
bG93IGZpbGVzeXN0ZW1zJwogICAgICAgICAgICBjYW5kIC0tbm8tZW50cnktY2hlY2sgJ0RvIG5v
dCBjaGVjayBlbnRyaWVzIGZvciBwcmVzZW5jZSB3aGVuIGxpc3RpbmcgYSBkaXJlY3RvcnkgdG8g
YXZvaWQgc2x1Z2dpbmcgcGVyZm9ybWFuY2Ugb24gc2xvdyBmaWxlc3lzdGVtcycKICAgICAgICAg
ICAgY2FuZCAtaCAnUHJpbnQgaGVscCcKICAgICAgICAgICAgY2FuZCAtLWhlbHAgJ1ByaW50IGhl
bHAnCiAgICAgICAgfQogICAgICAgICYnZHVhO2knPSB7CiAgICAgICAgICAgIGNhbmQgLWUgJ0Rv
IG5vdCBjaGVjayBlbnRyaWVzIGZvciBwcmVzZW5jZSB3aGVuIGxpc3RpbmcgYSBkaXJlY3Rvcnkg
dG8gYXZvaWQgc2x1Z2dpbmcgcGVyZm9ybWFuY2Ugb24gc2xvdyBmaWxlc3lzdGVtcycKICAgICAg
ICAgICAgY2FuZCAtLW5vLWVudHJ5LWNoZWNrICdEbyBub3QgY2hlY2sgZW50cmllcyBmb3IgcHJl
c2VuY2Ugd2hlbiBsaXN0aW5nIGEgZGlyZWN0b3J5IHRvIGF2b2lkIHNsdWdnaW5nIHBlcmZvcm1h
bmNlIG9uIHNsb3cgZmlsZXN5c3RlbXMnCiAgICAgICAgICAgIGNhbmQgLWggJ1ByaW50IGhlbHAn
CiAgICAgICAgICAgIGNhbmQgLS1oZWxwICdQcmludCBoZWxwJwogICAgICAgIH0KICAgICAgICAm
J2R1YTthZ2dyZWdhdGUnPSB7CiAgICAgICAgICAgIGNhbmQgLS1zdGF0cyAnSWYgc2V0LCBwcmlu
dCBhZGRpdGlvbmFsIHN0YXRpc3RpY3MgYWJvdXQgdGhlIGZpbGUgdHJhdmVyc2FsIHRvIHN0ZGVy
cicKICAgICAgICAgICAgY2FuZCAtLW5vLXNvcnQgJ0lmIHNldCwgcGF0aHMgd2lsbCBiZSBwcmlu
dGVkIGluIHRoZWlyIG9yZGVyIG9mIG9jY3VycmVuY2Ugb24gdGhlIGNvbW1hbmQtbGluZS4gT3Ro
ZXJ3aXNlIHRoZXkgYXJlIHNvcnRlZCBieSB0aGVpciBzaXplIGluIGJ5dGVzLCBhc2NlbmRpbmcn
CiAgICAgICAgICAgIGNhbmQgLS1uby10b3RhbCAnSWYgc2V0LCBubyB0b3RhbCBjb2x1bW4gd2ls
bCBiZSBjb21wdXRlZCBmb3IgbXVsdGlwbGUgaW5wdXRzJwogICAgICAgICAgICBjYW5kIC1oICdQ
cmludCBoZWxwJwogICAgICAgICAgICBjYW5kIC0taGVscCAnUHJpbnQgaGVscCcKICAgICAgICB9
CiAgICAgICAgJidkdWE7YSc9IHsKICAgICAgICAgICAgY2FuZCAtLXN0YXRzICdJZiBzZXQsIHBy
aW50IGFkZGl0aW9uYWwgc3RhdGlzdGljcyBhYm91dCB0aGUgZmlsZSB0cmF2ZXJzYWwgdG8gc3Rk
ZXJyJwogICAgICAgICAgICBjYW5kIC0tbm8tc29ydCAnSWYgc2V0LCBwYXRocyB3aWxsIGJlIHBy
aW50ZWQgaW4gdGhlaXIgb3JkZXIgb2Ygb2NjdXJyZW5jZSBvbiB0aGUgY29tbWFuZC1saW5lLiBP
dGhlcndpc2UgdGhleSBhcmUgc29ydGVkIGJ5IHRoZWlyIHNpemUgaW4gYnl0ZXMsIGFzY2VuZGlu
ZycKICAgICAgICAgICAgY2FuZCAtLW5vLXRvdGFsICdJZiBzZXQsIG5vIHRvdGFsIGNvbHVtbiB3
aWxsIGJlIGNvbXB1dGVkIGZvciBtdWx0aXBsZSBpbnB1dHMnCiAgICAgICAgICAgIGNhbmQgLWgg
J1ByaW50IGhlbHAnCiAgICAgICAgICAgIGNhbmQgLS1oZWxwICdQcmludCBoZWxwJwogICAgICAg
IH0KICAgICAgICAmJ2R1YTtjb21wbGV0aW9ucyc9IHsKICAgICAgICAgICAgY2FuZCAtaCAnUHJp
bnQgaGVscCcKICAgICAgICAgICAgY2FuZCAtLWhlbHAgJ1ByaW50IGhlbHAnCiAgICAgICAgfQog
ICAgICAgICYnZHVhO2hlbHAnPSB7CiAgICAgICAgICAgIGNhbmQgaW50ZXJhY3RpdmUgJ0xhdW5j
aCB0aGUgdGVybWluYWwgdXNlciBpbnRlcmZhY2UnCiAgICAgICAgICAgIGNhbmQgYWdncmVnYXRl
ICdBZ2dyZWdhdGUgdGhlIGNvbnN1bWVkIHNwYWNlIG9mIG9uZSBvciBtb3JlIGRpcmVjdG9yaWVz
IG9yIGZpbGVzJwogICAgICAgICAgICBjYW5kIGNvbXBsZXRpb25zICdHZW5lcmF0ZSBzaGVsbCBj
b21wbGV0aW9ucycKICAgICAgICAgICAgY2FuZCBoZWxwICdQcmludCB0aGlzIG1lc3NhZ2Ugb3Ig
dGhlIGhlbHAgb2YgdGhlIGdpdmVuIHN1YmNvbW1hbmQocyknCiAgICAgICAgfQogICAgICAgICYn
ZHVhO2hlbHA7aW50ZXJhY3RpdmUnPSB7CiAgICAgICAgfQogICAgICAgICYnZHVhO2hlbHA7YWdn
cmVnYXRlJz0gewogICAgICAgIH0KICAgICAgICAmJ2R1YTtoZWxwO2NvbXBsZXRpb25zJz0gewog
ICAgICAgIH0KICAgICAgICAmJ2R1YTtoZWxwO2hlbHAnPSB7CiAgICAgICAgfQogICAgXQogICAg
JGNvbXBsZXRpb25zWyRjb21tYW5kXQp9Cg==
```

### `fish` payload

```base64
IyBQcmludCBhbiBvcHRzcGVjIGZvciBhcmdwYXJzZSB0byBoYW5kbGUgY21kJ3Mgb3B0aW9ucyB0
aGF0IGFyZSBpbmRlcGVuZGVudCBvZiBhbnkgc3ViY29tbWFuZC4KZnVuY3Rpb24gX19maXNoX2R1
YV9nbG9iYWxfb3B0c3BlY3MKCXN0cmluZyBqb2luIFxuIHQvdGhyZWFkcz0gZi9mb3JtYXQ9IEEv
YXBwYXJlbnQtc2l6ZSBsL2NvdW50LWhhcmQtbGlua3MgeC9zdGF5LW9uLWZpbGVzeXN0ZW0gaS9p
Z25vcmUtZGlycz0gbG9nLWZpbGU9IGgvaGVscCBWL3ZlcnNpb24KZW5kCgpmdW5jdGlvbiBfX2Zp
c2hfZHVhX25lZWRzX2NvbW1hbmQKCSMgRmlndXJlIG91dCBpZiB0aGUgY3VycmVudCBpbnZvY2F0
aW9uIGFscmVhZHkgaGFzIGEgY29tbWFuZC4KCXNldCAtbCBjbWQgKGNvbW1hbmRsaW5lIC1vcGMp
CglzZXQgLWUgY21kWzFdCglhcmdwYXJzZSAtcyAoX19maXNoX2R1YV9nbG9iYWxfb3B0c3BlY3Mp
IC0tICRjbWQgMj4vZGV2L251bGwKCW9yIHJldHVybgoJaWYgc2V0IC1xIGFyZ3ZbMV0KCQkjIEFs
c28gcHJpbnQgdGhlIGNvbW1hbmQsIHNvIHRoaXMgY2FuIGJlIHVzZWQgdG8gZmlndXJlIG91dCB3
aGF0IGl0IGlzLgoJCWVjaG8gJGFyZ3ZbMV0KCQlyZXR1cm4gMQoJZW5kCglyZXR1cm4gMAplbmQK
CmZ1bmN0aW9uIF9fZmlzaF9kdWFfdXNpbmdfc3ViY29tbWFuZAoJc2V0IC1sIGNtZCAoX19maXNo
X2R1YV9uZWVkc19jb21tYW5kKQoJdGVzdCAteiAiJGNtZCIKCWFuZCByZXR1cm4gMQoJY29udGFp
bnMgLS0gJGNtZFsxXSAkYXJndgplbmQKCmNvbXBsZXRlIC1jIGR1YSAtbiAiX19maXNoX2R1YV9u
ZWVkc19jb21tYW5kIiAtcyB0IC1sIHRocmVhZHMgLWQgJ1RoZSBhbW91bnQgb2YgdGhyZWFkcyB0
byB1c2UuIERlZmF1bHRzIHRvIDAsIGluZGljYXRpbmcgdGhlIGFtb3VudCBvZiBsb2dpY2FsIHBy
b2Nlc3NvcnMuIFNldCB0byAxIHRvIHVzZSBvbmx5IGEgc2luZ2xlIHRocmVhZCcgLXIKY29tcGxl
dGUgLWMgZHVhIC1uICJfX2Zpc2hfZHVhX25lZWRzX2NvbW1hbmQiIC1zIGYgLWwgZm9ybWF0IC1k
ICdUaGUgZm9ybWF0IHdpdGggd2hpY2ggdG8gcHJpbnQgYnl0ZSBjb3VudHMnIC1yIC1mIC1hICJt
ZXRyaWNcdCcnCmJpbmFyeVx0JycKYnl0ZXNcdCcnCmdiXHQnJwpnaWJcdCcnCm1iXHQnJwptaWJc
dCcnIgpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfbmVlZHNfY29tbWFuZCIgLXMgaSAt
bCBpZ25vcmUtZGlycyAtZCAnT25lIG9yIG1vcmUgYWJzb2x1dGUgZGlyZWN0b3JpZXMgdG8gaWdu
b3JlLiBOb3RlIHRoYXQgdGhlc2UgYXJlIG5vdCBpZ25vcmVkIGlmIHRoZXkgYXJlIHBhc3NlZCBh
cyBpbnB1dCBwYXRoJyAtciAtRgpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfbmVlZHNf
Y29tbWFuZCIgLWwgbG9nLWZpbGUgLWQgJ1dyaXRlIGEgbG9nIGZpbGUgd2l0aCBkZWJ1ZyBpbmZv
cm1hdGlvbiwgaW5jbHVkaW5nIHBhbmljcycgLXIgLUYKY29tcGxldGUgLWMgZHVhIC1uICJfX2Zp
c2hfZHVhX25lZWRzX2NvbW1hbmQiIC1zIEEgLWwgYXBwYXJlbnQtc2l6ZSAtZCAnRGlzcGxheSBh
cHBhcmVudCBzaXplIGluc3RlYWQgb2YgZGlzayB1c2FnZScKY29tcGxldGUgLWMgZHVhIC1uICJf
X2Zpc2hfZHVhX25lZWRzX2NvbW1hbmQiIC1zIGwgLWwgY291bnQtaGFyZC1saW5rcyAtZCAnQ291
bnQgaGFyZC1saW5rZWQgZmlsZXMgZWFjaCB0aW1lIHRoZXkgYXJlIHNlZW4nCmNvbXBsZXRlIC1j
IGR1YSAtbiAiX19maXNoX2R1YV9uZWVkc19jb21tYW5kIiAtcyB4IC1sIHN0YXktb24tZmlsZXN5
c3RlbSAtZCAnSWYgc2V0LCB3ZSB3aWxsIG5vdCBjcm9zcyBmaWxlc3lzdGVtcyBvciB0cmF2ZXJz
ZSBtb3VudCBwb2ludHMnCmNvbXBsZXRlIC1jIGR1YSAtbiAiX19maXNoX2R1YV9uZWVkc19jb21t
YW5kIiAtcyBoIC1sIGhlbHAgLWQgJ1ByaW50IGhlbHAgKHNlZSBtb3JlIHdpdGggXCctLWhlbHBc
JyknCmNvbXBsZXRlIC1jIGR1YSAtbiAiX19maXNoX2R1YV9uZWVkc19jb21tYW5kIiAtcyBWIC1s
IHZlcnNpb24gLWQgJ1ByaW50IHZlcnNpb24nCmNvbXBsZXRlIC1jIGR1YSAtbiAiX19maXNoX2R1
YV9uZWVkc19jb21tYW5kIiAtYSAiaW50ZXJhY3RpdmUiIC1kICdMYXVuY2ggdGhlIHRlcm1pbmFs
IHVzZXIgaW50ZXJmYWNlJwpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfbmVlZHNfY29t
bWFuZCIgLWEgImkiIC1kICdMYXVuY2ggdGhlIHRlcm1pbmFsIHVzZXIgaW50ZXJmYWNlJwpjb21w
bGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfbmVlZHNfY29tbWFuZCIgLWEgImFnZ3JlZ2F0ZSIg
LWQgJ0FnZ3JlZ2F0ZSB0aGUgY29uc3VtZWQgc3BhY2Ugb2Ygb25lIG9yIG1vcmUgZGlyZWN0b3Jp
ZXMgb3IgZmlsZXMnCmNvbXBsZXRlIC1jIGR1YSAtbiAiX19maXNoX2R1YV9uZWVkc19jb21tYW5k
IiAtYSAiYSIgLWQgJ0FnZ3JlZ2F0ZSB0aGUgY29uc3VtZWQgc3BhY2Ugb2Ygb25lIG9yIG1vcmUg
ZGlyZWN0b3JpZXMgb3IgZmlsZXMnCmNvbXBsZXRlIC1jIGR1YSAtbiAiX19maXNoX2R1YV9uZWVk
c19jb21tYW5kIiAtYSAiY29tcGxldGlvbnMiIC1kICdHZW5lcmF0ZSBzaGVsbCBjb21wbGV0aW9u
cycKY29tcGxldGUgLWMgZHVhIC1uICJfX2Zpc2hfZHVhX25lZWRzX2NvbW1hbmQiIC1hICJoZWxw
IiAtZCAnUHJpbnQgdGhpcyBtZXNzYWdlIG9yIHRoZSBoZWxwIG9mIHRoZSBnaXZlbiBzdWJjb21t
YW5kKHMpJwpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfdXNpbmdfc3ViY29tbWFuZCBp
bnRlcmFjdGl2ZSIgLXMgZSAtbCBuby1lbnRyeS1jaGVjayAtZCAnRG8gbm90IGNoZWNrIGVudHJp
ZXMgZm9yIHByZXNlbmNlIHdoZW4gbGlzdGluZyBhIGRpcmVjdG9yeSB0byBhdm9pZCBzbHVnZ2lu
ZyBwZXJmb3JtYW5jZSBvbiBzbG93IGZpbGVzeXN0ZW1zJwpjb21wbGV0ZSAtYyBkdWEgLW4gIl9f
ZmlzaF9kdWFfdXNpbmdfc3ViY29tbWFuZCBpbnRlcmFjdGl2ZSIgLXMgaCAtbCBoZWxwIC1kICdQ
cmludCBoZWxwJwpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfdXNpbmdfc3ViY29tbWFu
ZCBpIiAtcyBlIC1sIG5vLWVudHJ5LWNoZWNrIC1kICdEbyBub3QgY2hlY2sgZW50cmllcyBmb3Ig
cHJlc2VuY2Ugd2hlbiBsaXN0aW5nIGEgZGlyZWN0b3J5IHRvIGF2b2lkIHNsdWdnaW5nIHBlcmZv
cm1hbmNlIG9uIHNsb3cgZmlsZXN5c3RlbXMnCmNvbXBsZXRlIC1jIGR1YSAtbiAiX19maXNoX2R1
YV91c2luZ19zdWJjb21tYW5kIGkiIC1zIGggLWwgaGVscCAtZCAnUHJpbnQgaGVscCcKY29tcGxl
dGUgLWMgZHVhIC1uICJfX2Zpc2hfZHVhX3VzaW5nX3N1YmNvbW1hbmQgYWdncmVnYXRlIiAtbCBz
dGF0cyAtZCAnSWYgc2V0LCBwcmludCBhZGRpdGlvbmFsIHN0YXRpc3RpY3MgYWJvdXQgdGhlIGZp
bGUgdHJhdmVyc2FsIHRvIHN0ZGVycicKY29tcGxldGUgLWMgZHVhIC1uICJfX2Zpc2hfZHVhX3Vz
aW5nX3N1YmNvbW1hbmQgYWdncmVnYXRlIiAtbCBuby1zb3J0IC1kICdJZiBzZXQsIHBhdGhzIHdp
bGwgYmUgcHJpbnRlZCBpbiB0aGVpciBvcmRlciBvZiBvY2N1cnJlbmNlIG9uIHRoZSBjb21tYW5k
LWxpbmUuIE90aGVyd2lzZSB0aGV5IGFyZSBzb3J0ZWQgYnkgdGhlaXIgc2l6ZSBpbiBieXRlcywg
YXNjZW5kaW5nJwpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfdXNpbmdfc3ViY29tbWFu
ZCBhZ2dyZWdhdGUiIC1sIG5vLXRvdGFsIC1kICdJZiBzZXQsIG5vIHRvdGFsIGNvbHVtbiB3aWxs
IGJlIGNvbXB1dGVkIGZvciBtdWx0aXBsZSBpbnB1dHMnCmNvbXBsZXRlIC1jIGR1YSAtbiAiX19m
aXNoX2R1YV91c2luZ19zdWJjb21tYW5kIGFnZ3JlZ2F0ZSIgLXMgaCAtbCBoZWxwIC1kICdQcmlu
dCBoZWxwJwpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfdXNpbmdfc3ViY29tbWFuZCBh
IiAtbCBzdGF0cyAtZCAnSWYgc2V0LCBwcmludCBhZGRpdGlvbmFsIHN0YXRpc3RpY3MgYWJvdXQg
dGhlIGZpbGUgdHJhdmVyc2FsIHRvIHN0ZGVycicKY29tcGxldGUgLWMgZHVhIC1uICJfX2Zpc2hf
ZHVhX3VzaW5nX3N1YmNvbW1hbmQgYSIgLWwgbm8tc29ydCAtZCAnSWYgc2V0LCBwYXRocyB3aWxs
IGJlIHByaW50ZWQgaW4gdGhlaXIgb3JkZXIgb2Ygb2NjdXJyZW5jZSBvbiB0aGUgY29tbWFuZC1s
aW5lLiBPdGhlcndpc2UgdGhleSBhcmUgc29ydGVkIGJ5IHRoZWlyIHNpemUgaW4gYnl0ZXMsIGFz
Y2VuZGluZycKY29tcGxldGUgLWMgZHVhIC1uICJfX2Zpc2hfZHVhX3VzaW5nX3N1YmNvbW1hbmQg
YSIgLWwgbm8tdG90YWwgLWQgJ0lmIHNldCwgbm8gdG90YWwgY29sdW1uIHdpbGwgYmUgY29tcHV0
ZWQgZm9yIG11bHRpcGxlIGlucHV0cycKY29tcGxldGUgLWMgZHVhIC1uICJfX2Zpc2hfZHVhX3Vz
aW5nX3N1YmNvbW1hbmQgYSIgLXMgaCAtbCBoZWxwIC1kICdQcmludCBoZWxwJwpjb21wbGV0ZSAt
YyBkdWEgLW4gIl9fZmlzaF9kdWFfdXNpbmdfc3ViY29tbWFuZCBjb21wbGV0aW9ucyIgLXMgaCAt
bCBoZWxwIC1kICdQcmludCBoZWxwJwpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlzaF9kdWFfdXNp
bmdfc3ViY29tbWFuZCBoZWxwOyBhbmQgbm90IF9fZmlzaF9zZWVuX3N1YmNvbW1hbmRfZnJvbSBp
bnRlcmFjdGl2ZSBhZ2dyZWdhdGUgY29tcGxldGlvbnMgaGVscCIgLWYgLWEgImludGVyYWN0aXZl
IiAtZCAnTGF1bmNoIHRoZSB0ZXJtaW5hbCB1c2VyIGludGVyZmFjZScKY29tcGxldGUgLWMgZHVh
IC1uICJfX2Zpc2hfZHVhX3VzaW5nX3N1YmNvbW1hbmQgaGVscDsgYW5kIG5vdCBfX2Zpc2hfc2Vl
bl9zdWJjb21tYW5kX2Zyb20gaW50ZXJhY3RpdmUgYWdncmVnYXRlIGNvbXBsZXRpb25zIGhlbHAi
IC1mIC1hICJhZ2dyZWdhdGUiIC1kICdBZ2dyZWdhdGUgdGhlIGNvbnN1bWVkIHNwYWNlIG9mIG9u
ZSBvciBtb3JlIGRpcmVjdG9yaWVzIG9yIGZpbGVzJwpjb21wbGV0ZSAtYyBkdWEgLW4gIl9fZmlz
aF9kdWFfdXNpbmdfc3ViY29tbWFuZCBoZWxwOyBhbmQgbm90IF9fZmlzaF9zZWVuX3N1YmNvbW1h
bmRfZnJvbSBpbnRlcmFjdGl2ZSBhZ2dyZWdhdGUgY29tcGxldGlvbnMgaGVscCIgLWYgLWEgImNv
bXBsZXRpb25zIiAtZCAnR2VuZXJhdGUgc2hlbGwgY29tcGxldGlvbnMnCmNvbXBsZXRlIC1jIGR1
YSAtbiAiX19maXNoX2R1YV91c2luZ19zdWJjb21tYW5kIGhlbHA7IGFuZCBub3QgX19maXNoX3Nl
ZW5fc3ViY29tbWFuZF9mcm9tIGludGVyYWN0aXZlIGFnZ3JlZ2F0ZSBjb21wbGV0aW9ucyBoZWxw
IiAtZiAtYSAiaGVscCIgLWQgJ1ByaW50IHRoaXMgbWVzc2FnZSBvciB0aGUgaGVscCBvZiB0aGUg
Z2l2ZW4gc3ViY29tbWFuZChzKScK
```

### `powershell` payload

```base64
CnVzaW5nIG5hbWVzcGFjZSBTeXN0ZW0uTWFuYWdlbWVudC5BdXRvbWF0aW9uCnVzaW5nIG5hbWVz
cGFjZSBTeXN0ZW0uTWFuYWdlbWVudC5BdXRvbWF0aW9uLkxhbmd1YWdlCgpSZWdpc3Rlci1Bcmd1
bWVudENvbXBsZXRlciAtTmF0aXZlIC1Db21tYW5kTmFtZSAnZHVhJyAtU2NyaXB0QmxvY2sgewog
ICAgcGFyYW0oJHdvcmRUb0NvbXBsZXRlLCAkY29tbWFuZEFzdCwgJGN1cnNvclBvc2l0aW9uKQoK
ICAgICRjb21tYW5kRWxlbWVudHMgPSAkY29tbWFuZEFzdC5Db21tYW5kRWxlbWVudHMKICAgICRj
b21tYW5kID0gQCgKICAgICAgICAnZHVhJwogICAgICAgIGZvciAoJGkgPSAxOyAkaSAtbHQgJGNv
bW1hbmRFbGVtZW50cy5Db3VudDsgJGkrKykgewogICAgICAgICAgICAkZWxlbWVudCA9ICRjb21t
YW5kRWxlbWVudHNbJGldCiAgICAgICAgICAgIGlmICgkZWxlbWVudCAtaXNub3QgW1N0cmluZ0Nv
bnN0YW50RXhwcmVzc2lvbkFzdF0gLW9yCiAgICAgICAgICAgICAgICAkZWxlbWVudC5TdHJpbmdD
b25zdGFudFR5cGUgLW5lIFtTdHJpbmdDb25zdGFudFR5cGVdOjpCYXJlV29yZCAtb3IKICAgICAg
ICAgICAgICAgICRlbGVtZW50LlZhbHVlLlN0YXJ0c1dpdGgoJy0nKSAtb3IKICAgICAgICAgICAg
ICAgICRlbGVtZW50LlZhbHVlIC1lcSAkd29yZFRvQ29tcGxldGUpIHsKICAgICAgICAgICAgICAg
IGJyZWFrCiAgICAgICAgfQogICAgICAgICRlbGVtZW50LlZhbHVlCiAgICB9KSAtam9pbiAnOycK
CiAgICAkY29tcGxldGlvbnMgPSBAKHN3aXRjaCAoJGNvbW1hbmQpIHsKICAgICAgICAnZHVhJyB7
CiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCctdCcsICctdCcsIFtDb21wbGV0
aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlck5hbWUsICdUaGUgYW1vdW50IG9mIHRocmVhZHMgdG8g
dXNlLiBEZWZhdWx0cyB0byAwLCBpbmRpY2F0aW5nIHRoZSBhbW91bnQgb2YgbG9naWNhbCBwcm9j
ZXNzb3JzLiBTZXQgdG8gMSB0byB1c2Ugb25seSBhIHNpbmdsZSB0aHJlYWQnKQogICAgICAgICAg
ICBbQ29tcGxldGlvblJlc3VsdF06Om5ldygnLS10aHJlYWRzJywgJy0tdGhyZWFkcycsIFtDb21w
bGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlck5hbWUsICdUaGUgYW1vdW50IG9mIHRocmVhZHMg
dG8gdXNlLiBEZWZhdWx0cyB0byAwLCBpbmRpY2F0aW5nIHRoZSBhbW91bnQgb2YgbG9naWNhbCBw
cm9jZXNzb3JzLiBTZXQgdG8gMSB0byB1c2Ugb25seSBhIHNpbmdsZSB0aHJlYWQnKQogICAgICAg
ICAgICBbQ29tcGxldGlvblJlc3VsdF06Om5ldygnLWYnLCAnLWYnLCBbQ29tcGxldGlvblJlc3Vs
dFR5cGVdOjpQYXJhbWV0ZXJOYW1lLCAnVGhlIGZvcm1hdCB3aXRoIHdoaWNoIHRvIHByaW50IGJ5
dGUgY291bnRzJykKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy0tZm9ybWF0
JywgJy0tZm9ybWF0JywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVyTmFtZSwgJ1Ro
ZSBmb3JtYXQgd2l0aCB3aGljaCB0byBwcmludCBieXRlIGNvdW50cycpCiAgICAgICAgICAgIFtD
b21wbGV0aW9uUmVzdWx0XTo6bmV3KCctaScsICctaScsIFtDb21wbGV0aW9uUmVzdWx0VHlwZV06
OlBhcmFtZXRlck5hbWUsICdPbmUgb3IgbW9yZSBhYnNvbHV0ZSBkaXJlY3RvcmllcyB0byBpZ25v
cmUuIE5vdGUgdGhhdCB0aGVzZSBhcmUgbm90IGlnbm9yZWQgaWYgdGhleSBhcmUgcGFzc2VkIGFz
IGlucHV0IHBhdGgnKQogICAgICAgICAgICBbQ29tcGxldGlvblJlc3VsdF06Om5ldygnLS1pZ25v
cmUtZGlycycsICctLWlnbm9yZS1kaXJzJywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1l
dGVyTmFtZSwgJ09uZSBvciBtb3JlIGFic29sdXRlIGRpcmVjdG9yaWVzIHRvIGlnbm9yZS4gTm90
ZSB0aGF0IHRoZXNlIGFyZSBub3QgaWdub3JlZCBpZiB0aGV5IGFyZSBwYXNzZWQgYXMgaW5wdXQg
cGF0aCcpCiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCctLWxvZy1maWxlJywg
Jy0tbG9nLWZpbGUnLCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0ZXJOYW1lLCAnV3Jp
dGUgYSBsb2cgZmlsZSB3aXRoIGRlYnVnIGluZm9ybWF0aW9uLCBpbmNsdWRpbmcgcGFuaWNzJykK
ICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy1BJywgJy1BICcsIFtDb21wbGV0
aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlck5hbWUsICdEaXNwbGF5IGFwcGFyZW50IHNpemUgaW5z
dGVhZCBvZiBkaXNrIHVzYWdlJykKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXco
Jy0tYXBwYXJlbnQtc2l6ZScsICctLWFwcGFyZW50LXNpemUnLCBbQ29tcGxldGlvblJlc3VsdFR5
cGVdOjpQYXJhbWV0ZXJOYW1lLCAnRGlzcGxheSBhcHBhcmVudCBzaXplIGluc3RlYWQgb2YgZGlz
ayB1c2FnZScpCiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCctbCcsICctbCcs
IFtDb21wbGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlck5hbWUsICdDb3VudCBoYXJkLWxpbmtl
ZCBmaWxlcyBlYWNoIHRpbWUgdGhleSBhcmUgc2VlbicpCiAgICAgICAgICAgIFtDb21wbGV0aW9u
UmVzdWx0XTo6bmV3KCctLWNvdW50LWhhcmQtbGlua3MnLCAnLS1jb3VudC1oYXJkLWxpbmtzJywg
W0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVyTmFtZSwgJ0NvdW50IGhhcmQtbGlua2Vk
IGZpbGVzIGVhY2ggdGltZSB0aGV5IGFyZSBzZWVuJykKICAgICAgICAgICAgW0NvbXBsZXRpb25S
ZXN1bHRdOjpuZXcoJy14JywgJy14JywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVy
TmFtZSwgJ0lmIHNldCwgd2Ugd2lsbCBub3QgY3Jvc3MgZmlsZXN5c3RlbXMgb3IgdHJhdmVyc2Ug
bW91bnQgcG9pbnRzJykKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy0tc3Rh
eS1vbi1maWxlc3lzdGVtJywgJy0tc3RheS1vbi1maWxlc3lzdGVtJywgW0NvbXBsZXRpb25SZXN1
bHRUeXBlXTo6UGFyYW1ldGVyTmFtZSwgJ0lmIHNldCwgd2Ugd2lsbCBub3QgY3Jvc3MgZmlsZXN5
c3RlbXMgb3IgdHJhdmVyc2UgbW91bnQgcG9pbnRzJykKICAgICAgICAgICAgW0NvbXBsZXRpb25S
ZXN1bHRdOjpuZXcoJy1oJywgJy1oJywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVy
TmFtZSwgJ1ByaW50IGhlbHAgKHNlZSBtb3JlIHdpdGggJyctLWhlbHAnJyknKQogICAgICAgICAg
ICBbQ29tcGxldGlvblJlc3VsdF06Om5ldygnLS1oZWxwJywgJy0taGVscCcsIFtDb21wbGV0aW9u
UmVzdWx0VHlwZV06OlBhcmFtZXRlck5hbWUsICdQcmludCBoZWxwIChzZWUgbW9yZSB3aXRoICcn
LS1oZWxwJycpJykKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy1WJywgJy1W
ICcsIFtDb21wbGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlck5hbWUsICdQcmludCB2ZXJzaW9u
JykKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy0tdmVyc2lvbicsICctLXZl
cnNpb24nLCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0ZXJOYW1lLCAnUHJpbnQgdmVy
c2lvbicpCiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCdpbnRlcmFjdGl2ZScs
ICdpbnRlcmFjdGl2ZScsIFtDb21wbGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlclZhbHVlLCAn
TGF1bmNoIHRoZSB0ZXJtaW5hbCB1c2VyIGludGVyZmFjZScpCiAgICAgICAgICAgIFtDb21wbGV0
aW9uUmVzdWx0XTo6bmV3KCdpJywgJ2knLCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0
ZXJWYWx1ZSwgJ0xhdW5jaCB0aGUgdGVybWluYWwgdXNlciBpbnRlcmZhY2UnKQogICAgICAgICAg
ICBbQ29tcGxldGlvblJlc3VsdF06Om5ldygnYWdncmVnYXRlJywgJ2FnZ3JlZ2F0ZScsIFtDb21w
bGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlclZhbHVlLCAnQWdncmVnYXRlIHRoZSBjb25zdW1l
ZCBzcGFjZSBvZiBvbmUgb3IgbW9yZSBkaXJlY3RvcmllcyBvciBmaWxlcycpCiAgICAgICAgICAg
IFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCdhJywgJ2EnLCBbQ29tcGxldGlvblJlc3VsdFR5cGVd
OjpQYXJhbWV0ZXJWYWx1ZSwgJ0FnZ3JlZ2F0ZSB0aGUgY29uc3VtZWQgc3BhY2Ugb2Ygb25lIG9y
IG1vcmUgZGlyZWN0b3JpZXMgb3IgZmlsZXMnKQogICAgICAgICAgICBbQ29tcGxldGlvblJlc3Vs
dF06Om5ldygnY29tcGxldGlvbnMnLCAnY29tcGxldGlvbnMnLCBbQ29tcGxldGlvblJlc3VsdFR5
cGVdOjpQYXJhbWV0ZXJWYWx1ZSwgJ0dlbmVyYXRlIHNoZWxsIGNvbXBsZXRpb25zJykKICAgICAg
ICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJ2hlbHAnLCAnaGVscCcsIFtDb21wbGV0aW9u
UmVzdWx0VHlwZV06OlBhcmFtZXRlclZhbHVlLCAnUHJpbnQgdGhpcyBtZXNzYWdlIG9yIHRoZSBo
ZWxwIG9mIHRoZSBnaXZlbiBzdWJjb21tYW5kKHMpJykKICAgICAgICAgICAgYnJlYWsKICAgICAg
ICB9CiAgICAgICAgJ2R1YTtpbnRlcmFjdGl2ZScgewogICAgICAgICAgICBbQ29tcGxldGlvblJl
c3VsdF06Om5ldygnLWUnLCAnLWUnLCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0ZXJO
YW1lLCAnRG8gbm90IGNoZWNrIGVudHJpZXMgZm9yIHByZXNlbmNlIHdoZW4gbGlzdGluZyBhIGRp
cmVjdG9yeSB0byBhdm9pZCBzbHVnZ2luZyBwZXJmb3JtYW5jZSBvbiBzbG93IGZpbGVzeXN0ZW1z
JykKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy0tbm8tZW50cnktY2hlY2sn
LCAnLS1uby1lbnRyeS1jaGVjaycsIFtDb21wbGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlck5h
bWUsICdEbyBub3QgY2hlY2sgZW50cmllcyBmb3IgcHJlc2VuY2Ugd2hlbiBsaXN0aW5nIGEgZGly
ZWN0b3J5IHRvIGF2b2lkIHNsdWdnaW5nIHBlcmZvcm1hbmNlIG9uIHNsb3cgZmlsZXN5c3RlbXMn
KQogICAgICAgICAgICBbQ29tcGxldGlvblJlc3VsdF06Om5ldygnLWgnLCAnLWgnLCBbQ29tcGxl
dGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0ZXJOYW1lLCAnUHJpbnQgaGVscCcpCiAgICAgICAgICAg
IFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCctLWhlbHAnLCAnLS1oZWxwJywgW0NvbXBsZXRpb25S
ZXN1bHRUeXBlXTo6UGFyYW1ldGVyTmFtZSwgJ1ByaW50IGhlbHAnKQogICAgICAgICAgICBicmVh
awogICAgICAgIH0KICAgICAgICAnZHVhO2knIHsKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1
bHRdOjpuZXcoJy1lJywgJy1lJywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVyTmFt
ZSwgJ0RvIG5vdCBjaGVjayBlbnRyaWVzIGZvciBwcmVzZW5jZSB3aGVuIGxpc3RpbmcgYSBkaXJl
Y3RvcnkgdG8gYXZvaWQgc2x1Z2dpbmcgcGVyZm9ybWFuY2Ugb24gc2xvdyBmaWxlc3lzdGVtcycp
CiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCctLW5vLWVudHJ5LWNoZWNrJywg
Jy0tbm8tZW50cnktY2hlY2snLCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0ZXJOYW1l
LCAnRG8gbm90IGNoZWNrIGVudHJpZXMgZm9yIHByZXNlbmNlIHdoZW4gbGlzdGluZyBhIGRpcmVj
dG9yeSB0byBhdm9pZCBzbHVnZ2luZyBwZXJmb3JtYW5jZSBvbiBzbG93IGZpbGVzeXN0ZW1zJykK
ICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy1oJywgJy1oJywgW0NvbXBsZXRp
b25SZXN1bHRUeXBlXTo6UGFyYW1ldGVyTmFtZSwgJ1ByaW50IGhlbHAnKQogICAgICAgICAgICBb
Q29tcGxldGlvblJlc3VsdF06Om5ldygnLS1oZWxwJywgJy0taGVscCcsIFtDb21wbGV0aW9uUmVz
dWx0VHlwZV06OlBhcmFtZXRlck5hbWUsICdQcmludCBoZWxwJykKICAgICAgICAgICAgYnJlYWsK
ICAgICAgICB9CiAgICAgICAgJ2R1YTthZ2dyZWdhdGUnIHsKICAgICAgICAgICAgW0NvbXBsZXRp
b25SZXN1bHRdOjpuZXcoJy0tc3RhdHMnLCAnLS1zdGF0cycsIFtDb21wbGV0aW9uUmVzdWx0VHlw
ZV06OlBhcmFtZXRlck5hbWUsICdJZiBzZXQsIHByaW50IGFkZGl0aW9uYWwgc3RhdGlzdGljcyBh
Ym91dCB0aGUgZmlsZSB0cmF2ZXJzYWwgdG8gc3RkZXJyJykKICAgICAgICAgICAgW0NvbXBsZXRp
b25SZXN1bHRdOjpuZXcoJy0tbm8tc29ydCcsICctLW5vLXNvcnQnLCBbQ29tcGxldGlvblJlc3Vs
dFR5cGVdOjpQYXJhbWV0ZXJOYW1lLCAnSWYgc2V0LCBwYXRocyB3aWxsIGJlIHByaW50ZWQgaW4g
dGhlaXIgb3JkZXIgb2Ygb2NjdXJyZW5jZSBvbiB0aGUgY29tbWFuZC1saW5lLiBPdGhlcndpc2Ug
dGhleSBhcmUgc29ydGVkIGJ5IHRoZWlyIHNpemUgaW4gYnl0ZXMsIGFzY2VuZGluZycpCiAgICAg
ICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCctLW5vLXRvdGFsJywgJy0tbm8tdG90YWwn
LCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0ZXJOYW1lLCAnSWYgc2V0LCBubyB0b3Rh
bCBjb2x1bW4gd2lsbCBiZSBjb21wdXRlZCBmb3IgbXVsdGlwbGUgaW5wdXRzJykKICAgICAgICAg
ICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy1oJywgJy1oJywgW0NvbXBsZXRpb25SZXN1bHRU
eXBlXTo6UGFyYW1ldGVyTmFtZSwgJ1ByaW50IGhlbHAnKQogICAgICAgICAgICBbQ29tcGxldGlv
blJlc3VsdF06Om5ldygnLS1oZWxwJywgJy0taGVscCcsIFtDb21wbGV0aW9uUmVzdWx0VHlwZV06
OlBhcmFtZXRlck5hbWUsICdQcmludCBoZWxwJykKICAgICAgICAgICAgYnJlYWsKICAgICAgICB9
CiAgICAgICAgJ2R1YTthJyB7CiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCct
LXN0YXRzJywgJy0tc3RhdHMnLCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0ZXJOYW1l
LCAnSWYgc2V0LCBwcmludCBhZGRpdGlvbmFsIHN0YXRpc3RpY3MgYWJvdXQgdGhlIGZpbGUgdHJh
dmVyc2FsIHRvIHN0ZGVycicpCiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCct
LW5vLXNvcnQnLCAnLS1uby1zb3J0JywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVy
TmFtZSwgJ0lmIHNldCwgcGF0aHMgd2lsbCBiZSBwcmludGVkIGluIHRoZWlyIG9yZGVyIG9mIG9j
Y3VycmVuY2Ugb24gdGhlIGNvbW1hbmQtbGluZS4gT3RoZXJ3aXNlIHRoZXkgYXJlIHNvcnRlZCBi
eSB0aGVpciBzaXplIGluIGJ5dGVzLCBhc2NlbmRpbmcnKQogICAgICAgICAgICBbQ29tcGxldGlv
blJlc3VsdF06Om5ldygnLS1uby10b3RhbCcsICctLW5vLXRvdGFsJywgW0NvbXBsZXRpb25SZXN1
bHRUeXBlXTo6UGFyYW1ldGVyTmFtZSwgJ0lmIHNldCwgbm8gdG90YWwgY29sdW1uIHdpbGwgYmUg
Y29tcHV0ZWQgZm9yIG11bHRpcGxlIGlucHV0cycpCiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVz
dWx0XTo6bmV3KCctaCcsICctaCcsIFtDb21wbGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlck5h
bWUsICdQcmludCBoZWxwJykKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy0t
aGVscCcsICctLWhlbHAnLCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQYXJhbWV0ZXJOYW1lLCAn
UHJpbnQgaGVscCcpCiAgICAgICAgICAgIGJyZWFrCiAgICAgICAgfQogICAgICAgICdkdWE7Y29t
cGxldGlvbnMnIHsKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJy1oJywgJy1o
JywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVyTmFtZSwgJ1ByaW50IGhlbHAnKQog
ICAgICAgICAgICBbQ29tcGxldGlvblJlc3VsdF06Om5ldygnLS1oZWxwJywgJy0taGVscCcsIFtD
b21wbGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlck5hbWUsICdQcmludCBoZWxwJykKICAgICAg
ICAgICAgYnJlYWsKICAgICAgICB9CiAgICAgICAgJ2R1YTtoZWxwJyB7CiAgICAgICAgICAgIFtD
b21wbGV0aW9uUmVzdWx0XTo6bmV3KCdpbnRlcmFjdGl2ZScsICdpbnRlcmFjdGl2ZScsIFtDb21w
bGV0aW9uUmVzdWx0VHlwZV06OlBhcmFtZXRlclZhbHVlLCAnTGF1bmNoIHRoZSB0ZXJtaW5hbCB1
c2VyIGludGVyZmFjZScpCiAgICAgICAgICAgIFtDb21wbGV0aW9uUmVzdWx0XTo6bmV3KCdhZ2dy
ZWdhdGUnLCAnYWdncmVnYXRlJywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVyVmFs
dWUsICdBZ2dyZWdhdGUgdGhlIGNvbnN1bWVkIHNwYWNlIG9mIG9uZSBvciBtb3JlIGRpcmVjdG9y
aWVzIG9yIGZpbGVzJykKICAgICAgICAgICAgW0NvbXBsZXRpb25SZXN1bHRdOjpuZXcoJ2NvbXBs
ZXRpb25zJywgJ2NvbXBsZXRpb25zJywgW0NvbXBsZXRpb25SZXN1bHRUeXBlXTo6UGFyYW1ldGVy
VmFsdWUsICdHZW5lcmF0ZSBzaGVsbCBjb21wbGV0aW9ucycpCiAgICAgICAgICAgIFtDb21wbGV0
aW9uUmVzdWx0XTo6bmV3KCdoZWxwJywgJ2hlbHAnLCBbQ29tcGxldGlvblJlc3VsdFR5cGVdOjpQ
YXJhbWV0ZXJWYWx1ZSwgJ1ByaW50IHRoaXMgbWVzc2FnZSBvciB0aGUgaGVscCBvZiB0aGUgZ2l2
ZW4gc3ViY29tbWFuZChzKScpCiAgICAgICAgICAgIGJyZWFrCiAgICAgICAgfQogICAgICAgICdk
dWE7aGVscDtpbnRlcmFjdGl2ZScgewogICAgICAgICAgICBicmVhawogICAgICAgIH0KICAgICAg
ICAnZHVhO2hlbHA7YWdncmVnYXRlJyB7CiAgICAgICAgICAgIGJyZWFrCiAgICAgICAgfQogICAg
ICAgICdkdWE7aGVscDtjb21wbGV0aW9ucycgewogICAgICAgICAgICBicmVhawogICAgICAgIH0K
ICAgICAgICAnZHVhO2hlbHA7aGVscCcgewogICAgICAgICAgICBicmVhawogICAgICAgIH0KICAg
IH0pCgogICAgJGNvbXBsZXRpb25zLldoZXJleyAkXy5Db21wbGV0aW9uVGV4dCAtbGlrZSAiJHdv
cmRUb0NvbXBsZXRlKiIgfSB8CiAgICAgICAgU29ydC1PYmplY3QgLVByb3BlcnR5IExpc3RJdGVt
VGV4dAp9Cg==
```

### `zsh` payload

```base64
I2NvbXBkZWYgZHVhCgphdXRvbG9hZCAtVSBpcy1hdC1sZWFzdAoKX2R1YSgpIHsKICAgIHR5cGVz
ZXQgLUEgb3B0X2FyZ3MKICAgIHR5cGVzZXQgLWEgX2FyZ3VtZW50c19vcHRpb25zCiAgICBsb2Nh
bCByZXQ9MQoKICAgIGlmIGlzLWF0LWxlYXN0IDUuMjsgdGhlbgogICAgICAgIF9hcmd1bWVudHNf
b3B0aW9ucz0oLXMgLVMgLUMpCiAgICBlbHNlCiAgICAgICAgX2FyZ3VtZW50c19vcHRpb25zPSgt
cyAtQykKICAgIGZpCgogICAgbG9jYWwgY29udGV4dCBjdXJjb250ZXh0PSIkY3VyY29udGV4dCIg
c3RhdGUgbGluZQogICAgX2FyZ3VtZW50cyAiJHtfYXJndW1lbnRzX29wdGlvbnNbQF19IiA6IFwK
Jy10K1tUaGUgYW1vdW50IG9mIHRocmVhZHMgdG8gdXNlLiBEZWZhdWx0cyB0byAwLCBpbmRpY2F0
aW5nIHRoZSBhbW91bnQgb2YgbG9naWNhbCBwcm9jZXNzb3JzLiBTZXQgdG8gMSB0byB1c2Ugb25s
eSBhIHNpbmdsZSB0aHJlYWRdOlRIUkVBRFM6X2RlZmF1bHQnIFwKJy0tdGhyZWFkcz1bVGhlIGFt
b3VudCBvZiB0aHJlYWRzIHRvIHVzZS4gRGVmYXVsdHMgdG8gMCwgaW5kaWNhdGluZyB0aGUgYW1v
dW50IG9mIGxvZ2ljYWwgcHJvY2Vzc29ycy4gU2V0IHRvIDEgdG8gdXNlIG9ubHkgYSBzaW5nbGUg
dGhyZWFkXTpUSFJFQURTOl9kZWZhdWx0JyBcCictZitbVGhlIGZvcm1hdCB3aXRoIHdoaWNoIHRv
IHByaW50IGJ5dGUgY291bnRzXTpGT1JNQVQ6KG1ldHJpYyBiaW5hcnkgYnl0ZXMgZ2IgZ2liIG1i
IG1pYiknIFwKJy0tZm9ybWF0PVtUaGUgZm9ybWF0IHdpdGggd2hpY2ggdG8gcHJpbnQgYnl0ZSBj
b3VudHNdOkZPUk1BVDoobWV0cmljIGJpbmFyeSBieXRlcyBnYiBnaWIgbWIgbWliKScgXAonKi1p
K1tPbmUgb3IgbW9yZSBhYnNvbHV0ZSBkaXJlY3RvcmllcyB0byBpZ25vcmUuIE5vdGUgdGhhdCB0
aGVzZSBhcmUgbm90IGlnbm9yZWQgaWYgdGhleSBhcmUgcGFzc2VkIGFzIGlucHV0IHBhdGhdOklH
Tk9SRV9ESVJTOl9maWxlcycgXAonKi0taWdub3JlLWRpcnM9W09uZSBvciBtb3JlIGFic29sdXRl
IGRpcmVjdG9yaWVzIHRvIGlnbm9yZS4gTm90ZSB0aGF0IHRoZXNlIGFyZSBub3QgaWdub3JlZCBp
ZiB0aGV5IGFyZSBwYXNzZWQgYXMgaW5wdXQgcGF0aF06SUdOT1JFX0RJUlM6X2ZpbGVzJyBcCict
LWxvZy1maWxlPVtXcml0ZSBhIGxvZyBmaWxlIHdpdGggZGVidWcgaW5mb3JtYXRpb24sIGluY2x1
ZGluZyBwYW5pY3NdOkxPR19GSUxFOl9maWxlcycgXAonLUFbRGlzcGxheSBhcHBhcmVudCBzaXpl
IGluc3RlYWQgb2YgZGlzayB1c2FnZV0nIFwKJy0tYXBwYXJlbnQtc2l6ZVtEaXNwbGF5IGFwcGFy
ZW50IHNpemUgaW5zdGVhZCBvZiBkaXNrIHVzYWdlXScgXAonLWxbQ291bnQgaGFyZC1saW5rZWQg
ZmlsZXMgZWFjaCB0aW1lIHRoZXkgYXJlIHNlZW5dJyBcCictLWNvdW50LWhhcmQtbGlua3NbQ291
bnQgaGFyZC1saW5rZWQgZmlsZXMgZWFjaCB0aW1lIHRoZXkgYXJlIHNlZW5dJyBcCicteFtJZiBz
ZXQsIHdlIHdpbGwgbm90IGNyb3NzIGZpbGVzeXN0ZW1zIG9yIHRyYXZlcnNlIG1vdW50IHBvaW50
c10nIFwKJy0tc3RheS1vbi1maWxlc3lzdGVtW0lmIHNldCwgd2Ugd2lsbCBub3QgY3Jvc3MgZmls
ZXN5c3RlbXMgb3IgdHJhdmVyc2UgbW91bnQgcG9pbnRzXScgXAonLWhbUHJpbnQgaGVscCAoc2Vl
IG1vcmUgd2l0aCAnXCcnLS1oZWxwJ1wnJyldJyBcCictLWhlbHBbUHJpbnQgaGVscCAoc2VlIG1v
cmUgd2l0aCAnXCcnLS1oZWxwJ1wnJyldJyBcCictVltQcmludCB2ZXJzaW9uXScgXAonLS12ZXJz
aW9uW1ByaW50IHZlcnNpb25dJyBcCic6OmlucHV0IC0tIE9uZSBvciBtb3JlIGlucHV0IGZpbGVz
IG9yIGRpcmVjdG9yaWVzLiBJZiB1bnNldCwgd2Ugd2lsbCB1c2UgYWxsIGVudHJpZXMgaW4gdGhl
IGN1cnJlbnQgd29ya2luZyBkaXJlY3Rvcnk6X2ZpbGVzJyBcCiI6OiA6X2R1YV9jb21tYW5kcyIg
XAoiKjo6OiA6LT5kdWEiIFwKJiYgcmV0PTAKICAgIGNhc2UgJHN0YXRlIGluCiAgICAoZHVhKQog
ICAgICAgIHdvcmRzPSgkbGluZVsyXSAiJHt3b3Jkc1tAXX0iKQogICAgICAgICgoIENVUlJFTlQg
Kz0gMSApKQogICAgICAgIGN1cmNvbnRleHQ9IiR7Y3VyY29udGV4dCU6KjoqfTpkdWEtY29tbWFu
ZC0kbGluZVsyXToiCiAgICAgICAgY2FzZSAkbGluZVsyXSBpbgogICAgICAgICAgICAoaW50ZXJh
Y3RpdmUpCl9hcmd1bWVudHMgIiR7X2FyZ3VtZW50c19vcHRpb25zW0BdfSIgOiBcCictZVtEbyBu
b3QgY2hlY2sgZW50cmllcyBmb3IgcHJlc2VuY2Ugd2hlbiBsaXN0aW5nIGEgZGlyZWN0b3J5IHRv
IGF2b2lkIHNsdWdnaW5nIHBlcmZvcm1hbmNlIG9uIHNsb3cgZmlsZXN5c3RlbXNdJyBcCictLW5v
LWVudHJ5LWNoZWNrW0RvIG5vdCBjaGVjayBlbnRyaWVzIGZvciBwcmVzZW5jZSB3aGVuIGxpc3Rp
bmcgYSBkaXJlY3RvcnkgdG8gYXZvaWQgc2x1Z2dpbmcgcGVyZm9ybWFuY2Ugb24gc2xvdyBmaWxl
c3lzdGVtc10nIFwKJy1oW1ByaW50IGhlbHBdJyBcCictLWhlbHBbUHJpbnQgaGVscF0nIFwKJyo6
OmlucHV0IC0tIE9uZSBvciBtb3JlIGlucHV0IGZpbGVzIG9yIGRpcmVjdG9yaWVzLiBJZiB1bnNl
dCwgd2Ugd2lsbCB1c2UgYWxsIGVudHJpZXMgaW4gdGhlIGN1cnJlbnQgd29ya2luZyBkaXJlY3Rv
cnk6X2ZpbGVzJyBcCiYmIHJldD0wCjs7CihpKQpfYXJndW1lbnRzICIke19hcmd1bWVudHNfb3B0
aW9uc1tAXX0iIDogXAonLWVbRG8gbm90IGNoZWNrIGVudHJpZXMgZm9yIHByZXNlbmNlIHdoZW4g
bGlzdGluZyBhIGRpcmVjdG9yeSB0byBhdm9pZCBzbHVnZ2luZyBwZXJmb3JtYW5jZSBvbiBzbG93
IGZpbGVzeXN0ZW1zXScgXAonLS1uby1lbnRyeS1jaGVja1tEbyBub3QgY2hlY2sgZW50cmllcyBm
b3IgcHJlc2VuY2Ugd2hlbiBsaXN0aW5nIGEgZGlyZWN0b3J5IHRvIGF2b2lkIHNsdWdnaW5nIHBl
cmZvcm1hbmNlIG9uIHNsb3cgZmlsZXN5c3RlbXNdJyBcCictaFtQcmludCBoZWxwXScgXAonLS1o
ZWxwW1ByaW50IGhlbHBdJyBcCicqOjppbnB1dCAtLSBPbmUgb3IgbW9yZSBpbnB1dCBmaWxlcyBv
ciBkaXJlY3Rvcmllcy4gSWYgdW5zZXQsIHdlIHdpbGwgdXNlIGFsbCBlbnRyaWVzIGluIHRoZSBj
dXJyZW50IHdvcmtpbmcgZGlyZWN0b3J5Ol9maWxlcycgXAomJiByZXQ9MAo7OwooYWdncmVnYXRl
KQpfYXJndW1lbnRzICIke19hcmd1bWVudHNfb3B0aW9uc1tAXX0iIDogXAonLS1zdGF0c1tJZiBz
ZXQsIHByaW50IGFkZGl0aW9uYWwgc3RhdGlzdGljcyBhYm91dCB0aGUgZmlsZSB0cmF2ZXJzYWwg
dG8gc3RkZXJyXScgXAonLS1uby1zb3J0W0lmIHNldCwgcGF0aHMgd2lsbCBiZSBwcmludGVkIGlu
IHRoZWlyIG9yZGVyIG9mIG9jY3VycmVuY2Ugb24gdGhlIGNvbW1hbmQtbGluZS4gT3RoZXJ3aXNl
IHRoZXkgYXJlIHNvcnRlZCBieSB0aGVpciBzaXplIGluIGJ5dGVzLCBhc2NlbmRpbmddJyBcCict
LW5vLXRvdGFsW0lmIHNldCwgbm8gdG90YWwgY29sdW1uIHdpbGwgYmUgY29tcHV0ZWQgZm9yIG11
bHRpcGxlIGlucHV0c10nIFwKJy1oW1ByaW50IGhlbHBdJyBcCictLWhlbHBbUHJpbnQgaGVscF0n
IFwKJyo6OmlucHV0IC0tIE9uZSBvciBtb3JlIGlucHV0IGZpbGVzIG9yIGRpcmVjdG9yaWVzLiBJ
ZiB1bnNldCwgd2Ugd2lsbCB1c2UgYWxsIGVudHJpZXMgaW4gdGhlIGN1cnJlbnQgd29ya2luZyBk
aXJlY3Rvcnk6X2ZpbGVzJyBcCiYmIHJldD0wCjs7CihhKQpfYXJndW1lbnRzICIke19hcmd1bWVu
dHNfb3B0aW9uc1tAXX0iIDogXAonLS1zdGF0c1tJZiBzZXQsIHByaW50IGFkZGl0aW9uYWwgc3Rh
dGlzdGljcyBhYm91dCB0aGUgZmlsZSB0cmF2ZXJzYWwgdG8gc3RkZXJyXScgXAonLS1uby1zb3J0
W0lmIHNldCwgcGF0aHMgd2lsbCBiZSBwcmludGVkIGluIHRoZWlyIG9yZGVyIG9mIG9jY3VycmVu
Y2Ugb24gdGhlIGNvbW1hbmQtbGluZS4gT3RoZXJ3aXNlIHRoZXkgYXJlIHNvcnRlZCBieSB0aGVp
ciBzaXplIGluIGJ5dGVzLCBhc2NlbmRpbmddJyBcCictLW5vLXRvdGFsW0lmIHNldCwgbm8gdG90
YWwgY29sdW1uIHdpbGwgYmUgY29tcHV0ZWQgZm9yIG11bHRpcGxlIGlucHV0c10nIFwKJy1oW1By
aW50IGhlbHBdJyBcCictLWhlbHBbUHJpbnQgaGVscF0nIFwKJyo6OmlucHV0IC0tIE9uZSBvciBt
b3JlIGlucHV0IGZpbGVzIG9yIGRpcmVjdG9yaWVzLiBJZiB1bnNldCwgd2Ugd2lsbCB1c2UgYWxs
IGVudHJpZXMgaW4gdGhlIGN1cnJlbnQgd29ya2luZyBkaXJlY3Rvcnk6X2ZpbGVzJyBcCiYmIHJl
dD0wCjs7Cihjb21wbGV0aW9ucykKX2FyZ3VtZW50cyAiJHtfYXJndW1lbnRzX29wdGlvbnNbQF19
IiA6IFwKJy1oW1ByaW50IGhlbHBdJyBcCictLWhlbHBbUHJpbnQgaGVscF0nIFwKJzpzaGVsbCAt
LSBUaGUgc2hlbGwgdG8gZ2VuZXJhdGUgYSBjb21wbGV0aW9ucy1zY3JpcHQgZm9yOihiYXNoIGVs
dmlzaCBmaXNoIHBvd2Vyc2hlbGwgenNoKScgXAomJiByZXQ9MAo7OwooaGVscCkKX2FyZ3VtZW50
cyAiJHtfYXJndW1lbnRzX29wdGlvbnNbQF19IiA6IFwKIjo6IDpfZHVhX19oZWxwX2NvbW1hbmRz
IiBcCiIqOjo6IDotPmhlbHAiIFwKJiYgcmV0PTAKCiAgICBjYXNlICRzdGF0ZSBpbgogICAgKGhl
bHApCiAgICAgICAgd29yZHM9KCRsaW5lWzFdICIke3dvcmRzW0BdfSIpCiAgICAgICAgKCggQ1VS
UkVOVCArPSAxICkpCiAgICAgICAgY3VyY29udGV4dD0iJHtjdXJjb250ZXh0JToqOip9OmR1YS1o
ZWxwLWNvbW1hbmQtJGxpbmVbMV06IgogICAgICAgIGNhc2UgJGxpbmVbMV0gaW4KICAgICAgICAg
ICAgKGludGVyYWN0aXZlKQpfYXJndW1lbnRzICIke19hcmd1bWVudHNfb3B0aW9uc1tAXX0iIDog
XAomJiByZXQ9MAo7OwooYWdncmVnYXRlKQpfYXJndW1lbnRzICIke19hcmd1bWVudHNfb3B0aW9u
c1tAXX0iIDogXAomJiByZXQ9MAo7OwooY29tcGxldGlvbnMpCl9hcmd1bWVudHMgIiR7X2FyZ3Vt
ZW50c19vcHRpb25zW0BdfSIgOiBcCiYmIHJldD0wCjs7CihoZWxwKQpfYXJndW1lbnRzICIke19h
cmd1bWVudHNfb3B0aW9uc1tAXX0iIDogXAomJiByZXQ9MAo7OwogICAgICAgIGVzYWMKICAgIDs7
CmVzYWMKOzsKICAgICAgICBlc2FjCiAgICA7Owplc2FjCn0KCigoICQrZnVuY3Rpb25zW19kdWFf
Y29tbWFuZHNdICkpIHx8Cl9kdWFfY29tbWFuZHMoKSB7CiAgICBsb2NhbCBjb21tYW5kczsgY29t
bWFuZHM9KAonaW50ZXJhY3RpdmU6TGF1bmNoIHRoZSB0ZXJtaW5hbCB1c2VyIGludGVyZmFjZScg
XAonaTpMYXVuY2ggdGhlIHRlcm1pbmFsIHVzZXIgaW50ZXJmYWNlJyBcCidhZ2dyZWdhdGU6QWdn
cmVnYXRlIHRoZSBjb25zdW1lZCBzcGFjZSBvZiBvbmUgb3IgbW9yZSBkaXJlY3RvcmllcyBvciBm
aWxlcycgXAonYTpBZ2dyZWdhdGUgdGhlIGNvbnN1bWVkIHNwYWNlIG9mIG9uZSBvciBtb3JlIGRp
cmVjdG9yaWVzIG9yIGZpbGVzJyBcCidjb21wbGV0aW9uczpHZW5lcmF0ZSBzaGVsbCBjb21wbGV0
aW9ucycgXAonaGVscDpQcmludCB0aGlzIG1lc3NhZ2Ugb3IgdGhlIGhlbHAgb2YgdGhlIGdpdmVu
IHN1YmNvbW1hbmQocyknIFwKICAgICkKICAgIF9kZXNjcmliZSAtdCBjb21tYW5kcyAnZHVhIGNv
bW1hbmRzJyBjb21tYW5kcyAiJEAiCn0KKCggJCtmdW5jdGlvbnNbX2R1YV9fYWdncmVnYXRlX2Nv
bW1hbmRzXSApKSB8fApfZHVhX19hZ2dyZWdhdGVfY29tbWFuZHMoKSB7CiAgICBsb2NhbCBjb21t
YW5kczsgY29tbWFuZHM9KCkKICAgIF9kZXNjcmliZSAtdCBjb21tYW5kcyAnZHVhIGFnZ3JlZ2F0
ZSBjb21tYW5kcycgY29tbWFuZHMgIiRAIgp9CigoICQrZnVuY3Rpb25zW19kdWFfX2NvbXBsZXRp
b25zX2NvbW1hbmRzXSApKSB8fApfZHVhX19jb21wbGV0aW9uc19jb21tYW5kcygpIHsKICAgIGxv
Y2FsIGNvbW1hbmRzOyBjb21tYW5kcz0oKQogICAgX2Rlc2NyaWJlIC10IGNvbW1hbmRzICdkdWEg
Y29tcGxldGlvbnMgY29tbWFuZHMnIGNvbW1hbmRzICIkQCIKfQooKCAkK2Z1bmN0aW9uc1tfZHVh
X19oZWxwX2NvbW1hbmRzXSApKSB8fApfZHVhX19oZWxwX2NvbW1hbmRzKCkgewogICAgbG9jYWwg
Y29tbWFuZHM7IGNvbW1hbmRzPSgKJ2ludGVyYWN0aXZlOkxhdW5jaCB0aGUgdGVybWluYWwgdXNl
ciBpbnRlcmZhY2UnIFwKJ2FnZ3JlZ2F0ZTpBZ2dyZWdhdGUgdGhlIGNvbnN1bWVkIHNwYWNlIG9m
IG9uZSBvciBtb3JlIGRpcmVjdG9yaWVzIG9yIGZpbGVzJyBcCidjb21wbGV0aW9uczpHZW5lcmF0
ZSBzaGVsbCBjb21wbGV0aW9ucycgXAonaGVscDpQcmludCB0aGlzIG1lc3NhZ2Ugb3IgdGhlIGhl
bHAgb2YgdGhlIGdpdmVuIHN1YmNvbW1hbmQocyknIFwKICAgICkKICAgIF9kZXNjcmliZSAtdCBj
b21tYW5kcyAnZHVhIGhlbHAgY29tbWFuZHMnIGNvbW1hbmRzICIkQCIKfQooKCAkK2Z1bmN0aW9u
c1tfZHVhX19oZWxwX19hZ2dyZWdhdGVfY29tbWFuZHNdICkpIHx8Cl9kdWFfX2hlbHBfX2FnZ3Jl
Z2F0ZV9jb21tYW5kcygpIHsKICAgIGxvY2FsIGNvbW1hbmRzOyBjb21tYW5kcz0oKQogICAgX2Rl
c2NyaWJlIC10IGNvbW1hbmRzICdkdWEgaGVscCBhZ2dyZWdhdGUgY29tbWFuZHMnIGNvbW1hbmRz
ICIkQCIKfQooKCAkK2Z1bmN0aW9uc1tfZHVhX19oZWxwX19jb21wbGV0aW9uc19jb21tYW5kc10g
KSkgfHwKX2R1YV9faGVscF9fY29tcGxldGlvbnNfY29tbWFuZHMoKSB7CiAgICBsb2NhbCBjb21t
YW5kczsgY29tbWFuZHM9KCkKICAgIF9kZXNjcmliZSAtdCBjb21tYW5kcyAnZHVhIGhlbHAgY29t
cGxldGlvbnMgY29tbWFuZHMnIGNvbW1hbmRzICIkQCIKfQooKCAkK2Z1bmN0aW9uc1tfZHVhX19o
ZWxwX19oZWxwX2NvbW1hbmRzXSApKSB8fApfZHVhX19oZWxwX19oZWxwX2NvbW1hbmRzKCkgewog
ICAgbG9jYWwgY29tbWFuZHM7IGNvbW1hbmRzPSgpCiAgICBfZGVzY3JpYmUgLXQgY29tbWFuZHMg
J2R1YSBoZWxwIGhlbHAgY29tbWFuZHMnIGNvbW1hbmRzICIkQCIKfQooKCAkK2Z1bmN0aW9uc1tf
ZHVhX19oZWxwX19pbnRlcmFjdGl2ZV9jb21tYW5kc10gKSkgfHwKX2R1YV9faGVscF9faW50ZXJh
Y3RpdmVfY29tbWFuZHMoKSB7CiAgICBsb2NhbCBjb21tYW5kczsgY29tbWFuZHM9KCkKICAgIF9k
ZXNjcmliZSAtdCBjb21tYW5kcyAnZHVhIGhlbHAgaW50ZXJhY3RpdmUgY29tbWFuZHMnIGNvbW1h
bmRzICIkQCIKfQooKCAkK2Z1bmN0aW9uc1tfZHVhX19pbnRlcmFjdGl2ZV9jb21tYW5kc10gKSkg
fHwKX2R1YV9faW50ZXJhY3RpdmVfY29tbWFuZHMoKSB7CiAgICBsb2NhbCBjb21tYW5kczsgY29t
bWFuZHM9KCkKICAgIF9kZXNjcmliZSAtdCBjb21tYW5kcyAnZHVhIGludGVyYWN0aXZlIGNvbW1h
bmRzJyBjb21tYW5kcyAiJEAiCn0KCmlmIFsgIiRmdW5jc3RhY2tbMV0iID0gIl9kdWEiIF07IHRo
ZW4KICAgIF9kdWEgIiRAIgplbHNlCiAgICBjb21wZGVmIF9kdWEgZHVhCmZpCg==
```


## Spec 18

When `--log-file PATH` is given, open/create the file in append mode before scanning and append a human-readable debug record for every invocation; never truncate existing content. A successful run must leave it nonempty. Each run contributes exactly one logical options record containing `dua options=Args {`, the input paths, and representations of the effective configuration. This record is pretty-printed across multiple physical lines: the first line has a `HH:MM:SS [INFO] dua options=Args {` prefix, nested fields occupy indented lines, and a line containing `}` closes the record. It is followed by a separate timestamped informational line containing `Ignoring canonicalized` and the canonicalized ignore set. It is not a one-physical-line-per-run format. Required substrings when relevant are:

```text
threads: 0
threads: 2
format: Bytes
format: Metric
apparent_size: true
log_file: Some(
Aggregate {
statistics: true
/proc
/dev
/sys
/run
Ignoring canonicalized
```

Use corresponding values for other chosen settings. Three runs against the same log produce exactly three occurrences of `dua options`, three following `Ignoring canonicalized` lines, and retain any text that predated the first run. Logging still occurs when scanned inputs fail. If the log's parent does not exist or it cannot be opened, write an OS-style message containing `No such file or directory (os error 2)` to stderr and exit 1 without scanning.

## Spec 19

Interactive mode requires both stdin and stdout to be connected to a terminal. Without a TTY, `interactive` and `i` return 1, emit no aggregate report, and write a diagnostic containing `Error: Interactive mode requires a connected terminal` (stderr). With a TTY, take ownership of the terminal, enter an alternate/full-screen interface, react to keystrokes without requiring Enter, and restore the terminal and exit on `q` or Escape from the main pane. Unknown keys are ignored without terminating.

Interactive input selection and measurement follow the aggregate rules, including global `--apparent-size`, multiple roots, special filenames, empty/deep directories, and `--no-entry-check`. That latter flag is accepted and must not prevent the same visible data from eventually rendering.

## Spec 20

The stable interactive main view must fit a 120-by-40 terminal and visibly contain:

- a header matching `Disk Usage Analyzer vX.Y.Z`;
- the current location and entries, directories shown with a `/` marker;
- each entry's formatted size and percentage of the total, with a bar or block visualization;
- `Sort mode: size descending` initially;
- `Total disk usage:` followed by the summed selected sizes;
- `N visible` and `Processed N entries`; and
- footer hints containing `press ? for help`, `mark-move`, `mark-toggle`, and `space`.

Entries initially sort by size descending. For a tree whose `dir1` contains two allocated one-block files and whose `dir2` contains a 102400-byte allocated file, with each directory itself occupying one 4096-byte block, show `/dir2` as `104.00 KiB` and `89.7%`, `/dir1` as `12.00 KiB` and `10.3%`, total `116.00 KiB`, `2 visible`, `5 total`, and `Processed 5 entries` (the two directories plus their three file descendants).

The current selection must be observable in captured terminal text; use a trailing solid block `█` on its row so movement changes the captured screen.

## Spec 21

Interactive navigation and panes behave as follows:

- Down/`j` and Up/`k` move selection without wrapping or crashing. The physical PageDown key and `Ctrl-D` page down; `Ctrl-U` pages up, and applying `Ctrl-D` then `Ctrl-U` returns to the same selected row. Home selects the first row and End the last.
- Enter/Right descends into a selected directory. Left and `u` return to the parent view; the parent then shows its own direct children, not stale descendant rows.
- `s` toggles between `Sort mode: size descending` and `Sort mode: size ascending` and reorders rows accordingly.
- `?` opens a help pane containing `Help`, `Pane control`, `Navigation`, `q/<Esc>`, `Down`, `Up`, and `Enter`. `?`, `q`, or Escape closes that pane and returns to the main listing instead of exiting.
- Tab cycles focus between the main, marked, and help panes where present.

## Spec 22

Space toggles the selected item's marked status. When at least one item is marked, show a `Marked N item`/`Marked N items` pane, its summed size, and marked names. Tab can focus it; Space there unmarks the focused item. When the last item is unmarked, remove the Marked pane without changing files.

`Ctrl-R` from the marked pane permanently removes all marked regular files (and recursively selected directories), refreshes ancestor sizes/counts, clears marks, and keeps navigation usable. In a subdirectory with three files, deleting one marked file leaves that view displaying `2 visible`; returning with `u` shows the updated parent. This action is authorized only by that explicit key sequence.

## Spec 23

Interactive search and display toggles are stateful:

- `/` opens a `Git-Glob (case-insensitive)` search pane and shows `search = enter | case = ^f | cancel = esc`. Typed glob text is displayed. Enter applies recursive git-style glob matching and the visible count reflects matches; Escape closes the search and restores the prior complete view. `Ctrl-F` toggles the pane title and matching between case-insensitive and case-sensitive.
- `M` toggles a modification-time column. When enabled, every applicable row has a timestamp containing `DD/MM/YYYY`; a second `M` removes the column.
- `C` toggles a recursive entry-count column. The count includes the directory itself, so a directory containing three files displays `4 |`; a second `C` removes it. `M` and `C` may be enabled together.

All redraws must retain the main header/status, avoid stale text, and remain responsive to subsequent navigation and quit keys.

## Spec 24

Behavior is determined from live metadata on every invocation. Handle duplicate roots, absolute and relative roots, trailing slashes, readonly/executable files, files modified or removed during traversal, inaccessible entries, sparse and very large files without overflow. Continue past recoverable metadata/read-directory errors. Attach their count to the affected root when failed rows are rendered and always to an applicable total; under `--no-sort`, follow Spec 14's failed-row omission. Do not read file contents merely to measure them.

Aggregate output is deterministic for a fixed directory state. `--no-sort` preserves command-line order for explicit roots and lexical name order for implicit or lone-directory-expanded entries as specified in Spec 13. The executable must scale linearly enough to scan thousands of files, hundreds of roots, wide trees, and files hundreds of megabytes in size within ordinary test timeouts.
