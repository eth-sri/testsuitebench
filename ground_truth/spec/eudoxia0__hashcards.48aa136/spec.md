# Hashcards executable specification

The required artifact is a native command-line program named exactly `executable`. It implements a Markdown-backed flashcard collection, an SQLite progress database, JSON inspection commands, and a local HTTP drilling interface. Unless a rule below says otherwise, successful commands exit with status 0, failures caused by collection data or I/O exit with status 1, and command-line syntax errors exit with status 2. Standard output and standard error must remain separate as specified. Text is UTF-8.

## Spec 1

The top-level command-line interface is case-sensitive and has these subcommands:

- `drill`: drill cards through a web interface.
- `check`: check the integrity of a collection.
- `stats`: print collection statistics.
- `orphans`: manage database cards that are no longer in the collection.
- `export`: export the collection and progress data.
- `help`: print top-level or subcommand help.

Invoking `executable` without arguments is a syntax error: it exits 2 with empty stdout and prints the complete concise top-level help shown below to stderr, beginning `A plain text-based spaced repetition system.`; it does not print a missing-argument diagnostic. `-h` and `--help` print that help to stdout and `-V` and `--version` print exactly `hashcards 0.3.0\n`; these operations leave stderr empty and succeed. The first line of top-level help is `A plain text-based spaced repetition system.` and its command list and option descriptions use the wording above. Its usage line is `Usage: executable <COMMAND>`. Unknown commands, misspelled or differently-cased commands, misplaced options, and unknown options produce a conventional command-line parser error on stderr containing `error: unrecognized subcommand` or `error: unexpected argument` as appropriate, a `Usage:` line, and `For more information, try '--help'.`; stdout is empty. Help takes precedence when it is the first top-level option, so `executable --help --anything` still prints help successfully. A literal `--` ends option processing and makes subsequent text a positional argument. Global `--version` is not accepted after a subcommand.

`executable help` is equivalent to top-level help, and `executable help stats` is equivalent to `executable stats --help`. `executable help --help` is not recursively interpreted as a help request; it is a syntax error reporting an unrecognized subcommand. The concise top-level help has this logical content and ordering:

```text
A plain text-based spaced repetition system.

Usage: executable <COMMAND>

Commands:
  drill    Drill cards through a web interface
  check    Check the integrity of a collection
  stats    Print collection statistics
  orphans  Commands relating to orphan cards
  export   Export a collection
  help     Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version
```

## Spec 2

The command shapes and defaults are as follows. Optional `DIRECTORY` always defaults to the current working directory.

- `check [DIRECTORY]`
- `stats [--format html|json] [DIRECTORY]`, with `html` as the default. There is no `-f` alias.
- `export [--output PATH] [DIRECTORY]`
- `orphans list [DIRECTORY]`
- `orphans delete [DIRECTORY]`
- `drill [OPTIONS] [DIRECTORY]`

The help outputs for check, export, and stats are exactly the following, including indentation, blank lines, and final newline:

```text
Check the integrity of a collection

Usage: executable check [DIRECTORY]

Arguments:
  [DIRECTORY]  Path to the collection directory. By default, the current working directory is used

Options:
  -h, --help  Print help
```

```text
Export a collection

Usage: executable export [OPTIONS] [DIRECTORY]

Arguments:
  [DIRECTORY]  Path to the collection directory. By default, the current working directory is used

Options:
      --output <OUTPUT>  Optional path to the output file. By default, the output is printed to stdout
  -h, --help             Print help
```

```text
Print collection statistics

Usage: executable stats [OPTIONS] [DIRECTORY]

Arguments:
  [DIRECTORY]
          Path to the collection directory. By default, the current working directory is used

Options:
      --format <FORMAT>
          Which output format to use

          Possible values:
          - html: HTML output
          - json: JSON output
          
          [default: html]

  -h, --help
          Print help (see a summary with '-h')
```

The orphans help is exactly:

```text
Commands relating to orphan cards

Usage: executable orphans <COMMAND>

Commands:
  list    List the hashes of all orphan cards in the collection
  delete  Remove all orphan cards from the database
  help    Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help
```

Its nested usages are `executable orphans list [DIRECTORY]` and `executable orphans delete [DIRECTORY]`, with the corresponding descriptions from that listing. Omitting the nested command is a status-2 syntax error with empty stdout; stderr is the complete orphans help block shown above, beginning `Commands relating to orphan cards`, rather than a missing-argument diagnostic.

Drill accepts these long options: `--card-limit INTEGER`, `--new-card-limit INTEGER`, `--host STRING` (default `127.0.0.1`), `--port INTEGER` (default `8000`, valid unsigned 16-bit port), `--from-deck STRING`, `--open-browser true|false`, `--answer-controls full|binary` (default `full`), and `--bury-siblings true|false`. Invalid enumerations or numeric values are status-2 argument errors. In particular, nonnumeric ports and values above 65535 are rejected, and `-1` is parsed as an unexpected option-like argument. Drill help names all of these options and defaults, displays `[default: 127.0.0.1]`, `[default: 8000]`, and `[default: full]`, lists `true`/`false` and `full`/`binary` as possible values, and describes full mode as showing `all four rating buttons (Forgot/Hard/Good/Easy)`.

The following status-2 validation cases have empty stdout and exactly these stderr strings:

- `stats -f html`: `error: unexpected argument '-f' found\n\n  tip: to pass '-f' as a value, use '-- -f'\n\nUsage: executable stats [OPTIONS] [DIRECTORY]\n\nFor more information, try '--help'.\n`
- `drill -1`: `error: unexpected argument '-1' found\n\n  tip: to pass '-1' as a value, use '-- -1'\n\nUsage: executable drill [OPTIONS] [DIRECTORY]\n\nFor more information, try '--help'.\n`
- `drill --port wat`: `error: invalid value 'wat' for '--port <PORT>': invalid digit found in string\n\nFor more information, try '--help'.\n`
- `drill --port 70000`: `error: invalid value '70000' for '--port <PORT>': 70000 is not in 0..=65535\n\nFor more information, try '--help'.\n`
- `stats --format` with no value: `error: a value is required for '--format <FORMAT>' but none was supplied\n  [possible values: html, json]\n\nFor more information, try '--help'.\n`
- `export --output` with no value: `error: a value is required for '--output <OUTPUT>' but none was supplied\n\nFor more information, try '--help'.\n`

## Spec 3

All collection commands resolve the selected directory to its canonical absolute path. If it does not exist, stdout is empty, the command exits 1, and stderr is exactly:

```text
hashcards: error: directory does not exist.
```

Collection state is stored in `<collection>/hashcards.db`. Opening any valid collection command initializes this SQLite file if it is absent. Separate directories have completely independent databases. The database must be owner-readable and owner-writable. Existing database contents must not be rewritten merely by `check`, `stats`, `export`, or `orphans list`; in particular those read-only operations preserve the bytes of an already-created database when there is nothing to change. An invalid or corrupt database produces a clean status-1 diagnostic beginning `hashcards: error:` rather than a crash or traceback.

Collection loading walks the directory recursively. Only paths whose target is a regular file and whose extension is exactly lowercase `.md` are decks; other files and uppercase/mixed-case extensions are ignored. Hidden paths are not inherently excluded, and `.gitignore` has no special meaning. Multiple filesystem paths that yield identical cards do not cause duplicate cards in the loaded collection. Symlink traversal must not enable files outside the canonical collection to be served over HTTP (see Spec 19).

An existing ordinary file supplied in place of a directory also exits 1 cleanly. Because database opening is attempted at `<that file>/hashcards.db`, use this exact debug-style error shape (substitute the actual canonical path):

```text
hashcards: error: rusqlite: SqliteFailure(
    Error {
        code: CannotOpen,
        extended_code: 14,
    },
    Some(
        "unable to open database file: <actual file path>/hashcards.db",
    ),
)
```

A database file containing non-SQLite data fails with exactly:

```text
hashcards: error: rusqlite: SqliteFailure(
    Error {
        code: NotADatabase,
        extended_code: 26,
    },
    Some(
        "file is not a database",
    ),
)
```

A symlink whose path itself ends in `.md` and whose target is a regular Markdown file may be read, but directory symlinks are not recursively followed; duplicate resulting content is still removed by hash and broken links are skipped without looping.

## Spec 4

A root-level file named `macros.tex` supplies optional TeX macros. Each physical line is independently considered. Ignore lines whose first non-whitespace character is `%` and lines containing no literal ASCII space. On every remaining line, the text before the first space is the macro name and the remainder is its definition. This is intentionally only a split rule, not semantic TeX validation: a whitespace-only physical line that contains a space is counted, while a truly empty line is not. These macros are exposed to the browser-side math setup and the number of accepted lines is the `texMacroCount` statistic. An absent, zero-byte, or comment-only file supplies zero macros.

Deck names normally equal the Markdown filename stem, retaining Unicode, spaces, hyphens, and internal dots. A file can override the name with TOML frontmatter only when its very first trimmed line is `---`; a leading blank line means the apparent block is ordinary card text, not frontmatter. Frontmatter continues through the next line whose trimmed contents are exactly `---`. Its supported optional field is a string `name`; unknown fields are ignored, an empty block is valid, and an explicitly empty name is valid. A missing closing delimiter produces exactly `hashcards: error: Frontmatter opening '---' found but no closing '---'\n`. Invalid TOML is reported as `Failed to parse TOML frontmatter:` followed by the TOML parser location/detail. In particular, the frontmatter body `date: 2025-01-01` produces exactly:

```text
hashcards: error: Failed to parse TOML frontmatter: TOML parse error at line 1, column 7
  |
1 | date: 2025-01-01
  |       ^
key with no value, expected `=`
```

The displayed detail line is followed by an empty line: the exact stderr ends with two consecutive newline bytes.

Other YAML-style constructs such as `name: Test` are likewise invalid. Card source line numbers restart at zero after a valid frontmatter block.

## Spec 5

Deck bodies are parsed as a small line-oriented language. Only uppercase markers beginning in column zero are recognized: `Q:`, `A:`, and `C:`. The remainder of a marker line is trimmed at both ends. Lowercase markers and markers preceded by whitespace are ordinary continuation text. A line whose trimmed content is exactly `---` is a flashcard separator; it is unrelated to frontmatter after body parsing starts. Repeated separators and separators before the first or after the last card are harmless.

In the idle state, arbitrary prose, headings, comments, blank lines, and separators are ignored. `Q:` begins a basic card's question. Ordinary following lines, including blank ones and Markdown, are joined to it with newline characters exactly as written. `A:` begins its answer, whose continuation lines are accumulated the same way. A new `Q:` or `C:`, a separator, or end of file finishes a complete question/answer card. The whole accumulated question and answer are each trimmed, so outer whitespace does not affect content, while internal whitespace, tabs, newlines, and Markdown do. Empty question and answer strings are legal when the two required markers are present. The final line need not end in a newline, and CRLF input behaves like equivalent LF input.

`C:` begins a cloze prompt; its continuation lines are joined by newlines and the result is outer-trimmed. A new `Q:` or `C:`, a separator, or end of file finishes it. Transition markers immediately start the next card.

## Spec 6

Malformed card state produces a status-1 parse diagnostic, no stdout, and no partial collection result. Its complete shape is:

```text
hashcards: error: Parse error: <reason> Location: <absolute deck path>:<one-based line>
```

Use these reasons for the corresponding conditions:

- `Found answer tag without a question.` for `A:` while idle.
- `New question without answer.` for `Q:` while still reading a question.
- `Found cloze tag while reading a question.` for `C:` while reading a question.
- `Found flashcard separator while reading a question.` for a separator before the answer.
- `File ended while reading a question without an answer.` for EOF before the answer marker.
- `Found answer tag while reading an answer.` for a second answer marker.
- `Found answer tag while reading a cloze card.` for an answer marker in a cloze prompt.
- `Cloze card must contain at least one cloze deletion.` when a finished cloze prompt has no completed deletion.

The location line is the line on which the invalid marker or separator occurs, the original question line for a question left open at EOF, and the `C:` line for a cloze with no deletion. Collection/database initialization may already have occurred before parsing fails, but no parsed cards are inserted by ordinary read-only commands.

## Spec 7

Cloze deletions are denoted by unescaped square brackets, with one logical card generated for every completed, non-nested bracketed deletion in the prompt. The stored cloze text is the prompt with the deletion delimiters removed. All cards from one prompt share this clean text but have different inclusive deletion offsets. Offsets are zero-based UTF-8 byte offsets in the clean text, not character indices. For example:

```text
C: Foo [bar] baz [quux].
```

creates two cloze cards with text `Foo bar baz quux.` and offsets `(4,6)` and `(12,15)`. `C: ab[cd]ef` has `(2,3)`. `\[` and `\]` represent literal brackets: the escaping backslash is removed and the bracket is not a cloze delimiter. Brackets belonging to Markdown image syntax such as `![alt](image.png)` remain literal and do not form a deletion; other ordinary bracket pairs do. Empty and nested bracket constructs must be handled successfully without a crash or invalid JSON response, although consumers should use the non-nested syntax for predictable offsets. Inputs support multiline prompts and Unicode correctly.

Every parsed card has a source location containing the deck's canonical absolute path and a zero-based `(lineStart,lineEnd)`. `lineStart` is its `Q:` or `C:` body line. When another marker or separator terminates the card, `lineEnd` is that terminating line's index; at EOF it is the final body-line index. Thus a two-line `Q:`/`A:` card beginning on line 2 has `(2,3)`, and continuation/blank lines expand the range.

## Spec 8

Card identity is content-addressed with BLAKE3 and represented as a lowercase 64-character hexadecimal string. Hash the following byte concatenations with no separators:

- Basic card: UTF-8 `Basic`, followed by the trimmed question bytes, followed by the trimmed answer bytes.
- Cloze card: UTF-8 `Cloze`, followed by the clean prompt bytes, followed by the start offset encoded as an unsigned 64-bit little-endian integer, followed by the inclusive end offset encoded the same way.
- Cloze family hash: UTF-8 `Cloze` followed by the clean prompt bytes.

Basic cards have no family hash. Deck name and location are deliberately absent from all hashes. After loading every file, deduplicate by card hash across the whole collection and sort cards by ascending raw hash (equivalently ascending lowercase hash string). Consequently moving or duplicating unchanged content does not create a second card, while an internal content change usually does. Outer question/answer/prompt whitespace is already normalized as described in Spec 5.

## Spec 9

Collection loading validates local media referenced by Markdown image syntax `![alt](destination)` in either side of a basic card and in clean cloze text. Ordinary Markdown links `[text](destination)` are not media and need not exist. Trim surrounding whitespace from a destination before resolving it.

A destination beginning `@/` is relative to the collection root. Its remainder must be relative, contain no `..` traversal component, exist, and canonically remain in the collection. Other relative destinations are based on the source deck's parent directory; `..` is permitted only if the canonical result remains inside the collection. Absolute paths, external/URL-like paths containing `://`, paths escaping the collection, and missing paths are invalid. If the literal path does not exist, percent-decode it as UTF-8 and retry, so a reference such as `my%20image.png` can resolve `my image.png`.

Report all distinct missing/invalid references together, sorted deterministically by displayed path and then source, in this shape:

```text
hashcards: error: Missing media files referenced in cards:
  - <decoded destination> (referenced in <absolute deck path>:<zero-based card start line>)
  - <another destination> (referenced in <absolute deck path>:<line>)
```

The diagnostic ends with a newline and exits 1 with empty stdout. Display `@/` references with that prefix, and use decoded human-readable text where percent decoding was attempted. An empty image destination is reportable. This common validation applies to check, stats, export, orphan operations, and drill.

## Spec 10

The SQLite connection enables foreign keys and initializes these strict tables (equivalent SQL types and constraints must be observably identical):

```sql
CREATE TABLE cards (
  card_hash TEXT PRIMARY KEY,
  added_at TEXT NOT NULL,
  last_reviewed_at TEXT,
  stability REAL,
  difficulty REAL,
  interval_raw REAL,
  interval_days INTEGER,
  due_date TEXT,
  review_count INTEGER NOT NULL
) STRICT;
CREATE TABLE sessions (
  session_id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT NOT NULL
) STRICT;
CREATE TABLE reviews (
  review_id INTEGER PRIMARY KEY,
  session_id INTEGER NOT NULL REFERENCES sessions(session_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  card_hash TEXT NOT NULL REFERENCES cards(card_hash)
    ON UPDATE CASCADE ON DELETE CASCADE,
  reviewed_at TEXT NOT NULL,
  grade TEXT NOT NULL,
  stability REAL NOT NULL,
  difficulty REAL NOT NULL,
  interval_raw REAL NOT NULL,
  interval_days INTEGER NOT NULL,
  due_date TEXT NOT NULL
) STRICT;
```

Use local naive timestamps formatted `YYYY-MM-DDTHH:MM:SS.mmm`, dates formatted `YYYY-MM-DD`, and lowercase grade strings `forgot`, `hard`, `good`, or `easy` in storage. Preserve externally inserted IDs, full-precision floating values, integer intervals/counts, timestamps, and dates when reading/exporting. A card's exported performance is present only if all six nullable performance columns (`last_reviewed_at`, `stability`, `difficulty`, `interval_raw`, `interval_days`, `due_date`) are non-null; if any is null, performance is JSON null. `review_count` itself is non-null in the table.

## Spec 11

`check` fully opens the database, parses every deck, deduplicates cards, and validates media and macros. On success it prints exactly `ok\n` to stdout, nothing to stderr, and exits 0. Empty collections and collections containing only unrelated files are valid. It does not synchronize parsed cards into the `cards` table.

`stats --format json` performs the same validation and prints a pretty, two-space-indented JSON object followed by a newline, with keys in this order:

```json
{
  "cardsInDeckCount": 0,
  "cardsInDbCount": 0,
  "texMacroCount": 0,
  "cardsReviewedTodayCount": 0
}
```

The values are respectively: unique parsed card count, row count in `cards`, accepted macro-line count, and count of rows in `reviews` whose `reviewed_at` date portion is today's local date. `stats` does not insert deck cards into the database. Default or explicit `--format html` still loads and validates the collection, then exits successfully with empty stdout and exactly `HTML output is not implemented yet.\n` on stderr. The accepted equals form `--format=html` has exactly the same behavior. Formats other than the two listed choices are status-2 CLI errors.

## Spec 12

`export` emits a pretty, two-space-indented JSON object with top-level keys `cards` then `sessions`. Without `--output`, it writes that JSON plus a final newline to stdout. With `--output PATH`, it creates or overwrites the named file and suppresses stdout; it does not create missing parent directories. The option may occur after the positional directory: `export DIRECTORY --output PATH` is accepted and behaves identically. Output-file failures are status 1 and begin `hashcards: error: I/O error:`. When `PATH` names an existing directory, stderr includes the Rust I/O variant line `kind: IsADirectory,`. The output path is not opened if collection loading fails. The empty representation is:

```json
{
  "cards": [],
  "sessions": []
}
```

Cards are the sorted, deduplicated in-deck cards, whether or not they have a database row. Each card object has fields in this order:

```json
{
  "hash": "<card hash>",
  "familyHash": null,
  "deckName": "<deck name>",
  "location": {
    "filePath": "<canonical absolute Markdown path>",
    "lineStart": 0,
    "lineEnd": 1
  },
  "content": {"basic": {"question": "...", "answer": "..."}},
  "performance": null
}
```

For cloze cards, `familyHash` is the separately computed family hash from Spec 8 and content is `{"cloze":{"text":"...","start":N,"end":N}}`. For a fully populated database performance row, replace null with an object whose ordered fields are `lastReviewedAt`, `stability`, `difficulty`, `intervalRaw`, `intervalDays`, `dueDate`, and `reviewCount`, using the stored values without rounding.

Sessions are sorted by `started_at`, including sessions without reviews. A session object contains `sessionId`, `startedAt`, `endedAt`, and `reviews`. Reviews within it are sorted by `reviewed_at`; each contains `reviewId`, `hash`, `reviewedAt`, `grade`, `stability`, `difficulty`, `intervalRaw`, `intervalDays`, and `dueDate`. Exported grades are title-cased as `Forgot`, `Hard`, `Good`, or `Easy` even though storage is lowercase.

## Spec 13

An orphan is a row in database table `cards` whose hash is absent from the current unique parsed deck cards. `orphans list` prints orphan hashes in ascending order, one per line, and changes nothing. It prints nothing for no orphans. `orphans delete` prints the same deterministic list and deletes those card rows and their associated review rows; foreign-key cascading or equivalent explicit deletion may be used. It leaves all session rows intact and does not insert any current deck cards. A second deletion is therefore successful and silent. Both operations load and validate the collection first.

## Spec 14

`drill` loads and validates the collection, then ensures every currently parsed card has a `cards` row. A newly discovered card is inserted with the current session-start timestamp as `added_at`, `review_count` zero, and no prior-performance fields. Existing progress is retained. The due queue consists of eligible new cards and reviewed cards due no later than today's local date, filtered by the optional limits/deck selection and sibling-burying choices. Cards are shuffled for presentation. `--from-deck` restricts selection to the named deck; `--card-limit` limits total selected cards and `--new-card-limit` limits selected new cards. Cards sharing a non-null family hash are siblings.

If no cards are eligible, do not start a server; print exactly `No cards due today.\n` and exit successfully. Otherwise bind the requested host and port, with the defaults from Spec 2. `--open-browser false` must never attempt to launch a browser. The process remains alive serving requests until shutdown or external termination. A nonexistent collection fails before binding.

The current card is initially unrevealed. A reveal action is idempotent and does not grade or persist it. A grade is ignored unless the answer has been revealed. `Good` and `Easy` remove the current card from the queue. `Forgot` and `Hard` also append it for repetition later in the same session. Each accepted grade increments the session's review count; a repeated card can therefore be reviewed more than once. `full` controls offer Forgot, Hard, Good, and Easy, while `binary` offers only Forgot and Good.

## Spec 15

The drill UI has actions `Reveal`, `Forgot`, `Hard`, `Good`, `Easy`, `Undo`, `End`, and `Shutdown` as context permits. Every displayed action is an HTML input submit control with `type="submit"`, `name="action"`, and `value="LABEL"`, where `LABEL` is that exact action name. A disabled Undo control is still present and has the `disabled` attribute. Actions are submitted as form data by POST and redirect back to `/`; except for Shutdown, following the redirect yields status 200. Before reveal, show Reveal, Undo, and End, with Undo disabled when no grade can be undone. After reveal, replace Reveal with the configured grading inputs, retaining Undo and End.

Maintain an undo stack of accepted grades. Undo restores the most recently graded card to the front, unrevealed, restores its performance state and displayed progress to their values before that grade, and removes the extra queued repetition introduced by a Hard/Forgot grade. Thus undoing a completing Good/Easy grade can decrement progress, while a Forgot followed by Undo leaves a one-card session at 0% both before and after the Undo. Ending or naturally exhausting the queue finalizes exactly one session row and all accepted review rows, updates each affected cached `cards` performance row, and shows completion. Repeated reviews are distinct review rows. Persisted review grades use Spec 10's values, all scheduling fields are non-null, the card's `review_count` increases, and its cached values equal its latest accepted review.

The completion screen contains `Session Completed 🎉`, `Reviewed N cards...`, `Session Stats`, and labels `Total Cards`, `Cards Reviewed`, `Started`, `Finished`, `Duration`, and `Pace`; duration is shown in seconds and pace in seconds per card. In both `Reviewed N cards...` and `Cards Reviewed`, N is the completed-card count used by the progress calculation in Spec 16, not the number of accepted grade events. Consequently, grading one card Forgot and then Good stores two review rows and raises that card's database `review_count` to 2, but both completion counts display 1; ending after only the Forgot would display 0. Its only session-control submit action is the Shutdown input described above. Shutdown responds to its POST with status 303, `Location: /`, and an empty body, then the serving process exits successfully before a redirected GET can be served; a client that follows the redirect therefore gets connection refused rather than status 200. Ending a session with zero reviews is valid and still stores a session.

## Spec 16

The root drill response is complete HTML beginning with a doctype and has title `hashcards`. It links `/style.css`, `/script.js`, `/katex/katex.css`, `/katex/katex.js`, and `/katex/mhchem.js`. A live session has a `.root` container, a `.progress-bar` containing `.progress-fill`, and a card header whose `h1` is the deck name. The fill's inline style is `width: N%;`, where N is integer floor of completed-card progress divided by initial card count times 100 (thus 0, 33, and 66 for the first three stages of a three-card session). A selected card contributes to completed-card progress only while it has been removed from the pending queue by Good or Easy; a card requeued by Forgot or Hard contributes zero until a later grade completes it. In particular, a one-card session immediately after Forgot renders exactly `width: 0%;`.

A basic live card uses exactly a `<div class="card-content">` whose first two direct children, with no intervening wrapper, are `<div class="question rich-text">...</div>` followed by `<div class="answer rich-text">...</div>`; the class order is part of this structure, and the answer div is immediately followed by the closing `</div>` of `card-content`. Before reveal the answer div is exactly `<div class="answer rich-text"></div>`; after reveal it contains the rendered answer. A cloze card puts its rendered prompt in `.prompt.rich-text`. In an unrevealed cloze, replace the inclusive deletion byte range with exactly `<span class='cloze'>.............</span>` before surrounding Markdown rendering. After reveal use `<span class='cloze-reveal'>DELETED CONTENT</span>`, allowing Markdown within the deleted content to render normally. HTTP root responses use an HTML UTF-8 content type.

## Spec 17

Rich text parses Markdown paragraphs, raw HTML, tables, lists, blockquotes, headings, links, inline/fenced code, emphasis, and math. Escape ordinary text appropriately (`&` becomes `&amp;`) but retain text that the Markdown parser recognizes as an HTML tag. Render the following tested inputs exactly (the shown fragments omit only the renderer's final newline):

```text
This has **bold**, *italic*, and ***both***.
=> <p>This has <strong>bold</strong>, <em>italic</em>, and <em><strong>both</strong></em>.</p>

Here's `inline code` and a [link](https://example.com).
=> <p>Here's <code>inline code</code> and a <a href="https://example.com">link</a>.</p>

# Main Heading
## Sub Heading
### Sub-sub Heading
Some text
=> <h1>Main Heading</h1>\n<h2>Sub Heading</h2>\n<h3>Sub-sub Heading</h3>\n<p>Some text</p>

> This is a blockquote.
> It spans multiple lines.
=> <blockquote>\n<p>This is a blockquote.\nIt spans multiple lines.</p>\n</blockquote>

- First item
- Second item
  - Nested item
- Third item
=> <ul>\n<li>First item</li>\n<li>Second item\n<ul>\n<li>Nested item</li>\n</ul>\n</li>\n<li>Third item</li>\n</ul>

| Name  | Value |
|-------|-------|
| Alpha | 1     |
| Beta  | 2     |
| Gamma | 3     |
=> <table><thead><tr><th>Name</th><th>Value</th></tr></thead><tbody>\n<tr><td>Alpha</td><td>1</td></tr>\n<tr><td>Beta</td><td>2</td></tr>\n<tr><td>Gamma</td><td>3</td></tr>\n</tbody></table>

The equation is $x^2 + y^2 = z^2$.
=> <p>The equation is <span class="math math-inline">x^2 + y^2 = z^2</span>.</p>

Here's text with **"quotes"** and 'apostrophes' and <angle brackets> & ampersands.
=> <p>Here's text with <strong>"quotes"</strong> and 'apostrophes' and <angle brackets> &amp; ampersands.</p>
```

Nested lists must produce properly nested `<ul>`/`<ol>` and `<li>` elements, fenced code must become `<pre><code...>`, and pipe tables must become `<table>` with `<thead>`/`<tbody>` rows and cells. Inline `$formula$` becomes `<span class="math math-inline">formula</span>`; display math uses a `math math-display` element. The browser assets subsequently typeset these elements with KaTeX.

Markdown images are rendered with resolved HTTP sources. For a collection-relative file, the URL is `http://localhost:<selected port>/file/<collection-relative path>` regardless of the address used for binding. An image `![Test Image](@/test.png)` renders as `<p><img src="http://localhost:PORT/file/test.png" alt="Test Image" /></p>` after normalizing the actual port to `PORT`. Images whose extension is exactly lowercase `mp3`, `wav`, or `ogg` are instead emitted as `<audio controls src="..." title="..."></audio>`, followed by their alt text. Thus `![Audio File](@/sound.mp3)` renders as `<p><audio controls src="http://localhost:PORT/file/sound.mp3" title=""></audio>Audio File</p>`. WAV and OGG behave identically. Multiple media references render in input order, and nested paths remain in the URL. Other images use the exact `<img src="..." alt="..." />` shape; preserve a provided title.

## Spec 18

The server exposes built-in static resources independent of the collection:

- `/style.css`: status 200, `Content-Type: text/css`, a substantive stylesheet longer than 100 bytes.
- `/script.js`: status 200, JavaScript content type, substantive content longer than 100 bytes, including TeX macro configuration and interaction/math initialization.
- `/katex/katex.css`: status 200, CSS content, size strictly between 20,000 and 30,000 bytes.
- `/katex/katex.js`: status 200, JavaScript content, size strictly between 270,000 and 280,000 bytes.
- `/katex/mhchem.js`: status 200, JavaScript content, size strictly between 30,000 and 40,000 bytes.

Successful stylesheet, KaTeX library, and font responses include `Cache-Control: public, max-age=604800, immutable`. The server must also supply nonempty `font/woff2` responses for exactly these KaTeX font stems, each followed by `.woff2`:

```text
KaTeX_AMS-Regular
KaTeX_Caligraphic-Bold
KaTeX_Caligraphic-Regular
KaTeX_Fraktur-Bold
KaTeX_Fraktur-Regular
KaTeX_Main-Bold
KaTeX_Main-BoldItalic
KaTeX_Main-Italic
KaTeX_Main-Regular
KaTeX_Math-BoldItalic
KaTeX_Math-Italic
KaTeX_SansSerif-Bold
KaTeX_SansSerif-Italic
KaTeX_SansSerif-Regular
KaTeX_Script-Regular
KaTeX_Size1-Regular
KaTeX_Size2-Regular
KaTeX_Size3-Regular
KaTeX_Size4-Regular
KaTeX_Typewriter-Regular
```

`KaTeX_Main-Regular.woff2` has size strictly between 20,000 and 35,000 bytes. Unknown font names, wrong extensions, and traversal attempts return 404.

## Spec 19

`GET /file/<relative path>` serves exact file bytes only when the URL path resolves to an existing regular file inside the collection. Reject absolute paths, `..` traversal, percent-encoded traversal, missing files, directories, and any requested final path that is itself a symbolic link with status 404 and a plain `Not Found` response. This containment check is required even for files that were not referenced by a card.

Use these content types by lowercase extension: `png` → `image/png`, `jpg`/`jpeg` → `image/jpeg`, `gif` → `image/gif`, `svg` → `image/svg+xml`, `mp3` → `audio/mpeg`, `wav` → `audio/wav`, `ogg` → `audio/ogg`, `mp4` → `video/mp4`, and `webm` → `video/webm`. Unknown extensions use `application/octet-stream`. Nested in-collection paths are supported. All other unknown routes return status 404 rather than disclosing filesystem information.

## Spec 20

Diagnostics never include a language traceback or panic dump for expected bad input. When `RUST_LOG` (the conventional environment variable name retained by this interface) is empty or absent, normal successful output does not contain debug logging. When it enables the `debug` level, successful commands may add debug log lines to stderr and at least one such line contains the case-insensitive word `debug`; their functional stdout and exit status remain unchanged. A command that later fails collection validation also emits debug lines before its functional error, with at least one line containing the case-insensitive word `debug`. In particular, a `check` that finds missing media emits those lines before the usual `hashcards: error: Missing media files referenced in cards:` diagnostic and still exits 1. An invalid logging directive must not prevent `--help` from succeeding.

Implementation must handle at least a thousand cards, hundreds of deck files, deep but reasonable directory nesting, Unicode paths/content, and long card strings within ordinary command-test timeouts. Ordering must remain deterministic wherever this document specifies sorting; HTTP card presentation is the deliberate exception because the drill queue is shuffled.
