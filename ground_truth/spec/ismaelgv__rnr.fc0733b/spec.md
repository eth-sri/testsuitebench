# Clarified executable specification

## Spec 1

The required artifact is one directly runnable program named exactly `executable`. It is a command-line batch-renaming tool. Tests invoke it as `executable ARGS...`, sometimes with a different current working directory, and observe its exit status, stdout, stderr, files, directories, symlinks, backup copies, and JSON dump files.

All command-line text and path strings are UTF-8. Relative paths are interpreted relative to the process current working directory, not relative to the executable or to a dump file. A path's spelling is retained for output and dump records: a relative input produces relative operation paths, while an absolute input produces absolute operation paths. Every displayed line ends in `\n`.

The interface has exactly the commands `regex`, `from-file`, `to-ascii`, and the generated help command `help`. Successful help, version, previews, and completed operations exit 0. Command-line syntax errors exit 2. Operational failures described below exit 1.

## Spec 2

`executable --help` must write the following exact bytes to stdout, write nothing to stderr, and exit 0. The blank-line placement and final newline are significant.

```text
RnR is a command-line tool to rename multiple files and directories that
supports regular expressions


Usage: executable <COMMAND>

Commands:
  regex      Rename files and directories using a regular expression
  from-file  Read operations from a dump file
  to-ascii   Replace file name UTF-8 chars with ASCII chars representation
  help       Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version
```

`-h` has the same function. `executable help` prints the main help, and `executable help regex`, `help from-file`, and `help to-ascii` print the corresponding command help from Spec 3. A leading global `--help` takes precedence over later arguments, so `executable --help regex` prints main help. `executable help --help` is instead an error because `--help` is treated as an unrecognized name following `help`.

`executable --version` and `executable -V` print exactly `rnr 0.5.1\n` to stdout and exit 0. A global version flag before a command also takes precedence and only prints the version.

## Spec 3

The three command help screens are exact. They go to stdout, leave stderr empty, and exit 0. A help flag takes precedence over missing or stray positional arguments after that command (for example, `regex --help ignored` still succeeds).

`regex --help` and `regex -h`:

```text
Rename files and directories using a regular expression

Usage: executable regex [OPTIONS] <EXPRESSION> <REPLACEMENT> <PATH(S)>...

Arguments:
  <EXPRESSION>   Expression to match (can be a regex)
  <REPLACEMENT>  Expression replacement (use single quotes for capture groups)
  <PATH(S)>...   Target paths

Options:
  -n, --dry-run
          Only show what would be done (default mode)
  -f, --force
          Make actual changes to files
  -b, --backup
          Generate file backups before renaming
  -s, --silent
          Do not print any information
      --color <COLOR>
          Set color output mode [default: auto] [possible values: always, never, auto]
      --dump
          Force dumping operations into a file even in dry-run mode
      --dump-prefix <DUMP_PREFIX>
          Set the dump file prefix [default: rnr-]
      --no-dump
          Do not dump operations into a file
  -l, --replace-limit <LIMIT>
          Limit of replacements, all matches if set to 0
  -t, --replace-transform <REPLACE_TRANSFORM>
          Apply a transformation to replacements including captured groups [possible values: upper, lower, ascii]
  -D, --include-dirs
          Rename matching directories
  -r, --recursive
          Recursive mode
  -d, --max-depth <LEVEL>
          Set max depth in recursive mode
  -x, --hidden
          Include hidden files and directories
  -h, --help
          Print help
```

`from-file --help` and `from-file -h`:

```text
Read operations from a dump file

Usage: executable from-file [OPTIONS] <DUMPFILE>

Arguments:
  <DUMPFILE>  

Options:
  -n, --dry-run                    Only show what would be done (default mode)
  -f, --force                      Make actual changes to files
  -b, --backup                     Generate file backups before renaming
  -s, --silent                     Do not print any information
      --color <COLOR>              Set color output mode [default: auto] [possible values: always, never, auto]
      --dump                       Force dumping operations into a file even in dry-run mode
      --dump-prefix <DUMP_PREFIX>  Set the dump file prefix [default: rnr-]
      --no-dump                    Do not dump operations into a file
  -u, --undo                       Undo the operations from the dump file
  -h, --help                       Print help
```

`to-ascii --help` and `to-ascii -h`:

```text
Replace file name UTF-8 chars with ASCII chars representation

Usage: executable to-ascii [OPTIONS] <PATH(S)>...

Arguments:
  <PATH(S)>...  Target paths

Options:
  -n, --dry-run                    Only show what would be done (default mode)
  -f, --force                      Make actual changes to files
  -b, --backup                     Generate file backups before renaming
  -s, --silent                     Do not print any information
      --color <COLOR>              Set color output mode [default: auto] [possible values: always, never, auto]
      --dump                       Force dumping operations into a file even in dry-run mode
      --dump-prefix <DUMP_PREFIX>  Set the dump file prefix [default: rnr-]
      --no-dump                    Do not dump operations into a file
  -D, --include-dirs               Rename matching directories
  -r, --recursive                  Recursive mode
  -d, --max-depth <LEVEL>          Set max depth in recursive mode
  -x, --hidden                     Include hidden files and directories
  -h, --help                       Print help
```

## Spec 4

The command syntaxes are:

```text
executable regex [OPTIONS] EXPRESSION REPLACEMENT PATH...
executable to-ascii [OPTIONS] PATH...
executable from-file [OPTIONS] DUMPFILE
```

Options may be interspersed with or placed after positionals. Long value options accept both `--option value` and `--option=value`. Short flags may be grouped, such as `-nf`. `--` ends option parsing and permits a dash-prefixed expression, replacement, or path.

All three operational commands accept the common options `-n/--dry-run`, `-f/--force`, `-b/--backup`, `-s/--silent`, `--color`, `--dump`, `--dump-prefix`, and `--no-dump`. Only `regex` accepts `-l/--replace-limit` and `-t/--replace-transform`. Only `from-file` accepts `-u/--undo`. Only `regex` and `to-ascii` accept `-D/--include-dirs`, `-r/--recursive`, `-d/--max-depth`, and `-x/--hidden`. These are command options, not global options; placing one before the command is a syntax error.

`COLOR` is exactly one of `always`, `never`, and `auto`. `REPLACE_TRANSFORM` is exactly one of `upper`, `lower`, and `ascii`. `LIMIT` and `LEVEL` are unsigned base-10 integers; negative or nonnumeric values are invalid. `--color` cannot occur twice. Dry-run and force are mutually exclusive, including grouped `-nf`. `--dump` and `--no-dump` are mutually exclusive. `--max-depth` and `--hidden` require `--recursive`.

## Spec 5

With no explicit mode, every operational command is a dry run. `-n/--dry-run` selects that same mode. On successful completion, dry-run mode computes and validates a plan, prints `This is a DRY-RUN\n` followed by planned operations, but performs no rename and creates no backup. It creates no JSON dump by default; `--dump` explicitly enables a dump of the preview. If creation of an explicitly requested dump fails, the exception in Spec 18 governs which of that output has already been written.

`-f/--force` executes the operations. Force output omits the dry-run header. Force mode creates a JSON dump by default, even if there are zero matching operations. `--no-dump` suppresses that automatic dump without suppressing renames. `--dump` requests a dump explicitly. A successful no-op force run has empty stdout unless another informational event occurs.

`-s/--silent` suppresses the dry-run header, every operation line, every backup-information line, and errors produced while planning or executing operations, without changing planning, execution, backup, dump behavior, or failure status. In particular, a silent existing-target conflict from Spec 14 and a silent filesystem rename failure from Spec 16 both exit 1 with empty stdout and stderr. It also suppresses dump open, parse, and creation errors. Command-line parsing diagnostics and the bad-expression diagnostic in Spec 23 are not suppressed. A successful silent run has empty stdout and stderr.

## Spec 6

For `regex` and `to-ascii`, each supplied path is inspected. Existing regular files and symlinks (including broken or circular symlinks) are eligible. A symlink is treated as a directory entry in its own right; traversal and renaming must not dereference or follow it. Renaming a symlink preserves its link target and leaves the target itself unchanged.

Nonexistent paths are silently ignored. Thus a dry run over only nonexistent paths prints just its header, while a force run over only nonexistent paths has empty normal output. Deduplication is by the operand's retained path spelling, not by filesystem identity or normalized path. Repeating the identical operand spelling such as `old.txt old.txt` produces one operation, but lexical aliases are distinct: `old.txt ./old.txt` produces both `./old.txt -> ./new.txt` and `old.txt -> new.txt`, in that order. A regular path and a distinct broken or circular symlink are not considered duplicates. Handling circular symlinks must terminate promptly.

Only the final filename component of each eligible path is transformed. Parent-directory text is never matched or transliterated merely because it occurs in an operand's path. The target remains beside the source and has the same parent. Whitespace, quotes, brackets, tabs, multiple periods, and other ordinary filename characters are preserved unless the selected transformation changes them.

## Spec 7

Without `--recursive`, only the explicitly named entries are considered; a named directory is never descended. With `-r/--recursive`, each named directory is walked to unlimited depth unless `--max-depth` is set. Multiple root paths are all walked.

Depth is the walk depth with the supplied root at depth 0 and its immediate children at depth 1. Only entries whose walk depth is at most `LEVEL` are visited. Consequently level 0 visits no children, level 1 processes only files directly inside the root, level 2 also processes files in immediate subdirectories, and so on. For example, with level 5 the root's direct files and files in four nested directory levels are eligible. `--max-depth 0` therefore yields no file operations for a directory root.

During recursive discovery, entries whose own basename begins with `.` are excluded by default, and an excluded dot-directory's entire subtree is skipped. This exclusion does not apply to an explicitly named operand: for example, nonrecursive `regex old new .old.txt` plans `.old.txt -> .new.txt` without `--hidden`. `-x/--hidden`, used with recursive mode, includes otherwise excluded dotfiles and traverses dot-directories. Hidden status does not otherwise alter matching or output.

Recursive traversal does not follow symlinked directories. It must scale to at least 100 operations, 50 siblings, and ten nested levels without a fixed small limit.

## Spec 8

Directories are ineligible by default, whether explicitly supplied or encountered recursively. `-D/--include-dirs` makes them eligible. Thus `regex -f -D foo bar /x/foo` renames the directory to `/x/bar` but, without `-r`, does not separately rename its children. The same rule applies to `to-ascii`.

When recursive selection and `--include-dirs` are combined, files and matching directories are all planned. Children and deeper directories must be processed before an ancestor directory is renamed, so old child paths remain usable. For example, renaming `dir` to `DIR` in `parent_dir/child_dir` prints and executes:

```text
parent_dir/child_dir -> parent_dir/child_DIR
parent_dir -> parent_DIR
```

The contents move with a renamed directory. Backups are never made for directories, though eligible regular files in the same batch are backed up.

## Spec 9

`regex` compiles `EXPRESSION` as a case-sensitive, Unicode-aware regular expression and applies it to each eligible basename. It supports literal text; `.`, `^`, and `$`; character classes and ranges; `*`, `+`, `?`, and counted repetition; greedy and lazy forms; alternation; nested groups; word boundaries such as `\b`; digit and word classes such as `\d` and `\w`; numbered capture groups; and named groups written `(?P<name>...)`.

It does not support a pattern backreference such as `([a-z])\1`, nor look-ahead/look-behind such as `(?=...)`; those are bad expressions. Matching is case-sensitive unless the expression itself uses a supported regex construct to say otherwise. In particular, lowercase `test` does not match `TEST`.

An empty expression is valid and matches at the start, so replacing `""` with `prefix_` changes `test.txt` to `prefix_test.txt`. Regex matching includes the extension because it operates on the complete basename: `\.txt$` can change an extension, and an unescaped dot matches any single character.

## Spec 10

The replacement string uses regex capture expansion. `$0` denotes the complete match; `$1`, `$2`, etc. and `${1}`, `${2}`, etc. denote numbered groups; `${name}` denotes a named group. Groups may be reordered, nested, or repeated in the replacement. Examples include:

```text
test_001.txt + /test_([0-9]+)/ -> file_$1       = file_001.txt
report_2023_01.txt -> $2-$1-report              = 01-2023-report.txt
file-abc-def-ghi.txt -> ${4}.${3}.${2}.${1}     = ghi.def.abc.file.txt
file-abc-xyz.txt -> [$0] for /file-([a-z]+)/    = [file-abc]-xyz.txt
```

Only non-overlapping matches are replaced. The default replacement limit is 1, meaning only the first match in each basename. `-l N` replaces at most the first `N` matches per basename. The special value 0 means unlimited/all matches. For instance, replacing `-` by `_` in `test-aaa-bbb-ccc.txt` yields `test_aaa-bbb-ccc.txt` by default, `test_aaa_bbb-ccc.txt` at limit 2, and `test_aaa_bbb_ccc.txt` at limit 0.

An empty replacement deletes matched text. It may legally leave only an extension: replacing `test` by empty in `test.txt` yields the hidden filename `.txt`.

## Spec 11

`regex -t/--replace-transform` transforms each fully expanded replacement fragment before that fragment is inserted; it does not transform unmatched portions of the filename. This applies to both literal replacement text and expanded captures, on each replaced match, and respects the replacement limit.

- `upper` applies Unicode uppercase to the expanded replacement.
- `lower` applies Unicode lowercase to the expanded replacement.
- `ascii` applies the transliteration in Spec 12 to the expanded replacement.

For example, replacing the first `([a-z]+)` by `${1}` with `upper` changes `aa-bb-cc.txt` to `AA-bb-cc.txt`, not `AA-BB-CC.TXT`. Replacing `([a-z]+)-([a-z]+)` by `${1}_${1}_${2}` with `upper` changes `hello-world.txt` to `HELLO_HELLO_WORLD.txt`. Without a transform, Unicode and case in expanded captures and literals remain unchanged.

## Spec 12

`to-ascii` does no regex matching. It transliterates the entire final basename from Unicode into an ASCII representation, preserving already-ASCII characters. It creates an operation only when the resulting basename differs. The same transliteration is used by regex's `ascii` replacement transform.

The required conversions include accent removal and the following complete examples:

```text
café.txt                 -> cafe.txt
naïve_résumé.pdf         -> naive_resume.pdf
über.doc                 -> uber.doc
ǹön-âścîı-lower.txt      -> non-ascii-lower.txt
ǸÖN-ÂŚCÎI-UPPER.txt      -> NON-ASCII-UPPER.txt
straße.txt               -> strasse.txt
Þórr.txt                 -> Thorr.txt
æther.txt                -> aether.txt
привет.txt               -> privet.txt
файл.txt                 -> fayl.txt
日本語.doc                -> RiBenYu.doc
한글.pdf                  -> HanGeul.pdf
Ελληνικά.txt             -> Ellinika.txt
العربية.md               -> l`rbyh.md
test☕.txt                -> test:coffee:.txt
file🎉.doc                -> file:tada:.doc
with╱slash.txt           -> with_slash.txt
```

Common composed and decomposed accented Latin letters produce the same unaccented result. In particular `ï/Ï -> i/I`, `é/É -> e/E`, `ö/Ö -> o/O`, `â/Â -> a/A`, `ś/Ś -> s/S`, `î/Î -> i/I`, `ñ -> n`, and dotless `ı -> i`. Transliteration must also produce a changed ASCII name rather than fail for other Cyrillic, Chinese, Japanese, Korean, Greek, Arabic, and emoji examples. Any slash-like Unicode character whose transliteration would introduce `/` must instead produce `_`, so transliteration never turns one basename into a nested path.

## Spec 13

Planning omits entries for which the expression has no match or for which ASCII conversion does not change the basename. Such entries are neither printed nor renamed nor included as operations in a dump. A no-match batch is a successful no-op.

For a plain, nonsilent dry run that reaches normal preview output, print the header even when the plan is empty:

```text
This is a DRY-RUN
```

Subject to the dump-creation failure ordering in Spec 18, print `SOURCE -> TARGET\n` for each planned operation. In no-color mode, examples are exactly:

```text
This is a DRY-RUN
file with spaces.txt -> document with spaces.txt
subdir/test.txt -> subdir/renamed.txt
```

Force mode prints the same operation lines without the header. The path spellings remain unquoted even when they contain spaces, quotes, backslashes, Unicode, or tabs.

## Spec 14

Before executing or dumping a regex/to-ascii-generated plan, validate target safety across the entire plan.

If multiple distinct sources map to one target, fail with status 1 and do not rename or back up any source. Unless `--silent` suppresses it as specified in Spec 5, the plain diagnostic on stderr is:

```text
Error: Files will have the same name

SOURCE1->TARGET
SOURCE2->TARGET

```

There are no spaces around arrows in this diagnostic. Before constructing it, colliding operations at the same depth are ordered lexicographically by their displayed source path, independently of the command-line operand order. With three or more colliders, report the first source in that ordering paired with each later source, separated by blank lines. Thus sources `file_a`, `file_b`, and `file_c` mapping to `file` produce the `a/b` pair, a blank line, then the `a/c` pair. Likewise, `file.test.txt`, `fileAtest.txt`, and `fileBtest.txt` mapping to `doc.txt` are reported exactly as:

```text
Error: Files will have the same name

file.test.txt->doc.txt
fileAtest.txt->doc.txt

file.test.txt->doc.txt
fileBtest.txt->doc.txt

```

If a target already exists and is not itself one of the selected sources, fail with status 1 and do not modify anything. Unless `--silent` suppresses it as specified in Spec 5, the exact plain diagnostic is:

```text
Error: Conflict with existing path SOURCE -> TARGET
```

Existing regular files and existing symlinks, including broken symlinks, count as occupied targets. A target that is also a source in the same generated batch is allowed and handled as a dependency as described in Spec 15.

## Spec 15

Regex/to-ascii-generated operations must be reordered to preserve every source when targets form chains. If `a -> aa`, `aa -> aaa`, and `aaa -> aaaa`, output, dump, and execute them target-first:

```text
aaa.txt -> aaaa.txt
aa.txt -> aaa.txt
a.txt -> aa.txt
```

This must work for chains at least seven operations long, including when selected targets/sources are symlinks. Distinct contents follow their corresponding source into the final names. Backups, when requested, preserve each original source's pre-batch content.

Independent recursive operations are ordered deepest path first. This ensures nested file and directory operations precede ancestor-directory operations. Among unrelated operations at the same depth, iteration order is not semantically significant and may vary; every operation must appear exactly once.

## Spec 16

In force mode, execute a filesystem rename for every planned operation and preserve regular-file bytes and symlink identity. The source ceases to exist under its old name unless a separate chain operation later recreates that name. Long basenames near the usual 255-byte filesystem component limit must not be artificially truncated.

Generated regex/to-ascii plans never overwrite an unrelated existing target because Spec 14 rejects it. A replacement containing `/` is not rejected merely during argument parsing; it creates a nested target path. If that parent does not exist, force execution fails with status 1 and this two-line stderr form:

```text
Error: Cannot rename test.txt -> path/to/file.txt
No such file or directory (os error 2)
```

If an execution error occurs, report the failing source and target using the same `Cannot rename` form followed by the operating-system error text, except that `--silent` suppresses both lines while retaining status 1.

## Spec 17

With `-b/--backup` in force mode, immediately before renaming each eligible nondirectory source, copy its content to a sibling backup. The first candidate is the literal source path plus `.bk`. If that entry exists, try `.bk.1`, then `.bk.2`, and so on, without overwriting an old backup. For example, a preexisting `data.txt.bk` causes the new backup to be `data.txt.bk.1`.

Backups retain the source's content from before any batch renames. No backup is created in dry-run mode, for a directory, for an unchanged entry, or after plan validation has failed. A `from-file` operation backs up its current source, not a target it is about to overwrite. Undo therefore backs up the original operation's target because that path is the undo source.

Unless silent, each backup message immediately precedes its corresponding operation line:

```text
Info:  Backup created - source.txt -> source.txt.bk
source.txt -> target.txt
```

There are two spaces after `Info:`.

## Spec 18

Dumping writes a UTF-8 JSON object in the current working directory unless the prefix contains another path. The default filename is:

```text
rnr-YYYY-MM-DD_HHMMSS.json
```

The timestamp represents the current local time. `--dump-prefix PREFIX` substitutes `PREFIX` directly for `rnr-`; no punctuation is added. Thus prefix `backup` produces `backupYYYY-MM-DD_HHMMSS.json`. No uniqueness suffix is added. If the selected name already exists, it is truncated and overwritten; consequently two runs using the same prefix within one second select the same filename and the second dump replaces the first. Failure to create it exits 1 and reports `Error: Cannot create file PATH\n`.

For a nonsilent `regex` dry run with `--dump`, the dry-run header is written before the program attempts to create the dump, while planned operation lines are written only after dump creation succeeds. Consequently, if dump creation fails, stdout contains exactly `This is a DRY-RUN\n` and no operation lines, even when the plan is nonempty; the creation diagnostic goes to stderr. For example, with an existing operand `old`, expression `old`, replacement `new`, and `--dump-prefix missing/rnr-` where `missing` does not exist, the program exits 1, leaves `old` unchanged, writes only the dry-run header to stdout, and writes `Error: Cannot create file missing/rnr-YYYY-MM-DD_HHMMSS.json\n` to stderr. Silent-mode suppression remains as specified in Spec 5.

The JSON is pretty-printed with two-space indentation and has exactly this schema for generated data:

```json
{
  "date": "2026-04-11 03:05:23",
  "operations": [
    {
      "source": "file1.txt",
      "target": "renamed1.txt"
    }
  ]
}
```

`date` uses `YYYY-MM-DD HH:MM:SS`. Each operation object has exactly the two string fields `source` and `target`, using the displayed path spellings. The operations are in execution/preview order. An empty plan has an empty array. Force mode dumps automatically; dry run dumps only with `--dump`; `--no-dump` disables dumping. These rules apply to all three operational commands, so force replaying a dump normally creates a new dump of what was replayed.

## Spec 19

`from-file` opens `DUMPFILE` and parses UTF-8 JSON. The root must be an object containing a string `date` and an array `operations`. The content of the date string is not validated, so formats such as `2026/04/11 00:00:00` are accepted. Each operation must be an object containing string `source` and `target` fields. Missing fields, nulls, wrong field types, a non-array operations field, malformed/empty JSON, or a wrong root structure are parse failures. An empty operations array is valid.

Relative operation paths are interpreted against the process current directory. Absolute Unix paths remain absolute. Backslashes in a JSON path remain literal backslash characters on Unix; previewing `C:\\Users\\Test\\file.txt` prints that spelling rather than normalizing it.

In default or explicit dry-run mode, `from-file` writes `This is a DRY-RUN\n` to stdout before attempting to open, read, or parse the dump. That header therefore remains on stdout if any of those steps fails, unless `--silent` suppresses it.

If the dump cannot be opened or read, exit 1 and print exactly `Error: Cannot open/read file DUMPFILE\n` to stderr. A missing path follows this case. If an existing directory is supplied as `DUMPFILE`, it instead exits 1 and prints exactly `Error: Cannot parse JSON file DUMPFILE\n`. Malformed or empty JSON, invalid UTF-8, and every schema failure listed above also use that parse diagnostic. These failures retain the preceding dry-run header on stdout; in force mode there is no header, and in silent mode both the header and operational diagnostic are suppressed.

## Spec 20

Without `--undo`, `from-file` previews or executes the listed operations in their array order. Unlike a generated regex/to-ascii plan, this is an explicit replay: in force mode its filesystem rename is permitted to replace an already existing target. On Unix, the target's old content is removed and the source content becomes the target content. It does not apply the generated-plan collision checks or dependency reordering.

Consequently, an explicitly supplied cycle executes literally and is not transactional. For `a->b`, `b->c`, `c->a` in that order on Unix, the final surviving `a` contains the original `a` content and `b` and `c` are absent. An error partway through replay may occur after earlier operations have run.

In dry-run mode, arbitrary syntactically valid source and target strings are simply previewed; they need not exist. A 100-operation file prints one header plus 100 operation lines in array order. In force mode, failure of a listed rename uses the `Cannot rename SOURCE -> TARGET` diagnostic from Spec 16.

## Spec 21

`from-file -u/--undo` constructs the inverse by reversing the operation array and then swapping each operation's source and target. If the original list is:

```text
before1.txt -> after1.txt
before2.txt -> after2.txt
```

the undo order is:

```text
after2.txt -> before2.txt
after1.txt -> before1.txt
```

Dry-run undo only shows that inverse and leaves files untouched. Force undo executes it, preserving content, with the same replay overwrite, backup, output, and dump rules as ordinary `from-file`. A missing undo source produces, for example:

```text
Error: Cannot rename renamed2.txt -> original2.txt
No such file or directory (os error 2)
```

## Spec 22

Color is controlled by `--color`. `never` emits no ANSI escapes. `auto` emits color only when the applicable stream is a terminal; captured stdout/stderr is not a terminal, so tests using ordinary subprocess capture receive the same plain text as `never`. `always` emits ANSI even when captured. Help text itself is uncolored.

For `always`, use these exact SGR sequences:

- bold: `ESC[1m`, red: `ESC[31m`, bold red: `ESC[1;31m`, green: `ESC[32m`, dark gray: `ESC[38;5;8m`, reset: `ESC[0m`;
- render the dry-run header as bold `This is a DRY-RUN` followed by reset and newline;
- render the source path in dark gray. If it has a parent prefix, render the prefix through its final `/` as one dark-gray/reset span and the basename as a second dark-gray/reset span;
- render an unchanged target parent prefix green;
- compare source and target basenames at Unicode-character granularity using a shortest insertion/deletion edit script (equivalently a longest common subsequence). Omit deleted source chunks; render equal target chunks green and inserted target chunks bold red, resetting after every diff chunk. Preserve separate equal chunks when a deleted chunk lay between them.

For example, exact color output for `hello_world.txt` changed to `goodbye_world.txt` is:

```text
\x1b[1mThis is a DRY-RUN\x1b[0m
\x1b[38;5;8mhello_world.txt\x1b[0m -> \x1b[1;31mgoodby\x1b[0m\x1b[32me\x1b[0m\x1b[32m_world.txt\x1b[0m
```

For `abc123xyz.txt -> abc456xyz.txt`, the target is `\x1b[32mabc\x1b[0m\x1b[1;31m456\x1b[0m\x1b[32mxyz.txt\x1b[0m`. For a backup, render `Info: ` bold/reset, then ` Backup created - ` plain, then the entire `source -> backup` text dark gray/reset.

For complete clarity about diff tie-breaking and chunk boundaries, the following table gives all required representative basename renderings. `G{text}` means one green/reset span and `R{text}` means one bold-red/reset span; adjacent entries remain separate spans.

| Source -> target | Colored target spans |
|---|---|
| `hello_world.txt -> goodbye_world.txt` | `R{goodby} G{e} G{_world.txt}` |
| `foo_bar.txt -> f0o_bar.txt` | `G{f} R{0} G{o} G{_bar.txt}` |
| `test.txt -> renamed.txt` | `R{r} G{e} R{named} G{.txt}` |
| `abc123xyz.txt -> abc456xyz.txt` | `G{abc} R{456} G{xyz.txt}` |
| `prefix_test.txt -> PRE_test.txt` | `R{PRE} G{_test.txt}` |
| `test_suffix.txt -> test_END.txt` | `G{test_} R{END} G{.txt}` |
| `complete_replacement.txt -> totally_different_name.txt` | `R{t} G{o} R{ta} G{l} R{ly_diff} G{e} R{ren} G{t} G{_} R{n} G{a} G{me} G{.txt}` |
| `file.txt -> document.txt` | `R{docum} G{e} R{nt} G{.txt}` |
| `short.txt -> very_long_replacement.txt` | `R{very_l} G{o} R{ng_} G{r} R{eplacemen} G{t.txt}` |
| `very_long_filename.txt -> tiny.txt` | `R{t} G{i} G{n} R{y} G{.txt}` |
| `backup_test.txt -> renamed_backup.txt` | `R{renamed_} G{backup} G{.txt}` |
| `abc.txt -> def.txt` | `R{def} G{.txt}` |
| `a.txt -> xyz.txt` | `R{xyz} G{.txt}` |
| `aaaa.txt -> bbaa.txt` | `R{bb} G{aa} G{.txt}` |
| `test123.txt -> TEST123.txt` | `R{TEST} G{123.txt}` |
| `file1.txt -> doc1.txt` | `R{doc} G{1.txt}` |
| `multi_word name.txt -> single_word name.txt` | `R{sing} G{l} R{e} G{_word name.txt}` |
| `test-file.txt -> renamed-file.txt` | `R{r} G{e} R{named} G{-file.txt}` |
| `extension.txt -> extension.doc` | `G{extension.} R{doc}` |

## Spec 23

Operational errors never masquerade as success; unless silent mode suppresses their text as specified in Spec 5, they go to stderr. Invalid regex syntax is not suppressed by silent mode. In plain mode, it starts with `Error: Bad expression provided`, then a blank line, then a multiline parse diagnostic with the expression, a caret, and the specific reason. Exact examples are:

```text
Error: Bad expression provided

regex parse error:
    ([
     ^
error: unclosed character class
```

```text
Error: Bad expression provided

regex parse error:
    (test
    ^
error: unclosed group
```

```text
Error: Bad expression provided

regex parse error:
    *
    ^
error: repetition operator missing expression
```

An unsupported pattern backreference diagnostic contains `backreferences are not supported`; an unsupported look-around diagnostic contains `look-around, including look-ahead and look-behind, is not supported`; an unclosed named group contains `error: unclosed capture group name`.

With color `always`, render `Error: ` red/reset, leave the short message plain, and render the whole subsequent regex parse diagnostic red/reset. With `never`, `auto` on captured streams, or silent mode, use the plain diagnostic. Silent mode does not suppress this bad-expression diagnostic; other planning and execution diagnostics follow Spec 5.

## Spec 24

Command-line parsing diagnostics go to stderr and have status 2. Running with no command prints the complete main help to stderr and no stdout. An unknown command uses this structure:

```text
error: unrecognized subcommand 'bogus'

Usage: executable <COMMAND>

For more information, try '--help'.
```

Missing positionals identify all missing placeholders under `error: the following required arguments were not provided:` and show the command usage. For example, `regex a` identifies `<REPLACEMENT>` and `<PATH(S)>`; `regex a b` identifies `<PATH(S)>`. Invoking `to-ascii` with no positionals exits 2, emits no stdout, and writes the complete `to-ascii` help from Spec 3 to stderr, beginning with `Replace file name UTF-8 chars with ASCII chars representation`; this full-help behavior is required, not optional.

An unknown option reports `error: unexpected argument '--unknown' found` and includes `tip: to pass '--unknown' as a value, use '-- --unknown'`. An invalid color reports `error: invalid value 'bogus' for '--color <COLOR>'` and lists possible values. A nonnumeric integer token consumed as an option value identifies `--replace-limit <LIMIT>` or `--max-depth <LEVEL>` and contains `invalid digit found in string`. A detached dash-leading token is parsed differently: `regex a b x -l -1` exits 2 with empty stdout and the following exact stderr:

```text
error: unexpected argument '-1' found

  tip: to pass '-1' as a value, use '-- -1'

Usage: executable regex [OPTIONS] <EXPRESSION> <REPLACEMENT> <PATH(S)>...

For more information, try '--help'.
```

Repeated color reports `error: the argument '--color <COLOR>' cannot be used multiple times`. A force/dry-run conflict reports `error: the argument '--dry-run' cannot be used with '--force'`. A dump/no-dump conflict reports `error: the argument '--dump' cannot be used with '--no-dump'` and exits 2 before any rename or dump. A command-specific option before the command is also rejected before dispatch. In particular, `executable --color never regex --help` exits 2, emits no stdout, and writes exactly:

```text
error: unexpected argument '--color' found

  tip: 'regex --color' exists

Usage: executable <COMMAND>

For more information, try '--help'.
```

All such failures occur before filesystem changes.

## Spec 25

Two malformed-but-JSON-valid preview cases intentionally retain the observed fatal behavior. If a `from-file -n` operation has an empty source string, exit nonzero and write exactly the following to stderr (a runtime may insert a numeric thread id after `main`, which is otherwise immaterial):

```text

thread 'main' panicked at src/output.rs:<error location>:
called `Option::unwrap()` on a `None` value
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

If the target string is empty, use the same text but `src/output.rs:<error location>`. These two empty strings pass JSON schema parsing but fail while formatting the preview. They must not be silently skipped, treated as the current directory, or converted to a friendly parse error.
