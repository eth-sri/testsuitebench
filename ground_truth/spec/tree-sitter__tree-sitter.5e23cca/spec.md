# Tree-sitter-compatible command-line executable

The required artifact is one executable file named exactly `executable`. The words “must”, “should”, and “may” below are normative. All paths are interpreted relative to the process working directory unless explicitly described otherwise. Output is UTF-8. Examples normally show ANSI-styled headings as plain text for readability; Spec 37 states when the escape bytes themselves are mandatory.

## Spec 1

`executable` must implement a Tree-sitter-compatible parser-generator CLI whose fixed product version is `0.27.0`. It must run as a normal POSIX executable, accept command-line arguments and optional standard input, create files beneath user-selected directories, invoke available native build tools when compilation is requested, and support concurrent invocations without sharing mutable temporary state.

Successful informational operations normally return 0. Runtime failures return 1 except for the two explicitly documented fuzz corpus-discovery cases in Spec 29, which print an `Error:` diagnostic but return 0, and the playground grammar-loading panics in Specs 30 and 31, which return 101. Command-line syntax, missing required arguments, invalid enum/numeric values, unknown commands/options, and declared option conflicts return 2. Help goes only to stdout and returns 0; argument diagnostics go only to stderr. Every textual output ends with a newline unless a described generated file format says otherwise. Outside the explicit fuzz exceptions, a failed operation must not fabricate a successful result.

## Spec 2

With `--version` or `-V`, print exactly `tree-sitter 0.27.0\n` to stdout and nothing to stderr. A leading global `--version` takes precedence over later arguments. With `--help` or `-h`, print the main help below exactly. A leading help option likewise takes precedence over later arguments. With no arguments, print the same main help to stderr and return 2.

```text
tree-sitter 0.27.0
Max Brunsfeld <maxbrunsfeld@gmail.com>
Amaan Qureshi <amaanq12@gmail.com>
Generates and tests parsers

Usage: executable <COMMAND>

Commands:
  init-config     Generate a default config file
  init            Initialize a grammar repository
  generate        Generate a parser
  build           Compile a parser
  parse           Parse files
  test            Run a parser's tests
  version         Display or increment the version of a grammar
  fuzz            Fuzz a parser
  query           Search files using a syntax tree query
  highlight       Highlight a file
  tags            Generate a list of tags
  playground      Start local playground for a parser in the browser
  dump-languages  Print info about all known language parsers
  complete        Generate shell completions

Options:
  -h, --help     Print help
  -V, --version  Print version
```

Recognize aliases `i` for `init`, `g` and `gen` for `generate`, `b` for `build`, `p` for `parse`, `t` for `test`, `f` for `fuzz`, and `q` for `query`. Alias behavior and help are identical to the named command. An unknown command must return 2 with `error: unrecognized subcommand '<value>'`, a usage line, and `For more information, try '--help'.` An unknown option must similarly identify the unexpected argument. `--` ends option parsing, and both `--option value` and `--option=value` forms are accepted. Compatible boolean short options may be grouped, such as parse `-jq`. Because `-j` is boolean, `parse -j=foo` is rejected with status 2, no stdout, and this exact stderr (the invalid grouped suffix is rendered as `-=`):

```text
error: unexpected argument '-=' found

  tip: to pass '-=' as a value, use '-- -='

Usage: executable parse [OPTIONS] [PATHS]...

For more information, try '--help'.
```

A command-local `--version` is rejected unless that command defines it.

Unknown options use clap's value-passing or similar-option tip when one is applicable, and the usage synopsis is narrowed to the suggested/participating argument. These invocations return 2, write nothing to stdout, and have the following exact stderr values:

- `generate --grammar-path`:

```text
error: unexpected argument '--grammar-path' found

  tip: to pass '--grammar-path' as a value, use '-- --grammar-path'

Usage: executable generate [OPTIONS] [GRAMMAR_PATH]

For more information, try '--help'.
```

- `generate --abi-version 15`:

```text
error: unexpected argument '--abi-version' found

  tip: a similar argument exists: '--abi'

Usage: executable generate --abi <VERSION> [GRAMMAR_PATH]

For more information, try '--help'.
```

- `test --filter foo`:

```text
error: unexpected argument '--filter' found

  tip: a similar argument exists: '--file-name'

Usage: executable test --file-name <FILE_NAME>

For more information, try '--help'.
```

## Spec 3

Help processing is eager: `command --help` succeeds and ignores any subsequent invalid option. The `init` help must be exactly:

```text
Initialize a grammar repository

Usage: executable init [OPTIONS]

Options:
  -u, --update                       Update outdated files
  -p, --grammar-path <GRAMMAR_PATH>  The path to the tree-sitter grammar directory
  -h, --help                         Print help
```

The `generate` help must be exactly:

```text
Generate a parser

Usage: executable generate [OPTIONS] [GRAMMAR_PATH]

Arguments:
  [GRAMMAR_PATH]  The path to the grammar file

Options:
  -l, --log
          Show debug log during generation
      --abi <VERSION>
          Select the language ABI version to generate (default 15).
          Use --abi=latest to generate the newest supported version (15). [env: TREE_SITTER_ABI_VERSION=]
      --no-parser
          Only generate `grammar.json` and `node-types.json`
  -b, --build
          Deprecated: use the `build` command
  -0, --debug-build
          Deprecated: use the `build` command
      --libdir <PATH>
          Deprecated: use the `build` command
  -o, --output <DIRECTORY>
          The path to output the generated source files
      --report-states-for-rule <REPORT_STATES_FOR_RULE>
          Produce a report of the states for the given rule, use `-` to report every rule
      --json
          Deprecated: use --json-summary
      --json-summary
          Report conflicts in a JSON format
      --js-runtime <EXECUTABLE>
          The name or path of the JavaScript runtime to use for generating parsers, specify `native` to use the native `QuickJS` runtime [env: TREE_SITTER_JS_RUNTIME=] [default: node]
      --disable-optimizations
          Disable optimizations when generating the parser. Currently, this only affects the merging of compatible parse states
  -h, --help
          Print help
```

## Spec 4

The canonical interfaces for the remaining commands are as follows. Their `--help` output must describe every listed item, begin with the shown summary and `Usage: executable <command>`, go to stdout, and return 0.

- `build [OPTIONS] [PATH]`: `-w/--wasm`, `-o/--output <OUTPUT>`, `--reuse-allocator`, `-0/--debug`, `-v/--verbose`.
- `parse [OPTIONS] [PATHS]...`: `--paths`, `-p/--grammar-path`, `-l/--lib-path`, `--lang-name`, `--scope`, `-d/--debug[=quiet|normal|pretty]`, `-0/--debug-build`, `-D/--debug-graph`, `--dot`, `-x/--xml`, `-c/--cst`, `-s/--stat`, `--timeout`, `-t/--time`, `-q/--quiet`, repeatable `--edits`, `--encoding=utf8|utf16-le|utf16-be`, `--open-log`, deprecated `--json`, `-j/--json-summary`, `--config-path`, `-n/--test-number`, `-r/--rebuild`, and `--no-ranges`.
- `test [OPTIONS]`: `-i/--include`, `-e/--exclude`, `--file-name`, `-p/--grammar-path`, `-l/--lib-path`, `--lang-name`, `-u/--update`, `-d/--debug`, `-0/--debug-build`, `-D/--debug-graph`, `--open-log`, `--config-path`, `--show-fields`, `--stat=all|outliers-and-total|total-only`, `-r/--rebuild`, `--overview-only`, and `--json-summary`.
- `fuzz [OPTIONS]`: repeatable `-s/--skip`, `--subdir`, `-p/--grammar-path`, `--lib-path`, `--lang-name`, `--edits`, `--iterations`, `-i/--include`, `-e/--exclude`, `--log-graphs`, `-l/--log`, and `-r/--rebuild`.
- `query [OPTIONS] <QUERY_PATH> [PATHS]...`: grammar/library/language selection, time, quiet, paths file, `--byte-range`, `--row-range`, `--containing-byte-range`, `--containing-row-range`, scope, `-c/--captures`, `--test`, config, test number, and rebuild.
- `highlight [OPTIONS] [PATHS]...`: `-H/--html`, `--css-classes`, `--check`, `--captures-path`, one-or-more `--query-paths`, scope, time, quiet, paths file, grammar path, config path, test number, rebuild, and encoding.
- `tags [OPTIONS] [PATHS]...`: scope, time, quiet, paths file, grammar path, config path, test number, and rebuild.
- `playground [OPTIONS]`: `-q/--quiet`, `--grammar-path`, and `-e/--export`; the serving address and port come from environment variables described later, not command-line options.
- `dump-languages [--config-path <CONFIG_PATH>]`.
- `complete -s/--shell <SHELL>` where values are `bash`, `elvish`, `fish`, `power-shell`, `zsh`, and `nushell`.
- `version [-p/--grammar-path <GRAMMAR_PATH>] [--bump patch|minor|major] [VERSION]`.
- `init-config` has no options except help.

Option conflicts must be checked before runtime work. In particular, grammar path conflicts with explicit rebuild; test number conflicts with source paths or a paths file; parse `--json` conflicts with `--json-summary` and `--stat`; generate `--json` conflicts with both `--json-summary` and `--report-states-for-rule`; and version positional `VERSION` conflicts with `--bump`. Invalid enum values show their possible values. Numeric parse failures identify the value and option. A missing required query path or completion shell is an argument error.

Conflict diagnostics return 2, write nothing to stdout, and specialize the usage line to the arguments that participated in the conflict. The following invocations have these exact stderr values:

- `test --grammar-path DIR --rebuild`:

```text
error: the argument '--grammar-path <GRAMMAR_PATH>' cannot be used with '--rebuild'

Usage: executable test --grammar-path <GRAMMAR_PATH>

For more information, try '--help'.
```

- `highlight --grammar-path DIR --rebuild`:

```text
error: the argument '--grammar-path <GRAMMAR_PATH>' cannot be used with '--rebuild'

Usage: executable highlight --grammar-path <GRAMMAR_PATH> [PATHS]...

For more information, try '--help'.
```

- `fuzz --grammar-path DIR --rebuild`:

```text
error: the argument '--grammar-path <GRAMMAR_PATH>' cannot be used with '--rebuild'

Usage: executable fuzz --grammar-path <GRAMMAR_PATH>

For more information, try '--help'.
```

- `parse --paths FILE --test-number 1`:

```text
error: the argument '--paths <PATHS_FILE>' cannot be used with '--test-number <TEST_NUMBER>'

Usage: executable parse --paths <PATHS_FILE> [PATHS]...

For more information, try '--help'.
```

- `parse --test-number 1 SOURCE`:

```text
error: the argument '--test-number <TEST_NUMBER>' cannot be used with '[PATHS]...'

Usage: executable parse --test-number <TEST_NUMBER> [PATHS]...

For more information, try '--help'.
```

- `highlight --test-number 1 SOURCE`:

```text
error: the argument '--test-number <TEST_NUMBER>' cannot be used with '[PATHS]...'

Usage: executable highlight --test-number <TEST_NUMBER> [PATHS]...

For more information, try '--help'.
```

- `highlight --paths FILE --test-number 1`:

```text
error: the argument '--paths <PATHS_FILE>' cannot be used with '--test-number <TEST_NUMBER>'

Usage: executable highlight --paths <PATHS_FILE> [PATHS]...

For more information, try '--help'.
```

- `version 1.2.3 --bump patch`:

```text
error: the argument '[VERSION]' cannot be used with '--bump <BUMP>'

Usage: executable version <VERSION>

For more information, try '--help'.
```

- `parse --json --json-summary`:

```text
error: the argument '--json' cannot be used with '--json-summary'

Usage: executable parse --json <PATHS>...

For more information, try '--help'.
```

- `parse --stat --json`:

```text
error: the argument '--stat' cannot be used with '--json'

Usage: executable parse --stat <PATHS>...

For more information, try '--help'.
```

- `generate --json --report-states-for-rule source_file`:

```text
error: the argument '--json' cannot be used with '--report-states-for-rule <REPORT_STATES_FOR_RULE>'

Usage: executable generate --json [GRAMMAR_PATH]

For more information, try '--help'.
```

- `parse --grammar-path DIR --rebuild`:

```text
error: the argument '--grammar-path <GRAMMAR_PATH>' cannot be used with '--rebuild'

Usage: executable parse --grammar-path <GRAMMAR_PATH> [PATHS]...

For more information, try '--help'.
```

The following precision-sensitive help texts must be emitted exactly (including indentation and final newline):

```text
Compile a parser

Usage: executable build [OPTIONS] [PATH]

Arguments:
  [PATH]  The path to the grammar directory

Options:
  -w, --wasm             Build a Wasm module instead of a dynamic library
  -o, --output <OUTPUT>  The path to output the compiled file
      --reuse-allocator  Make the parser reuse the same allocator as the library
  -0, --debug            Compile a parser in debug mode
  -v, --verbose          Display verbose build information
  -h, --help             Print help
```

```text
Parse files

Usage: executable parse [OPTIONS] [PATHS]...

Arguments:
  [PATHS]...  The source file(s) to use

Options:
      --paths <PATHS_FILE>           The path to a file with paths to source file(s)
  -p, --grammar-path <GRAMMAR_PATH>  The path to the tree-sitter grammar directory, implies --rebuild
  -l, --lib-path <LIB_PATH>          The path to the parser's dynamic library
      --lang-name <LANG_NAME>        If `--lib-path` is used, the name of the language used to extract the library's language function
      --scope <SCOPE>                Select a language by the scope instead of a file extension
  -d, --debug [<DEBUG>]              Show parsing debug log [possible values: quiet, normal, pretty]
  -0, --debug-build                  Compile a parser in debug mode
  -D, --debug-graph                  Produce the log.html file with debug graphs
      --dot                          Output the parse data with graphviz dot
  -x, --xml                          Output the parse data in XML format
  -c, --cst                          Output the parse data in a pretty-printed CST format
  -s, --stat                         Show parsing statistic
      --timeout <TIMEOUT>            Interrupt the parsing process by timeout (µs)
  -t, --time                         Measure execution time
  -q, --quiet                        Suppress main output
      --edits <EDITS>...             Apply edits in the format: \"row,col|position delcount insert_text\", can be supplied multiple times
      --encoding <ENCODING>          The encoding of the input files [possible values: utf8, utf16-le, utf16-be]
      --open-log                     Open `log.html` in the default browser, if `--debug-graph` is supplied
      --json                         Deprecated: use --json-summary
  -j, --json-summary                 Output parsing results in a JSON format
      --config-path <CONFIG_PATH>    The path to an alternative config.json file
  -n, --test-number <TEST_NUMBER>    Parse the contents of a specific test
  -r, --rebuild                      Force rebuild the parser
      --no-ranges                    Omit ranges in the output
  -h, --help                         Print help
```

```text
Search files using a syntax tree query

Usage: executable query [OPTIONS] <QUERY_PATH> [PATHS]...

Arguments:
  <QUERY_PATH>  Path to a file with queries
  [PATHS]...    The source file(s) to use

Options:
  -p, --grammar-path <GRAMMAR_PATH>
          The path to the tree-sitter grammar directory, implies --rebuild
  -l, --lib-path <LIB_PATH>
          The path to the parser's dynamic library
      --lang-name <LANG_NAME>
          If `--lib-path` is used, the name of the language used to extract the library's language function
  -t, --time
          Measure execution time
  -q, --quiet
          Suppress main output
      --paths <PATHS_FILE>
          The path to a file with paths to source file(s)
      --byte-range <BYTE_RANGE>
          The range of byte offsets in which the query will be executed
      --row-range <ROW_RANGE>
          The range of rows in which the query will be executed
      --containing-byte-range <CONTAINING_BYTE_RANGE>
          The range of byte offsets in which the query will be executed. Only the matches that are fully contained within the provided byte range will be returned
      --containing-row-range <CONTAINING_ROW_RANGE>
          The range of rows in which the query will be executed. Only the matches that are fully contained within the provided row range will be returned
      --scope <SCOPE>
          Select a language by the scope instead of a file extension
  -c, --captures
          Order by captures instead of matches
      --test
          Whether to run query tests or not
      --config-path <CONFIG_PATH>
          The path to an alternative config.json file
  -n, --test-number <TEST_NUMBER>
          Query the contents of a specific test
  -r, --rebuild
          Force rebuild the parser
  -h, --help
          Print help
```

```text
Highlight a file

Usage: executable highlight [OPTIONS] [PATHS]...

Arguments:
  [PATHS]...  The source file(s) to use

Options:
  -H, --html                           Generate highlighting as an HTML document
      --css-classes                    When generating HTML, use css classes rather than inline styles
      --check                          Check that highlighting captures conform strictly to standards
      --captures-path <CAPTURES_PATH>  The path to a file with captures
      --query-paths <QUERY_PATHS>...   The paths to files with queries
      --scope <SCOPE>                  Select a language by the scope instead of a file extension
  -t, --time                           Measure execution time
  -q, --quiet                          Suppress main output
      --paths <PATHS_FILE>             The path to a file with paths to source file(s)
  -p, --grammar-path <GRAMMAR_PATH>    The path to the tree-sitter grammar directory, implies --rebuild
      --config-path <CONFIG_PATH>      The path to an alternative config.json file
  -n, --test-number <TEST_NUMBER>      Highlight the contents of a specific test
  -r, --rebuild                        Force rebuild the parser
      --encoding <ENCODING>            The encoding of the input files [possible values: utf8, utf16-le, utf16-be]
  -h, --help                           Print help
```

```text
Generate shell completions

Usage: executable complete --shell <SHELL>

Options:
  -s, --shell <SHELL>  The shell to generate completions for [possible values: bash, elvish, fish, power-shell, zsh, nushell]
  -h, --help           Print help
```

```text
Print info about all known language parsers

Usage: executable dump-languages [OPTIONS]

Options:
      --config-path <CONFIG_PATH>  The path to an alternative config.json file
  -h, --help                       Print help
```

```text
Display or increment the version of a grammar

Usage: executable version [OPTIONS] [VERSION]

Arguments:
  [VERSION]
          The version to bump to
          
          Examples:
              tree-sitter version: display the current version
              tree-sitter version <version>: bump to specified version
              tree-sitter version --bump <level>: automatic bump

Options:
  -p, --grammar-path <GRAMMAR_PATH>
          The path to the tree-sitter grammar directory

      --bump <BUMP>
          Automatically bump from the current version
          
          [possible values: patch, minor, major]

  -h, --help
          Print help (see a summary with '-h')
```

The remaining stable help texts are:

```text
Run a parser's tests

Usage: executable test [OPTIONS]

Options:
  -i, --include <INCLUDE>            Only run corpus test cases whose name matches the given regex
  -e, --exclude <EXCLUDE>            Only run corpus test cases whose name does not match the given regex
      --file-name <FILE_NAME>        Only run corpus test cases from a given filename
  -p, --grammar-path <GRAMMAR_PATH>  The path to the tree-sitter grammar directory, implies --rebuild
  -l, --lib-path <LIB_PATH>          The path to the parser's dynamic library
      --lang-name <LANG_NAME>        If `--lib-path` is used, the name of the language used to extract the library's language function
  -u, --update                       Update all syntax trees in corpus files with current parser output
  -d, --debug                        Show parsing debug log
  -0, --debug-build                  Compile a parser in debug mode
  -D, --debug-graph                  Produce the log.html file with debug graphs
      --open-log                     Open `log.html` in the default browser, if `--debug-graph` is supplied
      --config-path <CONFIG_PATH>    The path to an alternative config.json file
      --show-fields                  Force showing fields in test diffs
      --stat <STAT>                  Show parsing statistics [possible values: all, outliers-and-total, total-only]
  -r, --rebuild                      Force rebuild the parser
      --overview-only                Show only the pass-fail overview tree
      --json-summary                 Output the test summary in a JSON format
  -h, --help                         Print help
```

```text
Fuzz a parser

Usage: executable fuzz [OPTIONS]

Options:
  -s, --skip <SKIP>                  List of test names to skip
      --subdir <SUBDIR>              Subdirectory to the language
  -p, --grammar-path <GRAMMAR_PATH>  The path to the tree-sitter grammar directory, implies --rebuild
      --lib-path <LIB_PATH>          The path to the parser's dynamic library
      --lang-name <LANG_NAME>        If `--lib-path` is used, the name of the language used to extract the library's language function
      --edits <EDITS>                Maximum number of edits to perform per fuzz test (Default: 3)
      --iterations <ITERATIONS>      Number of fuzzing iterations to run per test (Default: 10)
  -i, --include <INCLUDE>            Only fuzz corpus test cases whose name matches the given regex
  -e, --exclude <EXCLUDE>            Only fuzz corpus test cases whose name does not match the given regex
      --log-graphs                   Enable logging of graphs and input
  -l, --log                          Enable parser logging
  -r, --rebuild                      Force rebuild the parser
  -h, --help                         Print help
```

```text
Generate a list of tags

Usage: executable tags [OPTIONS] [PATHS]...

Arguments:
  [PATHS]...  The source file(s) to use

Options:
      --scope <SCOPE>                Select a language by the scope instead of a file extension
  -t, --time                         Measure execution time
  -q, --quiet                        Suppress main output
      --paths <PATHS_FILE>           The path to a file with paths to source file(s)
  -p, --grammar-path <GRAMMAR_PATH>  The path to the tree-sitter grammar directory, implies --rebuild
      --config-path <CONFIG_PATH>    The path to an alternative config.json file
  -n, --test-number <TEST_NUMBER>    Generate tags from the contents of a specific test
  -r, --rebuild                      Force rebuild the parser
  -h, --help                         Print help
```

```text
Start local playground for a parser in the browser

Usage: executable playground [OPTIONS]

Options:
  -q, --quiet                        Don't open in default browser
      --grammar-path <GRAMMAR_PATH>  Path to the directory containing the grammar and Wasm files
  -e, --export <EXPORT>              Export playground files to specified directory instead of serving them
  -h, --help                         Print help
```

`init-config --help` is exactly:

```text
Generate a default config file

Usage: executable init-config

Options:
  -h, --help  Print help
```

## Spec 5

Configuration is JSON. Its search precedence is: a command’s `--config-path`; `$TREE_SITTER_DIR/config.json`; `$XDG_CONFIG_HOME/tree-sitter/config.json`; `$HOME/.config/tree-sitter/config.json`; then legacy `$HOME/.tree-sitter/config.json`. An explicit path must override all valid lower-priority files. Missing explicit files and malformed explicit JSON are fatal and name the path; malformed JSON diagnostics begin `Bad JSON config` and include parse location. In particular, `dump-languages --config-path /nonexistent/config.json` returns 1, writes nothing to stdout, and, with the mandatory heading escape bytes from Spec 37, writes the text `Error: No such file or directory (os error 2) (/nonexistent/config.json)\n` to stderr; the path belongs in parentheses after the operating-system message. `TREE_SITTER_DIR` affects user configuration only, never the grammar directory used by `version`.

The object may contain `parser-directories` (array of directory names) and `theme` (capture-style map). A missing configuration or missing/empty parser-directory list is not fatal for discovery commands; emit this warning to stderr, with the `Warning:` heading yellow as specified in Spec 37:

```text
Warning: You have not configured any parser directories!
Please run `tree-sitter init-config` and edit the resulting
configuration file to indicate where we should look for
language grammars.

```

The warning has an additional newline after `language grammars.`, so it ends with a blank line. Do not emit it when a nonempty list is configured. Nonexistent listed directories are silently ignored. `NO_COLOR`, including `NO_COLOR=1`, does not suppress the heading's ANSI escapes.

## Spec 6

`init-config` creates parent directories and writes `config.json` at the selected default location. On success it writes `Saved initial configuration to <absolute-path>` to stderr, nothing to stdout, and returns 0. If the file exists, return 1, preserve it byte-for-byte, write nothing to stdout, and write `Error: Remove your existing config file first: <path>` to stderr with the mandatory heading coloring from Spec 37.

The default has exactly six parser directories, formed by appending `github`, `src`, `source`, `projects`, `dev`, and `git` to `$HOME`, in that order. Its theme has exactly these values:

```json
{
  "attribute": {"color": 124, "italic": true},
  "comment": {"color": 245, "italic": true},
  "constant": 94,
  "constant.builtin": {"bold": true, "color": 94},
  "constructor": 136,
  "embedded": null,
  "function": 26,
  "function.builtin": {"bold": true, "color": 26},
  "keyword": 56,
  "module": 136,
  "number": {"bold": true, "color": 94},
  "operator": {"bold": true, "color": 239},
  "property": 124,
  "property.builtin": {"bold": true, "color": 124},
  "punctuation": 239,
  "punctuation.bracket": 239,
  "punctuation.delimiter": 239,
  "punctuation.special": 239,
  "string": 28,
  "string.special": 30,
  "tag": 18,
  "type": 23,
  "type.builtin": {"bold": true, "color": 23},
  "variable": 252,
  "variable.builtin": {"bold": true, "color": 252},
  "variable.parameter": {"color": 252, "underline": true}
}
```

Write readable, indented JSON with top-level keys `parser-directories` then `theme`.

## Spec 7

Language discovery scans every immediate child of every configured parser directory whose basename begins `tree-sitter-`; symlinked parser directories work, non-directories and other names are ignored, and duplicate/same-path entries do not crash. Each project is described primarily by `tree-sitter.json`. Discovery, explicit language loading, and `version` require a `metadata` object containing semantic `version` and a `grammars` array. Parser generation is the exception: for `generate`, a descriptor containing only `{"metadata":{"version":"1.2.3"}}` is valid and selects ABI 15; it need not contain `grammars`. Every grammar entry, when the array is required, requires a string `scope` field and can provide `name`, `path`, `file-types`, `first-line-regex`, `content-regex`, `injection-regex`, `highlights`, `injections`, `locals`, `tags`, and `external-files`. `external-files` accepts either an array of strings or one string; for example, `"external-files": "scanner.c"` is a valid one-file form. Multiple grammar entries produce distinct languages, with paths resolved relative to their project.

Discovery preserves the configured symlink spelling; it does not replace it with the real target spelling. The recorded parser path includes the grammar entry's relative `path`, whose default is `.`. Thus, for a descriptor-backed child `/tmp/link-location/tree-sitter-linked` with no explicit grammar `path`, `dump-languages` prints `parser: "/tmp/link-location/tree-sitter-linked/."`. It must not print the real target spelling or append `/src/parser.c`.

For backward compatibility, a project with no usable `tree-sitter.json` may be discovered from `src/grammar.json`; extract its top-level name even if trailing JSON is incomplete, provided the name occurs within the first three lines. Missing metadata in a present project descriptor produces a warning and this fallback. Empty/missing `grammars`, invalid descriptor JSON, invalid regular expressions, invalid semantic versions, or a grammar JSON without an extractable string name must produce contextual errors when the project is explicitly loaded for language selection or version handling; the metadata-only generation exception above still applies. During discovery, an invalid descriptor is a recoverable warning: write `Warning: Failed to parse <path>/tree-sitter.json -- <reason> at line L column C` to stderr, write nothing for that project to stdout, continue discovery, and retain status 0 if there is no other failure. Descriptor deserialization can report an earlier missing required field before reaching later malformed JSON. In particular, the exact contents `{"metadata": {} "grammars": []}` produce:

```text
missing field `version` at line 1 column 15
```

When an explicitly selected descriptor has an invalid `injection-regex`, `content-regex`, or `first-line-regex` and also lacks generated grammar artifacts, artifact loading takes precedence over regex compilation. The command proceeds to the missing `<project>/./src/grammar.json` failure. With a source path, that cause appears under `Error: Failed to load language for path "SOURCE"`; without a source path, it appears as `Error: Failed to load language in current directory:`.

Discovery accepts `external-files` entries without constraining their normalized paths to the grammar project. In particular, an entry of `../outside.c` is accepted: `dump-languages` returns 0 and still prints that language's record rather than diagnosing an escape. Error messages must distinguish descriptor reading/parsing, grammar compilation, library opening, symbol loading, and “No language found”.

## Spec 8

`dump-languages` performs discovery but does not compile languages. It writes records to stderr and nothing to stdout. For each language, in deterministic discovery order, print:

```text
name: NAME
scope: SCOPE
parser: "PATH"
highlights: Some(["queries/one.scm"])
file_types: ["ext1", "ext2"]
content_regex: Some(Regex("PATTERN"))
injection_regex: Some(Regex("PATTERN"))

```

Use `None` for absent optional fields. The parser path is resolved as described by the project entry. In contrast, `highlights` is printed as the descriptor's unresolved list of strings, preserving its entries and order; the single declaration `"highlights": ["queries/one.scm"]` prints exactly `highlights: Some(["queries/one.scm"])`, not a project-resolved path. Include every grammar from multi-grammar projects and every declared file type and regex represented by the fields above. `external-files` is accepted during discovery but is not printed as an additional field. An empty but explicitly configured parser list emits the configuration warning; nonempty lists containing no existing parsers produce no records and no error.

## Spec 9

Language selection supports four sources. `--lib-path FILE --lang-name NAME` loads a dynamic library and calls the exported symbol `tree_sitter_<normalized-name>`. A missing `--lang-name` derives a name from the library basename; hyphens normalize to underscores. A supplied language name without a library emits `Warning: --lang-name\` specified without --lib-path. This argument will be ignored.` and continues ordinary selection. A nonexistent, unreadable, or directory library and a missing/wrong symbol produce distinct fatal diagnostics naming the path/symbol.

`--grammar-path DIR` explicitly loads, generates if necessary, compiles, and selects the project in DIR. `--scope` selects an exact configured scope; an unknown or empty scope is fatal. When both selectors are supplied, scope lookup happens first and takes precedence over grammar-path loading. For a source `SOURCE`, an unconfigured `--scope source.one --grammar-path DIR SOURCE` returns 1 and wraps the scope cause in the ordinary source-path context, even if DIR contains a grammar declaring that scope:

```text
Error: Failed to load language for path "SOURCE"

Caused by:
    Unknown scope 'source.one'
```

Otherwise select by source path using, in descending relevance: exact registered filename, longest compound suffix (so `x.min.js` can match `min.js`), ordinary extension, first-line regex, and content regex. When multiple candidates claim a type, use matching regexes and the strongest/longest match to score them deterministically. Stdin is selectable via explicit scope or grammar path.

A source-path selection failure is formatted as an `Error:` line naming the source as `Failed to load language for path "..."`, one blank line, `Caused by:`, and a cause indented by four spaces. There is no blank line between a preceding warning and the `Error:` line. In particular, supplying `--lang-name` without `--lib-path` and then failing ordinary selection has this line and blank-line ordering:

```text
Warning: --lang-name` specified without --lib-path. This argument will be ignored.
Error: Failed to load language for path "PATH"

Caused by:
    No language found
```

## Spec 10

`generate` accepts a positional JavaScript or JSON grammar file, not a directory; omitted input means `grammar.js` in the current directory. A directory supplied positionally writes nothing to stdout, returns 1, and reports the following stderr text, with the `Error:` heading colored as in Spec 37:

```text
Error: Error when generating parser

Caused by:
    Path to a grammar file with `.js` or `.json` extension is required
```

Reject nonexistent input and extensions other than `.js` or `.json`. An invalid extension returns 1 and uses the cause `Unknown grammar file extension: "PATH"`. Every such generation failure, including through the `g` and `gen` aliases, begins with the same `Error: Error when generating parser` wrapper, followed by a blank line and `Caused by:`; do not replace it with a bare path error. When the omitted `grammar.js` does not exist, return 1 and make the cause line `Failed to load grammar.js -- No such file or directory (os error 2) (<absolute-path>/grammar.js)`. Default output is a sibling `src` directory; `-o/--output` selects another directory and creates it. Ordinary successful generation creates nonempty `grammar.json`, `node-types.json`, `parser.c`, `tree_sitter/parser.h`, `tree_sitter/alloc.h`, and `tree_sitter/array.h`. With `--no-parser`, successful generation creates only `grammar.json` and `node-types.json` in the selected output directory: it omits `parser.c` and all three `tree_sitter` headers. With custom output, do not also place generated artifacts in default `src`.

The JavaScript runtime is chosen by command option, then `TREE_SITTER_JS_RUNTIME`, then `node`. `native` means an embedded runtime and must require no external program. If a selected `bun` or `deno` executable is absent, return 1 and report an `Error: Error when generating parser` cause chain whose final line is respectively ``Failed to load grammar.js -- Failed to run `bun` -- No such file or directory (os error 2)`` or ``Failed to load grammar.js -- Failed to run `deno` -- No such file or directory (os error 2)``. The runtime accepts CommonJS `module.exports = grammar(...)`, assignments through `exports`, and ESM `export default grammar(...)`.

## Spec 11

The native grammar runtime must execute the JavaScript used to compute a grammar, not merely scrape source text. It supports lexical scope and closures; arrays and objects; property access; function/arrow/class syntax; template literals; destructuring; spreads; conditionals; loops; try/catch and thrown errors; standard string/number/array methods used by grammar files; `BigInt`; `process.env`; `__filename` and `__dirname`; `require` of relative `.js` and `.json` files, directory `index.js`, parent paths, nested chains, and packages in `node_modules`; and `module.exports` reassignment or `exports` property assignment.

`console.log`, `console.warn`, and `console.error` are always surfaced on stderr by the native runtime, independently of `--log`. For example, `console.log('hello', 42, {ok: true})` emits `hello 42 [object Object]\n` even without `--log`. Format primitives, `undefined`, `null`, arrays including nested arrays, plain objects, errors, and BigInts in the conventional JavaScript console form. A grammar that performs no console output remains quiet except for required status/errors. Syntax errors, missing modules, invalid required JSON, undefined references, uncaught throws, and missing directory indexes fail with nonzero status and a useful stack/location referencing `grammar.js`; native-runtime diagnostics identify `QuickJS error` and the JavaScript error class such as `SyntaxError`, `ReferenceError`, or `TypeError`.

## Spec 12

The grammar constructor requires a string `name` and a nonempty `rules` object. A missing or non-string name returns 1 with an `Error when generating parser` cause chain containing `Failed to load grammar.js -- QuickJS error: Message: Grammar's 'name' property must be a string.` If the `rules` property itself is absent, return 1, write nothing to stdout, and include `Failed to load grammar.js -- QuickJS error: Message: Cannot convert undefined or null to object` in the stderr cause chain. An empty rules object likewise returns 1 with a cause containing `Failed to load grammar.js -- QuickJS error: Message: Grammar must have at least one rule.` Rule callbacks receive `$`, whose properties are symbolic rule references. The native DSL also exposes `new RustRegex(value)`: it accepts a Rust-regex string that need not be valid JavaScript-regex syntax and serializes it as a `PATTERN` whose `value` is that string. Implement the following expression constructors and preserve them in generated grammar JSON:

- string literals and JavaScript regexes become `STRING` and `PATTERN` terminals, including Unicode, escapes, character classes, case-insensitive regex flags, and control characters; `/select/i` is serialized as `{"type": "PATTERN", "value": "select", "flags": "i"}`, retaining the unchanged pattern text and recording `i` separately rather than expanding the letters into character classes;
- `blank()` produces a `BLANK` expression and is valid even as the grammar's start rule; `seq(...)`, `choice(...)`, `repeat(...)`, `repeat1(...)`, and `optional(...)` compose sequences, alternatives, repetitions, and a choice with `BLANK`;
- `prec`, `prec.left`, `prec.right`, and `prec.dynamic` wrap rules and preserve numeric or named precedence plus associativity;
- `token(...)` and `token.immediate(...)` create lexical tokens, with immediate tokens disallowing intervening extras;
- `field(name, rule)` records named child fields;
- `alias(rule, $.named)` and `alias(rule, "anonymous")` rename nodes with correct namedness.

Support top-level `extras`, `externals`, `conflicts`, `inline`, `supertypes`, `word`, `precedences`, and reserved-word declarations. In `grammar.json`, each conflicts group is an array of rule-name strings (for example `["expression"]`), `inline` and `supertypes` are arrays of rule-name strings (for example `"helper"`), and `word` is a single rule-name string such as `"identifier"`; these declaration references are not serialized as `SYMBOL` objects. Hidden rule names begin with `_`. Extras may be terminals or named rules; external tokens interact correctly with a supplied scanner; conflicts resolve declared ambiguities; inlining removes intermediate nodes; supertypes remain queryable categories while their abstract nodes are omitted from ordinary trees; `word` enables keyword extraction. JavaScript duplicate object keys have normal JavaScript semantics: the final rule definition wins and generation succeeds. Reject illegal epsilon/empty constructs, invisible or terminal start rules where invalid, unresolved recursion, and unresolved parse-table conflicts with actionable diagnostics. Declared conflicts must allow the same ambiguous grammar to generate.

A rule listed in `inline` must be a nonterminal, not a lexical token. In particular, if `inline` contains `$._helper`, `_helper` is defined as `token.immediate(/x/i)`, and the project has no `tree-sitter.json`, generation returns 1, writes nothing to stdout, and emits this stderr text. The `Warning:` heading is yellow and the `Error:` heading is red as required by Spec 37; there is no blank line between the warning's second line and the error heading.

```text
Warning: No `tree-sitter.json` file found in your grammar, this file is required to generate with ABI 15. Using ABI version 14 instead.
This file can be set up with `tree-sitter init`. For more information, see https://tree-sitter.github.io/tree-sitter/cli/init.
Error: Error when generating parser

Caused by:
    Token `_helper` cannot be inlined
```

## Spec 13

`grammar.json` is indented valid JSON with the grammar `name`, a `rules` object containing all rule names, and top-level arrays/properties corresponding to grammar declarations. Expression nodes use uppercase types such as `SYMBOL`, `STRING`, `PATTERN`, `SEQ`, `CHOICE`, `REPEAT`, `REPEAT1`, `BLANK`, `PREC`, `PREC_LEFT`, `PREC_RIGHT`, `PREC_DYNAMIC`, `TOKEN`, `IMMEDIATE_TOKEN`, `FIELD`, and `ALIAS`, with `content`, `members`, `name`, and `value` as appropriate. Preserve regex flags and Unicode text.

`node-types.json` is an indented JSON array. Every public named node and every reachable anonymous literal has at least `type` and boolean `named`. Hidden rules are absent. Describe possible `children`, `fields`, `subtypes`, multiplicity, and requiredness accurately. Field annotations appear under the owning node. Aliases appear under their alias names. Supertypes list their concrete subtypes. For a grammar whose public rules are `source_file`, `statement`, `identifier`, and `value`, and whose only literal is `=`, the type set is exactly those five names.

## Spec 14

Generated `parser.c` must be valid C, compile, and expose `const TSLanguage *tree_sitter_<grammar_name>(void)`. It begins with `/* Automatically @generated by tree-sitter */`, includes `tree_sitter/parser.h`, and defines correct language/state/symbol/alias/token/field counts, symbol enums, symbol names/maps, lexers, parse tables/actions, and the final `TSLanguage` structure.

Despite the help text advertising ABI 15 as the normal default, generation with no `tree-sitter.json` must warn that no descriptor was found, say it is falling back to ABI version 14, emit `#define LANGUAGE_VERSION 14`, and omit a `.metadata` initializer. This fallback also ignores an explicit unsupported numeric ABI: with a valid `grammar.js`, no descriptor, and `generate --abi 999`, generation returns 0, emits the same fallback warning, and writes ABI 14 output. With a valid descriptor, the default is ABI 15. ABI 15 requires `tree-sitter.json` metadata and embeds `.major_version`, `.minor_version`, and `.patch_version`; `latest` means 15. A present descriptor with no `metadata` fails with status 1, no stdout, and a cause containing ``Failed to parse `<path>/tree-sitter.json` -- missing field `metadata` ``. An invalid `metadata.version` likewise fails with status 1 and a cause containing ``Failed to parse `<path>/tree-sitter.json` version as semver``; for the value `not-a-version`, the cause continues `-- unexpected character 'n' while parsing major version number`. Explicit supported versions and `TREE_SITTER_ABI_VERSION` are honored when a descriptor is present. When a word token exists, emit `ts_lex_keywords` and wire `keyword_lex_fn`. Supertypes under ABI 15 emit `ts_supertype_symbols`, `ts_supertype_map_slices`, and `ts_supertype_map_entries`. Externals emit external-token identifiers, symbol maps, valid-state tables, and scanner hooks. Fields are numbered from 1 in lexical field-name order and produce field-name/map tables. Aliases produce alias symbol and sequence tables.

Anonymous C identifiers must be legal and deterministic. In particular map `~ \` ! @ # $ % ^ & * ( ) - + = { } [ ] \\ | : ; " ' < > , . ? /` and space to suffixes `TILDE`, `BQUOTE`, `BANG`, `AT`, `POUND`, `DOLLAR`, `PERCENT`, `CARET`, `AMP`, `STAR`, `LPAREN`, `RPAREN`, `DASH`, `PLUS`, `EQ`, `LBRACE`, `RBRACE`, `LBRACK`, `RBRACK`, `BSLASH`, `PIPE`, `COLON`, `SEMI`, `DQUOTE`, `SQUOTE`, `LT`, `GT`, `COMMA`, `DOT`, `QMARK`, `SLASH`, and `SPACE`; map newline, carriage return, tab, and NUL to `LF`, `CR`, `TAB`, and `NULL`.

## Spec 15

Parser generation must construct correct LR parsing and lexing tables, including precedence, associativity, dynamic precedence, lexical conflicts, zero-width transitions, Unicode character classes, current-column-dependent lexing, immediate tokens, external scanners, extras, aliases, field maps, error recovery, and incremental edit reuse. The resulting parser must parse all valid strings described by the grammar, produce named/anonymous nodes and error/missing nodes with accurate byte and row/column ranges, and remain robust on invalid or very large inputs.

`--disable-optimizations` disables compatible-state merging while retaining equivalent parse behavior. `--log` emits state/token/error-recovery diagnostics. `--report-states-for-rule RULE` always emits the general tab-separated rule/state-count table; for a known rule it additionally emits that rule's detailed state report, and `-` reports all rules. An unknown rule is not validated: generation returns 0, emits the general table, emits no detailed section for the unknown name, and does not name that unknown value. For a valid conflict-free grammar, `generate --json-summary` returns 0 and writes nothing to either stdout or stderr; it does not emit an empty JSON object or array. Deprecated `--json` conflicts with `--json-summary` and with `--report-states-for-rule`. An unresolved conflict fails. Deprecated build-related generate flags remain accepted, emit their deprecation meaning, and perform their legacy action where applicable.

## Spec 16

`build` compiles an already generated grammar. The optional path is the grammar directory, defaulting to the current directory. Native build reads `src/parser.c`, optional `src/scanner.c` or `src/scanner.cc`, and generated headers, then creates a loadable platform dynamic library. Without `--output`, the artifact is written in the process's current working directory. Its basename comes from the grammar directory's basename: remove a leading `tree-sitter-` and append `.so`; if the directory basename does not begin with `tree-sitter-`, use `parser.so`. Thus, running `build` inside a directory named `tree-sitter-mini`, or running `build /path/to/tree-sitter-mini` from another directory, writes `mini.so` in the process's current working directory. A positional grammar path does not change that output directory. The grammar's declared name does not determine this basename; for example, a grammar declared as `mini` but stored in `tree-sitter-folder-label` produces `folder-label.so`. `--output` supports relative and absolute file paths and creates parent directories. Reject an output path that is a directory. Rebuilding twice is safe and replaces the selected default artifact. Different and multiple grammars remain isolated.

`--debug` compiles without optimization and with debug information; `--reuse-allocator` supplies the allocator-reuse compile definition; `--verbose` prints compiler commands/output; flags compose. On a successful verbose build, stdout is empty and stderr begins with three lines in this order: the compiler-command line beginning with the literal prefix `[] `, an empty line, and `LC_ALL=C`. Debug and other composed flags alter the compiler command. When the compiler writes diagnostics to stderr, the executable appends them after `LC_ALL=C`: the next line begins with the literal `stderr:` immediately followed by the compiler's first diagnostic, and the remaining diagnostic lines follow. A successful debug/reuse-allocator build can therefore have more than three stderr lines when the compiler emits warnings. If the current grammar lacks `src/grammar.json`, return 1 and report `Error: Failed to compile parser`, a blank line, `Caused by:`, and an indented `No such file or directory (os error 2) (<absolute-path>/src/grammar.json)` cause. Other missing grammar directories or `src/parser.c` are likewise fatal and mention the missing item. A successful library must be usable immediately by parse, query, and test via `--lib-path`.

## Spec 17

`build --wasm` creates a genuine WebAssembly module with magic bytes `00 61 73 6d`, exporting the grammar language function and incorporating an external scanner when present. The default name is `tree-sitter-<grammar-name>.wasm`; `--output` overrides it. It may invoke a harness-available WASI C/C++ toolchain. If `src/parser.c` is absent, Wasm build first attempts to load the top-level `grammar.js`, even when `src/grammar.json` is present. If that `grammar.js` is also absent, return 1 with this cause chain; this takes precedence over reporting the absent `parser.c` or inspecting the existing `src/grammar.json`:

```text
Error: Failed to load grammar.js -- No such file or directory (os error 2) (DIR/grammar.js)

Caused by:
    No such file or directory (os error 2) (DIR/grammar.js)
```

Malformed/missing `grammar.json` after the parser input is found, absent toolchain inputs, and compiler failures are fatal with chained diagnostics. A corrupted or missing Wasm module is rejected when loaded. Native-only flags may be combined without crashing, but output must remain the requested Wasm artifact.

## Spec 18

`parse` reads positional files plus every newline-delimited entry from `--paths FILE`, or reads stdin when no paths are supplied and a language can be selected. It does not discard blank lines in a paths file: a blank line becomes an empty pathname at that position. With an explicitly selected library/language, that entry returns 1 and emits `Error: Error reading ""`, a blank line, `Caused by:`, and `    No such file or directory (os error 2)`. Results for preceding entries remain on stdout, and entries after the empty pathname are not processed. Globs expand to matching files. When positional pathname/glob expansion finds no files, return 1 and report `Error: No files were found at or matched by the provided pathname/glob`. Entries read from `--paths` are passed to language selection before existence filtering: if that file contains only `/tmp/nonexistent.txt` and no language matches, return 1 with `Error: Failed to load language for path "/tmp/nonexistent.txt"`, a blank line, `Caused by:`, and `    No language found`. Multiple valid files are processed in order.

`--test-number N` reads the numbered corpus input from `test/corpus` beneath the process working directory; `--grammar-path` selects the grammar but does not re-root this corpus lookup. N is a positive integer. If the working directory has no corpus directory, return 1, write nothing to stdout, and, after any ordinary configuration warning, emit:

```text
Error: Test corpus directory not found in current directory, see https://tree-sitter.github.io/tree-sitter/creating-parsers/5-writing-tests
```

Input defaults to UTF-8. `--encoding utf8` and `utf16-le` decode their corresponding inputs. Although `utf16-be` is an accepted option value, it does not correctly decode a BOM-less big-endian UTF-16 input: the 16-byte encoding of `abc=12;\n` is rendered as an `ERROR` spanning `[0, 0] - [0, 16]`, followed by its failed-parse timing line, and returns 1. UTF-16 BOMs are detected when applicable. Correctly count rows/columns for the successfully decoded encodings, handle empty, one-byte, binary, Unicode, and large files without crashing, and report invalid encoding values as argument errors.

## Spec 19

Default parse output is a parenthesized concrete syntax tree on stdout. A named node renders as `(type [start_row, start_column] - [end_row, end_column] children...)`; anonymous tokens normally do not appear in this S-expression. Fields render as `field: (node ...)`. `ERROR` and `MISSING` nodes are visible and determine parse failure. `--no-ranges` removes every bracketed range but preserves tree shape and error information. Empty valid inputs still render their start node. A syntactically successful parse returns 0; a completed parse containing errors returns 1.

`--xml` emits one XML document with declaration, `<sources>`, and one `<source name="PATH">` per input. Node names become elements, ranges become `srow`, `scol`, `erow`, `ecol`, fields are represented without losing identity, terminal source text is XML-escaped, and multiline/empty sources remain well formed. `--cst` emits an indented, colorized pretty CST including ranges, node/error markers, field names, anonymous token text, and escaped newlines; `--no-ranges` also affects CST. The plain, XML, CST, and JSON-summary renderers must describe the same tree/result.

## Spec 20

`--json-summary` prints an indented JSON object containing:

```json
{
  "parse_summaries": [{
    "file": "path-or-stdin",
    "successful": true,
    "start": {"row": 0, "column": 0},
    "end": {"row": 1, "column": 0},
    "duration": {"secs": 0, "nanos": 1},
    "bytes": 1
  }],
  "cumulative_stats": {
    "successful_parses": 1,
    "total_parses": 1,
    "total_bytes": 1,
    "total_duration": {"secs": 0, "nanos": 1}
  },
  "source_count": 1
}
```

Measured values vary, but types, keys, success counts, byte counts, endpoints, source count, and aggregation must be correct. Every failed parse prints a one-line timing/error summary to stdout even when neither `--time` nor `--stat` was requested. In ordinary tree mode it follows that file's tree; with `--json-summary` it precedes the JSON object. `--quiet` suppresses the tree or main structured renderer but does not suppress this failed-parse summary, so a quiet failed parse has exactly the one summary line on stdout. The line has the form `PATH<TAB>Parse: ... ms<TAB>... bytes/ms<TAB>(ERROR [START] - [END])`.

`--time` writes its per-file timing lines to stdout, not stderr, using `PATH<TAB>Parse: ... ms<TAB>... bytes/ms` and appending the earliest error range for failures. A failed parse writes that path-bearing line even with `--stat` alone; it follows the file's tree and precedes the aggregate. A successful parse with `--stat` but without `--time` does not write a per-file timing line. `--stat` writes its aggregate to stdout as one semicolon-separated line in this exact field order:

```text
Total parses: T; successful parses: S; failed parses: F; success percentage: P%; average speed: R bytes/ms
```

The aggregate is separated from the per-file output by a blank line and followed by a blank line. Percentages have two decimals. An empty failed input reports `average speed: 0 bytes/ms`. Statistics aggregate multiple files and work with all failures, empty files, edits, quiet, XML, and libraries.

## Spec 21

Parse debugging supports `-d` (normal by default), `--debug=quiet|normal|pretty`, `--debug-graph`, `--open-log`, and `--dot`. Normal logs contain parser actions such as `new_parse`, lexing, consume, shift/reduce, accept, and done. Pretty mode colorizes them unless `NO_COLOR` is set; quiet debug mode avoids normal log chatter. Debug logging may coexist with quiet main output. Debug-graph writes a nonempty `log.html` in the working directory; larger inputs add graph content, and open-log attempts to open it only when requested. Dot mode invokes the available Graphviz command and diagnoses invocation failure.

`--timeout N` is microseconds; zero means unlimited. A positive value is checked by the parser's progress callback, so merely supplying a very small timeout does not force failure: if parsing completes before an interrupt is observed, the command reports the completed result and returns its ordinary success status. In particular, the successful large-input `--timeout 1 --time` case and its `--timeout 1 --json-summary` counterpart return 0. If the callback actually interrupts before producing a tree, the result is unsuccessful, its timing line ends in `(timed out)` when timing is enabled, and the command returns 1. Each `--edits` value is `POSITION DELETE_COUNT INSERT_TEXT`, where POSITION is a byte offset, `$` for EOF, or `row,column`. Apply edits sequentially to the previous tree/input, reparse incrementally, and report `Edit:` duration with timing.

`--edits` accepts one or more consecutive values and consumes a following non-option source pathname as another edit value. Put positional source paths before `--edits`, or put `--` between the final edit and following source paths. Thus `parse ... --time --edits '$ 0 gamma=4;' -- SOURCE` accepts `$` as EOF, returns 0, and prints both `Parse:` and `Edit:` timing fields. Without the delimiter, `parse ... --time --edits '$ 0 gamma=4;' SOURCE` returns 1 and writes exactly one newline to stdout; after the ordinary missing-configuration warning when applicable, stderr ends with this red-headed diagnostic:

```text
Error: Invalid edit string 'SOURCE'. Edit strings must match the pattern '<START_BYTE_OR_POSITION> <REMOVED_LENGTH> <NEW_TEXT>'
```

Validate all actual edit values and reject negative/non-numeric deletion lengths, nonexistent rows, columns past a line/newline, and offsets past EOF with `Failed to address an offset: N` or an equally precise contextual error.

## Spec 22

`query` discovers its positional/path-file source inputs before selecting a language or opening/compiling the query file. Consequently, nonexistent or unmatched source pathname/glob inputs take precedence over both language selection and query-file loading: return 1 with `Error: No files were found at or matched by the provided pathname/glob`. The missing source path is not named separately. Once at least one source has been found, select its language before opening or compiling the query file. A missing query file `Q` then returns 1 and uses this exact wrapper and layout:

```text
Error: Error reading query file Q

Caused by:
    No such file or directory (os error 2)
```

The supported query syntax includes named node patterns `(node)`, anonymous literals, wildcard `_`, fields, captures `@name`, comments, alternatives, quantifiers, anchors, and predicates used for text filtering, including equality/inequality and regex matching with multiple predicates. Reject malformed syntax with row/column and caret context; reject nonexistent node/field names with `Query compilation failed`. A missing paths-list file is likewise fatal with its contextual read wrapper.

Default output begins with the source path, then groups captures by match. A capture contained on one row includes its numeric capture index and captured text:

```text
path
  pattern: 0
    capture: 0 - rule, start: (0, 0), end: (0, 5), text: `hello`
```

A capture spanning more than one row instead omits both the numeric index and captured text, even for predicate-filtered and containing-range matches:

```text
path
  pattern: 0
    capture: rule, start: (0, 0), end: (5, 0)
```

`-c/--captures` orders globally by capture and uses lines of the form `    pattern:  0, capture: 0 - rule, start: (0, 0), end: (3, 0), text: \`TEXT\``. `--quiet` prints only each processed filename. Valid queries with no matches still print the filename. `--time` appends a duration with `ns`, `µs`, `ms`, or `s`.

## Spec 23

Query ranges use `start:end`, not `start..end`. Byte ranges and zero-based row ranges restrict the execution interval. Containing ranges instead retain only matches fully contained within the interval. Byte and row constraints may be combined, including with quiet/capture ordering. Invalid syntax reports `Invalid range '<value>', expected 'start:end'`. Test-number/path conflicts follow Spec 4. `--rebuild`, grammar-path loading, explicit libraries, scopes, configuration, multiple input files, and compound language detection behave consistently with parse.

## Spec 24

`highlight` normally loads highlight queries from a grammar’s configured `highlights` path or `queries/highlights.scm`. Captures use hierarchical names such as `function.builtin`. Capture lookup first tries the full name and then dotted parents. The combination `--check --captures-path ALLOWED --query-paths QUERY --grammar-path GRAMMAR SOURCE` does not validate captures from `QUERY`: even when `QUERY` contains `@totally.nonstandard` and `ALLOWED` omits it, the command returns 0, writes no stdout, and warns `No syntax highlighting config found for path SOURCE`. Supplying query paths without a resolvable language is likewise an error.

Theme entries may be null, numeric ANSI colors, named terminal colors, `#RGB`/`#RRGGBB` hex colors in either case, or objects combining `color` with `bold`, `italic`, and `underline`. Numeric indexes 0–255 map directly. The bare numeric theme value `256` is also accepted and converted to ANSI index 0: a `variable` capture is opened with `\x1b[38;5;0m` and closed with `\x1b[0m`, and highlighting returns 0 without stderr. Reject malformed theme values. Terminal mode prints original source wrapped in correct ANSI spans and reset sequences. `-H/--html` emits an HTML fragment that begins with a newline and `<!doctype HTML>`, then contains `<head>`, `<body>`, escaped source, and `</body>`, but deliberately contains neither an opening nor a closing `html` element. Inline styles are default, while `--css-classes` uses stable capture-derived classes. Empty files, Unicode/UTF-16 inputs, binary data, and multiple files are safe.

## Spec 25

Highlight warnings and controls are observable. An unknown scope is fatal as `Error: Unknown scope '<scope>'`. With no positional pathname, `highlight` attempts language selection in the current path rather than treating the empty input set as a successful no-op. If no language is selectable, return 1; after any configuration warning, emit `Error: No language found in current path`. When every supplied positional pathname or glob is nonexistent or unmatched—including a sole pathname, a sole unmatched glob, or multiple missing inputs—return 1 and emit `Error: No files were found at or matched by the provided pathname/glob`; do not stop at the first pathname with an operating-system error. Mixed lists process existing files while warning for each missing/unrecognized one.

A broken symlink and a directory positional argument count as found path candidates: each returns 0 when no other error occurs and proceeds to language selection instead of failing while opening the path. Like an ordinary file whose extension has no matching language, each emits the no-language warning and advisory described below. Explicit `--encoding utf16-be` and `--encoding utf16-le` do not change this behavior. Multiple unrecognized path candidates yield one warning and advisory apiece.

For a path `P` with no matching language, stderr uses backticks around the path, has a blank line after the warning, and prints this advisory (the configured parser directories are numbered from 1 in configuration order):

```text
Warning: No language found for path `P`

If a language should be associated with this file extension, please ensure the path to `P` is inside one of the following directories as specified by your 'config.json':

  1. FIRST_CONFIGURED_DIRECTORY

If the directory that contains the relevant grammar for `P` is not listed above, please add the directory to the list of directories in your config file, which you need to create by running `tree-sitter init-config`

```

With multiple configured directories, every numbered directory line except the last ends in two ASCII spaces before its newline; the last has no trailing spaces. For example, the first line for `[/path1, /path2]` is exactly `  1. /path1  \n`, followed by `  2. /path2\n`. With one directory, its only line has no trailing spaces. The advisory uses the `which you need to create` ending shown above even when `--config-path` names an existing configuration; it does not print that configuration's path. When there is no existing configuration, the ordinary missing-configuration warning precedes the advisory and the numbered-directory section is empty. The no-language outcome returns 0 and writes no highlighted stdout.

If the file named by `--paths P` cannot be opened, return 1 and write nothing to stdout. When no configuration exists, first emit the complete missing-configuration warning from Spec 5, including its trailing blank line. Then emit this error and cause chain:

```text
Error: Failed to read paths file P

Caused by:
    No such file or directory (os error 2)
```

For `highlight --unknown-flag`, return 2, write nothing to stdout, and emit exactly:

```text
error: unexpected argument '--unknown-flag' found

  tip: to pass '--unknown-flag' as a value, use '-- --unknown-flag'

Usage: executable highlight [OPTIONS] [PATHS]...

For more information, try '--help'.
```

`--quiet` suppresses highlighted stdout, including HTML, but not warnings or requested timing/check diagnostics. `--time` reports duration. `--paths` ignores blank lines. Grammar-path conflicts with rebuild, and test number conflicts with paths. Config/grammar/query/captures paths are validated and named in errors. Encoding behavior matches parse.

## Spec 26

When a tags configuration is loaded, `tags` executes it and interprets captures `@name`, `@definition.<kind>`, and `@reference.<kind>`, emitting one line per definition/reference in source order with aligned columns in this logical form:

```text
NAME      \t | KIND    \tdef (START_ROW, START_COL) - (END_ROW, END_COL) `SOURCE LINE`
```

Use `ref` for references, preserve the exact captured spelling, and show its containing source line. An explicit `--grammar-path` does not load the descriptor-declared `tags` query for this command. With no parser configuration, even when the selected grammar's descriptor names `queries/tags.scm`, `tags --grammar-path GRAMMAR SOURCE` returns 0 and writes no stdout. Its stderr is the missing-configuration warning from Spec 5 followed by the no-language warning and advisory from Spec 25 with `P` replaced by `SOURCE` (including the empty numbered-directory section and the `tree-sitter init-config` ending); it does not emit `No tags config found`. Positional paths, paths files, stdin with `--scope`, multiple files, configuration selection, rebuild, and corpus test numbers otherwise work as for related commands. `--quiet` suppresses tags; `--time` appends `time: Nms` even when quiet. Unknown scope, missing source/path file, invalid/nonpositive test number, test-number/path conflict, and missing language/query produce contextual errors or per-file warnings rather than crashes. With no arguments, stdin content, and no selectable language in the current path, return 1, write exactly one newline (`\n`) to stdout, and emit the missing-configuration warning followed by `Error: No language found in current path` to stderr.

## Spec 27

Corpus files live under `test/corpus/*.txt`. Each case consists of a line of at least three `=` characters, a title, optional attribute lines beginning with `:`, another `=` divider, input text, a line of at least three `-` characters, and the expected S-expression/CST. Parse all files deterministically and assign one-based test numbers. Recognize `:skip`, `:error`, `:fail-fast`, `:platform(...)`, `:language(...)`, and `:cst`; malformed missing dividers are diagnosed. For the `test` command, grammar selection precedes corpus-directory validation. Thus `test --grammar-path EMPTY_EXISTING_DIRECTORY`, where both a loadable language and `test/corpus` are absent, returns 1, writes nothing to stdout, and emits the text `Error: No language found\n` with the mandatory heading coloring from Spec 37; it must not report the missing corpus first. Once a language has been selected, an absent corpus directory and an empty corpus produce clear nonzero results. The `fuzz` command's missing/empty-corpus status exception is specified separately in Spec 29.

`test` runs selected cases and compares normalized actual trees with expected trees. Show a nested file/case overview using green `✓`, red `✗`, and colored `⌀` for skipped/platform-excluded cases. On failures, show count and a structural colored expected/unexpected diff; `--show-fields` forces field labels. Return 0 only when every executed case passes (skips do not fail). After the overview, stdout contains one summary line in this field order and punctuation: `Total parses: T; successful parses: S; failed parses: F; success percentage: P; average speed: R`. Thus a passing suite with at least one executed case has `failed parses: 0` and `success percentage: 100.00%`; a passing single-test summary begins `Total parses: 1; successful parses: 1; failed parses: 0; success percentage: 100.00%; average speed:`. When no case is executed, the summary is exactly `Total parses: 0; successful parses: 0; failed parses: 0; success percentage: N/A; average speed: N/A`. The nonzero speed value is time-dependent as allowed by Spec 37.

## Spec 28

Test selection supports include and exclude regular expressions, exact `--file-name`, and multiple languages. Invalid regular expressions are errors. A syntactically valid `--file-name` that matches no corpus file is not an error: execute zero cases, return 0, write nothing to stderr, and write this exact stdout (including the leading and trailing blank lines):

```text

Total parses: 0; successful parses: 0; failed parses: 0; success percentage: N/A; average speed: N/A

```

`:fail-fast` stops later execution after that failure. `--overview-only` omits detailed diffs. `--update` replaces expected trees with current output only when doing so is safe; refuse updates containing error nodes and preserve passing content appropriately. Debug and debug-graph mirror parse.

`--stat` modes control per-case/outlier and total statistics. Totals use the same successful/failed/percentage/speed form as parse. `--json-summary` returns an object with `parse_results` (hierarchical names, outcomes `Passed`, `Failed`, `Skipped`, or `Platform`, parse rates, and test numbers), `parse_failures` (name, actual, expected, and `is_cst`), `parse_stats`, and arrays `highlight_results`, `tag_results`, and `query_results`. Counts exclude skipped/platform cases. JSON must be valid even when there are failures.

## Spec 29

`fuzz` loads corpus cases and repeatedly performs randomized incremental edits while checking that incremental and fresh parsing agree and do not crash. Defaults are 3 edits and 10 iterations. `TREE_SITTER_SEED` supplies a reproducible seed. When `TREE_SITTER_LOG_SEED` is present, stderr first contains `  start seed: N`; before each trial it then contains `   I.J  seed: N`, where `I` is the zero-based selected-case index and `J` is the zero-based trial index. For example, seed 9999, four selected cases, and one iteration produce these stderr lines in order:

```text
  start seed: 9999
   0.0  seed: 9999
   1.0  seed: 9999
   2.0  seed: 9999
   3.0  seed: 9999
```

For each selected case print a numbered line containing language, corpus path/group, and test title. Mark skipped cases ` - SKIPPED`.

Include/exclude are regex filters and may be combined; skip may occur multiple times; excluding all is valid. Invalid regexes are fatal. CLI `--edits` and `--iterations` override `TREE_SITTER_EDITS` and `TREE_SITTER_ITERATIONS`; both require nonnegative integers. Zero/minimal and large values must terminate safely. `TREE_SITTER_LOG`, `TREE_SITTER_LOG_SEED`, and `TREE_SITTER_LOG_GRAPHS` enable parser logs, seed logs, and graph/input logs, respectively.

When `TREE_SITTER_DUMP_EDITS` is present, create a `fuzz` directory in the process working directory and write one file for every executed case/trial. Its basename is exactly `edit.SEED.TEST_INDEX.TRIAL TEST_NAME`, where `TEST_NAME` is the same displayed name such as `mini - corpus - basic - word`, and its bytes are the edited input passed to the incremental parse. For example, seed 123, test index 0, and trial 0 create `fuzz/edit.123.0.0 mini - corpus - basic - word`.

A nonexistent `--grammar-path` returns 1 and emits `Error: No language found`. The following corpus-discovery outcomes are deliberate exceptions to the usual runtime-failure status rule. A generated grammar with no `test/corpus` directory emits ``Error: No corpus directory found, ensure that you have a `test/corpus` directory in your grammar directory with at least one test file.`` and returns 0. If `test/corpus` exists but contains no corpus files, emit ``Error: No corpus files found in `test/corpus`, ensure that you have at least one test file in your corpus directory.`` and return 0. In both cases stdout is empty. When `TREE_SITTER_SEED` is absent, stderr first contains `Seed: N`, where `N` is the automatically selected unsigned decimal seed, followed immediately by the applicable `Error:` line. When `TREE_SITTER_SEED` is set, no `Seed:` line is printed and the applicable `Error:` diagnostic is the entire stderr output. A grammar lacking generated artifacts produces a clear error. Fixed seed plus fixed inputs produces deterministic case/edit behavior; distinct seeds change randomized behavior.

## Spec 30

`playground --export DIR` deserializes `<grammar-path>/src/grammar.json` as a complete generated grammar object, not as a name-only descriptor. At minimum, both `name` and `rules` must be present. It then reads `<grammar-path>/tree-sitter-<name>.wasm`, creates/canonicalizes DIR, and writes/replaces `index.html` and `tree-sitter-parser.wasm`. The Wasm bytes are copied unchanged. HTML is a complete, substantial playground document beginning `<!DOCTYPE html>`, has title `tree-sitter <name>`, substitutes the language name everywhere (leaving no template token), and references hosted playground runtime assets. The HTML does not contain the literal filename `tree-sitter-parser.wasm`; local module loading is requested by `window.initializePlayground({local: true})`. On success stdout is exactly `Exported playground to <canonical-or-requested-dir>\n`.

The HTML bytes are otherwise fixed, not merely structurally equivalent. For the grammar name `anonymous_tokens_with_escaped_chars`, `index.html` is exactly the following 481-line document plus its final newline. For any other grammar, replace both occurrences of `anonymous_tokens_with_escaped_chars` with that grammar name and leave every other byte unchanged:

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>tree-sitter anonymous_tokens_with_escaped_chars</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/codemirror.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/clusterize.js/0.19.0/clusterize.min.css">
    <link rel="icon" type="image/png" href="https://tree-sitter.github.io/tree-sitter/assets/images/favicon-32x32.png"
      sizes="32x32" />
    <link rel="icon" type="image/png" href="https://tree-sitter.github.io/tree-sitter/assets/images/favicon-16x16.png"
      sizes="16x16" />
    <style>
      /* Base Variables */
      :root {
        --light-bg: #f9f9f9;
        --light-border: #e0e0e0;
        --light-text: #333;
        --light-hover-border: #c1c1c1;
        --light-scrollbar-track: #f1f1f1;
        --light-scrollbar-thumb: #c1c1c1;
        --light-scrollbar-thumb-hover: #a8a8a8;
        --light-tree-row-bg: #e3f2fd;
        
        --dark-bg: #1d1f21;
        --dark-border: #2d2d2d;
        --dark-text: #c5c8c6;
        --dark-panel-bg: #252526;
        --dark-code-bg: #1e1e1e;
        --dark-scrollbar-track: #25282c;
        --dark-scrollbar-thumb: #4a4d51;
        --dark-scrollbar-thumb-hover: #5a5d61;
        --dark-tree-row-bg: #373737;

        --primary-color: #0550ae;
        --primary-color-alpha: rgba(5, 80, 174, 0.1);
        --primary-color-alpha-dark: rgba(121, 192, 255, 0.1);
        --selection-color: rgba(39, 95, 255, 0.3);
      }

      /* Theme Colors */
      [data-theme="dark"] {
        --bg-color: var(--dark-bg);
        --border-color: var(--dark-border);
        --text-color: var(--dark-text);
        --panel-bg: var(--dark-panel-bg);
        --code-bg: var(--dark-code-bg);
        --tree-row-bg: var(--dark-tree-row-bg);
      }

      [data-theme="light"] {
        --bg-color: var(--light-bg);
        --border-color: var(--light-border);
        --text-color: var(--light-text);
        --panel-bg: white;
        --code-bg: white;
        --tree-row-bg: var(--light-tree-row-bg);
      }

      /* Base Styles */
      body {
        margin: 0;
        padding: 0;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background-color: var(--bg-color);
        color: var(--text-color);
      }

      /* Layout */
      #playground-container {
        width: 100%;
        height: 100vh;
        display: flex;
        flex-direction: column;
        background-color: var(--bg-color);
      }

      header {
        padding: 16px 24px;
        border-bottom: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        gap: 20px;
        background-color: var(--panel-bg);
        font-size: 14px;
      }

      .header-item {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .language-name,
      #language-version {
        font-weight: 600;
      }

      main {
        flex: 1;
        display: flex;
        overflow: hidden;
      }

      #input-pane {
        width: 50%;
        display: flex;
        flex-direction: column;
        border-right: 1px solid var(--border-color);
        background-color: var(--panel-bg);
        overflow: hidden;
      }

      #code-container {
        flex: 1;
        min-height: 0;
        position: relative;
        border-bottom: 1px solid var(--border-color);
        display: flex;
        flex-direction: column;
      }

      #query-container:not([style*="visibility: hidden"]) {
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
      }

      #query-container .panel-header {
        flex: 0 0 auto;
      }

      #query-container .CodeMirror {
        flex: 1;
        position: relative;
        min-height: 0;
      }

      #output-container-scroll {
        width: 50%;
        overflow: auto;
        background-color: var(--panel-bg);
        padding: 0;
        display: flex;
        flex-direction: column;
      }

      #output-container {
        font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
        line-height: 1.5;
        margin: 0;
        padding: 16px;
      }

      .panel-header {
        padding: 8px 16px;
        font-weight: 600;
        font-size: 14px;
        border-bottom: 1px solid var(--border-color);
        background-color: var(--panel-bg);
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .CodeMirror {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        height: 100%;
        font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
        font-size: 14px;
        line-height: 1.6;
        background-color: var(--code-bg) !important;
        color: var(--text-color) !important;
      }

      .query-error {
        text-decoration: underline red dashed;
        -webkit-text-decoration: underline red dashed;
      }

      /* Scrollbars */
      ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
      }

      ::-webkit-scrollbar-track {
        border-radius: 4px;
        background: var(--light-scrollbar-track);
      }

      ::-webkit-scrollbar-thumb {
        border-radius: 4px;
        background: var(--light-scrollbar-thumb);
      }

      ::-webkit-scrollbar-thumb:hover {
        background: var(--light-scrollbar-thumb-hover);
      }

      [data-theme="dark"] {
        ::-webkit-scrollbar-track {
          background: var(--dark-scrollbar-track) !important;
        }

        ::-webkit-scrollbar-thumb {
          background: var(--dark-scrollbar-thumb) !important;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: var(--dark-scrollbar-thumb-hover) !important;
        }
      }

      /* Theme Toggle */
      .theme-toggle {
        background: none;
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 6px;
        cursor: pointer;
        color: var(--text-color);
      }

      .theme-toggle:hover {
        background-color: var(--primary-color-alpha);
      }

      [data-theme="light"] .moon-icon,
      [data-theme="dark"] .sun-icon {
        display: none;
      }

      /* Form Elements */
      input[type="checkbox"] {
        margin-right: 6px;
        vertical-align: middle;
      }

      label {
        font-size: 14px;
        margin-right: 16px;
        cursor: pointer;
      }

      #output-container a {
        cursor: pointer;
        text-decoration: none;
        color: #040404;
        padding: 2px;
      }

      #output-container a:hover {
        text-decoration: underline;
      }

      #output-container a.node-link.named {
        color: #0550ae;
      }

      #output-container a.node-link.anonymous {
        color: #116329;
      }

      #output-container a.node-link.anonymous:before {
        content: '"';
      }

      #output-container a.node-link.anonymous:after {
        content: '"';
      }

      #output-container a.node-link.error {
        color: #cf222e;
      }

      #output-container a.highlighted {
        background-color: #cae2ff;
        color: red;
        border-radius: 3px;
        text-decoration: underline;
      }

      #copy-button {
        background: none;
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 6px;
        cursor: pointer;
        color: var(--text-color);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-left: 8px;
      }

      #copy-button:hover {
        background-color: var(--primary-color-alpha);
      }

      #copy-button:focus {
        outline: none;
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px var(--primary-color-alpha);
      }

      .toast {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: var(--light-text);
        color: white;
        padding: 12px 16px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        font-size: 14px;
        font-weight: 500;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s ease;
        z-index: 1000;
        pointer-events: none;
      }

      .toast.show {
        opacity: 1;
        transform: translateY(0);
      }

      /* Dark Theme Node Colors */
      [data-theme="dark"] {
        & #output-container a {
          color: #d4d4d4;
        }

        & #output-container a.node-link.named {
          color: #79c0ff;
        }

        & #output-container a.node-link.anonymous {
          color: #7ee787;
        }

        & #output-container a.node-link.error {
          color: #ff7b72;
        }

        & #output-container a.highlighted {
          background-color: #656669;
          color: red;
        }

        & .CodeMirror {
          background-color: var(--dark-code-bg) !important;
          color: var(--dark-text) !important;
        }

        & .CodeMirror-gutters {
          background-color: var(--dark-panel-bg) !important;
          border-color: var(--dark-border) !important;
        }

        & .CodeMirror-cursor {
          border-color: var(--dark-text) !important;
        }

        & .CodeMirror-selected {
          background-color: rgba(255, 255, 255, 0.1) !important;
        }

        & .toast {
          background-color: var(--dark-bg);
          color: var(--dark-text);
        }
      }
      .tree-row:has(.highlighted) {
        background-color: var(--tree-row-bg); 
      }
    </style>
  </head>

  <body>
    <div id="playground-container" style="visibility: hidden;">
      <header>
        <div class="header-item">
          <span class="language-name">Language: anonymous_tokens_with_escaped_chars</span>
          <span id="language-version"></span>
        </div>

        <div class="header-item">
          <input id="logging-checkbox" type="checkbox">
          <label for="logging-checkbox">log</label>
        </div>

        <div class="header-item">
          <input id="anonymous-nodes-checkbox" type="checkbox">
          <label for="anonymous-nodes-checkbox">show anonymous nodes</label>
        </div>

        <div class="header-item">
          <input id="query-checkbox" type="checkbox">
          <label for="query-checkbox">query</label>
        </div>

        <div class="header-item">
          <input id="accessibility-checkbox" type="checkbox">
          <label for="accessibility-checkbox">accessibility</label>
        </div>

        <div class="header-item">
          <label for="update-time">parse time: </label>
          <span id="update-time"></span>
        </div>

        <div class="header-item">
          <a href="https://tree-sitter.github.io/tree-sitter/7-playground.html#about">(?)</a>
        </div>

        <select id="language-select" style="display: none;">
          <option value="parser">Parser</option>
        </select>

        <div class="header-item">
          <button id="theme-toggle" class="theme-toggle" aria-label="Toggle theme">
            <svg class="sun-icon" viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor"
                d="M12 17.5a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11zm0 1.5a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm0-16a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1zm0 15a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1zm9-9a1 1 0 0 1-1 1h-2a1 1 0 1 1 0-2h2a1 1 0 0 1 1 1zM4 12a1 1 0 0 1-1 1H1a1 1 0 1 1 0-2h2a1 1 0 0 1 1 1z" />
            </svg>
            <svg class="moon-icon" viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor"
                d="M12.1 22c-5.5 0-10-4.5-10-10s4.5-10 10-10c.2 0 .3 0 .5.1-1.3 1.4-2 3.2-2 5.2 0 4.1 3.4 7.5 7.5 7.5 2 0 3.8-.7 5.2-2 .1.2.1.3.1.5 0 5.4-4.5 9.7-10 9.7z" />
            </svg>
          </button>
        </div>
      </header>

      <main>
        <div id="input-pane">
          <div class="panel-header">Code</div>
          <div id="code-container">
            <textarea id="code-input"></textarea>
          </div>

          <div id="query-container" style="visibility: hidden; position: absolute;">
            <div class="panel-header">Query</div>
            <textarea id="query-input"></textarea>
          </div>
        </div>

        <div id="output-container-scroll">
          <div class="panel-header">
            Tree
            <button type="button" id="copy-button" class="theme-toggle" aria-label="Copy tree">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round">
                <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
              </svg>
            </button>
          </div>
          <pre id="output-container" class="highlight"></pre>
        </div>
      </main>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/6.65.7/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/clusterize.js/0.19.0/clusterize.min.js"></script>

    <script>LANGUAGE_BASE_URL = "";</script>
    <script type="module" src="https://tree-sitter.github.io/tree-sitter/assets/js/playground.js"></script>
    <script type="module">
      import * as TreeSitter from 'https://tree-sitter.github.io/web-tree-sitter.js';
      window.TreeSitter = TreeSitter;
      setTimeout(() => window.initializePlayground({local: true}), 1)
    </script>
  </body>
</html>
```

Repeated export safely overwrites files byte-for-byte identically. Absolute and nonexistent output directories work. Export filesystem failures return 1, write nothing to stdout, and use these exact stderr cause chains (with the heading coloring from Spec 37):

- Failure to create export directory `DIR`:

```text
Error: Failed to create export directory: DIR

Caused by:
    Not a directory (os error 20)
```

- An `index.html` target that is a directory:

```text
Error: Failed to write index.html

Caused by:
    Is a directory (os error 21)
```

- A `tree-sitter-parser.wasm` target that is a directory:

```text
Error: Failed to write parser wasm file

Caused by:
    Is a directory (os error 21)
```

Failure to derive the Wasm filename is a deliberate panic rather than an ordinary `Error:` diagnostic. A missing grammar file, including through a nonexistent `--grammar-path`, has this behavior both with and without `--export`. For `playground --export`, malformed, empty, and non-UTF-8 grammar files, a missing or wrong-type `name`, and a missing `rules` field panic the same way. The panic writes nothing to stdout, returns 101, begins stderr with a blank line, and starts with these lines, where `PID` varies:

```text

thread 'main' (PID) panicked at crates/cli/src/wasm.rs:<error location>:
called `Result::unwrap()` on an `Err` value: Failed to get Wasm filename

Caused by:
```

The cause then identifies the actual failure. A missing file uses:

```text
    0: Failed to read grammar file GRAMMAR_PATH/src/grammar.json
    1: No such file or directory (os error 2)
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

Malformed or empty JSON instead uses `0: Failed to parse grammar file GRAMMAR_PATH/src/grammar.json` followed by the JSON parser cause; for an empty file that cause is `1: EOF while parsing a value at line 1 column 0`. A non-UTF-8 file uses `0: Failed to read grammar file GRAMMAR_PATH/src/grammar.json` and `1: stream did not contain valid UTF-8`. A missing name uses the parse-file cause and `1: missing field \`name\` at line 1 column C`; a numeric name uses `1: invalid type: integer \`42\`, expected a string at line 1 column C`. A three-line name-only object of the form `{"name": NAME}` uses the parse-file cause and `1: missing field \`rules\` at line 3 column 1`, before any Wasm read. Every panic ends with the same backtrace note shown above.

Once the full grammar object includes `rules`, an empty string is accepted as the name and interpolated rather than rejected. Full valid grammar objects with empty, Unicode, or slash-containing names proceed to the Wasm read. When that file is absent, return 1, write nothing to stdout, and write this exact structure (with the error heading colored as in Spec 37):

```text
Error: Failed to read tree-sitter-NAME.wasm. Run `tree-sitter build --wasm` first.

Caused by:
    No such file or directory (os error 2)
```

Thus the basenames in this first line are exactly `tree-sitter-.wasm`, `tree-sitter-언어.wasm`, and `tree-sitter-my-lang/test.wasm` for names `""`, `"언어"`, and `"my-lang/test"`, respectively. The first line contains no grammar-directory prefix. Excessive names produce their corresponding contextual filesystem failure.

## Spec 31

Without `--export`, playground is a persistent HTTP server. `TREE_SITTER_PLAYGROUND_ADDR` selects the bind address and defaults to `127.0.0.1`. `TREE_SITTER_PLAYGROUND_PORT` selects an integer from 0 through 65535. When the variable is unset, try ports sequentially in the half-open range `[8000, 12000)`, starting at 8000; if 8000 through 8002 are occupied, for example, emit `Started playground on: http://127.0.0.1:8003`. If all ports 8000 through 11999 are occupied, return 1, write nothing to stdout, and emit the text `Error: Failed to find a free port to bind to it\n` with the mandatory heading coloring from Spec 37. An explicit value of 0 instead requests an operating-system-assigned available port; for example, it can emit `Started playground on: http://127.0.0.1:36173`.

A malformed port such as `TREE_SITTER_PLAYGROUND_PORT=not_a_number` returns 1, writes nothing to stdout, and emits:

```text
Error: Invalid port specification

Caused by:
    invalid digit found in string
```

A malformed bind address used with an explicit port returns 1, writes nothing to stdout, and emits `Error: Failed to bind to the specified port\n`; this differs from exhaustion of the automatic port range. Occupied explicitly selected nonzero ports are rejected the same way. Print `Started playground on: http://ADDR:PORT` promptly to stderr. Unless `--quiet`, failure to open a browser must not stop the server. Grammar-file failures assigned status 101 in Spec 30 use that panic even in quiet serving mode; a complete valid grammar followed by a missing Wasm instead uses Spec 30's status-1 cause chain.

Serve `/` as the generated HTML with status 200, `Content-Type: text/html`, and exact byte `Content-Length`; serve `/tree-sitter-parser.wasm` unchanged as `application/wasm`. Unknown paths return status 404, body `Not found`, HTML content type, and length 9. Redirect `/web-tree-sitter.wasm` to `https://tree-sitter.github.io/web-tree-sitter.wasm`, `/web-tree-sitter.js` to `https://tree-sitter.github.io/web-tree-sitter.js`, and `/playground.js` to `https://tree-sitter.github.io/tree-sitter/assets/js/playground.js`, using HTTP 302 and a `Location` header. Handle repeated requests until terminated.

## Spec 32

`init` enters interactive initialization when the selected grammar directory has no `tree-sitter.json`. With captured non-terminal input, `init --grammar-path EMPTY_DIRECTORY` returns 1, writes nothing to stdout, writes the colored diagnostic `Error: IO error: not a terminal\n` to stderr, and creates no files. With an existing descriptor, it uses the descriptor’s first grammar plus metadata to scaffold a complete repository without overwriting user-modified existing files in ordinary mode. This existing-descriptor initialization returns 0 and writes nothing to stdout or stderr. It does not add a `$schema` member when that member is absent; a descriptor whose top-level keys were only `metadata`, `grammars`, and `bindings` still has exactly those top-level keys afterward.

Create nonempty `.editorconfig`, `.gitattributes`, `.gitignore`, `Cargo.toml`, `CMakeLists.txt`, `Makefile`, `Package.swift`, `binding.gyp`, `grammar.js`, `package.json`, `pyproject.toml`, `setup.py`, and the core binding trees. Core bindings include C headers/pkg-config, modern ESM Node binding/index/types/test, Python module/C extension/stubs/tests, Rust library/build script, Go binding, and Swift header/test. These six core binding trees are generated regardless of a descriptor binding allowlist: even when C is its only enabled entry, init creates `bindings/c`, `bindings/go`, `bindings/node`, `bindings/python`, `bindings/rust`, and `bindings/swift`. Java remains conditional and additionally creates Maven `pom.xml` and a camel-cased class; Zig remains conditional and additionally creates `build.zig`, `build.zig.zon`, and `bindings/zig/root.zig`.

The generated `.gitignore` is exactly:

```text
# Rust artifacts
target/

# Node artifacts
build/
prebuilds/
node_modules/

# Swift artifacts
.build/

# Go artifacts
_obj/

# Python artifacts
.venv/
dist/
*.egg-info
*.whl

# C artifacts
*.a
*.so
*.so.*
*.dylib
*.dll
*.pc
*.exp
*.lib

# Zig artifacts
.zig-cache/
zig-cache/
zig-out/

# Example dirs
/examples/*/

# Grammar volatiles
*.wasm
*.obj
*.o

# Archives
*.tar.gz
*.tgz
*.zip
*.jar
```

The generated `.editorconfig` is exactly:

```text
root = true

[*]
charset = utf-8

[*.{json,toml,yml,gyp,xml}]
indent_style = space
indent_size = 2

[*.{js,ts}]
indent_style = space
indent_size = 2

[*.scm]
indent_style = space
indent_size = 2

[*.{c,cc,h}]
indent_style = space
indent_size = 4

[*.rs]
indent_style = space
indent_size = 4

[*.{py,pyi}]
indent_style = space
indent_size = 4

[*.swift]
indent_style = space
indent_size = 4

[*.java]
indent_style = space
indent_size = 4

[*.go]
indent_style = tab
indent_size = 8

[Makefile]
indent_style = tab
indent_size = 8

[parser.c]
indent_size = 2

[{alloc,array,parser}.h]
indent_size = 2
```

Template source form is also stable. The grammar skeleton uses double-quoted JavaScript strings, including `name: "GRAMMAR_NAME"`, and its rules block has the TODO on its own line immediately before `source_file`:

```js
  rules: {
    // TODO: add the actual grammar rules
    source_file: $ => "hello"
  }
```

The Node smoke test begins with these three imports in this order:

```js
import assert from "node:assert";
import { test } from "node:test";
import Parser from "tree-sitter";
```

The Rust build script constructs and compiles `parser.c` using the following source blocks in this order rather than a one-line direct path. Target-specific setup occurs between these blocks:

```rust
let src_dir = std::path::Path::new("src");

let mut c_config = cc::Build::new();
c_config.std("c11").include(src_dir);
```

```rust
let parser_path = src_dir.join("parser.c");
c_config.file(&parser_path);
println!("cargo:rerun-if-changed={}", parser_path.to_str().unwrap());
```

Cargo package assignments are column-aligned as in the template. In particular, a grammar named `rust_test` produces the exact line `name         = "tree-sitter-rust-test"`, and the `version`, `license`, description, author, repository, and other package keys use the same template alignment and spacing.

The grammar skeleton is ESM, contains the configured grammar name, a `source_file` TODO rule, balanced delimiters, and an author JSDoc when authors exist. Existing grammar content is preserved. Query constants in Rust point to `../../queries/highlights.scm`, `injections.scm`, `locals.scm`, and `tags.scm` and are conditionally included.

## Spec 33

Initialization naming is deterministic. Preserve the grammar’s snake_case name for C exports and Python module directories (`tree_sitter_my_lang`), convert it to kebab-case for distribution names (`tree-sitter-my-lang`), remove separators and use PascalCase for Swift/Java/TypeScript identifiers (`MyLang`, `TreeSitterMyLang`), and preserve the repository path spelling where required by Go. C filenames use kebab-case. Java package segments remove underscores.

Metadata version defaults to `1.0.0`, license to `MIT`, and description to `<Title> grammar for tree-sitter`; custom values replace defaults everywhere. For an already mixed-case grammar name with no separator, derive `Title` by uppercasing only its first character and preserving all later capitalization. In particular, `cooLang` produces the exact default description `CooLang grammar for tree-sitter`, not `Coolang grammar for tree-sitter`. Authors with name/email render as `Name <email>` in Cargo and grammar comments and as structured author metadata in package JSON; omit entire author/developer blocks when none exist. Funding populates package JSON and Python project URLs; when absent package JSON omits it while the Python template retains its documented `FUNDING_URL` placeholder. Repository URLs populate all package managers; default is `https://github.com/tree-sitter/tree-sitter-<name>`, package JSON uses a `git+...git` URL, and normalized Go module host/owner text is lowercase. Zig fingerprint is exactly 16 nonzero lowercase hexadecimal digits. Package JSON’s `tree-sitter-cli` development requirement contains `0.27.0`.

Generated build metadata must be functional and include: Node scripts `test`, `start`, and `install`, with the `test` value exactly `node --test bindings/node/*_test.js`; a node-gyp target named `tree_sitter_<snake_case_grammar_name>_binding` using `bindings/node/binding.cc` (for grammar `test`, exactly `tree_sitter_test_binding`); Rust compilation of `src/parser.c`; Go `Language() unsafe.Pointer`; standard Make `all`, `clean`, and `install` targets; CMake project/library and generation targets; Python setuptools backend and free-threaded-compatible binding; valid Maven coordinates/license; Swift package targets; and a compilable Node smoke test using `node:test` and `node:assert`.

## Spec 34

`init --update` performs idempotent migrations on recognized old templates while preserving unrelated user content, and reports each performed migration on stderr. Required migrations are:

- uncomment/replace old Rust query constants with `#[cfg(with_*_query)]` dynamic `include_str!` constants;
- add the `wasm32-unknown-unknown` Rust build path using `DEP_TREE_SITTER_LANGUAGE_WASM_HEADERS`, `DEP_TREE_SITTER_LANGUAGE_WASM_SRC`, and `stdio.c`, plus rustc check-cfg/dynamic-query logic;
- add Zig entries to `.gitignore` and `.gitattributes`, and change `bindings/c/* linguist-generated` to `bindings/c/** linguist-generated`;
- add `"type": "module"`, convert `module.exports = grammar` to `export default grammar`, and replace old Node index, type declaration, and binding test with ESM variants;
- modernize CMake generation outputs/byproducts and its `ts-test` target;
- modernize Python C initialization to module slots including `Py_mod_gil, Py_MOD_GIL_NOT_USED`, change stubs to `CapsuleType`, update parser construction to `Parser(Language(...))`, and gate limited API on `not get_config_var("Py_GIL_DISABLED")`;
- fix Rust Cargo’s license include path to `"/LICENSE"`.

Emit the specific action phrases `Updating query constants in bindings/rust/lib.rs`, `Adding wasm32-unknown-unknown target`, `Adding support for dynamic query inclusion`, `Adding zig entries to .gitignore`, `Updating c bindings entry in .gitattributes`, `Migrating package.json to ESM`, `Migrating grammars.js to ESM`, `Replacing index.js`, `Replacing index.d.ts`, `Replacing binding_test.js`, and analogous `Updating ...` messages. A second update should not duplicate inserted content.

## Spec 35

`version` deserializes the complete `tree-sitter.json` descriptor in the grammar path before reading `metadata.version`; the descriptor requirements of Spec 7 therefore apply even when only displaying a version. For example, the compact descriptor `{"metadata":{"version":"3.4.5"},"grammars":[{"name":"test"}]}` has a grammar entry without `scope`: `version --grammar-path <that-directory>` returns 1, writes nothing to stdout, and reports ``Error: missing field `scope` at line 1 column 59``. With a valid descriptor and no new value, write `Current version: X.Y.Z` to stderr, nothing to stdout, and return 0. Versions are three nonnegative decimal components without prefixes/suffixes. Explicit invalid values fail without modifying files. `--bump patch` increments patch; minor increments minor and resets patch; major increments major and resets minor/patch. Components can exceed two digits.

For an increase write `Bumping version OLD to NEW`; for equality write `Keeping version OLD`; for a decrease write both `New version is lower than current!` and `Reverting version OLD to NEW`. A valid decrease succeeds. Update the descriptor and every present supported project version location: root `Makefile` (`VERSION :=`), Cargo package version, package JSON version, Python project version, and a CMake `project(... VERSION "OLD" ...)` declaration. For example, `VERSION "1.0.0"` becomes `VERSION "2.0.0"`. A root `build.zig.zon` is not updated: after a minor bump from `9.10.11` to `9.11.0`, its `.version = "9.10.11"` remains unchanged even though the descriptor and the other listed locations contain `9.11.0`. For multi-grammar repositories update `common/common.mak` instead of a root Makefile. Preserve unrelated fields, section/key order, and readable original formatting.

The Makefile is treated as expected for a single-grammar version change: if absent, update files that can be updated, then return nonzero with `Failed to update one or more files:` and identify `<path>/Makefile:\nNo such file or directory`. Other optional absent package-manager files do not prevent updating. Missing descriptor reports `No such file or directory (os error 2)`. For malformed JSON beginning `{ invalid json }`, `version` returns 1, writes nothing to stdout, and reports `Error: key must be a string at line 1 column 3\n` with the heading coloring from Spec 37; it does not prefix that message with the descriptor path. Other malformed JSON likewise includes the parser's exact cause and line/column. Grammar-path works from any current directory, and configuration environment variables do not redirect it.

## Spec 36

`complete` generates a nonempty completion program to stdout and no stderr for each supported shell. It describes all top-level commands, their options, enum choices, arguments, and aliases. Bash output contains `_tree-sitter()`, zsh begins/contains `#compdef tree-sitter`, fish contains `complete -c tree-sitter`, Elvish contains `use builtin`, PowerShell (`power-shell`) contains `System.Management.Automation`, and Nushell contains `export extern tree-sitter`. A missing shell or unsupported spelling (including `powershell` when `power-shell` is required) returns 2 and shows `--shell`/possible values. Every supplied unsupported value uses the same no-usage form below with that value substituted; this includes both `invalid` and `invalid-shell`. In particular, `complete --shell invalid` writes nothing to stdout and has this exact stderr, with no `Usage:` block:

```text
error: invalid value 'invalid' for '--shell <SHELL>'
  [possible values: bash, elvish, fish, power-shell, zsh, nushell]

For more information, try '--help'.
```

A positional spelling does not satisfy the required option. `complete bash` returns 2, writes nothing to stdout, and diagnoses the unexpected positional value before the absent `--shell` option:

```text
error: unexpected argument 'bash' found

Usage: executable complete --shell <SHELL>

For more information, try '--help'.
```

Completion output can be redirected by the invoking shell without changing behavior.

## Spec 37

Diagnostics must retain useful cause chains and paths. Ordinary fatal-error headings are always the bytes `\x1b[31mError:\x1b[0m`; recoverable-notice headings are always `\x1b[33mWarning:\x1b[0m`. This styling is emitted when stderr is captured, is not conditioned on a terminal, and is not disabled by `NO_COLOR=1`. The derive-Wasm-filename panic cases in Specs 30 and 31 are the explicit exception: they use Rust's uncolored panic text and status 101. File-not-found errors include `No such file or directory (os error 2)` where originating from the operating system. Parser compilation failures include captured compiler stdout/stderr. Dynamic-library failures distinguish `Error opening dynamic library ... -- dlopen failed` from `Failed to load symbol tree_sitter_NAME ... -- dlsym failed`. Grammar selection failures identify the affected source path.

Argument errors normally follow this exact shape and return 2:

```text
error: REASON

Usage: executable COMMAND ...

For more information, try '--help'.
```

Typed-value parsing omits the usage block for the invalid numeric and enum values listed below. Specifically, `fuzz --grammar-path <fixture> --edits abc --iterations 1` returns 2, writes nothing to stdout, and writes exactly:

```text
error: invalid value 'abc' for '--edits <EDITS>': invalid digit found in string

For more information, try '--help'.
```

The same no-usage rule applies to `parse --timeout abc`, which returns 2, writes nothing to stdout, and writes exactly:

```text
error: invalid value 'abc' for '--timeout <TIMEOUT>': invalid digit found in string

For more information, try '--help'.
```

It also applies to `parse --test-number abc`, `parse --encoding invalid`, `version --bump invalid`, and `test --stat invalid`. Each returns 2, writes nothing to stdout, and respectively writes exactly:

```text
error: invalid value 'abc' for '--test-number <TEST_NUMBER>': invalid digit found in string

For more information, try '--help'.
```

```text
error: invalid value 'invalid' for '--encoding <ENCODING>'
  [possible values: utf8, utf16-le, utf16-be]

For more information, try '--help'.
```

```text
error: invalid value 'invalid' for '--bump <BUMP>'
  [possible values: patch, minor, major]

For more information, try '--help'.
```

```text
error: invalid value 'invalid' for '--stat <STAT>'
  [possible values: all, outliers-and-total, total-only]

For more information, try '--help'.
```

Warnings do not alone change a successful exit code. Time-dependent values, temporary absolute paths, compiler wording, and color availability may vary, but all stable labels, structures, semantic values, stream choices, filenames, and ordering described above must remain deterministic.
