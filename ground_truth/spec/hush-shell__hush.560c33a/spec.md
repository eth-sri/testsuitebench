The required artifact is a Unix executable named exactly `executable`. It implements the Hush 0.1.4 command-line interpreter described below. All byte strings and output are byte-preserving unless a rule explicitly requires UTF-8. Examples of output are literal, including spaces, tabs, spelling, capitalization, and final newlines.

## Spec 1

The executable accepts this single-command interface (there are no subcommands):

```text
executable [FLAGS] [arguments]...
```

The recognized flags are `--ast`, `--check`, `-h`/`--help`, `--lex`, `--program`, and `-V`/`--version`. Each flag may appear at most once. An unknown option before the first positional argument, such as `--unknown-flag`, `--nonexistent`, or `-x`, exits 1, writes nothing to stdout, and emits a clap-style diagnostic to stderr containing `error: Found argument 'OPTION' which wasn't expected, or isn't valid in this context`, a blank line, `USAGE:`, the general usage line, another blank line, and `For more information try --help`. Repeating a flag exits 1 and similarly reports `The argument 'FLAG' was provided more than once, but cannot be used multiple times`, but its usage line is specialized to the repeated flag. In particular, `executable --lex --lex` writes nothing to stdout and uses exactly `    executable --lex`, not the general `    executable [FLAGS] [arguments]...`, beneath `USAGE:`. `--` ends option parsing; every later token is positional, even `-x`. Once an ordinary positional token has been seen, later dash-prefixed tokens are script arguments rather than interpreter flags.

## Spec 2

`--help` and `-h` succeed, write nothing to stderr, and write exactly the following newline-terminated text to stdout:

```text
Hush 0.1.4
gahag <gabriel.s.b@live.com>
Hush is a unix shell scripting language based on the Lua programming language

USAGE:
    executable [FLAGS] [arguments]...

FLAGS:
        --ast        Print the AST
        --check      Perform only static analysis instead of executing.
    -h, --help       Prints help information
        --lex        Print the lexemes
        --program    Print the PROGAM
    -V, --version    Prints version information

ARGS:
    <arguments>...    Script and/or arguments
```

`--version` and `-V` succeed, write nothing to stderr, and write exactly `Hush 0.1.4\n` to stdout.

## Spec 3

Source selection is positional and deliberately differs from a conventional mandatory script operand. Scan positional arguments from the start. If the first positional is `-`, read the entire source from stdin and do not include that marker in `std.args()`. If the first positional names an existing regular file, read that file as source and make only the remaining positionals available through `std.args()`. Otherwise, including when it resembles a nonexistent path, read source from stdin and make every positional available through `std.args()`. With no positionals, read stdin. An empty input, whitespace-only input, comment-only input, and a file with or without a terminal newline all succeed silently.

The source label used in diagnostics and debug output is exactly the supplied file path for file input and `<stdin>` for stdin. `std.args()` returns a new array of strings preserving argument order and bytes, including empty strings, whitespace, Unicode, numeric-looking strings, `$`, `-x`, and `--`. The source filename itself is never present.

## Spec 4

Normal processing is lexing, parsing, static name/context analysis, then execution. `--check` performs all static phases but never evaluates code or performs runtime side effects. `--lex`, `--ast`, and `--program` request diagnostic renderings but do not by themselves suppress execution. When combined, renderings always appear in the fixed order lexemes, AST, Program, regardless of flag order, and normal program stdout follows them. With `--check`, the requested renderings remain but program stdout and side effects do not occur.

The standard exit statuses are 0 for success, 1 for CLI parsing failure, 2 for lexical, syntax, or semantic failure, and 127 for a handled runtime panic. The uncaught native-runtime failures explicitly documented in Specs 20 and 33 are exceptions to the handled-panic status. `std.exit(n)` terminates immediately with the supplied integer status, which must be in 0 through 255. Static diagnostics and panics go to stderr. Debug renderings and language printing go to stdout. Noninteractive output contains no ANSI color escapes.

## Spec 5

Source consists of a sequence of statements and expressions. ASCII spaces, tabs, CR/LF line endings, and blank lines separate tokens. `#` begins a comment extending through the newline, both at top level and within command blocks. Consecutive comment lines are just consecutive line comments. Newlines are not mandatory between statements where the grammar makes the boundary unambiguous. A semicolon is not a top-level statement separator; outside a command block it is an unexpected lexical character. Within commands it is a pipeline/block separator.

Identifiers start with an ASCII letter or `_` and continue with ASCII letters, digits, or `_`; names are case-sensitive. Reserved words are `let`, `if`, `then`, `else`, `elseif`, `end`, `for`, `in`, `do`, `while`, `function`, `return`, `break`, and `self`. Literal words are `nil`, `true`, and `false`; operator words are `not`, `and`, and `or`.

## Spec 6

Literal forms are:

- signed behavior is expressed using unary `-`; integer tokens are unsigned decimal and their magnitude may not exceed `9223372036854775807`. Consequently, the token `9223372036854775808` is a lexical error even when immediately preceded by unary `-`: `-9223372036854775808` is rejected rather than treated as the signed minimum;
- decimal floats are IEEE-754 binary64 and accept fractional and exponent notation such as `456.7`, `89e10`, and `1.2e3`;
- a single-quoted literal contains exactly one byte, for example `'a'`, `'\n'`, or `'\0'`;
- a double-quoted string contains any number of bytes, including NUL and UTF-8;
- array literals are `[item, ...]`. Dictionary literals are `@[name: value, ...]`, where every key before `:` must be an identifier token; the identifier denotes its string spelling rather than an evaluated expression. Thus `@[name: 1,]` is valid, while `@["other": 2]` and `@[1: 2]` are syntax errors with `expected identifier`. Empty forms are `[]` and `@[]`, and trailing commas are accepted.

The valid source escapes in byte and string literals are `\0`, `\n`, `\t`, `\\`, `\'`, and `\"`. They mean NUL, LF, tab, backslash, apostrophe, and quotation mark. There is no numeric byte suffix: a decimal token stops when an identifier character other than exponent `e`/`E` is reached. Because adjacent statements are permitted, `let b = 65b` is consequently tokenized as `let b = 65` followed by the expression `b`, leaving `b` equal to integer 65. An invalid escape, empty byte literal, multiple-byte character literal, unterminated literal, malformed number, or integer token outside the representable range is a lexical error. Strings retain UTF-8 as its constituent bytes rather than changing normalization.

## Spec 7

Statements have these forms:

```text
let name = expression
target = expression
expression
return expression
return
break
while condition do statements end
for name in expression do statements end
function name(parameters) statements end
```

`function name(...) ... end` is declaration sugar for `let name = function(...) ... end`; `function(parameters) ... end` is also an expression. Parameter and argument lists are comma-separated and may be empty; trailing commas are accepted. A bare `let name` is syntactically accepted and initializes it to `nil`. A bare `return` returns `nil`. `return` is statically invalid outside a function, `break` is invalid outside a loop, and a break inside a function nested within a loop is still outside that loop. `self` and postfix `?` are invalid outside a function. Empty command blocks are syntax errors, while empty language blocks/functions are valid.

## Spec 8

Expressions include literals, names, `self`, parenthesized expressions, anonymous functions, `if` expressions, calls `f(args)`, indexing `value[key]`, member access `value.name`, command blocks, prefix `-` and `not`, postfix `?`, and binary operations. Postfix call/access/`?` binds tightest and may chain, followed by prefix operators, `* / %`, `+ -`, string concatenation `++`, relational `< <= > >=`, equality `== !=`, `and`, then `or`. Binary operators at each level associate left-to-right. Parentheses override precedence.

`if condition then statements elseif condition then statements else statements end` is an expression as well as a legal expression statement. Each branch yields its last statement's value, or `nil` when empty; no selected branch yields `nil`. `elseif` behaves as a nested `if` in the final `else`. Conditions for `if` and `while`, operands of `not`, and evaluated operands of `and`/`or` must be booleans; there is no truthiness. `and` and `or` short-circuit and return booleans.

## Spec 9

Lexical scoping is static. `std` is the predefined root binding. A `let` introduces a mutable binding in the current block; duplicate declarations in one scope are static errors, while a nested block may shadow an outer name. If branches, loop bodies, and function bodies have nested scopes. Loop variables shadow and then restore outer names. Referring to or assigning an undeclared/inaccessible name is a static error. Declaration visibility among siblings follows source order: a binding declared later is not visible in the initializer or function body of an earlier declaration. A named function declaration is nevertheless visible within its own body, permitting direct recursion. Thus, if `function odd(n) ... even(n - 1) ... end` precedes the sibling declaration of `even`, the reference fails static analysis at that use with `undeclared variable 'even'`; sibling function declarations do not provide mutual forward references.

Assignment is allowed only to a declared variable or to an index/member chain rooted in a value. Literal expressions, calls, and arithmetic expressions are not valid assignment targets. Arrays and dictionaries are reference objects: assignment aliases them, and element changes are seen through all aliases. Captured variables are mutable shared cells. Strings and Error objects are immutable, so assigning an indexed string or `error.description`/`error.context` panics or is rejected as appropriate.

## Spec 10

The runtime types, and the exact strings returned by `std.type`, are `nil`, `bool`, `int`, `float`, `char`, `string`, `array`, `dict`, `function`, and `error`. Bytes use type name `char`. Values of different types are never implicitly coerced for language operators. `nil == nil` is true; booleans compare by value. Equality across different types is false, notably `1 != 1.0`. Arrays and dictionaries compare structurally and recursively. Integers and floats remain distinct dictionary keys, so both `1` and `1.0` can be present.

Value display is used by `std.to_string`, nested collection formatting, and error contexts: `nil`, lowercase booleans, decimal integers, floats in the shortest debug-like representation that retains `.0` for integral floats (`42.0`) and uses `inf`, `-inf`, and `NaN`; strings are double-quoted with debug escapes; arrays are `[ ]` or `[ value, value ]`; dictionaries are `@[ ]` or `@[ key: value, ... ]`; user functions are `function<SOURCE (line L, column C)>`; native functions display their qualified name such as `std.env`; errors display `error: "description" (context)`. Dictionary iteration/display order is unspecified. When a top-level argument to `std.print` or `std.println` is a string it is written without surrounding quotes, and a char is written as its raw byte.

## Spec 11

Integer `+ - * / %` requires two integers and checks signed-64-bit overflow/underflow. Integer division truncates toward zero; remainder has the dividend's sign. Division or remainder by zero panics. Float arithmetic requires two floats and implements IEEE-754 behavior, including infinities, NaN, subnormals, and precision loss; float division by zero produces infinity or NaN instead of panicking, and float remainder is supported. Mixed int/float arithmetic is a type panic.

Relational operators require operands of the same comparable type: int, float, char, or string. Characters compare by byte value and strings lexicographically by bytes. Float ordering is totalized for sorting/relational purposes with NaN below ordinary numbers: a generated NaN is unequal to itself, `NaN < 1.0` is true, and `NaN > 1.0` is false. `++` requires two strings and concatenates their bytes; it chains left-to-right. Applying numeric, relational, boolean, or concatenation operators to other types panics with a type/value diagnostic.

## Spec 12

Arrays are heterogeneous, zero-indexed, mutable sequences. Indexing requires an integer. A negative or out-of-range index panics. Nested indexing and mutation work. `std.len(array)` returns its length. `std.push(array, value)` appends in place and returns `nil`; `std.pop(array)` removes and returns the last value and panics on an empty array. `std.sort(array)` sorts the same array in ascending runtime value order and returns `nil`; integers and strings sort naturally, duplicates remain, empty arrays work, and the global value type order is used for mixed values (all ints precede floats). Implementations must handle arrays of at least 10,000 elements and at least 15 nested levels.

## Spec 13

Dictionaries are mutable hash maps with arbitrary hashable runtime values as keys. Literal keys are nevertheless restricted to identifiers: `@[name: value]` turns `name` into the string key `"name"`, and duplicate literal names are static errors. Quoted strings, numbers, and other expressions are not accepted in the key position of a dictionary literal. Non-identifier keys are added with bracket assignment after construction, for example `let d = @[] d[1] = 2`. `obj.name` is sugar for `obj["name"]`. Bracket access supports computed string keys (including empty, whitespace, newline, NUL, and Unicode keys), numeric keys, booleans, and other hashable primitive keys. Assignment replaces or adds a key. Reading a missing key panics. `std.len(dict)`, `std.is_empty(dict)`, and `std.contains(dict, key)` operate on entries. Large dictionaries of at least 1,000 entries and deeply nested member access must work.

Accessing a function through a dictionary (`obj.method(...)` or `obj[key](...)`) invokes it with `self` bound to the receiving dictionary. A plain function call has `self == nil`. `std.bind(receiver, function)` returns a function that always uses that receiver as `self`. This applies to methods stored in nested objects and permits mutation through `self`.

## Spec 14

Functions are first-class and have exact arity. They can be anonymous, recursive, nested, stored in arrays/dictionaries, passed and returned, and invoked immediately through chains such as `factory()(x)`. A call with too few or too many arguments panics; calling a non-function also panics. A function body executes in order and returns the value supplied to the first executed `return`; absent an explicit return, its final statement value is returned, and an empty body returns `nil`.

Closures capture referenced lexical bindings by reference, not a snapshot. Multiple closures from one invocation share those cells; separate factory invocations receive independent cells; captures may cross three or more nested functions. At least 100 parameters/call arguments and recursion depth 1,000 must be supported. Postfix `expr?` evaluates `expr`: if it is an Error value it immediately returns that Error from the current function, otherwise it yields the value unchanged.

## Spec 15

`while condition do ... end` tests before every iteration and returns `nil`. `for name in iterator do ... end` does not accept a collection directly: `iterator` must be a zero-argument function. Each call must return a dictionary with boolean field `finished`; when false it must also contain `value`, which is assigned to the loop variable. A true `finished` ends the loop. Malformed protocol values or raw arrays/dicts/strings used directly panic. `break` terminates only the innermost loop, and loops themselves return `nil`.

`std.iter(x)` returns a stateful iterator function for an array, string, or dictionary. Arrays yield elements in index order. Strings yield one char/byte at a time. Dictionaries yield dictionaries of the form `@[key: original_key, value: original_value]` in unspecified order. Exhausted iterators stay exhausted. Passing another type uses the exact expected-type list `string, array or dict`; for example `std.iter(42)` panics with `value (42) has unexpected type, expected string, array or dict`. `std.range(from, to, step)` returns the same protocol, is half-open, and accepts all ints or a mix of ints/floats (promoting to floats). A positive step continues while current `< to`; a negative step continues while current `> to`. A zero step produces an empty iterator. Thus reverse bounds with a positive step are empty. Each iterator call itself accepts zero arguments only.

## Spec 16

`std.print(...)` and `std.println(...)` are variadic. They display arguments separated by one tab. `print` adds no newline; `println` adds exactly one newline, including with zero arguments. Both return `nil`. They preserve raw UTF-8/string bytes and char bytes. `std.read()` reads and returns the next stdin line including its newline (or the remaining bytes at EOF). `std.read(prompt)` first writes and flushes the unquoted prompt string to stdout, then reads a line. No other arities are valid.

`std.type(value)` returns the type strings in Spec 10. `std.to_string(value)` returns the value display as a string, except an input string is returned as its unquoted contents. A char is converted as the Unicode scalar having that byte's numeric value and then UTF-8 encoded; this is not byte-preserving for bytes at least `0x80`. For example, iterating `"é"` yields the two byte-valued chars `0xc3` and `0xa9`, but hex-encoding their `std.to_string` results yields `c383` and `c2a9`. (Printing a char directly remains raw-byte behavior.) These functions and all other fixed-arity standard functions panic on an incorrect argument count.

## Spec 17

String operations are byte-oriented:

- `std.len(string)` counts bytes, so multibyte UTF-8 counts by encoded length; string indexing is zero-based and returns a `char` byte. Negative/out-of-range indices panic.
- `std.bytes(string)` returns an array of its char bytes; empty input returns `[]`.
- `std.substr(string, start, length)` uses integer byte offsets. It returns exactly that slice, and returns `nil` rather than panicking if either integer is negative or the requested end exceeds the string. A zero-length slice at the end is valid.
- `std.split(string, literal_separator)` performs literal non-overlapping byte splitting and preserves leading, trailing, and consecutive empty fields. Empty input produces `[ "" ]`.
- `std.replace(string, literal_pattern, replacement)` replaces every non-overlapping match. An empty pattern inserts the replacement at every byte boundary, including both ends.
- `std.trim(string)` removes leading and trailing ASCII byte whitespace (space, tab, LF, CR, vertical tab, and form feed), returning unchanged internal content.

`std.contains(string, char)` tests a byte, while `std.contains(array, value)` uses structural equality and `std.contains(dict, key)` tests keys. `std.is_empty` and `std.len` accept only string, array, or dict. Wrong receiver/item types panic. The expected-type spelling is function-specific: `std.contains(42, 1)` reports `expected string ,array or dict` (including the space before the first comma and none after it), whereas `std.is_empty(42)` reports `expected string, array or dict`.

## Spec 18

`std.int(x)` accepts int unchanged, float truncated toward zero, or a decimal integer string; invalid strings and other types panic. `std.float(x)` accepts float unchanged, int converted through binary64, or a float string including scientific notation; invalid strings/types panic. Large int-to-float conversion may lose precision. Parsing errors use messages of the form `invalid value (DISPLAY), expected valid integer` (the reference float parser also uses the words `valid integer`).

`std.typecheck(value, type_name)` returns `value` unchanged when its exact type matches and otherwise panics. `std.try_typecheck(value, type_name)` instead returns `nil` on an exact match and an Error value on mismatch. This success result is independent of the matched value: `std.type(std.try_typecheck(42, "int"))` is `nil`. The valid type-name strings are exactly the ten names from Spec 10; a non-string or unknown name and wrong arity panic. Typechecking never performs coercion.

## Spec 19

An Error is an ordinary immutable value created by `std.error(description, context)`, with fields `.description` (the original string) and `.context` (any value). `std.has_error(value)` recursively detects an Error directly or anywhere in arrays or in dictionary keys or values. `std.panic(value)` raises a runtime panic whose message includes the displayed value. `std.assert(true)` returns `nil`; `std.assert(false)` panics with `assertion failed`. `std.catch(function)` calls its zero-argument function with nil self. A normal result, including a deliberately returned Error, passes through unchanged. A runtime panic is converted to an Error whose description is `caught panic: ` followed by the complete located panic rendering from Spec 29, with that rendering's final newline omitted, and whose context is the string `"panic"`. For example, a caught assertion whose failing value is at `<stdin>` line 1 column 103 produces the exact description `caught panic: Panic in <stdin> (line 1, column 103): assertion failed`, not `caught panic: assertion failed`.

Postfix `?` is Error propagation as described in Spec 14. Error-returning APIs do not automatically panic: callers may inspect their fields, use `std.has_error`, propagate with `?`, or return them. Attempting to modify either Error field is a runtime panic.

## Spec 20

Environment and process functions are:

- `std.env(name)` returns the exact environment value as a string, including an empty value, or `nil` if absent.
- `std.export(name, value)` requires strings, updates the interpreter environment for later `std.env` calls and child processes, and returns `nil`. A key containing `=` or NUL returns an Error with description `invalid export key`; a value containing NUL returns an Error with description `invalid export value`.
- `std.cwd()` returns the current working directory as a string.
- `std.cd(path)` changes it persistently and returns `nil`, or returns an Error on failure.
- `std.sleep(milliseconds)` requires a nonnegative integer, sleeps approximately that many milliseconds, and returns `nil`; negative values panic. Despite accepting zero, its negative-value diagnostic uses the exact expectation phrase `positive integer`, as in `invalid value (-100), expected positive integer`.
- `std.exit(code)` behaves as in Spec 4.

`std.rand()` takes no arguments and returns a nondeterministic float in `[0.0, 1.0)`. `std.randseed(integer)` resets the per-thread ChaCha8 random sequence deterministically and returns `nil`, so reseeding with the same integer reproduces subsequent values. `std.randint(min, max)` takes integers and returns an inclusive uniformly selected integer, with equal bounds returning that bound. Bad arity and types cause handled Hush panics. An inverted integer interval is a reference-runtime exception: `std.randint(3, 2)` reaches an uncaught Rust panic, writes a diagnostic containing `cannot sample empty range`, and exits 101 rather than the handled-panic status 127.

## Spec 21

Filesystem functions are:

- `std.glob(pattern)` accepts a string glob and returns matching paths in deterministic glob traversal order, supporting `*`, `?`, character classes, and recursive `**`. No matches returns `[]`; an invalid pattern returns an Error. Absolute patterns return absolute paths.
- `std.import(path)` loads a Hush source file, runs the same parse/static/runtime pipeline, and returns the final value of the imported top-level program. A relative path is resolved relative to the directory containing the importing file, not the current working directory. Canonical paths are cached so the same module is evaluated only once. Nested relative imports work. Failure reporting depends on the phase. A missing file panics at the import call with the raw OS description `No such file or directory (os error 2)`, without a `failed to import module` wrapper. A runtime panic inside a loaded module propagates with the imported file's original location and message. A module that fails parsing/static analysis first emits its own static diagnostic and then panics at the import call with `failed to import module (PATH)`, where `PATH` is the resolved imported path inserted as raw path text without the double quotes used by string value display.

The executable itself implements only this interpreter. External utilities invoked by command blocks (for example `echo`, `cat`, `grep`, `cut`, `tr`, `env`, `pwd`, `date`, `whoami`, `ls`, and `sh`) are harness-provided executables found through `PATH`; their behavior is not part of `executable`.

## Spec 22

Encoding APIs operate on raw string bytes. `std.base64.encode(string)` uses standard Base64 alphabet and `=` padding; decode returns the original byte string, including empty and binary data. Invalid Base64 returns an Error rather than panicking. `std.hex.encode(string)` emits two lowercase hex digits per byte; decode returns bytes, and malformed/odd/invalid input returns an Error. All four functions require exactly one string.

`std.json.encode(value)` returns pretty JSON with two-space indentation for nonempty arrays/objects; primitives and empty collections use ordinary compact JSON. It maps nil to `null`, bool/number/string naturally, char to a one-character JSON string, and recursively handles arrays/dictionaries. The non-finite floats positive infinity, negative infinity, and NaN are each encoded as JSON `null`; encoding one succeeds rather than panicking. Dictionary keys must be strings. A function, Error, or unsupported key panics as an invalid value. For a function, the exact expectation suffix is `expected nil, bool, byte, int, float, string, array or dict`. Because dictionary literal keys must be identifiers, a non-string-key JSON case must first construct the dictionary with bracket assignment; `@[1: 2]` is a syntax error before JSON encoding. `std.json.decode(string)` maps JSON back to Hush nil/bool/int/float/string/array/dict; malformed JSON returns an Error whose context is the original input. A non-string input panics.

## Spec 23

`std.regex(pattern)` compiles a case-sensitive, unanchored-by-default Rust-style regular expression and returns either a regex dictionary/object or an Error for invalid syntax. Supported constructs include literals and Unicode, `.`, escaped metacharacters, character classes/ranges/negation, `\d`, `\w`, `\s`, `\b`, `^`, `$`, capturing/noncapturing groups, alternation, `*`, `+`, `?`, `{n}`, and `{m,n}`. Dot does not match newline by default and quantifiers are greedy.

The object has methods `match(string)` (one argument, whether any match exists), `split(string)` (one argument, pieces in order without captured separators), and `replace(string, replacement)` (two arguments, replace every match). Split preserves boundary and consecutive empty pieces. Empty regex matches every boundary, splits `abc` into `[ "", "a", "b", "c", "" ]`, and replacement `X` produces `XaXbXcX`. Replacement with no match returns the input. Wrong method arity or non-string arguments panic.

## Spec 24

Command expressions use `{ commands }` for synchronous execution, `${ commands }` for captured execution, and `&{ commands }` for asynchronous execution. Inside, `;` separates commands and `|` constructs a pipeline. Commands are launched directly, without an intervening shell. Whitespace separates arguments. Single-quoted segments preserve literal content and spaces and recognize only `\'`, `\n`, `\t`, `\0`, and `\\`. Double-quoted segments preserve one argument, allow `$name`/`${name}` interpolation, and recognize `\"`, `\$`, `\n`, `\t`, `\0`, and `\\`. Unquoted segments also interpolate and allow a backslash before `#`, either quote, `>`, `<`, `?`, `;`, `$`, `=`, whitespace, `n`, `t`, `0`, or backslash. Adjacent quoted, literal, escaped, and interpolation parts concatenate into one logical argument.

Interpolating nil produces an empty argument; bool/int/float/char/string use unquoted scalar display suitable for argv. An array expands to zero or more arguments, one per element. Nested arrays, dictionaries, functions, and errors cannot be converted and panic; a nested array item uses `value (DISPLAY) has unexpected type, expected nil, bool, int, float, byte or string`. For example, interpolating `[ ["a", "b"], ["c", "d"] ]` reports `value ([ "a", "b" ]) has unexpected type, expected nil, bool, int, float, byte or string` at the interpolation expansion. An array expansion where a single item is required (program name, environment name, or redirect target) also panics. Empty arrays can therefore remove an argument. Unicode, embedded newlines, spaces, literal dollar signs, and backslashes must reach child argv intact.

## Spec 25

Unquoted command arguments support pathname expansion. `~/` at the beginning of an argument expands to the home directory. `*` matches zero or more path characters and `%` is Hush's one-character wildcard (corresponding to `?` in ordinary glob notation). Expansions can be combined with literal parts in a word. Quoting an expansion character makes it literal. Backslash escaping remains limited to the exact unquoted escape set in Spec 24: in particular, `\*` is not a literal-star spelling and is rejected as `invalid escape sequence '\*'.` Relative filesystem matches are emitted with a leading `./`; absolute patterns remain absolute. Multiple expanded arguments retain traversal order.

A leading `NAME=value` word on a basic command sets an environment variable only for that command. The name and value may contain legal interpolation. These assignments do not alter the interpreter environment. Ordinary assignment syntax outside command blocks remains the language assignment of Spec 9.

## Spec 26

Each basic external command yields either success or an Error. Status 0 is success. A nonzero child status becomes Error description `command returned non-zero` with context `@[status: integer, pos: "SOURCE (line L, column C)"]`. A signal status is encoded as signal number plus 255. A missing executable produces the exact Error description `No such file or directory (os error 2)`; the program name is not appended. Within a pipeline, all processes are waited for. One failure is returned directly; multiple failures produce Error description `Some commands failed in the pipeline` and an array of the component Errors as context. The reference counts the failure/pipe teardown in `${ echo test | false | cat }` as multiple failures, so its description is `Some commands failed in the pipeline`, not `command returned non-zero`. Likewise, `{ echo foo | cat | false | cat | cat > /dev/null; echo baz }` bails before `echo baz` and returns a context array of exactly two component Errors, each described as `command returned non-zero`. Across a semicolon-separated block, multiple failed pipelines similarly produce `Some commands failed in the block`.

By default, a command failure causes the remainder of that command block to be skipped. A trailing command `?` marks that basic command as allowed to fail so later commands continue, while its Error remains in the block result. Successful synchronous `{...}` writes child stdout/stderr directly to the corresponding interpreter streams and returns `nil`; failures return the Error value rather than changing the interpreter's exit status unless subsequently propagated/panicked.

Captured `${...}` does not stream child output. On full success it returns exactly a dictionary with `stdout` and `stderr` strings containing all captured bytes. On failure it returns the same Error description, but replaces its context with `@[stdout: captured_stdout, stderr: captured_stderr, error: original_context]`, preserving output produced before failure. Large simultaneous stdout/stderr streams (at least one megabyte each) must be drained without deadlock.

## Spec 27

Redirections are applied left-to-right and support `< path`, `<< value`, `> path`, `1> path`, `>> path`, `1>> path`, `2> path`, and descriptor duplication such as `2>1` and `1>2`. `<` reads a file. `<<` supplies the expanded argument's bytes followed by exactly one LF byte as stdin (there is no shell heredoc delimiter protocol). `>` creates/truncates, `>>` creates/appends. Multiple redirections on one command follow order-sensitive Unix descriptor semantics; redirections may occur on pipeline members, with pipes connecting stdout of one member to stdin of the next. An ampersand is not part of descriptor-duplication syntax: source `2>&1` is parsed as an ordinary redirection to the filename `&1` and its canonical AST form is `2>"&1"`.

Recognized stateful command builtins include `cd`, `exec`, `alias`, `exec0`, and `spawn0`. `{ cd path }` changes interpreter cwd and reports failures as Error values; a nonexistent path uses the exact description `No such file or directory (os error 2)`. `{ exec program args... }` replaces the interpreter process, so following Hush code is not run and the replacement's exit/output is the executable's. A stateful builtin in capture/async context, in a pipeline, or with unsupported redirection is a static error `use of built-in command in async context` or an equivalent builtin-context error.

## Spec 28

An asynchronous `&{...}` starts command execution concurrently, streams its output like a synchronous block, and immediately returns a dictionary with field `join`. Calling `result.join()` with no arguments waits and returns `nil` or the same Error structure a synchronous block would return. The join function is one-shot; calling it a second time panics with an invalid-join diagnostic. Static restrictions on command builtins apply before any asynchronous execution.

## Spec 29

Static errors use source locations and this exact outer form, one line per diagnostic:

```text
Error: SOURCE (line L, column C) - MESSAGE
```

Lines are one-based and columns are zero-based byte offsets from the start of that line. A location-free parser EOF diagnostic is `Error: unexpected end of file`. Runtime failures use:

```text
Panic in SOURCE (line L, column C): MESSAGE
```

All end in a newline. Diagnostics retained by a single analysis pass are emitted in source order, up to the implementation's 20-error cap, but the analyzer does not retain every independently detectable semantic error across a nonfinal top-level `return`. In particular, the exact source `missing\nreturn 1\nbreak\nself\n` emits only the line-3 `break statement outside loop` and line-4 `self keyword outside function` diagnostics; it omits the undeclared-name and return diagnostics from lines 1 and 2. By contrast, when `missing\nreturn 1` ends at that return, both diagnostics are emitted. Static message templates include `undeclared variable 'x'`, `duplicate variable 'x'`, `duplicate key 'x'`, `invalid assignment`, `return statement outside function`, `break statement outside loop`, `self keyword outside function`, `try operator outside function`, and `use of built-in command in async context`. Parser messages are `unexpected 'TOKEN', expected EXPECTATION`, `empty command block`, or location-free `unexpected end of file`. The identifier expectation is spelled `identifier`, not `id`, and expected punctuation/keywords are quoted, as in `expected '('` and `expected 'do'`.

Runtime message templates after the `Panic in LOCATION: ` prefix are exact:

- `integer overflow`, `division by zero`, `collection is empty`, and `assertion failed`;
- `index (DISPLAY) out of bounds`;
- `attempt to call (DISPLAY), which is not a function`;
- `incorrect amount of function parameters -- supplied N, expected M`;
- `condition (DISPLAY) is not a boolean`;
- `value (DISPLAY) has unexpected type, expected EXPECTED_TYPES`;
- `invalid value (DISPLAY), expected EXPECTATION`;
- `OBJECT expansion resulted in N items`;
- `unsupported file descriptor (N)`;
- `attempt to assign field (DISPLAY), which is readonly`;
- `failed to import module (PATH)`, where `PATH` is the unquoted resolved imported path; `attempt to call join more than once`; and `std.panic(DISPLAY)`.

For example, comparing an int with float `2.0` reports `value (2.0) has unexpected type, expected int`; adding strings reports `value ("a") has unexpected type, expected int or float`; and calling `std.assert()` reports `incorrect amount of function parameters -- supplied 0, expected 1`.

Diagnostic locations select the token/value that caused the error rather than merely the enclosing operator delimiter. The following observed cases fix the anchors precisely:

- in `let x = 1\nlet x = 2`, the duplicate declaration is at the second identifier, line 2 column 4;
- in `1 + 2 = 3`, `invalid assignment` is at `=`, line 1 column 6;
- in `let x = [][5]`, the bounds panic is at `5`, column 11, and in `x[-1]` it is at unary `-`, column 2;
- array, dictionary, and string bracket-access panics are anchored at the key/index expression, one byte after `[`: this gives column 2 for `x["key"]`, column 14 for `std.println(d["nonexistent"])`, and column 14 for `std.println(s[10])` in their respective observed lines;
- `let x = 1 > 2.0` anchors the mixed comparison at `2.0`, column 12, while `let x = "a" + "b"` anchors the invalid left operand at column 8.

Lexical recovery also reports precise causes, including the offending spelling where shown: `empty char literal.`, `invalid escape sequence '\q'.`, `unexpected 'b'.`, `invalid number 'TOKEN'.`, and `unexpected end of file.`. Recovery counts and locations are deterministic for these inputs:

- `std.println("unterminated string` reports `unexpected end of file.` at the physical EOF (line 1 column 32), followed by exactly two location-free `Error: unexpected end of file` lines;
- `let x = ''` reports `empty char literal.` at column 8, then one location-free EOF line;
- `let x = "\q"` reports exactly `invalid escape sequence '\q'.` at the backslash, column 9, with no follow-up;
- `let x = 999999999999999999999999999999` reports `invalid number '999999999999999999999999999999'.` at column 8, then one location-free EOF line;
- `for in [] {}` reports, in order, `unexpected 'in', expected identifier` at column 4, `unexpected '{', expected 'do'` at column 10, `empty command block` at column 11, then one location-free EOF line;
- `function {}` reports three column-9 lines for `unexpected '{'`, expecting `'('`, `identifier`, and `')'` respectively, then `empty command block` at column 10 and one location-free EOF line;
- `if then end` reports only `unexpected 'then', expected expression` at column 3.

No successful program output is emitted before static analysis completes, except the explicitly requested lex rendering.

## Spec 30

`--lex` writes a block beginning and ending with exactly 50 hyphens plus newline. Between them, every non-whitespace/non-comment token or lexer error appears in source order. A token line is:

```text
SOURCE (line L, column C):\tTOKEN_DISPLAY
```

The tab is one literal tab. Token display uses the canonical source spelling for keywords/operators/delimiters, composite delimiters `@[`/`${`/`&{`, and escaped quoted forms for strings/chars. Numeric values are normalized after parsing (`89e10` displays `890000000000`, `1.2e3` displays `1200`). Command argument tokens retain their segment quoting and normalized `${name}` expansion notation. A lexer error inside this stdout block is `Error: line L, column C - MESSAGE`. The same error also participates in stderr/static failure.

Empty input is exactly:

```text
--------------------------------------------------
--------------------------------------------------
```

For `let x = 1\n`, the complete block is:

```text
--------------------------------------------------
<stdin> (line 1, column 0):\tlet
<stdin> (line 1, column 4):\tx
<stdin> (line 1, column 6):\t=
<stdin> (line 1, column 8):\t1
--------------------------------------------------
```

## Spec 31

`--ast` prints a 50-hyphen separator, then `AST for SOURCE\n`, the canonical syntax tree, a newline, and another separator/newline. Empty input therefore has one blank line between its header and closing separator. Canonical formatting uses tabs for each indentation level, one statement per line, one space around binary operators, and parentheses around every unary/binary/try node: `(- 42)`, `(not true)`, `(value ?)`, `(a + b)`. Calls use `f(a, b)`; string-key access uses `.name`; other access uses `[expr]`. Named functions normalize to `let name = function(params)` followed by an indented body and `end`. `elseif` normalizes to an `else` containing a nested `if`.

Nonempty arrays and dictionaries are vertically formatted when they occur in normal indented context: opening delimiter, each item on a new indented line separated by commas, then the aligned `]`; empty forms remain `[]` and `@[]`. Identifier dictionary keys retain their bare spelling in canonical AST output: `@[user: value]` renders with `user:`, never `"user":`. This applies recursively and alongside access expressions. When embedded in an inline condition/call context the same structures use spaces and semicolons as dictated by recursively inline formatting. Strings/chars use double/single quotes and debug escapes. For the observed small-float case, source `0.00001` renders as `0.00001`, not `1e-05`; Program rendering inherits that spelling. Command blocks retain `{`, `${`, or `&{`, put each semicolon-separated pipeline on its own tab-indented line, quote every canonical argument, normalize `$x` to `${x}`, show pipeline ` | `, show explicit source descriptors (`>` becomes `1>`), and close on an aligned `}`. A recoverable missing AST node displays `***ill-formed***`.

For `let x = 1`, exact AST output is:

```text
--------------------------------------------------
AST for <stdin>
let x = 1
--------------------------------------------------
```

AST output is produced after syntactic analysis and before semantic evaluation; a syntactically valid but semantically invalid source can therefore have an AST block followed by stderr diagnostics.

## Spec 32

`--program` prints a 50-hyphen separator, `Program for SOURCE\n`, the canonical statically resolved program, a newline, and the closing separator/newline. Its expression/block formatting follows the AST rules, except identifiers are lexical frame slots `#N`, dot access remains dot access, and assignment lvalues with computed keys use brackets. Each function or root program has one frame: declarations in `if`/`else`, `while`, and `for` blocks do not begin nested slot numbering. Instead, all such declarations are hoisted into their containing function/root frame preamble and receive increasing slots in lexical source order, while their assignments remain inside the original blocks. A `for` loop variable is a declaration in that same containing frame. Root slot `#0` is always `std`. Thus `if true then let x = 1 end` declares root `let #1: auto` before the `if` and assigns `#1 = 1` inside it; `if`/`else` branch declarations use root slots `#1` and `#2`; and `for x in [1, 2, 3] do let y = x end` declares root slots `#1` and `#2`, renders `for #1 ...`, and assigns `#2 = #1` in the body. Source `let` statements become frame declarations plus later assignments, so `let x = 42` is exactly:

```text
--------------------------------------------------
Program for <stdin>
let #0: auto
let #1: auto
#1 = 42
--------------------------------------------------
```

A compiled function header is `function(PARAMETER_COUNT)`. Its local frame starts at `#0` for the first parameter and includes all parameters/locals as `auto`; a captured outer slot is declared `let #to: capture #from`; if needed, a slot declaration ends in ` self`. Captures and slots are assigned in first lexical-use/declaration order. The function's declarations precede its executable statements, and a blank line remains between an empty frame-declaration area and its body. For example, `function foo() return 42 end` compiles as a root slot assignment to:

```text
#1 = function(0)

	return 42
end
```

Program command interpolation replaces names by slots, such as `${#1}`. All static validation must precede this renderer; no Program block is produced when semantic analysis fails. Program output precedes execution and still appears under `--check`.

## Spec 33

The implementation must be robust under the observable workloads: strings of at least 1,000 bytes, command captures exceeding one megabyte on both streams, arrays with 10,000 elements, dictionaries with 1,000 keys, at least 100 function parameters, nested containers at least 15 levels deep, and ordinary recursion to 1,000 calls. It must not hang on empty stdin, exhausted iterators, empty ranges, empty expansions, failed pipelines, or concurrent output.

The reference runtime uses the native process stack. Recursion around 10,000 calls is expected to abort with signal 6 (subprocess return code `-6`) and stderr containing both a line matching `thread 'main' (DIGITS) has overflowed its stack` and `fatal runtime error: stack overflow, aborting`. This low-level abort is distinct from the handled exit-127 runtime panics above.
