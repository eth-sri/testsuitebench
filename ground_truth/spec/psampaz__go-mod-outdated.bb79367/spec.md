# Clarified specification for `executable`

The required artifact is a runnable file named exactly `executable`. It is a command-line filter for the JSON stream emitted by Go module-listing tools. All behavior needed to implement it is defined below.

## Spec 1

`executable` reads bytes from standard input, interprets them as a whitespace-separated stream of JSON module objects, and writes a summary table to standard output. It must not read an input filename or invoke a Go command itself. A single object may span lines, multiple objects may be adjacent with any JSON whitespace between them, and the last object need not have a trailing newline. Unix newlines, Windows CRLF, blank lines, and other JSON whitespace are accepted.

The output preserves the input-object order after filtering. Nothing is sorted or deduplicated. When there are no output rows, standard output is exactly empty: do not print headers, borders, whitespace, or a newline.

## Spec 2

The supported options are boolean presence flags `-update`/`--update`, `-direct`/`--direct`, and `-ci`/`--ci`, plus the string option `-style`/`--style`. The style value may be supplied as the following argument, as in `-style markdown` or `--style markdown`, or with `=`, as in `-style=markdown` or `--style=markdown`.

Only the exact, case-sensitive style value `markdown` selects Markdown output. An omitted style, `default`, an empty style, and every other style string select the default ASCII format without producing an error. Options can be combined in any order. A `--` argument ends option parsing; later arguments, including ones resembling options such as `--help`, are ignored and must not affect processing.

## Spec 3

Invoking the program with `--help` prints the following help text to standard error, prints nothing to standard output, and exits successfully. `<argv0>` means the exact path/string used to invoke the executable. The indentation before each description is four spaces followed by one tab, as produced in the block below. There is a newline after the final line and no additional text.

```text
Usage of <argv0>:
  -ci
    	Non-zero exit code when at least one outdated dependency was found
  -direct
    	List only direct modules
  -style string
    	Output style, pass 'markdown' for a Markdown table (default "default")
  -update
    	List only modules with updates
```

For example, invocation as `/workspace/executable --help` starts with `Usage of /workspace/executable:`. If other recognized options precede `--help`, help still has the behavior above and input is not processed. Normal successful, non-help operation emits nothing to standard error.

## Spec 4

Command-line option errors use Go-command-style diagnostics on standard error, print nothing to standard output, and exit with status 2. The first line describes the error, the complete usage text from Spec 3 immediately follows, and all lines end in newlines.

- An unknown option is reported as `flag provided but not defined: -NAME`; two leading hyphens are normalized to one in this diagnostic. Thus `--nonexistent` names `-nonexistent`.
- `-style` or `--style` without a value is reported as `flag needs an argument: -style`.
- An invalid explicit boolean value is reported with text containing `invalid boolean value "VALUE" for -FLAG`, followed by the usage. This applies to `ci`, `direct`, and `update`.

Options are parsed from left to right, so an unknown option before `--help` is an error rather than a help request.

## Spec 5

Each top-level JSON value must decode as an object with this schema. Omitted fields have their listed zero value.

| Field | Accepted JSON type | Default and purpose |
|---|---|---|
| `Path` | string | `""`; displayed module identity |
| `Version` | string | `""`; current version candidate |
| `Versions` | array of strings or null | ignored after validation |
| `Replace` | module object or null | replacement metadata |
| `Time` | timestamp string in the RFC-3339-like syntax and with the decoder acceptance rules in Spec 11, or null | current-version time |
| `Update` | module object or null | available-update metadata |
| `Main` | boolean | `false`; identifies the project itself |
| `Indirect` | boolean | `false`; identifies an indirect dependency |
| `Dir`, `GoMod`, `GoVersion` | string | ignored after validation |
| `Error` | object or null | accepted and ignored |

The nested objects in `Replace` and `Update` use the same relevant module fields. Unknown fields at any level are ignored. Optional valid fields such as `Versions`, `Dir`, `GoMod`, `GoVersion`, and `Error` never create extra columns and never cause an otherwise valid module to be omitted. An empty object `{}` is a valid module and produces a row of empty string fields, `DIRECT` equal to `true`, and `VALID TIMESTAMPS` equal to `true`.

## Spec 6

JSON parsing is strict. A top-level array is not a substitute for the object stream; wrong known-field types are not coerced; raw control characters in strings, trailing commas, malformed timestamp syntax, invalid timestamp calendar or clock components, and truncated objects are errors. Numeric timezone-offset components have the exceptional acceptance rule in Spec 11. Stop at the first decoding error and do not process any later JSON values. Do not crash for these input errors and do not print a table. Exit status remains 0.

Report one newline-terminated error line on standard error using the local current time and this format:

```text
YYYY/MM/DD HH:MM:SS <decoder error>
```

The decoder wording must be compatible with Go's `encoding/json` and time decoder. In particular, the tested inputs require these error texts or substrings:

- truncated object: `unexpected EOF`
- plain `not json at all`: `invalid character 'o' in literal null (expecting 'u')`
- a bare identifier beginning with `i` where a JSON value is required: `invalid character 'i' looking for beginning of value`
- a trailing comma before `}`: `invalid character '}' looking for beginning of object key string`
- raw newline within a JSON string: `invalid character '\n' in string literal`
- array where a module is expected: `json: cannot unmarshal array into Go value of type mod.Module`
- object supplied for `Path`: `json: cannot unmarshal object into Go struct field Module.Path of type string`
- string supplied for `Main`: `json: cannot unmarshal string into Go struct field Module.Main of type bool`
- number supplied for `Version`: `json: cannot unmarshal number into Go struct field Module.Version of type string`
- invalid `Time` value `not-a-date`: the error contains both `parsing time "not-a-date"` and `cannot parse "not-a-date"`.

For the truncated-object input `{"Path":"x"`, the decoder-error portion of the line is exactly `unexpected EOF`: the timestamp prefix is followed by `unexpected EOF\n` with no text before the newline. This exactness overrides the general "texts or substrings" phrasing above for that case.

Empty or whitespace-only input is not an error: it exits 0 with both output streams empty.

## Spec 7

Before user-selected filters, discard every module whose top-level `Main` value is `true`. This applies regardless of its path, version, update, replacement, or other fields. Do not display the main module or use it when determining CI status.

All other decoded objects are eligible, including objects with an empty/missing path or version and objects containing an `Error` field. A missing `Indirect` is the boolean zero value `false`, so such a module is direct.

## Spec 8

Apply filtering to top-level modules as follows:

- Without `-direct`, retain both direct and indirect dependencies. With it, retain exactly modules whose top-level `Indirect` is `false`.
- Without `-update`, retain modules whether or not an update exists. With it, retain exactly modules whose top-level `Update` field is a non-null object.
- With both flags, both predicates must hold (logical AND).

The update filter deliberately examines the top-level `Update`, not the replacement's `Update`. Therefore, a module having `Replace.Update` but no top-level `Update` is omitted by `-update`, even though the same module, when shown without that filter, displays the replacement update. Conversely, replacement projection described below does not change the top-level `Indirect` used by `-direct`.

## Spec 9

For display/version calculations, derive an effective module for each retained top-level module:

- If `Replace` is absent or null, the effective module is the top-level module.
- If `Replace` is a non-null object, the effective module is that replacement object. Use its `Version`, `Time`, and `Update` exclusively. Do not fall back to top-level values when one of those replacement fields is empty or absent.

The displayed module path is always the original top-level `Path`, never `Replace.Path`. Thus a replacement may point to a different fork or local directory while the row retains the requested module's identity. If both top-level and replacement updates exist, the replacement update wins. If only the top-level update exists but a replacement has no update, the displayed new version is blank. A local replacement with an empty replacement version displays a blank current version.

## Spec 10

Every retained module produces five string cells in exactly this order:

1. `MODULE`: top-level `Path`.
2. `VERSION`: effective module's `Version`.
3. `NEW VERSION`: effective module's `Update.Version` if effective `Update` is non-null, otherwise the empty string.
4. `DIRECT`: lowercase `true` if top-level `Indirect` is false, otherwise lowercase `false`.
5. `VALID TIMESTAMPS`: lowercase `true` or `false` according to Spec 11.

Versions are opaque strings: do not parse or normalize semantic versions, pseudo-versions, pre-release suffixes, build metadata, `+incompatible`, or unusual lengths. The renderer preserves cell strings as supplied, including leading and trailing whitespace, interior whitespace, UTF-8 text, and special characters. Such leading and trailing whitespace is content in addition to the renderer's one padding space on each side of every cell.

## Spec 11

Accepted timestamp strings have the form `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS±HH:MM`; an optional decimal fraction may follow the seconds (for example `.123Z`). Calendar-date and clock-time components must be valid. In a numeric timezone offset, each `HH` and `MM` component must contain exactly two decimal digits, but its numerical range is not validated: values from `00` through `99` are accepted in either component. Consequently, offsets such as `+99:00` and `+99:99` are accepted rather than producing a decoding error. Compare absolute instants after applying the parsed offset, not the textual timestamps or local clock fields. Use the effective module and effective update selected in Spec 9.

When both relevant times are present, `VALID TIMESTAMPS` is `false` exactly when the effective current `Time` is strictly later than the effective `Update.Time`; it is `true` when current time is earlier or the instants are equal. It is also `true` when there is no effective update, when current `Time` is missing, and when both times are missing. Dates at the Unix epoch and far-future dates such as year 2099 are valid. Replacement timestamp comparisons must use `Replace.Time` and `Replace.Update.Time`, not the top-level times.

## Spec 12

The default output is an ASCII table. The headers are exactly `MODULE`, `VERSION`, `NEW VERSION`, `DIRECT`, and `VALID TIMESTAMPS`. For each column, let its content width be the maximum display width of that header and all cells exactly as supplied, including any leading or trailing whitespace. Do not wrap or truncate any value. Unicode display width is used rather than UTF-8 byte count: ordinary narrow characters occupy one column, combining characters zero, and East Asian wide/full-width characters and wide emoji two.

For a width `w`, a border segment contains `w+2` hyphens. The top, header-divider, and bottom lines join these segments with `+` and have leading/trailing `+`. Header cells are centered within width `w` (when an odd padding cell remains, put it on the right); data cells are left-aligned. Every cell additionally has one literal space on each side, and vertical boundaries are `|`. There are no divider lines between data rows. Every emitted line, including the bottom border, ends in `\n`.

For example, one direct module with one valid update renders exactly:

```text
+---------------------+---------+-------------+--------+------------------+
|       MODULE        | VERSION | NEW VERSION | DIRECT | VALID TIMESTAMPS |
+---------------------+---------+-------------+--------+------------------+
| github.com/test/pkg | v1.0.0  | v1.1.0      | true   | true             |
+---------------------+---------+-------------+--------+------------------+
```

## Spec 13

Markdown style uses the same five columns, widths, centering, left alignment, exact preservation of cell strings, and input row order as the default style. It has no `+` borders and no top or bottom border. Its first line is the padded header row with leading/trailing `|`. Its second line has one `w+2`-hyphen segment per column joined and bounded by `|`, with no spaces inside those separator segments. Data rows follow, also bounded by `|`. Every line ends in `\n`.

The example from Spec 12 becomes exactly:

```text
|       MODULE        | VERSION | NEW VERSION | DIRECT | VALID TIMESTAMPS |
|---------------------|---------|-------------|--------|------------------|
| github.com/test/pkg | v1.0.0  | v1.1.0      | true   | true             |
```

Filtering happens before widths are calculated, so omitted rows do not influence table width.

## Spec 14

The stream and renderer must handle at least 1,000 objects, module paths longer than 500 characters, and version strings longer than 100 characters without fixed-buffer truncation, wrapping, repeated headers, or data loss. Print the header only once per invocation. Preserve Unicode module paths and versions, including Chinese characters, Greek letters, emoji, and punctuation such as `@` and `:`. Table padding must remain aligned according to the display-width rule in Spec 12.

Fields that are irrelevant to the five output cells must have no visible effect. In particular, a populated module `Error` object does not itself write an error message, and a `Versions` array is not used to infer an update; only the relevant non-null `Update` object controls update presence.

## Spec 15

After successful decoding, filtering, and table emission, determine the process status. Normally it is 0. With `-ci`, it is 1 if and only if at least one retained/displayed module has an effective non-null update according to Spec 9; otherwise it is 0. The table is still fully written before status 1 is returned, and CI status 1 does not itself produce any standard-error text.

CI status is based on the post-filter set: an outdated indirect dependency removed by `-direct`, a main module, or any input eliminated by the active filters cannot make CI fail. An empty result exits 0. Without `-ci`, finding updates never changes the successful status from 0.
