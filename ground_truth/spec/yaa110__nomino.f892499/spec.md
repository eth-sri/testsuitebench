## Spec 1

The required artifact is a single executable file named exactly `executable`. It implements `nomino` version 1.6.4, a batch-renaming command-line program. It must run on the Linux evaluation host, accept UTF-8 command-line arguments and filenames, and finish promptly for small directory trees.

Normal diagnostics go to stderr and normal reports go to stdout. A successful operation exits 0. A runtime/configuration failure exits 1. A command-line parsing or typed-value error exits 2. Except for errors encountered while applying individual map entries (described later), errors produce no stdout. All shown text uses `\n` line endings.

With no matches, the command is a silent success: exit 0 with empty stdout and stderr. Actual renames must preserve file bytes exactly, including arbitrary binary data.

## Spec 2

The command grammar is:

```text
executable [OPTIONS] [[SOURCE] OUTPUT]...
```

The supported options are:

```text
-d, --dir PATH
    working directory; default is the process current directory
--depth DEPTH
    nonnegative integer lower/exact traversal depth for regex mode
-E, --no-extension
    do not append each input's extension in regex or sort mode
-g, --generate PATH
    write the generated reverse/undo JSON map
-h, --help
-k, --mkdir
    recursively create missing parents of output paths
-m, --map PATH
--from-file PATH
    exact alias of --map
--max-depth DEPTH
    nonnegative integer upper traversal depth for regex mode
-q, --quiet
-r, --regex PATTERN
-s, --sort ORDER
    ORDER is asc or desc, parsed without ASCII-case sensitivity
-t, --test
--dry-run
    exact alias of --test
-V, --version
-w, --overwrite
```

Options may appear before, between, or after positional arguments. Thus `-s asc "{1}" -q` is valid. `--` ends option parsing, so tokens such as `--weird` after it are positionals. `--help` takes precedence over other arguments: even `--help --definitely-not-a-flag` prints normal long help and exits 0.

## Spec 3

`-h` must print the following short help byte-for-byte to stdout, including its final newline, and print nothing to stderr:

```text
Batch rename utility for developers

Usage: executable [OPTIONS] [[SOURCE] OUTPUT]...

Arguments:
  [[SOURCE] OUTPUT]...  OUTPUT is the pattern to be used for renaming files, and SOURCE is the optional regex pattern to match by filenames. SOURCE has the same function as -r option

Options:
  -d, --dir <PATH>         Sets the working directory
      --depth <DEPTH>      Optional value to overwrite inferred subdirectory depth value in 'regex' mode
  -E, --no-extension       Does not preserve the extension of input files in 'sort' and 'regex' options
  -g, --generate <PATH>    Stores a JSON map file in '<PATH>' after renaming files
  -h, --help               Print help (see more with '--help')
  -k, --mkdir              Recursively creates all parent directories of '<OUTPUT>' if they are missing
  -m, --map <PATH>         Sets the path of map file to be used for renaming files [aliases: --from-file]
      --max-depth <DEPTH>  Optional value to set the maximum of subdirectory depth value in 'regex' mode
  -q, --quiet              Does not print the map table to stdout
  -r, --regex <PATTERN>    Regex pattern to match by filenames
  -s, --sort <ORDER>       Sets the order of natural sorting (by name) to rename files using enumerator [possible values: asc, desc]
  -t, --test               Runs in test mode without renaming actual files [aliases: --dry-run]
  -V, --version            Print version
  -w, --overwrite          Overwrites output files, otherwise, a '_' is prepended to filename

OUTPUT pattern accepts placeholders that have the format of '{G:P}' where 'G' is the captured group and 'P' is the padding of digits with `0`. Please refer to https://github.com/yaa110/nomino for more information.
```

`--version` and `-V` print exactly `nomino 1.6.4\n` to stdout, nothing to stderr, and exit 0.

## Spec 4

`--help` must print the following long help byte-for-byte to stdout, including trailing spaces on the two otherwise blank lines before the alias annotations (each such line contains ten spaces) and including the final newline. It prints nothing to stderr and exits 0.

```text
Batch rename utility for developers

Usage: executable [OPTIONS] [[SOURCE] OUTPUT]...

Arguments:
  [[SOURCE] OUTPUT]...
          OUTPUT is the pattern to be used for renaming files, and SOURCE is the optional regex pattern to match by filenames. SOURCE has the same function as -r option

Options:
  -d, --dir <PATH>
          Sets the working directory

      --depth <DEPTH>
          Optional value to overwrite inferred subdirectory depth value in 'regex' mode

  -E, --no-extension
          Does not preserve the extension of input files in 'sort' and 'regex' options

  -g, --generate <PATH>
          Stores a JSON map file in '<PATH>' after renaming files

  -h, --help
          Print help (see a summary with '-h')

  -k, --mkdir
          Recursively creates all parent directories of '<OUTPUT>' if they are missing

  -m, --map <PATH>
          Sets the path of map file to be used for renaming files
          
          [aliases: --from-file]

      --max-depth <DEPTH>
          Optional value to set the maximum of subdirectory depth value in 'regex' mode

  -q, --quiet
          Does not print the map table to stdout

  -r, --regex <PATTERN>
          Regex pattern to match by filenames

  -s, --sort <ORDER>
          Sets the order of natural sorting (by name) to rename files using enumerator

          Possible values:
          - asc:  Sort in ascending order
          - desc: Sort in descending order

  -t, --test
          Runs in test mode without renaming actual files
          
          [aliases: --dry-run]

  -V, --version
          Print version

  -w, --overwrite
          Overwrites output files, otherwise, a '_' is prepended to filename

OUTPUT pattern accepts placeholders that have the format of '{G:P}' where 'G' is the captured group and 'P' is the padding of digits with `0`. Please refer to https://github.com/yaa110/nomino for more information.
```

## Spec 5

Exactly one input mode is selected as follows:

- Regex mode is selected by `-r PATTERN`/`--regex PATTERN`, followed by one positional `OUTPUT`.
- Positional-source mode is the same regex mode, written as two positionals `SOURCE OUTPUT` and no `-r`, `-s`, or `-m`.
- Sort mode is selected by `-s asc|desc`/`--sort asc|desc`, followed by one positional `OUTPUT`.
- Map mode is selected by `-m PATH`, `--map PATH`, or `--from-file PATH`; it requires no output pattern.

One positional alone does not implicitly select a mode. No arguments, only an output positional, or options such as `-t -d PATH` without a mode must exit 1 and print:

```text
error: one of 'regex', 'sort', 'map' or 'SOURCE' options must be set.
usage: run '<argv0> --help' for more information.
```

Here `<argv0>` is exactly the path used to invoke the executable (for example `./executable`). Combining a two-positional `SOURCE OUTPUT` pair with regex, sort, or map mode exits 1 and prints exactly:

```text
error: optional SOURCE must be used without setting regex, map or sort flags
```

This includes giving two positionals after `-s asc`, or giving a positional source in addition to `-r` or `-m`. A regex flag without its positional output is an error whose stderr contains `the following required arguments were not provided:` and `<[SOURCE] OUTPUT>...`.

## Spec 6

Parser-level validation follows clap-style diagnostics. These errors exit 2, write stderr, and leave stdout empty:

- An unknown flag reports `error: unexpected argument '--bogus' found` and ends with `For more information, try '--help'.` For `--nonexistent-flag`, it additionally says `a similar argument exists`.
- A missing `--dir` value says `a value is required for '--dir <PATH>'`.
- A missing `-r`/`--regex` value says `a value is required for '--regex <PATTERN>'`.
- An invalid sort value says `invalid value '<value>' for '--sort <ORDER>'`, lists `possible values`, `asc`, and `desc`. For lowercase `invalid`, the entire trimmed diagnostic is:

```text
error: invalid value 'invalid' for '--sort <ORDER>'
  [possible values: asc, desc]

For more information, try '--help'.
```

- A noninteger depth such as `--depth foo` says `invalid value 'foo' for '--depth <DEPTH>'`.
- In the spaced form `--depth -1`, `-1` is parsed as a flag-like token: the diagnostic contains `unexpected argument '-1'` and `to pass '-1' as a value, use '-- -1'`.
- In the equals form `--depth=-1`, the diagnostic contains `invalid value '-1' for '--depth <DEPTH>'`.

## Spec 7

`-d PATH` changes the root under which entries are discovered and renamed. If absent, use the process current directory. Relative source and destination names in a JSON map, and relative `-m` and `-g` paths, are resolved against this working root, not against the caller's current directory. Absolute paths remain absolute.

If the working directory does not exist, exit 1 and print exactly `error: No such file or directory (os error 2)\n` to stderr. An empty existing working directory is not an error.

Paths displayed in reports and stored in generated maps are relative to the working root when the inputs/outputs were relative. On Linux, nested displayed paths use `/`.

## Spec 8

Regex mode performs a leftmost search, not a required full-string match, against each candidate's path relative to the working root. Process candidates in the order yielded by the filesystem directory walker. Regex mode does not apply natural or lexicographic sorting to those paths; natural ordering is specific to sort mode. A nonmatching entry is untouched and omitted from reports/maps. Matching is UTF-8/Unicode aware and case-sensitive by default. At minimum, the regex dialect must support Rust-regex-compatible literals, `.`, `.*`, character classes, `\d`, `\w`, repetition (`+`), numbered groups, and named groups in both `(?<name>...)` and `(?P<name>...)` forms.

Examples of required matching and substitution include:

```text
file_01.txt, SOURCE file_(\d+)\.txt, OUTPUT renamed_{} -> renamed_01.txt
S01E05.mkv, SOURCE S(?<season>\d+)E(?<episode>\d+)\.mkv,
  OUTPUT Season{season}_Episode{episode} -> Season01_Episode05.mkv
doc-v1-final.txt, SOURCE doc-v(\d+)-(\w+),
  OUTPUT document_version{1}_status{2}.txt -> document_version1_statusfinal.txt.txt
café.txt, SOURCE (café), OUTPUT {1}_processed -> café_processed.txt
```

Positional `SOURCE OUTPUT` and `-r SOURCE OUTPUT` have identical semantics and output. Candidate names beginning with one or more `-` are ordinary filesystem names and remain matchable.

## Spec 9

Regex traversal depth counts a root entry as depth 1, an entry in an immediate child directory as depth 2, and so on.

- With neither depth option, infer one exact candidate depth from SOURCE: it is one plus the number of path separators represented by the pattern. Thus `file(\d+)` searches depth 1, while `a/b/(file)` searches depth 3 and can report `a/b/file.txt`.
- `--depth D` overrides the inferred minimum depth. Without `--max-depth`, it selects exactly depth D.
- `--max-depth M` without `--depth` searches all depths 1 through M.
- With both, search from `min(D, M)` through M. This clamping is observable for `--depth 3 --max-depth 2`, which searches depth 2.

For a tree containing `file1.txt`, `a/file2.txt`, `a/b/file3.txt`, and `a/b/c/file4.txt`: depth 2 alone selects only `a/file2.txt`; max-depth 2 selects the first two; depth 2 plus max-depth 3 selects `a/file2.txt` and `a/b/file3.txt`. A large maximum simply visits all available levels.

The path-separator pattern `s(\d+)/.*E(\d+).*` must match files in `s1/` and `s2/`. With output `{:2}/{:2}.mkv`, `-E`, and `-k`, episodes 1 and 2 under `s1` become `01/01.mkv` and `01/02.mkv`, while episodes 3 and 4 under `s2` become `02/03.mkv` and `02/04.mkv`.

## Spec 10

Sort mode enumerates every immediate entry in the working directory, including subdirectories. It does not recurse. It orders entry names with natural numeric comparison: digit runs compare numerically, so ascending order places `file1`, `file2`, `file10`, `file20`; descending is the exact reverse. Enumeration always starts at 1 in the selected order. `asc` and `desc` option values are accepted in any ASCII casing, but name ordering itself retains case/code-point distinctions. For the names `FILE2.txt`, `File1.txt`, and `file3.txt`, ascending output order is exactly that listed order.

In sort mode placeholder group 0 is the complete input entry name, including its final extension, and group 1 is the enumeration number. Therefore the first `{}` or `{:3}` uses the enumeration number. For `a.txt`, `b.txt` and output `{:2}`, ascending produces `01.txt`, `02.txt`; with `-E`, it produces extensionless `01`, `02`. Ascending `a.txt`, `b.md` with output `{0}_{1}_{}` reports `a.txt -> a.txt_1_1.txt` and `b.md -> b.md_2_2.md`. Descending `a.txt`, `b.txt`, `c.txt` with `file_{}` reports `c.txt -> file_1.txt`, `b.txt -> file_2.txt`, `a.txt -> file_3.txt`.

Unicode names are supported in sorting. Required ascending order for `café.txt`, `file_😀.txt`, `файл.txt`, `文件.txt` is that exact sequence.

## Spec 11

In regex and sort modes, extension preservation is enabled by default. Determine the extension from the final suffix of the input entry (the part after its last dot), remove that suffix for purposes where a stem is needed, format the requested output, then append `.` and the original extension. This append is unconditional with respect to the text already present in OUTPUT: `renamed_{}.txt` applied to `file1.txt` produces `renamed_1.txt.txt`; `archive_file.tar.gz` applied to `file.tar.gz` produces `archive_file.tar.gz.gz`. Different inputs retain their own extensions. Entries with no extension receive no suffix.

`-E`/`--no-extension` disables this final append. It does not strip text that was captured by the regex or explicitly placed in OUTPUT. Thus with `-E`, matching `(.+)` against `café.txt` and formatting `{1}_renamed` produces `café.txt_renamed`, while formatting `film_{}.mp4` can explicitly produce `.mp4`.

Map mode uses destination strings literally and does not add extensions.

## Spec 12

An OUTPUT format is arbitrary text plus placeholders. A placeholder is `{G:P}`, where both `:P` and, for automatic placeholders, `G` may be omitted:

- `{0}` is regex capture 0, the entire substring matched by SOURCE (not necessarily the whole filename).
- `{1}`, `{2}`, etc. select numbered capture groups.
- `{name}` selects a named capture.
- `{}` selects numbered capture 1; later automatic placeholders in the same OUTPUT select groups 2, 3, and so on.
- `{:P}` is the same automatic selection with padding.
- Explicit indexed or named placeholders do not advance or reset the automatic-placeholder counter. For two captures, `{2}_{}` therefore means group 2 followed by group 1.
- A placeholder may be repeated and is substituted every time.

Examples:

```text
SOURCE file_(\d+)_([a-z]), OUTPUT {}_{}       -> 1_a
SOURCE file_(\d+)_([a-z]), OUTPUT {2}_{}      -> a_1
SOURCE file(\d+), OUTPUT {1}_{1}_{1}          -> 1_1_1
SOURCE file(\d+), OUTPUT {0}_backup           -> file1_backup
SOURCE episode_s(?P<s>\d+)e(\d+), OUTPUT S{s}_E{2} -> S1_E2
```

If an indexed, named, or automatic placeholder refers to an absent/unmatched group, substitute the empty string rather than failing. Consequently `{1}_{2}_{3}` with only group 1 becomes `1__`, and `{}_{} ` with only group 1 has an empty second substitution. Very large group numbers are valid absent-group references.

## Spec 13

Padding syntax is `{group:width}` or `{:width}`. A nonnegative decimal width is accepted. Empty padding (`{:}`) and width zero mean no padding. If the selected capture is a nonnegative decimal integer shorter than the width, left-pad it with ASCII zeroes. Never truncate a longer value: with width 2, `1`, `2`, `999` become `01`, `02`, `999`. A width of 10 must be supported. Nonnumeric and negative captured values pass through unchanged rather than being padded.

Named captures can be padded in the same way. For example `{num:4}` turns captured `1` into `0001`, and `{quality}` preserves `720p` unchanged.

Malformed padding is a runtime format error, exits 1, and prints exactly one of these applicable messages to stderr:

```text
error: [output-format] unable to parse padding of 'abc'
error: [output-format] unable to parse padding of '5a'
error: [output-format] unable to parse padding of '-3'
error: [output-format] unable to parse padding of ':'
```

The last line is the result for `{1::}`.

## Spec 14

Within OUTPUT, the only valid backslash escapes are `\{` for a literal `{`, `\}` for a literal `}`, and `\\` for one literal backslash. Escaped braces do not delimit placeholders. Escapes and placeholders may be adjacent. Specifically, with captures `1` and `a`, `\{{1:3}\}_{}_\{{2}\}` yields `{001}_1_{a}`.

Required format validation errors, each exiting 1, are:

```text
unmatched closing brace: error: [output-format] an unopened placeholder could not be closed by '}'
unclosed opening brace: error: [output-format] all opened placeholders must be closed by '}'
```

Any backslash followed by another character is invalid. Its diagnostic is:

```text
error: [output-format] invalid escape character of '<character>' at '<one-based-position>'
```

Thus OUTPUT `\a` reports character `a` at position 1, and `renamed\a` reports it at position 8. These errors produce no rename and no report table.

## Spec 15

Before applying operations, construct output paths from matching inputs. Identity operations, where the final relative output path equals the input path, are valid successful no-ops: do not move, delete, or recreate the entry. They are nevertheless included in the stdout table and generated map. `file1.txt` matched by `file(\d+)` with OUTPUT `file{}` therefore reports `file1.txt -> file1.txt`, remains byte-for-byte unchanged, and generates the map entry `"file1.txt": "file1.txt"`. Identity behavior is unchanged by `-t`, `-w`, `-k`, `-q`, or `-g`; quiet only hides its table.

Nonmatching entries are not mentioned. A static OUTPUT is allowed. In dry-run, planned mappings are represented internally by destination key; if several candidates produce the same destination, the candidate encountered later in the filesystem-walker order replaces the earlier report/map entry. For example, if traversal yields `file1.txt`, `file2.txt`, `file3.txt`, static output `static_name` prints only `file3.txt -> static_name.txt`. For files `file10.txt`, `file1.txt`, and `file2.txt`, the reference filesystem walk yields them in that order, so `-t -r 'file\d+' static_name` prints only `file2.txt -> static_name.txt`. The same destination-key replacement applies to missing capture groups that all produce `.txt`.

## Spec 16

Without `-w`, actual filesystem collisions are resolved by repeatedly prepending `_` to the destination basename (after any parent directory), until a path not currently present is found. Collision assignment follows the same unsorted filesystem-walker order as regex discovery. With `f1.mkv` through `f5.mkv` and `-r 'f(\d+)' 1`, that order is `f5.mkv`, `f2.mkv`, `f3.mkv`, `f4.mkv`, `f1.mkv`; the respective outputs are `1.mkv`, `_1.mkv`, `__1.mkv`, `___1.mkv`, `____1.mkv`. Collision resolution is local to each output directory.

With `-w`/`--overwrite`, use the requested destination exactly and replace an existing destination. Multiple inputs targeting one name overwrite sequentially, leaving only the one destination and no underscore variants. The winning source's contents become the destination contents. An identity operation is never treated as a collision with itself.

In dry-run no files are moved, so collision checking sees existing on-disk paths but does not see earlier hypothetical moves. If `target.txt` already exists and both `file1.txt` and `file2.txt` plan to become `target.txt`, both resolve to `_target.txt`, and destination-key replacement leaves the report row `file2.txt -> _target.txt`. With overwrite enabled, no underscore is added.

## Spec 17

Unless `-t`/`--test`/`--dry-run` is active, carry out every planned rename. Preserve contents and entry type. Remove/replace a destination only under overwrite semantics. On an individual rename failure, continue attempting other entries, print this line for that source, and ultimately exit 1:

```text
[error] unable to rename '<source-relative-path>': <operating-system error>
```

For a missing source or missing destination parent on Linux, `<operating-system error>` is `No such file or directory (os error 2)`. A JSON map containing one existing and one missing source must still rename the existing source, omit creation for the missing one, report the missing error, and exit 1.

An entry whose actual rename fails is omitted from the stdout report mapping. Consequently, with only `file1.txt`, the invocation `-r 'file(\d+)' 'missing/renamed_{}'` without `-k` exits 1, emits the individual error above, leaves `file1.txt` in place, and has empty stdout. If other entries rename successfully, their rows are still printed.

`-t` suppresses file/directory-entry moves and overwrites, but still computes and reports the complete plan. `-q` suppresses the stdout table only; it does not suppress errors, actual renames, parent creation, or generated JSON.

## Spec 18

`-k`/`--mkdir` recursively creates all missing parent directories needed by output paths before rename execution. It works for multiple levels and Unicode directory names. For example, a target `nested/deep/path/renamed_1.txt` creates all three parent levels.

Legacy behavior requires these parent directories to be created even in test/dry-run mode, although no source entry is moved. Thus `-t -k ... output/nested/name` leaves `output/nested/` present and the original file untouched. This remains true when combined with `-E`, `-q`, and `-g`.

Without `-k`, do not create missing destination parents. An attempted actual rename then emits `[error] unable to rename '<source>': No such file or directory (os error 2)` and exits 1.

## Spec 19

When not quiet and the retained report mapping is nonempty, stdout is an ASCII table with headers `Input` and `Output`. In dry-run, computed operations are retained; in actual mode, identity operations and successfully applied renames are retained, while individual failed renames are not. Compute each column's width as the maximum terminal display width of its header and cells, not UTF-8 byte length: ordinary accented and Cyrillic code points occupy one column, while wide CJK characters and emoji occupy two. Each row is `| ` + left-aligned input + ` | ` + left-aligned output + ` |`. Borders use `+`, with `width + 2` hyphens per column. Print the top border, header, middle border, rows, bottom border, and a final newline. Example:

```text
+-----------+---------------+
| Input     | Output        |
+-----------+---------------+
| file1.txt | renamed_1.txt |
| file2.txt | renamed_2.txt |
+-----------+---------------+
```

Rows are ordered by destination/output path in ascending string order, not by the displayed input column. This makes `_collision...` appear before `collision...`. Ordinary distinct numbered outputs consequently appear in number/name order. The destination-key behavior in Spec 15 determines which row survives duplicate destinations.

If the mapping is empty, print no header or borders. `-q` always makes stdout empty. Errors remain on stderr. Table cells preserve Unicode, spaces, apostrophes, parentheses, brackets, emoji, and backslashes literally; never shell-escape them.

## Spec 20

Map mode reads a UTF-8 JSON object whose string keys are current/source paths and whose string values are desired/destination paths. Process entries in ascending key order and apply each `key -> value` literally relative to the working root. `--from-file` is identical to `--map`. Map mode supports nested relative paths, collision handling, overwrite, mkdir, test, quiet, and generate behavior just like other modes. It does not require SOURCE or OUTPUT positionals.

In test mode, map keys may be reported even if the corresponding source is absent because no move is attempted. Destinations that already exist still undergo collision naming. For example, if `café.txt` exists and the map contains `"renamed_café.txt": "café.txt"`, dry-run without overwrite reports `renamed_café.txt -> _café.txt`.

A missing map file exits 1 with `error: No such file or directory (os error 2)`. The JSON must deserialize as an object of strings. Required malformed-input examples are:

```text
input: not valid json at all
error: expected ident at line 1 column 2

input:
{
  "not_valid": "json",
  "missing": ["bracket"
}
error: invalid type: sequence, expected a string at line 3 column 13
```

Each displayed error is prefixed by `error: `, written to stderr with a final newline, and exits 1.

## Spec 21

`-g PATH`/`--generate PATH` writes a UTF-8 JSON object representing the reverse/undo map of the computed operations: every property is `final output path -> original input path`. Include identity mappings. Preserve Unicode characters correctly. Relative generated-map paths are resolved under the working root.

Generation occurs in both actual and test mode and is not disabled by quiet mode. For ascending sort of `a.txt`, `b.txt` with OUTPUT `{:2}`, the parsed generated object is exactly:

```json
{"01.txt": "a.txt", "02.txt": "b.txt"}
```

For `file1.txt`, `file2.txt` renamed to `renamed_{}.txt` with extension preservation, it is:

```json
{
  "renamed_1.txt.txt": "file1.txt",
  "renamed_2.txt.txt": "file2.txt"
}
```

The output must be valid JSON; insignificant indentation is not constrained. If the output map cannot be created, exit nonzero and emit an error diagnostic. A generated undo map can immediately be supplied to `-m` to restore the original names.

## Spec 22

All discovery, regex captures, formatting, reports, JSON, directory creation, and actual renames must preserve valid Unicode without byte corruption. Required supported examples include Cyrillic (`файл`), Chinese (`文件`), accented Latin (`café`), emoji, and mixtures of scripts in one name. Regex literal matching is case-sensitive: SOURCE `café` matches `café.txt` but not `Café.txt` or `CAFÉ.txt`; SOURCE `Café` matches only `Café.txt`.

Names containing spaces, apostrophes, parentheses, square brackets, hyphens, underscores, or leading hyphens are ordinary names. Long names with a 240-character base plus `.txt` must be handled in dry-run reports. Multiple suffixes follow the last-extension rule in Spec 11. Binary contents must remain unchanged after an actual rename.

Invalid regular expressions are runtime errors with exit 1 and Rust-regex-style stderr. These examples are exact (each ends with a newline):

```text
SOURCE [a-
error: regex parse error:
    [a-
    ^
error: unclosed character class

SOURCE (
error: regex parse error:
    (
    ^
error: unclosed group

SOURCE (?P<name
error: regex parse error:
    (?P<name
            ^
error: unclosed capture group name

SOURCE *
error: regex parse error:
    *
    ^
error: repetition operator missing expression

SOURCE (?P<>test)
error: regex parse error:
    (?P<>test)
        ^
error: empty capture group name
```
