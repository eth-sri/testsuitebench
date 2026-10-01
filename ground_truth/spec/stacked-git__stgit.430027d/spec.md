# Clarified executable specification

This document is the complete normative specification for the required artifact. The artifact is one executable file named exactly `executable`. In command examples it is called `stg` only to describe the command line and its displayed program name. A normal Git command-line program is provided by the harness and may be invoked by the executable; no StGit program or library is provided.

## Spec 1

The executable implements a Stacked Git command-line client over an existing Git repository. A stack belongs to a local Git branch and consists, from bottom to top, of three ordered groups: applied patches, unapplied patches, and hidden patches. A visible patch is in exactly one of the first two groups. Each patch has a unique name, a parent, a Git tree, a commit message, author identity/date, and committer identity/date. An applied patch is represented in the branch's first-parent commit history; the top applied patch is `HEAD`. Unapplying and reapplying patches must update the Git index and worktree as well as the branch and stack metadata. Ordinary Git commands such as `git status`, `git show`, `git log`, `git rev-parse`, `git show-ref`, and `git config` must observe the corresponding changes.

Stack metadata must persist between invocations and must be stored in the repository, not beside the executable or in process memory. Initializing branch `B` creates an actual ref beneath `refs/stacks/B`, and the loose path `.git/refs/stacks` must exist. Implementations may use any additional metadata, provided observable Git and command behavior matches this document. Operations must also work from any subdirectory of a non-bare repository and with packed Git refs.

## Spec 2

The global syntax is `stg [OPTIONS] <command> [...]`. Recognized global options, only before the command, are `--version`, repeatable `-C <path>`, `--color <when>`, `-h`, and `--help`. Both `-C=<path>` and `--color=<when>` are also accepted; in the short-option equals form the `=` is syntax and is not part of the path. Global options placed after a command are parsed by that command and rejected if that command does not define them. `--` ends global option parsing; the next token is treated as the command even if it begins with `-`.

Each `-C` changes directory before processing the next one. An absolute path replaces the current directory; a relative path is resolved from the directory established by the preceding `-C`. Empty or missing values are argument errors, and failure to enter a path is an error. A missing global value exits 1 with empty stdout and does not include a `Usage:` block. The exact stderr for `stg -C` is:

```text
error: a value is required for '-C <path>' but none was supplied

For more information, try '--help'.
```

The exact stderr for `stg --color` is:

```text
error: a value is required for '--color <when>' but none was supplied
  [possible values: auto, always, ansi, never]

For more information, try '--help'.
```

In particular, when relative path `foo` does not exist, `stg -C=foo` exits 2 with empty stdout and this stderr line:

```text
error: cannot change to `foo`: No such file or directory (os error 2)
```

Paths and pathspecs used by a later command are interpreted from the final directory. The early global `--version` action takes precedence over all later tokens and does not attempt pending `-C` changes, so even `-C /missing --version` succeeds. Global `--help` is different: preceding `-C` options are performed first. Thus `stg -C /path/that/does/not/exist --help garbage` exits 2 with empty stdout and prints exactly this stderr line:

```text
error: cannot change to `/path/that/does/not/exist`: No such file or directory (os error 2)
```

Closing the stdout side of a version pipeline early is a fatal broken-pipe condition. Under `set -o pipefail`, `stg --version | head -n 1 >/dev/null` exits 101 and stderr includes `failed printing to stdout: Broken pipe (os error 32)`.

The literal zero-argument invocation prints the short main help/usage to stderr, leaves stdout empty, and exits 1. Supplying a non-action global option does not use that special case: if option parsing finishes without a command, this is a required-subcommand argument error. In particular, `stg --color=auto` exits 1 with empty stdout and begins stderr with `error: 'stg' requires a subcommand but one was not provided`, followed by the subcommand list, main `Usage:` block, and help hint. With `--help`, print long main help to stdout and succeed even if later tokens are invalid. With `-h`, print short main help to stdout and succeed. `help` with no argument prints main help; `help COMMAND` prints that command's long help. Deliberately, `help --help` treats `--help` as a command name and fails as an unrecognized subcommand. Every listed command other than `help` accepts `-h` and `--help`, prints command-specific help containing `Usage:`, and exits zero without requiring a repository.

Argument errors use clap-style stderr diagnostics: start with `error:` and include the invalid or missing token. Except for the missing global `-C` and `--color` values shown above, they then include a blank line, the applicable `Usage:` form, another blank line, and `For more information, try '--help'.`. Unknown commands say `unrecognized subcommand '<token>'`; when a similar command exists, add a `tip:` suggestion. In particular, `stg nonexistent_subcmd` is classified as similar to `next`: it exits 1 with empty stdout and places this line in stderr between the unrecognized-subcommand line and the `Usage:` block:

```text
  tip: a similar subcommand exists: 'next'
```

The same rule applies to the hyphenated token `nonexistent-command`: it exits 1 with empty stdout and suggests `next`. `stg invalid-command` exits 1 with empty stdout and instead suggests `id` using `tip: a similar subcommand exists: 'id'`.

Unknown options say `unexpected argument`. In particular, `stg --invalid-flag` exits 1 with empty stdout and begins stderr with `error: unexpected argument '--invalid-flag' found`. Enumerated options identify the invalid value and possible values. Missing values say a value is required. Success is exit 0. The top-level failures for no command, an unknown global option, and an unknown subcommand use exit 1. The repository-discovery and unborn-branch failures specified in Spec 6 use exit 2; other failures use the command-specific statuses stated in this document and are nonzero. Errors go to stderr and do not put ordinary result text on stdout unless progress was emitted before the failure.

## Spec 3

The exact short main help is the following UTF-8 text, including final newline:

```text
Maintain a stack of patches on top of a Git branch.

Usage: stg [OPTIONS] <command> [...]
       stg [OPTIONS] <-h|--help>
       stg --version

Patch inspection commands:
  diff   Show a diff
  files  Show files modified by a patch
  id     Print git hash of a StGit revision
  log    Display or optionally clear the stack changelog
  name   Print patch name of a StGit revision
  show   Show patch commits

Patch manipulation commands:
  edit     Edit a patch
  fold     Fold diff file into the current patch
  new      Create a new patch at top of the stack
  refresh  Incorporate worktree changes into current patch
  rename   Rename a patch
  spill    Spill changes from the topmost patch
  sync     Synchronize patches with a branch or a series

Stack inspection commands:
  email    Format and send patches as email
  export   Export patches to a directory
  next     Print the name of the next patch
  patches  Show patches that modify files
  prev     Print the name of the previous patch
  series   Display the patch series
  top      Print the name of the top patch

Stack manipulation commands:
  branch    Branch operations: switch, list, create, rename, delete, ...
  clean     Delete empty patches from the series
  commit    Finalize patches to the stack base
  delete    Delete patches
  float     Push patches to the top, even if applied
  goto      Go to patch by pushing or popping as necessary
  hide      Hide patches in the series
  import    Import patches to stack
  init      Initialize a StGit stack on a branch
  pick      Import a patch from another branch or a commit object
  pop       Pop (unapply) one or more applied patches
  pull      Pull changes from a remote repository
  push      Push (apply) one or more unapplied patches
  rebase    Move the stack base to another point in history
  redo      Undo the last undo operation
  repair    Repair stack after branch is modified with git commands
  reset     Reset the patch stack to an earlier state
  sink      Move patches deeper in the stack
  squash    Squash two or more patches into one
  uncommit  Convert regular Git commits into StGit patches
  undo      Undo the last command
  unhide    Unhide hidden patches

Administration commands:
  completion  Support for shell completions
  version     Print version information and exit

Aliases:
  add       Alias for shell command `git -C "$GIT_PREFIX" add`
  mv        Alias for shell command `git -C "$GIT_PREFIX" mv`
  resolved  Alias for shell command `git -C "$GIT_PREFIX" add`
  rm        Alias for shell command `git -C "$GIT_PREFIX" rm`
  status    Alias for shell command `git status -s`

Help:
  help  Print this message or the help of the given subcommand(s)

Options:
      --version       Print version information
  -C <path>           Run as if started in <path>
      --color <when>  When to colorize output: auto, always, ansi, never
  -h, --help          Print help (see more with '--help')
```

Long help is the same text through the `Help:` entry and replaces the final Options block with this exact text:

```text
Options:
      --version
          Print version information

  -C <path>
          Run as if stg was started in '<path>' instead of the current working
          directory. When multiple `-C` options are given, each subsequent non-absolute
          `-C <path>` is interpreted relative to the preceding `-C <path>`.
          
          This option affects arguments that expect path names or path specs in that
          their interpretations of the path names would be made relative to the working
          directory caused by the `-C` option.

      --color <when>
          Specify when to colorize the output.
          
          `auto` (the default) enables colored output only when outputting to a terminal
          or TTY. The `NO_COLOR` environment variable is respected.
          
          `always` and `never` unconditionlly enable/disable colored output,
          respectively.
          
          `ansi` forces color to be output using ANSI escape sequences, even in a
          Windows console.

  -h, --help
          Print help (see a summary with '-h')
```

At a 120-column terminal this text and the preceding command listing are not reflowed. Long help ends in one newline.

The exact long `stg diff --help` output is:

```text
Show the diff (default) or diffstat between the current working copy or a tree-ish
object and another tree-ish object (defaulting to HEAD). File names can also be given to
restrict the diff output. The tree-ish object has the format accepted by the 'stg id'
command.

Usage: stg diff [OPTIONS] [path]...

Arguments:
  [path]...
          Limit diff to files matching path(s)

Options:
  -r, --range <revspec>
          Show diff between specified revisions. Revisions ranges are specified as
          'rev1[..[rev2]]'. The revisions may be standard Git revision specifiers or
          patches.

  -s, --stat
          Show the stat instead of the diff

  -O, --diff-opt <option>
          Pass additional <option> to `git diff`.
          
          See the git-diff(1) man page. This option may be specified multiple times.

      --color <when>
          Specify when to colorize the output.
          
          `auto` (the default) enables colored output only when outputting to a terminal
          or TTY. The `NO_COLOR` environment variable is respected.
          
          `always` and `never` unconditionlly enable/disable colored output,
          respectively.
          
          `ansi` forces color to be output using ANSI escape sequences, even in a
          Windows console.

  -h, --help
          Print help (see a summary with '-h')
```

Help goes only to stdout.

## Spec 4

`--version` and `version` print the same long report. The global `--version` is an early action and ignores every later token, including a nominal command; the `version` subcommand rejects extra positional arguments. The report is:

```text
Stacked Git 2.5.5
Copyright (C) 2005-2025 StGit authors
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
SPDX-License-Identifier: GPL-2.0-only
git version <git-version>
```

`<git-version>` is the version number reported by the harness-provided `git --version`, without duplicating the words `git version`. `version -s` and `version --short` produce the single line `stg 2.5.5`. Long-option abbreviations are not accepted. In particular, `version --sho` exits 1 with empty stdout and exactly this stderr:

```text
error: unexpected argument '--sho' found

  tip: a similar argument exists: '--short'

Usage: stg version --short

For more information, try '--help'.
```

The exact `version --help` output is:

```text
Print version information and exit

Usage: stg version [OPTIONS]

Options:
  -s, --short
          Show abbreviated version information

      --color <when>
          Specify when to colorize the output.
          
          `auto` (the default) enables colored output only when outputting to a terminal
          or TTY. The `NO_COLOR` environment variable is respected.
          
          `always` and `never` unconditionlly enable/disable colored output,
          respectively.
          
          `ansi` forces color to be output using ANSI escape sequences, even in a
          Windows console.

  -h, --help
          Print help (see a summary with '-h')
```

All forms end with a newline and do not use a pager.

## Spec 5

Color values are `auto`, `always`, `ansi`, and `never`. `always` and `ansi` force ANSI SGR escape sequences into color-capable output such as `series`, even when stdout is captured. `never` emits none. `auto` emits color only on a terminal and emits none when the `NO_COLOR` environment variable is present. Explicit `always` takes priority over `NO_COLOR`. The global value is inherited by a command; a command-local `--color` where supported overrides it. `series` accepts both command-local spellings, `series --color <when>` and `series --color=<when>`; in particular, both `series --color always` and `series --color=always` succeed and force ANSI SGR output. Invalid values fail during argument parsing. Git configuration color values may supply defaults but explicit command-line values win.

## Spec 6

Repository discovery follows Git: walk upward from the effective working directory and support normal and bare repositories where the operation makes sense. Commands needing Git fail outside a repository with empty stdout and a useful stderr error. In particular, `series` outside a repository exits 2 and prints exactly `error: Could not find a git repository in '.' or in any of its parents` plus newline on stderr. Commands needing stack state fail on an uninitialized branch, except where explicitly stated. Stack initialization requires an existing, non-unborn local branch and commit. `init [-b|--branch <branch>]` initializes the named branch or current branch without changing its content, index, or worktree. The long option also accepts `--branch=<branch>`. An empty value, whether supplied as `--branch=` or as the next token, is an argument error; `init --branch=` exits 1 with empty stdout and starts stderr with exactly:

```text
error: invalid value '' for '--branch <branch>': invalid branch locator ``
```

The missing-value diagnostic uses the canonical long spelling even when the short option was entered: `init -b` exits 1 with empty stdout and starts stderr with `error: a value is required for '--branch <branch>' but none was supplied`. The branch selector is not repeatable. For example, `init --branch=main --branch=dev` exits 1 with empty stdout and starts stderr with `error: the argument '--branch <branch>' cannot be used multiple times`, followed by the `init` usage and help hint. On an unborn branch, initialization exits 2 with empty stdout and stderr ``error: branch `refs/heads/<name>` is unborn`` plus newline; for an unborn `master`, `<name>` is `master`. Repeating initialization exits 2 with empty stdout and stderr ``error: StGit stack already initialized for branch `<name>`\n``; for example, repeating `init` on `master` prints exactly ``error: StGit stack already initialized for branch `master`\n``. `init` accepts no positional argument. Stack inspection then succeeds with an empty series.

The base is the commit immediately below the bottom patch. Creating, rewriting, moving, applying, or unapplying patches must preserve their logical changes, messages, and authors unless an option explicitly changes them. Generated commits use configured/environment Git identity and dates. Text, Unicode, binary data, executable modes, symlinks, deletions, renames, unusual filenames, nested directories, and large files must survive stack operations.

## Spec 7

Patch names are UTF-8 strings unique across applied, unapplied, and hidden patches on a stack. They may begin with `-` only when supplied through `--name`; ordinary positional parsing requires `--` to disambiguate option-looking operands. Letters, digits, hyphens, and underscores are valid. Empty names, whitespace, `^`, `~`, `:`, `?`, `*`, `[`, backslash, slash, `..`, `.lock` suffixes, control characters, and names beginning or ending with a dot are invalid. Diagnostics identify the name and reason, for example `invalid patch name 'invalid..name': patch name may not contain '..'`. A name already in use fails without changing state.

Where a name is optional, derive it from the first line of the patch description by lowercasing, replacing runs of non-name characters with `-`, trimming separators, and choosing a unique usable result. Thus `new -m 'Hello World'` without an explicit name creates `hello-world`. Importing from a named file and picking a commit are the exceptions described in Spec 26.

Patch locators accepted by inspection and manipulation commands include a patch name; `@` for top; `~`/`@~` for one patch below top; `~N`, `@~N`, or `PATCH~N` for N positions below; `+` for the first unapplied patch; a zero-based integer for a stack position from the bottom; escaped negative forms such as `\-1` for an offset below top; `{base}` for the stack base; `PATCH^` for the patch's parent; and any valid Git committish where a revision rather than strictly a patch is allowed. `id` and `name` also parse `BRANCH:PATCH`, with the different inverse-name behavior in Spec 13. A range `A..B` is inclusive of both endpoint patches and all between them. `..B` starts at the bottom and `A..` ends at the top of the visible series. Reversed/empty, malformed, or unresolved ranges fail atomically. Except for the stricter `series` operand rule in Spec 12, multiple operands preserve series order and remove duplicates.

## Spec 8

Mutation commands report transaction progress on stdout. The canonical one-line forms are:

```text
> name (new)
+ name
> name
- name
- first..last
# name
# first..last
& name
old => new
! name
```

They respectively mean newly created top patch, applied non-top patch, resulting top patch, popped patch/range, deleted patch/range, modified patch, renamed patch, and hidden patch. Empty patches may be annotated ` (empty)` and conflict results ` (conflict)`. A multi-step transaction prints events in execution order. Inspection output is separate from progress output. Commands which make no state change normally print nothing. Info/warning messages use `info:`/`warning:` and stderr unless an external Git command convention requires stdout. Errors use `error:` and stderr.

All mutating commands are transactional: a precondition or parse error leaves branch, stack, index, and worktree unchanged. If a conflict is the intended result of applying a patch, keep conflict stages and conflict markers and stop at that patch; print the following line, whose command is delimited by backticks, and a short status such as `UU file.txt`:

```text
error: merge conflicts; resolve conflicts manually then refresh or undo the operation with `stg undo --hard`.
```

Other mid-operation failures roll back and may say `command aborted (all changes rolled back)`.

## Spec 9

`new [OPTIONS] [patch]` creates and applies one patch above the current top. It is empty when no capture mode and no paths are supplied. Its long help identifies the positional operand as `patchname` and contains these usage forms:

```text
Usage: stg new [OPTIONS] [patchname] [-- <path>...]
       stg new [OPTIONS] [--name <patchname>] [-- <path>...]
```

`-m/--message <text>` supplies its message; `-f/--file <file>` reads it (`-` means stdin); `--name <name>` permits an option-looking name. Without a message, run the editor selected by `GIT_EDITOR`, then `EDITOR`, then the Git default, on a file prefilled from the patch-description template. Template lookup order is nonempty `$XDG_CONFIG_HOME/stgit/templates/patchdescr.tmpl`, then `$HOME/.stgit/templates/patchdescr.tmpl`; an empty `XDG_CONFIG_HOME` is ignored. Template text becomes the message if the editor leaves it as content. An empty edited message fails; explicitly creating a named empty patch with a nonempty message succeeds.

`--refresh` captures tracked worktree changes and staged changes into the new patch as in `refresh`; `--index` restricts that capture to the index. Supplying path operands after `--` requests refresh-style capture of those paths even when `--refresh` is absent. None of these forms implicitly adds an untracked file. Even when explicitly named after `--`, an untracked file is ignored until it is added to the Git index: with untracked `u.txt`, `new --refresh -m U u -- u.txt` exits 0, prints exactly `> u (new)\n`, creates an empty patch, and leaves exactly `?? u.txt\n` in short status. This also applies to multiple named untracked files; later pop, push, squash, clean, commit, email, show, spill, and undo operations therefore treat patches made only from such files as empty and leave the files outside patch history.

With staged new files `f1.txt` and `f2.txt`, `new -m 'With paths' with-paths -- f1.txt` exits 0, prints exactly `> with-paths (new)\n`, captures `f1.txt`, and leaves exactly `A  f2.txt\n` in short status. `new --refresh` with staged-only changes captures them successfully; for patch `with-refresh` it exits 0 with empty stderr and prints exactly `> with-refresh (new)\n`. With a clean index/worktree it still creates an empty patch. Metadata options include `--author 'Name <mail>'`, `--authname`, `--authemail`, `--authdate`, `--committer-date-is-author-date`, `--sign`, `--ack`, `--review`, `--signoff`, and repeatable trailers. They affect the commit as described in Spec 32. On an eligible committed local branch that is not yet initialized, `new` initializes the stack and creates the patch in the same invocation. Duplicate names, too many positional names, or invalid names fail atomically. In particular, trying to create existing patch `duplicate` exits 2 with empty stdout and exactly ``error: patch `duplicate` already exists\n`` on stderr.

## Spec 10

`refresh [OPTIONS] [--] [path]...` incorporates selected capturable index/worktree changes into a patch, defaulting to top. `-p/--patch <patch>` selects a named patch instead of the top patch; it works for a lower applied patch and for an unapplied patch, including when no patches are currently applied. For the top patch, the new patch tree is the selected current tree plus the prior patch's unselected changes. Refreshing a lower applied patch temporarily pops patches above it, rewrites the target, and reapplies those patches so their content/order is retained. Refreshing an unapplied patch similarly rewrites it while restoring the original applied boundary. On success selected tracked or staged changes disappear from `git status`; unselected paths remain exactly staged or unstaged as before. The untracked-path exception is stated below.

By default, refresh accepts either worktree-only changes when the index is clean or staged-only changes when the worktree is clean. In the staged-only case it incorporates the staged changes and leaves the index clean. If both the index and worktree contain changes, it fails with:

```text
error: the index is dirty; consider using `--index` or `--force`
```

That failure exits 2 with empty stdout and the displayed line plus newline on stderr. A successful refresh that captures tree changes into an existing top patch exposes its internal temporary-patch transaction on stdout, in this order: `> refresh-temp (new)`, `- refresh-temp`, `# refresh-temp`, `& <patch>`, and `> <patch>`, each followed by newline. This exact five-event sequence is produced by plain staged-only refresh, a path-limited refresh that selects changes, `--index`, `--force`, and an `--update` refresh that actually rewrites the patch; stderr is empty. For example, when the patch is `test`, the last two lines are `& test\n> test\n`.

`--index` uses only staged changes and is incompatible with path limits and `--force`. `--force` permits both index and worktree changes. Untracked files are not captured unless first added to the index, even when named by a path limit. When top patch `p` is empty and the only worktree path is an untracked file left by an earlier path-limited `new`, plain `refresh` exits 0, leaves the file untracked, and prints exactly `> refresh-temp (new)\n- refresh-temp\n# refresh-temp\n> p\n`; there is no `& p` line because `p` is not rewritten. A path-limited refresh selecting one of two untracked files likewise leaves both reported as `??`.

`--update` considers only already tracked paths already present in the patch. If an `--update` invocation has a worktree change to a tracked repository path which is not present in the current empty patch, no patch rewrite occurs. For top patch `p1`, that successful case prints exactly `> refresh-temp (new)\n- refresh-temp\n# refresh-temp\n> p1\n`, with no `& p1` event, and leaves stderr empty. `--submodules` includes submodule changes and `--no-submodules` excludes them. `-m/--message`, author/date options, trailer/sign/ack/review options, `--edit`, `-a/--annotate <note>`, `--no-verify`, and diff options update metadata or selection as named. A clean refresh may succeed as a no-op. No usable target, a nonexistent target, unresolved conflicts, or incompatible flags fail.

If moving selected changes into a lower patch cannot reapply cleanly, preserve those changes in a newly created unapplied patch named `refresh-temp`, leave the affected original patches unapplied, and print `The new changes did not apply cleanly to <patch>. They were saved in refresh-temp.`.

## Spec 11

`edit [OPTIONS] [patch]` edits the named patch or the top applied patch. It supports the message sources, editor/template, author/date fields, trailers, sign/ack/review/signoff, tree selection (`--set-tree`), and diff/editor controls used by `new`/`refresh`. In particular, its command help lists `-d, --diff`; this option appends the patch's diff to the description during interactive editing, and an edited diff is applied to the patch's parent tree. It may edit an unapplied patch. If metadata changes on the applied top patch, rewrite the commit and print `& name` followed by `> name`; for example, editing `p` prints exactly `& p\n> p\n`. If no field changes, print nothing. Editing a lower applied patch preserves and reapplies patches above and reports the temporary transition. For example, with empty applied patches `my-second-patch` and `renamed-patch`, editing the former's message exits 0 with empty stderr and prints exactly `- renamed-patch\n& my-second-patch\n> renamed-patch (empty)\n`. With no applied patch and no explicit usable patch, fail `error: no patches applied`.

`rename [old-patch] <new-patch>` renames `old-patch`, defaulting to the current patch when only the new name is given. `--branch <branch>` selects another stack. Preserve applied/unapplied/hidden position, commit contents, and metadata. Print `old => new` and, when applicable, the resulting top marker. Reject missing patches, too many arguments, invalid/taken names, or renaming to the same name. Invalid new names are command-line value errors with exit 1: for example, `rename invalid..name` and `rename feature/test-123` exit 1 with empty stdout, identify the invalid value for `<new-patch>`, give the specific name reason, and include the rename usage/help hint. Renaming current patch `renamed-patch` to that same name is instead a runtime collision: it exits 2 with empty stdout and exactly ``error: patch `renamed-patch` already exists\n`` on stderr.

## Spec 12

`series [OPTIONS] [patch-or-range]...` lists selected patches in bottom-to-top order unless `--reverse` is used. Multiple explicit operands must extend one contiguous selection in series order, and a patch may not be used twice. On an all-applied `p1`, `p2`, `p3` stack, `series p3 p1 p3` exits 2 with empty stdout and exactly ``error: `p1` not contiguous with preceding range `p3`\n`` on stderr. Default selection is all visible patches. Prefix each line with `+ ` for applied non-top, `> ` for top applied, `- ` for unapplied, and `! ` for hidden. Hidden patches are omitted unless `-H/--hidden` or `-a/--all` is selected. `-A/--applied` and `-U/--unapplied` select those groups. `--noprefix` removes the two-character marker. On an empty initialized stack, output is empty and success. On an eligible committed branch that has not been initialized, `series` likewise succeeds with empty stdout and does not require prior initialization.

`-d/--description` appends ` # ` plus the first paragraph of the message, joining that paragraph's nonblank lines with single spaces. Thus message `First patch\nWith details` is displayed as `First patch With details`; text after the first blank line is omitted. `--author` appends the author name; together use ` # author # description`. `-i/--commit-id[=<length>]` places the full hash, or requested abbreviation, before the name. `-e/--empty` prepends `*` to the normal marker for empty patches. `--count` (also `-c`) prints only the decimal count and newline. `--short=N` shows up to N applied patches below top, the top itself, and up to N unapplied patches above it; for seven fully applied patches, `--short=2` therefore prints patches 5, 6, and 7. Bare `--short` uses N=5. `--offsets`, `--commit-message`, and `--showbranch` add the corresponding position/message/branch fields. Ranges and explicit patch operands restrict output. `--all` is mutually exclusive with `--applied`, `--unapplied`, `--hidden`, and both the bare and valued forms of `--short`; these combinations are argument errors. The individual group selectors may be combined with one another. Examples:

```text
+ patch1
> patch2
- patch3
```

and with description and author:

```text
+ patch1 # Test User # First patch
> patch2 # Test User # Second patch
```

## Spec 13

`top` prints only the top applied patch name and newline. `prev` prints only the applied patch immediately below top. `next` prints only the first unapplied patch. Each of these three commands accepts `-b/--branch <branch>` to inspect that branch's stack; for example, on branch `master` whose top patch is `patch1`, `top --branch master` prints `patch1`. `top`/`prev` with no applied patches fail `error: no patches applied`; `prev` with only one applied patch fails `error: not enough patches applied`; `next` with no unapplied patch fails `error: no unapplied patches`.

`id [revision]` prints the full 40-hex Git object ID plus newline, defaulting to `HEAD`. Patch locators resolve to patch commits; `{base}` resolves to the stack base; parent/offset syntax resolves as in Spec 7. `name [revision]` performs the inverse in the current stack and prints the patch name, or `{base}` for the base. `name --showbranch` prefixes or qualifies that current-stack result. A branch-qualified operand does not preserve the operand's branch/patch identity during this inverse lookup: while on `other`, if `main:main-patch` resolves to the commit that is the `other` stack base, `name main:main-patch --showbranch` prints exactly `other:{base}\n`. By contrast, `id main:main-patch` resolves the named `main` patch commit normally. An operand which does not resolve is diagnosed as a missing patch, not as an unknown revision: `name deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` exits 2 with empty stdout and exactly ``error: patch `deadbeefdeadbeefdeadbeefdeadbeefdeadbeef` does not exist\n`` on stderr.

## Spec 14

`show [OPTIONS] [revision-or-patch]...` is a Git-log-style display of commits, defaulting to the top patch when a stack has applied patches and otherwise to `HEAD`. It accepts Git committishes, individual patches, inclusive patch ranges, `--applied`, `--unapplied`, `--stat`, `--no-decorate`, `--reverse`, and repeatable diff options. Default format contains `commit <full-hash>`, `Author: Name <email>`, `Date:`, the indented full message, then the canonical Git patch when the commit is nonempty. `--stat` includes diffstat. Multiple inputs display all selected commits. Binary changes use Git's binary indication rather than corrupting data.

`--no-patch` is not a recognized `show` option. Both `show --no-patch p1` and `show --no-patch p1..p3` exit 1 with empty stdout, begin stderr with `error: unexpected argument '--no-patch' found`, suggest the similar `--patch` argument, and show the applicable `Usage:` forms.

`diff [OPTIONS] [path]...` without `--range` shows the difference from `HEAD` to index/worktree, respecting staged and unstaged state in the same manner as `git diff`. `-r/--range A[..B]` compares the trees of the resolved revisions; an omitted B means the working state. Patch names are accepted. `-s/--stat` prints diffstat instead of hunks. Repeatable `-O/--diff-opt <option>` passes Git diff options such as `--ignore-all-space`, `--unified=N`, or cached/stat controls. Paths limit output. The output must use canonical Git diff headers, modes, hashes, hunks, rename/delete/add notation, and ordering.

## Spec 15

`files [OPTIONS] [patch]` reports the change from a patch's parent tree to its tree, defaulting to top, or to `HEAD` when there is no top patch. Default output is one line per path in Git name-status form, such as `M file`, `A file`, `D file`. Rename detection is disabled in this mode: a pure rename from `file1.txt` to `file1_renamed.txt` prints exactly `D file1.txt\nA file1_renamed.txt\n`, rather than an `R100` record. `--bare` prints only paths. `--stat` prints Git diffstat plus its extended summary lines. For a patch that adds one line each to `base.txt` and new `file2.txt`, it prints exactly:

```text
 base.txt  | 1 +
 file2.txt | 1 +
 2 files changed, 2 insertions(+)
 create mode 100644 file2.txt
```

The same output is used when that patch is selected explicitly. `--bare` and `--stat` are mutually exclusive: combining them exits 1 with empty stdout, starts stderr with `error: the argument '--bare' cannot be used with '--stat'`, and includes the applicable usage/help hint. Diff options and multiple selected patches are supported where accepted. Paths sort as Git sorts them. A nonexistent patch exits 2 with empty stdout and stderr ``error: patch `<name>` does not exist\n``. If the selected commit is a root commit, it exits 2 with empty stdout and stderr ``error: commit `<full-id>` does not have a parent\n``.

`patches [OPTIONS] [path]...` lists, in series order, applied patches whose diffs touch any named path. With no explicit file, use changes in the working tree to find overlapping patches; if there are no usable paths/applied patches, fail. `--diff` lays out each result exactly as follows: a 50-hyphen line, the patch name, another 50-hyphen line, the full description, one empty line, a `---` line, and then the patch's canonical diff beginning immediately with `diff --git` on the next line. There is no empty line between `---` and `diff --git`, and consecutive patch blocks likewise have no extra separator or blank line beyond the next block's initial 50-hyphen line. Branch and diff-option forms select another stack or alter the diff.

The built-in `status` alias executes harness `git status -s` with all trailing arguments, preserving its exact output/exit status. Therefore staged/unstaged XY columns, `??`, `!!` under `--ignored`, rename arrows, pathspec filtering, conflicts, and `--porcelain` behave exactly as the provided Git. `add`, `resolved`, `mv`, and `rm` similarly execute Git `add`, `add`, `mv`, and `rm`, from the repository prefix and with all arguments.

## Spec 16

`push [OPTIONS] [patch-or-range]` applies unapplied patches in series order. With no target apply one; a target applies through that patch; `-n/--number N` applies N; `-a/--all` applies all. N=0 is a successful no-op; N larger than the remaining count clamps to all; negative N leaves that many patches unapplied (for example `-1` applies all but the last). An explicit inclusive range applies its members in stack order. Applying a patch changes `HEAD`, index, and worktree to that patch's tree and preserves local state only under options that explicitly allow it.

`--reverse` applies the selected sequence in reverse ordering, `--noapply` reorders/imports the selected patch at the applied boundary without applying its diff, `--merged` detects patches whose changes already exist upstream and treats them as merged, `--set-tree` uses the recorded tree, and conflict policy options control whether conflicts may remain. Applying an already-applied or nonexistent patch fails. Explicit patch and range operands are validated before checking whether the stack has any unapplied patches. Thus, on a stack whose ten patches `p0` through `p9` are all applied, `push p99999` exits 2 with empty stdout and this stderr:

```text
error: patch `p99999` does not exist, but is similar to `p9`
```

On the same stack, `push p0..p2` exits 2 with empty stdout and this stderr, diagnosing the first invalid range member:

```text
error: patch `p0` is already applied
```

Only when no explicit operand produces such an error does having no unapplied patches fail with `error: no unapplied patches`. On conflict use Spec 8 and leave the conflicting patch as the top applied patch with unresolved index entries.

## Spec 17

`pop [OPTIONS] [patch]...` unapplies patches. With no operand pop the top patch. Explicit patch or range operands unapply exactly the selected applied patches, including each named endpoint; patches above a selected patch are temporarily popped and then reapplied so unselected patches remain applied. Thus, with `patch1`, `patch2`, and `patch3` all applied, `pop patch2` exits 0 with empty stderr, prints exactly `- patch2..patch3\n> patch3\n`, and leaves series output exactly `+ patch1\n> patch3\n- patch2\n`: the named `patch2`, not `patch3`, becomes unapplied. Popping the current top `p3` prints `- p3` followed by `> p2` when `p2` remains. `-n/--number N` pops N patches from the top; `-a/--all` pops all. N=0 is a no-op; an oversized positive count pops all; negative N leaves that many patches applied. An explicit already-unapplied patch fails. With no applied patch fail `error: no patches applied`.

`--keep` keeps local worktree changes while moving the applied boundary when those changes do not overlap; `--spill` leaves the popped patch's changes in the index/worktree. Dirty or conflicting states otherwise follow Spec 31.

`goto [OPTIONS] <patch>` makes that patch top-applied by invoking the equivalent push-through or pop-to transition. Going to the current top leaves `HEAD` and stack state unchanged but still prints the top marker; for current top `p3`, it exits 0 and prints exactly `> p3\n`. `--keep` preserves compatible local worktree changes; merged/conflict policy flags follow push. A missing target fails; a dirty index/worktree fails unless the selected preservation option makes the transition safe.

## Spec 18

`delete [OPTIONS] [patch-or-range]...` removes selected patch records and commits while retaining all nonselected patches in their previous relative order. Applied patches may be deleted by transactionally popping/reapplying surrounding patches. `--top` selects top; `--unapplied` selects all unapplied; `--all` selects every visible patch; `--branch` allows another stack. At least one positional operand or selector is required. Plain `delete` exits 1 with empty stdout and reports that `<patch>...` was not provided, followed by the delete usage/help hint. `--top` is mutually exclusive with positional operands: `delete --top foo` exits 1 with empty stdout and starts stderr with `error: the argument '--top' cannot be used with '[patch]...'`. When no patch is applied, `delete --top` exits 2 with empty stdout and exactly `error: no patches applied\n` on stderr.

Without `--spill`, deleting a patch discards that patch's logical changes. With `--spill`, its changes are left staged/in the worktree and the patch disappears. Deletion reports the complete temporary pop/delete/reapply transaction. Deleting empty lower patch `first` beneath empty top patch `second` prints exactly `- first..second\n# first\n> second (empty)\n`. With three nonempty applied patches `p1`, `p2`, and `p3`, `delete p1 p3` prints exactly `- p1..p3\n# p1\n# p3\n> p2\n`, while `delete p1..p2` prints exactly `- p1..p3\n# p1..p2\n> p3\n`. Deleting all three applied patches exposes the pop before deletion: it exits 0 with empty stderr and prints exactly `- p1..p3\n# p1..p3\n`. Deletion is atomic if any operand is invalid or conflicts exist. As a specific empty-range exception to Spec 6, `delete ..` on an eligible committed but uninitialized branch is a successful no-op: it exits 0 with empty stdout and stderr, does not initialize the stack, and leaves `HEAD`, the index, and the worktree unchanged.

`spill [OPTIONS] [patch] [--] [path]...` removes selected changes from the top patch (or named applied patch) and leaves exactly those changes in the index/worktree, keeping the patch, possibly empty. Its long help explicitly says the changes `remain in the index and worktree`. Pathspecs, directories, and globs restrict changes. `--reset` puts spilled content only in the worktree rather than staged; `-a/--annotate <text>` records the operation annotation; `--committer-date-is-author-date` controls rewritten metadata. Reject no applied patch, dirty index, unresolved conflicts, and a mismatch between `HEAD` and stack top. Typical success prints `& patch` and `> patch`.

## Spec 19

`float [OPTIONS] <patch>...` moves selected visible patches, preserving their listed/series order and content, to the top of the series and applies them. It can move applied or unapplied patches and can read names from `-S/--series <file>`. `--noapply` performs the reorder without pushing the moved patches; `--keep` preserves compatible local changes; `--above <patch>` places the group immediately above a target. A patch already at the requested position may be a no-op. Missing operands are a usage error; nonexistent patches fail.

`sink [OPTIONS] [patch]...` moves selected applied patches deeper, defaulting to moving the current top to the bottom. `-t/--below <target>` places them immediately below an applied target, and `--to <target>` is an alias for `--below <target>`; `-T/--above <target>` places them immediately above it; the numeric/bottom target form places them at the bottom. `--nopush` leaves patches above the resulting applied boundary unapplied and `--keep` preserves compatible changes. Preserve relative order and logical diffs while rewriting dependent commits. With three nonempty, independently applicable patches `patch1`, `patch2`, and `patch3`, all applied, successful transactions exit 0 with empty stderr. Plain `sink` prints exactly `- patch1..patch3\n+ patch3\n+ patch1\n> patch2\n`. Both `sink patch2` and `sink --below patch1 patch2` print exactly `- patch1..patch3\n+ patch2\n+ patch1\n> patch3\n`.

A target cannot also be in the moved set. `sink --below patch1 patch1` exits 2 with empty stdout and exactly ``error: target patch `patch1` may not also be a patch to sink\n`` on stderr. A target that is unapplied is invalid: with `patch3` unapplied, `sink --below patch3 patch2` exits 2 with empty stdout and exactly ``error: cannot sink below `patch3` since it is not applied\n`` on stderr. With no applied patches fail.

`sink` does not reject a dirty index before beginning its transactional pop/reapply sequence. If a staged edit would be overwritten by the tree transition, the underlying `git read-tree -m -u` failure aborts and rolls back the transaction. For two applied patches `p1` and `p2` and a staged edit to `file.txt` which conflicts with sinking the current `p2`, plain `sink` exits 2, prints exactly `- p1..p2\n@ p2 (rolled back)\n` on stdout, and prints exactly:

```text
error: `git read-tree -m -u`: error: Entry 'file.txt' would be overwritten by merge. Cannot merge.;
command aborted (all changes rolled back)
```

on stderr, with a final newline.

## Spec 20

`squash [OPTIONS] <patch-or-range>...` requires at least two patches and replaces a contiguous selected group by one patch at the group's position. Its tree change is the composition from the first selected patch's parent through the last selected patch. Other patches retain content/order and are reapplied as necessary. `-n/--name` sets the new unique valid name. `-m/--message <message>` sets its message; `-f/--file <path>` uses the contents of the named file instead of invoking the editor, with `-` reading from stdin; an editor form may also be used. Otherwise construct/edit a combined message. `--save-template <path>` writes that proposed message template and does not need to complete the squash. Its stderr line encloses the path in backticks; for `/tmp/squash-message.txt` it is exactly:

```text
info: patch template saved to `/tmp/squash-message.txt`
```

Reject noncontiguous selections, one patch, or a name taken by a patch outside the removed group. Squashing only `patch1` exits 2 with empty stdout and exactly `error: need at least two patches\n` on stderr. If `patch3` exists outside the selected group, `squash --name patch3 --message combined patch1 patch2` exits 2 with empty stdout and exactly ``error: patch name `patch3` already taken\n`` on stderr.

`fold [OPTIONS] [diff-file]` applies a unified Git diff from the file, or stdin when omitted, to the index and worktree without rewriting the current patch commit. `--strip N`, `--threeway`, and `--reject` control path stripping/fallback/reject handling. A valid clean diff succeeds silently and stages its result: folding a diff which changes tracked `base.txt` from `base\n` to `base\nfolded\n` leaves `HEAD:base.txt` as `base\n`, changes the worktree file to `base\nfolded\n`, and reports `M  base.txt` in short status. Invalid input, no applied patch, dirty/conflicting state, or a diff that cannot be applied under the selected policy fails without losing existing patch content.

## Spec 21

`hide <patch-or-range>...` removes selected visible patches from normal series operations and puts them in the hidden group. If applied patches are hidden, pop/reapply other patches so their changes disappear but remaining visible changes stay. `series --all` shows hidden patches after visible patches using `! `. Hiding an already-hidden patch is a successful no-op; a nonexistent patch fails. `unhide <patch-or-range>...` returns hidden patches to the visible series as unapplied patches, preserving requested/hidden order; trying to unhide a visible patch fails. After its `- name` events, `unhide` reprints the unchanged top marker. Thus, when `p3` remains top, `unhide p1` prints exactly `- p1\n> p3\n`, and `unhide p1 p2` prints exactly `- p1\n- p2\n> p3\n`. Both accept a branch selector.

`clean [--applied|--unapplied]` deletes empty patches (patch tree equals parent tree). Default cleans both applied and unapplied visible patches. The options restrict the group, leaving nonempty and nonselected empty patches. Hidden patches are not cleaned by default. Deleting empty unapplied patch `empty1` while `p3` remains top prints exactly `# empty1\n> p3\n`; the unchanged top marker is part of the transcript. With an uninitialized branch this command is a successful no-op with empty output. Extra operands fail.

## Spec 22

`commit [OPTIONS] [patch-or-range]...` finalizes selected applied patches into ordinary Git history by removing only their StGit patch records without changing their commits/trees. With no operand, finalize the bottom patch. Explicit names/ranges finalize exactly those patches, including a patch in the middle, while unrelated lower and upper patches remain recorded. `-n/--number N` finalizes N patches from the bottom; `-a/--all` finalizes all. Preserve file content and messages. `--allow-empty` permits finalizing empty commits. No usable patches/uninitialized stack is an error.

`uncommit [OPTIONS] [patch-name]...` converts ordinary first-parent commits immediately below the stack into applied StGit patches without changing their trees, messages, authors, or order. With no count convert one; `-n/--number N` converts N; `--to <committish>` converts back through the commit after that boundary; `--exclusive` excludes the boundary commit. Explicit names rename the produced patches in chronological order. It may initialize an otherwise uninitialized eligible branch. Reject a negative count, incompatible `--to`/count/name combinations, insufficient ordinary commits, merge/nonlinear input where unsupported, or duplicate generated/provided names.

## Spec 23

Every successful stack mutation creates a stack changelog transaction recording the command and enough before/after state for reversal. `log [OPTIONS] [patch-or-range]...` displays this changelog newest first. Default lines are `<7-hex-id>   <RFC-like local date>   <operation>`, with operations such as `initialize`, `new: patch`, `push`, `pop`, and `refresh`. `-n/--number N` limits records (zero prints none; oversized prints all). `-f/--full` uses full Git-log commit records. `-d/--diff` adds metadata diffs. Patch operands filter to transactions affecting those patches; `--branch` selects another stack. `-g/--graphical` launches `gitk` and is mutually exclusive with diff/full/number; inability to execute it is an error. `--clear` is mutually exclusive with patch operands and with `-d/--diff`, and replaces prior history with one `clear log` transaction.

`undo [-n|--number N] [--hard]` restores a prior stack transaction state; default N=1 and N must be positive. It restores patch order, names, metadata, applied boundary, HEAD, index, and (when safe or with `--hard`) worktree. The internal temporary-patch steps of `refresh` affect the actual undo boundary. Starting with top patch `patch1`, modifying a tracked file, successfully running plain `refresh`, and then running `undo` exits 0, prints exactly `> refresh-temp\n`, and leaves series output exactly `+ patch1\n> refresh-temp\n`; it does not restore a series containing only top patch `patch1`.

`redo` reapplies up to N undone transactions. A new mutation clears redo history. When no transaction remains to redo, plain `redo` exits 2 with empty stdout and exactly `error: no more redo information available\n` on stderr. Requesting more undo steps than are available exits 2 with empty stdout and exactly `error: not enough undo information available\n` on stderr. `undo --number 0` is an argument error: it exits 1 with empty stdout and stderr consisting of `error: invalid value '0' for '--number <n>': Bad number of commands to undo`, a blank line, `For more information, try '--help'.`, and a final newline. `redo --number 0` has the analogous status and layout, with `error: invalid value '0' for '--number <n>': Bad number of commands to redo`. With the two-token spelling `undo --number -1`, `-1` is parsed as an unexpected argument: the command exits 1 with empty stdout and stderr containing `error: unexpected argument '-1' found`, the `Usage: stg undo [OPTIONS]` block, and the help hint. `--hard` permits discarding conflicting local changes; without it protect local data. Both emit the same transition progress conventions as the underlying restored state.

On an uninitialized committed branch named `master`, both `undo` and `redo` exit 2 with empty stdout and exactly ``error: StGit stack not initialized for branch `master`\n`` on stderr.

`reset [--hard] [state]` restores the stack to the state identified by an accepted changelog committish. The state is optional and defaults to the current stack state; in particular, `reset --hard` on an initialized stack succeeds with exit 0 and empty stdout/stderr, resets index and worktree to that state, and removes tracked worktree modifications. A patch name is not accepted merely because it names a stack boundary: `reset --hard p1` exits 2 with empty stdout and exactly ``error: invalid committish `p1`\n`` on stderr. Without `--hard`, preserve compatible worktree changes; with it reset index/worktree too. Invalid states fail atomically. Resetting can restore patches removed or changed by later transactions when an accepted state is supplied.

## Spec 24

`branch` with no arguments prints only the current branch. `branch -l/--list [--all]` lists local branches alphabetically using `> ` for current or two spaces otherwise, then `s` if initialized and `p` if protected, a tab, an aligned branch name, two spaces, and `|`. A nonempty description follows as one space plus its text; with an empty description the line ends immediately after `|`, with no trailing space. Thus a repository whose sole branch is an initialized, unprotected `master` with no description prints exactly `> s \tmaster  |\n`. Example with a description: `> sp\tfeature  | description`. Non-stack branches have a blank `s` column.

`branch -c/--create <name> [committish]` creates, switches to, and initializes a new stack. By default it starts from current `HEAD`, records an identifiable current stack as `branch.<new>.stgit.parentbranch`, and reports that it is recording a local branch. A committish may be used; inability to infer a parent is informational, not fatal. Dirty compatible working changes survive creation. Existing names and switching to the current branch fail. Creating an already-existing branch named `master` exits 2 with empty stdout and exactly ``error: branch `master` already exists\n`` on stderr.

`branch --clone [<name>]` clones current branch and complete stack state, switches to it, and stores description `clone of <source>`. With no name, derive one from the source branch and local creation timestamp in the exact form `<source>-YYYYMMDD-HHMMSS`; for example, a clone of `master` made at the observed time selected `master-20260918-012746`. A successful nameless clone exits 0 with empty stdout and stderr. Clone requires a clean tracked worktree and index even when the clone would initially point to the same commit. With a tracked worktree modification, `branch --clone newbranch` exits 2 with empty stdout, leaves the current branch and modification unchanged, and prints exactly ``error: worktree not clean; use `refresh` or `reset --hard`\n`` on stderr. `branch <name>` switches to an existing branch, preserving each branch's independent stack and refusing dirty/conflicting switches. `branch -` switches to the previous branch. `branch -r/--rename [old] <new>` renames a Git branch, its stack ref, and all `branch.<name>.*` configuration, preserving description/parent/protection; with one name rename current. `branch {--delete,-D} [--force] [branch]` deletes the named branch, or the current branch when the name is omitted. Nameless deletion of a current branch with a known parent deletes that branch, switches to the parent, and exits 0 with empty stdout and stderr. Without a known parent, it exits 2 with empty stdout and exactly `error: cannot delete the current branch without a known parent branch\n` on stderr. Refuse protected branches and, without force, initialized branches containing patches. That refusal exits 2 with empty stdout and exactly `error: delete not permitted: the series still contains patches (override with --force)\n` on stderr. Deleting a nonexistent branch `nonexistent` exits 2 with empty stdout and exactly ``error: branch `nonexistent` not found\n`` on stderr.

`branch --describe <text>` sets `branch.<name>.description`; an empty string clears it. A branch argument targets another branch. `branch {--protect,-p} [branch]` and `branch {--unprotect,-u} [branch]` toggle persisted protection on the named branch, defaulting to the current branch; both successful forms exit 0 with empty stdout and stderr. Protection does not block `new`: immediately after `branch --protect`, `new -m blocked p` exits 0 with empty stderr, prints exactly `> p (new)\n`, and creates applied patch `p`. Commands including pull, rebase, repair, cleanup, and deletion perform their separately specified protection checks.

`--cleanup [--force]` removes stack metadata but leaves the Git branch and commits. On a protected branch it exits 2 with empty stdout and exactly `error: clean up not permitted: this branch is protected\n` on stderr. Without force, a nonempty stack exits 2 with empty stdout and exactly `error: clean up not permitted: the series still contains patches (override with --force)\n` on stderr. Deleting a protected branch likewise exits 2 with empty stdout and exactly `error: delete not permitted: this branch is protected\n` on stderr. `--merge` merges/switches as defined by Git while retaining stack state. Branch operations accept the other short forms shown in help and reject incompatible modes/argument counts.

## Spec 25

`export [OPTIONS] [patch-or-range]...` exports selected patches in series order, defaulting to all applied patches (not unapplied or hidden patches). A directory-format patch begins with its full description, a blank line, `From: Name <email>`, optional date/metadata, and—when there is no such metadata—exactly two empty lines after the `From:` line before `---`. Git diffstat follows `---`, then one empty line, then the canonical Git diff from its parent. The diffstat uses the reference's padded number column. For files `added.txt`, `created.txt`, and `modified.txt` with respectively 3 insertions, 1 insertion, and 2 insertions plus 2 deletions, its exact lines are:

```text
 added.txt    |    3 +++
 created.txt  |    1 +
 modified.txt |    4 ++--
 3 files changed, 6 insertions(+), 2 deletions(-)
```

An empty patch ends with `---\n\n` and no `diff --git` line. `-s/--stdout` uses the same two-empty-line header layout. With exactly one selected patch it emits the raw patch without a name separator; with multiple selected patches it prefixes each block with a 79-hyphen line, its patch name, and another 79-hyphen line. It writes nothing to stderr and creates no series file.

Otherwise `-d/--dir <directory>` selects the directory; without it use `patches-<current-branch>`. Create one file per patch plus a `series` file. Its first line is exactly `# This series applies on Git commit <full-base-id>`, where `<full-base-id>` is the 40-hex commit immediately below the first exported patch; subsequent lines list the exported filenames in order. The default filename is exactly the patch name with no extension. `-n/--numbered` prefixes sequence numbers padded to at least two digits and a hyphen (`01-name`); `-p/--patch` adds `.patch`; `-e/--extension <suffix>` adds `.<suffix>`; combinations compose (`01-name.patch`). `-t/--template <file>` is a content template, not a filename template, and substitutes at least `%(shortdescr)s`, `%(authname)s`, `%(authemail)s`, `%(authdate)s`, `%(description)s`, and `%(diffstat)s`. The output directory need not be newly created: if an empty directory `patches` already exists, `export --dir patches test-patch` exits 0 with empty stdout and stderr and writes `patches/series` and `patches/test-patch`. Invalid destinations fail. An unresolved explicit patch named `nonexistent` exits 2 with empty stdout and exactly ``error: patch `nonexistent` does not exist\n`` on stderr. Repeatable `-O/--diff-opt` changes generated diffs. Output includes Unicode losslessly and can be re-imported to reproduce logical changes and metadata.

## Spec 26

`import [OPTIONS] [file]` parses a StGit export or plain unified diff and creates a new applied patch. Omitted file or `-` reads stdin. For a named local non-mail file, the default patch name is its basename, independently of the first description line: importing a file named `patch1` whose description begins `Add new line to file1` creates `patch1` and prints `> patch1 (new)\n`. `-S/--series <series-file>` imports the files listed there, resolving relative entries from the series file's directory and preserving order; each imported patch likewise takes the listed file's basename, and the base-comment line written by `export` is not a patch entry. `-m/--mail` parses one email/Git format-patch message and `-M/--mbox` imports every message from an mbox. Mail import is an exception to filename-derived naming: a named file `mail_patch.eml` with subject `[PATCH] Fix bug in parser` creates `fix-bug-in-parser` and prints exactly `> fix-bug-in-parser (new)\n`. `-n/--name` overrides the name for a single patch; author fields override parsed headers. `--stripname` removes a leading sequence number and conventional extension from the filename-derived patch name; `-p/--strip N` strips path components; `--reject` keeps the patch applied and writes failed hunks to `.rej` files. If hunks are rejected, it exits 3 (not 2); the created patch is reported on stdout and stderr ends with `error: patch conflicts`. `--ignore`/whitespace flags affect application; mail-sign options add trailers. Missing, malformed, or nonapplicable input fails without a partial patch unless `--reject` explicitly permits rejected hunks.

`pick [OPTIONS] <commit-or-patch>...` imports one or more commits/patches into the current stack in operand order. A patch name may be resolved in `--ref-branch`; Git commits are accepted directly. Preserve source message, tree delta, and author while using a new committer date. When no name is supplied for a Git commit, derive it from the subject without lowercasing: picking subject `Source patch` with `--noapply` creates `Source-patch` and prints exactly `- Source-patch\n`. Inclusive patch ranges are expanded as multiple inputs before single-input option validation. Therefore `pick --ref-branch master --name custom patch1..patch2`, when that range resolves to two patches, exits 2 with empty stdout and exactly `error: --name can only be specified with one patch\n` on stderr. `--name` and `--parent` are valid only with one input; parent changes the delta base. `--noapply` creates selected patches as unapplied and does not require a clean worktree: picking source `patch1` with a worktree-only modification exits 0, preserves that modification, creates unapplied patch `patch1`, and prints exactly `- patch1\n`. `--revert` creates the inverse with Git's `Revert "subject"` message and, absent an explicit name, prefixes the source patch name with `revert-`. Thus `pick --revert patch2` creates `revert-patch2` and reports `- revert-patch2\n> revert-patch2\n`. `--expose` appends `(imported from commit <full-id>)`. `--fold` applies the source delta for folding into the current patch. Its repeatable `-f/--file <path>` option restricts this operation to the named paths; `pick --fold --file file1.txt patch2` succeeds silently, applies only `patch2`'s `file1.txt` delta to the index/worktree, and leaves its other paths unchanged. `--update` updates current patch and requires one applied. Dirty worktree fails modes which apply or fold changes, but not `--noapply`; missing source, name collisions, or application conflicts fail, and a fold conflict identifies the source as not applying cleanly.

An unresolved pick source is diagnosed as a missing patch. In particular, `pick nonexistent-patch` exits 2 with empty stdout and exactly ``error: patch `nonexistent-patch` does not exist\n`` on stderr.

## Spec 27

`sync [OPTIONS] [patch-or-range]...` synchronizes local patch diffs with patches of the same names from exactly one source: `--ref-branch <branch>` or `--series <file>`. With no explicit patches synchronize the top applied patch; `--all` synchronizes all common applied patches. Temporarily pop patches above each target, merge the source patch's changes into the local patch, then repush and preserve the prior applied boundary where possible. Print transitions and target top lines. Reject dirty index, no applied patches, the current branch as source, missing series files, invalid branches, or no common patches. A failed merge reports `error: merge conflicts syncing '<patch>'` and preserves a recoverable consistent stack.

## Spec 28

`rebase [OPTIONS] [committish]` moves the stack base to the target (or configured upstream when omitted), then reapplies patches in order so their logical deltas and metadata survive. If already based there, report `info: Already based on ` followed by the full ID enclosed in backticks and then a parenthesized ref name when one describes the target. For example, rebasing an initialized, patchless `master` to its current `HEAD` exits 0 with empty stdout and exactly ``info: Already based on `<full-id>` (master)\n`` on stderr. Otherwise pop patches, report `info: Rebasing to '<full-id>' (...)`, reset the branch to the target, and repush. `--nopush` leaves patches unapplied; `--merged` omits already-upstream changes; `--autostash` saves and restores dirty worktree changes; `--interactive` permits sequence editing; `--committer-date-is-author-date` sets rewritten commit dates accordingly.

If no target is supplied and the current branch has no upstream, fail with guidance for configuring one. On branch `master`, this exits 2 with empty stdout and exactly the following stderr, including the blank lines and indentation:

```text
info: if you wish to set tracking information for this branch you can do so with:

    git branch --set-upstream-to=<remote>/<branch> master

error: there is no tracking information for the current branch
```

Repeatable `--exec <shell-command>` runs after each successfully reapplied patch, printing `Executing: <command>` and forwarding output. A nonzero command reports `error: command exited with code N: <command>` and stops/rolls back as required to retain a valid stack. Conflicting patch application uses normal conflict handling. `--nopush` and `--merged` together are invalid. For a rebase that would move the base, protection is checked before making changes. On a protected branch, `rebase <different-target>` exits 2 with empty stdout and exactly `error: this branch is protected; rebase is not permitted\n` on stderr.

## Spec 29

`pull [OPTIONS] [repository]` updates the base from upstream while preserving the stack. Require a clean worktree/index and an unprotected branch. Without tracking information and without explicit repository, fail with:

```text
error: no tracking information for the current branch;
please specify the remote repository to pull from.
```

Default policy runs the configured `branch.<name>.stgit.pullcmd` or `stgit.pullcmd`, otherwise the equivalent Git pull. Before either the default or configured pull command, an explicit repository `origin` produces exactly ``info: Pulling from `origin`\n`` on stderr. This applies with `--nopush` and `--merged` as well as an ordinary pull.

`branch.<name>.stgit.pull-policy=fetch-rebase` runs configured `stgit.fetchcmd` then rebases using configured `stgit.rebasecmd`; before fetching from explicit repository `origin`, it prints exactly ``info: Fetching from `origin`\n`` on stderr, including when either external command is customized. Policy `rebase` uses `branch.<name>.stgit.parentbranch` or the tracked remote ref and rejects an explicit repository. When neither a parentbranch nor tracking configuration is present but the local ref `refs/heads/origin` exists, that ref is the rebase target. Before rebasing, including in this `refs/heads/origin` fallback case, it prints ``info: Rebasing to `<full-id>`\n`` on stderr, where `<full-id>` is the selected base's 40-hex ID. `--nopush` leaves patches unapplied and `--merged` detects upstreamed patches. If `stgit.keepoptimized=true`, perform repository optimization after success. Propagate external command failures and conflicts.

For a pull that has an actionable source, protection is checked before updating it. On a protected branch, `pull origin` exits 2 with empty stdout and exactly `error: this branch is protected; pulls are not permitted\n` on stderr.

## Spec 30

`repair` reconciles existing stack metadata after users modify an initialized branch with ordinary Git commands, but it does not turn newly added ordinary commits above an empty initialized stack into patches. When the patchless initialized branch receives either one Git commit with subject `External commit` or two successive ordinary commits, `repair` exits 0 with empty stdout and stderr, and `series` remains empty. A Git reset that moves `HEAD` backward changes formerly recorded applied patches to unapplied; amended commits update the corresponding recorded patch. For example, after resetting from applied `p2` to `p1`, repair exits 0, prints `> p1\n` on stdout, and exactly ``info: `p2` is now unapplied\n`` on stderr. Preserve patch order. Hidden patches discovered during repair become visible and repair reports their new applied/unapplied status. Merge commits that cannot be represented cause a warning and may make unreachable patch records visible rather than silently losing them. Running on a consistent stack succeeds as a no-op; running where there is no repairable initialized stack fails. Protection forbids repair with `error: this branch is protected; modification is not permitted.`.

## Spec 31

Before any operation that changes `HEAD` or reapplies commits, classify repository state independently as clean, index dirty, worktree dirty, both dirty, or unresolved. Unless a documented keep/spill/force/autostash mode or the transactional `sink` behavior in Spec 19 applies, use these exact errors:

```text
error: index not clean; use `refresh` or `reset --hard`
error: worktree not clean; use `refresh` or `reset --hard`
error: index and worktree not clean; use `refresh` or `reset --hard`
error: resolve outstanding conflicts first
```

These dirty-state errors protect tree transitions that would overwrite or merge tracked index/worktree content. An untracked path does not by itself set the worktree-dirty category. Thus, when a tracked change is staged while `file1.txt` is merely untracked, a protected transition reports only ``error: index not clean; use `refresh` or `reset --hard```. A stack-metadata-only operation does not trigger these errors, but `pop` performs its dirty-state check even when the patch is empty and the old and new `HEAD` trees are identical. In particular, if a new file is staged and then an empty patch `patch1` is created, plain `pop` exits 2 with empty stdout and exactly ``error: index not clean; use `refresh` or `reset --hard`\n`` on stderr; a subsequent `push patch1` consequently exits 2 with ``error: patch `patch1` is already applied\n``. The specifically supported metadata operations remain exceptions: staged paths may coexist with applied empty patches while hiding or deleting those empty patches, unhiding them, and undoing such a deletion, all while preserving the staged index and worktree unchanged. This also applies when several empty patches must be temporarily handled around the selected empty patches.

If `HEAD` differs from the recorded stack top, ordinary mutations such as spill fail with `error: HEAD and stack top are not the same. This can happen if you modify the branch with git. See 'stg repair --help' for next steps to take.`. Operations must never overwrite unrelated untracked files. Conflict status remains visible through the status alias using Git's `UU`/porcelain records. After resolution through `add`/`resolved`, `refresh` records the resolution and clears the conflict.

## Spec 32

Patch messages and identity are Git commit metadata. `--author 'Name <email>'`, `--authname`, `--authemail`, and `--authdate` set author fields; absent fields come from parsed input or Git configuration/environment. Normal rewrites retain original author and author date but create a current committer date. `--committer-date-is-author-date` makes them equal. Accepted date forms include `2001-02-03 04:05:06 +0000`, `Sat, 3 Feb 2001 04:05:06 +0000`, `2001-02-03T04:05:06+00:00`, and `981173106 +0000`; each produces author date `2001-02-03T04:05:06+00:00`. The otherwise similar UTC-designator form `2001-02-03T04:05:06Z` is rejected. In particular, `new --authdate 2001-02-03T04:05:06Z -m Metadata meta` exits 1 with empty stdout and exactly this stderr:

```text
error: invalid value '2001-02-03T04:05:06Z' for '--authdate <date>': invalid date `2001-02-03T04:05:06Z`

For more information, try '--help'.
```

`--signoff`/`--sign` adds `Signed-off-by: Name <email>`; `--ack` adds `Acked-by: ...`; `--review` adds `Reviewed-by: ...`; repeatable trailer options append their supplied trailer. Do not duplicate an identical trailer. Preserve multiline and Unicode messages. Message display indents every commit-message line by four spaces in Git-log style. An empty explicitly supplied message is invalid where a meaningful message is required.

## Spec 33

`email format [OPTIONS] [patch-or-range]...` formats selected applied patches using the harness Git's format-patch conventions. A single patch has subject `[PATCH] <subject>`; a series uses `[PATCH i/N]`; `--cover`/`--cover-letter` emits message 0 with `[PATCH 0/N]`, placeholder subject/blurb, author summary, and aggregate diffstat. Preserve From, Date, message body, diffstat, diff, and the Git version signature. Support output directory, numbered/no-numbered, start number, subject prefix, reroll/version count, RFC, signoff, thread controls, To/Cc/From/In-Reply-To, and format-only behavior. Without an option selecting another directory, write Git-format patch files in the current directory and print their filenames to stdout. `email format` does not support a `--stdout` option. With applied empty patch `email`, `email format --stdout email` exits 1 with empty stdout and exactly this stderr, before performing the empty-patch check:

```text
error: unexpected argument '--stdout' found

  tip: a similar argument exists: '--to'

Usage: stg email format [OPTIONS] <patch>...
       stg email format [OPTIONS] --all

For more information, try '--help'.
```

A selected empty patch is rejected when invoked with supported options; for a patch named `email`, plain `email format email` exits 2 with empty stdout and this diagnostic:

```text
error: cannot format empty patch `email`
```

Resulting files/order and text are those produced by `git format-patch` for the selected commit range and options.

`email send [OPTIONS] <patch-name|range|patch-file|directory>...` resolves patch operands to temporary formatted mail files, accepts existing files/directories, rejects hidden/nonexistent/noncontiguous invalid selections, then invokes `git send-email` with addressing/thread options. Patch operands must form one contiguous selection. Thus `email send p1 p3` exits 2 with empty stdout and exactly ``error: `p3` not contiguous with preceding range `p1`\n`` on stderr. A range may resolve far enough to classify a forbidden hidden endpoint: with hidden `p3`, `email send p2..p3` exits 2 with empty stdout and exactly ``error: hidden patch `p3` is not allowed\n`` on stderr.

The file/directory operand form cannot be mixed with the patch operand form, nor may a file and directory be combined in the same invocation. These are clap value errors with exit 1 and empty stdout. In either case stderr classifies the first existing file operand as an invalid value for `<patch>...`, says it is an `invalid patch range`, repeats that path in backticks, and then gives the email-send usage/help hint.

Every selected patch must be nonempty, whether selected explicitly or through `--all`; if selection includes an empty patch named `empty-patch`, reject it before invoking `git send-email`, exit 2 with empty stdout, and print exactly ``error: cannot send empty patch `empty-patch`\n`` on stderr. `--all` selects all applied patches and `--dump-aliases` invokes `git send-email --dump-aliases`. Forward output; wrap failure as, for example, `error: 'git send-email': <git error>`. For both `email format --all` and `email send --all`, having no applied patches exits 2 with empty stdout and exactly `error: no patches applied\n` on stderr.

For compatibility, `email` without the explicit `format`/`send` word uses the send mode when mail-recipient options are present. The legacy `email --git` form is format-only and writes Git-format patch files to `-o/--output-directory`. `email --help` documents both formatting and sending options and succeeds without a repository.

## Spec 34

`completion --help` begins with this exact two-line overview:

```text
Support completions for bash, fish, and zsh. Also provides 'stg completion list' command
for dynamically introspecting StGit's commands and aliases.
```

Its parent help enumerates the subcommands with these exact aligned descriptions:

```text
Commands:
  bash  Generate bash completion script
  fish  Generate fish shell completion script
  zsh   Generate zsh completion script
  list  List StGit command information
  man   Generate asciidoc man pages
  help  Print this message or the help of the given subcommand(s)
```

The nested help descriptions are exact: `completion list --help` begins `List StGit command information`; `completion bash --help` begins `Generate bash completion script`; `completion fish --help` begins `Generate fish shell completion script`; and `completion zsh --help` begins `Generate zsh completion script`. `completion man --help` begins with:

```text
Generate man pages in asciidoc format. The generated asciidoc files may be further
processed by asciidoc or asciidoctor to produce roff, html, or other output formats.
```

`completion list commands [--style STYLE] [--output FILE]` emits commands in this exact order:

```text
branch
clean
commit
completion
delete
diff
edit
email
export
files
float
fold
goto
hide
id
import
init
log
name
new
next
patches
pick
pop
prev
pull
push
rebase
redo
refresh
rename
repair
reset
series
show
sink
spill
squash
sync
top
uncommit
undo
unhide
version
help
```

`completion list aliases` emits `add`, `mv`, `resolved`, `rm`, and `status`, one per line. The literal kind `commands-and-aliases` emits the command list followed immediately by the alias list. Default/`name-only` style is the above. Fish style is `name<TAB>description`; zsh style is `name:description`; asciidoc style groups command categories and uses `linkstg:name[]::`, while aliases use an `Aliases` heading and their `Alias for shell command ...` descriptions. `--show-expansion` is accepted for aliases and does not alter `name-only` output. Missing list kind exits 1 with empty stdout and begins stderr exactly:

```text
error: 'stg completion list' requires a subcommand but one was not provided
  [subcommands: aliases, commands, commands-and-aliases, help]

Usage: stg completion list [OPTIONS] <COMMAND>
```

Invalid style fails. `-o/--output` writes the result to that file instead of stdout.

`completion bash`, `completion fish`, and `completion zsh` generate complete, deterministic UTF-8 completion programs for every command, option, patch/branch argument, and built-in alias. The bash output begins with these exact six lines:

```text
# -*- shell-script -*-
#
# SPDX-License-Identifier: GPL-2.0-only
#
# bash completion script for StGit (automatically generated)
#
```

It defines completion for `stg` and is valid bash; fish starts with the SPDX line and defines `complete -c stg` entries; zsh starts `#compdef stg` and defines `_stg`. `--output` writes instead of printing. `completion man [-o|--output <directory>]` creates exactly 45 files named `stg-<command>.txt`, including `stg-version.txt`, `stg-init.txt`, `stg-new.txt`, and `stg-branch.txt`. Each is an AsciiDoc man-page source beginning, for example, `stg-version(1)`, an underline of `=`, then `NAME`, `SYNOPSIS`, and `DESCRIPTION` sections; the version page contains `Print version information and exit`. All completion subcommands support help; invalid shell names fail.

Configuration-defined aliases are loaded through the normal Git configuration cascade. Keys are `stgit.alias.<name>` (equivalently `[stgit "alias"] name = ...`). A repository-local value overrides global configuration. Expand its command words before appending invocation arguments and dispatch it as an StGit command. Built-in aliases retain the exact descriptions and Git expansions shown in Spec 3.
