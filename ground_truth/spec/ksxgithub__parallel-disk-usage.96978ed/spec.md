# Clarified specification for `executable`

The required artifact is one directly runnable program named exactly `executable`. It is a single-command, UTF-8 command-line disk-usage analyzer. All byte counts and arithmetic described below must use unsigned 64-bit-or-wider arithmetic. Unless a rule explicitly says otherwise, successful operations exit with status 0, write their result to standard output, and do not write a diagnostic to standard error.

## Spec 1

The command synopsis is `executable [OPTIONS] [FILES]...`; there are no subcommands. Every non-option token is a file-system path, including words such as `add` or `remove`. `--` ends option parsing, so a token such as `--no-such-flag` after `--` is a path. Options may precede or follow paths.

With no paths, analyze `.`. With one path, analyze that file or directory. With multiple paths, compare all of them beneath a synthetic root named `(total)`. A normal scan produces a Unicode text chart; `--json-output` selects JSON instead. A run must finish promptly for ordinary trees of hundreds of entries and for nested trees at least 25 levels deep (the harness normally imposes a five-second timeout).

The defaults are:

- quantity: `block-size`;
- byte formatting: `metric`;
- maximum displayed depth: 10;
- minimum displayed ratio: 0.01;
- sorting enabled;
- bottom-up chart direction;
- left-aligned bars;
- thread selection: `auto`;
- default total chart width when no usable terminal width is available: 150 character cells.

The depth and ratio defaults above apply when constructing output from a filesystem scan. JSON-input reflection has the explicit exceptions in Spec 19: it accepts depth and ratio options but does not apply either filter to the supplied tree.

## Spec 2

When `--help` is reached before any parsing error, it exits 0 and prints the following exact UTF-8 text to stdout (including the final newline and blank lines). It prints nothing to stderr. The executable name in the usage line is always the literal word `executable`.

```text
Summarize disk usage of the set of files, recursively for directories.

Copyright: Apache-2.0 © 2021 Hoàng Văn Khải <https://github.com/KSXGitHub/>
Sponsor: https://github.com/sponsors/KSXGitHub

Usage: executable [OPTIONS] [FILES]...

Arguments:
  [FILES]...
          List of files and/or directories

Options:
      --json-input
          Read JSON data from stdin

      --json-output
          Print JSON data instead of an ASCII chart

  -b, --bytes-format <BYTES_FORMAT>
          How to display the numbers of bytes

          Possible values:
          - plain:  Display plain number of bytes without units
          - metric: Use metric scale, i.e. 1K = 1000B, 1M = 1000K, and so on
          - binary: Use binary scale, i.e. 1K = 1024B, 1M = 1024K, and so on
          
          [default: metric]

  -H, --deduplicate-hardlinks
          Detect and subtract the sizes of hardlinks from their parent directory totals
          
          [aliases: --detect-links, --dedupe-links]

      --top-down
          Print the tree top-down instead of bottom-up

      --align-right
          Set the root of the bars to the right

  -q, --quantity <QUANTITY>
          Aspect of the files/directories to be measured

          Possible values:
          - apparent-size: Measure apparent sizes
          - block-size:    Measure block sizes (block-count * 512B)
          - block-count:   Count numbers of blocks
          
          [default: block-size]

  -d, --max-depth <MAX_DEPTH>
          Maximum depth to display the data. Could be either "inf" or a positive integer
          
          [default: 10]
          [aliases: --depth]

  -w, --total-width <TOTAL_WIDTH>
          Width of the visualization
          
          [aliases: --width]

      --column-width <TREE_WIDTH> <BAR_WIDTH>
          Maximum widths of the tree column and width of the bar column

  -m, --min-ratio <MIN_RATIO>
          Minimal size proportion required to appear
          
          [default: 0.01]

      --no-sort
          Do not sort the branches in the tree

  -s, --silent-errors
          Prevent filesystem error messages from appearing in stderr
          
          [aliases: --no-errors]

  -p, --progress
          Report progress being made at the expense of performance

      --threads <THREADS>
          Set the maximum number of threads to spawn. Could be either "auto", "max", or a positive integer
          
          [default: auto]

      --omit-json-shared-details
          Do not output `.shared.details` in the JSON output

      --omit-json-shared-summary
          Do not output `.shared.summary` in the JSON output

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version

Examples:
    Show disk usage chart of current working directory
    $ pdu

    Show disk usage chart of a single file or directory
    $ pdu path/to/file/or/directory

    Compare disk usages of multiple files and/or directories
    $ pdu file.txt dir/

    Show chart in apparent sizes instead of block sizes
    $ pdu --quantity=apparent-size

    Detect and subtract the sizes of hardlinks from their parent nodes
    $ pdu --deduplicate-hardlinks

    Show sizes in plain numbers instead of metric units
    $ pdu --bytes-format=plain

    Show sizes in base 2¹⁰ units (binary) instead of base 10³ units (metric)
    $ pdu --bytes-format=binary

    Show disk usage chart of all entries regardless of size
    $ pdu --min-ratio=0

    Only show disk usage chart of entries whose size is at least 5% of total
    $ pdu --min-ratio=0.05

    Show disk usage data as JSON instead of chart
    $ pdu --min-ratio=0 --max-depth=inf --json-output | jq

    Visualize existing JSON representation of disk usage data
    $ pdu --json-input < disk-usage.json
```

`--help` does not override a parsing error caused by an earlier argument. In particular, `executable --definitely-invalid --help` exits 2, writes nothing to stdout, and writes exactly the following to stderr, including the final newline:

```text
error: unexpected argument '--definitely-invalid' found

  tip: to pass '--definitely-invalid' as a value, use '-- --definitely-invalid'

Usage: executable [OPTIONS] [FILES]...

For more information, try '--help'.
```

`-h` may print a shorter form, but it must exit 0 to stdout, leave stderr empty, and contain the same synopsis, `Options:`, `Examples:`, and a mention of `--help`. Printing the exact long form for `-h` is valid.

## Spec 3

`--version` and `-V` print exactly `pdu 0.21.1` followed by one newline, exit 0, and leave stderr empty. The embedded JSON producer version is likewise `0.21.1`.

Recognize all options and aliases documented in Spec 2. Options taking one value accept both `--option=value` and `--option value`; short byte-format also accepts `-bplain`, `-b=plain`, and `-b plain`. `--column-width` consumes exactly two unsigned integer values. A repeated occurrence of the same option or boolean flag is a parse error (status 2); diagnostics must contain `cannot be used multiple times` where applicable and identify the repeated option. Diagnostics canonicalize a repeated short boolean flag to its long name. In particular, `--json-output -p -p --max-depth=1 .` reports `error: the argument '--progress' cannot be used multiple times`, and `--json-output -s -s --max-depth=1 .` reports `error: the argument '--silent-errors' cannot be used multiple times` (each followed by the usage and help paragraphs).

## Spec 4

Command-line syntax and value-validation failures exit 2, write no normal result, and use clap-style diagnostics on stderr. The accepted enumerations are exactly:

- `--bytes-format`/`-b`: `plain`, `metric`, `binary`;
- `--quantity`/`-q`: `apparent-size`, `block-size`, `block-count`;
- `--threads`: `auto`, `max`, or a positive nonzero native-size integer;
- `--max-depth`/`--depth`/`-d`: `inf` or a positive nonzero 64-bit integer;
- `--min-ratio`/`-m`: a decimal floating-point value in `[0, 1)`, or an optional sign followed by an ASCII-case-insensitive `NaN`. The observed spellings `NaN`, `nan`, `NAN`, `+NaN`, and `-NaN` are accepted. A NaN ratio excludes no nodes during a filesystem scan. Positive infinity still fails as greater than or equal to 1, and negative infinity still fails as less than 0.

For the following invocations, stderr after removal of leading/trailing whitespace must be exactly the shown text:

```text
$ executable --bytes-format=invalid
error: invalid value 'invalid' for '--bytes-format <BYTES_FORMAT>'
  [possible values: plain, metric, binary]

For more information, try '--help'.

$ executable --quantity=invalid
error: invalid value 'invalid' for '--quantity <QUANTITY>'
  [possible values: apparent-size, block-size, block-count]

For more information, try '--help'.

$ executable --max-depth=-1
error: invalid value '-1' for '--max-depth <MAX_DEPTH>': Value is neither "inf" nor a positive integer: invalid digit found in string

For more information, try '--help'.

$ executable --max-depth=0
error: invalid value '0' for '--max-depth <MAX_DEPTH>': Value is neither "inf" nor a positive integer: number would be zero for non-zero type

For more information, try '--help'.

$ executable --max-depth=abc
error: invalid value 'abc' for '--max-depth <MAX_DEPTH>': Value is neither "inf" nor a positive integer: invalid digit found in string

For more information, try '--help'.

$ executable --threads=-5
error: invalid value '-5' for '--threads <THREADS>': Value is neither "auto", "max", nor a number: invalid digit found in string

For more information, try '--help'.

$ executable --threads=0
error: invalid value '0' for '--threads <THREADS>': Value is neither "auto", "max", nor a number: number would be zero for non-zero type

For more information, try '--help'.

$ executable --min-ratio=-0.5
error: invalid value '-0.5' for '--min-ratio <MIN_RATIO>': less than 0

For more information, try '--help'.

$ executable --min-ratio=1.5
error: invalid value '1.5' for '--min-ratio <MIN_RATIO>': greater than or equal to 1

For more information, try '--help'.

$ executable --min-ratio=1.0
error: invalid value '1.0' for '--min-ratio <MIN_RATIO>': greater than or equal to 1

For more information, try '--help'.

$ executable --min-ratio=abc
error: invalid value 'abc' for '--min-ratio <MIN_RATIO>': invalid float literal

For more information, try '--help'.
```

The spelling supplied by the caller is retained in the first diagnostic line, so `--min-ratio=1` says `invalid value '1'` and `greater than or equal to 1`. Overflow diagnostics are exactly:

```text
$ executable --max-depth=99999999999999999999999999999999
error: invalid value '99999999999999999999999999999999' for '--max-depth <MAX_DEPTH>': Value is neither "inf" nor a positive integer: number too large to fit in target type

For more information, try '--help'.

$ executable --threads=99999999999999999999999999999999
error: invalid value '99999999999999999999999999999999' for '--threads <THREADS>': Value is neither "auto", "max", nor a number: number too large to fit in target type

For more information, try '--help'.
```

Supplying only one column width produces exactly:

```text
error: 2 values required for '--column-width <TREE_WIDTH> <BAR_WIDTH>' but 1 was provided

Usage: executable [OPTIONS] [FILES]...

For more information, try '--help'.
```

An unknown option exits 2 and includes `unexpected argument '<token>' found`, the tip `to pass '<token>' as a value`, the usage line, and `For more information, try '--help'.` If `--max-depth -1` is written without `=`, `-1` is treated as an unexpected option-like argument and gets that same tip; `--max-depth=-1` instead gets the value error above.

## Spec 5

`--total-width` and `--column-width` are mutually exclusive. Their exact status-2 diagnostic for `--total-width=100 --column-width 30 50` is:

```text
error: the argument '--total-width <TOTAL_WIDTH>' cannot be used with '--column-width <TREE_WIDTH> <BAR_WIDTH>'

Usage: executable --total-width <TOTAL_WIDTH> [FILES]...

For more information, try '--help'.
```

Each JSON omission flag requires both `--json-output` and `--deduplicate-hardlinks`; missing a required option is a status-2 parser error that identifies the relevant JSON or hard-link requirement.

`--json-input` conflicts at parse time with an explicitly supplied `--quantity`; this exact invocation emits status 2 and:

```text
error: the argument '--json-input' cannot be used with '--quantity <QUANTITY>'

Usage: executable --json-input [FILES]...

For more information, try '--help'.
```

Visualization options such as byte format, width, direction, and alignment remain usable with `--json-input`. Depth and ratio options are syntactically accepted in this mode but are ignored as specified in Spec 19. `--json-output` may also accompany `--json-input`; input mode still wins and produces a chart. However, any positional path alongside `--json-input` is detected after parsing and exits 4 with exactly:

```text
[error] JsonInputArgConflict: Arguments exist alongside --json-input
```

## Spec 6

Build a complete in-memory tree before applying display depth or ratio filters. Each node has a name, a measured integer size, and ordered children. For a single explicit root, preserve the root spelling exactly as supplied (absolute paths remain absolute and `.` remains `.`). Descendants are named by their basename only. With no explicit path the root is `.`. With at least two roots, use `(total)` and name each immediate child with the corresponding path spelling. The normal recursive size sort also applies at this synthetic level; `--no-sort` instead preserves argument order there.

The size of a directory is its own measured metadata quantity plus the sizes of all recursively visited descendants. The synthetic `(total)` size is the sum of its root children. A file is a leaf with `children: []`. A single file input produces exactly one chart row, named with that input path and marked 100%.

## Spec 7

Use Unix no-follow metadata and never traverse symbolic links. Both valid and broken symlinks encountered inside a directory are retained as childless nodes. Measure each link from its own no-follow metadata using the selected quantity; for apparent size this is the link's own `st_size`, not the target's size. A link to a directory therefore does not introduce a second copy of the target subtree. An explicit symlink root is likewise a measured leaf. If a real directory and a symlink to it are supplied as two roots, keep both beneath the synthetic `(total)` root; with normal sorting the larger real directory precedes the symlink leaf in the observed case, while `--no-sort` preserves argument order.

Names must be handled as UTF-8 for all tested Unicode, spaces, quotes, apostrophes, dashes, and other ordinary special characters. JSON escaping must preserve the decoded names exactly. Support wide directories with at least 150 files, trees with at least 500 small files, long path components near normal file-system limits, binary file contents, empty files, files around 100 MiB, and sparse apparent sizes of at least 1 GiB without overflow or recursion failure.

## Spec 8

File-system access failures do not make an otherwise valid scan fail. On a missing path, emit a filesystem diagnostic to stderr, represent the failed path as a zero-sized leaf bearing that exact path before output filters are applied, and exit 0. The diagnostic has the form:

```text
[error] symlink_metadata "/nonexistent/path": No such file or directory (os error 2)
```

Substitute the real path and operating-system message. A failed directory read similarly uses an `[error] read_dir ... Permission denied ...` line and scanning continues with accessible entries. With multiple roots, failed roots are subject to the same ratio filtering as other non-root nodes. Consequently, with one missing root and one nonempty valid file, the default ratio excludes the zero-sized missing root from `(total)` while retaining the valid file; the missing-path diagnostic is still emitted and the command exits 0. With `--min-ratio=0`, both children are retained.

The one-row chart for `/nonexistent/path/xyz/that/does/not/exist` begins exactly `0    ┌──/nonexistent/path/xyz/that/does/not/exist`: after the size `0` there are four spaces before `┌`. One is the size/tree separator and three are the root's structural indentation.

`--silent-errors`, `-s`, and `--no-errors` suppress filesystem diagnostics only; the zero node and normal stdout result remain, and status remains 0. Parser and malformed-JSON errors are never suppressed.

## Spec 9

Measurement is selected independently for every invocation:

- `apparent-size` uses `st_size` for every visited entry, including a symlink's own no-follow metadata, and recursively sums it. Thus directory metadata contributes to its directory and ancestors.
- `block-count` uses the Unix `st_blocks` count (units of 512-byte blocks) for every visited entry and recursively sums it. JSON declares the unit as `blocks`.
- `block-size`, the default, uses `st_blocks * 512` bytes and recursively sums it. JSON declares the unit as `bytes`.

For an ordinary 8,192-byte allocated file, apparent size is exactly 8192, block count is at least 16, and block size is at least 8192. Empty files may be zero. On the evaluation filesystem, a fully allocated 100 MiB file reports exactly 104857600 bytes and 204800 blocks; the parent `/tmp/test_size_blocks_json` has the same aggregate block count when its own `st_blocks` is zero.

`--quantity` and `-q` are equivalent. Byte-format choices are accepted with every quantity; block counts themselves are always displayed as unscaled plain integers.

## Spec 10

In chart output, format byte quantities as follows:

- `plain`: unsigned decimal digits only, with no separators or suffix;
- `metric` (default): use thresholds and divisors 1000, 1000², 1000³, ... with suffixes `K`, `M`, `G`, ...;
- `binary`: use thresholds and divisors 1024, 1024², 1024³, ... with the same short suffixes `K`, `M`, `G`, ... (not `KiB`/`MiB`).

Values below the first threshold are plain integers. Scaled values have exactly one digit after the decimal point and use ordinary nearest rounding: metric 500000 is `500.0K`; binary 500000 is `488.3K`; binary 104857600 is `100.0M`. Zero is `0`. Align the size column to the right using the widest formatted size among displayed rows, followed by one space before the tree column.

JSON sizes are never human-formatted and are not affected by `--bytes-format`; they are integer counts in the top-level declared unit.

## Spec 11

By default, recursively sort every node's children by descending numeric size, including the children of synthetic `(total)`. Sorting is stable for equal sizes, thereby retaining filesystem enumeration order for ties and argument order for equal-sized synthetic roots. JSON exposes this descending order. Bottom-up chart traversal reverses that sibling order as part of reversing the tree display, so smaller siblings normally print first and the root prints last.

`--no-sort` disables this recursive size sort and preserves the enumeration order returned by the filesystem in JSON. A bottom-up chart still performs bottom-up/reversed traversal of that preserved tree. It must not accidentally return to descending size order. At synthetic `(total)`, the preserved order is input argument order.

## Spec 12

For filesystem-scan output, `--max-depth=N`, `--depth=N`, and `-d N` limit only emitted nodes; scanning and size aggregation still include deeper descendants. Count the root as depth 1. Therefore depth 1 emits only the root with its fully aggregated size and empty JSON `children`; depth 2 emits the root and its immediate children but makes those children childless in the emitted representation. `inf` means unlimited depth. The scan-mode default is 10. JSON-input reflection is the exception: it emits the complete supplied tree for `1`, `2`, `inf`, and the default, as detailed in Spec 19.

As a precise chart example, create `.` with `flat/{0,1,2,3}` of 0, 100000, 200000, and 300000 bytes, `nested/0/1` of 500000 bytes, and an empty `empty-dir`; then run `executable --quantity=apparent-size --total-width=100 --max-depth=1`. On the evaluation filesystem, stdout is exactly:

```text
1.1M ┌──.│█████████████████████████████████████████████████████████████████████████████████████│100%
```

including its final newline.

## Spec 13

For output constructed by a filesystem scan, `--min-ratio=R` retains the root and retains another node only when `node.size / root.size >= R`, using the same complete root size even for deeply nested nodes. An excluded node's descendants are also excluded. If root size is zero, retain the root; with `R=0`, retain every node, including zero-sized nodes. The scan-mode default is 0.01. Filtering applies to both scanned chart and JSON output and combines with depth limiting. It does not apply when reflecting an already supplied JSON tree: JSON-input mode emits nodes below an explicit or default ratio threshold.

Percentages in the chart are independently rounded to the nearest whole percent from `100 * node.size / root.size`, clamped to 0 through 100, and right-aligned in a four-cell field such as `  0%`, `  7%`, or `100%`. For a zero-size root, show `0%`. Very tiny retained entries can therefore display `0%`, while a dominant file may round to `100%` even beneath a slightly larger root.

## Spec 14

Every normal chart row has this layout with no header:

```text
<right-aligned size><space><padded tree cell>│<fixed-width bar cell>│<4-cell percentage>
```

Terminate every emitted row with `\n`. Use the Unicode tree characters `│`, `─`, `┌`, `├`, `└`, `┬`, and `┴`. A bottom-up root with visible children contains `┌─┴<root-name>`; a childless bottom-up root contains `┌──<root-name>`. Middle siblings use `├`. A top-down root with children contains `└─┬<root-name>`, and ordinary top-down child connectors use `├──`/`└──` or `├─┬`/`└─┬` according to sibling position and visible children. Vertical `│` strokes connect ancestry.

Default bottom-up is postorder: descendants before their parent and the root last. `--top-down` is preorder: root first and then children in descending-size order. Direction changes tree junctions as described, not just line order. The root connector itself has three leading structural spaces in the tree cell; combined with the one separator after a one-character size, a one-row leaf begins `<size>    ┌──<name>`.

## Spec 15

The bar cell visualizes a node and the chain of non-root ancestors using `█`, `▒`, and `░`, with spaces for the portion outside that chain. Its full scale is the root size. Compute each node's cumulative bar endpoint as nearest-integer `bar_width * node.size / root.size`. Draw the current node's interval from zero to its endpoint with `█`. For each successive non-root ancestor, extend from the previous endpoint to that ancestor's endpoint using a lighter shade: the tested hierarchy uses `▒` for the immediate depth-2 ancestor layer and `░` for the depth-1/root-child layer. Root is all `█`. This produces multiple visibly distinct bar patterns and the glyphs `█`, `▒`, and `░` in a sufficiently varied three-level tree.

Normally this constructed bar is anchored at the left and padded on the right. `--align-right` reverses the bar cell horizontally: padding comes first, ancestor shades occur in reverse spatial order, and the node's solid segment ends at the right. It must materially change nontrivial chart output and compose with top-down and narrow-width output without corrupting the two `│` separators.

For JSON input consisting of this compact semantic object:

```json
{"schema-version":"2024-11-02","pdu":"0.21.1","unit":"bytes","tree":{"name":"test","size":100,"children":[{"name":"child1","size":50,"children":[]},{"name":"child2","size":30,"children":[]}]}}
```

the default-width bottom-up stdout must be exactly:

```text
 30      ┌──child2│██████████████████████████████████████                                                                                        │ 30%
 50      ├──child1│███████████████████████████████████████████████████████████████                                                               │ 50%
100    ┌─┴test    │██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████│100%
```

including the final newline.

## Spec 16

`--column-width TREE BAR` sets the maximum tree-cell width and the exact bar-cell width. If every untruncated tree cell is shorter than `TREE`, use the natural maximum instead and pad the actual tree cells to that width. The tree cell begins only after the separately right-aligned size column and its one separator space. Consequently, splitting a complete row at its first ASCII space does not locate the tree-cell boundary and can yield unequal remaining-prefix lengths when formatted sizes have different digit widths. For the JSON-input tree `root` size 10 with child `x` size 5 and `--column-width 30 17`, the observed rows begin ` 5   ┌──x ` and `10 ┌─┴root`; the size field is two cells wide and both actual tree cells are seven cells wide (`  ┌──x ` and `┌─┴root`, respectively). If a name would exceed the tree width, retain as much leading text as fits and end the name with exactly `...`. The width includes indentation and connector glyphs. For example, a 20-cell tree column must truncate a moderately long `file_with_a_moderately_long_name.txt`, while a 10-cell tree limit on a nested varied tree produces at least two ellipsized names.

If even a meaningful connector plus an ellipsis cannot fit at a node's structural depth, omit that row and its descendants. Recompute parent child/leaf connectors based only on visible children. In a deeply nested long-name chain at `--total-width=28`, the evaluated layout retains three rows (an ellipsized `c...` child, `parent`, and `.`) and excludes `grandchild` and deeper names.

`--total-width W`, `--width W`, and `-w W` select the complete row width. Reserve the size and four-cell percentage columns plus separators, retain the natural tree width when possible, and assign the rest to the bar. For normal feasible values, rows are exactly `W` character cells; widths 40, 50, 60, 80, 100, 120, 200, 300, and 500 must work, and wider choices yield correspondingly wider bars. Extremely constrained layouts degrade without an error: omit rows that cannot be represented. In particular, `--quantity=apparent-size --total-width=20 .` on a nontrivial multi-level tree emits exactly nothing, while width 25 on a simple `./root_dir/file.txt` tree emits only the root. Width 10 is a special fallback rather than an empty layout: for a temporary directory containing one allocated `file.txt`, it exits 0 and emits two nonempty chart rows, including an ellipsized file row and a root row with formatted decimal size digits. The fallback can exceed 10 cells so that it retains the size, connector/name, separators, minimal bar, and percentage.

## Spec 17

As an exact binary-format fixture, create the fully allocated file `/tmp/test_size_large/large.bin` with 104857600 zero bytes and invoke `executable --bytes-format=binary /tmp/test_size_large` using the default `block-size` quantity and default width. When that directory has zero allocated metadata blocks, stdout is exactly the following two 150-cell rows, including the final newline:

```text
100.0M   ┌──large.bin         │██████████████████████████████████████████████████████████████████████████████████████████████████████████████████│100%
100.0M ┌─┴/tmp/test_size_large│██████████████████████████████████████████████████████████████████████████████████████████████████████████████████│100%
```

An empty directory or zero-size file must still be representable without division errors; an empty single root is shown as one root row. A single normal file likewise produces one row with a full bar and 100%.

## Spec 18

`--json-output` writes exactly one compact UTF-8 JSON object, with no prefix, progress text, pretty-print whitespace, or trailing newline. The top-level insertion/order and required fields are:

```json
{"schema-version":"2024-11-02","pdu":"0.21.1","unit":"bytes","tree":{"name":"...","size":0,"children":[]}}
```

`schema-version` is always the string `2024-11-02`; `pdu` is always `0.21.1`; `unit` is `bytes` for apparent-size and block-size or `blocks` for block-count. Each tree node has exactly `name` (string), `size` (nonnegative integer), and `children` (array), in that order. Apply the root naming, recursive sort, ratio, and depth rules above. JSON must support deep nesting, at least 100 immediate children, Unicode and quote escaping, and exact integer sizes.

For a single path, the JSON root is that real path spelling. For two or more paths it is `(total)`, and immediate children retain their full supplied path spellings. Normal sorting orders those children by descending size; `--no-sort` retains argument order. A missing single path still produces valid JSON with that name, size 0, and empty children while its filesystem error goes to stderr.

## Spec 19

`--json-input` reads one JSON object from stdin, constructs the supplied tree directly, and produces the Unicode chart rather than scanning paths. Even if `--json-output` is also present, output remains a chart and must not contain JSON field labels. Honor input `unit`, node names, sizes, child order, and visualization options other than the two scan-tree filters. Byte formatting may be changed when the input unit is `bytes`. `--min-ratio` and `--max-depth` (including their aliases) are parsed but ignored in JSON-input mode: emit the entire supplied tree at any explicit valid values and under their defaults. Thus a size-9 node under a size-1000 root remains visible with `--min-ratio=0.01`, and a 13-node chain emits all 13 rows with `--max-depth=1`, `--max-depth=2`, or no depth option. An exported full tree can be fed back and must visualize the same sizes, hierarchy, and chart as a direct scan under the same display options.

Required input fields and types are those in Spec 18. Hard-link `shared` information, when present, follows Specs 22–23. Empty or syntactically invalid input exits 3 and reports `[error] DeserializationFailure: ...` on stderr. The following errors are exact:

```text
input: invalid json
[error] DeserializationFailure: expected value at line 1 column 1

input: {}
[error] DeserializationFailure: missing field `schema-version` at line 1 column 2
```

Each diagnostic ends with one newline and stdout is empty.

## Spec 20

Validate a JSON input tree recursively before charting it. Every child's size must be no greater than its immediate parent's size. A violation exits 5 with no chart. For root `test` size 100 and child `child1` size 200, stderr is exactly:

```text
[error] InvalidInputReflection: ExcessiveChildren: "test" (Bytes(100)) is less than a child named "child1" (Bytes(200))
```

For root `root`, child `parent` size 500, and grandchild `child` size 600, it is exactly:

```text
[error] InvalidInputReflection: ExcessiveChildren: "root/parent" (Bytes(500)) is less than a child named "child" (Bytes(600))
```

Use `Blocks(N)` instead of `Bytes(N)` when the input unit is `blocks`. The path in this diagnostic is formed by joining ancestor node names with `/`.

## Spec 21

`--deduplicate-hardlinks`, `-H`, `--detect-links`, and `--dedupe-links` enable Unix hard-link detection. Group regular, non-directory, non-symlink files by `(device, inode)` when `st_nlink > 1`. Directory link counts are structural metadata and must not create hard-link groups; symlinks never belong to these groups. Detection scans the complete selected trees even when display depth later hides a link.

Without this option, every directory entry is counted at its full measured size, all link leaves appear normally, and JSON has no `shared` member. With it, leaves still retain their full individual sizes, but each ancestor aggregate counts one inode instance rather than every detected directory entry: relative to non-deduplicated totals, subtract `(number of detected paths in the aggregate - 1) * measured inode size`. Thus six observed 1000-byte links reduce their common-root total by exactly 5000 bytes. This works for apparent size, block size, and block count.

Hard-link detection must handle groups across subdirectories, multiple groups, empty linked files, at least 101 links to one inode, different path permissions, and groups partly outside the selected roots.

## Spec 22

When hard-link detection is enabled and at least one linked inode is observed, JSON adds top-level `shared` after `tree`. Unless omitted, `shared.details` is an array with one object per linked inode. Every detail object contains:

- `ino`: the positive integer `st_ino`;
- `size`: one instance's measured size in the JSON unit;
- `links`: the inode's global `st_nlink`, including links outside the analyzed trees;
- `paths`: all paths to that inode actually observed within the analyzed roots.

`paths.length` may therefore be smaller than `links`. An absolute root spelling yields absolute observed paths. Scanning relative `.` yields paths beginning `./`, such as `./dir1/original.txt`. A group spanning directories includes each such relative or absolute location exactly once. In block-size mode a small allocated linked file normally has detail size 4096; in apparent mode the same 18-byte content has size 18; in block-count mode sizes are small block integers.

## Spec 23

Unless omitted, `shared.summary` contains these seven integer fields:

```text
inodes, exclusive_inodes, all_links, detected_links,
exclusive_links, shared_size, exclusive_shared_size
```

Their definitions are:

- `inodes`: number of hard-linked inode groups observed;
- `exclusive_inodes`: groups for which `paths.length == links`;
- `all_links`: sum of global `links` over groups;
- `detected_links`: sum of `paths.length`;
- `exclusive_links`: sum of `links` for exclusive groups;
- `shared_size`: sum of one measured `size` per group, not size times link count;
- `exclusive_shared_size`: sum of one measured `size` per exclusive group.

For one fully contained 18-byte inode with three paths, these values are `1, 1, 3, 3, 3, 18, 18` respectively. For one inode having two global links but only one observed path, `exclusive_inodes=0`, `all_links=2`, and `detected_links=1`.

`--omit-json-shared-details` removes only `details`; `--omit-json-shared-summary` removes only `summary`; using both removes the entire `shared` member. If no hard-linked inode is detected, `shared` may be absent (and should be absent when both components would be empty).

## Spec 24

In chart mode with detected hard links, append a human-readable footer after the tree. It begins with `Hardlinks detected!` and includes lines beginning `Number of shared inodes:`, `Total number of links:`, and `Total shared size:` using the same measurement/byte formatting as the chart. Do not print this footer when no hard links are found or when detection was not requested.

The containment explanation and counts distinguish these cases:

- all groups exclusive: include `No files have links outside this tree`; simple counts may be `Number of shared inodes: 1` and `Total number of links: 3`;
- no group exclusive: include `All hardlinks within this tree have links without` and show, for example, `Total number of links: 3 total, 1 detected`;
- mixed groups: include `Some files have links outside this tree`, `Number of shared inodes: 2 total, 1 exclusive`, and `Total number of links: 4 total, 3 detected, 2 exclusive`.

The summary reports one copy as shared size: three 18-byte links display `Total shared size: 18` in plain format.

## Spec 25

When deduplication is enabled, normalize the selected argument set for exact duplicates and ancestor overlap before building the synthetic root. If one selected real path equals or contains another selected real path, retain only the outermost ancestor regardless of argument order. Exact duplicates collapse to one. If this leaves one root, represent it directly rather than under `(total)`; its descendants still appear normally. With no deduplication option, do not collapse duplicates: two occurrences become two same-named children of `(total)` and are both counted.

Do not resolve a symlink as an overlapping alias of its target. Non-overlapping roots are all retained. This argument-level overlap rule composes with inode deduplication across different retained roots.

## Spec 26

`--threads=auto`, `--threads=max`, and any positive numeric setting, including 1, 2, 4, and large valid values, may choose different traversal parallelism but must produce the same measurements and deterministic sorted output. Zero, negative, nonnumeric, and overflowing values fail as specified earlier.

`--progress` and `-p` may emit transient progress updates only to stderr; they must never add bytes to or otherwise alter the final chart/JSON on stdout, tree ordering, sizes, or schema. It is valid for a noninteractive implementation to emit no progress text. Progress must compose successfully with every quantity, byte format, thread setting, depth/ratio/sort/direction/alignment/width option, silent filesystem errors, hard-link detection, JSON output, and JSON omission flags.
