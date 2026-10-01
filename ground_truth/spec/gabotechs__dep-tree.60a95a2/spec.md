# Executable behavioral specification

## Spec 1

The required artifact is one executable file named exactly `executable`. It is a command-line program named `dep-tree` that analyzes source-file dependencies. It must work when invoked through an absolute or relative path from arbitrary current working directories. It must not require source files, assets, services, or documentation other than the files supplied by the caller. It must finish ordinary invocations within five seconds and larger HTML/TUI operations within thirty seconds.

The supported operations are `entropy`, `tree`, `check`, `explain`, `config`, and `help`; `init` is an exact alias of `config`. A source-file argument in root position selects `entropy`, so `dep-tree main.py --no-browser-open` and `dep-tree entropy main.py --no-browser-open` have the same semantics. With no arguments, print the main help and exit 0. `help` alone also prints main help. `help NAME` must equal `NAME --help` for each named command.

## Spec 2

Command and flag parsing follows conventional Cobra-style rules. Global options may occur after a subcommand and, where unambiguous, before it. These global options exist:

- `-c, --config string`, default `.dep-tree.yml`;
- `--exclude stringArray`, repeatable;
- `--only stringArray`, repeatable;
- `--unwrap-exports`, default false;
- `--js-tsconfig-paths`, default true;
- `--js-workspaces`, default true;
- `--python-exclude-conditional-imports`, default false.

Boolean options accept bare form and `--flag=true` or `--flag=false`. For example, `tree --json=false` is valid parsing, although it still needs an entrypoint. A value other than `true` or `false` fails; `tree --json=maybe` reports `Error: invalid argument "maybe" for "--json" flag`. String options accept separate and `=` forms. A missing value reports, for example, `Error: flag needs an argument: --config` or `Error: flag needs an argument: --render-path`.

Command-specific options are accepted only by their command: `entropy` has `--enable-gui`, `--no-browser-open`, and `--render-path string`; `tree` has `--json`; `explain` has `-l, --overlap-left` and `-r, --overlap-right`. Thus a root-level `--json` or `--overlap-left` is an unknown flag. Repeatable string-array options may use either `--only PATTERN` or `--only=PATTERN` (similarly for `--exclude`). `--` ends option parsing; subsequent words are positional inputs to the current/default command.

Unknown options exit 1 and write only an `Error: unknown flag: FLAG` diagnostic to stderr (possibly followed by a standard usage hint). Unknown words are not diagnosed as unknown subcommands: because entropy is the default, `chekc`, `CHECK`, or `totally-nonexistent-command` is treated as an entrypoint and normally reports `Error: ARG does not match with any existing file`. Command names are case-sensitive. `not-a-command --help` nevertheless prints main help and exits 0. If any unknown option accompanies `--help`, the option error takes precedence, stdout is empty, and the status is nonzero.

## Spec 3

`--version` and `-v` print exactly the following line to stdout, with its final newline, and exit 0 with empty stderr:

```text
dep-tree version v0.23.4
```

`--help`, `-h`, and the no-argument behavior print this exact main help (including the initial blank line and final newline) to stdout and exit 0 with empty stderr:

```text

      ____         _ __       _
     |  _ \   ___ |  _ \    _| |_  _ __  ___   ___
     | | | | / _ \| |_) |  |_   _||  __|/ _ \ / _ \
     | |_| ||  __/| .__/     | |  | |  |  __/|  __/
     |____/  \__| |_|        | \__|_|   \___| \___|

Usage:
  dep-tree [command]

Examples:
$ dep-tree src/index.ts
$ dep-tree entropy src/index.ts
$ dep-tree tree package/main.py --unwrap-exports
$ dep-tree check

Visualize your dependencies graphically
  entropy     (default) Renders a 3d force-directed graph in the browser
  tree        Render the dependency tree starting from the provided entrypoint

Check your dependencies against your own rules
  check       Checks that the dependency rules defined in the configuration file are not broken

Display what are the dependencies between two portions of code
  explain     Shows all the dependencies between two parts of the code

Additional Commands:
  config      Generates a sample config in case that there's not already one present
  help        Help about any command

Flags:
  -c, --config string                        path to dep-tree's config file. (default .dep-tree.yml)
      --unwrap-exports                       trace re-exported symbols to the file where they are declared. (default false)
      --js-tsconfig-paths                    follow the tsconfig.json paths while resolving imports. (default true)
      --js-workspaces                        take the workspaces attribute in the root package.json into account for resolving paths. (default true)
      --python-exclude-conditional-imports   exclude imports wrapped inside if or try statements. (default false)
      --only stringArray                     Files that do not match this glob pattern will be ignored. You can provide an arbitrary number of --only flags.
      --exclude stringArray                  Files that match this glob pattern will be ignored. You can provide an arbitrary number of --exclude flags.
  -h, --help                                 help for dep-tree
  -v, --version                              version for dep-tree

Use "dep-tree [command] --help" for more information about a command.
```

## Spec 4

Subcommand help is exact, exits 0, is written to stdout, and leaves stderr empty. Each block below has a final newline. `init --help` is identical to `config --help`.

For `entropy --help`:

```text
(default) Renders a 3d force-directed graph in the browser

Usage:
  dep-tree entropy [flags]

Flags:
      --enable-gui           Enables a GUI for changing rendering settings
  -h, --help                 help for entropy
      --no-browser-open      Disable the automatic browser open while rendering entropy
      --render-path string   Sets the output path of the rendered html file

Global Flags:
  -c, --config string                        path to dep-tree's config file. (default .dep-tree.yml)
      --exclude stringArray                  Files that match this glob pattern will be ignored. You can provide an arbitrary number of --exclude flags.
      --js-tsconfig-paths                    follow the tsconfig.json paths while resolving imports. (default true)
      --js-workspaces                        take the workspaces attribute in the root package.json into account for resolving paths. (default true)
      --only stringArray                     Files that do not match this glob pattern will be ignored. You can provide an arbitrary number of --only flags.
      --python-exclude-conditional-imports   exclude imports wrapped inside if or try statements. (default false)
      --unwrap-exports                       trace re-exported symbols to the file where they are declared. (default false)
```

For `tree --help`:

```text
Render the dependency tree starting from the provided entrypoint

Usage:
  dep-tree tree [flags]

Flags:
  -h, --help   help for tree
      --json   render the dependency tree in a machine readable json format

Global Flags:
  -c, --config string                        path to dep-tree's config file. (default .dep-tree.yml)
      --exclude stringArray                  Files that match this glob pattern will be ignored. You can provide an arbitrary number of --exclude flags.
      --js-tsconfig-paths                    follow the tsconfig.json paths while resolving imports. (default true)
      --js-workspaces                        take the workspaces attribute in the root package.json into account for resolving paths. (default true)
      --only stringArray                     Files that do not match this glob pattern will be ignored. You can provide an arbitrary number of --only flags.
      --python-exclude-conditional-imports   exclude imports wrapped inside if or try statements. (default false)
      --unwrap-exports                       trace re-exported symbols to the file where they are declared. (default false)
```

For `check --help`:

```text
Checks that the dependency rules defined in the configuration file are not broken

Usage:
  dep-tree check [flags]

Flags:
  -h, --help   help for check

Global Flags:
  -c, --config string                        path to dep-tree's config file. (default .dep-tree.yml)
      --exclude stringArray                  Files that match this glob pattern will be ignored. You can provide an arbitrary number of --exclude flags.
      --js-tsconfig-paths                    follow the tsconfig.json paths while resolving imports. (default true)
      --js-workspaces                        take the workspaces attribute in the root package.json into account for resolving paths. (default true)
      --only stringArray                     Files that do not match this glob pattern will be ignored. You can provide an arbitrary number of --only flags.
      --python-exclude-conditional-imports   exclude imports wrapped inside if or try statements. (default false)
      --unwrap-exports                       trace re-exported symbols to the file where they are declared. (default false)
```

For `explain --help`:

```text
Shows all the dependencies between two parts of the code

Usage:
  dep-tree explain [flags]

Flags:
  -h, --help            help for explain
  -l, --overlap-left    When there's an overlap between the files at the left and the right, keep the ones at the left
  -r, --overlap-right   When there's an overlap between the files at the left and the right, keep the ones at the right

Global Flags:
  -c, --config string                        path to dep-tree's config file. (default .dep-tree.yml)
      --exclude stringArray                  Files that match this glob pattern will be ignored. You can provide an arbitrary number of --exclude flags.
      --js-tsconfig-paths                    follow the tsconfig.json paths while resolving imports. (default true)
      --js-workspaces                        take the workspaces attribute in the root package.json into account for resolving paths. (default true)
      --only stringArray                     Files that do not match this glob pattern will be ignored. You can provide an arbitrary number of --only flags.
      --python-exclude-conditional-imports   exclude imports wrapped inside if or try statements. (default false)
      --unwrap-exports                       trace re-exported symbols to the file where they are declared. (default false)
```

For `config --help` and `init --help`:

```text
Generates a sample config in case that there's not already one present

Usage:
  dep-tree config [flags]

Aliases:
  config, init

Flags:
  -h, --help   help for config

Global Flags:
  -c, --config string                        path to dep-tree's config file. (default .dep-tree.yml)
      --exclude stringArray                  Files that match this glob pattern will be ignored. You can provide an arbitrary number of --exclude flags.
      --js-tsconfig-paths                    follow the tsconfig.json paths while resolving imports. (default true)
      --js-workspaces                        take the workspaces attribute in the root package.json into account for resolving paths. (default true)
      --only stringArray                     Files that do not match this glob pattern will be ignored. You can provide an arbitrary number of --only flags.
      --python-exclude-conditional-imports   exclude imports wrapped inside if or try statements. (default false)
      --unwrap-exports                       trace re-exported symbols to the file where they are declared. (default false)
```

For `help --help`:

```text
Help provides help for any command in the application.
Simply type dep-tree help [path to command] for full details.

Usage:
  dep-tree help [command] [flags]

Flags:
  -h, --help   help for help

Global Flags:
  -c, --config string                        path to dep-tree's config file. (default .dep-tree.yml)
      --exclude stringArray                  Files that match this glob pattern will be ignored. You can provide an arbitrary number of --exclude flags.
      --js-tsconfig-paths                    follow the tsconfig.json paths while resolving imports. (default true)
      --js-workspaces                        take the workspaces attribute in the root package.json into account for resolving paths. (default true)
      --only stringArray                     Files that do not match this glob pattern will be ignored. You can provide an arbitrary number of --only flags.
      --python-exclude-conditional-imports   exclude imports wrapped inside if or try statements. (default false)
      --unwrap-exports                       trace re-exported symbols to the file where they are declared. (default false)
```

## Spec 5

Argument counts are validated after option parsing. `entropy` requires at least one entrypoint; zero gives `Error: requires at least 1 arg(s), only received 0`. `tree` also requires at least one matched entrypoint, but its rendering supports exactly one: after expansion, two inputs give `Error: this functionality requires that only 1 entrypoint is provided, but 2 where passed. Consider providing a single entrypoint to your program`. `explain` requires exactly two positional patterns and reports `Error: accepts 2 arg(s), received N` for 0, 1, or 3 arguments. `config` accepts no positional arguments. `check` accepts no positional source paths.

The two explain overlap flags are mutually exclusive, including combined `-lr`; using both gives `Error: only one of --overlap-left (-l) or --overlap-right (-r) can be used at a time` and status 1.

For the default entropy route, match positional entrypoint patterns before opening an explicitly named config. Consequently `--config=nope -- tree` treats `tree` as a positional after `--` and reports `Error: tree does not match with any existing file`, rather than reporting the missing `nope` config first.

## Spec 6

Entrypoint arguments and explain operands are case-sensitive filesystem glob patterns. Support literal paths, `*`, `?`, bracket expressions such as `[ab]`, and recursive `**`. `**/name` also matches `name` at the starting directory. Resolve relative patterns against the current working directory; accept absolute paths. Sort expanded matches deterministically. Follow symlinks to regular files, but treat a broken symlink as no match. Ignore directories among matches; if nothing remains because only directories were supplied, report `Error: no valid files where provided`.

If an operand matches nothing, report `Error: OPERAND does not match with any existing file`. A malformed positional glob reports `Error: syntax error in pattern`. Source extensions identify a language family: Python `.py` and `.pyi`; JavaScript/TypeScript `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, and `.d.ts`; Rust `.rs`; Go `.go`; and the fixture language `.dl`. If matches exist but none has a supported extension, report exactly `Error: none of the provided files belong to the a supported language`. A single analysis accepts entrypoints from different supported language families. For example, when empty files `a.dl` and `b.js` exist, `entropy a.dl b.js --no-browser-open --render-path mixed.html` exits 0, writes exactly `mixed.html\n` to stdout, and creates `mixed.html`. `tree` still rejects multiple matches because it supports exactly one rendered entrypoint, as specified in Spec 5.

## Spec 7

The analyzer builds a directed file graph. A node is a local source file and edge `A -> B` means A directly imports, includes, declares, or re-exports B according to the relevant language. Never add external standard-library or third-party dependencies unless they are explicitly resolvable as a configured local workspace/path dependency. Deduplicate repeated imports and edges. Preserve diamonds: if two branches depend on one shared file, that file appears under both branches in nested tree output. Traverse without depth limits relevant to ordinary projects (chains of at least eleven files are required).

Graph traversal begins at every entrypoint and recursively loads reachable local files. Children and report lines are sorted lexicographically by displayed path. Empty files and files with no local imports are valid leaf nodes. Ordinary JavaScript/Python parse irregularities should be tolerated when imports can still be found; the entry file remains represented rather than causing a crash. Comments, shebangs, UTF-8 source, CRLF input, and filenames near filesystem length limits must work. Language-specific dependency syntax still limits names written inside source: in particular, the `.dl` `PATH` token has the narrower character set in Spec 21 and therefore cannot name dependencies containing spaces or non-ASCII characters.

## Spec 8

`tree --json ENTRY` writes one JSON object to stdout and exits 0 when initial validation succeeds, even if recoverable import-resolution errors occur. Serialize it as indented JSON with two spaces per nesting level: the opening and final top-level braces are each on their own line, and the final brace is followed by a newline. JSON examples below that compact a nested value onto one line specify parsed structure only; the emitted form still expands that value using this indentation. The object has exactly these top-level fields and types:

```json
{"tree": {"entry.js": null}, "circularDependencies": [], "errors": {}}
```

`tree` maps each displayed file path to either `null` for a leaf or another path-keyed object. A cycle back-edge is not recursively inserted; instead list the closed path in `circularDependencies`. For A importing B and B importing A:

```json
{
  "tree": {"a.js": {"b.js": null}},
  "circularDependencies": [["a.js", "b.js", "a.js"]],
  "errors": {}
}
```

A three-node cycle is `[["a.dl","b.dl","c.dl","a.dl"]]`. Multiple distinct cycles are all reported. Every cycle begins and ends with the same path and has at least three entries. Recoverable diagnostics are arrays of strings keyed by the source file responsible for them (or by `""` for malformed empty/single-character JavaScript import paths). JSON stdout contains no progress or explanatory text. Display paths use `/`, are normalized (no internal `./`), and are relative to the discovered project root wherever possible; an absolute entrypoint must not force otherwise-relative descendants to become absolute. Preserve the lexical path of a matched file symlink in display keys rather than replacing it with the symlink target: a `src_b.js` symlink to `../src_b.js` displays as `src_b.js`, and an imported `util_a.js` symlink to `../util_a.js` displays as `util_a.js`. Workspace nodes use the more specific base in Spec 17.

## Spec 9

`--only` and `--exclude` filter the complete graph and apply to entrypoints too. A file is eligible when either no `only` patterns exist or it matches at least one of them (OR semantics), and it matches none of the exclude patterns. Exclusion wins when both match. Repeated CLI patterns accumulate. Config-file patterns and CLI patterns also accumulate; CLI patterns do not replace config patterns. For a directly supplied `tree` or `entropy` entrypoint, an empty `--only ""`, a no-match-only set, wrong-case pattern, or explicit exclusion that removes the entrypoint fails with:

```text
Error: selected entrypoint ABSOLUTE_PATH is explicitly ignored
```

For `check`, filtering a configured `check.entrypoints` file does not produce that fatal diagnostic. The filtered entrypoint is skipped. If the sole configured entrypoint is filtered out, `check` succeeds with status 0 and empty stdout; stderr contains the initial Braille frame followed by `(0/1) Finished loading` twice, with transient clearing characters between frames.

Patterns may themselves be absolute. Match both normalized absolute paths and useful project-relative forms, so `util.js`, `util*.js`, `**/utils.js`, and an absolute path to the same file work. A malformed filter such as `[invalid` fails fast, before graph traversal, with `Error: only pattern 'ABSOLUTE_PATTERN' is not correctly formatted` or the equivalent `exclude pattern`. Validate exclude patterns before only patterns regardless of their textual or YAML order, so if both categories contain a malformed pattern, report only the exclude-pattern error.

Filtering removes a node and all traversal through it rather than promoting its children. For `main.js` importing `helper1.js` and `helper2.js`, both importing `utils.js`, excluding `utils.js` yields:

```json
{
  "tree": {"main.js": {"helper1.js": null, "helper2.js": null}},
  "circularDependencies": [],
  "errors": {}
}
```

The same filters apply to `tree`, `entropy`, `explain`, and `check`.

## Spec 10

Configuration is YAML. Unless explicitly overridden, look for `.dep-tree.yml` in the current working directory. Its absence is silently acceptable to `tree`, `entropy`, and `explain`, but not to `check`. Passing `-c/--config PATH` makes that file mandatory for analysis commands; a missing file reports `Error: open PATH: no such file or directory`. The `config`/`init` generator is the exception: it accepts the global option but does not read or write that path and always targets `.dep-tree.yml`. A malformed file fails before the operation with `Error: config file "PATH" is not a valid yml file: YAML_ERROR`, retaining useful YAML line information such as `yaml: line 5: did not find expected node content`.

The allowed document shape is:

- top-level `exclude: [string...]`, `only: [string...]`, `unwrapExports: boolean`;
- `check.entrypoints: [string...]`, `check.allowCircularDependencies: boolean`, `check.allow`, `check.deny`, and `check.aliases`;
- `js.workspaces: boolean` and `js.tsConfigPaths: boolean`;
- `python.excludeConditionalImports: boolean`;
- `rust`, currently null/empty.

An allow value is either a string-pattern list or `{to: [patterns...], reason: string?}`. A deny value is either a string-pattern list or a list of `{to: pattern, reason: string?}`. Aliases map a name to a string-pattern list and may appear as target entries in allow/deny. Reject malformed glob patterns in `only` and `exclude` with the filter diagnostic from Spec 9. CLI booleans override corresponding config booleans when explicitly set.

## Spec 11

`config` and `init` create exactly `.dep-tree.yml` in the current working directory, nowhere else. On success they exit 0, write no meaningful stdout/stderr, create no backup/temp files, encode plain UTF-8, and set mode `0600` (owner read/write only). They work in nested, whitespace-containing, and Unicode directories. Both commands produce byte-identical files and identical permissions.

Never overwrite an existing filesystem entry named `.dep-tree.yml`, including a directory or a symlink to an existing file. Fail nonzero, leave it untouched, place the error only on stderr, and mention `.dep-tree.yml` and `already exists`. A broken symlink is treated as a writable target: retain the symlink, create its target with the template, and succeed. Repeated creation attempts fail consistently.

## Spec 12

The generated `.dep-tree.yml` content is byte-for-byte the following, including comments, indentation, blank lines, spelling, single quotes, and final newline:

```yaml
# Files that should be completely ignored by dep-tree. It's fine to ignore
# some big files that everyone depends on and that don't add
# value to the visualization, like auto generated code.
exclude:
  - 'some-glob-pattern/**/*.ts'

# The only files that will be included by dep-tree. If a file does not
# match any of the provided patters, it is ignored.
only:
  - 'some-glob-pattern/**/*.ts'

# Whether to unwrap re-exports to the target file or not.
# Imagine that you have the following setup:
#
#  src/index.ts     -> import { foo } from './foo'
#  src/foo/index.ts -> export { bar as foo } from './bar'
#  src/foo/bar.ts   -> export function bar() {}
#
# If `unwrapExports` is true, a dependency will be created from
# `src/index.ts` to `src/foo/bar.ts`, and the middle file `src/foo/index.ts`
# will be ignored, as it's just there for re-exporting the `bar` symbol,
# which is actually declared on `src/foo/bar.ts`
#
# If `unwrapExports` is false, re-exported symbols will not be traced back
# to where they are declared, and instead two dependencies will be created:
# - from `src/index.ts` to `src/foo/index.ts`
# - from `src/foo/index.ts` to `src/foo/bar.ts`
#
# Entropy visualization tends to lead to better results if this is set to `false`,
# but CLI rendering is slightly better with this set to `true`.
unwrapExports: false

# Check configuration for the `dep-tree check` command. Dep Tree will check for dependency
# violation rules declared here, and fail if there is at least one unsatisfied rule.
check:
  # These are the entrypoints to your application. Dependencies will be checked with
  # these files as root nodes. Typically, an application has only one entrypoint, which
  # is the executable file (`src/index.ts`, `main.py`, `src/lib.rs`, ...), but here
  # you can declare as many as you want.
  entrypoints:
    - src/index.ts

  # Whether to allow circular dependencies or not. Languages typically allow
  # having circular dependencies, but that has an impact in execution path
  # traceability, so you might want to disallow it.
  allowCircularDependencies: false

  # map from glob pattern to array of glob patterns that determines the exclusive allowed
  # dependencies that a file matching a key glob pattern might have. If file that
  # matches a key glob pattern depends on another file that does not match any of
  # the glob patterns declared in the values array, the check will fail.
  allow:
    # example: any file in `src/products` can only depend on files that are also
    # in the `src/products` folder or in the `src/helpers` folder.
    'src/products/**':
      - 'src/products/**'
      - 'src/helpers/**'
    # additionally, instead of providing a simple list of allowed dependencies, you
    # can also provide the reason for this restriction to exist, that way, when if the
    # check fails, an informative error is displayed through stderr.
    'src/users/**':
      to:
       - 'src/helpers/**'
      reason: The Users domain is only allowed to import helper code, nothing else

  # map from glob pattern to array of glob patterns that determines forbidden
  # dependencies. If a file that matches a key glob pattern depends on another
  # file that matches at least one of the glob patterns declared in the values
  # array, the check will fail.
  deny:
    # example: files inside `src/products` cannot depend on files inside `src/users`,
    # as they are supposed to belong to different domains.
    'src/products/**':
      - 'src/users/**'
    # additionally, instead of providing a simple list of forbidden dependencies, you
    # can also provide the reason for each individual restriction to exist. If one of
    # these rules is broken, the reason will be displayed through stderr
    'src/users/**':
      - to: 'src/products/**'
        reason: The Users domain should not import anything from the Products domain
      - to: 'src/orders/**'
        reason: The Users domain should not import anything from the Orders domain

  # typically, in a project, there is a set of files that are always good to depend
  # on, because they are supposed to be common helpers, or parts that are actually
  # designed to be widely depended on. This allows you to create aliases to group
  # of files that are meant to be widely depended on, so that you can reference
  # them afterward in the `allow` or `deny` sections.
  aliases:
    # example: this 'common' entry will be available in the other sections:
    #
    # check:
    #   allow:
    #     'src/products/**':
    #       - 'common'
    'common':
      - 'src/helpers/**'
      - 'src/utils/**'
      - 'src/generated/**'

# JavaScript and TypeScript specific settings.
js:
  # Whether to take package.json workspaces into account while resolving paths
  # or not. You might want to disable it if you only want to analyze one workspace
  # in a monorepo.
  workspaces: true
  # Whether to follow tsconfig.json paths or not. You will typically want to
  # enable this, but for some monorepo setups, it might be better to leave this off
  # if you want to analyze only one package.
  tsConfigPaths: true

# Python specific settings.
python:
  # Whether to take into account conditional imports as dependencies between files or not.
  # A conditional import is an `import` statement that is wrapped inside an `if` block or
  # a function, for example:
  #
  # if SHOULD_IMPORT:
  #     from foo import *
  #
  # by default these statements introduce a dependency between importing and imported file,
  # but depending on your use case you might want to disable it.
  excludeConditionalImports: false

# Rust specific settings.
rust:
  # None available at the moment.
```

## Spec 13

Python analysis recognizes `import module`, comma-separated imports, aliases, `from module import name`, multiple/parenthesized/backslash-continued names, wildcard imports, absolute dotted imports, and relative forms such as `from . import helper`, `from .module import x`, and `from ..module import x`. Resolve local modules to `name.py`/`name.pyi`, nested dotted modules to directories, and packages to `package/__init__.py`; follow imports/re-exports in `__init__.py` recursively. Prefer a real `.py` implementation when a `.pyi` stub coexists. Ignore standard-library or otherwise non-local modules.

The `--python-exclude-conditional-imports`/`python.excludeConditionalImports` setting is accepted while parsing such projects. Syntax surrounding imports—including docstrings, comments, encoding declarations, shebangs, type syntax, inheritance, comprehensions, the walrus operator, and future imports—must not interfere. `from __future__ ...` itself is external and does not add a local edge. Missing local-looking modules and syntax errors are recoverable graph errors or ignored externals, never a crash.

## Spec 14

JavaScript/TypeScript analysis recognizes static ES imports in default, named, aliased, combined default/namespace, `import * as`, `import type`, and side-effect-only forms. It recognizes CommonJS `require("path")`, including assigned and destructured require, and literal dynamic `import("path")`, including `await import(...)`. Recognize dependency-bearing re-exports: `export * from`, `export {x}`, `export {x as y} from`, default re-export, and TypeScript type re-export.

Support modern JS/TS syntax without losing imports: JSX/TSX, interfaces, types, enums, namespaces, ambient declarations and `.d.ts`, nested destructuring, async code, shebangs, and mixed ESM/CommonJS. A parse error after an otherwise recognizable import does not remove that imported file. Multiple styles or repeated imports of the same path create one edge.

Normally a consumer depends on the barrel/re-export file and that file depends on its source. The `--unwrap-exports`/`unwrapExports` setting is accepted; regardless of its value, re-export chains must remain fully discoverable and never lose the target dependency.

## Spec 15

Resolve a relative JS/TS specifier from the importing file. An explicit extension is honored. Without an extension, probe supported JS/TS extensions, then a directory's `package.json` `main`, then its `index` file in a supported extension. Thus `./helper`, `./utils`, explicit `.js`/`.ts`, and directory barrels resolve. Do not include `node_modules` files as local graph nodes. Ignore Node built-ins, including `node:fs`, and unresolved third-party package names.

Recoverable resolution failures remain in JSON `errors` while status remains 0. Required exact messages include:

- empty specifier: key `""`, message `import path cannot be empty`;
- a single-character nonrelative specifier `x`: key `""`, message `invalid import path x`;
- absent relative target: key `""`, message `could not perform relative import for './nonexistent.js' because the file or dir was not found`.

Other missing relative imports are handled without a crash and keep the importing node in the tree.

## Spec 16

With JS tsconfig support enabled by default, find the relevant `tsconfig.json`, read `compilerOptions.baseUrl` and `compilerOptions.paths`, expand `*` captures, and resolve the resulting file using normal extension/index probing. Paths work in `.js` as well as TypeScript. When `baseUrl` is omitted, path targets are relative to the tsconfig directory. `--js-tsconfig-paths=false` or `js.tsConfigPaths: false` disables this special resolution without preventing ordinary relative resolution.

If an alias pattern matches but its target file does not exist, add one source-file error containing `import 'SPECIFIER' was matched to path ` and `in tscofing's paths option, but the resolved path did not match an existing file` (retain the misspelling `tscofing`). Malformed tsconfig JSON produces one source-file error containing `found TypeScript config file in `, `tsconfig.json but there was an error reading it:`, and the parse detail.

## Spec 17

With workspace support enabled by default, read a root `package.json` `workspaces` list, including ordinary and nested glob patterns. For each matching package directory, read its package name (including scoped names such as `@scope/pkg`) and entry (`main`, otherwise a supported `index` file). Resolve imports of that name and deep subpaths into the local workspace. In tree JSON, display each workspace dependency relative to that workspace package's own directory, not relative to the monorepo root: its entry is `index.js`, and a deep subpath is `nested/util.js`, rather than a key beginning with `packages/...`. `--js-workspaces=false` or `js.workspaces: false` disables this support.

A referenced workspace with no entry reports one error ending `packages/no-index' has no index file`. A missing deep subpath reports one error starting `path '@ws/good/nonexistent.js' matched workspace '@ws/good', but no file ` and ending `/packages/good/nonexistent.js' does not exist`. Malformed workspace `package.json` adds one error containing `error parsing`, the package's `package.json` path, and Go JSON-parser wording. A missing comma produces detail containing `invalid character`, while a truncated document produces `unexpected end of JSON input`. A project with no package.json and an unresolvable nonrelative import simply ignores that external import.

When explain output crosses two packages, remove one leading `@` from a scoped package name, then prefix each displayed relative file with that result and `@`. Thus packages named `@myorg/pkgA` and `@myorg/pkgB` produce `myorg/pkgA@index.js -> myorg/pkgB@util.js`.

## Spec 18

Rust analysis locates the crate root using `Cargo.toml` or lowercase `cargo.toml`, preferring `src/lib.rs`, then `src/main.rs`, then root `lib.rs`, then root `main.rs`. Parse `mod name;` and `pub mod name;`: from a module directory, resolve to `name.rs` or `name/mod.rs`, while an inline `mod name { ... }` remains in its containing file and is not a separate node. Recursively discover nested module declarations in either naming convention and allow named-file and `mod.rs` styles in the same crate. Attributes, visibility modifiers, test modules, comments, empty files, and cfg annotations must not break parsing.

If neither module file exists, keep the declaring file as a leaf and add an error exactly shaped as `could not find mod NAME while looking in dir ABSOLUTE_DIRECTORY`. For a crate at `rust_missing_mod/src/lib.rs` declaring `mod nonexistent`, JSON is:

```json
{
  "tree": {"src/lib.rs": null},
  "circularDependencies": [],
  "errors": {"src/lib.rs": ["could not find mod nonexistent while looking in dir ABSOLUTE_PROJECT/src"]}
}
```

## Spec 19

Rust `use` and `pub use` participate in dependency discovery. Handle crate-name-qualified paths, `crate::` from the crate root, `self::` from the current module, any number of `super::` parent traversals without crossing above root, aliases with `as`, glob imports, grouped items such as `{a,b,c}`, and nested re-exports. Fully qualified local crate paths used in code must not cause a crash. Resolve a binary's `use package_name::...` into its sibling library crate when both `main.rs` and `lib.rs` exist. Ignore non-path external crates.

Read Cargo path dependencies from both `[dependencies]` and `[dev-dependencies]`; resolve their package/module paths, including nested modules, but display files relative to the analyzed crate (for example an imported dependency module may display as `src/utils/math.rs`). Invalid path dependencies are recoverable errors. Their error includes the attempted dependency file; for a missing `../does_not_exist`, the relevant message shape is `error resolving use statement for name something: open ABSOLUTE_PATH/does_not_exist/cargo.toml: no such file or directory`.

Rust references to ancestors can form cycles; report every closed cycle deterministically. For a plain module project, representative output is:

```json
{
  "tree": {"src/lib.rs": {"src/a/mod.rs": {"src/a/b/mod.rs": {"src/a/b/c/mod.rs": null}}}},
  "circularDependencies": [],
  "errors": {}
}
```

## Spec 20

Go analysis reads the nearest `go.mod` module declaration. Parse both single and parenthesized import declarations, including normal, aliased, dot, and blank (`_`) imports. An import whose path begins with the current module name maps the remaining path to a local package directory; recursively analyze the package's `.go` files and resolve exports to their defining files. Support nested/internal packages and multiple files in one package. A representative graph is:

```json
{
  "tree": {
    "main.go": {
      "helper1/helper1.go": {"utils/utils.go": null},
      "helper2/helper2.go": {"utils/utils.go": null}
    }
  },
  "circularDependencies": [],
  "errors": {}
}
```

Ignore standard-library imports, third-party imports outside the module, and vendored external code. Build tags, `_test.go` files, generics, interfaces, constants, variables, init functions, type assertions, embed directives, and ordinary modern Go syntax must not disrupt import extraction. Same-package symbol use without an import is valid.

## Spec 21

Also support a small source language with extension `.dl`. Its complete line-oriented grammar is:

```text
statement := "export" IDENT
           | "import" IDENT ("," IDENT)* "from" PATH
```

Blank files are valid. Imports and exports can be interleaved and repeated. PATH consists only of one or more ASCII letters, `.` and `/`; the slash/dot combinations `./` and `../` are therefore accepted. Digits, underscores, hyphens, and non-ASCII characters are not PATH characters. Whitespace is skipped rather than retained within a PATH, so `de p.dl` is resolved as `dep.dl`, not as a filename containing a space. Resolve an accepted path relative to the importing file, normalize `./`, preserve a necessary leading `../` in displayed paths, and do not append an extension that was not written. Imported symbols do not alter edge identity: one path produces one edge. Imports-only and exports-only files are valid. CRLF line endings are accepted when the statement otherwise uses valid tokens.

Malformed grammar is fatal status 1 and reports an `Error:` containing the absolute source path and line/column. A syntactic token error contains `unexpected token` and the expected construct; missing `from` must mention `from`. A disallowed non-whitespace PATH character instead reports `invalid input text` beginning at that character. A missing imported `.dl` is recoverable status 0: keep the importer as a leaf and add `open ABSOLUTE_MISSING_PATH: no such file or directory` under that importer in `errors`. Literal/deep/diamond/cycle behavior is otherwise exactly the general graph behavior when all PATH tokens are valid. For example, A importing B and C, each importing D, nests D under both branches; A→B→C→A is cut at C and reported as `[["a.dl","b.dl","c.dl","a.dl"]]`.

## Spec 22

Initial-input failures are fatal (status 1): no match, unsupported language, invalid glob/config, a directly supplied `tree`/`entropy` entrypoint filtered as described in Spec 9, wrong argument count, or fatal `.dl` grammar. A configured `check` entrypoint filtered out under Spec 9 is the stated exception. Dependency-load/resolution failures discovered after a valid graph starts are generally recoverable: status 0 for JSON/entropy, an intact partial tree, and messages in `errors`.

For JavaScript/Rust missing targets, errors must retain the specific forms in Specs 15–19. Multiple errors for a source are kept in encounter order. `errors` is `{}` when none exist. A malformed JS dependency file that is already resolved still appears as a node. Self-imports do not recurse forever or create duplicate nodes. Cycles of two, three, or five files terminate promptly.

## Spec 23

Without `--json`, `tree ENTRY` is an interactive terminal program. Its stable screen is a Unicode dependency diagram. It sorts names, uses `▷` for forward dependency edges, `◁` for the return point of a circular edge, `│` for verticals, `─` for horizontals, `├`/`└` for branches, and `┴` where dependency paths merge. It never truncates filenames. Required canonical shapes include:

```text
main.js
│
├▷helper1.js
└▷│helper2.js
  ││
  └┴▷utils.js
```

```text
main.js
│
├▷dep1.js
├▷dep2.js
├▷dep3.js
├▷dep4.js
└▷dep5.js
```

```text
a.js◁─┐
│     │
└▷b.js┘
```

Two independent cycles render as:

```text
a.js◁─┐
│     │
├▷b.js┘
└▷c.js◁─┐
  │     │
  └▷d.js┘
```

A simple chain indents by two cells at each level. Shared dependencies are drawn once in the visual DAG with merging connectors, even though JSON repeats their nested occurrence. Exclusion reshapes connectors cleanly. Files with dashes, dots, underscores, spaces, Unicode, and very long names are printed unchanged.

## Spec 24

The tree TUI handles these keys: `j`/Down moves selection one screen row down; `k`/Up moves one row up; Ctrl-D and Ctrl-U move half a viewport; Enter makes the selected file the displayed subtree root; `q` returns to the prior selected root, or exits cleanly at the original root; `h` opens help; `q` from help restores the exact prior tree. Movement clamps at both ends and rapid/mixed key sequences lose no events.

The help screen is exactly:

```text

 ____         _ __       _
|  _ \   ___ |  _ \    _| |_  _ __  ___   ___
| | | | / _ \| |_) |  |_   _||  __|/ _ \ / _ \
| |_| ||  __/| .__/     | |  | |  |  __/|  __/
|____/  \__| |_|        | \__|_|   \___| \___|

Welcome to dep-tree's help section.

j      -> move one step down
k      -> move one step up
Ctrl d -> move half page down
Ctrl u -> move half page up
Enter  -> select the current node as the root node
q      -> navigate backwards on selected nodes or quit
h      -> show this help section
```

The default captured terminal viewport is 80 columns by 24 rows and exposes at most 24 diagram lines. Scrolling changes which lines are visible while retaining their original connector columns. Entering a node redraws it at column zero. For a selected `mod1.js` with five leaf dependencies, the subtree screen is exactly:

```text
mod1.js
│
├▷util1a.js
├▷util1b.js
├▷util1c.js
├▷util1d.js
└▷util1e.js
```

For a wide graph in which `main.js` imports `mod1.js`, `mod10.js`, `mod2.js`, ..., `mod9.js` and every module imports its five correspondingly numbered utilities, the initial 24-line viewport is exactly the following. This also specifies lexicographic ordering (`mod10` precedes `mod2`), connector placement, and viewport clipping:

```text
main.js
│
├▷mod1.js
├▷│mod10.js
├▷││mod2.js
├▷│││mod3.js
├▷││││mod4.js
├▷│││││mod5.js
├▷││││││mod6.js
├▷│││││││mod7.js
├▷││││││││mod8.js
└▷│││││││││mod9.js
  ││││││││││
  │├││││││││▷util10a.js
  │├││││││││▷util10b.js
  │├││││││││▷util10c.js
  │├││││││││▷util10d.js
  │└││││││││▷util10e.js
  ├─││││││││▷util1a.js
  ├─││││││││▷util1b.js
  ├─││││││││▷util1c.js
  ├─││││││││▷util1d.js
  └─││││││││▷util1e.js
    ├│││││││▷util2a.js
```

After three Down/`j` movements, the selected branch changes the horizontal routing and the same viewport is:

```text
main.js
│
├▷mod1.js
├▷│mod10.js
├▷││mod2.js
├▷│││mod3.js
├▷││││mod4.js
├▷│││││mod5.js
├▷││││││mod6.js
├▷│││││││mod7.js
├▷││││││││mod8.js
└▷│││││││││mod9.js
  ││││││││││
  │├────────▷util10a.js
  │├────────▷util10b.js
  │├────────▷util10c.js
  │├────────▷util10d.js
  │└────────▷util10e.js
  ├─││││││││▷util1a.js
  ├─││││││││▷util1b.js
  ├─││││││││▷util1c.js
  ├─││││││││▷util1d.js
  └─││││││││▷util1e.js
    ├│││││││▷util2a.js
```

One Up/`k` from there selects the `mod1.js` branch: the first 18 lines equal the initial viewport, lines 19–23 become `├─────────▷util1a.js`, `├─────────▷util1b.js`, `├─────────▷util1c.js`, `├─────────▷util1d.js`, and `└─────────▷util1e.js`, and line 24 remains `    ├│││││││▷util2a.js`. A second Up/`k` restores the byte-exact initial viewport. Two Ctrl-D movements scroll the viewport down one visible line and expose one more bottom line: it begins with `│` rather than `main.js`, otherwise has the same next 21 lines with the short-crossing (`─│...`) routing, and ends with both `    ├│││││││▷util2a.js` and `    ├│││││││▷util2b.js`. One Ctrl-U from that state changes navigation position but leaves this captured viewport byte-identical. Further movement clamps/restores according to the same half-page viewport rules.

## Spec 25

`explain FROM TO` independently expands the two glob sets, applies global filters, infers their common language, builds direct dependency information, and prints only direct edges whose source is in FROM and target is in TO. Do not report transitive reachability. Do not invent self-edges. Deduplicate graph edges before formatting and lexicographically sort them by their displayed records. Distinct edges whose endpoints both format as empty strings remain distinct records; do not collapse those identical rendered lines.

Normally overlapping files remain on both sides. `--overlap-left` keeps intersection members only in FROM (removes them from TO). `--overlap-right` keeps them only in TO (removes them from FROM). Flags work before or after operands, and short/long forms are identical. An empty TO after overlap succeeds with empty output. An empty FROM cannot infer a language and fails with `Error: at least 1 file must be provided for inferring the language`.

An operand with no matches fails using `Error: PATTERN does not match with any existing file`. Successful no-edge output is empty stdout and status 0.

## Spec 26

Each explain edge is exactly `SOURCE -> TARGET\n`. When a project root is discovered, display paths relative to that root. If the endpoint belongs to a named workspace/package distinct from the root representation, use `PACKAGE@RELATIVE_FILE`, with the scoped-name transformation from Spec 17. The following examples define sorting, overlap, and directness for inputs beneath a discovered project root:

```text
# [ab].js -> [bc].js
a.js -> b.js
a.js -> c.js
b.js -> c.js

# the same query with --overlap-left
a.js -> c.js
b.js -> c.js

# the same query with --overlap-right
a.js -> b.js
a.js -> c.js
```

For `*.js` to `c.js`, when both A and B directly import C, output exactly:

```text
a.js -> c.js
b.js -> c.js
```

For bidirectional imports and identical `mod*.js` sets beneath a discovered project root, output both lines:

```text
modA.js -> modB.js
modB.js -> modA.js
```

If layer1 imports layer2 and layer2 imports layer3, querying layer1 to layer3 yields nothing. A cross-package line is `myorg/pkgA@index.js -> myorg/pkgB@util.js`.

If no project or workspace root can be discovered for ordinary JavaScript or Python files, the reference does not fall back to each endpoint's basename: it formats each endpoint as the empty string. A direct edge is consequently ` -> \n`; three distinct qualifying edges produce that record three times, and two bidirectional edges produce it twice. Overlap processing still selects the same underlying edges before this blank-name formatting.

## Spec 27

`check` requires a usable config. If the default is absent, fail with exactly:

```text
Error: when using the `check` subcommand, a .dep-tree.yml file must be provided, you can create one sample .dep-tree.yml file executing `dep-tree config` in your terminal
```

`check.entrypoints` may contain one or more source paths. Missing or empty entrypoints are fatal. With the default `.dep-tree.yml`, report `Error: config file "ABSOLUTE_PROJECT_DIRECTORY" has no entrypoints`: name the project/current working directory, not the `.dep-tree.yml` file. A configured entrypoint path that does not exist is fatal after graph progress has begun and reports `Error: open ABSOLUTE_MISSING_PATH: no such file or directory`. Build the union of graphs reachable from all entrypoints that remain after the check-specific filtering behavior in Spec 9.

For every direct graph edge S→T, apply every rule whose source glob matches S. An allow rule is a whitelist: T must match at least one expanded target pattern. A deny rule is a blacklist: T must not match any expanded target pattern. Apply both kinds independently; a deny can reject an edge that passes allow. Aliases in target positions expand to their pattern lists. Globstar matches arbitrary nesting. An omitted reason is allowed; when present, retain it with the violation. Collect all violations rather than stopping at the first.

Circular dependencies are violations when `allowCircularDependencies` is false or omitted. Check supports all language graphs and the same filters. A successful nonempty check exits 0 and emits normal loading progress, including a Braille spinner and `Loading Files...`; it does not print a rule error.

## Spec 28

Rule failure exits nonzero and writes this structure to stderr:

```text
Error: Check failed, the following dependencies are not allowed:
- SOURCE -> TARGET
  OPTIONAL REASON
- SOURCE2 -> TARGET2
  OPTIONAL REASON
```

There is a final newline. Preserve deterministic graph/rule order. For example:

```text
Error: Check failed, the following dependencies are not allowed:
- src/products/product.py -> src/users/user.py
  Products cannot depend on Users
- src/products/product.py -> src/orders/order.py
  Products cannot depend on Orders
```

If circular dependencies are also forbidden, add a blank line, `detected circular dependencies:`, and one `- A -> B -> ... -> A` line per cycle. A cycle-only failure retains the initial `Check failed` heading even when the ordinary violation list is empty.

## Spec 29

`entropy ENTRY...` accepts one or multiple entrypoints and produces a standalone HTML visualization. `--render-path PATH` selects the output file and fails clearly if it cannot be written. Without it, create a private temporary directory containing `index.html`. Write the HTML with mode `0600`. With `--no-browser-open`, print the resulting path as the last nonempty stdout line and exit 0. The default-command spelling behaves identically. Multiple entrypoints of the same language form one combined graph.

The HTML is UTF-8, larger than 50,000 bytes for the normal bundled visualization, begins/contains a valid `<!doctype html>`, has `<html lang="en">`, `<head>`, `<body>`, one or more scripts, `<title>Dep Tree</title>`, and a closing `</html>`. It is self-contained; no network fetch is required to inspect or render its graph.

## Spec 30

Embed machine-readable entropy data literally in a script using this searchable form, with valid compact JSON in place of `DATA`:

```text
Jt(KC,"__INLINE_DATA",DATA);
```

The top-level DATA object has `nodes`, `links`, and `enableGui`. `nodes` and `links` are arrays. Every node has:

- integer `id`, unique within the graph;
- string `fileName`, its basename;
- `pathBuf`, an array of components of its absolute path, with the filename in the last component;
- string `group`, taken from the nearest JS `package.json` package name (all files in that package share it);
- string `dirName` identifying its relative directory;
- integer `loc`, the source line count;
- integer `size`, scaled monotonically from LOC into 1–10 for nonempty nodes, with a maximum-LOC node having maximum size;
- boolean `isEntrypoint`.

With exactly one requested entrypoint, exactly that node has `isEntrypoint: true`. With multiple requested entrypoints, no node is marked as the single entrypoint. Every link has integer `from` and `to` IDs referring to existing nodes and boolean `isCyclic`. Every direct dependency becomes a link. For a single dependency-free source there is one node and zero links.

## Spec 31

`enableGui` is false by default and true with `--enable-gui`; GUI-enabled output remains valid standalone HTML. Unless `--no-browser-open` is set, attempt to launch the generated file in the platform browser. On Linux use `xdg-open`. Failure to start it is fatal after the file is generated: exit 1 and write the underlying error, including exactly `exec: "xdg-open": executable file not found in $PATH` when that program is absent. `--no-browser-open` must never attempt the launch.

## Spec 32

Path and graph operations must be deterministic and robust. Normalize separators to `/` in machine/report output. Resolve dependencies relative to their importer rather than process launch path. Follow valid file symlinks, reject broken ones as unmatched, retain valid symlinks' lexical display paths as required by Spec 8, and do not loop through symlink/self-import cycles. Handle absolute entrypoints, `.`/`..`, deep directory nesting, Unicode, whitespace, dashes, multiple dots, underscores, CRLF, UTF-8 declarations, and long filenames without mangling where the source language's dependency syntax admits them. The `.dl` PATH restriction in Spec 21 is the explicit exception for dependency names written in `.dl` source. Read source as text defensively; unsupported/binary extensions are rejected during language inference.

The analyzer must not duplicate a file because it was imported more than once or reached by multiple edges, although a nested JSON tree intentionally renders the shared node below each parent. Dependency and cycle order must be stable across repeated runs.

## Spec 33

Exit and stream conventions are part of the contract. Help/version and successful noninteractive commands exit 0. Parser/input/config/check failures exit 1. Error diagnostic text is prefixed `Error:` and written to stderr; the transient progress bytes specified in Spec 35 can precede that text on the same stderr line. Exact JSON and explain records go to stdout without contaminating diagnostics. Successful config generation is silent. Successful entropy with browser opening disabled prints its output path to stdout. Recoverable graph errors live in JSON/embedded graph handling while the command exits 0.

Interactive `tree` expects a terminal. When launched without a terminal and without `--json`, it may emit progress frames and ultimately fail to initialize the terminal with status 1; it must never hang or panic. In a real pseudo-terminal it remains active until `q`. Progress animation, when shown, uses Braille spinner characters and status labels such as `Loading Files...` and `Finished loading`; its timing/rate values are not semantically significant.

## Spec 34

These representative outputs jointly define graph nesting, filtering, sorting, and cycle behavior and should be used as conformance examples:

```json
{
  "tree": {
    "main.js": {
      "helper1.js": {"utils.js": null},
      "helper2.js": {"utils.js": null}
    }
  },
  "circularDependencies": [],
  "errors": {}
}
```

```json
{
  "tree": {
    "a.js": {
      "b.js": {"c.js": {"d.js": {"e.js": null}}}
    }
  },
  "circularDependencies": [],
  "errors": {}
}
```

```json
{
  "tree": {
    "main.js": {
      "helper1.js": {"shared.js": null},
      "helper2.js": {"shared.js": null}
    }
  },
  "circularDependencies": [],
  "errors": {}
}
```

All object/array fields shown remain present even when empty. Emitted JSON uses the exact indentation and final-newline convention in Spec 8; parsed values, path strings, ordering-visible reports, exit status, and stream placement must follow the preceding sections.

## Spec 35

Graph loading uses a transient Braille progress display on stderr for interactive tree, entropy, check, and explain work. A successful explain invocation that loads files emits this display on stderr while keeping its edge records on stdout; the display includes a Braille spinner and the `Loading Files...` and `Finished loading` phases. A successful explicit or default entropy invocation includes at least one Braille spinner character, includes the generated `index.html` path when no render path was supplied, and uses the same phases. A successful nonempty check similarly includes a spinner and `Loading Files...`.

The progress writer starts before `tree` validates that expansion produced only one entrypoint. A two-input rejection therefore writes `\r⠋  (0 it/hr) [0s] ` immediately before `Error: this functionality requires that only 1 entrypoint is provided, but 2 where passed. Consider providing a single entrypoint to your program` on stderr, then a newline; stdout is empty and status is 1. This applies equally when the two inputs belong to different language families, because the entrypoint-count rejection happens first. A nonexistent configured `check.entrypoints` path likewise writes that initial progress prefix immediately before the `Error: open ABSOLUTE_MISSING_PATH: no such file or directory` diagnostic from Spec 27; stdout is empty and status is 1.

When `tree` is run without `--json` while stdout/stderr are plain captured pipes rather than a usable terminal, it first loads the graph, then its terminal initialization may fail with `Error: exit status 1` and status 1. The progress writer redraws a line using carriage returns and space clearing. If those control updates are split into lines and rates are normalized, a one-file load has this observable sequence (blank lines arise from clearing redraws):

```text
⠋  (RATE_HR) [0s]
⠋  (RATE) [0s]


⠋ (1/1) Loading Files... (RATE) [0s]


⠋ (1/1) Finished loading (RATE) [0s]


⠋ (1/1) Finished loading (RATE) [0s]
Error: exit status 1
```

For two files, emit `(1/2) Loading Files...` twice and `(2/2) Loading Files...` once, then `(2/2) Finished loading` twice. As new dependencies are discovered, the denominator can grow (for example a five-file chain progresses `1/2`, `2/3`, `3/4`, `4/5`, `5/5`; intermediate loading states are redrawn according to the same progress-writer transition behavior). Duplicate imports do not grow it. Rate values themselves are timing-dependent; the state/count sequence is deterministic. This pipe-only failure does not alter the real-terminal TUI behavior in Specs 23–24 or any `tree --json` behavior.
