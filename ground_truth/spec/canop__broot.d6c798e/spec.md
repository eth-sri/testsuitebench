# Clarified specification: `executable`

## Spec 1: Deliverable and identity

Produce one executable file named exactly `executable` at the repository root. It must be runnable on Linux and implement the command-line and terminal behavior described below. It is a compatible implementation of **broot 1.54.0**, a single-mode terminal file browser; it does not use subcommands.

The evaluation environment supplies a PTY/TUI driver named `tui2cli`. That driver is harness infrastructure, not part of this deliverable. Some evaluation may also invoke `cargo test` against harness-provided repository source; that source and those test commands are likewise not behavior assigned to `executable`.

Unless an early-exit operation is requested, launch an interactive terminal UI rooted at the optional `ROOT`. With no root, use the current directory. A directory argument may appear before, after, or between options. At most one positional root is accepted. Ordinary words such as `add`, `list`, `help`, or `version` are paths, not subcommands.

## Spec 2: Early output and exit behavior

- `--version` writes exactly `broot 1.54.0\n` to standard output, writes nothing to standard error, and exits 0.
- `--help` writes styled, width-dependent UTF-8/ANSI help, writes nothing to standard error, and exits 0. When stdout is captured without a terminal or an explicit width, the effective width is 80 columns and stdout is exactly the 11,182 bytes in `resources/cli-help.txt`. A 50-column output terminal instead produces the exact bytes in `resources/cli-help-50.txt`. Both resources include their final LF. A sized 80-column stdout TTY with non-TTY stdin also produces `resources/cli-help.txt` exactly. When stdin and stdout are the same 80-column PTY, the raw output is instead the 11-byte terminal-interrogation prefix `ESC ] 1 1 ; ? BEL ESC [ 5 n` followed immediately by `resources/cli-help.txt`; the literal byte sequence is `\x1b]11;?\x07\x1b[5n`. `--color no` does not remove the ANSI styling: at a given width its help body is byte-for-byte identical to `--help` without an explicit color option. These resource paths, like every `resources/` path below, are relative to this specification file and the files are part of the normative specification.
- The help describes one usage form, `broot [options] [ROOT]`, a `Root Directory`, and an options table. It has no Commands or Subcommands section.
- The help includes the exact prose `broot lets you explore file hierarchies with a tree-like view`, the line `Complete documentation and tips at https://dystroy.org/broot`, and the option description `Show the last modified date of files`. Its table contains every one of `┌`, `┬`, `┐`, `└`, `┴`, `┘`, and `│`, in the positions recorded in the width-specific resources.
- A valid single root may accompany `--help` or `--version`. Argument validation still happens: an unknown option or a second root is an error even if an early-output option is present.
- Independent early actions compose. In particular, `--print-shell-function bash --version` prints the version line first and then the shell function.
- Early version handling is not made fatal by an unexpected `BR_INSTALL` value or by malformed content in a file named by `--conf`.
- Early help handling likewise does not change its help body after a syntactically valid `--conf`, including an empty file, HJSON comments and whitespace, unknown or unusable fields, Unicode, legacy TOML, imports or nested imports, a long absolute path, or a semicolon-separated list. At 80 columns all of those invocations produce the `resources/cli-help.txt` body; the same-PTY case retains the terminal-interrogation prefix described above.

## Spec 3: Command-line grammar and validation

Support space-separated and `--option=value` forms for value options. Support combined short Boolean flags such as `-dD`, `-sdp`, `-ghi`, and `-DSFHIGP`. `--` terminates option parsing; subsequent dash-prefixed tokens are positional values.

Recognize these Boolean options and counter-options:

| Feature | Enable | Disable |
|---|---|---|
| dates | `-d`, `--dates` | `-D`, `--no-dates` |
| folders only | `-f`, `--only-folders` | `-F`, `--no-only-folders` |
| git information | `-g`, `--show-git-info` | `-G`, `--no-show-git-info` |
| hidden entries | `-h`, `--hidden` | `-H`, `--no-hidden` |
| git-ignored entries | `-i`, `--git-ignored` | `-I`, `--no-git-ignored` |
| permissions | `-p`, `--permissions` | `-P`, `--no-permissions` |
| sizes | `-s`, `--sizes` | `-S`, `--no-sizes` |
| root trimming | `-t`, `--trim-root` | `-T`, `--no-trim-root` |
| whale spotting | `-w`, `--whale-spotting` | `-W`, `--no-whale-spotting` |
| tree layout | `--tree` | `--no-tree` |

Also recognize `--show-root-fs`, `--git-status`, `--sort-by-count`, `--sort-by-date`, `--sort-by-size`, `--sort-by-type`, `--sort-by-type-dirs-first`, `--sort-by-type-dirs-last`, `--no-sort`, `--install`, `--listen-auto`, and `--get-root`.

Recognize the value options `--conf`, `--max-depth`, `--height`, `-c`/`--cmd`, `--color`, `--outcmd`, `--verb-output`, `--set-install-state`, `--print-shell-function`, `--listen`, `--send`, and `--write-default-conf`.

- `--color` accepts only `auto`, `yes`, and `no` and cannot be supplied more than once.
- `--set-install-state` accepts only `undefined`, `refused`, and `installed`.
- `--height` and `--max-depth` parse unsigned decimal integers. `--max-depth` accepts exactly the inclusive range `0..=65535`: `65535` is valid, while `65536` and `4294967296` exit 2 with errors saying the value `is not in 0..=65535`. Nonnumeric and negative forms fail cleanly. `--height 0` is accepted for a runtime TUI launch and leaves the TUI running rather than exiting with a diagnostic: with no input in a 24-by-80 PTY, it remains alive after at least four seconds and its terminal output contains none of `Termimad Error`, `IO error`, or `IO Error`.
- Repeated counter-flags and competing sort modes are accepted. For the competing type modes, `--sort-by-type-dirs-last` takes precedence whenever both it and `--sort-by-type-dirs-first` occur, regardless of their order; either option by itself has its named effect. Paired feature counters don't use occurrence order: if both the enabling and disabling CLI flag occur, the enabling flag wins. Thus all of `-hH`, `-Hh`, `-h -H`, `-H -h`, `--hidden --no-hidden`, and the reverse long-option order show hidden entries and render `h:y`. Likewise `-dsp -DSP` keeps dates, sizes, and permissions enabled, and supplying both forms of the folders-only pair keeps folders-only mode enabled. A disabling flag used without its enabling counterpart still disables the feature. The git-ignore pair follows the same positive-precedence rule for visibility: `--git-ignored --no-git-ignored` includes ignored paths. Its indicator is inverse-polarity: inclusion renders `gi:n`, while the default exclusion of ignored paths renders `gi:y`.
- Every value option rejects a missing value. An empty string is nevertheless a present and valid value for `--cmd`.
- Unknown options, extra positional arguments, invalid enums, and malformed integer values exit 2 and report a clap-style error on standard error. The error names the offending option/value and includes a usage line where applicable. Similarity changes both the tip and the usage form: `--not-real` writes exactly `error: unexpected argument '--not-real' found\n\n  tip: a similar argument exists: '--no-tree'\n\nUsage: executable --no-tree [ROOT]\n` to stderr and exits 2 with empty stdout. Invalid enums list their possible values; near `installed`, the install-state error suggests that similar value.
- A nonexistent root or a nonexistent configuration used for an ordinary launch with first-run prompting suppressed exits 1 with `IO Error : No such file or directory (os error 2)\n` on standard error. If no install decision exists and prompting is enabled, the first-run installation question occurs before root validation; declining it does not skip validation, so a nonexistent root then prints that I/O error and exits 1.

The following plain stderr forms are normative (each ends in one newline unless the block visibly ends otherwise):

```text
error: invalid value 'invalid' for '--color <color>'
  [possible values: auto, yes, no]
```

```text
error: invalid value 'abc' for '--height <height>': invalid digit found in string
```

```text
error: invalid value 'xyz' for '--max-depth <MAX_DEPTH>': invalid digit found in string
```

For the invalid install state `invalid_value`, stderr is:

```text
error: invalid value 'invalid_value' for '--set-install-state <state>'
  [possible values: undefined, refused, installed]

  tip: a similar value exists: 'installed'
```

For two roots `/tmp /var`, stderr is:

```text
error: unexpected argument '/var' found

Usage: executable [OPTIONS] [ROOT]
```

All valid display, sorting, git, root, color, height, depth, and path options must remain valid when combined with `--version` and produce only the normal version output (apart from explicitly composable early actions described above).

## Spec 4: Configuration

Read relaxed HJSON configuration and legacy TOML. The parser for every file named by `--conf` is chosen solely from its final filename extension, compared case-insensitively: `.hjson` selects HJSON and `.toml` selects legacy TOML. No other extension is accepted. In particular, a `.conf` file is rejected before its contents are inspected: the process exits 1 with empty stdout and the single stderr line `Bad configuration: unexpected file extension in "<PATH>"`, where `<PATH>` is the file path exactly as supplied (a relative path stays relative in this diagnostic). `--conf` accepts a semicolon-separated ordered list. Merge files in order, with later settings taking precedence. Resolve relative configuration paths against the process working directory when opening accepted files. HJSON supports comments, unquoted keys, trailing commas, UTF-8, empty objects/strings, and an `imports` array; imports are recursively loaded, including nested imports.

The concrete schema matters:

- `default_flags` is one string containing CLI flags, for example `default_flags: -h` or `default_flags = "-h"` in legacy TOML. It is not an object of Boolean members. A TOML `[default_flags]` table is rejected with a bad-configuration diagnostic containing `invalid type: map, expected a string`.
- `imports` is an array whose entries are either quoted path strings or objects containing `file` and an optional `luma` condition. Path entries must be quoted even when they are simple filenames: both `[verbs.hjson]` and `[sub/next.hjson]` fail HJSON parsing with `Eof at 2:1`, while `["verbs.hjson"]` and `["sub/next.hjson"]` are accepted. Each import path resolves relative to the file containing that import. Nested imports use this same representation; for example, a quoted `"sub/next.hjson"` may itself import quoted `"final.hjson"` relative to `sub/`.
- Unknown fields in an otherwise valid document are ignored. An unusable type for a recognized field is not promised to be ignored and may make the configuration invalid. In particular, the compact HJSON value `{ default_flags: { show_hidden: true } }` is rejected rather than enabling hidden files.

For an ordinary interactive launch, a missing specified file is an I/O error and malformed HJSON reports `Bad configuration file` and `unable to parse Hjson`. Valid configuration can add verbs and `default_flags`. Command-line counter-flags override corresponding configured defaults.

`BROOT_CONFIG_DIR` selects the default configuration directory. Otherwise respect XDG configuration location, falling back to `$HOME/.config/broot`. `BR_INSTALL=no` suppresses the first-run shell-function installation question. Early operations remain usable with `BR_INSTALL=yes` or an unrecognized value.

Before an ordinary launch or a remote-client operation, an empty resolved configuration directory is initialized with the same eleven bundled default files listed in Spec 5. This happens even when the subsequent operation fails. Initialization writes the following three stdout lines. The ANSI-bold span includes both quote characters: the first line's byte order is `New Configuration files written in `, `ESC[1m`, `"<CONFIG_DIR>"`, `ESC[0m`, `.\n`. Normal processing then continues:

```text
New Configuration files written in "<CONFIG_DIR>".
You should have a look at them: their comments will help you configure broot.
You should especially set up your favourite editor in verbs.hjson.
```

Thus an empty configuration directory plus a nonexistent root exits 1 with this notice on stdout and the normal I/O error on stderr. Likewise, `--send MISSING --get-root` first emits this notice, then exits 1 with the socket diagnostic from Spec 13. The notice is not emitted once the default files already exist.

## Spec 5: Default configuration export

`--write-default-conf PATH` exits 0 and creates missing parent directories. It writes exactly the payload represented by `resources/default-conf/`:

- `conf.hjson`
- `verbs.hjson`
- `skins/catppuccin-macchiato.hjson`
- `skins/catppuccin-mocha.hjson`
- `skins/dark-blue.hjson`
- `skins/dark-gruvbox.hjson`
- `skins/dark-orange.hjson`
- `skins/native-16.hjson`
- `skins/solarized-dark.hjson`
- `skins/solarized-light.hjson`
- `skins/white.hjson`

Those bundled files are normative, substantive, parseable configuration. Export is deterministic and idempotent. Existing files, especially a customized `conf.hjson`, are not overwritten, while other missing defaults are still created. Follow a destination symlink to a directory. If the destination is an existing regular file, fail nonzero with an error containing `isn't a directory`. Files must be owner-readable and not world-writable.

The bundled bytes are included with this specification rather than merely named. Their reference-export sizes are: `conf.hjson` 10064 bytes, `verbs.hjson` 4796 bytes, and, in the order listed above, the nine skins 4767, 4754, 4131, 3813, 3802, 3146, 5190, 3597, and 2658 bytes. `verbs.hjson` includes the default `edit` verb. An export to a newly created nested directory, or through a directory symlink, creates these same eleven files and is silent on both streams.

## Spec 6: Shell integration and installation state

`--print-shell-function SHELL` supports the case-sensitive names `bash`, `zsh`, `fish`, `nushell`, and `powershell`. It exits 0, writes nothing to standard error, and emits exactly the corresponding file:

- `resources/shell-function-bash.txt`
- `resources/shell-function-zsh.txt`
- `resources/shell-function-fish.txt`
- `resources/shell-function-nushell.txt`
- `resources/shell-function-powershell.txt`

Bash and zsh outputs are identical. The wrappers invoke `broot --outcmd` through a temporary file, execute/source a produced command only after success, preserve failure status, and always remove the temporary file. An unsupported or differently-cased name exits nonzero, emits no stdout, and writes exactly `Unknown shell: <name>\n` to stderr.

Each bundled shell-function resource includes an LF as its first byte and an LF as its last byte. Bash, zsh, and fish begin after that initial LF with these exact two lines:

```text
# This script was automatically generated by the broot program
# More information can be found in https://github.com/Canop/broot
```

The complete reference payload sizes are 596 bytes for bash and zsh and 549 bytes for fish; the exact bytes, including comment preambles and blank lines, are the included resource files rather than only the functional description of the wrappers.

`--install` initiates installation/reinstallation of the `br` launcher and reports text mentioning installation, the launcher, or `br`. On a normal first interactive launch with no saved decision, present an installation question containing `Can I install it now?`; declining must allow a clean continuation/exit.

`--set-install-state STATE` stores state in the `launcher` subdirectory of the resolved configuration directory, creating parents as needed. Before storing the new state it recognizes and removes `refused` and the finite marker set `installed-v0` through `installed-v4`. It does not treat later-looking names as prior markers: `installed-v5`, `installed-v8`, and `installed-v99` are left in place.

- `refused` creates `launcher/refused` with the following exact content (including an LF as the first byte and a final LF):

  ```text

  This file tells broot you refused the installation of the companion shell function.
  If you want to install it run
      broot -- install
  ```

- `installed` creates exactly one version marker, `launcher/installed-v4`, with the following exact content (including an LF as the first byte and a final LF):

  ```text

  This file tells broot the installation of the br function was done.
  If there's a problem and you want to install it again run
      broot -- install
  ```

- `undefined` creates no marker and removes the recognized markers above. For every removed marker, in the order `refused`, then ascending installed version, stdout contains a separate newline-terminated `Removing <launcher-path>.` line with ANSI styling around the path. For example, given `refused`, `installed-v4`, and `installed-v8`, it reports and removes the first two and leaves `installed-v8` untouched.

All three state operations exit 0 and leave standard error empty. They are silent only when no recognized old marker is removed. In particular, `refused` given `installed-v2` and `installed-v99` reports removal of `installed-v2`, leaves `installed-v99`, and creates `refused`; `installed` given `refused` reports removal of `refused` and creates `installed-v4`.

## Spec 7: Core terminal UI and rendering

The UI must run correctly in a PTY, use the available terminal dimensions (the reference interactions use 24 rows by 80 columns), redraw in response to input, and restore the terminal on exit. `Ctrl-Q` exits with status 0.

The main panel shows the absolute current root as its header followed by a depth-first tree. Use `├──`, `└──`, and `│` connectors and indentation to preserve hierarchy. Entries are ordered deterministically by name in the default view. Directories and files have distinguishable ANSI styling. Selection is maintained as UI state and changes the context-sensitive bottom hint, but the captured 24-by-80 rendering does not draw a `▶` or reserve a selection column. Staged entries use `◍`. The bottom area consists of a context-sensitive hint, an input line, and right-aligned option indicators including `h:n`/`h:y` and `gi:y`/`gi:n`.

The plain-text result of rendering the ANSI screen at 24 rows by 80 columns has this exact geometry:

- The root header is row 1, column 1. Tree rows follow without an intervening blank row. Unused rows are blank through row 22, the hint is on row 23, and the option indicators are on row 24.
- An ordinary top-level tree connector begins in column 1. There is no reserved leading selection slot, and selected and unselected rows have the same connector geometry. There is no space after `├──` or `└──`, and directory names have no trailing `/`.
- Each deeper level occupies exactly three columns. A continuing ancestor is `│  ` and a noncontinuing ancestor is three spaces. Thus the observed nested forms include `│  └──nested.txt`, `│     └──file3.txt`, and `│        └──file4.txt`, whether or not that final file is selected.
- With default hidden and git-ignore settings, row 24 is exactly 69 ASCII spaces followed by `h:n  gi:y`. The two indicators are separated by two spaces. The row-23 default hint begins with one ASCII space.
- Permission metadata precedes the connector, not the name: examples are exactly ` rw_r__r__ root root ├──file1.txt` and ` rwxr_xr_x root root ├──folder1`. The initial space in those examples is metadata-column padding, not a selection slot. Date and size metadata likewise precedes the connector. Disabling a metadata mode removes its entire prefix and returns the connector to column 1.

At initial root selection the hint contains `Hit enter to go up, ? for help, or a few letters to search`. A selected directory uses `Hit enter to focus`; a selected file uses `Hit alt-Enter to open and quit, ? for help, or a space then a verb`. The compact hint must include `? for help`.

Display nested descendants, Unicode and special-character names, and directories with many entries without truncation-related crashes. The initial viewport is balanced so expanded descendants do not consume all 22 tree rows before later root-level entries: subtrees are collapsed as needed, their directory names gain ` …`, and root-level files remain visible. In the replayed tree with `dir_0` through `dir_9` (each containing ten nested files) followed by `file_0.txt` through `file_59.txt`, rows 2–11 are the ten collapsed `dir_N …` rows and row 12 is `file_0.txt`. Hidden entries are absent by default and visible when hidden display is enabled. `--only-folders` removes regular files; its counter-option restores both types. Date, size, and permission modes add correctly aligned metadata columns; dates use `YYYY/MM/DD HH:MM`, permissions use forms such as `rwxr_xr_x`/`rw_r__r__` plus owner and group, and sizes use numeric/human-readable units. Disabling a column removes it and reflows the tree.

The files under `resources/tui/` are normative 24-by-80 final-screen snapshots with a final LF. For a single-panel snapshot, replace the literal `{ROOT}` token with the tested absolute root; no other normalization is applied. The two split-panel snapshots `advanced-focus-bang-24x80.txt` and `panel-preview-text-24x80.txt` record a six-cell root in the six-cell `{ROOT}` token. At other root lengths, retain the same pane boundaries, right-pad a fitting header to its pane boundary, and left-truncate an overflowing path with a leading `…` so that its suffix fits. This is why a long preview root begins with a form such as `…preview_selected_text_exa0/panel` and long `:focus!` roots are ellipsized in both headers rather than inserted literally into the resource. The fixture trees and uses are:

- `browser-default-24x80.txt`: `dir1/nested.txt`, `dir2/another.txt`, and `file1.txt`; it is also the result after `:select_first` selects the root.
- `app-default-24x80.txt`: `dir1/nested1.txt`, `dir2/nested2.txt`, `file1.txt`, and `file2.txt`; the initial screen, a Down-navigation test's initial frame, and the screen restored after entering verb mode with Space and leaving it with Escape are byte-identical to this file.
- `app-down-once-24x80.txt` uses that same fixture after one Down key. It selects `dir1`, leaves its rendered row beginning `├──dir1`, and is the exact pre-Enter frame used when testing directory focus, Escape restoration, and the directory-versus-file hint.
- `display-default-24x80.txt`: `file1.txt`, `file2.md`, `folder1/nested.txt`, `folder2`, and `new_file.txt`. This is the resulting layout for each individual negative mode `--no-dates`, `--no-sizes`, `--no-permissions`, `--no-hidden`, `--no-show-git-info`, and `--no-only-folders` when no configuration enables the corresponding mode.
- `display-permissions-24x80.txt` and `display-only-folders-24x80.txt` are the exact `--permissions` and `--only-folders` screens for that display fixture.
- `advanced-default-24x80.txt`, `focus-relative-24x80.txt`, `focus-absolute-24x80.txt`, and `select-nested-24x80.txt` use the advanced fixture `dir1/file2.txt`, `dir2/subdir/file3.txt`, `dir3/deep/nested/file4.txt`, and `file1.txt`. The first file is the exact initial frame before Enter focuses a directory; the other three record the exact navigation results described in Spec 10.
- `advanced-focus-bang-24x80.txt` and `advanced-back-24x80.txt` use the same advanced fixture. They are respectively the canonical split layout for `:focus! dir1` (with headers transformed as described above) and the exact result of selecting `dir1`, focusing it with Enter, and executing `:back`.
- The panel-state fixture consists of `.hidden_file`, `dir1/nested.txt`, `dir2/other.txt`, `file1.txt`, and `file2.md`, with `other.txt` containing the one line `Other file`. `panel-permissions-24x80.txt`, `panel-hidden-24x80.txt`, `panel-sort-type-24x80.txt`, and `panel-clear-stage-24x80.txt` are the exact results of `:toggle_perm`, `:toggle_hidden`, `:sort_by_type`, and clearing a stage while `nested.txt` remains selected, respectively. `panel-preview-text-24x80.txt` is the canonical split layout for previewing `other.txt`, with its headers transformed as described above.

`--max-depth N` limits expansion depth without adding an ellipsis marker for a directory whose descendants were omitted by that command-line option. In particular, at depth 1 `alpha` remains visible and its `nested/deep.txt` descendants disappear, but the rendered `alpha` row has no `…`. This differs from viewport balancing, `:toggle_tree`, and some `:set_max_depth` results described below. Non-tree sort modes show one level. Type sorting with directories first places directories before files. Whale spotting combines size sorting with showing hidden and git-ignored entries.

## Spec 8: Navigation, filtering, help, and completion

- Up and Down move selection through visible entries in depth-first order and redraw the context-sensitive hint while leaving connector geometry unchanged. A Down followed by Up restores the earlier screen. Tree boundaries are safe; the filesystem list specifically wraps Up from its first row to its last row.
- Enter on a selected directory pushes the current panel state and focuses that directory. Enter while the root itself is selected goes to its parent. Escape pops exactly one saved state and restores both root and selection.
- Typing ordinary text echoes the pattern in the input line and starts search processing. Backspace removes the last character. Escape first clears a nonempty pattern and restores the full tree. If Escape is pressed again without an intervening focus or navigation action, selection resets to the root: the root hint `Hit enter to go up, ? for help, or a few letters to search` is shown and no entry remains selected. Subsequent Escape handling follows normal back navigation when a saved focus state exists.
- `:select_first` selects the root/first row and `:select_last` selects the last visible entry.
- Space enters verb-entry mode and shows `Type a verb then enter to execute it (? for the list of verbs)`. Escape leaves command mode and restores the underlying panel.
- `?`, F1, and the `:help` verb open the same scrollable help panel. It begins with `broot 1.54.0`, describes navigation, and contains `Search Modes` and `Verbs`. It includes the exact sentences `The esc key gets you back to the previous state.` and `fuzzy search on file name`. Escape clears an active help filter before closing help; with no filter it returns to the unchanged tree. Reopening help works repeatedly.
- Up/Down scroll help by lines, PgUp/PgDn by pages, and scrolling clamps at the top and bottom. Typed help-filter text is echoed on the input row but does not change the current help viewport in the observed 24-by-80 interaction. In particular, typing `matches` at the top leaves the first three example rows visible and does not bring the later `nt/` and `ep/` rows into the transcript; PgDn is needed to reveal those later rows.
- At 24 by 80, opening help, moving Down once, and then moving Up once returns the exact top frame in `resources/tui/help-top-24x80.txt`. It contains the exact lines `broot lets you explore directory trees and launch commands.`, `It's best used when launched as br.`, and `See https://dystroy.org/broot for a complete guide.`, uses a right-edge `▐` on panel-content rows, puts `Hit esc to get back, or a space to start a verb` on row 23, and puts `y` at column 78 on row 24.
- From that top frame, typing `search` produces `resources/tui/help-filter-search-24x80.txt`: the top help viewport remains in place and `search` appears at the start of row 24. Pressing PgDn at the top produces `resources/tui/help-page-down-24x80.txt`; its first row contains `tokens search on file name`.
- Help includes the exact search examples `f/conh matches DefaultConf.hjson`, `/rs$ matches build.rs`, `e/feat matches help_features.rs`, `nt/fea,he matches HelpFeature.java`, and `ep/te\\/do matches website/docs`.
- While a verb prefix is entered, show matching suggestions. For `:co`, suggestions include `copy`, `copy_to_panel`, and `counts`; repeated Tab cycles from `copy` to `copy_to_panel`. Escape during a completion cycle restores the original `:co`. A prefix such as `:xyz` has no `Possible verbs:` line and Tab leaves it unchanged.

The 24x80 tree/help/panel renderings are stable: padding blank rows, connectors, selection-dependent hints, status text, columns, and panel splits remain in fixed positions so snapshots are reproducible.

## Spec 9: Search language and content search

The help panel documents bare/`f/` fuzzy name search, `e/` exact name search, `/` regular-expression name search, `c/` exact content search, `cr/` content regular-expression search, and logical composition. Searches complete, retain the entered pattern on row 24, remove the `searching…` indication, and filter the visible tree.

The concrete search fixture contains `alpha/nested/deep.txt`, `apple.txt`, `Feature.md`, `.secret`, `unicodé file.txt`, and `zeta`; their relevant contents include `needle on a deep line`, `ordinary apple`, `Keyword and a.b literal`, `hidden needle`, and `café`. The completed results are:

- `aplt` and `f/aplt` each leave only `apple.txt`.
- `e/Feature` and `/feature/i` each leave only `Feature.md`.
- `/\.txt$/` leaves `alpha/nested/deep.txt`, `apple.txt`, and `unicodé file.txt`, with the ancestor directories needed to display `deep.txt`.
- `e/apple|e/Feature`, `e/apple|e/Feature&e/Feature`, `(e/apple|e/Feature)&!e/unicode`, and `!(!(e/apple))` leave no matching tree row in this fixture.
- `c/a.b` leaves `Feature.md` and displays its matching text `Keyword and a.b literal`.
- `cr/^needle/` leaves `alpha/nested/deep.txt` and displays `needle on a deep line`; `cr/\bKeyw[a-z]{3}\b/` leaves `Feature.md` and its matching line.
- `md&c/Keyword` leaves only `Feature.md` and its matching line.

The bare logical operators `|` and `&` have equal precedence and are evaluated left-to-right. On a fixture containing `README.md`, `test.rs`, `main.rs`, `test.md`, and `notes.txt`, `md|rs&test` is interpreted as `(md|rs)&test`: only `test.md` and `test.rs` remain, while `README.md` and `main.rs` are excluded.

Content search excludes files by recognized binary extension even when their bytes are readable text. If `image.png`, `binary.bin`, `doc.pdf`, and `text.txt` all contain `needle`, `c/needle` displays only `text.txt`; `.png`, `.bin`, and `.pdf` entries are excluded. Empty text files still participate in negated content searches: after adding `empty.txt`, `!c/impossible` completes and retains `empty.txt` along with every other nonhidden text candidate.

With hidden display enabled, typing `/^\.secret$/` completes and leaves only `.secret`; `apple.txt`, `Feature.md`, and the other nonmatching entries disappear, and no `searching…` indicator remains.

The built-in `:print_tree` command exposes the current tree in the terminal.

## Spec 10: Built-in verbs, panels, and configured execution

Commands are entered as `:verb [arguments]` and executed with Enter. `--cmd` accepts a semicolon-separated startup sequence; empty segments are tolerated. These commands run during startup, before the initial directory tree has finished populating. Consequently, a `:select PATH` segment in `--cmd` does not move the selection, although the same command entered after the tree is rendered does. Later startup segments operate on the unchanged initial root selection. A root that names a file makes that file the initial selection, allowing startup commands to operate on it. `:quit` terminates the session.

The startup timing is visible in these exact sample-tree sequences:

- `--cmd ":select apple.txt"` leaves the root selected and retains the root hint `Hit enter to go up, ? for help, or a few letters to search`.
- `--cmd ":select alpha;:focus"` leaves `alpha` unselected and focuses the parent of the initial root.
- `--cmd ":select Feature.md;:preview_text"` previews the selected root as a right-hand tree panel with `entries: 7`; it does not show the contents of `Feature.md`.
- `--cmd ":select apple.txt;:stage;:select Feature.md;:stage"` stages the same root twice, so the staging panel reads `count: 1`.

Required navigation verbs:

- `:focus PATH` changes the current root. Relative paths resolve from the current root; absolute paths work directly. With no path it follows the current selection; when the root is still selected, it focuses the root's parent just as Enter on the root does.
- `:focus! [PATH]` opens the focused directory in a second side-by-side panel while preserving the original panel. For the advanced fixture, `:focus! dir1` has the layout in `resources/tui/advanced-focus-bang-24x80.txt`, subject to the split-header padding and ellipsis rule in Spec 7.
- Once the tree is populated, `:select PATH` expands parents as needed and moves the selection. An absolute path works directly. A relative path resolves from the current selection's directory: from a selected directory that is the directory itself, and from a selected file it is the file's containing directory. The initial selection is the root directory, so typing `:select apple.txt` from that state selects the root's `apple.txt` row and changes the hint to the selected-file hint. After selecting `dir1/nested.txt`, however, `:select dir2/other.txt` looks below `dir1`, finds no such target, and leaves `nested.txt` selected; `:select ../dir2/other.txt` or the target's absolute path selects `other.txt`. The startup limitation above still applies. A nonexistent selection/focus target must not crash or terminate the UI.
- `:back` pops one saved focus state just like Escape. Selecting `dir1` in the advanced fixture, entering it, and then executing `:back` renders `resources/tui/advanced-back-24x80.txt` exactly.

For the advanced fixture defined in Spec 7, `:focus dir2` renders `resources/tui/focus-relative-24x80.txt`; focusing the absolute path to `dir3` renders `resources/tui/focus-absolute-24x80.txt`. Selecting either the relative or absolute path to `dir3/deep/nested/file4.txt` renders `resources/tui/select-nested-24x80.txt`: the root remains unchanged, the selected row has the same `│        └──file4.txt` geometry as an unselected row, and row 23 is exactly ` Hit alt-Enter to open and quit, ? for help, or a space then a verb`.

Required state/display verbs include `:sort_by_type` (directories first, with a confirmation message), `:toggle_perm`, `:toggle_hidden`, `:toggle_tree`, `:toggle_ignore`, and `:set_max_depth N`. Their changes update the visible columns/tree and the bottom indicators/messages. `:toggle_tree` collapses descendant-bearing root directories and appends ` …` to each collapsed directory: with `dir1/nested.txt`, `dir2/other.txt`, and `file1.txt`, its rows are `├──dir1 …`, `├──dir2 …`, and `└──file1.txt`, followed by ` displaying only current directory`. The verb form `:set_max_depth 1` uses an ellipsis when a deeper directory branch is omitted: with `dir1/nested.txt`, `dir2/sub/deep.txt`, and `file1.txt`, it renders `├──dir1`, `├──dir2 …`, and `└──file1.txt`, followed by ` max depth updated`. This verb behavior is distinct from the no-ellipsis `--max-depth` command-line case in Spec 7.

On the panel-state fixture from Spec 7, the first three applicable exact results are `resources/tui/panel-sort-type-24x80.txt`, `resources/tui/panel-permissions-24x80.txt`, and `resources/tui/panel-hidden-24x80.txt`. `:preview_text` opens a right-hand panel containing the selected text file, its name, content, and a `lines:` count; previewing `other.txt` in that fixture has the layout in `resources/tui/panel-preview-text-24x80.txt`, subject to the split-header padding and ellipsis rule in Spec 7. Neither the selected tree row nor the preview-content line is prefixed by `▶`.

Staging is supported with `:stage` or Ctrl-G. It marks the selected path and opens a right-hand `Staging Area` panel with `count: N`; opening that panel does not transfer focus, so the original tree remains active and the staged path remains selected. Multiple distinct stages increase the count. In the panel-state fixture, after selecting and staging `dir1/nested.txt`, either Down twice or `:select ../dir2/other.txt` selects `dir2/other.txt`; staging then changes the right-hand header from `count: 1` to `count: 2` and marks both tree rows with `◍`. By contrast, `:select dir2/other.txt` after the first stage resolves from `dir1` as specified above, finds no target, and leaves `nested.txt` selected, so another `:stage` leaves `count: 1`. `:unstage` removes the selected item; `:clear_stage` removes all items. An empty staging area closes the panel and removes all `◍` markers. In the panel-state fixture, staging `nested.txt` and then clearing the stage leaves that file logically selected, as shown by the selected-file hint, but draws no selection marker; the resulting screen is `resources/tui/panel-clear-stage-24x80.txt` exactly.

Configuration may define verbs as HJSON objects with `invocation`, `execution`, and optional `leave_broot`. `execution` may be another internal command string or an argv array/string for an external program. Quoted invocation arguments keep embedded spaces together, but their quote characters are not stripped: the written arguments `"hello world"`, `""`, and `"$HOME;*"` substitute respectively as the literal argv values `"hello world"`, `""`, and `"$HOME;*"`, including the displayed quote characters. Unicode and shell-special characters remain data. Substitute every occurrence of:

| Placeholder | Value |
|---|---|
| `{file}` | selected path, absolute |
| `{directory}` | selected directory, or selected file's containing directory |
| `{parent}` | parent directory |
| `{file-name}` | basename |
| `{file-stem}` | basename without only its final extension |
| `{file-extension}` | final extension without `.`; empty if absent |
| `{file-dot-extension}` | final extension with `.`; empty if absent |
| `{root}` | current session root |
| `{initial-root}` | launch root |
| `{line}` | selected line, default `0` |
| `{argument-name}` | corresponding parsed invocation argument |

Substitutions may be adjacent or repeated. With the quoted first argument above, `X{first}X{first}` becomes the single argv value `X"hello world"X"hello world"`, retaining all four quote characters. External commands must actually execute, with paths containing spaces kept as one logical value.

With `--verb-output PATH`, the destination's parent directory must already exist; the command does not create missing parents. When the parent exists, `:write_output TEXT` creates the file if needed, writes the first value without an added trailing newline, and appends later values separated by one newline while preserving punctuation. Thus the two writes `first value!` and `second: value?` produce exactly `first value!\nsecond: value?`. If the parent is missing, startup exits 1, creates no output file, and displays `IO Error : No such file or directory (os error 2)`. `:clear_output` truncates an existing destination. Without `--verb-output`, these commands are rejected harmlessly and the UI stays alive.

## Spec 11: Filesystem view

`:fs` opens a filesystem panel populated from the system's mounted filesystems. It has the exact column headings `filesystem`, `usage`, `free`, `size`, and `mount point`, a Unicode separator, and usage bars/percentages. The first data row is logically selected but no `▶` appears anywhere in the rendered filesystem screen. Up/Down move among mounts; text filters rows and is shown in the input line; no-match filtering leaves headers and no selected data row. Enter browses the selected mount in a normal tree panel, and state navigation can return to the filesystem list.

## Spec 12: Git integration

Git options must be harmless outside a repository. By default, git-ignored paths are hidden and no branch/status decoration is shown; this default exclusion state renders `gi:y`. `--git-ignored` includes ignored paths, and `--no-git-ignored` used without an enable leaves the default hidden state. Consistent with the positive-precedence visibility rule in Spec 3, the exact sequence `--git-ignored --no-git-ignored` still includes an ignored `ignored.log`, but inclusion renders `gi:n`. Whale spotting likewise includes both `.hidden` and `ignored.log` while rendering `h:y  gi:n`. `--show-git-info` displays the branch and aggregate change counts in the root header and status markers such as `M` for modified and `N` for new beside entries; its counter-option removes this information. `--git-status` filters to paths with interesting modified/new/conflicted status, including relevant hidden paths when hidden display is enabled.

## Spec 13: Remote control

`--listen NAME` runs the interactive instance as a Unix-domain-socket server at `/tmp/broot-server-NAME.sock`. Names containing letters, digits, underscores, and hyphens are valid. `--listen-auto` chooses a unique name and creates a matching socket. Remove a stale regular/socket file before binding; remove the socket on normal exit.

`--send NAME` is a noninteractive client. A missing server exits 1 and ends its diagnostic with exactly `error on the socket: No such file or directory (os error 2)`. With `--get-root`, print the server's current absolute root as a newline-terminated stdout line. With `--cmd`, enqueue the semicolon-separated commands in order. A positional directory without `--cmd` is equivalent to sending `:focus <directory>`. Paths with spaces, Unicode, deep nesting, and symlink directories must remain usable. The server accepts multiple sequential client connections.

A client may combine a command and `--get-root`; the immediate response may precede asynchronous command application, but a later query must observe the new root. An empty command or empty sequence segments do not crash the client. An invalid remote verb is accepted by the client but causes the server to terminate and clean up its socket.

## Spec 14: Trash view

`:trash` moves the selected file to the platform trash so it disappears from its original directory. Preserve names containing spaces, Unicode, hyphens, and underscores. `:ot` opens a trash panel with `Original parent` and `Deleted file` columns and the exact bottom hint `Hit esc to get back, or a space to start a verb`; it works when empty and supports normal filtering/selection. Opening this panel selects no trash row, even when it contains exactly one row. `:rt` issued immediately in that state leaves the listing open and displays `an item must be selected`. Down selects the first row; the trash-table rendering has no visible selection marker.

A directory root is itself trashable. Because startup `:select` has the timing behavior specified in Spec 10, launching on a directory with `--cmd ":select collision.txt;:trash;:quit"` does not select `collision.txt`: `:trash` moves the whole selected root directory, status is 0, and both the root and its child disappear. The same applies when the child name is `restore me.txt` or `purge-me.txt`; a later invocation whose working directory is that removed root cannot exercise restore or empty-trash behavior.

After a trash row has been selected, `:rt` refuses to overwrite an existing item at the original path and displays `collision: <full-path> already exists`, leaving that existing file unchanged. `:et` purges all trash entries while keeping the empty trash panel and its headers visible.
