# Clarified specification for `executable`

The required artifact is a runnable command-line program named exactly `executable`. It is a single-purpose HTML-to-Markdown converter. All text input and output described below is UTF-8.

## Spec 1

The program has one conversion mode and no subcommands. Options are supplied directly to `executable`; bare positional arguments (including words such as `convert`, `help`, and `version`) are invalid. The supported interface is:

```text
-v, --version
--help
--input PATH
--output PATH
--output-overwrite
--domain URL
--exclude-selector SELECTOR       (repeatable)
--include-selector SELECTOR       (repeatable)
--opt-strong-delimiter VALUE
--plugin-strikethrough
--plugin-table
--opt-table-cell-padding-behavior VALUE
--opt-table-header-promotion
--opt-table-newline-behavior VALUE
--opt-table-presentation-tables
--opt-table-skip-empty-rows
--opt-table-span-cell-behavior VALUE
```

For value options, both `--name value` and `--name=value` forms work. `--` ends option parsing; every token after it is consequently a positional argument and is rejected. Successful conversions and informational flags exit 0. Usage, validation, and I/O failures exit 1. Successful conversion writes no stderr; failures write no conversion data to stdout. There must be no ANSI color sequences.

## Spec 2

`--version` prints the following bytes to stdout and exits 0 with empty stderr. `-v` is the short form and has the same version-reporting behavior.

```text
html2markdown

GitVersion:  dev
GitCommit:   none
BuildDate:   unknown
```

There is one newline after `unknown` and no leading newline.

## Spec 3

`--help` takes precedence even if a later option is invalid (for example, `--help --bogus` still succeeds), prints the following byte-exact text to stdout, and writes nothing to stderr. The output begins with one newline and ends with two newlines. The line ending in `malicious content.` has one ASCII space immediately before its newline.

```text

# html2markdown - convert html to markdown [version dev]

Convert HTML to Markdown. Even works with entire websites!

## Basics

By default the "Commonmark" Plugin will be enabled. You can customize the options,
for example changing the appearance of bold with --opt-strong-delimiter="__"

Other Plugins can also be enabled. For example "GitHub Flavored Markdown" (GFM)
extends Commonmark with more features.

## Relative / Absolute Links

Use --domain="https://example.com" to convert *relative* links to *absolute* links.
The same also works for images.

## Escaping

Some characters have a special meaning in markdown. The library escapes these — if necessary.
See the documentation for more info.

## Security

Once you convert this markdown *back* to HTML you need to be careful of malicious content. 
Use a HTML sanitizer before displaying the HTML in the browser!


## Examples

    echo "<strong>important</strong>" | html2markdown

    curl --no-progress-meter http://example.com | html2markdown


    html2markdown --input file.html --output file.md

    html2markdown --input "src/*.html" --output "dist/"


## Flags

    -v, --version
        show the version of html2markdown and exit

    --help

    --input PATH
        Input file, directory, or glob pattern (instead of stdin)

    --output PATH
        Output file or directory (instead of stdout)

    --output-overwrite
        Replace existing files

    If --input is a directory or glob pattern, --output must be a directory.



    --domain
        The url of the web page, used to convert relative links to absolute links.

    --exclude-selector
        css query selector to exclude parts of the input

    --include-selector
        css query selector to only include parts of the input

    --opt-strong-delimiter
        Make bold text. Should <strong> be indicated by two asterisks or two underscores?
        "**" or "__" (default: "**")

    --opt-table-cell-padding-behavior
        [for --plugin-table] whether cells in the tables should include extra padding for visual continuity: "aligned", "minimal", or "none"

    --opt-table-header-promotion
        [for --plugin-table] first row should be treated as a header

    --opt-table-newline-behavior
        [for --plugin-table] how tables containing newlines should be handled: "skip" or "preserve"

    --opt-table-presentation-tables
        [for --plugin-table] whether tables with role="presentation" should be converted

    --opt-table-skip-empty-rows
        [for --plugin-table] omit empty rows from the output

    --opt-table-span-cell-behavior
        [for --plugin-table] how colspan/rowspan should be rendered: "empty" or "mirror"

    --plugin-strikethrough
        enable the plugin ~~strikethrough~~

    --plugin-table
        enable the plugin table



For more information visit the documentation:
https://github.com/Johanneskaufmann/html-to-markdown

```

The literal Markdown heading markers inside this fenced sample are part of the help output. Help describes flags, not commands, and must not contain headings such as `Commands:`, `Subcommands:`, or `Available commands`.

## Spec 4

When `--input` is absent, HTML is read from stdin, but stdin must actually have been supplied as a pipe. A supplied empty pipe is valid HTML input: conversion succeeds and stdout is exactly one newline. If there is neither `--input` nor a pipe (including stdin inherited from an empty terminal/device), exit 1, leave stdout empty, and report on stderr that the input “should be piped”. A supplied whitespace-only document also succeeds and produces only insignificant output whitespace.

When `--input` names exactly one regular file, read that file regardless of its extension and write the result to stdout unless `--output` is present. Relative and absolute paths, UTF-8 names, names with spaces or dots, long names (at least 200 characters before the extension), and input symlinks must work. An input path that is itself a directory is rejected; directory traversal is requested with a glob such as `directory/**/*.html`, not by naming the directory alone.

## Spec 5

With no `--output`, a successful conversion is written to stdout and ends in exactly one `\n`, including when the converted content is empty. With `--output FILE`, stdout is empty and the converted Markdown is written without an automatically added trailing newline. Missing parent directories for an output file are created recursively.

An existing output path is never replaced unless `--output-overwrite` is present. Without that flag, exit 1 and leave the existing bytes unchanged. With it, replace rather than append. A symlink used as the output path counts as an existing file; overwrite permission is required, and an allowed overwrite writes through the symlink without replacing the link itself.

An output pathname ending in `/` is explicitly a directory destination, even for one input file. Create it if needed and place an output named from the input basename inside it. An already-existing directory named without a trailing slash is an error and the message suggests the same path with `/`.

## Spec 6

`--input` is a filesystem glob expression. Support ordinary wildcards and recursive `**`; matching is case-sensitive. Respect the pattern rather than filtering matches by extension, follow input-file symlinks, and include matching dotfiles. A pattern with zero matches is an error. One match may go to stdout or a file; two or more matches require `--output` ending in `/`. Multiple inputs are never concatenated to stdout.

For directory output, convert every match and change the final input extension to `.md`; an extensionless basename gains `.md`. Preserve Unicode and long basenames. Create the output directory. If different matched paths would produce the same basename, create distinct `.md` names (one may use the plain basename and the others deterministic hash suffixes) so no conversion is lost. Apply overwrite protection separately to every destination. Writing `.md` files into the same directory that contains the matching source files is allowed.

## Spec 7

Parse input as forgiving HTML, not XML and not by regular-expression substitution. Tags are case-insensitive. Recover from unclosed, overlapping, incorrectly nested, and otherwise malformed markup in the same best-effort fashion as an HTML parser. For example:

```text
<p><strong><em>Bold then italic</strong></em></p>
=> ***Bold then italic***

<p>Unclosed paragraph<strong>Unclosed bold<em>Nested unclosed
=> Unclosed paragraph**Unclosed bold*Nested unclosed***
```

DOCTYPEs, processing declarations, CDATA wrappers, and comments do not appear in output. Attributes are never emitted merely because they occur on an element. Null characters embedded in text are removed (`Before\0After` becomes `BeforeAfter`). Other unusual control characters must not crash conversion. The implementation must preserve valid UTF-8, emoji, combining marks, right-to-left text/marks, mathematical symbols, and zero-width Unicode content without corrupting surrounding text.

## Spec 8

HTML whitespace semantics apply outside preformatted content. Collapse runs of spaces, tabs, CR/LF, indentation, and inline source newlines to one ordinary space where text needs separation. Trim leading/trailing block whitespace. Keep inline elements adjacent when the HTML has no separating whitespace and keep one space when the source supplies one. Collapse excessive blank lines so output never has three consecutive blank separator lines. Separate ordinary block elements with blank lines, but do not create blank content for empty blocks.

Examples (shown without stdout's final newline):

```text
<p>   Leading   spaces   here </p>       => Leading spaces here
<p>Line with\n newline</p>               => Line with newline
<p>One</p><p>Two</p>                     => One\n\nTwo
<p><span>A</span><span>B</span></p>      => AB
```

## Spec 9

Render `<h1>` through `<h6>` as ATX headings with one through six `#` characters and one following space. Heading levels are independent and need not be sequential. Normalize whitespace and `<br>` inside a heading to single spaces, then trim the content, except that a source newline immediately after an empty anchor is discarded along with the boundary around that anchor. Thus `<h2><a name="pub-methods"></a>\nPublic Member Functions</h2>` becomes `## []()Public Member Functions`, without a space after `[]()`. Preserve inline Markdown in headings. Omit empty and whitespace-only headings.

A literal `#` at the very end of heading content must be escaped so it is not an ATX closing marker; when several hashes end the heading, escape only the final one. A source backslash immediately before a final hash is itself escaped, so the output contains two backslashes before the hash. Required examples are:

```text
<h2>Line One<br>Line Two</h2>             => ## Line One Line Two
<h2>Section 2.3#</h2>                     => ## Section 2.3\#
<h1>Section 1.2##</h1>                    => # Section 1.2#\#
<h2>Already\#</h2>                       => ## Already\\#
<h3>The <code>main()</code> <em>function</em> and <strong>setup</strong></h3>
=> ### The `main()` *function* and **setup**
```

Headings and neighboring block elements have one blank line between them.

## Spec 10

Render paragraphs as block text; `<div>`, `<article>`, `<section>`, `<main>`, `<header>`, `<footer>`, `<nav>`, `<aside>`, `<address>`, `<details>`, `<figure>`, `<figcaption>`, `<dl>`, `<dt>`, and `<dd>` preserve their visible descendants and participate in block spacing. Thus `<dl><dt>Term</dt><dd>Definition</dd></dl>` becomes `Term\n\nDefinition`, and a caption before an image is separated from it by a blank line. `<summary>` instead preserves its descendants as a transparent inline container and does not itself create block spacing: `<summary>A</summary><summary>B</summary>` becomes `AB`.

`<hr>` is a block whose exact Markdown is `* * *`; it has blank-line separation from surrounding content. `<br>` inside ordinary paragraph text is a hard line break consisting of two spaces plus `\n`. Two or more consecutive `<br>` elements collapse to a single blank-line break. `<wbr>` produces no bytes, so `Before<wbr>After` becomes `BeforeAfter`.

Elements not assigned special Markdown syntax—including `span`, custom/web-component tags, `abbr`, `cite`, `mark`, `sub`, `sup`, `time`, `button`, `option`, `video`, `audio`, and SVG container/text elements—are transparent: discard the tags and attributes but recursively retain their text and recognized descendants using inline/block whitespace rules. This also applies to nested and self-closing unknown tags.

`<kbd>` is rendered as inline code from its plain descendant text; Markdown formatting of nested descendants is not retained. Consequently `Before<kbd>X<strong>Y</strong></kbd>After` becomes ``Before`XY`After``. A `<select>` similarly retains the plain text of its descendants but discards their Markdown formatting, so `Before<select>X<strong>Y</strong></select>After` becomes `BeforeXYAfter`.

## Spec 11

Completely suppress comments and the entire subtrees of `script`, `style`, `iframe`, `noscript`, and `textarea`. Their attributes and fallback/text content must not leak into Markdown. Suppression works at any nesting depth and for repeated or adjacent removed nodes.

The `head` wrapper itself is discarded but is not a subtree-suppression boundary: ordinary text and recognized descendants inside syntactic `<head>...</head>` tags remain renderable. For example, `Before<head title="ATTR">SECRET<b>nested</b></head>After` becomes `BeforeSECRET**nested**After`.

`input`, `link`, and `meta` are parsed as HTML void elements. Each element itself emits nothing, but source text and elements after its start tag are not its children and are therefore retained even if a matching end tag is present. Each of `Before<input title="ATTR">SECRET<b>nested</b></input>After`, the corresponding `link` form, and the corresponding `meta` form becomes `BeforeSECRET**nested**After`. Removal itself adds no text; for example `Input<input type="text">field` becomes `Inputfield`. Normal content before and after removed nodes remains intact.

## Spec 12

Render both `<strong>` and `<b>` with `**` on each side by default. Render both `<em>` and `<i>` with `*` on each side. Nested strong+em collapses to triple emphasis, for example `<strong><em>x</em></strong>` becomes `***x***`. Preserve intraword formatting without injecting spaces: `Un<strong>freakin</strong>believable` becomes `Un**freakin**believable`. Source newlines inside these inline elements normalize to spaces.

`--opt-strong-delimiter=__` changes both strong tags to `__` while emphasis stays `*`. The only valid values are exactly the ASCII strings `**` and `__`. If this option is repeated, the last value wins. Nested redundant formatting must not multiply delimiter pairs. Preserve correct nesting with links, headings, lists, and plugin formatting.

Compatibility details for adjacent formatting are observable: `<strong>Bold</strong><em>Italic</em><code>Code</code>` becomes `**BoldItalic**` followed immediately by `` `Code` ``, while explicit source spaces yield `**Bold** *Italic* `Code``. An empty `<span>` between that adjacent strong and emphasis has the same merged `**BoldItalic**` result.

## Spec 13

Use context-sensitive escaping for ordinary text, while delimiters created by HTML renderers remain active. Required ordinary-text results include:

```text
fake **bold**              => fake \*\*bold\**
opening [ bracket          => opening [ bracket
a source backslash         => \\
* at a word-opening point  => \*
~ that could open strike when the strike plugin is on => \~
```

Do not blindly escape every punctuation character: ordinary `_`, `#`, `+`, `-`, `.`, `!`, parentheses, a closing `]`, and asterisks surrounded as harmless punctuation can remain literal when they cannot acquire Markdown meaning. A raw or decoded greater-than/less-than sign in normal prose is represented safely as `&gt;`/`&lt;`, so `Text before > and after` becomes `Text before &gt; and after`. Inside code, use code-specific rules instead of ordinary escaping. Inside table cells, protect syntax-significant pipes.

Decode HTML character references before rendering. `&amp;`, `&quot;`, `&apos;`, numeric decimal/hex references, and ordinary named references become their Unicode characters; `<` and `>` are then safety-encoded as above in prose. `&nbsp;` becomes U+00A0 and is preserved between words, although whitespace-only/NBSP-only blocks disappear. Never double-encode an ampersand.

## Spec 14

Render inline `<code>` with backtick fencing. Collapse internal ordinary whitespace runs for inline code. Trim a single surrounding space when the code has non-space content (`<code> space </code>` becomes `` `space` ``), but preserve content that consists only of spaces (`<code>   </code>` becomes a backtick, three spaces, and a backtick). If content contains a backtick, choose a longer delimiter and include separating spaces; ``<code>`backtick`</code>`` becomes ```` `` `backtick` `` ````.

Render `<pre>` and `<pre><code>` as fenced blocks while preserving internal newlines and indentation. Use at least three backticks and choose a fence longer than any backtick run in the content. A `language-NAME` class on the nested `code` adds `NAME` immediately after the opening fence. Decode HTML entities within preformatted content so an encoded HTML sample is literal code. Examples:

````text
<pre><code class="language-python">def f():
    pass</code></pre>
=> ```python
def f():
    pass
```

<pre><code></code></pre>
=> ```

```
````

Code blocks nested in list items are indented two spaces and preceded by an indented blank line. Code blocks in blockquotes receive the quote prefix on fence/content lines according to the surrounding quote rendering.

## Spec 15

Render `<a>` as `[rendered children](href)` and add a nonempty title as `[children](href "title")`. Missing and empty `href` both produce empty parentheses; empty child content is retained as `[](href)`. Inline formatting stays inside the brackets. Adjacent links stay adjacent if no source whitespace separates them.

Preserve HTTP(S), `mailto:`, `tel:`, `ftp:`, data, query, and fragment information. Percent-encode URL characters that would break the Markdown destination; for example `javascript:alert('xss')` renders as `javascript:alert%28'xss'%29`, while `?query=value&other=test`, `#section`, and an existing `%20` remain meaningful and are not lost or double-encoded.

Replace each title-attribute newline with one ASCII space, but preserve leading and trailing spaces and do not collapse existing runs of spaces. For example, `title="  Example\n title  "` produces `[x](u "  Example  title  ")`. Omit an empty title. Choose double quotes normally; if the title contains double quotes but no single quote, use single-quote delimiters. If it contains both, use double-quote delimiters and backslash-escape internal double quotes. Examples:

```text
title="Example"                  => [x](u "Example")
title='Title with "double"'      => [x](u 'Title with "double"')
title="Title with 'single'"      => [x](u "Title with 'single'")
```

HTML parsing rules still apply to malformed attribute quoting; a backslash does not quote a `"` in HTML.

## Spec 16

`--domain BASE` resolves relative `href` and image `src` values using URL-reference semantics. Root-relative paths use the base origin; `./` and `../` are normalized against the base path; a base trailing slash does not create a double slash. Query strings, fragments, and existing `%` escapes survive. Absolute URLs and special schemes remain unchanged. Protocol-relative URLs remain directed at their named host rather than being prefixed as an ordinary path. An empty domain disables resolution. A non-URL-looking domain value is accepted rather than causing a conversion failure. If `--domain` occurs multiple times, the last value wins.

Examples:

```text
BASE https://example.com/path/ + ../page => https://example.com/page
BASE https://example.com       + /page   => https://example.com/page
BASE https://example.com       + page    => https://example.com/page
empty href with that BASE                 => https://example.com
```

The same logic applies to both links and images, and combines normally with selectors and other options.

## Spec 17

Render an `<img>` with a nonempty `src` as `![alt](src)`. An image whose `src` attribute is missing or empty emits no Markdown; for example, both `<img alt="x">` and `<img alt="x" src="">` produce only stdout's final newline when converted alone. Missing or empty alt text on a rendered image gives `![]`; an absolute/data source is retained and a relative source is eligible for `--domain` resolution. Use the ordinary `src` even when `srcset` is present. A nonempty `title` uses the same title whitespace and quote-selection rules as links: `![Photo](photo.jpg "Click to view")`. In particular, `<img src="photo.jpg" srcset="wrong.jpg 2x" title=" Click  to\nview ">` becomes `![](photo.jpg " Click  to view ")`. Multiple adjacent images follow source whitespace (a source newline between inline images collapses to a space). Image elements inside transparent containers such as `picture` and `figure` still render.

## Spec 18

Render unordered list items as `- ` and ordered list items as sequential `N. ` markers. An ordered list begins at its integer `start` attribute, otherwise 1. Put each item on its own line. A nested list is indented to the content column after its parent item's complete marker, and is separated from the parent's inline text by an empty line at that indentation. An unordered `- ` marker therefore adds two spaces, while an ordered `3. ` marker adds three. Mixed ordered/unordered nesting retains each list type.

Multiple paragraphs in an item are separated by an indented blank line; continuation paragraphs align two spaces past the item marker. Inline formatting, links, inline code, blockquotes, and fenced blocks remain usable within items. A single empty list or empty item produces no meaningful content; the adjacent-empty-list compatibility sequence in Spec 27 is an exception. Required shapes:

```text
- Parent
  
  - Child
    
    1. Grandchild

- Parent
  
  3. Child
     
     - Grandchild
```

## Spec 19

Render a blockquote by prefixing its Markdown lines with `> `. Blank lines within it use `> ` (trailing space allowed). Each nested blockquote adds another `> ` level; a direct double nesting is `> > Nested quote`. Source newlines in otherwise-inline quote text collapse to spaces, so `<blockquote>Line 1\nLine 2</blockquote>` is `> Line 1 Line 2`.

Preserve headings, paragraphs, lists, links, emphasis, and code inside quotes. A representative nested result is:

```text
> Outer quote
> 
> > Nested quote
```

For compatibility, a blockquote containing `<pre><code>and a code block\ninside</code></pre>` renders its opening fence and first code line with `> `, the second source line as `inside` without a quote marker, and its closing fence with `> `.

## Spec 20

Apply selector filtering before Markdown rendering. `--include-selector S` retains only every element matching `S`, with its full descendant subtree; unmatched siblings/ancestors do not contribute text. Repeated include selectors form a union. `--exclude-selector S` removes every matching element and its entire subtree; repeated excludes form a union. When both forms are present, first choose included subtrees, then remove exclusions within them. A nonmatching include produces empty converted output; a nonmatching exclude changes nothing.

Support comma-separated selector groups, tag names, `.class`, `#id`, combined `#id.class`, multiple classes, descendant combinators such as `.container .content`, and attribute equality selectors such as `[data-exclude="true"]`. Matching class tokens is independent of other classes on the element. Invalid CSS syntax is an error containing `invalid css selector`; an empty selector is an error containing `empty string`.

## Spec 21

The strikethrough plugin is disabled by default. Without `--plugin-strikethrough`, `<del>`, `<s>`, and `<strike>` are transparent and only their children render. With the flag, all three render as `~~children~~`. Empty strike nodes disappear and directly nested redundant strike nodes collapse to one delimiter pair. Source newlines inside strike content normalize to spaces.

Preserve nested formatting order:

```text
<del><strong>x</strong></del>       => ~~**x**~~
<del><em>x</em></del>               => ~~*x*~~
<del><strong><em>x</em></strong></del> => ~~***x***~~
<a href="u"><del>x</del></a>       => [~~x~~](u)
<del>go <a href="u">here</a></del> => ~~go [here](u)~~
```

Literal tilde escaping remains distinct from delimiters. Multiple struck regions, struck headings/list items/code/links, the custom strong delimiter, and the table plugin must compose without one feature disabling another.

## Spec 22

The table plugin is disabled by default. Without `--plugin-table`, table-related tags are transparent and their cells become ordinary flattened text governed by source whitespace; no pipe-table syntax is introduced. Cell boundaries do not themselves add spaces. Thus `<table>\n<tr><td>Cell 1</td><td>Cell 2</td></tr>\n<tr><td>Cell 3</td><td>Cell 4</td></tr>\n</table>` becomes `Cell 1Cell 2 Cell 3Cell 4`: the source newlines between rows provide spaces, while adjacent cells within each row remain adjacent. Likewise, `<table role="presentation"><tr><td>Layout</td><td>Table</td></tr></table>` becomes `LayoutTable`.

With `--plugin-table`, convert semantic tables to GitHub-style pipe tables except when the newline or presentation-table rules below select fallback rendering. Read rows from direct `tr` elements and from `thead`, `tbody`, and `tfoot`; retain order. Render inline Markdown (strong, emphasis, strike, code, and links) inside cells and escape table-significant content. Normalize source whitespace, including source newlines within cells, to spaces; rendered line breaks such as `<br>` are instead governed by Spec 23. Normalize rows to the table's column count and retain empty cells.

If any first-row cells are `th`, that row is the header. Otherwise insert an all-empty synthetic header followed by the mandatory separator; keep all source rows as data. A table containing only an explicit header still emits header and separator. The basic exact forms are:

```text
<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>
=> | A | B |
   |---|---|
   | 1 | 2 |

<table><tr><td>A</td><td>B</td></tr></table>
=> |   |   |
   |---|---|
   | A | B |
```

## Spec 23

Default table cell padding is `aligned`. For each column, find the longest rendered cell (including the header), pad all cell content to that width, and add one space on both sides. A separator cell is a run of hyphens equal to that padded field width, with a minimum of three. Thus cells `A`/`Value` produce fields visually aligned to width five plus the two outer spaces.

`--opt-table-cell-padding-behavior=minimal` uses exactly one space on each side without aligning columns; separator fields are `---`. `--opt-table-cell-padding-behavior=none` puts no spaces around cell content and still uses `---` separator fields. These exact examples apply:

```text
minimal: | A | B |       none: |A|B|
         |---|---|             |---|---|
         | X | Y |             |X|Y|
```

The allowed padding values are `aligned`, `minimal`, and `none`.

`--opt-table-header-promotion` treats the first data row as the header rather than inserting an empty header. `--opt-table-skip-empty-rows` removes rows whose cells are all empty/whitespace; without it, preserve such rows.

The accepted explicit newline values are `skip` and `preserve`; the default behavior is `skip`. An ordinary source newline within cell text is whitespace and is reduced to one space in either mode, so a cell containing `A\n  B` renders as `A B` in a pipe table. A rendered line break such as `<br>` is different. With `skip` (including the default), its presence prevents pipe-table conversion and selects the table plugin's fallback rendering. For the exact input `<table><tr><th>H</th></tr><tr><td>A\n  B<br>C</td></tr></table>`, that fallback is `H\n\nA B  \nC` (plus stdout's final newline). With `preserve`, the same input remains a pipe table and the line break is represented by literal `<br />`, retaining the two spaces produced before the break:

```text
| H            |
|--------------|
| A B  <br />C |
```

## Spec 24

By default, a `colspan` or `rowspan` creates the required number of placeholder cells, whose content is empty. `--opt-table-span-cell-behavior=empty` selects that behavior explicitly. `mirror` duplicates the originating cell's rendered content into every horizontal or vertical position it spans. For example:

```text
empty:  | Merged |        |     mirror: | Merged | Merged |
        |--------|--------|             |--------|--------|
        | A      | B      |             | A      | B      |
```

The allowed span values are `empty` and `mirror`.

A table with `role="presentation"` is not converted to pipe-table syntax by default. Without the table plugin its tags are transparent under Spec 22, so `<table role="presentation"><tr><th>A</th><th>B</th></tr><tr><td>X</td><td>Y</td></tr></table>` becomes `ABXY`. With `--plugin-table`, the presentation-table fallback keeps cells adjacent within a row but makes rows separate blocks, so that same source becomes `AB\n\nXY`. `--opt-table-presentation-tables` forces normal pipe-table conversion instead. Table options can be combined (for example promotion + skipping + minimal padding), and option order does not disable any of them.

## Spec 25

Every `--opt-table-*` flag requires `--plugin-table`; otherwise exit 1 and include `requires --plugin-table to be enabled` in stderr. With the plugin enabled, invalid enum values exit 1 with these messages as applicable:

```text
error: error while initializing "table" plugin: unknown value "VALUE" for span cell behavior
error: error while initializing "table" plugin: unknown value "VALUE" for newline behavior
error: error while initializing "table" plugin: unknown value "VALUE" for cell padding behavior
```

An invalid strong delimiter exits exactly 1 and includes both the supplied value and the rule, in this form:

```text
error: invalid value for --opt-strong-delimiter="VALUE" must be exactly 2 characters of "**" or "__"
```

This rejects wrong length, mixed delimiters, spaces, arbitrary ASCII, and Unicode lookalikes. Duplicate `--input` or duplicate `--output` options are errors containing `another value has already been set`; duplicate `--domain` is permitted and last-wins. A value-taking flag with no following value exits 1 with `flag needs an argument`. Empty `--input`/`--output` values are rejected and mention `empty string`. In particular, with piped input, `--output ""` exits 1, leaves stdout empty, and writes exactly `\nerror: invalid value "" for flag -output: empty string\n\n` to stderr. Unknown options exit 1, leave stdout empty, and stderr contains `unknown flag` and the option spelling.

## Spec 26

Use the following byte-exact diagnostic behavior for argument and filesystem failures. Every diagnostic described in this section exits 1, leaves stdout empty, and writes one leading `\n`, then the displayed content, then two final `\n` bytes. The fenced blocks below show only the content between that common leading and trailing framing.

For positional tokens `unexpected arguments`, the displayed content is:

```text
error: unknown arguments: unexpected arguments

Here is how you can use the CLI:

    echo "<strong>important</strong>" | html2markdown
```

For an input pattern with no matches:

```text
error: no files found matching pattern "PATTERN"

Here is how you can use a glob to match multiple files:

    html2markdown --input "src/*.html" --output "dist/"
```

For a directory supplied as input, use `error: input path "PATH" is a directory, not a file`, followed by the same blank line and glob example. In these two input diagnostics, `PATH` or `PATTERN` is the complete supplied string, including all directory components.

For an existing output file, use `error: output path "PATH" already exists. Use --output-overwrite to replace existing files`, with the complete supplied path. Two output-directory diagnostics instead display only the final path component. For multiple inputs with an output that lacks a directory suffix, the content is `error: when processing multiple input files, --output "BASENAME" must end with "BASENAME/" to indicate a directory`. For example, an absolute output ending in `joined.md` is reported as `joined.md` and `joined.md/`. If output was omitted entirely, use `error: when processing multiple input files --output needs to be a directory` and append the blank line and glob example shown above.

For an existing directory passed without `/`, use the final path component in this exact content:

```text
error: path "BASENAME" exists and is a directory, did you mean "BASENAME/"?

The --output must end with "/" to indicate a directory
```

## Spec 27

The converter must be robust on realistic complete webpages and scale without changing semantics: handle at least 100 nested tags, at least 100 repeated heading/paragraph/list sections, a 10,000-character line, thousands of paragraphs, wide/tall tables, and multi-megabyte HTML files within ordinary test timeouts. Whole-page wrappers do not alter body conversion. Suppress `script`/`style` metadata and the other subtrees named in Spec 11, but do not treat the `head` wrapper itself as a suppression boundary; preserve its ordinary text and recognized descendants as described there. Preserve all visible body text, recognized formatting, SVG text descendants, buttons, template-like literal text, and malformed-body recovery. Processing must not silently truncate or omit later sections.

Except for the explicitly stated compatibility cases below, empty semantic elements (`p`, headings, strong/emphasis/strike, lists, and blockquotes) disappear; empty code blocks and empty links retain their syntactically meaningful forms. One legacy regression input is byte-exact: the sequence

```html
<p></p>
<strong></strong>
<em></em>
<a href="https://example.com"></a>
<ul></ul>
<ol></ol>
```

must produce on stdout exactly:

```text
[](https://example.com)

<!--THE END-->
```

including the final newline.

A second byte-exact compatibility case is the adjacent empty-list sequence `<p>A</p><ul><li></li></ul><ol></ol><p>B</p>`. It writes:

```text
A

<!--THE END-->

B
```

including the final newline. A lone empty `ul` or `ol`, including a list containing one empty `li`, does not emit this marker.
