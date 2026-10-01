# Normative byte-for-byte fixtures

All paths below are relative to `spec/sigoden__argc.04a08f1/`. Each command was run against `/workspace/executable`; every observed command exited 0 with empty stderr.

## Completion adapters

For each row, stdout is exactly the named golden file, including its final newline.

| Invocation | Exact stdout |
| --- | --- |
| `/workspace/executable --argc-completions bash simple` | `fixtures/completion-bash.golden` |
| `/workspace/executable --argc-completions zsh simple` | `fixtures/completion-zsh.golden` |
| `/workspace/executable --argc-completions fish simple` | `fixtures/completion-fish.golden` |
| `/workspace/executable --argc-completions nushell simple` | `fixtures/completion-nushell.golden` |
| `/workspace/executable --argc-completions powershell simple` | `fixtures/completion-powershell.golden` |
| `/workspace/executable --argc-completions elvish simple` | `fixtures/completion-elvish.golden` |

Changing `simple` to another command changes only the shell-specific registration occurrence(s) described by Spec 28. In particular, observed Bash invocations using `my-cli`, `mycommand`, and `test-cmd` retained the entire template and replaced the final registered command.

## Standalone builds

For each row except the file-output row, stdout is exactly the named golden file, including its final newline, and no output path is supplied.

| Invocation input | Exact output |
| --- | --- |
| `fixtures/build-simple.sh` | `fixtures/build-simple.golden` |
| `fixtures/build-complex.sh` | `fixtures/build-complex.golden` |
| `fixtures/build-dotenv.sh` | `fixtures/build-dotenv.golden` |
| `fixtures/build-hooks.sh` | `fixtures/build-hooks.golden` |
| `fixtures/build-bind-env.sh` | `fixtures/build-bind-env.golden` |
| `fixtures/build-required-default.sh` | `fixtures/build-required-default.golden` |
| `fixtures/build-default-subcommand.sh` | `fixtures/build-default-subcommand.golden` |
| `fixtures/build-choice-env.sh` | `fixtures/build-choice-env.golden` |
| `fixtures/build-bind-delimiter.sh` | `fixtures/build-bind-delimiter.golden` |

The command is `/workspace/executable --argc-build INPUT`. For file-output behavior, `/workspace/executable --argc-build fixtures/build-write.sh OUTFILE` writes `fixtures/build-write.golden` byte-for-byte to `OUTFILE` and leaves stdout and stderr empty.

These golden files are part of the specification. A behaviorally equivalent but textually different generated adapter or standalone implementation does not conform.
