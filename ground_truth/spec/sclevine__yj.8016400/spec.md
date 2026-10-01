# Ordered data-format converter specification

The required artifact is a file named `executable`. It is a command-line program that converts a single document read from standard input among YAML, JSON, TOML, and HCL. All requirements below are normative. Examples show literal output, apart from the final newline rules stated separately.

## Spec 1

`executable` must exist, have execute permission, and operate as a stdin/stdout filter. It must not require a filename, configuration file, network service, environment variable, or working-directory-specific resource. On a successful ordinary conversion it writes only the converted document to stdout, writes nothing to stderr, and exits 0. Except for the JSON-root-null-to-TOML panic specified in Spec 20, on a parsing, argument, or encoding failure it writes no partial result to stdout, writes the diagnostic to stderr, and exits 1.

The converter accepts UTF-8 text and preserves Unicode code points in keys and values, including emoji, CJK, Arabic, accents, and mathematical symbols. It must handle at least 10,000-character strings, mappings with at least 100 entries, arrays and documents with at least 1,000 entries, and nested structures at least 50 levels deep without truncation, panic, or excessive delay.

## Spec 2

Every command-line argument is concatenated in argv order and treated as a string of single-character flags; there are no positional arguments and no GNU long options. Space characters, tab characters, and every `-` character are ignored wherever they occur (other whitespace characters are not ignored). Thus `-yj`, `yj`, `- y j`, separate arguments `-y -j`, and `--yj` all select the same flags. The only recognized characters are `y t j c r n e i k h v`.

All other characters are invalid, including characters in a would-be filename or long option. Report every invalid character, in encounter order and including repetitions, separated by one space. For example, `-lp` gives `invalid flags specified: l p`, `--help` gives `invalid flags specified: l p` (the `h` and `e` are recognized), and the separate arguments `-ar`, `yb\te-`, `kn-k `, `h ~ dh`, `ab` give `invalid flags specified: a b ~ d a b`.

Argument validation happens before stdin is read or parsed. Unknown characters take precedence over `h` or `v`: `-h -p` is an error rather than help. A standalone `--` is merely ignored, so `-- -v` prints the version.

## Spec 3

The format characters mean YAML=`y`, TOML=`t`, JSON=`j`, and HCL=`c`. After removing non-format modifier characters, the last two format characters select input then output. A single format character selects that input and JSON output. With no format characters, use YAML input and JSON output. Examples: no flags, `y`, and `yj` are YAML-to-JSON; `t` and `tj` are TOML-to-JSON; `c` and `cj` are HCL-to-JSON; `jy` is JSON-to-YAML; and `ytj` uses TOML input and JSON output because its last two format characters are `t,j`.

Repeated/same-format pairs request parse and re-encode: `yy`, `tt`, `jj`, and `cc`. `r` is a conversion shortcut equivalent to the pair `jy`; it does not itself denote a fifth data format. Flag ordering otherwise has no effect on modifiers.

The complete normal conversion set is YAML to JSON/YAML/TOML/HCL, TOML to JSON/YAML/TOML/HCL, JSON to JSON/YAML/TOML/HCL, and HCL to JSON/YAML/TOML/HCL.

## Spec 4

The modifier flags are:

- `n`: disable the default conversion between non-finite floats and the strings `Infinity`, `-Infinity`, and `NaN` when YAML or TOML is involved.
- `e`: HTML-safe escaping for JSON output.
- `i`: indented output for JSON or TOML.
- `k`: parse string mapping keys as JSON values when producing YAML.
- `h`: help.
- `v`: version.

After unknown-character checking, validate modifier/output compatibility before processing input. `k` is valid only when output is YAML, otherwise the exact reason is `flag -k only valid for YAML output`. `e` is valid only when output is JSON, otherwise the reason is `flag -e only valid for JSON output`. `i` is valid only when output is JSON or TOML, otherwise the reason is `flag -i only valid for JSON or TOML output`. If more than one restriction applies, validate in the order `k`, `e`, `i` and report the first.

When all characters are recognized and restrictions are satisfied, `h` takes precedence over `v` and conversion; `v` takes precedence over conversion. Other recognized flags may accompany either meta flag. For example, `hr` prints help, `vyj` prints only the version, and `hv` prints help.

## Spec 5

Help is uncolored plain UTF-8. It is written to stdout with exit code 0 and empty stderr. In the following exact template, replace `%s` with argv[0] exactly as the process received it (so it may be `./executable` or an absolute path). Preserve all spacing, blank lines, the misspelling `covert`, and both newline bytes at the end: the `-v` line is followed by an empty line.

```text
Usage: %s [-][ytjcrneikhv]

Convert between YAML, TOML, JSON, and HCL.
Preserves map order.

-x[x]  Convert using stdin. Valid options:
          -yj, -y = YAML to JSON (default)
          -yy     = YAML to YAML
          -yt     = YAML to TOML
          -yc     = YAML to HCL
          -tj, -t = TOML to JSON
          -ty     = TOML to YAML
          -tt     = TOML to TOML
          -tc     = TOML to HCL
          -jj     = JSON to JSON
          -jy, -r = JSON to YAML
          -jt     = JSON to TOML
          -jc     = JSON to HCL
          -cy     = HCL to YAML
          -ct     = HCL to TOML
          -cj, -c = HCL to JSON
          -cc     = HCL to HCL
-n     Do not covert inf, -inf, and NaN to/from strings (YAML or TOML only)
-e     Escape HTML (JSON out only)
-i     Indent output (JSON or TOML out only)
-k     Attempt to parse keys as objects or numeric types (YAML out only)
-h     Show this help message
-v     Show version

```

`NO_COLOR` and similar environment variables do not alter this text.

## Spec 6

The version operation writes exactly `v0.0.0\n` to stdout, nothing to stderr, and exits 0.

For any argument error, write the full help template from Spec 5 to stderr, then immediately write `Error: ` followed by the reason and a newline. The empty line already at the end of the help template is the one blank line separating the `-v` line from `Error:`. Stdout is empty and the exit status is 1. For example, the final line for `-abc` is `Error: invalid flags specified: a b`, and the final line for `-jjk` is `Error: flag -k only valid for YAML output`.

## Spec 7

Read exactly one input document from stdin. Truly empty YAML input, or YAML input containing only spaces and line endings, is successful and produces no bytes on stdout or stderr. This also applies to the default no-argument YAML-to-JSON mode. A tab is not accepted as blank YAML whitespace: in the default mode the four input bytes ` \t\r\n` produce no stdout, exit 1, and exactly `Error parsing YAML: yaml: found character that cannot start any token\n` on stderr. YAML's explicit empty document `---`, however, is a document whose value is null and therefore emits `null\n` as JSON.

Empty or whitespace-only HCL is an empty ordered mapping, not an absent document; HCL-to-JSON therefore emits `{}` followed by a newline, and other targets encode that empty mapping normally. Empty TOML likewise represents an empty mapping. Empty/whitespace-only JSON is invalid JSON and follows the parsing-error rule.

Successful nonempty JSON and YAML output ends in one newline. Successful mapping-root TOML output also ends in one newline, with the scalar-root exception in Spec 20. Successful HCL output does not append a final newline. Input comments and presentation whitespace do not survive re-encoding. Same-format operations parse and canonically re-encode; they are not byte copies.

## Spec 8

Internally preserve an ordered tree containing null, booleans, strings, signed integers, IEEE-754 binary64 numbers, sequences, and ordered mappings. Preserve sequence order and mapping entry order recursively: at the root, inside nested mappings, inside mappings held in sequences, and through multi-step conversions. Never alphabetically, lexically, numerically, or hash-order sort keys. This applies to at least 30 keys and to special-character and Unicode keys.

Mappings may contain duplicate entries where the source parser allows them. JSON and YAML duplicate mapping keys are accepted and retained in encounter order. Thus YAML `key: value1\nkey: value2\n` converted to compact JSON is exactly `{"key":"value1","key":"value2"}\n`. HCL has the distinct duplicate rules in Spec 15; TOML rejects duplicate definitions.

When a target cannot represent a value, follow its target-specific rule rather than changing unrelated entry order: TOML omits null-valued mapping entries, while HCL renders a null attribute with an empty right-hand side.

## Spec 9

JSON input is strict JSON: quoted keys are required; comments, trailing commas, unquoted keys, `NaN`, `Infinity`, invalid escapes, incomplete strings, and trailing garbage are errors. Accept any JSON root value, including an object, array, number, string, boolean, or null. Decode non-surrogate `\uXXXX` escapes to Unicode and standard string escapes to their represented characters. A UTF-16 surrogate escape is rejected even when a valid high/low pair would represent a Unicode code point: the input `{"unicode":"\uD83C\uDF89"}` exits 1 with empty stdout and exactly `Error parsing JSON: yaml: found invalid Unicode character escape code\n` on stderr.

Decode an integer-form JSON token that fits signed 64-bit as an exact integer. Decode fractional or exponent-form tokens with IEEE-754 binary64 semantics, including rounding where necessary, but render a numerically integral value without `.0` in JSON and HCL. Required numeric normalization includes:

```text
1.0 -> JSON 1
1.23e10 -> JSON 12300000000
0.1234567890123456789 -> JSON 0.12345678901234568
1.7976931348623157e308 -> JSON 1.7976931348623157e+308
```

Preserve integers throughout the signed 64-bit range when converting to YAML (including `9223372036854775807` and `-9223372036854775808`), and preserve the exact integer `9007199254740992`. Negative zero may canonically render as zero.

## Spec 10

YAML input supports ordinary block and flow mappings/sequences, any root node, plain/single-quoted/double-quoted strings, comments, empty maps and sequences, null, booleans, integers, binary/octal/hexadecimal integers, decimal and scientific floats, numeric underscores, literal and folded block strings with YAML chomping/folding behavior, and explicit `!!str`, `!!int`, and `!!float` tags.

Use YAML-1.2-like scalar resolution: any capitalization of `true` and `false` is boolean, while `yes/no/on/off` and capitalization variants remain strings. `null`, `Null`, `NULL`, and `~` are null. For example, `0o755` becomes 493, `0xFF` becomes 255, and `1.23e-4` becomes 0.000123. Quoted date/time-looking values remain strings.

Literal blocks preserve line breaks and their final newline unless stripped; folded blocks join ordinary lines with spaces and obey `>-` stripping. Tabs used as indentation and illegal control/binary bytes are errors. A plain top-level `hello` becomes the JSON string `"hello"`, and top-level `42` becomes JSON number `42`.

## Spec 11

YAML anchors and aliases are resolved by deep value expansion in place. Preserve the anchored definition as an ordinary mapping entry and independently expand each alias. Detect direct or transitive self-reference and fail rather than recurse; detect excessive exponential alias expansion and fail with text containing `excessive aliasing`.

Treat `<<` as a merge instruction. A mapping alias is expanded at the exact position of the merge key, preserving the source mapping's order; separate merge keys are processed in encounter order. Entries appearing after the merge remain afterward, including a duplicate that overrides the merged value under consumers' last-value-wins interpretation. A merge encountered after local entries removes only earlier entries whose keys also occur in the merged mapping, retains earlier non-colliding entries in place, and then inserts the merged entries. Consequently:

```yaml
base: &b {zebra: 1, apple: 2, banana: 4}
item:
  banana: 99
  <<: *b
  cherry: 5
```

produces `item` entries in the order `zebra, apple, banana, cherry`, with banana 4; whereas placing `<<: *b` first and `banana: 99` later retains both banana entries, with the latter effective value.

The merge value must resolve to a mapping. Reject a scalar or sequence value (including a sequence of mappings, and a sequence containing any non-map) with `Error parsing YAML: map merge requires map or sequence of maps as the value`.

## Spec 12

YAML special floats `.inf`, `+.inf`, `-.inf`, and `.nan` (case-insensitive spellings where YAML permits) are non-finite binary64 values. The default compatibility transformation is recursive and applies to both mapping keys and values when crossing between a format with native special floats (YAML/TOML) and one without them (JSON/HCL):

- when YAML or TOML is the input and JSON or HCL is the output, positive infinity becomes string `Infinity`, negative infinity becomes `-Infinity`, and every NaN sign becomes `NaN`;
- when JSON or HCL is the input and YAML or TOML is the output, strings exactly equal to `Infinity`, `-Infinity`, and `NaN` become the target's native special floats.

Thus default YAML-to-JSON renders those values as JSON strings, while JSON `{"x":"Infinity"}` to YAML emits `x: .inf` and to TOML emits `x = +inf`. When both input and output natively support special floats (YAML-to-YAML, YAML-to-TOML, TOML-to-YAML, or TOML-to-TOML), preserve native special floats directly; an ordinary non-key string value `"Infinity"` remains a string rather than being mistaken for a native float. Mapping keys have the distinct YAML-output behavior in Spec 19.

With `n`, disable both string transformations. YAML/TOML output uses native `.inf`/`-.inf`/`.nan` or `+inf`/`-inf`/`nan`. Because JSON cannot encode non-finite floats, JSON output substitutes positive infinity with `1.7976931348623157e+308`, negative infinity with its negative, and NaN with `null`. Mapping keys are stringified after this substitution, producing keys `1.7976931348623157e+308`, `-1.7976931348623157e+308`, and `null`.

## Spec 13

TOML input supports comments and flexible whitespace; bare, quoted, dotted, and very long keys; basic and literal strings; multiline basic and literal strings; standard escapes and multiline line continuation; decimal/hex/octal/binary integers; decimal/scientific and special floats; booleans; homogeneous or mixed arrays, nested arrays, inline tables; ordinary tables, empty tables, dotted/nested tables, arrays of tables, and nested arrays of tables.

Reject malformed syntax, unterminated strings/tables, invalid dates, and duplicate key/table definitions. TOML dates/times become strings formatted as follows: offset date-times retain their offset, local date-times gain `Z`, dates become midnight UTC, and local times use date `0000-01-01`. Examples are `1979-05-27T07:32:00` -> `1979-05-27T07:32:00Z`, `1979-05-27` -> `1979-05-27T00:00:00Z`, and `07:32:00` -> `0000-01-01T07:32:00Z`.

TOML special values `inf`, `+inf`, `-inf`, `nan`, `+nan`, and `-nan` follow Spec 12. Preserve integer-versus-float type through TOML-to-YAML/TOML: `1` emits `1`, while `1.0` emits `1.0`.

## Spec 14

HCL input supports the legacy configuration syntax exercised here: line and block comments (`#`, `//`, `/*...*/`); quoted or identifier attribute names; `name = value` assignments; unlabeled and multiply labeled blocks; repeated blocks; strings with escapes and Unicode; heredocs (`<<TAG` and indented `<<-TAG`); booleans; signed decimal/scientific numbers; lists, including heterogeneous/nested lists; and object literals.

HCL has no accepted null literal in this language. Reject it with a diagnostic containing the case-sensitive text `Unknown token:` (including the colon); for example, `x = null\n` produces `Error parsing HCL: At 1:5: Unknown token: 1:5 IDENT null\n`. Reject unterminated blocks/objects, incomplete assignments, and missing `=`/`{`.

Preserve whether an HCL number token is integral or floating-point when targeting YAML: tokens `0` and `1` emit `0` and `1`, while tokens `0.0` and `1.0` emit `0.0` and `1.0`. Numeric input is binary64-normalized for JSON/HCL output (`1.23e10` becomes `12300000000`, and `-4.5e-6` becomes `-0.0000045`). JSON's finite-float spelling uses decimal notation for magnitudes from `1e-6` (inclusive) through `1e21` (exclusive), and scientific notation outside that interval. Thus `[1e-7,1e-6,-4.5e-6,1e20,1e21]` re-encodes as `[1e-7,0.000001,-0.0000045,100000000000000000000,1e+21]\n`.

Heredoc content excludes delimiters and includes its terminal content newline. For indented `<<-TAG` heredocs, the closing delimiter's leading indentation is the dedent baseline: remove that prefix from each content line. Thus content lines indented four spaces with a closing delimiter indented two spaces retain two leading spaces; the delimiter participates in the calculation rather than all of its indentation being ignored.

## Spec 15

Decode every HCL block as an array under its block name, even when it occurs only once. Each block label introduces another ordered mapping level whose value is likewise an array. Repeated equal block/label paths append elements. For example:

```hcl
resource "type" "a" { enabled = true }
resource "type" "b" { enabled = false }
```

becomes this abstract JSON structure:

```json
{"resource":[{"type":[{"a":[{"enabled":true}],"b":[{"enabled":false}]}]}]}
```

Nested blocks use the same rule. HCL object-literal attributes also decode as a one-element array containing their mapping: `tags = { Name = "web" }` becomes `"tags":[{"Name":"web"}]`. Scalar lists stay lists. Duplicate attributes within one body use last-value-wins in the original attribute position; duplicate blocks append.

## Spec 16

JSON output must be canonical and order preserving. Without `i`, put the complete value on one compact line with no insignificant spaces. With `i`, use two spaces per nesting level, one mapping member or sequence item per line, standard comma placement, and closing delimiters aligned with their opener. Append a newline in both modes.

Use JSON string escaping for quotes, backslashes, controls, and embedded newlines/tabs, but emit valid non-ASCII Unicode directly rather than as ASCII `\u` escapes. By default emit `<`, `>`, and `&` literally. With `e`, replace those three characters everywhere inside JSON strings—including keys—with lowercase escapes `\u003c`, `\u003e`, and `\u0026`. Do not HTML-escape apostrophes or the quote characters already handled by ordinary JSON syntax, and do not escape unrelated Unicode.

For example, default compact output for YAML `text: "<tag> &"` is `{"text":"<tag> &"}\n`; with `e` it is `{"text":"\u003ctag\u003e \u0026"}\n`.

## Spec 17

Before JSON encoding, stringify every non-string mapping key using its compact JSON representation after the special-float transformation. Scalar numeric/boolean/null keys therefore become strings such as `"123"`, `"true"`, or `"null"`; mapping and sequence keys become compact JSON text such as `{"key":"value"}` or `[1,2]`. Preserve entry order and duplicates.

JSON nulls, booleans, arrays, empty arrays/objects, escaped strings, and heterogeneous arrays must remain semantically intact. JSON-to-JSON is a parse/re-encode operation and therefore applies binary64 numeric normalization and the selected formatting/escaping options.

## Spec 18

YAML output is canonical block-style YAML with two-space indentation and a final newline. Mapping entries are one per line. Sequence entries use `- ` and, when a sequence is a mapping value, are indented two additional spaces. Nested mapping members are indented two spaces per level. Empty mappings/sequences are `{}` and `[]`; null is the word `null`; booleans are lowercase. Integers have no decimal point, while a value known to be a float and numerically integral keeps `.0` (for example TOML/YAML float 90.0 emits `90.0`). Use conventional scientific notation with a signed, at-least-two-digit exponent where applicable, such as `1.23e+10` and `-4.56e-07`.

Choose plain scalars when unambiguous, otherwise use the following deterministic quote styles to preserve string type and content. Numeric-looking and date-looking strings are double quoted (`"10":`, `"2023-01-15"`). String spellings that legacy YAML resolvers could treat as booleans or null are also double quoted. The relevant spellings are `y`, `Y`, `yes`, `Yes`, `YES`, `n`, `N`, `no`, `No`, `NO`, `on`, `On`, `ON`, `off`, `Off`, `OFF`, `true`, `True`, `TRUE`, `false`, `False`, `FALSE`, `null`, `Null`, `NULL`, and `~`; mixed-case variants not in this list remain plain when otherwise safe. Consequently a string key `y` is exactly `"y":`, including when deeply nested, and reverse-alphabetical keys include both `"y": 2` and `"n": 13`. Empty strings are `""`. A nonempty string consisting only of spaces is single quoted, preserving every space; for example, a three-space value is exactly `'   '`.

For an ordinary printable string that cannot use plain style because it begins with or consists of YAML indicator syntax, use single-quoted style rather than escaped double-quoted style, doubling any apostrophes. This choice applies equally to keys and values. Required examples are `'"key"': '"value"'`, `'{"key":1}': value`, `key: '"value"'`, and `<: '>'`; do not spell their quote characters as backslash escapes inside double-quoted YAML. With `n`, literal strings `Infinity`, `-Infinity`, and `NaN` use plain style, as in `Infinity: Infinity`, rather than being quoted. Strings containing actual newlines may use a literal block. Plain keys may contain spaces, dots, hyphens, underscores, and colons not followed by whitespace. BMP Unicode such as CJK and Arabic remains literal. Supplementary-plane characters are emitted inside a double-quoted scalar using uppercase eight-digit `\UXXXXXXXX`; for example `🎉` is `"\U0001F389"`. Input comments, anchors, aliases, tags, flow style, and original quote choices do not survive.

An example is:

```yaml
name: example
enabled: true
items:
  - id: 1
    value: first
  - id: 2
    value: null
empty: {}
```

## Spec 19

Unless `k` is set, mapping keys sent to YAML are preserved as strings after the target-neutral key stringification in Spec 17, except for the default special-string transformation. Without `n`, key strings exactly equal to `Infinity`, `-Infinity`, and `NaN` become the YAML native-float keys `.inf`, `-.inf`, and `.nan` even when `k` is absent. This applies to TOML string keys as well: `Infinity = inf\n` converted with `-ty` is exactly `.inf: .inf\n`. With `n`, those key strings remain strings. Other keys do not receive JSON key parsing without `k`; for example, a JSON key `"123"` emits as the quoted YAML key `"123"`.

With `k`, attempt to parse each string key independently as a complete JSON value. If parsing succeeds with a number, boolean, string, sequence, or mapping, use that value as the actual YAML key; otherwise retain the original string. Thus keys `"42"`, `"3.14"`, `"true"`, `"[1,2,3]"`, and `"{\"nested\":true}"` become respectively an integer, float, boolean, sequence, and mapping key. Complex keys use explicit YAML key syntax, for example:

```yaml
? - 1
  - 2
  - 3
: array value
? nested: true
: object value
```

Parsing the key `"\"key\""` yields string key `key`. Apply the default special-string-to-float behavior as well, so `"Infinity"` becomes YAML key `.inf` unless `n` is present. `k` changes keys only, never ordinary scalar values except through the independent special-float rule.

A key string that parses as JSON `null` reaches an unsupported YAML-key path and makes the complete write fail; it is not emitted as a `null` key. For example, `-jyk` on `{"null":"nothing"}` exits 1 with empty stdout and exactly `Error writing YAML: reflect: call of reflect.Value.Set on zero Value\n` on stderr. The same failure occurs if a null-parsing key is mixed with otherwise supported scalar or complex keys, and no partial YAML is written.

## Spec 20

Mapping-root TOML output is canonical TOML with a final newline. Emit scalar values and scalar/nested arrays as `key = value`; quote strings with TOML basic-string escaping; use lowercase booleans; preserve integral float `.0`; and use `nan`, `+inf`, and `-inf` for non-finite floats. Use a bare key when TOML permits it, otherwise a double-quoted escaped key. Null has no TOML representation: recursively omit null-valued mapping entries and null elements of sequences without disturbing the relative order of retained entries. For example, JSON array `["string",42,null,true]` becomes TOML array `["string", 42, true]`.

There is a non-mapping-root exception to both the document-shape and final-newline rules. A root scalar or array that the encoder can represent is written as a standalone TOML value with no final newline; for example, the root array above is exactly `["string", 42, true]` with no newline. In the recorded scalar case, YAML input `key = value\nnumber = 42` is one folded plain string scalar; `-yt` exits 0 with empty stderr and writes exactly the 25 bytes `"key = value number = 42"`, including the surrounding double quotes and with no final newline. It does not reject this root for failing to be a mapping.

JSON root null is an exceptional unsupported TOML path rather than a handled write failure. For `-jt` with the input `null`, stdout is empty, the process exits 2, and stderr is a Go panic stack trace beginning exactly:

```text
panic: reflect: call of reflect.Value.Type on zero Value

goroutine 1 [running]:
```

It does not emit an `Error writing TOML:` diagnostic.

Mappings become `[path]` tables and sequences of mappings become repeated `[[path]]` array-of-table sections. Inline mappings occurring as elements in an otherwise inline heterogeneous array use `{key = value}`. Emit a body's scalar/inline members in encounter order before its child table sections; recursively retain order within every group. Use dotted paths for nested tables. A nested example without `i` is:

```toml
[root]
number = 42
[root.child]
items = ["a", "b"]
[root.child.deep]
value = "x"
```

Separate repeated table elements and major table groups with the canonical blank lines shown by this example. Root scalar/inline assignments and the first following child table are distinct major groups: place exactly one empty line after the final root assignment and before that table header. Thus the retained values from `{"first":1,"gone":null,"array":["string",42,null,true],"nested":{"a":null,"b":2}}` begin exactly `first = 1\narray = ["string", 42, true]\n\n[nested]\nb = 2\n`.

```toml
[[products]]
name = "Hammer"
price = 9.99

[[products]]
name = "Nail"
price = 0.05
```

## Spec 21

With `i`, TOML retains the same table structure but indents each table header and its direct assignments by two spaces per table nesting depth (root table depth is zero). For example:

```toml
[root]
  number = 42
  [root.child]
    items = ["a", "b"]
    [root.child.deep]
      value = "x"
```

Without `i`, no leading indentation is used on headers or assignments. The flag does not change values, ordering, omission, table grouping, or path names.

## Spec 22

HCL output uses a canonical legacy-HCL representation and no final newline. Always encode mapping keys as JSON-style double-quoted strings, even if they could be bare. A scalar mapping entry is rendered as `"key" = value`; separate sibling assignments with one empty line. Strings use JSON-like double-quote/backslash/control escaping; boolean mapping/object values are lowercase; finite integral numbers omit `.0`; and scalar sequences are inline `[a, b]`. Boolean elements of a sequence are omitted before the remaining elements are rendered in their original order: for JSON input `{"values":[false,true,false,0,1,"","x"]}`, `jc` writes exactly `"values" = [0, 1, "", "x"]`. A nested mapping is an object expression:

```hcl
"application" = {
  "name" = "demo"

  "enabled" = true
}
```

Indent object bodies by two spaces per level. A null mapping value renders as an empty expression after the equals sign (`"key" = `). A sequence of mappings renders as repeated object assignments with the same key rather than bracket syntax:

```hcl
"servers" = {
  "name" = "one"
}

"servers" = {
  "name" = "two"
}
```

This repeated-key convention is what makes decoded HCL block arrays round-trip. Empty mappings render `{}` and empty sequences render `[]`. HCL-to-HCL is also parse and canonical re-encode, so original block spelling and comments are not preserved.

There is one structural shorthand for an entry whose mapping value consists exclusively of mapping-valued children: encode each child as a quoted, multiply labeled block rather than wrapping the parent in `= {}`. For example this abstract value:

```yaml
features:
  switches: {new_ui: true}
  limits: {users: 100}
```

is encoded as:

```hcl
"features" "switches" {
  "new_ui" = true
}

"features" "limits" {
  "users" = 100
}
```

A mapping that also has a scalar, sequence, or null child uses the ordinary object-expression form. Apply this shorthand recursively for chains of all-mapping children.

## Spec 23

YAML, JSON, TOML, and HCL parse failures must be prefixed respectively with `Error parsing YAML: `, `Error parsing JSON: `, `Error parsing TOML: `, or `Error parsing HCL: `, followed by a useful parser diagnostic and a newline. Do not prepend usage help for data parse failures. Stdout is empty and exit status is 1.

Except for the JSON-root-null-to-TOML panic in Spec 20, if parsing succeeds but the selected target cannot encode the normalized value, use `Error writing FORMAT: diagnostic\n` on stderr, with `FORMAT` equal to `YAML`, `JSON`, `TOML`, or `HCL`; exit 1 and do not emit a partial document.

Diagnostics must identify relevant syntax and locations. The following cases require these exact complete lines:

```text
Error parsing JSON: invalid character 'n' looking for beginning of object key string
Error parsing JSON: invalid character '"' after object key:value pair
Error parsing TOML: toml: line 1 (last key "name"): TOML files cannot contain control characters: '0x00'
Error parsing TOML: toml: line 2 (last key "name"): Key 'name' has already been defined.
Error parsing HCL: At 1:31: expected: IDENT | STRING got: LBRACE
Error parsing HCL: At 4:2: object expected closing RBRACE got: EOF
Error parsing HCL: At 1:25: key 'key "no_equals"' expected start of object ('{') or assignment ('=')
Error parsing YAML: yaml: line 2: mapping values are not allowed in this context
Error parsing YAML: anchor 'loop' value contains itself
Error parsing YAML: map merge requires map or sequence of maps as the value
```

Other tested malformed cases must retain characteristic parser wording: undefined YAML aliases mention `unknown anchor` and its name; tab indentation reports its line and `found character that cannot start any token` (for `a:\n\tb: 1\n`, the complete line is `Error parsing YAML: yaml: line 2: found character that cannot start any token\n`); the distinct malformed mapping `valid: value\nbad: value: again\n` reports `mapping values are not allowed in this context`; illegal YAML bytes mention that control characters are not allowed; JSON missing strings mention `unexpected end of JSON`, trailing commas mention `looking for beginning of object key`, bad escapes mention `escape code`, and unquoted keys mention `object key string`.

For TOML, a basic string that reaches EOF before a closing quote mentions `unexpected EOF`, but a raw newline encountered first reports that strings cannot contain newlines. In particular, `name = "test\n` produces exactly `Error parsing TOML: toml: line 1 (last key "name"): strings cannot contain newlines\n`. Malformed table headers mention `expected '.' or ']'` except for the NUL-containing exact case above, duplicate keys mention `has already been defined`, and invalid TOML dates fail. Unfinished HCL bodies/objects mention `expected closing RBRACE` and `EOF`; missing assignment syntax mentions the expected object or assignment; and a null token uses the `Unknown token:` spelling specified in Spec 14.

## Spec 24

Conversions must preserve the common semantic structure across round trips wherever the target can represent it: JSON↔YAML preserves nulls, empty collections, nested mappings/sequences, booleans, strings, numeric values, sequence order, and key order; TOML round trips preserve all of those except null mapping entries and null sequence elements, which are omitted; HCL round trips preserve its nested block/label array structure using Spec 15 and Spec 22.

Format-specific values use the explicit rules above rather than ad-hoc coercion. In particular, string values that merely look numeric remain strings; YAML float `3.0` and TOML float `3.0` retain float identity when emitted to YAML/TOML; JSON numeric values use binary64 normalization; TOML date/time values become their specified strings; YAML aliases become independent expanded data; and special floats obey `n`. Every conversion and same-format normalization must retain mapping order after these unavoidable target-specific transformations.
