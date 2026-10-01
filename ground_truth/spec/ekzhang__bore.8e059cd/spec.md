# `executable`: Bore-compatible TCP tunnel

## Spec 1: Deliverable and purpose

The required artifact is one runnable file named exactly `executable`. It is a
command-line TCP tunneling program compatible with `bore-cli` 0.6.0. It has two
modes:

- `executable server` runs a public relay.
- `executable local` exposes a TCP service on the local machine through that
  relay.

The program must run on Linux, must not require an interactive terminal, and
must remain running while serving or maintaining a tunnel. It must handle
several clients and forwarded connections concurrently without mixing their
data or allowing one malformed connection to terminate the server.

## Spec 2: Command-line interface

The root syntax is:

```text
executable <COMMAND>
```

The only functional commands are `local` and `server`; `help` is the usual help
pseudo-command. Options may appear before or after the positional argument
within their subcommand. Both `--option value` and `--option=value` forms are
accepted.

## Spec 3: Local mode

```text
executable local [OPTIONS] --to <TO> <LOCAL_PORT>
```

`LOCAL_PORT` is the local TCP port to expose. The options are:

| Short | Long | Value | Meaning |
|---|---|---|---|
| `-l` | `--local-host` | `HOST` | Local target host; default `localhost` |
| `-t` | `--to` | `TO` | Relay hostname or address; required unless supplied by `BORE_SERVER` |
| `-p` | `--port` | `PORT` | Requested public port; default `0`, meaning let the server choose |
| `-s` | `--secret` | `SECRET` | Optional authentication secret |
| `-h` | `--help` | none | Print local help |

`LOCAL_PORT` may instead come from `BORE_LOCAL_PORT`, `TO` from `BORE_SERVER`,
and the secret from `BORE_SECRET`. An explicit command-line value takes
precedence over its environment variable. Secret values are never displayed in
help. The local host and `TO` are strings rather than CLI-validated IP
addresses. They are passed to normal host resolution unchanged. In particular,
empty, whitespace-containing, Unicode, very long, or colon-containing `TO`
values must fail safely as connection/name-resolution errors rather than crash
or be silently rewritten. An explicitly empty `--local-host` value is accepted
by the CLI and is not rewritten to the default. The client can establish its
primary tunnel and remains running, but each public connection then fails to
connect to the empty local target: the public peer receives EOF instead of
forwarded data. The per-connection warning identifies the failed target using
an empty host followed by the requested local port.

## Spec 4: Server mode

```text
executable server [OPTIONS]
```

| Short | Long | Value | Meaning |
|---|---|---|---|
| none | `--min-port` | `MIN_PORT` | Inclusive minimum public port; default `1024` |
| none | `--max-port` | `MAX_PORT` | Inclusive maximum public port; default `65535` |
| `-s` | `--secret` | `SECRET` | Optional authentication secret |
| none | `--bind-addr` | `BIND_ADDR` | Control-server IP; default `0.0.0.0` |
| none | `--bind-tunnels` | `BIND_TUNNELS` | Public tunnel IP; defaults to the chosen `--bind-addr` |
| `-h` | `--help` | none | Print server help |

The corresponding environment variables are `BORE_MIN_PORT`, `BORE_MAX_PORT`,
and `BORE_SECRET`; explicit flags take precedence. Both bind values must be IP
literals accepted by the platform IP parser. IPv4 and IPv6 literals are valid,
but hostnames such as `localhost` and malformed/out-of-range IPv4 text are not.
An explicitly empty secret is valid and distinct from omitting the secret.

## Spec 5: Numeric validation

All port arguments and port environment variables are decimal integers in the
inclusive unsigned 16-bit range `0..=65535`. Leading zeroes remain decimal.
Letters, mixed alphanumeric text, floating-point notation, and hexadecimal
notation are invalid. The local port and requested public port both accept zero
at the parsing layer. A server range is valid when `min-port <= max-port`,
including a one-port range and ranges containing zero; a reversed range is a
usage error.

Missing local-option values, missing required arguments, unknown flags or
commands, duplicate single-value local options, and invalid values are usage
errors. Usage errors write nothing to stdout, write a clap-4-style error to
stderr, and exit with status 2. Runtime/network failures write to stderr and
exit with status 1. A negative value beginning with `-` is treated as an
unexpected argument unless positional parsing has been forced with `--`.

The negative option token has clap's short-option rendering quirk. In
particular, the invocation `executable server --min-port -100 --max-port 10000`
writes nothing to stdout, exits with status 2, and writes exactly:

```text
error: unexpected argument '-1' found

Usage: executable server [OPTIONS]

For more information, try '--help'.
```

Representative required parser forms are:

```text
error: the following required arguments were not provided:
  --to <TO>
  <LOCAL_PORT>

Usage: executable local --to <TO> <LOCAL_PORT>

For more information, try '--help'.
```

```text
error: invalid value 'abc' for '<LOCAL_PORT>': invalid digit found in string

For more information, try '--help'.
```

```text
error: invalid value '70000' for '<LOCAL_PORT>': 70000 is not in 0..=65535

For more information, try '--help'.
```

The same invalid-value wording applies with the displayed argument name
`--port <PORT>`, `--min-port <MIN_PORT>`, or `--max-port <MAX_PORT>`.
Invalid bind values use:

```text
error: invalid value 'VALUE' for '--bind-addr <BIND_ADDR>': invalid IP address syntax

For more information, try '--help'.
```

with the analogous `--bind-tunnels <BIND_TUNNELS>` name. A duplicate local
option uses, for example, `error: the argument '--to <TO>' cannot be used
multiple times`, followed by the local usage line and the help hint. A local
option present without its value uses `error: a value is required for
'--OPTION <VALUE_NAME>' but none was supplied`, followed by the standard help
hint, and exits 2. A reversed server range must produce exactly this stderr and
status 2:

```text
error: port range is empty

Usage: bore-cli <COMMAND>

For more information, try '--help'.
```

## Spec 6: Exact informational output

Help and version output goes only to stdout, ends with a newline, and exits 0.
`-h` equals `--help`, `-V` equals `--version`, `help` equals root help,
`help local` equals local help, and `help server` equals server help.

`executable --help` prints exactly:

```text
A modern, simple TCP tunnel in Rust that exposes local ports to a remote server, bypassing standard NAT connection firewalls.

Usage: executable <COMMAND>

Commands:
  local   Starts a local proxy to the remote server
  server  Runs the remote proxy server
  help    Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version
```

Invocation with no arguments writes that same block to stderr, writes nothing
to stdout, and exits 2. An unknown command uses the form below, with the actual
command substituted, and exits 2:

```text
error: unrecognized subcommand 'invalid'

Usage: executable <COMMAND>

For more information, try '--help'.
```

`executable local --help` prints exactly:

```text
Starts a local proxy to the remote server

Usage: executable local [OPTIONS] --to <TO> <LOCAL_PORT>

Arguments:
  <LOCAL_PORT>  The local port to expose [env: BORE_LOCAL_PORT=]

Options:
  -l, --local-host <HOST>  The local host to expose [default: localhost]
  -t, --to <TO>            Address of the remote server to expose local ports to [env: BORE_SERVER=]
  -p, --port <PORT>        Optional port on the remote server to select [default: 0]
  -s, --secret <SECRET>    Optional secret for authentication [env: BORE_SECRET]
  -h, --help               Print help
```

`executable server --help` prints exactly:

```text
Runs the remote proxy server

Usage: executable server [OPTIONS]

Options:
      --min-port <MIN_PORT>          Minimum accepted TCP port number [env: BORE_MIN_PORT=] [default: 1024]
      --max-port <MAX_PORT>          Maximum accepted TCP port number [env: BORE_MAX_PORT=] [default: 65535]
  -s, --secret <SECRET>              Optional secret for authentication [env: BORE_SECRET]
      --bind-addr <BIND_ADDR>        IP address to bind to, clients must reach this [default: 0.0.0.0]
      --bind-tunnels <BIND_TUNNELS>  IP address where tunnels will listen on, defaults to --bind-addr
  -h, --help                         Print help
```

`executable --version` and `executable -V` print exactly:

```text
bore-cli 0.6.0
```

Root help placed before a command, as in `executable --help local`, selects root
help. `executable help --help` is invalid because `--help` is interpreted as an
unknown help target. A subcommand-only option at root level is also invalid.

## Spec 7: Runtime error and status behavior

The local client always contacts the relay at TCP port 7835. It appends that
port to the `TO` value; it does not interpret a port embedded in `TO`. Connection
attempts and initial protocol reads time out after approximately 3 seconds.
Connection failures exit 1 with an error chain on stderr in this form:

```text
Error: could not connect to HOST:7835

Caused by:
    OPERATING-SYSTEM ERROR
```

For example, a refused Linux localhost connection reports `Connection refused
(os error 111)`, while failed name resolution reports the platform resolver
message. The supplied host text, including whitespace or an embedded colon, is
preserved in the first line.

Errors explicitly returned by the relay are printed as `Error: server error:
MESSAGE`. Important messages include `client port number not in allowed range`,
`port already in use`, and `invalid secret`. If a relay challenges an
unconfigured client, the client exits nonzero with `Error: server requires
authentication, but no client secret was provided`.

## Spec 8: Server listener and allocation

The server listens for protocol/control TCP connections on
`BIND_ADDR:7835`. It logs a startup line promptly. After ANSI and timestamp
decoration are ignored, that line contains all of `INFO`, `bore_cli::server`,
`server listening`, `addr`, and the selected bind IP.

For every accepted `Hello` request:

- A positive requested port must be inside the configured inclusive range. The
  server binds exactly that port on `BIND_TUNNELS`.
- Request `0` asks the server to choose an available port from the inclusive
  configured range. Active clients receive distinct bound ports. Allocation may
  make up to 150 random attempts; exhaustion returns `failed to find an
  available port`.
- Binding failure is mapped to `port already in use`, `permission denied`, or
  `failed to bind to port`, as applicable.
- On success, the listener remains open for the life of that client's control
  channel and the server replies with the actual bound port.

The control accept loop and all client handlers are concurrent. Rapid,
simultaneous, malformed, timed-out, or disconnected control clients must not
stop the server or prevent later clients from connecting.

## Spec 9: Wire protocol

Control messages are UTF-8 JSON frames terminated by one null byte (`0x00`).
TCP segmentation is irrelevant: partial reads must be buffered until the null
delimiter arrives. Leading and trailing JSON whitespace is accepted. A frame's
payload may contain at most 256 bytes, excluding the null delimiter: valid JSON
padded with whitespace to exactly 256 payload bytes is accepted, while a
257-byte payload is rejected. Likewise, an unterminated partial frame remains
buffered through 256 bytes, but receipt of a 257th non-null byte closes that
connection. An empty frame, malformed JSON, an unknown message variant, a
negative/overflowing JSON port, or another undecodable initial message closes
that connection cleanly without crashing the process.

The externally tagged JSON messages are:

| Direction | JSON shape | Meaning |
|---|---|---|
| client to server | `{"Hello": PORT}` | Establish primary control channel and request public port |
| client to server | `{"Authenticate": "TAG"}` | Answer an authentication challenge |
| client to server | `{"Accept": "UUID"}` | Pair this new control connection with a waiting public socket |
| server to client | `{"Challenge": "UUID"}` | Authentication challenge |
| server to client | `{"Hello": PORT}` | Public port successfully assigned |
| server to client | `"Heartbeat"` | Keepalive on the primary control connection |
| server to client | `{"Connection": "UUID"}` | A public peer is waiting to be forwarded |
| server to client | `{"Error": "MESSAGE"}` | Protocol/server error |

UUID values are ordinary lowercase hyphenated UUID strings (36 characters,
four hyphens); newly generated challenges and connection IDs are UUID v4 values
and are unique across concurrent connections.

The peer has about 3 seconds to send each initial `Hello`, `Accept`, or
authentication answer. An unauthenticated server silently closes a connection
that sends nothing in that interval. An authenticating server that times out
after sending its challenge sends:

```json
{"Error":"timed out waiting for initial message"}
```

A valid `Hello` receives `{"Hello":assigned_port}`. Values below or above the
allowed server range receive:

```json
{"Error":"client port number not in allowed range"}
```

and an occupied specifically requested port receives:

```json
{"Error":"port already in use"}
```

After the hello response, the server emits JSON `"Heartbeat"` frames promptly
and approximately every 500 ms while the primary control channel is alive.

## Spec 10: Authentication

When the server has a secret, every new control connection—including secondary
connections used to accept public sockets—must authenticate before its first
functional message:

1. The server immediately sends `{"Challenge":"UUID"}` with a fresh UUID v4.
2. Derive `key = SHA-256(secret encoded as UTF-8)`.
3. Compute HMAC-SHA-256 over the UUID's 16 raw bytes using `key`.
4. Send the 32-byte MAC as 64 lowercase hexadecimal characters in
   `{"Authenticate":"TAG"}`.
5. A correct answer permits the connection to continue. A malformed or unequal
   tag receives `{"Error":"invalid secret"}` and that connection terminates.

Comparison must validate the entire tag, not prefixes or suffixes. Secrets are
case-sensitive byte sequences and must be preserved exactly, including empty
strings, spaces, tabs, newlines, quotes, equals signs, control characters that
can be passed as an argument, Unicode, and lengths of at least 1000 bytes.
Authentication only protects the handshake; forwarded traffic is not encrypted.

A local client configured with a secret waits for a challenge before sending
its hello. If the server does not require authentication, no challenge arrives;
the mismatched configuration eventually times out/fails rather than being a CLI
parse error. A client without a secret that receives a challenge fails with the
client-side authentication-required error described above.

## Spec 11: Establishing and forwarding a tunnel

The end-to-end sequence is:

1. Local mode opens a primary connection to `TO:7835`, performs authentication
   if configured, sends `Hello(requested_port)`, and receives `Hello(actual_port)`.
2. It remains running and logs both `connected to server` with a `remote_port`
   field and `listening at TO:actual_port`. Logging may include normal timestamp,
   level, module, span, and ANSI decorations.
3. A public peer connects to the server's assigned tunnel port. The server
   accepts it, creates a fresh connection UUID, stores the socket, then sends
   `Connection(UUID)` on the primary channel.
4. The local client concurrently opens a new connection to `TO:7835`, performs
   authentication if required, and sends `Accept(UUID)`. It also connects to
   `LOCAL_HOST:LOCAL_PORT` with the 3-second connection timeout.
5. The server removes the matching stored public socket and bridges it to the
   secondary control connection. The client bridges that connection to the
   local target. From then on, bytes flow transparently in both directions.

Forwarding must preserve arbitrary binary data, at least 100 KB per connection,
and TCP half-close behavior: closing one write direction must not discard data
still traveling in the other direction. Several simultaneous and sequential
connections must be independent, and closing one forwarded socket must not end
the primary tunnel or its heartbeats.

If an `Accept` names a syntactically valid but missing UUID, the server handles
it without crashing; the process continues serving other connections. A public
socket not accepted within about 10 seconds is removed as stale. An invalid UUID
or an out-of-order/otherwise unexpected initial message is handled by closing or
rejecting only that control connection. If the relay closes, local mode must
detect EOF and exit without a panic or abort.

## Spec 12: Examples

Expose a service on local port 8000 through a relay:

```text
./executable local 8000 --to relay.example
```

Run a relay limited to public ports 40000 through 40100:

```text
./executable server --min-port 40000 --max-port 40100
```

Run both ends with authentication:

```text
./executable server --secret 'shared secret'
./executable local 8000 --to 127.0.0.1 --secret 'shared secret'
```
