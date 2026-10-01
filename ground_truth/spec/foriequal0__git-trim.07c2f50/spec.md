# Clarified executable specification

The required artifact is a directly runnable file named `executable`. It implements the behavior below by inspecting and, when requested, modifying the Git repository whose working directory contains the process's current directory. Git itself is provided by the execution environment.

## Spec 1

`executable` is a single-command command-line program named `git-trim`; it has no subcommands and accepts options only. Its usage form is `executable [OPTIONS]`. Positional arguments such as `add`, `list`, `config`, or `subcommand` are errors. Options may appear in any order.

Normal reports, help, version output, prompts, dry-run simulations, and successful deletion messages go to standard output. Argument diagnostics and operational errors go to standard error. Help and version terminate successfully without requiring a repository. A successful scan, a completed deletion, and a user-cancelled deletion return status 0. Repository/configuration/fetch failures return 1. Command-line parsing failures return 2. The one specially specified negative Git configuration interval in Spec 7 returns 101.

## Spec 2

`--version` and `-V` both write exactly the following, including the final newline, to standard output and nothing to standard error:

```text
git-trim 0.4.4
```

`--help` writes the following long help, with a final newline, and no ANSI escapes. The visually empty indented lines inside the `--bases` and `--delete` descriptions contain ten spaces before their newline.

```text
Automatically trims your tracking branches whose upstream branches are merged or stray.
`git-trim` is a missing companion to the `git fetch --prune` and a proper, safer, faster alternative to your `<bash oneliner HERE>`.

Usage: executable [OPTIONS]

Options:
  -b, --bases <BASES>
          Comma separated multiple names of branches. All the other branches are compared with the upstream branches of those branches. [default: branches that tracks `git symbolic-ref refs/remotes/*/HEAD`] [config: trim.bases]
          
          The default value is a branch that tracks `git symbolic-ref refs/remotes/*/HEAD`. They might not be reflected correctly when the HEAD branch of your remote repository is changed. You can see the changed HEAD branch name with `git remote show <remote>` and apply it to your local repository with `git remote set-head <remote> --auto`.

  -p, --protected <PROTECTED>
          Comma separated multiple glob patterns (e.g. `release-*`, `feature/*`) of branches that should never be deleted. [config: trim.protected]

      --no-update
          Do not update remotes [config: trim.update]

      --update-interval <UPDATE_INTERVAL>
          Prevents too frequent updates. Seconds between updates in seconds. 0 to disable. [default: 5] [config: trim.updateInterval]

      --no-confirm
          Do not ask confirm [config: trim.confirm]

      --no-detach
          Do not detach when HEAD is about to be deleted [config: trim.detach]

  -d, --delete <DELETE>
          Comma separated values of `<delete range>[:<remote name>]`. Delete range is one of the `merged, merged-local, merged-remote, stray, diverged, local, remote`. `:<remote name>` is only necessary to a `<delete range>` when the range is applied to remote branches. You can use `*` as `<remote name>` to delete a range of branches from all remotes. [default : `merged:origin`] [config: trim.delete]
          
          `merged` implies `merged-local,merged-remote`.
          
          `merged-local` will delete merged tracking local branches. `merged-remote:<remote>` will delete merged upstream branches from `<remote>`. `stray` will delete tracking local branches, which is not merged, but the upstream is gone. `diverged:<remote>` will delete merged tracking local branches, and their upstreams from `<remote>` even if the upstreams are not merged and diverged from local ones. `local` will delete non-tracking merged local branches. `remote:<remote>` will delete non-upstream merged remote tracking branches. Use with caution when you are using other than `merged`. It might lose changes, and even nuke repositories.

      --dry-run
          Do not delete branches, show what branches will be deleted

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

## Spec 3

`-h` writes this shorter help and succeeds. It differs from `--help` exactly by omitting the second opening paragraph, the extended paragraphs for `--bases` and `--delete`, and most blank separators, and by saying how to obtain more help:

```text
Automatically trims your tracking branches whose upstream branches are merged or stray.

Usage: executable [OPTIONS]

Options:
  -b, --bases <BASES>
          Comma separated multiple names of branches. All the other branches are compared with the upstream branches of those branches. [default: branches that tracks `git symbolic-ref refs/remotes/*/HEAD`] [config: trim.bases]
  -p, --protected <PROTECTED>
          Comma separated multiple glob patterns (e.g. `release-*`, `feature/*`) of branches that should never be deleted. [config: trim.protected]
      --no-update
          Do not update remotes [config: trim.update]
      --update-interval <UPDATE_INTERVAL>
          Prevents too frequent updates. Seconds between updates in seconds. 0 to disable. [default: 5] [config: trim.updateInterval]
      --no-confirm
          Do not ask confirm [config: trim.confirm]
      --no-detach
          Do not detach when HEAD is about to be deleted [config: trim.detach]
  -d, --delete <DELETE>
          Comma separated values of `<delete range>[:<remote name>]`. Delete range is one of the `merged, merged-local, merged-remote, stray, diverged, local, remote`. `:<remote name>` is only necessary to a `<delete range>` when the range is applied to remote branches. You can use `*` as `<remote name>` to delete a range of branches from all remotes. [default : `merged:origin`] [config: trim.delete]
      --dry-run
          Do not delete branches, show what branches will be deleted
  -h, --help
          Print help (see more with '--help')
  -V, --version
          Print version
```

Help takes precedence if combined with other ordinary options. A token after `--` is positional, so `executable -- --help` is an error rather than help.

## Spec 4

The public value-taking options are `-b/--bases`, `-p/--protected`, `--update-interval`, and `-d/--delete`. They accept either a separate value or long-option `--name=value` syntax. `--bases` also has the accepted long alias `--base`. The flags are `--dry-run`, `--no-update`, `--no-confirm`, and `--no-detach`. The positive forms `--update`, `--confirm`, and `--detach` are also accepted overrides, although they are intentionally omitted from help.

The parser accepts each positive flag together with its negative counterpart. These pairs are therefore not command-line parsing failures. Repository opening happens before the application checks for an opposite pair: outside a repository, for example, `--update --no-update` returns the ordinary status-1 repository-not-found error from Spec 6. Once a valid repository is open, either ordering of `--update` and `--no-update`, `--confirm` and `--no-confirm`, or `--detach` and `--no-detach` writes the corresponding line below to standard error and exits with status 255:

```text
Error: Flag 'update' and 'no-update' cannot be used simultaneously
Error: Flag 'confirm' and 'no-confirm' cannot be used simultaneously
Error: Flag 'detach' and 'no-detach' cannot be used simultaneously
```

`--update-interval` is a base-10 unsigned 64-bit integer and may occur only once. Zero is valid. A separate negative value is parsed as an unexpected option-like argument; an attached negative value is an invalid option value. Values greater than `18446744073709551615`, nonnumeric values, and repetitions fail during argument parsing.

## Spec 5

Command-line syntax errors use lowercase Clap-style diagnostics on standard error and return nonzero. Unknown flags or positionals begin `error: unexpected argument '<token>' found`. Missing values contain `a value is required for '--bases <BASES>'`, `--protected <PROTECTED>`, `--update-interval <UPDATE_INTERVAL>`, or `--delete <DELETE>` as applicable. Invalid typed values begin `error: invalid value '<value>' for '<option signature>': ...`. Every such diagnostic ends with a blank line and `For more information, try '--help'.`; diagnostics for unexpected arguments also show `Usage: executable [OPTIONS]` before that line.

Examples that are compared exactly are:

```text
error: unexpected argument '--unknown-flag' found

Usage: executable [OPTIONS]

For more information, try '--help'.
```

```text
error: invalid value 'invalid-range' for '--delete <DELETE>': Invalid delete range format `invalid-range`

For more information, try '--help'.
```

```text
error: invalid value 'invalid' for '--update-interval <UPDATE_INTERVAL>': invalid digit found in string

For more information, try '--help'.
```

Combined short syntax is not generally treated as several options when a value-taking option is involved: `-bd merged:origin` ultimately rejects `merged:origin` as unexpected. Repeating `--update-interval` reports that it `cannot be used multiple times`.

## Spec 6

Before scanning, open the current Git repository. If none can be found, write exactly `Error: could not find repository at '.'; class=Repository (6); code=NotFound (-3)\n` and return 1. Remote presence is checked before configuration/base discovery and before any operation that requires a worktree. Consequently, a freshly initialized bare repository with no configured remotes writes exactly `Error: git-trim requires at least one remote\n`, returns 1, and produces no standard output. A non-bare repository with no configured remotes, including an empty newly initialized repository, has the same result.

There is no eager bare-repository check merely because a remote exists. A bare repository with one configured remote but no discoverable base first takes the ordinary implicit-no-base path from Spec 9: it returns 1, writes `You also can set bases manually with any of following commands:\n` to standard output, and writes the complete single-remote guidance ending in `Error: No base branch is found!\n` to standard error. If a usable base is explicitly supplied so execution reaches a worktree-dependent operation, `--no-update --bases master --dry-run` instead returns 1, produces no standard output, and writes exactly `Error: Bare repository is not supported\n` to standard error. With updates enabled, that same bare-repository error is preceded on standard output by the captured empty update-output line.

Remote URLs may be local paths, HTTPS URLs, SSH-style URLs, or names with punctuation. Merely having a remote with a nonempty URL is sufficient when updates are disabled; the URL need not be reachable for a scan based on local refs. A configured remote whose URL is empty is silently excluded from that scan. In particular, when a valid `origin` exists alongside an empty-URL remote named `broken` with fetch refspec `+refs/heads/*:refs/remotes/broken/*`, `--no-update --bases main --dry-run` returns 0, writes no error, and reports only the local `main` and `origin/main` base references; it does not report `broken`.

## Spec 7

Read repository/global Git configuration keys `trim.bases`, `trim.protected`, `trim.update`, `trim.updateInterval`, `trim.confirm`, `trim.detach`, and `trim.delete`. Explicit command-line settings replace the corresponding configured setting; they are not appended to it. Thus, for example, CLI `--bases master`, `--protected hotfix-*`, or `--no-update` wins over a different configured value. Defaults are: update enabled, update interval 5 seconds, confirmation enabled, detaching enabled, no protected patterns, implicit bases as in Spec 8, and delete range `merged:origin`.

For list-valued Git keys, consume every `git config --add` entry, split each on commas, trim surrounding whitespace for protected patterns, and ignore empty list items. Whitespace is not trimmed from base items. Multiple base entries and comma-separated bases are accumulated. An invalid padded base item fails with status 1 and exactly `Error: could not use '<item>' as valid reference name; class=Reference (4); code=InvalidSpec (-12)\n`; for example, the item ` develop` produces `Error: could not use ' develop' as valid reference name; class=Reference (4); code=InvalidSpec (-12)\n`.

Delete ranges have their own parser: it trims whitespace around the keyword and, for a scoped form, around both sides of the first colon. Thus configured values such as ` merged:origin ` and ` stray ` are valid and are accumulated normally. Trimming does not turn an unknown word into a valid range, and its diagnostic retains the original item: with configured entries `merged:origin` and `local, bogus`, `--no-update --dry-run` returns 1 and writes exactly ``Error: Invalid delete range format ` bogus`\n`` to standard error.

An explicitly empty `trim.bases` is an error. An empty CLI occurrence, `--bases ''` or `--bases=`, contributes no explicit base item: configuration is used if present, otherwise implicit discovery from Spec 8 still runs. Its presence nevertheless changes the no-base case. If neither configuration nor implicit discovery supplies a base, accept the resulting empty base set and scan instead of emitting the implicit-no-base error from Spec 9. In a repository containing one untracked local `master`, a configured `origin` with no remote references or discoverable remote HEAD, and no `trim.bases`, `--bases '' --dry-run --no-update` returns 0, writes nothing to standard error, and writes exactly:

```text
Branches that will remain:
  local branches:
    master *2
  remote references:
  Some branches are skipped. Consider following to scan them:
    *2: Set an upstream to make it a tracking branch or add `--delete 'local'` flag.

```

The `--bases=` spelling has the same result. By contrast, when remote-HEAD discovery succeeds, an empty CLI occurrence uses those discovered bases: in the ordinary clone with local `master`, `origin/master`, and `origin/HEAD`, `--no-update --bases= --dry-run` returns 0 and reports both `master [base]` and `origin/master [base]`. A nonexistent but syntactically valid nonempty explicit base is allowed and simply matches nothing.

Git boolean `true` and `false` values are supported. An invalid boolean such as `maybe` or `notabool` returns 1 with `Error: failed to parse '<value>' as a boolean value; class=Config (7)\n`. A noninteger configured update interval similarly reports `Error: failed to parse '<value>' as an integer; class=Config (7)\n`. Invalid configured delete entries are fully validated, including later entries, and report ``Error: Invalid delete range format `<bad-item>`\n``.

A negative configured `trim.updateInterval` deliberately behaves like the Rust 0.4.4 panic: return 101 and write a panic diagnostic containing, on its own line, `` `git config trim.updateInterval` cannot be negative value `` and the final line ``note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace``. The thread line is of the form `thread 'main' (<decimal process/thread id>) panicked at src/config.rs:<error location>:`.

## Spec 8

Base specifications identify the upstream branches against which merge completion is judged. Explicit bases may be local short names such as `master` and `develop`, remote short names such as `origin/dev`, and comma-separated collections. A local-name base only becomes usable when that local branch has a resolvable upstream. A syntactically valid explicit local name with no upstream is allowed but is treated like another non-tracking branch; for example, with `trim.bases=master`, an untracked `master` is printed `master *2`, while ordinary `origin/master` and `origin/some-branch` refs are printed without `*3` because there is no usable base against which to scan or skip them.

Being a usable base protects a classified deletion candidate, but does not by itself force the display suffix `[base]`. The suffix depends on the classification path used by the selected delete ranges. A merged tracking local and its normal merged upstream, when classified and then preserved as bases, appear as `[base]`. If tracking classification is not enabled at all, even a usable explicit base and its upstream can instead appear with `*1`; `--delete remote:* --bases master` in the evaluated multi-remote fixture prints `master *1` and `origin/master *1`. A stray local preserved because it is a base is printed `[stray, but: base]`, and a base remote classified through the non-upstream path is printed `[merged non-upstream, but: base]`. An explicitly remote-only base such as `origin/dev` protects that remote base and also prevents its tracking local branch from being deleted, annotating the latter as tracking that base when that classification is reached. Usable base branches are never deletion targets, even when one base has been merged into another or its local/remote tips have diverged. Other branches may be merged into any one of several bases.

With no nonempty explicit/configured bases, discover all valid symbolic references matching `refs/remotes/*/HEAD`, resolve each to its target remote branch, and use the local branch that tracks that target as a base. Aggregate valid HEADs from multiple remotes. Silently ignore broken symbolic refs. An empty CLI value contributes no base and therefore does enter this discovery path. If discovery finds nothing, however, the occurrence permits the scan to continue with no bases as described in Spec 7.

If explicit `trim.bases` exists but contains no values, emit the following to standard error and fail:

```text
I found that `git config trim.bases` is empty! Try any following commands to set valid bases:
 * `git config trim.bases develop,master` for a repository.
 * `git config --global trim.bases develop,master` to set globally.
 * `git trim --bases develop,master` to set temporarily.
Error: No base branch is found!
```

## Spec 9

If implicit discovery is actually selected and finds no base, fail with the explanatory text below only when no CLI `--bases` occurrence was supplied. An empty `--bases ''` or `--bases=` occurrence suppresses this error and continues with no bases as specified in Spec 7. The lines are shown in temporal order (and therefore in this order when the streams are merged with `2>&1`). One historical stream quirk is required: the line `You also can set bases manually with any of following commands:` goes to standard output, while every other line in this diagnostic goes to standard error. Consequently, a caller that separately captures streams and concatenates `stdout + stderr` sees that one line first. For one remote named `origin`, use exactly:

```text
I can't detect base branch! Try following any resolution:
 * `git remote set-head origin --auto` will help `git-trim` to automatically
   detect the base branch.
   If you see `origin/HEAD set to <base branch>` in the output of the previous
   command, then `git branch --set-upstream origin/<base branch> <base branch>`
   to set an upstream branch for <base branch> if exists.
You also can set bases manually with any of following commands:
 * `git config trim.bases develop,master` for a repository.
 * `git config --global trim.bases develop,master` to set globally.
 * `git trim --bases develop,master` to set temporarily.
Error: No base branch is found!
```

For multiple remotes, replace the remote-specific paragraph by:

```text
 * `git remote set-head <remote> --auto` will help `git-trim` to automatically
   detect the base branch.
   Following command will sync all remotes for you:
   `for REMOTE in $(git remote); do git remote set-head "$REMOTE" --auto; done`
   Pick an appropriate one in mind if you see multiple `<remote>/HEAD set to
   <base branch>` in the output of the previous command.
   Then `git branch --set-upstream <remote>/<base branch> <base branch>` to set
   an upstream branch for <base branch> if exists.
```

Keep the same opening, manual-base paragraph, and final error. The final nonempty line must be `Error: No base branch is found!`.

## Spec 10

Unless disabled, update all configured remotes with pruning before classification, with behavior equivalent to `git remote update --prune`. Under `--dry-run`, this update is itself passed through as a Git dry run: it may print the actions Git would take, but it does not refresh or prune local remote-tracking refs. Classification therefore uses the refs that existed before invocation. Forward the update command's output; an attempted external fetch therefore produces `Fetching <remote>`. The captured standard-output text is emitted as a line even when empty, so a successful quiet local update contributes one leading blank line before `Branches that will remain:`. `--no-update` or configured `trim.update=false` performs no fetch and emits no fetch separator. Explicit `--update` forces an update even if it would otherwise be rate-limited.

Rate limiting is usable only when `fetch.prune` is true and `.git/FETCH_HEAD` exists. If its modification age is less than the selected interval, skip network access and print `Repository is updated recently. Skip to update it`. Interval 0 disables rate limiting and always updates. A missing `FETCH_HEAD`, an age at least the interval, or `fetch.prune=false` forces an update.

An update failure against a nonexistent local repository path does not stop classification or preserve Git's own fetch diagnostic in the following observed cases:

- `--update --bases main --dry-run --update-interval 3600` with a fresh `FETCH_HEAD` (the explicit update bypasses rate limiting);
- `--bases main --dry-run --update-interval 3600` with `fetch.prune=false` and a fresh `FETCH_HEAD`; and
- `--bases main --dry-run --update-interval 0`.

In every case, the program emits the captured empty update-output line, prints the complete retained-branch report from the existing refs, then returns 1 and writes exactly `Error: Key has been revoked (os error 128)\n` to standard error. For a clone containing only the base references, stdout therefore starts with a newline and reports `main [base]` and `origin/main [base]`. It does not write `Fetching origin`, `error: Could not fetch origin`, or `Error: Operation not permitted (os error 1)` in these cases.

## Spec 11

Enumerate local branches and ordinary remote-tracking references. Determine each local branch's configured upstream from `branch.<name>.remote` and `branch.<name>.merge`. Respect custom fetch refspecs when translating between a remote-side ref and a local remote-tracking ref. Exact mappings are supported: `+refs/heads/master:refs/remotes/origin/master` allows local `master` and `origin/master` to be resolved and reported as bases. Pattern mappings are supported when source and destination each contain exactly one `*`; the wildcard may occur at the beginning, middle, or end of either side and the matched substring is substituted at the destination wildcard. Thus destinations including `refs/remotes/origin/release-*`, `refs/remotes/origin/*-stable`, and `refs/remotes/origin/rel-*-branch` work and respectively display refs such as `origin/release-main`, `origin/main-stable`, and `origin/rel-main-branch`. An empty wildcard match is allowed, and matching is case-sensitive across slashes, dots, hyphens, underscores, Unicode, and long names. Use only fetch-direction refspecs. `Error: remote with matching refspec not found\n` applies when the consulted fetch mapping does not match, not merely because the mapping is exact or repositions its wildcard.

One important multiple-refspec quirk is contractual: translation consults only the first applicable-direction fetch refspec and returns its match or non-match without trying later fetch refspecs. With the ordinary `+refs/heads/*:refs/remotes/origin/*` mapping first and a later `+refs/pull/*:refs/remotes/origin/*`, a fetched `refs/pull/7` stored as `origin/7` is translated back through the first mapping as `refs/heads/7`. For `--no-update --bases master --delete 'merged:*,remote:*' --dry-run`, the retained report omits `origin/7`, the deletion section contains exactly `  - origin, refs/heads/7 (non-upstream)`, and Git's dry-run push writes a deletion line for `7` to standard error. The actual `refs/pull/7` ref remains because dry-run does not mutate it. A local `pull-copy` configured to merge `refs/pull/7` remains as a plain local entry in this invocation.

Direct-fetch arrangements are supported: `branch.<name>.remote` may be a URL/path such as `../origin.git` rather than a configured remote name. Inspect that remote ref directly and, if selected, display it as `<remote-or-path>, refs/heads/<branch>` while leaving unrelated local remote-tracking refs alone.

## Spec 12

For each candidate relative to all selected bases, classify merge completion by Git history and change equivalence, not only by the presence of a merge commit. A branch is merged if its tip is reachable from a base (fast-forward, ordinary merge, or `--no-ff` merge), or if all changes introduced by it are already represented in a base after a squash/rebase-style integration. This must work through deep/nested merge history and when several names point at the same commit.

An unmerged branch whose upstream still exists remains untouched. Merge classification takes precedence over a missing upstream: if a tracking local tip is already reachable from or change-equivalent to a base, it is merged even when its upstream disappeared after pruning. The default `merged:origin` therefore selects that local side, and a real `--no-confirm` run deletes it. A tracking local branch whose upstream disappeared is `stray` only when its local tip is not already merged. This includes a local side with later unmatched edits after the upstream side was integrated and deleted; the already integrated remote side may independently be classified as merged. A `diverged` pair is the converse tested case: the local tip has been integrated into a base while the upstream remote branch has additional commits not integrated into a base. A local branch with no upstream is non-tracking; a remote-tracking branch that is not the upstream of any local branch is non-upstream.

Classification must work in simple one-remote flows, Git-flow arrangements with both `develop` and `master` bases, triangular workflows where fetch/upstream and push remotes differ, and hub-style direct fetches.

## Spec 13

`--delete`/`trim.delete` accepts a comma-separated union of these exact ranges:

- `merged:<scope>` is shorthand for both `merged-local` and `merged-remote:<scope>`.
- `merged-local` selects merged local branches that have an upstream.
- `merged-remote:<scope>` selects the upstream remote refs of merged local branches.
- `stray` selects stray local branches.
- `diverged:<scope>` selects a merged local side and its diverged upstream remote side.
- `local` selects merged local branches with no upstream.
- `remote:<scope>` selects merged remote-tracking head refs that are not upstreams of local branches.

These ranges select only candidates that can be classified from the locally available base refs. In particular, `--dry-run` does not first refresh those refs (Spec 10). In the evaluated non-tracking fixture, the remote repository's `master` has received `feature` but the local `origin/master` is still stale; `--delete local --bases master --dry-run` retains `feature` as a plain local entry and prints `master *1` and `origin/master *1`. It does not print a deletion section or `Delete branch feature (dry run).` Merely observing that the remote repository was advanced is not enough to select the local-only branch during that dry run.

`scope` is either one exact remote name/path or `*` for every remote. `merged-remote`, `diverged`, and `remote` require a scope. `merged` also requires a scope in evaluated invocations. An empty scope on any scoped form fails with `Scope parse error for delete range while parsing scope: Scope is empty`; configuration-originated errors add a blank line and:

```text
Caused by:
    Scope is empty
```

An unknown keyword or malformed value fails with the text ``Invalid delete range format `<value>```. The default is `merged:origin`; thus it selects merged tracking locals and their merged `origin` upstreams, but not stray, diverged, local-only, or non-upstream remote branches.

## Spec 14

Selection is per side of an ordinary named-remote local/remote pair. For example, `merged-local` deletes the local branch but reports its merged remote ref as remaining because `merged-remote:<remote>` was not given; `merged-remote:origin` does the reverse. A protected local branch does not automatically protect its ordinary merged upstream remote ref: with default `merged:origin`, the local is retained with its protection reason while the remote ref can still be selected. Conversely, a remote-only/non-upstream or direct-fetch ref to which protection directly applies is retained.

Direct fetches are an exception to the per-side rule. If a merged local branch has `branch.<name>.remote=../origin.git`, then `--delete merged-remote:../origin.git` selects both the local branch and the direct remote ref. The local appears under `Delete merged local branches:`, the remote appears under `Delete diverged remote refs:` as `  - ../origin.git, refs/heads/<name>`, and dry-run output includes `Delete branch <name> (dry run).` Thus a remote-only range does not preserve the local side in this direct-path arrangement.

Remote scopes are strict. In a two-remote repository, `merged-remote:origin` cannot delete from `upstream`; `merged-remote:*` covers merged upstreams across remotes, and `remote:*` is separately needed for non-upstream refs. When a branch is pushed to several remotes but tracks only one, its other remote copies are non-upstream rather than merged-upstream candidates.

## Spec 15

`--protected` and `trim.protected` contain case-sensitive simple glob patterns over complete branch names. A pattern may have no wildcard (exact match) or one `*`, which matches any sequence including empty and `/`. Support prefix, suffix, middle, path (`feature/*`), `refs/...`-prefixed, overlapping, punctuation-containing, Unicode, and very long names. Comma-separated patterns form a union. Empty patterns protect nothing, and patterns matching nothing are harmless.

A selected local branch matching a pattern is retained and annotated `[merged, but: protected by a pattern `<pattern>`]` (or the corresponding diverged annotation). Do not silently omit protected branches from the report.

## Spec 16

Regardless of whether anything is deletable, print a branch plan headed exactly:

```text
Branches that will remain:
  local branches:
  remote references:
```

List retained local entries under the first subheading and remote-tracking/direct entries under the second, indented four spaces. Preserve the order of the repository's branch-reference iterator while filtering deletion targets; do not regroup entries by classification and do not sort the final remote list independently. This order is stable for a fixed repository representation but is not globally lexical. In the evaluated triangular and hub fixtures it puts `upstream/master [base]` before `origin/master *3`. In the evaluated Git-flow fixtures after fetch/prune it puts `origin/master [base]` before `origin/develop [base]`, while the local list remains `develop [base]` before `master [base]`. Preserved direct-fetch entries, which are not ordinary remote-tracking references in that iterator, are appended afterward. Do not introduce nondeterministic hash-map ordering.

Only a merged tracking local or merged tracking remote that is preserved as a base uses the short suffix ` [base]`. Other classifications preserved for being bases retain the classification in the annotation, including ` [stray, but: base]` and ` [merged non-upstream, but: base]`. Other explanatory suffixes include:

- ` [merged, but: delete range `merged-local` was not given]`
- ` [merged, but: delete range `merged-remote:origin` was not given]`
- ` [merged, but: protected by a pattern `release-*`]`
- ` [diverged with <remote>, refs/heads/<name>, but: protected by a pattern `<pattern>`]`
- ` [stray, but: tracks base `origin/dev`]`
- ` [stray, but: delete range `stray` was not given]`
- ` [merged, but: HEAD]`
- ` [merged non-tracking, but: HEAD]`
- ` [merged, but: worktree at <absolute-path>]`

Branches checked out by any linked worktree are always retained, with the exact absolute worktree path in the last annotation. With no-detach behavior, the current branch is always retained as `HEAD`. A base takes precedence over merge deletion. Already-detached HEAD does not protect any branch. When the retained report is the last output (there are no deletion sections or later operation messages), terminate it with a blank line: the final entry or suggestion line is followed by two newline bytes.

## Spec 17

Branches omitted from detailed classification because the relevant opt-in range was not supplied remain in the plan with numbered markers. After the remote list, print the used suggestions in numeric order under:

```text
  Some branches are skipped. Consider following to scan them:
```

The marker meanings and exact suggestion texts are:

```text
    *1: Add `--delete 'merged-local'` flag.
    *2: Set an upstream to make it a tracking branch or add `--delete 'local'` flag.
    *3: Make it upstream of a tracking branch or add `--delete 'remote:origin'` flag.
```

The scope displayed by a suggestion is determined by the number of skipped entries of that suggestion kind, not by the number of configured remotes or by the number of distinct remote names. For `*1`, collect the remote name once for every skipped tracking ref carrying a remote-scoped tracking suggestion. Exactly one collected entry prints `merged:<that-remote>`; two or more print `merged:*`, even when every entry names the same remote. If no remote-scoped tracking suggestion exists but an unscoped tracking suggestion does, print `merged-local`. A merged side that was classified and has an explicit `[merged, but: delete range ... was not given]` annotation does not also receive `*1`; this applies both to a retained local side under `merged-remote:<scope>` and a retained remote side under `merged-local`. Use `*1` instead when the selected ranges cause the whole tracking classification to be skipped. This can include the selected base and its upstream: in the evaluated `--delete remote:*` fixture, `master`, `feature1`, and `feature2` and their `origin` upstream refs all have `*1`, and the suggestion is exactly `    *1: Add `--delete 'merged:*'` flag.` The same whole-classification behavior can leave an otherwise stray tracking local as `<name> *1`; when stray classification is performed but `stray` was not selected, use the explicit `[stray, but: delete range `stray` was not given]` annotation instead.

Apply `*2` to non-tracking locals excluded by `local`. Apply `*3` to a non-upstream remote ref only while iterating at least one usable base; if there are no usable base upstreams, leave such remote refs plain and print no `*3` suggestion. For the `*3` line, collect one remote name per skipped non-upstream ref. Exactly one skipped ref prints its exact remote scope, regardless of how many remotes are configured: a two-remote report whose sole skipped ref is `upstream/master` prints exactly `    *3: Make it upstream of a tracking branch or add `--delete 'remote:upstream'` flag.` Two or more skipped refs print `remote:*`, even when all have the same remote: three skipped `origin/feature-*` refs print exactly `    *3: Make it upstream of a tracking branch or add `--delete 'remote:*'` flag.` Do not print the suggestions block if no marked entry exists.

## Spec 18

After the retained plan (and its optional suggestions), print one blank line before the first nonempty deletion section. Do not insert blank lines between successive deletion sections: the next heading immediately follows the preceding section's final list item. Use these exact headings and list syntax:

```text
Delete merged local branches:
  - <local-name>
Delete merged remote refs:
  - <remote>, refs/heads/<branch>
Delete diverged remote refs:
  - <remote>, refs/heads/<branch>
Delete stray local branches:
  - <local-name>
```

Merged local-only entries use `  - <name> (non-tracking)`, and non-upstream remote entries use `  - <remote>, refs/heads/<name> (non-upstream)`. Omit an empty section entirely. Plan entries and deletion-list entries are deterministic; multiple local/deletion names are lexical. Always preserve spelling and UTF-8 branch text without truncation.

A canonical default dry-run example is:

```text
Branches that will remain:
  local branches:
    master [base]
  remote references:
    origin/master [base]

Delete merged local branches:
  - feature
Delete merged remote refs:
  - origin, refs/heads/feature
Delete branch feature (dry run).
```

## Spec 19

`--dry-run` performs the complete scan and prints the plan, but must not change HEAD, local refs, remote refs, worktrees, or repository files. Its remote update and remote deletion subprocesses also run in their dry-run modes; their simulated fetch/push output can therefore describe changes that are not applied. It never asks for confirmation. For every selected local branch, append `Delete branch <name> (dry run).` after the plan. Remote-only deletions have no corresponding `Delete branch` line because that wording simulates the local `git branch` operation.

Dry-run output for several local branches may perform those final simulated local-deletion lines in an implementation-dependent order, but all selected names must appear exactly once. All earlier report sections are stable.

## Spec 20

Without `--dry-run`, and after any required confirmation, delete every selected local branch forcefully enough to remove merged, stray, or locally edited candidates, and delete every selected remote `refs/heads/...` ref from the selected remote. A default `merged:origin` real run therefore removes both a merged local branch and `origin/<branch>`. For ordinary named-remote pairs, a local-only `merged-local` run must leave the remote ref and a remote-only range must leave the local ref. The direct-fetch path exception in Spec 14 instead selects both sides.

Successful local deletion prints Git-compatible text `Deleted branch <name> (was <abbreviated-commit>).` to standard output. Remote deletion must update the actual remote as well as the local remote-tracking view. Return 0 only after all selected operations complete; propagate a failed fetch or deletion as an error.

## Spec 21

Confirmation is enabled by default and by `--confirm`/`trim.confirm=true`. If at least one deletion is planned in a non-dry run, display the complete plan first, flush output, then prompt with text containing `Confirm?`. An explicit `y` confirms. `n` and an empty response (Enter) decline; the default is No. Declining prints `Cancelled`, changes no refs, and exits 0.

`--no-confirm`, or `trim.confirm=false`, suppresses the prompt and immediately performs the plan. If there are no deletion candidates, never prompt, even with confirmation enabled; simply print the retained-branch report and return 0.

## Spec 22

Detaching is enabled by default and by `--detach`/`trim.detach=true`. If the current local branch itself is selected, detach HEAD at that branch's tip before deleting it. In a dry run, simulate that step on standard output in this exact order:

```text
Note: switching to 'refs/heads/<branch>' (dry run)
You are in 'detached HED' state... blah blah...
HEAD is now at <seven-hex-commit> <tip commit subject> (dry run)
Delete branch <branch> (dry run).
```

The spelling `HED` and ellipses are intentional. With detaching disabled, retain the current branch, though an independently selected remote side may still be deleted. A merged tracking branch is annotated `[merged, but: HEAD]`; a merged non-tracking current branch selected by `--delete local` is annotated `[merged non-tracking, but: HEAD]`. If HEAD was already detached before invocation, no branch receives HEAD protection and no extra detachment simulation is needed.

## Spec 23

Honor Git worktree safety and repository concurrency. Never delete a branch checked out in another worktree. Scanning must remain well-defined when multiple branches share commits, branch names contain nested paths/dots/underscores/dashes/numbers/non-ASCII text, commit subjects contain Unicode, and branch sets are moderately large or change near the scan. The program must not impose short fixed buffers or ASCII-only parsing.

An unmerged branch and its upstream remain without a deletion section. Orphan/unrelated-history branches remain. A ref fetched from a non-head namespace is subject to the first-refspec translation quirk in Spec 11 rather than receiving blanket preservation. The plan must still be nonempty and structured when nothing can be deleted.

## Spec 24

For branch push-remote classification, use `branch.<branch>.pushRemote` first, then `remote.pushDefault`, then `origin` as fallback. The branch's fetch/upstream remote remains determined separately by `branch.<branch>.remote`. This distinction is required for triangular workflows and for deciding which remote copies are upstream versus non-upstream.

If any configured remote has one or more explicit `remote.<name>.push` refspecs, append the following survey block once per execution after the branch/deletion report, substituting that remote's name:

```text


Help wanted!
I recognize that you've set a config `git config remote.<name>.push`!
I once (mis)used that config to classify branches, but I retracted it after realizing that I don't understand the config well.
It would be very helpful to me if you share your use cases of the config to me.
Here's the survey URL: https://github.com/foriequal0/git-trim/issues/134
Thank you!
                
```

The block is informational and does not change the status or branch decisions. Check all remotes, not only the first, so a push refspec configured only on `upstream` names `remote.upstream.push` in this text.
