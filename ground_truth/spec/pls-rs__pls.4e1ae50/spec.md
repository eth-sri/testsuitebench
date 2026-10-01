# Clarified specification for `executable`

## Spec 1

The required artifact is one executable file named exactly `executable`. It is a UTF-8 command-line directory lister with the public product name `pls`, intended for a Linux/POSIX filesystem. Unless an argument-validation failure is described below, an invocation exits with status 0 and writes its listing to stdout. A successful invocation does not write to stderr. Every nonempty logical output line ends with `\n`; an empty result is the empty byte string, not a placeholder message.

With no path operands, list the current working directory. `.` and `..`, absolute paths, relative paths containing directory components, paths ending in `/`, deep paths, Unicode paths, whitespace, shell metacharacters, and names up to the filesystem's maximum component length must all work. Directory enumeration must never synthesize `.` or `..` entries. Dotfiles are included by default except for the built-in below-cutoff entries `.git` and `.DS_Store` described in Spec 15.

The following option spellings are required. Options and paths may be interspersed, and both `--option=value` and `--option value` forms work except that a negative `--imp` value must use the equals form, as detailed in Specs 15 and 20:

| Short | Long | Value |
|---|---|---|
| `-d` | `--det` | repeatable detail field |
| `-g` | `--grid` | `true` or `false` |
| `-H` | `--header` | `true` or `false` |
| `-l` | `--sym` | `true` or `false` |
| `-s` | `--sort` | repeatable sort field |
| `-i` | `--icon` | `true` or `false` |
| `-S` | `--suffix` | `true` or `false` |
| `-a` | `--align` | `true` or `false` |
| `-t` | `--typ` | repeatable node type |

The long-only tested options are `--down`, `--collapse`, `--imp`, `--exclude`, `--only`, and `--unit`.

## Spec 2

`--help` exits 0, writes only to stdout, and presents a conventional help page whose usage line is exactly headed by `Usage: executable [OPTIONS] [PATHS]...`. It must contain headings or clearly delimited sections named `Arguments:`, `Options:`, `Detail view:`, `Grid view:`, `Presentation:`, `Filtering:`, and `Sorting:`. It must document `[PATHS]...`, `--det`, and `--grid` at minimum, along with the interface in this specification.

`--version` exits 0, writes only one newline-terminated line to stdout, and has the form `pls VERSION`. `VERSION` is nonempty, contains at least one digit, and contains at least one dot (for example, `pls 0.0.1-beta.9`).

Boolean-valued options accept only lowercase `true` and `false`. Invalid command-line syntax, an unknown option, an invalid enum value, an invalid regex, or an invalid integer exits 2, emits nothing to stdout, and emits the diagnostic to stderr. All other runtime errors described later are recoverable listing results and exit 0.

## Spec 3

A path operand which is a real directory means "list its immediate children"; it is not recursive. A path operand which is a regular file, FIFO, socket, device, or symlink means "display this operand as one entry." In particular, a symlink to a directory is never traversed when the symlink itself is supplied as an operand.

For an entry discovered inside a listed directory, display only its basename. For a direct non-directory operand, preserve the user's lexical spelling in the Name cell: an absolute operand remains absolute; `subdir/file.txt` remains that relative path; and `./src/../src/main.rs` remains exactly that spelling even though it is normalized internally to access metadata. Do not quote or shell-escape names.

One directory operand has no directory heading. Two or more directory operands each get a section headed by the operand spelling followed by `:`. Each such section begins with a blank line, including the first, and sections remain in operand order. Thus two operands `dir1 dir2` have the shape:

```text

dir1:
...children...

dir2:
...children...
```

When direct file-like operands and directory operands are mixed, display all direct entries first, then a blank line and the headed directory sections. Always preserve direct-operand order, even when an explicit sort is requested; sort options order children within each listed directory but do not reorder separate direct operands. Multiple unrelated absolute/relative direct operands remain separate entries with their supplied paths. Empty single directories produce no output; empty directories in a multi-directory invocation still have their heading.

## Spec 4

Use `lstat`-style metadata so symlinks have their own type, mode, size, and target text. Recognize regular file, directory, symlink, FIFO/named pipe, Unix socket, block device, and character device without crashing. At least 100 directory entries must be emitted without truncation.

The default presentation is one entry per line, icons enabled, suffixes enabled, symlink targets enabled, dot alignment enabled, grid disabled, headers enabled when detail fields exist, and collapsing enabled where a collapse relationship exists. Default sorting is described in Spec 13.

With suffixes enabled, append `/` to directories, `@` to symlinks, `|` to FIFOs, and `=` to sockets; ordinary regular files have no suffix. `--suffix=false` removes these suffix characters but does not independently hide symlink targets. `--icon=false` removes the icon cell but changes neither suffixes nor target text. These switches compose, so disabling both leaves plain aligned names (plus target text where applicable).

Names are emitted as valid UTF-8 without byte-based truncation. Unicode scalar sequences such as `café`, `日本語`, Greek text, and emoji must survive unchanged, and display-width calculations must not split multibyte text.

## Spec 5

An icon-enabled Name cell consists of a one-cell icon or blank placeholder, one separating space, the optionally aligned name, its optional suffix, and optional symlink annotation. A recognized icon followed by an aligned ordinary basename therefore appears as `ICON␠␠name`; an unrecognized icon is a blank icon cell and appears as three leading spaces before an ordinary basename. When a direct file operand is displayed, it normally uses `ICON␠path` without the directory-listing alignment pad.

The lowercase extensions below receive the stated mappings. More-specific filename rules override generic extension rules.

| Entry or pattern | Icon |
|---|---|
| ordinary directory | `` (U+F07B) |
| directory named `src` | `` |
| generic symlink without a stronger filename rule | `󰌹` |
| FIFO | `󰟥` |
| socket | `󰟨` |
| `.txt` | `` |
| `.md` | `` |
| `.rs` | `` |
| `.sh`, including executable shell scripts | `` |
| `.ini` | `` |
| `.json`, `.yaml`, `.yml`, `.toml` | `` |
| `.jpg`, `.png`, `.gif`, `.svg`, `.webp`, `.ico` | `󰋩` |
| `.mp3`, `.flac`, `.ogg`, `.wav` | `󰓃` |
| `.mp4`, `.mkv`, `.webm`, `.avi`, `.flv`, `.mov` | `󰕧` |
| `README`, `README.*` | `` |
| `LICENSE` | `` |
| `Makefile`, `justfile` | `󰜎` |
| `Dockerfile`, `docker-compose.yml` | `` |
| `Cargo.toml` | `` |
| `Cargo.lock` | `` |
| `.gitignore` | `󰊢` |
| `.env`, `.env.*` | `` |
| `.pls.yml` | `` |
| `rustfmt.toml` | `󰃢` |

Unknown extensions and extensionless ordinary files use the blank icon placeholder. Hidden files can still match extension rules; special full-name rules such as `.env.*` also apply. For compound names, use the final extension for extension-oriented rules. Symlinks can receive a filename icon (for example, a link named `link.txt` uses the text icon) while retaining symlink suffix/annotation behavior.

## Spec 6

With target display enabled (the default, or `--sym=true`), append one space, a state separator icon, one space, and the link text returned by `readlink`:

| Target state | Separator |
|---|---|
| resolvable target | `󰁔` |
| missing target | `󱞣` |
| symlink cycle | `󰑙` |

For example, a link created as `link.txt -> target.txt` is rendered as `link.txt@ 󰁔 target.txt`; an absolute link target stays absolute. A broken link is still listed. Detect cycles without recursively following forever: `link1 -> link2 -> link1` renders each listed link with the cyclic separator and its immediate stored target. For an acyclic chain, follow and append every stored target through the terminal target, placing the resolvable separator before every hop. Thus `link2 -> link1 -> target` renders as `link2@ 󰁔 link1 󰁔 target`.

`--sym=false` omits both the separator and target while retaining the symlink itself and, unless disabled separately, `@`. A symlink supplied as a direct operand remains a single output line even when it points at a directory. Configuration containing a top-level `symlink.error` mapping must not make ordinary or broken symlink processing crash, although unsupported configuration keys need not change the built-in rendering.

## Spec 7

`--det` switches to tabular detail view and is repeatable. Valid values, in the exact order shown in validation diagnostics, are:

```text
dev, ino, nlink, typ, perm, oct, user, uid, group, gid, size, blocks,
btime, ctime, mtime, atime, git, none, std, all
```

Every selected detail field becomes a column to the left of an always-present `Name` column. If there is at least one field and `--header` was not false, emit a header. With no selected fields, show normal name-only output and no header. `--header=false` suppresses only the header; `--header=true` is the default.

Process detail requests from left to right. An ordinary field removes its prior occurrence, if any, and appends it at the current position; consequently duplicates are represented once and the last occurrence determines column position. `none` clears all accumulated fields. `std` appends the standard fields `nlink, typ, perm, user, group, size, mtime`, applying the same deduplication. `all` clears the current list and installs, in order, `dev, ino, nlink, typ, perm, oct, user, uid, group, gid, size, blocks, btime, ctime, mtime, atime, git`. Therefore `std,none` yields no fields; `none,size,blocks` yields Size then Blocks; `all,std` still contains all fields; and `std,all` is reset to the canonical all-field order.

An empty directory in detail mode emits exactly its header plus `\n`. For `--det=std`, that empty header is exactly:

```text
Link# T Permissions User Group Size Modified Name
```

## Spec 8

Detail columns have these headings and values:

| Field | Heading | Value |
|---|---|---|
| `dev` | `Device` | nonnegative `st_dev` integer |
| `ino` | `inode` | positive `st_ino` integer |
| `nlink` | `Link#` | positive `st_nlink`; hard links share inode and increased count |
| `typ` | `T` | `d` directory, `f` regular file, `l` symlink, `p` FIFO, `s` socket, `b` block device, `c` character device |
| `perm` | `Permissions` | three space-separated `rwx` triplets |
| `oct` | `SUGO` | permission mode in octal as described in Spec 9 |
| `user` | `User` | owner name resolved from UID |
| `uid` | `UID` | numeric owner ID |
| `group` | `Group` | group name resolved from GID |
| `gid` | `GID` | numeric group ID |
| `size` | `Size` | lstat size for nondirectories; blank for directories |
| `blocks` | `Blocks` | allocated `st_blocks` for nondirectories; blank for directories |
| `btime` | `Created` | creation timestamp where included by `all` |
| `ctime` | `Changed` | metadata-change timestamp |
| `mtime` | `Modified` | modification timestamp |
| `atime` | `Accessed` | access timestamp |
| `git` | `Git` | a compact per-entry Git state or blank |

Time cells use local time and the fixed form `YYYY-Mon-DD hh:mmam` or `YYYY-Mon-DD hh:mmpm`, with English three-letter month names and 12-hour time (for example, `2024-Jan-01 12:00pm`). `mtime`, `ctime`, and `atime` must read their distinct filesystem fields. The all-field header contains each heading exactly once and ends in `Git Name`.

Names, IDs, device/inode/link counts, and timestamps must reflect live filesystem metadata, not fixture-specific constants. Unknown UID/GID handling may fall back to a numeric spelling, but IDs themselves remain available in numeric fields.

## Spec 9

Symbolic permissions are shown as three separate triplets: owner, group, other. Each triplet uses `r`, `w`, `x`, and `-` in the conventional positions. Special bits replace the execute character: setuid uses `s` when owner execute is present and `S` when absent; setgid uses `s`/`S` in group execute; sticky uses `t`/`T` in other execute. Thus modes include:

```text
4755 -> rws r-x r-x
4644 -> rwS r-- r--
2755 -> rwx r-s r-x
2644 -> rw- r-S r--
1755 -> rwx r-x r-t
1644 -> rw- r-- r-T
7755 -> rws r-s r-t
7644 -> rwS r-S r-T
0000 -> --- --- ---
0777 -> rwx rwx rwx
```

The `oct` value has width four. If any special bit is set, show all four octal digits (`1755`, `4755`, `6755`, `7755`, etc.). If the special digit is zero, replace that leading zero by a space rather than printing `0`, so ordinary modes are ` 644` and ` 755`. Given files `file1=0644`, `file2=4755`, and `file3=0755`, the exact table (ignoring only the final newline in this illustration) is:

```text
SUGO Name
 644    file1
4755    file2
 755    file3
```

The Name column uses the same icon rules, except that blank-icon names naturally appear after the table's inter-column padding. Symbolic permissions for symlinks come from the link's own lstat mode.

## Spec 10

`--unit` controls Size formatting and accepts `binary` (default), `decimal`, or `none`; if repeated, the last value wins.

In binary mode choose the largest of `B, KiB, MiB, GiB, TiB` whose 1024-based boundary is not greater than the byte count. In decimal mode use powers of 1000 and `B, kB, MB, GB, TB`. Show exactly one digit after the decimal point, including for byte values, and round to nearest at that precision rather than truncate. Examples: binary `1023 -> 1023.0 B`, `1024 -> 1.0 KiB`, `1536 -> 1.5 KiB`, `2816 -> 2.8 KiB`, `1048576 -> 1.0 MiB`; decimal `999 -> 999.0 B`, `1000 -> 1.0 kB`, `1024 -> 1.0 kB`, `1048576 -> 1.0 MB`; one TiB is `1.0 TiB` in binary and approximately `1.1 TB` in decimal. In `none` mode, print the exact integer byte count followed by ` B`, with no scaling and no decimal point.

Within one table, right-align the numeric portion to the widest numeric portion. Also align the unit subcolumn (`B` is padded to the width of `KiB`/`MiB` in binary, or `kB`/`MB` in decimal). Right-align the overall Size and Blocks cells and their headings to the widest cell. Directory Size and Blocks cells are blank rather than showing directory inode size or summing contents. A symlink size is the byte length of its stored target string, not the target file size. Blocks are the filesystem's allocated-block metadata, not a calculation from logical size; an empty regular file reports zero blocks.

## Spec 11

Detail output is a plain-text table. Determine each column's display width from its header and all data cells in that displayed group. Numeric fields (`dev`, `ino`, `nlink`, `oct`, `uid`, `gid`, `size`, `blocks`) are right-aligned; text and timestamp fields are left-aligned. Separate adjacent columns by one ASCII space. Use terminal display width, not UTF-8 byte length, for icons and Unicode names. Do not truncate long names.

Representative exact single-field tables are:

```text
T Name
d   dir755/
f   file644.txt
```

```text
Permissions Name
rwx r-x r-x   dir755/
rw- r-- r--   file644.txt
```

```text
Link# Name
    2   dir755/
    1   file.txt
```

The width of `Link#` is at least five, yielding four leading spaces before a one-digit value. Headers for isolated timestamps are exactly `Modified            Name`, `Changed             Name`, and `Accessed            Name`; the timestamp cell width is 19. Suppressing headers does not change data-column widths.

## Spec 12

Dot alignment concerns only a basename being shown as a directory child. With `--align=true` (the default), a name beginning with `.` receives no alignment pad and an ordinary name receives one leading ASCII space, so the first character after a dot visually aligns with the first ordinary character. Multiple leading dots are retained. With `--align=false`, neither class receives that alignment pad. With icons disabled, for example:

```text
# align=true
.config
..dotdot
 normal.txt

# align=false
.config
..dotdot
normal.txt
```

The same rule works for Unicode dotfiles and ordinary Unicode names. Direct path operands containing parent components are preserved and are not given an extra pad merely because their final basename is ordinary. Alignment composes with table view and collapse indentation.

When stdout is not a terminal (as when captured by a test harness), do not emit ANSI color/style escapes. Configuration styles must still parse, but captured output is plain UTF-8. This rule keeps table widths and golden text deterministic.

## Spec 13

`--sort` is repeatable. Valid values are exactly:

```text
dev, ino, nlink, typ, cat, user, uid, group, gid, size, blocks,
btime, ctime, mtime, atime, name, cname, ext,
inode_, nlinks_, typ_, cat_, user_, uid_, group_, gid_, size_, blocks_,
btime_, ctime_, mtime_, atime_, name_, cname_, ext_, none
```

Ordinary forms sort ascending. A trailing underscore means descending for the corresponding supported key. Apply multiple keys left-to-right as primary, secondary, and later tie breakers. Sorting is stable for entries equal under all requested keys. Remove duplicate sort keys without changing the effective order. `none` clears all sort keys accumulated before it and leaves filesystem discovery order.

With no explicit sort, use `cat` then `cname`: directories/categories precede ordinary files and each group is ordered by canonical name. Explicit `name` compares the raw displayed basename case-sensitively and lexicographically, so leading `.` sorts before digits, uppercase letters, `_`, and lowercase letters according to ordinary string ordering. `cname` removes every leading non-alphanumeric Unicode character and lowercases the remainder before comparison; ties retain discovery order. Hence `AAA.txt` and `aaa.txt` are adjacent, while `!exclaim.txt`, `.hidden`, and `_special.txt` compare using `exclaim`, `hidden`, and `special`. Unicode text and non-Latin scripts must not crash canonical comparison.

`ext` compares the substring after the final dot; a leading-dot name with no further dot and an extensionless name have the empty extension and sort before nonempty extensions. Compound `file.tar.gz` compares as `gz`. Within equal extensions, a later sort key such as `cname` supplies the tie breaker.

## Spec 14

The other sort keys compare their live metadata: `size` logical lstat size, `blocks` allocated blocks, `nlink` link count, `ino` inode, `uid`/`gid` numeric IDs, `user`/`group` resolved names, and `mtime`/`ctime`/`atime` their respective timestamps. For ascending `size`, all nondirectory sizes sort numerically first and the directory blank/none value sorts after them: zero-byte file, positive-size file, then directory. Descending `size_` reverses that order and places the directory first. `typ` compares node type, while `cat` compares the broader display category; in the tested regular-file/directory mixture, directories precede files ascending and follow files descending. Numeric/time ascending is smallest/oldest first; underscore reversal is largest/newest first. These sort keys order children within a listed directory. They do not reorder separate direct operands, which remain in command-line order as specified in Spec 3.

There are two required compatibility failure cases. Although `inode_` and `nlinks_` pass argument validation, attempting to use either reaches an internal unsupported reverse comparison. The process must exit nonzero and stderr must contain both:

```text
panicked at src/enums/sort_field.rs
internal error: entered unreachable code: src/enums/sort_fields.rs / impl SortField / cmp_time
```

Do not silently reinterpret these spellings as working `ino_` or `nlink_` sorts.

## Spec 15

Filtering is performed on immediate entry basenames before rendering. `--typ` accepts `dir`, `symlink`, `fifo`, `socket`, `block-device`, `char-device`, `file`, `none`, and `all`. Process repeated values from left to right. A concrete type adds that type to the allowed set, so repeated concrete values form a union (for example, `--typ file --typ dir` admits both). `none` clears the set at that position; later concrete values can add types again, so `--typ=none --typ=file` admits files while `--typ=file --typ=none` admits nothing. `all` adds all recognized types, after which regex filters still apply. A requested type absent from a directory simply produces empty output.

`--only REGEX` retains entries whose basename has a regex search match; `--exclude REGEX` removes entries whose basename has a regex search match. Both must use a Rust-regex-compatible syntax supporting anchors, alternation, character classes, escapes, quantifiers, and inline flags such as `(?i)`. Matching is case-sensitive unless the regex itself changes that. `--typ`, `--only`, and `--exclude` combine by logical AND. Examples that must work include retaining names matching `test`, retaining the literal bracket with `test\[`, retaining `(?i)FILE`, selecting directories matching `sub`, and selecting files matching `file` while excluding `\.log$`. `--exclude '.*'` removes everything.

Each entry also has an integer importance, supplied by matching configuration specs. The built-in baseline is 1 for an ordinary nonhidden entry, 0 for an ordinary dotfile (including `.pls.yml`), and -1 for `.DS_Store` and `.git`. The implicit default cutoff is 0, so normal hidden files and `.pls.yml` are shown while `.DS_Store` and `.git` are omitted. Explicit `--imp N` retains importance values at least `N`; it accepts signed 8-bit values from -128 through 127. A negative value must be attached with `=`, as in `--imp=-3`; when passed as a separate token it is parsed as an unexpected argument rather than as the option value. Thus `--imp=0` shows an ordinary dotfile and ordinary nonhidden file but not `.DS_Store`, `--imp=1` shows only the nonhidden file, and `--imp=2` shows none of those three. A custom importance `-5` is hidden by `--imp 0`, while a configured value `-2` is visible under `--imp=-3`. Importance filtering composes with type and regex filtering.

## Spec 16

`--grid=true` lays the already filtered and sorted entries into fixed-width cells. Read terminal width from `PLS_COLUMNS` when present; otherwise honor `COLUMNS`; if neither yields a usable width in a non-TTY, fall back to one column. Cell width is based on terminal display width of the longest complete rendered entry plus inter-cell padding. Choose as many columns as the implementation's cells fit without wrapping or truncation, then pad every non-final cell with ASCII spaces. Wide entries force fewer columns and an item wider than the terminal forces a one-column fallback.

Default `--down=false` fills rows left-to-right. `--down=true` fills each column top-to-bottom before moving right, preserving the same underlying entry order. The following tested sizing outcomes are normative and disambiguate layout calculations:

- Twenty names `file1.txt` through `file20.txt`, with icons, use 2 columns at width 40, 5 columns at width 100, and one column at width 15.
- Fifty names `very_long_filename_01.extension` through `...50.extension` use exactly 2 columns and 25 rows at width 80.
- Twenty short extensionless names `f1` through `f20` fit at least five per first row and no more than five rows at width 100 (the standard layout is ten columns by two rows).
- Five names `file1.txt` through `file5.txt` use one column at width 10.

Grid mode retains icons, suffixes, and dot alignment unless their switches disable them. It produces exactly empty output for an empty directory. Symlink target annotations are omitted from multi-entry grid cells; the symlink name and `@` remain. Collapse relationships are disabled in grid mode even if `--collapse=true`.

## Spec 17

`--collapse=true` groups a known dependent entry under its principal entry. The required built-in relationship is `Cargo.lock` under `Cargo.toml`, but only when both occur in the same listed group. The principal remains at its normal root position and the child follows on its own line, indented exactly as `   └─ ` before the child's icon/name. An orphan `Cargo.lock` remains a normal root entry. `--collapse=false` shows both at root. The default is collapse enabled.

For example, a directory containing `src/`, `Cargo.lock`, `Cargo.toml`, `lib.rs`, and `README.md` renders in ordinary collapsed mode as:

```text
  src/
  Cargo.toml
   └─   Cargo.lock
  lib.rs
  README.md
```

Detail view applies the tree prefix inside the Name column while retaining the child's own metadata in all other columns. Alignment still applies to noncollapsed and collapsed names. Grid mode instead renders every entry at root.

## Spec 18

Configuration is YAML. A file named `.pls.yml` in the directory being listed is itself an ordinary listed entry (with its built-in icon and importance 0). Configuration discovery has one base source plus an optional current-directory source:

1. When `PLS_CONFIG` is set, its value is the base configuration path. A nonexistent path is silently ignored but still suppresses the HOME fallback.
2. When `PLS_CONFIG` is unset, `$HOME/.pls.yml` is the base configuration path.
3. A `.pls.yml` in the current working directory is also loaded. Do not search Git ancestors for `.pls.yml` files.

When both a base configuration and the current-directory configuration exist, merge those two: icon definitions from the current-directory file override same-named base definitions, and specs from both remain available with current-directory specs later. Git-ancestor configurations are not part of this merge. Consequently, with `.pls.yml` files at `repo/.pls.yml` and `repo/sub/.pls.yml` and the process running in `repo/sub`, only the `repo/sub` file is discovered unless the parent file is separately named by `PLS_CONFIG` or is the selected HOME base. Empty YAML and YAML comments are accepted and leave built-in defaults operating. Duplicate YAML mapping keys use the last value.

Malformed or schema-invalid configuration is a recoverable listing error: exit 0, put the diagnostic in stdout, and do not use stderr. Prefix it with the affected path heading and a tab-indented `error:`. For a current-directory config containing `icons:\n  bad: [unclosed\n`, the exact output is:

```text
.:
	error: did not find expected ',' or ']' at line 3 column 1, while parsing a flow sequence at line 2 column 8 in .pls.yml YAML file
```

A malformed flow mapping analogously reports `did not find expected ',' or '}'` and `while parsing a flow mapping`, including the `.pls.yml YAML file` reference. Configuration regex compilation failures expose the parser details; for a first user spec pattern `[unclosed`, the exact current-directory diagnostic is:

```text
.:
	error: regex parse error:
    [unclosed
    ^
error: unclosed character class for key "default.specs.24.pattern" in .pls.yml YAML file
```

## Spec 19

The supported custom-icon schema is:

```yaml
icons:
  logical_name: "UTF-8 icon text"
specs:
  - pattern: 'regular expression matched against basename'
    icons:
      - logical_name
      - fallback_logical_name
    style: "optional style expression"
    importance: 2
```

All properties are optional except `pattern`. A spec may contain only importance or only style. For `icons`, inspect only the first logical name in the list. If it is defined, use its value; if it is undefined, abandon that custom icon choice and use the built-in fallback rather than trying later names. For example, with `icons: [missing, flame]` and only `flame: '🔥'` defined, an extensionless regular file uses the built-in fallback ``, not `🔥`. Apply every matching spec in order, retaining an earlier property when a later match omits it and replacing it when a later match supplies it. Thus three matching specs that supply icons 1, 2, and 3 leave icon 3, while an icon-setting spec followed by an importance-only spec retains the icon. The singular key `icon:` is not the supported list form and does not override built-in icon selection.

Patterns use the regex rules from Spec 15. Custom icon strings may be emoji or arbitrary Unicode such as `🔥`, `🌍`, or `→`. Parse style tokens such as `red bold`, `green`, and `rgb(255,100,50)`; captured/non-TTY output remains uncolored per Spec 12. `app_const.node_spacing` is accepted. `entry_const.perm` style keys such as `owner_read`, `owner_write`, and `owner_exec` are accepted without altering permission text.

For compatibility, these two malformed schema shapes must produce the exact recoverable errors shown (followed by a final newline):

```text
.:
	error: invalid type: found string "DIR", expected struct TypInfo for key "default.entry_const.typ.dir" in .pls.yml YAML file
```

```text
.:
	error: unknown variant: found `icon`, expected `one of `ok`, `broken`, `cyclic`, `error`` for key "default.entry_const.symlink.icon" in .pls.yml YAML file
```

An icon value ending in `.svg` may be treated as an image path. Expand environment variables in it, resolve relative paths against the applicable working/config directory, parse `PLS_ICON_SCALE` as a float with default 1.0, and clamp values above 2.0. Invalid scales fall back to 1.0. In a captured terminal without a usable image protocol, a configured SVG image, a missing SVG, malformed SVG, or a path containing an undefined environment variable falls back to the blank icon placeholder without a diagnostic or crash. A literal `.svg` file still receives the built-in image-file glyph.

## Spec 20

Filesystem lookup failures are recoverable and are printed to stdout in operand-processing order, before valid directory sections. A missing operand has exactly this form, including the tab and the single final newline; there is no blank line after the diagnostic:

```text
OPERAND:
	error: No such file or directory (os error 2)
```

Continue after an error so every missing operand gets one diagnostic and every valid operand is still listed. The exit status remains 0, even in detail or filtered mode. An empty result and a missing-path result must therefore remain distinguishable.

Argument-validation diagnostics use the following clap-style form and end in `For more information, try '--help'.` plus a newline. The exact possible-value lists are those in Specs 7, 13, and 15; their diagnostic metavariables are `--det <DETAILS>`, `--sort <SORT_BASES>`, `--typ <TYPES>`, `--only <ONLY>`, and `--exclude <EXCLUDE>`. Representative exact diagnostics are:

```text
error: invalid value 'invalid' for '--unit <UNIT>'
  [possible values: binary, decimal, none]

For more information, try '--help'.
```

```text
error: invalid value 'invalid' for '--icon <ICON>'
  [possible values: true, false]

For more information, try '--help'.
```

```text
error: invalid value 'notanumber' for '--imp <IMP>': invalid digit found in string

For more information, try '--help'.
```

For an out-of-range importance supplied as an option value, use `error: invalid value '999' for '--imp <IMP>': 999 is not in -128..=127`; the equals-form `--imp=-200` analogously reports `error: invalid value '-200' for '--imp <IMP>': -200 is not in -128..=127`. In contrast, the two-token invocation `--imp -200` does not consume the negative token as the value and emits exactly:

```text
error: unexpected argument '-2' found

  tip: to pass '-2' as a value, use '-- -2'

Usage: executable [OPTIONS] [PATHS]...

For more information, try '--help'.
```

An invalid `--only=[a-z` starts with `error: invalid value '[a-z' for '--only <ONLY>':`; an invalid `--exclude=[invalid` starts with `error: invalid value '[invalid' for '--exclude <EXCLUDE>':`. Each prefix is followed by:

```text
regex parse error:
    PATTERN
    ^
error: unclosed character class
```

An unknown `--unknown-flag` emits exactly:

```text
error: unexpected argument '--unknown-flag' found

  tip: to pass '--unknown-flag' as a value, use '-- --unknown-flag'

Usage: executable [OPTIONS] [PATHS]...

For more information, try '--help'.
```
