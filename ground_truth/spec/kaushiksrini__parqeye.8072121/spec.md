# parqeye executable specification

The required artifact is one executable file named exactly `executable`. It is a terminal-native, read-only Parquet inspector called **parqeye**. All behavior below belongs to that executable; any command used by a harness to create, drive, or snapshot a terminal is external and is not part of the artifact.

## Spec 1

`executable` shall implement a single-command interface with one required positional argument, a filesystem path to one Parquet file. It has no subcommands and no global verbose, quiet, debug, input, or output options. Words such as `add`, `remove`, and `list` are paths, not commands. A file's extension is irrelevant: content, rather than the name, determines whether it is Parquet.

The only accepted options are `-h`/`--help` and `-V`/`--version`. Options are case-sensitive. In particular, `-H`, `--HELP`, and `--VERSION` are invalid.

## Spec 2

Both help forms shall exit with status 0, write nothing to standard error, and write exactly the following UTF-8 text to standard output, including the final newline:

```text
Command line tool to visualize parquet files

Usage: executable <PATH>

Arguments:
  <PATH>  Path to the parquet file

Options:
  -h, --help     Print help
  -V, --version  Print version
```

The help output contains no ANSI escape sequences and does not advertise subcommands. Help is an immediate action: `--help some-file`, `some-file --help`, and `--help --version` all print only this help and succeed, provided no invalid option occurs before the help option. Thus `--foo --help` is an argument error rather than help.

## Spec 3

Both version forms shall exit with status 0, write nothing to standard error, and write exactly this line, including its final newline, to standard output:

```text
parqeye 0.0.2
```

Version is an immediate action and does not require a path. Once encountered, it ignores later positional arguments, so `--version extra` prints only the version and succeeds. A value form such as `--version=1` is invalid.

Displaying help or version must not inspect a file, initialize the interactive terminal, or validate environment configuration.

## Spec 4

Command-line syntax errors exit with status 2, emit nothing on standard output, and put their complete message on standard error. These diagnostics use exactly the following templates and blank lines:

No path, including an invocation containing only `--`:

```text
error: the following required arguments were not provided:
  <PATH>

Usage: executable <PATH>

For more information, try '--help'.
```

An extra positional argument `VALUE`:

```text
error: unexpected argument 'VALUE' found

Usage: executable <PATH>

For more information, try '--help'.
```

An unknown option `OPTION`:

```text
error: unexpected argument 'OPTION' found

  tip: to pass 'OPTION' as a value, use '-- OPTION'

Usage: executable <PATH>

For more information, try '--help'.
```

Each template ends in a newline. With two or more positionals, `VALUE` is the second positional even if more follow. For `--unknown=value`, report `--unknown`, not the entire token. For `-file.parquet`, report the first unrecognized short option, `-f`. The value error for `--version=1` begins `error: unexpected value '1' for '--version' found` and includes the same usage and more-information footer.

## Spec 5

The token `--` ends option parsing. A following option-looking token becomes the one path value. For example, `executable -- --unknown` attempts to launch the application on a file literally named `--unknown`; it must not report an unexpected-argument syntax error. A single `-` likewise means a literal path named `-`, not standard input. Redirected standard input never substitutes for the required path. A form such as `--path=file.parquet` is unsupported and is an option error.

Path arguments are preserved exactly for display and accepted as distinct argument-vector values, including relative and absolute paths, `.`/`..` components, spaces, shell punctuation, long components, and Unicode. Normal filesystem lookup semantics apply, including following valid symbolic links and reporting broken or cyclic links. The application never executes text embedded in a filename.

## Spec 6

For a syntactically valid path invocation, interactive terminal initialization occurs before the file is opened or parsed. A real terminal/PTY enters an alternate full-screen mode. If standard input/output cannot support an interactive terminal, the process exits nonzero with a runtime-panic diagnostic on standard error containing all of `panicked`, `failed to initialize terminal`, and the underlying `No such device or address`. This is an application/runtime failure, not status 2 and not an argument error. This rule also applies to a path introduced after `--`.

On successful interactive startup, the application remains active until a key event requests exit. Lowercase `q` and uppercase `Q` both restore the terminal and exit cleanly with status 0. The implementation must not leave raw mode or the alternate screen active after a normal exit.

## Spec 7

The executable shall read standard Parquet files by interpreting their footer metadata, schema, row groups, column chunks, pages, encodings, compression, definition/repetition levels, and logical types. It shall load file and row-group metadata for the whole file, while loading at most the first 200 logical rows for the data preview. The preview's row-count boundary and navigation boundary are therefore the number actually loaded, at most 200, rather than an unbounded full-file row count.

The parser must support empty datasets, one-row/one-column datasets, hundreds of rows or columns, multiple row groups, very small pages, null-only pages, page counts larger than a signed 16-bit value, page index/bloom metadata, sort-column metadata, and legacy schemas. It must not assume that all fields are optional or that repeated fields always carry modern LIST annotations.

## Spec 8

At minimum, valid inputs may use these physical and logical representations: BOOLEAN, INT32, INT64, INT96, FLOAT, DOUBLE, BYTE_ARRAY, FIXED_LEN_BYTE_ARRAY, strings, signed/unsigned integers, dates, times, timestamps, decimals of differing precision and scale, and 16-bit floats. Nested lists (including lists of lists), repeated unannotated values, and deeply nested structs must be accepted without flattening away their visible structure.

At minimum, pages and values may use PLAIN, PLAIN_DICTIONARY, RLE, RLE_DICTIONARY, DELTA_BINARY_PACKED, DELTA_BYTE_ARRAY, DELTA_LENGTH_BYTE_ARRAY, and BYTE_STREAM_SPLIT encoding, in Data Page V1 or V2 and dictionary pages. Compression support includes UNCOMPRESSED, SNAPPY, ZSTD, raw/non-Hadoop LZ4, and Hadoop-framed LZ4. Page checksums and files combining dictionary/RLE encoding with checksums must be accepted.

The compatibility corpus represented by the supplied assets includes all-types plain/dictionary/Snappy/tiny-page files; binary, decimal, list, nested-list, nested-struct, null, NaN, byte-stream-split, delta, RLE boolean, LZ4, and checksum files. A valid file in any of these categories opens as a TUI and does not print a panic or corruption error.

## Spec 9

The full-screen display is a character grid sized to the current terminal and is redrawn after meaningful key events. Split it vertically into a 3-row header, a flexible content area, and a 1-row footer. At 80 by 24 cells, this means rows 1-3 are the header, rows 4-23 are content, and row 24 is the footer.

The header is a rounded Unicode box (`╭╮╰╯─│`). Its single inner row contains the four tab labels in this order:

```text
Visualize   Metadata   Schema   Row Groups
```

Each tab label has one space of padding on either side and adjacent tabs have a one-space divider. The active tab is visually highlighted. The exact path string supplied by the user is shown in green. Its region is anchored at the right of the header's inner area and has a requested cell width equal to the path's UTF-8 byte length, but the path text is left-aligned within that region. Thus an all-ASCII path ends immediately before the right border, while `rich sample ü.parquet` leaves one space between the path and that border because `ü` occupies one terminal cell but two UTF-8 bytes. The tabs consume whatever width remains. Consequently, a long path clips later tab labels; an even longer path can leave only a prefix such as `Vis` or no tab text. The displayed path itself is clipped at the terminal edge, never wrapped.

The footer starts with bold green `parqeye` at the far left and right-aligns the active view's instructions. All content is clipped to the terminal dimensions and must remain stable on square, wide, tall, and 200-by-60 terminals.

## Spec 10

The initial active view is Visualize. Its footer instruction is exactly:

```text
↑/↓ : Row | →/← : Column | u/d : Page - [Tab] Next Tab, [Q]uit
```

The content is a borderless data table. Reserve a row-number section, then a vertical `│`, then data columns. The first content row contains column names, the second is a full-width `─` separator with `┬` at the row-number divider, and remaining content rows contain records or blanks. Data rows are numbered from 1. At a width of 80 with the usual sampled row counts, the column data begins at column 10 and the vertical divider is at column 7, producing prefixes such as `1     │  `.

The row-number width algorithm is: take the decimal digit count of `sampled_rows - vertical_scroll`, with a minimum of 4; the entire row-number section is that width plus 5 cells, and the separator is after that width plus 2 cells. The number itself is left-aligned at column 1.

## Spec 11

For the Visualize table, calculate available data width after the row-number section. The maximum number of visible data columns is `max(floor(available_width / 12), 1)`. Beginning at the horizontal column offset, take no more than that many columns.

For every chosen column, find the maximum UTF-8 byte length of its header and all sampled values from the current vertical-scroll position onward. Clamp that content width to 8 through 25 inclusive, then add two spacing cells. Headers are left-aligned. If an ASCII header exceeds its content width, retain `content_width - 3` bytes and append three periods (`...`). Values are left-aligned and padded to the complete column width. If a value's Unicode scalar count exceeds the content width, retain `content_width - 1` characters and append the single Unicode ellipsis `…`. Rendering clips anything that reaches the right screen edge; it does not wrap.

There is no visible scrollbar in the data preview. Files with fewer rows simply leave blank rows containing the row-number separator. An 80-by-24 screen can draw 18 records; exactly 18 and 19 sampled rows therefore both initially display rows 1 through 18.

## Spec 12

Preview values use these display conventions:

- null scalar values are `NULL`; nulls nested inside a list are `null`;
- booleans are lowercase `true` and `false`;
- UTF-8 strings, including empty strings, are surrounded by double quotes, so empty is `""` and differs from `NULL`;
- binary values use a byte-string form such as `b"\x00"`; printable bytes may appear literally, as in `b"d"`, while nonprintable bytes use two-digit lowercase `\xNN` escapes;
- lists use brackets and comma-space separators, nested lists retain nesting, and structs use braces;
- integers have no grouping commas and retain their full signed decimal value;
- decimals retain their declared scale, for example `1.00`;
- finite FLOAT and DOUBLE values use the following deterministic compact formatter. First obtain the ordinary shortest decimal representation `s`. Integral values whose absolute value is less than 999999 render with one fractional digit, including `1.0`, `0.0`, and `-0.0`. Otherwise, when `s` is longer than nine characters, magnitudes from 0.000001 through 999999 inclusive render with six fractional digits, rounded and then stripped of trailing zeroes while retaining at least one digit after the decimal point; values outside that magnitude interval use lowercase scientific notation with exactly four fractional digits and no plus sign in a positive exponent. When `s` is at most nine characters, a non-integral value uses `s`, while an integral value uses lowercase scientific notation. Consequently the preview includes forms such as `-1.306527`, `-0.46072`, `-3.141593`, `0.000001`, `0.0000001`, `1.0000e-8`, `9.99999e5`, `999999.1`, `1e6`, and `-1.7977e308`. Special values are `inf`, `-inf`, and `NaN`;
- date/time/timestamp values are human-readable ISO-like values rather than raw INT96 words.

Newline, carriage-return, tab, and other terminal control characters embedded in strings are deleted before display, not escaped or replaced. For example, the value `newline\ncharacter\ttest` displays as `"newlinecharactertest"`, and `carriage\rreturn\x07bell` displays as `"carriagereturnbell"`. They therefore cannot create extra screen rows or execute terminal controls. Unicode, emoji, CJK, and right-to-left text must not crash the renderer. Width clipping follows the rules in Spec 11.

## Spec 13

Visualize navigation maintains a selected preview-row index, a vertical viewport start, and a first-visible-column index, all initially zero.

Up/Down move the selection by one and saturate at row 0 and `sampled_rows - 1`. Let `V = max(terminal_height - 7, 1)`. After a row movement, if selection is above the viewport, set the viewport to the selection; if selection is at or below `viewport + V`, set the viewport to `selection - (V - 1)`. Finally clamp the viewport to at most `sampled_rows - V`. The selected row is bold with a dark background; its row number is bold and underlined.

`u` and `U` move the selection upward by `V`; `d` and `D` move it downward by `V`, with the same saturation and viewport adjustment. Note that at 80 by 24, `V` is 17 even though 18 data rows fit. Thus one page-down from the top of a long file selects logical row 18 and changes the viewport start from 0 to 1, displaying numbered rows 2 through 19. Page-up reverses by 17. The terminal PageUp/PageDown keys, Home/End, and `j`/`k` have no assigned action.

Left/Right move the first-visible-column state by one; Left saturates at zero and Right saturates at `column_count - 1`. At render time the offset is additionally clamped so that a complete terminal-width set of columns can be selected. Repeated Right therefore reaches the rightmost group without overflow; repeated Left returns to the original table.

## Spec 14

Global keys work from every view. Tab advances cyclically through `Visualize -> Metadata -> Schema -> Row Groups -> Visualize`; Shift+Tab/BackTab cycles in reverse. Every tab change resets row selection, data viewport, schema-tree scroll, and horizontal offset to zero. Escape resets those four values without changing the active tab. `q` and `Q` quit.

Unassigned printable keys, including digits, and unassigned control/Alt combinations are ignored. They must not alter the plain-text screen, terminate the program, or produce a panic. Only key-press events act; key-release and unrelated terminal events are ignored.

## Spec 15

The Metadata view derives eleven file-wide values from footer metadata, in this fixed order:

1. `Format version`: the Parquet metadata version as a decimal string.
2. `Created by`: the footer's created-by value, or the em dash `—` when absent.
3. `Rows`: sum of row counts across all row groups, with commas every three decimal digits.
4. `Columns`: number of primitive schema columns.
5. `Row groups`: number of row groups.
6. `Size (raw)`: sum of every column chunk's uncompressed size.
7. `Size (compressed)`: sum of every column chunk's compressed size.
8. `Compression ratio`: raw divided by compressed, to exactly two decimals plus `x`; use `0.00x` when compressed size is zero.
9. `Codecs (cols)`: alphabetically sorted codec-label entries followed immediately by `(count)`, where the count covers column chunks across all row groups, joined by comma-space. Most codec labels are the uppercase codec name, giving forms such as `UNCOMPRESSED(11)`. A ZSTD label also includes its compression-level descriptor before the count: level 1 is `ZSTD(ZstdLevel(1))`, so two such column chunks display as `ZSTD(ZstdLevel(1))(2)`.
10. `Encodings`: unique encoding names, alphabetically sorted and joined by comma-space.
11. `Avg row size`: floor of raw bytes divided by rows, followed by ` B`; use zero when there are no rows.

File-size formatting uses a 1024 base and units `B`, `KiB`, `MiB`, `GiB`, `TiB`. Bytes display with no decimal (`671 B`); larger units display exactly two decimals (`1.50 KiB`). Counts use ordinary comma grouping in this view.

## Spec 16

The Metadata content is a two-column table centered both horizontally and vertically in the content area, surrounded by a rounded border whose centered top title is `File Metadata`. Keys are right-aligned in an 18-cell column. Exactly one ordinary space separates the key and value; there is no internal vertical separator, so the nested-struct fixture visibly contains the contiguous text `Columns 216`. The value column is the greater of 20 and the UTF-8 byte length of the longest value. The requested table width is `18 + value_width + 5` cells including borders; overlong content is clipped rather than wrapped. The metadata footer is exactly:

```text
[Tab] Next Tab, [Q]uit
```

and is right-aligned after the left `parqeye` title. Arrow and paging keys have no effect in this view.

For `alltypes_plain.parquet`, the derived values are version `1`, 8 rows, 11 columns, 1 row group, raw and compressed sizes `671 B`, ratio `1.00x`, codecs `UNCOMPRESSED(11)`, encodings `PLAIN, PLAIN_DICTIONARY, RLE`, and average row size `83 B`. Its created-by value is `impala version 1.3.0-INTERNAL (build 8a48ddb1eff84592b3fc06bc6f51ec120e1fffc9)`.

## Spec 17

Construct the Schema Tree in depth-first file order. The first item is always `└─ root`. Each child is prefixed by three spaces per ancestor, with `│  ` retained beneath non-last ancestors, and uses `├─ name` except for the last sibling, which uses `└─ name`. Keep group nodes as well as primitive leaves, so nested lists and structs visibly preserve all intermediate nodes.

The tree's requested total width, including its two border cells, is the greater of 24 and the maximum UTF-8 byte length of a rendered tree line plus 4. Thus a short tree has a 24-cell outer box and a 22-cell interior; 24 is not a minimum interior/content width. It has a rounded border, centered title `Schema Tree`, and centered bottom legend `Leaf, Group`; append `, Selected` whenever a primitive leaf is selected. Root, group, leaf, and selected items use distinct styles, and a selected leaf has a yellow background with black text.

## Spec 18

The Schema view places the tree on the left and a rounded `Column Statistics` table in all remaining width. The statistics columns, in this exact order, are:

```text
Repetition, Physical, Compressed, Uncompressed, Ratio,
Encodings, Compression, Min, Max, Nulls
```

Each group-node row contains its repetition (`REQUIRED`, `OPTIONAL`, or `REPEATED`) and literal physical value `group`, leaving later cells blank. Each primitive row contains the uppercase physical type; total compressed and uncompressed sizes aggregated across row groups; their ratio to two decimals plus `x` (or `N/A` when unavailable); encoding and codec summaries; decoded aggregate minimum and maximum or `NULL`; and summed null count.

Column size formatting here differs from Metadata: units are `B`, `KB`, `MB`, `GB`, `TB`, base 1024; bytes have no decimal and larger units have one decimal. Aggregate INT32/INT64 statistics decode as little-endian signed integers, FLOAT/DOUBLE as little-endian values with four decimals, UTF-8 byte/fixed arrays as text, and non-UTF-8 statistics as contiguous uppercase hexadecimal.

## Spec 19

For Schema layout, reserve the tree width plus one spacer; if the total number of tree nodes exceeds `content_height - 2`, reserve two extra cells instead and draw a vertical scrollbar beside the tree. The remaining table determines visible statistics columns as `max(floor((remaining_width - 4) / 12), 1)`. It starts at the horizontal offset, and each visible column's width is the maximum of its header and displayed cells, capped at 30, plus one; table column spacing is one.

Up/Down select primitive leaves, not group nodes, from 0 (no selection) through the primitive-column count. Left/Right scroll the statistics fields horizontally. Left decrements the stored offset and saturates at zero. Right increments the stored offset without saturating at the last renderable field; rendering separately clamps that offset to the last valid starting field. Consequently, excess Right presses at the displayed end leave the screen unchanged but accumulate in the stored offset, and the same number of Left presses merely consumes that excess before the displayed fields begin moving left again. Selection updates both the tree highlight and the corresponding statistics row. When a selected primitive's actual tree node falls outside the visible tree window, scroll just enough to place it at the nearest edge. A vertical scrollbar uses `│` for its track and `█` for its thumb; thumb size is `max(floor(visible_items * track_length / total_items), 1)` and its proportional position spans the remaining track.

The Schema footer is exactly:

```text
←/→ : Scroll, ↑/↓ : Schema - [Tab] Next Tab, [Q]uit
```

## Spec 20

For the common `alltypes_plain.parquet`, the Schema Tree is root followed by these eleven optional primitive leaves in order: `id`, `bool_col`, `tinyint_col`, `smallint_col`, `int_col`, `bigint_col`, `float_col`, `double_col`, `date_string_col`, `string_col`, `timestamp_col`. Their physical types respectively are INT32, BOOLEAN, INT32, INT32, INT32, INT64, FLOAT, DOUBLE, BYTE_ARRAY, BYTE_ARRAY, INT96. Their aggregate compressed/uncompressed byte pairs are respectively 73/73, 24/24, 47/47, 47/47, 47/47, 55/55, 47/47, 55/55, 88/88, 49/49, 139/139. This provides the canonical initial schema layout and yields `1.00x` ratios.

Nested schemas must visibly distinguish groups from leaves. For example, nested lists show repeated `list` group nodes and `element` children at increasing indentation, while the nested-struct corpus can expose hundreds of primitive leaves and automatically scroll the tree without losing `Schema Tree`, `Repetition`, or `Physical` labels.

## Spec 21

The Row Groups view reuses the schema tree on the left. The right side always begins with a 3-row bordered progress strip titled ` Row Group: current / total `. Its inner center row is a full `─` line, with the selected group's proportional segment replaced by `█` cells. The complete strip remains in these same three rows when a primitive leaf is selected and a column-detail panel is displayed below it.

When no primitive leaf is selected, show below the progress strip four adjacent 3-row bordered statistic blocks titled `Rows`, `Compressed`, `Uncompressed`, and `Ratio`. The centered main values are the selected row group's row count, human-readable compressed size, human-readable uncompressed size, and ratio to two decimals without an `x`. Each block's centered bottom title is `average / median` across all row groups. Sizes use the Metadata size formatter; counts use comma grouping. The median is the sorted element at index `count / 2` (the upper middle for an even count). Average byte/count values are truncated to integers before formatting.

The remainder's left half contains two vertically stacked Unicode point charts; the right half remains unused. The first is titled `Compressed vs Uncompressed (B)` and plots both byte totals by row-group number. The second is titled `Compression Ratio`, uses labels ending in `x`, and plots uncompressed/compressed. Both have a bottom label `Row Group`. Layout is clipped naturally when narrow; do not replace it with prose.

## Spec 22

Up/Down in Row Groups changes the selected primitive leaf from 0 (overview) through the primitive-column count. Left/Right selects row groups from first through last. Both directions saturate rather than wrap. Returning Up from the first leaf to zero restores the overview. The footer is exactly:

```text
→/← : Iterate Row Groups, ↑/↓ : Schema - [Tab] Next Tab, [Q]uit
```

At row-group index changes, the progress strip, metric blocks, and detail data update. A single-group `alltypes_plain.parquet` overview reports 8 rows, 671 B compressed, 671 B uncompressed, and ratio 1.00. A nested-struct compatibility file reports one row, 216 primitive columns in Metadata, and a row-group ratio that renders as `0.78`.

## Spec 23

When a primitive leaf is selected in Row Groups, retain the progress strip and replace only the overview content below that strip with a column-detail panel. Directly beneath the strip, the panel's top-only border has a centered title ` Column: "path" `. Immediately below are four equal-width, 3-row indicator boxes titled `Statistics`, `Dict Page`, `Bloom Filter`, and `Page Stats`. Center `✓` when that footer feature is present and `✗` otherwise.

Split the remaining area 3:5. The left side starts with a 7-row `Metadata` box containing `File Offset (B)`, `Compressed Size`, `Uncompressed Size`, `Compression Ratio`, and `Compression Type`. The offset uses decimal comma grouping; sizes use the Metadata byte formatter; ratio has exactly two decimals plus `x`. If statistics exist, place a 6-row `Statistics` box below with `Min`, `Max`, `Null Count`, and `Distinct Count`, substituting `N/A` for absent values.

The right side is a `Pages` table with columns `#`, `Page Type`, `Size`, `Rows`, `Encoding`. Page numbers are one-based. Page types are `Data Page`, `Index Page`, `Dictionary Page`, or `Data Page V2`; encodings are title-cased labels such as `Plain`, `Plain Dictionary`, `RLE`, `Delta Binary Packed`, `Delta Length Byte Array`, `Delta Byte Array`, `RLE Dictionary`, and `Byte Stream Split`. Page size is the decoded page-buffer byte length and Rows is the page's value count. Files with many pages show as many rows as fit; dictionary-page and page-stat indicators must reflect actual metadata.

## Spec 24

At an 80-by-24 terminal, opening `/workspace/parquet-testing/data/alltypes_plain.parquet` produces this plain-text cell content initially (visual color/highlight attributes are additional):

```text
╭──────────────────────────────────────────────────────────────────────────────╮
│ Visualize   Metadata   /workspace/parquet-testing/data/alltypes_plain.parquet│
╰──────────────────────────────────────────────────────────────────────────────╯
         id        bool_col  tinyint_col  smallint_col  int_col
──────┬─────────────────────────────────────────────────────────────────────────
1     │  4         true      0            0             0
2     │  5         false     1            1             1
3     │  6         true      0            0             0
4     │  7         false     1            1             1
5     │  2         true      0            0             0
6     │  3         false     1            1             1
7     │  0         true      0            0             0
8     │  1         false     1            1             1
      │
      │
      │
      │
      │
      │
      │
      │
      │
      │
parqeye           ↑/↓ : Row | →/← : Column | u/d : Page - [Tab] Next Tab, [Q]uit
```

This example fixes spacing, clipping, borders, first-visible columns, row numbering, and footer placement. Other files use the same algorithms rather than filename-specific screens. For example, `binary.parquet` has header `foo` and begins with `b"\x00"`, `b"\x01"`, `b"\x02"`; fixed/int32/int64 decimal examples display `1.00`, `2.00`, ...; list data displays bracketed nested values; and null fixtures visibly show `NULL`.

## Spec 25

Malformed inputs must fail promptly and nonzero, without hanging, over-allocating according to an untrusted footer length, displaying a traceback/panic as the primary user message, or entering the interactive event loop. Under a PTY, the visible diagnostic is written in this wrapper form:

```text
Error: Custom { kind: Other, error: "DETAIL" }
```

Use these exact `DETAIL` values for the corresponding structural failures:

- a missing path target: `No such file or directory (os error 2)`;
- a file shorter than 8 bytes: `EOF: Parquet file too small. Size is S but need 8`, where `S` is its byte length;
- wrong or incomplete footer magic, ordinary text/JSON/binary garbage, all-zero/all-one content, or a footer missing its last byte: `Parquet error: Invalid Parquet file. Corrupt footer`;
- a valid footer whose unsigned little-endian metadata length `M` exceeds the available prefix: `EOF: Parquet file too small. Size is S but need M+8`;
- a footer that can be located but whose metadata cannot be decoded: prefix the decoder reason with `Parquet error: `;
- the malformed PARQUET-1481 schema: `Parquet error: unexpected parquet type: -7`;
- a negative/out-of-range dictionary count: `parquet: File out of specification: Number must be zero or positive: out of range integral type conversion attempted`.

Examples required by the length rule include size 112 with metadata length 1000 (`need 1008`), size 62 with length 1000 (`need 1008`), size 112 with length 2147483648 (`need 2147483656`), and size 112 with length 112 (`need 120`). A footer-only file whose invalid leading bytes lead to premature metadata exhaustion reports `Parquet error: Could not parse metadata: end of file`. Zero metadata, `PAR1PAR1`, unsigned length `0xffffffff`, repeated magic inside data, reversed magic, and misaligned corrupt metadata all produce an `Error:` diagnostic without unsafe allocation or a crash.

Directories, devices, unreadable paths, cyclic/broken symlinks, and overly long paths also fail promptly and nonzero with a meaningful nonempty error. `/dev/zero` must not block indefinitely. The malformed Arrow and Parquet assets supplied with the specification must likewise terminate nonzero with nonempty standard error when they cannot be decoded.

## Spec 26

The application is read-only: it does not modify input files or directories. It is independent of the current working directory except when resolving a relative path. It tolerates a minimal environment. An environment variable named `PARQUET_TEST_DATA`, whether unset, invalid, empty, or whitespace, must not affect help or version behavior; those immediate actions always retain their exact output and success status.

All screen rendering and key handling must complete quickly enough for an automation driver to see the first stable frame shortly after launch and subsequent stable frames after individual keys. Boundary presses, hundreds of rapid navigation keys, rapid tab cycling, ignored printable/control/Alt keys, nested schemas, unusual Unicode, very wide values, and malformed files must never cause an index error, integer underflow/overflow, uncontrolled memory allocation, or panic text in a still-running TUI.
