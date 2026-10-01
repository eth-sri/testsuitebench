# Website link-checker executable

The required artifact is a runnable command-line program named exactly `executable`. It checks links found in an HTTP or HTTPS HTML page, optionally crawls additional pages, and reports broken links. All behavior required to implement it is defined below.

## Spec 1

`executable` is a command-line program with the synopsis `executable [options] <url>`. Exactly one positional URL is required for an ordinary check. Options may precede or follow the URL. Options that take a value must accept both `--option=value` and `--option value`; short value options must likewise accept forms such as `-b=4096` and `-b 4096`. Repeatable options retain every occurrence.

An ordinary successful check exits 0. A check exits 1 if the root page cannot be fetched or parsed as a page, any checked link fails, an HTTP status is not accepted, or command-line validation fails. Diagnostics caused before a page can be checked go to standard error. Link-check reports in any selected report format go to standard output. Except for the selected report and defined diagnostics, the program must not print logging or progress messages.

## Spec 2

`-h` and `--help` print the following text verbatim to standard output, including the final newline, print nothing to standard error, and exit 0. Help takes precedence over positional-argument validation and valid options: for example, both `foo --help` and `--verbose --help` show help successfully rather than reporting another error. It does not override an option-parsing error encountered earlier in the argument list. In particular, `executable --not-a-real-option --help` exits 1, writes nothing to standard output, and writes exactly ``unknown flag `not-a-real-option'\n`` to standard error.

```text
Usage:
  executable [options] <url>

Application Options:
      --accepted-status-codes=<codes>       Accepted HTTP response status codes
                                            (e.g. '200..300,403') (default:
                                            200..300)
  -b, --buffer-size=<size>                  HTTP response buffer size in bytes
                                            (default: 4096)
  -c, --max-connections=<count>             Maximum number of HTTP connections
                                            (default: 512)
      --max-connections-per-host=<count>    Maximum number of HTTP connections
                                            per host (default: 512)
      --max-response-body-size=<size>       Maximum response body size to read
                                            (default: 10000000)
  -e, --exclude=<pattern>...                Exclude URLs matched with given
                                            regular expressions
  -i, --include=<pattern>...                Include URLs matched with given
                                            regular expressions
      --follow-robots-txt                   Follow robots.txt when scraping
                                            pages
      --follow-sitemap-xml                  Scrape only pages listed in
                                            sitemap.xml (deprecated)
      --header=<header>...                  Custom headers
  -f, --ignore-fragments                    Ignore URL fragments
      --max-retries=<count>                 Maximum retry count for network
                                            errors (default: 0)
      --dns-resolver=<address>              Custom DNS resolver
      --format=[text|json|junit]            Output format (default: text)
      --json                                Output results in JSON (deprecated)
      --experimental-verbose-json           Include successful results in JSON
                                            (deprecated)
      --junit                               Output results as JUnit XML file
                                            (deprecated)
  -r, --max-redirections=<count>            Maximum number of redirections
                                            (default: 64)
      --rate-limit=<rate>                   Max requests per second
  -t, --timeout=<seconds>                   Timeout for HTTP requests in
                                            seconds (default: 10)
  -v, --verbose                             Show successful results too
      --proxy=<host>                        HTTP proxy host
      --skip-tls-verification               Skip TLS certificate verification
      --one-page-only                       Only check links found in the given
                                            URL
      --color=[auto|always|never]           Color output (default: auto)
  -h, --help                                Show this help
      --version                             Show version
```

## Spec 3

`--version` prints only a semantic version of the form `MAJOR.MINOR.PATCH` followed by a newline, prints nothing to standard error, and exits 0. Each component is decimal digits; a fixed implementation version such as `2.10.2` is acceptable.

With neither help nor version selected, zero positional URLs or more than one positional URL is an error. It exits 1, leaves standard output empty, and writes a diagnostic containing `invalid number of arguments` to standard error.

An unknown long option exits 1 and identifies the option without its leading dashes, in the form `unknown flag `name'`; for example, `--nonexistent-flag` must yield text containing ``unknown flag `nonexistent-flag'``. A malformed or unsupported root URL must not crash; it exits 1 with a standard-error message containing `failed` or `error` and describing the URL/fetch failure. Specifically, `executable not-a-url` exits 1, leaves standard output empty, and writes exactly `failed to fetch root page: missing port in address\n` to standard error. A refused connection diagnostic must contain `failed` and/or `connect`, identify the address or port, and contain `connection refused` when that is the operating-system error.

## Spec 4

The accepted option surface is exactly the one documented in Spec 2. In particular, these aliases are supported: `-b` for `--buffer-size`, `-c` for `--max-connections`, `-e` for `--exclude`, `-i` for `--include`, `-f` for `--ignore-fragments`, `-r` for `--max-redirections`, `-t` for `--timeout`, and `-v` for `--verbose`. `--json` selects JSON output and `--junit` selects JUnit output even though both are deprecated. `--experimental-verbose-json`, when used with JSON output, requests inclusion of successful results.

Integer syntax is required for buffer size, connection counts, timeout, and redirection count. `--max-retries` is an unsigned integer. A negative value supplied as the next argument is parsed as an option rather than as the value: `executable --max-retries -1 http://example.com` exits 1, leaves standard output empty, and writes exactly ``expected argument for flag `--max-retries', but got option `-1'\n`` to standard error. In the attached-value form, `executable --max-retries=-1 http://example.com` exits 1, leaves standard output empty, and writes exactly ``invalid argument for flag `--max-retries' (expected uint): strconv.ParseUint: parsing "-1": invalid syntax\n`` to standard error. Other type errors identify the option's complete alias label and expected type, even when the invocation uses only its long name. These invocations each exit 1, leave standard output empty, and produce the following exact standard-error text:

```text
executable --buffer-size abc http://example.com
invalid argument for flag `-b, --buffer-size' (expected int): strconv.ParseInt: parsing "abc": invalid syntax

executable --max-connections abc http://example.com
invalid argument for flag `-c, --max-connections' (expected int): strconv.ParseInt: parsing "abc": invalid syntax

executable --timeout abc http://example.com
invalid argument for flag `-t, --timeout' (expected int): strconv.ParseInt: parsing "abc": invalid syntax
```

Each diagnostic line has a final newline. Boolean flags do not take values, so a form such as `--follow-robots-txt=http://example.com` reports that the flag `cannot have an argument`.

`--format` accepts only `text`, `json`, or `junit`. For every unsupported value `VALUE`, it exits 1, leaves standard output empty, and writes ``Invalid value `VALUE' for option `--format'. Allowed values are: text, json or junit\n`` to standard error, with the actual supplied value substituted for `VALUE`. For example, `--format=invalidformat` writes exactly ``Invalid value `invalidformat' for option `--format'. Allowed values are: text, json or junit\n``. `--color` similarly accepts only `auto`, `always`, or `never`, and invalid value `wat` produces `Invalid value `wat' for option `--color'`. Verbose output and JUnit are mutually exclusive: `-v --format=junit` (and the corresponding deprecated JUnit form) exits 1 with `verbose option not supported for JUnit output` on standard error.

## Spec 5

Before crawling, fetch the exact positional root URL with an HTTP GET, following the request rules in later sections. The URL may use `http` or `https`, a hostname such as `localhost`, an IPv4 address, a port, a path, query parameters, and/or a fragment. URL fragments are never sent in the HTTP request itself.

The root response must have an accepted status and an HTML content type in order to be scraped. A root status failure is fatal rather than a page-result entry: for a root 404, exit 1, write exactly `failed to fetch root page: 404\n` to standard error, and write nothing to standard output. Network root failures use the prefix `failed to fetch root page: ` followed by the underlying error. A successful non-HTML root, such as `image/png`, exits 1 with a standard-error diagnostic containing `invalid content type`. A valid HTML root with no links succeeds; in verbose text mode it still prints the root URL as a page heading.

## Spec 6

Scrape the root HTML and check every distinct eligible URL found on that source page. A check means performing an HTTP GET, following redirects, and classifying the final result. By default, successfully fetched HTML links are also scraped recursively, and their links are checked in the same manner. Continue to arbitrary depth until there are no new crawlable pages.

Every successfully fetched HTML resource may become a recursively scraped page, including an HTTP(S) resource on an origin different from the root. For example, if the root links to cross-origin HTML `/external` and that page links to `/hidden` on its own origin, both `/external` and `/hidden` are requested and each becomes a source-page section in verbose output. Non-HTML resources are checked but not scraped. Maintain a visited-page set so cycles terminate and each page appears at most once as a source-page section. The same target discovered on different source pages may still appear once in each source page's link results.

`--one-page-only` disables all recursive scraping: it still fetches the root and checks every eligible link directly present in the root, but never extracts links from those targets.

## Spec 7

For HTML link discovery, recognize at least all of the following:

- `href` on `a` elements;
- `src` on `img`, `script`, `iframe`, `source`, and `track` elements;
- `href` on ordinary resource `link` elements;
- comma-separated URLs in `srcset` on `source`, with descriptors such as `480w` or surrounding whitespace removed;
- `content` on `meta property="og:image"` and `meta property="twitter:image"`.

Do not check `<link rel="preconnect">` or `<link rel="dns-prefetch">` connection hints. Silently ignore empty references and non-web schemes such as `data:`, `mailto:`, `javascript:`, `tel:`, and `ftp:`. Eligible schemes are `http`, `https`, ordinary relative references, root-relative references, and scheme-relative HTTP(S) references.

An `img` element's ordinary `src` is discovered, but its `srcset` candidates are not discovered. Thus `<img src="i" srcset="one 1x, two 2x">` checks `i` only, whereas `<source srcset="three 480w">` checks `three`.

Resolve relative references according to normal URL resolution: `page2`, `./sibling.html`, `../index.html`, and `/about.html` resolve against the source page. If the document contains a valid `<base href>`, use it as the base for all relative and root-relative references; for example, with base `http://example.com/subdir/`, `page.html` becomes `http://example.com/subdir/page.html` and `/root.html` becomes `http://example.com/root.html`.

A malformed discovered URL is a failed link, not a process crash and not a fatal root error. It is reported alongside other link results. For the discovered string `http://[invalid`, its error text is exactly `parse "http://[invalid": missing ']' in host`, and valid links in the same document are still checked.

## Spec 8

Fragments are significant by default. For a link to `page.html#section`, fetch `page.html` and verify that the returned HTML contains the fragment target as an element identifier. A present target is a successful link reported under the original URL including `#section`; a missing target is a failed link and causes exit 1. Same-document fragments and fragments on another page are both supported.

`-f`/`--ignore-fragments` disables fragment-target validation. Fragment-bearing references with the same underlying URL share one HTTP fetch, so a missing identifier alone cannot fail the check. Reporting is not deduplicated by that fetch URL: each distinct original resolved reference remains a separate result under its fragment-bearing URL. For example, links to `/p#missing` and `/p#other` cause one request for `/p` but, in verbose text mode, produce separate successful rows ending in `/p#missing` and `/p#other`. The short and long flag forms behave identically.

## Spec 9

`-e`/`--exclude` and `-i`/`--include` take repeatable regular expressions. Compile every expression before any network work. An invalid expression exits 1. For the pattern `[invalid(regex`, after removal of any unrelated runtime warnings, the diagnostic is exactly:

```text
error parsing regexp: missing closing ]: `[invalid(regex`
```

Apply expressions as case-sensitive searches against the complete resolved URL string, including scheme, host, port, path, query, and fragment. They are regex searches, not literal or whole-string comparisons, so `api` matches any URL containing `api`, `\d+` and character classes work, and `^`/`$` anchors retain their normal meanings.

With no include expressions, every otherwise eligible URL is included. With one or more includes, a URL is eligible if any include matches. A URL is excluded if any exclude matches. When both kinds are present, the rule is `(matches any include) AND NOT (matches any exclude)`, so exclusion wins. Filtered URLs are silently omitted: do not request, report, or crawl them. The positional root itself is always fetched and scraped regardless of whether it matches the link filters.

## Spec 10

The default accepted HTTP status set is the half-open range `200..300`, meaning 200 through 299. `--accepted-status-codes=<codes>` replaces that set. Its value is a comma-separated union of decimal single codes and half-open `start..end` ranges. Thus `200..300,403`, `200,418`, and `200..300,400..500` are valid; the last range accepts 400 through 499 but not 500. Accepted unusual statuses such as 403, 404, or 418 count as successful checks and are displayed with their actual numeric status in verbose reports.

An unaccepted final status is a failed link whose error text is the decimal status, such as `404` or `500`. Check and report all links even after one fails. Malformed status syntax fails before crawling. The diagnostic for `200...300` is exactly `invalid status code: .300\n`. A wholly nonnumeric token is echoed in the diagnostic ``invalid status code range: TOKEN\n``; for example, `abc` produces exactly `invalid status code range: abc\n`, and `notanumber` produces exactly `invalid status code range: notanumber\n`.

A syntactically formed `start..end` range is accepted even when `start >= end`; it contributes no accepted codes. It is not rejected during argument parsing. Consequently, both `--accepted-status-codes 300..200` and `--accepted-status-codes 200..200` proceed to fetch the root. Against an HTML root returning 200, either invocation exits 1, leaves standard output empty, writes exactly `failed to fetch root page: 200\n` to standard error, and has made the root request.

## Spec 11

Follow HTTP redirects for both the root and checked links. Support absolute and relative `Location` values and status codes 301, 302, 303, 307, and 308; a successful redirect chain is classified by its final response, and intermediate redirects are not separate link results. For 307 and 308, preserve the GET method.

The default redirect limit is 64 and `-r`/`--max-redirections` changes it. A limit of zero rejects the first redirect; a positive limit permits at most that many hops. If the limit is exceeded, the original checked URL is a failed link with error text `too many redirections`. A 3xx response without a `Location` header is a failed link with error text `location header not set`. These failures use the normal page-result format and cause exit 1.

## Spec 12

`-t`/`--timeout` is a per-request timeout in seconds, with default 10. A checked link that does not respond within the limit is a failed link with error text `timeout`; for example, a slow link discovered in a page is rendered as `\ttimeout\t<slow-url>` in text output. A normal quick response must not time out under `--timeout=10`.

`--header=<name>: <value>` is repeatable. Validate that every header contains a colon; otherwise exit 1 and write exactly `invalid header format\n` to standard error. Send all supplied headers on the root request, special robots/sitemap requests, checked links, redirects, and recursively scraped pages. Header values may contain spaces. In particular, a custom `User-Agent` must replace or override the default request header and multiple differently named headers must all be transmitted.

The following network options must be parsed and honored without changing ordinary link-check semantics: `--buffer-size` (default 4096), `--max-connections` (default 512), `--max-connections-per-host` (default 512), `--max-response-body-size` (default 10000000), `--max-retries` (default 0), `--rate-limit`, `--dns-resolver`, `--proxy`, and `--skip-tls-verification`. Connection limits bound concurrency, rate limit is a maximum requests-per-second setting, buffer/body settings govern response reading, retry count applies to network errors, a custom resolver/proxy is used when supplied, and TLS certificate validation is disabled only with the skip flag. Settings may be freely combined with timeout, status, and redirect options. If proxy-host resolution fails while fetching the root, the diagnostic identifies the supplied proxy hostname. For example, `--proxy=http://proxy.example.com:8080 http://localhost:19999` exits 1 with empty standard output and a `failed to fetch root page: ` diagnostic containing `proxy.example.com`.

## Spec 13

The default `text` format and explicit `--format=text` are identical. A source-page section has this grammar:

```text
<source-page-url>
\t<status-or-error>\t<resolved-link-url>
\t<status-or-error>\t<resolved-link-url>
```

Every line ends with a newline. Numeric accepted responses use their decimal status. Failures use their error text, including HTTP codes, `timeout`, `too many redirections`, `location header not set`, or a URL parse error.

Without `-v`/`--verbose`, suppress accepted link results and suppress any page section that consequently has no reportable failures. Thus an entirely valid site produces empty standard output. With verbose enabled, include accepted and failed links and show every scraped source page, even a page with no links. Within each section, put successful numeric-status results first sorted lexicographically by resolved URL, followed by failed results sorted lexicographically by resolved URL. The root section is emitted first when it has reportable results; scheduling may otherwise affect the ordering of distinct recursively crawled page sections.

For example, a root page containing one valid `/ok` and one missing `/missing` produces only the following in non-verbose mode and exits 1:

```text
http://host/root
\t404\thttp://host/missing
```

In verbose mode its successful line `\t200\thttp://host/ok` precedes the failure line.

## Spec 14

`--format=json` writes valid JSON to standard output and no text report to standard error. The top-level value is an array of source-page result objects. A source-page object has string field `url` containing the source page URL and array field `links`. In non-verbose JSON, `links` contains failed links only. Each failed link is an object with string fields `url` and `error`; for example, a missing URL is represented as `{"url":"http://host/missing","error":"404"}`. A page with one failure therefore has the form:

```json
[{"url":"http://host/root","links":[{"url":"http://host/missing","error":"404"}]}]
```

In verbose JSON (`--format=json --verbose`, or JSON with `--experimental-verbose-json`), successful checks are included as well, and successful crawled pages are not all suppressed. The result remains an array of objects with a source URL and its link results. JSON must remain syntactically valid even when link checks fail. `--json` is a backward-compatible synonym for non-verbose `--format=json`. Broken links still cause exit 1; an all-success run exits 0.

## Spec 15

`--format=junit` writes a JUnit-style XML document beginning exactly with:

```xml
<?xml version="1.0" encoding="UTF-8"?>
```

The root element is `<testsuites>`. Create one `<testsuite>` for each reported source page, with `name` equal to that page URL, `tests` equal to the number of checked links represented, and `failures` equal to the number of failed links. Create one `<testcase>` per represented link, with `name` equal to the resolved target URL and `classname` equal to its source page URL. A failed testcase contains `<failure message="ERROR"></failure>`, where `ERROR` is the same error text used in text/JSON output; a successful testcase has no failure child. XML-escape all dynamic strings.

JUnit represents successful as well as failed checked links even though ordinary non-verbose text/JSON suppress successes. A page with three missing links therefore has one suite with `tests="3"`, `failures="3"`, three testcase children, and a `failure message="404"` in each. `--junit` is a deprecated synonym. Any failed testcase makes the process exit 1; an all-success JUnit report exits 0.

## Spec 16

`--color` controls ANSI coloring only for text reports. `never` emits no ANSI escape sequences. `always` may color page URLs and status/error values and must otherwise preserve the same textual content. `auto` is the default and enables color only when appropriate for the output terminal. JSON, JUnit, help, version, and standard-error diagnostics must remain parseable/plain rather than being corrupted by ANSI sequences.

## Spec 17

With `--follow-robots-txt`, first fetch and validate the exact positional root URL, then fetch `/robots.txt` from the root origin before scraping that already-fetched root or crawling any discovered page. A missing file is fatal: on HTTP 404, exit 1, write exactly `failed to fetch robots.txt: 404\n` to standard error, produce no report on standard output, and perform no page scrape. For a successful `/root` response followed by a missing robots file, the request order is exactly `/root`, `/robots.txt`. Other fetch failures are likewise fatal and descriptive.

Interpret robot exclusion groups using user-agent name `muffet`. A matching `muffet` group takes precedence over the wildcard group; if no specific group matches, use `User-agent: *`. Apply the selected `Disallow` path-prefix rules when deciding whether any successfully checked HTML link may be scraped, regardless of the link's origin. The single robots file fetched from the root origin therefore also gates cross-origin links by their URL paths; do not fetch a separate robots file from a linked origin. A robots-disallowed link is still fetched once and reported as a checked link on its source page, but it must not become a source-page heading and its outgoing links must not be discovered. For example, if the root-origin robots file contains `Disallow: /blocked`, a checked cross-origin HTML URL whose path is `/blocked` is not scraped and its outgoing links are not requested. Unmentioned paths are crawlable. Without this option, robots.txt does not restrict crawling.

## Spec 18

With deprecated `--follow-sitemap-xml`, first fetch and validate the exact positional root URL, then fetch `/sitemap.xml` from the root origin before scraping that already-fetched root or crawling any discovered page, and parse it strictly as XML. A non-200 fetch is fatal; a 404 writes exactly `failed to GET sitemap.xml: 404\n` to standard error and exits 1. For a successful `/root` response followed by a missing sitemap, the request order is exactly `/root`, `/sitemap.xml`. An unreachable sitemap request exits 1 with a diagnostic containing the underlying network error such as `connection refused`. Malformed XML exits 1 and performs no page scrape; for a one-line body `<urlset><url>`, it writes exactly `failed to parse sitemap.xml: XML syntax error on line 1: unexpected EOF\n`, after requests to `/root` and `/sitemap.xml` in that order.

Only a flat sitemap `<urlset>` is supported. Collect and deduplicate every `<url><loc>URL</loc></url>` value as an exact crawl whitelist. Preserve normal percent-encoded URL spelling so a sitemap entry such as `/page%20with%20spaces.html` matches the correspondingly encoded discovered URL. An empty URL set permits no discovered page to be scraped. A `<sitemapindex>` is not recursively followed and likewise yields an empty whitelist.

The sitemap is a crawling restriction, not a link-check filter or a source of seed pages: always scrape the positional root; check and report all eligible links found there; recursively scrape a checked internal HTML target only if its resolved URL is in the sitemap whitelist. Apply the same rule at every depth. Consequently, a link absent from the sitemap may appear as a checked result but cannot appear as a source-page heading or contribute further links. Without this option, no sitemap restriction applies.

## Spec 19

When robots and sitemap options are combined, both must permit a discovered page before it is recursively scraped: the URL must be in the sitemap whitelist and allowed for user-agent `muffet`. The link itself is still checked and reported even if either restriction blocks scraping. The positional root remains exempt from both crawl gates after the two control files have been fetched successfully.

Filters from `--include`/`--exclude` are different: those decide whether a discovered URL is checked at all and therefore run before robots/sitemap crawl gating. `--one-page-only` is stronger than either crawl policy and prevents every recursive scrape while retaining direct root-page link checks.

## Spec 20

Aggregate the outcome across the entire completed check. Exit 0 only when the root/control files were usable and every checked link satisfied URL parsing, redirect, timeout, fragment, and accepted-status requirements. Exit 1 if any link failed, while still reporting all other results. Fatal setup/root errors produce only a standard-error diagnostic and no partial formatted report. Per-link failures produce the selected report on standard output and normally leave standard error empty.

The implementation must complete finite sites, including cyclic link graphs, without hanging or repeatedly crawling the same page. Ordinary local checks and immediate connection failures must finish promptly; configured request timeouts and redirect limits must bound slow or pathological HTTP behavior.
