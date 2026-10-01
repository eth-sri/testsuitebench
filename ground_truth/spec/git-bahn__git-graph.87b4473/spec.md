# Specification for `executable`

## Spec 1: Purpose and process contract

The required artifact is a single executable file named exactly `executable`.
It is a command-line program compatible with `git-graph` version 0.7.0: it
discovers a Git repository, reads its commit and ref topology, and writes a
structured history graph either as terminal text or as SVG.

Unless a command below says otherwise:

- successful output is written to standard output and the exit status is 0;
- successful graph rendering writes nothing to standard error;
- application failures (repository discovery, invalid option values, invalid
  models, or invalid configuration) are written to standard error and exit 1;
- command-line grammar failures are written to standard error and exit 2;
- all text is UTF-8 and normal graph output ends with a newline;
- commit data must be read from the repository supplied at run time. Commit
  hashes, messages, authors, dates, branch names, tags, topology, and paths are
  not fixed data.

The program must comfortably process histories of at least 100 commits and
must preserve Unicode in commit metadata and in filesystem paths.

## Spec 2: Command-line interface

The root grammar is:

```text
Usage: executable [OPTIONS] [COMMAND]
```

It has the `model` and `help` commands and these root options:

| Option | Meaning |
| --- | --- |
| `-p, --path <path>` | Discover the repository from this path; default `.`. |
| `--skip-repo-owner-validation` | Disable Git repository-owner validation. |
| `-m, --model <model>` | Use a branching model for this invocation. |
| `-n, --max-count <n>` | Show no more than `n` commits. |
| `--color <color>` | Terminal color mode: `auto`, `always`, or `never`; default `auto`. |
| `--no-color` | Disable terminal color even if `--color always` is present. |
| `-w, --wrap [<width-or-mode> [<first-indent> [<following-indent>]]]` | Configure wrapping. |
| `-f, --format <format>` | Select a preset or custom commit format. |
| `-r, --reverse` | Render oldest first instead of newest first. |
| `-l, --local` | Exclude remote-tracking refs. |
| `--svg` | Produce SVG graph geometry instead of terminal text. |
| `-d, --debug` | Add diagnostic graph information and timing. |
| `-S, --sparse` | Draw merge connectors to target lanes rather than directly on merge commits. |
| `-s, --style <style>` | Select `normal`/`thin`, `round`, `bold`, `double`, or `ascii`; their first-character aliases are `n`/`t`, `r`, `b`, `d`, and `a`. |
| `-h, --help` | Print help. |
| `-V, --version` | Print the version. |

`--no-pager` is not a recognized option. It is handled as an unknown root
option, exits 2, and reports `unexpected argument '--no-pager'`; consequently
it is also absent from long help.

The options taking one value (`model`, `max-count`, `color`, `format`, `path`,
and `style`) consume exactly one argument. `wrap` consumes at most three.
Repeating `--model`, `--color`, or `--style` is a grammar error; the diagnostic
uses the form `the argument '--model <model>' cannot be used multiple times`
(with the corresponding option name). Negative-looking values such as `-1`
for `--max-count` or `--wrap` are parsed as unexpected options and exit 2.

Root options must precede a command. For example,
`--path REPO model --list` is valid, whereas
`model --path REPO` and `model --no-color` are grammar errors. `--list` is only
an option of `model`. A `--` separator makes following tokens positional:
at root an option-looking token is consequently treated as a command name; in
`model` it is treated as the model name.

Help and version take precedence over later tokens. Thus
`--help --unknown`, `--help model`, and `--version model` succeed and print the
root help or version, respectively.

## Spec 3: Help, version, and dispatch

`--version` and `-V` write exactly:

```text
git-graph 0.7.0
```

Both `-h` and `--help` succeed on stdout with empty stderr, but they are not
identical: `-h` is the short summary and `--help` is the long form. Both contain
the name `git-graph`, the description “Structured Git graphs for your branching
model”, the URL `https://github.com/mlange-42/git-graph`, an `EXAMPES:` section
(that spelling is intentional), and `Usage:`, `Commands:`, and `Options:`
sections. Both document every option and alias from section 2, list `model` and
`help`, and show `[auto|always|never]` and
`[normal/thin|round|bold|double|ascii]`. The long form expands the option
descriptions, gives wrapping examples, and documents the custom placeholders
including `%h`, `%H`, and `%s`.

`help` alone produces the same root help as the long help command.
`help model` produces exactly the same output as `model --help`. The model help
is the following, including its final newline:

```text
Prints or permanently sets the branching model for a repository.

Usage: executable model [OPTIONS] [model]

Arguments:
  [model]  The branching model to be used. Available presets are [simple|git-flow|none].
           When not given, prints the currently set model.

Options:
  -l, --list  List all available branching models.
  -h, --help  Print help
```

Unlike ordinary commands, the `help` command itself does not accept `--help`;
`help --help` is treated as an unrecognized subcommand.

An unknown flag or command exits 2 and uses clap-style diagnostics. For
example, `--invalid-flag` produces exactly:

```text
error: unexpected argument '--invalid-flag' found

Usage: executable [OPTIONS] [COMMAND]

For more information, try '--help'.
```

An unknown positional command says `unrecognized subcommand '<token>'`, shows
the root usage, and suggests `--help`. An unknown option following `model`
additionally gives the standard hint
`tip: to pass '<token>' as a value, use '-- <token>'`.

## Spec 4: Repository discovery and errors

Starting from `--path` (or `.`), resolve relative components and symlinks, then
search the path and its ancestors for a Git repository. If the starting path is
an ordinary file, repository discovery proceeds through its containing
directory and ancestors rather than rejecting the file. Accept:

- a working-tree root;
- any subdirectory inside a working tree;
- the working tree's `.git` directory itself;
- a bare repository containing commits;
- paths containing spaces or Unicode and long, deeply nested paths.

Do not search down into child directories. If nested repositories exist, an
explicit outer path selects the outer repository and an explicit inner path
selects the inner one.

A nonexistent path exits 1 with:

```text
ERROR: failed to resolve path '<path>': No such file or directory
       Navigate into a repository before running git-graph, or use option --path
```

An existing path from which no valid repository can be discovered (including
an ordinary file outside any repository or a corrupt `.git` directory) exits 1
with:

```text
ERROR: could not find repository at '<path>'
       Navigate into a repository before running git-graph, or use option --path
```

The displayed path is the argument as supplied; for the default it is `.`.
An empty repository exits 1, emits no stdout, and reports the unborn branch,
for example `reference 'refs/heads/master' not found` followed by a newline.

When `--skip-repo-owner-validation` is used, stdout begins with
`Warning: skip-repo-owner-validation is set! \n`, where `\n` denotes the
newline and there is one ASCII space between `!` and that newline. Then render
the graph normally.

## Spec 5: Commits, refs, ordering, and filtering

Read all commits reachable from local branch heads and tags, and, unless
`--local` is set, remote-tracking branch heads. A detached HEAD does not add
otherwise-unreferenced commits to the displayed history. If its commit is
already reachable through one of the included refs, it receives the detached
HEAD decoration described below. Stash-only commits must not be added to the
displayed history. A remote ref is shown with its full tracking name such as
`origin/feature`; `--local` removes those refs and any history reachable only
through them while retaining local branches.

Default order is reverse chronological/topological order: children appear
before parents and the newest linear commit is first. `--reverse` reverses the
display so roots/oldest commits come first and reverses connector direction as
well. `--max-count n` first limits the default newest-first history to its
first `n` commits; `--reverse` then reverses that retained subset. Thus, on a
three-commit linear history, `--reverse --max-count 1` still displays only the
newest `Third commit`, not the oldest commit. Zero is valid and produces
completely empty stdout in terminal mode; SVG mode has the zero-count document
specified in section 12. A value larger than the history simply displays the
entire history. A nonnumeric value is an application error such as:

```text
Option max-count must be a positive number, but got 'abc'
```

Branch and tag decorations use these forms:

- current attached branch: `(HEAD -> master)`;
- another local or remote branch: `(feature)` or `(origin/feature)`;
- several branch refs: one parenthesized, comma-and-space-separated group, with
  the current HEAD decoration first;
- tags: a separate square-bracket group after branch refs, sorted by name and
  separated by comma-space, for example `[release-1, v1.0, v1.0.0]`;
- detached HEAD: the ordinary branch remains `(master)` at its own tip and the
  checked-out commit is decorated `HEAD ->` without parentheses.

## Spec 6: Branching models and graph layout

The default model for rendering is `git-flow`, unless the repository has a
persisted model. `--model` temporarily chooses `simple`, `git-flow`, `none`, or
an available custom model without modifying repository configuration. Names
are case-sensitive and are not whitespace-trimmed.

A model determines which conceptual branch owns each commit, the left-to-right
lane order, and colors. Build the graph as follows:

1. Treat local/remote refs and tags as branch candidates. A merged branch may
   also be inferred from a two-parent merge even when no current ref names it.
2. Sort candidates by the model's persistence groups. In `git-flow`, the
   persistence order is `master|main|trunk`, `develop|dev`, `feature*`,
   `release*`, `hotfix*`, `bugfix*`, then unmatched names. Its lane order is
   `master|main|trunk`, `hotfix*|release*`, `develop|dev`, then unmatched names.
3. In persistence order, trace each head through its first-parent ancestry and
   claim commits until reaching a commit already assigned to another branch.
4. Remove unclaimed commits and assign nonoverlapping lane columns to the
   remaining branch ranges, respecting the model's lane-order groups.

`simple` keeps the principal `master`/`main`/`trunk` line persistent and left
of other branches. `none` applies no name-based persistence or ordering, so it
can produce a visibly different lane arrangement. For this representative
Git-flow history, `git-flow` and `simple` render as:

```text
 ○<┐    HASH (HEAD -> master) Release v1.0
 │ ○<┐  HASH (develop) Merge feature/new-thing into develop
 │ │ ●  HASH (feature/new-thing) Feature work
 │ ├─┘
 │ ●    HASH Develop work
 ├─┘
 ●      HASH Initial commit
```

whereas `none` renders the same topology as:

```text
   ┌>○  HASH (HEAD -> master) Release v1.0
 ┌>○ │  HASH (develop) Merge feature/new-thing into develop
 ● │ │  HASH (feature/new-thing) Feature work
 └─┤ │
   ● │  HASH Develop work
   ├─┘
   ●    HASH Initial commit
```

`HASH` in examples denotes the actual lower-case seven-hex commit abbreviation.

## Spec 7: Terminal graph rendering

The default `normal` style (also named `thin`) uses `●` for an ordinary commit,
`○` for a two-parent merge commit, thin box-drawing lines, and two spaces
between the graph region and commit text. Every physical line of multiline
commit text receives the current graph-lane prefix. Connector-only rows may be
inserted between commit rows and have two trailing separator spaces.

A single commit and a linear history therefore have these exact shapes:

```text
 ●  HASH (HEAD -> master) Single commit
```

```text
 ●  HASH (HEAD -> master) Third commit
 ●  HASH Second commit
 ●  HASH First commit
```

A non-fast-forward merge with main-line work has this normal form:

```text
 ○<┐  HASH (HEAD -> master) Merge feature
 ● │  HASH Main work
 │ ●  HASH (feature) Feature commit
 ├─┘
 ●    HASH Initial commit
```

In sparse mode the merge's branch connector moves to its own row:

```text
 ○    HASH (HEAD -> master) Merge feature
 ├<┐
 ● │  HASH Main work
 │ ●  HASH (feature) Feature commit
 ├─┘
 ●    HASH Initial commit
```

In reverse mode the same normal graph begins at the root and terminates at the
merge, reversing arrows and corners:

```text
   ●  HASH Initial commit
 ┌─┤
 ● │  HASH (feature) Feature commit
 │ ●  HASH Main work
 └>○  HASH (HEAD -> master) Merge feature
```

Other styles preserve topology and spacing. The aliases `n`, `t`, `r`, `b`,
`d`, and `a` select `normal`, `thin`, `round`, `bold`, `double`, and `ascii`,
respectively:

- `round` replaces applicable square corners with rounded `╭╮╰╯` characters;
- `bold` uses heavy box-drawing strokes;
- `double` uses double box-drawing strokes;
- `ascii` contains no Unicode graph characters and maps ordinary/merge commits
  to `*`/`o`, vertical and horizontal strokes to `|`/`-`, and corners to `.` or
  `'`. The merge above is:

```text
 o<.  HASH (HEAD -> master) Merge feature
 * |  HASH Main work
 | *  HASH (feature) Feature commit
 |-'
 *    HASH Initial commit
```

## Spec 8: Commit text formats

The default format is `oneline`. The presets are `oneline`, `short`, `medium`,
and `full`; their first letters `o`, `s`, `m`, and `f` are equivalent aliases.

`oneline` is:

```text
%h%d %s
```

Thus each commit row contains a 7-character lower-case hexadecimal hash,
decorations if any, and the subject. An empty subject is retained as an empty
field rather than causing the row to disappear.

`short` is the following Git-like block per commit:

```text
commit <40-hex-hash><decorations>
Merge: <7-hex-parent-1> <7-hex-parent-2>    # merge commits only
Author: <author name> <<author email>>

    <subject>

```

`medium` adds `Date:   <author date>` after `Author:` and prints the complete
message body after the indented subject, preserving paragraph blank lines.
`full` additionally adds
`Commit: <committer name> <<committer email>>` between Author and Date. These
formats use the full 40-hex commit ID on the `commit` line. Dates have the form
`Sun Jan  7 10:00:00 2024 +0000` (English abbreviated weekday/month,
space-padded day, 24-hour time, year, numeric zone). The author date is used in
the preset `Date:` line.

The graph prefix is repeated before every metadata, message, and blank line of
a preset. The four message spaces shown above are part of the formatted text,
in addition to the graph prefix.

## Spec 9: Custom commit formats

Any `--format` value other than a preset is a template. Expand this exact
placeholder subset:

| Placeholder | Expansion |
| --- | --- |
| `%n` | newline |
| `%H`, `%h` | full 40-hex and abbreviated 7-hex commit ID |
| `%P`, `%p` | space-separated full and 7-hex parent IDs, in parent order; empty for a root |
| `%d` | ref decorations, including their leading space when nonempty |
| `%s` | subject (first message line) |
| `%b` | body excluding the subject |
| `%B` | raw message including subject and body |
| `%an`, `%ae` | author name and email |
| `%ad`, `%as` | full and `YYYY-MM-DD` author date |
| `%ar` | relative author date |
| `%cn`, `%ce` | committer name and email |
| `%cd`, `%cs` | full and `YYYY-MM-DD` committer date |
| `%cr` | relative committer date |

Literal characters, including unknown percent sequences such as `%invalid`,
are preserved. Newlines originating from `%n` or message fields create graph-
prefixed continuation lines. Nonempty message lines retain their text and
order. In custom formats, empty lines contributed inside `%b` or `%B`, and an
empty trailing expansion line, are omitted; preset `medium` and `full` formats
do preserve the explicit paragraph-separator rows described in section 8.

The character immediately after `%` may conditionally modify any non-newline
placeholder:

- `+` inserts a newline immediately before a nonempty expansion;
- `-` removes all consecutive newlines immediately before an empty expansion;
- a space inserts one space immediately before a nonempty expansion.

For example, when `%b` is `body line`, `A%+b%s` contains `A\nbody line`,
`A%-b%s` contains `Abody line`, and `A% b%s` contains `A body line`.

## Spec 10: Wrapping

Wrapping is configured as `--wrap MODE [FIRST [FOLLOWING]]`, where MODE is
`auto`, `none`, or a nonnegative decimal width. The default is equivalent to
`auto 0 8`. `none` leaves each original formatted line intact. A numeric mode
greedily fills each line up to the requested width, preferring whitespace
boundaries and without discarding content. If the next whitespace-delimited
word does not fit, it starts the next line. An indivisible token longer than
the available width is split into consecutive width-sized pieces rather than
being allowed to exceed the width. For example, formatting the subject
`This is a long commit message that should be wrapped at the specified width`
with `--format %s --wrap 40 0 0` produces these two commit-text lines before
their graph prefixes are added:

```text
This is a long commit message that
should be wrapped at the specified width
```

Likewise, `--format %H --wrap 5 0 0` splits a 40-character ASCII hash across
eight five-character physical lines. `auto` derives the available width from
the terminal and behaves deterministically when output is captured. FIRST and
FOLLOWING are decimal indentation widths for the first and continuation lines.
Wrapping applies to commit text, while each resulting physical line still gets
the correct live graph prefix.

Invalid modes or indent values exit 1 with a message of the form:

```text
ERROR: Can't parse option --wrap '<complete wrap argument>' to integers.
```

More than three wrap values leaves the extra token to command parsing and is a
grammar error (for example, a trailing `9` is reported as an unrecognized
subcommand).

## Spec 11: Color and diagnostics

`--color always` emits ANSI SGR color sequences even when stdout is captured or
piped. `--color never` and `--no-color` emit none. `auto` emits color only for a
color-capable terminal. `--no-color` wins when combined with `--color always`.
Multiple `--color` occurrences are rejected rather than using last-one-wins.
Color changes only styling; removing escape sequences must leave the exact
graph structure and text.

`--debug` keeps ordinary graph output on stdout and writes branch diagnostics
and timing to stderr. Terminal diagnostics include branch column text such as
`(col N)`, range values containing `Some(...)`, elapsed values in `ms`, and a
final commit count ending in `commits)`. SVG debug behavior is specified below.

## Spec 12: SVG output

`--svg` writes only graph geometry to stdout—no terminal escapes and no output
file. It must be well-formed XML with exactly one `<svg>` root in namespace
`http://www.w3.org/2000/svg`. Serialize attributes and empty elements in the
following style:

```text
<svg height="45" viewBox="0 0 30 45" width="30" xmlns="http://www.w3.org/2000/svg">
<circle cx="15" cy="15" fill="blue" r="4" stroke="blue" stroke-width="1"/>
</svg>
```

Use a 15-unit grid. Lane zero is at x=15, lane one at x=30, and displayed
commit rows begin at y=15 and advance by 15. For `n` linear displayed commits,
height is `15 * (n + 2)`; consequently 1, 3, 4, and 20 commits have heights 45,
75, 90, and 330. Width and the `viewBox` width are `15 * (lane_count + 1)`.
The root's `width` and `height` exactly equal its `viewBox` dimensions.

Render one radius-4 `<circle>` per displayed commit. Ordinary circles have
fill equal to stroke; merge circles are hollow with `fill="white"`. Every
circle, line, and path uses `stroke-width="1"`, except debug range lines.
Same-lane ancestry uses `<line>` with complete `x1`, `y1`, `x2`, `y2`,
`stroke`, and `stroke-width` attributes. Lane changes use unfilled quadratic
paths whose `d` begins with `M` and contains `L` and two `Q` commands. For
example, an adjacent-lane connection is serialized as:

```text
<path d="M30,30 L30,30 Q30,37.5,22.5,37.5 Q15,37.5,15,45 L15,45" fill="none" stroke="turquoise" stroke-width="1"/>
```

For each displayed commit, serialize its outgoing connection element(s) before
its circle. A three-commit blue linear history is exactly:

```text
<svg height="75" viewBox="0 0 30 75" width="30" xmlns="http://www.w3.org/2000/svg">
<line stroke="blue" stroke-width="1" x1="15" x2="15" y1="15" y2="30"/>
<circle cx="15" cy="15" fill="blue" r="4" stroke="blue" stroke-width="1"/>
<line stroke="blue" stroke-width="1" x1="15" x2="15" y1="30" y2="45"/>
<circle cx="15" cy="30" fill="blue" r="4" stroke="blue" stroke-width="1"/>
<circle cx="15" cy="45" fill="blue" r="4" stroke="blue" stroke-width="1"/>
</svg>
```

A six-commit history consisting of a three-commit principal line, one feature
commit, one later principal commit, and a merge commit is serialized as below.
This example also fixes the bend coordinates, parent-edge order, and hollow
merge-circle behavior:

```text
<svg height="120" viewBox="0 0 45 120" width="45" xmlns="http://www.w3.org/2000/svg">
<line stroke="blue" stroke-width="1" x1="15" x2="15" y1="15" y2="30"/>
<path d="M15,15 L15,15 Q15,22.5,22.5,22.5 Q30,22.5,30,30 L30,45" fill="none" stroke="turquoise" stroke-width="1"/>
<circle cx="15" cy="15" fill="white" r="4" stroke="blue" stroke-width="1"/>
<line stroke="blue" stroke-width="1" x1="15" x2="15" y1="30" y2="60"/>
<circle cx="15" cy="30" fill="blue" r="4" stroke="blue" stroke-width="1"/>
<path d="M30,45 L30,45 Q30,52.5,22.5,52.5 Q15,52.5,15,60 L15,60" fill="none" stroke="turquoise" stroke-width="1"/>
<circle cx="30" cy="45" fill="turquoise" r="4" stroke="turquoise" stroke-width="1"/>
<line stroke="blue" stroke-width="1" x1="15" x2="15" y1="60" y2="75"/>
<circle cx="15" cy="60" fill="blue" r="4" stroke="blue" stroke-width="1"/>
<line stroke="blue" stroke-width="1" x1="15" x2="15" y1="75" y2="90"/>
<circle cx="15" cy="75" fill="blue" r="4" stroke="blue" stroke-width="1"/>
<circle cx="15" cy="90" fill="blue" r="4" stroke="blue" stroke-width="1"/>
</svg>
```

The Git-flow principal branch color is `blue` and its feature-branch color is
`turquoise`. The simple model uses `blue` for the principal branch and `purple`
for feature/other branches. Other independent Git-flow branch lanes may use
`orange`, then `gray`, as model matching requires. SVG color attributes are
present regardless of the terminal `--color` setting.

`--max-count`, `--local`, and `--model` remain applicable in SVG mode.
`--reverse` and `--sparse` are accepted in SVG mode but are ignored: for the
same repository and other options, each produces byte-for-byte the same SVG as
omitting it. Different terminal character styles do not invalidate SVG output.
Limiting commits reduces circles and dimensions proportionally. At a limit of
zero, SVG mode writes this empty document rather than empty stdout:

```text
<svg height="30" viewBox="0 0 30 30" width="30" xmlns="http://www.w3.org/2000/svg"/>
```

With `--debug`, prepend one cyan range line per assigned branch to the SVG
elements. Such lines have `stroke="cyan"`, `stroke-width="5"`, fixed lane x
coordinates, and span that branch's first through last commit y coordinates.
The SVG itself remains parseable on stdout; textual timing remains on stderr.

## Spec 13: Model command and configuration

`model --list` and `model -l` do not require a repository. They ensure the
three built-in definition files `simple.toml`, `none.toml`, and
`git-flow.toml` exist in the model directory and print exactly these names,
one per line, in this order:

```text
git-flow
none
simple
```

On Linux the model directory is
`$XDG_CONFIG_HOME/git-graph/models` when `XDG_CONFIG_HOME` is set, otherwise
`$HOME/.config/git-graph/models`. These environment variables must be honored
per invocation; creating a clean config home must not prevent listing models.
Additional valid TOML model files may supply custom model names and model
rules, using the persistence/order and terminal/SVG color concepts described
above.

Inside a repository, `model` with no argument prints the persisted name with
no trailing newline. If the repository has no model configuration, it prints
exactly `No branching model set`, also without a newline. This query does not
confuse the rendering default (`git-flow`) with a persisted selection.

`model <name>` validates that the named model exists, then replaces the
repository configuration with exactly:

```toml
model = "<name>"
```

including a final newline. For a normal repository the file is
`.git/git-graph.toml`; for a bare repository it is `git-graph.toml` at the bare
root. The file must not be world-writable. Success exits 0, writes no
stdout, and writes `Branching model set to '<name>'` to stderr with no trailing
newline. Changes persist across later program and Git invocations.

Unknown extra keys in the repository TOML are ignored. Malformed TOML exits 1
with a descriptive standard-error diagnostic containing `TOML parse error`
and its line location. A configured model that is not available also exits 1
and reports both:

```text
ERROR: No branching model named '<name>' found in <model-directory>
       Available models are: <available names>
```

An invalid model supplied to the command is handled the same way and must not
write repository configuration. Running `model` or `model <name>` outside a
repository uses the repository-discovery error from section 4.
