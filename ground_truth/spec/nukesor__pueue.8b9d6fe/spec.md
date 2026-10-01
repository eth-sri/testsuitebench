# Specification for `executable`

## Spec 1

The required artifact is one executable file named exactly `executable`. It is the Pueue 4.0.4 command-line client. A compatible `pueued` daemon is supplied by the harness and is not part of this artifact. The executable must run on Linux, communicate with that daemon, and expose the commands and representations below. It must not implement, launch, replace, or emulate the daemon.

Unless a rule below explicitly says otherwise, a successful invocation exits with code 0, writes its human-readable result followed by `\n` to stdout, and leaves stderr empty. CLI parse failures and daemon `Failure` responses exit nonzero (normally 2 for argument parsing and 1 for runtime/daemon failures) and write the diagnostic to stderr. The executable must tolerate repeated, rapid, and concurrent invocations against the same daemon; state ownership and synchronization belong to the daemon.

The displayed product name and version are `pueue 4.0.4`. Both `--version` and `-V` print exactly `pueue 4.0.4\n`. `-v`, `-vv`, `-vvv`, four separate `-v` flags, and repeated `--verbose` are accepted globally; they must not interfere with version output.

## Spec 2

Global syntax is:

```text
executable [OPTIONS] [COMMAND]

-v, --verbose...         repeatable verbosity
    --color COLOR         auto, never, or always; default auto
-c, --config CONFIG      explicit YAML configuration path
-p, --profile PROFILE    profile name
-h, --help
-V, --version
```

With no command, behave as `status` with no options. Help, version, and completion generation happen before configuration loading and therefore work without a config file or daemon. All other commands load configuration and connect. Global options may precede the command. Integer task IDs are unsigned decimal values; negative or nonnumeric IDs are parser errors. In particular, `log -1` exits 2 with stdout empty and the diagnostic `error: unexpected argument '-1' found`, followed by a blank line, `  tip: to pass '-1' as a value, use '-- -1'`, the `Usage:` block, and the standard help hint. `kill abc` exits 2 with stdout empty and exactly:

```text
error: invalid value 'abc' for '[TASK_IDS]...': invalid digit found in string

For more information, try '--help'.
```

Priorities are signed 32-bit decimal integers. Counts, line limits, and parallel limits are nonnegative platform-sized integers.

The command set and one-line descriptions, in this order, is:

```text
add          Enqueue a task for execution
remove       Remove tasks from the list. Running or paused tasks need to be killed first
switch       Switches the queue position of two commands
stash        Stash a task. Stashed tasks won't be automatically started
enqueue      Enqueue stashed tasks. They'll be handled normally afterwards
start        Resume operation of specific tasks or groups of tasks
restart      Restart failed or successful task(s)
pause        Either pause running tasks or specific groups of tasks
kill         Kill specific running tasks or whole task groups
send         Send something to a task. Useful for sending confirmations such as 'y\n'
edit         Adjust editable properties of a task
env          Use this to add or remove environment variables from tasks
group        Use this to add or remove groups
status       Display the current status of all tasks
log          Display the log output of finished tasks
follow       Follow the output of a currently running task. This command works like "tail -f"
wait         Wait until tasks are finished
clean        Remove all finished tasks from the list
reset        Kill all tasks, clean up afterwards and reset EVERYTHING!
shutdown     Remotely shut down the daemon. Should only be used if the daemon isn't started by a service manager
parallel     Set the amount of allowed parallel tasks
completions  Generates shell completion files
help         Print this message or the help of the given subcommand(s)
```

Long help starts with `Interact with the Pueue daemon`, then `Use the \`--help\` long form to get detailed help output on each subcommand!`, a blank line, usage, the command list, and the global options. `-h` uses the same content but compact option layout; `--help` uses multiline descriptions. Output wraps according to the `COLUMNS` environment variable (notably at 80 columns). Every command accepts `-h/--help`, exits 0, and describes exactly the arguments/options and behavior assigned to it in this document. Unknown commands/options and missing arguments use conventional lowercase Clap-style diagnostics, including a `Usage:` line and `For more information, try '--help'.` For example:

```text
error: unrecognized subcommand 'nonexistent'

Usage: executable [OPTIONS] [COMMAND]

For more information, try '--help'.
```

A single global `-v` enables informational tracing. For `-v status` when neither the platform config path nor `./pueue.yml` exists, stderr begins with these four records (each prefixed by a local `HH:MM:SS` timestamp and two spaces) before the structured missing-configuration error:

```text
INFO pueue_lib::settings: Parsing config files
INFO pueue_lib::settings: Checking path: "/root/.config/pueue/pueue.yml"
INFO pueue_lib::settings: Checking path: "./pueue.yml"
INFO pueue_lib::settings: No config file found. Use default config.
```

The `/root` shown here is the invoking user's platform config directory in the observed environment; substitute the corresponding path for another user. The quoted paths, module target, capitalization, and punctuation are exact.

## Spec 3

Configuration is YAML. Selection precedence is an explicit `-c/--config` path, then `PUEUE_CONFIG_PATH`, then `$XDG_CONFIG_HOME/pueue/pueue.yml` (or the platform config directory equivalent), then `./pueue.yml`. An explicit or environment-selected missing file is an error. If no default file exists, fail with `Couldn't find a configuration file. Did you start the daemon yet?`. An explicit CLI path overrides `PUEUE_CONFIG_PATH`.

The accepted top-level mapping has `client`, `daemon`, `shared`, and `profiles`. Unknown fields may follow normal Serde YAML behavior. Relevant defaults and types are:

```text
client.restart_in_place: boolean = false
client.read_local_logs: boolean = true
client.show_confirmation_questions: boolean = false
client.show_expanded_aliases: boolean = false
client.edit_mode: "toml" | "files" = "toml"
client.dark_mode: boolean = false
client.max_status_lines: nonnegative integer or null
client.status_time_format: string = "%H:%M:%S"
client.status_datetime_format: string = "%Y-%m-%d\n%H:%M:%S"

daemon.pause_group_on_failure: boolean = false
daemon.pause_all_on_failure: boolean = false
daemon.compress_state_file: boolean = false
daemon.callback: string or null
daemon.env_vars: string-to-string mapping = {}
daemon.callback_log_lines: nonnegative integer = 10
daemon.shell_command: sequence of strings or null

shared.pueue_directory: path or null
shared.runtime_directory: path or null
shared.alias_file: path or null
shared.use_unix_socket: boolean = true
shared.unix_socket_path: path or null
shared.unix_socket_permissions: nonnegative integer or null
shared.host: string = "127.0.0.1"
shared.port: TCP port accepted as either a numeric YAML scalar or a decimal string = "6924"
shared.pid_path, daemon_cert, daemon_key, shared_secret_path: path or null
profiles: mapping from profile name to a complete nested client/daemon/shared configuration
```

Missing sections and fields take these defaults. A selected profile must exist; otherwise fail with `Couldn't find profile with name "NAME"`. Loading a profile replaces the base client/daemon/shared sections with that profile's sections plus defaults rather than incrementally merging individual base values. Expand a leading `~` in all operational paths. Default `pueue_directory` is the platform local-data directory plus `pueue`; default runtime directory is `$XDG_RUNTIME_DIR` when available and otherwise the Pueue directory; default secret is `pueue_directory/shared_secret`; default alias file is the platform config directory plus `pueue/pueue_aliases.yml`; and a configured Unix socket path is used exactly.

Malformed YAML, duplicate fields, wrong scalar/container types, negative or overflowing unsigned values, and an edit mode other than `toml` or `files` must fail before connecting. Diagnostics begin with `Error:`, include `Failed to read configuration.` when deserialization/opening fails, preserve the YAML parser's field path plus line/column explanation, show a `Location:` referring to `pueue/src/bin/pueue.rs`, and finish with the two standard backtrace hints. In particular, tested errors include `expected a boolean`, `expected usize`, `expected a map`, `expected a sequence`, `expected path string`, `duplicate field \`pueue_directory\``, and `unknown variant \`invalid_mode\`, expected \`toml\` or \`files\``. ANSI color in this error reporter is permitted and expected by exact-output cases; comparisons may remove ANSI and normalize source line numbers.

The numbered causes and their line breaks are part of the diagnostic. After stripping ANSI, opening the absent explicit path `/nonexistent/config.yml` reports:

```text
   0: Failed to read configuration.
   1: I/O error at path "/nonexistent/config.yml" while opening config file:
      No such file or directory (os error 2)
```

For malformed YAML consisting of `client:`, a blank/comment line, `  restart_in_place: false`, and `  - invalid`, the corresponding causes are exactly:

```text
   0: Failed to read configuration.
   1: Error while reading configuration:
      did not find expected key at line 4 column 3, while parsing a block mapping at line 3 column 3
```

A missing selected profile is wrapped rather than reported as a bare cause:

```text
   0: Error while reading configuration:
      Couldn't find profile with name "nonexistent"
```

## Spec 4

For a Unix-socket configuration, open `shared.unix_socket_path`. Before every command exchange authenticate on the new connection: read the raw bytes of `shared.shared_secret_path`; send an unsigned 64-bit big-endian payload length followed by those bytes; then receive an unsigned 64-bit big-endian length and that many bytes. The reply is a UTF-8 daemon protocol-version string. An absent secret reports this single numbered cause, with the expanded path substituted exactly and the OS cause on the following indented line:

```text
   0: I/O error at path "/tmp/env_dir/data/shared_secret" while opening secret file. Did you start the daemon at least once?:
      No such file or directory (os error 2)
```

Thus an explicit `--config /tmp/flag_dir/pueue.yml` that overrides `PUEUE_CONFIG_PATH` names `/tmp/flag_dir/data/shared_secret` in the same template. An absent socket must preserve all three nested causes rather than replacing them with a generic client-unavailable message. They are `Failed to initialize client.`, then `Failed to initialize stream.`, then `I/O error at path "`, the exact expanded socket path, `" while connecting to daemon. Did you start it?:`, a newline, and `      No such file or directory (os error 2)`.

After the handshake, each request and response is framed in the same way: an 8-byte unsigned big-endian length followed by one CBOR payload. CBOR uses Serde's externally tagged enum representation, text map keys, and ordinary strings for paths and RFC-3339 datetimes. Thus a unit request is a CBOR text value such as `"Status"`; a newtype/tuple variant is a one-entry map such as `{ "Remove": [0, 2] }`; and a struct variant is a one-entry map whose value is a field map. Implementations may use any language, but their bytes must decode exactly as these types and field names:

```text
TaskSelection = TaskIds([uint...]) | Group(string) | All
Signal = SigInt | SigKill | SigTerm | SigCont | SigStop

Request =
  Add(AddRequest) | Remove([uint...]) | Switch(SwitchRequest) |
  Stash(StashRequest) | Enqueue(EnqueueRequest) | Start(StartRequest) |
  Restart(RestartRequest) | Pause(PauseRequest) | Kill(KillRequest) |
  Send(SendRequest) | EditRequest([uint...]) | EditRestore([uint...]) |
  EditedTasks([EditableTask...]) | Env(EnvRequest) | Group(GroupRequest) |
  Parallel(ParallelRequest) | Status | Log(LogRequest) | Stream(StreamRequest) |
  Reset(ResetRequest) | Clean(CleanRequest) | DaemonShutdown(ShutdownRequest)

AddRequest = {command:string, path:string, envs:{string:string},
  start_immediately:bool, stashed:bool, group:string,
  enqueue_at:datetime|null, dependencies:[uint...], priority:int|null,
  label:string|null}
SwitchRequest = {task_id_1:uint, task_id_2:uint}
StashRequest/EnqueueRequest = {tasks:TaskSelection, enqueue_at:datetime|null}
StartRequest = {tasks:TaskSelection}
PauseRequest = {tasks:TaskSelection, wait:bool}
KillRequest = {tasks:TaskSelection, signal:Signal|null}
SendRequest = {task_id:uint, input:string}
EnvRequest = Set{task_id:uint,key:string,value:string} | Unset{task_id:uint,key:string}
GroupRequest = Add{name:string,parallel_tasks:uint|null} | Remove(string) | List
ParallelRequest = {parallel_tasks:uint, group:string}
CleanRequest = {successful_only:bool, group:string|null}
ResetTarget = All | Groups([string...]); ResetRequest = {target:ResetTarget}
ShutdownRequest = Emergency | Graceful
StreamRequest = {tasks:TaskSelection, lines:uint|null}
LogRequest = {tasks:TaskSelection, send_logs:bool, lines:uint|null}
EditableTask = {id:uint, command:string, path:string, label:string|null, priority:int}
TaskToRestart = {task_id:uint, original_command:string, path:string,
  label:string|null, priority:int}
RestartRequest = {tasks:[TaskToRestart...], start_immediately:bool, stashed:bool}
```

## Spec 5

Responses use the following externally tagged CBOR variants:

```text
AddedTask({task_id:uint, enqueue_at:datetime|null, group_is_paused:bool})
Edit([EditableTask...])
Status(State)
Log({uint:TaskLogResponse...})
Group({groups:{string:Group...}})
Stream({logs:{uint:string...}})
Success(string)
Failure(string)
Close

TaskLogResponse = {task:Task, output_complete:bool, output:bytes|null}
State = {tasks:{uint:Task...}, groups:{string:Group...}}
Group = {status:"Running"|"Paused"|"Reset", parallel_tasks:uint}
Task = {id:uint, created_at:datetime, original_command:string, command:string,
  path:string, envs:{string:string}, group:string, dependencies:[uint...],
  priority:int, label:string|null, status:TaskStatus}
TaskStatus =
  Locked{previous_status:TaskStatus} |
  Stashed{enqueue_at:datetime|null} |
  Queued{enqueued_at:datetime} |
  Running{enqueued_at:datetime,start:datetime} |
  Paused{enqueued_at:datetime,start:datetime} |
  Done{enqueued_at:datetime,start:datetime,end:datetime,result:TaskResult}
TaskResult = Success | Failed(int) | FailedToSpawn(string) | Killed |
  Errored | DependencyFailed
```

For JSON, externally tagged unit variants become strings and data-bearing variants become one-key objects, e.g. `{"Queued":{"enqueued_at":"..."}}`, `{"Done":{"...":"...","result":"Success"}}`, and `{"Failed":42}` for a failed result. Serialize compact JSON on one line with a trailing newline. Task keys are decimal strings and task/group maps are ordered by numeric ID/name. Datetimes are RFC 3339; under the UTC test environment they resemble `2026-04-21T03:58:00.010173470Z`. Preserve the daemon-provided state exactly except where a command below explicitly filters it or clears environments.

A `Success(text)` prints `text` to stdout and exits 0. A `Failure(text)` prints `text` to stderr and exits 1. `AddedTask`, `Status`, `Log`, `Group`, `Stream`, `Edit`, and `Close` have the specialized handling below.

## Spec 6

`add` syntax is `add [OPTIONS] <COMMAND>...` and supports:

```text
-w, --working-directory PATH
-e, --escape
-i, --immediate
    --follow                 requires --immediate; conflicts with --print-task-id
-s, --stashed               conflicts with --immediate
-d, --delay DELAY           conflicts with --immediate
-g, --group GROUP
-a, --after ID...           repeatable/multi-value dependencies
-o, --priority INTEGER
-l, --label STRING
-p, --print-task-id
--                           ends option parsing
```

At least one command argument is syntactically required, but a single empty-string argument is valid. Without `--escape`, join all command arguments with one ASCII space without changing quotes, newlines, semicolons, pipes, redirections, backslashes, dollar signs, or other content. With `--escape`, POSIX-shell-quote each argument independently only when necessary and then join with spaces; for example `add --escape -- echo test '&' ls` stores `echo test '&' ls`.

The path is the process's current working directory, or the canonical absolute form of `--working-directory`; existing paths containing spaces and hyphens are valid. A nonexistent working directory fails locally with `Failed to canonicalize given working directory path`. Capture the complete environment of the client invocation into `envs`, including values such as `HOME`, `PATH`, `PWD`, and `SHLVL`. Use group `default` when omitted. Send all other supplied metadata exactly; empty or whitespace-only label strings are valid. Negative priorities are accepted when attached to the option, for example `--priority=-17`. When supplied as two arguments, `--priority -17` is instead parsed as an unexpected option: it exits 2 before connecting, begins `error: unexpected argument '-1' found`, suggests `to pass '-1' as a value, use '-- -1'`, and prints the `Usage: executable add [OPTIONS] <COMMAND>...` block. Commands of at least 1,000 characters must not be truncated.

On `AddedTask`, normally print `New task added (id N).`. If the response has an enqueue time, print `New task added (id N). It will be enqueued at TIME`, using the configured time format for today and datetime format otherwise. If `group_is_paused`, append `\nThe group of this task is currently paused!`. With `--print-task-id`, print only `N` and suppress both other notices. With `--follow`, print the add notice to stderr, suppress the paused warning, then follow the new task as in Spec 21.

The daemon assigns IDs starting at 0 and normally increasing; the client must display the returned ID, not invent one. Missing dependencies and groups surface daemon failures verbatim, including `Unable to setup dependencies : task(s) [999] not found` and `Group nonexistent doesn't exists. Use one of these: [...]`. `--immediate` force-starts even in a paused group. `--stashed` and `--delay` may be combined and produce a Stashed task with a non-null enqueue time. Exact parser conflicts include:

```text
error: the argument '--immediate' cannot be used with '--stashed'
error: the argument '--delay <delay>' cannot be used with '--immediate'
error: the following required arguments were not provided:
  --immediate
```

## Spec 7

Delay arguments accepted by `add`, `stash`, and `enqueue` are either a signed integer number of seconds from now or a flexible local-time date expression. Required examples include `1`, `2`, `10 seconds`, `1 hour`, `3h`, `3600s`, `1d`, `1days`, `1 week`, `4 months`, RFC-3339 timestamps, `YYYY-M-D H:M:S`, numeric month/day, and weekday expressions. The informal English-month/AM-PM expression `April 21 2027 3:00 PM` is not accepted: it exits 2 before connecting and reports exactly `error: invalid value 'April 21 2027 3:00 PM' for '--delay <delay>': could not parse as seconds or date expression`, followed by the standard help hint. An invalid expression such as `not-a-valid-delay` is likewise a parser error containing `could not parse as seconds or date expression`.

Convert a successfully parsed delay to an absolute local datetime and send it as `enqueue_at`. Delayed tasks remain Stashed until the daemon reaches that time and then become Queued/runnable. Time display uses `client.status_time_format` when the target date is today, otherwise `client.status_datetime_format`.

## Spec 8

Alias expansion is reflected in daemon state and must be preserved by all client workflows. The configured `shared.alias_file` is YAML mapping a case-sensitive first word to a replacement string. If it is absent, unreadable, or malformed, adding still succeeds without expansion. Only the first whitespace-delimited word is replaced once; arguments and remaining whitespace/content are retained. Alias values may contain quotes, pipes, redirects, shell variables, hyphens, underscores, digits, and compound shell syntax and are inserted literally without client-side environment expansion. State retains the typed text in `original_command` and exposes the expanded text in `command`. Restart and edit send the original form so the daemon can reapply current aliasing. Human status normally shows `original_command`; when `client.show_expanded_aliases` is true it shows `command`.

## Spec 9

Whenever a command accepts IDs plus `--group/-g` and `--all/-a`, select in this precedence: `--all`, then group, then a nonempty explicit ID list, otherwise group `default`. `--group` conflicts with `--all`. Group-wide operations validate the group at the daemon and report `Group NAME doesn't exists. Use one of these: ["default", ...]` on absence.

`group` with no subcommand sends `Group(List)`. Plain output has one line per group in name order: `Group "NAME" (N parallel): running`, `paused`, or `resetting`; JSON (`group -j/--json`) is compact, for example `{"default":{"status":"Running","parallel_tasks":1}}`. `group add NAME [-p|--parallel N]` creates a group (default parallelism supplied by daemon) and prints `New group "NAME" has been created`; duplicate names fail with `Group "NAME" already exists`. `group remove NAME` prints `Group "NAME" has been removed`, but removing `default`, an absent group, or any group still containing tasks fails (`You cannot delete the default group`; `You cannot remove a group, if there're still tasks in it.`). A group with `--parallel 0` is valid and means unlimited.

`parallel [N] [-g|--group GROUP]` sets the limit (default group if omitted) and prints `Parallel tasks setting for group "GROUP" adjusted`. Zero means unlimited. Lowering a limit does not stop currently running tasks. Omitting `N` requests the group list response. `parallel abc` exits 2 with stdout empty and exactly:

```text
error: invalid value 'abc' for '[PARALLEL_TASKS]': invalid digit found in string

For more information, try '--help'.
```

## Spec 10

`stash [OPTIONS] [TASK_IDS]...` and `enqueue [OPTIONS] [TASK_IDS]...` both accept `-g/--group`, `-a/--all`, and `-d/--delay`. `stash` changes only Queued tasks to Stashed (a delay sets their future enqueue time); `enqueue` changes only Stashed tasks to Queued now or schedules them for later. Default selection is all applicable tasks in `default`.

For explicit IDs, partial success uses `MESSAGE: comma-separated-ids` followed, when needed, by `\nThe command failed for tasks: ...`; all-invalid selection is a daemon `Failure`. The exact explicit-ID messages (including the historical wording used for `stash`) are `Stashed tasks have been enqueued: 0` without a delay and `Stashed tasks will be enqueued at TIME: 0` with one. Group/all messages are exactly `All queued tasks of group "G" have been stashd.`, `All queued tasks have been stashed.`, `All stashed tasks of group "G" have been enqueued.`, `All stashed tasks have been enqueued.`, `Enqueue stashed tasks of group G at TIME.`, and `Enqueue all stashed tasks at TIME.` Empty valid group/all selections still succeed with their group/all message; trying to enqueue explicit non-stashed tasks fails for those IDs.

## Spec 11

`start [OPTIONS] [TASK_IDS]...` accepts `-g/--group` and `-a/--all`. With explicit IDs it resumes Paused tasks and force-starts Queued or Stashed tasks, ignoring normal group parallel limits and dependencies; it prints `Tasks have been started/resumed: IDS`. With a group it sets the group Running, resumes its paused tasks, and prints `Group "G" is being resumed.`. With all it does this for all groups and prints `All groups are being resumed.`. Default is group `default`. Starting an already Running/Done or nonexistent explicit task reports it under `The command failed for tasks: ...`.

`pause [OPTIONS] [TASK_IDS]...` accepts `-g/--group`, `-a/--all`, and `-w/--wait`. Explicit IDs pause only Running tasks and print `Tasks have been paused: IDS`. A group/all selection marks the selected group(s) Paused so no new tasks start and prints `Group "G" is being paused.` or `All groups are being paused.`. Without `--wait`, already running tasks become Paused. With `--wait`, they are allowed to finish while no queued task starts. Default is group `default`. Group operations affect no other group.

## Spec 12

`kill [OPTIONS] [TASK_IDS]...` accepts `-g/--group`, `-a/--all`, and `-s/--signal SIGNAL`. Default is the default group. With no explicit signal, selected Running or Paused processes are terminated and ultimately have `Done.result == "Killed"`; killing a group/all also pauses the affected groups. Responses are `Tasks are being killed: IDS`, `All tasks of group "G" are being killed. The group will also be paused!!!`, or `All tasks are being killed. All groups will be paused!!!`. Non-running, queued, completed, and nonexistent explicit IDs fail through `The command failed for tasks: IDS`.

Signals are case-insensitive aliases: SIGINT=`sigint|int|2`, SIGKILL=`sigkill|kill|9`, SIGTERM=`sigterm|term|15`, SIGCONT=`sigcont|cont|18`, and SIGSTOP=`sigstop|stop|19`. Reject all others at parse time. For example, `kill --signal INVALIDSIGNAL 0` exits 2 with stdout empty and exactly:

```text
error: invalid value 'INVALIDSIGNAL' for '--signal <SIGNAL>': Matching variant not found

For more information, try '--help'.
```

A supplied signal is sent to the task's whole process group and bypasses the normal forced-kill transition; SIGSTOP makes a running process stop, SIGCONT resumes it, and INT/TERM normally allow status to become Done. Group/all signal responses begin `Sending signal SigInt`/`SigTerm`/etc. Explicit-ID response remains `Tasks are being killed: IDS`.

`send TASK_ID INPUT` sends the exact string to a running process's stdin and prints `Message is being send to the process.`. It requires exactly these two positional arguments; a non-running or absent task fails. The string is not modified or given an implicit newline.

## Spec 13

`remove` (alias `rm`) requires one or more IDs. It may remove Queued, Stashed, Locked, or Done tasks but not Running/Paused tasks. A task that still has a dependent cannot be removed unless that dependent is also included in the same recursively complete removal set. Successful IDs are deleted with their log files. Output is `Tasks removed from list: IDS`; mixed results append `\nThe command failed for tasks: IDS`; all-invalid results exit 1 with only the latter line.

`switch TASK_ID_1 TASK_ID_2` requires exactly two IDs and only accepts Queued/Stashed tasks. It swaps the complete tasks' IDs/queue positions (so their commands and metadata appear under the opposite IDs) and rewrites dependency references accordingly. Success is `Tasks have been switched`. Switching an ID with itself fails with `You cannot switch a task with itself.`; invalid state/nonexistent IDs fail with `Tasks have to be either queued or stashed.`.

`clean [-s|--successful-only] [-g|--group G]` deletes removable Done tasks, never active tasks. Without `-s`, all Done result kinds qualify; with it, only Success. A group limits the deletion. Exact success templates are `All finished tasks have been removed`, `All successfully finished tasks have been removed`, and either plus ` from group 'G'`. Cleaning must preserve tasks needed as dependencies.

`reset [-g|--groups G]... [-f|--force]` resets every group when none are named or only the named groups otherwise: terminate their processes, remove their tasks/logs, and return groups to an empty usable state. It prints `Everything is being reset right now.`. Unknown groups fail with `Group 'G' doesn't exist.`. When confirmation is enabled and running tasks would be removed, ask unless `--force` was used. `shutdown` sends graceful shutdown, prints `Daemon is shutting down`, and the daemon subsequently stops accepting connections.

## Spec 14

`restart` (alias `re`) accepts optional IDs and:

```text
-a, --all-failed
-g, --failed-in-group GROUP   conflicts with --all-failed
-k, --immediate               conflicts with --stashed
-s, --stashed
-i, --in-place
    --not-in-place
-e, --edit
```

Only Done tasks can restart. With normal IDs, report non-Done/nonexistent IDs as not restartable. With `--all-failed`, select every Done task whose result is not Success; `--failed-in-group` does the same in one group and ignores positional IDs. With neither mode, an empty ID list is a runtime error: `Please provide the ids of the tasks you want to restart.`.

Default behavior is controlled by `client.restart_in_place` (false by default); `--in-place` enables it and `--not-in-place` takes precedence and disables it. A non-in-place restart sends a new Add for each selected task, retaining original command, path, environment, group, label, and priority, clearing dependencies, and giving it a new ID. In-place restart reuses IDs and overwrites old logs. The new state is Queued, or Stashed with `--stashed`; `--immediate` force-starts. `--edit` runs the Spec 15 editor before sending the restart. Reapply aliases from `original_command`. Print `Restarted tasks: [0, 2]` to stdout for successful selections and `Couldn't restart tasks: [1]` to stderr for rejects. Restarting a Running task must not alter it.

## Spec 15

`edit [TASK_IDS]...` uses a three-step exchange. Send `EditRequest(ids)`; the daemon locks and returns editable records only for existing Queued/Stashed tasks. Then invoke the command in `$EDITOR` plus one shell-escaped temporary path. Set `PUEUE_EDIT_PATH` to that path for the editor process. Missing `$EDITOR`, failure to launch, or nonzero editor exit is an error. On any local edit error send `EditRestore(ids)`, print to stderr:

```text
Encountered an error while editing. Trying to restore the task's status.
The requested task ids have been restored their previous state: [IDS]
```

then print the structured error and exit nonzero; original values and state must remain intact.

In `files` mode, pass a temporary directory. For every task ID it contains a subdirectory named with that ID and four files: `command`, `path`, `label`, `priority`. Initial files contain the exact editable values (empty label for null). After editing, trim surrounding whitespace from command/path/label/priority. For task 0, reject an empty command with exactly `Found empty command after edit for task 0` and an empty path with exactly `Found empty path after edit for task 0`; for another task, substitute its decimal number directly after the word `task` without inserting the word `ID`. A non-integer priority file containing `not_a_number\n` reports a two-line quoted value and nested parse cause exactly as follows after ANSI is removed:

```text
   0: Failed to parse priority string 'not_a_number
      ' into an integer for task 0
   1: invalid digit found in string
```

Empty label means null. Signed negative priorities are valid. Preserve every unedited property. A nonzero editor exit uses the exact cause `The editor exited with a non-zero code. Aborting.`; an unset `$EDITOR` uses `The '$EDITOR' environment variable couldn't be read. Aborting.`. These causes follow the two restoration lines and the `Error:` heading shown above.

In `toml` mode, pass a `tasks.toml` file. It is a map with string ID table keys; each table has `id`, `command`, `path`, `label`, and `priority`, and `command` denotes the original command. Parse the edited TOML back into records; malformed TOML is an error beginning `Failed to deserialize tasks to toml:`. On success send `EditedTasks`, restore prior Queued/Stashed status, apply all edits and aliases, and print `All tasks have been updated`. Initial failures are verbatim `No task with this id.` or `You can only edit a queued/stashed task`.

## Spec 16

`env set TASK_ID KEY VALUE` and `env unset TASK_ID KEY` edit the captured environment of Queued or Stashed tasks only. Set creates or overwrites a variable, including an empty or special-character-containing value, and prints `Environment variable set.`. Unset removes an existing key and prints `Environment variable unset.`. Missing tasks print `No task with id N`; active/Done tasks print `You can only edit stashed or queued tasks`; an absent key prints `No environment variable with key 'KEY' found.`. Changes must affect eventual task execution and JSON status. No shell parsing or expansion is applied to values.

## Spec 17

`status [OPTIONS] [QUERY]...` sends `Status`. `-j/--json` emits the State schema from Spec 5. With `--group G`, JSON retains the complete `groups` mapping but filters `tasks` to group G; query filters/order/limit also filter JSON tasks. With no query and no group, emit the state unchanged. JSON must never be polluted by logs, warnings, tables, or ANSI.

Plain status displays one table per group that has selected tasks, with `default` first and other group names alphabetically. A group headline is `Group "NAME" (N parallel): running|paused|resetting`. An entirely empty daemon prints exactly:

```text
Group "default" (1 parallel): running

Task list is empty. Add tasks with `pueue add -- [cmd]`
```

For an explicitly selected existing empty group, use `Task list is empty. Add tasks with \`pueue add -g NAME -- [cmd]\``. In plain mode an unknown group is the unusual nonfatal case: write `There exists no group "NAME"` to stderr, write only a newline to stdout, and exit 0. JSON mode instead exits 0 with empty stderr and emits the normal State object with `tasks` filtered to `{}` and the complete groups map retained; for a default-only daemon this is exactly `{"tasks":{},"groups":{"default":{"status":"Running","parallel_tasks":1}}}\n`.

The default table uses Unicode horizontal-only borders (`─` separator, `═` beneath the header), dynamic widths, one leading/trailing space of cell padding, and columns in this order: `Id Status [Prio] [Enqueue At] [Deps] [Label] Command Path Start End`. Id, Status, Command, Path, Start, End are normally shown. Show Prio if any selected task has nonzero priority, Enqueue At if any has a delayed Stashed state, Deps if any has dependencies, and Label if any has a label. A row is capped at `max_status_lines` when configured. Status labels are `Stashed`, `Queued`, `Running`, `Paused`, `Locked`, `Success`, `Failed (CODE)`, `Failed to spawn`, `Killed`, `Errored`, and `Dependency failed`. Dependencies display comma-space-separated IDs. Today's times use `status_time_format`; older start/end times use `status_datetime_format`; absent values are blank.

## Spec 18

Status query tokens are joined with one space, then parsed case-insensitively for keywords as:

```text
[columns=COLUMN(,COLUMN)*]? FILTER* [order_by COLUMN [asc|desc]]? [first|last COUNT]?
```

Columns are `id,status,command,label,path,enqueue_at,dependencies,start,end`; selection preserves the fixed table column order rather than the textual request order. Filters are ANDed in order:

- `status=VALUE` or `status!=VALUE`, where VALUE is queued, stashed, paused, running, success, or failed. Failed means any Done result other than Success.
- `command=TEXT`, `command!=TEXT`, or `command%=TEXT`; `%=` means substring.
- The same operators for label. A missing label does not equal anything, does satisfy `!=`, and does not contain anything.
- `start`, `end`, or `enqueue_at` with `=`, `!=`, `<`, or `>` and a local `YYYY-MM-DD`, `HH:MM[:SS]`, or `YYYY-MM-DDHH:MM[:SS]` operand. Date equality means strictly within that local day, `<` before its start, and `>` after its end. Tasks lacking that timestamp do not match.

Orderable columns include id, status, command, label, path, enqueue_at, start, and end. Default direction is ascending. Status ascending rank is Stashed, Locked, Queued, Paused, Running, non-success Done, Success; descending reverses it. Null enqueue times sort as far-future; optional start/end/label follow ordinary optional-value ordering. Without `order_by`, retain daemon/numeric-ID order. `first N` keeps the first N; `last N` keeps the last N without reversing them. Zero/invalid queries fail clearly. Filters, ordering, and limits determine which tasks are selected in both table and JSON modes. Table rows preserve the query order. A JSON State is always reserialized as the numeric-ID-ordered map required by Spec 5, so query order is not observable in its key order: `order_by id desc first 2` over IDs 0 through 4 selects 4 and 3 but emits keys `"3"` then `"4"`; `order_by status asc` without a limit still emits the selected keys in numeric ID order.

## Spec 19

`log [OPTIONS] [TASK_IDS]...` accepts `-g/--group`, `-a/--all`, `-j/--json`, `-l/--lines N`, and `-f/--full`; lines conflicts with full. Selection defaults to group `default`. The effective line count is all lines with `--full`, explicit N with `--lines`, otherwise the last 15. Zero lines yields no task output. IDs/logs are processed in ascending ID order regardless of the order typed.

Send `LogRequest{tasks, send_logs: !client.read_local_logs, lines}`. When reading locally, read `pueue_directory/task_logs/ID.log`; stdout and stderr from the task share this file in their observed write order. When remote, `TaskLogResponse.output` is a Snappy framed stream and must be decompressed. Missing local files produce a clear `Failed to get log file handle` diagnostic but do not crash.

For plain output, only Done, Running, or Paused tasks are printed. For each, metadata goes to stderr: a Unicode box headed `Task ID: STATUS`, then Command, Path, optional Label, and RFC-2822 Start/End rows. Human statuses include `completed successfully`, `failed with exit code N`, `Failed to spawn`, `killed by system or user`, `dependency failed`, `running`, and `paused`. For local logs, if output is nonempty, stderr then contains a blank line and `output:` (or `output: (last N lines)` when genuinely truncated), while raw log bytes go to stdout. For remote logs (`client.read_local_logs: false`), that blank line and label are instead prefixed to stdout immediately before the decompressed bytes. For example, a complete remote payload `remote one\nremote two\n` produces stdout exactly `\noutput:\nremote one\nremote two\n`, while stderr contains only the metadata box and rows. Multiple printable tasks are separated by one blank stdout line. A single three-line local task therefore has exactly those three lines on stdout; default long output returns the last 15 lines, and `--full` returns all. Preserve arbitrarily long UTF-8 output and mixed stdout/stderr markers.

No matching explicit IDs is nonfatal: stdout empty, stderr `There are no finished tasks for your specified ids`, exit 0. Corresponding messages are `There are no finished tasks for group 'G'` and `There are no finished tasks` for group/all. JSON is a compact ID-keyed map `{ID:{"task":TASK,"output":"TEXT"}}`; clear each returned task's `envs` to `{}` to avoid leaking secrets, omit the response's `output_complete`, and place truncated text without a final newline when the line-reader strips it.

## Spec 20

`follow` (alias `fo`) syntax is `follow [-l|--lines N] [TASK_ID]`. It streams only task log text to stdout and exits after the task finishes. It may be called for a Queued/Stashed task and waits for it to start. It can also show the complete existing output of a Done task. `--lines N` seeks to the last N existing lines before streaming new bytes. Stdout and task stderr remain merged.

When `client.read_local_logs` is true, poll state, then tail `pueue_directory/task_logs/ID.log` approximately every 250 ms while periodically querying state. When false, send a `StreamRequest`; print each `Stream.logs` chunk immediately, stop at `Close`, and treat a streamed Failure as fatal. If no ID is supplied, auto-select exactly one Running or Paused task; zero produces `There are no running tasks.`, multiple produces `Multiple tasks are running, please select one of the following: IDS`. A nonexistent requested task exits 1 with `Pueue: The task to be followed doesn't exist.`. If its file/task disappears during follow, report that fact and terminate cleanly or nonzero as indicated by the message, never hang.

## Spec 21

`wait [OPTIONS] [TASK_IDS]...` accepts `-g/--group`, `-a/--all`, `-q/--quiet`, and `-s/--status STATUS`, where STATUS is case-sensitive aliases `done|Done`, `success|Success`, `queued|Queued`, or `running|Running`. Other values are parser errors. Default selection is all tasks currently and subsequently discovered in `default`; `--all` covers every group, and IDs cover those IDs. Continue discovering tasks added while a group/all wait is active. Removed watched tasks no longer block completion.

Targets are milestone semantics: Queued is reached by Queued, Running, or Done; Running by Running or Done; Done only by Done; Success only by Done/Success. When waiting for Success, any other Done result exits 1. Done without `--status success` exits 0 for Success, Failed, Killed, FailedToSpawn, Errored, or DependencyFailed. Stashed/Paused/Locked tasks continue blocking until their target is reached or they disappear.

`--quiet` produces no stdout status lines. Otherwise, print current local `HH:MM:SS` progress. Initially print only active tasks as `TIME - Found active Task ID with status STATUS`. Later-discovered tasks print `TIME - New task ID with status STATUS`; nonterminal transitions print `TIME - Task ID changed from OLD to NEW`. A transition to terminal Done output does not print that generic transition line; it prints only the applicable completion line: `Task ID succeeded with 0`, `failed with CODE`, `failed due to failed dependencies`, `failed to spawn`, `has been killed`, or `experienced an IO error.`. Thus a task observed first as Running and then as Done/Success produces `TIME - Found active Task 1 with status Running` followed by `TIME - Task 1 succeeded with 0`, with no `Task 1 changed from Running to Success` line. Poll around 250 ms when `PUEUED_TEST_ENV_VARIABLE` exists and around two seconds otherwise. If selection currently yields no tasks, write `No tasks found for selection TaskIds([999])` (or the analogous debug-form Group/All selection) to stderr and exit 0.

## Spec 22

Color behavior applies to human status, group, log metadata, wait messages, and daemon failure text. `--color never` emits no `ESC [` sequences. `--color always` emits ANSI even when stdout/stderr is captured; group names are bold, Running/Success green, Queued/Stashed yellow, Paused/Locked white, and failures red. `auto` enables style only when stdout is a terminal. `client.dark_mode` selects dark green/red/yellow variants. JSON is always uncolored.

Runtime failures created by the client use a structured color-eyre-like report:

```text
Error: 
   0: MESSAGE

Location:
   pueue/src/...:LINE

Backtrace omitted. Run with RUST_BACKTRACE=1 environment variable to display it.
Run with RUST_BACKTRACE=full to include source snippets.
```

Nested errors use numbered lines 0, 1, etc. Color the message bright red and location magenta in the default reporter. Daemon `Failure` strings, by contrast, are printed directly without the `Error:` wrapper (red only when output color is enabled). Never panic or emit a language traceback for malformed user input, missing configuration, unavailable daemon, invalid editor data, or absent IDs.

## Spec 23

Completion generation is `completions <SHELL> [OUTPUT_DIRECTORY]`, with possible shell values in this order: `bash`, `elvish`, `fish`, `power-shell`, `zsh`, `nushell`. An invalid value exits nonzero and says `invalid value` plus `possible values:`. Without a directory, write a complete nonempty completion definition to stdout. With a directory, stdout is empty and exactly one shell-appropriate file is created there; a nonexistent output directory fails. Names include `pueue.bash`, `pueue.fish`, and `_pueue` for Bash, Fish, and Zsh.

Definitions are deterministic and generated from the complete CLI grammar/descriptions in this document. The Bash output begins `_pueue() {`, initializes `local i cur prev opts cmd` and `COMPREPLY=()`, and dispatches `pueue__add`, `pueue__clean`, `pueue__completions`, and all other commands. Fish begins `# Print an optspec for argparse to handle cmd's options that are independent of any subcommand.` and defines `__fish_pueue_global_optspecs`. Zsh begins `#compdef pueue`, blank line, `autoload -U is-at-least`, and `_pueue() {`. PowerShell begins with a blank line, `using namespace System.Management.Automation`, and registers an argument completer for `pueue`. Elvish begins with a blank line then `use builtin;` and `use str;`. Nushell begins `module completions {` and defines the color completer plus externs for every command. For the fixed 4.0.4 command metadata, generated UTF-8 character counts are exactly 43,549 for Bash, 24,233 for Fish, and 34,366 for Zsh.

## Spec 24

The following integration invariants must hold across commands because they are directly observable through the supplied daemon:

- Commands and all task metadata survive client invocations exactly; IDs and environments are never confused during rapid additions/status queries.
- Groups are independent queues. Pausing, starting, killing, setting parallelism, or selecting one group must not affect another. Parallel value zero means unlimited.
- Same-priority queued work is FIFO. Higher numeric priority is chosen before lower priority once a slot is free. Explicit dependencies block execution until every dependency succeeds; any failed dependency produces Done/DependencyFailed. Dependency lists are sorted and deduplicated by the daemon and visible in state.
- `--immediate` and explicit `start ID` force a task despite group pause, parallel limits, and dependencies. A normal task added to a paused group stays Queued and produces the warning in Spec 6.
- Captured environments and later `env` edits are used by the task process; working directories are honored; shell operators and quoting execute according to the daemon-provided shell.
- Control commands return only after the requested state manipulation has been accepted/applied enough for an immediate status query to observe it. Process completion and kill cleanup may still require brief polling.
- Human output must remain suitable for tests that inspect exact text, line counts, Unicode table borders, ANSI presence/absence, and stdout-versus-stderr separation. Machine JSON must remain valid, compact, complete according to its schema, and free of unrelated diagnostics.
