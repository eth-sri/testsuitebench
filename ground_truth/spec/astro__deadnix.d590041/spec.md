# Executable specification

The required artifact is a file named exactly `executable`. It is a command-line
program that finds dead declarations in Nix source files. All text is UTF-8.
Unless a section says otherwise, diagnostics about successfully parsed source go
to standard output, operational and parse errors in human-readable mode go to
standard error, and successful invocations write nothing for files with no
findings.

## Spec 1

`executable` is a single-command program; it has no subcommands. Its command-line
shape is:

```text
executable [OPTIONS] [FILE_PATHS]...
```

Names such as `check`, `scan`, `lint`, `analyze`, `run`, `list`, and `help` are
ordinary file-path operands, not commands. Options may occur before or after
path operands. `--` ends option parsing, so a later token beginning with `-` is
treated as a path. With no path operands the program behaves exactly as if `.`
were supplied and recursively scans the current working directory.

The supported options are:

- `-l`, `--no-lambda-arg`
- `-L`, `--no-lambda-pattern-names`
- `-_`, `--no-underscore`
- `-W`, `--warn-used-underscore`
- `-q`, `--quiet`
- `-e`, `--edit`
- `-h`, `--hidden` (`-h` is not help)
- `--help`
- `-f`, `--fail`
- `-o FORMAT`, `--output-format FORMAT`, and `--output-format=FORMAT`
- `--exclude EXCLUDES...`
- `-V`, `--version`

Boolean short options can be combined, for example `-qh` and `-lL`.

## Spec 2

`--help` exits 0, writes nothing to standard error, ends its output with one
newline, and writes exactly the following to standard output. On the `--help`
option row there are 27 ASCII spaces after `--help` and before its newline.

```text
Find dead code in .nix files

Usage: executable [OPTIONS] [FILE_PATHS]...

Arguments:
  [FILE_PATHS]...  .nix files, or directories with .nix files inside [default: .]

Options:
  -l, --no-lambda-arg                  Don't check lambda parameter arguments
  -L, --no-lambda-pattern-names        Don't check lambda attrset pattern names (don't break nixpkgs callPackage)
  -_, --no-underscore                  Don't check any bindings that start with a _
                                       (Lambda arguments starting with _ are not checked anyway.)
  -W, --warn-used-underscore           Warn if bindings are referenced that start with '_'
  -q, --quiet                          Don't print dead code report
  -e, --edit                           Remove unused code and write to source file
  -h, --hidden                         Recurse into hidden subdirectories and process hidden .*.nix files
      --help                           
  -f, --fail                           Exit with 1 if unused code has been found
  -o, --output-format <OUTPUT_FORMAT>  Output format to use [default: human-readable] [possible values: human-readable, json]
      --exclude <EXCLUDES>...          Files to exclude from analysis
  -V, --version                        Print version
```

Other options may accompany `--help`; help still succeeds and is displayed.
`-V` and `--version` both exit 0, write nothing to standard error, and write
exactly `deadnix 1.3.1\n` to standard output.

## Spec 3

Command-line validation is clap-style. An invalid command line exits 2 and
describes the problem on standard error. Only `human-readable` and `json` are
valid output formats; `human-readable` is the default. A missing format reports
`a value is required for '--output-format <OUTPUT_FORMAT>'` and includes
`[possible values: human-readable, json]`. An invalid value such as `xml`
reports `invalid value 'xml' for '--output-format <OUTPUT_FORMAT>'` and the same
possible-values text.

An unknown long option reports `unexpected argument '--name'`; it also gives
the tip `tip: to pass '--name' as a value, use '-- --name'`. Unknown short
options similarly report `unexpected argument`. `--output-format` cannot be
specified more than once. `--exclude` cannot be specified more than once. A
repetition exits 2 and says that the option `cannot be used multiple times`.
`--exclude` requires one or more values; without one it exits 2 and reports
`a value is required for '--exclude <EXCLUDES>...'`.

One occurrence of `--exclude` greedily accepts multiple paths. When ordinary
input paths must follow it, `--` separates the exclusion list from those input
paths, as in `--exclude a.nix b.nix -- project`.

## Spec 4

Each explicit path operand is first statted, so a nonexistent token is reported
as a missing path even when it has no `.nix` suffix. An existing explicit file
whose extension is `.nix`, case-insensitively (thus also `.NIX` and `.Nix`), is
analyzed; an existing explicit non-Nix file is silently ignored. A directory
operand is walked recursively to arbitrary
practical depth and only files with that case-insensitive extension are
analyzed. Files and directories can be mixed, and every operand is processed.
Explicit operands retain their supplied path spelling in reports; discovered
files are reported using the path produced beneath the supplied directory.

Processing is deterministic. Explicit operands retain operand order; findings
within a file are in increasing source position. Directory traversal must be
stable (lexical path ordering is suitable). In JSON mode an emitted file is one
complete JSON object on one line. Empty directories, directories with no Nix
files, ignored non-Nix files, and valid files without findings produce no
output and are not represented by empty JSON objects.

## Spec 5

When a directory operand is walked, files or directory components whose
basename begins with `.` are not traversed or analyzed by default.
`-h`/`--hidden` includes hidden `.nix` files and recurses through hidden
directories at every depth, without excluding visible files. This hidden-path
filter does not apply to an explicit file operand: an explicitly supplied
`.name.nix` file is analyzed both with and without `--hidden`.

Symbolic links to files are followed and the link path is used as the reported
file path. Broken links are handled as missing files rather than crashing.
Directory walking must be safe against symlink cycles.

Every `--exclude` value denotes either a file or a directory subtree. For files
selected while walking a directory, compare canonicalized paths: a file is
excluded when its canonical path equals an excluded file or has an excluded
directory as a path prefix. Consequently, excluding a real directory also
excludes the same files reached through a symlink. Exclusion takes precedence
during recursive discovery, including discovery enabled by `--hidden`.

Exclusion does not override an explicit file operand. If the same file is both
named by `--exclude` and supplied after `--` as an input path, the file is
analyzed normally; with `--edit`, it is edited normally as well. Excluding all
files found through directory traversal succeeds silently.

## Spec 6

The analyzer parses Nix expressions rather than searching text with regular
expressions. It must handle comments, Unicode, very long identifiers and lines,
deeply nested expressions, and multiple declarations on one line. The syntax
needed by analysis includes:

- recursive `let DECLARATIONS in EXPR` bindings;
- simple lambdas (`name: EXPR`) and nested/curried lambdas;
- attribute-pattern lambdas (`{ a, b ? DEFAULT, ... }: EXPR`) and aliases in
  both `args@{ ... }` and `{ ... }@args` forms, with optional whitespace;
- `inherit a b;` and `inherit (SOURCE) a b;` declarations;
- ordinary and `rec` attribute sets, nested attribute-path declarations,
  dynamically interpolated attribute names, and attribute selection;
- strings (including multiline strings and `${...}` interpolation), lists,
  function application, `if/then/else`, `with`, `assert`, paths, URI literals,
  arithmetic/comparison/update operators, and attribute-existence expressions.

Comments and string contents are not identifiers, except that expressions
inside `${...}` are analyzed normally. A selector component after a dot is an
attribute name, not a variable reference: in `bar.foo`, `bar` is referenced but
a separate lexical variable named `foo` is not.

## Spec 7

The reportable declaration categories and their exact messages are:

- an unused `let` assignment or an unused name introduced by `inherit`:
  `Unused let binding: NAME`;
- an unused simple lambda parameter: `Unused lambda argument: NAME`;
- an unused attribute-pattern member or unused `@` alias:
  `Unused lambda pattern: NAME`;
- when underscore-use warnings are enabled, a referenced underscore-prefixed
  declaration uses the corresponding `Used ...: NAME` wording; for example a
  let binding produces `Used let binding: _x`.

Each declaration name is a separate finding. For example,
`inherit (s) a b c;` can yield three findings. Findings are ordered by the
starting position of the declared name, including when several occur on one
line. The location is the declared identifier itself, not the whole assignment,
default expression, `inherit` statement, or `@` construct.

Locations are one-based. `line` is the source line, `column` is the identifier's
starting column, and `endColumn` is the exclusive ending column. Thus the name
`unused` beginning after two spaces has `column: 3` and `endColumn: 9`.

## Spec 8

Name resolution is lexical and respects shadowing. A reference keeps alive the
nearest visible declaration with that name. An inner lambda, inner `let`, or
recursive attribute-set attribute can therefore shadow an outer declaration;
using the inner declaration does not keep the outer one alive. Attribute keys
in a non-recursive set also are not references to same-named outer variables.

References count in all expression positions, including a lambda body, a live
binding's value, either conditional branch, list items, function and argument
positions, `with` source expressions, assertions, selectors, interpolated
strings, and interpolated attribute keys. For example, in:

```nix
let name = "world"; dead = 1; in "Hello ${name}"
```

only `dead` is unused. In `with obj; a`, `obj` is referenced. In
`obj.nested.value`, only `obj` is the lexical reference.

## Spec 9

Liveness is reachability from the result expression of each scope, not a raw
count of textual references. A live binding keeps alive the declarations it
references. A declaration referenced only by another dead declaration remains
dead. Compute this to a fixed point and report every unreachable declaration in
source order. Therefore:

```nix
let dead1 = dead2; dead2 = dead3; dead3 = 42; in false
```

reports `dead1`, `dead2`, and `dead3`, in that order. A self-reference such as
`let dead = dead; in false` does not make itself live. Conversely, forward or
recursive references reachable from the body are live; in
`let a = b + 1; b = c + 1; c = 1; in a`, all three are live.

The same rule crosses nested scopes. A use of an outer binding inside a live
nested expression keeps it alive. Bindings in different scopes with identical
names remain distinct findings with their own locations.

## Spec 10

Simple lambda parameters, pattern members, and `@` aliases are tracked
independently. For example:

- `unused: 42` reports `Unused lambda argument: unused`;
- `outer: inner: inner` reports only the outer `outer`;
- `{ used, unused, ... }: used` reports only pattern member `unused`;
- `{ x ? 10, y, ... }: y` reports pattern member `x` despite its default;
- `args@{ used, unused, ... }: used + args.other` reports only `unused`;
- `dead@{ used, ... }: used` reports only alias `dead`;
- `{ dead }@args: args` reports pattern member `dead`;
- `{ bar, foo }: bar.foo` reports pattern member `foo`, because the selector
  name does not reference it.

A reference in a pattern default counts normally; for example, the alias is
live in `alive@{ x ? alive, ... }: x`. Shadowing between nested lambdas is
resolved lexically just like `let` shadowing.

## Spec 11

Each name in a `let`-level `inherit` is a let binding and is analyzed
separately. With `inherit (source) a b`, use of `a` keeps `a` and dependencies
of `source` alive; an unused inherited name does not, by itself, make the source
expression's dependencies live. This permits dead dependency chains through
successive inherits. In:

```nix
let
  alive = { key1 = 1; key2 = 2; };
  inherit (alive) key1 key2;
in key1
```

only `key2` is reported. In `let inherit (grave) a b c; in false`, all of
`a`, `b`, and `c` are reported in source order. For `inherit x;` without a
source expression, importing `x` is also a reference to the corresponding
outer/existing binding.

Ordinary attributes are not generally reported as unused declarations merely
because no selection reads them. Attribute sets still establish the scoping
needed for reference and shadowing analysis, especially `rec` sets. Each
`let`-level attribute-path assignment introduces a reportable occurrence of
its base name.
Thus `let foo.alive = 1; foo.dead = 2; in false` produces two findings named
`Unused let binding: foo`, at columns 5 and 20 respectively and in that order.
A use of the base keeps every repeated occurrence live: changing the body to
`in foo` produces no findings. Individual path components such as `alive` and
`dead` are not reported.

## Spec 12

The exact line comment `# deadnix: skip` suppresses findings whose declaration
names begin on the immediately following physical source line. It does not
disable a scope or all subsequent declarations. All candidate names on that
one following line are suppressed, so a one-line pattern, several same-line
curried lambda arguments, or a multi-name `inherit` can all be skipped together.
If a construct continues on later lines, names on those later lines are still
checked.

An intervening comment line consumes the adjacency: in this source both
bindings are reported because the pragma's immediately following line is
another comment:

```nix
let
  # deadnix: skip
  # explanation
  first = 1;
  second = 2;
in false
```

Multiple pragmas apply independently. The pragma affects analysis and editing:
suppressed declarations are not edited.

## Spec 13

Filtering options alter only the stated candidate classes:

- `-l`/`--no-lambda-arg` suppresses unused simple lambda-parameter findings at
  every nesting depth; it does not suppress let bindings or pattern findings.
- `-L`/`--no-lambda-pattern-names` suppresses attribute names destructured by
  lambda patterns. It does not suppress an unused `@` alias.
- `-_`/`--no-underscore` suppresses checking of every declaration whose name
  begins with `_`, including unused and used-underscore findings.
- Independently of flags, an underscore-prefixed simple lambda parameter is
  never checked: an unused `_arg` is not reported, and a referenced `_arg` does
  not produce a used-underscore finding even with `-W`. This convention does
  not apply to attribute-pattern members or `@` aliases: an unused `_member`
  or `_alias` is reported as `Unused lambda pattern: NAME`. Ordinary
  underscore-prefixed `let` bindings are also reported as unused by default.
- `-W`/`--warn-used-underscore` adds a finding when an eligible
  underscore-prefixed binding is actually referenced. In particular,
  referenced pattern members and aliases use `Used lambda pattern: NAME`, and
  referenced `let` bindings use `Used let binding: NAME`. Without `-W`, such
  use is not a finding. If `-_` and `-W` are combined, `-_` wins and no
  underscore finding is made.

The filters compose. For instance `-lL` suppresses both simple lambda arguments
and pattern members while leaving unused `let` bindings and unused `@` aliases
eligible.

## Spec 14

Human-readable output is the default. For every file with findings it begins a
report with the exact sentence:

```text
Warning: Unused declarations were found.
```

It then renders a source-code diagnostic containing the file path and first
location in a header of the form `PATH:LINE:COLUMN`, the relevant original
source line with its line number and a `│` separator, and a `╰`/horizontal marker
ending in the exact finding message. Multiple findings, including multiple
findings on one line, are all rendered. Unicode in source lines and file names
must be preserved. A representative uncolored report is:

```text
Warning: Unused declarations were found.
   ╭─[/tmp/test_simple.nix:2:3]
 2 │  unused = 42;
   │     ╰─── Unused let binding: unused
```

By default, a report with findings contains ANSI color escape sequences even
when standard output is captured rather than attached to a terminal. If the
`NO_COLOR` environment variable is present, regardless of whether its value is
`1`, empty, or anything else, neither standard output nor standard error may
contain an ANSI escape sequence. `NO_COLOR` does not suppress the text itself.

## Spec 15

JSON output is selected by `-o json` or `--output-format json`. It contains no
human-readable warning or ANSI escapes. Each file that has findings or an error
emits one compact JSON object followed by a newline:

```json
{"file":"PATH","results":[{"column":3,"endColumn":9,"line":2,"message":"Unused let binding: unused"}]}
```

The top-level object has exactly `file` (a string) and `results` (an array).
Ordinary analysis results have exactly the integer `column`, integer
`endColumn`, integer `line`, and string `message` data represented above.
Results occur in source order. With multiple emitted files, output is JSON
Lines: one independent object per line, never a surrounding array and never
concatenated objects on one line. A clean valid file emits no JSON at all.

Parse and file-system errors are placed in the same per-file envelope as result
objects containing at least a `message` string; they need not have source
location fields. JSON-mode errors go to standard output, not standard error.

## Spec 16

Finding dead declarations does not fail an invocation by default: the exit code
is 0 even when reports are emitted. Parse errors, nonexistent paths, and broken
symlinks are also per-input diagnostic conditions and leave the overall exit
code at 0 so other inputs can be processed. Help and version exit 0. Command-line
validation errors exit 2.

With `-f`/`--fail`, the exit code is 1 if at least one analysis finding was made
before any edit, and otherwise 0. Reporting still occurs in the chosen format.
With `-q`/`--quiet`, dead-code scan reports are suppressed, including JSON
analysis output, but parsing, analysis, editing, and `--fail` exit-status
calculation still happen. Thus a quiet failing scan exits 1 with both streams
empty. Quiet does not suppress human-readable parse or file-system diagnostics:
they remain on standard error, and diagnostic-only invocations still exit 0.
In JSON mode, parse and file-system error envelopes likewise remain on standard
output under `--quiet`. Quiet also does not suppress explicitly requested
help/version output or command-line validation errors.

## Spec 17

In human-readable mode, a nonexistent or unstatable path emits on standard
error:

```text
Error stating file PATH: No such file or directory (os error 2)
```

and exits 0. In JSON mode it instead emits exactly one error result whose
message is `No such file or directory (os error 2)` and whose top-level `file`
is the supplied path.

Malformed Nix is not analyzed as if it were valid. Human mode emits every
parser error, not only the first, on standard error; each diagnostic includes
`Error parsing file PATH:` followed by the parser message. The program does not
crash, does not stop processing later files, and exits 0. Empty, whitespace-only,
and comment-only `.nix` files are malformed missing expressions and report
`unexpected end of file`.

Required parser-message behavior includes:

- `let` yields at least two `Error parsing file` diagnostics including
  `unexpected end of file`;
- `let x = ; in alive` includes `unexpected TOKEN_SEMICOLON`;
- `let x = @@@; in x` includes `unexpected TOKEN_AT at 8..9`;
- `let x = {\n  foo = 42;\nin x` includes
  `unexpected TOKEN_IN at 22..24`, includes `unexpected end of file`, and
  yields at least five error diagnostics;
- `let x = syntax error` yields exactly three JSON messages, in order:
  `unexpected end of file, wanted any of [TOKEN_SEMICOLON]`, then
  `unexpected end of file`, then `unexpected end of file`;
- `let x = \n  y = \n  z = ` begins its JSON error list with
  `unexpected TOKEN_ASSIGN at 13..21, wanted any of [TOKEN_SEMICOLON]` and has
  multiple subsequent end-of-file errors.

In JSON mode an empty file has exactly one result containing an
`unexpected end of file` message. A malformed file containing several distinct
bad tokens must retain multiple parser errors in its result array.

## Spec 18

`-e`/`--edit` applies the analysis findings in place to every selected file,
including files found recursively. Edits operate on the original source spans,
preserve every unaffected byte and the general whitespace/newline structure,
and leave syntactically valid Nix. Apply nested or multiple edits without span
shifts corrupting later edits. A file with parse errors is never modified.

Editing an unused let assignment removes the complete assignment through its
semicolon and the whitespace that belongs solely to it. Editing individual
dead names out of an `inherit` retains its source expression and live names; if
no names remain, remove the whole `inherit` statement. If all declarations in a
`let ... in BODY` are thereby removed, replace the entire let expression with
`BODY` and preserve surrounding context.

These exact one-line transformations define whitespace behavior:

```text
let dead = 42; alive = 23; in alive  ->  let alive = 23; in alive
let dead1 = 1; dead2 = 2; alive = 4; in alive  ->  let alive = 4; in alive
let dead = 42; in alive  ->  alive
let inherit dead1 dead2 alive; in alive  ->  let inherit alive; in alive
let inherit (x) alive dead; in alive  ->  let inherit (x) alive; in alive
let inherit (x) dead; alive = true; in alive  ->  let alive = true; in alive
let outer = let inner = 1; in 2; in outer  ->  let outer = 2; in outer
let outer = let inner = 1; in 2; in 3  ->  3
```

If `--fail` is also present, the edits are still written and the invocation
exits 1 based on the pre-edit findings. `--quiet` suppresses output but does not
suppress edits.

## Spec 19

Editing an unused simple lambda parameter prefixes that declaration with one
underscore rather than deleting the lambda layer: `dead: false` becomes
`_dead: false`. For nested `a: b: c: { dead, alive, ... }: alive`, the result is
`_a: _b: _c: { alive, ... }: alive`.

Editing a dead pattern member removes the complete member, including any
`? DEFAULT`, and repairs commas without reformatting the rest. Editing a dead
`@` alias removes the alias, its `@`, and associated spacing in either alias
orientation. These transformations are exact:

```text
alive@{ dead, ... }: alive        -> alive@{ ... }: alive
alive@{ dead ? true, ... }: alive -> alive@{ ... }: alive
dead@{ ... }: false               -> { ... }: false
{ ... }@dead: false               -> { ... }: false
dead @ { ... }: false             -> { ... }: false
dead@{ dead2 ? dead, ... }: false -> { ... }: false
dead1@{ dead2, alive, ... }: alive -> { alive, ... }: alive
{ bar, foo, }: bar                -> { bar, }: bar
{ bar, foo }: bar                 -> { bar }: bar
```

For a multiline pattern, `{ alive\n, dead\n, ... }:\nalive` becomes
`{ alive\n, ... }:\nalive`. Shadowing is honored while editing: for
`dead@{ ... }: dead@{ ... }: dead`, remove only the outer alias, producing
`{ ... }: dead@{ ... }: dead`.

## Spec 20

The following conformance examples summarize ordering and exact result spans.
The displayed `file` value is illustrative and must actually be the path used
to invoke the program.

For:

```nix
let
  dead1 = 23;
  dead2 = 42;
  dead3 = 99;
  alive = 100;
in alive
```

the `results` array is exactly:

```json
[{"column":3,"endColumn":8,"line":2,"message":"Unused let binding: dead1"},{"column":3,"endColumn":8,"line":3,"message":"Unused let binding: dead2"},{"column":3,"endColumn":8,"line":4,"message":"Unused let binding: dead3"}]
```

For `args@{ used, unused, ... }: used + args.other`, the sole result is:

```json
{"column":14,"endColumn":20,"line":1,"message":"Unused lambda pattern: unused"}
```

For `let inherit (source) dead1 dead2 dead3; in false`, the three name spans
begin at columns 22, 28, and 34 respectively and end exclusively at columns 27,
33, and 39. For the canonical source `unusedArgs@{ unusedArg, usedArg, ... }:`
followed by a body containing unused `unused_inherit`, `unused`, `shadowed`,
`_unused = unused: false`, and a nested unused pattern member `unusedArg2`, the
messages are emitted in this exact order:

```text
Unused lambda pattern: unusedArgs
Unused lambda pattern: unusedArg
Unused let binding: unused_inherit
Unused let binding: unused
Unused let binding: shadowed
Unused let binding: _unused
Unused lambda argument: unused
Unused lambda pattern: unusedArg2
```

The first result in that example is on line 1 with `column` 1 and `endColumn`
11.
