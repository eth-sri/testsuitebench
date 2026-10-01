# Masscan-compatible executable specification

The required artifact is a single runnable program named `executable`. All examples below invoke that program directly. It must implement the command-line, configuration, parsing, conversion, and diagnostic behavior described here without requiring repository source code or another program. Unless a rule explicitly says otherwise, ordinary diagnostics go to standard error, generated configuration and converted scan data go to standard output, and files named by output options receive the generated data.

## Spec 1

The executable is a command-line-compatible implementation of the observable control-plane and file-format behavior of Masscan. It must accept GNU-style long options (`--name value` and, where a value is needed, `--name=value`), compact single-letter options such as `-p80`, and configuration files. Option names are case-sensitive; symbolic values such as output-format names are case-insensitive where stated below.

The program must not hang while processing malformed or extremely large inputs. Normal parsing and conversion operations must finish promptly. Unless another section assigns a different result, successful configuration echoing, self-testing, and list generation return status 0. Informational help/version modes intentionally return status 1. Many nonfatal parsing diagnostics deliberately coexist with a successful `--echo` result; those cases are identified below.

The program may be started from any working directory. Paths are interpreted relative to that directory. It must preserve arbitrary path spelling, including spaces, Unicode, `~`, and relative components, when echoing a path; shell expansion is not performed by the executable.

## Spec 2

In the evaluation environment, packet-capture support is unavailable. Any ordinary invocation that initializes capture support, including most `--echo`, scan, read-scan, self-test, and benchmark invocations, must append these exact lines to standard error:

```text
[-] FAIL: failed to load libpcap shared library
    [hint]: you must install libpcap or WinPcap
```

The lines end in a newline. This environmental warning does not by itself change an otherwise successful echo or self-test into a failure. Pure informational modes (`--help`, `--nmap`, and version display) and successful `--banner1` capture-file validation do not emit it. When another diagnostic is required, preserve that diagnostic's specified order relative to this warning; generally the specific parse/file message precedes or accompanies initialization output as illustrated below.

## Spec 3

`--help` writes exactly the following text to standard output, writes nothing to standard error, and returns 1:

```text
usage: masscan [options] [<IP|RANGE>... -pPORT[,PORT...]]
MASSCAN is a fast port scanner. The primary input parameters are the
IP addresses/ranges you want to scan, and the port numbers. An example
is the following, which scans the 10.x.x.x network for web servers:

    masscan 10.0.0.0/8 -p80

The program auto-detects network interface/adapter settings. If this
fails, you'll have to set these manually. The following is an
example of all the parameters that are needed:

    --adapter-ip 192.168.10.123
    --adapter-mac 00-11-22-33-44-55
    --router-mac 66-55-44-33-22-11

Parameters can be set either via the command-line or config-file. The
names are the same for both. Thus, the above adapter settings would
appear as follows in a configuration file:

    adapter-ip = 192.168.10.123
    adapter-mac = 00-11-22-33-44-55
    router-mac = 66-55-44-33-22-11

All single-dash parameters have a spelled out double-dash equivalent,
so '-p80' is the same as '--ports 80' (or 'ports = 80' in config file).
To use the config file, type:

    masscan -c <filename>

To generate a config-file from the current settings, use the --echo
option. This stops the program from actually running, and just echoes
the current configuration instead. This is a useful way to generate
your first config file, or see a list of parameters you didn't know
about. I suggest you try it now:

    masscan -p1234 --echo

```

There are two newline characters after the final nonempty line.

## Spec 4

`--nmap` writes this exact compatibility summary to standard output, writes nothing to standard error, and returns 1:

```text
Masscan (https://github.com/robertdavidgraham/masscan)
Usage: masscan [Options] -p{Target-Ports} {Target-IP-Ranges}
TARGET SPECIFICATION:
  Can pass only IPv4/IPv6 address, CIDR networks, or ranges (non-nmap style)
  Ex: 10.0.0.0/8, 192.168.0.1, 10.0.0.1-10.0.0.254
  -iL <inputfilename>: Input from list of hosts/networks
  --exclude <host1[,host2][,host3],...>: Exclude hosts/networks
  --excludefile <exclude_file>: Exclude list from file
  --randomize-hosts: Randomize order of hosts (default)
HOST DISCOVERY:
  -Pn: Treat all hosts as online (default)
  -n: Never do DNS resolution (default)
SCAN TECHNIQUES:
  -sS: TCP SYN (always on, default)
SERVICE/VERSION DETECTION:
  --banners: get the banners of the listening service if available. The
    default timeout for waiting to receive data is 30 seconds.
PORT SPECIFICATION AND SCAN ORDER:
  -p <port ranges>: Only scan specified ports
    Ex: -p22; -p1-65535; -p 111,137,80,139,8080
TIMING AND PERFORMANCE:
  --max-rate <number>: Send packets no faster than <number> per second
  --connection-timeout <number>: time in seconds a TCP connection will
    timeout while waiting for banner data from a port.
FIREWALL/IDS EVASION AND SPOOFING:
  -S/--source-ip <IP_Address>: Spoof source address
  -e <iface>: Use specified interface
  -g/--source-port <portnum>: Use given port number
  --ttl <val>: Set IP time-to-live field
  --spoof-mac <mac address/prefix/vendor name>: Spoof your MAC address
OUTPUT:
  --output-format <format>: Sets output to binary/list/unicornscan/json/ndjson/grepable/xml
  --output-file <file>: Write scan results to file. If --output-format is
     not given default is xml
  -oL/-oJ/-oD/-oG/-oB/-oX/-oU <file>: Output scan in List/JSON/nDjson/Grepable/Binary/XML/Unicornscan format,
     respectively, to the given filename. Shortcut for
     --output-format <format> --output-file <file>
  -v: Increase verbosity level (use -vv or more for greater effect)
  -d: Increase debugging level (use -dd or more for greater effect)
  --open: Only show open (or possibly open) ports
  --packet-trace: Show all packets sent and received
  --iflist: Print host interfaces and routes (for debugging)
  --append-output: Append to rather than clobber specified output files
  --resume <filename>: Resume an aborted scan
MISC:
  --send-eth: Send using raw ethernet frames (default)
  -V: Print version number
  -h: Print this help summary page.
EXAMPLES:
  masscan -v -sS 192.168.0.0/16 10.0.0.0/8 -p 80
  masscan 23.0.0.0/0 -p80 --banners -output-format binary --output-filename internet.scan
  masscan --open --banners --readscan internet.scan -oG internet_scan.grepable
SEE (https://github.com/robertdavidgraham/masscan) FOR MORE HELP

```

Thus there are two newline characters after the final nonempty line.

## Spec 5

`--version` and `-V` are aliases. They return 1, produce no standard error, and print a multi-line version report to standard output. Standard output begins with exactly one newline, so the first line is empty; the following lines must then occur in this order and match these forms:

```text
Masscan version <nonempty version> ( https://github.com/robertdavidgraham/masscan )
Compiled on: <nonempty build description>
Compiler: <nonempty compiler description>
OS: Linux
CPU: <nonempty CPU description> (64 bits)
GIT version: <possibly empty revision description>
```

Invoking the executable with no arguments returns 1, writes the capture-library warning from Spec 2 to standard error, and writes exactly this short usage document to standard output:

```text
usage: masscan [options] [<IP|RANGE>... -pPORT[,PORT...]]

examples:
    masscan -p80,8000-8100 10.0.0.0/8 --rate=10000
        scan some web ports on 10.x.x.x at 10kpps

    masscan --nmap
        list those options that are compatible with nmap

    masscan -p80 10.0.0.0/8 --banners -oB <filename>
        save results of scan in binary format to <filename>

    masscan --open --banners --readscan <filename> -oX <savefile>
        read binary scan results in <filename> and save them as xml in <savefile>
```

The final line ends with one newline.

`-h` also prints the short help rather than the long `--help` document. Its standard output contains `usage:`, `masscan`, `examples:`, a `masscan -p80...` example, and a pointer to `--nmap` for the compatibility option list.

## Spec 6

Long options which need values consume the next token even when that token begins with `-`. For example, `--adapter-ip --echo` tries to use `--echo` as the address and does not enter echo mode. It returns 1, writes nothing to standard output, does not initialize capture support, and writes exactly this ordered block to standard error:

```text
[-] _parser_next(): unknown coding failure
FAIL: bad source IP address: adapter-ip=--echo
hint   addresses look like "192.168.1.23" or "2001:db8:1::1ce9".
```

A bare `--` is not an end-of-options marker. `--echo -- 10.0.0.1 -p80` is diagnosed as `CONF: unknown config option: =10.0.0.1`.

An unknown value-less long option such as `--bogus` or `--nonexistent-flag` returns 1 and writes `<option-name-without-leading-dashes>: empty parameter` to standard error, followed by the capture-library warning. It writes the exact short usage document from Spec 5 to standard output, not standard error. Thus, after removal of the environmental warning, `--invalid-flag` has exactly `invalid-flag: empty parameter\n` on standard error. There is an order-dependent echo exception: if `--echo` has already been processed, a trailing unknown value-less long option preserves the ordinary configuration echo and status 0 while still writing its `empty parameter` line followed by the capture warning. For example, `--echo -p80 192.168.1.0/24 --norandomize` returns 0, echoes the configured port and range, and writes `norandomize: empty parameter` before the warning. `--foo=bar --echo` reports `CONF: unknown config option: foo=bar`. An unknown configuration-file key is fatal and its diagnostic contains `unknown config option`.

The same missing-parameter form applies when a recognized value-taking long option is the final token. In particular, invoking only `--range` returns 1, writes `range: empty parameter` and then the capture-library warning to standard error, and writes the exact short usage document from Spec 5 to standard output. Invoking only `--rate` behaves analogously with `rate: empty parameter`. An absent value is not passed to range or numeric validation as an empty string.

The deliberately unsupported compact forms have stable errors: `-r10` returns 1, writes nothing to standard output, and writes exactly `nmap(-r10): wat? randomization is our raison d'etre!! rethink prease\n` to standard error. `-oX` without a following filename returns 1, writes exactly `missing output filename\n` to standard error, writes nothing to standard output, and exits before capture initialization. Likewise, `-oZ file` returns 1, writes exactly `nmap(-oZ): unknown output format\n` to standard error, writes nothing to standard output, and emits no capture-library warning.

## Spec 7

`-c FILE` and `--conf FILE` load configuration. A configuration is line-oriented. A setting is `key = value`; spaces or tabs around the key, separator, and value are trimmed. Split only at the first `=`, so later equals signs are part of the value. Accept LF and CRLF, long lines, blank lines, and comment lines whose first non-space character is `#`. A `#` after a setting has begun is not an inline-comment delimiter; it remains part of the value even when preceded by whitespace. Consequently, a file line `rate = 222 # inline` is passed to rate parsing as the value `222 # inline`, produces `CONF: non-digit in rate spec: rate=222 # inline`, and does not replace an earlier valid rate. Ignore noncomment lines with no `=`. An empty or comment-only file is valid.

Configuration keys are the long option names without leading dashes. Command-line and file settings share one model. Repeated scalar settings use the last effective value in argument-processing order, regardless of whether the value came directly from the command line or from a configuration file. A file is applied where its `-c`/`--conf` token occurs: therefore `--max-rate 333 --rotate-dir cli -c <file-containing-rate-222-and-rotate-dir-two> --echo` echoes `rate = 222` and `rotate-dir = two`, while placing those command-line settings after the file echoes `rate = 333` and `rotate-dir = cli`. Set-valued targets, ports, and exclusions accumulate across all sources. Multiple configuration files are allowed, with later file values superseding earlier scalar file values.

Recognized positive Boolean spellings include `true`, `TRUE`, `yes`, `Yes`, `on`, `enable`, `enabled`, and `1`; enabled settings echo in their canonical form, normally `key = true`.

If a configuration file is missing during `--echo`, return 0 and report:

```text
[-] FAIL: reading configuration file
[-] <path>: No such file or directory
[-] cwd = <actual-current-directory>
```

The capture-library warning follows these three lines. Without echo, a missing required configuration is fatal and returns 1. It writes the exact short usage document from Spec 5 to standard output. Standard error contains this exact path-sensitive block, followed by the capture-library warning:

```text
[-] FAIL: reading configuration file
[-] <path>: No such file or directory
[-] cwd = <actual-current-directory>
```

The `<path>` field preserves the supplied spelling, including spaces: from working directory `/workspace`, `--conf '/nonexistent/file with spaces.conf'` uses `[-] /nonexistent/file with spaces.conf: No such file or directory`, while `-c /no/such/file` uses `[-] /no/such/file: No such file or directory`. Echo output contains no comments copied from source files and can itself be loaded as a valid configuration.

## Spec 8

`--echo` prints the canonical effective configuration and performs no scan. With no other explicit settings, standard output has this form:

```text
seed = <unsigned-decimal-seed>
rate = 100       
shard = 1/1
nocapture = servername
nocapture = servername


# TARGET SELECTION (IP, PORTS, EXCLUDES)
ports = 
```

There is a final newline. The default seed is nonzero and less than 2^64 and may vary from run to run. The spaces following integral rate 100 pad its numeric field to ten characters. The duplicated default `nocapture` line and the two empty lines before the heading are intentional compatibility behavior.

Explicit, nondefault settings that later sections define as serialized appear before the target heading. Represented scalar settings use a stable broad order independent of argument order; additive settings such as hello strings and capture types use the compatibility ordering stated in their sections. Some accepted states deliberately have no echo line, including the capture, VLAN, and packet compatibility cases identified in Specs 19 through 22. The broad ordering of represented settings is seed, rate, shard, banner/payload/HTTP/capture settings, output settings, adapter and packet settings, timing settings, then the target block. In particular, when output and adapter settings are both present, `output-filename` and `output-format` occur before `adapter`, `adapter-ip`, and `adapter-port`; within those groups, the members have exactly the orders just shown. The target block starts with `ports = ` and then contains zero or more `range = ...` and exclusion-derived canonical ranges. Do not print unset optional keys. `--echo-all` is accepted and prints an echo including defaulted settings.

## Spec 9

Canonical echo spelling is used regardless of the alias supplied. Important mappings include `--max-rate` to `rate`, `--source-ip` to `adapter-ip`, `--source-port` to `adapter-port`, `--interface` to `adapter`, `--output-file` to `output-filename`, and `--rotate-time` to `rotate`. `--blackrock-rounds` is the ordinary-echo omission described in Spec 20, not a `rounds` echo mapping. Repeating a scalar uses its final effective value; repeating an additive target or port merges it into the existing set.

Paths and free-form strings are echoed without shell interpretation. Numeric values are printed in decimal. A default-sized integral rate is left-aligned in a ten-character field (`1000` has six trailing spaces, `10000` five); rate `100000` is rendered `100000.000000`. Indexed hello keys retain brackets, for example `hello-string[80] = ...`; indexed HTTP headers instead use the compatibility serialization in Spec 22. Canonical output must be deterministic except for an unspecified default seed and clock-dependent informational timestamps.

## Spec 10

IPv4 targets may be positional or values of `--range`. Accept a single address, inclusive `first-last`, CIDR prefixes `/0` through `/32`, and comma-separated mixtures. Decimal components with leading zeroes remain decimal, not octal. Accept boundary addresses `0.0.0.0` and `255.255.255.255`.

Mask host bits in CIDR input: `192.168.1.129/28` becomes `192.168.1.128/28`. Sort target intervals, remove duplicates, and merge overlapping or adjacent intervals. Render a singleton as one address, an exactly aligned power-of-two interval as CIDR, and another interval as `first-last`. The full IPv4 space is the boundary compatibility case: both `-p80 0.0.0.0/0 --echo` and `--echo 0.0.0.0/0 -p80` emit exactly `range = 0.0.0.0/0`, not a `0.0.0.0-255.255.255.255` interval. Three adjacent addresses `10.0.0.1,10.0.0.2,10.0.0.3` become `10.0.0.1-10.0.0.3`.

Reject bad component counts, octets above 255, embedded whitespace, bad characters, and prefixes above 32 with `ERROR: bad IP address/range: <token>`. There are two range-separator compatibility exceptions when targets are read from an include file: the UTF-8 en dash (`U+2013`) and the single legacy byte `0x96` are treated as `-`. Thus a file containing either form of `192.168.1.1–192.168.1.10` returns 0 in echo mode and emits `range = 192.168.1.1-192.168.1.10`. There is also one historical component exception: a trailing empty fourth component is zero, so `192.168.1.` canonicalizes to `192.168.1.0`. In echo mode an invalid target is a nonfatal diagnostic and the bad item is omitted. A reversed IPv4 interval contributes no addresses rather than being reordered. A one-address explicit interval canonicalizes to the single address.

## Spec 11

IPv6 targets support full and compressed notation, upper- or lower-case hexadecimal, `::`, `::1`, inclusive address ranges, and CIDR `/0` through `/128`. Bracketed forms `[address]`, `[address]/prefix`, and `[address]-[address]` are accepted. There is a top-of-space parser exception: the unbracketed all-ones address `ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff` is rejected with these two lines:

```text
FAIL: unknown command-line parameter "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"
 [hint] did you want "--ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"?
```

Canonical output is lowercase and uses the standard longest-zero-run compression; CIDRs have host bits cleared. A `/128` echoes as its single address, while `2001:db8::1/0` reaches the full-space scan-size rejection described in Spec 13 before an ordinary echo can be produced. IPv4 and IPv6 targets may coexist and each family is sorted and merged internally.

Reject malformed multiple-compression forms, invalid hexadecimal, oversized groups, prefix 129 or greater, and IPv4-mapped IPv6 notation. Emit the same `ERROR: bad IP address/range: <token>` family of diagnostics and omit invalid echo entries. A forward pair of comma-separated IPv6 addresses is combined by normal interval merging (for example `2001:db8::1,2001:db8::2` becomes `2001:db8::1-2001:db8::2`). A reversed IPv6 interval read from an include file is treated as an unsigned wrapping range. For example, a file containing `2001:db8::10-2001:db8::1`, used by `--echo --includefile <file> -p80`, returns 1 without a configuration echo and reports the 128-bit scan-size failure from Spec 13 after the capture warning. Other IPv6 target sizes participate in that safety limit as well.

## Spec 12

`-iL FILE`, `--includefile FILE`, and `--include-file FILE` read targets. Each noncomment line may contain one target or a comma-separated target list. Ignore blank lines and lines whose first non-space characters are `#`, `;`, `//`, or `-`; trim surrounding whitespace, accept CRLF and a final line without newline, and accept mixed IPv4/IPv6. Apply the same normalization and merging as command-line targets, including the reversed-IPv6 wrapping rule in Spec 11. `-iL -` reads this data from standard input.

`--exclude VALUE` adds excluded addresses/ranges. `--excludefile FILE` and `--exclude-file FILE` are aliases that read them using the same text grammar, and multiple exclusion files accumulate. A successfully loaded nonempty exclude file reports `<path>: excluding N ranges from file` on standard error, where `N` counts normalized merged ranges rather than source lines. Thus two adjacent singleton lines `10.0.0.1` and `10.0.0.2`, even when separated by comments and blanks, report `excluding 1 ranges from file`. A successfully loaded empty file reports no exclusion-count line: specifically, `--echo -p80 10.0.0.0/24 --excludefile /dev/null` returns 0 and standard error contains only the capture-library warning. Subtract exclusions from inclusions, splitting intervals where necessary. For example, including `192.168.1.0/24` and excluding `.1-.10` leaves `192.168.1.0` and `192.168.1.11-192.168.1.255`; excluding `192.168.1.0/24` from `192.168.0.0/16` leaves `192.168.0.0/24` and `192.168.2.0-192.168.255.255`. An exclusion may eliminate everything.

A missing target/exclude file is fatal and reports `[-] FAIL: parsing IP addresses` plus the path and operating-system error. An invalid address in an include file is fatal and identifies `invalid IP address on line #<one-based-line>` followed by `[-] FAIL: error reading from include file`.

## Spec 13

`--echo-cidr` converts every effective IPv4 or IPv6 range into the minimal ordered list of aligned CIDR blocks, one per output line. A CIDR input that is already minimal is unchanged and a single IPv6 address is printed with `/128`. For example, `192.168.1.0-192.168.1.100` becomes:

```text
192.168.1.0/26
192.168.1.64/27
192.168.1.96/30
192.168.1.100/32
```

For IPv6, `2001:db8::1-2001:db8::ff` becomes:

```text
2001:db8::1/128
2001:db8::2/127
2001:db8::4/126
2001:db8::8/125
2001:db8::10/124
2001:db8::20/123
2001:db8::40/122
2001:db8::80/121
```

The top-of-space interval `ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff` hits the all-ones parser exception from Spec 11: `--echo-cidr` returns 1, produces no standard output, and writes:

```text
FAIL: unknown command-line parameter "ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"
 [hint] did you want "--ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"?
```

The lower boundary-crossing case does work: `::ffff:ffff:ffff:ffff-::1:0000:0000:0001:0001` decomposes to `::ffff:ffff:ffff:ffff/128`, `::1:0:0:0:0/112`, and `::1:0:0:1:0/127`.

Before either a real scan or ordinary `--echo` output, compute the compatibility address/port search-space bit count. Refuse a space requiring more than 63 index bits and report `[-] FAIL: scan range too large, max is 63-bits, requested is N bits` plus a hint. Examples include an IPv6 `/64` combined with one port (65 bits) and IPv6 `/32` with one port (97 bits). The count saturates at the IPv6 width instead of growing beyond it: `--echo --range ::/0 -p0-65535` reports `requested is 128 bits`, not 145, and a reversed IPv6 include interval that wraps across the top of the address space also reports 128 bits. In particular, `-p80 2001:db8::/32 --seed 12345 --echo` returns 1, emits no configuration, and writes the capture-library warning followed by:

```text
[-] FAIL: scan range too large, max is 63-bits, requested is 97 bits
    Hint: scan range is number of IP addresses times number of ports
    Hint: IPv6 subnet must be at least /66 
```

The final hint has one trailing ASCII space after `/66` and before its newline. Do not allocate memory proportional to an IPv6 range.

A real scan selecting more than 1,000,000,000 IPv4 addresses requires at least one explicit exclusion as confirmation; echo mode does not. With no exclusion it returns 1 and, after the capture-library warning, writes exactly:

```text
FAIL: range too big, need confirmation
 [hint] to prevent accidents, at least one --exclude must be specified
 [hint] use "--exclude 255.255.255.255" as a simple confirmation
```

The threshold is strictly greater than one billion: a range of exactly 1,000,000,000 addresses does not trigger it. The exclusion need not intersect the target; `--exclude 255.255.255.255` is sufficient confirmation for `0.0.0.0/1`.

## Spec 14

Target ports are accepted through `-p80`, `-p 80`, `--ports 80`, and `--ports=80`. Values are comma-separated single decimal ports or inclusive ranges; surrounding whitespace is accepted. Valid port numbers are 0 through 65535. Merge repetitions, sort, deduplicate, and coalesce adjacent/overlapping intervals. Port exclusions supplied by `--exclude-ports` or its unhyphenated alias `--excludeports` are subtracted, so `1-100` excluding `50-60` becomes `1-49,61-100`.

Prefixes select protocols: `T:` TCP, `U:` UDP, `S:` SCTP, and `I:` ICMP. Unprefixed ports are TCP by default and canonical TCP output omits `T:`. Protocol groups have deterministic TCP, UDP, SCTP, ICMP ordering; `T:80,T:443,U:53,S:7` echoes `80,443,U:53,S:7`. `-sU` changes unprefixed ports to UDP, `-sZ` to SCTP, and `--ping` adds `I:0`. The Nmap IP-protocol selector `-sO` is accepted as a compatibility no-op in echo mode: `--echo -sO -p1` returns 0 and echoes `ports = 1` without a separate scan-type setting.

The special spelling `-p-` selects TCP ports 1 through 65535 (not port zero) and echoes `ports = 1-65535`. Reversed port intervals and ports above 65535 are fatal. Empty separated short and long arguments differ. `-p "" 127.0.0.1` returns 1, writes nothing to standard output, and writes the following lines to standard error in this order:

```text
: empty parameter
[-] FAIL: failed to load libpcap shared library
    [hint]: you must install libpcap or WinPcap
FAIL: no ports were specified
 [hint] try something like "-p80,8000-9000"
 [hint] try something like "--ports 0-65535"
```

By contrast, `--ports "" --echo` returns 0, writes the ordinary echo with the empty line `ports = `, and writes only the capture-library warning to standard error. In particular, `-p99999` returns 1 without the capture-library warning and writes exactly:

```text
[-] FAIL: bad target port: 99999
    Hint: a port is a number [0..65535]
```

Other bad-port forms report the analogous `[-] FAIL: bad target port: <value>` (or `FAIL: bad target port`) and the same four-space-indented hint. Unknown prefix `A:` reports `bad port character = A` and `FAIL: bad target port: A:0`.

A reversed range terminates before capture initialization even when `--echo` is present. For example, `--echo -p 80-79 10.0.0.1` returns 1, writes nothing to standard output, and writes exactly:

```text
[-] FAIL: bad target port: 80-79
    Hint: a port is a number [0..65535]
```

A normal scan with targets but no ports returns 1 and, after the capture-library warning, writes:

```text
FAIL: no ports were specified
 [hint] try something like "-p80,8000-9000"
 [hint] try something like "--ports 0-65535"
```

A normal scan with ports but no target likewise returns 1 and writes:

```text
FAIL: target IP address list empty
 [hint] try something like "--range 10.0.0.0/8"
 [hint] try something like "--range 192.168.0.100-192.168.0.200"
```

If port exclusions remove every selected port, replace the ordinary no-ports failure and its two hints with the single line ` [hint] all ports were removed by exclusion ranges`. If address exclusions remove every selected target, retain `FAIL: target IP address list empty` but replace its two example hints with ` [hint] all addresses were removed by exclusion ranges`. These exclusion cases return 1. Echo mode permits either set to be empty.

## Spec 15

`--top-ports N` and `--topports N` are aliases that add the first N entries from the built-in popular-port ordering. In particular, `--top-ports 10` canonically produces:

```text
ports = 21-25,80,443,990,992,8080
```

and zero adds nothing. Top ports combine with explicitly selected ports and exclusions using the same set rules.

Compatibility scan selectors `-Pn`, `-n`, `-sS`, `--randomize-hosts`, and `--send-eth` are recognized and do not cause an unknown-option failure. `--offline` and `--dry-run` select a no-transmission mode and echo `offline = true`; it must still perform parsing and create any requested output file. `--infinite` and `--randomize-hosts` are accepted state controls. `--norandomize` is not recognized: `--norandomize --echo` returns 1, writes no standard output, and writes exactly `CONF: unknown config option: norandomize=--echo` followed by a newline to standard error.

`--arpscan` and `--arp` are aliases that select ARP discovery mode and are accepted by echo. In particular, `--arp --echo` returns 0 and its canonical echo contains `arpscan = true`, broadcast values for both router MAC families, and `ports = I:2`. A real invocation cannot combine ARP discovery with a nonempty port scan; it returns 1 before scanning and reports exactly `FAIL: cannot arpscan and portscan at the same time` apart from the environmental capture warning.

## Spec 16

`--rate` and `--max-rate` are aliases. Accept decimal integers and fractions including zero and `0.5`; the last scalar value wins. A nondigit such as `abc` emits `CONF: non-digit in rate spec: rate=abc` (using the supplied alias name when appropriate). Echo mode remains usable after that diagnostic. Formatting follows Spec 9.

A bare final `--rate` is the missing-parameter case from Spec 6, not a nondigit value. It returns 1, emits `rate: empty parameter` before the capture-library warning, and prints the short usage document to standard output.

`--seed N` accepts the full unsigned 64-bit range from 0 through `18446744073709551615` and echoes the decimal (zero may remain zero or be replaced by a time-derived value). `--seed time` requests a generated time-derived seed. A negative seed is accepted, converted/wrapped into an unsigned decimal seed, and does not make echo fail. With no explicit seed, echo generates a nonzero unsigned 64-bit value. Repeated seed settings use the last one. A nonnumeric value must still leave a valid seed line while being diagnosed or replaced by a generated seed.

`--min-rate VALUE` is recognized only for Nmap compatibility. In echo mode it returns 0, does not set the maximum rate, and reports exactly `nmap(min-rate): unsupported, we go as fast as --max-rate allows`.

`--retries` and `--max-retry` are aliases for a nonnegative integer below 1000. In echo mode the tested negative value is a nonfatal setting error: both `--retries -1 --echo` and `--max-retry -1 --echo` return 0, omit `retries` from the configuration, and write the literal-placeholder diagnostic `FAIL: retries=<n>: expected number less than 1000` before the capture-library warning. The diagnostic contains `<n>`, not the supplied value. `--ttl` accepts integers from 0 through 255. In ordinary echo output, both zero and the tested accepted upper bound in `--ttl 255 --echo` are omitted. The latter returns 0 with no TTL-specific diagnostic. In echo mode the tested out-of-range values 256 and 300 are nonfatal setting errors: return 0, omit `ttl` from the echoed configuration, and write the following literal-placeholder diagnostic before the capture-library warning:

```text
error: ttl=<n>: expected number less than 256
```

The text contains the literal characters `<n>`, not the supplied value `256`.

A nonnumeric TTL is silently ignored in echo mode: `--ttl abc -p80 192.168.0.0/24 --echo` returns 0, emits no TTL-specific diagnostic, and omits `ttl` while otherwise printing the normal configuration and capture-library warning.

Very large integral rate inputs are serialized as integral decimal text after the reference's floating-point conversion, without a `.000000` suffix. In particular, `--rate 99999999999999999999 --echo` returns 0 and echoes `rate = 100000000000000016384`.

## Spec 17

`--shard INDEX/COUNT` is one-indexed: both values are positive and INDEX may not exceed COUNT. Echo it as `shard = INDEX/COUNT`. An index of zero is nonfatal in echo mode: it leaves the default `shard = 1/1`, returns 0, and writes exactly these two lines before the capture-library warning:

```text
FAIL: shard index can't be zero
hint   it goes like 1/4 2/4 3/4 4/4
```

Other malformed shard specifications can additionally report `FAIL: shard spec is wrong`; that line is not printed for the zero-index case.

In echo mode, the tested malformed values with a zero denominator (`1/0`), an index greater than the count (`2/1` or `5/4`), or no slash (`2`) are nonfatal. Each returns 0, retains `shard = 1/1`, prints the normal echo, and writes exactly these two lines before the capture-library warning:

```text
FAIL: shard spec is wrong
hint   it goes like 1/4 2/4 3/4 4/4
```

When COUNT is greater than one and no seed was explicitly supplied, warn:

```text
[-] WARNING: --seed <num> is not specified
    HINT: all shards must share the same seed
```

`--resume-index`, `--resume-count`, and values loaded from `--resume FILE` participate in the echoed state; a resume file uses the configuration grammar. Accept duration options `--connection-timeout`, `--hello-timeout`, and `--wait`, with seconds as the basic unit and `forever` for an unbounded wait. Their echo representations differ: in `--connection-timeout 5 --hello-timeout 7 --wait forever --rotate 2h --rotate-size 512k --rotate-dir 'dir with spaces' --echo`, `hello-timeout = 7` is serialized, while both `connection-timeout = 5` and `wait = forever` are omitted. The command returns 0.

`--rotate` and `--rotate-time` accept bare seconds and minute or hour suffixes and echo seconds as `rotate = N`; the symbolic value `hourly` is accepted on the command line and in configuration files and echoes `rotate = 3600`. Despite accepting smaller duration suffixes, the aliases reject the tested day and week values. Each of `--rotate 2d --echo`, `--rotate-time 2d --echo`, `--rotate 1w --echo`, and `--rotate-time 1w --echo` returns 1, writes no standard output, initializes no capture support, and writes exactly `--rotate-offset: value is greater than 1 day` followed by a newline to standard error. Accept `--rotate-offset` with the same unit syntax, but require its effective value to be less than one day: `1d`, `25h`, `1w`, and `2d` fail with `--rotate-offset: value is greater than 1 day`. A negative offset counts backward from the end of a day, so `-5h` echoes `rotate-offset = 68400`; zero is valid and omitted from ordinary echo. `--rotate-size` and `--rotate-filesize` are aliases; accept bare bytes or binary `k`, `m`, `g`, `t`, `p`, and `e` suffixes (for example `512k` is `524288` and `2g` is `2147483648`). A suffix without digits means one unit, so `m` is `1048576`. A bad rotate-size suffix terminates parsing, returns 1, produces no configuration echo or capture-library warning, and writes only `--rotate-size: unknown character\n`; bad offsets use their corresponding diagnostic. `--rotate-dir` and `--rotate-directory` are aliases that store the path canonically as `rotate-dir`. Repeated rotation scalars use the last value.

## Spec 18

Source-address aliases are `--adapter-ip`, `--source-ip`, and `-S`; source-port aliases are `--adapter-port`, `--source-port`, and `-g`. Accept a single IPv4 or IPv6 source address. Also accept a comma-separated IPv4 source-address list; packet-template configuration uses its first member as the canonical adapter address. Thus `-p80 --source-ip 10.0.0.1,10.0.0.2 --seed 12345 --echo` returns 0 and echoes `adapter-ip = 10.0.0.1`, not the comma list. An IPv4 source-address interval is permitted only if its inclusive cardinality is a power of two and it is forward ordered, such as `.0-.7`; otherwise return 1 and write `FAIL: range must be even power of two: adapter-ip=<value>`. Thus `--adapter-ip 192.168.1.1-192.168.1.10 --echo` writes exactly `FAIL: range must be even power of two: adapter-ip=192.168.1.1-192.168.1.10` followed by a newline and produces no configuration echo or capture-library warning. A forward IPv6 source interval is accepted and echoed in canonical `first-last` notation. A bad address returns 1, produces no configuration echo or capture-library warning, and writes exactly these two lines after substituting the supplied value in the first. The diagnostic key retains a supplied `source-ip` alias; otherwise it is `adapter-ip`:

```text
FAIL: bad source IP address: <adapter-ip-or-source-ip>=<value>
hint   addresses look like "192.168.1.23" or "2001:db8:1::1ce9".
```

Thus `--source-ip 999.999.999.999 --echo` writes `FAIL: bad source IP address: source-ip=999.999.999.999` as its first line.

A source port is a single port or forward inclusive range of power-of-two cardinality, e.g. `60000-61023` or `1024-2047`. A one-value range canonicalizes to the value. Reject values above 65535 as a bad source port. A non-power-of-two range returns 1, produces no configuration echo or capture-library warning, and writes `FAIL: source port range must be even power of two: source-port=<value>` followed by a newline; for example, `61000-62000` is reported as `FAIL: source port range must be even power of two: source-port=61000-62000`. Malformed text reports `only one 'source-port' range may be specified, found 0 ranges`. Canonical echo keys are `adapter-ip` and `adapter-port`, and repeated scalar settings use the last value. Adapter/packet settings form a separate echo section after banner/capture settings. In the exact combination `--banners --source-port 12345 -p80,443 --echo`, the two default `nocapture` lines are followed by two blank lines, then `adapter-port = 12345`, and then immediately by the target heading with no intervening blank line:

```text
banners = true
nocapture = servername
nocapture = servername


adapter-port = 12345
# TARGET SELECTION (IP, PORTS, EXCLUDES)
ports = 80,443
```

## Spec 19

Interface aliases are `--adapter`, `--interface`, and `-e`. An explicitly empty interface value is accepted but omitted: `--echo --interface '' -p80 10.0.0.1` returns 0 and emits no `adapter = ` line. MAC aliases are `--adapter-mac`, `--spoof-mac`, and `--source-mac`. Accept six-byte hexadecimal MAC addresses with colon separators, dash separators, or no separators, in mixed case, and canonicalize to lowercase dash-separated form. If more than six well-formed octets are provided, retain the first six. Too few octets or invalid hexadecimal is nonfatal in echo mode: return 0, omit the invalid MAC from standard output, and report it before the capture-library warning. Invalid `--adapter-mac invalid` writes `[-] CONF: bad MAC address: adapter-mac = invalid`; invalid `--router-mac zz:zz:zz:zz:zz:zz` writes `[-] CONF: bad MAC address: router-mac = zz:zz:zz:zz:zz:zz`.

`--router-mac VALUE` sets both `router-mac-ipv4` and `router-mac-ipv6`; protocol-specific router-MAC options affect only their family. `--router-ip` is accepted and echoed canonically. `--adapter-vlan` and `--vlan` consume their values and are accepted, but they do not produce an `adapter-vlan` or `vlan` line in ordinary echo output. In particular, `--vlan 37 --echo` returns 0 and omits both keys. Repeating an adapter retains the final value and writes `CONF: overwriting "adapter=<old>"` before the capture-library warning. For example, `-e eth0 -e eth1 --echo` writes exactly `CONF: overwriting "adapter=eth0"\n` as the adapter-specific warning and echoes `adapter = eth1`. A repeated MAC assignment must retain the final value and write `[-] WARNING: overwriting MAC address, was <old>, now <new>` followed by a newline before the capture-library warning. This applies when the earlier value came from a configuration file and the later value came from the command line; the echo still returns 0.

## Spec 20

Recognize the packet-construction settings `--tcp-mss`/`--tcpmss`, `--tcp-wscale`, `--tcp-tsecho`, `--tcp-sackok`, `--noreset`, `--min-packet`, `--data-length`, `--sendq`, `--pfring`, and `--packet-trace`, but serialize only the state that the reference exposes. A bare `--tcp-mss`, `--tcpmss 1460`, and `--tcp-mss=1460` all echo `tcp-mss = enable`; the numeric spelling does not echo `1460`. `--tcp-mss=false` echoes `tcp-mss = disable`. A bare `--tcp-sackok` echoes `tcp-sackok = enable`, and `--noreset` echoes `noreset = true`. `--tcp-wscale 0` echoes `tcp-wscale = disable`; values 1 and 3 echo `tcp-wscale = enable`; value 2 and values 4 through 254 echo numerically. Thus `--tcp-wscale 15 --echo` succeeds and emits `tcp-wscale = 15`; the value is not limited to 14. Values 255 and 256 are omitted with `[-] tcp-wscale: bad value: <value>` before the capture-library warning. `--tcp-tsecho 123` echoes `tcp-tsecho = 123`. The bare Boolean form does not consume the following option: `--echo --tcp-tsecho -p80 10.0.0.1` returns 0, selects port 80, and echoes `tcp-tsecho = enable`. These forms return 0 in echo mode.

The default packet size `--min-packet 60` and the tested `--data-length 100` are accepted but omitted from ordinary echo. Every other tested effective minimum-packet value is serialized numerically: this includes 0, 1, 59, 61 through 65, and 100. In particular, `--min-packet 64 --echo` emits `min-packet = 64`, and `--echo --min-packet 100 -p80 10.0.0.1` emits `min-packet = 100`. `--sendq`, `--pfring`, and `--packet-trace` are accepted without their own configuration lines. These omissions are intentional. A nonnumeric `--min-packet not-a-number` is interpreted as zero and echoes `min-packet = 0`; nonnumeric `--data-length not-a-number` is accepted and omitted.

A data length at or above 1500 is rejected. In echo mode, `--data-length 1500` is a nonfatal setting error: return 0, omit `data-length`, and write the literal-placeholder line `error: data-length=<n>: expected number less than 1500` before the capture-library warning. The diagnostic contains `<n>`, not the supplied number.

`--pcap FILE` and `--pcap-filename FILE` are filename-valued aliases: each consumes `FILE` and canonically echoes `pcap-filename = FILE`. The configuration key `pcap-filename = FILE` has the same effect. Preserve the filename spelling as supplied.

`--blackrock-rounds N` affects the benchmark round count but is omitted from ordinary echo; `--blackrock-rounds 6 --echo` returns 0 without a `rounds` line. A nonnumeric value is also accepted and omitted in echo mode.

Debug and verbosity forms `-v`, `-vv`, `-d`, and `-dd` are accepted and cumulative. At debug level one, failed capture loading first reports these attempted library names in this order:

```text
[-] pcap: failed to load: libpcap.so
[-] pcap: failed to load: libpcap.A.dylib
[-] pcap: failed to load: libpcap.dylib
[-] pcap: failed to load: libpcap.so.1
[-] pcap: failed to load: libpcap.so.0.9.5
[-] pcap: failed to load: libpcap.so.0.9.4
[-] pcap: failed to load: libpcap.so.0.8
```

The ordinary two-line capture warning follows, then detailed missing-API lines beginning with `pcap: pcap_close: failed`. At debug level two or higher, including either `-dd` or repeated `-d -d`, standard error additionally ends with `pfring: error: dlopen('libpfring.so'): No such file or directory`. Three `-d` flags have the same PF_RING side effect. `--debug-tcp` is also an accepted value-less debugging flag. It is not represented by a configuration line: `--debug-tcp --echo` returns 0 and prints the ordinary configuration and capture-library warning without a `debug-tcp` line. Bare `--debug-tcp` returns 1, writes the exact short usage document from Spec 5 to standard output, and writes only the capture-library warning to standard error. Settings that only affect live packet transmission may remain inert in offline mode, but their validation and echo representation are still required.

## Spec 21

`--banners` enables banner collection and echoes `banners = true`; `--nobanners` removes that setting, with the later option winning. `--rawudp` also enables banner collection and echoes both `banners = true` and `rawudp = true`, in that order. Thus `--echo --rawudp -pU:161 10.0.0.1` emits those two lines and `ports = U:161`.

`--capture TYPE`, `--nocapture TYPE`, and the hyphenated alias `--no-capture TYPE` support `servername`, `heartbleed`, `ticketbleed`, `cert`, and `html`. Capture state is serialized in two compatibility passes. Capturing `servername` removes both default no-capture entries and emits no `capture = servername` line. Capturing any one of `heartbleed`, `ticketbleed`, or `html` retains the default in each pass and emits the following four-line sequence after `banners = true`, with `TYPE` replaced by the selected type:

```text
nocapture = servername
capture = TYPE
nocapture = servername
capture = TYPE
```

Thus a single heartbleed capture uses `capture = heartbleed` in both `TYPE` positions; ticketbleed and HTML behave analogously. Multiple active types retain their order within each pass. For example, capturing `servername`, `cert`, `heartbleed`, and `ticketbleed` emits exactly `capture = heartbleed`, `capture = ticketbleed`, `capture = heartbleed`, `capture = ticketbleed`, with no servername, cert, or default no-capture lines. Capturing servername and heartbleed emits only two `capture = heartbleed` lines. Later capture/no-capture state wins for a type. Consequently, capture-heartbleed followed by no-capture-heartbleed emits only the two default `nocapture = servername` lines, while the reverse order emits the four-line sequence above. An unsupported type is diagnosed as `FAIL: <type>: unknown capture type` (or `unknown nocapture type`).

Capturing `cert` is accepted but does not emit a `capture = cert` line. Thus `--banners --capture cert --echo -p443` returns 0 and its capture-related echo consists only of `banners = true` followed by the two default `nocapture = servername` lines. An invalid capture type remains nonfatal when `--echo` is present: `--banners --capture invalid --echo` returns 0, prints the normal banner configuration, and writes `FAIL: invalid: unknown capture type` before the capture-library warning.

`time` is not a supported capture type. `--capture time --echo` nevertheless returns 0 and prints the ordinary configuration with both default `nocapture = servername` lines; it writes `FAIL: time: unknown capture type` before the capture-library warning.

Recognize `--heartbleed`, `--ticketbleed`, and `--vuln` names `heartbleed`, `ticketbleed`, `poodle`, `sslv3`, and `ntp-monlist`; they enable the corresponding banner/vulnerability state. The standalone `--poodle` flag is not recognized: in `--poodle --echo`, it consumes `--echo` as its attempted value, returns 1 without an echo or capture initialization, and writes exactly `CONF: unknown config option: poodle=--echo`. In echo mode, each of `--heartbleed`, `--ticketbleed`, `--vuln heartbleed`, `--vuln ticketbleed`, `--vuln poodle`, and `--vuln sslv3` returns 0 and emits exactly this banner/capture sequence:

```text
banners = true
nocapture = cert
nocapture = servername
nocapture = cert
nocapture = servername
```

These vulnerability forms emit no separate `capture = ...` or `vuln = ...` line. Combining multiple checks such as `--vuln heartbleed --vuln ticketbleed --vuln poodle` still emits the four-line sequence only once. `--vuln ntp-monlist` itself adds no `banners` line to echo output; otherwise the ordinary configuration remains unchanged. An invalid name terminates before capture initialization, returns 1, produces no configuration echo, and writes exactly:

```text
FAIL: vuln check '<name>' does not exist
  hint: use '--vuln list' to list available scripts
```

## Spec 22

Support HTTP probe customization through `--http-method`, `--http-version`, `--http-url`, `--http-host`, `--http-user-agent`, `--http-cookie`, `--http-payload`, `--http-header`, and `--http-field`. Preserve case and arbitrary UTF-8/free-form content in these supported values: examples accepted verbatim include host `[::1]:8080`, user agent `Agent/Ünicode`, cookie `a=b; c=d`, and an HTTP payload containing an embedded newline. Normalize an unindexed HTTP header by removing optional space after its first colon, so `X-Custom: Value` echoes `http-header = X-Custom:Value`. `--http-field Empty:` is an alias that echoes `http-header = Empty:` rather than an `http-field` line.

`--http-path`, `--http-query`, and `--http-fragment` are not recognized customization options. They are fatal before capture initialization and produce no configuration echo. The tested forms diagnose exactly `CONF: unknown config option: http-path=/x`, `CONF: unknown config option: http-query=a=b=c`, and `CONF: unknown config option: http-fragment=`, respectively. Consequently, combining otherwise valid HTTP fields with `--http-query a=b=c` returns 1 and emits no partial echo.

Bracketed HTTP spellings have idiosyncratic canonicalization rather than retaining their brackets. The combined invocation `--http-header[2] 'X-Two: Value' --http-field[10] X-Ten:V --echo` returns 0 and emits, in order:

```text
http-header = 2:X-Two: Value
http-header = X-Ten:V
```

A bracket may also contain the header name instead of a numeric index. `--echo --http-header[X-Test] testvalue -p80 10.0.0.1` returns 0 and canonicalizes the pair to `http-header = X-Test:testvalue`; it is not an unknown configuration key.

`--hello-string[INDEX] VALUE` stores a raw hello string. The unindexed command-line form `--hello-string VALUE` and configuration key `hello-string = VALUE` store the complete value at index zero and echo it as `hello-string[0] = VALUE`. Repeated hello strings are additive rather than last-one-wins: preserve every entry, including when a hello file and a literal target the same index. Echo entries newest first, without sorting by numeric index; entries repeated at the same index are therefore also newest first. For example, a literal at index 80 followed by a hello file at index 80 emits the file-derived entry first and retains the earlier literal entry immediately afterward. Hello-string lines appear after `banners = true` when enabled and before the default `nocapture` lines. A leading bracket expression in an unindexed value is not parsed as an index: `--hello-string [80]R0VU...` echoes the complete bracket-prefixed value at `hello-string[0]`. Echo raw CR and LF bytes in hello-string values; do not convert them to the two-character spellings `\r` and `\n`. Thus values supplied at indices 80, 443, and then -1 echo in the index order 0, 443, 80, with the index-80 line physically continued by its embedded newlines. A negative command-line index is treated as index zero. The `--hello-string[PORT]=BASE64` form used in configurations preserves its value verbatim without validating the base64.

`--hello PROTOCOL` is also a value-taking option. It consumes the following token and echoes it unchanged, for example `--hello ssl` produces `hello = ssl` and returns 0 in echo mode.

`--hello-file[PORT]=FILE` reads the entire nonempty binary file and echoes its standard base64 encoding as the corresponding hello string. The bare two-token form `--hello-file VALUE` consumes `VALUE` as a literal filename; it does not extract a port from a value such as `[80]/tmp/hello.txt`. For both the indexed and bare forms, a missing file during `--echo` returns 0, prints the normal configuration echo, and writes these lines to standard error before the capture-library warning:

```text
[-] [FAILED] --hello-file
[-] <literal-path>: No such file or directory
```

An empty file is likewise nonfatal during `--echo`: it returns 0, prints the normal configuration, and writes `[FAILED] could not read hello file`, followed by `<path>: No such file or directory`, before the capture-library warning. A port index above 65535 is fatal. There is no separated `--hello-file PORT FILE` form. For `--hello-file 443 FILE --echo`, `443` is consumed as the literal filename, causing `[-] [FAILED] --hello-file` and `[-] 443: No such file or directory`; `FILE` is then parsed as another command-line token and the invocation returns 1 without a configuration echo. A zero hello timeout is accepted but omitted when it has no effective nondefault value.

## Spec 23

`--pcap-payloads FILE` and `--nmap-payloads FILE` name external UDP payload databases and echo their paths. A missing pcap-payload file in echo mode reports `payloads: can't read from file '<path>'` plus the system error, but echo may return 0. A missing nmap-payload file reports `FAIL: --nmap-payloads` plus the path error.

A classic little-endian PCAP is a valid `--pcap-payloads` input. Its 24-byte global header has magic `0xa1b2c3d4`, version 2.4, snap length 65535, and Ethernet link type 1. Each packet then has a 16-byte record header containing seconds, microseconds, captured length, and original length, followed by that many captured frame bytes. The reader processes more than one record rather than requiring a single-packet file. As a concrete accepted multi-record case, a file named `multi_packet_valid.pcap` containing two Ethernet/IPv4/TCP frames, each with captured length equal to original length, is accepted even though TCP frames contribute no UDP payload. `--pcap-payloads <that-path> --echo` returns 0, echoes `pcap-payloads = <that-path>`, writes no payload-file diagnostic, and then writes the ordinary capture-library warning. Thus irrelevant non-UDP records are skipped without invalidating the capture, including when there are multiple such records.

The Nmap UDP payload grammar consists of entries beginning with `udp` and a `PORTSPEC`, followed by zero or more quoted C-style byte strings and then an optional `source PORT`. The initial `udp`, `PORTSPEC`, and quoted strings are whitespace-separated rather than line-bound: each may occupy a separate physical line, while the compact `udp PORTSPEC` form is also accepted. The `source` keyword may begin on a later line after the payload strings, but its `PORT` is line-bound: a newline immediately after `source` produces `<path>:<source-line>: expected source port` rather than taking the number on the following line. Thus a line `source 0` is the compact form, whereas the two physical lines `source\n65535\n` produce `<path>:6: expected source port` when `source` is on line 6. A valid `source PORT` terminates that entry: a quoted string afterward is parsed as the attempted start of another entry and receives the `expected "udp"` diagnostic. PORTSPEC accepts singles, lists, and ranges including port 0 and port 65535. Source ports 0 and 65535 are accepted when present on the same line as `source`. An entry containing only `udp` and its port specification, with no quoted payload, is valid.

Ignore blank lines and `#`, `;`, or `//` comments. Decode `\xHH`, one-to-three-digit octal escapes, and `\a`, `\b`, `\f`, `\n`, `\r`, `\t`, `\v`, `\\`, and `\"`; concatenate strings across lines and accept empty strings. A quoted payload ending in an incomplete `\x` escape remains nonfatal and the file still echoes successfully. Handle oversized payloads safely. A wrong leading keyword produces `<path>:<line>: syntax error, expected "udp".`; malformed source syntax produces `<path>:<line>: expected source port`. Once the file has been opened, payload syntax, source-port, missing-payload, and bounded oversized-payload outcomes are nonfatal under `--echo`: the command returns 0 and prints the ordinary configuration including `nmap-payloads = <path>`, with any parser diagnostic on standard error before the capture-library warning. This also applies to a source port outside the normal port range.

## Spec 24

`--nmap-service-probes FILE` parses an Nmap-service-probe text database, echoes `nmap-service-probes = <path>`, and writes a normalized representation of parsed probes to standard output before the ordinary configuration echo. Support:

- `Exclude` port specifications;
- `Probe TCP|UDP NAME q<delimiter>PAYLOAD<delimiter>` with arbitrary delimiter;
- `ports`, `sslports`, `rarity`, `totalwaitms`, `tcpwrappedms`, and `fallback` directives;
- `match` and `softmatch` expressions with version fields `p`, `v`, `i`, `h`, `o`, `d`/`e`, and `cpe`.

Only allow `Exclude` before the first probe. Normalize query payload delimiters to `|`, preserve backslash escapes, and normalize both `match` and `softmatch` output to `match`. Match expressions use `/` as their canonical pattern delimiter whenever the pattern itself contains no slash, even when `|` was supplied. If the pattern contains `/`, retain a nonconflicting delimiter such as `|`; for example, `m|^HTTP/1|` remains pipe-delimited. Every emitted match line has exactly one trailing ASCII space after its final version field. The device-type version field is canonically emitted as `e/.../`, including when supplied as `d/.../`. For example, these normalized lines are exact, including their final spaces:

```text
match http m|^HTTP/1| p/HTTP/ 
match dns m/^\0\0/ p/DNS/ 
match test1 m/^test/i p/CaseInsensitive/ 
```

This delimiter rule also applies with regex flags, hex escapes, CPE suffixes, every version-information field, and self-test loading. For example, `m|^.{2}[\x81\x85]|`, `m|^test| cpe:/a:vendor:product/a`, and `m|^SSH-|i` normalize respectively to `m/^.{2}[\x81\x85]/`, `m/^test/ cpe:/a:vendor:product/a`, and `m/^SSH-/i`.

The `cpe` version field accepts the Nmap part suffix immediately after its closing delimiter. In particular, `cpe:/a:vendor:product/a` is valid and is preserved exactly in the normalized match line; the trailing `a` is not an unexpected character.

Port specifications are canonicalized by protocol and range rules. A UDP probe's unprefixed port list has the reference's compatibility prefix, so `ports 53` prints `ports T:53`. An exclusion supplied as `Exclude T:53,9100,U:30000-40000` is emitted with exactly that spelling: the unprefixed `9100` is not moved under `T:`. A missing range end extends through 65535, so `ports 80-` is valid and prints `ports 80-65535`.

Service-probe parser diagnostics are nonfatal when `--echo` is present. Missing protocol/name/query fields, an empty match service, unterminated match strings, late `Exclude`, directives before a probe, unknown commands, invalid regex options, and malformed match version fields all return 0 and retain `nmap-service-probes = <path>` in the ordinary echo. Any successfully parsed prefix may be normalized before the ordinary echo. Located diagnostics precede the capture-library warning and identify file basename/path, one-based line, and column. For the following exact file contents, the parser behavior is:

- `Probe\n`, `Probe TCP\n`, and `Probe TCP Name\n` report `line too short` at columns 5, 6, and 14 respectively;
- `Probe TCP Name q|unterminated\n` reports `missing end delimiter '|'` at column 29;
- `ports 80\n` reports `'directive only valid after a 'Probe'` at column 6;
- `Unknown thing\n` reports `unknown type: 'Unknown '` at column 8;
- after a valid probe, `match x m|x| p/missing\n` reports `missing ending delimiter '/'` at its line's column 22.

The numeric directive `rarity 99` is not rejected. After `Probe TCP A q||`, it is accepted, preserved as `rarity 99` in normalized output, and produces no rarity-specific diagnostic. Two `Exclude` directives before the first probe are also accepted rather than diagnosed as duplicates: the file `Exclude 1\nExclude 2\n` normalizes to `Exclude T:1-2` and produces no exclusion-specific diagnostic. An `Exclude` after a probe remains a located nonfatal error and reports `'Exclude' directive only valid before any 'Probe'` at column 8.

The following additional malformed forms have exact nonfatal located diagnostics under `--echo`:

- an unknown probe protocol in `Probe INVALID Test q||` reports `:1:6: unknown protocol`;
- `match http mHTTP/1.0` reports `:2:20: missing ending delimiter 'H'`;
- `match test m|^test|x p/Invalid/` reports `:3:19: unknown regex pattern option 'x'`;
- `Probe TCP Test q|\q|` first echoes that source line as `<path>:1: Probe TCP Test q|\q|`, then reports `:1:18: unexpected escape character 'q'`;
- `Probe TCP Test q|\xgg|` reports `:1:19: expected hex, found 'g|'`, while `Probe TCP Test q|\x1|` reports `:1:19: line too short`;
- `Probe TCP Test q|test\|` reports `:1:22: premature end of field`;
- after a probe, `rarity abc` reports `:2:7: unexpected character 'a'`;
- after a valid probe and ports directive, `match  m|test|  p/Product/` recovers as `:3:16: expected 'm', found 'p'` rather than reporting an empty service name.

Malformed match-version fields remain nonfatal under `--echo`. An unterminated `p/Product` field reports `missing ending delimiter '/'`; an unknown `z/value/` field reports `versioninfo unknown identifier 'z'`; and `match test m|^test| p/Product/x` reports `:3:30: unexpected character after delimiter '/'`. Each returns 0, retains the service-probe path in echo output, and then emits the capture-library warning. Long probe names are accepted and preserved rather than rejected at a 255-byte boundary; a 500-character ASCII name is valid. Parsing must remain bounded for very long lines and many probes.

If the named service-probe file is missing in echo mode, write `<path>: No such file or directory` to standard error, then the capture-library warning, but return 0 and still print the ordinary configuration echo containing `nmap-service-probes = <path>`.

## Spec 25

Output selection aliases are:

- `-oX` XML, `-oJ` JSON, `-oD` newline-delimited JSON, `-oG` grepable, `-oB` binary, `-oL` list, `-oU` unicornscan, and `-oH` host-only;
- `-oR` Redis destination;
- `--output-format FORMAT` plus `--output-file FILE` or `--output-filename FILE`.

Format names are case-insensitive. Also recognize `redis` and `certs`. The last complete output specification wins and echo orders `output-filename` before `output-format`. Filename `-` and `/dev/stdout` direct data to standard output and must not create a file literally named `-`. An empty filename or a filename consisting only of spaces is treated as absent. In an ordinary invocation such as `--output-format xml --output-filename ''` or the same invocation with a spaces-only filename, return 1, write the exact short usage document from Spec 5 to standard output, and write only the capture-library warning to standard error; do not emit an abbreviated usage line or `FAIL: no ports were specified`. A nonexistent parent or directory-as-file reports the exact line `out: could not open file for writing` followed by the path's operating-system error; it returns 1. A conversion containing no emitted records produces an empty output stream/file.

The long format value `hostonly` is accepted and echoes as `output-format = hostonly`; it selects the same host-only output as `-oH`. The `-oH` shortcut also uses this exact canonical echo spelling, never `host-only`.

If a nonempty filename is supplied without a format, default to XML. Invalid long format names are nonfatal in echo mode: return 0, omit `output-format` from the configuration, and write these lines before the capture-library warning, substituting the invalid value on the first line:

```text
FAIL: unknown output-format: <value>
  hint: 'binary', 'xml', 'grepable', ...
```

This applies to the tested invalid names `cert` and `null`; `certs` remains the valid certificate-output name. Reject the unsupported Nmap shortcuts `-oA`, `-oN`, and `-oS` with a diagnostic containing `unsupported`. `--ndjson-status` is accepted and echoes `ndjson-status = true`; deprecated `--json-status` merely warns `json-status not supported` and `use --status-ndjson` while echo continues successfully. `--redis-password` is not recognized and is reported as `unknown config option: redis-password=<value>`.

A trailing space is significant while diagnosing a long format. Specifically, `--echo --output-format 'xml ' --output-file /tmp/test.xml` returns 0 and writes exactly these two format-specific diagnostic lines before the capture-library warning:

```text
FAIL: unknown output-format: xml 
  hint: 'binary', 'xml', 'grepable', ...
```

Despite that diagnostic, this compatibility case echoes `output-filename = /tmp/test.xml` and `output-format = xml`.

`--append-output` echoes `output-append = true`; when used, append complete format documents rather than merging them. `--stylesheet FILE` and `--webxml` affect the same XML-presentation scalar, so the later option wins. Thus `--stylesheet sheet.xsl --webxml --echo` emits `stylesheet = http://nmap.org/svn/docs/nmap.xsl`, whereas the reverse order emits `stylesheet = sheet.xsl`. `--no-stylesheet` is a recognized XML-presentation control. `--webxml` canonically echoes the built-in URL, not `webxml = true`. Rotation options use Spec 17.

`--redis IPv4[:PORT]` and `-oR IPv4[:PORT]` select a Redis destination; `-oR`'s following token is the Redis address, not an output filename. Port 6379 is the default and the long form echoes `redis = <IPv4> <port>`. A pathname, hostname, or IPv6 address is rejected. For example, `-oR /tmp/test.redis`, `-oR localhost`, and `-oR ::1` each return 1, write no standard output or capture-library warning, and write exactly this one line after substituting the supplied value:

```text
FAIL:  bad redis IP address: <value>
```

Redis record output contains appropriate Redis commands such as `RPUSH`/`SADD`. Cert output must be creatable even if no certificate record is present.

## Spec 26

`--show open`, `--show closed`, and `--show all` select status records. `--output-status` accepts the same three values as an alias: `--output-status open`, `--output-status closed`, and `--output-status all` each return 0 in echo mode and are omitted from canonical echo. `--noshow open`, `--noshow closed`, and `--noshow host` suppress their corresponding classes; `--noshow all` is also accepted and suppresses both open and closed status records. In echo mode `--noshow all` returns 0 without printing a corresponding setting. `--open` and `--open-only` select open results. Invalid show/noshow values are errors. In particular, `--output-noshow unknown` returns 1, writes no standard output or capture-library warning, and writes exactly `FAIL: unknown 'noshow' spec: unknown\n` to standard error. By default, closed records are suppressed and open and banner records are emitted. Configured address and port selections filter converted records. Protocol-qualified port selection has a read-scan compatibility exception: `--readscan <mixed-scan> --show all --ports U:53 -oL <output>` does not retain a matching protocol-17 port-53 status record and creates an exactly empty output file, while returning 0 and reporting the ordinary capture warning followed by `[+] --readscan <mixed-scan>`.

With `--readscan` and no explicit output format, emit no document header. An open record prints:

```text
Discovered open port <port>/<protocol> on <address>
```

A banner record includes the bracketed application name and prints:

```text
Banner on port <port>/<protocol> on <address>: [<application-name>] <escaped-banner>
```

Before its newline, each console record is right-padded with ASCII spaces to a minimum width of 79 characters; records already longer than 79 characters are not truncated. Consequently the spaces occur after the address on status lines and after the payload on shorter banner lines. For example, the unpadded text `Discovered open port 9/err on 192.0.2.1` has forty trailing spaces before its newline, and `Discovered open port 12/tcp on 192.0.2.12` has thirty-eight. Preserve record order and do not deduplicate identical records. Known IP protocols are TCP 6, UDP 17, ICMP 1, SCTP 132, and ARP 0 in ARP-style records; unknown protocols are rendered `err`. Status reason bytes are TCP-flag-like: at minimum 1 maps to `fin`, 2 to `syn`, and banner reason is `response`.

## Spec 27

`--readscan FILE` reads the native binary format and implicitly enables banner collection; with `--echo`, this is represented by `banners = true`. It reports `[+] --readscan <path>` on standard error when it reads the file. The file starts with exactly 99 header bytes whose ASCII version prefix is `masscan/1.1`. Either a NUL byte or a newline may immediately follow that prefix: an immediately NUL-padded `masscan/1.1` header is valid, as is the newline form optionally followed by `s:<decimal>\n`; the remainder of the 99 bytes is NUL padding. Accept the compatible header spelling `masscan/1.1.2`. The reader's acceptance of both separators does not make writer choice variable: binary output produced by the executable always begins `masscan/1.1\ns:<first-selected-record-timestamp>\n`, then uses NUL padding through byte 99. In particular, bytes 11 and 12 are newline and lowercase `s`; an input whose header says `s:1234567890` but whose first selected record is timestamp `1640000000` is rewritten with `s:1640000000`. Produced files end with a separate 99-byte NUL-padded `masscan/1.1` footer, but the reader also accepts EOF immediately after the final complete record when this footer is absent. A footerless file ending at a complete record returns 0 rather than reporting `file too short` or `file corrupt`; this remains true for default standard-output conversion and for XML, JSON, NDJSON, grepable, list, unicornscan, and cert output, including verbosity, show/open, address/port, stylesheet, append, and repeated-file invocations.

There is also a bare echo compatibility form that does not require `FILE`. `--readscan --echo` returns 0 and prints the ordinary configuration with these two additional lines, in this order before the default `nocapture` lines:

```text
banners = true
rawudp = true
```

It does not try to open a file named `--echo`; standard error contains only the capture-library warning.

After the header are records encoded as a type and length, each an unsigned big-endian base-128 variable-length integer (shift accumulated value left seven and add each low seven-bit group; high bit means continuation), followed by exactly `length` bytes. A footer, when present, follows the records. Thus `80 01` decodes as 1 and `80 0c` as 12.

Decode these modern records, with all integers big-endian:

- type 6 IPv4 status, normally 13 bytes: timestamp u32, IPv4 u32, IP protocol u8, port u16, reason u8, TTL u8; state open. A 19-byte type-6 ARP record is also valid: it has the same 13-byte fields with protocol 0 followed by six MAC-address bytes. Consume and ignore those MAC bytes for list conversion; the status is emitted normally as protocol `arp`;
- type 7, same layout, state closed;
- type 9 IPv4 banner: timestamp u32, IPv4 u32, IP protocol u8, port u16, application protocol u16, TTL u8, then banner bytes;
- types 10 and 11 IPv6 open/closed, 26 bytes: timestamp u32, IP protocol u8, port u16, reason u8, TTL u8, IP-version byte 6, then the 16 address bytes;
- type 13 IPv6 banner: the corresponding timestamp, IP protocol, port, application protocol, TTL, version 6, address, then banner bytes.

Also accept legacy types: type 1/2 IPv4 open/closed records of timestamp, address, port, reason, TTL with implicit TCP; type 3 legacy IPv4 banners; and type 5 IPv4 banners containing an explicit IP protocol. For legacy banner types 3 and 5, compatibility decoding does not consume the byte following the application-protocol field as TTL; that byte is the first payload byte. Thus a type-3 fixed prefix ending in byte 48 followed by `legacy-ssh` produces banner `0legacy-ssh`, and a type-5 prefix ending in byte 47 followed by `legacy-udp` produces `/legacy-udp`.

A record whose type byte is ASCII `m` is a file-header metadata record; skip its declared payload silently and continue at the following record. Legacy banner type 4 uses the type-5 fixed layout inside its declared body: timestamp u32, IPv4 u32, IP protocol u8, port u16, and application protocol u16. It then performs one historical extra-byte read beyond the declared length and appends that byte to the banner payload. When the byte is present, conversion succeeds and emits one banner host; for example, a fixed type-4 body followed by byte `X` converts to an HTTP banner `X`. If that extra-byte read reaches EOF, return 1 and report `[-] read() error` rather than crashing.

## Spec 28

Binary output (`-oB`) creates the 99-byte header and footer described above and copies every selected source record's encoded type, length, and payload byte-for-byte between them. This permits a binary read/write round trip without altering timestamps, duplicates, unknown banner bytes, or record order; default closed filtering still applies.

Malformed binary inputs must be handled safely, but their parse diagnostics do not make the read-scan command fail: the malformed cases in this paragraph return 0 and emit no converted records. Both an empty file and a header-short file report `[-] <path>: Success`; after capture initialization, the short-header diagnostic follows `[+] --readscan <path>`. An unrecognized header reports `unknown file format (expeced "masscan/1.1")` (including the typo). A record with a declared body that is truncated at EOF, and a type-6 record whose declared length is shorter than its fixed fields, stop conversion without reading beyond the file and return 0. Unknown record type 99 reports `[-] file corrupt: unknown type 99`; a declared record larger than 1,048,576 bytes reports `[-] file corrupt`; an IPv6 record whose version byte is not 6 reports `[-] corrupt record`. Each still returns 0. Never read beyond the declared file data or allocate an unbounded record. Missing read-scan files report `[-] FAIL: --readscan` and the path error; compatibility behavior also returns 0 after this file error. The legacy type-4 EOF exception in Spec 27 remains the explicitly nonzero malformed-input case.

## Spec 29

List output begins `#masscan\n`, writes one status line as `<state> <protocol> <port> <address> <timestamp>\n`, and ends `# end\n`. For example:

```text
#masscan
open tcp 80 192.168.1.100 1640000000
open tcp 443 192.168.1.100 1640000001
open tcp 22 192.168.1.101 1640000002
# end
```

Host-only output is simply one address per selected record, including duplicates and banner records, without a header or footer.

Unicornscan output has the same `#masscan`/`# end` framing. A TCP status line uses this exact field-width layout, where `\t` is one tab, `%16s` right-aligns the service in 16 columns, `%5d` right-aligns the port in five columns, and `%-3d` left-aligns the TTL in three columns:

```text
TCP <state>\t%16s[%5d]\t\tfrom <address>  ttl %-3d
```

There is no space between the service field and `[`, there are two spaces before `ttl`, and the three-column TTL field leaves a trailing ASCII space after two-digit values. Thus the port-443 line for address `10.10.10.10` ends in `ttl 56 ` before its newline. Port 80 uses `http`, 443 `https`, and 22 `ssh`; a three-record fixture produces service/port fields `            http[   80]`, `           https[  443]`, and `             ssh[   22]`. Banner records are not printed in this format. Non-TCP status records may use the grepable-style fallback.

## Spec 30

Grepable output starts with:

```text
# Masscan 1.3.9-integration scan initiated <ctime-text>
# Ports scanned: TCP(0;) UDP(0;) SCTP(0;) PROTOCOLS(0;)
```

and ends `# Masscan done at <ctime-text>`. A status record is one line:

```text
Timestamp: <timestamp>\tHost: <address> ()\tPorts: <port>/<state>/<protocol>//<service>//
```

Use common service labels including TCP 22 `ssh`, TCP 80 `http`, TCP 443 `https`, UDP 53 `domain`, UDP 161 `snmp`, SCTP `sctp`, and ICMP `icmp`. A banner line contains `Host:`, `Port:`, and `Banner:` fields. Escape nonprintable banner bytes as lowercase `\xhh`; retain printable text. Empty banner payloads need not produce a line. Do not combine multiple records for the same host.

For read-scan conversion, the initiation `<ctime-text>` is the UTC `ctime` rendering of the first decoded record's timestamp, not the conversion clock and not an `s:` timestamp stored in the binary header. A first record timestamp of `1640000000` therefore produces exactly `Mon Dec 20 11:33:20 2021`, even if the header contains a different `s:` value. The closing `done at` time remains the conversion clock.

## Spec 31

JSON output for nonempty data is one valid top-level array, with one object for each selected record in order. Commas separate objects and there is no trailing comma. Status objects have this semantic shape (spacing is not significant):

```json
{"ip":"192.0.2.1","timestamp":"1640000000","ports":[{"port":80,"proto":"tcp","status":"open","reason":"fin","ttl":64}]}
```

Timestamp is a decimal string, port and TTL are numbers. A banner object replaces status fields with `"service":{"name":"<application-name>","banner":"<payload>"}`. Encode quotation marks, backslashes, controls, CR/LF, and arbitrary bytes so the JSON parses and round-trips the textual banner representation.

NDJSON (`ndjson`) writes exactly one complete JSON object per line. Its status records contain top-level `ip`, timestamp, port, protocol, `rec_type:"status"`, and a `data` object holding status, reason, and TTL. A banner record uses `rec_type:"banner"` and puts two sibling keys in `data`: `service_name` is the application name and `banner` is the payload. For example, the relevant portion is `"data":{"service_name":"http","banner":"..."}`; there is no nested `data.service.name` object. Preserve input ordering and duplicates in both JSON formats.

## Spec 32

XML output for nonempty results is a complete Masscan-style Nmap XML document. It begins with the XML declaration and `<!-- masscan v1.0 scan -->`, then an `nmaprun` element whose opening line has exactly two ASCII spaces between the closing quote of `version="1.0-BETA"` and `xmloutputversion`:

```text
<nmaprun scanner="masscan" start="TIMESTAMP" version="1.0-BETA"  xmloutputversion="1.03">
```

It is followed by `<scaninfo type="syn" protocol="tcp" />`. Use CRLF-compatible line endings.

Each status is its own host element:

```xml
<host endtime="TIMESTAMP"><address addr="ADDRESS" addrtype="ipv4"/><ports><port protocol="PROTO" portid="PORT"><state state="STATE" reason="REASON" reason_ttl="TTL"/></port></ports></host>
```

A banner host has an open `state` with reason `response`, followed by `<service name="NAME" banner="PAYLOAD"></service>`. The compatibility writer labels every address `addrtype="ipv4"`, including textual IPv6 addresses such as `2001:db8::1`. Banner payload bytes that would be XML metacharacters are rendered with the same lowercase `\xhh` byte escaping as nonprintables rather than as XML entities: the payload `<tag a="&">` followed by byte `01` is emitted as `banner="\x3ctag a=\x22\x26\x22\x3e\x01"`. End with `runstats`, a `finished` element containing numeric and formatted run time plus `elapsed="0"`, and then close `nmaprun`. The `hosts` counters do not count every emitted host element. For the six-record fixture containing two open TCP statuses for `192.0.2.1`, one open UDP status for `192.0.2.2`, one closed TCP status for `192.0.2.3`, and two banners on other addresses, XML still emits all six host elements but ends with exactly `<hosts up="2" down="1" total="3" />`. Thus the duplicate open address contributes only one to `up`, the closed status contributes to `down`, and banners contribute to neither counter. Duplicate records nevertheless remain duplicate host elements.

## Spec 33

Banner application identifiers must map to stable names where known, including ID 4 to `http` and ID 2 to `ssh`; an unknown numeric ID is rendered as `(<number>)`. Do not reinterpret or truncate the payload beyond removing fields belonging to the relevant binary record layout. Preserve printable UTF-8 where the destination format permits it and use that format's escaping for arbitrary bytes.

Across console, list, grepable, JSON, NDJSON, XML, host-only, and binary conversion, process records in file order and preserve duplicate status and banner records. Filtering is selection, not aggregation. Every record retains its own timestamp, address text, protocol, port, state/reason/TTL, application protocol, and payload; XML's deliberately incorrect `addrtype="ipv4"` label is the exception described in Spec 32. This behavior also applies when the same address and port appear multiple times.

## Spec 34

`-sL` performs a list scan: print target addresses only, one canonical address per line, without headers or ports. Order is a deterministic BlackRock-style permutation controlled by seed. For seed 12345, a four-address IPv4 `/30` is ordered:

```text
10.0.0.0
10.0.0.3
10.0.0.1
10.0.0.2
```

and IPv6 `2001:db8::/126` uses the analogous low-bit order `::`, `::3`, `::1`, `::2`. Different seeds may produce different deterministic permutations. Exclusions and shards apply before/while enumerating.

`--iflist` prints available interface/route information for diagnostics and terminates promptly even when capture support is unavailable. In the evaluation environment where libpcap is unavailable, it returns 0 while reporting the capture-library failure and `libpcap not loaded` on standard error. It must be recognized rather than treated as an unknown option. Offline scans validate inputs and create outputs without transmitting packets.

## Spec 35

`--banner1 PCAP` parses a classic-PCAP-looking file. Successful validation has the unusual status 1: a valid one-packet Ethernet/IPv4/TCP PCAP returns 1 with both output streams empty, as do valid multi-packet files (including two- and three-packet fixtures). This includes big-endian input. A concrete accepted file named `bigendian_valid.pcap` is 94 bytes: its 24-byte global header uses bytes `a1 b2 c3 d4`, big-endian version 2.4, zero timezone and timestamp accuracy, snap length 65535, and Ethernet link type 1; its big-endian packet header has seconds 1, microseconds 2, and captured and original lengths both 54; its frame consists of a 14-byte Ethernet header (twelve zero bytes and EtherType `08 00`), a 20-byte IPv4 header for TCP, and a 20-byte TCP header. `--banner1 <that-path>` returns 1 with exactly empty standard output and standard error. Successful paths do not initialize libpcap or emit the capture warning.

The mode also has several rejection-path compatibility behaviors. An empty file containing a complete version-2.4 global header is not silently accepted, even with little- or big-endian PCAP magic and link type 1, 119, `0x69`, or `0x7f`. Each of those eight cases returns 1, writes nothing to standard output, does not initialize libpcap, and writes exactly these two lines to standard error even though the file exists:

```text
<path>: No such file or directory
<path>: can't open capture file
```

A missing file returns 1 and writes:

```text
<path>: could not open capture file
<path>: No such file or directory
<path>: can't open capture file
```

A truncated global header reports `<path>: file too short` and then `can't open capture file`. Global-header validation has the following exact compatibility diagnostics, all on standard error. An invalid header filled with byte `a3` reports all three decoded fields before the final failure:

```text
<path>: unknown byte-order in cap file
<path>: unknown version 41891.41891
<path>: unknown cap file linktype = 41891 (expected Ethernet or wifi)
<path>: can't open capture file
```

A version-3.5 header reports:

```text
<path>: unknown version 3.5
<path>: No such file or directory
<path>: can't open capture file
```

The middle operating-system-error line is intentional even though the file was opened. A version-2.4 header with link type 999 reports:

```text
<path>: unknown cap file linktype = 999 (expected Ethernet or wifi)
<path>: can't open capture file
```

For packet entries, a packet body shorter than its captured-length claim returns 1 and writes only `<path>: premature end of file\n` to standard error. A complete packet declaring and supplying 10,001 captured bytes with original length 10,001 is a separate compatibility case: it returns 1 with both output streams empty, so there is no capture-length corruption diagnostic. For the tested 100-byte malformed-packet cases whose packet data starts at offset 40 and ends at offset 100 (invalid microseconds or original length smaller than captured length), return 1 and write:

```text
<path>:0: corruption found at 0x00000028 (40)
<path>:0: corruption found at 0x00000064 (100)
<path>: error at end of file
<path>: No such file or directory
```

and write `No valid packet found in chunk\n` to standard output. Do not append `can't open capture file` to either packet-level diagnostic form. Never read past EOF.

A little-endian link-type-1 file containing two complete short packets, `(usec=999999, captured=original=3, payload=abc)` and `(usec=0, captured=4, original=9, payload=defg)`, is also rejected regardless of their past/future timestamp seconds. It returns 1, writes `No valid packet found in chunk\n` to standard output, and writes the following four lines, where this fixture ends at byte 63:

```text
<path>:0: corruption found at 0x00000028 (40)
<path>:0: corruption found at 0x0000003f (63)
<path>: error at end of file
<path>: No such file or directory
```

## Spec 36

`--selftest`, `--self-test`, and `--regress` are aliases. They return 0, write no standard output, and write the capture-library warning followed by the exact success line:

```text
regression test: success!
```

No failure marker is present. If a service-probe file is also supplied, its normalized parse output precedes the self-test result.

`--benchmark` prints stable sections containing:

```text
=== benchmarking (64-bits) ===
-- blackrock-1 --
iterations/second = <positive>-million
-- blackrock-2 --
rounds = <configured-round-count>
iterations/second = <positive>-million
-- smack-1 --
bits/second = <positive>-million
```

Each of the three section-heading lines (`-- blackrock-1 -- `, `-- blackrock-2 -- `, and `-- smack-1 -- `) contains exactly one ASCII space between the final two hyphens and its newline. In particular, the trailing space in `-- blackrock-1 -- ` is required.

The default BlackRock round count is 14; explicit values including 0, 1, 4, 6, 8, 20, and 100 are reflected. Reported rates must be positive and coherent with elapsed work: the ordinary BlackRock figures are at least one million iterations/second, zero rounds exceeds 50 million, one round exceeds 10 million, twenty rounds exceeds 0.5 million, and low-round throughput is observably higher than high-round throughput without an implausible ratio. Smack throughput is at least 100 million bits/second. The benchmark must finish within a few seconds and may return 1 solely because capture initialization is unavailable.

## Spec 37

Lua scripting is unavailable in the evaluation environment. A nonempty `--script PATH` (or equivalent configuration) returns 1, including when `--echo` is also present. Standard error begins with:

```text
liblua: failed to load Lua shared library
    HINT: you must install Lua library
```

and then emits individual `liblua: <function>: failed` diagnostics for the required Lua API, including `lua_version`, `luaL_newstate`, `luaL_openlibs`, `luaL_loadfilex`, `lua_pcallk`, and `lua_close` (the full loader attempts at least 45 symbols). Standard output includes this case- and punctuation-sensitive two-line crash message, preceded by a backtrace heading and followed by backtrace data:

```text
 Segmentation fault: please post this backtrace to:
 https://github.com/robertdavidgraham/masscan/issues
```

The behavior is independent of whether the script path exists or what it contains and is consistent across repeated/concurrent runs. A configuration line with surrounding whitespace, such as `  script   =    test.lua   `, trims to the nonempty path and produces the same loader failure and crash message. Specifically, `--script nonexistent.lua --echo` enters the unavailable Lua loader, returns 1, emits the loader diagnostics and crash/backtrace output described above, and does not produce a configuration echo or a `script = nonexistent.lua` line.

An empty script value does not enter the Lua loader. This applies both to `--script ""` and to a configuration line `script =` (including whitespace that trims to empty). Either invocation returns 1, writes only the capture-library warning to standard error, and writes the exact short usage document from Spec 5 to standard output. It does not print the abbreviated `usage: masscan [options] -pPORT target` line or a no-ports failure.

## Spec 38

Recognize common Nmap options which Masscan cannot implement and issue stable explanatory diagnostics rather than treating them as targets. Required cases include:

- `-A`: `nmap(-A): unsupported: this tool only does SYN scan`;
- `-b`: `nmap(-b): FTP bounce scans will never be supported`;
- `-f`: `nmap(-f): fragmentation not yet supported`;
- `-F`: `nmap(-F): unsupported, no slow/fast mode`;
- `-O`, `-r`, `-R`, `-sC`, `-sA`, `-sF`, `-sI`, `-sM`, `-sN`, `-sn`, `-sV`, `-sW`, and `-sX`: identify the option and state that the corresponding OS detection, host randomization, DNS behavior, script/version discovery, ping-only, or non-SYN scan is unsupported;
- `-sT`: warn that a SYN scan is performed instead;
- `--host-timeout`, minimum/maximum host-group, parallelism, RTT-timeout, scan-delay, `--max-scan-delay`, `--ip-options`, `--log-errors`, `--scanflags`, `--send-ip`, `--dns-servers`, `--system-dns`, and `--traceroute`: when the option's required value is present (or the option is value-less), identify the supplied option and explain that the feature is unsupported or unnecessary; bare value-taking forms use the missing-parameter behavior specified below.

These compatibility errors return failure unless the option is explicitly documented elsewhere as accepted/ignored. In the `nmap(...)` diagnostic label, a short option retains its dash, while a long option is named without its two leading dashes. In particular, `--dns-servers 8.8.8.8` writes exactly `nmap(dns-servers): unsupported: DNS lookups too synchronous`, and `--host-timeout 10m` writes exactly `nmap(host-timeout): unsupported: this is an asynchronous tool, so no timeouts`. These four exact `-b`, `-f`, `--dns-servers`, and `--host-timeout` errors return 1, write no standard output, and terminate without the capture-library warning.

`-sT` is the exceptional warning-and-continue case. It writes these two lines before continuing with ordinary initialization and target validation:

```text
nmap(-sT): connect() is too synchronous for cool kids
WARNING: doing SYN scan (-sS) anyway, ignoring (-sT)
```

For example, `-sT -p80` subsequently emits the capture-library warning and the ordinary empty-target failure and returns 1.

The following additional invocations likewise return 1, write no standard output or capture-library warning, and write exactly the indicated single newline-terminated line to standard error:

```text
-O                              nmap(-O): unsupported, OS detection is too complex
-r                              nmap(-r): wat? randomization is our raison d'etre!! rethink prease
-R                              nmap(-R): unsupported. This code will never do DNS lookups.
-sA                             nmap(-sA): ACK scan not yet supported
-sC                             nmap(-sC): unsupported
-sF                             nmap(-sF): FIN scan not yet supported
-sI                             nmap(-sI): Zombie scans will never be supported
-sM                             nmap(-sM): Maimon scan not yet supported
-sN                             nmap(-sN): NULL scan not yet supported
-sn                             nmap(-sn): ping-sweeps not yet supported
-sV                             nmap(-sV): unlikely this will be supported
-sW                             nmap(-sW): Windows scan not yet supported
-sX                             nmap(-sX): Xmas scan not yet supported
--min-hostgroup 10              nmap(min-hostgroup): unsupported: we randomize all the groups!
--max-hostgroup 10              nmap(max-hostgroup): unsupported: we randomize all the groups!
--min-parallelism 10            nmap(min-parallelism): unsupported: we all the parallel!
--max-parallelism 10            nmap(max-parallelism): unsupported: we all the parallel!
--min-rtt-timeout 10            nmap(min-rtt-timeout): unsupported: we are asynchronous, so no timeouts, no RTT tracking!
--max-rtt-timeout 10            nmap(max-rtt-timeout): unsupported: we are asynchronous, so no timeouts, no RTT tracking!
--initial-rtt-timeout 10        nmap(initial-rtt-timeout): unsupported: we are asynchronous, so no timeouts, no RTT tracking!
--scan-delay 10                 nmap(scan-delay): unsupported: we do timing VASTLY differently!
--max-scan-delay 10             nmap(max-scan-delay): unsupported: we do timing VASTLY differently!
--scanflags SYN                 nmap(scanflags): TCP scan flags not yet supported
--send-ip                       nmap(send-ip): unsupported, we only do --send-eth
--ip-options test               nmap(ip-options): unsupported: maybe soon
--log-errors                    nmap(log-errors): unsupported: maybe soon
--system-dns                    nmap(system-dns): DNS lookups will never be supported by this code
--traceroute                    nmap(traceroute): unsupported
--host-timeout 10               nmap(host-timeout): unsupported: this is an asynchronous tool, so no timeouts
```

Thus a long-option diagnostic uses the normalized option name shown above, not the original spelling with `--`. Every invocation in the exact table returns 1, writes no standard output, writes precisely its listed newline-terminated diagnostic to standard error, and terminates before capture initialization.

The bare spellings divide according to whether this parser expects a value. Bare `--host-timeout`, `--min-hostgroup`, `--max-hostgroup`, `--min-parallelism`, `--max-parallelism`, `--min-rtt-timeout`, `--max-rtt-timeout`, `--initial-rtt-timeout`, `--scan-delay`, `--max-scan-delay`, `--ip-options`, `--scanflags`, and `--dns-servers` do not reach the explanatory Nmap diagnostic. Each instead returns 1, writes the exact short usage document from Spec 5 to standard output, and writes `<name-without-leading-dashes>: empty parameter` followed by the capture-library warning to standard error. Bare `--log-errors`, `--send-ip`, `--system-dns`, and `--traceroute` are value-less and do reach their exact single-line diagnostics from the table. None of these cases hangs or starts network activity.

## Spec 39

The ancillary parser has the following compatibility behavior in echo mode:

- `--interactive`, `--nostatus`, each of `--output-status open`, `--output-status closed`, and `--output-status all`, bare `--status`, `--reason`, `--datadir 'dir with spaces'`, and `--debug 7` are accepted but omitted from canonical echo. They return 0 and otherwise produce the ordinary echo and capture-library warning. `--status` is value-less: `--status true --echo` treats `true` as a positional token, returns 1 with no standard output, and writes exactly `FAIL: unknown command-line parameter "true"` plus the `did you want "--true"?` hint, without the capture-library warning.
- `--status-ndjson` and `--ndjson-status` are accepted and echo `ndjson-status = true`. `--status-timer 5` is not recognized; it returns 1 with no standard output and writes exactly `CONF: unknown config option: status-timer=5`.
- `--ssl-versions tls1.2,tls1.3`, `--pcap-payloadsize 1400`, `--script-args a=b,c=d`, and `--cisco-ike group:name` are not recognized. Each returns 1 with no standard output and a single `CONF: unknown config option: <name>=<value>` line. Consequently the combined data-control invocation beginning with `--datadir 'dir with spaces' --ssl-versions tls1.2,tls1.3 ... --echo` stops at `ssl-versions` and emits only `CONF: unknown config option: ssl-versions=tls1.2,tls1.3`.
- `--vulncheck` and `--tcp-syn-flag` are parsed as value-taking names rather than Boolean flags. When either is immediately followed by `--echo`, that token is consumed as its value and the command returns 1 with `CONF: unknown config option: vulncheck=--echo` or `CONF: unknown config option: tcp-syn-flag=--echo`, respectively.
- `--nobacktrace --echo` is accepted, omitted from echo, and returns 0. `--dynamic-ssl --echo` and `--ipv6 --echo` each return 1 with no standard output and respectively report `CONF: unknown config option: dynamic-ssl=--echo` and `CONF: unknown config option: ipv6=--echo`.
- `--ipv4 --echo` returns 1 with no standard output. It writes `[-] _parser_next(): unknown coding failure`, `ERROR: bad IP address/range: --echo`, the capture-library warning, and the ordinary three-line empty-target failure beginning `FAIL: target IP address list empty`, in that order.
- `--test` is a value-taking internal-test selector. The compatibility selectors `heartbleed`, `poodle`, `ticketbleed`, and `http` are all accepted. With ordinary ports/targets and `--echo`, each returns 0, prints the ordinary configuration without a `test`, selector-name, or banner line, and writes only the capture-library warning to standard error. In particular, `--test poodle -p443 127.0.0.1 --echo`, `--test ticketbleed -p443 127.0.0.1 --echo`, and `--test http -p80 127.0.0.1 --echo` echo their respective port and target normally. The selector is not mistaken for a target and does not hang.

Rates do not accept scientific notation. In particular, `--rate 1e6 --echo` returns 0, writes `CONF: non-digit in rate spec: rate=1e6` before the capture-library warning, and echoes the unchanged default `rate = 100       ` rather than one million. Very large all-decimal rate magnitudes must not overflow into a small or negative value and use the integral serialization specified in Spec 16. Unsupported `--port-ratio` is rejected with an explanatory `unsupported`/error diagnostic. These ancillary options need not perform unavailable network activity in the evaluation environment, but parsing, validation, canonical echoing, and combination with the main options must remain deterministic.
