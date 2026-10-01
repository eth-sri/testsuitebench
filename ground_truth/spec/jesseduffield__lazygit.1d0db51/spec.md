# Executable behavioral specification

The required artifact is a single executable file named `executable`. The following sections define its externally observable behavior. Terms such as “Git repository”, “index”, “working tree”, “commit”, “ref”, “stash”, and “reflog” have their ordinary Git meanings; the executable may invoke the harness-provided `git` command to implement them. Interactive requirements are exercised through a real pseudo-terminal, normally at 80 columns by 24 rows, and changes must be visible both in the terminal and to subsequent `git` commands.

## Spec 1

`executable` is a Lazygit-style terminal application with four noninteractive information modes and an interactive mode. It must run on Linux, use the current process environment and current working directory, and terminate promptly for `--help`, `--version`, `--config`, `--print-config-dir`, argument/config errors, and daemon requests. Interactive operation must read raw terminal key events, continuously repaint a text UI, react within roughly one second, and quit cleanly on `q` (or `Q` when the distinction is relevant). It must not crash or segfault when keys are rapidly repeated, unknown keys are pressed, lists are empty, the repository has no commits, HEAD is detached, paths contain spaces/non-ASCII characters, or common Git states such as merge/cherry-pick/rebase are active.

When interactive startup is attempted without a usable terminal, return exit status 1 and report a terminal error (the tested Linux environment expects text such as `terminal entry not found: term not set` when `TERM` is unset and `open /dev/tty` when no controlling TTY is available). This is a startup failure, not a usage or invalid-panel error.

## Spec 2

`-h` and `--help` are equivalent, return 0, write nothing to stdout, and write exactly the following UTF-8 text to stderr, including blank lines, spacing, capitalization, backticks, and final newline:

```text
executable

  Usage:
    executable [git-arg]

  Positional Variables: 
    git-arg   Panel to focus upon opening lazygit. Accepted values (based on git terminology): status, branch, log, stash. Ignored if --filter arg is passed.
  Flags: 
    -h --help               Displays help with available flag, subcommand, and positional value parameters.
    -p --path               Path of git repo. (equivalent to --work-tree=<path> --git-dir=<path>/.git/)
    -f --filter             Path to filter on in `git log -- <path>`. When in filter mode, the commits, reflog, and stash are filtered based on the given path, and some operations are restricted
    -v --version            Print the current version
    -d --debug              Run in debug mode with logging (see --logs flag below). Use the LOG_LEVEL env var to set the log level (debug/info/warn/error)
    -l --logs               Tail lazygit logs (intended to be used when `lazygit --debug` is called in a separate terminal tab)
       --profile            Start the profiler and serve it on http port 6060. See CONTRIBUTING.md for more info.
    -c --config             Print the default config
    -cd --print-config-dir   Print the config directory
    -ucd --use-config-dir     override default config directory with provided directory
    -w --work-tree          equivalent of the --work-tree git argument
    -g --git-dir            equivalent of the --git-dir git argument
    -ucf --use-config-file    Comma separated list to custom config file(s)
    -sm --screen-mode        The initial screen-mode, which determines the size of the focused panel. Valid options: 'normal' (default), 'half', 'full'

```

The help contains no ANSI escapes. A valid positional panel before `--help` does not alter this output. When `GIT_WORK_TREE` or `GIT_DIR` is nonempty, the generated help must additionally expose its value as the corresponding flag’s default; otherwise the output above is exact. Help describes flags only, never an “available subcommands” or `Commands:` section.

## Spec 3

The command line has no subcommands. It accepts at most one positional `git-arg`: exactly `status`, `branch`, `log`, or `stash`. Rather than merely focusing one panel in the default dashboard, these start a focused layout with one side context and one main pane (plus Command log), omitting the other side panels: `status` shows `Files - Worktrees - Submodules` beside `Diff`, `branch` shows `Local branches - Remotes - Tags` beside `Log`, `log` shows `Commits - Reflog` beside `Patch`, and `stash` shows `Stash` beside a second `Stash` pane. A filter overrides positional focus. Except when version dispatch applies as described below, any other ordinary positional value returns 1, writes nothing to stdout, and writes this timestamp-prefixed line to stderr (the prefix uses local time in `YYYY/MM/DD HH:MM:SS ` form):

`Invalid git arg value: '<value>'. Must be one of the following values: status, branch, log, stash. e.g. 'lazygit status'. See 'lazygit --help'.`

Two positional values are a syntax error: return 2, display the help/usage, and include `Unexpected argument: <second>`.

Recognized aliases are `-h/--help`, `-p/--path`, `-f/--filter`, `-v/--version`, `-d/--debug`, `-l/--logs`, `--profile`, `-c/--config`, `-cd/--print-config-dir`, `-ucd/--use-config-dir`, `-w/--work-tree`, `-g/--git-dir`, `-ucf/--use-config-file`, and `-sm/--screen-mode`. Value-taking flags accept either a following token or `=<value>` on the same token, subject to the filter/screen-mode parser quirk in Spec 4. Combined short flags such as `-dv` are not aliases. Ordinary parsing errors return 2 and include the full Usage/Flags help. In the parser used here, an unknown long option without `=` is diagnosed as `Expected a following arg for flag <name>`, while an unknown option with `=` is `Unknown flag: --<name>`. Missing values use `Expected a following arg for flag <short-or-long-name>`. A lone `-` and an empty argument each return 2 with empty stdout and a Go panic stack beginning `panic: cant add parsed value with no key or value`; these two panic paths do not include `Usage:` or the flag help.

`--help`, `--version`, `--config`, and `--print-config-dir` may occur with ordinary options in any order. A valid panel plus help produces the same help as help alone. Help dispatch can suppress later argument validation: specifically, `--help --unknown=value` returns 0 and emits exactly the ordinary help to stderr rather than an unknown-flag error. `--version` also takes precedence over positional-value validation: `invalid_panel --version` returns 0 with the normal version line and empty stderr. It succeeds from a non-repository current directory and bypasses config-file existence/YAML validation and screen-mode value validation. Information modes do not require the current directory to be a Git repository, but an explicitly supplied `--path` is still validated before any information action: thus `--path <missing> --version` and `--path <missing> --print-config-dir` fail as invalid repositories.

## Spec 4

`-v` and `--version` are equivalent, return 0, write nothing to stderr, and write one newline-terminated stdout line. It is a comma-and-space separated list in this exact field order:

`commit=<hex>, build date=<text>, build source=<text>, version=<hex-or-dotted-version>, os=<word>, arch=<word>, git version=<text>`

Every value is nonempty. `commit` must contain hexadecimal digits, and `version` must consist of hexadecimal digits and/or dots. The output is deterministic across consecutive calls. It continues to work when combined with debug/profile/config/path/filter/screen-mode options, valid positional panels, environment overrides, empty repositories, bare repositories, or unusual repository paths, except for this parser interaction: when an equals-form filter such as `--filter=tracked.txt` precedes a split-form `--screen-mode full`, the latter value is left as an unknown argument. Even with `--version`, the command returns 2 with empty stdout and the full help on stderr ending `Unknown arguments supplied:  full`; spelling the latter option `--screen-mode=full` succeeds.

## Spec 5

`-c` and `--config` return 0, write nothing to stderr, and print the built-in default configuration as UTF-8 YAML-like text. Config mode dispatches before configuration files are read: `--use-config-file`, `-ucf`, `LG_CONFIG_FILE`, and `--use-config-dir` do not change or validate this output, even if a named file is missing, contains malformed YAML, or contains a value that would fail interactive-startup validation. Stdout must always equal the following block exactly, including four-space indentation, key ordering, quoting, and final newline:

```yaml
gui:
    authorColors: {}
    branchColors: {}
    branchColorPatterns: {}
    customIcons:
        filenames: {}
        extensions: {}
    scrollHeight: 2
    scrollPastBottom: true
    scrollOffMargin: 2
    scrollOffBehavior: margin
    tabWidth: 4
    mouseEvents: true
    skipAmendWarning: false
    skipDiscardChangeWarning: false
    skipStashWarning: false
    skipNoStagedFilesWarning: false
    skipRewordInEditorWarning: false
    skipSwitchWorktreeOnCheckoutWarning: false
    sidePanelWidth: 0.3333
    expandFocusedSidePanel: false
    expandedSidePanelWeight: 2
    mainPanelSplitMode: flexible
    enlargedSideViewLocation: left
    wrapLinesInStagingView: true
    useHunkModeInStagingView: true
    language: auto
    timeFormat: 02 Jan 06
    shortTimeFormat: 3:04PM
    theme:
        activeBorderColor:
            - green
            - bold
        inactiveBorderColor:
            - default
        searchingActiveBorderColor:
            - cyan
            - bold
        optionsTextColor:
            - blue
        selectedLineBgColor:
            - blue
        inactiveViewSelectedLineBgColor:
            - bold
        cherryPickedCommitFgColor:
            - blue
        cherryPickedCommitBgColor:
            - cyan
        markedBaseCommitFgColor:
            - blue
        markedBaseCommitBgColor:
            - yellow
        unstagedChangesColor:
            - red
        defaultFgColor:
            - default
    commitLength:
        show: true
    showListFooter: true
    showFileTree: true
    showRootItemInFileTree: true
    showNumstatInFilesView: false
    showRandomTip: true
    showCommandLog: true
    showBottomLine: true
    showPanelJumps: true
    showIcons: false
    nerdFontsVersion: ""
    showFileIcons: true
    commitAuthorShortLength: 2
    commitAuthorLongLength: 17
    commitHashLength: 8
    showBranchCommitHash: false
    showDivergenceFromBaseBranch: none
    commandLogSize: 8
    splitDiff: auto
    screenMode: normal
    border: rounded
    animateExplosion: true
    portraitMode: auto
    filterMode: substring
    spinner:
        frames:
            - '|'
            - /
            - '-'
            - \
        rate: 50
    statusPanelView: dashboard
    switchToFilesAfterStashPop: true
    switchToFilesAfterStashApply: true
    switchTabsWithPanelJumpKeys: false
git:
    pagers: []
    commit:
        signOff: false
        autoWrapCommitMessage: true
        autoWrapWidth: 72
    merging:
        manualCommit: false
        args: ""
        squashMergeMessage: Squash merge {{selectedRef}} into {{currentBranch}}
    mainBranches:
        - master
        - main
    skipHookPrefix: WIP
    autoFetch: true
    autoRefresh: true
    autoForwardBranches: onlyMainBranches
    fetchAll: true
    autoStageResolvedConflicts: true
    branchLogCmd: git log --graph --color=always --abbrev-commit --decorate --date=relative --pretty=medium {{branchName}} --
    allBranchesLogCmds:
        - git log --graph --all --color=always --abbrev-commit --decorate --date=relative  --pretty=medium
    ignoreWhitespaceInDiffView: false
    diffContextSize: 3
    renameSimilarityThreshold: 50
    overrideGpg: false
    disableForcePushing: false
    commitPrefix: []
    commitPrefixes: {}
    branchPrefix: ""
    parseEmoji: false
    log:
        order: topo-order
        showGraph: always
        showWholeGraph: false
    localBranchSortOrder: date
    remoteBranchSortOrder: date
    truncateCopiedCommitHashesTo: 12
update:
    method: prompt
    days: 14
refresher:
    refreshInterval: 10
    fetchInterval: 60
confirmOnQuit: false
quitOnTopLevelReturn: false
disableStartupPopups: false
customCommands: []
services: {}
notARepository: prompt
promptToReturnFromSubprocess: true
keybinding:
    universal:
        quit: q
        quit-alt1: <c-c>
        suspendApp: <c-z>
        return: <esc>
        quitWithoutChangingDirectory: Q
        togglePanel: <tab>
        prevItem: <up>
        nextItem: <down>
        prevItem-alt: k
        nextItem-alt: j
        prevPage: ','
        nextPage: .
        scrollLeft: H
        scrollRight: L
        gotoTop: <
        gotoBottom: '>'
        gotoTop-alt: <home>
        gotoBottom-alt: <end>
        toggleRangeSelect: v
        rangeSelectDown: <s-down>
        rangeSelectUp: <s-up>
        prevBlock: <left>
        nextBlock: <right>
        prevBlock-alt: h
        nextBlock-alt: l
        nextBlock-alt2: <tab>
        prevBlock-alt2: <backtab>
        jumpToBlock:
            - "1"
            - "2"
            - "3"
            - "4"
            - "5"
        focusMainView: "0"
        nextMatch: "n"
        prevMatch: "N"
        startSearch: /
        optionMenu: <disabled>
        optionMenu-alt1: '?'
        select: <space>
        goInto: <enter>
        confirm: <enter>
        confirmMenu: <enter>
        confirmSuggestion: <enter>
        confirmInEditor: <a-enter>
        confirmInEditor-alt: <c-s>
        remove: d
        new: "n"
        edit: e
        openFile: o
        scrollUpMain: <pgup>
        scrollDownMain: <pgdown>
        scrollUpMain-alt1: K
        scrollDownMain-alt1: J
        scrollUpMain-alt2: <c-u>
        scrollDownMain-alt2: <c-d>
        executeShellCommand: ':'
        createRebaseOptionsMenu: m
        pushFiles: P
        pullFiles: p
        refresh: R
        createPatchOptionsMenu: <c-p>
        nextTab: ']'
        prevTab: '['
        nextScreenMode: +
        prevScreenMode: _
        cyclePagers: '|'
        undo: z
        redo: Z
        filteringMenu: <c-s>
        diffingMenu: W
        diffingMenu-alt: <c-e>
        copyToClipboard: <c-o>
        openRecentRepos: <c-r>
        submitEditorText: <enter>
        extrasMenu: '@'
        toggleWhitespaceInDiffView: <c-w>
        increaseContextInDiffView: '}'
        decreaseContextInDiffView: '{'
        increaseRenameSimilarityThreshold: )
        decreaseRenameSimilarityThreshold: (
        openDiffTool: <c-t>
    status:
        checkForUpdate: u
        recentRepos: <enter>
        allBranchesLogGraph: a
    files:
        commitChanges: c
        commitChangesWithoutHook: w
        amendLastCommit: A
        commitChangesWithEditor: C
        findBaseCommitForFixup: <c-f>
        confirmDiscard: x
        ignoreFile: i
        refreshFiles: r
        stashAllChanges: s
        viewStashOptions: S
        toggleStagedAll: a
        viewResetOptions: D
        fetch: f
        toggleTreeView: '`'
        openMergeOptions: M
        openStatusFilter: <c-b>
        copyFileInfoToClipboard: "y"
        collapseAll: '-'
        expandAll: =
    branches:
        createPullRequest: o
        viewPullRequestOptions: O
        copyPullRequestURL: <c-y>
        checkoutBranchByName: c
        forceCheckoutBranch: F
        checkoutPreviousBranch: '-'
        rebaseBranch: r
        renameBranch: R
        mergeIntoCurrentBranch: M
        moveCommitsToNewBranch: "N"
        viewGitFlowOptions: i
        fastForward: f
        createTag: T
        pushTag: P
        setUpstream: u
        fetchRemote: f
        addForkRemote: F
        sortOrder: s
    worktrees:
        viewWorktreeOptions: w
    commits:
        squashDown: s
        renameCommit: r
        renameCommitWithEditor: R
        viewResetOptions: g
        markCommitAsFixup: f
        setFixupMessage: c
        createFixupCommit: F
        squashAboveCommits: S
        moveDownCommit: <c-j>
        moveUpCommit: <c-k>
        amendToCommit: A
        resetCommitAuthor: a
        pickCommit: p
        revertCommit: t
        cherryPickCopy: C
        pasteCommits: V
        markCommitAsBaseForRebase: B
        tagCommit: T
        checkoutCommit: <space>
        resetCherryPick: <c-R>
        copyCommitAttributeToClipboard: "y"
        openLogMenu: <c-l>
        openInBrowser: o
        viewBisectOptions: b
        startInteractiveRebase: i
        selectCommitsOfCurrentBranch: '*'
    amendAttribute:
        resetAuthor: a
        setAuthor: A
        addCoAuthor: c
    stash:
        popStash: g
        renameStash: r
    commitFiles:
        checkoutCommitFile: c
    main:
        toggleSelectHunk: a
        pickBothHunks: b
        editSelectHunk: E
    submodules:
        init: i
        update: u
        bulkMenu: b
    commitMessage:
        commitMenu: <c-o>

```

This serialization is deterministic, contains no tabs or comment lines, uses lowercase booleans and unquoted ordinary enum strings, preserves integers as integers and `0.3333` exactly, and uses `{}` rather than null for empty maps. Configuration overrides used for interactive startup are merged into these defaults recursively, but config mode itself always serializes the unmodified built-in defaults.

## Spec 6

`-cd` and `--print-config-dir` return 0, write a single absolute directory path plus one newline to stdout, and write nothing to stderr. `--use-config-dir PATH`/`-ucd PATH` overrides all discovery and the printed path is `PATH` with trailing slashes removed. Otherwise nonempty `CONFIG_DIR` wins. Otherwise, search for an existing legacy `jesseduffield/lazygit/config.yml`: first below `XDG_CONFIG_HOME` (default `$HOME/.config`), then below each colon-separated `XDG_CONFIG_DIRS` entry in order. If found, use its parent even when a newer `XDG_CONFIG_HOME/lazygit/config.yml` also exists. If none exists, use `$XDG_CONFIG_HOME/lazygit`; with `HOME=/root` and no XDG override this is `/root/.config/lazygit`.

## Spec 7

Configuration is read as YAML before interactive startup, but not before the precedence-taking `--version` or `--config`. Explicit `--use-config-file`/`-ucf` accepts one path or a comma-separated ordered list. `LG_CONFIG_FILE` provides the same list when no explicit list supersedes it. When entering interactive mode, read every listed file; a missing later file is still fatal and its path is reported. Merge mappings recursively in list order so later values override earlier values while unrelated defaults/earlier keys remain. Nested maps, lists, custom commands, editor settings, keybinding overrides, and all top-level sections appearing in Spec 5 must be accepted where they use the types and values described in this document.

The editor configuration accepts `os.edit`, `os.editAtLine`, `os.editInTerminal`, and `os.editPreset`. Supported presets are `vim`, `nvim`, `emacs`, `nano`, `vscode`, `helix`, `sublime`, `kakoune`, `bbedit`, `xcode`, `zed`, `acme`, `micro`, `lvim`, and `nvim-remote`. With no explicit preset, conventional `EDITOR`/`VISUAL` values including `vim`, `code`, `hx`, and `emacs` are tolerated/detected.

## Spec 8

When configuration is actually loaded for interactive startup, malformed YAML or invalid validated values return nonzero and write one timestamp-prefixed error to stderr. These checks are bypassed by `--config` as specified above. Prefix errors with local time formatted `YYYY/MM/DD HH:MM:SS `; preserve the supplied path exactly, including spaces and Unicode. After tests normalize the timestamp and workspace prefix, the remainder must match these forms exactly:

```text
failed to parse YAML: yaml: line 3: could not find expected ':'
stat <path>: no such file or directory
The config at `<path>` has a validation error.
Unexpected value '<value>' for 'gui.statusPanelView'. Allowed values: dashboard, allBranchesLog
The config at `<path>` has a validation error.
Unexpected value '<value>' for 'gui.showDivergenceFromBaseBranch'. Allowed values: none, onlyArrow, arrowAndNumber
The config at `<path>` has a validation error.
Unexpected value '<value>' for 'git.autoForwardBranches'. Allowed values: none, onlyMainBranches, allBranches
The config at `<path>` has a validation error.
Unexpected value '<value>' for 'git.localBranchSortOrder'. Allowed values: date, recency, alphabetical
The config at `<path>` has a validation error.
Unexpected value '<value>' for 'git.remoteBranchSortOrder'. Allowed values: date, alphabetical
The config at `<path>` has a validation error.
Unexpected value '<value>' for 'git.log.order'. Allowed values: date-order, author-date-order, topo-order, default
The config at `<path>` has a validation error.
Unexpected value '<value>' for 'git.log.showGraph'. Allowed values: always, never, when-maximised
The config at `<path>` has a validation error.
keybinding.universal.jumpToBlock must have 5 elements; found <count>.
The config at `<path>` has a validation error.
Unrecognized key '<key>' for keybinding 'Universal.Quit'. For permitted values see https://github.com/jesseduffield/lazygit/blob/master/docs/keybindings/Custom_Keybindings.md
The config at `<path>` has a validation error.
Unrecognized key '<key>' for custom command. For permitted values see https://github.com/jesseduffield/lazygit/blob/master/docs/keybindings/Custom_Keybindings.md
The config at `<path>` has a validation error.
Unexpected value '<value>' for 'customCommand.output'. Allowed values: , none, terminal, log, logWithPty, popup
```

The enum values listed as allowed must be accepted. A custom command key may be an ordinary character or angle-bracket key such as `<c-t>`; outputs `popup` and `terminal` are valid. `jumpToBlock` is valid only with exactly five elements.

## Spec 9

`--path`/`-p PATH` selects a repository and is equivalent to work tree `PATH` plus Git directory `PATH/.git`. It accepts absolute, relative, symlinked, space-containing, special-character, and Unicode paths, but validates that the location is a Git repository before entering the TUI. A nonexistent path, regular file, or non-repository directory returns 1, stdout is empty, and stderr contains a timestamp followed by `<path> is not a valid git repository.` The displayed path must not acquire duplicated slashes.

`--path` is incompatible with either `--work-tree` or `--git-dir`; return 1 and include `--path option is incompatible with the --work-tree and --git-dir options`. `--work-tree`/`-w` changes to the specified directory and a nonexistent target returns 1 with `Failed to change directory to <path>`. `--git-dir`/`-g` and `--work-tree` may be supplied independently or together and must be forwarded to Git semantics, including bare repositories. Command-line values override `GIT_WORK_TREE` and `GIT_DIR`; otherwise those environment values are defaults. `--filter`/`-f` accepts absolute or repository-relative files, directories, globs, and nonexistent paths and applies `git log -- <path>` semantics without treating a missing filtered path as an argument error.

## Spec 10

`--debug`, `-d`, or environment `DEBUG=TRUE` enables append-only newline-delimited JSON logging before terminal initialization. Default path is `$XDG_STATE_HOME/lazygit/development.log`, with `XDG_STATE_HOME` defaulting to `$HOME/.local/state`; `LAZYGIT_LOG_PATH` replaces the complete path. Do not create missing parent directories for a custom log path: report `Unable to log to log file` and the underlying `no such file or directory`. Repository selection never relocates the log.

Every log line is a JSON object with `level`, `msg`, and `time` keys; `level` and `time` are nonempty, but `msg` is the empty string on error records for quiet failing commands such as `git rev-parse --verify --quiet` when Git writes no diagnostic. Include multiple startup entries and one or more objects with a `command` field containing a Git command. Repeated runs append and preserve previous content. `LOG_LEVEL=debug` admits debug and info; `info` suppresses debug but includes info and error; `warn` suppresses debug/info; `error` emits error but no debug/info. An invalid level remains usable and behaves like debug/default. `--profile` and debug are compatible and debug still creates the log.

## Spec 11

`--logs`/`-l` writes `Tailing log file <resolved-path>` followed by a blank line to stdout and follows that path. It does the same when the path does not yet exist: it writes nothing to stderr, does not return an error, and remains running while it waits for the file to appear. If the file is present, immediately render existing JSON lines in human-readable form and remain following until terminated. For a UTC record such as `{"level":"debug","msg":"Test debug message","time":"2026-04-18T10:00:00Z"}`, output includes `Apr 18 10:00:00`, `|DEBU|`, and the message; similarly use `|INFO|` and `|ERRO|`. Honor `LAZYGIT_LOG_PATH` both for the header and file read.

## Spec 12

`--profile` is a recognized, combinable interactive option that starts or attempts to start an HTTP profiler on localhost port 6060; terminal failure after recognition is acceptable. Help and version dispatch precede internal daemon dispatch. Thus, with positive `LAZYGIT_DAEMON_KIND` and an object instruction, `--help` returns 0 with the full ordinary help on stderr, and `--version` returns 0 with the ordinary version line on stdout; the daemon instruction is not run. In the absence of such a precedence-taking information flag, internal daemon mode is selected only when `LAZYGIT_DAEMON_KIND` parses as a positive integer. Kind `1`, with `LAZYGIT_DAEMON_INSTRUCTION` containing `{}` or an object with unknown extra fields, exits 0 with empty stdout and normally empty stderr. Missing, empty, or syntactically invalid instruction JSON returns nonzero with a JSON/panic diagnostic (invalid syntax includes `panic` and `invalid character`). Non-numeric or zero kind means normal mode. For kinds `2`, `3`, and `4`, an object instruction containing `{"Todos":[]}` reaches the interactive-rebase handler and panics with `panic: runtime error: index out of range [1] with length 1`; the three stack traces respectively identify `removeUpdateRefsForCopiedBranchInstruction`, `moveTodosUpInstruction`, and `moveTodosDownInstruction`.

## Spec 13

The default TUI is a bordered, multi-panel dashboard. It visibly labels Status, Files/Worktrees, Local branches/Remotes, Commits/Reflog, Stash, a main Diff/details view, and Command log; it shows repository name, current branch (including `master`/`main` or configured branch names), list counters such as `1 of 3`, and a context-sensitive bottom keybinding bar. At 80 columns with rounded borders, the captured side-panel title prefixes are `╭─[1]─Status`, `╭─[2]─Files - Worktrees -`, `╭─[3]─Local branches - Re`, `╭─[4]─Commits - Reflog` and `╭─[5]─Stash`. Focusing a panel does not insert `*` into that title; focus is represented by styling rather than an extra captured glyph. It must produce substantially more than 100 captured bytes at normal terminal sizes. A first-run welcome popup may appear and must close on Enter or Escape; `disableStartupPopups: true` suppresses it.

Keys `1` through `5` focus the five side contexts, `0` focuses the main view, Tab/Shift-Tab and Left/Right or `h`/`l` cycle contexts, and Up/Down or `k`/`j` move selection without leaving list bounds. Home/End, `<`/`>`, PageUp/PageDown, `J`/`K`, Ctrl-D/Ctrl-U scroll appropriately. Enter drills into a selected item or toggles applicable tree nodes; Escape closes the top dialog or returns one view level without corrupting state. `R` refreshes from disk. `?` opens a searchable `Keybindings` help/menu containing global and context bindings and closes with Enter/Escape. `/` begins search; text filters/highlights list matches, `n`/`N` move matches, and Escape exits search.

## Spec 14

The Files context accurately mirrors `git status --short`: unstaged modified ` M`, staged modified `M `, both `MM`, added `A `, deleted staged status, unresolved `UU`, and untracked `??`. It supports nested directory trees, expanding/collapsing nodes, filenames with spaces/special characters, empty and large sets, and preserves selection across harmless menus. The main view shows a standard unified diff for the selected file, including `diff --git`, hunk headers, additions, deletions, and staged versus unstaged headings.

When file-tree mode starts with multiple changed paths, selection is initially on the tree's root/group row rather than the first leaf filename. Space toggles the selected file between staged and unstaged using the Git index; on that initial root selection it stages or unstages every descendant. `a` stages or unstages all as appropriate. These operations must affect only the selected file unless a directory/root/range/all operation was selected, work for modified/new/deleted files, tolerate repeated toggles, and correctly represent a file with simultaneous staged and unstaged changes. Range selection with `v` and Shift-Up/Shift-Down applies staging/unstaging to every selected row. Refresh must preserve a sensible open tree and show external changes.

## Spec 15

Files key `d` opens `Discard changes`. For a file with only an unstaged modification, confirmation restores its HEAD contents while preserving other files. For `MM`, the menu offers `Discard all changes` and `Discard unstaged changes`; `x` chooses all and `u` chooses unstaged-only. The latter keeps the index version and removes only the work-tree delta; all removes both. Untracked discard removes the selected path after confirmation. On the initial root/group selection described in Spec 14, confirming discard applies to all untracked descendants (for example, both `a-untracked.txt` and `z-untracked.txt`), not just the lexicographically first path. Cancel leaves everything unchanged. Directory/range discard applies exactly to selected descendants/items.

Files key `D` opens reset/workspace choices displaying the operation summaries: `Nuke working tree` / `git reset --hard HEAD && git clean -fd`, `Discard unstaged changes` / `git checkout -- .`, `Discard untracked files` / `git clean -fd`, `Discard staged changes` / `stash staged and drop stash`, `Soft reset` / `git reset --soft HEAD`, `mixed reset` / `git reset --mixed HEAD`, and `Hard reset` / `git reset --hard HEAD`. Mixed reset preserves content unstaged; soft reset to an older commit preserves changes staged; hard reset moves HEAD and discards tracked/untracked changes; nuke restores HEAD and cleans untracked paths. Destructive choices require confirmation and appear in reflog.

## Spec 16

Files key `i` opens `Ignore or exclude file`, including `Add to .gitignore` and `Add to .git/info/exclude`. Ignoring a root file appends `/<filename>\n` to repository `.gitignore`; ignoring a directory uses a directory pattern that ignores its descendants. Excluding appends the equivalent pattern to `.git/info/exclude`. Existing patterns are preserved and new ones appended. A tracked target asks `Ignore tracked file` / `Are you sure you want to ignore a tracked file?` or the corresponding `Exclude tracked file` question before adding the rule; the tracked path remains on disk but appears deleted to Git. Cancellation changes nothing. Multiple operations append independently. Attempting to ignore `.gitignore` itself fails safely. The command log reports, for example, `Appending '/debug.log' to file '.gitignore'`, and status refreshes immediately.

Files `y` opens `Copy to clipboard` with entries in this order: `n File name`, `p Relative path`, `P Absolute path`, `s Diff of selected file`, `a Diff of all files`, then `Cancel`. The same menu is available for files, directories, untracked paths, and names with spaces and returns without changing selection. `e` invokes the configured editor for a file and `o` invokes the configured opener; neither crashes on special paths. They are disabled/no-op for directory-only selections. Configured `os.edit*`, `EDITOR`, and `VISUAL` commands receive the selected filename and line placeholders correctly.

## Spec 17

From Files, `c` starts a commit. If nothing is staged, show `No files staged` and `You have not staged any files. Commit all files?`; confirming stages all before opening the editor. The editor contains separate `Commit summary` and `Commit description` fields. Tab moves between them, and Ctrl-S or Alt-Enter submits from the description. The description border's visible hint is exactly `Press <tab> to toggle focus, <c-o> to open menu`; it does not display either submit binding. Preserve arbitrary long summary text, multiline descriptions, and blank lines. A successful commit uses summary, a blank line, then description, includes all staged files, updates Commit/File panels, and leaves committed paths clean.

Empty summary (even with description) is rejected with an `Error` mentioning committing `without a commit message`; the staged state remains. Escape from either field cancels and also preserves staged state. Files `w` is commit-without-hooks and displays `(hooks disabled)`; it prefills `WIP` according to `git.skipHookPrefix`. `C` commits through the configured Git editor. Branch-pattern `git.commitPrefixes` may prefill text such as `TASK-123:` when the current branch matches, while nonmatching branches get no false prefix; global/fallthrough prefixes and auto-wrapping at configured width are honored.

## Spec 18

The Commits panel shows newest first with abbreviated hashes, author initials, decorations/branch markers, subjects, and navigation footer `Squash: s | Fixup: f | Reword: r | Drop: d`. In the default 80-column dashboard, its subject field displays up to 11 cells: representative rows are `commit 6: b`, `Third commi`, `Second comm`, and the complete `Base commit`. Selecting a row updates the details pane, where the selected subject is shown in full (including `commit 6: bad`, `Third commit`, and `Second commit`), followed by its body, `Author: Name <email>`, `Date:`, and changed files/diff. Enter opens `Diff files`; selecting a commit file shows its patch and offers `Checkout: c | Remove: d | Edit: e`. Checkout of a commit/file or selected range changes the working tree only after any needed confirmation and handles local modifications safely.

Commit `y` opens `Copy to clipboard` with `Commit hash`, `s Commit subject`, `m Commit message (subject and body)`, `b Commit message body`, `u Commit URL`, `d Commit diff`, `a Commit author`, `t Commit tags`, and `Cancel`. Ctrl-O bypasses this menu and directly copies the selected commit hash. With the built-in `git.truncateCopiedCommitHashesTo: 12` setting, the clipboard receives exactly the first 12 lowercase hexadecimal characters of the full hash, with no trailing newline. The status encloses those same 12 characters in single quotes and follows them with ` copied to clipboard`. For either copy path, when no supported clipboard program exists, display `No clipboard utilities available` and mention `xsel, xclip, wl-clipboard`; do not crash. Configuration may disable copying message bodies. Pasting/copying commit messages into editor fields must preserve or replace existing content as selected.

## Spec 19

Commit rewriting is real Git history rewriting. `r` opens `Reword commit`, prefilled with the selected subject and body; changing the subject changes that commit hash while preserving an untouched body and other commits. Rewording older, first, last, merge, fixup, or current rebase commits uses an interactive rebase when necessary and leaves descendants consistently rewritten. Editor-based reword failures are reported without corrupting history.

`A` opens `Amend commit` and asks `Are you sure you want to amend this commit with your staged files?`; amending HEAD consumes staged changes, preserves its message, changes its hash, and does not change commit count. Amending an older commit performs the equivalent history rewrite. No-staged-files amend fails safely.

`s` squashes the selected commit into the one below after `Are you sure you want to squash the selected commit(s) into the commit below?`, combining content and messages and reducing count. `f` performs fixup and discards the fixup message; the menu also offers `Fixup and use this commit's message`. `F` creates a `fixup! <selected subject>` or `amend!` commit from staged changes. `S`/the fixup menu applies matching fixups above a base commit. These operations work for ranges and branch stacks and preserve final file content.

## Spec 20

From Commits, `i` enters interactive rebase mode only when there is an appropriate base commit. For example, on a feature branch with commits beyond the configured main branch, the mode shows `--- Pending rebase todos ---`, labels its todo entries `pick`, and shows `Rebasing (Reset)`. If the HEAD commit is a merge commit or is present on the main branch, `i` does not enter the mode; it opens `Error` with exactly ``Cannot start interactive rebase: the HEAD commit is a merge commit or is present on the main branch, so there is no appropriate base commit to start the rebase from. You can start an interactive rebase from a specific commit by selecting the commit and pressing `e`.`` Ctrl-J/Ctrl-K reorder the selected todo down/up, including multiple moves and top/bottom boundaries. `d` drops one or a range after confirmation. `s` and `f` squash/fixup todos; `e` marks edit/break behavior. The resulting Git history and file contents must match the reordered/dropped/combined plan.

The tested rebase editor supports repeated moves, moving to the top, dropping multiple commits or the bottom commit, and sequential fixups. Editing may stop at a commit; Escape/cancel aborts or dismisses without unwanted changes. Conflicts expose normal conflict resolution and permit continuation or abort without corrupting unrelated state.

## Spec 21

Commit `C` toggles copying the selected commit or selected range; the UI reports `1 commit copied`/`N commits copied`, toggling the same selection removes it, and Ctrl-R resets the copied set. Todo commits cannot be copied. `V` on a target branch asks `Are you sure you want to cherry-pick...` and cherry-picks copies in chronological order, creating new hashes and identical content/messages. It works with one or multiple commits, reflog context, range toggling, and empty ranges. Paste with nothing copied does nothing and shows no confirmation.

On conflict, show `(cherry-picking)` and `Pending cherry-picks`; after resolution continue the sequence. Abort restores the original target commit count/history.

## Spec 22

During a merge conflict, Status includes `(merging)`, Files shows each unresolved file as `UU`, and the diff displays literal `<<<<<<< HEAD`, `=======`, and `>>>>>>>` sections. Enter opens conflict selection. Space on the first alternative chooses ours; Down then Space chooses theirs; `b` chooses both in ours-then-theirs order. Resolution removes conflict markers, writes the chosen contents, stages the file, and when all conflicts are resolved displays `All merge conflicts resolved. Continue the merge?` plus `Merging (Reset)`. Escape returns to Files without resolving. Resolving one of multiple files leaves other `UU` files and their markers untouched.

For the standard three-line conflict used here, ours yields exactly `line 1 - master version\nline 2\nline 3\n`, theirs substitutes `feature version`, and both insert both first lines before lines 2 and 3. The post-resolution terminal layout is the ordinary 80x24 dashboard: ours may show `No changed files`, while theirs/both show a `Staged changes` unified diff and the Continue popup centered across the panes.

For complete rendering precision, the three normalized post-resolution snapshots are below. `XXXXXXXX` stands for the selected eight-hex-digit commit hash. The command-log row is normalized to the literal placeholder shown. Repository names are the fixed names displayed in each block.

Ours:

```text
╭─[1]─Status──────────────╮╭─[0]─Diff──────────────────────────────────────────╮
│(merging) test_tui_confli││No changed files                                   │
╰─────────────────────────╯│                                                   │
╭─[2]─Files - Worktrees -─╮│                                                   │
│                         ││                                                   │
│                         ││                                                   │
│                         ││                                                   │
│                         ││                                                   │
│                         ││                                                   │
│                         ││                                                   │
│╭─Continue────────────────────────────────────────────────────────────────────╮
││All merge conflicts resolved. Continue the merge?                            │
│╰─────────────────────────────────────────────────────────────────────────────╯
╰──────────────────0 of 0─╯│                                                   │
╭─[3]─Local branches - Re─╮│                                                   │
│  * master               ││                                                   │
╰──────────────────1 of 2─╯│                                                   │
╭─[4]─Commits - Reflog────╮│                                                   │
│XXXXXXXX TU ◯ Master     ││                                                   │
╰──────────────────1 of 2─╯╰───────────────────────────────────────────────────╯
╭─[5]─Stash───────────────╮╭─Command log───────────────────────────────────────╮
│                         ││(command log)                                         │
╰──────────────────0 of 0─╯╰───────────────────────────────────────────────────╯
View merge options: m | Confirm: <enter> | Close/Cancel: <esc> | Merging (Reset)
```

Theirs:

```text
╭─[1]─Status──────────────╮╭─[0]─Staged changes────────────────────────────────╮
│(merging) test_tui_pick_t││diff --git a/file1.txt b/file1.txt                 ▐
╰─────────────────────────╯│index 552a62b..d1814c0 100644                      ▐
╭─[2]─Files - Worktrees -─╮│--- a/file1.txt                                    ▐
│M  file1.txt             ││+++ b/file1.txt                                    ▐
│                         ││@@ -1,3 +1,3 @@                                    ▐
│                         ││-line 1 - master version                           ▐
│                         ││+line 1 - feature version                          ▐
│                         ││ line 2                                            ▐
│                         ││ line 3                                            ▐
│╭─Continue────────────────────────────────────────────────────────────────────╮
││All merge conflicts resolved. Continue the merge?                            │
│╰─────────────────────────────────────────────────────────────────────────────╯
╰──────────────────1 of 1─╯│                                                   ▐
╭─[3]─Local branches - Re─╮│                                                   │
│  * master               ││                                                   │
╰──────────────────1 of 2─╯│                                                   │
╭─[4]─Commits - Reflog────╮│                                                   │
│XXXXXXXX TU ◯ Master     ││                                                   │
╰──────────────────1 of 2─╯╰───────────────────────────────────────────────────╯
╭─[5]─Stash───────────────╮╭─Command log───────────────────────────────────────╮
│                         ││(command log)                                         │
╰──────────────────0 of 0─╯╰───────────────────────────────────────────────────╯
View merge options: m | Confirm: <enter> | Close/Cancel: <esc> | Merging (Reset)
```

Both:

```text
╭─[1]─Status──────────────╮╭─[0]─Staged changes────────────────────────────────╮
│(merging) test_tui_pick_b││diff --git a/file1.txt b/file1.txt                 ▐
╰─────────────────────────╯│index 552a62b..ad80c96 100644                      ▐
╭─[2]─Files - Worktrees -─╮│--- a/file1.txt                                    ▐
│M  file1.txt             ││+++ b/file1.txt                                    ▐
│                         ││@@ -1,3 +1,4 @@                                    ▐
│                         ││ line 1 - master version                           ▐
│                         ││+line 1 - feature version                          ▐
│                         ││ line 2                                            ▐
│                         ││ line 3                                            ▐
│╭─Continue────────────────────────────────────────────────────────────────────╮
││All merge conflicts resolved. Continue the merge?                            │
│╰─────────────────────────────────────────────────────────────────────────────╯
╰──────────────────1 of 1─╯│                                                   ▐
╭─[3]─Local branches - Re─╮│                                                   │
│  * master               ││                                                   │
╰──────────────────1 of 2─╯│                                                   │
╭─[4]─Commits - Reflog────╮│                                                   │
│XXXXXXXX TU ◯ Master     ││                                                   │
╰──────────────────1 of 2─╯╰───────────────────────────────────────────────────╯
╭─[5]─Stash───────────────╮╭─Command log───────────────────────────────────────╮
│                         ││(command log)                                         │
╰──────────────────0 of 0─╯╰───────────────────────────────────────────────────╯
View merge options: m | Confirm: <enter> | Close/Cancel: <esc> | Merging (Reset)
```

## Spec 23

The Local branches tab lists current/local branches with `*`, HEAD state, upstream status, divergence arrows/counts, and configurable `date`, `recency`, or `alphabetical` sort. `c` prompts for a ref name with live suggestions and checks it out; a nonexistent name can be confirmed to create a branch. New-branch actions apply configured branch prefixes; `R` renames (spaces become dashes) and updates the checked-out name. New-branch creation auto-stashes and restores dirty work when required.

`d` deletes a selected local branch after confirmation, including while list filtering is active; it does not delete unrelated refs. `u` sets or unsets upstream as selected. The Remotes tab shows a remote plus a count such as `3 branches`; at the default 80-column width, the side-panel tab strip is clipped to `Local branches - Re`, and after switching to the populated remote view the main pane's literal title is singular `Remote`, not `Remotes`. The row still shows text such as `origin 2 branches`. Enter opens `Remote branches`, lists its refs, and displays `Checkout: <space>`. Space checks out a remote ref as a local tracking branch, while `n` asks `New branch name` and suggests the remote leaf name. `u` asks `Set upstream branch` and identifies both local and remote names. Remote branches use configurable `date`/`alphabetical` order. `d` asks `Delete branch`, names the branch and remote, and deletes the remote ref without deleting unrelated local/tag refs; it respects a differently named upstream and supports a credential prompt.

## Spec 24

Branch merge supports the tested squash merge (`Squash merge <selected> into <current>` by default). Branch `r` rebases the current branch onto the selected/upstream/base branch; `B` on commits marks a base usable by later branch rebase, and copied branches can be rebased. Conflicts enter the resolver and allow cancel/abort or continue after fixes.

Reset-to-upstream/base/tag resolves fully qualified refs correctly even when a tag, local branch, or upstream shares a short name. Selecting commits of the current branch with `*` selects only that branch’s unique commits. Divergence display supports none, arrow-only, or arrow-and-number and shows ahead/behind from upstream or marked base without inventing divergence when none exists.

## Spec 25

Branch pull-request action `o` handles hosting remotes. With no upstream it asks for/selects a remote and target branch; with multiple remotes it displays choices and validates the target remote name. It forms an appropriate pull-request URL or reports a clear error, never corrupting refs. Status/remote commands cope with nonexistent, invalid HTTPS, and multiple remotes: push/fetch/pull errors return control to the TUI, and the Status and Local branches panels remain responsive. Help remains accessible after authentication/remote failures. Status shows current branch and repository basename.

## Spec 26

The Reflog tab displays recent HEAD operations (commits, branch checkouts, resets, cherry-picks, and merges) newest first with commit details. From a selected entry the user can create a branch. Navigation updates the selected commit’s details. Multiple sequential resets and other operations appear as distinct entries. Reset semantics invoked from the reset menus are as specified in Spec 15. Duplicate named refs are resolved according to the explicitly selected ref, not ambiguous short-name guessing.

## Spec 27

The Stash panel lists newest stash first and handles an empty list. At 80 columns, focusing an empty Stash retains the literal title prefix `╭─[5]─Stash` with no inserted `*`, and the main pane displays `No stash entries`. It represents multiple stashes in LIFO order and can include untracked content. Stash `g` pops and removes the entry, apply restores but retains it, drop deletes it, and `r` renames its message.

## Spec 28

Fetch, pull, and push operate on configured remotes and refresh divergence indicators. Before push, ahead state appears as `↑N`; after a successful push it becomes a check mark `✓` and Git reports no ahead count. Fetch updates remote-tracking refs without changing local HEAD. Pull incorporates remote commits and leaves a clean, synchronized indicator; pulling an already-equal/empty remote is a no-op. Multiple commits and explicit remote ref updates are supported. Operations requiring upstream prompt to select/set it; force/follow-tags/tag pushing and merge/rebase pull modes follow configuration and conflicts use the normal resolver.

## Spec 29

From a commit, `T` opens fields `Tag name` and `Tag description`. Empty description creates a lightweight tag; a description creates an annotated tag containing the full multiline description and tagger identity. The Tags view distinguishes `Lightweight tag: <name>` and `Annotated tag: <name>`, shows `Tagger:`, tag message, referenced commit, and multiple tags on one commit. Tags may include valid slashes such as `release/v1.0.0`. Delete is confirmed and removes only the selected local tag; cancellation leaves it. Creating an existing tag prompts to force/overwrite, and confirmation retargets it to the selected commit.

## Spec 30

The Worktrees tab lists every `git worktree` with basename, branch, current marker `*`, counters, and main-worktree label such as `main_repo (main)`. It is reached by first focusing Files with `2` and then pressing `]` once; `n` opens options including `Create worktree from ref` and `Create worktree from ref (detached)` (`w` is also the configured worktree-options binding). Creation prompts in order for `New worktree base ref` (suggesting the selected/current branch), `New worktree path`, and, for attached creation, `New branch name` with a leave-blank checkout hint. It creates a valid populated worktree and refreshes the list; detached worktrees display `(no branch)`/detached HEAD.

Enter/switch changes the application’s active repository and visibly reports `repo → branch`. Removing a noncurrent worktree asks `Are you sure you want to remove worktree '<name>'?`, deletes it from Git and disk, and leaves others intact. Escape cancels. The current worktree cannot be removed and remains listed.

## Spec 31

Repositories containing submodules show a Submodules tab/context with each path, URL, and initialized/uninitialized/dirty status; an initialized item has a check mark. It is the tab after Worktrees: from the dashboard, `2]]` focuses Files and advances twice to Submodules. By contrast, `1]` leaves the application in Status and does not open submodules. In the selected view, the main pane title is singular `Submodule` and its details include literal `Name: <path>`, `Path: <path>`, and `Url:  <url>` rows. Enter logs `Changing directory to <path>`, changes into the selected submodule context, and its panels show that repository. `i` initializes and logs `git submodule init`; `u` updates to the recorded commit and logs `git submodule update --init -- <path>`. `b` opens `Bulk submodule options` containing `Bulk init submodules`, `Bulk update submodules`, `Bulk init and update submodules recursively`, and `Bulk deinit submodules`. Removal asks `Remove submodule` and updates `.gitmodules`/index/worktree consistently; when the last is removed show `No submodules`. Nested repository state and uncommitted submodule changes remain visible.

## Spec 32

Patch-building mode can start from a commit file or unstaged changes. Before selection it says `No patch created yet` and instructs the user to use `space` on a commit file. A nonempty patch is titled `Custom patch`; fully chosen files use `●` and partial files `◐`. Space/a toggles whole hunks, line mode permits partial selection, Up/Down navigates hunks, and selection spans multiple files and large hunks while visibly removing/adding chosen content. Reset clears the markers and `Custom patch`; Escape returns to `Diff files`/the prior view; requesting options for an empty patch shows an error. Ctrl-P opens a patch options menu.

The `Patch options` menu visibly contains `Reset patch`, `Apply patch`, `Apply patch in reverse`, `Copy patch to clipboard`, `Remove patch from original commit`, `Move patch out into index`, and `Move patch into new commit`. Where applicable it adds `m Move patch to selected commit`, `n Move patch into new commit after the original commit`, and `N Move patch into new commit before the original commit`. Copying uses the normal no-clipboard diagnostic. These operations apply the exact chosen lines/files and rewrite history/index accordingly while preserving unrelated content. Reverse application produces the inverse work-tree effect. Applying to the index while unstaged files exist asks `Must stage files`, explains `Applying a patch to the index requires staging the unstaged files`, and asks `Continue?`; cancellation is safe.

## Spec 33

`customCommands` entries bind `key`, `context`, `description`, shell `command`, optional `prompts`, `output`, and `outputTitle`. Context matching is exact for `files`, `localBranches`, `commits`, `status`, etc.; `global` works from every panel. Bindings appear in searchable Keybindings help as `<key> <description>`. Execute commands with the repository as working directory and refresh afterward.

Template expansion supports at least `{{.SelectedFile.Name}}`, `{{.SelectedCommit.Hash}}` (the displayed eight-character hash), `{{.SelectedCommit.AuthorName}}`, and `{{.Form.<Key>}}`. The `quote` pipeline shell-quotes filenames with spaces/metacharacters. Input prompts show title and initial value, accept Ctrl-U replacement, and bind the entered text. Confirm prompts display title/body, execute only on Enter, and cancel on Escape. Menu prompts display named choices, navigate with Down, and bind the selected `value`. `output: popup` displays stdout under `outputTitle`; terminal output runs interactively.

## Spec 34

`W` (or Ctrl-E) opens a `Diffing` menu containing `Enter ref to diff` and `Cancel`. Its `Enter ref:` prompt includes a `Suggestions` panel with refs such as HEAD/current branch. Active mode displays a Git diff, `(Reset)`, `Reverse diff direction`, and `Exit diff mode`; exit restores `Unstaged changes` and removes `(Reset)`. Ctrl-S opens `Filtering`, with choices such as `Filter by '<selected-file>'`, `Enter path to filter by`, author names, and later `Stop filtering`. Filtering by path shows only commits touching that file/directory; filtering by author shows that author’s commits; exit restores the full count. CLI filter mode similarly limits commits/reflog/stash and restricts inappropriate operations. Search and filters update dynamically and remain usable with no matches.

Checkout-by-name/ref prompts provide case-insensitive substring and fuzzy suggestions, update on every typed character, and include local branches, remote refs, tags, and applicable pseudo-refs `HEAD`, `FETCH_HEAD`, `MERGE_HEAD`, and `ORIG_HEAD`. Names with hyphens, underscores, and slashes are preserved. The list has an `N of M` counter, narrows as text changes, displays `0 of 0` while retaining the typed query on no match, and Enter chooses the selected suggestion. Empty repositories return safely to the normal Status/Files UI.

## Spec 35

Commit `b` opens Bisect actions. Starting with a bad or good mark writes real `git bisect` refs and annotates rows `<-- bad`, `<-- good`, `<-- current`, or `<-- skipped`; the bottom/status action changes to `Bisecting (Reset)`. Skipping invokes `git bisect skip`. When the first bad commit is identified, show `Bisect complete!`, its subject/hash, and `Do you want to reset 'git bisect' now?`. Confirming reset removes annotations and bisect refs. Reset mid-run asks `Are you sure you want to reset 'git bisect'?`; cancellation of menus does not begin/reset bisect.

## Spec 36

Universal `z` and `Z` undo/redo recorded destructive actions. Undoing a commit asks for and performs a soft reset, removing the commit but leaving its files staged; redo asks for a hard reset and restores the exact commit/hash. Undoing/redoing checkout asks for the target branch and switches accordingly. Escape at confirmation makes no change. Multiple undos/redos walk the action stack in order. When a dirty working tree would be overwritten, the confirmation mentions an `auto-stash` “performed if necessary”, and local changes survive.

## Spec 37

The options menu (`?` in applicable contexts) is titled `Keybindings` and organizes context-sensitive entries under `--- Local ---`, global entries, and `--- Navigation ---`. In Files it includes `Copy path to clipboard`, `Stage`, and `Commit`; navigation includes `Toggle whitespace` and `Undo`. Home/End reach the first/last portions. Ctrl-W toggles ignoring whitespace in diffs and immediately changes both staged-file and commit diffs, marking their title `(ignoring whitespace)`; its state persists as selection changes. In the staging/hunk view it instead shows `Error` and the exact message `Ignoring whitespace is not supported in this view`. `{`/`}` change diff context and `(`/`)` adjust rename similarity. `+` and `_` change among usable normal, half, and full screen layouts without blanking or crashing the interface. Initial `--screen-mode normal|half|full` must also render a populated TUI. Version mode accepts and bypasses validation of an otherwise unrecognized screen-mode value.

## Spec 38

Commit base-finding (`Ctrl-F` from Files) analyzes staged/deleted lines with blame/history and offers candidate commits for a fixup. It must identify the commit that introduced a deleted/changed line, handle deleted files, ignore existing fixup commits as candidate bases, and create a fixup with `F`. Added-only changes either produce an explanatory warning/candidate behavior and never choose the configured main branch improperly. On a main branch, show `Error` and `The base commit for this change is already on the main branch`; with no changed files, show an error and do not change history. Nested `fixup! fixup! ...` subjects are recognized as fixups.

## Spec 39

Recent repositories (`Ctrl-R` or Status Enter) presents known repositories with path/current branch and detached-HEAD notation. Escape cancels. Selecting a non-Git target produces an error and leaves the current repository active.

## Spec 40

The UI must remain functional across repositories with many commits/branches/files, long commit messages, tags, stashes, worktrees, submodules, remotes, staged and unstaged changes, an empty repository, detached HEAD, merge conflict, and failed credential/remote operations. Numeric panel selection, Tab cycling, arrow/HJKL navigation, searches, menus, refreshes, screen-mode toggles, Enter/Escape patterns, Ctrl sequences, and terminal resize may be exercised repeatedly in one session. Each redraw must retain recognizable panel text (`Status`, `Files`, `Local branches`/`branch`, `Commits`/`commit`, `Stash`) and never leave the terminal blank or the process unresponsive.

## Spec 41

Branch-history edge operations must update Git rather than merely repainting: delete selected branches, reset to upstream/explicit refs, rebase onto upstream/marked/copied bases, and select branch-specific commits. Remote branch deletion must address the selected remote ref even when the local tracking name differs. Sorting and divergence indicators must refresh after each operation. Confirmation Escape always leaves refs and the work tree unchanged.

The broad harvested commit/rebase scenarios also launch the executable in repositories containing ordinary, merge, fixup, amend, tagged, stacked-branch, update-ref, conflict, and in-progress-rebase histories. In every such valid state startup must render more than 50 characters containing a recognizable `lazygit`, `branch`, or `commit` UI label; focusing Commits with `4` must also remain populated, and `q` must stop cleanly.

## Spec 42

Output-channel and status conventions are strict. Help is stderr/0; version, config, and config-directory are stdout/0 with empty stderr. Parser syntax failures are 2 with usage. Invalid positional values, invalid repositories, incompatible path modes, work-tree change failures, missing/invalid config in modes that load it, and missing log files are status 1/nonzero and use stderr for the diagnostic. Repository/config errors begin with a `YYYY/MM/DD HH:MM:SS` timestamp when described above. Interactive Git failures are shown inside the UI and return control rather than terminating or partially applying unrelated work. All noninteractive text is UTF-8, deterministic where specified, free of terminal color escapes, and newline-terminated unless explicitly described as a continuing stream.
