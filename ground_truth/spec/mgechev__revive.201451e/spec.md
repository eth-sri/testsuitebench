# Specification for `executable`

## Spec 1

The required artifact is a POSIX-runnable program named exactly `executable`. It is a command-line static-analysis tool for Go source. It reads files only; it must not rewrite them. Unless a fatal command/configuration/package-resolution error occurs, diagnostics are written to standard output and standard error is empty. Fatal errors are written to standard error and use exit status 1. Flag syntax errors use exit status 2. The program must finish ordinary invocations within five seconds and must not panic on malformed input.

With no target operands, the current directory is the implicit target. An empty current directory succeeds with no output. Finding ordinary lint issues does not by itself make the default invocation fail: the built-in warning and error exit codes are 0. `-set_exit_status` changes that behavior as specified below.

## Spec 2

`-help` and `--help` are equivalent, successful help requests. With no forced color, help must produce exactly the following standard output, including its initial blank line and final newline:

```text

 _ __ _____   _(_)__  _____
| '__/ _ \ \ / / \ \ / / _ \
| | |  __/\ V /| |\ V /  __/
|_|  \___| \_/ |_| \_/ \___|

Example:
  revive -config c.toml -formatter friendly -exclude a.go -exclude b.go ./...

```

When invoked as `./executable --help`, standard error must be exactly:

```text
Usage of ./executable:
  -config string
    	path to the configuration TOML file, defaults to $XDG_CONFIG_HOME/revive.toml or $HOME/revive.toml, if present (i.e. -config myconf.toml)
  -exclude value
    	list of globs which specify files to be excluded (i.e. -exclude foo/...)
  -formatter string
    	formatter to be used for the output (i.e. -formatter stylish)
  -max_open_files int
    	maximum number of open files at the same time
  -set_exit_status
    	set exit status to 1 if any issues are found, overwrites errorCode and warningCode in config
  -version
    	get revive version
```

The block above is the no-discovered-config form. If `$XDG_CONFIG_HOME` is empty and `revive.toml` exists in the current directory, the `-config` description instead ends with exactly ` (default "revive.toml")`; all other lines are unchanged. In particular, running `./executable --help` under those conditions prints:

```text
  -config string
    	path to the configuration TOML file, defaults to $XDG_CONFIG_HOME/revive.toml or $HOME/revive.toml, if present (i.e. -config myconf.toml) (default "revive.toml")
```

The `Usage of` name is the actual argv[0], so an absolute invocation may show an absolute name. Help takes precedence when combined with later flags. If `REVIVE_FORCE_COLOR=1`, the banner on stdout contains ANSI escape sequences; captured help without that environment variable contains none.

## Spec 3

`-version` succeeds, writes only to stdout, and writes nothing to stderr. The release-form output is a three-line block beginning exactly as follows, with nonempty build values after the whitespace:

```text
Version:	<version>
Commit:		<commit>
Built		<build information>
```

No unrelated linting or configuration loading occurs for a version request. A build may instead expose a single nonempty coverage/development version line, but the normal executable should use the three-line release form.

## Spec 4

Global flags are parsed before linting. Supported flags are `-config PATH`, repeatable `-exclude PATTERN`, `-formatter NAME`, integer `-max_open_files N`, boolean `-set_exit_status`, `-version`, and the help forms above. One- and two-dash spellings are accepted. A missing flag value, such as bare `-config`, exits 2 and stderr contains `flag needs an argument` followed by usage. An unknown flag exits 2 and stderr contains `flag provided but not defined: -<name>` and usage. In both cases stdout is the complete help banner from Spec 2 (205 bytes without forced color), including its initial and final blank lines; it is not empty. An unknown formatter exits 1 and stderr contains `formatting - getting formatter: unknown formatter <name>` (the shorter substring `unknown formatter <name>` is invariant).

Operands are file, directory, or package-pattern targets. Direct file operands, absolute paths, directories, `.`, and recursive `directory/...` patterns are supported. Multiple operands are unioned.

## Spec 5

An explicit `.go` file is analyzed even when supplied by absolute path or through a symlink. A directory operand analyzes its Go files, and a suffix `/...` recursively analyzes Go files in that directory tree. Multiple include patterns must all contribute results. Build-tagged files supplied explicitly are still parsed and linted; a leading legacy `// +build linux` line changes source line numbers but does not suppress the file. `//go:generate` is an ordinary accepted comment and does not suppress linting.

Directories containing no analyzable files succeed with no output. Files with CRLF line endings and valid Unicode source, strings, comments, and identifiers are accepted, and reported line numbers remain correct. Paths containing spaces, read-only files, very long lines (10,000 or more characters), files containing at least 1,000 functions, and repeated concurrent invocations must be handled without truncation, interference, or crashes.

## Spec 6

Each `-exclude` adds a global exclusion. An exclusion wins over every include regardless of argument order. Exact relative or absolute file paths are supported, but equivalent relative spellings are not normalized for an exact match: `-exclude x.go x.go` excludes the file, whereas `-exclude ./x.go x.go` does not and the file is analyzed. A recursive pattern `dir/...` excludes that directory and all descendants. An empty exclusion string is a no-op. Excluded files produce no findings even if also explicitly named. `-max_open_files` limits concurrent file opening without changing which files are analyzed; values 0 (unlimited/default), 1, small positive values, and very large positive values must all work.

## Spec 7

Package/file resolution failures are fatal and appear only on stderr. A nonexistent absolute target exits 1 with text containing `cannot import absolute path`; a nonexistent relative package target may instead contain `no required module provides package`. A mix containing an invalid absolute target exits 1 rather than silently ignoring it.

An existing non-Go file named as a target is parsed as requested and represented as a validity finding rather than crashing. Go syntax/lexical failures are likewise findings on stdout under non-JSON formatters and therefore use the configured diagnostic exit policy (normally 0). Required message fragments include `invalid file <path>`, `expected 'package', found 'EOF'` for an empty source, `expected 'package'` for source with no package clause, `expected declaration, found 'package'` for a second package clause, and `illegal character NUL` for a NUL byte. Invalid UTF-8 bytes use `illegal UTF-8 encoding`, not `illegal character`; specifically, a file named `binary.go` containing bytes `FF FE` has failure `invalid file binary.go: binary.go:1:1: illegal UTF-8 encoding (and 2 more errors)`. Positions identify the parser location, such as line 1 column 1 for that binary file, the NUL byte's location, or the second package keyword. A comments-only file yields at least one JSON finding with category `validity`.

## Spec 8

If `-config PATH` is supplied, that exact TOML file is used. Otherwise configuration discovery checks `$XDG_CONFIG_HOME/revive.toml` first, then `$HOME/revive.toml`; the first existing file wins. When `$XDG_CONFIG_HOME` is unset or empty, its first candidate becomes the relative path `revive.toml` in the current directory, still ahead of the home candidate. If neither exists, the built-in defaults are used. An explicit config overrides discovered files.

Failure to read an explicitly requested or discovered file exits 1 with `cannot read the config file` on stderr. For the explicit nonexistent path `/nonexistent/path/config.toml`, stderr is exactly `cannot read the config file\n`, without an operating-system path or cause. Malformed TOML exits 1 with `cannot parse the config file` and the TOML parser detail; for example, `confidence = this` produces detail containing `expected value but found "this" instead`. For a bad value on line 4 whose current key is `errorCode`, stderr is exactly `cannot parse the config file: toml: line 4 (last key "errorCode"): expected value but found "this" instead\n`. Discovery priority is observable: an invalid XDG config must fail even if a valid home config exists, while a missing XDG config allows the home config to be loaded.

## Spec 9

The TOML top-level fields understood by the program are:

- `severity = "warning"|"error"` (default `warning`), `confidence = <0..1>` (default 0.8), `errorCode = integer`, and `warningCode = integer` (both default 0);
- `enableDefaultRules` and `enableAllRules` booleans;
- `ignoreGeneratedHeader` boolean and `goVersion` string, which must be accepted;
- `[rule.<rule-name>]` tables with optional `severity`, `Disabled`, `arguments`/`Arguments`, and `exclude`/`Exclude`.

With an explicit config, only explicitly named rules are enabled unless `enableDefaultRules` or `enableAllRules` is true. An empty file or a config containing only `ignoreGeneratedHeader` enables no rules and therefore emits nothing. `Disabled = true` removes that rule even when otherwise enabled. `enableDefaultRules` adds the built-in default set; `enableAllRules` adds all implemented rules, after which explicitly disabled rules remain disabled. The deprecated configured name `imports-blacklist` is accepted as an alias for `imports-blocklist`.

The built-in no-config set must include at least `package-comments`, `exported`, `var-naming`, `blank-imports`, `context-as-argument`, `context-keys-type`, `dot-imports`, `error-return`, `error-strings`, `error-naming`, `increment-decrement`, `range`, `receiver-naming`, `unexported-return`, `errorf`, `empty-block`, `superfluous-else`, `unused-parameter`, `unreachable-code`, `redefines-builtin-id`, and `atomic`.

## Spec 10

Configuration is validated before target analysis. Unknown rules fail with `initializing revive - getting lint rules: cannot find rule: <name>`. Duplicate TOML rule tables fail with the TOML detail `Key 'rule.<name>' has already been defined`. A bad rule argument fails with prefix `initializing revive - getting lint rules: cannot configure rule: "<name>":` and a useful expected/actual type detail. In particular, string input to `add-constant` produces the complete detail `invalid argument to the add-constant rule, expecting a k,v map. Got string`, and a string for `argument-limit` says `invalid value`.

Rule-level excludes accept full paths, basename/path globs such as `**/file1.go`, regular expressions prefixed by `~`, the special marker `TEST` (equivalent to matching `_test.go`), and `*` to exclude every file from that rule. Rule exclusion affects only that rule. For `[rule.package-comments]` with `exclude = ["~[invalid(regex"]`, the invocation exits 1, stdout is empty, and stderr is exactly:

```text
error in config of rule [package-comments] : [invalid file filter [~[invalid(regex], regexp compile error: [error parsing regexp: missing closing ]: `[invalid(regex`]]
```

## Spec 11

Only findings whose confidence is greater than or equal to the configured confidence threshold are emitted; a threshold of 0 includes every finding. A rule-specific severity overrides global severity. JSON and other structured outputs expose the effective lowercase severity.

Without `-set_exit_status`, if emitted error-severity findings exist, return `errorCode`; otherwise if warning findings exist return `warningCode`; otherwise return 0. Thus configured codes such as 5, 3, 7, or 9 are returned exactly. `-set_exit_status` overrides both configured codes: return 1 if any finding of either severity is emitted and 0 if none is emitted. Fatal setup errors remain exit 1.

## Spec 12

Internally every finding has these fields: `Severity`, `Failure`, `RuleName`, `Category`, `Position`, `Confidence`, and `ReplacementLine`. `Severity`, `Failure`, `RuleName`, `Category`, and `ReplacementLine` are strings; confidence is numeric in `[0,1]`. `Position` has `Start` and `End`, each with `Filename`, `Offset`, `Line`, and `Column`. Lines and columns are 1-based; offsets are zero-based UTF-8 byte offsets; the end is the AST/parser end position. The filename reflects the path form resolved from the operand and is consistent across all findings for that file. `ReplacementLine` is present even when empty.

Findings are not coalesced merely because they share a line. Source traversal order must be stable within a rule (for example 100 exported variables on consecutive lines produce findings in consecutive line order). Rule categories and confidence values specified in later sections are part of the observable record.

## Spec 13

The default formatter emits one line per finding:

```text
<file>:<start-line>:<start-column>: <failure>\n
```

It adds no rule brackets or URL. The `plain` formatter appends exactly one documentation URL:

```text
<file>:<line>:<column>: <failure> https://revive.run/r#<rule>\n
```

The `unix` formatter instead inserts the rule in brackets:

```text
<file>:<line>:<column>: [<rule>] <failure>\n
```

All three emit exactly empty stdout for no findings. Quotes in a failure remain literal text. Each finding occupies one complete diagnostic line. With one or more findings, `plain` and `unix` append one additional newline after the last diagnostic, so their nonempty output ends in a blank line (`\n\n` after the last diagnostic); the default formatter does not have this extra blank line.

## Spec 14

The `json` formatter writes one valid JSON value followed by exactly one newline. No findings is exactly `null\n`; otherwise it is an array of finding objects followed by `\n`, using the exact capitalized field names and nested position structure from Spec 12. The `ndjson` formatter writes each same finding object as compact JSON on its own line, with no array wrapper, then appends one additional newline after the final object; two findings therefore produce two object lines followed by an empty third line. No findings produces exactly zero bytes. JSON correctly encodes Unicode and quotes, and every nonempty object line is independently parseable; the final blank line contains no object.

## Spec 15

The `checkstyle` formatter writes UTF-8 XML-shaped output beginning with an XML declaration and a root `<checkstyle version="5.0">`. Findings are grouped into `<file name="...">` elements; each finding is an `<error>` with decimal `line` and `column`, `severity="warning"` or `severity="error"`, `source="revive/<rule>"`, and `message="<failure> (confidence <number>)"`. XML-special characters in messages are escaped (for example, the apostrophe in `don't` is emitted as `&#39;`), but the filename is inserted into the `name` attribute verbatim. Consequently a filename such as `a&b.go` appears exactly as `<file name="a&b.go">` and makes the output not well-formed XML. For paths without such characters, the parsed message ends in the confidence parenthesis.

## Spec 16

The `friendly` formatter emits for each finding a warning/error symbol, `https://revive.run/r#<rule>`, the failure, and on the following line `<file>:<line>:<column>`. It ends with a grammatically counted summary such as `1 problem (0 errors, 1 warning)` and a `Warnings:` rule-count section when warnings exist; it emits nothing when there are no findings. The `stylish` formatter groups findings beneath each filename, gives positions as `(<line>, <column>)`, includes the same rule URLs, and ends with a summary such as `✖ 1 problem (0 errors) (1 warning)` or `✖ 2 problems`.

## Spec 17

The `sarif` formatter writes valid SARIF JSON with top-level `version` equal to `2.1.0` and a nonempty `runs` array. The first run's `tool.driver.name` is `revive`, and `tool.driver.informationUri` is `https://revive.run`. Each finding becomes a result with nonempty string `ruleId`, `message.text`, and at least one location. Its physical location contains `artifactLocation.uri` equal to the finding filename and a region with positive integer `startLine` and `startColumn`.

## Spec 18

Only line comments whose text begins immediately with lowercase `revive:` are control directives; block comments, uppercase forms, or prose before `revive:` are ordinary comments. Supported directives are `//revive:disable`, `//revive:enable`, `//revive:disable:<comma-separated-rules>`, `//revive:enable:<comma-separated-rules>`, `//revive:disable-line:<comma-separated-rules>`, and `//revive:disable-next-line:<comma-separated-rules>`. Trailing reason text after the rule list is allowed.

`disable-line` suppresses matching findings on that physical line. `disable-next-line` suppresses exactly the immediately following physical line, even if it is blank. Range disables begin after the directive and continue until the corresponding enable or EOF. Rule-specific enable can make that rule active while an all-rule disable is in effect; later disables can turn it off again. Nested all-rule ranges use the same state behavior as the underlying directive stream and must reproduce observable transitions (a second nested disable followed by one enable can expose a finding from the second disabled region). Invalid rule names affect no real rule. Multiple valid rule names on one directive are all applied. A rule-specific disable at file top suppresses that rule throughout the file until enabled.

## Spec 19

`package-comments` reports an undocumented package clause at the package keyword, category `comments`, confidence 1, failure exactly `should have a package comment`. Files whose names end in `_test.go` are exempt from this rule. A package comment is a leading attached comment describing that package. A would-be package comment separated from the package statement by a blank line instead reports exactly `package comment is detached; there should be no blank lines between it and the package statement`, category `comments`, confidence 0.9, positioned at line 2 column 1 for a comment on line 1 followed by a blank line.

When the `exported` rule is enabled, it reports undocumented exported functions, methods, types, variables, and constants outside package `main`, category `comments`, confidence 1. Package `main` declarations are exempt: a package-main file containing a `//go:generate` directive, undocumented exported type, and undocumented exported constants produces only the package-comment finding under the built-in defaults. Merely enabling `package-comments` also does not enable these declaration checks. Use templates such as `exported function Hello should have comment or be unexported`, `exported var X should have comment or be unexported`, and for a malformed existing comment `comment on exported var UnicodeVar should be of the form "UnicodeVar ..."`. In a grouped declaration like `var A, B, C = ...`, later exported names may be reported with `exported var B should have its own declaration`. Reports point at the declaration/comment line. A correctly documented exported declaration is accepted. A `//go:generate` directive remains valid ordinary input and does not itself enable any rule.

## Spec 20

`var-naming` enforces Go CamelCase: underscores in ordinary identifiers produce category `naming`, confidence 0.9, and `don't use underscores in Go names; var invalid_name should be invalidName`. An underscore-separated all-caps name such as `ALL_CAPS` instead produces `don't use ALL_CAPS in Go names; use CamelCase` at confidence 0.8, but the underscore-free name `ALLCAPS` is accepted and produces no finding. Package names may not contain underscores, mixed capitals, meaningless names (`common`, `interfaces`, `misc`, `types`, `util`, `utils`), or names colliding with the Go standard library; respective failures contain `don't use an underscore in package name`, `don't use MixedCaps in package names; MyPackage should be mypackage`, `avoid meaningless package names`, and `avoid package names that conflict with Go standard library package names`. Config options include initialism allow/block lists and a third options value supporting `upperCaseConst`, `skipInitialismNameChecks`, `skipPackageNameChecks`, `extraBadPackageNames`, and `skipPackageNameCollisionWithGoStd`. Because of the TOML compatibility shape, that third value must itself be a one-element array containing the option map, for example `arguments = [[], [], [{upperCaseConst=true, skipPackageNameChecks=true}]]`; using the bare map as the third value is fatal with `invalid third argument to the var-naming rule. Expecting a options of type slice, got map[string]interface {}`. `upperCaseConst=true` permits upper-snake constants and the skip options disable their named checks.

`receiver-naming` rejects `this`, `self`, `_`, inconsistent names for one receiver type, and names longer than configured integer `maxLength`; failures are respectively `receiver name should be a reflection of its identity; don't use generic names such as "this" or "self"`, `receiver name should not be an underscore, omit the name if it is unused`, `receiver name <x> should be consistent with previous receiver name <y> for <Type>`, and `receiver name <x> is longer than <N> characters`. Checks short-circuit for each receiver in this priority: underscore, generic name, configured maximum length, then consistency. Thus `this` and `self` on the same type each receive only the generic-name finding, and with `maxLength = 2`, receivers `t` then `long` produce only `receiver name long is longer than 2 characters`, not an additional consistency finding. The length setting must be supplied in one option map, for example `arguments = [{maxLength = 2}]`; `arguments = [2]` is fatal with `Expected object of key-value-pairs`. These findings have category `naming`, confidence 1.

## Spec 21

`unused-parameter` reports a named parameter not referenced by its function body, and `unused-receiver` reports an unreferenced method receiver with category `bad practice`, confidence 1, and `method receiver '<x>' is not referenced in method's body, consider removing or renaming it as _`. `_` is accepted. Each supports one option map with `allowRegex`; matching unused names are accepted, while the message for nonmatching names ends `renaming it to match <regex>`.

`banned-characters` takes a list of string characters and checks function, variable, and constant identifiers (not comments or string literals). It reports every identifier occurrence, including `_`, as `banned character found: <character>`, category equal to the empty string, confidence 1. An empty list reports nothing. A non-string argument is fatal with `invalid argument for the banned-characters rule: expecting a string, got int64`. `unexported-naming` reports a local symbol beginning uppercase with category `naming`, confidence 1, and `the symbol <name> is local, its name should start with a lowercase letter`.

`redefines-builtin-id` reports declarations and local shadows of built-in types (`int`, `string`, `error`), functions (`len`, `append`, and peers), and constants/variables (`true`, `false`, `nil`). Failures identify the built-in's kind even for a local short declaration: `func f() { len := 1; _ = len }` produces exactly `redefinition of the built-in function len`, not an `assignment creates a shadow` message. Other examples include `redefinition of the built-in type int` and failures containing `constant or variable`. Each occurrence is separate, category `logic`, confidence 1.

## Spec 22

Import rules behave as follows:

- `blank-imports` rejects `_ "pkg"` outside main/test packages unless a nearby comment justifies it; failure `a blank import should be only in a main or test package, or have a comment justifying it`, category `imports`.
- `dot-imports` rejects `. "pkg"` with `should not use dot imports`, category `imports`.
- `duplicated-imports` reports the later copy as `Package "fmt" already imported` (substitute package), category `imports`.
- `redundant-import-alias` reports aliases equal to the imported package name as `Import alias "fmt" is redundant`.
- `import-shadowing` reports declarations named like imported packages as `The name 'fmt' shadows an import name`, category `naming`, confidence 1.
- `imports-blocklist` takes regular-expression strings and reports matching imports as `should not use the following blocklisted import: "<path>"`, category `imports`, confidence 1. Regex `crypto/.*` and the literal `crypto/md5` match import `crypto/md5`; `crypto/*` does not act as a glob and does not match it. The deprecated `imports-blacklist` alias has the same matching behavior and emits `RuleName` as `imports-blocklist`.

`import-alias-naming` accepts `_` unconditionally. With no arguments its allow regex is `^[a-z][a-z0-9]{0,}$`; a string argument replaces it, while a map specifies only the constraints present as `allowRegex` and/or `denyRegex`. A deny-only map does not retain the default allow regex: `{denyRegex = "^[A-Z]+$"}` reports `ALLCAPS` but accepts aliases such as `customAlias` and `foo_bar`. Violations say `import name (<alias>) must match the regular expression: <regex>` or `must NOT match`. Both constraints apply when both exist; unknown/bad argument forms are configuration errors. Every finding has category `imports` and confidence 1.

## Spec 23

`context-as-argument` reports any function where a `context.Context` parameter is not first, category `arg-order`, confidence 0.9, failure exactly `context.Context should be the first parameter of a function`. Its optional map's comma-separated `allowTypesBefore` permits listed types before context. `context-keys-type` reports calls to `context.WithValue` using a basic built-in key type such as string or int; its failure contains `should not use basic type` and `context.WithValue`, and its category is `content`.

## Spec 24

Complexity and count limits are strict “greater than” limits:

- `argument-limit` accepts one integer (default 8) and says `maximum number of arguments per function exceeded; max N but got M`, confidence 1. Its position spans the complete function declaration and starts at the `func` keyword (for a declaration beginning on line 3 with no indentation, line 3 column 1), not at the function name.
- `function-result-limit` accepts one integer (default 3) and says `maximum number of return results per function exceeded; max N but got M`.
- `cyclomatic` accepts one integer (default 10), counts independent control-flow paths, and says `function <name> has cyclomatic complexity M (> max enabled N)`, category `maintenance`.
- `cognitive-complexity` accepts one integer (default 7), adds nesting-weighted control flow, and uses the analogous `cognitive complexity` message/category.
- `function-length` takes maximum statements and maximum lines (defaults 50 and 75); 0 disables that dimension. The line count is the number of physical source lines strictly between the lines containing the function body's opening `{` and closing `}`. The two brace-containing lines are excluded in their entirety, even if a statement shares one of those lines, and declaration/signature lines before the opening brace are also excluded. Thus `func f() {` followed by two body lines and then `}` has a line count of 2. The rule emits separate `maximum number of statements per function exceeded; max N but got M` and `maximum number of lines per function exceeded; max N but got M` findings.
- `max-control-nesting` accepts one integer (default 5), counts nested `if`, `for`, and `switch` independently inside function literals, and reports `control flow nesting exceeds N`, category `complexity`.
- `max-public-structs` takes one integer (default 5) per file and emits exactly one aggregate finding per file when the limit is exceeded, regardless of how many declarations exceed it. It reports `you have exceeded the maximum number (N) of public struct declarations`, category `style`.

Unless noted, these findings have confidence 1.

## Spec 25

File-oriented rules are:

- `line-length-limit N` counts characters per physical line and reports `line is M characters, out of limit N`, category `style`, confidence 1.
- `file-length-limit` takes one map with nonnegative `max`, `skipComments`, and `skipBlankLines`. It counts all physical lines except requested classes and reports `file length is M lines, which exceeds the limit of N`. `max=0` disables it. Negative max is fatal and mentions `invalid configuration value`, `need positive int64`.
- `file-header` takes exactly one required string and reports `the file doesn't have an appropriate header`; non-string is fatal with `invalid argument for "file-header" rule: argument should be a string, got int64`. A matching leading line or matching multiline comment is accepted.
- `filename-format` uses configured regex or default `^[_A-Za-z0-9][_A-Za-z0-9-]*\.go$`. Failure is `Filename <base> is not of the format <regex>.`; with the default, append one sentence per non-ASCII character in the exact form ` Non ASCII character <character> (U+<four uppercase hex digits>) found.`. For `файл.go`, the complete failure is `Filename файл.go is not of the format ^[_A-Za-z0-9][_A-Za-z0-9-]*\.go$. Non ASCII character ф (U+0444) found. Non ASCII character а (U+0430) found. Non ASCII character й (U+0439) found. Non ASCII character л (U+043B) found.` The category is the empty string and confidence is 1.
- `empty-lines` reports blank lines immediately after an opening brace or before a closing brace as `extra empty line at the start of a block` or `extra empty line at the end of a block`, category `style`, confidence 1.
- `comment-spacings` reports both `//text` and `/*text*/` without intervening spacing as `no space between comment delimiter and comment text`, category `style`, confidence 1; configured prefix exceptions are accepted.

## Spec 26

`enforce-map-style` accepts exactly one string `any`, `make`, or `literal` (no argument means `any`). `make` flags empty `map[K]V{}` as `use make(map[type]type) instead of map[type]type{}`. `literal` flags unsized `make(map[K]V)` as `use map[type]type{} instead of make(map[type]type)`. Nonempty literals and sized `make(map[K]V, n)` are never flagged. Named map types are treated like maps. Bad style text is fatal and includes `invalid map style: <value> (expecting one of [any make literal])`. A non-string `arguments = [123]` exits 1 with stderr containing exactly `invalid argument '123' for 'enforce-map-style' rule. Expecting string, got int64` after the standard rule-configuration prefix.

`enforce-slice-style` analogously accepts `any`, `make`, `literal`, or `nil`. `make` flags empty literals with `use make([]type) instead of []type{} (or declare nil slice)`; `literal` flags zero-length makes with `use []type{} instead of make([]type, 0) (or declare nil slice)`; `nil` flags either with `use nil slice declaration (e.g. var args []type) instead of <form>`. Actual nil declarations, nonempty literals, and makes with nonzero length/capacity are accepted. Array literals are not slices. Invalid text mentions `(expecting one of [any make literal nil])`. These rules use category `style`, confidence 1.

## Spec 27

`enforce-repeated-arg-type-style` accepts a single `any`, `short`, or `full`, applying to both function arguments and returns, or one map with optional string keys `funcArgStyle` and `funcRetValStyle`. Missing dimensions mean `any`. `short` reports each consecutive explicitly repeated argument type after the first as `repeated argument type "T" can be omitted`. For returns, it reports only consecutive separately named result fields (for example `(x int, y int)`); an unnamed result list such as `(int, int)` produces no return finding, including when `{funcRetValStyle="short"}` is supplied. The return failure is `repeated return type "T" can be omitted`. `full` reports grouped names with omitted types as `argument types should not be omitted` or `return types should not be omitted`. Single parameters/results are never flagged.

Invalid style `invalid` exits 1 and its configuration error contains exactly `invalid repeated arg type style: invalid (expecting one of [any short full])`. An unknown map key produces `invalid map key for 'enforce-repeated-arg-type-style' rule. Expecting 'funcArgStyle' or 'funcRetValStyle', got <key>`. A non-string/non-map argument such as `123` produces `invalid argument '123' for 'import-alias-naming' rule. Expecting string or map[string]string, got int64` (including the seemingly unrelated rule name). A non-string `funcArgStyle` value such as `123` produces `invalid map value type for 'enforce-repeated-arg-type-style' rule. Expecting string, got int64`. Each appears after the standard rule-configuration prefix from Spec 10.

`enforce-switch-style` takes zero or more of `allowNoDefault` and `allowDefaultNotLast`. Without `allowNoDefault`, a nonempty switch normally requires a default, except that no default is required when every case ends in either a `return` or an explicit `break`. A switch with one such terminating case and one nonterminating case is still reported. A present default normally must be last. The failures are `switch must have a default case clause` and `default case clause must be the last one`. `allowNoDefault` relaxes only the missing-default condition, while `allowDefaultNotLast` relaxes only default placement; both together disable both checks. A missing-default finding spans the whole switch. A default-not-last finding spans the default case clause and starts at its `default` keyword, not at the switch keyword. Empty case bodies are otherwise valid. Invalid string `invalid` is fatal with `invalid argument "invalid" for rule enforce-switch-style; expected "allowNoDefault" or "allowDefaultNotLast"`; non-string `123` is fatal with `invalid argument for rule enforce-switch-style; expected string but got int64`. Findings are category `style`, confidence 1.

## Spec 28

`identical-branches` reports an ordinary `if/else` whose complete bodies are structurally identical with failure `both branches of the if are identical`, category `logic`, confidence 1.

`identical-ifelseif-branches` recursively examines all branches, including a final `else`, of `if/else if` chains without init clauses. Equal empty, single-statement, or multiline bodies count. It reports adjacent occurrences within each equivalence sequence (four equal bodies yield three findings), while nonadjacent matching bodies separated by a different body yield the matching pair. Message: `"if...else if" chain with identical branches (lines A and B)`, positioned at line A, category `logic`. Confidence is 1, lowered to 0.8 when the relevant conditions contain calls/side effects. Chains with init clauses are skipped.

## Spec 29

`identical-ifelseif-conditions` recursively compares complete conditions in init-free `if/else if` chains and reports the later duplicate at its condition with `"if...else if" chain with identical conditions (lines A and B)`, category `logic`, confidence 1. Init-bearing clauses are skipped.

`identical-switch-branches` checks tagged switches only, recursively, and compares complete case bodies including empty bodies. It skips untagged switches and any case participating in `fallthrough`. It reports adjacent duplicate occurrences as `"switch" with identical branches (lines A and B)`, category `logic`, confidence 1.

`identical-switch-conditions` checks untagged switches only. Every expression in a multi-expression case is compared, nested switches are traversed, and each later duplicate reports `case clause at line A has the same condition` (A is the earlier case line), positioned on the later case, category `logic`, confidence 1. Tagged switches are skipped.

## Spec 30

`unnecessary-if` recognizes an `if/else` with no init where each branch contains exactly one corresponding statement: either each returns one Boolean literal, or each assigns one Boolean literal to the same single target. It reports the whole `if`, category `logic`, confidence 1, as `replace this conditional by: return <expr>` or `replace this conditional by: <target> = <expr>`. If true is in the first branch, `<expr>` is the formatted condition; if false is first, it is its logical inverse. Invert comparisons directly (`==`↔`!=`, `<`↔`>=`, `<=`↔`>`) and otherwise use `!(...)`; preserve needed parentheses, logical operators, and Unicode identifiers.

Do not report absent `else`, `else if`, init clauses, multiple statements in either branch, multiple return/assignment values, non-Boolean literals, different assignment targets, mismatched statement kinds, compound assignment, or a nonliteral branch. Nested eligible conditionals are independently found. Position spans from the `if` keyword through the final else brace.

## Spec 31

Control-flow simplification rules are:

- `early-return` reports `if c { ... } else { ... return }` when the condition can be inverted and the returning branch moved first: `if c { ... } else { ... return } can be simplified to if !c { ... return } ...`. Its optional flags are `preserveScope` and `allowJump`. With `allowJump`, an else branch ending in `continue` is also reported, with failure exactly `if c { ... } else { ... continue } can be simplified to if !c { ... continue } ...`; the inverted-condition spelling in this diagnostic is `!c`.
- `superfluous-else` reports an else after a branch ending in `continue`, `break`, or `goto`, using `if block ends with a <kind> statement, so drop this else and outdent its block`; optional `preserveScope` avoids scope-expanding rewrites. It does not report the corresponding `return` form: `if x { return 1 } else { return 2 }` produces no `superfluous-else` finding.
- `if-return` recognizes only the trivial `if ...; err != nil { return err }` pattern and says `redundant if ...; err != nil check, just return error instead.`; it does not trigger if the block contains additional work.
- `unreachable-code` reports the first dead statement following unconditional return, break, continue, goto, `os.Exit`, or `log.Fatal` as `unreachable code after this statement`, category `logic`, confidence 1; a reachable labeled target is not dead.

## Spec 32

Statement/declaration cleanup rules are:

- `unnecessary-stmt`: a switch with exactly one case says `switch with only one case can be replaced by an if-then`; a redundant function-final return says `omit unnecessary return statement`; redundant terminal breaks are also reported.
- `useless-break`: an unlabeled break at the end of a switch/select case says `useless break in case clause`; when nested in a loop, wording must warn that the break exits only the case, not the loop.
- `useless-fallthrough`: when `fallthrough` is the sole effective statement of a tagged switch case (an inline comment does not save it), says `this "fallthrough" can be removed by consolidating this case clause with the next one`. Do not report fallthrough into default, untagged switches, or cases with attached explanatory comments/other statements.
- `range`: `for k, _ := range m` and assignment form report `should omit 2nd value from range; this loop is equivalent to \`for k := range ...\`` (or `for k = range ...`) at confidence 1 and provide the complete shortened loop header in `ReplacementLine`. Do not report a used value, two real values, a lone `_`, or other valid forms.
- `var-declaration`: explicit types inferable from non-zero RHS values report `should omit type T from declaration of var x; it will be inferred from the right-hand side`, category `type-inference`, confidence 0.8. Explicit zero values `0`, `0.0`, `0.`, `""`, or `nil` report `should drop = V from declaration of var x; it is the zero value`, category `zero-value`, confidence 0.9. Constants and declarations where the type/value is necessary are accepted.

## Spec 33

Error-related rules are:

- `error-naming`: error variables use `err...` locally and `Err...` when exported; failures are `error var <name> should have name of the form errFoo`/`ErrFoo`, category `naming`, confidence 0.9.
- `error-return`: in multiple return values, error must be last; failure `error should be the last type when returning multiple items`, category `style`, confidence 0.9.
- `error-strings`: string literals passed to standard error constructors must begin lowercase and not end in punctuation/newline; failure `error strings should not be capitalized or end with punctuation or a newline`, category `errors`, confidence 0.8.
- `errorf`: replace `errors.New(fmt.Sprintf(format,args...))` with `fmt.Errorf(format,args...)`, and `t.Error(fmt.Sprintf(...))` with `t.Errorf(...)`. It emits those exact `should replace ...` messages, category `errors`, confidence 1, and puts the rewritten source line in `ReplacementLine`.
- `unhandled-error`: selected calls returning an error whose result is discarded report `Unhandled error in call to function <qualified-name>`, category `bad practice`, confidence 1. Direct discarded calls to both `fmt.Println("x")` and `os.Chdir("/")` produce no finding from this rule.

## Spec 34

`unexported-return` checks exported functions and exported methods of exported receivers and reports unexported named concrete types exposed in a result, including through nested pointers, slices, arrays, channels, and map keys/values. Failure template: `exported func <F> returns unexported type <fully-rendered-type>, which can be annoying to use` or `exported method ...`; category `unexported-type-in-api`, confidence 0.8. Built-in result types and exported aliases are not reported. An unexported named interface is also accepted, as is an unexported alias whose underlying type is an interface. Unexported methods and every function in package `main` are not reported.

## Spec 35

`package-directory-mismatch` compares a file's declared package with its containing directory after removing `-`, `_`, and `.` from both. It also accepts a directory name equal to `go` plus the normalized package name, so package `utils` in directory `goutils` is not a mismatch. Package `main`, any path under `testdata` by default, and files directly in a directory named `internal` are skipped; subdirectories below `internal` are checked. `_test.go` may use either the directory package or its `_test` form. In version directories `v1`, `v2`, etc., either the version name or parent name is accepted. A mismatch says `package name "P" does not match directory name "D"`; for version directories append ` or parent directory name "Q"`. Category is `naming`, confidence 1.

An optional argument map accepts only `ignoreDirectories = [strings...]`; these add/replace ignored path components as exercised by configuration. A non-map, unknown key, non-list value, or non-string list member is fatal. The observed complete details are `invalid argument type: expected map[string]any, got int64` for `arguments=[123]`, `unknown argument unknownArg for package-directory-mismatch rule` for an `unknownArg` key, and `invalid value in ignoreDirectories argument of rule package-directory-mismatch: expected string, got int64` for a numeric list member. Each follows the standard rule-configuration prefix from Spec 10.

## Spec 36

Range safety rules use the configured `goVersion`, or the module's Go version when no override is supplied. They analyze the following legacy patterns only when that active version is earlier than Go 1.22; at Go 1.22 and Go 1.23 the same examples emit JSON `null` because range variables have per-iteration semantics:

- `range-val-address` reports using `&value` in assignment, append, map storage, keyed composite literals, selector expressions, or index expressions when `value` is a range variable: `suspicious assignment of 'value'. range-loop variables always have the same address`, confidence 1. It does not report loops without a value variable, `&*value`, pointer selectors already based on pointers, or unrelated unary expressions.
- `range-val-in-closure` reports each range index/value captured by a dispatched/deferred function literal as `loop variable <name> captured by func literal`, including both index and value and nested occurrences.
- `datarace` reports a named return value captured by reference in a goroutine as `potential datarace: return value <name> is captured (by-reference) in goroutine`, category `logic`, confidence 0.8.

## Spec 37

Mutation/type-usage rules are:

- `modifies-parameter` reports assignments to value parameters with `parameter '<p>' seems to be modified`, category `bad practice`, confidence 0.5. Passing a slice parameter to `slices.Delete`/`DeleteFunc` and assigning the result reports `parameter '<p>' seems to be modified by 'slices.Delete...'`. Do not flag locals, `_`, or modification through a pointer field. Confidence filtering applies.
- `modifies-value-receiver` reports assigning to a field of a non-pointer receiver as `suspicious assignment to a by-value method receiver`, category equal to the empty string, confidence 1.
- `waitgroup-by-value` reports a `sync.WaitGroup` function/method parameter that is not a pointer: `sync.WaitGroup passed by value, the function will get a copy of the original one`, confidence 1.
- `unchecked-type-assertion` reports unchecked single-result assertions in assignments, returns, switch expressions, range expressions, comparisons in `if` or `switch` conditions, and channel sends. For `_ = x.(int)`, it reports `type cast result is unchecked in x.(int) - type assertion will panic if not matched`, category `bad practice`, confidence 1. If the assertion is the first value of a two-result assignment and the second result is discarded, as in `r, _ := x.(int)`, the suffix is instead `type assertion result ignored`. A bare expression statement `x.(int)` produces no finding. Meaningful comma-ok checks and type-switch assertions such as `switch x.(type)` are accepted. The reference fixture containing these contexts emits 15 findings, including assertions in a direct return, the expression of a tagged switch, a ranged value, both operand orders of comparisons, switch cases, and a channel send.
- `use-any` reports every `interface{}` type occurrence in parameter, result, or declaration as exactly `since Go 1.18 'interface{}' can be replaced by 'any'`.

## Spec 38

Small structural rules are:

- `bare-return`: a naked return in a named-result function says `avoid using bare returns, please add return expressions`.
- `bool-literal-in-expr`: Boolean literals used redundantly in comparisons/logical expressions (for example `x == true`, `x != false`, or `f() || false`) say `omit Boolean literal in expression`, category `style`, confidence 1. A literal that makes an entire `||`/`&&` expression constant instead reports category `logic` and exactly `Boolean expression seems to always evaluate to true` or `Boolean expression seems to always evaluate to false`.
- `confusing-results`: two or more unnamed results of the same type say `unnamed results of the same type may be confusing, consider using named results`, category `naming`, confidence 1; named results and differing types are accepted.
- `empty-block`: an empty removable block says `this block is empty, you can remove it`, category `logic`; ordinary `if`/`for`/`switch` blocks have confidence 1 and empty range-loop blocks have confidence 0.9. Empty function bodies are accepted, as are loops whose condition/range call itself performs work.
- `unconditional-recursion`: a direct self-call on every path with no terminating condition says `unconditional recursive call`, category `logic`, confidence 0.8.
- `nested-structs`: inline nonempty struct types inside another struct say `no nested structs are allowed`; idiomatic empty `struct{}` marker values inside channel/map types are accepted.
- `confusing-naming`: methods/fields in the same source differing only by capitalization report `Method '<a>' differs only by capitalization to method '<b>' in the same source file`, category `naming`, confidence 1.

## Spec 39

API/idiom rules are:

- `atomic`: assigning the result of `sync/atomic.Add*` back to the same addressed value (including dereference, selector, and index forms) reports `direct assignment to atomic value`, confidence 1; assigning it elsewhere is accepted.
- `get-return`: a function/method whose name starts `Get` but has no result says it `does not return any result`, category `logic`, confidence 0.8.
- `deep-exit`: calls to `os.Exit`, `syscall.Exit`, `log.Fatal`, `log.Fatalf`, and related fatal calls outside `main`/`init` say `calls to <qualified-call> only in main() or init() functions`.
- `optimize-operands-order`: in `&&`/`||`, expensive calls placed before cheaper terms produce a low-confidence suggestion containing both `for better performance` and `might be rewritten as`.
- `inefficient-map-lookup`: ranging over a map solely to compare each key by `==` or `!=` to a fixed value reports `inefficient lookup of map key`, category `style`, confidence 1; loops doing meaningful iteration are accepted.

## Spec 40

Modernization rules are:

- `increment-decrement`: `i += 1`/`i -= 1` say `should replace i += 1 with i++` / `should replace i -= 1 with i--`, category `unary-op`, confidence 0.8.
- `unnecessary-format`: known `Printf`/`Sprintf`/`Errorf` calls whose literal format contains no directive recommend the non-format form using messages `unnecessary use of formatting function "fmt.Printf", you can replace it with "fmt.Print" or "fmt.Println"`, `... "fmt.Sprintf" ... "fmt.Sprint" or just the string itself`, and `... "fmt.Errorf" ... "errors.New"`. Category is `optimization` and confidence is 0.8.
- `use-errors-new`: simple `fmt.Errorf("literal")` says `replace fmt.Errorf by errors.New`, category `errors`.
- `use-fmt-print`: built-in `print` and `println` report `avoid using built-in function "println", replace it by "fmt.Fprintln(os.Stderr, <arguments>)"` (and the corresponding print form), category `bad practice`.
- `string-of-int`: converting a non-rune, non-byte integer with `string(i)` says `dubious conversion of an integer into a string, use strconv.Itoa`, confidence 1. Conversions explicitly intended as `rune` or `byte` are accepted.
- `use-slices-sort` is active only when the configured or module Go version is at least 1.21. When active, it maps `sort.Float64s`, `Ints`, and `Strings` to `slices.Sort`; their `AreSorted` forms to `slices.IsSorted`; `sort.Slice`/`Sort` to `slices.SortFunc`; stable forms to `slices.SortStableFunc`; and `sort.SliceIsSorted`/`IsSorted` to `slices.IsSortedFunc`. Message is `replace <old> by <new>`, category `maintenance`, confidence 1. An isolated source with no module version and no `goVersion` override produces JSON `null` for `sort.Ints(x)`; setting `goVersion = "1.21"` produces `replace sort.Ints by slices.Sort`.
- `redundant-build-tag` reports legacy `// +build` when a `//go:build` constraint is also present as `The build tag "// +build" is redundant since Go 1.17 and can be removed`.
- `redundant-test-main-exit` is active only when the configured or module Go version is at least 1.15 and the source filename ends in `_test.go`. It reports direct final `os.Exit`, `syscall.Exit`, or `log.Fatal` calls in `TestMain` as `redundant call to <call> in TestMain function, the test runner will handle it automatically as of Go 1.15`, category `style`, confidence 1. The filename `not_a_test.go` does have the required `_test.go` suffix and is reported when `goVersion = "1.15"`; the same isolated source with no active module/configured version produces JSON `null`. A true non-test filename such as `ordinary.go` is not reported even at Go 1.15. Do not flag other functions, `flag.Parse`, or unrelated/direct method calls.

## Spec 41

`string-format` accepts any number of array arguments, each containing a scope, a regex delimited by `/.../`, and optional custom failure text. Scope is `package.Function`, optionally comma-separated, optionally selecting a zero-based argument as `[N]`, and optionally a top-level struct field as `.Field`; omitted index means 0. Matching is required normally, while a leading `!` before the regex delimiters reverses it. Each violating string literal reports the supplied custom message when present. Without a custom message, an ordinary regex violation reports `string literal doesn't match user defined regex <delimited-regex>`, while an inverse regex violation reports `string literal matches user defined regex <delimited-regex>`; `<delimited-regex>` retains its surrounding slashes but not the inverse marker. For example, violations of `/^[a-z]/` and `!/^[A-Z]/` respectively report `string literal doesn't match user defined regex /^[a-z]/` and `string literal matches user defined regex /^[A-Z]/`. Findings have confidence 1. Multiple scopes/configurations are independent.

An empty top-level argument list, `arguments = []`, is valid and enables no checks; an invocation over a source file then succeeds and produces JSON `null`. Within an argument entry, an empty scope or too few scope/regex strings is a fatal configuration error containing `empty scope provided` or `scope and regex are required`, as applicable. Tested messages include `must start lowercase`, `message must start lowercase`, `format string must start lowercase`, `string must be all lowercase`, and `string must not contain uppercase`.

## Spec 42

`unsecure-url-scheme` examines string literals. Nonlocal `http://` and `ws://` URLs report respectively `prefer secure protocol https over http in "<url>"` and `prefer secure protocol wss over ws in "<url>"`, confidence 1. Ordinary `https`/`wss` is accepted, as are localhost and `127.0.0.1`. IPv6 literals are still checked, including loopback `[::1]` and global IPv6 hosts.

`epoch-naming` recognizes assignments/declarations initialized from `time.Now().Unix*`. Names ending case-insensitively in `Sec`, `Second`, or `Seconds` for `Unix`; `Milli` or `Ms` for `UnixMilli`; `Micro`, `Microsecond`, `Microseconds`, or `Us` for `UnixMicro`; and `Nano` or `Ns` for `UnixNano` are accepted without an epoch finding.

## Spec 43

`time-date` type-checks calls to `time.Date`. It emits category `time`. A nil timezone is confidence 1 with `time.Date timezone argument cannot be nil, it would panic on runtime`. Literal month/day zero are confidence 1 with `time.Date month argument should not be zero` / `day argument should not be zero`. Other numeric bounds are confidence 0.8: month 1..12, day 1..31, hour 0..23, minute 0..59, second 0..60 (60 is accepted), nanosecond 0..999999999, with `time.Date <part> argument should be between L and H: V` when a more specific calendar message is unavailable.

When the year, month, and day are decimal integer literals and the month is in 1..12, the rule cross-checks the month's actual length and leap-year status. The failures are `time.Date day argument is <D>, but <Month> has only <N> days`, with the year appended after `February`. Exact observed examples at confidence 0.8 are `time.Date day argument is 32, but January has only 31 days`, `time.Date day argument is 30, but February 2023 has only 28 days`, and `time.Date day argument is 29, but February 2023 has only 28 days`. Negative years are accepted. A unary plus is reported as `time.Date month argument contains a useless plus sign: +1` at confidence 0.8.

Noncanonical numeric notation is reported as `use decimal digits for time.Date <part> argument: <notation-description> found: use <decimal> instead of <literal>`. The descriptions include `octal notation`, `hexadecimal notation`, and `binary notation`; thus `0o1`, `0x1`, and `0b1` in the month position respectively use those exact phrases. Other descriptions cover padded octal (`001`, confidence 1), float literals, exponential notation, and underscore alternative notation; ordinary decimal is accepted.

## Spec 44

`use-waitgroup-go` is active only when the configured or module Go version is at least 1.25. At Go 1.25 it recognizes the legacy sequence `wg.Add(...)`, followed by a goroutine function literal that calls `wg.Done()` (deferred or not, with intervening body statements), and reports `replace wg.Add()...go {...wg.Done()...} with wg.Go(...)`, category `style`, confidence 1. The same sequence produces no finding at Go 1.23. It does not trigger without preceding Add, without Done, for a named function passed to `go`, or for a waitgroup identifier other than the recognized `wg` pattern.

`forbidden-call-in-wg-go` is likewise active only for Go 1.25 or later. It checks function literals passed to `wg.Go`. Direct calls to `panic`, `wg.Done`, `log.Panic`, `log.Panicf`, and `log.Panicln` each produce `do not call <name> inside wg.Go`, category `errors`, confidence 1. At Go 1.23, the same `panic`, `wg.Done`, and `log.Panic` examples produce no finding. Ordinary work and `log.Print` are accepted.

## Spec 45

`struct-tag` parses the complete raw tag of every struct field. Malformed key/quoted-value syntax reports `malformed tag`. A tag on a lowercase unexported field reports `tag on not-exported field <field>`, except the special `_struct` codec configuration field. A tag name of `-` means ignored; any following options are reported as `useless option X for ignored field in <tag> tag` or `useless options X,Y ...`. All struct-tag findings have confidence 1.

Recognized tag families include `asn1`, `bson`, `cbor`, `codec`, `datastore`, `default`, `json`, `mapstructure`, `properties`, `protobuf`, `required`, `spanner`, `toml`, `url`, `validate`, `xml`, and `yaml`. Unknown options use `unknown option "X" in <tag> tag`. Configuration arguments `"tag,opt1,opt2"` add allowed options for that tag; `"!tag"` disables validation of that family. For a named non-ignored JSON tag, an empty trailing option reports `option can not be empty in json tag`; `omitzero` before Go 1.24 reports `prior Go 1.24, option "omitzero" is unsupported in json tag`. JSON/XML/YAML/TOML unknown option messages name the family exactly.

## Spec 46

For encoding-related struct tags:

- ASN.1 accepts `utf8`, `optional`, `omitempty`, `tag:N`, and `default:value`. Duplicate tag numbers report `duplicated tag number N in asn1 tag`. Default-value type checking is performed for Boolean, `float64`, and `int` fields, and an incompatible value reports `type mismatch between field type and default value type in asn1 tag`. String fields are left unchecked: a string field with tag `asn1:"default:1"` is accepted and produces JSON `null`.
- BSON accepts a name plus `omitempty`, `inline`, and `minsize`. Duplicate nonempty names across fields report `duplicated tag name "name" in bson tag`.
- CBOR accepts a name plus `omitempty`, `toarray`, and `keyasint`. `toarray` requires an empty name and cannot use meaningful `omitempty`/`omitzero`; use the exact failures `tag name for option "toarray" should be empty in cbor tag` and `options "omitempty" and "omitzero" are ignored in presence of "toarray" option in cbor tag`. Integer names require `keyasint`. Duplicate integer keys say `duplicated integer key N in cbor tag`; duplicate string names say `duplicated tag name X in cbor tag`.
- Codec accepts names and options including `omitempty`, `toarray`, `int`, `uint`, and `float`. Options placed on `_struct` apply globally; repetition on a normal field reports `redundant option "X", already set for all fields in codec tag`.
- Datastore accepts names plus `noindex`, `flatten`, and `omitempty`.

Valid forms above produce no finding from `struct-tag`.

## Spec 47

For data-binding struct tags:

- `default:"value"` must be parseable as the field's string, integer, Boolean, or floating type; otherwise report `type mismatch between field type and default value type in default tag`.
- Mapstructure accepts `omitempty`, `squash`, and `reminder` after the name.
- Properties accepts a name plus nonempty `default=value` and `layout=value`. Duplicate keys report `duplicated option "default" in properties tag`; malformed/bare options report `unknown or malformed option "X" in properties tag`; empty default reports `option "default" not of the form default=value in properties tag`; default type mismatch names the properties tag; layout on anything other than `time.Time` reports `layout option is only applicable to fields of type time.Time in properties tag`.
- Required accepts only the complete values `true` and `false`; otherwise report `required should be "true" or "false" in required tag`.
- Spanner accepts a field name and no built-in options; configured custom options may extend it.

## Spec 48

For remaining struct tags:

- URL accepts `int`, `omitempty`, `numbered`, `brackets`, and delimiter options such as `comma` or `semicolon`, but delimiter options are mutually exclusive. For both comma and semicolon report `can not set both "semicolon" and "comma" as delimiters in url tag`.
- Validate accepts standard validators including `required`, `min=`, `max=`, `email`, `dive`, `keys`, and `endkeys`. `keys` must immediately occur in a valid dive context; otherwise report `option "keys" must follow a "dive" option in validate tag`. `endkeys` requires a prior keys block; otherwise report `option "endkeys" without a previous "keys" option in validate tag`.
- Protobuf requires a valid wire type such as `bytes`, `fixed32`, or `varint`, a numeric field tag, cardinality option such as `opt`/`req`, and `name=...`. Missing name says `mandatory option "name" not found in protobuf tag`; invalid wire type says `invalid tag name "X" in protobuf tag`; duplicate options say `duplicated option "X" in protobuf tag`; duplicate numeric field tags within a struct say `duplicated tag number N in protobuf tag`.

All valid examples in Specs 45–48 must produce JSON `null` when `struct-tag` is the only enabled rule; each invalid field produces a separate `struct-tag` finding with the exact failure text given.

## Spec 49

`add-constant` accepts exactly one option map. Keys are accepted in camel, lowercase, or hyphen form: `maxLitCount` is a decimal string limiting tolerated repeated string literals; `allowStrs`, `allowInts`, and `allowFloats` are comma-separated literal allowlists; and `ignoreFuncs` is a comma-separated set of function-name regexes whose arguments are ignored. `ignoreFuncs = ""` is not an empty set: it is a fatal empty regular expression, producing `invalid argument to the ignoreFuncs parameter of add-constant rule, expected regular expression must not be empty` after the standard configuration-error prefix. Numeric literals not on their corresponding allowlist are magic numbers and report `avoid magic numbers like '<literal>', create a named constant for it`, confidence 1. For example, with `allowInts = "0,1"`, both `42` and `100` in `return x * 42 + 100` are separately reported. Allowed values and literals inside ignored calls are not reported. A non-map argument is the configuration error described in Spec 10.

## Spec 50

`defer` detects six independent gotchas. Loop, method-call, and call-chain findings have category `bad practice`; recover, immediate-recover, and deferred-return findings have category `logic`. Unless stated otherwise, confidence is 1:

- a defer directly inside a loop reports `prefer not to defer inside loops` (a defer inside a nested goroutine/function literal is scoped to that literal and is not a loop defer);
- the `method-call` check recognizes a type-qualified method expression such as `defer T.f()` and reports exactly `be careful when deferring calls to methods without pointer receiver`, category `bad practice`, confidence 0.8. It does not resolve an ordinary method value through its receiver declaration: defining `func (T) f()` and writing `var t T; defer t.f()` produces no finding;
- a deferred function that returns a value reports `return in a defer function has no effect`, category `logic`, confidence 1;
- `recover()` outside a deferred function reports `recover must be called inside a deferred function`, category `logic`, confidence 0.8; when evaluated while registering a defer, append `, this is executing recover immediately` and use confidence 1;
- `defer recover()` and recover passed as an eagerly evaluated defer argument are immediate-recover cases;
- a deferred call chain such as `defer factory()()` reports `prefer not to defer chains of function calls`.

With no arguments all gotchas are enabled. An optional nested string list may select only named checks `call-chain`, `loop`, `method-call`, `recover`, `immediate-recover`, and `return` (camel/lowercase aliases are accepted). Findings from separate gotchas are not merged.
