# `executable`: terminal folded-stack flamegraph viewer

## Spec 1: Required artifact and scope

The required artifact is one executable file named exactly `executable`. It is a
command-line program that reads profiler data in folded-stack form and presents an
interactive terminal flamegraph plus a Top table.

Only `executable` is part of the deliverable. A test harness may provide a PTY or a
terminal-driving command; that command is infrastructure and is not functionality
which `executable` must implement.

This specification describes the non-live build. In particular, process attachment,
`--pid`, Python sampling, and output-file options are not supported command-line
features.

## Spec 2: Command-line interface

The accepted invocation is:

```text
executable [OPTIONS] [FILENAME]
```

There is at most one positional filename. Options may occur before or after it.
The accepted options are the three value-less long flags `--sorted`, `--echo`, and
`--debug`, plus `-h`/`--help` and `-V`/`--version`.

`executable --help` exits successfully, writes nothing to stderr, and writes exactly
the following text to stdout, including the final newline:

```text
Usage: executable [OPTIONS] [FILENAME]

Arguments:
  [FILENAME]  Profile data filename

Options:
      --sorted   Whether to sort the stacks by time spent
      --echo     Print data to stdout on exit. Useful when piping to other tools
      --debug    Show debug info
  -h, --help     Print help
  -V, --version  Print version
```

The short help form also succeeds and presents this interface. `--version` and `-V`
exit with status 0, write nothing to stderr, and print exactly:

```text
flamelens 0.3.1
```

A version flag is an immediate successful action: accepted flags before it do not
prevent version output, and arguments following the version flag are ignored.

Argument syntax errors have exit status 2, no stdout, and a conventional
clap-style diagnostic on stderr. The diagnostic starts with `error:` and ends
with `For more information, try '--help'.` Its usage line is
`Usage: executable [OPTIONS] [FILENAME]` for the syntax errors listed below
except for the attached-value case. Applicable cases include:

- an unknown option, such as `--nonexistent` or `-x`;
- a second positional argument;
- unsupported `--output` or `-o` arguments; and
- attaching a value to a Boolean flag, such as `--sorted=1`. This case says
  `unexpected value '1'` and `no more were expected`, and its usage line is
  exactly `Usage: executable --sorted [FILENAME]`.

For an unknown long option, the diagnostic also gives the usual hint that a dashed
value may be passed after `--`. A standalone `--` ends option parsing, so a following
dashed token is treated as `FILENAME`. A terminal `--` with nothing after it leaves
the filename absent.

## Spec 3: Acquiring and echoing input

When `FILENAME` is supplied, read the entire named file as UTF-8. Otherwise read all
of standard input through EOF as UTF-8 and use the display label `stdin`.

`--echo` copies the complete, original decoded input to stdout before the interactive
UI begins and appends one newline of its own. It does not remove comments, normalize
lines, aggregate stacks, or apply `--sorted`. Consequently, input already ending in
`\n` is followed by one extra blank line. Without `--echo`, normal execution reserves
stdout and produces no ordinary stdout data.

The TUI itself is rendered to stderr. It requires terminal facilities (raw mode and
an alternate screen). In an ordinary captured, non-terminal invocation where those
facilities cannot be established, terminate with status 1, no non-echo stdout, and
an OS diagnostic on stderr containing `Error: Os` and `kind:` (commonly
`WouldBlock` or `NotFound`). Any requested echo must already have been emitted. This
case must terminate promptly rather than hang, including with no filename or with
`--sorted` and no filename.

Failure to read a named file is a panic-style failure with status 101 and no stdout.
Its stderr contains `thread 'main' (`, followed by a runtime-assigned unsigned
decimal thread ID and then `) panicked at src/main.rs:`,
`Could not read file:`, the OS error kind (for a missing file, `NotFound`), and the
underlying message such as `No such file or directory`. Invalid UTF-8 in a file is
the same kind of status-101 read failure and identifies `InvalidData` and UTF-8.
Invalid UTF-8 from stdin is a status-101 panic with the same parenthesized decimal
thread-ID preamble and contains `Could not parse stdin:`. The numeric thread ID is
runtime-dependent and can differ between invocations; the parentheses themselves
are part of the output.

## Spec 4: Folded-stack parsing and aggregation

Input is line-oriented. A valid data line has this form:

```text
frame-1;frame-2;frame-3 COUNT
```

Parsing uses the final literal ASCII space on the line as the separator. The text
before it must be nonempty and is the stack; the text after it must be an unsigned
decimal integer. This permits spaces inside frame names. The stack is split on
literal semicolons. Names are otherwise preserved, including punctuation, C++-like
syntax, parentheses, dollar signs, angle brackets, and UTF-8 text.

Ignore empty/whitespace-only lines, lines whose first character is `#`, and malformed
lines that lack a valid final count. Continue processing valid lines around malformed
ones. A zero count is valid. Counts and sums must support values well beyond the
32-bit range; totals around 18 billion must not overflow.

Construct a rooted ordered tree whose synthetic root is named `all`:

- Each distinct path prefix is one node. Repeated identical stacks and shared
  prefixes merge rather than creating duplicates.
- A valid line's count is added to the root and to the inclusive (`total`) count of
  every node on that path. It is added to the own/self count of the final frame only.
- With no valid lines, the tree still consists of `all` with count 0.
- Without `--sorted`, children retain first-appearance order.
- With `--sorted`, the children of every node are reordered by descending inclusive
  count. Equal-count children occur in reverse of their insertion order. The flag
  does not alter echoed input or the Top table's default sort.

For the Top table, aggregate by short frame name across the entire tree. `own` is the
sum of counts for lines ending at that name. `total` is the sum of line counts in
which that name occurs anywhere, but a recursive name appearing multiple times in
one line contributes to this global total only once for that line.

For example, this input:

```text
a;b;c 10
a;b;c 5
a;e 30
```

has root and `a` totals of 45, `b` and `c` totals of 15, `c` own count 15, and `e`
total/own count 30.

## Spec 5: Overall layout

On a terminal, enter raw mode and the alternate screen, hide the cursor except while
editing a search, and repaint on resize. Quit cleanly and restore the terminal on
`q` or Ctrl-C.

The screen is organized vertically as:

1. a header bounded by full-width `─` top and bottom rules;
2. a fill-height main area containing the flamegraph or Top table;
3. zero or more two-line context panels (`Match`, `Selected`, `Debug`, or `Info`),
   each introduced by its title and a `─` rule to the right; and
4. a two-line footer consisting of a `─` rule and key hints.

The header's left text is ` [Flamegraph] | Top ` in flamegraph view and
` Flamegraph | [Top] ` in table view. The input label is centered in the middle,
and `flamelens v0.3.1` is right-aligned. Preserve the supplied filename string (an
absolute filename therefore appears absolute). If it is too long for the middle
area, wrap it without trimming and increase the header height. More precisely, the
left area has the width of ` [Flamegraph] | Top `, the right area has the width of
`flamelens v0.3.1`, and the middle fills the remainder; wrapping height is determined
conservatively after reserving the larger indicator width on both sides.

The active view name is bracketed. At 80 columns the flamegraph footer begins exactly
as follows and is clipped at the right edge if necessary:

```text
 [hjkl: move cursor] [f/b: scroll] [enter/esc: zoom] [/: search] [#: search like cursor] [r: reset] [tab: switch view] [q: quit] 
```

While a manual search is active, insert `[n/N: next/prev search]` after the `#` hint.
The Top footer is:

```text
 [j/k: move cursor] [f/b: scroll] [1: sort by total] [2: sort by own] [/: filter] [r: reset] [tab: switch view] [q: quit] 
```

## Spec 6: Flamegraph geometry

Render `all` on level 0 and descendants one terminal row per call depth. The root's
horizontal budget is the full main-area width. Recursively, a child receives its
parent's floating-point width budget multiplied by
`child.total / parent.total`. Place children consecutively from left to right. For
cell placement, truncate each floating width toward zero; a node with less than one
cell is not drawn.

Within a visible node's cells, use one leading separator cell followed by as much of
the short frame name as fits, then padding. The separator is a space when the node is
wider than one cell and `.` for a one-cell node. Names are clipped at their cell
boundary. Thus the layout communicates sample share through width, and very narrow
frames may appear only as `.` or as a clipped first character.

The initially selected node is `all`. The normal Selected panel has this exact value
shape:

```text
NAME [COUNT samples, PP.PP% of all]
```

Percentages are calculated from the root count and rounded to exactly two decimal
places. For an empty graph, show
`all [0 samples, NaN% of all]`.

The main area is vertically scrollable by tree level. Levels above the current
offset are omitted and the remaining levels move upward; selected nodes are kept in
the visible viewport. Deep inputs (at least 250 levels) must remain navigable.

## Spec 7: Top table

Tab switches between flamegraph and Top views without discarding current search,
selection, or sort state. The Top view begins with this header:

```text
Total          Own [▼]       Name
```

Column widths expand to fit the widest visible formatted count. Each count cell is
formatted as `COUNT (PP.PP%)` using the root total, with two spaces after it before
the next column. The arrow ` [▼]` marks the active descending sort column.

The initial table order is descending own count. Ties are reverse lexicographic by
name. Key `1` changes to descending total count and key `2` changes to descending own
count, using the same reverse-lexicographic tie rule. Every distinct non-root short
name appears once. The selected row has a distinct terminal style; movement and
scrolling do not alter its textual cells.

## Spec 8: Interaction and state

Commands apply only outside search-input mode unless stated otherwise.

## Spec 9: Flamegraph movement, scrolling, and zoom

- `j` or Down selects the widest child of the current node that is at least one cell
  wide. If multiple children tie for widest, select the last of them in the current
  rendered child order. For example, with `a;b;c 10`, `a;b;d 20`, and `a;e 30`,
  descending from `a` selects `e`: both `b` and `e` have 30 samples, and `e` is
  later. `k` or Up selects the parent.
- `h` or Left and `l` or Right select the previous or next visible frame in the
  rendered ordering at the same depth. If none exists, they are no-ops.
- Movement beyond a boundary is a no-op: in particular, Up/Left at `all` must leave
  the screen and selection unchanged.
- `f` and `b` page the vertical level viewport down and up by one main-area height;
  `G` goes to the lowest useful level offset and `g` returns to level 0.
- Enter zooms to the selected non-root node. Preserve and render its ancestor chain,
  hide unrelated branches, and scale the selected subtree to the full width. The
  Selected panel then appends `, ZZ.ZZ% of zoomed` inside the brackets. Enter on
  `all` is a no-op. Escape clears the current zoom completely and leaves the zoom
  focus selected.

Navigation to a frame also establishes an internal exact-name match for equal-name
frames, but it does not display the manual `Match` panel.

## Spec 10: Searching

`/` enters search-input mode. During input, replace other context panels with a
`Search` panel containing the typed text, show the cursor after that text, and support
ordinary editing. Escape cancels the edit without applying it. Enter on an empty
buffer clears an existing manual search.

A nonempty `/` search is a regular expression applied to short frame names. On
successful submission:

- matching portions are highlighted;
- the flamegraph remains on its existing selection;
- the `Match` panel displays
  `"REGEX" [COUNT samples, PP.PP% of all]`; and
- in Top view, only matching names are visible.

Match coverage counts each sample path once: when a matched frame contains matched
descendants, its inclusive count already covers those descendants. A search with no
flamegraph matches is valid and displays `0 samples, 0.00% of all`. In Top view, if
the filter would have no rows, show all rows and append `(no match; showing all)` to
the Match text.

An invalid regular expression exits input mode, retains the prior state, and shows
an Info panel containing `Invalid regex: PATTERN`. The next handled command clears
this transient message.

`#` searches for the exact short name of the selected flamegraph frame. Escape all
regex metacharacters and anchor both ends; for example, selecting
`work (file.py:8)` yields the displayed regex
`^work \\(file\\.py:8\\)$`. `#` at `all` is a no-op. In Top view, Enter performs this
same exact-name search for the selected row and switches to flamegraph view.

With a manual search active, `n` selects the next visible hit and `N` the previous
visible hit. Search order is rendered level order: first later hits on the selected
depth, then the first hit on a deeper (or, for `N`, shallower) level. Do not wrap at
the ends. Scroll as needed to reveal the selected hit.

## Spec 11: Table navigation and global commands

In Top view, `j`/Down and `k`/Up move one visible row without wrapping; attempts to
move before the first or after the last row are no-ops. `f` and `b` move by one
main-area height and update the viewport, clamped to valid rows.

`r` resets the tree selection to `all`, vertical and table offsets to zero, and
clears zoom and search. It keeps the current view, current table sort column, debug
setting, and static input data. In flamegraph view this reproduces the initial
screen. Tab toggles the view. `q` and Ctrl-C exit cleanly.

`?` toggles a Debug context panel. Starting with `--debug` enables it initially. Its
body starts with `Debug:` and contains available named timings such as
`flamegraph:0.03ms`, `render:0.10ms`, and after input handling,
`handle_key_events:0.00ms`. Values are shown in milliseconds with two decimals;
field order and measured values are not deterministic. The panel is below Match and
Selected status and above Info/footer.

`z` may toggle an internal freeze state, but with the static file/stdin build in this
specification it causes no visible content change and does not add a live-mode UI.

## Spec 12: Capacity and responsiveness

The implementation must not assume shallow or narrow input. It must handle, render,
search, sort, zoom, and navigate data sets including:

- at least 10,000 unique input stacks;
- at least 1,000 siblings at one depth;
- at least 250 frames in one stack;
- mixtures of hundreds of shallow and deep stacks; and
- multi-billion counts and totals above 32-bit range.

On such supplied test data, initial parsing and stable TUI presentation must complete
within five seconds in the evaluation environment, and echoing 10,000 lines must be
complete rather than truncated.
