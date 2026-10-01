# `executable`: default-application manager

## Spec 1: Deliverable and compatibility target

The required artifact is one runnable file named exactly `executable` at the workspace root. It is a command-line program compatible with handlr 0.6.4. All behavior below is observable through process arguments, environment variables, standard streams, exit status, files, and launched desktop-entry commands. It must not require repository source code or another project-built command.

Unless an error is specified, successful mutating commands exit 0 and write nothing to stdout or stderr. Text output uses UTF-8 and `\n` line endings.

## Spec 2: Top-level command line

The public subcommands, in order, are:

`list`, `open`, `set`, `unset`, `launch`, `get`, and `add`.

There is also a callable but hidden `autocomplete` subcommand. The accepted forms are:

```text
executable list [-a|--all]
executable open <paths>...
executable set <mime-or-extension> <handler.desktop>
executable unset <mime-or-extension>
executable launch <mime-or-extension> [args]...
executable get [--json] <mime-or-extension>
executable add <mime-or-extension> <handler.desktop>
executable autocomplete [-m] [-d]
```

Options may precede or follow a positional where unambiguous, so both `get --json text/plain` and `get text/plain --json` work. `--` ends option parsing; this is required for positional values beginning with `-`. Unknown options, extra positionals, and missing required positionals are rejected. `-a` and `--all` are confined to `list`; `--json` is confined to `get`. Every subcommand accepts `-h`/`--help` and `-V`/`--version`. Compatible short options may be combined, such as `list -aV`.

No arguments prints the main usage material and exits 2. Unknown subcommands and argument-validation errors also exit 2. Unknown subcommands are described as unrecognized/unexpected, show usage and a `--help` hint, and for a close spelling such as `nope` include a “did you mean” suggestion.

## Spec 3: Version and help text

Top-level `-V` and `--version` print exactly:

```text
handlr 0.6.4
```

The normal top-level help is exactly:

```text
handlr 0.6.4

USAGE:
    executable <SUBCOMMAND>

FLAGS:
    -h, --help       Prints help information
    -V, --version    Prints version information

SUBCOMMANDS:
    list      List default apps and the associated handlers
    open      Open a path/URL with its default handler
    set       Set the default handler for mime/extension
    unset     Unset the default handler for mime/extension
    launch    Launch the handler for specified extension/mime with optional arguments
    get       Get handler for this mime/extension
    add       Add a handler for given mime/extension Note that the first handler is the default
```

The output ends in a newline, goes to stdout, and leaves stderr empty. `-h` has the same meaning. A top-level help flag takes precedence over a later invalid option.

Each public subcommand has distinct help on stdout, exits 0, includes its description, a `USAGE:` and `FLAGS:` section, and documents `-h, --help` and `-V, --version`. Its usage line is exactly one of:

```text
    executable list [FLAGS]
    executable open <paths>...
    executable set <mime> <handler>
    executable unset <mime>
    executable launch <mime> [args]...
    executable get [FLAGS] <mime>
    executable add <mime> <handler>
```

In `launch` help, an `ARGS:` section occurs after `USAGE:` and before `FLAGS:` and contains these two argument labels in this order:

```text
ARGS:
    <mime>
    <args>...
```

`list` help documents `-a, --all`; `get` help documents `--json`. A subcommand version request prints a line beginning `executable-<subcommand> ` and exits 0 (the compatibility output has no numeric version after that space).

## Spec 4: XDG locations and initialization

Honor the XDG base-directory environment. The writable association file is:

```text
$XDG_CONFIG_HOME/mimeapps.list
```

and the program configuration is:

```text
$XDG_CONFIG_HOME/handlr/handlr.toml
```

When `XDG_CONFIG_HOME` is absent, use the standard user configuration directory (`$HOME/.config` on Unix). Desktop entries are discovered by filename under `$XDG_DATA_HOME/applications` and the `applications` subdirectory of every directory in colon-separated `$XDG_DATA_DIRS`, with the normal Unix XDG defaults when those variables are absent.

The first ordinary invocation, including `list`, creates missing parent directories, an empty `mimeapps.list`, and this exact default TOML file:

```toml
enable_selector = false
selector = "rofi -dmenu -i -p 'Open With: '"
```

Existing valid TOML is read but not reformatted or overwritten merely by running a command.

## Spec 5: `mimeapps.list` data model and parsing

Recognize the case-sensitive INI sections `[Default Applications]` and `[Added Associations]`. Wrong-case section names are ignored. A section header with trailing whitespace is malformed and lookup fails. Ignore blank lines and `#` comments. An association has the form:

```text
mime/type=first.desktop;second.desktop;
```

Handler lists are semicolon-separated and may contain a trailing semicolon. Empty handlers and syntactically invalid MIME keys are ignored when reading. Duplicate handler names may exist on disk but are deduplicated, preserving first occurrence, for lookup and display. Duplicate MIME keys produce only one displayed association. A referenced handler that cannot be resolved to a valid desktop entry is excluded from displayed associations and cannot be returned by `get`.

Lookup priority is: exact MIME in Default Applications, matching major-type wildcard in Default Applications, exact MIME in Added Associations, then any available system association. A wildcard row in Added Associations is not a fallback for a concrete MIME: for example, `text/*=wild.desktop;` there does not satisfy a lookup for `text/html`. The first valid handler in the selected list is the default unless the selector described below is active.

## Spec 6: Canonical association-file writes

After a successful `set` or `add`, serialize the user association file in this canonical shape:

```ini
[Added Associations]
<preserved added-association entries, sorted by MIME>

[Default Applications]
<default entries, sorted lexicographically by normalized MIME>
```

Every stored handler is followed by `;`, including the last. There is exactly one section of each kind, one entry per MIME, and a final newline. If Added Associations is empty, its header is followed immediately by the separating blank line. For example, one mapping is exactly:

```ini
[Added Associations]

[Default Applications]
text/plain=vim.desktop;
```

Writing one MIME preserves unrelated MIME mappings and preserves the contents of Added Associations. The commands in this interface modify only Default Applications; they do not add new rows to Added Associations. Merely initializing an absent association file, or unsetting from a wholly absent/empty file, leaves that file empty rather than adding section headers.

## Spec 7: MIME-or-extension inputs

For `set`, `add`, `get`, `unset`, and `launch`, an input beginning with `.` is a filename extension and is resolved through the same MIME database represented by `assets/autocomplete-mimes.txt` (for example `.txt` to `text/plain`, `.png` to `image/png`, `.mp3` to `audio/mpeg`). A bare `.` or unknown extension is invalid.

Otherwise parse a MIME value. It must have one nonempty type, `/`, and one nonempty subtype, with MIME token characters only. Accept ordinary, vendor, experimental, structured-suffix, scheme, inode, message, multipart, and model values, including examples such as `a/b`, `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/rss+xml`, `application/x-wine.extension.ini`, `x-scheme-handler/https`, and `inode/directory`. Accept a subtype wildcard such as `text/*`. Normalize type and subtype to lowercase for storage and comparison.

A parameter without intervening whitespace, such as `text/plain;charset=utf-8`, is accepted and reduced to its essence `text/plain`. The whitespace-bearing operand `text/plain; charset=utf-8` is also accepted rather than producing a value error: `unset 'text/plain; charset=utf-8'` exits 0 silently. For lookup/removal it does not match an existing unparameterized `text/plain` row. Reject whitespace within the type or subtype (such as `text /plain` or `text/ plain`), missing or additional slashes, empty components, control characters, and invalid token characters.

For wildcard resolution in Default Applications, `type/*` matches valid concrete MIME values having the same major type only. An exact Default Applications association always beats its wildcard, regardless of insertion order. Removing that exact association exposes any matching Default Applications wildcard fallback.

## Spec 8: Desktop-entry discovery and validation

A handler operand is a desktop-entry filename, not a traversal path. Search the XDG application directories by that filename. Filenames can contain Unicode, hyphens, underscores, dots, and digits and must round-trip unchanged. Reject an empty name, a path such as `../evil.desktop`, or a filename not found in the search locations with exit 2.

Parse freedesktop desktop files as case-sensitive key/value data. A usable file must contain a `[Desktop Entry]` section, a nonempty `Name`, and a nonempty `Exec`. `Name` and `Exec` in another case do not satisfy these requirements. If the unqualified `Name` occurs more than once in `[Desktop Entry]`, use the last occurrence. Preserve surrounding whitespace in its value; the value `Name= 名称 ` is exposed as ` 名称 ` rather than being trimmed. Localized `Name[locale]` variants do not replace the unqualified `Name`.

`Version`, `Icon`, `MimeType`, `Categories`, `Terminal`, `Comment`, `NoDisplay`, `TryExec`, `Actions`, `DBusActivatable`, and further sections are optional and must not make an otherwise usable entry invalid. `MimeType` and `Categories` are semicolon lists; they may be empty and may omit or include the trailing semicolon. The handler need not declare the MIME for which the user assigns it. Accept quoted and complex `Exec` text, environment prefixes, pipes, redirects, and the `%f`, `%F`, `%u`, and `%U` field codes. Only the exact value `Terminal=true` enables terminal behavior; `false` and `True` do not.

The bundled `assets/cmus.desktop` is a valid reference entry named `cmus-remote` with MIME values `audio/mp3` and `audio/ogg`. The other bundled files are MIME-detection examples: `assets/rust.vim` is plain text and `assets/SettingsWidgetFdoSecrets.ui` is a Qt Designer UI document.

## Spec 9: `set`, `add`, and `unset`

`set MIME HANDLER` validates both operands and replaces the complete Default Applications handler list for the normalized MIME with exactly that handler.

`add MIME HANDLER` validates both operands and appends the handler to the Default Applications list, preserving insertion order. If no mapping exists, it creates one and the first added handler becomes the default. Repeated `add` of the same handler is retained repeatedly in the serialized file for compatibility, but lookup and display deduplicate it. `add` after `set` appends; `set` after one or more `add` operations replaces them all.

`unset MIME` removes the normalized MIME row from Default Applications only. It preserves Added Associations and every unrelated default mapping. It is idempotent: unsetting an absent association succeeds silently, including repeated calls, and creates an empty `mimeapps.list` if needed.

These operations work independently for many MIME keys and handler lists (at least 30 MIME rows and 20 handlers for one row) and remain persistent across separate process invocations.

## Spec 10: `get`

`get MIME` performs the priority lookup from requirement 5, validates the selected desktop entry, prints only its unchanged desktop filename followed by a newline, and exits 0.

`get --json MIME` prints one compact JSON object, followed by a newline, with exactly these keys in this order:

```json
{"handler":"vim.desktop","name":"Vim","cmd":"vim "}
```

`handler` is the desktop filename, `name` is its unqualified Name, and `cmd` is the parsed Exec command with launch field codes expanded for an empty argument list. JSON escaping must preserve Unicode and quotes correctly. Shell quoting in Exec is removed in the rendered command; for example `/usr/bin/app --title="My App" %u` renders as `/usr/bin/app --title=My App`. As a compatibility quirk, an Exec consisting of an executable plus only a `%u`/`%U` argument retains the separating trailing space (`vim %u` becomes `vim `); when fixed arguments precede the field code, no trailing space is retained (`/usr/bin/test-app --flag %u` becomes `/usr/bin/test-app --flag`). Plain and JSON modes must select the same handler.

## Spec 11: Optional handler selector

When `enable_selector` is false, or lookup yields only one valid handler, select the first handler without running the configured selector. When it is true and lookup yields multiple valid handlers:

- parse `selector` as a command plus quoted arguments;
- run it with the candidate desktop entries' display Names on stdin, in handler priority order, joined by a single newline byte between adjacent Names and with no newline after the final Name;
- allow multiword Names and match the selector's trimmed output back to the corresponding entry;
- forward selector stderr to the command's stderr; and
- if the selector process cannot be spawned, exit 1 with empty stdout and the not-found runtime diagnostic from requirement 18 rather than selecting a handler.

Thus a selector such as `tail -1` chooses the last handler and `head -n 1` chooses the first.

Malformed TOML is not silently replaced. It terminates nonzero with a parse/panic diagnostic. For the invalid file

```toml
enable_selector = invalid_value_not_boolean
selector = [this is not a string
```

the compatibility stderr, apart from the runtime numeric thread ID replacing `PID`, is exactly:

```text

thread 'main' (PID) panicked at src/config.rs:<error location>:
called `Result::unwrap()` on an `Err` value: BadTomlData(Error { inner: ErrorInner { kind: UnquotedString, line: Some(0), col: 18, at: Some(18), message: "", key: [] } })
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

## Spec 12: `list` table format

Plain `list` prints Default Applications only. It is a headerless, two-column Unicode box table. MIME rows are sorted lexicographically. Valid handler filenames are joined in priority order with `, `. Column widths fit their contents with one space of padding on either side; there are no horizontal separators between data rows. Examples:

```text
┌──┐
│  │
└──┘
```

```text
┌────────────┬────────────────────────────┐
│ text/plain │ app1.desktop, app2.desktop │
└────────────┴────────────────────────────┘
```

The exact border characters are `┌─┬┐`, `│`, and `└─┴┘`; every rendered line ends at its right border. Output remains in this table form when redirected. At the default noninteractive width of 80 columns, overly long cell text is clipped and ends in `+`; for example five handlers render the second cell as `app1.desktop, app2.desktop, app3.desktop, app4.desktop, app5.d+`.

Malformed/empty mappings and mappings whose desktop files do not exist are omitted. Wildcard and scheme keys are displayed literally. Multiple handler occurrences are deduplicated for this view.

## Spec 13: `list --all`

`list -a` and `list --all` are identical. They print labeled tables in this order:

1. `Default Apps`
2. `Added Associations`, only when that section has displayable rows
3. `System Apps`

There are no extra blank lines between a label and its table or between one table and the next label. Even when everything is empty, Default Apps and System Apps are shown:

```text
Default Apps
┌──┐
│  │
└──┘
System Apps
┌──┐
│  │
└──┘
```

Each constituent table follows requirement 12. The System Apps table is formed by grouping valid discovered desktop entries under the valid MIME values declared in their `MimeType` fields; it is also the final lookup fallback described in requirement 5.

## Spec 14: Opening paths and URLs

`open` requires one or more operands. For a filesystem path, verify/access the path and detect its MIME using both content and filename information. At minimum, recognize text files as `text/plain`, HTML as `text/html`, a shebang shell script as `application/x-shellscript`, and directories as `inode/directory`. Resolve symlinks normally. A `file://` URL is converted to its local path and handled as a file.

For another valid URL, map its lowercased scheme to `x-scheme-handler/<scheme>`; this includes `http`, `https`, and `ftp`. Preserve URL components, while normalizing a domain-only URL such as `http://example.com` to `http://example.com/` before passing it to the handler.

Look up a handler independently for every operand, group operands selecting the same handler, and start the handler command. For an Exec containing `%F`, pass a same-handler group in one invocation. For `%f`, invoke once per file and substitute exactly one path each time. `%u` supplies the URL for a single-URL invocation. Different selected handlers are all started. A successful `open` exits 0 with empty stdout and stderr.

## Spec 15: `launch` and process errors

`launch MIME [args]...` looks up the handler for the explicit MIME/extension and starts its Exec with the optional arguments; an empty argument list is valid. The `--` separator permits dash-prefixed arguments. A URL-like argument is passed to a `%u` handler. If the desktop Exec executable cannot be spawned, exit nonzero.

For a `Terminal=true` entry, use the configured `x-scheme-handler/terminal` desktop entry to form the command. If no terminal handler/emulator is available, fail nonzero with a diagnostic mentioning the terminal or not-found condition.

## Spec 16: Autocomplete output

`autocomplete` is absent from top-level help but callable:

- With no flags, exit 0 and produce no output.
- With `-m`, write exactly the bytes of `assets/autocomplete-mimes.txt`. That normative file has 2,153 newline-terminated entries and SHA-256 `2454d74ab1ee141c4aaf787cce26be7077ce3c971cac7c55fd937deb05403d34`. Extensions (including duplicates in the corpus) come first and retain their leading dot, followed by MIME values. It includes the custom values `inode/directory`, `x-scheme-handler/http`, `x-scheme-handler/https`, and `x-scheme-handler/terminal`.
- With `-d`, enumerate every valid discovered desktop entry once as `<filename>\t<Name>\n`. Each line has exactly one tab, but the unqualified `Name` value is emitted verbatim, including its leading or trailing spaces; for example `Name= 名称 ` produces `Ünicode.desktop\t 名称 \n`. Entries without both a valid filename and Name are omitted. In the baseline environment, the system entry is `python3.10.desktop\tPython (v3.10)\n`; valid entries added under the XDG data locations are included as well.
- If both flags occur in either order, `-d` takes precedence.

Autocomplete help is:

```text
executable-autocomplete 

USAGE:
    executable autocomplete [FLAGS]

FLAGS:
    -d               
    -m               
    -h, --help       Prints help information
    -V, --version    Prints version information
```

Its version output is exactly `executable-autocomplete ` followed by a newline.

## Spec 17: Parse-error formatting

Argument and value errors go only to stderr and exit 2. Missing required arguments use this exact layout, substituting the relevant argument lines and usage:

```text
error: The following required arguments were not provided:
    <mime>
    <handler>

USAGE:
    executable set <mime> <handler>

For more information try --help
```

The corresponding usages are `get [FLAGS] <mime>`, `open <paths>...`, `launch <mime> [args]...`, `unset <mime>`, and `add <mime> <handler>`. When `get` is invoked with only its JSON flag (`get --json`), however, its missing-argument usage is exactly `executable get <mime> --json`. An unexpected value or option uses:

```text
error: Found argument '<value>' which wasn't expected, or isn't valid in this context

If you tried to supply `<value>` as a PATTERN use `-- <value>`

USAGE:
    <applicable usage>

For more information try --help
```

MIME value errors have the wrapper `error: Invalid value for '<mime>': <detail>`, a blank line, and `For more information try --help`. Required exact details include:

| Input | Detail |
|---|---|
| `.` | `could not figure out the mime type of '.'` |
| unknown `.xyzzy_unknown_ext_12345` | `could not figure out the mime type of '.xyzzy_unknown_ext_12345'` |
| `text` or `image` | `mime parse error: a slash (/) was missing between the type and subtype` |
| `text/` or `image/` | `bad mime: <input>` |
| `/` | `mime parse error: an invalid token was encountered, 2F at position 0` |
| `text//plain` | `mime parse error: an invalid token was encountered, 2F at position 5` |
| `image//jpeg` | `mime parse error: an invalid token was encountered, 2F at position 6` |
| `text/plain/extra` | `mime parse error: an invalid token was encountered, 2F at position 10` |
| `invalid@mime` | `mime parse error: an invalid token was encountered, 40 at position 7` |
| `text /plain` | `mime parse error: an invalid token was encountered, 20 at position 4` |
| `text/ plain` | `mime parse error: an invalid token was encountered, 20 at position 5` |

A missing handler is exactly:

```text
error: Invalid value for '<handler>': no handlers found for 'nonexistent.desktop'

For more information try --help
```

A malformed desktop file uses the same wrapper with detail `malformed desktop entry at <absolute-path>`.

## Spec 18: Runtime-error formatting

Lookup failure, an unconfigured URL scheme, an unconfigured launch MIME, failure to access a nonexistent input path, a configured association whose desktop entry cannot be resolved, and failure to spawn an enabled selector are runtime errors. They exit 1, write nothing to stdout, and use exactly:

```text
Error: Io(Os { code: 2, kind: NotFound, message: "No such file or directory" })
```

Successful `get` and `list` output goes to stdout. Successful `set`, `add`, `unset`, `open`, and `launch` are silent unless a configured selector child itself emits stderr as described above.
