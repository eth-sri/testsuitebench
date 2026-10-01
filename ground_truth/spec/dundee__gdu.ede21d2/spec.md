# Executable specification

The required artifact is a Linux command-line executable named exactly `executable`. It is a disk-usage analyzer with both a plain-text mode and a full-screen terminal mode. All behavior below is part of the executable unless explicitly described as harness behavior. Paths, sizes, inode data, allocation data, modification times, mount points, and permissions must be obtained from the filesystem at run time; examples in this document illustrate formatting and are not fixed fixture data.

## Spec 1

The command syntax is:

```text
executable [directory_to_scan] [flags]
```

With no path, the scan root is the current working directory. A path may name a directory or a single file. Scanning a single regular file succeeds but has no child rows to print in ordinary non-interactive mode. Flag-like parsing ends at `--`, so a later argument is a literal path. Words such as `help`, `version`, `list`, `show`, `add`, and `remove` are ordinary paths, not subcommands. Consequently a nonexistent path with one of those names produces a filesystem `stat` error, never an “unknown command” error. Before that error is formatted, a relative scan path is resolved against the process working directory, so the diagnostic names the resulting absolute path.

The command accepts flags on either side of the path, `--flag=value` as well as `--flag value`, comma-separated and repeated values for list flags, standard short aliases, and conventional combinations of Boolean short flags. If an option occurs repeatedly, its last scalar value wins. Successful scans return status 0. Diagnostics go to stderr and operational output goes to stdout. Unless a later section says otherwise, failure returns status 1 and does not print normal scan output.

## Spec 2

The supported public options are:

```text
--archive-browsing
--collapse-path
--config-file string
-D, --db string
--depth int
--enable-profiling
-E, --exclude-type strings
-L, --follow-symlinks
-h, --help
-i, --ignore-dirs strings
-I, --ignore-dirs-pattern strings
-X, --ignore-from string
-f, --input-file string
-l, --log-file string
--max-age string
-m, --max-cores int
--min-age string
--mouse
-c, --no-color
-x, --no-cross
--no-delete
-H, --no-hidden
--no-prefix
-p, --no-progress
--no-spawn-shell
-u, --no-unicode
-n, --non-interactive
-o, --output-file string
-r, --read-from-storage
--reverse-sort
--sequential
-A, --show-annexed-size
-a, --show-apparent-size
-d, --show-disks
-k, --show-in-kib
-C, --show-item-count
-M, --show-mtime
-B, --show-relative-size
--si
--since string
-s, --summarize
-t, --top int
-T, --type strings
--until string
-v, --version
--write-config
```

`--help` prints a Cobra-style help page containing the description “Pretty fast disk usage analyzer written in Go.”, the usage line `gdu [directory_to_scan] [flags]`, a `Flags:` heading, every option above, and helpful descriptions. The config row is exactly `--config-file string            Read config from file (default is $HOME/.gdu.yaml)` after its six-column indentation; in particular, its description contains the literal substring `default is $HOME/.gdu.yaml` without quotes around the path. The log row is exactly `-l, --log-file string               Path to a logfile (default "/dev/null")` after its two-column indentation: unlike the config path, `/dev/null` is enclosed in double quotes. The other documented defaults include `[/proc,/dev,/sys,/run]` for ignored directories and the current available CPU count for maximum cores. Help exits successfully.

`--version`/`-v` exits successfully and prints exactly three nonempty lines, beginning respectively with `Version:\t`, `Built time:\t`, and `Built user:\t`. The values may describe the local build but must be nonempty.

An unknown flag prints, for example, `Error: unknown flag: --wat` and exits 1. A missing option operand contains `Error:` and `flag needs an argument: --flag`. An invalid integer uses Cobra's quoted flag diagnostic. For example, `--depth=abc` exits 1 and writes exactly `Error: invalid argument "abc" for "--depth" flag: strconv.ParseInt: parsing "abc": invalid syntax\n` to stderr. `-m -1` is valid and means no positive core limit; zero must be handled without crashing. A missing path is reported exactly in the usual form `Error: stat ABSOLUTE_PATH: no such file or directory\n` on stderr; as described in Spec 1, even a path supplied relatively is rendered as its resolved absolute path.

## Spec 3

Without `-n` or `-p`, the executable uses interactive mode only when attached to a terminal. Either `-n` or `-p` forces non-interactive mode, including on a terminal. Thus `-p` is not merely a request to hide a progress widget: `executable -c -p PATH` prints the plain listing and exits successfully without accepting TUI commands. A redirected/non-terminal execution must never hang waiting for input and emits the non-interactive representation. `-c` removes ANSI color sequences. Plain redirected output contains no ANSI escapes even without `-c`.

The default non-interactive view contains one row for each immediate child of the scan root; it does not print a row for the root. A truly empty root therefore produces empty stdout. Directory names have a leading `/`; leaf names do not. Rows are newline-terminated and use this shape:

```text
    8.0 KiB /subdir
    4.0 KiB file.bin
e   4.0 KiB /empty
@       0 B link
```

The first character is the status flag (a space for an ordinary item), immediately followed by a right-aligned formatted-size field whose minimum width is ten characters, and then one separating space before the displayed name. Thus the status-plus-size prefix is normally 11 columns, as in the examples. A value wider than ten characters is not truncated and expands the field; the separator follows the complete value. Names, including spaces and Unicode, are not shell-quoted.

## Spec 4

Every filesystem entry has an apparent size and an allocated/disk size. For a regular file, apparent size is `st_size`; allocated size is the number of allocated 512-byte blocks (`st_blocks * 512`). This distinction must preserve sparse-file behavior. A directory contributes its own filesystem-reported size/allocation plus the sizes of included descendants. The root total includes the root directory itself, while the normal listing shows each immediate child's cumulative total.

Allocated size is the default displayed metric. `-a` selects apparent size for display and summaries, but it does not change the disk-usage ordering of an ordinary listing. Top mode has its own apparent-size ranking described in Spec 5. Files with no content are accepted. A recognized annex value can reach the signed 64-bit maximum without truncating its output field, subject to Spec 7's required target-path recognition. Imported JSON has the maximum-value conversion quirk specified in Spec 12.

By default sizes use binary powers and the labels `B`, `KiB`, `MiB`, `GiB`, `TiB`, and `PiB`; scaled values have one decimal place, while zero/unscaled bytes use an integer such as `0 B`. `--si` instead uses powers of 1000 and `B`, `kB`, `MB`, `GB`, and so on. `-k` forces all values to KiB, or kB with `--si`. `--no-prefix` prints the exact byte integer without a suffix, still right-aligned. `--no-prefix` and `--si` together fail with exactly:

```text
Error: --no-prefix and --si cannot be used at once
```

## Spec 5

The default ordering for an ordinary immediate-child listing is allocated/disk size descending, including when `-a` makes the displayed numbers apparent sizes. `--reverse-sort` changes this disk-size ordering to ascending. Equal disk-size names use natural numeric-aware name order (`file1`, `file2`, `file10`), descending with default size order and ascending with reverse order. Thus an apparent-size listing need not be numerically ordered by the values it prints. Results must not vary between parallel and sequential scanning.

`-s`/`--summarize` prints exactly one row containing the root's cumulative selected size in a nine-character right-aligned field, one space, and the root basename; for example ` 20.0 KiB sample`, or `    20480 sample` with `--no-prefix`. Summary rows have no separate status column. `--depth N`, for positive N, prints the root and the tree beneath it in preorder using full paths: depth 1 includes root and immediate children, depth 2 also includes grandchildren, and so on. Depth and top rows likewise use the nine-character size field without a separate status column. Each sibling group uses the current ordering. Depth 0 is ignored and behaves like the ordinary immediate-child view; negative depth is accepted and likewise produces a bounded, non-crashing result.

`--top N` recursively selects leaf files rather than directories, prints their full paths, and limits output to N rows. Selection and ordering are always by apparent byte size, largest first, even when the rows display allocated sizes and even when `--reverse-sort` is present. For example, 1-, 100-, and 1000-byte files that each occupy 4.0 KiB yield the 1000-byte file followed by the 100-byte file for `--top 2`; a 2000-byte file wins `--top 1` over smaller files with the same 4.0 KiB allocation. Exact apparent-size ties retain the default descending natural-name tie-break. A value of zero is ignored; a negative value behaves as zero. If N exceeds the number of matching leaves, all leaves are shown. Followed file symlinks and recognized annex placeholders can participate as leaves. The same ranking is used for a loaded stored snapshot. When positive `--top`, positive `--depth`, and `--summarize` are combined, top mode has priority, then depth mode, then summarize mode.

`-C` makes descendant item counts available and visible in the interactive table; `-M` likewise makes latest modification times visible in `YYYY-MM-DD HH:MM:SS` form. `-B` selects relative-to-largest-item bar scaling in the interactive display. These flags do not change the basic size/name shape of ordinary redirected output.

## Spec 6

Scanning is recursive and robust to deep and wide directory trees. It recognizes regular files, directories, symbolic links, sockets, FIFOs, and other special entries. It continues past an unreadable descendant. The one-character flags are:

```text
!  the directory itself could not be fully read
.  an error occurred in a descendant, so the aggregate is incomplete
@  a symlink, socket, or non-regular leaf other than a FIFO
H  a regular-file inode has multiple directory links
e  an empty directory
Z  an expanded archive
```

A FIFO is the status-flag exception among special leaves: it has a blank ordinary status and zero allocated size, so `--no-prefix` renders it as `          0 pipe`; a Unix-domain socket in the same scan renders as `@         0 sock`. All hard-link directory entries remain visible, but only the occurrence counted first has the ordinary blank status and its full size. Each later occurrence of that inode is marked `H` and displays `0 B`; for three names of one allocated 4 KiB inode, the rows consist of one `    4.0 KiB` occurrence and two `H       0 B` occurrences. The inode is counted only once in ancestor totals. This marker/zero-size pattern survives both SQLite persistence and a subsequent read. Device-boundary mode `-x` does not descend into a directory whose `st_dev` differs from the root, but keeps normal behavior for entries on the root device. It combines normally with ignore rules and sequential mode.

`--sequential` performs the same logical scan in a single-file/rotating-disk-friendly order. `--max-cores` controls concurrency only and never changes results. `--enable-profiling` starts Go-compatible pprof HTTP service at `localhost:6060/debug/pprof/` without delaying or breaking the scan.

## Spec 7

Symlinks are not followed by default. A link is a non-regular `@` leaf; allocated size is zero and apparent size is the byte length of its stored target string. `-L` follows links only when the final target is a regular file: the entry then behaves like a regular file and uses the target's sizes. Directory symlinks are never traversed, preventing cycles. With `-L`, broken links disappear from the analyzed result. A symlink to a supported archive may be expanded when both `-L` and archive browsing are active.

With both `-L` and `-A`, special handling of a missing git-annex link is enabled only when the stored target string contains the path component `.git/annex/objects`. An annex-looking key or an `-sDECIMAL` component elsewhere is insufficient: such a link follows the ordinary broken-link rule and produces no row. This includes targets under `../annex/objects`, arbitrary absolute targets such as `/missing/MD5E-s77--absolute`, and targets such as `missing/SHA256E-s9223372036854775807--huge`.

For a qualifying `.git/annex/objects` target, the basename is parsed as the annex key. The first `-sDECIMAL` key component supplies the apparent size, including the signed 64-bit maximum; a canonical target with that maximum can therefore render `@ 9223372036854775807 huge`. If a qualifying key has no valid size, the link remains visible as an annex placeholder with zero apparent size instead of disappearing: `no_size.txt` renders `@         0 no_size.txt` under `-a --no-prefix`. A malformed qualifying size likewise leaves a zero-sized placeholder and logs its parse error. It does not fall back to the stored target-string length. `-A` alone has no special effect. Annex placeholders retain their non-regular identity in exported data and may be selected by apparent-size top mode.

## Spec 8

`-i` excludes entire directories by literal path. Values may be comma-separated or repeated, and all supplied values accumulate. Absolute values are used directly; relative values are resolved against the process working directory, not against a separately supplied scan root. Thus `-i a,b -i c` excludes children named `a`, `b`, and `c` from the supplied root only when that root is also the working directory. Its default is `/proc,/dev,/sys,/run`; explicitly passing an empty value (`-i ""`) replaces that default with no literal exclusions. `-I` accepts comma-separated and repeated Go regular-expression path patterns, but only the final pattern in the resulting sequence is effective. Matching is case-sensitive. Consequently `-I 'skip.*,nomatch'` applies `nomatch`, leaving `skip1` visible; reversing those comma-separated operands applies `skip.*` instead. An invalid effective expression produces a clean nonzero error using the Go regexp parser's wording; for example, `-I '[unclosed'` exits 1 with exactly ``Error: error parsing regexp: missing closing ]: `[unclosed`\n`` on stderr.

`-X FILE` reads every line as a regular-expression path pattern, including the first line. Relative patterns are resolved in the same process-working-directory context as `-I`, rather than relative to a separately supplied scan root. Thus, when the scan root is also the working directory, `node_modules\nlogs\n` excludes both directories, not just the second. Empty lines are not skipped; an empty expression matches every directory, so a file containing `cache\n\nbuild\n` excludes every directory while an ordinary rules file remains visible as a regular file. The ignore file is not automatically excluded from the scan. Failure to open it is reported as `Error: open FILE: no such file or directory` (with the platform's equivalent detail for other I/O failures).

`-H` excludes dot-prefixed directories and their contents but does not exclude dot-prefixed regular files. Excluded paths do not contribute to totals. Directory nodes left empty by other filtering remain representable as directories.

## Spec 9

`-T` is a case-insensitive extension allowlist and `-E` is a case-insensitive extension denylist. Values may be repeated or comma-separated and may include or omit the leading dot. Classification uses the last filename extension. An allowlist excludes extensionless files and all unlisted types. A denylist excludes listed types. When a nonempty allowlist and denylist are both supplied, the allowlist governs and the denylist is ignored, even if both mention the same extension. Directories needed to represent surviving content remain in the tree.

The type rules combine with path, hidden, age, filesystem-boundary, symlink, and archive rules. An expanded archive is a special case: extension filtering is applied first to the filesystem archive filename. If the archive container is rejected, it is never expanded merely because a member has an allowed extension; for example, `--archive-browsing -T txt` omits `mixed.zip` entirely even when it contains `keep.txt`. If the container is allowed (for example by `-T zip`), its members are expanded without applying the extension filter to their names. Other scan-time filters change totals and exported/persisted snapshots; they are not merely display filters.

## Spec 10

Age filters apply to leaf modification times and combine by logical AND:

* `--max-age DURATION`: include entries no older than the duration.
* `--min-age DURATION`: include entries at least the duration old.
* `--since TIME`: include entries at or after TIME.
* `--until TIME`: include entries at or before TIME.

Durations are case-insensitive, ignore embedded spaces, and permit compound nonnegative integer components using `y` (365 days), `mo` (30 days), `w`, `d`, `h`, `m`, and `s`, such as `1y2mo`, `2h30m`, or `7d`. An empty duration disables that bound. Negative, unitless, fractional, unknown-unit, or partially parsed strings are invalid. Repeated constraints intersect, so the strictest applicable boundary wins.

Absolute times accept strict RFC3339 timestamps with timezone or valid `YYYY-MM-DD` calendar dates. A date-only `--since` starts at that day's midnight and a date-only `--until` includes the whole day. Leap years and invalid calendar dates are validated. Every invalid bound exits 1 under the exact common prefix `Error: invalid time filter:`. Invalid absolute values use double quotes and this exact template:

```text
Error: invalid time filter: invalid --OPTION value: invalid time value "VALUE". Use RFC3339 timestamp or YYYY-MM-DD
```

For example, `--until=2020-02-30` substitutes `until` and `2020-02-30`, while `--since=not-a-date` substitutes `since` and `not-a-date`. Invalid durations use this exact template, again with double quotes:

```text
Error: invalid time filter: invalid --OPTION value: invalid duration format "VALUE". Use combinations like 7d, 2h30m, 1y2mo
```

This applies equally to `--max-age` and `--min-age`, including malformed, partially parsed, and negative values such as `invalid`, `not-a-duration`, `7d5`, `-7d`, and `xyz`. Each diagnostic is newline-terminated on stderr. Structural directories remain as needed even when some leaves fail the time predicate.

## Spec 11

`-o FILE` exports a live scan as JSON instead of printing the normal listing. `-o -` writes JSON to stdout. Opening a named output happens before scanning, so if the output file lies inside the root it can appear in its own snapshot as a zero-sized file. Export has no other normal stdout output.

`-f FILE` imports a prior JSON analysis rather than scanning; `-f -` reads stdin. In non-terminal use, an imported analysis uses the ordinary sorting, size selection, depth, and summary logic. Positive `--top` is ignored for this JSON-import path: `--top=1` still prints every immediate child rather than selecting one leaf. Input and output cannot be combined; that failure is:

```text
Error: reading analysis: reading analysis is not possible while exporting
```

A missing named input file fails before JSON reading with status 1 and exactly the prefix `Error: opening input file: open ...: no such file or directory`; for example, `-f /nonexistent/input.json` writes `Error: opening input file: open /nonexistent/input.json: no such file or directory\n`. An empty input instead fails as an unexpected end-of-input/EOF JSON error. A named output path that is already a directory fails with status 1 and `Error: opening output file: open PATH: is a directory`. Source-path validation errors remain scan errors even if an output file was requested.

The exported document is a JSON top-level array with this logical schema (insignificant whitespace is shown here only for readability):

```json
[1, 2, {"progname":"gdu","progver":"dev","timestamp":1700000000},
 [{"name":"ROOT","mtime":1700000000},
  {"name":"file","asize":10,"dsize":4096,"mtime":1700000000}]]
```

The first two integers are format versions. Element 3 is metadata with `progname` equal to `gdu`, a nonempty `progver`, and a positive epoch-second `timestamp`. Element 4 is the root directory array. Every directory is encoded as an array whose first item is its header object and whose remaining items are child file objects or nested directory arrays. A directory header contains its `name` and integer `mtime`, not aggregate `asize`/`dsize` fields; aggregates are reconstructed from the tree. The root header preserves the supplied scan path; child names are basenames. The on-disk stream starts with the compact header text `[1,2,{"progname":"gdu","progver":"` and compactly encoded metadata, even if line breaks delimit the tree. Integers are emitted exactly, never in scientific notation. Zero-valued optional size fields are omitted.

Leaf objects use `name`, optional `asize`, optional `dsize`, and `mtime`; non-regular entries add `notreg:true`. Hard links preserve `ino` and `hlnkc:true`. Names with quotes, control characters, newlines, and Unicode use valid JSON escaping. Within each exported directory array, child nodes are written in ascending lexicographic name order; an archive-browsing root containing `a_first.zip`, `b_second.jar`, `c_third.txt`, and `d_fourth.zip` emits those children in exactly that order, independently of ordinary display-size sorting. Directories, symlinks, hard links, sparse files, hidden entries, and archive trees all round-trip.

## Spec 12

The JSON reader accepts differing integer version values and missing informational metadata. It accepts missing mtime, duplicate names, zero sizes, negative signed sizes, and 64-bit integer tokens. Imported negative values are formatted normally (for example `-4096` as `-4.0 KiB`). Its numeric conversion does not preserve the positive signed 64-bit maximum: an imported apparent size of `9223372036854775807` is rendered by `-a --no-prefix` as `-9223372036854775808`. It rejects malformed JSON and structurally unusable trees with clear, prefixed diagnostics. Required diagnostic phrases are:

```text
Error: reading analysis: invalid character ...
JSON file does not contain top level array
top level array must have at least 4 items
array of maps not found in the top level array on 4th position
directory name is not a string
directory item is not a map
```

The latter two apply respectively when a directory header lacks a string `name`, and when the first member of a nested directory array is not an object. Scan-only filters (`-i`, `-I`, `-X`, `-H`, `-T`, `-E`, age bounds, crossing, following) are ignored when displaying an already imported snapshot. Display options remain effective except for `--top`, as specified in Spec 11.

## Spec 13

With `--archive-browsing`, filenames ending case-insensitively in `.zip` or `.jar` are inspected. A valid archive becomes a `Z` directory-like node named after the archive. File entry paths reconstruct the directories needed to contain them, including deep paths, Unicode, spaces, special characters, and zero-length files. A directory represented only by an explicit ZIP directory entry is omitted when it has no retained file descendant: a ZIP containing `empty-dir/` and `zero.txt` exports `zero.txt` but no `empty-dir`. Archive entry modification times are retained. Archived file apparent and disk sizes both equal the uncompressed byte count. Each synthesized archive directory contributes 4096 bytes to both aggregates; thus three entries of 100, 200, and 300 bytes split between an archive root and one child directory total 8792 bytes.

Archives are opaque regular files when the flag is absent. Corrupt/unsupported archives fall back to regular files. Archives nested inside an archive are not recursively expanded. An empty valid archive is an empty archive directory. Expanded archives participate in normal sorting, summaries, JSON, and terminal navigation, subject to Spec 9's container-first extension filtering. A SQLite-backed scan is the exception: when `-D STORE.sqlite` is used, even `--archive-browsing` leaves a valid archive as an opaque regular file (for example, a small `test.zip` prints as `    4.0 KiB test.zip`) and that opaque node is what is stored. `--no-prefix` and apparent/binary/SI formatting work on expanded archive totals in the same way as filesystem totals.

## Spec 14

`-D PATH` persists the analyzed snapshot. A `.sqlite` path is a nonempty regular SQLite database; a `.badger` path is a BadgerDB-style directory containing at least a `MANIFEST`. Fresh scans create or replace the stored analysis. Both backends retain nested data, Unicode, both size measures, hard-link identity, symlink state, archive nodes, and scan-time filters. As specified above, the SQLite analyzer stores archive files opaquely even when archive browsing was requested; this exception does not apply to a `.badger` scan.

With `-r -D PATH ROOT`, an existing snapshot is loaded rather than rescanning and produces the same default listing as the original stored scan. The root path is still validated where required by the stored analysis workflow. Display-time choices such as reverse order, depth, top, summary, counts, and mtime apply to loaded data, subject to top mode's always-largest-first rule. Apparent-size selection is an SQLite exception: `-a` on a SQLite read is ignored for the displayed rows, which continue to show the stored disk-size values. A type allowlist supplied on a Badger read is applied to the loaded nodes: after storing `α.txt`, reading with `-T zzz` succeeds with empty stdout rather than reproducing the original row. New ignore/time/follow flags supplied only on the read command do not reinterpret the snapshot. A missing store may be initialized by a fresh scan when a root is available. A corrupt SQLite file exits 1 and writes exactly `Error: creating sqlite analyzer: file is not a database (26)\n`; an unusable SQLite location similarly reports `unable to open database file`.

Exporting a populated Badger snapshot with `-r -D ... -o ...` follows the JSON schema. The SQLite read/export combination has a compatibility quirk: even after a prior scan, if the SQLite retrieval supplies no export tree, it exits 0 and writes only the standard compact header followed by a trailing comma and closing array, ending exactly `,\n]\n`. The same header-only form is used when `-r` export names a nonexistent SQLite store; this path creates/opens the store and must not crash. Ordinary SQLite display reads still return the stored listing, and corrupt SQLite data still fails. Badger export remains valid JSON and contains its stored tree.

## Spec 15

`-l FILE` creates/truncates a log and writes structured informational diagnostics there. `-l -` sends those logs to stdout. Log records include `time="..."` and `level=...` and use recognizable field/value text such as `Runtime flags:`, `LogFile:...`, `MaxCores:3`, `Max cores set to 3`, `SequentialScanning:true`, `Profiling:true`, and `Ignoring dirs /proc, /dev`. A successful scan also logs `Analyzing path:`. If the initial `stat` of the scan path fails, the already-created log retains the runtime/config/ignore/core records but contains no `Analyzing path:` record; the command exits 1 with the scan error. Failure to create the log exits 1 with the exact prefix `Error: opening log file: open ...`; for example, `/nonexistent/path/test.log` produces `Error: opening log file: open /nonexistent/path/test.log: no such file or directory\n`. The default `/dev/null` produces no visible log.

`--config-file FILE` reads YAML. A missing or malformed configuration is nonfatal: the scan continues, and if logging is enabled the log contains `Error reading config file`. Without an explicit file, `$HOME/.gdu.yaml` is the default. Command-line values override configuration values.

Recognized YAML keys correspond to the CLI behaviors and include `log-file`, `input-file`, `output-file`, `ignore-dirs`, `ignore-dir-patterns`, `ignore-from-file`, `max-cores`, `sequential-scanning`, `show-apparent-size`, `show-relative-size`, `show-item-count`, `no-color`, `mouse`, `non-interactive`, `no-progress`, `no-cross`, `no-hidden`, `no-delete`, `follow-symlinks`, `profiling`, `read-from-storage`, `summarize`, `use-si-prefix`, `no-prefix`, `reverse-sort`, `change-cwd`, `delete-in-background`, `delete-in-parallel`, `archive-browsing`, `collapse-path`, `top`, `depth`, `type`, `exclude-type`, and the time bounds. A nested `sorting` object accepts `by: size|name|itemCount|mtime` and `order: asc|desc` and initializes terminal sorting. It does not change an ordinary redirected listing: with equal-size `file1`, `file2`, and `file10`, YAML `by: name` and `order: asc` still emit the default descending tie order `file10`, `file2`, `file1`, while the same configuration starts the TUI in `file1`, `file2`, `file10` order.

`--write-config` writes the effective configuration as YAML to `--config-file` or, by default, `$HOME/.gdu.yaml`, creating it when absent. It includes the major keys above. The generated document has a top-level `style:` mapping; `footer`, `selected-row`, `result-row`, `header`, `progress-modal`, and `use-old-size-bar` are nested beneath it rather than emitted at top level. The separate `sorting:` mapping remains top-level. Color values are preserved, with defaults including footer text `#000000`, footer background `#2479D0`, footer number `#FFFFFF`, result number `#e67100`, and result directory `#3498db`.

## Spec 16

Progress is a terminal-only transient UI. During a sufficiently observable live scan it includes `Scanning`; during named JSON export it includes scan/write activity such as `Writing output file` and enough screen output to be visibly active. Any sizes in progress use the same binary or SI unit selection as final output, including GiB/GB-scale values. `-c` keeps progress visible but removes ANSI color. Progress must not contaminate redirected listings or JSON. As specified in Spec 3, `-p` both suppresses progress and forces the plain non-interactive execution path, even when all three standard streams are terminals.

`-d`/`--show-disks` replaces filesystem scanning with a mounted-device table. Non-interactive output has aligned columns headed `Device`, `Size`, `Used`, `Free`, `Used%`, and `Mount point`, followed by the available mount rows. Every emitted data row uses a device-path identifier beginning `/dev/` in the `Device` column (for example `/dev/mapper/system-root`), not a filesystem type such as `fuse-overlayfs`. At least the root mount is shown on a normal Linux host. Interactive disk mode uses a corresponding device/mount table. `-c` removes color. Disk mode cannot be exported with `-o`; that combination exits nonzero and stderr is exactly:

```text
Error: loading mount points: exporting devices list is not supported
```

## Spec 17

This section and Specs 18–22 apply only when interactive mode was selected under Spec 3. They do not apply when either `-n` or `-p` is present. In particular, input sent after a terminal invocation such as `-c -p PATH` has no application to receive it: the process has already printed its plain rows and exited with status 0.

Interactive mode is a full-screen terminal interface that redraws to the current terminal dimensions (tests use 80 columns by 24 rows). An 80×24 plain capture is exactly 24 rows and has no leading blank row. Its ordinary screen consists of:

1. the header on row 1, initially ` gdu ~ Use arrow keys to navigate, press ? for help`;
2. the path line on row 2, of the form ` --- FULL_PATH ---`;
3. a scrollable table of immediate children beginning on row 3;
4. blank padding through row 23; and
5. the footer on row 24, such as ` Total disk usage: 4.0 KiB Apparent size: 10 B Items: 1 Sorting by: size desc`.

A table row contains the status/mark, aligned size, an eleven-cell proportional-bar field, optional item count and mtime columns, and the name (`/name` for a directory). The Unicode field consists of ten proportional cells followed by the fixed right-edge glyph `▏`. For ordinary uncollapsed rows, unless relative scaling is selected, its denominator is the exact sum of the current view's unrounded row sizes; collapsed rows have the exception in Spec 18. The renderer first truncates each row's percentage to an integer, maps that percentage onto ten cells, and truncates the result to an eighth-cell boundary, using `▏`, `▎`, `▍`, `▌`, `▋`, `▊`, and `▉` for one through seven eighths. A sole item therefore has `██████████▏`; three equal items each have `███▎      ▏`; and items occupying two thirds and one third of the visible total have `██████▌   ▏` and `███▎      ▏`. For example, a sole ordinary file row is exactly `    4.0 KiB ██████████▏a.txt`; 12 KiB and 8 KiB rows are `   12.0 KiB ██████    ▏/name` and `    8.0 KiB ████      ▏/name`. A temporarily ignored/de-emphasized row retains a blank ten-cell portion followed by `▏`. `-u` uses the corresponding fixed-width ASCII bar. When YAML `style.use-old-size-bar` is true, the field instead uses brackets, as in the exact zero-size/count row `        0 B [          ]      1 file_1500.txt`. `-c` uses grayscale/no ANSI styling without changing any text or whitespace layout.

The item-count field is six columns including its leading separation; for example, rows with count and mtime enabled are `   12.0 KiB ██████    ▏     2 2023-11-14 22:13:20 /dir1` and `    8.0 KiB ████      ▏     1 2023-11-14 22:13:20 /dir2`. Binary/SI/apparent/large values, sparse files, and large counts are formatted consistently; counts abbreviate with `k` and `M` when necessary. Long paths, rows, and the footer are clipped at column 80 without shifting their fixed rows. Footer clipping does not emit a partial final word: for example, a constrained count-sort footer can end at the observed text `Sorting by:`.

The footer total is the current analyzed total, apparent size is also shown, and `Items` counts descendants. The current sorting field and direction are displayed. The selected row is visibly highlighted when color is available but its text stays readable in plain terminal captures.

## Spec 18

Interactive navigation accepts both arrows and Vim keys: Up/`k`, Down/`j`, PageUp/PageDown, `g` for first, and `G` for last. Right/Enter/`l` enters a selected directory; Left/`h` goes to its parent. The entered view contains a `/..` parent row where applicable. With the ordinary columns, that row is exactly `                         /..`: its status, size, and bar positions are blank rather than displaying `0 B`. `q` exits cleanly from any view; `Q` exits and prints the current path. Unsupported keys and Escape in the ordinary list are harmless.

`--collapse-path` displays an unbranched chain of single-child directories as one slash-separated row such as `/a/b/c/d`. The combined row displays the deepest represented directory's cumulative size, not the top directory's aggregate; its bar nevertheless uses that displayed deepest size over the uncollapsed top directory's aggregate. Thus a 20 KiB top chain whose deepest directory totals 8 KiB renders `    8.0 KiB ████      ▏/a/b/c/d`. Entering the row navigates to the deepest represented directory. Left/`h` from there goes to its immediate filesystem parent (for example, from `/a/b/c/d` to `/a/b/c`) and shows that parent's ordinary `/..` and `/d` rows; it does not jump directly to the original root. A file at the end of a chain is not merged into the directory label.

Sorting keys are stateful. `n` selects name order ascending on first use and toggles direction on repetition. `s` selects size order and toggles on repetition. `C` selects item-count sorting ascending on first use and `M` selects mtime sorting oldest-first/ascending on first use; repetition toggles the selected direction. These uppercase sorting keys do not themselves reveal the corresponding columns. Lowercase `c` toggles the count column and lowercase `m` toggles the mtime column. `a` toggles displayed/sorted disk versus apparent size. `B` toggles bar scaling between proportion of total and proportion of the largest visible item. CLI `-C`, `-M`, `-a`, and `-B` establish the corresponding initial display state.

## Spec 19

`?` opens a Unicode double-bordered help panel titled `gdu help` that fills an 80×24 screen. Its binding labels and descriptions include these exact rows (with padding added inside the border):

```text
       up/down, k/j    Move cursor up/down
    pgup/pgdn, g/G     Move cursor top/bottom
   enter, right, l     Go to directory/device
           left, h     Go to parent directory
                 r     Rescan current directory
                 E     Export analysis data to file as JSON
                 /     Search items by name
                 a     Toggle between showing disk usage and apparent size
                 B     Toggle bar alignment to biggest file or directory
                 c     Show/hide file count
                 m     Show/hide latest mtime
                 b     Spawn shell in current directory
                 q     Quit gdu
                 Q     Quit gdu and print current directory path
  Item under cursor:
                 d     Delete file or directory
```

The title is centered in a double-line top border and the bottom double-line border spans the full 80 columns. `?`, Escape, or `q` closes this panel without exiting the program.

`/` enters live name-filter input in the footer. Typed text restricts the visible rows by name while editing. Enter keeps the filter and returns focus to the table; Escape clears it and restores all rows. Filtering and empty results do not crash navigation.

`i` opens an item-information panel for the selected row while retaining the ordinary header, path, underlying table rows, blank padding, and footer in their fixed screen positions. On an 80×24 screen with two underlying rows, two blank rows follow the table, the panel's top border is on row 7, and its bottom border is on row 18. Its single-line border spans all 80 columns, with the title `Item info` centered in the top border. Two blank bordered rows precede the fields and two follow them. It uses the exact labels `Name:`, `Path:`, `Type:`, `Disk usage:`, and `Apparent size:`; both sizes show human-readable and parenthesized byte forms, such as `Disk usage: 8.0 KiB (8192 B)`. The content is inset two columns inside the border and the size labels are right-aligned to each other. `j`/`k` or arrows can change the inspected selection, and `i` or Escape closes the panel.

## Spec 20

Space marks or unmarks the highlighted item and advances the cursor. Marked rows show `✓`, and the footer adds `Selected items: N`. Multiple selections are supported.

`d` requests recursive deletion of all marked items, or the highlighted item if none is marked. `e` requests emptying a selected/marked directory: its contents are removed but the directory remains. Both show a confirmation modal, defaulting to the exact lowercase choice `no`, with the exact choices `no`, `yes`, and `don't ask me again` navigable by Tab or `h`/`l`. With no marks, the prompt uses the requested action verb and the quoted highlighted name: deletion uses `Are you sure you want to delete` and emptying uses `Are you sure you want to empty`, followed by the quoted name and `?`. With marks, the count form is used even for one item and uses the requested action verb; one marked directory emptied with `e` shows `Are you sure you want to empty 1 items?`. Marked deletion uses the analogous count form with `delete`. Enter activates the choice. `no` preserves the filesystem and marks. `yes` performs the operation and refreshes totals/listing. `don't ask me again` confirms and suppresses later confirmation during that session. Background and parallel deletion configuration may perform work asynchronously but must update the screen and filesystem correctly for multiple files and directory trees.

`--no-delete` prevents both deletion forms. Attempting one changes the header to `Deletion is disabled!` and leaves data untouched. Deletion errors are shown rather than terminating the UI.

`I` (uppercase i) toggles an item as temporarily ignored in the current analysis. Ignored entries cease contributing to totals/counts and are visually removed or de-emphasized; the cursor advances. Toggling again restores them. `r` performs a fresh filesystem scan, updates additions/removals, and recomputes totals, but it does not clear the set of ignored row indices. Because ignores are retained by row position rather than path, sorting changes after a rescan can transfer the de-emphasized/uncounted state to a different item at that same row; adding a new first row after ignoring the old first row leaves the new row with a blank bar and excludes it from the displayed item count.

## Spec 21

`v` views a selected regular file inside the same 80×24 frame; pressing it on a directory leaves the screen byte-for-byte unchanged. In file view, row 1 remains ` gdu ~ Use arrow keys to navigate, press ? for help`, row 2 becomes exactly ` --- FULL_FILE_PATH ---` (including the leading space and closing delimiter), content begins at column 1 of row 3, blank rows pad any unused viewport through row 23, and the ordinary directory footer remains on row 24. No extra blank row precedes the header. Text wraps at the 80-column edge on word boundaries without added indentation.

`j` and Down each advance the viewport by one displayed line: with unwrapped numbered input, the view then starts with line 2. PageDown advances one viewport page; in an 80-column fixture whose longer numbered lines wrap, the observed next top line is line 16. `G` bottom-aligns the end of the content in rows 3–23 (a 100-line wrapped fixture begins at line 91 and leaves a blank row after line 100). Escape or `q` returns to the directory listing. Files ending in `.gz`, `.bz2`, and `.xz` are transparently decompressed into this identical frame; the footer continues to report the compressed filesystem entry's sizes. An unreadable file or invalid compressed stream produces an error modal containing `Error reading file:` and can be dismissed back to the list.

`E` opens an export modal titled exactly `Export data to JSON`, with the editable field text `File name export.json` and an `Export` action; confirming writes the current analysis in the JSON format. `o` asks the platform opener to open the selected item and reports launch failure in a modal. `b` spawns the user's shell in the current directory. With `--no-spawn-shell`, neither external action runs: `o` changes the first screen line to exactly ` Opening items is disabled!`, while `b` changes it to ` Shell spawning is disabled!`. `--mouse` enables mouse interaction without changing keyboard behavior.

## Spec 22

Interactive archive nodes use the `Z` flag and can be entered like directories, including navigation through deep archive paths and back out to the filesystem. An empty archive remains navigable, but an explicit empty directory entry inside a nonempty archive is omitted as described in Spec 13. Archive browsing never permits archive contents to escape the virtual archive root through `..` components.

Interactive errors—unreadable directories, disappearing entries, opener failures, bad compressed data, and deletion failures—must be rendered within the 80x24 interface or as a dismissible modal and must not leave raw terminal control traffic after exit. On normal quit the terminal state is restored and the process exits 0.

## Spec 23

All modes compose subject to the explicit archive, storage, ordering, and `-p` exceptions above. Filters are applied before aggregation, except that archive extension filters act on the container before expansion and do not filter individual members. The resulting tree feeds text output, terminal output, JSON, and database storage; a Badger read may then apply a new type allowlist as specified in Spec 14. Hard-link deduplication keeps every directory entry but gives only the first-counted occurrence its full displayed size; later occurrences carry `H` and display zero as specified in Spec 6. Apparent/disk selection changes presentation without losing the other stored measure except for SQLite read display's `-a` compatibility behavior in Spec 14; ordinary listings remain disk-size ordered, while top mode is apparent-size ranked. Sorting is deterministic despite concurrent scanning. Sequential mode, no-color, SI/binary formatting, depth/top/summary, symlink policy, archives, and storage may be combined unless this specification names an explicit conflict; `-p` selects plain mode rather than a progress-free TUI.

The executable must handle empty trees, thousands of entries, deep nesting, very long paths, sparse and large files, special characters, Unicode, broken links, cyclic directory links, permission errors, and changes observed during an interactive rescan without panicking, deadlocking, emitting invalid JSON, or silently corrupting totals.
