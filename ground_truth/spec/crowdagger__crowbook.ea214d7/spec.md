# Crowbook-compatible executable specification

The required artifact is one executable file named `executable`. It is a UTF-8 command-line book renderer compatible with Crowbook 0.17.0. Unless a parser error or the explicit `html.dir` panic in Spec 8 is specified, operational failures are reported to standard error and the process still exits with status 0. Binary formats must be written as bytes, never decoded as text. All behavior below is part of the contract.

## Spec 1

The command has a flat interface, not a subcommand interface. Its synopsis is `executable [OPTIONS] [BOOK]`; tokens such as `add`, `remove`, `init`, `build`, `list`, `show`, and `help` are ordinary BOOK filenames. Options may precede or follow BOOK except that the variadic `--set` greedily consumes every following non-option token, including a would-be BOOK; put BOOK before `--set` when both are used. Exactly zero or one BOOK is accepted; two or more positionals are command-line parse errors. A lone `--` ends option parsing, so a later flag-looking token is treated as BOOK. Help/version short-circuit only after the parser reaches them: `--help --bad-option` and `--version --bad-option` succeed, but `--bad-option --help` and `--bad-option --version` exit 2 on the preceding unknown option.

Recognized switches and aliases are: `-h/--help`, `-V/--version`, `-v/--verbose`, `-q/--quiet`, `-o/--output VALUE`, `-t/--to FORMAT`, `-c/--create FILE...`, `-l/--list-options`, `--set KEY VALUE [KEY VALUE ...]`, `--print-template NAME`, `-L/--lang LANG`, `-S/--stats`, `-s/--single`, `-n/--no-fancy`, `-a/--autograph`, and `-f/--force-emoji`. Boolean short switches may be clustered, such as `-vn` and `-fsn`. Value options accept separated values; long options also accept `--name=value`. The short output alias also accepts `-o=VALUE`; for example, `-o=out.html` is parsed as an output request and, without `--to`, reaches the required-argument error rather than help. `--output` requires `--to`, but `--to` does not require `--output`. The parser's accepted `--to` values are exactly `epub`, `pdf`, `html`, `tex`, `odt`, and `html.dir`; nevertheless, selecting `odt` at runtime exits 0, writes no rendered bytes, and reports `ERROR unknown format odt` after the banner.

## Spec 2

Command-line parsing failures go to standard error and exit 2. Unknown options use wording containing `unexpected argument '<option>' found`, `Usage: executable`, and `For more information, try '--help'.`; for a long unknown option also show `tip: to pass '<option>' as a value, use '-- <option>'`. Missing values say `a value is required for '--NAME <name>'`. In particular, invoking `--to` with no value writes `error: a value is required for '--to <to>' but none was supplied`, immediately followed by `  [possible values: epub, pdf, html, tex, odt, html.dir]`, a blank line, and `For more information, try '--help'.`. Invalid formats likewise say `invalid value 'VALUE' for '--to <to>'` and `[possible values: epub, pdf, html, tex, odt, html.dir]`. `--output` without `--to`, including the `-o=VALUE` spelling, says `the following required arguments were not provided:` followed by `  --to <to>`. `--set` requires at least two values, but the parser does not require an even count: `--set title ok author` is accepted, leaves no BOOK, exits 0, and reaches the ordinary no-book diagnostic. One value still produces `2 values required by '--set <set> <set>...'; only 1 was provided`. More than one occurrence of `--set` is rejected with `cannot be used multiple times`. `--verbose` and `--quiet` conflict, with the error identifying both arguments. The usage line in an error should reflect supplied required flags in clap style.

## Spec 3

`--version` and `-V` write exactly `crowbook 0.17.0\n` to stdout, nothing to stderr, and exit 0. Help exits 0 and is written only to stdout. Its exact text is:

```text
crowbook 0.17.0 by Élisabeth Henry <liz.henry@ouvaton.org>
Render a Markdown book in EPUB, PDF or HTML.

USAGE:
    executable [OPTIONS] [BOOK]

OPTIONS:
  -f, --force-emoji
          Force emoji usage even if it might not work on your system
  -s, --single
          Use a single Markdown file instead of a book configuration file
  -n, --no-fancy
          Disably fancy UI
  -v, --verbose
          Print warnings in parsing/rendering
  -a, --autograph
          Prompts for an autograph for this book
  -q, --quiet
          Don't print info/error messages
  -c, --create <files>...
          Create a new book with existing Markdown files
  -o, --output <output>
          Specify output file
  -t, --to <to>
          Generate specific format
      --set <set> <set>...
          Set a list of book options
  -l, --list-options
          List all possible options
  -L, --lang <lang>
          Set the runtime language used by Crowbook
      --print-template <print-template>
          Prints the default content of a template
  -S, --stats
          Print some project statistics
  -h, --help
          Print help
  -V, --version
          Print version

ARGS:
  [BOOK]  File containing the book configuration file, or a Markdown file when called with --single
```

The final newline is required.

## Spec 4

In normal, non-quiet operation write `CROWBOOK 0.17.0\n` to stderr before operational information/errors; stdout remains reserved for requested rendered/template/stats/config data. `--quiet` suppresses the banner and informational output but not actual errors. `--no-fancy` uses plain records such as `[INFO] Succesfully generated HTML (standalone page): output.html`. `--verbose` enables records whose debug prefix includes the legacy counter and module, specifically `[DEBUG] (1) crowbook::book:` (a timestamp may precede the bracketed level); when HTML is selected, one such record contains `Attempting to generate html...`. In verbose stats mode it also emits `[WARN] This version of crowboook has been compiled without support for advanced statistics`. `--force-emoji` and `--no-fancy` alter presentation only and must not break rendering. `--autograph` reads one line from stdin and writes the prompt `Enter autograph:\n` to stdout before the rendered document. Standalone HTML then includes `<div id = "autograph">` containing the entered line; for input `With love, The Author\n`, that text occurs in the div.

## Spec 5

With no BOOK and no self-contained mode, exit 0 and write to stderr exactly:

```text
CROWBOOK 0.17.0
ERROR You must pass the name of a book configuration file.
For more information try --help.

```

There are two newline bytes after the final period: the diagnostic ends in a blank line.

For a missing ordinary BOOK named `X`, exit 0 and write `CROWBOOK 0.17.0\nERROR Could not find file 'X' for book\n`. After `--`, a flag-like filename follows this same rule. An empty/malformed named book file reports `FILE: Error parsing configuration file:` and suggests `Maybe you meant to run crowbook with the --single argument?`; this diagnostic also ends with two newline bytes (a blank line). A malformed configuration read through BOOK `-` uses the same text but omits the `FILE:` prefix. A chapter-declaration line beginning `- ` whose path contains whitespace is rejected as `BOOK:LINE: Error parsing configuration file: error.chapter_whitespace`, rather than being treated as a missing path. YAML syntax errors include the source filename and one-based line, `YAML block was not valid YAML`, and useful parser detail. A missing chapter reports `BOOK:LINE: Could not find file 'PATH' for book chapter`. Continue to return 0 for these application errors.

## Spec 6

Runtime UI language is selected first by `-L/--lang`, otherwise from the leading language portion of environment `LANG`. English is the fallback and `-L fr` overrides an English environment. A French missing-image error uses `Impossible de trouver le fichier 'PATH' pour image`; it does not contain `Erreur durant`. Runtime language selection is independent of a book's `lang` metadata. `--help` and `--version` take precedence over later modes/options, subject to the left-to-right unknown-option behavior in Spec 1.

## Spec 7

Without `--single`, BOOK is a UTF-8 book configuration. It consists of YAML-like `key: value` option lines, blank lines and `#` comment lines, followed/interspersed with chapter declarations. A valid nonempty book must contain at least one option line before its first chapter declaration; a file containing only declarations such as `+ chapter1.md` is rejected with the malformed-book diagnostic from Spec 5 before rendering or destination handling. Support quoted/unquoted scalars, real YAML booleans and integers, inline arrays such as `[html, epub]`, and YAML literal/folded multiline strings (`|` and `>`). A colon inside a quoted value is content. Repeated scalar keys use the last value. Config paths, chapter paths, and output paths resolve relative to the directory containing the book file, not the caller's current directory. When BOOK is `-`, read the configuration from stdin and resolve relative chapter paths against the process working directory. The same option-line validity rule applies: stdin containing only `+ stdin-chapter.md` exits 0 with no rendered stdout and reports `ERROR Error parsing configuration file: "could not parse %{file} as a book file."` followed by the single-mode suggestion and a blank line, whereas prepending `title: T` renders that chapter successfully.

Recognize chapter declaration forms: `+ path.md` numbered chapter; `- path.md` unnumbered chapter; `! path.md` hidden chapter; `-- path.md` subchapter; `N. path.md` numbered chapter explicitly numbered N; `@+ path.md` numbered part; and `@- path.md` unnumbered part. Preserve declaration order. A chapter's first level-one heading is its title. In standalone HTML, hidden content is rendered and its title is suppressed from the rendered chapter heading, but the TOCs still include that source title. Unnumbered items use unnumbered headings while remaining navigable. Parts render as parts and may reset chapter numbering. Explicit numbering affects headers and LaTeX counters. Missing headings and empty content are handled without crashing.

## Spec 8

Without `--to`, render every configured `output.FORMAT: PATH` (`output.html`, `output.html.dir`, `output.epub`, `output.tex`, `output.pdf`) and every format named in `output: [FORMATS]`. Multiple configured formats are all produced. For the list form derive filenames from the `.book` basename with the conventional extension/directory. `output.base_path` is prepended to relative output paths. With `--to`, render only that format; `--output` overrides any configured destination for single-file formats. If destination is omitted or is `-`, send the selected single-file format to stdout (including raw ZIP bytes for EPUB) and do not create a file named `-`. Existing ordinary output files are overwritten. Do not implicitly create a missing parent directory for a single-file destination; report `could not create file 'PATH': 'No such file or directory (os error 2)`. `html.dir` is an exception: `-t html.dir -o site` still requires an `output.html.dir` option in the book. Without that key the process creates/replaces the destination directory, then panics with status 101; stderr starts with the banner and contains `panicked at src/lib/html_dir.rs:<error location>` and `InvalidOption("option 'output.html.dir' is not present")`, and no required site files are written.

## Spec 9

With `--single`, BOOK is one Markdown document rather than a `.book` configuration. BOOK may be `-` for stdin. An initial YAML metadata block opened and closed by `---` is parsed for the same options; without such a block defaults are used. A YAML document-end marker `...` does not close this front matter: given `---`, metadata-looking lines, `...`, and Markdown, the attempted preamble remains document content and its options are not applied. `input.yaml_blocks` permits inline YAML option blocks where applicable, while multiple YAML-looking blocks after the initial block remain document content. The whole single Markdown file is one logical chapter for wrapper purposes: several level-one headings stay inside the sole `chapter-0` wrapper and do not create `chapter-1`. In single-file TeX those headings render as sections because that mode defaults to the `article` class. `--set` options override file metadata/configuration. Empty, huge, Unicode-heavy, and malformed-but-recoverable Markdown inputs must still render promptly and successfully.

## Spec 10

`--create FILE...` emits a book configuration to stdout, preserving file order and listing every supplied argument as `+ FILE`, even if it does not exist or has a `.book` extension. Without `--set`, `--create chapter.md` writes exactly 447 bytes and includes the quoted lines `"author: Your name"`, `"title: Your title"`, and `"lang: en"`, output guidance, and `## List of chapters`. Supplying `--set` changes this form to the explicitly set metadata rather than retaining the default metadata and guidance. In particular, `--set author 'Exact Author' title 'Exact Title' --create a.md missing.md odd.book` writes exactly these 92 bytes:

```text
author: Exact Author
title: Exact Title

## List of chapters
+ a.md
+ missing.md
+ odd.book
```

It does not include `lang: en` or output guidance. If the optional BOOK positional is also supplied, it is the destination: write the configuration there rather than stdout and print `Created BOOK` as confirmation; refuse to overwrite an existing file and report that it exists. Create mode exits 0.

## Spec 11

`--set` consumes one invocation containing a greedy list of values. It applies complete alternating option-name/value pairs before rendering/creation, parses values that reach it according to the option's declared type (including numeric and boolean strings supplied by the CLI), and allows spaces and special characters in values. A hyphen-leading token is still interpreted by the command-line parser rather than as a `--set` value; the negative-integer case and its exact failure are specified in Spec 14. It does not reject a dangling odd value during command-line parsing, and a following BOOK token is consumed as another set value; place BOOK before `--set`. Unknown keys produce `ERROR Error in setting key KEY: ... Error converting BookOption: unrecognized key 'KEY'` and exit 0. The source location attached to a CLI override is the line that terminated the preceding contiguous configuration-option block. Thus, when option lines 1-3 are followed by a blank line 4 and then the chapter list, `test.book --set invalid_option value` reports `test.book:4:`, not line 3. Important supported override keys include metadata, output paths, `rendering.highlight`, `rendering.inline_toc`, `rendering.num_depth`, `rendering.initials`, and `epub.version`.

## Spec 12

Configuration metadata consists of string-valued `author`, `title`, `lang`, `subject`, `description`, `subtitle`, `license`, `version`, `date`, and `autograph`, optional path-valued `cover`, plus arbitrary string-valued `metadata.*` keys. Empty title/author are valid. Preserve Unicode. Standalone HTML writes configured title and author metadata literally in the head and JSON-LD rather than HTML-escaping `<`, `>`, or `&`: title `A <Book> & More` produces `<title>A <Book> & More</title>`, and author `A <Writer> & B` produces `<meta name="author" content="A <Writer> & B">`. The visible author heading is escaped (`A &lt;Writer&gt; &amp; B`). Other formats use their required HTML/XML escaping. HTML places language on `<html lang="...">` and exposes extended metadata visibly or in structured data. A missing configured cover does not prevent standalone HTML generation: the HTML file is still emitted successfully, and this case by itself produces no missing-cover diagnostic. Unknown book-language codes retain safe output and use English behavior where a renderer requires a known language.

## Spec 13

Recognize and type-check the option catalog described throughout this document. In addition to metadata/output keys, it includes:

- rendering: `rendering.highlight` (`syntect`, `highlight.js`, or `none`), `rendering.highlight.theme`, `rendering.initials`, `rendering.inline_toc`, `rendering.inline_toc.name`, `rendering.num_depth`, `rendering.chapter`, `rendering.part`, `rendering.chapter.roman_numerals`, `rendering.part.roman_numerals`, `rendering.part.reset_counter`, `rendering.chapter.template`, `rendering.part.template`;
- HTML: `html.icon`, `html.header`, `html.footer`, `html.css`, `html.css.add`, `html.css.colors`, `html.js`, `html.css.print`, `html.highlight.js`, `html.highlight.css`, `html.side_notes`, `html.escape_nb_spaces`, `html.chapter.template`, `html.part.template`, `html.standalone.template`, `html.standalone.one_chapter`, `html.standalone.js`, `html.dir.template`;
- EPUB: `epub.version` (2 or 3), `epub.highlight.theme`, `epub.css`, `epub.css.add`, `epub.chapter.xhtml`, `epub.titlepage.xhtml`, `epub.toc.extras`, `epub.escape_nb_spaces`;
- TeX: `tex.cover`, `tex.highlight.theme`, `tex.links_as_footnotes`, `tex.pageref_template`, `tex.command`, `tex.escape_nb_spaces`, `tex.template`, `tex.template.add`, `tex.class`, `tex.paper.size`, all four `tex.margin.*`, `tex.title`, `tex.font.size`, `tex.hyperref`, `tex.stdpage`;
- resources/input/internal: `resources.files`, `resources.out_path`, `resources.base_path`, its `.links/.images/.files/.templates` variants, `input.clean`, `input.clean.smart_quotes`, `input.clean.ligature.dashes`, `input.clean.ligature.guillemets`, `input.yaml_blocks`, `proofread.repetitions` (boolean), `proofread.repetitions.fuzzy.threshold` (float), `crowbook.html_as_text`, `crowbook.files_mean_chapters`, `crowbook.markdown.superscript`, `crowbook.temp_dir`, and `crowbook.zip.command`.

The two `proofread.*` keys are accepted configuration options but are absent from the `--list-options` catalog, as specified in Spec 38.

## Spec 14

Reject unrecognized option names with a source-qualified `Error converting BookOption: unrecognized key 'KEY'`. Enforce exact YAML types: string options reject integers/arrays with `Expected a string as value for key KEY, found Integer(123)` or an `Array([...])`; integer options reject strings/booleans with `expected an integer as value for key 'KEY', found ...`; boolean options reject strings with `expected a boolean as value for key 'KEY', found String("yes")`; list-of-string options require an array. A scalar `output: html` reports `Expected a list as value for key output, found String("html")`; a mixed array reports `Expected only strings in the list for key output, found Integer(123)`. `output` additionally validates every format and reports `The output format invalid_format for key output is not recognized`. An invalid highlight enum is aggregated after `WARNING Crowbook exited successfully, but the following errors occurred:` as `ERROR rendering.highlight set to 'not_a_bool', not a valid value`. Float threshold options such as `proofread.repetitions.fuzzy.threshold` require a YAML real. The YAML integer value `123` produces `Error converting BookOption: could not parse 'Integer(123)' as a float for key 'proofread.repetitions.fuzzy.threshold'`; the `Integer(123)` debug representation is required. Errors include `BOOK:LINE:`, with the option-block location rule in Specs 11 and 41. Deprecated `autoclean` aliases through `input.autoclean` to `input.clean` while emitting both `WARNING 'autoclean' has been deprecated, you should now use 'input.autoclean'` and `WARNING 'input.autoclean' has been deprecated, you should now use 'input.clean'`. Removed `nb_char` reports `Error converting BookOption: key 'nb_char' has been deprecated.` Negative YAML integers are accepted. They are not accepted as separated `--set` values: `test.book --set title 'New title' rendering.num_depth -1 output.html out.html` writes nothing to stdout, creates no output, exits 2, and writes exactly:

```text
error: unexpected argument '-1' found

  tip: to pass '-1' as a value, use '-- -1'

Usage: executable [OPTIONS] [BOOK]

For more information, try '--help'.
```

Invalid `epub.version` values fall back to/generate a valid EPUB rather than crashing.

## Spec 15

`import: PATH` recursively imports options from another book configuration. Resolve imports relative to the importing file. Merge options through chains with nearer/main configurations overriding imported values, but do not import chapter declarations from any imported file. Thus, for `main.book` importing `mid.book`, which imports `base.book`, the main title overrides the intermediate and base titles and an author set only in the base reaches the rendered metadata, while a `+ ch.md` declaration present only in the base contributes no chapter or chapter content. Report missing imports as `Could not find file 'PATH' for book`. Resource and output path-valued options preserve absolute paths and otherwise honor the relevant configured base path. In particular, `resources.base_path` overrides specialized bases; otherwise `.links`, `.images`, `.files`, and `.templates` affect only their category.

## Spec 16

The Markdown parser implements the relevant CommonMark-like block syntax: ATX headings levels 1-6; setext headings; paragraphs and any number of blank lines; fenced code blocks (backtick fences, optional language, and longer fences containing shorter backticks); indented code; thematic breaks from `---`, `***`, `___`, and `****`; blockquotes including nesting, multiple paragraphs, formatting, and lists; unordered and ordered lists including mixed/deep nesting, multiple paragraphs/code blocks inside items, and custom ordered-list starting numbers; pipe tables including header/body, empty cells, and alignment markers; description lists using `Term` followed by `:   Definition`; task list items `- [ ]` and `- [x]/[X]`; and footnote definitions `[^id]: ...`. A description-list term may span consecutive source lines, which are joined with spaces in the rendered term. Description lists support several successive term/definition associations and multiple consecutive `:   Definition` entries for one term, producing a definition for each entry. Blank-separated top-level quote runs become separate `<blockquote>` elements, while a nested quote adds its own element; a document containing two such top-level runs and one nested run therefore contains three blockquotes. Preserve code whitespace and recover without hanging from unclosed emphasis or fences.

## Spec 17

The inline parser supports `*`/`_` emphasis, `**`/`__` strong, combined/nested emphasis, `~~deleted~~`, backtick code spans, escaped Markdown punctuation, hard breaks from two trailing spaces or backslash, soft breaks, inline links with optional titles, URLs containing balanced parentheses, case-insensitive reference links, `<URL>` autolinks, `<email>` mailto links, inline/reference images with alt/title, image-as-link, footnote references, and recognition of raw inline HTML and entities. Recognition does not imply that the source entity spelling or raw tags survive HTML serialization; the default behavior is specified in Spec 19. Do not misinterpret ordinary consecutive markers. For the ambiguous combined form `***both***`, emphasis is the outer node and strong is the inner node. Setting `crowbook.markdown.superscript: true` enables caret-delimited superscript and single-tilde-delimited subscript, including spaces inside a superscript: `X^two words^ H~2~O` renders as `X<sup>two words</sup> H<sub>2</sub>O`. Preserve all Unicode code points. Local standalone-image paragraphs must be distinguishable from inline images.

## Spec 18

HTML rendering of Markdown uses semantic elements: headings `<h1>` through `<h6>` with stable `id` values beginning `link-`; emphasis `<em>`; strong specifically `<b>`; deletion `<del>`; inline code `<code>`; blocks `<pre>`; `<ul>/<ol>/<li>`; `<blockquote>`; `<a href>`; `<table>/<tr>/<th>/<td>`; and `<dl>/<dt>/<dd>`. The ambiguous `***both***` form serializes specifically as `<em><b>both</b></em>`. Task markers serialize directly inside the surrounding `<ul>`, followed by their paragraph, rather than as ordinary `<li>` contents. The unchecked input is `<input type = "checkbox" disabled = "" />`; the checked input is `<input type = "checkbox" disabled = "" checked = ""/>`. Table header and body rows are direct children of `<table>`; the renderer emits neither `<thead>` nor `<tbody>`. In default/syntect standalone HTML, even a language-tagged fence such as `python` uses the literal unadorned opening tag `<pre>` and puts highlighting on inner spans; the language info string is discarded, so `python` appears neither as a class nor elsewhere in the output solely because it labeled the fence. Each logical chapter is enclosed in `<div id = "chapter-N" class = "chapter">`, starting with `chapter-0`; this wrapper is present for ATX/setext headings, ordinary and long paragraphs, blank-line-separated paragraphs, lists, emphasis/code combinations, escaped punctuation, Unicode, raw inline HTML, undefined footnote references, annotation-heavy text, and nested structures. As specified for `--single` in Spec 9, multiple level-one headings in one single-mode input share its sole `chapter-0` wrapper. A Markdown soft break is serialized as a literal space in HTML text, whereas hard breaks emit `<br />`. A rule is rendered as an element with `class = "rule"`. Standalone images are placed in `div.image`, while inline images remain in a paragraph, preserving `src`, `alt`, and `title`. Footnote references have IDs such as `note-source-1-ID`, definitions appear in a notes container with reciprocal destination IDs, and formatting inside definitions is retained. Paragraphs receive sequential IDs such as `para-1`.

## Spec 19

Standalone HTML begins with `<!DOCTYPE html>`, contains parseable `<html lang="LANG">`, `<head>`, and `<body>`, and ends with `</html>`. The head includes UTF-8 charset, viewport content containing `width=device-width`, `<meta name="generator" content="crowbook">`, author metadata, a title, a substantial embedded `<style type = "text/css">`, and substantial embedded JavaScript containing functions. Include schema.org JSON-LD with a `Book` object containing at least name/title, author, and `inLanguage`. Render book title/author/subtitle in the body as applicable. When `--autograph` is used, the stdin line is rendered in the body inside `<div id = "autograph">`, after the prompt described in Spec 4. HTML-reserved characters in ordinary Markdown text are escaped, while inline HTML behavior follows `crowbook.html_as_text`; its default is `true`. Under that default, source `<span data-x="yes">raw</span>` serializes as escaped text `&lt;span data-x=“yes”&gt;raw&lt;/span&gt;`, including smart quotes, and the named entity source `&copy;` serializes as the Unicode character `©` rather than preserving its source spelling. The standalone head-title exception is specified in Spec 12. Empty input still produces valid head/body. Syntect mode emits visibly highlighted spans inside code blocks; `none` preserves plain code.

## Spec 20

Numbered HTML chapters use a heading containing `<span class = 'chapter-header'>LocalizedChapter N</span><br />Title`; the chapter-header span and title are separated by the literal `<br />`, with no intervening space. `rendering.num_depth` controls how deeply headings are numbered; 0 disables displayed numbering. Roman-numeral options change the corresponding number. In standalone HTML, `rendering.chapter.template` is ignored for the rendered body heading but used for a numbered chapter's inline-TOC label. With Roman numerals, `rendering.inline_toc: true`, a first chapter headed `# First`, and the configured value `Unit {{number}}: {{chapter_title}}`, the body heading remains `<span class = 'chapter-header'>Chapter I</span><br />First` while the TOC contains the label `Unit I: First`. `rendering.inline_toc.name` substitutes its configured text. Default standalone HTML does not contain `<nav id = "nav">`. With `rendering.inline_toc: true`, include `div#toc` containing links to chapter and section anchors. A `!` hidden chapter still contributes its source title. In a book whose first numbered chapter has headings `# First` and `## Section` and whose next, hidden chapter is headed `# Secret`, the TOC contains `<li><a href="#link-3">Secret</a></li>`, while the hidden content wrapper has an empty heading and still renders its body. Every TOC href resolves. Internal book links to `.md` or their `.html` equivalent are rewritten to the rendered chapter/anchor.

## Spec 21

Recognized local images in standalone HTML are embedded losslessly as base64 data URIs. Detect MIME case-insensitively: PNG uses `data:image/png;base64,`, SVG `data:image/svg+xml;base64,`, and JPG/JPEG an image/jpeg-compatible prefix. Resolve relative images against their Markdown file or configured image base. Reusing or embedding large images must not truncate bytes. An extensionless local image is not base64-embedded in standalone HTML: its `<img src>` retains the display path such as `./image_no_ext`, so the original filename remains literally present, and configured-output rendering reports `ERROR Resources: could not guess mime type of file ./image_no_ext`. Remote HTTP images are left unchanged. For a configured HTML output containing `http://example.com/image.png`, stderr is the banner, the aggregate-warning header, and `WARNING Resources: book includes non-local image http://example.com/image.png, which might cause problem for proper inclusion.`; it has no success-info line. Missing images identify both chapter and the resolved display path. With BOOK passed relative from its containing directory, a relative image such as `gone.png` is displayed as `./gone.png`; with BOOK passed by absolute path, the same image is displayed as the absolute directory containing BOOK followed by `/./gone.png`. An image path that is itself absolute, such as `/nonexistent/absolute/path.png`, remains absolute. When HTML is explicitly selected with `--to html --output ...`, the standalone-HTML error line is `ERROR CHAPTER: Could not find file 'DISPLAY_PATH' for image`, without an `Error rendering html:` prefix or aggregate-warning header. For a configured `output.html`, stderr ordering is banner, `WARNING Crowbook exited successfully, but the following errors occurred:`, then `ERROR Error rendering html: CHAPTER: Could not find file 'DISPLAY_PATH' for image`; for example, `with_missing_image.md` and `nonexistent.png` produce exactly those three lines in that order. EPUB missing-cover errors likewise retain the book filename and relative display spelling, as in `BOOK: Could not find file './missing_cover.jpg' for cover`; configured-output rendering may prefix this with `Error rendering epub:`. As specified for standalone HTML metadata, a missing cover is ignored there and HTML is still emitted.

## Spec 22

`html.css` replaces the default base stylesheet with the named template file. `html.css.add` alone appends its literal CSS to the default stylesheet, but when `html.css` is also supplied the replacement file is the complete base stylesheet and `html.css.add` is not appended. For example, a replacement containing `body { color: rgb(1, 2, 3); }` appears in the output while simultaneous added text `p { border: 7px solid red; }` does not. Template paths use `resources.base_path.templates`. A value containing spaces is one filename, not multiple CSS files. Missing templates identify the source book, relative filename, and option key: `BOOK: Could not find file './FILE' for template 'html.standalone.template'`; missing CSS uses the same form with template key `'html.css'`. For configured output, missing CSS is aggregated after the banner and `WARNING Crowbook exited successfully, but the following errors occurred:`; `html.css: custom.css custom2.css` produces `ERROR Error rendering html: book.book: Could not find file './custom.css custom2.css' for template 'html.css'`. Custom standalone templates must substitute defined data such as `{{content}}`. An undefined variable reports `ERROR Error compiling template: render error` with no `Error rendering html:` prefix, followed by a blank line and the template-engine source location/reason. `html.header` and `html.footer` are honored. The standard standalone CSS includes Linux Libertine styling, body/paragraph/code/pre rules, table/note/image/chapter styles, and added code when no replacement stylesheet suppresses it.

## Spec 23

For `html.dir`, destination is a directory and must be supplied through `output.html.dir` in the book; a CLI-only `-o` destination has the status-101 behavior in Spec 8. Once that required option is present, delete an existing destination directory before generating, so no stale files survive. If it exists as a regular file, do not overwrite it; report `BOOK: Error during rendering: PATH already exists and is not a directory`, with the displayed path unquoted.

The built-in default `html.dir.template` does not complete a configured directory render. The process exits 0, and stderr is the banner followed by the aggregate-warning header and `ERROR Error rendering html.dir: Error compiling template: render error`. Before this error it writes every sequential `chapter_000.html`, `chapter_001.html`, etc., plus `stylesheet.css` and the 133-byte `print.css`. Each written chapter page contains the built-in navigation menu, including an anchor whose href is exactly `index.html`. The failed render does not write `index.html`, `menu.svg`, an `images/` directory, `highlight.js`, `highlight.css`, or `resources.files` output. This is also the behavior for one chapter and when `rendering.highlight: highlight.js` or image/resources options are configured.

When a supplied valid `html.dir.template` compiles for both chapter and index contexts, rendering completes and writes `index.html` and `menu.svg` in addition to the chapter and CSS files. `menu.svg` is 2,694 bytes, is valid SVG/XML, and begins `<?xml version="1.0" encoding="UTF-8" standalone="no"?>`. `print.css` remains 133 bytes and contains actual rules. An `images/` directory is created when local images are copied; a no-image book does not create an empty one. Every generated HTML page substitutes the supplied template data; navigation markup is present when that template includes the corresponding `toc`, `prev_chapter`, `next_chapter`, and index-link markup. On this successful path, `rendering.highlight: highlight.js` writes `highlight.js` (144,715 bytes, containing `n.hljs` and `highlight.js`) and `highlight.css` (1,159 bytes containing `.hljs`).

## Spec 24

On the successful custom-template path described in Spec 23, the HTML-directory index receives template data for `div#content`, title, author, optional subtitle, JSON-LD Book metadata, an all-chapter TOC whose links target real IDs in chapter files, optional inline `div#toc`, cover, and favicon when configured. A multi-chapter index has `p.next_chapter > a` linking to `chapter_000.html` with text such as `1. First »`; omit that start link for a single chapter. Chapter browser titles combine book and chapter titles. Chapter pages receive menu/script data including `function toggle()`, `display_menu`, `document.getElementById("nav")`, and `document.getElementById("content")`. With the built-in template, no index is produced, as specified in Spec 23.

## Spec 25

On a successful HTML-directory render, the `prev_chapter` and `next_chapter` template values depend on position: a one-chapter book has neither; first has only next; last has only previous; middle has both. When substituted, their containing paragraph classes are exactly `prev_chapter` and `next_chapter`. Hrefs use sequential filenames. Text is `« N. Title` and `N. Title »` when numbered, or omits `N.` when `rendering.num_depth: 0`. Images, cover, and icon are copied to `images/image_N.EXT` and markup uses that relative path. `resources.files` files/directories are recursively copied beneath `resources.out_path`, preserving nested layout, bytes, and symlink targets. Cross-chapter links using either `.md` or `.html` resolve to the matching `chapter_NNN.html`; unresolved links remain but warn that neither the given path nor its `.md` fallback matched. The built-in-template failure occurs before image/resource copying, as specified in Spec 23.

## Spec 26

LaTeX output is a complete UTF-8 document beginning with `\documentclass` and containing matching `\begin{document}`/`\end{document}`. A book configuration defaults to class `book`; `--single` defaults to `article`, so a single Markdown file containing `# First` and `# Second` emits `\documentclass{article}`, `\section{First}`, and `\section{Second}`. The `article` class never emits `\chapter`. For configured book output, Markdown levels map H1 to `\chapter`, H2 `\section`, H3 `\subsection`, H4 `\subsubsection`, and deeper headings through the renderer's legacy commands (including the tested spelling `\paragraoh` for the deepest tested heading). Label chapters sequentially `\label{chapter-0}`, etc. Unnumbered chapters use `\chapter*{Title}` plus `\addcontentsline{toc}{chapter}{Title}`. A `!` hidden declaration suppresses its source title and renders `\chapter*{}\label{chapter-N}` without a TOC entry. A `--` subchapter declaration renders `\section*{Title}` without a label or TOC entry. Parts use `\part{Title}`. Explicit chapter starts emit an appropriate `\setcounter{chapter}{N-1}`.

## Spec 27

LaTeX inline/block mappings are: strong `\mdstrong{}`, emphasis `\emph{}`, inline code `\mdcode{}`, deletion `\sout{}`, hard break `\mdhardbreak`, soft break as a space, rule `\mdrule`, quote `mdblockquote`, unordered list `itemize`, ordered list `enumerate`, and description list `\begin{description}[style=nextline, labelwidth=0pt]` with `\item[Term]`. The combined input `***both***` is exactly `\emph{\mdstrong{both}}`. A multiline term such as source lines `Long Term That` and `Might Wrap` before `:   Definition here.` becomes `\item[Long Term That Might Wrap]`. Custom ordered starts emit `\setcounter{enumi}{start-1}` (and correct deeper enum counters); support at least five nested enumerate levels without crashing. Tables use `\begin{mdtable}{|X|...|}`, ` & ` cells, `\\` rows, and `\hline`. Checked/unchecked tasks render `[$\boxtimes$]` and `[$\square$]`. Footnotes preserve the Markdown source label as the LaTeX optional ID: `[^second]` produces matching `\footnotemark[second]` and `\footnotetext[second]{...}`, rather than replacing it with a numeric sequence.

## Spec 28

Escape LaTeX-special text characters `& $ % # _ { } ~ ^ \` as `\&`, `\$`, `\%`, `\#`, `\_`, `\{`, `\}`, `\textasciitilde{}`, `\textasciicircum{}`, and `\textbackslash{}`. Syntect-highlighted blocks use `mdcodeblock` and color commands; non-highlighted blocks use `spverbatim`. Inline code adds `\allowbreak{}` after path/word-breaking punctuation such as `/`, `.`, `_`, parentheses, colon, and hyphen. Local images become `\mdimage{images/image_N.ext}` or `\mdstandaloneimage{...}`. A cover shares that sequential resource index rather than always using index 0: with one distinct chapter image at `images/image_0.png`, `tex.cover: true` adds `\usepackage{pdfpages}` and `\includepdf{images/image_1.png}`. Remote images are not emitted as local image commands.

## Spec 29

LaTeX metadata includes `\title{TITLE}`, `\author{AUTHOR}`, `pdfauthor={AUTHOR}`, and `pdftitle={TITLE}`. The default book preamble defines its title-page implementation with a literal `\renewcommand{\maketitle}` and later invokes `\maketitle`. Default paper is `a5paper`; book margins are left 2.5cm/right 1.5cm, article margins 2cm/2cm. Honor paper, all margins, font size (`\documentclass[12pt]{book}`), class, title-page enablement, cover, `tex.stdpage`, `tex.template.add`, and inline TOC (`\tableofcontents`). `rendering.initials` emits `\lettrine{F}{ollowing}` for an alphabetic first word but skips punctuation-led paragraphs. Custom chapter/part names emit `\renewcommand{\@chapapp}{...}` and `\renewcommand{\partname}{...}`.

## Spec 30

LaTeX language mappings include `en→english`, `fr→francais`, `de→ngerman`, `es→spanish`, `it→italian`, `nl→dutch`, `pt→portuguese`, `ru→russian`, and `pl→polish`; unknown languages fall back to English. Default/xelatex and tectonic output includes `fontspec` and `xunicode`. Links use `\href{URL}{text}`; when text equals URL use `\url{URL}`. By default external links also receive printable URL footnotes; `tex.links_as_footnotes: false` disables those. Internal chapter links with hyperref become `\hyperref[chapter-N]{text}`. `tex.pageref_template` accepts both `<<key>>` and the whitespace-bearing `<< key >>` placeholder and replaces either with the label; `\footnote{see p.\pageref{<< key >>}}` therefore produces `\footnote{see p.\pageref{chapter-1}}`. `tex.hyperref: false` must still yield a valid document.

## Spec 31

EPUB output is a readable ZIP. `mimetype` is the first-class required entry, stored uncompressed, with exact bytes `application/epub+zip`. Include `META-INF/container.xml`, an OPF package document, stylesheet, title page, chapter XHTML files, and EPUB-2 `toc.ncx`; generated XHTML starts with XML declaration, has a DOCTYPE, HTML/head/body, generator metadata, language (`lang` and `xml:lang`), stylesheet link, and valid closing tags. Default OPF version is `2.0`; `epub.version: 3` uses `3.0`. Output must be nontrivial (ordinary books exceed 1KB).

## Spec 32

EPUB OPF metadata includes exact configured `dc:title`, `dc:creator`, `dc:language`, optional subject/description, and a `dc:identifier` beginning `urn:uuid:`. The package's `unique-identifier` points to that identifier. Escape XML characters in title. Manifest entries all have nonempty unique IDs and appropriate media types; every spine `idref` refers to a manifest ID. Spine begins with title page and preserves chapter order. Guide contains at least `title-page` and `text`, plus cover when present. The NCX `docTitle` is the localized table-of-contents label, not the configured book title; with `lang: de`, its contained text element is `<text>Inhaltsverzeichnis</text>`. NCX also includes required `dtb:depth`, `dtb:totalPageCount`, and `dtb:maxPageNumber` metadata and sequential unique navPoints with play orders, labels, and src URLs. With `epub.toc.extras: true`, NCX includes `cover.xhtml` and `title_page.xhtml`.

## Spec 33

EPUB creates one XHTML per logical chapter in order and assigns IDs to headings and paragraphs. Chapter numbering/localized labels follow HTML rules. Markdown elements render with the same semantic XHTML tags, including code/pre, lists, emphasis/strong, and footnotes. EPUB 2 footnotes include superscript anchors and reciprocal `note-source-`/`note-dest-` IDs; EPUB 3 additionally uses `epub:type` noteref/footnote semantics. With `rendering.inline_toc: true`, the package contains separately named `OEBPS/nav.xhtml` and `OEBPS/toc.xhtml` documents (in addition to the EPUB-2 `toc.ncx`), but it does not add an inline navigation list or an element with id `toc` to chapter XHTML. Every XHTML file links `stylesheet.css`. Title page displays configured book title and author.

## Spec 34

EPUB embeds each distinct local image once under `OEBPS/images/image_N.EXT` (or an equivalent package root ending in `/images/image_N.EXT`), retains exact bytes, declares correct MIME type, and rewrites chapter src to `images/image_N.EXT`. Preserve PNG, JPEG, and SVG formats and uppercase extensions. Cover generation includes an embedded cover image, cover XHTML with `<img>`, and OPF cover declarations. An extensionless source receives a fallback name and assumed PNG format. Its warning display path prefixes the image spelling without normalizing an existing `./`: with Markdown source `![x](./image_no_ext)` and BOOK `b.book` passed relative from its containing directory, stderr includes `WARNING Resources: book includes image ././image_no_ext which doesn't have an extension`; passing that BOOK by absolute path instead places its absolute containing directory before `/././image_no_ext`. A source spelled `image_no_ext` (without its own `./`) correspondingly displays as `./image_no_ext` for the relative-BOOK invocation. In all of these cases stderr also includes `ERROR EPUB: could not guess the format of images/image_0 based on extension. Assuming png.`. `epub.css` replaces stylesheet content, while `epub.css.add` alone appends its literal CSS to the default stylesheet. When both are supplied, the replacement file is the complete resulting stylesheet and the `epub.css.add` text is not appended; a replacement containing `body { color: purple; }\n` yields exactly those bytes.

## Spec 35

`resources.files` is a list of file/directory paths. Recursively walk directories (following symlinks), preserve nested relative structure below `resources.out_path` (default `data`), and include exact bytes in EPUB output and in an HTML-directory output whose template compilation completes. The built-in HTML-directory template failure in Spec 23 happens before this copy, so that path creates no `resources.files` tree. A missing relative resource's diagnostic path depends on the BOOK spelling. With BOOK passed relative from its containing directory, configured EPUB output and `[nonexistent.txt]` produce `ERROR Error rendering epub: Error during rendering: error reading file ./nonexistent.txt: No such file or directory (os error 2)` after the aggregate-warning header. With BOOK passed by absolute path, the diagnostic instead places the absolute directory containing BOOK before `/./nonexistent.txt`. Unsupported special files must produce an error and never hang. When an external `zip` command cannot run, fall back to an internal ZIP writer and emit `WARNING Could not run zip command, falling back to zip library` where applicable.

## Spec 36

PDF generation first generates the same LaTeX/resources into a temporary directory (honoring `crowbook.temp_dir`), then invokes `tex.command` (default `xelatex`) three times so references settle. The command is harness/environment-provided. If it cannot start during configured PDF rendering, report `ERROR Error rendering pdf: Error during temporary files editing: failed to run command 'COMMAND'` after the aggregate-warning header. If it exits unsuccessfully or succeeds without producing the expected PDF, likewise report an `Error rendering pdf:` / `Error during temporary files editing:` diagnostic and do not create a bogus destination. On success copy the produced PDF bytes exactly to the requested output. This applies to large chapters, many/nested images, footnotes, tables, alternative commands (`pdflatex`, `lualatex`, tectonic/custom), and all TeX options.

## Spec 37

`--stats` parses the book/single document but renders no book format. For every declared chapter, in declaration order, print filename/path, Unicode character count, word count, and characters-per-word; then totals. Construct the counted text by recursively concatenating parsed token content: string and inline/block-code content is copied verbatim, a soft break contributes one space, a hard break or rule contributes one newline, and images (including alt/path syntax), footnotes, and tables contribute nothing. Formatting/container tokens contribute only their recursively collected content; critically, no separator is inserted between adjacent structural containers such as a heading and the following paragraph. Count Unicode code points in that concatenated string, and count words by splitting that same string on whitespace. Consequently, the source ``# H\n\nabc dé [link](https://x) `z` ![ignored](pic.png)\n`` has its heading text abut its following paragraph text and reports 15 characters, 4 words, and `3.75`. Empty/whitespace content gives 0, 0, and `NaN`; otherwise ratio is chars/words rounded to exactly two decimals.

Format exactly as follows: first-column width is `max(len("Chapter"), len("TOTAL:"), longest displayed chapter path)`, header is left aligned and numeric fields are each width 10, with two spaces before `Chars/Word`; the short separator line is exactly `---------`; rows and TOTAL use the same alignment, and output ends in a blank line. Example:

```text
Chapter           Chars      Words  Chars/Word
---------
chapter1.md         237         35        6.77
chapter2.md         141         18        7.83
chapter3.md          31          4        7.75
---------
TOTAL:              409         57        7.18

```

## Spec 38

`--list-options` exits 0 and prints a substantial human-readable catalog to stdout (over 5,000 bytes and 100 lines), headed by `METADATA`, `ADDITIONAL METADATA`, `OUTPUT OPTIONS`, `RENDERING OPTIONS`, `SPECIAL OPTIONS`, `HTML OPTIONS`, `STANDALONE HTML OPTIONS`, `MULTIFILE HTML OPTIONS`, `EPUB OPTIONS`, `LATEX OPTIONS`, `RESOURCES OPTIONS`, `INPUT OPTIONS`, and `CROWBOOK OPTIONS`. Include every key in Specs 12-15 except `proofread.repetitions` and `proofread.repetitions.fuzzy.threshold`; those two strings do not occur in the catalog even though the configuration parser accepts them. Each included key has `type: ...`, `default: ...`, and a description. The catalog's type vocabulary is distinct from the YAML storage types: `author`, `title`, `lang`, `subject`, `description`, and the other metadata strings are labeled with the literal `type: metadata` (for example, `type: metadata (default: "")`), while `cover` is `type: path`. Required descriptions include `Author of the book`, `Title of the book`, and `Language of the book`; include over 50 `default:` occurrences. The banner remains on stderr, never mixed into stdout.

## Spec 39

`--print-template NAME` exits 0 and writes only the template bytes to stdout, with the normal banner on stderr. Recognized names include `html.css`, `epub.css`, `tex.template`, `html.standalone.template`, `html.dir.template`, and `epub.chapter.xhtml`. CSS outputs are different where appropriate, substantial, newline-terminated, and contain actual body/code/pre/font/background rules plus literal template variables such as `{{additional_code}}`; `html.css` contains the EPUB base styles plus HTML navigation/layout rules and `{{colors}}`. `tex.template` is over 100 bytes and contains a complete templated LaTeX document with `\documentclass`, `\usepackage`, `\begin{document}`, `<<content>>`, and `\end{document}`. The built-in `html.standalone.template` is 1,888 bytes, contains DOCTYPE, inline `<style`, and `{{content}}`; the built-in `html.dir.template` is 1,342 bytes and contains DOCTYPE, external `stylesheet.css`, `{{...}}`, and `{%...%}`; EPUB chapter template is XML/XHTML with namespace and `{{content}}`. Template printing takes precedence over `-t` and `-o`: `--print-template epub.css -t html -o saved.css` still writes the 3,846 template bytes to stdout and does not create `saved.css`. Invalid NAME writes `CROWBOOK 0.17.0\nERROR NAME is not a valid template name\n` to stderr and nothing to stdout.

## Spec 40

The canonical stdout for the three exactly compared built-in templates is given below. The content inside each fence is literal, begins with its first shown character, and has exactly one final newline. No banner is part of stdout.

For `epub.css`:

```text
body {
    font-family: "Linux Libertine", "Georgia", serif;
    text-align: justify;
    font-size: 100%;
}

p {
    text-indent: 1.25em;
    margin:0;
    hyphens: auto;
}

blockquote {
    margin: 1em;
    font-style: italic;
}
code {
    font-size: 80%;
    font-family: "Linux Libertine Mono", monospace;
    background-color: #F0F0F0;
}
pre {
    font-family: "Linux Libertine Mono", monospace;
    text-align: left;
    margin: 1em;
    padding-top: 0;
    background-color: #F0F0F0;
    white-space: pre-wrap;
    word-wrap: break-word;
}
/* Try to disable hyphenation in titles */
h1, h2, h3, h4, h5, h5 {
    adobe-hyphenate: none;
    -ms-hyphens: none; /* Trident (Windows) */
    -moz-hyphens: none; /* Gecko (Firefox) */
    -webkit-hyphens: none; /* Webkit */
    -epub-hyphens: none; /* EPUB 3 */
    hyphens: none; /* Futur standard */
}

h1, h2, h3, h4, h5, h6 {
    text-align: left;
    font-family: Linux Biolinum, sans-serif;
    font-variant: small-caps;
}

/* Title of a part */
h1.part {
    font-size: 250%;
    text-align: center;
}

/* The `Part X` section of a part */
h2.part {
    font-size: 175%;
    text-align: center;
}

/* The "Chapter X" section of a chapter */
span.chapter-header {
    font-size: 75%;
}

/* Title of the book */
h1.title {
    text-align: center;
    font-size: 300%;
}
/* Author */
h2.author {
    text-align: right;
    font-size:  200%;
}

/* Subtitle */
h2.subtitle {
    text-align: center;
    font-size: 200%;
}

/* When toc is displayed inlined */
#toc ol, #toc ul {
    padding: 0;
    margin-left: 1em;
}
#toc li {
    list-style-type: none;
    margin: 0; padding: 0;
}

#toc li:before {
    content: none;
}

#cover img {
    width: 100%;
    max-height: 100%;
}

.image {
    margin: auto;
    width: 80%;
}

.image img {
    width: 100%;
    max-height: 100%;
}

.rule {
    text-align: center !important;
    margin-top: 1em;
    margin-bottom: 1em;
    font-weight: bold;
    page-break-inside: avoid;
    break-inside: avoid;
    page-break-after: avoid;
    break-after: avoid;
}

/* The number of the note in an expanded footnote (e.g. [3]) */
.note-number {
    font-weight: bold;
    margin-right: 1em;
}

td.note-number {
    vertical-align: top;
}

/* When footnotes (try to) be displayed as margin notes */
.sidenote {
    display: block;
    float: right;
    width: 30%;
    border: 1px solid black;
    margin: 1em;
    padding: .5em;
    margin-right: -1.5em;
}

.sidenote .note-number {
    float: left;
}

/* The div class displaying notes at the end of a chapter */
div.notes {
    text-align: justify;
    border-top: thin dashed black;
    margin-top: 1em;
}

table.notes {
    border-collapse: collapse;
    border-style: hidden;
}

table.notes tr td {
    margin-left: 1em;
    margin-right: 1em;
}

table.notes tr td p {
    text-indent: 0;
}

/* Every markdown table is included in a <div class = "table"> */
.table {
    margin: 1em;
}

.table table {
    width: 80%;
    margin: 0 auto;
    border-style: solid;
    border-width: thin;
    border-color: black;
    border-collapse: collapse;
}

.table table th, .table table td {
    border-style: solid;
    border-width: 1px;
    text-align: center;
}

.table table th {
    font-weight: bold;
    font-variant: small-caps;
}

{% if lang | eq: "fr" %}
/* Make list displays '–' instead of bullets */
ul li {
    list-style-type: '–';
    padding-left: .5em;
}
{% endif %}

span.initial {
    float: left;
    font-size: 285%;
    font-weight: bold;
    margin-right: 0.05em;
    line-height: 0.8em;
}

p.first-para {
    text-indent: 0;
}

/* Use this for escape narrow space so it is non-breaking */
.nnbsp {
    /* white-space: nowrap;*/
    word-spacing: -0.13em;
    /* Following necessary for Kobo EPUB3 reader??? */
    margin: 0;
    padding: 0;
}

{{additional_code}}

```

For `html.css`:

```text
body {
    font-family: "Linux Libertine", "Georgia", serif;
    text-align: justify;
    font-size: 100%;
}

p {
    text-indent: 1.25em;
    margin:0;
    hyphens: auto;
}

blockquote {
    margin: 1em;
    font-style: italic;
}
code {
    font-size: 80%;
    font-family: "Linux Libertine Mono", monospace;
    background-color: #F0F0F0;
}
pre {
    font-family: "Linux Libertine Mono", monospace;
    text-align: left;
    margin: 1em;
    padding-top: 0;
    background-color: #F0F0F0;
    white-space: pre-wrap;
    word-wrap: break-word;
}
/* Try to disable hyphenation in titles */
h1, h2, h3, h4, h5, h5 {
    adobe-hyphenate: none;
    -ms-hyphens: none; /* Trident (Windows) */
    -moz-hyphens: none; /* Gecko (Firefox) */
    -webkit-hyphens: none; /* Webkit */
    -epub-hyphens: none; /* EPUB 3 */
    hyphens: none; /* Futur standard */
}

h1, h2, h3, h4, h5, h6 {
    text-align: left;
    font-family: Linux Biolinum, sans-serif;
    font-variant: small-caps;
}

/* Title of a part */
h1.part {
    font-size: 250%;
    text-align: center;
}

/* The `Part X` section of a part */
h2.part {
    font-size: 175%;
    text-align: center;
}

/* The "Chapter X" section of a chapter */
span.chapter-header {
    font-size: 75%;
}

/* Title of the book */
h1.title {
    text-align: center;
    font-size: 300%;
}
/* Author */
h2.author {
    text-align: right;
    font-size:  200%;
}

/* Subtitle */
h2.subtitle {
    text-align: center;
    font-size: 200%;
}

/* When toc is displayed inlined */
#toc ol, #toc ul {
    padding: 0;
    margin-left: 1em;
}
#toc li {
    list-style-type: none;
    margin: 0; padding: 0;
}

#toc li:before {
    content: none;
}

#cover img {
    width: 100%;
    max-height: 100%;
}

.image {
    margin: auto;
    width: 80%;
}

.image img {
    width: 100%;
    max-height: 100%;
}

.rule {
    text-align: center !important;
    margin-top: 1em;
    margin-bottom: 1em;
    font-weight: bold;
    page-break-inside: avoid;
    break-inside: avoid;
    page-break-after: avoid;
    break-after: avoid;
}

/* The number of the note in an expanded footnote (e.g. [3]) */
.note-number {
    font-weight: bold;
    margin-right: 1em;
}

td.note-number {
    vertical-align: top;
}

/* When footnotes (try to) be displayed as margin notes */
.sidenote {
    display: block;
    float: right;
    width: 30%;
    border: 1px solid black;
    margin: 1em;
    padding: .5em;
    margin-right: -1.5em;
}

.sidenote .note-number {
    float: left;
}

/* The div class displaying notes at the end of a chapter */
div.notes {
    text-align: justify;
    border-top: thin dashed black;
    margin-top: 1em;
}

table.notes {
    border-collapse: collapse;
    border-style: hidden;
}

table.notes tr td {
    margin-left: 1em;
    margin-right: 1em;
}

table.notes tr td p {
    text-indent: 0;
}

/* Every markdown table is included in a <div class = "table"> */
.table {
    margin: 1em;
}

.table table {
    width: 80%;
    margin: 0 auto;
    border-style: solid;
    border-width: thin;
    border-color: black;
    border-collapse: collapse;
}

.table table th, .table table td {
    border-style: solid;
    border-width: 1px;
    text-align: center;
}

.table table th {
    font-weight: bold;
    font-variant: small-caps;
}

{% if lang | eq: "fr" %}
/* Make list displays '–' instead of bullets */
ul li {
    list-style-type: '–';
    padding-left: .5em;
}
{% endif %}

span.initial {
    float: left;
    font-size: 285%;
    font-weight: bold;
    margin-right: 0.05em;
    line-height: 0.8em;
}

p.first-para {
    text-indent: 0;
}

/* Use this for escape narrow space so it is non-breaking */
.nnbsp {
    /* white-space: nowrap;*/
    word-spacing: -0.13em;
    /* Following necessary for Kobo EPUB3 reader??? */
    margin: 0;
    padding: 0;
}

{{additional_code}}
/* Default  HTML CSS file includes default EPUB CSS file */

{{colors}}

p.first-para:first-letter {
    font-size: 300%;
    float: left;
    font-weight: bold;
    margin-right: 0.05em;
    line-height: 1em;
}

/* The nav element corresponding to the navigation menu */
nav {
    z-index: 2;
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 20%;
    overflow-y: auto;
    font-size: 80%;
    margin-left: 0;
    border-right-width: 2px;
    border-right-style: dashed;
}

#nav code {
    background-color: transparent;
}

#nav a:link {
    text-decoration: none;
}

#nav a:visited {
    text-decoration: none;
}

#nav {
    text-align: left;
}

#nav h2 {
    text-align: center;
}

#nav li {
    list-style-type: none;
    text-indent: -1em;
}

#nav li:before {
    content: none;
}

#nav ul {
    padding-right: 1em;
    padding-left: 1.5em;
}

/* The menu containing the button to display the navigation bar */
#menu {
    position: fixed;
    z-index: 2;
    top: 0em;
    left: 1em;
    transition: left 1s;
}

#menu img {
    opacity: 0.5;
}

#menu img:hover {
    opacity: 1.0;
    cursor: pointer;
}

#menu-button {
    height: 1.5em;
    padding: 0.5em;
}

#book-button {
    height: 1.5em;
    padding: 0.5em;
    float: left;
}

/* Hide navigation bar */
#nav {
    left: -21%;
    transition: left 1s;
}

/* The main content of the book */
#content {
    overflow-y: auto;
    margin-left: 0;
    margin-right: 0;
    margin-top: 0;
    margin-bottom: 0;
    transition: margin-left 1s;
}

/* Used for multifiles HTML */
.prev_chapter {
    text-align: left;
    text-indent: 0;
    margin-bottom: 1em;
    font-size: 120%;
    font-variant: small-caps;
    font-weight: bold;
}

.next_chapter {
    text-align: right;
    margin-top: 1em;
    margin-bottom: 1em;
    font-size: 120%;
    font-variant: small-caps;
    font-weight: bold;
}

/* Improving readability for the HTML format only */
p, blockquote, li, .image  {
    margin-right: auto;
    max-width: 33em;
}

blockquote {
    padding: 1em;
}

#content {
    text-align: center;
}

#page {
    display: inline-block;
    text-align: justify;
    max-width: 33em;
}

#nav-container {
    top: 0;
    width: 100%;
}

#nav-title {
    top: 0;
}

#toolbar {
    top: 0;
    float: left;
}

#toolbar img {
    cursor: pointer;
}

footer {
    margin-top: 2em;
    margin-bottom: 0;
}

#top {
    margin-top: 0;
    margin-bottom: 1em;
}

#top p {
    font-family: "Linux Biolinum";
    font-weight: bold;
    font-variant: small-caps;
}

footer, #top {
    padding-top: .25em;
    padding-bottom: .25em;
    margin-left: 0;
    margin-right: 0;
    text-align: center;
    transition: margin-left 1s;
}

footer a, #top a {
    text-decoration: none;
}

footer p, #top p {
    text-indent: 0;
    margin-left: auto;
    margin-right: auto;
    margin-bottom: 0.5em;
    margin-top: 0.5em;
    max-width: 33em;
}

.popup_footnote {
    margin: 2em;
    padding : 1em;
    right: 2em;
    max-width: 20em;
}


{{additional_code}}

```

For `tex.template`:

```text
\documentclass<# if has_tex_size #>[<<tex_size>>pt]<# endif #>{<<class>>}

%% Package inclusion
<# if xelatex #>
% Unicode support if xelatex is used
\usepackage{fontspec}
\usepackage{xunicode}
<# else #>
% Unicode support if xelatex is not used
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}

% Even with inputenc, not all unicode chars are recognized when not using xelatex. This a
% listof some I stumbled upon and manually added to fix
\usepackage{newunicodechar}
\newunicodechar{ }{ } % thin non breaking space
\newunicodechar{°}{$^{\circ}$}
% Force LaTeX not to overflow page e.g. when there is long words
% (e.g. filenames, urls, ...). The result is not necessarily very
% beautiful, though, but at least it's readable.
\setlength\emergencystretch{.5\textwidth}
<# endif #>

\usepackage[<<tex_lang>>]{babel} % Language support
\usepackage{fancyhdr} % Headers
\usepackage{enumitem}

% Allows hyphenatations in \texttt
\usepackage[htt]{hyphenat}

<# if use_strikethrough #>
% Only included if strikethrough is used in the document
\usepackage[normalem]{ulem}
<# endif #>
<# if use_taskitem #>
\usepackage{amssymb}
<# endif #>
% Set hyperlinks and metadata
\usepackage[colorlinks=true,breaklinks=true,hypertexnames=false]{hyperref}
\hypersetup{pdfauthor={<<author>>},
  pdftitle={<<title>>},
  pdfsubject={<<description>>}
}
<# if xelatex #>
<# else #>
\usepackage[anythingbreaks]{breakurl}
<# endif #>


<# if initials #>
% Only included if use_initials is set to true
\usepackage{lettrine}
<# endif #>

<# if stdpage #>
% Only included if the stdpage option is set to true
\usepackage[<<papersize>>]{geometry}
\usepackage[hyphen=false, parskip]{stdpage}
<# else #>
% Included if the stdpage option if set to false
\usepackage[<<papersize>>, top=<<margin_top>>, bottom=<<margin_bottom>>,
  left=<<margin_left>>,right=<<margin_right>>]{geometry} % Set dimensions/margins of the page
<# endif #>

<# if use_cover #>
% Only included if tex.cover is set to true
\usepackage{pdfpages}
<# endif #>


\makeatletter
\date{<<date>>}

<# if not stdpage #>
  <# if book #>
% Redefine the \maketitle command, only for book class (not used if stdpage option is set to true)
\renewcommand{\maketitle}{
  <# if use_cover #>
  % cover
  \includepdf{<<cover_path>>}
  \newpage
  % Empty left page
  \thispagestyle{empty}
  \cleardoublepage

  <# endif #>

  % First page with only the title
  \thispagestyle{empty}
  \vspace*{\stretch{1}}

  \begin{center}
    {\Huge \@title   \\[5mm]}
  \end{center}
  \vspace*{\stretch{2}}

  \newpage
  % Empty left page
  \thispagestyle{empty}
  \cleardoublepage

  % Main title page, with author, title, subtitle, date
  \begin{center}
    \thispagestyle{empty}
    \vspace*{\baselineskip}
    \rule{\textwidth}{1.6pt}\vspace*{-\baselineskip}\vspace*{2pt}
    \rule{\textwidth}{0.4pt}\\[\baselineskip]

    {\Huge\scshape \@title   \\[5mm]}
    {\Large <<subtitle>>}

    \rule{\textwidth}{0.4pt}\vspace*{-\baselineskip}\vspace{3.2pt}
    \rule{\textwidth}{1.6pt}\\[\baselineskip]

    \vspace*{4\baselineskip}

    {\Large \@author}
      <# if has_autograph #>

    \vspace*{10\baselineskip}

    <<autograph>>
      <# endif #>
    \vfill
      <# if has_date #>\@date<# endif #>
  \end{center}

  \pagebreak
  \newpage
  % Copyright page with author, version, and license
  \thispagestyle{empty}
  \null\vfill
  \noindent
  \begin{center}
    {\emph{\@title}<#if has_version #>{, <<version>>}<# endif #><# if has_author #>, © \@author<# endif #>.\\[5mm]}
    <# if has_license #>{<<license>>\\[5mm]}<# endif #>
  \end{center}
  \pagebreak
  \newpage
}
  <# endif #>


% Redefine headers
\pagestyle{fancy}
\fancyhead{}
\fancyhead[CO,CE]{\thepage}
\fancyfoot{}


<# endif #>

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Command and environment definitions
%
% Here, commands are defined for all Markdown element (even if some
% of them do nothing in this template).
%
% If you want to change the rendering of some elements, this is probably
% what you should modify.
%
% Note that elements that already have a LaTeX semantic equivalent aren't redefined
% : if you want to redefine headers, you'll have to renew \chapter, \section, \subsection,
% ..., commands. If you want to change how emphasis is displayed, you'll have to renew
% the \emph command, for list the itemize one, for ordered list the enumerate one,
% for super/subscript the \textsuper/subscript ones.
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Strong
\newcommand\mdstrong[1]{\textbf{#1}}

% Code
\newcommand\mdcode[1]{\texttt{#1}}

% Rule
% Default impl : (displays centered asterisks)
\newcommand\mdrule{
  \nopagebreak
  {\vskip 1em}
  \nopagebreak
  \begin{center}
    ***
  \end{center}
  \nopagebreak
 {\vskip 1em}
 \nopagebreak
}

% Hardbreak
\newcommand\mdhardbreak{\\}

% Block quote$
\newenvironment{mdblockquote}{%
  \begin{quotation}
    \itshape
}{%
  \end{quotation}
}


% Code block
%
% Only used if syntect is used for syntax highlighting is used, else
% the spverbatim environment is preferred.
<# if use_codeblocks #> % This part is only included if document contains code blocks
\usepackage{spverbatim}
\usepackage{color}
\usepackage[
  topline=false,
  rightline=false,
  bottomline=false]{mdframed}

\newenvironment{mdcodeblock}{%
  \begin{mdframed}
}{%
  \end{mdframed}
}
<# endif #>


<# if use_images #>
% Only included if document contains images
\usepackage{graphicx}

% Standalone image
% (an image alone in its paragraph)
\newcommand\mdstandaloneimage[1]{
  \begin{center}
    \includegraphics[width=0.8\linewidth]{#1}
  \end{center}
}

% Image
% (an image embedded in a pagraph or other element)
\newcommand\mdimage[1]{\includegraphics{#1}}
<# endif #>

<# if use_tables #>
% Only included if document contains tables
\usepackage{tabularx}

% Table environment
% Crowbook currently always insert \hline at beginning and end of the table


\newenvironment{mdtable}[1]{%
  \center
  \tabularx{\textwidth}{#1}
  \hline
}{%
  \endtabularx
  \endcenter
}
<# endif #>

<<additional_code>>

\makeatother

\title{<<title>>}
\author{<<author>>}

\begin{document}

% Redefine chapter and part names if they needs to be
% Needs to be after \begin{document} because babel
<# if chapter_name #>
\makeatletter
\renewcommand{\@chapapp}{<<chapter_name>>}
\makeatother
<# endif #>

<# if part_name #>
\renewcommand{\partname}{<<part_name>>}
<# endif #>


<# if tex_title #>
\maketitle
<# endif #>

<# if inline_toc #>
\tableofcontents
<# endif #>

<<content>>

\end{document}

```

## Spec 41

Operational diagnostics aggregate rather than crash when rendering multiple configured outputs. If earlier stages allow continuing, prefix the final group with `WARNING Crowbook exited successfully, but the following errors occurred:` and then one `ERROR ...` or `WARNING ...` line per issue. Important diagnostic forms are `Error rendering FORMAT: ...`, `BOOK:LINE: Error converting BookOption: ...`, `Could not find file 'PATH' for DESCRIPTION`, and template/resource/zip errors retaining the underlying filename and OS detail. Source line numbers are one-based. Chapter-declaration errors point to that declaration, but option-conversion errors use the line that terminates the contiguous YAML option block. If an invalid option is physically on line 5 and a blank line 6 ends its block, the diagnostic is `BOOK:6:`; the same terminating-blank rule gives the `--set` location described in Spec 11. When the next chapter declaration immediately follows the last option with no intervening blank, the last option's own line is reported instead. All output is UTF-8 and every textual diagnostic ends with a newline.

## Spec 42

The following parser-error transcripts are exact, including capitalization, blank lines, indentation, and final newline.

For `--to invalid_format`:

```text
error: invalid value 'invalid_format' for '--to <to>'
  [possible values: epub, pdf, html, tex, odt, html.dir]

For more information, try '--help'.
```

For `--output out.html BOOK` without `--to`:

```text
error: the following required arguments were not provided:
  --to <to>

Usage: executable --to <to> --output <output> <BOOK>

For more information, try '--help'.
```

For `--set key`:

```text
error: 2 values required by '--set <set> <set>...'; only 1 was provided

Usage: executable [OPTIONS] [BOOK]

For more information, try '--help'.
```

For `--quiet --verbose BOOK`:

```text
error: the argument '--quiet' cannot be used with '--verbose'

Usage: executable --quiet <BOOK>

For more information, try '--help'.
```

For `--verbose --quiet --single BOOK`:

```text
error: the argument '--verbose' cannot be used with '--quiet'

Usage: executable --verbose --single <BOOK>

For more information, try '--help'.
```

Representative exact operational transcripts are:

```text
CROWBOOK 0.17.0
ERROR missing_chapter.book:5: Could not find file 'nonexistent_chapter.md' for book chapter
```

and, for the same error under quiet mode:

```text
ERROR missing_chapter.book:5: Could not find file 'nonexistent_chapter.md' for book chapter
```

An invalid template named `nonexistent_template` yields:

```text
CROWBOOK 0.17.0
ERROR nonexistent_template is not a valid template name
```

Running `test.book --set invalid_option value` when option lines 1-3 are terminated by blank line 4 yields:

```text
CROWBOOK 0.17.0
ERROR Error in setting key invalid_option: test.book:4: Error converting BookOption: unrecognized key 'invalid_option'
```

An empty `empty.book` yields:

```text
CROWBOOK 0.17.0
ERROR empty.book: Error parsing configuration file: "could not parse %{file} as a book file."
Maybe you meant to run crowbook with the --single argument?

```
