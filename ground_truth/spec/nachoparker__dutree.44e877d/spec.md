## Spec 1

The required artifact is a directly runnable file named exactly `executable` in the workspace root. It is a command-line disk-usage viewer. It accepts zero or more filesystem paths and writes one textual tree to standard output. A successful scan, help request, or version request exits with status 0. Argument/validation failures exit with status 1. Except for diagnostics described below, successful scans write nothing to standard error. Every normal output line, help line, version line, and diagnostic ends with `\n`.

The behavior is defined for a Unix-like filesystem. Metadata must be obtained without following symbolic links when measuring an entry. The executable must not create or modify anything in a scanned tree.

## Spec 2

The accepted options are:

```text
-d, --depth [DEPTH]
-a, --aggr [N[KMG]]
-s, --summary
-u, --usage
-b, --bytes
-f, --files-only
-x, --exclude NAME
-H, --no-hidden
-A, --ascii
-h, --help
-v, --version
```

Options may occur before or after positional paths. `--` ends option parsing, so every later token is a path even if it begins with `-`. Boolean short options may be grouped, for example `-bu`. `-x`/`--exclude` requires one value and may be repeated; all its values accumulate. The other options are single-occurrence options: supplying both short and long forms, or otherwise supplying one twice, is an argument error such as `Option 'depth' given more than once`.

Depth and aggregation are options with optional values. A short option accepts an attached value (`-d2`, `-d-5`, `-a1K`) or consumes the next non-option token as a separate value (`-d 2`, `-a 1K`), even if that token could also name a path. To use the default value before a path unambiguously, terminate options, as in `-d -- <path>` or `-a -- <path>`. A short option at the end or followed by another option is bare: bare `-d` has value 1 and bare `-a` has value 1 MiB. A long option accepts an optional value only with `=` (`--depth=2`, `--aggr=1K`); `--depth 2 .` and `--aggr 1M .` leave `2` or `1M` as positional paths. A long option followed immediately by an existing path is therefore the bare option plus that path. An optional-value short option consumes the remainder of its token as its value rather than treating those characters as grouped options. Consequently `-da` is `-d` with the attached depth value `a`; failed depth conversion makes it depth 1, and it does not enable aggregation. Similarly, `-ab` makes `b` the aggregation value and is invalid. This actual parsing of `-da` applies despite the descriptive `equivalent to -da` phrase in the fixed help text in Spec 3.

## Spec 3

`-h` and `--help` produce identical output on standard output, no standard error, and status 0. The first line uses the actual invocation string from `argv[0]` (therefore it can be `./executable` or an absolute path). The output is exactly:

```text
Usage: <argv[0]> [options] <path> [<path>..]

Options:
    -d, --depth [DEPTH] show directories up to depth N (def 1)
    -a, --aggr [N[KMG]] aggregate smaller than N B/KiB/MiB/GiB (def 1M)
    -s, --summary       equivalent to -da, or -d1 -a1M
    -u, --usage         report real disk usage instead of file size
    -b, --bytes         print sizes in bytes
    -f, --files-only    skip directories for a fast local overview
    -x, --exclude NAME  exclude matching files or directories
    -H, --no-hidden     exclude hidden files
    -A, --ascii         ASCII characters only, no colors
    -h, --help          show help
    -v, --version       print version number
```

There is a final newline and no extra blank line after the last option. `-v` and `--version` likewise match and print exactly `dutree version 0.2.18\n` to standard output with status 0 and empty standard error.

All tokens are parsed before help/version is acted upon. Thus `--help --` is valid help, but `--help --nope` is an argument error: it prints usage to standard output and the unrecognized-option diagnostic to standard error rather than succeeding as help.

## Spec 4

Parser errors, including unknown options, duplicate single-occurrence options, or a missing required option value, print the complete usage text from Spec 3 to standard output and the parser diagnostic plus newline to standard error, then exit 1. Relevant diagnostic forms include `Unrecognized option: 'z'`, `Unrecognized option: 'invalid-flag'`, `Option 'depth' given more than once`, and the analogous names for other duplicated options. In particular, invoking `-x` without its required value writes exactly `Argument to option 'x' missing\n` to standard error.

After syntactic parsing, every positional path is validated before any tree is produced. If any path does not exist, write `path <path-as-supplied> doesn't exist\n` only to standard error and exit 1. Do not partially render valid paths from the same invocation. Because existence checking follows links, a broken symbolic link supplied as a root path is considered nonexistent. With no positional paths, use the single path `.` and scan the process's current working directory.

Aggregation-value validation errors similarly produce no usage and write `invalid argument '<value>'\n` to standard error with status 1.

## Spec 5

For one input path, that path itself is the root entry. For two or more paths, create a synthetic root named `<collection>` whose children are the supplied roots and whose size is their sum. Duplicate paths are allowed. Sort collection children by descending computed size just as directory children are sorted.

The displayed name of a real entry is its final path component, not the full path. Relative paths, absolute paths, `.` components, and trailing slashes must all work. For a non-symlink, form the name after canonicalizing the path where possible; this makes `.` display the basename of the current directory. Do not canonicalize a symlink itself. The filesystem root displays `/`. If a filename cannot be decoded as UTF-8, display `[invalid name]` rather than crashing.

Every output begins with an unrestricted, uncolored root header:

```text
[ <root-name> <formatted-root-size> ]
```

A single file or symlink root and a depth-zero directory have only this header line.

## Spec 6

Without `-d`/`--depth`, recursively construct and display the complete directory tree; there is no implicit depth limit. If a depth option is present, decimal `DEPTH` is parsed as an unsigned 8-bit integer. A missing value, a nonnumeric attached value, a negative attached value, a value greater than 255, or any other failed conversion falls back to 1 rather than being an error. Consequently `-dabc`, `-d-5`, `-d256`, and very large decimal depths behave as depth 1. Values 0 through 255 are honored.

Depth counts edges below each supplied root: depth 0 prints only the root header; depth 1 prints its direct children; depth 2 also prints grandchildren, and so on. The same independent limit applies beneath every child of a `<collection>` root. A limit larger than the actual tree prints the full tree.

Depth limits control construction of displayed entries, but not the byte total of an entry at the cutoff. Such an entry is measured recursively through every descendant even though those descendants are not printed. This recursive fallback measurement is raw: filters and aggregation are only applied in directories whose children are actually constructed. Thus exclusions and hidden-file filtering below a depth cutoff do not affect the cutoff entry's total.

## Spec 7

In the default mode, an entry's own size is the `lstat`/symlink-metadata `st_size`. A constructed directory's total is its own `st_size` plus the computed sizes of all retained child entries. Directory metadata size is therefore intentionally included. At a depth cutoff, recursively sum the directory's own `st_size` and every descendant's corresponding size. A synthetic collection has no own metadata size.

With `-u` or `--usage`, replace `st_size` everywhere with allocated bytes, calculated as `st_blocks * 512` from symlink metadata. Apply this to regular files, directories, and links before recursive summation. This distinguishes sparse files from their apparent length, generally rounds small allocated files to filesystem blocks, permits a completely sparse file or symlink to report zero allocated bytes, and must not overflow on very large sparse files.

Never follow a symbolic link while recursing or measuring it. Its apparent size is the byte length recorded for its link target, while its usage size is its own allocated blocks. A link to a directory remains a leaf. Broken links found inside a scanned directory are displayed normally.

## Spec 8

For every constructed directory, enumerate retained children, recursively compute each child's total, then sort ordinary children by descending byte total. Sorting is numeric, not lexicographic by the formatted size. Equal-sized items retain the filesystem enumeration/fixture order; do not introduce an arbitrary reverse-name tie break. After sorting, append any aggregation bucket (Spec 10), regardless of that bucket's size. Mark only the final displayed child as the last branch.

Percentages and bars use the computed sizes after filtering and the selected apparent/usage mode. A directory's own metadata bytes remain in its denominator, so child percentages need not add to 100%. Empty directories and zero-byte entries are valid and must not cause division-by-zero failures.

## Spec 9

`-x NAME` and `--exclude NAME` are exact, case-sensitive basename exclusions. Despite the word “pattern” sometimes used informally, do not interpret the value as a regular expression or glob. At every directory level that is constructed, omit a child exactly when its final displayed basename equals any supplied exclusion value. Omitting a directory omits its whole subtree and removes all of its bytes from constructed ancestor totals. The root path itself is never filtered.

`-H`/`--no-hidden` omits every constructed child whose basename starts with `.`, recursively at constructed levels. Hidden entries are included by default. `-f`/`--files-only` omits every constructed child for which the path resolves as a directory (including a symlink whose target is a directory). In the usual single-directory case this produces a flat listing of only direct regular files, non-directory links, and other non-directory entries, does not descend into omitted directories, and removes their sizes from the root total. Filters compose and are applied before aggregation.

## Spec 10

Aggregation is disabled unless `-a`, `--aggr`, or summary mode is present. The aggregation value must match one or more decimal digits followed by at most one nondigit character. The optional suffix is case-insensitive: `B` or no suffix means bytes, `K` means 1024, `M` means 1024², `G` means 1024³, and `T` means 1024⁴. Any other single-character suffix also falls back to bytes. Values such as `abc`, `1MB`, and `1.5M` are invalid. A negative value is invalid. Zero is accepted and effectively disables aggregation.

At each constructed directory, after recursively calculating a retained child, compare that child's entire byte total with the threshold. A child strictly smaller than the threshold is not displayed individually. Sum all such children into one leaf named `<aggregated>`, append that leaf after all sorted nonaggregated children, and use the sum for its bytes. A child exactly equal to the threshold remains visible. Do not emit a bucket when its sum is zero; therefore zero-byte children disappear under any positive threshold without creating a zero-size bucket. Aggregation preserves the parent's total because the bucket replaces the summed children.

## Spec 11

`-s` and `--summary` forcibly select depth 1 and an aggregation threshold of 1 MiB (1,048,576 bytes). This override occurs after parsing all other options, so summary has the same output as explicit `-d1 -a1M` and wins over another parsed depth or aggregation setting when the combination itself is syntactically legal. It still composes with usage, bytes, files-only, exclusion, hidden filtering, ASCII, and color rules.

All independent switches compose: `-u` chooses the number being calculated, `-b` chooses how that number is printed, `-d` chooses visible depth, filters choose retained entries, `-a` groups retained entries, and `-A` selects the bar/color presentation. Option order does not otherwise alter output, and options may appear after a path.

## Spec 12

Size formatting uses binary powers of 1024 and these exact suffixes. In normal mode:

- 0 through 1023: integer plus ` B`, such as `0 B` or `256 B`;
- 1024 through 1024²−1: value divided by 1024, two decimals, plus ` KiB`;
- 1024² through 1024³−1: two decimals plus ` MiB`;
- 1024³ through 1024⁴−1: two decimals plus ` GiB`;
- 1024⁴ and above: two decimals plus ` TiB`.

The conversions and rounding match IEEE-754 single-precision (`f32`) arithmetic followed by fixed two-decimal formatting. With `-b`/`--bytes`, print every magnitude as an ungrouped integer followed by ` B`; never use commas, scientific notation, or a decimal point. The header uses the size string directly. On entry rows the complete size string is right-aligned in a field of 13 display columns.

## Spec 13

When output is not attached to a terminal, use a total row width of 80 columns; do not treat the `COLUMNS` environment variable alone as a terminal-width override. When a terminal-width query succeeds, use that reported width. Let `T` be the width, `variable = T - 15`, `tree_name_width = max(25, floor(variable * 25 / 100))`, and `bar_width = variable - tree_name_width`. The normal captured-test layout at `T=80` therefore uses a 25-column tree/name area and a 40-column bar/percentage area.

Each non-root row starts with ancestor prefixes of width 3: `│  ` while a later sibling remains at that ancestor level, or three spaces after the ancestor's last child. Then print `├─ ` for a nonlast child or `└─ ` for the last. These Unicode tree glyphs are used in both normal and `-A` mode. Pad or truncate the name so the complete prefix plus name occupies exactly `tree_name_width` display columns, then print one space, the bar/percentage from Spec 14, one space, and the 13-column size. At width 80 the two vertical bar delimiters are at zero-based display columns 26 and 60 and every ordinary row is exactly 80 display columns.

The root header is not width-limited. If nesting consumes the whole name area (`3 * displayed-level > tree_name_width`), omit that row and its printed descendants. This is only a presentation limit; its bytes have already contributed to ancestors.

## Spec 14

Filename width and truncation are Unicode-display aware. Segment names into extended grapheme clusters and never split a cluster. Charge a cluster the sum of its component code-point widths rather than collapsing an emoji ZWJ sequence to the width with which a modern terminal may render the whole sequence. In particular, `👩‍👩‍👧‍👦` is one indivisible cluster but consumes 8 columns: four width-2 emoji joined by zero-width joiners. Consider every cluster in order, appending it if it fits in the still-available name width; if a cluster does not fit, skip that cluster but continue considering later clusters. Thus a top-level name `xxxxxxxxxxxxxxxxxxxx👩‍👩‍👧‍👦Z` is rendered as `xxxxxxxxxxxxxxxxxxxxZ` in its 22-column name allowance. This handling must preserve valid UTF-8 for combining characters, emoji sequences, zero-width characters, bidirectional text, accented Latin, Cyrillic, Arabic, and double-width CJK/Korean/Japanese characters. Pad according to the same calculated display width. For example, at the default width a top-level name receives 22 columns after its 3-column branch prefix, so a longer ASCII name is truncated to its first 22 characters.

Color escape sequences have zero display width and do not alter alignment. Truncation is performed on the uncolored name before escapes are inserted.

## Spec 15

Every entry row contains a proportional graph and an immediate-parent percentage. The graph is deliberately based on the largest displayed direct child of the overall root, and descendants retain their top-level ancestor's horizontal extent while different Unicode shades show nested proportions.

The following algorithm is normative. Let `bar_width` be from Spec 13 and `W = bar_width - 2 - 5` (33 at an 80-column width). For a current row, build `values = [root_total, top_level_size, ..., current_size]`. Let `max_bytes` be the maximum size among the root's displayed direct children, or the root size if it has no children. Use palette `[space, '#']` in ASCII mode and `[space, '░', '▒', '▓', '█']` otherwise.

Initialize an iterator to the values after `root_total`; `total = max_bytes`; `part = top_level_size`; `bars = 0` if `total == 0`, otherwise integer-floor `(part * W) / total`; `pos = W - bars`; and palette index `c = 0`. For each integer `x` from 0 through `W-1`, first do the following when `x > pos`: set `total = part`; advance `part` to the next descendant value, or 0 if there is none; set `bars = 0` if `total == 0`, otherwise integer-floor `(part * bars) / total`; set `pos = W - bars`; increment `c`; and if `c` equals the row depth (`len(values)-1`) or exceeds the palette, clamp it to the palette's final glyph. Then append palette glyph `c`. This intentional `x > pos` rule leaves one leading space even for a full-width maximum bar.

Render the result as `│<W glyphs>│ <percentage>`, where percentage is integer-floor `current_size * 100 / immediate_parent_size`, or zero for a zero parent, formatted right-aligned to three digits followed by `%`. At width 80, an ASCII maximum is therefore `│ ################################│`, not 33 hash characters. `-A` changes the graph shades to `#` but does not replace the tree's `│`, `├`, `└`, or `─` glyphs.

## Spec 16

Coloring is disabled completely by `-A`/`--ascii`. Otherwise, parse `LS_COLORS` and wrap only displayed child names (never the root header or padding) as `ESC[<code>m<name>ESC[0m`. An unset or empty variable means no name colors. Codes are opaque strings: numeric SGR sequences, semicolon sequences, Unicode text, or strings such as `dircode` are inserted verbatim.

Parse colon-separated entries from left to right. Stop parsing entirely at the first empty entry, so a trailing colon is harmless and a double colon ignores everything after it. Remove every literal double-quote from a nonempty entry, split it on `=`, and store its first key and first value. Empty values are allowed. Repeated keys use the last stored value before parsing stops.

Choose a color in this priority order:

1. For a symlink, read its target. If that returned path exists as written (an absolute path is checked absolutely and a relative target is checked relative to the process working directory), use `ln`; otherwise use `or`, when the respective key exists.
2. For a directory with the other-write permission bit, use `ow` when present; otherwise use `di` when present.
3. For any entry with at least one execute permission bit, use `ex` when present.
4. For an entry with a final extension, find a key exactly of the form `*.<that-final-extension>` and use it. Compound names use only the rightmost extension.
5. For a regular file, use `fi` when present.
6. For any remaining special type, use `bd` when present.

If none applies, leave the name uncolored. A key such as `.txt` without `*` is not an extension rule.

## Spec 17

`LS_COLORS` parsing occurs for every ordinary scan, even in `-A` mode, and occurs before path and aggregation-value validation. A nonempty colon component without `=` is a documented fatal case rather than an ignored component. Exit nonzero and emit a Rust-style panic diagnostic on standard error. Tests require the diagnostic to contain both `panicked at src/lib.rs:<error location>` and ``called `Option::unwrap()` on a `None` value``. Help, version, and syntactic option-parser errors occur before this environment parsing and therefore do not trigger that panic.

Quotes around keys or values are stripped rather than treated as syntax. Empty values are accepted, and unknown nonempty keys and their values do not themselves fail parsing; unknown keys simply have no coloring effect unless they match one of Spec 16's categories. An empty key is instead fatal: with `LS_COLORS` set to `=EMPTY:unknown=anything`, an ordinary scan exits 101, writes nothing to standard output, and emits a Rust panic containing `panicked at src/lib.rs:<error location>` and <code>byte index 2 is out of bounds of ``</code> on standard error.

## Spec 18

Filesystem errors encountered after root validation are nonfatal to the overall scan. If opening a directory or obtaining metadata fails, continue with other entries, substitute zero where metadata could not be read, and write a diagnostic such as `Couldn't read <basename> (<error-kind>)\n` to standard error. If reading an individual directory entry fails, write `Couldn't read entry (<error-kind>)\n` and skip that entry. An unreadable directory should still be represented using whatever metadata is available; an unreadable regular file can still report its metadata size. Empty directories, zero-sized parents, huge sparse files, deeply nested trees, files with no extension, executable files, world-writable directories, devices, and both working and orphaned links must be handled without arithmetic exceptions or traversal loops.

The tree traversal must be fast enough for directories containing thousands of files and deep but finite nesting, and a scan must never recurse through a symlink. Output ordering, totals, filtering, aggregation, formatting, and color selection must remain the same when the relevant options are combined.
