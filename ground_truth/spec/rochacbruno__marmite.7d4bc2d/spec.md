# Marmite executable behavioral specification

The required artifact is a single runnable file named `executable`. All paths and text are UTF-8 unless stated otherwise. The executable is a static-site generator: it reads a project directory, converts Markdown content to a flat HTML site, optionally scaffolds or manages that project, and optionally serves/watches the generated site. Requirements below are normative; examples clarify the rule rather than limiting it.

## Spec 1

The command-line grammar is:

```text
executable [OPTIONS] <INPUT_FOLDER> [OUTPUT_FOLDER]
```

`INPUT_FOLDER` is always required, including for action flags such as `--shortcodes`. `OUTPUT_FOLDER` defaults to `<INPUT_FOLDER>/site`. Options may appear before, between, or after positional arguments. Recognize `-h/--help`, `-V/--version`, repeatable `-v/--verbose`, `-w/--watch`, `--serve`, `--bind`, `-c/--config`, `--init-templates`, `--start-theme`, `--set-theme`, `--generate-config`, `--init-site`, `--force`, `--shortcodes`, `--show-urls`, `--new`, `-e`, `-p`, and `-t`, plus every configuration override named in Spec 4. Unknown options and malformed option values are command-line errors. A help option takes precedence over otherwise-invalid trailing arguments and exits successfully.

With no arguments, return status 2, write no stdout, and write a diagnostic to stderr containing `error: the following required arguments were not provided:`, `<INPUT_FOLDER>`, and the case-sensitive usage banner `Usage: executable <INPUT_FOLDER> [OUTPUT_FOLDER]`. `--shortcodes` without an input folder follows the same rule. An unknown flag returns status 2 and uses the exact diagnostic form `error: unexpected argument '<flag>' found`; in particular, `--definitely-not-a-flag` produces `error: unexpected argument '--definitely-not-a-flag' found`. Wording such as `invalid option` or `unrecognized arguments` is not equivalent. Invalid numeric values, such as `--pagination invalid`, are errors.

## Spec 2

`--help` must exit 0, write nothing to stderr, terminate with a newline, contain no ANSI escapes when stdout is not a terminal, and write exactly the following text to stdout:

```text
Marmite is the easiest static site generator.

Usage: executable [OPTIONS] <INPUT_FOLDER> [OUTPUT_FOLDER]

Arguments:
  <INPUT_FOLDER>   Input folder containing markdown files
  [OUTPUT_FOLDER]  Output folder to generate the site [default: `input_folder/site`]

Options:
  -v, --verbose...
          Verbosity level (0-4) [default: 0 warn] options: -v: info,-vv: debug,-vvv: trace,-vvvv: trace all
  -w, --watch
          Detect changes and rebuild the site automatically
      --serve
          Serve the site with a built-in HTTP server
      --bind <BIND>
          Address to bind the server [default: 0.0.0.0:8000]
  -c, --config <CONFIG>
          Path to custom configuration file [default: marmite.yaml]
      --init-templates
          Initialize templates in the project
      --start-theme <START_THEME>
          Initialize a theme with templates and static assets
      --set-theme <SET_THEME>
          Download and set a theme from a remote URL or local folder
      --generate-config
          Generate the configuration file
      --init-site
          Init a new site with sample content and default configuration this will overwrite existing files usually you don't need to run this because Marmite can generate a site from any folder with markdown files
      --force
          Force the rebuild of the site even if no changes detected
      --shortcodes
          List all available shortcodes
      --show-urls
          Show all site URLs organized by content type
      --new <NEW>
          Create a new post with the given title and open in the default editor
  -e
          Edit the file in the default editor
  -p
          Set the new content as a page
  -t <TAGS>
          Set the tags for the new content tags are comma separated
      --name <NAME>
          Site name [default: "Home" or value from config file]
      --tagline <TAGLINE>
          Site tagline [default: empty or value from config file]
      --url <URL>
          Site url [default: empty or value from config file]
      --https <HTTPS>
          If protocol is missing in the URL setting, whether to use HTTPS or not [default: false] [possible values: true, false]
      --footer <FOOTER>
          Site footer [default: from '_footer.md' or config file]
      --language <LANGUAGE>
          Site main language 2 letter code [default: "en" or value from config file]
      --pagination <PAGINATION>
          Number of posts per page [default: 10 or value from config file]
      --enable-search <ENABLE_SEARCH>
          Enable search [default: false or from config file] [possible values: true, false]
      --enable-related-content <ENABLE_RELATED_CONTENT>
          Enable backlinks and related content for posts [default: true or from config file] [possible values: true, false]
      --content-path <CONTENT_PATH>
          Path for content subfolder [default: "content" or value from config file] this is the folder where markdown files are stored inside `input_folder` no need to change this if your markdown files are in `input_folder` directly
      --templates-path <TEMPLATES_PATH>
          Path for templates subfolder [default: "templates" or value from config file]
      --static-path <STATIC_PATH>
          Path for static subfolder [default: "static" or value from config file]
      --media-path <MEDIA_PATH>
          Path for media subfolder [default: "media" or value from config file] this path is relative to the folder where your content files are
      --default-date-format <DEFAULT_DATE_FORMAT>
          Default date format [default: "%b %e, %Y" or from config file] see <https://docs.rs/chrono/0.4.19/chrono/format/strftime/index.html>
      --colorscheme <COLORSCHEME>
          Name of the colorscheme to use [default: "default" or from config file] see <https://marmite.blog/getting-started.html#colorschemes>
      --toc <TOC>
          Show Table of Contents in posts [default: false or from config file] this will generate a table of contents for each post [possible values: true, false]
      --json-feed <JSON_FEED>
          Generate JSON Feed [default: false or from config file] [possible values: true, false]
      --show-next-prev-links <SHOW_NEXT_PREV_LINKS>
          Show next and previous links in posts [default: true or from config file] [possible values: true, false]
      --publish-md <PUBLISH_MD>
          Publish markdown source files alongside HTML [default: false or from config file] [possible values: true, false]
      --source-repository <SOURCE_REPOSITORY>
          Source repository URL to link to markdown files [default: None or from config file]
      --image-provider <IMAGE_PROVIDER>
          Image provider for automatic banner image download [default: None or from config file] Available providers: picsum
      --theme <THEME>
          Theme to use for the site [default: from config file or embedded templates]
      --build-sitemap <BUILD_SITEMAP>
          Generate sitemap.xml file [default: true or from config file] [possible values: true, false]
      --publish-urls-json <PUBLISH_URLS_JSON>
          Generate urls.json file [default: true or from config file] [possible values: true, false]
      --enable-shortcodes <ENABLE_SHORTCODES>
          Enable shortcodes processing [default: true or from config file] [possible values: true, false]
      --shortcode-pattern <SHORTCODE_PATTERN>
          Custom shortcode pattern (regex) [default: <!-- \.(\w+)(?:\s+([^-][\s\S]*?))?\s*--> or from config file]
      --skip-image-resize <SKIP_IMAGE_RESIZE>
          Skip image resizing during build [default: false or from config file] Use this for faster development builds when image optimization is not needed [possible values: true, false]
  -h, --help
          Print help
  -V, --version
          Print version
```

## Spec 3

`--version` and `-V` exit 0 and print exactly `marmite 0.2.7\n` to stdout. Normal successful, non-verbose builds write nothing to stdout or stderr unless there is a warning or the selected operation has specified output. `-v`, `-vv`, `-vvv`, and `-vvvv` select increasing info/debug/trace verbosity and successful verbose builds emit some diagnostic output. Operational errors use stderr. A missing input path returns exactly status 1, no stdout, and an error containing `Input folder does not exist: "<supplied-path>"`, including those double quotes. A path that is a file rather than a directory returns status 1 and stderr contains `Unable to create output directory` followed by an OS debug error containing `kind: NotADirectory, message: "Not a directory"`. Never panic or print a language traceback for malformed user content.

## Spec 4

Load YAML configuration from `<INPUT_FOLDER>/marmite.yaml` by default. `--config PATH` selects another file; a relative path is relative to the input folder, while an absolute path is used as-is. A missing default or explicitly selected config is not an error and uses defaults. Malformed YAML or the wrong type for a known field is fatal with status 1 and an stderr message headed `Failed to parse config YAML`. In configuration, the exact text `menu: [unclosed bracket` is parsed as a one-element sequence and then rejected because `menu` requires two-element entries; stderr contains `Error("menu[0]: invalid type: string \"unclosed bracket\", expected a tuple of size 2", line: 1, column: 8)`, not a flow-sequence syntax error. For `pagination: not_a_number`, the parser error is printed through a debug wrapper, so stderr contains `Error("pagination: invalid type: string \"not_a_number\", expected usize", line: 1, column: 13)`; the backslashes before the inner quotation marks are literal output. CLI values override file values.

Recognized fields and override flags are: `name`, `tagline`, `url`, `https`, `footer`, `language`, `pagination`, `enable_search`, `enable_related_content`, `content_path`, `templates_path`, `static_path`, `media_path`, `default_date_format`, `toc`, `json_feed`, `show_next_prev_links`, `publish_md`, `source_repository`, `image_provider`, `theme`, `build_sitemap`, `publish_urls_json`, `enable_shortcodes`, `shortcode_pattern`, and `skip_image_resize`. `--colorscheme VALUE` controls `extra.colorscheme`. Preserve arbitrary configured values under `extra` when there is no colorscheme CLI override. Supplying `--colorscheme` replaces the entire effective `extra` mapping rather than merging into it: with configured `extra.keep: true` and `--colorscheme nord`, the effective `config.extra` in `marmite.json` is exactly `{"colorscheme":"nord"}`, and `keep` is absent. Support `authors`, `streams`, `series`, `menu`, `file_mapping`, `gallery_path`, `gallery_create_thumbnails`, `gallery_thumb_size`, `card_image`, `banner_image`, `logo_image`, `default_author`, `markdown_parser`, and the various taxonomy title strings. Boolean CLI options take explicit `true` or `false`. Defaults include name `Home`, pagination 10, language `en` for rendered HTML, paths `content`, `templates`, `static`, and `media`, date format `%b %e, %Y`, related content/next-prev/shortcodes/sitemap/urls JSON enabled, and search/TOC/JSON-feed/publish-Markdown/image-resize-skip disabled.

If `<input>/<content_path>` exists, recursively read Markdown there. If it does not, recursively read Markdown directly from the input root, including Markdown beneath `static/`, `media/`, and `templates/` rather than excluding those project-control directories. Thus the three `not-content.md` files in those directories are all processed, collide on slug `not-content`, and produce `site/not-content.html`. Theme paths resolve beneath `<input>/<theme>/`; without a theme, custom template/static paths resolve beneath the input root. Custom static and media path flags/configuration must be honored.

## Spec 5

`--generate-config` creates `<INPUT_FOLDER>/marmite.yaml`, reports `Config file generated` on stderr, writes no stdout, and returns 0. It is non-destructive: if the file already exists, leave it byte-for-byte unchanged and report `Config file already exists: <full path>` (the command may still return 0). The generated YAML is valid and contains the complete schema in a deterministic field order. At minimum it contains `name: Home`, `pagination: 10`, `content_path: content`, `templates_path: templates`, `static_path: static`, `menu`, `toc`, and `enable_search`. Apply all CLI overrides to the generated values. Quote date-format and shortcode-pattern strings as YAML strings. An unknown image provider prints `Warning: Unknown image provider '<value>'` and `Available providers: picsum`, and serializes `image_provider: null`.

For a generation using all of these overrides—tagline `My Site`, search/related/TOC/JSON/publish-Markdown true, next-prev false, repository `https://github.com/test/repo`, provider `picsum`, theme `mytheme`, sitemap/urls/shortcodes false—the exact file is:

```yaml
name: Home
tagline: My Site
url: ''
https: null
footer: <div>Powered by <a href="https://github.com/rochacbruno/marmite">Marmite</a> | <small><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC-BY_NC-SA</a></small></div>
language: ''
pagination: 10
pages_title: Pages
tags_title: Tags
tags_content_title: Posts tagged with '$tag'
archives_title: Archive
archives_content_title: Posts from '$year'
streams_title: Streams
streams_content_title: Posts from '$stream'
series_title: Series
series_content_title: Posts from '$series' series
default_author: ''
authors_title: Authors
enable_search: true
enable_related_content: true
search_title: ''
content_path: content
site_path: ''
templates_path: templates
static_path: static
media_path: media
card_image: ''
banner_image: ''
logo_image: ''
default_date_format: '%b %e, %Y'
menu:
- - Tags
  - tags.html
- - Archive
  - archive.html
- - Authors
  - authors.html
extra: null
authors: {}
streams: {}
series: {}
toc: true
json_feed: true
show_next_prev_links: false
publish_md: true
source_repository: https://github.com/test/repo
image_provider: picsum
markdown_parser: null
theme: mytheme
file_mapping: []
enable_shortcodes: false
shortcode_pattern: null
build_sitemap: false
publish_urls_json: false
gallery_path: gallery
gallery_create_thumbnails: true
gallery_thumb_size: 50
skip_image_resize: false
```

## Spec 6

`--init-site INPUT_FOLDER` accepts either a nonexistent path or an existing empty directory, creates it if needed, returns 0, writes no stdout, and reports `Site initialized` on stderr. Refuse a nonempty directory with status 1, `Input folder is not empty`, and no modification to existing data. Create a substantive default `marmite.yaml` (over 100 bytes, with at least `name` and `pagination`), `content/`, `content/media/`, nonempty root `custom.css` and `custom.js`, nonempty `content/about.md`, `content/_404.md`, and exactly one date-prefixed `*-welcome.md`. The welcome post contains `# Welcome to Marmite`, `Edit this content`, `Add more content`, and `Customize your site`. Also create nonempty content fragments `_hero.md`, `_sidebar.example.md`, `_announce.md`, `_comments.md`, `_markdown_header.md`, and `_markdown_footer.md`.

## Spec 7

`--new TITLE` always creates the Markdown file directly in the input-folder root; this action ignores configured `content_path`. In particular, with `content_path: articles`, it does not create or use `<INPUT_FOLDER>/articles`. Its filename is `<current-local-YYYY-MM-DD-HH-MM-SS>-<slug>.md`; `-p` instead creates an undated page named `<slug>.md`. Slugification lowercases, transliterates accents to ASCII, discards punctuation, turns runs of separators/spaces into one hyphen, and trims hyphens; for example `Hello World! Testing: Marmite & Café` becomes `hello-world-testing-marmite-cafe.md`. Print the created absolute path, and only that path, to stdout. For example, with that `articles` configuration, a project at `/project` prints `/project/hello-world-testing-marmite-cafe.md`.

The new file is nonempty and contains `# TITLE`. With `-t a,b`, begin with YAML delimiters and include the literal line `tags: a,b`, then the heading. `-p` and `-t` combine. Missing input folders return status 1 with `Input folder does not exist`. With `-e`, after writing the file, invoke the executable named by `EDITOR`, passing the file path as its argument, and wait for it.

## Spec 8

`--init-templates` creates `<input>/templates` only when it does not already exist; this action ignores configured `templates_path`. In particular, with `templates_path: layouts`, it creates `<input>/templates/base.html` and does not create `<input>/layouts`. A nonexistent input is status 1 with `Input folder does not exist`. If the `templates` path already exists, whether as a directory or a file, do not overwrite it; return 0 and report `Failed to create templates directory: Os { code: 17, kind: AlreadyExists, message: "File exists" }` on stderr. On success return 0 and report each created file on stderr as a line containing `Generated <path>`; every reported file exists and is nonempty. Create more than ten usable UTF-8 templates. Required names include `base.html`, `content.html`, `list.html`, `group.html`, `pagination.html`, `sitemap.xml`, `base_feeds.html`, `content_title.html`, `content_date.html`, `content_authors.html`, `comments.html`, `json_ld_content.html`, and `custom_index.html.example` (do not create `custom_index.html`). Every generated template file exceeds 100 bytes (the embedded `sitemap.xml` is 196 bytes) and contains supported template expressions where applicable, such as `{{ ... }}`.

## Spec 9

`--start-theme NAME` creates `<input>/NAME` containing `templates/`, `static/`, `README.md` longer than 100 bytes, and valid `theme.json`. Reject empty names or names containing `/` or `\` by writing `Invalid theme name: '<name>'` to stderr and creating nothing; this validation path returns 0. Never overwrite an existing theme directory; report `Theme directory already exists:` and preserve it. On success report every created file as `Generated <path>` on stderr, followed by `Theme '<name>' created successfully` and `To use this theme, add 'theme: <name>'`. The built-in theme currently creates 29 files and emits 29 `Generated` lines.

The theme contains the templates from Spec 8, including at least nontrivial `base.html`, `content.html`, `list.html`, and `group.html`; static assets `style.css`, `script.js`, `custom.css`, `custom.js`, `favicon.ico`, and `robots.txt`; and `static/colorschemes/` with at least ten nonempty CSS schemes, including `nord`, `dracula`, `gruvbox`, and `solarized`. `theme.json` has string fields `name`, `version`, `marmite_version`, `author`, `description`, plus a nonempty array `features`. Theme templates and nested partials must work immediately when selected.

## Spec 10

`--set-theme SOURCE` selects a local theme directory or downloads a ZIP. A valid local theme contains a readable JSON `theme.json` with name, version, author, and description; optional `features` and `tags` arrays are displayed under `Features:` and `Tags:` in stdout. For a local source, success stdout contains `Theme '<SOURCE-as-supplied>' has been successfully set`, and the same supplied path is written to the config's `theme` field without losing unrelated fields. Thus, passing an absolute local directory stores and reports its absolute path rather than just its final folder name. Missing local directories return 0 and report `Theme folder does not exist: <resolved-path>` on stderr. Invalid `theme.json` also returns 0 and reports `Failed to read theme metadata: <JSON-parser-reason>`. A missing `theme.json` or missing required metadata is likewise reported on stderr with status 0.

For `http(s)` ZIP URLs, download to a temporary location, extract a single wrapper directory into `<input>/<archive-stem>`, preserve subdirectories, locate `theme.json`, remove `.theme_download_temp`, and select that extracted theme. Thus `theme.zip` installs as `theme`, `feature_theme.zip` as `feature_theme`, and `complex_theme.zip` as `complex_theme`. Refuse an existing destination and invalid/no-metadata ZIPs with `Failed to download theme` and a useful reason. Recognize direct ZIP URLs and translate conventional GitHub (`/owner/repo[/tree/branch]`), GitLab (`/owner/project[/-/tree/branch]`), and Codeberg (`/owner/repo[/src/branch/branch]`) repository URLs to their ZIP downloads. Unsupported hosts and network/HTTP failures produce `Failed to download theme`, do not crash, and still return 0.

## Spec 11

A normal build recursively discovers `.md` files in the selected content root at arbitrary practical depth, including symlinks that resolve to files. A symlink is read successfully, but its fallback slug comes from the symlink's own filename: `content/link.md` pointing to a file containing `# Linked Page` produces `link.html`, not `linked-page.html`. Ignore non-Markdown/binary files as content. It must comfortably handle at least 120 files and individual Markdown files over 6 MiB within 30 seconds. Output is flat by content slug even when sources are nested. A fallback slug taken directly from a filename preserves that stem's case, spaces, and punctuation: nested `Deep File.md` produces `Deep File.html`. Files beginning `_` are fragments and not standalone pages; `_404.md` supplies the custom not-found page. `file_mapping` entries of `{source, dest}` read source relative to project root and render/copy it to the configured output destination, such as `README.md` to `about.html`.

Builds create a missing output directory. Existing output directories are reusable: regenerate current outputs without failure and do not corrupt unrelated files. A repeated unchanged build may be skipped based on state; `--force` must rewrite generated files and advance `marmite.json`'s build timestamp. Default-output builds target `<input>/site`.

## Spec 12

Markdown may have YAML frontmatter enclosed by leading and closing `---` lines or no frontmatter. Extract at least: `title`, `slug`, `date`, `kind`, `tags`, `author`, `authors`, `stream`, `series`, `draft`, `description`, `card_image`, `banner_image`, `comments`, `pinned`, `toc`, and arbitrary `extra`. Empty body/frontmatter-only and empty Markdown files do not crash; metadata-only content still generates a page. Malformed frontmatter logs `Failed to process content` and `Failed to parse YAML`, skips that source, and lets the rest of the build succeed; an unclosed flow sequence additionally contains `did not find expected ',' or ']'`. An invalid explicit date is fatal with status 1. For `date: not-a-valid-date-at-all`, stderr contains `ERROR: Invalid date format not-a-valid-date-at-all when parsing <absolute-source-path>, premature end of input`.

Title precedence is frontmatter title, the first level-one heading, then the first nonempty body line. That selected body line is removed from the rendered body; thus a headingless file whose body is `No heading` has title `No heading` and an empty content body rather than a humanized filename title. Slug precedence is explicit frontmatter slug, a frontmatter title-derived slug, then the filename stem after recognized date-prefix removal. Explicit and title-derived slugs are normalized to safe lowercase ASCII, but a filename-derived fallback is preserved verbatim; `Deep File.md` therefore produces `Deep File.html`. Special title characters are removed from a title-derived slug, e.g. `Post with Special: Quotes & Symbols / \ | ? *` gives `post-with-special-quotes-symbols`. Unicode titles/content remain literal UTF-8. Duplicate slugs produce a successful build, one output file, and stderr containing `ERROR` and `Duplicate slug found: '<slug>'`.

## Spec 13

A date makes content a post; content without a date is a page unless stream filename rules say otherwise. Recognize ISO date/datetime frontmatter and filename prefixes `YYYY-MM-DD-`, `YYYY-MM-DD-HH-MM-SS-`, and `YYYY-MM-DD-HH-MM-`. Strip such prefixes from ordinary output slugs. Parse stream-prefixed `STREAM-YYYY-MM-DD-SLUG.md` as stream `STREAM`, dated post, output `STREAM-SLUG.html`; parse `STREAM-S-SLUG.md` as stream content and output `STREAM-SLUG.html`, with a frontmatter date if present. A stream supplied only by frontmatter also prefixes the ordinary content slug: `2024-01-15-post.md` with `stream: dev` produces and is looked up as `dev-post`, not `post`. Dates render in archives/feeds; `%b %e, %Y` is the default display format and can be overridden.

Public post ordering is pinned posts first and otherwise newest date first. Series ordering is oldest first. A filename beginning `draft-` and a stream named `draft` do not suppress HTML publication: `draft-2024-01-06-hidden.md` is a dated post in stream `draft`, generates `draft-hidden.html`, and appears in `draft.html`; `draft-S-secret.md` generates the dateless standalone page `draft-secret.html`. The `draft` stream is special for RSS generation, however: this invocation does not generate `draft.rss`, although an otherwise equivalent `dev` stream generates `dev.rss`. The frontmatter field `draft: true` likewise does not suppress publication; such content still receives a standalone page and participates in lists and feeds. Dateless pages are still rendered but excluded from feeds and post-only groups.

## Spec 14

Authors accept singular `author`, plural `authors`, YAML arrays, or comma-separated strings; split and trim comma lists. Preserve all authors for HTML, grouping, author pages, and JSON Feed, while RSS item `<author>` contains only the first. Generate `authors.html`, `author-<author-slug>.html`, and `author-<author-slug>.rss`. A post appears in every listed author's group/feed. Every item in a filtered author RSS feed includes `<source url="<site-url>">author-<author-slug></source>` for that feed; for example Bob Jones's feed contains the literal text `author-bob-jones`, even though the item's `<author>` remains the first author. Empty author values are not discarded: the two-post invocation using `author: null` and `authors: ''` generates the empty-slug outputs `author-.html`, `author--1.html`, and `author-.rss`.

The config `authors` map supports `name`, `bio`, `avatar`, and `links`; use configured display names and metadata. The built-in author listing does not tolerate every partial metadata entry: when dated content references `bob` and the configured entry is only `bob: {name: Bob Jones}`, the build writes some earlier outputs but returns status 1 while rendering `author-bob-1.html`. Stderr identifies `list.html`, `url_for`, and ``Missing `path` argument``; the absent avatar is passed as a path. `links` must be a YAML sequence of two-element sequences in `[label, URL]` order, for example `links: [[Website, https://alice.example]]`; a scalar entry such as `links: [https://alice.example]` is invalid global configuration, returns status 1, and reports that `authors.alice.links[0]` has `invalid type: string` and `expected a tuple of size 2`. The label and URL are both rendered on the built-in author page. Feed files written before such a later template failure retain the normal JSON author shape: the author object always has `name`, `url`, and `avatar`; use the URL (the second element) of the first configured link, empty strings for absent values, and the author key itself as the name when not configured. Do not invent an RSS author for content with no author.

## Spec 15

Tags accept YAML arrays or comma-separated strings. Generate `tags.html`, one `tag-<slug>.html` per distinct post tag, and `tag-<slug>.rss`; when JSON feeds are enabled also generate `tag-<slug>.json`. A tag page/feed contains exactly posts with that tag. Slugify unsafe tag characters consistently. Pages without dates do not contribute to tag/author grouping. The built-in tag index exposes a count as a bare superscript numeral, for example `Café & Tea <sup>2</sup>`; it does not render the phrase `2 posts`.

## Spec 16

Streams may come from `stream` frontmatter or filename forms in Spec 13. Generate `streams.html` and a per-stream listing at `<stream-slug>.html` (not `stream-...html`). The config `streams.<key>.display_name` controls presentation with the key as fallback. Series come from frontmatter and produce `series.html`, `series-<slug>.html`, and `series-<slug>.rss`; configured `display_name` is used. A configured series `description` remains available as configuration/data metadata, but the built-in `series-<slug>.html` listing does not render it: with display name `The Guide` and description `Guide description`, `series-guide.html` contains `The Guide` and omits `Guide description`. Series list/feed order is chronological oldest-to-newest. Every item in a series RSS feed includes `<source url="<site-url>">series-<series-slug></source>`. Generic previous/next post links are controlled by `show_next_prev_links`.

## Spec 17

Every built-in HTML document is deterministic UTF-8 beginning exactly `<!DOCTYPE html>`, contains `<html lang="<language>">`, a viewport and UTF-8 meta tag, `<meta name="generator" content="Marmite" />` (the form without the slash is also discoverable as the same tag), a `<title>PAGE TITLE | SITE NAME</title>`, Open Graph title/description/type/site-name metadata, JSON-LD for website/content, links to `/static/favicon.ico`, `/static/pico.min.css`, `/static/marmite.css`, `/static/custom.css`, `/static/marmite.js`, and `/static/custom.js`, and the configured menu/footer. Content pages use `<article class="h-entry">` and `<div class="content-html e-content">`; the heading/title, date, authors, tags, banner, TOC, and navigation are emitted when applicable. Metadata and attribute values are interpolated without HTML escaping: a title `"Quoted" & <unsafe>` appears literally in `<title>` and produces a malformed Open Graph attribute of the form `content=""Quoted" & <unsafe>"`. Unicode is preserved literally. Raw body HTML follows Spec 19.

The default empty site is still a complete document. Its page title is `Welcome to Marmite | Home`; it contains a hidden `Welcome to Marmite` feed name, an item headed `No content found`, a Getting Started link, and the default Tags/Archive/Authors menu and powered-by footer. The built-in 404 has page title `Page not found | Home`, Open Graph title `Page not found`, an `h1` of that text, and body `Page not found :/`. Built-in output has stable whitespace so the same inputs and config produce byte-identical HTML. Empty-post body renders as an empty `<div class="content-html e-content"></div>` and its one-minute reading-time/date metadata remains valid.

## Spec 18

Convert CommonMark-style Markdown to HTML: ATX headings, paragraphs, bold, emphasis, inline code, fenced code, links, unordered/ordered lists, blockquotes, horizontal rules, and images. Headings that remain in the Markdown body contain a leading empty anchor with `href="#<heading-slug>"`, `aria-hidden="true"`, `class="anchor"`, and matching `id`. When the first H1 supplies the page title because no frontmatter title exists, it is extracted from the body and the content template emits it separately as plain `<h1>TITLE</h1>` with no anchor; `# Home` in `index.md` therefore produces the literal `<h1>Home</h1>`. Fenced language blocks preserve code text and expose `class="language-<language>"`; built-in content pages include Highlight.js CSS/JS and call `hljs.highlightAll()`. Preserve indentation and escape code rather than interpreting it.

## Spec 19

Support GitHub-flavored tables (`table`, `thead`/`th`, `tbody`/`td`), `~~strikethrough~~` as deletion text, task-list checkboxes, and footnotes with working reference/back-reference markup. Support `||spoiler||` with visible spoiler text in appropriate spoiler markup and common `:smile:`, `:heart:`, and `:rocket:` emoji aliases (preserving an unknown alias is acceptable). Preserve raw HTML blocks verbatim; Markdown inside a raw block is not recursively parsed. Literal Unicode across scripts, emoji, math, arrows, and symbols must survive unchanged.

## Spec 20

When site config `toc: true` or content frontmatter `toc: true` is set, derive a navigable table of contents from the headings that remain in the Markdown body, preserving hierarchy and linking to their exact anchor IDs. Render it in an element identifiable by `content-toc`/`toc`. The `toc` shortcode also emits `<div class="content-toc">` with those same body headings. The first H1 extracted as the page title is absent from both TOCs and has no anchor; for `# First`, `## Nested`, `### Deeper`, both TOCs contain only `Nested` and `Deeper`.

## Spec 21

Transform `[[target]]` and `[[display|target]]` into `<a href="resolved-or-fallback.html" data-wikilink="true">display-or-target</a>`. Explicit-slug references such as `[[first]]` resolve, and a self-reference by its own title can resolve to that explicit slug. A cross-page title target is not reliably matched before fallback encoding: `[[Shown Two|Page Two]]` produces `href="page-20two.html"`, while unresolved `[[missing thing]]` produces `href="missing-20thing.html"`. The `-20` text is literal. Such missing references may emit a `Reference missing: [...]` warning; self-links and circular links are legal and cannot recurse infinitely. When related content is enabled, collect reverse links without duplicates or self-backlinks and render backlinks on the target using absolute-root links such as `href="/post-one.html"`.

## Spec 22

Generate each content page plus `index.html` as the main newest-first post/listing page and `pages.html` as the page listing. A source whose resulting slug is `index` may supply `index.html`; otherwise the generated listing is the index. Listing entries include title, link, description/excerpt, relevant date/authors/tags, and configured site identity. Generate `index-2.html`, `index-3.html`, and so on whenever needed; `pagination` is the maximum items per page and total pages use ceiling division. Keep each content page accessible regardless of pagination.

## Spec 23

Generate taxonomy/navigation pages even for an empty site: at least `archive.html`, `authors.html`, `tags.html`, `pages.html`, `series.html`, `streams.html`, and `404.html`. For dated content, generate year archive pages and feeds named `archive-YYYY.html` and `archive-YYYY.rss`. Month-specific archive pages and feeds are not generated. Files such as `archive-2024-1.html` and `archive-2024-2.html` are pagination pages for the yearly archive, not January and February archives; no corresponding `archive-2024-1.rss` or `archive-2024-2.rss` is created. Archive indexes group newest years first. All generated pages are substantive valid HTML.

## Spec 24

With the default path names, copy a project `static/` tree to `output/static/` and a project `media/` tree to `output/media/`, preserving nested paths and bytes. When a project `static/` directory exists, its tree replaces rather than merges with the embedded static tree: `output/static` contains the project assets (plus copied root `custom.css`/`custom.js`) but does not contain embedded `favicon.ico`, `pico.min.css`, `marmite.css`, or `marmite.js` unless supplied by the project. Custom path names are preserved as destination names rather than normalized: `static_path: assets` copies to `output/assets/`, and `media_path: uploads` copies to `output/uploads/`. Missing/empty static or media directories are harmless. When the configured content directory exists, do not treat static/media files as content; the missing-content-directory fallback instead follows Spec 4 and scans Markdown below those trees. Theme static assets are copied first, then project-level custom assets may override them.

## Spec 25

Determine banner and social-card images in this precedence-aware manner. An explicit content `banner_image` (top-level, then `extra.banner_image`) supplies the banner; otherwise detect `<content-root>/<media_path>/<slug>.banner.<ext>`. An explicit `card_image` wins for social cards; otherwise detect `<slug>.card.<ext>`, then `<slug>.<ext>` in that same content media directory, then the first body image, then the banner. A project-root `<input>/media` tree is copied to output but is not the automatic-image lookup directory when the selected content root is `<input>/content`: putting `post.banner.jpg` and `post.card.png` only in `<input>/media` emits no `content-banner-image` and the body image `/media/body.png` supplies `og:image`; putting those files in `<input>/content/media` emits the banner and uses `/media/post.card.png`. Common raster extensions are searched. Emit banner markup identifiable by `content-banner-image`. Relative Open Graph image paths are combined with the site URL. An already-absolute explicit card URL is nevertheless corrupted by the current interpolation: with site URL `https://example.com/blog` and card `https://cdn.example/x.png`, emit exactly `<meta property="og:image" content="https://example.com/blog/"https://cdn.example/x.png"">`. Config-level `card_image`, `banner_image`, and `logo_image` affect site/list/feed metadata; configured logo/card references must appear in generated HTML. If no image exists, omit optional RSS image markup and use empty-string JSON-feed image fields.

## Spec 26

Unless `skip_image_resize` is true, optionally optimize raster media according to `extra.max_image_width`, `extra.banner_image_width`, and `extra.resize_filter`. Supported filters are `fast`, `balanced`, and `quality`; an unknown filter falls back safely. Widths must be 1 through 10,000; invalid widths leave files unchanged. Resize JPEG, PNG, and WebP (and safely process other raster formats where the decoder supports them), preserve output format and aspect ratio with sensible rounding, and never upscale. Banner width applies to explicit banner paths normalized from `media/`, `./media/`, or `../media/`, and to filenames containing `.banner.`; other raster files use max width. If only banner width exists, ordinary images remain unchanged. SVG, ICO, unknown files, and files already inside any `thumbnails` directory are copied byte-for-byte.

## Spec 27

One bad/corrupt image never aborts a build or prevents valid images from being processed. When resizing is actually attempted, log its failure and continue. If `max_image_width` is invalid, resizing is skipped before image decoding: with width `0`, unknown filter `unknown`, `good.jpg`, and corrupt `bad.jpg`, both files are copied unchanged, status is 0, stderr warns `Invalid value for 'max_image_width': 0 (must be between 1 and 10000 pixels). Setting ignored.` and `Invalid resize_filter value 'unknown'. Valid options: 'fast', 'balanced', 'quality'. Using default 'quality'.`, and stderr does not mention `bad.jpg`. For optimized images create `output/media/.marmite-resize-state.json` containing `config_hash` and an `images` map. Each entry includes `source_size`, `source_modified`, `target_width`, and boolean `was_resized`. Do not create this state file for a media directory with no images. Reuse unchanged state, but reprocess when source size/modification or resize configuration changes. Configuration changes must be applied from the original source, not from a previously downsized output. A batch of 15 images completes and records all 15 entries; its integer aspect fitting makes several actual widths smaller than the recorded target. In that batch, the 51×20 JPEG with `max_image_width: 25` becomes 23×9 while its state entry has `target_width: 25` and `was_resized: true`.

## Spec 28

Gallery shortcode paths are relative to `<content-root>/<media_path>/<gallery_path>`, whose defaults are `media/gallery`. A gallery is one directory only: include top-level image files but exclude nested directories and its `thumbnails` directory. Recognize `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.bmp`, and `.tiff` case-insensitively. Preserve filenames, including spaces/case. Ignore nonimages. A missing path, a path that is a file, an empty gallery, empty config, invalid config, invalid regex, or corrupt image must not abort the site build.

Optional `gallery.yaml` fields are `name` (default directory name), `ord` (`asc` default or `desc` alphabetical filename order), `cover` (default first sorted image, with graceful fallback), and `images`, a list of `{filename, description}` matchers. Description matching is case-insensitive and precedence is exact filename, then regex/pattern or partial match, then `*` wildcard. Earlier/more specific entries must not be overwritten by a later generic match. HTML text in descriptions remains available in the `data-description` attribute value. Invalid YAML logs `Failed to parse gallery config` and then uses all defaults; an invalid regex is skipped so a later wildcard can match.

## Spec 29

`<!-- .gallery path=NAME -->` renders a `div.shortcode-gallery` with id containing `gallery-NAME`, optional `h3.gallery-title`, a `div.gallery-main-panel`, main image id `gallery-NAME-main-image`, and one `img.gallery-thumbnail` per gallery image. Original URLs are `/media/gallery/NAME/FILENAME`; thumbnail URLs are `/media/gallery/NAME/thumbnails/FILENAME`. Each thumbnail has the original filename as `alt`, a full-image reference (`data-full`), and its description (`data-description`). Ordering and cover follow Spec 28.

When `gallery_create_thumbnails` is true, create actual smaller thumbnails in output using `gallery_thumb_size` (default 50), retaining file format/name; valid thumbnails are smaller than their originals. Reuse valid existing source thumbnails rather than recursively including them. If thumbnail creation fails, write the exact connector phrase `Failed to create thumbnail for ` followed by the full source path on stderr, omit only the failed thumbnail file, but retain an HTML gallery entry and process all valid siblings. A conflicting `thumbnails` file/invalid target is handled without crashing.

## Spec 30

Shortcodes are enabled by default and use the default regular expression shown in help, matching HTML comments such as `<!-- .youtube id="x" -->`. Accept quoted parameter values containing spaces, unquoted values, booleans/numbers as strings, multiple invocations, and invocations with no parameters. A configured `shortcode_pattern` is retained in effective configuration. For the pattern `\[\[\.(\w+)(?:\s+([^\]]+))?\]\]`, the input `[[.youtube id=custom]]` does not invoke YouTube and the later wikilink pass emits `<a href=".youtube%20id=custom" data-wikilink="true">.youtube id=custom</a>`. With shortcodes disabled, leave the original HTML comments unchanged and render no replacement.

`--shortcodes INPUT` prints a human-readable report to stdout containing `Shortcodes:`, `Enabled: true|false`, `Pattern:`, `Available shortcodes:`, and `Examples based on your configuration:`. Each available shortcode line uses the exact bullet prefix `  - ` and form `  - <name>: <description>`. In particular, the tags line is `  - tags: Display a list of all tags with post counts. Params: ord=desc, items=0`. Built-ins are `authors`, `card`, `gallery`, `pages`, `posts`, `series`, `socials`, `spotify`, `streams`, `tags`, `toc`, and `youtube`; descriptions include `Display a list of all authors`, `Display a list of recent posts`, `Display a list of all pages`, `Display a list of all tags with post counts`, `Display table of contents`, and `Embed a YouTube video`.

## Spec 31

The YouTube shortcode accepts `id`, `width` default `560`, and `height` default `315`, renders a paragraph-wrapped iframe at `https://www.youtube.com/embed/<id>` with fullscreen enabled, and applies custom dimensions. If `id` already begins with `http`, use it unchanged instead of double-prefixing. Spotify accepts `url`, width default `100%`, and height default `352`, rendering `https://open.spotify.com/embed/<url>` with `data-testid="embed-iframe"` and a style containing `border-radius:12px`. Multiple embeds render independently.

The `posts` shortcode produces `ul.posts-list`, newest-first post links, and enforces `items` exactly (items 3 means three links). `tags` produces `ul.tags-list` with one linked list item per tag and correct `(N posts)` counts. `card slug="..."` resolves content and renders a link plus `div.card-title` containing its title; `div.card-text` contains the content date rather than its description. For a post dated 2024-01-02 with `description: Desc 2`, card text is exactly `2024-01-02` and omits `Desc 2`. The authors/pages/series/streams/socials/gallery/toc built-ins expose the analogous configured collections.

## Spec 32

Load user shortcode definitions only from files directly inside `<input>/shortcodes`; do not recursively discover definitions in nested directories. A direct user definition overrides a built-in. Consequently, `shortcodes/nested/note.md` is not registered, and invoking `note` renders visible `Shortcode Error: Shortcode 'note' not found` content. A directly contained `.html` shortcode is a template file defining a macro whose name matches the filename stem and whose named arguments match invocation keys, for example `{% macro youtube(id) %}<strong>{{ id | upper }}</strong>{% endmacro youtube %}`. The processor invokes it as `youtube(id="hello")`, producing `<strong>HELLO</strong>`. It does not pass a single `parameters` object: a macro declared as `youtube(parameters)` and reading `parameters.id` fails at rendering, logs `Shortcode 'youtube' failed to render`, and emits visible `Shortcode Error:` content. Support defaults, variable interpolation, `upper`, loops, conditionals, and HTML output using named macro arguments. A directly contained `.md` shortcode is template-rendered and then Markdown-rendered, but invocation parameters are not exposed in its template context, either as top-level variables or through `parameters`/`params` objects. Thus `shortcodes/note.md` containing `**Hello {{ name }}**`, invoked as `<!-- .note name=World -->`, does not render `Hello World`: the build returns 0, logs `Shortcode 'note' failed to render: Failed to render markdown shortcode 'note': Failed to render '__tera_one_off'`, and emits visible `Shortcode Error:` content. A parameter-free Markdown definition such as `**Static**` renders normally as `<strong>Static</strong>`. Extract a listing description from a first-line `{# description #}` comment.

A standalone HTML file with no macro logs `HTML shortcode file ... must contain at least one macro`; a mismatched name produces `... must contain a macro named '<stem>'` and lists found macros. Definition-collection errors are not aggregated. With `empty.html` containing no macro and `wanted.html` containing only macro `other`, the build returns 0 and reports only `HTML shortcode file <path>/wanted.html must contain a macro named 'wanted'. Found macros: ["other"]`; it does not report the no-macro error for `empty.html`. An invocation of an unknown shortcode similarly returns 0, logs `Shortcode '<name>' failed to render` and `Shortcode '<name>' not found`, and emits visible `Shortcode Error:` content in the generated HTML. Unbalanced parameter quotes must not crash and must still produce valid HTML.

## Spec 33

Use a deterministic template language compatible with these constructs: `{{ dotted.value }}`, `{% set x = function(...) %}`, `{% if/else/endif %}`, `{% for item in values %}` and two-target map iteration, `{% extends %}`, `{% block/endblock %}`, `{% include 'path' ignore missing %}`, macros, `|length`, and `|upper`. Preserve literal template whitespace exactly; do not auto-prettify rendered custom templates. Rendered Markdown HTML supplied as `content.html` includes its own terminating newline, so interpolating it before a template newline produces an additional blank line. Recursively load template subdirectories. Search precedence is theme templates over project templates over embedded defaults. When both selected theme and project define `content.html` and `list.html`, the theme versions win: a theme content template `THEME {{ content.title }}` renders `THEME Page`, and a theme list template `THEME LIST` renders that exact index. A winning custom `content.html` wholly controls both source-backed content pages and the synthetic `404.html`; a winning custom `list.html` controls index and other list pages.

Undefined referenced template fields are fatal with nonzero status and an error naming the field and saying it was `not found`. A malformed template logs `Failed to load template <name>`; loading may fall back sufficiently for the overall build to return 0. A configured missing theme is fatal status 1 with `Theme folder '<path>' does not exist`.

## Spec 34

Selecting a theme uses that theme's templates/static tree; `--theme` overrides config. Theme templates win over same-named project templates. `--colorscheme NAME` (or config `extra.colorscheme`) adds exactly the selected stylesheet reference `/static/colorschemes/NAME.css`; the CLI choice replaces, rather than supplements, the config choice. It is acceptable to reference a nonexistent scheme without failing. Theme and colorscheme work together. Project `custom.css` plus arbitrary theme static assets are copied, and modifications to a theme base/partial are visible in all generated documents.

## Spec 35

Expose `url_for(path=..., abs=false)` in templates. External `http://`, `https://`, and `mailto:` values pass through unchanged. Normalize `./`, leading slashes, and duplicate joins, but preserve a trailing slash supplied by a nonempty path. For site URL `https://example.com/blog/`, `url_for(path="./static/style.css")` returns `/blog/static/style.css`, `url_for(path="/x/", abs=true)` returns `https://example.com/blog/x/`, and an empty absolute path returns `https://example.com/blog/`. With no site URL, both modes return root-relative paths. Joining a base URL ending `/` does not otherwise produce a doubled slash.

Expose `source_link(content=...)`. With `source_repository`, return that URL stripped of trailing slash plus `/` plus the source filename; e.g. repository `https://github.com/user/repo/blob/main/content/` and source `.../test.md` gives `https://github.com/user/repo/blob/main/content/test.md`. Otherwise, when `publish_md` is true return `./test.md`; otherwise return the empty string. The function requires `content.source_path`. Because project `content.html` is also applied to synthetic `404.html`, calling `source_link(content=content)` there is fatal: return status 1 and log ``Missing `source_path` in content`` followed by `Failed to render 'content.html'`. An unguarded call in a global content override therefore prevents the whole build from completing.

## Spec 36

Expose template functions `get_posts(ord="desc", items=0)` and `group(kind, ord="desc", items=0)`. Accept `items` as a number or numeric string; zero/omitted means unlimited. `get_posts` excludes pages but includes dated stream posts and posts marked with frontmatter `draft: true`; in the helper fixture containing ordinary post `A` and stream post `B`, unlimited `get_posts` has length 2. It orders by date descending by default or ascending for `asc`, then truncates. `group` supports `tag`, `author`, `stream`, `series`, and `archive`; group values are lists of posts. Ascending order is alphabetical/chronological. Default descending tag/author/stream ordering is greatest post count first; ties preserve first encounter order. Archive order is newest year first. Pages never enter post groups.

Expose `stream_display_name(stream=...)` and `series_display_name(series=...)`, returning configured display names or the original key. These functions and collection items are usable by custom templates. Arbitrary configuration metadata is not inserted as a top-level `extra` variable: `{{ extra.words }}` and `{{ extra.custom }}` are fatal with ``Variable `extra.words` not found in context while rendering 'list.html'`` and the analogous `extra.custom` message. It is available under the site object instead; changing those expressions to `site.extra.words`, `site.extra.mapping`, and `site.extra.custom` renders the configured values successfully.

## Spec 37

Expose `get_data_by_slug(slug=...)` returning an object with `title`, `text`, `image`, `content_type`, and `slug`. Resolve ordinary posts/pages by their effective slug; `text` is a post date such as `2024-01-15` and `content_type` is `post`, while pages have type `page`. Because a frontmatter stream prefixes that effective slug, a post from `2024-01-15-post.md` with `stream: dev` is available as `dev-post`; looking up `post` is fatal with `Content not found for slug: post`. Resolve `series-X` using configured display name/description and type `series`; `tag-X` with title X, text `N posts`, type `tag`; `archive-YYYY` with title `Posts from YYYY`, text `N posts`, type `archive`; `stream-X` with display name, `N posts`, type `stream`, and bare slug X; and `author-X` with configured author name/avatar, `N posts`, and type `author`.

Expose `get_gallery(path=...)`, returning null for a missing gallery. An existing gallery exposes `name`, `cover`, and `ord`; for a gallery configured as `name: Pictures`, `cover: b.jpg`, and `ord: desc`, these render as `Pictures|b.jpg|desc`. It does not expose an `images` member. Referencing `g.images` is fatal with ``Variable `g.images` not found in context while rendering 'list.html'``.

## Spec 38

Generate RSS 2.0 as `index.rss` whenever at least one non-stream dated post exists, plus filtered stream/tag/author/series and year archive feeds. A dated post assigned to a stream is omitted from `index.rss` but remains in its filtered feeds. In the taxonomy fixture, streamed post `First` dated 2024-01-15 is absent from `index.rss`, whose items begin with `Second` dated 2024-01-10, while `First` appears in `dev.rss`, `tag-rust.rss`, both author feeds, `series-guide.rss`, and `archive-2024.rss`; its RSS author is the first plural-author value, `alice`. Month archive feeds are not generated. Root is `<rss version="2.0">` with `<channel>`. Channel includes site name as title, normalized site URL as link, tagline as description, `<generator>marmite</generator>`, and `pubDate` equal to the newest included item. A configured site card image creates a channel image URL; otherwise omit `<image>`. For compatibility, this channel image is formed by literal `site-url + "/" + card-image`, so a card image already beginning `/` yields the tested double slash, e.g. `https://example.com//logo.png`. If URL has no protocol, prepend `https://` when config `https` is true and `http://` otherwise; preserve an existing protocol.

Include at most the 15 newest matching dated posts; apply the stream exclusion only to the main index feed, not the filtered feeds, except that a stream named `draft` has no filtered RSS feed. Frontmatter-only `draft: true` does not suppress an item. Each item has title, absolute link/guid, RFC-822 GMT date (e.g. `Mon, 15 Jan 2024 00:00:00 GMT`), description, Markdown-converted HTML in the RSS content namespace, one `<category>` per tag, and only its first frontmatter author value if any (for configured key `alice`, RSS text remains `alice`). Omit author/categories when absent. Preserve Unicode and XML-escape special characters. A nonempty scalar frontmatter description is serialized in item description/JSON summary as its JSON string representation, including surrounding double quotes; an absent description becomes an empty JSON summary. Series feeds are oldest-first. Archive and taxonomy feeds contain only matching items; author and series feeds add the `<source>` elements specified in Specs 14 and 16.

## Spec 39

When `json_feed` is enabled, generate JSON Feed v1 at `index.json` and filtered stream/taxonomy/archive feeds such as `dev.json`, `tag-tech.json`, and `archive-2024.json`. Top-level keys include `version: "https://jsonfeed.org/version/1"`, site title, `home_page_url`, `feed_url`, description, and `items`. Unlike RSS, JSON-feed URL fields do not normalize a missing protocol or trim a trailing slash. With configured `url: example.com/blog/` and `https: true`, `home_page_url` is exactly `example.com/blog/`, `feed_url` is `example.com/blog//index.json`, and the `Second` item's `id` and `url` are both exactly `example.com/blog//second.html`. Use the same dateless and main-index stream filtering, newest-first order, and 15-item limit as RSS; filtered feeds still include matching stream posts. Neither a `draft` stream name nor `draft: true` suppresses an otherwise eligible item.

Each item contains identical `id` and `url` strings, title, rendered `content_html`, `date_published` formatted like `2024-01-15T00:00:00-00:00`, language, `authors` array, `tags` array, and always-present `summary` and `image` strings (empty if unavailable). The rendered `content_html` string ends with a newline; the body `Multiple authors on this post.` is exactly `<p>Multiple authors on this post.</p>\n`. Author objects follow Spec 14. Preserve Unicode as real JSON Unicode. One-item feeds remain valid with arrays present.

## Spec 40

Normal builds generate `robots.txt` exactly:

```text
User-agent: Mediapartners-Google
Disallow:

User-agent: *
Allow: /
```

When `build_sitemap` is true (default), generate XML with declaration `<?xml version="1.0" encoding="UTF-8"?>`, a valid `<urlset>`, and locations for generated index/content/taxonomy pages using the configured base URL; false suppresses it. When `publish_urls_json` is true (default), generate valid `urls.json` with arrays named at least `posts`, `pages`, `tags`, `authors`, `streams`, `series`, and `feeds`, using root-style URLs ending in the actual filenames, plus `summary.total` as a positive integer when content exists. `--show-urls` computes the same organization without needing a prior build: if a site URL is set, it may print full URLs line-wise; otherwise stdout must be the valid JSON object and include posts/pages. It always includes the index URL.

Always write valid `marmite.json` containing `marmite_version`, integer Unix `timestamp`, `generated_at`, numeric `elapsed_time`, and the effective `config`. Respect configuration that disables sitemap or urls JSON.

## Spec 41

`--serve` first makes the normal build, then remains running and serves the output directory over HTTP on `--bind HOST:PORT` (default `0.0.0.0:8000`). A custom address must be honored. `/` serves `index.html`. JavaScript is served as `Content-Type: text/javascript`, but a `.css` asset is served as `Content-Type: text/plain`, not `text/css`. A missing path serves the generated `404.html` body; returning HTTP 200 for that fallback is required. Sanitize URL decoding/path normalization so traversal attempts cannot read outside the output root and instead get an HTTP error or the HTML fallback. Handle port conflicts without an uncontrolled crash: either report a start failure cleanly or fall back to an OS-assigned port. Remain alive until terminated by the caller. When the running process is terminated with SIGTERM, it need not perform a graceful coverage-runtime shutdown: in particular, setting `LLVM_PROFILE_FILE` must not cause the server to leave a matching `.profraw` file merely because it was terminated.

## Spec 42

`--watch` makes an initial build and remains running. Plain watch mode does not rebuild for a newly created Markdown source within eight seconds: starting with `content/first.md` creates `site/first.html`, but subsequently creating `content/second.md` leaves `site/second.html` absent while the process remains alive. Current compatibility behavior may retain an orphaned HTML file after its source is deleted. Combined watch-and-serve mode does detect and rebuild an existing Markdown source modified after startup within 10 seconds. In the fresh-project invocation with pagination 1 that initially serves `content/index.md` containing `# Original` and then immediately changes it to `# Changed`, the initial response at `/` contains `Original`; throughout the 10-second polling window no response contains `Changed`, and the final response contains neither `Original` nor `Changed`. The regenerated `pages.html` and `pages-1.html` do contain `Changed`.

With `--serve --watch`, every initially served HTML response contains a reference to `__marmite__/livereload.js`, including in the root-response scenario above. Serving without watch must not inject that script.

## Spec 43

Generation is resilient and deterministic. Empty input succeeds with no diagnostics and produces the complete core site. Missing optional config/static/media/gallery/template fragments are handled by defaults. Unsupported/binary files are ignored or copied appropriately. Spaces, punctuation, very long legal filenames, deeply nested paths, non-Latin text, circular references, frontmatter-only pages, many simultaneous images, and repeated builds cannot crash the executable. Preserve source files. Return 0 when recoverable per-file problems are logged and useful site output can still be generated; reserve status 1/nonzero for command-line errors, invalid input/output paths, invalid global configuration, explicit invalid dates, missing selected themes, and unrecoverable rendering/output failures.


## Spec 44

The following are byte-exact conformance snapshots for the embedded default renderer, including indentation, blank lines, entities, and one final newline after the closing `</html>`. They make the otherwise visual template contract in Spec 17 fully self-contained. The empty-site case uses defaults and no content. The frontmatter-only case is a root `post.md` containing only `title: Only Frontmatter` and `date: 2024-01-01`. The special-title case has title `Post with Special: Quotes & Symbols / \\ | ? *` and body heading `Content with special chars`. The self-link case has title `Self Link Test`, slug `self-link`, and body `This post links to [[self-link]] itself.`. The 404 snapshot is the built-in fallback.

### Empty site index

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark" />
    <meta name="generator" content="Marmite" />
    
    
    <meta property="og:title" content="Home">
    <meta property="og:description" content="">
    
    
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Home">
    
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      "name": "Home",
      "url": ""
    }
</script>
    <title>Welcome to Marmite | Home</title>
    <link rel="stylesheet" type="text/css" href="/static/pico.min.css">
    <link rel="stylesheet" type="text/css" href="/static/marmite.css">
    
    <link rel="stylesheet" type="text/css" href="/static/custom.css">
    
        <link rel="alternate" type="application/rss+xml" title="index" href="/index.rss">
    

    

    
    
</head>
<body>
    
    <main class="container">
        
        <header class="header-content">
            <nav class="header-nav">
                <ul class="header-name">
                    <li>
                        <hgroup class="h-card">
                            <h2>
                                <a href="/" class="contrast p-name u-url">
                                    
                                        Home
                                    
                                </a>
                            </h2>
                            
                        </hgroup>
                    </li>
                </ul>
                <button id="menu-toggle" class="hamburger">&#9776;</button>

                <ul class="header-menu" id="header-menu">
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/tags.html">Tags</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/archive.html">Archive</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/authors.html">Authors</a>
                        
                    </li>
                    
                    
                    
                    <div class="underline"></div>
                </ul>
            </nav>
            
        </header>
        
        <section class="main-content">
            




    
    

    




<div class="content-list  h-feed">
    <h1 class="p-name" style="display: none;">Welcome to Marmite</h1>
    <div class="left">
    <article class="content-list-item left">
        <h2 class="content-title">No content found</h2>
        <p class="content-excerpt">
            Add some markdown content and generate the site. &rarr; <a target="_blank" href="https://marmite.blog/getting-started.html">Getting Started</a>
        </p>
    </article>
    
    
    </div>
</div>

        </section>
        
        <footer class="footer-content grid">
            <div>Powered by <a href="https://github.com/rochacbruno/marmite">Marmite</a> | <small><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC-BY_NC-SA</a></small></div>
            
        </footer>
        
    </main>
    <script src="/static/marmite.js"></script>
    <script src="/static/custom.js"></script>
    
    
    
    
</body>
</html>
```

### Frontmatter-only dated post

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark" />
    <meta name="generator" content="Marmite" />
    
<meta property="og:title" content="Only Frontmatter">

<meta property="og:description" content="">


<meta property="og:type" content="article">
<meta property="og:site_name" content="Home">

<meta property="article:published_time" content=" 2024-01-01T00:00:00+00:00">



<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": "/only-frontmatter.html"
    },
    "url": "/only-frontmatter.html",
    "headline": "Only Frontmatter",
    "description": "",
    
    
    "publisher": {
        "@type": "Organization",
        "name": "Home",
        "logo": {
            "@type": "ImageObject",
            "url": "/"
        }
    },
    "datePublished": "2024-01-01T00:00:00+00:00"
}
</script>


    <title>Only Frontmatter | Home</title>
    <link rel="stylesheet" type="text/css" href="/static/pico.min.css">
    <link rel="stylesheet" type="text/css" href="/static/marmite.css">
    
    <link rel="stylesheet" type="text/css" href="/static/custom.css">
    
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/styles/github.min.css" id="highlightjs-theme" />



        <link rel="alternate" type="application/rss+xml" title="index" href="/index.rss">
    <link rel="alternate" type="application/rss+xml" title="year: 2024" href="/archive-2024.rss">
    

    

    
    
</head>
<body>
    
    <main class="container">
        
        <header class="header-content">
            <nav class="header-nav">
                <ul class="header-name">
                    <li>
                        <hgroup class="h-card">
                            <h2>
                                <a href="/" class="contrast p-name u-url">
                                    
                                        Home
                                    
                                </a>
                            </h2>
                            
                        </hgroup>
                    </li>
                </ul>
                <button id="menu-toggle" class="hamburger">&#9776;</button>

                <ul class="header-menu" id="header-menu">
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/tags.html">Tags</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/archive.html">Archive</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/authors.html">Authors</a>
                        
                    </li>
                    
                    
                    
                    <div class="underline"></div>
                </ul>
            </nav>
            
        </header>
        
        <section class="main-content">
            



<article class="h-entry">
  <data class="p-name" value="Only Frontmatter"></data>
  <a class="u-url" href="/only-frontmatter.html" style="display: none;"></a>
  
  <time class="dt-published" datetime="2024-01-01T00:00:00+00:00" style="display: none;">Jan  1, 2024</time>
  

  

  


<div class="content-title" id="title">
    <h1>Only Frontmatter</h1> 
    


<span class="content-date">
    <small> Jan  1, 2024 - &#10710; 1 min</small>
</span>

</div>

  
  

  <div class="content-html e-content"></div>
  
  <footer class="data-tags-footer">

    <div class="content-authors-flex">
      <div class="content-authors-full">
        

      </div>

      <div class="date-tags-container">
        <div class="content-date">
          


<span class="content-date">
    <small> Jan  1, 2024 - &#10710; 1 min</small>
</span>

          
        </div>

        <ul class="content-tags">
          
        </ul>
      </div>
    </div>
  </footer>
  
</article>















        </section>
        
        <footer class="footer-content grid">
            <div>Powered by <a href="https://github.com/rochacbruno/marmite">Marmite</a> | <small><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC-BY_NC-SA</a></small></div>
            
        </footer>
        
    </main>

    <script src="/static/marmite.js"></script>
    <script src="/static/custom.js"></script>
    
    
    
    
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/highlight.min.js"></script>
<script>
  hljs.highlightAll();
</script>



</body>
</html>
```

### Special-character title page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark" />
    <meta name="generator" content="Marmite" />
    
<meta property="og:title" content="Post with Special: Quotes & Symbols / \ | ? *">

<meta property="og:description" content="Content with special chars
">


<meta property="og:type" content="article">
<meta property="og:site_name" content="Home">



<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": "/post-with-special-quotes-symbols.html"
    },
    "url": "/post-with-special-quotes-symbols.html",
    "headline": "Post with Special: Quotes & Symbols / \ | ? *",
    "description": "Content with special chars
",
    
    
    "publisher": {
        "@type": "Organization",
        "name": "Home",
        "logo": {
            "@type": "ImageObject",
            "url": "/"
        }
    },
    
}
</script>


    <title>Post with Special: Quotes & Symbols / \ | ? * | Home</title>
    <link rel="stylesheet" type="text/css" href="/static/pico.min.css">
    <link rel="stylesheet" type="text/css" href="/static/marmite.css">
    
    <link rel="stylesheet" type="text/css" href="/static/custom.css">
    
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/styles/github.min.css" id="highlightjs-theme" />



        <link rel="alternate" type="application/rss+xml" title="index" href="/index.rss">
    

    

    
    
</head>
<body>
    
    <main class="container">
        
        <header class="header-content">
            <nav class="header-nav">
                <ul class="header-name">
                    <li>
                        <hgroup class="h-card">
                            <h2>
                                <a href="/" class="contrast p-name u-url">
                                    
                                        Home
                                    
                                </a>
                            </h2>
                            
                        </hgroup>
                    </li>
                </ul>
                <button id="menu-toggle" class="hamburger">&#9776;</button>

                <ul class="header-menu" id="header-menu">
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/tags.html">Tags</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/archive.html">Archive</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/authors.html">Authors</a>
                        
                    </li>
                    
                    
                    
                    <div class="underline"></div>
                </ul>
            </nav>
            
        </header>
        
        <section class="main-content">
            



<article class="h-entry">
  <data class="p-name" value="Post with Special: Quotes & Symbols / \ | ? *"></data>
  <a class="u-url" href="/post-with-special-quotes-symbols.html" style="display: none;"></a>
  

  

  


  
  

  <div class="content-html e-content"><h1><a href="#content-with-special-chars" aria-hidden="true" class="anchor" id="content-with-special-chars"></a>Content with special chars</h1>
</div>
  
</article>















        </section>
        
        <footer class="footer-content grid">
            <div>Powered by <a href="https://github.com/rochacbruno/marmite">Marmite</a> | <small><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC-BY_NC-SA</a></small></div>
            
        </footer>
        
    </main>

    <script src="/static/marmite.js"></script>
    <script src="/static/custom.js"></script>
    
    
    
    
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/highlight.min.js"></script>
<script>
  hljs.highlightAll();
</script>



</body>
</html>
```

### Self-wikilink page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark" />
    <meta name="generator" content="Marmite" />
    
<meta property="og:title" content="Self Link Test">

<meta property="og:description" content="This post links to self-link itself.
">


<meta property="og:type" content="article">
<meta property="og:site_name" content="Home">



<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": "/self-link.html"
    },
    "url": "/self-link.html",
    "headline": "Self Link Test",
    "description": "This post links to self-link itself.
",
    
    
    "publisher": {
        "@type": "Organization",
        "name": "Home",
        "logo": {
            "@type": "ImageObject",
            "url": "/"
        }
    },
    
}
</script>


    <title>Self Link Test | Home</title>
    <link rel="stylesheet" type="text/css" href="/static/pico.min.css">
    <link rel="stylesheet" type="text/css" href="/static/marmite.css">
    
    <link rel="stylesheet" type="text/css" href="/static/custom.css">
    
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/styles/github.min.css" id="highlightjs-theme" />



        <link rel="alternate" type="application/rss+xml" title="index" href="/index.rss">
    

    

    
    
</head>
<body>
    
    <main class="container">
        
        <header class="header-content">
            <nav class="header-nav">
                <ul class="header-name">
                    <li>
                        <hgroup class="h-card">
                            <h2>
                                <a href="/" class="contrast p-name u-url">
                                    
                                        Home
                                    
                                </a>
                            </h2>
                            
                        </hgroup>
                    </li>
                </ul>
                <button id="menu-toggle" class="hamburger">&#9776;</button>

                <ul class="header-menu" id="header-menu">
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/tags.html">Tags</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/archive.html">Archive</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/authors.html">Authors</a>
                        
                    </li>
                    
                    
                    
                    <div class="underline"></div>
                </ul>
            </nav>
            
        </header>
        
        <section class="main-content">
            



<article class="h-entry">
  <data class="p-name" value="Self Link Test"></data>
  <a class="u-url" href="/self-link.html" style="display: none;"></a>
  

  

  


<div class="content-title" id="title">
    <h1>Self Link Test</h1> 
    


<span class="content-date">
    <small></small>
</span>

</div>

  
  

  <div class="content-html e-content"><p>This post links to <a href="self-link.html" data-wikilink="true">self-link</a> itself.</p>
</div>
  
</article>















        </section>
        
        <footer class="footer-content grid">
            <div>Powered by <a href="https://github.com/rochacbruno/marmite">Marmite</a> | <small><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC-BY_NC-SA</a></small></div>
            
        </footer>
        
    </main>

    <script src="/static/marmite.js"></script>
    <script src="/static/custom.js"></script>
    
    
    
    
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/highlight.min.js"></script>
<script>
  hljs.highlightAll();
</script>



</body>
</html>
```

### Default 404 page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark" />
    <meta name="generator" content="Marmite" />
    
<meta property="og:title" content="Page not found">

<meta property="og:description" content=" :/">


<meta property="og:type" content="article">
<meta property="og:site_name" content="Home">



<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "mainEntityOfPage": {
        "@type": "WebPage",
        "@id": "/404.html"
    },
    "url": "/404.html",
    "headline": "Page not found",
    "description": " :/",
    
    
    "publisher": {
        "@type": "Organization",
        "name": "Home",
        "logo": {
            "@type": "ImageObject",
            "url": "/"
        }
    },
    
}
</script>


    <title>Page not found | Home</title>
    <link rel="stylesheet" type="text/css" href="/static/pico.min.css">
    <link rel="stylesheet" type="text/css" href="/static/marmite.css">
    
    <link rel="stylesheet" type="text/css" href="/static/custom.css">
    
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/styles/github.min.css" id="highlightjs-theme" />



        <link rel="alternate" type="application/rss+xml" title="index" href="/index.rss">
    

    

    
    
</head>
<body>
    
    <main class="container">
        
        <header class="header-content">
            <nav class="header-nav">
                <ul class="header-name">
                    <li>
                        <hgroup class="h-card">
                            <h2>
                                <a href="/" class="contrast p-name u-url">
                                    
                                        Home
                                    
                                </a>
                            </h2>
                            
                        </hgroup>
                    </li>
                </ul>
                <button id="menu-toggle" class="hamburger">&#9776;</button>

                <ul class="header-menu" id="header-menu">
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/tags.html">Tags</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/archive.html">Archive</a>
                        
                    </li>
                    
                      
                      
                    <li>
                        
                        <a class="menu-item secondary"  href="/authors.html">Authors</a>
                        
                    </li>
                    
                    
                    
                    <div class="underline"></div>
                </ul>
            </nav>
            
        </header>
        
        <section class="main-content">
            



<article class="h-entry">
  <data class="p-name" value="Page not found"></data>
  <a class="u-url" href="/404.html" style="display: none;"></a>
  

  

  


<div class="content-title" id="title">
    <h1>Page not found</h1> 
    


<span class="content-date">
    <small></small>
</span>

</div>

  
  

  <div class="content-html e-content">Page not found :/</div>
  
</article>















        </section>
        
        <footer class="footer-content grid">
            <div>Powered by <a href="https://github.com/rochacbruno/marmite">Marmite</a> | <small><a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC-BY_NC-SA</a></small></div>
            
        </footer>
        
    </main>

    <script src="/static/marmite.js"></script>
    <script src="/static/custom.js"></script>
    
    
    
    
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.10.0/highlight.min.js"></script>
<script>
  hljs.highlightAll();
</script>



</body>
</html>
```
