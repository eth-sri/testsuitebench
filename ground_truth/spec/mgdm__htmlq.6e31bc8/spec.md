# Clarified specification for `executable`

The required artifact is a runnable file named exactly `executable`. It implements the `htmlq` 0.4.0 single-purpose command described below. Unless a section says otherwise, successful invocations exit with status 0 and write nothing to standard error. All output is UTF-8.

## Spec 1

`executable` is a command-line HTML query tool, not a command with subcommands. Its invocation grammar is:

```text
executable [FLAGS] [OPTIONS] [--] [selector]...
```

It accepts these flags and options, with the short and long spellings being aliases:

- `-h`, `--help`
- `-V`, `--version`
- `-B`, `--detect-base`
- `-w`, `--ignore-whitespace`
- `-p`, `--pretty`
- `-t`, `--text`
- `-a ATTRIBUTE`, `--attribute ATTRIBUTE`, and `--attribute=ATTRIBUTE`
- `-b BASE`, `--base BASE`, and `--base=BASE`
- `-f FILE`, `--filename FILE`, and `--filename=FILE`
- `-o FILE`, `--output FILE`, and `--output=FILE`
- repeatable `-r SELECTOR`, `--remove-nodes SELECTOR`, and `--remove-nodes=SELECTOR`

Options may occur before or after positional selector pieces. Compatible short Boolean flags may be combined, so `-wt` means `-w -t`. `--` ends option recognition; every later token is positional even if it starts with `-`. Words such as `add`, `list`, `remove`, and `help` without a leading dash are selectors, not subcommands.

## Spec 2

`-h` and `--help` exit 0, write nothing to stderr, end with a newline, and produce exactly the following stdout (including capitalization, indentation, blank lines, and wrapping):

```text
htmlq 0.4.0
Michael Maclean <michael@mgdm.net>
Runs CSS selectors on HTML

USAGE:
    executable [FLAGS] [OPTIONS] [--] [selector]...

FLAGS:
    -B, --detect-base          Try to detect the base URL from the <base> tag in the document. If not found, default to
                               the value of --base, if supplied
    -h, --help                 Prints help information
    -w, --ignore-whitespace    When printing text nodes, ignore those that consist entirely of whitespace
    -p, --pretty               Pretty-print the serialised output
    -t, --text                 Output only the contents of text nodes inside selected elements
    -V, --version              Prints version information

OPTIONS:
    -a, --attribute <attribute>         Only return this attribute (if present) from selected elements
    -b, --base <base>                   Use this URL as the base for links
    -f, --filename <FILE>               The input file. Defaults to stdin
    -o, --output <FILE>                 The output file. Defaults to stdout
    -r, --remove-nodes <SELECTOR>...    Remove nodes matching this expression before output. May be specified multiple
                                        times

ARGS:
    <selector>...    The CSS expression to select [default: html]
```

Help takes precedence if it is reached after ordinary flags or before extra positional values following `--`: it displays help and exits 0 without reading input. Argument errors encountered before the help flag take precedence instead. In particular, `--unknown --help` exits 1 with empty stdout and the unknown-argument diagnostic described in Spec 20, whereas `--help --unknown` displays help and exits 0.

## Spec 3

`-V` and `--version` exit 0, use no input, write nothing to stderr, and write exactly:

```text
htmlq 0.4.0
```

## Spec 4

By default the complete input is read from standard input. `-f/--filename FILE` instead reads `FILE` and ignores stdin. The special filename `-` means stdin. Relative filenames are resolved from the executable's current working directory, and names containing spaces are accepted.

Output goes to stdout by default. `-o/--output FILE` creates or truncates `FILE`, writes all result bytes there, and leaves stdout empty. The special output name `-` means stdout. Input and output options may be combined, including text or attribute modes.

The program must comfortably handle at least 10,000 matching elements, documents of hundreds of kilobytes, 100 levels of nesting, long text and selector strings, and Unicode filenames/content within the test timeout.

## Spec 5

HTML is decoded as UTF-8, replacing malformed byte sequences with U+FFFD rather than rejecting the document. It is parsed as a complete, forgiving HTML5 document. Apply normal HTML5 tree construction and error recovery: insert missing `html`, `head`, `body`, and table-container elements where HTML5 requires them; implicitly close elements such as adjacent paragraphs; repair unclosed, mismatched, misnested, and orphaned tags; accept quoted and unquoted attributes; retain comments, doctypes, script/style text, whitespace text nodes, and Unicode.

Empty input therefore parses to an empty document tree, and the default query produces exactly:

```text
<html><head></head><body></body></html>
```

Plain text or an HTML fragment is placed into the implied document body. For example, querying the default selector on `just plain text` includes that text inside the synthesized body, while querying `div` on `<div>x</div>` returns the `div` itself.

## Spec 6

All positional selector tokens are joined with one ASCII space into one CSS selector expression. If there are no positional tokens, the expression is `html`. Consequently, arguments `p` and `span` mean the descendant selector `p span`, not two independent queries. To request alternatives, the caller uses one comma-separated selector such as `p, span`. Arguments `.a` and `.b` similarly become `.a .b` and produce no match when the two classes occur only on sibling elements.

A selector-list query emits matches once each in document order, regardless of the order of alternatives, and deduplicates an element that satisfies several alternatives. A valid selector with no matches succeeds and emits no bytes.

## Spec 7

Support HTML CSS type, universal, class, ID, and compound selectors. This includes examples such as:

```text
p
*
.item
#main
div.item
div#main.item.featured
a.link[href][title]
```

HTML type names are matched according to HTML selector rules. Class matching treats the `class` value as a whitespace-separated set, while IDs and ordinary attribute values retain their value semantics. Names containing hyphens and underscores, custom HTML element names, data attributes, and all ordinary HTML5 element/attribute names must work.

## Spec 8

Support attribute presence selectors and all of these value operators:

- `[x]`: attribute is present.
- `[x="v"]`: exact equality.
- `[x~="v"]`: `v` is one whitespace-delimited word.
- `[x|="v"]`: value is `v` or starts with `v-`.
- `[x^="v"]`: starts with `v`.
- `[x$="v"]`: ends with `v`.
- `[x*="v"]`: contains `v` as a substring.

Attribute constraints can be chained and combined with type, class, ID, combinator, and pseudo-class constraints. Quoted selector values may contain spaces, dots, slashes, underscores, dashes, brackets, and other ordinary punctuation. The ASCII-insensitive modifier is supported, e.g. `[title="test" i]` matches `title="TEST"`.

## Spec 9

Support the four standard combinators, arbitrarily chained and with surrounding whitespace:

- `A B`: descendant
- `A > B`: direct child
- `A + B`: immediately following element sibling
- `A ~ B`: any following element sibling

Examples that must behave normally include `div ul li span`, `body > div > p`, `.a > .b > .c > p#deep`, `h1 + p`, `h1 ~ p`, `div > * > p`, and compound selectors on either side of a combinator.

## Spec 10

Support these structural pseudo-classes with normal CSS one-based element indexing:

```text
:root
:empty
:first-child        :last-child        :only-child
:first-of-type      :last-of-type      :only-of-type
:nth-child(...)
:nth-last-child(...)
:nth-of-type(...)
:nth-last-of-type(...)
:not(...)
```

The `nth` arguments accept integer positions, `odd`, `even`, and `an+b` forms such as `2n`, `2n+1`, `3n`, `3n+2`, `n`, and `n+3`. Type-based variants count only siblings of the same element type. `:not` accepts tested simple or compound arguments such as `.skip`, `[href]`, `:first-child`, and `:empty`, and can occur inside a longer compound/descendant selector. Pseudo-classes may be combined with a type, class, ID, or attribute selector.

The state pseudo-class `:disabled` is syntactically accepted but matches no elements. Thus `input:disabled` produces no output even for `<input id="disabled" disabled>`.

## Spec 11

Before any output-mode formatting, the program processes matching element nodes in document order. With no attribute, text, or pretty option, serialize each surviving matched element as HTML and append exactly one `\n`. Multiple matches have no blank separator.

Use HTML serialization, not source slicing. Element and attribute names use the parsed HTML form, attribute values use double quotes, and void elements such as `area`, `base`, `br`, `col`, `embed`, `hr`, `img`, `input`, `link`, `meta`, `source`, `track`, and `wbr` have no closing tag and no XML `/>`. Within a start tag, ordinary HTML attributes are emitted in ascending lexicographic order of their normalized parsed names, not in source order; boolean attributes have the value `""`. For example, `<input id="email" type="email" name="email" required>` serializes as `<input id="email" name="email" required="" type="email">`. Preserve parsed child order, comments, and meaningful whitespace. Escape markup-significant characters in text and attributes. For example:

```text
input:  <div class='x'><p>Text &amp; more</p></div>
query:  div
output: <div class="x"><p>Text &amp; more</p></div>\n
```

If the default `html` node is selected, its full parsed subtree is serialized. A doctype is outside the `html` node and is therefore not included merely by selecting `html`.

## Spec 12

`-a/--attribute NAME` switches to attribute mode. For each surviving matched element, look up exactly that parsed attribute name. If present, emit its decoded value followed by `\n`; if missing, emit nothing for that element. An explicitly empty value emits one blank line. Do not include the attribute name, quotes, tags, or element text.

Examples:

```text
input:  <a href="/one">1</a><a>2</a><a href="">3</a>
query:  -a href a
output: /one\n\n
```

Character references are decoded by HTML parsing, so `title="Test &quot;quotes&quot;"` extracts as `Test "quotes"`. A multiword class value is emitted intact. Attribute mode takes precedence over `--text` and `--pretty`. URL rewriting described later occurs before the value of a surviving link element is extracted.

An explicit empty equals-form operand, `--attribute=`, counts as a supplied attribute name: parsing succeeds, attribute mode is selected, and a normal document emits no bytes because no selected element has an attribute with that empty name. This differs from writing `--attribute` with no following operand, which is the missing-value error in Spec 20.

## Spec 13

`-t/--text` switches to text mode when attribute mode is absent. For each surviving matched element, visit every descendant text node in tree order and concatenate its decoded text exactly; tags, comments, and markup are omitted. Text in nested elements, `pre`, `script`, and `style` participates. `<br>` itself contributes no text. Append one final `\n` after the concatenated result for each match, including an empty match.

Thus `<div>Hello <b>World</b></div>` produces `Hello World\n`, three selected `<p>` elements produce one result line per `p`, and character references such as `&lt;` and `&amp;` appear as literal `<` and `&` in text output. Whitespace is not trimmed or normalized by default.

`--pretty` and all base-URL options have no direct formatting effect in text mode. Text mode takes precedence over pretty mode.

## Spec 14

`-w/--ignore-whitespace` affects only text mode. Without it, follow Spec 13 exactly. With it, examine each descendant text node separately:

1. If trimming the node according to Unicode whitespace yields an empty string, skip that node entirely.
2. Otherwise append the node's original, untrimmed text and then append `\n`.
3. After all text nodes of that selected element, append the usual final `\n` from text mode.

For example, `<div>  <p>Text</p>  </div>` queried with `-t` gives `  Text  \n`; queried with `-tw` it gives `Text\n\n`. The flag does nothing to compact HTML, pretty HTML, or attribute output.

## Spec 15

`-p/--pretty` applies only when neither attribute nor text mode is active. Pretty-print every selected node independently, then append `\n`. Formatting uses a two-space depth increment and the following exact streaming rules:

- Keep an indentation depth, initially zero, and a Boolean `previous_was_block`, initially false.
- On an element start: if the element is block-like **or** `previous_was_block` is true, emit `\n` followed by the current number of spaces; then add 2 to the depth and serialize the start tag normally.
- On an element end: subtract 2. For an inline element, set `previous_was_block` false and serialize the end tag immediately. For a block-like element, first emit `\n` and the current indentation, set `previous_was_block` true, and then serialize its end tag.
- Discard any text node consisting entirely of whitespace. For other text, if `previous_was_block` is true, first emit `\n` and current indentation; then set it false and serialize the original text unchanged.
- Serialize comments, doctypes, and processing instructions in place without changing the block-state flag.

The inline set is exactly: `a`, `abbr`, `acronym`, `audio`, `b`, `bdi`, `bdo`, `big`, `button`, `canvas`, `cite`, `code`, `data`, `datalist`, `del`, `dfn`, `em`, `embed`, `i`, `iframe`, `img`, `input`, `ins`, `kbd`, `label`, `map`, `mark`, `meter`, `noscript`, `object`, `output`, `picture`, `progress`, `q`, `ruby`, `s`, `samp`, `script`, `select`, `slot`, `small`, `span`, `strong`, `sub`, `sup`, `svg`, `template`, `textarea`, `time`, `u`, `tt`, `var`, `video`, `wbr`. Every other element is block-like.

For example, pretty-printing `<div><p>Hello</p><p>World</p></div>` produces:

```text

<div>
  <p>Hello
  </p>
  <p>
    World
  </p>
</div>
```

The initially blank line is intentional for a selected block element. Inline runs such as `Text <strong>bold</strong>` remain together.

## Spec 16

`-r/--remove-nodes REMOVAL_SELECTOR` is repeatable. Join all supplied removal selector strings with commas into one selector list. The primary selector results are consumed by a live document traversal, and removal participates after the primary query is established but before URL rewriting and rendering:

1. For each primary match reached, search that node's inclusive subtree for the first element matching the removal selector list.
2. If none is found, render that primary match normally and continue the traversal.
3. If one is found, detach that one removal match. Do not render the current primary match, and terminate the primary traversal immediately; no later primary match, including a nested or sibling match, is visited or rendered.

This is a prefix-stopping filter, not a “serialize the parent minus all unwanted descendants” operation. Clean primary matches before the first removal are emitted, while the match that triggers removal and every match after it are omitted. For example, `.item --remove-nodes .ad` on `<div class="item"><p>Content 1</p></div><div class="item ad"><p>Content 2</p></div><div class="item"><p>Content 3</p></div>` emits exactly `<div class="item"><p>Content 1</p></div>\n`. If the selected node itself matches the removal expression, the inclusive search finds it, detaches it, emits nothing for it, and stops traversal. Multiple removal options match any alternative. A syntactically invalid removal expression is treated as matching nothing and does not fail the command.

## Spec 17

The effective base URL is chosen after parsing and before rendering:

- With `--base URL` alone, use it only if it parses as an absolute URL.
- With `--detect-base` alone, inspect the first parsed `base` element. Use its `href` only if present and parseable as an absolute URL.
- With both, a valid detected first-base `href` takes precedence; otherwise fall back to the explicit base if it is valid.
- With neither, there is no base.

An invalid explicit or detected base is silently ignored; it does not make the command fail. If the first `base` element lacks `href` or has an invalid `href`, detection yields no URL rather than searching later `base` elements. If several valid base elements exist, the first wins.

## Spec 18

For each surviving primary matched element, and only that element (not all descendants), URL rewriting occurs before rendering. Rewrite only an `href` on an `a`, `area`, or `link` element. Do not rewrite `src`, `data-href`, or `href` on other element types such as `div` or `span`. Consequently selecting an anchor rewrites it, while selecting a containing `div` leaves a nested anchor untouched unless that anchor is itself also a primary match.

Resolve an eligible `href` against the effective base with standard URL-reference resolution:

- `/x` replaces the path from the origin.
- `x`, `./x`, and `../x` resolve against the base path with dot segments normalized.
- `//host/x` inherits the base scheme.
- `?query` and `#fragment` replace or augment the appropriate base components.
- An empty `href` resolves to the base URL.
- Already absolute schemes such as `http`, `https`, `mailto`, `tel`, `javascript`, `data`, and `blob` remain absolute rather than being prefixed.
- Unicode in URL paths is UTF-8 percent encoded; query strings, fragments, ports, and user information are preserved according to normal URL resolution.
- If joining a reference fails, use the base URL itself.

There is one special rule: if `href` begins with four or more `/` characters, remove **all** leading slashes and use the remaining string directly, without adding the base. Thus `////example.com/path`, `/////example.com/path`, and `////////example.com/path` all become `example.com/path`. Three leading slashes are not special and normal URL resolution applies (against `https://example.com`, `///path` becomes `https://example.com/`).

## Spec 19

Processing precedence is fixed and observable:

1. Parse CLI arguments; help/version may terminate here.
2. Open the chosen input and output streams.
3. Parse the complete HTML document.
4. Determine the effective base URL.
5. Evaluate the primary selector in document order.
6. Consume primary matches through the live traversal. For each reached match, apply removal filtering; the first successful removal detaches its target, suppresses that current match, and ends the traversal.
7. For a surviving match, rewrite that node's eligible `href` if a base exists.
8. Render it using the first applicable mode: attribute, then text, then pretty, otherwise compact HTML.

This precedence means `-a href -t a` emits only href values; `-t -p p` is identical to text mode; `-w` without text changes nothing; base options do not alter text; and the first removal-triggering match and all later primary matches produce no attribute, text, pretty, or compact result.

## Spec 20

Command-line syntax errors are reported by a clap-2-style parser on stderr with stdout empty and exit status 1. Unknown flags must include `Found argument 'FLAG'` and a `USAGE:` section. Supplying any of `-a/--attribute`, `-b/--base`, `-f/--filename`, `-o/--output`, or `-r/--remove-nodes` without its value must include `requires a value` and `USAGE:`. `--attribute` may not occur more than once; the exact repeated-attribute diagnostic is:

```text
error: The argument '--attribute <attribute>' was provided more than once, but cannot be used multiple times

USAGE:
    executable --attribute <attribute>

For more information try --help
```

The other singular options likewise represent one value, while removal is explicitly repeatable.

## Spec 21

A syntactically invalid **primary** CSS selector is fatal: stdout is empty, the process exits 101, and stderr contains a Rust-style panic report including both `panicked at src/main.rs` and `Failed to parse CSS selector`. This is distinct from a valid selector that matches nothing and from an invalid removal selector as described above.

Failure to open an explicitly named input file is also fatal with exit 101 and empty stdout. Its stderr contains `panicked`; for a missing path, it contains this exact Rust debug error line:

```text
should have opened input file: Os { code: 2, kind: NotFound, message: "No such file or directory" }
```

Failure to create an output file, such as a path inside a nonexistent directory, is fatal and nonzero with a corresponding output-file creation panic. Successful no-match and empty-content cases remain status 0.
