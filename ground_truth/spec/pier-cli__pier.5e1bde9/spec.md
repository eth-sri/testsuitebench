# `pier` command-line executable specification

The deliverable is a Unix command-line executable named `executable`. It implements
`pier`, a small TOML-backed catalog and runner for shell scripts. All text is UTF-8.
Unless a behavior below says otherwise, successful commands exit with status 0,
write their result to standard output, and leave standard error empty. Application
errors exit with status 1, write one `error: ...` line to standard error, and leave
standard output empty.

## Spec 1

This section defines the top-level command-line interface.

The program identifies itself as `pier` version `0.1.6`. Both `--version` and `-V`
exit successfully and print a line matching exactly the form `pier 0.1.6` (a final
newline is expected). `--help`, `-h`, and the `help` subcommand exit successfully and
print the main help. The first line of main help is `pier 0.1.6`; it also contains the
description `A simple script management CLI` and sections headed `USAGE:`, `FLAGS:`,
`OPTIONS:`, `ARGS:`, and `SUBCOMMANDS:`.

The main usage has these two forms:

```text
executable [FLAGS] [OPTIONS] <alias>
executable [FLAGS] [OPTIONS] <SUBCOMMAND>
```

The global options are:

- `-h`, `--help`;
- `-V`, `--version`;
- single-use `-v`, `--verbose`;
- `-c <path>`, `--config-file <path>`.

Global `-v` and `-c` options must occur before a subcommand. They are rejected as
unexpected if placed after a subcommand. Help and version flags are available on
each canonical subcommand as both short and long forms. For a canonical subcommand
`name`, either `name -V` or `name --version` prints exactly
`executable-name 0.1.6\n` (for example, `executable-config-init 0.1.6\n` and
`executable-show 0.1.6\n`), not the top-level `pier` banner. Main help lists at
least these canonical subcommands, each on a line indented by four spaces:

```text
add
config-init
copy
edit
list
move
remove
run
show
help
```

The aliases are `init` for `config-init`, `cp` for `copy`, `ls` for `list`, `mv`
and `rename` for `move`, and `rm` for `remove`. An alias invokes exactly the same
parser and operation as its canonical command. In particular, alias help displays
the canonical usage line, such as `USAGE:\n    executable copy` for `cp --help`.

Every canonical subcommand has distinct help output containing `USAGE:` and an
identifier of the form `executable-add`, `executable-list`, and so forth. Its help
contains these descriptions:

```text
add          Add a new script to config.
config-init  alias: init - Add a config file.
copy         alias: cp - Copy existing alias to the new one
edit         Edit a script matching alias.
list         alias: ls - List scripts
move         Move/rename existing alias to the new one
remove       alias: rm - Remove a script matching alias.
run          Run a script matching alias.
show         Show a script matching alias.
```

Subcommand help must also show the arguments and options described in the relevant
sections below.

With no arguments, or with an option but no alias/subcommand, parsing fails before
any config access. Parser failures are written to standard error, start with
`error:`, include `USAGE:`, and end with `For more information try --help`. A
missing value normally says that the option `requires a value`; missing positionals
say `The following required arguments were not provided:` followed by their
displayed names. There is a top-level precedence exception: bare `-c` or bare
`--config-file` reports the missing `<alias>` rather than a missing option value and
its usage is exactly `executable <alias> --config-file <path>`. Similarly, when any
of `-vv`, `-v -v`, or `-v --verbose` is supplied with no alias, the missing-`<alias>`
diagnostic takes precedence and its usage is `executable <alias> --verbose`. Those
repeated verbose forms are not generally valid: once an alias or subcommand is
present, each is rejected with `The argument '--verbose' was provided more than
once, but cannot be used multiple times`. Unknown options use the Clap-style phrase
`Found argument '<value>' which wasn't expected`. Examples of displayed required
names are `--alias <alias>`, `<alias>`, and the pair `<from-alias>` / `<to-alias>`.

An unrecognized non-option top-level token is normally the direct-execution alias,
not an unknown subcommand. Thus a valid catalog key may be invoked without `run`,
and an absent key reaches the `AliasNotFound` application error. `token --help`,
where `token` is not a canonical subcommand, prints main help successfully. For
compatibility with the command parser's subcommand-name inference, a direct alias
named `hello` is ambiguous with the built-in help command and is rejected with a
nonzero diagnostic containing `subcommand` and `wasn't recognized`; use
`run hello` to execute it.

## Spec 2

This section defines configuration discovery and initialization.

Commands which read or mutate a catalog select exactly one config path, in this
descending precedence:

1. the global `-c` / `--config-file` value;
2. the `PIER_CONFIG_PATH` environment variable, if it is set, including when its
   value is the empty string;
3. `pier.toml` in the process's current working directory;
4. `$XDG_CONFIG_HOME/pier/config.toml`;
5. `$XDG_CONFIG_HOME/pier/config`;
6. `$XDG_CONFIG_HOME/pier.toml`;
7. `$HOME/.pier.toml`;
8. `$HOME/.pier`.

If `XDG_CONFIG_HOME` is unset, its conventional value is `$HOME/.config`. Relative
explicit paths are resolved relative to the current working directory. Paths may
contain spaces and non-ASCII characters. Once an existing fallback is found, a
read or parse error at that path is reported; discovery does not silently continue
to a later path. If no default path exists, fail with exactly:

```text
error: No default config file found. See help for more info.
```

Thus an empty `PIER_CONFIG_PATH` selects the empty pathname rather than continuing
to `pier.toml`; reading it fails with
`error: Unable to read config from file : No such file or directory (os error 2) `.
An explicitly selected missing file fails with a message beginning
`error: Unable to read config from file {path}:` and containing
`No such file or directory (os error 2)`. Other read errors have the same prefix
and the operating-system reason; attempting to read a directory, for example,
contains `Is a directory (os error 21)`.

`config-init` (also `init`) creates a new config. With `-c` or
`PIER_CONFIG_PATH`, it creates that path. With no selected existing path, it creates
the first standard XDG target, `$XDG_CONFIG_HOME/pier/config.toml`. It may create
the file's immediate parent directory with one non-recursive mkdir operation. This
means `/existing/new/config.toml` works and creates `new`, while
`/missing/also-missing/config.toml` fails because the grandparent is absent; that
failure contains `error:` and `Failed to create directory`.

Initialization never overwrites an existing file. It then exits 1 with:

```text
error: Cannot initialize config at {path}, file already exists.
```

On success it writes exactly the following bytes and prints `Added hello-pier\n`:

```toml
[scripts.hello-pier]
command = 'echo Hello, Pier!'
description = 'This is an example command.'

[default]
```

## Spec 3

This section defines the TOML data model, validation, and persistence.

The config is TOML. It has an optional top-level `scripts` table mapping alias keys
to script records and an optional `default` record. An absent `scripts` table, an
empty `[scripts]`, an empty/whitespace-only file, and a file containing only
`[default]` all represent a catalog with no scripts.

A script record has:

- required `command`: string, including possibly empty, whitespace-only, multiline,
  very long, or Unicode text;
- optional `description`: string;
- optional `reference`: string;
- optional `tags`: array of strings, including an explicitly empty array;
- legacy `alias`: ignored input. It may have any TOML type. Operational identity
  and lookup always use the key under `scripts`; the value is not displayed or
  type-checked and is discarded whenever the config is rewritten.

The default record accepts optional `interpreter`, an array of strings, and optional
`command_width`, a nonnegative integer. The parser supports ordinary TOML syntax:
single- and double-quoted strings, escapes, literal/basic multiline strings, quoted
table keys (including aliases containing dots), inline tables, multiline arrays,
comments, whitespace, and Unicode, subject to this legacy multiline-literal parser
exception: it rejects a literal-string value whose content ends in an apostrophe
immediately adjacent to the closing `'''` delimiter (the resulting source has four
consecutive apostrophes). For example, each of these otherwise valid values is
rejected:

```toml
[scripts.loud]
command='''printf 'hello \nlast''''
```

```toml
[scripts.x]
command='''printf 'line\n''''
```

Running `-v run loud` with the first config, or `-v run x` with the second, exits
with status 1, leaves stdout empty, and writes exactly:

```text
error: Unable to parse toml config from file pier.toml: newline in string found at line 2
```

Catalog parsing therefore fails before the child or verbose wrapper runs. Tags
retain their order and duplicates. Missing optional fields remain absent rather
than becoming empty fields. Ignore unknown fields, but all modeled fields other
than ignored legacy `alias` must have the types above, every script must have a
string command, tags and interpreter arrays must contain only strings, and
`scripts` must be a map rather than a string, array, or number.

Syntax or schema failure exits 1. Its single stderr line begins:

```text
error: Unable to parse toml config from file {path}: {detail}
```

The detail must be descriptive and preserve these compatibility phrases for the
corresponding inputs:

- an unclosed table header: `expected a right bracket, found a newline at line 1`;
- a newline in an unclosed string: `newline in string found at line {n}`;
- repeated command keys: `duplicate field `command` for key `scripts.{alias}``;
- a script lacking command: `missing field `command` for key `scripts.{alias}``;
- a non-map `scripts` value: `expected map` (and for a string also
  `invalid type: string`).

Any successful add, edit, copy, move, or remove rewrites the selected file. Except
for the empty-new-alias case described in Spec 4, it is valid TOML. The resulting
parsed data must preserve all unrelated scripts and modeled metadata exactly,
including multiline and Unicode strings, empty arrays, and optional-field absence;
as noted above, every legacy `alias` field is discarded, including fields on
unrelated records. Script sections are serialized in ascending lexical order by
alias. Simple strings should use TOML literal strings when possible, producing
lines such as `command = 'echo first'`, `description = 'First script'`, and
`tags = ['tag1']`; strings requiring escaping or multiple lines must use a valid
lossless TOML representation. Alias keys requiring quoting must be quoted. In
particular, an actual newline in a newly added alias is represented by a `\n`
escape in a double-quoted TOML key, so reparsing the file restores the actual
newline in the map key rather than changing it to the two characters backslash and
`n`. Failed operations must not modify the file.

## Spec 4

This section defines adding scripts.

The grammar is:

```text
executable [GLOBAL OPTIONS] add [FLAGS] [OPTIONS] [<command>]
```

Options are required `-a <alias>` / `--alias <alias>`, optional
`-d <description>` / `--description <description>`, repeatable variadic
`-t <tags>...` / `--tag <tags>...`, and `-f` / `--force`. A space-separated tag
occurrence greedily consumes consecutive non-option tokens. Consequently, in
`add -a x -t tag 'echo first'` both `tag` and `echo first` are tag values and the
command is considered omitted. Put the positional command before `-t`, use the
single-token `--tag=value` form, or put `--` between the final tag value and the
command to disambiguate it. Exactly zero or one positional command argument is
accepted. `--` ends option parsing so a command beginning with `-` is positional,
but it does not join multiple OS arguments: `add -a x -- echo hi` is invalid because
`hi` is a second positional. There is no `--command` option.

When command is supplied, store its bytes literally as one string; do not expand
environment variables, command substitutions, backticks, quotes, backslashes,
pipes, redirects, or newlines while adding. Create a new record consisting of
`command` plus `description` only if the option appeared and `tags` only if at least
one tag option appeared. Newly created records omit the legacy `alias` and
`reference` fields. Empty descriptions are present empty strings. Repeated tags,
including equal tags, are stored in their input order.

If command is omitted, create a temporary file and launch the program named by
`EDITOR` with the temporary path as its argument. The file initially contains no
text for add. After a successful editor exit, read its complete UTF-8 contents as
the command, including any final LF or CRLF supplied by the editor. If no editor can
be launched, fail nonzero with an `error:` diagnostic mentioning the editor and do
not add the entry.

An alias is case-sensitive and otherwise unrestricted: empty strings, spaces,
hyphens, underscores, dots, digits, mixed case, and Unicode are acceptable. On a
fresh alias, write the updated config and print:

```text
Added {alias}
```

For the empty alias this is `Added ` followed by newline (and commonly appears as
`Added` after trimming). This case also writes the literal invalid TOML header
`[scripts.]`; the success does not make the file parseable, and a later catalog
operation reports a TOML parse error.

If the alias already exists and force is absent, fail without changing it:

```text
error: AliasAlreadyExists:  {alias}
```

There are two spaces between the colon and alias. With force, completely replace
that one record and print the normal `Added` line. This is replacement, not merge:
old descriptions, references, or tags disappear unless supplied in the new record;
all other catalog entries retain their modeled contents, subject to the global
legacy-`alias` discard rule in Spec 3.

## Spec 5

This section defines showing and editing scripts.

`show <alias>` requires exactly one alias. If found, print only its full command,
verbatim, followed by one newline; never include alias, tags, description, reference,
table decoration, or truncation. Empty commands therefore produce just a newline,
and multiline/very long/Unicode commands retain their content and line order.

`edit <alias>` first performs the same catalog and alias validation. It creates a
temporary UTF-8 file containing the current command and invokes `$EDITOR` with that
path. After a successful editor exit, replace `command` with the complete file
contents, preserving a final LF or CRLF. Preserve all other modeled metadata,
optional-field presence, and all other scripts; as with every rewrite, discard all
ignored legacy `alias` fields. Empty editor content is a valid empty command;
spaces, tabs, interior newlines, multiline shebangs, special characters, Unicode,
and very large content must be retained. Persist the config and print:

```text
Edited {alias}
```

For both commands, a nonempty catalog lacking the key fails with:

```text
error: AliasNotFound: No script found by alias {alias}
```

If the catalog has no scripts, `show` and `edit` instead use the no-scripts error
from Spec 10 and do not launch an editor.

## Spec 6

This section defines removing, copying, and moving scripts.

`remove <alias>` (also `rm`) deletes exactly the named record, preserves every other
record's modeled contents, rewrites the config, and prints `Removed {alias}\n`.
Legacy `alias` fields are still discarded under Spec 3. When it removes the
last record, serialization retains an empty top-level `[scripts]` table rather than
omitting `scripts`. In a nonempty catalog, an absent alias produces the exact
`AliasNotFound` line from Spec 5. In an empty catalog it produces the no-scripts
error from Spec 10.

`copy <from-alias> <to-alias>` (also `cp`) clones the complete modeled source record
to the destination key and leaves the source key and modeled contents intact.
Preserve command, description,
reference, tags (including order, duplicates, and an explicitly empty array),
optional-field absence, multiline text, Unicode, and large values. Ignored legacy
`alias` fields are not copied and are discarded from all records by the rewrite.
The records are independent thereafter. Success prints:

```text
Copy from alias {from-alias} to new alias {to-alias}
```

Copy never overwrites. If the destination already exists—including when source and
destination names are equal—fail with the exact `AliasAlreadyExists` line from
Spec 4. Destination collision is checked before source lookup, so copying from a
missing source to an existing destination reports the destination collision. If the
destination is free but source is absent, report `AliasNotFound` for the source.
An empty catalog also reports source `AliasNotFound`, not the no-scripts message.

`move <from-alias> <to-alias>` (also `mv` and `rename`) transfers the complete
modeled source record to the destination key and removes the source. Command,
description, reference, tags, and their optional-field presence are transferred,
but a legacy `alias` field is discarded rather than transferred (and legacy alias
fields on unrelated records are also discarded by the rewrite). It accepts `-f` /
`--force` before or after its positional arguments. Success prints:

```text
Move from alias {from-alias} to new alias {to-alias}
```

Without force, an existing destination (including the same key) is an
`AliasAlreadyExists` error and neither record changes. With force, delete the old
destination and replace it wholly with the source record, then delete the source;
do not merge destination metadata. If source is absent and destination is free,
report source `AliasNotFound`. Like copy, an empty catalog reports source
`AliasNotFound`. All successful and failed operations are safe across repeated
process invocations and always reflect the latest on-disk state.

## Spec 7

This section defines listing and filtering.

`list` (also `ls`) supports:

- `-q`, `--list_aliases`: output aliases only;
- `-l`, `--cmd_full`: do not limit the command column;
- `-c <unsigned integer>`, `--cmd_width <unsigned integer>`: command display width;
- repeatable `-t <tag>`, `--tag <tag>`: exact tag filters.

The long option names contain underscores exactly as shown. Invalid integer text
fails in the parser with `Invalid value for '--cmd_width` and an `invalid digit`
detail. `--cmd_width=-1` is invalid. When supplied as a separate token, a value
beginning `-` is treated as an unexpected argument and the diagnostic contains
`Found argument '-1'`.

First sort scripts by their map keys in ascending lexical order. With no tag filter,
include each once. Tag matching is exact and case-sensitive. With filters, iterate
each sorted script and emit it once for every requested tag value which occurs in
the script's tags. This implements OR filtering but intentionally does not
deduplicate: a script tagged `tag1,tag2` appears twice for `-t tag1 -t tag2`, and
every script tagged `tag1` appears twice for `-t tag1 -t tag1`. Untagged scripts do
not match.

Display-mode precedence is `-q` first, then `-l`, then an explicit width, then
`default.command_width`, then fallback width 80. In alias-only mode, print just each
selected map key and newline, with no header or decoration. No matches is successful
and produces empty stdout. Tag filtering still applies in this mode.

In table mode, make four left-aligned columns in this order: `Alias`, `Tags`,
`Command`, `Description`. Alias is the map key. Tags are joined by commas with no
spaces. Missing/empty tags and descriptions are empty cells. `reference` and legacy
`alias` metadata are not displayed. Commands whose first two characters are `#!`
display as the literal `#! script` in every table mode. Other commands retain all
leading and trailing whitespace in the command cell. Unless `-l` is active, treat
the chosen width as a UTF-8 byte index into that raw, untrimmed command, with no
ellipsis: if the command has more bytes than the width, display the Rust string
slice `command[..width]`; otherwise display the whole command. This counts neither
Unicode scalar values nor terminal columns. Thus widths 4 and 7 applied to
`  ab界dé  ` display `  ab` and `  ab界`, respectively, including the two leading
spaces. If the byte index lies inside a multibyte character, slicing panics rather
than rounding to a character boundary. In particular, `list --cmd_width 5` for
that command exits with status 101, leaves stdout empty, and writes:

```text
thread 'main' panicked at src/script.rs:36:52:
byte index 5 is not a char boundary; it is inside '界' (bytes 4..7) of `  ab界dé  `
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

The width may be very large. `-l` always wins over a width option, and `-q` wins
over both.

Render the table in the following deterministic pretty-table style:

1. For each column, find the maximum terminal display width among its header and
   every line of every selected cell.
2. A physical table row is `⋮ `, then each cell padded on the right to its column
   width, with ` ⋮ ` between cells, and a final ` ⋮\n`.
3. A border is the character `≖` repeated to the display width of a physical row,
   followed by newline.
4. Output top border, header row, another border, all data rows, and bottom border.
   A cell containing newlines expands to further physical rows; columns without a
   corresponding line are empty on those rows.
5. Unicode text is emitted unchanged and padding uses terminal column width, so
   wide characters do not misalign following columns.

For example, a single record with alias `solo`, tags `['lonely']`, command
`echo one`, and description `Only script` renders exactly:

```text
≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖
⋮ Alias ⋮ Tags   ⋮ Command  ⋮ Description ⋮
≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖
⋮ solo  ⋮ lonely ⋮ echo one ⋮ Only script ⋮
≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖
```

With scripts present but no filter matches, render the same structure using only
header widths:

```text
≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖
⋮ Alias ⋮ Tags ⋮ Command ⋮ Description ⋮
≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖
≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖≖
```

## Spec 8

This section defines running inline commands.

`run <alias> [args...]` executes a stored script, as does the top-level direct form
`<alias> [args...]`. The two forms have the same lookup, streams, exit status, and
argument semantics. `run -- <dash-leading-alias> [args...]` stops option parsing,
so dash-leading values reach config lookup rather than causing a parser error.

If `command` does not begin exactly with `#!`, execute it through an interpreter.
Use `default.interpreter` when present: its first element is the executable and its
remaining elements precede the command text. Otherwise, if the `SHELL` environment
variable is present, use its value with `-c`; this includes the empty string, which
is attempted as an executable and fails with
`error: Command execution failed with: No such file or directory (os error 2)`.
Use `/bin/sh` with `-c` only when `SHELL` is unset.
The effective argv is conceptually:

```text
interpreter... command alias arg1 arg2 ...
```

This makes the pier alias available as shell `$0`, and user arguments as `$1`,
`$2`, ... and `$@`. Before `--`, an argument beginning with `-` is still parsed as
a CLI option and an unrecognized one (for example `-n`) fails with the normal
`Found argument '-n' which wasn't expected` parser diagnostic. Put `--` after the
alias to pass such arguments. For arguments which reach the child, preserve each OS
argument boundary and every character within it, including spaces, newlines,
dollar signs, glob characters, equals signs, and backslashes. The stored command is
genuine shell/program text, so pipes, redirects,
`&&`, subshells, variable/command expansion, blank lines, `set -e`, and long output
work normally.

The child inherits the caller's environment, current working directory, and stdin.
Forward its stdout without truncation and preserve its exit status exactly,
including statuses 1, 2, 42, 99, 100, and 127. Forward child stderr as stderr;
compatibility behavior prints a newline after a nonempty captured stderr buffer, so
child stderr `error\n` becomes `error\n\n`. Do not print a generic application
error merely because the child exits nonzero.

Before execution, an empty catalog fails with the no-scripts error in Spec 10. A
nonempty catalog lacking the selected key fails with exact `AliasNotFound`. An empty
stored command executes successfully with no stdout or stderr.

## Spec 9

This section defines running shebang scripts and verbose mode.

If a command starts at byte zero with `#!`, write the complete command to a
temporary file, make it executable, and execute that file directly with the user
arguments. This lets the kernel honor any valid shebang, including `/bin/sh`,
`/bin/bash`, and `/usr/bin/env python3`. The temporary file must retain all lines,
indentation, blank lines, and Unicode, and must be cleaned up afterward. Child
environment, working directory, stdin, streams, argument boundaries, and exit-code
propagation are the same as for inline commands.

With the single global verbosity flag, successful lookup wraps captured script
stdout in this exact stdout format (25 hyphens on each separator line):

```text
Starting script "{alias}"
-------------------------
{raw child stdout}-------------------------
Script complete
```

Normally child stdout already ends in newline, putting the closing separator on the
next line. Preserve the child's bytes, including a trailing space before its
newline. Verbosity does not change argument passing or exit status. Child stderr
remains on stderr under the rule in Spec 8. Verbose is a global flag and therefore
must appear before `run` or before the direct alias.

## Spec 10

This section defines empty-catalog behavior and operational errors.

For `list`, `run`, `remove`, `show`, and `edit`, a successfully parsed config with
no scripts fails with status 1 and exactly:

```text
error: No scripts exist. Would you like to add a new script?
```

`add` is allowed on an empty config. As specified above, `copy` and `move` instead
report source `AliasNotFound` when empty.

All aliases are matched exactly and case-sensitively against TOML map keys. The
standard missing-key error is exactly:

```text
error: AliasNotFound: No script found by alias {alias}
```

All application errors end in newline on stderr. No success message is emitted on
failure. Validate command-line syntax before loading config; after syntax succeeds,
load and validate the whole config before executing the requested operation. For
mutations, validate all collisions and lookups before rewriting, ensuring malformed
input, missing aliases, duplicate aliases, editor failures, and other errors leave
the original file byte-for-byte unchanged.
