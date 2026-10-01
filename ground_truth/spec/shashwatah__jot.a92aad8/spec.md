# Jot executable behavioral specification

In this document, `executable` is the required command-line program. It implements a local, terminal-oriented note manager. All paths and state described below are local to the user running the process. Unless a rule says otherwise, every textual result ends in `\n`.

The following byte sequences are used throughout:

- `B = "\x1b[0;34m"` (blue),
- `R = "\x1b[0;31m"` (red), and
- `Z = "\x1b[0m"` (reset).

Notation such as `{B}{name}{Z}` means direct concatenation; braces are not printed. Output is UTF-8.

## Spec 1

The executable is a multi-invocation, persistent CLI. It must read the process environment independently on every invocation. If `XDG_CONFIG_HOME` is set, the configuration file is `${XDG_CONFIG_HOME}/jot/config`; otherwise it is `${HOME}/.config/jot/config`. If `XDG_DATA_HOME` is set, the vault registry is `${XDG_DATA_HOME}/jot/vaults`; otherwise it is `${HOME}/.local/share/jot/vaults`.

On first use, create the parent directories and both files. The exact fresh contents are:

```text
editor = 'nvim'
conflict = true
```

for `config`, and:

```text
[vaults]
```

for `vaults`. These files must also be initialized when the first useful command touches only the other subsystem (for example, `config editor` still creates the empty vault registry). State changes must be flushed before the process exits and visible to the next invocation.

## Spec 2

The canonical subcommands and aliases are exactly:

| Canonical | Alias | Arguments |
|---|---|---|
| `vault` | `vl` | no args; `-l`; or `<vault name> <vault location>` |
| `note` | `nt` | `<note name>` |
| `folder` | `fd` | `<folder name>` |
| `enter` | `en` | `<vault name>` |
| `open` | `op` | `<note name>` |
| `opdir` | `od` | none |
| `chdir` | `cd` | `<folder path>` |
| `list` | `ls` | optional `<item type>` |
| `remove` | `rm` | `<item type> <name>` |
| `rename` | `rn` | `<item type> <name> <new name>` |
| `move` | `mv` | `<item type> <name> <new location>` |
| `vmove` | `vm` | `<item type> <name> <vault name>` |
| `config` | `cf` | optional `<config type>` and optional single `<config value>` |

Aliases must have the same validation, side effects, normal output, and errors as their canonical commands. For item-type arguments, `vault`/`vl`, `note`/`nt`, and `folder`/`fd` are interchangeable where that type is supported. `vmove` supports only note and folder types. `list` supports no filter, note/`nt`, or folder/`fd`.

## Spec 3

Normal help invocations return 0 and write only to stdout. `--help`, `-h`, and `help` display main help. `help <canonical-or-alias>` and `<canonical-or-alias> --help` or `-h` display that subcommand's help. A help flag placed after a subcommand selects subcommand help. A leading `--help` takes precedence over later garbage. A token after `--` is positional and is not interpreted as a help flag.

With no arguments, stdout is empty; write to stderr the exact main banner specified as the `--help` stdout in Spec 4, with no `error:` prefix, and exit 2. Unknown commands or global flags (including `--version`) and invalid item/config types are syntax errors: print a useful clap-style error to stderr and return a nonzero status (normally 2). Unknown input must be quoted in a phrase of the form `Found argument 'INPUT' which wasn't expected` and finish with `For more information try --help` when a usage diagnostic is shown.

Missing required arguments are syntax errors on stderr, exit 2. They contain `The following required arguments were not provided:`, list every missing placeholder, include the applicable `USAGE:` block, and end with `For more information try --help`. The placeholders are exactly `<vault location>`, `<vault name>`, `<note name>`, `<folder name>`, `<folder path>`, `<item type>`, `<name>`, `<new name>`, and `<new location>` as applicable.

## Spec 4

The main `--help` stdout must equal the following Python-style escaped string exactly. Interpret `\x1b`, `\n`, and `\\` as their represented bytes/characters, rather than printing the backslash notation:

```text
'\x1b[0;34m________      _____ \n______(_)_______  /_\n_____  /_  __ \\  __/\n____  / / /_/ / /_  \n___  /  \\____/\\__/  \n/___/         ᵥ₀.₁.₂  \n\x1b[0m         \n\nusage: jt <command>\n\n\x1b[0;34mcommands:\x1b[0m\n\ncreate items\n    \x1b[0;34mvault\x1b[0m, \x1b[0;34mvl\x1b[0m       create a vault or list vaults\n    create items in current folder\n        \x1b[0;34mnote\x1b[0m, \x1b[0;34mnt\x1b[0m        create a note \n        \x1b[0;34mfolder\x1b[0m, \x1b[0;34mfd\x1b[0m      create a folder\n\ninteract with items\n    \x1b[0;34menter\x1b[0m, \x1b[0;34men\x1b[0m       enter a vault\n    \x1b[0;34mopen\x1b[0m, \x1b[0;34mop\x1b[0m        open a note from current folder\n    \x1b[0;34mopdir\x1b[0m, \x1b[0;34mod\x1b[0m       open current folder in file explorer\n    \x1b[0;34mchdir\x1b[0m, \x1b[0;34mcd\x1b[0m       change folder within current vault\n    \x1b[0;34mlist\x1b[0m, \x1b[0;34mls\x1b[0m        list items in current folder\n\nperform fs operations on items\n    \x1b[0;34mremove\x1b[0m, \x1b[0;34mrm\x1b[0m      remove an item \n    \x1b[0;34mrename\x1b[0m, \x1b[0;34mrn\x1b[0m      rename an item \n    \x1b[0;34mmove\x1b[0m, \x1b[0;34mmv\x1b[0m        move an item to a new location\n    \x1b[0;34mvmove\x1b[0m, \x1b[0;34mvm\x1b[0m       move an item to a different vault\n\nconfig\n    \x1b[0;34mconfig\x1b[0m, \x1b[0;34mcf\x1b[0m      display, set or open config\n\nget help \n    use \x1b[0;34mhelp\x1b[0m or \x1b[0;34m-h\x1b[0m and \x1b[0;34m--help\x1b[0m flags along with a command to get corresponding help\n'
```

In particular, this includes the ANSI coloring, Unicode subscript version `ᵥ₀.₁.₂`, blank lines, final newline, and trailing spaces encoded immediately before several `\n` escapes.

## Spec 5

Canonical subcommand help is byte-exact as follows. Each shown block has a final newline. The first line of every block has one trailing ASCII space after the command name. The `<item type>` line in `list` has four trailing spaces after the placeholder.

```text
executable-vault 
create a vault or list vaults

USAGE:
    jt vault
    jt vault -l
    jt vault <vault name> <vault location>

ARGS:
    <vault name>        name for new vault
    <vault location>    absolute path to location of new vault

OPTIONS:
    -l            show vaults' location
    -h, --help    Print help information
```

```text
executable-note 
create a note

USAGE:
    jt note
    jt note [note name]

ARGS:
    <note name>    name for new note (to be created in the current folder)

OPTIONS:
    -h, --help    Print help information
```

```text
executable-folder 
create a folder

USAGE:
    jt folder
    jt folder [folder name]

ARGS:
    <folder name>    name for new folder (to be created in the current folder)

OPTIONS:
    -h, --help    Print help information
```

```text
executable-enter 
enter a vault

USAGE:
    executable enter <vault name>

ARGS:
    <vault name>    name of the vault to enter

OPTIONS:
    -h, --help    Print help information
```

```text
executable-open 
open a note (from the current folder)

USAGE:
    executable open <note name>

ARGS:
    <note name>    name of note to be opened

OPTIONS:
    -h, --help    Print help information
```

```text
executable-opdir 
open current folder in file explorer

USAGE:
    executable opdir

OPTIONS:
    -h, --help    Print help information
```

```text
executable-chdir 
change folder within current vault

USAGE:
    executable chdir <folder path>

ARGS:
    <folder path>    path to folder to switch to (from current folder)

OPTIONS:
    -h, --help    Print help information
```

```text
executable-list 
list items in current folder

USAGE:
    executable list [item type]

ARGS:
    <item type>    

OPTIONS:
    -h, --help    Print help information
```

## Spec 6

The remaining canonical subcommand help is also exact and ends in a newline:

```text
executable-remove 
remove an item

USAGE:
    executable remove <item type> <name>

ARGS:
    <item type>    remove a vault (or vl) | note (or nt) | folder (or fd)
    <name>         name of item to be removed

OPTIONS:
    -h, --help    Print help information
```

```text
executable-rename 
rename an item

USAGE:
    executable rename <item type> <name> <new name>

ARGS:
    <item type>    rename a vault (or vl) | note (or nt) | folder (or fd)
    <name>         name of item to be renamed
    <new name>     new name of item

OPTIONS:
    -h, --help    Print help information
```

```text
executable-move 
move an item

USAGE:
    executable move <item type> <name> <new location>

ARGS:
    <item type>       move a vault (or vl) | note (or nt) | folder (or fd)
    <name>            name of item to be moved
    <new location>    path to new location of item (current folder as root in case of note or
                      folder)

OPTIONS:
    -h, --help    Print help information
```

```text
executable-vmove 
move notes and folders to a different vault

USAGE:
    executable vmove <item type> <name> <vault name>

ARGS:
    <item type>     move a note (or nt) | folder (or fd)
    <name>          name of item to be moved
    <vault name>    name of vault to move the item to

OPTIONS:
    -h, --help    Print help information
```

```text
executable-config 
display, set or open config

USAGE:
    jt config <config type>
    jt config <config type> [config value]

ARGS:
    <config type>     name of config item to display or set
    <config value>    pass a value if config needs to be updated

OPTIONS:
    -h, --help    Print help information
```

Alias help may identify the alias in its heading/usage, but must otherwise expose the same description, `USAGE:`, argument information, `OPTIONS:`, and `-h, --help` material as canonical help.

## Spec 7

Vault, note, folder, and rename-target names must be validated before filesystem mutation. Reject a name containing any of `*`, `\\`, `/`, `?`, `%`, `:`, `|`, `"`, `<`, or `>`, including traversal strings such as `../escape`, with `{R}error{Z}: invalid name\n`, stdout, status 0. Hyphens, underscores, digits, and mixed case are valid for all item kinds; vault names of at least 100 characters are valid; and note/folder names may also contain spaces and Unicode. Vault names may contain ASCII spaces, including a name composed entirely of spaces; at a valid location these names follow the normal vault-creation path and print the Spec 8 success response. A zero-length note or folder name is not rejected as `invalid name`; its operation-specific behavior is defined in Spec 12. A valid name is preserved exactly in messages and filenames.

A note's on-disk name is its supplied name with one `.md` suffix appended, unless the supplied name already ends with `.md`. Thus `note x` creates `x.md`, while `note x.md` creates `x.md`, not `x.md.md`. Operations that address a note use the same normalization.

## Spec 8

Runtime/application messages use stdout and an exit status of 0, even when the message reports an error; stderr is empty. Success names and values are blue. Exact success templates are:

```text
vault {B}{name}{Z} created
entered {B}{name}{Z}
note {B}{name}{Z} created
folder {B}{name}{Z} created
folder changed
note {B}{old}{Z} renamed to {B}{new}{Z}
folder {B}{old}{Z} renamed to {B}{new}{Z}
vault {B}{old}{Z} renamed to {B}{new}{Z}
note {B}{name}{Z} removed
folder {B}{name}{Z} removed
vault {B}{name}{Z} removed
note {B}{name}{Z} moved
folder {B}{name}{Z} moved
vault {B}{name}{Z} moved
note {B}{name}{Z} moved to vault {B}{vault}{Z}
folder {B}{name}{Z} moved to vault {B}{vault}{Z}
```

Every runtime error begins `{R}error{Z}: ` and ends in `\n`. The error text and precedence needed by operations are detailed below.

## Spec 9

`vault <name> <location>` creates a vault. `location` is the existing parent directory, and the actual vault root is `location/name`. The location must be absolute; otherwise emit `specified path isn't absolute`. It must already exist; otherwise emit `couldn't find the path specified`. Do not create missing location parents. Reject an already-registered name with `vault NAME already exists`.

On success create the root directory and its `.jot` directory. Create `.jot/data` as valid TOML containing at least these exact logical fields and values:

```text
name = '<name>'
location = '<location>'
folder = ''
```

The global registry maps the vault name to the supplied parent location, not to `location/name`. For example, with one non-current vault it serializes as `[vaults]\nNAME = 'LOCATION'\n`. TOML must remain valid and must quote/escape supported names, Unicode, editor strings, and paths correctly.

## Spec 10

`vault` lists registered vaults and `vault -l` adds locations. With none registered, stdout is exactly empty. A non-current row is `   NAME\n`; a current row is `👉 {B}NAME{Z}\n`. With `-l`, append ` \t LOCATION` before the newline; the current vault's name remains blue and a non-current name is uncolored. All registered vaults must appear exactly once. The registry persists additions, removal, renames, moves, and the current marker.

`-l` is valid only on `vault`. Supplying `-l` globally or to `list` is a syntax error. Supplying it twice, as `vault -l -l` or `vault -ll`, is exit 2 and reports that `'-l' was provided more than once`. `vault --nonexistent` reports `Found argument '--nonexistent'` and suggests `If you tried to supply \`--nonexistent\` as a value` and `use \`-- --nonexistent\``. After `--`, `-l` is treated as a vault-name value, so `vault -- -l` reports missing `<vault location>`. `vault -l=1` reports `Found argument '-='`.

## Spec 11

`enter NAME` requires a registered vault. If absent, emit `vault NAME doesn't exist`. If it is already current, emit `already in vault NAME`. Otherwise make it the current vault persistently, preserve every other vault, and emit the success message from Spec 8. Subsequent independent processes operate on that current vault.

Every vault has a persistent current-folder path relative to its root, initially the empty string. Entering a newly created vault therefore selects its root. Current-vault and current-folder state must survive process boundaries. Renaming or moving the active vault must leave it active and operational; renaming updates its name in global and per-vault state while retaining its folder path. Removing the active vault clears the global current value, so later current-vault operations report `not inside a vault`.

## Spec 12

`note NAME` requires an active vault and creates a new empty regular Markdown file in the vault's current folder. The file contents are exactly empty. Reject an existing note of that name without modifying it, using `a note named NAME already exists in this location`. Notes in different folders or vaults are independent. Multiple notes may coexist, and arbitrary existing note contents must be preserved by every rename and move.

An empty note name is a compatibility edge case. It prints the normal success response `note {B}{Z} created` and extension normalization is applied to the current folder path itself: the program creates an empty `.md` sibling of that folder, not a `.md` child inside it. Thus, at the root of vault `V` whose registered parent is `LOCATION`, `note ""` creates `LOCATION/V.md`. In a current folder `sub`, it creates `sub.md` beside `sub`. Repeating the operation when that sibling exists emits `{R}error{Z}: a note named  already exists in this location\n`.

`folder NAME` similarly requires an active vault and creates a directory in the current folder. Reject an existing folder with `a folder named NAME already exists in this location`. Nested folder creation is achieved by creating a folder, changing into it, and creating another. A folder and all nested content must remain an ordinary filesystem hierarchy.

An empty folder name resolves to the existing current folder. It therefore emits `{R}error{Z}: a folder named  already exists in this location\n` and does not create a directory.

For `note`, `folder`, `list`, `open`, `chdir`, and note/folder forms of `remove`, `rename`, or `move`, absence of an active vault produces exactly `{R}error{Z}: not inside a vault\n`. The `vmove` validation order is the exception described in Spec 18: it checks whether the target vault is registered before checking for an active vault.

## Spec 13

`chdir PATH` resolves a relative path from the active vault's current folder. It accepts folder names, slash-separated descendants, `.`, `..`, and multi-level combinations such as `b/c`, `../..`, and `../../..`. The resolved target must exist at or below the vault root, but the executable does not require it to be a directory. In particular, a regular file target is accepted: `chdir file` prints `folder changed` and persists that file's root-relative path (for example, `folder = 'here/file'`) in `.jot/data`. The target must never cross above the root, even after normalization.

On success persist the root-relative target to `.jot/data` and print `folder changed`. If the path cannot be found, emit `couldn't find the path specified`; if it crosses above the root, emit `path crosses the bounds of vault`; if it resolves to the existing current folder (for example `.`), emit `new location is same as old location`. A failed navigation must not change the saved folder. Navigation and subsequent creation/list/mutation may be arbitrarily deep (at least five levels).

## Spec 14

An unfiltered `list` prints a recursive UTF-8 tree rooted at the active current folder. The first line is exactly the vault name at root, or `VAULT > relative/path` below root, using `/` separators. An empty location prints only that header plus `\n`.

Entries in each unfiltered directory are rendered in the filesystem iterator's discovery order, without sorting and without substituting creation order. Each underlying child is assigned `├── ` except the final underlying child, which receives `└── `. The vault root's `.jot` metadata entry participates in that ordering and branch assignment and is then suppressed from the unfiltered output. Consequently the last visible root child can retain `├── ` when the hidden `.jot` entry follows it. Descendant prefixes use the conventional continuation strings `│   ` and `    `. Traverse folders recursively. Folder names are plain. Note names omit the final `.md` suffix and are wrapped in `{B}` and `{Z}`.

For example, after creating `note1`, then `note2.md`, then `folder1`, then creating `folder1/sub`, `folder1/inside.md`, and `folder1/sub/deep.md` in that order, the exact unfiltered output is:

```text
vault-name
├── folder1
│   ├── {B}inside{Z}
│   └── sub
│       └── {B}deep{Z}
├── {B}note2{Z}
├── {B}note1{Z}
```

Filters are not recursive. `note`/`nt` shows only note files that are direct children of the current folder and excludes every folder without traversing it. Thus a note at `docs/inside.md` is omitted when listing the vault root with `list note`. `folder`/`fd` shows only direct child directories, excludes notes, and includes the root's `.jot` directory when listing folders at the vault root. Filtered entries retain filesystem discovery order. The aliases produce byte-identical output to the corresponding canonical forms.

## Spec 15

`remove TYPE NAME` operates on a registered vault for vault type, or on an item in the active current folder for note/folder types. Removing a note deletes its normalized `.md` file. Removing a folder recursively deletes it and every nested file/subfolder. Removing a vault recursively deletes its entire `LOCATION/NAME` directory and removes its registry entry. It must not affect unrelated items or vaults.

Missing sources produce:

- `vault NAME doesn't exist` for a vault,
- `note NAME not found` for a note, and
- `folder NAME not found` for a folder.

Using the wrong type addresses that type and therefore reports it missing; for example a note named `x` does not make folder `x` exist.

## Spec 16

`rename TYPE OLD NEW` renames the source in place. Notes retain the single `.md` suffix, folders retain their entire tree and file contents, and vaults retain all content while the physical root changes from `LOCATION/OLD` to `LOCATION/NEW`. Update the global registry and `.jot/data`; if the vault was current, update the current name and keep the active folder usable.

For note/folder sources missing in the current folder, emit `note OLD not found` or `folder OLD not found`. For a missing vault, emit `vault OLD doesn't exist`. For note/folder `OLD == NEW`, emit `new name is same as old name`. For a same-name vault rename, the vault collision rule wins and emits `vault NEW already exists`. A new vault name already registered also emits `vault NEW already exists`.

Renaming a note onto an existing note succeeds, replaces the destination, leaves only the new name, and prints the normal success message. Renaming a folder onto an existing empty folder likewise replaces that empty destination. If the existing destination folder is nonempty, however, the rename fails with `{R}error{Z}: undefined error: Directory not empty (os error 39)\n`; both the source tree and destination tree remain intact. This is distinct from creation and move collision behavior. Validate `NEW` using Spec 7 before mutation.

## Spec 17

`move TYPE NAME DESTINATION` performs a same-vault filesystem move for notes/folders and a parent-location move for vaults.

For note/folder, resolve `DESTINATION` from the active current folder, using the same normalization and vault-boundary rules as `chdir`. The destination must already be an existing directory. Move the named source from the current folder into it without changing the current-folder state. A trailing slash is allowed. Preserve file contents and recursive folder contents. Destinations such as `../`, `../archive/`, `level1/level2`, and nested siblings must work. Success prints `note NAME moved` or `folder NAME moved`.

For vault, `DESTINATION` must be an absolute existing parent directory. Move `OLD_LOCATION/NAME` to `DESTINATION/NAME`, preserve `.jot` and all content, and replace the registry/per-vault location with `DESTINATION`. The vault remains current if it was current.

Errors are:

- nonexistent note/folder destination: `couldn't find the path specified`;
- nonexistent absolute vault destination: `no such file or directory (os error 2)`;
- destination normalization above vault root: `path crosses the bounds of vault`;
- destination is the source's current parent: `new location is same as old location`;
- source note/folder missing during a filesystem move: `no such file or directory (os error 2)`;
- an identically named destination item exists: `a note named NAME already exists in this location` or the corresponding `folder` wording;
- source vault missing: `vault NAME doesn't exist`;
- relative vault destination: `specified path isn't absolute`.

Validate without partially moving or deleting the source on errors.

## Spec 18

`vmove TYPE NAME TARGET_VAULT` moves a note or folder from the active current folder to the root of another registered vault. It never changes the active vault or current folder. A note is moved as its normalized Markdown file. A folder is moved recursively with all content. Remove the source and create the destination filesystem entry, preserving all bytes, then print the appropriate `moved to vault` message from Spec 8.

If the destination vault is not registered, return a runtime error and do not move anything. For compatibility, this diagnostic mistakenly substitutes the source item's name rather than the requested target name: `vault SOURCE_ITEM doesn't exist` (for either notes or folders). A missing source that reaches the filesystem move reports `no such file or directory (os error 2)`. Item aliases `nt` and `fd`, and command alias `vm`, behave identically.

Target-vault registration is checked before active-vault state. Therefore `vmove folder x v` with no active vault and no registered `v` emits `{R}error{Z}: vault x doesn't exist\n`. If `v` is registered but there is still no active vault, the same invocation instead emits `{R}error{Z}: not inside a vault\n`.

## Spec 19

`config editor` prints `editor: {B}VALUE{Z}\n`; `config conflict` prints `conflict: {B}true-or-false{Z}\n`, using lowercase booleans. Adding one value sets and persists the field, preserving the other field, and prints `set {B}FIELD{Z} to {B}VALUE{Z}\n`.

Editor values are one argument and must be preserved exactly, including empty strings, spaces, quotes, long values, and Unicode. Serialize a valid TOML string. Conflict values accept exactly lowercase `true` or `false` and serialize as TOML booleans. Repeated reads/writes must not corrupt or truncate the file, and the last write wins.

An invalid config type is a parser error on stderr, exit 2, exactly:

```text
error: "VALUE" isn't a valid value for '<config type>'
	[possible values: editor, conflict]

For more information try --help
```

More than one value, as in `config editor vim emacs`, is exit 2 and reports `Found argument 'emacs' which wasn't expected, or isn't valid in this context`, followed by the two config usage lines and the help hint. With no config arguments, attempt to open the config file in the configured editor; if the default editor is unavailable, report an error containing `editor not found` rather than treating this as a missing parser argument.

## Spec 20

An invalid conflict boolean intentionally has panic-compatible behavior: return a nonzero code (101 is expected), do not change/corrupt the config, and write a panic diagnostic to stderr. It must contain `panicked at src/state/config.rs`, `ParseBoolError`, and `called \`Result::unwrap()\` on an \`Err\` value`. Compatibility output has this form (the decimal process identifier may vary):

```text

thread 'main' (PID) panicked at src/state/config.rs:<error location>:
called `Result::unwrap()` on an `Err` value: ParseBoolError
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

This applies to values such as `invalid`, `notabool`, and case variants such as `True`; parsing is not case-insensitive. If an existing config file or vault registry is malformed TOML, startup must fail nonzero with a panic-style diagnostic containing both `panicked` and `couldn't parse data`, rather than silently resetting user data.

## Spec 21

`open NAME` requires an active vault and addresses only a note in its current folder. If missing, emit `note NAME not found`. If present, attempt to launch the configured editor on that note. If the configured executable cannot be launched, report a stdout runtime error mentioning the editor/not-found condition without hanging.

The `op` spelling routes to the same `open` behavior. `opdir`/`od` must be recognized by the parser and expose the help contract in Specs 4–6.

All tested invocations must complete promptly in noninteractive environments. Commands that merely create, list, navigate, rename, remove, or move content must never wait for stdin.

## Spec 22

Parser edge behavior is part of the interface. Unexpected extra positionals are rejected rather than ignored: for example, `open note extra` reports `Found argument 'extra' which wasn't expected`, and `list --bogus` reports `Found argument '--bogus'`. A global flag that belongs only to a subcommand is rejected. Syntax errors use nonzero status and stderr, while every validation/filesystem error explicitly described in Specs 7–18 uses status 0 and stdout.

Every operation must preserve consistency across a long workflow: different vaults keep independent contents; switching vaults does not mix files; nested traversal, moves, and renames compose; recursive folder moves/renames retain file contents; removing one vault does not alter others; and all registry, current-vault, location, name, and current-folder state remains valid TOML and agrees with the filesystem after the process exits.
