# Specification: `executable`

## Spec 1: Required artifact and compatibility target

Provide one directly runnable command-line program named exactly `executable`. It is a structural source-code search, lint, and rewrite tool compatible with ast-grep CLI version 0.42.1. It must not require a build step or another repository command at runtime.

`executable --version` prints:

```text
ast-grep 0.42.1
```

`--help` must identify the commands `run`, `scan`, `test`, `new`, `lsp`, `completions`, and `help`. Help and argument errors use the actual invocation name (`executable`) in usage lines. Help must remain available even if an invalid `sgconfig.yml` is present in the current directory. Invoking `executable` with no arguments is the exception to the usual short argument-error layout: it exits 2, writes the complete top-level help page to stderr, writes nothing to stdout, and does not append a `For more information, try '--help'.` footer.

The complete stderr value for that no-argument invocation is exactly:

```text
Search and Rewrite code at large scale using precise AST pattern

Usage: executable [OPTIONS] <COMMAND>

Commands:
  run          Run one time search or rewrite in command line. (default command)
  scan         Scan and rewrite code by configuration
  test         Test ast-grep rules
  new          Create new ast-grep project or items like rules/tests
  lsp          Start language server
  completions  Generate shell completion script
  help         Print this message or the help of the given subcommand(s)

Options:
  -c, --config <CONFIG_FILE>  Path to ast-grep root config, default is sgconfig.yml
  -h, --help                  Print help (see more with '--help')
  -V, --version               Print version
```

The program reads and writes UTF-8 text, preserves Unicode source text, and reports positions correctly when text contains multibyte characters. It must handle empty files, files without a final newline, deeply nested syntax trees, wide trees, and large numbers of matches without crashing or imposing a shallow traversal limit.

## Spec 2: Commands and command-line shape

The top-level shape is:

```text
executable [OPTIONS] <COMMAND>
```

The global `-c, --config CONFIG_FILE` selects a project configuration; its default name is `sgconfig.yml`. `-h/--help` and `-V/--version` are supported. Invoking pattern options such as `-p` without spelling `run` selects the `run` command. Invoking the program with neither a command nor a pattern is an argument error.

The tested command shapes are:

```text
executable run [OPTIONS] --pattern PATTERN [PATH ...]
executable scan [OPTIONS] [PATH ...]
executable test [OPTIONS]
executable new [OPTIONS] [NAME] [project|rule|test|util]
executable lsp [OPTIONS]
executable completions [OPTIONS] [bash|elvish|fish|powershell|zsh]
```

In generated argument-parser usage text, an omitted optional repeated run pathname is spelled `[PATHS]...`, but once the user supplied at least one pathname it is spelled `<PATHS>...` in a diagnostic for another argument. In particular, `executable run -l js` exits 2 with empty stdout and exactly:

```text
error: the following required arguments were not provided:
  --pattern <PATTERN>

Usage: executable run --pattern <PATTERN> --lang <LANG> [PATHS]...

For more information, try '--help'.
```

By contrast, if `test.js` was supplied, `executable run -l js test.js` exits 2 with empty stdout and exactly:

```text
error: the following required arguments were not provided:
  --pattern <PATTERN>

Usage: executable run --pattern <PATTERN> --lang <LANG> <PATHS>...

For more information, try '--help'.
```

For `run` and `scan`, omitted paths mean the current directory, and multiple file and directory paths are accepted. A directory is searched recursively. Work may be parallel and cross-file result order need not be stable; `-j/--threads NUM` is accepted, including `0` for automatic selection and `1` for single-threaded operation.

## Spec 3: Languages and parsing

The program performs syntax-aware matching using concrete parsers, not substring or regular-expression emulation. It supports at least Bash, C, C++, C#, CSS, Dart, Elixir, Go, Haskell, HTML, Java, JavaScript, JSON, Kotlin, Lua, PHP, Python, Ruby, Rust, Scala, Swift, TSX, TypeScript, and YAML. Common case-insensitive names and aliases are accepted where conventional, including `js`, `javascript`, `jsx`, `ts`, `typescript`, `tsx`, `py`, `python`, `rs`, `rust`, `c`, `cpp`, `css`, `html`, and `go`. Canonical display names include `JavaScript`, `TypeScript`, `Python`, `Java`, `Go`, `C`, `Cpp`, and `Rust`.

When `--lang/-l` is omitted for file input, infer the language from each file name or configured language glob. When it is supplied, parse the pattern in that language and search only content of that language, including eligible injected regions. Standard language-specific syntax must work, including JavaScript/TypeScript and JSX, Python indentation and await/subscript syntax, Rust postfix `.await` and function syntax, Go declarations, C declarations, HTML elements, and CSS rules.

Invalid language names are command-line errors of the form `invalid is not supported!`. Stdin has no file name from which to infer a language, so `run --stdin` requires `--lang`. A pattern must normally parse as exactly one matchable AST node; empty patterns and patterns containing multiple top-level nodes are configuration/query errors. A JavaScript pattern that parses as one tree containing an `ERROR` node is nevertheless accepted. For example, `run -p 'let =' -l js --stdin` exits 0 even when it finds no match and writes this warning block to stderr, ending with the displayed empty line:

```text
Warning: Pattern contains an ERROR node and may cause unexpected results.
Help: ast-grep parsed the pattern but it matched nothing in this run. Try using playground to refine the pattern.
See also: https://ast-grep.github.io/playground.html

```

Source files with syntax errors are normally skipped during ordinary rule scans rather than crashing the scan. A YAML rule can explicitly match tree-sitter error nodes with `kind: ERROR`.

## Spec 4: `run`: one-time structural search

`run` accepts these options and aliases:

- `-p, --pattern PATTERN` (required for explicit `run`)
- `--selector KIND`
- `-r, --rewrite FIX`
- `-l, --lang LANG`
- `--strictness MODE`
- `--debug-query[=pattern|ast|cst|sexp]`
- `-c, --config CONFIG_FILE` when `run` is explicitly named
- `--stdin`, `--follow`, repeated `--no-ignore TYPE`, repeated `--globs GLOB`, and `-j/--threads`
- `-i/--interactive`, `-U/--update-all`, `--files-with-matches`, and `--json[=STYLE]`
- `--color WHEN`, `--inspect GRANULARITY`, `-A/--after`, `-B/--before`, `-C/--context`, and `--heading WHEN`

The default-command spelling (`executable -p ...`) does not accept a top-level `-c` mixed into that implicit command. It nevertheless discovers the default `sgconfig.yml` from the current directory or its ancestors and retains that project context. Consequently configured features such as `languageGlobs` apply to an implicit run. For example, from a project that maps `*.custom` to JavaScript, `executable -p 'foo()' --inspect summary --json=compact input.custom` searches that file successfully and reports `isProject=true`. An explicitly selected configuration is still expressed as `executable run -c CONFIG -p ...`.

Each AST node in each selected source is considered, including nodes at arbitrary nesting depth. Literal syntax in a pattern is exact structurally: method names, string contents, numeric values, operators, declarations, and argument count matter unless replaced by metavariables. A pattern never matches merely a partial incompatible structure.

A successful match search exits 0. A valid `run` that finds no matches exits 1 and normally emits no human-readable output. With pretty or compact JSON it emits an empty array; stream JSON emits nothing.

`--update-all` requires `--rewrite`. In particular, this implicit-`run` invocation:

```text
executable -p 'console.log($A)' -l ts --update-all .
```

exits 2, emits nothing to stdout, and writes exactly this parser diagnostic to stderr:

```text
error: the following required arguments were not provided:
  --rewrite <FIX>

Usage: executable --pattern <PATTERN> --lang <LANG> --update-all --rewrite <FIX> <PATHS>...

For more information, try '--help'.
```

## Spec 5: Pattern metavariables and strictness

Pattern code uses metavariables:

- `$NAME` captures one required named AST node.
- `$$NAME` captures one node while permitting that node to be unnamed in the tree-sitter tree. It is not an optional or zero-node capture. For example, `return $$VALUE` matches bare `return;` by binding `VALUE` to the unnamed `;` token, whereas `return $$VALUE;` does not match bare `return;` because the pattern requires another literal semicolon after the captured node.
- `$$$NAME` captures zero or more consecutive nodes, such as arguments, parameters, statements, or elements. Bare `$$$` is also a variadic wildcard.

Metavariable names are uppercase-style identifiers in normal use. A single metavariable can capture a complex subtree. Reusing the same metavariable in one combined match requires structural consistency: every occurrence must bind to the same subtree. Distinct names have independent bindings. Multi-captures retain every captured node and can span lines. Bindings and their exact ranges are included in JSON.

`--selector KIND` extracts a named subnode of that kind from the parsed pattern context and uses it as the matcher. If the context contains several nodes of that kind, it selects the first one in syntax-tree/source order; it does not prefer the occurrence containing a metavariable. For example, selecting `pair` from `({ first: 0, key: $VALUE, last: 2 })` selects `first: 0`, not `key: $VALUE`. The equivalent YAML pattern object is:

```yaml
pattern:
  context: 'class A { $METHOD() {} }'
  selector: method_definition
  strictness: smart
```

Strictness accepts exactly these modes:

- `cst`: compare all concrete nodes and punctuation. Differences such as a trailing comma matter.
- `smart`: the default structural behavior; ignore source-trivial whitespace and optional trailing commas, but do not ignore redundant parentheses. Thus `foo(a)` matches multiline `foo(\n a\n);` and `foo(a,);`, but does not match `foo((a));` or `foo(\n (a),\n);`.
- `ast`: compare named AST nodes, retaining comments as relevant AST content.
- `relaxed`: compare AST nodes while ignoring unnamed nodes and comments embedded between a node's ordinary tokens, including a block comment in a parameter list and a comment trailing another statement. A standalone comment that occupies its own position in a statement sequence is not discarded: for example, `function $F($X) { return $X * 2; }` in relaxed mode matches `function bar(/* block comment */ y) { return y * 2; }` and `function baz(z) { return z * 2; // trailing\n}`, but does not match a function with a standalone `// comment` line before the `return`.
- `signature`: compare structure while ignoring comments and terminal text, so structurally identical names/operators can match.
- `template`: compare textual template shape while ignoring node kinds, allowing the same text in different syntactic node kinds.

Whitespace can vary freely in smart mode, including multiline formatting. CST, ranges, and JSON byte offsets must remain Unicode-correct. Any other strictness value exits 2. For example, `--strictness invalid_mode` starts its stderr exactly as follows; the `<STRICTNESS>` placeholder is part of the diagnostic:

```text
error: invalid value 'invalid_mode' for '--strictness <STRICTNESS>'
  [possible values: cst, smart, ast, relaxed, signature, template]

For more information, try '--help'.
```

## Spec 6: Project configuration and rule discovery

A project configuration is YAML with these fields:

```yaml
ruleDirs:
  - /path/to/rules
testConfigs:
  - testDir: /path/to/rule-tests
    snapshotDir: optional-relative-or-absolute-snapshot-directory
utilDirs:
  - /path/to/utils
languageGlobs:
  javascript: ['.eslintrc']
  python: ['BUILD', 'WORKSPACE']
customLanguages: {}
languageInjections: []
```

`ruleDirs` is required for a normal project scan. Paths in an explicitly loaded configuration are resolved relative to the configuration file, unless absolute. Rule and utility directories are searched recursively for `.yml` and `.yaml` files. Malformed configuration, nonexistent configured paths, and malformed rule/test YAML produce structured errors rather than tracebacks. A malformed explicitly selected configuration does not echo the selected filename: for `scan -c bad.yml .` with `bad.yml` containing `ruleDirs: [unterminated`, exit status is 8, stdout is empty, the header is `Error: Cannot parse configuration`, the Help line refers generically to `sgconfig.yml`, and the cause reports the YAML line and column.

One rule file may contain several YAML documents separated by `---`. A missing rule `id` defaults to the file stem for a single document. In a multi-document file, an implicit id is `stem-N`, where `N` is that document's zero-based position; explicit IDs remain unchanged and do not consume a different numbering scheme. An id-less rule supplied as `--inline-rules` has no file stem and retains the empty string as its ID; matching scan JSON therefore contains the literal field `"ruleId":""`.

Duplicate resulting IDs across the project are rejected. For duplicate ID `no-console`, exit status is 8, stdout is empty, and stderr is exactly:

```text
Error: Duplicate rule id `no-console` is found
Help: Multiple rule files have the same id. Please add a unique `id` field to each rule.
See also: https://ast-grep.github.io/guide/rule-config.html

```

`scan --rule/-r FILE` loads the rules in one file without requiring a project. `scan --inline-rules YAML` does the same from command-line text and supports `---`; an inline rule may omit `id`. `--rule` and `--inline-rules` conflict. `--filter REGEX` selects project rules whose IDs match the regular expression and conflicts with `--rule`.

Malformed YAML wording is part of the diagnostic. A malformed rule mapping such as `this is: not: valid: yaml` produces a cause containing exactly `mapping values are not allowed in this context at line 3 column 13`. A malformed configuration beginning `invalid: yaml: [bracket` produces exactly this cause line:

```text
╰▻ mapping values are not allowed in this context at line 1 column 14
```

With no discoverable configuration, `scan` exits 3 with empty stdout and the exact no-project diagnostic shown in Spec 22. If a configured rule directory does not exist, it exits 6 with empty stdout and this exact path-sensitive form (each displayed blank line is significant):

```text
Error: Cannot read rule directory ABSOLUTE_RULE_DIRECTORY
Help: The rule directory cannot be read or traversed

✖ Caused by
╰▻ ABSOLUTE_RULE_DIRECTORY: IO error for operation on ABSOLUTE_RULE_DIRECTORY: No such file or directory (os error 2)

```

An implicit rule ID cannot be inferred from a filename whose bytes are not valid UTF-8. Such a file exits 8 with empty stdout and this diagnostic; `DISPLAY_PATH` is the lossy displayed absolute pathname, with each invalid byte represented by the Unicode replacement character:

```text
Error: Cannot infer rule id from DISPLAY_PATH
Help: The rule file name is not valid UTF-8. Please add an explicit `id` field to the rule.
See also: https://ast-grep.github.io/guide/rule-config.html

```

## Spec 7: Rule document format

A lint rule is a YAML mapping. `language` and `rule` are required; the remaining fields are optional:

```yaml
id: no-console
language: JavaScript
message: Avoid console.log
severity: warning
rule:
  pattern: console.log($MSG)
constraints:
  MSG:
    regex: '^"'
utils:
  local-util:
    kind: call_expression
transform: {}
fix: console.warn($MSG)
rewriters: []
note: Additional Markdown-capable explanation.
labels:
  MSG:
    style: secondary
    message: captured message
files: ['src/**/*.js']
ignores: ['**/*.test.js']
url: https://example.invalid/rule
metadata:
  category: best-practice
  tags: [console, logging]
```

`severity` is `hint`, `info`, `warning`, `error`, or `off`; omitted severity behaves as `hint`. An off rule is not run in normal scan/test operation. `files` is an allow-list and `ignores` an exclusion list, evaluated against project-relative paths. Each may contain a glob string or `{glob: STRING, caseInsensitive: BOOL}`.

Messages and rule IDs are preserved verbatim, including hyphens, underscores, and dots. `note` supports multiline text and Markdown-like rendering in rich reports. A label key names a captured node metavariable; its style is `primary` or `secondary`, with an optional message. Without custom labels the whole match receives one primary label.

## Spec 8: Atomic, logical, and relational YAML matchers

The `rule` mapping can combine any of the following keys:

- `pattern`: a pattern string or `{context, selector?, strictness?}` object.
- `kind`: either one exact parser node-kind name or an ESQuery-style selector. An invalid kind/selector is rejected. The exact kind `ERROR` matches parse-error nodes.
- `regex`: a Rust-style regular expression applied to the complete node text.
- `range`: an exact source range.
- `nthChild`: a sibling-position selector.
- `inside`, `has`, `precedes`, `follows`: relational matchers.
- `all`, `any`, `not`: logical composition.
- `matches`: a local/global utility reference or parameterized utility call.

Multiple matcher keys in one mapping are conjunctive. `all` requires every subrule to match the same target node and merges captures while enforcing repeated-variable consistency. `any` tries alternatives independently; a successful branch contributes only that branch's captures and failed branches leak no bindings. `not` succeeds only when its subrule fails and does not corrupt bindings established outside it. These rules can be nested arbitrarily. A rule made only from unconstrained negation and having no possible positive node kind is invalid. A standalone `range` also supplies no positive kind set and is invalid; both column-exact and line-only standalone forms exit 8 with the final cause `╰▻ Rule must specify a set of AST kinds to match. Try adding `kind` rule.`. Conjoining the range with a positive matcher such as `kind` enables the range behavior in Spec 10.

`constraints` applies additional matchers to metavariables captured by the main rule. All named constraints are checked. Captures from a local utility are exported and are visible to constraints, fixes, and JSON. Captures made internally by a global utility's own rule body are not exported; by themselves they do not cause `metaVariables` to appear in the caller's JSON. Captures produced by a rule supplied as a parameterized-utility argument are exported after the whole call succeeds.

## Spec 9: Relational search

`inside` asks whether the target has a matching ancestor; `has` asks whether it has a matching descendant; `precedes` and `follows` inspect later and earlier siblings respectively. A relation accepts all normal rule keys plus:

```yaml
inside:
  kind: function_declaration
  field: body
  stopBy: neighbor
```

`field` restricts the relationship to the parser's named AST field and invalid field names are rejected. `stopBy` is:

- `neighbor` (default): examine only the immediate relevant neighbor/parent/child.
- `end`: continue to the end of the relevant ancestor/descendant/sibling direction.
- another rule mapping: continue until that boundary rule matches.

Custom stop rules may themselves use patterns, metavariables, regex, kind, field, utilities, logical matchers, nth-child, and relational matchers. The boundary is inclusive where traversal reaches it. Nested and conflicting relations must terminate safely. Invalid `stopBy` strings are rejected.

## Spec 10: Child, ESQuery, and range selectors

`nthChild` uses one-based CSS position semantics and accepts an integer, a CSS `An+B` string such as `2n`, `2n+1`, or `-n + 3`, or:

```yaml
nthChild:
  position: 2n
  ofRule:
    kind: string
  reverse: false
```

`ofRule` counts only siblings satisfying that rule; `reverse` counts from the end.

In contrast to a pattern object's `selector`, the YAML `kind` matcher accepts ESQuery-style selectors. The rightmost matching component is the primary matched node. Supported observed forms include a descendant combinator (`call_expression identifier`), direct-child combinator (`array > number`), adjacent and general siblings (`A + B` and `A ~ B`), `:has(...)` including a direct-child argument such as `array:has(>number)`, `:not(...)`, `:is(...)`, and `:nth-child(An+B)`. Thus `array > number:nth-child(2n+1)` matches the first, third, and fifth number children; `A + B` and `A ~ B` report the matching `B`; and `call_expression identifier` reports the descendant identifier. In the relational selector forms, the relationship witness is attached as a secondary label and appears in JSON under the reserved multi-capture name `secondary`.

A pattern object's `selector` remains one exact parser node-kind name, not an ESQuery expression. The whole string is validated as a kind. For example, `selector: 'class_declaration > class_body > method_definition'` exits 8 because that complete string is an invalid kind; the final cause line is exactly:

```text
╰▻ Kind `class_declaration > class_body > method_definition` is invalid.
```

`range` has `start` and `end`, each with a zero-based `line` and optional zero-based `column`. With columns, the target node must exactly occupy the supplied multiline span. If columns are omitted, any columns on the supplied line span are accepted.

## Spec 11: Utilities and parameterized utilities

Local utilities appear under a rule's `utils` as a mapping from utility ID directly to a rule object. Local utilities are always zero-argument helpers; neither an `arguments` field nor a wrapper `rule` field is valid inside a local utility value. For example, a local utility is written as `utils: {u: {pattern: 'foo($A)'}}`, not `utils: {u: {rule: {pattern: 'foo($A)'}}}`. The wrapper form exits 8 with an `unknown field` YAML cause (`arguments` or `rule`, whichever is encountered).

Global utility YAML files are loaded recursively from `utilDirs` and have `id`, `language`, optional `arguments`, and `rule`. Only global utilities can declare parameters. A non-parameterized local or global utility is referenced as:

```yaml
rule:
  matches: utility-id
```

A parameterized utility declares arguments and is called by mapping each argument to a rule:

```yaml
# utility
id: wrap-with-condition
language: JavaScript
arguments: [BODY]
rule:
  all:
    - pattern: 'if ($COND) { $$$STATEMENTS }'
    - has:
        matches: BODY
        stopBy: end

# caller
rule:
  matches:
    wrap-with-condition:
      BODY:
        pattern: console.$METHOD($$$)
```

Parameter arguments may be arbitrary nested rules, including `all`, `has`, and other utility calls. A parameter is consumed inside the global utility body with `matches: ARGUMENT_NAME`, rather than by writing `$ARGUMENT_NAME` in a pattern. Multiple calls in one `matches` object are conjunctive. Argument-rule bindings are exported after the full parameterized call succeeds, without cross-call leakage; captures belonging to the global utility body itself remain internal.

Utility IDs and argument names must be nonempty and cannot contain reserved `(`, `)`, `,`, or `=` characters. Argument names must be unique. Reject undefined utilities, self-reference cycles, attempts to call a parameter as a utility, missing arguments, extra/unknown arguments, calls with an empty map when parameters are required, and passing arguments to a non-parameterized utility. Validation errors identify the utility, but two forms do not enumerate individual argument names. Using a parameterized utility `u` as scalar `matches: u` ends with:

```text
╰▻ Utility `u` requires arguments and cannot be used as `matches: u`.
```

Passing a map to a non-parameterized `u` ends with:

```text
╰▻ Utility `u` does not accept arguments.
```

Global utility declaration failures exit 8, write nothing to stdout, and use this complete stderr wrapper:

```text
Error: Error occurs when parsing global utility rules
Help: Please check the YAML rules inside the rule directory
See also: https://ast-grep.github.io/guide/rule-config/utility-rule.html

✖ Caused by
╰▻ `rule` is not configured correctly.
╰▻ Rule contains invalid utils.
╰▻ SPECIFIC_CAUSE

```

The final `SPECIFIC_CAUSE` is exactly one of these argument-specific lines:

```text
Utility id `ID` contains reserved characters.
Utility `ID` declares invalid argument `ARGUMENT`.
Utility `ID` declares duplicate argument `ARGUMENT`.
Utility parameter `ARGUMENT` cannot be called with arguments.
```

The first line applies to an empty ID as well as an ID containing any reserved character; an empty ID therefore produces this final cause:

```text
Utility id `` contains reserved characters.
```

The second line applies to an empty or reserved-character argument (for an empty name, its backtick pair is empty); the third to a duplicate argument; and the fourth to calling a declared parameter as though it were a utility accepting an argument map. Thus IDs `wrap(BODY)`, `wrap,body`, `wrap=body`, and `wrap(test)` are named verbatim in the first form; an empty argument and `BODY(X)` use the second form; and duplicate `BODY` uses the third form.

Invalid utility use inside an ordinary rule instead uses the rule-file wrapper below. `RULE_PATH` is printed with the same spelling passed to or discovered by the command. Missing parameter mappings—including an empty call map—use `Rule contains invalid utils.` and name the first missing declared argument:

```text
Error: Cannot parse rule RULE_PATH
Help: The file is not a valid ast-grep rule. Please refer to doc and fix the error.
See also: https://ast-grep.github.io/guide/rule-config.html

✖ Caused by
╰▻ Fail to parse yaml as Rule.
╰▻ `rule` is not configured correctly.
╰▻ Rule contains invalid utils.
╰▻ Parameterized utility `UTILITY_ID` is missing argument `ARGUMENT`.

```

For example, mappings that omit `FIRST`, `MIDDLE`, or `BODY` end in precisely those respective names. An undefined utility reference instead replaces the final two lines with:

```text
╰▻ Rule contains invalid matches reference.
╰▻ Rule `UTILITY_ID` is not defined.
```

Supplying an undeclared argument uses the same rule-file wrapper and `Rule contains invalid utils.` chain, ending exactly:

```text
╰▻ Parameterized utility `UTILITY_ID` does not declare argument `ARGUMENT`.
```

Passing a map to a zero-argument utility likewise uses that wrapper and chain, ending exactly:

```text
╰▻ Utility `UTILITY_ID` does not accept arguments.
```

A self-reference cycle is diagnosed specifically as a cycle, not as an undefined utility. For a correctly shaped local utility `u` whose direct rule object contains `matches: u`, the causal chain ends with exactly:

```text
╰▻ `utils` is not configured correctly.
╰▻ Rule contains invalid matches reference.
╰▻ Rule `u` has a cyclic dependency in its `matches` sub-rule.
```

## Spec 12: Transforms and rewriters

`transform` maps a new metavariable name to a transformation. A transform source is a previously captured or previously transformed variable. Transforms execute in declaration/dependency order, appear under `metaVariables.transformed` in JSON, and are substituted into fixes like captured variables. A transform output may not shadow a captured variable.

Object syntax supports:

```yaml
transform:
  PART:
    substring: {source: $TEXT, startChar: 1, endChar: -1}
  RENAMED:
    convert:
      source: $PART
      toCase: camelCase
      separatedBy: [underscore, dash, caseChange]
  CLEAN:
    replace: {source: $RENAMED, replace: '(\d+)', by: 'N$1'}
  REWRITTEN:
    rewrite: {source: $$$ITEMS, rewriters: [rewrite-one, rewrite-two], joinBy: ', '}
```

`substring` indexes Unicode characters, not UTF-8 bytes. Missing start/end means beginning/end, negative indices count from the end, and out-of-range slices yield an empty string rather than crashing. `replace` performs global regular-expression replacement and supports capture groups. `convert.toCase` accepts `lowerCase`, `upperCase`, `capitalize`, `camelCase`, `snakeCase`, `kebabCase`, and `pascalCase`; `separatedBy` accepts `caseChange`, `dash`, `dot`, `slash`, `space`, and `underscore`, including an empty list.

Equivalent function-string syntax is accepted:

```yaml
transform:
  A: 'substring($TEXT, startChar=1, endChar=-1)'
  B: 'convert($A, toCase=upperCase, separatedBy=[underscore, dash])'
  C: "replace($B, replace='_', by='--')"
  D: "rewrite($$$ITEMS, rewriters=[r1, r2], joinBy=',')"
```

The parser tolerates whitespace, single/double quoted values, commas or spaces inside quoted values, empty arrays, and chained transforms. It rejects unknown transformation names, unknown arguments, missing required arguments, invalid enum values, malformed arrays, and unclosed quotes. A missing final right parenthesis is tolerated rather than treated as a punctuation error: the function string `substring($X, startChar=1` is accepted, and in the observed `foo($X)` rule its transformed value is the empty string (and a fix of `$A` is therefore an empty replacement).

A rewriter is an entry in `rewriters` with required `id`, `rule`, and `fix`, and optional `constraints`, `utils`, and `transform`. The rewrite transform applies named rewriters to the captured source and optionally joins multi-results with `joinBy`. For a multi-capture, only elements matched and rewritten by one of the named rewriters contribute to the transformed result; unmatched elements are discarded before `joinBy` is applied. Thus rewriting `list(old(1), keep, old(2))` with an `old($X)` rewriter and `joinBy: ', '` produces `new(1), new(2)`, not a value containing `keep`. Rewriters can access parent-rule metavariables. Later rewriters may reference already declared rewriters.

Rewriters without a fix, invalid utility references, undefined metavariables, and transform name collisions are rejected before scanning. When the rule has a `rewriters` section, every name in a rewrite transform's `rewriters` list must resolve to an entry in that section. An unresolved name exits 8 before scanning; for the name `missing`, the final cause is exactly:

```text
╰▻ Undefined rewriter `missing` used in transform.
```

If the rule has no `rewriters` section at all, the reference does not perform that name-set validation. In that case an unresolved name is accepted, and if no named rewriter resolves or matches a single captured node, that node's original source text is retained: rewriting captured `x` through only `missing` produces transformed value `x`.

## Spec 13: Fixes and rewrite ranges

`fix` is one of:

```yaml
fix: 'replacement using $VARS and $$$MULTI'
```

```yaml
fix:
  template: replacement
  title: Optional title
  expandStart: {regex: ',', stopBy: neighbor}
  expandEnd: {kind: pair, stopBy: end}
```

```yaml
fix:
  - {title: First choice, template: 'first $VALUE'}
  - {title: Second choice, template: 'second $VALUE'}
```

Template substitution preserves the captured source text and indentation. `expandStart` and `expandEnd` enlarge the replacement range across matching siblings in the respective direction. They support all relational rule forms, `neighbor`, `end`, and custom stop rules. Both directions may be used together and expansion stays within the current syntactic sibling context. A fixer whose required expansion cannot match the relevant edge sibling is not available: in the tested `expandStart` case where its matcher cannot match the preceding comma sibling, the scan exits 0 and writes nothing to stdout or stderr; it does not report the unexpanded original match.

Every item in a multi-fixer list must have a title. An empty fixer list is valid and means the rule has no suggested replacement. Human noninteractive output and JSON consistently use only the first fixer as the default suggestion. JSON exposes a single `replacement` and `replacementOffsets`, never an `additionalFixes` field.

A list containing a fixer without `title` exits 8 with empty stdout and exactly this stderr, where `RULE_PATH` preserves the command's pathname spelling:

```text
Error: Cannot parse rule RULE_PATH
Help: The file is not a valid ast-grep rule. Please refer to doc and fix the error.
See also: https://ast-grep.github.io/guide/rule-config.html

✖ Caused by
╰▻ Fail to parse yaml as Rule.
╰▻ `fix` pattern is invalid.
╰▻ Fixer in list must have title.

```

Every variable used in a fix, constraint, transform source, or label must be defined in the appropriate rule/utility/parent scope. Labels may target captured nodes, not string-only transform outputs. Configuration violations are reported before matching.

## Spec 14: `scan`: linting, overrides, suppression, and fixes

With no `--rule` or `--inline-rules`, `scan` locates `sgconfig.yml` (or `--config`) and loads project rules. It dispatches each rule only to its language and applies rule `files`/`ignores`. Multiple languages and multiple paths can be scanned together. Empty and syntactically unusable source files do not produce false diagnostics.

Severity overrides are repeatable:

```text
--error[=RULE_ID]  --warning[=RULE_ID]  --info[=RULE_ID]
--hint[=RULE_ID]   --off[=RULE_ID]
```

With no value, an override applies to all selected rules; with values it applies to those IDs. When several overrides affect one rule, the last applicable override wins. For ordinary file scans, `off` suppresses the rule entirely. A single-rule stdin scan is an exception: `scan --inline-rules ... --stdin --off=RULE_ID --json=compact` still emits the match, with its JSON `severity` set to the literal string `off`, and exits 0. A rule configured with `severity: off` remains excluded from normal scan/test discovery. `--max-results NUM` globally caps emitted matches across files and stops once the cap is reached.

Comments containing `ast-grep-ignore` suppress a diagnostic on the same line or the following code line. A first-line suppression followed by an empty line suppresses the file. During a full project scan, an ignore comment that suppresses nothing is itself reported as an `unused-suppression` finding.

Normal `scan` exit status is 0 for no findings or findings no more severe than warning/info/hint. If one or more error-severity findings exist, output is still produced, exit status is 1, and human/SARIF output ends with:

```text
Error: N error(s) found in code.
Help: Scan succeeded and found error level diagnostics in the codebase.
```

Those two footer lines are written to stderr, not stdout, and are followed by one empty line (the stderr suffix is therefore `codebase.\n\n`). This also applies when the findings themselves use rich, GitHub, or file-name-only output.

`scan -U/--update-all` applies every available default fix to files without prompting. For file input it writes exactly `Applied N changes\n` to stderr and nothing to stdout. Files with no matches remain byte-for-byte unchanged. Multiple files and multiple matches are updated coherently and use one aggregate count. With stdin, update-all writes the fully rewritten source to stdout instead of a file, appends its own newline after that source, and still writes `Applied N changes\n` to stderr. Therefore rewriting the newline-terminated input `old(3);\n` produces stdout `new(3);\n\n` and stderr `Applied 1 changes\n`.

## Spec 15: File traversal and filtering

By default directory traversal does not follow symbolic links. `--follow` follows file and directory symlinks, reports each traversed path even if several symlinks reach the same underlying file, detects ancestor loops, reports broken links, and continues with other reachable files. These reported errors do not override the match-derived status: if another reachable file matches, the command still exits 0. Directly supplied nonexistent files/directories and circular file symlinks are errors.

For a relative traversal root spelled `.`, successful human match lines remove the root component: they start `src/main.js:...`, `.hidden.js:...`, `ignored_dir/lib.js:...`, or `linked_hidden/secret.js:...`, never `./src/main.js:...`. This normalization applies equally to default traversal, `--follow`, every combination of repeated `--no-ignore`, and positive or negative `--globs` filters. It does not apply to traversal diagnostics. With `--follow`, a broken link and an ancestor loop are written to stderr exactly as single newline-terminated lines:

```text
ERROR: ./broken_link: No such file or directory (os error 2)
ERROR: File system loop found: ./nested/deep/loop points to an ancestor .
```

The diagnostic path retains the leading `./`; successful match paths do not. If reachable files match, these errors coexist with match output and the exit status remains 0.

Normal traversal respects VCS ignore rules and other ignore sources. A `.gitignore` participates only when traversal recognizes a Git repository boundary (for example, a `.git` directory); a standalone `.gitignore` in an ordinary non-repository directory is ignored, so files it names remain searchable. Repeated `--no-ignore TYPE` accumulates disabled categories. Accepted types are `hidden`, `dot`, `exclude`, `global`, `parent`, and `vcs`. `hidden` includes dot-named paths; `dot` disables `.ignore`; `vcs` disables VCS ignore files such as `.gitignore` while leaving `.ignore` active and implies the corresponding parent-VCS behavior.

Repeated `--globs` applies gitignore-style path filters. Positive globs include, a leading `!` excludes, and a later matching glob overrides an earlier one. Explicit globs override ordinary ignore decisions. Invalid glob syntax is rejected. Hidden files themselves are searchable in the ordinary tested scan cases; hidden-directory behavior follows the selected ignore mode.

`--files-with-matches` suppresses match bodies. `run`, which has one query, prints a matching path once. `scan` prints a path once for each selected rule that has at least one match in that path; consequently the same path is repeated when two rules match it. For example, if one error rule and one warning rule both match `src/app.js`, stdout is exactly `src/app.js\nsrc/app.js\n`, followed (when applicable) by the error-count footer on stderr.

It conflicts with `--json`, `--interactive`, and `--update-all` for both `run` and `scan`. For `run` without an explicit `--lang`, the first two conflicts have these exact exit-2 stderr diagnostics (and empty stdout):

```text
error: the argument '--files-with-matches' cannot be used with '--json[=<STYLE>]'

Usage: executable run --pattern <PATTERN> --files-with-matches <PATHS>...

For more information, try '--help'.
```

```text
error: the argument '--files-with-matches' cannot be used with '--interactive'

Usage: executable run --pattern <PATTERN> --files-with-matches <PATHS>...

For more information, try '--help'.
```

## Spec 16: Language globs, injections, and custom languages

`languageGlobs` maps a built-in language to additional file-name globs. It supports nonstandard and extensionless names such as `.eslintrc`, `BUILD`, and `WORKSPACE`, and mapping component files such as `*.vue` and `*.svelte` to HTML so their embedded regions can be searched. Invalid configured language names are errors. Explicit `run -c CONFIG` loads this configuration.

Built-in HTML injection discovers JavaScript in `<script>` and CSS in `<style>` while preserving original host-file line and column positions. Eligible TypeScript script regions can be scanned as TypeScript. Searches for a language not injected by the host produce no false matches.

Custom injections use:

```yaml
languageInjections:
  - hostLanguage: js
    rule:
      pattern: 'styled`$CONTENT`'
    injected: css
  - hostLanguage: js
    rule:
      pattern: 'styled.$LANG`$CONTENT`'
    injected: [css, js, ts]
```

`$CONTENT` defines the exact injected source range. A scalar `injected` is static. An array is dynamic: the `$LANG` capture selects an allowed language, including normal aliases such as `ts`. Missing required captures cause that region to be skipped safely. Multiple injection rules for one host and multiple regions per file accumulate. Empty/whitespace regions are harmless. Injected text is parsed as a standalone document in the injected language; the host pattern does not provide missing syntactic context around `$CONTENT`. In particular, with the static JavaScript-to-CSS configuration shown above, a CSS scan rule whose pattern is `$P: $V` over ``const X = styled`color: red;`;`` exits 0 and emits compact JSON `[]\n`, not a `color: red` finding. Injection ranges that do produce matches remain positions in the host file. Invalid host languages and invalid injection matchers are configuration errors.

For a `languageInjections` entry whose `hostLanguage` is `not_a_real_language`, project scan exits 1, writes nothing to stdout, and writes exactly `Error: not_a_real_language is not supported!\n` to stderr, with no extra blank line.

Custom tree-sitter languages use:

```yaml
customLanguages:
  MyCustomLang:
    libraryPath: ./lib/parser.so
    languageSymbol: tree_sitter_json
    extensions: [mcl, customjson]
    metaVarChar: '#'
    expandoChar: '_'
```

`libraryPath` may be a string or a mapping from target triple (for example `x86_64-unknown-linux-gnu`) to path. Relative paths resolve from the configuration directory; absolute paths remain absolute; valid symlink paths load normally. `languageSymbol` defaults from the custom name if omitted. `extensions` is required but may be empty. Custom names are case-sensitive. All extensions are registered, and their canonical custom language name appears in JSON. `metaVarChar`/`expandoChar` customize pattern metavariable expansion. Missing paths/fields, unsupported current target, missing dynamic-library symbols, malformed YAML, and unknown custom rule languages produce explicit configuration/load errors in the project-loading paths described below.

An explicit one-time run is an exception: CLI language validation occurs before `run -c CONFIG` registers custom languages. Thus, even when `sgconfig.yml` defines `MyCustomLang` with `libraryPath: ./missing-parser.so`, `run -c sgconfig.yml -p '{}' -l MyCustomLang x.mcl` exits 2 with empty stdout and exactly:

```text
error: invalid value 'MyCustomLang' for '--lang <LANG>': MyCustomLang is not supported!

For more information, try '--help'.
```

It does not attempt the configured library and does not mention `missing-parser.so`.

When a project-loading path reaches custom-language registration, a nonexistent custom-language library and a target map that omits the current `x86_64-unknown-linux-gnu` target both exit 79 with empty stdout and this common prefix:

```text
Error: Cannot load custom language library
Help: The custom language library is not found or cannot be loaded.
See also: https://ast-grep.github.io/advanced/custom-language.html

✖ Caused by
```

For a nonexistent library path, the suffix is exactly:

```text
╰▻ cannot get the absolute path of dynamic lib
╰▻ No such file or directory (os error 2)

```

For a library that loads but lacks the configured symbol, the suffix has all three cause lines below. `LOADED_LIBRARY_PATH` is the resolved library pathname and `SYMBOL` is the configured symbol:

```text
╰▻ cannot read symbol
╰▻ dlsym failed
╰▻ LOADED_LIBRARY_PATH: undefined symbol: SYMBOL

```

For a target map missing the current target, the suffix is exactly, including the reference's `configure` spelling:

```text
╰▻ Target dynamic lib `x86_64-unknown-linux-gnu` is not configure

```

A custom language named `nolibpath` with no `libraryPath` exits 8 under the full configuration-parse wrapper:

```text
Error: Cannot parse configuration
Help: The sgconfig.yml is not a valid configuration file. Please refer to doc and fix the error.
See also: https://ast-grep.github.io/reference/sgconfig.html

✖ Caused by
╰▻ customLanguages.nolibpath: missing field `libraryPath` at line LINE column COLUMN

```

`LINE` and `COLUMN` are the YAML parser's one-based source coordinates; for the five-line minimal fixture they are `5` and `5`. A rule whose `language` is an unregistered `NonexistentLang` exits 8 using the ordinary `Cannot parse rule RULE_PATH` header/help/link and this exact cause section:

```text
✖ Caused by
╰▻ Fail to parse yaml as RuleConfig
╰▻ data did not match any variant of untagged enum SgLang

```

Malformed YAML in a custom-language entry uses the same parser-specific wording as other configuration YAML. For an unterminated `extensions: [broken` on line 6, the cause is exactly:

```text
╰▻ did not find expected ',' or ']' at line 7 column 1, while parsing a flow sequence at line 6 column 17
```

An unsupported key such as `invalid_lang` in `languageGlobs` exits 33 with empty stdout and exactly:

```text
Error: Language `invalid_lang` is not supported
Help: Please choose a built-in language or register a custom language in sgconfig.yml.
See also: https://ast-grep.github.io/reference/languages.html

✖ Caused by
╰▻ invalid_lang is not supported!

```

## Spec 17: Human output, context, colors, and inspection

Non-JSON `run` output reports the matched source with one-based display line numbers. With headings disabled it uses `path:line:source`; with `--heading=always` it groups matches under a path heading and renders numbered source lines. `--heading` accepts `auto`, `always`, and `never`; auto follows TTY status. `-B N`, `-A N`, and `-C N` add before, after, or both kinds of context, merging adjacent contexts. `-C` conflicts with separate `-A`/`-B`.

Rewrite suggestions are rendered as structured diffs with a file heading, `@@` hunk header, and aligned `-` old/`+` new lines. Scan diagnostics in `--report-style rich` use this general shape:

```text
error[rule-id]: message
  ┌─ path:LINE:COLUMN
  │
LINE │ source text
  │ ^^^^^^^^^^^^
```

A match spanning several lines uses connected multiline markers: `╭` on the first matched source line, `│` on each interior line, and `╰───^` on the closing line. For example, a rule matching the complete three-line `if` statement in `test.js` emits this diagnostic block:

```text
error[no-console-in-condition]: Console call in condition
  ┌─ test.js:2:3
  │  
2 │ ╭   if (x) {
3 │ │     console.log(x);
4 │ │   }
  │ ╰───^

```

In rich human diagnostic headings, rule severity `hint` is displayed as `help`, and `info` is displayed as `note`; `warning` and `error` retain those names. This applies both to explicitly configured severities and to the omitted-severity default, so an omitted-severity rule starts with `help[rule-id]: ...`, not `hint[rule-id]: ...`.

Every complete rich diagnostic block ends with a newline followed by one empty line. Consecutive diagnostics therefore have exactly one blank line between the preceding underline/label block and the next severity heading, and the final rich diagnostic also has the blank-line terminator. This is true for file input, stdin (`STDIN`), inline rules, project/filter scans, language-specific scans, and rules without a fix (including an empty fixer list).

Rich output includes custom primary/secondary labels and notes. `medium` and `short` are condensed one-line records of the form `path:line:column: severity[rule-id]: message`, with medium retaining applicable notes. Fixes use diff output even when a report style is otherwise selected.

`--color` accepts `auto`, `always`, `ansi`, and `never`. Any other value is an exit-2 parser error. For `--color invalid`, stdout is empty and stderr is exactly:

```text
error: invalid value 'invalid' for '--color <WHEN>'
  [possible values: auto, always, ansi, never]

For more information, try '--help'.
```

`never` emits no ANSI escapes; `always` and `ansi` force them. In non-heading `run` output, both forced modes leave the `path:line:` prefix, surrounding whitespace, and unmatched punctuation unstyled and wrap each matched source span in bold red `\x1b[1;31m` followed immediately by reset `\x1b[0m`. For example, matching the call in `test.js:2:  console.log("world");` emits `test.js:2:  \x1b[1;31mconsole.log("world")\x1b[0m;\n`. Auto disables color when stdout is not suitable, `TERM=dumb`, or `NO_COLOR` is set. Unicode source is never damaged by styling.

`--inspect` accepts `nothing`, `summary`, and `entity`, writes tracing only to stderr, and does not alter matches. Summary's project record is spelled `sg: summary|project: isProject=BOOLEAN,projectDir=VALUE`. For an implicitly discovered project, `VALUE` is the absolute directory containing its configuration; an explicitly selected relative configuration can report an empty value, producing `sg: summary|project: isProject=true,projectDir=`. File counts use a separate record such as `sg: summary|file: scannedFileCount=N,skippedFileCount=M`. Entity supplies per-file/per-rule detail. This project detection also applies to implicit-run spelling: an invocation beginning directly with `-p` from a directory beneath a discoverable `sgconfig.yml` reports `isProject=true`, includes the literal `,projectDir=` field, and uses that project's configured language globs.

Paths use forward slashes in displayed and serialized output on the tested platform. Rule IDs and source lines are not escaped or normalized beyond what the selected protocol requires.

## Spec 18: JSON output contract

`--json` means pretty JSON. Pretty output uses two-space indentation for object contents, places the first object brace on the line immediately after `[`, and ends with `]` and a newline. `--json=compact` is one JSON array on one line with no formatting whitespace. `--json=stream` emits one standalone object per line with no array brackets. Pretty/compact no-match output is `[]` followed by a newline; stream no-match output is empty. `--json` conflicts with interactive and file-name-only output.

A run match object has the following shape; scan adds the diagnostic fields shown below. Fields described as conditional below are omitted rather than serialized as empty placeholders:

```json
{
  "text": "console.log(\"x\")",
  "range": {
    "byteOffset": {"start": 0, "end": 16},
    "start": {"line": 0, "column": 0},
    "end": {"line": 0, "column": 16}
  },
  "file": "file.js",
  "lines": "console.log(\"x\");",
  "charCount": {"leading": 0, "trailing": 1},
  "replacement": "console.warn(\"x\")",
  "replacementOffsets": {"start": 0, "end": 16},
  "language": "JavaScript",
  "metaVariables": {
    "single": {
      "MSG": {"text": "\"x\"", "range": {"byteOffset": {"start": 12, "end": 15}, "start": {"line": 0, "column": 12}, "end": {"line": 0, "column": 15}}}
    },
    "multi": {},
    "transformed": {}
  },
  "ruleId": "no-console",
  "severity": "warning",
  "note": null,
  "message": "Avoid console.log",
  "labels": [
    {"text": "console.log(\"x\")", "range": {}, "style": "primary"}
  ]
}
```

The numeric values above illustrate the conventions rather than prescribing offsets for different input. Source ranges and byte offsets are half-open and zero-based; display lines are one-based. `lines` contains the complete source lines selected for display, including requested before/after context, and `charCount.leading/trailing` identifies characters in `lines` before and after `text`. Each exported single/multi capture includes text and ranges; transformed values are strings. The entire `metaVariables` field is present when the query produces exported named single, multi, or transformed bindings. It is omitted when there are no exported named bindings; in particular, literal patterns, a pattern using only bare `$$$`, and captures made solely inside a referenced global utility body do not emit `"metaVariables":{"single":{},"multi":{},"transformed":{}}`. Local-utility captures and parameter-argument-rule captures are exported as described in Specs 8 and 11. `replacement` and `replacementOffsets` appear only when a default fix exists. Scan objects always include `ruleId`, `severity`, `note`, `message`, and `labels`; for an id-less `--inline-rules` document, `ruleId` is present as the empty string rather than a generated identifier.

`scan --include-metadata --json` copies the rule's arbitrary metadata mapping into top-level `metadata`; without the flag it is omitted. The flag requires JSON. JSON remains valid even when scan later prints an error-count footer; protocol consumers can take the JSON portion preceding `Error:`/`Help:`.

## Spec 19: SARIF and GitHub Actions formats

`scan --format sarif` emits pretty-printed JSON with two-space indentation, one field per line at the corresponding nesting depth, and exactly one terminating newline after the final `}`. It is not compact JSON. The top-level value is:

```json
{
  "runs": [
    {
      "results": [],
      "tool": {
        "driver": {
          "name": "ast-grep"
        }
      }
    }
  ],
  "version": "0.42.1"
}
```

Each result contains `ruleId`, mapped `level`, `{text: ...}` message, and one physical location. The location contains `artifactLocation.uri` and a region with one-based `startLine`, `startColumn`, `endLine`, `endColumn`, plus zero-based `byteOffset`, `byteLength`, and `snippet.text`. A fix adds `fixes[0].description.text`, `artifactChanges`, and one replacement containing `deletedRegion` and `insertedContent.text`. The fix description is exactly `Apply suggested fix`.

`scan --format github` emits one GitHub annotation per diagnostic, for example:

```text
::error file=path.js,line=1,endLine=1,title=rule-id::message
```

The annotation kind reflects severity (notably `error` and `warning`) and locations are one-based.
Each annotation is written to stdout and ends with one newline. If an error-severity annotation makes the scan fail, the two-line error-count footer is written separately to stderr with the blank-line terminator specified in Spec 14.

## Spec 20: Interactive rewriting

`run -i` and `scan -i` use a real terminal session. With a fix, show the diff and an `Accept?` prompt. Responses are:

- Enter or `y`: apply the current replacement.
- `n`: reject it and continue.
- `a`: apply the current and all remaining nonoverlapping replacements without more prompts.
- `q`: quit without applying unaccepted replacements.
- Tab: cycle among overlapping alternatives at the current location.
- `e`: invoke an editor and treat the current choice as not accepted.

Accepted edits are written to their respective files, counts persist across files, and the end message is `Applied N changes` only when `N > 0`. For noninteractive file rewriting with `run -U`, the exact completion message is `Applied N changes\n` on stderr and stdout remains empty. Once an overlapping replacement is accepted, incompatible overlapping matches are discarded safely.

Without a fix, interactive view mode offers `Next[enter], Quit[q], Edit[e]`; it never modifies source. `e` runs `$EDITOR FILE +LINE`, defaulting to `vim`, waits for completion, and propagates editor spawn/failure status. Quit from view mode succeeds.

Interactive mode cannot consume source from stdin because stdin is needed for prompts. The exception is `-U --stdin`, which requires no prompt, writes the fully rewritten source to stdout followed by an additional output newline, and writes the usual `Applied N changes\n` completion message to stderr. For example, rewriting newline-terminated `console.log(1);\n` produces stdout `console.warn(1);\n\n` and stderr `Applied 1 changes\n`. No-match interactive/update-all runs exit 1 and do not print `Applied 0 changes`.

Any `run --stdin --interactive` invocation is rejected before matching, including interactive view mode without a rewrite. It exits 7, writes nothing to stdout, and writes exactly:

```text
Error: Interactive mode is incompatible with parsing code from StdIn.
Help: `--interactive` needs StdIn, but it is used as source code. Please use files as input.
See also: https://ast-grep.github.io/guide/tooling-overview.html#parse-code-from-stdin

```

## Spec 21: Rule-test runner and snapshots

`test` requires a project and discovers test YAML through `testConfigs`, or accepts `-t/--test-dir`. In configuration-driven discovery, the snapshot directory comes from the selected `testConfigs[].snapshotDir`, with `__snapshots__` as the default. A relative configured value is resolved beneath that test directory; an absolute value remains absolute. In this configuration-driven mode, the accepted CLI option `--snapshot-dir VALUE` does not override the configured selection and its value is ignored. When `-t/--test-dir` explicitly selects the test directory, however, `--snapshot-dir VALUE` is used beneath that explicit test directory. For example, `test -t explicit-tests -U --snapshot-dir chosen-snaps` writes `explicit-tests/chosen-snaps/ID-snapshot.yml`. Other options are `-f/--filter REGEX`, `-U/--update-all`, `-i/--interactive`, `--skip-snapshot-tests`, `--include-off`, and `--color`. Update-all and skip-snapshot-tests conflict.

Malformed test YAML exits 8 with empty stdout and the header `Error: Cannot parse test case TEST_PATH`. For a test file containing `invalid yaml: [unclosed bracket`, the complete cause line is:

```text
╰▻ did not find expected ',' or ']' at line 2 column 1, while parsing a flow sequence at line 1 column 15
```

A test file has:

```yaml
id: rule-id
valid:
  - 'code that must produce no match'
invalid:
  - 'code that must produce at least one match'
```

Lists may be absent or empty and code strings may be multiline. A valid case that matches is `Noisy`; an invalid case with no match is `Missing`. Invalid cases also compare generated output to a per-rule snapshot unless snapshot checking is skipped. Missing or changed baselines are `Wrong` and show generated snapshot/diff details. `--update-all` creates or updates snapshots and marks cases `Updated`; a later identical run passes.

Each snapshot file has the literal top-level keys `id` and `snapshots`. `id` is the rule ID, and `snapshots` maps each invalid source string to its snapshot object. The serialized shape is:

```yaml
id: no-console
snapshots:
  console.log(1):
    fixed: console.warn(1)
    labels:
    - source: console.log(1)
      style: primary
      start: 0
      end: 14
```

The `fixed` key is present only when the rule has a fix. `labels` is always a sequence whose entries use the literal keys `source`, `style`, `start`, and `end`. Multiple test files for one rule use the same per-rule snapshot file.

In `Running N tests`, `N` is the number of selected test YAML documents, not the number of `valid`/`invalid` cases and not the number of distinct rule IDs. A document with absent or empty lists still contributes one. Two files for the same rule contribute two, receive two result lines, and contribute two to the final passed/failed count. Rule-ID filtering is regular-expression based and this count is taken after filtering.

The detailed layout starts exactly with `Running N tests\n\n----------- Case Details -----------\n`. The header is immediately followed by the first detail or document-result line; there is no additional blank line there. Each case detail block ends with a blank line, separating it from the next detail or result. Each selected document gets `PASS ID  STATUS`, `FAIL ID  STATUS`, or `SKIP ID  STATUS`, with exactly two spaces between the ID and the compact status sequence. Status characters follow case order: `.` is an ordinary passing case, `N` is Noisy, `M` is Missing, `W` is a missing or mismatched snapshot, and `U` is an updated snapshot. With both lists empty the line is `SKIP ID  `, the document is nevertheless counted as passed, and the leading count remains one. For more than 40 identical statuses, the counted aggregate is inserted into—not substituted for—the per-case compact sequence. In the observed 41-pass case, the exact result line is `PASS no-console  ....................Pass × 41.....................`: it contains 20 dots, `Pass × 41`, and 21 more dots.

An updated invalid case uses this detail form before its result line:

```text
[Updated] Rule ID's snapshot baseline has been updated.

  SOURCE
```

A Noisy case starts `[Noisy] Expect ID to report no issue, but some issues found in:`, a Missing case starts `[Missing] Expect rule ID to report issues, but none found in:`, and a Wrong case starts `[Wrong] No ID baseline found.` (or reports the mismatching baseline) followed by `Generated Snapshot:` and `For Code:`. Successful output has one blank line after the last document result and ends exactly `test result: ok. P passed; F failed;\n`. Expectation/snapshot failures exit 4, use `FAIL`, and replace the success summary with an `Error: test failed. ...` diagnostic.

Off rules are excluded unless `--include-off`. If a selected test document names a known off rule while off rules are excluded, the run succeeds and the document still contributes to `Running N tests` but not to the final passed count. The message is on stdout immediately after the count line; for one such document the prefix is exactly `Running 1 tests\nConfiguration not found! off-rule\n\n----------- Case Details -----------\n`. This differs from a filter regular expression that matches no test/rule ID at all: `test -f no-such-id` exits 3, writes nothing to stdout, and writes this exact stderr, including the final empty line:

```text
Error: Rule not found: no-such-id
Help: Rule with id 'no-such-id' not found in project configuration. Please make sure it exists.
See also: https://ast-grep.github.io/guide/tooling-overview.html#parse-code-from-stdin

```

## Spec 22: `new` scaffolding

`new` creates projects and project items. `-y/--yes` disables ordinary prompts and requires every needed `name` and, for rules/utils, `--lang`. In an empty directory with no discoverable project, `new --yes` defaults to project creation. It exits 0, writes nothing to stderr, creates the same files and configuration as `new project --yes`, and writes exactly:

```text
No sgconfig.yml found. Creating a new ast-grep project...
Your new ast-grep project has been created!
```

Inside an already discoverable project, the same omitted entity is instead a missing noninteractive argument. `new --yes` exits 22, writes nothing to stdout, and writes exactly:

```text
Error: Insufficient command line argument provided to use `--yes` option.
Help: You need to provide `entity` in command line to use non-interactive `new`.

```

For project items, project discovery precedes validation of the remaining noninteractive values: outside a discoverable project, `new rule --yes` exits 3 with the no-project diagnostic later in this section, even though `name` and `lang` are also absent. Once the required project context exists, a missing required noninteractive value exits 22 with empty stdout and one of the following exact stderr values:

```text
Error: Insufficient command line argument provided to use `--yes` option.
Help: You need to provide `name` in command line to use non-interactive `new`.

```

```text
Error: Insufficient command line argument provided to use `--yes` option.
Help: You need to provide `lang` in command line to use non-interactive `new`.

```

Each value ends with the displayed empty line: two newline bytes follow the Help sentence.

`new project --yes [NAME]` creates in the current directory (the optional name is descriptive and does not create a nested directory):

- `sgconfig.yml`
- `rules/.gitkeep`
- `rule-tests/.gitkeep`
- `utils/.gitkeep`

The `.gitkeep` files are empty. The exact configuration uses absolute paths and this layout:

```yaml
ruleDirs:
- /absolute/current/directory/rules
testConfigs:
- testDir: /absolute/current/directory/rule-tests
utilDirs:
- /absolute/current/directory/utils
```

Stdout is:

```text
Creating a new ast-grep project...
Your new ast-grep project has been created!
```

Creating a project within an existing project's directory tree must not overwrite configuration. It exits 17 with empty stdout and exactly this stderr, including the final empty line:

```text
Error: ast-grep project already exists.
Help: You are already inside a sub-folder of an ast-grep project. Try finding sgconfig.yml in ancestor directory?
See also: https://ast-grep.github.io/guide/scan-project.html

```

Filesystem creation errors are reported and partial configuration is not claimed as successful. Project creation writes its initial progress line before attempting all filesystem creation. For example, if the `rules` destination already exists as a regular file, `new project --yes` exits 1 with stdout exactly `Creating a new ast-grep project...\n` and stderr exactly `Error: File exists (os error 17)\n`; it does not print the success line.

`new rule NAME --lang LANG --yes` writes the rule to the sole configured rule directory and, by default, writes `NAME-test.yml` to the sole test directory. The rule message uses the resolved absolute rule path: `Created rules at ABSOLUTE_RULE_PATH`. The test message preserves the configured test-directory spelling: a relative `testConfigs[].testDir` produces `Created test at RELATIVE_TEST_PATH`, while an absolute test directory produces an absolute path. For example, with `testDir: rule-tests`, creating `My-Rule` prints `Created test at rule-tests/My-Rule-test.yml`. The exact rule template is:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/ast-grep/ast-grep/main/schemas/rule.json

id: NAME
message: Add your rule message here....
severity: error # error, warning, info, hint
language: CanonicalLanguage
rule:
  pattern: Your Rule Pattern here...
# utils: Extract repeated rule as local utility here.
# note: Add detailed explanation for the rule.
```

The exact test template, also used by `new test NAME --yes`, is:

```yaml
id: NAME
valid:
- "valid code"
invalid:
- "invalid code"
```

`new util NAME --lang LANG --yes` writes this to the sole `utilDirs` entry and prints `Created util at ABSOLUTE_PATH`:

```yaml
id: NAME
language: CanonicalLanguage
rule:
  pattern: Your Rule Pattern here...
# utils: Extract repeated rule as local utility here.
```

The project configuration and test template end with a newline. The generated rule and utility templates end immediately after the final period, without a trailing newline.

`new rule`, `new test`, and `new util` require a discoverable project. When none exists, they exit 3 with empty stdout and exactly this stderr, including the final empty line:

```text
Error: No ast-grep project configuration is found.
Help: You need to create an ast-grep project for this command. Try `sg new` to create one.
See also: https://ast-grep.github.io/guide/scan-project.html

```

Missing or empty test configuration exits 5 with this exact stderr:

```text
Error: No test file directory is configured.
Help: Fail to create a test file because the project `sgconfig.yml` does not specify any test configuration.
See also: https://ast-grep.github.io/guide/test-rule.html

```

If rule creation succeeds before automatic test creation discovers this condition, retain the rule and first write `Created rules at ABSOLUTE_PATH\n` to stdout, then emit the stderr diagnostic and exit 5. Missing `utilDirs` and `utilDirs: []` behave identically: they exit 5 with empty stdout and this exact stderr:

```text
Error: No util file directory is configured.
Help: Fail to create a utility rule because the project `sgconfig.yml` does not specify any utils directory.
See also: https://ast-grep.github.io/guide/rule-config/utility-rule.html

```

Each of these three-line diagnostics ends with the displayed empty line. More than one candidate test/util directory requires interactive selection and, in a non-TTY invocation even with `--yes`, exits 1 with empty stdout and stderr exactly `Error: The input device is not a TTY\n`. This one-line diagnostic has one terminating newline and no extra blank line.

Existing target files are never overwritten and cause exit 17 with empty stdout. `PATH` is the destination spelling used by the command: rule and utility directory paths are resolved against the configuration and printed as absolute paths; a relative `testConfigs[].testDir` remains relative, while an absolute test directory remains absolute. Stderr is exactly:

```text
Error: File `PATH` already exists.
Help: The item you want to create already exists. Try editing the existing file or create a new one with a different name?

```

This applies identically to existing rule `NAME.yml`, test `NAME-test.yml`, and utility `NAME.yml` targets. The backticks, period after `exists`, question mark after `name`, and final empty line are required. Names preserve case, Unicode, spaces, dots, hyphens, underscores, digits, and other YAML-safe characters in both filenames and unquoted `id` lines. Empty names create `.yml` and `-test.yml`. Names are joined directly to the configured directory before appending the suffix: absolute names and `..` therefore follow ordinary platform path-join/normalization behavior. On the tested platform, a name such as `util/name` whose intermediate destination directory does not exist exits 1 with empty stdout and exact stderr `Error: No such file or directory (os error 2)\n`. A rule, test, or utility name that makes its destination filename exceed the platform limit likewise exits 1 with empty stdout and exact stderr `Error: File name too long (os error 36)\n`. These one-line operating-system diagnostics have one terminating newline and no extra blank line.

## Spec 23: Debug queries, completions, and diagnostics

`run --debug-query` requires explicit `--lang` and defaults to `pattern`. For a valid single-node query, it writes the debug tree to stderr:

- `pattern` starts `Debug Pattern:` and shows matcher nodes, AST kinds, field labels, and `MetaVar $X`/`MetaVar $$$X` nodes.
- `ast` starts `Debug AST:` and shows named tree-sitter nodes and `(row,column)-(row,column)` ranges.
- `cst` starts `Debug CST:` and also shows unnamed punctuation/tokens and `MISSING` nodes.
- `sexp` starts `Debug Sexp:` and prints a balanced tree-sitter S-expression.

Debugging works for the supported language-specific syntax. `--color=always` styles tree kinds/fields; `--color=never` contains no escapes. An invalid format lists `pattern, ast, cst, sexp`. `--debug-query` is valid together with `--selector`: the selector first extracts that node, the debug pattern displays the selected node (for example it starts with `method_definition`), and matching proceeds normally.

The parsed-tree formats `ast`, `cst`, and `sexp` are emitted before single-node pattern validation, while the default `pattern` debug representation requires a valid pattern and is not emitted for a multi-node query. Therefore `executable -p 'foo;bar;' -l js --debug-query=ast` exits 8, writes nothing to stdout, and writes the AST before the validation error, exactly:

```text
Debug AST:
program (0,0)-(0,8)
  expression_statement (0,0)-(0,4)
    identifier (0,0)-(0,3)
  expression_statement (0,4)-(0,8)
    identifier (0,4)-(0,7)

Error: Cannot parse query as a valid pattern.
Help: The pattern either fails to parse or contains error. Please refer to pattern syntax guide.
See also: https://ast-grep.github.io/guide/pattern-syntax.html

✖ Caused by
╰▻ Multiple AST nodes are detected. Please check the pattern source `foo;bar;`.

```

The same query with bare `--debug-query` still emits no `Debug Pattern` and writes only the validation-diagnostic portion above.

`completions SHELL` emits a complete native completion script for exactly `bash`, `elvish`, `fish`, `powershell`, or `zsh`, reflecting the complete command/options tree in this specification. With no argument it infers the flavor from the basename of `$SHELL` (for example `/bin/bash`, `/usr/bin/zsh`, `/usr/bin/fish`). If inference fails, exit 10, write nothing to stdout, and print the following to stderr followed by one empty line (the stderr suffix is `cli.html\n\n`):

```text
Error: Can not infer which shell to generate completions.
Help: Either specify shell flavor by `sg completions [SHELL]` or set correct `SHELL` environment.
See also: https://ast-grep.github.io/reference/cli.html

```

An invalid explicit shell is an argument error and lists the five possible values. The generated scripts describe the executable's command tree. `executable completions --help` exits 0, writes nothing to stderr, and its stdout is exactly:

```text
Generate shell completion script

Usage: executable completions [OPTIONS] [SHELL]

Arguments:
  [SHELL]  Output the completion file for given shell. If not provided, shell flavor will be inferred from environment [possible values: bash, elvish, fish, powershell, zsh]

Options:
  -c, --config <CONFIG_FILE>  Path to ast-grep root config, default is sgconfig.yml
  -h, --help                  Print help
```

Argument parsing errors exit 2 and ordinarily use standard `error: ...`, `Usage: ...`, and `For more information, try '--help'.` formatting. The no-command full-help exception is specified in Spec 1. Operational errors go to stderr as an `Error:` line, usually followed by `Help:` and sometimes `See also:`. Preserve a causal chain when present using a `✖ Caused by` section and `╰▻` cause lines, including YAML line/column or OS error details.

An invalid JSON style is an argument-parsing error with no usage line. For example, `run -p foo -l js --json=invalid` exits 2, writes nothing to stdout, and writes exactly:

```text
error: invalid value 'invalid' for '--json[=<STYLE>]'
  [possible values: pretty, stream, compact]

For more information, try '--help'.
```

The significant operational exit codes are:

| Code | Meaning |
| ---: | --- |
| 0 | command succeeded; for scan, no error-severity finding |
| 1 | run found no match, a directly fatal file selection/traversal operation failed, or scan found error diagnostics; recoverable errors encountered during `--follow` do not force this status when a match is found |
| 2 | invalid/missing/conflicting command-line option |
| 3 | project/rule/language selection is unavailable or ambiguous |
| 4 | rule test expectations or snapshots failed |
| 5 | configured test/util destination is absent |
| 6 | configuration or rule path cannot be read |
| 7 | interactive mode is incompatible with stdin |
| 8 | YAML, rule, pattern, kind, test, transform, or validation parse failure |
| 9 | CLI glob construction failed |
| 10 | completion shell cannot be inferred |
| 17 | project or output item already exists |
| 22 | `new --yes` lacks a required CLI value |
| 33 | a configured `languageGlobs` language is unsupported |
| 79 | a custom-language dynamic library cannot be selected or loaded |

Errors identify the relevant rule, utility, metavariable, field, path, or invalid value when the corresponding diagnostic forms in this specification show it. The malformed explicitly selected configuration exception is specified in Spec 6: its parse diagnostic identifies YAML positions but does not echo the selected configuration filename. In particular, reject conflicting output modes, `--update-all` without a run rewrite, undefined variables and utility references, duplicate rule IDs, and malformed configuration without hanging, silently succeeding, or printing a language-runtime traceback. Undefined names in a rewrite transform follow the `rewriters`-section-dependent validation behavior in Spec 12.

Stdin ambiguity rejection does not apply to multiple YAML documents passed in one `--inline-rules` value. `scan --inline-rules DOCS --stdin` accepts such documents, evaluates all of them, emits matches for each matching rule, and exits according to normal finding severity. For example, two inline documents matching `one()` and `two()` both report their respective matches from stdin. Other stdin rule-selection ambiguity continues to use the `Only one rule can scan code from StdIn.` diagnostic described by the command.
