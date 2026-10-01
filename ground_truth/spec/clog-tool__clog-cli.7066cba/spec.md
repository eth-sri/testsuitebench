# Clarified executable specification

## Spec 1

The required artifact is a directly runnable program named exactly `executable`. It is a single-command, option-driven command-line program; it has no positional operands and no subcommands. It models the legacy `clog` command and generates a minimal changelog header from the current invocation context. Unless a rule below specifies an error, successful generation exits with status 0.

All text is UTF-8. Normal generated output and the completion notice go to standard output. Argument-parser diagnostics and runtime failures go to standard error. A fatal runtime failure must leave standard output empty.

## Spec 2

`--help` and `-h` are help actions. They exit 0, write nothing to standard error, and print the following text to standard output, including the final newline. The four spaces following `<STR>` on the otherwise-empty subtitle-description line are significant.

```text
a conventional changelog for the rest of us

Usage: executable [OPTIONS]

Options:
  -r, --repository <URL>  Repository used for generating commit and issue links
                          (without the .git, e.g.
                          https://github.com/thoughtram/clog)
  -f, --from <COMMIT>     e.g. 12a8546
  -T, --format <STR>      The output format, defaults to markdown [default:
                          markdown] [possible values: markdown, json]
  -M, --major             Increment major version by one (Sets minor and patch
                          to 0)
  -g, --git-dir <PATH>    Local .git directory (defaults to "$(pwd)/.git")
  -w, --work-tree <PATH>  Local working tree of the git project (defaults to
                          "$(pwd)")
  -m, --minor             Increment minor version by one (Sets patch to 0)
  -p, --patch             Increment patch version by one
  -s, --subtitle <STR>    
  -t, --to <COMMIT>       e.g. 8057684 [default: HEAD]
  -o, --outfile <PATH>    Where to write the changelog (Defaults to stdout when
                          omitted)
  -c, --config <COMMIT>   The Clog Configuration TOML file to use [default:
                          .clog.toml]
  -i, --infile <PATH>     A changelog to append to, but *NOT* write to (Useful
                          in conjunction with --outfile)
      --setversion <VER>  e.g. 1.0.1
  -F, --from-latest-tag   use latest tag as start (instead of --from)
  -l, --link-style <STR>  The style of repository link to generate [default:
                          github] [possible values: github, gitlab, stash, cgit]
  -C, --changelog <PATH>  A previous changelog to prepend new changes to (this
                          is like using the same file for both --infile and
                          --outfile and should not be used in conjunction with
                          either)
  -h, --help              Print help
  -V, --version           Print version


If your .git directory is a child of your project directory (most common, such
as /myproject/.git) AND not in the current working directory (i.e you need to
use --work-tree or --git-dir) you only need to specify either the --work-tree
(i.e. /myproject) OR --git-dir (i.e. /myproject/.git), you don't need to use
both.

If using the --config to specify a clog configuration TOML file NOT in the
current working directory (meaning you need to use --work-tree or --git-dir) AND
the TOML file is inside your project directory (i.e. /myproject/.clog.toml) you
do not need to use --work-tree or --git-dir.
```

The help contains an `Options:` section and deliberately contains no `Commands:` or `Subcommands:` section.

## Spec 3

`--version` and `-V` exit 0, write nothing to standard error, and print exactly:

```text
clog 0.10.0
```

The displayed line has one terminating newline.

## Spec 4

The executable recognizes these scalar options and aliases:

| Meaning | Long option | Short option | Value |
|---|---|---|---|
| repository URL | `--repository` | `-r` | string |
| starting revision | `--from` | `-f` | string |
| output format | `--format` | `-T` | `markdown` or `json` |
| Git metadata directory | `--git-dir` | `-g` | path |
| Git working tree | `--work-tree` | `-w` | path |
| subtitle | `--subtitle` | `-s` | string |
| ending revision | `--to` | `-t` | string |
| output file | `--outfile` | `-o` | path |
| configuration file | `--config` | `-c` | path, despite the help metavariable `<COMMIT>` |
| input changelog | `--infile` | `-i` | path |
| explicit version | `--setversion` | none | string |
| link style | `--link-style` | `-l` | `github`, `gitlab`, `stash`, or `cgit` |
| in-place changelog | `--changelog` | `-C` | path |

It also recognizes the boolean switches `--major`/`-M`, `--minor`/`-m`, `--patch`/`-p`, and `--from-latest-tag`/`-F`.

Long scalar options accept either `--name value` or `--name=value`. Short scalar options accept `-X value`, `-X=value`, and attached values such as `-Tjson`. Boolean short options may be clustered, such as `-Mp`. Options may otherwise occur in any order. The defaults are markdown output, GitHub link style, ending revision `HEAD`, configuration path `.clog.toml`, and no explicit version or subtitle.

## Spec 5

Argument parsing follows clap-style validation. An unknown long option, unknown short option, misspelling, bare word, extra positional argument, or any token after `--` is rejected with exit status 2. The diagnostic goes to standard error, identifies an `unexpected argument`, contains a `Usage:` line, and ends with `For more information, try '--help'.`; standard output is empty. Because there are no subcommands, words such as `add`, `remove`, `init`, `list`, `show`, `help`, `version`, `config`, `update`, `delete`, `create`, `get`, and `set` are ordinary unexpected positional arguments.

An option that needs a value but has none also exits 2. Its diagnostic must contain both `a value is required` and `but none was supplied` (the shorter substring `value is required` therefore also appears) and name the offending option. A separate value beginning with `-` is treated as another option rather than as the scalar value, so, for example, `--subtitle -test-value` is an argument error. A scalar option cannot be repeated; in particular, repeating `--repository` exits 2 and says it `cannot be used multiple times`.

## Spec 6

Format and link-style values are lowercase and case-sensitive. Any invalid format exits 2 and leaves standard output empty. When clap does not find a similar allowed value, it uses this standard-error shape, substituting the supplied value for `VALUE`:

```text
error: invalid value 'VALUE' for '--format <STR>'
  [possible values: markdown, json]

For more information, try '--help'.
```

This is the exact result for `JSON`, `xml`, `pdf`, `html`, and `anything`. The case-only value `Markdown` is also invalid, but clap recognizes its similarity to `markdown` and inserts a tip and a following blank line. Its exact standard error is:

```text
error: invalid value 'Markdown' for '--format <STR>'
  [possible values: markdown, json]

  tip: a similar value exists: 'markdown'

For more information, try '--help'.
```

Any invalid link style likewise exits 2 with empty standard output. With no similar allowed value, it uses:

```text
error: invalid value 'VALUE' for '--link-style <STR>'
  [possible values: github, gitlab, stash, cgit]

For more information, try '--help'.
```

That is the exact result for `bitbucket` and `unknown`. For the case-only invalid value `GitHub`, the exact standard error instead includes the similarity tip:

```text
error: invalid value 'GitHub' for '--link-style <STR>'
  [possible values: github, gitlab, stash, cgit]

  tip: a similar value exists: 'github'

For more information, try '--help'.
```

Thus values such as `JSON`, `Markdown`, `xml`, `pdf`, `html`, `bitbucket`, and arbitrary names are invalid. Other near matches follow the same clap behavior: a recognized similar allowed value adds the two-space-indented `tip:` paragraph between the possible-values paragraph and the final help sentence.

## Spec 7

`--from` and `--from-latest-tag` are mutually exclusive. `--changelog` is mutually exclusive with each of `--infile` and `--outfile`; `--infile` and `--outfile` may be used together. Conflicts exit 2, do not perform generation or file writes, and use this clap-style diagnostic:

```text
error: the argument 'FIRST' cannot be used with 'SECOND'

Usage: executable FIRST

For more information, try '--help'.
```

`FIRST` is the option encountered first, including its metavariable (for example `--from <COMMIT>` or `--changelog <PATH>`), and `SECOND` is the conflicting later option. For example, `--from abc123 --from-latest-tag` reports the first as `--from <COMMIT>`, while `--infile a --changelog b` reports the first as `--infile <PATH>`.

Help is an immediate successful action only when encountered before an invalid token: `--help --bad-option` prints help and succeeds. An invalid positional token followed by `--help` still fails on the positional token. A `--help` token after `--` is positional and is rejected.

## Spec 8

Normal generation obtains settings from a TOML configuration. With no explicit `--config`, it selects `.clog.toml` relative to the process's current working directory. The selected configuration must exist whether its path is implicit or explicit; a missing selected file is the fatal I/O error in Spec 20. In particular, a repository URL and a usable initialized Git repository do not substitute for the missing implicit `.clog.toml`. This remains a fatal I/O error for an empty repository or a one-commit repository, and when matching `--work-tree` and `--git-dir` paths explicitly identify the current repository. A valid configuration contains a `[clog]` table. An explicitly supplied empty file, malformed TOML, an unclosed string, a missing table syntax element, or an incompatible field type is a TOML runtime error.

The recognized `[clog]` keys are `repository`, `subtitle`, `link-style`, `output-format`, `from-latest-tag`, `changelog`, `outfile`, and `infile`. String fields must be strings and `from-latest-tag` must be Boolean. Standard TOML quoted and multiline strings are accepted. Preserve the legacy setting bug: configuration values for `subtitle` and `output-format` are parsed but ignored. Without the corresponding command-line options, even `subtitle = "From config"` plus `output-format = "json"` produces the default markdown header with no subtitle; a multiline configured subtitle such as `Line one` followed by `Line two` is likewise absent from the output. A `[sections]` table may be absent, empty, or contain arbitrary quoted or unquoted display-name keys whose values are arrays of string aliases. Many entries and aliases must be accepted.

A valid config may provide enough context to generate a header even when the working directory is not a Git repository. Conversely, a missing implicit or explicit selected config fails cleanly rather than printing help, regardless of otherwise usable repository context. Command-line `--format` and `--subtitle` values take effect even though their configuration keys do not; `--repository` overrides a configured repository value.

## Spec 9

The executable may invoke the harness-provided `git` command to examine repository metadata. With neither location flag it uses the current directory and its `.git`. With only `--work-tree PATH`, it uses that tree and infers its Git metadata; with only `--git-dir PATH`, it uses that metadata directory and infers the associated tree. Either one works from a different current directory when paired with an explicit valid config. Relative paths resolve from the process current directory.

Supplying both `--work-tree` and `--git-dir` is accepted by the parser. It succeeds when invoked from the designated work tree and a usable `.clog.toml` is available there, including repositories made with a separate Git directory. If that implicit `.clog.toml` is absent, it instead produces the fatal I/O error even though both paths identify a usable repository and `--repository` is supplied. Preserve the legacy context quirk: when both flags are used from an unrelated current directory, initialization fails with the fatal I/O error even if an absolute `--config` is also supplied.

Do not reject a nonexistent path merely because it is supplied to one Git-location option. Specifically, from a nonrepository directory with an explicit valid configuration, each of `--work-tree does-not-exist` and `--git-dir does-not-exist` succeeds and generates the ordinary header. Relative paths still resolve from the process current directory when they are used.

## Spec 10

`--from COMMIT` selects an exclusive starting revision and `--to COMMIT` selects the ending revision; the latter defaults to `HEAD`. Full hashes, short hashes, symbolic names such as `HEAD`, and revision expressions are accepted as strings. `--from-latest-tag` asks Git for the latest reachable tag and uses it as the starting point. A repository with no tags still succeeds for `--from-latest-tag` and generates the ordinary empty-version header.

Commit-range lookup is deliberately forgiving: an unresolved `--from` or `--to` reference does not become a command-line or fatal error; it produces the same minimal header-only changelog and completion notice. Valid ranges, including ranges with no commits, also succeed.

## Spec 11

Once a usable configuration file has been selected, repository history must not make the executable crash or reject an otherwise valid invocation. In that configured context it must tolerate repositories with no commits, one commit, many commits or tags, separate Git metadata when otherwise configured, binary files, and conventional as well as non-conventional commit messages. This tolerance does not bypass configuration loading: a valid empty or one-commit repository with no implicit `.clog.toml` fails with the fatal I/O error before history can be processed. Messages may contain Unicode, punctuation, Markdown syntax, long subjects or bodies, multiple lines and footers, and conventional forms such as `type: text`, `type(scope): text`, an empty scope, or `!`/`BREAKING CHANGE` markers.

The observable legacy generation result does not render commit entries or named sections: regardless of which of those messages are in the selected range, the generated body is header-only and its JSON-like `sections` field is `null`. Unrecognized or oddly cased types are silently tolerated as well. Configuration section aliases are parsed but do not change this header-only result.

## Spec 12

Without `--setversion` or a successful increment operation, the output version is absent: markdown uses an empty anchor and heading version, and JSON-like output uses `None`. `--setversion VALUE` bypasses all version discovery and increment logic and preserves VALUE verbatim. It does not validate semantic-version syntax. Ordinary numeric versions, a single component such as `1`, partial versions, `v` prefixes, prerelease/build suffixes, arbitrary labels, punctuation, Unicode, surrounding whitespace, leading zeroes, and very long strings are therefore usable when supplied as one argument. The verbatim value appears in the anchor and heading, or in `Some("VALUE")` in JSON-like output.

If `--setversion` is combined with any of `--major`, `--minor`, or `--patch`, the explicit value wins and generation succeeds; the increment switches are ignored.

## Spec 13

Preserve the legacy version-increment failure. If at least one of `--major`, `--minor`, or `--patch` is present and `--setversion` is absent, the program attempts to parse Git's described version without trimming its trailing newline. It consequently fails in tested repositories, whether there is no tag, a normal `X.Y.Z`/`vX.Y.Z` tag, several tags, a prerelease/build tag, an extended `git describe` value, or any malformed tag. Multiple increment flags are accepted syntactically but reach the same failure.

This is a runtime failure (exit 1), not an argument error, and its exact standard error is:

```text
\x1b[1;31merror:\x1b[0m Failed to parse version into valid SemVer. Ensure the version is in the X.Y.Z format.
```

The line ends in one newline and standard output is empty. In this document `\x1b` denotes one literal ESC byte; the actual output contains that byte followed by `[1;31m` or `[0m`, so the `error:` prefix remains bold red even when output is captured.

## Spec 14

Markdown is the default output format. Let `V` be the explicit version or the empty string, `S` be the command-line `--subtitle` value or the empty string, and `D` be the local calendar date at execution formatted `YYYY-MM-DD`. A configured `subtitle` does not supply `S`, as specified in Spec 8. The generated markdown fragment is exactly:

```text
<a name="V"></a>
## V S (D)

```

`V` and `S` in that template mean direct textual substitution, with no escaping or trimming. Consequently there are two spaces between a nonempty version and `(D)` when there is no subtitle, two spaces after `##` when only a subtitle is present, and three spaces between `##` and `(D)` when both are absent. For an illustrative date of `2030-01-02`, examples of the first two lines are `<a name="1.2.3"></a>` followed by `## 1.2.3  (2030-01-02)`, and `<a name=""></a>` followed by `##  Release Candidate (2030-01-02)`.

## Spec 15

`--format json` selects a compact, one-line legacy debug representation. It is intentionally not valid JSON. With absent version and subtitle the fragment is exactly:

```text
{"header":{"version":None,"patch_version":false,"subtitle":null,"date":"D"},"sections":null}
```

With explicit version `V`, `version` is `Some("V")`. With command-line subtitle `S`, `subtitle` is the raw, unquoted subtitle text rather than a JSON string; otherwise it is `null`. A configured `subtitle` is ignored and therefore leaves this field `null`. For example:

```text
{"header":{"version":Some("1.0.1"),"patch_version":false,"subtitle":Bug Fix Release,"date":"2030-01-02"},"sections":null}
```

There are no spaces outside raw inserted values, `patch_version` is always lowercase `false` on successful tested paths, and `sections` is always `null`. No markdown anchor or heading appears in this format.

## Spec 16

After every successful generation, the executable prints this completion notice to standard output:

```text
changelog written. (took N ms)
```

`N` is a nonnegative decimal integer measuring elapsed milliseconds. If there is no output file, the generated fragment is first written to standard output and the notice follows immediately. Thus markdown's blank line precedes the notice, whereas the compact JSON-like closing `}` is immediately followed by `changelog written...` with no intervening newline. If output is directed to a file, standard output contains only the notice; the changelog data is not duplicated there. Successful generation writes nothing to standard error.

## Spec 17

`--outfile PATH` directs the generated changelog to PATH. It creates a missing file but does not create missing parent directories. Relative paths are relative to the process current directory; absolute, hidden, deeply nested (when parents exist), Unicode, space-containing, and other ordinary filesystem paths are supported. If the file already exists, the new release fragment is prepended and the old bytes are retained.

The file contains the generated fragment, then three additional newline bytes, then any retained old content. Therefore a new markdown output file with no old content has five newline bytes after its heading line (the fragment's two plus the separator's three). A JSON-like output file contains the compact object followed by the same three-newline separator. The completion notice is never stored in the output file.

Failure to create or write the file, including a nonexistent parent or a read-only destination, is the fatal I/O error in Spec 20.

## Spec 18

`--infile PATH` reads existing changelog bytes and places them after the newly generated fragment plus the three-newline separator. With no `--outfile`, the combined data and then the completion notice go to standard output. With `--outfile`, the combined data goes to the output file and the input file remains unchanged. A missing infile is silently treated as empty and is not created; an empty infile is valid.

Existing content is preserved byte-for-byte, including UTF-8 text, Markdown structure, large files, and CRLF line endings. Repeated output or in-place updates therefore order newly generated versions newest first.

`--changelog PATH` is the in-place shorthand that uses PATH as both infile and outfile: it reads the existing bytes, prepends the new fragment and separator, writes the result back to the same file, and leaves only the completion notice on standard output. Its parser conflicts are those in Spec 7.

## Spec 19

`--repository` accepts its argument as an opaque string; normal HTTPS/SSH-style URLs, punctuation, and very long values are not rejected or normalized. `--link-style` accepts exactly the four values in Spec 6, with `github` as default. The repository and link style would control commit/issue links, but because the tested legacy output is header-only they cause no visible change to the generated header. All four valid styles must nevertheless be accepted both from the CLI and from TOML, and must compose with formats, subtitles, versions, ranges, and file output.

## Spec 20

All non-parser operational errors are fatal: they exit 1, write no standard output, and put exactly one newline-terminated diagnostic on standard error. The prefix is always the literal ANSI-colored `\x1b[1;31merror:\x1b[0m ` even when stderr is not a terminal.

Malformed, empty, structurally invalid, or type-invalid configuration uses:

```text
\x1b[1;31merror:\x1b[0m Failed to parse TOML configuration file
```

A missing selected config, whether implicit or explicitly requested, an unusable combination of both Git-location flags as described in Spec 9, or a failed output-file operation uses the intentionally generic legacy message. A nonexistent path supplied to just one Git-location flag with an explicit valid config is not an error, as specified in Spec 9:

```text
\x1b[1;31merror:\x1b[0m fatal I/O error with output file
```

These runtime errors are distinct from clap argument errors, which exit 2 and are not ANSI-colored. The executable must terminate promptly and gracefully on all described inputs rather than panic, hang, or expose underlying parser/Git/filesystem exception details.
