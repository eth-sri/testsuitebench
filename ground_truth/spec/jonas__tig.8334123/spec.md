# Clarified executable specification

## Spec 1

The required artifact is a single executable file named `executable`. It is a Tig-compatible, terminal-based Git repository browser and staging client. It may invoke the harness-provided `git` command, but all argument interpretation, terminal interaction, view state, formatting, configuration parsing, and error handling described here belong to `executable`.

The program supports both launches on a controlling terminal and launches in which stdout and stderr are captured, but those arrangements do not have identical input semantics. Interactive operation uses the controlling terminal (normally `/dev/tty`) even when standard input is a pipe. When stdout and stderr are captured away from the controlling PTY while standard input remains that PTY, the PTY remains in canonical, echoing mode: input is line-buffered rather than acted on one key at a time. A bare `q` is echoed and does not exit, whereas `q` followed by Enter exits 0. Consequently each of these timed key sequences remains running at its 5- or 6-second deadline: `f`, `café`, Enter, `:save-display <path>`, `q`; `f`, `no-such-query`, Escape, `:save-display <path>`, `q`; `f`, `definitely-no-matching-file-xyz`, Escape, `q`; `f`, `empty.txt`, Enter, `:save-display <path>`, `q`; and `f`, `unterminated.txt`, Enter, `:save-display <path>`, `q`. The per-key finder, cancel, save, and final quit results described in Specs 15 and 22 are not reached in this captured-output arrangement. In an interactive arrangement that has entered noncanonical terminal mode, accept individual key presses without requiring Enter. Restore the terminal on exit and never leave stale alternate-screen or input-mode state behind. Unless a more specific rule below applies, successful informational operations return 0 and fatal initialization, directory, argument, or Git-resolution failures return 1.

Repository data must be obtained from the repository actually selected by the current directory, `-C`, or Git environment variables; output must never be hard-coded to a particular fixture. Commit IDs, branch names, authors, dates, paths, modes, sizes, messages, diffs, and file contents must reflect live Git data.

## Spec 2

`-v` and `--version` are identical global informational options. They write exactly the following two newline-terminated lines to stdout, write nothing to stderr, do not require a terminal or Git repository, ignore stdin, and return 0:

```text
tig version 2.6.0-g87c9c25
ncursesw version 6.3.20211021
```

The first encountered `-v`, `--version`, `-h`, or `--help` before a `--` separator determines the informational result. Thus version followed by help prints only version, help followed by version prints only help, and repeated or mixed forms still produce one result. These flags short-circuit later positionals, subcommands, unknown options, and invalid `+text`. In particular, the exact invocation `-C --help` treats `-C` as the no-argument Git diff/copy option rather than consuming `--help` as a directory: it returns 0, prints the main help to stdout, and writes nothing to stderr. An informational flag works before or after any recognized subcommand and with arbitrary Git pass-through options. Tokens after `--` are paths/positionals and are not interpreted as help or version flags.

## Spec 3

`-h` and `--help` are identical, return 0, write nothing to stderr, ignore stdin and repository state, and write exactly this newline-terminated text to stdout:

```text
tig 2.6.0-g87c9c25 

Usage: tig        [options] [revs] [--] [paths]
   or: tig log    [options] [revs] [--] [paths]
   or: tig show   [options] [revs] [--] [paths]
   or: tig reflog [options] [revs]
   or: tig blame  [options] [rev] [--] path
   or: tig grep   [options] [pattern]
   or: tig refs   [options]
   or: tig stash  [options]
   or: tig status
   or: tig <      [git command output]

Options:
  +<number>       Select line <number> in the first view
  -v, --version   Show version and exit
  -h, --help      Show help message and exit
  -C <path>       Start in <path>
```

Consequently `<subcommand> --help` routes to this same main help, which visibly mentions that subcommand, including the `path` operand for blame and `pattern` operand for grep. The help contains no terminal escape sequences.

## Spec 4

Before subcommand/revision processing, accept only the detached spelling `-C path` as a directory change. Change directory immediately. Multiple leading `-C` operations are applied left-to-right, so relative later paths are relative to the directory reached by the preceding one. `.` and `..` are valid. Do not shell-expand `~`; it is an ordinary path. Empty, nonexistent, and non-directory values fail with status 1 and a nonempty stderr diagnostic. Once a detached `-C` has consumed a non-option path operand, a failed change stops processing even if help or version follows. The diagnostic is exactly `tig: Failed to change directory to <supplied-path>\n` (without appending `strerror` text); for example, `/nonexistent` produces `tig: Failed to change directory to /nonexistent\n`. The attached spelling `-Cpath` is not directory syntax; it proceeds as revision input. In particular, from an empty non-repository directory the exact invocation `-Cdoes-not-exist` returns 1, writes nothing to stdout, and writes `tig: No revisions match the given arguments.\n` to stderr. A bare final `-C` is not diagnosed as a missing directory operand: it continues through revision processing. In an empty non-repository directory with captured input/output, the exact bare invocation returns 1, writes nothing to stdout, and writes `tig: No revisions match the given arguments.\n` to stderr. The exceptional two-token form `-C --help` is the pass-through/informational case specified in Spec 2, not a request to change to a directory named `--help`. A `-C` appearing after a subcommand is not a global directory change.

Accept `+N` (decimal digits, including zero and leading zeroes) as a request to initially select one-based display line N. A representable value beyond the available rows clamps to the last selectable row; zero clamps to the first. For example, in a three-commit main view `+4` and `+999` select commit 3, while `+000` selects commit 1. An overflowing decimal is ignored rather than clamped: the exact argument `+999999999999999999999` leaves the initial selection on commit 1. Placement is order-sensitive. A leading `+N` works for the default main view, and `+N` works after an already-dispatched `log`, `status`, or `blame` subcommand. It is not hoisted across a later subcommand token: the exact prefix invocations `+5 status`, `+3 status`, and `+2 blame README.md` each return 1, write nothing to stdout, write exactly `tig: No revisions match the given arguments.\n` to stderr, and never open the requested view or execute its script. The corresponding orderings `status +5`, `status +3`, and `blame +2 README.md` enter the requested view and return 0 under scripted quit. Non-decimal `+text`, bare `+`, negative-looking tokens, and `+:command` are ordinary Git revision arguments unless an earlier informational option short-circuits them. In particular, `+:echo command-ran` in a valid repository is not executed as an internal command: it returns 1, creates no saved display, and reports `tig: No revisions match the given arguments.` `--` terminates executable option recognition and separates revisions/options from paths.

## Spec 5

Recognize these case-sensitive subcommands:

- no subcommand: main commit-history view;
- `log`: full-screen detailed log view, with rendered log lines rather than commits as its selectable items;
- `show`: diff view for the supplied revision, defaulting to HEAD;
- `reflog`: reflog view;
- `blame [options] [revision] [--] path`: blame view;
- `grep [options] pattern [revision] [--] [paths...]`: repository grep view;
- `refs [patterns...]`: reference view;
- `stash`: stash view;
- `status`: worktree/index status view.

Upper- or mixed-case spellings are not aliases. An unrecognized non-option word in the default/log position is treated as a revision expression, not as a distinct “unknown command”; if it resolves to nothing, fail nonzero with a diagnostic containing `No revisions match the given arguments`. `blame` without a path and `grep` without a pattern fail nonzero. Unknown options such as `--invalid-flag`, `--definitely-not-a-real-option`, or invalid short options fail nonzero with nonempty diagnostic output when no earlier informational flag applies.

The explicit `log` view begins with detailed commit output such as `commit <full-sha>` and uses a footer of the form `[log] <full-sha> - line N of M`. Its `+N` selects rendered line N; it does not select the Nth commit. In the three-commit fixture, `log +2` retains the HEAD commit as footer context and produces `[log] <HEAD-sha> - line 2 of 36` rather than a `[main]` footer for commit 2.

## Spec 6

Any operation that needs the TUI must open a controlling terminal for input. If none is available, return 1 promptly and write `tig: Failed to open tty for input` (the substring `Failed to open tty` is mandatory) to stderr. This applies to a normal launch, explicit views, and `+N` without help/version. Do not hang waiting on captured or `/dev/null` stdin. Help and version bypass terminal initialization.

Redirected-input dispatch is based on stdin not being a terminal, not on whether any bytes can be read. Thus empty `/dev/null` is input redirection and is not equivalent to terminal stdin. With a controlling terminal and stdin attached to empty `/dev/null`, a launch without an explicit view opens an empty pager, including launches carrying `+N`, revisions, traversal options, or path arguments. A saved 80-by-24 display has a blank body and a footer beginning `[pager]` and ending `0%`; scripted quit returns 0. Configuration is still loaded and its diagnostics are still emitted, but the initial view remains this pager. This rule also applies in an empty repository: a save script runs and captures the empty pager rather than failing revision resolution. Scripted refresh, search, and `:view-close-no-quit` operate on that pager; `:view-tree` opens the HEAD tree rather than acting on a synthetic main row.

There are explicit-subcommand distinctions for the same empty `/dev/null` input. `show`, including `show --no-patch HEAD` and `show HEAD~1 -- path`, opens an empty diff whose saved footer begins `[diff]` and ends `0%`, and scripted quit returns 0. With otherwise valid operands, each of `blame`, `grep`, `refs`, `reflog`, `stash`, and `status` instead stops before script or interactive-key processing, returns status 1, creates no saved display, and writes exactly `tig: Ignoring stdin.\n` to stderr. This includes an empty or no-match grep pattern, grep options such as `-i` and `-w`, and `+N` supplied to blame or status. No editor is launched and no status staging, unstaging, or revert operation occurs. These redirected-input rules take precedence over normal initial repository-view selection and over the normal view behaviors in Specs 13 and 16–21.

Commands can still switch away from an initial empty pager. In the exact default launch with empty `/dev/null`, scripted `:view-diff` replaces the pager with a single full-screen diff for HEAD; the saved display contains only the `[diff]` footer, not a retained `[pager]` or `[main]` pane. Conversely, interactive keys are interpreted in the pager context. The exact key sequences `f`, `café`, Enter, `:save-display <path>`, `q` and `f`, `no-such-query`, Escape, `:save-display <path>`, `q` do not enter or cancel the main-view finder and leave the process running beyond 12 seconds.

When nonempty stdin is piped while a controlling terminal exists, enter pager mode rather than discarding input. Accept text, UTF-8, long-line, large, binary, CRLF, Git log/show/diff/blame/status output, raw commit records, or newline-separated commit IDs without crashing. Character rendering follows the active locale: in the C locale, the exact first input line `λ日本語\r\n` is saved as `l???`; a UTF-8 locale preserves valid UTF-8. `show --stdin` displays commits named on stdin, and `--stdin`/`--no-walk` are forwarded consistently. If a pipe is supplied without a controlling terminal, a clean status 1 tty diagnostic is acceptable.

## Spec 7

Honor normal Git discovery, including `.git` directories, bare repositories, linked worktrees whose `.git` is a file, nested repositories, shallow clones, submodules, orphan/unborn branches, and `GIT_DIR` plus `GIT_WORK_TREE`. Honor `HOME`, `XDG_CONFIG_HOME`, `TIGRC_USER`, `TIGRC_SYSTEM`, `GIT_CONFIG_NOSYSTEM`, `LC_ALL`/`LANG`, `TZ`, `TERM`, `LINES`, and `COLUMNS`. An explicit empty `TIGRC_SYSTEM` or `TIGRC_USER` disables that config. `COLUMNS` and `LINES` determine the rendered viewport when supplied; otherwise query the terminal. Time formatting must respect `TZ` and locale while remaining valid under C and UTF-8 locales.

The program must remain responsive for an empty repository, an empty commit, many commits/files, merges and octopus merges, very deep directories, a 10 MiB file, very long filenames/messages/arguments/config lines, unreadable or corrupt Git metadata, symlinks, executable files, binary data, mixed line endings, Unicode authors/content/paths, spaces, punctuation, emoji, and non-UTF-8 input. It must not abort, overflow, or interpret argument/config text as shell syntax unless a documented external command explicitly requests a shell. Valid UTF-8 is preserved under a UTF-8 locale such as `C.UTF-8`; the plain C locale has the lossy rendering described in Specs 6, 10, 14, and 19.

## Spec 8

The TUI is a full-screen character-cell application. Each visible view owns one footer/status row. A single view uses all rows except its footer; a default horizontal split assigns one third of the available rows to the upper view and two thirds to the lower view, counting each pane's footer. At 24 rows this produces an 8-row upper pane and a 16-row lower pane. Fill unused body rows with blanks. Text is clipped at the right edge by display width (not byte count); under a UTF-8 locale valid UTF-8 characters remain intact. Default list dates use `YYYY-MM-DD HH:MM +ZZZZ`. Views whose rows include commit IDs, such as blame and reflog, use seven hexadecimal characters, while footers and diff headers use the full 40-character object ID. The default main rows omit commit IDs entirely.

Footers ordinarily have the form `[view] context - item-kind current of total`, padded with spaces, with a right-aligned integer percentage when applicable. At end-of-input show `100%`. The synthetic uncommitted main row is an explicit exception: when selected its footer is exactly `[main] Untracked changes` followed by padding and `100%`, without `commit N of M`. Partial tree progress counts the directory header as both a visible and total logical row and truncates the resulting integer percentage: an 80-by-24 root tree showing its header and 21 of 50 files reports `43%`. Examples of required forms are `[main] <sha> - commit 1 of 3`, `[tree] <selected-entry-object-id> - file 1 of 4`, `[blob] README.md - line 1 of 5`, `[grep] file.txt - line 1 of 13`, `[refs] All references`, `[reflog] HEAD@{0} - reference 1 of 2`, and `[stash] stash@{0} - stash 1 of 1`. Selection is represented using terminal attributes, not extra printable marker characters, so plain snapshots retain column alignment.

## Spec 9

All scrollable views support Up/Down and `k`/`j` for one item, Home for the first, End for the last, PageUp/Ctrl-B and PageDown/Ctrl-F for pages, command-line `+N`, and in-range internal `:N` for an absolute line. `g` is the generic grep-view key from the next paragraph, not a first-line alias. In main, `G` toggles `commit-title-graph` rather than moving to the last line; a scripted literal `G` on the initial row leaves that row selected, so a following scripted `j` selects commit 2 rather than attempting to move beyond commit 3. Ordinary navigation and non-overflowing command-line `+N` clamp at bounds, scroll the viewport to keep the cursor visible, update the footer, and never crash. Internal `:N` instead changes selection only when N names an existing logical row: in a three-commit main view `:2` and `:3` select those commits, while `:4` and the exact `:99999` leave commit 1 selected. During ordinary interactive input, attempting to move down from the final logical row displays exactly `Cannot move beyond the last line`, and attempting to move up from the first displays exactly `Cannot move beyond the first line`. These notifications also apply in an already-open blob reached again from grep and at the end of a stage diff. A `TIG_SCRIPT` key line immediately followed by `:save-display` is an exception: `k` on the first row and `j` after `:3` in a three-commit main view clamp at the boundary, but the saved screen contains the ordinary main footer and neither boundary notification. Enter performs the view-specific open action. `<` goes back in view/path history. `q` closes the focused child view; on the last view it exits. Tab changes focus between split panes. `R`/F5 refreshes live Git data without losing a valid selection. Unknown/unbound keys leave the view alive.

The generic view keys are `m` main, `d` diff, `l` log, `L` reflog, `t` tree, `f` file finder/blob action as context dictates, `b` blame, `r` refs, `s` or `S` status, `c` stage, `y` stash, `g` grep, `p` pager, and `h` help. `O` and `:maximize` maximize/restore the focused pane. Colon introduces an internal command prompt; slash introduces a regular-expression search. `n` moves to the next match and `N` to the previous, wrapping when configured. An interactive failed search uses `No match found for '<pattern>'` as the transient footer. A search issued as a `TIG_SCRIPT` `:/pattern` command behaves differently at the following save: a successful search moves the selection, but neither success nor failure leaves a search-result message in the display captured by the next `:save-display`; the ordinary view footer is captured instead.

## Spec 10

The default main view lists commits newest first using live Git revision traversal. When the launch reaches the main view, an initialized repository with no commits returns 1, creates no saved main display, and writes `tig: No revisions match the given arguments.` after terminal teardown; the redirected-input dispatch in Spec 6 instead reaches the empty pager and takes precedence over this main-view rule. If tracked or untracked worktree changes exist in a repository with history, expose a synthetic first entry labeled `Untracked changes`, authored `Not Committed Yet`, so it can be selected and diffed; its footer is the count-free exception specified in Spec 8. It is not a real tree. A scripted `:view-tree` while this entry is selected keeps the main view intact, returns 0, and leaves no `No tree exists for this commit` message in the following saved display. Each ordinary commit row is:

```text
YYYY-MM-DD HH:MM +ZZZZ Author graph [references] subject
```

Columns are aligned across rows. Show the configured author/committer identity, decorated local branches/tags, and complete subject up to the viewport width. A checked-out local branch is decorated as `[<branch>]`, for example `[master]`; never render the Git-log spelling `[HEAD -> master]`. This same bracketed checked-out-branch form is used in main, reflog, and other list views. Main rows contain no abbreviated ID by default; the selected commit’s full ID appears only in the footer. A normal linear commit uses graph marker `o`, a root uses `I`, and a merge uses `M`. The initial cursor is the first commit unless a non-overflowing `+N` selects another as specified in Spec 4. Enter or `d` opens that commit’s diff in a lower split; `q` returns to the list. The colon command `:view-diff` has distinct geometry: from a single main view it replaces main with one full-screen HEAD diff, so the saved screen contains a `[diff]` footer and no `[main]` footer. The view must display at least 50 commits without truncating the underlying list.

Both graph engines selected by `set main-view-commit-title-graph = v1` or `v2` must render ancestry lanes correctly. With a UTF-8 locale, UTF-8 mode uses `│─┐┘┴┬` connectors; ASCII mode uses `|-.\'` equivalents. Lanes remain aligned through parallel branches, deep histories, interleaved merges, first-parent boundaries, and octopus merges. Ignoring the date/author prefix and decoration/subject suffix, the UTF-8-locale topology fragments are:

- linear: `o`, `o`, `I`;
- one side branch: `M─┐`, `│ o`, `I─┘` (ASCII `M-.`, `| *`, `I-'`);
- a five-commit side branch: `M─┐`, five rows of `│ o`, `I─┘`;
- three-way v1 octopus: `M─┐─┐`, `│ │ o`, `│ o │`, `o │ │`, `I─┴─┘`;
- three-way v2 octopus: `M─┬─┬─┐`, `│ │ │ o`, `│ │ o │`, `│ o │ │`, `I─┴─┴─┘`;
- consecutive merged branches in v1 may reuse the side lane (`M─┐ ... M─┐ ... I─┘`), while v2 retains open lanes (`M─┐ ... M─│─┐ ... I─┴─┘`);
- interleaved main work uses `o │` while a side lane remains open.

Boundary-limited history omits parents outside the selected range without inventing connectors.

Forcing `line-graphics = utf-8` while `LC_ALL=C` does not preserve those connectors. In the tested side-branch history, v1 renders graph fragments `???`, two `| ?` rows, and `?-+`; v2 renders `?-?`, two `| ?` rows, and `?-?`. In the tested octopus history, v1 renders `?????`, `| | ?`, `| ? |`, `? | |`, and `?-+-+`; v2 renders `?-+-?`, the same three interior fragments, and `?-+-?`.

## Spec 11

When the launch reaches a repository view, accepted revision and Git-option spellings not owned by the UI must be passed through to the appropriate Git operation, preserving order, spelling, equals values, and arguments. Support single revisions, full/short hashes, branch/tag names, `HEAD`, `HEAD~N`, `HEAD^N`, `A..B`, `A...B`, exclusions, multiple revisions, and paths following `--`. Empty redirected input can select the empty pager or diff first as specified in Spec 6; in that case these arguments do not force repository content into the saved input view.

The accepted pass-through surface includes revision selection/traversal (`--all`, `--branches`, `--remotes`, `--tags`, `--glob`, `--exclude`, `--first-parent`, `--merges`, `--no-merges`, `--min-parents`, `--max-parents`, `--no-min-parents`, `--no-max-parents`, `--reverse`, `--parents`, `--children`, `--topo-order`, `--date-order`, `--author-date-order`, `--full-history`, `--dense`, `--sparse`, `--simplify-merges`, `--simplify-by-decoration`, `--ancestry-path`, `--left-right`, `--cherry-mark`, `--cherry-pick`, `--walk-reflogs`, `--no-walk`, `--max-count=<n>`, and `--skip=<n>`); filters (`--since`/`--after`, `--until`/`--before`, `--author`, `--committer`, `--grep`, `--invert-grep`, `--all-match`, `-i`, `-E`, `-F`, `-P`); and output/diff controls (`--graph`, `--patch`, `--no-patch`, `--stat`, `--numstat`, `--shortstat`, `--summary`, `--patch-with-stat`, `--name-only`, `--name-status`, `--full-diff`, `--abbrev-commit`, `--no-abbrev-commit`, `--abbrev`, `--pretty`, `--format`, `--oneline`, `--date`, `--relative-date`, `--encoding`, `--decorate`, `--no-decorate`, `--show-notes`, `--notes`, `--no-notes`, `--show-signature`, `--submodule`, `-U`/`--unified`, `--function-context`, `-M`/`--find-renames`, `-C` when used as a Git diff option after dispatch, `--find-copies`, `--no-renames`, `-w`, `-b`, `--ignore-space-change`, `--ignore-all-space`, `--ignore-blank-lines`, `--ignore-submodules`, `--textconv`, `--no-textconv`, `--ext-diff`, `--no-ext-diff`, `--minimal`, `--patience`, `--histogram`, `--diff-algorithm`, `--word-diff`, `--word-diff-regex`, `--color-words`, `--color-moved`, `--no-color-moved`, `--color`, and `--no-color`). For `--max-count` and `--skip`, the equals spelling is required: `--max-count=1 --skip=1` selects the second commit, while the exact spelling `--max-count=1 --skip 1` returns 1 and reports `tig: No revisions match the given arguments.` Empty equals values must not crash. Options before help/version may be accepted without consulting Git because the informational result wins.

## Spec 12

When populated from Git rather than selected as the empty redirected-input view in Spec 6, the diff/show view renders Git’s complete commit and patch information. For a commit, show `commit <full-sha>`, then a `Refs:` row whenever Git supplies a reference or describe label for that commit, followed by `Author:`, `AuthorDate:`, `Commit:`, and `CommitDate:`, the indented commit message, `---`, diffstat, and unified patch. The `Refs:` row is mandatory for a decorated checked-out HEAD—including ordinary, long-message, empty, and merge commits—and begins `Refs: [<branch>]`; for example, an observed tagged history rendered `Refs: [master], v1-2-g96b31aa`. An undecorated commit has no `Refs:` row. Preserve blank lines and standard Git markers such as `diff --git`, `new file mode`, `deleted file mode`, `index`, `---`, `+++`, `@@`, `+`, `-`, `Binary files ... differ`, and `\ No newline at end of file`. Wrap a long commit-message line at the available display width rather than corrupting later rows. Empty commits and merge commits still show correct metadata and message. In repository-view dispatch, `show <revision>` uses exactly that revision and path filters constrain displayed changes.

When diff is opened from a blame line for the working tree, label it `Changes to '<path>'`; when opened from a commit show the commit identity. The footer is `[diff] <context> - line N of M` with progress. Respect unified context, whitespace, word-diff, stat, patch/no-patch, rename/copy, binary, color, and algorithm options by forwarding them to Git and displaying the resulting semantics.

## Spec 13

Blame view accepts a worktree path and optionally a revision such as a hash, branch, or `stash@{0}`. Render one source line per row with aligned columns:

```text
abcdef0 Author Name YYYY-MM-DD HH:MM +ZZZZ   Nx source text
```

Use the commit responsible for that line, author or configured date identity, one-based line number, and exact file content. The author field is left-aligned to the widest displayed author, while the line-number field is right-aligned with a minimum width of three characters. There is one separator space before that field and none between its last digit and the literal saved-display separator `x`. Thus line 1 after a date ending in `+0000` is rendered as `+0000   1x`, and line 10 as `+0000  10x`; do not use a two-character minimum merely because the file has fewer than 100 lines. The footer is `[blame] <full-sha>:<path> - line N of M`. `+N` initially selects N. End selects the last line. Enter opens the selected change’s diff in a horizontal split; in a 24-row terminal the upper blame pane occupies rows 1–8 including its footer and the lower diff pane rows 9–24 including its footer. The newly opened diff selects the corresponding patch line rather than its first row (an observed first-line blame entry opened at `[diff] Changes to 'main.c' - line 18 of 26`). Comma visits the corresponding parent version and `<` restores the prior blame state and selection. `m` switches to the unfiltered main history.

Include uncommitted worktree lines: identify them with the null/uncommitted blame identity (`0000000`/`Not Committed Yet` semantics), include their current text, and let Enter show the working-tree diff. Handle multiple authors, Unicode names, author timezone offsets, renamed/history paths, stash revisions, and files with or without final newline.

## Spec 14

Tree view (`t`) displays the selected commit’s tree, initially its root, with header `Directory path /`. Directories sort before files in name mode; names sort byte/locale-stably as Git provides. A directory row uses `drwxr-xr-x`, a normal blob `-rw-r--r--`, an executable blob `-rwxr-xr-x`, and a symbolic link `lrwxrwxrwx`. Ordinary rows contain mode, last author, commit date, and name; only normal and executable blob rows contain an exact decimal byte size (do not abbreviate 10485760). These are compact, data-width-driven table fields, not fixed arbitrary gaps: author is left-aligned to the widest displayed author, the regular-blob size is right-aligned to the widest displayed decimal size, and adjacent populated fields have one separating space. Directory and symbolic-link rows leave the whole size field blank. For example, with `Test User` and a two-digit size column, rows are `drwxr-xr-x Test User    2026-04-25 05:07 +0000 docs`, `lrwxrwxrwx Test User    2026-04-25 10:00 +0000 link.txt`, and `-rw-r--r-- Test User 15 2026-04-25 10:00 +0000 target.txt`; with an eight-digit size column they include `-rw-r--r-- Test User 10485760 2026-04-25 10:00 +0000 large.bin` and `-rw-r--r-- Test User        6 2026-04-25 10:00 +0000 small.txt`. Nested directories update the header to paths such as `/docs/api/` and include a synthetic parent row whose author, size, and date fields are all blank, with `..` aligned in the name column; one observed row is `drwxr-xr-x                                    ..`. For an ordinary selected entry, the tree footer context is that entry’s full Git object ID—not the commit ID whose tree is being browsed. Thus selecting a directory uses its tree object ID, while selecting a file uses its blob object ID. The special empty-tree footer described below remains an exception.

Enter on a directory descends; `<` goes to its parent and restores sensible selection. Enter on a file opens blob view in the default one-third/two-thirds split with tree retained. Thus a 24-row split can show 14 of a 15-line blob and report `93%`. A scripted `b` or `e` on a selected directory leaves the tree visible; the following `:save-display` contains neither `Blame only supported for files` nor `Edit only supported for files`. The root of an empty commit is not rendered as `Tree is empty`: after `Directory path /` it contains the exact synthetic row `  ..` and its footer is `[tree] Files in /` with `100%`. Tree state must correspond to the selected historical commit, not always HEAD. Handle 50+ entries with scrolling/progress, deep nesting, special/Unicode names, symlinks, executable modes, submodules/worktrees, and sorting toggled by `:toggle sort-field`. Under `LC_ALL=C`, Git-quoted non-ASCII path bytes remain quoted in this view: a name beginning `long ☕ ` is displayed beginning `"long \342\230\225 `, while its exact size still appears as `10240000`. A command-line directory path opens the appropriate subtree; a file path filters history to that file.

## Spec 15

Blob view displays the exact bytes of the selected blob as terminal-safe text. Preserve UTF-8 and line boundaries, do not invent a source line for an empty file, and count a final unterminated line correctly. Its footer is `[blob] path - line N of M`; cursor motion updates N and `+N` is applied when the blob first opens. A file opened from tree/grep appears in a split unless the calling context replaces the current view. A direct finder selection may replace the current view.

Long lines must be clipped safely by default and visually wrapped when `wrap-lines = yes`, while navigation remains based on logical source lines. Binary blobs must not crash or corrupt terminal control state. Refresh reloads the blob. Opening blame from a blob selects the same file and logical line. Resolve `revision:path` with Git so branches and old commits show historical content rather than the worktree copy.

## Spec 16

When grep dispatch is not preempted by redirected input as specified in Spec 6, `grep` delegates matching semantics to Git grep and supports regex patterns, `-i`, `-w`, `-E`, `-F`, `-P`, `-n`, `-p`, an optional revision, and path/directory restrictions after `--`. Group matches under a filename header and render each match with the literal saved-display separator `x`, for example:

```text
file1.txt
  1x function search_pattern() {
  2x     let pattern = "test";
```

Revision results retain enough `revision:path` identity to open the historical blob. Case-insensitive search includes all case variants; word matching excludes partial words. Filename headers count as logical grep rows: one header plus two matches produces `[grep] file1.txt - line 1 of 3`. An empty pattern and a no-result search both produce an entirely blank body and only the padded `[grep]` footer with `0%`; they do not display `No matches found`. Down changes the selected result/footer. Enter opens the selected file in a blob split but initially selects blob line 1, not the matched source line; the observed sole match on source line 2 produced `[grep] src/app.txt - line 1 of 2` and `[blob] src/app.txt - line 1 of 3`. `+N` selects the requested grep row.

From grep, `:edit` passes the one-based selected match ordinal rather than the source line number. With a sole match on source line 2 of `src/app.txt`, it invokes the selected editor with the two arguments `+1` and `src/app.txt`. Correctly quote paths for the child process without altering what the editor receives.

## Spec 17

When refs dispatch is not preempted by redirected input as specified in Spec 6, refs view lists local branches, remote branches, tags, and other requested references with heading `All references` by default. The heading is not centered in the viewport: its first `A` is aligned with the first character of the short-reference-name column below it. Consequently its leading-space count varies with the preceding date/author column widths (in the fixed 80-column fixture, the heading begins at column 34 and has exactly 33 leading spaces). Each row contains date, author, a padded short reference name, and target commit subject. Decorations and ordering must be deterministic. Accept positional reference operands such as `refs/heads` and `refs/tags`; compatibility behavior for that pair is still the complete `All references` listing. Flags such as `--branches`, `--remotes`, `--tags`, and `--all` are accepted and forwarded where used. It must show multiple refs pointing at one commit, annotated/lightweight tags as applicable, and branches checked out in linked worktrees. Its footer starts `[refs] All references`; `+N` selects the Nth reference. Enter opens that reference’s history/diff as appropriate, search/filter works, and refresh rereads changed refs without moving the heading away from the reference-name column.

## Spec 18

When reflog dispatch is not preempted by redirected input as specified in Spec 6, reflog view shows `git reflog` entries newest first with seven-character ID, decorations, and reflog subject, for example `d86a050 [master] reset: moving to HEAD`. The footer identifies `HEAD@{N}` and `reference current of total`. Accept `--all` and `--walk-reflogs`. `L` opens this view from another view. Empty reflogs render an empty but valid view.

When stash dispatch is not preempted by redirected input as specified in Spec 6, stash view shows stashes newest first with date, author, and stash subject such as `On master: Work in progress`. Its footer identifies `stash@{N}` and position. `y` opens it. Enter opens the selected stash’s complete diff in a child diff view. `+N` clamps/selects correctly even if larger than the stash count.

## Spec 19

When dispatch reaches status rather than rejecting redirected stdin as specified in Spec 6, status view reflects both index and worktree and begins with either `On branch <name>` or `Initial commit` on an unborn branch. When the current branch tracks an equal upstream, use the exact combined header `On branch <name>. Your branch is up-to-date with '<remote>/<upstream>'.`; analogous ahead/behind states report their counts. It always displays these sections in order:

```text
Changes to be committed:
Changes not staged for commit:
Untracked files:
```

The header and three sections are consecutive logical rows: do not insert blank rows before or between section headings. Under each section list status letter plus path: `A`, `M`, `D`, `R`, or `?` as appropriate. A real status letter is in column 1 and is followed by exactly one space and the path, for example `M main.c`, `A staged.txt`, or `? untracked.txt`; do not indent these rows. If a section is empty, show the deliberately different two-space indentation `  (no files)`. Preserve spaces in names and preserve Unicode under a UTF-8 locale. Under `LC_ALL=C`, a non-ASCII character in a status path is replaced by `?`; the exact untracked path `untracked ☕.txt` is rendered `? untracked ?.txt`. A clean or unborn repository still shows all sections when `status` is launched explicitly, even though the empty default main launch fails as specified in Spec 10. The default footer is `[status] Nothing to update`; selection-specific footers explain the available stage/unstage action. `+N` selects by display row, refresh recomputes branch and file states, and linked worktrees show their own branch and files.

Enter on a staged or unstaged file opens a stage/diff pane for exactly that side. Interactive search in status/main/diff/blob views is regex-capable, moves between matches with `n`/`N`, wraps at ends, and uses the transient failed-search footer described in Spec 9 without destroying the underlying view. Scripted search snapshots follow Spec 9.

## Spec 20

Once status and stage views have actually been reached rather than rejected by Spec 6, stage view displays the exact staged diff for “Changes to be committed” and exact unstaged diff for “Changes not staged,” including diffstat, multiple hunks, additions/deletions, new/deleted/renamed files, binary markers, and no-newline markers. Its retained upper status pane follows Spec 19 exactly: the branch header and section headings remain consecutive, and real `M`/`A` rows begin in column 1 even for no-final-newline and binary-file diffs. In the default horizontal split, one third of the terminal rows belong to the upper status pane and two thirds to the lower stage pane, counting each pane's footer; at 24 rows this is exactly 8 upper rows and 16 lower rows. Maximizing expands the stage pane, and closing returns to status. Enter on a diff line jumps to the corresponding file/hunk. Hunk navigation and scrolling update `[stage] ... - line N of M`. Both N and M count every logical diff row, including diffstat, its summary and blank separator, file headers, hunk headers, context, removal, and addition rows. End selects M of M and reports `100%`; a further downward movement preserves that count and displays `Cannot move beyond the last line`. In an observed stage diff this transition was from `[stage] ... - line 23 of 23` to that exact notification.

Pressing `u` on an unstaged file/hunk stages it into the index without modifying worktree content; on a staged item it removes it from the index while preserving worktree content. This must work for one or multiple hunks and leave `git diff --cached` and `git diff` with exactly the appropriate changes. After every mutation, refresh both panes and their empty sections.

## Spec 21

Fine-grained staging operates on unified patches:

- `1` stages only the selected changed line while leaving other changed lines unstaged. If the cursor is on a new-file summary rather than a selectable changed line, leave the index untouched and report `Please select a change to stage`.
- `2` stages only the selected independently splittable portion of a hunk, leaving later portions unstaged. On the `new file mode` row of a staged new file, it instead leaves the index untouched and displays no partial-chunk notification. In the fixed 80-by-24 two-line-new-file fixture, the following saved screen retains the ordinary footer `[stage] Staged changes to 'new-file.txt' - line 5 of 11` with `100%`.
- Backslash (`\`) splits a hunk at separable change groups and redraws the resulting chunks without displaying a split-count notification. In the fixed two-change fixture, splitting at `FIRST CHANGE` changes the ordinary footer from `[stage] Unstaged changes to 'README.md' - line 13 of 21` with `66%` to `[stage] Unstaged changes to 'README.md' - line 13 of 25` with `56%`; the index remains empty and the worktree remains unchanged. If splitting is impossible report `The chunk cannot be split`.
- `!` requests reverting the selected unstaged change and displays an `Are you sure?` confirmation. `y` restores content from the index and clears the diff; `n` cancels without changing the file.

Patch application must preserve context and generate a valid index. It must never stage unrelated hunks or alter the worktree for stage/unstage operations.

## Spec 22

Pressing `f` from the main context opens a file finder populated from the selected commit’s recursively tracked files. Display one repository-relative path per row and footer `[finder] file current of total`, followed by prompt `Find file: <query>`. With no query, paths are sorted lexically. Typed Unicode text filters immediately using fuzzy ordered-character matching (so `src` can match `docs/reference.md` as well as paths containing literal `src`). Backspace refilters; Up/Down moves within results. With no matches, show no rows and the literal footer `[finder] file 1 of 0`.

Escape and Ctrl-C cancel and restore the previous main screen. Enter replaces the finder with blob view for the selected file. Unicode filenames such as `café.txt`, `Привет.md`, and `日本語.txt` must display and open unchanged.

## Spec 23

Interactive help opened by `h` or `:view-help` is distinct from CLI help. With default configuration it has exactly 114 logical content rows. In its aligned binding rows, the right edge of the key field is column 28, the request begins in column 30, and a description, when present, begins in column 57. Thus the reflog row has 27 leading spaces and is exactly `                           L view-reflog                Show reflog view`. The default corpus is exactly the following; terminal clipping follows Spec 8:

```text
Quick reference for tig keybindings:
[-] Collapse all sections

[-] generic bindings
View switching
                           m view-main                  Show main view
                           d view-diff                  Show diff view
                           l view-log                   Show log view
                           L view-reflog                Show reflog view
                           t view-tree                  Show tree view
                           f view-blob                  Show blob view
                           b view-blame                 Show blame view
                           r view-refs                  Show refs view
                        s, S view-status                Show status view
                           c view-stage                 Show stage view
                           y view-stash                 Show stash view
                           g view-grep                  Show grep view
                           p view-pager                 Show pager view
                           h view-help                  Show help view
View manipulation
                     <Enter> enter                      Enter and open selected line
                           < back                       Go back to the previous view state
         <Down>, <Ctrl-N>, J next                       Move to next
           <Up>, <Ctrl-P>, K previous                   Move to previous
                         ',' parent                     Move to parent
                       <Tab> view-next                  Move focus to the next view
                     R, <F5> refresh                    Reload and refresh view
                           O maximize                   Maximize the current view
                           q view-close                 Close the current view
                 Q, <Ctrl-C> quit                       Close all views and quit
Cursor navigation
                           k move-up                    Move cursor one line up
                           j move-down                  Move cursor one line down
                 <PageUp>, - move-page-up               Move cursor one page up
         <PageDown>, <Space> move-page-down             Move cursor one page down
                    <Ctrl-U> move-half-page-up          Move cursor half a page up
                    <Ctrl-D> move-half-page-down        Move cursor half a page down
                      <Home> move-first-line            Move cursor to first line
                       <End> move-last-line             Move cursor to last line
Scrolling
          <Insert>, <Ctrl-Y> scroll-line-up             Scroll one line up
          <Delete>, <Ctrl-E> scroll-line-down           Scroll one line down
                <ScrollBack> scroll-page-up             Scroll one page up
                 <ScrollFwd> scroll-page-down           Scroll one page down
                           | scroll-first-col           Scroll to the first line columns
                      <Left> scroll-left                Scroll two columns left
                     <Right> scroll-right               Scroll two columns right
Searching
                           / search                     Search the view
                           ? search-back                Search backwards in the view
                           n find-next                  Find next search match
                           N find-prev                  Find previous search match
Misc
                           e edit                       Open in editor
                           : prompt                     Open the prompt
                           o options                    Open the options menu
                    <Ctrl-L> screen-redraw              Redraw the screen
                           z stop-loading               Stop all loading views
                           v show-version               Show version information
Option toggling:
                           I :toggle sort-order
                           i :toggle sort-field
                           # :toggle line-number
                           D :toggle date
                           A :toggle author
                           T :toggle committer
                           ~ :toggle line-graphics
                           F :toggle file-name
                           W :toggle ignore-space
                           X :toggle id
                           $ :toggle commit-title-overflow
                           % :toggle file-filter
                           ^ :toggle rev-filter
[-] search bindings
View manipulation
                    <Ctrl-C> view-close                 Close the current view
Searching
  <Down>, <Ctrl-N>, <Ctrl-J> find-next                  Find next search match
    <Up>, <Ctrl-P>, <Ctrl-K> find-prev                  Find previous search match
[+] main bindings
[+] diff bindings
[+] reflog bindings
[+] refs bindings
[+] status bindings
[+] stage bindings
[+] stash bindings
[-] pager bindings
Internal commands:
                           @ :/^@@
[-] toggle bindings
Toggle keys (enter: o <key>):
                           . line-number                Toggle line numbers
                           D date                       Toggle dates
                           A author                     Toggle author
                           T committer                  Toggle committer
                           ~ line-graphics              Toggle graphics
                           g commit-title-graph         Toggle revision graph
                           # file-name                  Toggle file names
                           * file-size                  Toggle file sizes
                           W ignore-space               Toggle space changes
                           l commit-order               Toggle commit order
                           F commit-title-refs          Toggle reference display
                           C show-changes               Toggle local change display
                           X id                         Toggle commit ID display
                           % file-filter                Toggle file filtering
                           ^ rev-filter                 Toggle revision filtering
                           $ commit-title-overflow      Toggle commit title overflow display
                           d status-show-untracked-dirs Toggle untracked directory info
                           | vertical-split             Toggle view split
```

Expanding every section replaces the seven collapsed rows for main, diff, reflog, refs, status, stage, and stash with the following rows (all other rows above, including the already expanded pager section, remain in the same order), making the complete all-keybindings corpus exactly 150 rows:

```text
[-] main bindings
Option toggling:
                           G :toggle commit-title-graph
                           F :toggle commit-title-refs
Internal commands:
                           H :goto HEAD
External commands:
                           C ?git cherry-pick %(commit)
[-] diff bindings
Option toggling:
                           [ :toggle diff-context -1
                           ] :toggle diff-context +1
Internal commands:
                           @ :/^@@
[-] reflog bindings
Option toggling:
                           F :toggle commit-title-refs
External commands:
                           C ?git checkout %(branch)
                           ! ?git reset --hard %(commit)
[-] refs bindings
External commands:
                           C ?git checkout %(branch)
                           ! ?git branch -D %(branch)
[-] status bindings
View-specific actions
                           u status-update              Stage/unstage chunk or file changes
                           ! status-revert              Revert chunk or file changes
                           M status-merge               Merge file using external tool
External commands:
                           C !git commit
[-] stage bindings
View-specific actions
                           u status-update              Stage/unstage chunk or file changes
                           ! status-revert              Revert chunk or file changes
                           1 stage-update-line          Stage/unstage single line
                           2 stage-update-part          Stage/unstage part of a chunk
                           \ stage-split-chunk          Split current diff chunk
Option toggling:
                           [ :toggle diff-context -1
                           ] :toggle diff-context +1
Internal commands:
                           @ :/^@@
[-] stash bindings
External commands:
                           A ?git stash apply %(stash)
                           P ?git stash pop %(stash)
                           ! ?git stash drop %(stash)
```

With all sections expanded and the collapse-all row selected, the footer is `[help] - line 2 of 150`; a viewport tall enough to show all 150 rows reports `100%`.

At 80 columns by 24 rows, the initial footer is `[help] - line 1 of 114` with right-aligned `19%`. The initial selection is row 1, `Quick reference for tig keybindings:`, not the collapse-all row; therefore an immediate `:enter` leaves `[-] Collapse all sections` and the binding details unchanged. After moving to row 2, Enter changes the collapse-all row to `[+] Expand all sections`, reduces the complete logical content to exactly these 14 rows, and selects row 2, so the footer is `[help] - line 2 of 14` with `100%`:

```text
Quick reference for tig keybindings:
[+] Expand all sections

[+] generic bindings
[+] search bindings
[+] main bindings
[+] diff bindings
[+] reflog bindings
[+] refs bindings
[+] status bindings
[+] stage bindings
[+] stash bindings
[+] pager bindings
[+] toggle bindings
```

User-defined external bindings are inserted under `External commands:` in their keymap section, using the same columns, and increase the total by one row apiece. For example, `bind generic X !echo user-command` adds exactly `                           X !echo user-command` and changes the default total from 114 to 115. A colon-command binding is instead listed under `Internal commands:`. If that subsection was absent, its heading adds another logical row: `bind generic Z :echo custom-binding-text` changes the total from 114 to 116 and includes the exact row `                           Z :echo custom-binding-text`. In a 130-row terminal the complete configured help fits, but a scripted literal `G` does not invoke End: it leaves the selection at line 1 and produces `[help] - line 1 of 115` for the external binding and `[help] - line 1 of 116` for the colon-command binding, both with `100%`.

## Spec 24

Load configuration from the system location (unless disabled by `TIGRC_SYSTEM`) and then the user location selected by `TIGRC_USER`; otherwise use `$XDG_CONFIG_HOME/tig/config` when applicable and `$HOME/.tigrc` according to normal precedence. A `source path` directive resolves a relative path from the executable's process working directory, not from the directory containing the including configuration file. Thus a child beside the configuration but absent from the repository working directory reports `File does not exist: child.rc`; putting `child.rc` in the process working directory succeeds. `source -q path` suppresses the missing-file error. A source flag other than `-q` reports `Invalid source option: <flag>`. The two-unflagged-operand form `source one two` likewise reports `Invalid source option: one`. A missing path reports `Invalid source command: source [-q] <path>`.

The language is line-oriented and accepts blank lines, leading/trailing whitespace, tabs, full-line and trailing `#` comments, quoted strings, escapes, Unicode, backslash continuations, and multiple commands. Commands are:

- `set name = value` for scalar or view-column settings;
- `bind keymap key request-or-command`;
- `color area foreground background [attributes...]`;
- `source [-q] path`.

Boolean spellings `yes/no`, `true/false`, and `1/0` are accepted where a boolean is expected. Do not crash or stop reading subsequent lines after malformed content; collect diagnostics. Configuration parse diagnostics use a warning prefix (stderr therefore contains the word `warning`), identify the bad command/value, and cover invalid `set`, `bind`, and `color` arity as well as unknown top-level commands. When at least one error occurs, stderr must contain `Errors while loading`.

## Spec 25

Support, at minimum, the active configuration names and types used by the views: `line-graphics` (`auto`, `ascii`, `utf-8`), `tab-size`, `diff-context`, `ignore-space`, `commit-order`, `split-view-height`, `split-view-width`, `vertical-split`, `horizontal-scroll`, `wrap-lines`, `focus-child`, `wrap-search`, `show-changes`, `id-width`, `refresh-mode`, `refresh-interval`, `history-size`, `mouse`, `mouse-scroll`, boolean `editor-line-number`, `reference-format`, `truncation-delimiter`, `git-colors`, `show-notes`, `diff-highlight`, and `<view>-view` / `<view>-view-<column>-<property>` column settings. Also accept view-specific forms used above such as `main-view-commit-title-graph`, `blame-view-date-use-author`, and `tree-view-date-use-author`.

The following exact assignments are errors, return 0, and end with `Errors while loading`: `set title-overflow = yes` warns `title-overflow is obsolete; see tigrc(5) for how to set the commit-title and text column option`; `set show-line-numbers = yes` warns `show-line-numbers is obsolete; see tigrc(5) for how to set the line-number column option`; `set filename-width = 20` warns `filename-width is obsolete; see tigrc(5) for how to set the file-name column option`; `set editor = vi` warns `Unknown option name: editor`; `set editor-line-number = +%(lineno)` warns `Non-boolean value treated as false: +%(lineno)`; and `set reference-format = [%s]` warns `Unknown ref format: [%s]`. `show-id` is likewise obsolete rather than active: `set show-id = true` warns `show-id is obsolete; see tigrc(5) for how to set the id column option` and then reports `Errors while loading`. They show the main view when repository-view dispatch applies; with empty `/dev/null` they emit the same diagnostics but save the empty pager from Spec 6. The legacy scalar names `author-width`, `show-refs`, `show-author`, `show-date`, and `show-rev-graph` are errors as specified below, not accepted aliases.

For strict validation: `tab-size` is 1..1024; `diff-context`, `mouse-scroll`, `history-size`, and `refresh-interval` are 0..1024; `id-width` is nonnegative and smaller than a full object-ID buffer; percentages are 0..100; `horizontal-scroll` is a number or percentage. `commit-order` accepts the documented automatic/default, date, topo, and reverse/order variants; `vertical-split` accepts `auto`, `horizontal`, `vertical`, and boolean values; `ignore-space` accepts `no`, `all`, `some`, `at-eol`, and boolean equivalents. Invalid values emit respectively `Value must be between ...`, `Percentage is larger than 100%`, `Percentage is less than 0%`, or `Invalid double or percentage`. Invalid enum values are errors; specifically use `'invalid' is not a valid value for refresh-mode; using manual` and `'garbage' is not a valid value for ignore-case; using no`. A malformed `set` lacking the required spaced `option = value` grammar reports `Invalid set command: set option = value`; this includes `set`, `set tab-size`, `set ignore-space`, `set ignore-space =`, and the unspaced form `set ignore-space=no`. An unknown name in an otherwise well-formed assignment reports `Unknown option name`. The exact invalid column assignment `set main-view-made-up = yes` reports `Failed to parse view column type: yes`, using the supplied value rather than the `made-up` suffix.

## Spec 26

`bind` validates keymaps, keys, and actions. Recognize at least `generic`, all view names, and `branch` as the `refs` alias. Recognize ordinary characters, multikey sequences, and bracketed special forms such as `<Enter>`, `<Esc>`, `<F1>`, `<Ctrl-X>`, and navigation keys. `none` unbinds. A later ordinary binding replaces an earlier one. Because Ctrl letters are case-insensitive, conflicting `<Ctrl-a>`/`<Ctrl-A>` actions report both `Key binding for ... conflict` and `keys using Ctrl are case insensitive`.

Diagnostics must contain: `Unknown key map: <name>`; `Missing '>' from key mapping`; `Unknown key mapping`; and `Control key mapping must now use '<Ctrl-`. The obsolete escape spelling is a caret followed by a literal left bracket: the exact line `bind generic ^[X view-main` reports `Escape key combo must now use '<Esc>X' instead of '^[X'` and `Errors while loading`. By contrast, `bind generic \eX view-main` is accepted without either diagnostic. Built-in actions use request names or colon commands such as `:toggle line-number`. External/run commands begin with one or more recognized prefix flags from `:!?@<+>`; any other first flag reports `Unknown command flag '<char>'; expected one of :!?@<+>`.

## Spec 27

`color` accepts a global area, `view.area`, or quoted literal, followed by foreground, background, and zero or more attributes. Support standard named/default colors and `color0` through `color255`; support attributes including `bold`, `dim`, and `underline`. A slash-delimited token is treated as an ordinary unsupported color-area name, not compiled as a regular expression: `color /[/ red black` warns `Unknown color name: /[/`; in the combined line `color /subject [0-9]+/ blue black`, tokenization makes the area `/subject` and the warning is `Unknown color name: /subject`. The preceding lines `color main.date color0 color255 bold dim underline` and `color "literal text" red default` are accepted. Validate every part. Other required diagnostic substrings are `Unknown color name: <area>`, `Unknown key map: <view>`, `Unknown color: <value>`, `Unknown color attribute: <value>`, and `Invalid color mapping: color area fgcolor bgcolor [attrs]`.

Recognize obsolete settings/actions and reject them with actionable diagnostics: `line-number-interval is obsolete` plus `line-number column option`; `author-width is obsolete` plus `author column option`; `show-refs is obsolete` plus `commit-title column option`; `show-author`, `show-date`, and `show-rev-graph` each name themselves and say they are obsolete/deprecated/renamed; `status-untracked-dirs` was `renamed to status-show-untracked-dirs`; `read-git-colors has been obsoleted by the git-colors option`; `acked has been replaced by '    Acked-by'`; `main-revgraph is obsolete`; `diff-rename-from has been replaced by 'rename from '`; `tree-dir has been replaced by tree.directory`; `filename has been replaced by file`; and obsolete requests map in diagnostics to `:toggle author`, `view-refs`, `:toggle line-number`, `:toggle diff-context +1`, `:toggle diff-context -1`, `:toggle file-filter`, `:toggle commit-title-graph`, and `:/^@@` for `stage-next`. `toggle-split-orientation` is not recognized as an obsolete request: the exact line `bind generic x toggle-split-orientation` reports `Unknown command flag 't'; expected one of :!?@<+>` and does not mention either the old request or `:toggle show-vertical-split`.

## Spec 28

Choose an editor from environment variables in this order: `TIG_EDITOR`, `GIT_EDITOR`, `VISUAL`, then `EDITOR`. The first variable that is present wins even when its value is empty; thus an explicitly empty `TIG_EDITOR` prevents a nonempty `GIT_EDITOR`, `VISUAL`, or `EDITOR` from being invoked, and similarly for empty variables at the later precedence levels. There is no active scalar `editor` setting: if `set editor = <helper>` is combined with a different `TIG_EDITOR`, configuration loading warns `Unknown option name: editor` and the `TIG_EDITOR` helper is invoked. Invoke a nonempty selected editor as an argument vector or documented shell command and, when boolean `editor-line-number` enables it, supply the default `+N` argument first. For a grep selection, the path argument is repository-relative and N is the one-based match ordinal, not the source line; a sole match on source line 2 supplies `+1` and the repository-relative path. A blob opened from the tree is instead materialized for editing: the path argument is an absolute temporary file whose basename has the form `tigblob.<temporary-suffix>.<original-basename>`. For the one-line root-tree file `only.txt`, the observed argument vector is `+1` followed by a path of the form `/tmp/tigblob.2nskIe.only.txt`; repeated invocations use different temporary suffixes. Return to and repaint the TUI after the editor exits. Editing a tree directory is rejected as described earlier.

Colon commands required by interaction and scripts include `:enter`, `:next`, `:edit`, `:view-main`, `:view-diff`, `:view-log`, `:view-reflog`, `:view-tree`, `:view-blob`, `:view-blame`, `:view-refs`, `:view-status`, `:view-stage`, `:view-stash`, `:view-grep`, `:view-pager`, `:view-help`, `:view-close`, `:view-close-no-quit`, `:maximize`, `:toggle <option>`, `:refresh`, `:quit`, `:echo ...`, `:exec ...`, `:!command`, `:N`, and `:/regex`. In a `TIG_SCRIPT`, the argumentless forms `:exec` and `:exec !` return 0 and preserve the current view without placing `Failed to execute command: No arguments` or `Failed to format arguments` in either terminal output or the following saved display.

The placeholders `%(cmdlineargs)` and `%(fileargs)` are not expanded into visible `:echo` output in a `TIG_SCRIPT`. With empty `/dev/null` stdin and launch arguments `--max-count=1 -- README.md`, `:echo %(cmdlineargs) | %(fileargs)` followed by `:save-display` captures the empty pager specified in Spec 6 and contains neither launch argument. With empty `/dev/null` and no such arguments, `:echo before%(cmdlineargs)middle%(fileargs)after` likewise leaves the empty pager and does not display `beforemiddleafter`. When the current view was reached through another accepted input context, these commands leave that current view in place. Execute explicit shell/run bindings with their documented confirmation/silent/background/exit prefixes, without accidentally treating ordinary paths or grep metacharacters as shell code.

## Spec 29

If `TIG_SCRIPT` names a file, after terminal initialization read it sequentially. Ignore blank lines and lines beginning with `#`. Treat key lines as input keys and colon lines as the internal commands from Spec 28. `:save-display path` writes the current logical screen as plain UTF-8 text with terminal attributes and escape sequences removed, right-side unused blanks omitted except meaningful alignment, and a final newline. The saved logical screen contains `LINES - 1` lines: a 12-row terminal saves 11 lines, and a 13-row terminal saves 12. Ordinary scripted view changes, enters, saves, and quit complete in sequence so each completed save observes a stable redraw.

Prompt-driven interaction is an exception. From main, scripted `:view-blob` initiates the file finder but is not equivalent to a synchronous `f`, select, and Enter sequence: later script lines are consumed around the prompt rather than as ordinary internal commands. The exact sequence `:view-blob`, `:save-display <path>`, `:quit` returns 0 without creating `<path>`. The exact sequence `:view-blob`, `:enter`, `:save-display <path>`, `:quit` saves the unchanged main view. The exact sequence `:view-blob`, `:next`, `:enter`, `:save-display <path>`, `:quit` saves the main view split with the selected commit's diff. These sequences do not open `README.md`, the empty blob, an unterminated blob, or a selected historical blob. Consequently finder contents, fuzzy filtering, blob line counts, and historical blob contents must be exercised through an interactive input driver rather than inferred from these scripted sequences. Scripted `:/pattern` searches have the saved-display behavior specified in Spec 9.

Those exact results are conditional on starting in main. With the default launch and empty `/dev/null` stdin, the initial view is instead the empty pager from Spec 6. In that context the exact four-command sequence `:view-blob`, `:enter`, `:save-display <path>`, `:quit` returns 0 and saves the unchanged empty pager, whose only footer begins `[pager]` and ends `0%`; it does not save `[main]` or `[blob]`. The argumentless scripted commands `:exec` and `:exec !` likewise preserve that empty pager while producing neither of the errors excluded in Spec 28.

Terminal initialization occurs before executing the script. Therefore with no controlling tty, return 1 with `Failed to open tty` and do not execute script-bound external commands. Closing a child with `:view-close` restores its parent; `:view-close-no-quit` on the last view is a safe no-op rather than an abort.

## Spec 30

The implementation must be deterministic for identical repository, environment, configuration, terminal dimensions, and input sequence. In particular, use Git-provided ordering and data, stable lexical ordering where Git does not dictate it, exact one-based counts, exact decimal sizes, and consistent padding. Repaint operations must not mix old and new panes. Refresh, failed search, failed edit/blame-on-directory, invalid prompt command, and canceled revert preserve the current usable view.

All repository-changing behavior is limited to the explicit staging/revert operations described above. Browsing, filtering, pager input, configuration parsing, help/version, editor launch, and view navigation must not alter commits, refs, index, worktree files, or user configuration.
