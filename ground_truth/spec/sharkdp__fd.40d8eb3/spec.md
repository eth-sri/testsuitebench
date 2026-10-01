# Behavioral specification for `executable`

The artifact is a single directly runnable program named exactly `executable`. The descriptions below define its complete externally observable contract on a Unix-like system. Paths shown with `/` use the Unix separator. Unless a section explicitly gives another status, successful searches—including searches with no matches—exit with status 0, write results to standard output, and leave standard error empty. Options may precede or follow the search pattern unless `--exec` or `--exec-batch` has begun consuming its command.

## Spec 1

The program is an `fd`-compatible recursive filesystem entry finder. Its invocation grammar is `executable [OPTIONS] [pattern] [path]...`. With no pattern, or with an explicitly empty pattern, every eligible entry below the search root matches. With no root path, the root is the current working directory. The root itself is never emitted; its descendants are. A normal no-match search is successful and produces no output. `--version` and `-V` both print exactly `fd 10.3.0\n` to stdout and exit 0 with empty stderr. `--help` and `-h` take precedence over otherwise invalid following arguments, exit 0, and have the exact outputs specified later.

Options support their shown long and short spellings, `--option=value` where applicable, and ordinary attached type forms such as `-tf`, `-td`, `-tl`, `-tx`, `-te`, `-tp`, and `-ts`. Repeatable options may occur multiple times. `--` terminates option parsing so a pattern beginning with `-` can be supplied. Once `-x`/`--exec` or `-X`/`--exec-batch` is encountered, following words belong to the external command until an optional standalone `;` command separator.

## Spec 2

For each visited descendant, matching normally applies only to its basename, not to directory components. The default matcher is an unanchored regular expression, so `foo` matches `a.foo` and `directory_foo`, while `^foo$` requires the whole basename. The matcher supports normal Rust-regex-style constructs exercised by the contract: `.`, `.*`, `+`, `^`, `$`, groups, alternation, `[abc]`, `[a-z]`, negated character classes, `\d`, and `\w`. A pattern containing `/` is still a basename regex unless `--full-path` is active.

All filters compose conjunctively: every required name pattern, depth constraint, extension, size, time, owner, ignore, exclusion, and special-type constraint must permit an entry. Repeated `--type` and repeated `--extension` are unions within their own category. Each supplied root is searched independently: overlapping roots and repeated positional or `--search-path` roots emit one copy for every traversal that reaches the entry. For example, if `one/sub/item` exists, `executable '' one one one/sub` emits `one/sub/` twice and `one/sub/item` three times.

## Spec 3

`--glob`/`-g` switches every primary and `--and` pattern to glob syntax. A glob without a slash matches basenames at any depth. It supports `*` (zero or more non-separator characters), `?` (exactly one), bracket classes and ranges including negation, brace alternatives such as `*.{txt,rs}`, and recursive `**`. `**/*.txt` matches `.txt` files both at the root and below it. A single `*` does not cross a path separator. In glob mode, ordinary literal text is matched as a complete basename rather than as a substring. `--regex` switches back to regex mode and overrides an earlier `--glob`.

Malformed regexes and globs are rejected before walking, but only after search-root validation. Each invalid root diagnostic is written first. If no valid root remains, the program writes the invalid-root diagnostics and `[fd error]: No valid search paths given.\n`, exits 1, and does not diagnose malformed pattern syntax. Thus `[invalid`, `(unclosed`, or `*invalid` with the sole root `missing-root` each produces only the two root-error lines specified in Spec 5. If at least one root is valid, malformed-pattern validation still occurs before traversal. The relevant exact pattern diagnostics are in Spec 26. In particular, unclosed classes/groups, a quantifier without an operand, and an unclosed glob bracket or brace are errors.

## Spec 4

`--fixed-strings`/`-F` makes every search pattern a literal substring: regex and glob metacharacters such as `.`, `*`, `[`, `]`, and parentheses have no special meaning. This remains substring matching, not whole-basename matching. An empty fixed pattern matches everything.

Matching uses smart case by default: if all literal alphabetic characters in all patterns are lowercase, matching is Unicode-aware case-insensitive; the presence of an uppercase letter makes matching case-sensitive. `--case-sensitive`/`-s` forces sensitivity, and `--ignore-case`/`-i` forces insensitivity. If both occur, the last one on the command line wins. These case rules apply to regex, glob, and fixed-string matching, but not to extension filtering (Spec 12). `--and <pattern>` is repeatable; the primary pattern and all additional patterns must match the same basename (or full path under `--full-path`). An invalid `--and` pattern is fatal no matter where it occurs.

## Spec 5

Search roots may be supplied as positional `[path]...` after the pattern, or by repeating `--search-path <path>`. Multiple roots contribute independently to the output rather than being deduplicated as a set. A relative positional root remains as the leading component in displayed results (for example, searching `one` prints `one/file`); an absolute root produces absolute displayed paths. `--search-path` follows the same relative/absolute display rule. With the default root `.` the usual display omits `./`.

`--base-directory <path>`/`-C <path>` first changes the logical working directory. All relative roots, search paths, ignore-file paths, and output paths are then resolved relative to that directory. Output is relative to this new base unless another path-display mode dictates otherwise. A nonexistent or non-directory base is an exit-1 error containing `The '--base-directory' path '<path>' is not a directory.`

Each invalid search root produces `[fd error]: Search path '<path>' is not a directory.\n`. If at least one root is valid, invalid roots do not prevent searching the valid ones. If none is valid, append `[fd error]: No valid search paths given.\n` and exit 1. A regular file is not a valid search root.

## Spec 6

Traversal is recursive without an artificial maximum and must handle at least 150 directory levels and 1,000 entries in one directory. Depth is one-based for descendants: immediate children of a root are depth 1. `--max-depth <n>`/`-d <n>` visits and emits only depths at most `n`; zero emits nothing. `--min-depth <n>` suppresses shallower entries but still traverses through them. `--exact-depth <n>` is equivalent to setting both minimum and maximum to `n`. The options combine normally, and a minimum beyond the tree produces no output. The legacy spellings `--maxdepth` and `--mindepth` must be recognized sufficiently to validate their numeric values.

Directories that are emitted in ordinary output always end in one separator; this applies at every depth. By default, output order for the deterministic trees in this contract is bytewise/lexicographic path order, with a directory emitted before descendants whose paths follow it. Features explicitly documented as parallel may otherwise have nondeterministic order, and batch argument order is not significant.

## Spec 7

Basenames beginning with `.` are hidden. Hidden files are suppressed and hidden directories are not descended into by default. `--hidden`/`-H` enables both, and `--no-hidden` disables them again; opposing flags use the last occurrence. `--unrestricted`/`-u` is equivalent to `--hidden --no-ignore`; repeated `u` spellings such as `-uu` and `-uuu` remain accepted and unrestricted.

When hidden searching is disabled, an anchored regex that clearly can match only leading-dot names (for example `^\..*`) is an exit-1 user error. Its diagnostic is byte-exact:

```text
[fd error]: The pattern(s) seems to only match files with a leading dot, but hidden files are filtered by default. Consider adding -H/--hidden to search hidden files as well or adjust your search pattern(s).
```

Likewise, an exact leading-dot glob such as `.gitignore` errors without `--hidden`. A plain unanchored regex `.gitignore` is allowed and simply yields no hidden results.

## Spec 8

Ignore rules use gitignore syntax, including basename patterns, directory patterns ending in `/`, `*`, `**`, path-specific patterns, comments, and later `!` negation. By default the walk honors `.ignore` and `.fdignore` files in and above the walk, and honors `.gitignore`, Git exclude data, and the standard per-user Git ignore file (such as `$XDG_CONFIG_HOME/git/ignore`) when the root is inside a Git repository. It does not discover a different global ignore file merely because `core.excludesFile` names it in the file selected by `GIT_CONFIG_GLOBAL`. Nested ignore files affect their subtrees. A nested `.git` begins a repository boundary, so `.gitignore` rules above it no longer apply inside it. An explicitly named search root is traversed even if its own name matches an ancestor ignore rule; ignore rules still apply to descendants. `.fdignore` has higher precedence than `.ignore`, which has higher precedence than `.gitignore`; higher-precedence or later negations can re-include an entry. Ignore files are themselves hidden by the normal hidden rule.

`--no-ignore`/`-I` disables all ignore sources; `--ignore` reverses it. `--no-ignore-vcs` disables only VCS ignore sources while leaving `.ignore` and `.fdignore` active; `--ignore-vcs` reverses it. `--no-require-git` makes `.gitignore` rules apply even outside a detected repository; `--require-git` restores the repository requirement. `--no-ignore-parent` disables ignore files inherited from ancestors but not ignore files inside the searched tree. `--no-global-ignore-file` disables fd's own global ignore file, such as `$XDG_CONFIG_HOME/fd/ignore`; it does not disable the standard Git global ignore source.

`--ignore-file <path>` is repeatable and loads an additional gitignore-format file. A malformed line is skipped silently, later valid rules in that file remain active, and the search exits 0 if nothing else fails. A nonexistent custom ignore file likewise does not abort the search: the program applies no rules from it, continues producing results, exits 0, and writes exactly one diagnostic of the form `[fd error]: Malformed pattern in custom ignore file. <path>: No such file or directory (os error 2).\n` to stderr.

## Spec 9

`--exclude <glob>`/`-E <glob>` is repeatable and filters both output and traversal. Excludes use gitignore/glob-style matching: `*.foo` excludes matching basenames anywhere; `one/two/` excludes that subtree; `one/**/*.foo` crosses descendants. Multiple excludes form a union. Exclusion applies in addition to name patterns and other filters and has priority over ignore-file re-inclusion. An empty exclude pattern is accepted, excludes every entry, emits nothing, and exits 0 with empty stderr.

`--prune` emits matching directories but does not descend into any directory that itself satisfies the search criteria; nonmatching directories are still traversed. `--ignore-contain <name>` suppresses an entire directory when it directly contains an entry of that name. This containment check takes precedence over root/depth emission decisions so the directory and its descendants are absent.

## Spec 10

Symbolic links are entries and can match normally, including dangling links. By default the program never descends through a directory symlink. `--follow`/`-L` follows directory links; `--no-follow` reverses it. Following a directory link may produce descendants under both the real and symlink paths. Without `--follow`, type filtering classifies every link as `symlink`, never by its target. With `--follow`, a resolvable link is classified by its target (so a good link is absent from `--type l`), while a dangling link remains a symlink and is still returned by `--type l`. Broken links remain usable by formatting, colors, details, and execution.

Filesystem loops must never hang. With `--follow`, a loop entry is not emitted or executed. By default its error is suppressed and other entries continue. With `--show-errors`, stderr contains one line per loop in the form `[fd error]: File system loop found: <loop-path> points to an ancestor <ancestor>\n`; processing still succeeds if commands succeed. For a search rooted at the current directory, both diagnostic paths use cwd-relative action-style spelling: the loop is prefixed with `./`, and the current directory as ancestor is `./`. For example, a link `loop_dir/circular` back to the root produces exactly `[fd error]: File system loop found: ./loop_dir/circular points to an ancestor ./\n` in ordinary, `--exec`, and `--exec-batch` processing.

`--one-file-system`, `--mount`, and `--xdev` are equivalent: do not descend from a root onto another device/filesystem. Multiple roots each establish their own starting device.

## Spec 11

`--type <value>`/`-t <value>` is repeatable and accepts these aliases: `f` or `file`; `d`, `dir`, or `directory`; `l` or `symlink`; `s` or `socket`; `p` or `pipe`; `b` or `block-device`; `c` or `char-device`; `x` or `executable`; `e` or `empty`. Repeated ordinary types are ORed. `-tf` and similar attached values are valid.

`file` means a regular file, `directory` a real directory, `symlink` any symlink including broken ones, and pipe/socket/device types use the filesystem entry type. `executable` selects regular files having an executable permission bit (not merely a shebang or extension) and implicitly restricts to files unless another ordinary type is also requested. `empty` selects zero-byte regular files and directories having no direct entries at all; hidden contents count when deciding whether a directory is empty. With `empty` plus `file` or `directory`, restrict emptiness to that ordinary type; with `empty` alone search both. Invalid type values are argument errors.

## Spec 12

`--extension <ext>`/`-e <ext>` is repeatable. It selects regular files whose final filename suffix, after the last dot, equals any supplied extension case-insensitively. This comparison ignores `--case-sensitive`/`-s`; for example, `-s '' -e TXT` matches both `UPPER.TXT` and `alpha.txt`. A leading dot on the option value is optional, so `foo` and `.foo` are equivalent. Multiple extensions are ORed; extension filtering still combines by AND with name and type filters. A name such as `archive.tar.gz` has extension `gz`. Extensionless entries do not match an extension filter.

## Spec 13

`--size <constraint>`/`-S <constraint>` filters regular files by byte length. Syntax is an optional `+` or `-`, then an unsigned integer, then a mandatory case-insensitive unit. No sign means exact equality, `+` means greater than or equal, and `-` means less than or equal (boundaries are inclusive). Decimal units `b`, `k`/`kb`, `m`/`mb`, `g`/`gb`, `t`/`tb` use powers of 1000; binary `ki`/`kib`, `mi`/`mib`, `gi`/`gib`, `ti`/`tib` use powers of 1024. Large values must not overflow. A bare number, nonnumber, or unknown unit is an argument error using the exact template in Spec 26. Size filtering composes with every other filter.

## Spec 14

`--changed-within <value>` selects entries whose modification time is newer than the cutoff; aliases are `--change-newer-than`, `--newer`, and `--changed-after`. `--changed-before <value>` selects entries older than the cutoff; aliases are `--change-older-than` and `--older`. Both together create an intersection/range.

A value may be a duration before now or an absolute local-time cutoff. Durations accept integer quantities with common singular/plural or abbreviated units, including `min`/`minute(s)`, `h`/`hour(s)`, `d`/`day(s)`, `week(s)`, and `year(s)`; use 60 seconds per minute, 3600 per hour, 86400 per day, 7 days per week, and 365 days per year. Absolute forms are `YYYY-MM-DD HH:MM:SS`, `YYYY-MM-DD` (midnight), and `@<Unix-seconds>`. Invalid values exit 1 with the diagnostic in Spec 26. Boundary comparisons follow fd behavior: “within” is strictly newer; “before” includes the cutoff tolerance exposed by filesystem timestamp precision.

## Spec 15

`--owner <user:group>`/`-o <user:group>` filters using Unix uid/gid metadata. Either side is optional: `alice`, `1000`, `:staff`, `:100`, or `alice:staff`. Names are resolved from the system user/group databases; decimal IDs compare numerically. Prefix either component with `!` to negate that component. When both components are present, both conditions must hold. Empty values `''` and `':'` impose no restriction. Owner filters combine with pattern, type, and size filters.

Invalid owner values are exit-2 parser errors in the form described by Spec 24. For an unknown user, the explanation is exactly `'<name>' is not a recognized user name`; for an unknown group, it is exactly `'<name>' is not a recognized group name`. More than one colon uses exactly `more than one ':' present in owner string '<value>'. See 'fd --help'.` after the usual `invalid value '<value>' for '--owner <user:group>': ` prefix.

## Spec 16

Ordinary default output is the discovered path relative to the logical working directory, without `./`; directory results have a trailing slash. Long-listing output is the exception described in Spec 19. Relative explicit roots remain visible, while absolute roots yield absolute output. `--absolute-path`/`-a` resolves every displayed path to a canonical absolute path; in particular, if the process cwd itself was reached through a symlink, the real target path is printed rather than the symlink spelling. `--relative-path` reverses it. `--full-path`/`-p` changes the string against which all patterns match to the full absolute path but does not by itself force absolute display.

A pattern containing a path separator that exactly denotes an existing directory is treated as a likely mistaken root and exits 1. The error says the pattern contains a path-separation character and will not lead to results, and suggests both `fd . '<directory>'` and `fd --full-path '<directory>'`. If such a pattern does not denote an existing directory it is allowed. Absolute paths and symlink roots must remain normalized without duplicated separators or components.

## Spec 17

`--format <fmt>` replaces ordinary path output with one line per result produced from a template. Recognized substitutions are `{}` = displayed path; `{/}` = basename; `{//}` = displayed parent directory (`.` for a root-level entry); `{.}` = displayed path with only its final extension removed; and `{/.}` = basename with only its final extension removed. Extensionless names remain unchanged. Dotted directory names are treated the same as dotted file names for `{.}` and `{/.}`: a directory `dir.name` produces `dir` for both placeholders. For `.hidden`, the leading dot is not treated as an extension; for `archive.tar.gz`, only `.gz` is removed. Directory trailing separators are omitted inside placeholders.

Placeholders may repeat and interleave with arbitrary text. Unknown brace expressions such as `{invalid}` are literal. `{{` becomes literal `{` and `}}` becomes literal `}`; escaping is scanned left-to-right and must handle adjacent and nested-looking sequences. A recognized placeholder immediately followed by an escaped close brace is itself preserved literally. These template-to-output mappings are exact: `{}}}}` → `{}}`; `{/}}}` → `{/}}`; `{//}}}` → `{//}}`; `{.}}}` → `{.}}`; `{/.}}}` → `{/.}}`; `before-{}}}after` → `before-{}}after`; `{/}}}-{//}}}` → `{/}}-{//}}`; `}}}}` → `}}`; `{{{{` → `{{`; `{}}}{{}` → `{}}{}`; and `text{}}}more` → `text{}}more`. Other representative results are: `{{}}{}{{}}` with `file1.txt` becomes `{}file1.txt{}`; `{{prefix}} {}` becomes `{prefix} file1.txt`; and `path={} name={/} parent={//} noext={.} base={/.}` on `dir/file.txt` becomes `path=dir/file.txt name=file.txt parent=dir noext=dir/file base=file`. Using `--format` suppresses SGR color styling even if color is forced, but OSC 8 hyperlink mode wraps the entire formatted visible record.

## Spec 18

`--path-separator <string>` replaces every filesystem separator in visible paths and in path-bearing placeholders (`{}`, `{.}`, `{//}`), but not in basenames. The replacement may contain multiple characters. A directory retains one trailing replacement string. Absolute-path leading `/` is replaced too. Hyperlink URL paths always retain `/` regardless of the visible separator.

`--print0`/`-0` terminates every ordinarily printed result with NUL rather than newline and ends with a final NUL. The prefix-adding modes are `-0`, `-l`, `-x`, and `-X`: `-0` and `-l` normally add `./` to relative displayed paths, while `-x` and `-X` normally add it to the `{}` and `{//}` action substitutions, preventing dash-prefixed names from becoming command options. An active hyperlink alone does not add this prefix. The action substitution `{.}` is an exception and never receives the automatic prefix. `--strip-cwd-prefix=auto` uses those defaults; `--strip-cwd-prefix=always` (or the option with no value) removes `./`; `--strip-cwd-prefix=never` forces `./` even during ordinary printing, but still does not prefix `{.}`. The prefix is also expressed through a custom separator (for example `.#dir#file`). Using `--strip-cwd-prefix` with positional root paths is an argument conflict.

When `-0` and per-result execution are combined, child stdout passes through unchanged and is not made into one NUL-terminated record per command. The executable writes its own NUL markers separately. In a directory containing only `a` and `b`, the invocation `executable '^[ab]$' -0 --threads=1 -x /usr/bin/printf '%s' '{}'` produces `./b./a\0\0`: both child payloads are adjacent and both NUL markers follow them.

## Spec 19

`--color <auto|always|never>`/`-c` controls ANSI styling. `never` emits no ESC byte. `auto` emits no color when stdout is a pipe/non-TTY. `always` enables ANSI SGR styling for file types that have a style in `LS_COLORS` or fd's defaults, with a reset around each styled portion; it does not invent a style for an unconfigured type. In particular, with both `NO_COLOR` and `LS_COLORS` absent, a lone ordinary file is printed as the unstyled bytes `file\n` even under `--color always`. With `LS_COLORS=fi=31`, that file is wrapped in the configured SGR style and reset. An explicit `--color always` takes precedence over `NO_COLOR`: with `NO_COLOR=1` and `LS_COLORS=fi=31`, `alpha.txt` is exactly `ESC [ 31 m alpha.txt ESC [ 0 m LF` on stdout.

`--list-details`/`-l` emits deterministic, lexicographically sorted, `ls -l`-style records: file-type/permission bits, link count, owner, group, byte size, date/time, and path; symlinks append ` -> target`. Relative path fields rooted at the current directory gain `./`, including a dangling-link field such as `./bad -> missing`. Unlike ordinary directory output, a directory's long-listing path field has no trailing separator, as in `./d`. For a recently modified entry, the timestamp occupies three whitespace-separated fields: abbreviated English month, day of month, and hour-and-minute time. Consequently a regular-file record has at least nine whitespace-separated fields including its path. It works for files, directories, and dangling links. It conflicts with `--absolute-path` and with `--format`, producing a nonzero argument error containing `cannot be used with`.

## Spec 20

`--hyperlink[=<auto|always|never>]` wraps each printed path separately in an OSC 8 hyperlink. Its default mode is `never`; supplying the flag without a value selects `auto`. `never` emits no OSC sequence. `auto` hyperlinks exactly when color is enabled, so `--hyperlink=auto --color=always` enables it and `--color=never` disables it. Hyperlinks do nothing for `--exec` and `--exec-batch`.

The wrapper is `ESC ] 8 ; ; file://<hostname><absolute-path> ESC \\ <visible-text> ESC ] 8 ; ; ESC \\`. The URL is absolute and uses `/`; it may use an empty hostname (`file:///...`) or the current hostname. Encode the UTF-8 bytes of every character except ASCII alphanumerics and `/ : - . _ ~` using uppercase `%HH`. Thus space, `#`, `?`, `%`, `$`, `*`, `é`, and `😃` become `%20`, `%23`, `%3F`, `%25`, `%24`, `%2A`, `%C3%A9`, and `%F0%9F%98%83`. Visible text stays unencoded and obeys path-separator, absolute-path, format, color, newline/NUL rules. Hyperlinking by itself leaves default relative visible text without a `./` prefix. Each record has its own opener and closer.

## Spec 21

`--exec <cmd>...`/`-x` executes the given program once per final result, potentially in parallel. It performs no shell word splitting: every supplied command word is one argv item and a filename containing spaces stays one argument. If no real placeholder occurs anywhere, append an implicit `{}` argument. Substitute every occurrence of `{}`, `{/}`, `{//}`, `{.}`, and `{/.}` using the same meanings as formatting. The action-mode `./` safety prefix applies to relative `{}` and `{//}` values, but not to `{.}`, `{/}`, or `{/.}`. Thus `archive.tar.gz -x echo '{.}'` passes `archive.tar`, while the same result substituted through `{}` normally passes `./archive.tar.gz`. Escaped `{{` and `}}` become literal braces and do not count as placeholders. Multiple placeholders and placeholders embedded within literal argument text are allowed. A standalone `;` terminates this command specification and returns to option parsing, allowing another `--exec` or `--exec-batch`; every configured command is run for the applicable result(s), in declaration order.

External stdout/stderr pass through. A missing command is an argument error. If there are no results, do not launch the command and exit 0. If a command is not found, write an error containing `Command not found` and exit 1. If any launched command fails, ultimately exit 1; other already scheduled results may still run. `--threads=1` guarantees sequential execution. Search filters, following, path style, separator, and placeholders all apply before launching.

## Spec 22

`--exec-batch <cmd>...`/`-X` runs the program once with all result substitutions occupying one argv position per result at the placeholder location. Placeholder meanings and safety-prefix exceptions are the same as in Spec 21; in particular, `{.}` values do not gain `./`. With no placeholder, append all `{}` values. A placeholder may appear before or after fixed command arguments, preserving those fixed arguments. Exactly one real placeholder occurrence is permitted in the complete batch command. More than one exits 2 with `Only one placeholder allowed for batch commands`; a placeholder in argv[0] exits 2 with `First argument of exec-batch is expected to be a fixed executable`. As in per-result mode, a standalone `;` ends the batch command and permits another `-x`/`-X` command specification.

`--batch-size <n>` limits each invocation to at most `n` result arguments and makes as many invocations as required; zero means unlimited. Filesystem-error items are excluded before forming/counting batches. An empty result set runs no command. Batch command failure makes the overall status nonzero. Argument order within a batch is unspecified.

## Spec 23

`--max-results <count>` stops after at most that many output results; `-1` is the alias for a count of one. A count of zero means unlimited. Negative and nonnumeric counts are exit-2 argument errors. Result limiting is incompatible with `--exec`, including `--max-results=0`; report a `cannot be used with` conflict. `-1` likewise conflicts with exec.

`--quiet`/`-q` and `--has-results` are equivalent: emit nothing, stop once eligibility is known, return 0 if a match exists and 1 otherwise. `--threads <positive-int>`/`-j` selects search/execution concurrency without changing the result set; zero or nonnumeric values are argument errors. `--max-buffer-time <nonnegative-milliseconds>` is accepted and does not change results; zero is valid, nonnumeric values are errors.

## Spec 24

Argument-parser failures exit 2 and write to stderr. Unknown options report `unexpected argument '<arg>'` and a tip explaining `to pass '<arg>' as a value`; the output includes a `Usage:` line. Missing values specifically name the canonical operand, for example `a value is required for '--max-depth <depth>'`, `--max-results <count>`, `--format <fmt>`, `--ignore-file <path>`, `--search-path <search-path>`, or `--exec <cmd>...`. Choice errors for color, hyperlink, and type contain `invalid value`. Numeric options reject nonnumbers, and `--threads 0` additionally says `number would be zero for non-zero type`.

Search/validation failures generally exit 1 and prefix domain errors with `[fd error]:`. Help/version ignore invalid options following them. Error messages go only to stderr. Unless quiet mode or an explicit command is active, eligible paths go only to stdout. A deleted current directory is an exit-1 error with exactly `[fd error]: Could not retrieve current directory (has it been deleted?).\n`.

## Spec 25

Filesystem metadata/read errors are silently skipped by default. `--show-errors` prints each one on stderr with an `[fd error]:` prefix while continuing to traverse and process other entries; such traversal errors alone do not make an otherwise successful search or exec return failure. This applies consistently under one or many threads and in both exec modes. Error-producing entries are never handed to commands.

Filenames are opaque filesystem names for traversal and argv passing. Valid UTF-8 names—including spaces, punctuation, CJK, Greek, composed accents, emoji, and embedded newlines—must be found without crashing or being split into command arguments. Newline output can naturally span lines; NUL mode remains unambiguous. The executable must complete wide/deep tests within the harness timeout and avoid recursion-stack failure.

## Spec 26

These diagnostics are byte-exact, including final newlines. Regex parse errors use the shown pattern/caret/reason followed by the same two-sentence note; substitute the actual pattern and appropriate reason/caret position:

```text
[fd error]: regex parse error:
    [invalid
    ^
error: unclosed character class

Note: You can use the '--fixed-strings' option to search for a literal string instead of a regular expression. Alternatively, you can also use the '--glob' option to match on a glob pattern.
```

### Exact Bash completion payload

`--gen-completions bash` exits 0 with empty stderr and stdout byte-for-byte equal to the following script, including its final newline:

```bash
_executable() {
    local i cur prev opts cmd
    COMPREPLY=()
    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
        cur="$2"
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
    fi
    prev="$3"
    cmd=""
    opts=""

    for i in "${COMP_WORDS[@]:0:COMP_CWORD}"
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="executable"
                ;;
            *)
                ;;
        esac
    done

    case "${cmd}" in
        executable)
            opts="-H -I -u -s -i -g -F -a -l -L -p -0 -d -E -t -e -S -o -x -X -c -j -1 -q -C -h -V --hidden --no-hidden --no-ignore --ignore --no-ignore-vcs --ignore-vcs --no-require-git --require-git --no-ignore-parent --no-global-ignore-file --unrestricted --case-sensitive --ignore-case --glob --regex --fixed-strings --and --absolute-path --relative-path --list-details --follow --no-follow --full-path --print0 --max-depth --min-depth --exact-depth --exclude --prune --type --extension --size --changed-within --changed-before --owner --format --exec --exec-batch --batch-size --ignore-file --color --hyperlink --ignore-contain --threads --max-buffer-time --max-results --quiet --show-errors --base-directory --path-separator --search-path --strip-cwd-prefix --one-file-system --gen-completions --help --version [pattern] [path]..."
            if [[ ${cur} == -* || ${COMP_CWORD} -eq 1 ]] ; then
                COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
                return 0
            fi
            case "${prev}" in
                --and)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --max-depth)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -d)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --min-depth)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --exact-depth)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --exclude)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -E)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --type)
                    COMPREPLY=($(compgen -W "file directory symlink block-device char-device executable empty socket pipe" -- "${cur}"))
                    return 0
                    ;;
                -t)
                    COMPREPLY=($(compgen -W "file directory symlink block-device char-device executable empty socket pipe" -- "${cur}"))
                    return 0
                    ;;
                --extension)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -e)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --size)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -S)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --changed-within)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --changed-before)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --owner)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -o)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --format)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --exec)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -x)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --exec-batch)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -X)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --batch-size)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --ignore-file)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --color)
                    COMPREPLY=($(compgen -W "auto always never" -- "${cur}"))
                    return 0
                    ;;
                -c)
                    COMPREPLY=($(compgen -W "auto always never" -- "${cur}"))
                    return 0
                    ;;
                --hyperlink)
                    COMPREPLY=($(compgen -W "auto always never" -- "${cur}"))
                    return 0
                    ;;
                --ignore-contain)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --threads)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -j)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --max-buffer-time)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --max-results)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --base-directory)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                -C)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --path-separator)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --search-path)
                    COMPREPLY=($(compgen -f "${cur}"))
                    return 0
                    ;;
                --strip-cwd-prefix)
                    COMPREPLY=($(compgen -W "auto always never" -- "${cur}"))
                    return 0
                    ;;
                --gen-completions)
                    COMPREPLY=($(compgen -W "bash elvish fish powershell zsh" -- "${cur}"))
                    return 0
                    ;;
                *)
                    COMPREPLY=()
                    ;;
            esac
            COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
            return 0
            ;;
    esac
}

if [[ "${BASH_VERSINFO[0]}" -eq 4 && "${BASH_VERSINFO[1]}" -ge 4 || "${BASH_VERSINFO[0]}" -gt 4 ]]; then
    complete -F _executable -o nosort -o bashdefault -o default executable
else
    complete -F _executable -o bashdefault -o default executable
fi
```


For `(unclosed`, the reason is `unclosed group`; for `*invalid`, it is `repetition operator missing expression`. The exact invalid-glob line for `[invalid` is:

```text
[fd error]: error parsing glob '[invalid': unclosed character class; missing ']'
```

For `file*.{txt`, use `unclosed alternate group; missing '}' (maybe escape '{' with '[{]'?)`. Invalid size values use:

```text
error: invalid value '<value>' for '--size <size>': '<value>' is not a valid size constraint. See 'fd --help'.

For more information, try '--help'.
```

Invalid time values use exactly `[fd error]: '<value>' is not a valid date or duration. See 'fd --help'.\n`. The exact zero-thread error is `error: invalid value '0' for '--threads <num>': number would be zero for non-zero type\n\nFor more information, try '--help'.\n`. The exact invalid-type error is:

```text
error: invalid value 'invalid' for '--type <filetype>'
  [possible values: file, directory, symlink, block-device, char-device, executable, empty, socket, pipe]

For more information, try '--help'.
```

`--gen-completions` without a shell argument and without a usable `SHELL` environment variable exits 1 with exactly `[fd error]: Unable to get shell from environment\n`.

## Spec 27

The precise option/alias surface, including options whose detailed behavior is specified above, is: `-H/--hidden`, `--no-hidden`, `-I/--no-ignore`, `--ignore`, `--no-ignore-vcs`, `--ignore-vcs`, `--no-require-git`, `--require-git`, `--no-ignore-parent`, `--no-global-ignore-file`, `-u/--unrestricted`, `-s/--case-sensitive`, `-i/--ignore-case`, `-g/--glob`, `--regex`, `-F/--fixed-strings`, `--and`, `-a/--absolute-path`, `--relative-path`, `-l/--list-details`, `-L/--follow`, `--no-follow`, `-p/--full-path`, `-0/--print0`, `-d/--max-depth`, `--min-depth`, `--exact-depth`, `-E/--exclude`, `--prune`, `-t/--type`, `-e/--extension`, `-S/--size`, all time aliases from Spec 14, `-o/--owner`, `--format`, `-x/--exec`, `-X/--exec-batch`, `--batch-size`, `--ignore-file`, `-c/--color`, `--hyperlink`, `--ignore-contain`, `-j/--threads`, `--max-buffer-time`, `--max-results`, `-1`, `-q/--quiet`, `--has-results`, `--show-errors`, `-C/--base-directory`, `--path-separator`, `--search-path`, `--strip-cwd-prefix`, `--one-file-system`/`--mount`/`--xdev`, `--gen-completions`, `-h/--help`, and `-V/--version`.

All feature interactions use one shared stream of eligible entries: name modes affect all `--and` patterns; ignore/exclude/depth determine traversal; type, extension, size, time, and owner narrow entries; rendering then applies absolute/relative/prefix/separator/format/color/hyperlink/NUL settings; finally quiet, ordinary printing, per-entry exec, or batch exec consumes that stream.

## Spec 28

For `--help`, stdout must be byte-for-byte the following UTF-8 text (including the final newline), with no ANSI escapes and no stderr:

```text
A program to find entries in your filesystem

Usage: executable [OPTIONS] [pattern] [path]...

Arguments:
  [pattern]
          the search pattern which is either a regular expression (default) or a glob pattern (if
          --glob is used). If no pattern has been specified, every entry is considered a match. If
          your pattern starts with a dash (-), make sure to pass '--' first, or it will be
          considered as a flag (fd -- '-foo').

  [path]...
          The directory where the filesystem search is rooted (optional). If omitted, search the
          current working directory.

Options:
  -H, --hidden
          Include hidden directories and files in the search results (default: hidden files and
          directories are skipped). Files and directories are considered to be hidden if their
          name starts with a `.` sign (dot). Any files or directories that are ignored due to the
          rules described by --no-ignore are still ignored unless otherwise specified. The flag
          can be overridden with --no-hidden.

  -I, --no-ignore
          Show search results from files and directories that would otherwise be ignored by
          '.gitignore', '.ignore', '.fdignore', or the global ignore file, The flag can be
          overridden with --ignore.

      --no-ignore-vcs
          Show search results from files and directories that would otherwise be ignored by
          '.gitignore' files. The flag can be overridden with --ignore-vcs.

      --no-require-git
          Do not require a git repository to respect gitignores. By default, fd will only respect
          global gitignore rules, .gitignore rules, and local exclude rules if fd detects that you
          are searching inside a git repository. This flag allows you to relax this restriction
          such that fd will respect all git related ignore rules regardless of whether you're
          searching in a git repository or not.
          
          This flag can be disabled with --require-git.

      --no-ignore-parent
          Show search results from files and directories that would otherwise be ignored by
          '.gitignore', '.ignore', or '.fdignore' files in parent directories.

  -u, --unrestricted...
          Perform an unrestricted search, including ignored and hidden files. This is an alias for
          '--no-ignore --hidden'.

  -s, --case-sensitive
          Perform a case-sensitive search. By default, fd uses case-insensitive searches, unless
          the pattern contains an uppercase character (smart case).

  -i, --ignore-case
          Perform a case-insensitive search. By default, fd uses case-insensitive searches, unless
          the pattern contains an uppercase character (smart case).

  -g, --glob
          Perform a glob-based search instead of a regular expression search.

      --regex
          Perform a regular-expression based search (default). This can be used to override
          --glob.

  -F, --fixed-strings
          Treat the pattern as a literal string instead of a regular expression. Note that this
          also performs substring comparison. If you want to match on an exact filename, consider
          using '--glob'.

      --and <pattern>
          Add additional required search patterns, all of which must be matched. Multiple
          additional patterns can be specified. The patterns are regular expressions, unless
          '--glob' or '--fixed-strings' is used.

  -a, --absolute-path
          Shows the full path starting from the root as opposed to relative paths. The flag can be
          overridden with --relative-path.

  -l, --list-details
          Use a detailed listing format like 'ls -l'. This is basically an alias for '--exec-batch
          ls -l' with some additional 'ls' options. This can be used to see more metadata, to show
          symlink targets and to achieve a deterministic sort order.

  -L, --follow
          By default, fd does not descend into symlinked directories. Using this flag, symbolic
          links are also traversed. Flag can be overridden with --no-follow.

  -p, --full-path
          By default, the search pattern is only matched against the filename (or directory name).
          Using this flag, the pattern is matched against the full (absolute) path. Example:
            fd --glob -p '**/.git/config'

  -0, --print0
          Separate search results by the null character (instead of newlines). Useful for piping
          results to 'xargs'.

  -d, --max-depth <depth>
          Limit the directory traversal to a given depth. By default, there is no limit on the
          search depth.

      --min-depth <depth>
          Only show search results starting at the given depth. See also: '--max-depth' and
          '--exact-depth'

      --exact-depth <depth>
          Only show search results at the exact given depth. This is an alias for '--min-depth
          <depth> --max-depth <depth>'.

  -E, --exclude <pattern>
          Exclude files/directories that match the given glob pattern. This overrides any other
          ignore logic. Multiple exclude patterns can be specified.
          
          Examples: 
            --exclude '*.pyc' 
            --exclude node_modules

      --prune
          Do not traverse into directories that match the search criteria. If you want to exclude
          specific directories, use the '--exclude=…' option.

  -t, --type <filetype>
          Filter the search by type: 
            'f' or 'file':         regular files 
            'd' or 'dir' or 'directory':    directories 
            'l' or 'symlink':      symbolic links 
            's' or 'socket':       socket 
            'p' or 'pipe':         named pipe (FIFO) 
            'b' or 'block-device': block device 
            'c' or 'char-device':  character device 
          
            'x' or 'executable':   executables 
            'e' or 'empty':        empty files or directories
          
          This option can be specified more than once to include multiple file types. Searching
          for '--type file --type symlink' will show both regular files as well as symlinks. Note
          that the 'executable' and 'empty' filters work differently: '--type executable' implies
          '--type file' by default. And '--type empty' searches for empty files and directories,
          unless either '--type file' or '--type directory' is specified in addition.
          
          Examples: 
            - Only search for files: 
                fd --type file … 
                fd -tf … 
            - Find both files and symlinks 
                fd --type file --type symlink … 
                fd -tf -tl … 
            - Find executable files: 
                fd --type executable 
                fd -tx 
            - Find empty files: 
                fd --type empty --type file 
                fd -te -tf 
            - Find empty directories: 
                fd --type empty --type directory 
                fd -te -td

  -e, --extension <ext>
          (Additionally) filter search results by their file extension. Multiple allowable file
          extensions can be specified.
          
          If you want to search for files without extension, you can use the regex '^[^.]+$' as a
          normal search pattern.

  -S, --size <size>
          Limit results based on the size of files using the format <+-><NUM><UNIT>.
             '+': file size must be greater than or equal to this
             '-': file size must be less than or equal to this
          
          If neither '+' nor '-' is specified, file size must be exactly equal to this.
             'NUM':  The numeric size (e.g. 500)
             'UNIT': The units for NUM. They are not case-sensitive.
          Allowed unit values:
              'b':  bytes
              'k':  kilobytes (base ten, 10^3 = 1000 bytes)
              'm':  megabytes
              'g':  gigabytes
              't':  terabytes
              'ki': kibibytes (base two, 2^10 = 1024 bytes)
              'mi': mebibytes
              'gi': gibibytes
              'ti': tebibytes

      --changed-within <date|dur>
          Filter results based on the file modification time. Files with modification times
          greater than the argument are returned. The argument can be provided as a specific point
          in time (YYYY-MM-DD HH:MM:SS or @timestamp) or as a duration (10h, 1d, 35min). If the
          time is not specified, it defaults to 00:00:00. '--change-newer-than', '--newer', or
          '--changed-after' can be used as aliases.
          
          Examples: 
              --changed-within 2weeks 
              --change-newer-than '2018-10-27 10:00:00' 
              --newer 2018-10-27 
              --changed-after 1day

      --changed-before <date|dur>
          Filter results based on the file modification time. Files with modification times less
          than the argument are returned. The argument can be provided as a specific point in time
          (YYYY-MM-DD HH:MM:SS or @timestamp) or as a duration (10h, 1d, 35min).
          '--change-older-than' or '--older' can be used as aliases.
          
          Examples: 
              --changed-before '2018-10-27 10:00:00' 
              --change-older-than 2weeks 
              --older 2018-10-27

  -o, --owner <user:group>
          Filter files by their user and/or group. Format: [(user|uid)][:(group|gid)]. Either side
          is optional. Precede either side with a '!' to exclude files instead.
          
          Examples: 
              --owner john 
              --owner :students 
              --owner '!john:students'

      --format <fmt>
          Print results according to template

  -x, --exec <cmd>...
          Execute a command for each search result in parallel (use --threads=1 for sequential
          command execution). There is no guarantee of the order commands are executed in, and the
          order should not be depended upon. All positional arguments following --exec are
          considered to be arguments to the command - not to fd. It is therefore recommended to
          place the '-x'/'--exec' option last.
          The following placeholders are substituted before the command is executed:
            '{}':   path (of the current search result)
            '{/}':  basename
            '{//}': parent directory
            '{.}':  path without file extension
            '{/.}': basename without file extension
            '{{':   literal '{' (for escaping)
            '}}':   literal '}' (for escaping)
          
          If no placeholder is present, an implicit "{}" at the end is assumed.
          
          Examples:
          
            - find all *.zip files and unzip them:
          
                fd -e zip -x unzip
          
            - find *.h and *.cpp files and run "clang-format -i .." for each of them:
          
                fd -e h -e cpp -x clang-format -i
          
            - Convert all *.jpg files to *.png files:
          
                fd -e jpg -x convert {} {.}.png

  -X, --exec-batch <cmd>...
          Execute the given command once, with all search results as arguments.
          The order of the arguments is non-deterministic, and should not be relied upon.
          One of the following placeholders is substituted before the command is executed:
            '{}':   path (of all search results)
            '{/}':  basename
            '{//}': parent directory
            '{.}':  path without file extension
            '{/.}': basename without file extension
            '{{':   literal '{' (for escaping)
            '}}':   literal '}' (for escaping)
          
          If no placeholder is present, an implicit "{}" at the end is assumed.
          
          Examples:
          
            - Find all test_*.py files and open them in your favorite editor:
          
                fd -g 'test_*.py' -X vim
          
            - Find all *.rs files and count the lines with "wc -l ...":
          
                fd -e rs -X wc -l

      --batch-size <size>
          Maximum number of arguments to pass to the command given with -X. If the number of
          results is greater than the given size, the command given with -X is run again with
          remaining arguments. A batch size of zero means there is no limit (default), but note
          that batching might still happen due to OS restrictions on the maximum length of command
          lines.
          
          [default: 0]

      --ignore-file <path>
          Add a custom ignore-file in '.gitignore' format. These files have a low precedence.

  -c, --color <when>
          Declare when to use color for the pattern match output

          Possible values:
          - auto:   show colors if the output goes to an interactive console (default)
          - always: always use colorized output
          - never:  do not use colorized output
          
          [default: auto]

      --hyperlink[=<when>]
          Add a terminal hyperlink to a file:// url for each path in the output.
          
          Auto mode  is used if no argument is given to this option.
          
          This doesn't do anything for --exec and --exec-batch.

          Possible values:
          - auto:   Use hyperlinks only if color is enabled
          - always: Always use hyperlinks when printing file paths
          - never:  Never use hyperlinks
          
          [default: never]

      --ignore-contain <name>
          Ignore directories containing the named entry

  -j, --threads <num>
          Set number of threads to use for searching & executing (default: number of available CPU
          cores)

      --max-results <count>
          Limit the number of search results to 'count' and quit immediately.

  -1
          Limit the search to a single result and quit immediately. This is an alias for
          '--max-results=1'.

  -q, --quiet
          When the flag is present, the program does not print anything and will return with an
          exit code of 0 if there is at least one match. Otherwise, the exit code will be 1.
          '--has-results' can be used as an alias.

      --show-errors
          Enable the display of filesystem errors for situations such as insufficient permissions
          or dead symlinks.

  -C, --base-directory <path>
          Change the current working directory of fd to the provided path. This means that search
          results will be shown with respect to the given base path. Note that relative paths
          which are passed to fd via the positional <path> argument or the '--search-path' option
          will also be resolved relative to this directory.

      --path-separator <separator>
          Set the path separator to use when printing file paths. The default is the OS-specific
          separator ('/' on Unix, '\' on Windows).

      --search-path <search-path>
          Provide paths to search as an alternative to the positional <path> argument. Changes the
          usage to `fd [OPTIONS] --search-path <path> --search-path <path2> [<pattern>]`

      --strip-cwd-prefix[=<when>]
          By default, relative paths are prefixed with './' when -x/--exec, -X/--exec-batch, or
          -0/--print0 are given, to reduce the risk of a path starting with '-' being treated as a
          command line option. Use this flag to change this behavior. If this flag is used without
          a value, it is equivalent to passing "always".

          Possible values:
          - auto:   Use the default behavior
          - always: Always strip the ./ at the beginning of paths
          - never:  Never strip the ./

      --one-file-system
          By default, fd will traverse the file system tree as far as other options dictate. With
          this flag, fd ensures that it does not descend into a different file system than the one
          it started in. Comparable to the -mount or -xdev filters of find(1).

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version

Bugs can be reported on GitHub: https://github.com/sharkdp/fd/issues
```

## Spec 29

For `-h`, stdout must be byte-for-byte the following UTF-8 text (including the final newline), with no ANSI escapes and no stderr:

```text
A program to find entries in your filesystem

Usage: executable [OPTIONS] [pattern] [path]...

Arguments:
  [pattern]  the search pattern (a regular expression, unless '--glob' is used; optional)
  [path]...  the root directories for the filesystem search (optional)

Options:
  -H, --hidden                     Search hidden files and directories
  -I, --no-ignore                  Do not respect .(git|fd)ignore files
  -s, --case-sensitive             Case-sensitive search (default: smart case)
  -i, --ignore-case                Case-insensitive search (default: smart case)
  -g, --glob                       Glob-based search (default: regular expression)
  -a, --absolute-path              Show absolute instead of relative paths
  -l, --list-details               Use a long listing format with file metadata
  -L, --follow                     Follow symbolic links
  -p, --full-path                  Search full abs. path (default: filename only)
  -d, --max-depth <depth>          Set maximum search depth (default: none)
  -E, --exclude <pattern>          Exclude entries that match the given glob pattern
  -t, --type <filetype>            Filter by type: file (f), directory (d/dir), symlink (l),
                                   executable (x), empty (e), socket (s), pipe (p), char-device
                                   (c), block-device (b)
  -e, --extension <ext>            Filter by file extension
  -S, --size <size>                Limit results based on the size of files
      --changed-within <date|dur>  Filter by file modification time (newer than)
      --changed-before <date|dur>  Filter by file modification time (older than)
  -o, --owner <user:group>         Filter by owning user and/or group
      --format <fmt>               Print results according to template
  -x, --exec <cmd>...              Execute a command for each search result
  -X, --exec-batch <cmd>...        Execute a command with all search results at once
  -c, --color <when>               When to use colors [default: auto] [possible values: auto,
                                   always, never]
      --hyperlink[=<when>]         Add hyperlinks to output paths [default: never] [possible
                                   values: auto, always, never]
      --ignore-contain <name>      Ignore directories containing the named entry
  -h, --help                       Print help (see more with '--help')
  -V, --version                    Print version
```

## Spec 30

Completion generation is a pure information mode: it performs no filesystem search, exits 0, writes only the generated script to stdout, and supports `bash`, `zsh`, `fish`, `powershell`, and `elvish`. The byte-exact Bash payload is embedded under “Exact Bash completion payload” in Spec 26. The required beginnings of the other three completion formats are given in Spec 31. Elvish output is over 100 bytes and contains both `use builtin` and `edit:completion:arg-completer`. Each generated script names the command `executable`. The Bash, zsh, PowerShell, and Elvish scripts document `--gen-completions`, but the Fish script contains no occurrence of `--gen-completions`.

## Spec 31

For `--gen-completions zsh`, the first 30 lines (and newline following line 30) are exactly:

```zsh
#compdef executable

autoload -U is-at-least

_executable() {
    typeset -A opt_args
    typeset -a _arguments_options
    local ret=1

    if is-at-least 5.2; then
        _arguments_options=(-s -S -C)
    else
        _arguments_options=(-s -C)
    fi

    local context curcontext="$curcontext" state line
    _arguments "${_arguments_options[@]}" : \
'*--and=[Additional search patterns that need to be matched]:pattern:_default' \
'-d+[Set maximum search depth (default\: none)]:depth:_default' \
'--max-depth=[Set maximum search depth (default\: none)]:depth:_default' \
'--min-depth=[Only show search results starting at the given depth.]:depth:_default' \
'(-d --max-depth --min-depth)--exact-depth=[Only show search results at the exact given depth]:depth:_default' \
'*-E+[Exclude entries that match the given glob pattern]:pattern:_default' \
'*--exclude=[Exclude entries that match the given glob pattern]:pattern:_default' \
'*-t+[Filter by type\: file (f), directory (d/dir), symlink (l), executable (x), empty (e), socket (s), pipe (p), char-device (c), block-device (b)]:filetype:((file\:""
directory\:""
symlink\:""
block-device\:""
char-device\:""
executable\:"A file which is executable by the current effective user"
```

For `--gen-completions fish`, the first 30 lines are exactly:

```fish
complete -c executable -l and -d 'Additional search patterns that need to be matched' -r
complete -c executable -s d -l max-depth -d 'Set maximum search depth (default: none)' -r
complete -c executable -l min-depth -d 'Only show search results starting at the given depth.' -r
complete -c executable -l exact-depth -d 'Only show search results at the exact given depth' -r
complete -c executable -s E -l exclude -d 'Exclude entries that match the given glob pattern' -r
complete -c executable -s t -l type -d 'Filter by type: file (f), directory (d/dir), symlink (l), executable (x), empty (e), socket (s), pipe (p), char-device (c), block-device (b)' -r -f -a "file\t''
directory\t''
symlink\t''
block-device\t''
char-device\t''
executable\t'A file which is executable by the current effective user'
empty\t''
socket\t''
pipe\t''"
complete -c executable -s e -l extension -d 'Filter by file extension' -r
complete -c executable -s S -l size -d 'Limit results based on the size of files' -r
complete -c executable -l changed-within -d 'Filter by file modification time (newer than)' -r
complete -c executable -l changed-before -d 'Filter by file modification time (older than)' -r
complete -c executable -s o -l owner -d 'Filter by owning user and/or group' -r
complete -c executable -l format -d 'Print results according to template' -r
complete -c executable -s x -l exec -d 'Execute a command for each search result' -r
complete -c executable -s X -l exec-batch -d 'Execute a command with all search results at once' -r
complete -c executable -l batch-size -d 'Max number of arguments to run as a batch size with -X' -r
complete -c executable -l ignore-file -d 'Add a custom ignore-file in \'.gitignore\' format' -r -F
complete -c executable -s c -l color -d 'When to use colors' -r -f -a "auto\t'show colors if the output goes to an interactive console (default)'
always\t'always use colorized output'
never\t'do not use colorized output'"
complete -c executable -l hyperlink -d 'Add hyperlinks to output paths' -r -f -a "auto\t'Use hyperlinks only if color is enabled'
always\t'Always use hyperlinks when printing file paths'
never\t'Never use hyperlinks'"
```

The complete Fish script must contain more than 50 nonblank lines and use `complete -c executable` declarations. For `--gen-completions powershell`, the first 30 lines are exactly:

```powershell

using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'executable' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'executable'
        for ($i = 1; $i -lt $commandElements.Count; $i++) {
            $element = $commandElements[$i]
            if ($element -isnot [StringConstantExpressionAst] -or
                $element.StringConstantType -ne [StringConstantType]::BareWord -or
                $element.Value.StartsWith('-') -or
                $element.Value -eq $wordToComplete) {
                break
        }
        $element.Value
    }) -join ';'

    $completions = @(switch ($command) {
        'executable' {
            [CompletionResult]::new('--and', '--and', [CompletionResultType]::ParameterName, 'Additional search patterns that need to be matched')
            [CompletionResult]::new('-d', '-d', [CompletionResultType]::ParameterName, 'Set maximum search depth (default: none)')
            [CompletionResult]::new('--max-depth', '--max-depth', [CompletionResultType]::ParameterName, 'Set maximum search depth (default: none)')
            [CompletionResult]::new('--min-depth', '--min-depth', [CompletionResultType]::ParameterName, 'Only show search results starting at the given depth.')
            [CompletionResult]::new('--exact-depth', '--exact-depth', [CompletionResultType]::ParameterName, 'Only show search results at the exact given depth')
            [CompletionResult]::new('-E', '-E ', [CompletionResultType]::ParameterName, 'Exclude entries that match the given glob pattern')
            [CompletionResult]::new('--exclude', '--exclude', [CompletionResultType]::ParameterName, 'Exclude entries that match the given glob pattern')
```

The remaining PowerShell output must contain `Register-ArgumentCompleter`, `CompletionResult`, `System.Management.Automation`, and `--gen-completions`.
