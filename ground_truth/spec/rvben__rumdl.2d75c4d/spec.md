# Executable behavioral specification

The required artifact is one executable file named `executable`. It is a command-line Markdown linter and formatter compatible with the behavior described below. All strings are UTF-8. Unless a section explicitly says otherwise, “output” means stdout, paths are interpreted relative to the process working directory, line and column numbers shown to users are one-based, and JSON/LSP positions use their format's stated conventions.

## Spec 1

### Identity, process behavior, and version

`executable` must be directly runnable on a POSIX system. It must not require repository source files or network access for ordinary linting. It must terminate promptly for non-watch, non-server commands and must not panic or print tracebacks for malformed input.

The product name is `rumdl`, its semantic version is `0.1.13`, and both `executable --version` and `executable version` print exactly `rumdl 0.1.13` followed by a newline and exit 0. `-V` is the short version flag. Version information embedded in SARIF and persistent cache entries is also `0.1.13`.

Exit status 0 means the operation succeeded (or lint findings did not meet the selected failure threshold), 1 means lint findings or an ordinary file-selection/runtime failure, and 2 means command-line/configuration usage failure and the compatibility failures explicitly classified that way below. In particular, `import` returns 2 when its input file is missing or malformed, and `completions` returns 2 when no shell can be detected; both write nothing to stdout. `fmt` is intentionally an exception: it returns 0 after formatting even when unfixable lint findings remain, unless argument/configuration/file I/O itself fails. Output must be deterministic apart from elapsed-time fields, absolute temporary path prefixes, filesystem ordering that is explicitly normalized below, and external-editor/tool output.

The executable must handle empty files, UTF-8 in every major script, combining characters and emoji without corruption. Diagnostic columns and edits must not split UTF-8. It must accept LF and CRLF input and preserve appropriate line-ending style during fixes. An initial UTF-8 BOM is not stripped for parsing: it remains leading content, so even `BOM + # Heading` receives MD041 at line 1, column 1, and `BOM + ---` does not start YAML front matter. Fixes never introduce a BOM.

An explicitly selected file whose bytes are not valid UTF-8 is skipped rather than making the check fail. The read failure is written to stderr in the form `Error reading file PATH: Failed to read file PATH: stream did not contain valid UTF-8`; for this read-error message specifically, `PATH` is the absolute filesystem path in both positions even when the operand was relative. The file is still included in the checked-file count, the ordinary clean-success body is written to stdout, and the command exits 0 if there are no findings in other files.

## Spec 2

### Top-level command grammar and exact main help

The top-level commands are `check`, `fmt`, `init`, `rule`, `explain`, `config`, `server`, `schema`, `import`, `vscode`, `completions`, `clean`, `version`, and `help`. Every command except the variadic `help` dispatcher accepts `--help`; `help COMMAND` must be byte-for-byte equivalent to `COMMAND --help` for the other commands. `help --help` treats `--help` as a requested subcommand, returns 2 with empty stdout, and writes exactly `error: unrecognized subcommand '--help'`, a blank line, `Usage: executable [OPTIONS] <COMMAND>`, another blank line, and `For more information, try '--help'.` to stderr. No arguments is a usage error (status 2) and writes the same main-help body to stderr. An unknown command is status 2 and says `unrecognized subcommand`; its stderr also contains the blank-line-separated usage line `Usage: executable [OPTIONS] <COMMAND>` before `For more information, try '--help'.`. A trailing `--help` does not rescue an unknown command: both `unknown` and `unknown --help` have this status-2 diagnostic. At top level, `--` ends option parsing, so `executable -- --help` treats `--help` as the subcommand token and exits 2 with `unrecognized subcommand '--help'`, the similar-subcommand tip for `help`, the same usage line, and the help hint. A command-only option placed before the command (for example `--verbose check`) is an unexpected argument. In particular, `executable --invalid-flag` exits 2, writes nothing to stdout, and writes exactly:

```text
error: unexpected argument '--invalid-flag' found

Usage: executable [OPTIONS] <COMMAND>

For more information, try '--help'.
```

Version takes precedence over help when both top-level flags are present: `executable --version --help` exits 0 and writes exactly `rumdl 0.1.13\n` to stdout. Text help is uncolored unless color is explicitly forced.

The following is the exact stdout for `--help` (one terminal newline):

```text
A fast Markdown linter written in Rust (Ru(st) MarkDown Linter)

Usage: executable [OPTIONS] <COMMAND>

Commands:
  check        Lint Markdown files and print warnings/errors
  fmt          Format Markdown files (alias for check --fix)
  init         Initialize a new configuration file
  rule         Show information about a rule or list all rules
  explain      Explain a rule with detailed information and examples
  config       Show configuration or query a specific key
  server       Start the Language Server Protocol server
  schema       Generate or check JSON schema for rumdl.toml
  import       Import and convert markdownlint configuration files
  vscode       Install the rumdl VS Code extension
  completions  Generate shell completion scripts
  clean        Clear the cache
  version      Show version information
  help         Print this message or the help of the given subcommand(s)

Options:
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
  -V, --version          Print version
```

Global `--color`, `--config`, `--no-config`, and `--isolated` are also accepted after relevant subcommands. Color values are `auto`, `always`, and `never`; `NO_COLOR` disables color unless explicit `--color always` takes precedence. Forced color uses ANSI escapes, while `never` guarantees none except for warning labels. The labels are always rendered as `\x1b[33m[cli warning]\x1b[0m`, `\x1b[33m[config warning]\x1b[0m`, or `\x1b[33m[inline config warning]\x1b[0m`, even with both `NO_COLOR=1` and `RUMDL_COLOR=never`, and even with explicit `--color never`. The reset escape therefore occurs between the closing `]` of the label and the following space and message.

## Spec 3

### Exact `check` interface and argument errors

`check [OPTIONS] [PATHS]...` lints files or directories. Its exact `--help` is:

```text
Lint Markdown files and print warnings/errors

Usage: executable check [OPTIONS] [PATHS]...

Arguments:
  [PATHS]...  Files or directories to lint (use '-' for stdin)

Options:
  -f, --fix
          Fix issues automatically where possible
      --diff
          Show diff of what would be fixed instead of fixing files
      --check
          Exit with code 1 if any formatting changes would be made (for CI)
  -l, --list-rules
          List all available rules
  -d, --disable <DISABLE>
          Disable specific rules (comma-separated)
  -e, --enable <ENABLE>
          Enable only specific rules (comma-separated) [aliases: --rules]
      --extend-enable <EXTEND_ENABLE>
          Extend the list of enabled rules (additive with config)
      --extend-disable <EXTEND_DISABLE>
          Extend the list of disabled rules (additive with config)
      --exclude <EXCLUDE>
          Exclude specific files or directories (comma-separated glob patterns)
      --no-exclude
          Disable all exclude patterns
      --include <INCLUDE>
          Include only specific files or directories (comma-separated glob patterns)
      --respect-gitignore[=<RESPECT_GITIGNORE>]
          Respect .gitignore files when scanning directories (does not apply to explicitly provided paths) [possible values: true, false]
  -v, --verbose
          Show detailed output
      --color <COLOR>
          Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --profile
          Show profiling information
      --config <CONFIG>
          Path to configuration file
      --statistics
          Show statistics summary of rule violations
      --no-config
          Ignore all configuration files and use built-in defaults
  -q, --quiet
          Print diagnostics, but nothing else
      --isolated
          Ignore all configuration files (alias for --no-config)
  -o, --output <OUTPUT>
          Output format: text (default) or json [default: text]
      --output-format <OUTPUT_FORMAT>
          Output format (default: text, or $RUMDL_OUTPUT_FORMAT, or output-format in config) [possible values: text, full, concise, grouped, json, json-lines, github, gitlab, pylint, azure, sarif, junit]
      --show-full-path
          Show absolute file paths in output instead of relative paths
      --flavor <FLAVOR>
          Markdown flavor: standard (default), mkdocs, mdx, quarto, or obsidian [possible values: standard, mkdocs, mdx, quarto, obsidian]
      --stdin
          Read from stdin instead of files
      --stdin-filename <STDIN_FILENAME>
          Filename to use when reading from stdin (e.g., README.md)
      --stderr
          Output diagnostics to stderr instead of stdout
  -s, --silent
          Disable all logging (but still exit with status code upon detecting diagnostics)
  -w, --watch
          Run in watch mode by re-running whenever files change
      --force-exclude
          Enforce exclude patterns even for explicitly specified files
      --no-cache
          Disable caching (re-check all files)
      --cache-dir <CACHE_DIR>
          Directory to store cache files (default: .rumdl_cache, or $RUMDL_CACHE_DIR, or cache-dir in config)
      --fail-on <FAIL_ON>
          Exit code behavior: 'any' (default) exits 1 on any violation, 'warning' on warning+error, 'error' only on errors, 'never' always exits 0 [default: any] [possible values: any, warning, error, never]
  -h, --help
          Print help
```

Unknown options say `unexpected argument`; for `check --badflag`, stderr also includes `tip: to pass '--badflag' as a value, use '-- --badflag'`. `--` stops option parsing and later dash-prefixed tokens are paths. Missing values name the placeholder, e.g. `a value is required for '--config <CONFIG>'`. Invalid enum values say `invalid value`. In particular, `check --fail-on invalid /dev/null` writes nothing to stdout, returns 2, and writes exactly the following stderr, including the indented possible-values line:

```text
error: invalid value 'invalid' for '--fail-on <FAIL_ON>'
  [possible values: any, warning, error, never]

For more information, try '--help'.
```

The other checked enum errors use the same rendering, write nothing to stdout, and return 2. In particular, `check --output-format invalid /dev/null` writes exactly:

```text
error: invalid value 'invalid' for '--output-format <OUTPUT_FORMAT>'
  [possible values: text, full, concise, grouped, json, json-lines, github, gitlab, pylint, azure, sarif, junit]

For more information, try '--help'.
```

Likewise, `check --flavor invalid /dev/null` writes exactly:

```text
error: invalid value 'invalid' for '--flavor <FLAVOR>'
  [possible values: standard, mkdocs, mdx, quarto, obsidian]

For more information, try '--help'.
```

A non-repeatable scalar such as `--output-format` used twice is status 2 with `cannot be used multiple times`. `--respect-gitignore` takes an optional value only in the `--respect-gitignore=false`/`=true` form; a separate following token is a path. Explicit `check --fix` and `check --diff` conflict with the exact phrase `--diff and --fix cannot be used together`. Formatter mode's implicit fixing does not create that conflict: `fmt --diff PATH` is valid. `--fix` and `--check`, in either argument order, exit 2, write nothing to stdout, and write exactly these two lines to stderr:

```text
Error: --check and --fix cannot be used together
Use --check to verify formatting without changes, or --fix to apply them
```

Despite its help description, `check --list-rules` does not print the rule catalog or return early. It runs the check with all rules enabled against the supplied/default paths and produces the ordinary diagnostic or success output. The separate `rule` command lists catalog entries. `--include` is non-repeatable: a second occurrence is status 2 and says `the argument '--include <INCLUDE>' cannot be used multiple times`; multiple patterns must be comma-separated in one value.

## Spec 4

### Input selection, stdin, and path presentation

With no explicit path, `check` scans the current directory. Directories are recursive. Default scanning considers `.md`, `.markdown`, `.mdown`, `.mkd`, `.mdx`, `.qmd`, and `.rmd` as Markdown where applicable; ordinary `.txt` files are excluded. An explicit file may have any extension. An explicit include pattern may opt nonstandard files such as `*.txt`, `**/*.md.jinja`, `**/*.md.tmpl`, or `**/*.md.erb` into scanning. When one invocation mixes directory operands with one or more explicit individual-file operands, the individual files take precedence and the directory operands contribute no additionally discovered files: with invalid `a.md` and `b.md` in `.`, `check ... . a.md` reports only `a.md`, regardless of operand order. Multiple explicit files are still all processed. Process each selected path only once and produce stable path-sorted results. Symlink cycles must not hang; inaccessible and nonexistent targets produce concise errors rather than crashes.

`-` or `--stdin` reads UTF-8 Markdown from standard input. A dash may be accompanied by `--stdin`; it is still read once. The default diagnostic name is `<stdin>`; `--stdin-filename NAME` changes it and supplies a virtual path for configuration/flavor resolution. In ordinary lint mode, stdin diagnostics and summaries go to stderr and stdout stays empty. `--stderr` likewise sends diagnostics to stderr. Formatter mode is different: `fmt -` and `fmt --stdin` write the fully formatted document alone to stdout and write nothing to stderr, even when fixes were applied; there are no diagnostic or summary lines. `--quiet` has the same document-only result. Clean stdin is echoed unchanged in `fmt` mode. For example, `printf '# H\ntext\n' | executable fmt --no-config -` returns 0, writes exactly `# H\n\ntext\n` to stdout, and leaves stderr empty.

Filesystem diagnostics present paths relative to the invocation/project root when that representation stays beneath the root. Thus a relative argument remains relative, and even an absolute argument naming a file inside the working/project root is displayed root-relative. An explicitly named absolute file outside that root remains absolute; it is not rewritten with `..` components. Paths discovered while scanning a relative directory are likewise relative to the invocation/project root. This rule also applies to structured formats; structured paths use `/` separators. `--show-full-path` makes relative presentations absolute. Inline-configuration warnings are an intentional exception to this path presentation rule: for filesystem input they show the absolute file path even when the checked operand was relative. In ordinary check mode, a missing explicit path returns 1 and writes a message containing either `Error: Failed to find markdown files: File not found: PATH` or the equivalent concise file-not-found form to stderr, with nothing on stdout; this routing also applies when a machine output format such as JSON was selected. Formatter mode is an intentional status exception: `fmt /nonexistent/file.md` writes exactly `Error: Failed to find markdown files: File not found: /nonexistent/file.md\n` to stderr, writes nothing to stdout, and returns 0. Selecting no matching files is not an error and prints `No markdown files found to check.` unless quiet/silent.

## Spec 5

### Include, exclude, ignore-file, and explicit-path semantics

Include and exclude values are comma-separated glob lists on the CLI and string arrays in configuration. CLI values are split on every comma before glob compilation; commas inside braces are not protected. Consequently, brace alternatives such as `{README,CHANGELOG}.md` work as one pattern in a configured string-array element, but that spelling in a CLI value is split into invalid `{README` and `CHANGELOG}.md` patterns, which produce invalid-pattern warnings on stderr; other valid comma-separated patterns in the same CLI value are still applied. A CLI include replaces the configured include; a CLI exclude is applied in addition to/with priority over configured selection. `--no-exclude` removes configured excludes. Exclude wins over include for the same path. Patterns are project-root-relative, `/`-normalized, and support `*` within one path component, `?`, `**` across directories, character classes such as `[abc]` and `[0-9]`, and brace alternatives when supplied without CLI comma splitting. Empty and whitespace-only patterns are ignored rather than matching everything. If an explicitly supplied include value contains only empty or whitespace-only comma-separated elements, its effective empty list is treated as no include filter and ordinary eligible files are scanned; it does not select zero files. Leading `/`, `.` and `..` path components are accepted and normalized without crashing; a leading slash remains root-anchored rather than being silently reinterpreted as a relative glob. A bare basename such as `README.md` matches that basename at any depth; `docs/*.md` does not cross into `docs/temp`; directory patterns such as `docs/temp` exclude the directory and descendants.

Configured include filters govern only implicit/default scans. Any explicitly supplied path bypasses the configured include, whether that operand is an individual file or a directory; files recursively discovered beneath an explicit directory are therefore not removed by the configured include. For example, with `include=["src/*.md"]`, explicit `check docs --verbose` still processes both `docs/doc1.md` and `docs/temp/temp.md`. Excludes still govern directory traversal. Explicit files matching an exclude are skipped with a warning on stderr whose prefix is the exact lowercase `warning:` and which says the path was `ignored because of exclude pattern`. Explicit paths otherwise take priority over type filtering.

`--force-exclude` is retained only as a deprecated no-op; it does not change file selection. It writes these exact three lines to stderr (and otherwise preserves the check's normal status/output):

```text
warning: --force-exclude is deprecated and has no effect
Exclude patterns are now always respected by default (as of v0.0.156)
Use --no-exclude if you want to disable exclusions
```

Directory scans respect `.gitignore` and `.ignore` at every tree level by default, including negation rules and anchored/directory patterns; explicitly named paths are not removed merely by those ignore files. Directory scans also honor `.markdownlintignore`. Thus, if a directory contains one clean Markdown file and a second invalid file named by `.markdownlintignore`, a directory check reports `Success: No issues found in 1 file`, not two files. `--respect-gitignore=false` or `respect-gitignore = false` disables `.gitignore`/`.ignore` filtering. Include/exclude behavior must be identical in normal, fix, format, cache, parallel, and watch processing. Verbose output contains `Processing file: PATH` for each actually processed file and never names a filtered file as processed.

## Spec 6

### Configuration discovery and precedence

Primary configuration is TOML. Search from the working file/project directory upward, but do not continue above the nearest directory containing `.git`. At a project level, precedence is `.rumdl.toml`, then `rumdl.toml`, then `[tool.rumdl]` in `pyproject.toml`; the first applicable project source wins, and a `pyproject.toml` with no `[tool.rumdl]` is ignored. If none exists, also discover and translate markdownlint-compatible `.markdownlint.json`, `.markdownlint.yaml`, or `.markdownlint.yml`. If no project source exists, use `$XDG_CONFIG_HOME/rumdl/rumdl.toml`, falling back to the platform user-config location. Project configuration overrides user configuration rather than merging a user rule-disable list through it. `--config PATH` selects the stated file; a missing file is status 2 with `Config error: Failed to read config file at PATH: ...`. `--config` conflicts with `--no-config`/`--isolated` and this is a status-2 argument error. For the global `--config config.toml --no-config check` form, stdout is empty and stderr is exactly:

```text
error: the argument '--config <CONFIG>' cannot be used with '--no-config'

Usage: executable --config <CONFIG> <COMMAND>

For more information, try '--help'.
```

The corresponding global `--config config.toml --isolated check` form preserves the spelling actually supplied and has the same usage stanza; stdout is empty and stderr is exactly:

```text
error: the argument '--config <CONFIG>' cannot be used with '--isolated'

Usage: executable --config <CONFIG> <COMMAND>

For more information, try '--help'.
```

`--no-config` and `--isolated` are aliases and ignore project and user files, using built-in defaults.

The value precedence from highest to lowest is CLI, environment, project/explicit config, user config, built-in default. In particular, `--output-format` overrides `RUMDL_OUTPUT_FORMAT`, which overrides `output-format` in TOML; `--cache-dir` overrides `RUMDL_CACHE_DIR`, which overrides config; explicit color overrides `NO_COLOR`/`RUMDL_COLOR`. A file-local inline directive overrides enabled state for its affected lines.

The ordinary reference-suite project profile discovered by fixture checks (unless the invocation uses `--no-config`/`--isolated`) includes `[MD046] style = "fenced"` and `[MD060] enabled = true, style = "aligned"`. Accordingly, those unisolated checks must not be modeled as raw built-in defaults: an all-indented document receives MD046 and an unaligned table receives MD060. Explicit isolated execution still exposes MD046 `consistent` and MD060 `enabled=false`, `style="any"` as described in the rule sections.

`config file` prints only the absolute path of the loaded project/config file and exits 0. With no discoverable configuration it instead writes exactly `No configuration file found (using defaults)\n` to stdout and exits 0. When configuration loading was explicitly disabled, `config file --isolated` writes exactly `No configuration file loaded (--no-config/--isolated specified)\n` to stdout and exits 0. Neither case invents a path or writes to stderr. Malformed TOML, a missing requested config, and duplicate keys are nonzero configuration errors with useful line/key context. A missing explicit `/nonexistent/path.toml` is status 2 and stderr is exactly `Config error: Failed to read config file at /nonexistent/path.toml: No such file or directory (os error 2)\n`.

Unknown configuration names are ignored for configuration purposes but emit warnings during lint configuration loading. They do not make the status nonzero, and with `/dev/null` as the only input stdout is exactly `No markdown files found to check.\n`. In the four observed cases, the warning bodies and suggestions are:

- `[global] unknown-thing=true`: `Unknown global option in unknown0.toml: unknown-thing`
- `[MD013] unknown-thing=true`: `Unknown option for rule MD013: unknown-thing`
- `[MD00X] foo=true`: `Unknown rule in unknown2.toml: MD00X (did you mean: MD001?)`
- `[global] disable=["MD999"]`: `Unknown rule in global.disable: MD999 (did you mean: MD069?)`

Each is preceded by the yellow `[config warning]` label and reset described in Spec 2 and ends with a newline. When the warning form names a file, it displays the supplied configuration filename; the examples above used `unknown0.toml` through `unknown3.toml`, and the fourth warning names `global.disable` rather than its file. An unknown `global.flavor` read from a configuration file is accepted and falls back silently to `standard`; an invalid CLI `--flavor` is still an argument error.

Configuration type errors are recoverable. A string where `global.enable` expects an array is ignored, linting continues, and the configuration itself does not make the status nonzero. The `config` display is especially permissive: `[global] line-length = "wide"` exits 0 without stderr and displays the default `line-length = 80`; `[global] enable = [1]` exits 0 without stderr and displays an empty project-provided enable list; and `[MD013] line-length = -1` exits 0 without stderr and displays `line-length = -1` from project config. The exact unknown-name cases above are ignored after emitting their lint-time warnings. An invalid typed rule option encountered during linting emits a yellow `[config warning] Type mismatch for RULE.OPTION: expected EXPECTED, got ACTUAL`, emits an `Invalid configuration for rule RULE` warning, and uses that rule's defaults; it does not itself make the status nonzero. For example, `[MD013] line-length = "not a number"` says `Type mismatch for MD013.line-length: expected integer, got string` and falls back to MD013 defaults, while `[MD003] style = true` says `Type mismatch for MD003.style: expected string, got boolean` and falls back to MD003 defaults. For `[MD044] code-blocks = [1, 2]`, stderr is the yellow `[config warning] Type mismatch for MD044.code-blocks: expected boolean, got array`, followed in order by `Warning: Invalid configuration for rule MD044: invalid type: sequence, expected a boolean`, ``in `code-blocks` ``, a blank line, `Using default values for rule MD044.`, and `Hint: Check the documentation for valid configuration values.`; with `/dev/null` as the only input, stdout then says `No markdown files found to check.` and status is 0.

A floating-point value is not coerced to an integer. With forced color, `[MD013] line-length = 80.5` first emits the yellow label and exact body `[config warning] Type mismatch for MD013.line-length: expected integer, got float`. It then emits this rule-validation block twice, in order, before the ordinary lint result:

```text
Warning: Invalid configuration for rule MD013: invalid type: floating point `80.5`, expected usize
in `line-length`

Using default values for rule MD013.
Hint: Check the documentation for valid configuration values.
```

The mismatch does not make the status nonzero, and MD013 runs with its defaults.

For malformed TOML, the status is 2 and stderr preserves the parser's multiline location/context. For a file whose first and only line is `[global`, the diagnostic has this form (an explicitly supplied path is displayed according to the command's path presentation):

```text
Config error: Failed to parse config: invalid_toml.toml: Failed to parse TOML: TOML parse error at line 1, column 8
  |
1 | [global
  |        ^
unclosed table, expected `]`

```

Duplicate TOML keys use the same parser diagnostic rather than a shortened one-line error. For this input:

```toml
[global]
enable = ["MD001"]
enable = ["MD002"]
```

stderr is, with the actual config path substituted for `PATH`:

```text
Config error: Failed to parse config: PATH: Failed to parse TOML: TOML parse error at line 3, column 1
  |
3 | enable = ["MD002"]
  | ^^^^^^
duplicate key

```

## Spec 7

### Configuration data model and merge rules

Global keys in a normal `.rumdl.toml` belong under `[global]`; under `pyproject.toml` they appear below `[tool.rumdl]`. A bare root-level declaration such as `exclude = ["docs/*"]` is not a global exclude: it is ignored with `[config warning] Unknown rule in .rumdl.toml: exclude`. Consequently, a CLI `--include docs/doc1.md` still selects that file in such a malformed configuration. Kebab-case and snake_case option spellings are equivalent on input. Most queried/canonical option names use kebab-case, but the human `config --defaults` display spells the global key exactly `respect_gitignore`. The global settings and defaults are:

| Key | Type | Default |
| --- | --- | --- |
| `enable`, `disable`, `exclude`, `include` | string arrays | `[]` |
| `respect-gitignore` | boolean | `true` |
| `line-length` | integer | `80` |
| `flavor` | string | `standard` |
| `output-format` | enum | `text` |
| `cache` | boolean | `true` |
| `cache-dir` | path | `.rumdl_cache` |
| `fixable`, `unfixable` | string arrays | `[]` |

The legacy `[global] force-exclude` configuration key is accepted silently for compatibility, including an array value such as `["ignored.md"]`, but has no file-selection effect. This mirrors the deprecated no-op CLI spelling rather than producing an unknown-option or type error.

An empty `enable` means all default-enabled rules, not no rules. A nonempty enable is an allow-list; disable is then subtracted. CLI `--enable` replaces configured enable; `--disable` replaces/sets disabled rules; `--extend-enable` and `--extend-disable` add to the configured sets. Rule names and aliases are case-insensitive, and a hyphenated canonical name also accepts its underscore spelling: for example, `--enable heading_increment` enables MD001. `all` is accepted where rule lists allow all rules. `fixable`, when nonempty, limits automatic fixes to the named rules; `unfixable` prevents the named rule's own fix and takes precedence. It does not protect the same bytes from an overlapping fix belonging to another rule. In the exact `# H1\n\n### H3   \n` example with both rules fixable but `unfixable=["MD009"]`, MD001's whole-heading rewrite changes `### H3   ` to `## H3` and thereby removes the trailing spaces too. The original MD001 line ends `[fixed]`, the original MD009 line is printed without `[fixed]`, the resulting file is `# H1\n\n## H3\n`, and the command exits 0 with the ordinary `Success: No issues found in 1 file (Tms)` summary. A rule table `[MDxxx]` may contain `severity = "error"|"warning"|"info"` and that rule's typed options. `enabled` is not common rule-table metadata: for example, `[MD013] enabled = true` emits the warning `Unknown option for rule MD013: enabled`, while other valid MD013 settings are still applied. Rule-specific line length overrides global line length.

Per-file maps are root-level sibling tables, `[per-file-ignores]` and `[per-file-flavor]`; they are not members nested beneath `[global]`. Therefore `[global.per-file-ignores]` is ignored with `[config warning] Unknown global option in .rumdl.toml: per-file-ignores`, and its entries suppress no findings. In a correctly placed `[per-file-ignores]` table, all matching rule arrays are unioned with global disables. Per-file flavor entries preserve declaration order and the first matching pattern wins; an explicit match overrides both filename-extension inference and the global flavor.

Unknown names in a CLI `--enable` or `--disable` list are warned about and ignored rather than making the command fail or discarding valid neighbors. The warning is a yellow `[cli warning]` line on stderr. For example, `check --enable MD99` writes `[cli warning] Unknown rule in --enable: MD99 (did you mean: MD069?)`, continues checking, and can exit 0; `check --enable MD001,invalid-rule,MD013` writes `[cli warning] Unknown rule in --enable: invalid-rule` and retains MD001 and MD013. Likewise, `check --profile --disable MD001,MD002,MD003 FILE`, where `MD002` is unassigned, writes `[cli warning] Unknown rule in --disable: MD002 (did you mean: MD042?)` to stderr, ignores that one name, processes the file with MD001 and MD003 disabled, prints the normal output followed by `Profiling is disabled.`, and returns 0 when there are no remaining findings.

Empty files/tables/arrays are valid and use defaults. TOML nested arrays/maps, quoted strings, comments, booleans and integers must be parsed normally. When validation emits a diagnostic, it distinguishes wrong scalar type, invalid array element type, invalid range, and unknown key. The permissive `config`-display cases and recoverable lint-time rule-option mismatches are the explicit exceptions in Spec 6. The rule option defaults and accepted values are given with each rule below.

## Spec 8

### Inline configuration comments

Recognize directives in HTML comments with either `rumdl-` or markdownlint-compatible `markdownlint-` prefixes. Directives inside fenced/indented code are literal and do not affect linting. Unknown/malformed directives do not crash. Any unknown rule named by an inline enable or disable comment emits a yellow stderr warning whose uncolored body is `[inline config warning] PATH:LINE: Unknown rule in inline ACTION comment: RULE`, then continues linting. For filesystem input, `PATH` is absolute even when the command-line operand was relative; stdin uses `<stdin>`. This applies equally to `rumdl-*` and `markdownlint-*`. The raw yellow label and reset remain present when color is disabled as specified in Spec 2. A close rule typo appends ` (did you mean: MDxxx?)`; for example `<!-- rumdl-disable MD00 -->` produces `Unknown rule in inline disable comment: MD00 (did you mean: MD050?)`.

- `<!-- rumdl-disable -->` disables all rules until enabled; `<!-- rumdl-disable MD013 MD033 -->` disables those rules. Commas or whitespace may separate IDs.
- `<!-- rumdl-enable -->` restores all rules; with IDs, it re-enables those rules within the current scope, even if command/config enable state had disabled them where explicit inline enabling is supported.
- `disable-line` suppresses named/all rules only on its own line; `disable-next-line` only on the following physical line. `<!-- prettier-ignore -->` suppresses all rules on the following line.
- `disable-file` suppresses named/all rules for the entire document regardless of placement. `enable-file` enables named/all rules for the file.
- `capture` pushes the current enabled state and `restore` pops it. Nested capture/restore and nested disable/enable regions behave as a stack; unmatched restores are harmless.
- `configure-file` is followed by a JSON object of rule configurations, for example `<!-- rumdl-configure-file { "MD013": { "line_length": 120 } } -->`; validate and apply it for the whole file.

Directive lines themselves are skipped by rules for which comments are excluded. Multiple directives, disable-all followed by enabling one rule, end-of-file directives, CRLF, and adjacent code fences must retain correct line numbering.

## Spec 9

### Lint execution, severity, and failure thresholds

Run every enabled rule against the same parsed document and report all distinct findings, including multiple findings on one line. A syntactic construct represented by paired tokens can still be one finding: in particular, MD033 emits one finding for an opening/closing HTML element pair rather than a second finding for its closing tag. Some shared-boundary interactions are deliberately consolidated. When a closed YAML block's closing `---` is followed immediately by a heading, report only MD071 `Missing blank line after frontmatter` at the closing delimiter, not an additional MD022 finding for that same missing separator. Likewise, when a fenced code block is followed immediately by a list, MD031 reports `No blank line after fenced code block` and MD032 does not also report `List should be preceded by blank line` for that separator; an independently missing blank after the list is still an MD032 finding. Sort findings by file, then byte/character location, with deterministic rule ordering for ties. Unless overridden, these rules have error severity because they describe broken structure/functionality: MD001, MD011, MD024, MD025, MD042, MD045, MD051, MD057, MD066, MD068. Other rules default to warning. A `[MDxxx] severity` setting changes displayed severity, machine-format severity mapping, LSP severity, and failure behavior.

`--fail-on any` (default) returns 1 for info/warning/error findings; `warning` for warning or error; `error` only for errors; `never` always returns 0 while still reporting diagnostics. File/config/runtime errors remain failures. After `--fix`, relint the resulting content: return 0 if no threshold-reaching issue remains and 1 if an unfixable or unfixed one remains. `--check` is dry-run CI mode: do not modify files and return 1 if any automatic formatting change would be made. Empty and fully valid documents return 0 without diagnostics.

Rules can yield a replacement range. The public rule catalog labels every rule except MD033, MD054, and MD059 as fixable (64 of 67); those three must not be offered by `--fixable`. At runtime, a particular finding is marked fixable only when it has a safe concrete replacement. MD033 must not rewrite general HTML; MD054 and MD059 require author judgment.

## Spec 10

### Default text, quiet, silent, verbose, statistics, and profiling output

Default diagnostics use:

```text
PATH:LINE:COLUMN: [MDxxx] MESSAGE [*]
```

`[*]` means a concrete fix exists; an unfixable finding has no marker. In fix mode the original finding line ends `[fixed]` when applied. After findings, print a blank line and a summary. If all checked files have findings it is `Issues: Found N issues in M file/files (Tms)`; if only K of M checked files have findings it is `Issues: Found N issues in K/M files (Tms)`. The word `issues` is used even when N is 1, while `file` is singular only when exactly one file was checked. If any findings are fixable, follow the summary with `Run `rumdl fmt` to automatically fix F of the N issues`. Clean ordinary-check stdout begins with one blank line: the exact body is `\nSuccess: No issues found in M file/files (Tms)\n`; timing may vary. Ordinary dash/stdin checking instead uses the timing-free summary `Found N issue(s) in <stdin>` (or the supplied stdin filename), written to stderr after one blank line. It does not use the filesystem summary form or print the automatic-fix suggestion. Thus checking `# Test   \n\nTest   ` ends exactly `Found 3 issue(s) in <stdin>\n`.

`--quiet` retains diagnostic lines but suppresses progress, success, summary, suggestion, statistics, and profiling. `--silent` emits nothing at all, while preserving status and file changes. `--verbose` begins with `Enabled rules:` and one `  - MDxxx (summary)` line in numeric catalog order. Every processed file gets a `Processing file: PATH` line even on a cache hit; a hit additionally gets `Cache hit for ABSOLUTE_PATH` rather than replacing the processing line. On the built-in default configuration this list contains all 67 catalog rules, including MD060, MD063, MD072, and MD073 even when a rule's own settings leave its checks inert until activated.

`--statistics` appends a table only when findings exist:

```text
Rule Violation Statistics:
Rule     Violations   Fixable  Percentage
--------------------------------------------------
MDxxx    COUNT        FIXES      PERCENT%
...
--------------------------------------------------
Total    TOTAL        FIXES     100.0%
```

The columns are byte-aligned exactly. In particular, a one-finding, one-fix row is `MD009    1            1         100.0%`, and the corresponding total is `Total    1            1         100.0%`; both have nine spaces between the last `1` and `100.0%`. Rows aggregate all files, percentages are one decimal of total findings, `-` represents no fixes, and rows are ordered by descending count with deterministic tie ordering. Silent suppresses it. Profiling is not compiled into this executable. For a check that processes a file, `--profile` appends a blank line and exactly `Profiling is disabled.\n` to stdout after the ordinary output; it emits no phase/rule timings and writes no profiling text to stderr. For example, a clean one-file check ends its ordinary success line, then writes `\nProfiling is disabled.\n`. This same clean text body and disabled-profiling suffix are produced when the explicit output format is `text`, `full`, `concise`, `grouped`, `json-lines`, or `github`; the latter machine/CI selections do not suppress or structurally encode the profiling message. `--color always` colors the ordinary success label but leaves `Profiling is disabled.` uncolored, while `--color never` leaves the whole output uncolored. `--show-full-path` does not alter this path-free clean message. The option otherwise preserves enabled-rule/file filtering and combines with fix, diff, configuration, flavor, no-cache processing, multiple files, and multiple directories. Large inputs and empty selections remain well-formed.

## Spec 11

### Machine-readable and CI output formats

`-o json` is an alias for JSON output. `--output-format` accepts `text`, `full`, `concise`, `grouped`, `json`, `json-lines` (and rule-command alias `jsonl`), `github`, `gitlab`, `pylint`, `azure`, `sarif`, and `junit`.

JSON lint output is one pretty-printed array, using two-space indentation and a terminal newline. Findings retain the normal file/location sort. Each finding object emits keys in this exact order: `file`, `line`, `column`, `rule`, `message`, `severity`, `fixable`, `fix`. For a nonfixable finding, `fix` is JSON `null`; for a fixable finding it is an object with `range` followed by `replacement`, and `range` contains `start` followed by `end`. `start` and `end` are zero-based byte offsets into the original UTF-8 document and form a half-open range: `start` is included and `end` is excluded. A pure insertion has equal offsets, a deletion has an empty `replacement`, and a replacement carries the exact complete corrected source span rather than only its first marker character. For example, in `# H1\n\n### H3\n`, the MD001 fix is `{"range":{"start":6,"end":12},"replacement":"## H3"}`: it replaces the complete `### H3`, not only its hash run. Ranges must fall on UTF-8 boundaries. JSON-lines emits one compact object per line with keys in the same order through `fixable` but without `fix`; there are no spaces outside string values. Its diagnostic object lines are followed by a blank line and the normal `Issues:` summary and fix suggestion. No diagnostic objects means `[]\n` for JSON and no object lines for JSON-lines.

`full` includes rich source/context and rule data. In ordinary check mode, `concise` emits one diagnostic per line in the exact `PATH:LINE:COLUMN: [MDxxx] MESSAGE` shape, using the rule's complete canonical diagnostic rather than its catalog summary and omitting `[*]` even for a fixable finding. After the lines it still emits the ordinary blank line, `Issues:` summary, and automatic-fix suggestion when applicable. `grouped` groups first by file and then by rule: the file heading is exactly `PATH:` (including the colon and the path spelling required by Spec 4), each rule heading is indented two spaces as `MDxxx:`, and its `LINE:COLUMN MESSAGE` entries are indented four spaces. A fixable grouped entry ends in `(fixable)`. GitHub format is `::error|warning|notice file=PATH,line=L,col=C,endLine=EL,endColumn=EC,title=MDxxx::MESSAGE`, escaping command characters. Its end column is the one-based exclusive end of the complete offending span: for `### Skipped H2` at line 3, MD001 uses `col=1,endLine=3,endColumn=15`. GitHub output then includes a blank line, the ordinary `Issues:` summary, and the automatic-fix suggestion when applicable. GitLab is a JSON array of Code Quality objects with `description`, `check_name`, stable fingerprint `PATH-L-C-MDxxx`, severity exactly `minor` for every finding regardless of rumdl severity, and `location.path/lines.begin`; it has no console summary. Pylint begins with `PATH:L:C: [CMDxxx] MESSAGE` lines and forwards each rule's canonical diagnostic message verbatim; it does not substitute a shorter rule summary. Like GitHub, it appends a blank line, the ordinary summary, and any automatic-fix suggestion. Azure uses `##vso[task.logissue type=...;sourcepath=...;linenumber=...;columnnumber=...;code=MDxxx]MESSAGE` with escaping; there is no semicolon between the rule code and the closing `]`.

SARIF is valid, two-space-indented SARIF 2.1.0 with a terminal newline. Its top-level keys are `$schema`, `version`, then `runs`; `$schema` equals `https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json`, `version` is `"2.1.0"`, and there is one run. The driver has `name: "rumdl"`, `version: "0.1.13"`, `informationUri: "https://github.com/rvben/rumdl"`, and `rules`. Each rule metadata entry has `id` and `name` both equal to `MDxxx`, `shortDescription.text` equal to `Markdown rule MDxxx`, and `fullDescription.text` equal to `Markdown linting rule MDxxx`. The rules array contains exactly one entry for each distinct result rule and none for an enabled rule with no result; repeated findings share one entry. Across repeated executions of the same multi-rule invocation, the reference produced different rules-array orders, so consumers and tests must treat that metadata array as an unordered set. The `results` array retains normal finding order and each object contains, in order, `ruleId`, mapped `level`, `message.text`, and one `locations` entry whose `physicalLocation` has `artifactLocation.uri` followed by one-based `region.startLine` and `startColumn`.

JUnit is two-space-indented XML beginning `<?xml version="1.0" encoding="UTF-8"?>\n` and ending with `</testsuites>\n\n`. Its root start tag has attributes in this order: `<testsuites name="rumdl" tests="FILES_WITH_FINDINGS" failures="FINDINGS" errors="0" time="SECONDS">`. Its `tests` count is the number of files with findings, not the number of findings or all checked files. Files are emitted in normal path order. Each file with findings is represented exactly by this nesting (with elapsed-time fields substituted):

```xml
  <testsuite name="PATH" tests="1" failures="FILE_FINDINGS" errors="0" time="SECONDS">
    <testcase name="Lint PATH" classname="rumdl" time="SECONDS">
      <failure type="MDxxx" message="MESSAGE">MESSAGE at line LINE, column COLUMN</failure>
    </testcase>
  </testsuite>
```

Every additional finding for that file is another sibling `<failure>` inside the single testcase. Clean files are omitted, so an all-clean run has `tests="0"` and no per-file suites. The root and per-file `failures` counts are finding counts. The canonical message is XML-escaped independently in the failure's `message` attribute and text body; for example, the MD042 message containing `<brackets>`, `&`, and `"quotes"` becomes `&lt;brackets&gt;`, `&amp;`, and `&quot;quotes&quot;`. Machine structures must remain valid for multiple findings/files, Unicode and no findings.

## Spec 12

### Fix, diff, and formatter behavior

`check --fix` applies all safe nonoverlapping fixes, resolving overlapping replacements deterministically and iterating/re-linting until stable. It writes files atomically, preserves permissions, does not rewrite unchanged files, and is idempotent: a second fix makes no further change. It reports each applied original finding as `[fixed]`, reports remaining findings normally, and bases status on remaining findings. Fixes in one file must not offset positions in another.

`check --fix` uses the ordinary post-fix check summary, not the formatter summary. When all findings are eliminated it exits 0 and ends with `Success: No issues found in N file/files (Tms)`, even though the preceding original diagnostic lines end in `[fixed]`. For the file `# H1\n\n### H3   \n` checked with only MD001 and MD009, the two diagnostic lines end `[fixed]`, a blank line follows, and the final line is `Success: No issues found in 1 file (Tms)`. The `Fixed: Fixed A/B ...` summary below belongs to `fmt`, not `check --fix`.

`check --diff` computes the same fixed result without writing. For each changed file it prints a unified diff with headers `--- PATH` and `+++ PATH (fixed)`, context hunks, `-` old lines and `+` new lines. The diff replaces the individual diagnostic lines; two empty lines (three newline characters after the final diff content) separate it from the ordinary `Issues:` summary and fix suggestion. For example, fixing the only violation in a five-line file containing `# Title`, a blank, `### Skipped H2`, a blank, and `Content` produces this layout before the timing-dependent summary:

```diff
--- PATH
+++ PATH (fixed)
@@ -1,5 +1,5 @@
 # Title
 
-### Skipped H2
+## Skipped H2
 
 Content


```

The line-oriented diff renderer has a trailing-empty-line special case. For a file whose exact bytes are `# Title\n\n\n\n`, `check PATH --diff` finds the MD012 issue but renders:

```text
--- PATH
+++ PATH (fixed)
No changes
```

Those three lines are followed by two empty lines, the normal `Issues: Found 1 issues in 1 file (Tms)` summary, and the automatic-fix suggestion. It returns 1 and does not modify the file. The literal `No changes` is required here even though the lint result has a fixable finding.

Stdin diff likewise does not mutate anything. `--check` neither writes nor emits a diff unless otherwise selected; it merely tests whether formatting differs.

`fmt PATHS...` is `check --fix` in formatter mode. For files it writes changes and prints per-file fixes. When at least one file changes, the final formatter line is `Fixed: Fixed A/B issues in N file/files (Tms)`, where A is the number applied, B includes remaining unfixable issues, and N counts only files actually changed. If no file changes, including a run containing only unfixable MD033 findings, omit the `Fixed:` line entirely and retain the ordinary remaining-issues summary. A clean unchanged file therefore produces the normal leading blank line and `Success: No issues found in 1 file (Tms)`, never `Fixed: 0 files`. It returns 0 even if unfixable findings remain. `fmt --diff PATH` is its dry-run diff form: return 0, do not modify the file, print the same unified diff headers and hunks as `check --diff`, and finish with `Fixed: Fixed A/B issues in N file/files (Tms)` rather than treating the implicit formatter fix as a `--fix`/`--diff` argument conflict. For stdin (`fmt -` or `fmt --stdin`), stdout must be exactly the formatted document, with no status text. Typical required transformations include `#Title\n` to `# Title\n`, `# H\ntext\n` to `# H\n\ntext\n`, removing trailing spaces, normalizing excess blank lines, tabs and list indentation, and ensuring exactly one final newline. Formatting must preserve Unicode, front matter, code literals, hard breaks configured to remain, and Markdown syntax not targeted by a fix.

## Spec 13

### `init`, `config`, and schema operations

The exact `init --help` stdout is:

```text
Initialize a new configuration file

Usage: executable init [OPTIONS]

Options:
      --pyproject        Generate configuration for pyproject.toml instead of .rumdl.toml
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

`init` creates `.rumdl.toml` in the current directory by default. On success stdout is exactly:

```text
Created default configuration file: .rumdl.toml

Setup complete! You can now:
  • Run rumdl check . to lint your Markdown files
  • Open your editor to see real-time linting
```

The created file is UTF-8 and has exactly the following content, including comments, indentation, blank lines, and final newline:

```toml
# rumdl configuration file

# Global configuration options
[global]
# List of rules to disable (uncomment and modify as needed)
# disable = ["MD013", "MD033"]

# List of rules to enable exclusively (if provided, only these rules will run)
# enable = ["MD001", "MD003", "MD004"]

# List of file/directory patterns to include for linting (if provided, only these will be linted)
# include = [
#    "docs/*.md",
#    "src/**/*.md",
#    "README.md"
# ]

# List of file/directory patterns to exclude from linting
exclude = [
    # Common directories to exclude
    ".git",
    ".github",
    "node_modules",
    "vendor",
    "dist",
    "build",

    # Specific files or patterns
    "CHANGELOG.md",
    "LICENSE.md",
]

# Respect .gitignore files when scanning directories (default: true)
respect-gitignore = true

# Markdown flavor/dialect (uncomment to enable)
# Options: standard (default), gfm, commonmark, mkdocs, mdx, quarto
# flavor = "mkdocs"

# Rule-specific configurations (uncomment and modify as needed)

# [MD003]
# style = "atx"  # Heading style (atx, atx_closed, setext)

# [MD004]
# style = "asterisk"  # Unordered list style (asterisk, plus, dash, consistent)

# [MD007]
# indent = 4  # Unordered list indentation

# [MD013]
# line-length = 100  # Line length
# code-blocks = false  # Exclude code blocks from line length check
# tables = false  # Exclude tables from line length check
# headings = true  # Include headings in line length check

# [MD044]
# names = ["rumdl", "Markdown", "GitHub"]  # Proper names that should be capitalized correctly
# code-blocks = false  # Check code blocks for proper names (default: false, skips code blocks)
```

A second default initialization returns status 2, writes nothing, preserves the existing file byte-for-byte, and writes exactly `Error: Failed to create config file: Configuration file already exists at .rumdl.toml` followed by a newline to stderr.

`init --pyproject` creates a new `pyproject.toml`, prints exactly `Created pyproject.toml with rumdl configuration` and a newline, and writes exactly this content:

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"


[tool.rumdl]
# Global configuration options
line-length = 100
disable = []
exclude = [
    # Common directories to exclude
    ".git",
    ".github",
    "node_modules",
    "vendor",
    "dist",
    "build",
]
respect-gitignore = true

# Rule-specific configurations (uncomment and modify as needed)

# [tool.rumdl.MD003]
# style = "atx"  # Heading style (atx, atx_closed, setext)

# [tool.rumdl.MD004]
# style = "asterisk"  # Unordered list style (asterisk, plus, dash, consistent)

# [tool.rumdl.MD007]
# indent = 4  # Unordered list indentation

# [tool.rumdl.MD013]
# line-length = 100  # Line length
# code-blocks = false  # Exclude code blocks from line length check
# tables = false  # Exclude tables from line length check
# headings = true  # Include headings in line length check

# [tool.rumdl.MD044]
# names = ["rumdl", "Markdown", "GitHub"]  # Proper names that should be capitalized correctly
# code-blocks = false  # Check code blocks for proper names (default: false, skips code blocks)
```

If `pyproject.toml` already exists, prompt exactly `pyproject.toml already exists. Would you like to append rumdl configuration? [y/N]` followed by a newline. Only the exact lowercase response `y` affirms: it appends the rumdl section without damaging existing TOML and then prints `> Added rumdl configuration to pyproject.toml`. The longer response `yes` is not affirmative; like every other response it leaves the file unchanged and prints `> Aborted. No changes made to pyproject.toml`. When the existing file ends in its ordinary single newline, successful append places two empty lines between its last existing line and `[tool.rumdl]` (three consecutive newline bytes before the section header), matching the new-file layout above. If the file already has `[tool.rumdl]`, an affirmative response still receives the append prompt first; the program then leaves the file unchanged and prints, in order, `> The pyproject.toml file already contains a [tool.rumdl] section.` and `Please edit the file manually to avoid overwriting existing configuration.` on their own lines.

`config` prints the effective configuration starting with `[global]`. Human output annotates each value with provenance such as `[from default]` or `[from project config]`. Before adding provenance, find the longest rendered assignment in the complete output; right-pad every assignment and section header with spaces to that width. Append one space and the provenance to assignment lines, leave the padding on section headers, put one empty line between sections, and end the complete display with an empty line (two newline bytes). Human output uses the exact snake-case global spelling `respect_gitignore`. A `config get` response preserves the spelling used in the query rather than forcing one canonical spelling: after `init`, `config get global.respect-gitignore` prints `global.respect-gitignore = true [from project config]\n`, while `config get global.respect_gitignore` prints `global.respect_gitignore = true [from project config]\n`. `--defaults` prints built-in defaults only, not merely the global table: after `[global]` and its default values (including `respect_gitignore = true` and `flavor = Standard` before provenance/padding), it prints rule tables such as `[MD001]` and each rule's built-in options. `--no-defaults` omits default-valued entries.

The exact stdout of `config --help` is:

```text
Show configuration or query a specific key

Usage: executable config [OPTIONS] [COMMAND]

Commands:
  get   Query a specific config key (e.g. global.exclude or MD013.line_length)
  file  Show the absolute path of the configuration file that was loaded
  help  Print this message or the help of the given subcommand(s)

Options:
      --defaults         Show only the default configuration values
      --no-defaults      Show only non-default configuration values (exclude defaults)
      --output <OUTPUT>  Output format (e.g. toml, json)
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

`--output toml` is deterministic parseable TOML without annotations. It uses canonical kebab-case keys, renders empty arrays inline as `[]`, renders each nonempty array with `[` and `]` on their own lines and one four-space-indented quoted item plus a trailing comma per line, represents empty maps as empty table headers rather than `{ }`, leaves one empty line after every table including the last, and preserves the stable global/subtable/rule order. For example, the human `respect_gitignore = true` is `respect-gitignore = true` in TOML, and the configuration maps appear as `[per-file-ignores]`, `[per-file-flavor]`, `[code-block-tools.languages]`, `[code-block-tools.language-aliases]`, and `[code-block-tools.tools]`. JSON output is valid JSON. Supplying both `--defaults` and `--no-defaults` writes nothing to stdout, returns 2, and writes exactly `Error: Cannot use both --defaults and --no-defaults flags together\n` to stderr. `config get global.exclude` prints the queried key/value and provenance, e.g. `global.exclude = ["docs/temp", "node_modules"] [from project config]`; recognized underscores and hyphens are accepted and retained in the displayed key. An unknown global member is status 2 and stderr is `Unknown global key: NAME\n`; for example, `config get global.unknown` prints `Unknown global key: unknown`. Any other unknown dotted query is status 2 and is echoed byte-for-byte after `Unknown config key: ` rather than uppercasing its namespace or rejecting its shape. In particular, `config get nonexistent.key` writes nothing to stdout and writes exactly `Unknown config key: nonexistent.key\n` to stderr. An unknown `MDxxx` member follows the same echo rule.

`schema` has nested `print`, `generate`, and `check` commands. With no nested command it exits 2, writes nothing to stdout, and writes the nested schema help body to stderr (beginning `Generate or check JSON schema for rumdl.toml`, followed by `Usage: executable schema [OPTIONS] <COMMAND>` and the `generate`, `check`, `print`, and `help` rows). `schema print` emits the deterministic pretty JSON Schema stored byte-for-byte in the companion file `schema-print.json`, including that file's one terminal newline. This complete artifact, rather than a reduced set of invariants, is the schema contract. Its top level has keys `$schema`, `title`, `description`, `type`, `properties`, `additionalProperties`, and `$defs` in that order. The exact description is `rumdl configuration for linting Markdown files. Rules can be configured individually using [MD###] sections with rule-specific options.` The four top-level properties are `global`, `per-file-ignores`, `per-file-flavor`, and `code-block-tools`; `global` references `#/$defs/GlobalConfig` and `code-block-tools` references `#/$defs/CodeBlockToolsConfig`, each with the defaults shown in the companion artifact. `$defs` contains exactly `CodeBlockToolsConfig`, `GlobalConfig`, `LanguageToolConfig`, `LineLength`, `MarkdownFlavor`, `NormalizeLanguage`, `OnError`, `OnMissing`, `RuleConfig`, `Severity`, and `ToolDefinition`. It does not enumerate named rule definitions such as `MD001` or `MD073`; top-level additional properties instead reference `#/$defs/RuleConfig`. The Markdown flavor enum contains `standard`, `gfm`, `github`, `commonmark`, `mkdocs`, `mdx`, `quarto`, `qmd`, `rmd`, `rmarkdown`, and `obsidian`.

`schema generate` takes no path operand. It writes the exact bytes of `schema-print.json` without a terminal newline to `rumdl.schema.json` in the working directory. (`schema print` adds the one stdout newline; the generated file does not.) A supplied operand is a status-2 argument error with empty stdout and stderr beginning `error: unexpected argument 'PATH' found`, followed by the blank-line-separated usage `Usage: executable schema generate [OPTIONS]` and the normal help hint. Schema messages show the absolute default path. Creating or replacing a missing/outdated default file exits 0 and writes exactly `Schema updated: ABSOLUTE_PATH/rumdl.schema.json\n` to stdout. Generating again when its bytes already match exits 0 and writes exactly `Schema is already up-to-date: ABSOLUTE_PATH/rumdl.schema.json\n`; it leaves the file's bytes and modification time unchanged.

`schema check` likewise takes no path operand and checks only `rumdl.schema.json` in the working directory. A supplied operand is a status-2 argument error with empty stdout and stderr beginning `error: unexpected argument 'PATH' found`, followed by `Usage: executable schema check [OPTIONS]` and the normal help hint. For the current default file it writes exactly `Schema is up-to-date: ABSOLUTE_PATH/rumdl.schema.json\n` to stdout. A missing default file exits 2, writes nothing to stdout, and writes exactly these two lines to stderr:

```text
Error: Schema file not found: ABSOLUTE_PATH/rumdl.schema.json
Run 'rumdl schema generate' to create it.
```

An outdated file likewise exits 2 with empty stdout and exactly:

```text
Error: Schema is out of date: ABSOLUTE_PATH/rumdl.schema.json
Run 'rumdl schema generate' to update it.
```

A malformed file follows the same non-current failure contract rather than succeeding.

`schema --help` exits 0 and includes `Usage: executable schema [OPTIONS] <COMMAND>`, the four command rows `generate`, `check`, `print`, and `help`, and an `Options:` section containing the global color/config switches and `-h, --help`. Nested help is recognized as an option; it never creates or checks a file literally named `--help`. The exact nested help bodies are:

```text
Print the schema to stdout

Usage: executable schema print [OPTIONS]

Options:
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

```text
Generate/update the JSON schema file

Usage: executable schema generate [OPTIONS]

Options:
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

```text
Check if the schema is up-to-date

Usage: executable schema check [OPTIONS]

Options:
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

## Spec 14

### Import and completion commands

`import FILE [-o|--output OUTPUT] [--dry-run] [--format toml|json]` converts markdownlint configuration from JSON, JSONC, YAML, or CommonJS-like supported syntax. The displayed positional placeholder is exactly `<FILE>`, not `<INPUT>`. It recognizes boolean rule enable/disable, aliases, integer shorthand (notably MD013 line length), arrays and nested option objects; converts option names to canonical kebab-case; maps top-level `default`, enabled/disabled rules, and supported markdownlint names to `[global]` and `[MDxxx]`; maps markdownlint MD013 option `stern` to rumdl `strict`; and warns about unsupported/unknown rules/options instead of inventing behavior. A non-object scalar rule value is retained under the rule's literal `value` key: importing `{"MD001":"error"}` as TOML produces exactly `[MD001]\nvalue = "error"\n\n\n`. `default=true` plus false rules becomes a disable list; `default=false` plus enabled/configured rules becomes an enable list. `--dry-run` prints the converted document and writes nothing. Every nonempty TOML dry-run serialization ends with an empty line plus one additional terminal newline, i.e. exactly three consecutive newline bytes after its final assignment. For example, importing `{"default": true, "MD013": false, "MD033": {"allowed_elements": ["br", "img"]}}` produces exactly the byte string `[global]\ndisable = ["MD013"]\n\n[MD033]\nallowed-elements = ["br", "img"]\n\n\n`. An input containing only `{"default": false}` has no enabled rules to serialize, so TOML dry-run stdout is instead exactly one newline.

Otherwise the default target is `.rumdl.toml`; `--output` changes it, `.json`/`--format json` produces JSON, and a `pyproject.toml` target uses `[tool.rumdl...]` tables without damaging unrelated content. JSON files use two-space pretty printing and have no terminal newline. Object members retain conversion order. For example, importing a configuration that disables MD013 and configures MD007 indent 3 writes exactly the following bytes, with the closing `}` as the final byte:

```json
{
  "global": {
    "disable": [
      "MD013"
    ]
  },
  "MD007": {
    "indent": 3,
    "style": "fixed"
  }
}
```

Importing a markdownlint MD007 object with an `indent` value always injects `style = "fixed"` in TOML immediately after `indent`; thus `{"MD007":{"indent":3}}` dry-runs as exactly `[MD007]\nindent = 3\nstyle = "fixed"\n\n\n`.

A successful write exits 0 and prints exactly these two lines, including the single quotes around both displayed paths:

```text
Converted markdownlint config from 'INPUT' to 'OUTPUT'
You can now use: rumdl check --config OUTPUT .
```

`INPUT` is displayed as supplied (including an absolute path), while `OUTPUT` uses the supplied target spelling; the default is `.rumdl.toml`. Missing and malformed input are import usage failures: they exit 2 and write nothing to stdout. A missing file uses the supplied path and exact platform suffix: stderr is `Import error: Failed to read config file PATH: No such file or directory (os error 2)\n`. For example, `/nonexistent/config.json` and `/nonexistent/file.json` are reproduced literally in place of `PATH`.

Malformed YAML uses a single parser-summary line, not a multiline source excerpt. These observed inputs and complete stderr bytes are normative:

- `MD013:\n  line_length: 80\n    indentation: broken\n` produces `Import error: Failed to parse YAML: mapping values are not allowed in this context at line 3 column 16\n`.
- `MD013:\n  line_length: 90\n  - invalid item\n` produces `Import error: Failed to parse YAML: did not find expected key at line 3 column 3, while parsing a block mapping at line 2 column 3\n`.

Malformed JSON analogously begins `Import error: Failed to parse JSON: `. An unsupported format is status 2 with empty stdout; `--format xml` writes exactly `Error: Unsupported format 'xml'. Use 'toml' or 'json'.\n` to stderr. Never overwrite an existing target, and preserve it byte-for-byte on failure. Refusing an existing target also exits 2 with empty stdout and writes exactly `Error: Output file 'OUTPUT' already exists\n` to stderr.

The exact `import --help` stdout is:

```text
Import and convert markdownlint configuration files

Usage: executable import [OPTIONS] <FILE>

Arguments:
  <FILE>  Path to markdownlint config file (JSON/YAML)

Options:
  -o, --output <OUTPUT>  Output file path (default: .rumdl.toml)
      --format <FORMAT>  Output format: toml or json [default: toml]
      --dry-run          Show converted config without writing to file
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

`completions [SHELL]` supports `bash`, `zsh`, `fish`, `powershell`, and `elvish`. `completions --list` and `completions -l` exit 0, write nothing to stderr, and print exactly:

```text
Available shells:
  bash         Bourne Again SHell
  zsh          Z shell
  fish         Friendly Interactive SHell
  powershell   PowerShell
  elvish       Elvish shell
```

With no argument, infer from the basename of `$SHELL`. If `$SHELL` is unavailable or cannot be recognized, exit 2, write nothing to stdout, and write exactly this body to stderr:

```text
Error: Could not detect shell from $SHELL environment variable

Please specify a shell explicitly:
  rumdl completions bash
  rumdl completions zsh
  rumdl completions fish
  rumdl completions powershell
  rumdl completions elvish

Or use --list to see all available shells
```

An explicit invalid shell is a command-line usage error, not shell-detection failure: `completions invalid_shell` exits 2, writes nothing to stdout, and writes exactly:

```text
error: invalid value 'invalid_shell' for '[SHELL]'
  [possible values: bash, elvish, fish, powershell, zsh]

For more information, try '--help'.
```

Generated output is script only on stdout and no stderr: bash defines `_rumdl()` and `COMPREPLY`; zsh starts `#compdef rumdl`, defines `_rumdl()` and autoloads completion; fish defines helpers whose names begin `__fish_rumdl` (including exact names `__fish_rumdl_global_optspecs`, `__fish_rumdl_needs_command`, and `__fish_rumdl_using_subcommand`) and emits `complete -c rumdl`; PowerShell uses `Register-ArgumentCompleter` and `CompletionResult`; Elvish imports needed modules and uses the exact assignment prefix `set edit:completion:arg-completer[rumdl] =`. Scripts are deterministic and enumerate commands. The generated fish script contains `check` and omits the literal option `--output-format`.

The exact `completions --help` stdout is:

```text
Generate shell completion scripts

Usage: executable completions [OPTIONS] [SHELL]

Arguments:
  [SHELL]  Shell to generate completions for (detected from $SHELL if omitted) [possible values: bash, elvish, fish, powershell, zsh]

Options:
  -l, --list             List available shells
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

## Spec 15

### Rule catalog and explanation commands

The rule-command option grammar includes `-o|--output-format <FORMAT>`, `-f|--fixable`, and `-c|--category <CATEGORY>`. `-o json-lines` is accepted (as is `json`) and has the same semantics as the long form. These short options combine, so `rule -f -c heading -o json` exits 0 and emits the filtered JSON array.

There are exactly 67 rules, sorted numerically, omitting unassigned MD002, MD006, MD008, and MD015–MD017. Plain `rule` prints `Available rules:`, two-space-indented `MDxxx - SUMMARY` lines in the exact catalog in Spec 21, a blank line, and `Total: 67 rules`. Filtered text changes the header to name every active filter in parentheses. For example, `rule --fixable --category heading` begins exactly `Available rules (fixable, category=heading):`, while `rule -f` begins `Available rules (fixable):`. The catalog assigns MD013 to category `whitespace`, so `rule 013` includes the exact line `Category: whitespace`. `rule ID` accepts case-insensitive canonical IDs such as `MD001`/`md001` and the three-digit numeric spelling `001`. It does not accept an unpadded number or alias: `rule 1` and `rule heading-increment` each return 2, write nothing to stdout, and respectively write `Rule '1' not found.\n` and `Rule 'heading-increment' not found.\n` to stderr. A successful `rule MD001`, `rule md001`, or `rule 001` prints:

```text
MD001 - Heading levels should only increment by one level at a time

Name: heading-increment
Category: heading
Fix: Fix is always available.
Documentation: https://rumdl.dev/md001/
```

The URL pattern is `https://rumdl.dev/mdxxx/`. JSON objects contain exactly/usefully `code`, primary canonical `name`, remaining `aliases` array, `summary`, `category`, human `fix`, `fix_availability` (`Always`, `Sometimes`, or `None`), and `url`; all-rules JSON is an array and JSONL is one object per line. The primary name is not duplicated in `aliases`: MD001 has `name: "heading-increment"` and `aliases: []`. MD025 has `name: "single-h1"` and `aliases: ["single-title"]`. For MD041, `name` is exactly `first-line-h1` and `aliases` is exactly `["first-line-heading"]`; the two strings are not interchangeable between those fields. When `fix_availability` is `None`, the exact human `fix` value is `Fix is not available.`; MD059 uses that pair. `--fixable` returns 64 rules, excluding MD033/MD054/MD059. `--category` is case-insensitive; filters combine by intersection. `--list-categories` prints exactly:

```text
Available categories:
  blockquote (1 rules)
  code-block (4 rules)
  emphasis (1 rules)
  front-matter (1 rules)
  heading (11 rules)
  html (1 rules)
  link (7 rules)
  list (7 rules)
  other (29 rules)
  whitespace (5 rules)
```

The complete `heading` category, in output order, is MD001, MD003, MD018, MD019, MD020, MD021, MD022, MD023, MD024, MD025, and MD043. Accordingly `rule --category heading` prints exactly those 11 catalog rows between `Available rules (category=heading):` and `Total: 11 rules`.

An invalid ID prints `Rule 'VALUE' not found.` for `rule`; `explain` prints `Error: Rule 'VALUE' not found.` then a blank line and `Use 'rumdl rule' to see all available rules.` An invalid category returns 2, writes nothing to stdout, and uses exactly two stderr lines with a final newline:

```text
Invalid category: 'nonexistent'
Valid categories: blockquote, code-block, emphasis, front-matter, heading, html, link, list, other, whitespace
```

Multiple positional IDs are rejected. Invoking `explain` without its required rule exits 2, writes nothing to stdout, and writes this diagnostic shape to stderr: `error: the following required arguments were not provided:` followed on the next indented line by `<RULE>`, then the `Usage: executable explain <RULE>` line and the normal help hint. Identifier acceptance matches `rule`: `explain MD001`, `explain md001`, and `explain 001` succeed, while `explain 1` and `explain heading-increment` return 2 with the invalid-ID diagnostic.

Explanation detail depends on whether the source documentation is available to the executable from its runtime directory. When available, `explain ID` and `rule ID --explain` provide detailed documentation headed `MDxxx - SUMMARY`, including an `Aliases:` line containing the rule's canonical aliases, `What this rule does`, `Why this matters`, and `Examples` whose subsection markers are exactly `✅ Correct`, `❌ Incorrect`, and, where a fix exists, `🔧 Fixed`, plus `Configuration`; their layouts are deliberately different. In particular, `explain MD047` contains the backtick-delimited canonical alias `single-trailing-newline`. `explain ID` renders the documentation for terminal reading and ends with a `Default Configuration:` block. `rule ID --explain` first prints the ordinary `rule ID` metadata block, then a blank line, then the source documentation with Markdown `#`/`##`/`###` headings; it does not append the rendered default-configuration block. The final default-settings section of `explain` is headed exactly `Default Configuration:` (capitalized and with the colon); for MD045 it is followed by `[MD045]` and `placeholder-text = "TODO: Add image description"`. JSON `--explain` adds an `explanation` field.

In an isolated working directory with no source documentation, `explain MD001`, `explain md001`, and `explain 001` instead all return 0 with empty stderr and exactly this fallback stdout:

```text
MD001 - Heading levels should only increment by one level at a time

Category: Heading

This rule helps maintain consistent Markdown formatting.

For more information, see the documentation at:
  https://rumdl.dev/md001/
```

The exact `explain --help` stdout is:

```text
Explain a rule with detailed information and examples

Usage: executable explain [OPTIONS] <RULE>

Arguments:
  <RULE>  Rule name or ID to explain

Options:
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

When source documentation is available, the exact `rule MD001 --explain` stdout, including its terminal newline, is:

````text
MD001 - Heading levels should only increment by one level at a time

Name: heading-increment
Category: heading
Fix: Fix is always available.
Documentation: https://rumdl.dev/md001/

# MD001 - Heading levels should only increment by one

Aliases: `heading-increment`

## What this rule does

Prevents skipping heading levels (like jumping from # to ### without ##).

## Why this matters

- **Document structure**: Logical heading hierarchy makes documents easier to navigate
- **Accessibility**: Screen readers rely on proper heading order to help users
- **Table of contents**: Automated TOC generators need correct heading levels
- **SEO**: Search engines use heading structure to understand content

## Examples

### ✅ Correct

```markdown
# Title
## Chapter 1
### Section 1.1
### Section 1.2
## Chapter 2
### Section 2.1
```

### ❌ Incorrect

```markdown
# Title
### Section 1.1     (skipped level 2)
##### Subsection    (skipped levels 2, 3, and 4)
```

### 🔧 Fixed

```markdown
# Title
## Section 1.1
### Subsection
```

## Configuration

This rule has no configuration options.

## Automatic fixes

This rule automatically adjusts heading levels to maintain proper hierarchy, changing skipped levels to the next appropriate level.

## Learn more

- [Web Content Accessibility Guidelines - Headings](https://www.w3.org/WAI/tutorials/page-structure/headings/) - Why heading structure matters
- [CommonMark headings](https://spec.commonmark.org/0.31.2/#atx-headings) - Technical specification

## Related rules

- [MD002](md002.md) - First heading should be a top-level heading
- [MD003](md003.md) - Heading style should be consistent
- [MD022](md022.md) - Headings should be surrounded by blank lines

````

When source documentation is available, the exact `explain MD001` stdout, including its terminal newline, is:

````text
MD001 - Heading levels should only increment by one level at a time


Aliases: `heading-increment`


What this rule does

Prevents skipping heading levels (like jumping from # to ### without ##).


Why this matters

- **Document structure**: Logical heading hierarchy makes documents easier to navigate
- **Accessibility**: Screen readers rely on proper heading order to help users
- **Table of contents**: Automated TOC generators need correct heading levels
- **SEO**: Search engines use heading structure to understand content


Examples


✅ Correct

```markdown
  # Title

Chapter 1

Section 1.1

Section 1.2

Chapter 2

Section 2.1
```


❌ Incorrect

```markdown
  # Title

Section 1.1     (skipped level 2)
  ##### Subsection    (skipped levels 2, 3, and 4)
```


🔧 Fixed

```markdown
  # Title

Section 1.1

Subsection
```


Configuration

This rule has no configuration options.


Automatic fixes

This rule automatically adjusts heading levels to maintain proper hierarchy, changing skipped levels to the next appropriate level.


Learn more

- [Web Content Accessibility Guidelines - Headings](https://www.w3.org/WAI/tutorials/page-structure/headings/) - Why heading structure matters
- [CommonMark headings](https://spec.commonmark.org/0.31.2/#atx-headings) - Technical specification


Related rules

- [MD002](md002.md) - First heading should be a top-level heading
- [MD003](md003.md) - Heading style should be consistent
- [MD022](md022.md) - Headings should be surrounded by blank lines

Default Configuration:
[MD001]
front-matter-title = true
````

## Spec 16

### Persistent cache and `clean`

Caching is on by default and off with `--no-cache` or `cache = false`. For commands that expose the cache option, resolve the directory as CLI `--cache-dir`, then `$RUMDL_CACHE_DIR`, then config `cache-dir`, then `.rumdl_cache` in the project. Store entries below a version directory `.rumdl_cache/0.1.13/`. A JSON entry includes at least `file_hash`, `config_hash`, `rules_hash`, `version` (`0.1.13`), `warnings` (complete message/line/column/rule/severity/fix information), and `timestamp`. Content hashes, not basenames, identify reusable file results, so identical bytes at different names may share one entry; multiple different files must not overwrite one another. Configuration, enabled rules, flavor, content, and executable version participate in invalidation. Entries survive runs and must be written atomically under parallel invocations.

The cache root contains `.gitignore` whose exact contents are `# Automatically created by rumdl.\n*\n`, and a `CACHEDIR.TAG` beginning `Signature: 8a477f597d28d172789f06886806bc55\n# This file is a cache directory tag created by rumdl.\n`. A cache-enabled filesystem check also creates `workspace_index.bin` for cross-file headings/links; it is present alongside the tag, ignore file, and version entries after checking a directory. Nested source directories do not require nested cache trees. Corrupt/stale entries are ignored and regenerated without crashing. Cached `warnings` preserve exactly the eligible diagnostics emitted by linting: for a line containing one ordinary multi-space run and another run inside inline code, MD064 emits and caches one warning, not two.

`clean` removes the entire cache directory resolved from environment/configuration/default settings, including version entries, metadata, workspace index, tags and ignore file. It has no `--cache-dir` option: `clean --cache-dir PATH` is a status-2 unexpected-argument error. It returns 0 when the directory is missing or empty. For a missing default cache, stdout is exactly `No cache found at .rumdl_cache (nothing to clean)\n`. For an existing empty default directory, stdout is instead exactly `Cache is empty at .rumdl_cache (nothing to clean)\n`, and that directory is removed. A nonempty removal uses exactly two lines in this order: `Cleared cache: .rumdl_cache`, then two leading spaces and `Removed SIZE UNIT across N files`; for example, a 49-byte three-file cache prints `  Removed 49 B across 3 files`. It must not delete anything outside the exact resolved cache directory.

The exact `clean --help` stdout is:

```text
Clear the cache

Usage: executable clean [OPTIONS]

Options:
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

## Spec 17

### Parallel processing, watch mode, and robustness

Directory/file processing may be parallel but observable results remain deterministic, fixes are race-free, cache JSON is not corrupted, duplicate paths are not processed twice, and hundreds of small files or a multi-megabyte/very-long-line document complete without pathological slowdown. The executable must handle overlapping fixes, very large front matter/code blocks, unclosed constructs, Unicode and CRLF without a crash.

`check --watch PATHS` performs an initial lint, prints a clear watching message, then remains alive and re-lints after relevant filesystem changes. Watch recursively for creation, modification, deletion and rename of supported Markdown files and configuration/ignore files. Coalesce rapid events with a short debounce so one logical save produces one run. Reload changed config, update include/exclude/ignore decisions, handle an empty or disappearing watched path gracefully, and avoid a self-trigger loop after `--fix`. Changes to `.md`, `.markdown`, `.mdown`, `.mkd`, `.mdx`, `.qmd`, and `.rmd` are eligible. Termination signals end promptly. Watch help and all advertised combinations parse without beginning an accidental infinite watch in a dry-run/help request.

In normal mode, each watch run begins by clearing the terminal and printing a local-time `HH:MM:SS` timestamp. The initial transcript starts in this exact order (with the actual timestamp substituted), before the initial lint result:

```text
[HH:MM:SS] Starting linter in watch mode...
Press Ctrl-C to exit

```

After the initial result it prints a blank line and `Watching for file changes...`. A relevant Markdown event clears the terminal and starts the next run with `[HH:MM:SS] File change detected...`, then a blank line and the new lint result; after that result it again prints a blank line and `Watching for file changes...`. A configuration-file event instead uses `[HH:MM:SS] Configuration change detected...` before reloading and re-linting.

Watch-mode lifecycle output is an exception to the ordinary quiet/silent rules in Spec 10. With `--quiet`, the terminal-clear sequence, timestamped startup/change headings, `Press Ctrl-C to exit`, and diagnostics remain visible, while success/summary/suggestion and `Watching for file changes...` are suppressed. With `--silent`, the terminal-clear sequence, timestamped startup/change headings, `Press Ctrl-C to exit`, and `Watching for file changes...` remain visible, while lint diagnostics/results are suppressed.

If a watched path does not exist, the process remains in watch mode. Stderr contains exactly `Warning: Failed to watch PATH: No path was found.\n` before the ordinary `Error: Failed to find markdown files: File not found: PATH\n`; stdout still contains the startup transcript and `Watching for file changes...`.

## Spec 18

### VS Code-compatible editor integration

`vscode` installs/checks the extension ID `rvben.rumdl`. Its exact help is:

```text
Install the rumdl VS Code extension

Usage: executable vscode [OPTIONS]

Options:
      --force            Force reinstall the current version even if already installed
      --update           Update to the latest version (only if newer version available)
      --status           Show installation status without installing
      --color <COLOR>    Control colored output: auto, always, never [default: auto] [possible values: auto, always, never]
      --config <CONFIG>  Path to configuration file
      --no-config        Ignore all configuration files and use built-in defaults
      --isolated         Ignore all configuration files (alias for --no-config)
  -h, --help             Print help
```

`vscode --help` returns 0 and writes nothing to stderr.

The operation flags are not a mutually-exclusive parser group. Operation precedence is `--status`, then `--update`, then `--force`, then ordinary installation. Thus `vscode --status --force` performs the status query, and `vscode --force --update` performs the update path rather than force-reinstalling. In particular, with the extension absent, the latter returns 0 and prints exactly `✗ Rumdl VS Code extension is not installed\n  Run rumdl vscode to install it\n`; it does not invoke the install operation. Detect available compatible editor commands in priority order `code`, `cursor`, `windsurf`, then `codium`/`vscodium`; `$TERM_PROGRAM` may identify the active editor. When both `code` and `cursor` are available without a controlling environment override, `code` is selected. Verify the command with `--version`. Installation detection is a two-stage query: first run `--list-extensions` without `--show-versions` and require a line exactly equal to `rvben.rumdl`; only after that exact unversioned ID is found, run `--list-extensions --show-versions` to obtain the version. Thus an editor shim that returns only `rvben.rumdl@0.1.13` from the first query is reported as not installed and the second query is not made; returning `rvben.rumdl` first and `rvben.rumdl@VERSION` for the versioned query produces the installed status with `Current version: VERSION`. Install with that editor's extension-install option (including force when requested).

If no compatible command is available, ordinary install, `--status`, `--update`, and `--force` all write nothing to stdout, return status 2, and write exactly this line to stderr:

```text
Error: VS Code (or compatible editor) not found. Please ensure one of the following commands is available: code, cursor, windsurf, codium, vscodium
```

Global `--no-config` and `--color never` do not alter that status or message. A successful `--status` returns 0 even when the extension is absent. Its absent-extension stdout is exactly:

```text
✗ Rumdl VS Code extension is not installed
  Run rumdl vscode to install it
```

When installed, status uses the same branding for VS Code, Cursor, Windsurf, and VSCodium; its first two lines are:

```text
✓ Rumdl VS Code extension is installed
  Current version: VERSION
```

An ordinary invocation that finds the extension already installed returns 0 without reinstalling and begins:

```text
✓ Rumdl VS Code extension is already installed
  Current version: VERSION
```

`--update` on an absent extension also returns 0 and prints the same two-line absent-extension instruction instead of installing it. When an update is available, update prints current/latest and `Updating to version ...` as appropriate. For a first install through `code`, the successful stdout is:

```text
Installing rumdl - Markdown Linter extension...
✓ Successfully installed Rumdl VS Code extension!
  Installed version: VERSION
```

For `--force` through `code`, replace that first line with `Force reinstalling rumdl - Markdown Linter extension...`; the success and installed-version lines follow unchanged. Successful install, already-installed, force, update-with-absent-extension, and status results return 0.

An editor install-command execution failure and a marketplace-not-found install failure return status 2. The install progress line remains on stdout before the error on stderr. A failed process launch is reported as `Error: Failed to run VS Code command: DETAILS`. If an invoked install command exits unsuccessfully for a reason not recognized as a marketplace miss, stderr is exactly `Error: Failed to install extension: DETAILS\n`; an exit-127 shim with no detail therefore produces `Error: Failed to install extension: \n`.

A VS Code marketplace miss writes exactly these two stderr lines:

```text
Error: Extension not found in VS Code Marketplace.
Please check: https://marketplace.visualstudio.com/items?itemName=rvben.rumdl
```

Cursor and Windsurf marketplace misses begin stderr with the exact contiguous sentence `Error: Extension not found in marketplace. Please install from Open VSX:`, followed by `https://open-vsx.org/extension/rvben/rumdl`, a blank line, `Or download the VSIX directly and install with:`, and respectively `cursor --install-extension path/to/rumdl-*.vsix` or `windsurf --install-extension path/to/rumdl-*.vsix`. Before invoking either editor, stdout also includes the Open VSX guidance headed `ℹ Note: Cursor/Windsurf may default to VS Code Marketplace.` VSCodium instead writes exactly:

```text
Error: Extension not found. VSCodium uses Open VSX by default.
Please check: https://open-vsx.org/extension/rvben/rumdl
```

These marketplace errors return 2.

## Spec 19

### Language Server Protocol server

`server` defaults to stdio; `server --stdio` is explicit stdio and `server --port PORT` listens on TCP. Stdio uses standard LSP framing: ASCII `Content-Length: N\r\n\r\n` followed by exactly N UTF-8 JSON bytes, with no ordinary stdout chatter. It supports JSON-RPC 2.0 lifecycle (`initialize`, `initialized`, `shutdown`, `exit`) and returns MethodNotFound for unknown request methods rather than terminating. Shutdown response has `result: null`. Null root URI and multi-root `workspaceFolders` are valid.

The initialize result has `serverInfo.name = "rumdl"` and advertises at least these exact structures:

```json
{
  "textDocumentSync": {"openClose":true,"change":1,"willSave":false,"willSaveWaitUntil":true,"save":{"includeText":false}},
  "codeActionProvider": {"codeActionKinds":["quickfix","source.fixAll","source.fixAll.rumdl"]},
  "completionProvider": {"resolveProvider":false,"triggerCharacters":["`"]},
  "workspace": {"workspaceFolders":{"supported":true,"changeNotifications":true}},
  "diagnosticProvider": {"identifier":"rumdl","interFileDependencies":true,"workspaceDiagnostics":false}
}
```

Also advertise document/range formatting. Track independently opened Markdown-family documents and monotonically increasing versions. `didOpen` and `didChange` (full-text and incremental changes) re-lint and publish `textDocument/publishDiagnostics`; reject/ignore stale versions. `didSave`, `didClose`, `workspace/didChangeWorkspaceFolders`, `workspace/didChangeWatchedFiles`, and `workspace/didChangeConfiguration` must not crash; closing releases in-memory content, folder/config changes invalidate and re-lint. Non-Markdown extensions are ignored. For an unopened file URI, diagnostic/formatting requests may read an existing file from disk; nonexistent/malformed URIs return a JSON-RPC error/null as appropriate, never crash.

`textDocument/diagnostic` returns `{kind:"full", items:[...]}`. Each diagnostic has a zero-based UTF-16-safe `range`, severity 1 error/2 warning/3 information, code `MDxxx`, source `rumdl`, message, and a code-description documentation URL when applicable. Multiple findings stay separate. Formatting returns text edits that produce the same result as `fmt`; no required changes yields JSON null, not an empty list. Range formatting returns edits only inside the requested line range. `willSaveWaitUntil` returns applicable edits. Code actions honor the request range/context, offer preferred quick fixes for concrete findings, and source fix-all actions that fix every safe finding; workspace edits are grouped by URI.

MD041 uses the same recoverable-heading interpretation as the CLI when diagnostics are produced. In particular, a leading no-space ATX form such as `#Heading` already supplies the level-1 document heading for MD041 even though MD018 diagnoses its missing space. For a document consisting of `#Heading`, a blank line, and an unlabeled backtick fence containing code, both published and pulled LSP diagnostics contain exactly two items, in rule order: MD018 followed by MD040; MD041 is not an additional item.

Completion after a backtick fence returns at least 100 nonempty language-label items from the built-in language data, filters prefixes, works for longer fences, and honors MD040 allowed/disallowed/preferred aliases. Initialization/dynamic settings accept lint enablement, enabled/disabled rules, flavor, configuration path and per-rule settings. The server remains responsive through rapid changes, large documents, many simultaneous documents, and repeated open/change/close cycles without unbounded retention.

## Spec 20

### Shared Markdown parser and skipped contexts

All rules and fixes must share a structure-aware parser. Recognize ATX headings only with one through six `#` characters and up to three leading spaces; recognize Setext headings only when content and `=`/`-` underline indentation is compatible and the line is not a list/thematic break. Recognize backtick and tilde fenced blocks of length at least three with up to three leading spaces, optional info strings, matching fence character, and a closing fence at least as long as its opener. A four-space-indented would-be fence is indented code. An unclosed fence consumes to EOF. Recognize four-space/tab indented code, inline code using matching runs, HTML comments/blocks, links/images/reference definitions, blockquotes, ordered/unordered/task lists, tables, emphasis/strong/strikethrough, thematic breaks, and footnotes.

Kramdown/Python-Markdown attribute lists are recognized even in the default `standard` flavor. This includes heading IDs written inline as `{#id}`, `{ #id }`, `{:#id}`, or `{: #id }`, extended lists containing classes or quoted key/value attributes, and those same ID/list forms on the line immediately following a heading. A next-line attribute list belongs to its preceding heading: MD022 measures the required blank line after the attribute-list line rather than between it and the heading. Multiple consecutive valid attribute-list lines are all attached to the heading. Inline span attribute lists immediately adjacent to their span are likewise syntax rather than ordinary brace text. Empty `{}` and text-only `{not an ial}` are not attribute lists; directly after a heading they are ordinary content and MD022 reports the missing blank below that heading.

Unless a rule specifically targets one of these constructs, do not lint literal code (inline, fenced, or indented), front-matter bodies, HTML comments, link destinations/reference-definition URLs, or dialect-specific opaque regions. This includes the raw backtick strings used inside Go/Hugo template actions: in ``{{ $x := printf  `<div>content</div>` }}``, neither backtick is an MD038 finding and the embedded opening/closing `div` tags are not MD033 findings; the two spaces before the raw string remain independently eligible for MD064. An ordinary padded code span outside that construct, such as ``Normal `bad ` code.``, still produces its MD038 finding. MD009 and MD010 are explicit front-matter exceptions: trailing whitespace in delimiters or body fields is reported and fixable, as is a hard tab inside YAML front matter. Blank lines do not close fences. A tilde cannot close backticks. Backticks contained within a longer outer fence are literal. Blockquote and list prefixes are stripped for parsing and correctly restored for fixes. Tabs use four-column tab stops for structural indentation. Parsing and fixes preserve all non-targeted bytes and maintain accurate original locations even after earlier fixes, except for MD041's documented whole-preamble heading move in Spec 33.

Heading IDs and reference labels are case-insensitive where their Markdown semantics require. Escapes, nested brackets/parentheses, angle autolinks, titles, query strings/fragments, entities, punctuation next to URLs, and Unicode must not confuse element boundaries. Line-oriented rules distinguish leading indentation, trailing hard breaks, and internal spaces.

## Spec 21

### Exact rule catalog

The numeric order and public summaries are exactly:

```text
MD001 - Heading levels should only increment by one level at a time
MD003 - Heading style
MD004 - Use consistent style for unordered list markers
MD005 - List indentation should be consistent
MD007 - Unordered list indentation
MD009 - Trailing spaces should be removed
MD010 - No tabs
MD011 - Reversed link syntax
MD012 - Multiple consecutive blank lines
MD013 - Line length should not be excessive
MD014 - Commands in code blocks should show output
MD018 - No space after hash in heading
MD019 - Multiple spaces after hash in heading
MD020 - No space inside hashes on closed heading
MD021 - Multiple spaces inside hashes on closed heading
MD022 - Headings should be surrounded by blank lines
MD023 - Headings must start at the beginning of the line
MD024 - Multiple headings with the same content
MD025 - Multiple top-level headings in the same document
MD026 - Trailing punctuation in heading
MD027 - Multiple spaces after quote marker (>)
MD028 - Blank line inside blockquote
MD029 - Ordered list marker value
MD030 - Spaces after list markers should be consistent
MD031 - Fenced code blocks should be surrounded by blank lines
MD032 - Lists should be surrounded by blank lines
MD033 - Inline HTML is not allowed
MD034 - No bare URLs - wrap URLs in angle brackets
MD035 - Horizontal rule style
MD036 - Emphasis should not be used instead of a heading
MD037 - Spaces inside emphasis markers
MD038 - Spaces inside code span elements
MD039 - Spaces inside link text
MD040 - Code blocks should have a language specified
MD041 - First line in file should be a top level heading
MD042 - No empty links
MD043 - Required heading structure
MD044 - Proper names should have the correct capitalization
MD045 - Images should have alternate text (alt text)
MD046 - Code blocks should use a consistent style
MD047 - Files should end with a single newline character
MD048 - Code fence style should be consistent
MD049 - Emphasis style should be consistent
MD050 - Strong emphasis style should be consistent
MD051 - Link fragments should reference valid headings
MD052 - Reference links and images should use a reference that exists
MD053 - Link and image reference definitions should be needed
MD054 - Link and image style should be consistent
MD055 - Table pipe style should be consistent
MD056 - Table column count should be consistent
MD057 - Relative links should point to existing files
MD058 - Tables should be surrounded by blank lines
MD059 - Link text should be descriptive
MD060 - Table columns should be consistently aligned
MD061 - Forbidden terms
MD062 - Link destination should not have leading or trailing whitespace
MD063 - Heading capitalization
MD064 - Multiple consecutive spaces
MD065 - Horizontal rules should be surrounded by blank lines
MD066 - Footnote validation
MD067 - Footnote definitions should appear in order of first reference
MD068 - Footnote definitions should not be empty
MD069 - Duplicate list markers
MD070 - Nested code fence collision - use longer fence to avoid premature closure
MD071 - Blank line after frontmatter
MD072 - Frontmatter keys should be sorted alphabetically
MD073 - Table of Contents should match document headings
```

All except MD063, MD072, and MD073 are enabled by the reference's ordinary default project profile; in particular, MD060 is active and reports a malformed alignment row as `Table columns should be aligned`. MD063 has an additional rule-local `enabled=false` gate: selecting it with CLI `--enable MD063` does not make it run unless `[MD063] enabled=true` is also configured. For example, `[MD063] style="title_case"` plus `check --quiet --enable MD063` accepts `# the wrong title\n` with status 0 and no output; adding `enabled=true` makes the heading reportable/fixable. Canonical aliases are ordered, and the first alias is the primary JSON `name`; the remainder populate `aliases`. In rule order they are: MD001 `heading-increment`; MD003 `heading-style`; MD004 `ul-style`; MD005 `list-indent`; MD007 `ul-indent`; MD009 `no-trailing-spaces`; MD010 `no-hard-tabs`; MD011 `no-reversed-links`; MD012 `no-multiple-blanks`; MD013 `line-length`; MD014 `commands-show-output`; MD018 `no-missing-space-atx`; MD019 `no-multiple-space-atx`; MD020 `no-missing-space-closed-atx`; MD021 `no-multiple-space-closed-atx`; MD022 `blanks-around-headings`; MD023 `heading-start-left`; MD024 `no-duplicate-heading`; MD025 `single-h1` then `single-title`; MD026 `no-trailing-punctuation`; MD027 `no-multiple-space-blockquote`; MD028 `no-blanks-blockquote`; MD029 `ol-prefix`; MD030 `list-marker-space`; MD031 `blanks-around-fences`; MD032 `blanks-around-lists`; MD033 `no-inline-html`; MD034 `no-bare-urls`; MD035 `hr-style`; MD036 `no-emphasis-as-heading`; MD037 `no-space-in-emphasis`; MD038 `no-space-in-code`; MD039 `no-space-in-links`; MD040 `fenced-code-language`; MD041 `first-line-h1` then `first-line-heading`; MD042 `no-empty-links`; MD043 `required-headings`; MD044 `proper-names`; MD045 `no-alt-text`; MD046 `code-block-style`; MD047 `single-trailing-newline`; MD048 `code-fence-style`; MD049 `emphasis-style`; MD050 `strong-style`; MD051 `link-fragments`; MD052 `reference-links-images`; MD053 `link-image-reference-definitions`; MD054 `link-image-style`; MD055 `table-pipe-style`; MD056 `table-column-count`; MD057 `existing-relative-links`; MD058 `blanks-around-tables`; MD059 `descriptive-link-text`; MD060 `table-format`; MD061 `forbidden-terms`; MD062 `link-destination-whitespace` and `no-space-in-link-destination`; MD063 `heading-capitalization`; MD064 `no-multiple-consecutive-spaces`; MD065 `blanks-around-horizontal-rules`; MD066 `footnote-validation`; MD067 `footnote-definition-order`; MD068 `empty-footnote-definition`; MD069 `no-duplicate-list-markers`; MD070 `nested-code-fence`; MD071 `blank-line-after-frontmatter`; MD072 `frontmatter-key-sort`; MD073 `toc-validation`.

## Spec 22

### Front matter and dialect selection

At byte zero, recognize YAML front matter delimited by `---`. A closed delimiter pair with an empty body is front matter when document content follows it: `---\n---\n\n# Heading\n` is clean. The special file consisting only of `---\n---\n` is instead not an empty front-matter block: its first line is a thematic rule and receives MD065 at line 1, column 4. A BOM before an opener prevents recognition: the BOM-prefixed five-line document `BOM + ---`, `title: Test`, `---`, a blank line, and `# Test` produces MD041 at line 1 column 1, MD003 at line 2 column 1, and MD022 at line 2 column 1.

Leading TOML `+++` and a complete leading JSON object are recognized sufficiently to protect their bodies for applicable front-matter rules, but unlike YAML they remain first-line content for MD041; each receives `First line in file should be a level 1 heading` at line 1 column 1 even when followed by a valid H1. This remains true for TOML arrays, array tables, and multiline strings and for JSON nested objects, arrays, and `null` values. Empty `+++\n+++\n` and `{}` blocks follow that same MD041 behavior rather than satisfying the first-heading rule.

Also recognize the two deliberately malformed YAML delimiter pairs `- --` ... `- --` and `-- -` ... `-- -` as front matter; their bodies and delimiters do not produce ordinary Markdown findings. YAML, TOML, JSON-closing, and these malformed delimiter lines accept trailing horizontal whitespace for boundary recognition. The ordinary MD009 policy still applies to that whitespace: in particular, the default-allowed two trailing spaces leave a closed YAML or malformed-YAML example clean, while the analogous TOML and JSON examples have only the line-1 MD041 finding. Delimiters later in a document are thematic/content, not front matter.

A YAML/TOML opener is front matter only if a matching same-kind closer exists; `+++` does not close a `---` opener. An unclosed or mixed-closer `---`/`+++` opener is parsed as ordinary Markdown through EOF rather than suppressing all of its lines as front matter. Thus a leading `---` followed by YAML-like text, `+++`, and a heading produces MD041/MD065 ordinary-Markdown findings and exits 1. An unclosed leading `{` is likewise ordinary content and produces line-1 MD041. An unclosed leading malformed delimiter `- --` or `-- -` produces line-1 MD041 plus `Missing blank line after horizontal rule` at column 5, but no MD035 style finding for that first delimiter.

Preserve closed front matter except for the formats and transformations explicitly targeted by MD009, MD010, MD071, and MD072; MD071's narrower YAML/TOML scope is specified in Spec 39. MD009 applies to trailing whitespace in both delimiters and body fields; for example, three trailing spaces after `title: Test` produce `3 trailing spaces found` at the start of that three-space run and are fixable. MD010 reports hard tabs in YAML front-matter fields (for example a tab after `title:` is `Found tab for alignment, use spaces instead`), while other front-matter contents do not create headings, lists, HTML, line-length, or forbidden-term findings. Correctly parse huge, CRLF, scalar, array, quoted, multiline, comments, colons/equals in values, nested maps, and mixed scalar types without confusing document lines; this parsing protection does not make TOML or JSON satisfy MD041.

The canonical flavors are `standard`, `mkdocs`, `mdx`, `quarto`, and `obsidian`. The CLI accepts only those five spellings. In particular, `--flavor gfm`, `--flavor github`, and `--flavor commonmark` each return 2 with `invalid value` and the possible-values list `standard, mkdocs, mdx, quarto, obsidian`; aliases listed in the configuration schema are not CLI enum values. CLI wins over configured selection. Standard includes commonly used GFM tables, task lists, strikethrough and extended URL recognition, treating autolinks/tables/tasks/strikethrough as syntax with security-conscious HTML handling. A flavor is a parser exemption only for its actual constructs; the same text under a different flavor may receive ordinary rule findings.

The default `standard` flavor recognizes the Kramdown extension delimiters `{::comment}`/`{:/comment}` and `{::nomarkdown}`/`{:/nomarkdown}`, including nested comment delimiters, but does not make all of their body text opaque to every Markdown rule. For the nested sample consisting of a heading, an outer comment whose first body line is `<div>bad</div>  `, an inner comment containing `<b>x</b>`, and then a nomarkdown block containing `<i>y</i>`, checking only MD009 and MD033 exits 1 and emits exactly one diagnostic: `doc.md:4:1: [MD033] Inline HTML found: <div>`. It emits no MD009 diagnostic for that line and no MD033 diagnostic for the inner-comment or nomarkdown HTML in this sample. Lookalikes without the required double-colon syntax, such as `{:comment}` and `{/comment}`, are not extension delimiters; a later `<div>...</div>` remains ordinary HTML and produces the one MD033 finding `Inline HTML found: <div>` at its opening tag.

MDX recognizes JSX elements/fragments, JSX comments, attributes, multiline expressions/braces, and ESM import/export/dynamic import/re-export regions, but those regions are not wholly opaque to Markdown rules. For `import Thing from './Thing'`, followed by `<Thing prop={"two  spaces"}>`, a nested `<div>html</div>`, and `</Thing>`, checking MD033 and MD064 in `mdx` flavor exits 1 and emits, in this order, `doc.mdx:3:18: [MD064] Multiple consecutive spaces (2) found [*]` and `doc.mdx:4:1: [MD033] Inline HTML found: <div>`. The import line and the `Thing` component tags produce no additional finding in this sample. Quarto recognizes `:::` div/callout delimiter syntax (including classes/attributes), but the Markdown body between those delimiters remains lintable rather than opaque: `::: {.callout-note}\n#not a heading\n:::\n` produces MD018 on line 2, column 2 with `No space after # in heading`. Quarto also recognizes `@citation`/`[@a; @b]`, `{{< shortcode >}}`, display/inline math, executable chunk options, and heading attributes. Obsidian recognizes wiki links/embeds, callouts, `%%` comments, `==highlight==`, tags such as `#todo` and `#project/active` (not malformed headings), Dataview and Templater constructs, and Obsidian code/math conventions.

## Spec 23

### MkDocs extensions

In `mkdocs` flavor, recognize and protect the complete construct rather than linting its punctuation as ordinary Markdown:

- admonitions `!!! type`, collapsible `???`/`???+`, optional quoted titles and `inline`/`inline end`, arbitrary custom types, nested four-space bodies;
- content tabs `=== "Title"` and unquoted titles, with nested/complex indented content;
- definition lists (`Term` followed by one or more `:   definition` blocks and nested continuations);
- abbreviations `*[ABBR]: definition` anywhere, including empty/multiword definitions, special characters/numbers, case-sensitive names;
- attribute lists with optional colon (`{#id .class key="value"}`, single quotes, compact/no-space forms), on headings and inline/block elements, and invisible anchors `[](){#id}`;
- Critic Markup `{++add++}`, `{--delete--}`, `{~~old~>new~~}`, `{==highlight==}`, `{>>comment<<}`, including multiple, multiline and nested Markdown, but not malformed/single-marker or template braces;
- Material/icon shortcodes such as `:material-check:`, `:fontawesome-brands-github:`, `:octicons-alert-24:` and custom hyphenated prefixes, distinct from ordinary emoji;
- PyMdown `/// type` blocks with bare `///` close and nesting; MkDocstrings `::: package.module.Class`, handler prefixes and cross-reference shorthand; snippets, superfences, annotations, keys, task-list and other normal MkDocs/Python-Markdown constructs exercised in combination.

MkDocs autorefs/backtick references and custom heading IDs participate in link-fragment validation as their rendered anchors dictate. These exemptions activate only for MkDocs.

## Spec 24

### Code-block external tools

The optional `[code-block-tools]` system is disabled by default. Options are `enabled=false`, `normalize-language="linguist"|"exact"`, `on-error="fail"|"warn"|"skip"`, `on-missing-language-definition="ignore"|"fail"|"fail-fast"`, `on-missing-tool-binary` with the same values, and `timeout=30000` milliseconds. `[code-block-tools.languages]` maps canonical language names to `{lint=[tool IDs], format=[tool IDs], on-error=...}`; `[code-block-tools.language-aliases]` adds/overrides aliases; `[code-block-tools.tools.NAME]` defines `command` argv, stdin/stdout behavior and related execution settings.

Extract every fenced block, treating the first info-string token as its case-insensitive language and preserving remaining attributes. Empty/whitespace languages are skipped by this processor (MD040 separately reports them). Linguist mode maps common aliases such as py/python, js/javascript, sh/bash/shell and cpp/C++; exact mode does not. Strip blockquote/list indentation before sending code on stdin and reapply it afterward. Preserve whether original code had a trailing newline, Unicode, blank/empty content, fence length/type/info string, and all Markdown outside replacement ranges.

In check mode run configured lint tools and translate common concise/compiler, Ruff, ESLint and ShellCheck output into findings whose line is offset into the Markdown block; infer `E###`/`F###` as error and normal warnings/info appropriately. In fix mode, try configured formatters in order and accept the first successful formatter only. Process replacement blocks from end to beginning so earlier offsets remain valid. A timeout or nonzero result follows the effective on-error mode. Missing language/tool `fail` records an error and continues, `fail-fast` stops immediately, and `ignore` silently skips; an unknown registry tool warns rather than crashes where warn behavior applies. The special `rumdl` tool is built in for fenced Markdown and must never be executed as an external binary.

Built-in tool IDs include `ruff:check`, `ruff:format`, `black`, `isort`, `shellcheck`, `shfmt`, `beautysh`, `prettier`, `eslint`, `oxfmt`, `rustfmt`, `gofmt`, `goimports`, `clang-format`, `stylua`, `taplo`, `tombi`, `yamlfmt`, `jq`, `sql-formatter`, `pg_format`, `nixfmt`, `terraform-fmt`, `mix:format`, `dart-format`, `ktfmt`, `scalafmt`, `ormolu`, `fourmolu`, `latexindent`, `markdownlint`, `typos`, `cljfmt`, `rubocop`, and `djlint`. They are harness/environment-provided binaries when a test config uses them; the executable invokes but does not install them.

## Spec 25

### MD001 and MD003: heading hierarchy and style

MD001 flags a heading whose level is more than one deeper than the preceding actual heading, e.g. H1 followed by H3. Message: `Expected heading level 2, but found heading level 3`, located at the heading marker. Fix reduces it to the next allowed level while preserving text, indentation, attributes and Unicode. The first heading establishes the baseline. Headings inside front matter/code/comments are ignored. Setext and ATX headings share the sequence; a seven-hash marker followed by whitespace and mismatched-indentation Setext-like text are not headings. The no-space form beginning with seven hashes has the MD018-specific recovery described in Spec 29.

MD003 has `style`, default `consistent`; values are `consistent`, `atx`, `atx_closed`, `setext`, `setext_with_atx`, and `setext_with_atx_closed`. Consistent chooses the document's prevalent style and prefers ATX on ties. Its diagnostic renders the expected and actual styles as Markdown syntax rather than configuration enum names. Converting a Setext H1 to ATX, when diagnosed, says `Heading style should be # Heading, found Heading (underlined with =)`. With `style="atx_closed"`, an open ATX heading says `Heading style should be # Heading #, found # Heading`. With `style="setext"`, an ATX H2 produces a two-line message whose text is exactly `Heading style should be Heading\n-------, found # Heading`. Closed ATX means matching opening and closing hash counts with one separating space. Mismatched trailing counts are ordinary ATX. Setext is valid only for levels 1–2; pure `setext` and hybrid modes fall back to ATX for higher levels, and the closed hybrid uses closed ATX at levels 3–6. One observed conversion is not implemented: with `[MD003] style="atx"`, the document `Title\n=====\n` is clean, `check --fix` returns 0, and the two lines remain unchanged rather than becoming `# Title\n`. Other offered fixes preserve heading text/Unicode/custom IDs and up-to-three-space indentation, emit a minimum one-character underline whose visible width follows the heading text where required, and are idempotent.

## Spec 26

### MD004, MD005, and MD007: unordered-list markers and indentation

MD004 requires consistent unordered markers. `style="consistent"` chooses the prevalent `-`, `*`, or `+` and prefers dash on ties; explicit `dash`, `asterisk`, `plus`, and `sublist` are supported. `sublist` cycles marker by depth. Default `after-marker=1`. Flag each mismatching marker (including mixed markers at a nesting level) with wording such as `List marker '*' does not match expected style '-'`; fix only the marker. Do not mistake emphasis, thematic breaks, escaped markers, code, version numbers, or nested marker text for list items.

MD005 enforces the same indentation for sibling items and top-level column 0. Infer an established increment/text alignment (including 2/3/4 spaces, ordered-parent marker width, task boxes and blockquote prefix) and report `Expected indentation of X spaces, found Y`; fix leading whitespace. It must handle deep/mixed lists and continuation lines without conflating nesting levels.

MD007 enforces unordered nesting. Options: `indent=2`, `start-indented=false`, `start-indent=2`, `style="text-aligned"` (default) or `fixed`. Text-aligned puts a child under the parent's content start; fixed uses configured increments. Supplying `indent` alone selects fixed behavior; explicitly combining a custom indent with text-aligned is warned/validated because text alignment ignores it. Bullets under variable-width ordered markers remain text-aligned. `start-indented` permits/configures the first depth. `Expected X spaces for indent depth D, found Y` is fixed by changing leading whitespace while preserving blockquotes, ordered markers, task checkboxes, content continuations and Unicode.

## Spec 27

### MD009–MD012: trailing space, tabs, reversed links, and blank lines

MD009 flags trailing spaces. On a line containing non-whitespace content, the message is `N trailing spaces found`, where N is the run length. A whitespace-only line uses the special exact message `Empty line has trailing spaces`, regardless of run length, located at column 1. Options are `br-spaces=2`, `strict=false`, `list-item-empty-lines=false`. In non-strict mode exactly `br-spaces` trailing spaces that intentionally form a hard line break are allowed; other trailing runs are removed/reduced appropriately. Strict removes all. Respect the empty-list-line option. Do not alter spaces inside code, and preserve CRLF style. Fix removes only the offending suffix.

MD010 flags hard tabs outside exempt literal contexts and replaces each with enough spaces using `spaces-per-tab=4` and tab-stop-aware columns. Consecutive tabs form one finding per consecutive group, at the first tab's source column. In nonempty content, a one-tab alignment group says `Found tab for alignment, use spaces instead`, while a group of N tabs says `Found N tabs for alignment, use spaces instead`; for example, two adjacent tabs after `author:` produce one finding at column 8 with `Found 2 tabs for alignment, use spaces instead`. Consecutive leading tabs on a nonempty line likewise form one finding at column 1 and use `Found N leading tabs, use S spaces instead`, where `S = N * spaces-per-tab`; a single leading tab says `Found leading tab, use 4 spaces instead`.

A whitespace-only line has its own message family. A consecutive group of one tab says `Empty line contains tab`, and a group of N tabs says `Empty line contains N tabs`; separated groups on the same whitespace-only line are separate findings, each using this family. Thus the five-line input `\t\n\t\t\n\t\t\t\n\t \t\n \t \t \n` produces seven findings: singular, `2 tabs`, `3 tabs`, then four singular group messages. A leading tab that supplies the indentation for what Markdown would otherwise parse as an indented code block is not exempt. Tabs within fenced code and other configured code contexts remain exempt; list indentation tabs are handled consistently.

MD011 recognizes reversed link syntax of the form `(DESTINATION)[TEXT]`, reports it at the opening `(`, and safely swaps the two parts. Its exact message is `Reversed link syntax: use [TEXT](DESTINATION) instead`, and the finding is fixable. Destination classification includes explicit protocols such as `https:`, `http:`, `ftp:`, `mailto:`, and `xmpp:`, absolute paths, `./` and `../` relative paths, filenames, and even ambiguous one-word destinations. Link text may contain multiple words. Thus `(https://example.com)[click]`, `(/absolute/path)[text]`, `(url)[this is text]`, and `(word)[another]` respectively name `[click](https://example.com)`, `[text](/absolute/path)`, `[this is text](url)`, and `[another](word)` in their messages. Footnote references/definitions and wiki links such as `[[Wiki Page]]` and `[[Target|Display]]` are not reversed links and produce no MD011 finding.

MD012 allows at most `maximum=1` consecutive blank lines. Between content, each excess line yields `Multiple consecutive blank lines between content`; fenced-code and YAML/front-matter body blanks remain exempt. Outer excess blanks are not exempt: the corresponding messages are `Multiple consecutive blank lines at start of file` and `Multiple consecutive blank lines at end of file`. Once an outer run violates the limit, fixing trims that run completely: an input beginning `\n\nLine\n` becomes `Line\n`, and an input ending `Line 2\n\n\n` becomes `Line 2\n`. Blockquote semantics must not create false positives. Combined MD009/MD012 fixes must not leave whitespace-only phantom blanks.

## Spec 28

### MD013: line length and reflow

MD013 defaults: `line-length=80`, `code-blocks=true`, `tables=false`, `headings=true`, `paragraphs=true`, `strict=false`, `reflow=false`, `reflow-mode="default"`, `length-mode="visual"`, plus optional `abbreviations`. With `reflow=false`, a violation message is `Line length ACTUAL exceeds LIMIT characters`, located at the first over-limit column and not marked fixable. With `reflow=true`, a reflowable ordinary paragraph in the default/normal wrapping case instead reports at column 1 with `Line length exceeds LIMIT characters`, has a concrete fix, and therefore carries `[*]` in text output and contributes to the automatic-fix suggestion. For example, a reflowable line longer than a configured limit of 200 reports exactly `Line length exceeds 200 characters` at column 1. A reflowable over-limit list-item line also reports at column 1 and is fixable, but retains the measured length in its message: `Line length ACTUAL exceeds LIMIT characters`. `sentence-per-line` has a single-sentence exception: an over-limit line containing only one sentence is not wrapped merely to meet the width. It uses the measured diagnostic `Line length ACTUAL exceeds LIMIT characters` at column `LIMIT+1`, has no concrete fix or `[*]`, and does not contribute to the fix suggestion. The observed 104-character line at limit 80 therefore reports `Line length 104 exceeds 80 characters` at column 81. A line containing N sentences instead reports at column 1 as `Line contains N sentences (one sentence per line required)`; with reflow enabled this finding is fixable and carries `[*]`. `line-length=0` disables warnings. Visual width treats CJK and emoji as terminal-width two and combining marks correctly; a tab advances to the next four-column tab stop when computing both total visual line length and the first over-limit column. For example, a tab-expanded line of visual width 88 at the default limit reports `Line length 88 exceeds 80 characters` at column 81. `chars` counts Unicode characters and `bytes` UTF-8 bytes.

Skip tables when `tables=false`, code blocks when false, headings/paragraphs when their toggle is false, front matter, HTML comments/blocks, reference definitions and thematic-rule syntax. Non-strict mode entirely exempts blockquote prose, including an otherwise breakable long blockquote paragraph. With `strict=true`, that paragraph is measured normally; for example, a 156-character quote at the default limit reports `Line length 156 exceeds 80 characters` at column 81. Non-strict mode can also exempt an otherwise unbreakable URL/autolink/link destination and lines whose only excess is an unavoidable Markdown construct, but it does not exempt an ordinary long word outside a blockquote. For example, with `line-length=20`, an ordinary paragraph consisting of 100 `x` characters produces `Line length 100 exceeds 20 characters` at column 21 and exits 1 even though `strict=false`; strict additionally reports the URL/construct cases. Inline Markdown must not distort visible/selected length or columns.

With `reflow=true`, fix wraps paragraphs at whitespace without exceeding the configured width when possible. Preserve inline code, emphasis/strong/strikethrough, links/images and titles, entities, escaped punctuation, Unicode/emoji, hard breaks, paragraph boundaries, list/blockquote continuation prefixes, indentation and explicit Markdown constructs. Never reflow headings, tables, code, reference definitions, front matter or HTML blocks. Do not break an indivisible URL/long token. The default mode wraps minimally; `normalize` joins and rewraps existing soft line breaks; `sentence-per-line` splits sentences so each sentence begins on its own line (then wraps it if necessary), recognizing built-in abbreviations `Mr`, `Mrs`, `Ms`, `Dr`, `Prof`, `Sr`, `Jr`, `i.e`, `e.g` plus configured forms with optional periods, decimals, ellipses, initials, quotes/brackets and both ASCII `.!?` and CJK `。！？` boundaries. The CJK terminator stays at the end of the preceding sentence. For example, `这是第一个句子。这是第二个句子！这是第三个句子？` becomes those same three sentences on three lines without altering any character other than the two inserted line breaks; Japanese ideographic-full-stop-separated sentences split the same way. A CJK character can also begin the next sentence after an ASCII terminator; `English sentence. 日本語の文章が続く。` becomes those two sentences on separate lines rather than requiring an ASCII uppercase letter after the period.

Sentence-final inline closing-marker runs stay with the preceding sentence, and the line break is inserted after the marker even when the following text is adjacent. Thus `这是句子。~~~next sentence` becomes `这是句子。~~~\nnext sentence`, and `这是句子。***   next` becomes `这是句子。***\nnext`. Emphasis or strikethrough inside a CJK sentence remains intact, including ordinary spaces before its opening marker: `这是 **第一句**。这是 *第二句*。这是 ~~第三句~~。` becomes the same three marked-up sentences on three lines.

## Spec 29

### MD014 and MD018–MD021: commands and ATX spacing

MD014 (`commands-show-output`) inspects shell-like fenced blocks. With `show-output=true` (default), a sequence made only of prompt-prefixed commands such as `$ command` and no demonstrated output is reported as incomplete; blocks that contain corresponding non-command output pass. Ignore non-shell blocks, comments, blank-only blocks and escaped/literal dollar uses. The safe fix does not invent output: it removes the `$ ` prompt prefix from every command in that prompt-only block. Thus `$ ls -l`, `$ pwd`, and `$ echo hello` become `ls -l`, `pwd`, and `echo hello`; leading indentation before each prompt is retained. The block produces one finding at its first command, with a message such as `Command 'ls -l' should show output (add example output or remove $ prompt)`.

MD018 (`no-missing-space-atx`) flags `#Heading` through `######Heading` and inserts one space. The location is immediately after the recognized marker, so `#Bad` reports at column 2 rather than column 1. Its message names the complete opening marker as `No space after MARKER in heading`: `#Missing` reports `No space after # in heading`, while `###Missing` reports `No space after ### in heading`. A run of seven hashes with no following space is recovered as a six-hash marker whose content begins with `#`: `#######Not a heading` reports at column 7 as `No space after ###### in heading` and fixes to `###### #Not a heading`. MD018 ignores emoji keycap hashtags, CSS/HTML/comments/closed front matter, escaped hashes, indented code, and numeric `#123` lines when `[MD018] magiclink=true`. Under Obsidian, valid tags (`#todo`, nested `#project/active`) are not headings, while a genuine malformed heading is. An MD018-repairable first line such as `#Missing space after hash` counts as the document's initial top-level heading for MD041, so it receives MD018 but not an additional MD041 finding. MD019 (`no-multiple-space-atx`) reduces two or more post-marker spaces to one. Its message includes the actual space count and the complete marker. Thus the three lines `#  Heading 1`, `##   Heading 2`, and `###    Heading 3` produce three findings whose messages are respectively `Multiple spaces (2) after # in heading`, `Multiple spaces (3) after ## in heading`, and `Multiple spaces (4) after ### in heading`.

MD020 (`no-missing-space-closed-atx`) requires one space after the opener and before a valid closing hash run. Its exact diagnostic is `Missing space before CLOSER at end of closed heading`, where `CLOSER` is the complete trailing hash run; a heading ending in a single closing hash therefore says `Missing space before # at end of closed heading`.

MD021 (`no-multiple-space-closed-atx`) reduces multiple inner spaces at either end to one and emits exactly one finding per affected heading, never one finding per bad boundary. When both boundaries are bad, combine their counts in that one message: `#  One  #` says `Multiple spaces (2 at start, 2 at end) inside hashes on closed heading (with # at start and end)`. A start-only example says `Multiple spaces (2) after ## at start of closed heading`; an end-only example says `Multiple spaces (2) before ### at end of closed heading`. Consequently, three affected headings produce three MD021 findings even when two boundaries on a heading need correction. Closed style applies only when the trailing run is syntactically a close; preserve escaped/content hashes and correct opening/closing counts. All four rules retain up-to-three-space heading indentation and only alter the targeted interior space.

## Spec 30

### MD022–MD026: heading spacing, uniqueness, title, and punctuation

MD022 requires blank lines around headings. Defaults are `lines-above=1`, `lines-below=1`, `allowed-at-start=true`; above/below may instead be six-element H1–H6 arrays and `-1` means inherit the scalar default. No above line is required at document start and no below line at document end. Setext's text+underline is one heading unit. A list beginning on the line immediately after a heading is a compatibility exception: MD022 does not add a missing-below-heading finding; MD032 reports `List should be preceded by blank line` for that boundary instead. Do not add blank lines inside list/blockquote structure incorrectly. Messages use grammatical number: `Expected 1 blank line above heading` and `Expected 1 blank line below heading` for one, or `Expected N blank lines above/below heading` for other counts. Fix inserts/removes to the exact requirement.

MD023 requires a heading at the left edge and fixes leading spaces/tabs. It applies to otherwise valid ATX headings but does not turn four-space code or arbitrary `#` text into headings.

MD024 flags duplicate normalized heading content according to `siblings-only=true` and `allow-different-nesting=false`. By default, compare sibling headings at the same structural parent, reducing false positives for repeated subsections in separate chapters; configured modes broaden/narrow this. Normalize inline formatting while retaining meaningful Unicode/text and account for explicit IDs. Report duplicates without guessing replacement text, although the catalog exposes fix capability metadata for compatibility.

MD025 permits only one heading at configured `level=1`. Defaults also include `front-matter-title="title"`, `allow-document-sections=false`, and `allow-with-separators=false`. Every extra title uses the exact diagnostic `Multiple top-level headings (level 1) in the same document`. For an ATX H1, locate it at the first content character after `# ` (normally column 3), rather than at the hash; for a Setext H1, locate it at the first character of the heading-text line. The safe demotion makes the text diagnostic end in `[*]`. ATX and Setext titles normally both participate when detecting an extra title. There is one compatibility exception: a document whose two level-1 headings are both Setext `=` headings and which has no ATX level-1 heading produces no MD025 finding and exits clean when no other rule is violated. If an ATX level-1 heading is present, a Setext level-1 heading can still be the extra title and is reported. A matching YAML title, using the configured `front-matter-title` field name, counts as the document title and makes a body H1 extra.

With `allow-document-sections=true`, later H1s matching the following case-insensitive vocabulary are exempt without requiring a thematic separator: `appendix`, `appendices`, `reference`, `references`, `bibliography`, `index`, `indices`, `glossary`, `glossaries`, `conclusion`, `conclusions`, `summary`, `executive summary`, `acknowledgment`, `acknowledgments`, `acknowledgement`, `acknowledgements`, `about`, `contact`, `license`, `legal`, `changelog`, `change log`, `history`, `faq`, `frequently asked questions`, `troubleshooting`, `support`, `installation`, `setup`, `getting started`, `api reference`, `api documentation`, `examples`, `tutorials`, and `guides`. A heading qualifies when its lowercased text begins with an indicator or contains an indicator preceded by a space. Suffixes and punctuation therefore remain eligible: examples that pass include `Appendix: Details`, `Appendix A`, `References (2024)`, `About This Project`, `Contact Us`, and `API Reference Guide`. This exemption composes with `allow-with-separators=true`; `References` and `Appendix` remain exempt while an unrecognized `Random Title` is still the sole finding. Thematic breaks may independently delimit titles when the separator option is enabled. A four-space-indented `#` inside an indented code block is not a title. A safe fix demotes later H1s to the hierarchy-appropriate level while preserving text.

MD026 strips configured terminal punctuation (default `punctuation=".,;:!"`) from heading text, repeatedly if needed, before optional closing hashes/attribute lists. Question marks are allowed by default. Colons/question-like punctuation inside or not at the final semantic character are untouched. Fix preserves closing hashes and custom IDs.

## Spec 31

### MD027–MD032: blockquotes, ordered lists, marker spacing, and surrounding blanks

MD027 permits exactly one space after every `>` quote marker that is followed by nonempty quote content and reports `Multiple spaces after quote marker (>)` for extras. A quote-marker line followed only by two or more spaces is also a violation: `>  \n` reports at line 1, column 3 even though it has no non-whitespace content. A bare `>` is valid. Every finding is located at the first excess separator space in the original line, so any run of two or more spaces after a top-level marker reports at column 3; for a directly nested `>>  text` marker it reports at column 4. Fixing a nonempty quote leaves exactly one separator space, while fixing a whitespace-only quote-marker line removes all separator whitespace and leaves bare `>`. A single tab that acts as separator where valid, list continuation indentation after the quote, fenced code and nested combinations are treated structurally; content inside an embedded fenced block is not examined as quote-marker spacing. Fix preserves every quote marker and nesting level.

MD028 detects an unmarked blank line between consecutive blockquote segments because it ambiguously splits/joins quotes. Its exact message is `Blank line inside blockquote (level N)`, where N is the quote nesting level; a top-level example says `Blank line inside blockquote (level 1)`. A blank quote line written `>` is valid. Fix prefixes the intervening blank with the correct nested quote marker. Ordinary blank space separating a quote from unrelated content is not flagged, so a blank between a final quote segment and an ordinary paragraph does not create a second finding.

MD029 defaults to `style="one-or-ordered"`: each CommonMark-parsed ordered-list group may use all `1.` markers or the sequential series inferred for that group. CommonMark grouping is authoritative, so visually contiguous top-level markers do not necessarily form one sequence. In particular, `1.`, `2.`, `10.`, and `100.` on successive item lines produce no MD029 finding and return clean when MD029 is the only enabled rule; likewise, `1.`, `2.`, `3.`, `10.` does not produce a finding for `10.`. The two-line document `1. first\n3. second\n` is also clean under MD029; `check --fix` returns 0 and leaves both markers unchanged. A following list without a separating blank can still independently produce MD032. Other accepted style values are `one`/`one-one`, `ordered`, `ordered0`, and document-wide `consistent`. In the observed `style="one"` case, the exact document `2. first\n2. second\n` is accepted unchanged: a quiet MD029-only check emits nothing and exits 0. It must not be diagnosed on the assumption that `one` requires literal `1.` markers. Ordered mode honors each parsed group's start number; ordered0 is zero-based; nested lists have independent sequences. Fix changes numeric prefixes without altering delimiter, text, indentation or code/version-like numbers when the parser reports an MD029 violation.

MD030 enforces marker-to-content spacing. Defaults are `ul-single=1`, `ol-single=1`, `ul-multi=1`, `ol-multi=1`; select single/multiline and ordered/unordered setting per item. Message: `Spaces after list markers (Expected: X; Actual: Y)`, located immediately after the marker; fix changes that run. Empty items, tasks (`- [ ]`/`- [x]`), ordered widths, blockquotes and nested lists must be recognized.

MD031 requires fenced blocks to be surrounded by blank lines, with `list-items=true` by default. Its directional messages are exactly `No blank line before fenced code block` and `No blank line after fenced code block`. Document boundaries are exempt. When nested, insert a blank continuation line carrying the necessary list/blockquote prefix. Do not flag adjacent fences incorrectly, content inside a fence, or an indented block as a fence.

MD032 requires blank lines before the first and after the last item of a list, except at document boundaries or adjacent compatible list structure. `allow-lazy-continuation=true` permits an unindented paragraph that CommonMark treats as continuation. This applies inside blockquotes and nested blockquotes too: when only the blank before such a list is missing and following quote text is its lazy continuation, report exactly one `List should be preceded by blank line` finding, not a second after-list finding. With `allow-lazy-continuation=false`, diagnose the continuation line itself at its first column with the exact message `Lazy continuation line should be properly indented or preceded by blank line`. This finding is fixable: indent the continuation to the list item's content column rather than inserting a blank line. For `- Item 1 with long\ntext that continues`, the fix is exactly `- Item 1 with long\n  text that continues`.

Nested lists, task lists, blockquotes and fenced children can remain one structural list, but an adjacent top-level ordered-to-unordered or unordered-to-ordered transition starts a separate list even without an existing blank line. The shared transition therefore produces `List should be followed by blank line` on the last item of the first list and `List should be preceded by blank line` on the first item of the second list. A fix inserts one blank line at that boundary, satisfying both findings; special characters, inline code, and links in item content do not change this treatment. The usual messages are exactly `List should be preceded by blank line` and `List should be followed by blank line`; their fixes insert a correctly prefixed blank.

## Spec 32

### MD033–MD039: HTML, URLs, rules, emphasis, code spans, and links

MD033 flags inline/block HTML elements outside code and dialect constructs. Its exact message is `Inline HTML found: TAG`, where `TAG` is the complete source spelling of the reported opening or self-closing tag, including its attributes and malformed source spelling; for example, an opening tag with an unterminated quoted attribute written `<div class="test>` is reported with that same text. A tag source may span lines: `<div class="test\ncontinued>` produces the two-line message `Inline HTML found: <div class="test\ncontinued>` and remains one finding located at its opener. A matched opening/closing pair is one finding located at and naming the opening tag (for example, `<b>inline HTML</b>` produces one `Inline HTML found: <b>` finding), not separate findings for both tags. Nested ordinary HTML elements can each produce a finding at their own opening tag, while a self-closing/void form such as `<br/>` produces one finding at that tag. SVG and MathML containers are treated as opaque foreign-content elements for this rule: `<svg ...><circle .../></svg>` reports the outer `<svg ...>` only, not the nested `<circle .../>`, and `<math><mi>...</mi></math>` reports `<math>` only, not `<mi>`. Consequently the observed document containing outer `svg`, `math`, and `canvas` elements reports those three outer opening tags rather than adding findings for the SVG `circle` or MathML `mi`. `<hr>`, `<hr/>`, `<hr />`, and `<hr class="special" />` are four independently reportable source spellings. Under `--flavor mkdocs`, a container bearing either a bare `markdown` attribute or `markdown="1"`, together with its matching close, is Markdown-enabled dialect syntax and is excluded from MD033; an otherwise identical plain container is still reported. Defaults: `allowed-elements=[]`, `disallowed-elements=[]`, `fix=false`, `br-style="trailing-spaces"`; aliases `allowed`/`disallowed` work. Allowed mode exempts listed tag names case-insensitively, including both sides of a matched pair. A nonempty disallowed list switches to only-these mode; token `gfm` expands to `title, textarea, style, xmp, iframe, noembed, noframes, script, plaintext`. HTML comments and entities are not tags, and angle-bracket email addresses and URL autolinks are not HTML elements. With opt-in `fix=true`, convert only lossless simple forms: `em/i`→emphasis, `strong/b`→strong, `code`→inline code, simple `a`/`img` with href/src/alt/title→Markdown, `br`→two spaces or backslash newline, and `hr`→`---`. Attributes/entities or semantic/block HTML that cannot be safely represented stay unchanged. Despite this opt-in, the catalog's `--fixable` filter excludes MD033.

MD034 finds bare `http://`, `https://`, and `ftp://` URLs, along with other supported extended GFM URLs, outside existing links/autolinks, destinations, code, HTML and comments; message is `URL without angle brackets or link formatting: 'URL'`. Thus bare `ftp://files.server.com/data` and a bracketed-IPv6 URI such as `ftp://[2001:db8::1]/file.txt` are each reported and fixable just like HTTP URLs. Standard flavor's extended recognition also reports bare email addresses with `Email address without angle brackets or link formatting: 'ADDRESS'` and an XMPP URI such as `xmpp:user@example.com` with `URL without angle brackets or link formatting: 'xmpp:user@example.com'`. Correctly trim adjacent sentence punctuation and balance URL parentheses while retaining query/fragment/unicode. Fix wraps the exact URL or address in `<...>`.

MD035 enforces thematic-break style, with built-in default `style="consistent"`; accepted concrete styles include `---`, `***`, `___`, `- - -`, and `* * *`. Consistent mode adopts the document's prevalent thematic-break syntax rather than imposing `---`, so a document whose only break is `***` is clean and an MD065-only spacing fix preserves that marker. When different styles tie, use the one that appears first; for example, `---` followed later by `***` reports the latter as `Horizontal rule style should be "---"`. Recognize valid longer runs and whitespace while not treating Setext underlines, list markers, code or front-matter delimiters as breaks. Once the parser recognizes a marker as a thematic break, a missing required blank line does not reclassify it: report only the applicable MD065 boundary finding at that line, not MD035 or MD036 merely because the boundary is missing. The ATX-heading adjacency exception that is not exposed as a thematic break is specified under MD065. Fix replaces only the thematic marker.

MD036 detects a standalone line whose whole semantic content is emphasis/strong and looks like a heading. Its diagnostic includes the unwrapped emphasized source text in single quotes: `**This looks like a heading**` reports exactly `Emphasis used instead of a heading: 'This looks like a heading'`. This applies to single/double asterisk and underscore forms. Terminal punctuation in `punctuation=".,;:!?"` suppresses it. Default `fix=false`; with `fix=true`, use `heading-style="atx"`, `heading-level=2` (validated 1–6), remove emphasis markers and create that heading while preserving indentation/text. Without opt-in, do not mutate it.

MD037 removes spaces immediately inside valid emphasis/strong delimiters (`*`, `_`, doubled forms) while respecting escapes, intraword underscores, unmatched markers, nested emphasis and code. Its diagnostic is `Spaces inside emphasis markers: "SOURCE"`, where `SOURCE` is the complete offending source including its delimiters; for example, `* wrong spaces *` produces exactly `Spaces inside emphasis markers: "* wrong spaces *"`. Emit one MD037 finding for each offending emphasis/strong construct, not one for each spaced boundary. For example, `Text with * bad * here` yields one finding, `** text ** and **text ** and ** text**` yields three, and `Here is * text * and _ text _ in one line` yields two. Ignore the same delimiter text inside a fenced code block. An immediately adjacent valid Kramdown span IAL exempts its construct: in the six-line sequence `Good: *text*{:.class}`, `Bad: * text *`, `Good: **bold**{:#id}`, `Bad: ** bold **`, `Good: _italic_{:attr="value"}`, and `Bad: _ italic _`, only lines 2, 4, and 6 yield findings. A non-IAL such as `{not-ial}`, or whitespace before `{:.class}`, does not exempt the preceding construct.

In the default flavor, MD037 also treats dollar-delimited math as protected syntax. It ignores asterisks inside inline `$...$` and inline/display `$$...$$`, including empty `$$`, whitespace-only `$ $`/`$  $`, multiple math spans on one line, spans beginning or ending at line boundaries, and a span occupying a full line; protection never extends past the closing delimiter or across a newline. An unmatched opening `$` does not protect the rest of its line: `This has $unclosed math and * bad emphasis * here.` still produces one finding for `* bad emphasis *`. Consequently, `Empty $$ here and * bad emphasis *.` yields one finding for `* bad emphasis *`; placing that line before `Mid-line $p * q$ and then * bad emphasis *.` yields exactly two findings, one on each line. `Math $a * b$ and $c * d$ and $$ empty and * bad *.` yields only the final `* bad *` finding. A three-line sequence `Inline $x * y$ math.`, `Display $$a * b$$ math.`, and `And * bad emphasis *.` likewise yields only the line-3 finding.

MD038 does the same for inline code span delimiters, but preserves the single-padding-space convention needed to represent code whose content begins/ends with backtick or space; consequently ``Use ` code ` now.`` is clean and unchanged when MD038 is the only enabled rule. Ignore fenced blocks and flavor-specific code-like constructs. Code spans inside table cells are still ordinary inline code for this rule: in ``| ` code` | `code ` |``, each offending span produces one `Spaces inside code span elements` finding at its opening backtick, while MD064 does not separately report the spaces inside those spans. MD039 removes leading/trailing whitespace inside link text/image-alt brackets, including Unicode and nested/escaped brackets, but not whitespace intrinsic to inline code; empty text is left for MD042. MD039 likewise emits one finding per offending link or image, not per whitespace boundary: `[ link ](url) and [ another ](url) in one line` yields two findings, while an identical link inside a fenced code block is ignored. Each rule produces precise, idempotent range fixes.

## Spec 33

### MD040–MD043: fenced languages and document structure

MD040 flags every fenced opener whose info string is empty/whitespace with the exact message ````Code block (```) missing language````. The message uses three backticks even when the actual fence is tildes. This finding always has a concrete fix: append the literal language `text` to the actual opening fence (for example, replace `` ``` `` with `` ```text `` and `~~~` with `~~~text`), so text output includes `[*]` and the automatic-fix suggestion. In standard flavor, any nonempty first token, including numeric or unknown labels, satisfies the basic requirement. MkDocs flavor recognizes a leading `title="..."` token as an attribute rather than a language, so a fence whose only info token is that title still receives the missing-language finding at the opener. Quarto's code-chunk form such as `````{python}````` supplies the `python` language and passes. Defaults are `style="disabled"`, empty `preferred-aliases`, `allowed-languages`, and `disallowed-languages`, and `unknown-language-action="ignore"`. Linguist data resolves labels case-insensitively. With `style="consistent"`, all aliases of a canonical language use the prevalent spelling (tie deterministic), unless its canonical-name preferred alias overrides it; fix replaces only the label. A nonempty allow-list rejects all other canonical languages; otherwise deny-list rejects its members. Unknown action `warn`/`error` produces corresponding severity. Info-string attributes after the language are preserved.

MD041 requires the first semantic document content to be a heading at `level=1` by default. Its exact default diagnostic is `First line in file should be a level 1 heading`. Skip comments and leading `---` YAML front matter, but do not skip a BOM. Also skip a leading badge preamble: a line composed entirely of one or more complete Markdown image badges is exempt, and each badge may optionally be wrapped in a complete link. Multiple badges on one line and linked badges are therefore allowed before the heading. Incomplete image syntax such as `![badge](badge.svg` and a linked badge with an incomplete outer link such as `[![badge](badge.svg)](https://example.com` are not badge preamble; each is semantic first content and produces that MD041 diagnostic at line 1, column 1 even when a valid H1 follows. Reference-definition lines and Python-Markdown abbreviation-definition lines such as `*[HTML]: Hyper Text Markup Language` may coexist with valid leading badge lines and are skipped while seeking the heading; arbitrary mixtures of blank lines, HTML comments, those definitions, and complete badge-only lines remain preamble. Ordinary text on a badge line makes the line semantic content and produces MD041. An HTML heading at the configured level also satisfies the rule, including a single-line heading with attributes or nested inline tags and a properly closed multiline heading with attributes or arbitrarily nested tags. Thus `<h1 class="title" id="main">Title</h1>`, `<h1><strong>Bold</strong> Heading</h1>`, and `<h1>\nProject\n</h1>` satisfy the default level, while an otherwise identical `<h2>` produces the diagnostic at line 1.

In MkDocs flavor only, one or more leading invisible-anchor lines of the forms `[](){ #anchor }` and `[](){: #anchor }` are likewise preamble and are skipped before the required heading, including when combined with front matter or comments. The same anchor line is semantic first content in `standard` flavor and therefore receives the MD041 diagnostic at line 1.

For MD041 specifically, leading TOML `+++` and JSON-object front matter are not skipped and do not satisfy the rule: even when they contain a title and are protected from unrelated rules, MD041 reports at line 1. Defaults include `front-matter-title="title"`, `front-matter-title-pattern="^(title|header):"`, and `fix=false`; a matching nonempty YAML front-matter title satisfies the rule. With the default `fix=false`, the diagnostic has no fix marker and `--fix` leaves the file unchanged.

With opt-in `fix=true`, an existing wrong-level ATX first heading is rewritten to the configured level: `## Project\n` becomes `# Project\n`, and the original diagnostic ends `[fixed]`. The fixer reconstructs the preamble and moves that first heading immediately after closed YAML front matter, so this operation intentionally changes surrounding blank lines rather than preserving them in place. For the exact input `---\nauthor: John Doe\ndate: 2024-01-01\n---\n\n## Wrong Level\n\nContent`, with front-matter-title checking disabled, the fixed bytes are `---\nauthor: John Doe\ndate: 2024-01-01\n---\n# Wrong Level\n\n\nContent`: the blank before the heading is removed and two blank lines precede `Content`. The missing terminal newline is preserved; the same input and output with one terminal newline also retain it.

An eligible wrong-level Setext heading is also converted to ATX while changing its level and removing its underline. With level 1, `Wrong Level\n-----------\n\nContent` becomes exactly `# Wrong Level\n\nContent`, and the diagnostic is `[fixed]`; terminal-newline presence is preserved. Content before a later heading, a document with no heading, and a wrong-level HTML heading are not automatically rewritten or prefixed because doing so is not a safe deterministic correction. Empty documents pass.

MD042 flags a Markdown link whose destination is empty or whitespace-only. Its exact diagnostic is `Empty link found: SOURCE`, where `SOURCE` is the complete offending link source, preserving punctuation, Unicode, angle brackets, ampersands, and quotes. For example, `[link with <brackets> & "quotes"]()` produces exactly `Empty link found: [link with <brackets> & "quotes"]()`. This same canonical message is carried verbatim as the JSON/JSON-lines `message`, SARIF `message.text`, GitLab `description`, and the decoded JUnit failure message; only each serialization's required JSON/XML escaping changes its encoded bytes. Empty link text by itself is not an MD042 violation (images are handled by MD045). Thus `[Link]() and []() and [](url)` produces exactly two MD042 findings, for `[Link]()` and `[]()`; `[](url)` is accepted because its destination is nonempty. Valid fragment/reference/autoref constructs and MkDocs invisible anchor idioms under that flavor are also permitted. Nested parentheses, escaped delimiters, titles and reference links are parsed before deciding emptiness. Do not report an already valid link or code sample. Apply only a safe placeholder/removal fix when one is defined.

MD043 does nothing by default because `headings=[]`. When configured, compare the actual heading sequence with required patterns, ignoring code/front matter. `match-case=false` is default. Literal entries encode both marker level and text; `*` matches zero or more arbitrary headings, `+` one or more, and `?` exactly one. Diagnose missing, unexpected, wrong-level/text and out-of-order headings. Fix only deterministic textual/level mismatches; never discard arbitrary sections.

## Spec 34

### MD044–MD050: names, images, code style, newline, and emphasis styles

MD044 uses configured `names=[]` as correctly cased canonical terms. Match whole words case-insensitively and replace wrong casing with the configured form, including repeated and Unicode names, without matching substrings. Every finding's exact message quotes both the source spelling and configured canonical spelling: `Proper name 'SOURCE' should be 'CANONICAL'`. Thus wrong-case variants respectively produce `Proper name 'javascript' should be 'JavaScript'`, `Proper name 'JAVASCRIPT' should be 'JavaScript'`, and `Proper name 'Javascript' should be 'JavaScript'`; do not replace `SOURCE` in the message with the canonical spelling. Matching also uses the reference's canonical-name variants: periods in a configured name are ignored for comparison, so with `Node.js` configured, both `nodejs` and `node.js` are findings and are replaced with `Node.js`; and the observed Latin accent normalization makes both `cafe` and incorrectly cased `café` match configured `Café` and be replaced with `Café`. Report every occurrence independently and in source order, including multiple proper-name violations on one line. Defaults: `code-blocks=false`, `html-elements=true`, `html-comments=true`; honor them and skip inline code unless explicitly covered. When HTML comments are disabled, their contents are skipped while outside prose retains the same exact message. Visible Obsidian wiki-link text is checked: `[[javascript]]` reports the source spelling at its text column. Preserve plural/punctuation boundaries where appropriate.

MD045 flags inline and reference-style images whose alt text is empty or whitespace, outside code/comments. Message: `Image missing alt text (add description for accessibility: ![description](url))`. Default `placeholder-text="TODO: Add image description"`. With that built-in default, the fixer first tries to derive useful alt text from the destination: take its final usable path component, discard a query and a conventional file extension, turn hyphens and underscores into spaces, capitalize the resulting words, and append ` image`. Thus the observed fixes include `https://example.com/images/user-profile-icon.png` → `User Profile Icon image`, `https://example.com/test_image.jpg` → `Test Image image`, `banner.svg` → `Banner image`, `https://example.com/no-extension` → `No Extension image`, and `https://example.com/photo.png?size=large` → `Photo image`. The same extraction applied to the data destination `data:image/png;base64,iVBORw0KG...` yields `Png;base64,iVBORw0KG image`. If there is no usable component, as for `https://example.com/`, use the literal default placeholder. A nondefault configured `placeholder-text` is always inserted literally instead of deriving from the destination; for example, `CUSTOM ALT` produces `![CUSTOM ALT](https://example.com/user-profile.png)`. The fix changes only the empty `![...]` text and preserves destination/title/reference. Valid Unicode alt text passes.

MD046 enforces `style="consistent"|"fenced"|"indented"` across code blocks. The reference's ordinary default project profile selects `fenced`; consequently a document containing only one indented block still produces one fixable `Use fenced code blocks` finding at that block's first line. The same applies to an all-indented document and to a four-space-indented would-be fence, which is parsed as indented code and reports at line 1, column 1. An explicit `consistent` setting instead selects the prevalent representation. Recognize tabs as indented code, 0–3-space fences, tilde/backtick, and empty blocks. Under `style="fenced"`, every distinct indented block produces its own `Use fenced code blocks` finding and fix: one block has one finding, while two separated indented blocks have two. An unclosed fence is itself an MD046 finding even when it is the document's only code-block style: a backtick opener emits the exact message `Code block opened with '```' but never closed` at the opener and is fixable by appending a matching closing fence after its content. A would-be closing marker followed by non-whitespace content, such as `` ``` trailing ``, is not a closer, so the opener receives that same unclosed-fence diagnostic. Convert indented to a safe fence and fenced to indentation only when semantics can be preserved; retain info strings/content/nesting. MD047 ensures every nonempty text file ends with exactly one newline, removing extras or adding a missing one; empty input remains valid/empty where tested, and CRLF files use their established ending.

MD048 enforces `style="consistent"` (default, backtick tie preference), `backtick`, or `tilde` for fenced blocks. Change both opener and matching closer, preserve length/indent/info, and lengthen the replacement fence if its content contains a colliding run. MD049 likewise enforces emphasis `consistent`/`asterisk`/`underscore`, preferring asterisk on ties; MD050 does so for strong emphasis. MD049's diagnostic names the literal preferred and found delimiters: when asterisk is selected, `_different emphasis_` reports exactly `Emphasis should use * instead of _`. Both rules parse nested/escaped/intraword syntax, leave code alone, change paired delimiters only, and avoid converting a delimiter when it would change word-boundary semantics.

## Spec 35

### MD051: heading anchors and workspace lookup

MD051 validates fragment-only links against headings/custom anchors in the current document. A cross-file fragment is handled using the workspace index when available and otherwise is not mistaken for a same-file fragment. The path/fragment boundary is lexical: ordinary paths with a nonempty extension, extensionless alphanumeric/Unicode names such as `somefile` or `文档`, hidden names such as `.hidden`, URL/network/absolute paths, and encoded filenames remain cross-file destinations. In contrast, a pre-fragment path ending in an empty extension such as `file.` or containing a non-path character such as `file@name` is treated as ambiguous and its fragment is validated against the current document. Therefore two occurrences of `file.#section` each produce an MD051 finding when `section` is absent, while `somefile#section` and `.hidden#section` do not. Likewise `file@name#section` produces a finding, but `文档#section` does not. A destination containing literal unencoded spaces is not parsed as a Markdown link and produces no MD051 finding; for example, `#multiple   spaces` is ignored rather than normalized and validated.

Percent-decode valid URL encodings and compare generated Markdown heading anchors case-insensitively. Explicit HTML `id` anchors are case-sensitive: for `<div id="CamelCase">`, `#CamelCase` matches but `#camelcase` does not. If one HTML element repeats the `id` attribute, only the first value is registered; a later value on that same element is not a valid target. Accept explicit heading attributes/HTML named anchors supported by the flavor, and assign duplicate heading suffixes `-1`, `-2`, etc. In the default `standard` flavor, all custom-ID forms listed in Spec 20 are active for MD051, including inline IDs, extended class/attribute lists, and next-line IDs. A custom ID is an additional valid anchor rather than a replacement for the generated one: `# Normal Heading {#custom-id}` is reachable through both `#custom-id` and `#normal-heading`. A missing target is located at the opening `[` of the link (column 1 when the link begins the line) and uses `Link anchor 'FRAGMENT' does not exist in document headings` under the default GitHub anchor style as well as Kramdown; for example, `[link](#nonexistent-id)` reports exactly `Link anchor '#nonexistent-id' does not exist in document headings`. Thus a line beginning `[bad](#specialcharacters)` reports at column 1, not at the fragment inside the destination. A unique close anchor may be suggested/fixed, otherwise do not guess. Selecting `[MD051] anchor-style = "kramdown"` activates Kramdown ID generation even while the global Markdown flavor remains `standard`. Under that style, `# Test with underscores` followed by `[link](#test_with_underscores)` reports exactly `Link anchor '#test_with_underscores' does not exist in document headings`. Anchor style defaults to `github` and also supports `kramdown`, `kramdown-gfm`, `pandoc`, and `bitbucket`:

- GitHub lowercases; strips Markdown formatting and most punctuation; converts each space to `-`; preserves Unicode, underscores and consecutive hyphens. Examples: `Hello World`→`hello-world`, `respect_gitignore`→`respect_gitignore`, `The End - yay`→`the-end---yay`, `Café au Lait`→`café-au-lait`, `你好世界` stays `你好世界`.
- Kramdown lowercases, retains only its accepted ASCII characters rather than transliterating accents, removes underscores/leading digits as its renderer does, preserves meaningful hyphens, and uses `section` when no usable characters remain. Thus `respect_gitignore`→`respectgitignore`, `123 Numbers`→`numbers`, `Café`→`caf`, and CJK-only→`section`.
- Kramdown GFM (`anchor-style = "kramdown-gfm"`) follows GitHub's underscore behavior rather than Kramdown's: it preserves underscores, so `test_with_underscores` generates `test_with_underscores`; a link to `#testwithunderscores` is missing while `#test_with_underscores` matches.
- Pandoc preserves Unicode/underscores but omits leading nonletters/digits according to Pandoc identifier rules.
- Bitbucket uses GitHub-like text normalization with `markdown-header-` prefix, stronger hyphen collapsing/transliteration, e.g. `Hello World`→`markdown-header-hello-world`.

Custom IDs supplement generated ones. Inline code/link/emphasis text contributes visible heading text; HTML tags do not. Automatic-anchor input from a heading is capped at 10,240 UTF-8 bytes, not 10,240 Unicode characters. Consequently, a 15,000-ASCII-character heading followed by a fragment link containing the full 15,000-character slug does not match and emits `[MD051] Link anchor '#…' does not exist in document headings`; the diagnostic retains the full requested fragment. A 6,000-character heading made of two-byte `é` characters likewise exceeds the byte cap and its full fragment does not match. Apostrophes, slashes, ampersands, emoji, non-Latin scripts and punctuation-heavy/empty headings follow the chosen algorithm deterministically. The cached workspace index tracks files, headings, defined references and cross-file links, normalizes `.`/`..` and URL encodings, deduplicates links, updates on file/config changes, and is safe when empty/corrupt.

## Spec 36

### MD052–MD054: reference definitions and link style

Reference labels normalize case and internal whitespace, but leading and trailing whitespace inside the label is preserved and distinguishes labels rather than being trimmed. Recognize full `[text][id]`, collapsed `[text][]`, images, multiline definitions/titles and (only when `shortcut-syntax=true`) shortcut `[id]`. MD052 reports each distinct normalized missing label once, at its first use, rather than once per repeated use. Thus three uses of `[reference][missing]` produce one finding with the exact message `Reference 'missing' not found`. For `[one][Missing] and [two][ missing ] and ![three][MISSING]`, the case variants deduplicate but the edge-spaced label does not: the two diagnostics are `test.md:1:1: [MD052] Reference 'missing' not found` followed by `test.md:1:20: [MD052] Reference ' missing ' not found`. The finding is located at the opening `[` of the complete link/image construct, not at the second label: `Prefix is [text][undefined]` and `Prefix is [collapsed][]` both report at column 11. Different missing labels on the same line produce separate findings at their respective construct starts; different full, collapsed, and image uses of the same normalized missing label still produce only the earliest finding.

Exclude configured case-insensitive `ignore=[]`, ordinary bracket prose, code, escaped brackets, footnotes and flavor-resolved autorefs. MD052 also ignores reference-like constructs inside inline/display dollar math. Undefined reference links or images on an unordered-list/task-list item line are skipped; for example, lines beginning `- Unordered item [text][ref1]`, `* Star item [text][ref2]`, `+ Plus item [text][ref3]`, and `- [ ] Task [text][ref4]` together produce no MD052 finding.

Only the actual Jinja delimiters (`{{ ... }}`/`{% ... %}`) and complete Hugo/Quarto shortcode tags (`{{< ... >}}`/`{{% ... %}}`) are opaque; Markdown in the body between opening and closing template/shortcode control tags is still checked. Consequently, a reference link written inside a complete shortcode tag is ignored, but `![alt][missing]` on a body line between `{% if show %}` and `{% endif %}`, or between `{{% note %}}` and `{{% /note %}}`, reports `Reference 'missing' not found`. In MkDocs flavor, complete `--8<--` snippet-inclusion lines are also opaque to MD052, while a normal missing reference after them is still reported. MkDocs Python autorefs for the observed built-in names `bool`, `float`, `int`, `object`, and `str` (and the literals `True` and `False`) are flavor-resolved rather than undefined references; an ordinary `[undefined][]` remains an MD052 finding. A duplicate/forward definition still defines the label. The rule must not invent a destination; any offered compatibility fix is applied only when deterministic.

MD053 flags reference definitions never used by a link/image, but the advertised automatic fix is not applied to the observed unused-definition case. For a file containing only `[unused]: https://example.com\n`, `check --fix --enable MD053` leaves the file unchanged, reports `Unused link/image reference: [unused]` at line 1, column 1 without a fix marker, and returns 1. It also reports every definition after the first for the same normalized label, even when that label is used; `[link][id]` followed by definitions for `[id]` at two destinations produces one finding on the second definition with `Duplicate link or image reference definition: [id]`. `ignored-definitions=[]` retains configured labels. Treat `[//]: # (...)`, `[comment]: #`, `[note]: #`, `[todo]: #`, `[fixme]: #`, `[hack]: #`, and any definition whose destination is only `#` as comment conventions, not unused real references. Definitions used through collapsed/shortcut forms count.

MD054 checks whether each link/image representation is among six booleans, all true by default: `autolink`, `inline`, `full`, `collapsed`, `shortcut`, and `url-inline`. Disallowed representations are reported, including URL-as-both-text/destination separately from ordinary inline links. It has no automatic conversion because selecting a definition placement/text style needs judgment and is excluded from `--fixable`.

## Spec 37

### MD055–MD060: tables, relative links, surrounding blanks, and link text

MD055 checks consistency of table outer pipes. Its `style` setting defaults to `consistent` and accepts `leading-and-trailing`, `leading-only`, `trailing-only`, and `no-leading-or-trailing`, but a concrete configured value does not force that convention on a table which is already internally consistent. In particular, a uniformly leading-and-trailing table remains clean under `style="no-leading-or-trailing"`. For a mixed table, choose the prevalent existing convention and prefer leading-and-trailing on ties; this selection is likewise used even when another concrete style is configured. Report and fix only rows that differ from the selected convention. Parse escaped/code-span pipes as cell content. MD056 requires every row to have the header's column count. Its exact diagnostic is `Table row has ACTUAL cells, but expected EXPECTED`; for a three-column header, two- and four-cell body rows respectively say `Table row has 2 cells, but expected 3` and `Table row has 4 cells, but expected 3`. The finding is located at column 1 and carries a concrete fix. Preserve empty cells and alignment markers, add empty missing cells or remove truly extra cells without confusing escaped pipes. Only syntactically valid tables are examined.

MD057 checks local relative destinations from inline links/images and definitions against the filesystem. Ignore absolute URLs, schemes, fragment-only links, anchors/query for path existence, and dialect placeholders. Resolve URL encoding, `.`/`..`, directories/index behavior and case according to the host filesystem. An `.html`/`.htm` destination is considered present if the same-directory `.md` source exists. Report `Relative link 'PATH' does not exist`; do not invent a target.

MD058 defaults `minimum-before=1`, `minimum-after=1`; require those blank lines around a complete table except at file boundaries and insert exactly the required blanks with nesting prefixes. A valid Kramdown block attribute list immediately after the final table row, such as `{:.striped}`, belongs to the table, so the after-table boundary is measured after that attribute line rather than before it. Thus `# Title` immediately followed by a table, then `{:.striped}`, a blank line, and `Text` produces exactly one MD058 finding, `Missing blank line before table`, at the header row; it does not also report a missing blank after the table. MD059 rejects exact case-insensitive trimmed link texts from `prohibited-texts=["click here","here","link","more"]`. Larger phrases containing those words pass, as do empty text (MD042) and images. It is not fixable.

MD060 is active in the reference's ordinary default project profile, with `enabled=true` and `style="aligned"`; no CLI `--enable MD060` switch is required for that profile. This is why ordinary checks of the fixed-suite table and mixed-content fixtures report `Table columns should be aligned`. Its lower-level no-project configuration values are `enabled=false`, `style="any"`, `max-width=0`, `column-align="auto"`, header/body overrides `auto`, and `loose-last-column=false`, and explicit isolated/no-config execution exposes those values. Configuration discovery and precedence determine which profile applies; an implementation must not discard a discovered `[MD060]` table merely because MD060 can otherwise be opt-in. When active, each nonconforming table row is reported at column 1 with the exact message `Table columns should be aligned` and a concrete fix; for an otherwise aligned three-row table whose delimiter is the sole malformed row, only that delimiter row is reported. Other styles: `aligned` pads display-width columns with one outer space, `aligned-no-space` omits delimiter-row padding, `compact` uses one minimal cell space, and `tight` puts pipes adjacent; `any` preserves layout until the rule is activated, at which point its alignment check is enforced. Respect delimiter alignment colons and left/center/right/auto alignment, Unicode display widths, escaped pipes and code spans. Runs of padding used to align a recognized table are not MD064 findings. `max-width=0` inherits MD013 only when table checking and a positive line length make it applicable; otherwise unlimited. If an aligned result exceeds the limit, compact safely. Skip ambiguous tables containing width-unstable multiline/complex emoji when alignment cannot be reliable. Fix is deterministic/idempotent and integrates with MD055/056/058.

## Spec 38

### MD061–MD065: forbidden terms, destinations, capitalization, spaces, and thematic blanks

MD061 does nothing with default `terms=[]`. With terms, find whole-word/phrase occurrences; `case-sensitive=true` by default, false folds case. Report every nonoverlapping occurrence at its actual column with the exact message `Found forbidden term 'TERM'`, using the configured term's spelling for `TERM`; for example, a case-insensitive source match `todo` against configured `TODO` says `Found forbidden term 'TODO'`. Skip front matter, code, HTML comments/blocks, URLs and other literal contexts, but check ordinary headings and link text. Markdown link destinations are not skipped: with `terms=["TODO"]` and `case-sensitive=true`, the line `` `TODO` [safe](TODO) TODO `` produces `doc.md:5:15: [MD061] Found forbidden term 'TODO'` for the destination followed by `doc.md:5:21: [MD061] Found forbidden term 'TODO'` for prose, while the front-matter and inline-code occurrences are skipped. Escape configured terms for regex purposes so punctuation-bearing terms work; do not match a term inside a larger alphanumeric word. No automatic semantic replacement is required.

MD062 flags whitespace just inside an inline link/image destination's parentheses and fixes by trimming only leading/trailing whitespace while preserving destination, balanced nested parentheses, angle form and optional quoted title. It does not alter spaces in the title or encoded destination, nor autolinks/reference definitions.

MD063 is opt-in and supports `title_case` (default), `sentence_case`, and `all_caps`. Its rule-local `enabled` default is false, and CLI rule selection alone does not override that gate; `[MD063] enabled=true` activates it. Defaults: standard lowercase title words `a, an, and, as, at, but, by, for, from, in, into, nor, of, off, on, or, per, so, the, to, up, via, with, yet`; `ignore-words=[]`; `preserve-cased-words=true`; `min-level=1`, `max-level=6`. Thus title-case fixes retain lowercase `with`, including `This Is Another Heading with Lowercase Words` and `Working with macOS and iOS`. Always capitalize first/last title words, handle hyphenated components, preserve configured brand names/internal capitals, inline code, link destinations and trailing heading attributes while correcting visible heading/link text. Sentence case capitalizes the first applicable word and lowercases ordinary later words; all caps uppercases applicable text. Fix is Unicode-safe.

MD064 flags each eligible run of at least two internal spaces: `Multiple consecutive spaces (N) found`; fix reduces to one. Default `allow-sentence-double-space=false`. When true, exactly two spaces after a real sentence-ending `. ! ?` (possibly followed by quotes/brackets) are allowed, but not three, ellipses, decimal points or recognized abbreviations. Skip leading indentation, trailing spaces (MD009), inline/fenced/indented code, front matter, comments/HTML blocks, table alignment, list/blockquote marker spacing, reference definitions, footnote/definition markers, task checkboxes and intentional Markdown structural padding; runs in these skipped contexts are not separate findings or cache warnings.

MD065 defaults `minimum-before=1`, `minimum-after=1` and requires blank lines around thematic breaks. Document start/end are exempt. Do not treat front-matter delimiters, Setext underlines, code-contained runs or list syntax as thematic breaks. In particular, `before\n---\nafter\n` has no MD065 finding because `---` is parsed as the Setext underline for `before`, not as a thematic break. The parser also does not expose `---` immediately following an ATX heading as an MD065 thematic break: the exact document `# H\n---\n\ntext\n` is accepted by a quiet MD065-only check with status 0 and no diagnostic. Fix inserts correctly nested blank lines and remains compatible with MD035.

## Spec 39

### MD066–MD073: footnotes, duplicate markers, fence collisions, front matter order, and TOC

MD066 requires every `[^id]` reference to have a definition and every definition to be referenced. Labels normalize case/whitespace; escaped/code occurrences are ignored; definition occurrences are not counted as references. Four-space-indented pseudo-definitions are code. Multiline definitions with indented content are valid. Report orphan reference/definition separately without inventing content. The exact orphan messages are `Footnote reference '[^ID]' has no corresponding definition` and `Footnote definition '[^ID]' is never referenced`; each is placed at column 1 of the first affected line. Repeated definitions are also MD066 errors: report every definition after the first at column 1 as `Duplicate footnote definition '[^NORMALIZED_ID]' (first defined on line LINE)`. Duplicate comparison is case-insensitive, so definitions `[^note]` and `[^NOTE]` produce that message on the second definition using normalized label `note`. MD067 requires definition blocks in order of first reference and fixes by moving whole blocks, preserving multiline bodies and inter-block whitespace. Arbitrary numeric/text IDs need not themselves be sequential. MD068 flags a definition with no non-whitespace content across its continuation block; whitespace/tabs alone remain empty and no content is fabricated.

MD069 detects two unordered list markers separated by whitespace at one item start (`- - text`, `* * text`, mixed variants). Locate the finding at the first marker and use the exact message `Duplicate list marker 'FIRST SECOND' - likely copy-paste error`, preserving the two marker characters: examples include `'- -'`, `'- *'`, and `'+ -'`. For three leading markers such as `- - - item`, report the first pair once. The finding is fixable; remove the first marker and its following separator while preserving indent, the second marker, the rest of the item, and the final newline. A marker pair after a blockquote prefix is exempt: `> * * quoted` produces no MD069 finding, even though a following top-level `* * ordinary` does. Also do not flag `- --flag`, `* *emphasis*`, `- **bold**`, a properly indented nested item, thematic rules or code.

MD070 detects an outer fenced code block containing a same-character fence run long enough to close it prematurely. Different fence characters and shorter inner runs do not collide. The observed nested-fence diagnostic is not automatically fixed: for an outer triple-backtick `markdown` fence containing an inner four-backtick `python` fence, `check --fix --enable MD070` leaves the file unchanged, reports the following at line 1, column 1 without a fix marker, and returns 1:

```text
Nested ``` at line 2 closes block prematurely — use ````` for outer fence
```

An equal/longer actual intended closing fence is parsed as close rather than blindly reported; collision analysis follows the intended nested-document pattern.

MD071 requires one blank line immediately after a closed leading YAML or TOML front-matter block and fixes by inserting it. It does not apply to a leading JSON object: `{"title":"Example","nested":{"key":"value"}}\n# H\n` produces no MD071 finding and returns 0. EOF after front matter and already blank separation pass. MD072 is opt-in and sorts top-level front-matter keys. With no `key-order`, compare key spellings case-insensitively: the YAML keys `Title`, `author`, `DATE` are reordered to `author`, `DATE`, `Title`. Its finding for that example is located at the first key and says `YAML frontmatter keys are not sorted alphabetically: 'author' should come before 'Title'`. With `key-order`, named keys come first in stated order and unlisted keys follow by the same case-insensitive alphabetical comparison. Preserve each key's original spelling and preserve nested structures/scalars. YAML/TOML with comments is diagnosed but not automatically reordered because comment attachment is ambiguous; comment-free YAML/TOML and JSON are fixed, with valid delimiters/format and document body content preserved. For the observed comment-free YAML input ending `---\n\nText\n`, sorting `zeta` before `alpha` also removes the document's terminal newline, leaving the body ending exactly `---\n\nText`.

MD073 (`toc-validation`) is opt-in with `min-level=2`, `max-level=4`, `enforce-order=true`, and `indent` inherited from MD007 or 2. Detect a TOC either between `<!-- toc -->` and `<!-- tocstop -->` markers or under a heading named Table of Contents/Contents. Compare list entries against actual in-range headings outside code/front matter/TOC itself: text, generated/custom anchor, hierarchy indentation, presence, stale extras, duplicates and (when enabled) document order. Duplicate headings use numbered anchors. Marker-based TOCs are safely regenerable/fixable while preserving markers; heading-based ambiguous TOCs are reported conservatively. Min/max levels and indentation are validated and fixes are idempotent.

## Spec 40

### Diagnostic locations, messages, interactions, and final invariants

Locations point to the earliest meaningful offending character: heading/list/fence rules usually use marker column, MD030 the post-marker whitespace, MD034 the URL start, MD064 the extra-space run, and LSP converts those locations to zero-based UTF-16 ranges. Required message forms include:

```text
Expected heading level 2, but found heading level 3
Multiple consecutive blank lines between content
List marker '*' does not match expected style '-'
Expected indentation of 0 spaces, found 1
Expected 2 spaces for indent depth 1, found 4
Found leading tab, use 4 spaces instead
Spaces after list markers (Expected: 1; Actual: 2)
Multiple spaces after quote marker (>)
Code block (```) missing language
URL without angle brackets or link formatting: 'http://example.com'
Link destination has leading and trailing whitespace
Link text should be descriptive
Multiple consecutive spaces (2) found
Image missing alt text (add description for accessibility: ![description](url))
Relative link 'image.png' does not exist
```

Rule interactions must be computed from the original structure, then fixed coherently: a line may validly receive MD005, MD007 and MD010; a malformed heading may receive spacing plus surrounding-blank/title findings after it becomes recognizable; table pipes are not bare syntax for other rules; blockquote/list prefixes are not internal multiple spaces; front matter `---` is not MD035/065; Setext `---` is not a horizontal rule; HTML/code suppress their unrelated contents. Applying all fixes must yield syntactically valid Markdown, never lose user content, and a subsequent identical lint/fix run must be stable. Diagnostic counts, per-rule statistics, fixable counts, file counts, remaining-issue status, JSON structures, cache contents, and LSP results must all describe that same final rule engine consistently.
