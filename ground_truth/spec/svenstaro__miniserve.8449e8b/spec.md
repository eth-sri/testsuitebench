# Clarified specification for `executable`

The required artifact is one executable file named `executable`. It is a command-line HTTP file server compatible with the behavior below. “Serve root” means the resolved path selected by the positional `PATH` argument or `MINISERVE_PATH`. Options may occur before or after the positional path. Unless a CLI-output rule explicitly says otherwise, diagnostics go to standard error and successful informational output goes to standard output.

## Spec 1

Invocation and lifetime:

- The syntax is `executable [OPTIONS] [PATH]`. A directory path serves a browsable tree rooted there. A regular-file path serves that file directly at `/` with its exact bytes and inferred media type.
- The path is resolved before listening. A nonexistent/unresolvable path exits 1, emits nothing on stdout, and emits stderr containing both `Error` and `Failed to resolve path to be served`; when the literal path is `--help` after an option terminator, the stderr text contains `Failed to resolve path`.
- With neither positional `PATH` nor a nonempty `MINISERVE_PATH`, a noninteractive invocation must refuse to start and exit 1. A no-argument invocation writes exactly `miniserve v0.32.0\n` to stdout before writing stderr containing both `no explicit serve path was set` and `no interactive terminal was attached`. The diagnostic used for a bare `--` must contain `Refusing to start as no explicit serve path was set` and `Please set an explicit serve path`.
- A running server stays alive until terminated and handles concurrent requests. It writes a startup announcement containing `miniserve` and at least one complete `http://HOST:PORT` (or, for valid TLS, `https://HOST:PORT`) URL to stdout promptly and flushes it. This URL must contain the actual selected port so a harness can parse it.
- `-p, --port PORT` selects a TCP port; default is 8080 and 0 requests an OS-assigned ephemeral port. Ports must be decimal integers in 0..65535. `-i, --interfaces ADDRESS` selects a bind interface and may be supplied in either short or long form. With no interface option, the server must be reachable through localhost. Binding `127.0.0.1` must work; a nonlocal address such as `12.34.56.78` must fail nonzero with stderr mentioning a bind failure. CLI port values override environment values.
- `-v, --verbose` enables access logging without changing responses. `MINISERVE_VERBOSE=true` enables the same mode. Boolean flags do not accept explicit values, so `--verbose=false` is an argument error even when the environment enables verbosity.

## Spec 2

Version, generated shell data, and man page:

- `-V` and `--version` exit 0, write only stdout, and output exactly one newline-terminated line matching `miniserve X.Y.Z...`, where `X`, `Y`, and `Z` are decimal version components.
- `--print-completions SHELL` accepts exactly `bash`, `elvish`, `fish`, `powershell`, and `zsh`, exits 0, writes no stderr, and produces a shell-appropriate completion script longer than 100 bytes which names `miniserve`. It should include the conventional marker for the requested shell: `complete`/`COMPREPLY` for bash, `#compdef` for zsh, `complete` for fish, `Register-ArgumentCompleter` for PowerShell, and `edit:completion:arg-completer` for Elvish.
- `--print-manpage` exits 0, writes no stderr, and writes a man page longer than 500 bytes containing `.TH miniserve`, `.SH NAME`, and `.SH SYNOPSIS`.
- An invalid completion shell is an argument error as detailed in Spec 4.

## Spec 3

Help output is an exact interface contract. When help is reached without an earlier parse error, `--help` and `-h` exit 0, emit no stderr and no ANSI escape sequences, and emit the byte-for-byte UTF-8 texts in Spec 20 and Spec 21 respectively, including their final newline. Parsing is order-sensitive: `executable --help --definitely-invalid` prints long help and exits 0, whereas `executable --definitely-invalid --help` exits 2, emits no stdout, and reports `error: unexpected argument '--definitely-invalid' found` on stderr. After `--`, tokens are positional: `executable -- --help` therefore tries to serve a path named `--help` and does not print help.

## Spec 4

Argument parsing and validation:

- Unknown options exit exactly 2, write no stdout, and write a clap-style stderr diagnostic containing `error: unexpected argument 'OPTION' found`, a `Usage:` line, and `For more information, try '--help'.` where applicable.
- Missing values for `--port`/`-p`, `--index`, and `--header` exit 2 and say `a value is required for '--port <PORT>'`, `a value is required for '--index <INDEX>'`, or `a value is required for '--header <HEADER>'` respectively, followed by `For more information, try '--help'.`
- Invalid numeric values exit 2. For example, `--port abc`, `-pabc`, and `--port=abc` say `invalid value 'abc' for '--port <PORT>'`; `--chmod invalid` says `invalid value 'invalid' for '--chmod <CHMOD>'`. Port 99999 is invalid.
- Choice options validate before trying to run and show these possible values in an error: sorting method `name, size, date`; sorting order `asc, desc`; color schemes `squirrel, archlinux, zenburn, monokai`; size display `human, exact`; completions `bash, elvish, fish, powershell, zsh`; upload media type `image, audio, video`; duplicate handling `error, overwrite, rename`.
- `--spa` requires `--index <INDEX>`. Omitting it exits 2 and includes `the following required arguments were not provided:`, `--index <INDEX>`, and `Usage: executable --index <INDEX> --spa [PATH]`.
- `-u, --upload-files` and `-R, --rm-files` take optional path values. A following `--` ends their optional value. An explicit empty value such as `--upload-files=` exits 2 and says `a value is required for '--upload-files [<ALLOWED_UPLOAD_DIR>]' but none was supplied`.
- `-U, --mkdir` requires `--upload-files [<ALLOWED_UPLOAD_DIR>]`. Supplying `-U` without upload mode exits 2, emits no stdout, and reports `the following required arguments were not provided:` followed by `--upload-files [<ALLOWED_UPLOAD_DIR>]`.
- `--header` requires `Name:Value`; no colon is invalid. `--auth` requires one of the credential formats in Spec 12. `--auth-file` must name a readable existing file. TLS validation is in Spec 18. Invalid argument/configuration cases exit nonzero and do not start a server.

## Spec 5

Environment configuration mirrors the CLI. At minimum support the environment variables shown in the exact help text, including `MINISERVE_PATH`, `MINISERVE_PORT`, `MINISERVE_INTERFACE`, `MINISERVE_VERBOSE`, `MINISERVE_HIDDEN`, `MINISERVE_AUTH`, `MINISERVE_TITLE`, and `MINISERVE_COLOR_SCHEME`. CLI values take precedence. Invalid typed environment values, such as `MINISERVE_PORT=notanint`, prevent startup with a nonzero parse/configuration error. Unlike the bare `-u` flag, `MINISERVE_ALLOWED_UPLOAD_DIR` must contain a nonempty path; an empty value is invalid. `MINISERVE_PATH` can supply the serve root with no positional argument.

## Spec 6

Ordinary file responses:

- A GET for an existing regular file under the serve root returns 200 and its exact bytes, including binary bytes, invalid UTF-8, zero-byte files, and files of at least 1 MiB. It sets `Content-Length` to the byte length.
- Infer media types by extension at least as follows: `.txt` is `text/plain`, `.html` is `text/html`, `.json` is `application/json`, `.png` is `image/png`, `.pdf` is `application/pdf`, and unknown/binary `.bin` is `application/octet-stream`. CSS, JavaScript, XML, and other ordinary files must still be returned intact.
- Names and paths are case-sensitive. Correctly URL-decode percent-encoded path segments so spaces and Unicode names can be fetched. Listings safely display Unicode and names containing spaces, `&`, `#`, `%`, `+`, semicolons, equals signs, commas, quotes, and other punctuation, with HTML and URL escaping as needed.
- Deep nested files and directories work. Missing resources return 404 with a response body containing `404` or `not found`. A request URL must not escape the serve root through `..`, percent-encoded traversal components, or another request-path traversal spelling; such attempts return 400, 403, or 404 and never reveal outside files. This request-path rule does not prohibit reaching an outside target by following a symlink that is itself under the serve root; default symlink behavior is specified in Spec 11. Mutation-path behavior is specified separately in Specs 14 and 15.

## Spec 7

HTTP transfer semantics:

- HEAD on a file returns 200, the same representation headers as GET (especially identical `Content-Length`), and no response body.
- A single byte range `Range: bytes=START-END` for an existing file returns 206, exactly the inclusive requested bytes, and a valid `Content-Range` header. Examples: bytes 0-9 of `0123456789...` return ten bytes, and bytes 100-119 return twenty bytes.
- With `-C, --compress-response`, the server accepts clients advertising gzip and may gzip suitable bodies using a correct `Content-Encoding`; clients that transparently decode must obtain the original exact content. Enabling it must not break archive/listing responses.
- `--header Name:Value` is repeatable and adds each header to file and listing responses without overwriting a header already generated or an earlier custom value. Preserve the supplied value exactly (for example `X-Test-Header:abc` and `Cache-Control:no-cache`).

## Spec 8

Directory listings:

- GET of an existing directory returns 200 and valid UTF-8 HTML containing `<html` and `</html>`, links (`href`) for its visible direct files and subdirectories, and navigation that permits browsing nested directories. An empty directory still returns valid HTML.
- The visible filename text appears in the page, so lists of at least 100 files can be recognized. Directories should be recognizable as directories (a trailing `/` is acceptable).
- Dot-prefixed files/directories are hidden from listings by default. `-H, --hidden` includes them and permits direct access to a hidden file. Non-hidden content remains visible.
- `-D, --dirs-first` groups directories before files. `-S, --default-sorting-method` accepts `name`, `size`, or `date`; the default is `name`. `-O, --default-sorting-order` accepts `asc` or `desc` and advertises `desc` as its default, but its initial-listing behavior is inverted: `asc` renders descending name order (`z-file` before `a-file`), while `desc` renders ascending name order (`a-file` before `z-file`). Consequently, an unflagged listing places `aaa.txt` before `zzz.txt`.
- The table labels its date column `Last modification` and includes date-sort links. It includes enough file size/date metadata for the supported sort modes. `--size-display exact` shows an exact decimal byte count for regular files (for example `1234`); default `human` may use human-readable units.
- `--directory-size` does not render a directory's recursive size directly into the initial HTML. With `--directory-size --size-display exact`, a 321-byte directory initially has an empty `<td class="size-cell"></td>`; the page's script requests the recursive size from `/__miniserve_internal/api`, whose `DirSize` response for that directory is `321 B`.
- `?raw=true` still returns valid HTML and the complete file listing; it may omit nonessential decoration.

## Spec 9

Indexing and special routing:

- `--index NAME` changes every directory lookup: if that directory contains regular file `NAME`, return its exact bytes instead of a generated listing. This applies at the root and in subdirectories. If the configured index is absent, a normal listing may be shown.
- `-I, --disable-indexing` prevents generated directory listings: a directory without a served index returns 403 or 404. Direct file access remains available. Archive query endpoints are unavailable and return 404 in this mode, even when archive flags are set.
- `--spa --index NAME` preserves normal handling of all existing files but replaces what would be a 404 for a nonexistent route with the serve-root index file, status 200, and its exact bytes.
- `--pretty-urls` maps a nonexistent extensionless path such as `/about` to an existing sibling `/about.html`, returning that file with status 200.

## Spec 10

Route prefixes and internal route:

- `--route-prefix PREFIX` places the entire public server beneath that URL prefix. Accept the prefix with or without a leading slash and normalize it. Both `/prefix` and `/prefix/` identify its root. Files are at `/prefix/path`. The unprefixed root returns 404.
- GET `/__miniserve_internal/healthcheck` returns 200 and a body whose surrounding whitespace stripped is `OK` or `ok`.
- `--random-route` generates a six-hex-digit route prefix, keeps the process serving, announces the usable URL, and makes the unprefixed root return 404 (an informational root page is also tolerated where explicitly queried by a client).

## Spec 11

Symlinks:

- By default, symlinks within a directory are shown and followed, including when the symlink target is outside the serve root. A GET of an in-root symlink to an outside regular file returns 200 and the exact target bytes.
- `-P, --no-symlinks` omits symlinks from listings and makes direct requests through a symlink return 403 or 404.
- `-l, --show-symlink-info` keeps symlinks visible and adds recognizable link information, such as the word `link`, `->`, or `→`.
- Directory creation can follow a symlink outside the serve root; the exact mkdir behavior is specified in Spec 14.

## Spec 12

HTTP Basic authentication:

- `-a, --auth RECORD` is repeatable. A protected normal route returns 401 without valid credentials and includes `WWW-Authenticate`; any configured account may authenticate.
- Functionally required records are `username:plaintext-password` and `username:sha256:HEX_DIGEST`. For a SHA-256 record, hash the password supplied over Basic authentication and compare the lowercase hexadecimal digest. Empty plaintext passwords are valid. The help surface also advertises the `username:sha512:HEX_DIGEST` spelling, but no SHA-512 authentication behavior beyond that CLI documentation is required here.
- Wrong username, wrong password, missing credentials, or a password belonging to another account returns 401. Correct credentials return the ordinary resource/listing response.
- `--auth-file FILE` loads one record on every physical line using the same syntax; empty lines are not skipped. Multiple adjacent valid records work, but a blank line makes startup exit 1 with no stdout and stderr `Error: Invalid format for credentials string. Expected username:password, username:sha256:hash or username:sha512:hash\n`. A nonexistent file or malformed inline record also causes nonzero startup failure.

## Spec 13

Page presentation options:

- `-t, --title TEXT` places the provided title in the HTML `<title>` and visible page text. Escape it safely; text with `<`, `>`, `&`, double quotes, and apostrophes must not corrupt the page.
- `-c, --color-scheme` and `-d, --color-scheme-dark` accept only `squirrel`, `archlinux`, `zenburn`, and `monokai`; defaults are squirrel and archlinux. Each accepted selection yields a working, styled HTML listing (embedded `<style>` or linked CSS is sufficient).
- `-q, --qrcode` adds identifiable QR-code content to the listing HTML (`qrcode`, `qr`, or an SVG). With no flag the page must not contain the substring `qrcode`. Piped/non-TTY stdout must not prevent startup when QR is enabled.
- `-F, --hide-version-footer` and `--hide-theme-selector` suppress those respective controls while retaining valid listing HTML. `-W, --show-wget-footer` adds a `wget` recursive-download command containing `-r` or `--recursive`.
- `--readme` causes a `README.md` in the current listed directory to be rendered/included below or alongside the listing, at both root and subdirectory levels. The listing remains present. If there is no README and the flag is absent, do not generate a section containing the word `readme`.
- `--file-external-url URL`, `--temp-directory DIR`, and `--web-upload-files-concurrency N` are accepted with their documented argument shapes and do not prevent normal serving. External URL may prefix file links; the temp directory is used for upload staging, and concurrency is a nonnegative browser-upload setting.

## Spec 14

Uploads and directory creation:

- Uploading is disabled by default: GET or POST `/upload?path=/...` returns an error status (403/404, with 405 also acceptable for a method the endpoint does not support) and creates nothing.
- `-u, --upload-files [ALLOWED_UPLOAD_DIR]` enables multipart/form-data uploads. Accept a file part named `file`, use its supplied filename, write its exact bytes into the requested existing directory under the root, and respond with 200, 201, 302, or 303. If an allowed directory is supplied (for example `/subdir`), restrict uploads to that URL-relative subtree.
- Duplicate mode `-o, --on-duplicate-files` defaults to `error`, which leaves the existing file unchanged. `rename` preserves the original and chooses the first available `stem-N.ext`, beginning with `file-1.txt`. `overwrite` may replace it.
- `-U, --mkdir` enables directory creation and requires upload mode; using it without `--upload-files` is the argument error specified in Spec 4. With both enabled, a listing contains a form whose id is `mkdir`, whose action identifies the upload endpoint, and whose field is named `mkdir`. A multipart request containing that field creates the named child and returns a 2xx or 3xx response; the refreshed listing shows it with a `/`. Without `--mkdir`, a mkdir request returns 4xx and creates nothing.
- `-m, --media-type image|audio|video` and `-M, --raw-media-type EXPRESSION` control the upload form accept/media hint and are accepted individually with upload mode. The corresponding word/expression may appear in HTML. The two options are mutually exclusive, including when supplied as `-m` and `-M`: supplying both exits 2, emits no stdout, and emits stderr beginning exactly `error: the argument '--media-type <MEDIA_TYPE>' cannot be used with '--raw-media-type <MEDIA_TYPE_RAW>'`. `--chmod` accepts an octal permission integer for uploaded files.
- Absolute filesystem upload paths are rejected, but the tested traversal spellings are sanitized rather than rejected. Posting a file to upload directory `/../` returns 303 and writes it at the serve root, not its parent. A multipart filename `../filename-escape.txt` returns 303 and is reduced to the basename `filename-escape.txt` at the serve root. For mkdir, an in-root `escape-link` symlink to an outside directory is followed: requesting child `must-not-exist` under `/escape-link` returns 200 and creates that child in the outside target.

## Spec 15

Deletion:

- `-R, --rm-files [ALLOWED_RM_DIR]` is accepted and the server starts, but it does not expose direct HTTP DELETE at the served file URL. With bare `--rm-files`, `DELETE /victim.txt` returns 404 and leaves the file intact. With `--rm-files /allowed`, both `DELETE /allowed/good.txt` and `DELETE /bad.txt` return 404 and leave both files intact. Directory DELETE may likewise be declined with 404 or 405.
- Without deletion authorization, mutation is rejected. Never delete outside the serve root or through a symlink escape.

## Spec 16

On-demand directory archives:

- Archive generation is disabled by default: listings contain no `Download .tar.gz` or `Download .tar` link, and `?download=tar`, `?download=tar_gz`, and `?download=zip` each return 403.
- `-r, --enable-tar` enables `?download=tar`; `-g, --enable-tar-gz` enables `?download=tar_gz`; `-z, --enable-zip` enables `?download=zip`. Only explicitly enabled formats succeed; other format queries remain 403. Listings expose suitable download links, including literal `Download .tar.gz` for gzip tar.
- A successful archive response is a standards-compliant archive of the selected directory tree. Tar is uncompressed; tar-gz begins with gzip magic bytes `1f 8b`; zip is readable as ZIP. It includes nested files and preserves their exact contents. Member names may include a containing directory prefix but must expose the original filenames.
- When generated directory indexing is disabled, archive download queries return 404 regardless of enable flags.

## Spec 17

Read-only WebDAV:

- WebDAV is off by default; PROPFIND then returns 404, 405, or 501.
- `--enable-webdav` enables PROPFIND on directories and files. Return 207 Multi-Status (200 is tolerated by a basic client) with a nonempty XML response and an XML content type; Depth 0 describes the target and Depth 1 includes children such as listed filenames.
- With WebDAV enabled, OPTIONS on the served root returns 200, has a `DAV` header, and has an `Allow` header containing at least `OPTIONS` and `PROPFIND`.
- WebDAV obeys `--route-prefix`: PROPFIND at the prefixed root succeeds with 2xx, while the unprefixed root fails with 4xx or 5xx.

## Spec 18

TLS startup validation: supplying `--tls-cert CERT` without a key exits nonzero and mentions the missing key or an error. When certificate and key arguments are supplied together, a nonexistent/unreadable certificate or key exits nonzero and stdout must not misleadingly announce a running server. In particular, from a directory containing neither file, `--tls-cert missing-cert.pem --tls-key missing-key.pem PATH` exits 1, emits no stdout, and emits stderr containing `Couldn't access TLS certificate "missing-cert.pem"` and `No such file or directory (os error 2)`. When both files are valid they select HTTPS serving.

## Spec 19

The implementation must be robust across the combined behaviors: flags such as hidden files, directories-first, QR code, authentication, prefix routing, compression, archives, uploads, and UI settings may be combined. A valid combination must still start, preserve exact file bytes, and apply every independently observable option. HTTP errors must be actual status codes rather than successful pages merely containing an error message.


## Spec 20

The exact stdout for `executable --help` is the following. The content between the fence markers begins in column 1; the fence markers themselves are not output. Every blank line, indentation, wrap, and final newline is significant.

```text
For when you really just want to serve some files over HTTP right now!

Usage: executable [OPTIONS] [PATH]

Arguments:
  [PATH]
          Which path to serve
          
          [env: MINISERVE_PATH=]

Options:
  -v, --verbose
          Be verbose, includes emitting access logs
          
          [env: MINISERVE_VERBOSE=]

      --temp-directory <TEMP_UPLOAD_DIRECTORY>
          The path to where file uploads will be written to before being moved to their correct
          location. It's wise to make sure that this directory will be written to disk and not into
          memory.
          
          This value will only be used **IF** file uploading is enabled. If this option is not set,
          the operating system default temporary directory will be used.
          
          [env: MINISERVER_TEMP_UPLOAD_DIRECTORY=]

      --index <INDEX>
          The name of a directory index file to serve, like "index.html"
          
          Normally, when miniserve serves a directory, it creates a listing for that directory.
          However, if a directory contains this file, miniserve will serve that file instead.
          
          [env: MINISERVE_INDEX=]

      --spa
          Activate SPA (Single Page Application) mode
          
          This will cause the file given by --index to be served for all non-existing file paths. In
          effect, this will serve the index file whenever a 404 would otherwise occur in order to
          allow the SPA router to handle the request instead.
          
          [env: MINISERVE_SPA=]

      --pretty-urls
          Activate Pretty URLs mode
          
          This will cause the server to serve the equivalent `.html` file indicated by the path.
          
          `/about` will try to find `about.html` and serve it.
          
          [env: MINISERVE_PRETTY_URLS=]

  -p, --port <PORT>
          Port to use
          
          [env: MINISERVE_PORT=]
          [default: 8080]

  -i, --interfaces <INTERFACES>
          Interface to listen on
          
          [env: MINISERVE_INTERFACE=]

  -a, --auth <AUTH>
          Set authentication
          
          Currently supported formats:
          username:password, username:sha256:hash, username:sha512:hash
          (e.g. joe:123,
          joe:sha256:a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3)
          
          [env: MINISERVE_AUTH=]

      --auth-file <AUTH_FILE>
          Read authentication values from a file
          
          Example file content:
          
          joe:123
          bob:sha256:a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3
          bill:
          
          [env: MINISERVE_AUTH_FILE=]

      --route-prefix <ROUTE_PREFIX>
          Use a specific route prefix
          
          [env: MINISERVE_ROUTE_PREFIX=]

      --random-route
          Generate a random 6-hexdigit route
          
          [env: MINISERVE_RANDOM_ROUTE=]

  -P, --no-symlinks
          Hide symlinks in listing and prevent them from being followed
          
          [env: MINISERVE_NO_SYMLINKS=]

  -H, --hidden
          Show hidden files
          
          [env: MINISERVE_HIDDEN=]

  -S, --default-sorting-method <DEFAULT_SORTING_METHOD>
          Default sorting method for file list

          Possible values:
          - name: Sort by name
          - size: Sort by size
          - date: Sort by last modification date (natural sort: follows alphanumerical order)
          
          [env: MINISERVE_DEFAULT_SORTING_METHOD=]
          [default: name]

  -O, --default-sorting-order <DEFAULT_SORTING_ORDER>
          Default sorting order for file list

          Possible values:
          - asc:  Ascending order
          - desc: Descending order
          
          [env: MINISERVE_DEFAULT_SORTING_ORDER=]
          [default: desc]

  -c, --color-scheme <COLOR_SCHEME>
          Default color scheme
          
          [env: MINISERVE_COLOR_SCHEME=]
          [default: squirrel]
          [possible values: squirrel, archlinux, zenburn, monokai]

  -d, --color-scheme-dark <COLOR_SCHEME_DARK>
          Default color scheme
          
          [env: MINISERVE_COLOR_SCHEME_DARK=]
          [default: archlinux]
          [possible values: squirrel, archlinux, zenburn, monokai]

  -q, --qrcode
          Enable QR code display
          
          [env: MINISERVE_QRCODE=]

  -u, --upload-files [<ALLOWED_UPLOAD_DIR>]
          Enable file uploading (and optionally specify for which directory)
          
          The provided path is not a physical file system path. Instead, it's relative to the serve
          dir. For instance, if the serve dir is '/home/hello', set this to '/upload' to allow
          uploading to '/home/hello/upload'. When specified via environment variable, a path always
          needs to be specified.
          
          [env: MINISERVE_ALLOWED_UPLOAD_DIR=]

      --web-upload-files-concurrency <WEB_UPLOAD_CONCURRENCY>
          Configure amount of concurrent uploads when visiting the website. Must have upload-files
          option enabled for this setting to matter.
          
          For example, a value of 4 would mean that the web browser will only upload 4 files at a
          time to the web server when using the web browser interface.
          
          When the value is kept at 0, it attempts to resolve all the uploads at once in the web
          browser.
          
          NOTE: Web pages have a limit of how many active HTTP connections that they can make at one
          time, so even though you might set a concurrency limit of 100, the browser might only make
          progress on the max amount of connections it allows the web page to have open.
          
          [env: MINISERVE_WEB_UPLOAD_CONCURRENCY=]
          [default: 0]

      --chmod <CHMOD>
          Set unix file permissions of uploaded files
          
          This takes an octal number, for example 0600. By default 0666 & ~umask is used to simulate
          the system's default behavior.
          
          [env: MINISERVE_CHMOD=]

      --directory-size
          Enable recursive directory size calculation
          
          This is disabled by default because it is a potentially fairly IO intensive operation.
          
          [env: MINISERVE_DIRECTORY_SIZE=]

  -U, --mkdir
          Enable creating directories
          
          [env: MINISERVE_MKDIR_ENABLED=]

  -m, --media-type <MEDIA_TYPE>
          Specify uploadable media types
          
          [env: MINISERVE_MEDIA_TYPE=]
          [possible values: image, audio, video]

  -M, --raw-media-type <MEDIA_TYPE_RAW>
          Directly specify the uploadable media type expression
          
          [env: MINISERVE_RAW_MEDIA_TYPE=]

  -o, --on-duplicate-files <ON_DUPLICATE_FILES>
          What to do if existing files with same name is present during file upload
          
          If you enable renaming files, the renaming will occur by adding a numerical suffix to the
          filename before the final extension. For example file.txt will be uploaded as file-1.txt,
          the number will be increased until an available filename is found.
          
          [env: MINISERVE_ON_DUPLICATE_FILES=]
          [default: error]
          [possible values: error, overwrite, rename]

  -R, --rm-files [<ALLOWED_RM_DIR>]
          Enable file and directory deletion (and optionally specify for which directory)
          
          [env: MINISERVE_ALLOWED_RM_DIR=]

  -r, --enable-tar
          Enable uncompressed tar archive generation
          
          [env: MINISERVE_ENABLE_TAR=]

  -g, --enable-tar-gz
          Enable gz-compressed tar archive generation
          
          [env: MINISERVE_ENABLE_TAR_GZ=]

  -z, --enable-zip
          Enable zip archive generation
          
          WARNING: Zipping large directories can result in out-of-memory exception because zip
          generation is done in memory and cannot be sent on the fly
          
          [env: MINISERVE_ENABLE_ZIP=]

  -C, --compress-response
          Compress response
          
          WARNING: Enabling this option may slow down transfers due to CPU overhead, so it is
          disabled by default.
          
          Only enable this option if you know that your users have slow connections or if you want
          to minimize your server's bandwidth usage.
          
          [env: MINISERVE_COMPRESS_RESPONSE=]

  -D, --dirs-first
          List directories first
          
          [env: MINISERVE_DIRS_FIRST=]

  -t, --title <TITLE>
          Shown instead of host in page title and heading
          
          [env: MINISERVE_TITLE=]

      --header <HEADER>
          Inserts custom headers into the responses. Specify each header as a 'Header:Value' pair.
          This parameter can be used multiple times to add multiple headers.
          
          Example: --header "Header1:Value1" --header "Header2:Value2" (If a header is already set
          or previously inserted, it will not be overwritten.)
          
          [env: MINISERVE_HEADER=]

  -l, --show-symlink-info
          Visualize symlinks in directory listing
          
          [env: MINISERVE_SHOW_SYMLINK_INFO=]

  -F, --hide-version-footer
          Hide version footer
          
          [env: MINISERVE_HIDE_VERSION_FOOTER=]

      --hide-theme-selector
          Hide theme selector
          
          [env: MINISERVE_HIDE_THEME_SELECTOR=]

  -W, --show-wget-footer
          If enabled, display a wget command to recursively download the current directory
          
          [env: MINISERVE_SHOW_WGET_FOOTER=]

      --print-completions <shell>
          Generate completion file for a shell
          
          [possible values: bash, elvish, fish, powershell, zsh]

      --print-manpage
          Generate man page

      --tls-cert <TLS_CERT>
          TLS certificate to use
          
          [env: MINISERVE_TLS_CERT=]

      --tls-key <TLS_KEY>
          TLS private key to use
          
          [env: MINISERVE_TLS_KEY=]

      --readme
          Enable README.md rendering in directories
          
          [env: MINISERVE_README=]

  -I, --disable-indexing
          Disable indexing
          
          This will prevent directory listings from being generated and return an error instead.
          
          [env: MINISERVE_DISABLE_INDEXING=]

      --enable-webdav
          Enable read-only WebDAV support (PROPFIND requests)
          
          [env: MINISERVE_ENABLE_WEBDAV=]

      --size-display <SIZE_DISPLAY>
          Show served file size in exact bytes
          
          [env: MINISERVE_SIZE_DISPLAY=]
          [default: human]
          [possible values: human, exact]

      --file-external-url <FILE_EXTERNAL_URL>
          Optional external URL (e.g., 'http://external.example.com:8081') prepended to file links
          in listings.
          
          Allows serving files from a different URL than the browsing instance. Useful for setups
          like: one authenticated instance for browsing, linking files (via this option) to a
          second, non-indexed (-I) instance for direct downloads. This obscures the full file list
          on the download server, while users can still copy direct file URLs for sharing. The
          external URL is put verbatim in front of the relative location of the file, including the
          protocol. The user should take care this results in a valid URL, no further checks are
          being done.
          
          [env: MINISERVE_FILE_EXTERNAL_URL=]

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

## Spec 21

The exact stdout for `executable -h` is the following. The same literal-output rules as Spec 20 apply.

```text
For when you really just want to serve some files over HTTP right now!

Usage: executable [OPTIONS] [PATH]

Arguments:
  [PATH]  Which path to serve [env: MINISERVE_PATH=]

Options:
  -v, --verbose
          Be verbose, includes emitting access logs [env: MINISERVE_VERBOSE=]
      --temp-directory <TEMP_UPLOAD_DIRECTORY>
          The path to where file uploads will be written to before being moved to their correct
          location. It's wise to make sure that this directory will be written to disk and not into
          memory [env: MINISERVER_TEMP_UPLOAD_DIRECTORY=]
      --index <INDEX>
          The name of a directory index file to serve, like "index.html" [env: MINISERVE_INDEX=]
      --spa
          Activate SPA (Single Page Application) mode [env: MINISERVE_SPA=]
      --pretty-urls
          Activate Pretty URLs mode [env: MINISERVE_PRETTY_URLS=]
  -p, --port <PORT>
          Port to use [env: MINISERVE_PORT=] [default: 8080]
  -i, --interfaces <INTERFACES>
          Interface to listen on [env: MINISERVE_INTERFACE=]
  -a, --auth <AUTH>
          Set authentication [env: MINISERVE_AUTH=]
      --auth-file <AUTH_FILE>
          Read authentication values from a file [env: MINISERVE_AUTH_FILE=]
      --route-prefix <ROUTE_PREFIX>
          Use a specific route prefix [env: MINISERVE_ROUTE_PREFIX=]
      --random-route
          Generate a random 6-hexdigit route [env: MINISERVE_RANDOM_ROUTE=]
  -P, --no-symlinks
          Hide symlinks in listing and prevent them from being followed [env:
          MINISERVE_NO_SYMLINKS=]
  -H, --hidden
          Show hidden files [env: MINISERVE_HIDDEN=]
  -S, --default-sorting-method <DEFAULT_SORTING_METHOD>
          Default sorting method for file list [env: MINISERVE_DEFAULT_SORTING_METHOD=] [default:
          name] [possible values: name, size, date]
  -O, --default-sorting-order <DEFAULT_SORTING_ORDER>
          Default sorting order for file list [env: MINISERVE_DEFAULT_SORTING_ORDER=] [default:
          desc] [possible values: asc, desc]
  -c, --color-scheme <COLOR_SCHEME>
          Default color scheme [env: MINISERVE_COLOR_SCHEME=] [default: squirrel] [possible values:
          squirrel, archlinux, zenburn, monokai]
  -d, --color-scheme-dark <COLOR_SCHEME_DARK>
          Default color scheme [env: MINISERVE_COLOR_SCHEME_DARK=] [default: archlinux] [possible
          values: squirrel, archlinux, zenburn, monokai]
  -q, --qrcode
          Enable QR code display [env: MINISERVE_QRCODE=]
  -u, --upload-files [<ALLOWED_UPLOAD_DIR>]
          Enable file uploading (and optionally specify for which directory) [env:
          MINISERVE_ALLOWED_UPLOAD_DIR=]
      --web-upload-files-concurrency <WEB_UPLOAD_CONCURRENCY>
          Configure amount of concurrent uploads when visiting the website. Must have upload-files
          option enabled for this setting to matter [env: MINISERVE_WEB_UPLOAD_CONCURRENCY=]
          [default: 0]
      --chmod <CHMOD>
          Set unix file permissions of uploaded files [env: MINISERVE_CHMOD=]
      --directory-size
          Enable recursive directory size calculation [env: MINISERVE_DIRECTORY_SIZE=]
  -U, --mkdir
          Enable creating directories [env: MINISERVE_MKDIR_ENABLED=]
  -m, --media-type <MEDIA_TYPE>
          Specify uploadable media types [env: MINISERVE_MEDIA_TYPE=] [possible values: image,
          audio, video]
  -M, --raw-media-type <MEDIA_TYPE_RAW>
          Directly specify the uploadable media type expression [env: MINISERVE_RAW_MEDIA_TYPE=]
  -o, --on-duplicate-files <ON_DUPLICATE_FILES>
          What to do if existing files with same name is present during file upload [env:
          MINISERVE_ON_DUPLICATE_FILES=] [default: error] [possible values: error, overwrite,
          rename]
  -R, --rm-files [<ALLOWED_RM_DIR>]
          Enable file and directory deletion (and optionally specify for which directory) [env:
          MINISERVE_ALLOWED_RM_DIR=]
  -r, --enable-tar
          Enable uncompressed tar archive generation [env: MINISERVE_ENABLE_TAR=]
  -g, --enable-tar-gz
          Enable gz-compressed tar archive generation [env: MINISERVE_ENABLE_TAR_GZ=]
  -z, --enable-zip
          Enable zip archive generation [env: MINISERVE_ENABLE_ZIP=]
  -C, --compress-response
          Compress response [env: MINISERVE_COMPRESS_RESPONSE=]
  -D, --dirs-first
          List directories first [env: MINISERVE_DIRS_FIRST=]
  -t, --title <TITLE>
          Shown instead of host in page title and heading [env: MINISERVE_TITLE=]
      --header <HEADER>
          Inserts custom headers into the responses. Specify each header as a 'Header:Value' pair.
          This parameter can be used multiple times to add multiple headers [env: MINISERVE_HEADER=]
  -l, --show-symlink-info
          Visualize symlinks in directory listing [env: MINISERVE_SHOW_SYMLINK_INFO=]
  -F, --hide-version-footer
          Hide version footer [env: MINISERVE_HIDE_VERSION_FOOTER=]
      --hide-theme-selector
          Hide theme selector [env: MINISERVE_HIDE_THEME_SELECTOR=]
  -W, --show-wget-footer
          If enabled, display a wget command to recursively download the current directory [env:
          MINISERVE_SHOW_WGET_FOOTER=]
      --print-completions <shell>
          Generate completion file for a shell [possible values: bash, elvish, fish, powershell,
          zsh]
      --print-manpage
          Generate man page
      --tls-cert <TLS_CERT>
          TLS certificate to use [env: MINISERVE_TLS_CERT=]
      --tls-key <TLS_KEY>
          TLS private key to use [env: MINISERVE_TLS_KEY=]
      --readme
          Enable README.md rendering in directories [env: MINISERVE_README=]
  -I, --disable-indexing
          Disable indexing [env: MINISERVE_DISABLE_INDEXING=]
      --enable-webdav
          Enable read-only WebDAV support (PROPFIND requests) [env: MINISERVE_ENABLE_WEBDAV=]
      --size-display <SIZE_DISPLAY>
          Show served file size in exact bytes [env: MINISERVE_SIZE_DISPLAY=] [default: human]
          [possible values: human, exact]
      --file-external-url <FILE_EXTERNAL_URL>
          Optional external URL (e.g., 'http://external.example.com:8081') prepended to file links
          in listings [env: MINISERVE_FILE_EXTERNAL_URL=]
  -h, --help
          Print help (see more with '--help')
  -V, --version
          Print version
```
