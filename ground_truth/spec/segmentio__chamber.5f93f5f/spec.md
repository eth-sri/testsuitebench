# Clarified executable specification

The deliverable is one directly runnable file named `executable`. The test harness invokes it as a command-line program from the branch root. It must implement the behavior below without depending on repository source files. AWS-compatible HTTP endpoints, credentials, environment variables, standard input, output files, and child commands mentioned below are supplied by the harness at run time.

## Spec 1

`executable` is a Unix command-line program whose application name is always `chamber`, regardless of the filename used to launch it. Successful commands return status 0. CLI, validation, store, parsing, and I/O failures return status 1 unless a successfully launched child process supplies another status. Ordinary results and help go only to stdout; diagnostics go only to stderr. Output must be UTF-8, must not contain tracebacks or panic text, and must terminate complete textual lines with `\n`. Empty-success commands emit no incidental whitespace.

The commands are `completion`, `delete`, `env`, `exec`, `export`, `find`, `help`, `history`, `import`, `list`, `list-services`, `read`, `tag`, `version`, and `write`. `tag` contains `read`, `write`, and `delete`; `completion` contains `bash`, `fish`, `powershell`, and `zsh`.

## Spec 2

The root parser accepts persistent options before or after a command and between positional arguments, up to a literal `--`. Long options accept both `--name value` and `--name=value`. The persistent options are:

```text
-b, --backend string
    --backend-s3-bucket string
    --kms-key-alias string
-r, --retries int
    --retry-mode string
    --verbose
```

Repeated bare Boolean options remain true. Boolean long options also accept `--name=true` and `--name=false`; explicit false disables the option (notably, `find --by-value=false` uses key-search mode). A value-taking option consumes the next token even if that token is a command name. Consumption does not itself initialize or validate the resulting option value: `--backend list version` consumes `list` as the backend value, selects `version` as the command, and succeeds with `chamber dev\n` because `version` is backend-independent. Local options may likewise appear before or after their positionals. A literal `--` stops option parsing; it is structurally significant to `exec` and lets `write` accept values beginning with `-`. Unknown options fail, for example `Error: unknown flag: --does-not-exist\n`. `--version` is not a root option. An unknown root command fails with exactly:

```text
Error: unknown command "NAME" for "chamber"
Run 'chamber --help' for usage.
```

Replacing `NAME` with the supplied token. Known `-h`/`--help` returns help successfully, but it does not make an independently unknown option valid. An unknown subcommand below `tag` displays tag usage/the help hint and returns success, matching the command-group behavior rather than the root unknown-command behavior.

## Spec 3

No arguments, `-h`, `--help`, and `help` print the following exact root help to stdout, with no stderr and status 0. Each `\t` escape visibly written in the block below denotes one literal tab character in actual output; all other alignment is spaces.

```text
CLI for storing secrets

Usage:
  chamber [command]

Available Commands:
  completion    Generate the autocompletion script for the specified shell
  delete        Delete a secret, including all versions
  env           Print the secrets from the parameter store in a format to export as environment variables
  exec          Executes a command with secrets loaded into the environment
  export        Exports parameters in the specified format
  find          Find the given secret across all services
  help          Help about any command
  history       View the history of a secret
  import        import secrets from json or yaml
  list          List the secrets set for a service
  list-services List services
  read          Read a specific secret from the parameter store
  tag           work with tags on secrets
  version       print version
  write         write a secret

Flags:
  -b, --backend string             Backend to use; AKA $CHAMBER_SECRET_BACKEND
                                   \tnull: no-op
                                   \tssm: SSM Parameter Store
                                   \tsecretsmanager: Secrets Manager
                                   \ts3: S3; requires --backend-s3-bucket
                                   \ts3-kms: S3 using AWS-KMS encryption; requires --backend-s3-bucket and --kms-key-alias set (if you want to write or delete keys). (default "ssm")
      --backend-s3-bucket string   bucket for S3 backend; AKA $CHAMBER_S3_BUCKET
  -h, --help                       help for chamber
      --kms-key-alias string       KMS Key Alias for writing and deleting secrets; AKA $CHAMBER_KMS_KEY_ALIAS. This option is currently only supported for the S3-KMS backend. (default "alias/parameter_store_key")
  -r, --retries int                For SSM or Secrets Manager, the number of retries we'll make before giving up; AKA $CHAMBER_RETRIES (default 10)
      --retry-mode string          For SSM, the model used to retry requests
                                     standard
                                     adaptive (default "standard")
      --verbose                    Print more information to STDERR

Use "chamber [command] --help" for more information about a command.
```

`version` prints exactly `chamber dev\n`, accepts and ignores extra positional arguments, and does not initialize or validate a backend. Thus it succeeds even with unusable backend environment configuration. Its help description is `print version`, usage is `chamber version [flags]`, and its sole local flag is `-h, --help   help for version`.

## Spec 4

Every command supports `-h` and `--help`; `help PATH` is identical to `PATH --help`. Help is status 0, stdout-only, and ends in a newline. A leaf help page is constructed as: description, blank line, `Usage:`, two-space-indented usage, blank line, `Flags:`, aligned local flags, blank line, then `Global Flags:` and the persistent flag text from Spec 3 with the root `-h` line omitted. Group pages also list their child commands and end with `Use "chamber GROUP [command] --help" for more information about a command.`

The common `Global Flags:` suffix is exactly the following. The five visible `\t` markers each mean one literal tab in the output.

```text
Global Flags:
  -b, --backend string             Backend to use; AKA $CHAMBER_SECRET_BACKEND
                                   \tnull: no-op
                                   \tssm: SSM Parameter Store
                                   \tsecretsmanager: Secrets Manager
                                   \ts3: S3; requires --backend-s3-bucket
                                   \ts3-kms: S3 using AWS-KMS encryption; requires --backend-s3-bucket and --kms-key-alias set (if you want to write or delete keys). (default "ssm")
      --backend-s3-bucket string   bucket for S3 backend; AKA $CHAMBER_S3_BUCKET
      --kms-key-alias string       KMS Key Alias for writing and deleting secrets; AKA $CHAMBER_KMS_KEY_ALIAS. This option is currently only supported for the S3-KMS backend. (default "alias/parameter_store_key")
  -r, --retries int                For SSM or Secrets Manager, the number of retries we'll make before giving up; AKA $CHAMBER_RETRIES (default 10)
      --retry-mode string          For SSM, the model used to retry requests
                                     standard
                                     adaptive (default "standard")
      --verbose                    Print more information to STDERR
```

For the help pages subject to exact comparison, the text before the blank line and common suffix is exactly one of these blocks:

```text
Delete a secret, including all versions

Usage:
  chamber delete <service> <key> [flags]

Flags:
      --exact-key   Prevent normalization of the provided key in order to delete any keys that match the exact provided casing.
  -h, --help        help for delete
```

```text
Find the given secret across all services

Usage:
  chamber find <secret name> [flags]

Flags:
  -v, --by-value   Find parameters by value
  -h, --help       help for find
```

```text
View the history of a secret

Usage:
  chamber history <service> <key> [flags]

Flags:
  -h, --help   help for history
```

```text
import secrets from json or yaml

Usage:
  chamber import <service> <file|-> [flags]

Flags:
  -h, --help                           help for import
      --normalize-keys chamber write   Normalize keys to match how chamber write would handle them. If not specified, keys will be written exactly how they are defined in the import source.
```

```text
List the secrets set for a service

Usage:
  chamber list <service> [flags]

Flags:
  -e, --expand    Expand parameter list with values
  -h, --help      help for list
  -t, --time      Sort by modified time
  -u, --user      Sort by user
  -v, --version   Sort by version
```

```text
List services

Usage:
  chamber list-services <service> [flags]

Flags:
  -h, --help      help for list-services
  -s, --secrets   Include secret names in the list
```

```text
Read a specific secret from the parameter store

Usage:
  chamber read <service> <key> [flags]

Flags:
  -h, --help          help for read
  -q, --quiet         Only print the secret
  -v, --version int   The version number of the secret. Defaults to latest. (default -1)
```

```text
write a secret

Usage:
  chamber write <service> <key> [--] <value|-> [flags]

Flags:
  -h, --help                  help for write
  -s, --singleline            Insert single line parameter (end with \n)
      --skip-unchanged        Skip writing secret if value is unchanged
  -t, --tags stringToString   Add tags to the secret; new secrets only (default [])
```

```text
print version

Usage:
  chamber version [flags]

Flags:
  -h, --help   help for version
```

The tag leaf pages use these exact preambles:

```text
Read tags for a specific secret

Usage:
  chamber tag read <service> <key> [flags]

Flags:
  -h, --help   help for read
```

```text
Write tags for a specific secret

Usage:
  chamber tag write <service> <key> <tag>... [flags]

Flags:
      --delete-other-tags   Delete tags not specified in the command
  -h, --help                help for write
```

```text
Delete tags for a specific secret

Usage:
  chamber tag delete <service> <key> <tag key>... [flags]

Flags:
  -h, --help   help for delete
```

Append one blank line and the common suffix to each of those blocks. The leaf page ends immediately after the common suffix's `--verbose                    Print more information to STDERR\n` line: there is exactly one terminating newline and no trailing blank line or footer.

The exact descriptions, usages, and local flags are:

```text
delete  Delete a secret, including all versions
        chamber delete <service> <key> [flags]
        --exact-key   Prevent normalization of the provided key in order to delete any keys that match the exact provided casing.

env     Print the secrets from the parameter store in a format to export as environment variables
        chamber env <service> [flags]
        -p, --preserve-case    preserve variable name case
        -e, --escape-strings   escape special characters in values

exec    Executes a command with secrets loaded into the environment
        chamber exec <service...> -- <command> [<arg...>] [flags]
        --pristine              only use variables retrieved from the backend; do not inherit existing environment variables
        --strict                enable strict mode:
                                only inject secrets for which there is a corresponding env var with value
                                <strict-value>, and fail if there are any env vars with that value missing
                                from secrets
        --strict-value string   value to expect in --strict mode (default "chamberme")

export  Exports parameters in the specified format
        chamber export <service...> [flags]
        -f, --format string        Output format (json, yaml, java-properties, csv, tsv, dotenv, tfvars) (default "json")
        -o, --output-file string   Output file (default is standard output)

find    Find the given secret across all services
        chamber find <secret name> [flags]
        -v, --by-value   Find parameters by value

history View the history of a secret
        chamber history <service> <key> [flags]

help    Help provides help for any command in the application.
        Simply type chamber help [path to command] for full details.
        chamber help [command] [flags]

import  import secrets from json or yaml
        chamber import <service> <file|-> [flags]
        --normalize-keys chamber write   Normalize keys to match how chamber write would handle them. If not specified, keys will be written exactly how they are defined in the import source.

list    List the secrets set for a service
        chamber list <service> [flags]
        -e, --expand    Expand parameter list with values
        -t, --time      Sort by modified time
        -u, --user      Sort by user
        -v, --version   Sort by version

list-services  List services
               chamber list-services <service> [flags]
               -s, --secrets   Include secret names in the list

read    Read a specific secret from the parameter store
        chamber read <service> <key> [flags]
        -q, --quiet         Only print the secret
        -v, --version int   The version number of the secret. Defaults to latest. (default -1)

write   write a secret
        chamber write <service> <key> [--] <value|-> [flags]
        -s, --singleline            Insert single line parameter (end with \n)
            --skip-unchanged        Skip writing secret if value is unchanged
        -t, --tags stringToString   Add tags to the secret; new secrets only (default [])
```

The `exec` help additionally contains illustrative strict/pristine examples. The `tag` group description is lowercase `work with tags on secrets`, usage `chamber tag [command]`, and lists `delete`, `read`, and `write`. With no nested command, it prints this group help successfully. The nested descriptions are `Read tags for a specific secret`, `Write tags for a specific secret`, and `Delete tags for a specific secret`; usages are `chamber tag read <service> <key> [flags]`, `chamber tag write <service> <key> <tag>... [flags]`, and `chamber tag delete <service> <key> <tag key>... [flags]`. Only tag-write adds `--delete-other-tags   Delete tags not specified in the command`.

## Spec 5

Enforce positional cardinality before performing backend work, except for the `list-services` behavior noted below. `list`, `env`, and `find` require exactly one positional; `list-services` permits any number of positionals; `read`, `history`, `delete`, and tag-read require exactly two; `write` requires exactly three; `export` requires at least one; `import` requires exactly two; tag-write and tag-delete require at least three. For `list-services`, only the first positional is used as the optional prefix and later positionals are ignored: `list-services a b --backend=null` succeeds with `Service\n`, as do invocations with three or four positionals. `exec` has the rules in Spec 15. Too few/many errors use Cobra-style text, followed by the applicable usage and flag blocks, for example `Error: accepts 2 arg(s), received 1` or `Error: requires at least 3 arg(s), only received 1`. These are status 1 and stderr-only. Backend initialization still occurs for `list-services` with ignored trailing positionals: `list-services a b --backend bad` reports the invalid-backend diagnostic from Spec 6, with `BAD` as the uppercased value.

Integer options accept signed decimal integers. Invalid text produces Go-style parsing errors such as `Error: invalid argument "abc" for "-v, --version" flag: strconv.ParseInt: parsing "abc": invalid syntax`. Missing option values and unknown local flags are likewise parser errors, never crashes.

## Spec 6

Backend selection is case-insensitive. The accepted canonical values are `null`, `ssm`, `secretsmanager`, `s3`, and `s3-kms`; default is `ssm`. `--backend`/`-b` overrides `CHAMBER_SECRET_BACKEND`, even if the environment value is invalid. An invalid or empty selected backend on an operational command other than `export` fails as:

```text
Error: Failed to get secret store: invalid backend `UPPERCASED-VALUE`
```

where the supplied value is uppercased and the empty value appears as empty backticks. `export` uses the same uppercase rendering but omits the store-creation context. For example, `export test-service --backend invalid-backend` fails exactly with:

```text
Error: invalid backend `INVALID-BACKEND`
```

`--backend-s3-bucket` overrides `CHAMBER_S3_BUCKET`. S3 and S3-KMS operational commands require a nonempty bucket and otherwise fail with `Error: Failed to get secret store: Must set bucket for s3 backend`.

`--retries` overrides `CHAMBER_RETRIES` and defaults to 10. Any syntactically valid signed integer, including zero or negative values, is accepted. An invalid environment value fails with `Error: Failed to get secret store: Cannot parse $CHAMBER_RETRIES to an integer.`. `--retry-mode` defaults to `standard`; `standard` and `adaptive` are valid for SSM. Invalid retry mode fails SSM initialization with `Invalid retry mode VALUE` in the store-creation error. The null backend deliberately ignores retry-mode validity.

AWS region configuration is taken from the standard `AWS_REGION` environment variable. SSM uses `CHAMBER_AWS_SSM_ENDPOINT`, Secrets Manager uses `CHAMBER_AWS_SECRETS_MANAGER_ENDPOINT`, and the S3 variants use `AWS_ENDPOINT_URL`; the common endpoint may also be used by supplied Secrets Manager mocks. Dummy AWS credentials supplied by the harness are sufficient. Requests to local HTTP endpoints must not require real AWS access.

## Spec 7

The KMS alias defaults to `alias/parameter_store_key`; `--kms-key-alias` overrides `CHAMBER_KMS_KEY_ALIAS`. A nonempty alias without `alias/` is normalized by prepending that prefix. An explicitly supplied `--kms-key-alias` is rejected for SSM with `Unable to use --kms-key-alias with this backend. Use CHAMBER_KMS_KEY_ALIAS instead.` and for plain S3 with `Unable to use --kms-key-alias with this backend.`; those messages follow `Error: Failed to get secret store: `. The null backend accepts and ignores an explicit alias: `list svc --backend=null --kms-key-alias=x` succeeds with its ordinary empty header. S3-KMS accepts the option and environment value.

`--verbose` never contaminates structured stdout. It may add useful request/configuration diagnostics to stderr, but commands that normally have no diagnostics remain functionally identical.

## Spec 8

An ordinary service is one or more nonempty `/`-separated segments. Each segment contains only ASCII letters, ASCII digits, `_`, `-`, and `.`. Arbitrary mixtures, leading dots/underscores/digits, uppercase, hierarchical names, repeated permitted punctuation, and long names are accepted. Empty strings, leading/trailing `/`, `//`, whitespace, non-ASCII characters, backslashes, and any other punctuation are rejected. The error is:

```text
Error: Failed to validate service: Failed to validate service name 'RAW'. Only alphanumeric, dashes, forward slashes, full stops and underscores are allowed for service names. Service names must not start or end with a forward slash
```

`list` and each service operand of `exec` use a distinct label-capable validator, with an observable hierarchical-name restriction: a colon suffix is accepted only when the base contains at least one `/`. Thus `top/app:QA_1` and `app/dev:blue` are accepted, while the otherwise well-formed simple-base names `app:dev` and `a:.x-y` are rejected. After a hierarchical base, each colon-delimited label component must be nonempty and contain only letters, digits, `_`, `-`, and `.`; multiple such components are accepted (`a/b:x:y` succeeds). A slash in the suffix, an empty component, or invalid characters fail with the analogous message that says `..., and colon followed by a label name.` and says the name must not start or end with `a forward slash or colon`. Other commands use ordinary-service validation and reject a colon. In the evaluated null/empty cases, an accepted label does not change `list` output or prevent `exec` from launching its child.

The optional argument to `list-services` is treated as an unvalidated prefix rather than an ordinary service operand. It accepts the empty string, leading or trailing slash, doubled slash, spaces, Unicode, backslashes, `!`, and colon spellings; against the null backend each of those invocations succeeds with `Service\n`.

The exact service `_chamber` is accepted but first emits this stderr warning, even if the later backend operation fails:

```text
Service name _chamber is reserved for chamber's own use and will be prohibited in a future version. Please switch to a different service name.
```

## Spec 9

A key is a nonempty sequence of ASCII letters, digits, `_`, `-`, and `.`. It may begin with a dot, underscore, digit, or dash and may be long. It may not contain `/`, whitespace, non-ASCII text, or other punctuation. Invalid keys fail with:

```text
Error: Failed to validate key: Failed to validate key name 'RAW'. Only alphanumeric, dashes, full stops and underscores are allowed for key names
```

Normal `write`, `read`, and `delete` storage keys are normalized by converting ASCII letters to lowercase. Hyphens are preserved, as are underscores, dots, and digits. Thus `Upper-Case.Key` becomes `upper-case.key`; reading `upper-case.key` finds that write, while `upper_case.key` is a distinct key. `delete --exact-key` validates but uses the original spelling/case instead. Imported keys follow Spec 17.

When a key becomes an environment variable name, replace every character other than ASCII letters, digits, and `_` with `_`; make it uppercase unless preserve-case was requested. This same mapping is used for `env`, `exec`, strict matching, and dotenv export.

## Spec 10

The logical store holds independent secrets keyed by `(service, lowercased key)`, with punctuation including hyphens preserved. Values are opaque UTF-8 strings and may be empty, very long, contain spaces, tabs, quotes, dollar signs, backslashes, Unicode, or embedded newlines. A first successful write creates version 1; each changed update increments by one and retains earlier versions. `--skip-unchanged` compares the complete current value byte-for-byte and suppresses a new version when equal. Deleting a secret removes all its versions; recreating it starts at version 1.

Each version records a modification time and user. Human tables format time as local `YYYY-MM-DD HH:MM:SS`. When an AWS backend can obtain caller identity, user is the complete ARN returned by STS `GetCallerIdentity`; it must not be shortened. First history event is `Created`, later events are `Updated`.

`write SERVICE KEY VALUE` emits nothing on success. A value that is a single argv item is preserved exactly, including embedded newlines. If VALUE is `-`, read stdin to EOF. With `--singleline`/`-s`, read only through the first newline but discard that terminating newline from the stored value. Thus stdin `first\nignored\n` stores `first`, and a quiet read emits only `first\n` (the read command's own terminating newline). If EOF occurs before a newline, discard the partial input and fail with `Error: EOF`. `--tags` is a repeatable/comma-capable `key=value` map passed with creation as described in Spec 18.

## Spec 11

`read SERVICE KEY` reads the latest version by default. `--version N` reads that version; default `-1` denotes latest, while any other parsed integer is sent through as a version request and an unavailable version fails cleanly. `--quiet`/`-q` prints exactly the value followed by one newline, with no header or metadata; it combines with `--version`. Ordinary output is a tabwriter-aligned table with logical columns `Key`, `Value`, `Version`, `LastModified`, `User` and one row. Tab separation/alignment must match Go `text/tabwriter` style; the header begins exactly `Key\tValue\tVersion\t\tLastModified\t\tUser\n` for the usual widths, with one tab between `Key` and `Value`.

A missing secret/version fails with `Error: Failed to read: secret not found`. `delete SERVICE KEY` deletes every version and emits nothing on success. A missing target fails with `Error: secret not found`. Backend details may add a command context, but errors are always stderr-only and nonzero.

## Spec 12

`list SERVICE` prints one row per current secret that the selected backend returns as a valid Chamber key. The SSM exception for punctuation-bearing keys created by unnormalized import is specified in Specs 17 and 20. The logical columns are `Key`, `Version`, `LastModified`, `User`; `--expand`/`-e` adds `Value`. Default ordering is ascending key, and `--time`/`-t` orders populated results by ascending modification time. `--user`/`-u` and `--version`/`-v` are recognized sorting options, and any combination of the three sorting flags is accepted. Empty output is still a header. The exact non-expanded empty header is `Key\tVersion\t\tLastModified\tUser\n`; expanded output includes `\tValue` at the end of its header. Keys are displayed in their stored spelling: ordinary writes have already normalized them, while an unnormalized imported key such as `Mixed-Key` retains that exact spelling.

`history SERVICE KEY` prints all retained versions in ascending version/chronological order, using logical columns `Event`, `Version`, `Date`, `User`. Its empty-store header is exactly `Event\tVersion\t\tDate\tUser\n`; populated tabwriter output may contain extra tabs needed for aligned columns. Version 1 is `Created`; later versions are `Updated`. A missing secret fails with `Error: Failed to get history: secret not found`.

## Spec 13

`list-services [PREFIX]` prints `Service\n` followed by distinct service names in lexical order. No prefix means all services. A prefix restricts results to that service hierarchy while returned hierarchical names remain complete, for example `app/dev`, `app/prod`, and `db`. `--secrets` must be recognized as described in help. On an empty store it does not alter the output. An empty store prints only `Service\n`.

`find TERM` searches all services by exact secret-key equality and prints logical column `Service` plus one sorted, deduplicated service per match. Its empty output is `Service\n`. `find --by-value TERM` instead uses exact value equality and prints logical columns `Service`, `Key`; its empty header is exactly `Service\t\tKey\n`. Search terms are literal opaque strings: including empty text, whitespace, newlines, Unicode, shell metacharacters, JSON-looking text, or path-like text does not invoke name validation or substring/regex interpretation.

## Spec 14

`export SERVICE...` loads current raw key/value pairs from every named service and merges them in command-line order; a later service wins a duplicate key. Every overridden duplicate also emits `warning: parameter KEY specified more than once (overridden by service SERVICE)\n` on stderr, while the merged export remains successful. For example, if `shared` from `app/prod` overrides an earlier value, the line is exactly `warning: parameter shared specified more than once (overridden by service app/prod)\n`. Format matching is case-insensitive. Supported names are `json`, `yaml`, `csv`, `tsv`, `dotenv`, `tfvars`, `java-properties`, and alias `properties`. Anything else fails with `Error: Unable to export parameters: Unsupported export format: VALUE`; for example, the `xml` diagnostic is exactly `Error: Unable to export parameters: Unsupported export format: xml\n`.

Use deterministic lexical key ordering where the format has rows. JSON is one valid flat JSON object mapping string keys to string values; YAML is a valid flat YAML mapping. CSV and TSV contain no header and each record is key then value using proper CSV quoting and comma/tab delimiter; for example a CSV value containing commas is enclosed in double quotes. Dotenv uses sanitized uppercase environment keys and double-quoted, escaped values. Tfvars uses `key = "escaped value"` and sanitizes a dot in a key to `_`, so stored `complex.key` is emitted as `complex_key`. Java-properties and its `properties` alias preserve that dot and use `key = value`, with one ASCII space on both sides of `=`. In their values, an embedded newline is written as `\n`, a backslash as `\\`, and non-ASCII `雪` as `\u96ea`; a double quote remains unescaped. Values containing quotes, slashes, control characters, Unicode, and newlines must produce syntactically valid output without losing their content.

For no secrets, JSON and YAML represent an empty mapping (`{}`, optionally followed by a newline), while every row-based format is zero bytes. `--output-file PATH` creates or truncates PATH, writes the entire formatted result there, and leaves stdout empty. It does not create missing parent directories. On this Linux executable the complete missing-parent diagnostic is `Error: Failed to open output file for writing: open PATH: no such file or directory\n`, with lowercase `no`.

## Spec 15

`env SERVICE` emits current values as one line per lexically sorted key:

```text
export ENV_NAME=value
```

There is no header and an empty service emits zero bytes. Default names use the uppercase mapping from Spec 9; `--preserve-case`/`-p` preserves letter case while still replacing invalid name characters. By default ordinary simple values are emitted literally after `=`. `--escape-strings`/`-e` wraps each value in double quotes and uses backslash escapes. Quotes and backslashes survive evaluation by a POSIX shell, but an embedded newline does not round-trip through that shell: it is emitted as the two characters `\n`, which remain backslash-plus-`n` after evaluation rather than becoming a newline. For example, the observed complex value begins `export COMPLEX_KEY="line1\n\"quoted\"`. The two flags combine. No diagnostic text may appear on stdout.

`exec SERVICE... -- COMMAND [ARG...]` requires a literal separator. This check occurs after ordinary flag parsing. If the would-be command contains a flag-looking token before any separator, its parser error can therefore win: `exec svc /usr/bin/python3 -c pass --backend=null` fails with `Error: unknown shorthand flag: 'c' in -c\n`. Otherwise, each of the following failures returns status 1, has empty stdout, and writes the stated first line followed immediately by the exec command's `Usage:`, `Examples:`, `Flags:`, and `Global Flags:` blocks to stderr:

```text
Error: please separate services and command with '--'. See usage
Error: at least one service must be specified: requires at least 1 arg(s), only received 0
Error: must specify command to run. See usage: requires at least 1 arg(s), only received 0
```

The first line applies respectively when the separator is absent, no service precedes it, or no command follows it.

After validation and loading, execute COMMAND directly, without joining or shell-interpreting its arguments. Preserve argument boundaries, spaces, quotes, empty arguments, and Unicode. Connect the child's stdin/stdout/stderr to the caller. Resolve a relative command through the parent's PATH, and report normal OS exec errors such as `Error: exec: "NAME": executable file not found in $PATH` or `Error: exec: "/path": stat /path: no such file or directory`. Return the child's exact exit status, including non-1 statuses such as 2, 5, or 42.

## Spec 16

Normal `exec` starts with the inherited environment and overlays loaded secrets using the environment-name mapping. Secret values win over inherited variables. Services are loaded left-to-right; later services win collisions, and a collision produces a warning on stderr identifying the overwritten variable without changing success. A null store therefore behaves as a transparent execution wrapper.

`--pristine` gives the child only loaded secret variables (apart from unavoidable variables an operating system or invoked shell itself synthesizes). In particular it removes inherited PATH, HOME, and arbitrary user variables from the child, but command lookup still uses the parent's PATH before constructing the pristine child environment.

`--strict` compares loaded secret names with the inherited environment using `--strict-value` (default `chamberme`). A secret is injected only when its normalized environment name already exists in the parent and has exactly the sentinel value. If the matching parent variable exists with another value, fail using this exact template:

```text
Error: parent env has NAME, but was expecting value `SENTINEL`, not `ACTUAL`
```

Every normalized parent variable whose value is the sentinel must be supplied by some loaded secret; otherwise fail before launching the child with exactly:

```text
Error: parent env was expecting NAME=SENTINEL, but was not in store
```

Check all parent variables, not only the first.

A sentinel-bearing parent name must already be in normalized uppercase/underscore form. Otherwise fail using this exact template:

```text
Error: parent env has key `RAW` with expected value `SENTINEL`, but key is not normalized like `NORMALIZED`, so would never get substituted
```

All these errors end in one newline. Non-sentinel inherited variables remain unchanged in non-pristine mode. Strict checking occurs before pristine filtering, so `--strict --pristine` uses parent sentinel variables as a request set and then passes only resolved secret values. If there are no sentinel variables and no conflicting store/environment pair, strict mode succeeds.

## Spec 17

`import SERVICE FILE` reads FILE, or stdin when FILE is `-`, and auto-decodes a JSON or YAML document. The document must be one flat mapping with string keys and scalar values. Empty mappings succeed. String values are preserved; non-string scalars are coerced to strings instead of producing decode errors: numbers use their textual form, booleans become `true` or `false`, and null becomes the empty string. For example, importing `{"key": 3}` into a writable backend stores `3` and prints `Successfully imported 1 secrets\n`. Top-level arrays/scalars, nested objects/lists, and malformed syntax fail as decode errors; diagnostics begin `Error: Failed to decode input as json:` and include useful parse position/context even for YAML input. On this Linux executable an unreadable relative path such as `nonexistent.json` fails exactly with `Error: Failed to open file: open nonexistent.json: no such file or directory\n`.

Decode diagnostics use these exact multiline forms for the representative malformed inputs shown (including spacing, caret position, blank lines, and final newline):

```text
input:
{
  "key1": "value1",
  "key2": "value2"
  invalid json here
}

stderr:
Error: Failed to decode input as json: [4:3] ',' or '}' must be specified
   1 | {
   2 |   "key1": "value1",
   3 |   "key2": "value2"
>  4 |   invalid json here
         ^
   5 | }
```

```text
input:
key1: value1
key2: [value2, value3
key3: value4

stderr:
Error: Failed to decode input as json: [3:1] ',' or ']' must be specified
   1 | key1: value1
   2 | key2: [value2, value3
>  3 | key3: value4
       ^

```

For a JSON mapping whose `database` value begins with a nested object on line 2, the error is `Error: Failed to decode input as json: [2:15] cannot unmarshal map[string]interface {} into Go value of type string`, followed by a numbered source excerpt with the caret under the object. For a YAML top-level sequence beginning `- key1: value1`, it is `Error: Failed to decode input as json: [1:1] sequence was used where mapping is expected`, followed by the numbered excerpt and caret. The executable must reproduce this decoder-style source context rather than emitting a traceback.

Import does not apply Spec 9's key validator. Without `--normalize-keys`, source key spelling is stored exactly, including punctuation that an ordinary command would reject: importing `{"bad!":"value"}` succeeds on a writable backend and uses `bad!` as the storage key. With the flag, apply the same ASCII lowercasing as `write`, still preserving hyphens. On SSM, successful storage does not make an invalid key visible to `list`: an unnormalized import containing `"bad!":"ok"` sends `PutParameter` for `/svc/bad!` and counts it in `Successfully imported 5 secrets\n`, but a following `list svc -e` omits both the `bad!` row and its `ok` value. Import entries sequentially through the selected backend. A backend failure stops and begins `Error: Failed to write secret:`. Complete success prints exactly `Successfully imported N secrets\n`, including `Successfully imported 0 secrets\n`.

## Spec 18

A standalone tag argument is `KEY=VALUE`, split at its first `=` so VALUE may itself contain `=`. A tag key is 1–128 characters and a tag value is 1–256 characters. Both accept ASCII letters/digits, spaces, and `+ - = . _ : / @`; other characters such as `!` are invalid. Missing `=` fails as `Error: Failed to parse tag RAW: tag must be in the form key=value`. Invalid tag-write keys use `Error: Failed to validate tag with key KEY: Failed to validate tag key 'KEY'. Only 128 alphanumeric, space, and characters +-=._:/@ are allowed for tag keys`; invalid values use the same outer prefix and `Failed to validate tag value 'VALUE'. Only 256 alphanumeric, space, and characters +-=._:/@ are allowed for tag values`. Tag-delete validates each supplied tag key and uses the outer prefix `Error: Failed to validate tag key KEY:`. Empty key/value strings follow these invalid templates.

The `write --tags` flag uses the CLI string-to-string map parser rather than the standalone validation path. It accepts comma-separated pairs, repeat occurrences, values containing additional `=`, and even an empty key or value; these parsed maps reach the backend. An item with no `=` fails before backend creation with text in the form `Error: invalid argument "ITEM" for "-t, --tags" flag: ITEM must be formatted as key=value`. An entirely empty argument has the same form with an empty detail prefix.

`tag read SERVICE KEY` prints all returned tags as an aligned table with logical columns `Key`, `Value`; row order is not significant. `tag write SERVICE KEY TAG...` adds new tags and overwrites values of matching tag keys while preserving unspecified tags in the backend, but its success table contains only the tags supplied by that invocation, not the complete resulting tag set. For example, writing `owner=security new=a=b` while `stage=dev` exists prints rows for `owner` and `new`; a subsequent `tag read` also prints the preserved `stage`. With `--delete-other-tags`, the resulting tag set contains exactly the supplied tags. `tag delete SERVICE KEY TAG_KEY...` removes those keys and preserves the rest; deleting a tag key that is not present succeeds. The tag subcommands do not support `--quiet`; supplying it is an unknown-flag error.

## Spec 19

The `null` backend is an offline no-op reader, not an in-memory persistent store. `list`, `list-services`, `history`, `find`, `export`, and `env` succeed with the empty representations specified above. `exec` still launches the child using inherited/pristine/strict rules.

Unsupported mutations and point reads fail exactly by operation: write is `Error: Write is not implemented for Null Store`; write with a nonempty tag map is `Error: WriteWithTags is not implemented for Null Store`; read is `Error: Failed to read: Not implemented for Null Store`; delete is `Error: Not implemented for Null Store`. Tag operations are respectively prefixed `Error: Failed to read tags:`, `Error: Failed to write tags:`, or `Error: Failed to delete tags:`, followed by `Not implemented for Null Store`.

## Spec 20

The SSM backend interoperates with an AWS Systems Manager Parameter Store-compatible JSON HTTP endpoint. Store a secret at parameter name `/<service>/<normalized-key>` using `PutParameter` with `Type: SecureString`, `Overwrite: true`, and the configured KMS key id. Every `PutParameter` also sends `Description` as the decimal Chamber logical version string: the first write sends `"1"`, the next changed write sends `"2"`, and so on. The endpoint must preserve and return that `Description` in its parameter metadata/history responses; Chamber uses it rather than the native SSM version as its logical version. Without this round trip, the reference renders version 0, treats all history events as `Updated`, and cannot find requested Chamber version 1. With it, 25 writes render one `Created` and 24 `Updated` events.

Read specific names with `GetParameters`. Metadata enumeration for `list SERVICE` uses paginated `DescribeParameters` requests whose `ParameterFilters` contains `{"Key":"Path","Option":"OneLevel","Values":["/<service>"]}`; the filter value has no trailing slash. Chamber filters those metadata results through its valid-key rules before fetching values with `GetParameters`, which is why an SSM parameter such as `/svc/bad!` created by unnormalized import is not listed or included in that subsequent fetch.

Commands that load all raw values of a service—`env`, `exec`, and `export`—instead use paginated `GetParametersByPath`. The initial request is exactly `{"Path":"/<service>/","WithDecryption":true}`: unlike the `DescribeParameters` filter, `Path` has a trailing slash, and the request omits `Recursive` and `MaxResults`. A multi-service command issues one such request per service in command-line order.

Obtain all versions with `GetParameterHistory` and delete with `DeleteParameter`. Discover services for `list-services [PREFIX]` with `DescribeParameters`, `MaxResults: 50`, and a `Name`/`BeginsWith` filter. With no prefix its value is `/`; with prefix `app` the filter is exactly `{"Key":"Name","Option":"BeginsWith","Values":["/app"]}`. Follow every returned `NextToken` until absent; lists and history must work beyond a single page (at least 15 secrets and 25 versions).

AWS JSON operations are POST requests whose `X-Amz-Target` ends with the operation name. Request/response fields use the standard names just listed, including `Parameters`, `Parameter`, `Name`, `Value`, `Version`, `Description`, `LastModifiedDate`, `NextToken`, and parameter metadata. Returned parameter records must echo the stored `Description` wherever that operation supplies parameter metadata or history. `WithDecryption` must be true when reading values. It is acceptable for local mock requests to carry ordinary AWS-signing headers; mocks do not require real credentials.

SSM writes obtain the caller ARN from STS `GetCallerIdentity` for metadata. For a new secret written with `--tags`, `PutParameter` contains no `Tags` field. After it succeeds, send the parsed tags in a separate `AddTagsToResource` request with resource type `Parameter` and the full parameter name. Standalone tag operations use `ListTagsForResource`, `AddTagsToResource`, and `RemoveTagsFromResource` with the same resource type/name shape. `--delete-other-tags` first determines/removes omitted keys and then leaves exactly the requested map. Reading tags for a nonexistent secret fails with `Error: Failed to read tags: secret not found`; write/delete against a nonexistent resource surface the corresponding SSM `InvalidResourceId` error. Surface other remote errors with the command's contextual prefix and nonzero status.

## Spec 21

The Secrets Manager backend represents one chamber service as one AWS secret named exactly by that service. `SecretString` is a JSON object containing all current chamber keys plus `_chamber_metadata`, whose value is serialized JSON used to preserve independent per-key versions, timestamps, users, and history. `list` filters out this member. These paths expose it: `read SERVICE _chamber_metadata -q` returns its serialized value, `env` emits it as `_CHAMBER_METADATA`, JSON `export` includes the `_chamber_metadata` member, and `exec` injects `_CHAMBER_METADATA`. Create a missing service with `CreateSecret`; read with `GetSecretValue`; update atomically with `PutSecretValue`; inspect AWS versions with `ListSecretVersionIds` and requested `VersionId` reads.

Every write to an already existing service—including an empty-value write that deletes a key—first sends `GetSecretValue`, then sends `DescribeSecret` with exactly `{"SecretId":"SERVICE"}`, and only then sends `PutSecretValue`. The endpoint must implement that probe and return a successful JSON response; an empty object `{}` is sufficient. A newly created service does not receive this probe before `CreateSecret`. The executable issues only one `ListSecretVersionIds` request and does not follow a returned `NextToken`. Consequently, against an endpoint whose first page contains four snapshots, chamber version 1 remains readable after six writes but version 6 fails with `Error: Failed to read: secret not found\n`.

Updating one key must preserve other keys. Each key has its own chamber version sequence even though AWS versions contain service snapshots. Reading an older chamber key version searches the snapshots; when deletion and recreation leave two snapshots with chamber version 1, lookup selects the pre-deletion value. Writing an empty value deletes that key; attempting an empty write for a nonexistent key fails. Recreating a removed key resets its current metadata to version 1, and current history reports that recreation as `Created` version 1, but it does not make the old version-1 snapshot inaccessible: after writing `present`, deleting it, and recreating it as `reborn`, a latest quiet read returns `reborn\n` while `read ... -q -v 1` returns the older `present\n`. Caller/user metadata is the full STS ARN.

A service that does not exist surfaces the endpoint's resource-not-found error rather than an empty list. Both a point read and `list` retain the literal AWS error-code token `ResourceNotFoundException` in stderr; the respective contextual prefixes are `Error: Failed to read:` and `Error: Failed to list store contents:`. `list-services` fails exactly with `Error: Failed to list store contents: Secrets Manager Backend is experimental and does not implement this command`. Standalone tag operations fail exactly as follows:

```text
Error: Failed to read tags: Not implemented for Secrets Manager Store
Error: Failed to write tags: Not implemented for Secrets Manager Store
Error: Failed to delete tags: Not implemented for Secrets Manager Store
```

Each invocation emits only its applicable line. A normal `write` with a nonempty `--tags` map also fails nonzero with a not-implemented tag error; it must not silently modify data.

## Spec 22

The plain S3 backend interoperates with a path-style S3-compatible endpoint and the configured bucket. Within the bucket, each service owns `<service>/__latest.json` plus one `<service>/<lowercased-key>.json` object per current secret; lowercasing preserves hyphens, so writing `Upper-Key` creates `<service>/upper-key.json`, not `<service>/upper_key.json`. The secret object contains the retained version records and metadata; the index records current entries used by list/raw-list/export. A write reads existing state, appends the next version, writes the secret object, and updates the index. A normal delete removes the object and its index entry. A missing index means an empty service. If an index references an absent secret object, `list` fails with an error line `Error: Failed to list store contents: secret not found\n`. Malformed secret JSON or malformed index JSON is likewise an error, not a crash or fabricated result.

Use ordinary HEAD/GET/PUT/DELETE bucket/object requests and URL-encode object paths correctly. Support full CRUD, current reads, requested versions, list, raw list, export/env/exec, and ascending history across repeated writes. `list-services` fails exactly with `Error: Failed to list store contents: S3 Backend is experimental and does not implement this command`. Standalone tag read/write/delete are unsupported; their errors contain `Failed to ... tags: Not implemented for S3 Store`.

Server 4xx responses and unreachable endpoints return prompt, clean contextual errors and are not interpreted as empty data. A GET of an S3 object that receives HTTP 500 with S3 error code `InternalError` behaves differently: the reference repeatedly sends the identical GET despite `AWS_MAX_ATTEMPTS=1`, emits no stdout or stderr while doing so, and does not return within at least five seconds. This retrying response is not interpreted as empty data.

## Spec 23

S3-KMS has the same observable secret, version, export, exec, and error semantics as S3, but separates indexes by KMS alias. For alias `alias/test-key`, the service index object is `<service>/__kms_alias_test-key__latest.json`: prefix `__kms_`, replace `/` with `_`, then suffix `__latest.json`. It must never read or update the plain `__latest.json` or another alias's index.

Every PUT of both a secret and its KMS-specific index includes headers `x-amz-server-side-encryption: aws:kms` and `x-amz-server-side-encryption-aws-kms-key-id: alias/...`. Reads retain the key-id association. Before updating or deleting, the executable discovers existing KMS index objects through S3 object listing. If that discovery exposes the same secret under a different alias, the diagnostic error line is exactly `Error: Unable to overwrite secret KEY using new KMS key NEW; mismatch with existing key OLD\n`; an SDK warning described in Spec 25 can precede it. `KEY` uses the raw CLI spelling with hyphens preserved, not an underscore-normalized spelling. Delete uses the same error wording and leaves the secret intact. For example, the observed write error names `shared-key`, and the delete error names `protected-key`.

This mismatch protection is conditional on object discovery. If a compatible endpoint returns an empty object listing despite retaining the old alias's objects, the executable treats the new alias index as absent: an overwrite under the new alias succeeds, and a following delete under that alias also succeeds. A normal same-key deletion makes a subsequent point read fail. `list-services` reports `Error: Failed to list store contents: S3KMS Backend is experimental and does not implement this command`; tag operations are unsupported as for S3.

## Spec 24

`completion --help` has description:

```text
Generate the autocompletion script for chamber for the specified shell.
See each sub-command's help for details on how to use the generated script.
```

Its usage is `chamber completion [command]`; it lists `bash`, `fish`, `powershell`, and `zsh` with descriptions `Generate the autocompletion script for SHELL`. Each valid shell prints a nonempty, syntactically appropriate Cobra-style completion script; `completion SHELL --help` succeeds and mentions that shell. With no shell, or with an unrecognized shell token, print the completion-group help to stdout and return status 0 rather than emitting an unknown-command error.

More precisely, the completion-group help begins with this exact block:

```text
Generate the autocompletion script for chamber for the specified shell.
See each sub-command's help for details on how to use the generated script.

Usage:
  chamber completion [command]

Available Commands:
  bash        Generate the autocompletion script for bash
  fish        Generate the autocompletion script for fish
  powershell  Generate the autocompletion script for powershell
  zsh         Generate the autocompletion script for zsh

Flags:
  -h, --help   help for completion
```

Append one blank line, the exact common `Global Flags:` block from Spec 4, another blank line, `Use "chamber completion [command] --help" for more information about a command.`, and a final newline.

The first 30 bash lines are exactly:

```bash
# bash completion V2 for chamber                              -*- shell-script -*-

__chamber_debug()
{
    if [[ -n ${BASH_COMP_DEBUG_FILE-} ]]; then
        echo "$*" >> "${BASH_COMP_DEBUG_FILE}"
    fi
}

# Macs have bash3 for which the bash-completion package doesn't include
# _init_completion. This is a minimal version of that function.
__chamber_init_completion()
{
    COMPREPLY=()
    _get_comp_words_by_ref "$@" cur prev words cword
}

# This function calls the chamber program to obtain the completion
# results and the directive.  It fills the 'out' and 'directive' vars.
__chamber_get_completion_results() {
    local requestComp lastParam lastChar args

    # Prepare the command to request completions for the program.
    # Calling ${words[0]} instead of directly chamber allows handling aliases
    args=("${words[@]:1}")
    requestComp="${words[0]} __complete ${args[*]}"

    lastParam=${words[$((${#words[@]}-1))]}
    lastChar=${lastParam:$((${#lastParam}-1)):1}
    __chamber_debug "lastParam ${lastParam}, lastChar ${lastChar}"
```

It is a balanced-brace, functional script with exactly 338 lines, and its final five lines are exactly:

```bash
else
    complete -o default -o nospace -F __start_chamber chamber
fi

# ex: ts=4 sw=4 et filetype=sh
```

The first 20 zsh lines are exactly:

```zsh
#compdef chamber
compdef _chamber chamber

# zsh completion for chamber                              -*- shell-script -*-

__chamber_debug()
{
    local file="$BASH_COMP_DEBUG_FILE"
    if [[ -n ${file} ]]; then
        echo "$*" >> "${file}"
    fi
}

_chamber()
{
    local shellCompDirectiveError=1
    local shellCompDirectiveNoSpace=2
    local shellCompDirectiveNoFileComp=4
    local shellCompDirectiveFilterFileExt=8
    local shellCompDirectiveFilterDirs=16
```

The complete zsh script has exactly 212 lines and contains the literal lowercase substring `read`.

The first 20 fish lines are exactly:

```fish
# fish completion for chamber                              -*- shell-script -*-

function __chamber_debug
    set -l file "$BASH_COMP_DEBUG_FILE"
    if test -n "$file"
        echo "$argv" >> $file
    end
end

function __chamber_perform_completion
    __chamber_debug "Starting __chamber_perform_completion"

    # Extract all args except the last one
    set -l args (commandline -opc)
    # Extract the last arg and escape it in case it is a space
    set -l lastArg (string escape -- (commandline -ct))

    __chamber_debug "args: $args"
    __chamber_debug "last arg: $lastArg"

```

The complete fish script has exactly 235 lines, defines other `__chamber...` helpers, and contains exactly these four non-comment registration lines:

```fish
complete -c chamber -e
complete -c chamber -n '__chamber_clear_perform_completion_once_result'
complete -c chamber -n 'not __chamber_requires_order_preservation && __chamber_prepare_completions' -f -a '$__chamber_comp_results'
complete -k -c chamber -n '__chamber_requires_order_preservation && __chamber_prepare_completions' -f -a '$__chamber_comp_results'
```

The fish leaf additionally accepts `--no-descriptions`. Its help lists `--no-descriptions   disable completion descriptions`. `completion fish --no-descriptions` succeeds with no stderr and emits the no-description fish script: it has 235 lines, begins with the same fish header above, and requests dynamic completion through `__completeNoDesc`.

The first 20 PowerShell lines are exactly:

```powershell
# powershell completion for chamber                              -*- shell-script -*-

function __chamber_debug {
    if ($env:BASH_COMP_DEBUG_FILE) {
        "$args" | Out-File -Append -FilePath "$env:BASH_COMP_DEBUG_FILE"
    }
}

filter __chamber_escapeStringWithSpecialChars {
    $_ -replace '\s|#|@|\$|;|,|''|\{|\}|\(|\)|"|`|\||<|>|&','`$&'
}

[scriptblock]${__chamberCompleterBlock} = {
    param(
            $WordToComplete,
            $CommandAst,
            $CursorPosition
        )

    # Get the current command line and convert into a string
```

It is longer than 50 lines and contains exactly one registration line: `Register-ArgumentCompleter -CommandName 'chamber' -ScriptBlock ${__chamberCompleterBlock}`.

## Spec 25

All backend and serialization operations must be deterministic and robust against empty data, long values/names, malformed remote JSON/XML, missing fields, partial backend state, network refusal, and HTTP error responses, subject to the explicitly non-paginating Secrets Manager version lookup in Spec 21 and the S3 HTTP 500 retry behavior in Spec 22. Never print secrets in diagnostics. Perform validation and required configuration checks before network access where applicable. Help, version, and CLI syntax failures do not contact a backend.

Contextual error prefixes are part of the interface: store creation uses `Error: Failed to get secret store:` except for the `export` case in Spec 6, read uses `Error: Failed to read:`, history uses `Error: Failed to get history:`, import writes use `Error: Failed to write secret:`, tag operations use `Error: Failed to read/write/delete tags:`, and list-services backend failures use `Error: Failed to list store contents:`. Do not put partial structured results on stdout after a failure.

Reserved-service warnings, export duplicate-key warnings from Spec 14, and exec collision warnings are expected successful stderr output. In addition, GET-dependent S3 and S3-KMS operations against a compatible endpoint response with no supported checksum emit one SDK warning line for each such response, even without `--verbose`, in this form:

```text
SDK YYYY/MM/DD HH:MM:SS WARN Response has no supported checksum. Not validating response payload.
```

The timestamp is the invocation time. A successful quiet read still writes its value to stdout while this warning goes to stderr.
