# `executable`: Go error-wrapping checker

The required artifact is one executable file named exactly `executable`. It is a command-line static analyzer for Go source. Its analyzer name is `wrapcheck`; its purpose is to find error values obtained from calls outside the current package (and from interface calls) that are returned without first being passed through an accepted wrapping/constructor call.

All paths, source text, package declarations, modules, configuration, and command-line arguments needed for an invocation are inputs at run time. The executable must analyze those inputs rather than recognize a fixed collection of files.

## Spec 1

The command accepts zero or more flags followed by one or more Go package arguments. Package arguments may be `.`; relative directories; a single absolute or relative `.go` file; import paths; multiple separate paths; or Go's recursive `...` patterns such as `./...`. It can be invoked from an arbitrary working directory and uses that directory when resolving relative arguments and the local configuration file. An absolute directory is not made into a loadable package argument merely because it contains a module: when an absolute subdirectory of a module is passed while the working directory is outside that module, the command exits 1 and writes exactly `wrapcheck: <absolute-directory> matched no packages` plus a newline to stderr. By contrast, the subpackage's import path is loadable from the module root.

Normal successful analysis has these statuses:

- no findings: exit 0;
- one or more findings in ordinary text mode: exit 3;
- one or more findings in JSON mode: exit 0;
- package loading, parsing, type-checking, configuration, profile creation, or analyzer-initialization failure: exit 1;
- ordinary command-line flag syntax errors: exit 2.

The special invalid-version case described below exits 1 rather than 2. In normal text mode stdout is empty and diagnostics/errors go to stderr. JSON results go to stdout and do not mix diagnostic prose into stderr. Every textual diagnostic and all normal command outputs except the `-flags` JSON described in Spec 5 end with a newline. A clean text-mode run is silent.

## Spec 2

`--help` must short-circuit package analysis, exit 0, write nothing to stdout, and write exactly the following text to stderr (including tabs, blank lines, and the final newline):

```text
wrapcheck: Checks that errors returned from external packages are wrapped

Usage: wrapcheck [-flag] [package]


Flags:
  -V	print version and exit
  -all
    	no effect (deprecated)
  -c int
    	display offending line with this many lines of context (default -1)
  -cpuprofile string
    	write CPU profile to this file
  -debug string
    	debug flags, any subset of "fpstv"
  -diff
    	with -fix, don't update the files, but print a unified diff
  -fix
    	apply all suggested fixes
  -flags
    	print analyzer flags in JSON
  -json
    	emit JSON output
  -memprofile string
    	write memory profile to this file
  -source
    	no effect (deprecated)
  -tags string
    	no effect (deprecated)
  -test
    	indicates whether test files should be analyzed, too (default true)
  -trace string
    	write trace log to this file
  -v	no effect (deprecated)
```

Invoking the command with no arguments prints this usage/help material to stderr and exits 1 rather than implicitly analyzing the current directory. Help or a valid full-version request ignores later package arguments, including nonexistent ones.

## Spec 3

Flag parsing follows the Go command-line flag style. Both `-json` and `--json` forms are accepted. A value may use a separate argument or `=`, for example `-c 2`, `-c=2`, `-test=true`, and `-test=false`. Repeating a Boolean flag such as `-json` is harmless. Bundled short options such as `-Vjson` are not supported.

Parsing stops at the first positional argument. Consequently, every later token is a package argument even if it begins with `-`. `--` also ends flag parsing. Thus `executable -- --help` attempts to load `--help` as a package and does not display usage. Given a valid current package, `executable . -json` treats `-json` as another package, exits 1, leaves stdout empty, and writes exactly:

```text
-: malformed import path "-json": leading dash
wrapcheck: analysis skipped due to errors in package
```

Analysis of other valid positional arguments may still produce findings.

Unknown flags and invalid/missing flag operands exit 2, write no normal output, print the Go-style parsing error followed by the usage text on stderr, and normalize a doubled leading dash to one dash in the error. Required examples include:

```text
flag provided but not defined: -nonexistent-flag
flag needs an argument: -c
invalid value "abc" for flag -c: parse error
invalid boolean value "maybe" for -test: parse error
```

The exact Boolean parse suffix may contain further Go parser detail, but the quoted value, flag name, and usage must be present.

## Spec 4

`-V` is represented as a Boolean-capable flag for flag introspection, but the only accepted version request is `-V=full`. That request exits 0 and writes one line to stdout of this form:

```text
<invocation-path> version devel comments-go-here buildID=<id>
```

`<invocation-path>` is the path by which the running executable identifies itself (when invoked as `/workspace/executable`, the line begins `/workspace/executable version `). `<id>` is exactly 64 lowercase hexadecimal characters. The output is sufficiently substantial (over 50 characters) and ends in a newline.

A bare `-V` is interpreted as `-V=true`. Any value other than `full`, including `true`, `short`, and `invalid`, exits 1, writes nothing to stdout, and writes exactly this pattern to stderr:

```text
wrapcheck: unsupported flag value: -V=<value> (use -V=full)
```

Unlike an ordinary parse error, this response does not append usage.

## Spec 5

`-flags` short-circuits analysis, exits 0, and writes a tab-indented JSON array to stdout. It contains exactly these ten entries, in this order, and each object has exactly the keys `Name`, `Bool`, and `Usage`:

| Name | Bool | Usage |
|---|---:|---|
| `V` | true | `print version and exit` |
| `all` | true | `no effect (deprecated)` |
| `c` | false | `display offending line with this many lines of context` |
| `diff` | true | `with -fix, don't update the files, but print a unified diff` |
| `flags` | true | `print analyzer flags in JSON` |
| `json` | true | `emit JSON output` |
| `source` | true | `no effect (deprecated)` |
| `tags` | false | `no effect (deprecated)` |
| `test` | true | `indicates whether test files should be analyzed, too` |
| `v` | true | `no effect (deprecated)` |

`Bool` says whether the flag can be used without a separate operand. Flags documented by help but absent from this introspection array (`fix`, `cpuprofile`, `memprofile`, `trace`, and `debug`) must remain absent. The final byte of this JSON is the closing `]`; there is no final newline.

## Spec 6

Package loading must be compatible with ordinary Go package semantics: read all build-eligible `.go` files, resolve imports and aliases, type-check expressions, obtain the package/import identity, and understand function and method signatures. Different packages below one module are still different package boundaries. For example, returning an error obtained from `test/helper.InternalErr` in package `main` is an external-package return even though both packages are in module `test`.

Recursive patterns must discover all nested packages, including directories named `internal`; multiple package arguments must all be processed. A directory need not itself contain `go.mod` if Go package loading can otherwise place it in a package context. Unicode file names, deeply nested directories, large files, packages with many files, third-party imports already available to the Go build, variadic signatures, and modern aliases such as `any` must work. There must be no low diagnostic count cap: hundreds of functions and at least 90 findings in a large file must all be handled in source order and without a timeout-scale slowdown.

Test files are included by default because `-test` defaults to true. `-test=true` keeps them; `-test=false` excludes `_test.go` analysis while retaining ordinary files. In JSON mode the Go test-package variants are separate package identities and may legitimately repeat a diagnostic from a non-test file, for example keys `testpkg1` and `testpkg1 [testpkg1.test]`. In ordinary text output, identical diagnostics arising from those variants are emitted only once.

## Spec 7

Analyze functions whose result tuple contains the predeclared `error` interface. A finding concerns an explicit returned error expression whose value can be traced to an error result of a call. The fundamental case is:

```go
_, err := json.Marshal(v)
if err != nil {
    return err // finding is located at this err expression
}
```

The origin is the canonical called function, here `encoding/json.Marshal`. Report an external finding if that function or concrete method belongs to a different package than the function being analyzed. This includes standard-library packages, third-party packages, and sibling packages in the same module. Analyze any external package, not a hard-coded package list; exercised origins include `encoding/json`, `encoding/xml`, `io`, `io/ioutil`, `os`, `os/exec`, `fmt`, `strconv`, `regexp`, `bufio`, `path/filepath`, `crypto/rand`, `database/sql`, `net/http`, and third-party YAML packages.

Calls to concrete functions or methods declared in the current package are not findings by default. Nonetheless, their bodies are independently analyzed, so a local helper returning an unwrapped `io.ReadAll` error produces one finding at the helper's external boundary, not additional findings at every caller that propagates the helper error.

## Spec 8

Error-origin tracking must cover all of these forms:

- a call directly used by a return, including a call returning several values, such as `return json.Marshal(v)`;
- `:=`, `=`, and `var` declarations followed by assignment;
- tuple/multiple assignment where the error occupies any return position;
- named result variables when they are explicitly present in a return expression;
- repeated reassignment, using the reaching/latest origin for each return;
- separate error variables without confusing their origins;
- lexical shadowing, so inner and outer variables retain different origins;
- package import aliases, values created in another file, chained selectors such as `json.NewEncoder(w).Encode(v)`, pointer/value receiver methods, and method calls on type-asserted values.

The reported source position is the beginning of the offending expression in the `return` statement: the returned identifier's column for `return err`, or the call's column for a direct call. For a diagnosed two-result `return result, err`, position the finding at `err`. Do not position it at the earlier assignment. Subject to the following compatibility limitation, every offending return is reported; do not stop after the first return, function, file, or package.

A required compatibility limitation applies to the three-result propagation form below: it produces no finding at the explicit return, although a direct `return json.Marshal(v)` in the same package is diagnosed.

```go
b, err := json.Marshal(v)
return len(b), b, err
```

Assignments from `nil`, constants, unrelated identifiers, or other non-call expressions must not crash and do not manufacture an origin. A plain `nil` error result is never a finding. Package-level error variables can retain a call origin across package initialization. In particular, after `var Global error` and `func init() { _, Global = json.Marshal(1) }`, a later explicit `return Global` is an external-package finding whose signature is `func encoding/json.Marshal(v any) ([]byte, error)`. A package-level sentinel initialized with `errors.New(...)` remains unreported because that origin is suppressed by the default accepted-signature list, not because package-level variables are categorically untraced. A package-level object of an external concrete type may likewise have its method resolved by type information, so returning `GlobalDecoder.Decode(...)` is analyzed as an external method call.

## Spec 9

Traversal is syntactic and must inspect all explicit return statements in `if`/`else` arms, initializer clauses, ordinary and type switches, every switch case, `select` cases and defaults, indexed and range loops, and arbitrarily nested combinations. Statically unreachable branches (for example `if false`) are still analyzed. Error checks against `nil`, `break`, `continue`, and unrelated `defer` statements do not prevent analysis. Errors merely printed, passed to testing methods, assigned, sent on channels, or otherwise consumed without being returned are not findings.

Function literals are analyzed when an external-call error is first assigned to a variable and that variable is explicitly returned; this applies at any nesting depth and inside a goroutine. One compatibility limitation is required: a call returned *directly* from within a function literal, such as `func() error { return decoder.Encode(v) }`, is not diagnosed. An equivalent named declaration is diagnosed, and a function literal that performs `err := decoder.Encode(v); return err` is diagnosed.

Another required limitation is that a bare return in a function with named results is not diagnosed, even if a named error was assigned from an external call. An explicit `return err` or `return value, err` is diagnosed normally.

## Spec 10

Calls whose statically selected receiver is an interface method are findings even when the interface type is declared in the current package. Their diagnostic category is distinct from ordinary external concrete calls:

```text
error returned from interface method should be wrapped
```

This includes local interfaces and imported interfaces such as `context.Context`, `io.Reader`, and `io.Writer`; interface declarations and uses may be in different files. The canonical signature retains the interface receiver, for example:

```text
func (context.Context).Err() error
func (io.Reader).Read(p []byte) (n int, err error)
func (example.com/module.Reader).Read(key string) ([]byte, error)
```

A call statically dispatched to a concrete method declared in the current package is package-internal, not an interface finding. Its method body may still contain separately reportable external calls.

When configuration sets `reportInternalErrors: true`, explicit returns of errors obtained from same-package functions and concrete methods are additionally reported using:

```text
package-internal error should be wrapped
```

The default is false. The internal message includes that local call's canonical signature. Internal sentinel-variable returns remain unreported because they have no call origin.

## Spec 11

Whether a returned call is accepted as wrapped is determined from the canonical signature of its current origin. With no overriding configuration, suppress a finding when the signature contains any one of these exact, case-sensitive substrings:

```text
.Errorf(
errors.New(
errors.Unwrap(
errors.Join(
.Wrap(
.Wrapf(
.WithMessage(
.WithMessagef(
.WithStack(
```

Consequently `fmt.Errorf` is accepted regardless of whether its format uses `%w` or `%v`, `errors.New` and `errors.Join` are accepted, and common `github.com/pkg/errors` wrapping calls are accepted. This is signature-based compatibility behavior, not semantic inspection of format strings. If the default list is replaced by configuration, these calls become reportable unless the replacement rules suppress them.

Returning an original call error unchanged is unwrapped. Returning a new accepted wrapper-call result is not. In a function containing both patterns, report only the unchanged paths. Values that originate at a properly wrapped local helper and are later returned through another same-package helper do not create a new external finding.

## Spec 12

Each ordinary finding is one stderr line in this exact form:

```text
<absolute-file>:<line>:<column>: <category>: sig: <canonical-signature>
```

`<category>` is exactly one of:

```text
error returned from external package is unwrapped
error returned from interface method should be wrapped
package-internal error should be wrapped
```

Use the absolute source filename and one-based UTF-8/Go token line and byte-column positions. Use Go's canonical type-string style with real import paths rather than local aliases, named parameters/results when present, `...` for variadics, and parenthesized receivers. Required examples are:

```text
func encoding/json.Marshal(v any) ([]byte, error)
func encoding/json.Unmarshal(data []byte, v any) error
func os.Open(name string) (*os.File, error)
func (*encoding/json.Encoder).Encode(v any) error
func fmt.Scanf(format string, a ...any) (n int, err error)
func io.Copy(dst io.Writer, src io.Reader) (written int64, err error)
```

Within a package, findings are deterministic in file/source-position order. Multi-package output is deterministic according to package loading order. There are no headings, summaries, blank separators, or ANSI decoration around ordinary diagnostics.

For example, if `/workspace/p/main.go` returns the `err` from `fmt.Scanf` at line 14, column 10, the complete line is:

```text
/workspace/p/main.go:14:10: error returned from external package is unwrapped: sig: func fmt.Scanf(format string, a ...any) (n int, err error)
```

## Spec 13

`-c` controls source context only in ordinary text mode. Its default and the explicit value `-1` add no source lines. A value of `0` adds exactly the offending source line. A nonnegative `N` adds up to `N` preceding lines, the offending line, and up to `N` following lines, clamped to the file boundaries; a large value therefore prints the entire file.

Context immediately follows its diagnostic and each source line has this exact form, preserving the original source text after the delimiter:

```text
<decimal-line-number>\t<original-line>
```

For instance, an offending source line whose indentation begins with two tabs may appear as `14\t\t\treturn err`. A terminal newline in the source is represented as one additional numbered empty context line: if an eight-line file ends immediately after line 8's newline, full-file context ends with `9\t` followed by a newline. Repeat a context block after each finding, without an extra marker or blank separator. `-c=2` and `-c 2` are identical. In JSON mode, any `-c` value is ignored: it adds neither fields nor text and cannot corrupt the JSON.

## Spec 14

`-json` emits one tab-indented JSON object followed by a newline. A clean analysis is exactly an empty object (`{}` plus newline). Otherwise, top-level keys are the Go package identities supplied by package loading. Each successful package value contains exactly one key, `wrapcheck`, whose value is an array of diagnostics in occurrence order. Each diagnostic object has exactly two string fields in this order:

```json
{
	"posn": "/absolute/file.go:14:10",
	"message": "error returned from external package is unwrapped: sig: func encoding/json.Marshal(v any) ([]byte, error)"
}
```

`posn` is the same position used in text mode. `message` is exactly the portion after the position and space in the text diagnostic. JSON has no context, source excerpt, summary, or duplicate output on stderr. Multiple packages become separate top-level keys; the key comes from Go's package/module identity (for example `testpkg2` or a full module import path), not merely an arbitrary directory basename. Findings do not cause a nonzero status in JSON mode.

If package analysis is skipped because an otherwise addressed package cannot load, JSON mode still exits 1 and represents the analyzer failure under the resolved Go package identity, not the literal command-line argument. For a module whose identity is `example.com/test`, analyzing `.` therefore produces:

```json
{
	"example.com/test": {
		"wrapcheck": {
			"error": "analysis skipped due to errors in package"
		}
	}
}
```

Package/compiler details may additionally be on stderr, but stdout must remain valid JSON.

## Spec 15

Before analysis, look for `.wrapcheck.yaml` in the process's current working directory. Absence is silent. An empty file or a file containing only comments/whitespace is equivalent to default configuration. Parse ordinary YAML mappings, quoted or unquoted scalar text, arrays, comments, blank lines, and escaped regular-expression backslashes.

The recognized keys and types are:

```yaml
ignoreSigs:             # list of signature substrings
  - json.Marshal(
extraIgnoreSigs:        # list of additional signature substrings
  - io.ReadAll(
ignoreSigRegexps:       # list of regular expressions over canonical signatures
  - 'json\..*\('
ignorePackageGlobs:     # list of glob patterns over origin import paths
  - 'encoding/*'
ignoreInterfaceRegexps: # list of regular expressions over interface type names
  - 'Reader'
reportInternalErrors: false
```

String-list fields use weak scalar-to-list decoding for primitive scalar values, but a mapping/object inside a string list is invalid. A scalar string is split at each literal comma rather than treated as one list entry. For example, `ignoreSigs: ([]byte, error)` becomes the two substring filters `([]byte` and ` error)`, which suppress the `json.Marshal`, `xml.Marshal`, and `os.Open` signatures while leaving `(*encoding/json.Encoder).Encode` reportable. `reportInternalErrors` is a Boolean (with standard weak textual Boolean parsing); an unparseable value is invalid.

The default `reportInternalErrors` is false. The default signature list is the nine entries in Spec 11. Merely providing other configuration keys does not remove those defaults.

## Spec 16

Configuration filtering follows these rules:

- If `ignoreSigs` is absent, start with the default list. If it is present, its value replaces the entire default list. This is true even for `ignoreSigs: []`, which means no substring is ignored.
- Append `extraIgnoreSigs` to whichever base list was selected. It extends defaults when `ignoreSigs` is absent, and extends the custom replacement when `ignoreSigs` is present.
- Each signature substring is searched anywhere in the full canonical signature, literally and case-sensitively. It need not start at the function name: fragments such as `Marshal(`, `New(`, or `([]byte, error)` work. Punctuation has no special meaning for this list.
- Compile every `ignoreSigRegexps` entry as a Go/RE2-style regular expression and suppress a call if any expression searches/matches its full canonical signature. Matching is case-sensitive unless the expression itself changes case behavior. Anchors, alternation, character classes, quantifiers, and escaped punctuation work.
- Match every `ignorePackageGlobs` entry against the complete defining import path of an external call. A pattern must match the whole path, not just a prefix: `os` matches `os` but not `os/exec`; `encoding/*` matches `encoding/json` and `encoding/xml`; `github.com/pkg/*` matches `github.com/pkg/errors`; and `*` matches every package path, including paths containing `/`. Suppress when any glob matches.
- Match `ignoreInterfaceRegexps` against the canonical underlying interface type/name, not the method name. For an interface declared in the package being analyzed, this filter does not suppress or recategorize the call: even a matching local `example.com/test.Reader` remains reportable as `error returned from interface method should be wrapped` with signature `func (example.com/test.Reader).Read(string) ([]byte, error)`. For an imported interface, a match removes the call from the interface-method category but does not suppress the ordinary external-package check. Thus a matching `io.Reader` call is instead reported as `error returned from external package is unwrapped` with signature `func (io.Reader).Read(p []byte) (n int, err error)`. Multiple expressions are alternatives. A nonmatching interface remains reportable in the interface-method category.

All applicable lists are cumulative alternatives, and all files in a package use the same loaded configuration.

## Spec 17

Configuration errors fail before useful analysis and exit 1. Malformed YAML produces exactly one fatal stderr line in Go log style (date and time prefix followed by a space) containing:

```text
failed to parse config: While parsing config: yaml: line <N>: <parser-detail>
```

Preserve parser details such as `found character that cannot start any token`, `did not find expected node content`, `did not find expected '-' indicator`, or `did not find expected key` as appropriate to the input.

A valid YAML document that cannot decode must contain `failed to unmarshal config:` followed by the decoder's detailed error list. Required details include, as appropriate:

```text
1 error(s) decoding:
cannot parse 'reportInternalErrors' as bool: strconv.ParseBool: parsing "not a boolean": invalid syntax
'ignoreSigs[0]' expected type 'string', got unconvertible type 'map[string]interface {}'
```

All signature and interface regular expressions and all package globs are validated before reporting findings. An invalid regexp exits 1 on stderr in this form, preserving the bad pattern and Go regexp detail:

```text
wrapcheck: unable to compile regexp <pattern>: error parsing regexp: <detail>
```

For the invalid glob `[`, exit 1, leave stdout empty, and write exactly the following line followed by one additional blank line (two newline bytes after `input`):

```text
wrapcheck: unable to compile globs %!s(<nil>): unexpected end of input

```

Do not silently discard an invalid filter.

## Spec 18

`-fix` is accepted, but this analyzer supplies no suggested fixes. On valid source it must never modify any source file. It suppresses all findings and exits 0 even when the same invocation without `-fix` would exit 3. This holds for multiple findings and repeated runs. When combined with `-json`, fix mode takes precedence: stdout remains empty rather than emitting JSON.

`-diff` also never modifies files. Because there are no suggested fixes, it produces no unified diff markers (`---`, `+++`, or `@@`) and otherwise behaves exactly like ordinary analysis: findings remain on stderr and exit 3. It must work with read-only inputs and multiple packages. When combined with `-json`, JSON mode takes precedence over diff presentation: emit the normal JSON diagnostics on stdout, exit 0 for findings, and emit no diff.

## Spec 19

The profiling flags each take a filesystem path:

- `-cpuprofile PATH` creates a nonempty CPU profile;
- `-memprofile PATH` creates a nonempty memory profile;
- `-trace PATH` creates a nonempty execution trace.

The generated CPU and memory files must contain substantive profile data (more than 100 bytes for a normal analysis), not placeholder empty files. The flags can be used together and also in JSON mode without corrupting stdout. Existing parent directories are usable; parent directories need not be created automatically. Failure to open an output path is fatal and reports the operating-system error, for example `open /nonexistent/dir/cpu.prof: no such file or directory`.

Trace creation also writes viewing guidance to stderr without changing analysis status, containing all of:

```text
To view the trace, run:
go tool trace view
<trace-path>
```

`-debug` accepts a string made from any subset of `fpstv`. Values such as `f` and `fpstv` allow analysis to proceed. Full debugging includes analysis timing/identity text such as `wrapcheck@<package>`, package `load` activity, and `building graph of analysis passes` on stderr. `-all`, `-source`, and `-v` are accepted Boolean no-ops; `-tags` accepts a string and is also a no-op. They produce no deprecation warning and do not change findings.

## Spec 20

Invalid Go inputs are reported as failures, not crashes. For directories with no Go files, syntax errors, undefined identifiers/import failures, and type errors, forward the Go loader/compiler diagnostics to stderr, then include the exact analyzer line:

```text
wrapcheck: analysis skipped due to errors in package
```

and exit 1. Representative required loader lines are:

```text
-: no Go files in <directory>
./main.go:4:15: undefined: json
./main.go:6:17: cannot use "string" (untyped string constant) as int value in variable declaration
```

Two failures occur before that ordinary package-analysis diagnostic sequence:

- An absolute path used as a package/directory argument, whether it is nonexistent or is an existing module subdirectory supplied from outside the module, exits 1 with empty stdout and exactly `wrapcheck: <absolute-path> matched no packages` plus a newline on stderr. It does not emit a `stat`, `directory not found`, or `analysis skipped due to errors in package` line.
- A malformed `go.mod` exits 1 with empty stdout and begins stderr with `wrapcheck: err: exit status 1: stderr: go: errors parsing go.mod:` followed by a newline and the Go tool's `go.mod:<line>: <detail>` diagnostic. For example, `this is not a module file` produces `go.mod:1: unknown directive: this`; `go 1.invalid` on line 3 produces `go.mod:3: invalid go version '1.invalid': must match format 1.23`. This early failure does not append `wrapcheck: analysis skipped due to errors in package`.

Use the paths and detailed positions/messages supplied by the Go parser/type checker for the actual input, including possibly several syntax diagnostics for one malformed file. Do not run wrapcheck analysis for an invalid package, but continue far enough across multiple positional package arguments to surface errors associated with each argument. A valid empty Go package or a package with no error-returning functions is successful and produces no wrapcheck diagnostics.
