# Eureka executable specification

The required artifact is a directly runnable file named exactly `executable`. It is a command-line program for configuring an ideas repository, viewing that repository's `README.md`, and capturing an idea by opening the README in an editor and committing it to Git. All paths, output, exit statuses, environment-variable behavior, and external-program interactions needed to implement it are defined below.

In escaped output examples, `\x1b` denotes the single ESC byte (U+001B), `\n` denotes LF, and adjacent quoted fragments are concatenated without adding characters.

## Spec 1

The executable has no subcommands and accepts only these options:

- `--clear-config`
- `-v` and `--view`, which are equivalent
- `-h` and `--help`, which are equivalent
- `-V` and `--version`, which are equivalent

Short options may be clustered, so `-vh` is accepted and displays help. Repeating equivalent help options (`-h --help`) or version options (`-V --version`) is accepted. Options are case-sensitive.

No positional operands are accepted, including operands after `--`. Unknown options, positional operands, and attempts to give `--clear-config` a value (for example `--clear-config=true`, `--clear-config=false`, or `--clear-config true`) are command-line errors. Such an error exits with status 2, writes nothing to standard output, produces no normal workflow, and writes a diagnostic to standard error containing `error:`, `unexpected argument` (or, for an attached value, an equivalent `unexpected value`/`invalid` phrase), and `For more information, try '--help'.`. The offending argument must be named in the diagnostic. Except for the argument-specific cases below, the diagnostic contains the line `Usage: executable [OPTIONS]`; this generic form applies to a separated value such as `--clear-config true`.

The complete diagnostics for the two attached-value examples are:

```text
error: unexpected value 'true' for '--clear-config' found; no more were expected

Usage: executable --clear-config

For more information, try '--help'.
```

```text
error: unexpected value 'false' for '--clear-config' found; no more were expected

Usage: executable --clear-config

For more information, try '--help'.
```

Because options are case-sensitive, `--View` is rejected with this complete diagnostic, including the suggestion and argument-specific usage line:

```text
error: unexpected argument '--View' found

  tip: a similar argument exists: '--view'

Usage: executable --view

For more information, try '--help'.
```

Each displayed diagnostic ends with one newline. Command-line diagnostic/help text contains no ANSI color sequences.

## Spec 2

Help is available without configuration and exits 0. `-h` and `--help` produce identical standard output and empty standard error. The complete output is exactly the following, including blank lines, indentation, and one final newline; no line has trailing spaces:

```text
Input and store your ideas without leaving the terminal

Usage: executable [OPTIONS]

Options:
      --clear-config  Clear your stored configuration
  -v, --view          View ideas with your $PAGER env variable. If unset use less
  -h, --help          Print help
  -V, --version       Print version
```

There is no `Commands:` or `Subcommands:` section. Help also takes effect when combined with a valid operational flag, such as `--help --view` or `-vh`, without accessing configuration. `--help --version` displays help. An unknown argument encountered in a command line such as `--bogus --help` remains an error rather than being hidden by help.

## Spec 3

Version is available without configuration. `-V` and `--version` exit 0, write exactly `eureka 2.0.0\n` to standard output, and write nothing to standard error. Version terminates normal processing when combined with an operational option, as in `--version --clear-config`.

When both `--clear-config` and either form of `--view` are supplied, in either order, clearing takes precedence: only the clear operation is performed and README content is not displayed.

## Spec 4

The configuration location is selected on every invocation as follows:

- If `XDG_CONFIG_HOME` is set, its value is used even when it is empty. For a nonempty value, the directory is `$XDG_CONFIG_HOME/eureka`; for an empty value, the directory is the relative path `eureka`, resolved from the process working directory.
- If `XDG_CONFIG_HOME` is unset, the directory is `$HOME/.config/eureka`.
- The sole recognized configuration file is `config.json` in that directory. Files such as `config.toml`, `eureka.json`, and `settings.json` are ignored.

`XDG_CONFIG_HOME` takes precedence over `HOME`. Separate environment locations must remain independent; no configuration may be cached between processes. Paths may contain spaces, dots, Unicode, shell metacharacters, or be very long.

## Spec 5

A newly written configuration is UTF-8 JSON with exactly one field, `repo`, whose value is a JSON string. It uses compact serialization with no spaces and no final newline. For example, accepting `/tmp/valid_absolute` writes exactly:

```json
{"repo":"/tmp/valid_absolute"}
```

The displayed code block's structural newline is not part of the file. JSON escaping must preserve the string value on a decode/encode round trip, including quotes, backslashes, tabs, Unicode, spaces, and paths roughly 2,000 characters long. The configuration directory is created recursively if absent and must at least be readable, writable, and searchable by its owner. Writing a new setup replaces any prior file rather than appending.

When reading, `repo` must be a string and is used as the repository path. Unknown top-level fields, including nested objects, are ignored. Symlinks and special characters are handled as ordinary path content. A syntactically valid configuration with extra fields continues to work.

## Spec 6

With no operational flag, the program chooses setup or capture as follows:

- If `config.json` is absent, run first-time setup and stop after setup completes. Capturing an idea requires a later invocation.
- If `config.json` contains a usable configuration, do not show setup; enter idea-capture mode.
- An entirely empty config file is interpreted as a default configuration whose `repo` is the empty string. Thus it enters capture mode, prompts for a summary, and later reports a Git path-resolution error rather than rerunning setup.
- A nonempty config that cannot be decoded instead triggers first-time setup. In particular, a file containing `{"repo": "/some/path"` causes the setup banner and repository-path prompt to be written; it does not produce a JSON-decoder diagnostic in this unflagged mode. Input such as `unused summary` is consequently validated as a setup path, rejected with `Path must be absolute`, and followed by another repository-path prompt. Accepting a later absolute path replaces the malformed file with the new compact configuration and completes setup.

With `--view`, a missing configuration is an error; view mode never initiates setup.

## Spec 7

First-time setup writes this exact standard-output byte sequence for a first-attempt valid path and writes nothing to standard error:

```text
"\x1b[0m\x1b[33m############################################################\n"
"####                  First Time Setup                  ####\n"
"############################################################\n"
"\n"
"This tool requires you to have a repository with a README.md\n"
"in the root folder. The markdown file is where your ideas\n"
"will be stored.\n"
"\n"
"Once first time setup has completed, simply run Eureka again\n"
"to begin writing down ideas.\n"
"        \n"
"\x1b[0m\x1b[0m\x1b[1m\x1b[32mAbsolute path to your idea repo\n"
"\x1b[0m> First time setup complete. Happy ideation!\n"
```

The quotation marks are notation, not output. The otherwise blank line before the first reset contains exactly eight ASCII spaces. The banner is emitted once, in yellow (`ESC[33m`). Each input heading is bold green (`ESC[1m` and `ESC[32m`) and is followed by a reset and the input marker `> `. Prompts must be flushed so an interactive caller sees them before typing.

## Spec 8

Setup reads one line at a time, removes leading and trailing whitespace from that line, and validates the result lexically:

- Empty or whitespace-only input silently causes one additional prompt with these exact bytes:

  ```text
  "\x1b[0m\x1b[1m\x1b[32mAbsolute path to your idea repo\n"
  "\x1b[0m> "
  ```

  This repeated prompt starts with one reset sequence. It is therefore not byte-identical to the first heading in Spec 7, which has two consecutive resets because the banner's final reset immediately precedes the prompt's reset.
- A nonempty path is accepted only if it is absolute on Unix (starts at `/`). Relative forms including `relative/path`, `./path`, `../path`, and `~/path` are rejected. A tilde is not expanded.
- Every rejected relative path prints `\x1b[0m\x1b[31mPath must be absolute\n\x1b[0m` immediately after the current `> ` marker, then prompts again.
- Any lexically absolute path is accepted without requiring that the path, a Git repository, or a README currently exist.
- An accepted path is stored exactly after outer whitespace removal. Interior whitespace/tabs, Unicode, backslashes, dot components, symlink-looking components, and a trailing slash are preserved.

For example, relative input followed by `/tmp/test_repo` produces exactly the Spec 7 banner through its first `> `, followed by:

```text
"\x1b[0m\x1b[31mPath must be absolute\n"
"\x1b[0m\x1b[0m\x1b[1m\x1b[32mAbsolute path to your idea repo\n"
"\x1b[0m> First time setup complete. Happy ideation!\n"
```

Each empty or invalid line causes exactly one additional prompt. If standard input reaches EOF while setup is still waiting for a valid path, every subsequent read is treated as another empty input: the program continuously emits the same one-reset prompt rather than exiting. Once a valid path is accepted, extra already-buffered input lines are ignored, the compact config is written, the completion line is printed, and the process exits 0.

## Spec 9

`--clear-config` removes only the selected `config.json`; it leaves the containing `eureka` directory and every other file intact. Successful removal exits 0 with completely empty standard output and standard error. Subsequent no-argument execution performs setup again.

If `config.json` does not exist, clearing still exits 0, writes nothing to standard output, and writes exactly this to standard error:

```text
 ERROR eureka > No such file or directory (os error 2)
```

The line ends with one newline.

## Spec 10

View mode reads the configured repo and constructs the path by appending the filename `README.md`. It launches a pager executable with that complete path as its sole argument and waits for it:

- Use the nonempty value of `PAGER` as the executable name/path.
- If `PAGER` is unset, use `less`.
- Treat the entire environment value as one executable name; do not shell-split it. Consequently `PAGER="head -n 3"` attempts to find a program literally bearing that name and reports a not-found error.

The pager inherits the executable's standard output and standard error. Thus `PAGER=cat` reproduces README bytes exactly (including empty files, blank lines, Unicode, shell-like characters, and large files); `PAGER=head` applies that program's normal ten-line behavior; `PAGER=echo` prints the README path; and a custom pager receives the exact path. Repo paths with spaces, Unicode, metacharacters, long components, dots, and symlinks must be passed as one argument, without shell interpretation.

Successful paging exits 0 and adds no output of its own. Repeated view invocations are independent.

## Spec 11

Failures in ordinary operations are logged but do not make the top-level program fail: configuration-read errors, missing files, pager launch failures, invalid Git repositories, commit errors, and push errors normally produce process status 0. These errors use standard error; view/config errors leave standard output empty. The generic log format is one line beginning with exactly one leading space:

```text
 ERROR eureka > <underlying error text>
```

For a missing configuration, nonexistent configured repo, missing `README.md`, empty repo path, whitespace-only repo path, or otherwise missing file during view, the complete standard error is:

```text
 ERROR eureka > No such file or directory (os error 2)
```

A pager value naming no executable, including a value containing embedded arguments, likewise produces a logged `No such file or directory` error. Pager exit failure must be handled without a crash or hang.

## Spec 12

In `--view` mode, nonempty malformed JSON is rejected rather than triggering setup. The program exits 0, emits no normal view output, and logs the JSON decoder's message. (The unflagged workflow instead enters setup as specified in Spec 6.) These input/error pairs are exact, including the leading space and final newline:

- `{"repo": "/some/path"` → ` ERROR eureka > EOF while parsing an object at line 1 column 21\n`
- `{repo: "/some/path"}` → ` ERROR eureka > key must be a string at line 1 column 2\n`
- `{"other_key": "value"}` produces the following exact line (the backticks around `repo` are literal):

  ```text
   ERROR eureka > missing field `repo` at line 1 column 22
  ```

  The line begins with one space and ends with one newline.
- the bytes `   \n  \t  \n` → ` ERROR eureka > EOF while parsing a value at line 3 column 0\n`
- `{\n  // This is a comment\n  "repo": "/some/path"\n}` → ` ERROR eureka > key must be a string at line 2 column 3\n`

An entirely zero-byte file is the special default configuration described in Spec 6, not a JSON syntax error. In view mode its empty repo ultimately produces the missing-file message in Spec 11.

## Spec 13

In capture mode, after reading the configuration, repeatedly ask for a summary; the prompt occurs even if the configured path is empty, nonexistent, or not a Git repository. Each attempt emits and flushes exactly:

```text
"\x1b[0m\x1b[1m\x1b[32m>> Idea summary\n"
"\x1b[0m> "
```

Read one input line and trim its leading and trailing whitespace. Empty or whitespace-only summaries are silently rejected and cause exactly one new prompt. A valid summary may be long (at least 1,000 characters) and may contain Unicode, quotes, backslashes, dollar signs, punctuation, and multiple interior spaces; all such content after outer trimming is preserved for the commit message.

After accepting the summary, attempt to open/validate the configured Git repository. If that succeeds, launch an editor with the configured repo's `README.md` path as its sole argument and wait for it to finish. Use nonempty `EDITOR` when set; when it is unset, use `vi`. The editor inherits standard streams, so its own output is visible. Changes made by the editor must remain in README and be used by the following Git operation.

## Spec 14

Every valid capture operates on branch `main`:

- Open the Git repository rooted at the configured path.
- If `main` exists, check it out before committing.
- If the repository has commits but no `main`, create `main` at the current HEAD and check it out.
- Stage the repository-root `README.md` and create a new commit whose subject/message is exactly the trimmed idea summary.
- Use the repository's configured `user.name` and `user.email` as both author and committer.
- A commit is created even when the editor exits successfully without changing README, so repeated captures with a no-op editor still create distinct commits.

README edits must be present in the created commit. Branch creation and checkout must be observable through ordinary Git commands after execution.

## Spec 15

For a capture that reaches Git commit/push, standard output has this ordered progress sequence after the summary prompt and any editor output:

```text
Adding and committing your new idea to main..
Added and committed!
Pushing your new idea..
```

Print the first line immediately before add/commit, the second only after a successful commit, and the third immediately before pushing. Push local `main` to remote `origin` as remote branch `main`. On successful push, append exactly:

```text
Pushed!
```

and ensure the remote's `refs/heads/main` points to the same commit as local `main`. The successful workflow exits 0.

With a first-attempt valid summary, a no-output editor, and a push that fails, the entire stdout is exactly:

```text
"\x1b[0m\x1b[1m\x1b[32m>> Idea summary\n"
"\x1b[0m> Adding and committing your new idea to main..\n"
"Added and committed!\n"
"Pushing your new idea..\n"
```

With two empty summaries before the valid summary, prepend two additional identical prompt fragments, yielding three prompts total and otherwise the same progress text.

## Spec 16

Push failures preserve the successful local commit, exit 0, log the error to standard error, and do not print `Pushed!`. If `origin` is absent, standard error is exactly:

```text
 ERROR eureka > remote 'origin' does not exist; class=Config (7); code=NotFound (-3)
```

If an `origin` exists but cannot be reached or rejects the push, print the same three pre-push progress lines and a nonempty ` ERROR eureka > ...` diagnostic, but no success line.

## Spec 17

Capture attempts to validate/open the configured Git repository after accepting a summary. A failure to open the configured path or recognize it as a Git repository occurs before invoking the editor or printing add/commit progress; the summary prompt has already been printed. Once the repository opens successfully, a later Git failure can occur after the capture reaches add/commit progress. Failures have these externally visible forms and exit 0:

- A nonexistent configured path logs a line containing `failed to resolve path '<path>'`, `No such file or directory`, `class=Os`, and `code=NotFound`; it does not print `Adding and committing`.
- An existing directory that is not a Git repository, or a repository whose metadata is corrupted (for example missing `.git/HEAD`), logs a line containing `ERROR eureka > could not find repository from '<path>'`, plus repository-class/not-found details.
- A newly initialized repository with a root `README.md`, an unborn `master` branch, and no commits reaches the add/commit attempt. With a first-attempt valid summary and a no-output editor, standard output is exactly:

  ```text
  "\x1b[0m\x1b[1m\x1b[32m>> Idea summary\n"
  "\x1b[0m> Adding and committing your new idea to main..\n"
  ```

  It does not print `Added and committed!` or `Pushing your new idea..`. Standard error is exactly ` ERROR eureka > reference 'refs/heads/master' not found; class=Reference (4); code=UnbornBranch (-9)\n` (the branch name reflects Git's unborn default HEAD in this scenario).
- An existing empty config uses path `''` and logs a line containing `ERROR eureka > failed to resolve path ''`, `class=Os`, and `code=NotFound`, without showing the first-time banner.

Errors must not cause a panic, traceback, interactive hang, or a nonzero top-level status.

## Spec 18

All normal textual data is UTF-8. The executable must preserve exact README content in view mode, preserve accepted configuration-path values through JSON serialization, and preserve accepted summary content as the Git commit message. It must handle rapid piped input and interactive terminal input, flush prompts before blocking, and complete noninteractive successful operations promptly (within five seconds under ordinary local test conditions).

Except for command-line parsing failures from Spec 1, every described operation that terminates does so with status 0, including setup, clear-on-missing, view/config errors, Git errors, and push errors. The continuous EOF reprompt in Spec 8 does not terminate on its own. Successful help, version, clear, view, setup, and capture operations terminate with status 0.
