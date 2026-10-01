# Clarified specification for `executable`

## Spec 1

The deliverable is a directly runnable command-line program named exactly `executable`. It implements `xq`, a formatter and extractor for XML, HTML, and JSON. It must accept raw bytes from standard input or one or more file paths, write ordinary results to standard output, and use exit status `0` for successful work. Unless a mode below expressly says otherwise, successful output ends in one newline and successful execution produces no standard-error output. It must operate noninteractively and must not invoke a pager when output is captured or piped.

The program must be able to process Unicode documents, inputs with at least 100 levels of XML nesting, XML containing at least 1,000 sibling records, individual lines and values of at least 100,000 bytes, and JSON arrays/objects of ordinary test-suite size without truncation, hanging, or stack failure.

## Spec 2

The supported command line is:

```text
executable [flags] [file ...]
```

The public flags and aliases are:

```text
-a, --attr STRING
-c, --color
    --compact
-d, --depth INT
-e, --extract STRING
-h, --help
-m, --html
-i, --in-place
    --indent INT
-j, --json
    --no-color
-n, --node
-q, --query STRING
    --tab
-v, --version
-x, --xpath STRING
```

Long value flags accept both `--flag value` and `--flag=value`; short value flags accept a following argument. Flags may precede, follow, or be interspersed with path arguments. A bare `--` ends flag parsing, so a following string such as `--notaflag` is treated as a file name. Every positional argument is a file to process; there is no one-positional limit outside in-place mode.

An unknown flag is an error with nonzero status, no formatted document result, and text containing `Error:` and `unknown flag`. A value-taking flag without a value is an error containing `Error:` and `flag needs an argument`. A non-integer supplied to `--indent` or `--depth`, and a value supplied to a boolean flag (for example `--compact=maybe`), is a nonzero command-line error containing `Error:`. Diagnostics for invalid typed values may additionally say `invalid argument`.

## Spec 3

`-h` and `--help` print exactly the following UTF-8 text to standard output, including spacing, blank lines, ordering, capitalization, and the final newline; they exit `0` and write nothing to standard error. Help takes precedence over other otherwise valid flags such as `--json`.

```text
Command-line XML and HTML beautifier and content extractor

Usage:
  xq [flags]

Flags:
  -a, --attr string      Extract an attribute value instead of node content for provided CSS query
  -c, --color            Force colorful output
      --compact          Compact JSON output (no indentation)
  -d, --depth int        Maximum nesting depth for JSON output (-1 for unlimited) (default -1)
  -e, --extract string   Extract a single node from XML
  -h, --help             Print this help message
  -m, --html             Use HTML formatter
  -i, --in-place         Format file in place
      --indent int       Use the given number of spaces for indentation (default 2)
  -j, --json             Output the result as JSON
      --no-color         Disable colorful output
  -n, --node             Return the node content instead of text
  -q, --query string     Extract the node(s) using CSS selector
      --tab              Use tabs for indentation
  -v, --version          Print version information
  -x, --xpath string     Extract the node(s) from XML
```

## Spec 4

`-v` and `--version` exit `0`, write nothing to standard error, and print exactly:

```text
xq version 1.4.0
```

with one final newline.

When no paths are given and standard input is not an actual supplied stream of document bytes, the program displays the same help/usage behavior and exits `0`. When standard input is explicitly connected to a pipe, it is the input source even if it contains no bytes; the empty-stream behavior is specified separately below.

## Spec 5

Input type is determined independently for each input. Leading ordinary whitespace is ignored for detection. JSON objects and arrays are recognized from their leading `{` or `[`. Markup beginning with an XML declaration or an ordinary non-HTML element is XML. HTML is recognized from case-insensitive `<html>` document structure; an HTML doctype alone does not force tolerant HTML parsing. In particular, `<!DOCTYPE html><root><child>text</child></root>` is handled by the XML formatter and produces `<!doctype html>\n<root>\n  <child>text</child>\n</root>\n`, whereas a doctype followed by an `<html>` root is HTML. HTML files must also be recognized without `--html`. A file extension may support detection but is not sufficient by itself: XML, HTML, and JSON all work from standard input.

`-m`/`--html` forces tolerant HTML parsing and formatting, even if the supplied file has an `.xml` name or XML-like contents. Without that flag, well-formed markup that is not recognized as HTML is parsed as XML. `-j`/`--json` controls the requested output representation; it does not mean that the input must be JSON. Thus XML or HTML becomes JSON, while native JSON is reformatted as JSON.

A UTF-8 BOM before XML is accepted and preserved as the first UTF-8 BOM in the formatted output. A BOM before JSON is not silently accepted; it produces a JSON invalid-character error. XML declarations naming encodings such as UTF-8 and windows-1251 are honored while decoding, and textual output is UTF-8. There is a detection compatibility exception for a declaration-less document whose content contains a CDATA opener: `<r><![CDATA[plain text]]></r>` is sent to the JSON parser, exits `1`, writes exactly `Error: invalid character '<' looking for beginning of value\n` to standard output, and writes nothing to standard error. Prefixing the same document with `<?xml version="1.0"?>` makes it XML.

## Spec 6

With no indentation flags, the indent unit is two ASCII spaces. `--indent N` selects `N` spaces per structural depth, where `N` is an integer in the inclusive range 0 through 8. Values outside that range exit `1`, put no document output on standard output, and put this line on standard error:

```text
Error: indent should be between 0-8 spaces
```

`--indent 0` is compact structural formatting: XML/HTML elements are not separated by formatting newlines and the complete simple document is on one line, followed by the usual final newline. `--tab` selects exactly one tab per depth and takes precedence over every numeric indent setting regardless of flag order. Indentation choices apply consistently to XML, tolerant HTML, native JSON pretty-printing, and node-mode query output. Noncompact XML/HTML-to-JSON conversion is an exception: its serializer always uses two spaces, as detailed in Spec 15.

For example:

```text
input:  <root><child>text</child></root>
default output:
<root>
  <child>text</child>
</root>

--indent 0 output:
<root><child>text</child></root>

--tab output:
<root>
\t<child>text</child>
</root>
```

Here `\t` in the example denotes one literal tab byte.

## Spec 7

Plain output contains no ANSI control sequences. This is the normal behavior when standard output is captured or piped, and it is guaranteed by `--no-color`. `-c`/`--color` forces ANSI coloring even on a pipe and applies to XML, HTML, JSON, and extracted output where applicable. If both `--color` and `--no-color` are supplied on the command line, force-color takes precedence regardless of their order. Command-line versus configuration precedence is specified separately in Spec 8.

For XML/HTML, tag syntax uses ANSI yellow (`ESC[33m`) with resets (`ESC[0m`); attribute values use ANSI green (`ESC[32m`). The exact colored form of `<root><child>text</child></root>` at default indent is:

```text
ESC[33m<rootESC[0mESC[33m>ESC[0m
  ESC[33m<childESC[0mESC[33m>ESC[0mtextESC[33m</child>ESC[0m
ESC[33m</root>ESC[0m
```

where each written `ESC` means the single byte `0x1b`, not the three letters. An opening tag with `class="test"` is colored as `ESC[33m<divESC[0m classESC[32m="test"ESC[0mESC[33m>ESC[0m`. Colored JSON must contain valid ANSI CSI color sequences and, after removing sequences matching `ESC\[[0-9;]*m`, must be the same valid JSON value as plain output.

## Spec 8

On startup the program loads user configuration from `$HOME/.xq`. It does not load `$XDG_CONFIG_HOME/xq/config`: with only that file containing `tab=True`, `<r><x>v</x></r>` still produces `<r>\n  <x>v</x>\n</r>\n`. Absence of `$HOME/.xq` and a `$HOME/.xq` path that is a directory are silently treated as no configuration.

The file is line-oriented. Trim whitespace around each line, key, and value. Ignore blank lines, lines whose first non-whitespace character is `#`, lines without exactly one `=`, lines with multiple `=` characters, and unknown or incorrectly capitalized keys. Key names are case-sensitive. Recognized keys are `indent`, `tab`, `color`, and `no-color`.

Integer parsing of config `indent` is permissive: a nonnumeric value becomes `0`; the resulting value is then subject to the 0–8 validation rule. The true boolean spellings are exactly `1`, `t`, `T`, `true`, `TRUE`, and `True`; the false spellings are exactly `0`, `f`, `F`, `false`, `FALSE`, and `False`. An unrecognized boolean becomes false. Long comment lines of at least 100,000 characters must be tolerated.

All settings in the file are applied. `tab=true` overrides numeric indentation, including an explicit command-line `--indent`; the command line does not clear the configured tab setting. Thus a file containing `tab=true` together with `--indent 3 --no-color` formats `<r><x/></r>` as the plain-text bytes `<r>\n\t<x/>\n</r>\n`. An explicit command-line color choice overrides the opposing configured color choice: `--no-color` disables configured `color=true`, and `--color` enables color despite configured `no-color=true`. If both `color=true` and `no-color=true` are set in the configuration itself, color is enabled. Other explicit command-line values, including numeric indent when configured tab mode is false, override their matching configured values.

## Spec 9

In XML formatting mode, parse the document rather than merely inserting whitespace in the source. Emit elements in document order with one structural item per line, nesting each child by the chosen indent. Elements containing only a single ordinary text node remain on one line. Elements with children put their opening and closing tags at their own depth and each child at the next depth. Remove source-only whitespace between elements and normalize closing layout, but preserve meaningful text.

For example:

```text
input: <?xml version="1.0"?><user status="active"><first_name>John</first_name><address><city>Bellville</city></address></user>

output:
<?xml version="1.0"?>
<user status="active">
  <first_name>John</first_name>
  <address>
    <city>Bellville</city>
  </address>
</user>
```

Attributes remain on the opening-tag line, separated by one space and kept in input order. Attribute values are quoted and safely escaped: `"`, `&`, and a literal newline become `&quot;`, `&amp;`, and `&#xA;` as needed. Valid element names containing namespace prefixes, digits, hyphens, and dots are supported. Namespace declarations and namespace meaning must be retained. When a child element uses a redundant prefix for a namespace URI already bound to another prefix in scope, the element name is canonicalized to the existing in-scope prefix while the child's redundant declaration remains. For example, a `soap:Envelope` binding the SOAP URI and containing `<wstxns8:Body xmlns:wstxns8="http://schemas.xmlsoap.org/soap/envelope/"/>` emits `<soap:Body xmlns:wstxns8="http://schemas.xmlsoap.org/soap/envelope/"/>`.

Empty XML elements, whether written `<x/>` or `<x></x>`, become `<x/>`. Multiple empty siblings remain separate structural items. An element whose content is only ignorable formatting whitespace also becomes empty. A document comprised of `<root></root>` therefore produces `<root/>\n`.

## Spec 10

XML declarations, processing instructions, doctypes, and comments are preserved in document order. Items before the root appear at depth zero on separate lines. Preserve the declaration's version, encoding, and original quote form. Normalize an HTML doctype's keyword to lowercase when formatting, e.g. `<!DOCTYPE html>` becomes `<!doctype html>`, while retaining its name/content. Multiple well-formed processing instructions that contain target data are not merged or dropped.

Comments use `<!-- ... -->`, are indented at their structural depth, and retain their text and internal newlines. Each continuation line of a multiline comment is indented consistently relative to that comment. Root-level comments before and after the document element remain outside it. A trailing root-level comment is placed directly after the root closing tag and then followed by two newlines. For example, `<!-- Top --><?xml version="1.0"?><root><child>text</child></root><!-- Bottom -->` becomes `<!-- Top -->\n<?xml version="1.0"?>\n<root>\n  <child>text</child>\n</root><!-- Bottom -->\n\n`. For an ordinary inner comment:

```text
input:  <root><!-- This is a comment --><child>text</child></root>
output:
<root>
  <!-- This is a comment -->
  <child>text</child>
</root>
```

CDATA is semantically decoded once the input has been detected as XML. Text that contains literal XML-sensitive characters after entity decoding is emitted safely as CDATA, so `<child>Text with &lt;special&gt; &amp; characters</child>` becomes `<child><![CDATA[Text with <special> & characters]]></child>`. In recognized XML, such as a document beginning with an XML declaration, existing CDATA with sensitive content is preserved in that safe form and CDATA containing only safe plain text is emitted as ordinary text. The declaration-less CDATA detection exception is specified in Spec 5. Comments do not contribute text to XML-to-JSON values.

## Spec 11

Meaningful XML text and Unicode are preserved without mojibake, including CJK, Arabic, Cyrillic, accented text, and emoji. Entity references in text are decoded to their characters before safe reserialization or extraction. Adjacent text nodes behave as a single logical text value. Very long text and attribute values are not wrapped or truncated.

Whitespace that exists only to format the source tree is discarded. Leading/trailing whitespace surrounding element-only children is normalized. Meaningful internal whitespace is retained: for `<child>   text with spaces   </child>`, the leading three spaces before `text` remain, while trailing padding may be removed. Text-only elements whose source intentionally puts text on its own lines may keep the text on a separate indented line. In mixed content, do not lose text before, between, or after child elements. A representative result is:

```text
<root>
  <child>Text
    <nested>with mixed</nested> content</child>
</root>
```

for `<root><child>Text <nested>with mixed</nested> content</child></root>`. Formatting must preserve the semantic character data even where mixed-content line breaks are introduced.

## Spec 12

`-m`/`--html` uses a tolerant, streaming HTML parser/formatter. It accepts full HTML documents and fragments, recognizes tag names case-insensitively, writes normalized lowercase HTML tag names, and tolerates missing and mismatched closing tags without an XML syntax error. It does not synthesize omitted closing tags to make malformed input balanced: it emits the formatted prefix represented by the tokens actually encountered. For example, `--html` with `<DIV><p>Hello` exits `0` and outputs exactly `<div>\n  <p>Hello\n`; `-m` with `<html><body><p>test` outputs exactly `<html>\n  <body>\n    <p>test\n`. An explicit mismatched end tag is retained in the streaming position: `<html><body><div>Test<p>Paragraph</div></body></html>` becomes exactly:

```text
<html>
  <body>
    <div>Test
      <p>Paragraph</div>
    </body>
  </html>
```

The final newline shown above is present. Likewise, `<html><body><p>Unclosed paragraph<div>Div inside p</div>` ends after the formatted `</div>\n` and does not gain `</p>`, `</body>`, or `</html>`. The formatter does not invent an `<html>`/`<body>` wrapper around a standalone fragment such as `<div>Just a div</div>`. If the input already has an `<html>` root but directly contains a custom element and no body, the element remains directly under `<html>`; for example, `<html><tag></tag></html>` is not wrapped in a synthesized `<body>`.

Use the same structural indentation model as XML. Preserve comments, attributes and their order, element text, HTML5 semantic elements, nested lists, tables, forms, links, media elements, and arbitrary custom elements. In double-quoted HTML attribute values, entity spellings needed by the serializer remain encoded; in particular, `onclick="alert(&apos;hello&apos;)"` is emitted with both `&apos;` spellings intact, and an encoded double quote is emitted as `&quot;`. Preserve script and style contents as raw text rather than parsing their `<`, `>`, braces, quotes, or ampersands as markup. Textual whitespace inside `<pre>` is retained, but apparent markup inside it is still parsed and structurally formatted as described in Spec 13. Decode named and numeric HTML entities to their Unicode characters in text. The serializer writes the decoded text literally even for `<`, `>`, and `&`: `<p>Text with &lt;escaped&gt; &amp; special &copy; characters &#169; numeric &#xA9;</p>` is emitted as `<p>Text with <escaped> & special © characters © numeric ©</p>`.

A basic document is formatted as:

```text
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8"/>
    <title>Test Page</title>
  </head>
  <body>
    <h1 id="main">Title</h1>
    <p class="text">Content</p>
  </body>
</html>
```

## Spec 13

HTML void elements are serialized with XML-style `/>`, including `area`, `base`, `br`, `hr`, `img`, `input`, `link`, `meta`, and `source`. An input `<meta charset="UTF-8">` thus becomes `<meta charset="UTF-8"/>`. A valueless/boolean attribute is retained with an empty value, for example `<video controls>` becomes `<video controls="">`. Ordinary empty HTML elements are not collapsed: `<p></p>`, `<div></div>`, `<span></span>`, `<title></title>`, and empty scripts retain separate closing tags.

Closing-tag layout after a final void child depends on the preceding children. If all of the parent's element children are void elements, the parent closing tag directly follows the final void element; for example, `<video><source src='a.mp4'></video>` becomes `<video>\n  <source src="a.mp4"/></video>\n`, and a `head` containing only `base`, `link`, and `meta` ends with `<meta .../></head>`. If an ordinary non-void child precedes the final void child, the parent closing tag is placed on its own structural line. Thus a `head` containing a `title` followed by `<link rel="stylesheet" href="style.css">` ends with:

```text
    <link rel="stylesheet" href="style.css"/>
  </head>
```

The same separate-line layout applies to a form whose label is followed by a final `<input type="submit" value="Submit"/>`, and to a container whose earlier ordinary content is followed by a final `area` element.

Inline and mixed HTML content must retain all text while following structural indentation. For example, `<p>Text before<strong>bold text</strong> and after</p>` formats equivalently to:

```text
<p>Text before
  <strong>bold text</strong> and after
</p>
```

Consecutive sibling inline elements under a block container may each occupy their own indented line. A `<pre>` block preserves whitespace in its text nodes, but markup-looking content is parsed as markup rather than kept as a literal byte payload. The exact input `<pre>line 1\n    line 2\n<not-a-tag></pre>` produces `<pre>line 1\n    line 2\n\n  <not-a-tag></pre>\n`. HTML comments, including multiline comments containing apparent tags, remain comments and are indented rather than interpreted.

## Spec 14

Native JSON input is parsed and re-emitted without changing JSON types: objects remain objects, arrays remain arrays, strings remain strings, numbers remain numeric (including negative, floating-point, and exponent forms semantically), and booleans/null remain `true`, `false`, and `null`. Escapes and Unicode must round-trip to an equivalent JSON value. Object member order should follow input order for native JSON formatting.

Default output is conventional pretty JSON with one member or array item per line, a space after each colon, the configured indent unit at each depth, and a trailing newline. For example:

```text
input: {"name":"John","address":{"city":"New York"},"items":[1,2]}
output:
{
  "name": "John",
  "address": {
    "city": "New York"
  },
  "items": [
    1,
    2
  ]
}
```

`--indent 4` and `--tab` change JSON pretty indentation in the same fashion as markup. Native JSON is formatted whether or not `--json` is present.

## Spec 15

`-j`/`--json` converts XML or HTML into a JSON object whose single outer property is the document element name. Conversion follows these rules recursively:

- An element containing only nonempty text becomes a JSON string.
- An element with neither meaningful text, attributes, nor child elements becomes `{}` rather than `null` or `""`.
- Attributes become object properties with `@` prefixed to the local attribute name.
- If an element has attributes or element children as well as its own direct text, that text is stored under `#text`.
- XML child elements become properties named by local element name. HTML child properties use the source-case rule below. Two or more same-named siblings at one level become an array in document order; a single child does not become an array.
- Repetition is handled independently at every nesting level, allowing arrays of objects that themselves contain arrays.
- Namespace prefixes are removed from element property names. Namespace declarations are not represented as ordinary `xmlns` properties; a declared prefix/URI can appear as an `@prefix` property, while identically named local elements from different namespaces are grouped under the same local-name key.
- XML declarations, processing instructions, comments, and doctypes do not become JSON properties.
- Character/entity and CDATA content is decoded. Mixed direct-text segments are trimmed and joined with newline characters under `#text`; child elements are represented normally.
- Properties produced from XML/HTML are emitted in deterministic lexicographic key order.

HTML-to-JSON conversion preserves the source spelling and case of element names for property keys; it does not apply the lowercase tag-name normalization used by formatted HTML output. For example, `--html --json` on `<DIV id='x'><P>hello</P><P>world</P></DIV>` produces a `DIV` outer property and a `P` child property, not `div` and `p`.

Thus:

```text
<book id="123"><title lang="en">Sample Book</title><author>John Doe</author></book>
```

becomes:

```json
{
  "book": {
    "@id": "123",
    "author": "John Doe",
    "title": {
      "#text": "Sample Book",
      "@lang": "en"
    }
  }
}
```

Noncompact XML/HTML-to-JSON serialization always uses exactly two spaces per depth. `--indent` and `--tab` do not affect this conversion output. Both `--json --indent 4` and `--json --tab` on `<r><x>1</x></r>` therefore produce exactly:

```json
{
  "r": {
    "x": "1"
  }
}
```

## Spec 16

`-d`/`--depth N` limits only XML/HTML-to-JSON structural conversion. The default `-1`, and any accepted negative depth used for conversion, means unlimited depth. Depth zero retains the outer root property but collapses the root element value to the concatenated descendant text. Depth one retains the root and its direct child properties, with each direct child's deeper structure collapsed to descendant text. In general, depth `N` retains the root plus `N` descendant element levels; an element at the cutoff becomes its complete descendant character data rather than an object.

For `<root><level1><level2><level3><level4>Deep Value</level4></level3></level2></level1></root>`:

```text
--depth 0 => {"root":"Deep Value"}
--depth 1 => {"root":{"level1":"Deep Value"}}
--depth 2 => {"root":{"level1":{"level2":"Deep Value"}}}
--depth 4 => {"root":{"level1":{"level2":{"level3":{"level4":"Deep Value"}}}}}
```

Attributes on element levels above the cutoff are retained. Once an element itself is collapsed at the cutoff, its attributes and deeper element keys are omitted in favor of its descendant text.

## Spec 17

`--compact` makes output from the explicit `--json` conversion/serialization pipeline a single line followed by one newline. This applies to XML/HTML conversion and to native JSON when `--json` is also present. The explicit compact serializer retains one space after every object colon, uses no space after object or array commas, and removes other formatting whitespace. Thus `--json --compact` on native JSON `{ "a": [1, 2], "b": true }` produces exactly `{"a": [1,2],"b": true}\n`. The flag by itself does not switch an auto-detected native JSON document into the explicit JSON-output pipeline: native JSON given only `--compact` is still pretty-printed according to Spec 14. XML-to-JSON uses the same established spacing. For example:

```text
<root><item>value1</item><item>value2</item></root>
```

with `--json --compact` produces exactly:

```text
{"root": {"item": ["value1","value2"]}}
```

`--compact` combines with `--depth`, with depth conversion occurring before compact serialization. Without `--compact`, XML-to-JSON uses two-space pretty indentation by default and a final newline.

## Spec 18

`-x`/`--xpath EXPR` evaluates an XPath 1.0-style expression against XML. It must support absolute and descendant paths, child navigation, `..` parent navigation, wildcard element tests, `text()`, and attribute selection with `@name`. Node-set results are in document order. Element results default to their complete descendant text; attribute and text-node results use their string values. Emit one result per match, each followed by a newline. An empty element match emits one empty line; a valid query with no matches emits no bytes and exits `0`.

Predicates must support one-based numeric positions, `last()`, attribute equality, child-value equality/comparison, numeric comparisons, and multiple chained/nested conditions. Position is evaluated within each local context, so `//team/member[1]` selects the first member of every team rather than only one member globally. Both single and double quoted string literals work. Examples of required query shapes include:

```text
//book/title
//book[@id="2"]/author
//book[price>25]/title
//book[1]/title
//book[last()]/title
//child/..
//department[@name="Engineering"]//member[@role="developer"]/name
```

## Spec 19

XPath scalar/function support includes `count`, `sum`, `string`, `concat`, `substring`, `contains`, `starts-with`, `normalize-space`, `position`, `last`, and `local-name` in the ordinary XPath 1.0 roles exercised by paths and predicates. `substring` uses XPath's one-based conventions; `normalize-space` trims and collapses whitespace. `local-name()` permits selecting elements in documents with namespaces, for example `//*[local-name()="setting"]/@name` and chained namespaced-element queries.

String and numeric scalar output is one textual line. String functions return the expected string; node-set-to-string conversion uses the first node as XPath specifies. Numeric scalar output uses zero decimal places, so `count` of three nodes prints `3`, and a sum of `74.97` prints `75`. A top-level boolean scalar result is not serializable, even though boolean-returning functions can be used within XPath predicates. In particular, both `contains('alphabet', 'pha')` and `starts-with('alphabet', 'alpha')` evaluate to true but exit `1`, write exactly `Error: unknown type error: true\n` to standard output, and write nothing to standard error. Entity references are decoded in extracted text and UTF-8 is preserved.

Syntactically invalid XPath exits `1` and prints exactly this line to standard output, not standard error:

```text
Error: unable to parse the XPath query
```

## Spec 20

`-e`/`--extract EXPR` is the single-result XPath mode. It has the same XPath parsing and value rules as `--xpath`, but stops after and emits only the first selected result. For example, against `<root><item>first</item><item>second</item></root>`, `-e //item` outputs only `first\n`.

If both `--xpath` and `--extract` are supplied, `--xpath` takes precedence. If both XPath and CSS query flags are supplied, XPath takes precedence. These combinations succeed rather than being rejected. Applying `--json` together with an XPath query still performs the XPath extraction behavior; it must not hide the selected textual value behind an unrelated conversion.

## Spec 21

`-q`/`--query SELECTOR` evaluates CSS selectors against the parsed markup tree and emits all matches in document order. It works with tolerant HTML and with simple XML-like markup, from files or standard input, whether or not `--html` is also supplied. Required selector features are:

- type selectors (`p`, `a`, `div`), universal selector `*`, `.class`, `#id`, and compound forms such as `a.nav-link.active`;
- descendant (`A B`), direct-child (`A > B`), and adjacent-sibling (`A + B`) combinators;
- attribute presence `[data-id]` and exact attribute value `[data-id="102"]`;
- `:not(...)`, including `button:not([disabled])`;
- `:first-of-type`;
- combinations of the above, such as `div.product:first-of-type .product-title` and `div.product > *`.

A valid selector with no matches emits no bytes and exits `0`. Each match normally contributes its complete descendant text followed by a newline. Leading and trailing whitespace around each matched element's complete descendant-text value is removed before that newline is added. Whitespace between descendant text segments is not globally collapsed and retains its source indentation. For example, querying `#main-nav` on `<nav id="main-nav">\n        <a>Home</a>\n        <a>Products</a>\n        <a>Contact</a>\n    </nav>` produces exactly `Home\n        Products\n        Contact\n`: the whitespace outside `Home` and `Contact` is trimmed, while the eight spaces between link texts remain. The same per-match boundary trimming applies to type, ID, class, and attribute-selector matches; selecting leaf elements gives clean leaf text.

## Spec 22

`-a`/`--attr NAME` changes CSS-query output from element text to the named attribute value. It applies to every CSS match and writes one line per match in document order. A missing attribute contributes an empty line, not an error; therefore three matches lacking the attribute yield exactly three newline bytes. Attribute extraction works regardless of whether `-a` appears before or after `-q`.

`--attr` is valid only when a CSS `--query` is present. Using it alone or with XPath but without CSS exits `1` and writes this line to standard error:

```text
Error: query option (-q) is missed for attribute selection
```

## Spec 23

`-n`/`--node` changes element query output from descendant text to serialized node markup including the selected element's own opening/closing tags, attributes, and descendants. It applies to XPath, single extraction, and CSS queries. Multiple selected nodes are serialized one after another in document order, each as a separately formatted node ending in a newline. `--indent` and `--tab` control indentation inside every returned node; the selected node itself begins at depth zero.

For example, selecting the first book in node mode can produce:

```text
<book id="1" genre="fiction">
  <title lang="en">The Great Adventure</title>
  <author nationality="US">Jane Smith</author>
</book>
```

Node serialization uses the relevant XML/HTML escaping and formatting rules and preserves nested tags, comments, attributes, Unicode, and textual quotes. Detached node serialization does not copy unused namespace declarations inherited only from ancestors onto an unprefixed selected element. For example, selecting `//title` in node mode from a document whose `rss` ancestor declares `xmlns:webfeeds="http://webfeeds.org/rss/1.0"` and `xmlns:media="http://search.yahoo.com/mrss/"` outputs `<title>Some Title</title>\n`, without either declaration on `title`.

## Spec 24

With one or more positional paths, first open every path in exact command-line order. Only after every open succeeds are the files processed in that order. A mixture of XML and JSON files is permitted; detect and format each separately. Concatenate their completed outputs directly, relying on each document's final newline—do not insert headers, separators, or blank lines.

A nonexistent path exits `1`, writes no normal result for that path, and reports on standard error:

```text
Error: open PATH: no such file or directory
```

where `PATH` is reproduced exactly. The first open failure aborts the command before any document is formatted, and later paths are not processed. Consequently, if a valid `good.xml` containing `<r/>` is followed by nonexistent `extra`, the command exits `1`, standard output is empty, and standard error is exactly `Error: open extra: no such file or directory\n`; the valid first file's result is not emitted. If a nonexistent first path is followed by a valid file, that later file likewise produces no output. A second positional token such as `extra` is genuinely opened as another file; it is not rejected as an argument-count error. A path naming a directory is treated as undetectable input and exits `1` with `Error: unknown content type: 3\n` on standard output. Other unreadable/non-regular inputs and invalid binary data must fail promptly with status `1` and an `Error:` diagnostic rather than hang or crash.

## Spec 25

`-i`/`--in-place` requires exactly one positional file path. It parses and formats that file using all applicable indentation settings, replaces the contents of the same file with the formatted bytes, exits `0`, and writes nothing to standard output or standard error. It works through both aliases and with custom indentation/tab settings.

With zero paths—even if XML bytes exist on standard input—or with two or more successfully opened paths, it exits `1`, emits no formatted result, and writes exactly this line to standard error:

```text
Error: in-place formatting requires a file path (and only one file path)
```

Positional files are opened before this arity validation. Therefore `--in-place a b` when `a` does not exist exits `1` with empty standard output and exactly `Error: open a: no such file or directory\n` on standard error, rather than the arity diagnostic. When both files exist, the arity diagnostic above is used and neither file is modified. When the one path is a symbolic link, follow it and modify its target while leaving the directory entry as a symbolic link. Failure to open the designated path uses the normal file-open error behavior.

## Spec 26

An explicitly piped input containing zero bytes is not a request for help. It exits `1` and writes an error beginning `Error: unknown content type:` to standard output. An empty file behaves the same; the established diagnostic for an empty file is exactly `Error: unknown content type: 3\n`. Whitespace-only input is handled without a crash and may produce no non-whitespace output; the normal successful form is status `0` with empty/whitespace-only standard output.

Invalid UTF-8/binary markup exits `1` and prints an XML syntax diagnostic on standard output, including `Error: XML syntax error`, its line, and `invalid UTF-8`. Malformed XML in formatting mode likewise exits `1`; because formatting is streaming, already parsed opening markup may precede the error on standard output. For `<root><unclosed>`, the canonical output is:

```text
<root>
  <unclosedError: XML syntax error on line 1: unexpected EOF
```

The incomplete `unclosed` start tag has no emitted `>`; the error text immediately follows its name. Tolerant HTML mode is exempt: unclosed HTML produces the successful streaming-prefix behavior in Spec 12.

## Spec 27

Malformed detected JSON exits nonzero and reports an `Error:` on standard output. For an invalid token in `{"key": invalid}`, the message includes `invalid character 'i' looking for beginning of value`; a streaming formatter may have already emitted the partial prefix. When `--json` is converting malformed XML, the standard-output diagnostic contains `Error: error while parsing XML: XML syntax error` and the underlying detail such as `unexpected EOF`. When `--json` receives malformed JSON, its standard-output diagnostic contains `Error: error while parsing JSON` and the parser detail.

There is one compatibility quirk for processing instructions: the XML input `<?target?><root/>`, whose processing instruction has a target but no following data, must terminate nonzero and standard error must contain `panic: runtime error: index out of range`. This quirk does not apply to declarations or processing instructions with data, such as `<?xml version="1.0"?>` or `<?xml-stylesheet href="a.xsl" type="text/xsl"?>`.

An input that ends after a syntactically valid JSON member but omits the final object brace retains the formatter's streaming behavior: `{"key": "value"` exits `0` and outputs the partial pretty form

```text
{
  "key": "value"
```

with a final newline. This special incomplete-object behavior does not make arbitrary invalid JSON tokens successful.

## Spec 28

Formatting and extraction must preserve content rather than merely satisfy syntactic examples. In particular, it must retain all siblings, attributes, nested structures, declarations, comments, CDATA meaning, entity meaning, scripts/styles, numeric/boolean/null JSON values, and multilingual text. No-match queries are successful and silent. Except for the explicit empty-data processing-instruction compatibility quirk in Spec 27, parse and validation errors are controlled failures with status `1`, not uncaught exceptions or signals. Output is deterministic across file and standard-input modes for the same bytes and options, aside from the intentional difference between XML and forced tolerant-HTML parsing.
