# `executable`: terminal JSON viewer specification

The required artifact is one directly runnable program named exactly `executable`. It is a single-purpose, interactive JSON viewer whose command-line identity is `json-tui`. All text is UTF-8. Unless a requirement below explicitly describes terminal-control bytes, quoted output is literal and case-sensitive.

## Spec 1

`executable` shall be a regular executable file and shall implement this invocation grammar:

```text
executable [OPTIONS] [file]
```

There are no subcommands. A non-option token such as `add`, `list`, or `show` is a file name. At most one positional file is allowed. With a valid JSON input, the process starts an interactive terminal UI and remains alive until the user quits; it must not automatically exit merely because stdin or stdout is redirected. A normal interactive quit returns success. All command-line, file-open, and JSON-parse failures return status 1.

## Spec 2

The supported options, and only these options, are:

- `-h` and `--help` for help;
- `-v` and `--version` for the version;
- `-k`, `--key`, and `--keybinding` for the key table;
- `-f` and `--fullscreen` for alternate-buffer fullscreen mode.

Options are case-sensitive and may occur before or after the positional file. Exact long names are required; abbreviations such as `--ver`, misspellings, unknown options, triple-dash options, and value forms such as `--key=true`, `--fullscreen=true`, or `-f=true` are invalid. Short boolean options may be clustered: for example, `-vk`, `-kv`, `-vf`, `-fv`, and `-vkf` are valid. Every character in a short cluster must name a supported short option. Options may be repeated.

A token consisting of one hyphen (`-`) is a literal file name, not stdin. A token consisting of two hyphens (`--`) ends option parsing and is not itself positional; every later token, including `-v`, `--help`, or another `--`, is positional. If the terminator is last, there is no file and stdin is used.

## Spec 3

Argument syntax is validated before any informational action is selected. Thus an unknown option causes `Invalid arguments` even if `--help` is also present, and two positional tokens are invalid. Once the complete argument list is valid, actions have fixed precedence independent of argument order:

```text
help > version > keybinding > JSON display
```

Consequently, help wins over version and keybinding; version wins over keybinding and fullscreen; keybinding wins over JSON display; and fullscreen is only a modifier of JSON display. An informational option ignores the contents or existence of the single allowed file operand. Examples include `file.json --help` displaying help, `-k -v` displaying the version, and `--keybinding missing.json` displaying the key table.

## Spec 4

Both help spellings shall return 0, write nothing to stderr, and write exactly the following bytes to stdout, including the two leading spaces on the first line, blank lines, indentation, spelling, URL, and final line feed:

```text
  json-tui {OPTIONS} [file]

    A JSON terminal UI

  OPTIONS:

      file                              A JSON file. Omit to read from stdin.
      -h, --help                        Display this help menu.
      -v, --version                     Print version.
      -k, --key, --keybinding           Display key binding.
      -f, --fullscreen                  Display the JSON in fullscreen, in an
                                        alternate buffer
      "--" can be used to terminate flag options and force all following
      arguments to be treated as positional options

    If no file is given, json-tui reads JSON from the standard input
    Please report bugs to:https://github.com/ArthurSonzogni/json-tui/issues
```

The output is deterministic and identical for `-h` and `--help` and across repeated runs.

## Spec 5

Both version spellings shall return 0, write nothing to stderr, and write exactly `1.4.1` followed by one line feed to stdout. There is no program-name prefix or other version text.

All three key-table spellings shall return 0, write nothing to stderr, and produce identical deterministic output. The visible table is:

```text
┌───────────┬────────────────┐
│keys       │action          │
├───────────┼────────────────┤
│Navigate   │← ↑ ↓ →         │
│           │h j k l         │
│           │Mouse::WheelUp  │
│           │Mouse::WheelDown│
├───────────┼────────────────┤
│Toggle     │enter           │
│           │Mouse::Left     │
├───────────┼────────────────┤
│Deep       │                │
│ - Expand  │+               │
│ - Collapse│-               │
├───────────┼────────────────┤
│Exit       │Escape          │
│           │q               │
├───────────┼────────────────┤
│Navigate   │                │
│ - first   │page-up         │
│ - last    │page-down       │
│ - top     │gg              │
│ - bottom  │G               │
└───────────┴────────────────┘
```

For exact byte compatibility, every line before the bottom border is followed by CR LF. In the header row only, `keys       ` and `action          ` are each preceded by `ESC[36mESC[49m` and followed by `ESC[39mESC[49m`, where `ESC` is the single byte 0x1B and no spaces occur in these sequences. After the bottom-right `┘`, write a NUL byte and then LF (with no CR there). Text-mode readers therefore observe the displayed lines with LF endings, a NUL immediately before the final LF, and an output ending in LF.

## Spec 6

If a positional file is supplied, open that exact path as a binary input stream. File extensions have no significance. Relative paths, absolute paths, long paths, spaces, Unicode, quotes, punctuation, repeated separators, and other ordinary path characters are not altered by the program. If the path cannot be opened as a readable input stream, write exactly:

```text
Could not open file <argument>
```

to stderr, substituting the original argument byte-for-byte, write nothing to stdout, and return 1. The diagnostic has one final LF.

A directory operand is not rejected by a separate file-type check. When an existing directory is supplied on the reference platform, opening and reading it yields an empty input stream. The result is therefore status 1, empty stdout, and the exact empty-input parse diagnostic from Spec 10 on stderr (including its leading and trailing LF), rather than `Could not open file <argument>\n`.

If there is no file operand, read the complete standard input. Before reading/parsing, write exactly `Reading from stdin...` to stdout and flush it; do not append a newline. This message is emitted for valid, malformed, empty, and whitespace-only stdin. File input never emits this message.

## Spec 7

Unknown options, invalid option values or clusters, and too many positional arguments produce status 1, empty stdout, and exactly `Invalid arguments\n` on stderr. File-open errors use Spec 6. JSON errors use Spec 10. No error mentions commands, subcommands, configuration, usage hints, or a help suggestion.

## Spec 8

Input is one strict JSON text surrounded by arbitrary JSON whitespace. Accept every root type: object, array, string, number, `true`, `false`, and `null`. Accept compact and pretty-printed forms. Objects require double-quoted keys, colons, and comma-separated members; arrays require comma-separated values. String escapes are exactly `\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t`, and `\u` followed by four hexadecimal digits, including valid surrogate-pair escapes. Unescaped code points U+0000 through U+001F are forbidden.

Numbers follow `-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?`. Preserve enough range and precision to accept signed 64-bit endpoints, unsigned values such as 9999999999999999999, decimals, negative zero, and finite exponents through approximately `1e±308`. `NaN`, `Infinity`, hexadecimal, a leading plus, leading zeroes, a leading/trailing decimal point, and an incomplete exponent are not JSON.

After the root value, only whitespace and end-of-input are allowed. Comments, single quotes, bare identifiers, capitalized keywords, trailing commas, mismatched delimiters, and multiple root values are rejected.

## Spec 9

Decode input as well-formed UTF-8 and render Unicode without ASCII-escaping it. Reject invalid start bytes, invalid or absent continuation bytes, overlong encodings, malformed surrogate data, and incomplete sequences with a parse error containing `ill-formed UTF-8 byte`. Valid multilingual text, emoji, combining characters, and zero-width characters are accepted.

There shall be no small fixed input, string, collection, or nesting limit. At minimum, parsing and initial display must safely handle 500 nested objects or arrays, a 5 MiB string, a stdin document larger than 100 KiB, 1,000 mixed/deep items, and arrays with tens of thousands of elements within a few seconds. Duplicate object member names are accepted; the last occurrence replaces earlier occurrences.

## Spec 10

Every JSON parse failure returns 1. Its stderr is a leading LF, one diagnostic line, and a trailing LF. The diagnostic begins `[json.exception.parse_error.101] parse error at line L, column C: `, where lines and columns identify the byte position as illustrated below. Positions are normally one-based; an illegal literal line feed inside a string is attributed to the new line at column 0. Stdin still has the separate, non-newline-terminated stdout message from Spec 6; file parsing has empty stdout.

The remainder distinguishes context and token. These exact mappings define the required wording (each `D(...)` below means LF + the displayed string + LF):

- Empty input: `D([json.exception.parse_error.101] parse error at line 1, column 1: attempting to parse an empty input; check that your input string or stream contains the expected JSON)`.
- `not json`: `D([json.exception.parse_error.101] parse error at line 1, column 2: syntax error while parsing value - invalid literal; last read: 'no')`.
- `{"a": 1}{"b": 2}`: `D([json.exception.parse_error.101] parse error at line 1, column 9: syntax error while parsing value - unexpected '{'; expected end of input)`.
- `[}`: `D([json.exception.parse_error.101] parse error at line 1, column 2: syntax error while parsing value - unexpected '}'; expected '[', '{', or a literal)`.
- `{"num": 0123}`: `D([json.exception.parse_error.101] parse error at line 1, column 12: syntax error while parsing object - unexpected number literal; expected '}')`.
- `{"num": +123}`: `D([json.exception.parse_error.101] parse error at line 1, column 9: syntax error while parsing value - invalid literal; last read: '"num": +')`.
- `{'key': 'value'}`: `D([json.exception.parse_error.101] parse error at line 1, column 2: syntax error while parsing object key - invalid literal; last read: '{''; expected string literal)`.
- A literal LF in `{"key": "line1<LF>line2"}`: `D([json.exception.parse_error.101] parse error at line 2, column 0: syntax error while parsing value - invalid string: control character U+000A (LF) must be escaped to \u000A or \n; last read: '"line1<U+000A>')`.
- A literal tab in `{"key": "before<TAB>after"}`: `D([json.exception.parse_error.101] parse error at line 1, column 16: syntax error while parsing value - invalid string: control character U+0009 (HT) must be escaped to \u0009 or \t; last read: '"before<U+0009>')`.
- A literal NUL in `{"key": "value<NUL>here"}`: `D([json.exception.parse_error.101] parse error at line 1, column 15: syntax error while parsing value - invalid string: control character U+0000 (NUL) must be escaped to \u0000; last read: '"value<U+0000>')`.
- `{"num": 0xFF}`: `D([json.exception.parse_error.101] parse error at line 1, column 10: syntax error while parsing object - invalid literal; last read: '0x'; expected '}')`.
- `{"num": Infinity}` and `{"num": NaN}` fail at column 9 with `syntax error while parsing value - invalid literal; last read: '"num": I'` and `... last read: '"num": N'`, respectively.
- `{"key": "value" /* comment */}`: `D([json.exception.parse_error.101] parse error at line 1, column 17: syntax error while parsing object - invalid literal; last read: '"value" /'; expected '}')`.
- `{"key": "invalid\x20escape"}`: `D([json.exception.parse_error.101] parse error at line 1, column 18: syntax error while parsing value - invalid string: forbidden character after backslash; last read: '"invalid\x')`.
- `{"key": "incomplete\u00"}`: `D([json.exception.parse_error.101] parse error at line 1, column 24: syntax error while parsing value - invalid string: '\u' must be followed by 4 hex digits; last read: '"incomplete\u00"')`.
- `{"key" "value"}`: `D([json.exception.parse_error.101] parse error at line 1, column 14: syntax error while parsing object separator - unexpected string literal; expected ':')`.
- `{"a": 1 "b": 2}`: `D([json.exception.parse_error.101] parse error at line 1, column 11: syntax error while parsing object - unexpected string literal; expected '}')`.
- `[1 2 3]`: `D([json.exception.parse_error.101] parse error at line 1, column 4: syntax error while parsing array - unexpected number literal; expected ']')`.
- `{key: "value"}`: `D([json.exception.parse_error.101] parse error at line 1, column 2: syntax error while parsing object key - invalid literal; last read: '{k'; expected string literal)`.
- `{"num": 1.2.3}`: `D([json.exception.parse_error.101] parse error at line 1, column 12: syntax error while parsing object - invalid literal; last read: '1.2.'; expected '}')`.
- `{"num": 123.}`: `D([json.exception.parse_error.101] parse error at line 1, column 13: syntax error while parsing value - invalid number; expected digit after '.'; last read: '123.}')`.
- `{"num": .123}` fails at column 9 as an invalid literal with last read `'"num": .'`.
- `{"num": 123e}`: `D([json.exception.parse_error.101] parse error at line 1, column 13: syntax error while parsing value - invalid number; expected '+', '-', or digit after exponent; last read: '123e}')`.
- `{"num": 123e-}`: `D([json.exception.parse_error.101] parse error at line 1, column 14: syntax error while parsing value - invalid number; expected digit after exponent sign; last read: '123e-}')`.

For an EOF after a started structure, report the parsing context and expected token: an object awaiting a member says `syntax error while parsing object key - unexpected end of input; expected string literal`; an object awaiting its close says `syntax error while parsing object - unexpected end of input; expected '}'`; an array says `syntax error while parsing array - unexpected end of input; expected ']'`; and a missing value says it expected `'[', '{', or a literal`. A physical final newline advances EOF to the next line, column 1. These rules also apply recursively.

## Spec 11

The UI renders a parsed JSON tree, not the original lexical formatting. Object keys are sorted lexicographically by their decoded strings. Array order is preserved. Duplicate-key replacement occurs before sorting. Each structural indentation level is two ASCII spaces. Object keys and string values are surrounded by literal double-quote characters, but decoded string content is not JSON-escaped for display: embedded double quotes and backslashes are displayed literally, without a preceding escape added by the renderer. Booleans are lowercase `true`/`false`, null is `null`, integers are decimal, and floating values use a compact faithful decimal representation.

Expanded containers use conventional pretty JSON punctuation: opening delimiter, one member/element per line, commas after every nonfinal sibling, then the aligned closing delimiter. An expanded empty object is two lines, `{` then `}`. A collapsed nonempty or empty object is `{...}`; a collapsed array is `[...]`. A root primitive without a decoded line break is one line. A decoded LF in a string value creates an actual visible line break instead of the two displayed characters `\` and `n`. For example, the root JSON text `"hello\nworld"` appears as two visible lines:

```text
"hello
world"
```

The valid input `{"é":"你好 👩‍💻 é","esc":"quote: \" slash: \\ tab:\t","pair":"\ud83d\ude00"}` initially appears as:

```text
{
  "esc": "quote: " slash: \ tab:",
  "pair": "😀",
  "é": "你好 👩‍💻 é"
}
```

In particular, the decoded quote and backslash in `esc` are literal display characters, and the decoded tab is not shown as the two-character sequence `\t`. Every visible snapshot line has no trailing padding, and the final visible line has LF.

For example, `{"name":"John Doe","age":30,"active":true,"balance":null}` initially appears as:

```text
{
  "active": true,
  "age": 30,
  "balance": null,
  "name": "John Doe"
}
```

## Spec 12

Initial expansion is depth based. The root container is expanded. Object-valued children directly below the root are also expanded, including object elements of a root array; deeper containers are collapsed. Array-valued children or elements below the root are initially collapsed. Thus:

```json
{"count":42,"items":["apple","banana","cherry"],"user":{"name":"Alice","email":"alice@example.com"}}
```

initially renders as:

```text
{
  "count": 42,
  "items": [...],
  "user": {
    "email": "alice@example.com",
    "name": "Alice"
  }
}
```

and `{"level1":{"level2":{"level3":{"value":"deep"}}}}` initially shows `level1` expanded and `level2` as `{...}`.

## Spec 13

Every object and array is an independently focusable expandable item. Focus begins on the root item. `Enter`, Space, or a left-mouse activation toggles the focused container between expanded and collapsed without losing its remembered descendants' states. Toggling a primitive has no structural effect. Repeating a toggle is reversible and deterministic.

Focus styling may use ANSI attributes and is not part of the whitespace of the JSON serialization. When terminal control codes are interpreted or stripped, navigation alone on a document that already fits remains the same visible text. Collapsing the root object from Spec 11 produces exactly `{...}\n`; re-expanding restores the initial five-line object.

## Spec 14

`+` performs one global deep-expansion step: find the shallowest currently hidden frontier beneath expanded ancestors and expand every container at that frontier. Repeated `+` therefore reveals one additional nesting level at a time, and becomes idempotent once the whole tree is expanded.

`-` performs the inverse global step: collapse every expanded container at the greatest expanded depth, leaving shallower parents visible. Repeated `-` works upward one level at a time. For sibling branches it acts on all branches at that depth, and a single collapse after a deep expansion collapses the deepest leaves before their parents. For `{"a":{"b":1,"c":2},"d":{"e":3}}`, `-` from the initial state leaves the root displayed with both `"a": {...}` and `"d": {...}`; the next `+` restores `b`, `c`, and `e`. No additional `+` after full expansion changes the screen.

## Spec 15

Keyboard navigation is supported with Left/Up/Down/Right and the equivalent `h`/`k`/`j`/`l`. Up and Down traverse focusable items in visible pre-order. Left and Right traverse adjacent controls at the same UI location, including the table-view switch. Mouse wheel up/down performs vertical navigation. Page Up and Page Down each move by one visible focus target in the same directions as Up and Down, respectively; they do not jump to the first or last target. The two-key sequence `gg` jumps to the last visible focus target. Uppercase `G` is ignored: it changes neither focus nor the viewport. These runtime behaviors apply even though the literal key table in Spec 5 labels Page Up/Page Down as `first`/`last`, `gg` as `top`, and `G` as `bottom`. Navigation clamps safely at boundaries and scrolls the viewport as needed to keep the focused item reachable.

Other unbound letters, digits, Tab, punctuation, and rapid mixed key sequences are ignored safely. They must not terminate, blank, or corrupt the UI. `q` and Escape each immediately quit from either display mode.

## Spec 16

An array is table-capable when every element is an object and either the array has at least two rows or the union of its object keys has at least two columns. A one-row, one-column array such as `[{"id":1}]` is not table-capable. Heterogeneous arrays are not table-capable. Sparse object rows are allowed.

Table-capable arrays initially remain in ordinary array view and have a focusable literal label `(table view)` on the opening/placeholder line, separated from the JSON delimiter by three spaces. For a root expanded array the first line is `[   (table view)`; for a collapsed root it is `[...]   (table view)`; for a nested field it can be `"users": [...],   (table view)`. Non-table-capable arrays have no such label.

## Spec 17

Activating `(table view)` changes that array to a grid and replaces the control with `(array view)` on its own first line. Activating `(array view)` restores the exact prior ordinary array rendering. The table columns are the union of keys in first-encounter order while scanning rows; because each parsed object itself has sorted keys, a uniform row's columns are lexical, while later sparse keys append at the end. Cells contain compact JSON representations, including quotes around strings. A missing key is an empty padded cell, not `null`. Each column width is the greater terminal display width of its header and all rendered cells.

The grid has an unbordered zero-based row-number column and these exact border styles: heavy `┏━┳━┓` top/header borders, `┃` around headers, `┡━╇━┩` between header and data, light `│` between data cells, and `└─┴─┘` at the bottom. For `[ {"id":1}, {"id":2}, {"id":3} ]` the result is:

```text
(array view)
 ┏━━┓
 ┃id┃
 ┡━━┩
0│1 │
1│2 │
2│3 │
 └──┘
```

For `[ {"id":1,"name":"Alice","age":30} ]`, sorted columns and padding produce:

```text
(array view)
 ┏━━━┳━━┳━━━━━━━┓
 ┃age┃id┃name   ┃
 ┡━━━╇━━╇━━━━━━━┩
0│30 │1 │"Alice"│
 └───┴──┴───────┘
```

## Spec 18

These rendering examples further define punctuation, table labels, empty nested containers, and collapse behavior. The input

```json
[{"id":1,"name":"Product A","price":19.99,"inStock":true},{"id":2,"name":"Product B","price":29.99,"inStock":false},{"id":3,"name":"Product C","price":39.99,"inStock":true}]
```

has this initial ordinary-array view:

```text
[   (table view)
  {
    "id": 1,
    "inStock": true,
    "name": "Product A",
    "price": 19.99
  },
  {
    "id": 2,
    "inStock": false,
    "name": "Product B",
    "price": 29.99
  },
  {
    "id": 3,
    "inStock": true,
    "name": "Product C",
    "price": 39.99
  }
]
```

Its table view is:

```text
(array view)
 ┏━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━┓
 ┃id┃inStock┃name       ┃price┃
 ┡━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━┩
0│1 │true   │"Product A"│19.99│
1│2 │false  │"Product B"│29.99│
2│3 │true   │"Product C"│39.99│
 └──┴───────┴───────────┴─────┘
```

If focus moves down from the root to the first array object and that object is toggled, only that row becomes `{...},`; the other two objects retain their expanded rendering.

## Spec 19

Normal mode uses an inline interactive screen. It adapts to terminal width and height and, after quit, leaves the final visible JSON in the terminal scrollback. Fullscreen mode, selected by either `-f` or `--fullscreen` in any pre-terminator position, uses the terminal alternate screen buffer and occupies the terminal viewport; quitting restores the prior screen and shell. Both modes have identical JSON tree content, initial expansion rules, table behavior, navigation, and quit keys.

The program shall emit appropriate ANSI terminal control sequences while interactive and use color/attributes for JSON/UI elements, while keeping the visible characters described here. It shall work in pseudo-terminals of at least 80×24, 100×30, and 120×40. Rendering begins promptly (well under half a second for ordinary documents), and input events update the display promptly.

## Spec 20

Long values wrap responsively rather than being dropped or causing a crash. Continuation lines align under the value portion, not under the object opening brace, and the visible viewport clips content that does not fit. At the standard 80-column inline capture used for a long-value view, the beginning of

```json
{"short":"short value","long":"This is a very long string that should demonstrate how the TUI handles text wrapping and display of strings that exceed the normal line width. It contains multiple sentences to ensure we have enough content to test proper rendering behavior.","very_long":"Lorem ipsum dolor sit amet"}
```

is exactly:

```text
{
  "long": "This is a very long string that should demonstrate how the TUI    ,
          handles text wrapping and display of strings that exceed the normal
          line width. It contains multiple sentences to ensure we have enough
          content to test proper rendering behavior."
```

The unusual spaces before the comma on the first wrapped line are intentional terminal-layout behavior. Scrolling/navigation must remain safe for large objects and arrays, and all visible UTF-8 characters must remain intact rather than being replaced or split mid-sequence. In particular, in an 80×24 viewport showing an object with members `"000":0` through `"099":99` followed by `"zzz":"終😀"`, pressing uppercase `G` leaves the viewport at the top, with members `000` through `022` visible and `zzz` not visible.

## Spec 21

For completeness, the following newline-terminated file contents pin additional exact diagnostics that are compared literally. As in Spec 10, each listed diagnostic is surrounded by one leading and one trailing LF on stderr, and stdout is empty. Spaces shown in an input are significant.

- Input `{<LF>`: `[json.exception.parse_error.101] parse error at line 2, column 1: syntax error while parsing object key - unexpected end of input; expected string literal`
- Input `{"key": "value",}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 17: syntax error while parsing object key - unexpected '}'; expected string literal`
- Input `{"key": "bad\xescape"}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 14: syntax error while parsing value - invalid string: forbidden character after backslash; last read: '"bad\x'`
- Input consisting only of `<LF>`, or of three spaces followed by `<LF>`: `[json.exception.parse_error.101] parse error at line 2, column 1: syntax error while parsing value - unexpected end of input; expected '[', '{', or a literal`
- Input `not json at all<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 2: syntax error while parsing value - invalid literal; last read: 'no'`
- Input `{invalid json<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 2: syntax error while parsing object key - invalid literal; last read: '{i'; expected string literal`
- Input `{"a":1<LF>`: `[json.exception.parse_error.101] parse error at line 2, column 1: syntax error while parsing object - unexpected end of input; expected '}'`
- Input `[1, 2, 3<LF>`: `[json.exception.parse_error.101] parse error at line 2, column 1: syntax error while parsing array - unexpected end of input; expected ']'`
- Input `{"key": 123abc}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 12: syntax error while parsing object - invalid literal; last read: '123a'; expected '}'`
- Input `{"key": NaN}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 9: syntax error while parsing value - invalid literal; last read: '"key": N'`
- Input `{"key" "value"}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 14: syntax error while parsing object separator - unexpected string literal; expected ':'`
- Input `{"key": "value" "extra"}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 23: syntax error while parsing object - unexpected string literal; expected '}'`
- Input `{"valid": true}<LF>{"second": false}<LF>`: `[json.exception.parse_error.101] parse error at line 2, column 1: syntax error while parsing value - unexpected '{'; expected end of input`
- Input `{"unescaped": "bad"quote"}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 20: syntax error while parsing object - invalid literal; last read: '"bad"q'; expected '}'`
- Input `[,]<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 2: syntax error while parsing value - unexpected ','; expected '[', '{', or a literal`
- Input `[1,,2]<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 4: syntax error while parsing value - unexpected ','; expected '[', '{', or a literal`
- Input `[1,]<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 4: syntax error while parsing value - unexpected ']'; expected '[', '{', or a literal`
- Input `[1 2]<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 4: syntax error while parsing array - unexpected number literal; expected ']'`
- Input `{"key":undefined}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 8: syntax error while parsing value - invalid literal; last read: '"key":u'`
- Input `{"key": undefined}<LF>`: `[json.exception.parse_error.101] parse error at line 1, column 9: syntax error while parsing value - invalid literal; last read: '"key": u'`
- Input `{"key":"val<LF>` or `{"key": "val<LF>`: `[json.exception.parse_error.101] parse error at line 2, column 0: syntax error while parsing value - invalid string: control character U+000A (LF) must be escaped to \u000A or \n; last read: '"val<U+000A>'`

For stdin specifically, `{"name": "test",, "value": 123}` produces the same LF-wrapped form with line 1, column 17 and `syntax error while parsing object key - unexpected ','; expected string literal`. The stdin text `{"name": "test", "value": <LF>` produces line 2, column 1 and `syntax error while parsing value - unexpected end of input; expected '[', '{', or a literal`. These diagnostic requirements supplement, rather than relax, the general strict-parser behavior in Specs 8–10.
