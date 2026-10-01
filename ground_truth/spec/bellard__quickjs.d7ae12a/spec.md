# QuickJS-compatible executable specification

The deliverable is one executable file named exactly `executable`. It is a command-line JavaScript interpreter whose observable behavior is compatible with QuickJS 2025-09-13 for the features described below. This document defines the required surface; no source tree, compiler, helper executable, or preinstalled JavaScript runtime is part of the deliverable. Files, modules, shell commands, and standard input named by an invocation are harness-provided inputs.

Unless a requirement says otherwise, successful execution exits with status 0, writes program output to standard output, and leaves standard error empty. Uncaught compile-time or run-time exceptions exit with status 1 and are written to standard error. Output comparisons are byte-for-byte, including spaces and final newlines.

## Spec 1

The executable shall accept either inline source or a source filename. `-e EXPR` and `--eval EXPR` evaluate all of `EXPR`, including multiline text. A positional `.js` or `.mjs` file is decoded as UTF-8 and executed. An empty file succeeds silently. A missing source file exits nonzero and reports that the file could not be loaded. Script execution must be general-purpose: the source and filenames are not fixed in advance, and scripts may create, inspect, rename, and remove files in their current working directory and `/tmp`.

The global `scriptArgs` is an array. For file execution its first element is the filename exactly as supplied and subsequent elements are the remaining command-line arguments; with no extra arguments its length is one. `--` stops option recognition and is itself retained among the script arguments, as are later strings beginning with `-`. Options may occur on either side of `--eval` and its expression where unambiguous.

## Spec 2

The supported command-line options and aliases are:

```
-h, --help
-e, --eval EXPR
-i, --interactive
-m, --module
--script
--strict
-I, --include FILE
--std
-T, --trace
-d, --dump
--memory-limit N
--stack-size N
--no-unhandled-rejection
-s
--strip-source
-q, --quit
```

Bundled no-argument short options such as `-dT` are accepted. Repeated `-I`/`--include` options are processed left to right. Unknown options print `qjs: unknown option '<option>'` to standard error, print the help text to standard output, and exit 1. A missing `-e` value exits 2 with `qjs: missing expression for -e`. A missing `-I`/`--include` filename exits 1, writes exactly `expecting filename` to standard error, and does not append a newline. Missing memory or stack values exit 1 with respectively `expecting memory limit` or `expecting stack size`.

## Spec 3

`-h` and `--help` print exactly the following text to standard output, nothing to standard error, and exit 1:

```
QuickJS version 2025-09-13
usage: qjs [options] [file [args]]
-h  --help         list options
-e  --eval EXPR    evaluate EXPR
-i  --interactive  go to interactive mode
-m  --module       load as ES6 module (default=autodetect)
    --script       load as ES6 script (default=autodetect)
    --strict       force strict mode
-I  --include file include an additional file
    --std          make 'std' and 'os' available to the loaded script
-T  --trace        trace memory allocation
-d  --dump         dump the memory usage stats
    --memory-limit n  limit the memory usage to 'n' bytes (SI suffixes allowed)
    --stack-size n    limit the stack size to 'n' bytes (SI suffixes allowed)
    --no-unhandled-rejection  ignore unhandled promise rejections
-s                    strip all the debug info
    --strip-source    strip the source code
-q  --quit         just instantiate the interpreter and quit
```

The closing newline is required.

## Spec 4

`-q`/`--quit` initializes and destroys a runtime without evaluating inline source. It succeeds silently unless combined with diagnostics. `-d`/`--dump` appends a QuickJS-style memory report containing at least the headings/fields `QuickJS memory usage`, `JSRuntime`, `JSContext`, `memory allocated`, `atoms`, and `objects`. When `-q -d` is used, the report ends with a timing line of the form `Instantiation times (ms): 0.069 = 0.014+0.038+0.000+0.017`: the value before `=` is a decimal numeric total, followed by four decimal component values separated by `+`.

`-T`/`--trace` emits allocation, reallocation, and free trace records to standard output. Allocation lines have the exact shape `A <decimal-size> -> H<signed-decimal-offset>.<decimal-usable-size>`. Trace and dump modes compose, including when their short flags are bundled.

## Spec 5

`--memory-limit` and `--stack-size` accept nonnegative decimal quantities, including fractional values, optionally followed by uppercase `K`, `M`, or `G`, multiplying by 2^10, 2^20, or 2^30. The suffixes are case-sensitive: for example, `1.5M` is accepted but `1.5m` exits 1 with `qjs: invalid suffix: m`. Zero means unlimited. Any other suffix, for example `X`, exits 1 with `qjs: invalid suffix: X`.

A 10 KiB memory limit must fail runtime-context creation, exit 2, and print exactly `qjs: cannot allocate JS context`; 100 KiB permits a trivial context, 1.5 MiB permits trivial execution, and 10 GiB behaves normally. Runtime allocation beyond a real limit throws/reports `InternalError: out of memory`. Stack limits are enforced: unbounded recursion under either 10 KiB or 1 MiB is catchable as an `InternalError`, while ordinary calls work with 256 KiB. Deep recursion without an explicit limit must fail safely with a catchable stack-overflow `InternalError`, never crash the process.

## Spec 6

Plain `.js` input defaults to script semantics unless import/export syntax triggers module autodetection. `.mjs` always autodetects as a module. `-m`/`--module` forces module parsing for files and inline source, while `--script` forces script parsing and rejects import/export syntax. Modules are strict by default. `--strict` prepends strict semantics to scripts and inline source: implicit global assignment, writes/deletes forbidden by property attributes, duplicate parameters, legacy octal syntax/escapes, assignments to `eval`/`arguments`, and `with` are rejected as appropriate. Without strict mode, sloppy implicit globals, mapped arguments, duplicate simple parameters, and `with` work.

Each `-I FILE` is evaluated as a script before the main source, in a shared global environment, so later includes and the main source can see global properties it creates. Includes also work when the main source is a module. Missing includes produce a nonzero load error. `-s` strips debug location information from generated stack traces; normal mode retains filenames, lines, and columns. `--strip-source` must not remove those locations.

## Spec 7

The lexical grammar supports UTF-8 source, Unicode identifiers, comments, automatic semicolon insertion, decimal/binary/octal/hex integer literals, numeric separators where valid, floating-point and exponent literals, BigInt literals ending in `n`, string escapes, Unicode code-point escapes, regular-expression literals, and template literals. It must distinguish division from a regular-expression literal by syntactic context.

Malformed source is rejected before execution with `SyntaxError`, a useful message, and source location. Covered malformed cases include unterminated strings/comments/regex/templates and delimiters, invalid escapes and identifiers, illegal numeric forms, duplicate lexical declarations/exports/default switch clauses/group names/private names, invalid labels, misplaced `break`/`continue`/`return`/`yield`/`await`/`super`/`new.target`/`import.meta`, rest parameters not last, uninitialized `const`, invalid class constructors, and incomplete `try`. If several errors exist, report the first in source order.

## Spec 8

Implement JavaScript declarations and lexical environments: `var`, `let`, `const`, function and class declarations; block/function/global/module/catch/switch/loop scopes; hoisting; temporal dead zones; shadowing; redeclaration checks; and per-iteration `let` bindings. Closures retain captured mutable and immutable variables for their full lifetime through nested calls, callbacks, generators, async functions, and dynamically created functions.

Direct `eval` executes in and may access its caller's lexical environment, while indirect eval executes globally. Strict eval does not leak new bindings. Eval returns the last expression value, reports syntax errors normally, uses the appropriate `this`, and can create closures over visible bindings. `globalThis` is the actual global object; its mutations are visible through global name resolution. Arrow functions capture lexical `this`, `arguments`, and surrounding bindings; ordinary functions receive dynamic `this` according to strict/sloppy call rules.

## Spec 9

The value model includes `undefined`, `null`, booleans, IEEE-754 binary64 Numbers (with NaN, infinities, subnormals, +0 and -0), arbitrary-precision BigInts, UTF-16 Strings, unique Symbols, and objects. Implement `typeof`, `instanceof`, `in`, `delete`, `void`, conditional expressions, comma expressions, property access, optional chaining, `new`, and function calls with their JavaScript results and evaluation order.

Truthiness is false only for `undefined`, `null`, false, +0, -0, NaN, 0n, and the empty string. Strict equality treats signed zeros as equal and NaN as unequal; `Object.is` distinguishes signed zeros and equates NaN. Loose equality and relational comparison perform the tested string/number/boolean/null/BigInt/object conversions, including unusual arrays and whitespace strings. Logical `&&`, `||`, `??`, optional chaining, ternary expressions, and their assignment forms short-circuit and evaluate side effects exactly once. Mixing `??` directly with `&&` or `||` without parentheses is a syntax error.

## Spec 10

Implement abstract conversion behavior throughout operators, built-ins, descriptors, and property keys. Primitive conversion uses `Symbol.toPrimitive` with the proper hint, then `valueOf`/`toString` in hint-dependent order; returning only objects throws `TypeError`, and user exceptions propagate. Symbols remain Symbols as property keys, explicit `String(symbol)` works, and implicit numeric/string concatenation conversions that forbid Symbols throw.

String-to-number conversion recognizes trimmed decimal, exponent, hexadecimal, binary, octal, Infinity, empty/whitespace strings, and produces NaN for invalid or incomplete forms. Integer/index/length conversions truncate finite fractions where required, preserve or normalize signed zero where required, and correctly handle NaN and infinities. Operators perform conversion in left-to-right observable order. BigInt/Number mixtures are allowed only for comparisons and specified explicit conversions; arithmetic mixtures throw.

## Spec 11

Implement all arithmetic and assignment operators: unary `+ - ~ !`, `+ - * / % **`, increment/decrement, signed and unsigned shifts, 32-bit bitwise operations, comparisons, equality, and compound/logical assignments. Number operations use binary64 edge behavior, including NaN propagation, infinity arithmetic, signed-zero division/remainder, overflow, underflow, and exponentiation corner cases. Bitwise Number operands convert to 32-bit words, shifts mask their count to five bits, and `>>>` returns an unsigned 32-bit result. Exponentiation is right-associative and binds correctly relative to unary operators.

Spread/rest and destructuring work in array/object literals, calls, parameters, declarations, assignments, loops, catch bindings, generators, and nested patterns. Defaults are lazy and apply only to `undefined`; object spread copies own enumerable string and Symbol keys in order; later properties override earlier ones. Iterator cleanup depends on the point of abrupt completion: if the first `next()` result reports `done: false` but its `value` getter throws `9`, array destructuring propagates `9` without invoking the iterator's `return`, so printing the caught value and a `return`-incremented close counter produces `9 0`. In the following object-default check, a getter that returns `undefined` is read once and the default `7` is used, producing `7 1` after that first line.

## Spec 12

Functions support declarations, expressions, named expressions, arrows, default/rest/destructured parameters, methods, getters/setters, async and generator forms, recursion, and the `Function` constructor. Function objects expose correct `name`, `length`, `prototype`, and printable `toString` forms. `call`, `apply`, and `bind` implement receiver selection, array-like argument lists, partial application, bound-function chaining, constructor forwarding/new-target behavior, and suitable bound names/lengths. Calling noncallables or constructing nonconstructors (including arrow functions) throws `TypeError`.

The non-strict `arguments` object aliases simple named parameters; strict arguments do not. Missing and extra arguments, `callee` restrictions, rest arrays, and interaction with defaults behave normally. Getter/setter receiver bindings, exceptions, recursive access, and method shorthand are observable and correct.

## Spec 13

Control flow includes blocks, `if`, `switch`, conditional expressions, `while`, `do`, classic `for`, `for-in`, `for-of`, labeled statements, and correctly targeted `break`/`continue`. `for-in` enumerates enumerable string keys across a prototype chain without duplicates according to property enumeration rules. `for-of` consumes the iterator protocol and closes iterators by calling `return` on early break, return, destructuring failure, or exceptions.

`try`, `catch`, and `finally` preserve execution order under nesting. `finally` always runs and its `return` or thrown value overrides an earlier completion. Any JavaScript value, including null, undefined, numbers, strings, Symbols, and plain objects, can be thrown and is caught without coercion or loss of identity.

## Spec 14

Classes support declarations/expressions, named and anonymous classes, instance/static methods, getters/setters, public fields, computed names, static initialization blocks, `extends`, `super()` and `super.property`, and `new.target`. Derived construction initializes `this` only after `super`; missing/illegal super calls throw. Constructor return-value rules distinguish base and derived classes and object versus primitive returns. Static and instance namespaces remain separate, inheritance chains work over multiple levels, and classes cannot be called without `new`.

Private instance/static fields, methods, getters, and setters implement lexical private names and brand checking. Support `#name in object`, initialization order, updates, nested classes, inheritance isolation, async methods, closures, destructuring around private values, and proxy receivers. Duplicate/undeclared private names, private names in object literals, deletion, or access with the wrong brand fail with the correct SyntaxError or TypeError. Private state is omitted by ordinary reflection, spread, and JSON serialization.

## Spec 15

Objects use prototype-based property lookup and support ordinary, null-prototype, primitive-wrapper, function, error, date, regex, arguments, String-exotic, Array-exotic, typed-array-exotic, Proxy, and module-namespace objects. Object literals support shorthand, methods, accessors, computed keys, `__proto__`, spread, and duplicate-key overwrite semantics.

Implement `Object.create`, `getPrototypeOf`, `setPrototypeOf`, `isPrototypeOf`, `assign`, `keys`, `values`, `entries`, `fromEntries`, `getOwnPropertyNames`, `getOwnPropertySymbols`, `hasOwn`, `hasOwnProperty`, `propertyIsEnumerable`, and `getOwnPropertyDescriptors`. Numeric-index keys precede other string keys; other strings retain insertion order; Symbols come last for own-key reflection. Prototype changes affect subsequent lookup, circular chains are rejected, and null prototypes do not inherit Object methods.

## Spec 16

Property descriptors distinguish data (`value`, `writable`) and accessor (`get`, `set`) forms plus `enumerable` and `configurable`; omitted fields use the correct defaults. `Object.defineProperty`, `defineProperties`, legacy `__defineGetter__`/`__defineSetter__` and lookup methods, and corresponding Reflect operations validate descriptor objects and callable accessors. Mixing data and accessor members is invalid. Non-configurable properties enforce all transition invariants; writable may change true-to-false but not back. Getter/setter calls use the actual receiver and propagate exceptions.

Implement `preventExtensions`, `seal`, `freeze`, `isExtensible`, `isSealed`, and `isFrozen`. They prevent additions and/or lock descriptors without incorrectly freezing values returned by accessors. Strict forbidden writes/deletes throw; sloppy forbidden writes fail silently. `Object.assign` invokes source getters and target setters and creates ordinary enumerable writable configurable data properties where appropriate.

## Spec 17

Arrays are exotic indexed objects. Their `length` is a non-enumerable uint32-related property: index writes grow it; shrinking deletes configurable trailing indices; a non-configurable trailing index blocks shrink; invalid, negative, fractional, 2^32-or-larger assigned lengths throw `RangeError`; index `4294967295` is an ordinary property. Sparse holes are distinct from explicit `undefined`, are skipped or preserved as required, and use the indexed sparse display form specified in Spec 38.

Support Array construction and `isArray`, `from`, `of`, `at`, `with`, `push`, `pop`, `shift`, `unshift`, `splice`, `slice`, `concat`, `join`, `toString`, `toLocaleString`, `reverse`, stable `sort`, `fill`, `copyWithin`, `flat`, `flatMap`, `map`, `filter`, `reduce`, `reduceRight`, `forEach`, `every`, `some`, `find`, `findIndex`, `findLast`, `findLastIndex`, `includes`, `indexOf`, `lastIndexOf`, `keys`, `values`, and `entries`. Methods honor generic array-like receivers, callback `thisArg`, mutation during iteration, species construction, `Symbol.isConcatSpreadable`, NaN/signed-zero matching rules, negative/from indices, empty-array reductions, holes, and readonly length failures.

## Spec 18

Strings are immutable sequences of UTF-16 code units. `length`, bracket access, `charAt`, `charCodeAt`, `codePointAt`, `at`, `fromCharCode`, and `fromCodePoint` correctly distinguish code units, surrogate pairs, lone surrogates, and code points. String iteration and spread yield Unicode code points (a valid surrogate pair together), not grapheme clusters; indexing/slicing still use code-unit offsets.

Support `concat`, `repeat`, `padStart`, `padEnd`, `trim`, `trimStart`, `trimEnd`, `slice`, `substring`, legacy `substr`, `split`, `replace`, `replaceAll`, `search`, `match`, `matchAll`, `indexOf`, `lastIndexOf`, `includes`, `startsWith`, `endsWith`, locale comparison, case and locale-case conversion, `normalize`, `toString`, and `valueOf`. `String.raw` joins a template object's raw segments with converted substitutions without interpreting escapes. Implement edge conversions for missing, negative, huge, NaN, and infinite arguments; reject negative/infinite repeat counts; preserve embedded NUL/control characters; and handle very long concatenation/rope strings without incorrect equality, hashing, slicing, collection keys, switch matching, or stack growth.

## Spec 19

Unicode behavior includes normalization forms NFC, NFD, NFKC, and NFKD; omitted form means NFC and an unknown form throws `RangeError`. Handle combining marks, Hangul, compatibility characters, CJK, Arabic, multilingual case mappings, emoji, variation selectors, modifiers, ZWJ sequences, supplementary planes, and invalid/lone surrogates. Locale arguments do not enable Turkish-specific casing: `"i".toLocaleUpperCase("tr")` is `"I"`, and `"I".toLocaleLowerCase("tr")` is `"i"`. Unicode whitespace is recognized by trim and language whitespace rules.

Regular expressions in `u` mode support Unicode code points and property escapes for general categories, composite categories, scripts, script extensions, binary/derived properties, identifier properties, whitespace, case properties, emoji-related properties, negation, rare scripts, and supplementary-plane boundaries. Property names/values are case-sensitive as JavaScript requires.

## Spec 20

Regular expressions support literal and `RegExp` construction, legacy `compile`, source/flags, `g i m s u y d`, lastIndex, `exec`, `test`, and Symbol-based match/search/replace/split protocols. Implement character classes and ranges, dot/dotAll, anchors, word boundaries, escapes, alternation, greedy/non-greedy quantifiers, captures, noncapturing groups, numbered/named backreferences, positive/negative lookahead and lookbehind, nested patterns, zero-width and empty matches, has-indices results and named group indices. `RegExp.escape(string)` returns text safe as a literal pattern: the first ASCII alphanumeric is hex-escaped, regex and punctuator metacharacters are escaped, control whitespace uses `\t`, `\n`, and `\r`, Latin-1 non-ASCII may use `\xHH`, and other Unicode characters remain valid Unicode; examples are `RegExp.escape("abc123") === "\\x61bc123"` and `RegExp.escape("a-b=c<d>e") === "\\x61\\x2db\\x3dc\\x3cd\\x3ee"`.

String replacement expands `$$`, `$&`, ``$` ``, `$'`, numbered and named captures and calls replacement functions with the proper arguments. Global/sticky `lastIndex` advances and resets correctly, including empty matches. `matchAll` requires a global regular expression and returns an iterator. Invalid patterns, ranges, duplicate/incompatible/unknown flags, and invalid group definitions throw `SyntaxError`; wrong RegExp receivers throw `TypeError`. Long inputs and nested backtracking must finish safely for tested patterns.

## Spec 21

Numbers and Number objects implement constants (`NaN`, infinities, epsilon, min/max values, safe integer bounds), conversion, `isNaN`, `isFinite`, `isInteger`, `isSafeInteger`, `parseInt`, `parseFloat`, `toString(radix)`, `toFixed`, `toExponential`, and `toPrecision`. Global `isNaN`/`isFinite` coerce while Number versions do not. Radices 2 through 36 work and others throw. Formatting handles rounding, boundaries, signed zero, very large/small magnitudes, omitted arguments, and allowed precision ranges.

`Math` includes the ordinary constants and arithmetic, power, square/cube roots, rounding, sign, min/max, random, logarithmic, exponential, trigonometric, inverse, hyperbolic, `atan2`, `hypot`, `imul`, `clz32`, `fround`, `trunc`, `expm1`, `log1p`, `log2`, and `log10`. It observes NaN/infinity/signed-zero rules. Also provide `Math.sumPrecise(iterable)` with precision sufficient to recover cancellation-sensitive sums and `Math.f16round` with IEEE binary16 rounding.

## Spec 22

BigInts have arbitrary precision and support decimal/base-prefixed literals, `BigInt(value)`, string conversion in radices 2–36, comparison, `+ - * / % **`, unary minus, `++`/`--`, and infinite-width signed two's-complement `& | ^ ~ << >>`. Division truncates toward zero; division/modulo by zero and negative exponents throw `RangeError`; unsigned right shift and unary plus throw `TypeError`. Large positive/negative shifts and bit masks must not truncate to machine word size. `BigInt.asIntN`/`asUintN` and BigInt typed arrays use modulo 2^N wrapping. Number arithmetic mixed with BigInt throws rather than silently converting. Math functions reject BigInts.

## Spec 23

Symbols are unique primitives. Implement `Symbol(description)`, description, explicit string conversion, `toString`, `valueOf`, global `Symbol.for`/`keyFor`, Symbol property keys, and all tested well-known Symbols: iterator, asyncIterator, toStringTag, toPrimitive, hasInstance, isConcatSpreadable, species, match/search/replace/split, and unscopables. `new Symbol` is invalid. Symbol keys are absent from `for-in`, `Object.keys`, and JSON, but present in own-symbol/Reflect key APIs. Well-known hooks alter iteration, coercion, instanceof, concatenation, species construction, string dispatch, and `with` lookup as indicated by their names.

## Spec 24

The synchronous iterator protocol uses an object with callable `next` returning `{value, done}`; malformed iterators/results and noniterables throw `TypeError`. Built-in arrays, strings, typed arrays, Sets, Maps, and generators are iterable. Iterator objects return themselves from `[Symbol.iterator]`. Abrupt consumers invoke iterator `return` when required and preserve the original completion appropriately.

Provide `Iterator.from` and iterator-helper methods `map`, `filter`, `take`, `drop`, `flatMap`, `reduce`, `some`, `every`, `find`, `forEach`, and `toArray`. Helpers are lazy except terminal operations, pass value and zero-based index to callbacks, short-circuit terminal predicates, close sources on early completion/errors, and accept arrays, strings, Sets, Maps, generators, custom iterables, and existing iterators. One reference edge case is required: consuming `Iterator.from([1,2,3,4]).map((x,i)=>(calls++,x)).filter(x=>x%2).take(2)` with `toArray()` invokes the map callback three times and then throws `TypeError: not a function` while attempting to close the composed helper. Callback arguments must be callable. `take`/`drop` coerce and truncate counts, reject negative counts, and accept Infinity. Empty and no-initial-value reduction behavior matches Array reduction.

## Spec 25

Generators implement `function*`, generator methods, `yield`, `yield*`, and `{next, throw, return}` state transitions. The first `next` argument is ignored; later values become results of suspended yield expressions. Completion records contain the final return value. Calls before start and after completion, injected throws, catches/finally blocks, and `return` through a yielding `finally` all work. `yield*` delegates next/throw/return to arrays, generators, and custom iterators and propagates the delegate's return value and errors.

Async generators implement the same protocol with each operation returning a Promise, await internally, serialize queued requests, expose `[Symbol.asyncIterator]`, and correctly handle early return/throw, yielded finally blocks, async delegation, and wrapping of synchronous iterators.

## Spec 26

Promises run their executor synchronously and reactions as jobs after current synchronous code. Resolution assimilates thenables and nested promises, settles only once, detects circular resolution, and turns executor/handler exceptions into rejections. Implement `then`, `catch`, and `finally`; nonfunction handlers pass through, returned promises are flattened, catch can recover, and finally preserves the outcome unless it throws or returns a rejected promise.

Implement `Promise.resolve`, `reject`, `all`, `race`, `allSettled`, and `any`, including subclass constructors, arbitrary iterables, strings/Sets/Maps/generators, empty inputs, immediate values, thenables, iterator failures, and input-order preservation independent of settlement order. `any` rejects with `AggregateError` containing ordered reasons when all reject. Invalid receivers, executors, resolve methods, or noniterable inputs throw TypeError. Drain all pending jobs before normal process exit.

## Spec 27

Async functions/methods/arrows always return Promises; return values are wrapped, thrown values reject, and `await` assimilates values/thenables and resumes with fulfillment or throws the rejection. Support multiple/nested awaits, loops, try/catch/finally, class/object methods, async IIFEs, concurrent combinators, and `for await` over async or synchronous iterables with correct break/continue/close/error behavior.

By default, a still-unhandled rejection makes the process exit 1 and prints `Possibly unhandled promise rejection: <QuickJS-formatted reason>` to standard error (for the string `test error`, the reason is printed as `"test error"`). `--no-unhandled-rejection` suppresses this diagnostic and allows status 0. A rejection that receives a handler is not reported.

## Spec 28

Static modules support named/default declarations and expressions, combined default plus named imports, namespace imports, aliases, side-effect-only imports, `export {}`, renamed re-exports, `export *`, and default re-export. Imported bindings are read-only live bindings, module top-level bindings are isolated, dependencies execute before importers, and a module instance executes once even if imported repeatedly. Circular dependencies are linked without recursion or duplicate execution. Namespace objects contain all named exports plus a `default` key when present; exports are enumerable live properties, the object is nonextensible and sealed but reports the tested live-binding descriptors, assignment through it cannot mutate an export, and `Symbol.toStringTag` is `Module`.

`import.meta` exists only in modules. It is a distinct extensible ordinary object per module with initial enumerable writable properties `url` and `main`; `url` is an absolute `file:///...` URL for that module, `main` identifies the entry module, and user code may add properties or replace `url`.

Resolve relative specifiers from the importing file, normalize `.`/`..`, and require the written extension rather than trying `.js`. Deep and circular chains and nested directories work. Missing modules report a load `ReferenceError`; nonexistent named exports and duplicate exports are link/parse `SyntaxError`s. Dynamic `import(expression[, options])` returns a Promise, works in expressions/functions/loops, shares the module cache, and rejects load/link/evaluation errors.

## Spec 29

JSON files can be imported as modules with a default export of parsed JSON. Static import attributes accept `with { type: "json" }`; the supported JSON5 form is selected only with `type: "json5"` and admits tested comments/trailing/extended syntax. A JavaScript source file imported with a JSON type produces the tested module error rather than silently changing language. For dynamic imports of a `.json` file, the string value of the `type` attribute is not used to reject or select the loader: `"json"`, `"module"`, `"text"`, `""`, `"日本語"`, and an omitted type all load the file as JSON.

Dynamic import's second argument is either undefined or an object. Its own `with` property is read exactly once; if present it must yield an object. Only own enumerable string keys from that attributes object participate; inherited, Symbol, and non-enumerable keys are ignored. Attribute keys and values are validated: values must be strings; only supported names (not arbitrary empty, whitespace, numeric, Unicode, or special-character names) are accepted; key matching is case-sensitive; getter/proxy side effects and exceptions propagate. Reimports of the same `.json` path with `type: "json"`, `type: "module"`, and no type share the same default-export value.

## Spec 30

`Proxy` and `Proxy.revocable` support callable and constructable targets and all traps: get/set, has, deleteProperty, ownKeys, getOwnPropertyDescriptor, defineProperty, get/setPrototypeOf, isExtensible, preventExtensions, apply, and construct. Pass the exact target/key/value/receiver/newTarget arguments, use Reflect-compatible fallback when a trap is absent, propagate trap exceptions, and support nested proxy chains without native stack crashes.

Enforce proxy invariants for nonconfigurable properties, nonextensible targets, frozen data/accessor properties, own-key completeness/uniqueness, descriptor compatibility, prototype/extensibility reports, false set/define/delete results in strict contexts, and construct traps returning objects. Revocation makes every operation throw TypeError. Constructors reject null/nonobject targets and handlers.

`Reflect` provides `apply`, `construct`, `defineProperty`, `deleteProperty`, `get`, `set`, `has`, `ownKeys`, `getOwnPropertyDescriptor`, `getPrototypeOf`, `setPrototypeOf`, `isExtensible`, and `preventExtensions`, returning booleans where Reflect specifies rather than throwing for an ordinary rejected mutation. It honors receiver and newTarget and validates target/callable/constructor requirements.

## Spec 31

`Map` and `Set` support construction from iterables, size, insertion-order iteration, keys/values/entries, `[Symbol.iterator]`, `forEach`, chained `set`/`add`, get/has/delete/clear, and mutation while iterating. Equality is SameValueZero: NaN equals NaN and +0/-0 denote the same key; object and Symbol keys use identity. Map distinguishes a missing key from a present key whose value is undefined. Constructor iteration calls the instance's `set`/`add` method and closes iterators on failure. Invalid entries, callbacks, iterables, and incompatible method receivers throw TypeError.

## Spec 32

`WeakMap` and `WeakSet` implement iterable construction and get/has/set/add/delete with weakly held keys. Object, function, and non-global Symbol keys/values are accepted; strings, numbers, null, and undefined are rejected where a key/value is required. Query methods with omitted invalid keys return false/undefined when that operation calls for a query rather than insertion. Constructors use overridable `set`/`add` and validate each iterable entry. Methods reject incompatible receivers.

`WeakRef` requires `new` and an object or eligible Symbol target and `deref` returns the live target. `FinalizationRegistry` requires `new` and a callable cleanup callback; `register(target, heldValue, token)` validates target/token, forbids target===heldValue, returns undefined, and supports multiple registrations; `unregister(token)` returns a boolean. Wrong receivers and primitive targets/tokens throw. Collection behavior must remain safe under explicit `std.gc()`, cycles, and allocation pressure. In the tested WeakRef lifetime, repeated `deref()` calls return the live target while its strong reference exists; after that reference is set to null and `std.gc()` returns, `deref()` immediately returns `undefined`.

## Spec 33

Implement `ArrayBuffer`, resizable buffer properties where supported by the tested syntax, `SharedArrayBuffer`, `DataView`, and typed arrays `Int8Array`, `Uint8Array`, `Uint8ClampedArray`, `Int16Array`, `Uint16Array`, `Int32Array`, `Uint32Array`, `Float16Array`, `Float32Array`, `Float64Array`, `BigInt64Array`, and `BigUint64Array`. Construction works from lengths, buffers with offsets/lengths, iterables, arrays, and other typed arrays; views share storage where required. Expose buffer, byteOffset, byteLength, length, BYTES_PER_ELEMENT, `ArrayBuffer.isView`, and iterable methods.

DataView reads/writes signed/unsigned integers, BigInts, float16/32/64 with endianness and boundary validation. Typed array conversion wraps integer values, clamps Uint8Clamped values, rounds floating types, preserves NaN/infinities/signed zero, and requires BigInts for BigInt arrays. Support `set`, `slice`, `subarray`, `copyWithin`, `sort`, `map`, `filter`, `find`, iteration, `at`, `includes`, and index searches. Sorting is numeric with NaN last and -0 ordered before +0 where observable.

## Spec 34

Typed arrays implement integer-indexed exotic rules. Valid in-range canonical numeric index keys denote fixed enumerable writable elements that cannot be reconfigured or deleted; defining them permits only compatible descriptor flags. Out-of-range, negative, `-0`, NaN, Infinity, fractional canonical numeric strings, and huge indices do not create indexed elements, while nonnumeric strings and Symbols are ordinary properties when extensibility permits. BigInt property keys first undergo property-key conversion: `1n` becomes `"1"`, so `Object.defineProperty(array, 1n, { value: 99 })` updates typed-array element 1. `Object.defineProperty` and ordinary assignment differ in their specified failure/throw behavior. Enumeration and descriptors reflect the fixed indices in order.

Reject negative/excessive/misaligned lengths and offsets and out-of-bounds DataViews. Detached buffers invalidate element definitions/access as required. Freezing a nonempty typed array fails. `Object.seal` on a nonempty typed array throws `TypeError: invalid descriptor flags`; despite throwing, it has made the array non-extensible, while `Object.isSealed` remains false. By contrast, sealing a zero-length typed array returns normally and makes `Object.isSealed` true. Preventing extensions follows the same integer-index invariants. All element types, prototype properties, and conversion overflow are covered.

## Spec 35

`JSON.parse` supports all valid JSON primitives/arrays/objects, Unicode escapes, large objects, deep tested nesting, and an optional reviver applied bottom-up with deletion/replacement semantics. Invalid/trailing/incomplete syntax throws `SyntaxError`. `JSON.stringify` implements object/array traversal, insertion ordering, string escaping, `toJSON`, replacer function or property list, indentation (number/string truncated as required), wrapper primitives, and cycle detection.

Undefined/functions/Symbols are omitted in objects, become null in arrays, and stringify to undefined at top level. Nonfinite Numbers stringify as null. BigInt without an overriding serialization throws TypeError. Getters/proxies and replacers execute in observable order and exceptions propagate. Provide `JSON.rawJSON` and `JSON.isRawJSON`. Primitive JSON texts such as `1`, `true`, `null`, and `"x"` are accepted and embedded without quoting; compound array or object texts such as `[1,2]` and `{"x":1}` are rejected with `SyntaxError: invalid rawJSON string`.

## Spec 36

`Date` supports construction from no arguments, milliseconds, date strings, and components; `Date.now`, `parse`, and UTC; local and UTC getters/setters; arithmetic/value conversion; ISO/JSON/string formatting; deprecated `getYear`/`setYear`; leap dates, rollovers, negative and boundary timestamps, and invalid dates. Invalid dates carry NaN; most display methods return the invalid-date form while `toISOString` throws RangeError. Date's default primitive hint prefers string. Date prototype methods validate their internal receiver.

## Spec 37

Provide `Error`, `EvalError`, `RangeError`, `ReferenceError`, `SyntaxError`, `TypeError`, `URIError`, `AggregateError`, and `InternalError` with correct prototype hierarchy, `name`, `message`, optional `cause`, writable properties, `toString`, `instanceof`, and stack. Uncaught errors are formatted as `<Name>: <message>` followed by QuickJS-style frames such as `    at function (file:line:column)`; eval source uses `<cmdline>` and an `<eval>` frame. Preserve call chains and source locations unless `-s` was used. Throwing a primitive prints an appropriate QuickJS representation.

Receiver/type/range failures throughout the runtime use the correct error class. This includes null/undefined property access, undefined names, noncallable/nonconstructable values, invalid array/buffer lengths, invalid number formats/precisions/radices, bad iterators/descriptors/prototypes, frozen/nonextensible strict writes, revoked proxies, illegal weak keys, and incompatible built-in method receivers. Such failures must be catchable without terminating; only uncaught errors determine process status.

## Spec 38

Provide global `console.log`, `print`, `eval`, `globalThis`, numeric globals, `parseInt`, `parseFloat`, `isNaN`, `isFinite`, URI encode/decode functions (whole-URI and component variants), and legacy escape/unescape behavior used by the tests. `console.log` and `print` convert each argument with QuickJS display formatting, separate arguments by one space, and append one newline.

Display formatting is structural and deterministic: strings displayed as values inside arrays/objects are double-quoted with QuickJS escaping; plain objects resemble `{ key: value }`; dense arrays resemble `[ value, ... ]`, while sparse arrays show each present element with its index, so `[1,,3]` displays exactly as `[ 0: 1, 2: 3 ]`; typed arrays resemble `Uint8Array(4) [ 1, 2, 3, 255 ]`; regexes use literal notation; Symbols and errors use their conventional labels. Top-level string arguments print without surrounding quotes, while unhandled rejection strings are quoted. Circular/deep structures must not crash the formatter.

## Spec 39

Without `--std`, free identifiers `std` and `os` are undefined. With `--std`, both are global module objects. Static imports `import * as std from "std"` and `import * as os from "os"` also work in modules. `std` exports `Error`, `SEEK_SET`, `SEEK_CUR`, `SEEK_END`, `in`, `out`, `err`, `open`, `fdopen`, `popen`, `tmpfile`, `puts`, `printf`, `sprintf`, `loadFile`, `loadScript`, `evalScript`, `getenv`, `setenv`, `unsetenv`, `getenviron`, `strerror`, `parseExtJSON`, `urlGet`, `exit`, and `gc`. It does not export `readFile`: `"readFile" in std` is false and `typeof std.readFile` is `"undefined"`. `os` exposes its callable APIs plus platform/POSIX constants. Key enumeration begins in this exact order: `Object.keys(std)` starts with `Error,SEEK_CUR,SEEK_END,SEEK_SET`, and `Object.keys(os)` starts with `O_APPEND,O_CREAT,O_EXCL`.

Native API arguments use normal JavaScript conversion, and Symbol conversion failures throw TypeError instead of crashing, except for the `std.exit` behavior described here. `std.exit(code)` exits with the converted status; specifically, `std.exit(Symbol("x"))` produces no output and exits with status 255 rather than throwing. `std.gc()` requests cycle collection. `parseExtJSON` accepts extended JSON tested forms and rejects malformed input.

## Spec 40

`std.sprintf` returns and `std.printf` writes C/QuickJS-style formatted text. Support `%s`, `%c`, `%d`/`%i`, `%u`, `%o`, `%x`/`%X`, `%f`, `%e`/`%E`, `%g`/`%G`, `%a`, and `%%`; length modifier `l`; flags `-`, `+`, space, `#`, `0`, and apostrophe; literal and `*` width/precision; negative dynamic width; Unicode characters; 64-bit integer boundaries; infinities/NaN; and correct rounding/padding/prefix/case. Very large widths, precisions, and flag combinations allocate safely. A missing conversion value or a missing dynamic width or precision value throws a catchable `ReferenceError` whose message is exactly `missing argument for conversion specifier`; invalid conversion characters throw a catchable `TypeError` with QuickJS-compatible wording. `%c` validates code points.

## Spec 41

`std.open(path, mode)`, `fdopen(fd, mode)`, `popen(command, mode)`, and `tmpfile()` return a File object or, for ordinary open failure, a null/error result as exercised. Modes include text/binary `r`, `w`, `a`, update `+`, and their valid combinations; invalid modes throw `TypeError`. A File supports `puts`, `printf`, `flush`, `tell`, `seek(offset, whence)`, `eof`, `error`, `clearerr`, `fileno`, `getline`, `getByte`, `putByte`, `read(buffer, offset, length)`, `write(buffer, offset, length)`, `readAsString`, and `close`. `clearerr()` clears the stream's EOF/error indicators and returns `undefined`. A first successful `close()` returns 0; another `close()` on that handle throws `TypeError: invalid file handle`. Files handle empty, multiline, binary/NUL, Unicode, large, and partial data and detect operations on closed/invalid files.

`std.in/out/err` wrap the corresponding streams. `std.loadFile` returns file contents, including binary data in the requested mode, or the documented failure value. `loadScript` executes a file in the current context; `evalScript` evaluates source and returns its completion value. `popen` permits reading command output and writing command input and reports nonexistent commands without runtime corruption.

## Spec 42

Environment operations convert string arguments and provide `getenv` (undefined for absent variables), `setenv`, `unsetenv`, and `getenviron` (an object containing the current environment), including empty, long, Unicode, and special-character values. `strerror(errno)` returns the platform message for an integer error.

`std.urlGet` must validate its URL and options (including object/type checks), preserve URL escaping, handle empty/large and binary results, and report malformed/unavailable resources. It does not load local `file:` URLs: ordinary file URLs and escaped URLs such as one naming `a b[1].txt` return `null`. No successful live HTTP transaction is required by this specification.

## Spec 43

The `os` filesystem API implements POSIX-like `open`, `close`, `seek`, `read`, `write`, `remove`, `rename`, `realpath`, `getcwd`, `chdir`, `mkdir`, `stat`, `lstat`, `utimes`, `symlink`, `readlink`, and `readdir`. Expose relevant `O_RDONLY`, `O_WRONLY`, `O_RDWR`, `O_APPEND`, `O_CREAT`, `O_EXCL`, `O_TRUNC`, seek, mode/type, and errno constants. Low-level reads/writes operate on ArrayBuffer regions and return byte counts; stat/lstat return `[metadata, errno]`, and other fallible functions use QuickJS's integer/tuple error convention. Metadata includes mode, size, and timestamps sufficient to identify files/directories and observe `utimes`.

Operations must work for nested directories, relative and absolute paths, symlinks, renames, large/chunked files, and cleanup. Invalid descriptors, whence values, buffer bounds, missing paths, nonexistent rename sources, and permission errors return an errno result or throw exactly according to that API and never corrupt memory. Directory entries include the platform entries QuickJS exposes; ordering should be stable enough for scripts that sort/filter them.

## Spec 44

The `os` process/descriptor API provides `pipe`, `dup`, `dup2`, `isatty`, `ttyGetWinSize`, `ttySetRaw`, `getpid`, `exec`, `waitpid`, `kill`, and `platform`. Pipes return two usable descriptors. `exec(argv, options)` supports blocking and nonblocking execution, exit-status reporting, `file`, `cwd`, `env`, and stdin/stdout/stderr descriptor redirection; it handles empty/excessive argument arrays and missing programs without crashing. `waitpid` supports normal waits and `WNOHANG`. Mixed child stdout/stderr routing and nonzero exits remain observable. Invalid descriptors/PIDs/options produce QuickJS-compatible negative errno tuples or exceptions.

Signal APIs allow callable handlers, ignore/default modes, handler replacement/removal, and delivery of ordinary test signals. Invalid signal numbers or nonfunction handlers are rejected. TTY calls report non-TTY descriptors appropriately.

## Spec 45

The host event loop provides `os.setTimeout(callback, delay)`, `clearTimeout(id)`, `sleep(milliseconds)`, `sleepAsync(milliseconds)`, `setReadHandler(fd, callback)`, and `setWriteHandler(fd, callback)`. Timers accept zero and negative delay as immediate scheduling, run in deadline/registration order, support nested scheduling, many simultaneous timers, cancellation before/from callbacks (including self-cancellation), duplicate/unknown cancellation, and ignore callback return values. Invalid callbacks/IDs/delays are validated. An uncaught exception in a timer callback is formatted to standard error as a JavaScript error, but after surfacing it the process exits with status 0 rather than the status-1 rule for an uncaught top-level exception.

Read/write handlers integrate with pipes, may be installed, replaced, or removed with null, and do not fire after removal. Async sleeps compose through Promise jobs. Pending timers/handlers/process waits keep the loop alive as necessary; `os.exec` and jobs coexist with pending timers. Time APIs such as `os.now()` return a positive numeric monotonic/high-resolution millisecond value suitable for elapsed-time checks.

## Spec 46

Provide `os.Worker` with isolated JavaScript realms running a supplied module/script filename, `postMessage`/`onmessage` APIs, structured cloning of tested primitives and objects, and support for SharedArrayBuffer sharing. Preserve the reference behavior of the tested bidirectional round trip: when the worker installs `parent.onmessage`, replies with `parent.postMessage`, and the parent installs `w.onmessage` and sends an object, no reply is printed and the interpreter remains alive instead of exiting. Shared buffers plus `Atomics` provide integer atomic load/store/add and coordination operations used by worker tests. Worker creation validates paths and arguments.

## Spec 47

Interactive mode is entered with `-i` or when invoked in the tested interactive configuration. It prints `QuickJS - Type "\h" for help`, uses the prompt `qjs > `, reads UTF-8 stdin, evaluates expressions/statements repeatedly in one persistent global environment, displays non-undefined completion values using the QuickJS formatter, and recovers after syntax/runtime errors. Variables, functions, objects, and other bindings persist between entries.

The REPL's multiline decision uses its own declaration-continuation heuristic rather than stopping whenever the accumulated text is syntactically complete. For piped input exactly `let x=40\nx+2\n\q\n`, it combines the first two lines without a separator as `let x=40x+2`, reports `SyntaxError: invalid number literal` at `<evalScript>:1:7`, and does not evaluate `x+2` separately or display `42`. That invocation emits exactly two `qjs > ` prompts, accepts the final `\q`, leaves stderr empty, and exits with status 0. The REPL also accepts long lines and backslash commands including `\h` for help, clear-screen, hexadecimal display toggle, and timing toggle. It supports the same expressions, declarations, loops, classes, generators, promises, collections, proxies, reflection, regexes, templates, destructuring, scoping, and built-ins as file mode. Terminal-style character echo and incremental redisplay must match QuickJS behavior for piped interactive input, including prompts and the final quit line.

## Spec 48

The runtime must be robust under the tested stress workloads: at least 150 levels of object/array nesting, 500 safe recursive calls, 100 nested try/catch structures, large loops, 100,000-element arrays, 10,000-property objects, 10 MiB strings, megabyte concatenation growth, very large BigInts/powers/shifts, long regex inputs, deep closures/prototypes/proxies/generators/import chains, circular object graphs, and repeated allocations. It must preserve results and deterministic output, collect unreachable cycles/weak structures safely, and turn true stack or memory exhaustion into JavaScript `InternalError` rather than a native crash, hang, or memory corruption.

All features above must interoperate rather than work only in isolation. Representative required workflows include module chains that read and transform JSON/CSV/text, async pipelines using promises/generators/timers, proxies and accessors during JSON/object operations, typed-array binary transformations, class-based data models, collection aggregation, file write/read/seek/rename/remove cycles, child-process piping, dynamic imports, and error propagation through imported modules. The final observable stdout, stderr, exit status, filesystem effects, scheduling order, and cleanup are those produced by applying the semantics in this document.
