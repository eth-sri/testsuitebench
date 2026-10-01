# Clarified specification for `executable`

The required artifact is one executable file named exactly `executable`. It is a command-line website path scanner compatible with the behavior below. Unless a section says otherwise, all text is UTF-8, all displayed URLs are absolute URLs, and a successful scan exits with status 0.

## Spec 1

`executable` is a single-mode command-line program; it has no subcommands. Its first non-option argument is a target URI, not a word such as `scan`, `add`, `list`, `config`, or `help`. Such bare words consequently fail URI validation. Options are global and may generally occur before or after a target, subject to the variadic-option rule in Spec 4.

Normal successful scans write progress and discoveries to standard output and leave standard error empty. Command-line parsing failures write to standard error and exit 2. Network/request failures do not make the overall scan fail: they are reported on standard output and the process still exits 0 after it has exhausted or abandoned its work.

## Spec 2

`-h` and `--help` must exit 0, write nothing to standard error, end standard output with a newline, and produce exactly the following text (including capitalization, indentation, wrapping, blank lines, the trailing space after `should be `, and the program name `executable`):

```text
Fast directory scanning and scraping tool

Usage: executable [OPTIONS] <uri|--uri-file <uri-file>|--uri <uri>>

Arguments:
  [uri]
          The URI of the host to scan, optionally supports basic auth with
          http://user:pass@host:port

Options:
  -u, --uri <uri>
          Additional hosts to scan [aliases: url]
  -U, --uri-file <uri-file>
          The filename of a file containing a list of URIs to scan - cookies and
          headers set will be applied to all URIs [aliases: url-file]
      --verb <http_verb>
          Specify which HTTP verb to use
           [default: get] [possible values: get, head, post]
  -w, --wordlist <wordlist>
          Sets which wordlist to use, defaults to dirble_wordlist.txt in the same
          folder as the executable
  -p, --prefixes <prefixes>...
          Provides comma separated prefixes to extend queries with
  -P, --prefix-file <prefix-file>
          The name of a file containing extensions to extend queries with, one
          per line
  -x, --extensions <extensions>...
          Provides comma separated extensions to extend queries with
  -X, --extension-file <extension-file>
          The name of a file containing extensions to extend queries with, one
          per line
      --ext-sub
          Indicates whether the string "%EXT%" in a wordlist file should be 
          substituted with the current extension
  -f, --force-extension
          Only scan with provided extensions
  -k, --ignore-cert
          Ignore the certificate validity for HTTPS
      --show-htaccess
          Enable display of items containing .ht when they return 403 responses
      --timeout <timeout>
          Maximum time to wait for a response before giving up, given in seconds
           [default: 5]
      --max-errors <max_errors>
          The number of consecutive errors a thread can have before it exits,
          set to 0 to disable [default: 5]
      --json-file <json_file>
          Sets a file to write JSON output to [aliases: oJ]
      --no-color
          Disable coloring of terminal output
  -o, --output-file <output_file>
          Sets the file to write the report to [aliases: oN]
      --xml-file <xml_file>
          Sets a file to write XML output to [aliases: oX]
      --hide-lengths <length_blacklist>...
          Specify length ranges to hide, e.g. --hide-lengths 348,500-700
      --output-all <output_all>
          Stores all output types respectively as .txt, .json and .xml [aliases: oA]
      --burp
          Sets the proxy to use the default burp proxy values
          (http://localhost:8080)
      --no-proxy
          Disables proxy use even if there is a system proxy
      --proxy <proxy>
          The proxy address to use, including type and port, can also include a
          username and password in the form 
          "http://username:password@proxy_url:proxy_port"
  -t, --max-threads <max-threads>
          Sets the maximum number of request threads that will be spawned [default: 10]
  -T, --wordlist-split <wordlist_split>
          The number of threads to run for each folder/extension combo [default: 3]
  -z, --throttle <milliseconds>
          Time each thread will wait between requests, given in milliseconds
      --username <username>
          Sets the username to authenticate with
      --password <password>
          Sets the password to authenticate with
  -l, --scan-listable
          Scan listable directories
      --max-recursion-depth <max_recursion_depth>
          Sets the maximum directory depth to recurse to, 0 will disable
          recursion
  -r, --disable-recursion
          Disable discovered subdirectory scanning
      --scrape-listable
          Enable scraping of listable directories for urls, often produces large
          amounts of output
  -a, --user-agent <user_agent>
          Set the user-agent provided with requests, by default it isn't set
  -c, --cookie <cookie>
          Provide a cookie in the form "name=value", can be used multiple times
  -H, --header <header>
          Provide an arbitrary header in the form "header:value" - headers with
          no value must end in a semicolon
  -S, --silent
          Don't output information during the scan, only output the report at
          the end.
  -v, --verbose...
          Increase the verbosity level. Use twice for full verbosity.
  -B, --code-blacklist <code_blacklist>...
          Provide a comma separated list of response codes to not show in output
      --disable-validator
          Disable automatic detection of not found codes
  -W, --code-whitelist <code_whitelist>...
          Provide a comma separated list of response codes to show in output,
          also disables detection of not found codes
      --scan-401
          Scan folders even if they return 401 - Unauthorized frequently
      --scan-403
          Scan folders if they return 403 - Forbidden frequently
  -h, --help
          Print help
  -V, --version
          Print version

OUTPUT FORMAT:
    + [url] - File
    D [url] - Directory
    L [url] - Listable Directory

EXAMPLE USE:
    - Run against a website using the default dirble_wordlist.txt from the
      current directory:
        dirble [address]

    - Run with a different wordlist and including .php and .html extensions:
        dirble [address] -w example_wordlist.txt -x .php,.html

    - With listable directory scraping enabled:
        dirble [address] --scrape-listable

    - Providing a list of extensions and a list of URIs:
        dirble [address] -X wordlists/web.lst -U uri-list.txt

    - Providing multiple hosts to scan via command line:
        dirble [address] -u [address] -u [address]
```

Help exits as soon as `-h` or `--help` is encountered, so argument order matters. `executable --help --unknown` exits 0 with the main help because the unknown option is never processed. In the reverse order, `executable --unknown --help` exits 2, writes nothing to stdout, and writes the usual `error: unexpected argument '--unknown' found` diagnostic, its `tip: to pass '--unknown' as a value, use '-- --unknown'`, the main usage line, and the help hint to stderr. In `executable -- --help`, the latter token is a positional URI and must fail URI validation. There is never per-subcommand help, and the help contains exactly one `Usage:` occurrence.

## Spec 3

`-V` and `--version` exit 0, write nothing to standard error, and write exactly:

```text
Dirble 1.4.2 (commit d520c82, build 2026-04-17)
```

with one terminating newline. Invoking the executable with no arguments exits 2, writes no standard output, and writes the exact help text from Spec 2 to standard error (without an additional error preface).

## Spec 4

At least one target source is required. Targets may be supplied by one optional positional URI, repeatable `-u`/`--uri` (also `--url`), and repeatable `-U`/`--uri-file` (also `--url-file`). All sources are combined, normalized, deduplicated, sorted lexicographically by normalized target URL, and scanned in that target order, including for captured live stdout. Thus a positional `http://httpbin.org` combined with `-u http://example.com` scans and prints all `http://example.com` results before the `http://httpbin.org` results.

The argument parser, rather than post-parse host validation, rejects an invocation that contains no target source. For example, `executable --wordlist dirble_wordlist.txt` exits 2, writes nothing to stdout, and writes exactly this to stderr:

```text
error: the following required arguments were not provided:
  <uri|--uri-file <uri-file>|--uri <uri>>

Usage: executable --wordlist <wordlist> <uri|--uri-file <uri-file>|--uri <uri>>

For more information, try '--help'.
```

A URI file contains one URI per physical line. Do not manually trim or discard a line before validation. The URL parser can accept surrounding whitespace on a valid HTTP URL, but a blank line is reported as `Invalid URL: ` and an invalid line preserves its spaces in the diagnostic. For example, a line containing ` invalid host ` produces `Invalid URL:  invalid host ` (one separator space after the colon followed by the line's own leading space). Continue with valid lines, then normalize and deduplicate the valid targets. URI-file entries must use HTTP or HTTPS: unlike a syntactically parseable non-HTTP command-line target, `ftp://bad.com` in a URI file is reported as `Invalid URL: ftp://bad.com` and is not sent to the request layer. If a supplied URI file leaves the combined set with no valid host, exit 2, write the invalid-line messages followed by `No valid hosts were provided - exiting` to stdout, and leave stderr empty. The latter diagnostic is a post-parse URI-file validation result; it does not replace the required-argument diagnostic for an invocation with no target source.

The list-valued options `-p/--prefixes`, `-x/--extensions`, `-B/--code-blacklist`, `-W/--code-whitelist`, and `--hide-lengths` accept one or more values, split comma-separated values, and accumulate repeated occurrences. Because they consume following non-option values, a positional URI placed after such an option can be consumed as another option value. In particular, `executable -x .php http://example.com` must fail with a missing target-group error. Put the positional URI first, use `--uri`, or terminate option values explicitly to avoid that ambiguity. Long options support `--name=value` syntax.

## Spec 5

The following command-line constraints are mandatory and are detected before scanning:

- `--verb` accepts `get`, `head`, or `post` case-insensitively and defaults to `get`. Lowercase, uppercase, and mixed-case forms are accepted; in particular, `GET`, `HEAD`, and `HeAd` pass argument parsing and select the corresponding method rather than producing an invalid-value error.
- `--timeout` is an unsigned integer number of seconds, default 5; zero is accepted. `--max-errors` is unsigned, default 5; zero disables the consecutive-error cutoff. `--max-threads` is an unsigned integer in `1..=4294967295`, default 10. `--wordlist-split` is unsigned, default 3, and zero is accepted. `--throttle` is unsigned milliseconds, default zero. `--max-recursion-depth` is unsigned; zero is accepted.
- Numeric text such as `abc`/`notanumber` exits 2 with an `invalid value` diagnostic naming the option. A negative token such as `-1` is treated as an unexpected option and the diagnostic includes `to pass '-1' as a value, use '-- -1'`. `--max-threads 4294967296` exits 2 and reports `4294967296 is not in 1..=4294967295`, just like the lower-bound diagnostic rather than reporting an integer-overflow message. A value too large for the parser's target integer type follows a different path: `--max-threads 999999999999999999999` exits 2, writes nothing to stdout, and begins stderr with exactly `error: invalid value '999999999999999999999' for '--max-threads <max-threads>': number too large to fit in target type`, followed by a blank line and the usual help hint.
- `--username` and `--password` require each other. A missing mate exits 2 and names the required option.
- `--force-extension` and `--ext-sub` each require at least one `--extensions` or `--extension-file` occurrence. Failure exits 2 and identifies the required alternative group.
- `--code-whitelist` and `--code-blacklist` conflict. `--silent` conflicts with any `--verbose`/`-v`. `--proxy`, `--burp`, and `--no-proxy` are pairwise conflicting. Conflict diagnostics include `cannot be used with` and exit 2.
- Unknown options and missing option values exit 2 and identify the unexpected option or the option requiring a value.

For compatibility, malformed code-list and length-list elements must not be silently accepted. Length values are decimal integers or inclusive `start-end` ranges with `start < end`; invalid/reversed forms terminate nonzero with an error diagnostic.

## Spec 6

`-w/--wordlist` is repeatable. If absent, search for `dirble_wordlist.txt` next to the executable, then compatible system locations `/usr/share/dirble/`, `/usr/share/wordlists/`, and `/usr/share/wordlists/dirble/`. Use every supplied wordlist, not only the last. The runtime test environment may provide the default file; the executable must be able to find it independently of its current working directory.

Wordlist, extension-list, and prefix-list files are decoded as text using automatic character-set detection. Wordlist decoding has an observable UTF-8 compatibility bug: a UTF-8 file entry spelled `café` is decoded as the mojibake text `cafÃ©`, so its requested and displayed path is `/caf%C3%83%C2%A9`, not `/caf%C3%A9`. Already escaped ASCII remains intact; `a%20b` is requested as `/a%20b`, not `/a%2520b`. Wordlist processing removes line endings but does not first trim surrounding spaces and does not discard blank lines. Leading/trailing `/` characters are removed only when they are at the literal ends of the line before URL parsing. URL parsing itself strips surrounding spaces from the assembled URL. Consequently, the wordlist ` /z/ \n\n/a/b/\na/b\n z \n` produces the four distinct candidates `/`, `/z/`, `/z`, and `/a/b`; the two spellings of `a/b` deduplicate. Sort and deduplicate the resulting entries, and retain internal slashes, punctuation, percent escapes, and very long entries. Multiple input files are merged.

A missing wordlist/extension/prefix file terminates nonzero (the reference behavior is exit 101) and writes a panic-style diagnostic to standard error containing `panicked at src/wordlist.rs:<error location>` and `No such file or directory`. A zero-byte wordlist or extension file terminates nonzero and includes `panicked at src/wordlist.rs:<error location>`, `Error detecting file encoding`, and `is the file empty?`. A missing URI file also terminates nonzero with a file-not-found diagnostic.

## Spec 7

Targets must parse as absolute URLs. A relative input such as `invalid-url` exits 2, writes nothing to stdout, and writes:

```text
error: invalid value 'invalid-url' for '[uri]': relative URL without a base

For more information, try '--help'.
```

The same shape applies to other invalid positional URIs; an invalid port, for example, uses reason `invalid port number`. HTTP and HTTPS URLs, explicit ports, bracketed IPv6 hosts, embedded credentials, existing path components, and percent-encoded paths are accepted. Trim trailing whitespace from command-line URLs. If the parsed URL has an empty path, normalize it to `/`; otherwise preserve its parsed path and percent encoding. Candidate joining uses URL-reference semantics: a target path that does not end in `/` is treated as a final file-like segment and that segment is replaced. Thus target `http://host/base/path` plus word `child` requests `http://host/base/child`, whereas `http://host/base/path/` plus `child` retains the directory path. The resulting request does not contain doubled path slashes.

When supplied directly as a positional URI or through `--uri`, syntactically parseable non-HTTP schemes such as `ftp://` reach the request layer. Three validator requests then fail as unsupported protocol requests and the target is skipped, rather than the process hanging or crashing. This does not apply to URI-file entries, which are restricted as stated in Spec 4.

## Spec 8

Extensions come from repeatable `-x/--extensions` values and repeatable `-X/--extension-file` files. CLI values are comma-separated; files contribute their lines without trimming surrounding spaces. Merge and deduplicate exact values from all sources. Preserve extensions literally: do not automatically add a dot, so extension `php` appended to `admin` produces `adminphp`, while `.php` produces `admin.php`. For an extension-file line ` .b `, the leading space remains between the word and extension and is URL-encoded; word `x` is requested as `/x%20.b` (the URL parser discards the final surrounding space). This is distinct from a separate `.b` entry, so both requests occur.

Normally each word generates the bare candidate and a candidate with each extension. With `-f/--force-extension`, omit the bare candidate. For example, word `admin` and extensions `.php,.html` normally generate `admin`, `admin.php`, `admin.html`; with `-f`, only the last two are generated.

With `--ext-sub`, each `%EXT%` occurrence in a word is replaced by each literal extension rather than appending it. Thus `file%EXT%` with `.php,.html` becomes `file.php` and `file.html`; `index.%EXT%` with `php` becomes `index.php`. This composes with force-extension and prefixes without leaving `%EXT%` in requested or displayed URLs.

## Spec 9

Prefixes come from repeatable `-p/--prefixes` comma-separated values and repeatable `-P/--prefix-file` files. Remove line endings from prefix-file entries, but do not trim their surrounding spaces; merge and deduplicate the resulting literal values. For example, the prefix-file line ` prod- ` combined with word `config` produces `/prod-%20config`: URL parsing discards the leading space at the start of the assembled path, while the space between `prod-` and `config` is retained and encoded. With extension `.php`, it also produces `/prod-%20config.php`. A prefix is prepended literally to a word before extension appending or `%EXT%` substitution. Prefixes augment the empty prefix, so base candidates remain eligible as well. Given prefixes `dev-,prod-`, word `config`, and extensions `.php,.bak`, candidates include all prefix/word/extension combinations such as `dev-config.php` and `prod-config.bak`, as well as the corresponding unprefixed set unless force/other generation rules remove it. Preserve punctuation and long prefix strings without crashing.

## Spec 10

Before requests, sort and deduplicate generated candidates. A repeated word must result in one request/result for the same URL. Each target and each recursively discovered folder is scanned with all wordlist/modifier combinations. A scraped directory within the recursion limit is represented by its fetched `D` or `L` result, without an additional `(SCRAPED)` placeholder. A scraped directory beyond the limit is instead represented by the single placeholder defined in Specs 17 and 19.

The scanner must comfortably handle at least 100 word entries, 25 extensions, 250-character modifiers, 2,000-character path entries, blank lines, Unicode, and ordinary URL punctuation without fixed-buffer truncation or crashes.

## Spec 11

Use HTTP without automatically following redirects. The selected method (`GET`, `HEAD`, or `POST`) applies both to the three validator probes and to scan requests. A one-word scan with validation therefore makes exactly four requests of that method: three probes and one candidate. `HEAD` must not issue a compensating `GET`, and its reported body size is 0. `POST` sends an empty request body. `-k/--ignore-cert` disables HTTPS peer/hostname certificate verification.

For GET/POST, `SIZE` is the number of response-body bytes actually received; for HEAD it is zero. Accept and report all numeric HTTP response statuses, including nonstandard values such as 600 and 999. Do not treat HTTP error statuses as transport failures. Do not set a User-Agent header by default.

## Spec 12

Support HTTP Basic authentication from either `--username USER --password PASS` or userinfo in a target URL (`http://user:pass@host`). Send `Authorization: Basic ` followed by Base64 of the exact UTF-8 `username:password`. Preserve special characters and colons in flag-provided credentials. When both forms exist, flag credentials override URI credentials for the request, while the displayed result URL retains the original target spelling (including URI userinfo). An empty username is valid when paired with a password.

## Spec 13

`-H/--header` and `-c/--cookie` are repeatable and accumulate. Split a nonempty-valued header on its first colon only, preserving spaces, later colons, equals signs, Unicode, and long values. The compatibility form `Name;` sends a present header with an empty value, but `Name:` is omitted by the HTTP layer and is not present on the wire. Header matching is naturally case-insensitive on the wire. Multiple differently named headers must all be sent subject to that empty-colon exception; repeated names must send at least one supplied value without corrupting it.

Join cookies, in input order, into one `Cookie` value separated by `; `, e.g. `a=b; token=x=y`. Preserve empty and long cookie values. `-a/--user-agent` sends the exact supplied value, including spaces and non-ASCII text where the HTTP stack supports it. Authentication, arbitrary headers, cookies, and user-agent settings all apply simultaneously and also apply to validator requests and every target loaded from a URI file.

## Spec 14

`--proxy URL` routes every request for every target through that proxy. HTTP proxy requests use the absolute target URL as the request target. Proxy URLs may contain percent-encoded `username:password`; decode them and send correct HTTP Basic `Proxy-Authorization`. Empty proxy passwords are accepted. `socks5://` proxy URLs are accepted. A scheme-less proxy such as `localhost:8080` is also accepted and is treated as an HTTP proxy at that host and port. `--burp` is exactly shorthand for `--proxy http://localhost:8080`.

Passing that default Burp address explicitly as `--proxy http://localhost:8080` prints the exact line `You could use the --burp flag instead of the --proxy flag!` to stdout before any request diagnostics. Using the scheme-less `--proxy localhost:8080` still attempts the same endpoint but does not print the hint.

In the absence of an explicit proxy, honor standard system proxy environment variables such as `http_proxy`. `--no-proxy` bypasses both environment and explicit proxy behavior. A 407 response is an ordinary reportable response. An unreachable or unresolvable proxy produces per-request curl-style errors and does not hang or crash.

## Spec 15

Unless `--disable-validator` or a code whitelist is active, validate each target/folder before scanning it by requesting three random alphanumeric child paths, conventionally of lengths 10, 20, and 30. Exactly three probes are made. Determine the common nonexistent-response fingerprint:

- A common 404 is represented by code alone: `(CODE:404)`.
- A common 301/302 includes its common redirect location: `(CODE:C|DEST:location)`.
- A common 401 or 403 includes its fixed size and triggers the skip behavior below.
- For other common codes, if at least two probe body lengths match, use `(CODE:C|SIZE:N)`.
- If lengths vary but the absolute difference between response length and full requested-URL length is stable, use `(CODE:C|DIFF_SIZE:N)`.

Print `[INFO] Detected nonexistent paths for <folder> are <fingerprint>` to stdout. A candidate is suppressed as nonexistent only when its code and the applicable redirect/size/difference fields match the fingerprint. Code or size mismatches remain discoveries. With validator disabled, make no probes, print no detection message, and report otherwise unfiltered 404-like responses.

If validation itself repeatedly suffers transport errors, print each error and then `[WARN] <folder> errored too often during validation, skipping scanning`. If the detected fingerprint is 401 or 403, skip that folder unless `--scan-401` or `--scan-403`, respectively, is present. The exact 401 skip block is:

```text
[INFO] Skipping <folder>: 
    Scanning of directories returning 401 is disabled.
    Use the --scan-401 flag to scan this directory,
    or provide a valid session token or credentials.
```

The exact 403 block is:

```text
[INFO] Skipping <folder>: 
    Scanning of directories returning 403 is disabled.
    Use the --scan-403 flag to scan this directory,
    or provide valid session token or credentials.
```

Each line, including the first line's space after the colon, ends in a newline. These flags concern a folder's validator fingerprint; they do not hide an individually discovered 401/403 result.

## Spec 16

Ordinary reportable candidates are files and use prefix `+`. A request to a path without trailing slash is classified as a directory only when it returns 301 or 302 whose `Location` is that same path with exactly one trailing slash (relative or equivalent absolute form). An unrelated redirect remains a file result and carries its redirect destination.

For a directory redirect, request the slash form separately and report only the slash URL using the slash response's status and body length. Prefix it `D`, or `L` if its content is listable. This classification is independent of whether the slash response is 200, 401, or 403. For example:

```text
D http://host/admin/ (CODE:200|SIZE:19)
+ http://host/moved (CODE:301|SIZE:0|DEST:http://elsewhere/)
```

There is an observable exception when authentication comes from `--username` and `--password`. The HTTP layer resolves a relative redirect against a credential-bearing request URL. Consequently, for target `http://127.0.0.1:19104`, credentials `admin`/`secret`, and a response from `/admin` with `Location: /admin/`, the resolved destination is `http://admin:secret@127.0.0.1:19104/admin/`. It does not compare equal to the displayed target spelling, so the scanner does not perform the slash-form directory request and reports the original response as an ordinary redirect:

```text
+ http://127.0.0.1:19104/admin (CODE:301|SIZE:0|DEST:http://admin:secret@127.0.0.1:19104/admin/)
```

The same behavior applies to another same-path redirect such as `/api` under flag-provided credentials. Do not rewrite these authenticated 301 results as `D` slash-URL results.

## Spec 17

Recursion is enabled by default. When a non-listable directory is discovered through an HTTP redirect, scan it with the same generated wordlists. Track fetched folder URLs and do not scan them twice. `-r/--disable-recursion` disables all scanning below the initial target but still reports directories found at the root.

`--max-recursion-depth N` counts the initial target as depth 0. A discovered child at depth 1 is reported, but its contents are scanned only when the allowed depth reaches that level. Thus 0 is equivalent to disabled recursion, 1 permits scanning immediate child folders and discovering depth-2 entries, and so on. Without a limit, arbitrarily deep trees are scanned until exhausted.

When a scraped directory is beyond the allowed recursion depth, do not request its URL and show it as:

```text
D http://host/parent/child/ (SCRAPED)
```

When it is within the allowed depth, fetch and classify the scraped directory itself as specified in Spec 19 instead of emitting this placeholder.

## Spec 18

After obtaining a directory's slash response, classify it as listable when status is 200 and its body contains, case-insensitively, any of `parent directory`, `up to `, or `directory listing for`. This supports Apache-, nginx-, and IIS-style directory pages, malformed HTML, and empty listings. A listable directory is reported with `L`; a regular directory is `D`.

By default, a listable directory is reported but the normal wordlist is not recursively run inside it. `-l/--scan-listable` enables normal wordlist scanning inside listable directories. Non-listable directory recursion is unaffected.

## Spec 19

`--scrape-listable` parses anchor `href` values from each detected listable page and discovers linked entries whose resolved path ends in `/`. It operates even without `--scan-listable`. When a scraped directory is within the recursion limit, request its slash URL, report its real status and size, and classify its body as `L` or `D` under Spec 18; do not also emit a `(SCRAPED)` placeholder. A fetched listable child is itself scraped recursively. A fetched non-listable child is scanned with the normal generated wordlist candidates when recursion permits. Thus scraping `child/` from `/root/` first requests `/root/child/`; if that response is non-listable, a word `root` is then requested as `/root/child/root`.

Resolve ordinary relative links against the listing URL and same-host absolute paths against the target origin. Reject external origins, out-of-scope absolute paths, and links beginning `../`, `./`, `?`, or `#`; files whose resolved path does not end in `/` are not printed. The parser does not reject `javascript:` and `mailto:` spellings: `javascript:bad/` and `mailto:a@b/` are treated as relative folder names resolving to `/root/javascript:bad/` and `/root/mailto:a@b/`, then follow the same depth-dependent fetch-or-placeholder rules as other scraped directories. Parent and sorting links must not cause loops.

When a scraped directory is beyond the allowed recursion depth, emit only the unfetched placeholder from Spec 17. In structured reports that placeholder has `code: 0`, `size: 0`, `is_directory: true`, `is_listable: false`, an empty `redirect_url`, and `found_from_listable: true`. A scraped directory that is fetched instead has its observed code, size, and classification and has `found_from_listable: false`; any wordlist results subsequently found below it also have `found_from_listable: false`.

## Spec 20

Apply all enabled output filters to live and file reports:

- `-B/--code-blacklist` suppresses exactly the listed comma-separated status codes but leaves validator operation enabled.
- `-W/--code-whitelist` reports only listed codes and automatically disables validation and validator INFO lines.
- `--hide-lengths` accumulates comma-separated/repeated single sizes and inclusive ranges. It suppresses an ordinary `+` file result whose body length is in one, but it is not applied to a result already classified as a `D` directory or `L` listable directory. For example, with hidden length 6, a six-byte ordinary file is absent while `D http://127.0.0.1:19104/dir/ (CODE:200|SIZE:6)` and `L http://127.0.0.1:19104/listed/ (CODE:200|SIZE:6)` remain visible.
- By default, suppress a 403 result whose URL contains `.ht`. `--show-htaccess` includes it. This special suppression is for 403 `.ht` items and does not broadly hide unrelated paths.

The filters compose subject to the directory exception for `--hide-lengths`: a result is shown only if it survives every filter applicable to its result kind. They must not create duplicate results.

## Spec 21

The exact uncolored result-line forms are:

```text
+ URL (CODE:C|SIZE:N)
+ URL (CODE:C|SIZE:N|DEST:LOCATION)
D URL/ (CODE:C|SIZE:N)
L URL/ (CODE:C|SIZE:N)
```

Use `DEST` only for ordinary 301/302 redirect results. The HTTP layer resolves a relative `Location` against the request URL before the scanner stores or displays it, so `Location: /different` from `http://127.0.0.1:PORT/shown` is displayed as `DEST:http://127.0.0.1:PORT/different`. An already absolute location retains that absolute value. Non-redirects never have `DEST`; validator redirect fingerprints use the same resolved representation.

Candidate sorting does not imply globally sorted live output, even with one worker. After sorting, `--wordlist-split N` forms interleaved jobs: job `i` contains sorted candidate indices `i`, `i+N`, `i+2N`, and so on. A single worker drains those jobs in increasing job-index order. With the default split of 3, sorted words `admin, api, foo, session, test` therefore appear live as `admin, session, api, test, foo`; sorted words `other, validate-empty, validate-multi, validate-spaces, validate-special-auth, validate-ua` appear as `other, validate-spaces, validate-empty, validate-special-auth, validate-multi, validate-ua`. Authentication, headers, cookies, and user-agent options do not change this scheduling order. Concurrent workers may additionally interleave live lines by request-completion order. Final terminal reports and all structured/file output are sorted lexicographically by URL and grouped consistently, irrespective of live order.

When stdout is not a terminal, do not print a startup banner or a final `Dirble Scan Report` section to stdout. Print only live INFO/WARN/DEBUG/TRACE/error/result lines. A simple captured scan with validator disabled, words `admin`, `dir`, `missing`, and corresponding 200, directory redirect, and 404 responses must therefore be exactly three result lines with no banner or report header.

## Spec 22

When stdout is a terminal, print a final section for every target in the form `Dirble Scan Report for TARGET:` followed by its sorted results. Indent terminal report results by two spaces per path depth below the target; the same results may already have appeared as unindented live output. Multiple targets get distinct report headers.

Color only the numeric status code when terminal color is enabled: 200-299 green (`ESC[32m`), 300-399 cyan (`ESC[36m`), 400-499 red (`ESC[31m`), and 500-599 yellow (`ESC[33m`), followed by reset `ESC[0m`. Codes outside those ranges are uncolored. `--no-color` and the `NO_COLOR` environment convention remove all ANSI escapes. Never put ANSI escapes in report files.

## Spec 23

`-S/--silent` suppresses all ordinary stdout scan output, including startup, validator INFO, live discoveries, and terminal final report. Operational errors/warnings may still be emitted when necessary. Silent mode does not suppress or corrupt requested report files: an exercised one-word scan using `--silent --json-file PATH` exits 0, leaves stdout and stderr empty, and writes a complete valid JSON report. Combining `--silent` with `--output-file`, `--json-file`, and `--xml-file` likewise exits 0 with empty stdout and stderr and writes all three complete reports.

One `-v/--verbose` enables DEBUG in addition to INFO and results, but not TRACE. Every scheduled wordlist-split job emits one `[DEBUG]` line containing `Scanning <folder>` and one containing `Finished scanning <folder>`, including a job whose partition is empty because the wordlist has fewer candidates than the split count. The output thread then emits one final `[DEBUG]` line containing `Received signal to end, generating the report`. Consequently, a single scanned folder with an effective split count of 3 produces exactly seven DEBUG lines: three scanning lines, three finished lines, and the final output-thread line. This is true both for a six-word input split into three nonempty jobs and for a validated one-word input using `--max-threads 2` with the default three-way split. The lines also contain time, thread, and module prefixes. Two occurrences (`-vv` or `-v -v`) additionally emit `[TRACE] Requesting <url>` for validator and scan requests. Silent and verbose are mutually exclusive as stated in Spec 5.

## Spec 24

`-o/--output-file PATH` creates or truncates a UTF-8 plain-text report. For each target, write:

```text
Dirble Scan Report for http://host/:
+ http://host/a (CODE:200|SIZE:10)
+ http://host/b (CODE:201|SIZE:11)

```

There is one blank line after each target section, including the final one. Result lines in files have no recursion indentation and no ANSI codes. Existing files are overwritten rather than appended. Multiple targets receive separate sections in deterministic target order.

## Spec 25

`--json-file PATH` creates or truncates valid UTF-8 JSON containing one top-level array combining every target's sorted results. Every element contains exactly these semantically required fields and types:

```json
{"url":"http://host/a","code":200,"size":10,"is_directory":false,"is_listable":false,"redirect_url":"","found_from_listable":false}
```

`url` and `redirect_url` are strings; `code` and `size` are numbers; the remaining fields are JSON booleans. A directory/listing sets the respective flags, with the out-of-depth scraped-placeholder values specified in Spec 19. A non-redirect has an empty redirect string. A relative redirect is stored as the absolute URL resolved by the HTTP layer: `Location: /next?x="q"&y=1` becomes `http://host/next?x="q"&y=1` in `redirect_url`. Escape JSON strings correctly. Arrays with one or multiple results must have no trailing comma and must parse normally, including reports produced in silent mode.

## Spec 26

`--xml-file PATH` creates or truncates UTF-8 output with this nominal XML structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dirble_scan>
<path url="http://host/a" code="200" content_len="10" is_directory="false" is_listable="false" redirect_url="" found_from_listable="false"/>
</dirble_scan>
```

There is one direct `<path>` element per combined result. Use exactly the attribute names shown, lowercase `true`/`false`, and decimal code/length values. Attribute values are interpolated without XML escaping. For example, word `a&b` produces a raw attribute such as `url="http://127.0.0.1:PORT/a&b"`; the bare ampersand makes the document not well-formed and an XML parser reports an invalid token. This malformed output is the required compatibility behavior.

## Spec 27

`--output-all BASE` supplies `BASE.txt`, `BASE.json`, and `BASE.xml` as the text, JSON, and XML destinations using Specs 24-26. An explicit per-format option overrides the corresponding `--output-all` destination rather than adding a second destination. For example, `--output-all bundle --output-file extra.txt --json-file extra.json --xml-file extra.xml` writes the three `extra.*` files and does not create `bundle.txt`, `bundle.json`, or `bundle.xml`. Without those overrides, `--output-all bundle` creates all three `bundle.*` reports. Explicit text, JSON, and XML options may be combined with one another and all selected destinations must succeed.

Support the long compatibility aliases `--oN`, `--oJ`, `--oX`, and `--oA` for text, JSON, XML, and all-formats output. Preserve the reference short-option quirk: `-oN file` is parsed as short `-o` with attached value `N`, leaving `file` to be interpreted as the positional URI. Forms such as `-oN=/absolute/path` consequently use literal output path `N=/absolute/path`; failure to create that relative nested path exits 101 and stderr contains `couldn't create N=` (similarly `J=`, `X=`, and `A=`). Normal long options with equals, such as `--output-file=/tmp/report`, work.

Failure to create a requested output file, such as because its parent directory does not exist, terminates nonzero with a clear creation error; do not silently omit the report.

## Spec 28

`--max-threads` limits concurrently active scan jobs. `--wordlist-split` partitions each folder/prefix/extension wordlist into interleaved jobs; different split counts must find the identical URL set. Immediately before an initial target scan that was not skipped by validation, derive an initial split target of `max-threads - 2` when `max-threads` is above 2. If that target is greater than the configured `--wordlist-split`, use it and print `[INFO] Increasing wordlist-split for initial scan of TARGET to N`, even when the wordlist contains fewer than `N` entries. Thus the defaults (`--max-threads 10`, `--wordlist-split 3`) always print the line with `to 8`; `--max-threads 6` with a smaller split prints `to 4`; and `--max-threads 1`, `2`, or `3` does not increase it. The line follows any validator fingerprint line and precedes candidate results. Concurrency must not lose or duplicate generated-candidate results, and an in-depth scraped directory must not receive a placeholder in addition to its fetched result.

`--throttle M` waits approximately M milliseconds between requests made by each worker, not globally. With one worker and three scan items, 500 ms throttling makes the scan at least about one second slower; multiple workers remain concurrent. Zero adds no delay.

The request timeout is per request. A slow response beyond `--timeout` is aborted, produces a curl-style line containing `Timeout was reached`, and does not prevent other work from completing. Track transport failures consecutively per worker. On reaching the positive `--max-errors` threshold, stop that worker early and emit a warning containing `stopping due to multiple` and `consecutive errors`. A successful request resets the count; non-consecutive errors do not accumulate. Zero disables this worker cutoff.

## Spec 29

Transport diagnostics use the observable curl-compatible shape:

```text
Curl error after requesting URL : [N] SHORT (DETAIL)
```

Important categories are `[1] Unsupported protocol`, `[5] Could not resolve proxy name`, `[6] Could not resolve hostname`, `[7] Could not connect to server`, and timeout text `Timeout was reached`. During validation, exactly three failing probes are printed before the folder-level skip warning, even when `--max-errors` is 0 or a small positive value. IPv4, bracketed IPv6, DNS failure, connection refusal, and proxy failure must complete promptly rather than hang. These diagnostics go to stdout and the completed scan exits 0.

The parenthesized detail is also fixed for the exercised failures. Resolving target `nonexistent-host-12345.invalid` uses `(Could not resolve host: nonexistent-host-12345.invalid)`. Resolving proxies `not-a-valid-url` and `invalid-proxy` uses `(Could not resolve proxy: not-a-valid-url)` and `(Could not resolve proxy: invalid-proxy)`, respectively. Refused connections to the exercised endpoints use `(Failed to connect to ::1 port 8080 after 0 ms: Could not connect to server)`, `(Failed to connect to localhost port 1080 after 0 ms: Could not connect to server)`, `(Failed to connect to localhost port 19999 after 0 ms: Could not connect to server)`, and `(Failed to connect to 127.0.0.1 port 19999 after 0 ms: Could not connect to server)`. Do not substitute operating-system errno prose for these libcurl details.

Ordinary malformed CLI inputs instead use clap-compatible stderr diagnostics beginning `error:`, include a blank line and `For more information, try '--help'.`, and exit 2. In particular, invalid `--verb INVALID` also lists `[possible values: get, head, post]`; `--max-threads 0` states that 0 is not in `1..=4294967295`.

Clap renders each option's declared value placeholder in diagnostics; it must not replace these placeholders with a generic `<value>`. The exact invalid-value first lines are:

```text
error: invalid value '0' for '--max-threads <max-threads>': 0 is not in 1..=4294967295
error: invalid value '4294967296' for '--max-threads <max-threads>': 4294967296 is not in 1..=4294967295
error: invalid value '999999999999999999999' for '--max-threads <max-threads>': number too large to fit in target type
error: invalid value 'notanumber' for '--timeout <timeout>': invalid digit found in string
error: invalid value 'abc' for '--max-errors <max_errors>': invalid digit found in string
error: invalid value 'abc' for '--max-threads <max-threads>': invalid digit found in string
```

These invalid-value diagnostics are followed by a blank line and the help hint, without a `Usage:` paragraph. By contrast, required-dependency, conflict, and unexpected-negative-token diagnostics include their invocation-specific `Usage:` paragraph and a blank line before the help hint. The following renderings are mandatory:

- `--password <password>` without a username names missing `--username <username>` and uses `Usage: executable --password <password> --username <username> <uri|--uri-file <uri-file>|--uri <uri>>`.
- `--username <username>` without a password names missing `--password <password>` and uses `Usage: executable --username <username> --password <password> <uri|--uri-file <uri-file>|--uri <uri>>`.
- `--ext-sub` and `--force-extension` each name the required group exactly as `<--extensions <extensions>...|--extension-file <extension-file>>`. Their respective usage lines are `Usage: executable --ext-sub <uri|--uri-file <uri-file>|--uri <uri>> <--extensions <extensions>...|--extension-file <extension-file>>` and `Usage: executable --force-extension <uri|--uri-file <uri-file>|--uri <uri>> <--extensions <extensions>...|--extension-file <extension-file>>`.
- Negative numeric tokens use `error: unexpected argument '-5' found` or `error: unexpected argument '-1' found`, then the corresponding `tip: to pass '-5' as a value, use '-- -5'` or `tip: to pass '-1' as a value, use '-- -1'`, and then `Usage: executable [OPTIONS] <uri|--uri-file <uri-file>|--uri <uri>>`.
- The code-list conflict names the variadic placeholders: `error: the argument '--code-whitelist <code_whitelist>...' cannot be used with '--code-blacklist <code_blacklist>...'`. Without other displayed options its usage is `Usage: executable --code-whitelist <code_whitelist>... <uri|--uri-file <uri-file>|--uri <uri>>`; with wordlist and max-errors active it is `Usage: executable --wordlist <wordlist> --code-whitelist <code_whitelist>... --max-errors <max_errors> <uri|--uri-file <uri-file>|--uri <uri>>`.
- `--burp --proxy URL` renders `error: the argument '--burp' cannot be used with '--proxy <proxy>'` and `Usage: executable --burp <uri|--uri-file <uri-file>|--uri <uri>>`. When `--proxy URL` precedes `--burp`, it renders `error: the argument '--proxy <proxy>' cannot be used with '--burp'` and, when a wordlist is present, `Usage: executable --proxy <proxy> --wordlist <wordlist> <uri|--uri-file <uri-file>|--uri <uri>>`.
- `--burp --no-proxy` renders `error: the argument '--burp' cannot be used with '--no-proxy'` and `Usage: executable --burp --wordlist <wordlist> <uri|--uri-file <uri-file>|--uri <uri>>` when a wordlist is present. In reverse order, `--no-proxy --burp` renders `error: the argument '--no-proxy' cannot be used with '--burp'` and uses `Usage: executable --no-proxy --wordlist <wordlist> <uri|--uri-file <uri-file>|--uri <uri>>`.
- `--proxy URL --no-proxy` retains the proxy placeholder and uses `Usage: executable --proxy <proxy> --wordlist <wordlist> <uri|--uri-file <uri-file>|--uri <uri>>` when a wordlist is present. In reverse order, `--no-proxy --proxy URL` renders `error: the argument '--no-proxy' cannot be used with '--proxy <proxy>'` and uses `Usage: executable --no-proxy --wordlist <wordlist> <uri|--uri-file <uri-file>|--uri <uri>>`.
- The silent/verbose conflict names the variadic flag exactly: `error: the argument '--silent' cannot be used with '--verbose...'`. For an invocation containing wordlist, max-threads, max-errors, timeout, and silent options, its usage is `Usage: executable --wordlist <wordlist> --max-threads <max-threads> --max-errors <max_errors> --timeout <timeout> --silent <uri|--uri-file <uri-file>|--uri <uri>>`.

## Spec 30

All reports and console output use UTF-8 and must safely represent Unicode URL paths, credentials, user agents, and response metadata, subject to the specific UTF-8 wordlist-decoding bug in Spec 6. Preserve existing percent escapes rather than encoding the percent sign again: the exercised wordlist entry `a%20b` remains `/a%20b`. HTML parsing, URL construction, JSON escaping, and output sorting must remain correct for malformed HTML, empty listable pages, special characters, long URLs, multiple targets, and concurrent completion order. XML deliberately retains the unescaped-attribute behavior in Spec 26. Silent JSON reports are complete and valid as stated in Spec 23. A scan should otherwise recover from individual flaky/failed endpoints and continue other candidates unless that worker reaches its configured consecutive-error cutoff.
