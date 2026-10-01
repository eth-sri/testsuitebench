# Clarified specification for `executable`

## Spec 1

The required artifact is a directly runnable file named exactly `executable`. It is a single-purpose command-line program named `dupl`; it has no subcommands. It analyzes source text written in the Go language and reports structurally duplicated syntax. All diagnostics and progress logs go to standard error, while all clone reports go to standard output. Unless an error behavior below says otherwise, a completed analysis exits with status 0, including an analysis that finds no clones or encounters one or more per-file parse/read errors that it can skip.

Clone equality is structural, not textual. The program parses each input as Go, converts its syntax tree to the normalized tree defined below, and compares the preorder sequence of normalized node-type numbers. Identifier spellings, literal values, operators, assignment forms, and comments do not participate unless their presence changes the shape or kinds of syntax-tree nodes. For example, `if a == 13 {}` and `if x == 100 {}` have the same normalized structure. This deliberately permits false positives.

## Spec 2

The command-line grammar is:

```text
dupl [flags] [paths]
```

The supported flags are:

- `-files`: obtain input path strings from standard input instead of crawling positional paths.
- `-html`: select HTML output.
- `-plumbing`: select machine-readable plumbing output.
- `-t N` and `-threshold N`: aliases that set the minimum normalized-node sequence size; the default is 15.
- `-vendor`: include files underneath directories named `vendor` during directory crawling.
- `-v` and `-verbose`: aliases that enable progress logging.

Use Go-style flag parsing behavior. A flag name may begin with one or two hyphens. Integer flags accept a separate signed decimal argument or an equals form such as `-t=15`. Repeating an integer flag uses its last value, even across the two aliases. Repeating a Boolean flag, or using both aliases of the same Boolean setting, remains idempotent. Flag names are case-sensitive; for example, `-Verbose` is unknown. Bundled short flags such as `-vt` are not supported. Parsing stops at the first positional argument, so every later argument is also positional even if it begins with `-`. A standalone `--` ends flag parsing and is not itself a path.

All signed integer threshold values that successfully parse, including zero and negative values, are accepted. Very large values are valid and normally yield no groups. A clone is eligible at the boundary: a normalized sequence of exactly `N` nodes is eligible at threshold `N`.

## Spec 3

`-h`, `--help`, and `-help` print usage to standard error, print nothing to standard output, and exit with status 2. The exact usage text, including capitalization, punctuation, blank lines, indentation, tab-indented description lines, and final newline, is:

```text
Usage: dupl [flags] [paths]

Paths:
  If the given path is a file, dupl will use it regardless of
  the file extension. If it is a directory, it will recursively
  search for *.go files in that directory.

  If no path is given, dupl will recursively search for *.go
  files in the current directory.

Flags:
  -files
    	read file names from stdin one at each line
  -html
    	output the results as HTML, including duplicate code fragments
  -plumbing
    	plumbing (easy-to-parse) output for consumption by scripts or tools
  -t, -threshold size
    	minimum token sequence size as a clone (default 15)
  -vendor
    	check files in vendor directory
  -v, -verbose
    	explain what is being done

Examples:
  dupl -t 100
    	Search clones in the current directory of size at least
    	100 tokens.
  dupl $(find app/ -name '*_test.go')
    	Search for clones in tests in the app directory.
  find app/ -name '*_test.go' |dupl -files
    	The same as above.
```

An unknown flag exits 2, leaves stdout empty, and writes an error line followed immediately by the same usage block. The error has the Go-flag form `flag provided but not defined: -NAME`. A missing integer value similarly begins with `flag needs an argument: -t` or `flag needs an argument: -threshold`. An invalid integer begins, for example, `invalid value "abc" for flag -t: parse error`. A path-looking value beginning with `-` is nevertheless consumed when it is the required value of an immediately preceding integer flag.

## Spec 4

Without `-files`, positional paths are processed in the given order. If there are none, behave as though the sole path were `.`. Inspect each top-level argument with a non-following symbolic-link status operation equivalent to `lstat`:

- If it is not a directory, send that exact path string to the parser regardless of extension. This includes an ordinary file and a symbolic link.
- If it is a directory, walk it recursively with no fixed depth limit. Within each directory, traversal is lexicographic by entry name. Send only nondirectory entries whose basename ends case-sensitively in `.go`.
- Directory crawling ignores non-Go files. An explicitly named regular file is parsed regardless of extension.
- Preserve the spelling of a path in reports. Absolute inputs produce absolute report paths; relative inputs remain relative. Do not canonicalize or resolve symbolic-link paths before reporting them.

Multiple files and directories form one combined analysis, allowing clones across inputs and packages. Long filenames and deeply nested paths must work.

## Spec 5

While crawling directories, exclude every entry whose complete walked path either begins with `vendor/` or contains `/vendor/`, unless `-vendor` is present. This is a path-component rule for directory crawling, not a global rule: an explicitly named file under `vendor`, or a path received through `-files`, is still parsed directly. With `-vendor`, recursively include `.go` files in both top-level and nested `vendor` directories.

Do not follow symbolic links encountered as directories during a recursive walk. An explicitly supplied symlink to a regular file is read through the symlink but retains the symlink path in output. Because the initial inspection does not follow links, an explicitly supplied symlink to a directory is treated as a file; attempting to parse it logs an `is a directory` read error, the analysis continues, and the overall status is 0 if no fatal condition occurs.

An empty directory or a directory containing no `.go` files is a successful empty analysis.

## Spec 6

With `-files`, completely replace positional/default path crawling with a line-oriented standard-input feed. Read one path per line until EOF. For every line, remove one leading literal `./` if present and pass the remainder directly to the parser. Preserve every other part of the path spelling. Relative paths resolve against the process working directory. Empty stdin is a successful empty analysis.

This feed does not preflight with `lstat` and does not recursively expand directory lines. Consequently, missing/unreadable lines and lines naming directories are ordinary per-input read/parse errors: log each error and continue through all later lines. Positional arguments, if any, do not add inputs while `-files` is active. This mode must be able to continue past a nonexistent line and still report clones from valid lines before and after it.

## Spec 7

Fatal setup/runtime errors use a timestamped log line on stderr in this form:

```text
YYYY/MM/DD HH:MM:SS message
```

The timestamp uses numeric four-digit year and two-digit month, day, hour, minute, and second. A nonexistent positional path is fatal, exits 1, and reports the underlying `lstat` message, for example `lstat missing.go: no such file or directory`. Processing stops rather than producing a clone footer. This also explains flag ordering: `dupl some-directory -t 15` treats `-t` and `15` as paths and fatally reports `lstat -t: no such file or directory` after flag parsing has stopped.

`-html` and `-plumbing` are mutually exclusive. If both are true, validate the conflict before input processing, emit the timestamped message `you can have either plumbing or HTML output` to stderr, print nothing to stdout, and exit 1. This remains true when `-verbose` is also present.

An individual file read or Go parse failure after a path has entered the parser is nonfatal: emit the timestamped error, skip that file, and keep processing. The eventual exit status remains 0. Representative required parser diagnostics include `file.go:1:1: expected 'package', found 'EOF'` for an empty file, `file.txt:1:1: expected 'package', found This` for explicit text beginning `This`, an `expected '}', found 'EOF'` location for a missing closing brace, and an `illegal UTF-8 encoding` location for invalid UTF-8. Valid files in the same invocation must still contribute clones.

## Spec 8

Parse the conventional Go constructs listed in Specs 9 and 10, retaining each normalized node's input filename and half-open byte offsets `[Pos, End)` in the original file. Positions are zero-based bytes internally; line reporting later is one-based. Comments are not normalized nodes. Import declarations are omitted from the normalized tree altogether. Package-name spelling is not a child of the normalized file root.

Each normalized node has:

```text
Type      integer node tag
Filename  exact input path string
Pos, End  original-source byte offsets
Children  ordered normalized child nodes
Owns      number of all descendants, computed later
```

Unsupported or bad syntax-node kinds normalize to tag 0 with no children. A syntax error for which no complete file tree is returned causes the whole file to be skipped as described in Spec 7. The parser must handle functions and methods, declarations, structs and interfaces, arrays/slices/maps, pointers, composite literals, calls and selectors, arithmetic/comparison/logical expressions, assignments, returns, if/else, all ordinary `for`/range forms, switch/type-switch, select/channels, labels and branches, goroutines, `defer`, variadics, function literals, and empty/declaration statements. It must also accept valid generic function/type-parameter syntax without a fatal exit; generic-only AST fields for which no child rule appears below are ignored or represented by the tag-0 fallback.

## Spec 9

Use the following exact normalized tags and child order for tags 0 through 24. “All” always means source order; “optional” means omit the child when absent.

| Tag | Kind | Ordered children |
|---:|---|---|
| 0 | BadNode | none |
| 1 | File | all non-import declarations |
| 2 | ArrayType | optional length expression, then element type |
| 3 | AssignStmt | all right-hand expressions, then all left-hand expressions |
| 4 | BasicLit | none; literal kind and value are ignored |
| 5 | BinaryExpr | left expression, right expression; operator is ignored |
| 6 | BlockStmt | all statements |
| 7 | BranchStmt | optional label; branch keyword is ignored |
| 8 | CallExpr | called expression, then all arguments |
| 9 | CaseClause | all case expressions, then all body statements |
| 10 | ChanType | value type; channel direction is ignored |
| 11 | CommClause | optional communication statement, then body statements |
| 12 | CompositeLit | optional explicit type, then all elements |
| 13 | DeclStmt | declaration |
| 14 | DeferStmt | call |
| 15 | Ellipsis | optional element type |
| 16 | EmptyStmt | none |
| 17 | ExprStmt | expression |
| 18 | Field | all names, then field type |
| 19 | FieldList | all fields |
| 20 | ForStmt | optional init, optional condition, optional post, then body |
| 21 | FuncDecl | optional receiver, name, function type, optional body |
| 22 | FuncLit | function type, body |
| 23 | FuncType | parameter field list, then optional result field list |
| 24 | GenDecl | all specs |

The source span for a composite normalized node is the full corresponding construct. Thus a `FuncDecl` begins at `func` and ends immediately after its body, while its name is a tag-26 child whose spelling does not affect equality.

## Spec 10

Use this continuation of the exact normalized tags and child order:

| Tag | Kind | Ordered children |
|---:|---|---|
| 25 | GoStmt | call |
| 26 | Ident | none; spelling is ignored |
| 27 | IfStmt | optional init, condition, body, optional else |
| 28 | IncDecStmt | operand; `++` versus `--` is ignored |
| 29 | IndexExpr | indexed expression, index |
| 30 | InterfaceType | method field list |
| 31 | KeyValueExpr | key, value |
| 32 | LabeledStmt | label, statement |
| 33 | MapType | key type, value type |
| 34 | ParenExpr | enclosed expression |
| 35 | RangeStmt | optional key, optional value, ranged expression, body |
| 36 | ReturnStmt | all result expressions |
| 37 | SelectStmt | body block |
| 38 | SelectorExpr | base expression, selected identifier |
| 39 | SendStmt | channel expression, value expression |
| 40 | SliceExpr | base expression, then optional low, high, and max expressions |
| 41 | StarExpr | operand |
| 42 | StructType | field list |
| 43 | SwitchStmt | optional init, optional tag, body |
| 44 | TypeAssertExpr | expression, then optional asserted type |
| 45 | TypeSpec | name, type |
| 46 | TypeSwitchStmt | optional init, assignment, body |
| 47 | UnaryExpr | operand; unary operator is ignored |
| 48 | ValueSpec | all names, optional explicit type, then all values |

These rules intentionally make differently named functions, receivers, variables, fields, labels, selectors, and called functions structurally equal when their surrounding node shapes agree. Different literal strings/numbers and different binary or assignment operators likewise do not distinguish clones. Structural additions or omissions—such as an extra `if`, argument, declaration, or result—do distinguish the affected portion.

## Spec 11

Serialize each normalized file tree by preorder: append the node, then recursively serialize its children from left to right. During this traversal set `Owns` to the total count of descendants, so the serialized subtree rooted at a node has size `Owns + 1`. Concatenate complete per-file streams in input-feed order, without inserting a separator between files. Keep that node array for fragment recovery. After all files have been processed, append one unique final sentinel with type `-1` only to the sequence indexed for repeat searching; do not append it to the fragment-recovery array. The sentinel is not itself reportable syntax.

The threshold refers to normalized-node sequence length, despite the help text calling these “tokens.” A complete candidate syntax unit rooted at node `n` is large enough precisely when `n.Owns + 1 >= threshold`. Because identifiers and literals each contribute nodes, an empty function still has structural nodes, and threshold 1 can expose very small matches—even two different tag-26 identifier leaves on adjacent source lines.

As boundary examples, two structurally identical functions whose serialized subtrees contain 20 nodes are reported at `-t 20` and excluded at `-t 21`. Two functions of 16 nodes are reported at 16 and excluded at 17. The default threshold is exactly 15. A sufficiently high threshold produces the empty report for the selected format.

## Spec 12

Find raw repeats over the entire concatenated tag stream using the following observable maximal-repeat definition. A raw repeat is a substring of at least `threshold` normalized tags that occurs at least twice, is right-maximal (its occurrences do not all continue with the same next tag), and is left-maximal (its occurrences do not all have the same preceding tag). Treat the preceding context of stream position 0 as integer tag 0. The final `-1` sentinel supplies a distinct right context at stream end. Emit the occurrence start positions and repeated length for every such maximal repeat; do not restrict repeats to lexical tokens, functions, or files at this stage.

An equivalent implementation may build a compact suffix tree and visit every explicit internal state at depth at least the threshold. At a leaf, recover the suffix start and bucket it by the immediately preceding tag (or 0 at stream start). At an internal state, combine descendant buckets; emit that state's depth and all descendant suffix starts only when at least two preceding-context buckets exist. Sorting context-bucket integer keys before joining occurrence lists matches the reference behavior. The implementation must handle hundreds of source lines, many files, long repeated bodies, overlapping suffixes, and threshold 1 without hanging or quadratic blowups; the tested large project must complete within 30 seconds.

## Spec 13

Convert each raw repeat to complete reportable syntax units exactly as follows. Let `seq` be the first occurrence's repeated slice and let `L = len(seq)`. Scan with `i = 0`, `split = false`, and an initially empty `indexes` list:

```text
while i < L:
    n = seq[i]
    if n.Owns >= L - i:          # its subtree runs beyond the raw repeat
        i = i + 1
        split = true
        continue
    if n.Owns + 1 < threshold:  # a complete but undersized unit
        split = true
    else:
        if split:
            clear indexes
            split = false
        append i to indexes
    i = i + n.Owns + 1
```

If at least one index remains, compare the `Owns` value of the final selected node with the node at the same relative index in every other occurrence. At the first mismatch, remove that final index once. Reject the raw repeat if no indexes remain. Otherwise each occurrence becomes a fragment consisting of the nodes at the retained relative indexes. A fragment starts at the first retained node's `Pos` and ends at the last retained node's `End`. This permits one fragment to comprise several adjacent complete statements, but it must never comprise a partial normalized subtree.

Reject a candidate if two or more retained roots in the first fragment have different `Filename` values. This prevents a single reported fragment from crossing a concatenated file boundary; it does not prevent a clone group from containing one complete fragment from each of several files.

## Spec 14

Also reject cyclic/redundant unit sequences using this exact filter, where `indexes` and `seq` are from Spec 13:

```text
if count(indexes) <= 1: not cyclic
candidates = every divisor d of count(indexes), 1 <= d <= count/2
for offset from 0 up to (but excluding) indexes[count/2]:
    base = seq[offset + indexes[0]]
    for each still-present d:
        for j = d; j < count; j += d:
            k = offset + indexes[j]
            if k < len(seq) and
               seq[k].Owns == base.Owns and seq[k].Type == base.Type:
                continue this inner loop
            if k >= len(seq) and offset >= indexes[d]:
                return cyclic
            remove d from candidates
            stop checking this d
    if candidates is empty: return not cyclic
return cyclic
```

For every accepted fragment, compute its group key from the first occurrence. Let `first = indexes[0]`, `last = indexes[-1]`; hash with SHA-1 the byte sequence of node tags in the half-open slice `seq[first : last + seq[last].Owns]`, encoding each tag as its low byte. The upper bound is intentionally exactly as written (there is no additional `+1`). Merge fragments produced by all raw repeats with the same 20-byte digest.

Within each digest group, deduplicate occurrences by the pair `(Filename, Pos of first retained node)`, preserving the first occurrence. Discard groups with fewer than two unique occurrences. Sort the remaining groups by the raw 20 digest bytes in lexicographic order. This digest order—not filename order or source order—is the order in which clone groups appear. Within each group, all output modes sort occurrences first by filename string and then by starting line number.

## Spec 15

Default text mode has no header. For each retained group, print:

```text
found N clones:
  PATH:START,END
  PATH:START,END
```

There are exactly two ASCII spaces before each path. `START` and `END` are inclusive one-based source line numbers containing, respectively, the byte at fragment start and the final byte immediately before fragment end. There is no extra blank line between adjacent groups. After all groups, including when there are none, print exactly:

```text

Found total G clone groups.
```

Thus the empty text report is exactly `\nFound total 0 clone groups.\n`. The word `groups` remains plural for 1. The final newline is required.

For example, if relative files `a.go` and `b.go` each consist of a structurally equal nine-line file tree, the complete one-group report is:

```text
found 2 clones:
  a.go:1,9
  b.go:1,9

Found total 1 clone groups.
```

Line counting is based on original bytes: start at line 1 and increment after each byte `\n`. Comments and blank lines can therefore affect reported line numbers even though comments are absent from structural matching.

## Spec 16

Plumbing mode has no header, footer, summary, or blank lines. An empty result writes zero bytes. For a sorted group with occurrences `C[0] ... C[N-1]`, emit exactly one line per occurrence, pointing cyclically to the next occurrence:

```text
C[i].PATH:C[i].START-C[i].END: duplicate of C[(i+1) mod N].PATH:C[(i+1) mod N].START-C[(i+1) mod N].END
```

Each line ends in `\n`. For two clones this produces two bidirectional lines. For three clones it produces `A -> B`, `B -> C`, and `C -> A`, rather than all pairwise combinations. Group order and within-group occurrence order are those in Spec 14. There must be no verbose or diagnostic text on stdout.

## Spec 17

HTML mode always begins by writing exactly this header, even for an empty result:

```html
<!DOCTYPE html>
<meta charset="utf-8"/>
<title>Duplicates</title>
<style>
	pre {
		background-color: #FFD;
		border: 1px solid #E2E2E2;
		padding: 1ex;
	}
</style>
```

There is no `<html>`, `<body>`, summary, or closing footer. Number printed groups from 1 in the digest order of Spec 14. For each group print:

```html
<h1>#K found N clones</h1>
<h2>PATH:START</h2>
<pre>ESCAPED_FRAGMENT</pre>
```

Repeat the `<h2>`/`<pre>` pair for every sorted occurrence. The heading contains only its inclusive starting line, not the ending line. Escape source fragment text with these HTML substitutions: `&` to `&amp;`, `'` to `&#39;`, `<` to `&lt;`, `>` to `&gt;`, and `"` to `&#34;`. Escaping happens after fragment extraction and whitespace adjustment.

For each occurrence, read the original file again. Begin at the start of the physical line containing the fragment's first node. In the prefix between that line beginning and `Pos`, retain every tab byte as a tab and replace every other Unicode rune with one ASCII space; then append original bytes from `Pos` through the last retained node's `End`.

Deindent that resulting block by examining only line beginnings that match `(^|\n)(\t*)\S`: a participating line must have zero or more tabs immediately followed by a non-whitespace character. Take the minimum captured-tab count. If there is no participating line, or that minimum is zero, return the block unchanged. Otherwise remove that many bytes from the beginning of the block, then examine every newline other than a final newline and remove that many bytes immediately after it only when all of those bytes are tabs; leave that later line unchanged when they are not all tabs. Thus a one-line fragment whose adjusted prefix is one tab followed by three spaces does not participate in the minimum calculation and retains the tab and all three spaces. This filtering is why the HTML fragment for the source prefix `\t   čřď; ` begins with exactly `\t   čřď`, while ordinary tab-only common indentation is removed. The prefix conversion still accommodates multibyte runes and leaves source indentation within the fragment intact.

## Spec 18

With `-v` or `-verbose`, emit exactly two progress-message lines to stderr, each with the timestamp prefix from Spec 7:

```text
YYYY/MM/DD HH:MM:SS Building suffix tree
YYYY/MM/DD HH:MM:SS Searching for clones
```

Emit `Building suffix tree` before beginning the input parse/build phase. Emit `Searching for clones` after all input trees have been serialized and the final sentinel added, but before clone results are printed. Each message appears exactly once even if verbose flags or aliases are repeated. They also appear for an empty input and when a high threshold finds no clones. If a positional path is nonexistent, the building message appears before the fatal path error, while the searching message does not. Without verbose mode, successful valid-input runs have empty stderr.

Progress logs never enter text, plumbing, or HTML stdout, and clone results never enter stderr. Per-file parse diagnostics may accompany verbose logs on stderr in processing order.

Detected failures while writing the text footer or HTML header are fatal: exit 1 with the timestamped underlying write error. In particular, when stdout is `/dev/full`, text and HTML modes report `write /dev/stdout: no space left on device`. Text mode detects this on its footer write (earlier per-group formatting writes need not be the point of detection); HTML mode detects it while writing its required header.
