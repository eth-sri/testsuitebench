# Clarified specification for `executable`

The required artifact is one executable file named exactly `executable`. It is a command-line Go test-skeleton generator. All behavior below is observable behavior of that artifact; no repository source, configuration, helper program, or documentation other than this file may be assumed to exist. Input Go files and user-supplied template directories are ordinary runtime inputs.

## Spec 1

`executable` is a single-command, flag-based CLI. It has no subcommands. Every non-flag argument is an input path, so bare words such as `help`, `version`, `add`, `list`, and `generate` are paths rather than commands. The general invocation is:

```text
executable [flags] PATH [PATH ...]
```

The program must be usable through either an absolute or relative executable path and from any current working directory. Unless another rule below specifies otherwise, successful generation, validation messages, source/template errors, and “no tests” messages go to stdout, stderr is empty, and the exit status is 0. This deliberately includes most operational errors. Flag-syntax errors are the exception described in Spec 3, and invalid AI configuration is the exception described in Spec 21.

## Spec 2

`--help`, and a parsed help flag following other flags, prints help to stderr, prints nothing to stdout, and exits 0 immediately. Help takes precedence over later arguments, including an unknown flag after it. The first line is `Usage of <actual argv[0]>:` and the text ends in a newline. Other than the dynamic `argv[0]`, the help text is exactly:

```text
Usage of ./executable:
  -ai
    	generate test cases using AI (requires Ollama)
  -ai-endpoint string
    	Ollama API endpoint (default "http://localhost:11434")
  -ai-max-cases int
    	maximum number of test cases to generate with AI (default 10)
  -ai-min-cases int
    	minimum number of test cases to generate with AI (default 3)
  -ai-model string
    	AI model to use for test generation (default "qwen2.5-coder:0.5b")
  -all
    	generate tests for all functions and methods
  -excl string
    	regexp. generate tests for functions and methods that don't match. Takes precedence over -only, -exported, and -all
  -exported
    	generate tests for exported functions and methods. Takes precedence over -only and -all
  -i	print test inputs in error messages
  -named
    	switch table tests from using slice to map (with test name for the key)
  -nosubtests
    	disable generating tests using the Go 1.7 subtests feature
  -only string
    	regexp. generate tests for functions and methods that match only. Takes precedence over -all
  -parallel
    	enable generating parallel subtests using the Go 1.7 feature
  -template string
    	optional. Specify custom test code templates, e.g. testify. This can also be set via environment variable GOTESTS_TEMPLATE
  -template_dir string
    	optional. Path to a directory containing custom test code templates. Takes precedence over -template. This can also be set via environment variable GOTESTS_TEMPLATE_DIR
  -template_params string
    	read external parameters to template by json with stdin
  -template_params_file string
    	read external parameters to template by json with file
  -use_go_cmp
    	use cmp.Equal (google/go-cmp) instead of reflect.DeepEqual
  -version
    	print version information and exit
  -w	write output to (test) files instead of stdout
```

The spaces before each description include a literal tab in the same style as Go's standard `flag` package. Help must not contain `subcommand` or a `Commands:` section.

## Spec 3

Accept one or two leading dashes for every named flag (for example, `-all` and `--all`). Value flags accept both `-only VALUE` and `-only=VALUE`. The value flags are `only`, `excl`, `template`, `template_dir`, `template_params`, `template_params_file`, `ai-model`, `ai-endpoint`, `ai-min-cases`, and `ai-max-cases`; the final two require base-10 integers. All other flags are booleans. Repeating a value flag uses its last parsed value.

`--` terminates flag parsing and is not a path; every later token is positional even when it begins with `-`. Flags are expected before the first ordinary positional argument. Help and version act only when parsed as flags.

Use Go-standard flag diagnostics. An unknown flag exits nonzero, writes no stdout, and writes a diagnostic such as `flag provided but not defined: -unknown` followed by the full usage text to stderr. A missing value similarly reports `flag needs an argument: -only`. A malformed integer reports text such as `invalid value "notint" for flag -ai-min-cases: parse error` and usage. Supplying a non-boolean attachment such as `-all=filename.go` reports `invalid boolean value ... for -all` and usage. These parse failures happen before runtime validation.

## Spec 4

At least one effective selector must be present: `-all`, `-exported`, a nonempty `-only` value, or a nonempty `-excl` value. Merely spelling `-only=` or `-excl=` with an empty value does not count as a selector, whether or not a source path follows it; such an invocation prints the missing-selector message below. If no effective selector is present, print exactly:

```text
Please specify either the -only, -excl, -exported, or -all flag
```

and exit 0. Perform this check before requiring paths. Thus no arguments, a bare path, or only modifier flags gets this message. Once a selector exists, at least one positional path is required; otherwise print exactly:

```text
Please specify a file or directory containing the source
```

and exit 0.

Validate nonempty `-only` and `-excl` as Go/RE2 regular expressions before reading inputs. Failures print one line and exit 0:

```text
Invalid -only regex: <regexp compiler error>
Invalid -excl regex: <regexp compiler error>
```

For example, `(invalid` produces `Invalid -only regex: error parsing regexp: missing closing ): `(invalid``. Runtime validation errors do not print usage.

## Spec 5

`-version` and `--version` print version information to stdout and exit 0 without validating AI options, selectors, paths, or generating tests. Stdout consists of exactly four newline-terminated, nonempty lines, in this order, with no additional metadata before or after them:

```text
gotests <version>
Go version: <go-version>
Git commit: <git-commit>
Build time: <build-time>
```

`<version>`, `<git-commit>`, and `<build-time>` are nonempty; `<version>` may be a release such as `v0.0.0` or a development label, and `<go-version>` starts with `go` and contains a major/minor version. Supplying a path or invalid AI settings together with a parsed version flag must not produce test code, warnings, or validation errors.

## Spec 6

Each positional input is resolved relative to the process working directory and may be:

- A regular `.go` file. An explicitly named hidden file (basename starts with `.`) or non-Go file is rejected with `input.Files: no Go source files found at <absolute-path>`, where a relative argument is resolved against the process working directory rather than retaining its caller-supplied spelling. An explicitly named `_test.go` file is admitted past input selection, but generation for a file whose contents are `package p\nfunc helper(x int) int { return x }\n` does not produce a test. It exits 0 with no banner and prints one `output.Process: imports.Process:` line whose temporary filename has the form `/tmp/gotests_<decimal-digits>` and whose diagnostic is `:7:1: expected declaration, found unc (and 1 more errors)`.
- A directory. Scan only its immediate regular `.go` children; do not descend. Ignore hidden files and all `*_test.go` files as generation targets. Non-Go children are silently ignored.
- A path ending in the path component `...`, such as `./...`, `nested/...`, or `/tmp/base/...`. Recursively walk the directory before `...` to unlimited depth. Skip any directory whose basename starts with `.`, skip hidden files, skip `*_test.go` targets, and ignore non-Go files.

Support absolute paths, `./`, `../`, ordinary punctuation in path components, and deeply nested paths. For an ordinary missing input or broken symbolic link, resolve a relative input against the process working directory and lexically clean the resulting absolute path (in particular, remove trailing separators): print `input.Files: os.Stat: stat <cleaned-absolute-path>: no such file or directory` followed by a blank line. A missing recursive input ending in `...` instead removes that final component, resolves and cleans the base, and prints `input.Files: filepath.Walk: lstat <cleaned-absolute-base>: no such file or directory` followed by a blank line. Thus `/nonexistent/directory/` is displayed as `/nonexistent/directory`, while `/nonexistent/pkg/...` reports `input.Files: filepath.Walk: lstat /nonexistent/pkg: no such file or directory`. A directory or recursive tree with no eligible targets prints `No tests generated for <path>` using the path spelling supplied by the caller. A nonrecursive directory must not process its subdirectories. Multiple paths are all processed; output for a file remains contiguous, but ordering among independently discovered files need not be stable.

## Spec 7

Parse Go source using the current Go grammar, preserving spelling of types, package aliases, Unicode identifiers/comments, CRLF input semantics, variadic syntax, anonymous structs/interfaces, channels and direction, function types, pointers, arrays, maps, nested generic types, embedded fields, and named results. Interface method declarations are not concrete functions and receive no tests. Package variables, constants, imports, and type declarations receive no tests.

An exactly zero-byte source prints `Parser.Parse source file: file is empty`. Other syntax errors print:

```text
Parser.Parse source file: target parser.ParseFile(): <absolute-or-resolved-path>:<line>:<column>: <Go parser diagnostic>
```

Additional parser diagnostics may be summarized as `(and N more errors)`. The missing-package case whose first token is `import` is an exact exception: report only the primary diagnostic `expected 'package', found 'import'`, with no `(and N more errors)` suffix. If another non-test `.go` file in the target's directory is malformed, prefix its diagnostic with `Parser.Parse source file: other file parser.ParseFile:`. If the corresponding test file is malformed, use `Parser.Parse test file: target parser.ParseFile():`. Do not panic on missing package declarations, mismatched braces, undefined types, mixed packages, blank identifiers, or unusual but syntactically parseable declarations. Where type checking cannot resolve a type, retain its source spelling and still generate a structural test.

## Spec 8

Select concrete top-level functions and methods in source order. A plain `func init()` with no receiver, parameters, or results is never testable and is omitted. A function named `init` that has a receiver, parameters, or results is treated normally.

The selectors narrow one another rather than causing a conflict:

- `-all` establishes an unrestricted starting set.
- `-only REGEXP` keeps matches and takes precedence over the breadth of `-all`.
- `-exported` keeps only exported declarations and takes precedence over the breadth of `-all`; when combined with `-only`, both restrictions apply.
- `-excl REGEXP` removes matches after all inclusion restrictions, so it has final precedence. With no other selector, `-excl` starts from all declarations and removes its matches.

Regex matching is case-sensitive unless the pattern itself uses syntax such as `(?i)`. For a function, match its declared name. For a method, matching either its method name or the receiver type name concatenated directly with the method name selects/excludes it; for example both `BarFilter` and `BarBarFilter` can address `(*Bar).BarFilter`. Ordinary regexp substring semantics apply unless the pattern is anchored.

If a source is valid but has no selected functions, print exactly one line `No tests generated for <path>` and no package/test skeleton.

## Spec 9

For every newly generated test, first emit one stdout banner:

```text
Generated <TestName>
```

Banners appear in selected declaration order and precede the generated Go file. Without `-w`, stdout then contains the complete formatted test-file content: preserved leading package comments/build constraints, `package <source-package>`, imports, and all applicable test functions. Stderr is empty. With `-w`, stdout contains only banners (or error/no-test text), while Go content is written as specified in Spec 18.

Generated Go must be formatted equivalently to `gofmt` plus import cleanup: tabs for indentation, aligned struct fields, deterministic imports, a final newline, and one blank line between top-level declarations. A newly created import declaration is single-line when only one import is used and is a block otherwise. A successful merge with a nonempty existing test file instead rebuilds the import declaration as a parenthesized block, even when the existing declaration was single-line and cleanup leaves only `testing`. Generated Go must be syntactically valid except when the source itself has an unresolved/blank type that necessarily carries through, a user template deliberately renders invalid Go, or the observed `-i` writer diagnostic described in Spec 15 emits its dangling `tt.args.<writer>` reference.

## Spec 10

Test names are deterministic:

- Exported free function `Foo` becomes `TestFoo`; unexported `foo` becomes `Test_foo`.
- A method `Method` on receiver base type `Thing` becomes `TestThing_Method`.
- Preserve receiver/method capitalization independently: `sameName` on `sameTypeName` becomes `Test_sameTypeName_sameName`.
- Strip pointer notation and generic arguments from the receiver portion of the test name.

Each default test has signature `func <TestName>(t *testing.T)`. Its table begins with `// TODO: Add test cases.` and contains no invented test cases. In default (not `-named`) mode it is:

```go
tests := []struct {
	name string
	// receiver/args/want fields as applicable
}{
	// TODO: Add test cases.
}
```

No-parameter functions omit `type args` and the `args args` member. Functions with parameters declare a local `type args struct` immediately before the table and add `args args` after receiver table data. Preserve declared parameter order and exact type. Expand grouped parameters (`a, b int`) into separate fields. Name anonymous parameters `in0`, `in1`, ... in positional order. A variadic parameter `xs ...T` is stored as `xs []T` and passed as `tt.args.xs...`.

## Spec 11

The default subtest shape is:

```go
for _, tt := range tests {
	t.Run(tt.name, func(t *testing.T) {
		// receiver setup, call, and checks
	})
}
```

For a call with no results, emit the call as a statement. For a “naked” function (no receiver, parameters, or results), the table still contains `name string` and the TODO. Under `-nosubtests`, use `for range tests` for a naked function because no `tt` value is needed; otherwise use `for _, tt := range tests`.

`-named` changes the table/key structure: use `tests := map[string]struct { ... }`, omit the `name string` member, iterate `for name, tt := range tests`, and pass `name` to `t.Run`. With both `-named` and `-nosubtests`, use the map but no `t.Run`; a non-naked test still iterates `for name, tt := range tests`, while a naked one uses `for range tests`.

## Spec 12

For a method, include receiver state in the table before `args`:

- A generic receiver is represented directly rather than through a `fields` helper, even when its base type is a known struct with fields. Add a receiver member using the declared receiver variable and the instantiated receiver type, such as `s *Set[string]` or `c *Container[int]`. In the loop, construct an empty instantiated composite literal such as `s := &Set[string]{}`; do not copy the generic struct's fields from table data.
- If the receiver's base type is a known struct with fields, declare `type fields struct` containing every named and embedded field in declaration order, except for the receiver-name collision case for `T` described below. An embedded field uses its type-derived field name (for example embedded `string` becomes `string string`, `*io.PipeWriter` becomes `PipeWriter *io.PipeWriter`). Add `fields fields` to the table, then construct the receiver in each iteration with a keyed composite literal populated from `tt.fields`. Respect pointer versus value receiver (`&Thing{...}` versus `Thing{...}`).
- If it is a known struct without fields, add a receiver table member such as `c *Calculator` or `b Bar`, and construct an empty receiver literal for the call.
- If it is a named non-struct or an unresolved receiver, add a receiver table member and call through `tt.<receiver>` instead of constructing it.

Use the declared receiver variable name where safe. If absent, derive a lowercase short name from the receiver type (`MyType` -> `m`). Avoid collisions: a receiver based on `Name` uses `n` rather than `name`, and a receiver based on `T` uses `tr` rather than `t` so it does not collide with `*testing.T`. When such receivers are in the directly represented non-struct/unresolved case above, the aligned table members are `n Name` and `tr T`, and calls use `tt.n.GetValue()` and `tt.tr.GetData()` respectively; do not introduce local `name` or `t` variables.

The observed `T` collision case, in which a receiver named `t` would collide with the `*testing.T` argument, is also directly represented when `T` is declared as `struct { data int }`: it bypasses `type fields struct`, uses the aligned table member `tr   T`, and calls `tt.tr.GetData()` without creating a local receiver composite literal. This is a specific exception to the known-struct rule above; the analogous `Name` struct continues to use its `fields` helper and a local receiver named `n`. A struct field's spelling is preserved, including unexported and keyword-like capitalized names.

## Spec 13

Model outputs in the table after receiver and args fields. The built-in default rules are:

- Every diagnostic identifies a free function as `Function()` and a method as `ReceiverType.Method()`, not merely `Method()`. Strip pointer notation from the displayed receiver but preserve its declared base-type spelling and capitalization. Preserve declared generic parameters in this label rather than substituting their chosen concrete types: examples include `Bar.Foo7()`, `Undefined.Do()`, `door.Open()`, and `Container[T].Get()`. The same qualified label is used in value comparisons, error checks, `-i` messages, and `-nosubtests` messages.
- The final result whose type is exactly the predeclared `error` is not a value expectation; add `wantErr bool` instead. Other results named `err` but not typed as `error` remain ordinary results.
- Unnamed value results are `want`, `want1`, `want2`, ... and call variables are `got`, `got1`, `got2`, .... A named result `result` uses `wantResult`/`gotResult`; likewise `count` becomes `wantCount`/`gotCount`. Treat a declared blank result name `_` as unnamed. Its numeric suffix is the zero-based position among all non-error value results, including intervening named results, with the suffix omitted at position zero. Thus `(_ string, i int, _ []byte, err error)` produces `want`, `wantI`, `want2`, and `wantErr`, and assigns to `got`, `gotI`, `got2`, and `err`.
- Directly comparable basic values, and pointers to basic values, use `got != tt.want`. Slices, maps, arrays, structs, interfaces, channels, function values, named complex objects, and unresolved/non-basic values use `!reflect.DeepEqual(got, tt.want)` and require `reflect`. A result still modeled as a generic type parameter is treated as non-basic even if its chosen concrete instantiation is `int`.
- With one value result and no error, use an inline initializer: `if got := Call(...); comparison { ... }`. With multiple value results or a value plus error, assign all results first in order.

For a trailing error plus value results, emit:

```go
got, err := Call(...)
if (err != nil) != tt.wantErr {
	t.Fatalf("Call() error = %v, wantErr %v", err, tt.wantErr) // t.Errorf outside subtests
}
if tt.wantErr {
	return
}
// value checks
```

Inside subtests, the mismatch uses `t.Fatalf`; without subtests it uses `t.Errorf` followed by `continue`. The `if tt.wantErr { return }` is retained in both modes. If error is the only result, use `if err := Call(...); (err != nil) != tt.wantErr { t.Errorf(...) }` and no separate early return. Multiple value-result error messages insert the result variable label (`Call() got1 = ...`); a single value does not.

## Spec 14

Treat a parameter specially when its declared source type is exactly `io.Writer`; structural assignability alone does not trigger this handling. Do not put such an `io.Writer` parameter in `type args`. Before calling, create a `bytes.Buffer`, named from the parameter (`w`, `w1`, ...), pass it directly, and add a string expectation `wantW`, `wantW1`, ... after ordinary value expectations. After a successful error check and ordinary result checks, compare `w.String()` with that expectation using a local such as `gotW` and a normal string comparison. Import `bytes`; retain any other signature imports actually needed. A parameter declared as `interface{ Write([]byte) (int, error) }` remains an ordinary member of `args`, is passed as `tt.args.<name>`, and receives no buffer-content expectation even though that interface has the same method as `io.Writer`.

This applies to free functions and methods, to multiple writers, and alongside ordinary parameters and results. A non-writer interface such as `io.Reader` or `io.Closer` remains in `args`.

## Spec 15

`-nosubtests` removes every `t.Run` wrapper. Its error messages begin with the table name as `%q. `. In slice mode, pass `tt.name` as the first formatting argument, for example:

```go
t.Errorf("%q. Add() = %v, want %v", tt.name, got, tt.want)
```

In `-named` map mode, pass the loop variable `name` in that position instead.

Default subtest-mode messages omit that prefix. `-i` adds one `%v` for every declared call parameter inside the displayed call parentheses, in source order. An ordinary parameter contributes its corresponding `tt.args` value before `got`/`err`; for example, `Add(a, b int)` produces `Add(%v, %v)` with `tt.args.a, tt.args.b`. A writer parameter is still printed in these diagnostic contexts even though Spec 14 omits it from `type args`: it contributes the literal expression `tt.args.<writer-name>`, not the local buffer variable. This applies both to the ordinary result diagnostic and to the buffer-content diagnostic. For example, `Emit(x int, w io.Writer) int` under `-i` emits both:

```go
t.Errorf("Emit(%v, %v) = %v, want %v", tt.args.x, tt.args.w, got, tt.want)
t.Errorf("Emit(%v, %v) = %v, want %v", tt.args.x, tt.args.w, gotW, tt.wantW)
```

Consequently, this particular combination preserves the reference's dangling `tt.args.w` expression even though no `w` member exists in `args`.

`-parallel` inserts `t.Parallel()` immediately inside every top-level generated test. When subtests are enabled it also inserts `t.Parallel()` as the first statement inside each `t.Run` callback. With `-nosubtests`, only the top-level call remains. All combinations of `-named`, `-nosubtests`, `-parallel`, `-i`, templates, and comparison options compose according to these rules.

## Spec 16

Support Go type parameters on functions and receiver types. Generated tests instantiate every type parameter with a deterministic concrete type and substitute it consistently in argument/result/receiver types and calls:

- `any` maps to `int`.
- `comparable` maps to `string`.
- `~X` maps to `X` (for example `~int`, `~string`, and `~float64`).
- A union maps to its first alternative after removing `~`, even if that alternative is a named type (`int32 | int64` -> `int32`; `CustomType | int` -> `CustomType`).
- Constraints named `Integer`, `Signed`, `Unsigned`, `Float`, `Complex`, or `Ordered` (including qualified names such as `constraints.Integer`) map to `int`.
- Other interface or named constraints map to `string`.

A generic free function call includes chosen type arguments, such as `Identity[int](...)` or `Pair[int, int](...)`. A method on a generic receiver instantiates the receiver (`*Container[int, int]`) but does not append type arguments to the method call (`c.Get()`, not `c.Get[int, int]()`); receiver type parameters do not appear in the method test name. Generic-result comparisons retain non-basic comparison behavior as described in Spec 13.

## Spec 17

The generated header uses the source package name exactly, including valid names beginning with `_`. Preserve all comments that occur before the source's `package` clause, including copyright/package comments, Unicode and special characters, `//go:build` directives, legacy `// +build` directives, and multiple comment groups with their intervening blank lines. Normalize CRLF source line endings to LF in generated output. After the final leading comment, always emit one empty line before the `package` clause; this blank line is inserted even when the source comment and package clause were adjacent. Thus a CRLF prefix `// π package\r\npackage p\r\n` becomes `// π package\n\npackage p\n`. Do not copy ordinary function documentation into the generated tests.

Imports must make the generated file self-contained and must be formatted/cleaned like `goimports`: always include `testing`; include source imports referenced by parameter/result/receiver-field types and retain explicit aliases; add `bytes`, `reflect`, `fmt`, `github.com/google/go-cmp/cmp`, or `github.com/stretchr/testify/assert` only when emitted code uses them; remove unused imports; group standard-library imports before a blank line and third-party imports. Existing test-file imports required by preserved code must remain semantically, but a successful merge rebuilds the declaration as a parenthesized block even if the existing file used `import "testing"` and `testing` is still the only import. The merged form is exactly:

```go
import (
	"testing"
)
```

Comments attached to imports in an existing declaration are not preserved: for example, comments immediately preceding `"go/ast"` and `"go/types"` disappear while those required import specs and the surrounding parenthesized block remain.

## Spec 18

`-w` maps a target `name.go` to the sibling `name_test.go`, creates it with ordinary file permissions when absent, and writes the formatted Go file there. It never prints generated Go code to stdout, only one `Generated <TestName>` banner per newly added test. It does not create any test file if validation fails or no test is generated.

Except for the observed malformed-merge case below, whether writing or printing, if the target test file already exists, parse and preserve its leading comments, package, import specs required by its code, declarations, test cases, comments within tests, and other code, then append newly generated tests and merge/format imports. Preservation is semantic rather than a byte-for-byte prefix guarantee: as specified in Specs 9 and 17, a preexisting single-line import is rewritten as a parenthesized block. A zero-byte existing sibling test file is treated as absent, so generation starts a fresh test file from the nonempty source; it does not produce the zero-byte source error from Spec 7. Do not regenerate a test whose exact generated `TestName` already exists; generate other missing tests. Never truncate existing content. Any other malformed existing test file produces the parse error described in Spec 7 rather than being overwritten. In stdout mode the complete merged would-be test file, including preserved existing tests, is printed.

There is one observed malformed-merge case even though both files parse successfully: if `top.go` contains `package p\nfunc Top() {}\n` and its existing sibling `top_test.go` contains `package p\nfunc ExistingHelper() {}\n`, processing `top.go` (including by supplying their directory) exits 0, emits no `Generated TestTop` banner, and prints one `output.Process: imports.Process:` line. Its temporary filename has the form `/tmp/gotests_<decimal-digits>` and the remainder is `:7:1: expected declaration, found unc`. This case is not governed by the successful preservation rule above.

When a directory is supplied, each eligible source file still maps to its own basename test file. Sibling source files may be consulted for type information and must be syntactically checked. A write target whose parent/source path does not exist produces the ordinary `input.Files: os.Stat: ...` operational error and exit 0.

## Spec 19

The default template described above is used when no template is selected. `-template testify` selects a built-in Testify style and imports `github.com/stretchr/testify/assert`. With subtests enabled and `-i` absent, value results use `assert.Equal(t, tt.want, Call(...))` for the one-result case, or assign results and call `assert.Equal` for each. In every Testify mode that needs diagnostic context—whenever `-nosubtests` or `-i` is present—use `assert.Equalf` instead. Its final message and arguments use the same qualified call label, table-name prefix, and printed inputs as Specs 13 and 15. For example:

```go
assert.Equalf(t, tt.want, Add(tt.args.a, tt.args.b), "%q. Add(%v, %v)", tt.name, tt.args.a, tt.args.b) // -nosubtests -i
assert.Equalf(t, tt.want, Add(tt.args.a, tt.args.b), "Add(%v, %v)", tt.args.a, tt.args.b)              // subtests -i
```

For a function returning an error, the table has `assertion assert.ErrorAssertionFunc`. With subtests and no `-i`, execute `tt.assertion(t, err)` and then use ordinary `assert.Equal` for value results. In contextual modes, pass a formatted context to the error assertion and use `Equalf` for values, importing `fmt`; examples include `tt.assertion(t, err, fmt.Sprintf("%q. Calculator.Divide()", tt.name))` under `-nosubtests` and `tt.assertion(t, err, fmt.Sprintf("Calculator.Divide(%v, %v)", tt.args.a, tt.args.b))` under subtests plus `-i`. In `-named -nosubtests` mode use the loop variable `name` rather than `tt.name`. Concretely, `-template=testify -named -nosubtests -parallel -i` for `func Divide(a int) (int, error)` emits `tt.assertion(t, err, fmt.Sprintf("%q. Divide(%v)", name, tt.args.a))`; the formatted context is a required third argument in this combination. Structural options (`named`, `parallel`, `nosubtests`, and `i`) otherwise affect the Testify skeleton as described in their respective sections. The `-i` writer placeholder behavior from Spec 15 also applies to Testify `Equalf` contexts.

`-use_go_cmp` replaces `reflect.DeepEqual` comparisons for non-basic values with:

```go
if got := Call(...); !cmp.Equal(tt.want, got) {
	t.Errorf("Call() = %v, want %v\ndiff=%s", got, tt.want, cmp.Diff(tt.want, got))
}
```

and imports `github.com/google/go-cmp/cmp`. Basic comparisons remain ordinary. A selected named template controls its own assertion strategy and takes precedence over `-use_go_cmp` when they would conflict.

## Spec 20

Template selection observes these rules:

1. A nonempty command-line `-template_dir` overrides `GOTESTS_TEMPLATE_DIR` and all named-template choices.
2. Otherwise a nonempty `GOTESTS_TEMPLATE_DIR` selects that directory.
3. Otherwise a nonempty command-line `-template` selects a built-in named template.
4. Otherwise use nonempty `GOTESTS_TEMPLATE`; an explicitly supplied empty `-template` still falls back to the environment value.
5. Otherwise use the built-in default.

A template directory consists of all `*.tmpl` Go `text/template` files and must define a usable `function` template plus any partials it invokes. A custom `header` definition is optional: when it is absent, rendering uses the built-in default header and proceeds to execute the custom `function`. Thus a directory containing only a `function` whose body evaluates `.UndefinedFunction` reports that execution error as `output.Process: render.TestFunction: ... can't evaluate field UndefinedFunction ...`; it is not rejected merely for lacking `header`. Header `Comments` is an iterable sequence of strings, not source text in one scalar string; iterate it to reproduce comments. Directly interpolating an empty collection as `{{.Comments}}` renders the literal `[]`, so placing that expression before `package` makes the rendered file invalid and produces `output.Process: imports.Process: /tmp/gotests_<decimal-digits>:1:1: expected 'package', found '['`. Header data also contains `Package` and an iterable `Imports` collection whose entries expose `Name` and quoted `Path`. Function data contains `Name`, `TestName`, `Receiver`, `Parameters`, `TestParameters`, `Results`, `TestResults`, `ReturnsError`, `OnlyReturnsError`, `OnlyReturnsOneValue`, `ReturnsMultiple`, `IsNaked`, `PrintInputs`, `Subtests`, `Parallel`, `Named`, `UseGoCmp`, `TemplateParams`, and `AIGeneratedCases`. Each parameter, result, receiver, and receiver-field entry exposes `Name` and a nested `Type` object; `Type` renders as the Go type when interpolated and exposes `Value`, `IsStar`, `IsVariadic`, and `IsWriter`, so expressions such as `.Type.IsVariadic` must work. These type flags are not promoted to a parameter/result entry: evaluating `.IsStar` directly while ranging over `.Parameters` fails with `can't evaluate field IsStar in type *models.Field`. Field entries also expose `IsWriter` and `IsBasicType`. Receiver data additionally exposes `IsStruct` and an iterable `Fields` collection. Provide template helper functions `Field`, `Param`, `Receiver`, `Want`, `Got`, and `TypeArgs` implementing the naming and concrete-generic-instantiation rules in this document. In particular, copied built-in partials that invoke `TypeArgs` must parse and execute rather than fail with an undefined-function error.

`-template_params JSON` parses its flag value as a JSON object and exposes it as `.TemplateParams`. `-template_params_file PATH` reads and parses the file; file parameters may be used with custom templates. Invalid inline JSON prints `Failed to unmarshal template_params JSON: <JSON error>`. A missing parameter file prints `Failed to read from <path> ,err open <path>: no such file or directory`. Invalid file JSON deliberately uses the spelling `Failed to umarshal <path> er <JSON error>`. Each of these three template-parameter validation messages ends immediately after the displayed error, with no trailing newline.

Missing/unreadable template directories, directories with no matching templates, template parse/execution failures, and invalid rendered Go are operational errors on stdout with exit 0. Do not emit partial generated code. Their observed forms are:

- A missing directory is exactly `output.Process: loading custom templates: ioutil.ReadDir: open <path>: no such file or directory` followed by a newline.
- An existing directory with no matching `*.tmpl` files is exactly `output.Process: loading custom templates: tmpls.ParseFiles: template: no files named in call to ParseFiles` followed by a newline.
- An unknown built-in name is exactly ``output.Process: loading custom templates of name: templates.ParseFS: template: pattern matches no files: `*.tmpl` `` followed by a newline. The unknown name itself is not interpolated into this message.
- Other template parse or execution failures begin `output.Process: render.TestFunction:` and retain the underlying Go template diagnostic.
- Invalid rendered Go begins `output.Process: imports.Process:` and retains the underlying parse/import diagnostic.

## Spec 21

AI mode is enabled only by `-ai`. AI tuning flags without `-ai` are accepted and do not alter ordinary generation. Defaults are model `qwen2.5-coder:0.5b`, endpoint `http://localhost:11434`, minimum 3, maximum 10. As soon as `-ai` is recognized (unless version/help already exited), write this warning to stderr, substituting the configured endpoint:

```text
⚠️  WARNING: Function source code will be sent to AI provider at <endpoint>
   Ensure your code does not contain secrets or sensitive information.

```

Then validate, in order: model is nonempty; minimum is at least 1; maximum is at most 100; minimum is not greater than maximum. A failure writes `Error: ...` to stderr after the warning and exits 1 before selector/path processing or file creation. Exact messages are:

```text
Error: -ai-model cannot be empty when using -ai flag
Error: -ai-min-cases must be at least 1, got <n>
Error: -ai-max-cases must be at most 100, got <n>
Error: -ai-min-cases (<min>) cannot be greater than -ai-max-cases (<max>)
```

Endpoints must parse as URLs and use only `http` or `https`; for example `file:///etc/passwd` is rejected during processing with `invalid endpoint: invalid URL scheme "file": only http and https are allowed` while the overall exit status remains 0. Before sending functions, probe the Ollama endpoint. An unreachable provider must fail quickly without hanging or panicking, exit 0, and print `output.Process: AI provider ollama is not available - ensure Ollama is running at <endpoint>` followed by a newline on stdout (in addition to the warning on stderr). Parsing complex function signatures and empty/trivial bodies must reach this same graceful availability failure.


## Spec 22

The following canonical example fixes the default formatting and ordering for the common case. Given:

```go
package math

func Add(a, b int) int { return a + b }
```

running `executable -all math.go` prints exactly this shape (including the banner and final newline):

```go
Generated TestAdd
package math

import "testing"

func TestAdd(t *testing.T) {
	type args struct {
		a int
		b int
	}
	tests := []struct {
		name string
		args args
		want int
	}{
		// TODO: Add test cases.
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Add(tt.args.a, tt.args.b); got != tt.want {
				t.Errorf("Add() = %v, want %v", got, tt.want)
			}
		})
	}
}
```

For methods, multiple results, errors, non-basic types, writers, generics, existing files, and option combinations, apply Specs 10–21 mechanically to this skeleton. The source declaration order determines test function order, and all rendering must remain deterministic for a single input file.
