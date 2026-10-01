# Atlas-compatible command-line executable

The required artifact is one executable file named `executable`. It is a command-line program whose command name in all usage and diagnostic text is `atlas`. Unless stated otherwise, successful commands exit 0, failures exit nonzero (normally 1), ordinary results go to standard output, diagnostics go to standard error, and every nonempty textual output ends with a newline. The byte-exact empty-source import result in Spec 18 is an explicit no-newline exception. Timing values and generated UTC timestamps are inherently variable.

## Spec 1

With no arguments, `-h`, `--help`, or `help`, print the following root help to stdout and exit 0 (with no stderr):

```text
Manage your database schema as code

Usage:
  atlas [command]

Available Commands:
  completion  Generate the autocompletion script for the specified shell
  help        Help about any command
  license     Display license information
  migrate     Manage versioned migration files
  schema      Work with atlas schemas.
  version     Prints this Atlas CLI version information.

Flags:
  -h, --help   help for atlas

Use "atlas [command] --help" for more information about a command.
```

`help schema`, `schema -h`, and `schema --help` are equivalent; likewise for `migrate` and nested topics such as `help migrate apply`. A group command without a child prints its group help and succeeds. Help takes precedence over normal required-flag validation, is deterministic under concurrent invocations, and is written only to stdout.

The postfix form `migrate help` also prints the exact `migrate` group help and exits 0 with no stderr.

`help help` prints the help command's own meta-help to stdout and exits 0 with no stderr:

```text
Help provides help for any command in the application.
Simply type atlas help [path to command] for full details.

Usage:
  atlas help [command] [flags]

Flags:
  -h, --help   help for help
```

## Spec 2

`version` prints exactly:

```text
atlas unofficial version - development
https://github.com/ariga/atlas/releases/latest
To download an official version, visit: https://atlasgo.io/getting-started#installation
```

`license` prints exactly:

```text
LICENSE
Atlas is licensed under Apache 2.0 as found in https://github.com/ariga/atlas/blob/master/LICENSE.
```

Both exit 0 and use stdout only. `version --help`/`version -h` prints help beginning `Prints this Atlas CLI version information.`, containing `Usage:\n  atlas version [flags]` and the help flag. `license --help` is exactly:

```text
Display license information

Usage:
  atlas license [flags]

Flags:
  -h, --help   help for license
```

There is no global `--version` or `-v` shortcut. With no separately applicable community-error suggestion (see Spec 11), `atlas --version` exits 1 with no stdout and exactly `Error: unknown flag: --version` on stderr. `atlas -v` exits 1 with no stdout and exactly `Error: unknown shorthand flag: 'v' in -v` on stderr. Neither diagnostic has a usage footer.

## Spec 3

The exact `schema` group help is:

```text
The `atlas schema` command groups subcommands working with declarative Atlas schemas.

Usage:
  atlas schema [command]

Available Commands:
  apply       Apply an atlas schema to a target database.
  clean       Removes all objects from the connected database.
  diff        Calculate and print the diff between two schemas.
  fmt         Formats Atlas HCL files
  inspect     Inspect a database and print its schema in Atlas DDL syntax.

Flags:
  -c, --config string        select config (project) file using URL format (default "file://atlas.hcl")
      --env string           set which env from the config file to use
  -h, --help                 help for schema
      --var <name>=<value>   input variables (default [])

Use "atlas schema [command] --help" for more information about a command.
```

The exact `migrate` group help is:

```text
'atlas migrate' wraps several sub-commands for migration management.

Usage:
  atlas migrate [command]

Available Commands:
  apply       Applies pending migration files on the connected database.
  diff        Compute the diff between the migration directory and a desired state and create a new migration file.
  hash        Hash (re-)creates an integrity hash file for the migration directory.
  import      Import a migration directory from another migration management tool to the Atlas format.
  lint        Run analysis on the migration directory
  new         Creates a new empty migration file in the migration directory.
  set         Set the current version of the migration history table.
  status      Get information about the current migration status.
  validate    Validates the migration directories checksum and SQL statements.

Flags:
  -c, --config string        select config (project) file using URL format (default "file://atlas.hcl")
      --env string           set which env from the config file to use
  -h, --help                 help for migrate
      --var <name>=<value>   input variables (default [])

Use "atlas migrate [command] --help" for more information about a command.
```

Every listed child has working `--help` and `help ...` routing. Child help identifies the full command and its usage, examples where applicable, exposed local flags, and a `Global Flags` block for `--config`, `--env`, and `--var` when applicable. Two accepted legacy/community-only flags are deliberately hidden from these pages: `schema apply --file` does not appear in `schema apply --help`, and `migrate diff --dry-run` does not appear in `migrate diff --help`.

The following observed child-help details are required (all of these help invocations exit 0, write to stdout, and have no stderr):

- `schema inspect --help` has an `Examples:` section containing `mysql://`, `postgres://`, and `sqlite://` URL examples.
- `schema apply --help` has an `Examples:` section containing a credential-bearing `mysql://user:pass@localhost/dbname` example. Its flags include the combined label `-s, --schema strings`, and `--dry-run` is described as `print SQL without executing it`.
- `schema diff --help` says it `calculates the difference in their schemas` and has an `Examples:` section.
- `schema clean --help` begins `'atlas schema clean' drops all objects in the connected database and leaves it in an empty state.` and has an `Examples:` section.
- `schema fmt --help` says it formats all `".hcl"` files under the given paths.
- `migrate apply --help` has an `Examples:` section. It describes `--baseline` as `start the first migration after the given baseline version`, `--tx-mode` as `set transaction mode [none, file, all]`, and `--exec-order` as `set file execution order [linear, linear-skip, non-linear]`.
- `migrate diff --help` has an `Examples:` section containing a `docker://` dev-database URL.
- `migrate import --help` has an `Examples:` section whose source URL contains `format=liquibase`.
- `migrate hash --help` says the integrity hash is stored in the `atlas.sum` file.
- `migrate validate --help` says it `computes the integrity hash sum of the migration directory`, explicitly says that it compares the result to the `atlas.sum` file, and has an `Examples:` section.
- `migrate new --help` begins `'atlas migrate new' creates a new migration according to the configured formatter without any statements in it.`
- `migrate status --help` says it reports information about the `current status` of a connected database.
- `migrate set --help` says it `edits the revision table` and has an `Examples:` section.

The exact `migrate apply --help` output is:

```text
'atlas migrate apply' reads the migration state of the connected database and computes what migrations are pending.
It then attempts to apply the pending migration files in the correct order onto the database. 
The first argument denotes the maximum number of migration files to apply.
As a safety measure 'atlas migrate apply' will abort with an error, if:
  - the migration directory is not in sync with the 'atlas.sum' file
  - the migration and database history do not match each other

If run with the "--dry-run" flag, atlas will not execute any SQL.

Usage:
  atlas migrate apply [flags] [amount]

Examples:
  atlas migrate apply -u "mysql://user:pass@localhost:3306/dbname"
  atlas migrate apply --dir "file:///path/to/migration/directory" --url "mysql://user:pass@localhost:3306/dbname" 1
  atlas migrate apply --env dev 1
  atlas migrate apply --dry-run --env dev 1

Flags:
  -u, --url string                [driver://username:password@address/dbname?param=value] select a resource using the URL format
      --dir string                select migration directory using URL format (default "file://migrations")
      --format string             Go template to use to format the output
      --revisions-schema string   name of the schema the revisions table resides in
      --dry-run                   print SQL without executing it
      --lock-timeout duration     set how long to wait for the database lock (default 10s)
      --baseline string           start the first migration after the given baseline version
      --tx-mode string            set transaction mode [none, file, all] (default "file")
      --exec-order string         set file execution order [linear, linear-skip, non-linear] (default "linear")
      --allow-dirty               allow start working on a non-clean database
  -h, --help                      help for apply

Global Flags:
  -c, --config string        select config (project) file using URL format (default "file://atlas.hcl")
      --env string           set which env from the config file to use
      --var <name>=<value>   input variables (default [])
```

## Spec 4

Command and flag parsing follows conventional case-sensitive GNU/Cobra-style rules. Long values work as `--flag value` and `--flag=value`; short values such as `-u value`, `-u=value`, `-s`, `-f`, and `-c` work where documented. Repeatable flags accumulate (`--schema`, `--to`, `--exclude`, `--var`), while a repeated scalar such as `--env` uses its last value. A bare `--` ends flag parsing, so later tokens are positional. Boolean flags consume no value. Value flags with no value fail with a diagnostic containing `flag needs an argument`; invalid durations, unsigned integers, enum values, or migration amounts fail rather than being ignored.

Unknown top-level commands are case-sensitive and fail on stderr, for example:

```text
Error: unknown command "unknowncommand" for "atlas"
Run 'atlas --help' for usage.
```

An unknown flag similarly fails. The parser's own diagnostic is one newline-terminated line and has no `Run 'atlas --help' for usage.` footer: `atlas --invalid-flag` reports `Error: unknown flag: --invalid-flag`; if several invalid flags are supplied it stops at the first, so `atlas --invalid1 --invalid2` reports only `Error: unknown flag: --invalid1`. A separately applicable stateful community-error suggestion from Spec 11 can follow that parser line. Numeric, punctuation-only, whitespace-containing, or reversed top-level command paths are unknown. In contrast, any otherwise-unrecognized immediate child supplied to the `schema` or `migrate` group (for example, `schema nonexistent`, `schema migrate`, or `migrate nonexistent`) is not an error: it prints that parent's exact group help to stdout, prints no stderr, and exits 0. It must not be dispatched as another command. Extra positional tokens after a recognized leaf do not turn the path into an unknown command before that leaf's own validation: specifically, `schema inspect extra` exits 1 with no stdout and stderr `Error: required flag(s) "url" not set`. `help unknowncommand` is another special case: it exits 0 and prints `Unknown help topic [`unknowncommand`]` followed by root usage, command list, and the normal help footer.

The following parser diagnostics and validation order are exact:

- `schema apply -u` exits 1 with stderr `Error: flag needs an argument: 'u' in -u`.
- Required-flag validation precedes schema-apply transaction-mode validation: `schema apply --tx-mode nope` exits 1 with no stdout and stderr `Error: required flag(s) "url" not set`. Once the required inputs are present, enum validation still precedes database and desired-file work; for example, `schema apply --tx-mode nope --url 'sqlite://file?mode=memory' --to file:///tmp/does-not-exist.hcl` exits 1 with no stdout and stderr `Error: unknown tx-mode "nope"`.
- For `schema apply --lock-timeout nope ...`, invalid duration parsing occurs before database work and stderr is `Error: invalid argument "nope" for "--lock-timeout" flag: time: invalid duration "nope"`.
- In `schema apply --url sqlite://file.db --to file://schema.sql --dev-url sqlite://dev?mode=memory --dry-run -- --not-a-flag`, the token following `--` is not parsed as either a flag or a subcommand. Execution proceeds to loading the target and exits 1 with `Error: stat schema.sql: no such file or directory` on stderr.

## Spec 5

The executable exposes these important command flags and validates required inputs before doing work:

- `schema inspect`: `-u/--url` (required unless supplied by a selected environment), repeatable `-s/--schema`, `--exclude`, `--format`, `--dev-url`.
- `schema apply`: required `-u/--url` and one of `--to` or hidden legacy `--file`; also `--dev-url`, `-s/--schema`, `--exclude`, `--include`, `--dry-run`, `--auto-approve`, `--tx-mode`, `--lock-timeout`, `--plan`, `--edit`, `--format`/`--log`.
- `schema diff`: required repeatable `--from/-f` and `--to`; also `--dev-url`, `--schema`, `--exclude`, `--include`, `--format`.
- `schema clean`: required `-u/--url`; also `--dry-run`, `--auto-approve`, `--format`.
- `migrate apply`: optional integer `[amount]`, `-u/--url`, `--dir` (default `file://migrations`), `--format`, hidden legacy `--log`, `--revisions-schema`, `--dry-run`, duration `--lock-timeout` (default `10s`), `--baseline`, `--tx-mode` in `none,file,all` (default `file`), `--exec-order` in `linear,linear-skip,non-linear`, and `--allow-dirty`.
- `migrate diff`: name plus `--to`, `--dev-url`, `--dir`, `--dir-format`, `--lock-timeout`, `--schema`, `--qualifier`, `--edit`, and hidden community-only `--dry-run`; missing `--to` or `--dev-url` fails.
- `migrate new/hash/validate`: `--dir` and `--dir-format`; `new` also has `--edit`; `validate` also has `--dev-url`.
- `migrate status/set`: `-u/--url`, `--dir`, `--dir-format`, `--revisions-schema`, and `--format` on status. `set` accepts at most one version.
- `migrate lint`: `--dir`, `--dir-format`, required `--dev-url`, mutually exclusive positive `--latest` and `--git-base`, plus `--git-dir` and `--format`.
- `migrate import`: `--from` and `--to` both default to `file://migrations`; it also accepts `--dir-format`.

Missing required flag errors name all missing flags. In particular, `migrate apply` with a usable directory but no URL exits 1 with exactly `Error: required flag "url" not set`; `migrate diff` with neither required state flag reports exactly `Error: required flag(s) "to", "dev-url" not set`. Other command forms include `Error: required flag(s) "from", "to" not set` and `Error: one of flag(s) "file" or "to" is required`. `migrate import` is not one of those required-flag cases: with neither endpoint flag, it resolves its default `file://migrations` source and, when that directory is absent, exits 1 with the ordinary error `Error: sql/migrate: stat migrations: no such file or directory` (plus the first-error suffix from Spec 11 when applicable). An explicitly supplied empty `--url=` is treated as absent. In particular, `schema apply --url=` exits 1 with no stdout and exactly `Error: required flag(s) "url" not set` on stderr. Command-specific flags such as `--url` are not accepted globally or by `version`. The schema/migrate persistent configuration flags are accepted before their group name, however; for example, `atlas --config=/nonexistent schema apply` reaches configuration URL validation and reports `Error: missing scheme for config file. Did you mean file:///nonexistent?`.

## Spec 6

`completion` without a shell prints the following exact help:

```text
Generate the autocompletion script for atlas for the specified shell.
See each sub-command's help for details on how to use the generated script.

Usage:
  atlas completion [command]

Available Commands:
  bash        Generate the autocompletion script for bash
  fish        Generate the autocompletion script for fish
  powershell  Generate the autocompletion script for powershell
  zsh         Generate the autocompletion script for zsh

Flags:
  -h, --help   help for completion

Use "atlas completion [command] --help" for more information about a command.
```

Each `completion SHELL` succeeds and emits a substantial usable dynamic completion script to stdout only. `completion bash --no-descriptions` is accepted. Shell help succeeds. An unrecognized immediate child is handled like other group-command children: for example, `completion invalid` exits 0, prints the exact completion group help above to stdout, and prints nothing to stderr.

The shell-help pages use these exact opening sentences: `Generate the autocompletion script for the bash shell.`, `Generate the autocompletion script for the zsh shell.`, and `Generate the autocompletion script for the fish shell.` The bash help also contains the current-session installation command `source <(atlas completion bash)`.

The generated scripts must use these exact identifying starts and mechanisms: bash starts `# bash completion V2 for atlas                                -*- shell-script -*-`, defines `__atlas_debug` and `__atlas_init_completion`, and normally constructs its request dynamically as `requestComp="${words[0]} __complete ${args[*]}"` (it does not contain the literal command text `atlas __complete`). The accepted `completion bash --no-descriptions` variant instead constructs exactly `requestComp="${words[0]} __completeNoDesc ${args[*]}"`. Zsh starts `#compdef atlas\ncompdef _atlas atlas`, then `# zsh completion for atlas`, defines `__atlas_debug` and `_atlas`; fish starts `# fish completion for atlas                                -*- shell-script -*-`, defines `__atlas_debug` and `__atlas_perform_completion`, and invokes `ATLAS_ACTIVE_HELP=0 ... __complete`; PowerShell starts `# powershell completion for atlas                                -*- shell-script -*-`, defines `__atlas_debug`, an escaping filter, and `[scriptblock]${__atlasCompleterBlock}`. The first function in each script reads `BASH_COMP_DEBUG_FILE` and appends debug messages when it is set. Scripts include completion directive constants for error=1, no-space=2, no-file-completion=4, filter-extension=8, filter-directories=16, and keep-order=32 as appropriate for the shell.

The required 50-line compatibility prefix for each generated script is reproduced below verbatim. The real script may continue after this prefix.

```bash
# bash completion V2 for atlas                                -*- shell-script -*-

__atlas_debug()
{
    if [[ -n ${BASH_COMP_DEBUG_FILE-} ]]; then
        echo "$*" >> "${BASH_COMP_DEBUG_FILE}"
    fi
}

# Macs have bash3 for which the bash-completion package doesn't include
# _init_completion. This is a minimal version of that function.
__atlas_init_completion()
{
    COMPREPLY=()
    _get_comp_words_by_ref "$@" cur prev words cword
}

# This function calls the atlas program to obtain the completion
# results and the directive.  It fills the 'out' and 'directive' vars.
__atlas_get_completion_results() {
    local requestComp lastParam lastChar args

    # Prepare the command to request completions for the program.
    # Calling ${words[0]} instead of directly atlas allows handling aliases
    args=("${words[@]:1}")
    requestComp="${words[0]} __complete ${args[*]}"

    lastParam=${words[$((${#words[@]}-1))]}
    lastChar=${lastParam:$((${#lastParam}-1)):1}
    __atlas_debug "lastParam ${lastParam}, lastChar ${lastChar}"

    if [[ -z ${cur} && ${lastChar} != = ]]; then
        # If the last parameter is complete (there is a space following it)
        # We add an extra empty parameter so we can indicate this to the go method.
        __atlas_debug "Adding extra empty parameter"
        requestComp="${requestComp} ''"
    fi

    # When completing a flag with an = (e.g., atlas -n=<TAB>)
    # bash focuses on the part after the =, so we need to remove
    # the flag part from $cur
    if [[ ${cur} == -*=* ]]; then
        cur="${cur#*=}"
    fi

    __atlas_debug "Calling ${requestComp}"
    # Use eval to handle any environment variables and such
    out=$(eval "${requestComp}" 2>/dev/null)

    # Extract the directive integer at the very end of the output following a colon (:)
```

```zsh
#compdef atlas
compdef _atlas atlas

# zsh completion for atlas                                -*- shell-script -*-

__atlas_debug()
{
    local file="$BASH_COMP_DEBUG_FILE"
    if [[ -n ${file} ]]; then
        echo "$*" >> "${file}"
    fi
}

_atlas()
{
    local shellCompDirectiveError=1
    local shellCompDirectiveNoSpace=2
    local shellCompDirectiveNoFileComp=4
    local shellCompDirectiveFilterFileExt=8
    local shellCompDirectiveFilterDirs=16
    local shellCompDirectiveKeepOrder=32

    local lastParam lastChar flagPrefix requestComp out directive comp lastComp noSpace keepOrder
    local -a completions

    __atlas_debug "\n========= starting completion logic =========="
    __atlas_debug "CURRENT: ${CURRENT}, words[*]: ${words[*]}"

    # The user could have moved the cursor backwards on the command-line.
    # We need to trigger completion from the $CURRENT location, so we need
    # to truncate the command-line ($words) up to the $CURRENT location.
    # (We cannot use $CURSOR as its value does not work when a command is an alias.)
    words=("${=words[1,CURRENT]}")
    __atlas_debug "Truncated words[*]: ${words[*]},"

    lastParam=${words[-1]}
    lastChar=${lastParam[-1]}
    __atlas_debug "lastParam: ${lastParam}, lastChar: ${lastChar}"

    # For zsh, when completing a flag with an = (e.g., atlas -n=<TAB>)
    # completions must be prefixed with the flag
    setopt local_options BASH_REMATCH
    if [[ "${lastParam}" =~ '-.*=' ]]; then
        # We are dealing with a flag with an =
        flagPrefix="-P ${BASH_REMATCH}"
    fi

    # Prepare the command to obtain completions
    requestComp="${words[1]} __complete ${words[2,-1]}"
    if [ "${lastChar}" = "" ]; then
```

```fish
# fish completion for atlas                                -*- shell-script -*-

function __atlas_debug
    set -l file "$BASH_COMP_DEBUG_FILE"
    if test -n "$file"
        echo "$argv" >> $file
    end
end

function __atlas_perform_completion
    __atlas_debug "Starting __atlas_perform_completion"

    # Extract all args except the last one
    set -l args (commandline -opc)
    # Extract the last arg and escape it in case it is a space
    set -l lastArg (string escape -- (commandline -ct))

    __atlas_debug "args: $args"
    __atlas_debug "last arg: $lastArg"

    # Disable ActiveHelp which is not supported for fish shell
    set -l requestComp "ATLAS_ACTIVE_HELP=0 $args[1] __complete $args[2..-1] $lastArg"

    __atlas_debug "Calling $requestComp"
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

    __atlas_debug "Comps: $comps"
    __atlas_debug "DirectiveLine: $directiveLine"
    __atlas_debug "flagPrefix: $flagPrefix"

```

```powershell
# powershell completion for atlas                                -*- shell-script -*-

function __atlas_debug {
    if ($env:BASH_COMP_DEBUG_FILE) {
        "$args" | Out-File -Append -FilePath "$env:BASH_COMP_DEBUG_FILE"
    }
}

filter __atlas_escapeStringWithSpecialChars {
    $_ -replace '\s|#|@|\$|;|,|''|\{|\}|\(|\)|"|`|\||<|>|&','`$&'
}

[scriptblock]${__atlasCompleterBlock} = {
    param(
            $WordToComplete,
            $CommandAst,
            $CursorPosition
        )

    # Get the current command line and convert into a string
    $Command = $CommandAst.CommandElements
    $Command = "$Command"

    __atlas_debug ""
    __atlas_debug "========= starting completion logic =========="
    __atlas_debug "WordToComplete: $WordToComplete Command: $Command CursorPosition: $CursorPosition"

    # The user could have moved the cursor backwards on the command-line.
    # We need to trigger completion from the $CursorPosition location, so we need
    # to truncate the command-line ($Command) up to the $CursorPosition location.
    # Make sure the $Command is longer then the $CursorPosition before we truncate.
    # This happens because the $Command does not include the last space.
    if ($Command.Length -gt $CursorPosition) {
        $Command=$Command.Substring(0,$CursorPosition)
    }
    __atlas_debug "Truncated command: $Command"

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
    __atlas_debug "RequestComp: $RequestComp"
```


## Spec 7

All resources use URLs, not unadorned paths. Support at least `sqlite://`, `file://`, `env://`, `mem://`, and parsing/diagnostics for `mysql://`, `mariadb://`, `postgres://`, and `docker://`. SQLite forms include absolute paths (`sqlite:///tmp/a.db` or `sqlite:///tmp/a.db?_fk=1`), host/path forms (`sqlite://file:/tmp/a.db`), relative database names, and shared/in-memory forms such as `sqlite://file?mode=memory&_fk=1`; query parameters must be retained. Opening an ordinary nonexistent SQLite file creates it where SQLite normally does. An impossible parent directory errors.

A missing general URL scheme normally fails with `Error: missing scheme. See: https://atlasgo.io/url`. The malformed scheme-like value `://missing-scheme` is a distinct parse case: `schema inspect --url ://missing-scheme` exits 1 with no stdout and exactly `Error: missing protocol scheme` on stderr. An unknown database driver fails with `Error: sql/sqlclient: unknown driver "NAME"` (and may append `. See: https://atlasgo.io/url`). An out-of-range MySQL port retains driver and operation context: `schema inspect -u mysql://localhost:99999/db` exits 1 with no stdout and exactly `Error: mysql: query system variables: dial tcp: address 99999: invalid port` on stderr. Malformed bracketed URLs fail clearly. Trying to open a SQLite database below a nonexistent parent fails with an OS-level cause; for example, `migrate status --url sqlite:///nonexistent_parent/nested/test.db` ends with `unable to open database file: no such file or directory`. For `schema clean -u sqlite:///NONEXISTENT/PATH/db.db --auto-approve`, the driver context is also retained: it exits 1 with no stdout and stderr `Error: sqlite: querying schemas: unable to open database file: no such file or directory`. A migration directory must normally be `file://...`; a bare directory produces `missing scheme for dir url. Did you mean "file://PATH"?`. Only local `file` and in-process `mem` directory schemes are accepted. A non-directory scheme has the exact driver diagnostic; for example, `migrate hash --dir http://example.com/migrations` exits 1 with `Error: unsupported driver "http"`. Invalid directory formats normally fail. The `mem` hash path is an exception: `migrate hash --dir 'mem://x?format=nonesuch'` exits 0 with empty stdout and stderr, ignoring that format query. `file://` paths may contain spaces, Unicode, symlinks, and query parameters such as `?format=atlas`.

## Spec 8

Project configuration is HCL. `-c/--config` requires a URL; `file://atlas.hcl` is the default. The default file is consulted when an environment-dependent operation requests `--env`; simple commands such as help and version work when it is absent. Missing config diagnostics preserve whether the resolved path is relative or absolute and are exact: absent default `atlas.hcl` reports `Error: config file "atlas.hcl" was not found: stat atlas.hcl: no such file or directory`, while `file:///nonexistent/file.hcl` reports `Error: config file "/nonexistent/file.hcl" was not found: stat /nonexistent/file.hcl: no such file or directory`. Bare `config.hcl` fails with `Error: missing scheme for config file. Did you mean file://config.hcl?`; `http://...` fails with `Error: unsupported config file driver "http"`. A malformed bracketed config URL has the exact underlying parser wording: `atlas --config 'file://[invalid' schema inspect` exits 1 with no stdout and stderr `Error: parse "file://[invalid": missing ']' in host`. Invalid HCL reports filename, source range, and the HCL parse reason. For an invalid construct where an argument or block is expected, that reason is `Argument or block definition required; An argument or block definition is required here.` Empty/commented config files parse, but selecting an absent environment fails with `env "NAME" not defined in config file`.

Support labeled environments:

```hcl
variable "db_name" { type = string default = "default.db" }
locals { common_dev = "sqlite://dev?mode=memory" }
env "dev" {
  url = "sqlite://${var.db_name}"
  dev = local.common_dev
  schemas = ["main"]
  src = "file://schema.hcl"
  migration { dir = "file://migrations" }
}
```

Variables without defaults are required. If `db_name` is required and omitted, the exact diagnostic is `Error: missing value for required variable "db_name"`. Repeatable `--var name=value` values override defaults and may provide multiple variables. A malformed token is quoted in the exact flag-parser diagnostic; for example, `--var invalid_format` reports `Error: invalid argument "invalid_format" for "--var" flag: variables must be format as key=value, got: "invalid_format"`. String interpolation, `var.x`, `local.x`, `atlas.env`, and `getenv("NAME")` are evaluated; unset environment variables yield the empty string. Multiple environments remain separate and `--env` selects exactly one. Explicit CLI values, especially `--dir`, override environment configuration.

## Spec 9

Configuration also supports unlabeled/dynamic environments using `name = atlas.env`, schema blocks (`schema { src = ... }`), and `src` as either a string or a list of strings. A numeric `src` fails with `Error: expected src to be either a string or strings, got: number`. Multiple schema sources are merged for commands that accept them.

`env://attribute` resolves a value in the selected environment, including `url`, `dev`, custom attributes, and `schema.src`. Behavior without a selected environment is command-path specific. `schema inspect -u env://url` exits 1 with no stdout and the ordinary error `Error: missing scheme. See: https://atlasgo.io/url`; on the first qualifying error under a fresh home, the troubleshooting block from Spec 11 follows that line. In contrast, `schema diff --from env://url --to 'sqlite://file?mode=memory'` and `schema apply -u env://url --to file:///nonexistent.hcl --dry-run` each exit 1 with no stdout and exactly `Error: cannot use env:// variables without selecting an environment` on stderr. An `env://` URL must contain a nonempty host and no path or query: examples of exact failures are `Error: invalid env:// variable "env://url/extra"` and `Error: invalid env:// variable "env://url?param=value"`. Unknown attributes and absent `src` fail explicitly. A selected environment's own `url` attribute may itself be an `env://` reference: with environment `e` containing `url = "env://custom"` and `custom = "sqlite://db.sqlite"`, `schema inspect --env e` resolves the nested reference, creates/opens `db.sqlite`, prints the empty `main` schema, and exits 0. This does not extend to an explicitly requested custom attribute whose value is another `env://` reference. With environment `dev` containing `nested = "env://url"`, `schema inspect --env dev --url env://nested` exits 1 with no stdout and stderr `Error: env://env://nested (attribute) cannot reference another env://`. The exact scalar-resolution behavior is:

- With environment `dev` lacking `src`, resolving `env://src` exits 1 with `Error: env://src: no src attribute defined in env "dev"` on stderr.
- Resolving an unknown attribute exits 1; for `env://nonexistent` in environment `dev`, stderr is `Error: env://nonexistent (attribute) not found in env.dev`.
- `env://src` requires the configured `src` to be a scalar string. A list is rejected even when it has one element, with `Error: env://src: expect one schema in env "dev", got N`, where `N` is the list length (observed for both `N=1` and `N=2`). Commands that consume schema sources directly may still merge list-valued `src` as described above; the rejection is specific to resolving the list through a scalar `env://src` URL.

Global `diff` and `lint` blocks are inherited/extended by environment-specific settings (including diff skip policies and lint git/review settings), not discarded.

## Spec 10

Evaluate these HCL data sources eagerly when referenced:

- `data "sql" "x" { url = ... query = ... args = [...] }` opens the database and executes a parameterized query. It accepts numeric, string, and boolean arguments and exposes `.value` (first scalar), `.values` (all first-column results), and `.count`. Errors are prefixed `Error: data.sql.x:`; examples include `executing query: no such table: ...`, `executing query: incomplete input`, and `opening connection: sql/sqlclient: unknown driver ...`.
- `data "external" "x" { program = [command, args...] working_dir = ... }` executes without a shell, captures stdout as its value, and respects the optional working directory. A nonzero exit is an error prefixed `Error: data.external.x: running program ...`, and the child's captured stderr text is preserved in that error after the program context. For example, with `program = ["/bin/sh", "-c", "printf 'child boom' >&2; exit 7"]` supplying an environment URL, `schema inspect --env e` exits 1 with no stdout and the ordinary stderr line `Error: data.external.x: running program /bin/sh: child boom`. By contrast, stderr from a program that exits 0 is ignored rather than treated as a datasource error. In particular, when the program is `["/bin/sh", "-c", "echo bad >&2"]` and its empty stdout supplies an environment URL, `schema inspect --env e` continues to URL validation and exits 1 with the ordinary error `Error: required flag(s) "url" not set` (followed by Spec 11's troubleshooting block on the first qualifying error). An empty program fails with `program cannot be empty`; a missing executable reports the normal `executable file not found in $PATH` text.
- `data "template_dir" "x" { path = ... vars = {...} }` renders every top-level SQL template with Go-template-style `.Variable` substitutions and exposes a temporary migration-directory `.url`. A missing path is reported as `Error: data.template_dir.x: path PATH is not a directory`. A missing variable retains the datasource address, template filename, source coordinates, action, and missing key. For datasource `migrations` and a template `001_init.sql` containing the line `SELECT 'value={{.UndefinedVar}}';` as line 2, the exact diagnostic is `Error: data.template_dir.migrations: executing template: template: 001_init.sql:2:16: executing "001_init.sql" at <.UndefinedVar>: map has no entry for key "UndefinedVar"`. Strings, numbers, and booleans are valid variables.
- `data "runtimevar" "x" { url = ... }` supports at least `constant://...?val=VALUE&decoder=string`, respects `timeout`, and only accepts the `string` decoder. Unknown schemes enumerate supported runtime-variable schemes; unsupported decoders fail with `unsupported decoder: "..."`.
- AWS RDS token and GCP Cloud SQL token data sources perform normal credential resolution. Their errors are prefixed with their full addresses. A nonexistent AWS profile mentions `loading aws config: failed to get shared config profile`; absent GCP credentials mentions `finding default credentials: google: could not find default credentials`. With syntactically valid AWS credentials, token generation proceeds far enough that an unreachable database reports its DNS/connection error rather than an AWS-loading error.

## Spec 11

Community-edition upgrade notices are stateful. On the first qualifying advanced schema operation, print this notice to stderr (before the normal result, which remains on stdout):

```text
Notice: This Atlas edition lacks support for features such as checkpoints,
testing, down migrations, and more. Additionally, advanced database objects such as views, 
triggers, and stored procedures are not supported. To read more: https://atlasgo.io/community-edition

To install the non-community version of Atlas, use the following command:

	curl -sSf https://atlasgo.sh | sh

Or, visit the website to see all installation options:

	https://atlasgo.io/docs#installation
```

Record the suggestion in `$HOME/.atlas/local-community.json` as valid UTF-8 JSON containing key `"v1.us"` and a UTC RFC3339 timestamp (optional fractional seconds, ending `Z`). Create the parent directory automatically. Do not repeat or update the notice within one week, and share the same state across schema commands. `ATLAS_NO_UPGRADE_SUGGESTIONS` disables both notice and state creation. Corrupt, empty, whitespace-only, large, or forward-compatible JSON state must never crash a command; on parse error leave it unchanged and skip the notice. `version` never creates this file. `ATLAS_NO_UPDATE_NOTIFIER` with any value suppresses update checks but never changes normal command output.

There is a separate, throttled troubleshooting suggestion for qualifying command errors. On its first occurrence, append this exact block to stderr after the ordinary error line:

```text
You're running the community build of Atlas, which may differ from the official version.
If this error persists, try installing the official version as a troubleshooting step:

  curl -sSf https://atlasgo.sh | sh

More installation options: https://atlasgo.io/docs#installation
```

For example, the first `migrate apply` connection attempt using an unknown `invalid://` driver emits its normal unknown-driver error and then this block. A first qualifying error under a fresh home may also be any of the following, and appends the same block: a required-input failure from `schema clean`, `schema diff`, `migrate diff`, or an empty-output external datasource; the default-directory `migrate import` stat failure; a status-template parse/execution failure; a lint selection failure; a migration checksum failure; a missing SQL-schema or HCL-directory dev URL; or the scheme error from a CLI `env://` URL without `--env`. Thus, where the affected command sections call the preceding error line "exact", that exactness describes the ordinary diagnostic before this stateful suffix. Record this error suggestion in `$HOME/.atlas/community_error.json` as JSON with a `last_suggested` RFC3339 timestamp. A second qualifying error under the same home does not repeat the block and emits only the ordinary error. This suggestion is independent of the advanced-schema-operation notice and its state file above.

## Spec 12

`schema fmt [paths...]` formats Atlas HCL files in place. With no paths, inspect only the current directory. A path may be a file or directory; a directory is nonrecursive and only its immediate `.hcl` regular entries are processed. Explicit non-`.hcl` files, binary/non-HCL directory entries, and nested directories are ignored. Multiple files/directories and symlinked files/directories work. Empty files/directories succeed silently. Missing paths fail on stderr with `stat PATH: no such file or directory` (or equivalent including those substrings).

Print one input-form path per changed file, and nothing for unchanged files. Thus absolute input produces absolute output; relative input produces relative output. Directory results are deterministic. Preserve file permissions and do not create extra files. Formatting is idempotent.

## Spec 13

The HCL formatter preserves semantic content, block order, UTF-8 text, heredocs, and `//`/`#` comments. It uses two-space indentation in expanded nested blocks, one space between block kind and quoted labels, spaces around `=`, and compact single-line blocks when the input block was inline. A block whose opening brace and first attribute were on one line retains that compact placement even when another attribute followed on a new line: this mixed layout is not expanded, indented, or attribute-aligned, and its closing brace is placed after the last attribute. Preserve whether a nonempty input ended with a newline. Normalize whitespace-only lines to newline-only lines. A UTF-8 BOM may be retained or removed but the following HCL must be formatted. For example:

```hcl
// This is a schema file
table "users" {
  schema = schema.public
  // User ID column
  column "id" { type = int }
  # Name column
  column "name" { type = varchar(255) }
}
```

For the exact input:

```hcl
table   "single" {schema=schema.public}
table "multi"{schema=schema.public
comment="has comment"}
```

the exact formatted bytes are:

```hcl
table "single" { schema = schema.public }
table "multi" { schema = schema.public
comment = "has comment" }
```

Deeply nested blocks, lists, references, function calls, hundreds of blocks, filenames with spaces, and read-only files must be handled. Syntax errors that the formatter rejects fail nonzero and do not corrupt the file. The malformed list input `table "x" { invalid = [ }\n` is a permissive exception: `schema fmt FILE` exits 0 with no stdout or stderr and leaves those bytes unchanged.

## Spec 14

A migration directory contains top-level migration files ordered lexicographically by filename plus an optional `atlas.sum`. Non-SQL files and subdirectories are ignored by Atlas-format hashing and execution. An Atlas filename is `VERSION[_DESCRIPTION].sql`; version is the part before the first underscore (after removing `.sql`), description is the remainder. Descriptions preserve case, spaces, Unicode, hyphens, dots, colons, underscores, and numbers. Long names must not be truncated by the program beyond filesystem limits.

Supported directory formats are `atlas`, `golang-migrate`, `goose`, `flyway`, `liquibase`, and `dbmate`; select one by `?format=...` in the directory URL or `--dir-format`. A URL query parameter takes precedence over the flag. Invalid formats normally fail with `unknown dir format`. An explicit `file://` with an empty path resolves to the default relative `migrations` directory; thus `migrate new test --dir file://` creates `migrations/` below the current directory, its timestamped SQL file, and `migrations/atlas.sum`. `mem://name` represents an empty in-process directory and is supported by `migrate hash`: hashing such a directory succeeds silently without a filesystem traceback. For this in-process hash operation, even an unknown URL format is ignored: `migrate hash --dir 'mem://x?format=nonesuch'` exits 0 with empty stdout and stderr.

## Spec 15

`migrate new [name]` creates parent directories as necessary and is quiet on success. For Atlas format, use the current UTC timestamp `YYYYMMDDHHMMSS`, followed by `_name` only if name is nonempty, then `.sql`; create an empty file. The timestamp has only one-second resolution and there is no collision suffix: repeated calls with the same name in one second all exit 0 and target the same filename; after three such calls, only one empty SQL file and `atlas.sum` remain. Do not sanitize or URL-encode the supplied name.

Other formats create:

- golang-migrate: matching empty `TIMESTAMP_name.up.sql` and `TIMESTAMP_name.down.sql`.
- goose: one `TIMESTAMP_name.sql` containing both `-- +goose Up` and `-- +goose Down` sections.
- flyway: `VTIMESTAMP__name.sql` and matching `UTIMESTAMP__name.sql`.
- liquibase: one Atlas-style timestamped file whose trimmed content is `--liquibase formatted sql`.
- dbmate: one Atlas-style timestamped file containing `-- migrate:up` and `-- migrate:down` sections.

After creation, regenerate `atlas.sum` so it names every SQL file. `--edit` is recognized and uses `$EDITOR` when actual editing is requested.

## Spec 16

`migrate hash` creates or atomically replaces `atlas.sum`, succeeds for an existing empty directory, is deterministic and idempotent, preserves migration permissions/content, and emits no normal output. It handles large files, UTF-8, BOMs, CRLF and LF as distinct byte sequences, empty SQL files, case-sensitive names, and symlinked directories. Only immediate `.sql` files are included in lexicographic order.

The exact checksum algorithm is cumulative SHA-256. Start one SHA-256 state empty. For each ordered file, append its filename bytes then its exact content bytes to that same state; the file's hash is base64 of the cumulative digest at that point. Then compute the directory hash as SHA-256 over the concatenation, for every entry, of filename bytes followed by the unprefixed base64 file-hash bytes. The file is UTF-8 text:

```text
h1:<base64-directory-hash>
<filename-1> h1:<base64-cumulative-hash-1>
<filename-2> h1:<base64-cumulative-hash-2>
```

It ends in exactly one newline. An empty directory contains exactly `h1:47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=\n`. A nonexistent directory fails with `sql/migrate: stat ...: no such file or directory`.

## Spec 17

`migrate validate` first validates `atlas.sum`. A valid directory is silent and exits 0. An empty directory is also a valid silent success even if no sum file exists. A directory containing migrations without a sum fails with the ordinary stderr line `Error: checksum file not found` and stdout:

```text
You have a checksum error in your migration directory.
Please check your migration files and run 'atlas migrate hash' to re-hash the contents
```

An edited file fails with the ordinary stderr line `Error: checksum mismatch` and stdout:

```text
You have a checksum error in your migration directory.

	L2: VERSION_NAME.sql was edited

Please check your migration files and run 'atlas migrate hash' to re-hash the contents
```

For either checksum failure, the first qualifying error under a fresh home appends Spec 11's troubleshooting block to stderr after the ordinary line; a later qualifying error under the same home has only that ordinary line. Report the first differing entry in checksum-file order. After `migrate hash`, validation succeeds again. Without `--dev-url`, validation is checksum-only. With a SQLite dev URL, replay files in order and fail on invalid SQL with a message identifying the statement and version. For a migration version `20240101000001` containing `CREATE TABLLE users (id INTEGER PRIMARY KEY);`, the exact ordinary stderr is `Error: replaying the migration directory: sql/migrate: read migration directory state: sql/migrate: executing statement "CREATE TABLLE users (id INTEGER PRIMARY KEY);" from version "20240101000001": near "TABLLE": syntax error`.

A syntactically malformed checksum entry (for example, a valid `h1:` directory header followed by a line without the required filename/hash fields) is distinct from an edited-file mismatch. `migrate validate` exits 1 with stderr `Error: checksum file format invalid` and the same two-line checksum guidance used for a missing sum on stdout. Each checksum-guidance block ends with a blank line (two newline bytes after its final text line).

## Spec 18

`migrate import --from SOURCE --to TARGET` converts a non-Atlas migration directory to Atlas format, creates a missing target, preserves source ordering, SQL text/comments/semicolons inside strings, handles empty files, and finishes by writing a valid `atlas.sum`. Target occupancy is determined by migration-directory entries, not by arbitrary files. A target containing an existing `.sql` migration is rejected before the empty-source shortcut: an empty Liquibase source plus a target containing `001_existing.sql` exits 1 with no stdout and exactly `Error: target migration directory must be empty` on stderr. In contrast, unrelated non-SQL entries are ignored and preserved. Thus an empty source plus a target containing only `occupied.txt` exits 0 with exactly the stdout bytes `nothing to import` (no trailing newline) and no stderr, leaving that file in place. A nonempty golang-migrate source containing `1.up.sql` can likewise be imported into a target containing only a file named `x`: the command exits 0 with empty streams, preserves `x`, and adds `1.up.sql` and `atlas.sum`. A nonexistent source fails. With no source `format` query, fail with `cannot import a migration directory already in "atlas" format`; an invalid one fails with `unknown dir format "..."`.

Conversion keeps only forward/up operations:

- dbmate: strip `-- migrate:up/down` directives and discard the down section; keep ordinary comments and multiline SQL.
- goose: strip Up/Down and StatementBegin/StatementEnd directives, discard Down, and keep statement blocks intact.
- golang-migrate: import `.up.sql` files only and normally remove the direction suffix; for example, `1_init.up.sql` becomes `1_init.sql`. A basename with no underscore/description is retained as observed: importing `1.up.sql` produces a target file named `1.up.sql`.
- flyway: import versioned `V...`, baseline `B...`, and repeatable `R__...` files in their execution order; ignore undo `U...`; convert names deterministically. In the observed fixture containing `V1__init.sql`, `U1__init.sql`, and `R__views.sql`, the target files are exactly `1_init.sql`, `1R_views.sql`, and `atlas.sum`; there is no `2R_views.sql`, and the undo SQL is not imported.
- liquibase formatted SQL: preserve the `--liquibase formatted sql` header and each `--changeset AUTHOR:ID` metadata line. A rollback directive recognized as a complete newline-terminated line is removed, but an unterminated rollback directive on the final source line is preserved. In particular, importing a file named `1.sql` whose exact bytes are `--liquibase formatted sql\n--changeset atlas:1-1\nCREATE TABLE t(id int);\n--rollback DROP TABLE t;` creates `1.sql` with exactly those four lines plus a final newline; the command exits 0 with empty stdout and stderr and also creates `atlas.sum`.

Relative `file://` paths work, `--dir-format atlas` is accepted for the target, and all five foreign formats above must import at least one valid fixture directory successfully.

## Spec 19

The executable provides real SQLite integration. It executes SQL through SQLite, enables foreign-key semantics where needed, and persists changes to file-backed databases. `schema inspect`, `schema apply/diff/clean`, `migrate apply/status/set`, validation replay, and SQL datasources all share compatible SQLite behavior. Do not expose SQLite internal tables, except the Atlas revision table when it is genuinely present and not being filtered as internal command metadata.

Atlas versioned migrations are tracked in table `atlas_schema_revisions`, keyed by version and containing at least description, type, applied/total statement counts, executed timestamp, execution time, error fields, hash fields, and operator version. Migration commands can create/query this table and do not reapply recorded versions.

## Spec 20

`schema inspect -u SQLITE_URL` emits canonical Atlas HCL. Even an empty database produces:

```hcl
schema "main" {
}
```

Tables precede the final schema block. Preserve table/column declaration order, quoted special or keyword identifiers, SQLite type declarations (`integer`, `text`, `real`, `blob`, `boolean`, `date`, `datetime`, `varchar(255)`, and `decimal(10,2)`), nullability, autoincrement, literal defaults, SQL-expression defaults via `sql("...")`, primary keys, named/automatic indexes, uniqueness, checks, and foreign keys. Two SQLite declarations are normalized rather than preserved verbatim: `TIME` renders as `type = sql("time")`, and `CHAR(10)` renders as `type = sql("char")` (the length is omitted). A representative shape is:

```hcl
table "users" {
  schema = schema.main
  column "id" {
    null = true
    type = integer
  }
  column "name" {
    null = false
    type = text
  }
  primary_key {
    columns = [column.id]
  }
  index "idx_name" {
    columns = [column.name]
  }
}
schema "main" {
}
```

Composite key column order is retained. Foreign keys use `foreign_key "NAME"`, `columns`, `ref_columns = [table.parent.column.id]`, and explicit `on_update`/`on_delete` enum values such as `NO_ACTION`, `CASCADE`, or `SET_NULL`. `--exclude` is repeatable and supports exact/glob table patterns. `--schema main` is accepted. Missing URL and invalid drivers use the errors in Specs 5 and 7.

## Spec 21

Inspection formatting supports Go-like templates. `--format '{{ json . }}'` returns JSON shaped as `{"schemas":[{"name":"main","tables":[...]}]}`. A table has `name`, `columns` (`name`, original uppercase SQLite `type`, and `null:true` only when applicable), optional `primary_key:{"parts":[{"column":"id"}]}`, `indexes` (name, unique, parts), and `foreign_keys` (`columns` plus `references:{table,columns}`). Empty schemas have an absent or empty tables list. `--format '{{ sql . }}'` emits commented SQLite CREATE DDL. Invalid fields/functions/template syntax fail nonzero with a template parse/execution diagnostic. In particular, a schema-inspect format whose action ends with a single `}` (for example `{{.Foo}`) exits 1 with exactly `Error: parse log format: template: format:1: bad character U+007D '}'`.

When schema state is read from `file://`, accept a single HCL file, multiple HCL files, a top-level directory of HCL files, or a directory of SQL files. Both HCL and SQL directory inputs require a nonempty `--dev-url`; a clean directory containing valid HCL files but inspected without that flag exits 1 with no stdout and the ordinary stderr line `Error: --dev-url cannot be empty`. Supplying `--dev-url sqlite://file?mode=memory` allows such an HCL directory to be read and its files merged. A top-level `variable` block is valid in a schema HCL file and does not by itself make that file a project configuration: a file containing a defaulted variable plus `schema "main"` and `table "users"` blocks successfully inspects with `--format '{{ json . }}'` and emits JSON containing the `main` schema and `users` table. Ignore unrelated extensions. Reject a directory containing both SQL and HCL as ambiguous and reject a project config used as a schema file after dev-URL validation. Thus, a project file at `PATH/atlas.hcl` supplied through `--url file://PATH/atlas.hcl` without `--dev-url` exits 1 with no stdout and the ordinary stderr line `Error: --dev-url cannot be empty`; with `--dev-url sqlite://file?mode=memory`, it exits 1 with no stdout and exactly `Error: cannot parse project file "PATH/atlas.hcl" as a schema file` on stderr. Nested directories are not traversed and do not themselves count as schema files. Consequently, a directory named `nested` containing only a child directory named `subdir` exits 1 with no stdout and the ordinary stderr line `Error: "nested" contains neither SQL nor HCL files`. An empty schema directory named `empty_schema` fails as `Error: "empty_schema" contains neither SQL nor HCL files`. SQL schema input requires nonempty `--dev-url`; its ordinary diagnostic is `Error: --dev-url cannot be empty. See: https://atlasgo.io/atlas-schema/sql#dev-database`. On the first qualifying missing-dev-URL occurrence under a fresh home, Spec 11's troubleshooting block follows the ordinary diagnostic. SQL replay errors retain both filename and statement context: if `schema.sql` contains `INSERT INTO nonexistent_table VALUES (1);`, inspection exits 1 with no stdout and exactly `Error: read state from "schema.sql": executing statement: "INSERT INTO nonexistent_table VALUES (1);": no such table: nonexistent_table` on stderr.

An HCL source with multiple schema blocks cannot be evaluated using a dev-database URL bound to a single SQLite schema. For example, a source containing `main` and `other` with `--dev-url sqlite://file?mode=memory` exits 1 with `Error: cannot use HCL with more than 1 schema when dev-url is limited to schema "main"`. Invalid HCL retains the source location and the parser's full explanation; an unclosed block reports `Unclosed configuration block; There is no closing brace for this block before the end of the file. This may be caused by incorrect brace nesting elsewhere in this file.` A syntactically valid table that lacks a schema association fails conversion rather than producing a partial plan; the diagnostic begins `Error: sqlite: failed converting to *schema.Realm:`. For a table named `users`, the observed full diagnostic is `Error: sqlite: failed converting to *schema.Realm: cannot extract schema name for table "users": schemahcl: type "schema" was not found in nil reference`.

## Spec 22

The schema HCL accepted by apply/diff contains `schema`, `table`, `column`, `primary_key`, `index`, `foreign_key`, and `check` blocks. References such as `schema.main`, `column.id`, and `table.users.column.id` resolve across files. Column attributes include `type`, optional `null` (default false for desired schemas), `default`, and `auto_increment`; indexes have `unique` and ordered `columns`; foreign keys have ordered local/reference columns and update/delete actions. Types and values may be identifiers/function calls such as `integer`, `varchar(255)`, `sql("CURRENT_TIMESTAMP")`, strings, numbers, and booleans. Invalid syntax or missing schema association fails with useful source diagnostics rather than partial execution. In particular, the malformed block header `table "users" schema.main {` is rejected with a source range followed by the exact reason `Invalid block definition; Either a quoted string block label or an opening brace ("{") is expected here.`

## Spec 23

`schema diff --from A --to B --dev-url SQLITE` computes the SQL needed to transform A into B, where either side may be a SQLite database URL or file schema. Identical schemas print exactly `Schemas are synced, no changes to be made.`. Changes cover creating/dropping tables, adding/dropping/changing columns and nullability/types/defaults, indexes/unique constraints, composite keys, checks, and foreign keys. Parent tables are created before referencing children. `--exclude` filters matching objects; `--schema` filters schema scope. Multiple `--to` HCL sources are merged.

Default output is comments followed by executable SQLite DDL. Examples:

```sql
-- Add column "email" to table: "users"
ALTER TABLE `users` ADD COLUMN `email` text NOT NULL;
-- Create "posts" table
CREATE TABLE `posts` (`id` int NOT NULL, `title` text NOT NULL, `user_id` int NOT NULL, PRIMARY KEY (`id`));
```

This example also fixes ordering for independent changes in one plan: existing-table alterations such as the `users.email` addition are rendered before creation of an unrelated new table such as `posts`. `--format '{{ sql . }}'` preserves that order.

SQLite changes that cannot use simple ALTER (drop/type/nullability/key/FK changes, and plans that combine indexed-column changes) use one canonical safe sequence. The default diff renderer uses these exact comments and order, substituting the table and retained columns:

```sql
-- Disable the enforcement of foreign-keys constraints
PRAGMA foreign_keys = off;
-- Create "new_users" table
CREATE TABLE `new_users` (...);
-- Copy rows from old table "users" to new temporary table "new_users"
INSERT INTO `new_users` (...) SELECT ... FROM `users`;
-- Drop "users" table after copying rows
DROP TABLE `users`;
-- Rename temporary table "new_users" to "users"
ALTER TABLE `new_users` RENAME TO `users`;
-- Enable back the enforcement of foreign-keys constraints
PRAGMA foreign_keys = on;
```

The reconstructed `CREATE TABLE` explicitly renders nullable columns with `NULL`, for example `` `name` text NULL ``. Index creation follows the rename and precedes foreign-key re-enablement; its comments are `-- Create index "NAME" to table: "TABLE"`, followed by `CREATE INDEX` or `CREATE UNIQUE INDEX`. Independent table drops are ordered after a reconstruction and before the final re-enablement. Even a plan consisting only of direct table drops is enclosed by the exact disable/enable comment-and-PRAGMA pair; each drop is introduced by `-- Drop "TABLE" table`. A reverse diff produces complementary drops.

Independent changes follow the order illustrated above in this section: alterations/reconstructions of existing tables occur before unrelated table creations, and index operations belonging to the reconstructed table occur before the final PRAGMA. `--format '{{ sql . }}'` preserves this same order and wording. Applying the target and diffing again reports synchronized state. The `sql` formatter accepts an optional indentation string, which expands CREATE TABLE columns onto indented lines. `{{if .Changes}}...{{else}}...{{end}}` can test whether changes exist. SQLite string defaults use single quotes in rendered DDL; for example, a string default `active` is rendered `DEFAULT 'active'`.

When a database URL is bound to one schema and an HCL source declares a different one, diff rejects the mismatch. In particular, a source URL ending `?schema=main` compared with HCL declaring only schema `test` exits 1 with no stdout and stderr `Error: mismatched HCL and database schemas: "main" <> "test"`.

## Spec 24

`schema apply -u DB --to SCHEMA` computes the same changes as diff. `--dry-run` prints a plan and does not modify the database. Plan output begins `-- Planned Changes:` and then uses the same comments/DDL, with multiline CREATE TABLE formatting, for example:

```sql
-- Planned Changes:
-- Create "users" table
CREATE TABLE `users` (
  `id` integer NOT NULL,
  `name` text NOT NULL,
  PRIMARY KEY (`id`)
);
```

`--auto-approve` prints that plan and executes it without input. A no-op prints `Schema is synced, no changes to be made`. Applying twice is idempotent. Support `--tx-mode none` and `--tx-mode file`; reject invalid modes. `--exclude` prevents matching tables from being planned or changed; `--schema main` qualifies the target. Multiple `--to` files merge.

Execution must create/drop tables and indexes with accurate defaults, nullability, uniqueness, composite primary keys, and cascade foreign keys. Adding a nullable SQLite column prints the optional keyword explicitly: for a nullable text column `email`, the plan statement is ``ALTER TABLE `users` ADD COLUMN `email` text NULL;``. Preserve existing rows when adding a nullable column and when recreating a table to drop a column; retained values and primary keys must survive. Apply uses the exact reconstruction comments and PRAGMA order specified for diff in Spec 23, after its `-- Planned Changes:` heading; CREATE TABLE is multiline in this renderer.

The database URL is parsed and validated before a desired schema file is loaded. Thus even when `file:///tmp/test.hcl` does not exist, `schema apply -u invalid://url --to file:///tmp/test.hcl --auto-approve` exits 1 with `Error: sql/sqlclient: unknown driver "invalid". See: https://atlasgo.io/url`, while the same invocation with `-u sqlite:` exits 1 with `Error: missing scheme. See: https://atlasgo.io/url`; neither reports the missing file. Other missing/invalid files and URLs fail before mutation. Once required flags are present, an invalid transaction mode is also rejected before database and desired-file work; `schema apply --tx-mode invalid --url 'sqlite://file?mode=memory' --to file:///tmp/does-not-exist.hcl` produces `Error: unknown tx-mode "invalid"`. Without the required URL, the missing-URL result in Spec 4 takes precedence.

## Spec 25

`schema clean -u DB --auto-approve` drops user objects and leaves the database inspectably empty, handling foreign-key dependencies by disabling and re-enabling SQLite FK enforcement around drops. A nonempty successful clean prints the applied plan to stdout, not silently. For tables `users` then `posts`, the exact output is:

```sql
-- Planned Changes:
-- Disable the enforcement of foreign-keys constraints
PRAGMA foreign_keys = off;
-- Drop "users" table
DROP TABLE `users`;
-- Drop "posts" table
DROP TABLE `posts`;
-- Enable back the enforcement of foreign-keys constraints
PRAGMA foreign_keys = on;
```

An indexed table and tables connected by foreign keys use the same printed PRAGMA wrapper; indexes are removed with their tables rather than printed as separate drops. Cleaning an empty/already-clean database succeeds with `Nothing to drop`; cleaning twice is idempotent. Without `--auto-approve`, clean prints the plan and an interactive selector whose default is `Apply`. When stdin is a non-TTY pipe containing the literal bytes `n\n`, that input does not select `Abort`: the command accepts the default, exits 0 with no stderr, and performs the drops. Missing URL fails. Realm-level URLs and URLs qualified to SQLite's `main` schema both work. The impossible-parent diagnostic is the exact schema-query error specified in Spec 7.

## Spec 26

`migrate apply` validates checksums first, then executes only pending files in lexicographic/version order and records revisions. It requires a usable migration directory and URL; malformed URLs, nonexistent directories, missing sum files, edited files, and a zero/negative/nonnumeric amount fail. Amount parsing observes the flag terminator. A bare `-1` is parsed as an option, not as the positional amount: `migrate apply -1 --url 'sqlite://file?mode=memory' --dir mem://x` exits 1 with no stdout and exactly `Error: unknown shorthand flag: '1' in -1` on stderr. In contrast, `migrate apply -- -1` reaches amount validation and reports `Error: cannot apply '-1' migration files`. A positional `0` also exits 1 with no stdout and exactly `Error: cannot apply '0' migration files` on stderr. Nonnumeric values use a distinct parser diagnostic; for example, `abc` produces `Error: invalid amount argument "abc" (invalid syntax). Omit the argument or pass a valid integer instead`. An omitted amount applies all pending migrations; a positive amount limits file count. A repeat with nothing pending prints `No migration files to execute`.

Checksum failures from `migrate apply`, including when a positive amount is present, use the same streams and guidance as `migrate validate` in Spec 17. A missing `atlas.sum` writes `Error: checksum file not found` to stderr and the two-line missing-sum guidance to stdout. An edited migration writes `Error: checksum mismatch` to stderr and the stdout block naming the edited line/file. The guidance ends with the same final blank line described in Spec 17.

Progress output identifies the destination version and each file, for example `Migrating to version 20240103`, `  -- migrating version 20240101`, a `  -- ok (<duration>)` line, and totals such as `  -- 3 migrations` and `  -- 3 sql statements` (singular when one). Starting from a prior revision says `Migrating to version TARGET from CURRENT`. Multiple SQL statements in a file execute in order. `--dry-run` reports without mutating. Transaction modes, lock timeout, baseline, execution order, dirty-database allowance, and revision-schema flags are parsed as in Spec 5.

## Spec 27

`migrate status` opens the migration directory before validating its database URL. From a working directory with no `migrations` entry, invoking `migrate status` with neither `--dir` nor `--url` exits 1 with no stdout and exactly `Error: sql/migrate: stat migrations: no such file or directory` on stderr. Otherwise it compares ordered available files with persisted revisions. Its default format is exactly this shape:

```text
Migration Status: PENDING
  -- Current Version: No migration applied yet
  -- Next Version:    20240101000001
  -- Executed Files:  0
  -- Pending Files:   3
```

When no files exist it is `OK`, next is `Already at latest version`, and both counts are 0. When all are applied it is `OK`, current is the latest version, next is `Already at latest version`, executed is the total, and pending is 0. A new SQLite file is a valid empty database. Mixed-length versions (1, 2, 10), long descriptions, and URL query parameters work.

`--format '{{ json . }}'` emits one JSON value. Top-level fields are `Env`, `Available`, optional `Pending`, optional `Applied`, `Current`, `Next`, and `Status`. When passed through `json`, available/pending items serialize with `Name`, `Version`, and `Description`. That JSON shape is not the raw Go-template field set: an element reached by `range .Pending` is a `migrate.File`, exposes `.Version`, but does not expose `.Description`. With pending files `1_a.sql` and `2_b.sql`, the template `{{if eq .Status "PENDING"}}{{$s := .Status}}{{range .Pending}}{{.Version}}:{{.Description}};{{end}} {{$s}} {{len .Available}}{{else}}bad{{end}}` writes the partial stdout `1:` and then exits 1 with the ordinary diagnostic `Error: template: format:1:77: executing "format" at <.Description>: can't evaluate field Description in type migrate.File` (with the Spec 11 suffix on a first qualifying error). `Env` contains `Driver:"sqlite"`, a parsed `URL` object including `Scheme` and `Schema:"main"`, and a normalized `Dir` ending `?format=atlas`. Applied records include `Version`, `Description`, `Type:"applied"`, `Applied`, `Total`, `ExecutedAt`, `ExecutionTime`, and `OperatorVersion`. Omit `Applied` when empty and `Pending` when empty.

## Spec 28

`migrate set [version]` has working help identifying it as the command for setting the current revision, and exposes URL, directory, directory-format, and revision-schema flags. It requires URL/directory context. An empty explicit version and an invalid directory format fail cleanly. If the implementation accepts a valid version, it must persist the revision update so a subsequent `migrate status` reports that version; an unsupported valid set operation may instead fail nonzero without corrupting state.

## Spec 29

`migrate lint` requires `--dev-url` and exactly one selection mode, positive `--latest N` or `--git-base BRANCH`. Syntactic flag-value parsing precedes required-flag validation. Thus `migrate lint --latest invalid` exits 1 with no stdout and begins stderr with `Error: invalid argument "invalid" for "--latest" flag: strconv.ParseUint: parsing "invalid": invalid syntax`; `migrate lint --latest -1` likewise begins stderr with `Error: invalid argument "-1" for "--latest" flag: strconv.ParseUint: parsing "-1": invalid syntax`. These parser errors occur even though `--dev-url` is absent. After successfully parsing supplied values, required-flag validation applies: `migrate lint --latest 1` and an invocation with neither selection flag nor `--dev-url` exit 1 with the ordinary line `Error: required flag(s) "dev-url" not set`. Once `--dev-url` is supplied, absence of both selection modes reports the ordinary line `Error: --latest or --git-base is required`, and supplying both reports `Error: --latest and --git-base are mutually exclusive`. An explicit `--latest 0` is treated as no selection mode and therefore reports `Error: --latest or --git-base is required`; it does not report a positivity error. The first qualifying lint error under a fresh home appends the troubleshooting block from Spec 11 after its ordinary line. It verifies/replays migrations against `--dev-url`, analyzes at most the selected latest files (or all if N exceeds the count), and is silent for an empty directory or a git comparison with no new files.

The default successful report is mode-specific. Latest mode begins `Analyzing changes until version TARGET (N migration[s] in total):` when analysis starts at the first migration. When `--latest` selects only a suffix and earlier migrations establish the baseline, it instead begins `Analyzing changes from version BASE to TARGET (N migration[s] in total):`; for two files where `--latest 1` analyzes `20240101000002`, `BASE` is `20240101000001`. Git-base mode also uses the `Analyzing changes from version BASE to TARGET ...` form. The heading is immediately followed by a blank line. Each clean file is then reported as:

```text
  -- analyzing version VERSION
    -- no diagnostics found
  -- ok (<duration>)
```

The duration is emitted as a concrete Go duration such as `7.53µs`, not as a literal timing placeholder. A blank line follows every `  -- ok (<duration>)` line, including between file blocks. After the final such blank line, output continues with `  -------------------------`, a concrete total-duration line such as `  -- 2.078556ms`, then `  -- N version ok` or `  -- N versions ok`, and finally `  -- N schema change` or `  -- N schema changes`. The target is the highest analyzed version, even when `--latest` exceeds the available count. For example, two available clean migrations analyzed with `--latest 10` still use the heading `Analyzing changes until version 20240101000002 (2 migrations in total):`, render the two clean file blocks separated by blank lines, and end with `  -- 2 versions ok` and `  -- 2 schema changes`. A git range uses the last base version and last newly added version; for example, three new versions after `20240101000001` through `20240101000004` are headed `Analyzing changes from version 20240101000001 to 20240101000004 (3 migrations in total):` and end with `  -- 3 versions ok` and `  -- 3 schema changes`.

Detect SQL syntax failures and destructive `DROP TABLE` operations. A syntax error identifies the action as statement execution. For a one-file migration containing `CREATE TABLLE users (id INTEGER PRIMARY KEY);`, stdout includes `Error: executing statement: CREATE TABLLE users (id INTEGER PRIMARY KEY);: near "TABLLE": syntax error` and the footer `-- 1 version with errors`; the command exits 1. Destructive findings are grouped under `    -- destructive changes detected:`; each finding is rendered as `      -- L<line>: Dropping table "NAME" https://atlasgo.io/lint/analyzers#DS102`. Suggested emptiness checks are grouped under `    -- suggested fixes:` and begin `      -> Add a pre-migration check`. Report every destructive operation, not just the first, and exit 1 when diagnostics/errors exist. After the normal version and schema-change footer lines, append `  -- N diagnostic` or `  -- N diagnostics`. The observed two-drop report ends with `  -- 2 schema changes` then `  -- 2 diagnostics`; the three-drop report ends with `  -- 3 schema changes` then `  -- 3 diagnostics`. Git-base mode runs against the requested branch and git directory, includes only newly added migrations, and surfaces invalid-branch/non-repository failures as `Error: git diff: exit status ...`. JSON/custom templates expose `Files` with each file's `Name`, `Text`, `Reports`, and `Error`, and permit `{{len .Files}} files analyzed`.

## Spec 30

All command `--format` values use a Go-text-template-compatible language: field and nested-field access, `if/else/end`, `with`, `range`, variables (`{{$s := .Status}}`), pipelines, `index`, `len`, `eq`, `gt`, `not`, and `printf`. Supported extra functions include `default`, `json`, `json_merge`, `sql`, and no-op-on-non-TTY color wrappers `cyan`, `green`, `red`, `yellow`, and `redBgWhiteFg`. `default` is not a generic two-argument fallback function: for `migrate status` it takes exactly one `*cmdlog.MigrateStatus` argument and renders the normal status report, so `{{default .}}` works. Calling `(default "none" .Current)` fails with `wrong number of args for default: want 1 got 2`. Unknown functions fail during template parsing.

`json VALUE` is compact by default, accepts an indent argument, and accepts prefix+indent arguments; it encodes Unicode/control characters correctly and maps an absent slice to `null`. `json_merge` merges JSON objects left-to-right, with later keys winning, and rejects invalid JSON. `sql` renders schema changes and accepts optional indentation. Template output is sent to stdout exactly, without ANSI escapes when stdout is captured. Parse/execution failures exit nonzero on stderr and retain Go-template wording such as `function "x" not defined`, `unclosed action`, `can't evaluate field`, `index out of range`, or `incompatible types for comparison`. For `migrate status`, `--format '{{ .Status'` reports exactly `Error: parse format: template: format:1: unclosed action`; `--format '{{ .Status.Field }}'` reports exactly `Error: template: format:1:10: executing "format" at <.Status.Field>: can't evaluate field Field in type string`. Applying `--format '{{ .InvalidField }}'` to status exits 1 with no stdout and exactly `Error: template: format:1:3: executing "format" at <.InvalidField>: can't evaluate field InvalidField in type *cmdlog.MigrateStatus` on stderr.

## Spec 31

This is the community edition. The following commands/features are recognized but unavailable: `schema test`, `schema plan`, `schema push`, `migrate checkpoint`, `migrate down`, `migrate rebase`, `migrate rm`, `migrate edit`, `migrate push`, and `migrate test`; also `schema apply --edit/--plan/--include`, `schema diff --include`, `schema clean --dry-run/--format`, and `migrate diff --dry-run`. Flag syntax, required-value validation, command-required-flag validation where noted below, and mutual-exclusion validation happen before the unavailable-feature check: in particular, bare `schema apply --plan` exits 1 and starts stderr with `Error: flag needs an argument: --plan`, rather than using the unsupported-feature notice. Both `schema clean --dry-run` and `schema clean --format x` without a URL exit 1 with no stdout and the ordinary line `Error: required flag(s) "url" not set`, not the community abort. Likewise, `migrate diff --dry-run` without its required state inputs exits 1 with the ordinary line `Error: required flag(s) "to", "dev-url" not set`. On a first qualifying error under a fresh home each of these ordinary lines is followed by Spec 11's troubleshooting block; subsequent qualifying errors under that home have only the line. `migrate diff --edit --dry-run` with its required `--to` and `--dev-url` inputs exits 1 with `Error: if any flags in the group [edit dry-run] are set none of the others can be; [dry-run edit] were all set`, before checking whether dry-run is available. Except for the lone `migrate diff --dry-run` exception described below, recognized unavailable-feature attempts exit 1 and use this pattern:

```text
Abort: 'atlas schema apply --edit' is not supported by the community version.

To install the non-community version of Atlas, use the following command:

	curl -sSf https://atlasgo.sh | sh

Or, visit the website to see all installation options:

	https://atlasgo.io/docs#installation
```

Substitute the exact attempted command/flag. The abort-and-installation notice ends with a blank line: its final URL is followed by two newline bytes. Bare `schema test` follows that rule: it exits 1 with no stdout and uses the block beginning `Abort: 'atlas schema test' is not supported by the community version.` Its help form is an informational exception. `schema test --help` exits 0 with no stderr and prints this block to stdout (also ending with a blank line):

```text
'atlas schema test' is not supported by the community version.

To install the non-community version of Atlas, use the following command:

	curl -sSf https://atlasgo.sh | sh

Or, visit the website to see all installation options:

	https://atlasgo.io/docs#installation

```

Once the required `--to` and `--dev-url` inputs are supplied, lone `migrate diff --dry-run` instead exits 1 with the ordinary diagnostic `Error: '--dry-run' is not supported in the community version`; required-flag validation still takes precedence when those inputs are absent. The same precedence applies to `schema diff --include`: `schema diff --include x` without sources exits 1 with no stdout and the ordinary line `Error: required flag(s) "from", "to" not set`, rather than printing the community abort. The stateful Spec 11 suffix applies when either is the first qualifying error under a fresh home. Multi-environment iteration fails with `Error: multi-environment "NAME" is not supported`. On `migrate apply`, hidden legacy `--log VALUE` and `--format VALUE` are mutually exclusive; supplying both exits 1 with `Error: if any flags in the group [log format] are set none of the others can be; [format log] were all set`. `schema apply --format/--log` without `--dry-run` or `--auto-approve` fails with `Error: --log and --format can only be used with --dry-run or --auto-approve`. These failures must occur predictably without performing database or filesystem changes.
