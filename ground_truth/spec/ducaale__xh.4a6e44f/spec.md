# Clarified specification: `executable`

## Spec 1: Product and compatibility target

The required artifact is one executable file named `executable` at the repository root. It is a command-line HTTP client compatible with the observable behavior of xh 0.25.3. It must perform real HTTP requests, construct requests without sending them, translate requests to curl commands, persist sessions, download files, and generate documentation/completion output.

Unless a rule below says otherwise, successful commands exit 0, write their primary result to standard output, and do not write to standard error. Diagnostics use the actual invocation name, normally `executable`, as their prefix, except for the configuration-file parse warning specified in Spec 15, whose fixed prefix is `xh:`. The implementation must not panic or print a language backtrace during ordinary errors.

`--version` exits 0, writes nothing to stderr, and prints exactly:

```text
xh 0.25.3
-native-tls +rustls
```

with a final newline. The required build therefore uses the rustls behavior described below and has no native-tls support.

The short `-V` form also exits 0 and writes nothing to stderr, but its output is only the first line, exactly `xh 0.25.3\n`; it does not print the TLS feature line.

## Spec 2: Command-line shape and help

The command grammar is:

```text
executable [OPTIONS] <[METHOD] URL> [REQUEST_ITEM]...
```

There is no git-style subcommand system. The sole special positional word is `help`, which prints detailed help and exits 0. Words such as `list`, `add`, `remove`, `delete`, and `show` are URLs or methods according to the normal positional grammar, not subcommands. An explicit `--` ends option parsing; a following `--help` is positional data rather than a help request.

`--help` prints concise help when option parsing reaches it, and then ignores later arguments. It does not override a malformed option that occurs earlier. Thus `--help --bad-option` exits 0 with concise help, but `--bad-option --help` exits 2, writes nothing to stdout, and writes exactly:

```text
error: unexpected argument '--bad-option' found

  tip: to pass '--bad-option' as a value, use '-- --bad-option'

Usage: executable [OPTIONS] <[METHOD] URL> [REQUEST_ITEM]...

For more information, try '--help'.
```

For a successful concise-help invocation, output is written only to stdout. Its first line is:

```text
xh is a friendly and fast tool for sending HTTP requests
```

It contains `Usage: executable [OPTIONS] <[METHOD] URL> [REQUEST_ITEM]...`, distinct `Arguments:` and `Options:` sections, and the argument description line:

```text
  <[METHOD] URL>     The request URL, preceded by an optional HTTP method
```

It ends with these concepts:

```text
Each option can be reset with a --no-OPTION argument.
Run "xh help" for more complete documentation.
```

The detailed `executable help` text contains the headings `Arguments:` and `Options:`. It explains method inference, URL shorthand, every request-item separator, each option's full semantics, and environment variables, and includes several option-local lines introduced by the singular label `Example:`. It has neither an exit-status section nor a plural `Examples` section, and contains neither the phrase `exit status` nor the word `examples`. It must include at least the request-item forms `key==value`, `key=value`, `key:=value`, `key@filename`, `@filename`, `header:value`, `header:`, and `header;`. Help output ends in a newline. `-h` is the response-headers shortcut, not help.

The concise help documents the following public options and their short forms where shown:

```text
-j, --json                         -f, --form
    --multipart                        --raw <RAW>
    --pretty <STYLE>                   --format-options <FORMAT_OPTIONS>
-s, --style <THEME>                   --response-charset <ENCODING>
    --response-mime <MIME_TYPE>    -p, --print <FORMAT>
-h, --headers                     -b, --body
-m, --meta                        -v, --verbose...
    --debug                            --all
-P, --history-print <FORMAT>      -q, --quiet...
-S, --stream                      -x, --compress...
-o, --output <FILE>               -d, --download
-c, --continue                        --session <FILE>
    --session-read-only <FILE>
-A, --auth-type <AUTH_TYPE>       -a, --auth <USER[:PASS] | TOKEN>
    --ignore-netrc                    --offline
    --check-status                -F, --follow
    --max-redirects <NUM>             --timeout <SEC>
    --proxy <PROTOCOL:URL>             --verify <VERIFY>
    --cert <FILE>                     --cert-key <FILE>
    --ssl <VERSION>                   --https
    --http-version <VERSION>          --resolve <HOST:ADDRESS>
    --interface <NAME>            -4, --ipv4
-6, --ipv6                            --unix-socket <FILE>
-I, --ignore-stdin                    --curl
    --curl-long                        --generate <KIND>
    --help                        -V, --version
```

The implementation also accepts the compatibility options `--bearer TOKEN` (equivalent to bearer auth), `--native-tls`, and `--default-scheme SCHEME`; these may be hidden from concise help but must be represented in generated completions. Every long option except `--version` can be negated as `--no-OPTION`; `--no-version` is an unknown argument and is absent from generated completions. Negation removes an earlier occurrence, including one supplied by configuration. For mutually exclusive serialization flags, the last effective option wins: `--json` overrides form/multipart, `--form` overrides JSON/multipart, and `--multipart` overrides JSON/form.

Missing required arguments, unknown flags, missing option values, invalid enumerated values, and malformed option payloads print a concise `error:` diagnostic and usage/help hint to stderr and exit nonzero (normally 2 for command-line parse errors). Running with no arguments reports that `<[METHOD] URL>` is required, includes `Usage:`, and says `For more information, try '--help'`. Help may appear before or after a method or other ordinary arguments.

## Spec 3: Methods and URLs

The optional method is case-insensitive and is emitted uppercase. At minimum GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS, and CONNECT are recognized. An explicit uppercase custom HTTP token followed by a URL is also accepted and preserved. A sole method token fails because the URL is missing; a sole non-method word is treated as a URL.

If no method is supplied, choose GET when there is no request body and POST when a body exists. An empty serialization selection is mode-specific: `--json` with no fields uses GET while still adding the JSON Content-Type and Accept defaults; `--form` with no fields uses GET while adding its form headers and `Content-Length: 0`; and `--multipart` with no fields uses POST. `--raw ''` also produces POST. The same inference applies when a serialization option comes from `config.json`. HEAD never prints a response body.

URLs support HTTP and HTTPS, credentials, explicit ports, IPv4, bracketed IPv6, paths, queries, and fragments. URL serialization supplies `/` as the path when the input contains only an authority. If no scheme is given, prepend `http://`; `--https` or `--default-scheme https` changes that default to HTTPS. A program invoked via an alias named `xhs`, `https`, or `xhttps` also defaults to HTTPS. Consequently, invoking an `xhs` alias as `xhs --curl example.com` exits 0 with empty stderr and stdout exactly `curl https://example.com/\n`. Invocation as `http` or `https` additionally enables HTTPie compatibility mode.

The following shorthand is required:

```text
:                 -> http://localhost/
:8000             -> http://localhost:8000/
:8000/path        -> http://localhost:8000/path
:/path            -> http://localhost/path
://example.com/x  -> http://example.com/x
```

The selected scheme changes appropriately under HTTPS-default modes. Query items are appended to an existing URL query rather than replacing it. URL fragments are never sent in the HTTP request.

Offline HTTP/1.x request lines contain only the path and query, for example `GET /path?q=x HTTP/1.1`. The `Host` header includes a non-default port. Invalid URLs are rejected cleanly; an internationalized hostname containing spaces reports `Invalid <URL>: invalid international domain name` and exits 2.

## Spec 4: Standard input, files, and body selection

When stdin is redirected, its bytes are read as the request body by default, including arbitrary Unicode and binary data. Outside the exceptions below, the presence of redirected stdin counts as explicit body intent and causes implicit POST even when the redirected stream contains zero bytes; an inherited terminal stdin with no supplied input does not. `--ignore-stdin`/`-I` suppresses this behavior completely and restores normal GET/body inference from the other arguments. This flag is important for scripts whose stdin happens to be non-terminal.

An explicit method is not replaced by that inference. In particular, an explicit `GET` with an ordinary redirected stream already at EOF remains GET but selects a zero-byte JSON body; on HTTP/1.x it sends `Content-Type: application/json`, `Content-Length: 0`, and the JSON Accept default.

There are two observable exceptions. Curl translation (`--curl`) does not implicitly consume redirected stdin, whether it is empty or nonempty; only body sources named in the curl-translation arguments contribute data (an explicit `@-` is preserved as curl's `--data-binary @-`, rather than being read by xh). This remains true with every other curl-translation option, including multipart, timeout, certificate/key, proxy, verification, stream, check-status, debug, quiet, follow, output, TLS, and HTTP-version options. Also, when `XH_TEST_MODE_TERM` is present, stdin is treated as a terminal along with the output descriptors, so bytes supplied through a captured/redirected stdin descriptor—including an inherited pipe already at EOF—are ignored completely. Thus the fixed test environment's empty captured stdin does not infer POST or conflict with command-line data, whereas an ordinary redirected zero-byte stream without either exception remains an explicit empty body.

Stdin cannot be combined with command-line body data fields, a whole-body `@file`, or `--raw`. For example, feeding `hello` to `--offline --raw @- POST https://example.com -v` exits 1, writes nothing to stdout, and writes exactly this newline-terminated stderr diagnostic:

```text
executable: error: Request body from stdin and --raw cannot be mixed. Pass --ignore-stdin to ignore standard input.
```

Raw data similarly cannot be combined with another body-producing request item, though both stdin and raw data may coexist with headers and query parameters. Empty, large, and binary whole-body files are valid. A standalone `@filename` reads that file verbatim as the complete request body, and two whole-body files are rejected. `~` in request-item filenames is expanded.

Content type for a whole-body file is inferred from its extension when known, with a sensible fallback. A `;type=MIME` annotation on a whole-body file sets it explicitly; a `;filename=` annotation on a whole-body item is ignored with a warning because filenames apply to multipart parts. Redirected stdin and raw/whole-file bodies may coexist with header and query items, since those do not create a competing body.

## Spec 5: Request items and serialization

Request-item parsing is separator-driven. Backslash escapes a request-item separator so it becomes literal data and the escape marker is consumed. In JSON-mode path parsing it also escapes brackets. Form and multipart field names do not apply JSON-path bracket unescaping: a backslash before `[` or `]` remains part of the field name. Values and keys preserve Unicode, whitespace, newlines, punctuation, equals signs, and colons unless a separator rule consumes them. In every `...@file` value form, the referenced file's contents supply the value. For example, with both test-mode variables present, `--print=B --offline --form : '\]=a'` exits 0 with empty stderr and stdout exactly `%5C%5D=a\n\n`.

- `name==value` adds a URL query parameter. Multiple values preserve input order and are application/x-www-form-urlencoded encoded: spaces become `+`, and reserved characters such as `&` and `=` are percent encoded.
- `name=value` adds a string-valued JSON member in JSON mode or a form field in form mode. Empty values are empty strings.
- `name:=json` parses the right side as a JSON literal. Numbers (including negative, floating-point, and scientific forms), booleans, null, arrays, and objects retain their JSON types. Invalid JSON is an error. Literal JSON fields are not permitted in multipart mode.
- `Header:value` adds a request header. Repeated headers with the same name are preserved for that request. `Header:` removes values accumulated for that header, and `Header;` sends the header with an empty value. Built-in `User-Agent` and `Accept-Encoding` values can be suppressed this way. `Accept:` is a special case: after removing the earlier Accept value, final default-header construction restores `Accept: */*` unless a later request item supplies another Accept value. If a header is first unset and then set, the later value is sent.
- `field@path` uploads a file and implies multipart form behavior when used with `--form`. Optional `;type=MIME` and `;filename=NAME` annotations become that part's media type and presented filename.
- In multipart mode, `field=<path` creates a non-file text part whose value is the literal string `<path`; it does not read the named path and does not add a `filename` parameter.
- A standalone `@path` is the complete body as described above.

JSON is the default field serialization. JSON request objects are compact on the wire and preserve command-line insertion order. Form mode encodes fields as `application/x-www-form-urlencoded`; characters requiring escaping are percent encoded, and bracket notation remains part of the literal field name rather than constructing nested JSON. `--multipart` with one or more parts generates multipart framing using CRLF and a closing `--boundary--` marker. With no fields, it still selects POST and advertises `Content-Type: multipart/form-data; boundary=...`, but its request body is empty and contains no opening or closing boundary marker.

Default request headers are compatible with xh 0.25.3:

- `User-Agent: xh/0.25.3`, `Connection: keep-alive`, the correct `Host`, and `Accept-Encoding: gzip, deflate, br, zstd` are normally sent.
- A JSON body (or explicit JSON mode) uses `Content-Type: application/json` and `Accept: application/json, */*;q=0.5`.
- A URL-encoded form uses `Content-Type: application/x-www-form-urlencoded` and `Accept: */*`.
- Multipart supplies `Content-Type: multipart/form-data; boundary=...`.
- A request with no JSON intent/body uses `Accept: */*`.
- HTTP/1.x bodies have the correct byte `Content-Length`, including zero where a zero-length selected body is represented.

## Spec 6: Nested JSON paths

In JSON mode, bracket notation in the field name constructs nested objects and arrays at arbitrary practical depth:

```text
user[name]=Ada                 -> {"user":{"name":"Ada"}}
items[0]=a items[2]=c          -> {"items":["a",null,"c"]}
items[]=a items[]=b            -> {"items":["a","b"]}
[][name]=Ada                   -> [{"name":"Ada"}]
matrix[1][2]:=4                -> {"matrix":[null,[null,null,4]]}
```

At the root, ordinary text, including numeric text, is an object key. Inside brackets, an unsigned decimal is an array index, `[]` appends, and all other text (including negative numbers) is an object key. Sparse arrays are padded with JSON null and indices at least as large as 1000 are supported. Multiple paths merge into the existing structure; setting the exact same location again replaces its value, while repeated append operations add elements.

Escaped `\[` and `\]` are literal brackets in a key. Inside a bracket, `\0` denotes object key `0` rather than array index 0; doubled backslashes preserve one literal backslash. Escaped `\:` and `\=` can appear in keys. Whitespace, special characters, and multibyte Unicode in keys are preserved.

Paths are syntax checked: unmatched/missing brackets, text following a closed bracket without another `[`, a nonnumeric root array selector, and nested `[[` forms fail with a contextual parse error. These errors exit 1, write nothing to stdout, and use a three-part stderr layout: the newline-terminated `executable: error: ...` sentence, a blank line, and the complete path indented by two spaces followed by a caret line marking the offending token. In particular:

- Text after a completed bracket expression reports `executable: error: expected '['`; the caret is under the first character that should instead have been `[`. For `foo[x]extra`, stderr is exactly:

  ```text
  executable: error: expected '['

    foo[x]extra
          ^
  ```

- A nonnumeric selector at the root, including a nested opening bracket, reports `executable: error: expected number or ']'`; the caret is under the first character after the initial `[`. For `[text]`, stderr is exactly:

  ```text
  executable: error: expected number or ']'

    [text]
     ^
  ```

- A nested `[` after an ordinary root key reports `executable: error: expected text, number or ']'`. For `x[[y]]`, stderr is exactly:

  ```text
  executable: error: expected text, number or ']'

    x[[y]]
      ^
  ```

- A path beginning with `]` reports `executable: error: expected text or '['`, with the caret under that initial closing bracket. For `]foo`, stderr is exactly:

  ```text
  executable: error: expected text or '['

    ]foo
    ^
  ```

Caret placement uses display columns rather than UTF-8 byte offsets. For the path `emoji😀[x]extra`, the supplementary-plane emoji occupies two display columns and stderr is exactly:

```text
executable: error: expected '['

  emoji😀[x]extra
            ^
```

Existing scalar/object/array types are not silently converted when a later path needs an incompatible container. A type conflict's first line is exactly of the form `executable: error: Can't perform '<operation>' based access on '<resolved-prefix>' which has a type of '<actual-type>' but this operation requires a type of '<required-type>'.`, followed by the same blank-line/path/caret display. Operations are `key`, `index`, or `append`; types are rendered as `string`, `number`, `bool`, `object`, or `array`. The resolved prefix names the value on which the failing access is attempted (for example, `x`, nested `x[x]`, or the empty string for root access), not the complete input path. The carets span the complete failing bracket token. For example, `x=5 x[y]=10` produces exactly:

```text
executable: error: Can't perform 'key' based access on 'x' which has a type of 'string' but this operation requires a type of 'object'.

  x[y]
   ^^^
```

Correspondingly, an array used with `[abc]` reports `key`/`array`/`object`, a string, boolean, or object used with `[0]` reports `index` and requires `array` (the boolean type is spelled `bool`), and a string or object used with `[]` reports `append` and requires `array`.

## Spec 7: Offline request display

`--offline` fully constructs but does not send the request. It exits 0 and prints the portions of the synthetic request selected by the normal print rules. In its default useful form it displays an HTTP request line, headers, a blank line, and any body; `-v`/request print selectors make those sections explicit. For example:

```text
executable --offline --ignore-stdin GET https://example.com
```

begins with `GET / HTTP/1.1`, includes `Host: example.com`, `User-Agent: xh/0.25.3`, and has no body. Adding `name=alice age:=30` without an explicit method changes the line to POST, sets JSON headers and content length, and emits the compact body `{"name":"alice","age":30}`. Raw bodies pass through byte-for-byte. Offline mode honors all parsing, auth, headers, sessions, URL, HTTP-version, compression, and output-file rules that do not inherently require a server.

The synthetic request display is text-framed, not wire-framed: every displayed request line and header ends in one LF byte (`\n`, hexadecimal `0a`), never CRLF. The empty separator between headers and body is therefore exactly two consecutive LF bytes. Any selected body begins immediately after that separator and its payload bytes are unchanged, but the offline presentation appends two LF bytes after the displayed body. For example, `printf hi | executable --offline :1234` exits 0 with empty stderr and its stdout ends exactly `Host: localhost:1234\n\nhi\n\n`; the final two LF bytes are presentation framing, not body bytes. The same two-LF suffix follows raw and JSON bodies. This applies to every header, including JSON/form `Content-Type` and `Accept: */*`.

## Spec 8: Authentication and credential safety

`--auth/-a` defaults to Basic authentication. Split Basic/Digest credentials at the first colon only; passwords may contain further colons, equals signs, spaces, punctuation, and Unicode. Basic auth sends `Authorization: Basic ` followed by Base64 of the UTF-8 bytes of `USER:PASS`. A trailing colon represents an empty password. If a password is omitted entirely in an interactive context, it may be prompted for.

`--auth-type bearer --auth TOKEN` and `--bearer TOKEN` send `Authorization: Bearer TOKEN` without encoding or splitting the token, even if it contains colons or punctuation. An empty bearer token is accepted. `--auth-type digest` performs the standard HTTP Digest challenge-response flow: the first request is unauthenticated, a 401 Digest challenge triggers a second request with a computed `Digest` header, and a response that does not challenge remains a one-request success. Digest works with redirects and empty passwords. If auth is repeated, the last explicit credentials win.

An invalid type such as `--auth-type invalid` exits 2, writes nothing to stdout, and writes exactly:

```text
error: invalid value 'invalid' for '--auth-type <AUTH_TYPE>'
  [possible values: basic, bearer, digest]

For more information, try '--help'.
```

Unless disabled, credentials may be loaded from `$NETRC`, then `~/.netrc` or `~/_netrc`. The parser supports `machine`, `default`, `login`, `password`, optional `account`, comments, multiline entries, multiple machines, `macdef` sections, Unicode, and permissive file modes. A matching machine beats `default`; explicit CLI auth beats netrc. In bearer mode, a matching entry's password can be used as the token. `--ignore-netrc` disables automatic netrc credentials.

Authentication is preserved on same-origin redirects. Sensitive headers, including Authorization, Proxy-Authorization, and Cookie, are removed when a redirect crosses to a different host/origin.

Actual Authorization headers are visible when the user explicitly asks to print request headers (`-v`, `-vv`, or `--print=H`). However, `--debug` must redact credential-bearing parsed arguments in diagnostic structure dumps; raw passwords/tokens, including empty, Unicode, and special-character credentials, must not leak into debug diagnostics. When `--auth` is present, the `Cli` debug structure contains this exact field layout regardless of auth type and even when `--debug` is combined with `-v`:

```text
    auth: Some(
        (redacted),
    ),
```

When neither CLI nor other credentials populate that field, the same dump instead contains the literal line `    auth: None,` and contains no `(redacted)` marker for it.

After the complete `Cli { ... }` structure dump, debug output contains a line whose timestamped prefix is followed by the exact marker `DEBUG xh] Complete URL: ` and the normalized complete URL. For example, a request to `http://example.com` produces a line ending `DEBUG xh] Complete URL: http://example.com/`. This marker occurs after the closing brace of the CLI dump for Basic and bearer credentials, empty passwords, and repeated credentials, so that dump can be delimited without inspecting secret text.

## Spec 9: Sending requests, proxies, redirects, and protocol controls

The client performs real HTTP/1.0, HTTP/1.1, and HTTP/2 requests as selected by `--http-version` values `1.0`, `1.1`, `2`, and `2-prior-knowledge`. The parser also accepts `3-prior-knowledge`, but this build rejects request construction for it as specified below. HTTP/1.1 is the normal wire default in offline output. In the offline request line, both `--http-version=2` and `--http-version=2-prior-knowledge` display the version as `HTTP/2.0`, not `HTTP/2`; with test-mode terminal presentation, each begins exactly `GET / HTTP/2.0\n`. `--ipv4` and `--ipv6` constrain name resolution. `--interface` binds to an interface name or local address. `--unix-socket` connects through the supplied Unix-domain socket while retaining the URL's HTTP host/path semantics.

`--resolve HOST:ADDRESS` overrides DNS for that host; it is repeatable and accepts IPv4 or bracketed IPv6 addresses. Its input deliberately does not contain a port. In curl translation, when a port must be inferred from the request URL, stderr contains exactly one copy of `Warning: Inferred port number in --resolve from request URL.\n\n` for the invocation, including when multiple `--resolve` entries require the same inference. The following malformed values exit 2, write nothing to stdout, and produce these exact stderr bytes (including the blank line and final newline):

```text
error: invalid value 'invalid-format' for '--resolve <HOST:ADDRESS>': Value should be formatted as <HOST>:<ADDRESS>

For more information, try '--help'.
```

```text
error: invalid value 'example.com:8080:192.168.1.1' for '--resolve <HOST:ADDRESS>': Value should be formatted as <HOST>:<ADDRESS> (not <HOST>:<PORT>:<ADDRESS>)

For more information, try '--help'.
```

```text
error: invalid value 'example.com:invalid-ip' for '--resolve <HOST:ADDRESS>': Invalid address 'invalid-ip'

For more information, try '--help'.
```

`--proxy PROTOCOL:URL` is repeatable. Protocol is `http`, `https`, or `all`; the URL must be valid. A later proxy for the same protocol wins. `http_proxy`/`HTTP_PROXY`, `https_proxy`/`HTTPS_PROXY`, and `NO_PROXY` are supported; explicit `--proxy` settings replace environment-derived proxy configuration. Proxy credentials in the URL are allowed. If an HTTPS proxy answers the CONNECT request unsuccessfully, the request exits 1; for a proxy returning 502 to `--check-status --proxy=https:http://127.0.0.1:PORT GET https://example.test/get`, stdout is empty and stderr is exactly:

```text
executable: error: error sending request for url (https://example.test/get)

Caused by:
    0: client error (Connect)
    1: tunnel error: unsuccessful
```

The block has a final newline. Invalid proxy syntax and an unknown protocol exit 2, write nothing to stdout, and respectively write exactly:

```text
error: invalid value 'invalid-format' for '--proxy <PROTOCOL:URL>': The value passed to --proxy should be formatted as <PROTOCOL>:<PROXY_URL>

For more information, try '--help'.
```

```text
error: invalid value 'unknown:http://localhost:8080' for '--proxy <PROTOCOL:URL>': Unknown protocol to set a proxy for: unknown

For more information, try '--help'.
```

`--timeout SEC` applies to the request operation. Zero means no time limit; positive integer and fractional seconds are valid. Because a separate token beginning with `-` is parsed as another option, `--timeout -1` exits 2 with the ordinary `unexpected argument '-1' found` parser diagnostic and its `tip: to pass '-1' as a value, use '-- -1'` line. The joined spelling `--timeout=-1` reaches value validation and exits 2 with `invalid value '-1' for '--timeout <SEC>': Connection timeout is negative`. Overflow or infinity says `Connection timeout is too big`, and NaN/non-numeric input says `Connection timeout is not a valid number`. A request timeout exits 2 and reports `operation timed out`.

Redirects are not followed unless `--follow/-F` is effective, except that download mode enables following automatically. Relative and cross-scheme Location values are supported. For POST, 301/302/303 change the redirected method to GET as normal browser semantics require, while 307/308 preserve method and replay a buffered body. Invalid or non-UTF-8 redirect locations produce a warning rather than a panic where recovery is possible.

`--max-redirects N` limits the total requests in the chain: with value 3, two redirects succeed but a third redirect is rejected. Exceeding the limit exits 6, and a quiet/captured invocation writes nothing to stdout and writes exactly `executable: error: Too many redirects (--max-redirects=N)\n` to stderr, substituting the selected decimal value for `N`. Redirect loops are subject to the same failure.

`--all` prints each intermediate request/response while following. `--history-print FORMAT` selects only the fields shown for intermediates. Verbose implies `--all`. The final response still uses the normal `--print` selection.

TLS verification is enabled by default. `--verify no` or `--verify false` disables it; `yes`/`true` enables it; any other value is a custom CA-bundle path and replaces built-in roots. `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` also select a CA bundle. `--cert` selects a client certificate and `--cert-key` its separate private key. `--ssl` accepts `auto`, `tls1`, `tls1.1`, `tls1.2`, or `tls1.3`; with this required rustls-only build, TLS 1.0 and 1.1 are rejected even in offline mode, while auto/1.2/1.3 are accepted. For either `--ssl tls1` or `--ssl tls1.1`, the rejection exits 1, writes nothing to stdout, and writes exactly:

```text
executable: warning: rustls does not support older TLS versions. Consider building with the `native-tls` feature enabled.
executable: error: builder error

Caused by:
    empty supported tls versions
```

`--native-tls` fails nonzero and explains that the program was built without native-tls support.

Although `3-prior-knowledge` is a syntactically valid `--http-version` value and has the curl mapping in Spec 14, this required binary was built without the HTTP/3 feature and cannot construct such a request. This applies in offline mode too. `--offline --http-version=3-prior-knowledge :` exits 1, writes nothing to stdout, and writes exactly:

```text
executable: error: This binary was built without support for HTTP/3. Enable the `http3` feature.
```

## Spec 10: Status checking and exit codes

Status checking is enabled by default. It can be disabled with `--no-check-status`. It is also not implied when HTTPie compatibility mode is active, though explicit `--check-status` still enables it. Compatibility mode is activated by the presence (regardless of value, including an empty value) of `XH_HTTPIE_COMPAT_MODE`, or by invocation as `http`/`https`.

Exit statuses are:

```text
0  successful execution, including HTTP error responses when checking is disabled
1  syntax/construction failures not classified by the CLI parser, decoding failures,
   connection/DNS/TLS failures, and other generic network errors
2  command-line usage/URL errors and request timeouts
3  an unfollowed 3xx response when status checking is enabled
4  any 4xx response when status checking is enabled
5  any 5xx response when status checking is enabled
6  too many redirects
```

The response remains printable even when its status determines a nonzero exit. Status lines use uppercase conventional reason phrases, but a reason phrase received from an HTTP/1 server is preserved when available. When stdout is redirected and status checking causes a 3xx/4xx/5xx exit, write an explanatory status warning to stderr; `-q` still allows this checked-status warning, while `-qq` suppresses it.

Network failures include a readable cause chain. Connection refusal mentions `error sending request` and `Connection refused`. On this target platform, resolving `invalid-domain-that-does-not-exist-12345.com` fails with a cause chain containing the requested host, `Caused by:`, `client error (Connect)`, `dns error`, and the final line `failed to lookup address information: Name or service not known`. Compression decoding errors identify the algorithm. Ordinary failures must not emit debug logs/backtraces; `--debug` enables full cause/backtrace and low-level log output.

## Spec 11: Print selection

`--print/-p FORMAT` is a sequence containing only:

```text
H  request line and request headers
B  request body
h  response status line and response headers
b  response body
m  response metadata
```

Characters may be combined in any case-sensitive order; any other character is an error. `-h/--headers` means `--print=h`, `-b/--body` means `--print=b`, and `-m/--meta` means `--print=m`. Printed sections are separated by blank lines. Response headers begin with `HTTP/version status REASON`; header names are displayed in title case while values and receive order are preserved unless sorting is requested. Thus a received lowercase `hello: Rodos` header is displayed exactly as `Hello: Rodos`. Request headers begin with `METHOD path?query HTTP/version`.

Normal displayed response headers are text-framed just like the offline request display: every displayed status/header line ends in one LF byte (`\n`), never CRLF, and the separator after the headers is exactly a second LF. Header-only output therefore ends in `\n\n`; combined `hb` output begins the body immediately after that separator. This rule applies whether stdout is a terminal or a pipe and whether header sorting is enabled.

For example, `--print HBx URL` exits 2, writes nothing to stdout, and writes exactly the following to stderr (with a final newline):

```text
error: invalid value 'HBx' for '--print <FORMAT>': 'x' is not a valid value

For more information, try '--help'.
```

When stdout is not a terminal, the default is raw response body only with no ANSI color and no automatic pretty indentation. When stdout is a terminal, the normal presentation includes response headers and body with pretty formatting/color. `XH_TEST_MODE_TERM` being present forces terminal presentation decisions even when file descriptors are captured and also makes captured stdin count as terminal as specified in Spec 4. It does not itself force ANSI bytes; `XH_TEST_MODE_COLOR` is the separate color override (request methods use green and the HTTP version uses blue in the default style). `XH_TEST_MODE` enables the deterministic substitutions specified in Spec 18.

Terminal body presentation supplies a final presentation newline in addition to body bytes that already end in LF. Concretely, with `XH_TEST_MODE_TERM=1`, a captured `--print=b get URL` response having no media-type header and body bytes `foobar\n` exits 0 with empty stderr and stdout exactly `foobar\n\n`, with no ANSI escapes. Unknown/untyped and plain-text bodies are not wrapped in generic foreground-color escapes merely because terminal presentation is active.

`-v`/`--verbose` is equivalent to request headers + request body + response headers + response body and enables redirect history. `-vv` additionally prints response metadata. `-q` suppresses ordinary stdout/stderr but may retain the checked-status warning; `-qq` suppresses warnings too. Quiet output never suppresses the process exit status. `--output FILE` redirects exactly the selected normal output bytes to that file, overwriting an existing explicit output file. Its parent directory must already exist. Failure to open `/nonexistent_dir_12345_xh_test/output.json` because its parent is absent exits 1, writes nothing to stdout, and writes exactly `executable: error: No such file or directory (os error 2)\n` to stderr.

Metadata consists of lines in this form, with positive fractional seconds and the actual peer endpoint:

```text
Elapsed time: 0.00123s
Remote address: 127.0.0.1:8080
```

## Spec 12: Pretty modes and content recognition

`--pretty` accepts `all`, `colors`, `format`, and `none`:

- `all` enables syntax color and structural formatting.
- `colors` adds ANSI syntax color without changing whitespace.
- `format` formats without ANSI color.
- `none` preserves content bytes/text without either transformation.

In a terminal the default is `all`; with `NO_COLOR` it is `format`; when piped it is `none`. An explicit pretty option overrides this automatic choice. `--style` accepts `auto`, `solarized`, `monokai`, and `fruity`, using 256-color ANSI-compatible themes. HTML, XML, CSS, JavaScript, headers, and JSON receive syntax-aware coloring when colors are enabled. No ANSI sequences are emitted in non-color output.

Valid JSON is pretty printed with four-space indentation by default and key insertion order preserved. JSON formatting applies to declared JSON media types and may also be inferred for a valid JSON value served as `text/plain` or JavaScript. Malformed JSON is printed unchanged rather than failing. Non-JSON JavaScript, XML, HTML, CSS, URL-encoded form data, multipart data, unknown media types, and plain text retain their textual content (with syntax color only when requested). `text/event-stream` automatically streams without waiting for the complete response.

When stdout is a non-terminal pipe and JSON formatting is explicitly selected, a selected response body is followed by one blank line: the pretty-printed closing `}` is followed by exactly `\n\n`. This is unchanged by `json.indent`; both `json.indent:2` and `json.indent:8` have that exact ending. When formatted response headers are selected too, their LF-only blank separator precedes the body, and `headers.sort:true` sorts only the response-header lines rather than mixing body lines into the header set.

`--format-options` is a comma-separated set and repeated occurrences merge. Supported keys are:

```text
json.indent:NUM
json.format:true|false
headers.sort:true|false
```

Indent changes the JSON nesting width; disabling JSON formatting keeps it compact. Header sorting defaults on as part of formatting and can be disabled to preserve receive order. Keys outside the supported set, including `json.sort_keys`, `xml.format`, and `xml.indent`, are rejected rather than ignored. For example, `--format-options unknown.option:value` exits 2, writes nothing to stdout, and writes exactly:

```text
error: invalid value 'unknown.option:value' for '--format-options <FORMAT_OPTIONS>': Unknown option 'unknown.option'

For more information, try '--help'.
```

The unsupported `json.sort_keys` key uses `Unsupported option`, not `Unknown option`. `--format-options=json.sort_keys:true --offline http://example.org` exits 2, writes nothing to stdout, and writes exactly:

```text
error: invalid value 'json.sort_keys:true' for '--format-options <FORMAT_OPTIONS>': Unsupported option 'json.sort_keys'

For more information, try '--help'.
```

The unsupported XML-formatting keys retain the complete option value and identify the unsupported key in the CLI diagnostic. `--format-options xml.format:true URL` and `--format-options xml.indent:4 URL` each exit 2, write nothing to stdout, and respectively write exactly:

```text
error: invalid value 'xml.format:true' for '--format-options <FORMAT_OPTIONS>': Unsupported option 'xml.format'

For more information, try '--help'.
```

```text
error: invalid value 'xml.indent:4' for '--format-options <FORMAT_OPTIONS>': Unsupported option 'xml.indent'

For more information, try '--help'.
```

`--response-mime MIME` overrides content classification solely for display. `--response-charset ENCODING` overrides terminal/display decoding. Encoding names are case-insensitive and normalized; aliases include `u8`/`utf` for UTF-8, `u16` for UTF-16LE, underscore forms such as `utf_8`, and compact forms such as `iso88591`. Invalid names fail at argument processing. Otherwise charset comes from Content-Type or encoding detection. Text decoding is performed when needed for a terminal or formatting, but raw piped/binary output is not destructively transcoded.

An invalid name has an exact CLI diagnostic. `--response-charset invalid-encoding URL` exits 2, writes nothing to stdout, and writes:

```text
error: invalid value 'invalid-encoding' for '--response-charset <ENCODING>': invalid-encoding is not a supported encoding, please refer to https://encoding.spec.whatwg.org/#names-and-labels for supported encodings

For more information, try '--help'.
```

With both `XH_TEST_MODE` and `XH_TEST_MODE_TERM` present, a captured invocation using `--print=b` and any of `--response-charset=u8`, `--response-charset=utf`, or `--response-charset=utf_8` decodes response bytes `Hello World` to exactly `Hello World\n`, with no ANSI escapes or stderr. `--response-charset=iso88591` produces the same exact output for those ASCII response bytes. Using `--response-charset=u16` on the UTF-16LE encoding of the same text likewise exits 0 and prints exactly `Hello World\n` with empty stderr.

If a body appears binary (notably contains NUL/control bytes), do not dump it to a terminal. Print `NOTE: binary data not shown in terminal` instead. Request bodies that actually exist and are selected for diagnostic printing are screened this way, including offline `--print=B`; response bodies are screened in terminal presentation. As specified in Spec 4, however, `XH_TEST_MODE_TERM` makes captured stdin count as a terminal and ignores bytes supplied through it. Consequently, `XH_TEST_MODE_TERM=1 executable --offline --print=B example.com` with captured stdin bytes `a\0b` exits 0 with empty stdout and stderr: there is no selected request body and no binary-data note. When stdout is a pipe/file, binary response bytes pass through exactly.

`--stream/-S` requests streaming delivery but does not disable an explicitly selected presentation transform. In particular, `--stream --pretty=format` still JSON-formats a declared JSON response; in this combination JSON string escapes are preserved rather than decoded and re-encoded. With both test-mode variables present, a body of `{"hello": "\u4f60\u597d"}` returned as `application/json` to `--print=b -S --pretty=format post URL` produces exactly:

```text
{
    "hello": "\u4f60\u597d"
}


```

with empty stderr. Streaming retains correct decompression and terminal binary detection.

## Spec 13: Content encoding and request compression

The client advertises and automatically decodes the exact lowercase Content-Encoding tokens `gzip`, legacy `x-gzip`, zlib-wrapped `deflate`, Brotli `br`, and `zstd`. Matching is case-sensitive. Uppercase tokens such as `GZIP`, `X-GZIP`, `DEFLATE`, `BR`, and `ZSTD` are unrecognized and their encoded response bytes pass through unchanged. Large and chunked responses carrying a recognized lowercase encoding must stream/decode without truncation. If multiple Content-Encoding fields exist, use the first recognized encoding. Content-Encoding takes precedence over any compression implication from Transfer-Encoding. Any other encoding is treated as uncompressed rather than rejected.

HEAD responses, zero-length bodies, `Content-Length: 0`, and entirely empty bodies carrying a compression header produce empty success output rather than decoder errors. With `XH_TEST_MODE` and `XH_TEST_MODE_TERM` present and body-only output selected, an empty gzip response, a HEAD response carrying gzip metadata, and a gzip response with `Content-Length: 0` each exit 0 with empty stderr and stdout exactly `\n`, the terminal presentation newline; no response headers are printed.

A valid gzip stream's trailing bytes may be ignored. Malformed/truncated gzip, Brotli, zstd, and malformed zlib-deflate fail with exit 1 and `error decoding <algorithm> response body`; a truncated zlib stream may yield the decoder's available partial output successfully. In particular, a response whose body is the eight ASCII bytes `not gzip` while labeled `Content-Encoding: gzip` exits 1, writes nothing to stdout, and produces this exact newline-terminated stderr cause chain:

```text
executable: error: error decoding gzip response body

Caused by:
    unexpected end of file
```

For `Content-Encoding: br`, the algorithm name in the primary diagnostic is the human-readable `brotli`, not the wire token `br`; the newline-terminated primary diagnostic line is exactly `executable: error: error decoding brotli response body`. Raw RFC-1951 deflate without a zlib wrapper is rejected.

A truncated otherwise-valid gzip member exits 1, and its stderr ends with this exact cause (including the final newline):

```text
executable: error: error decoding gzip response body

Caused by:
    unexpected end of file
```

`--compress/-x` deflate-compresses the outgoing body and sets `Content-Encoding: deflate`. With one occurrence, skip compression if it makes the body larger; with `-xx`, force it. It works for JSON, form, raw, stdin, and whole-body files. If the user supplies a nonempty `Content-Encoding` header, compression is disabled, the supplied header and uncompressed body are sent, the command otherwise succeeds, and stderr contains exactly this newline-terminated warning:

```text
executable: warning: --compress can't be used with a 'Content-Encoding:' header. --compress will be disabled.
```

Compression cannot be combined with multipart. The conflict is a command-line parse error: it exits 2, writes nothing to stdout, and begins stderr with this exact line (followed by the normal blank line, usage, and help hint):

```text
error: the argument '--multipart' cannot be used with '--compress...'
```

## Spec 14: Curl translation

`--curl` prints one shell-ready curl command followed by a newline instead of sending a request. It never implicitly consumes redirected stdin, including a nonempty stream; data is translated only when selected by an explicit request item or body option. When used for a curl translation, `--curl-long` substitutes long spellings where curl provides them. Shell-sensitive arguments are single-quoted as needed; embedded query parameters are encoded. The emitted URL is the normalized serialization, so an input containing an authority but no path gains a root slash: `http://example.com` is emitted as `http://example.com/`. In the table below, `URL` means that normalized serialization. The translated command preserves functional ordering sufficiently to produce these canonical simple forms:

```text
GET URL                         curl -X GET URL
PUT URL                         curl -X PUT URL
PATCH URL                       curl -X PATCH URL
--follow URL                    curl -L URL
--follow --max-redirects 5 URL  curl -L --max-redirs 5 URL
--quiet URL                     curl -s URL
--stream URL                    curl -N URL
--check-status URL              curl -f URL
--verify no URL                 curl -k URL
--http-version 1.0 URL          curl --http1.0 URL
--http-version 1.1 URL          curl --http1.1 URL
--http-version 2 URL            curl --http2 URL
--http-version 2-prior-knowledge URL
                                curl --http2-prior-knowledge URL
--http-version 3-prior-knowledge URL
                                curl --http3-only URL
--curl-long --verify no URL     curl --insecure URL
--curl-long --stream URL        curl --no-buffer URL
--curl-long --check-status URL  curl --fail URL
--curl-long HEAD URL            curl --head URL
--curl-long OPTIONS URL         curl --include --request OPTIONS URL
--curl-long --proxy all:localhost:8080 URL
                                curl --proxy localhost:8080 URL
--curl-long --ipv4 URL          curl URL --ipv4
--curl-long --ipv6 URL          curl URL --ipv6
--timeout 30 URL                curl --max-time 30 URL
--auth-type basic --auth user:pass URL
                                curl URL --basic -u user:pass
```

For the authority-only input `http://example.com`, every form in this table ends in `http://example.com/`. For example, the short forms produce exactly `curl -L http://example.com/\n`, `curl --http2-prior-knowledge http://example.com/\n`, and `curl --max-time 30 http://example.com/\n`; the long forms produce exactly `curl --insecure http://example.com/\n`, `curl --no-buffer http://example.com/\n`, `curl --fail http://example.com/\n`, `curl --head http://example.com/\n`, `curl --include --request OPTIONS http://example.com/\n`, and `curl --proxy localhost:8080 http://example.com/\n`.

Option order and quoting are observable. These invocations exit 0 and produce the exact newline-terminated stdout shown:

```text
--curl --interface eth0 http://httpbin.org/get
    curl http://httpbin.org/get --interface eth0
--curl --unix-socket /tmp/socket.sock http://localhost/api
    curl http://localhost/api --unix-socket /tmp/socket.sock
--curl --ignore-netrc http://httpbin.org/get
    curl http://httpbin.org/get --no-netrc
--curl --verbose --check-status --follow --output /tmp/out.txt http://httpbin.org/get
    curl -v -f -L -o /tmp/out.txt http://httpbin.org/get
--curl --curl-long --verbose --quiet --debug http://httpbin.org/get
    curl --verbose --silent --trace - http://httpbin.org/get
--curl --follow POST http://httpbin.org/post
    curl -L -X POST http://httpbin.org/post
--curl --follow --max-redirects 5 --ssl tls1.2 --http-version 2 http://httpbin.org/get
    curl -L --max-redirs 5 --tlsv1.2 --tls-max 1.2 --http2 http://httpbin.org/get
--curl --raw 'hello world' http://httpbin.org/post
    curl http://httpbin.org/post -H 'content-type: application/json' -H 'accept: application/json, */*;q=0.5' -d 'hello world'
```

The verbose combinations above can also emit the already-specified ignored-option warnings on stderr; those warnings do not alter stdout.

Mappings include:

- explicit methods -> `-X METHOD`, except an ordinary HEAD method -> `-I`; OPTIONS also includes response headers (`-i -X OPTIONS`);
- `-h/--headers` -> `-I` plus explicit `-X METHOD` because xh's flag controls output rather than changing its request method;
- headers -> lowercase `-H 'name: value'`; unset headers -> `-H name:`; empty headers -> `-H 'name;'`;
- JSON -> compact `-d 'JSON'` plus lowercase JSON Content-Type and Accept headers;
- URL-encoded form fields -> one `--data-urlencode 'name=value'` each; the payload remains single-quoted even when its characters are otherwise shell-safe;
- raw -> `-d`, retaining the serialization mode's Content-Type/Accept headers;
- multipart text/file/file-content fields -> `-F` (`--form` in long mode), preserving type and filename annotations; each complete field payload is single-quoted even when shell-safe, so `--curl --multipart http://httpbin.org/post key=value` prints exactly `curl http://httpbin.org/post -F 'key=value'\n`, and a file part is rendered like `-F 'file=@path'`;
- whole body file -> `--data-binary @path` and an inferred Content-Type;
- Basic/Digest -> `--basic/--digest -u credentials`; bearer -> `--oauth2-bearer token`;
- protocol-specific proxies -> `http_proxy=value` or `https_proxy=value` environment prefixes; `all` -> `-x value`;
- timeout -> `--max-time`, follow -> `-L`, maximum redirects -> `--max-redirs`;
- download -> `-f -L -O`, or `-f -L -o FILE`; resume adds `-C -`;
- debug -> `--trace -`; verbose -> `-v`; output -> `-o`; IPv4/IPv6 -> `-4`/`-6`;
- client certificate -> `-E FILE`, key -> `--key FILE`, CA bundle -> `--cacert FILE`;
- TLS 1.0/1.1/1.2/1.3 -> paired `--tlsv1.N --tls-max 1.N`;
- interface and Unix socket -> `--interface` and `--unix-socket`;
- ignore netrc -> `--no-netrc`;
- resolve -> curl's `--resolve HOST:PORT:ADDRESS`, inferring 80 or 443 from the request URL and emitting the exact warning specified in Spec 9;
- URL bracket/brace glob characters -> `-g`/`--globoff` and a quoted URL.

Long mode uses forms such as `--request`, `--include`, `--head`, `--verbose`, `--silent`, `--location`, `--fail`, `--output`, `--continue-at`, `--no-buffer`, `--insecure`, `--cert`, `--proxy`, `--ipv4`, and `--ipv6` instead of their short equivalents.

Translation prints warnings to stderr for xh-only options it ignores: offline, print/body, pretty/style, session, compression, response charset/mime, history-print, native-tls, and all-history display. The tested warning lines are exactly:

```text
Warning: Ignored --offline
Warning: Ignored --pretty
Warning: Ignored -s/--style
Warning: Ignored -x/--compress
Warning: Ignored --response-charset
Warning: Ignored --response-mime
Warning: Ignored --all
Warning: Ignored -P/--history-print
Warning: Ignored --session
Warning: Ignored --native-tls
```

When one or more such warnings occur, they are written in the fixed implementation order shown above (omitting absent warnings) as adjacent newline-terminated lines, followed by one additional newline after the final warning. Thus one warning ends in `\n\n`; `--pretty all --style monokai --session session.json` produces exactly `Warning: Ignored --pretty\nWarning: Ignored -s/--style\nWarning: Ignored --session\n\n`, regardless of the relative order of those three options. These warnings do not change the successful exit status.

Combining explicit POST with `--follow` emits exactly `Warning: Using a combination of -X/--request and -L/--location which may cause unintended side effects.\n\n`. Combining `-h/--headers` with a data-bearing POST emits exactly `Warning: -I/--head is incompatible with sending data. Consider omitting -h/--headers.\n\n`. Translation still exits 0 for these warnings.

Literal JSON fields are rejected in multipart curl translation just as in a sent multipart request. `--curl --multipart http://httpbin.org/post field:=1` exits 1, writes nothing to stdout, and writes exactly `executable: error: JSON values are not supported in multipart fields\n` to stderr.

## Spec 15: Sessions and configuration

`--session FILE_OR_NAME` loads existing state, applies it to the request, merges explicit request state, receives cookies, and writes updated state. `--session-read-only` loads and applies the same state but never alters an existing file's bytes or modification time; concurrent read-only access is allowed. A missing writable session is initialized. Parent directories for explicit writable session paths are created. A value containing a path separator is an explicit path. A simple name is stored below `$XH_CONFIG_DIR/sessions/<host-directory>/<name>.json` (using the platform default config directory if the variable is absent). For a URL with an explicit non-default port, `<host-directory>` is `<host>_<port>`: for example, `http://127.0.0.1:38254/plain` with session name `named` uses `sessions/127.0.0.1_38254/named.json`. Without such a port, the host directory is the host. Invalid host components `.` and `..` are rejected.

Session JSON has this schema and pretty layout semantics:

```json
{
    "__meta__": {
        "about": "xh session file",
        "xh": "0.25.3"
    },
    "auth": {
        "type": null,
        "raw_auth": null
    },
    "cookies": [],
    "headers": []
}
```

Stored header entries are `{"name":"lower-case-name","value":"value"}`. Distinct headers accumulate; a later invocation explicitly setting an existing case-insensitive header replaces its prior value, while duplicate occurrences in one invocation remain duplicate entries. Headers not mentioned later persist. Large and punctuation-containing values are preserved. Auth stores `type` (`basic`, `bearer`, or `digest`) and unmodified `raw_auth`, is reused on subsequent requests, and remains unless explicitly replaced. Credentials acquired solely from netrc are not persisted.

Cookies from Set-Cookie are stored with name/value/domain and applicable path, secure, and expiry fields. A missing Domain defaults to the request host. A missing Path defaults to the request directory (`/some/path` for `/some/path/file`, `/` at root). Domain, path, and Secure matching control which cookies are sent. Cookies are isolated by domain; expired cookies are pruned. Explicit Cookie request values override same-name stored cookies for the outgoing request, while the server's subsequent Set-Cookie value becomes the persisted value.

Older session shapes are migrated: legacy headers represented as a mapping become header entries; legacy cookies missing domain/path gain the current request host and default path; a historical localhost-local domain is normalized. Unknown auth types fail with the credential-based diagnostic specified below. Malformed or empty JSON fails with `executable: error: couldn't load session "PATH"`, followed by a blank line, `Caused by:`, and the JSON parser reason. It must not silently discard corrupt data.

Session-loaded request headers are displayed in HTTP title case, including legacy mapping keys: `x-custom-header` becomes `X-Custom-Header` and `x-api-key` becomes `X-Api-Key`. In the normal non-pretty offline display, request headers are not alphabetically sorted. For an empty session and an inherited empty nonterminal stdin, this exact invocation shape:

```text
executable --offline --session FILE --print=HhBb http://example.com
```

prints the following bytes; the empty redirected body supplies JSON intent and the four final LF bytes are significant:

```text
POST / HTTP/1.1
Accept-Encoding: gzip, deflate, br, zstd
User-Agent: xh/0.25.3
Connection: keep-alive
Accept: application/json, */*;q=0.5
Content-Type: application/json
Content-Length: 0
Host: example.com


```

Equivalently, the byte suffix is `Host: example.com\n\n\n\n`. A session-derived `Authorization`, `Cookie`, or persisted custom-header line is inserted after `Content-Type` and before `Content-Length`; multiple persisted custom headers retain their session order. `Content-Length` then precedes the final `Host` line. This ordering and LF-only framing also applies when the host includes a port, when cookie domain/path/secure matching omits or supplies `Cookie`, when a `localhost.local` cookie is migrated for `localhost`, and for writable and read-only session reuse.

For a named session, URLs whose host is exactly `.` or `..` reach session-host extraction rather than the ordinary international-domain diagnostic. They exit 1, write nothing to stdout, and write exactly (substituting the requested session name):

```text
executable: error: couldn't load session "test_session"

Caused by:
    couldn't extract host from url
```

If stored auth has an unrecognized `type`, the error reports the stored `raw_auth` value rather than the unknown type name. For `{"type":"kerberos","raw_auth":"some_token"}`, exit status is 1, stdout is empty, and stderr is exactly `executable: error: Unknown auth type some_token\n`.

The JSON parser reasons are also part of the diagnostic. A session whose complete contents are `{ invalid json }` ends its cause chain with `    key must be a string at line 1 column 3\n`; a zero-byte session ends it with `    EOF while parsing a value at line 1 column 0\n`.

`XH_CONFIG_DIR` selects both `config.json` and named-session storage. `config.json`, when present, is JSON with a `default_options` string array. Those arguments act as defaults before actual CLI arguments; command-line repeats or `--no-OPTION` can override them. A missing file is silent. Malformed JSON or an invalid schema prints a warning but the requested command (including help) continues. Unlike ordinary diagnostics, this warning uses the fixed product-name prefix `xh:` even when the executable is invoked as `executable`; the warning text begins exactly `xh: warning: Unable to parse config file:`. The warning is surrounded by a leading and trailing blank line in both ordinary nonterminal capture (with neither test-mode variable set) and terminal test presentation: stderr starts with one LF before `xh:` and has two consecutive LF bytes after the parser reason.

For a `config.json` whose complete contents are `{ invalid json }`, the parser reason is part of the warning. A help invocation still exits 0 and stderr is exactly:

```text

xh: warning: Unable to parse config file: key must be a string at line 1 column 3

```

## Spec 16: Download behavior

`--download/-d` follows redirects, requests identity transfer encoding, and routes decoded response-body bytes to a download destination instead of normal response presentation. `--output FILE` gives the exact path and overwrites it. Without `--output`, choose a safe non-overwriting filename when stdout is a terminal, but stream to stdout when it is not a terminal as specified below. Auto-name collisions append `-1`, `-2`, and so on after the complete filename (`data.txt-1`). Explicit output parents must exist.

Automatic naming precedence is:

1. a valid nonempty `Content-Disposition` filename;
2. the last nonempty URL path segment from the original requested URL (not the final redirect URL), with query and fragment removed;
3. `index`.

`filename*` takes precedence over `filename`. Parse attachment and inline dispositions case-insensitively, quoted or unquoted values, whitespace, language tags, and redundant semicolons. RFC 5987 percent decoding supports UTF-8 and ISO-8859-1/Windows-1252 (including bytes such as 0x99 -> ™), with case-insensitive charset names. Unknown charsets attempt UTF-8; malformed extended values fall back to ordinary filename when available, otherwise use a safe decoded/fallback result. Ordinary `filename` percent characters are literal; encoded `filename*` special characters are decoded.

Sanitize generated names so they can create only one file in the current directory: each `/` or `\` path separator is replaced by one underscore, while dots that are not leading dots remain intact; control characters and path traversal cannot create directories. Replace decoded double-quote characters with underscores; trim surrounding whitespace and all leading dots. Thus a received ordinary filename `\..\..\malicious.txt` selects exactly `_.._.._malicious.txt`, and `filename*=UTF-8''file%20with%20%22quotes%22.txt` selects exactly `file with _quotes_.txt`. If sanitization leaves no usable name, use the URL/index fallback. Spaces, parentheses, brackets, Unicode, and emoji are otherwise retained.

When automatic-file mode is active, infer a common extension from Content-Type if the chosen name has none. Required mappings include HTML, plain text, JSON, PNG and other common images, PDF, video, and audio; specifically, `audio/mpeg` maps to `.mpga`, not `.mp3`. Never append or replace an extension when the name already has one. In that mode, an empty response creates an empty file. In nonterminal-stdout mode, even an empty response, an extension-bearing Content-Type, or a Content-Disposition filename still uses stdout and creates no file. Unknown Content-Length and large/binary bodies are supported. Gzip, deflate, Brotli, and zstd downloads store decompressed bytes at whichever destination mode selected.

Progress is written only to stderr, never stdout. Before transfer it announces the quoted destination. With a known length the line is `Downloading SIZE to "PATH"`; for example, a 5-byte response automatically saved as `tiny.txt` prints `Downloading 5 B to "tiny.txt"`. With no Content-Length it is exactly `Downloading to "PATH"`, so explicit output paths are included verbatim and in double quotes. An automatically selected collision name is likewise announced—for an existing `file.txt`, a 10-byte response causes stderr to contain `Downloading 10 B to "file.txt-1"` before writing `file.txt-1`.

The progress display uses bytes/percentage/speed when length is known and a spinner-style display when unknown; very fast transfers remain well formed. On success, its final line begins `Done. ` followed by the human-readable transferred size. Byte counts below 1024 use the unit `B`, not `bytes`, so a five-byte transfer begins its final line exactly `Done. 5 B`; 6081 bytes are rendered as `Done. 5.94 KiB`. Timing and speed follow on that line. This applies to transfers larger than 1024 bytes too, and the label must not be replaced by `Complete:`. Quiet mode suppresses progress. When stdout is not a terminal and `--output` is absent, download mode streams the response body to stdout rather than choosing an automatic filename; it creates no destination file and identifies the progress destination as `"<stdout>"`. For example, a 200 response body `stdout content\n` produces those exact bytes on stdout.

`--continue/-c` requires both `--download` and `--output`; missing either is a usage error listing the missing flags. In particular, `--continue URL` exits 2, writes nothing to stdout, and writes exactly:

```text
error: the following required arguments were not provided:
  --download
  --output <FILE>

Usage: executable --download --output <FILE> --continue <[METHOD] URL> [REQUEST_ITEM]...

For more information, try '--help'.
```

To resume an existing N-byte file, send `Range: bytes=N-`. A 206 response must contain a valid `Content-Range: bytes N-LAST/TOTAL` or `bytes N-LAST/*`, start exactly at N, have coherent increasing bounds, and have LAST below a numeric TOTAL. Append only after validation. Missing, malformed, wrongly-started, or inconsistent Content-Range fails with exit 1 without changing the existing destination. The primary diagnostic lines for the exercised cases are exactly:

```text
executable: error: Missing Content-Range header
executable: error: Invalid Content-Range: "bytes 10-5/20"
executable: error: Content-Range has wrong start: "bytes 5-9/10"
executable: error: Content-Range has wrong start: "bytes 6-10/11"
```

Each applicable line is newline-terminated. In terminal presentation, displayed response headers precede it on stderr. If the server returns 200, restart/overwrite with the full response rather than append.

For a resume request, a 416 response—including a bare 416 with no `Content-Range` header—is treated as success: leave the existing destination unchanged, exit 0, and print `Download "PATH" is already complete` as a newline-terminated stderr line (after displayed response headers in terminal presentation).

A user-supplied `Range:` header takes precedence over `--continue`; it does not cause a usage error. Disable continue processing, perform the request using the supplied range, and exit according to that request. Before the response/progress display, stderr contains exactly this newline-terminated warning:

```text
executable: warning: --continue can't be used with a 'Range:' header. --continue will be disabled.
```

HTTP 4xx/5xx download responses retain normal check-status exit codes and must not be confused with successful file transfer.

## Spec 17: Generated artifacts

`--generate KIND` is a standalone operation and cannot be combined with a URL/request. Valid, case-sensitive values are:

```text
complete-bash
complete-elvish
complete-fish
complete-nushell
complete-powershell
complete-zsh
man
```

Combining a valid generation kind with a URL is a CLI usage error. For example, `--generate complete-bash http://example.com` exits 2, writes nothing to stdout, and writes exactly:

```text
error: the argument '--generate <KIND>' cannot be used with '<[METHOD] URL>'

Usage: executable --generate <KIND> <[METHOD] URL> [REQUEST_ITEM]...

For more information, try '--help'.
```

Each successful kind exits 0, emits only to stdout, and produces a complete, nontrivial artifact for the invoked command name `executable`, covering all public and compatibility options, their enumerated values, and the supported `--no-*` forms. In particular, every artifact includes `--version` but omits the unsupported `--no-version`. Completion output must use each shell's normal native structure: Bash defines `_executable` and `COMPREPLY`; Zsh starts with `#compdef executable`; Fish contains `complete -c executable` directives plus custom `@` file completion; PowerShell registers an argument completer; Elvish assigns an argument completer and emits candidates; Nushell defines an `export extern executable` module and value completers. The scripts must be syntactically usable rather than placeholder text.

The exact completion bytes are normative fixtures in `completion-fixtures/` next to this document; generated output for the corresponding kind must equal the entire named file, including its final LF. The fixture identities observed for invocation name `executable` are:

```text
kind                 bytes  lines  SHA-256
complete-bash         7296    178  124a131961267679a3fe54480ffe0e64c1134ce9e336c81da139a2451f4b7858
complete-elvish       8551    153  c7eb2c0f14ba2f93e8ddd712b1f79d8ae7156d023768166f37e4a1bafa98b93f
complete-fish         7789    136  982bbba0830d475d18fb21c546f4dd45ea898359a1329248aa03ef7fc751ce18
complete-nushell      6376    142  12c08dbe941c6bd6033396fa1e7af6d412c25985840e94ac858f46d8e7ca1ab8
complete-powershell  18730    159  a3519e8051aebc5e007319fd55539d62b25fe4f88e2b186a7298a2b6c6607cba
complete-zsh          7500    165  12d02ad67aac8668d7a10448740d52d0bb72e4767feb96f532d9c86012c90ded
```

Generation kinds are case-sensitive. For example, `--generate COMPLETE-BASH` exits 2, writes nothing to stdout, and writes exactly:

```text
error: invalid value 'COMPLETE-BASH' for '--generate <KIND>'
  [possible values: complete-bash, complete-elvish, complete-fish, complete-nushell, complete-powershell, complete-zsh, man]

For more information, try '--help'.
```

Supplying `--generate` without a value also exits 2, writes nothing to stdout, and writes exactly:

```text
error: a value is required for '--generate <KIND>' but none was supplied
  [possible values: complete-bash, complete-elvish, complete-fish, complete-nushell, complete-powershell, complete-zsh, man]

For more information, try '--help'.
```

`man` produces a full roff manual with a `.TH XH 1 YYYY-MM-DD 0.25.3 "User Commands"` heading and NAME, SYNOPSIS, DESCRIPTION, POSITIONAL ARGUMENTS, OPTIONS, EXIT STATUS, ENVIRONMENT, FILES, and EXAMPLES sections. The exact output for `SOURCE_DATE_EPOCH=1234567890 executable --generate man` is the normative `generated-fixtures/man-source-date-epoch-1234567890` file next to this document: 13,511 bytes, 458 lines, final LF, SHA-256 `fd1bf6ce2c05c2c1cdf5fad2cf9036580cd5ab1ae1e1b2a7f057065843415bae`. The date is the current UTC date unless `SOURCE_DATE_EPOCH` is present, in which case use that epoch reproducibly (for `1234567890`, `2009-02-13`). Missing/invalid/case-mismatched kinds exit 2 and list the valid values.

## Spec 18: Environment summary and robustness

The observable environment variables are:

```text
XH_CONFIG_DIR             config.json and named-session root
XH_HTTPIE_COMPAT_MODE     presence enables compatibility mode
NETRC                     explicit netrc path
NO_COLOR                  disables automatic color
http_proxy/HTTP_PROXY     HTTP proxy
https_proxy/HTTPS_PROXY   HTTPS proxy
NO_PROXY                  comma-separated proxy bypass, with * matching all
REQUESTS_CA_BUNDLE        custom CA bundle
CURL_CA_BUNDLE            custom CA bundle
RUST_LOG                  debug-log filtering when debug logging is enabled
SOURCE_DATE_EPOCH         reproducible generated-manual date
XH_TEST_MODE              deterministic test behavior
XH_TEST_MODE_TERM         force terminal presentation decisions
XH_TEST_MODE_COLOR        force ANSI color, including through a pipe
XH_TEST_DIGEST_AUTH_CNONCE deterministic Digest cnonce when supplied
```

`XH_TEST_MODE` replaces network-dependent request identity in deterministic displays: the Host is `http.mock` and the User-Agent is `xh/0.0.0 (test mode)`. It also replaces the `"xh"` version in newly written session metadata with `"0.0.0"`; without test mode, the session schema shown in Spec 15 uses `"0.25.3"`. Together with `XH_TEST_MODE_TERM`, the invocation `--offline --resolve example.org:[::1] example.org` exits 0, writes nothing to stderr, contains no ANSI escapes, and writes exactly:

```text
GET / HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate, br, zstd
Connection: keep-alive
Host: http.mock
User-Agent: xh/0.0.0 (test mode)

```

The same uncolored, LF-only deterministic rendering applies after URL shorthand expansion. With both test variables present, `--offline ://example.org/path` and `--offline :8080/test` exit 0 with empty stderr and respectively write exactly:

```text
GET /path HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate, br, zstd
Connection: keep-alive
Host: http.mock
User-Agent: xh/0.0.0 (test mode)

```

```text
GET /test HTTP/1.1
Accept: */*
Accept-Encoding: gzip, deflate, br, zstd
Connection: keep-alive
Host: http.mock
User-Agent: xh/0.0.0 (test mode)

```

The program must handle large request fields, large output files, responses exceeding 5 MB after decompression, small/choppy reads, interrupted reads where retry is valid, empty bodies, binary bytes, Unicode filenames/credentials/headers, and broken stdout pipes without hanging or panicking. Files written through `--output` or download contain exact intended bytes and flush fully before successful exit.
