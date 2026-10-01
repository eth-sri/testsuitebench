# Clarified executable specification

The deliverable is one executable named `executable`. In the examples below it is
called `dstask`; that is only the program name printed in user-facing text. The
executable is a persistent, Git-backed command-line task manager. Arguments are
individual operating-system argument strings, all text is UTF-8, and behavior must
be preserved across separate invocations.

In exact-output blocks, `<ESC>` means the single byte `0x1b`, not the five printed
characters. Unless explicitly noted, every diagnostic and ordinary line ends in
`\n`.

## Spec 1

Repository selection, initialization, and process I/O work as follows.

- Use `DSTASK_GIT_REPO` when it is present and nonempty. Otherwise use
  `$HOME/.dstask`. Resolve a relative value against the process working directory
  and normalize it to an absolute repository path. Paths containing spaces,
  Unicode, or shell-special characters are ordinary paths and must work without
  interpretation. Never mix data or local state between repositories.
- An existing selected directory must be a Git repository. If it is merely an
  ordinary directory, fail with status 1 and a diagnostic containing
  `Failed to create directory in git repository`.
- If the selected directory does not exist and output is noninteractive, create it,
  run the equivalent of `git init` (with branch `master`), and continue. If terminal
  mode is active, first print text containing `Could not find dstask repository` and
  ask to create it. A case-insensitive, whitespace-trimmed `y` or `yes` creates it;
  creation output must contain `Initialized empty Git repository`. EOF at this
  particular prompt reproduces the command's panic behavior: exit 2 and include
  `panic: EOF`. The environment variable `DSTASK_FAKE_PTY=1` forces terminal mode
  even when streams are captured for commands that have a terminal renderer;
  command-specific exceptions such as `show-resolved` are stated below.
- After automatically creating a repository with no remote, stdout includes
  `Add a remote repository with:` and a useful `git remote add` hint.
- `help`, `version`, and the three shell-script-generating completion commands do
  not require a repository. Normal command errors go to stderr, are wrapped as
  `<ESC>[31mMESSAGE<ESC>[0m\n`, and exit 1 unless another rule says otherwise.
- Successful mutation/status messages go to stdout. Help always goes to stderr and
  leaves stdout empty. Completion scripts and version information go to stdout.
- Git identity is not invented by the program. If a mutation cannot commit because
  Git has no user identity, exit nonzero and include `failed to commit changes` on
  stderr. A hook-rejected commit exits 1 and its stderr contains the hook's own
  output followed by the red diagnostic
  `error: failed to commit changes: exit status 1`.
- Git is a required external command. If it cannot be found on `PATH`, exit 1 and
  include `git required, please install`. If a required state directory such as
  `pending/` is blocked by a non-directory filesystem entry, exit 1 and include the
  underlying `not a directory` detail; do not crash or partially create a task.

## Spec 2

Each task has these externally visible fields, in this JSON order:

```json
{
  "uuid": "a UUID string",
  "status": "pending",
  "id": 1,
  "summary": "text",
  "notes": "",
  "tags": [],
  "project": "",
  "priority": "P2",
  "created": "2026-09-10T12:34:56.123456789Z",
  "resolved": "0001-01-01T00:00:00Z",
  "due": "0001-01-01T00:00:00Z"
}
```

The statuses are `pending`, `active`, `paused`, `resolved`, and `template`.
Priority is exactly one of `P0`, `P1`, `P2`, `P3`, from most to least important;
the default is `P2`. Missing project and notes are empty strings, missing tags are
an empty array, and unset times use the exact zero timestamp shown above.

New tasks receive a fresh RFC 4122 version-4 UUID (canonical lowercase
`8-4-4-4-12` hexadecimal form), a current UTC `created` timestamp, zero `resolved`
and `due` times, and the lowest positive ID not used by any open or template task.
UUID and `created` never change. IDs remain stable through pending/active/paused
transitions and modifications. Resolving sets the JSON ID to 0 and releases the
short ID for immediate reuse; removing or undoing creation also releases it.
Different tasks, including copies of a template, always get different UUIDs.

Tags and projects are Unicode-safe and are normalized to lowercase. Task tags are
sorted alphabetically and deduplicated, preserving all otherwise valid punctuation
such as `-`, `_`, `.`, `@`, and Unicode. Summaries, notes, long strings, whitespace,
quotes, shell metacharacters, and Unicode are stored as data without execution or
arbitrary truncation.

## Spec 3

Tasks are actual files in the selected Git work tree, so external edits and normal
Git commands can observe them.

- A task is stored as `<uuid>.yml`. Pending tasks live in `pending/`, paused tasks
  in `paused/`, active tasks in `active/`, resolved tasks in `resolved/`, and
  templates in `template/`. State changes move the file as necessary.
- YAML contains at least these editable keys: `summary`, `notes`, `tags`, `project`,
  `priority`, `delegatedto`, `subtasks`, `dependencies`, `created`, `resolved`, and
  `due`. Generated task files omit `status`; status is inferred from their
  directory. Empty scalar fields are emitted as `""` and empty lists as `[]`; in
  particular a new file contains the literal lines `notes: ""`, `tags: []`,
  `project: ""`, and `priority: P2`. Plain-safe nonempty summaries are emitted as
  unquoted scalars (for example, `summary: First task`), while quoting/block style
  is used where YAML requires it. The `created`, `resolved`, and `due` timestamps
  are likewise unquoted, for example `resolved: 2026-09-17T16:38:11.233448637Z`.
  Multiline/quoted YAML must round trip correctly. Status is also inferred from the
  directory when an externally supplied status is absent or unrecognized.
- Local short-ID and context state is repository-specific and persists beneath
  `.git/dstask/`. Adding a task creates a nonempty `ids.bin`; `state.bin` is absent
  until a context has been saved, after which it is nonempty. These files are not
  task data and are not committed.
- On every load, ignore hidden files. A candidate filename must be a canonical
  hexadecimal UUID plus `.yml`; malformed names are skipped with stderr containing
  `filename does not encode UUID` and the filename. For a filename of the wrong
  length, the filename is immediately followed by ` (wrong length)`, as in
  `filename does not encode UUID invalid-uuid-short.yml (wrong length)`. Malformed
  YAML is skipped with `failed to unmarshal` and the filename. An empty summary is
  loaded, and an unknown YAML status is replaced by the status inferred from the
  containing directory. Priorities outside P0-P3 are invalid; log
  `error loading task: invalid priority specified` and continue loading other
  records. Duplicate UUIDs are loaded once, and short-ID collisions are reassigned
  to distinct lowest-free IDs.

## Spec 4

Command-line parsing is intentionally flexible but deterministic.

- Recognized commands are `next`, `add`, `template`, `log`, `start`, `note`,
  `notes`, `stop`, `done`, `resolve`, `context`, `modify`, `edit`, `undo`, `sync`,
  `open`, `git`, `remove`, `rm`, `show-next`, `show-projects`, `show-tags`,
  `show-active`, `show-paused`, `show-open`, `show-resolved`, `show-templates`,
  `show-unorganised`, `bash-completion`, `fish-completion`, `zsh-completion`,
  `_completions`, `help`, and `version`.
- `show-next` is an alias of `next`, `rm` of `remove`, `resolve` of `done`, and
  `notes` of `note`.
- With no recognized command, use `next`. Thus no arguments means `next`, and an
  unknown word is a case-insensitive text filter rather than an invalid-command
  error. Command recognition itself is case-insensitive: for example, `ADD` routes
  to `add` and, without a description, fails with
  `task description or template required`.
- IDs may precede the command (`1 2 done`) or immediately follow it (`done 1 2`).
  Consecutive decimal integers are consumed as IDs only until the first non-ID
  token; a later integer is ordinary text. Command and ID order therefore does not
  alter routing. ID-addressed queries ignore context.
- Remove every standalone `--` from parsing and set “ignore context.” It is not a
  conventional end-of-options marker: `add hello -- world` creates summary
  `hello world`. It may occur before or after the command.
- Before note mode, recognize `+tag`, `-tag`, `project:name`, `+project:name`,
  `-project:name`, `P0` through `P3`, `priority:P0` through `priority:P3`,
  `template:N`, and the due operators in Spec 10. Operators may appear anywhere
  among summary words. The exact uppercase tokens P0-P3 are case-sensitive; `p1`,
  `P4`, `P-1`, and other unknown priority-like words remain summary text.
- The first recognized project operator and first recognized priority token win;
  later project/priority-looking tokens remain ordinary text. For example,
  `add P1 P2 P3` creates priority P1 and summary `P2 P3`, and
  `add project:foo project:bar` creates project `foo` and summary `project:bar`.
  Multiple due operators in one query fail with
  `Query should only have one due date`.
- A standalone `/` enters note mode. Words before it form the space-joined summary;
  all later arguments are joined with single spaces into notes and are never parsed
  as operators. `/` with no later words means an empty note. A slash embedded in an
  argument, URL, or path is ordinary text.

## Spec 5

`add [template:N] [summary/operators] [--]` creates one pending task. A non-template
add needs nonempty summary text; otherwise fail with
`task description or template required`. On success commit it and print exactly
`Added ID: SUMMARY` as the first operation line.

Positive tags, project, priority, and due date are applied. Anti-tags remove matching
tags from a copied template; an anti-project removes a matching copied project.
Duplicate tags collapse. A task can contain dozens of tags and very long text.

`log [summary/operators] [--]` uses the same creation grammar but requires a summary
(`task description required` on failure), creates the task directly as resolved,
sets both current timestamps, gives it JSON ID 0, excludes it from open lists, and
prints `Logged SUMMARY`.

`start [IDs] [optional note]` starts existing tasks. With no IDs, non-operator text
instead creates a new task using add syntax and immediately makes it active. With
neither IDs nor a usable description, fail with
`nothing to do -- specify an ID or describe a task`. `start template:N` fails with
`templates not yet supported for start command`. When this form creates a task,
its operation line and commit subject are exactly
`Added and started ID: SUMMARY`.

Creation commands normally merge the active context: positive context tags are
added, and context project/priority/due become defaults. Explicit tags are added to
context tags. Conflicting nonempty project, priority, or due values fail respectively
with `Could not apply q2, project conflict`,
`Could not apply q2, priority conflict`, or
`Could not apply q2, date filter conflict`. `--` bypasses both inheritance and
conflict checks. Anti-tags and anti-projects in a context are filters only and do not
become task attributes.

## Spec 6

Lifecycle transitions and operation output are:

- `start ID... [note]`: pending or paused to active; print and commit
  `Started ID: SUMMARY` once per task.
- `stop ID... [note]`: active to paused; print and commit
  `Stopped ID: SUMMARY` once per task.
- `done|resolve ID... [closing note]`: pending, active, or paused to resolved; set
  `resolved` to the current UTC time, set external ID to 0, and print/commit
  `Resolved OLD_ID: SUMMARY` once per task.

When note text follows any of these commands, prepend one `\n` separator and append
the text even when the existing notes are empty. Thus starting a task whose notes
are empty with the text `note 7` stores `\nnote 7`. Multiple IDs are processed in
command-line order and receive separate commits. All other task fields and the UUID
are preserved.

The valid state edges are pending→active, pending→resolved, pending→template,
active→paused, active→resolved, paused→active, and paused→resolved. Repeating
`start ID` for an already-active task is a special successful no-op: it prints
`Started ID: SUMMARY`, then `No changes detected`, leaves the task active, creates
no commit, and exits 0. Other invalid edges fail status 1 with
`invalid state transition: FROM -> TO`. A resolved task is not addressable by its
old short ID and produces `no open task with ID N exists`.

Before resolving, scan notes for GitHub-style unchecked checklist items `- [ ]`.
If any exist, refuse with
`refusing to resolve task with incomplete tasklist`. Items marked `- [x]` or
`- [X]` are complete and do not block resolution.

## Spec 7

`modify ID... OPERATORS` changes tags, project, priority, and due date on each named
open task. It may add/remove tags case-insensitively, set a project, clear it with
`-project:CURRENT`, set priority, and set/change due. An empty `project:` token is
ignored: by itself it fails as `no operations specified` and preserves the current
project; if followed by `project:ignored`, that later nonempty token is the first
effective project operation and sets project `ignored`. Operators are normalized as
in Spec 2; removing an absent tag is a successful no-op. The first nonempty project
operator and the first priority operator win. More than one due operator fails.
Changing attributes on a task with nonempty notes also appends one newline to the
notes (`notes` becomes `notes\n`). Preserve summary, status, UUID, and creation time,
and preserve other fields except for that notes newline. Successful stdout begins
with a blank line, so `Modified ID: SUMMARY` is its second line. Print and commit
that operation separately for every task.

Adjacent tag removals retain the reference implementation's iteration behavior. If
a task has `tag1`, `tag2`, and `tag3`, then
`modify 1 -tag2 -tag3 +tag4 +tag5` removes `tag2` but skips the now-adjacent
`tag3`, producing exactly `tag1`, `tag3`, `tag4`, and `tag5`.

No operators gives the exact error `<ESC>[31mno operations specified<ESC>[0m\n`.
A nonexistent ID gives `no open task with ID N exists`.

With no IDs, `modify` targets every task matching the current context. In terminal
mode stderr asks the single prompt
`no IDs specified. Apply to all N tasks in current ctx? [y/n] `; there is no
separate `Continue?` text. Only trimmed, case-insensitive `y` or `yes` proceeds.
Every other answer (including empty input) prints the red diagnostic `Aborted.`,
exits 1, and changes nothing.

`remove|rm ID... [comment]` permanently deletes each named open task file and
releases its ID. It commits each deletion with subject `Removed: ID: SUMMARY`;
optional plain text is included in the commit message. It first prints
`ID: SUMMARY`, then a blank line and `Removed: ID: SUMMARY`. In
terminal mode, first report the number as `N task(s)` and ask
`Continue? [y/n]` on stderr. Confirmation parsing and abort behavior are identical
to bulk modify. Nonterminal removal proceeds without prompting. With no IDs the
exact error is `<ESC>[31mno ID(s) specified<ESC>[0m\n`.

## Spec 8

Commands that address existing tasks apply only to open/template tasks. For any
required ID that is unavailable, fail with
`no open task with ID N exists`. Explicit-ID `next`, `show-next`, and default-command
queries are exceptions: they silently omit unavailable and template IDs, and an
invocation such as `next 999` with no matching open task succeeds with `[]`.
`done`, `edit`, `note`, `open`, `remove`, and
`stop` require at least one ID; absent IDs fail with `no ID(s) specified`.
`done`, `edit`, `note`, `open`, `remove`, and `stop` reject tag/project/priority/due
operators with `operators not valid in this context`. `next` with both explicit IDs
and operators fails with `operators not valid when addressing task by ID`.

`note|notes ID... [text]` behaves by output mode:

- In nonterminal mode with no text, write the raw notes bytes to stdout, with no
  decoration and no added newline. Empty notes produce empty stdout.
- In terminal mode with text, append the exact text to every named task, separating
  old and new notes by one newline. Whitespace-only, multiline, Unicode, quotes,
  paths, and metacharacters are preserved. Commit each as
  `Edit note ID: SUMMARY`.
- In terminal mode with no text, open the task notes in the configured editor.

`edit ID...` serializes each task as editable YAML using the scalar styles described
in Spec 3, invokes the command in `$EDITOR`
(split into program and arguments, then append the temporary filename; use a
reasonable system editor if unset), reloads and validates the result, applies valid
status/file moves, and commits `Edited ID: NEW_SUMMARY`. Multiple tasks are edited
and committed separately. A no-change editor exit is a successful no-op. Changes to
summary, notes, tags, project, priority, due, or a valid status transition persist;
UUID and creation time remain unchanged. Resolved tasks cannot be edited by old ID.

`open ID...` extracts HTTP/HTTPS URLs from each task's summary and notes and launches
them with the platform browser opener. If none are found, fail with
`no URLs found in task N`.

## Spec 9

The current context is a persistent query.

- `context` with no operands prints only the current query string followed by `\n`;
  an empty context therefore prints exactly one newline. A successful context
  mutation prints nothing: `context none` clears it with empty stdout, and any
  other operand-bearing invocation replaces, rather than extends, the old context
  with empty stdout. A later operand-free `context` prints the saved, normalized
  query. Printable context normalizes case, preserves duplicate tags, resolves
  relative due dates to absolute `YYYY-MM-DD`, and orders due before priority. For
  example, setting `+Ctx +CTX project:MyProj P1 due:tomorrow` on 2026-09-17 has
  empty stdout; the subsequent `context` prints
  `+ctx +ctx project:myproj due:2026-09-18 P1`.
- A context may contain positive/negative tags, one positive project, multiple
  anti-projects, one priority, one due/date filter, and a `template:N` criterion.
  `context template:1` succeeds with empty stdout; a subsequent operand-free
  `context` prints `template:1`. It is a query criterion and does not make later
  creation copy that template. A context may not contain IDs or free text: fail
  with `context cannot contain IDs` or `context cannot contain text`.
- Tags and projects match case-insensitively and print/store lowercase forms.
- The saved context persists in `.git/dstask/state.bin`. It filters `next`,
  status-based task lists, resolved/template lists, and creation as described above.
  `--` ignores it for that invocation. Explicit ID lookup always ignores it.
- If `DSTASK_CONTEXT` is nonempty, parse its whitespace-separated value and use it
  in place of saved context for every command. An empty value is treated as though
  the variable were unset, so it neither overrides saved context nor prevents
  `context none` from clearing it. Attempts to change context under a nonempty
  environment context fail with
  `setting context not allowed while DSTASK_CONTEXT is set`.
- Whenever a nonempty context affects an ordinary command, print a yellow line on
  stdout: `<ESC>[33mActive context: QUERY<ESC>[0m`. For the environment form use
  `<ESC>[33mActive context (set by DSTASK_CONTEXT): QUERY<ESC>[0m`. Do not prefix
  machine-readable JSON with this line; context descriptions are shown for
  mutation/TTY output. Template creation itself stays minimal and need not print
  the description.

## Spec 10

Task queries combine every supplied criterion with logical AND.

- `+x` requires tag x; `-x` excludes tag x. Multiple positive tags all must be
  present. `project:x` requires that project; `-project:x` excludes it. `P0`…`P3`
  require exact priority.
- Remaining text is a case-insensitive substring search over both summary and notes.
  Multiple remaining words are joined with spaces before matching.
- Due dates are stored at midnight UTC and accepted as `YYYY-MM-DD`, `MM-DD`
  (current year), `DD` (current year/month), case-insensitive `today`, `yesterday`,
  `tomorrow`, any full weekday name, `this-WEEKDAY`, and `next-WEEKDAY`. A bare or
  `this-` weekday means its first occurrence on or after today; `next-` means the
  occurrence in the following week.
- `due:DATE` and `due.on:DATE` match exactly; `due.before:DATE` and
  `due.after:DATE` are inclusive comparisons, so a task due exactly on the boundary
  matches either. `due:overdue` means a nonzero due date on or before today, so a
  task due today is included. `due.in:DATE` is accepted and behaves as a date-scoped filter.
  The same `due:DATE` grammar sets dates during add/template/log/modify.
- `due.before:` and `due.after:` may not be used by `add`; fail exactly with
  `<ESC>[31mcannot use date filter with add command<ESC>[0m\n`. `due.on:` and
  `due.in:` are accepted by add.
- An empty due value fails with exactly:

```text
<ESC>[31mInvalid due date format: 
Expected format: YYYY-MM-DD, MM-DD or DD, relative date like 'next-monday', 'today', etc.<ESC>[0m
```

- An unknown dotted filter, e.g. `due.wrongfilter:...`, fails with:

```text
<ESC>[31mInvalid date filter format: wrongfilter
Valid filters are: after, before, on, in<ESC>[0m
```

Calendar-invalid values and nonexistent weekdays fail status 1. A token such as
plain `due` with no colon is ordinary search/summary text.

## Spec 11

Templates are normal task-shaped records with status `template` and their own live
short IDs.

- `template SUMMARY/operators` creates a new template and prints/commits
  `Created Template ID: SUMMARY`.
- `template ID...` converts each pending task in order, preserving ID, UUID and
  attributes, and prints/commits `Changed ID: SUMMARY to Template`. Active→template
  fails with `invalid state transition: active -> template`. If one conversion in a
  multi-ID command fails, previously completed conversions remain committed, the
  failing task is not converted, and later work may stop.
- `show-templates [filter] [--]` is the only ordinary list containing templates.
  `next` and `show-open` never contain them.
- `add template:ID` copies the referenced template into a new pending task. With no
  summary it copies the template summary; supplied summary replaces it. Notes, tags,
  project, priority, and due are copied, then supplied additions/removals/overrides
  are applied. As a serialization quirk, copying a nonempty source note with no note
  override appends one newline: `template notes` becomes `template notes\n` in the
  copy. The source template is unchanged. A missing/zero template behaves as
  no usable template and produces the appropriate missing-summary or missing-ID
  error.
- Copying a non-template open task is allowed but stdout also contains
  `You've copied an open task!` and
  `To learn more about creating templates` plus `dstask help template`.
- `modify` can modify a template by its ID. Context inheritance and `--` apply to
  template creation, and template filtering supports the ordinary query grammar.

## Spec 12

Nonterminal task-list output is JSON. This is the mode used whenever stdout is not a
terminal and `DSTASK_FAKE_PTY` is not `1`. `--json` is accepted but does not override
terminal selection: `next --json` under `DSTASK_FAKE_PTY=1` still uses the ANSI
terminal detail/table renderer. Emit a JSON array, with each task using the complete
schema and types in Spec 2. Every empty JSON list is exactly the two bytes `[]`, with
no trailing newline.

- `next`/`show-next`: all pending, active, and paused tasks, subject to query/context.
- `show-open`: the same three open statuses without terminal truncation.
- `show-active`, `show-paused`, `show-resolved`, `show-templates`: only that status,
  still subject to filters/context. `show-resolved` is a special case that ignores
  `DSTASK_FAKE_PTY=1`: with captured/non-TTY stdout it still emits JSON despite that
  variable. A real stdout TTY selects its terminal report.
- `show-unorganised`: global open tasks having both no tags and no project. It rejects
  explicit IDs or query operators with `query/context not used for show-unorganised`.
- Explicit IDs with `next`, `show-next`, or the default command return the requested
  open (pending/active/paused) records in the ordinary priority/creation sort order,
  not argument order, and bypass context. Thus, for two P2 tasks created as IDs 1
  then 2, both `2 1 next` and `next 2 1` return IDs 1 then 2. Template and
  unavailable IDs are silently omitted; for example, after task 2 is converted to
  a template, `next 2 1` returns only task 1.

Sort open/template output by priority P0→P3 and then creation time oldest-first;
when priorities are equal this preserves creation/ID order. Resolved output is
oldest-resolution-first and is limited to the latest 1000 records where relevant.
Nonterminal filtering to no records succeeds with `[]`.

`show-tags` is deliberately plain text even in nonterminal mode: print each unique
tag used by a non-resolved, non-template task once, one tag per line. Exclude tags
that exist only on resolved tasks and emit empty output when there are none.

`show-projects` rejects explicit IDs or query operators with
`query/context not supported for show-projects`. In nonterminal mode it returns a
JSON array sorted by lowercase project name. Include fully resolved projects. Each
object is:

```json
{
  "name": "website",
  "taskCount": 2,
  "resolvedCount": 1,
  "active": false,
  "created": "RFC3339 earliest creation time",
  "resolved": "RFC3339 latest resolution time or zero time",
  "priority": "P0"
}
```

`taskCount` includes open and resolved tasks, `active` is true if any member is
active, and project priority is the best (lowest-numbered) priority among unresolved
members. Empty project data is `[]`.

## Spec 13

Terminal list rendering is selected by a real stdout TTY or
`DSTASK_FAKE_PTY=1`. The fake terminal is 80 columns; all tables clamp any wider
terminal to 160 columns. Use Unicode display-cell width (East Asian wide characters
occupy two cells), two spaces between columns, and truncate cells without an
ellipsis. Determine natural column widths, then repeatedly reduce the currently
widest column until the row plus gaps fits. A table must never hang even if columns
shrink to zero.

For zero total tasks, `next` and `show-open` print exactly:

```text
No tasks found. Run `dstask help` for instructions.
```

If tasks exist but a terminal query matches none, exit 1 with `No matching tasks`.
One matching task uses a two-column `Name  Value` detail table with rows ID,
Priority, Summary, Status, Project, Tags, UUID, Created, and (only when nonzero) Due.
Tags are sorted and joined by comma-space, for example `a, z`. Created/Due use Go-style UTC display such as
`2026-04-13 00:00:00 +0000 UTC`. If notes are nonempty, append:

```text

Notes on task N:
<ESC>[38;5;245mNOTES<ESC>[0m

```

The reset immediately follows the final note byte, with no inserted newline
between `NOTES` and `<ESC>[0m`; two newline bytes follow the reset.

Two or more tasks use columns `ID`, `Priority`, `Tags`, `Due`, `Project`, `Summary`.
Due uses `today`, `yesterday`, or `tomorrow` for those three dates; other dates in
the current year use `D Mon` without a leading zero, and dates in another year use
`D Mon YYYY`, such as `1 Jan 2020`. Tags are alphabetically sorted and
space-separated; project is the bare name. After the rows print a blank line and
`N tasks.`. A height-limited list may instead print `SHOWN/TOTAL tasks shown.`, must
show at least eight tasks, and must never truncate nonterminal JSON.

ANSI style is exact: header `<ESC>[4;38;5;250;48;5;232m`; normal rows use mode 0,
P0/P1/P2/P3 foregrounds 160/166/250/245 and alternating backgrounds 233, 232.
Overdue tasks use foreground 166. Paused rows use background 236. Active rows use
background 250 and foreground 124 for P0, 130 for P1, and 233 for ordinary active
tasks. Every styled row ends `<ESC>[0m`. A literal ` / ` inside a displayed summary
is removed and switches the remainder to foreground 240, then restores the row's
foreground before reset. Slashes in URLs, paths, or `10/5` do not trigger it.

As an exact 80-column reference, after adding in order
`Test task with normal length summary`, the long summary shown below, the Unicode
task below, and `Task with / note keyword P0 +urgent +work`, `next` prints (the long
second summary is `Very long summary that should be truncated when the terminal width is limited and we need to test the column width reduction algorithm`):

```text
<ESC>[4;38;5;250;48;5;232mID  Priority  Tags         Due  Project  Summary                                <ESC>[0m
<ESC>[0;38;5;160;48;5;233m4   P0        urgent work                Task with<ESC>[38;5;240m note keyword                 <ESC>[38;5;160m<ESC>[0m
<ESC>[0;38;5;250;48;5;232m1   P2                                   Test task with normal length summary   <ESC>[0m
<ESC>[0;38;5;250;48;5;233m2   P2                                   Very long summary that should be trunc <ESC>[0m
<ESC>[0;38;5;250;48;5;232m3   P2                                   Unicode test: 日本語テスト ☕ café     <ESC>[0m

4 tasks.
```

If a terminal filter hides unresolved P0 tasks, append in foreground 160:
`N critical task(s) outside this context! Use \`dstask -- P0\` to see them.`.
Do not count resolved/templates or P0 tasks already visible. `show-projects` in TTY
mode uses `Name  Progress  Created`, progress `resolved/total`, date like
`Sun 12 Apr 2026`, hides fully resolved projects, and gives projects with active
tasks foreground 233/background 250. Other terminal status lists use the same task
rendering. On a real stdout TTY, `show-resolved` groups records by ISO week with
headings of the form `> Week N, starting DAY D Mon YYYY`, as observed in
`> Week 38, starting Thu 17 Sep 2026`. When terminal behavior is requested only by
`DSTASK_FAKE_PTY=1` while stdout remains captured, `show-resolved` instead emits the
JSON array described in Spec 12 and no week heading.

## Spec 14

Every successful data mutation is staged and committed in the selected real Git
repository, leaving a clean work tree. Commit subjects are the operation lines
specified above (`Added`, `Added and started`, `Started`, `Stopped`, `Resolved`,
`Modified`, `Edited`, `Created Template`, `Changed ... to Template`, `Edit note`,
`Removed`, or `Logged`), including ID/summary where specified. Multi-task operations
make one commit per task. Git hooks run normally and a rejecting hook causes the
command to fail. When an operation produces no filesystem difference, treat it as a
successful no-op: do not attempt an empty commit and leave the repository clean.

`git ARGS...` runs the installed `git` command in the selected repository with all
arguments and stdin passed through and stdout/stderr observable. It must support all
normal Git operations (status, log, diff, show, branch, tag, config, remote, etc.) and
return Git's failure as nonzero with a diagnostic containing
`Failed to run git cmd`. With no useful args, command-specific help may be shown.

`sync` performs `git pull` followed, only on success, by `git push`. It supports
up-to-date, pull-only, push-only, and divergent merge cases. Pass Git's messages
through. Missing tracking information or an unreachable remote exits 1, retains a
usable repository, and includes `Failed to run git cmd` plus Git's own explanation.

`undo [N]` defaults to one and creates N Git revert commits, newest target first; it
must not reset or erase history. The work-tree task view immediately reflects the
reverts and subsequent mutations continue normally. `undo 1` is valid. Trying to
undo beyond history exits nonzero and exposes `Failed to run git cmd` and Git's
`fatal: bad revision`. A nonnumeric argument exits successfully after printing the
exact undo help from Spec 15 to stderr.

Failures from corrupt Git objects/index/config are nonzero rather than crashes.
Include `error: failed to run git commit` for an unreadable objects directory,
`error: failed to add changes to repo` for a failed add, and the underlying error
detail/exit status.

## Spec 15

`version` ignores extra context and prints exactly these three stdout lines, with no
stderr:

```text
Version: Unknown
Git commit: Unknown
Build date: Unknown
```

`help [topic...]` uses only the first topic, exits 0, writes only stderr, and matches
topics exactly and case-sensitively. Aliases use canonical help (`resolve`→`done`,
`notes`→`note`, `rm`→`remove`; zsh/fish completion help→bash completion help).
Unknown, empty, numeric, partial, malformed, `version`, `show-tags`, `show-active`,
`show-paused`, `show-open`, and `show-unorganised` topics use general help.

The exact general help is:

```text
Usage: dstask [id...] <cmd> [task summary/filter]

Where [task summary] is text with tags/project/priority specified. Tags are
specified with + (or - for filtering) eg: +work. The project is specified with
a project:g prefix eg: project:dstask -- no quotes. Priorities run from P3
(low), P2 (default) to P1 (high) and P0 (critical). Text can also be specified
for a substring search of description and notes.

Cmd and IDs can be swapped, multiple IDs can be specified for batch
operations.

run "dstask help <cmd>" for command specific help.

Add -- to ignore the current context. / can be used when adding tasks to note
any words after.

Available commands:

next              : Show most important tasks (priority, creation date -- truncated and default)
add               : Add a task
template          : Add a task template
log               : Log a task (already resolved)
start             : Change task status to active
note              : Append to or edit note for a task
stop              : Change task status to pending
done              : Resolve a task
context           : Set global context for task list and new tasks (use "none" to set no context)
modify            : Change task attributes specified on command line
edit              : Edit task with text editor
undo              : Undo last n commits
sync              : Pull then push to git repository, automatic merge commit.
open              : Open all URLs found in summary/annotations
git               : Pass a command to git in the repository. Used for push/pull.
remove            : Remove a task (use to remove tasks added by mistake)
show-projects     : List projects with completion status
show-tags         : List tags in use
show-active       : Show tasks that have been started
show-paused       : Show tasks that have been started then stopped
show-open         : Show all non-resolved tasks (without truncation)
show-resolved     : Show resolved tasks
show-templates    : Show task templates
show-unorganised  : Show untagged tasks with no projects (global context)
bash-completion   : Print bash completion script to stdout
fish-completion   : Print fish completion script to stdout
zsh-completion    : Print zsh completion script to stdout
help              : Get help on any command or show this message
version           : Show dstask version information

Colour Key:
<ESC>[0;38;5;160;48;5;232mCritical priority        <ESC>[0m
<ESC>[0;38;5;166;48;5;232mHigh priority            <ESC>[0m
<ESC>[0;38;5;250;48;5;233mNormal priority          <ESC>[0m
<ESC>[0;38;5;245;48;5;232mLow priority             <ESC>[0m
<ESC>[0;38;5;233;48;5;250mActive                   <ESC>[0m
<ESC>[0;38;5;250;48;5;236mPaused                   <ESC>[0m
```

The command-specific help bodies are exact:

```text
== add ==
Usage: dstask add [template:<id>] [task summary] [--]
Example: dstask add Fix main web page 500 error +bug P1 project:website

Add a task, returning the git commit output which contains the task ID, used
later to reference the task.

Tags, project and priority can be added anywhere within the task summary.

Add -- to ignore the current context. / can be used when adding tasks to note
any words after.

A copy of an existing task can be made by including "template:<id>". See
"dstask help template" for more information on templates.

== next ==
Usage: dstask next [filter] [--]
Usage: dstask [filter] [--]
Example: dstask +work +bug --

Display list of non-resolved tasks in the current context, most recent last,
optional filter. It is the default command, so "next" is unnecessary.

Bypass the current context with --.

Colour key:
<ESC>[0;38;5;160;48;5;232mCritical priority        <ESC>[0m
<ESC>[0;38;5;166;48;5;232mHigh priority            <ESC>[0m
<ESC>[0;38;5;250;48;5;233mNormal priority          <ESC>[0m
<ESC>[0;38;5;245;48;5;232mLow priority             <ESC>[0m
<ESC>[0;38;5;233;48;5;250mActive                   <ESC>[0m
<ESC>[0;38;5;250;48;5;236mPaused                   <ESC>[0m

== modify ==
Usage: dstask <id...> modify <filter>
Usage: dstask modify <filter>
Example: dstask 34 modify -work +home project:workbench -project:website

Modify the attributes of the given tasks, specified by ID. If no ID is given,
the operation will be performed to all tasks in the current context subject to
confirmation.

Modifiable attributes: tags, project and priority.

== context ==
Usage: dstask context <filter>
Example: dstask context +work -bug
Example: dstask context none

Set a global filter consisting of a project, tags or antitags. Subsequent new
tasks and most commands will then have this filter applied automatically.

For example, if you were to run "task add fix the webserver," the given task
would then have the tag "work" applied automatically.

To reset to no context, run: dstask context none

Context can also be set with the environment variable DSTASK_CONTEXT. If set, 
this context string will override the context stored on disk.

== done ==
Usage: dstask <id...> done [closing note]
Example: dstask 15 done
Example: dstask 15 done replaced some hardware

Resolve a task. Optional text may be added, which will be appended to the note.

== edit ==
Usage: dstask <id...> edit

Edit a task in your text editor.

== git ==
Usage: dstask git <args...>
Example: dstask git status

Run the given git command inside ~/.dstask

== log ==
Usage: dstask log [task summary] [--]
Example: dstask log Fix main web page 500 error +bug P1 project:website

Add an immediately resolved task. Syntax identical to add command.

Tags, project and priority can be added anywhere within the task summary.

Add -- to ignore the current context.

== note ==
Usage: dstask note <id>
Usage: dstask note <id> <text>
Example task 13 note problem is faulty hardware

Edit or append text to the markdown notes attached to a particular task.

== open ==
Usage: dstask <id...> open

Open all URLs found within the task summary and notes. If you commonly have
dozens of tabs open to later action, convert them into tasks to open later with
this command.

== remove ==
Usage: dstask remove <id...>
Example: dstask 15 remove

Remove a task.

The task is deleted from the filesystem, and the change is committed.

== show-projects ==
Usage: dstask show-projects

Show a breakdown of projects with progress information

== show-resolved ==
Usage: dstask resolved

Show a report of last 1000 resolved tasks.

== show-templates ==
Usage: dtask show-templates [filter] [--]

Show a report of stored template tasks with an optional filter.

Bypass the current context with --
== start ==
Usage: dstask <id...> start
Usage: dstask start [task summary] [--]
Example: dstask 15 start
Example: dstask start Fix main web page 500 error +bug P1 project:website

Mark a task as active, meaning you're currently at work on the task.

Alternatively, "start" can add a task and start it immediately with the same
syntax is the "add" command.  Tags, project and priority can be added anywhere
within the task summary.

Add -- to ignore the current context.

== stop ==
Usage: dstask <id...> stop [text]
Example: dstask 15 stop
Example: dstask 15 stop replaced some hardware

Set a task as inactive, meaning you've stopped work on the task. Optional text
may be added, which will be appended to the note.

== sync ==
Usage: dstask sync

Synchronise with the remote git server. Runs git pull then git push. If there
are conflicts that cannot be automatically resolved, it is necessary to
manually resolve them in  ~/.dstask or with the "task git" command.

== undo ==
Usage: dstask undo
Usage: dstask undo <n>

Undo the last <n> commits on the repository. Default is 1. Use

	dstask git log

To see commit history. For more complicated history manipulation it may be best
to revert/rebase/merge on the dstask repository itself. The dstask repository
is at ~/.dstask by default.

== completion help (bash, zsh, or fish topic) ==
Usage: dstask [bash|zsh|fish]-completion

Print a shell completion script to stdout. The script can be sourced from
a user's .bashrc, .zshrc, or fish.config like so:

    source <(dstask bash-completion)
    source <(dstask zsh-completion)
    dtask fish-completion | source
```

The template topic is:

```text
Usage dstask template <id> [task summary] [--]
Example: dstask template Fix main web page 500 error +bug P1 project:website
Example: dstask template 34 project:

If valid task ID is supplied, a copy of the task is created as a template. If
no ID is given, a new task template is created.

Tags, project and priority can be added anywhere within the task summary.

Add -- to ignore the current context. / can be used when adding tasks to note
any words after

Template tasks are not displayed with "show-open" or "show-next" commands.
Their intent is to act as a readily available task template for commonly used
or repeated tasks.

To create a new task from a template use the command:
"dstask add template:<id> [task summary] [--]"
The template task <id> remains unchanged, but a new task is created as a copy
with any modifications made in the task summary.

Github-style task lists (checklists) are recommended for templates, useful for
performing procedures. Example:

- [ ] buy bananas
- [ ] eat bananas
- [ ] make coffee
```

The `add`, `log`, `remove` (and its `rm` alias), and `template` help outputs end in
two consecutive newline bytes. Every other displayed help block ends with one
newline except `show-templates`, whose exact body ends immediately after `--`.

## Spec 16

The shell completion script commands ignore extra arguments, exit 0, write no
stderr, and print exactly the following stdout (each ends with a newline).

`bash-completion`:

```bash
# wire bash completions to dstask completion engine. Some of the workarounds for
# idiosyncrasies around separation with colons taken from /etc/bash_completion

_dstask() {
    # reconstruct COMP_WORDS to re-join separations caused by colon (which is a default separator)
    # yes, this method ends up splitting by spaces, but that's not a problem for the dstask parser
    # see http://tiswww.case.edu/php/chet/bash/FAQ
    original_args=( $(echo "${COMP_WORDS[@]}" | sed 's/ : /:/g' | sed 's/ :$/:/g') )

    # hand to dstask as canonical args
    COMPREPLY=( $(dstask _completions "${original_args[@]}") )

    # convert dstask's suggestions to remove prefix before colon so complete can understand it
    local last_arg="${original_args[-1]}"
    local colon_word=${last_arg%"${last_arg##*:}"}
    local i=${#COMPREPLY[*]}
    while [[ $((--i)) -ge 0 ]]; do
        COMPREPLY[$i]=${COMPREPLY[$i]#"$colon_word"}
    done
}

complete -F _dstask dstask
complete -F _dstask task
#complete -F _dstask n
#complete -F _dstask t
```

`zsh-completion`:

```text
#compdef dstask
#autoload


_dstask() {
    compadd -- $(dstask _completions "${words[@]}")
}

compdef _dstask dstask
```

`fish-completion`:

```text
#!/usr/bin/env fish

complete -f -c dstask -a (echo (dstask _completions) | string collect)
#complete -f -c task -a (echo (task _completions) | string collect)
#complete -f -c t -a (echo (t _completions) | string collect)

```

`_completions` is the internal line-oriented completion engine. Its arguments are
the shell words including the executable word; filter candidates by the prefix in
the final word, and suppress candidates already supplied. It completes command
names, priorities, tags from current open tasks as both `+tag` and `-tag`, and
projects as both `project:name` and `-project:name`. It works on an empty repository.
With `_completions dstask` in an empty repository, stdout is exactly:

```text
next
add
rm
remove
template
log
start
note
notes
stop
done
resolve
context
modify
edit
undo
sync
open
git
show-next
show-projects
show-tags
show-active
show-paused
show-open
show-resolved
show-templates
show-unorganised
bash-completion
fish-completion
zsh-completion
help
version
P0
P1
P2
P3
```

For a final prefix `sh`, output the nine `show-*` entries above in that order. For
prefix `+w` with tag `work`, output `+work`. For prefix `project:` with projects
`myapp` and `webapp`, output those two `project:` forms alphabetically. If `+work`
has already been supplied and the final prefix is `+`, suggest every other matching
tag but not `+work`. Suggestions are unique and newline-terminated.
