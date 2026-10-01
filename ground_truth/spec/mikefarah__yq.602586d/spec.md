# Clarified specification for the `yq` executable

This document is the complete behavioural contract for the executable. It is a command-line structured-data processor named `yq`. Unless a rule explicitly permits variation, output is UTF-8, mapping keys retain insertion order, successful output ends in LF, diagnostics go to standard error, and success/failure means exit status 0/non-zero. Raw `-o=base64` and `-o=uri` output, and `-o=xml` output for a scalar root, are the exceptions: they have no trailing LF.

The internal value model is a stream of YAML-compatible nodes: null, Boolean, arbitrary signed integer, IEEE-754 float, string, ordered mapping, or sequence. Ordinary strings contain Unicode text; a string produced by Base64 decoding may instead carry opaque bytes so it can be re-encoded without loss. Nodes also carry a YAML tag, style, anchor/alias identity, head/line/foot comments, source filename, zero-based file/document indexes, and one-based source line/column. Operations preserve metadata unless their purpose changes it. An empty result stream differs from a stream containing null.

## Spec 1

`--version` and `-V` print one line: `yq (https://github.com/mikefarah/yq/) version v4.52.5`. Another numeric semantic version is allowed, but name, URL, word `version`, leading `v`, spacing, and LF are mandatory. `--help`/`-h` return 0 and print a full page containing `Usage:`, `Available Commands:`, commands `eval`, `eval-all`, `completion`, and all flags below.

The default command is `eval`, alias `e` or no command. `eval-all` has alias `ea`. `eval --help` contains `Evaluate Sequence` and `yq eval`; `eval-all --help` describes loading all YAML documents. Flags work before/after positional arguments where unambiguous and accept `--flag value` and `--flag=value`. Short format flags also accept equals forms: in particular, `eval -p=hcl -o=yaml -` parses HCL stdin and emits YAML.

Input formats/aliases: `auto|a`, `yaml|y`, `kyaml|ky`, `json|j`, `properties|props|p`, `csv|c`, `tsv|t`, `xml|x`, `base64`, `uri`, `toml`, `hcl|h|tf`, `lua|l`, `ini|i`. The accepted but unadvertised `tf` alias works in short equals forms such as `-p=tf` and `-o=tf`. Output also supports `shell|s`. Accept compact forms such as `-oy`, `-oj`, `-pj`. An unknown long flag begins stderr with `Error: unknown flag: --invalid-flag-that-does-not-exist` and then prints root usage. Despite accepting `properties` and `tf`, the unknown-format diagnostic uses the shorter advertised list: either `-o=badformat` or `-p=badformat` fails with exactly `Error: unknown format 'badformat' please use [yaml|y|kyaml|ky|json|j|props|p|csv|c|tsv|t|xml|x|base64|uri|toml|hcl|h|shell|s|lua|l|ini|i]\n`. Invalid flags/formats never panic.

## Spec 2

An invocation selects a command, expression, and zero or more input sources. Default expression is `.`. `--expression EXPR` forces EXPR even if a file has that name. `--from-file PATH` reads the complete expression, accepting LF/CRLF. There is no directly executable expression-file/shebang mode. In a directory containing the executable as `./yq`, an executable file named `pick` containing exactly `#!./yq\n.a.b\n`, invoked as `./pick data.yml` with `data.yml` containing `a: {b: apple}\n`, is decoded as the first data input rather than as an expression. The invocation returns 0, writes no stderr, and emits exactly `#!./yq\n.a.b\n---\na: {b: apple}\n`.

Without `-n`, read named sources in order. Literal `-` means stdin at that position. If no file is named, read stdin. If real files are named without `-`, do not additionally read stdin. When every positional argument names an existing data file and no expression was forced, all of them are input files and the expression is identity; this is why the `pick` script and `data.yml` in the preceding example are both decoded as data. Otherwise the first positional is the expression and the remaining ones are files. The all-existing-files rule applies to both `eval` and `eval-all`, including with `-i`; for example, `-i first.yml second.yml` appends the second document to `first.yml` and leaves `second.yml` unchanged.

`auto` uses case-insensitive extension: `.yaml/.yml` YAML, `.json/.tfstate` JSON, `.xml`, `.csv`, `.tsv`, `.properties`, `.toml`, `.hcl/.tf`, `.lua`, `.ini`; unknown/stdin defaults YAML. With auto input, default output is the detected file format; explicit `-o` wins. Supplying `-p/--input-format` explicitly while leaving output auto selects YAML for backward compatibility. For a named `.hcl`, `.tf`, or `.json` file, it writes a timestamped compatibility warning to stderr; thus a scalar selected from an explicitly parsed HCL file succeeds and is emitted as an unwrapped YAML scalar line rather than being rejected as a non-map HCL root. Explicitly parsed stdin also defaults to YAML, but does so silently: `printf 'a = "apple"\n' | yq -p=tf .a` returns 0, emits exactly `apple\n`, and has empty stderr. Empty YAML sources add no decoded document when other documents exist, but if the entire invocation's input is zero bytes, evaluation occurs once against an empty, null-like document and identity emits exactly one LF. Blank-only input is distinct: identity preserves its LF bytes, so inputs consisting of one, two, or three LF bytes emit respectively one, two, or three LF bytes. An update evaluates against the zero-byte fallback document: `.apple = "tree"` emits exactly `apple: tree\n` under both `eval` and `eval-all`. `-n/--null-input` evaluates once on synthetic null and reads nothing; files with `-n` fail `Error: cannot pass files in when using null-input flag`.

## Spec 3

`completion`, alias `shell-completion`, accepts exactly one lowercase argument: `bash`, `zsh`, `fish`, or `powershell`. It writes only stdout and alias output is byte-identical. Names are case-sensitive. Bash starts `# bash completion V2 for yq`, exceeds 100 lines/1000 bytes, uses `COMPREPLY`, `__complete`, directive bit flags, and functions `__yq_debug`, `__yq_init_completion`, `__yq_get_completion_results`, `__yq_process_completion_results`, `__yq_handle_completion_types`, `__yq_handle_standard_completion_case`, `__yq_handle_special_char`. Zsh starts `#compdef yq`, second line `compdef _yq yq`, and contains `_yq()`, `_describe`, `__yq_debug`, `__complete`. Fish starts `# fish completion for yq` and contains `function __yq_perform_completion`, `function __yq_debug`, `commandline`, `YQ_ACTIVE_HELP`, `__complete`, `complete -c yq`. PowerShell starts `# powershell completion for yq` and contains `[scriptblock]`, `__yqCompleterBlock`, `function __yq_debug`, `param(` with `$WordToComplete`, `$CommandAst`, `$CursorPosition`, `__complete`, and `Register-ArgumentCompleter -CommandName 'yq'`.

Bad argument count/shell returns 1 and prints `Error:` plus usage `yq completion [bash|zsh|fish|powershell]`. Messages include respectively `accepts 1 arg(s), received 0`, `accepts 1 arg(s), received 2`, or `invalid argument "VALUE" for "yq completion"`. Help contains that usage, `Aliases:`, `completion, shell-completion`, and `Bash:`, `Zsh:`, `Fish:` installation instructions. Spec 36 supplies byte-exact assets.

The completion protocol command is also callable directly. `__complete ""` returns 0 and stdout is exactly:

```text
completion\tGenerate the autocompletion script for the specified shell
eval\t(default) Apply the expression to each document in each yaml file in sequence
eval-all\tLoads _all_ yaml documents of _all_ yaml files and runs expression once
help\tHelp about any command
:4
```

Each displayed `\t` in that block denotes one horizontal tab and every displayed line ends in LF. Stderr is exactly `Completion ended with directive: ShellCompDirectiveNoFileComp\n`.

## Spec 4

Default/eval decodes every document from every source and evaluates separately in order. `documentIndex` is zero-based within each source and resets to zero for the next source; it is not a global logical-stream index. `fileIndex` is zero-based by source, and `filename` is the exact input name (`-` for stdin). For a two-document first file followed by a one-document second file, evaluating `documentIndex` emits exactly `0\n1\n0\n`, while `fileIndex` emits `0\n0\n1\n`. `di` is an exact shorthand for `documentIndex`, including inside assignment selectors. Results retain source metadata except when an operator creates a fresh scalar result, as the metadata accessors themselves do.

`eval-all` decodes all sources then evaluates once with all documents as a stream. Thus `. as $item ireduce ({}; . * $item)` merges documents, `[.]` collects them, and `select(fileIndex == 1)` filters sources. Plain `.` emits every loaded document. Zero-byte sources use the whole-invocation fallback from Spec 2: one or multiple all-zero-byte files produce exactly one LF, while a zero-byte file beside nonempty documents adds no result. Blank-only YAML follows Spec 2 instead. Both modes support stdin, explicit `-`, multiple files, multi-doc YAML.

Separate YAML results that belong to distinct source documents with `---`; do not prefix the first ordinary single document. Multiple scalar results selected from the same source document are adjacent lines without separators even though they originated in that document. This applies to `.[]`, `map(EXPR) | .[]`, `select(...)`, alternatives, and recursive descent: for example `[1, null, 2, null, 3] | .[] | select(. != null)` emits exactly `1\n2\n3\n`, and `[reading, hiking, coding] | .[]` emits exactly `reading\nhiking\ncoding\n`. Fresh scalar results and metadata accessors are likewise adjacent. In particular, evaluating `fileIndex` over two one-document files emits exactly `0\n1\n`, whereas `documentIndex` emits `0\n0\n` because its counter is per file. Preserve a leading explicit separator where input leading content requires it. Four identity documents across two files have exactly three separators. `-N/--no-doc` suppresses generated separators.

## Spec 5

Syntax, decoding, file, security, type, and encoding failures return non-zero, use useful stderr, and do not panic/hang/stack-trace. A missing input or expression file reports `Error: open ` followed by the supplied path and `: no such file or directory`; this is identical under `eval` and `eval-all`. Passing `/tmp` as input reports exactly `Error: read /tmp: is a directory`. A decoder error begins `Error: bad file '`, then the input name, then `': ` and the decoder reason. Malformed expressions (`[[invalid`, `.a =`, `.a |`) fail. Expression `bad syntax ][` reports exactly `Error: 1:1: lexer: invalid input text "bad syntax ]["\n`. The explicit-command invocation `eval '..invalid'` reports exactly `Error: 1:3: lexer: invalid input text "invalid"`. Under `eval-all`, malformed expression `.[invalid` produces that same exact diagnostic and no stdout. For stdin containing `[{"name": "value"}` under `-p json`, stderr is exactly `Error: bad file '-': json: array of object unexpected end of JSON input\n`. For YAML stdin `good: value\n  bad_indent: here\n`, stderr is exactly `Error: bad file '-': yaml: line 2, column 13: mapping values are not allowed in this context\n`. The `@jsond` operator's distinct diagnostic is specified in Spec 33.

`-e/--exit-status` returns 1 and writes `Error: no matches found` to stderr if the complete evaluation emits nothing or only null/false; values are still printed. It returns 0 if any result is true, zero, empty string, empty sequence/map, or another non-null/non-false value. Accumulate across all results.

Exact combination errors:

```text
Error: write in place flag only applicable when giving an expression and at least one file
Error: write in place cannot be used with split file
Error: cannot pass files in when using null-input flag
```

The first covers `-i` without an input file, the second `-i` with split output.

## Spec 6

Parse UTF-8 YAML 1.2 streams: block/flow maps and sequences, quoted scalars/escapes, literal/folded blocks and chomping, directives/separators/end markers, standard/application tags, anchors, aliases, merge keys, comments, CRLF, Unicode, numeric keys, duplicate keys, empty/multiple documents. Explicit empty documents retain whether the final marker was LF-terminated. Input `---\n---\n---\n` serializes exactly as `---\n---\n---\n`, but a final marker at EOF contributes an empty content line: `name: John\n---` serializes exactly as `name: John\n---\n\n`, and `---\na: test\n---\nb: test2\n---` serializes exactly as `---\na: test\n---\nb: test2\n---\n\n`. Scalar content placed on a document-marker line is normalized onto the following line: `---  hello world\n` becomes exactly `---\nhello world\n`. Identity conversion retains leading `---` markers but consumes and omits every YAML document-end marker `...`; `---\ndoc1: value1\n...\n---\ndoc2: value2\n...\n` therefore becomes `---\ndoc1: value1\n---\ndoc2: value2\n`. Reject tab indentation, malformed indentation, unclosed quotes/flows, invalid/forward anchors with line/column.

For the corresponding malformed inputs, YAML decoder reasons include exactly `unknown anchor 'forward' referenced`, `did not find expected ',' or ']'`, `did not find expected alphabetic or numeric character`, and `did not find expected key`. A tab used for indentation reports `found character that cannot start any token`. For `root:\n  child1: value1\n   child2: value2\n` on stdin, stderr is exactly `Error: bad file '-': yaml: line 3, column 10: mapping values are not allowed in this context\n`. A leading comment is excluded from this decoder's reported line count: `# leading comment\nroot:\n  child1: value1\n   child2: value2\n` produces the same `line 3, column 10` reason even though the malformed content is on physical line four. These diagnostics follow the bad-file prefix from Spec 5.

Plain `null` variants, `~`, omitted values are null; true/false case variants are Boolean; `yes/no/on/off` remain strings. Parse signed decimal, `0x` hex, `0o` octal, `0b` binary, numeric underscores, decimal/scientific floats, `.inf`, `-.inf`, `.nan`; preserve spelling/base/style when untouched. RFC3339-like datetimes tag `!!timestamp`. Explicit tags override inference.

Mappings remain ordered and may have non-string scalar keys. `<<: *anchor` makes inherited fields traversable; explicit fields override inherited; merge sequences combine sources in order. On the default `--yaml-fix-merge-anchor-to-spec=false` setting, traversing an inherited merge value emits one stderr warning line beginning with `time=` and the current UTC timestamp, followed by this exact remainder: ` level=WARN msg="--yaml-fix-merge-anchor-to-spec is false; causing merge anchors to override the existing values which isn't to the yaml spec. This flag will default to true in late 2025. See https://mikefarah.gitbook.io/yq/operators/traverse-read for more details."\n`. For example, both `.service1.timeout | path` through `<<: *defaults` and `.obj.x, .obj.y` when `x` is inherited emit that warning while still producing their normal stdout. An anchor defined in an earlier YAML document remains available to aliases and merge keys in a later document of the same decoded source stream; forward references are still invalid. Preserve comments, blank/leading content, aliases/styles on identity/local updates. `--header-preprocess=false` retains line numbers and each document's leading comments.

## Spec 7

YAML/KYAML output preserves ordered values and all metadata carried by untouched nodes. Default indent two. Block maps use `key: value`, sequences `- value`; empty collections `{}`/`[]`; lowercase booleans; quote strings when needed for type/syntax. An ordinary explicit or newly constructed null is `null`, but a null node carrying empty scalar style is blank at the root as well as after a mapping colon or sequence dash (`key:` or `-`). In particular, Lua input `return nil\n` converted to YAML emits exactly one LF. CSV empty cells and `pivot` padding use that empty style. Scalar results unwrap by default (Spec 18). Identity and localized updates retain existing flow/quote/tag/anchor/alias/block styles, comments, numeric spelling, and directives; newly constructed nodes use the defaults in this section.

`-P/--prettyPrint` recursively changes collection styles to ordinary block form, clears explicit quote style from ordinary strings (including mapping keys), and preserves values and comments. Thus `leaveUnquoted: [yesSir, hellno, bonapite]\nmakeUnquoted: ["yesSir", "hellno", "bonapite"]\n` becomes exactly `leaveUnquoted:\n  - yesSir\n  - hellno\n  - bonapite\nmakeUnquoted:\n  - yesSir\n  - hellno\n  - bonapite\n`, and `"removeQuotes": "please"\n` becomes exactly `removeQuotes: please\n`. This normalization also applies after an expression: `.a --prettyPrint` on `a: {b: {c: ["cat"]}}\n` emits exactly `b:\n  c:\n    - cat\n`. A multiline string is re-encoded in block form as needed, so `"removeQuotes": |\n  "please"\n` becomes exactly `removeQuotes: |\n  "please"\n`. Strings whose spelling requires quotes to retain string type remain quoted. Plain uppercase YAML-1.1-looking strings such as `YES`, `NO`, `ON`, and `OFF` remain plain and uppercase. Newly constructed empty strings use double quotes (`""`), including as an array element. `-I N` controls indentation and accepts zero; for YAML, applying `-I 0` to `obj:\n  nested:\n    deep: value\n` emits `obj:\n    nested:\n        deep: value\n`, using four spaces per mapping level. `-c` is the short alias of `--yaml-compact-seq-indent`; both treat `- ` as indentation, so `a:\n  - 1\n  - 2\n` becomes `a:\n- 1\n- 2\n`. `--yaml-fix-merge-anchor-to-spec` uses Spec 6 overrides. Every non-NUL YAML/KYAML result ends LF.

## Spec 8

JSON input is strict UTF-8 JSON supporting objects, arrays, escapes/Unicode, booleans/null, negative/large integers, decimal/scientific numbers, empty structures/scalar roots. Reject truncation/malformed data; preserve object order and signed integer precision through at least `9999999999999`.

JSON output emits one independent value per result. Default indent 2, `-I 4` four spaces, `-I 0` compact one line. Auto-detected `.tfstate` is an exception: its default identity output is one line but retains a space after each colon and comma. For example, an indented `.tfstate` containing `{"mike":{"things":"cool"}}` emits exactly `{"mike": {"things": "cool"}}\n`; it is not the separator-free `-I 0` form. Double-quote keys/strings and escape controls/backslash/quotes; emit non-ASCII directly; retain scalar types; end LF. Strip YAML metadata and recursively explode aliases/merges. Multiple documents yield separate JSON values. `-j` selects the same stdout encoding as `-o=json`, but it additionally writes exactly `Flag --tojson has been deprecated, please use -o=json instead\n` to stderr; `-o=json` does not write that warning. `-r` may unwrap selected scalar strings.

## Spec 9

XML decode maps each element to a key named by its tag. Children nest; repeated same-name siblings become a sequence in encounter order. Attributes are string fields prefixed `+@`. Text on elements with attributes/children uses `+content`; text-only elements become scalar. Decode entities/CDATA. Before tokenization, tolerate horizontal whitespace preceding an XML declaration: input beginning with two spaces followed by `<?xml version="1.0"?>` succeeds rather than reporting that the declaration is not at the start. This tolerance applies with ordinary decoding and with `--xml-attribute-prefix`, `--xml-content-name`, and `--xml-proc-inst-prefix`. A decode followed by XML encode retains empty versus self-closing elements, namespaces and declarations, mixed-content ordering, comments, processing instructions, directives, element order, and significant whitespace.

For example `<item id="42">text</item>` decodes in content-before-attribute order as `{item: {+content: text, +@id: "42"}}`; `<root><x>a</x><x>b</x></root>` decodes as `{root: {x: [a,b]}}`. With `--xml-attribute-prefix ATTR --xml-content-name TEXT`, `<item id="7">hi</item>` likewise emits exactly `item:\n  TEXT: hi\n  ATTRid: "7"\n`. XML text is always a string, and when its spelling would otherwise be inferred as a different YAML type, YAML output uses double quotes: decoding `<root><foo>bar</foo><count>42</count></root>` emits `foo: bar` and `count: "42"`. Conversely `{root: {item: [{+@id: "1", +content: a}, {+@id: "2", +content: b}]}}` encodes as one `<root>` containing two `<item>` elements with those attributes/text.

Flags replace defaults: `--xml-attribute-prefix` (`+@`), `--xml-content-name` (`+content`), `--xml-directive-name` (`+directive`), `--xml-proc-inst-prefix` (`+p_`). `--xml-keep-namespace` defaults true: prefixes are retained even when the flag is omitted. Thus `<ns:root xmlns:ns="http://example.com"><ns:val>hello</ns:val></ns:root>` decodes with keys `ns:root` and `ns:val` and attribute key `+@xmlns:ns`. Encoding reverses representation, escapes XML special characters, repeats sequence elements, reconstructs metadata tokens, indents two spaces, preserves attribute order. An explicitly paired empty element stays paired on one line: `<map xmlns="some-namespace" xmlns:xsi="some-instance" xsi:schemaLocation="some-url"></map>` is not expanded across two lines. One mapping root is normal; scalar root emits its text without a trailing LF (`hello\n` as YAML input under `-o=xml` produces exactly the five bytes `hello`); sequence root/non-scalar attribute fails. Arrays under named keys become repeated elements.

Malformed XML token diagnostics use the phrase `XML syntax error`; for example, `<root>\n<child>\n</root!>\n` fails with exactly `Error: bad file '-': XML syntax error on line 3: invalid characters between </root and >\n`. Character data before any root element uses a distinct diagnostic: `text<root></root>\n` fails with exactly `Error: bad file '-': invalid XML: Encountered chardata [text] outside of XML node\n`.

`--xml-strict-mode` rejects use of document-local custom entity references. In particular, for a file named `test.yml` whose document declares `writer` and `copyright` in an internal `DOCTYPE` subset and whose line 7 contains `<item>&writer;&copyright;</item>`, `-p=xml --xml-strict-mode test.yml -o=xml` exits 1 with no stdout and writes exactly `Error: bad file 'test.yml': XML syntax error on line 7: invalid character entity &writer;\n` to stderr.

## Spec 10

CSV uses comma and TSV tab. First row is headers; each later row is ordered mapping in a root sequence. Implement doubled-quote RFC quoting, literal delimiters/newlines in quotes, UTF-8 BOM stripping. Empty fields decode as empty-style null nodes and consequently emit as blank YAML values (`field:`), not quoted empty strings. A BOM-prefixed header-only input emits `[]\n`. Entirely empty CSV input has no rows but still uses the whole-invocation empty-input fallback, so identity emits exactly one LF. Uneven rows fail.

Default auto-parse independently parses nonempty cells using YAML rules, including numbers/booleans/null/arrays/maps; CSV quotation does not force string type. `--csv-auto-parse=false`/`--tsv-auto-parse=false` are accepted, and the one-letter Boolean value `f` is accepted as the false spelling. With auto-parse disabled, scalar-looking cells such as `123`, `true`, and `null` still receive `!!int`, `!!bool`, and `!!null`, but collection-looking YAML is retained as a string rather than decoded. Thus CSV `name,count,data\nAlice,123,"[1, 2, 3]"\nBob,true,"{key: value}"\n` emits exactly `- name: Alice\n  count: 123\n  data: '[1, 2, 3]'\n- name: Bob\n  count: true\n  data: '{key: value}'\n`; likewise `thing1\nname: cat\n` with `--csv-auto-parse=f` emits exactly `- thing1: 'name: cat'\n`. `--csv-separator X` changes CSV input/output and validates the UTF-8 byte length as exactly one, not the Unicode code-point count. `--csv-separator ab` fails with a line beginning `Error: invalid argument "ab" for "--csv-separator" flag: [ab] is not a valid character. Must be length 1 was 2`; an empty argument fails with a line beginning `Error: invalid argument "" for "--csv-separator" flag: [] is not a valid character. Must be length 1 was 0`; and the one-character, two-byte separator `§` fails with a first line exactly `Error: invalid argument "§" for "--csv-separator" flag: [§] is not a valid character. Must be length 1 was 2`. Each then prints `eval` usage and exits non-zero.

## Spec 11

CSV/TSV output: sequence of mappings gets header from first map key order and one row/map; later missing fields empty and later extra keys ignored. Sequence of sequences has no header. Sequence of scalars is one row. Scalar root is one cell. Empty sequence emits nothing. An unsupported mapping root fails `Error: csv encoding only works for arrays, got: !!map`. Within a sequence of rows, a scalar where a sequence is required fails `Error: csv encoding only works for arrays of scalars (string/numbers/booleans), child[1] is a !!str`. A nested sequence or mapping cell at index 1 uses that same prefix and ends respectively `child[1] is a !!seq` or `child[1] is a !!map`. These failures are non-zero and emit no encoded CSV.

Render booleans lowercase and numbers ordinarily. Quote only delimiter/quote/CR/LF fields, doubling quotes. End rows LF; TSV uses tabs. Preserve order, Unicode, embedded newlines, and semantic CSV round trips.

## Spec 12

Properties decode non-comment `path = value` records into ordered nested mappings. Split at the first delimiter, trim adjacent whitespace, retain later `=`, preserve Unicode, and treat dot/numeric components as nested paths/indexes. Property values remain strings; when YAML needs quotes to preserve that type, use double quotes, so `port = 5432` becomes `port: "5432"` rather than single quotes. Empty input is empty. Preserve `#`/`!` comment blocks both in same-format round trips and when emitting YAML. A comment block immediately preceding a property becomes the decoded value's head comment: before `person.name` it appears inside `person` immediately before `name`, and before `person.pets.0` it appears inside `pets` immediately before `- cat`. Multiple comment lines retain their order.

Encoding recursively flattens maps/sequences. Default paths use dots and records `key = value`; `--properties-array-brackets` renders `[0]`; `--properties-separator S` replaces ` = `. Thus `{items: [one, two]}` encoded with `-o=properties` is exactly `items.0 = one\nitems.1 = two\n`. Root sequence uses numeric keys, scalar root prints scalar. Preserve traversal order, spaces/quotes in values, LF. YAML comments survive conversion: a root head comment is emitted first, and a head comment on a nested scalar is emitted immediately before that scalar's flattened property. For example the comments `# This is a comment` on the root and `# Database host` on `database.host` appear as those two lines before `database.host = localhost`.

## Spec 13

INI decode maps root `key = value` attributes and `[section name]` sections to an ordered mapping whose sections are mappings. Dots/spaces in section names are literal. Preserve Unicode and equals signs after the first delimiter. In an unquoted value, the first semicolon begins an inline comment and that semicolon and the remaining suffix are discarded: `root = x=y;z` decodes as exactly `root: x=y\n`. Every INI value is a string: for example `port = 5432`, `debug = true`, and `version = 1.0` become YAML strings `"5432"`, `"true"`, and `"1.0"`. Empty INI input decodes as an empty mapping, so `-p=ini -o=yaml` on zero bytes emits exactly `{}` followed by LF. A nonempty line lacking a delimiter fails with `failed to parse INI content: key-value delimiter not found`.

Encode root scalar fields first, then a blank line and each map as `[section]` plus scalar children. One blank line separates sections. Within each contiguous assignment group—including the root scalar group and each section—pad keys with spaces so all `=` signs align one column after that group's longest key. Thus root keys `name` and `version` emit `name    = config` and `version = 1.0`; section keys `key.with.dots`, `key-with-dashes`, and `key_with_underscores` emit exactly `key.with.dots        = value1`, `key-with-dashes      = value2`, and `key_with_underscores = value3`. An empty-style YAML null mapping value is an empty INI value: `database:\nserver:\n  host: localhost\n  port: 5432\n` encodes exactly as `database = \n\n[server]\nhost = localhost\nport = 5432\n`. Empty maps become empty sections. Skip unrepresentable sequence/deeper values. A scalar root passes through. A root sequence fails with `Error: INI encoder supports only MappingNode at the root level, got 1`. Preserve order and strings with spaces/quotes/special keys.

## Spec 14

TOML decode supports bare/quoted/dotted keys, pairs, tables/nested tables, inline tables, arrays, arrays-of-tables, comments, basic/literal/multiline strings, escapes, booleans, signed decimal/hex/octal/binary integers with underscores, decimal/scientific floats and `inf/-inf/nan`, offset/local datetime/date/time. Preserve order/type/timestamp spelling/Unicode/comments. Tables become maps and table arrays sequences of maps. TOML basic and literal multiline strings become YAML literal blocks with strip chomping. For example, a multiline value `This is a multi-line\nstring that spans\nmultiple lines` emits exactly `description: |-\n  This is a multi-line\n  string that spans\n  multiple lines\n`; a literal value containing the characters `\\n \\t` retains them literally inside the block. Reject invalid escapes, unclosed strings/arrays, missing commas, malformed inline tables/headers. Decoder reasons are precise: `\q` in a basic string reports `invalid escaped character U+0071 'q'`; a basic string split by LF reports `basic strings cannot have new lines`; an array that reaches EOF reports `expected character ] but the document ended here`; array elements on successive lines without commas report `array elements must be separated by commas`; a table header missing its closing bracket reports `expected character ]`; and an assignment `empty =` at end of input reports exactly `Error: bad file '-': expected value, not eof\n`. Each reason otherwise follows the Spec 5 bad-file prefix.

TOML encode visits root mapping entries in insertion order. Nonempty block-style nested maps use `[a.b]`, while nonempty flow-style maps use inline `{ key = value }` assignments; sequences of maps use `[[a.b]]`, with full dotted paths for deeper headers. Nested arrays use inline `[...]` where appropriate. Quote special keys. Double-quote/escape strings; use triple quotes for multiline when needed. Booleans/numbers/datetimes unquoted. Null maps to empty string where required. Empty sequences use `[]`; every empty map is an inline assignment using two interior spaces, such as `config = {  }` or, inside `[nested]`, `nested_empty = {  }`. Preserve comments. Scalar root passes through, sequence root fails, aliases explode. End LF.

Normative layout examples distinguish YAML styles. The block-style root mapping `title: app\ndatabase: {host: localhost, port: 5432}\nconfig: {}\n`, whose `database` value is flow-style, retains that order and emits exactly `title = "app"\ndatabase = { host = "localhost", port = 5432 }\nconfig = {  }\n`, with no blank lines. The flow-root input `{title: app, database: {host: localhost, port: 5432}, products: [{name: A, price: 1.2}, {name: B, price: 2}]}\n` emits exactly `title = "app"\ndatabase = { host = "localhost", port = 5432 }\n[[products]]\nname = "A"\nprice = 1.2\n[[products]]\nname = "B"\nprice = 2\n`, also with no blank lines. Headers and assignments begin in column 1, spaces surround `=`, and inline arrays use comma-space. By contrast, when `database` is a block-style child after the root assignment `title`, one blank line precedes `[database]`.

## Spec 15

HCL decode supports attributes `name = expression`, unlabeled/labeled blocks with arbitrary labels, comments, heredocs, quoted templates/interpolation, lists/tuples/sets, objects, traversal/index/splat, calls, unary/binary arithmetic/logical/comparison and conditionals. Literal/constant expressions become typed/evaluated nodes; expressions requiring unknown variables/functions are preserved as source strings. Repeated blocks never overwrite. Preserve attribute-vs-block distinction, labels, order, comments/blank lines, escapes/Unicode, booleans/null, exact large integers and floats. A decoded HCL quoted string retains double-quoted style when emitted as YAML at any nesting depth or inside an array: for example, `value = "deep"` becomes `value: "deep"`, and `strings = ["a", "b"]` emits double-quoted `"a"` and `"b"`. Evaluated HCL object expressions retain flow style, so `config = { bucket = "test", project = "test" }` emits `config: {bucket: "test", project: "test"}`. HCL's unified number type becomes an integer node whenever its evaluated value is integral: `scientific = 1.5e10` emits `scientific: 15000000000`, while `fractional = 3.14159` remains a float. A decoded HCL null used as a YAML mapping value retains empty null style, so `missing = null` emits `missing:` rather than `missing: null`.

Malformed assignments/strings/collections/blocks fail. An HCL quoted string split by LF reports a reason containing, in order, `Invalid multi-line string` and `Quoted strings may not be split`. An unclosed block reports `Unclosed configuration block` followed by `There is no closing brace for this block before the end of the file.` An unclosed object expression `config = {\n  name = "test"\n` instead fails exactly `Error: hcl parse error: input.hcl:3,1-1: Missing expression; Expected the start of an expression, but found the end of the file.\n`. An unclosed `items = [1, 2` reports exactly `Error: hcl parse error: input.hcl:1,9-10: Unterminated tuple constructor expression; There is no corresponding closing bracket before the end of the file. This may be caused by incorrect bracket nesting elsewhere in this file.\n`. A block header without `{` reports `Invalid block definition`. These HCL parse errors begin `Error: hcl parse error:`.

Encode root maps as HCL. Scalar/sequence values use `key = value`; nonempty ordinary map values use `key { ... }`; an empty map is an attribute assignment `key = {}` on one line. Decoded label metadata regenerates labels. In addition, ordinary YAML maps under the conventional top-level keys `variable` and `resource` infer labels from successive sole nested keys: `variable -> region` emits `variable "region" {`, and `resource -> aws_instance -> app` emits `resource "aws_instance" "app" {`. Inference stops where a level branches. Thus `resource` containing sole key `aws_instance`, whose value has sibling keys `empty: {}` and `populated: {name: "test"}`, begins `resource "aws_instance" {`, then emits `empty = {}` and a `populated { ... }` block; it does not infer `empty` as another label. Maps below the inferred labels remain ordinary nested blocks. Two-space indent, inline primitive lists, nested braces. Preserve YAML string quoting style where representable: a double-quoted YAML `"string"` stays quoted and escaped, while a plain YAML `string` emits the bare HCL token `string`. Null/booleans/numbers are unquoted; comments retained. Sequence root fails; aliases explode.

Thus `{config: {name: test, count: 2, flags: [true,false], nested: {x: 1}}}` encodes exactly in the shape `config {`, two-space-indented `name = test`, `count = 2`, `flags = [true, false]`, nested `nested { ... }`, and a closing brace on its own line. A labeled hierarchy such as `resource -> aws_instance -> web` encodes as `resource "aws_instance" "web" { ... }` either from decoded block-label metadata or from the conventional YAML hierarchy just described.

## Spec 16

Lua decode supports chunks returning a value or global assignments: `nil`, booleans, integers/floats/infinities/NaN, quoted/long strings and escapes, sequence/keyed/mixed/nested/empty tables, numeric/string keys, comments, identifier/bracket keys. Consecutive integer keys from 1 become sequence; otherwise map with key types retained. Without return, collect globals. Returned nil is an empty-style null and therefore emits one bare LF in YAML. A returned function becomes a scalar carrying tag `tag:lua.org,2006,function` and a nonempty runtime representation beginning `function: 0x`. Syntax/runtime errors fail. In particular, `return }\n` fails exactly `Error: bad file '-': @input line:1(column:8) near '}':   syntax error\n\n`; `return pcall(42)\n` fails with `Error: bad file '-': @input:1: attempt to call a non-function object\n` followed by a stack traceback.

Default encoding is structurally:

```lua
return {
	["key"] = "value";
	["array"] = {
		1,
		true,
		nil,
	};
};
```

Use tabs, commas after sequence elements, semicolons after mapping members, `nil`, lowercase booleans, and faithful numbers (`math.huge`, `-math.huge`, NaN form). Every empty mapping or sequence is the inline token `{}`; for example, nested `empty: {}` emits `["empty"] = {};`. Multiline literal-block strings use a long-bracket form beginning `[[` on the assignment line, place the content on following lines, and end with `]];`; a block containing `function test()\n  print("Hello")\n  return true\nend\n` preserves those lines exactly. Other strings preserve useful YAML quote style: double-quoted input uses an escaped double-quoted Lua literal, while single-quoted YAML values such as `He said "hello"` and `C:\path\to\file` emit respectively `'He said \"hello\"'` and `'C:\\path\\to\\file'`. Sequence elements omit keys. Map keys bracket-quote by default, including numeric-looking, keyword, empty/special keys. `--lua-unquoted` allows valid non-keyword identifiers. `--lua-prefix`/`--lua-suffix` replace `return ` / `;\n`. `--lua-globals` requires map root and writes top-level assignments. Preserve comments/Unicode and support large/deep tables.

## Spec 17

`-o=base64` and `@base64` encode scalar bytes with alphabet `A-Z a-z 0-9 + /` and `=` padding; empty string -> empty. Ordinary scalar strings contribute their UTF-8 bytes. Bytes produced by `@base64d` are retained even when they are not valid UTF-8: decoding and re-encoding the Base64 representation of bytes `0x00` through `0xFF` reproduces it byte-for-byte. Non-string operator input fails. Decoder operators accept valid unpadded data by adding the minimum `=` padding. Invalid data fails with Go Base64's exact byte offset: `"abc!" | @base64d` reports `Error: illegal base64 data at input byte 3`, and `"invalid!@#$%" | @base64d` reports `Error: illegal base64 data at input byte 7`.

URI encoding uses form/query escaping: ASCII letters/digits and `- . _ ~` remain literal, a space becomes `+`, and other bytes (including `&`, `(`, `)`, `*`, `=`, and an existing `%`) are uppercase percent-encoded. Thus `this has & special () characters *` becomes `this+has+%26+special+%28%29+characters+%2A`, and `search=test value` becomes `search%3Dtest+value`. A non-string operator input fails with a tag-specific conversion hint; for a mapping the diagnostic is exactly `Error: cannot encode !!map as URI, can only operate on strings. Please first pipe through another encoding operator to convert the value to a string\n`. Raw output formats do not add a terminator: `-o base64 .` on `"hello world"` emits exactly `aGVsbG8gd29ybGQ=`, and `-o uri .` emits exactly `hello+world`. Operator results still use their surrounding encoder's normal terminator.

Decoder shorthands are `@base64d`, `@urid`, `@jsond`, `@yamld`, `@xmld`, `@csvd`, `@tsvd`, and `@propsd`. They require a scalar string and return its decoded value. URI decoding treats both `%20` and `+` as a space and rejects malformed percent escapes. Named aliases `from_yaml` and the corresponding `from_FORMAT` forms have the same decoding role. `@json` always returns compact JSON such as `{"cool":"thing","nested":{"value":42}}`; when assigned as a one-line YAML scalar, that JSON text uses single quotes. Thus `.b = (.a | @json)` on `a:\n  cool: thing\n  nested:\n    value: 42\n` emits the original `a` mapping followed by exactly `b: '{"cool":"thing","nested":{"value":42}}'\n`. `to_json` returns two-space pretty JSON with internal/trailing LF; `to_json(N)` uses N spaces at every nesting level. `@yaml` returns normal two-space YAML text; `to_yaml(N)` uses N spaces at every nested level. These encoded texts remain scalar strings, so assigning a multiline one to YAML renders it as a literal `|` block.

`@yaml`, `@json`, `@xml`, `@csv`, `@tsv`, `@props`, `@sh` return a string containing the serialization. `@sh` leaves each leading safe ASCII alphanumeric/underscore/hyphen run unquoted, opens a single-quoted segment at the first unsafe character, and represents an embedded apostrophe as `\'` while transitioning quoted segments. Consequently `strings with spaces and a 'quote'` becomes exactly `strings' with spaces and a '\'quote\'`, and `it's ok` becomes exactly `it\'s' ok'`. `$HOME & stuff` becomes `'$HOME & stuff'`.

`-o=shell` recursively flattens to assignments, joining path components/indexes with `_` or `--shell-key-separator`. Normalise names by Unicode decomposition to ASCII, punctuation/spaces to `_`, unsupported non-ASCII removed; prefix `_` if empty/starting digit. A value consisting only of shell-safe alphanumerics/underscore is unquoted. Other string values, including a hyphenated value such as `starts-with-digit`, are surrounded in single quotes; an embedded apostrophe closes that quote, emits the exact three-character double-quoted segment `"'"`, and reopens it. Thus `{123: starts-with-digit}` emits `_123='starts-with-digit'`, and `{key: "val'ue"}` emits exactly `key='val'"'"'ue'`. Scalar root key is `value`. Other examples: `{person:{name: John}}` -> `person_name=John`; `{items:[a,b]}` -> `items_0=a` then `items_1=b`.

## Spec 18

YAML scalar results unwrap by default (`-r=true`): string content only, no quotes/tag/colour/comments. `-r=false` serializes YAML spelling. Collections use encoder. JSON strings remain quoted unless `-r`. Properties records must not be accidentally unwrapped.

`-0/--nul-output` uses one NUL as the result separator instead of the encoder's ordinary final LF. It does not strip an LF or CRLF that is part of an unwrapped scalar's value; all such scalar-content newlines are preserved before the NUL. Consequently `-0 -r .a` on `a: |\n  one\n  two\n` writes the exact bytes `one\ntwo\n\x00`. Compose with JSON, multidoc, `-r`, `-N`; unwrapped scalar containing NUL fails. `-I` accepts zero/positive levels. `-N` affects markers only.

Colour defaults off for non-TTY. `-C` forces on and `-M` forces off when used alone. When both flags occur, `-C` takes precedence regardless of their order: both `-C -M` and `-M -C` produce coloured output. `NO_COLOR` disables unless a later explicit force wins. Cyan `\x1b[36m` surrounds mapping, JSON, TOML, and HCL keys or block names; green `\x1b[32m` surrounds strings; high-magenta `\x1b[95m` surrounds numbers, booleans, and null; high-black `\x1b[90m` surrounds comments; bold yellow `\x1b[33;1m` surrounds TOML headers. Reset each coloured token with `\x1b[0m`; punctuation, whitespace, quotes, braces, and line endings remain outside the colour sequences. HCL applies these same classes automatically on a TTY. `-v` logs diagnostics to stderr without altering data. For expression `.name`, its parser trace contains both `Parsing expression: [.name]` and `PathToken name`; the verbose stream also includes the surrounding argument detection, token/postfix, traversal, and encoding debug records.

## Spec 19

Front matter `-f/--front-matter extract|process` accepts either an opening `---\n` followed by one YAML document and a closing `---\n`, or a YAML document starting at byte zero followed by its first `---\n` delimiter; arbitrary appendix follows the delimiter. `extract` prints only evaluated YAML and discards appendix. It retains a leading `---\n` exactly when the input had the opening marker: marked input beginning `---\ntitle: My Document\nauthor: Alice\n---\n` extracts as `---\ntitle: My Document\nauthor: Alice\n`, while unmarked `a: apple\nb: cat\n---\nnot yaml\n` updated with `.b = "dog"` extracts as `a: apple\nb: dog\n`. In-place extract replaces the file with the same marker rule and no closing appendix marker. `process` prints evaluated YAML, closing marker, appendix byte-for-byte. Support nested changes/comments/Unicode/empty appendix. Front matter also reads stdin when no path is named: `-f extract .` on stdin `a: 1\n---\nbody\n` succeeds with empty stderr and emits exactly `a: 1\n`.

Otherwise retain leading comment blocks, explicit leading separators/directives, comments between maps/documents, trailing comments. Identity/pretty-print do not discard them. Root `foot_comment` assignment appends after existing trailing comment content rather than replacing it: `. foot_comment = "tail"` on `a: 1\n# old\n` emits exactly `a: 1\n# old\n# tail\n`.

## Spec 20

`-i/--inplace` sends no stdout and atomically writes all encoded results to the first named path. Additional files' results append as documents to first; other files unchanged. Preserve chosen/detected format, all YAML docs, LF, comments, and symlink identity (update the target without replacing the link); writable-by-replacement read-only files succeed. A nonexistent input, including one whose parent is absent, fails exactly `Error: stat PATH: no such file or directory\n`. A directory input fails exactly `Error: read PATH: is a directory\n`.

`-s/--split-exp NAME_EXPR` writes each main result to a filename from evaluating NAME_EXPR in that result context. String and numeric scalar results are accepted and converted to their textual spelling; in particular, numeric `$index` creates `0.yml`, `1.yml`, and so on under both `eval` and `eval-all`. A literal numeric naming expression works too: `-s 1 '.[]'` on `[a]\n` succeeds silently and creates `1.yml` containing `a\n`. Append the selected output format's default extension only when the computed filename has no extension: with YAML output, names `doc1` and `doc2` create `doc1.yml` and `doc2.yml`, but computed names `test_doc1.txt`, `a/b/c/alice.yaml`, and `item-0.yaml` are used exactly and do not acquire another suffix. Create parents, so `a/b/c/alice.yaml` creates all missing directories. `--split-exp-file` loads the naming expression and uses the same extension rule. `$index` is zero-based increasing. No extra separators per result file. A missing split-expression file `/nonexistent.yq` fails exactly `Error: open /nonexistent.yq: no such file or directory`. A split expression `..bad` fails exactly `Error: bad split document expression: 1:3: lexer: invalid input text "bad"`. A naming expression whose bytes are `bad syntax ][\n` fails exactly `Error: bad split document expression: 1:1: lexer: invalid input text "bad syntax ][\\n"\n`. Other invalid/missing expressions fail likewise. Split and inplace conflict.

## Spec 21

Parse jq-like expressions with whitespace/`#` comments: `.`, literals, parentheses, `[e]`, ordered object literals with double-quoted or computed keys (`{"key":e}` and `{($k):$v}`), paths, functions, unary `-`/`not`, binary operations, assignment/update assignment, comma union, pipe. Bare object keys are not accepted: `-n '{a: 1}'` fails exactly `Error: 1:2: lexer: invalid input text "a: 1}"\n`, whereas `-n '{"a": 1}'` succeeds and emits `a: 1\n`. Double strings support `\n \t \r \f \v \b \a \" \\` and `\(expression)`; `--string-interpolation=false` leaves interpolation literal. This Boolean flag also accepts the one-letter false value: `--string-interpolation=f -n '"Mike \(3 + 4)"'` succeeds and emits the literal `Mike \(3 + 4)\n`.

Expressions transform streams. `A | B` applies B to each A result; `A, B` concatenates; `[A]` collects; object values evaluate in original context. Literals include null, booleans, Unicode strings, decimal/hex/octal numbers, arrays/maps. Precedence: unary, multiplicative, additive, comparisons, `and`, `or`, assignment; parentheses override.

## Spec 22

Traversal forms `.name`, `.a.b`, and `.["key"]` address exact ordered map keys, including dot/space/numeric/empty keys. The bracket-key string must use double quotes: `.['a.b']` is rejected at lexing, while `.['key']` and `.['']` are not alternate spellings. For example, expression `[.normal, .['a.b'], .["spaced key"], .['']]` fails exactly `Error: 1:13: lexer: invalid input text "'a.b'], .[\"space..."\n`. `[N]` is zero-based; negatives count from the end; out-of-range produces null. `[start:end]`, `[:end]`, `[start:]` are half-open on sequences/Unicode strings, negative bounds count from the end, and bounds are clamped; out-of-range/reversed gives an empty value of the same kind. `[]` iterates sequence elements/map values in order; `.*` map values; `.ba*` glob-matches keys.

Optional `?` suppresses traversal type errors. Invalid string sequence index fails without it. `..` recursively walks the root and descendant values in pre-order without alias loops. `...` is the corresponding recursive-descent form that also emits every mapping key immediately before that key's value; it includes the root and still traverses sequence elements. Missing fields return null; assignments through null create map/sequence and beyond-end indices fill nulls.

`path` returns a root-relative array of string keys/integer indexes; root is `[]`, with one component per node. A value inherited through a YAML merge retains the anchor-definition provenance rather than the merge-site path: for `defaults: &defaults\n  timeout: 30\nservice1:\n  <<: *defaults\n`, `.service1.timeout | path` emits exactly `- defaults\n- timeout\n`. `parent`, `parent(N)` ascend; past root emits nothing. `parents` returns one sequence node containing all ancestors nearest-first; it does not emit the ancestors as separate stream results. Thus `.a.b[1] | [parents | kind]` on `a:\n  b:\n    - x\n    - y\n` emits only `- seq\n`, because the sole `parents` result is itself a sequence. Negative `parent(N)` indexes backward through that sequence: `parent(-1)` is the root, `parent(-2)` is the penultimate ancestor, and so on. If the negative magnitude exceeds the number of ancestors, it returns the original selected node itself. For input `a: {b: {c: 5}}`, `.a.b.c | parents` is the sequence `[{c: 5}, {b: {c: 5}}, {a: {b: {c: 5}}}]`, `parent(-2)` returns `{b: {c: 5}}`, and `parent(-10)` returns `5`.

`setpath(PATH;VALUE)` and `delpaths(PATHS)` use path arrays. Set creates/fills. Delete nonexistent no-op. Multiple deletion paths are applied in their listed order against the already-mutated structure, so sequence indexes can shift: `delpaths([["a",1],["a",3]])` on `a:\n  - zero\n  - one\n  - two\n  - three\n` first removes `one`, then finds index 3 out of range, and emits exactly `a:\n  - zero\n  - two\n  - three\n`. Components must be strings/integers. A scalar `setpath` path is rejected with its tag: `setpath("foo"; "bar")` fails exactly `Error: SETPATH: expected path array, but got !!str instead\n`. `getpath` is not recognized by this executable: even `getpath(1)` fails at lexing with exactly `Error: 1:1: lexer: invalid input text "getpath(1)"\n`, rather than reaching path-array validation. `delpaths` requires a sequence of sequences. A scalar argument fails exactly `Error: DELPATHS: expected a sequence of sequences, but found !!str\n`. A flat argument such as `delpaths(["not", "nested"])` fails exactly `Error: DELPATHS: expected entry [0] to be a sequence, but its a !!str. Note that delpaths takes an array of path arrays, e.g. [["a", "b"]]`. A float component such as `delpaths([["a", 1.5]])` fails exactly `Error: DELPATHS: expected either a !!str or !!int in the path, found !!float instead`.

## Spec 23

`L = R` replaces selected locations and returns updated root; creates paths/updates arrays. `L |= R` evaluates RHS in each selected value context. Arithmetic assignments use matching operation. Pipes sequence updates. `del(...)` deletes fields/elements; `del(.)` emits no document; missing path succeeds; filters can select deletion targets. `with(PATH;EXPR)` scopes/writebacks and returns whole root.

Mapping `+` is shallow ordered merge: retain left positions, overwrite conflicts, append new right keys, replace conflicting nested maps. `*` recursively merges mappings with RHS winning and multiplies numbers otherwise; `*=` per document.

`pick([keys])` on a mapping emits requested keys in list order/nested values; empty -> `{}`; duplicates follow list semantics. On a sequence, numeric entries select indexes in the requested order, duplicates repeat values, and out-of-range indexes are omitted: `[a,b,c] | pick([2,9,0,2])` emits `[c, a, c]`. `omit([keys])` preserves remaining mapping order and all mapping keys removed -> `{}`. On a sequence, numeric entries remove those indexes while retaining the other elements' order; duplicate and out-of-range indexes have no additional effect, so `[a,b,c,d] | omit([3,1,9,1])` emits `[a, c]`, and all removed -> `[]`.

## Spec 24

Only null/false are false for `//`; zero, empty string/sequence/map are truthy. `A // B` chooses A unless false/null/empty-stream; chaining first truthy; `null // null` null. `and`, `or`, `not` emit booleans.

The `==` operator does not structurally compare collections: two sequence operands or two mapping operands compare false even when their nested contents are identical, and `!=` is its inverse. Scalar `==` compares stored scalar text (the RHS also supports `*`/`?` glob matching) rather than normalizing numeric values or requiring equal YAML tags. Consequently identically spelled `!!str 123` and integer `123` compare true, while alternate integer spellings `0o12` and `0x0A` compare false even though both denote ten; `1` and `1.0` likewise compare false. Null equals null. Operators that expressly require recursive matching—sequence subtraction, collection containment, and deduplication—do use deep type-sensitive comparison, with mapping order irrelevant. Ordered comparison is separate: numbers compare numerically, strings case-sensitive lexicographically, timestamps chronologically, and null only equals null. Boolean ordering is not implemented: `false < true` fails exactly `Error: !!bool not yet supported for comparison\n`. Map/sequence ordered comparison fails `maps not yet supported for comparison` / `arrays not yet supported for comparison`; null-number `<`/`>` is false both directions.

`contains(X)`: case-sensitive substring, deep map subset, every-element sequence subset. Map arguments must follow Spec 21's quoted/computed-key literal syntax, so `contains({"a": 1})` works but `contains({a: 1})` is a lexer error. Matching empties/null contain each other. Kind mismatch is not coerced. In particular, object-with-string containment fails exactly `Error: !!str cannot check contained in !!map\n`, array-with-string containment fails exactly `Error: !!str cannot check contained in !!seq`, and string-with-array containment fails exactly `Error: !!seq cannot check contained in !!str`. `has(K)` checks map key or valid sequence index; missing/wrong-kind/scalar/null/out-of-range/string-on-sequence false.

## Spec 25

Numeric `+ - * / %` supports int/float, promotes mixed, retains large signed integers and precedence. `/` permits fraction; an exactly integral integer quotient is emitted as an integer without a decimal suffix (`20 / 2` emits `10`, not `10.0`). Division by positive zero yields the YAML float spelling `+Inf` for a positive numerator and `-Inf` for a negative numerator, not `.inf`. Computed floats use the reference's shortest decimal/scientific rendering: `1.23456789e10 * 2` emits exactly `2.46913578e+10`. `% 0` fails `cannot modulo by 0`. Integer remainder sign follows dividend: `-10%3=-1`, `10%-3=1`, `-10%-3=-1`; float remainder is `x-trunc(x/y)*y` at IEEE precision. Hex/octal format and custom LHS tag remain on integer results; underscores accepted.

`+` concatenates strings (coercing numeric counterpart), sequences, appends scalar to sequence, treats null as identity and null+null null; maps shallow merge. Boolean/incompatible direction fails. String `* int` repeats. Sequence minus sequence removes all deeply equal requested elements. Null-LHS subtraction returns RHS. Map/string/incompatible subtraction fails. String/string `/` exact-splits, absent delimiter gives one-element sequence; a newly created empty split field is rendered as `""`. Other nonnumeric division fails.

Arithmetic type failures use YAML tags and, for structural operands, their simple input paths. The following diagnostics are exact (with the usual final LF):

```text
Error: !!bool cannot be added to !!bool
Error: !!int (b) cannot be added to a !!map (a)
Error: !!seq (b) cannot be added to a !!int (a)
Error: maps not yet supported for subtraction
Error: strings cannot be subtracted
Error: !!str (b) cannot be subtracted from !!seq
Error: !!int cannot be added to !!str
Error: !!bool cannot be divided by !!int
Error: !!null (a) cannot be divided by !!int (b)
Error: !!seq (a) cannot be divided by !!int (b)
Error: !!null (a) cannot modulo by !!int (b)
Error: !!str cannot modulo by !!int
Error: !!seq (a) cannot modulo by !!int (b)
Error: !!map (a) cannot modulo by !!int (b)
```

These correspond respectively to adding Boolean/Boolean, map `a` plus integer `b`, integer `a` plus sequence `b`; subtracting maps (including `-=`), strings, sequence `a` minus string `b`, and integer minus nonnumeric string; dividing Boolean by integer, null `a` by integer `b`, and sequence `a` by integer `b`; and taking modulo with null, string, sequence, or map `a` and integer `b`.

Timestamp plus/minus duration performs temporal arithmetic, retaining timestamp form/tag. Durations accept concatenated units such as `1h30m`, `5h`, minute/second/subsecond units. Invalid fails `unable to parse duration`.

## Spec 26

`length` counts UTF-8 bytes for a string, sequence elements for a sequence, and pairs for a map; unsupported scalar forms fail. Consequently `length` on `"Café ☕ España"` emits `17\n`, not the 13 Unicode-code-point count, and a string containing 10,000 repetitions of `é` emits `20000\n`. `keys` returns map keys in insertion order or `[0,1,...]` for sequence; empty -> `[]`. On a scalar it fails; string input writes exactly `Error: cannot get keys of !!str, keys only works for maps and arrays\n`. There is no `values` operator: `[values]` fails with exactly `Error: 1:2: lexer: invalid input text "values]"\n`. `key` yields node key/index; `is_key` identifies key nodes.

`type` is an alias for retrieving the YAML type tag, so integer, float, string, null, and Boolean return `!!int`, `!!float`, `!!str`, `!!null`, `!!bool`. It is also accepted in tag-assignment syntax: `.string_val type = "!!int"` changes the selected node's queried tag to `!!int`. The parenthesized pipeline spelling from the fixed interface, `(.string_val | type) = "!!int"`, is likewise a valid expression and returns exit status 0 instead of an invalid-path error; on input `string_val: "12"\n` it emits the unchanged bytes `string_val: "12"\n`. `to_number` and alias `tonumber` leave numbers unchanged and parse strings as signed decimal integers, unsigned `0x` hexadecimal or `0o` octal integers, decimal floats, or scientific floats, changing the tag appropriately while retaining the input numeric spelling (`"1.23e5"` -> float value rendered `1.23e5`). A leading minus before the hexadecimal prefix is not accepted: for `"-0x10"`, either alias fails with exactly `Error: cannot convert node value [-0x10] at path  of tag !!str to number\n`. A nonnumeric string fails with an informative message naming its value/path/tag.

`sort` is stable ascending. Cross-kind precedence null < Boolean < number < string; false < true; mixed numbers numeric; timestamps chronological. `sort_by(EXPR)` supports nested/multiple keys, but an absent selected path is a special missing key ordered after every present key rather than by the ordinary null precedence. Thus sorting `- {a: 2, b: b}\n- {b: z}\n- {a: 1, b: c}\n- {a: 1, b: a}\n` by `.a, .b` emits exactly `- {a: 1, b: a}\n- {a: 1, b: c}\n- {a: 2, b: b}\n- {b: z}\n`. Scalars fail `not an array or map`. `reverse` reverses. `unique` and `unique_by(EXPR)` each deduplicate deeply while retaining the first occurrence and its original position; neither sorts. Thus `[5, 2, 8, 1, 5, 9, 2, 3] | unique` is `[5, 2, 8, 1, 9, 3]`, and `[1, null, 2, null, 3] | unique` is `[1, null, 2, 3]`. `group_by(EXPR)` forms deep-equality groups without sorting: groups occur in the order their key is first encountered, and members retain encounter order. Thus `[1,2,3,4,5,6,7,8] | group_by(. % 2)` yields the odd group `[1,3,5,7]` followed by the even group `[2,4,6,8]`. Missing keys group as null; empty -> `[]`.

`sort_keys(SELECTOR)` and alias `sortKeys(SELECTOR)` alphabetically reorder every selected mapping's keys while retaining values. Selecting `..` recursively sorts mappings inside mappings and sequences. Empty/single-key maps remain valid; applying separately to streamed array maps works.

`flatten` recursively flattens; `flatten(N)` at most N levels. `map(EXPR)` returns transformed sequence/map entries; `filter(PRED)` retains truthy sequence items; `select` streams matching input. `first`, `last`, predicate variants emit matching element or nothing; `min` and `max` use the same ordering and emit nothing for empty input. `min_by` and `max_by` are not recognized; `min, max, min_by(-.), max_by(-.)` fails with exactly `Error: 1:14: lexer: invalid input text "_by(-.), max_by(..."\n`. `any` and `all` aggregate input directly; their predicate forms are spelled `any_c(PRED)` and `all_c(PRED)`. Thus `[any_c(. > 2), all_c(. > 0)]` on `[1,2,3]\n` emits exactly `- true\n- true\n`, while jq-like `[any(. > 2), all(. > 0)]` fails with exactly `Error: bad expression, please check expression syntax\n`. `shuffle` preserves exact multiset/length. Support empty/single/large/mixed/deep arrays.

`pivot` transposes sequence rows, padding missing cells with empty-style null nodes. In YAML those cells are bare sequence dashes, not `- null`; `[[1,2],[3,4,5],[6]] | pivot` emits exactly:

```yaml
- - 1
  - 3
  - 6
- - 2
  - 4
  -
- -
  - 5
  -
```

Sequence of maps becomes map key -> sequence of row values; single row works.

## Spec 27

`to_entries`: ordered map -> sequence `{key,value}`; sequence -> zero-based integer keys; null -> an empty result stream. In particular, `to_entries` on `null` exits 0 with empty stdout and stderr; it does not emit `[]`. A nonnull scalar fails, and string input fails exactly with `Error: !!str has no keys\n`. `from_entries` requires a sequence and fails on a mapping with exactly `Error: from entries only runs against arrays\n`. Each entry must contain a `key` and a `value`; a missing field at zero-based position `N` fails with `Error: expected to find one 'key' entry but found 0 in position N\n` or the corresponding exact `'value'` message. Valid entries reconstruct the mapping. `with_entries(EXPR)` is to_entries/map/from_entries and may transform/filter. `map_values` updates values retaining keys; empty maps remain empty.

Array construction/`collect` collects streams. `ireduce` syntax `GENERATOR as $x ireduce(INIT; UPDATE)`: INIT once, bind each in order, accumulator as `.`, final emitted even for empty. Supports sums/products, strings/sequences, map updates, filtering, multi-field state.

## Spec 28

String transformations, splitting, and regex matching/replacement preserve valid Unicode text; this does not alter the UTF-8 byte-count rule for `length` in Spec 26. For example, replacing 3,000 ASCII `a` characters with `é` using `sub("a"; "é")` and then applying `length` emits `6000\n`. `upcase`/`downcase` use Unicode case mapping; `trim` removes outer Unicode whitespace. `split(DELIM)` exact-splits, retains interior empties, handles Unicode/newline/tab/multichar, maps empty-string input to `[]`, maps an empty delimiter to individual Unicode characters, and emits no result for null input. Other non-string input fails, including `cannot split !!int, can only split strings` for an integer. `join(SEP)` text-converts numbers/booleans and null to the empty field; an empty array becomes an empty string. `tostring` leaves string text unchanged, renders scalars in YAML spelling (`123`, `true`, `null`), and serializes collections as YAML text using their retained style rather than forcing JSON object syntax. On block-map input `a: 1\n`, `tostring` produces exact CLI stdout `a: 1\n`; on flow-sequence input `[1,2,3]\n`, it produces `[1, 2, 3]\n`. Interpolation uses the same conversion; null appears `null`. Escaped `\(` remains literal.

Regex is leftmost-first Unicode RE2-style: classes, quantifiers, numbered and `(?<name>...)` groups. `test` Boolean. `sub` accepts both `sub(RE;REP)` and comma-separated `sub(RE, REP)`; it replaces all non-overlapping matches and expands `$1` etc. For example, `.a |= sub("dogs", "cats")` changes `a: dogs are great` to `a: cats are great`. `match` emits ordered `{string, offset, length, captures}`; every capture has `{string, offset, length}` and a `name` when named. For `match("h(.*?)o")` on `hello world`, the match is string `hello`, offset 0, length 5, with capture `ell`, offset 1, length 3. `match(RE;"g")` streams all; no match emits nothing. `capture` returns a mapping of named strings; newly constructed numeric-looking capture values are double quoted, so capturing named `major`, `minor`, and `patch` groups from `1.2.3` emits exactly `major: "1"\nminor: "2"\npatch: "3"\n`.

Invalid regular expressions fail with the Go/RE2 parser text used by the executable. In particular, both `sub("["; "x")` and `match("[")` write exactly ``Error: error parsing regexp: missing closing ]: `[`\n``. A non-string `sub` input identifies the tag and includes the update-assignment hint: on integer `123`, `sub("2"; "x")` writes exactly `Error: cannot substitute with !!int, can only substitute strings. Hint: Most often you'll want to use '|=' over '=' for this operation\n`. These failures have non-zero status and no stdout.

## Spec 29

`tag` returns `!!null`, `!!bool`, `!!int`, `!!float`, `!!str`, `!!timestamp`, `!!seq`, `!!map`, `!!binary`, custom. Assignment changes tag retaining node; works all kinds/nested/filtered/recursive; empty RHS no-op. Retagging an integer, Boolean, or null scalar as `!!str` gives it double-quoted YAML style, not single-quoted style: `.integer tag = "!!str"` changes `integer: 42\n` to exactly `integer: "42"\n`, `.boolean tag = "!!str"` changes `boolean: true\n` to exactly `boolean: "true"\n`, and `.val tag = "!!str"` changes `val: null\n` to exactly `val: "null"\n`. `kind` returns `scalar`, `seq`, `map`, `alias`.

`style` returns empty default/block/plain or `single`, `double`, `literal`, `folded`, `flow`, `tagged`. Assignment accepts only these/empty: quotes, `|`, `>`, flow braces/brackets, explicit tag. Unknown fails `unknown style` naming value; empty RHS no-op.

`line`/`column` are one-based original positions. `filename`, `fileIndex`, `documentIndex` are Spec 4. `line_comment`, `head_comment`, `foot_comment` get text without `#`/optional space, preserving newlines. Assignment renders every line `# `; targets root/array/map/multidoc/recursive and supports context `|=`. Missing comment -> empty string; empty selection no output.

The camel-case spellings `lineComment`, `headComment`, and `footComment` are accepted in assignment position. They are not read operators: `.a lineComment`, `.a headComment`, and `. footComment` each fail with exactly `Error: bad expression, please check expression syntax\n`. Root `. footComment = "tail"` has the same appending behavior described for `foot_comment` in Spec 19.

`anchor`/`alias` get/set names and render `&name`/`*name`, on scalars/collections. Unanchored query -> empty. `explode(EXPR)` recursively replaces aliases/merges with independent concrete values respecting overrides.

## Spec 30

`EXPR as $name | REST` lexically binds each result while REST keeps original/current context. Multiple/nested/shadowed variables coexist; work in object literals whose keys follow Spec 21's quoted/computed-key syntax, filters, arrays, and reduce. For example, `.a as $x | {"old": $x, "current": ., "sum": ($x + .b)}` works, whereas the corresponding `{old: ...}` spelling is rejected as specified in Spec 21. Undefined variable emits empty stream. No incorrect cross-document leakage.

`strenv(NAME)` returns exact environment string, including empty. `env(NAME)` requires present nonempty and parses full YAML/JSON-like value, typing numbers/arrays/maps/multiline. Empty env error is exactly `Error: value for env variable 'NAME' not provided in env()`. `--security-disable-env-ops` blocks env/strenv/envsubst mentioning `env operations have been disabled`.

`envsubst` replaces every `${NAME}`; default unset/empty -> empty. `envsubst(nu)` errors `Error: variable ${NAME} not set`; `(ne)` errors `Error: variable ${NAME} set but empty`; combine `(nu, ne)`.

## Spec 31

`load(PATH_EXPR)` evaluates the path and auto-detects structured format. A single-document file returns that document directly. A multi-document YAML file returns one sequence containing the documents rather than streaming them: loading `---\na: 1\n---\na: 2\n` emits exactly `- a: 1\n- a: 2\n`, so `[load(PATH) | .a]` fails because `.a` is applied to that sequence. `load_str`/`strload` returns raw UTF-8 including final/internal newlines. Relative paths use process cwd. Compose/multi-load/null-input are supported. If PATH_EXPR produces a null value, it is not stringified: both `-n 'load(.a)'` and `-n 'strload(.a)'` fail exactly `Error: filename expression returned nil\n`. For either `load("cat.yml")` or `strload("cat.yml")` when that literal relative path is absent, stderr is exactly `Error: failed to load cat.yml: open cat.yml: no such file or directory\n`; substitute the supplied path in both positions for other missing paths. `--security-disable-file-ops` blocks.

`system(COMMAND[;ARGS])` is disabled by default; its error mentions `system operations are disabled` and `--security-enable-system-operator`. Enablement is independent of env/file security. COMMAND must be a nonnull, nonempty string scalar. ARGS null/empty means none, a scalar means one argument, and a sequence supplies nonnull scalar arguments; a map, nested sequence, or null member fails. Its validation diagnostics are exact:

```text
Error: system operator: command must be a string scalar
Error: system operator: command must be a non-empty string
Error: system operator: argument must be a non-null scalar; got kind=4 tag=!!null
Error: system operator: argument must be a non-null scalar; got kind=1 tag=!!seq
Error: system operator: args must be a non-null scalar or sequence of non-null scalars; got kind=2 tag=!!map
```

The first two are produced by null and empty-string commands respectively; the next two by a null or nested-sequence member of ARGS; and the last by a mapping ARGS value. Execute directly through PATH with arguments preserved and no implicit shell. Feed the current scalar's unquoted textual value to the child process on stdin, capture stdout, strip one final LF or CRLF, return the remainder as a string, and invoke once for each input node. A nonzero exit reports `Error: system command 'CMD' failed: exit status N`; if the child wrote stderr, append it on the next line prefixed by `stderr: `. For example, `system("sh"; ["-c", "echo test >&2; exit 1"])` fails with exactly:

```text
Error: system command 'sh' failed: exit status 1
stderr: test
```

With the operator enabled, a missing `nonexistent-command-xyz` fails exactly `Error: system command 'nonexistent-command-xyz' failed: exec: "nonexistent-command-xyz": executable file not found in $PATH\n`.

## Spec 32

`now` is actual current UTC whole-second `YYYY-MM-DDTHH:MM:SSZ`, timestamp tag. `from_unix` accepts int/float seconds (fraction truncated) -> UTC RFC3339; other tags fail `from_unix only works on numbers, found TAG instead`. `to_unix` accepts RFC3339/date -> integer epoch; second-precision roundtrip.

`format_datetime(LAYOUT)` accepts RFC3339 or `YYYY-MM-DD` and uses reference tokens: `2006` year, `01` month, `02` day, `15` 24h, `3` 12h, `04` minute, `05` second, `PM`, `Monday`, `Jan`, `06` short year, `MST` zone. Invalid fails with `could not parse datetime`/`cannot parse`. Timestamp comparison/duration use earlier specs. `tz("Invalid/Timezone")` fails including `could not load tz [Invalid/Timezone]: unknown time zone Invalid/Timezone`.

## Spec 33

`split_doc` does not iterate a sequence. It marks each value already present in its input stream as a separate document, assigning document indexes from zero; use `.[] | split_doc` to split sequence elements. It preserves scalars, mappings, sequences (including `[]`), and null. In particular, `-n 'split_doc'` succeeds and emits exactly one LF for its synthetic null input. `eval(STRING)` parses/evaluates dynamically in current context, allowing paths, updates, array-derived and environment-derived expressions. Evaluating the invalid string `.invalid syntax [[` fails exactly `Error: 1:10: lexer: invalid input text "syntax [["\n`.

`error(MESSAGE)` aborts nonzero with no contextual wrapper: `error("custom error message")` writes exactly `Error: custom error message\n` to stderr. No argument also fails. It supports input/env-built validation text.

The named `encode(FORMAT)` and `decode(FORMAT)` functions are not part of this executable's expression grammar. In particular, `encode("json") | decode("json")` fails exactly `Error: 1:1: lexer: invalid input text "encode(\"json\") |..."\n` and emits no stdout. The `@yaml`, `@json`, `@xml`, `@props`, `@csv`, `@tsv`, `@base64`, `@uri`, and `@sh` shorthand encoders, with the decoder shorthands listed in Spec 17, provide the supported encoding interface. Encoded output is a scalar string and a decoder shorthand parses it. A structure decoded from a JSON string retains JSON flow style and double-quoted keys/strings when subsequently emitted as YAML: decoding `{"cool": "thing", "count": 42, "active": true}` emits exactly that same flow-form line plus LF, rather than block YAML. JSON compact/pretty/custom indent, YAML indent, and deep/special values work through those shorthands. One-line `@xml` text includes an internal trailing LF; when its unwrapped scalar result is printed, the outer result terminator produces a second LF. Thus `-n '{"cool": {"+@id": "hi", "foo": "bar", "nested": {"value": 42}}} | @xml'` emits exactly `<cool id="hi"><foo>bar</foo><nested><value>42</value></nested></cool>\n\n`.

Invalid/incomplete JSON/Base64 fails with no partial structure. `@jsond` uses the YAML-compatible decoder diagnostic: applying it to the string `{"incomplete": ` writes exactly `Error: yaml: while parsing a flow node at line 1: did not find expected node content\n`. The exact Base64 errors are specified in Spec 17.

## Spec 34

`--debug-node-info` replaces serialization with YAML node descriptions. Root string `hello`:

```yaml
kind: ScalarNode
tag: '!!str'
value: hello
line: 1
column: 1
```

Kind names: `ScalarNode`, `SequenceNode`, `MappingNode`, `AliasNode`. Omit absent/default fields. Include optional `style: FlowStyle|SingleQuotedStyle|DoubleQuotedStyle|LiteralStyle|FoldedStyle`, `anchor`, `headComment`, `lineComment`, `footComment`, quoted `tag`, scalar `value`, one-based `line`/`column`, `content`. Sequence content lists children; mapping alternates key/value descriptions in insertion order; alias value is anchor name. Indent content children four spaces relative. Numeric/bool/null values are diagnostic YAML strings (`"42"`, `"true"`, `"null"`); safe strings plain; multiline uses `|`. Blank line after each result. Accurate through selections, iteration, multidoc/frontmatter, anchors/merges, comments, Unicode, numeric keys, scientific notation, long lines.

## Spec 35

Support sequences/maps of 100–500 records, strings of 10,000 code points, 3,000 regex replacements, 50–100 keys, nesting 5+, signed 64-bit-scale integers, extreme scientific floats, multiple sources/documents. No toy limits, ordering randomness, truncation, UTF-8 corruption. Only `shuffle` nondeterministic and multiset-preserving.

Cross-format conversion preserves the ordered abstract tree and scalar types unless a destination-specific loss is stated above. Conversion back to the same metadata-capable format retains comments, styles, anchors, labels, and order. Unsupported shapes return a deterministic diagnostic. Every size enumerated in the preceding paragraph must finish well under ten seconds.

## Spec 36

Some CLI text is fixed. The normative archive below contains UTF-8 `main-help.txt`, `completion/bash.txt`, `zsh.txt`, `fish.txt`, `powershell.txt`, `help.txt`, and completion argument-error outputs. It is a gzip-compressed POSIX tar encoded standard Base64. Implementations may embed decoded bytes. `main-help.txt` is root `--help`; completion files are corresponding stdout; error files are combined stdout+stderr (whole text may be stderr). Except semantic-version allowance in Spec 1, assets are byte-exact.

```base64
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
Patn9cDzP2/CFLAAQAEA
```
