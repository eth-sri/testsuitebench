# RustOwl executable behavioral specification

This document is the complete behavioral contract for the required artifact. The artifact is one executable file named exactly `executable`. All paths, arguments, environment variables, standard streams, exit statuses, filesystem effects, and protocol objects below are observable requirements. The files under `exact-output/` are normative parts of this specification; they contain bytes that would be needlessly ambiguous in prose. No source code, repository history, test suite, or outside documentation is required to interpret this contract.

Unless a requirement says otherwise, textual output is UTF-8, uses LF (`\n`) line endings, ends with one LF, and is deterministic across repeated processes. Successful help, version, and completion requests use stdout only. Argument-parser failures use stderr only and exit 2. Runtime failures exit 1. Successful commands exit 0.

## Spec 1

The executable presents itself as `RustOwl`, version `v1.0.0-rc.1`, while all usage lines use the literal program name `executable` regardless of the path used to launch it.

`executable --version` and `executable -V` must print exactly `RustOwl v1.0.0-rc.1\n` to stdout and nothing to stderr. A global quiet occurrence before the version flag, including `-q`, `--quiet`, repeated `-q` tokens, or a combined short form containing `q`, removes only the `RustOwl ` prefix: the exact output becomes `v1.0.0-rc.1\n`. Thus `-qV`, `-Vq`, `-qqqV`, `-Vqqq`, and `-qqVq` all produce that quiet form. Quiet never suppresses help or completion output.

The global options are `-V`/`--version`, repeatable counting `-q`/`--quiet`, `--stdio`, and `-h`/`--help`. The commands, in order, are `check`, `clean`, `toolchain`, `completions`, and `help`. Global options are valid only before a command. A command, when present, takes precedence over LSP startup even when `--stdio` precedes it.

Version routing has one token-specific edge case: `executable --version clean` exits 0 with both stdout and stderr empty. This is not the behavior of an arbitrary token after `--version`; for example, the exact `--version extra` parser failure is mapped in Spec 8.

## Spec 2

Top-level help is selected by `-h`, `--help`, or `help`. It exits 0, writes nothing to stderr, and is exactly:

```text
Usage: executable [OPTIONS] [COMMAND]

Commands:
  check        Check availability
  clean        Remove artifacts from the target directory
  toolchain    Install or uninstall the toolchain
  completions  Generate shell completions
  help         Print this message or the help of the given subcommand(s)

Options:
  -V, --version   Print version
  -q, --quiet...  Suppress output
      --stdio     Use stdio to communicate with the LSP server
  -h, --help      Print help
```

At top level, help takes precedence over version, quiet, stdio, repeated help, and even an otherwise invalid later option. Both `--help --version` and `--version --help` show help. A bare `--` stops option parsing, so `-- --help` instead attempts to dispatch a command literally named `--help` and fails as an unknown subcommand.

The `help` pseudo-command accepts a valid command path such as `help check`, `help clean`, `help toolchain`, `help completions`, `help toolchain install`, or `help toolchain uninstall` and displays the same corresponding help shown by `--help`. It is itself a routing pseudo-command, not a normal command with options: `help --help`, `toolchain help --help`, an unknown help target, or extra flags after the help target are parser errors.

## Spec 3

`check -h`, `check --help`, and `help check` exit 0 and print exactly:

```text
Check availability

Usage: executable check [OPTIONS] [path]

Arguments:
  [path]  The path of a file or directory to check availability

Options:
      --all-targets   Run the check for all targets instead of current only
      --all-features  Run the check for all features instead of the current active ones only
  -h, --help          Print help
```

`check` accepts at most one optional path plus the two non-repeatable flags `--all-targets` and `--all-features`. The flags may occur before or after the path, in either order. `--` ends option recognition, allowing a flag-looking token to be the path. An empty-string path is a parser error; whitespace-only, Unicode, special-character, relative, `.`, `..`, and very long paths are parsed as ordinary paths. Unknown or repeated flags and a second path are parser errors. Global flags placed after `check`, including `-q`, are parser errors even if a later `--help` is present.

## Spec 4

`clean -h`, `clean --help`, and `help clean` exit 0 and print exactly:

```text
Remove artifacts from the target directory

Usage: executable clean

Options:
  -h, --help  Print help
```

`clean` accepts no positional arguments and no command-specific flags. Global flags after it are rejected. Help is unaffected by preceding quiet or stdio flags.

## Spec 5

`toolchain --help` and `help toolchain` print exactly:

```text
Install or uninstall the toolchain

Usage: executable toolchain [COMMAND]

Commands:
  install    Install the toolchain
  uninstall  Uninstall the toolchain
  help       Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help
```

A bare `toolchain` is a silent successful no-op. Its only action subcommands are case-sensitive `install` and `uninstall`; near misspellings are rejected with suggestions. The nested `help` routing form behaves as described in Spec 2.

`toolchain install --help` and its help-routing equivalent print exactly:

```text
Install the toolchain

Usage: executable toolchain install [OPTIONS]

Options:
      --path <path>             Runtime directory path to install RustOwl toolchain
      --skip-rustowl-toolchain  Install Rust toolchain only
  -h, --help                    Print help
```

`toolchain uninstall --help` and its help-routing equivalent print exactly:

```text
Uninstall the toolchain

Usage: executable toolchain uninstall

Options:
  -h, --help  Print help
```

The install options are case-sensitive and non-repeatable. `--path` accepts either `--path VALUE` or `--path=VALUE`, but an absent or empty value is a parser error. `--skip-rustowl-toolchain` takes no value. `uninstall` accepts no arguments or flags of its own. Global flags appearing after either nested action are rejected.

## Spec 6

`completions --help` and `help completions` print exactly:

```text
Generate shell completions

Usage: executable completions <SHELL>

Arguments:
  <SHELL>
          The shell to generate completions for

          Possible values:
          - bash:       Bourne Again `SHell` (bash)
          - elvish:     Elvish shell
          - fish:       Friendly Interactive `SHell` (fish)
          - powershell: `PowerShell`
          - zsh:        Z `SHell` (zsh)
          - nushell:    Nushell

Options:
  -h, --help
          Print help (see a summary with '-h')
```

The command requires exactly one shell value from the case-sensitive ordered set `bash`, `elvish`, `fish`, `powershell`, `zsh`, `nushell`. No partial, prefixed, uppercase, mixed-case, numeric, empty, whitespace-containing, special-character, newline-containing, or Unicode-extended value is accepted. A second shell or any option after the shell is rejected. A preceding global quiet flag does not change the generated script.

## Spec 7

For a valid completion shell, exit 0, write nothing to stderr, and write exactly the bytes of `exact-output/completions/<shell>.golden` to stdout. These six local files are authoritative, including whitespace and their final newline. They are distinct shell-specific scripts and must be returned unchanged on every call. In particular they define the `_rustowl()` Bash function and `complete -F _rustowl`, the Fish `__fish_rustowl` conditions, the Zsh `#compdef rustowl`/autoload script, the PowerShell `Register-ArgumentCompleter` script block, the Elvish `edit:completion:arg-completer` definitions, and the Nushell `export extern rustowl` declarations. Completion generation is pure metadata behavior: it never reads or installs a toolchain, changes the filesystem, or emits logging, regardless of `RUST_LOG`, `RUSTOWL_CACHE`, `RUSTOWL_CACHE_DIR`, or `HOME`.

The checked-in golden files are the complete scripts, not illustrative fragments. Among other byte-for-byte consequences, Bash begins `_rustowl() {` followed by `    local i cur prev opts cmd`; Fish defines both `__fish_rustowl_needs_command` and `__fish_rustowl_using_subcommand`; Zsh invokes `_arguments "${_arguments_options[@]}"`; Elvish begins with an empty line and then `use builtin;` and `use str;`, and uses `edit:complex-candidate`; Nushell defines `export extern "rustowl toolchain install"` and types the install option as `--path: path`; PowerShell begins with an empty line before its namespace declarations. These structural statements do not replace or relax exact equality with the files.

The exact stdout byte lengths are 11,451 for Bash, 3,600 for Elvish, 5,311 for Fish, 7,308 for PowerShell, 8,891 for Zsh, and 2,767 for Nushell.

## Spec 8

Command-line parsing follows the diagnostic wording, suggestion behavior, stream choice, spacing, and usage hints represented by `exact-output/errors/`. Except for the timestamp-normalized runtime-error fixture called out in Spec 11, each file is the exact stderr for its mapped parser condition; stdout is empty and status is 2. The subdirectories disambiguate cases whose wording depends on the precise token:

- `errors/cli/` covers the baseline invocations: unknown top-level flag, `invalid_command`, `check --unknown`, an extra argument to `clean`, missing/empty/invalid/case-mismatched completion shell, and an invalid `toolchain` action.
- `errors/error_messages/` covers the filename-described variants and tokens: multiple paths, active valid flags followed by an unknown flag, repeated flags, `--all-feature`/`--all-target` corrections, missing install path value, mixed valid/invalid install flags, extra completion or uninstall arguments, the exact `--version extra` case, `instal`/`uninsta`/`clen`/`chek`/`completion` suggestions, repeated version spellings, empty or whitespace commands, special-character command/shell values, and invalid `help` routing.
- `errors/flag_interactions/` covers command-scoping errors, repeated `--stdio`, repeated check/install options, empty paths, and multiple check paths for the concrete token sequences described by those filenames.
- `errors/output_format/` gives exact diagnostics for top-level and `check` token `--invalid-flag`, completion value `invalid`, and a missing completion value.
- `errors/shells/` gives exact diagnostics for `unknown_shell`, `BASH`, `Bash`, the empty string, `bas h`, `bash;`, `123`, `bas`, `/bin/bash`, two values `bash fish`, `bash🐚`, `bash\ntab`, and a missing value.
- `errors/toolchain/` gives the exact empty-path parser diagnostic, install unknown-flag diagnostic, and the normalized runtime error for an install destination that is an existing regular file.

The following attributed cases have explicit exact mappings. The argv lists omit argv[0]. Each invocation exits 2, emits no stdout, and emits exactly the named file on stderr. `PATH`, `PATH1`, and `PATH2` below stand for arbitrary nonempty path argument strings; their spelling is not interpolated into these diagnostics.

| argv | Exact stderr file |
|---|---|
| `["check", "--unknown"]` | `exact-output/errors/attributed/check_unknown.golden` |
| `["check", "--unknown-flag"]` | `exact-output/errors/attributed/check_unknown_flag.golden` |
| `["check", ""]` | `exact-output/errors/attributed/check_empty_path.golden` |
| `["check", "--all-feature"]` | `exact-output/errors/attributed/check_all_feature.golden` |
| `["check", "--all-target"]` | `exact-output/errors/attributed/check_all_target.golden` |
| `["check", "--all-features", "--all-targets", "--unknown"]` | `exact-output/errors/attributed/check_active_flags_unknown.golden` |
| `["check", "-q"]` | `exact-output/errors/attributed/check_quiet_after.golden` |
| `["completions", ""]` | `exact-output/errors/attributed/completions_empty_shell.golden` |
| `["completions"]` | `exact-output/errors/output_format/completions_missing_arg.golden` |
| `["completions", "--all-targets"]` | `exact-output/errors/attributed/completions_check_flag.golden` |
| `["completions", "ba$h"]` | `exact-output/errors/attributed/completions_ba_dollar_h.golden` |
| `["completions", "fihs"]` | `exact-output/errors/attributed/completions_fihs.golden` |
| `["completions", "PowerShell"]` | `exact-output/errors/attributed/completions_PowerShell.golden` |
| `["completions", "Nushell"]` | `exact-output/errors/attributed/completions_Nushell.golden` |
| `["toolchain", "install", "--path", PATH, "--unknown-option"]` | `exact-output/errors/attributed/toolchain_install_mixed_unknown.golden` |
| `["toolchain", "install", "--path", PATH1, "--path", PATH2]` | `exact-output/errors/attributed/toolchain_install_path_repeated.golden` |
| `["--version", "extra"]` | `exact-output/errors/attributed/version_extra.golden` |
| `["-V", "-V"]` | `exact-output/errors/error_messages/version_short_repeated.golden` |
| `["check|grep"]` | `exact-output/errors/error_messages/check_pipe_grep.golden` |
| `["help", "unknown"]` | `exact-output/errors/attributed/help_unknown.golden` |
| `["help", "check", "--unknown"]` | `exact-output/errors/attributed/help_check_unknown.golden` |
| `["completions", "bash", "-q"]` | `exact-output/errors/attributed/completions_bash_quiet_after.golden` |
| `["toolchain", "instal"]` | `exact-output/errors/attributed/toolchain_instal.golden` |
| `["toolchain", "uninsta"]` | `exact-output/errors/attributed/toolchain_uninsta.golden` |
| `["check", "--invalid-flag"]` | `exact-output/errors/output_format/check_invalid_flag.golden` |
| `["completions", "unknown_shell"]` | `exact-output/errors/shells/unknown_shell.golden` |
| `["completions", "BASH"]` | `exact-output/errors/shells/BASH.golden` |
| `["completions", "Bash"]` | `exact-output/errors/shells/Bash.golden` |
| `["completions", "123"]` | `exact-output/errors/shells/123.golden` |
| `["completions", "bas"]` | `exact-output/errors/shells/bas.golden` |
| `["completions", "bas h"]` | `exact-output/errors/shells/bas_space_h.golden` |
| `["completions", "bash;"]` | `exact-output/errors/shells/bash_semicolon.golden` |
| `["completions", "/bin/bash"]` | `exact-output/errors/shells/bin_bash.golden` |
| `["completions", "bash🐚"]` | `exact-output/errors/shells/bash_emoji.golden` |
| `["completions", "bash\ntab"]` | `exact-output/errors/shells/bash_newline_tab.golden` |
| `["completions", "雪x"]` | `exact-output/errors/shells/snow_x.golden` |
| `["toolchain", "install", "--path"]` | `exact-output/errors/toolchain/install_path_missing.golden` |
| `["toolchain", "install", "--path="]` | `exact-output/errors/toolchain/install_path_missing.golden` |
| `["toolchain", "install", "--path", ""]` | `exact-output/errors/toolchain/install_path_missing.golden` |
| `["toolchain", "install", "--skip-rustowl-toolchain=yes"]` | `exact-output/errors/toolchain/install_skip_value.golden` |

These mappings fix distinctions that the general model alone does not convey: an explicitly supplied empty `completions` value is reported as missing rather than invalid; an explicitly supplied empty `check` path is likewise reported as missing and has no usage block; and the mapped invalid supplied completion values omit a usage block, whether or not they receive a close-match tip. All three missing or empty `--path` forms mapped above also omit a usage block. By contrast, assigning a value to `--skip-rustowl-toolchain` prints the narrowed usage line `Usage: executable toolchain install --skip-rustowl-toolchain`. Close shell values use `a similar value exists`, close check flags use `a similar argument exists`, and an already-active check flag is written literally in the usage line. Unknown flag-like values also receive the `to pass ... as a value, use '-- ...'` tip where shown by the corresponding file. Help routing retains the selected command context: `help unknown` uses top-level usage, while `help check --unknown` uses check usage.

For an invalid token not captured by a fixture, apply the same model: begin `error:` in lowercase, quote the offending token, optionally include a `tip:` correction for a close match, include a usage block when that parser route does so, and end with `For more information, try '--help'.`. This offending-spelling rule applies to invalid tokens, not to repeated recognized options: a repeated option diagnostic may use that option's canonical long name, as the mapped `-V -V` case does. The exact mappings above govern routes that omit or narrow usage. Suggestions are case-sensitive and include all relevant valid alternatives. Parser help/version handling is immediate; help at top level wins over later invalid arguments, while subcommand-scoping errors still apply as stated in Specs 3–6 and the `--version clean` exception in Spec 1.

## Spec 9

The `clean` operation works relative to the process current directory. If usable Cargo target metadata can be identified there, recursively remove only that project's `target/owl` directory. Preserve `Cargo.toml`, all source files, `target` itself, and every sibling such as `target/debug` and `target/release`, with contents unchanged. Deep trees inside `target/owl` are removed completely.

If no usable Cargo target metadata or no `target/owl` exists, do nothing. A package manifest with no `src` directory and no source target is such a no-op: `target/owl` remains present. A package with `src/lib.rs` is recognized and its `target/owl` is removed. Cleaning is idempotent across any number of calls. Every successful clean is silent on both streams and exits 0, including the manifest-only no-op and directories with no `Cargo.toml`. It does not require or auto-install the RustOwl toolchain. It must not affect another project elsewhere. Cache-related environment settings do not alter this behavior.

## Spec 10

At runtime, `check [path]` analyzes the supplied target, defaulting to the current directory when omitted. Parser-valid paths are interpreted relative to the process current directory without shell expansion. A usable project target is a directory with parseable Cargo metadata and Rust sources; standalone files, non-Rust or binary files, broken links, empty directories, directories lacking `Cargo.toml`, and malformed manifests are invalid or fail analysis.

On these failures the process exits 1, stdout is empty, and stderr identifies the supplied/resolved target and contains `Invalid analysis target: <path>` when validation fails, followed by an error containing `Analyze failed`. Error reporting remains present enough to identify the failure even under quiet mode, and quiet never changes the exit status. `--all-targets` and `--all-features` are forwarded as independent analysis choices but do not make an invalid target valid. Paths with spaces, punctuation, Unicode, dot segments, or extreme length must fail gracefully rather than crash when they do not name a usable project.

The one-path rule still applies after `--`: for example, `check -- --help` treats `--help` as the path, exits 1, and reports `Invalid analysis target: --help` rather than displaying help.

## Spec 11

The runtime directory for managed tools is an explicit install `--path` when supplied; otherwise it is `$HOME/.rustowl`. Installation creates missing parent directories. The managed sysroot is `<runtime>/sysroot/nightly-2025-06-20-x86_64-unknown-linux-gnu` on the evaluated Linux target.

`toolchain install` installs the pinned nightly Rust components identified as `rustc`, `cargo`, and `rust-std`, preserving their component directory structure so the managed sysroot has a `bin` directory and at least a `rustc`-named entry. Without `--skip-rustowl-toolchain`, it additionally installs RustOwl toolchain binaries; with that option it installs only the Rust components. The observable contract does not mandate how these files are obtained. A normal default-path or writable custom-path install must finish successfully within its several-minute allowance and exit 0; acquisition, archive, or filesystem problems are recoverable runtime errors rather than crashes.

Progress/log output goes only to stderr; stdout stays empty. Non-quiet installation reports at least `start installing Rust toolchain`, `start downloading`, downloaded component names such as `rustc`, `cargo`, or `rust-std`, percentage completion including `100% received`, and finally `installing Rust toolchain finished`. Network, extraction, or filesystem failures exit 1 with a useful stderr error. An existing regular file such as `/dev/null`, `/dev/zero`, `/proc/self/fd/0`, or a regular temporary file cannot be an install directory and is preserved unchanged. This failure exits 1 with empty stdout. Its stderr has a varying leading UTC timestamp in the exact shape `YYYY-MM-DDTHH:MM:SS.sssZ`, where `sss` is exactly three decimal digits. After removing that timestamp and the following single space, the remaining bytes are exactly `exact-output/errors/toolchain/error_install_invalid_path.golden`.

## Spec 12

`toolchain uninstall` operates on the default runtime selected from `HOME`, removing the installed managed sysroot tree recursively when present. It succeeds silently with exit 0 when the runtime directory or sysroot is absent and remains silent and successful on repeated calls. It must handle nested directories. It never emits stdout.

When a managed nightly sysroot is actually present and removed, uninstall exits 0 and writes one timestamped INFO line to stderr in this form, ending in LF:

```text
<timestamp> INFO  [rustowl::toolchain] remove sysroot: <absolute managed nightly sysroot path>
```

The path is the directory being removed, such as `$HOME/.rustowl/sysroot/nightly-2025-06-20-x86_64-unknown-linux-gnu`. Preceding quiet occurrences, including `-qqq`, are accepted but do not suppress this removal line. Quiet uninstall is silent only when no managed nightly sysroot is present to remove.

After a real default-path install, the managed sysroot contains at least one nightly directory; uninstall leaves no entries under the default `~/.rustowl/sysroot`, and another uninstall remains a no-op. An install to an explicit custom `--path` is located at that custom runtime rather than silently redirecting to the default.

## Spec 13

Before analysis, `check` uses the managed toolchain and may fall back to system commands when a required binary is unavailable. In particular, an unavailable `rustowlc` produces a stderr message containing `rustowlc not found; fallback` before the ultimate analysis error.

If the managed sysroot directory itself is absent, `check` automatically performs the installation behavior of Spec 11 and logs `sysroot not found; start setup toolchain`, followed by the normal installation progress. A completed auto-install creates `$HOME/.rustowl/sysroot/...`. Malformed projects, missing executables, and external-command failure are handled as normal runtime errors rather than crashes. `clean`, help, version, and completions never trigger this setup.

## Spec 14

`RUSTOWL_CACHE` and `RUSTOWL_CACHE_DIR` must be accepted without parse errors for all CLI operations. Values may be absent, empty, Boolean-like in any case, numeric, arbitrary text, surrounded by whitespace, contain tabs/newlines, or point to absolute, relative, nonexistent, symlinked, space-containing, Unicode, punctuation-containing, dot-segment, tilde-containing, trailing-slash, or very long paths. These variables must never alter help, version, or completion bytes and must not add output. They do not prevent silent cleaning.

`RUST_LOG` may control runtime logging, but an invalid value falls back without an error. It never changes help, version, or completion output; in particular completion stdout remains byte-identical and stderr empty under `RUST_LOG=debug`. Check and toolchain diagnostics belong on stderr.

## Spec 15

With no command, both `executable` and `executable --stdio` enter an LSP server mode over stdin/stdout and immediately write exactly this to stderr:

```text
RustOwl v1.0.0-rc.1
This is an LSP server. You can use --help flag to show help.
```

EOF before a message ends the process successfully. LSP stdout contains protocol frames only. Each input and output message uses ASCII `Content-Length: N\r\n\r\n` followed by exactly `N` UTF-8 bytes of JSON. Input frames are decoded in stream order and responses preserve the request's JSON `id` exactly, but request handlers are dispatched concurrently. Responses do not generally preserve input order: reading a complete `initialize` frame does not by itself establish initialized state for subsequent frames already available in the same stdin payload, and those requests produce the concrete response ordering below.

In particular, if a valid `initialize` request and one or more `rustowl/analyze` or `rustowl/cursor` requests are submitted together without waiting for the initialize response, every following custom request receives `{"jsonrpc":"2.0","error":{"code":-32002,"message":"Server not initialized"},"id":<same id>}` before the initialize success response. This applies to analyze parameter objects `{}`, `{"unknown":[1,2,3]}`, `{"all_targets":true}`, `{"all_features":true}`, and `{"all_targets":false,"all_features":true}`, to absent analyze parameters, and to cursor requests for existing, nonexistent, HTTP, and `untitled:` URIs. With three absent-parameter analyze requests having IDs 21, 22, and 23, their three `-32002` responses occur in that ID order, followed by the initialize response. Notifications interposed after the initialize frame produce no responses and do not create a synchronization barrier; a final analyze request with ID 40 likewise receives `-32002` before the initialize success.

For the single-payload sequence initialize ID 1, shutdown ID 11, and an `exit` notification, the two responses occur in this order: initialize ID 1 receives code `-32800` and message `Canceled`, then shutdown ID 11 receives code `-32002` and message `Server not initialized`; `exit` has no response. The process exits 0.

A malformed input with no `Content-Length` or a request whose `jsonrpc` is not `"2.0"` ends cleanly with status 0. A zero content length is ignored while the server stays alive. An extremely large declared length may leave the server waiting for the body or make it exit cleanly, but must not crash or allocate unsafely.

## Spec 16

Before a successful `initialize`, ordinary requests receive a JSON-RPC error with code `-32002` and message `Server not initialized`. An unknown request method after initialization receives code `-32601`. An `initialize` request lacking the required `capabilities` member receives code `-32602` and the exact message ``missing field `capabilities``` (the inner backticks are literal message characters). Null/zero/nonzero process IDs, a null `rootUri`, workspace folders containing valid, invalid, duplicate, nonexistent, mixed, or non-Cargo file URIs, and arbitrary client capability detail are tolerated when the rest of the request is valid.

A syntactically invalid relative `rootUri` is not tolerated. In the concrete request whose `rootUri` is `not a valid uri`, initialize returns code `-32602` with message `relative URL without a base: "not a valid uri"`. If that failed initialize is immediately followed by another initialize having null `processId`, `rootUri`, and `workspaceFolders`, the first error response is followed by a successful response to the second request.

A successful `initialize` response is `{"jsonrpc":"2.0","id":<same id>,"result":{"capabilities":...}}` with no error. Its capabilities include:

```json
{
  "textDocumentSync": {"openClose": true, "change": 2, "save": true},
  "workspace": {"workspaceFolders": {"supported": true, "changeNotifications": true}}
}
```

Additional valid capability fields are allowed. Incremental sync is represented by `change: 2`. Repeated initialize requests must not crash the process. Once initialization has completed and its success response has been received, `shutdown` returns a JSON-RPC success response with `result: null`; repeated shutdown may also respond or may leave a caller waiting, but the server must not crash. The immediate initialize/shutdown/exit batch instead has the pre-initialization behavior specified in Spec 15. The `exit` notification may terminate the process.

## Spec 17

After initialization has completed and the client has received its success response, accept and safely ignore or process these notifications without replying or terminating: `initialized`, `textDocument/didOpen`, `textDocument/didChange` (full or ranged incremental changes, empty changes, rapid/repeated versions, and change without prior open), `textDocument/didClose`, and `workspace/didChangeWorkspaceFolders` (empty, additions, removals, duplicates, and invalid/nonexistent URIs). Missing optional document fields, non-Rust documents, directory URIs, invalid schemes, nonexistent files, duplicate opens, UTF-8 content, and CRLF text must not crash the server. Notifications submitted in the same input batch as an in-progress initialize behave as specified in Spec 15.

Opening a Rust document or adding a valid workspace may trigger analysis. Analysis may run asynchronously, but `shutdown` during it must promptly acknowledge with null and clean up child processes. Client work-done-progress capability and progress tokens must be tolerated; the server need not emit progress notifications to satisfy this contract.

## Spec 18

The custom request `rustowl/analyze` is valid after initialization has completed and the client has received the initialize success response. It accepts an absent/empty object and also ignores unknown parameter fields, returning a JSON-RPC success response whose result is exactly an object (the empty object `{}` is valid). It must accept the Boolean choices `all_targets` and `all_features`, separately or together. Repeated requests, requests for a Cargo workspace, a single opened Rust file without Cargo metadata, an invalid/empty project, and workspaces added or removed through notifications must all receive a response rather than hang or crash. Requests sent immediately behind an initialize frame without waiting for its response instead receive the pre-initialization error in Spec 15.

Analysis failures are a supported outcome. The executable is not required by this evaluated contract to synthesize ownership decorations when its analyzer/toolchain is unavailable. It must, however, settle promptly into a coherent terminal error state after an attempted analysis.

## Spec 19

After initialization has completed and the client has received its success response, the custom request `rustowl/cursor` accepts an object containing `document.uri` and an LSP `position` (`line` and `character`, zero-based). It returns a JSON-RPC success response with an object containing all four fields:

```json
{
  "is_analyzed": false,
  "status": "error",
  "path": "/decoded/local/path/to/file.rs",
  "decorations": []
}
```

The shown values are the canonical analysis-error result; a genuinely successful analysis may instead use `is_analyzed: true` and `status: "finished"`. `status` is always one lowercase string from `analyzing`, `finished`, or `error`. `finished` implies `is_analyzed: true`; `error` implies `is_analyzed: false` and an empty decorations array. Once an attempt has settled, repeated cursor calls and calls for multiple files in the same workspace report a consistent terminal status. The status field exists even before explicit analysis.

For an existing local `file://` URI, percent-decode it and return its native path string, ending with the requested filename. For a nonexistent file or non-file URI, return `path: null` and empty decorations. Existing but unreadable files, empty positions, positions beyond end of file, multi-byte UTF-8 text, CRLF text, and repeated calls must receive a structurally valid response without a crash. In the supported error outcome, empty decorations satisfy all of these cases. If decorations are ever returned, each must at minimum contain an LSP `range` with `start` and `end`, each having nonnegative integer `line` and `character` fields; the end must be strictly later than the start in lexicographic `(line, character)` order.

Cursor requests sent immediately behind an initialize frame without waiting for its response return no cursor-result object or decoded path; they receive the pre-initialization error in Spec 15, including for the URI and position edge cases above.

## Spec 20

All modes must be robust and isolated across processes. Informational and completion calls are stateless and deterministic. Cleaning one working directory cannot affect another. CLI-only operations should complete within a few seconds; parser errors and completion generation must not wait for a network. LSP requests that do not perform real analysis respond promptly, the server remains alive after tolerated notifications and malformed-but-ignorable events, and it never mixes logs into protocol stdout.

Filesystem deletion is restricted to the exact cache/toolchain locations specified: `clean` removes only the current Cargo project's `target/owl`, and `toolchain uninstall` removes the managed sysroot created under the selected default runtime. All path data is treated as data rather than shell syntax, and Unicode is preserved as UTF-8.
