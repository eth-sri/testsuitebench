# Executable behavioral specification

The required artifact is a directly runnable file named `executable`. It implements the command-line Go source linter described below. All text is UTF-8. Unless a rule explicitly says otherwise, every emitted line ends in `\n`.

## Spec 1

The command line is `executable <command> [arguments...]`. The supported, case-sensitive commands are `check`, `doc`, `help`, and `version`.

`help`, `version`, and successful `doc` output go to standard output and leave standard error empty. `check` never writes ordinary diagnostics to standard output: lint diagnostics, verbose lines, argument errors, and panic text go to standard error. A clean non-verbose check writes nothing to either stream.

The process must terminate promptly (ordinary invocations are expected to finish in under five seconds), except for the `-concurrency=0` check case specified in Spec 10. It must accept absolute and relative paths containing whitespace and UTF-8 source text. It must not require network access.

## Spec 2

With no command, exit 0, write nothing to stdout, and write exactly:

```text
no args provided
```

An unrecognized command exits 0 and writes to both streams. For `invalidcmd`, stdout is exactly:

```text
"invalidcmd" unknown command
Run "go-critic help" for usage.

```

and stderr is exactly `no such command "invalidcmd"\n`. The token `invalid_command` has the same layout with that token substituted: its stdout is `"invalid_command" unknown command\nRun "go-critic help" for usage.\n\n`, and its stderr is `no such command "invalid_command"\n`. Command names are case-sensitive: `Help` exits 0, writes `"Help" unknown command, did you mean "help"?\nRun "go-critic help" for usage.\n\n` to stdout, and writes `no such command "Help"\n` to stderr.

Top-level `--help` is not a global flag. It exits 0, writes `"--help" unknown command, did you mean "help"?\nRun "go-critic help" for usage.\n\n` to stdout, and writes `no such command "--help"\n` to stderr. Top-level `-h` is likewise not global: it exits 0, writes `"-h" unknown command\nRun "go-critic help" for usage.\n\n` to stdout, and writes `no such command "-h"\n` to stderr.

The `help` and `version` commands ignore all trailing arguments. Command and checker names are case-sensitive.

## Spec 3

`version` exits 0 and prints exactly:

```text
go-critic version: v0.0.0-SNAPSHOT

```

`help` exits 0 and prints exactly the following, including blank lines and indentation:

```text
Usage:

    go-critic <command> [arguments...]

The commands are:

    check             run linter over specified targets
    doc               get installed checkers documentation
    help              shows help message
    version           shows version of the application

Version: v0.0.0-SNAPSHOT

```

## Spec 4

`doc` with no positional argument exits 0 and prints the following registry exactly in this order. This registry also defines the valid checker names and their tag memberships.

```text
appendAssign [diagnostic]
appendCombine [performance]
argOrder [diagnostic]
assignOp [style]
badCall [diagnostic]
badCond [diagnostic]
badLock [diagnostic experimental]
badRegexp [diagnostic experimental]
badSorting [diagnostic experimental]
badSyncOnceFunc [diagnostic experimental]
boolExprSimplify [style experimental]
builtinShadow [style opinionated]
builtinShadowDecl [diagnostic experimental]
captLocal [style]
caseOrder [diagnostic]
codegenComment [diagnostic]
commentFormatting [style]
commentedOutCode [diagnostic experimental]
commentedOutImport [style experimental]
defaultCaseOrder [style]
deferInLoop [diagnostic experimental]
deferUnlambda [style experimental]
deprecatedComment [diagnostic]
docStub [style experimental]
dupArg [diagnostic]
dupBranchBody [diagnostic]
dupCase [diagnostic]
dupImport [style experimental]
dupOption [diagnostic experimental]
dupSubExpr [diagnostic]
dynamicFmtString [diagnostic experimental]
elseif [style]
emptyDecl [diagnostic experimental]
emptyFallthrough [style experimental]
emptyStringTest [style experimental]
equalFold [performance experimental]
evalOrder [diagnostic experimental]
exitAfterDefer [diagnostic]
exposedSyncMutex [style experimental]
externalErrorReassign [diagnostic experimental]
filepathJoin [diagnostic experimental]
flagDeref [diagnostic]
flagName [diagnostic]
hexLiteral [style experimental]
httpNoBody [style experimental]
hugeParam [performance]
ifElseChain [style]
importShadow [style opinionated]
indexAlloc [performance]
initClause [style opinionated experimental]
mapKey [diagnostic]
methodExprCall [style experimental]
nestingReduce [style opinionated experimental]
newDeref [style]
nilValReturn [diagnostic experimental]
octalLiteral [style experimental opinionated]
offBy1 [diagnostic]
paramTypeCombine [style opinionated]
preferDecodeRune [performance experimental]
preferFilepathJoin [style experimental]
preferFprint [performance experimental]
preferStringWriter [performance experimental]
preferWriteByte [performance experimental opinionated]
ptrToRefParam [style opinionated experimental]
rangeAppendAll [diagnostic experimental]
rangeExprCopy [performance]
rangeValCopy [performance]
redundantSprint [style experimental]
regexpMust [style]
regexpPattern [diagnostic experimental]
regexpSimplify [style experimental opinionated]
returnAfterHttpError [diagnostic experimental]
ruleguard [style experimental]
singleCaseSwitch [style]
sliceClear [performance experimental]
sloppyLen [diagnostic]
sloppyReassign [diagnostic experimental]
sloppyTypeAssert [diagnostic]
sortSlice [diagnostic experimental]
sprintfQuotedString [diagnostic experimental]
sqlQuery [diagnostic experimental]
stringConcatSimplify [style experimental]
stringXbytes [performance]
stringsCompare [style experimental]
switchTrue [style]
syncMapLoadAndDelete [diagnostic experimental]
timeExprSimplify [style experimental]
todoCommentWithoutDetail [style opinionated experimental]
tooManyResultsChecker [style opinionated experimental]
truncateCmp [diagnostic experimental]
typeAssertChain [style experimental]
typeDefFirst [style experimental]
typeSwitchVar [style]
typeUnparen [style opinionated]
uncheckedInlineErr [diagnostic experimental]
underef [style]
unlabelStmt [style experimental]
unlambda [style]
unnamedResult [style opinionated experimental]
unnecessaryBlock [style opinionated experimental]
unnecessaryDefer [diagnostic experimental]
unslice [style]
valSwap [style]
weakCond [diagnostic experimental]
whyNoLint [style experimental]
wrapperFunc [style]
yodaStyleExpr [style experimental]
zeroByteRepeat [performance]
```

## Spec 5

`doc NAME` accepts exactly one checker name. An unknown or incorrectly cased name exits 1, writes nothing to stdout, and writes `checker with name "NAME" not found\n`; this also applies when `NAME` is the empty string. More than one positional argument exits 1 with exactly `expected 0 or 1 positional arguments\n` on stderr. `doc --invalid-flag` is a special parse-error path: it exits 0 and stderr is exactly:

```text
flag provided but not defined: -invalid-flag
Usage of go-critic:
flag provided but not defined: -invalid-flag
```

Every successful single-checker document begins with `NAME checker documentation`, then `URL: https://github.com/go-critic/go-critic/checkers`, then `Tags: [...]`, and contains meaningful prose. In particular, documents for `assignOp`, `badCall`, `rangeExprCopy`, and `badLock` must identify respectively style/assignment, diagnostic, performance, and experimental behavior. The exact documents tested most strictly are given in Specs 6 and 7.

## Spec 6

The following `doc` results are exact (each block has a final newline).

For `appendAssign`:

```text
appendAssign checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [diagnostic]

Detects suspicious append result assignments.

Non-compliant code:
p.positives = append(p.negatives, x)
p.negatives = append(p.negatives, y)

Compliant code:
p.positives = append(p.positives, x)
p.negatives = append(p.negatives, y)
```

For `dupSubExpr`:

```text
dupSubExpr checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [diagnostic]

Detects suspicious duplicated sub-expressions.

Non-compliant code:
sort.Slice(xs, func(i, j int) bool {
	return xs[i].v < xs[i].v // Duplicated index
})

Compliant code:
sort.Slice(xs, func(i, j int) bool {
	return xs[i].v < xs[j].v
})
```

For `builtinShadow`:

```text
builtinShadow checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [style opinionated]

Detects when predeclared identifiers are shadowed in assignments.

Non-compliant code:
len := 10

Compliant code:
length := 10
```

For `commentFormatting`:

```text
commentFormatting checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [style]

Detects comments with non-idiomatic formatting.

Non-compliant code:
//This is a comment

Compliant code:
// This is a comment
```

For `exitAfterDefer`:

```text
exitAfterDefer checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [diagnostic]

Detects calls to exit/fatal inside functions that use defer.

Non-compliant code:
defer os.Remove(filename)
if bad {
	log.Fatalf("something bad happened")
}

Compliant code:
defer os.Remove(filename)
if bad {
	log.Printf("something bad happened")
	return
}
```

For `badRegexp`:

```text
badRegexp checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [diagnostic experimental]

Detects suspicious regexp patterns.

Non-compliant code:
regexp.MustCompile(`(?:^aa|bb|cc)foo[aba]`)

Compliant code:
regexp.MustCompile(`^(?:aa|bb|cc)foo[ab]`)
```

For `unslice`:

```text
unslice checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [style]

Detects slice expressions that can be simplified to sliced expression itself.

Non-compliant code:
copy(b[:], values...)

Compliant code:
copy(b, values...)
```

For `valSwap`:

```text
valSwap checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [style]

Detects value swapping code that are not using parallel assignment.

Non-compliant code:
*tmp = *x; *x = *y; *y = *tmp

Compliant code:
*x, *y = *y, *x
```

## Spec 7

The parameterized documents are exact as follows.

For `hugeParam`:

```text
hugeParam checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [performance]

Detects params that incur excessive amount of copying.

Non-compliant code:
func f(x [1024]int) {}

Compliant code:
func f(x *[1024]int) {}

Checker parameters:
  -@hugeParam.sizeThreshold int
    	size in bytes that makes the warning trigger (default 80)
```

For `rangeValCopy`:

```text
rangeValCopy checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [performance]

Detects loops that copy big objects during each iteration.

Suggests to use index access or take address and make use pointer instead.

Non-compliant code:
xs := make([][1024]byte, length)
for _, x := range xs {
	// Loop body.
}

Compliant code:
xs := make([][1024]byte, length)
for i := range xs {
	x := &xs[i]
	// Loop body.
}

Checker parameters:
  -@rangeValCopy.sizeThreshold int
    	size in bytes that makes the warning trigger (default 128)
  -@rangeValCopy.skipTestFuncs bool
    	whether to check test functions (default true)
```

For `ifElseChain`:

```text
ifElseChain checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [style]

Detects repeated if-else statements and suggests to replace them with switch statement.

Non-compliant code:
if cond1 {
	// Code A.
} else if cond2 {
	// Code B.
} else {
	// Code C.
}

Compliant code:
switch {
case cond1:
	// Code A.
case cond2:
	// Code B.
default:
	// Code C.
}

Permits single else or else-if; repeated else-if or else + else-if
will trigger suggestion to use switch statement.
See [EffectiveGo#switch](https://golang.org/doc/effective_go.html#switch).

Checker parameters:
  -@ifElseChain.minThreshold int
    	min number of if-else blocks that makes the warning trigger (default 2)
```

For `nestingReduce`:

```text
nestingReduce checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [style opinionated experimental]

Finds where nesting level could be reduced.

Non-compliant code:
for _, v := range a {
	if v.Bool {
		body()
	}
}

Compliant code:
for _, v := range a {
	if !v.Bool {
		continue
	}
	body()
}

Checker parameters:
  -@nestingReduce.bodyWidth int
    	min number of statements inside a branch to trigger a warning (default 5)
```

For `ruleguard`, print this exact document:

```text
ruleguard checker documentation
URL: https://github.com/go-critic/go-critic/checkers
Tags: [style experimental]

Runs user-defined rules using ruleguard linter.

Reads a rules file and turns them into go-critic checkers.

Non-compliant code:
N/A

Compliant code:
N/A

See https://github.com/quasilyte/go-ruleguard.

Checker parameters:
  -@ruleguard.debug string
    	enable debug for the specified named rules group (default )
  -@ruleguard.disable string
    	comma-separated list of disabled groups or skip empty to enable everything (default )
  -@ruleguard.enable string
    	comma-separated list of enabled groups or skip empty to enable everything (default <all>)
  -@ruleguard.failOn string
    	Determines the behavior when an error occurs while parsing ruleguard files.
If flag is not set, log error and skip rule files that contain an error.
If flag is set, the value must be a comma-separated list of error conditions.
* 'import': rule refers to a package that cannot be loaded.
* 'dsl':    gorule file does not comply with the ruleguard DSL. (default )
  -@ruleguard.failOnError bool
    	deprecated, use failOn param; if set to true, identical to failOn='all', otherwise failOn='' (default false)
  -@ruleguard.rules string
    	comma-separated list of gorule file paths. Glob patterns such as 'rules-*.go' may be specified (default )
```

## Spec 8

`check [flags] [targets...]` parses and analyzes explicitly named Go source files, including multiple file targets. With no targets, including when `-enable=unslice` is the only argument, do not scan the current directory: exit 0 with both streams empty even if it contains a Go file with an unslice finding.

Individual nonexistent paths, nonexistent directories, empty-string targets, non-`.go` files, and empty directories exit 0 without output. If a nonexistent file target precedes an otherwise analyzable Go file in the same invocation, the entire invocation likewise exits 0 without analyzing the valid file. In a module-free directory containing standalone Go files, the targets `.`, a directory name, and `./...` each exit 0 without output; nested files are not discovered. Follow a symlink to an individual Go file, but a symlink to such a module-free directory exits 0 without analysis. Invalid Go syntax is silently skipped rather than diagnosed. Package declarations, imports, build tags, type aliases, generics, methods, goroutines, channels, `defer`, `init`, variadic and anonymous functions, closures, `select`, embedded structs, Unicode comments/strings, and long paths must not prevent ordinary matching in an explicitly named source file.

Files whose basename ends `_test.go` are analyzed by default; `-checkTests=false` skips them and `-checkTests=true` includes them. Files beginning with a standard generated-code marker such as `// Code generated by tool. DO NOT EDIT.` are skipped by default; `-checkGenerated` and `-checkGenerated=true` include them, while `-checkGenerated=false` skips them.

## Spec 9

Each lint finding is one stderr line:

```text
DISPLAY_PATH:LINE:COLUMN: checkerName: message
```

Line and column are one-based byte positions at the syntactic construct identified in the checker tables. Stdout remains empty. Findings cause the configured lint exit code (default 1); no findings cause exit 0 even if a nondefault exit code was configured. `-exitCode=N` accepts zero, negative, and positive integers. A zero lint exit code still emits findings. Positive values such as 7, 42, and 99 are returned exactly when findings exist.

Default `-shorterErrLocation=true` renders an explicitly supplied relative file target with a leading `./`: for example, `sample.go`, `loc.go`, and `sub/nested.go` are displayed as `./sample.go`, `./loc.go`, and `./sub/nested.go`. For a file discovered from target `.` or a directory, display its path relative to that directory without an absolute prefix. An explicitly supplied absolute temporary file remains absolute. With `-shorterErrLocation=false`, use a full path; in every mode the displayed name must at least contain the source basename.

Where multiple targets are given, preserve target/file order. Within a file, checker groups follow enabled-checker registry order; preserve a checker's own source traversal order. In particular, default findings on `x == x && x == x` are `badCond`, then the outer `dupSubExpr` for `&&`, then the two `dupSubExpr` equality findings, and a later `unslice` checker can be printed after those even if its source location is earlier.

## Spec 10

The default enabled set is exactly:

```text
appendAssign,argOrder,assignOp,badCall,badCond,captLocal,caseOrder,codegenComment,commentFormatting,defaultCaseOrder,deprecatedComment,dupArg,dupBranchBody,dupCase,dupSubExpr,elseif,exitAfterDefer,flagDeref,flagName,ifElseChain,mapKey,newDeref,offBy1,regexpMust,singleCaseSwitch,sloppyLen,sloppyTypeAssert,switchTrue,typeSwitchVar,underef,unlambda,unslice,valSwap,wrapperFunc
```

`-enable=A,B` replaces the default set with the union of the named checkers/tags. `-disable=A,B` removes members from the current set. A `#tag` expands to registry entries having that tag. Mixed names and tags and long comma-separated lists work. Disable takes precedence when a checker appears in both lists. `-enableAll` is accepted as broad selection and remains filtered by `-disable`; specifically, `-enableAll -disable=#experimental` still runs non-experimental `unslice`, while `-enableAll -disable=unslice` still runs `badCond` and `dupSubExpr`. Experimental and opinionated checkers do not run in the stated default set but do run when explicitly named.

Boolean flags accept bare form for true and `=true`/`=false`. Value-taking flags accept both `-flag=value` and two-token `-flag value`; in particular both `-exitCode=7` and `-exitCode 7` work.

Unknown names and tags are ignored during expansion. If selection produces no checkers (including empty `-enable=`, only an unknown selector, or enabling and disabling the same sole checker), exit 1 and write exactly `init checkers: empty checkers set selected\n`.

Supported configuration flags include:

- `-concurrency=N` (default runtime parallelism), accepting 1 and positive integers for normal checking. The value 0 is parsed, but with an analyzable file it blocks without emitting output and does not terminate;
- `-go=VERSION` or `-go VERSION`, accepting numeric major/minor forms including `1.12`, `1.13`, `1.18`, `1.20`, `1.21`, and `2.0`;
- `-cpuprofile=PATH` and `-memprofile=PATH`, each creating a nonempty file on successful checking;
- checker parameters `-@captLocal.paramsOnly=BOOL` (default true), `-@hugeParam.sizeThreshold=N` (80), `-@ifElseChain.minThreshold=N` (2), `-@rangeExprCopy.sizeThreshold=N` (512), `-@rangeValCopy.sizeThreshold=N` (128), `-@tooManyResultsChecker.maxResults=N` (5), `-@unnamedResult.checkExported=BOOL` (false), and the `ruleguard` values listed in Spec 7.

Very large integer thresholds such as 999999999 are accepted. With a negative concurrency and at least one real package/file to process, preserve the observed runtime failure: exit nonzero and put a Go-style panic trace on stderr containing `panic: makechan: size out of range`, `goroutine 1 [running]`, and either `main.(*program).checkFile` or `main.(*program).checkPackage`.

## Spec 11

The following core expression/assignment checkers operate on parsed Go expressions; spacing and nesting do not change structural identity, and text inside comments or strings is not code.

- `assignOp`: for `LHS = LHS OP RHS`, where `OP` is `+`, `-`, `*`, or `/`, report `replace \`LHS = LHS OP RHS\` with \`LHS OP= RHS\``. Use increment/decrement for integer-one forms: `x = x + 1` must report `replace \`x = x + 1\` with \`x++\`` on stderr (and subtraction by one analogously uses `--`). Other exact examples include `x = x + 10` → `replace \`x = x + 10\` with \`x += 10\``, `x = x - 5` → `x -= 5`, `x = x * 2` → `x *= 2`, `x = x / 3` → `x /= 3`, and `y = y + "suffix"` → `y += "suffix"`. It applies inside functions, methods, closures, goroutines, loops, `select`, `init`, and to package variables or selectors. Report every occurrence.
- `dupSubExpr`: structurally identical operands of a binary operator report `suspicious identical LHS and RHS for \`OP\` operator` at that expression. This includes `a == a`, `x < x`, `x > 0 || x > 0`, `flag && flag`, and `xs[i].v < xs[i].v`. For `x == x && x == x`, report the outer `&&` and both inner `==` nodes. An otherwise duplicated binary operand that contains a call is excluded: `len(items) > 0 && len(items) > 0` emits no `dupSubExpr` finding. Distinct expressions such as `xs[i] < xs[j]` and `x > 10 && y > 10` are also silent.
- `badCond`: contradictory same-variable bounds such as `x < 3 && x > 10` report `` `x < 3 && x > 10` condition is always false``. Unequal simultaneous equalities such as `x == 5 && x == 10` report `` `x == 5 && x == 10` condition is suspicious``. An upward loop initialized with `i := 0` and advanced using `i++` but guarded by `i > n` reports at the `for` keyword with `` `i > n` in loop; probably meant `i < n`?``. Suppress the loop warning if the relevant variable can be mutated or its address escapes in the body. `x > 5 && x < 10` is valid.
- `unslice`: a full slice of an existing slice, such as `x[:]`, reports at the slice expression `could simplify x[:] to x`; partial slices are not this issue.

For this canonical input, replace `PATH` with the selected display path and emit exactly the shown diagnostic:

```go
package main
func main() {
	x := []int{1, 2, 3}
	y := x[:]
	println(len(y))
}
```

```text
PATH:4:7: unslice: could simplify x[:] to x
```

## Spec 12

Implement these default control-flow and structural checks:

- `appendAssign`: if an assignment destination differs from the first argument of the `append` whose result it receives, report at the append call `append result not assigned to the same slice`. Examples are `d.positives = append(d.negatives, x)` and `xs = append(ys, "a")`. Normal `xs = append(xs, x)` is valid.
- `appendCombine`: two or more uninterrupted assignments appending to the same slice report once at the first assignment: `can combine chain of N appends into one`. Any unrelated intervening statement ends the chain and begins a new possible chain; thus one append, `println(x)`, then two appends reports `can combine chain of 2 appends into one` at the first append after `println(x)`.
- `dupBranchBody`: identical `if` and `else` bodies report at the `if`: `both branches in if statement have same body`.
- `dupCase`: repeated literal switch alternatives report on the duplicate with `'<case text>' is duplicated`, for example `'case 1' is duplicated`. Similar-looking `select` operations are not duplicate switch values.
- `elseif`: an `else` block whose substantive body is one `if` reports at the inner `if`: `can replace 'else {if cond {}}' with 'else if cond {}'`.
- `singleCaseSwitch`: a value or type switch with exactly one case and no `default` reports at `switch`: `should rewrite switch statement to if statement`. A switch with one non-default case plus a `default` is silent.
- `switchTrue`: `switch true` reports at `switch`: `replace 'switch true {}' with 'switch {}'`.
- `ifElseChain`: `minThreshold` (default 2) counts `else if` clauses, not the initial `if`. Once a chain reaches that count, report at its initial `if`: `rewrite if-else to switch statement`. For `if a {} else if b {} else if c {}`, thresholds 1 and 2 report, while thresholds 3 and 4 are silent.
- `defaultCaseOrder`: a `default` case strictly between other cases reports `consider to make \`default\` case as first or as last case`.
- `caseOrder`: in a type switch, an interface case must follow concrete types it subsumes. If `interface{}` precedes `string`, report at the interface case `case string must go before the interface{} case`. For consecutive unresolved cases `Missing1`, `Missing2`, and `Missing3`, report only the first, with `type is not defined Missing1`, and exit 1 without crashing.
- `typeSwitchVar`: two or more type-switch cases that repeatedly assert the switched expression report at `switch`: `2 cases can benefit from type switch with assignment`.

## Spec 13

Implement these default API/value-use diagnostics using import/type identity, not arbitrary method spelling:

- `badCall`: `strings.Replace` and `bytes.Replace` with count argument `0` report `suspicious arg 0, probably meant -1`. Counts `-1` and `1` are valid.
- `argOrder`: in the supported standard `strings`/`bytes` search functions, a literal needle before a variable haystack reports `ARG1 and ARG2 arguments order looks reversed`, preserving source formatting. Required pairs include `"prefix_" and searchText` for `strings.Contains` and `[]byte("_suffix") and searchData` for `bytes.Contains`. The analogous `strings.Index("some constant text", searchText)` call is silent. Correct variable-first calls are also silent.
- `dupArg`: duplicated operands in known operations report `suspicious duplicated args in CALL`. Required calls include `strings.Compare(s, s)`, `strings.Contains(s, s)`, `strings.HasPrefix(s, s)`, `math.Max(x, x)`, `math.Min(x, x)`, and `copy(dest, dest)`. Do not flag custom/nonstandard functions solely due to repeated arguments.
- `flagName`: flag names report: leading hyphen → `flag name "-verbose" should not start with a hyphen`; whitespace → `flag name "output file" contains whitespace`; empty → `empty flag name`; equals → `flag name "config=file" should not contain '='`.
- `flagDeref`: immediately dereferencing a pointer returned by a `flag` constructor, e.g. `*flag.Bool(...)`, reports `flagDeref`.
- `mapKey`: a literal key with leading or trailing whitespace reports `suspicious whitespace in "KEY" key`, retaining the whitespace inside the quoted key. Thus `"bar "` reports `suspicious whitespace in "bar " key`, and `" bad "` reports `suspicious whitespace in " bad " key`. A repeated nonconstant key expression reports `suspicious duplicate KEY key`; for duplicate `k` entries the message is `suspicious duplicate k key`. Both findings are emitted when a map literal contains both kinds of problem.
- `nilValReturn`: in a branch proving a value nil, returning that value reports at the `return` keyword with `returned expr is always nil; replace NAME with nil`. This covers errors and pointers. Explicit `return nil` is silent.
- `sloppyTypeAssert`: an assertion whose source and target interface types are identical reports `type assertion from/to types are identical`.
- `sloppyLen`: an invariant length comparison `len("hello") >= 0` reports exactly `len("hello") >= 0 is always true`.
- `offBy1`: indexing `slice[len(slice)]` reports `offBy1`.

## Spec 14

Implement these naming, comment, and syntactic-style checks:

- `captLocal`: by default, uppercase parameter and named-result identifiers report `` `Name' should not be capitalized``; `func f(InputFile, OutputFile int) (Result int)` therefore reports all three identifiers. Uppercase local declarations are added with `-@captLocal.paramsOnly=false`; in `func f(InputFile, OutputFile int) (Result int) { X := 1 }`, this mode reports `InputFile`, `OutputFile`, `Result`, and `X`. Package-level exported identifiers are not local.
- `commentFormatting`: `//missing space` reports at the comment `put a space between \`//\` and comment text`. Recognized `//line` compiler directives are exempt: `//line generated.go:1` and the absolute-path forms `//line /foo/bar.go:10`, `//line /foo/bar/f-ad/a_d.go:13`, and `//line /bar.go:14` emit no `commentFormatting` finding.
- `deprecatedComment`: `DEPRECATED: ` reports `use \`Deprecated: \` (note the casing) instead of \`DEPRECATED: \``. The misspellings `Dprecated`, `Derecated`, and `Depecated` each report `typo in \`MISSPELLING\`; should be \`Deprecated\``. This typo detection applies to documentation attached to imports, constants, variables, types, struct fields, and functions. The distinct near-miss `Depreciated: old` is silent. A correctly cased notice must be a dedicated paragraph: `// F does x.` immediately followed by `// Deprecated: use G.` reports `` `Deprecated: ` notices should be in a dedicated paragraph, separated from the rest``; inserting an intervening `//` line makes it silent.
- `codegenComment`: this checker concerns generated-file marker comments, not `go:generate` directives. A bare `//go:generate` after the package clause is silent. At the start of a file, `// generated file - do not edit` reports `comment should match \`Code generated .* DO NOT EDIT.\` regexp`; the canonical `// Code generated by tool. DO NOT EDIT.` is silent.
- `newDeref`: `*new(T)` reports `replace \`*new(T)\` with \`VALUE\``. Exact zero values: `int`→`0`, `float64`→`0.0`, `string`→`""`, `bool`→`false`; `int8/int16/int32/int64/uint/uint8/uint16/uint32/uint64`→`T(0)`; `float32`→`float32(0.0)`; named scalar types wrap their zero (`MyInt(0)`, `MyFloat(0.0)`, `MyString("")`, `MyBool(false)`); slices/maps/pointers/interfaces use typed nil (`[]int(nil)`, `map[string]int(nil)`, `(*int)(nil)`, `interface{}(nil)`); arrays/structs use `[5]int{}`/`MyStruct{}`. Thus `*new(Config)` suggests `Config{}`.
- `underef`: `(*p).x` reports `could simplify (*p).x to p.x`.
- `valSwap`: a three-statement swap is recognized when its first statement declares a local temporary. For example, `tmp := a; a = b; b = tmp` reports `can re-write as \`a, b = b, a\``, while `tmp := *a; *a = *b; *b = tmp` reports `can re-write as \`*a, *b = *b, *a\``. Using a third pointer as storage, `*tmp = *a; *a = *b; *b = *tmp`, is silent.

## Spec 15

Implement performance checks using Go type sizes:

- `hugeParam`: a by-value parameter whose size is greater than or equal to `sizeThreshold` (default 80 bytes) reports at its name `NAME is heavy (N bytes); consider passing it by pointer`. Equality triggers: an 80-byte parameter with threshold 80 and a 512-byte parameter with threshold 512 both report. Required sizes also include 104, 1024, and 16384 bytes. Pointer parameters are silent.
- `rangeExprCopy`: a range loop with both index and value variables over an array expression whose size is greater than or equal to its threshold (default 512) reports at the `for` keyword with `copy of NAME (N bytes) can be avoided with &NAME`. Equality triggers for a 256-byte array at threshold 256 and a 512-byte array at threshold 512; 800- and 2048-byte arrays also report with two variables at threshold 512. A loop with no iteration variables, such as `for range a {}`, is silent even for 256, 800, or 2048 bytes under those lowered thresholds. Ranging over `&array` is silent.
- `rangeValCopy`: binding a large range value (threshold default 128) reports at the `for` keyword with `each iteration copies N bytes (consider pointers or indexing)`. Index-only range is silent.
- `indexAlloc`: `strings.Index(string(data), needle)` where `data` is bytes reports `consider replacing strings.Index(string(data), needle) with bytes.Index(data, []byte(needle))`; the original `strings.Index` call in the message preserves its source spacing. Consequently, source spelled `strings.Index(string(data),needle)` reports `consider replacing strings.Index(string(data),needle) with bytes.Index(data, []byte(needle))`. Direct `bytes.Index` is silent.
- `equalFold`: `strings.ToLower(a) == strings.ToLower(b)` reports `equalFold` and suggests case-insensitive `EqualFold` behavior.
- `zeroByteRepeat`: `bytes.Repeat([]byte{0}, n)` reports `zeroByteRepeat`.

Thresholds are effective: raising one above the relevant size suppresses its warning.

## Spec 16

`badRegexp` examines constant patterns supplied to `regexp.Compile`/`MustCompile` and reports these exact messages:

| Pattern | Message |
|---|---|
| `foo^bar` | `dangling or redundant ^, maybe \^ is intended?` |
| `[aa]`, `[aba]` | `` `a` is duplicated in [aa]``, `` `a` is duplicated in [aba]`` |
| `(a+)+`, `(a*)+` | `repeated greedy quantifier in (a+)+`, `repeated greedy quantifier in (a*)+` |
| `[!-_]` | ``suspicious char range `!-_` in [!-_]`` |
| `[\d0-9]` | `` `\d` intersects with `0-9` in [\d0-9]`` |
| `[\s\t]` | `` `\s` intersects with `\t` in [\s\t]`` |
| `[\wa-z]` | `` `\w` intersects with `a-z` in [\wa-z]`` |
| `[\x30-\x390-9]` | `` `\x30-\x39` intersects with `0-9` in [\x30-\x390-9]`` |
| `(?-i:test)` | `clearing unset flag i in (?-i:test)` |
| `(?ii:test)` | `redundant flag i in (?ii:test)` |

The backslash-escaped-pipe patterns `foo\|bar\|foo`, `(?:^aa\|bb\|cc)`, and `(?:aa\|bb\|cc$)` are silent: each `\|` is a literal pipe rather than an alternation. Normal anchored alternations and deduplicated classes are also silent.

## Spec 17

`boolExprSimplify` is experimental and reports `can simplify \`OLD\` to \`NEW\``. Required rewrites are:

| OLD | NEW |
|---|---|
| `!(!x)` | `x` |
| `!!(x)` | `x` |
| `!!(!x)` | `!x` |
| `!x == !y` | `x == y` |
| `!(x < y)` | `x >= y` |
| `!(a < b)` | `a >= b` |
| `!(elapsed >= expectMin)` | `elapsed < expectMin` |
| `x > y \|\| x == y` | `x >= y` |
| `x < y \|\| x == y` | `x <= y` |
| `x+1 > y` | `x >= y` |
| `x-1 < y` | `x <= y` |
| `x+1 <= y` | `x < y` |
| `x < 5 \|\| x > 5` | `x != 5` |
| `!(a == b) && !(a != b) && !(a <= b) && !(a >= b)` | `a != b && a == b && a > b && a < b` |

Do not invert floating-point comparisons because NaN makes the rewrite unsafe, and do not rewrite merely similar nonmatching range conjunctions.

## Spec 18

`regexpSimplify` reports `can re-write \`OLD\` as \`NEW\`` for constant regexps. Apply up to two passes so chained rewrites reach these results:

- Repetition: `a{0,1}`→`a?`, `b{1,}`→`b+`, `c{0,}`→`c*`, `e{1}`→`e`.
- Common classes: `[0-9]`/`[[:digit:]]`→`\d`; `[[:word:]]`→`\w`; `[[:^word:]]`→`\W`; `[[:space:]]`→`\s`; `[[:^space:]]`→`\S`; `[[:^digit:]]`→`\D`; `[][]`→`\]\[`; `[]]`→`\]`.
- Negated classes: `[^0-9]`/`[^\d]`→`\D`; `[^\s]`→`\S`; `[^\S]`→`\s`; `[^\w]`→`\W`; `[^\W]`→`\w`; `[^\D]`→`\d`. POSIX equivalents map analogously: `[^[:^space:]]`→`\s`, `[^[:space:]]`→`\S`, `[^[:^word:]]`→`\w`, `[^[:word:]]`→`\W`, `[^[:^digit:]]`→`\d`, `[^[:digit:]]`→`\D`.
- Repeated atoms: `....`→`.{4}`, two spaces→` {2}`, `aaaaa`→`a{5}`, `\w\w\w`→`\w{3}`, `[0-9][0-9]`→`\d{2}`, `(?:ab)(?:ab)`→`(?:ab){2}`. Do not compress three dots. Thresholds are dots 4, spaces 2, literal characters 5, escapes 3, and classes/groups 2.
- Merge one-plus-star: `aa*`→`a+`, `\d\d*`→`\d+`, `\w\w*`→`\w+`, `[0-9][0-9]*`→`\d+`, `(?:ab)(?:ab)*`→`(?:ab)+`.
- Alternation/factoring: `(?:a|b|c)` and `a|b|c`→`[abc]`; `http|https`→`https?`; `foo|foos`→`foos?`; `xfoo|foo`→`x?foo`; `afoo|foo`→`a?foo`. Avoid factoring alternatives differing by more than one rune or arbitrary larger non-character alternatives.
- Degenerate ranges: `[a-a]`→`a`, `[0-0]`→`0`, `[a-b]`→`[ab]`, `[a-c]`→`[abc]`; leave `[a-d]` unchanged.
- Preserve groups while simplifying inside: `(?P<name>[0-9]+)`→`(?P<name>\d+)`, `([0-9]+)`→`(\d+)`, `(?:[0-9]+)`→`(?:\d+)`.
- Remove unnecessary escapes before `& # ! @ % < > : ; / , =`, e.g. `\&test`→`&test`; preserve meaningful `\.`.
- Other required examples: `[a-z][a-z]*`→`[a-z]+`, three spaces→` {3}`, and `[0-9] [0-9] [0-9]`→`\d \d \d`.

## Spec 19

Implement these selected experimental analyses:

- `evalOrder`: if one return expression reads a variable and a later expression may mutate it by address or pointer receiver, report at the mutating call `may want to evaluate CALL before the return statement`. Required calls include `modify(&x)`, `processValue(&x)`, and `c.Inc()`. Independent returns are silent; analyze all dependencies rather than stopping after one.
- `sqlQuery`: a bare expression-statement call `db.QueryContext(ctx, "delete from t")` on `*database/sql.DB` is silent. If the returned rows value is explicitly discarded while the error is retained, as in `_, err := db.QueryContext(nil, "DELETE FROM users")`, report at the call `use db.Exec() if returned result is not needed`.
- `truncateCmp`: narrowing a 32-bit value to 16 bits and comparing it with an uncast 16-bit variable reports `truncation in comparison 32->16 bit; cast the other operand to TYPE32 instead`, regardless of which side has the cast. Use `int32` or `uint32` as appropriate.
- `sortSlice`: in `sort.Slice`/`sort.SliceStable`, sorting `xs` while comparing `keys[i] < keys[j]` reports `cmp func must use xs slice in comparison`; comparing `xs[j] < xs[i]` reports `unusual order of {i,j} params in comparison`. Unwrap `xs[:]` to `xs`.
- `commentedOutCode`: executable comments such as `// fmt.Println("debug", x)`, `// log.Fatal(x)`, or a multiline commented `if` block report `may want to remove commented-out code`.

## Spec 20

Implement these additional transformations:

- `hexLiteral`: `0X1234` reports `prefer 0x over 0X, s/0X1234/0x1234/`; mixed-case hex digits such as `0xAbCd` also report `hexLiteral` and suggest consistent casing.
- `octalLiteral`: with target Go 1.13+, old `0755`/`077` forms report `use new octal literal style, 0o755`/`0o77`; `0o755` is silent. `-go=1.12` suppresses this checker, while 1.13 and 2.0 enable it. Compare version major, then minor.
- `tooManyResultsChecker`: more than `maxResults` result slots reports `function has more than N results, consider to simplify the function`, where N is the active limit (default 5; custom 2 is required).
- `dupImport`: importing one path twice under aliases reports on both specs: `package is imported 2 times under different aliases on lines L1 and L2`.
- `dupOption`: in a variadic option-function API, structurally identical option calls after required parameters report on every occurrence after the first: `function argument \`CALL\` is duplicated`. Support functions, methods, indirect function values, multi-parameter option signatures, arithmetic and nested calls. Required formatted calls include `withOpt(1)`, `withOpt(10)`, `withValue(x)`, `withValue(5 + 3)`, `withValue(len("abc"))`, `withSize(10)`, `inner(1)`, `outer("a")`, and `withOption(1, "a")`. No variadic arguments must not crash; `...interface{}` is not an option-function signature.
- `unlambda`: `func(a, b int) int { return add(a, b) }` reports replacement by `add`, retaining the multiline wrapper in the message. Its message formats that wrapper independently of its source indentation, with one tab before `return` and the closing brace unindented:

  ```text
  replace `func(a, b int) int {
  	return add(a, b)
  }` with `add`
  ```

  Do not simplify wrappers around builtins, complex callable expressions, or unsafe ellipsis forwarding.
- `whyNoLint`: a bare line-comment `//nolint` directive reports `include an explanation for nolint directive`; the suffix form `//nolint -- required for compatibility` still reports the same warning. A second line-comment introducer supplies an accepted explanation, so `//nolint // has explanation` is silent. Text in block comments is not a directive for this checker.

## Spec 21

Opinionated checkers are disabled by default and obey ordinary selection:

- `builtinShadow`: `len := 10` reports `shadowing of predeclared identifier: len`.
- `importShadow`: a local such as `fmt := 5` after importing `fmt` reports `importShadow`.
- `paramTypeCombine`: `func f(a int, b int, c int)` reports `paramTypeCombine` and suggests combining types.
- `ptrToRefParam`: pointer parameters to maps, channels, and interfaces (including named interfaces), in functions or methods, report ``consider `NAME' to be of non-pointer type``. Struct pointers are valid. An unnamed pointer-to-map result reports `consider to make non-pointer type for \`*map[string]int\``.
- `unnamedResult`: a function with at least two unnamed results generally reports once at the function declaration's `func` keyword with `consider giving a name to these results`. Exactly `(T, error)` is exempt; `(T, T, error)` reports. By default exported and unexported functions are checked. With `-@unnamedResult.checkExported=true`, only exported functions report. Repeated pointer, slice, and array types count normally; one function yields one finding.
- `typeUnparen`: recursively remove redundant type parentheses. Required OLD→NEW forms: `[](func([](func())))`→`[]func([]func())`, `map[string](*int)`→`map[string]*int`, `map[string](int)`→`map[string]int`, `chan (*string)`→`chan *string`, `chan (int)`→`chan int`, `(struct{...})`→`struct{...}`, `(interface{...})`→`interface{...}`. Message: `could simplify OLD to NEW`.
- `typeDefFirst`: a method before its receiver definition reports `definition of type 'Receiver' should appear before its methods`. Handle pointer and generic receivers such as `*Receiver[T]`; a prior type definition is silent.
- `unnecessaryBlock`: a standalone block with no declarations reports `block doesn't have definitions, can be simply deleted`; a standalone block containing declarations is silent. An extra block directly inside a switch case reports `case statement doesn't require a block statement` even when the block contains a declaration such as `z := 2`. Nested blocks are analyzed independently.
- `unlabelStmt`: a same-loop label used only by break/continue reports `label NAME is redundant`. At the tested nested-loop end position, `continue loop` that can become leaving the inner loop reports `change \`continue loop\` to \`break\``. A label genuinely needed to break an outer loop is not redundant.

## Spec 22

The following explicitly selectable checkers need the stated detections. Use the standard diagnostic format and a substantive message naming the checker or construct.

- `builtinShadowDecl`: package declarations such as `var len int = 5` shadowing predeclared identifiers.
- `deferInLoop`: a `defer f.Close()` lexically inside a loop.
- `deferUnlambda`: `defer func(){ cleanup() }()` when direct defer is equivalent.
- `emptyDecl`: an empty group such as `var ()`.
- `exposedSyncMutex`: a struct exposing an embedded `sync.Mutex`.
- `methodExprCall`: `(T).Method(t)` when ordinary method-call syntax is clearer.
- `emptyStringTest`: preserve the source spelling of the comparison in the message. For the source `len(s)==0`, the exact message is `replace \`len(s)==0\` with \`s == ""\``.
- `docStub`: stub documentation used only to silence doc lint reports `silencing go lint doc-comment warnings is unadvised` at the documented declaration, not at the comment: at the `func` keyword for a function and at the type identifier for a type spec.

`exitAfterDefer` reports terminating calls after an active defer: `log.Fatal` after `defer f.Close()` → `log.Fatal will exit, and \`defer f.Close()\` will not run`; `os.Exit` after `defer os.Remove(path)` → `os.Exit will exit, and \`defer os.Remove(path)\` will not run`. A fatal/exit call earlier in that function, before the first relevant defer, is not among the findings.

## Spec 23

Checker execution is real and compositional:

- Enabling one checker excludes all others; enabling several runs all; disabling one leaves unrelated selected/default checkers active.
- Clean idiomatic code emits nothing. Correct imports, concrete-before-interface type cases, valid flag names, distinct operands, ordinary struct pointers, and valid regexp forms are silent.
- Emit all findings in a function/file and across many files. Fifty empty functions, many clean files, and nested package paths create no findings themselves.
- Accept `-@ruleguard.rules=PATH` with `-enable=ruleguard`. For a valid harness-provided rules file and `package main\nfunc main() {}\n`, exit 0 with empty streams. The rules file itself is harness-provided; the executable loads/applies it without crashing.
- Local type-resolution trouble must not crash checking; `caseOrder` follows Spec 12.

## Spec 24

`-v` adds debug lines to stderr before diagnostics without changing detection or exit status. For every registry checker not selected, print a tab then `debug: NAME: not enabled by name or tag (-enable)`; for every selected checker, print a tab then `debug: NAME is enabled`. Print all unselected lines first and all selected lines second, preserving registry order within each group. Then print the package line with `package` after the quoted package identity. For a one-file ordinary command-line package it is exactly:

```text
	debug: checking "command-line-arguments" package (1 files)
```

For the default set this includes `debug: appendCombine: not enabled by name or tag (-enable)` and `debug: unslice is enabled`. Any ordinary diagnostic follows. Verbose checking of clean code exits 0 while retaining debug output.
