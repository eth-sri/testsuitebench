# Clarified specification for `executable`

The required artifact is one directly runnable program named exactly `executable`. It is a command-line page archiver compatible with Monolith 2.11.0: it accepts an HTML document, rewrites retrievable dependencies into the document, and emits one self-contained HTML or MHTML file. All behavior below is part of the executable unless a section explicitly describes input supplied by the operating system or test harness.

## Spec 1

The command-line shape is `executable [OPTIONS] <TARGET>`. Exactly one target is required. Options may precede or follow the target, long options accept `--name=value`, and compatible short boolean options may be combined (for example `-Ijci`, `-Mn`, and `-qi`). `--` ends option parsing, so the next token is the target even if it begins with `-`.

The supported options, with both spellings, are:

- `-a`, `--no-audio`
- `-b VALUE`, `--base-url VALUE`
- `-B`, `--blacklist-domains`
- `-c`, `--no-css`
- `-C FILE`, `--cookie-file FILE`
- repeatable `-d DOMAIN`, `--domain DOMAIN`
- `-e`, `--ignore-errors`
- `-E ENCODING`, `--encoding ENCODING`
- `-f`, `--no-frames`
- `-F`, `--no-fonts`
- `-i`, `--no-images`
- `-I`, `--isolate`
- `-j`, `--no-js`
- `-k`, `--insecure`
- `-m`, `--mhtml`
- `-M`, `--no-metadata`
- `-n`, `--unwrap-noscript`
- `-o FILE`, `--output FILE`
- `-q`, `--quiet`
- `-t INTEGER`, `--timeout INTEGER`
- `-u STRING`, `--user-agent STRING`
- `-v`, `--no-video`
- `-h`, `--help`
- `-V`, `--version`

Boolean flags take no value. A timeout is an unsigned decimal integer in seconds; zero and large values such as 999 are valid. User-agent, base URL, encoding, domain, cookie-file, and output options take exactly one value.

## Spec 2

`-V` and `--version` exit 0, write exactly `monolith 2.11.0\n` to standard output, and write nothing to standard error.

`-h` and `--help` exit 0, write nothing to standard error, end the output with a newline, and produce exactly the following text (the backslashes shown are literal):

```text
 _____    _____________   __________     ___________________    ___
|     \  /             \ |          |   |                   |  |   |
|      \/       __      \|    __    |   |    ___     ___    |__|   |
|              |  |          |  |   |   |   |   |   |   |          |
|   |\    /|   |__|          |__|   |___|   |   |   |   |    __    |
|   | \__/ |          |\                    |   |   |   |   |  |   |
|___|      |__________| \___________________|   |___|   |___|  |___|

monolith 2.11.0

CLI tool and library for saving web pages as a single HTML file

Usage: executable [OPTIONS] <TARGET>

Arguments:
  <TARGET>  URL or file path, use - for STDIN

Options:
  -a, --no-audio                      Remove audio sources
  -b, --base-url <http://localhost/>  Set custom base URL
  -B, --blacklist-domains             Treat specified domains as blacklist
  -c, --no-css                        Remove CSS
  -C, --cookie-file <cookies.txt>     Specify cookie file
  -d, --domain <example.com>          Specify domains to use for white/black-listing
  -e, --ignore-errors                 Ignore network errors
  -E, --encoding <UTF-8>              Enforce custom charset
  -f, --no-frames                     Remove frames and iframes
  -F, --no-fonts                      Remove fonts
  -i, --no-images                     Remove images
  -I, --isolate                       Cut off document from the Internet
  -j, --no-js                         Remove JavaScript
  -k, --insecure                      Allow invalid X.509 (TLS) certificates
  -m, --mhtml                         Use MHTML as output format
  -M, --no-metadata                   Exclude timestamp and source information
  -n, --unwrap-noscript               Replace NOSCRIPT elements with their contents
  -o, --output <result.html>          File to write to, use - for STDOUT
  -q, --quiet                         Suppress verbosity
  -t, --timeout <60>                  Adjust network request timeout
  -u, --user-agent <Firefox>          Set custom User-Agent string
  -v, --no-video                      Remove video sources
  -h, --help                          Print help
  -V, --version                       Print version
```

Help takes effect even when followed by valid flags. An earlier invalid option still causes a parse error; after `--`, `--help` is an ordinary target and does not display help.

## Spec 3

Command-line syntax errors exit 2, put nothing on standard output, and use clap-style diagnostics on standard error. They finish with `For more information, try '--help'.\n`. Relevant exact forms and required phrases are:

```text
error: the following required arguments were not provided:
  <TARGET>

Usage: executable <TARGET>

For more information, try '--help'.
```

An unknown flag reports `unexpected argument '--nonexistent' found`, includes `Usage: executable [OPTIONS] <TARGET>`, and includes `tip: to pass '--nonexistent' as a value, use '-- --nonexistent'`. An extra positional reports `unexpected argument 'extra' found`. A missing option value reports `a value is required` and names that option. A nonnumeric timeout has no `Usage:` block and, for `--timeout invalid`, produces exactly:

```text
error: invalid value 'invalid' for '--timeout <60>': invalid digit found in string

For more information, try '--help'.
```

A bare negative timeout token is treated as an unexpected flag and gets the `use '-- -1'` tip; `--timeout=-1` is parsed as the option value and then rejected as invalid. Supplying `--quiet=true` reports an unexpected value for `--quiet`.

These parse errors are distinct from run-time errors, which exit 1 and do not include the help hint.

## Spec 4

Target selection and loading obey these rules:

- The literal target `-` reads all bytes from standard input. No progress line is emitted merely for reading stdin.
- A nonempty existing filesystem path, absolute or relative to the current directory, is loaded as a local file. An explicit `file://` URL is also supported. Relative file targets and assets are canonicalized to absolute `file://` URLs for resolution and diagnostics.
- A nonempty target with an explicit `http://`, `https://`, or `data:` scheme is loaded using that scheme.
- A target without a scheme which is not an existing local path is interpreted as an HTTP URL (including normal URL normalization such as a root slash), rather than immediately being diagnosed as a missing file.
- The empty string exits 1 with empty stdout and exactly `Error: no target specified\n` on stderr unless quiet mode suppresses it.
- Unsupported target schemes, including `mailto:` and `ftp:`, exit 1. For example `mailto:snshn@tutanota.com` produces exactly `Error: unsupported target URL scheme "mailto"\n`.
- A directory used as the target exits 1 with `Error: local target "PATH" is not a file\n`.
- Failure to retrieve the target itself exits 1, produces no document, and ends its diagnostic with `Error: could not retrieve target document\n`. A nonexistent explicit file URL first logs `file:///... (file not found)`. HTTP target status failures include the status code. Asset failures inside an otherwise loaded HTML document do not by themselves fail the command.

If a successfully retrieved HTTP response is not HTML or XHTML (for example `text/plain`), its response body is passed through unchanged: it is not wrapped, given metadata, or parsed as HTML. Likewise, a non-HTML target such as `data:,Hello%2C%20World!` decodes to the raw bytes `Hello, World!` without an added newline.

## Spec 5

By default the completed archive is written to standard output. `-o -` explicitly selects standard output and behaves identically. A non-`-` output path is created or truncated and receives the complete result; stdout is then empty. An existing file is overwritten, not appended. Ordinary missing parent directories are not created. Failure to prepare the output path is a failure; compatibility with the reference includes the Rust-style exit status 101 and panic diagnostic for `/nonexistent/directory/output.html`, containing `thread 'main' (...) panicked at src/main.rs:` and `could not prepare output: Os { code: 2, kind: NotFound`.

Before opening an output path, replace every occurrence of:

- `%title%` with the document title text, or the empty string if no title exists;
- `%ext%` with `htm` for HTML or `mht` for MHTML;
- `%extension%` with `html` for HTML or `mhtml` for MHTML;
- `%timestamp%` with the current UTC timestamp suitable for a filename.

Multiple placeholders are all replaced. For filenames, sanitize a title colon as ` - `; thus title `Test: File & Data` used in `output-%title%.html` produces `output-Test -  File & Data.html`. Other ordinary title characters, including spaces and `&`, remain. The title inside HTML retains its content and normal HTML escaping.

## Spec 6

Unless `-q` is set, each actual target or asset retrieval writes one line to standard error containing its normalized URL. Local paths are shown as absolute `file://` URLs. Retrieval errors append a parenthesized reason on the same line, such as `(file not found)`, `(is a directory)`, `(security error)`, `(builder error for url (...))`, an HTTP status, or `error sending request for url (...)`. Successful document content never goes to stderr.

`-q` suppresses all such progress and run-time error messages, including fatal run-time diagnostics, without changing success/failure status or document bytes. It does not suppress help/version, parser diagnostics, or the archive when the archive itself is directed to stdout. `NO_COLOR` being set or `TERM=dumb` forces error diagnostics to contain no ANSI escape sequences; diagnostics captured through a non-TTY may also be uncolored.

## Spec 7

HTML input is parsed with forgiving HTML5 tree-building semantics and serialized deterministically. Missing `html`, `head`, or `body` elements are synthesized. Empty input becomes `<html><head>...</head><body></body></html>`. Malformed nesting and unclosed tags are repaired rather than rejected. Doctypes, comments, whitespace text, attributes, tables, forms, framesets, inline SVG, semantic HTML5 elements, and ordinary deep parent/child relationships are preserved. A `template` element is preserved, but its template contents are discarded: `<template><b>inside</b></template>` serializes as `<template></template>`. Preservation of an HTML doctype means preserving its presence and parsed identity, not its source capitalization: an input `<!doctype html>` is canonically serialized as exactly `<!DOCTYPE html>`.

Serialization uses lowercase HTML tag names, double-quoted attribute values, and normal HTML escaping. HTML void elements originating in input (`meta`, `link`, `img`, `input`, `br`, `hr`, `source`, and `frame`) have no slash and no end tag. Boolean attributes serialize with an empty value, for example `controls=""`. A generated robots, CSP, or custom-base node is serialized in the reference form with an explicit end tag (`</meta>` or `</base>`), while a parsed pre-existing void element keeps ordinary void serialization. Preserve source whitespace and raw text as the HTML5 parser does, normalize CR/CRLF to LF in HTML, strip an initial UTF-8 BOM, and terminate processed HTML output with one LF.

Text-only, one-character, whitespace-only, binary-contaminated, or null-containing input must still produce a document. Invalid byte sequences are replaced by U+FFFD under a UTF-8 decode. HTML entities are decoded into the DOM and safely re-escaped on serialization; they must not be double-escaped. Raw script text and CDATA-style markers inside scripts are preserved unless JavaScript is disabled. When embedding external JavaScript, every literal `</script>` in its contents is escaped as `<\/script>` so it cannot close the containing element.

## Spec 8

Every processed HTML document contains exactly one `<meta name="robots" content="none">` in its head. If absent, append a generated node at the end of the head as it exists at that processing stage. A later generated node can therefore follow it: when `-E Utf-8` must add a missing charset declaration to an otherwise empty head, the exact order is `<head><meta name="robots" content="none"></meta><meta charset="Utf-8"></meta></head>`. If an existing robots meta is present (match the `name` value case-insensitively), set its content to `none` instead of adding another; overwrite values such as `index, follow` or empty content.

Unless `-M` is supplied, place a metadata comment before the doctype/document:

```text
<!-- Saved from SOURCE at YYYY-MM-DDTHH:MM:SSZ using monolith v2.11.0 -->
```

For local files and data targets, `SOURCE` is `local source`. Stdin has no source target, so it does not receive this metadata comment even without `-M`. The timestamp is current UTC with whole-second precision. For a network target, use its normalized URL as the source. `-M` suppresses only this generated comment; it does not remove user meta elements. Metadata appears inside the HTML part when MHTML is selected.

## Spec 9

URL resolution follows standard hierarchical URL joining, preserving existing percent escapes, credentials, ports, queries, and fragments:

- A local document uses its containing directory as a `file://` base for resources, anchors, areas, and form actions.
- Stdin/data input has a data-URL base. With no custom base, resolving a relative navigation reference produces `data:,` rather than retaining its relative path/query or gaining local filesystem access. This includes non-ASCII input: stdin `<a href="路径?q=值">x</a>` serializes as `<a href="data:,">x</a>`.
- An existing HTTP(S) `<base href>` controls relative resolution. Except for the empty-value behavior described below and the stdin/file-scheme case in the next bullet, a custom `-b VALUE` takes precedence, replaces the first existing base href or inserts a generated `<base href="VALUE"></base>` at the end of the head, and may name a nonexistent path.
- An empty custom base value is valid. If stdin has no existing base, `-b "" -` inserts `<base href=""></base>` and relative navigation still resolves from the stdin data-URL base. If stdin already contains an HTTP(S) base, the empty custom value replaces that element's serialized href but the original base still controls URL resolution. In particular, `-b "" -` applied to stdin `<base href="http://old/"><a href="next">x</a>` emits `<base href="">` while resolving the anchor as `href="http://old/next"`.
- For local-file documents, an existing relative `<base>` value is itself preserved rather than rewritten, but it is still used where applicable. A custom `file://` base on a file target resolves local relative references. On stdin, a custom file base is inserted but is ignored for resolution as well as retrieval: `-b file:///tmp/ -` applied to `<a href="other.html">` emits `<base href="file:///tmp/"></base>` but resolves the anchor to `href="data:,"`.
- A trailing slash has normal URL meaning: base `http://example.com/dir/` plus `page.html` gives `/dir/page.html`, while base `http://example.com/dir` gives `/page.html`.
- Protocol-relative URLs inherit the applicable base scheme. In particular, a local-file document containing `href="//example.com/path"` serializes that navigation URL as `href="file://example.com/path"`.
- Fragment-only values such as `#section`, and absolute non-fetch navigation schemes such as `mailto:` and `tel:`, remain unchanged. Relative `a[href]`, `area[href]`, and `form[action]` become absolute; a local absolute path `/submit` becomes `file:///submit`.
- `javascript:` anchor/area URLs remain unchanged normally. The `-j` replacement is case-sensitive: replace a URL beginning with the exact lowercase `javascript:` by exactly `javascript:;`, but leave an uppercase value unchanged. Thus under `-j`, `<a href="javascript:go()">` gets `href="javascript:;"` while `<area href="JAVASCRIPT:x">` retains `href="JAVASCRIPT:x"`.

Resource URLs are resolved with the same base before deciding whether they may be retrieved.

## Spec 10

`data:` URLs support both percent-encoded and `;base64` payloads and retain media-type parameters such as `charset=utf-8`. HTML data targets are decoded then processed as HTML. Existing data resources are decoded and canonically embedded using base64 when processed; for example a non-base64 `data:text/html;charset=utf-8,...` image value becomes `data:text/html;charset=utf-8;base64,...`. Already valid base64 data may remain byte-for-byte identical. A fragment after the payload, such as `#my-fragment`, is preserved after re-encoding.

Data and stdin documents may not read local files at all. This includes an explicitly absolute `file://` asset URL; a custom `file://` base does not grant permission. Denial happens before signature or extension media-type detection. Unless `-q` suppresses diagnostics as in Spec 6, every denied fetch attempt writes its own normalized `file:///... (security error)` line to stderr, including repeated attempts for the same URL. The command still exits 0 when the containing document otherwise succeeds.

Apply the ordinary failed-local-fetch transformation for the context. In the exercised stdin cases, an `img` whose `src` is an absolute file URL becomes `<img>`; audio/video/source, iframe, SVG-image, input-image, body-background, stylesheet-link, and external-script fetch attributes are removed; the external script and iframe elements remain (and the script remains empty); an absolute file URL in a CSS value becomes `url()`, and a file `@import` loses its operand. An SVG `use` is different: its absolute file `href` remains and no referenced subtree is inserted. Failed file candidates in `srcset` become the transparent placeholder from Spec 17 while their descriptors remain. An `img[data-src]` value remains present even when its file fetch is denied. These rules also apply inside `noscript`; unwrapping or JavaScript suppression does not grant file access. Empty and whitespace-only frame values retain the behavior in Spec 22.

Because a denied resource was not processed, its `integrity` attribute is not discarded merely because its URL is local. A denied stdin external script becomes empty but retains its integrity attribute. Explicit data resources remain usable in isolation mode and are not subject to domain filtering or the HTTP cache.

## Spec 11

HTTP and HTTPS retrieval follows redirects, normally rejects a non-2xx target response, uses the `-t` timeout for every request, uses `-u` as the User-Agent, and, when `-k` is present, accepts invalid TLS certificates. Proxy-related behavior may follow the standard `http_proxy`, `https_proxy`, and `no_proxy` environment variables.

Within a document, retrieval failures are nonfatal: processing continues. A failed HTTP(S) CSS URL is normally retained so the reference remains recognizable; failed local or unsupported-scheme fetches in fetch-only element contexts generally remove the relevant `src`/`href`. `-e` suppresses/ignores network asset errors and guarantees that missing assets do not make document processing fail. It also accepts an HTTP target response with an error status when a response body was received: an `-e -q` request for a `404` `text/plain` target whose body is `missing` exits 0 and writes exactly `missing` to stdout. Without `-e`, the non-2xx target is rejected as described in Spec 4.

During one invocation, cache successful HTTP(S) asset responses by their complete URL, including empty and large bodies. On the first request log `URL`; on each duplicate reference log `URL (from cache)` while still processing every occurrence. Different URLs have independent entries. Cache behavior is unchanged by timeout or quiet mode; quiet merely hides its lines. Local file and data retrievals do not produce `(from cache)`.

## Spec 12

Domain rules apply to both the initial HTTP(S) target and HTTP(S) asset retrievals, but not to navigation links, `data:`, `file:`, `javascript:`, or other schemes. Each repeatable `-d` contributes an OR-list entry. Without `-B`, the list is an allowlist; with `-B`, it is a blocklist. A filtered asset is not requested and its original absolute URL is left in the output. A filtered initial target is likewise not requested; it exits 1 with no document and, unless quiet, `Error: could not retrieve target document\n`.

Host matching is case-insensitive and ignores the URL port. `example.com` matches that host exactly but not `www.example.com`; `.example.com` matches the root and every depth of subdomain; `.` matches every host. An empty allowlist entry matches nothing (thus blocks all when it is the only allow rule), while an empty blocklist entry blocks nothing. Multiple entries are ORed.

`-I` is not a retrieval filter. With no `-d` entries it still fetches and embeds external HTTP(S) stylesheets, images, scripts, frames, and other resources; it only emits the isolation CSP. If `-I` is combined with one or more `-d` entries, those domain rules independently select the HTTP(S) targets and resources that may be attempted while the isolation CSP is emitted. Local-file and data-resource handling is otherwise unchanged by `-I`.

## Spec 13

`-C FILE` reads a Netscape HTTP cookie file before processing. A valid file begins with the Netscape cookie-file header and contains tab-separated cookie records; it is accepted and its parsed cookies are available to HTTP(S) requests. A missing file exits 1 with `could not read specified cookie file "PATH"\n`. A nonempty malformed file or invalid header exits 1 with a message containing `could not parse specified cookie file`. No archive is written on these failures. Cookie parsing happens independently of stdin/local input so a bad cookie file is still an error even if no network request would be needed.

## Spec 14

Successful retrievable binary resources are represented as `data:MEDIA-TYPE;base64,BASE64`, where BASE64 is the complete resource bytes without truncation. Determine the media type first by a complete, case-sensitive signature at byte offset zero, in this order-compatible mapping:

- `GIF87a` or `GIF89a` -> `image/gif`
- bytes `FF D8 FF` -> `image/jpeg`
- bytes `89 50 4E 47 0D 0A 1A 0A` -> `image/png`
- literal bytes `<svg ` -> `image/svg+xml`
- literal bytes `RIFF....WEBPVP8 ` -> `image/webp`
- bytes `00 00 01 00` -> `image/x-icon`
- `ID3`, bytes `FF 0E`, or bytes `FF 0F` -> `audio/mpeg`
- `OggS` -> `audio/ogg`
- literal bytes `RIFF....WAVEfmt ` -> `audio/wav`
- `fLaC` -> `audio/x-flac`
- literal bytes `RIFF....AVI LIST` -> `video/avi`
- literal bytes `....ftyp` -> `video/mp4`
- bytes `00 00 01 0B` -> `video/mpeg`
- literal bytes `....moov` -> `video/quicktime`
- bytes `1A 45 DF A3` -> `video/webm`

The dots in the listed signatures are four actual ASCII full-stop bytes, not wildcards. A partial signature or a signature later in the file does not match. For a retrieved HTTP(S) resource without a recognized signature, prefer the response's media type to an extension fallback. In particular, an empty `/empty.png` response served as `application/octet-stream` becomes `data:application/octet-stream;base64,`, not `data:image/png;base64,`; repeated uses still follow the successful-response cache rules in Spec 11. Otherwise, if no signature or response media type determines the type, fall back to the URL/file extension. Recognize `.png`, `.jpg`/`.jpeg`, `.gif`, `.webp`, `.svg`, `.ico`, `.mp3`, `.ogg`, `.wav`, `.avi`, and `.mp4` with the types shown above; `.flac` is an extension-fallback exception and produces `audio/flac` rather than the signature type `audio/x-flac`. For resources to which extension fallback applies, it applies even to empty/tiny/wrong-magic files. The `.mpg`, `.mpeg`, `.mov`, and `.webm` extensions are not recognized as fallbacks: a one-byte `?` file under each of those names becomes `data:;base64,Pw==`. Other unknown data likewise uses an empty type: `data:;base64,...`.

## Spec 15

Stylesheet processing is recursive and lossless apart from specified rewrites:

- A successfully fetched `<link rel="stylesheet" href="...">` keeps the link and replaces `href` with `data:text/css;base64,` plus the base64 of the fully processed stylesheet.
- Inline `<style>` content and `style` attributes are processed too.
- Every `@import` spelling—quoted, `url('...')`, `url("...")`, or unquoted—is resolved relative to the stylesheet that contains it, fetched, recursively processed, and replaced by a `data:text/css;base64,...` URL. Nested import chains of at least three levels must work. Each occurrence is retained, even when duplicate and served from cache.
- Preserve an `@charset` rule and the ordinary contents of large stylesheets. A URL fragment on an imported resource is appended after the embedded data URL.
- Empty imports are accepted: `@import url("");` normalizes to `@import url('');`; the empty forms `url()`, `url("")`, and `url('')` used as values normalize to `url()`.
- If a local quoted import cannot be read, log the error and leave an empty import operand (`@import ;`). If an HTTP(S) import cannot be retrieved, retain its absolute URL, with URL-function output normalized to double quotes. The same preserve-on-network-failure rule applies to ordinary HTTP(S) `url(...)` property values; failed local ordinary values become `url()` where no safer original value is applicable.

Do not treat fragment-only CSS URLs such as `url(#gradient)` as fetches; retain them exactly. Preserve a fragment on an embedded image URL.

## Spec 16

The CSS parser/serializer must tolerate malformed input and retain valid material following bad tokens. Preserve comments and whitespace, CDO/CDC (`<!--` and `-->`), color hashes, ID hashes, delimiters, unexpected close tokens, strings, escapes, Unicode selectors, empty rules, and explicit positive signs on numbers, dimensions, and percentages (`+5`, `+0`, `+10px`, `+50%`, `+0.8`). Preserve all attribute-selector operators (`~=`, `|=`, `^=`, `$=`, `*=`), chained/nested square brackets, parentheses, and nested functions such as `rotate(calc(...))`, gradients containing `rgba(...)`, `var(...)`, `minmax(...)`, and `@supports (...) and (...)`.

Bad URL/bad string tokens and unmatched braces must not crash processing; keep whatever surrounding CSS the tolerant parser can recover. URL rewriting must visit every occurrence, including multiple URLs in one declaration and URLs in custom properties. For failed unquoted network URLs, normalized output uses `url("ABSOLUTE_URL")`.

## Spec 17

Normal image handling embeds retrievable content and preserves layout elements:

- Process `img[src]`, preferring and likewise processing `img[data-src]` when present; `input[type=image][src]`; `video[poster]`; `body[background]`; favicon/icon links; SVG `image[href]` and `image[xlink:href]`; and image candidates in `img[srcset]` and `picture source[srcset]`.
- Parse comma-separated `srcset` candidates and retain each original density/width descriptor (`1x`, `2x`, `480w`, `1024w`) after replacing its URL. Preserve query strings and fragments.
- For an SVG `<use href="icons.svg#id">` or `xlink:href`, retrieve and parse the SVG, retain the `<use>` with a fragment-only href, and insert the referenced symbol inside it. On the inserted symbol root, preserve `id` but discard every other root attribute, including `viewBox`, `class`, and `fill`; preserve its descendants and their attributes. Without a fragment, insert the complete referenced SVG contents inside the use element. SVG image references instead become base64 data URLs.
- `body[background]` and video poster resources become data URLs on success. A failed ordinary local media source has its fetch attribute removed, rather than keeping a broken relative path.

When `-i` is active, do not remove `img`, `input`, `picture`, or video layout. Replace every image source/candidate/poster/data-src with exactly this transparent placeholder, including an explicitly empty `src=""`:

```text
data:image/png,%89PNG%0D%0A%1A%0A%00%00%00%0DIHDR%00%00%00%0D%00%00%00%0D%08%04%00%00%00%D8%E2%2C%F7%00%00%00%11IDATx%DAcd%C0%09%18G%A5%28%96%02%00%0A%F8%00%0E%CB%8A%EB%16%00%00%00%00IEND%AEB%60%82
```

For an `img` srcset, replace every candidate URL separately and retain descriptors. For a `picture source[srcset]`, a single/multiple source may collapse to the placeholder as exercised by the reference serializer. Remove `body[background]`. Clear all child nodes of inline `<svg>` while preserving the SVG container. Add the image CSP described later. These placeholder transformations apply when `-i` is active; in normal mode an unsupported FTP image fetch removes the fetch attribute instead. For example, `<img src="ftp://example.test/p.png">` becomes `<img>` and logs `ftp://example.test/p.png (builder error for url (ftp://example.test/p.png))`.

## Spec 18

CSS image suppression under `-i` replaces each `url(...)` in an image-bearing property with the same transparent PNG URL from Spec 17. Image-bearing properties include `background`, `background-image`, `border-image`, `border-image-source`, `content`, `cursor`, `list-style`, `list-style-image`, `mask`, and `mask-image`, plus the `@counter-style` properties `additive-symbols`, `negative`, `pad`, `prefix`, `suffix`, and `symbols`. Replace every URL occurrence in shorthands and comma-separated values.

Do not blindly replace URLs in other properties. For example, retain the internal reference in `clip-path: url(#my-clip)`, and process a URL occurring in an otherwise non-image property by normal retrieval/failure rules. Quote style may normalize, but the CSS structure around rewritten values remains intact.

## Spec 19

JavaScript behavior is:

- Normally preserve inline scripts. Fetch a retrievable external `script[src]`, remove its `src`, and put the decoded script bytes inline. Decode data-URL scripts similarly. Escape embedded closing-script sequences as described in Spec 7.
- With `-j`, preserve every script element but remove `src` and empty all its contents. Remove every HTML event-handler attribute (attributes whose name begins with `on`, including `onclick`) and replace `javascript:` navigation URLs as described in Spec 9. Add `script-src 'none';` to CSP.
- MHTML mode implies the same JavaScript disabling even without an explicit `-j`.

## Spec 20

CSS/font filtering behaves as follows:

- With `-c`, preserve `<style>` elements as empty `<style></style>`, preserve stylesheet `<link>` elements but remove their `href`, and remove every inline `style` attribute. Do not remove unrelated document structure. Add `style-src 'none';` to CSP.
- With `-F`, remove each entire `@font-face { ... }` block while retaining all other CSS rules, even rules that continue to refer to the font-family name. Also suppress fetches of font resources/preloads as appropriate. Add `font-src 'none';` to CSP. A stylesheet consisting only of a font-face rule becomes empty.

These filters apply to inline CSS, external CSS before it is base64 encoded, nested imported CSS, and CSS found in noscript content.

## Spec 21

Audio and video resources are embedded as typed base64 data URLs in normal mode, both from a media element's own `src` and from child `<source src>` elements. Preserve the media and source elements, fallback text, `type`, `controls`, and other non-fetch attributes.

With `-a`, remove the `src` attribute from every `<audio>` and each of its `<source>` children, leaving the elements. With `-v`, do the same for `<video>` and its source children. The `-v` flag alone does not suppress `poster`; the poster is still processed by the normal image rules. In particular, for stdin `<video src="v" poster="p"><source src="s"></video>`, `-v` produces `<video poster="data:text/plain;base64,"><source></video>`. When `-v` and `-i` are combined, replace each nonempty poster with the transparent image placeholder instead. These media flags add no separate CSP directive.

## Spec 22

Frames and embedded documents are processed recursively. A retrievable `iframe[src]` or `frame[src]` becomes `data:text/html;base64,...` containing a complete processed HTML document. Multiple frames are embedded independently, including their own styles/titles. Empty and whitespace-only iframe src values remain exactly empty/whitespace rather than being fetched.

With `-f`, keep iframe/frame elements and their inner fallback content but set each existing `src` to the empty string. Add both `frame-src 'none';` and `child-src 'none';` to CSP. Object `data` and embed `src` references must at least be processed safely under the same general retrieval rules and may be embedded when retrievable.

## Spec 23

By default, preserve `<noscript>` start/end tags and parse their contents as markup, including recursively processing images, links, and nested noscript elements. An inline `<style>` encountered inside preserved noscript markup is discarded together with its contents rather than processed or serialized. For the exact input `<noscript><style>.x{background:url(data:,a)}</style><img src="data:,b"><noscript>deep</noscript></noscript>`, both noscript elements and the processed image remain, but no style element or `data:text/plain;base64,YQ==` remains. This behavior remains in effect under `-j`.

With `-n`, replace every opening tag by an HTML comment and every close tag by a closing comment, preserving all children in place. A tag without attributes becomes `<!--noscript-->...<!--/noscript-->`; attributes are retained in the opening marker, for example `<noscript class="">test</noscript>` becomes `<!--noscript class=""-->test<!--/noscript-->`. Apply this at every nesting depth and combine it normally with `-j` and other filters.

## Spec 24

Subresource Integrity is honored on fetchable stylesheet and script resources for `sha256-`, `sha384-`, and `sha512-` base64 digests. A single well-formed matching digest for any of those algorithms embeds the resource. A mismatch leaves the resource external and does not insert its content. In the exercised script cases, an unknown-only integrity value such as `md5-unknown` also blocks ordinary embedding and leaves the resource external. If an earlier supported digest token is malformed or mismatching, a later matching token does not rescue it; a malformed SHA-256 token followed by a matching SHA-384 token leaves the script external, while a lone matching SHA-512 digest embeds it. In each of these processed HTTP script cases, remove the `integrity` attribute whether embedding succeeds or the external URL remains. Preserve unrelated attributes, such as `crossorigin="anonymous"`, on an embedded element.

For successfully processed local-file resources, discard `integrity`; it must not remain after the local resource is embedded. In contrast, an already embedded data URL retains its `integrity` attribute unchanged: `<img src="data:image/png;base64,eA==" integrity="wrong">` remains exactly so after processing. A local-file URL denied by the stdin/data-origin rule in Spec 10 was not processed and retains integrity as described there.

## Spec 25

Apply these additional HTML safety/link transformations:

- For `<meta http-equiv="refresh">` and `<meta http-equiv="location">` (case-insensitive), remove the `http-equiv` attribute but keep the meta element and its `content`. Preserve other http-equiv values such as `content-type`.
- On a link whose rel is `preload`, remove the entire `rel` attribute to prevent the browser request, even when the value also contains another token: `rel="alternate preload"` produces a link with no `rel`, rather than `rel="alternate"`. A `dns-prefetch` link likewise loses its rel attribute. Leave the element and attributes such as `as`, `type`, and `href`. Preserve `prefetch`, `alternate` when not combined with `preload`, and ordinary stylesheet relations subject to their respective processing.
- Process the href of `rel="icon"`, `rel="shortcut icon"`, and `rel="apple-touch-icon"` as an image where applicable, and keep the link even when retrieval fails. Only `icon` and `shortcut icon` count as explicit icon declarations for suppressing the automatic `/favicon.ico` request. A page whose only such link is `rel="apple-touch-icon"` still triggers one automatic `/favicon.ico` request.
- If and only if the initial target is HTTP(S), no explicit icon relation exists, and images are enabled, request `/favicon.ico` at the target origin. On success append one `<link rel="icon" href="data:...">`; on failure add nothing and do not fail. Never auto-fetch a favicon for a file, stdin, or data target, even if stdin has an HTTP base URL.

## Spec 26

When any relevant restriction is active, create one generated head meta element with `http-equiv="Content-Security-Policy"`. Its `content` is the concatenation of applicable directives in this exact order and punctuation:

1. `-I`: `default-src 'unsafe-eval' 'unsafe-inline' data:;`
2. `-c`: `style-src 'none';`
3. `-F`: `font-src 'none';`
4. `-f`: `frame-src 'none'; child-src 'none';`
5. `-j`, or implied by `-m`: `script-src 'none';`
6. `-i`: `img-src data:;`

Separate adjacent directives with one space. For example, all relevant flags yield exactly `default-src 'unsafe-eval' 'unsafe-inline' data:; style-src 'none'; font-src 'none'; frame-src 'none'; child-src 'none'; script-src 'none'; img-src data:;`. Insert this generated meta as the first child of the head, before source head contents. `-I` alone does not delete inline styles/scripts, existing data URLs, or fetched external content; it adds this CSP but does not block retrieval.

## Spec 27

Character decoding and encoding are document-aware. Detect an initial UTF-8 BOM, an initial UTF-16LE BOM, and charset declarations in `<meta charset="...">` or `<meta http-equiv="Content-Type" content="...; charset=...">`; the first applicable declaration wins. Support at least UTF-8 aliases/casing (`utf8`, `UTF-8`, `Utf-8`), GB2312, ISO-8859-1, and Windows-1252. Preserve the spelling/case of an input declaration when no override is requested, including `GB2312` and `iso-8859-1`, and correctly decode text represented by that encoding. With no `-E` override, encode ordinary output using the detected input encoding: declared ISO-8859-1 emits `café` with byte `E9`, declared Windows-1252 emits the euro sign with byte `80`, and declared GB2312 emits `中文` with bytes `D6 D0 CE C4`, rather than transcoding those outputs to UTF-8.

UTF-16 input is an output exception. For bytes `FF FE` followed by the UTF-16LE encoding of `<meta charset="UTF-16"><p>Omega Ω</p>`, detect and decode the UTF-16LE input, retain `<meta charset="UTF-16">`, recover `Omega Ω`, and emit the processed document as UTF-8 bytes without a BOM (`Ω` is `CE A9`).

`-E NAME` is case-insensitive for lookup, updates the first charset declaration (or inserts `<meta charset="NAME">` if none exists), and preserves the supplied spelling in that declaration. It selects the output encoding but does not override input decoding: the source declaration/detection is applied first. Thus Latin-1 bytes declared as UTF-8 become U+FFFD before `-E iso-8859-1` is applied and serialize as `&#65533;`, not as the original byte E9. Ordinary HTML output uses the requested encoding, with unrepresentable characters emitted as numeric references; requested UTF-16 is an output exception and emits UTF-8 bytes without a BOM while declaring the requested `utf-16` spelling. `-E` works with both `-M` and `-m`, but MHTML byte encoding follows the separate rule in Spec 28. Invalid names exit 1 with no document and exactly `Error: unknown encoding "NAME"\n` for the canonical error path.

Preserve Unicode text across HTML, CSS, and JavaScript, including supplementary emoji, CJK, Arabic/Hebrew RTL, Cyrillic, Greek, and mathematical symbols. URL attributes are still subject to Spec 9 resolution: in particular, the non-ASCII path and query in stdin `href="路径?q=值"` are replaced by `href="data:,"`, not preserved as URL content. Do not truncate long multibyte content. Invalid input byte sequences are handled with replacement characters rather than causing a crash.

## Spec 28

With `-m`, first apply all normal HTML processing and implicitly disable JavaScript, then wrap the single resulting HTML document in this deterministic one-part MHTML envelope. Use CRLF for MIME lines and boundaries, the fixed boundary `----=_NextPart_000_0000`, the fixed lowercase MIME charset label `utf-8`, and the compatibility content location `http://example.com/`:

```text
MIME-Version: 1.0\r\n
Content-Type: multipart/related; boundary="----=_NextPart_000_0000"\r\n
\r\n
------=_NextPart_000_0000\r\n
Content-Type: text/html; charset="utf-8"\r\n
Content-Location: http://example.com/\r\n
\r\n
PROCESSED_HTML\r\n
------=_NextPart_000_0000--\r\n
```

There are no separate asset parts because resources have already become data URLs. The output begins exactly with `MIME-Version: 1.0\r\n` and ends exactly with the closing boundary plus CRLF. The fixed MIME charset label does not force the HTML payload to UTF-8: an explicit `-E` selects the payload byte encoding just as it does for ordinary HTML. With `-m -E ISO-8859-1`, the part header remains `Content-Type: text/html; charset="utf-8"`, the document contains `<meta charset="ISO-8859-1"></meta>`, and `café` is encoded with ISO-8859-1 bytes `63 61 66 E9`, not UTF-8. `-M` controls the metadata comment inside the HTML part exactly as in HTML mode.

## Spec 29

Processing must be robust and complete rather than size-limited or recursion-fragile. It must handle in reasonable command-line execution time at least: a one-megabyte stdin document; 10,000 HTML elements; 2,000 paragraphs; 100 levels of DOM nesting; 50 explicitly identified nested levels; a 120,000-character single line; 12,000-character attributes and data URLs; 1,500 CSS rules; several independently embedded styles/scripts/images/frames/media resources; malformed and unclosed HTML/CSS; mixed line endings; empty assets; and repeated resources. Preserve all element counts, IDs, classes, text, comments, attribute values, and complete base64 payloads. Malformed content within these limits must not cause a crash, hang, arbitrary truncation, or loss of later valid content.
