# DataSurgeon executable specification

The required artifact is a directly runnable file named `executable` in the repository root. It is a single, flag-based command-line program for finding structured values in text. All text described below is UTF-8 and all shown spaces, punctuation, capitalization, and newlines are significant unless a section explicitly says otherwise.

## Spec 1

`executable` must be invocable directly (without a language-specific launcher) and must finish promptly after consuming its input. Normal extraction, including empty input and input with no matches, exits with status 0. Command-line syntax errors exit with status 2. Input/output opening failures exit with status 1. Ordinary diagnostics described as stdout messages must not be moved to stderr.

The command has no subcommands and accepts no positional arguments. Words such as `add`, `remove`, `list`, `update`, `extract`, and `scan` are not commands; when supplied without their leading `--`, they are unexpected arguments and cause a nonzero syntax-error result. Help must not contain a `Commands:`, `Subcommands:`, `[COMMAND]`, or `<COMMAND>` section.

The version flags `-V` and `--version` exit 0 and write the following exact newline-terminated version line, with nothing on stderr. When plugin discovery emits the missing-file notice from Spec 19, that notice is written first; otherwise this is the entirety of stdout.

```text
DataSurgeon: https://github.com/Drew-Alleman/DataSurgeon 1.2.8
```

## Spec 2

`--help` exits 0 and writes the following exact newline-terminated help body to stdout, and `-h` exposes the same main help context and documented options. When plugin discovery emits the missing-file notice from Spec 19, that notice precedes this body; otherwise the body is the entirety of stdout.

```text
Note: All extraction features (e.g: -i) work on a specified file (-f) or an output stream.

Usage: executable [OPTIONS]

Options:
  -f, --file <file>            File to extract information from [default: ""]
      --add <add>              Adds a plugin from a GitHub repository (e.g ds --add https://github.com/Drew-Alleman/ds-winreg-plugin/) [default: ""]
      --update <update>        Updates a plugin from a GitHub repository. You can also use `ds --update all` to update all plugins. (e.g ds --update https://github.com/DataSurgeon-ds/ds-cve-plugin/) [default: ""]
      --remove <remove>        Removes a plugin from a GitHub repository (e.g ds --remove https://github.com/Drew-Alleman/ds-winreg-plugin/) [default: ""]
      --list                   List all added plugins
  -C, --clean                  Only displays the matched result, rather than the entire line
      --directory <directory>  Process all files found in the specified directory [default: ""]
      --ignore                 Silences error messages
  -l, --line                   Displays the line number where the match occurred
  -T, --thorough               Doesn't stop at first match (useful for -C if multiple unique matches are on the same line
  -D, --display                Displays the filename assoicated with the content found (https://github.com/Drew-Alleman/DataSurgeon#reading-all-files-in-a-directory)
  -S, --suppress               Suppress the 'Reading standard input' message when not providing a file
      --drop <drop>            Specify a regular expression to exclude certain patterns from the search. (e.g --drop "^.{1,10}$" will hide all matches not under 10 characters) [default: ""]
      --filter <filter>        Include only lines that match the specified regex. (e.g: '--filter ^error' will only include lines that start with the word 'error' [default: ""]
  -X, --hide                   Hides the identifier string infront of the desired content (e.g: 'hash: ', 'url: ', 'email: ' will not be displayed.
  -o, --output <output>        Output's the results of the procedure to a local file (recommended for large files) [default: ""]
  -t, --time                   Time how long the operation took
  -e, --email                  Extract email addresses
  -p, --phone                  Extracts phone numbers
  -H, --hash                   Extract hashes (NTLM, LM, bcrypt, Oracle, MD5, SHA-1, SHA-224, SHA-256, SHA-384, SHA-512, SHA3-224, SHA3-256, SHA3-384, SHA3-512, MD4)
  -i, --ip-addr                Extract IP addresses
  -6, --ipv6-addr              Extract IPv6 addresses
  -m, --mac-addr               Extract MAC addresses
  -c, --credit-card            Extract credit card numbers
  -u, --url                    Extract urls
  -F, --files                  Extract filenames
  -b, --bitcoin                Extract bitcoin wallets
  -a, --aws                    Extract AWS keys
  -g, --google                 Extract Google service account private key ids (used for google automations services)
  -d, --dns                    Extract Domain Name System records
  -s, --social                 Extract social security numbers
  -h, --help                   Print help
  -V, --version                Print version
```

If a help flag occurs before an otherwise invalid option, help takes precedence and the command still exits 0. By contrast, `-- --help` treats `--help` as an unsupported positional argument and errors.

## Spec 3

The parser supports long options, separate option values, and `--name=value`. In particular, all of `-o path`, `-o=path`, `--output path`, and `--output=path` are valid. Boolean short options may be clustered in either order, such as `-Ce`, `-eC`, `-eCT`, and `-iClD`.

The value-taking options are `-f`/`--file`, `-o`/`--output`, `--directory`, `--add`, `--update`, `--remove`, `--drop`, and `--filter`. Omitting a value is a status-2 error. The diagnostic goes to stderr and contains `a value is required for '<canonical option>'`, followed by `For more information, try '--help'.` The canonical labels are `--file <file>`, `--output <output>`, `--directory <directory>`, `--add <add>`, `--update <update>`, `--remove <remove>`, `--drop <drop>`, and `--filter <filter>`, including when the short spelling `-f` or `-o` was supplied.

Unknown options similarly exit 2. The stderr text contains `error: unexpected argument '<argument>' found`, a `Usage: executable [OPTIONS]` line, and `For more information, try '--help'.` In an invalid cluster such as `-Ze`, identify `-Z` as unexpected. `--` does not enable a positional-argument mode: any token following it is still unexpected.

An option may not be supplied more than once, including once inside a cluster and once separately. For example, two `-o` occurrences are diagnosed using the canonical label `--output <output>`; two `--output` occurrences, `-iCT ... -T`, and `-e --email` identify `--output <output>`, `--thorough`, and `--email`, respectively, followed by `cannot be used multiple times`. These cases exit 2, emit no extraction data, and create no requested output files.

For all syntax errors in this section, stdout is empty when either plugin configuration file exists. If neither exists, the exact Spec 19 missing-plugin notice is written to stdout before the stderr parser diagnostic; that notice does not change status 2.

## Spec 4

Input selection follows these rules:

- A nonempty `-f/--file` value selects that one literal path. The special string `-` is a filename, not stdin.
- Omitting `--file`, or explicitly using `--file ""`, reads standard input until EOF.
- In stdin mode, unless `-S/--suppress` is set, the stdin portion of stdout begins with exactly `[*] Reading standard input. If you meant to analyze a file use 'ds -f <FILE>' (ctrl+c to exit)\n`. This informational line is still on stdout when extracted records are redirected with `--output`. `--suppress` removes only this line. A missing-plugin notice, when applicable, precedes the banner and is not suppressed by `--suppress`.
- File and directory input do not print the stdin banner. Empty stdin succeeds; apart from a possible preceding Spec 19 notice, it prints just the banner unless suppressed. Empty files produce no extraction output.

Split input into logical lines. Line numbering is one-based and resets for each file. Strip LF and a preceding CR from the data. Process a final unterminated line. Preserve other Unicode and whitespace in full-line output. Support very long lines and matches (at least 20,000-character lines and a 5,000-character email local part) without truncation.

Decode files line by line as UTF-8. Silently skip a line that is not valid UTF-8, but continue with later lines. A skipped invalid-UTF-8 line does not advance the displayed `--line` counter: for `before@example.com\ninvalid\xffx@example.com\nnull\x00x@example.com\nafter@example.org\n`, clean email extraction numbers the emitted `before@example.com`, `x@example.com` (from the NUL-containing line), and `after@example.org` records 1, 2, and 3. A tab, internal CR, or NUL does not by itself discard an otherwise valid UTF-8 line. Tab and internal CR are preserved in full-line output: stdin `test@example.com\ttab\rseparated\r\ndata` with `-e -S` emits `email: test@example.com\ttab\rseparated\n`. A NUL-containing line is also searched, so a clean match after the NUL can be emitted.

## Spec 5

`--directory DIR` recursively visits every regular file beneath `DIR`, including nested files, dotfiles, extensionless files, and files with extensions such as `.txt`, `.log`, `.md`, and `.json`. It does not restrict input by suffix. Each file is processed as an independent source and line numbers restart at 1. Empty directory trees and trees containing no matches produce no extraction records and succeed. Their stdout is empty when a plugin file exists; when neither plugin file exists, it consists of the Spec 19 missing-plugin notice. Traversal must handle at least 50 files, five levels of nesting, and hundreds of input lines. A stable lexical path traversal is suitable; where filesystem ordering differs, the semantic requirement is that every eligible file be processed exactly once.

When `--display` is enabled, retain the actual source path used for each file. For a single file this is the `--file` string (relative stays relative, absolute stays absolute); directory descendants use their joined paths. The source name for stdin is the empty string.

## Spec 6

The built-in selectors are `-e/--email`, `-p/--phone`, `-H/--hash`, `-i/--ip-addr`, `-6/--ipv6-addr`, `-m/--mac-addr`, `-c/--credit-card`, `-u/--url`, `-F/--files`, `-b/--bitcoin`, `-a/--aws`, `-g/--google`, `-d/--dns`, and `-s/--social`. If at least one built-in or plugin selector is present, search only the selected types. If no selector is present, enable every built-in type and every plugin loaded from the discovered plugin file. Thus merely installing a plugin does enable it in the no-selector default search.

For every source line, determine which enabled patterns match. Without `--thorough`, emit at most one record for the first matching enabled extractor family on that line. In clean mode with no filter or drop, use that family's first extracted match. With a filter or drop, examine same-family matches from left to right until one survives both expressions and emit the first survivor. For example, clean URL extraction with `--filter example` on `http://short.co and https://verylongdomainname.example.org/path/to/resource` emits the later `https://verylongdomainname.example.org/path/to/resource`. The extractor-family priority may be implementation-defined but must remain consistent throughout one process; this is why a line containing email, IPv4, URL, and hash yields one record, and two such lines use the same type prefix. Lines on which only different individual types occur must still select their respective matching types.

With `--thorough`, visit every matching enabled extractor family and every nonoverlapping match on the line, except for the multiple-plugin compatibility behavior specified in Spec 20. Duplicate extracted strings from the same type on the same input line are collapsed, preserving first-occurrence order. Duplicates on different lines are not collapsed.

There is one compatibility quirk when `--thorough` is used without `--clean`: for each unique extracted match, emit a pair consisting of a full-source-line record followed by that extracted-match record. Consequently, a line containing one email produces two identical-looking records, while `a@example.com then b@example.org` produces, in order, the full line, `a@example.com`, the full line again, and `b@example.org`. With `--clean --thorough`, emit only the unique extracted matches.

## Spec 7

Each extractor has the following exact output type identifier:

| Selector | Type identifier |
| --- | --- |
| email | `email` |
| phone | `phone_number` |
| hash | `hashes` |
| IPv4 | `ip_address` |
| IPv6 | `ipv6_address` |
| MAC | `mac_address` |
| credit card | `credit_card` |
| URL | `url` |
| filename | `files` |
| Bitcoin | `bitcoin_wallet` |
| AWS | `aws_keys` |
| Google | `google` |
| DNS SRV | `srv_dns` |
| social security number | `social_security` |

The data field is the entire source line by default and the exact matched substring with `-C/--clean`, except that the DNS extractor retains the full source line even in clean mode as specified in Spec 14. Plain-text records have these exact forms:

- Default: `<type>: <data>\n`.
- `--hide`: `<data>\n`.
- `--line`: `<type>, <data>, line: <N>\n`.
- `--hide --line`: `<data>, line: <N>\n`.
- `--display`: `<type>, file: <source> <data>\n`.
- `--hide --display`: `file: <source> <data>\n`.
- `--display --line`: `<type>, file: <source> <data>, line: <N>\n`.
- All three of hide, display, and line: `file: <source> <data>, line: <N>\n`.

For stdin plus display, `<source>` is empty, so `file:` is followed by two spaces before the data. Every emitted record ends in exactly one newline. No-match input emits no placeholder or summary.

## Spec 8

`--filter REGEX` and `--drop REGEX` use regular-expression search semantics, including `.`, quantifiers such as `*` and `{1,15}`, `^`/`$` anchors, alternation (`a|b`), character classes and ranges, escaped metacharacters such as `\[` and `\.`, parenthesized groups, and the leading case-insensitive flag `(?i)`. Candidate records are formed as in Spec 6, then the regular expressions are applied to the candidate record's data field (not to its type/file/line decoration). `--filter` keeps a candidate only if its data has a match; `--drop` rejects a candidate if its data has a match. If both occur, both conditions apply (filter inclusion followed by drop exclusion).

This makes filters naturally line-oriented in default mode and match-oriented in clean mode. For example, default `--filter '^ERROR'` retains full lines beginning with `ERROR`; clean `--filter '@example\.com'` retains only matching extracted emails; clean `--drop '^.{1,15}$'` rejects short extracted emails. `--drop '.*'` rejects everything. Filtering to no candidates is a successful, empty result.

An invalid filter/drop expression is not an ordinary ignored error. It exits 101 and writes a Rust-panic-compatible diagnostic to stderr. It must contain ``called `Result::unwrap()` on an `Err` value``, `regex parse error`, and the parser's specific reason. `[unclosed` and `[invalid` report `unclosed character class`; `(?P<invalid` reports `unclosed capture group name`; and `(?invalid)` reports `unrecognized flag`. Each includes `panicked at src/main.rs:<error location>:`. `--ignore` does not suppress this failure.

Preserve one legacy first-match quirk when a filter or drop rejects the first of several same-type matches on a line: continue looking for a surviving later match even without `--thorough`; if one survives, emit that extracted match rather than the full line. For example, applying credit-card extraction with `--drop 3456` to a line containing continuous cards `4532123456789012 and 5425233430109903` rejects the first and emits `credit_card: 5425233430109903`.

## Spec 9

Email extraction recognizes case-preserving addresses whose local part contains one or more ASCII letters, digits, `.`, `_`, `%`, `+`, or `-`; then `@`; then a domain made of letters, digits, dots, or hyphens; then a final dot and an ASCII alphabetic TLD of exactly 2 through 4 characters. Domain underscores are not accepted: clean email extraction of `user@sub_domain.com` produces no output. Matching is case-insensitive with respect to allowed letters but does not alter the captured spelling.

Required examples include `user.name+tag@subdomain.domain.co.uk`, `admin@test-site.org`, `user_name@example.com`, `TEST@EXAMPLE.COM`, and arbitrarily long local parts. TLDs `.io`, `.com`, and `.info` match; `.x` and `.local` do not. Inputs such as `notanemail@`, `also@.com`, and `@domain.com` do not form matches. In clean thorough mode, multiple distinct addresses on one line are each emitted in left-to-right order.

## Spec 10

IPv4 extraction recognizes four decimal octets separated by literal dots, with every octet in 0 through 255. Leading zero-compatible decimal forms may be accepted. All valid ranges are included, including `0.0.0.0`, `255.255.255.255`, loopback, RFC1918 private addresses, link-local, multicast, and documentation ranges. It is a substring-oriented matcher rather than a strict token validator: from `256.1.1.1` it captures `56.1.1.1`, and from `300.200.100.50` it captures `0.200.100.50`; `999.999.999.999` yields no valid four-octet substring.

IPv6 extraction accepts full and compressed colon-hex forms sufficiently to recognize full eight-group addresses, `2001:db8:85a3::8a2e:370:7334`, `::1`, and `fe80::`. Preserve the historical clean-match behavior for a compressed address: clean extraction of `2001:db8::1` is `2001:db8` (the prefix before the double colon).

MAC extraction recognizes exactly six two-hex-digit octets separated by colons, case-insensitively and without changing case. Examples are `00:1A:2B:3C:4D:5E`, `aa:bb:cc:dd:ee:ff`, and `Aa:Bb:Cc:Dd:Ee:Ff`. Five-octet, hyphen-separated, and Cisco dotted forms do not match.

## Spec 11

URL extraction recognizes `http://` and `https://` URLs and preserves ordinary host, path, query, ampersand-separated parameters, and fragment text when no explicit port intervenes. An explicit port is not included and terminates the match: clean URL extraction from `see https://api.example.com:8443/v1/users?id=123&sort=asc now` emits exactly `url: https://api.example.com\n`, excluding the port and everything after it. Required clean results include `https://example.com`, `https://example.com/`, deep paths, `https://api.example.com/v1/users?id=123&sort=asc`, and `https://example.com/page#section-1`. URLs may appear adjacent to prose, multiple URLs on a line are available in thorough mode, and a trailing prose delimiter is not part of the match.

Filename extraction (`-F/--files`) uses the type label `files`, independently of the source-filename display feature. Its observed clean mappings include `document.pdf` to `document.pdf`, `image.jpg` to `image.jpg`, `report.docx` to `report.doc`, `data.json` to `data.json`, `config.yaml` to `config.yaml`, `backup.tar.gz` to `backup.tar`, `script.sh` to `script.sh`, and `script.ps1` to `script.ps1`. Do not infer a filename merely from dotted syntax: domain fragments within emails or URLs, such as `company.com` and `example.com`, and dotted IPv4 text are not filename-family matches. This exclusion also applies when the no-selector thorough search runs every family.

## Spec 12

Hash extraction is case-insensitive over hexadecimal digits and preserves original case. At minimum it recognizes standalone exact-length hexadecimal hashes of 32 (MD5/MD4-style), 40 (SHA-1), 56 (SHA-224), 64 (SHA-256), 96 (SHA-384), and 128 (SHA-512) characters. A hexadecimal run one character shorter or longer than an accepted length must not be accepted or sliced into an apparent valid hash. Thus 31-, 33-, and 65-character runs do not match while 32-, 40-, and 64-character runs do. Hashes embedded in colon-delimited password-dump lines still match. The type label for all supported hash families is `hashes`.

## Spec 13

Phone extraction recognizes North-American-style `AAA-BBB-CCCC` substrings where `AAA` begins with 2 through 9. It therefore recognizes examples such as `555-123-4567`, `911-555-0000`, and the `212-555-1234` substring inside `+1-212-555-1234`; it does not accept `123-456-7890` as a phone. Parenthesized and dot-separated forms need not be treated as this extractor's canonical match.

Credit-card extraction recognizes 16 decimal digits arranged as four groups of four with either no separators, spaces, or hyphens, without performing a Luhn or issuer check. Examples include `4532123456789012`, `4532 1234 5678 9012`, and `4532-1234-5678-9012`. A 15-digit Amex-style number does not match. The continuous 20-digit input `11112222333344445555` is not sliced into a card and produces no credit-card record.

Social-security extraction recognizes the syntactic form exactly three digits, hyphen, two digits, hyphen, four digits. Unhyphenated and space-separated forms do not match. It deliberately does not validate prohibited numeric ranges, so `000-45-6789`, `123-00-6789`, and `123-45-0000` all match.

## Spec 14

Bitcoin extraction recognizes legacy Base58 addresses matching `[13][123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{25,34}`: they begin with `1` or `3` and have total length 26 through 35. Both P2PKH and P2SH examples such as `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`, `3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy`, and the 26-character boundary example `1111111111111111111114oLvT2` match. Strings beginning with `2`, very short strings such as `1A1z`, and `bc1...` Bech32 addresses do not.

AWS extraction recognizes a case-insensitive label `aws_access_key_id`, `ACCESS_KEY`, `secret_key`, or `aws_secret_access_key`, optional horizontal spaces, `=`, optional spaces, and a 20-through-40-character key/secret from `[A-Za-z0-9/+=]`. The match includes the label, spacing, equals sign, and value; a bare `AKIA...` without one of these labels does not match. Values shorter than 20 do not match. Examples include `aws_access_key_id=AKIAIOSFODNN7EXAMPLE` and `aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`.

Google extraction requires the JSON-style field name `"private_key_id"`, a colon with optional whitespace, an opening quote, 40 word/alphanumeric characters, and a closing quote. The closing quote is required: `"private_key_id": "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG` followed by a newline produces no output. In clean mode the closing quote is part of the exact match; `"private_key_id":  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"` emits exactly `google: "private_key_id":  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"\n`. The same closing-quote-inclusive boundary applies when no selector is supplied. Unrelated 40-character strings do not match. The `google` match and full-line output therefore retain the JSON field context.

DNS extraction recognizes SRV records of the form `_service._protocol.name IN SRV priority weight port target`, where the service/protocol/host portions are dot-separated names and the three SRV numeric fields are decimal. The literal uppercase sequence ` IN SRV ` is required. It recognizes short names such as `_s._t.d IN SRV 1 1 1 h` and records embedded in prose; an A record or text merely mentioning SRV without the `IN` field does not match. Unlike the other built-ins, clean DNS output is still the entire source line: `prefix _s._t.d IN SRV 1 1 1 h suffix` with `-d -C -S` emits `srv_dns: prefix _s._t.d IN SRV 1 1 1 h suffix`.

## Spec 15

`-o/--output PATH` directs extraction records to PATH rather than stdout. Plain output files are opened in append mode and newly created files are owner-readable. Existing content is preserved across invocations. The stdin banner, if enabled, remains on stdout rather than entering the output file. With neither timing nor a banner/error, successful file-output operation has empty stdout and stderr.

Do not create missing parent directories. Failure to create/open an output file exits 1 and prints a stdout message containing `[-] Failed to open output file:`. With `--ignore`, suppress that error text but retain exit 1. A write failure after opening exits 0 and prints a stdout message containing `Failed to write to output file` and the operating-system reason such as `No space left on device`. For example, writing one email record to `/dev/full` exits 0, writes exactly `Failed to write to output file:  error: No space left on device (os error 28)\n` to stdout, and writes nothing to stderr.

## Spec 16

CSV mode is selected solely when the output path's final suffix is exactly lowercase `.csv`. `.CSV`, extensionless paths, and `.txt` remain plain text; `data.backup.csv` is CSV. CSV output is deliberately simple text with comma-space separators and does not quote/escape commas contained in data.

The header and field order are computed from `--hide`, `--display`, and `--line`:

| Options | Exact header |
| --- | --- |
| none | `content_type, data` |
| display | `content_type, file, data` |
| line | `content_type, line, data` |
| display + line | `content_type, file, line, data` |
| hide | `data` |
| hide + display | `file, data` |
| hide + line | `line, data` |
| hide + display + line | `file, line, data` |

Every header ends in `\n`. Rows use the same column order and literal `, ` separators. Type is the Spec 7 identifier, file is the source string, line is the decimal one-based number, and data follows clean/full-line rules. For example: `ip_address, /tmp/in.txt, 2, 1.1.1.1\n`. Header-only CSV is produced for empty/no-match input. Directory output writes one header for the entire traversal.

CSV files also append. Each separate invocation writes its header again, so running twice against one existing CSV produces two header blocks. This behavior is intentional.

## Spec 17

`-t/--time` appends one and only one timing line after all extraction output:

```text
[*] Time elapsed: HHh:MMm:SSs
```

Hours, minutes, and seconds are two-digit, zero-padded whole units. Normal short operations used for small or empty inputs report exactly `[*] Time elapsed: 00h:00m:00s\n`. Timing appears even when there are no matches or `--ignore` is present. In unsuppressed stdin mode the order is stdin banner, records, timing. For file input with no matches it is the only stdout line. Timing is ordinary output, not an error.

## Spec 18

A missing input file exits 1, writes nothing to stderr, and (unless `--ignore`) writes exactly `[-] File not found: <path>\n` to stdout. `--ignore` suppresses the message but does not change the exit status. In particular, `-f -` attempts to open the literal path `-` and may produce `[-] File not found: -`.

Read/decode errors in individual directory entries or individual malformed binary lines are skipped so other valid files/lines can still produce records. Lack of any match is never an error.

## Spec 19

Plugins are described by a UTF-8 JSON array. Each object has six required string fields: `content_type`, `arg_long_name`, `help_message`, `regex`, `version`, and `source_url`. Extra JSON whitespace is accepted. Each valid plugin adds a dynamic boolean option named `--<arg_long_name>` whose help text is `help_message`; selecting it enables its regular expression. A missing or empty plugin array means those dynamic options do not exist, so using one is an ordinary unexpected-argument syntax error. Extra object fields do not prevent a plugin with all six required string fields from loading, although a later removal writeback retains only the six modeled fields.

Plugin discovery occurs before ordinary argument parsing and command output. It checks `$HOME/.DataSurgeon/plugins.json` first and loads `./plugins.json` only when the home-location file is absent. The path reported by management operations is `$HOME/.DataSurgeon/plugins.json`, even when the loaded file is local.

If neither file exists and `HOME` is available, built-in flags still work, but an invocation first writes exactly `Failed to open plugins.json file. PLUGIN_PATH: <home-path>\n` to stdout. The notice therefore precedes a version line, help body, parser error on stderr, stdin banner, extraction record, or timing line. It is also the sole stdout for an otherwise silent successful empty-directory scan. The missing-file `--list` path writes this same notice twice and then the empty-state line from Spec 21. All exact-output and empty-stdout statements elsewhere in this specification are conditional on this notice not applying unless they explicitly describe its ordering. An existing empty JSON array suppresses the notice.

If plugin JSON is malformed, `--list` writes messages containing `Failed to parse plugins.json` and `Do you want to exit?`. Answering `y` exits 1. If the `HOME` environment entry is absent, plugin path resolution exits 101 before loading even an existing local `./plugins.json`; stdout is empty and stderr contains ``Home directory not found. Failed to read environmental variable: `HOME`.: NotPresent`` and `panicked at src/plugins/mod.rs:<error location>`.

## Spec 20

Plugin matching and formatting use the same clean, thorough, hide, display, line, filter, drop, stdin, directory, timing, and output-file pipeline as built-ins, including repetition of the full source line before every match in thorough non-clean mode. The output type identifier is `content_type`, not `arg_long_name`. Clean plugin extraction always uses the full regex match; capturing groups do not replace it. Thus regex `number=(\d+)` on `number=123` emits `numbers: number=123`.

For example, a plugin with `content_type: "numbers"`, `arg_long_name: "numbers"`, and regex `(\\d+)` extracts the full matches `123` and `456`; a plugin with `content_type: "hexvalue"`, `arg_long_name: "hex"`, and regex `0x[0-9a-fA-F]+` prints `hexvalue: 0x1234ABCD`. For a single selected plugin, clean thorough mode emits every unique match and non-thorough mode emits only the first match.

The following exact multiple-plugin compatibility behavior is required even though `--thorough` is present: with a `numbers`/`--numbers` plugin whose regex is `(?<![A-Za-z])\d+(?![A-Za-z])` and a `hexvalue`/`--hex` plugin whose regex is `0x[0-9a-fA-F]+`, running `--numbers --hex -CTS` on `number 123 and 0xAB\n` exits 0 and writes exactly `hexvalue: 0xAB\n` to stdout with empty stderr; it does not emit `numbers: 123`. This exact compatibility case overrides Spec 6's every-family thorough rule.

An invalid plugin regex is silently ignored: selecting that otherwise valid plugin succeeds with no output and no panic.

## Spec 21

`--list` is a terminal plugin-management operation and returns status 1. For no plugins, stdout ends with (and normally consists of) `No plugins found. Plugin File: <HOME>/.DataSurgeon/plugins.json\n`.

For a nonempty array, list entries in JSON order using:

```text
Plugin File: <HOME>/.DataSurgeon/plugins.json

Source URL<pad> | Version<pad> | Argument Long Name
<source_url><pad> | <version><pad> | <arg_long_name><pad>
```

There are exactly two ` | ` separators per header/data row. Each column's width is the maximum Unicode code-point count of its heading and all values; left-pad nothing and right-pad shorter values. This is not terminal display-width padding, so East Asian wide characters can make the rendered columns differ by a cell even though no content is truncated. The three headings and column order are exactly `Source URL`, `Version`, and `Argument Long Name`. Preserve Unicode content.

`--remove URL` is a terminal plugin-management operation and returns status 1 whether or not a plugin matches. It removes every plugin whose `source_url` matches after case-folding, treating `http://` and `https://` as equivalent, and trimming trailing `/`. Do not discard or normalize query parameters, and do not treat `www.github.com` as equivalent to `github.com`. Preserve the relative order and the six required modeled fields of remaining plugins, discard extra object fields during a removal writeback, and write a valid JSON array back to the same file that discovery loaded: the home file when it existed, otherwise local `./plugins.json`. If at least one plugin is removed, print exactly one `[*] Removed plugin: <URL>\n` line, preserving the user's URL spelling. If nothing matches, print nothing and leave the loaded file byte-for-byte unchanged. Removing the final entry rewrites that loaded file to `[]` rather than deleting it; removal of a locally loaded final entry does not create the home plugin file.

`--add` and `--update` are top-level value-taking flags rather than subcommands. Their network/repository side effects are outside the required extraction and local plugin-management behavior, but their argument parsing and missing-value errors must follow Spec 3.
