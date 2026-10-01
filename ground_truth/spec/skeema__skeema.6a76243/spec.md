# Skeema-compatible executable specification

The required artifact is a single executable file named `executable`. It implements the command-line and filesystem behavior below. “Output” means UTF-8 text. Paths shown in messages are the actual paths supplied or discovered at run time; timestamps are generated at run time. MySQL, MariaDB, Docker, the shell, and the filesystem are ordinary facilities available to the executable, not behaviors to emulate as separate commands.

## Spec 1

`executable` is a non-interactive-capable, Unix-style CLI named `skeema`. It accepts the commands `add-environment`, `diff`, `format`, `help`, `init`, `lint`, `pull`, `push`, and `version`; command names are case-sensitive. With no arguments it prints main help to stdout and exits 0. Normal help and version output go only to stdout. Main and command-help pages have a trailing blank line (their last two bytes are both `\n`); the version string ends in one newline. Diagnostics and progress logs go only to stderr.

The normal status meanings are: 0 success/no differences; 1 a non-fatal difference, warning, reformat, or partial unsupported operation as described by the command; 2 a parse or operational failure in the traditional small-code interface; and 78 (`EX_CONFIG`) for command-line/configuration/usage failure. In particular, unknown commands/options, invalid enumerated CLI values, missing required option values, invalid environment names, prohibited option placement, and a missing required `--host` use 78. The explicit empty-host and numeric-port compatibility exceptions are described in Specs 7 and 17: `--host ''` is not treated as a missing value, port 0 uses 3306, and both a nonnumeric port and an out-of-range positive port reach the connection/construction path and use status 2. A port embedded in a hostname that conflicts with the separately configured port also uses status 2, as detailed in Spec 26, rather than the generic status 78. Configured connection-option errors, an external `.skeema` symlink, and the init destination cases have the specific statuses in Specs 11, 13, and 17. Some directory walkers intentionally skip unusable directories, log a warning, and still return 0 if no fatal operation was attempted.

Every ordinary log line has the form `YYYY-MM-DD HH:MM:SS [LEVEL] message\n`. `LEVEL` is `ERROR`, `WARN`, `INFO`, or `DEBUG`; WARN and INFO labels are padded to align with ERROR. Command-line parser errors that concern an option normally prefix the message with `CLI: `. `--debug` may appear before or after a command and does not change the underlying result. For a successful version invocation, both `--debug version` and `version --debug` print the normal version line to stdout and append `[DEBUG] Exit code 0 (SUCCESS)` as the sole stderr log line. On a normal diagnosed failure it instead appends `[DEBUG] Exit code N` without a colon or parenthesized label; for example, `--debug init --host localhost --schema mysql` logs the schema error followed by `[DEBUG] Exit code 78`. This exit record is not unconditional: `unknown-cmd` and `--debug unknown-cmd` both exit 78 with the same sole diagnostic, `[ERROR] Unknown command "unknown-cmd"`.

## Spec 2

The main-help forms `help`, `--help`, and `-?`, and invocation with no arguments, are identical and exit 0. The exact stdout is:

```text

Usage:  skeema [<options>] <command>

Skeema is a declarative schema management system for MySQL and MariaDB. It
allows you to export a database schema to the filesystem, and apply online
schema changes by modifying CREATE statements in .sql files.

Commands:
      add-environment  Add a new named environment to an existing host directory
      diff             Compare a DB server's schemas to the filesystem
      format           Normalize format of filesystem representation of database objects
      help             Display usage information
      init             Save a DB server's schemas to the filesystem
      lint             Check for problems in filesystem representation of database objects
      pull             Update the filesystem representation of schemas
      push             Alter objects on DBs to reflect the filesystem representation
      version          Display program version

Global Options:
  -o, --connect-options value  Comma-separated session options to set upon connecting to each database server
      --debug                  Enable debug logging
  -?, --help[=value]           Display usage information for the specified command
  -H, --host-wrapper value     External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value      Ignore functions that match regex
      --ignore-proc value      Ignore stored procedures that match regex
      --ignore-schema value    Ignore schemas that match regex
      --ignore-table value     Ignore tables that match regex
      --[skip-]my-cnf          Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]       Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value         Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value             Username to connect to database host (default "root")
      --version                Display program version

Complete documentation for this command suite is available online:
https://www.skeema.io/docs/commands

```

The leading blank line and trailing blank line are significant; the exact block ends with `https://www.skeema.io/docs/commands\n\n`.

## Spec 3

Command help is selected equivalently by `help COMMAND`, `COMMAND --help`, or `--help=COMMAND` for the seven principal commands listed below; each exits 0, writes nothing to stderr, starts with a blank line, and ends with a blank line (two terminal newline bytes). An unknown help target exits 2 and logs `[ERROR] Unknown command "NAME"`. All invalid-help forms produce the same diagnostic. `help help` prints main help. The special forms `--help=version`, `version --help`, and `version help` print the version-command help page (usage `skeema version [<options>]` and description `Display program version`); plain `version` and `--version` print the version string. `--help` takes precedence over ordinary valid flags, but not over a bare password prompt: `--help --password` attempts the prompt, and with non-TTY stdin exits 78 after writing `Enter password:`, `[ERROR] STDIN must be a TTY to read password`, and the non-interactive password guidance from Spec 5 to stderr. An unknown flag is still an error even if `--help` is present. Bare `-h` is not global help: outside a command that defines it, it is `Unknown option "h"`.

Each help page uses `Usage:  skeema COMMAND [<options>]` followed by either `[<environment>]`, `<environment>`, or no operand as appropriate, explanatory paragraphs, named option groups, `Global Options:` exactly as in Spec 2, and the final URL `https://www.skeema.io/docs/commands/COMMAND`. The command-page option groups and memberships are normative:

- `init`: `Init Options:` with `-d/--dir` default `<hostname>`, `-h/--host`, `--include-auto-inc`, `-P/--port` default `3306`, `--schema`, `-S/--socket` default `/tmp/mysql.sock`, and `--strip-partitioning`.
- `add-environment`: `Add-Environment Options:` with `-d/--dir` default `.`, `-h/--host`, `-P/--port` default `3306`, and `-S/--socket` default `/tmp/mysql.sock`.
- `pull`: `Pull Options:` with `--[skip-]format` enabled by default, `--include-auto-inc`, `--[skip-]new-schemas` enabled by default, `--strip-partitioning`, and `--update-partitioning`; then Workspace Options.
- `format`: `Format Options:` with `--strip-partitioning` and `--[skip-]write` enabled by default; then Workspace Options.
- `lint`: Format Options, Linter Rule Options, Workspace Options.
- `diff`: External Tool, SQL Generation, Linter Rule, Safety, Sharding, Workspace, and Global Options.
- `push`: the same groups as diff, except it adds `--dry-run` and `--foreign-key-checks`, and has no `--brief`.

Help text must explain that the optional environment defaults to `production`; diff emits DDL and is push dry-run; format canonicalizes SHOW CREATE; lint checks rules and may format; pull refreshes files; push executes changes; and init exports server schemas while excluding system schemas.

The exact version-command help produced by `version help`, `version --help`, and `--help=version` is:

```text

Usage:  skeema version [<options>]

Display program version

Global Options:
  -o, --connect-options value  Comma-separated session options to set upon connecting to each database server
      --debug                  Enable debug logging
  -?, --help[=value]           Display usage information for the specified command
  -H, --host-wrapper value     External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value      Ignore functions that match regex
      --ignore-proc value      Ignore stored procedures that match regex
      --ignore-schema value    Ignore schemas that match regex
      --ignore-table value     Ignore tables that match regex
      --[skip-]my-cnf          Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]       Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value         Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value             Username to connect to database host (default "root")
      --version                Display program version

Complete documentation for this command is available online:
https://www.skeema.io/docs/commands/version

```

The exact stdout for the principal command help pages follows. These blocks include their leading blank line and trailing blank line; the fence itself is not output.

Command `init`:

```text

Usage:  skeema init [<options>] [<environment>]

Creates a filesystem representation of the schemas on a database server. For
each schema on the DB server (or just the single schema specified by --schema),
a subdir with a .skeema config file will be created. Each directory will be
populated with .sql files containing CREATE statements for every table and
routine in the schema.

When operating on all schemas on the server, this command automatically skips
pre-installed / system schemas (information_schema, performance_schema, mysql,
sys, test).

You may optionally pass an environment name as a command-line arg. This will
affect which section of .skeema config files the host-related options are
written to. For example, running `skeema init staging` will add config
directives to the [staging] section of config files. If no environment name is
supplied, the default is "production", so directives will be written to the
[production] section of the file.

Init Options:
  -d, --dir value              Subdir name to use for this host's schemas (default "<hostname>")
  -h, --host value             Database hostname or IP address
      --include-auto-inc       Include starting auto-inc values in table files
  -P, --port value             Port to use for database host (default "3306")
      --schema value           Only import the one specified schema; skip creation of subdirs for each schema
  -S, --socket value           Absolute path to Unix socket file used if host is localhost (default "/tmp/mysql.sock")
      --strip-partitioning     Omit PARTITION BY clause when writing partitioned tables to filesystem

Global Options:
  -o, --connect-options value  Comma-separated session options to set upon connecting to each database server
      --debug                  Enable debug logging
  -?, --help[=value]           Display usage information for the specified command
  -H, --host-wrapper value     External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value      Ignore functions that match regex
      --ignore-proc value      Ignore stored procedures that match regex
      --ignore-schema value    Ignore schemas that match regex
      --ignore-table value     Ignore tables that match regex
      --[skip-]my-cnf          Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]       Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value         Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value             Username to connect to database host (default "root")
      --version                Display program version

Complete documentation for this command is available online:
https://www.skeema.io/docs/commands/init

```

Command `diff`:

```text

Usage:  skeema diff [<options>] [<environment>]

Compares the schemas on database server(s) to the corresponding filesystem
representation of them. The output is a series of DDL commands that, if run on
the DB server, would cause its schemas to now match the definitions from the
filesystem.

You may optionally pass an environment name as a command-line arg. This will
affect which section of .skeema config files is used for processing. For
example, running `skeema diff staging` will apply config directives from the
[staging] section of config files, as well as any sectionless directives at the
top of the file. If no environment name is supplied, the default is
"production".

The `skeema diff` command is equivalent to running `skeema push` with its
--dry-run option enabled.

An exit code of 0 will be returned if no differences were found; 1 if some
differences were found; or 2+ if an error occurred.

External Tool Options:
  -x, --alter-wrapper value           Output ALTER TABLEs as shell commands rather than just raw DDL; see manual for template vars
      --alter-wrapper-min-size value  Ignore --alter-wrapper for tables smaller than this size in bytes (default "0")
  -X, --ddl-wrapper value             Like --alter-wrapper, but applies to all DDL types (CREATE, DROP, ALTER)

SQL Generation Options:
      --alter-algorithm value         Apply an ALGORITHM clause to all ALTER TABLEs (valid values: "inplace", "copy", "instant", "nocopy")
      --alter-lock value              Apply a LOCK clause to all ALTER TABLEs (valid values: "none", "shared", "exclusive")
      --alter-validate-virtual        Apply a WITH VALIDATION clause to ALTER TABLEs affecting virtual columns
      --compare-metadata              For stored programs, detect changes to creation-time sql_mode or DB collation
      --exact-match                   Follow *.sql table definitions exactly, even for differences with no functional impact
      --lax-column-order              When comparing tables, don't re-order columns if they only differ by position
      --lax-comments                  When comparing tables or routines, don't modify them if they only differ by comment clauses
      --partitioning value            Specify handling of partitioning status on the database side (valid values: "keep", "remove", "modify") (default "keep")

Linter Rule Options:
      --allow-auto-inc value          List of allowed auto_increment column data types for --lint-auto-inc (default "int unsigned, bigint unsigned")
      --allow-charset value           List of allowed character sets for --lint-charset (default "latin1,utf8mb4")
      --allow-compression value       List of allowed compression settings for --lint-compression (default "none,4kb,8kb")
      --allow-definer value           List of allowed definer users for --lint-definer (default "%@%")
      --allow-engine value            List of allowed storage engines for --lint-engine (default "innodb")
      --allow-pk-type value           List of allowed data types for --lint-pk-type
      --[skip-]lint                   Check modified objects for problems before proceeding (enabled by default; disable with --skip-lint)
      --lint-auto-inc value           Only allow auto_increment column data types listed in --allow-auto-inc (valid values: "ignore", "warning", "error") (default "warning")
      --lint-charset value            Only allow character sets listed in --allow-charset (valid values: "ignore", "warning", "error") (default "warning")
      --lint-compression value        Only allow compression settings listed in --allow-compression (valid values: "ignore", "warning", "error") (default "warning")
      --lint-definer value            Only allow definer users listed in --allow-definer for stored objects (valid values: "ignore", "warning", "error") (default "error")
      --lint-display-width value      Only allow default display width for int types (valid values: "ignore", "warning", "error") (default "warning")
      --lint-dupe-index value         Flag redundant secondary indexes (valid values: "ignore", "warning", "error") (default "warning")
      --lint-engine value             Only allow storage engines listed in --allow-engine (valid values: "ignore", "warning", "error") (default "warning")
      --lint-fk-parent value          Flag foreign keys where same-schema parent table is missing or lacks unique key on referenced columns (valid values: "ignore", "warning", "error") (default "warning")
      --lint-has-enum value           Flag columns using ENUM or SET data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-fk value             Flag any use of foreign keys; intended for environments that restrict their presence (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-float value          Flag columns using FLOAT or DOUBLE data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-routine value        Flag any use of stored procs or funcs; intended for environments that restrict their presence (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-time value           Flag columns using TIMESTAMP, DATETIME, or TIME data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-name-case value          Flag tables that have uppercase letters in their names (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-pk value                 Flag tables that lack a primary key (valid values: "ignore", "warning", "error") (default "warning")
      --lint-pk-type value            Only allow primary keys to have types listed in --allow-pk-type (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-reserved-word value      Flag names of tables, columns, or routines that used reserved words (valid values: "ignore", "warning", "error") (default "warning")
      --lint-zero-date value          Flag DATE, DATETIME, and TIMESTAMP columns that have zero-date default values (valid values: "ignore", "warning", "error") (default "warning")

Safety Options:
      --allow-unsafe                  Permit generating ALTER or DROP operations that are potentially destructive
      --safe-below-size value         Always permit generating destructive operations for tables below this size in bytes (default "0")
      --[skip-]verify                 Test all generated ALTER statements on temp schema to verify correctness (enabled by default; disable with --skip-verify)

Sharding Options:
  -q, --brief                         Don't output DDL to STDOUT; instead output list of database servers with at least one difference
  -c, --concurrent-servers value      Perform operations on this number of database servers concurrently (default "1")
  -1, --first-only                    For dirs mapping to multiple hosts or schemas, only run against the first target per dir

Workspace Options:
      --docker-cleanup value          With --workspace=docker, specifies how to clean up containers (valid values: "none", "stop", "destroy") (default "none")
  -t, --temp-schema value             Name of temporary schema for intermediate operations, created and dropped each run (default "_skeema_tmp")
      --temp-schema-binlog value      Controls whether temp schema DDL operations are replicated (valid values: "on", "off", "auto") (default "auto")
      --temp-schema-mode value        Tunes workspace load with workspace=temp-schema; heavier load makes Skeema faster but may disrupt other workloads on the database (valid values: "serial", "light", "regular", "heavy", "extreme") (default "regular")
      --temp-schema-threads value     Deprecated manner of controlling workspace load with workspace=temp-schema (default "5")
  -w, --workspace value               Specifies where to run intermediate operations (valid values: "temp-schema", "docker") (default "temp-schema")

Global Options:
  -o, --connect-options value         Comma-separated session options to set upon connecting to each database server
      --debug                         Enable debug logging
  -?, --help[=value]                  Display usage information for the specified command
  -H, --host-wrapper value            External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value             Ignore functions that match regex
      --ignore-proc value             Ignore stored procedures that match regex
      --ignore-schema value           Ignore schemas that match regex
      --ignore-table value            Ignore tables that match regex
      --[skip-]my-cnf                 Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]              Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value                Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value                    Username to connect to database host (default "root")
      --version                       Display program version

Complete documentation for this command is available online:
https://www.skeema.io/docs/commands/diff

```

Command `pull`:

```text

Usage:  skeema pull [<options>] [<environment>]

Updates the existing filesystem representation of the schemas on a DB server.
Use this command when changes have been applied to the database manually or
outside of Skeema, in order to make the filesystem representation reflect those
changes.

You may optionally pass an environment name as a command-line arg. This will
affect which section of .skeema config files is used for processing. For
example, running `skeema pull staging` will apply config directives from the
[staging] section of config files, as well as any sectionless directives at the
top of the file. If no environment name is supplied, the default is
"production".

Pull Options:
      --[skip-]format              Reformat SQL statements to match canonical SHOW CREATE (enabled by default; disable with --skip-format)
      --include-auto-inc           Include starting auto-inc values in new table files, and update in existing files
      --[skip-]new-schemas         Detect any new schemas and populate new dirs for them (enabled by default; disable with --skip-new-schemas)
      --strip-partitioning         Omit PARTITION BY clause when writing partitioned tables to filesystem
      --update-partitioning        Update PARTITION BY clauses in existing table files

Workspace Options:
      --docker-cleanup value       With --workspace=docker, specifies how to clean up containers (valid values: "none", "stop", "destroy") (default "none")
  -t, --temp-schema value          Name of temporary schema for intermediate operations, created and dropped each run (default "_skeema_tmp")
      --temp-schema-binlog value   Controls whether temp schema DDL operations are replicated (valid values: "on", "off", "auto") (default "auto")
      --temp-schema-mode value     Tunes workspace load with workspace=temp-schema; heavier load makes Skeema faster but may disrupt other workloads on the database (valid values: "serial", "light", "regular", "heavy", "extreme") (default "regular")
      --temp-schema-threads value  Deprecated manner of controlling workspace load with workspace=temp-schema (default "5")
  -w, --workspace value            Specifies where to run intermediate operations (valid values: "temp-schema", "docker") (default "temp-schema")

Global Options:
  -o, --connect-options value      Comma-separated session options to set upon connecting to each database server
      --debug                      Enable debug logging
  -?, --help[=value]               Display usage information for the specified command
  -H, --host-wrapper value         External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value          Ignore functions that match regex
      --ignore-proc value          Ignore stored procedures that match regex
      --ignore-schema value        Ignore schemas that match regex
      --ignore-table value         Ignore tables that match regex
      --[skip-]my-cnf              Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]           Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value             Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value                 Username to connect to database host (default "root")
      --version                    Display program version

Complete documentation for this command is available online:
https://www.skeema.io/docs/commands/pull

```

Command `push`:

```text

Usage:  skeema push [<options>] [<environment>]

Modifies the schemas on database server(s) to match the corresponding filesystem
representation of them. This essentially performs the same diff logic as `skeema
diff`, but then actually runs the generated DDL. You should generally run
`skeema diff` first to see what changes will be applied.

You may optionally pass an environment name as a command-line arg. This will
affect which section of .skeema config files is used for processing. For
example, running `skeema push staging` will apply config directives from the
[staging] section of config files, as well as any sectionless directives at the
top of the file. If no environment name is supplied, the default is
"production".

An exit code of 0 will be returned if the operation was fully successful; 1 if
at least one table could not be updated due to use of unsupported features, or
if the --dry-run option was used and differences were found; or 2+ if a fatal
error occurred.

External Tool Options:
  -x, --alter-wrapper value           External bin to shell out to for ALTER TABLE; see manual for template vars
      --alter-wrapper-min-size value  Ignore --alter-wrapper for tables smaller than this size in bytes (default "0")
  -X, --ddl-wrapper value             Like --alter-wrapper, but applies to all DDL types (CREATE, DROP, ALTER)

SQL Generation Options:
      --alter-algorithm value         Apply an ALGORITHM clause to all ALTER TABLEs (valid values: "inplace", "copy", "instant", "nocopy")
      --alter-lock value              Apply a LOCK clause to all ALTER TABLEs (valid values: "none", "shared", "exclusive")
      --alter-validate-virtual        Apply a WITH VALIDATION clause to ALTER TABLEs affecting virtual columns
      --compare-metadata              For stored programs, detect changes to creation-time sql_mode or DB collation
      --exact-match                   Follow *.sql table definitions exactly, even for differences with no functional impact
      --lax-column-order              When comparing tables, don't re-order columns if they only differ by position
      --lax-comments                  When comparing tables or routines, don't modify them if they only differ by comment clauses
      --partitioning value            Specify handling of partitioning status on the database side (valid values: "keep", "remove", "modify") (default "keep")

Linter Rule Options:
      --allow-auto-inc value          List of allowed auto_increment column data types for --lint-auto-inc (default "int unsigned, bigint unsigned")
      --allow-charset value           List of allowed character sets for --lint-charset (default "latin1,utf8mb4")
      --allow-compression value       List of allowed compression settings for --lint-compression (default "none,4kb,8kb")
      --allow-definer value           List of allowed definer users for --lint-definer (default "%@%")
      --allow-engine value            List of allowed storage engines for --lint-engine (default "innodb")
      --allow-pk-type value           List of allowed data types for --lint-pk-type
      --[skip-]lint                   Check modified objects for problems before proceeding (enabled by default; disable with --skip-lint)
      --lint-auto-inc value           Only allow auto_increment column data types listed in --allow-auto-inc (valid values: "ignore", "warning", "error") (default "warning")
      --lint-charset value            Only allow character sets listed in --allow-charset (valid values: "ignore", "warning", "error") (default "warning")
      --lint-compression value        Only allow compression settings listed in --allow-compression (valid values: "ignore", "warning", "error") (default "warning")
      --lint-definer value            Only allow definer users listed in --allow-definer for stored objects (valid values: "ignore", "warning", "error") (default "error")
      --lint-display-width value      Only allow default display width for int types (valid values: "ignore", "warning", "error") (default "warning")
      --lint-dupe-index value         Flag redundant secondary indexes (valid values: "ignore", "warning", "error") (default "warning")
      --lint-engine value             Only allow storage engines listed in --allow-engine (valid values: "ignore", "warning", "error") (default "warning")
      --lint-fk-parent value          Flag foreign keys where same-schema parent table is missing or lacks unique key on referenced columns (valid values: "ignore", "warning", "error") (default "warning")
      --lint-has-enum value           Flag columns using ENUM or SET data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-fk value             Flag any use of foreign keys; intended for environments that restrict their presence (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-float value          Flag columns using FLOAT or DOUBLE data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-routine value        Flag any use of stored procs or funcs; intended for environments that restrict their presence (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-time value           Flag columns using TIMESTAMP, DATETIME, or TIME data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-name-case value          Flag tables that have uppercase letters in their names (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-pk value                 Flag tables that lack a primary key (valid values: "ignore", "warning", "error") (default "warning")
      --lint-pk-type value            Only allow primary keys to have types listed in --allow-pk-type (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-reserved-word value      Flag names of tables, columns, or routines that used reserved words (valid values: "ignore", "warning", "error") (default "warning")
      --lint-zero-date value          Flag DATE, DATETIME, and TIMESTAMP columns that have zero-date default values (valid values: "ignore", "warning", "error") (default "warning")

Safety Options:
      --allow-unsafe                  Permit running ALTER or DROP operations that are potentially destructive
      --dry-run                       Output DDL but don't run it; equivalent to `skeema diff`
      --foreign-key-checks            Force the server to check referential integrity of any new foreign key
      --safe-below-size value         Always permit destructive operations for tables below this size in bytes (default "0")
      --[skip-]verify                 Test all generated ALTER statements on temp schema to verify correctness (enabled by default; disable with --skip-verify)

Sharding Options:
  -c, --concurrent-servers value      Perform operations on this number of database servers concurrently (default "1")
  -1, --first-only                    For dirs mapping to multiple hosts or schemas, only run against the first target per dir

Workspace Options:
      --docker-cleanup value          With --workspace=docker, specifies how to clean up containers (valid values: "none", "stop", "destroy") (default "none")
  -t, --temp-schema value             Name of temporary schema for intermediate operations, created and dropped each run (default "_skeema_tmp")
      --temp-schema-binlog value      Controls whether temp schema DDL operations are replicated (valid values: "on", "off", "auto") (default "auto")
      --temp-schema-mode value        Tunes workspace load with workspace=temp-schema; heavier load makes Skeema faster but may disrupt other workloads on the database (valid values: "serial", "light", "regular", "heavy", "extreme") (default "regular")
      --temp-schema-threads value     Deprecated manner of controlling workspace load with workspace=temp-schema (default "5")
  -w, --workspace value               Specifies where to run intermediate operations (valid values: "temp-schema", "docker") (default "temp-schema")

Global Options:
  -o, --connect-options value         Comma-separated session options to set upon connecting to each database server
      --debug                         Enable debug logging
  -?, --help[=value]                  Display usage information for the specified command
  -H, --host-wrapper value            External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value             Ignore functions that match regex
      --ignore-proc value             Ignore stored procedures that match regex
      --ignore-schema value           Ignore schemas that match regex
      --ignore-table value            Ignore tables that match regex
      --[skip-]my-cnf                 Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]              Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value                Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value                    Username to connect to database host (default "root")
      --version                       Display program version

Complete documentation for this command is available online:
https://www.skeema.io/docs/commands/push

```

Command `format`:

```text

Usage:  skeema format [<options>] [<environment>]

Reformats the filesystem representation of database objects to match the
canonical format shown in SHOW CREATE.

This command relies on accessing a database server to test the SQL DDL in a
temporary location. See the --workspace option for more information.

You may optionally pass an environment name as a command-line arg. This will
affect which section of .skeema config files is used for workspace selection.
For example, running `skeema format staging` will apply config directives from
the [staging] section of config files, as well as any sectionless directives at
the top of the file. If no environment name is supplied, the default is
"production".

An exit code of 0 will be returned if all files were already formatted properly;
1 if some files were not already in the correct format; or 2+ if any errors
occurred.

Format Options:
      --strip-partitioning         Remove PARTITION BY clauses from *.sql files
      --[skip-]write               Update files to correct format (enabled by default; disable with --skip-write)

Workspace Options:
      --docker-cleanup value       With --workspace=docker, specifies how to clean up containers (valid values: "none", "stop", "destroy") (default "none")
  -t, --temp-schema value          Name of temporary schema for intermediate operations, created and dropped each run (default "_skeema_tmp")
      --temp-schema-binlog value   Controls whether temp schema DDL operations are replicated (valid values: "on", "off", "auto") (default "auto")
      --temp-schema-mode value     Tunes workspace load with workspace=temp-schema; heavier load makes Skeema faster but may disrupt other workloads on the database (valid values: "serial", "light", "regular", "heavy", "extreme") (default "regular")
      --temp-schema-threads value  Deprecated manner of controlling workspace load with workspace=temp-schema (default "5")
  -w, --workspace value            Specifies where to run intermediate operations (valid values: "temp-schema", "docker") (default "temp-schema")

Global Options:
  -o, --connect-options value      Comma-separated session options to set upon connecting to each database server
      --debug                      Enable debug logging
  -?, --help[=value]               Display usage information for the specified command
  -H, --host-wrapper value         External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value          Ignore functions that match regex
      --ignore-proc value          Ignore stored procedures that match regex
      --ignore-schema value        Ignore schemas that match regex
      --ignore-table value         Ignore tables that match regex
      --[skip-]my-cnf              Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]           Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value             Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value                 Username to connect to database host (default "root")
      --version                    Display program version

Complete documentation for this command is available online:
https://www.skeema.io/docs/commands/format

```

Command `lint`:

```text

Usage:  skeema lint [<options>] [<environment>]

Checks for problems in filesystem representation of database objects. A set of
linter rules are run against all objects. Each rule may be configured to
generate an error, a warning, or be ignored entirely. Statements that contain
invalid SQL, or otherwise return an error from the database, are always flagged
as linter errors.

By default, this command also reformats CREATE statements to their canonical
form, just like `skeema format`.

This command relies on accessing a database server to test the SQL DDL in a
temporary location. See the --workspace option for more information.

You may optionally pass an environment name as a command-line arg. This will
affect which section of .skeema config files is used for linter configuration
and workspace selection. For example, running `skeema lint staging` will apply
config directives from the [staging] section of config files, as well as any
sectionless directives at the top of the file. If no environment name is
supplied, the default is "production".

An exit code of 0 will be returned if no errors or warnings were emitted and all
files were already formatted properly; 1 if any warnings were emitted and/or
some files were reformatted; or 2+ if any errors were emitted for any reason.

Format Options:
      --[skip-]format              Reformat SQL statements to match canonical SHOW CREATE (enabled by default; disable with --skip-format)
      --strip-partitioning         Remove PARTITION BY clauses from *.sql files

Linter Rule Options:
      --allow-auto-inc value       List of allowed auto_increment column data types for --lint-auto-inc (default "int unsigned, bigint unsigned")
      --allow-charset value        List of allowed character sets for --lint-charset (default "latin1,utf8mb4")
      --allow-compression value    List of allowed compression settings for --lint-compression (default "none,4kb,8kb")
      --allow-definer value        List of allowed definer users for --lint-definer (default "%@%")
      --allow-engine value         List of allowed storage engines for --lint-engine (default "innodb")
      --allow-pk-type value        List of allowed data types for --lint-pk-type
      --lint-auto-inc value        Only allow auto_increment column data types listed in --allow-auto-inc (valid values: "ignore", "warning", "error") (default "warning")
      --lint-charset value         Only allow character sets listed in --allow-charset (valid values: "ignore", "warning", "error") (default "warning")
      --lint-compression value     Only allow compression settings listed in --allow-compression (valid values: "ignore", "warning", "error") (default "warning")
      --lint-definer value         Only allow definer users listed in --allow-definer for stored objects (valid values: "ignore", "warning", "error") (default "error")
      --lint-display-width value   Only allow default display width for int types (valid values: "ignore", "warning", "error") (default "warning")
      --lint-dupe-index value      Flag redundant secondary indexes (valid values: "ignore", "warning", "error") (default "warning")
      --lint-engine value          Only allow storage engines listed in --allow-engine (valid values: "ignore", "warning", "error") (default "warning")
      --lint-fk-parent value       Flag foreign keys where same-schema parent table is missing or lacks unique key on referenced columns (valid values: "ignore", "warning", "error") (default "warning")
      --lint-has-enum value        Flag columns using ENUM or SET data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-fk value          Flag any use of foreign keys; intended for environments that restrict their presence (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-float value       Flag columns using FLOAT or DOUBLE data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-routine value     Flag any use of stored procs or funcs; intended for environments that restrict their presence (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-has-time value        Flag columns using TIMESTAMP, DATETIME, or TIME data types (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-name-case value       Flag tables that have uppercase letters in their names (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-pk value              Flag tables that lack a primary key (valid values: "ignore", "warning", "error") (default "warning")
      --lint-pk-type value         Only allow primary keys to have types listed in --allow-pk-type (valid values: "ignore", "warning", "error") (default "ignore")
      --lint-reserved-word value   Flag names of tables, columns, or routines that used reserved words (valid values: "ignore", "warning", "error") (default "warning")
      --lint-zero-date value       Flag DATE, DATETIME, and TIMESTAMP columns that have zero-date default values (valid values: "ignore", "warning", "error") (default "warning")

Workspace Options:
      --docker-cleanup value       With --workspace=docker, specifies how to clean up containers (valid values: "none", "stop", "destroy") (default "none")
  -t, --temp-schema value          Name of temporary schema for intermediate operations, created and dropped each run (default "_skeema_tmp")
      --temp-schema-binlog value   Controls whether temp schema DDL operations are replicated (valid values: "on", "off", "auto") (default "auto")
      --temp-schema-mode value     Tunes workspace load with workspace=temp-schema; heavier load makes Skeema faster but may disrupt other workloads on the database (valid values: "serial", "light", "regular", "heavy", "extreme") (default "regular")
      --temp-schema-threads value  Deprecated manner of controlling workspace load with workspace=temp-schema (default "5")
  -w, --workspace value            Specifies where to run intermediate operations (valid values: "temp-schema", "docker") (default "temp-schema")

Global Options:
  -o, --connect-options value      Comma-separated session options to set upon connecting to each database server
      --debug                      Enable debug logging
  -?, --help[=value]               Display usage information for the specified command
  -H, --host-wrapper value         External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value          Ignore functions that match regex
      --ignore-proc value          Ignore stored procedures that match regex
      --ignore-schema value        Ignore schemas that match regex
      --ignore-table value         Ignore tables that match regex
      --[skip-]my-cnf              Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]           Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value             Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value                 Username to connect to database host (default "root")
      --version                    Display program version

Complete documentation for this command is available online:
https://www.skeema.io/docs/commands/lint

```

Command `add-environment`:

```text

Usage:  skeema add-environment [<options>] <environment>

Modifies the .skeema file in an existing host directory to add a new named
environment. For example, if `skeema init` was previously used to create a dir
for a host with the default "production" environment, `skeema add-environment`
could be used to define a "staging" or "development" environment pointing at a
different host and port, or perhaps a "local" environment pointing at localhost
and a socket path.

This command currently only handles very simple cases. For many situations,
editing .skeema files directly is a better approach.

Add-Environment Options:
  -d, --dir value              Base dir for this host's schemas (default ".")
  -h, --host value             Database hostname or IP address
  -P, --port value             Port to use for database host (default "3306")
  -S, --socket value           Absolute path to Unix socket file used if host is localhost (default "/tmp/mysql.sock")

Global Options:
  -o, --connect-options value  Comma-separated session options to set upon connecting to each database server
      --debug                  Enable debug logging
  -?, --help[=value]           Display usage information for the specified command
  -H, --host-wrapper value     External bin to shell out to for host lookup; see manual for template vars
      --ignore-func value      Ignore functions that match regex
      --ignore-proc value      Ignore stored procedures that match regex
      --ignore-schema value    Ignore schemas that match regex
      --ignore-table value     Ignore tables that match regex
      --[skip-]my-cnf          Parse ~/.my.cnf for configuration (enabled by default; disable with --skip-my-cnf)
  -p, --password[=value]       Password for database user; omit value to prompt from TTY (default "$MYSQL_PWD")
      --ssl-mode value         Specify desired connection security SSL/TLS usage (valid values: "disabled", "preferred", "required")
  -u, --user value             Username to connect to database host (default "root")
      --version                Display program version

Complete documentation for this command is available online:
https://www.skeema.io/docs/commands/add-environment

```

## Spec 4

`version` and `--version` are identical, take precedence over valid command behavior, and exit 0. Their sole output matches exactly this grammar (including commas, spaces, UTC `Z`, lowercase hexadecimal, and newline):

```text
skeema version MAJOR.MINOR.PATCH-community, commit HEXHASH, released YYYY-MM-DDTHH:MM:SSZ
```

Use semantic numeric components, a nonempty hex commit (at least seven characters), and a valid-looking timestamp. The compatibility version represented by the executable is Skeema `1.13.2-community`; therefore text or generated metadata that needs the running version uses `1.13.2-community`.

## Spec 5

Options may generally occur before or after the command. Long required-value options accept `--name=value` and `--name value`; short required-value forms accept `-u value` and concatenation such as `-ualice`. The exact parser quirks are preserved: a lone `-u` followed by `version` treats the would-be command as the missing value situation, prints main usage, and exits 0; optional-value password does not consume a space-separated token. Thus the token after `--password` or `-p` is not its value, whereas `--password=secret` and `-psecret` set the password. A bare `-p`/`--password` always attempts the prompt before dispatching any following token: for example, `--password version` with non-TTY stdin does not print the version and exits 78. Its stderr, in order, is `Enter password:`, `[ERROR] STDIN must be a TTY to read password`, and `[ERROR] Interactive password prompting requires an input terminal. To supply a password non-interactively, configure the password value in a global option file, or supply it directly on the command-line, or set the $MYSQL_PWD environment variable. For more information, see https://www.skeema.io/docs/options/#password`.

`--` ends option parsing. If it occurs before a command, the next token is interpreted as a literal command; if after a command, remaining tokens are operands. Extra operands produce `Extra command-line arg "ARG" supplied; command CMD takes a max of N args`. Combined arbitrary short flags are unsupported and parsing reports the first character as the option: `-vh` exits 78 with `CLI: Unknown option "v"`. A missing required value says `Missing required value for option NAME`. Unknown long flags omit leading hyphens in `CLI: Unknown option "NAME"`; an unknown command says `Unknown command "NAME"`.

## Spec 6

Global options are those in Spec 2. Defaults are user `root`, password from `MYSQL_PWD`, SSL mode `preferred`, and my.cnf reading enabled. `--my-cnf` and `--skip-my-cnf` are boolean opposites. `--skip-my-cnf` remains accepted and, even on an otherwise empty successful command such as `push --skip-my-cnf`, emits exactly `[WARN]  Option --my-cnf is deprecated. This option will be removed in Skeema v2, and .my.cnf will always be parsed, with additional safety logic already in place. For more information, visit https://www.skeema.io/v2-changes` and exits 0. Passwords must never be echoed in output, including debug logs.

Ignore options are repeatable RE2-compatible regular expressions. Compile them before any database work. A command-line invalid pattern exits 78 and its sole diagnostic is `Invalid regexp for option OPTION: PATTERN`, with no `CLI:` prefix or regex-engine explanation. Thus `diff --ignore-table +` reports `Invalid regexp for option ignore-table: +`, and `diff --ignore-proc ***` reports `Invalid regexp for option ignore-proc: ***`. Lookahead, lookbehind, and backreferences are likewise rejected because RE2 does not support them. Apply ignore-schema to target schemas and the object-specific patterns to table/function/procedure names.

`--host` and `--schema` are intentionally not global command-line options: they are accepted for init (and host for add-environment), but rejected for diff/lint/format/pull/push with status 78. Supplying either before any command, as in `skeema --host global-not-allowed` or `skeema --schema global-not-allowed`, is rejected the same way rather than being reported as an unknown option. The exact diagnostic is `The host option cannot be set via command line for this command. For more information, visit https://www.skeema.io/docs/config/#limitations-on-host-and-schema-options`, substituting `schema` for `host` as applicable. If both are supplied to diff, report the host error only.

## Spec 7

Command-line enumerated-value validation occurs before traversal or connection, except for the numeric port construction behavior stated below. Effective configured values are validated when their mapped directory is processed; for lint this is after its applicable `Linting PATH` headings have been emitted. Enumerations are:

- `ssl-mode`: `disabled`, `preferred`, `required`, or the empty string.
- `workspace`: `temp-schema`, `docker`.
- `docker-cleanup`: `none`, `stop`, `destroy`.
- `temp-schema-binlog`: `on`, `off`, `auto` (default `auto`).
- `temp-schema-mode`: `serial`, `light`, `regular`, `heavy`, `extreme` (default `regular`).
- `alter-algorithm`: `inplace`, `copy`, `instant`, `nocopy`.
- `alter-lock`: `none`, `shared`, `exclusive`.
- `partitioning`: `keep`, `remove`, `modify` (default `keep`).
- every `lint-*` severity: `ignore`, `warning`, `error`.

Invalid values name the option, invalid value, and valid choices. For `ssl-mode`, trim surrounding whitespace before validation but do not remove internal whitespace or otherwise normalize the value. Thus `--ssl-mode='required '` is accepted and reaches connection, while the observed invalid forms `req uired`, `verify-ca`, `verify-identity`, `true`, `0`, `req`, `require`, `required;DROP TABLE`, `required=extra`, and the Cyrillic-lookalike `requіred` are rejected. Direct command-line rejection exits 78 and says exactly `Invalid connection options: Option ssl-mode can only be set to one of these values: "disabled", "preferred", "required", ""`. An explicit `--ssl-mode=` is accepted, not treated as a missing required value, and proceeds to the connection attempt. The same allowed-choice text is used when an invalid configured value is discovered in a mapped directory.

Integer options include port, concurrent-servers, safe-below-size, alter-wrapper-min-size, and temp-schema-threads. Concurrent servers must be at least 1; `0` or negative produces `concurrent-instances cannot be less than 1`. `concurrent-instances` is a deprecated alias and conflicts if the new and old names are set differently. Port 0 is treated as the default 3306; an explicitly supplied `--port 0` still selects TCP, so `init --host localhost --port 0` attempts `localhost:3306`. A positive port above 65535 is not rejected as CLI/config status 78: connection construction fails with status 2 and `dial tcp: address PORT: invalid port`. For init the line is `Unable to connect to localhost:PORT for PATH: dial tcp: address PORT: invalid port`; for a mapped diff directory it is `Skipping localhost:PORT for PATH: dial tcp: address PORT: invalid port`, followed by `Skipped 1 operation due to problem`. A nonnumeric port, including direct `--port notanumber`, falls back to 3306 rather than producing an integer-parser error; init then attempts the connection and exits 2 on failure. Pull accepts `--strip-partitioning` and `--update-partitioning` together; with a mapped localhost schema and no socket server it proceeds to the ordinary status-1 socket connection warning rather than rejecting the combination.

Deprecated aliases remain accepted with warnings: `concurrent-instances`, `--skip-normalize` (alias of `--skip-format`), `--reuse-temp-schema`, `--warnings`/legacy lint controls, and `temp-schema-threads`. Supplying any numeric value to `--temp-schema-threads` emits exactly `[WARN]  Option --temp-schema-threads is deprecated. This option will be removed in Skeema v2. Use the new temp-schema-mode enum option instead. See --help or visit https://www.skeema.io/docs/options/#temp-schema-mode`; on an otherwise empty `push --temp-schema-threads=3`, this is the sole diagnostic and the status is 0.

## Spec 8

The executable reads files named `.skeema` as an INI-like configuration. A file consists of sectionless `name=value` directives and `[environment]` sections. Blank lines and full-line `#` or `;` comments are ignored; an unquoted `#` following a value begins an inline comment; comment markers inside quotes remain data. CRLF, LF, and mixed endings work. Surrounding key/value whitespace is trimmed. Single- or double-quoted values lose the surrounding quotes; `=` inside a value is retained. Empty values are permitted where the option permits them. In particular, an explicit `ignore-table=` is valid: it is not a missing required value, and processing proceeds to the normal connection or workspace stage. Unicode and long values must not crash. Duplicate scalar options in one effective scope use the last value; repeatable `ignore-*` directives accumulate. Duplicate sections merge in file order, again with later scalar values winning. Section names may contain letters, digits, dash, dot, and underscore, but not brackets, CR, LF, or be unterminated.

Errors identify file and 1-based line: `Parse error in PATH/.skeema line N: unterminated section name`, `PATH/.skeema line N: Unknown option "NAME"`, or `Missing required value for option NAME`. An empty section is legal. A malformed section-like line that is not an unterminated header is not silently reinterpreted as a valid environment. The `user` option specifically accepts an empty value after trimming: a whitespace-only `user=   ` does not produce a missing-value error, and connection processing proceeds (for example to `prod.example.com:3306`).

## Spec 9

The selected environment is the sole optional operand of init/diff/pull/push/format/lint and the required operand of add-environment. It defaults to the exact lowercase name `production`; environment lookup is case-sensitive. An explicitly empty operand is accepted by format: `format ""` in an empty directory exits 0 and emits its normal `Reformatting PATH` INFO line rather than an invalid-environment error. Sectionless directives always apply, and matching-section directives override them. If the requested section is absent, sectionless directives still apply. Command-line values override directory configuration except prohibited host/schema CLI placement.

For `diff ENV` on a directory whose `.skeema` has a schema only in another environment section and no applicable sectionless schema, exit 0 and emit exactly `[WARN]  Skipping PATH: no schema defined for environment "ENV"` followed by `[WARN]  Other environments do define a schema name. Refer to the .skeema file in this directory for details.` This applies to ordinary absent names as well as punctuation: with only `[production]` defining `schema`, `diff nonexistent` substitutes `nonexistent`, and `diff .` substitutes `.`.

Configuration inherits down the directory tree. Starting at the working/target directory, combine ancestor `.skeema` files from outermost to innermost, then the local file; closer directives override ancestors. Stop parent discovery at a `.git` repository boundary. This inheritance includes host, port, user, workspace, default-character-set/collation, flavor, ignore rules, lint settings, and schema. A child may independently override only port or another field while retaining an ancestral host.

## Spec 10

User-global configuration is `$HOME/.skeema`. For diff, lint, format, pull, and push, `host` or `schema` may not be supplied there: return 78 and say `host option cannot be set` (or schema) and identify `/.skeema`. Init may use global host configuration and is not subject to this restriction, although its explicit `--host` requirement remains where applicable.

Unless disabled, parse `$HOME/.my.cnf` client options for connection defaults without exposing credentials. Explicit CLI and `.skeema` values override these defaults. Environment variables are inherited normally; `MYSQL_PWD` supplies the password default. Shell-like `$NAME` text in `.skeema` values is expanded where configuration supports environment interpolation, without executing it as a command.

## Spec 11

`connect-options` is a comma-separated list of `name=value` session/driver parameters. Commas and equals signs inside correctly quoted values are data; backslash may escape separators. Reject missing values, empty entries/trailing commas, duplicate keys, quotes in option names, unterminated quotes, and malformed trailing escapes. A malformed value supplied directly on the command line exits 78 and logs `[ERROR] Invalid connection options: DETAIL`, without `CLI:`. The following direct invocations establish the exact detail strings:

- `no_value`: `Option no_value is missing a value at byte offset 8 in connect-options "no_value"`.
- `opt1=val1,opt2=val2,opt1=val3`: `Option opt1 is set multiple times in connect-options "opt1=val1,opt2=val2,opt1=val3"`.
- `opt=val,`: `Invalid comma placement in option value at byte offset 8 in connect-options "opt=val,"`.
- `opt=va\` (one terminal backslash): `Trailing backslash in connect-options "opt=va\"`.
- `'unterminated` (the quote is in the name): `Invalid quote character in option name at byte offset 0 in connect-options "'unterminated"`.
- `opt='unterminated`: `Unterminated quote in connect-options "opt='unterminated"`.
- `opt1=val1,opt2=has=equals`: `Invalid equals-sign character in option value at byte offset 18 in connect-options "opt1=val1,opt2=has=equals"`.

Configured malformed values retain the configuration-specific forms where applicable. A quoted value with no closing quote is a status-78 `.skeema` parse error: `[ERROR] Parse error in PATH/.skeema line N: Quoted value has no terminating quote`; `Value ends in a single backslash` uses the analogous file-and-line parse-error form. Other connection-option errors encountered while constructing a mapped connection use `[ERROR] Skipping PATH: Invalid connection options: DETAIL`, return 2, and are followed by `[ERROR] Skipped 1 operation due to problem`. Exact configured examples are:

- `key=val=other`: `Invalid equals-sign character in option value at byte offset 7 in connect-options "key=val=other"`.
- `name_without_value`: `Option name_without_value is missing a value at byte offset 18 in connect-options "name_without_value"`.
- `'quoted_name'=value`: `Invalid quote character in option name at byte offset 0 in connect-options "'quoted_name'=value"`.
- `key1=value1,key1=value2`: `Option key1 is set multiple times in connect-options "key1=value1,key1=value2"`.
- `key=,other=value`: `Invalid comma placement in option value at byte offset 4 in connect-options "key=,other=value"`.

An unquoted extra `=` in a value is rejected when it makes the pair ambiguous; quoted values may contain it. Dedicated connection properties must not be smuggled through this string: both `autocommit` and `multistatements` are rejected, with `connect-options is not allowed to contain NAME` as the detail. Thus configured `multistatements=true` produces `connect-options is not allowed to contain multistatements` in the mapped-connection error.

Driver-specific entries such as TLS settings are accepted, but legacy `tls=preferred` emits `[WARN]  Setting the tls option in connect-options is deprecated, and will no longer be allowed in Skeema v2. Use the dedicated ssl-mode option instead.` before the later connection result. If `ssl-mode` is explicitly supplied as well as a `tls` connect option, reject the combination with `Invalid connection options: When using the ssl-mode option, connect-options should not also set the tls field`. A direct CLI conflict exits 78. When the conflict comes from an effective mapped-directory configuration, the same text follows `Skipping PATH: ` and the command exits 2 with the normal skipped-operation summary.

## Spec 12

Directory-oriented commands start from the current directory unless their command defines `--dir`. They recurse through ordinary subdirectories to find independently configured schema branches. A descendant is not normally made into a schema mapping merely by inheriting a parent's connection settings or by containing a SQL file: an ordinary child with SQL but no child `.skeema` is ignored. For example, if a configured root has `not_a_schema/table.sql` but `not_a_schema` has no `.skeema`, `diff` does not connect for that child and silently exits 0. There is a specific wildcard exception: an effective `schema=*` makes conventional immediate schema subdirectories into discoverable branches, so a child such as `mydb/` is traversed and its `users.sql` is parsed even if `mydb/` has no `.skeema`. The wildcard-bearing parent is not terminal. At the traversal limit, pull exits 1 and writes `[ERROR] Not walking subdirs of PATH: max depth reached`, where PATH is the deepest directory whose children were not visited. Format uses the same exact ERROR-level line but treats the skipped descent as nonfatal and exits 0 if nothing else fails. Hidden directories (names beginning with `.`) are skipped. A truly empty/unmapped directory and a directory containing only irrelevant files are valid no-ops. In contrast, a directory whose `.skeema` explicitly maps a schema is processed even if it contains no SQL files; format logs its `Reformatting PATH` line and validates workspace inputs. If that mapped directory has neither the required host nor flavor, it exits 78 with the either-host-or-flavor error instead of treating the directory as an empty no-op. Spaces, Unicode, very long names, many SQL files, absolute paths, and relative multi-component paths are supported.

Only files whose extension compares case-insensitively equal to `.sql` are SQL inputs. Other files are neither parsed nor modified. Empty, whitespace-only, and comments-only SQL files are harmless. A UTF-8 BOM is accepted. LF, CRLF, mixed endings, and missing final newline are accepted.

## Spec 13

Symlinks are handled conservatively relative to a repository root (the closest tree boundary used for configuration). A direct symlink to a regular `.sql` or `.skeema` file inside the repository may be followed. Broken links, links to non-regular objects, circular links, chains of links, and SQL links escaping the repository are ignored rather than followed indefinitely. A `.skeema` symlink escaping the repository exits 2 with `PATH/.skeema is a symlink pointing outside of its repo`, for both absolute and relative escaping targets. A `.skeema` symlink to a directory or to another symlink also exits 2 and says exactly `PATH/.skeema is not a regular file, nor a symlink to a regular file`. Processing the same object through a real file and symlink must not silently create two conflicting definitions; report the duplicate when both resolve as processable definitions. The duplicate diagnostic uses the full discovered paths of both entries, including the ordinary file path: `table \`NAME\` defined multiple times in same directory: PATH/link.sql line N and PATH/original.sql line N`.

## Spec 14

Before attempting workspace creation or database access, lex every SQL input into statements with 1-based start line and column. Keywords are case-insensitive. Recognize `CREATE TABLE`, `CREATE [OR REPLACE] PROCEDURE`, `FUNCTION`, `VIEW`, `TRIGGER`, `ALTER TABLE`, `USE`, and otherwise unsupported statements without crashing. Every lexically closed unknown statement is retained as an unsupported/unparsed statement in the directory parse result rather than silently discarded. Top-level `GRANT` and standalone `SET` statements specifically follow this nonfatal unsupported path; they are not parse errors. On an otherwise processable `workspace=docker` lint operation, an arbitrary unknown statement, `GRANT`, or standalone `SET` therefore permits processing to continue to Docker discovery. Support `IF NOT EXISTS`, schema-qualified and backtick-quoted names, doubled backticks, Unicode identifiers, DEFINER variants, generated columns, CHECK/foreign-key/fulltext/spatial constraints, partition clauses, comments inside statements, and multiple adjacent statements/empty semicolons.

Recognize MySQL comments (`#`, `--` only when followed by whitespace/control, `/*...*/`, and `/*!...*/`), single and double quoted strings, doubled-quote and backslash escapes, national `N'...'` literals, hex and bit literals, integers/decimals/leading-dot/scientific notation, and unusual whitespace. Delimiters begin as `;`; a line-oriented `DELIMITER token` changes them, allowing compound `BEGIN...END`, loops, declarations, and embedded semicolons. Delimiter tokens may be multi-character or Unicode and occurrences inside quotes/comments do not terminate statements.

## Spec 15

Malformed lexical constructs are fatal before missing-host/workspace errors. Return 2 and identify the file plus the opening location, using messages such as `File PATH: String is missing closing quote at line N, column C` and `Comment starting with /* is never closed at line N, column C`. For an unterminated block comment, the line is 1-based but the reported column is the zero-based byte offset of the opening `/` within that line; an opening slash at the twelfth character is therefore reported as `line 2, column 11`. Most unterminated input follows that ordinary parse-error path, but preserve the reference's specific unterminated-backtick bug: an unterminated backtick identifier in a CREATE statement exits 2 and emits these three ERROR messages, in order: `Uncaught panic in github.com/skeema/skeema/internal/tengo.(*parser).skipUntilSequence at github.com/skeema/skeema/internal/tengo/parser.go:<error location>: runtime error: index out of range [0] with length 0`; `This situation indicates a bug in Skeema. Use --debug to view full stack trace.`; and `Please file an issue report at https://github.com/skeema/skeema/issues with any available background information.` It must terminate rather than hang. A syntactically incomplete but lexically closed statement may be retained as unsupported/unparsed instead of crashing.

Within one directory, create-object identity is `(object type, exact object name)`. Two tables, two procedures, or two functions of the same exact name are duplicates even within one file. Report `table|procedure|function \`NAME\` defined multiple times in same directory`, followed by both filenames and precise start lines (`first.sql line 1 and second.sql line 5`). Procedure and function names occupy different namespaces. `ALTER` and `USE` statements are tracked separately and do not count as duplicate CREATE definitions. Name comparison is case-sensitive at this pre-server stage.

## Spec 16

When a directory is usable as a filesystem schema but lacks connection/workspace information, validation happens after SQL parsing. Diff and push treat a missing host as a warning and return 0 if nothing else fails. They emit `[WARN]  Skipping PATH: no host defined for environment "ENV"` followed by `[WARN]  This command requires a hostname, which can be specified using the host option in a [ENV] section of the .skeema file in this directory, or in a parent directory.` Pull instead treats a mapped schema lacking a host as bad configuration and returns 78. Its two lines are `[ERROR] Skipping PATH: No host defined for environment "ENV"` and `[ERROR] This command requires a hostname to pull from, which can be specified using the host option in a [ENV] section of the .skeema file in this directory, or in a parent directory.` These paths do not append an aggregate `Skipped N operations` line. Lint/format require either `host` with `workspace=temp-schema` or `flavor` with `workspace=docker`; their error contains exactly `This command needs either a host (with workspace=temp-schema) or flavor (with workspace=docker), but one is not configured for environment "ENV"`. Walkers continue to other sibling directories where safe.

Schema-selection patterns are not compiled during the earlier ignore-regexp/config preflight. For example, with an effective `schema=/[/` and no host, `diff` follows the missing-host warning path above and exits 0; it does not report the malformed schema pattern first. Schema selection is server-dependent and is evaluated only after a connection has been obtained, so a connection failure likewise precedes any such pattern error.

An empty directory without `.skeema` is a successful silent no-op for diff/pull/push. Format may emit its normal INFO heading but does not invent SQL work; lint's mandatory heading and status-0 behavior are specified in Spec 20. A malformed root configuration prevents traversal below it; a malformed child is logged and does not prevent unrelated siblings from being considered.

## Spec 17

`init [environment]` requires the `--host` option to occur on the command line; if it is absent, return 78 with `Option --host must be supplied on the command-line`. An explicitly present empty value is a compatibility exception: `init --host ''` uses the empty host text as its default destination, attempts to create that empty path, and exits 73 with `Cannot create dir : mkdir : no such file or directory`. Validate the environment and schema before connecting. Environment names are nonempty and may contain letters, digits, dash, dot, and underscore, but not brackets, CR, or LF. Reject `mysql`, `information_schema`, `performance_schema`, `sys`, and `test` case-insensitively as explicit `--schema`, saying `Option --schema may not be set to a system database name`.

The destination defaults to the host text, adding `:PORT` for a nondefault TCP port; `--dir` overrides it and may be absolute, relative, nested, Unicode, or contain spaces. Create missing destination parents and the destination before connecting, so it remains after connection failure. Refuse collisions before connecting and never overwrite them. An existing `.skeema` returns 78 with `Cannot use dir PATH: already has .skeema file`; any existing SQL file returns 78 with `Cannot use dir PATH: already contains *.sql files`. If an ancestor `.skeema` defines `schema`, return 78 with `Cannot use dir PATH: an ancestor option file defines schema option`. If PATH is occupied by a regular file, return 73 with `Cannot create dir PATH: mkdir PATH: not a directory`. Like the explicit empty-host case above, a whitespace-only host derives an empty destination name after trimming; directory creation fails before connection with status 73 and `Cannot create dir : mkdir : no such file or directory`.

For `host=localhost` with no explicit port, use the Unix socket (default `/tmp/mysql.sock` or `--socket`). Its failure form is `Unable to connect to localhost:SOCKET for PATH: dial unix SOCKET: connect: no such file or directory` and exits 2. Explicit port requests TCP. For an unused localhost port such as 3307, the observed failure is `Unable to connect to localhost:3307 for PATH: dial tcp [::1]:3307: connect: connection refused`, also with status 2. A nonnumeric explicit port falls back to 3306 and has the same TCP form with `localhost:3306` and `[::1]:3306`. A negative port has a separate construction failure: `init --host localhost --port=-1` exits 78 and emits `Invalid connection information for PATH/localhost:-1 (DSN=root@tcp(localhost:-1)/?allowFallbackToPlaintext=true&default_storage_engine=%27InnoDB%27&foreign_key_checks=0&interpolateParams=true&readTimeout=20s&timeout=5s&tls=oldtls&writeTimeout=5s): invalid port -1 supplied`. For `--host 127.0.0.1` with an unused explicit port, the exact suffix is lowercase Go-style text: `Unable to connect to 127.0.0.1:PORT for PATH: dial tcp 127.0.0.1:PORT: connect: connection refused`. This applies whether or not `--schema` names a nonexistent server schema, because connection failure occurs first. Port 0 and out-of-range ports otherwise behave as specified in Spec 7. Other hosts use TCP. The evaluated behavior ends at connection failure; successful server introspection/export is not part of this contract.

## Spec 18

`add-environment [options] ENV` requires exactly one valid environment and an existing directory (default `.`) containing `.skeema`. With no ENV, it returns 78 and writes `Too few positional args supplied on command line; command add-environment requires at least 1 args`. It also requires that some existing section already defines a host and that `--host` is supplied. Missing file, nonexistent `--dir`, a regular-file `--dir`, duplicate section, invalid name, or no prior host returns 78 without modifying the file. The missing-file diagnostic is `Dir PATH does not have an existing .skeema file! Can only use \`skeema add-environment\` on a dir previously created by \`skeema init\``. An existing regular-file target uses `--dir=PATH already exists but is not a directory`. Omitting the command-line host uses exactly `` `skeema add-environment` requires --host to be supplied on command-line ``. Other exact messages include `Environment name "ENV" is invalid`, `Environment name "ENV" already defined in PATH/.skeema`, `In add-environment, --dir must refer to a directory that already exists`, and `This command should be run against a --dir whose .skeema file already defines a host for another environment`.

On success, parse and rewrite the complete config deterministically, preserve existing section order, append a blank line and `[ENV]`, alphabetize options within every section, and end with newline. Existing comments need not survive this normalized rewrite. The new section contains explicit nondefault/relevant connectivity and ignore options. A remote host gets `host=...` and `port=...` (including default 3306); localhost with a socket gets `host=localhost` and `socket=...` rather than port. Store user, connect-options, ssl-mode, and ignore-* when supplied. If host-wrapper resolves hosts, write the resolved first host rather than the placeholder. Log `Added environment [ENV] to PATH/.skeema` at INFO level and exit 0.

For example, adding staging produces this shape:

```text
[production]
host=localhost
port=3306
schema=mydb

[staging]
host=192.168.1.100
port=3307
```

## Spec 19

`format [environment]` parses the directory tree and obtains a workspace for a mapped schema or for processable CREATE definitions. Default `--write` is write mode and uses a `Reformatting PATH` progress description; `--skip-write` is check-only and uses `Checking format of PATH`. Empty/comment-only SQL files are harmless and non-SQL files are never modified during these preflight/error paths. A directory containing only a recognized `CREATE VIEW` or `ALTER TABLE` statement logs the normal progress line but exits 0 without workspace validation; these statement categories are parsed but are not format targets in this community behavior. `--strip-partitioning` is accepted. Actual canonical SQL generation after successful workspace creation is outside this contract.

Return 0 if no change was needed, 1 if files were/would be reformatted, and 2/78 on operational/config failure according to Spec 1. Invalid `.skeema`, bad regex, SQL lexical failure, missing workspace inputs, external symlinks, and unavailable Docker are reported before changes unsafe to perform. The format traversal-limit case is the nonfatal status-0 exception described in Spec 12.

## Spec 20

`lint [environment]` parses all schema SQL, validates rule settings, and then attempts to obtain a workspace. It accepts optional formatting (`--format` default; `--skip-format` disables). For every selected directory whose SQL files are harmless or parse successfully, lint emits the INFO line `Linting PATH` before any later configuration or workspace diagnostic. This is mandatory for empty, whitespace-only, and comments-only `.sql` files; incomplete but lexically closed statements; ordinary and multiple CREATE statements; delimiter changes and compound or nested routine bodies; comments; `USE` statements; long statements; and quoted or special-character identifiers. A lexical failure such as the unterminated-backtick panic in Spec 15 occurs earlier and therefore has no `Linting` line. An empty directory is a successful operation, not a completely silent no-op: it exits 0 after emitting the single INFO line `Linting PATH`. A mapped directory without the required host/flavor still emits `Linting PATH` first, then the directory-specific either-host-or-flavor error and fatal-error summary from Spec 16, and exits 78. Lint otherwise returns 2 or 78 for parse/config/workspace failures as specified elsewhere. Invalid configured severity values are rejected before workspace access. For an effective `lint-pk=invalid_value`, the exact sequence is the INFO line `Linting PATH`, `[ERROR] Skipping directory BASENAME due to error: Option lint-pk can only be set to one of these values: "ignore", "warning", "error"`, and `[ERROR] Skipped 1 operation due to fatal errors`, with status 78. Other severity names substitute into that same option message; validation aborts the affected directory on an invalid setting rather than emitting a synthetic combined-severity diagnostic. For effective `lint-charset=warning` with an empty `allow-charset`, the corresponding status-78 sequence is `Linting PATH`, `[ERROR] Skipping directory BASENAME due to error: With option lint-charset=warning, corresponding option allow-charset must be non-empty`, and `[ERROR] Skipped 1 operation due to fatal errors`. Actual inspection of successfully loaded database objects is outside this contract.

Severity options and defaults are: warning for `lint-auto-inc`, `lint-charset`, `lint-compression`, `lint-display-width`, `lint-dupe-index`, `lint-engine`, `lint-fk-parent`, `lint-pk`, `lint-reserved-word`, and `lint-zero-date`; error for `lint-definer`; ignore for `lint-has-enum`, `lint-has-fk`, `lint-has-float`, `lint-has-routine`, `lint-has-time`, `lint-name-case`, and `lint-pk-type`. Config and CLI settings may override any with `ignore|warning|error`. Each documented severity option also accepts its boolean negation spelling, such as `--skip-lint-auto-inc`; this is an alias for setting that individual rule to `ignore`, not an unknown option. The legacy/hidden `lint-nullable` option is also accepted at the three explicit severities, but is not added to the byte-exact help block above.

## Spec 21

The lint help page descriptions and corresponding option behavior have these meanings. The 18 options present in its exact help block must remain documented; the hidden `lint-nullable` only needs to parse/configure without being reported as unknown.

- auto-inc: AUTO_INCREMENT type must appear in allow-auto-inc (default `int unsigned, bigint unsigned`).
- charset: table/column character sets must appear in allow-charset (default `latin1,utf8mb4`).
- compression: compression must be in allow-compression (default `none,4kb,8kb`).
- definer: routine definer must match allow-definer (default `%@%`).
- engine: storage engine must be in allow-engine (default `innodb`).
- pk-type: every primary-key column type must be in allow-pk-type.
- display-width: integer display width must equal the type's conventional width.
- dupe-index: flag secondary indexes whose ordered columns are redundant with another key.
- fk-parent: same-schema parent table must exist and have a unique key over referenced columns.
- has-enum, has-fk, has-float, has-routine, has-time: flag presence of the named construct (SET accompanies ENUM; DOUBLE accompanies FLOAT; DATE/DATETIME/TIMESTAMP/TIME are temporal as appropriate).
- name-case: flag uppercase table names.
- nullable: flag nullable columns.
- pk: flag tables with no primary key.
- reserved-word: flag reserved table, column, and routine identifiers.
- zero-date: flag zero DATE/DATETIME/TIMESTAMP defaults.

Allow lists are comma-separated, trimmed, case-insensitive where SQL semantics are case-insensitive, and accept multiple values. `--skip-lint` suppresses pre-push/diff linting but not SQL parse errors.

## Spec 22

`pull [environment]` recursively discovers mapped schema directories, performs all preflight parsing/validation, and attempts a connection for each usable mapping. The options `format/skip-format`, `new-schemas/skip-new-schemas`, `include-auto-inc/skip-include-auto-inc`, `strip-partitioning`, and `update-partitioning` are accepted with the defaults shown in help. Pull also accepts the hidden command-line option `--flavor=VALUE`, although it is not listed in pull help; `--flavor=mysql` remains accepted when combined with `--skip-format`. Default formatting emits a DEBUG-level compatibility notice only when debug logging is enabled: `Upgrade notice: the --format option, which currently defaults to true in Skeema v1, will change to default to false in Skeema v2. For more information, visit https://www.skeema.io/v2-changes`. On an otherwise empty successful `pull --debug`, this notice is followed by `[DEBUG] Exit code 0`. Explicit `--format` or `--skip-format` suppresses the notice, leaving `[DEBUG] Exit code 0` as the sole line for the equivalent empty successful debug invocation.

`--skip-new-schemas` only disables discovery/population of new schema directories; it does not suppress processing or connection of an already mapped directory. For a mapping with `host=127.0.0.1`, `port=3306`, and `schema=mydb` when nothing is listening, `pull --skip-new-schemas` emits `[WARN]  Skipping PATH: Unable to connect to 127.0.0.1:3306 for PATH: dial tcp 127.0.0.1:3306: connect: connection refused` and exits 1.

A directory containing only SQL files but no `.skeema` mapping is a silent status-0 pull no-op. Conversely, an explicit schema mapping is processed even when no SQL files exist. An explicit empty `schema=` is valid and maps all schemas rather than removing the mapping; with `host=localhost` and no socket server this reaches the usual status-1 socket connection warning. Pull accepts `--workspace=docker` but still connects to the mapped database host for export: a mapped `host=localhost` and `schema=test` reaches the ordinary status-1 `/tmp/mysql.sock` warning without requiring `flavor` or looking for the Docker CLI.

Missing-host behavior is the command-specific status-78 path in Spec 16. A configured host-wrapper is executed even when there is no static host placeholder; if it yields no hosts, pull exits 78 and writes `[ERROR] Skipping PATH: No host defined for environment "ENV"` followed by `[ERROR] The host-wrapper option controls which hosts this directory maps to, but the executed script returned no hostnames.` A root parse error prevents work; a child parse error skips that child and continues, using `[WARN]  Skipping CHILD: Parse error in CHILD/.skeema line N: REASON`; if that is the only discovered error, the status is 78. A generator major version newer than the running major blocks the directory with status 2. For `generator=skeema:9.0.0-community` while running this v1 executable, the exact diagnostic is `Directory NAME was generated using Skeema v9, but you are running Skeema v1. In order to interact with this directory, you must download a newer version of Skeema.` A newer minor/premium generator emits `[WARN]  Directory NAME was generated using an enhanced paid edition of Skeema, but you are currently running Skeema Community Edition.` before any subsequent missing-host diagnostic and continues. In a Skeema generator value, omitting the edition suffix is interpreted as an enhanced paid edition, not as Community Edition: both `generator=skeema:1.99.0` and an unlabeled current-version value produce that paid-edition warning. A different generator program emits `[WARN]  Directory NAME was generated using \`PROGRAM\`, not \`skeema\`` and then continues to the ordinary connection/configuration check; for example, `generator=other:9.0.0` substitutes `other` for `PROGRAM`. These generator preflight messages are the same for diff and pull. Successful database export and resulting file mutations are outside this contract.

## Spec 23

`diff [environment]` advertises comparison of live schemas with filesystem CREATE definitions and DDL output, but evaluated execution covers its CLI, configuration, filesystem/SQL preflight, wrapper resolution, and connection/workspace failure paths. It never modifies SQL files in those paths. `push --dry-run` accepts the same comparison-related options. Empty/no-config directories return 0; so does a directory that only configures `workspace=docker` and `flavor` but has no schema mapping or processable SQL objects. That no-change case does not look for the Docker CLI and writes nothing to stderr. Fatal parse/config failures use 2 or 78.

The options `--brief`, `--first-only`, `--exact-match`, `--compare-metadata`, `--lax-column-order`, `--lax-comments`, `--alter-algorithm`, `--alter-lock`, `--alter-validate-virtual`, `--partitioning`, `--allow-unsafe`, `--safe-below-size`, `--verify/--skip-verify`, all linter options, all wrapper options, and all workspace options must be documented and accepted for diff as shown in help. Their post-connection DDL effects are outside this contract.

## Spec 24

`push [environment]` exposes the same preflight surface as diff, plus `--dry-run` and `--foreign-key-checks`. By default lint and verification flags are enabled; `--skip-lint` and `--skip-verify` are accepted. All safety, sharding, comparison, linter, wrapper, connection, and workspace options shown in push help may be combined without becoming unknown-option errors, subject to their value/conflict validation. Empty/no-config directories are successful no-ops. As with diff, `workspace=docker` plus a flavor but no schema mapping or processable SQL objects is also a silent status-0 no-op and does not require the Docker CLI. Actual DDL planning/execution after a successful connection is outside this contract.

On an otherwise empty directory, `push --debug` exits 0 and emits the sole line `[DEBUG] Exit code 0 (SUCCESS)`. The accepted compatibility options below each emit their stated warning as the sole diagnostic and still exit 0 in that situation:

- Each of `--temp-schema-binlog=off`, `--temp-schema-binlog=auto`, and `--temp-schema-binlog=on` emits `[WARN]  Option --temp-schema-binlog is deprecated. This option will be removed in Skeema v2, with "auto" behavior always being used. For more information, visit https://www.skeema.io/v2-changes`.
- `--lint-display-width=warning` emits `[WARN]  Option --lint-display-width is deprecated. This option will be removed in Skeema v2. For more information, visit https://www.skeema.io/v2-changes`.

`alter-wrapper`, `ddl-wrapper`, and `alter-wrapper-min-size` are accepted together and documented with their intended DDL scope. Since evaluated paths do not generate live DDL, invoking these wrappers after successful schema comparison is outside this contract.

## Spec 25

`host-wrapper` is a shell command used to dynamically map a directory to hosts. Diff retains the reference's placeholder requirement: if a mapped diff directory configures `host-wrapper` but has no nonempty `host`, do not execute the wrapper. Exit 0 and emit `[WARN]  Skipping PATH: no host defined for environment "ENV"` followed by `[WARN]  The host-wrapper option controls which hosts this directory maps to, but a .skeema file also needs to set the host option to some value (even just a placeholder value) for this command to properly map directories to hosts and schemas.` Pull's distinct no-placeholder behavior is stated in Spec 22. When a wrapper is eligible to run, execute it through a shell so quoted arguments, variables, command substitution, pipes, redirection, spaces in paths, and working-directory changes behave normally. Do not impose a small stdout/stderr limit. Nonzero exit, signal termination, Docker-style 125, or no non-whitespace output is an operational error. In particular, an unquoted executable path containing a space is split by the shell; if its prefix is not found, pass the shell's `/bin/sh: 1: PREFIX: not found` line through to stderr, then emit `[ERROR] Skipping PATH: exit status 127` and `[ERROR] Skipped 1 operation due to problem`, and exit 2.

Split successful output into hosts by newline when any newline is present; otherwise split by commas, tabs, or spaces. Trim leading/trailing delimiters and discard empty fields, preserve Unicode, host:port text, original order, and duplicates. A trailing delimiter does not add an empty host. The wrapper may use documented template variables and shell `${VAR}` syntax; malformed template-variable syntax is diagnosed rather than panicking.

## Spec 26

Connection construction supports TCP host/port and localhost Unix sockets, username/password, session connect-options, and SSL modes. `disabled` makes an unencrypted connection, `preferred` attempts TLS with fallback where driver/server permits, and `required` requires TLS. Invalid SSL mode is rejected before connection. Pull treats per-directory connection failures as partial failures: it exits 1, emits one WARN per failed mapping, and does not append an aggregate summary. For a configured nonexistent socket, the exact form is `[WARN]  Skipping PATH: Unable to connect to localhost:SOCKET for PATH: dial unix SOCKET: connect: no such file or directory`; this includes the literal Go-style `dial unix ...: connect: no such file or directory` suffix. It applies both to the default `/tmp/mysql.sock` and to a supplied path such as `/nonexistent/path/to/mysql.sock`, and remains status 1 with multiple mapped schema directories. Diff uses the same Go-style socket suffix but its error form is `[ERROR] Skipping localhost:SOCKET for PATH: dial unix SOCKET: connect: no such file or directory`, followed by `[ERROR] Skipped 1 operation due to problem`, and exits 2. A host containing `:port` supplies its port; if a separate different port is also configured, diff exits 2 with `[ERROR] Skipping PATH: Port was supplied as P1 inside hostname HOST:P1 but as P2 in option file`, followed by `[ERROR] Skipped 1 operation due to problem`.

For TCP connection refusal to the numeric loopback mapping `127.0.0.1:3306`, diff emits exactly `[ERROR] Skipping 127.0.0.1:3306 for PATH: dial tcp 127.0.0.1:3306: connect: connection refused`, followed by `[ERROR] Skipped 1 operation due to problem`, and exits 2. This form is unchanged when `--alter-wrapper`, `--ddl-wrapper`, or both are present; when `--alter-wrapper-min-size` is 0, 100, or a large accepted integer; or when a wrapper command contains template syntax, `${...}` shell syntax, quotes, shell metacharacters, multiple arguments, or a space-containing command string. These options are accepted before the attempted connection and do not replace its diagnostic.

Except for the exact init, pull, diff-TCP, and diff-socket forms specified above, preserve the host, port/socket, operation, and underlying platform error without substituting a different diagnostic style. Authentication and TLS errors likewise retain the server/driver cause.

## Spec 27

Workspace `temp-schema` requires a host and uses `_skeema_tmp` by default (or `--temp-schema`), creating and dropping it for validation. Workspace `docker` requires `flavor` and the `docker` CLI once format, lint, diff, or push has a mapped, processable workspace operation; the silent no-change diff/push exception is in Specs 23 and 24, and pull's host-connection behavior is the separate exception in Spec 22. For lint on a processable child directory when the client is absent, emit, in order: `Linting ROOT`; `Linting PATH`; `[ERROR] Skipping directory ROOT_BASENAME/CHILD_BASENAME due to error: unable to find \`docker\` command-line client among directories in PATH`; `[ERROR] Skeema v1.11+ no longer includes a built-in Docker client. If you are using workspace=docker while also running \`skeema\` itself in a container, be sure to put a Linux \`docker\` client CLI binary in the container as well.`; `[ERROR] For more information, see https://github.com/skeema/skeema/issues/186#issuecomment-1648483625`; and `[ERROR] Skipped 1 operation due to fatal errors`. Exit 2. The same three Docker-error lines and fatal-error summary are mandatory when the processable mapping is the current directory; in that case they follow its single `Linting PATH` heading and `Skipping directory BASENAME` line. A valid `connect-options` setting does not alter or precede this sequence. Missing flavor is detected after the applicable lint headings and exits 78 with `[ERROR] Skipping directory RELATIVE_DIRECTORY due to error: ` followed by the exact either-host-or-flavor message in Spec 16, then `[ERROR] Skipped 1 operation due to fatal errors`.

Recognize MySQL 5.7, 8.0, and 8.4, Percona 8.0, and MariaDB 10.5, 10.11, and 11.4 without a flavor warning; if Docker is absent, each proceeds directly from its lint headings to the Docker-client error sequence above. MySQL 5.5/5.6 and MariaDB 10.1/11.1 syntax is also recognized, with deprecation warnings where the reference emits them. MySQL 5.5 emits exactly `[WARN]  workspace=docker: MySQL 5.5 is deprecated in this release of Skeema. The next major version of Skeema will likely drop support for this database server.` after the lint headings and before Docker discovery. MySQL 5.0 is rejected after the applicable `Linting PATH` heading with `[ERROR] Skipping directory RELATIVE_DIRECTORY due to error: MySQL 5.0 is not supported by Skeema.`, followed by `[ERROR] Skipped 1 operation due to fatal errors`, and status 2. An unrecognized flavor such as `unknown:1.0` emits `[WARN]  Flavor unknown:1.0 is not recognized, and may not work properly with workspace=docker` after the two lint headings and before the Docker-client errors; it is not rejected early as an unsupported family. An unrecognized family is canonicalized to `unknown` while retaining its version in this warning: configured `postgresql:14.0` emits `[WARN]  Flavor unknown:14.0 is not recognized, and may not work properly with workspace=docker` and then continues to Docker discovery.

Docker cleanup values `none`, `stop`, and `destroy` are accepted and default to none. For an effective `docker-cleanup=invalid_value` on a processable lint mapping, whether supplied in `.skeema` or as `--docker-cleanup=invalid`, emit the applicable `Linting` heading(s) first, then `[ERROR] Skipping directory RELATIVE_DIRECTORY due to error: Option docker-cleanup can only be set to one of these values: "none", "stop", "destroy"`, then `[ERROR] Skipped 1 operation due to fatal errors`, and exit 78. Workspace option names and enumerated values are accepted consistently by format, lint, diff, pull, and push, but pull has the distinct execution behavior stated in Spec 22. When a processable operation actually needs Docker, configured-value validation and SQL parsing happen first, then the clear Docker error is returned without hanging. Creating, retaining, stopping, or destroying a real container after successful discovery of Docker is outside this contract.

## Spec 28

Filesystem object discovery recognizes table, procedure, function, view, trigger, USE, and ALTER statement categories as described in the parser sections. A deterministic filesystem-safe name mapping uses `.sql`; unusual identifier characters must not permit directory traversal or a crash. Community behavior may identify views/triggers/events as unsupported while still parsing them. No successful server dump, canonical `SHOW CREATE` rewrite, or post-connection object round trip is required by this contract.

## Spec 29

Traversal and preflight operations must be deterministic and robust when multiple command processes run. Sort filesystem entries where stable diagnostic order is required. Accept `concurrent-servers` without allowing preflight output or config rewrites to interleave corruptly. Handle permission errors, broken links, huge but reasonable files/wrapper output, deep structures, BOMs, Unicode, and special characters without deadlock or unbounded recursion; the recovered unterminated-backtick panic in Spec 15 is the sole documented panic exception. Byte-invalid UTF-8 in a SQL file is tolerated by preflight rather than producing an invalid-UTF-8 parse diagnostic: a raw `0xFF` byte inside a block comment or an unquoted identifier still permits a mapped `diff` with no host to reach the ordinary missing-host warning and status 0. Preflight/error paths never delete user files, and add-environment validation failure never partially rewrites `.skeema`.

## Spec 30

Validation order is observable and therefore normative: parse command line; honor help/version; validate option names, placement, types, aliases, and conflicting values; locate and parse configuration hierarchy; validate generator and regex/connect settings other than server-dependent schema selection; discover files safely; lex SQL and detect duplicate definitions; validate host/flavor/workspace; resolve wrappers; connect/create workspace; evaluate any server-dependent schema selection; then format, lint, diff, pull, or push. A schema-selection pattern is specifically governed by Spec 16 rather than the earlier regexp stage. Earlier failures suppress later-stage noise. Across all stages, errors must name the relevant command option, environment, path, object, or host, preserve useful underlying causes, use singular/plural summaries correctly, and never print stack traces or secret values.
