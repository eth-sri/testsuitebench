# Clarified specification for `executable`

The required artifact is one executable file named exactly `executable`. It is a compatible implementation of the Onefetch 2.25.0 command-line interface described below. “Repository” means a non-bare Git working repository. All paths, author names, file names, manifest strings, and other textual data are UTF-8 unless the underlying file is binary. The behavior in every section is normative.

## Spec 1

`executable` is a command-line Git repository information program. Invoke it as `executable [OPTIONS] [INPUT]`, where the optional positional `INPUT` is the directory in which to operate; in its absence use the process current working directory. `INPUT` is a path, never a subcommand. For example, `executable languages` attempts to use a directory literally named `languages`; special operations are selected only by options such as `--languages`.

The executable must work when invoked through either an absolute or relative executable path and when `INPUT` is absolute, relative, has a trailing slash, contains spaces or Unicode, or is the same path as the current directory. Resolve an image path relative to the process current directory, not relative to a separately supplied repository path. Write successful output to stdout and no diagnostics to stderr. Repository/IO failures use exit status 1; command-line parsing and validation failures use exit status 2. Normal repository display and special listing/generation modes use status 0. The deliberately preserved empty-custom-art failure in Spec 17 is the sole stated exception to these status classes.

Unless a section says otherwise, inspect real on-disk files and real Git metadata at invocation time. The implementation may use the harness-provided `git` command. It must not assume fixed commit IDs, dates, paths, or Git configuration.

## Spec 2

Recognize the following interface and aliases. Long option values may be supplied with a space or `=`, except the optional regex value of `--no-bots`, which is supplied only as `--no-bots=REGEX`. Options whose metavariable ends in `...` accept one or more adjacent values and can also be repeated; their values are accumulated. A `--` ends option parsing, after which exactly one positional input may follow.

| Group | Options and value rules |
|---|---|
| General | `-h`, `--help`; `-V`, `--version` |
| Info | `-d`, `--disabled-fields <FIELD>...`; `--no-title`; `--number-of-authors <NUM>` (default 3); `--number-of-languages <NUM>` (default 6); `--number-of-file-churns <NUM>` (default 3); `--churn-pool-size <NUM>`; `-e`, `--exclude <EXCLUDE>...`; `--no-bots[=<REGEX>]`; `--no-merges`; `-E`, `--email`; `--http-url`; `--hide-token`; `--include-hidden`; `-T`, `--type <TYPE>...` (default `programming markup`) |
| Text | `-t`, `--text-colors <X>...`; `-z`, `--iso-time`; `--number-separator <SEPARATOR>` (default `plain`); `--no-bold` |
| ASCII | `--ascii-input <STRING>`; `-c`, `--ascii-colors <X>...`; `-a`, `--ascii-language <LANGUAGE>`; `--true-color <WHEN>` (default `auto`) |
| Image | `-i`, `--image <IMAGE>`; `--image-protocol <PROTOCOL>`; `--color-resolution <VALUE>` (default 64 when image mode is used) |
| Visual | `--no-color-palette`; `--no-art`; `--nerd-fonts` |
| Machine/developer | `-o`, `--output <FORMAT>`; `--generate <SHELL>` |
| Lists | `-l`, `--languages`; `-p`, `--package-managers` |

Valid disabled field values are, in this order: `project`, `description`, `head`, `pending`, `version`, `created`, `languages`, `dependencies`, `authors`, `last-change`, `contributors`, `url`, `commits`, `churn`, `lines-of-code`, `size`, `license`. Valid types are `programming`, `markup`, `prose`, `data`. Valid separators are `plain`, `comma`, `space`, `underscore`. Valid true-color modes are `auto`, `never`, `always`. Valid image protocols are `kitty`, `sixel`, `iterm`; valid color resolutions are `16`, `32`, `64`, `128`, `256`; valid outputs are `json`, `yaml`; and valid completion shells are `bash`, `elvish`, `fish`, `powershell`, `zsh`.

The three count options and churn pool size parse as nonnegative native unsigned integers. Zero and large representable values are valid. Negative, nonnumeric, and overflowing values are parsing failures. ASCII/text color numbers accept exactly 0 through 15. `--image-protocol` and `--color-resolution` require `--image`. A non-repeatable option such as `--image-protocol` fails if supplied twice. `--ascii-language` is case-sensitive and accepts the lowercase CLI names enumerated in Spec 16.

Greedy multi-value options matter: without `--`, `-d pending .` consumes `.` as another disabled-field value and fails with status 2; `-d pending -- .` makes `.` the positional input.

## Spec 3

`--version` and `-V` print exactly `onefetch 2.25.0\n` and exit 0. `--help` takes precedence even if a later option is unknown and emits the exact long help below, with a final newline and no stderr. The displayed program name is always `executable`.

```text
Command-line Git information tool

Usage: executable [OPTIONS] [INPUT]

Arguments:
  [INPUT]
          Run as if onefetch was started in <input> instead of the current working directory

Options:
  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version

INFO:
  -d, --disabled-fields <FIELD>...
          Allows you to disable FIELD(s) from appearing in the output

      --no-title
          Hides the title

      --number-of-authors <NUM>
          Maximum NUM of authors to be shown
          
          [default: 3]

      --number-of-languages <NUM>
          Maximum NUM of languages to be shown
          
          [default: 6]

      --number-of-file-churns <NUM>
          Maximum NUM of file churns to be shown
          
          [default: 3]

      --churn-pool-size <NUM>
          Minimum NUM of commits from HEAD used to compute the churn summary
          
          By default, the actual value is non-deterministic due to time-based computation and will
          be displayed under the info title "Churn (NUM)"

  -e, --exclude <EXCLUDE>...
          Ignore all files & directories matching EXCLUDE

      --no-bots[=<REGEX>]
          Exclude [bot] commits. Use <REGEX> to override the default pattern

      --no-merges
          Ignores merge commits

  -E, --email
          Show the email address of each author

      --http-url
          Display repository URL as HTTP

      --hide-token
          Hide token in repository URL

      --include-hidden
          Count hidden files and directories

  -T, --type <TYPE>...
          Filters output by language type
          
          [default: programming markup]
          [possible values: programming, markup, prose, data]

TEXT FORMATTING:
  -t, --text-colors <X>...
          Changes the text colors (X X X...)
          
          Goes in order of title, ~, underline, subtitle, colon, and info
          
          For example:
          
          '--text-colors 9 10 11 12 13 14'

  -z, --iso-time
          Use ISO 8601 formatted timestamps

      --number-separator <SEPARATOR>
          Which thousands SEPARATOR to use
          
          [default: plain]
          [possible values: plain, comma, space, underscore]

      --no-bold
          Turns off bold formatting

ASCII:
      --ascii-input <STRING>
          Takes a non-empty STRING as input to replace the ASCII logo
          
          It is possible to pass a generated STRING by command substitution
          
          For example:
          
          '--ascii-input "$(fortune | cowsay -W 25)"'

  -c, --ascii-colors <X>...
          Colors (X X X...) to print the ascii art

  -a, --ascii-language <LANGUAGE>
          Which LANGUAGE's ascii art to print

      --true-color <WHEN>
          Specify when to use true color
          
          If set to auto: true color will be enabled if supported by the terminal
          
          [default: auto]
          [possible values: auto, never, always]

IMAGE:
  -i, --image <IMAGE>
          Path to the IMAGE file

      --image-protocol <PROTOCOL>
          Which image PROTOCOL to use
          
          [possible values: kitty, sixel, iterm]

      --color-resolution <VALUE>
          VALUE of color resolution to use with SIXEL backend
          
          [default: 64]
          [possible values: 16, 32, 64, 128, 256]

VISUALS:
      --no-color-palette
          Hides the color palette

      --no-art
          Hides the ascii art or image if provided

      --nerd-fonts
          Use Nerd Font icons
          
          Replaces language chips with Nerd Font icons

DEVELOPER:
  -o, --output <FORMAT>
          Outputs Onefetch in a specific format
          
          [possible values: json, yaml]

      --generate <SHELL>
          If provided, outputs the completion file for given SHELL
          
          [possible values: bash, elvish, fish, powershell, zsh]

OTHER:
  -l, --languages
          Prints out supported languages

  -p, --package-managers
          Prints out supported package managers
```

`-h` emits a shorter summary that is strictly shorter than this long help, includes all its option tokens/section names, contains `see more with '--help'`, ends in a newline, writes nothing to stderr, and exits 0. After `--`, the token `--help` is an input path instead of an option and therefore produces a path-access error naming `--help`.

## Spec 4

`--languages`/`-l` is a repository-independent side operation. It exits 0, emits no stderr, and prints exactly these 117 newline-terminated display names in this order, one per line:

```text
ABNF
ABAP
Ada
Agda
Arduino C++
Assembly
ATS
AutoHotKey
BASH
C
CMake
C#
Ceylon
Clojure
CoffeeScript
ColdFusion
Coq
C++
Crystal
CSS
CUDA
D
Dart
Dockerfile
Emacs Lisp
Elixir
Elm
Emojicode
Erlang
F#
Fish
Forth
FORTRAN Legacy
FORTRAN Modern
GDScript
GLSL
Go
GraphQL
Groovy
Haskell
Haxe
HCL
HLSL
HolyC
HTML
Idris
Java
JavaScript
JSON
Jsonnet
JSX
Julia
Jupyter Notebooks
Kotlin
LLVM
Lean
Common Lisp
Lua
Makefile
Markdown
Modelica
Nim
Nix
OCaml
Objective-C
Odin
OpenSCAD
Org
Oz
Pascal
Perl
PHP
PowerShell
Processing
Prolog
Protocol Buffers
PureScript
Python
QML
R
Racket
Raku
Razor
Ren'Py
Ruby
Rust
Sass
Scala
Scheme
Shell
Solidity
SQL
Svelte
SVG
Swift
SystemVerilog
TCL
TeX
Plain Text
TOML
TSX
TypeScript
Typst
Vala
Verilog
VHDL
Vim Script
Visual Basic
Vue
WebAssembly
Wolfram
XSL
XAML
XML
YAML
Zig
Zsh
```

`--package-managers`/`-p` similarly prints exactly `Npm\nCargo\n`. If `--languages` is combined with `--package-managers` or `--generate`, the language list wins. These side operations do not inspect a repository.

## Spec 5

`--generate SHELL` is another repository-independent side operation. It exits 0, emits only a newline-terminated completion script to stdout, and emits no stderr. The generated scripts describe every option, its aliases, and the positional input from Spec 2. Their command identity is `onefetch` (completion functions and registration use that name), even though the executable file is named `executable`.

For Bash, output begins exactly `_onefetch() {`, is longer than 30 lines, contains `--disabled-fields`, `--number-of-authors`, `--output`, and `--generate`, and defines the `_onefetch` completion function in the conventional `clap_complete` Bash layout. Its final five lines are exactly:

```text
if [[ "${BASH_VERSINFO[0]}" -eq 4 && "${BASH_VERSINFO[1]}" -ge 4 || "${BASH_VERSINFO[0]}" -gt 4 ]]; then
    complete -F _onefetch -o nosort -o bashdefault -o default onefetch
else
    complete -F _onefetch -o bashdefault -o default onefetch
fi
```

For Zsh, output begins `#compdef onefetch`, contains `autoload -U is-at-least`, `local context curcontext`, `_arguments "${_arguments_options[@]}"`, and all options. For Fish, every entry begins with `complete -c onefetch`; it includes the disabled-field choices and all options. PowerShell begins with `using namespace System.Management.Automation`, uses `Register-ArgumentCompleter -Native -CommandName 'onefetch'`, and enumerates all options. Elvish begins with a blank line followed by `use builtin;` and `use str;`, assigns `edit:completion:arg-completer[onefetch]`, and enumerates all options.

Completion descriptions use the descriptions and order from the long help. Possible-value lists are shell-specific: PowerShell and Elvish do not embed allowed enum values. In particular, their generated scripts contain none of `project`, `description`, `lines-of-code`, `license`, `programming`, `markup`, `prose`, or `data`. Fish includes the disabled-field choices as stated above. All shell scripts must be deterministic across runs.

## Spec 6

CLI diagnostics use the following exact shape, are written to stderr only, and exit 2. Finish every diagnostic with a newline. Replace `OPTION`, `META`, `BAD`, and the possible-value line as appropriate:

```text
error: invalid value 'BAD' for '--OPTION <META>'
  [possible values: comma, separated, values]

For more information, try '--help'.
```

The concrete possible-value lists are exactly those in Spec 2. For an invalid disabled field the option spelling is `--disabled-fields <FIELD>...`; invalid types use `--type <TYPE>...`; and invalid output, true-color, image protocol, color resolution, number separator, or shell use their help metavariables. Invalid `--ascii-language invalid` prints all CLI names from Spec 16 on one possible-values line and additionally prints `  tip: a similar value exists: 'vala'` after a blank line. The same suggestion is made for `invalidlanguage`. An uppercase `Python` is rejected and the diagnostic suggests/mentions lowercase `python`.

Out-of-range colors use this exact form (substitute the supplied number and option):

```text
error: invalid value '16' for '--ascii-colors <X>...': 16 is not in 0..16

For more information, try '--help'.
```

The upper endpoint in `0..16` is exclusive. A malformed bot regex such as `[invalid` produces exactly:

```text
error: invalid value '[invalid' for '--no-bots[=<REGEX>]': regex parse error:
    [invalid
    ^
error: unclosed character class

For more information, try '--help'.
```

Nonnumeric unsigned integers include `invalid digit found in string`; overflow includes `number too large to fit in target type`; both name the relevant option. A separate token beginning with `-` is parsed as an option rather than as the value of the preceding unsigned-count option. In particular, `--number-of-authors -1` produces exactly:

```text
error: unexpected argument '-1' found

  tip: to pass '-1' as a value, use '-- -1'

Usage: executable [OPTIONS] [INPUT]

For more information, try '--help'.
```

An unknown option fails nonzero and contains `unexpected argument`, `found argument`, or `unknown argument`. A missing required image dependency prints, for example:

```text
error: the following required arguments were not provided:
  --image <IMAGE>

Usage: executable --image <IMAGE> --image-protocol <PROTOCOL> [INPUT]

For more information, try '--help'.
```

For color resolution the usage line contains `--image <IMAGE> --color-resolution <VALUE> [INPUT]`. Validation of an invalid enum value occurs before dependency checking. Supplying image protocol twice reports `the argument '--image-protocol <PROTOCOL>' cannot be used multiple times`.

Glob syntax is validated during repository analysis. For example, `--exclude '[invalid'` reaches analysis, writes nothing to stdout, exits 1, and writes exactly `Error: error parsing glob '[invalid': unclosed character class; missing ']'\n` to stderr.

## Spec 7

Before analysis, verify the selected path exists and is a directory. Otherwise exit 1 with stdout empty and exactly `Error: Failed to access a directory, or path is not a directory: 'PATH'\n`. Starting within a nested working tree analyzes that inner repository only. Find a repository at the selected directory or its ancestors. A directory with no discoverable non-bare repository exits 1 with empty stdout and exactly `Error: Could not find a git repository in 'PATH' or in any of its parents\n`, where `PATH` is the input spelling supplied to the executable, or `.` when no input was supplied. A bare repository is handled by this same exact path-substitution rule.

Traverse all commits reachable from HEAD. Count empty commits and merge commits by default. A fresh repository without commits exits 1 and reports:

```text
Error: Failed to traverse Git commit history

Caused by:
    Branch 'refs/heads/BRANCH' does not have any commits
```

where `BRANCH` is normally `master` or `main`. If the object named directly by a branch ref is missing, exit 1 with empty stdout and use this exact diagnostic shape (including capitalization and blank line), substituting the object ID and ref name:

```text
Error: Failed to traverse Git commit history

Caused by:
    Object OBJECT_ID as referred to by "refs/heads/BRANCH" could not be found
```

`OBJECT_ID` is the unavailable lowercase 40-hex ID. Stale index lock files, detached HEAD, shallow clones, long/deep paths, Unicode commit data, binary files, and histories of at least 150 commits must be handled without crashes or timeouts. `CommitsInfo.numberOfCommits` is the count after bot and merge filtering; `isShallow` is true exactly for a shallow repository.

## Spec 8

`-o json` and `-o yaml` suppress all art, palettes, line-wrapping controls, and ANSI escapes. They serialize the same data model. JSON is pretty-printed valid JSON; YAML is valid block-style YAML. Both have exactly the top-level keys `title` and `infoFields` in that order. `title` is either `null` with `--no-title`, or an object containing string keys `gitUsername` then `gitVersion`. `gitUsername` is the repository’s Git `user.name` (empty string if unavailable). `gitVersion` is the complete output of `git --version`, such as `git version 2.34.1`.

`infoFields` is an ordered list. Each entry is an object with exactly one PascalCase key ending in `Info`. The normal order and exact inner schema are:

```text
ProjectInfo       {repoName: string, numberOfBranches: integer, numberOfTags: integer}
DescriptionInfo   {description: string-or-null}
HeadInfo          {headRefs: {shortCommitId: string, refs: [string...]}}
PendingInfo       {added: integer, deleted: integer, modified: integer}
VersionInfo       {version: string}
CreatedInfo       {creationDate: string}
LanguagesInfo     {languagesWithPercentage: [{language: string, percentage: number}...]}
DependenciesInfo  {dependencies: string}
AuthorsInfo       {authors: [{name: string, email: string-or-null, nbrOfCommits: integer, contribution: integer}...]}
LastChangeInfo    {lastChange: string}
ContributorsInfo  {totalNumberOfAuthors: integer}
UrlInfo           {repoUrl: string}
CommitsInfo       {numberOfCommits: integer, isShallow: boolean}
ChurnInfo         {file_churns: [{filePath: string, nbrOfCommits: integer}...], churn_pool_size: integer}
LocInfo           {linesOfCode: integer}
SizeInfo          {repoSize: string, fileCount: integer}
LicenseInfo       {license: string}
```

An enabled field normally remains in structured output even when its value is empty: missing description is `null`; missing version, dependencies, URL, and license are `""`; pending counts may all be zero; contributors still carries the total. If no language/LOC data exists, omit `LanguagesInfo` and `LocInfo`; other field omissions described below also apply. Field order must be stable across repeated JSON/YAML runs. JSON and YAML must yield the same set and count of fields. YAML uses keys and indentation equivalent to this example fragment:

```yaml
title:
  gitUsername: Test User
  gitVersion: git version 2.34.1
infoFields:
- ProjectInfo:
    repoName: ''
    numberOfBranches: 0
    numberOfTags: 0
- HeadInfo:
    headRefs:
      shortCommitId: abc1234
      refs:
      - master
```

## Spec 9

`ProjectInfo.repoName` comes from the basename of the `remote.origin` fetch URL path with a trailing `.git` removed. Preserve punctuation such as hyphens and underscores. For a local path like `/tmp/origin.git`, the result is `origin`. If origin has no usable path, use the empty string. Do not fall back to a Cargo/npm manifest name or to the working-directory basename: without origin, Cargo name `manifest_name` and npm name `npm-name` both still produce an empty `repoName`.

`numberOfBranches` is derived from the number of remote-tracking references, not ordinary local-only branches: subtract one from that reference count with saturation at zero. The subtraction normally removes symbolic `origin/HEAD`; it is still performed if a remote was initially empty and has no such symbolic ref. Thus a normal local repository without a remote has 0, a clone exposing `origin/HEAD`, `origin/master`, `origin/feature1`, and `origin/feature2` has 3, and an initially-empty clone in which only `origin/master` and `origin/feature` were later created has 1. `numberOfTags` counts all tags. Structured values remain numeric and never contain thousands separators.

Text Project values are omitted when repoName is empty. With no counts use `Project: name`; otherwise append parentheses and omit zero components: `name (1 branch)`, `name (2 branches)`, `name (1 tag)`, `name (3 tags)`, or `name (2 branches, 3 tags)`. Apply correct singular/plural forms and number separator formatting.

`DescriptionInfo.description` comes from the selected root Cargo/npm manifest’s description. Preserve arbitrary Unicode and long strings. Use null when absent; empty-valued text info fields do not render a text line.

## Spec 10

`HeadInfo.headRefs.shortCommitId` is the lowercase first seven hexadecimal characters of HEAD’s object ID. `refs` contains the names of refs pointing to HEAD: local branch short names such as `master` or `main`, and applicable remote tracking names such as `origin/master`. A detached HEAD has an empty `refs` array. Text renders the ID followed by refs in parentheses when nonempty, e.g. `HEAD: abc1234 (main)`.

`PendingInfo` describes working-tree changes. A clean tree is all zeros. Count unstaged modifications as `modified`, working-tree deletions as `deleted`, and untracked files as `added`. A newly staged-but-never-committed file is not counted as added. Mixed changes populate their corresponding counts. Pending is rendered only when at least one count is nonzero; structured output retains all three integer keys even when zero. In text, show an added count as `N+`, a deleted count as `N-`, and a modified count as `N+-`. Join nonzero components with spaces in the fixed order modified, added, deleted; one of each renders as `Pending: 1+- 1+ 1-`.

## Spec 11

`VersionInfo.version` is the name of the most recently reached Git tag in history. Both lightweight and annotated tags qualify; tags take precedence over manifests and names are preserved verbatim (including `v`, slashes, hyphens, prerelease and build suffixes). Prefer the tag reached most recently from HEAD; if several names point to one commit, choosing any of those tag names is acceptable. With no tag, fall back to a nonempty version from a valid root Cargo `[package].version` or root npm `version`; otherwise use empty string. Behavior when both manifest ecosystems coexist is not constrained.

`CreatedInfo.creationDate` represents the oldest reachable included commit’s author/commit time and `LastChangeInfo.lastChange` the newest. By default format them as human relative time (`now`, `N seconds ago`, and analogous larger units). With `-z`/`--iso-time`, format UTC ISO 8601 as `YYYY-MM-DDTHH:MM:SSZ` (a `T` separator, no `ago`). Preserve the strings in structured output and use the same strings in text.

## Spec 12

Group reachable included commits by resolved author identity. By default identity is author name plus email, so the same name with different emails is treated as separate authors. Honor a repository `.mailmap` and merge aliases into its canonical name/email. Preserve empty, long, and Unicode author values.

For each author, `nbrOfCommits` is its included commit count and `contribution` is that count divided by the total included commits, rounded to the nearest whole percentage so examples 3/6, 2/6, 1/6 become 50, 33, 17. A sole author is 100; 7/10 and 3/10 are 70 and 30. Sort descending by commit count and alphabetically by name for ties; identical results must be stable. Calculate percentages against all included authors before truncating. By default return the top 3; `--number-of-authors N` returns at most N, N=0 returns an empty author list/does not render author rows, and N above the total returns all.

Without `--email`, every structured author still has `email: null`. With `-E`/`--email`, use the exact Git author email and show it in text. The text label is singular `Author` for one shown author and `Authors` for multiple, and author rows contain contribution, name, optional email, and commit count (for example `100% Test 1`). `ContributorsInfo.totalNumberOfAuthors` is the full distinct-author count even when the displayed author list is truncated. The structured field is always retained when enabled, but its `Contributors:` text row is rendered only when the total exceeds the number of displayed authors.

## Spec 13

By default include bot and merge commits. `--no-merges` excludes every commit with more than one parent from commit totals, author totals, percentages, and relevant history-derived summaries. `--no-bots` without a value applies the exact author-name regex `(?:-|\s)[Bb]ot$|\[[Bb]ot\]`. It excludes names such as `foo bot`, `foo Bot`, `foo-bot`, `bar-Bot`, `dependabot[bot]`, `github-actions[bot]`, and `renovate[bot]`, but does not exclude the bare name `bot`; commit-message text alone is irrelevant. `--no-bots=REGEX` replaces the default pattern with the supplied regular expression applied to author names. Examples: `^CI-` removes `CI-Bot`; `^Bot` removes `BotAlpha`; `^(automated-|ci-)` removes both prefixes. An empty regex matches every author and therefore leaves zero included commits. Custom regex matching is case-sensitive unless the expression requests otherwise.

Filters combine by intersection: with four commits consisting of a normal human commit, a normal bot commit, a human merge, and another human commit, no-merges alone and no-bots alone each leave 3 while both leave 2. Recompute `CommitsInfo`, author counts, contributors and percentages after filtering.

## Spec 14

Only the fetch URL configured under `remote.origin` is considered. Ignore other remotes when origin exists, and return empty URL when only non-origin remotes exist. Preserve clean `https://`, `http://`, `git://`, `file://`, scp-style SSH (`git@host:path`), and explicit `ssh://` URLs by default, except credential redaction. Query strings, fragments, ports, IPv4 hosts, long paths, colons and legitimate `@` characters in the path must survive.

For HTTP(S) URLs with userinfo, default behavior preserves the username and replaces the secret/password/token portion with literal `redacted` (e.g. `https://myuser:secret_token@github.com/x/y.git` becomes `https://myuser:redacted@github.com/x/y.git`) so the secret never appears. `--hide-token` removes the entire authority userinfo and delimiter, yielding `scheme://host/path`. It works for http and https, usernames with/without passwords and percent-encoded special characters, and removes only the authority’s final credential delimiter—not legitimate later `@` in a path such as `team/email@handler.git`. It is a no-op on clean or scp-style SSH URLs.

`--http-url` converts the recognized user-at-host form `git@github.com:group/x.git` to `https://github.com/group/x.git`, preserving the path and `.git` suffix. It does not treat a userless colon form as convertible: `host:group/nested:path.git` remains exactly `host:group/nested:path.git`. Its parsing of an explicit SSH URL is intentionally nonstandard: `ssh://git@example.com:2222/a.git` becomes `https://example.com/2222/a.git`, with the port text turned into the first path segment. Existing http(s), `git://`, and `file://` URLs are not transformed. Combining `--http-url` and `--hide-token` is order-independent and produces a credential-free HTTPS URL when conversion occurs. Text has exactly one `URL:` line when nonempty and none when empty.

If `remote.origin` exists but neither a fetch `url` nor `pushUrl` is configured, exit 1 with empty stdout and exactly:

```text
Error: Failed to determine repository URL

Caused by:
    Neither 'url` nor 'pushUrl' fields were set in the remote's configuration.
```

This differs from there being no origin remote, which is successful and yields an empty URL.

## Spec 15

Recursively classify source files and count logical lines of code. Aggregate all files of a language into one entry. A logical code line is nonblank and not solely a comment for ordinary programming languages; shebangs count as comments. Markdown is a prose language whose nonblank HTML-comment lines count, so a Markdown fixture with a heading, two content lines and two `<!-- ... -->` lines has 5 LOC. A recognized extension is still classified when the content contains NUL bytes: the exact bytes `\0function x() {}\n` in `binary.js` contribute one JavaScript LOC. Ignore empty/whitespace-only source files, symlinks as source content, unknown extensions, extensionless ordinary files, and files excluded from language analysis by Spec 18.

Language percentage is `language LOC / total LOC * 100` as a floating-point number without forced rounding. Thus 2 of 3 may serialize as `66.66666666666666`. Percentages are positive, no greater than 100, and sum to approximately 100. Sort descending by LOC with deterministic tie behavior. A single detected language is 100.0. `LocInfo.linesOfCode` is the same total used for included language statistics.

Recognize extensions case-insensitively. At minimum use the detection mapping in Spec 16. Important aliases in JSON are `Cpp` for C++, `Html`, `Css`, `Json`, `Yaml`, `Toml`, `Php`, `Sh`, `Tcl`, `Glsl`, `Hlsl`, `Vhdl`, `Jsx`, `Tsx`, `Tex`, `Svg`, and the exact names shown in Spec 16; the side list’s human display spellings are separate.

`--number-of-languages N` is a presentation limit only: JSON and YAML always retain every detected language and never add an `Other` entry. In text, show the first N principal languages and aggregate all remaining percentages into one `Other` row. `N=0` means unlimited and therefore shows every detected language; a value above the count also shows all and does not add `Other`. Every displayed language row has `● Name (P %)` and the displayed percentages sum to approximately 100.

## Spec 16

The default language-type filter is the union of programming and markup. Data and prose files are ignored unless explicitly selected. Repeated/adjacent `--type` values combine by union. Selecting a type recalculates LOC and percentages using only that type; when no language survives, omit `LanguagesInfo` and `LocInfo`.

The required CLI-name, JSON-name, type, and tested filename mapping is:

```text
abnf/ABNF/data/.abnf; abap/Abap/programming/.abap; ada/Ada/programming/.adb;
agda/Agda/programming/.agda; arduino/Arduino/programming/.ino; assembly/Assembly/programming/.asm;
ats/Ats/programming/.dats; autohotkey/AutoHotKey/programming/.ahk; bash/Bash/programming/.bash;
c/C/programming/.c,.h; cmake/CMake/programming/CMakeLists.txt,.cmake; c#/CSharp/programming/.cs;
ceylon/Ceylon/programming/.ceylon; clojure/Clojure/programming/.clj; coffeescript/CoffeeScript/programming/.coffee;
coldfusion/ColdFusion/programming/.cfm; coq/Coq/programming/.v; c++/Cpp/programming/.cpp,.cc,.hpp;
crystal/Crystal/programming/.cr; css/Css/markup/.css; cuda/Cuda/programming/.cu; d/D/programming/.d;
dart/Dart/programming/.dart; dockerfile/Dockerfile/programming/Dockerfile,.dockerfile;
emacs-lisp/Elisp/programming/.el; elixir/Elixir/programming/.ex,.exs; elm/Elm/programming/.elm;
emojicode/Emojicode/programming/.emojic; erlang/Erlang/programming/.erl; f#/FSharp/programming/.fs;
fish/Fish/programming/.fish; forth/Forth/programming/.forth; fortran/FortranLegacy/programming/.f;
fortranmodern/FortranModern/programming/.f90; gdscript/GdScript/programming/.gd; glsl/Glsl/programming/.glsl;
go/Go/programming/.go; graphql/Graphql/data/.graphql; groovy/Groovy/programming/.groovy;
haskell/Haskell/programming/.hs; haxe/Haxe/programming/.hx; hcl/Hcl/programming/.hcl;
hlsl/Hlsl/programming/.hlsl; holyc/HolyC/programming/.HC; html/Html/markup/.html;
idris/Idris/programming/.idr; java/Java/programming/.java; javascript/JavaScript/programming/.js;
json/Json/data/.json; jsonnet/Jsonnet/programming/.jsonnet; jsx/Jsx/programming/.jsx;
julia/Julia/programming/.jl; jupyter-notebooks/Jupyter/programming/.ipynb; kotlin/Kotlin/programming/.kt;
llvm/LLVM/programming/.ll; lean/Lean/programming/.lean; lisp/Lisp/programming/.lisp;
lua/Lua/programming/.lua; makefile/Makefile/programming/Makefile; markdown/Markdown/prose/.md;
modelica/Modelica/programming/.mo; nim/Nim/programming/.nim; nix/Nix/programming/.nix;
ocaml/OCaml/programming/.ml; objective-c/ObjectiveC/programming/.m; odin/Odin/programming/.odin;
openscad/OpenScad/programming/.scad; org/Org/prose/.org; oz/Oz/programming/.oz;
pascal/Pascal/programming/.pas; perl/Perl/programming/.pl; php/Php/programming/.php;
powershell/PowerShell/programming/.ps1; processing/Processing/programming/.pde;
prolog/Prolog/programming/.pro; protocol-buffers/Protobuf/programming/.proto;
purescript/PureScript/programming/.purs; python/Python/programming/.py; qml/Qml/programming/.qml;
r/R/programming/.r; racket/Racket/programming/.rkt; raku/Raku/programming/.raku;
razor/Razor/markup/.cshtml; renpy/Renpy/programming/.rpy; ruby/Ruby/programming/.rb;
rust/Rust/programming/.rs; sass/Sass/markup/.sass; scala/Scala/programming/.scala;
scheme/Scheme/programming/.scm; shell/Sh/programming/.sh; solidity/Solidity/programming/.sol;
sql/Sql/data/.sql; svelte/Svelte/markup/.svelte; svg/Svg/data/.svg;
swift/Swift/programming/.swift; systemverilog/SystemVerilog/programming/.sv; tcl/Tcl/programming/.tcl;
tex/Tex/markup/.tex; text/Text/prose/.txt; toml/Toml/data/.toml; tsx/Tsx/programming/.tsx;
typescript/TypeScript/programming/.ts; typst/Typst/markup/.typ; vala/Vala/programming/.vala;
verilog/Verilog/programming/.v; vhdl/Vhdl/programming/.vhdl; vimscript/VimScript/programming/.vim;
visualbasic/VisualBasic/programming/.vb; vue/Vue/markup/.vue; webassembly/WebAssembly/programming/.wasm;
wolfram/Wolfram/programming/.wl; xsl/XSL/programming/.xsl; xaml/Xaml/data/.xaml;
xml/Xml/data/.xml; yaml/Yaml/data/.yaml,.yml; zig/Zig/programming/.zig; zsh/Zsh/programming/.zsh.
```

All CLI names in that table must be accepted even when machine output means the art itself is not rendered. The accepted-value order for diagnostics is the table order beginning `abnf, abap, ada` and ending `yaml, zig, zsh`.

For the overlapping `.v` extension, this version selects `Coq` without content disambiguation. Thus a repository containing both `proof.v` with `Inductive day : Type := monday.` and `hardware.v` with `module x; endmodule` reports only one aggregated `Coq` language entry and no `Verilog` entry.

## Spec 17

In normal terminal text mode, surround the complete output with the ANSI wrap-control sequences `\x1b[?7l` at the very beginning and `\x1b[?7h` at the very end. The latter is the final byte; a trailing newline is not required after it. JSON and YAML output contain neither sequence and no other ANSI escapes.

The default presentation places language ASCII art at the left and an information panel at the right, separated by three spaces. If there is no included dominant language and no explicit custom/selected art, use the plain information printer with no art and a white primary color. In ordinary ANSI mode this is foreground code 37, not the terminal's unspecified/default foreground. `--ascii-language` selects only the art/palette and does not change detected language data; `--ascii-input` takes precedence over selected and detected built-in art. Omit trailing art rows that contain no visible character after color placeholders are interpreted. During composition, pad every retained art row to the art's maximum visible width and then add the information gap; rows without right-hand information therefore retain padding spaces exactly as illustrated in Spec 30. `--no-art` removes the art and its gap. `--no-title` removes the title and underline but not other information. `--no-bold` removes bold attributes while retaining colors. `--ascii-input TEXT` uses `TEXT` itself as the art, never as a filename; preserve Unicode and embedded newlines. In custom art, `{0}`, `{1}`, and later numeric placeholders select art palette colors and have zero display width. Literal input without placeholders is also valid.

An explicitly supplied empty custom-art value (`--ascii-input ""`) passes command-line parsing but has a required compatibility failure: exit with status 101 and write a crash report diagnostic to stderr. That diagnostic contains all of `Well, this is embarrassing`, `onefetch had a problem and crashed`, `crash report`, `report file at`, `https://onefetch.dev`, and `o2sh`.

The information panel begins, unless disabled, with the title `gitUsername ~ gitVersion`, where the two spaces around `~` are literal and the values are those in Spec 8. If exactly one component is empty, render only the nonempty component and no tilde. Its next row is a run of `-` characters whose visible length equals the rendered title. Field rows follow in the structured order in Spec 8, except empty optional fields are omitted. Each ordinary row is `Label: value`; wrapped/list continuation rows align beneath the start of the value. A minimal repository must still produce nonempty text output.

The language text block uses `Language:` for one displayed language and `Languages:` for more than one, followed by a horizontal color chip occupying 26 spaces. Following content begins under the value column, then a colored `●`, a space, the display language name, a space, and the percentage in parentheses such as `Rust (100.0 %)`. Multiple compact entries may be packed two per physical line. The LOC label is `Lines of code`; its value is an integer count. File count uses `file` only for one and `files` otherwise. Size uses the IEC units of Spec 19.

## Spec 18

Determine the repository worktree file set recursively, never scanning `.git` as project content. Respect Git ignore rules, so ignored tracked-status candidates do not contribute to languages, LOC, size, licenses, dependencies, or churn. By default omit paths whose basename begins with `.` at any depth from language/LOC and churn analysis. `--include-hidden` admits those hidden paths to those analyses but still never admits `.git` internals. `SizeInfo` is the exception: it includes tracked, non-ignored hidden worktree files, including a tracked `.gitignore`, regardless of `--include-hidden`; it does not include untracked files. Source symlinks do not contribute language or LOC.

Each `--exclude PATTERN` adds a case-sensitive glob filter over slash-separated repository-relative paths. Support literal filenames and directory names, `*`, `?`, `**`, and leading `/` root anchoring. A directory match excludes its descendants. A basename pattern can match that basename below the root, while `/name` is root-only. Multiple exclusions form a union. The empty pattern is valid and excludes the entire filter-sensitive content set. Apply these filters to language/LOC and file churn; commit history counts remain available even when every filter-sensitive file is excluded. They do not affect `SizeInfo`: `/name.rs`, basename/directory filters, and the empty pattern all leave its file count and byte total unchanged.

## Spec 19

The byte quantity represented by `SizeInfo.repoSize` is the sum of raw byte lengths of all tracked, non-ignored regular worktree files outside `.git`, and `SizeInfo.fileCount` is their count. Use byte size, not character count. Include tracked dotfiles such as `.gitignore` and tracked files hidden at any depth, but exclude untracked files even when they are not ignored. For example, after committing the 13-byte `main.rs` containing `fn main() {}\n`, adding an untracked 9-byte `untracked.rs` containing `fn x(){}\n` leaves size at `repoSize: "13 B"` and `fileCount: 1`; text renders `Size: 13 B (1 file)` while the untracked file makes `Pending: 1+`. Do not apply `--exclude` to either size value. In the seven-file fixture consisting of `keep.rs`, `skip.rs`, `dir/drop.py`, `dir/keep.py`, `.hidden.py`, `dir/.nested.rs`, and `.gitignore`, where all seven files are committed, the result remains `repoSize: "38 B"` and `fileCount: 7` even with `--exclude skip.rs drop.py`. Empty repositories produce `repoSize: "0 B"` and `fileCount: 0`. Git-ignored files do not contribute.

In text, format sizes using binary IEC scaling (1024 bytes per KiB, then MiB, GiB) with at most two fractional decimal places and without meaningless trailing zeroes. Required examples are `0 B`, `33 B`, and `11001` bytes as `10.74 KiB`. Render the complete value as `SIZE (N file)` or `SIZE (N files)`. The separator option in Spec 24 applies to the displayed file count and integer portions where relevant; structured byte/file values remain integers.

## Spec 20

Dependency counting recognizes a valid root `Cargo.toml` or a root `package.json` that contains both top-level string keys `name` and `version` (their string values may be empty). For Cargo, count only direct keys in `[dependencies]`; do not count `[dev-dependencies]`, `[build-dependencies]`, workspace-only declarations, target-only unrelated tables, or nested configuration keys. Both simple version strings and table-valued dependency declarations count once per key. For an eligible npm manifest, count only keys in the top-level `dependencies` object; do not count `devDependencies`, `peerDependencies`, or `optionalDependencies`. A syntactically valid `package.json` containing only `dependencies`, even an object with 1000 keys, is not an eligible npm manifest and yields an empty dependencies string for every number-separator setting.

Missing, empty, malformed, or valid-but-dependency-free manifests are not fatal and yield an empty dependencies value rather than `0 (...)`. A nonzero result is the exact string `N (Cargo)` or `N (Npm)`. Apply the requested number separator to `N` even in JSON/YAML because this Info value is a string. Manifest behavior when multiple different package ecosystems coexist is not otherwise constrained.

## Spec 21

License discovery first honors a nonempty valid license declaration in the selected root package manifest. A Cargo package `license` string and an npm package `license` string such as `ISC` are returned verbatim. An absent or empty declaration allows file detection. A malformed manifest does not prevent file detection.

For file detection inspect only root entries whose basename begins exactly with `LICENSE`, `LICENCE`, or `COPYING`, including suffixes such as `.md`, `.txt`, `-CODE`, and `-DOCS`. Do not treat `NOTLICENSE` as a candidate and do not search subdirectories. Follow a candidate symlink to readable content. Recognize sufficiently complete standard texts for MIT, Apache 2.0, BSD 3-Clause, and ISC, returning identifiers `MIT`, `Apache-2.0`, `BSD-3-Clause`, and `ISC`. Distinctive clauses alone are not sufficient. In particular, each of these exact abbreviated candidate contents is below the recognizer's confidence threshold and yields an empty license string:

```text
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files. THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND.
```

```text
Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.
```

This remains true when the abbreviated MIT content is next to malformed `Cargo.toml` or reached through a root `LICENSE.txt` symlink. Conversely, a root `LICENSE` containing the complete Apache 2.0 text is detected as `Apache-2.0`, and so is a root `LICENSE.txt` symlink to that complete text. Empty, whitespace-only, arbitrary/custom, truncated low-confidence, and GPL-3 text in the tested corpus yield no detected identifier.

Deduplicate identifiers found in multiple files, sort them alphabetically, and join them with comma-space. One license is emitted without punctuation. An enabled but absent license is represented as `LicenseInfo` with an empty `license` string in structured output and is omitted as a text row.

## Spec 22

File churn measures how often repository-relative files participate in the analyzed recent commit pool. Use newest-first commits. With `--churn-pool-size N`, inspect at most N commits and cap at the number of available included commits; `N=0` is accepted and may use an empty or minimal HEAD-only pool. Without the option choose a bounded recent pool, but it must include all commits in the small tested repositories. `ChurnInfo.churn_pool_size` is the number actually inspected, not the requested upper bound.

For an initial or ordinary single-parent commit, increment a path once if it is added or modified in that commit. Do not increment deleted paths. Treat a detected rename as deletion of the old path plus addition of the new path, so only the new path receives that commit's count. Binary blobs participate; tree entries, submodule/gitlink entries, and other non-blob objects do not. A merge commit with multiple parents contributes no changed-file increments even though it can remain in the analyzed pool. Apply hidden/exclude eligibility from Spec 18 to the counted paths.

Sort file-churn entries by descending count, then path ascending for ties. By default return/render at most three. `--number-of-file-churns N` changes this display limit; zero retains `ChurnInfo` with an empty `file_churns` list, and a value above the available paths returns all. Each structured entry is `{"filePath": RELATIVE_PATH, "nbrOfCommits": INTEGER}`. Text begins `Churn (POOL): PATH COUNT`; additional entries align their path beneath the first path.

## Spec 23

Text coloring uses the standard 16-color ANSI foreground map: indices 0–7 become codes 30–37 and indices 8–15 become 90–97. Background use is the corresponding 40–47 or 100–107 family. True-color values use `38;2;R;G;B` for foreground and `48;2;R;G;B` for background. Reset styling with `\x1b[0m` at segment boundaries.

The six `--text-colors` positions are, in order: title components, title tilde, underline, field labels, field colon, field values. With `--text-colors 0 1 2 3 4 5`, for example, bold-enabled title/tilde/labels/colon use `\x1b[30;1m`, `\x1b[31;1m`, `\x1b[33;1m`, and `\x1b[34;1m`; underline and values use nonbold `\x1b[32m` and `\x1b[35m`. Supply defaults position by position: title and field labels use the dominant art color; when there is no dominant language, use ANSI white (foreground code 37), or RGB white (`#FFFFFF`) when true-color output is forced. Tilde, underline, colon, and values use terminal default foreground code 39. Thus three supplied values override only title, tilde, and underline; the label falls back to the dominant art color (or white fallback) and colon/value to 39. `--no-bold` removes only `;1`.

The exact `--ascii-colors` sequence replaces the corresponding leading entries of the built-in palette for placeholder indices in art. Standard indices use the ANSI map above. Hex values use true color. If fewer custom colors are supplied than the art needs, append the remaining built-in colors in their original positions; if more are supplied, preserve them as available placeholders and ignore unused entries. Built-in true-color palettes and language-chip colors required by exact fixtures are: Rust art `#E43717,#FFFFFF`, chip `#DEA584`; Python art `#2F69A2,#FFD940`, chip `#3572A5`; JavaScript art `#ECE653`, chip `#F1E05A`; Go art `#74CDDD,#FFFFFF,#F6D2A2`, chip `#00ADD8`. Their default ANSI art palettes are respectively red/default, blue/yellow, yellow, and cyan/default/yellow. The chip is rendered as a background-colored 26-space bar.

`--true-color always` forces the built-in RGB values, `never` forces their ANSI approximations, and `auto` uses ANSI in captured/non-TTY output unless the terminal is positively identified as true-color capable. Normal text output includes a color-palette row at the bottom of the information panel. It is exactly eight adjacent blocks, one for each standard background 40 through 47, each block being `ESC[4Xm` + three spaces + `ESC[49m`. `--no-color-palette` removes this entire row. JSON and YAML never include it. `--nerd-fonts` replaces the language chip and ordinary bullet with the selected art language's Nerd Font icon from Spec 26; it does not alter structured language data.

## Spec 24

`--number-separator` controls display grouping. `plain` uses uninterrupted digits; `comma` uses `,`; `space` uses the narrow no-break space U+202F, not ordinary ASCII space; and `underscore` uses `_`. Group digits from the right in groups of three.

Apply grouping throughout human text to commit counts, contributor totals, LOC, file counts, churn pool/counts, branch/tag counts, and dependency counts. Apply it inside structured string values such as dependencies, but never convert structured numeric fields (`numberOfCommits`, `linesOfCode`, `fileCount`, contribution integers, churn integers, branch/tag integers) to strings and never group their JSON/YAML numeric representation. `repoSize` remains its human-readable string regardless of output format.

## Spec 25

`--disabled-fields` removes only the named information variants. Map accepted names as follows: `project`→ProjectInfo, `description`→DescriptionInfo, `head`→HeadInfo, `pending`→PendingInfo, `version`→VersionInfo, `created`→CreatedInfo, `languages`→LanguagesInfo, `dependencies`→DependenciesInfo, `authors`→AuthorsInfo, `last-change`→LastChangeInfo, `contributors`→ContributorsInfo, `url`→UrlInfo, `commits`→CommitsInfo, `churn`→ChurnInfo, `lines-of-code`→LocInfo, `size`→SizeInfo, and `license`→LicenseInfo. Values are greedy and may be repeated; take their union. Supplying all 17 names removes every information entry; `all` itself is not a valid field name.

Disabled fields do not appear in text, JSON, or YAML and do not leave blank labels. Disabling authors does not implicitly disable contributors or commits, and disabling languages does not implicitly disable LOC. Disabling all 17 fields while also using `--no-art --no-title --no-color-palette` is still successful, producing only the text-mode wrapping controls. `--no-title` is independent of ProjectInfo: it affects only the decorative title.

## Spec 26

Every accepted ASCII-language name has a stable, nonempty built-in art asset available in text mode. The six assets below are the ones whose complete pattern is byte-sensitive and are exact after substituting ANSI color selections for placeholders. Keep every visible character and leading space; remove source-template trailing spaces. Rust has icon U+E7A8, Python U+E73C, JavaScript U+F2EE, and Go U+E627 when a glyph/icon is needed elsewhere. The C++ template uses four color placeholders, so `--ascii-language c++ --ascii-colors 1 2` necessarily emits both ANSI red and ANSI green art segments. The Java template uses two color placeholders.

Rust:

```text
{0}                 R RR RR
{0}              R RRRRRRRR R          R
{0} R RR       R RRRRRRRRRRRRR R      RR
{0}rR RRR    R RRRRRRRRRRRRRRRRR R   RRR R
{0}RRR RR   RRRRRRRRRRRRRRRRRRRRRRR  RRRRR
{0} RRRRR  RRRRRRRRRRRRRRRRRRRRRRRR  RRRR
{0}  RRR RRRRRRRRRRRRRRRRRRRRRRRRRRRR RR
{0}    R  RRRRRRRRRR{1}=  {0}RR{1} = {0}RRRRRRRRRRR
{0}     RRRRRRRRRRRR{1}=  {0}RR{1} = {0}RRRRRRRRRR
{0}      RRRRRRRRRRR   RR   RRRRRRRRRR
{0}     RR==RRRRRRRRRRRRRRRRRRRRRR===RR
{0}     RR =  ==RRRRRRR  RRRRRR==  = RR
{0}      RR =     ===========     = RR
{0}       RR                        R
{0}        R                       R
{0}         R
```

Python:

```text
{0}               =========
{0}            ===============
{0}           =================
{0}          ===  ==============
{0}          ===================
{0}                   ==========
{0}   ========================== {1}=======
{0} ============================ {1}========
{0}============================= {1}=========
{0}============================ {1}==========
{0}========================== {1}============
{0}============ {1}==========================
{0}========== {1}============================
{0}========= {1}=============================
{0} ======== {1}============================
{0}  ======= {1}==========================
{1}          ==========
{1}          ===================
{1}          ==============  ===
{1}           =================
{1}            ===============
{1}               =========
```

JavaScript:

```text
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
{0}JSJSJSJSJSJSJSJSJ    SJSJS      JSJSJS
{0}JSJSJSJSJSJSJSJSJ    SJS          JSJS
{0}JSJSJSJSJSJSJSJSJ    SJS     JSJSJSJSJ
{0}JSJSJSJSJSJSJSJSJ    SJSJ     SJSJSJSJ
{0}JSJSJSJSJSJSJSJSJ    SJSJSJ     SJSJSJ
{0}JSJSJSJSJSJSJSJSJ    SJSJSJSJ     JSJS
{0}JSJSJSJSJSJSJSJSJ    SJSJSJSJS     JSJ
{0}JSJSJSJSJS     JS    JSJS          JSJ
{0}JSJSJSJSJSJ          SJSJSJ      SJSJS
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
{0}JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS
```

Go:

```text
{0}           --==============--
{0}  .-==-.===oooo=oooooo=ooooo===--===-
{0} .==  =o={1}oGGGGGG{0}o=oo=o{1}GGGGGGG{0}G=o=  oo-
{0} -o= oo={1}G .=GGGGG{0}o=o={1}= .=GGGGG{0}=ooo o=-
{0}  .-=oo={1}o==oGGGGG{0}=oo={1}oooGGGGGo{0}=oooo.
{0}   -ooooo{1}=oooooo{0}={2}.   .{0}={1}=ooo=={0}oooooo-
{0}   -ooooooooooo{2}====_===={0}ooooooooooo=
{0}   -oooooooooooo{2}=={1}#{0}.{1}#{2}=={0}ooooooooooooo
{0}   -ooooooooooooo={1}#{0}.{1}#{0}=oooooooooooooo
{0}   .oooooooooooooooooooooooooooooooo.
{0}    oooooooooooooooooooooooooooooooo.
{2}  ..{0}oooooooooooooooooooooooooooooooo{2}..
{2}-=o-{0}=ooooooooooooooooooooooooooooooo{2}-oo.
{2}.=- {0}oooooooooooooooooooooooooooooooo{2}-.-
{0}   .oooooooooooooooooooooooooooooooo-
{0}   -oooooooooooooooooooooooooooooooo-
{0}   -oooooooooooooooooooooooooooooooo-
{0}   -oooooooooooooooooooooooooooooooo-
{0}   .oooooooooooooooooooooooooooooooo
{0}    =oooooooooooooooooooooooooooooo-
{0}    .=oooooooooooooooooooooooooooo-
{0}      -=oooooooooooooooooooooooo=.
{2}     =oo{0}====oooooooooooooooo==-{2}oo=-
{2}    .-==-    {0}.--=======---     {2}.==-
```

C++:

```text
{0}                 ++++++
{0}              ++++++++++++
{0}          ++++++++++++++++++++
{0}       ++++++++++++++++++++++++++
{0}    ++++++++++++++++++++++++++++++++
{0} +++++++++++++{3}************{0}+++++++++++++
{0}+++++++++++{3}******************{0}++++++++{2};;;
{0}+++++++++{3}**********************{0}++{2};;;;;;;
{0}++++++++{3}*********{0}++++++{3}******{2};;;;;;;;;;;
{0}+++++++{3}********{0}++++++++++{3}**{2};;;;;;;;;;;;;
{0}+++++++{3}*******{0}+++++++++{2};;;;;;{3}**{2};;;;{3}**{2};;;
{0}+++++++{3}******{0}+++++++{2};;;;;;;;{3}****{2};;{3}****{2};;
{0}+++++++{3}*******{0}+++{1}:::::{2};;;;;;;{3}**{2};;;;{3}**{2};;;
{0}+++++++{3}********{1}::::::::::{3}**{2};;;;;;;;;;;;;
{0}++++++++{3}*********{1}::::::{3}******{2};;;;;;;;;;;
{0}++++++{1}:::{3}**********************{1}::{2};;;;;;;
{0}+++{1}::::::::{3}******************{1}::::::::{2};;;
{1} :::::::::::::{3}************{1}:::::::::::::
{1}    ::::::::::::::::::::::::::::::::
{1}       ::::::::::::::::::::::::::
{1}          ::::::::::::::::::::
{1}              ::::::::::::
{1}                 ::::::
```

Java:

```text
{0}                  |
{0}                 ||
{0}               |||
{0}             ||||    ||
{0}           ||||| ||||
{0}          ||||  |||
{0}         ||||  |||
{0}         |||    |||
{0}          |||    |||
{0}            ||    ||
{0}              |   |
{1}   ####               #    ##
{1}    ################       ##
{1}       #                   ##
{1}      ################   ###
{1}
{1}       ##############
{1}####      #######          #
{1}#####                   ####
{1}   #####################      #
{1}                          ###
{1}          ###############
```

## Spec 27

`--image PATH` changes the art source to an image while leaving repository information semantics unchanged. Before attempting terminal rendering, open and decode the file. A nonexistent path fails with status 1 and:

```text
Error: Could not load the image file at 'PATH'

Caused by:
    No such file or directory (os error 2)
```

A `.png` file containing the exact seven ASCII bytes `not png` exits 1 with empty stdout and this exact diagnostic:

```text
Error: Could not load the image file at 'PATH'

Caused by:
    0: Format error decoding Png: Invalid PNG signature.
    1: Invalid PNG signature.
```

PNG decode failures depend on how many bytes are available. An empty `.png` file, or a `.png` file containing the exact three ASCII bytes `bad`, exits 1 with empty stdout and exactly:

```text
Error: Could not load the image file at 'PATH'

Caused by:
    unexpected end of file
```

An extensionless file named `image` containing the exact seven ASCII bytes `not png` exits 1 with empty stdout and exactly:

```text
Error: Could not load the image file at 'image'

Caused by:
    The image format could not be determined
```

For the same bytes in `image.xyz`, an unknown extension instead produces the same first-line shape with path `image.xyz` and the exact cause ``The file extension `."xyz"` was not recognized as an image format``. Paths containing spaces or Unicode are accepted and printed exactly in diagnostics.

Decode/load validation precedes terminal capability checks. Under captured, non-TTY execution, a valid image with any explicit `--image-protocol kitty|sixel|iterm` fails exactly with status 1 and:

```text
Error: Failed to render image

Caused by:
    Inappropriate ioctl for device (os error 25)
```

With a valid image and no explicit protocol in the same environment, the first error line contains the historical spelling `Failed to recieve terminal attibutes`, followed by an ioctl cause. Accept all four width/height combinations, zero and large dimensions, all supported protocols, and `--no-art` combinations without a parser conflict; file decoding errors still take precedence.

## Spec 28

All repository operations must handle empty repositories, detached HEAD, unborn HEAD, bare repositories when meaningful, branches with slashes/Unicode, long paths, Unicode filenames/content/metadata, empty author fields, binary blobs, shallow history, many refs, and ordinary valid Git timestamps without a crash or panic. Results must be deterministic for an unchanged repository.

Special side modes (`--help`, `--version`, `--languages`, `--package-managers`, and `--generate`) do not require a repository. If special modes are combined, `--help` has the precedence stated in Spec 3; otherwise `--languages` takes precedence over both `--package-managers` and `--generate`. Ordinary analysis must use the requested path exactly once and must not mutate the repository, its config, index, refs, files, or environment. Never invoke network services. Write successful payloads to stdout and diagnostics to stderr; do not leak secrets redacted under Spec 14.


## Spec 29

`--generate SHELL` is a repository-independent side mode. It writes a deterministic completion program to stdout, exits 0, and writes no stderr. Although the generated completion command is named `onefetch` (not `executable`), the option vocabulary and descriptions match this specification. The Bash, Zsh, Fish, and Elvish outputs are exactly the following, including their final newline.

Bash:

```text
_onefetch() {
    local i cur prev opts cmd
    COMPREPLY=()
    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
        cur="$2"
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
    fi
    prev="$3"
    cmd=""
    opts=""

    for i in "${COMP_WORDS[@]:0:COMP_CWORD}"
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="onefetch"
                ;;
            *)
                ;;
        esac
    done

    case "${cmd}" in
        onefetch)
            opts="-d -e -E -T -t -z -c -a -i -o -l -p -h -V --disabled-fields --no-title --number-of-authors --number-of-languages --number-of-file-churns --churn-pool-size --exclude --no-bots --no-merges --email --http-url --hide-token --include-hidden --type --text-colors --iso-time --number-separator --no-bold --ascii-input --ascii-colors --ascii-language --true-color --image --image-protocol --color-resolution --no-color-palette --no-art --nerd-fonts --output --generate --languages --package-managers --help --version [INPUT]"
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                --disabled-fields)
                    COMPREPLY=($(compgen -W "project description head pending version created languages dependencies authors last-change contributors url commits churn lines-of-code size license" -- "${cur}"))
                    return 0
                    ;;
                -d)
                    COMPREPLY=($(compgen -W "project description head pending version created languages dependencies authors last-change contributors url commits churn lines-of-code size license" -- "${cur}"))
                    return 0
                    ;;
                --number-of-authors)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --number-of-languages)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --number-of-file-churns)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --churn-pool-size)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --exclude)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -e)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --no-bots)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --type)
                    COMPREPLY=($(compgen -W "programming markup prose data" -- "${cur}"))
                    return 0
                    ;;
                -T)
                    COMPREPLY=($(compgen -W "programming markup prose data" -- "${cur}"))
                    return 0
                    ;;
                --text-colors)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -t)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --number-separator)
                    COMPREPLY=($(compgen -W "plain comma space underscore" -- "${cur}"))
                    return 0
                    ;;
                --ascii-input)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --ascii-colors)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -c)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --ascii-language)
                    COMPREPLY=($(compgen -W "abnf abap ada agda arduino assembly ats autohotkey bash c cmake c# ceylon clojure coffeescript coldfusion coq c++ crystal css cuda d dart dockerfile emacs-lisp elixir elm emojicode erlang f# fish forth fortran fortranmodern gdscript glsl go graphql groovy haskell haxe hcl hlsl holyc html idris java javascript json jsonnet jsx julia jupyter-notebooks kotlin llvm lean lisp lua makefile markdown modelica nim nix ocaml objective-c odin openscad org oz pascal perl php powershell processing prolog protocol-buffers purescript python qml r racket raku razor renpy ruby rust sass scala scheme shell solidity sql svelte svg swift systemverilog tcl tex text toml tsx typescript typst vala verilog vhdl vimscript visualbasic vue webassembly wolfram xsl xaml xml yaml zig zsh" -- "${cur}"))
                    return 0
                    ;;
                -a)
                    COMPREPLY=($(compgen -W "abnf abap ada agda arduino assembly ats autohotkey bash c cmake c# ceylon clojure coffeescript coldfusion coq c++ crystal css cuda d dart dockerfile emacs-lisp elixir elm emojicode erlang f# fish forth fortran fortranmodern gdscript glsl go graphql groovy haskell haxe hcl hlsl holyc html idris java javascript json jsonnet jsx julia jupyter-notebooks kotlin llvm lean lisp lua makefile markdown modelica nim nix ocaml objective-c odin openscad org oz pascal perl php powershell processing prolog protocol-buffers purescript python qml r racket raku razor renpy ruby rust sass scala scheme shell solidity sql svelte svg swift systemverilog tcl tex text toml tsx typescript typst vala verilog vhdl vimscript visualbasic vue webassembly wolfram xsl xaml xml yaml zig zsh" -- "${cur}"))
                    return 0
                    ;;
                --true-color)
                    COMPREPLY=($(compgen -W "auto never always" -- "${cur}"))
                    return 0
                    ;;
                --image)
                    local oldifs
                    if [ -n "${IFS+x}" ]; then
                        oldifs="$IFS"
                    fi
                    IFS=$'\n'
                    COMPREPLY=($(compgen -f "${cur}"))
                    if [ -n "${oldifs+x}" ]; then
                        IFS="$oldifs"
                    fi
                    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
                        compopt -o filenames
                    fi
                    return 0
                    ;;
                -i)
                    local oldifs
                    if [ -n "${IFS+x}" ]; then
                        oldifs="$IFS"
                    fi
                    IFS=$'\n'
                    COMPREPLY=($(compgen -f "${cur}"))
                    if [ -n "${oldifs+x}" ]; then
                        IFS="$oldifs"
                    fi
                    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
                        compopt -o filenames
                    fi
                    return 0
                    ;;
                --image-protocol)
                    COMPREPLY=($(compgen -W "kitty sixel iterm" -- "${cur}"))
                    return 0
                    ;;
                --color-resolution)
                    COMPREPLY=($(compgen -W "16 32 64 128 256" -- "${cur}"))
                    return 0
                    ;;
                --output)
                    COMPREPLY=($(compgen -W "json yaml" -- "${cur}"))
                    return 0
                    ;;
                -o)
                    COMPREPLY=($(compgen -W "json yaml" -- "${cur}"))
                    return 0
                    ;;
                --generate)
                    COMPREPLY=($(compgen -W "bash elvish fish powershell zsh" -- "${cur}"))
                    return 0
                    ;;
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
    esac
}

if [[ "${BASH_VERSINFO[0]}" -eq 4 && "${BASH_VERSINFO[1]}" -ge 4 || "${BASH_VERSINFO[0]}" -gt 4 ]]; then
    complete -F _onefetch -o nosort -o bashdefault -o default onefetch
else
    complete -F _onefetch -o bashdefault -o default onefetch
fi
```

Zsh:

```text
#compdef onefetch

autoload -U is-at-least

_onefetch() {
    typeset -A opt_args
    typeset -a _arguments_options
    local ret=1

    if is-at-least 5.2; then
        _arguments_options=(-s -S -C)
    else
        _arguments_options=(-s -C)
    fi

    local context curcontext="$curcontext" state line
    _arguments "${_arguments_options[@]}" : \
'*-d+[Allows you to disable FIELD(s) from appearing in the output]:FIELD:(project description head pending version created languages dependencies authors last-change contributors url commits churn lines-of-code size license)' \
'*--disabled-fields=[Allows you to disable FIELD(s) from appearing in the output]:FIELD:(project description head pending version created languages dependencies authors last-change contributors url commits churn lines-of-code size license)' \
'--number-of-authors=[Maximum NUM of authors to be shown]:NUM:_default' \
'--number-of-languages=[Maximum NUM of languages to be shown]:NUM:_default' \
'--number-of-file-churns=[Maximum NUM of file churns to be shown]:NUM:_default' \
'--churn-pool-size=[Minimum NUM of commits from HEAD used to compute the churn summary]:NUM:_default' \
'*-e+[Ignore all files & directories matching EXCLUDE]:EXCLUDE:_default' \
'*--exclude=[Ignore all files & directories matching EXCLUDE]:EXCLUDE:_default' \
'--no-bots=[Exclude \[bot\] commits. Use <REGEX> to override the default pattern]' \
'*-T+[Filters output by language type]:TYPE:(programming markup prose data)' \
'*--type=[Filters output by language type]:TYPE:(programming markup prose data)' \
'*-t+[Changes the text colors (X X X...)]:X:_default' \
'*--text-colors=[Changes the text colors (X X X...)]:X:_default' \
'--number-separator=[Which thousands SEPARATOR to use]:SEPARATOR:(plain comma space underscore)' \
'--ascii-input=[Takes a non-empty STRING as input to replace the ASCII logo]:STRING:_cmdstring' \
'*-c+[Colors (X X X...) to print the ascii art]:X:_default' \
'*--ascii-colors=[Colors (X X X...) to print the ascii art]:X:_default' \
'-a+[Which LANGUAGE'\''s ascii art to print]:LANGUAGE:(abnf abap ada agda arduino assembly ats autohotkey bash c cmake c# ceylon clojure coffeescript coldfusion coq c++ crystal css cuda d dart dockerfile emacs-lisp elixir elm emojicode erlang f# fish forth fortran fortranmodern gdscript glsl go graphql groovy haskell haxe hcl hlsl holyc html idris java javascript json jsonnet jsx julia jupyter-notebooks kotlin llvm lean lisp lua makefile markdown modelica nim nix ocaml objective-c odin openscad org oz pascal perl php powershell processing prolog protocol-buffers purescript python qml r racket raku razor renpy ruby rust sass scala scheme shell solidity sql svelte svg swift systemverilog tcl tex text toml tsx typescript typst vala verilog vhdl vimscript visualbasic vue webassembly wolfram xsl xaml xml yaml zig zsh)' \
'--ascii-language=[Which LANGUAGE'\''s ascii art to print]:LANGUAGE:(abnf abap ada agda arduino assembly ats autohotkey bash c cmake c# ceylon clojure coffeescript coldfusion coq c++ crystal css cuda d dart dockerfile emacs-lisp elixir elm emojicode erlang f# fish forth fortran fortranmodern gdscript glsl go graphql groovy haskell haxe hcl hlsl holyc html idris java javascript json jsonnet jsx julia jupyter-notebooks kotlin llvm lean lisp lua makefile markdown modelica nim nix ocaml objective-c odin openscad org oz pascal perl php powershell processing prolog protocol-buffers purescript python qml r racket raku razor renpy ruby rust sass scala scheme shell solidity sql svelte svg swift systemverilog tcl tex text toml tsx typescript typst vala verilog vhdl vimscript visualbasic vue webassembly wolfram xsl xaml xml yaml zig zsh)' \
'--true-color=[Specify when to use true color]:WHEN:(auto never always)' \
'-i+[Path to the IMAGE file]:IMAGE:_files' \
'--image=[Path to the IMAGE file]:IMAGE:_files' \
'--image-protocol=[Which image PROTOCOL to use]:PROTOCOL:(kitty sixel iterm)' \
'--color-resolution=[VALUE of color resolution to use with SIXEL backend]:VALUE:(16 32 64 128 256)' \
'-o+[Outputs Onefetch in a specific format]:FORMAT:(json yaml)' \
'--output=[Outputs Onefetch in a specific format]:FORMAT:(json yaml)' \
'--generate=[If provided, outputs the completion file for given SHELL]:SHELL:(bash elvish fish powershell zsh)' \
'--no-title[Hides the title]' \
'--no-merges[Ignores merge commits]' \
'-E[Show the email address of each author]' \
'--email[Show the email address of each author]' \
'--http-url[Display repository URL as HTTP]' \
'--hide-token[Hide token in repository URL]' \
'--include-hidden[Count hidden files and directories]' \
'-z[Use ISO 8601 formatted timestamps]' \
'--iso-time[Use ISO 8601 formatted timestamps]' \
'--no-bold[Turns off bold formatting]' \
'--no-color-palette[Hides the color palette]' \
'--no-art[Hides the ascii art or image if provided]' \
'--nerd-fonts[Use Nerd Font icons]' \
'-l[Prints out supported languages]' \
'--languages[Prints out supported languages]' \
'-p[Prints out supported package managers]' \
'--package-managers[Prints out supported package managers]' \
'-h[Print help (see more with '\''--help'\'')]' \
'--help[Print help (see more with '\''--help'\'')]' \
'-V[Print version]' \
'--version[Print version]' \
'::input -- Run as if onefetch was started in <input> instead of the current working directory:_files -/' \
&& ret=0
}

(( $+functions[_onefetch_commands] )) ||
_onefetch_commands() {
    local commands; commands=()
    _describe -t commands 'onefetch commands' commands "$@"
}

if [ "$funcstack[1]" = "_onefetch" ]; then
    _onefetch "$@"
else
    compdef _onefetch onefetch
fi
```

Fish:

```text
complete -c onefetch -s d -l disabled-fields -d 'Allows you to disable FIELD(s) from appearing in the output' -r -f -a "project\t''
description\t''
head\t''
pending\t''
version\t''
created\t''
languages\t''
dependencies\t''
authors\t''
last-change\t''
contributors\t''
url\t''
commits\t''
churn\t''
lines-of-code\t''
size\t''
license\t''"
complete -c onefetch -l number-of-authors -d 'Maximum NUM of authors to be shown' -r
complete -c onefetch -l number-of-languages -d 'Maximum NUM of languages to be shown' -r
complete -c onefetch -l number-of-file-churns -d 'Maximum NUM of file churns to be shown' -r
complete -c onefetch -l churn-pool-size -d 'Minimum NUM of commits from HEAD used to compute the churn summary' -r
complete -c onefetch -s e -l exclude -d 'Ignore all files & directories matching EXCLUDE' -r
complete -c onefetch -l no-bots -d 'Exclude [bot] commits. Use <REGEX> to override the default pattern' -r
complete -c onefetch -s T -l type -d 'Filters output by language type' -r -f -a "programming\t''
markup\t''
prose\t''
data\t''"
complete -c onefetch -s t -l text-colors -d 'Changes the text colors (X X X...)' -r
complete -c onefetch -l number-separator -d 'Which thousands SEPARATOR to use' -r -f -a "plain\t''
comma\t''
space\t''
underscore\t''"
complete -c onefetch -l ascii-input -d 'Takes a non-empty STRING as input to replace the ASCII logo' -r -f -a "(__fish_complete_command)"
complete -c onefetch -s c -l ascii-colors -d 'Colors (X X X...) to print the ascii art' -r
complete -c onefetch -s a -l ascii-language -d 'Which LANGUAGE\'s ascii art to print' -r -f -a "abnf\t''
abap\t''
ada\t''
agda\t''
arduino\t''
assembly\t''
ats\t''
autohotkey\t''
bash\t''
c\t''
cmake\t''
c#\t''
ceylon\t''
clojure\t''
coffeescript\t''
coldfusion\t''
coq\t''
c++\t''
crystal\t''
css\t''
cuda\t''
d\t''
dart\t''
dockerfile\t''
emacs-lisp\t''
elixir\t''
elm\t''
emojicode\t''
erlang\t''
f#\t''
fish\t''
forth\t''
fortran\t''
fortranmodern\t''
gdscript\t''
glsl\t''
go\t''
graphql\t''
groovy\t''
haskell\t''
haxe\t''
hcl\t''
hlsl\t''
holyc\t''
html\t''
idris\t''
java\t''
javascript\t''
json\t''
jsonnet\t''
jsx\t''
julia\t''
jupyter-notebooks\t''
kotlin\t''
llvm\t''
lean\t''
lisp\t''
lua\t''
makefile\t''
markdown\t''
modelica\t''
nim\t''
nix\t''
ocaml\t''
objective-c\t''
odin\t''
openscad\t''
org\t''
oz\t''
pascal\t''
perl\t''
php\t''
powershell\t''
processing\t''
prolog\t''
protocol-buffers\t''
purescript\t''
python\t''
qml\t''
r\t''
racket\t''
raku\t''
razor\t''
renpy\t''
ruby\t''
rust\t''
sass\t''
scala\t''
scheme\t''
shell\t''
solidity\t''
sql\t''
svelte\t''
svg\t''
swift\t''
systemverilog\t''
tcl\t''
tex\t''
text\t''
toml\t''
tsx\t''
typescript\t''
typst\t''
vala\t''
verilog\t''
vhdl\t''
vimscript\t''
visualbasic\t''
vue\t''
webassembly\t''
wolfram\t''
xsl\t''
xaml\t''
xml\t''
yaml\t''
zig\t''
zsh\t''"
complete -c onefetch -l true-color -d 'Specify when to use true color' -r -f -a "auto\t''
never\t''
always\t''"
complete -c onefetch -s i -l image -d 'Path to the IMAGE file' -r -F
complete -c onefetch -l image-protocol -d 'Which image PROTOCOL to use' -r -f -a "kitty\t''
sixel\t''
iterm\t''"
complete -c onefetch -l color-resolution -d 'VALUE of color resolution to use with SIXEL backend' -r -f -a "16\t''
32\t''
64\t''
128\t''
256\t''"
complete -c onefetch -s o -l output -d 'Outputs Onefetch in a specific format' -r -f -a "json\t''
yaml\t''"
complete -c onefetch -l generate -d 'If provided, outputs the completion file for given SHELL' -r -f -a "bash\t''
elvish\t''
fish\t''
powershell\t''
zsh\t''"
complete -c onefetch -l no-title -d 'Hides the title'
complete -c onefetch -l no-merges -d 'Ignores merge commits'
complete -c onefetch -s E -l email -d 'Show the email address of each author'
complete -c onefetch -l http-url -d 'Display repository URL as HTTP'
complete -c onefetch -l hide-token -d 'Hide token in repository URL'
complete -c onefetch -l include-hidden -d 'Count hidden files and directories'
complete -c onefetch -s z -l iso-time -d 'Use ISO 8601 formatted timestamps'
complete -c onefetch -l no-bold -d 'Turns off bold formatting'
complete -c onefetch -l no-color-palette -d 'Hides the color palette'
complete -c onefetch -l no-art -d 'Hides the ascii art or image if provided'
complete -c onefetch -l nerd-fonts -d 'Use Nerd Font icons'
complete -c onefetch -s l -l languages -d 'Prints out supported languages'
complete -c onefetch -s p -l package-managers -d 'Prints out supported package managers'
complete -c onefetch -s h -l help -d 'Print help (see more with \'--help\')'
complete -c onefetch -s V -l version -d 'Print version'
```

Elvish:

```text

use builtin;
use str;

set edit:completion:arg-completer[onefetch] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'onefetch'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'onefetch'= {
            cand -d 'Allows you to disable FIELD(s) from appearing in the output'
            cand --disabled-fields 'Allows you to disable FIELD(s) from appearing in the output'
            cand --number-of-authors 'Maximum NUM of authors to be shown'
            cand --number-of-languages 'Maximum NUM of languages to be shown'
            cand --number-of-file-churns 'Maximum NUM of file churns to be shown'
            cand --churn-pool-size 'Minimum NUM of commits from HEAD used to compute the churn summary'
            cand -e 'Ignore all files & directories matching EXCLUDE'
            cand --exclude 'Ignore all files & directories matching EXCLUDE'
            cand --no-bots 'Exclude [bot] commits. Use <REGEX> to override the default pattern'
            cand -T 'Filters output by language type'
            cand --type 'Filters output by language type'
            cand -t 'Changes the text colors (X X X...)'
            cand --text-colors 'Changes the text colors (X X X...)'
            cand --number-separator 'Which thousands SEPARATOR to use'
            cand --ascii-input 'Takes a non-empty STRING as input to replace the ASCII logo'
            cand -c 'Colors (X X X...) to print the ascii art'
            cand --ascii-colors 'Colors (X X X...) to print the ascii art'
            cand -a 'Which LANGUAGE''s ascii art to print'
            cand --ascii-language 'Which LANGUAGE''s ascii art to print'
            cand --true-color 'Specify when to use true color'
            cand -i 'Path to the IMAGE file'
            cand --image 'Path to the IMAGE file'
            cand --image-protocol 'Which image PROTOCOL to use'
            cand --color-resolution 'VALUE of color resolution to use with SIXEL backend'
            cand -o 'Outputs Onefetch in a specific format'
            cand --output 'Outputs Onefetch in a specific format'
            cand --generate 'If provided, outputs the completion file for given SHELL'
            cand --no-title 'Hides the title'
            cand --no-merges 'Ignores merge commits'
            cand -E 'Show the email address of each author'
            cand --email 'Show the email address of each author'
            cand --http-url 'Display repository URL as HTTP'
            cand --hide-token 'Hide token in repository URL'
            cand --include-hidden 'Count hidden files and directories'
            cand -z 'Use ISO 8601 formatted timestamps'
            cand --iso-time 'Use ISO 8601 formatted timestamps'
            cand --no-bold 'Turns off bold formatting'
            cand --no-color-palette 'Hides the color palette'
            cand --no-art 'Hides the ascii art or image if provided'
            cand --nerd-fonts 'Use Nerd Font icons'
            cand -l 'Prints out supported languages'
            cand --languages 'Prints out supported languages'
            cand -p 'Prints out supported package managers'
            cand --package-managers 'Prints out supported package managers'
            cand -h 'Print help (see more with ''--help'')'
            cand --help 'Print help (see more with ''--help'')'
            cand -V 'Print version'
            cand --version 'Print version'
        }
    ]
    $completions[$command]
}
```

For PowerShell, emit a deterministic script longer than 500 bytes containing `using namespace System.Management.Automation`, a `Register-ArgumentCompleter` registration, and `-CommandName 'onefetch'`, with candidates for all options and their constrained values from Spec 2.


## Spec 30

The following encoded reference outputs fix the exact ANSI segment boundaries, padding, side-by-side alignment, and palette placement for a one-file, one-commit Rust repository. In these blocks, each literal `\\x1b` denotes one ESC byte. The concrete examples contain HEAD `6069fcf`, relative-time placeholder `<TIME>` or example `29 seconds ago`, size `33 B`, and `git version 2.34.1`; substitute the values calculated for the actual repository and installed Git. The final decoded byte is the ESC sequence represented by `\\x1b[?7h`; the formatting newline before each closing Markdown fence is not output. Other built-in arts use the same composition algorithm with the templates in Spec 26 and pad each art row to that art's maximum visible width before the three-space information gap.

Default ANSI rendering:

```text
\\x1b[?7l\\x1b[39;1m\\x1b[0m\\x1b[31;1m                 R RR RR\\x1b[0m                  \\x1b[31;1mTest\\x1b[0m \\x1b[39;1m~\\x1b[0m \\x1b[31;1mgit version 2.34.1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m              R RRRRRRRR R          R\\x1b[0m     \\x1b[39m-------------------------\\x1b[39m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m R RR       R RRRRRRRRRRRRR R      RR\\x1b[0m     \\x1b[31;1mHEAD\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m6069fcf (master)\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1mrR RRR    R RRRRRRRRRRRRRRRRR R   RRR R\\x1b[0m   \\x1b[31;1mCreated\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m<TIME>\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1mRRR RR   RRRRRRRRRRRRRRRRRRRRRRR  RRRRR\\x1b[0m   \\x1b[31;1mLanguage\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m\\x1b[41m                          \\x1b[49m\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m RRRRR  RRRRRRRRRRRRRRRRRRRRRRRR  RRRR\\x1b[0m    \\x1b[39m          \\x1b[31m●\\x1b[39m \\x1b[39mRust (100.0 %)\\x1b[39m \\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m  RRR RRRRRRRRRRRRRRRRRRRRRRRRRRRR RR\\x1b[0m     \\x1b[31;1mAuthor\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m100% Test 1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m    R  RRRRRRRRRR\\x1b[0m\\x1b[39;1m=  \\x1b[0m\\x1b[31;1mRR\\x1b[0m\\x1b[39;1m = \\x1b[0m\\x1b[31;1mRRRRRRRRRRR\\x1b[0m      \\x1b[31;1mLast change\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m<TIME>\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m     RRRRRRRRRRRR\\x1b[0m\\x1b[39;1m=  \\x1b[0m\\x1b[31;1mRR\\x1b[0m\\x1b[39;1m = \\x1b[0m\\x1b[31;1mRRRRRRRRRR\\x1b[0m       \\x1b[31;1mCommits\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m      RRRRRRRRRRR   RR   RRRRRRRRRR\\x1b[0m       \\x1b[31;1mChurn (1)\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39mmain.rs 1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m     RR==RRRRRRRRRRRRRRRRRRRRRR===RR\\x1b[0m      \\x1b[31;1mLines of code\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m     RR =  ==RRRRRRR  RRRRRR==  = RR\\x1b[0m      \\x1b[31;1mSize\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m33 B (1 file)\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m      RR =     ===========     = RR\\x1b[0m       
\\x1b[39;1m\\x1b[0m\\x1b[31;1m       RR                        R\\x1b[0m        \\x1b[40m   \\x1b[49m\\x1b[41m   \\x1b[49m\\x1b[42m   \\x1b[49m\\x1b[43m   \\x1b[49m\\x1b[44m   \\x1b[49m\\x1b[45m   \\x1b[49m\\x1b[46m   \\x1b[49m\\x1b[47m   \\x1b[49m
\\x1b[39;1m\\x1b[0m\\x1b[31;1m        R                       R\\x1b[0m      
\\x1b[39;1m\\x1b[0m\\x1b[31;1m         R\\x1b[0m                             
\\x1b[?7h
```

Forced true-color rendering:

```text
\\x1b[?7l\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m                 R RR RR\\x1b[0m                  \\x1b[38;2;228;55;23;1mTest\\x1b[0m \\x1b[39;1m~\\x1b[0m \\x1b[38;2;228;55;23;1mgit version 2.34.1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m              R RRRRRRRR R          R\\x1b[0m     \\x1b[39m-------------------------\\x1b[39m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m R RR       R RRRRRRRRRRRRR R      RR\\x1b[0m     \\x1b[38;2;228;55;23;1mHEAD\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m6069fcf (master)\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1mrR RRR    R RRRRRRRRRRRRRRRRR R   RRR R\\x1b[0m   \\x1b[38;2;228;55;23;1mCreated\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m29 seconds ago\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1mRRR RR   RRRRRRRRRRRRRRRRRRRRRRR  RRRRR\\x1b[0m   \\x1b[38;2;228;55;23;1mLanguage\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m\\x1b[48;2;222;165;132m                          \\x1b[49m\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m RRRRR  RRRRRRRRRRRRRRRRRRRRRRRR  RRRR\\x1b[0m    \\x1b[39m          \\x1b[38;2;222;165;132m●\\x1b[39m \\x1b[39mRust (100.0 %)\\x1b[39m \\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m  RRR RRRRRRRRRRRRRRRRRRRRRRRRRRRR RR\\x1b[0m     \\x1b[38;2;228;55;23;1mAuthor\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m100% Test 1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m    R  RRRRRRRRRR\\x1b[0m\\x1b[38;2;255;255;255;1m=  \\x1b[0m\\x1b[38;2;228;55;23;1mRR\\x1b[0m\\x1b[38;2;255;255;255;1m = \\x1b[0m\\x1b[38;2;228;55;23;1mRRRRRRRRRRR\\x1b[0m      \\x1b[38;2;228;55;23;1mLast change\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m29 seconds ago\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m     RRRRRRRRRRRR\\x1b[0m\\x1b[38;2;255;255;255;1m=  \\x1b[0m\\x1b[38;2;228;55;23;1mRR\\x1b[0m\\x1b[38;2;255;255;255;1m = \\x1b[0m\\x1b[38;2;228;55;23;1mRRRRRRRRRR\\x1b[0m       \\x1b[38;2;228;55;23;1mCommits\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m      RRRRRRRRRRR   RR   RRRRRRRRRR\\x1b[0m       \\x1b[38;2;228;55;23;1mChurn (1)\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39mmain.rs 1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m     RR==RRRRRRRRRRRRRRRRRRRRRR===RR\\x1b[0m      \\x1b[38;2;228;55;23;1mLines of code\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m1\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m     RR =  ==RRRRRRR  RRRRRR==  = RR\\x1b[0m      \\x1b[38;2;228;55;23;1mSize\\x1b[0m\\x1b[39;1m:\\x1b[0m \\x1b[39m33 B (1 file)\\x1b[0m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m      RR =     ===========     = RR\\x1b[0m       
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m       RR                        R\\x1b[0m        \\x1b[40m   \\x1b[49m\\x1b[41m   \\x1b[49m\\x1b[42m   \\x1b[49m\\x1b[43m   \\x1b[49m\\x1b[44m   \\x1b[49m\\x1b[45m   \\x1b[49m\\x1b[46m   \\x1b[49m\\x1b[47m   \\x1b[49m
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m        R                       R\\x1b[0m      
\\x1b[39;1m\\x1b[0m\\x1b[38;2;228;55;23;1m         R\\x1b[0m                             
\\x1b[?7h
```
