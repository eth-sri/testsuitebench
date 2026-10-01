# Clarified specification: `ethabi-cli`

The deliverable is one executable file named `executable` at the workspace root. It is a command-line Ethereum ABI encoder and decoder compatible with `ethabi-cli` version 18.0.0. It must read only its command-line arguments and ABI files named by those arguments; no network service is involved.

In this document, a “word” is 32 bytes, hexadecimal is case-insensitive on input, and all generated hexadecimal is lowercase and has no `0x` prefix. “Keccak-256” means the original Ethereum Keccak-256 variant (Keccak-f[1600], 1088-bit rate, 512-bit capacity, Keccak padding/domain byte `0x01`), not standardized SHA3-256.

## Spec 1

### Process and stream behavior

The executable must work regardless of its current working directory. A relative ABI path is resolved in the normal process-relative way; an absolute path is also accepted.

Every successful data-producing command writes its result to standard output followed by `\n`, writes nothing to standard error, and exits 0. Multiple decoded values are separated by one newline, with a final newline after the last. A successful operation whose result is empty may write either an empty stream or a single newline; the preferred reference behavior is a single newline.

All command-line parsing failures and operational failures write nothing to standard output, write a diagnostic to standard error ending in `\n`, and exit 1. The executable must not panic, hang, or emit a traceback for bad input. Help and version are successful and go only to standard output.

## Spec 2

### Top-level CLI, help, and version

The command tree is:

```text
executable encode params [--lenient|-l] [-v TYPE VALUE]...
executable encode function [--lenient|-l] ABI-PATH FUNCTION [-p VALUE]...
executable decode params [-t TYPE]... DATA
executable decode function ABI-PATH FUNCTION DATA
executable decode log ABI-PATH EVENT [-l TOPIC]... DATA
executable help [encode|decode|encode params|encode function|decode params|decode function|decode log]
```

`--help` and `-h` at top level must produce exactly the following bytes, including spacing and the final newline:

```text
ethabi-cli 18.0.0
Ethereum ABI coder

USAGE:
    executable <SUBCOMMAND>

FLAGS:
    -h, --help       Prints help information
    -V, --version    Prints version information

SUBCOMMANDS:
    decode    Decode ABI call result
    encode    Encode ABI call
    help      Prints this message or the help of the given subcommand(s)
```

Running with no arguments prints that same help to standard error and exits 1. `help` alone prints the top-level help to standard output and exits 0. `--version` and `-V` print exactly `ethabi-cli 18.0.0\n`. A top-level help or version flag short-circuits later arguments; for example, `--version decode` prints the top-level version.

Every command level supports its own `--help`/`-h` and `--version`/`-V`, except that the literal `help` pseudo-command does not accept `--help`. Nested version output starts with the routed program name and a semantic version: `executable-encode`, `executable-decode`, `executable-encode-params`, `executable-encode-function`, `executable-decode-params`, `executable-decode-function`, or `executable-decode-log` as applicable.

Subcommand help must be clap-v2-style text on standard output and include the following exact usage lines and descriptive terms:

```text
executable encode <SUBCOMMAND>
executable decode <SUBCOMMAND>
executable encode params [FLAGS] [OPTIONS]
executable encode function [FLAGS] [OPTIONS] <abi-path> <function-name-or-signature>
executable decode params [OPTIONS] <data>
executable decode function <abi-path> <function-name-or-signature> <data>
executable decode log [OPTIONS] <abi-path> <event-name-or-signature> <data>
```

The `encode` help description is `Encode ABI call` and lists `function`, `params`, and `help`. The `decode` description is `Decode ABI call result` and lists `function`, `params`, `log`, and `help`. Leaf help respectively includes `Specify types of input params inline`, `Load function from JSON ABI file`, or `Decode event log`, plus `FLAGS:`, `OPTIONS:`, and/or `ARGS:` as indicated by its arguments. It documents `-v`, `-p`, `-t`, `-l`, `<abi-path>`, `<function-name-or-signature>`, `<event-name-or-signature>`, and `<data>` where relevant. The first line of nested help includes the routed hyphenated name such as `executable-encode`.

In `encode params --help`, the `-v` option's two value metavariables are both spelled exactly `type-or-param`; its option synopsis is `-v <type-or-param> <type-or-param>`.

## Spec 3

### Command-line parsing rules

Options may precede or follow positional arguments once their leaf command has been selected. `-t=uint256` is equivalent to `-t uint256`. `--` terminates option parsing. Each `-v` consumes exactly two values, a type then its textual value. Each `-p`, `-t`, and log-topic `-l` consumes one value and may be repeated. The long form `--lenient` and short form `-l` are interchangeable only on encoding commands; on `decode log`, `-l` means a log topic.

Unknown flags, unknown subcommands, surplus positional arguments, missing option values, and missing required positional arguments are errors. Diagnostics use the clap-v2 form. In particular, they contain `USAGE:` and finish with `For more information try --help`; missing positionals begin `The following required arguments were not provided:` and list every missing metavariable. Representative exact phrases are:

```text
Found argument '--nonexistent'
requires a value but none was supplied
requires 2 values, but 1 was provided
```

The missing markers are `<abi-path>`, `<function-name-or-signature>`, `<event-name-or-signature>`, and `<data>` as appropriate. A bad top-level command/flag produces no stdout and exits 1. `help decode` is valid, while `help --help` fails with a diagnostic containing `wasn't recognized`.

## Spec 4

### ABI type language and textual values

Supported elementary types are `bool`, `address`, `string`, dynamic `bytes`, fixed `bytes1` through `bytes32`, and integer names `uintN`/`intN`. The reference type parser is deliberately permissive for integer names: bare `uint` and `int` normalize to `uint256` and `int256`, and decimal suffixes are not restricted to canonical ABI widths, so names such as `uint7` and `uint999` are accepted. A whole elementary token that is not otherwise recognized—including `bogus`, `notatype`, `invalid_type`, and the empty string—falls back to `uint8` instead of failing. On decode, that fallback is printed as `uint8`, as in `-t invalid_type` producing `uint8 1`. Malformed composite syntax can still fail. Types compose recursively as dynamic arrays `T[]`, fixed arrays `T[K]` (including `K=0`), and tuples `(T1,T2,...)` (including `()`). Arbitrary tested nesting—nested arrays, fixed multidimensional arrays, tuples in arrays, arrays in tuples, and nested tuples—must work.

Text values use these forms:

- Booleans accept exactly `true`, `false`, `1`, and `0`, case-sensitively. No other numeric or textual spelling is valid.
- Addresses are exactly 20 hex bytes and may have an optional `0x` prefix. Mixed-case hex is accepted; checksum casing is not validated.
- A fixed byte string is exactly its declared number of bytes of hex. Fixed and dynamic byte strings accept an optional `0x` prefix. Dynamic `bytes` is any even number of payload hex digits, including empty.
- A `string` value is the argument’s bytes encoded as UTF-8, including spaces, newlines, quotes, punctuation, and non-ASCII characters. Quote characters are data, not delimiters: the token `"hello"` encodes seven bytes including both quotes.
- An array value is `[item1,item2,...]`; a tuple is `(item1,item2,...)`. Commas at the current nesting depth separate elements, while commas inside nested brackets or parentheses do not. Empty structures are `[]` and `()`. Surrounding structural delimiters are mandatory and fixed-array length must match. Tuple parsing zips supplied values with declared members and silently omits missing trailing members: encoding `(true)` as `(bool,address)` succeeds and emits only the bool word. Empty elements are meaningful for strings/bytes; for example `[,,,]` is four empty byte strings. The parser must handle at least 256 fixed-array elements and at least twelve top-level parameters.

In strict mode (the default), unsigned and signed integer values are raw, exactly 32-byte (64-digit) hexadecimal words with no `0x` prefix. The word is used directly as the integer’s ABI representation. Thus a short decimal-looking value such as `42` is not a valid strict integer value, while 64 hex digits ending in `...002a` are valid. Odd hex produces the hex-parser error before length validation. Strictness applies recursively within arrays and tuples.

In lenient mode, integer tokens are decimal. Unsigned tokens reject a minus sign. Signed tokens accept an optional minus sign and use 256-bit two’s-complement output; `-0` equals zero. `uint256` must reject values above `2^256-1`; `int256` must reject values outside `[-2^255, 2^255-1]`. For narrower declared integer types, the reference tokenizer deliberately does not enforce the nominal bit width: for example lenient `uint8 256` encodes the 256-bit value `0x100`, `int8 128` encodes `0x80`, and `int8 -129` encodes the 256-bit two’s-complement value ending in `7f`.

Lenient unsigned integers also accept exact decimal Ether units with optional whitespace before the unit. Required conversions include `wei = 10^0`, `gwei = 10^9`, and `ether = 10^18`; thus `1 ether`, `1 gwei`, and `0.5 ether` are valid. A fraction is valid only if multiplication yields an integral wei amount. `0.1 wei` and more than 18 fractional places for ether are invalid. Unit conversion also applies to integer elements nested in collections.

## Spec 5

### Ethereum ABI encoding

For complete value structures, encoding commands implement canonical Ethereum ABI head/tail encoding. The short-tuple omission in Spec 4 and zero-length fixed-array classification below are deliberate compatibility exceptions.

A type is dynamic if it is `string`, `bytes`, a dynamic array, a nonzero-length fixed array whose element is dynamic, or a tuple containing any dynamic member. A zero-length fixed array is zero-size static even when its element type would be dynamic; consequently top-level `string[0] []` emits no offset or data, only the command's final newline. Every other supported type is static. The static size of an elementary type is one word; fixed arrays and static tuples have the sum of their members’ static sizes.

- `uint` values are 32-byte big-endian and left-zero-padded. `int` values use a 256-bit two’s-complement word (negative values are sign-extended with `ff`). A bool is a word containing 0 or 1. An address occupies the low/rightmost 20 bytes of a zero-padded word.
- `bytesN` contains its N bytes at the left of a word and is right-zero-padded. Dynamic `bytes` and `string` are encoded as a 32-byte byte-length followed by the data right-padded with zero bytes to a word boundary.
- A static fixed array is the concatenation of its element encodings and has no length word. A dynamic array has a length word followed by the elements encoded as a tuple. A tuple is the encoding of its ordered components. Empty static tuples/zero-length fixed arrays encode to zero bytes.
- For any aggregate, its head contains each static member inline at its full static size; each dynamic member contributes one word containing the byte offset to that member’s tail. Offsets are measured from the beginning of that aggregate’s tuple encoding. For a dynamic array, element offsets are measured from the region immediately after the array’s length word. Tails are appended in member order. The top-level argument list itself is such a tuple.

The result is emitted as one continuous lowercase hex line without `0x`. Examples:

```text
bool true  -> 0000000000000000000000000000000000000000000000000000000000000001
bytes1 ff  -> ff00000000000000000000000000000000000000000000000000000000000000
uint256[] [] ->
0000000000000000000000000000000000000000000000000000000000000020
0000000000000000000000000000000000000000000000000000000000000000
```

The two displayed lines for the empty array are concatenated in actual output.

## Spec 6

### `encode params`

`encode params` parses each repeated `-v TYPE VALUE` using Spec 4, ABI-encodes all pairs as one top-level tuple using Spec 5, and prints the resulting hex. With no `-v`, it succeeds with empty output (normally just `\n`). The order of `-v` pairs is preserved.

Examples that fix important parsing and layout behavior:

```text
executable encode params -v bool 1
=> 0000000000000000000000000000000000000000000000000000000000000001

executable encode params -v bool 1 -v string gavofyork -v bool 0
=> 0000000000000000000000000000000000000000000000000000000000000001
   0000000000000000000000000000000000000000000000000000000000000060
   0000000000000000000000000000000000000000000000000000000000000000
   0000000000000000000000000000000000000000000000000000000000000009
   6761766f66796f726b0000000000000000000000000000000000000000000000
```

Again, example continuation lines concatenate. Invalid value/type/shape data is an operational error, not partial output.

## Spec 7

### JSON ABI files

`encode function`, `decode function`, and `decode log` open and JSON-decode the supplied file. The root is an array of ABI entries. Recognized entry kinds include `function`, `event`, `constructor`, `fallback`, `receive`, and `error`; only functions are callable and only events are log-decodable. The other kinds must parse without interfering with regular entries.

A function has a case-sensitive `name`, an `inputs` array, and an `outputs` array. An event additionally requires `anonymous`. Its input `indexed` field is optional and defaults to `false`; omitting it is not a serialization error. Ordinary input/output/event parameter objects require string `name` and string `type` fields (an empty name string is allowed). `internalType` is optional and does not alter encoding. Tuple types written in JSON as `tuple`, `tuple[]`, or `tuple[K]` require a `components` array; component `type` is required, while component `name` and `internalType` are optional. Components may recursively be tuples and arrays.

Unknown common metadata such as `constant`, `payable`, and `stateMutability` is tolerated. Duplicate JSON fields are rejected rather than silently taking one value. Missing required fields, invalid JSON, non-object parameter entries, and invalid type descriptions are rejected. Non-object ordinary parameters use `expected a valid event parameter spec`; missing fields instead identify the field directly. A non-object tuple component uses `expected a valid tuple parameter spec`; a component missing `type` reports the internal field name `kind`.

Serialization failures render the parser detail twice, with exactly one empty line before a four-space-indented cause:

```text
Error: Serialization error: DETAIL

Caused by:
    DETAIL
```

`DETAIL` includes the parser's line and column. For duplicate or missing structural fields, the location is the reference deserializer's cursor after consuming the surrounding structure, which can be the end of the complete ABI document rather than the line containing the field. The following exact reference results fix the field labels, locations, and layout for the implicated inputs:

```text
tuple parameter with duplicate components       duplicate field `components` at line 25 column 1
ordinary parameter with duplicate name          duplicate field `name` at line 14 column 1
ordinary parameter with duplicate type          duplicate field `kind` at line 14 column 1
ordinary parameter with duplicate internalType  duplicate field `internalType` at line 15 column 1
ordinary parameter missing name                  missing field `name` at line 12 column 1
ordinary parameter missing type                  missing field `kind` at line 12 column 1
tuple parameter missing type                     missing field `kind` at line 18 column 1
tuple component with duplicate internalType      duplicate field `internalType` at line 21 column 1
tuple component with duplicate name              duplicate field `name` at line 20 column 1
tuple component with duplicate type              duplicate field `type` at line 20 column 1
event parameter with duplicate indexed           duplicate field `indexed` at line 15 column 1
event parameter missing name                     missing field `name` at line 13 column 1
```

For the compact ABI input `[{"type":"function","name":"x","inputs":[{"type":"bool"}],"outputs":[]}]` and the equivalent missing-name output case, and for the compact tuple-component case in the tested enclosing ABI, the respective details are:

```text
missing field `name` at line 1 column 72
missing field `kind` at line 1 column 112
```

Invalid JSON retains equally exact parser wording. An ABI file containing `{ invalid json` reports `invalid type: map, expected valid abi spec file at line 1 column 3` as `DETAIL`; one containing `not valid json` reports `expected ident at line 1 column 2`. Thus the first diagnostic includes the literal word `invalid`. A missing file reports `Error: No such file or directory (os error 2)` on Linux.

## Spec 8

### Function and event lookup

A bare identifier performs exact, case-sensitive lookup by name. No match gives `Error: Invalid name: NAME`. More than one entry with that name is an error:

```text
Error: More than one function found for name `NAME`, try providing the full signature
```

This wording is also used for ambiguous events.

A function identifier containing parentheses is parsed as a full structural signature and matched against the ABI entry, including outputs when present. Accepted forms are `name(T1,T2,...)` with no outputs and `name(T1,...):(R1,...)` when output types are supplied. A bare empty-parentheses signature is valid: `empty()` matches a function having no inputs and no outputs and encodes normally. An empty input list with outputs, such as `totalSupply():(uint256)`, is also valid. Whitespace inside function signatures is not normalized and causes failure. Tuple and array type syntax is supported. Supplied outputs must exactly match the ABI outputs; for example an ABI `bar(address):(bool)` is not matched by `bar(address)` or by `bar(address):(uint256)`.

An event signature is `Name(T1,T2,...)`, has no output portion, supports tuple/array types, and is matched exactly after trimming spaces around comma-separated types. Therefore `Transfer(address, address, uint256)` matches `Transfer(address,address,uint256)`. Function and event names remain case-sensitive.

Lookup checks the base name before assigning a signature diagnostic. If no ABI entry has that base name, even a parenthesized identifier reports `Error: Invalid name: NAME`, with only the portion before `(` as `NAME`; for example, `bar(bool)` against an ABI containing only `foo` reports `Error: Invalid name: bar`. If entries with that base name exist but the supplied function signature is malformed or does not structurally match them, report exactly `Error: invalid function signature ` followed by the supplied signature in backticks. A structurally valid but nonmatching event signature fails rather than falling back to name-only matching, subject to the same missing-base-name rule.

## Spec 9

### `encode function`

After loading a function, parse supplied `-p` values in ABI input order, using strict or lenient mode exactly as for `encode params`. If fewer values than inputs are supplied, fail with `Error: Invalid data`. If more are supplied, silently ignore values beyond the declared input count; ignored extras are not parsed or validated.

Canonicalize the function’s input types, replacing JSON `tuple` types by parenthesized component types, and compute:

```text
selector = first 4 bytes of Keccak-256(UTF-8(name + "(" + comma_join(input types) + ")"))
```

Output the selector followed immediately by the ABI encoding of the declared inputs. Outputs never affect selector computation. A no-input function emits only eight hex digits. Required known selectors include:

```text
foo(bool)                         45557578
bar(bool)                         6fae9412
bar(string)                       d473a8ed
approve(address,uint256)          095ea7b3
transfer(address,uint256)         a9059cbb
transferFrom(address,address,uint256) 23b872dd
balanceOf(address)                70a08231
totalSupply()                     18160ddd
```

## Spec 10

### ABI decoding and value display

The DATA positional argument of every decode command is first hex-decoded and rejects a `0x` prefix; log topics have the separate prefix rule in Spec 12. Uppercase and mixed-case hex are accepted. Odd digit count produces `Error: Odd number of digits`. An invalid digit produces `Error: Invalid character 'X' at position P`, where P is the zero-based character index. Except for the empty `decode params` case below, truncated required head, length, and static-value words, offsets beyond the buffer, declared dynamic payload lengths beyond available payload bytes, and oversized offset/length words fail safely with `Error: Invalid data`. ABI right-padding after a complete declared `string` or dynamic-`bytes` payload is not required: a five-byte `hello` payload succeeds even when its final padded word contains only 24 of the canonical 27 zero padding bytes. Offsets need not be canonical or point beyond the head: an offset of zero is accepted when decoding from it produces an otherwise valid value. Extra complete trailing data after all requested values is ignored. For example, decoding `bytes` from a long all-zero buffer succeeds as empty bytes because its zero offset points to a zero length word.

Decoding is the inverse of Spec 5, including recursive fixed/dynamic arrays and tuples. Display values as follows:

- `bool`: the first 31 bytes must all be zero or decoding fails with `Error: Invalid data`. Given zero high bytes, the value is `true` only when the final byte is exactly `01`; every other low byte is accepted and displayed as `false`, so a canonical-high word ending in `02` displays as `false`.
- `uintN`: lowercase minimal hexadecimal, without `0x` or leading zeroes; zero is `0`.
- `intN`: the lowercase hexadecimal representation of the entire decoded 256-bit two’s-complement word. Thus a negative value retains all leading `f` digits, while a positive value is minimal hex.
- `address`: exactly 40 lowercase hex digits, without `0x`.
- `bytesN`: exactly N lowercase hex bytes, omitting ABI right padding. Dynamic `bytes`: exactly its payload as lowercase hex; empty bytes displays as the empty string.
- `string`: decoded as lossy UTF-8 and displayed verbatim, without adding or removing quotes. Each malformed byte sequence is replaced using the Unicode replacement character `�` (U+FFFD); for example, a one-byte payload `ff` succeeds and prints `string �`.
- arrays: `[v1,v2,...]`; tuples: `(v1,v2,...)`; no spaces are inserted after commas. Formatting recurses.

For `decode params`, print one line per requested type as `TYPE VALUE`, normally using the type spelling supplied on the command line. The aliases `uint` and `int` are instead printed as their normalized forms `uint256` and `int256`; an unrecognized elementary token that triggers Spec 4's fallback is printed as `uint8`. For an empty string/bytes value this leaves a trailing space before the newline (which appears as just the type after trimming). If no `-t` options are given, validate that DATA is hex, then succeed with empty output.

When `decode params` has at least one `-t` option and DATA is the empty string, it writes no standard output, exits 1, and reports exactly:

```text
Error: Invalid name: please ensure the contract and method you're calling exist! failed to decode empty bytes. if you're using jsonrpc this is likely due to jsonrpc returning `0x` in case contract or method don't exist
```

This takes precedence over the truncated-head `Error: Invalid data` rule. With no `-t` options, empty DATA retains the successful empty-result behavior above.

Examples:

```text
uint256 word ending 002a       -> uint256 2a
int8 word ffff...ff80          -> int8 ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff80
address word ...1234567890     -> address 1234567890123456789012345678901234567890
uint256[3] values 10,20,30     -> uint256[3] [a,14,1e]
bool[] values 1,0,1            -> bool[] [true,false,true]
```

## Spec 11

### `decode function`

Load the selected function and interpret DATA as only its ABI-encoded return values; DATA does not contain and must not be expected to contain the 4-byte selector. Function lookup follows Spec 8. Print each declared output on its own line as `TYPE VALUE`, in ABI output order, using the recursive display rules of Spec 10. Parameter names are not printed. JSON tuple types are printed in expanded canonical form, such as `(uint256,address)`, rather than as the word `tuple`.

Functions with no outputs accept empty DATA and succeed with empty output. A function with outputs rejects empty or insufficient DATA. In particular, empty data for a nonempty result reports:

```text
Error: Invalid name: please ensure the contract and method you're calling exist! failed to decode empty bytes. if you're using jsonrpc this is likely due to jsonrpc returning `0x` in case contract or method don't exist
```

Otherwise malformed ABI data reports `Error: Invalid data`. Extra return-data words are accepted and ignored.

## Spec 12

### `decode log`

Load an event by name or signature. Each repeated `-l TOPIC` is one 32-byte hex topic and DATA is the ABI encoding of all non-indexed event parameters. A topic accepts one optional `0x` prefix; its payload after removing that prefix must be exactly 64 hex digits or it fails with `Error: Invalid input length`. DATA does not accept `0x` and follows Spec 10's hex diagnostics.

For a non-anonymous event, topics must consist of the event signature topic followed by one topic for each indexed input. The signature topic is the full 32 bytes of:

```text
Keccak-256(UTF-8(event name + "(" + comma_join(canonical input types) + ")"))
```

It must match exactly. For an anonymous event, omit the signature topic and provide exactly one topic per indexed input. Too few or too many topics, a wrong signature topic, insufficient data, or otherwise invalid topic/data layout normally gives `Error: Invalid data`. One diagnostic precedence case differs: after a non-anonymous event's signature topic has been supplied and validated, if an indexed topic is still missing and DATA is empty, the long empty-result diagnostic from Spec 11 is returned instead of `Error: Invalid data`. If an event expects non-indexed data and DATA is the empty string, that same long diagnostic also applies.

For parenthesized event identifiers, base-name lookup has the precedence described in Spec 8. Against an ABI containing only event `Other`, both `Transfer(` and `Transfer(address)` report exactly `Error: Invalid name: Transfer`; no abbreviated signature hash is reported.

Decode static indexed parameters directly from their topic word. For indexed dynamic/aggregate values, the topic represents the Keccak hash and is displayed as that 32-byte lowercase hex value. Decode non-indexed parameters from DATA as an ABI tuple. Merge both groups back into the event’s original input declaration order and print one line per input as `PARAMETER_NAME VALUE`; unlike function/parameter decoding, do not print the type.

For example, ERC-20

```text
event Transfer(address indexed from, address indexed to, uint256 value)
```

has signature topic `ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`. Given indexed addresses ending in `a94f...bf0b` and `5a0b...29c4` and a data word of `64`, output is:

```text
from a94f5374fce5edbc8e2a8697c15331677e6ebf0b
to 5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c
value 64
```

## Spec 13

### Error compatibility and boundary cases

Operational value errors use these reference diagnostics where applicable:

```text
Error: Invalid data
Error: Uint parse error: InvalidCharacter
Error: int256 parse error: Overflow
Error: int256 parse error: Underflow
Error: Invalid name: NAME
Error: invalid function signature `SIGNATURE`
```

Strict-mode hex errors occurring while tokenizing an encode value retain their context and cause chain, exactly:

```text
Error: Hex parsing error: Odd number of digits

Caused by:
    Odd number of digits
```

or, substituting the underlying message:

```text
Error: Hex parsing error: Invalid character 'n' at position 0

Caused by:
    Invalid character 'n' at position 0
```

Invalid booleans, wrong fixed-byte length, wrong fixed-array length, missing function inputs, and malformed ABI-encoded data use `Error: Invalid data`. Short tuple values follow the omission behavior in Spec 4 rather than this error rule. Invalid lenient unsigned decimal text, negative unsigned integers, and inexact units use `Error: Uint parse error: InvalidCharacter`. Arithmetic and offset calculations must be bounds-checked so maliciously large lengths or deeply invalid offsets return an error without excessive allocation, crash, or timeout.
