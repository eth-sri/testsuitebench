# Clarified behavioral specification

The required artifact is a single executable file named `executable`. It is a non-interactive, direnv-compatible command-line program. All paths below are POSIX paths, all text is UTF-8, and all examples use the process environment and current working directory of the invocation.

## Spec 1

The executable must behave as a conventional, short-lived CLI, never as a full-screen or cursor-addressing TUI. It must work when stdin/stdout are pipes and when no terminal is allocated.

Commands write their data result to stdout and diagnostics to stderr. Successful commands normally return 0. Usage, validation, configuration, filesystem, decoding, network, and authorization errors return 1 unless a later section explicitly says that a command emits shell code representing an error while the executable itself returns 0. A normal diagnostic is prefixed `direnv: `; fatal diagnostics have the exact outer form `\x1b[31mdirenv: error MESSAGE\x1b[0m\n`. Commands must not emit tracebacks, panic text, or prompts.

Command names, flags, and shell names are case-sensitive. `-h` is not a help flag: it is an unknown command and fails. An unknown command fails and reports `command "ARGV0 COMMAND" not found`, where `ARGV0` is the executable spelling used by the caller and `COMMAND` is the first unknown subcommand; later arguments are omitted. For example, invoking `./executable fake_command arg1 arg2` reports `command "./executable fake_command" not found`. The message contains both `error` and `not found`. The empty invocation, `help`, and `--help` succeed and print help. If the first argument is `--help`, later arguments are ignored.

## Spec 2

The public command set is exactly the following behavioral surface (aliases are not separate help entries): `allow`, `block`, `edit`, `exec`, `export`, `fetchurl`, `help`, `hook`, `prune`, `reload`, `status`, `stdlib`, `version`, and `log`. `permit` and `grant` dispatch exactly like `allow`. `deny`, `disallow`, and `revoke` dispatch exactly like `block`.

The help output goes only to stdout, ends in a newline, and begins exactly:

```text
direnv v2.37.1
Usage: direnv COMMAND [...ARGS]

Available commands
------------------
```

It then documents these signatures and descriptions (the order of names inside the supported-shell bracket may vary):

```text
allow [PATH_TO_RC]:
  aliases: permit, grant
  Grants direnv permission to load the given .envrc or .env file.
block [PATH_TO_RC]:
  aliases: deny, disallow, revoke
  Revokes the authorization of a given .envrc or .env file.
edit [PATH_TO_RC]:
  Opens PATH_TO_RC or the current .envrc or .env into an $EDITOR and allow
  the file to be loaded afterwards.
exec DIR COMMAND [...ARGS]:
  Executes a command after loading the first .envrc or .env found in DIR
export SHELL:
  Loads an .envrc or .env and prints the diff in terms of exports.
  Supported SHELL values are: [bash, elvish, fish, gha, gzenv, json, murex, pwsh, systemd, tcsh, vim, zsh]
fetchurl <url> [<integrity-hash>]:
  Fetches a given URL into direnv's CAS
help [SHOW_PRIVATE]:
  Shows this help
hook SHELL:
  Used to setup the shell hook
prune:
  Removes old allowed and required files
reload:
  Triggers an env reload
status [--json]:
  Prints some debug status information
stdlib:
  Displays the stdlib available in the .envrc execution context
version [VERSION_AT_LEAST]:
  prints the version or checks that direnv is older than VERSION_AT_LEAST.
log [--status | --error] <message>:
  Logs a given message
```

`help` with any nonempty extra argument (including `true` or `SHOW_PRIVATE`) adds a `* = private commands` legend and at least these private entries: `apply_dump FILE`, `check-required SHELL ENVRC_PATH PATH...`, `current PATH`, `dotenv [SHELL] [PATH_TO_DOTENV]`, `dump [SHELL] [FILE]`, `show_dump DUMP`, `watch SHELL PATH...`, `watch-dir SHELL DIR`, `watch-list [SHELL]`, and `watch-print [--null]`. Every private-command signature starts with `*` immediately followed by the command, has no space after the star, and ends with a colon; for example, `*apply_dump FILE:`. Help with an unknown argument still succeeds and shows general help.

## Spec 3

`version` and `--version` with no comparison argument print exactly `2.37.1\n` to stdout and nothing to stderr. `version DESIRED` parses semantic versions, accepting an optional leading `v`, prerelease identifiers, and build metadata, but rejecting malformed versions and numeric components with leading zeroes. It also accepts numeric shorthand: `1` means `1.0.0`, and `1.2` means `1.2.0`; both therefore return 0 with no output against current version `2.37.1`. It performs semantic-version ordering against current version `2.37.1`.

If current is at least DESIRED, it returns 0 with no stdout. Thus `2.37.1`, `v2.37.0`, `2.36.99`, `1.20.3`, `2.30.0-alpha`, and `2.30.0+build.123` succeed. If current is older, return 1 and report `current version v2.37.1 is older than the desired version vDESIRED`; for example `2.37.2`, `2.38.0`, `3.0.0`, and `99.0.0` fail. Invalid input returns 1 and says that the supplied text `is not a valid semver version`. Comparison mode prints no version on success.

## Spec 4

Configuration uses these directories, with the first available form taking precedence:

- Config directory: `$DIRENV_CONFIG`; otherwise `$XDG_CONFIG_HOME/direnv`; otherwise `$HOME/.config/direnv`.
- Data directory: `$XDG_DATA_HOME/direnv`; otherwise `$HOME/.local/share/direnv`.
- Cache directory: `$XDG_CACHE_HOME/direnv`; otherwise `$HOME/.cache/direnv`.

When a command needs one of these and neither its XDG variable nor `HOME` makes it available, fail respectively with `couldn't find a configuration directory for direnv`, `couldn't find a data directory for direnv`, or `couldn't find a cache directory for direnv`. `export SHELL` resolves and requires all three directories before RC discovery, even when no RC exists: with `HOME` and `XDG_CACHE_HOME` absent it fails with the cache-directory message, and with `HOME` and `XDG_DATA_HOME` absent it fails with the data-directory message rather than succeeding as an RC-free no-op.

Read `$CONFIG/direnv.toml`, falling back to `$CONFIG/config.toml` only when the first file is absent. Settings may occur below `[global]` or, for backward compatibility, at top level. Supported global keys are `bash_path`, `disable_stdin`, `hide_env_diff`, `load_dotenv`, `strict_env`, `log_filter`, `log_format`, and `warn_timeout`. Supported `[whitelist]` keys are string arrays `prefix` and `exact`. Malformed TOML is fatal and mentions `LoadConfig() failed to parse`, the filename, and the TOML parse error. For example, a missing value for `[global]`'s `warn_timeout` reports `expected value but found '\n' instead`. An invalid regular expression in `log_filter` is fatal and uses Go regexp wording: for `log_filter="["`, it reports:

```text
error in log filter: error parsing regexp: missing closing ]: `[`
```

An invalid TOML `warn_timeout` is also reported as a `LoadConfig() failed to parse FILENAME` error, identifies the key as `global.warn_timeout`, and includes `time: invalid duration "VALUE"`; for `not_a_duration`, the latter text is `time: invalid duration "not_a_duration"`.

Defaults are `disable_stdin=false`, `load_dotenv=false`, `strict_env=false`, `hide_env_diff=false`, `warn_timeout=5s`, and log format `direnv: %s`. Durations accept Go-like forms such as `123ms`, `10s`, `60s`, and `1m30s`. `DIRENV_LOG_FORMAT` is applied only when `$CONFIG/direnv.toml` or its fallback `$CONFIG/config.toml` exists and is loaded; it then overrides a TOML `log_format`. When neither config file exists, `DIRENV_LOG_FORMAT` is ignored: `LOG[%s]` leaves the default log format in effect, and `-` does not suppress diagnostics. With a config file present, `-` is treated as the formatting template rather than as a suppression sentinel; loading diagnostics remain nonempty and begin `-\n%!!(MISSING)(EXTRA string=loading `. The explicit `log` subcommand retains the fixed behavior in Spec 22. `DIRENV_WARN_TIMEOUT` overrides TOML when valid; an invalid value logs `invalid DIRENV_WARN_TIMEOUT` and `invalid duration`, then retains the TOML/default duration and continues. `bash_path` takes precedence, otherwise use `DIRENV_BASH`, otherwise locate `bash` on `PATH`; inability to find it is fatal. The deprecated `skip_dotenv` setting is accepted but emits `direnv: skip_dotenv has been inverted to load_dotenv.`

Expand a leading `~/` in whitelist entries using `HOME`. A prefix entry performs a raw lexical prefix comparison against the RC path, without requiring a path-component boundary. Thus prefix `/trusted` authorizes RCs below `/trusted` and also an RC such as `/trusted-evil/.envrc`. An exact entry names one RC; if it ends in neither `.envrc` nor `.env`, append `/.envrc`. Exact `.env` entries are meaningful when `load_dotenv=true`. Status displays the expanded entries.

## Spec 5

An RC is either `.envrc`, or `.env` only when `load_dotenv=true`. Starting with a supplied directory or the current directory, search that directory and each ancestor through `/`; stop at the nearest directory containing a regular RC file. At each level `.envrc` has priority over `.env`, and finding `.envrc` means `.env` in that directory is not also loaded. A directory named `.envrc` is not an RC. Symlinked directories are followed during discovery. A `.envrc` that is itself a symlink has asymmetric authorization behavior: explicit `allow SYMLINK` follows the symlink and creates the allow record for its canonical target, but later RC discovery and authorization use the symlink path. Consequently, exporting from that directory does not accept the target's allow record: it returns 1, reports the symlink path as blocked, and emits that symlink path as `DIRENV_FILE`. Relative paths, repeated separators, deep nesting, whitespace, `$`, parentheses, Unicode, and other ordinary path characters must work.

With the required base directories resolvable, an invocation without an RC makes `export` a successful no-op with completely empty stdout/stderr, makes `status` report no loaded/found RC, and makes `exec` run its command in the incoming environment. A newly found but unauthorised `.envrc` is not executed; export reports `.envrc is blocked. Run `direnv allow` to approve its content`. Whitelist authorization and an explicit allow record authorize it. An explicit deny record has priority over allow records. Authorization status values are 0=Allowed, 1=NotAllowed, 2=Denied.

## Spec 6

`allow [PATH]` (and its aliases) and `block [PATH]`/`deny [PATH]` (and their aliases) operate on only their first path argument and ignore further path arguments. With no path, find the nearest RC from cwd. An explicit directory resolves to the RC found from that directory; an explicit RC file is used directly if it is an enabled RC type. Canonicalize to an absolute symlink-resolved file. A missing implicit RC fails with exactly `direnv: error .envrc file not found` after ANSI removal. A nonexistent explicit path or broken symlink fails with a system `no such file or directory` diagnostic naming it. An explicit `.env` is rejected as no RC unless `load_dotenv=true`.

Define:

```text
pathHash(P) = lowercase_hex(SHA256(UTF8(canonical_absolute_P + "\n")))
fileHash(P) = lowercase_hex(SHA256(UTF8(canonical_absolute_P + "\n") || exact_file_bytes))
```

Allow creates `$DATA/allow/fileHash(RC)` with mode 0644 and contents `canonical_RC + "\n"`. It removes `$DATA/deny/pathHash(RC)`. Deny creates `$DATA/deny/pathHash(RC)`, mode 0644, with the same path-and-newline content; it removes only `$DATA/allow/fileHash(RC)` for the RC's content at deny time. It does not scan for or remove stale allow hashes created for earlier contents of the same canonical RC. Repetition is idempotent. A content change requires a new allow hash, while the deny filename remains stable across content changes. Successful ordinary allow/deny writes no stdout.

For backward compatibility, if `$CONFIG/allow` is a real directory and `$DATA/allow` does not yet exist, the first allow migrates all old entries to `$DATA/allow`, replaces the old directory by a symlink to the new one, and prints a human-readable migration notice to stdout with empty stderr. The notice contains `Migrating the allow data to the new location`, `The allowed .envrc or .env permissions used to be stored`, `moving`, and `All done, have a nice day!`.

## Spec 7

Required-file approval is scoped to an RC. `$DATA/allowed-required/pathHash(RC)/fileHash(REQUIRED_ABSOLUTE_PATH)` is a mode-0644 record whose text is the required path as originally supplied, plus newline. Required paths are resolved relative to the RC's directory. `DIRENV_REQUIRED` is a colon-separated list created by `check-required` and consumed by `allow`. During allow, approve the main RC first, then each existing required file, printing `direnv: allowing RELATIVE_PATH\n` per file. A missing required file makes allow return 1 with `required file does not exist: RELATIVE_PATH` and creates no record for that required file. Denying the RC removes its entire `allowed-required/pathHash(RC)` directory.

`check-required SHELL RC FILE...` requires all three argument classes; missing ones fail with `a shell name is required`, `an envrc path is required`, or `at least one file path is required`. Validate the target shell as for export. Each FILE must be relative and must contain no `..` path component. Security validation is represented as emitted shell code with process exit 0. For bash/zsh, an absolute path produces exactly:

```text
log_error $'require_allowed: path must be relative: /the/path';
exit 1;
```

and a parent traversal produces:

```text
log_error $'require_allowed: path must not contain \'..\': ../the/path';
exit 1;
```

If all required files have matching approval hashes, emit nothing and return 0. Otherwise emit a shell-specific assignment of `DIRENV_REQUIRED` to the colon-joined unapproved paths, followed by a shell `log_error` call saying `X requires approval. Run 'direnv allow' to approve.` for one file or `X and Y [and Z] require approval...` for multiple files, then shell code `exit 0;`. For bash/zsh, the assignment and `log_error` statement occupy the same physical line with no whitespace or newline between their semicolons: `export DIRENV_REQUIRED=$'secrets.txt';log_error $'secrets.txt requires approval. Run \'direnv allow\' to approve.';\nexit 0;\n`. Fish uses `set -x -g 'DIRENV_REQUIRED' '...';`. Modifying a required file invalidates its approval.

## Spec 8

An authorized `.envrc` is arbitrary Bash, not a key/value file. Execute it in a Bash subprocess with its directory as `PWD`, starting from the incoming environment and with the built-in stdlib available. Set and export `DIRENV_IN_ENVRC=1` only inside this evaluation. If `disable_stdin=true`, attach `/dev/null` as its stdin. If `strict_env=true`, evaluate under `set -euo pipefail`.

Capture the complete exported environment after evaluation. Ordinary Bash constructs must work: multiple exports, overrides, `unset`, quotes and preserved leading/trailing whitespace, command substitution, comments, `$PWD`, inherited variables, Unicode, long values, and changes to `PATH`. An empty `.envrc` is valid. Log `loading ABSOLUTE_RC` to stderr using the configured log format. Unless `hide_env_diff=true`, also log a concise added/changed/removed-variable summary; hiding the summary must not hide the loading line. A failing or partially failing RC must terminate without hanging and must still produce updated tracking state so the it does not reload forever; changes successfully exported before a non-strict failing command remain observable. In particular, `export SHELL` returns 0 while emitting those changes and metadata after a non-strict command-not-found error in the RC. `exec` may continue after a nonfatal sourced-file error but must surface its diagnostic.

Environment diffs must ignore shell/process internals including `_`, `PWD`, `OLDPWD`, `SHLVL`, `DIRENV_BASH`, names beginning `BASH_FUNC_`, and fish-private names beginning `__fish`. They must not appear merely because the evaluation subprocess changed them.

## Spec 9

`stdlib` returns 0 and prints a syntactically valid Bash script. Its first line is `#!/usr/bin/env bash`. The script contains the comment `# These are the commands available in an .envrc context`, enables `shopt -s gnu_errfmt`, `shopt -s nullglob`, and `shopt -s extglob`, assigns `direnv_config_dir="${DIRENV_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/direnv}"`, exports `DIRENV_IN_ENVRC=1`, and embeds the absolute path of the running executable in a `direnv="/absolute/path"` assignment (never the literal placeholder `$(command -v direnv)`). It must be substantial rather than a stub: more than 15,000 output characters and more than 500 lines of valid comments/functions.

It defines at least `has`, `PATH_add`, `expand_path`, `layout`, `use`, `dotenv`, `dotenv_if_exists`, `source_env`, `watch_file`, `watch_dir`, `require_allowed`, `strict_env`, `unstrict_env`, `__env_strictness`, `direnv_load`, `use_nix`, and one or more `layout_...` functions. The behavior used during RC evaluation is:

- `has CMD` succeeds iff `CMD` is available on `PATH`.
- `expand_path PATH [BASE]` prints a normalized absolute path, using `BASE` or `$PWD` for relative input.
- `PATH_add PATH` prepends the expanded path to exported `PATH`.
- `watch_file` and `watch_dir` add their arguments to the watch state described later.
- `source_env PATH_OR_DIR` finds/sources an RC at that location in the same shell and watches it, so its exports survive in the caller. If the referenced path does not exist, it reports `direnv: referenced PATH does not exist`; in a non-strict RC this is nonfatal, later code and an `exec` child still run, and Bash's own `No such file or directory` diagnostic is not substituted for this message.
- `dotenv [FILE]` loads the dotenv file (default `.env`) into the current shell; `dotenv_if_exists` silently skips a missing file.
- `layout NAME ...` dispatches to `layout_NAME`; `use NAME ...` dispatches to `use_NAME`.
- `strict_env`/`unstrict_env` select strict/non-strict Bash behavior.
- `__env_strictness` contains a `case` dispatch with literal `strict)` and `unstrict)` arms.
- `require_allowed FILE...` evaluates `check-required` output, preventing the caller's later code when validation emits `exit 1` and arranging reapproval when it emits `DIRENV_REQUIRED`.
- `direnv_load COMMAND...` runs a child that emits a default gzenv dump and replaces the current exported environment with that dump, including unsets.

In addition to uppercase `PATH_add`, the script defines lowercase `path_add VARNAME PATH...`; `PATH_add` delegates to `path_add PATH "$@"`.

## Spec 10

`export SHELL` loads the nearest RC and emits only the environment difference needed by the requested target. Missing or unknown shell fails with `unknown target shell 'VALUE'`; `export -- json` treats `--` as the shell value and therefore fails. A single leading dash on an actual shell name is stripped, so `-bash` is bash.

On a successful first load, include user additions/removals plus these metadata values:

- `DIRENV_DIR` is `-` followed by the absolute RC directory.
- `DIRENV_FILE` is the absolute discovered RC path. It is normally canonical, but when the RC file itself is a symlink it retains the final symlink path rather than the target path.
- `DIRENV_WATCHES` is a nonempty padded URL-safe-base64, zlib-compressed state string beginning `eJ`; it watches the RC plus its allow and deny record paths and all explicit watches.
- `DIRENV_DIFF` is a nonempty padded URL-safe-base64, zlib-compressed reversible environment-diff string beginning `eJ`.

An empty string is different from an unset variable and must be exported. When the caller supplies the emitted `DIRENV_*` metadata and matching user environment on a later call, an unchanged RC and unchanged watches yield a successful empty stdout. A changed/deleted/appeared watch, pending `DIRENV_REQUIRED`, or change to RC path forces reevaluation. Loading a different RC must start from the environment before the previous RC (using `DIRENV_DIFF`) and then apply the new one. A malformed `DIRENV_DIFF` needed for reversion is fatal with `Revert() failed:` and a base64/unmarshal error.

For NotAllowed status, do not execute user code, return 1, report the blocked message, but still emit tracking/diff metadata in the selected shell format. Explicitly Denied RCs are not executed and their user variables are absent. An RC evaluation error still emits `DIRENV_DIFF`/`DIRENV_WATCHES` state.

## Spec 11

The bash and zsh serializers use identical per-variable syntax, but environment-map iteration order is not stable. Separate bash and zsh dump invocations may place otherwise identical statements in different orders and therefore need not be byte-for-byte equal. A set operation is `export KEY=VALUE;`; conventional all-uppercase keys are literal, while other keys may be Bash-escaped (for example `export $'MixedCase'=...;`). Empty VALUE is `''`; every nonempty value is ANSI-C quoted as `$'...'`. Within it, escape backslash, single quote, newline, carriage return, tab, and control bytes; encode each byte of non-ASCII UTF-8 as lowercase `\xhh`. Examples are:

```text
export SIMPLE=$'value';
export EMPTY='';
export SPECIAL=$'line1\nline2\tquote\'back\\slash';
export UNICODE=$'caf\xc3\xa9';
```

An unset is `unset KEY;`. Every statement ends in a semicolon.

Fish set operations are `set -x -g 'KEY' 'VALUE';`, with single quotes, backslashes, newlines/tabs/control bytes escaped so the statement round-trips. An unset is `set -e -g 'KEY';`. `PATH` is special: split its colon-separated value, preserve empty elements, and emit the entries as separate quoted arguments. Thus `/custom/bin::/usr/bin` is `set -x -g PATH '/custom/bin' '' '/usr/bin';`.

Tcsh set operations are `setenv KEY VALUE ;`; empty value is `''`, spaces and single quotes are backslash-escaped, and tabs/newlines/control bytes use backslash escapes such as `\t` and `\x01`. Unset uses `unsetenv KEY ;`. In a full dump, `PATH=/a:/b:/c` is emitted specially as `set path = ( /a /b /c )`.

## Spec 12

JSON output is a JSON object mapping names to values. `dump json` contains the complete incoming environment, all values are strings, and it is multi-line with two-space indentation. `export json` contains only changes and metadata, is likewise pretty-printed, and represents an unset as JSON `null`. JSON escaping must round-trip quotes, backslashes, newlines, control characters, and UTF-8.

Elvish and murex use the same object semantics but compact, single-line JSON for both dump and export; unsets are `null`. `gzenv` serializes an environment object as zlib-compressed JSON followed by padded URL-safe base64 (the `-`/`_` alphabet), one line beginning `eJ`. It is the default format for `dump` when no shell is provided. Decoding with standard-base64 rather than URL-safe-base64 is not valid. The matching decoder must round-trip arbitrary environment strings.

## Spec 13

PowerShell uses one statement per change: `${env:KEY}='VALUE';`. Single quotes in values are doubled; backslashes, literal newlines, and Unicode otherwise remain literal. Empty keys are skipped. An unset is `Remove-Item -LiteralPath 'env:/KEY';`. Keys are safely escaped so special key characters cannot break the `${env:...}` expression.

Vim uses `call setenv('KEY','VALUE')`, doubling single quotes and representing embedded or consecutive newlines as the two characters `\n`; literal tabs remain literal. An unset is `call setenv('KEY',v:null)`. Every nonempty dump line is a `call setenv(...)` call.

Systemd output writes each variable as `KEY=VALUE` followed by a newline, without `export`, but a value containing newlines spans multiple physical output lines. Simple values such as `value` are unquoted. Ordinary spaces alone do not trigger quoting: `SPACE` with value `a b` is emitted exactly as `SPACE=a b\n`. A multiline value is enclosed in double quotes while its newlines remain literal rather than being escaped. For a value consisting of `a`, LF, `b`, LF, the exact output is:

```text
LINES="a
b
"
```

The newline after the closing quote is the record terminator. Other values requiring escaping, such as those containing backslashes, embedded quotes, or mixed quoting, are enclosed/escaped with systemd-compatible double quotes; already wholly single- or double-quoted content is preserved where safe. UTF-8 and empty values are supported.

## Spec 14

The `gha` serializer writes every set variable as a GitHub Actions environment-file heredoc:

```text
KEY<<ghadelimiter_0123456789abcdef0123456789abcdef
VALUE EXACTLY AS STORED
ghadelimiter_0123456789abcdef0123456789abcdef
```

Generate a fresh, unique delimiter for every variable. It is `ghadelimiter_` plus exactly 32 lowercase hexadecimal characters, and it must not collide with a complete line in that value. Preserve empty strings, multiline values, trailing newlines, tabs, quotes, dollar signs, backslashes, control characters, very long strings, and Unicode literally. GHA has no unset operation, so removed variables produce no record.

Valid keys match `[A-Za-z_][A-Za-z0-9_]*` and retain case. Skip every invalid key and write `direnv: Skipping invalid environment variable key: KEY\n` to stderr, while still returning 0. This applies to both dump and export.

## Spec 15

`hook SHELL` supports bash, zsh, fish, elvish, tcsh, pwsh, and murex. Before lookup, strip one leading `-`, then take the path basename; thus `-bash`, `/bin/bash`, and `-/bin/bash` select bash. Other spellings, case changes, whitespace, numeric, Unicode lookalikes, and unknown names fail as unknown target shells. Missing shell is `unknown target shell ''`.

In the following templates, substitute `<EXE>` with the absolute executable path. Output, including leading/trailing newlines, indentation, and punctuation, is exactly the shown template subject to the explicit final-byte notes below.

Bash:

```bash

_direnv_hook() {
  local previous_exit_status=$?;
  vars="$("<EXE>" export bash)";
  trap -- '' SIGINT;
  eval "$vars";
  trap - SIGINT;
  return $previous_exit_status;
};
if [[ ";${PROMPT_COMMAND[*]:-};" != *";_direnv_hook;"* ]]; then
  if [[ "$(declare -p PROMPT_COMMAND 2>&1)" == "declare -a"* ]]; then
    PROMPT_COMMAND=(_direnv_hook "${PROMPT_COMMAND[@]}")
  else
    PROMPT_COMMAND="_direnv_hook${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
  fi
fi
```

Zsh:

```zsh

_direnv_hook() {
  vars="$("<EXE>" export zsh)"
  trap -- '' SIGINT
  eval "$vars"
  trap - SIGINT
}
typeset -ag precmd_functions
if (( ! ${precmd_functions[(I)_direnv_hook]} )); then
  precmd_functions=(_direnv_hook $precmd_functions)
fi
typeset -ag chpwd_functions
if (( ! ${chpwd_functions[(I)_direnv_hook]} )); then
  chpwd_functions=(_direnv_hook $chpwd_functions)
fi
```

Fish:

```fish

    function __direnv_export_eval --on-event fish_prompt;
        "<EXE>" export fish | source;

        if test "$direnv_fish_mode" != "disable_arrow";
            function __direnv_cd_hook --on-variable PWD;
                if test "$direnv_fish_mode" = "eval_after_arrow";
                    set -g __direnv_export_again 0;
                else;
                    "<EXE>" export fish | source;
                end;
            end;
        end;
    end;

    function __direnv_export_eval_2 --on-event fish_preexec;
        if set -q __direnv_export_again;
            set -e __direnv_export_again;
            "<EXE>" export fish | source;
            echo;
        end;

        functions --erase __direnv_cd_hook;
    end;
```

Elvish:

```text
## hook for direnv
set @edit:before-readline = $@edit:before-readline {
	try {
		var m = [("<EXE>" export elvish | from-json)]
		if (> (count $m) 0) {
			set m = (all $m)
			keys $m | each { |k|
				if $m[$k] {
					set-env $k $m[$k]
				} else {
					unset-env $k
				}
			}
		}
	} catch e {
		echo $e
	}
}
```

Tcsh is exactly `alias precmd 'eval \`<EXE> export tcsh\`'` with no required trailing newline.

Murex:

```text
event: onPrompt direnv_hook=before {
	"<EXE>" export murex -> set exports
	if { $exports != "" } {
		$exports -> :json: formap key value {
			if { is-null value } then {
				!export "$key"
			} else {
				$value -> export "$key"
			}
		}
	}
}
```

The final `}` in the Murex template is the final output byte; there is no trailing newline.

PowerShell:

```powershell
using namespace System;
using namespace System.Management.Automation;

if ($PSVersionTable.PSVersion.Major -lt 7 -or ($PSVersionTable.PSVersion.Major -eq 7 -and $PSVersionTable.PSVersion.Minor -lt 2)) {
    throw "direnv: PowerShell version $($PSVersionTable.PSVersion) does not meet the minimum required version 7.2!"
}

$hook = [EventHandler[LocationChangedEventArgs]] {
  param([object] $source, [LocationChangedEventArgs] $eventArgs)
  end {
    $export = (<EXE> export pwsh) -join [Environment]::NewLine;
    if ($export) {
      Invoke-Expression -Command $export;
    }
  }
};
$currentAction = $ExecutionContext.SessionState.InvokeCommand.LocationChangedAction;
if ($currentAction) {
  $ExecutionContext.SessionState.InvokeCommand.LocationChangedAction = [Delegate]::Combine($currentAction, $hook);
}
else {
  $ExecutionContext.SessionState.InvokeCommand.LocationChangedAction = $hook;
};
```

PowerShell ends with exactly two newline bytes after its final `};`, i.e. the final bytes are `};\n\n`.

Unsupported hook formats fail as follows: `gha` says `Hook not implemented for GitHub Actions shell`; `gzenv` says `the gzenv shell doesn't support hooking`; `vim` says `this feature is not supported. Install the direnv.vim plugin instead`; `json` and `systemd` say `this feature is not supported`.

## Spec 16

`dotenv [SHELL] [PATH]` parses PATH (default `.env`) and serializes only the parsed assignments using the target formats above; default shell is bash. It does not add `DIRENV_*` metadata. A missing file is fatal and names the failed `open`. Empty and comment-only files succeed and emit exactly one newline byte (`\n`) to stdout, with empty stderr.

Accept blank/whitespace lines, CRLF, `#` comment lines, optional `export `, keys including dots/underscores/digits after the first character, optional whitespace around the separator, `KEY=value`, and YAML-like `KEY: value`. Empty assignments are empty strings. Bare values stop before whitespace or `#`; e.g. `HASH=value#comment` yields `value` and `SMTP=smtp    # comment` yields `smtp`. Single-quoted values are literal, perform no expansion, and may span physical lines; preserve their literal newlines through the closing quote. `#` inside either quote style is literal. Double-quoted values may also span lines; preserve those literal newlines. Detect EOF before a closing quote and fail exactly with `unclosed quoted value in .env file`. A non-comment line with no valid assignment fails with `invalid line: ORIGINAL_LINE`.

Expand `$NAME`, `${NAME}`, and `${NAME:-default}` in bare and double-quoted values using the incoming process environment plus assignments already parsed. Missing simple variables expand to empty; defaults are used when missing/empty. Nested later assignments can reference earlier results. Single-quoted `$NAME` remains literal. For a self-reference such as `PATH=/new:$PATH`, use the incoming value of `PATH`. During parsing, `PWD` is the absolute parent directory of the dotenv file.

Within double quotes, `\n` becomes a newline, `\r` becomes a carriage return, `\\` becomes one backslash, `\"` becomes a quote, and a backslash before an ordinary character removes the quoting backslash (for example the evaluated value of `"tab\there"` is `tabthere`). Within single quotes, sequences such as `\n` remain backslash plus `n`. Preserve Unicode. Later duplicate assignments override earlier ones.

A missing dotenv file uses lowercase operating-system wording. For example, `dotenv bash /nonexistent/path/to/.env` fails with `open /nonexistent/path/to/.env: no such file or directory` inside the standard red wrapper.

Representative parsed results are:

```text
export A=2                 -> A is "2"
B='\n'                     -> B is the two characters backslash,n
C="line1\nline2"          -> C contains a newline
D=${MISSING:-default}/x   -> D is "default/x"
E='$HOME'                 -> E is "$HOME"
F: value                  -> F is "value"
```

## Spec 17

`exec` has two forms. `exec DIR COMMAND [ARGS...]` requires both the directory and command, resolves DIR relative to cwd, loads the nearest authorized RC from DIR, and executes COMMAND with the resulting environment. `exec EXECUTABLE_FILE [ARGS...]` recognizes a non-directory first argument as the command itself and searches for an RC from that file's parent. Missing all positional arguments fails with `missing DIR and COMMAND arguments`; a directory without a command fails with `missing COMMAND argument`. A nonexistent directory fails with `stat PATH: no such file or directory`.

After loading the RC, resolve an ordinary command name using the resulting `PATH`; thus an RC may add the command being invoked. An absolute or relative executable-file path may be invoked directly only when executable. An empty, nonexistent, or existing non-executable command fails with `command 'COMMAND' not found on PATH 'PATH_VALUE'`; for an explicit path, `COMMAND` is that path. Preserve argument boundaries literally, including spaces, quotes, `=`, Unicode, and shell metacharacters—do not concatenate and reparse them through a shell.

The child inherits stdin and separate stdout/stderr. Preserve arbitrary multiline/binary-safe output and propagate the child's exact exit status (including 0, 1, 42, and 127). RC loading diagnostics precede child stderr. With no RC, run the command in the pristine incoming environment with no loading diagnostic. Environment overrides, unsets, empty/long values, PATH changes, and parent-RC discovery all apply to the child.

## Spec 18

`status`, `status --json`, and `status -json` succeed for all ordinary states. Trailing/unknown status arguments are ignored; only `--json`/`-json` select JSON. Successful status normally has empty stderr.

Plain status starts with these stable lines, substituting resolved values:

```text
direnv exec path ABSOLUTE_EXISTING_EXECUTABLE_PATH
DIRENV_CONFIG RESOLVED_CONFIG_DIR
bash_path RESOLVED_BASH_PATH
disable_stdin false
warn_timeout 5s
whitelist.prefix []
whitelist.exact map[]
```

Use configured values instead of the shown defaults. If `DIRENV_FILE`/`DIRENV_WATCHES` do not describe a loaded RC, print `No .envrc or .env loaded`; otherwise print `Loaded RC path PATH`, one `Loaded watch: "DISPLAY_PATH" - RFC3339_UTC` per watch, `Loaded RC allowed N`, and `Loaded RC allowPath PATH`. If discovery finds no current RC, print `No .envrc or .env found`; otherwise print the analogous `Found RC path`, `Found watch:`, `Found RC allowed N`, and `Found RC allowPath` lines. Missing watched paths use Unix epoch `1970-01-01T00:00:00Z`; real timestamps are stable UTC `YYYY-MM-DDTHH:MM:SSZ`. An RC normally contributes watches for itself, its allow path, and its deny path.

JSON status is pretty-printed and has exactly top-level keys `config` and `state`. Its shape is:

```json
{
  "config": {
    "ConfigDir": "/resolved/config/direnv",
    "SelfPath": "/absolute/path/to/executable"
  },
  "state": {
    "foundRC": {"allowed": 0, "path": "/project/.envrc"},
    "loadedRC": null
  }
}
```

Each RC value is either null or an object with exactly lowercase `path` (string) and `allowed` (integer). `loadedRC` comes from `DIRENV_FILE` and decoded watches; `foundRC` comes from cwd discovery. With neither, both are null. Status reflects filesystem changes immediately and finds parent RCs.

## Spec 19

`dump [SHELL] [FILE]` serializes the entire incoming environment using the shell formats in Specs 11–14; default SHELL is gzenv. Unknown shells fail. It supports empty, large, Unicode, control-character, and multiline values. If FILE is supplied, it must already exist; open it for truncation/rewrite, write the serialization there, and leave stdout empty. A new/nonexistent output path fails with `open PATH: no such file or directory`. Without FILE, write stdout.

`show_dump DUMP` requires one direct gzenv string, decodes it, and prints a valid pretty JSON object. Missing input fails with `missing DUMP argument`. Malformed base64 reports `unmarshal() base64 decoding: illegal base64 data at input byte N`; specifically, `show_dump invalid_base64_data_xyz` reports byte `20`.

`apply_dump FILE` accepts exactly one filename containing a gzenv dump. No argument fails with `not enough arguments`; more than one fails with `too many arguments`; a missing file reports the failed `open` using lowercase `no such file or directory`, as in `open /tmp/nonexistent_dump_file_xyz.txt: no such file or directory`. Decode the target environment, compare it to the current process environment, and print bash statements that transform current into target, including `unset NAME;` for current-only variables. Identical environments produce no non-whitespace output.

## Spec 20

Watch state is an opaque, padded URL-safe-base64 zlib-compressed value beginning `eJ`, stored in `DIRENV_WATCHES`. It represents a de-duplicated mapping of canonical absolute paths to their observed modification state, including an explicit missing state. All watch-mutating commands merge the existing decoded `DIRENV_WATCHES` rather than replacing it; malformed base64 is fatal with the prefix `unmarshal() base64 decoding:`, followed by an error such as `illegal base64 data at input byte 10`.

`watch SHELL PATH...` accepts zero or more paths. It records each supplied path's current state and emits only the updated `DIRENV_WATCHES` assignment in SHELL syntax. With no paths and no prior state, `watch bash` returns 0 with empty stderr and emits exactly `export DIRENV_WATCHES=$'eJyKjgUEAAD__wEVALk=';` with no trailing newline. `watch-list [SHELL]` defaults to bash, reads stdin lines `INTEGER_MTIME PATH` (split once so PATH may contain spaces), merges them, and emits the updated `DIRENV_WATCHES` assignment in the selected shell syntax. Invalid lines fail as `line N: expected to contain two elements`; invalid integers include `strconv.Atoi: parsing "TEXT": invalid syntax`.

`watch-print` decodes the environment value and prints each path once, newline-terminated; with `--null`, terminate every path with NUL. With no state, it succeeds silently.

`current PATH` requires a path; omitting it returns 1 with `missing PATH argument`. It returns 0 silently iff that path is known and still has exactly its recorded existence/mtime state. Unknown returns 1 and says `File "PATH" is unknown`; changed returns 1 and says `File "PATH" has changed`; a once-existing now-missing path says `File "PATH" is missing (Stat)`. A once-missing file that appears also fails.

`watch-dir SHELL DIR` validates both arguments and the shell. Missing DIR says exactly `a directory is required to add to the list of watches`; a nonexistent directory says `dir 'PATH' does not exist`, including the single quotes. Recursively record the directory itself plus all descendant directories/files, including hidden entries and deep/large trees. Resolve relative input to absolute. Do not follow a broken symlink into its target and do not fail the whole traversal because of it. Merge existing unrelated file/directory watches and emit the updated assignment using bash, zsh, fish, elvish, tcsh, pwsh, json, or vim syntax. Zsh and fish assignments end at their final semicolon with no trailing newline.

## Spec 21

`fetchurl URL [SRI]` implements a content-addressed store at `$CACHE/cas`. A missing URL returns 1 with exactly `missing URL argument`. Create the CAS directory before network activity, even if the request later fails. HTTP/network parsing errors are fatal; any response status other than 200 fails exactly with `expected status code 200 but got CODE` inside the standard red error wrapper.

With no SRI, stream the exact response bytes through SHA-256 and print `sha256-` plus standard padded base64 of the 32-byte digest, followed by newline. This includes the known empty-content digest and must work for binary, Unicode, and large files.

An SRI parser recognizes `sha256-BASE64`, `sha384-BASE64`, and `sha512-BASE64` forms with digest length appropriate to the named algorithm. Reject malformed syntax/base64. An unsupported algorithm token has the exact Go SRI diagnostic; for `not-a-valid-hash`, report `sri: unsupported algo not`. Before parsing, replace `_` with `/` in its base64 part. The CAS filename is lowercase hex of the supplied digest bytes (64 characters for SHA-256). If that path already exists, immediately print it without making a request. Otherwise download and always hash the response bytes with SHA-256. A supplied SHA-256 SRI can match and is installed. A noncached SHA-384 or SHA-512 SRI therefore fails with `hash mismatch. Expected 'EXPECTED' but got 'sha256-ACTUAL_BASE64'`, does not accept/cache the data, and includes both full SRI strings. A SHA-256 match installs the exact file atomically at the CAS path, sets mode 0500 (at least owner read/execute), and prints the absolute path. Query parameters are part of the request URL.

## Spec 22

`edit [PATH]` is intentionally non-interactive at the executable level: it invokes an editor child and waits. Without PATH, find the nearest RC; if none, return 1 with exactly `.envrc or .env not found. Use `direnv edit .` to create a new .envrc in the current directory`. An explicit directory, including `.`, maps to `DIRECTORY/.envrc` even if it does not yet exist. An explicit file is passed as that file.

Use `$EDITOR` when set, finding a bare editor name on `PATH`. If unset, print `\x1b[31mdirenv: $EDITOR not found.\x1b[0m\n` to stderr and search `PATH` in this order for `editor`, `nano`, `vim`, then `emacs`; `vi` is not a default candidate. If no default exists, fail with `could not find a default editor in the PATH`. Invoke the selected editor through `/bin/bash` with the selected RC as an argument. Preserve its output and turn nonzero editor exit into `exit status N`. Thus `$EDITOR=/nonexistent/editor` produces Bash's `/nonexistent/editor: No such file or directory` diagnostic and then the fatal `exit status 127` diagnostic. Only after a successful editor exit, if the file was created or its content/mtime changed, automatically perform allow on it. A failed editor must not authorize a modified file. Successful no-op/edit emits no stdout.

`log TYPE MESSAGE` accepts exactly two arguments. TYPE is `--status`/`-status` or `--error`/`-error`; missing/extra/conflicting arguments fail with `invalid arguments`, while an unknown two-argument type fails with `invalid log-type 'TYPE'`. Output is only on stderr and uses fixed formatting, ignoring `DIRENV_LOG_FORMAT` (including the value `-`). Status is exactly `\x1b[0mdirenv: MESSAGE\n` (no final reset required), while error is exactly `\x1b[31mdirenv: MESSAGE\x1b[0m\n`. Preserve empty, tabbed, multiline, special-character, and Unicode messages exactly; only the first line gets the prefix.

## Spec 23

`prune` validates stored approval state. For every approval record in `$DATA/allow`, read its stored canonical RC path and recompute `fileHash`; remove the record if the RC is missing/non-regular or the filename no longer matches. Keep matching entries. Process every entry, not just the first. If the allow directory itself is absent, return nonzero.

Then validate `$DATA/allowed-required`. A subdirectory name must equal `pathHash` of some still-valid allowed RC or it is removed recursively. Within a valid subdirectory, each nonempty record contains a path relative to that RC directory; remove it if the dependency is gone or its current `fileHash` differs from the record filename. A missing `allowed-required` directory is harmless. Successful pruning produces no required stdout.

`reload` finds the nearest `.envrc` from cwd, follows symlinks, and updates the target file's modification time without altering content or touching unrelated `.env` files. It searches parents. Success returns 0; if none is found, fail and include `.envrc not found`.
