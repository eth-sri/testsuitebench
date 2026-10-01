# GitType executable behavioral specification

The deliverable is one directly runnable program named exactly `executable`. All text is UTF-8. Unless a rule below explicitly permits operating-system-dependent details, text shown in a fenced block is exact, including capitalization, punctuation, indentation, blank lines, and the final newline. `stdout` and `stderr` are distinct as specified.

## Spec 1

`executable` is a command-line typing-practice application named GitType, version `0.8.0`. It supports this grammar:

```text
executable [OPTIONS] [REPO_PATH] [COMMAND]
```

The top-level options are `--repo <REPO>`, `--langs <LANGS>`, `-h`, `--help`, `-V`, and `--version`. The commands are `history`, `stats`, `export`, `cache`, `repo`, `trending`, and `help`. A recognized command may follow the optional repository path and global options; for example, `--langs rust,python repo_path history` must route to `history`. Global options are accepted before a command, but not after it: `--repo owner/repo history --help` succeeds as history help, while `history --repo owner/repo --help` is an argument error. `--force` is local to `repo clear`, and `--period` is local to `trending`.

There are three exit classes: success/help/version is `0`; a parsed command that encounters a runtime failure or is not implemented is `1`; malformed command-line syntax is `2`. Help and version use stdout only. Successful cache/repository messages use stdout only. Parser errors, unimplemented messages, warnings, and runtime errors use stderr only.

Both `--option value` and `--option=value` forms work. A bare `--` ends option parsing. User arguments are treated literally—never shell-evaluated—and must safely preserve Unicode, punctuation, embedded newlines, leading/trailing spaces, and very long strings.

## Spec 2

The exact long top-level help for `--help` and the bare `help` command is:

```text
GitType turns your own source code into typing challenges. Practice typing by using functions, classes, and methods from your actual projects. 

Examples:
  gittype                           # Use current directory
  gittype /path/to/repo             # Use specific repository
  gittype --repo owner/repo         # Clone and use GitHub repository
  gittype --langs rust,python       # Filter by languages

Usage: executable [OPTIONS] [REPO_PATH] [COMMAND]

Commands:
  history   Show session history
  stats     Show analytics
  export    Export session data
  cache     Manage challenge cache
  repo      Manage repositories
  trending  Select and practice with trending repositories from GitHub
  help      Print this message or the help of the given subcommand(s)

Arguments:
  [REPO_PATH]
          Repository path to extract code from

Options:
      --repo <REPO>
          GitHub repository URL or path to clone and play with. Supports formats:
            - owner/repo
            - https://github.com/owner/repo
            - git@github.com:owner/repo.git

      --langs <LANGS>
          Filter by programming languages (comma-separated). Supported languages:
            rust, typescript, javascript, python, ruby, go, swift, kotlin, java, php, csharp, c, cpp, haskell, dart, scala, zig
            Example: --langs rust,python,typescript

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

It ends with one newline and writes nothing to stderr.

## Spec 3

The top-level short help for `-h` is different from long help and is exactly:

```text
A typing practice tool using your own code repositories - extracts all code chunks (functions, classes, methods, etc.)

Usage: executable [OPTIONS] [REPO_PATH] [COMMAND]

Commands:
  history   Show session history
  stats     Show analytics
  export    Export session data
  cache     Manage challenge cache
  repo      Manage repositories
  trending  Select and practice with trending repositories from GitHub
  help      Print this message or the help of the given subcommand(s)

Arguments:
  [REPO_PATH]  Repository path to extract code from

Options:
      --repo <REPO>    GitHub repository URL or path to clone and play with
      --langs <LANGS>  Filter by programming languages (comma-separated)
  -h, --help           Print help (see more with '--help')
  -V, --version        Print version
```

`-V` and `--version` both write exactly `gittype 0.8.0\n` to stdout and exit 0. Help/version processing is left-to-right: the first encountered help or version flag wins. Thus `--version --help` prints the version, while `--help --version` prints long help and `-h --version` prints short help. A leading global version also wins over a following command, such as `--version history`. Repeated help flags are accepted.

## Spec 4

The leaf-command help outputs are exact:

```text
Show session history

Usage: executable history

Options:
  -h, --help  Print help
```

```text
Show analytics

Usage: executable stats

Options:
  -h, --help  Print help
```

```text
Export session data

Usage: executable export [OPTIONS]

Options:
      --format <FORMAT>  Export format [default: json]
      --output <OUTPUT>  Output file path
  -h, --help             Print help
```

```text
Show cache statistics

Usage: executable cache stats

Options:
  -h, --help  Print help
```

```text
Clear all cached challenges

Usage: executable cache clear

Options:
  -h, --help  Print help
```

```text
List cached repository keys

Usage: executable cache list

Options:
  -h, --help  Print help
```

```text
List all cached repositories

Usage: executable repo list

Options:
  -h, --help  Print help
```

```text
Clear all cached repositories

Usage: executable repo clear [OPTIONS]

Options:
      --force  Force clear without confirmation
  -h, --help   Print help
```

```text
Play a cached repository interactively

Usage: executable repo play

Options:
  -h, --help  Print help
```

For these leaf commands, `-h` and `--help` produce the same text. Help takes precedence over later invalid arguments, while an invalid argument appearing before help is reported first.

## Spec 5

The parent help for `cache --help` is:

```text
Manage challenge cache

Usage: executable cache <COMMAND>

Commands:
  stats  Show cache statistics
  clear  Clear all cached challenges
  list   List cached repository keys
  help   Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help
```

The parent help for `repo --help` is:

```text
Manage repositories

Usage: executable repo <COMMAND>

Commands:
  list   List all cached repositories
  clear  Clear all cached repositories
  play   Play a cached repository interactively
  help   Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help
```

Invoking bare `cache` or bare `repo` is a usage error: exit 2, stdout empty, and write the corresponding complete parent help above to stderr. The `help` command routes hierarchically: `help cache`, `help cache stats`, `help export`, and `help repo clear` produce the same stdout as placing `--help` on those targets. `help nonexistent` exits 2 and writes:

```text
error: unrecognized subcommand 'nonexistent'

Usage: executable [OPTIONS] [REPO_PATH] [COMMAND]

For more information, try '--help'.
```

## Spec 6

Argument errors are clap-style, go only to stderr, end with a newline, and exit 2. General forms are:

```text
error: unexpected argument 'VALUE' found

Usage: COMMAND_USAGE

For more information, try '--help'.
```

```text
error: unrecognized subcommand 'VALUE'

Usage: COMMAND_USAGE

For more information, try '--help'.
```

Only the first invalid argument is reported. The usage is the narrowest parsed command, e.g. `executable history`, `executable stats`, `executable export [OPTIONS]`, `executable cache <COMMAND>`, `executable cache clear`, `executable cache stats`, `executable cache list`, `executable repo <COMMAND>`, `executable repo list`, or `executable repo clear [OPTIONS]`. Extra positional arguments are invalid for every leaf except the two documented trending positionals. At top level only one `REPO_PATH` is allowed.

For an unknown top-level option, and for an unknown option in `trending`, insert this tip between the error and usage:

```text
  tip: to pass '--invalid-flag' as a value, use '-- --invalid-flag'
```

Use the actual option spelling in place of `--invalid-flag`. Close misspellings receive a similarity tip and a usage reflecting the suggested option already recognized. Exact examples are:

```text
error: unexpected argument '--lange' found

  tip: a similar argument exists: '--langs'

Usage: executable --langs <LANGS> [REPO_PATH]

For more information, try '--help'.
```

```text
error: unexpected argument '--fromat' found

  tip: a similar argument exists: '--format'

Usage: executable export --format <FORMAT>

For more information, try '--help'.
```

`--ouput` similarly suggests `--output`. Supplying no value writes `error: a value is required for '--repo <REPO>' but none was supplied` (or `--langs <LANGS>`, `--format <FORMAT>`, `--output <OUTPUT>`, `--period <PERIOD>`), then a blank line and `For more information, try '--help'.`; there is no Usage line. A duplicate non-repeatable option writes `error: the argument '--format <FORMAT>' cannot be used multiple times` (or `--output <OUTPUT>` or `--repo <REPO>`), followed by the normal blank line, usage, blank line, and help hint. If `--langs=rust,python` precedes a later bad option, its error usage is `Usage: executable --langs <LANGS> [REPO_PATH]`.

## Spec 7

The global `--langs` value is a comma-separated filter. Its supported-name report contains these canonical names and aliases: `rust`/`rs`, `typescript`/`ts`, `javascript`/`js`, `python`/`py`, `ruby`/`rb`, `go`, `swift`, `kotlin`/`kt`, `java`, `php`, `csharp`/`cs`/`c#`, `c`, `cpp`/`c++`, `haskell`/`hs`, `dart`, `scala`/`sc`, `zig`, and `clojure`/`clj`/`cljs`. Validation matches supported names case-insensitively, so `RUST` is accepted. It checks every comma-separated item and does not silently discard invalid entries. Whitespace adjacent to commas is not normalized into a valid name; it remains visible in the reported invalid input.

On validation failure, emit the invalid entries followed by the complete alias list in this layout:

```text
❌ Unsupported language(s): invalid1, invalid2
💡 Supported languages:
   rust, rs, typescript, ts, javascript, js
   python, py, ruby, rb, go, swift
   kotlin, kt, java, php, csharp, cs
   c#, c, cpp, c++, haskell, hs
   dart, scala, sc, zig, clojure, clj
   cljs
```

Replace `invalid1, invalid2` with all invalid comma-separated items in their input order, joined by `, `. When language validation is performed, a failure writes this report to stderr and exits 1 before TUI startup. Valid filters continue to TUI startup. An empty explicit `--langs ""` is allowed by argument parsing; runtime behavior may proceed to TUI startup rather than treating the option as missing.

## Spec 8

`history` and `stats` are deliberately unimplemented. With no arguments they exit 1, write nothing to stdout, and write exactly two lines to stderr:

```text
❌ History command is not yet implemented
💡 This feature is planned for a future release
```

or:

```text
❌ Stats command is not yet implemented
💡 This feature is planned for a future release
```

All supplied positional arguments or unknown flags are parser errors (exit 2), including Unicode, shell punctuation, very long arguments, and repeated invalid flags. Only the first is reported. `history --help --invalid` shows help, while `history --invalid --help` reports the invalid option; the same applies to `stats`.

## Spec 9

`export` is also deliberately unimplemented. It accepts one optional `--format <FORMAT>` (default exactly `json`) and one optional `--output <OUTPUT>` in either order and in space or equals syntax. It does not validate either value, normalize case, trim whitespace, expand `~`, resolve paths, execute metacharacters, or reject nonexistent/protected/directory-like paths. It never creates the requested output file. It exits 1, writes nothing to stdout, and emits:

```text
❌ Export command is not yet implemented
💡 Requested format: FORMAT
💡 Requested output: OUTPUT
💡 This feature is planned for a future release
```

The output line is omitted when `--output` was not supplied, producing exactly three lines. `FORMAT` and `OUTPUT` are substituted literally, including embedded newlines and surrounding spaces. An explicitly empty format therefore leaves nothing after the format line's space. Missing option values, duplicate format/output options, unknown options, mixed-case option names, and positional arguments are parser errors as defined above.

## Spec 10

Operational commands initialize per-user state beneath `$HOME/.gittype`. At minimum this creates `$HOME/.gittype` and `$HOME/.gittype/logs`, with owner read/write/search permissions, without deleting pre-existing files. Empty or trailing-slash HOME values must not crash; normalize a trailing slash and use a safe current-directory/platform fallback for an empty value.

Each operational invocation creates or retains at least one nonempty routine log in `$HOME/.gittype/logs`. Routine filenames contain a `YYYYMMDD_HHMMSS` substring, conventionally `gittype_YYYYMMDD_HHMMSS.log`. Repeated and concurrent cache calls must not corrupt state or delete earlier logs. There must be no routine `.log` files directly in `$HOME/.gittype`.

Fatal runtime failures additionally create exactly one `gittype_error_YYYYMMDD_HHMMSS.log` in the process's current working directory and announce `💾 Error details written to: gittype_error_YYYYMMDD_HHMMSS.log` on stderr. That file contains lines/fields including `ERROR OCCURRED AT:`, `ERROR MESSAGE: ...`, `EXECUTABLE: ...executable`, and `COMMAND_ARGS:`. If `RUST_LOG` or `RUST_BACKTRACE` is present in the environment, record it verbatim on a line `RUST_LOG: value` or `RUST_BACKTRACE: value`. Loading a missing or malformed `$HOME/.gittype/config.json` is nonfatal and must not replace the primary runtime error.

## Spec 11

The challenge cache is the directory `$HOME/.gittype/cache`; it is independent of `$HOME/.gittype/repos` and any XDG data directories. `cache stats` exits 0 with stderr empty and reports immediate regular files in that directory, regardless of filename extension, hidden status, compression validity, or contents. It does not recursively count files in subdirectories. The exact empty output is:

```text
Challenge Cache Statistics:
  Cached repositories: 0
  Total size: 0 bytes
```

If `$HOME/.gittype/cache` does not exist, `cache stats` reports the empty output above without creating that directory.

For a nonempty cache the same three-line structure is used. The repository count is the number of immediate regular files and total size is their sum in on-disk bytes. Sizes below 1024 are `N bytes`; from 1024 bytes use kibibyte scaling displayed as one decimal followed by `KB`; from 1024² use one decimal followed by `MB`. A zero-byte file counts as one repository but contributes `0 bytes`. Repeated and concurrent calls return a consistent snapshot and exit successfully.

## Spec 12

`cache clear` creates required application directories if missing, removes every immediate regular file in `$HOME/.gittype/cache` (including read-only files when permissions allow), does not touch nested subdirectories or repository files, and exits 0 with stderr empty and exactly:

```text
Challenge cache cleared successfully.
```

It is idempotent and safe under concurrent invocations. `cache list` considers only immediate files whose extension is exactly lowercase `.bin`; malformed, corrupt, non-gzip, or otherwise unrecognized entries are skipped without failing. If no valid entries can be decoded, it exits 0 with stderr empty and exactly:

```text
No cached challenges found.
```

Missing and empty cache directories produce identical output. When the directory is missing, `cache list` does not create it. Cache stats still counts malformed and non-`.bin` files, which is intentionally different from list. Cache operations never alter `$HOME/.gittype/repos` or sibling/custom directories.

## Spec 13

Repository storage is rooted at `$HOME/.gittype/repos`, independently of the challenge cache. `repo list` and `repo play` are interactive commands; when stdout/stdin do not provide a usable terminal they exit 1, write nothing to stdout, create the fatal error log described above, and write its announcement followed by exactly:

```text
Error: Terminal error: Not running in a terminal environment. Please run in a proper terminal.
```

Launching the main application without a usable terminal similarly exits 1 with a logged `IO error` or terminal-creation error. A top-level unrecognized bare word may be parsed as `REPO_PATH` and reach this runtime error rather than being rejected as a subcommand. Supplying both `--repo owner/repo` and a positional repository path is syntactically accepted and proceeds to runtime/TUI selection, with `--repo` taking precedence. Supplying `--repo` twice is a parser error.

## Spec 14

`repo clear [--force]` recursively detects cached repositories as directories anywhere below `$HOME/.gittype/repos` that directly contain an entry named `.git`. That entry may be a directory or a regular file; either form is sufficient, and other files and Git internals are irrelevant. Directories without a `.git` entry do not contribute to the count.

If `$HOME/.gittype/repos` does not exist, exit 0 with stderr empty and exactly `No cached repositories directory found.\n`. If it exists but contains no detected repositories, exit 0 with exactly `No cached repositories found.\n` and do not prompt.

When repositories exist and `--force` is absent, stdout begins with these three newline-terminated lines, followed by a prompt that is not newline-terminated before the response:

```text
This will delete all locally cached repositories in:
  HOME/.gittype/repos
(N cached repositories will be removed)
Are you sure you want to continue? [y/N]: 
```

Trim surrounding input whitespace and compare case-insensitively. `y` and `yes` confirm. Every other response, including `n`, `no`, empty, and invalid text, prints `Operation cancelled.\n` immediately after the prompt on the same line, exits 0, and changes nothing. Confirmation recursively removes the entire `$HOME/.gittype/repos` tree and prints `Successfully deleted all cached repositories.\n` immediately after the prompt on the same line, then prints:

```text
Cache directory HOME/.gittype/repos has been removed.
```

With `--force`, omit the warning/prompt and immediately print `Successfully deleted all cached repositories.\n` followed by the cache-directory line above. The literal absolute path replaces `HOME/.gittype/repos`. Repository clearing must preserve every challenge-cache file and all unrelated application state; in particular, it does not create `$HOME/.gittype/cache` when that directory is absent.

## Spec 15

The long `trending --help` output is:

```text
Select and practice with trending repositories from GitHub

Usage: executable trending [OPTIONS] [LANGUAGE] [REPO_NAME]

Arguments:
  [LANGUAGE]
          Programming language to filter trending repositories.
          Supported languages: C, C#, C++, Dart, Go, Haskell, Java, JavaScript, Kotlin, PHP, Python, Ruby, Rust, Scala, Swift, TypeScript, Zig

  [REPO_NAME]
          Specific repository name to select from trending list

Options:
      --period <PERIOD>
          Time period for trending (daily, weekly, monthly)
          
          [default: daily]

  -h, --help
          Print help (see a summary with '-h')
```

The short `trending -h` output is:

```text
Select and practice with trending repositories from GitHub

Usage: executable trending [OPTIONS] [LANGUAGE] [REPO_NAME]

Arguments:
  [LANGUAGE]   Programming language to filter trending repositories
  [REPO_NAME]  Specific repository name to select from trending list

Options:
      --period <PERIOD>  Time period for trending (daily, weekly, monthly) [default: daily]
  -h, --help             Print help (see more with '--help')
```

## Spec 16

At runtime, trending recognizes exactly these 16 language display names, case-insensitively: `C`, `C#`, `C++`, `Dart`, `Go`, `Haskell`, `Java`, `JavaScript`, `Kotlin`, `PHP`, `Python`, `Ruby`, `Rust`, `Scala`, `Swift`, `TypeScript`. The documentation intentionally also mentions Zig, but runtime trending must reject Zig. Matching is exact apart from case: do not trim whitespace or perform prefix/fuzzy matching.

An invalid language exits 1, stdout empty, writes a fatal log, and writes this stderr shape:

```text
❌ Unsupported language: 'VALUE'
📚 Supported languages: C, C#, C++, Dart, Go, Haskell, Java, JavaScript, Kotlin, PHP, Python, Ruby, Rust, Scala, Swift, TypeScript
💾 Error details written to: gittype_error_YYYYMMDD_HHMMSS.log
Error: Validation error: Unsupported language: VALUE
```

Language validation happens before repository-name validation. `--period` defaults to `daily`, accepts space/equals syntax in any option position, and accepts any string at parse time (including values other than daily/weekly/monthly). Missing `--period` values remain parser errors.

With a valid language, a missing repository name opens the interactive repository selector; without a TTY it exits 1 with the logged terminal-creation error. A provided repository name passes the initial format check if and only if it contains at least one `/`; even `/`, `owner/`, `/repo`, multiple slashes, spaces, and Unicode pass this shallow check and proceed to repository/TUI work. A name containing no slash—including an empty name—does not create an error log, exits 0, and writes exactly to stderr:

```text
⚠️ Repository name must be in format 'owner/repo'
```

## Spec 17

Interactive execution requires a real pseudo-terminal, supports UTF-8 and ANSI terminal control, and settles to deterministic 80-column by 24-row snapshots. On launch with a repository path (valid or invalid), first show an initial screen containing `Update Available`, with Space offered to continue and Escape to exit. Space must reach the title screen; Escape or Ctrl+C cleanly terminates, restores the terminal, and leaves no substantial screen content. Repeated snapshots of a stable screen are identical. Once on the title screen, Escape or Ctrl+C likewise exits promptly.

## Spec 18

The default title screen is exactly:

```text


                          ____ _ _  _____
                         / ___(_) ||_   _|   _ _ __   ___
                        | |  _| | __|| || | | | '_ \ / _ \
                        | |_| | | |_ | || |_| | |_) |  __/
                         \____|_|\__||_| \__, | .__/ \___|
                                         |___/|_|

                              Code Typing Challenge

                             Difficulty: ← Normal →
                 Challenge count will be displayed after loading
                                 ~200 characters
                                Medium functions

                            [←→/HL] Change Difficulty
              [R] Records  [A] Analytics  [S] Settings  [I/?] Help
                            [SPACE] Start  [ESC] Quit
```

Difficulty is a circular sequence `Easy → Normal → Hard → Wild → Zen → Easy`, initially Normal. Right/`l` advances and Left/`h` reverses. The ASCII logo, blank lines, challenge-count line, and footer remain identical. Replace the three centered difficulty-specific lines with exactly:

```text
                              Difficulty: ← Easy →
                                 ~100 characters
                               Short code snippets
```

```text
                             Difficulty: ← Normal →
                                 ~200 characters
                                Medium functions
```

```text
                              Difficulty: ← Hard →
                                 ~500 characters
                            Long functions or classes
```

```text
                              Difficulty: ← Wild →
                                   Full chunks
                           Unpredictable length chunks
```

```text
                               Difficulty: ← Zen →
                                  Entire files
                          Complete files as challenges
```

Navigation to and back from another screen preserves the selected difficulty. Rapid balanced navigation produces the corresponding deterministic final screen.

## Spec 19

Repository startup must tolerate missing paths, empty files, comments, Unicode, mixed indentation, deeply nested constructs, very long lines, multiple files, and realistic syntax without crashing. Recognize source files for Python, Rust, C, C++, Java, JavaScript, TypeScript, Go, Ruby, PHP, C#, Kotlin, Swift, Scala, Haskell, Dart, Zig, and Clojure. Relevant extensions include `.py`, `.rs`, `.c`, `.h`, `.cpp`, `.java`, `.js`, `.ts`, `.go`, `.rb`, `.php`, `.cs`, `.kt`, `.swift`, `.scala`, `.hs`, `.dart`, `.zig`, `.clj`, `.cljs`, and `.cljc`.

Scanning should be robust around language constructs such as functions/methods, classes/structs/interfaces/traits/protocols, generics/templates, annotations/decorators/attributes, macros, namespaces/modules, lambdas/arrow functions, async syntax, operator overloads, comments, strings, regular expressions, and metaprogramming. Regardless of whether extractable chunks are ultimately found, startup reaches the title screen showing `Code Typing Challenge`, `Difficulty:`, `[SPACE] Start`, and `[ESC] Quit`. If Space is pressed and no challenge is available for the current difficulty—including a missing repository or code too short for that difficulty—remain on the title view and visibly add the phrase `No challenges available` without crashing.

## Spec 20

From the title screen, `i` or `?` opens Help, `r` or `R` opens Records, `a` or `A` opens Analytics, and `s` or `S` opens Settings. Escape from any of these returns to the title screen; a second Escape exits. The Help screen's initial 80×24 snapshot is exactly:

```text
┌Help──────────────────────────────────────────────────────────────────────────┐
│ CLI Usage │ Scoring System │ Rank System │ Game Help │ Community │ About & Cr│
└──────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────┐
│  Basic Usage:                                                                ▲
│                                                                              █
│  gittype                          # Start with current directory             █
│  gittype /path/to/repo            # Use specific repository path             █
│  gittype --repo owner/repo        # Clone and use GitHub repository          █
│  gittype --langs rust,python      # Filter by programming languages          █
│                                                                              █
│  Repository Commands:                                                        ║
│                                                                              ║
│  gittype repo list                # List all cached repositories             ║
│  gittype repo clear               # Clear all cached repositories            ║
│  gittype repo clear --force       # Force clear without confirmation         ║
│  gittype repo play                # Play a cached repository interactively   ║
│                                                                              ║
│  Cache Management:                                                           ▼
└──────────────────────────────────────────────────────────────────────────────┘

★ Star us on GitHub (https://github.com/unhappychoice/gittype) if you enjoy GitT

            [←→/HL] Switch tabs [↑↓/JK] Scroll [G] GitHub [ESC] Close
```

## Spec 21

With an empty database, Records initially renders exactly:

```text
┌Session Records───────────────────────────────────────────────────────────────┐
│  Records - Typing Session Records                                            │
│  Filter: Last 30 days | Sort: Date ↓ | Sessions: 0                           │
└──────────────────────────────────────────────────────────────────────────────┘
┌Sessions──────────────────────────────────────────────────────────────────────┐
│            No typing sessions found for the selected time period.            │
│                      Start typing to build your records!                     │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
[↑↓/JK] Navigate  [SPACE] Details  [F] Filter  [S] Sort  [R] Refresh  [ESC] Back
```

On an empty list, Up/Down/`j`/`k`, Space, and refresh `R` leave the screen unchanged. `f`/`F` cycles the date filter; the first press changes `Last 30 days` to `Last 90 days`. `s`/`S` cycles the sort field; the first press changes `Date ↓` to `Score ↓`, preserving descending direction. These actions remain safe under rapid input. Ctrl+C initiates clean application exit.

## Spec 22

Analytics starts on Overview. Left/Right and `h`/`l` cycle `Overview`, `Trends`, `Repositories`, and `Languages`; `r` or `R` refreshes without crashing and Escape returns to title. With no session data, the four snapshots are respectively:

```text
┌GitType Analytics─────────────────────────────────────────────────────────────┐
│  Performance Analytics                                                       │
└──────────────────────────────────────────────────────────────────────────────┘
┌Views─────────────────────────────────────────────────────────────────────────┐
│  Overview | Trends | Repositories | Languages                                │
└──────────────────────────────────────────────────────────────────────────────┘
┌Overview (Last 7 days)────────────────────────────────────────────────────────┐
│      Sessions: 0  │  Avg CPM: 0.0  │  Best CPM: 0.0  │  Avg Accuracy: 0.0%   │
│Total Time: 0.0h  │  Avg Session: 0.0m  │  Total Mistakes: 0  │  Repositories:│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
┌Recent Activity───────────────────────────────────────────────────────────────┐
│                                                                              │
│  No recent activity - start typing to see your activity chart!               │
└──────────────────────────────────────────────────────────────────────────────┘
┌Top Repositories (Last 90 Days)───────┐┌Top Languages (Last 90 Days)──────────┐
│No repository data available          ││No language data available            │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
└──────────────────────────────────────┘└──────────────────────────────────────┘
         [←→/HL] Switch View  [↑↓/JK] Navigate  [R] Refresh  [ESC] Back
```

```text
┌GitType Analytics─────────────────────────────────────────────────────────────┐
│  Performance Analytics                                                       │
└──────────────────────────────────────────────────────────────────────────────┘
┌Views─────────────────────────────────────────────────────────────────────────┐
│  Overview | Trends | Repositories | Languages                                │
└──────────────────────────────────────────────────────────────────────────────┘
┌CPM Trend─────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  No trend data available - keep typing to build your performance history!    │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
┌Accuracy Trend────────────────────────────────────────────────────────────────┐
│                                                                              │
│  No accuracy trend data available - keep typing to build your accuracy histor│
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
         [←→/HL] Switch View  [↑↓/JK] Navigate  [R] Refresh  [ESC] Back
```

```text
┌GitType Analytics─────────────────────────────────────────────────────────────┐
│  Performance Analytics                                                       │
└──────────────────────────────────────────────────────────────────────────────┘
┌Views─────────────────────────────────────────────────────────────────────────┐
│  Overview | Trends | Repositories | Languages                                │
└──────────────────────────────────────────────────────────────────────────────┘
┌Repositories──────────────────┐┌Repository Details (Last 90 Days)─────────────┐
│► No repositories available   ││                                              │
│                              ││  No Repository Selected                      │
│                              ││                                              │
│                              ││  Select a repository from the list to view de│
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
└──────────────────────────────┘└──────────────────────────────────────────────┘
         [←→/HL] Switch View  [↑↓/JK] Navigate  [R] Refresh  [ESC] Back
```

```text
┌GitType Analytics─────────────────────────────────────────────────────────────┐
│  Performance Analytics                                                       │
└──────────────────────────────────────────────────────────────────────────────┘
┌Views─────────────────────────────────────────────────────────────────────────┐
│  Overview | Trends | Repositories | Languages                                │
└──────────────────────────────────────────────────────────────────────────────┘
┌Languages─────────────────────┐┌Language Details (Last 90 Days)───────────────┐
│► No languages available      ││                                              │
│                              ││  No Language Selected                        │
│                              ││                                              │
│                              ││  Select a language from the list to view deta│
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
│                              ││                                              │
└──────────────────────────────┘└──────────────────────────────────────────────┘
         [←→/HL] Switch View  [↑↓/JK] Navigate  [R] Refresh  [ESC] Back
```

## Spec 23

Settings starts on the Color Mode tab in Dark mode. Left/Right and `h`/`l` switch between Color Mode and Theme; Up/Down and `j`/`k` move the selection. The ANSI-stripped Color Mode snapshot is identical whether Dark or Light is selected and is exactly:

```text
┌Settings──────────────────────────────────────────────────────────────────────┐
│ Color Mode │ Theme                                                           │
└──────────────────────────────────────────────────────────────────────────────┘
┌Color Mode────────────────────────────┐┌Description───────────────────────────┐
│  Dark                                ││  Choose between dark and light       │
│  Light                               ││  modes                               │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
│                                      ││                                      │
└──────────────────────────────────────┘└──────────────────────────────────────┘
         [←→/HL] Switch tabs [↑↓/JK] Navigate [SPACE] Save [ESC] Cancel
```

The initial Theme snapshot is:

```text
┌Settings──────────────────────────────────────────────────────────────────────┐
│ Color Mode │ Theme                                                           │
└──────────────────────────────────────────────────────────────────────────────┘
┌Theme─────────────────────────────────┐┌Description───────────────────────────┐
│  Default                             ││  Select theme - preview changes      │
│  Original                            ││  instantly                           │
│  ASCII                               ││                                      │
│  Aurora                              ││  Default theme with softened         │
│  Blood Oath                          ││  contrast and balanced palette for   │
│  Cyber Void                          ││  comfortable readability             │
│  Eclipse                             ││                                      │
│  Glacier                             ││  Color Preview:                      │
│  Inferno                             ││  ● This is Border color              │
│  Neon Abyss                          ││  ● This is Title color               │
│  Oblivion                            ││  ● This is Text color                │
│  Runic                               ││  ● This is Text Secondary color      │
│  Spectral                            ││  ● This is Success color             │
│  Starforge                           ││  ● This is Error color               │
│  Venom                               ││  ● This is Warning color             │
│  Custom                              ││  ● This is Info color                │
│                                      ││  ● This is Key Action color          │
│                                      ││  ● This is Key Navigation color      │
└──────────────────────────────────────┘└──────────────────────────────────────┘
         [←→/HL] Switch tabs [↑↓/JK] Navigate [SPACE] Save [ESC] Cancel
```

Space saves all pending settings as valid JSON in `$HOME/.gittype/config.json`. The object has a `theme` object containing `current_theme_id` and `current_color_mode`. Defaults are `default` and `Dark`. Moving once down on Theme selects id `original`; moving three times selects `aurora`. Moving once down on Color Mode selects `Light`. Saving both yields `{"theme":{"current_theme_id":"aurora","current_color_mode":"Light"}}` modulo additional fields and JSON whitespace. Escape cancels and returns to the unchanged title screen.

## Spec 24

Interactive `executable trending` opens this exact language-selection screen directly (there is no update screen in this command):

```text
  ┌GitType - Trending Languages──────────────────────────────────────────────┐
  │  🌏 Select Programming Language                                          │
  └──────────────────────────────────────────────────────────────────────────┘
  ┌Programming Languages─────────────────────────────────────────────────────┐
  │                                                                          │
  │  1. C                                                                    │
  │  2. C#                                                                   │
  │  3. C++                                                                  │
  │  4. Dart                                                                 │
  │  5. Go                                                                   │
  │  6. Haskell                                                              │
  │  7. Java                                                                 │
  │  8. JavaScript                                                           │
  │  9. Kotlin                                                               │
  │ 10. PHP                                                                  │
  │ 11. Python                                                               │
  │ 12. Ruby                                                                 │
  │ 13. Rust                                                                 │
  │ 14. Scala                                                                │
  │ 15. Swift                                                                │
  │ 16. TypeScript                                                           │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘
                 [↑↓/JK] Navigate  [SPACE] Select  [ESC] Return
```

The initial cursor is the first item (C), with highlighting allowed through ANSI attributes. Up/Down and `j`/`k` navigate; Space selects. Escape exits cleanly. Ctrl+C from this language-selection screen instead exits with status 101 and reports the panic message `Invalid screen transition: TrendingLanguageSelection -> TotalSummary`. Selecting a language, or invoking `trending LANGUAGE` in a TTY, opens a repository-selection view containing all of these strings and Unicode box borders: `GitType - Trending`, `Select Trending Repository to Play`, `Currently trending repositories`, `Trending Repositories`, `[↑↓/JK] Navigate`, `[SPACE] Play`, and `[ESC] Return`. This layout must remain valid even when no remote results are available. From that repository-selection view, Escape/Ctrl+C returns or exits cleanly, and rapid navigation/selection must not crash. The period option does not change these structural requirements.

## Spec 25

Interactive repository startup initializes SQLite at `$HOME/.gittype/gittype.db` before showing the stable title screen. Initialization is idempotent and preserves the same database across commands. It creates at least these tables: `repositories`, `sessions`, `stages`, `challenges`, `session_results`, `stage_results`, and `schema_version`.

The required columns and declared SQLite types are:

- `repositories`: `id INTEGER` (or `INT`), `user_name TEXT`, `repository_name TEXT`, plus `remote_url` and `created_at`.
- `sessions`: `id INTEGER` (or `INT`), `repository_id`, `started_at DATETIME` (or `TEXT`), `completed_at`, `branch`, `commit_hash`, `is_dirty`, and `game_mode TEXT`. It declares a foreign key referencing `repositories`.
- `challenges`: `id TEXT`, `code_content TEXT`, `language TEXT`, `file_path TEXT`, `start_line`, `end_line`, and `difficulty_level`.
- `stages`: `id`, `session_id`, `challenge_id`, `stage_number`, `started_at`, and `completed_at`, with foreign keys referencing both `sessions` and `challenges`.
- `stage_results`: `id`, `stage_id`, `session_id`, `repository_id`, `keystrokes INTEGER` (or `INT`), `mistakes INTEGER` (or `INT`), `duration_ms INTEGER` (or `INT`), `wpm REAL`, `cpm`, `accuracy REAL`, `score`, `was_skipped`, `was_failed`, and `completed_at`.
- `session_results`: `id`, `session_id`, `repository_id`, `keystrokes INTEGER` (or `INT`), `mistakes INTEGER` (or `INT`), `duration_ms`, `wpm REAL`, `cpm`, `accuracy`, `stages_completed INTEGER` (or `INT`), `stages_attempted`, `stages_skipped`, `score REAL`, `rank_name`, and `tier_name`.
- `schema_version`: at least `version` and `applied_at`. It contains at least one row whose version is an integer of at least 1 and whose applied_at is non-null.

Merely launching and quitting without completing a typing game leaves records/analytics empty. Cache commands continue to work without a database and do not destroy or recreate an existing database.
