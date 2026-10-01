# Curlie executable specification

The required artifact is a runnable file named exactly `executable`. It is a command-line front end to a harness-provided `curl` command. The implementation must find and invoke `curl` through `PATH`; `curl` itself is not part of the artifact to implement. Unless a rule below says otherwise, bytes produced by curl on stdout are the response body and bytes produced by curl on stderr are diagnostics/verbose headers. Argument strings, header values, JSON strings, URLs, and response bytes must be preserved without ASCII-only assumptions.

## Spec 1

The command-line grammar is:

```text
executable [options...] [METHOD] URL [REQUEST_ITEM [REQUEST_ITEM ...]]
```

Options may be mixed with positionals on either side of the URL. A standalone `--` ends option parsing and is itself discarded. The first recognized method token, if present, is handled as described below; after removing that method and option values from consideration, the first remaining positional is the URL even when its spelling matches request-item syntax. Only later positionals are classified as request items. Remaining unrecognized positional strings are retained as additional curl operands, rather than silently discarded. Unknown options are also forwarded to curl rather than rejected by curlie. This matters, for example, for a request containing a final operand `baditem`: curl attempts that operand too and its resolution diagnostic remains visible.

With no arguments, invoke curl with exactly `-h`, `all`, `-H`, and `Accept: application/json, */*`, in that order. Curlie's help output depends on that child invocation: the reference environment's real curl produces the full table in Spec 3 with empty stderr and status 0, while a harness replacement which prints nothing and exits 0 makes curlie produce empty stdout and stderr and status 0. This is not a no-child parser-error path.

## Spec 2

`-h` and `--help` execute the curl found through `PATH`; help does not preempt other request processing. Preserve a following category as a separate curl argument. For example, with non-terminal stdin, `--help all`, `--help wat`, `--help http`, and `--help auth` are respectively followed by the appended `-s -S -H "Accept: application/json, */*"`. A bare `--help`, including when invoked through a differently named symlink, is followed by the same defaults.

Help stdout is conditional on what that curl process emits. A replacement curl that exits 0 with empty stdout yields empty curlie stdout for every help form. With the reference environment's real curl, bare or unknown-category help produces the category-list form below, and a valid category produces a usage line, its `CATEGORY: DESCRIPTION` heading, and its rows. In these real-curl forms, `ARGV0` is replaced by curlie's actual invocation path, including a symlink path. There is no internally synthesized fallback when the child emits nothing.

When a help option is mixed with a URL and other options, process it as a request. The invocation `http://bad.invalid --nonesuch -h` writes `http://bad.invalid` plus newline to stderr and invokes curl with `--nonesuch`, `-h`, `http://bad.invalid`, `-s`, `-S`, `-H`, and `Accept: application/json, */*`, in that order.

The reference environment's real-curl category-list form is exactly:

```text
Usage: ARGV0 [options...] [METHOD] URL [REQUEST_ITEM [REQUEST_ITEM ...]]
Invalid category provided, here is a list of all categories:

 auth        Different types of authentication methods
 connection  Low level networking operations
 curl        The command line tool itself
 dns         General DNS options
 file        FILE protocol options
 ftp         FTP protocol options
 http        HTTP and HTTPS protocol options
 imap        IMAP protocol options
 misc        Options that don't fit into any other category
 output      Filesystem output
 pop3        POP3 protocol options
 post        HTTP Post specific options
 proxy       All options related to proxies
 scp         SCP protocol options
 sftp        SFTP protocol options
 smtp        SMTP protocol options
 ssh         SSH protocol options
 telnet      TELNET protocol options
 tftp        TFTP protocol options
 tls         All TLS/SSL related options
 upload      All options for uploads
 verbose     Options related to any kind of command line output of curl
```

Here `ARGV0` is a placeholder in this specification only. In this real-curl output it is replaced by the actual path used to invoke curlie.

For valid real-curl categories, `http` has description `HTTP and HTTPS protocol options` and includes `--http0.9`, `--hsts`, `--etag-save`, `--etag-compare`, `--expect100-timeout`, `-G, --get`, `-I, --head`, `-H, --header`, `-d, --data`, `-F, --form`, `--compressed`, and `--cookie`. Category `auth` has description `Different types of authentication methods` and includes `--anyauth`, `--basic`, `--digest`, and `--user`. Categories `dns`, `tls`, `output`, and `proxy` likewise show their relevant rows.

## Spec 3

The option table below is curlie's supported-option and arity inventory. It is also the exact stdout, including its final newline and `ARGV0` substitution, when the reference environment's real curl is used for either the no-argument translation in Spec 1 or `--help all`. A replacement curl's stdout is used instead, including empty output. `--help all` is forwarded as `--help`, `all`, then the normal appended defaults, whereas no arguments use the special translation in Spec 1. The angle-bracketed words document which options take a following value during curlie's translation.

```text
Usage: ARGV0 [options...] [METHOD] URL [REQUEST_ITEM [REQUEST_ITEM ...]]
     --abstract-unix-socket <path> Connect via abstract Unix domain socket
     --alt-svc <file name> Enable alt-svc with this cache file
     --anyauth            Pick any authentication method
 -a, --append             Append to target file when uploading
     --aws-sigv4 <provider1[:provider2[:region[:service]]]> Use AWS V4 signature authentication
     --basic              Use HTTP Basic Authentication
     --cacert <file>      CA certificate to verify peer against
     --capath <dir>       CA directory to verify peer against
 -E, --cert <certificate[:password]> Client certificate file and password
     --cert-status        Verify the status of the server cert via OCSP-staple
     --cert-type <type>   Certificate type (DER/PEM/ENG)
     --ciphers <list of ciphers> SSL ciphers to use
     --compressed         Request compressed response
     --compressed-ssh     Enable SSH compression
 -K, --config <file>      Read config from a file
     --connect-timeout <fractional seconds> Maximum time allowed for connection
     --connect-to <HOST1:PORT1:HOST2:PORT2> Connect to host
 -C, --continue-at <offset> Resumed transfer offset
 -b, --cookie <data|filename> Send cookies from string/file
 -c, --cookie-jar <filename> Write cookies to <filename> after operation
     --create-dirs        Create necessary local directory hierarchy
     --create-file-mode <mode> File mode for created files
     --crlf               Convert LF to CRLF in upload
     --crlfile <file>     Use this CRL list
     --curves <algorithm list> (EC) TLS key exchange algorithm(s) to request
 -d, --data <data>        HTTP POST data
     --data-ascii <data>  HTTP POST ASCII data
     --data-binary <data> HTTP POST binary data
     --data-raw <data>    HTTP POST data, '@' allowed
     --data-urlencode <data> HTTP POST data url encoded
     --delegation <LEVEL> GSS-API delegation permission
     --digest             Use HTTP Digest Authentication
 -q, --disable            Disable .curlrc
     --disable-eprt       Inhibit using EPRT or LPRT
     --disable-epsv       Inhibit using EPSV
     --disallow-username-in-url Disallow username in url
     --dns-interface <interface> Interface to use for DNS requests
     --dns-ipv4-addr <address> IPv4 address to use for DNS requests
     --dns-ipv6-addr <address> IPv6 address to use for DNS requests
     --dns-servers <addresses> DNS server addrs to use
     --doh-cert-status    Verify the status of the DoH server cert via OCSP-staple
     --doh-insecure       Allow insecure DoH server connections
     --doh-url <URL>      Resolve host names over DoH
 -D, --dump-header <filename> Write the received headers to <filename>
     --egd-file <file>    EGD socket path for random data
     --engine <name>      Crypto engine to use
     --etag-compare <file> Pass an ETag from a file as a custom header
     --etag-save <file>   Parse ETag from a request and save it to a file
     --expect100-timeout <seconds> How long to wait for 100-continue
 -f, --fail               Fail silently (no output at all) on HTTP errors
     --fail-early         Fail on first transfer error, do not continue
     --fail-with-body     Fail on HTTP errors but save the body
     --false-start        Enable TLS False Start
 -F, --form <name=content> Specify multipart MIME data
     --form-escape        Escape multipart form field/file names using backslash
     --form-string <name=string> Specify multipart MIME data
     --ftp-account <data> Account data string
     --ftp-alternative-to-user <command> String to replace USER [name]
     --ftp-create-dirs    Create the remote dirs if not present
     --ftp-method <method> Control CWD usage
     --ftp-pasv           Use PASV/EPSV instead of PORT
 -P, --ftp-port <address> Use PORT instead of PASV
     --ftp-pret           Send PRET before PASV
     --ftp-skip-pasv-ip   Skip the IP address for PASV
     --ftp-ssl-ccc        Send CCC after authenticating
     --ftp-ssl-ccc-mode <active/passive> Set CCC mode
     --ftp-ssl-control    Require SSL/TLS for FTP login, clear for transfer
 -G, --get                Put the post data in the URL and use GET
 -g, --globoff            Disable URL sequences and ranges using {} and []
     --happy-eyeballs-timeout-ms <milliseconds> Time for IPv6 before trying IPv4
     --haproxy-protocol   Send HAProxy PROXY protocol v1 header
 -I, --head               Show document info only
 -H, --header <header/@file> Pass custom header(s) to server
 -h, --help <category>    Get help for commands
     --hostpubmd5 <md5>   Acceptable MD5 hash of the host public key
     --hostpubsha256 <sha256> Acceptable SHA256 hash of the host public key
     --hsts <file name>   Enable HSTS with this cache file
     --http0.9            Allow HTTP 0.9 responses
 -0, --http1.0            Use HTTP 1.0
     --http1.1            Use HTTP 1.1
     --http2              Use HTTP 2
     --http2-prior-knowledge Use HTTP 2 without HTTP/1.1 Upgrade
     --http3              Use HTTP v3
     --ignore-content-length Ignore the size of the remote resource
 -i, --include            Include protocol response headers in the output
 -k, --insecure           Allow insecure server connections
     --interface <name>   Use network INTERFACE (or address)
 -4, --ipv4               Resolve names to IPv4 addresses
 -6, --ipv6               Resolve names to IPv6 addresses
 -j, --junk-session-cookies Ignore session cookies read from file
     --keepalive-time <seconds> Interval time for keepalive probes
     --key <key>          Private key file name
     --key-type <type>    Private key file type (DER/PEM/ENG)
     --krb <level>        Enable Kerberos with security <level>
     --libcurl <file>     Dump libcurl equivalent code of this command line
     --limit-rate <speed> Limit transfer speed to RATE
 -l, --list-only          List only mode
     --local-port <num/range> Force use of RANGE for local port numbers
 -L, --location           Follow redirects
     --location-trusted   Like --location, and send auth to other hosts
     --login-options <options> Server login options
     --mail-auth <address> Originator address of the original email
     --mail-from <address> Mail from this address
     --mail-rcpt <address> Mail to this address
     --mail-rcpt-allowfails Allow RCPT TO command to fail for some recipients
 -M, --manual             Display the full manual
     --max-filesize <bytes> Maximum file size to download
     --max-redirs <num>   Maximum number of redirects allowed
 -m, --max-time <fractional seconds> Maximum time allowed for transfer
     --metalink           Process given URLs as metalink XML file
     --negotiate          Use HTTP Negotiate (SPNEGO) authentication
 -n, --netrc              Must read .netrc for user name and password
     --netrc-file <filename> Specify FILE for netrc
     --netrc-optional     Use either .netrc or URL
 -:, --next               Make next URL use its separate set of options
     --no-alpn            Disable the ALPN TLS extension
 -N, --no-buffer          Disable buffering of the output stream
     --no-keepalive       Disable TCP keepalive on the connection
     --no-npn             Disable the NPN TLS extension
     --no-progress-meter  Do not show the progress meter
     --no-sessionid       Disable SSL session-ID reusing
     --noproxy <no-proxy-list> List of hosts which do not use proxy
     --ntlm               Use HTTP NTLM authentication
     --ntlm-wb            Use HTTP NTLM authentication with winbind
     --oauth2-bearer <token> OAuth 2 Bearer Token
 -o, --output <file>      Write to file instead of stdout
     --output-dir <dir>   Directory to save files in
 -Z, --parallel           Perform transfers in parallel
     --parallel-immediate Do not wait for multiplexing (with --parallel)
     --parallel-max <num> Maximum concurrency for parallel transfers
     --pass <phrase>      Pass phrase for the private key
     --path-as-is         Do not squash .. sequences in URL path
     --pinnedpubkey <hashes> FILE/HASHES Public key to verify peer against
     --post301            Do not switch to GET after following a 301
     --post302            Do not switch to GET after following a 302
     --post303            Do not switch to GET after following a 303
     --preproxy [protocol://]host[:port] Use this proxy first
 -#, --progress-bar       Display transfer progress as a bar
     --proto <protocols>  Enable/disable PROTOCOLS
     --proto-default <protocol> Use PROTOCOL for any URL missing a scheme
     --proto-redir <protocols> Enable/disable PROTOCOLS on redirect
 -x, --proxy [protocol://]host[:port] Use this proxy
     --proxy-anyauth      Pick any proxy authentication method
     --proxy-basic        Use Basic authentication on the proxy
     --proxy-cacert <file> CA certificate to verify peer against for proxy
     --proxy-capath <dir> CA directory to verify peer against for proxy
     --proxy-cert <cert[:passwd]> Set client certificate for proxy
     --proxy-cert-type <type> Client certificate type for HTTPS proxy
     --proxy-ciphers <list> SSL ciphers to use for proxy
     --proxy-crlfile <file> Set a CRL list for proxy
     --proxy-digest       Use Digest authentication on the proxy
     --proxy-header <header/@file> Pass custom header(s) to proxy
     --proxy-insecure     Do HTTPS proxy connections without verifying the proxy
     --proxy-key <key>    Private key for HTTPS proxy
     --proxy-key-type <type> Private key file type for proxy
     --proxy-negotiate    Use HTTP Negotiate (SPNEGO) authentication on the proxy
     --proxy-ntlm         Use NTLM authentication on the proxy
     --proxy-pass <phrase> Pass phrase for the private key for HTTPS proxy
     --proxy-pinnedpubkey <hashes> FILE/HASHES public key to verify proxy with
     --proxy-service-name <name> SPNEGO proxy service name
     --proxy-ssl-allow-beast Allow security flaw for interop for HTTPS proxy
     --proxy-ssl-auto-client-cert Use auto client certificate for proxy (Schannel)
     --proxy-tls13-ciphers <ciphersuite list> TLS 1.3 proxy cipher suites
     --proxy-tlsauthtype <type> TLS authentication type for HTTPS proxy
     --proxy-tlspassword <string> TLS password for HTTPS proxy
     --proxy-tlsuser <name> TLS username for HTTPS proxy
     --proxy-tlsv1        Use TLSv1 for HTTPS proxy
 -U, --proxy-user <user:password> Proxy user and password
     --proxy1.0 <host[:port]> Use HTTP/1.0 proxy on given port
 -p, --proxytunnel        Operate through an HTTP proxy tunnel (using CONNECT)
     --pubkey <key>       SSH Public key file name
 -Q, --quote <command>    Send command(s) to server before transfer
     --random-file <file> File for reading random data from
 -r, --range <range>      Retrieve only the bytes within RANGE
     --raw                Do HTTP "raw"; no transfer decoding
 -e, --referer <URL>      Referrer URL
 -J, --remote-header-name Use the header-provided filename
 -O, --remote-name        Write output to a file named as the remote file
     --remote-name-all    Use the remote file name for all URLs
 -R, --remote-time        Set the remote file's time on the local output
 -X, --request <method>   Specify request method to use
     --request-target <path> Specify the target for this request
     --resolve <[+]host:port:addr[,addr]...> Resolve the host+port to this address
     --retry <num>        Retry request if transient problems occur
     --retry-all-errors   Retry all errors (use with --retry)
     --retry-connrefused  Retry on connection refused (use with --retry)
     --retry-delay <seconds> Wait time between retries
     --retry-max-time <seconds> Retry only within this period
     --sasl-authzid <identity> Identity for SASL PLAIN authentication
     --sasl-ir            Enable initial response in SASL authentication
     --service-name <name> SPNEGO service name
 -S, --show-error         Show error even when -s is used
 -s, --silent             Silent mode
     --socks4 <host[:port]> SOCKS4 proxy on given host + port
     --socks4a <host[:port]> SOCKS4a proxy on given host + port
     --socks5 <host[:port]> SOCKS5 proxy on given host + port
     --socks5-basic       Enable username/password auth for SOCKS5 proxies
     --socks5-gssapi      Enable GSS-API auth for SOCKS5 proxies
     --socks5-gssapi-nec  Compatibility with NEC SOCKS5 server
     --socks5-gssapi-service <name> SOCKS5 proxy service name for GSS-API
     --socks5-hostname <host[:port]> SOCKS5 proxy, pass host name to proxy
 -Y, --speed-limit <speed> Stop transfers slower than this
 -y, --speed-time <seconds> Trigger 'speed-limit' abort after this time
     --ssl                Try SSL/TLS
     --ssl-allow-beast    Allow security flaw to improve interop
     --ssl-auto-client-cert Use auto client certificate (Schannel)
     --ssl-no-revoke      Disable cert revocation checks (Schannel)
     --ssl-reqd           Require SSL/TLS
     --ssl-revoke-best-effort Ignore missing/offline cert CRL dist points
 -2, --sslv2              Use SSLv2
 -3, --sslv3              Use SSLv3
     --stderr <file>      Where to redirect stderr
     --styled-output      Enable styled output for HTTP headers
     --suppress-connect-headers Suppress proxy CONNECT response headers
     --tcp-fastopen       Use TCP Fast Open
     --tcp-nodelay        Use the TCP_NODELAY option
 -t, --telnet-option <opt=val> Set telnet option
     --tftp-blksize <value> Set TFTP BLKSIZE option
     --tftp-no-options    Do not send any TFTP options
 -z, --time-cond <time>   Transfer based on a time condition
     --tls-max <VERSION>  Set maximum allowed TLS version
     --tls13-ciphers <ciphersuite list> TLS 1.3 cipher suites to use
     --tlsauthtype <type> TLS authentication type
     --tlspassword <string> TLS password
     --tlsuser <name>     TLS user name
 -1, --tlsv1              Use TLSv1.0 or greater
     --tlsv1.0            Use TLSv1.0 or greater
     --tlsv1.1            Use TLSv1.1 or greater
     --tlsv1.2            Use TLSv1.2 or greater
     --tlsv1.3            Use TLSv1.3 or greater
     --tr-encoding        Request compressed transfer encoding
     --trace <file>       Write a debug trace to FILE
     --trace-ascii <file> Like --trace, but without hex output
     --trace-time         Add time stamps to trace/verbose output
     --unix-socket <path> Connect through this Unix domain socket
 -T, --upload-file <file> Transfer local FILE to destination
     --url <url>          URL to work with
 -B, --use-ascii          Use ASCII/text transfer
 -u, --user <user:password> Server user and password
 -A, --user-agent <name>  Send User-Agent <name> to server
 -v, --verbose            Make the operation more talkative
 -V, --version            Show version number and quit
 -w, --write-out <format> Use output FORMAT after completion
     --xattr              Store metadata in extended file attributes
```

## Spec 4

The exact one-argument command `version` is handled internally and prints exactly:

```text
curlie v0.0.0-LOCAL (0000-00-00T00:00:00Z)
```

followed by one newline, to stdout, and exits 0. It is case-sensitive and special only when it is the sole argument. `VERSION`, `Version`, or `version extra` are normal request operands and must not print the internal version string.

`--version` is not the internal command. It is curl's version option: invoke the provided curl and expose its normal stdout (starting with `curl ` and containing its libcurl version, `Protocols:`, and `Features:`), exiting successfully.

## Spec 5

Recognize the method words `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, `TRACE`, and `HEAD` case-insensitively when used in the method position. Normalize all except HEAD to uppercase and translate them to the two curl arguments `-X METHOD` before the URL. Translate HEAD to `-I`, never to `-X HEAD`. If no explicit method is present, do not add `-X GET`; let curl infer its method. Explicit curl `-X/--request` options remain intact.

A method token by itself is not rejected by curlie's parser: translate it and attempt to invoke curl with no URL operand, leaving the resulting behavior to curl. This permits a harness substitute for curl to observe `-X POST`; real curl will ordinarily report its own missing-URL error.

The invocation basename has no method semantics. Invoking the executable through symlinks named `post`, `put`, `delete`, or `head` with the sole operand `example.com` produces the same curl argv as any other basename: with terminal stdin it is exactly `example.com -s -S -H "Accept: application/json, */*"`. In particular, none of those basenames adds `-X` or `-I`. Explicit method words and user-provided `-X/--request` options still behave as described above.

## Spec 6

Normalize the request URL used as curl's operand as follows:

- Strip a leading `//`, so `//example.com:8080` becomes `example.com:8080`.
- A URL beginning with `:PORT` becomes `localhost:PORT`, preserving a following path. Thus `:5000/api` becomes `localhost:5000/api`.
- Inside an explicit HTTP scheme, a missing hostname before a port is filled with localhost: `http://:8080` becomes `http://localhost:8080`, and `http://:` becomes `http://localhost`.
- Otherwise preserve the operand exactly, except that URL serialization encodes raw non-ASCII path characters as UTF-8 percent escapes in an explicit HTTP or HTTPS URL while retaining existing percent escapes and the raw query. In particular, the displayed form of `https://example.com/café/東?x=%2F` remains that exact Unicode string, but curl receives `https://example.com/caf%C3%A9/%E6%9D%B1?x=%2F`. Bare hostnames, hostname and port, paths and their ASCII punctuation, existing query strings, fragments, embedded credentials, bracketed IPv6, IPv4, existing percent escapes, and non-HTTP schemes such as `ftp://` are otherwise preserved.

Before dry-run output or actual execution, write a display URL plus newline to stderr. Strip a leading `//` for both the curl operand and display basis; otherwise the display basis retains the user's pre-localhost-insertion URL. The display form begins with `http://` unless that basis begins with `http://` or `https://`; this affects display only. Consequently `//example.com:8080` and bare `example.com` are displayed as `http://example.com:8080` and `http://example.com`, and even the curl operand `ftp://ftp.example.com/file.txt` is displayed as `http://ftp://ftp.example.com/file.txt`. The localhost insertion described above applies only to curl's operand, not to this display string: `:5000/api`, `http://:8080`, and `http://:` are displayed exactly as `http://:5000/api`, `http://:8080`, and `http://:`, each followed by newline, while curl receives `localhost:5000/api`, `http://localhost:8080`, and `http://localhost`. There is no URL line when no URL was identified, including help-only and version invocations.

## Spec 7

After the URL positional has been selected, later HTTPie-style request items are classified by their first applicable separator. Request-item-looking strings before the intended URL are not skipped. For the four positional arguments `X-Before:yes`, `q==a b`, `name=value`, and `example.com`, the first is the URL basis, the second and third are the later query and JSON items, and the fourth is an additional unclassified curl operand. Curl is invoked with `example.com`, `-d`, `{"name":"value"}`, `http://X-Before:yes?q=a+b`, then the defaults and automatic headers; `X-Before:yes` is not translated to `-H`.

Those later request items are classified as follows:

- `Header:value` becomes curl arguments `-H` and the entire original string. Split only at the first colon conceptually; all later colons, equals signs, spaces, empty values, URLs, and punctuation in the value remain intact. Repeated headers, including repeated names, remain separate and in input order.
- `key==value` is a query item. Split at the first `==`, form-URL-encode the key and value in UTF-8 (space becomes `+`; reserved bytes such as `&`, `=`, and Unicode bytes become uppercase `%HH`), and append `key=value` to the URL. Use `?` for the first addition to a URL without a query and `&` thereafter. Existing queries and empty values are preserved. For example, `expr==a=b` produces `?expr=a%3Db`, and `query==café` produces `query=caf%C3%A9`.
- `key=value` is a JSON string field. Split only on the first equals sign. Empty remains `""`; later equals signs, spaces, newlines, quotes, backslashes, `@`, and Unicode are JSON-escaped as necessary.
- `key:=JSON` is a typed JSON field. Parse its right side as JSON, preserving numbers (including negative, zero, and floating point), booleans, null, arrays, objects, mixed arrays, and deeply nested or large values.

All `=` and `:=` fields are combined into one compact JSON object supplied by one `-d` argument. Serialize object keys in lexicographic order and put no insignificant whitespace in the JSON. Keys are literal strings: dots, hyphens, underscores, spaces, quotes, and numeric-looking keys do not imply nesting and must be correctly escaped. Thus input `name=value age:=25` produces `{"age":25,"name":"value"}`.

## Spec 8

`-F` and `--form` select HTTPie form mode and are not forwarded as a bare mode flag. In that mode each `key=value` request item becomes a separate pair `-F`, `key=value`, in original order; do not combine it into JSON and do not inject a JSON Content-Type. Preserve values containing spaces and `@file` references. Multiple form fields remain multiple `-F` pairs. Form fields do not count as explicit data for the stdin default: when stdin is non-terminal, the normal implicit `-d@-` is still appended. Thus `--curl -F example.com a=b file=@x` prints `curl -F a=b -F file=@x example.com -s -S -d@- -H "Accept: application/json, */*"` plus newline. Curl's `--form-string VALUE` remains an ordinary value-taking pass-through option.

An unclassified request item is passed as an additional curl operand before the URL and quoted in dry-run output when needed. For example, the literal `path with spaces` appears as `"path with spaces"` before the URL.

## Spec 9

Pass supported curl options to curl without changing their spelling or value, except for `--curl`, `--pretty`, short `-i`, and HTTPie form-mode handling described elsewhere. Help options and long `--include` are passed through. Preserve order, duplicates, conflicts, and values as individual argv elements. Options can precede or follow the URL.

The complete help table defines the supported options and whether each takes a value. Tested value-taking forms include `-A`, `-b`, `-c`, `-C`, `-d`, `-D`, `-e`, `-E`, `-H`, `-K`, `-m`, `-o`, `-r`, `-T`, `-u`, `-U`, `-w`, `-x`, `-X`, `-Y`, `-y`, `-z`, plus `--cacert`, `--cert`, `--config`, `--connect-timeout`, `--connect-to`, `--cookie`, `--data-binary`, `--data-raw`, `--data-urlencode`, `--form-string`, `--interface`, `--keepalive-time`, `--limit-rate`, `--max-filesize`, `--max-redirs`, `--max-time`, `--netrc-file`, `--noproxy`, `--parallel-max`, `--proto`, `--proxy`, `--pubkey`, `--resolve`, `--retry`, `--socks5`, `--speed-limit`, `--speed-time`, `--unix-socket`, `--user`, and `--user-agent`. Tested valueless forms include `-0`, `-4`, `-6`, `-I`, `-k`, `-L`, `-O`, `-s`, `-S`, `-v`, and `--anyauth`, `--basic`, `--compressed`, `--digest`, `--http1.1`, `--http2`, `--http3`, `--insecure`, `--location`, `--negotiate`, `--ntlm`, `--silent`, `--tcp-nodelay`, `--tlsv1.2`, and `--verbose`.

Long options using `=` are retained as one argument rather than validated by curlie. This includes both `--user=admin:pass` and `--output=a.txt`; any acceptance, diagnostic, or exit status then comes from curl.

## Spec 10

Expand compound short flags character by character. Valueless combinations such as `-vLI`, `-Lkv`, and `-vLIs` become separate `-v`, `-L`, `-I`, etc. If a character is a value-taking option, the rest of that same token is its inline value, or otherwise the next argv token is consumed as its value, and compound parsing stops. Examples: `-vH X:1` becomes `-v -H X:1`; `-vHX:1` does the same; `-vu user:pass`, `-vb cookies.txt`, `-vo /tmp/out`, `-vd data`, and `-vX PUT` behave analogously. Unknown short members are expanded and forwarded too: `-v? example.com` begins curl's argv with `-v`, `-?`, `example.com`.

Curlie does not reject an option-bearing invocation merely because it identified no URL, and it does not validate unknown or numeric options. It invokes curl and returns curl's result. In particular:

- `-v` is forwarded before the normal appended defaults.
- Bare `--max-time` is forwarded before the defaults. With the reference environment's real curl, it exits 2 and stderr is exactly `curl: option --max-time: expected a proper numerical parameter` newline, then `curl: try 'curl --help' or 'curl --manual' for more information` newline.
- `-o -s` consumes `-s` as the output value, then appends another `-s -S`; curlie emits no `looks like a flag` warning and performs no missing-URL check.
- An unknown long option such as `--definitely-not-real` and the single argument `--output=a.txt` are forwarded unchanged. Their diagnostics and status are curl's.
- After `--`, a token such as `-s` is treated positionally; attempting it displays `http://-s` and passes `-s` as a curl operand.

## Spec 11

Before executing curl, append default arguments `-s -S` so its progress meter is suppressed while its errors remain visible. Retain user-provided silent/verbose flags too, even if they duplicate or conflict with defaults.

Inject `-H "Accept: application/json, */*"` unless the user supplied an Accept header, either through `-H/--header` or HTTPie header syntax. Detection is case-insensitive, preserves the user's exact header spelling/value, and never creates a duplicate default.

When the request has input data, also inject `-H "Content-Type: application/json"`, unless form mode is active or the user supplied a Content-Type header. Header-name detection is case-insensitive and preserves the user header. Input data means any explicit `-d`, generated JSON, or implicit stdin input. Explicit nonempty `-d` values are all preserved in order and suppress implicit `-d@-`; values beginning with `@`, containing `=`, or containing quotes/backslashes remain unchanged. `-d @filename` is passed to curl rather than read by this executable. An explicit empty `-d ''` still causes the JSON Content-Type header but does not suppress non-terminal stdin: its curl argv contains the `-d`, empty-string pair and later `-d@-`.

If there is no nonempty explicit data and no generated JSON, and stdin is not a terminal, append the single argument `-d@-`, allowing curl to read stdin directly, even when stdin is empty, with an empty explicit `-d`, in form mode, and with an explicitly written GET method. If stdin is a terminal, do not add it. Form mode does not require a JSON Content-Type; explicit form operands are left to curl. Always add the default Accept header unless overridden.

## Spec 12

`--curl` is a dry-run switch owned by this executable. Remove it from the translated argv, do not start curl or make any network request, print the display URL to stderr, and print exactly one shell-like command line plus newline to stdout. It begins `curl ` and renders the same argv that normal execution would use. Arguments containing spaces are surrounded with double quotes; embedded double quotes and backslashes in such an argument are backslash-escaped so parsing the displayed command reconstructs the original argv element. Ordinary arguments and compact JSON without spaces are unquoted.

The general order is: translated/passed-through user operands (including explicit method, generated headers/data, and unknown positional operands), normalized URL, appended defaults `-s -S`, implicit `-d@-` if any, then automatic Content-Type and Accept headers. The invocation basename adds nothing. Generated JSON is placed before the URL. Automatic headers use `-H` followed by a quoted header argument in the rendered line.

For a non-terminal stdin, these outputs are normative (each has a trailing newline):

```text
$ executable --curl http://example.com
curl http://example.com -s -S -d@- -H "Content-Type: application/json" -H "Accept: application/json, */*"

$ executable --curl GET http://example.com
curl -X GET http://example.com -s -S -d@- -H "Content-Type: application/json" -H "Accept: application/json, */*"

$ executable --curl POST http://example.com name=value age:=25
curl -X POST -d {"age":25,"name":"value"} http://example.com -s -S -H "Content-Type: application/json" -H "Accept: application/json, */*"

$ executable --curl http://example.com Authorization:Bearer-token
curl -H Authorization:Bearer-token http://example.com -s -S -d@- -H "Content-Type: application/json" -H "Accept: application/json, */*"
```

Headers or operands containing spaces are double-quoted, e.g. `-H "Authorization:Bearer token123"` and `"path with spaces"`. User `Accept:custom` suppresses the automatic Accept; user `Content-Type:custom` suppresses the automatic Content-Type. `--pretty` never appears in the rendered command and ordinarily causes `-v` to appear, but an explicitly supplied silent flag suppresses that generated verbosity.

## Spec 13

Without `--curl`, start the harness-provided `curl` with the translated argv and connect its stdin to executable's stdin. Stream curl's response body to executable stdout. Write the display URL first on stderr, then cleaned curl diagnostics/headers. Options such as `-L`, `--compressed`, timeouts, IPv4/IPv6, authentication, referer, ranges, HTTP-version selection, proxies, certificates, cookies, `-G`, uploads, and custom headers must therefore have their normal curl effects.

`-o/--output` causes curl to write the body to the named file, leaving executable stdout empty. `-D/--dump-header` causes curl to create a response-header file. Preserve data so local servers receive compact generated JSON and `Content-Type: application/json`; for example `POST URL hello=world` sends exactly `{"hello":"world"}`. Query items affect the actual request path, Unicode JSON is sent as UTF-8, redirects can be followed, and explicit GET/POST/PUT/PATCH/HEAD methods reach the server as selected.

Short `-i` is consumed as a curlie presentation option rather than retained in a `--curl` command. Long `--include` is not special and is forwarded in its original position. Both must still allow curl to determine the request result.

## Spec 14

Normally, when stdout is not a terminal and `--pretty` is absent, response body bytes pass through exactly and without ANSI escapes. This includes compact JSON, text, arbitrary high bytes, and NUL-containing binary data. `--raw` is passed through to curl and also results in unchanged captured body bytes; for example a server body `{"hello": "world", "n": 1}` must remain byte-for-byte identical.

When stdout is a terminal, pretty body presentation is automatic: JSON body formatting and the binary filter apply, and curl receives `-v` unless the user supplied a silent flag. `--pretty` forces both body and stderr presentation even when the streams are captured, including colored response headers, but it likewise does not add `-v` when an explicit silent flag is present. The automatic stdout-terminal condition alone does not color a separately captured stderr stream. Explicit `--pretty` is removed before curl invocation. An explicitly supplied `-s/--silent` remains present; no progress meter should appear. Specifically, with terminal stdin, `--pretty -s example.com` invokes curl as `-s example.com -s -S -H "Accept: application/json, */*"`, with no `-v`.

## Spec 15

Pretty JSON formatting is streaming and byte-state-oriented. It activates only if the first response-body byte is `{` or `[`. Otherwise ordinary text is passed through unchanged. Remove insignificant spaces, tabs, CR, and LF while the formatter considers itself outside a quoted string, while preserving bytes while it considers itself inside one. After `{` or `[`, output a newline and increase indentation; before `}` or `]`, output a newline, decrease indentation, and indent; after `,`, output newline plus current indentation; after `:`, output one space. Indentation is exactly four ASCII spaces per nesting level. Empty arrays therefore render as `[` newline four spaces newline `]`. On a normally completed formatting path, finish with newline and the reset sequence.

The quote state deliberately does not implement JSON backslash escaping: every raw `"` byte toggles the state, even when preceded by a backslash. Consequently an escaped quote can desynchronize formatting. For the input used here, `{"z":"a \\n \\t \\" \\\\","a":[true,false,null,-0.50,1e+09,{"u":"café"}]}`, the `"z"` field is formatted normally, but after the escaped quote the remaining `,"a":[...]` fragment stays compact, color sequences interrupt later quoted-name byte sequences, and no final reset is appended. The original quote, escape, and UTF-8 value bytes remain present.

Apply these ANSI SGR sequences in pretty mode:

- default/delimiters: `ESC[37m`
- object field names, and string elements in arrays under the formatter's field state: `ESC[34m`
- string and numeric object-field values: `ESC[36m`
- object-field values `true`, `false`, and `null`: `ESC[35m`
- final reset: `ESC[0m`

Primitive values directly inside arrays do not select a value color; they retain the current delimiter color. Thus `[0]` renders its indented `0` without a preceding `ESC[36m`. Twelve nested arrays still use 48 spaces before their innermost `0`, but that `0` likewise has no cyan sequence.

For example, where `\e` denotes byte 0x1b, compact input `{"name":"test","value":42}` becomes exactly:

```text
\e[37m{
    \e[34m"name"\e[37m: \e[36m"test"\e[37m,
    \e[34m"value"\e[37m: \e[36m42
\e[37m}
\e[0m
```

Nested objects/arrays, eleven or more levels, Unicode, and literal values follow the byte-state rules above. Do not reserialize the response through a generic JSON encoder: preserve input field order and number spelling except for the formatter's whitespace and quote-state transformations.

## Spec 16

Clean verbose curl stderr line by line. Remove curl's leading `< ` marker from response protocol lines and headers, and suppress internal upload/download chunk marker lines such as `{ [429 bytes data]` and `} [16 bytes data]`. Unless the user explicitly supplied `-v/--verbose`, suppress connection-information lines beginning `* ` and all request-side lines beginning `> ` as well; this includes verbosity added internally by `--pretty`, and the first diagnostic after the display URL is therefore the response status line. Preserve response HTTP versions, status codes/text, blank separators, every repeated response header, and the conventional `Name: value` separation. Preserve the carriage return at the end of HTTP/header content when curl supplied one; any ANSI reset follows that carriage return and precedes the newline. Redirect chains retain each response. Headers remain on stderr, never mixed into the response body on stdout.

An explicit user `-v/--verbose` is different: connection and request lines are retained, with their `* ` content and with `> ` removed from request lines. If only stdout is attached to a terminal while stderr is captured, these diagnostics remain entirely uncolored. For example, the captured sequence is the display URL, `* Connected`, `GET / HTTP/1.1`, `HTTP/1.1 200 OK`, `X: y`, and a blank line, each with its curl-supplied line ending.

With `--pretty` presentation colors enabled, response lines use blue `ESC[34m` for the `HTTP` portion, white `ESC[37m` for separators and header names, cyan `ESC[36m` for protocol version/status code and header values, yellow `ESC[33m` for status reason text, red `ESC[31m` for `curl:` errors, and reset `ESC[0m` at the line end. Because internally generated connection and request lines are suppressed, gray `ESC[90m` and colored request methods do not occur for them. A run with explicit `-v` but without `--pretty` contains no ANSI escapes merely because stdout is a terminal.

## Spec 17

In pretty mode only, treat a NUL byte anywhere in a body write/chunk as binary. Suppress that entire chunk—including bytes before the NUL—and all subsequent body writes. Emit exactly one copy of this ASCII banner to stdout:

```text
+-----------------------------------------+
| NOTE: binary data not shown in terminal |
+-----------------------------------------+
```

Each banner line, including the last, ends in newline. Multiple NULs or a multi-megabyte binary stream still produce exactly one banner and no leaked prefix/suffix. High bytes `0x80`–`0xff` without a NUL are not binary and pass through unchanged. Large ordinary text passes. Outside pretty mode, no binary filtering occurs and NUL bytes pass through unchanged.

## Spec 18

When curl starts and exits nonzero, forward its stderr after the already printed display-URL line, leave stdout as curl produced it, and exit with exactly curl's status (including 1, 3, 6, 7, 22, 23, 28, 35, 47, and 60). Do not replace it with a generic status. In a captured/non-pretty run, diagnostics remain uncolored. For example, a curl process that writes `curl: (6) Could not resolve host: badhost\n` and exits 6 yields exactly:

```text
http://example.com
curl: (6) Could not resolve host: badhost
```

on stderr and exits 6.

If the `curl` file is found but cannot be executed (for example, exec-format error), print the display URL and the operating-system execution error to stderr, keep stdout empty, but retain compatibility behavior of exiting 0. After the display URL's newline, stderr ends with exactly `fork/exec CURL_PATH: exec format error`, where `CURL_PATH` is the resolved curl path; the error text has no following newline.

## Spec 19

Do not suppress curl configuration behavior. By default curl may read `$HOME/.curlrc`, so settings such as `-A fromcurlrc` affect an actual request. Forward `-K FILE`/`--config FILE` in its original location; an explicit config setting takes effect after defaults from `.curlrc`, and a later CLI setting such as `-A fromcli` wins over the config file. A missing explicit config emits curl's warning containing `error trying read config` but the otherwise successful request exits 0. An unknown option inside an explicit config emits a warning containing `is unknown` but does not prevent the otherwise successful request.

## Spec 20

The executable must operate correctly under concurrent independent invocations and must not rely on the current directory except for paths explicitly supplied by the user. It must be executable directly and through symlinks, without interpreting the symlink basename as a method. Internal version and `--curl` dry-run paths do not start curl. Help and malformed/unknown options do start curl and expose curl's result; curl's own help/error processing ordinarily makes no network request. For real requests, the executable must stream rather than require a complete response in memory, preserve separation of stdout and stderr, and terminate promptly with the underlying curl result.
