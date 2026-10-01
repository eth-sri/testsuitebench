# Clarified executable specification

The required artifact is a single executable file named `executable`. It is a command-line program for creating, building, testing, cleaning, watching, and serving books whose source is Markdown. All paths, streams, files, subprocess interactions, and HTTP behavior below are observable parts of the interface. Text files are UTF-8 unless explicitly described otherwise.

## Spec 1

The program's public name and version are `mdbook` and `0.5.0-alpha.1`. Running `executable --version` or `executable -V` writes exactly `mdbook v0.5.0-alpha.1\n` to stdout and exits 0. A version flag following a subcommand exits 0 and uses that subcommand's scoped name, for example `executable clean --version` prints `mdbook-clean v0.5.0-alpha.1`; the same rule applies to `init`, `build`, `test`, `completions`, `watch`, and `serve`.

The command set, in order, is `init`, `build`, `test`, `clean`, `completions`, `watch`, and `serve`. `help` is also displayed as the final help command. No arguments is an error: print the main help to stderr and exit 2. `--help` and `-h` print help to stdout and exit 0. `help` alone displays main help, and `help NAME` displays help for a real subcommand.

## Spec 2

The main help text is exactly the following, including order, capitalization, blank lines, indentation, spelling, and final newline (terminal-width wrapping of descriptions is allowed only where whitespace-normalized comparisons cannot distinguish it):

```text
Creates a book from markdown files

Usage: executable [COMMAND]

Commands:
  init         Creates the boilerplate structure and files for a new book
  build        Builds a book from its markdown files
  test         Tests that a book's Rust code samples compile
  clean        Deletes a built book
  completions  Generate shell completions for your shell to stdout
  watch        Watches a book's files and rebuilds it on changes
  serve        Serves a book at http://localhost:3000, and rebuilds it on changes
  help         Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version

For more information about a specific command, try `mdbook <command> --help`
The source code for mdBook is available at: https://github.com/rust-lang/mdBook
```

Subcommand help goes to stdout, exits 0, starts with the description shown above for that subcommand, contains its usage and options, and ends in a newline. Its usage is:

```text
Usage: executable init [OPTIONS] [dir]
Usage: executable build [OPTIONS] [dir]
Usage: executable test [OPTIONS] [dir]
Usage: executable clean [OPTIONS] [dir]
Usage: executable watch [OPTIONS] [dir]
Usage: executable serve [OPTIONS] [dir]
Usage: executable completions <SHELL>
```

All subcommands expose `-h, --help` and `-V, --version`. The optional `[dir]` means the book root and defaults to the current directory.

The `init --help` text is exact:

```text
Creates the boilerplate structure and files for a new book

Usage: executable init [OPTIONS] [dir]

Arguments:
  [dir]  Directory to create the book in
         (Defaults to the current directory when omitted)

Options:
      --theme            Copies the default theme into your source folder
      --force            Skips confirmation prompts
      --title <title>    Sets the book title
      --ignore <ignore>  Creates a VCS ignore file (i.e. .gitignore) [possible values: none, git]
  -h, --help             Print help
  -V, --version          Print version
```

Help processing is position-sensitive. If the help flag occurs first, it takes effect immediately: `executable init --help --bogus-flag` exits 0, writes the exact init help above to stdout, and writes nothing to stderr. An unknown option before a help flag is instead diagnosed before help processing. In particular, `executable init --unknown --help` exits 2, writes nothing to stdout, and writes exactly:

```text
error: unexpected argument '--unknown' found

  tip: to pass '--unknown' as a value, use '-- --unknown'

Usage: executable init [OPTIONS] [dir]

For more information, try '--help'.
```

## Spec 3

Argument parsing follows a strict git-style subcommand parser. Unknown commands or options, missing values, duplicate non-repeatable options, invalid enumerated values, and excess positional arguments write only to stderr and exit 2. Diagnostics use these forms, followed as applicable by the shown usage and `For more information, try '--help'.`:

```text
error: unrecognized subcommand 'unknown-command'

Usage: executable [COMMAND]

For more information, try '--help'.
```

```text
error: unexpected argument '--unknown-flag' found

Usage: executable [COMMAND]

For more information, try '--help'.
```

A top-level unexpected option does not receive a pass-as-value tip: `executable --unknown-flag` produces exactly the unexpected-argument diagnostic shown above, including its usage and help hint. An unexpected option within a subcommand can additionally suggest `tip: to pass 'TOKEN' as a value, use '-- TOKEN'`, as in the `init --unknown --help` diagnostic in Spec 2. `--` ends option parsing, so a later dash-prefixed token is positional. A value beginning with `-` is not consumed from a separate token; an `--option=value` form can represent it. Short options may be clustered (`-od` means `-o -d`, so it errors because `-d` then lacks a value). Both `-d VALUE`, `-d=VALUE`, `--dest-dir VALUE`, and `--dest-dir=VALUE` are accepted. `--dest-dir` cannot occur twice.

Missing values use the canonical long option and its declared metavariable, even when a short-option cluster triggered the error. Both `build --dest-dir` and `build -od` exit 2, write nothing to stdout, and write exactly:

```text
error: a value is required for '--dest-dir <dest-dir>' but none was supplied

For more information, try '--help'.
```

Likewise, `serve --port -- BOOK_DIR` exits 2 and writes exactly this stderr, because `--` is not consumed as the port value:

```text
error: a value is required for '--port <port>' but none was supplied

For more information, try '--help'.
```

The enumerations are case-sensitive: completion shells are exactly `bash`, `elvish`, `fish`, `powershell`, and `zsh`; ignore-file choices are `none` and `git`; watcher choices are `poll` and `native`. An invalid choice says `invalid value 'VALUE'`, identifies the option or argument, and lists possible values. Omitting the completion shell says that required argument `<SHELL>` was not provided and shows `Usage: executable completions <SHELL>`.

In particular, `completions invalid-shell` produces exactly this stderr:

```text
error: invalid value 'invalid-shell' for '<SHELL>'
  [possible values: bash, elvish, fish, powershell, zsh]

For more information, try '--help'.
```

and `completions` with no shell produces exactly:

```text
error: the following required arguments were not provided:
  <SHELL>

Usage: executable completions <SHELL>

For more information, try '--help'.
```

## Spec 4

Subcommand options and their help-visible spellings are:

- `init [dir]`: `--theme`, `--force`, `--title <title>`, and `--ignore <ignore>`.
- `build [dir]`: `-d, --dest-dir <dest-dir>` and `-o, --open`.
- `test [dir]`: `-c, --chapter <chapter>`, repeatable `-L, --library-path <dir>` (each value may also be comma-separated), and `-d, --dest-dir <dest-dir>`.
- `clean [dir]`: `-d, --dest-dir <dest-dir>`.
- `watch [dir]`: `-d, --dest-dir <dest-dir>`, `-o, --open`, and `--watcher <watcher>` with default `poll`.
- `serve [dir]`: the watch options plus `-n, --hostname <hostname>` (default `localhost`) and `-p, --port <port>` (default `3000`).

The `init` help includes `Arguments:` and says `[dir]` is the directory in which to create the book. Build/test/clean/watch/serve say it is the root directory. The clean help description is `Deletes a built book`; completions is `Generate shell completions for your shell to stdout`; build is `Builds a book from its markdown files`; test is `Tests that a book's Rust code samples compile`. The clean help explains that relative destination paths are relative to the book root and the fallback is `build.build-dir` or `./book`.

Ignoring only terminal line wrapping, clean help is:

```text
Deletes a built book

Usage: executable clean [OPTIONS] [dir]

Arguments:
  [dir]  Root directory for the book
         (Defaults to the current directory when omitted)

Options:
  -d, --dest-dir <dest-dir>  Output directory for the book
                             Relative paths are interpreted relative to the book's root directory.
                             If omitted, mdBook uses build.build-dir from book.toml or defaults to
                             `./book`.
  -h, --help                 Print help
  -V, --version              Print version
```

## Spec 5

Each book root may contain `book.toml` and has a source directory. Defaults, even if `book.toml` is absent, are: source `src`, output `book`, language `en`, left-to-right text, Rust edition `2015`, create missing chapters enabled, default preprocessors enabled, and the HTML renderer enabled. A missing `book.toml` is not itself an error; building succeeds if `src/SUMMARY.md` exists. An absent source directory or `SUMMARY.md`, including under an empty or nonexistent book root, is an operational error with exit 101 and no stdout. Its stderr consists of timestamped logger lines whose error text is `Error: Couldn't open SUMMARY.md in "ABSOLUTE_SOURCE_DIRECTORY" directory` followed by `\tCaused By: No such file or directory (os error 2)`. This same logger form is used by `clean` when the selected root lacks the summary.

Relative filesystem paths in configuration are relative to the book root except executable tokens in custom renderer and preprocessor `command` values, whose distinct resolution rules are specified in Specs 33 and 34. A CLI `[dir]` selects a different root, and can be relative, absolute, `.`, nested, or contain spaces. `--dest-dir` has highest precedence, then environment configuration, then `build.build-dir`, then `book`; for build and rendering commands a relative destination is resolved against the selected book root, including `../` paths, while an absolute destination is used unchanged. `clean` has the distinct relative-CLI behavior specified in Spec 35.

## Spec 6

`book.toml` is parsed as TOML. The supported general data is:

```toml
[book]
title = "..."                 # optional string
authors = ["...", "..."]     # array of strings
description = "..."           # optional string
src = "src"                   # path, default src
language = "en"               # default en
text-direction = "ltr"        # ltr or rtl, optional

[rust]
edition = "2015"              # 2015, 2018, 2021, or 2024

[build]
build-dir = "book"
create-missing = true
use-default-preprocessors = true
extra-watch-dirs = []
```

Unknown keys do not fail a build. Known values of the wrong type either fail during configuration loading when essential (for example integer `book.title`, non-array `authors`, or non-path `build-dir`) or log an error and use the default when the HTML option can be recovered. Every essential type failure is wrapped by the timestamped logger text `Error: Invalid configuration file`; examples then report `invalid type: integer \`42\`, expected a string` with `in \`title\``, `invalid type: string "one", expected a sequence` with `in \`authors\``, or `invalid type: integer \`42\`, expected path string` with `in \`build-dir\``. A string supplied for boolean `output.html.no-section-label` succeeds but logs `Error: Parsing configuration [output.html]`, `\tCaused By: Couldn't deserialize the value`, and `\tCaused By: invalid type: string "yes", expected a boolean`, followed by `in \`no-section-label\``; this error group occurs once while loading and once when rendering.

Invalid TOML syntax exits 101. For `[book` the timestamped cause chain contains the exact strings `Error: Invalid configuration file`, `\tCaused By: TOML parse error at line 1, column 6`, and `unclosed table, expected \`]\``, together with the source line and caret. A non-table top-level value such as `preprocessor=3` exits 101 with `Error: failed to get preprocessor table config: Couldn't deserialize the value`; `output=3` analogously says `Error: failed to get output table config: Couldn't deserialize the value`.

A neighboring deprecated `book.json` does not replace TOML. Before normal build logs it emits five timestamped warnings, in this order: `It appears you are still using book.json for configuration.`, `This format is no longer used, so you should migrate to the`, `book.toml format.`, `Check the user guide for migration information:`, and a tab followed by `https://rust-lang.github.io/mdBook/format/config.html`.

## Spec 7

Environment variables beginning `MDBOOK_` override the loaded configuration. Remove the prefix; lowercase the rest; interpret `__` as a nested-table separator and a single `_` as `-`. Thus, when supplied individually, `MDBOOK_BOOK__TITLE` maps to `book.title` and `MDBOOK_BUILD__BUILD_DIR` maps to `build.build-dir`. First parse an environment value as JSON; if JSON parsing fails, use the raw string. A variable naming a table may provide an entire JSON object, such as `MDBOOK_BOOK={"title":"JSON title","language":"fr"}`. Environment values override TOML; explicit CLI options override environment values.

Environment override insertion order is observable when a whole-table object and a later nested override are combined. With `MDBOOK_BOOK={"title":"JSON title","language":"fr"}` inserted before `MDBOOK_BUILD__BUILD_DIR="env-out"`, the book object applies but the later build-directory variable is ignored: the HTML uses title `JSON title` and language `fr` but is written to the default `book/`, not `env-out/`. Inserting the build-directory variable before the whole-book object applies both and writes to `env-out/`.

## Spec 8

`init` creates the selected root and missing parent directories, then creates directories `src/` and `book/` and a UTF-8 `book.toml`. With `--force` and no title, the stable generated content is:

```toml
[book]
authors = ["AUTHOR"]
language = "en"
src = "src"
```

`AUTHOR` is the available Git user identity; if none is available the array is exactly `authors = []`. All other shown lines and ordering are required. If `--title VALUE` was explicitly supplied, append `title = "VALUE"`, producing valid TOML with exact round-tripping of empty strings, quotes, backslashes, embedded newlines, long text, and Unicode. No title key is emitted when an omitted or interactively whitespace-only title resolves to no title.

When there is no existing `src/SUMMARY.md`, write exactly:

```markdown
# Summary

- [Chapter 1](./chapter_1.md)
```

including the final newline, and write exactly `# Chapter 1\n` to `src/chapter_1.md`. Successful init stdout ends with a blank line and `All done, no errors...\n`; with `--force` it performs no confirmation prompts. Repeating forced initialization is allowed and leaves a valid scaffold. Existing unrelated files must not be deleted. Creating stub content also emits this progress line to stderr (an actual local timestamp prefixes it): `YYYY-MM-DD HH:MM:SS [INFO] (mdbook_driver::init): Creating a new book with stub content`.

## Spec 9

Without `--force`, init interacts on stdout/stdin in this order when values were not supplied:

```text

Do you want a .gitignore to be created? (y/n)
What title would you like to give the book? 

All done, no errors...
```

Responses `y`, `Y`, `yes`, and `Yes` mean yes; other/no responses mean no. Closed stdin chooses defaults and still succeeds. `--ignore git` or affirmative input creates `.gitignore` containing exactly `book\n`; `--ignore none` or negative input does not create it. An explicit `--title ""` differs from omission and creates `title = ""`.

If an existing valid `src/SUMMARY.md` is present, preserve it, do not create the default `chapter_1.md`, and create every missing linked chapter (including nested paths, prefix/suffix chapters) with content `# TITLE\n`, using its summary title. Invalid summary syntax during init exits 101 and reports `Summary parsing failed` and `The BookBuilder should always create a valid book`. Existing source files are not overwritten. A path component such as `src` or `book` that is a regular file causes exit 101 and must not overwrite the file. For either collision, stdout is empty and stderr is exactly three timestamped logger lines in this order, with no additional plain error line: the `mdbook_driver::init` INFO line from Spec 8; `[ERROR] (mdbook_core::utils): Error: Unable to create directory structure`; and `[ERROR] (mdbook_core::utils): \tCaused By: File exists (os error 17)`.

## Spec 10

`init --theme` copies a usable built-in theme into `theme/` and prints `\nCopying the default theme to ABSOLUTE_THEME_PATH\n` before the final success text. The copied set contains at least:

```text
theme/index.hbs
theme/book.js
theme/highlight.js
theme/highlight.css
theme/css/chrome.css
theme/css/general.css
theme/css/print.css
theme/css/variables.css
theme/favicon.png
theme/favicon.svg
theme/fonts/fonts.css
theme/fonts/OPEN-SANS-LICENSE.txt
theme/fonts/SOURCE-CODE-PRO-LICENSE.txt
```

and at least ten `.woff2` font files, including Open Sans and Source Code Pro names. These are real, nonempty assets: each principal CSS file is over 100 bytes, `index.hbs` is over 500 bytes and contains `<!DOCTYPE HTML>`, and `book.js` is over 1000 bytes and contains `'use strict';` and `playground_text`. If copying could overwrite an existing theme and `--force` is absent, print `This could potentially overwrite files already present in that directory.`, ask `Are you sure you want to continue? (y/n) `, and honor the response. Declining preserves existing files and adds no theme files; accepting copies the set. `--force` skips that prompt.

When ordinary interactive init and this overwrite interaction are combined, the theme interaction comes first for either a yes or no response: stdout prints the blank line and `Copying the default theme to ABSOLUTE_THEME_PATH`, the overwrite warning, a blank line, `Are you sure you want to continue? (y/n) `, then the gitignore and title prompts from Spec 9, and finally the success text.

## Spec 11

`SUMMARY.md` determines all chapters and ordering. Its recognized forms are:

- An optional heading such as `# Summary`, ignored as a book item.
- Root-level links before the first list item are unnumbered prefix chapters.
- Root list items `- [Title](path.md)`, `* [Title](path.md)`, or ordered-list forms such as `1. [Title](path.md)`, `2. ...`, and `3. ...` are numbered chapters. The written ordered markers do not replace mdBook's own continuous chapter numbering. Indented list items are children; arbitrary depth, blank lines, and mixing `-`/`*` are accepted.
- Root-level links after numbered chapters are unnumbered suffix chapters when a blank line separates the link from the preceding list. Without that blank line, as in a final `- [Two](two.md)` immediately followed by `[End](end.md)`, the latter is not recognized as a suffix chapter and no `end.html` page is emitted.
- A link with an empty destination, `- [Draft title]()`, is a draft: it participates in numbering/TOC hierarchy but has no source/output page.
- A level-one heading between items is a part title, displayed in the TOC but not numbered or linked.
- A line containing at least three dashes and nothing else is a separator/spacer.
- HTML comments are ignored. In TOC output, inline emphasis and code delimiters in link titles are flattened to contiguous plain text rather than emitted as `<em>` or `<code>`. For example, a title containing Markdown emphasis around `Italic` followed by inline code `code` produces the TOC text `Italic code`; escaped emphasis/code punctuation remains literal, while an escaped tag is HTML-escaped as `&lt;escaped tag&gt;`.

Chapter numbering is continuous across parts. Top-level numbered chapters are `1.`, `2.`, etc.; children append components (`2.1.`, `2.1.1.`). Prefixes, suffixes, parts, and separators do not consume numbers. Source paths preserve subdirectories and punctuation (`-`, `_`, multiple dots), and `.md` becomes `.html` in HTML output. Unicode and very long titles are preserved.

## Spec 12

Every non-draft source path in `SUMMARY.md` must be unique across prefix, numbered, nested, and suffix items; duplicates exit 101 with a timestamped `Error: Summary parsing failed for file="ABSOLUTE_SUMMARY_PATH"` wrapper followed by `\tCaused By: Duplicate file in SUMMARY.md: "PATH"`. Absolute source paths are rejected with `Chapters are always inside a book`. Relative paths containing `..` are accepted and read relative to the source directory. A malformed nested item which is not solely a chapter hyperlink fails with a location-bearing summary parse error and text `The link items for nested chapters must only contain a hyperlink`. Empty `SUMMARY.md` is valid and builds an empty book.

On load, missing linked files are created when `build.create-missing` is true (the default), including parent directories. Each created file contains `# TITLE\n`; it is then rendered as an otherwise empty chapter. If `create-missing = false`, fail with exit 101 and timestamped lines containing `Error: Chapter file not found, PATH` and `\tCaused By: No such file or directory (os error 2)`. Invalid UTF-8 in a chapter fails with exit 101 and a timestamped `Error: Unable to read "TITLE" (ABSOLUTE_CHAPTER_PATH)` followed by `\tCaused By: stream did not contain valid UTF-8`. A leading UTF-8 BOM is consumed rather than rendered.

## Spec 13

`build` first loads the book, logs `Book building has started` and `Running the NAME backend` to stderr, runs preprocessors, and renders all configured backends. A successful HTML render also logs `HTML book written to` followed by its destination. It exits 0 on success and 101 on an operational/configuration/rendering failure. `--open` performs the build and attempts to open the resulting index using the environment's browser facility; browser failure must not prevent the build artifact.

Before rendering, the selected renderer destination is created and stale renderer output is replaced so builds are deterministic and idempotent. A rebuild reflects changed source. The source hierarchy is preserved in output. Every non-Markdown file under the source tree (images, JPEGs, snippets, arbitrary assets, nested files, and custom CSS/JS) is recursively copied with content unchanged. Markdown files listed as real chapters are rendered rather than blindly copied; unlisted Markdown files are not chapter pages. A `.nojekyll` file is created in HTML output.

`print.md` is reserved for the HTML renderer because it collides with `print.html`; a chapter using it fails with `print.md is reserved for internal use`. An output destination that is an existing regular file fails.

## Spec 14

Renderer selection is controlled by `[output.NAME]`. With no output tables, use built-in HTML. An explicitly empty `[output.html]` also enables HTML; `[output.markdown]` enables the built-in Markdown renderer. Any other name is a custom renderer. If exactly one renderer is enabled, it writes directly to the selected build directory. If multiple are enabled, each writes to `BUILD_DIR/NAME/` (for example `book/html`, `book/markdown`, `book/custom1`). Log every enabled backend. `--dest-dir` changes the build-directory root but not this single-versus-multiple layout.

## Spec 15

The built-in HTML renderer creates one complete UTF-8 HTML document for each real chapter. Files begin `<!DOCTYPE HTML>\n<html lang="LANG"`; normal pages have a `<head>`, UTF-8 charset, viewport/meta information, linked assets, a `<body>`, sidebar/menu/search UI, exactly one chapter-content `<main>`, and page-navigation `<nav>` elements. Book title appears in `<h1 class="menu-title">`. A chapter page `<title>` is `CHAPTER TITLE - BOOK TITLE`; the initial index uses the book title where appropriate. Description becomes `<meta name="description" content="DESCRIPTION">`.

`book.language` supplies `<html lang="...">`. Arabic (`ar`), Hebrew (`he`), Persian (`fa`), and Urdu (`ur`) imply `dir="rtl"`; otherwise direction is `ltr`. Explicit `book.text-direction` overrides inference.

The first real chapter is also emitted as root `index.html`, even if drafts or non-chapter elements precede it. A source chapter named `README.md` is instead converted by the index preprocessor to `index.md`/`index.html` in its own directory, and no `README.html` is produced. If no chapters exist, still create a structurally valid substantial `print.html`, TOC, assets, and output directory.

## Spec 16

All real chapters form a depth-first linear navigation sequence, including prefix and suffix pages. The first has no previous link, the last has no next link, and middle pages have both. Links use output-relative paths appropriate to the current page. The generated page contains mobile navigation inside `nav.nav-wrapper` and wide navigation inside `nav.nav-wide-wrapper`; links to the previous chapter use `rel="prev"`, while links to the next chapter use the two-token attribute `rel="next prefetch"`, and both use correct `href`s.

`toc.js` contains the complete table-of-contents HTML for JavaScript insertion and must not put `target="_parent"` on its links. `toc.html` is the no-JavaScript iframe fallback; every chapter link there uses `target="_parent"`, and its fixed document wrapper starts with `<!DOCTYPE HTML>`, has `<html lang="LANG" class="light" dir="DIRECTION">`, a UTF-8/noindex head with default stylesheet links, `<body class="sidebar-iframe-inner">`, and a single `<ol class="chapter">`.

In addition to assigning the generated `innerHTML`, `toc.js` defines the `MDBookSidebarScrollbox` custom element and uses `tagName` checks and `addEventListener` for link navigation behavior.

## Spec 17

TOC item serialization is stable and compact. A numbered real chapter is:

```html
<li class="chapter-item expanded "><a href="ch1.html" target="_parent"><strong aria-hidden="true">1.</strong> Chapter 1</a></li>
```

In `toc.js`, omit only the ` target="_parent"` portion. Unnumbered prefix/suffix links use `class="chapter-item expanded affix "` and omit `<strong>`. A draft uses `<div>` instead of `<a>` while retaining its number. A part title is `<li class="chapter-item expanded affix "><li class="part-title">TITLE</li>`. A separator is `<li class="chapter-item expanded affix "><li class="spacer"></li>`. Children immediately follow their parent inside `<li><ol class="section">...</ol></li>`. With `output.html.no-section-label = true`, omit every numeric `<strong>` while retaining chapter text and links.

The fallback document surrounding that compact `<ol>` uses this exact fixed layout, substituting language, direction, and generated items:

```html
<!DOCTYPE HTML>
<html lang="LANG" class="light" dir="DIRECTION">
    <head>
        <!-- sidebar iframe generated using mdBook

        This is a frame, and not included directly in the page, to control the total size of the
        book. The TOC contains an entry for each page, so if each page includes a copy of the TOC,
        the total size of the page becomes O(n**2).

        The frame is only used as a fallback when JS is turned off. When it's on, the sidebar is
        instead added to the main page by `toc.js` instead. The JavaScript mode is better
        because, when running in a `file:///` URL, the iframed page would not be Same-Origin as
        the rest of the page, so the sidebar and the main page theme would fall out of sync.
        -->
        <meta charset="UTF-8">
        <meta name="robots" content="noindex">
        <!-- Custom HTML head -->
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="theme-color" content="#ffffff">
        <link rel="stylesheet" href="css/variables.css">
        <link rel="stylesheet" href="css/general.css">
        <link rel="stylesheet" href="css/chrome.css">
        <link rel="stylesheet" href="css/print.css" media="print">
        <!-- Fonts -->
        <link rel="stylesheet" href="FontAwesome/css/font-awesome.css">
        <link rel="stylesheet" href="fonts/fonts.css">
        <!-- Custom theme stylesheets -->
    </head>
    <body class="sidebar-iframe-inner">
        <ol class="chapter">GENERATED_ITEMS_WITH_NO_ADDED_NEWLINES</ol>
    </body>
</html>
```

## Spec 18

The default HTML build installs usable, nontrivial static assets at these paths:

```text
css/general.css              css/chrome.css
css/print.css                css/variables.css
book.js                      highlight.js
clipboard.min.js             toc.js
toc.html                     404.html
favicon.png                  favicon.svg
highlight.css                tomorrow-night.css
ayu-highlight.css            .nojekyll
fonts/fonts.css              fonts/*.woff2
FontAwesome/css/font-awesome.css
FontAwesome/fonts/*
```

With search enabled (default), also create `searcher.js`, `elasticlunr.min.js`, `mark.min.js`, and `searchindex.js`. CSS and JS are actual usable text, not empty placeholders: `css/chrome.css` starts with `/* CSS for UI elements`, `css/variables.css` contains `:root {\n    --sidebar-target-width`, general/theme CSS is over 100 bytes, `book.js` is over 1000 bytes, and `highlight.js` is over 10000 bytes. HTML links all corresponding assets by output-relative URLs, with `css/print.css` marked `media="print"`.

## Spec 19

The Markdown-to-HTML subset includes paragraphs; ATX headings levels 1 through 6; unordered and ordered lists with arbitrary nesting; emphasis (`*x*`/`_x_` to `<em>`); strong emphasis (`**x**` to `<strong>`); nesting of emphasis, links, and inline code; inline code to `<code>`; fenced code blocks; blockquotes including nested paragraphs/lists/code; horizontal rules; hard line breaks from two trailing spaces; inline links, reference links, shortcut references and autolinks; images with alt text and optional title; and raw inline/block HTML passthrough. HTML special characters in ordinary Markdown text are escaped. Malformed but non-structural Markdown is rendered best-effort and does not crash. Unicode, emoji, long lines/files, empty files, whitespace-only files, and deeply nested lists are preserved.

Relative Markdown links ending `.md` become `.html`, retaining fragments. This syntactic link rewrite does not special-case the filename `README.md`: an ordinary `[read](README.md#top)` link becomes `README.html#top`. The separate index-preprocessor behavior for an actual chapter whose source path is `README.md` is specified in Spec 15. HTTP, HTTPS, FTP, mailto, and arbitrary URI schemes remain unchanged. The same `.md` conversion applies inside raw HTML `<a href>` and `<img src>` attributes: `<a href="README.md#top">` becomes `<a href="README.html#top">` and `<img src="images/info.md">` becomes `<img src="images/info.html">`, while external schemes remain unchanged. Images and links retain correct paths from nested output documents.

## Spec 20

Every rendered Markdown heading gets a linkable, unique ID and this shape:

```html
<h2 id="sub-heading"><a class="header" href="#sub-heading">Sub Heading</a></h2>
```

Default IDs lowercase textual heading content, replace runs of spaces with `-`, remove unsafe punctuation/markup such as backticks and angle brackets, preserve meaningful Unicode, and disambiguate repeated IDs by suffixing. Heading attributes at the end of the heading are consumed rather than displayed: `{#custom-id}` sets the ID; `{.class1 .class2}` adds classes; both may be combined with optional spaces as `{ #both .class1 .class2 }`.

Fenced blocks render as `<pre><code class="language-LANG ATTRS">CONTENT</code></pre>`, HTML-escaping code without truncation. The info string accepts comma-, space-, or tab-separated attributes and normalizes commas to spaces; languages such as Rust, Python, JavaScript, and text remain visible in the class. Empty and whitespace-only fenced blocks still produce code elements.

## Spec 21

Enable these Markdown extensions:

- `~~text~~` becomes `<del>text</del>` and allows nested emphasis.
- Pipe tables become `<table><thead>...<tbody>...`; alignment markers apply `style="text-align: left|center|right"` to header/data cells; empty cells and escaped pipes inside code are retained. Every table, independently, is wrapped directly in `<div class="table-wrapper">`.
- Task list markers `[ ]`, `[x]`, and `[X]` become checkbox inputs serialized beginning `<input disabled="" type="checkbox"`; completed inputs also contain `checked=""`. Nested task lists work.
- If `output.html.smart-punctuation = true`, contextual straight double/single quotes become `“”`/`‘’`, apostrophes become `’`, `---` becomes `—`, `--` becomes `–`, and `...` becomes `…`. It defaults false. Deprecated `curly-quotes` acts as the alias but emits `The output.html.curly-quotes field has been renamed to output.html.smart-punctuation.` followed by `Use the new name in book.toml to remove this warning.`

## Spec 22

Footnote syntax `[^name]` and `[^name]: definition` is supported in paragraphs, tables, lists, nested lists, and within another footnote. References are numbered by first-reference order. A reference has exactly the conceptual form `<sup class="footnote-reference" id="fr-NAME-K"><a href="#footnote-NAME">NUMBER</a></sup>`, where `K` counts references to that definition. At the end of `<main>`, emit `<hr>` and `<ol class="footnote-definition">`; each used definition is `<li id="footnote-NAME">...</li>`.

Each definition gets backlinks in reference order: the first text is `↩`, then `↩2`, `↩3`, etc., linking to `#fr-NAME-K`. If a definition ends in a paragraph, backlinks go inside that paragraph; if it ends in a code block/list, backlinks follow that block before `</li>`. Unused definitions are omitted and warn with the exact detailed form ``footnote `NAME` in `PATH` is defined but not referenced``, including the inner backticks. Duplicate definitions warn `defined multiple times - not updating to new definition`, use only the first definition, but retain all references/backlinks. Footnote names and generated attributes are HTML-escaped, including `<`, `>`, `"`, `'`, backslash, and `&`; an apostrophe is serialized specifically as the decimal entity `&#39;`. Empty definitions do not crash.

## Spec 23

Rust fenced-code behavior recognizes attributes `ignore`, `no_run`, `should_panic`, `compile_fail`, `editable`, `noplayground`, `mdbook-runnable`, and `edition2015`/`edition2018`/`edition2021`/`edition2024`. Rust blocks use class `language-rust`; edition selection appears as an edition class where applicable. With playground enabled, runnable Rust blocks have `class="playground"` around the code UI. `output.html.playground` accepts `editable` (default false), `copyable` (true), and `runnable` (true), reflected in page JavaScript such as `window.playground_copyable = true;` and whether run/edit UI is offered. With `editable = false`, do not emit `window.playground_editable = true;`.

In displayed Rust, a line beginning `# ` is hidden initially but retained in HTML using `class="boring"`; `##` escapes a literal leading `#`. Per-language hide prefixes can be configured under `[output.html.code.hidelines]`, and a fence attribute `hidelines=PREFIX` overrides it.

## Spec 24

The default `links` preprocessor expands directives relative to the containing source file:

- `{{#include path}}` inserts the entire file.
- `{{#include path:N}}` inserts one 1-based line; `path::END`, `path:START:`, and `path:START:END` select inclusive ranges.
- `{{#include path:anchor}}` inserts lines between matching `ANCHOR: anchor` and `ANCHOR_END: anchor` marker lines, excluding marker lines. Anchor names contain word characters, `_`, or `-`.
- `{{#playground path attributes...}}` produces a fenced `rust` block containing the file and supplied attributes.
- `{{#rustdoc_include path:range-or-anchor}}` includes the complete Rust file but prefixes non-selected lines with `# `, so selected lines display while all lines remain testable.

Expansion is recursive and works from nested chapters. Guard recursion/depth: a cyclic or excessively deep include does not fail the build and logs one timestamped ERROR line of the exact form `Stack depth exceeded in CHAPTER_FILENAME. Check for cyclic includes`. `CHAPTER_FILENAME` is the source filename of the book chapter whose content is being expanded, not the included file in which the depth limit is reached. Thus, when `chapter_1.md` includes `recursive.md` and `recursive.md` includes itself, the line is exactly `Stack depth exceeded in chapter_1.md. Check for cyclic includes`. It leaves finite/truncated repeated output (a direct cycle expands far enough to contain at least five repetitions before stopping). A missing include also does not fail: log `Error updating "DIRECTIVE"`, `Could not read file for link DIRECTIVE`, and the file error, and preserve the directive literally. Setting `[build] use-default-preprocessors = false` disables both `links` and `index`; explicitly configuring `[preprocessor.links]` or `[preprocessor.index]` enables that named built-in regardless.

## Spec 25

The HTML `print.html` is one complete document whose `<main>` concatenates every real chapter in reading order, placing `<div style="break-before: page; page-break-before: always;"></div>` boundaries between chapters. It contains `<meta name="robots" content="noindex">`; normal chapter/index pages do not.

When combining chapters for print, local fragment links become `CHAPTER_OUTPUT.html#fragment`; `.md` links become corresponding `.html`; nested links are rebased to the combined page's output-root perspective while preserving meaningful `..` segments. Images are similarly rebased. External schemes are unchanged.

When `output.html.input-404` is unset, create a default `404.html` with a valid document, `<title>` mentioning `Page not found`, a `<main>`/`<h1>` mentioning 404, and visible text `Document not found (404)`. When `output.html.input-404 = "missing.md"`, render that source as `missing.html` and do not create `404.html`; the configured source path is converted from `.md` to `.html` rather than renamed to `404.html`. If `output.html.site-url = "/docs/"` is also configured, the resulting `missing.html` head includes `<base href="/docs/">`.

## Spec 26

HTML search is enabled by default. `searchindex.js` has exactly this outer protocol:

```javascript
window.search = Object.assign(window.search, JSON.parse('ESCAPED_JSON'));
```

The JSON object contains `doc_urls`, `index`, `results_options`, and `search_options`. `index.fields` is `['title','body','breadcrumbs']`; its `documentStore.docs` maps string IDs to `{id,title,body,breadcrumbs}`. A basic introduction headed `Introduction`, in the Introduction chapter, with body `Welcome to the book.` produces title `Introduction`, breadcrumbs `Introduction » Introduction`, and that body. Documents split at headings through `heading-split-level` (default 3), and URLs use chapter HTML plus the heading anchor. Drafts are omitted. Text strips HTML tags but includes ordinary text and code. Unicode and JSON-special characters/backslashes round-trip. Terms longer than 80 characters remain in stored body but are excluded from the inverted index; length 80 is indexed.

`[output.html.search]` accepts `enable`, `limit-results` (30), `teaser-word-count` (30), `use-boolean-and` (false), `boost-title` (2), `boost-hierarchy` (1), `boost-paragraph` (1), `expand` (true), `heading-split-level` (3), and `copy-js` (true). Map these to `results_options.limit_results` and `search_options` fields: boolean mode is `AND` or `OR`; field boosts are title/breadcrumbs/body. `[output.html.search.chapter]` applies recursive per-source-path/directory `enable` overrides, with a more specific path winning. A configured key matching no chapter/directory exits 101 with a rendering-failure cause exactly shaped ``[output.html.search.chapter] key `KEY` does not match any chapter paths``.

## Spec 27

`[output.html]` additionally supports:

- `default-theme` (default `light`) and `preferred-dark-theme` (default `navy`), emitted as `const default_light_theme = "...";` and `const default_dark_theme = "...";`; the HTML's initial class contains the light theme.
- `git-repository-url` and optional `git-repository-icon` (default `fa-github`), creating a menu link titled and aria-labeled `Git repository` with `<i class="fa ICON">`.
- `edit-url-template`, creating a `Suggest an edit` link per chapter. Replace `{path}` with the path from book root to source, including the configured source directory (for example `src/ch1.md` or `guide/src2/README.md`).
- `mathjax-support`, which when true includes a script whose URL contains `MathJax.js`.
- `cname`, written to output file `CNAME` as the configured string followed by an added newline. For `cname = "docs.example.test"`, the file's exact bytes are `docs.example.test\n`.
- `[output.html.fold] enable` and `level`, used by sidebar folding.

Book metadata, themes, Unicode, and special characters must be HTML-escaped in attributes/text where required while remaining readable.

## Spec 28

The HTML theme is the union of built-in files and optional overrides. The theme directory defaults to `BOOK_ROOT/theme` and can be set by `output.html.theme`; a configured nonexistent directory exits 101 with the rendering-failure cause `theme dir ABSOLUTE_PATH does not exist`. Any supplied file replaces the built-in file byte-for-byte, including an empty file. Recognized overrides include `index.hbs`, `head.hbs`, `header.hbs`, `book.js`, `highlight.js`, `highlight.css`, `tomorrow-night.css`, `ayu-highlight.css`, `favicon.png`, `favicon.svg`, `css/{general,chrome,print,variables}.css`, and `fonts/**`. Missing override files fall back independently to built-ins. If only one favicon format is present in the custom theme, output/link only that format.

`head.hbs` is inserted in `<head>` and `header.hbs` above page content. `index.hbs` is a Handlebars-like template with HTML-escaped `{{title}}`, `{{book_title}}`, `{{chapter_title}}`, `{{description}}`, `{{path}}`, and `{{path_to_root}}`, and unescaped `{{{content}}}`. Malformed template syntax fails with `Template error` / `invalid handlebars syntax`. Template data uses `path` relative to source root (such as `ch1.md`).

## Spec 29

The template helper `{{theme_option "TEXT"}}` outputs `TEXT` unchanged and HTML-escaped, followed by ` (default)` exactly when `TEXT` and configured `default-theme` compare equal after case folding. Do not trim or otherwise normalize either string; preserve case, Unicode, and whitespace. The implicit configured default is `light`. Unknown and empty strings are valid and simply do not match. Calling with no parameter or a non-string is fatal with `Error: Rendering failed`, `Error rendering "index"`, and `Helper/Decorator theme_option param with name 0 type mismatch for string`.

The standard theme selector provides buttons for Light, Rust, Coal, Navy, and Ayu; a custom template using those five helper calls marks exactly the matching default.

## Spec 30

`output.html.additional-css` and `additional-js` are ordered arrays of paths relative to the book root. Copy every listed file to the same relative path under output, including nested directories and exact bytes; inject stylesheet/script URLs in configuration order. Theme overrides still take precedence only for their recognized built-in path. Custom fonts under `theme/fonts` are copied recursively and their `fonts.css` is linked. Deprecated `copy-fonts = false` suppresses built-in `fonts/fonts.css` and built-in font files and logs a deprecation warning; custom font CSS/files remain usable.

## Spec 31

`[output.html.redirect]` maps an output-root source URL to a target URI. For a removed page without fragment mappings, create the source HTML path and parent directories. It is a small redirect document containing both `<meta http-equiv="refresh" content="0; URL=TARGET">` and `<link rel="canonical" href="TARGET">`. Copy the configured target literally into both elements; do not rebase a relative target for the source page's nesting. Thus a redirect at `deprecated/guide.html` configured with target `guide.html` uses `guide.html`, not `../guide.html`, in both elements. Fragment redirects use JavaScript dispatch when needed. If a redirect source is also an existing real chapter, the build succeeds and the normal rendered chapter page wins; for example, mapping `ch1.html` to `new.html` leaves `ch1.html` as the chapter page rather than a redirect. A simple removed-page mapping such as `old.html = "#section"` is valid and creates a redirect containing that fragment. By contrast, a removed page having only source keys of the form `old.html#old-fragment` and no base `old.html` source mapping is fatal with `only has source paths`.

## Spec 32

The built-in Markdown renderer runs the same configured preprocessors, then writes each real chapter's resulting Markdown, byte-for-byte apart from intentional preprocessor transformations, to the same relative `.md` path in its destination. It preserves Unicode, formatting, large files, empty content, and exact trailing-newline counts; skips drafts; creates nested directories; removes stale destination files before rendering; and is deterministic. The index preprocessor maps `README.md` to `index.md`. When both HTML and Markdown are enabled, outputs are placed in `html/` and `markdown/` subdirectories under the build directory.

## Spec 33

For `[output.NAME]` where `NAME` is not built in, obtain its command from `command`, otherwise default to `mdbook-NAME`. Parse command strings using shell-style quote grouping but execute directly (quoted paths/arguments with spaces remain single arguments). A multi-component relative executable path is relative first to book root. For backward compatibility, if absent there but present relative to that renderer's destination, execute it and warn that destination-relative renderer paths were previously accepted/deprecated and should be relative to book root. A single-component executable is searched on `PATH`; absolute paths are used directly. The renderer's current working directory is its absolute destination, which is created before launch; inherit environment variables such as `RUST_LOG`.

Write one JSON render-context object to its stdin. It contains at least:

```json
{
  "version": "0.5.0-alpha.1",
  "root": "/absolute/book/root",
  "destination": "/absolute/renderer/destination",
  "config": {"book": {"title": "..."}},
  "book": {"sections": []}
}
```

`book.sections` includes every summary item and all chapter content/hierarchy, even large books. A chapter section has the tagged shape `{"Chapter": {"name": TITLE, "content": MARKDOWN, "path": SOURCE_PATH, "source_path": SOURCE_PATH, "number": NUMBER_OR_NULL, "sub_items": [...]}}`; nested chapters occur recursively in `sub_items`. Pass renderer stdout/stderr through to the executable's corresponding streams. Nonzero renderer exit makes build exit 101 and says `Renderer exited with non-zero return code` and `The "NAME" renderer failed`.

A missing required command exits 101 and logs exactly this substantive sentence before the rendering-failure cause: ``The command `COMMAND` wasn't found, is the "NAME" backend installed? If you want to ignore this error when the "NAME" backend is not installed, set `optional = true` in the `[output.NAME]` section of the book.toml configuration file.`` `COMMAND` is the literal configured first command token, or `mdbook-NAME` for the default.

If `optional = true`, a missing command instead succeeds and warns ``The command `COMMAND` for backend `NAME` was not found, but was marked as optional.`` A non-boolean value is fatal with a rendering-failure cause ``expected bool for `output.NAME.optional`: Couldn't deserialize the value``. An empty renderer command is fatal with `Command string was empty`.

## Spec 34

Custom preprocessors are configured by `[preprocessor.NAME]`; `command` overrides default executable `mdbook-NAME`. Parse command strings using the renderer rule for shell-style quote grouping followed by direct execution. Absolute executable paths are used directly and a single-component executable is searched on `PATH`, but, unlike a renderer command, a multi-component relative preprocessor executable such as `./processor.py` is resolved from the mdBook process's current working directory and is not rebased to the book root. Before applying it for renderer `R`, invoke the command with arguments `supports R`; exit 0 means supported and any other exit means skip. An explicit `renderers = ["..."]` also filters it. To apply one, send JSON `[context, book]` on stdin and parse stdout as the replacement `book`. A nonzero apply exit is fatal and its final diagnostic is a timestamped `[ERROR]` logger line identifying `The "NAME" preprocessor exited unsuccessfully` and the exit status. Invalid stdout is fatal with a timestamped `Error: Unable to parse the preprocessed book from "NAME" processor`; invalid text beginning `invalid json` is followed by `\tCaused By: expected value at line 1 column 1`.

An empty custom-preprocessor command succeeds after warning `Unable to create the command for the "NAME" preprocessor, Command string was empty`. A missing executable also succeeds and emits two warnings: `The command wasn't found, is the "NAME" preprocessor installed?` and `\tCommand: COMMAND`, preserving the configured path. Consequently, if `./processor.py`, `./badjson.py`, or `./exit.py` exists only in the selected book root while mdBook is invoked from another directory, that command is not executed: it is handled as missing, the build exits 0, and rendering proceeds without its transformation, invalid output, or nonzero exit.

`before` and `after` arrays define a dependency graph. Execute a deterministic topological order (same-priority names sorted); honor both directions. References to absent preprocessors are ignored after a warning whose direction label is inverted: an absent `MISSING` listed in `preprocessor.NAME.before` warns exactly `preprocessor.NAME.after contains "MISSING", which was not found`, while one listed in `preprocessor.NAME.after` warns exactly `preprocessor.NAME.before contains "MISSING", which was not found`. A cycle exits 101 with `Cyclic dependency detected in preprocessors`.

## Spec 35

`clean` loads the selected book/config, recursively removes the resolved destination and nothing else, then prints a summary to stdout. It preserves `book.toml`, the complete source tree, and unrelated destinations. With a valid book but no destination, it succeeds and prints exactly `Removed 0 files\n`.

Unlike build, a relative CLI `clean --dest-dir` is made absolute against the process current working directory before the selected book root is loaded. Thus, from a parent working directory, `clean -d chosen ROOT` looks for `CWD/chosen`, not `ROOT/chosen`; if only `ROOT/chosen` exists, it succeeds with `Removed 0 files\n` and leaves that directory intact. Absolute CLI destinations remain absolute, while a destination selected from `build.build-dir` remains book-root-relative.

Directory entries contribute their filesystem-reported size. If no regular files exist, the summary counts directories instead of using the zero form. A destination consisting of itself plus two nested empty directories is removed and prints exactly `Removed 3 directories, 12.00KiB total\n` on this interface.

For nonzero files, print `Removed N file[s], SIZE total\n`, singular only for one. Use binary units and exactly two decimals: a 2 MiB file yields `Removed 1 file, 2.00MiB total`, 2 GiB yields `2.00GiB`, and 1 TiB yields `1.00TiB`; ordinary built books report an appropriate `KiB` or larger size. A nonexistent/empty book root that lacks `SUMMARY.md` is an operational error (exit 101, `Couldn't open SUMMARY.md`), rather than being treated as an already-clean book.

## Spec 36

`test` loads the book and runs Rust documentation tests for every real chapter in reading order using an available harness-provided `rustdoc` command. Before each chapter, log `Testing chapter 'TITLE': PATH` (at least title and source filename must appear). With `--chapter QUERY`, select exactly a chapter by title or its relative source path and skip all others. If no match, exit 101 and report `Chapter not found: QUERY`; for `?`, also log skipped chapters.

Rust and unlabelled fenced blocks are test candidates; explicitly non-Rust languages and `ignore` blocks are not. Preserve hidden `# ` lines for compilation. Honor `no_run`, `should_panic`, `compile_fail`, per-block edition attributes, and default `[rust] edition`; accept 2015, 2021, and 2024 behavior. Forward every repeatable/comma-separated `-L` directory to rustdoc. `-d/--dest-dir` is accepted. Chapters with no candidates still log and succeed. Any compilation/runtime/assertion or expected-failure mismatch fails the command with exit 101, passes through rustdoc diagnostics (`FAILED`, error codes/messages, panic/assert values), says `rustdoc returned an error` where applicable, and ends with `One or more tests failed`. A `compile_fail` block that compiles reports: "Test compiled successfully, but it's marked `compile_fail`".

## Spec 37

`completions SHELL` writes a substantial, syntactically valid completion program to stdout and exits 0. It describes every public subcommand and option using public name `mdbook`. Bash output begins `_mdbook() {`, includes `complete -F _mdbook`, and is accepted by `bash -n`. Zsh begins `#compdef mdbook`, contains `_mdbook() {`, `autoload -U is-at-least`, and `case $state in`. Fish begins with `# Print an optspec for argparse to handle cmd's options that are independent of any subcommand.` and defines `__fish_mdbook_global_optspecs`. PowerShell begins (after one blank line) with `using namespace System.Management.Automation`, then `using namespace System.Management.Automation.Language`, and uses `Register-ArgumentCompleter -Native -CommandName 'mdbook'`. Elvish begins with one blank line then `use builtin;`, `use str;`, and defines `edit:completion:arg-completer[mdbook]`.

The first 30 lines are stable. Bash starts exactly as follows:

```bash
_mdbook() {
    local i cur prev opts cmd
    COMPREPLY=()
    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
        cur="$2"
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
    fi
    prev="$3"
    cmd=""
    opts=""

    for i in "${COMP_WORDS[@]:0:COMP_CWORD}"
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="mdbook"
                ;;
            mdbook,build)
                cmd="mdbook__build"
                ;;
            mdbook,clean)
                cmd="mdbook__clean"
                ;;
            mdbook,completions)
                cmd="mdbook__completions"
                ;;
            mdbook,help)
                cmd="mdbook__help"
                ;;
```

Zsh starts exactly as follows:

```zsh
#compdef mdbook

autoload -U is-at-least

_mdbook() {
    typeset -A opt_args
    typeset -a _arguments_options
    local ret=1

    if is-at-least 5.2; then
        _arguments_options=(-s -S -C)
    else
        _arguments_options=(-s -C)
    fi

    local context curcontext="$curcontext" state line
    _arguments "${_arguments_options[@]}" : \
'-h[Print help]' \
'--help[Print help]' \
'-V[Print version]' \
'--version[Print version]' \
":: :_mdbook_commands" \
"*::: :->mdbook" \
&& ret=0
    case $state in
    (mdbook)
        words=($line[1] "${words[@]}")
        (( CURRENT += 1 ))
        curcontext="${curcontext%:*:*}:mdbook-command-$line[1]:"
        case $line[1] in
```

Fish starts exactly as follows; indentation inside functions is a tab:

```fish
# Print an optspec for argparse to handle cmd's options that are independent of any subcommand.
function __fish_mdbook_global_optspecs
	string join \n h/help V/version
end

function __fish_mdbook_needs_command
	# Figure out if the current invocation already has a command.
	set -l cmd (commandline -opc)
	set -e cmd[1]
	argparse -s (__fish_mdbook_global_optspecs) -- $cmd 2>/dev/null
	or return
	if set -q argv[1]
		# Also print the command, so this can be used to figure out what it is.
		echo $argv[1]
		return 1
	end
	return 0
end

function __fish_mdbook_using_subcommand
	set -l cmd (__fish_mdbook_needs_command)
	test -z "$cmd"
	and return 1
	contains -- $cmd[1] $argv
end

complete -c mdbook -n "__fish_mdbook_needs_command" -s h -l help -d 'Print help'
complete -c mdbook -n "__fish_mdbook_needs_command" -s V -l version -d 'Print version'
complete -c mdbook -n "__fish_mdbook_needs_command" -f -a "init" -d 'Creates the boilerplate structure and files for a new book'
complete -c mdbook -n "__fish_mdbook_needs_command" -f -a "build" -d 'Builds a book from its markdown files'
```

PowerShell has an empty first line, then these lines through line 30:

```powershell

using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'mdbook' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'mdbook'
        for ($i = 1; $i -lt $commandElements.Count; $i++) {
            $element = $commandElements[$i]
            if ($element -isnot [StringConstantExpressionAst] -or
                $element.StringConstantType -ne [StringConstantType]::BareWord -or
                $element.Value.StartsWith('-') -or
                $element.Value -eq $wordToComplete) {
                break
        }
        $element.Value
    }) -join ';'

    $completions = @(switch ($command) {
        'mdbook' {
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('-V', '-V ', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('--version', '--version', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('init', 'init', [CompletionResultType]::ParameterValue, 'Creates the boilerplate structure and files for a new book')
            [CompletionResult]::new('build', 'build', [CompletionResultType]::ParameterValue, 'Builds a book from its markdown files')
            [CompletionResult]::new('test', 'test', [CompletionResultType]::ParameterValue, 'Tests that a book''s Rust code samples compile')
```

Elvish also has an empty first line, then:

```elvish

use builtin;
use str;

set edit:completion:arg-completer[mdbook] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'mdbook'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'mdbook'= {
            cand -h 'Print help'
            cand --help 'Print help'
            cand -V 'Print version'
            cand --version 'Print version'
            cand init 'Creates the boilerplate structure and files for a new book'
            cand build 'Builds a book from its markdown files'
            cand test 'Tests that a book''s Rust code samples compile'
            cand clean 'Deletes a built book'
            cand completions 'Generate shell completions for your shell to stdout'
            cand watch 'Watches a book''s files and rebuilds it on changes'
```

Completion help is:

```text
Generate shell completions for your shell to stdout

Usage: executable completions <SHELL>

Arguments:
  <SHELL>  the shell to generate completions for [possible values: bash, elvish, fish, powershell,
           zsh]

Options:
  -h, --help     Print help
  -V, --version  Print version
```

## Spec 38

`watch` does not perform an initial build. It starts watching the source tree, `SUMMARY.md`, `book.toml`, the active theme directory, and every `build.extra-watch-dirs` path, and remains running without creating the book output until a watched change occurs. On content modification, creation, deletion, summary restructuring, or relevant theme/config change, build so output modification time advances and final content is reflected. Coalesce rapid changes without losing the last update. Do not watch the selected build output (prevent loops), and ignore files matched by the book root's `.gitignore`; later relevant changes must still work. Support both `poll` (the default, approximately one-second scanning is acceptable) and `native`. The poll watcher prints a stderr status containing `Watching for changes...`; the native watcher instead prints one containing `Listening for changes...`. Invalid watcher values are argument errors; a missing book fails with the standard summary error.

## Spec 39

`serve` first builds, then performs watch behavior while serving the HTML destination over HTTP. Defaults are `localhost:3000`; `--hostname`, `--port`, `--dest-dir`, `--watcher`, and optional `[dir]` combine normally. Accept valid hostnames, `localhost`, IPv4 addresses, and ports through 65535. Empty/unresolvable hosts, nonnumeric/out-of-range/negative ports, and an already-bound address are nonzero operational failures; invalid ports say `invalid port value`.

Serve `/` and chapter/print/assets with correct output bytes and MIME types: HTML `text/html`, CSS `text/css`, JS containing `text/javascript`, PNG exactly `image/png`. Missing paths return the generated 404 body with HTTP 404. HEAD returns the same status/headers as GET with an empty body. Concurrent requests succeed. Byte range `Range: bytes=0-99` returns 206, exactly 100 bytes, `Content-Range: bytes 0-99/TOTAL`, and `Accept-Ranges: bytes`.

A WebSocket endpoint exists at `/__livereload`; clients can repeatedly connect/disconnect. Served HTML contains client code with `const socket = new WebSocket`. After a watched rebuild, connected clients receive text `reload`. The server remains responsive after malformed/non-UTF-8 request paths. An empty book may serve either its empty index with 200 or generated 404 with 404.

## Spec 40

Operational diagnostics and progress logs go to stderr; user-result text such as help, version, init prompts/success, completion scripts, renderer stdout, and clean summaries goes to stdout. Successful commands exit 0, CLI syntax errors exit 2, and book/config/build/test failures normally exit 101. Errors should form a cause chain with actionable substrings specified above. Required stress behavior includes at least 200 chapters, 50 hierarchy levels/directories, 10,000-line/large Markdown chapters, very long headings and Unicode filenames/content without truncation or crashes. Builds of empty/whitespace chapters and malformed ordinary Markdown succeed, whereas invalid TOML, invalid UTF-8, structural summary errors, unavailable required renderers, renderer/preprocessor failures, and impossible filesystem destinations fail cleanly.
