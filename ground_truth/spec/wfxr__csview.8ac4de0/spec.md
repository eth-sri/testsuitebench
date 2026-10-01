# Behavioral specification for `executable`

## Spec 1

`executable` is a command-line CSV viewer. It reads one delimited-text input, parses it as records, and writes a formatted text table to standard output. On a successful data-rendering invocation it exits with status 0, writes no diagnostics to standard error, and terminates its table output with `\n`.

The invocation grammar is:

```text
executable [OPTIONS] [FILE]
```

There may be zero or one `FILE` positional argument. If it is present, read that file as raw bytes. Otherwise read standard input through EOF. File input and standard-input input have identical parsing and rendering semantics. An empty input is valid. Options may occur before or after `FILE`. `--` ends option parsing, so a following dash-prefixed token is the file name. More than one positional argument is a command-line error.

## Spec 2

The executable accepts these options and defaults:

```text
-H, --no-headers              input has no header record (default: false)
-n, --number                  prepend line numbers (default: false)
    --seq                     hidden alias of --number
-t, --tsv                     use a tab delimiter
-d, --delimiter CHAR          use CHAR as the delimiter (default: comma)
-s, --style STYLE             table style (default: sharp)
-p, --padding N               spaces on each side of every cell (default: 1)
-i, --indent N                spaces before each rendered table line (default: 0)
    --sniff N                 data records used to discover widths (default: 1000; 0 means unlimited)
    --header-align ALIGN       header alignment (default: center)
    --body-align ALIGN         body alignment (default: left)
-P, --disable-pager           disable use of a pager
-h, --help                    print help
-V, --version                 print version
```

`STYLE` accepts `none`, `ascii`, `ascii2`, `sharp`, `rounded`, `reinforced`, `markdown`, and `grid`. Style names are ASCII-case-insensitive, so, for example, `MARKDOWN`, `MarkDown`, and `markdown` are equivalent. `ALIGN` accepts `left`, `center`, or `right`. `-t` and `-d`/`--delimiter` are mutually exclusive. No delimiter is inferred from a file extension: a tab-containing `.tsv` file is still comma-delimited unless `-t` or `-d` with a literal tab is supplied.

## Spec 3

Help and version are order-sensitive early-exit actions. The parser processes arguments from left to right until it encounters `--help`/`-h`, `--version`/`-V`, or an error. An earlier invalid argument wins over a later help or version option: `executable --unknown --help` exits 2 with the unexpected-argument error described in Spec 20. Conversely, once help or version is encountered, later arguments are not processed. Thus `executable --help --unknown` prints help, `executable --version --help` prints the version, and `executable --help --version` prints help. Valid options or a positional file before `--help` do not prevent the help early exit.

On a help early exit, the executable exits 0, writes nothing to standard error, and writes exactly the following UTF-8 text to standard output, including the final newline and wrapping shown:

```text
A high performance csv viewer with cjk/emoji support.

Usage: executable [OPTIONS] [FILE]

Arguments:
  [FILE]
          File to view

Options:
  -H, --no-headers
          Specify that the input has no header row
  -n, --number
          Prepend a column of line numbers to the table
  -t, --tsv
          Use '\t' as delimiter for tsv
  -d, --delimiter <DELIMITER>
          Specify the field delimiter [default: ,]
  -s, --style <STYLE>
          Specify the border style [default: sharp] [possible values: none, ascii, ascii2, sharp,
          rounded, reinforced, markdown, grid]
  -p, --padding <PADDING>
          Specify padding for table cell [default: 1]
  -i, --indent <INDENT>
          Specify global indent for table [default: 0]
      --sniff <LIMIT>
          Limit column widths sniffing to the specified number of rows. Specify "0" to cancel limit
          [default: 1000]
      --header-align <HEADER_ALIGN>
          Specify the alignment of the table header [default: center] [possible values: left,
          center, right]
      --body-align <BODY_ALIGN>
          Specify the alignment of the table body [default: left] [possible values: left, center,
          right]
  -P, --disable-pager
          Disable pager
  -h, --help
          Print help
  -V, --version
          Print version
```

The help contains no terminal color/ANSI escape sequences. `-h` has the same successful help behavior. `--version` and `-V` exit 0, use no standard error, and print exactly:

```text
csview 1.3.4
```

## Spec 4

The default delimiter is comma. `--tsv`/`-t` changes it to one literal tab byte. `--delimiter`/`-d` accepts exactly one Unicode scalar value syntactically and supports all of these forms: `-d X`, `-dX`, `-d=X`, `--delimiter X`, and `--delimiter=X`. The scalar's code point is then truncated to its low eight bits, and that single byte is used as the CSV delimiter. Consequently, ordinary single-byte ASCII delimiters behave directly, but a non-ASCII scalar is not matched as its UTF-8 byte sequence. For example, `界` (U+754C) selects byte `0x4c`, so it does not split `a界b` but does split `aLb`. Required behavior includes comma, tab, pipe, semicolon, colon, equals sign, and space delimiters. The selected delimiter byte is authoritative: if it does not occur in the input, each record is parsed as one field rather than triggering delimiter auto-detection or an error.

Parsing follows conventional CSV rules using `"` as the quote character. Delimiters and record terminators inside a quoted field are data. Two consecutive quotes inside a quoted field decode to one literal quote. Preserve empty fields, including fields made by adjacent delimiters and leading or trailing delimiters. Preserve all field text verbatim after CSV unquoting, including leading/trailing spaces, tabs, punctuation, numeric spelling such as leading or trailing zeroes, non-ASCII text, and embedded newlines. Accept LF, CRLF, and mixed LF/CRLF record endings without retaining a terminating `\r`. Ignore a UTF-8 BOM at the very beginning. A trailing record terminator does not create an extra record, and blank physical lines outside quoted fields do not create table rows.

## Spec 5

Input must be valid UTF-8 after an optional initial UTF-8 BOM, and every parsed record must have the same number of fields as the first parsed record. Do not silently replace invalid bytes, pad short records, or discard extra fields. Parse and validate the input before writing table output, so a parse failure leaves standard output empty.

For a record-length mismatch, exit 1 and write a newline-terminated diagnostic of this form to standard error:

```text
csview: CSV error: record R (line: L, byte: B): found record with X fields, but the previous record has Y fields
```

`R` is the zero-based record index of the first bad record; `L` is its one-based physical starting line; `B` is its zero-based starting byte offset. For example, the input `a,b,c\n1,2,3\n4,5\n` produces exactly:

```text
csview: CSV error: record 2 (line: 3, byte: 12): found record with 2 fields, but the previous record has 3 fields
```

For invalid UTF-8, exit 1 and report the record, line, zero-based field index, record-start byte offset, and invalid byte position. For the bytes `name,value\ntest,data\ninvalid,\xff\xfe\n`, the exact diagnostic is:

```text
csview: CSV parse error: record 2 (line 3, field: 1, byte: 21): invalid utf-8: invalid UTF-8 in field 1 near byte index 0
```

## Spec 6

By default, the first parsed record is the table header and all later records are body rows. Header cells use header alignment; body cells use body alignment. Emit a header/body dividing rule only when there is both a header record and at least one body record.

With `-H`/`--no-headers`, every parsed record is a body row, including the first, and no header/body rule is emitted. Do not synthesize column names. A one-record no-header input is one ordinary body row between the applicable outer borders.

## Spec 7

With `-n`, `--number`, or `--seq`, prepend a new first column. In header mode its header text is `#`, and body rows contain decimal sequence numbers `1`, `2`, ... in input order. The header itself is not numbered. In no-header mode there is no `#` row; all input records receive numbers starting at 1. The number column participates in width calculation, padding, alignment, indentation, truncation, and all table styles exactly like other columns. Header alignment applies to `#`; body alignment applies to the decimal numbers.

## Spec 8

Column sizing uses terminal display width, not UTF-8 byte length. Calculate a string's width from its CJK display widths: ordinary Latin characters and accented Latin letters count as 1, CJK/full-width characters and wide emoji count as 2, and combining marks/variation selectors/zero-width joiners count as 0. If the width routine has no defined width for a scalar (notably an embedded tab, carriage return, or newline), count that scalar as 1. There is one sequence-level exception: an adjacent `\r\n` pair inside a field has width 1 in total rather than counting both scalars separately. A lone `\r` or lone `\n` still has width 1. Thus `你好` is width 4, `🙂` is width 2, the literal three-scalar string `a\tb` is width 3, and `x\r\ny` is width 3.

Preserve Unicode scalars exactly in output. Width-based truncation must never split a UTF-8 encoding or partially include a scalar.

## Spec 9

The `--sniff N` option affects column-width discovery, not row count. Always output every parsed row. In header mode, always consider the header when calculating each content width, then consider at most the first `N` body rows. In no-header mode, consider at most the first `N` rows. `N=0` removes this limit and considers all rows. Each column's content width `W` is the maximum display width seen in that sniff set; an empty column can have `W=0`.

When a later cell is wider than its discovered `W`, truncate it to the longest leading sequence whose display width is at most `W`. Do not add an ellipsis, wrap, or widen the table. For example, if sniffing establishes width 2, `1000` renders as `10`; at width 5, `This is long` renders as `This ` (the first five display columns). Rows beyond the sniff limit remain present.

## Spec 10

For a column with discovered content width `W` and padding `P`, its rendered segment width is `W + 2P`. First truncate the content as in Spec 9, then add alignment spaces to reach `W`, then add exactly `P` literal spaces on both the left and right of that aligned content.

Alignment within the `W`-wide content area is:

- `left`: zero extra spaces before, all extra spaces after.
- `right`: all extra spaces before, zero after.
- `center`: `floor(extra/2)` before and `ceil(extra/2)` after, so an unmatched space goes on the right.

Default header alignment is center and default body alignment is left. Alignment is textual; numeric-looking fields are not treated specially. `--padding 0` removes only cell padding, not alignment spaces or style-owned edge characters.

## Spec 11

Prefix every renderer-created output line—including border and separator lines—with exactly `I` spaces, where `I` is `--indent` (default 0). Do not otherwise indent or trim rows. Preserve trailing padding and style-owned trailing spaces. Every rendered row/rule ends with `\n`, including the last one.

An embedded newline inside a field remains a literal newline inside that already-constructed content row; it is not converted to `\\n`, wrapped into a new boxed table row, or given newly synthesized side borders. Its scalar nevertheless contributes width 1 as specified above. For example, a field containing `123 Main St\nApt 4B` causes those substrings to appear on consecutive physical output lines within the same logical row string.

## Spec 12

The default `sharp` style uses the following characters:

```text
top:       ┌  ┬  ┐
row:       │ between and outside cell segments
header:    ├  ┼  ┤
bottom:    └  ┴  ┘
horizontal fill: ─
```

For column segment widths `S1...Sk`, a rule consists of its left character, `S1` fills, its junction, `S2` fills, ..., and its right character. A content row consists of `│`, each padded/aligned segment separated by `│`, and a closing `│`. With default settings, input `Name,Age\nAlice,30\nBob,25\n` renders exactly:

```text
┌───────┬─────┐
│ Name  │ Age │
├───────┼─────┤
│ Alice │ 30  │
│ Bob   │ 25  │
└───────┴─────┘
```

## Spec 13

The `rounded` and `reinforced` styles have the same row separators, horizontal fill, internal top/bottom junctions, header rule, and row behavior as `sharp`, but replace only the four outer corners:

```text
rounded:    ╭ top-left, ╮ top-right, ╰ bottom-left, ╯ bottom-right
reinforced: ┏ top-left, ┓ top-right, ┗ bottom-left, ┛ bottom-right
```

In particular, reinforced style still uses light `─`, `│`, `┬`, `┴`, `├`, `┼`, and `┤`; only its four corners are heavy.

## Spec 14

The `ascii` style has full borders and the same rule-placement behavior as `sharp`, but every corner and junction is `+`, horizontal fill is `-`, and vertical edge/separator is `|`. For `a,b\n1,2\n` at default padding it is exactly:

```text
+---+---+
| a | b |
+---+---+
| 1 | 2 |
+---+---+
```

It must contain no Unicode box-drawing characters.

## Spec 15

The `ascii2` style has no top or bottom rules. Each content row is one literal style-owned leading space, followed by the normal cell segments joined directly with `|`, followed by one literal style-owned trailing space. If header and body are both present, its sole rule is between them: one leading space, `-` repeated for each segment width with `+` at column junctions, then one trailing space. There are no rules between body rows.

For `Name,Age\nAlice,30\nBob,25\n` with default padding:

```text
  Name  | Age  
 -------+----- 
  Alice | 30   
  Bob   | 25   
```

The leading/trailing style spaces remain even with padding 0.

## Spec 16

The `markdown` style has no top or bottom rule. Each content row is `|`, followed by normal cell segments joined with `|`, followed by `|`. When header and body are both present, emit one divider immediately after the header: `|`, then `-` repeated to exactly each full segment width, with `|` at junctions and the right edge. Alignment options alter spaces in content rows but do not add Markdown colon markers. There are no rules between body rows.

For `Name,Age\nAlice,30\nBob,25\n` with default padding:

```text
| Name  | Age |
|-------|-----|
| Alice | 30  |
| Bob   | 25  |
```

## Spec 17

The `grid` style uses exactly the same characters as `sharp`, but places a `├...┼...┤` rule between every pair of adjacent logical content rows, not only between header and body. Thus a header plus two body records has a top rule, header, rule, first body, rule, second body, and bottom rule. In no-header mode it likewise separates every pair of body rows. It does not place an extra middle rule after the final row.

## Spec 18

The `none` style emits no border, junction, separator, or horizontal-rule characters. A logical row is simply the normal padded/aligned cell segments concatenated with no additional separator. Padding and alignment therefore provide the whitespace between columns. Preserve the leading padding before the first column and trailing padding after the last. For `Name,Age\nAlice,30\nBob,25\n` with default padding:

```text
 Name   Age 
 Alice  30  
 Bob    25  
```

No header divider is emitted in this style.

## Spec 19

Degenerate tables remain renderable. With default header behavior, completely empty input is represented as one empty logical header row with zero columns. In `sharp` (and identically in `grid`) the exact result is:

```text
┌┐
││
└┘
```

In `none` style, the same empty input produces exactly one newline. A header-only nonempty input produces top rule, header row, and bottom rule, with no middle rule. Empty fields retain their columns; with three zero-width columns and padding 1, each rule segment is two characters wide and each content cell contains two spaces. Single-cell, single-column, very wide, many-column, and at least 1000-row tables follow the same rules without artificial row or field-length limits.

## Spec 20

Command-line syntax/validation failures exit 2, write nothing to standard output, and write a newline-terminated parser diagnostic to standard error. Diagnostic layout depends on the error class. The unknown-option and second-positional examples below include the general `Usage: executable [OPTIONS] [FILE]` block. A separate negative token following `--padding`, `--indent`, or `--sniff` is also an unexpected-argument error and includes that general usage block, as detailed below. For a `--tsv`/`--delimiter` conflict, the specific usage synopsis names the conflicting option that appeared first: `Usage: executable --tsv [FILE]` when `--tsv` appeared first, and `Usage: executable --delimiter <DELIMITER> [FILE]` when `--delimiter` appeared first. Missing option values and invalid option values—including delimiter, nonnegative-integer tokens that do not begin with `-`, style, and alignment values—include no `Usage:` line at all; after the error details they end with one blank line followed by exactly `For more information, try '--help'.\n`.

Required diagnostics include these phrases:

- Unknown `--unknown`: `unexpected argument '--unknown'`.
- Unknown `--nonexistent-flag`: also include `tip: to pass '--nonexistent-flag' as a value, use '-- --nonexistent-flag'`.
- A second positional such as `executable a b`: `unexpected argument 'b' found`.
- Missing `-d`/`--delimiter` value: `a value is required for '--delimiter <DELIMITER>'`.
- Empty delimiter: `invalid value '' for '--delimiter <DELIMITER>'` and `cannot parse char from empty string`.
- Multi-character delimiter `::`: `invalid value '::'` and `too many characters in string`.
- An invalid padding/indent/sniff value that does not begin with `-`: identify the supplied value and relevant metavariable (`--padding <PADDING>`, `--indent <INDENT>`, or `--sniff <LIMIT>`) and include `invalid digit found in string`.
- Invalid style: `invalid value 'bad' for '--style <STYLE>'` and a `possible values:` list containing every accepted style.
- Combining `--tsv` with `--delimiter`: identify both options and state they `cannot be used with` one another.

In the following invocations, each separate negative token is not consumed as the preceding option's value; it is processed as another argument. For `executable --padding -1`, standard error is exactly:

```text
error: unexpected argument '-1' found

  tip: to pass '-1' as a value, use '-- -1'

Usage: executable [OPTIONS] [FILE]

For more information, try '--help'.
```

For `executable --indent -2`, standard error is exactly:

```text
error: unexpected argument '-2' found

  tip: to pass '-2' as a value, use '-- -2'

Usage: executable [OPTIONS] [FILE]

For more information, try '--help'.
```

For `executable --sniff -3`, standard error is exactly:

```text
error: unexpected argument '-3' found

  tip: to pass '-3' as a value, use '-- -3'

Usage: executable [OPTIONS] [FILE]

For more information, try '--help'.
```

For the delimiter-first conflict spelling `executable '-d;' -t`, standard error is exactly:

```text
error: the argument '--delimiter <DELIMITER>' cannot be used with '--tsv'

Usage: executable --delimiter <DELIMITER> [FILE]

For more information, try '--help'.
```

Padding, indent, and sniff values are nonnegative decimal integers. They must support, at minimum, padding values through 10, indent values through 20, and sniff values through 1000 without clamping.

## Spec 21

An input-file open/read failure exits 1, leaves standard output empty, and writes `csview: ` followed by the operating-system error and a final newline. A missing file must produce exactly:

```text
csview: No such file or directory (os error 2)
```

`-P`/`--disable-pager` must be accepted with any rendering combination and cause the rendered bytes to be written directly to standard output. When standard output is captured or otherwise non-interactive, rendering must also be written directly, without invoking a pager, adding colors, changing bytes, or suppressing output. All options—delimiter choice, header handling, numbering, style, padding, indent, sniffing, and the two alignments—compose according to the preceding sections.
