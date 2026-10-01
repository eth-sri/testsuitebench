# Specification for `executable`

This file is the complete and authoritative behavioral specification for the required artifact.

## Spec 1

The required artifact is a directly runnable command-line program named exactly `executable`. It is a static checker for Go source code: it loads the Go packages or Go files named on its command line, finds discarded error results, writes findings, and exits with the status defined below. It must not require a subcommand and must not print banners, progress output, JSON, stack traces, or other text unless a later section explicitly requires that text.

The command is a single-mode program. Words such as `help`, `version`, `check`, `run`, `list`, `add`, and `analyze` are not commands or aliases; when supplied positionally, they are Go package patterns and normally fail as such. Error messages must not say `unknown command`, suggest a subcommand, or list a `Commands:`/`Subcommands:` section.

## Spec 2

Command-line parsing has the behavior of a conventional Go `flag` flag set. A flag may use one or two leading hyphens. Boolean flags are enabled by their presence. A value flag accepts both `-name=value` and `-name value`. Parsing stops at the first positional argument; every remaining argument, even one beginning with `-`, is a package/file argument. A standalone `--` also ends option parsing and is removed. Thus `-- -h` attempts to load a package named `-h` rather than showing help.

The recognized top-level flags are exactly:

- `-abspath` (boolean)
- `-asserts` (boolean)
- `-blank` (boolean)
- `-exclude string`
- `-excludeonly` (boolean)
- `-ignore value`
- `-ignoregenerated` (boolean)
- `-ignorepkg string`
- `-ignoretests` (boolean)
- `-mod string`
- `-tags value`
- `-verbose` (boolean)

There is no version flag or version subcommand. Unless stated otherwise, flags are independent and their effects compose regardless of the order in which they appear before the first positional argument.

## Spec 3

`-h`, `-help`, and `--help`, when encountered while options are still being parsed, write usage to standard error, write nothing to standard output, and exit 2. The first line contains the program name exactly as it appeared in argument zero; it is `Usage of <argv0>:`. Apart from substituting the real `<argv0>`, usage is exactly the following, including flag order, capitalization, line breaks, and indentation (the deeply indented description text is tab-indented in the same manner as shown):

```text
Usage of <argv0>:
  -abspath
    	print absolute paths to files
  -asserts
    	if true, check for ignored type assertion results
  -blank
    	if true, check for errors assigned to blank identifier
  -exclude string
    	Path to a file containing a list of functions to exclude from checking
  -excludeonly
    	Use only excludes from -exclude file
  -ignore value
    	[deprecated] comma-separated list of pairs of the form pkg:regex
    	            the regex is used to ignore names within pkg.
  -ignoregenerated
    	if true, checking of files with generated code is disabled
  -ignorepkg string
    	comma-separated list of package paths to ignore
  -ignoretests
    	if true, checking of _test.go files is disabled
  -mod string
    	module download mode to use: readonly or vendor. See 'go help modules' for more.
  -tags value
    	comma or space-separated list of build tags to include
  -verbose
    	produce more verbose logging
```

Here `    \t` describes four literal spaces followed by a tab, as emitted by Go-style flag help; it is not the two printable characters backslash and `t`. Help text ends in a newline. `-h` and `--help` produce byte-for-byte identical text when invoked with the same argument-zero spelling. A help flag parsed before any positional argument takes precedence over later flags. A help-looking word after `--` or after a positional argument does not.

## Spec 4

After flags are parsed, all positional arguments are package/file patterns to analyze. If there are none, the effective argument is `.` (the current directory). Supported inputs include:

- `.` and relative or absolute directories;
- ordinary Go import paths;
- the recursive Go package pattern `./...`;
- one or more `.go` filenames; and
- multiple directory/package arguments in one invocation.

Multiple named `.go` files are loaded together as the ad-hoc package `command-line-arguments`. A directory/package argument analyzes every build-selected source file in each directly matched package, not just one file. `./...` visits matched packages recursively, including deeply nested packages. Imported dependencies supply type information but are not themselves reported unless they are also directly selected by an input pattern. Overlapping package variants, including test variants, must not cause duplicate findings for the same source occurrence.

Both `package main` and library packages without a `main` function are valid analysis targets. Package semantics and static type information must be resolved across files and across imports, so calls through interfaces, imported packages, methods, function-valued maps, and embedded interfaces are understood correctly.

## Spec 5

Package loading obeys Go build constraints. Both modern `//go:build` expressions and legacy `// +build` constraints are recognized. Normal platform/toolchain tags remain active; user tags augment them. Boolean build expressions, including `!`, `&&`, and `||`, determine which files are analyzed.

`-tags` supplies additional tags. Its value is split at every comma or ordinary space, empty pieces are discarded, and names containing underscores remain intact. Consequently `custom1,custom2`, `custom1 custom2`, `custom1, custom2`, and `custom1,,custom2` all activate `custom1` and `custom2`. An empty value has the same effect as omitting the flag. Repeating `-tags` accumulates all supplied tags. Both `-tags=x` and `-tags x` are accepted. Only build-selected files may produce findings.

## Spec 6

`-mod` controls the module download mode used while loading packages. An omitted or empty value leaves Go's normal module resolution unchanged. The values `mod`, `readonly`, and `vendor` are accepted and passed through with their ordinary meanings; in particular, vendor mode must work without fetching a vendored dependency from the network. `-mod=value` and `-mod value` are equivalent, and `-mod` composes with `-tags` in either order.

An unsupported value is a package-loading fatal error, not an unknown-flag error, and does not print usage. For `-mod=invalid`, the diagnostic is:

```text
error: failed to check packages: err: exit status 1: stderr: -mod=invalid not supported (can be '', 'mod', 'readonly', or 'vendor')
```

It is written to standard error, followed by exactly two consecutive LF bytes
(`\n\n`): the first terminates the displayed diagnostic and the second creates
one empty line after it. Standard output is empty and the process exits 2.

## Spec 7

The primary finding is an ignored result of a call when at least one returned value is an error type. The built-in `error` interface is the interface containing `Error() string`. A result counts as error-like when its static type implements that interface. This includes the built-in `error` interface itself, user-defined concrete value types with an `Error() string` method, pointer types whose method set implements the interface, and interface methods reached through embedded-interface chains. For a tuple-returning function, every tuple element is classified independently; a bare call is a finding if any element is error-like.

Examples that must be recognized include package functions (`os.Open`), local functions, variadic functions, named-result functions, functions returning `(value, error)` or `(error, value)`, methods with value or pointer receivers, interface method calls, nested selectors such as `x.member.Method()`, function values retrieved from a map, and immediately invoked function literals.

How an error value was constructed is irrelevant: calls remain reportable when their implementation creates a custom error, wraps another error (including formatting with `%w`), unwraps one, works with a context, or communicates through channels.

The built-in `recover()` is a special error-like call for this checker even though its language return type is not `error`. A discarded bare `recover()`, `defer recover()`, and—when blank checking is enabled—`_ = recover()` are findings.

## Spec 8

A result is ignored when an error-returning call is used as a standalone expression statement, or when its results are discarded by a `go` or `defer` statement. Report these calls wherever they occur: ordinary function bodies, anonymous functions and closures, immediately invoked functions, goroutines, deferred anonymous functions, nested blocks, `if` blocks, all forms of `for` loop, switch cases (including type-switch cases), select cases, and default branches. The checker must walk arbitrarily nested valid syntax rather than limiting analysis to top-level statements.

An ordinary ignored call produces one finding at the opening parenthesis of the invocation, even if it returns a tuple. For example, in four-space-indented `os.Open("x")`, the `(` is column 12. For `defer f.Close()`, the position is the `(` after `Close`, while the printed source excerpt is the complete `defer` line.

A call is considered handled if its error result is assigned to a nonblank variable, used as a value in another expression, or returned. The program performs no data-flow analysis after assignment: assigning an error to a named variable is sufficient even if that variable is later overwritten or the error is never inspected. Calls returning no error-like result are not findings merely because their values are discarded.

## Spec 9

By default, assigning an error result to Go's blank identifier `_` is treated as an explicit discard and is not reported. `-blank` enables these findings in assignments, short declarations, and `var` declarations.

Return positions must be mapped to assignment positions. Only a `_` receiving an error-like result is reported; a `_` receiving a non-error value is not. Examples include the second underscore in `file, _ := os.Open("x")`, the second underscore in `_, _ = f()` when `f` returns `(value, error)`, and the first underscore in `_, n := errorOnly(), 5`. With several independent right-hand expressions, match each expression to its corresponding left-hand target. Each report is positioned at the relevant `_`, not at the call's parenthesis, and prints the entire trimmed source line. `recover()` follows the same rule. Exclusion and ignore rules also suppress matching blank-assignment findings.

Enabling `-blank` does not report blanks which receive ordinary non-error values, and it does not by itself turn a type assertion's boolean `ok` result into an error; type assertions have the separate rules in the next section.

## Spec 10

By default, type assertions are not checked. `-asserts` reports non-comma-ok assertions such as `v := x.(T)`, `v = x.(T)`, `_ = x.(T)`, and assertions used in larger expressions. A report for such an assertion is positioned at the beginning of the asserted expression (the `x` in `x.(T)`), not at the assignment target. A type switch `switch x.(type)` is never a finding.

A comma-ok assertion such as `v, ok := x.(T)` or `v, ok = x.(T)` is considered checked. If its `ok` target is `_`, it is still not reported by `-asserts` alone; when both `-asserts` and `-blank` are enabled, it is reported once at that second `_`.

There is one observable multi-expression assignment behavior that must be preserved. For a line such as:

```go
a, b := x.(int), x.(string)
```

`-asserts` emits four findings on that line, sorted by column: one at `a`, one at `b`, one at the first right-hand `x`, and one at the second right-hand `x`. In general, when an assignment has multiple right-hand expressions, each right-hand type assertion creates both the assignment-target-position report and the assertion-expression-position report. A single assertion on the right-hand side follows the preceding single-report/comma-ok rules.

## Spec 11

Test files are included by default. `-ignoretests` excludes files whose names end in `_test.go` from package loading and analysis while continuing to analyze ordinary files in the same package.

Generated source is also included by default. With `-ignoregenerated`, a source file produces no findings if any of its line comments matches this case-sensitive, whole-comment pattern:

```text
^// Code generated .* DO NOT EDIT\.$
```

For example, `// Code generated by protoc-gen-go. DO NOT EDIT.` marks the file generated. Nonmatching files must still be analyzed when the flag is present. These filters affect only their intended file classes and compose with all checking flags.

## Spec 12

Unless `-excludeonly` is present, the following 29 resolved call patterns are excluded by default. Names use import paths, and receiver notation distinguishes value receivers/interfaces from pointer receivers:

```text
(*bytes.Buffer).Write
(*bytes.Buffer).WriteByte
(*bytes.Buffer).WriteRune
(*bytes.Buffer).WriteString
crypto/rand.Read
fmt.Print
fmt.Printf
fmt.Println
fmt.Fprint(*bytes.Buffer)
fmt.Fprintf(*bytes.Buffer)
fmt.Fprintln(*bytes.Buffer)
fmt.Fprint(*strings.Builder)
fmt.Fprintf(*strings.Builder)
fmt.Fprintln(*strings.Builder)
fmt.Fprint(os.Stderr)
fmt.Fprintf(os.Stderr)
fmt.Fprintln(os.Stderr)
(*io.PipeReader).CloseWithError
(*io.PipeWriter).CloseWithError
math/rand.Read
(*math/rand.Rand).Read
(*strings.Builder).Write
(*strings.Builder).WriteByte
(*strings.Builder).WriteRune
(*strings.Builder).WriteString
(hash.Hash).Write
(*hash/maphash.Hash).Write
(*hash/maphash.Hash).WriteByte
(*hash/maphash.Hash).WriteString
```

These are exact exclusions, not prefixes. Thus `fmt.Fprintln(os.Stdout, ...)`, `fmt.Fprintln` to an arbitrary `*os.File`, `io.WriteString`, `io.Copy`, `os.Open`, and names merely resembling a listed symbol remain reportable. Import aliases do not change resolved identity. `-excludeonly` removes the complete built-in list, even when no custom exclude file is supplied; all 29 patterns are then reportable if their results are discarded.

## Spec 13

`-exclude PATH` reads custom exact symbol exclusions from `PATH` before loading target packages. Without `-excludeonly`, they augment the 29 defaults. With `-excludeonly`, they are the only symbol exclusions. An empty or comments-only file contributes no custom symbols; duplicate entries are harmless.

The file is scanned as newline-delimited text. An exactly empty line and any line whose first two characters are `//` are skipped. No other whitespace is trimmed: `  os.Open  ` does not match `os.Open`, and a line beginning with spaces followed by `//` is not a comment. Windows CRLF endings are accepted with the trailing carriage return removed. A single leading `/` is not a comment. Entry matching is literal, exact, and case-sensitive; entries such as `os.Ope`, `Open`, `OS.Open`, and `os.open` do not match `os.Open`.

Relative paths, `..` components, absolute paths, and symbolic links use normal filesystem resolution from the current working directory. Lines around 10 KiB must work. Scanning uses a roughly 64 KiB maximum token size; an overlong line (for example 70,000 bytes) is fatal with `Could not read exclude file: bufio.Scanner: token too long`. A missing file and a directory used as the file are also fatal as detailed in Spec 20.

## Spec 14

A custom symbol entry can have these forms:

- `import/path.Function` for a package function;
- `(import/path.Type).Method` for a value/interface receiver;
- `(*import/path.Type).Method` for a pointer receiver; or
- a package function followed immediately by `(FIRST_ARGUMENT)`, such as `fmt.Fprintf(*strings.Builder)`, `fmt.Fprintln(os.Stderr)`, or `io.Copy(*bytes.Buffer)`.

Matching uses statically resolved function and receiver identities. Parentheses, dots, and `*` are literal syntax, not regular-expression metacharacters. When a method is selected through embedded interfaces, all applicable embedded-interface receiver identities are candidates, which permits `(hash.Hash).Write` to match implementations reached through that interface. Calls written as unqualified local identifiers such as `localFunc()` have no selector-qualified identity and are not matched by a symbol-file entry.

For a first-argument-qualified entry, ordinary types use the first argument's static type string. `os.Stdout` and `os.Stderr` are special value-qualified forms and match only a first argument that is syntactically that resolved package variable; `os.Stderr` does not match `os.Stdout` or a different variable of type `*os.File`. Vendored third-party symbols use their full resolved vendored import path in custom symbol entries.

## Spec 15

`-ignore` is a deprecated regex-based suppression flag. Its value is a comma-separated series of `package:regex` pairs. The package and colon may be omitted, in which case the regex applies globally. Split a pair at its first colon, compile the remainder as a Go/RE2-style regular expression, and search the callee's final identifier (for example `Open` or `WriteString`), rather than its full source spelling. Matching is case-sensitive and unanchored unless the expression supplies anchors. Therefore `os:Open` also matches `OpenFile`, `os:Open$` does not, `os:Open.ile` uses `.` as a wildcard, and `os:^(Open|Create)$` matches exactly those two identifiers. A global `Open` applies across packages.

An empty entire value is a no-op. Multiple comma-separated pairs for distinct packages all apply. If the same package key is supplied again, including in a later `-ignore` occurrence, its later regex replaces the earlier regex for that package; different package keys remain present. (A comma-created empty pair inside an otherwise nonempty value is an empty global regex and therefore matches every supported callee name.) `-ignore` and custom/default symbol exclusions are combined: a finding suppressed by either mechanism is absent.

An invalid regex is a flag-parse error. For example, `-ignore 'os:[invalid('` starts its standard-error diagnostic with:

```text
invalid value "os:[invalid(" for flag -ignore: error parsing regexp: missing closing ]: `[invalid(`
```

and then prints the complete usage text and exits 2.

## Spec 16

`-ignorepkg` is a comma-separated list of resolved package import paths whose called functions and methods are to be suppressed. Empty components—including trailing commas and doubled commas—are ignored. It applies equally to standard-library and third-party paths, and it takes precedence over a narrower `-ignore` regex for the same package. Vendored identities are compared after removing the enclosing `/vendor/` prefix.

This flag suppresses calls *into* the named package; it does not skip source files whose own package has that path. For example, while analyzing all packages in a module, ignoring package `example.com/p/pkg2` removes calls to `pkg2` from any file, but a source file in `pkg2` is still walked and can report its unchecked call into `pkg1`. If all otherwise reportable calls are suppressed, the command exits 0.

## Spec 17

Every ordinary finding is written to standard output as one newline-terminated line. In nonverbose mode its exact form is:

```text
<file>:<line>:<column>:\t<trimmed physical source line>\n
```

There is one literal tab after the final colon. `line` and `column` are one-based. For calls, the column is the byte column of the opening `(`; for blank assignments and type assertions use the positions in Specs 9 and 10. Columns follow Go token positions: they count UTF-8 bytes from the start of the physical line, and a source tab occupies one byte for this purpose. The source excerpt is the complete physical source line with leading and trailing Unicode whitespace removed; internal spacing, punctuation, escape sequences, inline comments, and Unicode characters are preserved exactly. Very long lines must not be truncated.

For example:

```text
main.go:6:12:\tos.Open("test.txt")
main.go:7:11:\tos.Remove("file.txt") // unchecked
```

No explanatory prefix such as `unchecked error:` is added. Clean analysis produces no standard-output bytes.

## Spec 18

Without `-abspath`, each finding's filename is made relative to the process's current working directory. Preserve subdirectory structure and `..` components naturally: analyzing `./subdir` from its parent reports `subdir/main.go`, analyzing `.` inside that subdirectory reports `main.go`, and analyzing an outside directory may report `../other/main.go`. Filenames containing hyphens, underscores, and multiple dots are preserved. Recursive results show paths such as `pkg/util/util.go` rather than only basenames.

With `-abspath`, each finding begins with the normalized absolute source filename. This flag changes only the filename portion; it does not alter findings, locations, source excerpts, ordering, or exit status. It composes with every other flag and must work for long/deep paths and large output.

## Spec 19

`-verbose` adds package progress messages and, where available, a resolved callee identity. Before checking each directly selected package, write this newline-terminated line to standard error:

```text
checking <resolved-package-path>
```

For a module package the path is its import path; for explicitly supplied files it is `command-line-arguments`. These progress lines never go to standard output.

If a finding's call is a selector whose referenced function or method can be resolved, verbose standard output has three tab-separated fields:

```text
<file>:<line>:<column>:\t<resolved-callee>\t<trimmed source line>\n
```

Package functions appear as `os.Open` or `fmt.Fprintln`. Methods include their receiver, for example `(*os.File).Close`, `(*command-line-arguments.MyStruct).PointerMethod`, `(command-line-arguments.MyStruct).ValueMethod`, and `(command-line-arguments.Interface).InterfaceMethod`. Use the defining import path rather than a source import alias.

Plain identifier calls (`localFunc()`), map/function-value calls, anonymous calls, `recover`, and type-assertion-only reports have no resolved selector identity. Such findings retain the normal two-field format even in verbose mode. Thus verbose mode does not insert an empty middle field. `-verbose -abspath` combines the absolute filename with the same conditional callee column.

## Spec 20

Findings are deduplicated and sorted before printing. Sort first by source filename lexicographically, then by numeric line, then by numeric column, and finally by source excerpt for otherwise equal positions. Identical findings introduced because one source file belongs to multiple loaded package variants appear once. Multiple distinct calls on one line remain distinct and are ordered by column.

There is no maximum findings count or practical small-input buffer limit. The executable must report every occurrence in files with at least 200 findings, packages with at least 50 files/100 findings, recursive projects with at least 20 packages, 15 or more nested scopes, source files beyond 1,000 lines, source lines beyond 1,000 characters, long identifiers, deeply nested filesystem paths, and valid Unicode identifiers/source text.

Exit status and stream rules are:

- Exit 0 when package loading and checking succeed and no unsuppressed finding exists. Normal stdout and stderr are empty, except that `-verbose` may have its required progress lines.
- Exit 1 when one or more unsuppressed findings exist. All finding lines go to stdout; stderr is empty except for required verbose progress lines.
- Exit 2 for flag parsing failures, unreadable exclusion configuration, or failures to load/type-check the requested packages. Fatal diagnostics go to stderr and no finding output is produced.

An unknown flag writes `flag provided but not defined: -<name>`, a newline, and the complete usage text from Spec 3 to stderr, then exits 2. Missing or malformed flag values behave analogously. Invalid Go syntax/type information, and a package/file/directory loading failure that the package loader surfaces as an error, are reported beginning:

```text
error: failed to check packages: 
```

The remainder preserves the package loader's concrete explanation, including the requested pattern, absolute filesystem path where applicable, and compiler/parser details. There are two specifically silent empty-match cases. From an empty current working directory, requesting `.` exits 0 with empty stdout and stderr. From that same empty directory, requesting the nonexistent relative subdirectory `./nonexistent` also exits 0 with empty stdout and stderr. Neither invocation is diagnosed as a loading failure.

Syntax failures likewise include `errors while loading package <package-id>` and the underlying `syntax error`/position messages, without a panic or traceback. Failure to read an exclude file instead uses exactly this prefix without `error:`:

```text
Could not read exclude file: <operating-system-or-scanner-error>
```

For example, a missing relative file is `Could not read exclude file: open nonexistent.txt: no such file or directory`, and a directory is `Could not read exclude file: read unreadable_dir: is a directory`. Every diagnostic ends with a newline; the invalid-`-mod` diagnostic has the two-LF termination specified in Spec 6.
