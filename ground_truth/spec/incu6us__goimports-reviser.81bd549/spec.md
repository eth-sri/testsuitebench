# Clarified specification for `executable`

The required artifact is one executable file named exactly `executable`. It is a command-line Go-source import organizer with a flag-based interface. Paths and source text are UTF-8 unless an operating-system error prevents reading them. All behavior below is part of the executable itself; no other repository program is required.

## Spec 1

`executable` uses a flat, flag-based command line, not subcommands. Every non-flag argument is an input path. Words such as `add`, `remove`, `list`, `show`, `init`, and `help` are ordinary paths and consequently fail as missing paths when no such file exists. Multiple paths are accepted and processed in their command-line order. A path may be absolute or relative and may contain spaces.

Parsing follows Go's standard `flag` style. Both one- and two-hyphen spellings are accepted for flags such as `-help`/`--help`. String flags accept both `-name value` and `-name=value`. Boolean flags may be bare (meaning true); an invalid assigned value such as `-format=maybe` is a parse error. Flag parsing stops at the first positional argument, so later tokens beginning with `-` are paths, not flags. A standalone `--` terminates flag parsing and is not itself included in the path list.

An unknown flag exits 2 and writes a Go-style `flag provided but not defined` diagnostic followed by usage to stderr. A string flag missing its argument exits 2 with `flag needs an argument`; an invalid explicit Boolean exits 2 with `invalid boolean value`. With no input paths (including an invocation containing only `-recursive`), print usage plus `no file(s) or directory(ies) specified on input` to stderr and exit 1. Help and `-version` are terminal and do not require paths.

## Spec 2

The accepted flags and defaults are:

- `-apply-to-generated-files` (Boolean, default false)
- `-company-prefixes string` (default empty)
- `-excludes string` (default empty)
- `-file-path string` (deprecated, default empty)
- `-format` (Boolean, default false)
- `-imports-order string` (default `std,general,company,project`)
- `-list-diff` (Boolean, default false)
- `-local string` (deprecated, default empty)
- `-output string` (default `file`; valid values are `file`, `write`, and `stdout`)
- `-project-name string` (default empty)
- `-recursive` (Boolean, default false)
- `-rm-unused` (Boolean, default false)
- `-separate-named` (Boolean, default false)
- `-set-alias` (Boolean, default false)
- `-set-exit-status` (Boolean, default false)
- `-use-cache` (Boolean, default false)
- `-version` (Boolean, default false)
- `-version-only` (Boolean, default false)

`-file-path P` remains operational: append `P` after all positional paths, process all of them, and make the final status 1 even if processing succeeds. After processing, write these two timestamp-prefixed warning lines to stderr exactly:

```text
-file-path is deprecated. Put file name(s) as last argument to the command(Example: goimports-reviser -rm-unused -set-alias -format goimports-reviser/main.go)
All changes to file are applied, but command-line syntax should be fixed
```

`-local P` remains operational as the old name for `-company-prefixes`; warn that `-local is deprecated` and that `-company-prefixes` should be used, use the `-local` value if both flags are supplied, and make the final status 1 after otherwise successful processing.

## Spec 3

`-h`, `-help`, and `--help` exit 0, write nothing to stdout, and write the following help text to stderr, ending in a newline. Replace `<argv0>` with the exact string used to invoke the executable. The descriptions, indentation, capitalization, punctuation, blank lines, and defaults are exact.

```text
Usage of <argv0>:
  -apply-to-generated-files
    	Apply imports sorting and formatting(if the option is set) to generated files. Generated file is a file with first comment which starts with comment '// Code generated'. Optional parameter.
  -company-prefixes string
    	Company package prefixes which will be placed after 3rd-party group by default(if defined). Values should be comma-separated. Optional parameters.
  -excludes string
    	Exclude files or dirs, example: '.git/,proto/*.go'.
  -file-path string
    	Deprecated. Put file name as an argument(last item) of command line.
  -format
    	Option will perform additional formatting. Optional parameter.
  -imports-order string
    	Your imports groups can be sorted in your way. 
    	std - std import group; 
    	general - libs for general purpose; 
    	company - inter-org or your company libs(if you set '-company-prefixes'-option, then 4th group will be split separately. In other case, it will be the part of general purpose libs); 
    	project - your local project dependencies;
    	blanked - imports with "_" alias;
    	dotted - imports with "." alias.
    	Optional parameter. (default "std,general,company,project")
  -list-diff
    	Option will list files whose formatting differs from goimports-reviser. Optional parameter.
  -local string
    	Deprecated
  -output string
    	Can be "file", "write" or "stdout". Whether to write the formatted content back to the file or to stdout. When "write" together with "-list-diff" will list the file name and write back to the file. Optional parameter. (default "file")
  -project-name string
    	Your project name(ex.: github.com/incu6us/goimports-reviser). Optional parameter.
  -recursive
    	Apply rules recursively if target is a directory. In case of ./... execution will be recursively applied by default. Optional parameter.
  -rm-unused
    	Remove unused imports. Optional parameter.
  -separate-named
    	Option will separate named imports from the rest of the imports, per group. Optional parameter.
  -set-alias
    	Set alias for versioned package names, like 'github.com/go-pg/pg/v9'. In this case import will be set as 'pg "github.com/go-pg/pg/v9"'. Optional parameter.
  -set-exit-status
    	set the exit status to 1 if a change is needed/made. Optional parameter.
  -use-cache
    	Use cache to improve performance. Optional parameter.
  -version
    	Show version information
  -version-only
    	Show only the version string
```

The short `-h` spelling has the same successful help behavior. If help is the first argument it takes precedence over later unknown tokens. After `--`, a token such as `--help` is a path and must not display usage.

## Spec 4

`-version` exits 0 and writes full version metadata to stdout. It contains five labeled lines: `version:`, `built with:` followed by a Go-version-looking value containing `go1.`, `tag:`, `commit:`, and `source: github.com/incu6us/goimports-reviser/v3`. No particular build tag or commit value is required, but none of the labels may be omitted.

## Spec 5

For normal processing, stderr carries progress logs and stdout is reserved for source or file-list output. Logs use the conventional timestamp prefix `YYYY/MM/DD HH:MM:SS `. First log the complete resolved input list as `Paths: [p1 p2 ...]`, then log `Processing p` for each top-level target. Errors use the same stream and prefix where applicable. Tests ignore the varying timestamp but require the phrases and paths.

An ordinary successful operation exits 0. A flag-parse error exits 2. A validation, module-discovery, file, directory, or Go-parse failure exits 1. If an input among multiple inputs fails, return failure; stopping at that failure is allowed. Do not crash or hang on malformed, empty, inaccessible, or missing input.

## Spec 6

Each processed `.go` source is parsed as Go, its imports are reorganized, and valid source is emitted with canonical Go formatting: tabs for indentation/alignment, normalized spaces, and a final newline. Package declarations, all non-import declarations, expressions, constants, variables, structs, receiver methods, function bodies, Unicode comments, and codeless declarations retain their semantics and text content apart from canonical whitespace.

Import declarations are consolidated and formatted, but an existing one-item declaration's parenthesized shape is preserved. A source-level `import "path"` remains a single-line declaration. A parenthesized block remains `import (` with tab-indented specs and `)`, even when it initially contains only one spec or `-rm-unused` leaves only one spec. Thus reducing

```go
import (
	"fmt"
	"os"
)
```

to the sole used `fmt` import produces:

```go
import (
	"fmt"
)
```

Multiple import declarations may be combined. Empty `import ()` declarations and an import declaration left empty after removal are deleted completely. Duplicate identical imports in the source collapse to one. A file with no imports is accepted and does not gain an import declaration. Already canonical source is stable byte-for-byte.

Without `-rm-unused`, an import remains even when the file does not refer to it. Processing is about organization, not compiler validity.

## Spec 7

Every ordinary import is assigned to one of four base categories, with this precedence:

1. `project`: paths beginning with the project/module name.
2. `company`: paths beginning with any configured company prefix.
3. `std`: standard-library paths, conventionally paths whose first component contains no dot (for example `fmt`, `encoding/json`, and `net/http`). Project matching occurs first, so a dotless module such as `testmodule/internal/pkg` is still project-local.
4. `general`: all remaining third-party imports.

Project matching takes precedence over company matching when prefixes overlap. For example, with project `example.com/acme/project` and company prefix `example.com/acme/project/company`, both `example.com/acme/project/company/x` and `example.com/acme/project/local` belong to the project group and are adjacent rather than separated by a blank line. Project and company prefix matching uses the full unquoted import path, not its alias. Standard-library classification has the dot-alias exception described in Spec 8. Within every emitted group, sort lexicographically by full import path. Thus standard subpackages sort as `encoding/json`, `encoding/xml`, `fmt`, `net/http`, `net/url`, and versioned paths use ordinary lexical path ordering. Populated groups are separated by exactly one blank line; empty groups produce neither content nor extra blank lines.

The default group order is `std`, `general`, `company`, `project`. With no company prefixes, would-be company packages are general. With no usable project name, would-be project packages are general.

## Spec 8

`-imports-order` is a comma-separated order drawn from `std`, `general`, `company`, `project`, `blanked`, and `dotted`. Trim surrounding whitespace from each item. Empty or whitespace-only input selects the default. First reject any unrecognized entry with exit 1 and `unknown order group type: "NAME"`, even if the list is also short. If all names are recognized, a nonempty order must contain at least four entries; otherwise exit 1 and include exactly:

```text
use default at least 4 parameters to sort groups of your imports: "std,general,company,project"
```

Four, five, or six recognized entries are accepted and emitted in the specified order. Repeated group names are processed repeatedly rather than rejected; for example, `std,general,std,company,project` emits the `std` imports at both requested positions.

When the corresponding special group is absent, `_` imports remain classified in their base category. A `.` import still uses a matching project or company category, but otherwise belongs to `general`, including when its dotless import path would ordinarily be `std`. For example, with `-project-name=none` and the default order, imports `"fmt"`, `"other.example/x"`, `_ "project.example/side"`, and `. "stdlike"` are emitted as `"fmt"` in the `std` group, followed by one `general` group ordered as `"other.example/x"`, `_ "project.example/side"`, `. "stdlike"`.

If `blanked` appears in the order, all `_` imports instead form that category. If `dotted` appears, all `.` imports instead form that category. Explicit special groups are separated with the same single blank line as base groups.

## Spec 9

Preserve an import's explicit name, including ordinary aliases, `_`, and `.`. With `-separate-named`, within each main category emit unnamed imports first and explicitly named imports second, separated by one blank line when both subsets exist. `_` and `.` are governed by the special-group rule in Spec 8 rather than treated as ordinary named aliases when their special categories are requested.

For example, in the standard group, `"fmt"` and `"strings"` precede a blank line and then `myos "os"`; the same unnamed-then-named subdivision applies independently to general, company, and project groups.

## Spec 10

Inline `//` comments and inline `/* ... */` comments attached to import specs are preserved and move with their imports. Canonical formatting aligns adjacent trailing comments with tabs/spaces in the manner of `gofmt`; comment text is not truncated. Unattached standalone comments inside a reorganized import block need not survive. Comments outside imports, including package documentation and ordinary top-of-file comments, are preserved in their original logical position.

Preserve modern build constraints such as `//go:build (linux && amd64) || (darwin && arm64)` and `//go:build !windows` above the package declaration. A legacy first-line constraint such as `//+build linux,amd64` is canonicalized like modern Go formatting to:

```go
//go:build linux && amd64
// +build linux,amd64

package main
```

Build constraints remain before any package documentation, which remains immediately associated with the package clause.

## Spec 11

The cgo pseudo-import is special. Preserve its preamble comment and a separate `import "C"` declaration; do not merge `C` into or reorder it with the ordinary import block. Ordinary imports elsewhere in the same file are still sorted and grouped. With `-rm-unused`, `C` is always retained while unused ordinary imports can be removed. A file whose only import is `C` is accepted and its cgo calls and preamble remain intact.

## Spec 12

`-format` requests full canonical Go formatting in addition to import organization. It must fix compact forms such as `func main(){...}`, indentation, spacing around operators/assignments, package/import separation, and blank-line separation between top-level functions, methods, types, and declarations. Import sorting and grouping still occur. Baseline processing already applies canonical Go formatting even without this flag, including to a valid file with no imports: for example, four spaces before `_ = 1 + 1` become one tab under `-output stdout` alone.

## Spec 13

`-rm-unused` removes each ordinary import whose effective package identifier is not referenced anywhere in that file's Go syntax. Detect usage throughout the entire AST, including selectors in nested calls and closures, package variables/constants, composite literals, embedded fields, struct-field types, interfaces, parameter and return types, pointer types, channels, slices, maps, type assertions, and methods on package-defined values. For an explicitly aliased import, usage is through that alias. Multiple references and multiple import declarations must be handled.

Always retain `_` side-effect imports, `.` imports, and `C`, regardless of ordinary selector analysis. There is an additional observed exception to ordinary unused removal: when a parenthesized import block contains a `_` or `.` import, unreferenced ordinary imports in that block are retained too. For example, a block containing used `"fmt"`, `_ "image/png"`, unused `"os"`, and used `"strings"` remains a four-item block under `-rm-unused`. When removal leaves no imports, remove the import declaration entirely. The operation composes with grouping, `-format`, and `-set-alias`.

## Spec 14

`-set-alias` handles imported packages whose declared package name differs from a semantic-version-looking final import-path component. Determine the package's actual Go package name in the current module environment and add it explicitly. Required examples are:

```go
pg "github.com/go-pg/pg/v9"
yaml "gopkg.in/yaml.v2"
```

It applies to multiple such imports in one file and keeps normal grouping/order. Do not add redundant aliases to standard-library or ordinary non-versioned paths.

## Spec 15

The project name comes from `-project-name` when supplied; this bypasses all `go.mod` discovery and works even if no module file exists. Otherwise, perform module discovery before applying exclusions, including for a directly named target that matches `-excludes`. For a regular-file target, search for `go.mod` from the target file's containing directory and then each parent up to the filesystem root. For a directory target, start from that target directory and search its parents. Parse the discovered file's `module` directive. The target location controls this search rather than the process's current working directory: when the CWD and target are in different modules, the target's module is used. Stdin has no filesystem target and instead searches from the process's current working directory and its parents. Preserve complete module names, including subdomains, `gopkg.in` forms, and `/vN` suffixes. A file containing only a valid `module` directive is sufficient; comments and blank lines are allowed.

When automatic discovery is in use and no module can be found, exit 1 and report `Could not determine project name for path PATH: open go.mod: no such file or directory`. A parsed `go.mod` with no module directive reports `module is undefined`; malformed module syntax propagates a specific error such as `go.mod:3: unknown directive: this`. An empty path exits 1 and reports exactly `Could not determine project name for path : path is not set`, not merely the inner `path is not set` error. These project-name errors go to stderr and may be preceded by usage.

## Spec 16

For a regular file target, the output modes are:

- `file` (the default): replace the input file in place with the result and emit no source on stdout.
- `write`: likewise replace the input file in place and emit no source on stdout.
- `stdout`: write the complete resulting source to stdout and leave the file byte-for-byte unchanged.

When several files use `stdout`, concatenate each complete formatted source in input order; each source ends in a newline. Progress logs remain on stderr, so stdout is clean source text. A generated file skipped in `stdout` mode yields its original source unchanged. An invalid output value is an operational validation error: exit 1 and log `invalid output "VALUE" specified` (or equivalently a diagnostic containing `invalid output` and the value).

## Spec 17

The special path `-` means standard input and is logged/displayed as `<standard-input>`. Read all stdin as Go source and always emit the result to stdout; default `file` mode must not try to create a file. Import-order, company, project, formatting, and exit-status options apply to stdin, and `-output stdout` is accepted explicitly. `-rm-unused` is not supported for stdin because its package analysis treats `-` as a package-loading target. Given valid stdin and `-rm-unused -format -company-prefixes corp/ -output stdout -`, it exits 1, emits no source, writes the unprefixed detail `-: no Go files in`, and then logs `Failed to fix file: package has an errors`.

For valid input, output is exactly the canonical source and ends in a newline. A package-only input `package main\n` is returned unchanged; valid no-import source is supported. Empty stdin exits 1 with `Failed to fix file: file is empty and cannot be parsed as Go source` and a parser detail containing `expected 'package', found 'EOF'`. Invalid source exits 1 and reports `<standard-input>`, `Failed to fix file: file has invalid Go source content`, and the specific parse detail. Consequently, a noninteractive invocation with `-` and empty input is rejected rather than hanging.

## Spec 18

After the module discovery described in Spec 15 succeeds, directory traversal selects only files whose names end in `.go`; other file types are not transformation candidates. `go.mod` is therefore not transformed, but a `go.mod` at the directory target or an ancestor is read for module discovery before traversal. A malformed target-local `go.mod` makes the invocation exit 1 even when the directory tree contains no Go files; for example, content `not relevant` produces an `unknown directive: not` module-discovery error. Without `-recursive`, inspect only `.go` files directly in that directory. With `-recursive`, traverse descendants to arbitrary practical depth. A target ending in `/...` has no special meaning: `tree/...` is treated as that literal path, and if it does not exist the command exits 1 with `Failed to fix file: open PATH: no such file or directory`. Use `-recursive` for recursive traversal. `.` means the current directory. Handle several directory targets and mixtures of individual files and directories.

In normal fix mode, process every selected Go file. Directory processing always writes selected files in place and emits no source, even with `-output stdout`; output modes in Spec 16 govern regular-file targets, not files reached through a directory target. Once module discovery succeeds, empty directories, directories containing only non-Go files, and nested empty directory trees succeed with no stdout data. Directory symlinks must not cause a crash or traversal loop; it is acceptable not to follow them. The tested workloads (roughly ten files and ten directory levels) must complete comfortably within five seconds.

## Spec 19

Recursive directory traversal excludes `.git`, `.idea`, and `.vscode` directory trees by default. `-excludes` adds a comma-separated list of exclusion globs. During directory traversal, patterns are interpreted relative to the top-level directory target (or as absolute patterns when absolute); they are not reapplied to every basename or directory component at arbitrary depth. Consequently:

- `proto/*.go` excludes a matching file under the target's top-level `proto` directory.
- `vendor/` prunes a top-level `vendor` tree.
- `pkg/*/generated/` prunes matching target-relative trees.
- an absolute pattern such as `/tmp/project/skip/*.go` matches that absolute location.
- `excluded.go`, `*_test.go`, `*.pb.go`, and `file?.go` do not match files below `nested/` merely by basename.
- `internal/` does not match `a/internal/` merely because an `internal` component occurs deeper in the path.

Every comma-separated pattern participates in directory traversal. A matched directory prunes its complete subtree, and component matching is exact: top-level `vendor/` excludes `vendor` but not `vendor-tools` or `vendordata`. For directory traversal, apply exclusions before generated-file inclusion.

`-excludes` does not exclude a directly named file target. Such a file is processed normally; with `-list-diff` it is listed, and with `-apply-to-generated-files` a directly named generated file is transformed even if its basename appears in `-excludes`. Module discovery likewise occurs before this ineffective direct-file exclusion check.

## Spec 20

By default, do not transform a generated Go file. Recognize a generated marker only when it is a line comment before the package declaration whose content begins `// Code generated` and ends exactly `DO NOT EDIT.`. Text may occur between those phrases. These are generated markers:

```go
// Code generated by protoc-gen-go. DO NOT EDIT.
// Code generated by my-tool version 1.2.3 DO NOT EDIT.
```

A marker missing `DO NOT EDIT.`, a `/* ... */` block comment, a marker after `package`, or a line with extra text after `DO NOT EDIT.` does not mark the file generated and the file is processed normally. A recognized generated file is left byte-for-byte unchanged in ordinary file/write mode; explicit stdout mode may pass its original text through. A directly named generated file is nevertheless listed by `-list-diff` even without `-apply-to-generated-files`. `-apply-to-generated-files` disables the transformation skip, allowing all ordinary transformations, formatting, listing, and writing.

## Spec 21

For files reached through a directory target, `-list-diff` detects whether import organization and requested formatting would change each file. Write each changed file's path alone on stdout, one path per line, and do not list unchanged or skipped directory members. In contrast, a directly named regular file under default/`file` list-diff is listed whether it is changed or already canonical. It is also listed when it is a recognized generated file or when its basename matches `-excludes`. Without `-set-exit-status`, listing a file still exits 0.

For a directory target, list-diff is always a non-mutating scan, even with `-output write`. For a directly named file, default/`file` list-diff is non-mutating, while `-list-diff -output write` both lists and writes that file. For a directly named changed file with `-output stdout`, the filename listing takes precedence over source output and the disk file remains unchanged. If such a directly named file is already unchanged, stdout mode may output its canonical source rather than a filename. `-apply-to-generated-files`, directory exclusions, recursion, and cache behavior otherwise apply to the comparison.

## Spec 22

`-set-exit-status` changes a successful regular-file or stdin processing status to 1 if the source needed or received a transformation; it remains 0 if the source was already canonical. This applies in file, write, stdout, supported stdin, `-rm-unused`, `-format`, and direct-file `-list-diff` workflows. The requested write or stdout output still happens before exit 1.

An ordinary directory fix does not aggregate this change status: it exits 0 even when selected files are rewritten. Directory `-list-diff` does aggregate comparison status: with `-set-exit-status`, a scan containing a changed member lists that path as specified in Spec 21 and exits 1; an all-clean or empty scan exits 0. Independent parse/module/I/O failures are already errors and remain nonzero.

## Spec 23

`-use-cache` maintains a persistent per-file cache under `.cache/goimports-reviser` in the operating-system account's home directory. It resolves that account home independently of the process's `HOME` environment variable: when the executable runs as `root`, setting `HOME` to a temporary directory still creates entries under `/root/.cache/goimports-reviser/`, not under the overridden value.

Cache identity includes the file path and current file contents, so different paths containing identical text are processed independently and changing a file's contents invalidates its entry. Transformation and output options are not part of the identity. Thus, after caching `package p\nimport "fmt"\n`, a second invocation of the same file with `-rm-unused` is treated as a hit and leaves the import intact. A hit skips output as well as transformation: adding `-output stdout` on a cached canonical file succeeds with empty stdout. On a cache hit in an in-place mode, do not rewrite the file, so its modification time remains unchanged.

## Spec 24

Unreadable, nonexistent, empty, and syntactically invalid source must produce useful stderr diagnostics and never partial invalid output. Missing targets report the attempted path and `no such file or directory`, normally in `Failed to fix file: open PATH: no such file or directory` after module discovery succeeds. An invalid directory member makes directory processing fail with a diagnostic containing `Failed to fix directory`, `failed to walk dif`, and the underlying parser error.

For malformed Go, include `Failed to fix file: file has invalid Go source content, use -excludes flag to skip this file:` followed by the path, line/column, and parser detail (for example `string literal not terminated` or `missing import path`). For an empty file, use `Failed to fix file: file is empty and cannot be parsed as Go source, use -excludes flag to skip this file:` plus `expected 'package', found 'EOF'`. An inaccessible file encountered during a directory scan must not crash the process; accessible siblings should still be considered whenever possible.
