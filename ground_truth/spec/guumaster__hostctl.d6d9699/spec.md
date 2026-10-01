# Clarified specification for `executable`

## Spec 1

The required artifact is one executable file named exactly `executable`. It implements the command-line program `hostctl`, version `dev`, and manages hosts-file entries grouped into named profiles. It must run non-interactively on Linux, read and write arbitrary files selected by the caller, accept UTF-8 input/output, and complete ordinary invocations within five seconds except when a positive or indefinite `--wait` explicitly requires longer. Successful help, version, information, listing, and mutation operations exit 0. Validation, missing-file, and Docker-connection failures exit 1 (any nonzero status is acceptable for an unknown command or flag). Unless a rule below expressly says otherwise, diagnostics, informational messages, success messages, and rendered results go to stdout; stderr remains empty for normal hostctl application errors.

## Spec 2

The hosts file is selected by `--host-file PATH`; this global flag is accepted before or after commands and nested subcommands. If absent on Linux, use `/etc/hosts`: the Linux executable ignores `HOSTCTL_FILE`, even when it is nonempty. A command that needs to read a nonexistent hosts file fails rather than implicitly inventing its content. Relative and absolute paths and symlinks are supported.

For a non-default selected path, ordinary non-quiet, non-JSON commands begin stdout with exactly `[ℹ] Using hosts file: PATH`, followed by a blank line. `--quiet`/`-q` and `--out json` suppress this line. A CLI `--host-file` selects its path regardless of `HOSTCTL_FILE`. Opening failures use `[✖] error: open PATH: no such file or directory`; the path-selection info line precedes this when applicable. Argument validation (for example, a missing profile) occurs before opening the hosts file.

## Spec 3

Parse a hosts file as an ordered collection of routes and managed profiles. A route line is an IP token followed by one or more whitespace-separated host tokens. Accept valid IPv4 and IPv6 textual addresses, arbitrary spacing/tabs, CRLF or LF, a missing final newline, long lines, and Unicode host tokens. Inside managed profiles, expand multiple hosts on one line into separate `(IP, host)` routes. Outside managed profiles, retain only the first host token: for example, `127.0.0.1 a b` lists only `a`, and `::1 localhost ip6-localhost ip6-loopback` lists only `localhost`. Ignore blank lines, general comments, IP-only or host-only lines, and lines whose first token is not a valid IP. Strip from the first `#` that follows the address/hostname data even when it is attached to a hostname, so `1.2.3.5 name#part` produces host `name`. A line of the form `# IP host...` is parsed as route data, which is how disabled routes are represented; outside a managed profile it likewise retains only its first host.

Canonicalize parsed IP addresses for route data and rendered results. In particular, use compressed lowercase IPv6 spelling with leading zeroes removed: `2001:0db8:85a3::8a2e:0370:7334` renders as `2001:db8:85a3::8a2e:370:7334`, `2001:db8:85a3:0:0:8a2e:370:7335` as `2001:db8:85a3::8a2e:370:7335`, and `fe80:0:0:0:0:0:0:1` as `fe80::1`.

Outside a recognized managed block, valid routes belong to the synthetic profile `default`. Status is retained per route rather than fixed for that profile: an uncommented route has status `on`, while a route parsed from `# IP host...` has status `off`. Consequently one listing can contain both `on` and `off` rows for `default`. When a mutation rewrites the file, retain unmanaged comments, blank lines, route order, Unicode in retained tokens, and non-comment text that is not a valid route. This retained unmanaged content is not limited to content preceding the first managed profile or banner: non-route text found after the banner or between managed blocks is moved into the unmanaged prefix before the canonical banner. Such a line is ignored as route data but is not discarded from the rewritten file. Do not preserve default-route lines byte for byte. Re-serialize each parsed default route as canonical `IP HOST` with a single space and only the first host token, consistently with the parsing rule above. For example, mutating a file containing `127.0.0.1\tlocal café` rewrites that line as `127.0.0.1 local`; the tab and second host token are discarded. Comments occurring only among managed blocks need not be retained.

## Spec 4

A managed block starts with `# profile.on NAME` or `# profile.off NAME`. The `profile` and state tokens are lowercase and case-sensitive. A recognized name requires at least one character and consists of ASCII lowercase letters, digits, hyphen, underscore, dot, and spaces; trim trailing spaces. Names can be long, numeric, contain spaces, or equal command words, but an empty marker such as `# profile.off ` is not recognized and does not appear in status. Marker matching is not anchored after the valid name prefix: a non-ASCII suffix is discarded, so `# profile.on café` creates the managed profile `caf`. An uppercase marker such as `# Profile.on upper` is not recognized, and its subsequent valid routes are default routes. The terminator is `# end`, case-insensitively (`# END` and `# End` work). EOF or another profile header also ends an unterminated block.

Within each profile, preserve route order but deduplicate an identical `(IP, host)` pair; the same host on different IPs remains distinct. Preserve the order in which profiles occur. Named profiles with zero routes are valid and appear in status, though naturally produce no list rows.

Duplicate profile names are accepted. Keep every occurrence in the profile-order sequence, but store profile contents and status by name, so the last block with that name replaces the earlier block's definition. Every retained occurrence then renders using that last definition. For example, given an enabled `dup` block containing `1.1.1.1 only-first`, then an enabled `middle` block, then a disabled `dup` block containing `3.3.3.3 only-second`, status JSON contains `dup`, `middle`, `dup`, both `dup` entries are `off`, and list JSON emits `3.3.3.3 only-second` at both `dup` positions; `only-first` is absent.

## Spec 5

Every successful mutation that parses and flushes a hosts file rewrites its managed area canonically. Keep unmanaged comments, blank lines, and the parsed default routes, re-serializing default route lines as specified in Spec 3; ensure one blank line, then ensure exactly this banner:

```text
##################################################################
# Content under this line is handled by hostctl. DO NOT EDIT.
##################################################################
```

When at least one managed profile remains, write a blank line after the banner and then profiles in their existing order, with newly created profiles appended. When no managed profiles remain, end the file immediately after the banner's final newline; do not append a blank line. Each block is `# profile.on NAME` or `# profile.off NAME`, then one line per route, then `# end`; separate blocks by one blank line. Enabled route lines are `IP HOST`. Disabled route lines are `# IP HOST`. Normalize source lines containing multiple hosts into one output line per host. End the file with a newline. Do not duplicate an existing banner. A mutation can add the banner to a file whose profile markers previously existed without it. Enabling/disabling, adding/removing routes, and removing profiles must not reorder unaffected profiles or corrupt default content.

## Spec 6

With no arguments, `help`, `--help`, or `-h`, exit 0 and print the same main help. It begins with a blank line, contains no ANSI escapes, and is exactly:

```text

hostctl is a CLI tool to manage your hosts file with ease.
You can have multiple profiles, enable/disable exactly what
you need each time with a simple interface.

Usage:
  hostctl [command]

Available Commands:
  add         Add content to a profile in your hosts file.
  backup      Creates a backup copy of your hosts file
  disable     Disable a profile from your hosts file.
  enable      Enable a profile on your hosts file.
  help        Help about any command
  list        Shows a detailed list of profiles on your hosts file.
  remove      Remove a profile from your hosts file.
  replace     Replace content to a profile in your hosts file.
  restore     Restore hosts file content from a backup file.
  status      Shows a list of profile names and statuses on your hosts file.
  sync        Sync some system IPs with a profile.
  toggle      Change status of a profile on your hosts file.

Flags:
  -c, --column strings     Column names to show on lists. comma separated
  -h, --help               help for hostctl
      --host-file string   Hosts file path (default "/etc/hosts")
      --no-color           force colorless output
  -o, --out string         Output type (table|raw|markdown|json) (default "table")
  -q, --quiet              Run command without output
      --raw                Output without borders (same as -o raw)
  -v, --version            version for hostctl

Use "hostctl [command] --help" for more information about a command.
```

`--version` and `-v` print exactly `hostctl version dev\n`. The hidden but callable `info` command prints exactly:

```text

        __                       __             __     __
       / /_    ____     _____   / /_   _____   / /_   / /
      / __ \  / __ \   / ___/  / __/  / ___/  / __/  / /
     / / / / / /_/ /  (__  )  / /_   / /__   / /_   / /
    /_/ /_/  \____/  /____/   \__/   \___/   \__/  /_/  Version: dev

     Your dev tool to manage /etc/hosts like a pro
```

## Spec 7

Every visible command supports `--help`; `help COMMAND` is equivalent. Command help has a `Usage:` section, command-specific flags, and a `Global Flags:` section documenting the global flags from Spec 6. In particular, `add` uses `hostctl add [profiles] [flags]`, documents `-f, --from` and `-w, --wait`, and has the exact `Available Commands:` line `  domains     Add content in your hosts file.` (five spaces between `domains` and `Add`). The top-level commands are add, backup, disable, enable, list, remove, replace, restore, status, sync, and toggle. `rm` is not routed and must report an unknown command, even if some generated metadata describes it as an alias. Hidden callable commands are info and completion. Nested commands are `add domains`, `remove domains`, `list enabled` (alias `on`), `list disabled` (alias `off`), `sync docker`, and `sync docker-compose`. The singular tokens in `add domain --help` and `remove domain --help` are treated as ordinary profile arguments, so those invocations show the respective parent command help rather than nested-domain help. Their help must be distinct and routable. The two sync help pages use `[profile]` and document the flags in Spec 19; sync parent help lists exactly the lines `  docker         Sync your Docker containers IPs with a profile.` and `  docker-compose Sync your docker-compose containers IPs with a profile.`.

Unknown commands/flags fail and mention `unknown command "TOKEN"` or `unknown flag: FLAG`, respectively. Missing values mention `flag needs an argument`. Missing profile validation prints `[✖] error: missing profile name`. Help does not bypass unknown-flag validation. In particular, `enable --help --bad-flag extra` exits 1, writes exactly `[✖] error: unknown flag: --bad-flag\n` to stdout, writes nothing to stderr, and does not show command help.

## Spec 8

Global output flags are accepted both before and after a subcommand. `-o VALUE`, `--out VALUE`, `-o=VALUE`, and `--out=VALUE` select `table`, `raw`, `markdown`, or `json`. `--raw` selects raw and takes precedence if it is combined with `--out`. `-c`/`--column` accepts a comma-separated value, may be repeated, and selects columns in the supplied order for `list`; `status` ignores it as described in Spec 10. `--no-color` guarantees no ANSI escape bytes. This implementation may color table output otherwise, but color must never alter textual data. JSON is always colorless and suppresses the hosts-file info prefix. It does not suppress every success message: the add-domains prefix is described in Spec 12, and whole-profile removal is described in Spec 14. `-q` suppresses informational/success chatter; for mutation commands it suppresses substantive output, subject to the single-newline wait behavior in Spec 16, while for `list` and `status` it retains the requested data rendering.

Compatibility corner cases: an unrecognized list or status output value succeeds and falls back to table. An empty status rendered as JSON is `null\n`; empty table/raw/markdown status has no data output. For a non-default selected file with no managed profiles, `status --raw` and `status -o raw --raw` emit only `[ℹ] Using hosts file: PATH\n\n`. `status -o json --raw` is completely silent because `--raw` chooses the empty raw renderer while `-o json` suppresses the info prefix. `status -oq` parses as `-o q`, not as quiet mode; because `q` is an unrecognized output value, a populated file produces the normal hosts-file info prefix followed by the complete status table. `--help --version` may show either help or version. A duration is Go-style: integer/decimal sequences with units such as `ms`, `s`, `m`, or `h`; invalid units fail with text like `invalid argument "5x" for "-w, --wait": time: unknown unit "x" in duration "5x"`.

## Spec 9

`list [profiles...]` renders route rows. With no filters it includes default routes first, then every managed profile and route in file order. Explicit names act as a membership filter but do not impose argument order: selected results remain in file order, with default first when selected, and unknown names are silently omitted. Thus requesting `second missing default first` from a file ordered as default, first, second renders default, first, second. Explicit `default` selects default rows. `list enabled`/`list on` includes all default rows, retaining each row's `on` or `off` status, plus only enabled managed profiles. `list disabled`/`list off` likewise includes all default rows, then only disabled managed profiles. A profile named `enabled`, `disabled`, `on`, or `off` is shadowed by these nested selectors when used in that position.

Default list columns are `PROFILE`, `STATUS`, `IP`, `DOMAIN`. Valid column names are `profile`, `status`, `ip`, and `domain`; plural aliases `ips` and `domains` select the same data but use headers `IPS` and `DOMAINS`. Column filtering changes only the shown fields, not row order. An unknown requested column is accepted rather than rejected or omitted: non-JSON renderers retain it in the supplied position and use the uppercased requested name as its header. For a hosts file containing `1.1.1.1 x\n`, `list -q -c profile,not-a-column,domain --raw` exits 0 and writes exactly `PROFILE\tNOT-A-COLUMN\tDOMAIN \ndefault\tx           \t\n`; stderr is empty. JSON retains its fixed schema from Spec 11 rather than exposing display-column headers. With no selected rows, non-JSON list output is empty after any info line; JSON uses `null` when the underlying result is nil and may use `[]` for an explicitly empty filtered result.

## Spec 10

`status [profiles...]` renders one row per managed profile, never the synthetic default. With or without names, use managed file order; supplied names are only a membership filter, and missing names and `default` are silently omitted. For example, requesting `second missing first default` from a file ordered first, second renders first, then second. Status always uses only the fixed `PROFILE` and `STATUS` display columns and ignores `-c`/`--column`, including requested route fields and requested column order. Empty status JSON is `null`. JSON status objects nevertheless use the four-field schema and set IP and Host to empty strings.

Statuses are the literal lowercase strings `on` and `off`. Listing a disabled profile shows its routes without the comment prefix and with status `off`.

## Spec 11

All result renderers preserve row and group order, begin immediately at the first rendered character without adding a leading newline, and end nonempty output with `\n`:

- JSON is compact JSON with no spaces: an array of objects whose key order is exactly `Profile`, `Status`, `IP`, `Host`; list rows contain actual values and status rows contain `"IP":"","Host":""`.
- Table output starts with its top `+` border. For each selected column, width is the maximum printable width of its uppercase header and all cells. A border is `+` plus `width+2` hyphens per column; headers are centered with one outer space, cells are left-aligned with one outer space. If centering leaves one indivisible padding space, put it on the right: the non-outer padding is `floor((width-header_length)/2)` on the left and `ceil((width-header_length)/2)` on the right. Print the border before/after the header and after the last row. In `list`-style route output, also print it when the profile changes; in `status` output, keep the one-row-per-profile records contiguous without intermediate borders.
- Markdown starts with its `|` header row and uses the same widths, header-centering bias, padding, and `|` cell boundaries. Its header rule and list profile-group rules contain only hyphens between the pipes, with no spaces, such as `|---------|--------|`. Status rows are contiguous. Markdown has no outer `+` border or final hyphen row.
- Raw starts with the uppercase header. Each header is right-padded to the same computed column width as its data cells. Non-final padded header fields are followed by tabs; the final padded header field has one additional trailing space before its newline rather than a trailing tab. Thus, when the final `IP` column has the value `1.1.1.1`, that header ends as `IP      \n`: five spaces pad `IP` to width seven and the sixth is the final separator. Data cells are right-padded to the column width and separated by tabs, and every data row retains a trailing tab. Raw has no `+`, `|`, or group separators. For `-c profile,status`, the exact output is `PROFILE\tSTATUS \np      \ton    \t\n`.

For example, table status for two rows is structurally:

```text
+---------+--------+
| PROFILE | STATUS |
+---------+--------+
| first   | on     |
| second  | off    |
+---------+--------+
```

## Spec 12

`add domains PROFILE DOMAIN... [--ip IP]` appends routes to PROFILE, creating it enabled at the end when absent. Default IP is `127.0.0.1`. The domain list may contain zero, one, or multiple values. Thus `add domains p` succeeds with exit 0, creates an empty enabled `p` profile when absent, and reports `[✔] Domains '' added.`. Accept IPv6, arbitrary domain strings (including wildcard, port, underscores, Unicode, and long values), an empty profile argument, and multiple domains. An empty profile argument is written as a `# profile.on ` block, but that empty marker is not recognized when the post-action listing reparses the file, so JSON output lists it as `null` rather than as an object with an empty `Profile`. Deduplicate identical `(IP, domain)` pairs but retain equal domains on different IPs. An invalid direct `--ip` is not rejected: serialize it as `<nil>` while retaining the domains. `default` is reserved and fails with `[✖] error: 'default' profile should not be handled by hostctl`.

Without quiet mode, print `[✔] Domains 'd1, d2' added.`, a blank line, then list the affected profile in the selected JSON/raw/markdown/table format. JSON does not suppress this command's success line. For example, `add domains new one.test two.test -o json` emits the success line, a blank line, the compact JSON array, and then one additional blank line; equivalently its suffix is `added.\n\n[{...}]\n\n`. For the empty profile case, the corresponding rendered portion is `null\n\n`. Quiet suppresses all of this output. Adding to a disabled profile preserves its `off` status and writes its new routes commented.

## Spec 13

`add PROFILE [--from SOURCE]` merges standard-input routes into one destination profile; `replace PROFILE [--from SOURCE]` discards that profile's old routes and installs the standard-input routes. Each accepts exactly one destination profile, creates it enabled if absent, and rejects `default`. Replace of a disabled profile makes it enabled. Add preserves the status of an existing profile. Replace preserves every other profile and their relative order, but removes an existing destination from its old position and appends its enabled replacement at the end. For example, replacing `target` in the order `first`, `target`, `last` produces `first`, `last`, `target`. Repeated operations are deterministic and deduplicate exact routes. Replace does not accept `--wait`.

For add and replace, `-f`/`--from` is accepted but its value does not select the input: these commands always read stdin. This remains true when SOURCE is `-`, a readable local pathname, an HTTP(S) URL, or a nonexistent/path-like string. Piped stdin is therefore imported even when a different `--from` value is present. Immediate EOF is treated as a successful empty source rather than an error: exit 0 and create an empty enabled destination profile when it was absent; replace discards an existing destination's routes and leaves that profile empty and enabled. With EOF and no destination routes, parent `add ... -o json` emits exactly `null\n\n`; ordinary table-mode replace emits no data table for the empty destination, only any applicable hosts-file information prefix. Parse stdin as the route and profile syntax described in Spec 3, but use a distinct host-expansion rule for this import: expand every host token on every valid route line, whether that line occurs outside or inside an input managed block. Flatten those expanded routes from all default/managed input sections into the named destination. Thus an outside/default input line `1.1.1.1 a b` imports both `(1.1.1.1, a)` and `(1.1.1.1, b)`, unlike ordinary hosts-file parsing in Spec 3. Ignore ordinary comments and malformed/IP-only/host-only lines; accept commented route lines. Add/replace normally prints the resulting destination profile listing but no `Domains ...` success sentence. Quiet suppresses it; JSON emits only the compact result.

## Spec 14

`remove PROFILE...` removes one or more entire managed profiles. `remove --all` removes every managed profile but preserves default content and the canonical banner. It requires either names or `--all`; combining names with `--all` fails with `args must be empty with --all flag`. Unknown names fail atomically with `unknown profile name`, and `default` fails with the reserved-profile error. Success prints `[✔] Profile(s) 'p1, p2' removed.` unless quiet suppresses it. JSON does not suppress this success chatter and does not add a JSON result: for example, a successful `remove c -o=json` writes exactly `[✔] Profile(s) 'c' removed.\n\n\n` and nothing to stderr, including when `c` was the final managed profile.

`remove domains PROFILE DOMAIN...` removes exact hostname matches from every IP route in that one profile. It requires a profile but permits zero domains; unknown profile fails, and zero or nonexistent domains are a successful no-op on the route set. Preserve unremoved hosts, their IPs, profile state, and order. If no routes remain, delete the profile and report `[✔] Profile 'PROFILE' removed.`; specifically, applying `remove domains p` to an already-empty `p` reports `[✔] Profile 'p' removed.`. Otherwise report `[✔] Domains 'd1, d2' removed.` and render the remaining affected profile.

## Spec 15

`enable PROFILE...`, `disable PROFILE...`, and `toggle PROFILE...` modify state and then render the affected profile route rows. Enable changes headers to `profile.on` and uncomments routes; disable changes to `profile.off` and comments each route; toggle flips each selected profile. Already-correct enable/disable is successful and idempotent. Multiple supplied names form a membership selection: after atomic validation, selected profiles are mutated and rendered in existing file order, not argument order. Thus enabling `b a` in a file ordered `a`, `b` renders `a` before `b`. Without `--only`, a missing or unknown name fails and a list containing any unknown name causes no partial mutation. `default` cannot be enabled, disabled, or toggled.

Enable and disable accept `--all`, which applies to all managed profiles and rejects explicit names. They also accept `--only`: `enable --only NAMES` enables the existing named profiles and disables every other managed profile; `disable --only NAMES` disables the existing named profiles and enables every other managed profile. In `--only` mode, unknown names are ignored rather than rejected. For example, on profiles `web`, `database`, and `cache`, `disable --only web nonexistent --quiet` exits 0, makes `web` off, and makes `database` and `cache` on. Toggle accepts multiple names but not `--all`/`--only`. Quiet mutation mode emits no stdout when no positive or interrupted zero-duration wait is involved; wait output is specified in Spec 16.

## Spec 16

`-w DURATION`/`--wait DURATION` is supported by add, enable, disable, and toggle. Perform and flush the initial action, show its normal listing, then for a positive duration print `[ℹ] Waiting for DURATION or ctrl+c to ACTION from profile 'NAMES'`, wait approximately the requested real elapsed time, perform the inverse, flush, and show the final result. ACTION is `remove` after parent add, `remove domains` after `add domains`, `disable` after enable, `enable` after disable, and `toggle` after toggle. Ordinarily join multiple profile names with comma-space. For `add domains`, however, NAMES contains every positional argument—profile followed by domains—joined with comma-space: `add domains temporary x -w 100ms` prints `[ℹ] Waiting for 100ms or ctrl+c to remove domains from profile 'temporary, x'`. For an `--all` state action the displayed name is empty. Both add variants ultimately delete the entire newly added profile as their inverse.

Enable/disable wait inverses invoke the complementary state command with the same selection flags. Consequently, an `--only` inverse also reapplies `--only` behavior to unselected profiles; it does not limit rollback to the named profiles. Starting with `a` and `b` both off, `enable --only a -w 50ms` initially makes `a` on and leaves `b` off, then its `disable --only a` inverse finishes with `a` off and `b` on.

A duration of zero means wait indefinitely until interrupted and says `Waiting until ctrl+c to ...`; on termination it performs the inverse and renders the final state. A negative duration performs only the initial action, with no waiting message or inverse. Quiet mode still waits and mutates and suppresses the normal action, listing, and waiting text, but successful wait completion emits a newline. A quiet positive-duration wait exits 0 with stdout exactly `\n` and empty stderr after performing its inverse; for example, on a file containing disabled profile `p`, `enable --all --wait 1000ms -q` waits approximately one second, restores `p` to `off`, and produces that one byte. The zero-duration interruption path behaves the same after receiving the interrupt and performing the inverse: stdout is exactly `\n` and stderr is empty. A quiet negative-duration invocation has no wait completion and remains silent. Invalid/unknown profiles fail immediately before waiting. Millisecond timing must be honored (500ms completes in roughly 0.45–0.8 seconds; N-second waits complete within about 0.1 seconds below to 0.5 seconds above N). Positive durations in the message use Go's normalized duration string rather than preserving the input spelling: `--wait 1h` prints `Waiting for 1h0m0s or ctrl+c to disable from profile 'p'`.

Separate info/listing blocks with blank lines as demonstrated by: initial table, blank line, wait message, exactly four newline characters, then the final table or removal success. For JSON state output, the boundary is `profile 'p'\n\n\n\n[{`.

## Spec 17

`backup [--path DIRECTORY]` byte-for-byte copies the selected hosts file to `DIRECTORY/BASENAME.YYYYMMDD`, where the date is the current local calendar date and omitted DIRECTORY means the current working directory. Do not create missing directories. If the directory is missing, the OS-style diagnostic names the full dated destination, for example `[✖] error: open /nonexistent/deeply/nested/path/backup-source.hosts.20260917: no such file or directory`, rather than naming only the directory. A second backup on the same date overwrites that one file. Follow symlinks for source content. Preserve arbitrary bytes, UTF-8, line endings, trailing whitespace, and empty/large files. A newly created backup uses normal file-creation permissions rather than copying source mode: under the evaluated `022` umask, a `0640` source produced a `0644` backup. Success stdout includes `[✔] Backup 'FULL_DESTINATION' created.` after the optional hosts-file info line.

`restore --from FILE` requires both an existing source and an already-existing selected target. It replaces target bytes exactly (including with an empty file), supports paths in other directories, and preserves/restores usable permissions. It must not create a missing target. Success includes `[✔] File 'FILE' restored.`. Missing `--from` behaves as opening the empty path and reports `open : no such file or directory`. Quiet backup/restore performs the copy with completely empty stdout. Errors do not alter the target.

## Spec 18

For add/replace, `-f`/`--from` does not inspect or classify its value. It neither opens a local path nor performs an HTTP request; input always comes from stdin as specified in Spec 13. Thus readable files and reachable HTTP URLs contribute no content when stdin is at EOF. Nonexistent/path-like values such as `example.com/hosts.txt`, `http:///path`, and `has spaces` likewise do not produce an open or network error: the operation succeeds using empty stdin. In particular, add creates an empty enabled destination, while replace removes the destination's old routes and leaves an empty enabled replacement.

## Spec 19

`sync docker PROFILE` accepts `--domain VALUE` and `--network VALUE`. `sync docker-compose PROFILE` accepts those plus `--compose-file FILE` (default `docker-compose.yml`), `--project-name VALUE`, and boolean `--prefix`. Exactly one non-default profile is required. Domain, project, and network values containing hyphens, digits, underscores, and dots parse without validation errors. Unknown flags fail normally.

In the evaluated environment Docker is unavailable. After argument validation, `sync docker` fails promptly with exactly the essential diagnostic `[✖] error: Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?`. Docker connection occurs before opening the selected hosts file. Docker-compose validates an explicitly missing compose path first and reports `open PATH: no such file or directory`; an omitted missing default mentions `docker-compose.yml`. Existing compose files—including empty, syntactically odd, mixed explicit/implicit container names, or no explicit container names—proceed to the same Docker connection diagnostic. Quiet does not hide errors; `--no-color` produces no escapes.

## Spec 20

`completion bash` and `completion zsh` are hidden callable commands that write fixed, deterministic shell scripts to stdout, write nothing to stderr, and exit 0. Extra positional arguments and global `--quiet`/`--no-color` do not alter these bytes. The bash script is valid under `bash -n`, starts `# bash completion for hostctl`, has more than 1000 lines, defines the hostctl command and nested-command functions (including `_hostctl_root_command`, `_hostctl_help`, `_hostctl_add_domains`, `_hostctl_remove_domains`, `_hostctl_list_enabled`, `_hostctl_list_disabled`, `_hostctl_sync_docker`, and `_hostctl_sync_docker-compose`), includes `__hostctl_debug`, `BASH_COMP_DEBUG_FILE`, `__hostctl_handle_flag`, `local_nonpersistent_flags=`, `must_have_one_flag=`, and ends by registering `_hostctl` for `hostctl`. The zsh script has 212 lines, begins with `#compdef hostctl`, puts `compdef _hostctl hostctl` on its second line, and defines `_hostctl()` and `__hostctl_debug()`. It ends with the conditional lines `if [ "$funcstack[1]" = "_hostctl" ]; then`, `    _hostctl`, and `fi`, followed by a final newline.

The byte-exact required bash output follows:

```bash
# bash completion for hostctl                              -*- shell-script -*-

__hostctl_debug()
{
    if [[ -n ${BASH_COMP_DEBUG_FILE:-} ]]; then
        echo "$*" >> "${BASH_COMP_DEBUG_FILE}"
    fi
}

# Homebrew on Macs have version 1.3 of bash-completion which doesn't include
# _init_completion. This is a very minimal version of that function.
__hostctl_init_completion()
{
    COMPREPLY=()
    _get_comp_words_by_ref "$@" cur prev words cword
}

__hostctl_index_of_word()
{
    local w word=$1
    shift
    index=0
    for w in "$@"; do
        [[ $w = "$word" ]] && return
        index=$((index+1))
    done
    index=-1
}

__hostctl_contains_word()
{
    local w word=$1; shift
    for w in "$@"; do
        [[ $w = "$word" ]] && return
    done
    return 1
}

__hostctl_handle_go_custom_completion()
{
    __hostctl_debug "${FUNCNAME[0]}: cur is ${cur}, words[*] is ${words[*]}, #words[@] is ${#words[@]}"

    local shellCompDirectiveError=1
    local shellCompDirectiveNoSpace=2
    local shellCompDirectiveNoFileComp=4
    local shellCompDirectiveFilterFileExt=8
    local shellCompDirectiveFilterDirs=16

    local out requestComp lastParam lastChar comp directive args

    # Prepare the command to request completions for the program.
    # Calling ${words[0]} instead of directly hostctl allows to handle aliases
    args=("${words[@]:1}")
    # Disable ActiveHelp which is not supported for bash completion v1
    requestComp="HOSTCTL_ACTIVE_HELP=0 ${words[0]} __completeNoDesc ${args[*]}"

    lastParam=${words[$((${#words[@]}-1))]}
    lastChar=${lastParam:$((${#lastParam}-1)):1}
    __hostctl_debug "${FUNCNAME[0]}: lastParam ${lastParam}, lastChar ${lastChar}"

    if [ -z "${cur}" ] && [ "${lastChar}" != "=" ]; then
        # If the last parameter is complete (there is a space following it)
        # We add an extra empty parameter so we can indicate this to the go method.
        __hostctl_debug "${FUNCNAME[0]}: Adding extra empty parameter"
        requestComp="${requestComp} \"\""
    fi

    __hostctl_debug "${FUNCNAME[0]}: calling ${requestComp}"
    # Use eval to handle any environment variables and such
    out=$(eval "${requestComp}" 2>/dev/null)

    # Extract the directive integer at the very end of the output following a colon (:)
    directive=${out##*:}
    # Remove the directive
    out=${out%:*}
    if [ "${directive}" = "${out}" ]; then
        # There is not directive specified
        directive=0
    fi
    __hostctl_debug "${FUNCNAME[0]}: the completion directive is: ${directive}"
    __hostctl_debug "${FUNCNAME[0]}: the completions are: ${out}"

    if [ $((directive & shellCompDirectiveError)) -ne 0 ]; then
        # Error code.  No completion.
        __hostctl_debug "${FUNCNAME[0]}: received error from custom completion go code"
        return
    else
        if [ $((directive & shellCompDirectiveNoSpace)) -ne 0 ]; then
            if [[ $(type -t compopt) = "builtin" ]]; then
                __hostctl_debug "${FUNCNAME[0]}: activating no space"
                compopt -o nospace
            fi
        fi
        if [ $((directive & shellCompDirectiveNoFileComp)) -ne 0 ]; then
            if [[ $(type -t compopt) = "builtin" ]]; then
                __hostctl_debug "${FUNCNAME[0]}: activating no file completion"
                compopt +o default
            fi
        fi
    fi

    if [ $((directive & shellCompDirectiveFilterFileExt)) -ne 0 ]; then
        # File extension filtering
        local fullFilter filter filteringCmd
        # Do not use quotes around the $out variable or else newline
        # characters will be kept.
        for filter in ${out}; do
            fullFilter+="$filter|"
        done

        filteringCmd="_filedir $fullFilter"
        __hostctl_debug "File filtering command: $filteringCmd"
        $filteringCmd
    elif [ $((directive & shellCompDirectiveFilterDirs)) -ne 0 ]; then
        # File completion for directories only
        local subdir
        # Use printf to strip any trailing newline
        subdir=$(printf "%s" "${out}")
        if [ -n "$subdir" ]; then
            __hostctl_debug "Listing directories in $subdir"
            __hostctl_handle_subdirs_in_dir_flag "$subdir"
        else
            __hostctl_debug "Listing directories in ."
            _filedir -d
        fi
    else
        while IFS='' read -r comp; do
            COMPREPLY+=("$comp")
        done < <(compgen -W "${out}" -- "$cur")
    fi
}

__hostctl_handle_reply()
{
    __hostctl_debug "${FUNCNAME[0]}"
    local comp
    case $cur in
        -*)
            if [[ $(type -t compopt) = "builtin" ]]; then
                compopt -o nospace
            fi
            local allflags
            if [ ${#must_have_one_flag[@]} -ne 0 ]; then
                allflags=("${must_have_one_flag[@]}")
            else
                allflags=("${flags[*]} ${two_word_flags[*]}")
            fi
            while IFS='' read -r comp; do
                COMPREPLY+=("$comp")
            done < <(compgen -W "${allflags[*]}" -- "$cur")
            if [[ $(type -t compopt) = "builtin" ]]; then
                [[ "${COMPREPLY[0]}" == *= ]] || compopt +o nospace
            fi

            # complete after --flag=abc
            if [[ $cur == *=* ]]; then
                if [[ $(type -t compopt) = "builtin" ]]; then
                    compopt +o nospace
                fi

                local index flag
                flag="${cur%=*}"
                __hostctl_index_of_word "${flag}" "${flags_with_completion[@]}"
                COMPREPLY=()
                if [[ ${index} -ge 0 ]]; then
                    PREFIX=""
                    cur="${cur#*=}"
                    ${flags_completion[${index}]}
                    if [ -n "${ZSH_VERSION:-}" ]; then
                        # zsh completion needs --flag= prefix
                        eval "COMPREPLY=( \"\${COMPREPLY[@]/#/${flag}=}\" )"
                    fi
                fi
            fi

            if [[ -z "${flag_parsing_disabled}" ]]; then
                # If flag parsing is enabled, we have completed the flags and can return.
                # If flag parsing is disabled, we may not know all (or any) of the flags, so we fallthrough
                # to possibly call handle_go_custom_completion.
                return 0;
            fi
            ;;
    esac

    # check if we are handling a flag with special work handling
    local index
    __hostctl_index_of_word "${prev}" "${flags_with_completion[@]}"
    if [[ ${index} -ge 0 ]]; then
        ${flags_completion[${index}]}
        return
    fi

    # we are parsing a flag and don't have a special handler, no completion
    if [[ ${cur} != "${words[cword]}" ]]; then
        return
    fi

    local completions
    completions=("${commands[@]}")
    if [[ ${#must_have_one_noun[@]} -ne 0 ]]; then
        completions+=("${must_have_one_noun[@]}")
    elif [[ -n "${has_completion_function}" ]]; then
        # if a go completion function is provided, defer to that function
        __hostctl_handle_go_custom_completion
    fi
    if [[ ${#must_have_one_flag[@]} -ne 0 ]]; then
        completions+=("${must_have_one_flag[@]}")
    fi
    while IFS='' read -r comp; do
        COMPREPLY+=("$comp")
    done < <(compgen -W "${completions[*]}" -- "$cur")

    if [[ ${#COMPREPLY[@]} -eq 0 && ${#noun_aliases[@]} -gt 0 && ${#must_have_one_noun[@]} -ne 0 ]]; then
        while IFS='' read -r comp; do
            COMPREPLY+=("$comp")
        done < <(compgen -W "${noun_aliases[*]}" -- "$cur")
    fi

    if [[ ${#COMPREPLY[@]} -eq 0 ]]; then
        if declare -F __hostctl_custom_func >/dev/null; then
            # try command name qualified custom func
            __hostctl_custom_func
        else
            # otherwise fall back to unqualified for compatibility
            declare -F __custom_func >/dev/null && __custom_func
        fi
    fi

    # available in bash-completion >= 2, not always present on macOS
    if declare -F __ltrim_colon_completions >/dev/null; then
        __ltrim_colon_completions "$cur"
    fi

    # If there is only 1 completion and it is a flag with an = it will be completed
    # but we don't want a space after the =
    if [[ "${#COMPREPLY[@]}" -eq "1" ]] && [[ $(type -t compopt) = "builtin" ]] && [[ "${COMPREPLY[0]}" == --*= ]]; then
       compopt -o nospace
    fi
}

# The arguments should be in the form "ext1|ext2|extn"
__hostctl_handle_filename_extension_flag()
{
    local ext="$1"
    _filedir "@(${ext})"
}

__hostctl_handle_subdirs_in_dir_flag()
{
    local dir="$1"
    pushd "${dir}" >/dev/null 2>&1 && _filedir -d && popd >/dev/null 2>&1 || return
}

__hostctl_handle_flag()
{
    __hostctl_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"

    # if a command required a flag, and we found it, unset must_have_one_flag()
    local flagname=${words[c]}
    local flagvalue=""
    # if the word contained an =
    if [[ ${words[c]} == *"="* ]]; then
        flagvalue=${flagname#*=} # take in as flagvalue after the =
        flagname=${flagname%=*} # strip everything after the =
        flagname="${flagname}=" # but put the = back
    fi
    __hostctl_debug "${FUNCNAME[0]}: looking for ${flagname}"
    if __hostctl_contains_word "${flagname}" "${must_have_one_flag[@]}"; then
        must_have_one_flag=()
    fi

    # if you set a flag which only applies to this command, don't show subcommands
    if __hostctl_contains_word "${flagname}" "${local_nonpersistent_flags[@]}"; then
      commands=()
    fi

    # keep flag value with flagname as flaghash
    # flaghash variable is an associative array which is only supported in bash > 3.
    if [[ -z "${BASH_VERSION:-}" || "${BASH_VERSINFO[0]:-}" -gt 3 ]]; then
        if [ -n "${flagvalue}" ] ; then
            flaghash[${flagname}]=${flagvalue}
        elif [ -n "${words[ $((c+1)) ]}" ] ; then
            flaghash[${flagname}]=${words[ $((c+1)) ]}
        else
            flaghash[${flagname}]="true" # pad "true" for bool flag
        fi
    fi

    # skip the argument to a two word flag
    if [[ ${words[c]} != *"="* ]] && __hostctl_contains_word "${words[c]}" "${two_word_flags[@]}"; then
        __hostctl_debug "${FUNCNAME[0]}: found a flag ${words[c]}, skip the next argument"
        c=$((c+1))
        # if we are looking for a flags value, don't show commands
        if [[ $c -eq $cword ]]; then
            commands=()
        fi
    fi

    c=$((c+1))

}

__hostctl_handle_noun()
{
    __hostctl_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"

    if __hostctl_contains_word "${words[c]}" "${must_have_one_noun[@]}"; then
        must_have_one_noun=()
    elif __hostctl_contains_word "${words[c]}" "${noun_aliases[@]}"; then
        must_have_one_noun=()
    fi

    nouns+=("${words[c]}")
    c=$((c+1))
}

__hostctl_handle_command()
{
    __hostctl_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"

    local next_command
    if [[ -n ${last_command} ]]; then
        next_command="_${last_command}_${words[c]//:/__}"
    else
        if [[ $c -eq 0 ]]; then
            next_command="_hostctl_root_command"
        else
            next_command="_${words[c]//:/__}"
        fi
    fi
    c=$((c+1))
    __hostctl_debug "${FUNCNAME[0]}: looking for ${next_command}"
    declare -F "$next_command" >/dev/null && $next_command
}

__hostctl_handle_word()
{
    if [[ $c -ge $cword ]]; then
        __hostctl_handle_reply
        return
    fi
    __hostctl_debug "${FUNCNAME[0]}: c is $c words[c] is ${words[c]}"
    if [[ "${words[c]}" == -* ]]; then
        __hostctl_handle_flag
    elif __hostctl_contains_word "${words[c]}" "${commands[@]}"; then
        __hostctl_handle_command
    elif [[ $c -eq 0 ]]; then
        __hostctl_handle_command
    elif __hostctl_contains_word "${words[c]}" "${command_aliases[@]}"; then
        # aliashash variable is an associative array which is only supported in bash > 3.
        if [[ -z "${BASH_VERSION:-}" || "${BASH_VERSINFO[0]:-}" -gt 3 ]]; then
            words[c]=${aliashash[${words[c]}]}
            __hostctl_handle_command
        else
            __hostctl_handle_noun
        fi
    else
        __hostctl_handle_noun
    fi
    __hostctl_handle_word
}

_hostctl_add_domains()
{
    last_command="hostctl_add_domains"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--ip=")
    two_word_flags+=("--ip")
    local_nonpersistent_flags+=("--ip")
    local_nonpersistent_flags+=("--ip=")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")
    flags+=("--wait=")
    two_word_flags+=("--wait")
    two_word_flags+=("-w")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_add()
{
    last_command="hostctl_add"

    command_aliases=()

    commands=()
    commands+=("domains")
    if [[ -z "${BASH_VERSION:-}" || "${BASH_VERSINFO[0]:-}" -gt 3 ]]; then
        command_aliases+=("domain [profile] [domains] [flags]")
        aliashash["domain [profile] [domains] [flags]"]="domains"
    fi

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--from=")
    two_word_flags+=("--from")
    two_word_flags+=("-f")
    local_nonpersistent_flags+=("--from")
    local_nonpersistent_flags+=("--from=")
    local_nonpersistent_flags+=("-f")
    flags+=("--wait=")
    two_word_flags+=("--wait")
    two_word_flags+=("-w")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_backup()
{
    last_command="hostctl_backup"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--path=")
    two_word_flags+=("--path")
    local_nonpersistent_flags+=("--path")
    local_nonpersistent_flags+=("--path=")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_disable()
{
    last_command="hostctl_disable"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--all")
    local_nonpersistent_flags+=("--all")
    flags+=("--only")
    local_nonpersistent_flags+=("--only")
    flags+=("--wait=")
    two_word_flags+=("--wait")
    two_word_flags+=("-w")
    local_nonpersistent_flags+=("--wait")
    local_nonpersistent_flags+=("--wait=")
    local_nonpersistent_flags+=("-w")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_enable()
{
    last_command="hostctl_enable"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--all")
    local_nonpersistent_flags+=("--all")
    flags+=("--only")
    local_nonpersistent_flags+=("--only")
    flags+=("--wait=")
    two_word_flags+=("--wait")
    two_word_flags+=("-w")
    local_nonpersistent_flags+=("--wait")
    local_nonpersistent_flags+=("--wait=")
    local_nonpersistent_flags+=("-w")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_help()
{
    last_command="hostctl_help"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    has_completion_function=1
    noun_aliases=()
}

_hostctl_list_disabled()
{
    last_command="hostctl_list_disabled"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_list_enabled()
{
    last_command="hostctl_list_enabled"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_list()
{
    last_command="hostctl_list"

    command_aliases=()

    commands=()
    commands+=("disabled")
    if [[ -z "${BASH_VERSION:-}" || "${BASH_VERSINFO[0]:-}" -gt 3 ]]; then
        command_aliases+=("off")
        aliashash["off"]="disabled"
    fi
    commands+=("enabled")
    if [[ -z "${BASH_VERSION:-}" || "${BASH_VERSINFO[0]:-}" -gt 3 ]]; then
        command_aliases+=("on")
        aliashash["on"]="enabled"
    fi

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_remove_domains()
{
    last_command="hostctl_remove_domains"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_remove()
{
    last_command="hostctl_remove"

    command_aliases=()

    commands=()
    commands+=("domains")
    if [[ -z "${BASH_VERSION:-}" || "${BASH_VERSINFO[0]:-}" -gt 3 ]]; then
        command_aliases+=("domain [profile] [domains] [flags]")
        aliashash["domain [profile] [domains] [flags]"]="domains"
    fi

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--all")
    local_nonpersistent_flags+=("--all")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_replace()
{
    last_command="hostctl_replace"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--from=")
    two_word_flags+=("--from")
    two_word_flags+=("-f")
    local_nonpersistent_flags+=("--from")
    local_nonpersistent_flags+=("--from=")
    local_nonpersistent_flags+=("-f")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_restore()
{
    last_command="hostctl_restore"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--from=")
    two_word_flags+=("--from")
    local_nonpersistent_flags+=("--from")
    local_nonpersistent_flags+=("--from=")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_status()
{
    last_command="hostctl_status"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_sync_docker()
{
    last_command="hostctl_sync_docker"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--domain=")
    two_word_flags+=("--domain")
    two_word_flags+=("-d")
    local_nonpersistent_flags+=("--domain")
    local_nonpersistent_flags+=("--domain=")
    local_nonpersistent_flags+=("-d")
    flags+=("--network=")
    two_word_flags+=("--network")
    local_nonpersistent_flags+=("--network")
    local_nonpersistent_flags+=("--network=")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")
    flags+=("--wait=")
    two_word_flags+=("--wait")
    two_word_flags+=("-w")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_sync_docker-compose()
{
    last_command="hostctl_sync_docker-compose"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--compose-file=")
    two_word_flags+=("--compose-file")
    local_nonpersistent_flags+=("--compose-file")
    local_nonpersistent_flags+=("--compose-file=")
    flags+=("--domain=")
    two_word_flags+=("--domain")
    two_word_flags+=("-d")
    local_nonpersistent_flags+=("--domain")
    local_nonpersistent_flags+=("--domain=")
    local_nonpersistent_flags+=("-d")
    flags+=("--network=")
    two_word_flags+=("--network")
    local_nonpersistent_flags+=("--network")
    local_nonpersistent_flags+=("--network=")
    flags+=("--prefix")
    local_nonpersistent_flags+=("--prefix")
    flags+=("--project-name=")
    two_word_flags+=("--project-name")
    local_nonpersistent_flags+=("--project-name")
    local_nonpersistent_flags+=("--project-name=")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")
    flags+=("--wait=")
    two_word_flags+=("--wait")
    two_word_flags+=("-w")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_sync()
{
    last_command="hostctl_sync"

    command_aliases=()

    commands=()
    commands+=("docker")
    commands+=("docker-compose")

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--wait=")
    two_word_flags+=("--wait")
    two_word_flags+=("-w")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_toggle()
{
    last_command="hostctl_toggle"

    command_aliases=()

    commands=()

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--wait=")
    two_word_flags+=("--wait")
    two_word_flags+=("-w")
    local_nonpersistent_flags+=("--wait")
    local_nonpersistent_flags+=("--wait=")
    local_nonpersistent_flags+=("-w")
    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

_hostctl_root_command()
{
    last_command="hostctl"

    command_aliases=()

    commands=()
    commands+=("add")
    commands+=("backup")
    commands+=("disable")
    commands+=("enable")
    commands+=("help")
    commands+=("list")
    commands+=("remove")
    if [[ -z "${BASH_VERSION:-}" || "${BASH_VERSINFO[0]:-}" -gt 3 ]]; then
        command_aliases+=("rm [profiles] [flags]")
        aliashash["rm [profiles] [flags]"]="remove"
    fi
    commands+=("replace")
    commands+=("restore")
    commands+=("status")
    commands+=("sync")
    commands+=("toggle")

    flags=()
    two_word_flags=()
    local_nonpersistent_flags=()
    flags_with_completion=()
    flags_completion=()

    flags+=("--column=")
    two_word_flags+=("--column")
    two_word_flags+=("-c")
    flags+=("--host-file=")
    two_word_flags+=("--host-file")
    flags+=("--no-color")
    flags+=("--out=")
    two_word_flags+=("--out")
    two_word_flags+=("-o")
    flags+=("--quiet")
    flags+=("-q")
    flags+=("--raw")

    must_have_one_flag=()
    must_have_one_noun=()
    noun_aliases=()
}

__start_hostctl()
{
    local cur prev words cword split
    declare -A flaghash 2>/dev/null || :
    declare -A aliashash 2>/dev/null || :
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion -s || return
    else
        __hostctl_init_completion -n "=" || return
    fi

    local c=0
    local flag_parsing_disabled=
    local flags=()
    local two_word_flags=()
    local local_nonpersistent_flags=()
    local flags_with_completion=()
    local flags_completion=()
    local commands=("hostctl")
    local command_aliases=()
    local must_have_one_flag=()
    local must_have_one_noun=()
    local has_completion_function=""
    local last_command=""
    local nouns=()
    local noun_aliases=()

    __hostctl_handle_word
}

if [[ $(type -t compopt) = "builtin" ]]; then
    complete -o default -F __start_hostctl hostctl
else
    complete -o default -o nospace -F __start_hostctl hostctl
fi

# ex: ts=4 sw=4 et filetype=sh
```

The byte-exact required zsh output follows:

```zsh
#compdef hostctl
compdef _hostctl hostctl

# zsh completion for hostctl                              -*- shell-script -*-

__hostctl_debug()
{
    local file="$BASH_COMP_DEBUG_FILE"
    if [[ -n ${file} ]]; then
        echo "$*" >> "${file}"
    fi
}

_hostctl()
{
    local shellCompDirectiveError=1
    local shellCompDirectiveNoSpace=2
    local shellCompDirectiveNoFileComp=4
    local shellCompDirectiveFilterFileExt=8
    local shellCompDirectiveFilterDirs=16
    local shellCompDirectiveKeepOrder=32

    local lastParam lastChar flagPrefix requestComp out directive comp lastComp noSpace keepOrder
    local -a completions

    __hostctl_debug "\n========= starting completion logic =========="
    __hostctl_debug "CURRENT: ${CURRENT}, words[*]: ${words[*]}"

    # The user could have moved the cursor backwards on the command-line.
    # We need to trigger completion from the $CURRENT location, so we need
    # to truncate the command-line ($words) up to the $CURRENT location.
    # (We cannot use $CURSOR as its value does not work when a command is an alias.)
    words=("${=words[1,CURRENT]}")
    __hostctl_debug "Truncated words[*]: ${words[*]},"

    lastParam=${words[-1]}
    lastChar=${lastParam[-1]}
    __hostctl_debug "lastParam: ${lastParam}, lastChar: ${lastChar}"

    # For zsh, when completing a flag with an = (e.g., hostctl -n=<TAB>)
    # completions must be prefixed with the flag
    setopt local_options BASH_REMATCH
    if [[ "${lastParam}" =~ '-.*=' ]]; then
        # We are dealing with a flag with an =
        flagPrefix="-P ${BASH_REMATCH}"
    fi

    # Prepare the command to obtain completions
    requestComp="${words[1]} __complete ${words[2,-1]}"
    if [ "${lastChar}" = "" ]; then
        # If the last parameter is complete (there is a space following it)
        # We add an extra empty parameter so we can indicate this to the go completion code.
        __hostctl_debug "Adding extra empty parameter"
        requestComp="${requestComp} \"\""
    fi

    __hostctl_debug "About to call: eval ${requestComp}"

    # Use eval to handle any environment variables and such
    out=$(eval ${requestComp} 2>/dev/null)
    __hostctl_debug "completion output: ${out}"

    # Extract the directive integer following a : from the last line
    local lastLine
    while IFS='\n' read -r line; do
        lastLine=${line}
    done < <(printf "%s\n" "${out[@]}")
    __hostctl_debug "last line: ${lastLine}"

    if [ "${lastLine[1]}" = : ]; then
        directive=${lastLine[2,-1]}
        # Remove the directive including the : and the newline
        local suffix
        (( suffix=${#lastLine}+2))
        out=${out[1,-$suffix]}
    else
        # There is no directive specified.  Leave $out as is.
        __hostctl_debug "No directive found.  Setting do default"
        directive=0
    fi

    __hostctl_debug "directive: ${directive}"
    __hostctl_debug "completions: ${out}"
    __hostctl_debug "flagPrefix: ${flagPrefix}"

    if [ $((directive & shellCompDirectiveError)) -ne 0 ]; then
        __hostctl_debug "Completion received error. Ignoring completions."
        return
    fi

    local activeHelpMarker="_activeHelp_ "
    local endIndex=${#activeHelpMarker}
    local startIndex=$((${#activeHelpMarker}+1))
    local hasActiveHelp=0
    while IFS='\n' read -r comp; do
        # Check if this is an activeHelp statement (i.e., prefixed with $activeHelpMarker)
        if [ "${comp[1,$endIndex]}" = "$activeHelpMarker" ];then
            __hostctl_debug "ActiveHelp found: $comp"
            comp="${comp[$startIndex,-1]}"
            if [ -n "$comp" ]; then
                compadd -x "${comp}"
                __hostctl_debug "ActiveHelp will need delimiter"
                hasActiveHelp=1
            fi

            continue
        fi

        if [ -n "$comp" ]; then
            # If requested, completions are returned with a description.
            # The description is preceded by a TAB character.
            # For zsh's _describe, we need to use a : instead of a TAB.
            # We first need to escape any : as part of the completion itself.
            comp=${comp//:/\\:}

            local tab="$(printf '\t')"
            comp=${comp//$tab/:}

            __hostctl_debug "Adding completion: ${comp}"
            completions+=${comp}
            lastComp=$comp
        fi
    done < <(printf "%s\n" "${out[@]}")

    # Add a delimiter after the activeHelp statements, but only if:
    # - there are completions following the activeHelp statements, or
    # - file completion will be performed (so there will be choices after the activeHelp)
    if [ $hasActiveHelp -eq 1 ]; then
        if [ ${#completions} -ne 0 ] || [ $((directive & shellCompDirectiveNoFileComp)) -eq 0 ]; then
            __hostctl_debug "Adding activeHelp delimiter"
            compadd -x "--"
            hasActiveHelp=0
        fi
    fi

    if [ $((directive & shellCompDirectiveNoSpace)) -ne 0 ]; then
        __hostctl_debug "Activating nospace."
        noSpace="-S ''"
    fi

    if [ $((directive & shellCompDirectiveKeepOrder)) -ne 0 ]; then
        __hostctl_debug "Activating keep order."
        keepOrder="-V"
    fi

    if [ $((directive & shellCompDirectiveFilterFileExt)) -ne 0 ]; then
        # File extension filtering
        local filteringCmd
        filteringCmd='_files'
        for filter in ${completions[@]}; do
            if [ ${filter[1]} != '*' ]; then
                # zsh requires a glob pattern to do file filtering
                filter="\*.$filter"
            fi
            filteringCmd+=" -g $filter"
        done
        filteringCmd+=" ${flagPrefix}"

        __hostctl_debug "File filtering command: $filteringCmd"
        _arguments '*:filename:'"$filteringCmd"
    elif [ $((directive & shellCompDirectiveFilterDirs)) -ne 0 ]; then
        # File completion for directories only
        local subdir
        subdir="${completions[1]}"
        if [ -n "$subdir" ]; then
            __hostctl_debug "Listing directories in $subdir"
            pushd "${subdir}" >/dev/null 2>&1
        else
            __hostctl_debug "Listing directories in ."
        fi

        local result
        _arguments '*:dirname:_files -/'" ${flagPrefix}"
        result=$?
        if [ -n "$subdir" ]; then
            popd >/dev/null 2>&1
        fi
        return $result
    else
        __hostctl_debug "Calling _describe"
        if eval _describe $keepOrder "completions" completions $flagPrefix $noSpace; then
            __hostctl_debug "_describe found some completions"

            # Return the success of having called _describe
            return 0
        else
            __hostctl_debug "_describe did not find completions."
            __hostctl_debug "Checking if we should do file completion."
            if [ $((directive & shellCompDirectiveNoFileComp)) -ne 0 ]; then
                __hostctl_debug "deactivating file completion"

                # We must return an error code here to let zsh know that there were no
                # completions found by _describe; this is what will trigger other
                # matching algorithms to attempt to find completions.
                # For example zsh can match letters in the middle of words.
                return 1
            else
                # Perform file completion
                __hostctl_debug "Activating file completion"

                # We must return the result of this command, so it must be the
                # last command, or else we must store its result to return it.
                _arguments '*:filename:_files'" ${flagPrefix}"
            fi
        fi
    fi
}

# don't run the completion function when being source-ed or eval-ed
if [ "$funcstack[1]" = "_hostctl" ]; then
    _hostctl
fi
```

## Spec 21

Error operations must not partially change the hosts file. Validate missing names, one-profile-only commands, reserved `default`, `--all` conflicts, and existence of every named profile before flushing, except that `enable --only` and `disable --only` deliberately ignore unknown names as specified in Spec 15. Add/replace `--from` values are not readability-validated because those values are ignored as specified in Specs 13 and 18. Canonical application errors use `[✖] error: MESSAGE\n`, optionally after the hosts-file info line and a blank line. Required stable message fragments include `missing profile name`, `specify only one profile`, `unknown profile name`, `'default' profile should not be handled by hostctl`, `args must be empty with --all flag`, `unknown flag: --name`, and OS-style `open PATH: no such file or directory` for operations that actually open such a path.

Operations must handle thousands of routes and hundreds-character names without truncation or crashes. Consecutive invocations observe persisted state. Backups/restores are byte-preserving; profile mutations may deliberately canonicalize only the managed representation described above.
