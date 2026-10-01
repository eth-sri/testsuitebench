# Clarified specification: `executable`

## Spec 1 — Product and process contract

Create one directly runnable program named exactly `executable`. It is a Unix command-line implementation of zoxide 0.9.9. It must accept UTF-8 arguments, use stdout and stderr exactly as described below, persist state across processes, and finish ordinary operations on databases of at least 100 entries comfortably within the harness timeouts.

The public command grammar is:

```text
executable add [-s|--score SCORE] PATH...
executable edit
executable import [--merge] --from {autojump,z} PATH
executable init [--cmd CMD] [--hook {none,prompt,pwd}] [--no-cmd] SHELL
executable query [-a|--all] [-i|--interactive] [-l|--list] [-s|--score]
                 [--exclude PATH] [--base-dir PATH] [KEYWORD...]
executable remove [PATH...]
```

`fasd` is an accepted hidden alias of import format `z`; `ksh` is an accepted alias of init shell `posix`. Command and enum names are otherwise case-sensitive. Every command accepts `-h`/`--help` and `-V`/`--version`. `--` terminates option parsing. Repeated scalar options such as `--score` and `--from` are usage errors. `query --interactive --list` is a usage error. With both `--cmd` and `--no-cmd`, `--no-cmd` takes precedence.

The import merge flag has only the long spelling `--merge`; `-m` is an unexpected argument and returns status 2. For `add`, a negative score must be attached to its option token. Accepted spellings include `--score=-7`, `-s-7`, and `-s=-7`; the space-separated forms `--score -7` and `-s -7` treat `-7` as an unexpected argument and return status 2. Once accepted, a negative score has the rank semantics in Spec 5.

## Spec 2 — Exit status, streams, and CLI presentation

Successful operations return 0. Runtime/data errors return 1 and write an error beginning `zoxide:` to stderr. Argument parsing errors return 2 and use the clap-style form shown below. A successful state-changing command normally emits nothing. A bare invocation returns 2 and writes the same text as `--help` to stderr; `--help` returns 0 and writes it to stdout. `--version` and `-V` print exactly `zoxide 0.9.9\n`; subcommand version output must also identify zoxide and 0.9.9.

The root help output is exactly:

```text
zoxide 0.9.9
Ajeet D'Souza <98ajeet@gmail.com>
https://github.com/ajeetdsouza/zoxide

A smarter cd command for your terminal

Usage:
  executable <COMMAND>

Commands:
  add     Add a new directory or increment its rank
  edit    Edit the database
  import  Import entries from another application
  init    Generate shell configuration
  query   Search for a directory in the database
  remove  Remove a directory from the database

Options:
  -h, --help     Print help
  -V, --version  Print version

Environment variables:
  _ZO_DATA_DIR          Path for zoxide data files
  _ZO_ECHO              Print the matched directory before navigating to it when set to 1
  _ZO_EXCLUDE_DIRS      List of directory globs to be excluded
  _ZO_FZF_OPTS          Custom flags to pass to fzf
  _ZO_MAXAGE            Maximum total age after which entries start getting deleted
  _ZO_RESOLVE_SYMLINKS  Resolve symlinks when storing paths
```

All subcommand help includes the same version, author, URL, environment-variable block, its description, grammar, arguments and options. In particular, `add --help` and `query --help` must be exactly the following two blocks (including final newline):

```text
zoxide-add 0.9.9
Ajeet D'Souza <98ajeet@gmail.com>
https://github.com/ajeetdsouza/zoxide

Add a new directory or increment its rank

Usage:
  executable add [OPTIONS] <PATHS>...

Arguments:
  <PATHS>...  

Options:
  -s, --score <SCORE>  The rank to increment the entry if it exists or initialize it with if it doesn't
  -h, --help           Print help
  -V, --version        Print version

Environment variables:
  _ZO_DATA_DIR          Path for zoxide data files
  _ZO_ECHO              Print the matched directory before navigating to it when set to 1
  _ZO_EXCLUDE_DIRS      List of directory globs to be excluded
  _ZO_FZF_OPTS          Custom flags to pass to fzf
  _ZO_MAXAGE            Maximum total age after which entries start getting deleted
  _ZO_RESOLVE_SYMLINKS  Resolve symlinks when storing paths
```

```text
zoxide-query 0.9.9
Ajeet D'Souza <98ajeet@gmail.com>
https://github.com/ajeetdsouza/zoxide

Search for a directory in the database

Usage:
  executable query [OPTIONS] [KEYWORDS]...

Arguments:
  [KEYWORDS]...  

Options:
  -a, --all              Show unavailable directories
  -i, --interactive      Use interactive selection
  -l, --list             List all matching directories
  -s, --score            Print score with results
      --exclude <path>   Exclude the current directory
      --base-dir <path>  Only search within this directory
  -h, --help             Print help
  -V, --version          Print version

Environment variables:
  _ZO_DATA_DIR          Path for zoxide data files
  _ZO_ECHO              Print the matched directory before navigating to it when set to 1
  _ZO_EXCLUDE_DIRS      List of directory globs to be excluded
  _ZO_FZF_OPTS          Custom flags to pass to fzf
  _ZO_MAXAGE            Maximum total age after which entries start getting deleted
  _ZO_RESOLVE_SYMLINKS  Resolve symlinks when storing paths
```

Parsing diagnostics use `error: ...`, a blank line, an optional two-space-indented `tip: ...`, `Usage: ...`, another blank line, and `For more information, try '--help'.`. Required examples are:

```text
error: the following required arguments were not provided:
  <PATHS>...

Usage: executable add <PATHS>...

For more information, try '--help'.
```

Other parser diagnostics must identify: unrecognized subcommands; unexpected flags; missing `<SHELL>`, `<PATH>`, or `--from <FROM>`; invalid floats; duplicate `--score`/`--from`; valid shell names `bash, elvish, fish, nushell, posix, powershell, tcsh, xonsh, zsh`; import values `autojump, z`; hook values `none, prompt, pwd`; and the interactive/list conflict. Unexpected subcommand flags include the tip to use `-- --flag` when appropriate. An empty string supplied as the sole add path is a parsing error saying a value is required for `<PATHS>...`.

## Spec 3 — Database and entry model

Store the database at `<data-dir>/db.zo`. Each entry consists of a path string, floating-point rank, and integer Unix last-access time. State must survive independent invocations; operations must not cache environment or database state between processes. Preserve UTF-8, spaces, punctuation, tabs and (for the internal edit protocol) newlines exactly.

The database is binary, contains stored path bytes verbatim, and begins with little-endian u32 version 3. The rest of the encoding is implementation-defined provided this executable can reliably reload it. A missing database means an empty database. A file whose first u32 is not 3 causes `edit reload` to fail with `zoxide: unsupported version (got N, supports 3)`, where N is that little-endian value (for `invalid data`, N is 1635151465; for zero bytes, N is 0). Corrupt/truncated data must fail cleanly, never crash or signal.

## Spec 4 — Environment

Read configuration anew on every invocation that uses it. Configuration is not eagerly validated by commands that do not use a setting; command-specific behavior is stated below.

- `_ZO_DATA_DIR`: absolute directory holding `db.zo`. Create it and missing parents when a write is needed. A relative value is runtime error 1: `zoxide: _ZO_DATA_DIR must be an absolute path`. Paths containing spaces or Unicode work and separate values select isolated databases. On Linux when unset, use `$XDG_DATA_HOME/zoxide` if `XDG_DATA_HOME` is set, otherwise `$HOME/.local/share/zoxide`.
- `_ZO_MAXAGE`: parsed by `add` as an unsigned decimal integer, default 10000. Zero, leading zeros, and one leading plus sign are valid (`+1` is accepted); a minus sign, floats, whitespace, non-digits, and overflow are invalid. Add-time errors begin `zoxide: unable to parse _ZO_MAXAGE as integer: VALUE`, followed by a blank line and a `Caused by:` parse explanation. `query` does not parse or validate this setting: for example, on an empty database `query --list` with either `not_a_number` or `12.5` returns 0 with empty stdout and stderr.
- `_ZO_RESOLVE_SYMLINKS`: only value `1` enables canonical symlink resolution; unset or `0` leaves symlink identity intact.
- `_ZO_EXCLUDE_DIRS`: platform path-separator-separated glob patterns (`:` on Unix). Empty means no exclusions. Support literal characters, `*`, `?`, and character classes. Reject malformed patterns with `zoxide: invalid glob in _ZO_EXCLUDE_DIRS: PATTERN`, plus a cause. Apply exclusions both when adding and when querying already-stored entries. Match after optional symlink resolution. Excluded adds silently succeed without storing. A query permanently removes matching existing entries from the database rather than merely hiding them; clearing the setting afterward does not restore them. If unset, the user's home directory is the default exclusion.
- `_ZO_ECHO=1` affects generated shell navigation helpers; direct `query` still prints its result normally.
- `_ZO_FZF_OPTS` is listed in help, but direct `query --interactive` does not parse or forward its value. For example, even with `_ZO_FZF_OPTS=--height=40% --reverse`, query invokes fzf with exactly three arguments, in this order: `--delimiter=<TAB>`, `--nth=2`, and `--read0`.

## Spec 5 — Ranking, scoring, ordering, and aging

An ordinary add contributes rank 1.0; `--score S` contributes the parsed floating-point S, subject to the negative-value option syntax in Spec 1. Contributions accumulate for a duplicate path and add refreshes its last-access time. Ranks never fall below 0 when changed through add/edit. A newly added path may have rank 0.0 and remains queryable/listable. Equivalent normalized add spellings deduplicate.

At query/display time calculate score from rank and age:

```text
age < 1 hour:  rank * 4
age < 1 day:   rank * 2
age < 1 week:  rank * 0.5
otherwise:     rank * 0.25
```

Gather query candidates in reverse current-storage order, then sort them by descending computed score using an unstable score-only sort: there is no secondary comparison by timestamp, path, or database position. Equal-score order is therefore the deterministic permutation produced by that unstable sort, not a stable newest/later-entry ordering. In particular, after sequentially adding 110 paths named `bulk-000` through `bulk-109`, then adding score 2 to `bulk-000`, `bulk-010`, ... through `bulk-100`, the tied leading group from `query --list bulk` is, in order, `bulk-000`, `bulk-070`, `bulk-050`, `bulk-020`, `bulk-060`, `bulk-040`, `bulk-030`, `bulk-010`, `bulk-090`, `bulk-100`, `bulk-080`. Display scores as `min(max(score, 0.0), 9999.0)`, right-aligned in a minimum width of 6 with exactly one decimal digit. Query uses `SCORE PATH\n`; edit uses `SCORE<TAB>PATH<NUL>`.

After an `add` that changes the database, if sum of base ranks exceeds maxage, multiply every rank by `0.9 * maxage / total_rank`, then delete entries whose scaled rank is below 1.0. `_ZO_MAXAGE=0` therefore ages all added entries out immediately. Import and internal edit mutations do not trigger this aging step: importing `/import-aged|100|0` with `_ZO_MAXAGE=10` leaves base rank 100, which `edit reload` displays as `  25.0<TAB>/import-aged<NUL>`, and `edit increment edit-aged` with `_ZO_MAXAGE=0` retains the entry and displays `   4.0<TAB>edit-aged<NUL>`.

## Spec 6 — `add`

Resolve each input lexically against the process's actual current working directory, removing `.`, `..`, repeated separators and trailing separators; make it absolute. Preserve symlinks unless resolution is enabled. Every supplied path must exist and be a directory. A failure returns 1 with `zoxide: not a directory: NORMALIZED_PATH`. Validate the whole batch before committing: one bad path leaves all ranks unchanged. Do not expand `$VARS` or `~` in argument strings.

On success, add the contribution to each normalized entry, set access time to now, age/save atomically, and emit nothing. Existing entries are updated rather than duplicated. Directory names containing spaces, Unicode and shell metacharacters are valid. Paths containing line-feed or carriage-return characters are silently ignored so normal query output remains line-oriented. At least one nonempty path argument is syntactically required.

## Spec 7 — `query`: filtering and matching

Without `--all`, permanently remove from the stored database entries whose current path is not a directory, before keyword matching. A later `--all` query cannot recover an entry pruned this way. `--all` retains and includes unavailable, relative and imported paths that have not already been pruned. Likewise, permanently remove `_ZO_EXCLUDE_DIRS` matches. `--base-dir B` retains only entries beneath B as spelled, and `--exclude P` removes only the stored path equal to P as spelled; neither option lexically normalizes its argument. Thus an argument containing `unused/..` is not treated as the equivalent path with those components removed. These per-query filters combine, but unlike the unavailable and environment-exclusion pruning, `--base-dir` and `--exclude` do not themselves delete stored entries.

Keyword matching is Unicode-capable, case-insensitive literal substring matching: regex/glob metacharacters in keywords have no special meaning. Empty keywords are ignored. Keywords must occur in argument order without overlapping. The final keyword must match within the final path component; earlier keywords may match earlier portions/components. Thus `/alpha/beta/gamma` matches `alpha gamma` and `beta gamma`, but not `gamma alpha`; `/usr/local/bin` matches `usr bin` and `bin`, but not `loc`; `/foo/bar` matches the cross-boundary literal `oo/ba`. A keyword ending in `/`, such as `foo/`, selects an immediate child of the matching directory (`/foo/bar`, not `/foo` or `/foo/bar/baz`). A standalone `/` can match a separator between other ordered keywords.

With no keywords, all filtered entries match. Without `--list`, print only the highest score. With `--list`, print every match in score order. Without `--score`, each result is exactly its path and newline; with it, prefix the formatted score and one ASCII space. Non-list no match returns 1 and `zoxide: no match found\n`. List mode with no matches returns 0 and empty stdout/stderr. If a non-list query had exactly one match before `--exclude` removed it, return 1 and `zoxide: you are already in the only match\n`.

## Spec 8 — Interactive query

`query -i` performs the same existence, exclusion, base-directory and keyword filtering, then launches the external `fzf` available on `PATH`, streaming candidates as NUL-delimited records of a score field, tab, and path. The interactive field uses the same minimum-width-six, one-fractional-digit format as other scored query output; for a newly added rank-1 entry it is `   4.0<TAB>PATH<NUL>`. It must tolerate fzf selecting early and closing stdin. Treat fzf stdout as the selection. On status 0, require at least seven bytes, but do not validate that those bytes contain a score or a tab: return the whole selection for `--score`; otherwise blindly strip exactly the first seven bytes and return the remainder without adding a newline. Thus the tabless selection `1234567path` succeeds and returns exactly `path`.

If fzf is absent, return 1 with `zoxide: could not find fzf, is it installed?\n`. A status-0 selection shorter than seven bytes, including an empty selection, returns 1 with `zoxide: could not read selection from fzf\n`. fzf status 1 maps to `zoxide: no match found`; status 2 reports `zoxide: fzf returned an error`; status 130 is propagated with completely empty output; other signal-style statuses report `zoxide: fzf was terminated`.

## Spec 9 — `remove`

With no paths, succeed silently as a no-op. Otherwise normalize arguments lexically to absolute form as for add, but do not require the filesystem objects to exist; stale entries can be removed. Lookup is exact and case-sensitive. Remove all requested paths atomically and preserve every other entry's rank and timestamp. If any path is absent, including a duplicate occurrence after its first provisional removal, return 1 with `zoxide: path not found in database: PATH\n` and commit none of the removals. Successful removal emits nothing. Re-adding a removed path creates a fresh entry.

## Spec 10 — `import`

The import file is UTF-8 and read line by line, ignoring empty lines. Opening failure returns 1 as:

```text
zoxide: could not open database for importing: PATH

Caused by:
    No such file or directory (os error 2)
```

Without `--merge`, importing is allowed only when the current database is empty; otherwise return `zoxide: current database is not empty, specify --merge to continue anyway\n`. Empty files succeed silently. Parsing and merging are atomic.

For `autojump`, each nonempty record is `RANK<TAB>PATH`, split only at the first tab. Parse RANK as a float, preserve the remainder exactly (including further tabs and trailing spaces), convert its contribution to the logistic sigmoid `1 / (1 + exp(-RANK))`, and use last-access epoch 0. A missing tab is `invalid entry: LINE`; a bad rank is `invalid rank: VALUE` with `invalid float literal` as its cause.

For `z` and alias `fasd`, parse each record from the right as `PATH|RANK|EPOCH`, allowing `|` inside PATH. RANK is a float and EPOCH is an integer Unix time. Preserve both directly, including a negative RANK; the stored base rank is not clamped during import, although its displayed score is floored at 0.0 as specified in Spec 5. For example, importing `relative|-1|0` and then incrementing `relative` once produces base rank 0 and displays `   0.0`. Report bad/missing fields as an import error, identifying `invalid rank: VALUE` or `invalid epoch: VALUE` and the underlying parse cause.

Within one file and under `--merge`, duplicate path ranks are summed and the maximum last-access time is kept. Autojump sigmoid conversion occurs per record before summing. Imported paths are neither required to exist nor normalized: relative paths and punctuation are stored verbatim. Success emits nothing.

All parse failures have this structure:

```text
zoxide: import error

Caused by:
    0: SPECIFIC_ERROR
    1: PARSE_CAUSE
```

For a structural error with no nested parse cause, omit numeric nesting and indent the specific error once.

## Spec 11 — Internal edit protocol

`edit` normally opens an interactive database editor through external `fzf`; if fzf cannot be run it returns 1 with `zoxide: could not find fzf, is it installed?\n`. The following positional forms are also accepted as a machine-facing protocol:

```text
edit reload
edit increment PATH
edit decrement PATH
edit delete PATH
```

They do not normalize, validate, or trim PATH; empty, relative, whitespace, tab, newline, Unicode and very long strings are accepted verbatim. `increment` adds 1 to base rank, creating a missing entry at rank 1 with current access time. `decrement` subtracts 1 but clamps at 0, creating a missing entry at rank 0. `delete` is idempotent and silently ignores a missing entry. Changes persist and each form prints the complete resulting database in reverse current-storage order. Additions append; deletion uses swap-removal (the last stored record fills the removed slot). `reload` only prints. Every record is exactly `score:>6.1<TAB>path<NUL>`, including one terminating NUL per record and no newline; empty databases produce zero bytes. Incrementing or decrementing an existing entry does not reorder it.

## Spec 12 — Shell initialization

`init` accepts the nine shells listed in Spec 2 plus alias `ksh`. Default command prefix is `z`; `--cmd X` generates public functions X and Xi while retaining internal `__zoxide_*` helpers; special characters in X are inserted literally. `--no-cmd` suppresses public command functions and marks that section `-- not configured --`. Default hook is `pwd`; explicit `--hook pwd` is byte-identical. `prompt`, `pwd`, and `none` generate their shell-appropriate tracking behavior, with `none` generating no tracking hook. `ksh` output is byte-identical to `posix`.

The scripts call a command named `zoxide` (not the current executable path), implement direct-directory, home, previous-directory and keyword navigation, and define `__zoxide_pwd`, `__zoxide_cd`, `__zoxide_z`, and `__zoxide_zi` where appropriate. Runtime `_ZO_RESOLVE_SYMLINKS=1` causes generated Bash pwd logic to use `pwd -P`; otherwise it uses `pwd -L`. Runtime `_ZO_ECHO=1` makes generated navigation echo the destination.

For the invocations listed in Appendix A, stdout must match the supplied canonical script byte-for-byte and stderr is empty. Other combinations are produced by the same substitutions and hook fragments.

## Spec 13 — Robustness and literal-data rules

Never invoke a shell to interpret path or keyword arguments. Preserve valid filesystem strings, including Unicode, spaces, `$`, `~`, `*`, `?`, brackets, parentheses, backslashes, ampersands and pipes. Add/query/remove workflows must remain consistent across many sequential changes. A malformed user database or broken symlink must produce an ordinary status 1 error at worst, never a crash, panic, hang, or signal termination.

## Appendix A — Canonical `init` outputs

Each subsection names the exact `init` arguments whose stdout is the following fenced payload. The final newline inside every payload is significant.

### A.1 — `init bash`

````text
# shellcheck shell=bash

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd() {
    \builtin pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd() {
    # shellcheck disable=SC2164
    \builtin cd -- "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
__zoxide_oldpwd="$(__zoxide_pwd)"

function __zoxide_hook() {
    \builtin local -r retval="$?"
    \builtin local pwd_tmp
    pwd_tmp="$(__zoxide_pwd)"
    if [[ ${__zoxide_oldpwd} != "${pwd_tmp}" ]]; then
        __zoxide_oldpwd="${pwd_tmp}"
        \command zoxide add -- "${__zoxide_oldpwd}"
    fi
    return "${retval}"
}

# Initialize hook.
if [[ ${PROMPT_COMMAND:=} != *'__zoxide_hook'* ]]; then
    if [[ "$(declare -p PROMPT_COMMAND 2>&1)" == "declare -a"* ]]; then
        PROMPT_COMMAND=("${PROMPT_COMMAND[@]}" __zoxide_hook)
    else
        # shellcheck disable=SC2128,SC2178
        PROMPT_COMMAND="${PROMPT_COMMAND%"${PROMPT_COMMAND##*[![:space:];]}"}"
        # shellcheck disable=SC2128,SC2178
        PROMPT_COMMAND="${PROMPT_COMMAND:+${PROMPT_COMMAND};}__zoxide_hook"
    fi
fi

# Report common issues.
function __zoxide_doctor() {
    [[ ${_ZO_DOCTOR:-1} -eq 0 ]] && return 0
    # shellcheck disable=SC2199
    [[ ${PROMPT_COMMAND[@]:-} == *'__zoxide_hook'* ]] && return 0
    # shellcheck disable=SC2199
    [[ ${__vsc_original_prompt_command[@]:-} == *'__zoxide_hook'* ]] && return 0

    _ZO_DOCTOR=0
    \builtin printf '%s\n' \
        'zoxide: detected a possible configuration issue.' \
        'Please ensure that zoxide is initialized right at the end of your shell configuration file (usually ~/.bashrc).' \
        '' \
        'If the issue persists, consider filing an issue at:' \
        'https://github.com/ajeetdsouza/zoxide/issues' \
        '' \
        'Disable this message by setting _ZO_DOCTOR=0.' \
        '' >&2
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

__zoxide_z_prefix='z#'

# Jump to a directory using only keywords.
function __zoxide_z() {
    __zoxide_doctor

    # shellcheck disable=SC2199
    if [[ $# -eq 0 ]]; then
        __zoxide_cd ~
    elif [[ $# -eq 1 && $1 == '-' ]]; then
        __zoxide_cd "${OLDPWD}"
    elif [[ $# -eq 1 && -d $1 ]]; then
        __zoxide_cd "$1"
    elif [[ $# -eq 2 && $1 == '--' ]]; then
        __zoxide_cd "$2"
    elif [[ ${@: -1} == "${__zoxide_z_prefix}"?* ]]; then
        # shellcheck disable=SC2124
        \builtin local result="${@: -1}"
        __zoxide_cd "${result:${#__zoxide_z_prefix}}"
    else
        \builtin local result
        # shellcheck disable=SC2312
        result="$(\command zoxide query --exclude "$(__zoxide_pwd)" -- "$@")" &&
            __zoxide_cd "${result}"
    fi
}

# Jump to a directory using interactive search.
function __zoxide_zi() {
    __zoxide_doctor
    \builtin local result
    result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

\builtin unalias z &>/dev/null || \builtin true
function z() {
    __zoxide_z "$@"
}

\builtin unalias zi &>/dev/null || \builtin true
function zi() {
    __zoxide_zi "$@"
}

# Load completions.
# - Bash 4.4+ is required to use `@Q`.
# - Completions require line editing. Since Bash supports only two modes of
#   line editing (`vim` and `emacs`), we check if either them is enabled.
# - Completions don't work on `dumb` terminals.
if [[ ${BASH_VERSINFO[0]:-0} -eq 4 && ${BASH_VERSINFO[1]:-0} -ge 4 || ${BASH_VERSINFO[0]:-0} -ge 5 ]] &&
    [[ :"${SHELLOPTS}": =~ :(vi|emacs): && ${TERM} != 'dumb' ]]; then

    function __zoxide_z_complete_helper() {
        READLINE_LINE="z ${__zoxide_result@Q}"
        READLINE_POINT=${#READLINE_LINE}
        bind '"\e[0n": accept-line'
        \builtin printf '\e[5n' >/dev/tty
    }

    function __zoxide_z_complete() {
        # Only show completions when the cursor is at the end of the line.
        [[ ${#COMP_WORDS[@]} -eq $((COMP_CWORD + 1)) ]] || return

        # If there is only one argument, use `cd` completions.
        if [[ ${#COMP_WORDS[@]} -eq 2 ]]; then
            \builtin mapfile -t COMPREPLY < <(
                \builtin compgen -A directory -- "${COMP_WORDS[-1]}" || \builtin true
            )
        # If there is a space after the last word, use interactive selection.
        elif [[ -z ${COMP_WORDS[-1]} ]]; then
            # shellcheck disable=SC2312
            __zoxide_result="$(\command zoxide query --exclude "$(__zoxide_pwd)" --interactive -- "${COMP_WORDS[@]:1:${#COMP_WORDS[@]}-2}")" && {
                # In case the terminal does not respond to \e[5n or another
                # mechanism steals the response, it is still worth completing
                # the directory in the command line.
                COMPREPLY=("${__zoxide_z_prefix}${__zoxide_result}/")

                # Note: We here call "bind" without prefixing "\builtin" to be
                # compatible with frameworks like ble.sh, which emulates Bash's
                # builtin "bind".
                bind -x '"\e[0n": __zoxide_z_complete_helper'
                \builtin printf '\e[5n' >/dev/tty
            }
        fi
    }

    \builtin complete -F __zoxide_z_complete -o filenames -- z
    \builtin complete -r zi &>/dev/null || \builtin true
fi

# =============================================================================
#
# To initialize zoxide, add this to your shell configuration file (usually ~/.bashrc):
#
# eval "$(zoxide init bash)"
````

### A.2 — `init bash --cmd mycd`

````text
# shellcheck shell=bash

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd() {
    \builtin pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd() {
    # shellcheck disable=SC2164
    \builtin cd -- "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
__zoxide_oldpwd="$(__zoxide_pwd)"

function __zoxide_hook() {
    \builtin local -r retval="$?"
    \builtin local pwd_tmp
    pwd_tmp="$(__zoxide_pwd)"
    if [[ ${__zoxide_oldpwd} != "${pwd_tmp}" ]]; then
        __zoxide_oldpwd="${pwd_tmp}"
        \command zoxide add -- "${__zoxide_oldpwd}"
    fi
    return "${retval}"
}

# Initialize hook.
if [[ ${PROMPT_COMMAND:=} != *'__zoxide_hook'* ]]; then
    if [[ "$(declare -p PROMPT_COMMAND 2>&1)" == "declare -a"* ]]; then
        PROMPT_COMMAND=("${PROMPT_COMMAND[@]}" __zoxide_hook)
    else
        # shellcheck disable=SC2128,SC2178
        PROMPT_COMMAND="${PROMPT_COMMAND%"${PROMPT_COMMAND##*[![:space:];]}"}"
        # shellcheck disable=SC2128,SC2178
        PROMPT_COMMAND="${PROMPT_COMMAND:+${PROMPT_COMMAND};}__zoxide_hook"
    fi
fi

# Report common issues.
function __zoxide_doctor() {
    [[ ${_ZO_DOCTOR:-1} -eq 0 ]] && return 0
    # shellcheck disable=SC2199
    [[ ${PROMPT_COMMAND[@]:-} == *'__zoxide_hook'* ]] && return 0
    # shellcheck disable=SC2199
    [[ ${__vsc_original_prompt_command[@]:-} == *'__zoxide_hook'* ]] && return 0

    _ZO_DOCTOR=0
    \builtin printf '%s\n' \
        'zoxide: detected a possible configuration issue.' \
        'Please ensure that zoxide is initialized right at the end of your shell configuration file (usually ~/.bashrc).' \
        '' \
        'If the issue persists, consider filing an issue at:' \
        'https://github.com/ajeetdsouza/zoxide/issues' \
        '' \
        'Disable this message by setting _ZO_DOCTOR=0.' \
        '' >&2
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

__zoxide_z_prefix='z#'

# Jump to a directory using only keywords.
function __zoxide_z() {
    __zoxide_doctor

    # shellcheck disable=SC2199
    if [[ $# -eq 0 ]]; then
        __zoxide_cd ~
    elif [[ $# -eq 1 && $1 == '-' ]]; then
        __zoxide_cd "${OLDPWD}"
    elif [[ $# -eq 1 && -d $1 ]]; then
        __zoxide_cd "$1"
    elif [[ $# -eq 2 && $1 == '--' ]]; then
        __zoxide_cd "$2"
    elif [[ ${@: -1} == "${__zoxide_z_prefix}"?* ]]; then
        # shellcheck disable=SC2124
        \builtin local result="${@: -1}"
        __zoxide_cd "${result:${#__zoxide_z_prefix}}"
    else
        \builtin local result
        # shellcheck disable=SC2312
        result="$(\command zoxide query --exclude "$(__zoxide_pwd)" -- "$@")" &&
            __zoxide_cd "${result}"
    fi
}

# Jump to a directory using interactive search.
function __zoxide_zi() {
    __zoxide_doctor
    \builtin local result
    result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

\builtin unalias mycd &>/dev/null || \builtin true
function mycd() {
    __zoxide_z "$@"
}

\builtin unalias mycdi &>/dev/null || \builtin true
function mycdi() {
    __zoxide_zi "$@"
}

# Load completions.
# - Bash 4.4+ is required to use `@Q`.
# - Completions require line editing. Since Bash supports only two modes of
#   line editing (`vim` and `emacs`), we check if either them is enabled.
# - Completions don't work on `dumb` terminals.
if [[ ${BASH_VERSINFO[0]:-0} -eq 4 && ${BASH_VERSINFO[1]:-0} -ge 4 || ${BASH_VERSINFO[0]:-0} -ge 5 ]] &&
    [[ :"${SHELLOPTS}": =~ :(vi|emacs): && ${TERM} != 'dumb' ]]; then

    function __zoxide_z_complete_helper() {
        READLINE_LINE="mycd ${__zoxide_result@Q}"
        READLINE_POINT=${#READLINE_LINE}
        bind '"\e[0n": accept-line'
        \builtin printf '\e[5n' >/dev/tty
    }

    function __zoxide_z_complete() {
        # Only show completions when the cursor is at the end of the line.
        [[ ${#COMP_WORDS[@]} -eq $((COMP_CWORD + 1)) ]] || return

        # If there is only one argument, use `cd` completions.
        if [[ ${#COMP_WORDS[@]} -eq 2 ]]; then
            \builtin mapfile -t COMPREPLY < <(
                \builtin compgen -A directory -- "${COMP_WORDS[-1]}" || \builtin true
            )
        # If there is a space after the last word, use interactive selection.
        elif [[ -z ${COMP_WORDS[-1]} ]]; then
            # shellcheck disable=SC2312
            __zoxide_result="$(\command zoxide query --exclude "$(__zoxide_pwd)" --interactive -- "${COMP_WORDS[@]:1:${#COMP_WORDS[@]}-2}")" && {
                # In case the terminal does not respond to \e[5n or another
                # mechanism steals the response, it is still worth completing
                # the directory in the command line.
                COMPREPLY=("${__zoxide_z_prefix}${__zoxide_result}/")

                # Note: We here call "bind" without prefixing "\builtin" to be
                # compatible with frameworks like ble.sh, which emulates Bash's
                # builtin "bind".
                bind -x '"\e[0n": __zoxide_z_complete_helper'
                \builtin printf '\e[5n' >/dev/tty
            }
        fi
    }

    \builtin complete -F __zoxide_z_complete -o filenames -- mycd
    \builtin complete -r mycdi &>/dev/null || \builtin true
fi

# =============================================================================
#
# To initialize zoxide, add this to your shell configuration file (usually ~/.bashrc):
#
# eval "$(zoxide init bash)"
````

### A.3 — `init bash --no-cmd`

````text
# shellcheck shell=bash

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd() {
    \builtin pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd() {
    # shellcheck disable=SC2164
    \builtin cd -- "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
__zoxide_oldpwd="$(__zoxide_pwd)"

function __zoxide_hook() {
    \builtin local -r retval="$?"
    \builtin local pwd_tmp
    pwd_tmp="$(__zoxide_pwd)"
    if [[ ${__zoxide_oldpwd} != "${pwd_tmp}" ]]; then
        __zoxide_oldpwd="${pwd_tmp}"
        \command zoxide add -- "${__zoxide_oldpwd}"
    fi
    return "${retval}"
}

# Initialize hook.
if [[ ${PROMPT_COMMAND:=} != *'__zoxide_hook'* ]]; then
    if [[ "$(declare -p PROMPT_COMMAND 2>&1)" == "declare -a"* ]]; then
        PROMPT_COMMAND=("${PROMPT_COMMAND[@]}" __zoxide_hook)
    else
        # shellcheck disable=SC2128,SC2178
        PROMPT_COMMAND="${PROMPT_COMMAND%"${PROMPT_COMMAND##*[![:space:];]}"}"
        # shellcheck disable=SC2128,SC2178
        PROMPT_COMMAND="${PROMPT_COMMAND:+${PROMPT_COMMAND};}__zoxide_hook"
    fi
fi

# Report common issues.
function __zoxide_doctor() {
    [[ ${_ZO_DOCTOR:-1} -eq 0 ]] && return 0
    # shellcheck disable=SC2199
    [[ ${PROMPT_COMMAND[@]:-} == *'__zoxide_hook'* ]] && return 0
    # shellcheck disable=SC2199
    [[ ${__vsc_original_prompt_command[@]:-} == *'__zoxide_hook'* ]] && return 0

    _ZO_DOCTOR=0
    \builtin printf '%s\n' \
        'zoxide: detected a possible configuration issue.' \
        'Please ensure that zoxide is initialized right at the end of your shell configuration file (usually ~/.bashrc).' \
        '' \
        'If the issue persists, consider filing an issue at:' \
        'https://github.com/ajeetdsouza/zoxide/issues' \
        '' \
        'Disable this message by setting _ZO_DOCTOR=0.' \
        '' >&2
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

__zoxide_z_prefix='z#'

# Jump to a directory using only keywords.
function __zoxide_z() {
    __zoxide_doctor

    # shellcheck disable=SC2199
    if [[ $# -eq 0 ]]; then
        __zoxide_cd ~
    elif [[ $# -eq 1 && $1 == '-' ]]; then
        __zoxide_cd "${OLDPWD}"
    elif [[ $# -eq 1 && -d $1 ]]; then
        __zoxide_cd "$1"
    elif [[ $# -eq 2 && $1 == '--' ]]; then
        __zoxide_cd "$2"
    elif [[ ${@: -1} == "${__zoxide_z_prefix}"?* ]]; then
        # shellcheck disable=SC2124
        \builtin local result="${@: -1}"
        __zoxide_cd "${result:${#__zoxide_z_prefix}}"
    else
        \builtin local result
        # shellcheck disable=SC2312
        result="$(\command zoxide query --exclude "$(__zoxide_pwd)" -- "$@")" &&
            __zoxide_cd "${result}"
    fi
}

# Jump to a directory using interactive search.
function __zoxide_zi() {
    __zoxide_doctor
    \builtin local result
    result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

# -- not configured --

# =============================================================================
#
# To initialize zoxide, add this to your shell configuration file (usually ~/.bashrc):
#
# eval "$(zoxide init bash)"
````

### A.4 — `init bash --hook none`

````text
# shellcheck shell=bash

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd() {
    \builtin pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd() {
    # shellcheck disable=SC2164
    \builtin cd -- "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Report common issues.
function __zoxide_doctor() {
    return 0
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

__zoxide_z_prefix='z#'

# Jump to a directory using only keywords.
function __zoxide_z() {
    __zoxide_doctor

    # shellcheck disable=SC2199
    if [[ $# -eq 0 ]]; then
        __zoxide_cd ~
    elif [[ $# -eq 1 && $1 == '-' ]]; then
        __zoxide_cd "${OLDPWD}"
    elif [[ $# -eq 1 && -d $1 ]]; then
        __zoxide_cd "$1"
    elif [[ $# -eq 2 && $1 == '--' ]]; then
        __zoxide_cd "$2"
    elif [[ ${@: -1} == "${__zoxide_z_prefix}"?* ]]; then
        # shellcheck disable=SC2124
        \builtin local result="${@: -1}"
        __zoxide_cd "${result:${#__zoxide_z_prefix}}"
    else
        \builtin local result
        # shellcheck disable=SC2312
        result="$(\command zoxide query --exclude "$(__zoxide_pwd)" -- "$@")" &&
            __zoxide_cd "${result}"
    fi
}

# Jump to a directory using interactive search.
function __zoxide_zi() {
    __zoxide_doctor
    \builtin local result
    result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

\builtin unalias z &>/dev/null || \builtin true
function z() {
    __zoxide_z "$@"
}

\builtin unalias zi &>/dev/null || \builtin true
function zi() {
    __zoxide_zi "$@"
}

# Load completions.
# - Bash 4.4+ is required to use `@Q`.
# - Completions require line editing. Since Bash supports only two modes of
#   line editing (`vim` and `emacs`), we check if either them is enabled.
# - Completions don't work on `dumb` terminals.
if [[ ${BASH_VERSINFO[0]:-0} -eq 4 && ${BASH_VERSINFO[1]:-0} -ge 4 || ${BASH_VERSINFO[0]:-0} -ge 5 ]] &&
    [[ :"${SHELLOPTS}": =~ :(vi|emacs): && ${TERM} != 'dumb' ]]; then

    function __zoxide_z_complete_helper() {
        READLINE_LINE="z ${__zoxide_result@Q}"
        READLINE_POINT=${#READLINE_LINE}
        bind '"\e[0n": accept-line'
        \builtin printf '\e[5n' >/dev/tty
    }

    function __zoxide_z_complete() {
        # Only show completions when the cursor is at the end of the line.
        [[ ${#COMP_WORDS[@]} -eq $((COMP_CWORD + 1)) ]] || return

        # If there is only one argument, use `cd` completions.
        if [[ ${#COMP_WORDS[@]} -eq 2 ]]; then
            \builtin mapfile -t COMPREPLY < <(
                \builtin compgen -A directory -- "${COMP_WORDS[-1]}" || \builtin true
            )
        # If there is a space after the last word, use interactive selection.
        elif [[ -z ${COMP_WORDS[-1]} ]]; then
            # shellcheck disable=SC2312
            __zoxide_result="$(\command zoxide query --exclude "$(__zoxide_pwd)" --interactive -- "${COMP_WORDS[@]:1:${#COMP_WORDS[@]}-2}")" && {
                # In case the terminal does not respond to \e[5n or another
                # mechanism steals the response, it is still worth completing
                # the directory in the command line.
                COMPREPLY=("${__zoxide_z_prefix}${__zoxide_result}/")

                # Note: We here call "bind" without prefixing "\builtin" to be
                # compatible with frameworks like ble.sh, which emulates Bash's
                # builtin "bind".
                bind -x '"\e[0n": __zoxide_z_complete_helper'
                \builtin printf '\e[5n' >/dev/tty
            }
        fi
    }

    \builtin complete -F __zoxide_z_complete -o filenames -- z
    \builtin complete -r zi &>/dev/null || \builtin true
fi

# =============================================================================
#
# To initialize zoxide, add this to your shell configuration file (usually ~/.bashrc):
#
# eval "$(zoxide init bash)"
````

### A.5 — `init fish`

````text
# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd
    builtin pwd -L
end

# A copy of fish's internal cd function. This makes it possible to use
# `alias cd=z` without causing an infinite loop.
if ! builtin functions --query __zoxide_cd_internal
    if status list-files functions/cd.fish &>/dev/null
        status get-file functions/cd.fish | string replace --regex -- '^function cd\s' 'function __zoxide_cd_internal ' | source
    else
        string replace --regex -- '^function cd\s' 'function __zoxide_cd_internal ' <$__fish_data_dir/functions/cd.fish | source
    end
end

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd
    if set -q __zoxide_loop
        builtin echo "zoxide: infinite loop detected"
        builtin echo "Avoid aliasing `cd` to `z` directly, use `zoxide init --cmd=cd fish` instead"
        return 1
    end
    __zoxide_loop=1 __zoxide_cd_internal $argv
end

# =============================================================================
#
# Hook configuration for zoxide.
#

# Initialize hook to add new entries to the database.
function __zoxide_hook --on-variable PWD
    test -z "$fish_private_mode"
    and command zoxide add -- (__zoxide_pwd)
end

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
function __zoxide_z
    set -l argc (builtin count $argv)
    if test $argc -eq 0
        __zoxide_cd $HOME
    else if test "$argv" = -
        __zoxide_cd -
    else if test $argc -eq 1 -a -d $argv[1]
        __zoxide_cd $argv[1]
    else if test $argc -eq 2 -a $argv[1] = --
        __zoxide_cd -- $argv[2]
    else
        set -l result (command zoxide query --exclude (__zoxide_pwd) -- $argv)
        and __zoxide_cd $result
    end
end

# Completions.
function __zoxide_z_complete
    set -l tokens (builtin commandline --current-process --tokenize)
    set -l curr_tokens (builtin commandline --cut-at-cursor --current-process --tokenize)

    if test (builtin count $tokens) -le 2 -a (builtin count $curr_tokens) -eq 1
        # If there are < 2 arguments, use `cd` completions.
        complete --do-complete "'' "(builtin commandline --cut-at-cursor --current-token) | string match --regex -- '.*/$'
    else if test (builtin count $tokens) -eq (builtin count $curr_tokens)
        # If the last argument is empty, use interactive selection.
        set -l query $tokens[2..-1]
        set -l result (command zoxide query --exclude (__zoxide_pwd) --interactive -- $query)
        and __zoxide_cd $result
        and builtin commandline --function cancel-commandline repaint
    end
end
complete --command __zoxide_z --no-files --arguments '(__zoxide_z_complete)'

# Jump to a directory using interactive search.
function __zoxide_zi
    set -l result (command zoxide query --interactive -- $argv)
    and __zoxide_cd $result
end

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

abbr --erase z &>/dev/null
complete --erase --command z
alias z=__zoxide_z

abbr --erase zi &>/dev/null
complete --erase --command zi
alias zi=__zoxide_zi

# =============================================================================
#
# To initialize zoxide, add this to your configuration (usually
# ~/.config/fish/config.fish):
#
#   zoxide init fish | source
````

### A.6 — `init fish --cmd mycd`

````text
# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd
    builtin pwd -L
end

# A copy of fish's internal cd function. This makes it possible to use
# `alias cd=z` without causing an infinite loop.
if ! builtin functions --query __zoxide_cd_internal
    if status list-files functions/cd.fish &>/dev/null
        status get-file functions/cd.fish | string replace --regex -- '^function cd\s' 'function __zoxide_cd_internal ' | source
    else
        string replace --regex -- '^function cd\s' 'function __zoxide_cd_internal ' <$__fish_data_dir/functions/cd.fish | source
    end
end

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd
    if set -q __zoxide_loop
        builtin echo "zoxide: infinite loop detected"
        builtin echo "Avoid aliasing `cd` to `z` directly, use `zoxide init --cmd=cd fish` instead"
        return 1
    end
    __zoxide_loop=1 __zoxide_cd_internal $argv
end

# =============================================================================
#
# Hook configuration for zoxide.
#

# Initialize hook to add new entries to the database.
function __zoxide_hook --on-variable PWD
    test -z "$fish_private_mode"
    and command zoxide add -- (__zoxide_pwd)
end

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
function __zoxide_z
    set -l argc (builtin count $argv)
    if test $argc -eq 0
        __zoxide_cd $HOME
    else if test "$argv" = -
        __zoxide_cd -
    else if test $argc -eq 1 -a -d $argv[1]
        __zoxide_cd $argv[1]
    else if test $argc -eq 2 -a $argv[1] = --
        __zoxide_cd -- $argv[2]
    else
        set -l result (command zoxide query --exclude (__zoxide_pwd) -- $argv)
        and __zoxide_cd $result
    end
end

# Completions.
function __zoxide_z_complete
    set -l tokens (builtin commandline --current-process --tokenize)
    set -l curr_tokens (builtin commandline --cut-at-cursor --current-process --tokenize)

    if test (builtin count $tokens) -le 2 -a (builtin count $curr_tokens) -eq 1
        # If there are < 2 arguments, use `cd` completions.
        complete --do-complete "'' "(builtin commandline --cut-at-cursor --current-token) | string match --regex -- '.*/$'
    else if test (builtin count $tokens) -eq (builtin count $curr_tokens)
        # If the last argument is empty, use interactive selection.
        set -l query $tokens[2..-1]
        set -l result (command zoxide query --exclude (__zoxide_pwd) --interactive -- $query)
        and __zoxide_cd $result
        and builtin commandline --function cancel-commandline repaint
    end
end
complete --command __zoxide_z --no-files --arguments '(__zoxide_z_complete)'

# Jump to a directory using interactive search.
function __zoxide_zi
    set -l result (command zoxide query --interactive -- $argv)
    and __zoxide_cd $result
end

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

abbr --erase mycd &>/dev/null
complete --erase --command mycd
alias mycd=__zoxide_z

abbr --erase mycdi &>/dev/null
complete --erase --command mycdi
alias mycdi=__zoxide_zi

# =============================================================================
#
# To initialize zoxide, add this to your configuration (usually
# ~/.config/fish/config.fish):
#
#   zoxide init fish | source
````

### A.7 — `init fish --hook none`

````text
# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd
    builtin pwd -L
end

# A copy of fish's internal cd function. This makes it possible to use
# `alias cd=z` without causing an infinite loop.
if ! builtin functions --query __zoxide_cd_internal
    if status list-files functions/cd.fish &>/dev/null
        status get-file functions/cd.fish | string replace --regex -- '^function cd\s' 'function __zoxide_cd_internal ' | source
    else
        string replace --regex -- '^function cd\s' 'function __zoxide_cd_internal ' <$__fish_data_dir/functions/cd.fish | source
    end
end

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd
    if set -q __zoxide_loop
        builtin echo "zoxide: infinite loop detected"
        builtin echo "Avoid aliasing `cd` to `z` directly, use `zoxide init --cmd=cd fish` instead"
        return 1
    end
    __zoxide_loop=1 __zoxide_cd_internal $argv
end

# =============================================================================
#
# Hook configuration for zoxide.
#

# -- not configured --

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
function __zoxide_z
    set -l argc (builtin count $argv)
    if test $argc -eq 0
        __zoxide_cd $HOME
    else if test "$argv" = -
        __zoxide_cd -
    else if test $argc -eq 1 -a -d $argv[1]
        __zoxide_cd $argv[1]
    else if test $argc -eq 2 -a $argv[1] = --
        __zoxide_cd -- $argv[2]
    else
        set -l result (command zoxide query --exclude (__zoxide_pwd) -- $argv)
        and __zoxide_cd $result
    end
end

# Completions.
function __zoxide_z_complete
    set -l tokens (builtin commandline --current-process --tokenize)
    set -l curr_tokens (builtin commandline --cut-at-cursor --current-process --tokenize)

    if test (builtin count $tokens) -le 2 -a (builtin count $curr_tokens) -eq 1
        # If there are < 2 arguments, use `cd` completions.
        complete --do-complete "'' "(builtin commandline --cut-at-cursor --current-token) | string match --regex -- '.*/$'
    else if test (builtin count $tokens) -eq (builtin count $curr_tokens)
        # If the last argument is empty, use interactive selection.
        set -l query $tokens[2..-1]
        set -l result (command zoxide query --exclude (__zoxide_pwd) --interactive -- $query)
        and __zoxide_cd $result
        and builtin commandline --function cancel-commandline repaint
    end
end
complete --command __zoxide_z --no-files --arguments '(__zoxide_z_complete)'

# Jump to a directory using interactive search.
function __zoxide_zi
    set -l result (command zoxide query --interactive -- $argv)
    and __zoxide_cd $result
end

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

abbr --erase z &>/dev/null
complete --erase --command z
alias z=__zoxide_z

abbr --erase zi &>/dev/null
complete --erase --command zi
alias zi=__zoxide_zi

# =============================================================================
#
# To initialize zoxide, add this to your configuration (usually
# ~/.config/fish/config.fish):
#
#   zoxide init fish | source
````

### A.8 — `init zsh`

````text
# shellcheck shell=bash

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd() {
    \builtin pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd() {
    # shellcheck disable=SC2164
    \builtin cd -- "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
function __zoxide_hook() {
    # shellcheck disable=SC2312
    \command zoxide add -- "$(__zoxide_pwd)"
}

# Initialize hook.
\builtin typeset -ga precmd_functions
\builtin typeset -ga chpwd_functions
# shellcheck disable=SC2034,SC2296
precmd_functions=("${(@)precmd_functions:#__zoxide_hook}")
# shellcheck disable=SC2034,SC2296
chpwd_functions=("${(@)chpwd_functions:#__zoxide_hook}")
chpwd_functions+=(__zoxide_hook)

# Report common issues.
function __zoxide_doctor() {
    [[ ${_ZO_DOCTOR:-1} -ne 0 ]] || return 0
    [[ ${chpwd_functions[(Ie)__zoxide_hook]:-} -eq 0 ]] || return 0

    _ZO_DOCTOR=0
    \builtin printf '%s\n' \
        'zoxide: detected a possible configuration issue.' \
        'Please ensure that zoxide is initialized right at the end of your shell configuration file (usually ~/.zshrc).' \
        '' \
        'If the issue persists, consider filing an issue at:' \
        'https://github.com/ajeetdsouza/zoxide/issues' \
        '' \
        'Disable this message by setting _ZO_DOCTOR=0.' \
        '' >&2
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
function __zoxide_z() {
    __zoxide_doctor
    if [[ "$#" -eq 0 ]]; then
        __zoxide_cd ~
    elif [[ "$#" -eq 1 ]] && { [[ -d "$1" ]] || [[ "$1" = '-' ]] || [[ "$1" =~ ^[-+][0-9]+$ ]]; }; then
        __zoxide_cd "$1"
    elif [[ "$#" -eq 2 ]] && [[ "$1" = "--" ]]; then
        __zoxide_cd "$2"
    else
        \builtin local result
        # shellcheck disable=SC2312
        result="$(\command zoxide query --exclude "$(__zoxide_pwd)" -- "$@")" && __zoxide_cd "${result}"
    fi
}

# Jump to a directory using interactive search.
function __zoxide_zi() {
    __zoxide_doctor
    \builtin local result
    result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

function z() {
    __zoxide_z "$@"
}

function zi() {
    __zoxide_zi "$@"
}

# Completions.
if [[ -o zle ]]; then
    __zoxide_result=''

    function __zoxide_z_complete() {
        # Only show completions when the cursor is at the end of the line.
        # shellcheck disable=SC2154
        [[ "${#words[@]}" -eq "${CURRENT}" ]] || return 0

        if [[ "${#words[@]}" -eq 2 ]]; then
            # Show completions for local directories.
            _cd -/

        elif [[ "${words[-1]}" == '' ]]; then
            # Show completions for Space-Tab.
            # shellcheck disable=SC2086
            __zoxide_result="$(\command zoxide query --exclude "$(__zoxide_pwd || \builtin true)" --interactive -- ${words[2,-1]})" || __zoxide_result=''

            # Set a result to ensure completion doesn't re-run
            compadd -Q ""

            # Bind '\e[0n' to helper function.
            \builtin bindkey '\e[0n' '__zoxide_z_complete_helper'
            # Sends query device status code, which results in a '\e[0n' being sent to console input.
            \builtin printf '\e[5n'

            # Report that the completion was successful, so that we don't fall back
            # to another completion function.
            return 0
        fi
    }

    function __zoxide_z_complete_helper() {
        if [[ -n "${__zoxide_result}" ]]; then
            # shellcheck disable=SC2034,SC2296
            BUFFER="z ${(q-)__zoxide_result}"
            __zoxide_result=''
            \builtin zle reset-prompt
            \builtin zle accept-line
        else
            \builtin zle reset-prompt
        fi
    }
    \builtin zle -N __zoxide_z_complete_helper

    [[ "${+functions[compdef]}" -ne 0 ]] && \compdef __zoxide_z_complete z
fi

# =============================================================================
#
# To initialize zoxide, add this to your shell configuration file (usually ~/.zshrc):
#
# eval "$(zoxide init zsh)"
````

### A.9 — `init zsh --hook prompt`

````text
# shellcheck shell=bash

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd() {
    \builtin pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd() {
    # shellcheck disable=SC2164
    \builtin cd -- "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
function __zoxide_hook() {
    # shellcheck disable=SC2312
    \command zoxide add -- "$(__zoxide_pwd)"
}

# Initialize hook.
\builtin typeset -ga precmd_functions
\builtin typeset -ga chpwd_functions
# shellcheck disable=SC2034,SC2296
precmd_functions=("${(@)precmd_functions:#__zoxide_hook}")
# shellcheck disable=SC2034,SC2296
chpwd_functions=("${(@)chpwd_functions:#__zoxide_hook}")
precmd_functions+=(__zoxide_hook)

# Report common issues.
function __zoxide_doctor() {
    [[ ${_ZO_DOCTOR:-1} -ne 0 ]] || return 0
    [[ ${precmd_functions[(Ie)__zoxide_hook]:-} -eq 0 ]] || return 0

    _ZO_DOCTOR=0
    \builtin printf '%s\n' \
        'zoxide: detected a possible configuration issue.' \
        'Please ensure that zoxide is initialized right at the end of your shell configuration file (usually ~/.zshrc).' \
        '' \
        'If the issue persists, consider filing an issue at:' \
        'https://github.com/ajeetdsouza/zoxide/issues' \
        '' \
        'Disable this message by setting _ZO_DOCTOR=0.' \
        '' >&2
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
function __zoxide_z() {
    __zoxide_doctor
    if [[ "$#" -eq 0 ]]; then
        __zoxide_cd ~
    elif [[ "$#" -eq 1 ]] && { [[ -d "$1" ]] || [[ "$1" = '-' ]] || [[ "$1" =~ ^[-+][0-9]+$ ]]; }; then
        __zoxide_cd "$1"
    elif [[ "$#" -eq 2 ]] && [[ "$1" = "--" ]]; then
        __zoxide_cd "$2"
    else
        \builtin local result
        # shellcheck disable=SC2312
        result="$(\command zoxide query --exclude "$(__zoxide_pwd)" -- "$@")" && __zoxide_cd "${result}"
    fi
}

# Jump to a directory using interactive search.
function __zoxide_zi() {
    __zoxide_doctor
    \builtin local result
    result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

function z() {
    __zoxide_z "$@"
}

function zi() {
    __zoxide_zi "$@"
}

# Completions.
if [[ -o zle ]]; then
    __zoxide_result=''

    function __zoxide_z_complete() {
        # Only show completions when the cursor is at the end of the line.
        # shellcheck disable=SC2154
        [[ "${#words[@]}" -eq "${CURRENT}" ]] || return 0

        if [[ "${#words[@]}" -eq 2 ]]; then
            # Show completions for local directories.
            _cd -/

        elif [[ "${words[-1]}" == '' ]]; then
            # Show completions for Space-Tab.
            # shellcheck disable=SC2086
            __zoxide_result="$(\command zoxide query --exclude "$(__zoxide_pwd || \builtin true)" --interactive -- ${words[2,-1]})" || __zoxide_result=''

            # Set a result to ensure completion doesn't re-run
            compadd -Q ""

            # Bind '\e[0n' to helper function.
            \builtin bindkey '\e[0n' '__zoxide_z_complete_helper'
            # Sends query device status code, which results in a '\e[0n' being sent to console input.
            \builtin printf '\e[5n'

            # Report that the completion was successful, so that we don't fall back
            # to another completion function.
            return 0
        fi
    }

    function __zoxide_z_complete_helper() {
        if [[ -n "${__zoxide_result}" ]]; then
            # shellcheck disable=SC2034,SC2296
            BUFFER="z ${(q-)__zoxide_result}"
            __zoxide_result=''
            \builtin zle reset-prompt
            \builtin zle accept-line
        else
            \builtin zle reset-prompt
        fi
    }
    \builtin zle -N __zoxide_z_complete_helper

    [[ "${+functions[compdef]}" -ne 0 ]] && \compdef __zoxide_z_complete z
fi

# =============================================================================
#
# To initialize zoxide, add this to your shell configuration file (usually ~/.zshrc):
#
# eval "$(zoxide init zsh)"
````

### A.10 — `init zsh --no-cmd`

````text
# shellcheck shell=bash

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
function __zoxide_pwd() {
    \builtin pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
function __zoxide_cd() {
    # shellcheck disable=SC2164
    \builtin cd -- "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
function __zoxide_hook() {
    # shellcheck disable=SC2312
    \command zoxide add -- "$(__zoxide_pwd)"
}

# Initialize hook.
\builtin typeset -ga precmd_functions
\builtin typeset -ga chpwd_functions
# shellcheck disable=SC2034,SC2296
precmd_functions=("${(@)precmd_functions:#__zoxide_hook}")
# shellcheck disable=SC2034,SC2296
chpwd_functions=("${(@)chpwd_functions:#__zoxide_hook}")
chpwd_functions+=(__zoxide_hook)

# Report common issues.
function __zoxide_doctor() {
    [[ ${_ZO_DOCTOR:-1} -ne 0 ]] || return 0
    [[ ${chpwd_functions[(Ie)__zoxide_hook]:-} -eq 0 ]] || return 0

    _ZO_DOCTOR=0
    \builtin printf '%s\n' \
        'zoxide: detected a possible configuration issue.' \
        'Please ensure that zoxide is initialized right at the end of your shell configuration file (usually ~/.zshrc).' \
        '' \
        'If the issue persists, consider filing an issue at:' \
        'https://github.com/ajeetdsouza/zoxide/issues' \
        '' \
        'Disable this message by setting _ZO_DOCTOR=0.' \
        '' >&2
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
function __zoxide_z() {
    __zoxide_doctor
    if [[ "$#" -eq 0 ]]; then
        __zoxide_cd ~
    elif [[ "$#" -eq 1 ]] && { [[ -d "$1" ]] || [[ "$1" = '-' ]] || [[ "$1" =~ ^[-+][0-9]+$ ]]; }; then
        __zoxide_cd "$1"
    elif [[ "$#" -eq 2 ]] && [[ "$1" = "--" ]]; then
        __zoxide_cd "$2"
    else
        \builtin local result
        # shellcheck disable=SC2312
        result="$(\command zoxide query --exclude "$(__zoxide_pwd)" -- "$@")" && __zoxide_cd "${result}"
    fi
}

# Jump to a directory using interactive search.
function __zoxide_zi() {
    __zoxide_doctor
    \builtin local result
    result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

# -- not configured --

# Completions.
if [[ -o zle ]]; then
    __zoxide_result=''

    function __zoxide_z_complete() {
        # Only show completions when the cursor is at the end of the line.
        # shellcheck disable=SC2154
        [[ "${#words[@]}" -eq "${CURRENT}" ]] || return 0

        if [[ "${#words[@]}" -eq 2 ]]; then
            # Show completions for local directories.
            _cd -/

        elif [[ "${words[-1]}" == '' ]]; then
            # Show completions for Space-Tab.
            # shellcheck disable=SC2086
            __zoxide_result="$(\command zoxide query --exclude "$(__zoxide_pwd || \builtin true)" --interactive -- ${words[2,-1]})" || __zoxide_result=''

            # Set a result to ensure completion doesn't re-run
            compadd -Q ""

            # Bind '\e[0n' to helper function.
            \builtin bindkey '\e[0n' '__zoxide_z_complete_helper'
            # Sends query device status code, which results in a '\e[0n' being sent to console input.
            \builtin printf '\e[5n'

            # Report that the completion was successful, so that we don't fall back
            # to another completion function.
            return 0
        fi
    }

    function __zoxide_z_complete_helper() {
        if [[ -n "${__zoxide_result}" ]]; then
            # shellcheck disable=SC2034,SC2296
            BUFFER="cd ${(q-)__zoxide_result}"
            __zoxide_result=''
            \builtin zle reset-prompt
            \builtin zle accept-line
        else
            \builtin zle reset-prompt
        fi
    }
    \builtin zle -N __zoxide_z_complete_helper
fi

# =============================================================================
#
# To initialize zoxide, add this to your shell configuration file (usually ~/.zshrc):
#
# eval "$(zoxide init zsh)"
````

### A.11 — `init powershell`

````text
# =============================================================================
#
# Utility functions for zoxide.
#

# Call zoxide binary, returning the output as UTF-8.
function global:__zoxide_bin {
    $encoding = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = [System.Text.Utf8Encoding]::new()
        $result = zoxide @args
        return $result
    } finally {
        [Console]::OutputEncoding = $encoding
    }
}

# pwd based on zoxide's format.
function global:__zoxide_pwd {
    $cwd = Get-Location
    if ($cwd.Provider.Name -eq "FileSystem") {
        $cwd.ProviderPath
    }
}

# cd + custom logic based on the value of _ZO_ECHO.
function global:__zoxide_cd($dir, $literal) {
    $dir = if ($literal) {
        if ($null -eq $dir) {
            Set-Location
        } else {
            Set-Location -LiteralPath $dir -Passthru -ErrorAction Stop
        }
    } else {
        if ($dir -eq '-' -and ($PSVersionTable.PSVersion -lt 6.1)) {
            Write-Error "cd - is not supported below PowerShell 6.1. Please upgrade your version of PowerShell."
        }
        elseif ($dir -eq '+' -and ($PSVersionTable.PSVersion -lt 6.2)) {
            Write-Error "cd + is not supported below PowerShell 6.2. Please upgrade your version of PowerShell."
        }
        else {
            Set-Location -Path $dir -Passthru -ErrorAction Stop
        }
    }
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
$global:__zoxide_oldpwd = __zoxide_pwd
function global:__zoxide_hook {
    $result = __zoxide_pwd
    if ($result -ne $global:__zoxide_oldpwd) {
        if ($null -ne $result) {
            zoxide add "--" $result
        }
        $global:__zoxide_oldpwd = $result
    }
}

# Initialize hook.
$global:__zoxide_hooked = (Get-Variable __zoxide_hooked -ErrorAction Ignore -ValueOnly)
if ($global:__zoxide_hooked -ne 1) {
    $global:__zoxide_hooked = 1
    $global:__zoxide_prompt_old = $function:prompt

    function global:prompt {
        if ($null -ne $__zoxide_prompt_old) {
            & $__zoxide_prompt_old
        }
        $null = __zoxide_hook
    }
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
function global:__zoxide_z {
    if ($args.Length -eq 0) {
        __zoxide_cd $null $true
    }
    elseif ($args.Length -eq 1 -and ($args[0] -eq '-' -or $args[0] -eq '+')) {
        __zoxide_cd $args[0] $false
    }
    elseif ($args.Length -eq 1 -and (Test-Path -PathType Container -LiteralPath $args[0])) {
        __zoxide_cd $args[0] $true
    }
    elseif ($args.Length -eq 1 -and (Test-Path -PathType Container -Path $args[0] )) {
        __zoxide_cd $args[0] $false
    }
    else {
        $result = __zoxide_pwd
        if ($null -ne $result) {
            $result = __zoxide_bin query --exclude $result "--" @args
        }
        else {
            $result = __zoxide_bin query "--" @args
        }
        if ($LASTEXITCODE -eq 0) {
            __zoxide_cd $result $true
        }
    }
}

# Jump to a directory using interactive search.
function global:__zoxide_zi {
    $result = __zoxide_bin query -i "--" @args
    if ($LASTEXITCODE -eq 0) {
        __zoxide_cd $result $true
    }
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

Set-Alias -Name z -Value __zoxide_z -Option AllScope -Scope Global -Force
Set-Alias -Name zi -Value __zoxide_zi -Option AllScope -Scope Global -Force

# =============================================================================
#
# To initialize zoxide, add this to your configuration (find it by running
# `echo $profile` in PowerShell):
#
# Invoke-Expression (& { (zoxide init powershell | Out-String) })
````

### A.12 — `init powershell --cmd j`

````text
# =============================================================================
#
# Utility functions for zoxide.
#

# Call zoxide binary, returning the output as UTF-8.
function global:__zoxide_bin {
    $encoding = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = [System.Text.Utf8Encoding]::new()
        $result = zoxide @args
        return $result
    } finally {
        [Console]::OutputEncoding = $encoding
    }
}

# pwd based on zoxide's format.
function global:__zoxide_pwd {
    $cwd = Get-Location
    if ($cwd.Provider.Name -eq "FileSystem") {
        $cwd.ProviderPath
    }
}

# cd + custom logic based on the value of _ZO_ECHO.
function global:__zoxide_cd($dir, $literal) {
    $dir = if ($literal) {
        if ($null -eq $dir) {
            Set-Location
        } else {
            Set-Location -LiteralPath $dir -Passthru -ErrorAction Stop
        }
    } else {
        if ($dir -eq '-' -and ($PSVersionTable.PSVersion -lt 6.1)) {
            Write-Error "cd - is not supported below PowerShell 6.1. Please upgrade your version of PowerShell."
        }
        elseif ($dir -eq '+' -and ($PSVersionTable.PSVersion -lt 6.2)) {
            Write-Error "cd + is not supported below PowerShell 6.2. Please upgrade your version of PowerShell."
        }
        else {
            Set-Location -Path $dir -Passthru -ErrorAction Stop
        }
    }
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
$global:__zoxide_oldpwd = __zoxide_pwd
function global:__zoxide_hook {
    $result = __zoxide_pwd
    if ($result -ne $global:__zoxide_oldpwd) {
        if ($null -ne $result) {
            zoxide add "--" $result
        }
        $global:__zoxide_oldpwd = $result
    }
}

# Initialize hook.
$global:__zoxide_hooked = (Get-Variable __zoxide_hooked -ErrorAction Ignore -ValueOnly)
if ($global:__zoxide_hooked -ne 1) {
    $global:__zoxide_hooked = 1
    $global:__zoxide_prompt_old = $function:prompt

    function global:prompt {
        if ($null -ne $__zoxide_prompt_old) {
            & $__zoxide_prompt_old
        }
        $null = __zoxide_hook
    }
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
function global:__zoxide_z {
    if ($args.Length -eq 0) {
        __zoxide_cd $null $true
    }
    elseif ($args.Length -eq 1 -and ($args[0] -eq '-' -or $args[0] -eq '+')) {
        __zoxide_cd $args[0] $false
    }
    elseif ($args.Length -eq 1 -and (Test-Path -PathType Container -LiteralPath $args[0])) {
        __zoxide_cd $args[0] $true
    }
    elseif ($args.Length -eq 1 -and (Test-Path -PathType Container -Path $args[0] )) {
        __zoxide_cd $args[0] $false
    }
    else {
        $result = __zoxide_pwd
        if ($null -ne $result) {
            $result = __zoxide_bin query --exclude $result "--" @args
        }
        else {
            $result = __zoxide_bin query "--" @args
        }
        if ($LASTEXITCODE -eq 0) {
            __zoxide_cd $result $true
        }
    }
}

# Jump to a directory using interactive search.
function global:__zoxide_zi {
    $result = __zoxide_bin query -i "--" @args
    if ($LASTEXITCODE -eq 0) {
        __zoxide_cd $result $true
    }
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

Set-Alias -Name j -Value __zoxide_z -Option AllScope -Scope Global -Force
Set-Alias -Name ji -Value __zoxide_zi -Option AllScope -Scope Global -Force

# =============================================================================
#
# To initialize zoxide, add this to your configuration (find it by running
# `echo $profile` in PowerShell):
#
# Invoke-Expression (& { (zoxide init powershell | Out-String) })
````

### A.13 — `init elvish`

````text
use builtin
use path

# =============================================================================
#
# Utility functions for zoxide.
#

# cd + custom logic based on the value of _ZO_ECHO.
fn __zoxide_cd {|path|
    builtin:cd $path
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# Initialize hook to track previous directory.
var oldpwd = $builtin:pwd
set builtin:before-chdir = [$@builtin:before-chdir {|_| set oldpwd = $builtin:pwd }]

# Initialize hook to add directories to zoxide.
if (builtin:not (builtin:eq $E:__zoxide_shlvl $E:SHLVL)) {
    set E:__zoxide_shlvl = $E:SHLVL
    set builtin:after-chdir = [$@builtin:after-chdir {|_| zoxide add -- $pwd }]
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
fn __zoxide_z {|@rest|
    if (builtin:eq [] $rest) {
        __zoxide_cd ~
    } elif (builtin:eq [-] $rest) {
        __zoxide_cd $oldpwd
    } elif (and ('builtin:==' (builtin:count $rest) 1) (path:is-dir &follow-symlink=$true $rest[0])) {
        __zoxide_cd $rest[0]
    } else {
        var path
        try {
            set path = (zoxide query --exclude $pwd -- $@rest)
        } catch {
        } else {
            __zoxide_cd $path
        }
    }
}
edit:add-var __zoxide_z~ $__zoxide_z~

# Jump to a directory using interactive search.
fn __zoxide_zi {|@rest|
    var path
    try {
        set path = (zoxide query --interactive -- $@rest)
    } catch {
    } else {
        __zoxide_cd $path
    }
}
edit:add-var __zoxide_zi~ $__zoxide_zi~

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

edit:add-var z~ $__zoxide_z~
edit:add-var zi~ $__zoxide_zi~

# Load completions.
fn __zoxide_z_complete {|@rest|
    if (!= (builtin:count $rest) 2) {
        builtin:return
    }
    edit:complete-filename $rest[1] |
        builtin:each {|completion|
            var dir = $completion[stem]
            if (path:is-dir $dir) {
                builtin:put $dir
            }
        }
}
set edit:completion:arg-completer[z] = $__zoxide_z_complete~

# =============================================================================
#
# To initialize zoxide, add this to your configuration (usually
# ~/.elvish/rc.elv):
#
#   eval (zoxide init elvish | slurp)
#
# Note: zoxide only supports elvish v0.18.0 and above.
````

### A.14 — `init nushell`

````text
# Code generated by zoxide. DO NOT EDIT.

# =============================================================================
#
# Hook configuration for zoxide.
#

# Initialize hook to add new entries to the database.
export-env {
  $env.config = (
    $env.config?
    | default {}
    | upsert hooks { default {} }
    | upsert hooks.env_change { default {} }
    | upsert hooks.env_change.PWD { default [] }
  )
  let __zoxide_hooked = (
    $env.config.hooks.env_change.PWD | any { try { get __zoxide_hook } catch { false } }
  )
  if not $__zoxide_hooked {
    $env.config.hooks.env_change.PWD = ($env.config.hooks.env_change.PWD | append {
      __zoxide_hook: true,
      code: {|_, dir| ^zoxide add -- $dir}
    })
  }
}

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
def --env --wrapped __zoxide_z [...rest: string] {
  let path = match $rest {
    [] => {'~'},
    [ '-' ] => {'-'},
    [ $arg ] if ($arg | path expand | path type) == 'dir' => {$arg}
    _ => {
      ^zoxide query --exclude $env.PWD -- ...$rest | str trim -r -c "\n"
    }
  }
  cd $path
}

# Jump to a directory using interactive search.
def --env --wrapped __zoxide_zi [...rest:string] {
  cd $'(^zoxide query --interactive -- ...$rest | str trim -r -c "\n")'
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

alias z = __zoxide_z
alias zi = __zoxide_zi

# =============================================================================
#
# Add this to your env file (find it by running `$nu.env-path` in Nushell):
#
#   zoxide init nushell | save -f ~/.zoxide.nu
#
# Now, add this to the end of your config file (find it by running
# `$nu.config-path` in Nushell):
#
#   source ~/.zoxide.nu
#
# Note: zoxide only supports Nushell v0.89.0+.
````

### A.15 — `init posix (and init ksh)`

````text
# shellcheck shell=sh

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
__zoxide_pwd() {
    \command pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
__zoxide_cd() {
    # shellcheck disable=SC2164
    \command cd "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

\command printf "%s\n%s\n" \
    "zoxide: PWD hooks are not supported on POSIX shells." \
    "        Use 'zoxide init posix --hook prompt' instead."

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
__zoxide_z() {
    __zoxide_doctor

    if [ "$#" -eq 0 ]; then
        __zoxide_cd ~
    elif [ "$#" -eq 1 ] && [ "$1" = '-' ]; then
        if [ -n "${OLDPWD}" ]; then
            __zoxide_cd "${OLDPWD}"
        else
            # shellcheck disable=SC2016
            \command printf 'zoxide: $OLDPWD is not set'
            return 1
        fi
    elif [ "$#" -eq 1 ] && [ -d "$1" ]; then
        __zoxide_cd "$1"
    else
        __zoxide_result="$(\command zoxide query --exclude "$(__zoxide_pwd || \command true)" -- "$@")" &&
            __zoxide_cd "${__zoxide_result}"
    fi
}

# Jump to a directory using interactive search.
__zoxide_zi() {
    __zoxide_doctor
    __zoxide_result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${__zoxide_result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

\command unalias z >/dev/null 2>&1 || \true
z() {
    __zoxide_z "$@"
}

\command unalias zi >/dev/null 2>&1 || \true
zi() {
    __zoxide_zi "$@"
}

# =============================================================================
#
# To initialize zoxide, add this to your configuration:
#
# eval "$(zoxide init posix --hook prompt)"
````

### A.16 — `init posix --hook none`

````text
# shellcheck shell=sh

# =============================================================================
#
# Utility functions for zoxide.
#

# pwd based on the value of _ZO_RESOLVE_SYMLINKS.
__zoxide_pwd() {
    \command pwd -L
}

# cd + custom logic based on the value of _ZO_ECHO.
__zoxide_cd() {
    # shellcheck disable=SC2164
    \command cd "$@"
}

# =============================================================================
#
# Hook configuration for zoxide.
#

# -- not configured --

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
__zoxide_z() {
    __zoxide_doctor

    if [ "$#" -eq 0 ]; then
        __zoxide_cd ~
    elif [ "$#" -eq 1 ] && [ "$1" = '-' ]; then
        if [ -n "${OLDPWD}" ]; then
            __zoxide_cd "${OLDPWD}"
        else
            # shellcheck disable=SC2016
            \command printf 'zoxide: $OLDPWD is not set'
            return 1
        fi
    elif [ "$#" -eq 1 ] && [ -d "$1" ]; then
        __zoxide_cd "$1"
    else
        __zoxide_result="$(\command zoxide query --exclude "$(__zoxide_pwd || \command true)" -- "$@")" &&
            __zoxide_cd "${__zoxide_result}"
    fi
}

# Jump to a directory using interactive search.
__zoxide_zi() {
    __zoxide_doctor
    __zoxide_result="$(\command zoxide query --interactive -- "$@")" && __zoxide_cd "${__zoxide_result}"
}

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

\command unalias z >/dev/null 2>&1 || \true
z() {
    __zoxide_z "$@"
}

\command unalias zi >/dev/null 2>&1 || \true
zi() {
    __zoxide_zi "$@"
}

# =============================================================================
#
# To initialize zoxide, add this to your configuration:
#
# eval "$(zoxide init posix --hook prompt)"
````

### A.17 — `init tcsh`

````text
# =============================================================================
#
# Hook configuration for zoxide.
#

# Hook to add new entries to the database.
set __zoxide_pwd_old = `pwd -L`
alias __zoxide_hook 'set __zoxide_pwd_tmp = "`pwd -L`"; test "$__zoxide_pwd_tmp" != "$__zoxide_pwd_old" && zoxide add -- "$__zoxide_pwd_tmp"; set __zoxide_pwd_old = "$__zoxide_pwd_tmp"'

# Initialize hook.
alias precmd ';__zoxide_hook'

# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#

# Jump to a directory using only keywords.
alias __zoxide_z 'set __zoxide_args = (\!*)\
if ("$#__zoxide_args" == 0) then\
    cd ~\
else\
    if ("$#__zoxide_args" == 1 && "$__zoxide_args[1]" == "-") then\
        cd -\
    else if ("$#__zoxide_args" == 1 && -d "$__zoxide_args[1]") then\
        cd "$__zoxide_args[1]"\
    else\
        set __zoxide_pwd = `pwd -L`\
        set __zoxide_result = "`zoxide query --exclude '"'"'$__zoxide_pwd'"'"' -- $__zoxide_args`" && cd "$__zoxide_result"\
    endif\
endif'

# Jump to a directory using interactive search.
alias __zoxide_zi 'set __zoxide_args = (\!*)\
set __zoxide_pwd = `pwd -L`\
set __zoxide_result = "`zoxide query --exclude '"'"'$__zoxide_pwd'"'"' --interactive -- $__zoxide_args`" && cd "$__zoxide_result"'

# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

alias z __zoxide_z
alias zi __zoxide_zi

# =============================================================================
#
# To initialize zoxide, add this to your shell configuration file (usually ~/.tcshrc):
#
#     zoxide init tcsh > ~/.zoxide.tcsh
#     source ~/.zoxide.tcsh
````

### A.18 — `init xonsh`

````text
# pylint: disable=missing-module-docstring

import builtins  # pylint: disable=unused-import
import os
import os.path
import subprocess
import sys
import typing

import xonsh.dirstack  # type: ignore # pylint: disable=import-error
import xonsh.environ  # type: ignore # pylint: disable=import-error

# =============================================================================
#
# Utility functions for zoxide.
#


def __zoxide_bin() -> str:
    """Finds and returns the location of the zoxide binary."""
    zoxide = typing.cast(str, xonsh.environ.locate_binary("zoxide"))
    if zoxide is None:
        zoxide = "zoxide"
    return zoxide


def __zoxide_env() -> dict[str, str]:
    """Returns the current environment."""
    return builtins.__xonsh__.env.detype()  # type: ignore  # pylint:disable=no-member


def __zoxide_pwd() -> str:
    """pwd based on the value of _ZO_RESOLVE_SYMLINKS."""
    pwd = __zoxide_env().get("PWD")
    if pwd is None:
        raise RuntimeError("$PWD not found")
    return pwd


def __zoxide_cd(path: str | bytes | None = None) -> None:
    """cd + custom logic based on the value of _ZO_ECHO."""
    if path is None:
        args = []
    elif isinstance(path, bytes):
        args = [path.decode("utf-8")]
    else:
        args = [path]
    _, exc, _ = xonsh.dirstack.cd(args)
    if exc is not None:
        raise RuntimeError(exc)


class ZoxideSilentException(Exception):
    """Exit without complaining."""


def __zoxide_errhandler(
    func: typing.Callable[[list[str]], None],
) -> typing.Callable[[list[str]], int]:
    """Print exception and exit with error code 1."""

    def wrapper(args: list[str]) -> int:
        try:
            func(args)
            return 0
        except ZoxideSilentException:
            return 1
        except Exception as exc:  # pylint: disable=broad-except
            print(f"zoxide: {exc}", file=sys.stderr)
            return 1

    return wrapper


# =============================================================================
#
# Hook configuration for zoxide.
#

# Initialize hook to add new entries to the database.
if "__zoxide_hook" not in globals():

    @builtins.events.on_chdir  # type: ignore  # pylint:disable=no-member
    def __zoxide_hook(**_kwargs: typing.Any) -> None:
        """Hook to add new entries to the database."""
        pwd = __zoxide_pwd()
        zoxide = __zoxide_bin()
        subprocess.run(
            [zoxide, "add", "--", pwd],
            check=False,
            env=__zoxide_env(),
        )


# =============================================================================
#
# When using zoxide with --no-cmd, alias these internal functions as desired.
#


@__zoxide_errhandler
def __zoxide_z(args: list[str]) -> None:
    """Jump to a directory using only keywords."""
    if args == []:
        __zoxide_cd()
    elif args == ["-"]:
        __zoxide_cd("-")
    elif len(args) == 1 and os.path.isdir(args[0]):
        __zoxide_cd(args[0])
    else:
        try:
            zoxide = __zoxide_bin()
            cmd = subprocess.run(
                [zoxide, "query", "--exclude", __zoxide_pwd(), "--"] + args,
                check=True,
                env=__zoxide_env(),
                stdout=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            raise ZoxideSilentException() from exc

        result = cmd.stdout[:-1]
        __zoxide_cd(result)


@__zoxide_errhandler
def __zoxide_zi(args: list[str]) -> None:
    """Jump to a directory using interactive search."""
    try:
        zoxide = __zoxide_bin()
        cmd = subprocess.run(
            [zoxide, "query", "-i", "--"] + args,
            check=True,
            env=__zoxide_env(),
            stdout=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise ZoxideSilentException() from exc

    result = cmd.stdout[:-1]
    __zoxide_cd(result)


# =============================================================================
#
# Commands for zoxide. Disable these using --no-cmd.
#

builtins.aliases["z"] = __zoxide_z  # type: ignore  # pylint:disable=no-member
builtins.aliases["zi"] = __zoxide_zi  # type: ignore  # pylint:disable=no-member

# =============================================================================
#
# To initialize zoxide, add this to your configuration (usually ~/.xonshrc):
#
# execx($(zoxide init xonsh), 'exec', __xonsh__.ctx, filename='zoxide')
````

## Appendix B — Exact diagnostic fixtures

The following invocations return the status specified in the main text, write nothing to stdout, and write exactly the shown payload to stderr (including final newline).

### B.1 — `executable unknown-cmd`

````text
error: unrecognized subcommand 'unknown-cmd'

Usage: executable <COMMAND>

For more information, try '--help'.
````

### B.2 — `executable --invalid-flag`

````text
error: unexpected argument '--invalid-flag' found

Usage: executable <COMMAND>

For more information, try '--help'.
````

### B.3 — `executable add`

````text
error: the following required arguments were not provided:
  <PATHS>...

Usage: executable add <PATHS>...

For more information, try '--help'.
````

### B.4 — `executable add --invalid-flag /tmp`

````text
error: unexpected argument '--invalid-flag' found

  tip: to pass '--invalid-flag' as a value, use '-- --invalid-flag'

Usage: executable add [OPTIONS] <PATHS>...

For more information, try '--help'.
````

### B.5 — `executable add --score notanumber /tmp`

````text
error: invalid value 'notanumber' for '--score <SCORE>': invalid float literal

For more information, try '--help'.
````

### B.6 — `executable query --interactive --list`

````text
error: the argument '--interactive' cannot be used with '--list'

Usage: executable query --interactive [KEYWORDS]...

For more information, try '--help'.
````

### B.7 — `executable import`

````text
error: the following required arguments were not provided:
  --from <FROM>
  <PATH>

Usage: executable import --from <FROM> <PATH>

For more information, try '--help'.
````

### B.8 — `executable import /tmp/file.txt`

````text
error: the following required arguments were not provided:
  --from <FROM>

Usage: executable import --from <FROM> <PATH>

For more information, try '--help'.
````

### B.9 — `executable import --from invalid /tmp/file.txt`

````text
error: invalid value 'invalid' for '--from <FROM>'
  [possible values: autojump, z]

For more information, try '--help'.
````

### B.10 — `executable init`

````text
error: the following required arguments were not provided:
  <SHELL>

Usage: executable init <SHELL>

For more information, try '--help'.
````

### B.11 — `executable init invalidshell`

````text
error: invalid value 'invalidshell' for '<SHELL>'
  [possible values: bash, elvish, fish, nushell, posix, powershell, tcsh, xonsh, zsh]

For more information, try '--help'.
````

### B.12 — `executable init bash --hook invalid`

````text
error: invalid value 'invalid' for '--hook <HOOK>'
  [possible values: none, prompt, pwd]

For more information, try '--help'.
````

### B.13 — `executable query --unknown-flag`

````text
error: unexpected argument '--unknown-flag' found

  tip: to pass '--unknown-flag' as a value, use '-- --unknown-flag'

Usage: executable query [OPTIONS] [KEYWORDS]...

For more information, try '--help'.
````

### B.14 — `executable remove --unknown-flag`

````text
error: unexpected argument '--unknown-flag' found

  tip: to pass '--unknown-flag' as a value, use '-- --unknown-flag'

Usage: executable remove [PATHS]...

For more information, try '--help'.
````

### B.15 — `executable init bash --unknown-flag`

````text
error: unexpected argument '--unknown-flag' found

  tip: to pass '--unknown-flag' as a value, use '-- --unknown-flag'

Usage: executable init <SHELL>

For more information, try '--help'.
````

### B.16 — `executable edit --unknown-flag`

````text
error: unexpected argument '--unknown-flag' found

Usage: executable edit

For more information, try '--help'.
````

### B.17 — duplicate `--from`

````text
error: the argument '--from <FROM>' cannot be used multiple times

Usage: executable import [OPTIONS] --from <FROM> <PATH>

For more information, try '--help'.
````

### B.18 — `executable Add`

````text
error: unrecognized subcommand 'Add'

  tip: a similar subcommand exists: 'add'

Usage: executable <COMMAND>

For more information, try '--help'.
````

### B.19 — `executable QUERY`

````text
error: unrecognized subcommand 'QUERY'

Usage: executable <COMMAND>

For more information, try '--help'.
````

### B.20 — duplicate `--score`

````text
error: the argument '--score <SCORE>' cannot be used multiple times

Usage: executable add [OPTIONS] <PATHS>...

For more information, try '--help'.
````

### B.21 — `executable add ""`

````text
error: a value is required for '<PATHS>...' but none was supplied

For more information, try '--help'.
````

### B.22 — `executable edit` when fzf is absent

````text
zoxide: could not find fzf, is it installed?
````

## Appendix C — Exact runtime-error fixtures

For these concrete inputs, stderr is exactly the following (a trailing newline is required):

### C.1 — relative `_ZO_DATA_DIR`

````text
zoxide: _ZO_DATA_DIR must be an absolute path
````

### C.2 — `add` with invalid `_ZO_MAXAGE=not_a_number`

````text
zoxide: unable to parse _ZO_MAXAGE as integer: not_a_number

Caused by:
    invalid digit found in string
````

### C.3 — `add` with invalid `_ZO_MAXAGE=12.5`

````text
zoxide: unable to parse _ZO_MAXAGE as integer: 12.5

Caused by:
    invalid digit found in string
````

### C.4 — invalid exclusion glob `/tmp/[`

````text
zoxide: invalid glob in _ZO_EXCLUDE_DIRS: /tmp/[

Caused by:
    Pattern syntax error near position 5: invalid range pattern
````

### C.5 — an unmatched query

````text
zoxide: no match found
````

### C.6 — removing `/nonexistent/path`

````text
zoxide: path not found in database: /nonexistent/path
````

### C.7 — autojump rank `invalid_rank`

````text
zoxide: import error

Caused by:
    0: invalid rank: invalid_rank
    1: invalid float literal
````

### C.8 — autojump record with no tab

````text
zoxide: import error

Caused by:
    invalid entry: 10.0 /home/user/no_tab_separator
````

### C.9 — z rank `invalid`

````text
zoxide: import error

Caused by:
    0: invalid rank: invalid
    1: invalid float literal
````

### C.10 — z epoch `not_a_number`

````text
zoxide: import error

Caused by:
    0: invalid epoch: not_a_number
    1: invalid digit found in string
````

### C.11 — import into a nonempty database without `--merge`

````text
zoxide: current database is not empty, specify --merge to continue anyway
````

### C.12 — opening `/nonexistent/file.txt` for import

````text
zoxide: could not open database for importing: /nonexistent/file.txt

Caused by:
    No such file or directory (os error 2)
````

### C.13 — excluding the only query match

````text
zoxide: you are already in the only match
````
