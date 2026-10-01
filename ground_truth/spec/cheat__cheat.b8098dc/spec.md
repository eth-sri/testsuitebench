# Clarified specification for `executable`

The required artifact is a single runnable command-line program named exactly `executable`. It implements the cheatsheet manager described below. All paths and examples are POSIX paths unless stated otherwise. Output is UTF-8 except that an uncolorized cheatsheet body is fundamentally copied as bytes and may therefore contain arbitrary bytes. Every shown output line ends with `\n` except search output, whose framing and lack of a final newline are specified in Spec 19. Unless a requirement explicitly names stdout, diagnostics go to stderr and successful data goes to stdout. The process must not emit debugging or logging text.

## Spec 1

The command-line shape is `executable [cheatsheet] [flags]`, with at most one positional cheatsheet argument. It accepts both separated flag values (`--tag value`) and the documented short forms. The flags are:

```
-a, --all
-b, --brief
-c, --colorize
    --completion shell
    --conf
-d, --directories
-e, --edit cheatsheet
-h, --help
    --init
-l, --list
-p, --path name
-r, --regex
    --rm cheatsheet
-s, --search phrase
-t, --tag tag
-T, --tags
-u, --update
-v, --version
```

An unknown long flag fails with status 1 and writes exactly `unknown flag: FLAG\n` to stderr. A value-taking long flag with no value fails with status 1 and writes `flag needs an argument: FLAG\n`. Missing values for the four value-taking short flags instead fail with status 1 and write exactly `flag needs an argument: 't' in -t\n`, `flag needs an argument: 'p' in -p\n`, `flag needs an argument: 's' in -s\n`, or `flag needs an argument: 'e' in -e\n`, respectively. These parsing failures have empty stdout. Multiple occurrences of a scalar flag use the last value. More than one positional argument fails with status 1 and writes `accepts at most 1 arg(s), received N\n`. Status 0 means success, status 1 means a configuration, parsing, validation, editing, repository, or other application error, and status 2 means that a requested sheet/list selection was not found. Search is an exception: a valid search with no content matches is successful status 0.

## Spec 2

`--version`/`-v` succeeds without loading configuration and prints exactly:

```
5.1.0
```

`--help`/`-h`, or an invocation with no command/positional argument after a valid configuration has been loaded, succeeds and prints exactly the following. `-c` alone is not a configuration-free help invocation: it first performs normal configuration loading under Spec 3. Thus, with no config and EOF on stdin, `-c` fails status 1 with `failed to create config: failed to prompt: EOF\n` on stderr; with a valid config it reaches the no-command help behavior.

```text
cheat allows you to create and view interactive cheatsheets on the
command-line. It was designed to help remind *nix system administrators of
options for commands that they use frequently, but not frequently enough to
remember.

Usage:
  cheat [cheatsheet] [flags]

Examples:
  To initialize a config file:
    mkdir -p ~/.config/cheat && cheat --init > ~/.config/cheat/conf.yml

  To view the tar cheatsheet:
    cheat tar

  To edit (or create) the foo cheatsheet:
    cheat -e foo

  To edit (or create) the foo/bar cheatsheet on the "work" cheatpath:
    cheat -p work -e foo/bar

  To view all cheatsheet directories:
    cheat -d

  To list all available cheatsheets:
    cheat -l

  To briefly list all cheatsheets whose titles match "apt":
    cheat -b apt

  To list all tags in use:
    cheat -T

  To list available cheatsheets that are tagged as "personal":
    cheat -l -t personal

  To search for "ssh" among all cheatsheets, and colorize matches:
    cheat -c -s ssh

  To search (by regex) for cheatsheets that contain an IP address:
    cheat -c -r -s '(?:[0-9]{1,3}\.){3}[0-9]{1,3}'

  To remove (delete) the foo/bar cheatsheet:
    cheat --rm foo/bar

  To update all git-backed cheatpaths:
    cheat --update

  To view the configuration file path:
    cheat --conf

  To generate shell completions (bash, zsh, fish, powershell):
    cheat --completion bash

Flags:
  -a, --all                Search among all cheatpaths
  -b, --brief              List cheatsheets without file paths
  -c, --colorize           Colorize output
      --completion shell   Generate shell completion script (shell: bash, zsh, fish, powershell)
      --conf               Display the config file path
  -d, --directories        List cheatsheet directories
  -e, --edit cheatsheet    Edit cheatsheet
  -h, --help               help for cheat
      --init               Write a default config file to stdout
  -l, --list               List cheatsheets
  -p, --path name          Return only sheets found on cheatpath name
  -r, --regex              Treat search <phrase> as a regex
      --rm cheatsheet      Remove (delete) cheatsheet
  -s, --search phrase      Search cheatsheets for phrase
  -t, --tag tag            Return only sheets matching tag
  -T, --tags               List all tags in use
  -u, --update             Update git-backed cheatpaths
  -v, --version            Print the version number
```

## Spec 3

Commands other than `--help`, `--version`, `--init`, and completion generation require configuration. On Unix, locate the first existing config in this order:

1. `CHEAT_CONFIG_PATH` when set; expand a leading `~` using `HOME`.
2. `$XDG_CONFIG_HOME/cheat/conf.yml` when `XDG_CONFIG_HOME` is set.
3. `$HOME/.config/cheat/conf.yml`.
4. `$HOME/.cheat/conf.yml`.
5. `/etc/cheat/conf.yml`.

An explicitly selected missing file is treated as no config. `--conf` loads and validates the config, then prints its selected path as one line and status 0. It honors `CHEAT_CONFIG_PATH` over all defaults and `XDG_CONFIG_HOME` over the HOME defaults.

If no config exists, print `A config file was not found. Would you like to create one now? [Y/n]: ` and read a reply. A negative reply (`n`/`N`) exits successfully and creates nothing. EOF causes status 1; the combined prompt and error must include `failed to create config: failed to prompt: EOF` (an equivalent outer wrapper `failed to run installer` is also permitted). Other accepted replies enter the installer described later.

## Spec 4

The configuration is one YAML document with these fields:

- `editor`: string. A usable editor is mandatory after environment fallback.
- `colorize`: YAML boolean, defaulting false when omitted. The field is parsed but does not itself activate colorization; see Spec 12.
- `style`: string; the default when the field is omitted is `bw`. An unknown style must not make configuration loading fail; its observed rendering fallback is specified in Spec 12.
- `formatter`: string, defaulting to `terminal` when omitted; only `terminal`, `terminal256`, and `terminal16m` are valid.
- `pager`: one command string, possibly empty and possibly containing arguments. A YAML null value, including the bare empty mapping value in `pager: `, is accepted and decoded as the empty pager.
- `cheatpaths`: a nonempty sequence. Each entry contains a nonempty unique string `name`, a path string `path`, a YAML boolean `readonly`, and optional `tags`, which must be a sequence of strings.

YAML types are strict: quoted strings such as `colorize: "true"` or `readonly: "true"` are not booleans and cause a YAML unmarshal error containing `failed to load config: could not unmarshal yaml: yaml: unmarshal errors:` and `cannot unmarshal !!str ... into bool`. Malformed YAML uses the Go YAML parser's diagnostic. In particular, a document whose first three lines are `---`, `editor: /bin/true`, and `colorize: [unclosed` fails status 1 with empty stdout and exactly `failed to load config: could not unmarshal yaml: yaml: line 2: did not find expected ',' or ']'\n` on stderr. A frontmatter/config `tags` scalar must fail with unmarshal detail including `cannot unmarshal` and `into []string`.

After parsing and after the nonexistent-directory filtering in Spec 5, reject no/empty remaining `cheatpaths` with exactly `failed to load config: config error: no cheatpaths specified`; reject an omitted or empty name among the remaining entries with exactly `failed to load config: config error: cheatpath name cannot be empty`; reject repeated names among them with `failed to load config: config error: cheatpath name is not unique: NAME`; reject repeated path strings among them with `failed to load config: config error: cheatpath path is not unique: PATH`; and reject invalid formatter values with `failed to load config: config error: formatter is invalid: VALUE`. These errors use status 1.

Editor precedence is `VISUAL`, then `EDITOR`, then the trimmed configured `editor`: a nonempty environment value overrides even a nonempty configured value. If all three are empty, try an available conventional editor; if none can be selected, fail with exactly `failed to load config: no editor set`. Tildes in cheatpath paths are expanded against `HOME`.

## Spec 5

While loading cheatpaths, resolve symlinked cheatpath directories to their real directory. For every nonexistent configured directory, write exactly `WARNING: cheatpath 'PATH' does not exist, skipping\n` to stderr and continue. If at least one valid path remains, normal commands proceed. If none remains, configuration validation fails with `failed to load config: config error: no cheatpaths specified` and status 1.

Existence filtering precedes all of the semantic checks in Spec 4. A skipped entry therefore cannot trigger the empty-name, duplicate-name, duplicate-path, or invalid-formatter diagnostic. If all entries are skipped, emit every warning in configuration order and then the no-cheatpaths error. For example, two nonexistent entries named `a` at `PATH` and `PATH2` produce the two warnings for `PATH` and `PATH2`, followed by `failed to load config: config error: no cheatpaths specified`; the duplicate name is not reported.

`--path NAME`/`-p NAME` restricts all subsequent sheet or update work to the exactly named configured path. An unknown name fails status 1 with exactly `invalid option --path: cheatpath does not exist: NAME`.

In addition to configured paths, walk from the process working directory upward toward the filesystem root and find the nearest ancestor entry named `.cheat` that is a directory. Add that one directory, and no more distant `.cheat` directory, as the final/highest-precedence cheatpath named `cwd`. It appears in `--directories`, and its sheets can be viewed from descendants.

## Spec 6

`--init` succeeds without an existing config and writes a substantial, valid YAML document beginning with `---`. Its parsed active configuration has exactly two cheatpaths named `personal` then `work`; both have `readonly: false`, and each has exactly one path-level tag equal to its name. Their paths point respectively to `cheatsheets/personal` and `cheatsheets/work` beneath the normal config directory. The top level includes a nonempty editor, `colorize: false`, `style: monokai`, `formatter: terminal256`, and a `pager` key. When a pager is selected its value is a string. When no pager is available, the required literal `pager: ` line has a YAML null value rather than an empty string value.

Choose the editor from `VISUAL`, then `EDITOR`, then an available conventional editor. Choose the pager from nonempty `PAGER`, otherwise an available pager command such as `less` or `more`; if no pager executable is on `PATH`, emit the literal line `pager: ` with an empty value. With `PAGER=/usr/bin/custom-pager`, emit `pager: /usr/bin/custom-pager`.

The YAML text also contains an inactive community template using these exact line shapes (with two leading spaces before each `#`):

```
  #- name: community
  #  path: ABSOLUTE_CONFIG_DIR/cheatsheets/community
  #  tags: [ community ]
  #  readonly: true
```

It must contain, on one comment line, a `git clone` instruction whose URL contains `github.com/cheat/cheatsheets`. No template placeholder such as `PAGER_PATH`, `EDITOR_PATH`, `COMMUNITY_PATH`, `PERSONAL_PATH`, or `WORK_PATH` may remain.

## Spec 7

The first-run installer follows the missing-config prompt. After acceptance it asks `Would you like to download the community cheatsheets? [Y/n]: `. The installer uses the selected missing configuration path as its destination. In particular, when `CHEAT_CONFIG_PATH` names a missing file, it creates the valid configuration at that exact path and creates `cheatsheets/personal` and `cheatsheets/work` beneath that file's parent directory; it does not instead create `$HOME/.config/cheat/conf.yml`. When `CHEAT_CONFIG_PATH` is unset but `XDG_CONFIG_HOME` is set, the same rule places these at `$XDG_CONFIG_HOME/cheat/conf.yml` and beneath `$XDG_CONFIG_HOME/cheat`, respectively. When neither override is set, the destination is `$HOME/.config/cheat/conf.yml`, with the two sheet directories beneath `$HOME/.config/cheat`. It prints a line beginning `Created config file: ` followed by the absolute file path it created. After successful installation, terminate with status 0 instead of resuming the originally requested list/view operation; this keeps a declined-community install successful even though the new personal/work directories are empty.

If community download is declined, do not create the community directory and retain the commented community block described in Spec 6. The newly written config must load on the next invocation and `--directories` must then show only personal and work.

If accepted, print text containing `Cloning community cheatsheets`, shallow-clone the public Git repository `https://github.com/cheat/cheatsheets` into the sibling directory `cheatsheets/community`, and activate (uncomment) the four community YAML lines. The clone must be a usable `.git` repository with `HEAD`, `config`, `refs`, and `objects`, and actual nonempty community sheets including at least `tar`, `git`, `ssh`, `curl`, and `grep`. The community entry is tagged `[ community ]` and readonly true. Clone failure is status 1 and stderr includes the wrapper chain `failed to run installer`, `failed to clone cheatsheets`, and the underlying reason; attempting to clone over an existing repository must include `repository already exists`. A normal shallow clone must complete rather than hanging indefinitely.

## Spec 8

A valid cheatsheet source is a regular file beneath a cheatpath, recursively at arbitrary practical depth. Its title is its slash-separated relative path. Discover UTF-8 names and symlinked files. A symlinked file is listed under the symlink's own title/path, while a symlinked cheatpath uses the resolved real base path. Do not traverse a symlink to a directory. An extensionless, nonhidden directory symlink is instead treated as a sheet candidate at the link's own relative title; attempting to list sheets then fails status 1 with empty stdout and the error chain `failed to list cheatsheets: failed to load cheatsheets: failed to load sheet: TITLE, path: LINK_PATH, err: failed to read file: LINK_PATH, read LINK_PATH: is a directory`. If following a circular symlink fails, the command fails status 1 with an error chain containing `failed to list cheatsheets` and `too many levels of symbolic links`.

Do not harvest a file whose own basename starts with `.`, and do not harvest files whose basename has an extension (for example `readme.txt`). Hidden directories are still traversed: a nonhidden extensionless file `.secret/value` is harvested under that title even though a directory component starts with `.`. Nested directories are represented in titles (`docker/compose`, `lang/python/libs/pandas`). There must be no small line/file-size limit: listing and byte-exact viewing work for at least a 1.3 MB sheet, 100,000 repeated tokens, and lines of 500 bytes.

## Spec 9

Select one delimiter style for the entire file before recognizing optional frontmatter. If the file contains `\r\n` anywhere, the delimiter is `---\r\n`; otherwise it is `---\n`. Parse frontmatter only when the file begins with the selected delimiter, and end the header at the next occurrence of that same delimiter. Parse the bytes between as YAML with optional `syntax` and `tags: [STRING, ...]`. A numeric syntax scalar is accepted: a sheet containing `---\nsyntax: 42\n---\nbody` loads successfully, appears in `--list`, and views as `body`. The body is every byte after the closing delimiter, unchanged—including leading/trailing whitespace, tabs, blank lines, long lines, Unicode, or no bytes. Do not display recognized frontmatter when viewing/searching.

This whole-file line-break selection is significant for mixed endings. A file beginning `---\n` but containing a later `\r\n` does not begin with the selected `---\r\n` delimiter, so it has no recognized frontmatter: its apparent header receives no metadata meaning, is searched as text, and is displayed as part of the ordinary body. For example, the observed file `---\nsyntax: bash\ntags:\n- one\n---\nBODY\r\n` is viewed byte-for-byte including both `---` lines. A file beginning with `--` is likewise ordinary body text, not frontmatter.

If an opening delimiter has no closing delimiter, fail status 1 with a chain containing `failed to list cheatsheets`, `failed to load cheatsheets`, `failed to load sheet: TITLE`, `failed to parse front-matter`, and `failed to delimit frontmatter`. Invalid header YAML has the same outer chain and then `failed to unmarshal frontmatter: YAML_ERROR`. For header content `tags: [ invalid yaml without closing bracket`, the parser suffix is exactly `failed to unmarshal frontmatter: yaml: line 1: did not find expected ',' or ']'`. A header with no body is valid and views as empty. A header without tags is valid.

## Spec 10

Cheatpaths are ordered as configured; a later path has higher precedence. In ordinary view/edit/remove behavior, sheets of the same title are consolidated so the last eligible one wins. Listing is the exception: `--list` and `--brief` retain and print every eligible same-title instance rather than consolidating them. A name and/or tag/path filter is applied to eligible sheet instances before selection where applicable. `--all` disables consolidation for viewing and displays every eligible instance in original cheatpath order.

Without `--all`, viewing a title prints exactly the chosen body's bytes to stdout and status 0. Empty and whitespace-only bodies are valid. If no eligible sheet exists, print `No cheatsheet found for 'TITLE'.\n` to stdout and exit 2. The same nested title supplied by the user appears verbatim in that message.

## Spec 11

With `--all`/`-a`, viewing a title prints one block per eligible instance. For block framing, trim Unicode whitespace from both ends of each body before indenting it; whitespace that remains between non-whitespace content is unchanged. Thus the body `\n  padded  \n` is framed as the single content line `padded`, without its boundary spaces. Each block is:

```
TITLE (CHEATPATH_NAME)
\tBODY_LINE_1
\tBODY_LINE_2
...
```

Prefix every remaining body line, including blank lines inside the body, with one tab. An empty body is rendered as one empty indented body line: a frontmatter-bearing sheet named `empty` on path `test` with no body renders exactly `empty (test)\n\t\n`. Separate instance blocks by exactly one blank line and terminate the final rendered line with a newline. For example, two one-line bodies are rendered as `x (first)\n\tone\n\nx (second)\n\ttwo\n`. Tag and path filters still restrict the instances shown. A single `--all` result still has the labeled/indented form.

## Spec 12

Colorization is enabled only when `-c`/`--colorize` is present. Config `colorize: true` alone is ignored: viewing a sheet whose body is `# C\ngit commit -m "Initial commit"\n` without either flag emits those exact uncolored body bytes. In the notation below, `ESC` is the single byte `0x1b`, not the three letters E-S-C. Use the sheet's `syntax`; absent syntax is treated as shell/bash for the tested shell-like sheets.

When `style` and `formatter` are omitted, their Spec 4 defaults are `bw` and `terminal`. For the observed bash and Python fixtures, comments render as `ESC[3mCOMMENTESC[0m`, ordinary command/code text is uncolored, and a quoted bash string renders as `ESC[3m"STRING"ESC[0m`. Preserve all body whitespace, including a leading blank line. Thus a default-config Python body `\n# To create a virtual environment:\npython -m venv myenv\n` renders exactly `\nESC[3m# To create a virtual environment:ESC[0m\npython -m venv myenv\n`. A default-config colorized search of the body `Commit changes:\ngit commit -m "Initial commit"` produces exactly `git ESC[2m(test)ESC[0m\n\tCommit changes:\n\tgit commit -m ESC[3m"Initial commit"ESC[0m`, without a final newline. A default-config unknown syntax succeeds and emits the body uncolored; for `\n# Test with invalid syntax\necho "test"\n`, the output is those exact bytes. With every formatter, labeled view/search output dims the parentheses and cheatpath name as `TITLE ESC[2m(PATH)ESC[0m`; tabs and layout are not colorized.

When configuration explicitly selects `style: monokai` and `formatter: terminal256`, Chroma's terminal-256 sequences are normative:

- A full shell comment body `# Comment` with no terminating source newline renders as `ESC[38;5;242m# CommentESC[0m`.
- The shell line `git commit -m "message"` renders as `ESC[38;5;231mgit commit -m ESC[0mESC[38;5;186m"message"ESC[0m` when it has no terminating source newline.

For the newline-terminated bash body `# Comment\necho "message"\n`, both `-c --all x` and `--colorize --all x` produce exactly `x ESC[2m(test)ESC[0m\n\tESC[38;5;242m# CommentESC[0mESC[38;5;231mESC[0m\n\tESC[38;5;231mechoESC[0mESC[38;5;231m ESC[0mESC[38;5;186m"message"ESC[0mESC[38;5;231mESC[0m\n`.

Thus, under this explicit `monokai`/`terminal256` configuration, a colorized search match whose body is exactly `# Comment\ngit commit -m "message"` is `git ESC[2m(test)ESC[0m\n\tESC[38;5;242m# CommentESC[0mESC[38;5;231mESC[0m\n\tESC[38;5;231mgit commit -m ESC[0mESC[38;5;186m"message"ESC[0m`, with no final newline as required by Spec 19. Unknown highlighter names do not make the command fail; their fallback depends on the selected style/formatter as described above. With body `# C\necho "x"\n`, `-c`, absent sheet syntax, config style `no-such-style`, and `formatter: terminal256`, output is exactly `ESC[38;5;6m# CESC[0mESC[38;5;254mESC[0m\nESC[1mESC[38;5;231mechoESC[0mESC[38;5;254m ESC[0mESC[1mESC[38;5;51m"x"ESC[0mESC[38;5;254mESC[0m\n`. With explicit `style: monokai`, `formatter: terminal256`, and sheet syntax `no-such-language`, the same invocation and body output exactly `ESC[38;5;231m# CESC[0m\nESC[38;5;231mecho "x"ESC[0m\n`. Both succeed with status 0. Colorization never exposes recognized frontmatter.

## Spec 13

`--list`/`-l` enumerates every eligible sheet instance without consolidating duplicate titles, sorted ascending by title using byte/Unicode string order. Thus if two cheatpaths each contain a sheet titled `same`, the table contains two `same` rows even though ordinary view selects only the higher-precedence instance. An optional positional argument is a case-insensitive regular expression matched anywhere against titles. Compile it as the literal concatenation `(?i)` plus the supplied pattern. Thus `DOCKER` matches `docker`, `kube` matches `kubectl`, `^g` uses its anchor, and slashes remain part of nested titles. An invalid title regex fails status 1 with the shape `failed to compile regexp: (?i)PATTERN, ERROR\n`. For `[invalid`, the complete diagnostic is:

```text
failed to compile regexp: (?i)[invalid, error parsing regexp: missing closing ]: `[invalid`
```

No list matches means status 2 and empty stdout.

The full table has fields `title:`, `file:`, and `tags:` in that order. Every sheet row contains title, absolute harvested file path, and its comma-joined displayed tags. Format as an elastic tabular table: each nonfinal column begins at one space after the widest value (including its header) in that column. Do not add brackets or spaces around the comma-separated tag list. A sheet without tags is included with an empty final field. The header and each row end with newline.

For example, a directory containing `curl` tagged `networking,http` and `tar` tagged `compression` lists briefly as exactly:

```
title: tags:
curl   http,networking
tar    compression
```

## Spec 14

`--brief`/`-b` performs the same duplicate-preserving enumeration, sorting, name filtering, tag filtering, statuses, and elastic alignment as `--list`, but includes only `title:` and `tags:` fields and must never print file paths or a `file:` header. It acts as a listing command even without `--list`. Its optional positional title regex and all filters combine by intersection.

`--directories`/`-d` prints valid cheatpaths in configuration order (followed by any discovered `cwd` path), one per line. Align paths using a common column: print `NAME:` then enough spaces that all path values start one column after the longest `NAME:`. Example:

```
community: /a/community
personal:  /b/personal
```

The `-l`, `-b`, `-d`, and `-t` short forms are identical to their long forms.

## Spec 15

Each sheet's effective displayed/filter tags are the concatenation of its cheatpath-level tag list followed by its frontmatter tag list, sorted lexicographically as strings. Preserve duplicates in this per-sheet list, including a duplicate contributed by both levels. Preserve case, commas inside a YAML tag string, leading/trailing spaces, Unicode, and long values. YAML's normal folding of physical newlines in a double-quoted scalar applies before display. Join per-sheet tags with literal commas for tables.

`--tag VALUE`/`-t VALUE` splits the option value on literal commas and requires every requested element to be an exact, case-sensitive member of the effective tag list (AND semantics). Do not case-fold tag names. Empty or whitespace-only requested tag input matches no sheet. Tag filtering combines with name, path, view, search, edit, remove, list, brief, and `--all` selection.

## Spec 16

`--tags`/`-T` collects all effective tags from all eligible sheet instances, deduplicates identical strings, sorts them lexicographically with uppercase distinct from lowercase, and prints one raw tag per line. It returns status 0 and empty stdout when there are no tags or no sheets. It includes cheatpath-level tags and frontmatter tags. For example, tags `Linux`, `UNIX`, `linux`, and `unix` print in exactly that order. Whitespace in a tag is printed rather than trimmed; a tag containing commas remains one printed line containing those commas.

## Spec 17

`--search PHRASE`/`-s PHRASE` searches every eligible sheet instance, optionally limited by one positional title. For search, that positional value is an exact, case-sensitive title, not the regular-expression title filter used by list/brief: `apple` selects `apple`, while `app`, `APPLE`, `^app`, and `.*` do not select it. Path and tag filters are applied by intersection with this exact-title selection. It does not consolidate duplicate titles: without or with `--all`, same-title matches from multiple cheatpaths are all emitted in cheatpath configuration order. Split each body into paragraphs at each double newline (`\n\n`). Match each paragraph as one unit, so a match may span the single newlines inside that paragraph. Return only matching paragraphs in their original order. Join matching paragraphs with `\n\n` before the trimming and indentation in Spec 19. An empty phrase matches every paragraph and therefore reconstructs every sheet body subject to that rendering. Recognized frontmatter is never searched.

Without `--regex`, compile the literal concatenation `(?i)` plus `PHRASE`; do not quote regex metacharacters. The resulting search is case-insensitive but still interprets metacharacters. For example, `[user]` is a character class and `.*` is a repetition, while a user must supply `\[user\]` to match those brackets literally. A multiword phrase remains one pattern, not separate terms. Unicode text is supported. A valid search with zero matches produces no stdout/stderr and status 0.

## Spec 18

With `--regex`/`-r`, interpret the phrase using Go RE2-compatible regular expression semantics and default case-sensitive matching. Support grouping, alternation, character/negated classes, `+`, `*`, bounded quantifiers, `\d`, `\w`, `\b`, `^`, `$`, and inline flags such as `(?i)` and `(?s)`. Do not implement backreferences or lookahead: they are invalid as they are in Go regexp.

Regex compilation failure is status 1, empty stdout, and exactly `failed to compile regexp: PATTERN, ERROR\n` on stderr. In particular:

```
failed to compile regexp: (?:[0-9, error parsing regexp: missing closing ]: `[0-9`
failed to compile regexp: (\w+) \1, error parsing regexp: invalid escape sequence: `\1`
failed to compile regexp: ssh(?= user), error parsing regexp: invalid or unsupported Perl syntax: `(?=`
```

## Spec 19

Search processes cheatpaths in configuration order and sorts titles ascending within each cheatpath. Emit a sheet instance only if it has at least one matching paragraph. Its block is:

```
TITLE (CHEATPATH_NAME)
\tMATCHED_PARAGRAPH_LINE_1
\tMATCHED_PARAGRAPH_LINE_2
```

Before indentation, trim Unicode whitespace from both ends of the joined matching text. Then prefix every resulting line with one tab, including empty lines created by paragraph separators. Consequently two matching paragraphs `hit one\ncontinued` and `hit two` render their content as `\thit one\n\tcontinued\n\t\n\thit two`: the separator is a tab-only blank line. Two consecutive blank source lines become two tab-only lines. Separate sheet-instance blocks by one completely empty line. Include the cheatpath label even without `--all`. When colorized, dim the `(CHEATPATH_NAME)` as in Spec 12 and apply syntax coloring to matched content.

After all blocks are assembled, trim whitespace from both ends of the complete output. Therefore every nonempty search result ends at its last content byte (or final ANSI reset) with no terminating `\n`; for example, a one-line match is exactly `git (test)\n\tneedle`. Empty search output is zero bytes. `--all` does not change this search framing or instance selection.

## Spec 20

`--edit TITLE`/`-e TITLE` opens an existing sheet or an editor target for a new sheet. Validate TITLE before any filesystem change. Select the editor command from the environment/config resolution in Spec 4, split the selected command at runs of whitespace into executable plus arguments, append the target absolute filename as the final argument, inherit stdio, wait for completion, and propagate its visible stdout. Quotes have no shell-grouping meaning during this split: a configured suffix `'two words'` becomes the two literal arguments `'two` and `words'`. A nonzero editor result fails status 1 with exactly `failed to edit cheatsheet: exit status N\n` on stderr.

For a new sheet, choose the last writable eligible cheatpath (or the selected `--path`), create all parent directories, and invoke the editor with the target path. Do not precreate the target file: at editor start it does not exist, and if the chosen editor exits successfully without creating it (for example `/bin/true`), the edit still returns status 0 and the target remains absent. If there is no writable eligible path, fail status 1 with exactly `failed to get writeable path: no writeable cheatpaths found`. Unicode, hyphens, underscores, dots away from the first character, and deep nested names are valid target names.

For an existing writable matching sheet, invoke the editor on that file. Among same-title instances, tag filtering is honored before the precedence choice. If a tag filter leaves no matching instance of the requested title, treat it as a new-sheet edit: invoke the editor on the selected writable target without precreating it. Any resulting file is created only if the editor creates it and is not automatically assigned frontmatter tags.

## Spec 21

If the selected existing sheet is on a readonly cheatpath, editing is allowed only by copying its entire file byte-for-byte (including frontmatter) to the last eligible writable cheatpath at the same relative title, creating parent directories, then opening the copy. Do not alter the readonly original. Tag filtering participates in selecting which same-title instance is copied. If no writable destination exists, use the no-writeable-path error from Spec 20.

`--path NAME` fixes the edit destination/source path; if that path is readonly and no eligible writable destination remains, editing fails. When several writable paths exist and no path is specified, the last path is selected.

## Spec 22

For both edit and remove, reject these title forms with status 1 and the exact diagnostic shown:

```
empty                         invalid cheatsheet name: cheatsheet name cannot be empty
contains the substring `..`  invalid cheatsheet name: cheatsheet name cannot contain '..'
absolute path                invalid cheatsheet name: cheatsheet name cannot be an absolute path
starts with `~`               invalid cheatsheet name: cheatsheet name cannot start with '~'
starts with `.`               invalid cheatsheet name: cheatsheet name cannot start with '.' (hidden files are not supported)
```

Append one newline and write these diagnostics to stderr. This validation must prevent any creation/modification outside a configured cheatpath.

`--rm TITLE` applies path/tag filtering and consolidation, then deletes exactly the selected file, never its parent directories or same-title lower-precedence copies. Success is silent status 0. If none is eligible, exit 2 and write `No cheatsheet found for 'TITLE'.\n` to stderr. If selected sheet's cheatpath is readonly, exit 1, write `cheatsheet 'TITLE' is read-only.\n`, and preserve it. Unicode and nested titles are removable.

## Spec 23

`--update`/`-u` visits eligible cheatpaths in configuration order, regardless of their `readonly` field. For each:

- If the directory is not a Git work repository, print `NAME: skipped (not a git repository)\n` to stdout.
- If any tracked modification, staged change, deletion, untracked file, or unresolved/conflict-marker modification makes the worktree dirty, do not pull and print `NAME: skipped (dirty worktree)\n` to stdout.
- For a clean repository with a usable `origin`-style remote, fetch/pull its current branch. Up-to-date and successfully fast-forwarded repositories both print `NAME: ok\n` to stdout. Preserve clean local commits and never push them.
- A repository with no remote writes `NAME: error (remote not found)\n` to stderr. An initialized/cloned empty repository whose remote has no commit writes `NAME: error (remote repository is empty)\n` to stderr. Other repository failures use `NAME: error (REASON)\n` on stderr.

Continue after every success, skip, and error. Preserve result order independently on each stream. Exit 1 if any path produced an error, otherwise 0. Success and skip lines remain on stdout even when another path errors. Support at least five repositories in arbitrary config order and at least twenty total. A real upstream commit must be materialized in the worktree after a successful update.

## Spec 24

`--completion SHELL` succeeds without configuration only for the exact lowercase names `bash`, `zsh`, `fish`, and `powershell`. It writes the shell-specific script given verbatim below and nothing to stderr. Repeated completion flags use the final shell value. Every other value—including empty, whitespace-padded, uppercase/mixed-case, numeric, Unicode, shell metacharacters, and very long strings—fails status 1 with empty stdout and exactly:

```
unsupported shell: VALUE (valid: bash, zsh, fish, powershell)
```

The following four blocks are normative byte-for-byte outputs, including comments, spacing, and the final newline.

### Bash completion

```bash
# bash completion V2 for cheat                                -*- shell-script -*-

__cheat_debug()
{
    if [[ -n ${BASH_COMP_DEBUG_FILE-} ]]; then
        echo "$*" >> "${BASH_COMP_DEBUG_FILE}"
    fi
}

# Macs have bash3 for which the bash-completion package doesn't include
# _init_completion. This is a minimal version of that function.
__cheat_init_completion()
{
    COMPREPLY=()
    _get_comp_words_by_ref "$@" cur prev words cword
}

# This function calls the cheat program to obtain the completion
# results and the directive.  It fills the 'out' and 'directive' vars.
__cheat_get_completion_results() {
    local requestComp lastParam lastChar args

    # Prepare the command to request completions for the program.
    # Calling ${words[0]} instead of directly cheat allows handling aliases
    args=("${words[@]:1}")
    requestComp="${words[0]} __complete ${args[*]}"

    lastParam=${words[$((${#words[@]}-1))]}
    lastChar=${lastParam:$((${#lastParam}-1)):1}
    __cheat_debug "lastParam ${lastParam}, lastChar ${lastChar}"

    if [[ -z ${cur} && ${lastChar} != = ]]; then
        # If the last parameter is complete (there is a space following it)
        # We add an extra empty parameter so we can indicate this to the go method.
        __cheat_debug "Adding extra empty parameter"
        requestComp="${requestComp} ''"
    fi

    # When completing a flag with an = (e.g., cheat -n=<TAB>)
    # bash focuses on the part after the =, so we need to remove
    # the flag part from $cur
    if [[ ${cur} == -*=* ]]; then
        cur="${cur#*=}"
    fi

    __cheat_debug "Calling ${requestComp}"
    # Use eval to handle any environment variables and such
    out=$(eval "${requestComp}" 2>/dev/null)

    # Extract the directive integer at the very end of the output following a colon (:)
    directive=${out##*:}
    # Remove the directive
    out=${out%:*}
    if [[ ${directive} == "${out}" ]]; then
        # There is not directive specified
        directive=0
    fi
    __cheat_debug "The completion directive is: ${directive}"
    __cheat_debug "The completions are: ${out}"
}

__cheat_process_completion_results() {
    local shellCompDirectiveError=1
    local shellCompDirectiveNoSpace=2
    local shellCompDirectiveNoFileComp=4
    local shellCompDirectiveFilterFileExt=8
    local shellCompDirectiveFilterDirs=16
    local shellCompDirectiveKeepOrder=32

    if (((directive & shellCompDirectiveError) != 0)); then
        # Error code.  No completion.
        __cheat_debug "Received error from custom completion go code"
        return
    else
        if (((directive & shellCompDirectiveNoSpace) != 0)); then
            if [[ $(type -t compopt) == builtin ]]; then
                __cheat_debug "Activating no space"
                compopt -o nospace
            else
                __cheat_debug "No space directive not supported in this version of bash"
            fi
        fi
        if (((directive & shellCompDirectiveKeepOrder) != 0)); then
            if [[ $(type -t compopt) == builtin ]]; then
                # no sort isn't supported for bash less than < 4.4
                if [[ ${BASH_VERSINFO[0]} -lt 4 || ( ${BASH_VERSINFO[0]} -eq 4 && ${BASH_VERSINFO[1]} -lt 4 ) ]]; then
                    __cheat_debug "No sort directive not supported in this version of bash"
                else
                    __cheat_debug "Activating keep order"
                    compopt -o nosort
                fi
            else
                __cheat_debug "No sort directive not supported in this version of bash"
            fi
        fi
        if (((directive & shellCompDirectiveNoFileComp) != 0)); then
            if [[ $(type -t compopt) == builtin ]]; then
                __cheat_debug "Activating no file completion"
                compopt +o default
            else
                __cheat_debug "No file completion directive not supported in this version of bash"
            fi
        fi
    fi

    # Separate activeHelp from normal completions
    local completions=()
    local activeHelp=()
    __cheat_extract_activeHelp

    if (((directive & shellCompDirectiveFilterFileExt) != 0)); then
        # File extension filtering
        local fullFilter="" filter filteringCmd

        # Do not use quotes around the $completions variable or else newline
        # characters will be kept.
        for filter in ${completions[*]}; do
            fullFilter+="$filter|"
        done

        filteringCmd="_filedir $fullFilter"
        __cheat_debug "File filtering command: $filteringCmd"
        $filteringCmd
    elif (((directive & shellCompDirectiveFilterDirs) != 0)); then
        # File completion for directories only

        local subdir
        subdir=${completions[0]}
        if [[ -n $subdir ]]; then
            __cheat_debug "Listing directories in $subdir"
            pushd "$subdir" >/dev/null 2>&1 && _filedir -d && popd >/dev/null 2>&1 || return
        else
            __cheat_debug "Listing directories in ."
            _filedir -d
        fi
    else
        __cheat_handle_completion_types
    fi

    __cheat_handle_special_char "$cur" :
    __cheat_handle_special_char "$cur" =

    # Print the activeHelp statements before we finish
    __cheat_handle_activeHelp
}

__cheat_handle_activeHelp() {
    # Print the activeHelp statements
    if ((${#activeHelp[*]} != 0)); then
        if [ -z $COMP_TYPE ]; then
            # Bash v3 does not set the COMP_TYPE variable.
            printf "\n";
            printf "%s\n" "${activeHelp[@]}"
            printf "\n"
            __cheat_reprint_commandLine
            return
        fi

        # Only print ActiveHelp on the second TAB press
        if [ $COMP_TYPE -eq 63 ]; then
            printf "\n"
            printf "%s\n" "${activeHelp[@]}"

            if ((${#COMPREPLY[*]} == 0)); then
                # When there are no completion choices from the program, file completion
                # may kick in if the program has not disabled it; in such a case, we want
                # to know if any files will match what the user typed, so that we know if
                # there will be completions presented, so that we know how to handle ActiveHelp.
                # To find out, we actually trigger the file completion ourselves;
                # the call to _filedir will fill COMPREPLY if files match.
                if (((directive & shellCompDirectiveNoFileComp) == 0)); then
                    __cheat_debug "Listing files"
                    _filedir
                fi
            fi

            if ((${#COMPREPLY[*]} != 0)); then
                # If there are completion choices to be shown, print a delimiter.
                # Re-printing the command-line will automatically be done
                # by the shell when it prints the completion choices.
                printf -- "--"
            else
                # When there are no completion choices at all, we need
                # to re-print the command-line since the shell will
                # not be doing it itself.
                __cheat_reprint_commandLine
            fi
        elif [ $COMP_TYPE -eq 37 ] || [ $COMP_TYPE -eq 42 ]; then
            # For completion type: menu-complete/menu-complete-backward and insert-completions
            # the completions are immediately inserted into the command-line, so we first
            # print the activeHelp message and reprint the command-line since the shell won't.
            printf "\n"
            printf "%s\n" "${activeHelp[@]}"

            __cheat_reprint_commandLine
        fi
    fi
}

__cheat_reprint_commandLine() {
    # The prompt format is only available from bash 4.4.
    # We test if it is available before using it.
    if (x=${PS1@P}) 2> /dev/null; then
        printf "%s" "${PS1@P}${COMP_LINE[@]}"
    else
        # Can't print the prompt.  Just print the
        # text the user had typed, it is workable enough.
        printf "%s" "${COMP_LINE[@]}"
    fi
}

# Separate activeHelp lines from real completions.
# Fills the $activeHelp and $completions arrays.
__cheat_extract_activeHelp() {
    local activeHelpMarker="_activeHelp_ "
    local endIndex=${#activeHelpMarker}

    while IFS='' read -r comp; do
        [[ -z $comp ]] && continue

        if [[ ${comp:0:endIndex} == $activeHelpMarker ]]; then
            comp=${comp:endIndex}
            __cheat_debug "ActiveHelp found: $comp"
            if [[ -n $comp ]]; then
                activeHelp+=("$comp")
            fi
        else
            # Not an activeHelp line but a normal completion
            completions+=("$comp")
        fi
    done <<<"${out}"
}

__cheat_handle_completion_types() {
    __cheat_debug "__cheat_handle_completion_types: COMP_TYPE is $COMP_TYPE"

    case $COMP_TYPE in
    37|42)
        # Type: menu-complete/menu-complete-backward and insert-completions
        # If the user requested inserting one completion at a time, or all
        # completions at once on the command-line we must remove the descriptions.
        # https://github.com/spf13/cobra/issues/1508

        # If there are no completions, we don't need to do anything
        (( ${#completions[@]} == 0 )) && return 0

        local tab=$'\t'

        # Strip any description and escape the completion to handled special characters
        IFS=$'\n' read -ra completions -d '' < <(printf "%q\n" "${completions[@]%%$tab*}")

        # Only consider the completions that match
        IFS=$'\n' read -ra COMPREPLY -d '' < <(IFS=$'\n'; compgen -W "${completions[*]}" -- "${cur}")

        # compgen looses the escaping so we need to escape all completions again since they will
        # all be inserted on the command-line.
        IFS=$'\n' read -ra COMPREPLY -d '' < <(printf "%q\n" "${COMPREPLY[@]}")
        ;;

    *)
        # Type: complete (normal completion)
        __cheat_handle_standard_completion_case
        ;;
    esac
}

__cheat_handle_standard_completion_case() {
    local tab=$'\t'

    # If there are no completions, we don't need to do anything
    (( ${#completions[@]} == 0 )) && return 0

    # Short circuit to optimize if we don't have descriptions
    if [[ "${completions[*]}" != *$tab* ]]; then
        # First, escape the completions to handle special characters
        IFS=$'\n' read -ra completions -d '' < <(printf "%q\n" "${completions[@]}")
        # Only consider the completions that match what the user typed
        IFS=$'\n' read -ra COMPREPLY -d '' < <(IFS=$'\n'; compgen -W "${completions[*]}" -- "${cur}")

        # compgen looses the escaping so, if there is only a single completion, we need to
        # escape it again because it will be inserted on the command-line.  If there are multiple
        # completions, we don't want to escape them because they will be printed in a list
        # and we don't want to show escape characters in that list.
        if (( ${#COMPREPLY[@]} == 1 )); then
            COMPREPLY[0]=$(printf "%q" "${COMPREPLY[0]}")
        fi
        return 0
    fi

    local longest=0
    local compline
    # Look for the longest completion so that we can format things nicely
    while IFS='' read -r compline; do
        [[ -z $compline ]] && continue

        # Before checking if the completion matches what the user typed,
        # we need to strip any description and escape the completion to handle special
        # characters because those escape characters are part of what the user typed.
        # Don't call "printf" in a sub-shell because it will be much slower
        # since we are in a loop.
        printf -v comp "%q" "${compline%%$tab*}" &>/dev/null || comp=$(printf "%q" "${compline%%$tab*}")

        # Only consider the completions that match
        [[ $comp == "$cur"* ]] || continue

        # The completions matches.  Add it to the list of full completions including
        # its description.  We don't escape the completion because it may get printed
        # in a list if there are more than one and we don't want show escape characters
        # in that list.
        COMPREPLY+=("$compline")

        # Strip any description before checking the length, and again, don't escape
        # the completion because this length is only used when printing the completions
        # in a list and we don't want show escape characters in that list.
        comp=${compline%%$tab*}
        if ((${#comp}>longest)); then
            longest=${#comp}
        fi
    done < <(printf "%s\n" "${completions[@]}")

    # If there is a single completion left, remove the description text and escape any special characters
    if ((${#COMPREPLY[*]} == 1)); then
        __cheat_debug "COMPREPLY[0]: ${COMPREPLY[0]}"
        COMPREPLY[0]=$(printf "%q" "${COMPREPLY[0]%%$tab*}")
        __cheat_debug "Removed description from single completion, which is now: ${COMPREPLY[0]}"
    else
        # Format the descriptions
        __cheat_format_comp_descriptions $longest
    fi
}

__cheat_handle_special_char()
{
    local comp="$1"
    local char=$2
    if [[ "$comp" == *${char}* && "$COMP_WORDBREAKS" == *${char}* ]]; then
        local word=${comp%"${comp##*${char}}"}
        local idx=${#COMPREPLY[*]}
        while ((--idx >= 0)); do
            COMPREPLY[idx]=${COMPREPLY[idx]#"$word"}
        done
    fi
}

__cheat_format_comp_descriptions()
{
    local tab=$'\t'
    local comp desc maxdesclength
    local longest=$1

    local i ci
    for ci in ${!COMPREPLY[*]}; do
        comp=${COMPREPLY[ci]}
        # Properly format the description string which follows a tab character if there is one
        if [[ "$comp" == *$tab* ]]; then
            __cheat_debug "Original comp: $comp"
            desc=${comp#*$tab}
            comp=${comp%%$tab*}

            # $COLUMNS stores the current shell width.
            # Remove an extra 4 because we add 2 spaces and 2 parentheses.
            maxdesclength=$(( COLUMNS - longest - 4 ))

            # Make sure we can fit a description of at least 8 characters
            # if we are to align the descriptions.
            if ((maxdesclength > 8)); then
                # Add the proper number of spaces to align the descriptions
                for ((i = ${#comp} ; i < longest ; i++)); do
                    comp+=" "
                done
            else
                # Don't pad the descriptions so we can fit more text after the completion
                maxdesclength=$(( COLUMNS - ${#comp} - 4 ))
            fi

            # If there is enough space for any description text,
            # truncate the descriptions that are too long for the shell width
            if ((maxdesclength > 0)); then
                if ((${#desc} > maxdesclength)); then
                    desc=${desc:0:$(( maxdesclength - 1 ))}
                    desc+="…"
                fi
                comp+="  ($desc)"
            fi
            COMPREPLY[ci]=$comp
            __cheat_debug "Final comp: $comp"
        fi
    done
}

__start_cheat()
{
    local cur prev words cword split

    COMPREPLY=()

    # Call _init_completion from the bash-completion package
    # to prepare the arguments properly
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion -n =: || return
    else
        __cheat_init_completion -n =: || return
    fi

    __cheat_debug
    __cheat_debug "========= starting completion logic =========="
    __cheat_debug "cur is ${cur}, words[*] is ${words[*]}, #words[@] is ${#words[@]}, cword is $cword"

    # The user could have moved the cursor backwards on the command-line.
    # We need to trigger completion from the $cword location, so we need
    # to truncate the command-line ($words) up to the $cword location.
    words=("${words[@]:0:$cword+1}")
    __cheat_debug "Truncated words[*]: ${words[*]},"

    local out directive
    __cheat_get_completion_results
    __cheat_process_completion_results
}

if [[ $(type -t compopt) = "builtin" ]]; then
    complete -o default -F __start_cheat cheat
else
    complete -o default -o nospace -F __start_cheat cheat
fi

# ex: ts=4 sw=4 et filetype=sh
```

### Zsh completion

```zsh
#compdef cheat
compdef _cheat cheat

# zsh completion for cheat                                -*- shell-script -*-

__cheat_debug()
{
    local file="$BASH_COMP_DEBUG_FILE"
    if [[ -n ${file} ]]; then
        echo "$*" >> "${file}"
    fi
}

_cheat()
{
    local shellCompDirectiveError=1
    local shellCompDirectiveNoSpace=2
    local shellCompDirectiveNoFileComp=4
    local shellCompDirectiveFilterFileExt=8
    local shellCompDirectiveFilterDirs=16
    local shellCompDirectiveKeepOrder=32

    local lastParam lastChar flagPrefix requestComp out directive comp lastComp noSpace keepOrder
    local -a completions

    __cheat_debug "\n========= starting completion logic =========="
    __cheat_debug "CURRENT: ${CURRENT}, words[*]: ${words[*]}"

    # The user could have moved the cursor backwards on the command-line.
    # We need to trigger completion from the $CURRENT location, so we need
    # to truncate the command-line ($words) up to the $CURRENT location.
    # (We cannot use $CURSOR as its value does not work when a command is an alias.)
    words=("${=words[1,CURRENT]}")
    __cheat_debug "Truncated words[*]: ${words[*]},"

    lastParam=${words[-1]}
    lastChar=${lastParam[-1]}
    __cheat_debug "lastParam: ${lastParam}, lastChar: ${lastChar}"

    # For zsh, when completing a flag with an = (e.g., cheat -n=<TAB>)
    # completions must be prefixed with the flag
    setopt local_options BASH_REMATCH
    if [[ "${lastParam}" =~ '-.*=' ]]; then
        # We are dealing with a flag with an =
        flagPrefix="-P ${BASH_REMATCH}"
    fi

    # Prepare the command to obtain completions
    requestComp="${words[1]} __complete ${words[2,-1]}"
    if [ "${lastChar}" = "" ]; then
        # If the last parameter is complete (there is a space following it)
        # We add an extra empty parameter so we can indicate this to the go completion code.
        __cheat_debug "Adding extra empty parameter"
        requestComp="${requestComp} \"\""
    fi

    __cheat_debug "About to call: eval ${requestComp}"

    # Use eval to handle any environment variables and such
    out=$(eval ${requestComp} 2>/dev/null)
    __cheat_debug "completion output: ${out}"

    # Extract the directive integer following a : from the last line
    local lastLine
    while IFS='\n' read -r line; do
        lastLine=${line}
    done < <(printf "%s\n" "${out[@]}")
    __cheat_debug "last line: ${lastLine}"

    if [ "${lastLine[1]}" = : ]; then
        directive=${lastLine[2,-1]}
        # Remove the directive including the : and the newline
        local suffix
        (( suffix=${#lastLine}+2))
        out=${out[1,-$suffix]}
    else
        # There is no directive specified.  Leave $out as is.
        __cheat_debug "No directive found.  Setting do default"
        directive=0
    fi

    __cheat_debug "directive: ${directive}"
    __cheat_debug "completions: ${out}"
    __cheat_debug "flagPrefix: ${flagPrefix}"

    if [ $((directive & shellCompDirectiveError)) -ne 0 ]; then
        __cheat_debug "Completion received error. Ignoring completions."
        return
    fi

    local activeHelpMarker="_activeHelp_ "
    local endIndex=${#activeHelpMarker}
    local startIndex=$((${#activeHelpMarker}+1))
    local hasActiveHelp=0
    while IFS='\n' read -r comp; do
        # Check if this is an activeHelp statement (i.e., prefixed with $activeHelpMarker)
        if [ "${comp[1,$endIndex]}" = "$activeHelpMarker" ];then
            __cheat_debug "ActiveHelp found: $comp"
            comp="${comp[$startIndex,-1]}"
            if [ -n "$comp" ]; then
                compadd -x "${comp}"
                __cheat_debug "ActiveHelp will need delimiter"
                hasActiveHelp=1
            fi

            continue
        fi

        if [ -n "$comp" ]; then
            # If requested, completions are returned with a description.
            # The description is preceded by a TAB character.
            # For zsh's _describe, we need to use a : instead of a TAB.
            # We first need to escape any : as part of the completion itself.
            comp=${comp//:/\\:}

            local tab="$(printf '\t')"
            comp=${comp//$tab/:}

            __cheat_debug "Adding completion: ${comp}"
            completions+=${comp}
            lastComp=$comp
        fi
    done < <(printf "%s\n" "${out[@]}")

    # Add a delimiter after the activeHelp statements, but only if:
    # - there are completions following the activeHelp statements, or
    # - file completion will be performed (so there will be choices after the activeHelp)
    if [ $hasActiveHelp -eq 1 ]; then
        if [ ${#completions} -ne 0 ] || [ $((directive & shellCompDirectiveNoFileComp)) -eq 0 ]; then
            __cheat_debug "Adding activeHelp delimiter"
            compadd -x "--"
            hasActiveHelp=0
        fi
    fi

    if [ $((directive & shellCompDirectiveNoSpace)) -ne 0 ]; then
        __cheat_debug "Activating nospace."
        noSpace="-S ''"
    fi

    if [ $((directive & shellCompDirectiveKeepOrder)) -ne 0 ]; then
        __cheat_debug "Activating keep order."
        keepOrder="-V"
    fi

    if [ $((directive & shellCompDirectiveFilterFileExt)) -ne 0 ]; then
        # File extension filtering
        local filteringCmd
        filteringCmd='_files'
        for filter in ${completions[@]}; do
            if [ ${filter[1]} != '*' ]; then
                # zsh requires a glob pattern to do file filtering
                filter="\*.$filter"
            fi
            filteringCmd+=" -g $filter"
        done
        filteringCmd+=" ${flagPrefix}"

        __cheat_debug "File filtering command: $filteringCmd"
        _arguments '*:filename:'"$filteringCmd"
    elif [ $((directive & shellCompDirectiveFilterDirs)) -ne 0 ]; then
        # File completion for directories only
        local subdir
        subdir="${completions[1]}"
        if [ -n "$subdir" ]; then
            __cheat_debug "Listing directories in $subdir"
            pushd "${subdir}" >/dev/null 2>&1
        else
            __cheat_debug "Listing directories in ."
        fi

        local result
        _arguments '*:dirname:_files -/'" ${flagPrefix}"
        result=$?
        if [ -n "$subdir" ]; then
            popd >/dev/null 2>&1
        fi
        return $result
    else
        __cheat_debug "Calling _describe"
        if eval _describe $keepOrder "completions" completions $flagPrefix $noSpace; then
            __cheat_debug "_describe found some completions"

            # Return the success of having called _describe
            return 0
        else
            __cheat_debug "_describe did not find completions."
            __cheat_debug "Checking if we should do file completion."
            if [ $((directive & shellCompDirectiveNoFileComp)) -ne 0 ]; then
                __cheat_debug "deactivating file completion"

                # We must return an error code here to let zsh know that there were no
                # completions found by _describe; this is what will trigger other
                # matching algorithms to attempt to find completions.
                # For example zsh can match letters in the middle of words.
                return 1
            else
                # Perform file completion
                __cheat_debug "Activating file completion"

                # We must return the result of this command, so it must be the
                # last command, or else we must store its result to return it.
                _arguments '*:filename:_files'" ${flagPrefix}"
            fi
        fi
    fi
}

# don't run the completion function when being source-ed or eval-ed
if [ "$funcstack[1]" = "_cheat" ]; then
    _cheat
fi
```

### Fish completion

```fish
# fish completion for cheat                                -*- shell-script -*-

function __cheat_debug
    set -l file "$BASH_COMP_DEBUG_FILE"
    if test -n "$file"
        echo "$argv" >> $file
    end
end

function __cheat_perform_completion
    __cheat_debug "Starting __cheat_perform_completion"

    # Extract all args except the last one
    set -l args (commandline -opc)
    # Extract the last arg and escape it in case it is a space
    set -l lastArg (string escape -- (commandline -ct))

    __cheat_debug "args: $args"
    __cheat_debug "last arg: $lastArg"

    # Disable ActiveHelp which is not supported for fish shell
    set -l requestComp "CHEAT_ACTIVE_HELP=0 $args[1] __complete $args[2..-1] $lastArg"

    __cheat_debug "Calling $requestComp"
    set -l results (eval $requestComp 2> /dev/null)

    # Some programs may output extra empty lines after the directive.
    # Let's ignore them or else it will break completion.
    # Ref: https://github.com/spf13/cobra/issues/1279
    for line in $results[-1..1]
        if test (string trim -- $line) = ""
            # Found an empty line, remove it
            set results $results[1..-2]
        else
            # Found non-empty line, we have our proper output
            break
        end
    end

    set -l comps $results[1..-2]
    set -l directiveLine $results[-1]

    # For Fish, when completing a flag with an = (e.g., <program> -n=<TAB>)
    # completions must be prefixed with the flag
    set -l flagPrefix (string match -r -- '-.*=' "$lastArg")

    __cheat_debug "Comps: $comps"
    __cheat_debug "DirectiveLine: $directiveLine"
    __cheat_debug "flagPrefix: $flagPrefix"

    for comp in $comps
        printf "%s%s\n" "$flagPrefix" "$comp"
    end

    printf "%s\n" "$directiveLine"
end

# this function limits calls to __cheat_perform_completion, by caching the result behind $__cheat_perform_completion_once_result
function __cheat_perform_completion_once
    __cheat_debug "Starting __cheat_perform_completion_once"

    if test -n "$__cheat_perform_completion_once_result"
        __cheat_debug "Seems like a valid result already exists, skipping __cheat_perform_completion"
        return 0
    end

    set --global __cheat_perform_completion_once_result (__cheat_perform_completion)
    if test -z "$__cheat_perform_completion_once_result"
        __cheat_debug "No completions, probably due to a failure"
        return 1
    end

    __cheat_debug "Performed completions and set __cheat_perform_completion_once_result"
    return 0
end

# this function is used to clear the $__cheat_perform_completion_once_result variable after completions are run
function __cheat_clear_perform_completion_once_result
    __cheat_debug ""
    __cheat_debug "========= clearing previously set __cheat_perform_completion_once_result variable =========="
    set --erase __cheat_perform_completion_once_result
    __cheat_debug "Successfully erased the variable __cheat_perform_completion_once_result"
end

function __cheat_requires_order_preservation
    __cheat_debug ""
    __cheat_debug "========= checking if order preservation is required =========="

    __cheat_perform_completion_once
    if test -z "$__cheat_perform_completion_once_result"
        __cheat_debug "Error determining if order preservation is required"
        return 1
    end

    set -l directive (string sub --start 2 $__cheat_perform_completion_once_result[-1])
    __cheat_debug "Directive is: $directive"

    set -l shellCompDirectiveKeepOrder 32
    set -l keeporder (math (math --scale 0 $directive / $shellCompDirectiveKeepOrder) % 2)
    __cheat_debug "Keeporder is: $keeporder"

    if test $keeporder -ne 0
        __cheat_debug "This does require order preservation"
        return 0
    end

    __cheat_debug "This doesn't require order preservation"
    return 1
end


# This function does two things:
# - Obtain the completions and store them in the global __cheat_comp_results
# - Return false if file completion should be performed
function __cheat_prepare_completions
    __cheat_debug ""
    __cheat_debug "========= starting completion logic =========="

    # Start fresh
    set --erase __cheat_comp_results

    __cheat_perform_completion_once
    __cheat_debug "Completion results: $__cheat_perform_completion_once_result"

    if test -z "$__cheat_perform_completion_once_result"
        __cheat_debug "No completion, probably due to a failure"
        # Might as well do file completion, in case it helps
        return 1
    end

    set -l directive (string sub --start 2 $__cheat_perform_completion_once_result[-1])
    set --global __cheat_comp_results $__cheat_perform_completion_once_result[1..-2]

    __cheat_debug "Completions are: $__cheat_comp_results"
    __cheat_debug "Directive is: $directive"

    set -l shellCompDirectiveError 1
    set -l shellCompDirectiveNoSpace 2
    set -l shellCompDirectiveNoFileComp 4
    set -l shellCompDirectiveFilterFileExt 8
    set -l shellCompDirectiveFilterDirs 16

    if test -z "$directive"
        set directive 0
    end

    set -l compErr (math (math --scale 0 $directive / $shellCompDirectiveError) % 2)
    if test $compErr -eq 1
        __cheat_debug "Received error directive: aborting."
        # Might as well do file completion, in case it helps
        return 1
    end

    set -l filefilter (math (math --scale 0 $directive / $shellCompDirectiveFilterFileExt) % 2)
    set -l dirfilter (math (math --scale 0 $directive / $shellCompDirectiveFilterDirs) % 2)
    if test $filefilter -eq 1; or test $dirfilter -eq 1
        __cheat_debug "File extension filtering or directory filtering not supported"
        # Do full file completion instead
        return 1
    end

    set -l nospace (math (math --scale 0 $directive / $shellCompDirectiveNoSpace) % 2)
    set -l nofiles (math (math --scale 0 $directive / $shellCompDirectiveNoFileComp) % 2)

    __cheat_debug "nospace: $nospace, nofiles: $nofiles"

    # If we want to prevent a space, or if file completion is NOT disabled,
    # we need to count the number of valid completions.
    # To do so, we will filter on prefix as the completions we have received
    # may not already be filtered so as to allow fish to match on different
    # criteria than the prefix.
    if test $nospace -ne 0; or test $nofiles -eq 0
        set -l prefix (commandline -t | string escape --style=regex)
        __cheat_debug "prefix: $prefix"

        set -l completions (string match -r -- "^$prefix.*" $__cheat_comp_results)
        set --global __cheat_comp_results $completions
        __cheat_debug "Filtered completions are: $__cheat_comp_results"

        # Important not to quote the variable for count to work
        set -l numComps (count $__cheat_comp_results)
        __cheat_debug "numComps: $numComps"

        if test $numComps -eq 1; and test $nospace -ne 0
            # We must first split on \t to get rid of the descriptions to be
            # able to check what the actual completion will be.
            # We don't need descriptions anyway since there is only a single
            # real completion which the shell will expand immediately.
            set -l split (string split --max 1 \t $__cheat_comp_results[1])

            # Fish won't add a space if the completion ends with any
            # of the following characters: @=/:.,
            set -l lastChar (string sub -s -1 -- $split)
            if not string match -r -q "[@=/:.,]" -- "$lastChar"
                # In other cases, to support the "nospace" directive we trick the shell
                # by outputting an extra, longer completion.
                __cheat_debug "Adding second completion to perform nospace directive"
                set --global __cheat_comp_results $split[1] $split[1].
                __cheat_debug "Completions are now: $__cheat_comp_results"
            end
        end

        if test $numComps -eq 0; and test $nofiles -eq 0
            # To be consistent with bash and zsh, we only trigger file
            # completion when there are no other completions
            __cheat_debug "Requesting file completion"
            return 1
        end
    end

    return 0
end

# Since Fish completions are only loaded once the user triggers them, we trigger them ourselves
# so we can properly delete any completions provided by another script.
# Only do this if the program can be found, or else fish may print some errors; besides,
# the existing completions will only be loaded if the program can be found.
if type -q "cheat"
    # The space after the program name is essential to trigger completion for the program
    # and not completion of the program name itself.
    # Also, we use '> /dev/null 2>&1' since '&>' is not supported in older versions of fish.
    complete --do-complete "cheat " > /dev/null 2>&1
end

# Remove any pre-existing completions for the program since we will be handling all of them.
complete -c cheat -e

# this will get called after the two calls below and clear the $__cheat_perform_completion_once_result global
complete -c cheat -n '__cheat_clear_perform_completion_once_result'
# The call to __cheat_prepare_completions will setup __cheat_comp_results
# which provides the program's completion choices.
# If this doesn't require order preservation, we don't use the -k flag
complete -c cheat -n 'not __cheat_requires_order_preservation && __cheat_prepare_completions' -f -a '$__cheat_comp_results'
# otherwise we use the -k flag
complete -k -c cheat -n '__cheat_requires_order_preservation && __cheat_prepare_completions' -f -a '$__cheat_comp_results'
```

### PowerShell completion

```powershell
# powershell completion for cheat                                -*- shell-script -*-

function __cheat_debug {
    if ($env:BASH_COMP_DEBUG_FILE) {
        "$args" | Out-File -Append -FilePath "$env:BASH_COMP_DEBUG_FILE"
    }
}

filter __cheat_escapeStringWithSpecialChars {
    $_ -replace '\s|#|@|\$|;|,|''|\{|\}|\(|\)|"|`|\||<|>|&','`$&'
}

[scriptblock]${__cheatCompleterBlock} = {
    param(
            $WordToComplete,
            $CommandAst,
            $CursorPosition
        )

    # Get the current command line and convert into a string
    $Command = $CommandAst.CommandElements
    $Command = "$Command"

    __cheat_debug ""
    __cheat_debug "========= starting completion logic =========="
    __cheat_debug "WordToComplete: $WordToComplete Command: $Command CursorPosition: $CursorPosition"

    # The user could have moved the cursor backwards on the command-line.
    # We need to trigger completion from the $CursorPosition location, so we need
    # to truncate the command-line ($Command) up to the $CursorPosition location.
    # Make sure the $Command is longer then the $CursorPosition before we truncate.
    # This happens because the $Command does not include the last space.
    if ($Command.Length -gt $CursorPosition) {
        $Command=$Command.Substring(0,$CursorPosition)
    }
    __cheat_debug "Truncated command: $Command"

    $ShellCompDirectiveError=1
    $ShellCompDirectiveNoSpace=2
    $ShellCompDirectiveNoFileComp=4
    $ShellCompDirectiveFilterFileExt=8
    $ShellCompDirectiveFilterDirs=16
    $ShellCompDirectiveKeepOrder=32

    # Prepare the command to request completions for the program.
    # Split the command at the first space to separate the program and arguments.
    $Program,$Arguments = $Command.Split(" ",2)

    $RequestComp="$Program __complete $Arguments"
    __cheat_debug "RequestComp: $RequestComp"

    # we cannot use $WordToComplete because it
    # has the wrong values if the cursor was moved
    # so use the last argument
    if ($WordToComplete -ne "" ) {
        $WordToComplete = $Arguments.Split(" ")[-1]
    }
    __cheat_debug "New WordToComplete: $WordToComplete"


    # Check for flag with equal sign
    $IsEqualFlag = ($WordToComplete -Like "--*=*" )
    if ( $IsEqualFlag ) {
        __cheat_debug "Completing equal sign flag"
        # Remove the flag part
        $Flag,$WordToComplete = $WordToComplete.Split("=",2)
    }

    if ( $WordToComplete -eq "" -And ( -Not $IsEqualFlag )) {
        # If the last parameter is complete (there is a space following it)
        # We add an extra empty parameter so we can indicate this to the go method.
        __cheat_debug "Adding extra empty parameter"
        # PowerShell 7.2+ changed the way how the arguments are passed to executables,
        # so for pre-7.2 or when Legacy argument passing is enabled we need to use
        # `"`" to pass an empty argument, a "" or '' does not work!!!
        if ($PSVersionTable.PsVersion -lt [version]'7.2.0' -or
            ($PSVersionTable.PsVersion -lt [version]'7.3.0' -and -not [ExperimentalFeature]::IsEnabled("PSNativeCommandArgumentPassing")) -or
            (($PSVersionTable.PsVersion -ge [version]'7.3.0' -or [ExperimentalFeature]::IsEnabled("PSNativeCommandArgumentPassing")) -and
              $PSNativeCommandArgumentPassing -eq 'Legacy')) {
             $RequestComp="$RequestComp" + ' `"`"'
        } else {
             $RequestComp="$RequestComp" + ' ""'
        }
    }

    __cheat_debug "Calling $RequestComp"
    # First disable ActiveHelp which is not supported for Powershell
    ${env:CHEAT_ACTIVE_HELP}=0

    #call the command store the output in $out and redirect stderr and stdout to null
    # $Out is an array contains each line per element
    Invoke-Expression -OutVariable out "$RequestComp" 2>&1 | Out-Null

    # get directive from last line
    [int]$Directive = $Out[-1].TrimStart(':')
    if ($Directive -eq "") {
        # There is no directive specified
        $Directive = 0
    }
    __cheat_debug "The completion directive is: $Directive"

    # remove directive (last element) from out
    $Out = $Out | Where-Object { $_ -ne $Out[-1] }
    __cheat_debug "The completions are: $Out"

    if (($Directive -band $ShellCompDirectiveError) -ne 0 ) {
        # Error code.  No completion.
        __cheat_debug "Received error from custom completion go code"
        return
    }

    $Longest = 0
    [Array]$Values = $Out | ForEach-Object {
        #Split the output in name and description
        $Name, $Description = $_.Split("`t",2)
        __cheat_debug "Name: $Name Description: $Description"

        # Look for the longest completion so that we can format things nicely
        if ($Longest -lt $Name.Length) {
            $Longest = $Name.Length
        }

        # Set the description to a one space string if there is none set.
        # This is needed because the CompletionResult does not accept an empty string as argument
        if (-Not $Description) {
            $Description = " "
        }
        New-Object -TypeName PSCustomObject -Property @{
            Name = "$Name"
            Description = "$Description"
        }
    }


    $Space = " "
    if (($Directive -band $ShellCompDirectiveNoSpace) -ne 0 ) {
        # remove the space here
        __cheat_debug "ShellCompDirectiveNoSpace is called"
        $Space = ""
    }

    if ((($Directive -band $ShellCompDirectiveFilterFileExt) -ne 0 ) -or
       (($Directive -band $ShellCompDirectiveFilterDirs) -ne 0 ))  {
        __cheat_debug "ShellCompDirectiveFilterFileExt ShellCompDirectiveFilterDirs are not supported"

        # return here to prevent the completion of the extensions
        return
    }

    $Values = $Values | Where-Object {
        # filter the result
        $_.Name -like "$WordToComplete*"

        # Join the flag back if we have an equal sign flag
        if ( $IsEqualFlag ) {
            __cheat_debug "Join the equal sign flag back to the completion value"
            $_.Name = $Flag + "=" + $_.Name
        }
    }

    # we sort the values in ascending order by name if keep order isn't passed
    if (($Directive -band $ShellCompDirectiveKeepOrder) -eq 0 ) {
        $Values = $Values | Sort-Object -Property Name
    }

    if (($Directive -band $ShellCompDirectiveNoFileComp) -ne 0 ) {
        __cheat_debug "ShellCompDirectiveNoFileComp is called"

        if ($Values.Length -eq 0) {
            # Just print an empty string here so the
            # shell does not start to complete paths.
            # We cannot use CompletionResult here because
            # it does not accept an empty string as argument.
            ""
            return
        }
    }

    # Get the current mode
    $Mode = (Get-PSReadLineKeyHandler | Where-Object {$_.Key -eq "Tab" }).Function
    __cheat_debug "Mode: $Mode"

    $Values | ForEach-Object {

        # store temporary because switch will overwrite $_
        $comp = $_

        # PowerShell supports three different completion modes
        # - TabCompleteNext (default windows style - on each key press the next option is displayed)
        # - Complete (works like bash)
        # - MenuComplete (works like zsh)
        # You set the mode with Set-PSReadLineKeyHandler -Key Tab -Function <mode>

        # CompletionResult Arguments:
        # 1) CompletionText text to be used as the auto completion result
        # 2) ListItemText   text to be displayed in the suggestion list
        # 3) ResultType     type of completion result
        # 4) ToolTip        text for the tooltip with details about the object

        switch ($Mode) {

            # bash like
            "Complete" {

                if ($Values.Length -eq 1) {
                    __cheat_debug "Only one completion left"

                    # insert space after value
                    $CompletionText = $($comp.Name | __cheat_escapeStringWithSpecialChars) + $Space
                    if ($ExecutionContext.SessionState.LanguageMode -eq "FullLanguage"){
                        [System.Management.Automation.CompletionResult]::new($CompletionText, "$($comp.Name)", 'ParameterValue', "$($comp.Description)")
                    } else {
                        $CompletionText
                    }

                } else {
                    # Add the proper number of spaces to align the descriptions
                    while($comp.Name.Length -lt $Longest) {
                        $comp.Name = $comp.Name + " "
                    }

                    # Check for empty description and only add parentheses if needed
                    if ($($comp.Description) -eq " " ) {
                        $Description = ""
                    } else {
                        $Description = "  ($($comp.Description))"
                    }

                    $CompletionText = "$($comp.Name)$Description"
                    if ($ExecutionContext.SessionState.LanguageMode -eq "FullLanguage"){
                        [System.Management.Automation.CompletionResult]::new($CompletionText, "$($comp.Name)$Description", 'ParameterValue', "$($comp.Description)")
                    } else {
                        $CompletionText
                    }
                }
             }

            # zsh like
            "MenuComplete" {
                # insert space after value
                # MenuComplete will automatically show the ToolTip of
                # the highlighted value at the bottom of the suggestions.

                $CompletionText = $($comp.Name | __cheat_escapeStringWithSpecialChars) + $Space
                if ($ExecutionContext.SessionState.LanguageMode -eq "FullLanguage"){
                    [System.Management.Automation.CompletionResult]::new($CompletionText, "$($comp.Name)", 'ParameterValue', "$($comp.Description)")
                } else {
                    $CompletionText
                }
            }

            # TabCompleteNext and in case we get something unknown
            Default {
                # Like MenuComplete but we don't want to add a space here because
                # the user need to press space anyway to get the completion.
                # Description will not be shown because that's not possible with TabCompleteNext

                $CompletionText = $($comp.Name | __cheat_escapeStringWithSpecialChars)
                if ($ExecutionContext.SessionState.LanguageMode -eq "FullLanguage"){
                    [System.Management.Automation.CompletionResult]::new($CompletionText, "$($comp.Name)", 'ParameterValue', "$($comp.Description)")
                } else {
                    $CompletionText
                }
            }
        }

    }
}

Register-ArgumentCompleter -CommandName 'cheat' -ScriptBlock ${__cheatCompleterBlock}
```

## Spec 25

The executable must preserve raw cheatsheet data robustly. In uncolorized ordinary view, write the exact body bytes even when they include NUL and control bytes. Do not decode/re-encode, normalize line endings, trim whitespace, append a newline, truncate, or wrap long lines. For table/search/frontmatter operations, handle valid UTF-8 Unicode filenames, tags, and contents. Files with no frontmatter remain ordinary text. All failure paths must terminate within the harness timeout rather than hanging or emitting a traceback/panic.
