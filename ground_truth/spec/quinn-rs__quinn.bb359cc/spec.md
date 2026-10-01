# Quinn performance executable specification

The required artifact is a runnable file named exactly `executable`. It is a command-line QUIC throughput tool with `server` and `client` modes. All text is UTF-8. Unless a section says otherwise, option names are case-sensitive and may be written as either `--option value` or `--option=value`.

## Spec 1

`executable` must be directly runnable on Linux and must remain usable when several independent copies are run concurrently. It must support a long-running UDP/QUIC server and, except for the non-`-` JSON-file shutdown behavior specified in Spec 16, a finite-duration client. A server that has started successfully remains alive until externally terminated and must tolerate SIGTERM without printing a panic or fatal error. It must handle multiple simultaneous streams, multiple simultaneous clients, and several sequential client connections without retaining stale connection state.

Command-line syntax errors use exit status 2, write only to stderr, and leave stdout empty. Successful help uses status 0, writes only to stdout, and leaves stderr empty. Operational failures discovered after argument parsing (for example DNS failure or failure to read a credential file) are logged to stdout and the program then returns status 0. A successful client transfer returns status 0.

## Spec 2

The top-level grammar is `executable <COMMAND>`, where the only commands are `server`, `client`, and the built-in `help`. With no arguments, print the exact top-level help below to stderr and exit 2. `--help`, `-h`, repeated help flags, and `help` print it to stdout and exit 0. The text, spacing, capitalization, blank lines, and final newline are part of the interface:

```text
Usage: executable <COMMAND>

Commands:
  server  Run as a perf server
  client  Run as a perf client
  help    Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help
```

`help server` and `help client` are aliases for the corresponding subcommand help. A top-level help flag takes precedence over a later unknown top-level flag. By contrast, after the option terminator, `executable -- --help` treats `--help` as a subcommand and rejects it. `executable help --help` likewise rejects `--help` as an unrecognized subcommand. No `--version` option exists.

## Spec 3

`executable server --help` and `executable help server` print exactly the following, with a final newline, and exit 0:

```text
Run as a perf server

Usage: executable server [OPTIONS]

Options:
      --listen <LISTEN>
          Address to listen on
          
          [default: [::]:4433]

  -k, --key <KEY>
          TLS private key in DER format

  -c, --cert <CERT>
          TLS certificate in PEM format

      --send-buffer-size <SEND_BUFFER_SIZE>
          Send buffer size in bytes
          
          This can use SI suffixes for sizes. For example, 1M will request 1MiB, 10G will request 10GiB.
          
          [default: 2M]

      --recv-buffer-size <RECV_BUFFER_SIZE>
          Receive buffer size in bytes
          
          This can use SI suffixes for sizes. For example, 1M will request 1MiB, 10G will request 10GiB.
          
          [default: 2M]

      --conn-stats
          Whether to print connection statistics

      --keylog
          Perform NSS-compatible TLS key logging to the file specified in `SSLKEYLOGFILE`

      --initial-mtu <INITIAL_MTU>
          UDP payload size that the network must be capable of carrying
          
          [default: 1200]

      --no-protection
          Disable packet encryption/decryption (for debugging purpose)

      --initial-rtt <INITIAL_RTT>
          The initial round-trip-time (in msecs)

      --ack-frequency
          Ack Frequency mode

      --congestion <CONG_ALG>
          Congestion algorithm to use
          
          [possible values: cubic, bbr, new-reno]

      --stream-receive-window <STREAM_RECEIVE_WINDOW>
          Maximum number of bytes the peer may transmit without acknowledgement on any one stream before becoming blocked.
          
          This can use SI suffixes for sizes. For example, 1M will limit to 1MiB, 10G will limit to 10GiB.

      --receive-window <RECEIVE_WINDOW>
          Maximum number of bytes the peer may transmit across all streams of a connection before becoming blocked.
          
          This can use SI suffixes for sizes. For example, 1M will limit to 1MiB, 10G will limit to 10GiB.

      --send-window <SEND_WINDOW>
          Maximum number of bytes to transmit to a peer without acknowledgment
          
          This can use SI suffixes for sizes. For example, 1M will limit to 1MiB, 10G will limit to 10GiB.

      --max-udp-payload-size <MAX_UDP_PAYLOAD_SIZE>
          Max UDP payload size in bytes
          
          [default: 1472]

      --qlog <QLOG_FILE>
          qlog output file

  -h, --help
          Print help (see a summary with '-h')
```

`executable server -h` is also accepted, writes nothing to stderr, exits 0, and prints this distinct compact help, with a final newline:

```text
Run as a perf server

Usage: executable server [OPTIONS]

Options:
      --listen <LISTEN>
          Address to listen on [default: [::]:4433]
  -k, --key <KEY>
          TLS private key in DER format
  -c, --cert <CERT>
          TLS certificate in PEM format
      --send-buffer-size <SEND_BUFFER_SIZE>
          Send buffer size in bytes [default: 2M]
      --recv-buffer-size <RECV_BUFFER_SIZE>
          Receive buffer size in bytes [default: 2M]
      --conn-stats
          Whether to print connection statistics
      --keylog
          Perform NSS-compatible TLS key logging to the file specified in `SSLKEYLOGFILE`
      --initial-mtu <INITIAL_MTU>
          UDP payload size that the network must be capable of carrying [default: 1200]
      --no-protection
          Disable packet encryption/decryption (for debugging purpose)
      --initial-rtt <INITIAL_RTT>
          The initial round-trip-time (in msecs)
      --ack-frequency
          Ack Frequency mode
      --congestion <CONG_ALG>
          Congestion algorithm to use [possible values: cubic, bbr, new-reno]
      --stream-receive-window <STREAM_RECEIVE_WINDOW>
          Maximum number of bytes the peer may transmit without acknowledgement on any one stream before becoming blocked
      --receive-window <RECEIVE_WINDOW>
          Maximum number of bytes the peer may transmit across all streams of a connection before becoming blocked
      --send-window <SEND_WINDOW>
          Maximum number of bytes to transmit to a peer without acknowledgment
      --max-udp-payload-size <MAX_UDP_PAYLOAD_SIZE>
          Max UDP payload size in bytes [default: 1472]
      --qlog <QLOG_FILE>
          qlog output file
  -h, --help
          Print help (see more with '--help')
```

## Spec 4

`executable client --help` and `executable help client` print exactly the following, with a final newline, and exit 0:

```text
Run as a perf client

Usage: executable client [OPTIONS] [HOST]

Arguments:
  [HOST]
          Host to connect to
          
          [default: localhost:4433]

Options:
      --ip <IP>
          Override DNS resolution for host

      --local-addr <LOCAL_ADDR>
          Specify the local socket address

      --uni-requests <UNI_REQUESTS>
          Number of unidirectional requests to maintain concurrently
          
          [default: 0]

      --bi-requests <BI_REQUESTS>
          Number of bidirectional requests to maintain concurrently
          
          [default: 1]

      --download-size <DOWNLOAD_SIZE>
          Number of bytes to request
          
          This can use SI suffixes for sizes. For example, 1M will transfer 1MiB, 10G will transfer 10GiB.
          
          [default: 1M]

      --upload-size <UPLOAD_SIZE>
          Number of bytes to transmit, in addition to the request header
          
          This can use SI suffixes for sizes. For example, 1M will transfer 1MiB, 10G will transfer 10GiB.
          
          [default: 1M]

      --duration <DURATION>
          The time to run in seconds
          
          [default: 60]

      --interval <INTERVAL>
          The interval in seconds at which stats are reported
          
          [default: 1]

      --json <JSON>
          File path to output JSON statistics to. If the file is '-', stdout will be used

      --send-buffer-size <SEND_BUFFER_SIZE>
          Send buffer size in bytes
          
          This can use SI suffixes for sizes. For example, 1M will request 1MiB, 10G will request 10GiB.
          
          [default: 2M]

      --recv-buffer-size <RECV_BUFFER_SIZE>
          Receive buffer size in bytes
          
          This can use SI suffixes for sizes. For example, 1M will request 1MiB, 10G will request 10GiB.
          
          [default: 2M]

      --conn-stats
          Whether to print connection statistics

      --keylog
          Perform NSS-compatible TLS key logging to the file specified in `SSLKEYLOGFILE`

      --initial-mtu <INITIAL_MTU>
          UDP payload size that the network must be capable of carrying
          
          [default: 1200]

      --no-protection
          Disable packet encryption/decryption (for debugging purpose)

      --initial-rtt <INITIAL_RTT>
          The initial round-trip-time (in msecs)

      --ack-frequency
          Ack Frequency mode

      --congestion <CONG_ALG>
          Congestion algorithm to use
          
          [possible values: cubic, bbr, new-reno]

      --stream-receive-window <STREAM_RECEIVE_WINDOW>
          Maximum number of bytes the peer may transmit without acknowledgement on any one stream before becoming blocked.
          
          This can use SI suffixes for sizes. For example, 1M will limit to 1MiB, 10G will limit to 10GiB.

      --receive-window <RECEIVE_WINDOW>
          Maximum number of bytes the peer may transmit across all streams of a connection before becoming blocked.
          
          This can use SI suffixes for sizes. For example, 1M will limit to 1MiB, 10G will limit to 10GiB.

      --send-window <SEND_WINDOW>
          Maximum number of bytes to transmit to a peer without acknowledgment
          
          This can use SI suffixes for sizes. For example, 1M will limit to 1MiB, 10G will limit to 10GiB.

      --max-udp-payload-size <MAX_UDP_PAYLOAD_SIZE>
          Max UDP payload size in bytes
          
          [default: 1472]

      --qlog <QLOG_FILE>
          qlog output file

  -h, --help
          Print help (see a summary with '-h')
```

`executable client -h` is also accepted, writes nothing to stderr, exits 0, and prints this distinct compact help, with a final newline:

```text
Run as a perf client

Usage: executable client [OPTIONS] [HOST]

Arguments:
  [HOST]  Host to connect to [default: localhost:4433]

Options:
      --ip <IP>
          Override DNS resolution for host
      --local-addr <LOCAL_ADDR>
          Specify the local socket address
      --uni-requests <UNI_REQUESTS>
          Number of unidirectional requests to maintain concurrently [default: 0]
      --bi-requests <BI_REQUESTS>
          Number of bidirectional requests to maintain concurrently [default: 1]
      --download-size <DOWNLOAD_SIZE>
          Number of bytes to request [default: 1M]
      --upload-size <UPLOAD_SIZE>
          Number of bytes to transmit, in addition to the request header [default: 1M]
      --duration <DURATION>
          The time to run in seconds [default: 60]
      --interval <INTERVAL>
          The interval in seconds at which stats are reported [default: 1]
      --json <JSON>
          File path to output JSON statistics to. If the file is '-', stdout will be used
      --send-buffer-size <SEND_BUFFER_SIZE>
          Send buffer size in bytes [default: 2M]
      --recv-buffer-size <RECV_BUFFER_SIZE>
          Receive buffer size in bytes [default: 2M]
      --conn-stats
          Whether to print connection statistics
      --keylog
          Perform NSS-compatible TLS key logging to the file specified in `SSLKEYLOGFILE`
      --initial-mtu <INITIAL_MTU>
          UDP payload size that the network must be capable of carrying [default: 1200]
      --no-protection
          Disable packet encryption/decryption (for debugging purpose)
      --initial-rtt <INITIAL_RTT>
          The initial round-trip-time (in msecs)
      --ack-frequency
          Ack Frequency mode
      --congestion <CONG_ALG>
          Congestion algorithm to use [possible values: cubic, bbr, new-reno]
      --stream-receive-window <STREAM_RECEIVE_WINDOW>
          Maximum number of bytes the peer may transmit without acknowledgement on any one stream before becoming blocked
      --receive-window <RECEIVE_WINDOW>
          Maximum number of bytes the peer may transmit across all streams of a connection before becoming blocked
      --send-window <SEND_WINDOW>
          Maximum number of bytes to transmit to a peer without acknowledgment
      --max-udp-payload-size <MAX_UDP_PAYLOAD_SIZE>
          Max UDP payload size in bytes [default: 1472]
      --qlog <QLOG_FILE>
          qlog output file
  -h, --help
          Print help (see more with '--help')
```

## Spec 5

Argument errors must follow this clap-style form and end in a newline:

```text
error: DESCRIPTION

Usage: USAGE

For more information, try '--help'.
```

Value-conversion errors omit the `Usage` paragraph and consist of the `error:` line, an optional possible-values line, a blank line, and `For more information, try '--help'.`. Unknown subcommands say `error: unrecognized subcommand 'VALUE'` and use `Usage: executable <COMMAND>`. Unknown top-level or server/client options say `error: unexpected argument 'VALUE' found` and use the appropriate usage line. Every rendered tip line begins with exactly two ASCII spaces before `tip:`. In particular, `client --invalid-option value` includes a blank line and `  tip: to pass '--invalid-option' as a value, use '-- --invalid-option'` before `Usage: executable client [OPTIONS] [HOST]`; an unknown server option has no such tip. `--conn-stats server` at top level must be rejected and include `  tip: 'server --conn-stats' exists`.

Options cannot be repeated. For example, repeating `--initial-mtu` reports `error: the argument '--initial-mtu <INITIAL_MTU>' cannot be used multiple times`; repeating `--listen` uses the same wording with `<LISTEN>`. Boolean switches take no values; `server --conn-stats=true` reports `error: unexpected value 'true' for '--conn-stats' found; no more were expected` and shows `Usage: executable server --conn-stats`. Every non-boolean option requires a value; a missing value says `a value is required for '--name <METAVAR>'`. At most one client HOST positional is allowed; a second is reported as `error: unexpected argument 'SECOND_HOST' found` and uses `Usage: executable client [OPTIONS] [HOST]`. `--` stops option parsing, so following text can be the single HOST.

Within a subcommand, help can appear before or after HOST and normally overrides ordinary execution. However malformed values and duplicate options encountered before help are still errors. Both short and long help together are accepted.

## Spec 6

The byte-size parser is shared by `--download-size`, `--upload-size`, both socket-buffer options, and all three window options. It trims leading and trailing whitespace, then accepts a nonempty decimal integer with an optional single leading `+` and with either no suffix or exactly one of these case-sensitive binary suffixes:

| Suffix | Multiplier |
|---|---:|
| none | 1 |
| `k` | 1,024 |
| `M` | 1,048,576 |
| `G` | 1,073,741,824 |
| `T` | 1,099,511,627,776 |

Thus `512k` is 524288, `1M` is 1048576, `5G` is 5368709120, and `2T` is 2199023255552. Zero, one, leading zeroes, and values through unsigned 64-bit maximum are valid when representable; `--download-size=+1` is accepted as the value one. Reject decimals, negative signs that reach conversion, embedded whitespace, suffix-only values, repeated suffixes, `K`, `m`, `g`, `t`, `MB`, and all other letters. Empty or suffix-only numeric parts produce `cannot parse integer from empty string`; invalid characters produce `invalid digit found in string`; a numeric part itself above unsigned 64-bit range produces `number too large to fit in target type`. Multiplication by a suffix is not overflow-checked: `--download-size=18000000T` passes argument parsing and proceeds to the ordinary connection attempt rather than reporting a conversion error. The full first line is, for example:

```text
error: invalid value '1.5M' for '--download-size <DOWNLOAD_SIZE>': invalid digit found in string
```

When a negative token is supplied with a space, such as `--download-size -1`, it is treated as an unexpected option-like argument and the error includes `  tip: to pass '-1' as a value, use '-- -1'`. For the suffixed token `--download-size -1M`, the diagnostic strips the suffix and reports `error: unexpected argument '-1' found`, followed by `  tip: to pass '-1' as a value, use '-- -1'`. With equals syntax a negative value reaches unsigned parsing and is invalid.

## Spec 7

`--listen` and `--local-addr` are complete numeric socket addresses: IPv4 uses `IP:PORT`, and IPv6 uses `[IP]:PORT`. No whitespace is trimmed. Missing hosts, missing ports, malformed syntax, and ports above 65535 are invalid. A listen conversion error is exactly of the form `error: invalid value 'VALUE' for '--listen <LISTEN>': invalid socket address syntax`, followed by the standard final help hint. `--ip` is a bare IPv4 or IPv6 address and reports `invalid IP address syntax` on bad input.

HOST is a hostname or IPv4 address plus decimal port and defaults to `localhost:4433`. Split it into host and port, resolve the host, and connect to the resolved address. Unlike `--listen` and `--local-addr`, HOST does not parse bracketed IPv6 socket syntax: `client [::1]:PORT` returns status 0 without transferring, leaves stderr empty, and logs `ERROR quinn_perf: parsing port: cannot parse integer from empty string` to stdout. Other malformed ports are likewise operational `parsing port` errors. An empty HOST is an operational `resolving host: invalid socket address` error. DNS failure is logged as `ERROR quinn_perf: resolving host: ...`; on Linux, an unknown host must include `failed to lookup address information: Name or service not known`. `--ip IP` bypasses DNS for the address while preserving the HOST name for connection identity and its port. `--local-addr` selects the local UDP bind address. Without it, choose `[::]:0` for a successfully resolved IPv6 peer and `0.0.0.0:0` for an IPv4 peer; an IPv6-unspecified server socket should be dual-stack so IPv4 clients can connect when the platform supports it.

## Spec 8

The following are unsigned decimal integer options with no fractional or negative forms: `--uni-requests`, `--bi-requests`, `--duration`, `--interval`, `--initial-rtt`, `--initial-mtu`, and `--max-udp-payload-size`. Their unsigned conversion accepts a single leading `+`; in particular, `--interval=+1` is accepted as one and proceeds to ordinary execution. `initial-mtu` is parsed as an unsigned 16-bit value, so 65536 reports `65536 is not in 0..=65535`; values 1, 576, 1200, 1300, 1400, 1500, and 9000 are accepted. RTT is milliseconds and accepts at least 0 through 5000, subject to the unsigned 64-bit limit. Duration and interval are whole seconds; values such as `0.1` are invalid.

`--congestion` is case-sensitive and has exactly `cubic`, `bbr`, and `new-reno`. The base form for an invalid value that receives no similarity suggestion is:

```text
error: invalid value 'VALUE' for '--congestion <CONG_ALG>'
  [possible values: cubic, bbr, new-reno]

For more information, try '--help'.
```

When clap finds a close valid spelling, it inserts a two-space-indented similarity tip and another blank line before the final help hint. These two invocations have the following exact stderr and exit status 2:

`server --congestion Cubic`:

```text
error: invalid value 'Cubic' for '--congestion <CONG_ALG>'
  [possible values: cubic, bbr, new-reno]

  tip: a similar value exists: 'cubic'

For more information, try '--help'.
```

`server --congestion new_reno`:

```text
error: invalid value 'new_reno' for '--congestion <CONG_ALG>'
  [possible values: cubic, bbr, new-reno]

  tip: a similar value exists: 'new-reno'

For more information, try '--help'.
```

Apply the selected congestion controller, initial RTT, initial MTU, maximum UDP payload size, ACK-frequency mode, per-stream receive window, connection receive window, and send window to the QUIC transport on whichever side supplied them. Valid options must work independently and in arbitrary combinations on both client and server.

## Spec 9

Server mode binds a UDP QUIC endpoint at `--listen`, defaulting to `[::]:4433`. When `RUST_LOG` enables info, successful startup writes an info line to stdout whose normalized text is exactly `INFO perf::server: listening on ADDRESS`. It writes this once per server process. When debug logging is enabled, each accepted connection writes `DEBUG perf::server: PEER connected`.

Both modes request `SO_SNDBUF` and `SO_RCVBUF` using `--send-buffer-size` and `--recv-buffer-size`, each defaulting to 2 MiB. Query the effective kernel value. If it is smaller than requested, write to stdout: `WARN perf: Unable to set desired send buffer size. Desired: REQUESTED, Actual: ACTUAL` or its `recv` counterpart. Do not warn merely because the effective value is larger than requested. Normal logs are timestamped in UTC RFC-3339 form, such as `2026-04-25T05:10:51.461160Z`, and may carry ANSI level/target styling. Warning-level logs appear even without `RUST_LOG`; info and debug obey that environment filter.

## Spec 10

The server uses TLS 1.3 for normal QUIC connections and negotiates the ALPN protocol identifier `perf`. If neither `--cert` nor `--key` is supplied, generate an in-memory self-signed certificate usable by this client. If either is supplied, the other becomes required during CLI validation. Supplying only the certificate must name `--key <KEY>` as missing and use `Usage: executable server --cert <CERT> --key <KEY>`; the inverse names the certificate and orders the usage as `server --key <KEY> --cert <CERT>`.

With both paths present, read the private key first, accepting standard PEM private-key encodings, then read the PEM certificate chain and verify the key matches. Failures discovered here are operational: log to stdout and return normally. Required normalized messages include `ERROR quinn_perf: reading private key: I/O error: No such file or directory (os error 2)`, `reading private key: no items found`, `reading certificate chain file: I/O error: ...`, and `reading certificate chain: base64 decode error: InvalidCharacter(...)`. Cryptographic construction failures terminate with status 101, leave stdout empty, and emit a Rust panic on stderr. An invalid private-key encoding includes the exact substring ``called `Result::unwrap()` on an `Err` value: General("failed to parse private key as RSA, ECDSA, or EdDSA")``. A certificate/private-key mismatch includes the exact substring ``called `Result::unwrap()` on an `Err` value: InconsistentKeys(KeyMismatch)``. A valid supplied pair must support client connections and the server must remain alive afterward.

## Spec 11

The client establishes one QUIC connection to HOST and accepts the server's generated or supplied test certificate without requiring an external trust store. With info logging, it writes `INFO perf::client: connecting to HOSTNAME at RESOLVED_SOCKET_ADDRESS`, then `INFO perf::client: local addr LOCAL_SOCKET_ADDRESS`. Connection establishment and transport failures are operational log errors rather than CLI errors. The normal connection attempt timeout is approximately 30 seconds; a timeout is logged as `ERROR quinn_perf: connecting: timed out`.

Once connected, the client runs for approximately `--duration` seconds. Except for the non-`-` JSON-file case specified in Spec 16, a two-second workload should take at least 1.5 seconds and finish comfortably before four seconds on localhost, and repeated one- to three-second runs complete reliably. When both `--uni-requests` and `--bi-requests` are zero, the client connects but creates no work and remains waiting rather than exiting at the duration deadline.

## Spec 12

Each request begins with an eight-byte, big-endian unsigned download-length header, followed by exactly `upload-size` arbitrary payload bytes. The server decodes the header, completely drains the request payload, and sends exactly the requested `download-size` bytes. It must handle sizes 0 and 1 without special failure, the 1 MiB chunk boundary, multi-megabyte upload/download bodies, and enough chunking that large bodies are not allocated as one unbounded buffer.

For a bidirectional request, the client opens a client-initiated bidirectional QUIC stream, sends header and upload on it, and reads the response on that same stream. For a unidirectional request, it opens a client-initiated unidirectional stream for header/upload, and the server opens a separate server-initiated unidirectional response stream. The peers must associate and continuously replace completed streams so the configured concurrency is maintained throughout the duration. Both stream types may operate simultaneously without blocking each other.

## Spec 13

With server debug logging, completed bidirectional work emits these lines in phase order for each logical stream, with logical IDs starting at 0 and increasing by one:

```text
DEBUG perf::server: got req for N bytes on client bidirectional stream ID
DEBUG perf::server: finished reading client bidirectional stream ID
DEBUG perf::server: finished responding on client bidirectional stream ID
```

Unidirectional work emits:

```text
DEBUG perf::server: got req for N bytes on client unidirectional stream CLIENT_ID
DEBUG perf::server: finished reading client unidirectional stream CLIENT_ID
DEBUG perf::server: finished responding on server unidirectional stream SERVER_ID
```

Client- and server-unidirectional logical IDs are independent and start at 0. Under termination, at most the final in-flight read/response may lack its completion log. At least the configured concurrency worth of distinct streams must be processed promptly; 50 concurrent bidirectional streams over three localhost seconds must achieve at least 5 completed requests per second.

## Spec 14

The client defaults are one bidirectional worker, zero unidirectional workers, 1 MiB download, 1 MiB upload, 60-second duration, and one-second report interval. It must support zero-byte bodies, small bodies, several-megabyte bodies, at least 20 concurrent bidirectional workers, at least five workers of each type together, and rapid sequential reconnection. Valid custom congestion, buffer, MTU, RTT, ACK-frequency, and flow-control settings must still allow transfers even when client and server choose different valid values.

At every whole reporting interval through the requested duration, emit a cumulative report. Consequently duration 1/interval 1 produces one report, duration 2/interval 1 produces at least two, and duration 3/interval 1 produces at least three. Request totals never decrease. The RPS value is completed-request count divided by displayed elapsed seconds, rounded consistently enough that recomputation from the printed count and time differs by no more than 1%.

## Spec 15

Each ordinary report on stdout has this structure and these exact labels and box characters; numeric values vary:

```text
Overall stats:
RPS: 123.45 (123 requests in 1.00s)

Stream metrics:

      │ Upload Duration │ Download Duration | FBL        | Upload Throughput | Download Throughput
──────┼─────────────────┼───────────────────┼────────────┼───────────────────┼────────────────────
 AVG  │ ...
 P0   │ ...
 P10  │ ...
 P50  │ ...
 P90  │ ...
 P100 │ ...
```

Every row has all five values. Durations use readable `ns`, `µs`, or `ms` forms and throughput uses a positive decimal followed by `Mb/s` when completed nonzero transfers exist. `FBL` means time to first byte. `AVG` is the arithmetic average; percentile rows represent the 0th, 10th, 50th, 90th, and 100th percentile over completed request observations. Reports for active localhost workloads with a nonzero upload or download must contain positive RPS and meaningful nonzero upload/download throughput; large transfers should readily exceed 100 Mb/s on localhost. A one-second bidirectional workload with both `--download-size 0` and `--upload-size 0` still processes requests and exits 0, but its report is exactly `RPS: 0.00 (0 requests in 1.00s)` rather than counting those zero-byte completions.

## Spec 16

`--json PATH` adds machine-readable statistics. `PATH` must be nonempty. A value of `-` writes one compact, single-line JSON document to stdout after the human reports. Any other value creates or replaces that file with the JSON document; in that case stdout must not contain a line beginning with `{`, though human reports remain on stdout.

There is a deterministic shutdown exception for the non-`-` file form. Against an active localhost server, `client HOST --duration 2 --interval 1 --json FILE --download-size 16k --upload-size 16k` emits two human reports, replaces `FILE` with JSON, and emits no JSON line on stdout, but remains running beyond 12 seconds instead of returning at the duration deadline.

The top-level object has exactly `start` and `intervals`. `start` has exactly `timestamp`, whose only member is positive integer Unix epoch seconds `timesecs`. `intervals` contains one entry per completed report boundary; it is empty when duration is shorter than interval. Each interval has exactly `streams` and `sum`. Each stream has exactly:

```text
id, start, end, seconds, bytes, bits_per_second, sender
```

`id` and `bytes` are integers, `sender` is Boolean, and the time/throughput members are numbers. Times are seconds relative to test start, `end >= start`, and `seconds > 0`. A bidirectional transfer may produce a sender entry and a receiver entry with the same QUIC stream ID. Each interval `sum` has exactly `start`, `end`, `seconds`, `bytes`, `bits_per_second`, and `sender`. Byte and throughput values are nonnegative, and active intervals have positive values. For every stream and sum, `bits_per_second = bytes * 8 / seconds` within normal floating-point error (0.1%). Intervals represent sequential, non-overlapping measurement periods and contain completed stream activity for active workloads.

## Spec 17

`--conn-stats` makes each side periodically print the active QUIC connection statistics to stdout in a one-line Rust-Debug-like representation beginning `ConnectionStats {`. It must include nested fields named `udp_tx: UdpStats { datagrams: N, bytes: N, ios: N }`, `udp_rx`, `frame_tx: FrameStats { ... }`, `frame_rx`, and `path: PathStats { ... }`. Frame statistics include at least `ACK`, `ACK_FREQUENCY`, `CRYPTO`, and `STREAM` numeric counters. Path statistics include duration-formatted `rtt` (for example `608.542µs`), plus numeric `cwnd`, `congestion_events`, `lost_packets`, `lost_bytes`, `sent_packets`, and `current_mtu`. An active transfer must show positive sent datagram/byte counts; sustained default localhost traffic should exceed 100 transmitted datagrams. Client stats follow each interval report. A server with this switch emits at least once while a multi-second connection is active.

## Spec 18

`--keylog` enables NSS TLS key logging at the filesystem path in the `SSLKEYLOGFILE` environment variable. On server startup, create the file even before a connection; it is empty until a handshake. Do not create it merely because the environment variable exists when the flag is absent. The client likewise creates it when enabled. After a successful protected connection, both enabled endpoints write all of these TLS 1.3 labels:

```text
CLIENT_HANDSHAKE_TRAFFIC_SECRET
SERVER_HANDSHAKE_TRAFFIC_SECRET
CLIENT_TRAFFIC_SECRET_0
SERVER_TRAFFIC_SECRET_0
EXPORTER_SECRET
```

Every non-comment line is `LABEL CLIENT_RANDOM_HEX SECRET_HEX`, exactly three whitespace-separated fields; the latter two are each 64 hexadecimal characters. Files must contain more than 100 bytes after a handshake. `--qlog FILE` is accepted on client and server and configures that connection's qlog destination without interfering with startup, resolution, or transfer.

## Spec 19

`--no-protection` selects a debug QUIC cryptographic backend that bypasses packet encryption/decryption while retaining the QUIC handshake, framing, flow control, stream behavior, and statistics. A client and server both using the flag must transfer normally for the same size and concurrency combinations as protected mode and produce positive reports. It must compose with all three congestion algorithms, ACK-frequency mode, RTT/MTU settings, socket buffers, and flow-control windows. Server startup and logging remain identical apart from the crypto implementation.

## Spec 20

The server and client must perform real sustained data movement, not merely accept options or print canned success. They must preserve exact requested byte counts (including binary suffix expansion), fully drain uploads before completing requests, send complete downloads, keep concurrent workers supplied with new streams, and shut down individual connections without bringing down the server. Apart from the exact zero-body reporting behavior in Spec 15 and non-`-` JSON-file shutdown behavior in Spec 16, normal one- to three-second localhost workloads must finish within the surrounding five- to ten-second process timeouts, produce at least one completed request for each active configuration, and avoid deadlock under mixed or high stream concurrency.
