The required artifact is a single POSIX-runnable file named `executable`. It is a terminal application named **keifu**. It reads the Git repository containing the process's current working directory and, when attached to a terminal, presents an interactive Unicode commit graph. No command-line operand selects a repository; the current directory is the only input location.

## Spec 1

`executable --help` and `executable -h` must exit successfully, write nothing to standard error, end standard output with a newline, and produce exactly this UTF-8 text:

```text
A TUI tool to visualize Git commit graphs with branch genealogy

Usage: executable

Options:
  -h, --help     Print help
  -V, --version  Print version
```

Help takes precedence over later options: for example, `--help --bad-option`, repeated help flags, and the combined short-option form `-hV` all print this help and exit 0. The name in the synopsis is always the literal `executable`, regardless of the file's absolute path.

## Spec 2

`--version` and `-V` must exit 0, write nothing to standard error, and print exactly one line:

```text
keifu 0.2.3
```

The output must contain no usage or option text. A long version flag with an attached value is invalid rather than being treated as a version request. In particular, `executable --version=1` exits 2, writes nothing to standard output, and writes exactly this diagnostic to standard error, including the blank lines and trailing newline:

```text
error: unexpected value '1' for '--version' found; no more were expected

Usage: executable --version

For more information, try '--help'.
```

## Spec 3

There are no positional arguments and no options other than those in Specs 1 and 2. An unknown long option, unknown short option, or positional argument is a command-line usage error with exit status 2. The diagnostic is written to standard error and follows this form, including blank lines and the trailing newline:

```text
error: unexpected argument '--invalid-flag' found

Usage: executable

For more information, try '--help'.
```

Substitute the actual offending token, including leading dashes, for the unknown-option and positional-argument cases described in this spec. The recognized `--version` option with an attached value is instead diagnosed exactly as specified in Spec 2. Standard output is empty. Multiple invalid tokens may stop at the first one. A bare `--` ends option parsing and is accepted when it is the last token; a token after it is still rejected as an unexpected positional argument. Thus `-- --help` is an error while a lone `--` proceeds as a no-argument TUI launch.

## Spec 4

With no effective arguments, first discover a Git repository from the current working directory, walking through its parents as Git normally does. This must work at a repository root and from nested subdirectories. A normal repository with commits, branches, remote-tracking references, tags, merges, a dirty index/worktree, long or empty commit messages, or disconnected branch histories must be recognized without panic.

If discovery fails, exit 1, print nothing resembling command usage, and write a diagnostic to standard error containing both of these lines/ideas:

```text
Error: Git repository not found. Please run inside a Git repository.

Caused by:
    could not find repository at '.'; class=Repository (6); code=NotFound (-3)
```

The first line and the phrases `Git repository not found`, `Please run inside a Git repository`, and `could not find repository` are required.

## Spec 5

After successful repository discovery, an interactive terminal is required. If standard input/output are captured pipes rather than a TTY, initialization must fail promptly with exit status 1 and a nonempty standard-error diagnostic identifying a terminal/device failure (the usual platform text is `Error: No such device or address (os error 6)`). This is not a repository error and must not print `Usage: executable` or `repository not found`. Repository loading and configuration parsing must not panic before this graceful failure.

Under a PTY of ordinary size, the interface must render within roughly half a second, process single key events without requiring Enter, continuously redraw in place, and restore the terminal when it exits.

## Spec 6

The optional configuration file is `keifu/config.toml` below `XDG_CONFIG_HOME`. When `XDG_CONFIG_HOME` is unset, use `$HOME/.config` as that base. If `XDG_CONFIG_HOME` is set, do not consult `$HOME/.config/keifu/config.toml` as a substitute.

A missing or empty file is valid and uses defaults. An unreadable file, malformed TOML, or a TOML file with wrong field types must be ignored as a whole and replaced by defaults; none may prevent TUI startup. A partial valid table merges missing values with defaults.

## Spec 7

The supported TOML schema and defaults are:

```toml
[refresh]
auto_refresh = true
refresh_interval = 10
auto_fetch = true
fetch_interval = 60
```

The two booleans use TOML boolean values. Intervals are integer seconds. Clamp a valid `refresh_interval` below 1 to 1 and a valid `fetch_interval` below 10 to 10. Boundary values 1 and 10 and large values such as 999999 are accepted without overflow. When enabled, refresh local state and fetch `origin` periodically at the corresponding interval; when disabled, omit that periodic action. Disabling either or both does not alter the initial screen. Invalid syntax or types fall back without emitting a panic.

In a clean linear repository, if a new tip is committed externally, the next automatic refresh both reveals that tip and selects it; the previously selected old tip does not remain selected.

## Spec 8

The TUI uses the full terminal and reserves its final row for a status bar. Above it, draw a rounded Unicode box titled `Commits`. The remaining lower area contains rounded boxes titled `Commit Detail` and `Changed Files`.

At 80 columns by 24 rows, `Commits` occupies columns 0–79 and rows 0–15. The two lower boxes occupy rows 16–22, with `Commit Detail` at columns 0–39 and `Changed Files` at columns 40–79. Row 23 is the status bar. At 70, 80, or 100 columns by 20 rows, the commits box occupies rows 0–12, the two detail boxes share rows 13–18 horizontally, and row 19 is status. At a narrow width of 40 columns, the lower boxes stack vertically instead of splitting horizontally. The specific 25-column layout is defined in Spec 13. All unused box cells are spaces and every successfully rendered visible row is clipped to the terminal width.

Use these exact box characters and title style: `┌`, `┐`, `└`, `┘`, `─`, `│`, and for example `┌ Commits ─...┐`. Do not print a conventional scrolling log or shell prompts inside the alternate screen.

## Spec 9

At startup, harvest commits reachable from all displayed local and remote-tracking branch tips, deduplicating commit objects reached through multiple references. Include histories not reachable from the currently checked-out branch and disconnected/orphan histories. The implementation must comfortably retain and navigate at least 60 commits.

Order rows newest/topologically first while never placing a parent above its child. The current implementation's observable ordering is equivalent to walking all branch tips in Git topological/time order. Every real commit appears once, even when several names point to it. The default selection is the first displayed node. Consequently, it is the first real commit in a clean repository, but it is the synthetic uncommitted-changes row when that row exists. Selection is not visually highlighted by terminal styling; it controls the lower panels. In particular, an escape-preserving terminal capture of the initially selected `[master] Second` row in a clean two-commit repository contains no ANSI escape sequence.

The ordering of incomparable tips with equal commit timestamps is deterministic. In particular, when local branches `master` and `feature` diverge from `Add file3`, their respective equal-timestamp tips `More work on master` and `Feature work` are ordered with `master` first. The graph begins:

```text
│ ◉    [master] More work on master
│ │ ●  [feature] Feature work
│ ├─╯
│ ●    Add file3
```

The same rule puts equal-timestamp `Master commit` on `master` before `Feature 1 commit` on `feature1`, with `master` in the first lane (`◉    [master]`) and `feature1` in the second. These rows, not merely the timestamp relation, are normative: startup selects the `master` tip; from there `j` selects `Feature work`, and `j` followed by either `k` or `g` returns to `More work on master`.

## Spec 10

Each commit row begins with a graph made from two-character-wide lanes. A normal commit marker is `●`; use `◉` instead only when the commit carries the currently checked-out local branch. In detached-HEAD mode no branch commit receives `◉`. A linear history therefore has one `●`/`◉` per row and no merge-corner glyphs.

After the graph prefix, show a branch label when a reference points to the commit, then the commit's first subject line. The basic form is:

```text
│ ◉  [master] Latest message                              2026-04-13  Test     │
│ ●  Older message                                       2026-04-13  Test     │
```

Long or empty subjects must not crash rendering. Clip text by displayed terminal-cell width, not byte length, so Unicode remains valid.

## Spec 11

Allocate a new lane for a diverging ancestry when no existing lane tracks it, choosing the first reusable empty lane; release and reuse lanes after histories converge. Continued lanes use `│`, horizontal connections use `─`, and corners/tees use `╭`, `╮`, `╰`, `╯`, `├`, `┤`, `┬`, `┴`, and `┼` as their topology requires. A merge row fans from its first-parent lane toward other parent lanes, for example `◉─╮`. When parents finally converge, emit a separate connector row such as `├─╯`, `├─┴─╯`, or `├─┴─┴─╯`. Octopus merges must create one connected lane for every parent, with `┴` at middle joined lanes and a corner at the end.

The following normalized commits panel is normative for a branch with two commits merged into `branch2` after `branch2` made its own commit. `DATE` stands for the actual formatted date:

```text
┌ Commits ─────────────────────────────────────────────────────────────────────┐
│ ◉─╮  [branch2] Merge branch1 to branch2                 DATE  Test     │
│ ● │  Branch2 commit                                     DATE  Test     │
│ │ ●  [branch1] Branch1 commit B                         DATE  Test     │
│ │ ●  Branch1 commit A                                   DATE  Test     │
│ ├─╯                                                                          │
│ ●    [master] Base                                      DATE  Test     │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Spec 12

Complex graphs must remain connected and compact. This includes several simultaneous branches, sequential merges, nested branches, branches created from merge commits, crossing active pipes, criss-cross-like histories, and merges whose parent lane is already active but its commit has not yet been printed. In the latter case use a tee rather than prematurely ending that lane. Twelve concurrent branches must fit by extending the same two-column lane model, and freed lanes must be reused instead of increasing width indefinitely. Each branch-tip commit and each merge subject must remain present if within the visible commit window.

For a merge of an independent bugfix followed by a release commit, the standard-width graph portion has this shape:

```text
│ ◉      [release/v1.0] Release                                       Test     │
│ │ ●    [feature/test] Feature                                       Test     │
│ ●─┼─╮  [main] Merge bugfix                                          Test     │
│ │ │ ●  [bugfix/test] Bugfix                                         Test     │
│ ├─┴─╯                                                                        │
│ ●      Initial                                                      Test     │
```

Lane colors should remain stable along a pipe and through its connector cells; color must not change the text glyphs captured from the terminal.

## Spec 13

Adapt the right-side metadata on commit rows to the width remaining after reserving the graph's lane columns. For a compact single-lane graph, the evaluated terminal widths produce these tiers:

- At 40 columns, show no date, author, or abbreviated hash.
- At 70 columns, show the author field right-aligned, but no date or hash.
- At 80 columns, show `YYYY-MM-DD`, two spaces, and the author field, but no hash.
- At 100 columns, show date, the author field, and the seven-character abbreviated commit hash.

The author field is exactly eight display cells wide at every tier that includes it. Clip longer names to those eight cells; for example, `Test User` is rendered as `Test Use` at 70, 80, and 100 columns.

Additional lanes reduce the remaining width and therefore step down through the same tiers. For example, a sufficiently wide three-lane graph in an 80-column terminal shows author only, whereas a one- or two-lane graph can still show date plus author. The subject/branch area is clipped before the reserved right-side metadata. At 40 columns, a three-commit linear history must begin exactly as follows:

```text
┌ Commits ─────────────────────────────┐
│ ◉  [master] Third commit             │
│ ●  Second commit                     │
│ ●  First commit with a longer message│
```

At exactly 25×24, the long-branch case also clips safely. With checked-out branch `feature/very-long-name`, file `長い.txt`, and subject `Unicode 雪だるま ☃ message`, the process remains responsive and renders these visible rows at their indicated zero-based positions:

```text
0:  ┌ Commits ──────────────┐
1:  │ ◉  [feature/very-long-│
15: └───────────────────────┘
16: ┌ Commit Detail ────────┐
20: ┌ Changed Files ────────┐
23:  repo   feature/very-long
```

It emits no `index outside of buffer` diagnostic, and `q` exits normally with status 0.

## Spec 14

When one reference points to a commit, render `[name]`. When several displayed references point to the same commit, show only the currently selected one in square brackets followed by ` +N`, where N is the number of other references at that commit. Thus two references display `+1`, and nine display `+8`.

While that commit is selected, overlay a rounded `Branches` box at the right of the commits panel. It lists at most eight references, one per row, and prefixes the selected one with `▶`; unselected rows use two spaces. Put the checked-out local branch first, then the remaining names alphabetically. If more than eight references point to the commit, retain the full count in the `+N` suffix but show only the first eight names in that ordering in the box. Thus, with `master` and `label-0` through `label-7` all at one commit, the row says `[master] +8`, while the box contains `master` and `label-0` through `label-6` and omits `label-7`. The overlay may cover commit-row metadata beneath it. Changing which branch is selected changes the bracketed label and `▶`, but does not by itself check out that branch.

The `Branches` box is suppressed while the deletion `Confirm` dialog is open, even though the selected commit still has multiple names and its row retains the bracketed label and `+N` suffix. The confirmation dialog is drawn without a Branches box behind it.

At 80×24, the `Branches` box begins on zero-based row 2, rather than sharing row 1 with the selected commit. Its right border is column 77, leaving column 78 blank before the commits-panel border at column 79. Its outer width is the larger of 12 cells and six cells plus the displayed-cell width of the longest listed reference; right-align that width against column 77. Thus a longest name of 16 cells produces a 22-cell box at columns 56–77 whose top is exactly `┌ Branches ──────────┐`. These placement and sizing rules apply again after a search is confirmed or cancelled and its search overlay closes.

Local and remote-tracking names such as `feature` and `origin/feature` are both available when both references exist. A remote-only name is displayed with its remote prefix. After remote checkout has made the same-named local and remote references point to the same object, the UI folds that pair into one displayed branch item labeled `[feature ↔ origin]`. The pair does not count as two names for `+N` and, when it is the only item at the commit, does not open a `Branches` box or show a `▶ feature` row.

## Spec 15

An initialized repository with no commits still opens a valid TUI. Its commits panel is empty. `Commit Detail` contains `Select a commit` as its first interior line; `Changed Files` is blank. There is no branch/HEAD token in the footer. At 80×24 the last line is:

```text
 <repository-name>   j/k move  Enter checkout  b branch  f fetch  ? help  q quit
```

In detached-HEAD mode, retain the ordinary reachable commit graph and branch labels but use only `●` markers. The status branch token is the literal `HEAD`. The initial selection remains the first displayed real commit. Pressing `@` leaves that selection unchanged; it does not move to the detached HEAD commit.

## Spec 16

The `Commit Detail` panel describes the selected real commit in this order:

1. `Commit:` and the full lowercase 40-hex-digit object ID.
2. `Author: Name <email>`.
3. `Date:   YYYY-MM-DD HH:MM:SS`.
4. `Parent: ` followed by a seven-character parent ID when room remains and a parent exists.
5. The commit subject (the first line of its message) when room remains.

Use the available interior width and normal text wrapping. Do not render message body text after the first line, even when blank detail rows remain. For example, at 100×30 a commit whose message is `Subject line`, a blank line, then `Body text retained` displays `Subject line` in the detail panel but does not display `Body text retained`. At an 80-column split, `Commit:` occupies its own row and a 40-character ID wraps as 38 characters plus 2 on the next row. At 100 columns the left panel has enough width for `Commit: ` and all 40 digits on one row. Fields below the visible panel height are simply clipped. Changing the selected commit must immediately update this panel.

## Spec 17

The `Changed Files` panel begins with the summary

```text
N files changed  +I -D
```

followed by a blank row and then one line per available file in Git diff order:

```text
 M path/to/modified.txt +2 -1
 A path/to/added.txt +3 -0
 D path/to/deleted.txt +0 -4
```

Use status letters `A`, `M`, and `D` as shown, and support mixed additions, modifications, and deletions. Count inserted/deleted text lines. For a root commit, treat its files as additions against an empty tree. An empty commit shows `0 files changed  +0 -0`. Large counts such as `+500` remain intact. Cap collected/displayable changed-file entries at 50. The leading N still reports the total number of changed paths, but I/D are totals over the capped entries; consequently a commit adding 60 one-line files reports `60 files changed  +50 -0`. The physical box may show fewer than 50 rows because of terminal height.

## Spec 18

Represent staged and tracked-worktree changes as a synthetic row above the real history:

```text
●  uncommitted changes (N)
```

Integrate that row into the HEAD lane without disconnecting or overwriting active merge lanes. If the nearest lane is occupied, choose the closest free lane and connect it to HEAD. At 80×24, for a master history that has sequentially merged `branch1` and `branch2`, with `branch3` still active and one staged added file, the graph rows are:

```text
│ ●        uncommitted changes (1)                                             │
│ ◉─╮      [master] Merge branch2                                     Test Use │
│ │ │ ●    [branch3] Branch 3 commit                                  Test Use │
│ │ ● │    [branch2] Branch 2 commit                                  Test Use │
│ ●─┼─┼─╮  Merge branch1                                              Test Use │
│ │ │ │ ●  [branch1] Branch 1 commit                                  Test Use │
│ ├─┴─┴─╯                                                                      │
│ ●        Base                                                       Test Use │
```

When selected, its detail panel reads `Uncommitted Changes`, then `N files with changes`; the changed-files panel uses the same status/stat format as commits. Because the synthetic row is the first displayed node, it is selected at startup and these uncommitted-change details are initially visible instead of `Commit:` details for the first real commit.

A clean index and working tree produce no synthetic row and no occurrence of `uncommitted` in the interface.

## Spec 19

Normal-mode vertical navigation is:

- `j` or Down: one displayed node downward.
- `k` or Up: one displayed node upward.
- `g` or Home: first/top node.
- `G` or End: last/bottom node.
- `@`: when a local branch is checked out, move to the real commit to which that current branch points; in detached-HEAD mode, make no movement and leave the current selection unchanged.
- `Ctrl+d`: exactly ten nodes down.
- `Ctrl+u`: exactly ten nodes up.

Clamp every movement at list boundaries; do not wrap or index outside the list. Keep the selected row visible by scrolling the commit viewport, and update details/files on every move. Thus in a 60-commit linear history, one `Ctrl+d` moves selection from commit 60 to commit 50, repeated page moves reach 40 and 30, and `Ctrl+u` reverses them exactly.

## Spec 20

`R` reloads commits, branch references, and working-tree state from disk. It must reveal commits and branches created externally while the TUI is open. `g` after such a refresh reaches a newly added tip in a clean repository. Manual refresh does not preserve the previously selected real object/ref when the current checked-out branch has advanced externally; it selects that branch's new tip.

Concretely, begin with the tip `Selected before refresh` selected, externally commit `New external tip` on `master`, add `external-label` there, and dirty one tracked file. After `R`, the graph shows the synthetic `uncommitted changes (1)` row, the new commit, and the new label, while Commit Detail contains the full object ID of `New external tip`. The old tip is no longer selected, and selection does not move to the synthetic row even though it is the top displayed node.

`q` and Escape in normal mode terminate the application.

## Spec 21

Branch-oriented navigation is separate from row navigation:

- `Tab` or `]` selects the next branch position in graph order, moving to its commit as needed.
- `[` selects the previous branch position.
- `h`/Left and `l`/Right select the previous/next branch only among names on the current commit.

Within a multi-name commit, names are ordered as in the Branches overlay. These actions update the bracket label, overlay arrow, and selected commit details. At the first/last global branch position, `[`/`Tab` is a no-op rather than wrapping. At the left/right edge on one commit, h/l is a no-op rather than wrapping. All four actions are no-ops in a single-branch repository. For a linear master history with labels `feature-c` and `hotfix` on commit 3, `feature-b` on commit 2, and `feature-a` on commit 1, Tab from master selects `feature-c`; l selects `hotfix`; h selects `feature-c`; later branch jumps reach feature-b and feature-a.

## Spec 22

The normal status row starts with one space, the repository root's basename, three spaces, and the current checked-out branch (or `HEAD` when detached), followed by three spaces and these hints:

```text
j/k move  Enter checkout  b branch  f fetch  ? help  q quit
```

Clip the row at terminal width. Selection of a different branch without checkout does not change this current-branch token. The untruncated forms of the other mode-specific endings are:

```text
Esc/q close help                                                   HELP
Enter confirm  Esc cancel                                         INPUT
y yes  n no                                                       CONFIRM
<error message>    Esc/Enter close                                ERROR
```

Right-align each uppercase mode indicator one cell before the terminal edge, leaving exactly one trailing space after the indicator. Thus fixed-width HELP, INPUT, and ERROR status rows do not end with the indicator itself. Input mode is used for both branch-name entry and search. Error text is retained visibly until dismissed. Error mode has an error/red visual style; other styling may use ordinary terminal colors.

The right-aligned mode indicator has priority when an error row is too narrow. Retain the beginning of the error diagnostic ahead of the close hint; the `Esc/Enter close` hint is clipped away entirely if the diagnostic consumes its space. Specifically, after `f` in an 80-column repository named `repo` on `master` with no `origin`, the complete 80-cell status row is:

```text
 repo   master   git fetch failed: fatal: 'origin' does not appear to be  ERROR 
```

## Spec 23

`?` opens a centered rounded overlay titled `Help`. A second `?` or `q` closes only the overlay and returns to normal mode; it must not quit the application. The help overlay contains at least the following exact labels and descriptions in these groups:

```text
Navigation
  j / ↓      Move down
  k / ↑      Move up
  ] / Tab    Select next branch
  [ / S-Tab  Select previous branch
  h / ←      Select left branch (same commit)
  l / →      Select right branch (same commit)
  Ctrl+d     Page down
  Ctrl+u     Page up
  g / Home   Go to top
  G / End    Go to bottom
  @          Jump to HEAD (current branch)

Git Operations
```

At 80×24 the overlay is 48 cells wide, centered horizontally (columns 16–63), begins on zero-based screen row 4, and is clipped where the available screen ends. It is drawn above the existing commits/detail boxes. While visible, the footer uses `Esc/q close help` and the `HELP` indicator.

## Spec 24

Pressing the single `/` key opens incremental branch search and saves the previous branch/row selection. Draw a centered rounded overlay titled `Search branches`, 48 cells wide at an 80-column terminal (columns 16–63), anchored so its bottom is zero-based row 22. Its first line is two spaces, the typed query, and an underscore cursor. With no query its bottom hint is:

```text
Enter: confirm  Esc: cancel
```

With results, insert a separator, show one result per row (`▶ ` on the active result, two spaces otherwise), and show:

```text
↑↓: select  Enter: jump  Esc: cancel
```

Typed characters update a case-sensitive search over branch names, with prefix matches ranked first. Thus lowercase query `feat` finds lowercase `feature/auth` and `feature/search` and selects `feature/auth` first, while uppercase query `FEAT` finds neither. Backspace edits the query. Up/Down changes the active result and previews that result by changing the selected branch label in the graph. Enter closes search and leaves the selected matching branch/commit selected, but does not check it out. Escape closes search and restores exactly the selection that existed before `/`, even after result navigation. Search mode uses the INPUT footer.

## Spec 25

Pressing `b` on a selected real commit opens a centered 40-by-4 rounded box within the commits panel titled `New Branch Name`. Its input row starts with two spaces and displays the buffer followed by `_`. The footer changes to INPUT mode. Printable characters append to the buffer, Backspace removes one character, and Escape closes the box with no Git change.

Enter with a valid Git branch name creates a new local branch pointing at the selected commit; it does not check it out. Refresh the graph immediately, show the new name (and `+N`/Branches overlay if it shares the commit), and preserve selection on the same real commit/branch context. Names containing `/` and dots, such as `feature/mybranch` and `v1.0.0`, are valid. If Git rejects creation, enter ERROR mode. Attempting the existing name `master` must display `Failed to create branch 'master'` in the status row and leave the existing branch unchanged.

## Spec 26

In normal mode, Enter checks out the selected target and refreshes the display:

- If a selected local branch name exists, check out that branch. Update the working tree, move the `◉` marker, and change the footer's current branch.
- If the selected real commit has no selected branch reference, check out its object ID in detached-HEAD mode. The footer then says `HEAD`, no commit gets `◉`, and the working tree matches that commit.
- Preserve nonconflicting staged/worktree changes as Git checkout normally permits, and retain selection on the branch/commit that was acted upon.

Checking out a historical commit must remove files that did not yet exist; checking out a divergent local branch must likewise make its tree visible.

## Spec 27

Enter on `origin/name` attempts remote-branch checkout using local name `name`:

- If local `name` does not exist and the remote-tracking reference belongs to `origin` through its configured fetch mapping, create it at `origin/name`, configure its upstream remote as `origin`, and check it out.
- A manually installed `refs/remotes/origin/feature` reference does not satisfy that lookup when `origin` has a URL but no fetch mapping. Enter first creates local `feature` at the remote-tracking object, then fails to determine its remote. It does not configure an upstream or check out the new local branch: `master`, HEAD, and the working tree remain unchanged, and the visible label remains `[origin/feature]` rather than `[feature ↔ origin]`. The UI enters ERROR mode. For repository `repo` on `master` at 100 columns, the complete status row is:

  ```text
   repo   master   could not determine remote for 'refs/remotes/origin/feature'; class=Referenc ERROR 
  ```

- If local `name` exists at the same object, simply check it out.
- If local `name` exists but differs, force-update it to the remote-tracking object and check it out. This is required whether that local branch was current or noncurrent; divergent local-only commits/files are discarded. Do not add an upstream when this pre-existing branch lacks one: after either current or noncurrent `feature` is replaced, it remains a branch with no configured upstream.

After a successful checkout, the footer names the local branch, its local and remote references remain visible, and the working tree matches the remote target. The refreshed branch selection switches from the selected `origin/name` target to the combined local/remote item. For `feature` and `origin/feature`, the complete label is `[feature ↔ origin]`, both when a newly created local has its upstream configured and when a pre-existing local still has no upstream. As specified in Spec 14, this combined item has no Branches overlay when it is the only item at the commit.

## Spec 28

Pressing `d` while a selected non-current local branch name is active opens a centered rounded `Confirm` dialog containing exactly:

```text
Delete branch '<name>'?
```

The footer is `y yes  n no` plus the right-aligned `CONFIRM` indicator. `y` deletes the branch and refreshes the graph; `n` cancels without changing Git. Deletion removes the name from labels/dropdowns and decrements/removes the `+N` suffix. The checked-out branch must never be deleted; attempting it leaves Git and its label intact and may report an error. Confirmation acts on the selected branch name, not merely any other name at the same commit.

## Spec 29

Pressing `f` runs a fetch of remote `origin` and refreshes the repository view afterward. Newly fetched remote commits/references must become available to the graph. A fetch failure, including absence of `origin`, is reported in ERROR mode without terminating or corrupting the TUI; the existing commit graph remains visible. Preserve the selected real commit/ref or uncommitted pseudo-row through the fetch when it still exists.

For the missing-`origin` case, apply the diagnostic-versus-close-hint truncation and exact 80-column example in Spec 22; entering ERROR mode does not imply that `Esc/Enter close` remains visible at every width.

## Spec 30

The following is the canonical 80×24 shape for a repository named `repo`, on `master`, whose latest commit `Add file2` by `Test User <test@example.com>` added one one-line file and whose preceding commit is `Initial commit`. `DATE`, `TIME`, the 38+2 hex hash characters, and the repository name are dynamic; all borders, labels, spacing rules, ordering, and clipping are normative:

```text
┌ Commits ─────────────────────────────────────────────────────────────────────┐
│ ◉  [master] Add file2                                   DATE  Test Use │
│ ●  Initial commit                                       DATE  Test Use │
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
┌ Commit Detail ───────────────────────┐┌ Changed Files ───────────────────────┐
│Commit:                               ││1 files changed  +1 -0                │
│<first 38 hash characters>            ││                                      │
│<last 2 hash characters>              ││ A file2.txt +1 -0                    │
│Author: Test User <test@example.com>  ││                                      │
│Date:   DATE TIME                     ││                                      │
└──────────────────────────────────────┘└──────────────────────────────────────┘
 repo   master   j/k move  Enter checkout  b branch  f fetch  ? help  q quit
```

The real strings replace their placeholders without angle brackets. Interior text is clipped at each panel's right border. In particular, the author column in the 80-column commit list has eight display cells (`Test User` becomes `Test Use`), and a long repository/footer naturally clips later hints.

## Spec 31

For an 80×24 one-commit repository with two local names `master` (current) and `develop`, selecting `develop` and pressing `d` produces a 40-by-4 confirmation overlay at columns 20–59 and zero-based rows 10–13 inside the commits box. The selected label becomes `[develop] +1`; the commit marker remains `◉` because the current `master` name points to the same commit. The overlay is exactly shaped as:

```text
│                   ┌ Confirm ─────────────────────────────┐                   │
│                   │                                      │                   │
│                   │  Delete branch 'develop'?            │                   │
│                   └──────────────────────────────────────┘                   │
```

The branch-input overlay occupies the same coordinates and shape, substituting title `New Branch Name` and input line `  _`. These overlays do not erase the lower detail panels. Search overlays, by contrast, are bottom-anchored and may cover portions of both lower panels as described in Spec 24.

## Spec 32

The executable must remain responsive and must not panic for the combinations described above, including the 25×24 case in Spec 13, long branch names at supported widths, long commit messages, empty commits, large diffs, many changed files, many active lanes, and multiple Git actions in one session. Every successful redraw must leave a complete coherent screen: panel titles remain present, branch/commit subjects correspond to repository state, the details correspond to selection, and modal keys are interpreted by the active mode rather than leaking into normal-mode actions.
