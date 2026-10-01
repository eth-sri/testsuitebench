## Spec 1

The required artifact is one executable file named exactly `executable`. It is a command-line JSON document validator. It reads one JSON Schema from a file named by the sole positional argument and optionally reads zero or more JSON instance files named by repeated options. It must not read or validate standard input; when no instance option is present, it validates the schema itself and ignores any bytes supplied on standard input.

All input is UTF-8 JSON. The complete file must contain exactly one JSON value; empty input, truncated input, invalid syntax, or non-whitespace trailing characters is an error. Support every JSON value kind: object, array, string, arbitrary-precision number, boolean, and null. Preserve number precision sufficiently to compare and print integers well beyond 64-bit range and decimal `multipleOf` cases such as `0.1`, `0.01`, `0.0000001`, and large scientific-notation values. Handle Unicode file names, spaces in paths, Unicode object keys and strings, 100 KB strings, large arrays/maps, and ordinary nesting. Reject excessive nesting with a controlled parse error rather than crashing or hanging. In particular, serializing 200 nested `{"nested": value}` objects with the ordinary space after each colon produces exactly `Error: recursion limit exceeded at line 1 column 1398\n`.

## Spec 2

The command-line syntax is:

`executable [OPTIONS] [SCHEMA]`

`SCHEMA` is required for normal operation and at most one positional value is accepted, although its displayed synopsis uses square brackets. Options may precede or follow it. `--` ends option parsing, so the next token becomes the schema name even if it begins with `-`. Supported options are:

- `-i, --instance <INSTANCES>`: instance file; repeatable and processed in occurrence order. The help must say it “may be specified multiple times”.
- `-d, --draft <DRAFT>`: one of `4`, `6`, `7`, `2019`, `2020`; accept separated and equals forms and compact short form such as `-d2020`.
- `--assert-format` and `--no-assert-format`: enable/disable known format assertions. Repetition is accepted and the last occurrence wins.
- `--output <OUTPUT>`: one of `text`, `flag`, `list`, `hierarchical`; default `text`; accept separated and equals forms.
- `--errors-only`: omit successful results.
- `--connect-timeout <SECONDS>` and `--timeout <SECONDS>`: finite, non-negative decimal seconds, including zero and fractions.
- `-k, --insecure`: disable TLS certificate verification for HTTPS retrieval.
- `--cacert <FILE>`: add a PEM CA certificate read from this file.
- `-v, --version` and `-h, --help`.

Except for repeatable `--instance` and the two format toggles, repeating a value option (for example `--timeout 1 --timeout 2` or two `--output` options) is an argument error containing `cannot be used multiple times`.

## Spec 3

`--help` and `-h` print help to stdout and succeed. Its exact first line is `Usage: executable [OPTIONS] [SCHEMA]`. It contains `Arguments:` and `Options:` sections; describes `[SCHEMA]` as `The JSON Schema to validate with`; contains each option spelling listed in Spec 2; describes output as `Select output style`; shows `[default: text]`; and lists possible values in the orders `4, 6, 7, 2019, 2020` and `text, flag, list, hierarchical`.

Help is an immediate action when encountered: `--help --unknown` succeeds with help, while `--unknown --help` fails on the unknown option. After `--`, `--help` is a schema filename and therefore produces a runtime file error. `--version` and `-v` succeed without a schema and write exactly `Version: 0.41.0\n` to stdout.

## Spec 4

Use these status codes and streams:

- `0`: help/version, valid schema-only operation, or every supplied instance is valid.
- `1`: any invalid schema, invalid instance, JSON/file/reference/network/certificate runtime error, or at least one invalid instance.
- `2`: command-line syntax/value error.

Argument errors are clap-style diagnostics on stderr with empty stdout. They begin `error:` and end with a blank line followed by `For more information, try '--help'.`. No arguments must mention `the following required arguments were not provided` and `<SCHEMA>`. Unknown and extra arguments say `unexpected argument '<token>' found`. Missing option values use `a value is required for '--option <PLACEHOLDER>'`. Invalid draft/output values say `invalid value`, and enumerate possible values. A spaced negative timeout, such as `--timeout -1`, is treated as a flag-like unexpected argument; equals form is parsed as its value. Invalid numeric text says `'<value>' is not a valid number`; negative, `NaN`, and infinity say `must be a non-negative finite number`.

Runtime diagnostics are written to stdout, with stderr empty, and begin `Error: `. File errors include `No such file or directory (os error 2)`. JSON parser errors preserve useful line/column wording, including `EOF while parsing a value at line 1 column 0`, `key must be a string at line 1 column 2`, and `trailing characters at line 1 column 20` for the corresponding inputs. In particular, schema text `{"type": "string"` produces exactly `Error: EOF while parsing an object at line 1 column 17\n`; malformed identifier text `tx`, whether used as the schema or an instance, produces exactly `Error: expected ident at line 1 column 2\n`. A nonexistent `--instance` or `--cacert` is a runtime status-1 error, not an argument error.

## Spec 5

Default/explicit `text` output is newline-terminated. With no instances, a valid schema produces exactly:

`Schema is valid`

An invalid but parseable schema produces one line of the form `Schema is invalid. Error: <first schema compilation or reference error>`. A valid instance produces exactly `<instance-argument> - VALID`. An invalid instance produces:

```
<instance-argument> - INVALID. Errors:
1. <message>
2. <message>
```

There is normally one numbered line for every independently reported validation error, starting at 1. Collect failures across properties, required names, array positions and recursive levels. Composition and optimized applicators have the explicit aggregation exceptions in Specs 14, 16, 20, and 21: in particular, text output for an `anyOf` or zero-match `oneOf` failure reports only its aggregate composition message, not the failed branches' leaf messages. Multiple instances are fully processed and their reports are concatenated in option order. Preserve the instance path spelling supplied by the caller. `--errors-only` suppresses every valid instance report and is completely silent when all instances pass; in schema-only mode it likewise suppresses `Schema is valid` but still displays an invalid-schema error. It does not change the final status.

JSON values embedded in messages use compact JSON with lowercase booleans/null and no spaces. Important message templates are: `<value> is not of type "<type>"`; `<value> is not of types "a", "b"`; `"name" is a required property`; `<value> is less than the minimum of N`; `greater than the maximum of`; `less than or equal to the minimum of`; `greater than or equal to the maximum of`; `<value> is not a multiple of N`; `"s" is shorter than N character(s)`; `is longer than`; `does not match "<translated-pattern>"`; `has less/more than N item(s)`; `has less/more than N propert(y|ies)`; `has non-unique elements`; `Additional properties are not allowed ('a', 'b' were unexpected)`; `Additional items are not allowed (<values> were unexpected)`; and `False schema does not allow <value>`. Sort grouped unexpected property names lexically and use `was unexpected` for one versus `were unexpected` for many.

## Spec 6

The non-text modes write compact UTF-8 newline-delimited JSON: exactly one object and newline for schema-only validation, or one object per instance in supplied order after the schema compiles. A parseable but meta-invalid root schema is handled before instance processing and instead emits exactly one schema-only record, even when instances were supplied; that record omits `instance`. Suppressed successes produce no record. Every record has top-level members in this serialization order: optional `instance`, `output`, `payload`, `schema`. `schema` and `instance` are the exact path strings passed on the command line. `output` is the selected mode.

For `flag`, `payload` is exactly `{"valid":true}` or `{"valid":false}` and never has details. This applies to instance and schema validity, including a schema that cannot compile but was valid JSON. Thus an invalid-instance record has the shape `{"instance":"...","output":"flag","payload":{"valid":false},"schema":"..."}`.

For `list`, `payload` has Boolean `valid` and a `details` array containing the emitted evaluation nodes in pre-order, flattened so that no node in the array has its own `details`. It is not necessarily a node for every schema keyword: optimized validators omit some keyword and property leaves. For example, validating `{"a/b~c":"bad"}` against `{"type":"object","required":["x","y"],"properties":{"a/b~c":{"type":"integer"}}}` emits exactly the root, `/type`, and failing `/properties` nodes; it emits neither `/required` nor `/properties/a~1b~0c/type`. For `hierarchical`, `payload` itself is the root evaluation node and emitted child evaluations are recursively placed in `details`. A valid structured result still has its appropriate trace/details. `--errors-only` filters whole top-level records only, not the detail nodes inside an invalid result.

## Spec 7

Every evaluation node in list/hierarchical output has:

- `valid`: Boolean result for that node.
- `evaluationPath`: an RFC-6901-style JSON Pointer describing the keywords traversed from the submitted root schema; root is `""`.
- `instanceLocation`: a JSON Pointer into the instance; root is `""`, array indexes are zero-based, and property tokens escape `~` as `~0` and `/` as `~1`.
- `schemaLocation`: an absolute `file://` URI (or resolved external URI) for the actual schema resource plus `#` and its schema pointer.

A reported leaf or directly reported keyword failure has `errors`, an object keyed by that keyword (`type`, `required`, `minimum`, `pattern`, `falseSchema`, etc.) whose value is its human message; if one optimized keyword node owns several errors, the value is an ordered array of messages. For example, two missing names, when the `/required` node is emitted, appear as `errors.required:["\"x\" is a required property","\"y\" is a required property"]`. Failing composition container nodes for `anyOf`, `oneOf`, and `allOf` are an exception: they have `valid:false` but no `errors` member, while emitted failing branch leaves carry the errors. Successful annotation-producing nodes have `annotations`. An invalid annotation-producing applicator uses `droppedAnnotations` for results that cannot contribute to unevaluated tracking: for property applicators its value is the array of matched property names, while a specialized all-items type failure may use `true`. A specialized `items:{"type":T}` hierarchical failure is represented as one `/items` node with `droppedAnnotations:true` and `errors.type`: this is a scalar indexed message when exactly one element fails, such as `"\"not a number\" at index 2 is not of type \"number\""`, and an ordered array of those messages when several elements fail. List output includes the root node first, then emitted evaluations in deterministic validation order. Hierarchical output nests emitted keyword containers, property/index subschemas and leaf constraints.

Evaluation paths, when their nodes are emitted, include the complete applicator traversal: `/properties/name/type`, `/items/type`, `/prefixItems/2/type`, `/patternProperties/^x-/minimum`, `/additionalProperties/type`, `/anyOf/1/...`, `/allOf/0/...`, `/then/...`, and every traversed `/$ref`. For external references, evaluationPath describes the traversal while schemaLocation names the referenced resource. Paths must remain complete beyond 20 nesting levels. Hierarchical property annotations use an optimized combined shape when `properties`, `patternProperties`, and `additionalProperties` coexist: there are no separate aggregate `/properties` or `/patternProperties` nodes; their per-property child evaluations are nested under the aggregate `/additionalProperties` node, whose `annotations` lists only the names actually handled by `additionalProperties` in lexical order. For `{"properties":{"b":{},"a":{}},"patternProperties":{"^x":{}},"additionalProperties":{}}` and `{"b":1,"a":2,"x1":3,"z":4}`, that aggregate is `/additionalProperties`, has `annotations:["z"]`, and contains children at `/properties/a`, `/properties/b`, `/patternProperties/^x`, and `/additionalProperties`. A successful `contains` aggregate annotates ascending matching indexes; a non-array `contains` evaluation annotates `[]`.

## Spec 8

Select a schema dialect as follows. An explicit `-d/--draft` always overrides the schema’s `$schema`. Otherwise recognize the `http` or `https` forms (and optional trailing `#` where historically used) of `json-schema.org/draft-04/schema`, `json-schema.org/draft-06/schema`, `json-schema.org/draft-07/schema`, `json-schema.org/draft/2019-09/schema`, and `json-schema.org/draft/2020-12/schema`. Absent a declaration, use Draft 2020-12 behavior. Explicit values `4`, `6`, `7`, `2019`, and `2020` map respectively to those five dialects.

Core differences observable here are:

- Draft 4 uses `id`, boolean-valued `exclusiveMinimum`/`exclusiveMaximum` paired with `minimum`/`maximum`, tuple arrays in `items`, `additionalItems`, and `dependencies`. It ignores later keywords such as `const`, `if`, `propertyNames`, `minContains`, `unevaluatedItems`, and `unevaluatedProperties`. A JSON lexical float such as `42.0` does not satisfy the Draft 4 `integer` instance type. As a compatibility extension, however, Boolean schemas are accepted even under explicit Draft 4: schema-only `-d4` with root `false` prints `Schema is valid` and exits 0.
- Draft 6 adds `const`, numeric exclusive bounds, `propertyNames`, and content assertions. Draft 7 adds `if`/`then`/`else`; zero-fraction numbers such as `1.0` satisfy `integer` in these later drafts.
- Draft 2019-09 supports `dependentRequired`, `dependentSchemas`, `minContains`/`maxContains`, recursive references and unevaluated tracking; it also retains array-form `items`/`additionalItems` behavior used by the tests.
- Draft 2020-12 uses `prefixItems` for tuple positions and `items` for the remaining positions, supports dynamic references and unevaluated tracking, and rejects array-valued `items` as an invalid schema.

Keywords not defined by the selected dialect are generally annotations/no-ops rather than validation failures. Explicit Draft 4 must therefore ignore a modern `$schema` declaration and modern keywords within it. One required compatibility extension is that legacy `dependencies` remains active when the default/modern dialect is selected, as described in Spec 18.

## Spec 9

A schema is either a JSON object or a Boolean in all five selectable dialects, including the Draft 4 compatibility behavior in Spec 8. `{}` and `true` accept every instance; `false` rejects every instance with `False schema does not allow <compact-instance>`. Constraints whose target JSON kind does not match are ignored unless a separate `type` constraint rejects that value.

`type` accepts one type name or an array of names from `null`, `boolean`, `object`, `array`, `number`, `integer`, and `string`. These kinds are distinct: booleans are not numbers; arrays are not objects. `number` accepts integer and decimal representations. `integer` follows the dialect distinction in Spec 8. A type array succeeds if any named type matches.

`enum` succeeds when the instance deeply equals at least one candidate; `const` succeeds on deep equality with its value. Object key order is irrelevant, array order matters, extra object members prevent equality, booleans are distinct from 0/1, and mathematically equal JSON numeric representations compare equal for equality/uniqueness except for the Draft 4 integer type rule. Error prose uses `<expected> was expected` for `const`; enum messages show exactly the first two candidates when more than two exist, join them with `or`, and summarize the remainder as `or N other candidate(s)`. Thus four candidates render the first two plus `or 2 other candidates`, and five render the first two plus `or 3 other candidates`.

## Spec 10

Apply numeric constraints only to numbers and compare without binary floating-point artifacts:

- `minimum` and `maximum` are inclusive.
- Draft 6+ numeric `exclusiveMinimum` and `exclusiveMaximum` are strict.
- In Draft 4, `exclusiveMinimum:true` makes `minimum` strict and `exclusiveMaximum:true` makes `maximum` strict; false leaves it inclusive.
- `multipleOf` requires a strictly positive numeric schema value and succeeds exactly when instance/divisor is integral. Zero and negative instances are handled normally, including negative zero. It must correctly distinguish nonmultiples in high-precision decimal and very-large-integer cases.

Bounds may be negative, fractional, very large, or scientific notation, and contradictory bounds simply reject every number outside their intersection. Numeric keywords ignore strings, objects, arrays, booleans and null. Error output preserves significant input precision, including large integers.

## Spec 11

Apply string constraints only to strings. `minLength` and `maxLength` count Unicode scalar characters, not UTF-8 bytes; composed Unicode and emoji sequences are handled as their constituent code points, with no normalization. Zero limits and equal boundaries are inclusive. `pattern` searches for a match anywhere unless the expression itself is anchored; matching is case-sensitive.

Regex behavior is ECMAScript-compatible and supports ordinary groups, alternation, anchors, quantifiers, positive/negative lookahead, lookbehind, backreferences, Unicode literals, and escaped metacharacters. Translate `\d`/`\D` to ASCII `[0-9]`/`[^0-9]`, and `\w`/`\W` to `[A-Za-z0-9_]`/its negation; `\s`/`\S` use the ECMAScript whitespace set. Make these translations everywhere, including inside bracket classes, and display the translated form in mismatch messages. Translate `\cA` through `\cZ` and lowercase equivalents to control bytes 1 through 26 (`\cI` is tab). Reject incomplete/non-letter `\c`, `\a`, unmatched brackets/parentheses, reversed quantifier ranges, and a trailing backslash at schema-compilation time. An invalid ordinary `pattern` names the JSON pattern in the message ending `<json-pattern> is not a "regex"`; the `patternProperties` diagnostic has the distinct subject rule in Spec 16.

## Spec 12

Known `format` values are assertions only when the last format switch is `--assert-format`; by default and under `--no-assert-format`, even malformed known-format strings pass. Unknown format names always pass. Format applies only to strings. On failure the text is `<json-string> is not a "<format>"` and the structured error key is `format`.

Implement these formats and boundary behavior:

- `email` and `idn-email`: require nonempty local and domain parts separated by `@`; allow normal dots, subdomains and `+`; IDN form allows Unicode.
- `hostname` and `idn-hostname`: valid labels, hyphens only internally, no underscore, maximum label length 63; allow single/numeric labels, Unicode for IDN and punycode.
- `ipv4`: four decimal octets 0–255, rejecting incomplete forms and leading zeros such as `192.168.001.1`; `ipv6`: compressed/full hexadecimal forms and IPv4 suffixes.
- Gregorian `date` (`YYYY-MM-DD`, valid month/day and leap years), `time` (valid hour/minute/second, required `Z` or signed offset, and fractions allowed; leap-second value 60 is accepted only when the local hour/minute and signed offset represent UTC 23:59), and `date-time` (uppercase or lowercase `T` separator and uppercase or lowercase `Z` UTC designator, or a signed offset; fractions are allowed and a space separator is invalid). For example, asserted format accepts `"23:59:60.5Z"`, `"01:29:60.5+01:30"`, and `"2020-01-01T00:00:00z"`, but rejects `"23:59:60.5+01:30"` as a `time`.
- canonical hyphenated `uuid` in either case; absolute `uri` with scheme and no raw spaces; relative/absolute/fragment `uri-reference`; Unicode `iri` and relative `iri-reference`, still rejecting raw spaces.
- `json-pointer`: empty or slash-prefixed tokens with only `~0`/`~1` escapes; `relative-json-pointer`: leading nonnegative integer followed by a pointer suffix or `#`.
- syntactically valid `regex`; ISO-8601 `duration` beginning `P` with at least one component, including week form; and syntactically balanced `uri-template` expressions.

Formats work inside nested schemas and composition and combine normally with length/type constraints.

## Spec 13

For arrays, `minItems`/`maxItems` are inclusive bounds and `uniqueItems:true` requires deep pairwise inequality. Uniqueness handles nested objects/arrays, treats reordered object members as equal, treats `1` and `1.0` as equal, and detects repeated null. These keywords ignore non-arrays.

In Draft 4/6/7, object/Boolean `items` validates every element. Array-valued `items` is positional tuple validation: schema element N applies to instance element N; fewer instance elements are allowed. Uncovered elements are allowed by default, rejected together by `additionalItems:false`, or individually validated by a schema-valued `additionalItems`. In Draft 2019 behavior exercised here, tuple `items` also marks its prefix evaluated. In Draft 2020, `prefixItems` validates corresponding positions and object/Boolean `items` validates every later position; omitted `items` permits extras and `items:false` rejects each extra. Empty arrays satisfy all per-item validators.

Collect all failing positions. Their instance locations use `/0`, `/1`, etc.; evaluation paths distinguish `/items`, `/items/type`, `/prefixItems/N/type`, and `/additionalItems`. Specialized `items:{"type":...}` errors may aggregate under the `/items` node as an array of indexed messages in hierarchical output, while list output also exposes individual `/items/type` leaves where applicable.

## Spec 14

`contains` applies only to arrays and succeeds if enough elements validate against its subschema. Without `minContains`, at least one match is required, even when only `maxContains` is written. In 2019/2020, `minContains` changes the lower bound (zero permits no matches) and `maxContains` sets an inclusive upper bound. Enforce both even when their range is impossible or equal. Draft 4/7 ignore min/max modifiers but still apply their supported `contains` behavior where defined by the selected dialect; specifically Draft 4 ignores both `contains` and modifiers, while Draft 7 enforces at least one match and ignores `minContains`/`maxContains`.

Boolean, composed, `const`, `enum`, pattern, and nested-array schemas work as the contained subschema. A non-array instance passes `contains`. An empty array fails whenever its effective minimum is one; a false contained schema cannot match anything; true matches every element. Every text failure of the `contains` constraint uses exactly `None of <compact-array> are valid under the given schema`, not a count-specific message. This includes an unmet `minContains` despite some matches, an exceeded `maxContains`, equal lower/upper bounds that are missed in either direction, and an impossible range. Hierarchical successful `contains` nodes annotate the complete sorted list of matching indexes.

## Spec 15

In 2019/2020, `unevaluatedItems` applies after other applicators and sees the union of array positions selected by direct `items` and tuple/prefix-item applicators, matches from `contains`, successful `allOf` branches, every successful `anyOf` branch, the uniquely successful `oneOf` branch, the selected conditional branch, and references (including nested chains). A direct tuple/prefix position counts as evaluated even when validation of that position's nested subschema fails; this prevents an outer `unevaluatedItems` error from duplicating a nested failure. `additionalItems` also contributes evaluated positions in Draft 2019. Failed composition alternatives do not contribute. An `items` schema that applies to all items leaves none unevaluated.

`unevaluatedItems:true` permits all remaining positions; false rejects them; a schema validates each remaining value. Track this independently at every nested array and through recursive/mutually recursive references. Report all rejected values in index order as `Unevaluated items are not allowed ('<compact-json>', ... were unexpected)` and expose both the aggregate `unevaluatedItems` error and false-schema/per-value leaves in detailed output. Ignore the keyword in Draft 4/6/7 and on non-arrays.

## Spec 16

Object `properties` maps exact, case-sensitive property names to schemas and validates only names that are present; it does not make them required and extra names pass by default. `patternProperties` applies every regex whose search matches a name. A property that matches both `properties` and one or several patterns must satisfy every applicable schema. Regexes have Spec 11 behavior and invalid regex keys make the schema invalid. Both keywords ignore non-object instances and support Boolean, referenced, nested, and composed child schemas.

`additionalProperties` concerns only names matched by neither `properties` nor any `patternProperties`. Omitted/true permits them, false ordinarily rejects them as one grouped error, and a schema validates each such value and reports its validator's result. There is an optimized exception when no `properties` or `patternProperties` map is declared: `{"additionalProperties":false}` reports exactly one false-schema leaf for the lexically first property and stops. Thus `{"foo":"bar"}` produces `False schema does not allow "bar"`, while `{"foo":"bar","baz":42,"qux":true}` produces only `False schema does not allow 42`. The three mechanisms remain independent at nested object levels. Successful aggregate evaluation annotations use the combined hierarchical shape described in Spec 7.

An invalid `patternProperties` regex has an implementation-specific compilation subject: it renders the child schema value, not the invalid key. Consequently, `{"patternProperties":{"[invalid":{"type":"string"}}}` produces exactly `Schema is invalid. Error: {"type":"string"} is not a "regex"\n`.

## Spec 17

`required` applies only to objects and requires presence, regardless of a member’s value (null counts as present and `default`, `readOnly`, or `writeOnly` never creates it). Empty required arrays do nothing. Missing names produce one error per name, in required-array order, including when every name is absent; special, empty, long and Unicode names are accepted and matching is case-sensitive.

`propertyNames` applies its schema to every object key as a string, supports Boolean, `type`, pattern, length, enum, and combined constraints, reports all invalid names, and ignores non-objects. It composes independently with `properties`, `patternProperties`, `additionalProperties`, and `required`.

`minProperties`/`maxProperties` count object members; `minItems`/`maxItems`, string length limits, and property-count limits accept non-negative mathematically integer-valued numbers such as `3.0` in every selectable draft, including Draft 4, but reject fractional or negative values. Singular/plural error wording follows the limit value (`1 property`, otherwise `properties`; likewise character/item).

## Spec 18

Support old `dependencies` and modern split dependencies. All apply only to objects and trigger only when their key is present:

- The legacy `dependencies` keyword is accepted in all five selectable dialects for compatibility. A value that is an array requires every named sibling property; a schema value validates the whole object.
- In Draft 2019/2020, `dependentRequired` maps triggers to arrays of unique strings and requires each named sibling, while `dependentSchemas` maps triggers to schemas applied to the whole object.

Support multiple simultaneous triggers, transitive dependency chains, self/circular property dependencies, empty dependency maps/arrays, Boolean and referenced dependent schemas, nested dependent schemas, and interaction with properties/required/additionalProperties. A missing trigger imposes nothing. Collect all missing dependencies; messages use the normal `"name" is a required property` form. During unevaluated-property processing, only a triggered and successful dependent schema contributes its evaluated properties.

Schema compilation rejects non-object dependency maps, non-array `dependentRequired` values, duplicate/non-string dependent names, and non-object `dependentSchemas`; legacy `dependencies` values must be either a schema or a string array. The first diagnostic descends to the failing leaf rather than reporting an enclosing meta-schema `anyOf`: a non-array dependent list such as `"age"` yields `"age" is not of type "array"`, and `["age","age","city"]` yields `["age","age","city"] has non-unique elements`.

## Spec 19

Implement `if`/`then`/`else` in Draft 7 and later. Evaluate `if`; if it succeeds, apply only `then` when present, otherwise apply only `else` when present. `if` itself does not make the instance fail. Missing selected branches do nothing. Boolean conditions behave naturally (`if:true` selects then; `if:false` selects else), and conditionals may nest or combine with sibling type/properties/required constraints.

Evaluation output includes an `/if` node showing its own Boolean result and only the selected branch evaluation (`/then/...` or `/else/...`). Errors are the selected branch’s actual leaf errors, such as `/then/properties/price/minimum`, with normal instance paths. Properties/items successfully evaluated by the condition and successful selected branch participate in modern unevaluated tracking.

## Spec 20

Composition semantics are recursive. Text and structured modes deliberately summarize them differently:

- `allOf`: every schema must validate; one or many elements are allowed.
- `anyOf`: at least one must validate; if none validates, list/hierarchical traces include emitted failures from every branch, while text output contains only the aggregate `<value> is not valid under any of the schemas listed in the 'anyOf' keyword` and omits branch leaves. The false `/anyOf` structured container has no `errors` member.
- `oneOf`: exactly one must validate; none produces the analogous no-schema text message, more than one produces `<value> is valid under more than one of the schemas listed in the 'oneOf' keyword`. Text output again contains only that aggregate. The false `/oneOf` structured container has no `errors` member; emitted branch leaves carry errors when no branch matches.
- `not`: succeeds exactly when its child fails. On failure report one `not` error at `/not`, root-relative instance location, formatted `<schema-json> is not allowed for <instance-json>`; do not present the successful child as the validation error.

Allow Boolean children, a single child, duplicate branches, conflicting types, nested combinations, and references in every applicator. Paths include branch indexes and preserve deep nesting. A schema keyword such as `allOf` that must be an array is rejected at schema-compilation time when it has another type.

## Spec 21

In Draft 2019/2020, `unevaluatedProperties` applies after other applicators and tracks the union of property names selected by direct `properties`, `patternProperties`, and `additionalProperties` applicators, plus names contributed by successful `allOf` and `anyOf` branches, the uniquely successful `oneOf` branch, the condition/selected conditional branch, triggered dependent schemas, and references. A name selected by a direct property applicator remains evaluated at its containing object even when the property's nested schema fails. The same bookkeeping propagates through ordinary circular references, `$recursiveRef`, and `$dynamicRef`, so a nested failure is not duplicated as an outer unevaluated-property error. Failed composition alternatives still do not contribute annotations; when `oneOf` has none or multiple matches, its branch properties do not count.

True permits all remaining names and false rejects them. A schema-valued `unevaluatedProperties` is attempted against each remaining value, but if any values fail, text mode reports the failed names together using the same aggregate rejection wording rather than the child schema's leaf messages. For example, `{"properties":{"fixed":{}},"unevaluatedProperties":{"type":"integer"}}` against `{"fixed":0,"a":"x","b":false}` produces only `Unevaluated properties are not allowed ('a', 'b' were unexpected)`. Report names lexically. Tracking must work independently in nested objects, across `$ref` chains, circular/recursive references, `$recursiveRef`, and `$dynamicRef`/`$dynamicAnchor`. Ignore this keyword in Draft 7 and earlier and for non-objects.

## Spec 22

Resolve references during schema compilation and validation. Support local fragments into `$defs` and `definitions`; RFC-6901 JSON Pointer including `~0` and `~1`; named `$anchor`; `$id`-established/rebased identifiers; absolute self-identifier references; recursive local schemas; `$recursiveRef`; and `$dynamicRef` with nearest matching `$dynamicAnchor`. The same target may be reused by multiple properties. Detect cycles without infinite compilation and validate finite recursive instances at every level.

Support references from all schema locations, including properties, items, pattern/additional properties, composition and dependent schemas. A missing local pointer is a status-1 compilation error exactly shaped `Schema is invalid. Error: Pointer '/path' does not exist`. Schema-only mode must traverse and meta-validate referenced schemas too, so an invalid referenced schema makes the root schema invalid.

## Spec 23

Resolve relative external references against the directory/URI of the schema containing that reference, not the current process directory. Support plain relative paths, `file://` URIs, sibling/subdirectory paths, and fragments into one external file. A further retrieval from an already loaded external resource is not supported once the registry is populated. For a root referring to `sub/middle.json`, where middle declares `$id:"nested/base.json"` and `$ref:"../../leaf.json"`, resolution correctly rebases to the root directory's `leaf.json` but compilation fails with `Schema is invalid. Error: Resource '<absolute-leaf-file-URI>' is not present in a registry and retrieving it failed: Retrieving external resources is not supported once the registry is populated`. Canonical file resource identifiers are absolute `file:///...` URIs.

Support HTTP and HTTPS retrieval, applying total timeout, connection timeout, and insecure TLS settings from the CLI. `--cacert` is passed into HTTPS client configuration, but the self-signed localhost server certificate produced by `openssl req -x509 -newkey rsa:2048 -nodes -subj /CN=localhost -addext subjectAltName=DNS:localhost` is not made trusted by supplying that same PEM: retrieval fails with the ordinary `error sending request for url (<uri>)` cause, whereas `--insecure` succeeds. Only file/http/https schemes are recognized. Retrieval and decoding failures are schema compilation errors of this form:

`Schema is invalid. Error: Resource '<uri>' is not present in a registry and retrieving it failed: <cause>`

Causes preserve useful wording such as file OS errors, JSON parse errors, `Unknown scheme ftp`, `error sending request for url (<uri>)`, or `error decoding response body`. Missing CA output is `Error: Failed to read certificate file '<path>': No such file or directory (os error 2)`. Merely supplying malformed PEM does not itself fail a local-only operation: `--cacert bad.pem` with contents `not a certificate` and schema `{}` exits 0 with `Schema is valid\n`. Network failures must honor short timeouts and complete rather than hang.

## Spec 24

Support `contentEncoding` assertions for Draft 6/7 strings. Recognized encodings are strict `base64` (alphabet `A-Z a-z 0-9 + /`), URL-safe `base64url` (replace `+ /` with `- _`), `base32` (alphabet `A-Z 2-7`), `base32hex` (alphabet `0-9 A-V`), and hexadecimal `base16` (`0-9 A-F`, case-insensitive). `=` is padding only where valid for that base encoding. Reject illegal alphabets, bad length/padding, odd hex length, whitespace/newlines, and base64 versus base64url alphabet mixing as appropriate; accept both hex letter cases and valid base32 padding variants. An empty string is valid encoded content. Decoded bytes need not be UTF-8 unless subsequently interpreted as text. The failure message is `<json-string> is not compliant with "<encoding>" content encoding`.

Support `contentMediaType: application/json` by parsing the relevant string bytes as exactly one JSON value; objects, arrays, strings, numbers, booleans, null, Unicode and escapes all count as valid JSON, while empty text, trailing commas, unquoted keys, single quotes, or trailing data fail. Its failure message is `<json-string> is not compliant with "application/json" media type`. When both keywords occur, decode first and parse decoded bytes only if decoding succeeds; if decoding fails, report only the encoding error. Unknown encodings/media types and these keywords on non-strings are ignored. Draft 4 ignores both; Draft 2019/2020 treat them as non-asserting annotations and therefore also do not reject; the tested asserting behavior is Draft 6/7.

## Spec 25

Before validating instances, meta-validate the complete schema for its chosen draft. At minimum enforce these schema shapes recursively: schemas are objects or Booleans; type names are from the fixed set; `properties`, `patternProperties`, dependency maps and definition maps are objects; every schema-valued position contains a schema; `required` and dependency-name lists contain unique strings; composition/prefix/tuple collections have the required array shape; `additionalProperties`, `additionalItems`, `items`, propertyNames, contains and unevaluated keywords have their dialect-appropriate Boolean/object/array form; `format` and regex patterns are strings; numeric bounds are numbers; `multipleOf` is greater than zero; and size/count/minContains/maxContains values are non-negative mathematically integer-valued numbers.

Only the first meta-schema error is printed in text mode, prefixed `Schema is invalid. Error: `. Representative exact errors are `"invalid" is not valid under any of the schemas listed in the 'anyOf' keyword` for `type:"invalid"`, `"invalid_type" is not valid under any of the schemas listed in the 'anyOf' keyword`, `"invalid" is not of types "boolean", "object"`, `"not an object" is not of type "object"`, `"not a number" is not of type "integer"`, `-1 is less than the minimum of 0`, and `0 is less than or equal to the minimum of 0`. For `required`, descend to the offending item or collection: non-string entries produce `<value> is not of type "string"`, a non-array value produces `<value> is not of type "array"`, and duplicate arrays produce `<array> has non-unique elements`. This applies at every position, including `123`, `null`, `true`, and `[]` entries.

In structured modes, a parseable invalid local root schema yields one selected-mode schema-only record with `payload.valid:false` (and details for list/hierarchical); supplied instances are not preserved or processed. Failures that prevent construction of an evaluation, such as malformed JSON or some unresolved/invalid external references, remain plain `Error:`/`Schema is invalid. Error:` text even if a structured mode was requested. The exact external result depends on the invalid target: under `--output flag`, a Draft 7 root whose property references an external object containing `type:"invalid_type_here"` produces exactly `Error: Unexpected type\n`; under `--output hierarchical`, a root referring to an external array `[]` produces exactly `Error: [] is not of types "boolean", "object"\n`.

## Spec 26

Validation is deterministic and, except for the explicit optimized/aggregate cases in Specs 5, 14, 16, 20, and 21, reports independent leaf failures including multiple bad properties, missing required names, bad array elements, and failures reached through references. Preserve instance ordering. Within an object/array validation, use stable schema/property/index traversal so repeated runs produce byte-identical output; required/dependency failures precede ordinary property-value failures at the same object level, array errors are index order, required errors are declaration order, property evaluations are lexical name order, and grouped property names are lexical order. Object values embedded in messages are serialized with their keys in lexical order regardless of input order: for example, input order `foo, bar, baz` renders as `{"bar":123,"baz":true,"foo":"text"}`. The text error messages do not include instance paths, only values and constraints; structured output carries paths.

Use compact JSON rendering in messages and structured records (no insignificant spaces). Escape strings as JSON while retaining UTF-8 characters. Render integral lexical JSON numbers as integers and explicit decimal values with their decimal form when used in messages. Always terminate validation, structured-record, runtime-error, and version output with a newline. Successful operations and validation failures produce no stderr output; only argument parser diagnostics use stderr.

## Spec 27

The following common keyword interactions are required, not merely isolated keyword checks: nested object/array schemas; all object applicators together; tuple/prefix items plus remaining items; size/type/pattern/range constraints together; properties plus required and dependencies; conditionals inside compositions and vice versa; refs inside array/object/composition/dependency positions; Boolean schemas in all applicators; and multiple instances mixing valid and invalid results. Successful evaluation of one keyword does not mask a sibling failure, and irrelevant type-specific keywords do not themselves fail a different JSON type.

Schema annotations such as `$schema`, `$id`, `$anchor`, `$dynamicAnchor`, `title`, `description`, `default`, `readOnly`, and `writeOnly` do not impose instance constraints beyond their explicit reference/dialect roles. The implementation must finish ordinary large and deeply nested tested cases within five seconds and must not crash on recursive schemas, precision extremes, invalid regular expressions, bad references, or malformed input.
