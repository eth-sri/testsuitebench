# Specification for `executable`

The required artifact is one executable file named exactly `executable`. It is a command-line file compressor compatible with the Zstandard CLI version described below. All paths and byte streams are arbitrary unless a restriction is stated. “Preserve data” means byte-for-byte preservation, including empty input, NUL bytes, every byte value, Unicode encoded in file contents, and large inputs. The executable must never depend on files from this specification directory at run time.

## Spec 1

`executable` is a flag-oriented CLI, not a subcommand-oriented CLI. A bare non-option word is an input pathname; if it does not exist, report a file access error rather than “unknown command”. The default operation is compression. The primary operation selectors are `-z`/`--compress`, `-d`/`--decompress`/`--uncompress`, `-l`/`--list`, `-t`/`--test`, `--train`, and `-b`/`-b#` for benchmarking. When compatible operation selectors occur more than once, the last selector wins (for example, `--compress -d` selects decompression). Help and version terminate without performing file work. Normal success exits 0; the error statuses defined later must be honored.

The process must be safe for concurrent independent invocations and complete ordinary small operations well within five seconds. It must not emit binary data anywhere except the selected output file or standard output.

## Spec 2

Parse options anywhere before or among input names. `--` ends option parsing, so every following token is a pathname even if it begins with `-`. A lone `-` denotes standard input. Support conventional combined short flags such as `-dc`, `-tq`, `-qf`, `-fo OUTPUT`, and repeated verbosity forms such as `-vvv` and `-qq`.

Options whose value is fused to the short name include `-1` through `-22`, `-T#`, `-M#`, `-b#`, `-e#`, `-i#`, `-B#`, `-P#`, and `-s#`. `-o` and `-D` require a separate following token; `--output=path` and a missing value for `-o` are errors. A fused dictionary token such as `-Dfoo` is treated as a missing separate argument: it exits 1, leaves standard output empty, and writes exactly `error: missing command argument ` plus a newline to standard error, without short help. The separate value after `-o` cannot begin with `-`: for example, `INPUT -o -destination` exits 1, creates no `-destination` file, and writes exactly `error: command cannot be separated from its argument by another command ` plus a newline to standard error. A dash-prefixed destination must instead be expressed by a spelling that does not begin with a command marker, such as `./-destination`. For repeatable settings such as `-o`, thread count, and output-directory selection, the last setting wins. Long Boolean switches do not accept `=value`; for example, `--check=1`, `--progress=maybe`, and `--asyncio=no` are invalid. Long valued switches documented with `=` accept that form; the separate-value forms documented in the help also work.

For gzip command compatibility, hidden short `-n` is accepted even under the normal executable name. It suppresses an original-name field for gzip and is a harmless no-op for native Zstandard output. This is intentionally different from long `--no-name`, whose availability depends on invocation name as specified later.

Unless a more specific parsing or diagnostic rule below applies, an unrecognized or malformed option exits 1 and writes `Incorrect parameter: TOKEN ` (including the space before the newline), followed immediately by the complete short help text from Spec 3, to standard error. Thus `--zstd=invalid`, `--zstd=wlog=25,extra`, `--longX`, `--fast=0`, `--fastX`, and `--adapt=min=999,max=1` each use that exact first-line form and then the short help. A missing option argument exits 1 and includes `error: missing command argument`. `--help` takes precedence over later invalid flags, but `-- --help` treats `--help` as a file.

## Spec 3

`-h` prints exactly the following short help to standard output, including blank lines and the final newline, and nothing to standard error:

```text
Compress or decompress the INPUT file(s); reads from STDIN if INPUT is `-` or not provided.

Usage: executable [OPTIONS...] [INPUT... | -] [-o OUTPUT]

Options:
  -o OUTPUT                     Write output to a single file, OUTPUT.
  -k, --keep                    Preserve INPUT file(s). [Default] 
  --rm                          Remove INPUT file(s) after successful (de)compression to file.

  -#                            Desired compression level, where `#` is a number between 1 and 19;
                                lower numbers provide faster compression, higher numbers yield
                                better compression ratios. [Default: 3]

  -d, --decompress              Perform decompression.
  -D DICT                       Use DICT as the dictionary for compression or decompression.

  -f, --force                   Disable input and output checks. Allows overwriting existing files,
                                receiving input from the console, printing output to STDOUT, and
                                operating on links, block devices, etc. Unrecognized formats will be
                                passed-through through as-is.

  -h                            Display short usage and exit.
  -H, --help                    Display full help and exit.
  -V, --version                 Display the program version and exit.

```

`-H` and `--help` print the banner from Spec 4, a blank line, then the exact short-help introduction/options above, followed by these sections and a final newline:

```text
Advanced options:
  -c, --stdout                  Write to STDOUT (even if it is a console) and keep the INPUT file(s).

  -v, --verbose                 Enable verbose output; pass multiple times to increase verbosity.
  -q, --quiet                   Suppress warnings; pass twice to suppress errors.
  --trace LOG                   Log tracing information to LOG.

  --[no-]progress               Forcibly show/hide the progress counter. NOTE: Any (de)compressed
                                output to terminal will mix with progress counter text.

  -r                            Operate recursively on directories.
  --filelist LIST               Read a list of files to operate on from LIST.
  --output-dir-flat DIR         Store processed files in DIR.
  --output-dir-mirror DIR       Store processed files in DIR, respecting original directory structure.
  --[no-]asyncio                Use asynchronous IO. [Default: Enabled]

  --[no-]check                  Add XXH64 integrity checksums during compression. [Default: Add, Validate]
                                If `-d` is present, ignore/validate checksums during decompression.

  --                            Treat remaining arguments after `--` as files.

Advanced compression options:
  --ultra                       Enable levels beyond 19, up to 22; requires more memory.
  --fast[=#]                    Use to very fast compression levels. [Default: 1]
  --adapt                       Dynamically adapt compression level to I/O conditions.
  --long[=#]                    Enable long distance matching with window log #. [Default: 27]
  --patch-from=REF              Use REF as the reference point for Zstandard's diff engine. 
  --patch-apply                 Equivalent for `-d --patch-from` 

  -T#                           Spawn # compression threads. [Default: 4; pass 0 for core count.]
  --single-thread               Share a single thread for I/O and compression (slightly different than `-T1`).
  --auto-threads={physical|logical}
                                Use physical/logical cores when using `-T0`. [Default: Physical]

  --jobsize=#                   Set job size to #. [Default: 0 (automatic)]
  --rsyncable                   Compress using a rsync-friendly method (`--jobsize=#` sets unit size). 

  --exclude-compressed          Only compress files that are not already compressed.

  --stream-size=#               Specify size of streaming input from STDIN.
  --size-hint=#                 Optimize compression parameters for streaming input of approximately size #.
  --target-compressed-block-size=#
                                Generate compressed blocks of approximately # size.

  --no-dictID                   Don't write `dictID` into the header (dictionary compression only).
  --[no-]compress-literals      Force (un)compressed literals.
  --[no-]row-match-finder       Explicitly enable/disable the fast, row-based matchfinder for
                                the 'greedy', 'lazy', and 'lazy2' strategies.

  --format=zstd                 Compress files to the `.zst` format. [Default]
  --[no-]mmap-dict              Memory-map dictionary file rather than mallocing and loading all at once
  --format=gzip                 Compress files to the `.gz` format.

Advanced decompression options:
  -l                            Print information about Zstandard-compressed files.
  --test                        Test compressed file integrity.
  -M#                           Set the memory usage limit to # megabytes.
  --[no-]sparse                 Enable sparse mode. [Default: Enabled for files, disabled for STDOUT.]
  --[no-]pass-through           Pass through uncompressed files as-is. [Default: Disabled]

Dictionary builder:
  --train                       Create a dictionary from a training set of files.

  --train-cover[=k=#,d=#,steps=#,split=#,shrink[=#]]
                                Use the cover algorithm (with optional arguments).
  --train-fastcover[=k=#,d=#,f=#,steps=#,split=#,accel=#,shrink[=#]]
                                Use the fast cover algorithm (with optional arguments).

  --train-legacy[=s=#]          Use the legacy algorithm with selectivity #. [Default: 9]
  -o NAME                       Use NAME as dictionary name. [Default: dictionary]
  --maxdict=#                   Limit dictionary to specified size #. [Default: 112640]
  --dictID=#                    Force dictionary ID to #. [Default: Random]

Benchmark options:
  -b#                           Perform benchmarking with compression level #. [Default: 3]
  -e#                           Test all compression levels up to #; starting level is `-b#`. [Default: 1]
  -i#                           Set the minimum evaluation to time # seconds. [Default: 3]
  --split=#                     Split input into independent chunks of size #. [Default: No chunking]
  -S                            Output one benchmark result per input file. [Default: Consolidated result]
  -D dictionary                 Benchmark using dictionary 
  --priority=rt                 Set process priority to real-time.
```

The full help must contain no “subcommand”, “Commands:”, or “available commands” section. The short help is a literal contiguous substring of full help and contains `Display short usage`.

## Spec 4

`-V` and `--version` normally print exactly this line to standard output and nothing to standard error:

```text
*** Zstandard CLI (64-bit) v1.6.0, by Yann Collet ***
```

With `-qq`, version output is exactly `1.6.0\n`. With `-vvv`, it is exactly:

```text
*** Zstandard CLI (64-bit) v1.6.0, by Yann Collet ***
*** supports: zstd, gzip
zlib version 1.2.11
lz4 version Unsupported
lzma version Unsupported
supports Multithreading 
_POSIX_C_SOURCE defined: 200809L
_POSIX_VERSION defined: 200809L 
PLATFORM_POSIX_VERSION defined: 200809L
```

## Spec 5

With no input pathname, read standard input. Compression of nonempty stdin defaults to standard output; `-c`/`--stdout` explicitly selects standard output and implies keeping named inputs. Decompression from stdin likewise defaults to stdout. A lone `-` may explicitly select stdin. Standard streams are binary and must not be text-transcoded. Successful pipe-to-pipe operation at ordinary verbosity produces no diagnostic output. Empty stdin in a mode requiring a compressed stream fails with an `unexpected end of file` message.

When stdin or binary stdout is an interactive terminal, refuse it by default to avoid reading a console or printing compressed bytes; the diagnostic identifies `stdin is a console, aborting` or `stdout is a console, aborting`. `-f` permits the operation. The fake-console hooks are not symmetric in this build. `--fake-stdin-is-console` makes a three-byte piped input fail with status 1, no standard output, and `stdin is a console, aborting` on standard error. `--fake-stderr-is-console` implies progress unless disabled. By contrast, `--fake-stdout-is-console -c` does not make a captured standard-output pipe act like a terminal: with three input bytes it exits 0, writes a 16-byte native frame beginning `28 B5 2F FD`, and leaves standard error empty, both with and without `-f`.

## Spec 6

Native compression must produce genuine interoperable Zstandard frames, not an implementation-private wrapper. Every ordinary frame begins with bytes `28 B5 2F FD`. It must encode and decode empty, one-byte, repetitive, random, and arbitrary binary inputs, from zero bytes through at least hundreds of megabytes. Files generated by this executable must decode correctly in a conforming independent Zstandard implementation, and this executable must decode independent frames using raw, RLE, or entropy-compressed blocks, including frames whose window/block size reaches 128 KiB and frames produced by older compatible encoders.

Decoding must honor frame headers, optional content size, optional dictionary ID, optional 32-bit content-checksum field, block boundaries, and end-of-frame validation. Invalid offsets, malformed Huffman/sequence states, illegal trailing bytes, truncation at any point, and checksum mismatch must produce a nonzero failure rather than a successful status. Named-file destinations remain transactional as specified later; standard-output streaming can retain bytes decoded before a late failure as described below. Invalid-offset, extraneous-sequence, and truncated-Huffman-state streams whose decoder cause is data corruption exit 1 and report `PATH : Decoding error (36) : Data corruption detected ` plus a newline to standard error; the numeric `Decoding error (36) :` prefix is mandatory. In ordinary named-file decompression, a malformed stream consisting of native magic followed by `corrupted data here` exits 1, creates no requested output, and reports `PATH : Decoding error (36) : Dictionary mismatch ` on standard error; in particular, the diagnostic retains the `Decoding error` prefix rather than reporting only the underlying cause.

A wholly non-Zstandard named input, even when its name ends in `.zst`, exits 1 and writes exactly `zstd: PATH: unsupported format ` plus a newline to standard error. A named `.zst` input only one, two, or three bytes long exits 1 and instead writes exactly `zstd: PATH: unknown header ` plus a newline. Corrupting the checksum field of an otherwise valid checksummed frame exits 1 and writes exactly `PATH : Decoding error (36) : Restored data doesn't match checksum ` plus a newline. These failures do not create or retain a destination.

A truncated native frame supplied to ordinary decompression on standard input exits 1 and writes exactly `/*stdin*\ : Read error (39) : premature end ` plus a newline to standard error. Standard-output decompression is streaming rather than transactional: if only the final byte of a checksum-bearing frame is removed, all bytes decoded before that late failure remain on standard output. In particular, truncating the last byte of a frame for the 1,400-byte payload `payload` repeated 200 times emits all 1,400 payload bytes before returning that error.

## Spec 7

For a named input in compression mode, the default destination is beside the input and appends `.zst`; gzip mode appends `.gz`. The source is kept by default. Standard output remains empty for file-to-file operations. `-o OUTPUT` selects one exact destination. The output must be nonempty and have the correct format magic even for empty input. Named inputs may contain spaces, punctuation, Unicode, leading dots, no extension, or very long valid path components.

Compression is deterministic for the same bytes, options, dictionary, and thread configuration: repeated runs produce identical frame bytes. This is canonical encoder compatibility, not merely repeatability or decodability: for a given input, options, dictionary, and thread configuration, the complete emitted frame bytes (including header choices, block representation and boundaries, and checksum) must match the reference CLI byte for byte. This applies across ordinary, fast, ultra, and multithreaded modes, so a conforming but differently encoded Zstandard frame is insufficient. Different supported levels and tuning flags remain decodable and may choose different representations from one another. Highly repetitive input must materially shrink; a trained relevant dictionary must be capable of improving compression over no dictionary.

## Spec 8

For a named input in decompression mode, remove a recognized suffix to form the default destination: `.zst` and `.gz` map to the basename, while `.tzst` and `.tgz` map to the basename with `.tar` appended. For example, decompressing `item.tzst` creates `item.tar`. A valid compressed file with an unknown suffix may still be decoded with `-c` or `-o`; without an explicit destination, exit 1 and write exactly `zstd: NAME: unknown suffix (.zst/.tzst/.gz/.tgz expected). Can't derive the output file name. Specify it with -o dstFileName. Ignoring.` plus a newline to standard error. `-o OUTPUT` always names the exact result.

Decompression reproduces original bytes exactly. It must support named-file to named-file, named-file to stdout, stdin to named-file, and stdin to stdout. It must not delete the compressed input unless `--rm` is used. Options that only tune compression may be accepted during decompression without changing decoded bytes; a multi-thread request during decompression is ignored with `Warning : decompression does not support multi-threading` when diagnostics are enabled.

## Spec 9

Decode all consecutive native frames in one stream and concatenate their uncompressed payloads in order. Frames with or without checksums can be mixed. Recognize Zstandard skippable frames whose little-endian magic lies from `50 2A 4D 18` through `5F 2A 4D 18`; skip exactly their declared payload and continue. Concatenating independently compressed inputs and then decoding must yield the concatenated originals. Garbage or an unsupported format after an otherwise valid frame is an error unless pass-through rules explicitly apply to the whole input.

## Spec 10

Native compression level defaults to 3. Accept normal levels 1–19 with `-#`. `-0` selects the default. In ordinary compression mode, without `--ultra`, a positive level over 19 is reduced to 19 and reports `Warning : compression level higher than max, reduced to 19`; with `--ultra`, accept 20–22 and reduce larger values to 22 with the analogous warning. Benchmark mode is the exception: its supported range always extends through level 22, and `-b25 -i0` clamps to level 22 even without `--ultra` and ends its standard output in `22#`. Absurd/overflowing and syntactically invalid level tokens fail. `--ultra` alone is accepted.

`--max` is an accepted maximum-compression alias. It performs compression successfully (including in quiet mode and with `-o`) rather than being rejected as an unknown option.

`--fast` equals `--fast=1`; accept positive fast levels including 1, 2, 3, 4, 5, and larger practical values. A trailing character after a positive numeric prefix is ignored: `--fast=2x` succeeds and selects the same setting as `--fast=2`, producing identical frame bytes for the same input. Reject zero, negative, or wholly nonnumeric forms using the exact malformed-option layout in Spec 2; for example, `--fast=0` and `--fastX` have first lines `Incorrect parameter: --fast=0 ` and `Incorrect parameter: --fastX ` respectively, followed by short help. Larger fast numbers favor speed and generally produce output no smaller than lower fast numbers on compressible fixtures. Across ordinary levels, higher levels should generally be no larger than lower levels on the tested repetitive corpora.

At `-vv`, the detailed `--zstd=` configuration line exposes the selected target length and numeric strategy. `--fast` and `--fast=1` include `tlen=1,strat=1`; tested explicit levels preserve the fast number, including `--fast=2` with `tlen=2,strat=1` and `--fast=5` with `tlen=5,strat=1`. `--ultra -20` includes `tlen=512,strat=9`, including with `-T2`. In `--fast --ultra -20`, the later `-20` level selection wins and the line likewise includes `tlen=512,strat=9`; `--ultra` enables the high level rather than preserving the earlier fast selection.

For gzip output, levels 1–9 work and `--best` (in gzip invocation mode) is level 9.

## Spec 11

If no command-line level is given, integer environment variable `ZSTD_CLEVEL` sets it. An explicit command-line level overrides it. Unsigned `ZSTD_NBTHREADS` sets worker count unless overridden by a CLI thread option. Invalid values do not abort compression; ignore them and warn on standard error:

```text
Ignore environment variable setting ZSTD_CLEVEL=VALUE: not a valid integer value 
Ignore environment variable setting ZSTD_NBTHREADS=VALUE: not a valid unsigned value 
```

For decimal overflow, replace the explanation with `numeric value too large`. At `-v`, an invalid or overflowing `ZSTD_NBTHREADS` is diagnosed exactly twice: once before the version banner during environment initialization and once after that banner during worker initialization; the ordinary compression status follows the second warning. An invalid or overflowing `ZSTD_CLEVEL` is diagnosed once before the version banner, followed by the ordinary compression status. Environment settings must affect real compression behavior, not merely be accepted.

## Spec 12

Support `--zstd=NAME=VALUE[,NAME=VALUE...]` for explicit native compression parameters. Accepted short names are `wlog` (window log), `clog` (chain log), `hlog` (hash log), `slog` (search log), `mml` (minimum match), `tlen` (target length), `strat` (strategy), `ovlog` (overlap log), and long-distance names `lhlog`, `lmml`, `lblog`, and `lhrlog`. Also accept the equivalent long spellings used by the CLI, such as `windowLog`, `ldmHashLog`, `ldmMinMatch`, `ldmBucketSizeLog`, and `ldmHashRateLog`. Validate ranges; strategy values outside the supported strategy set and unknown/malformed names fail with the Spec 2 `Incorrect parameter: TOKEN ` line (including its trailing space) plus short help. This applies, for example, to `--zstd=invalid` and `--zstd=wlog=25,extra`.

`--show-default-cparams INPUT` writes the selected parameters to standard error, then continues the requested compression; standard output remains empty for an ordinary named-file invocation. The parameter display begins `INPUT (N bytes)` and has separate lines labeled exactly `windowLog`, `chainLog`, `hashLog`, `searchLog`, `minMatch`, `targetLength`, and `strategy`. The strategy line includes both the symbolic strategy and its numeric value. For a 10-byte file named `small.txt` at the default level, the parameter portion is exactly:

```text
small.txt (10 bytes)
 - windowLog     : 10
 - chainLog      : 6
 - hashLog       : 7
 - searchLog     : 2
 - minMatch      : 4
 - targetLength  : 0
 - strategy      : ZSTD_dfast (2)
```

The normal compression status follows on standard error. It cannot be combined with decompression and then exits 1 with `error : can't use --show-default-cparams in decompression mode `.

`--compress-literals`/`--no-compress-literals` and `--row-match-finder`/`--no-row-match-finder` select their respective encoder behavior while retaining round-trip correctness. The last of each positive/negative pair wins.

## Spec 13

Support `-T#` and `--threads=#`: 0 auto-detects cores; positive counts including 1, 2, 4, and 8 are valid. An empty long-option value is accepted as zero: `--threads=` selects the same setting as `--threads=0` and produces identical frame bytes for the same input. Negative, nonnumeric, and overflowing counts are rejected. In particular, `--threads=-1` and `--threads=no` each exit 1, leave standard output empty, and write exactly `error: only numeric values with optional suffixes K, KB, KiB, M, MB, MiB are allowed ` plus a newline to standard error, without short help. `--single-thread` selects a genuinely single combined I/O/compression thread and can override an earlier `-T0`; a later thread setting may override an earlier one. `--auto-threads=physical` and `--auto-threads=logical` choose the core-count policy for `-T0`.

Multi-threaded output must round-trip and be deterministic for repeated identical runs. `--jobsize=#` controls worker job granularity and accepts values such as 10KB, 16KB, 512K, 1M, 1MB, and 2M. `--target-compressed-block-size=#` controls approximate compressed block size, and hidden `-B#` controls input block/split size. All combinations tested with levels, fast mode, gzip, dictionaries, and empty/small inputs must remain valid.

At `-vv`, an ordinary named-file compression exposes the effective worker and job settings on standard error. An explicit positive `-T#` emits `Compressing with N worker threads ` plus a newline (including the plural `threads` for `N=1`), and the configuration line contains `--threads=N`. This applies unchanged when combined with `--fast=5`, `--ultra -20`, `--adapt`, `--rsyncable`, or explicit job size. A later thread option wins in both places: `-T4 -T2` reports 2, while `ZSTD_NBTHREADS=2` reports 2 when no CLI thread option overrides it. `-T4` and `-T8` therefore report `Compressing with 4 worker threads ` and `Compressing with 8 worker threads `, respectively. Canonicalized job sizes appear on that configuration line: `--jobsize=512K`, `--jobsize=1M`, and `--jobsize=2M` produce `--jobsize=524288`, `--jobsize=1048576`, and `--jobsize=2097152`, respectively, whether or not `-T4` is also present.

At the same display level, `-T0` announces its auto-detection policy before the worker line. Physical selection writes `Note: N physical core(s) detected ` plus a newline; `--auto-threads=logical` instead writes `Note: N logical core(s) detected ` plus a newline. The following worker line and `--threads=N` configuration field use that detected count. Explicit `--auto-threads=physical` and the default physical policy have the same wording.

Combining hidden `-B#` with `--single-thread` remains successful but, when diagnostics are enabled, writes exactly `Setting block size is useless in single-thread mode ` plus a newline to standard error before the ordinary compression status.

## Spec 14

`--long` enables long-distance matching with default window log 27; `--long=#` accepts supported numeric logs such as 18–27. A trailing character after a supported numeric prefix is ignored: `--long=20x` succeeds and selects the same setting as `--long=20`, producing identical frame bytes for the same input. The malformed token `--longX`, which is neither the Boolean `--long` form nor the `--long=#` form, exits 1 with `Incorrect parameter: --longX ` (including the trailing space) and then the complete short help. At `-vv`, the detailed `--zstd=` configuration line exposes the selected window log. In particular, `-vv -19 --long=23` includes `--zstd=wlog=23,clog=17,hlog=17,slog=5,mml=3,tlen=256,strat=9`.

`--rsyncable` creates stable rsync-friendly job boundaries and works with explicit threads/job size. It is incompatible with `--single-thread`, which exits 1 and writes exactly the following to standard error, including the trailing space on each line and the otherwise blank second line:

```text
zstd: error 1 : Rsyncable mode is not compatible with single thread mode 
 
```

At `-vv`, successful rsyncable compression includes the literal field `--rsyncable` on its configuration line, including when combined with `-T4`; it does not merely apply the behavior silently.

`--adapt` enables adaptive level selection and accepts `--adapt=min=N,max=N`, either bound alone, negative minimums, normal maximums, fast/ultra bounds, and thread counts. Minimum greater than maximum or malformed keys are usage errors using the Spec 2 malformed-option layout. In particular, `--adapt=invalid` exits 1 and writes `Incorrect parameter: --adapt=invalid ` (including the trailing space) plus a newline and the complete short help to standard error; `--adapt=min=999,max=1` behaves analogously with that complete token. Adaptive mode requires worker-thread compression. Combining it with `--single-thread` exits 1 and writes exactly the following to standard error, including the trailing space on each line and the otherwise blank second line:

```text
zstd: error 1 : Adaptive mode is not compatible with single thread mode 
 
```

With `-vv`, adaptive mode's configuration line spells the default bounds exactly `--adapt=min=-131072,max=22`; explicit bounds replace those values (for example, `--adapt=min=5,max=15`). Adaptive output must still be a valid deterministic-decodable stream for every input type.

`--asyncio` and `--no-asyncio` choose the I/O path without changing bytes or file semantics. `--rsyncable`, adaptive mode, long mode, job sizing, literal modes, and row matching must compose where no incompatibility is stated.

## Spec 15

By default, a frame made from a seekable named file records its exact uncompressed content size. `--content-size` explicitly requests it. `--no-content-size` omits it. For stdin, `--stream-size=#` supplies an exact declared size: consume exactly that much data and fail if the actual stream length differs. Whether stdin is shorter or longer than the declared size, the mismatch emits no compressed output, exits 11, and writes exactly `zstd: error 11 : Src size is incorrect ` plus a newline to standard error. `--size-hint=#` is only a tuning hint and does not impose equality. These settings must be reflected correctly in list output and must compose with adaptive, sparse, checksum, and threaded modes.

By default, native frames include and decoders validate the Zstandard frame checksum (the low 32 bits of XXH64 over the uncompressed content). `-C`, `--check`, and `--checksum` request it; `--no-check` omits it. List mode reports `XXH64` or `None` accordingly.

## Spec 16

`-t` and `--test` fully decode and validate each input, including format structure and checksum, but discard decoded bytes and create no output file. A single valid named file exits 0, preserves the input, and at normal diagnostic level left-aligns a short pathname in a 20-character field before reporting `: N bytes ` on standard error. For example, testing a 140-byte frame named `data.zst` writes exactly `data.zst            : 140 bytes ` plus a newline. For either implicit stdin or an explicit `-`, the displayed path is exactly `/*stdin*\`; for example, a stream decoding to 463474 bytes reports `/*stdin*\           : 463474 bytes ` plus a newline. A truncated named native frame exits 1 and writes exactly `PATH : Read error (39) : premature end ` plus a newline to standard error. Other corruption, invalid offsets/states, checksum failures, or trailing junk likewise exit nonzero with the applicable precise diagnostic.

Test mode uses the same cause-specific diagnostics as decompression. In particular, a plain-text `.zst` input writes exactly `zstd: PATH: unsupported format ` plus a newline. Corrupting only the checksum field of an otherwise valid checksummed frame writes exactly `PATH : Decoding error (36) : Restored data doesn't match checksum ` plus a newline, so the cause literally identifies `checksum` rather than using generic data-corruption wording. A malformed native frame whose header contains an unsupported frame parameter exits 1 and writes exactly `PATH : Decoding error (36) : Unsupported frame parameter ` plus a newline; it is not reported as generic data corruption.

Testing multiple files validates all of them and reports failure if any fails. At normal diagnostic level, a multi-file test reports successfully decoded members in an aggregate rather than printing their individual-file lines, including when another member fails. The summary has the form `N files decompressed : TOTAL bytes total `. For two valid files that each decode to 12 bytes, standard error is exactly `2 files decompressed :     24 bytes total ` plus a newline. If `bad.zst` is a truncated version of a frame and the following `ok.zst` decodes to 2 bytes, the invocation `-t bad.zst ok.zst` exits 1 and standard error is exactly:

```text
bad.zst : Read error (39) : premature end 
1 files decompressed :      2 bytes total 
```

`--rm` has no effect in test mode.

## Spec 17

`--format=gzip` produces genuine gzip/DEFLATE streams beginning `1F 8B`, with correct header, CRC32, length trailer, and end-of-stream handling. Independent `gzip -dc` must reproduce the input. The executable must decode independently generated gzip by its magic bytes even when the extension is absent or wrong, from files or stdin. Handle empty, tiny, binary, Unicode-named, large, and multiple gzip files. Gzip corruption/truncation is an error, and test mode validates gzip CRC/structure without extracting a file. A named-file gzip decoding diagnostic begins exactly `zstd: PATH: `. A file consisting of only the two gzip magic bytes `1F 8B` exits 1, creates no requested output, and writes exactly `zstd: PATH: unknown header ` plus a newline. A five-byte truncated gzip header instead writes exactly `zstd: PATH: premature gz end ` plus a newline. Malformed non-gzip contents use `zstd: PATH: unsupported format ` plus a newline.

An explicit format controls compression regardless of the output suffix. Gzip uses all ordinary file safety, `-k`, `--rm`, `-f`, `-c`, verbosity, and `-T` rules. A supplied `-D` is harmless and ignored for gzip compression. In normal `executable` mode, `--no-name` is unsupported and yields `Incorrect parameter`; gzip argv-name compatibility is described later.

## Spec 18

This build supports output formats only `zstd` and `gzip`. `--format=xz`, `--format=lz4`, and `--format=lzma` each exit 1. Their first standard-error lines are respectively `Incorrect parameter: --format=xz `, `Incorrect parameter: --format=lz4 `, and `Incorrect parameter: --format=lzma `, including the space before the newline, and each is followed immediately by the complete short help from Spec 3. Other unknown output formats use the same malformed-option layout. During decompression, detect xz/lzma and lz4 magic rather than treating them as native data. Xz emits `xz/lzma file cannot be uncompressed (zstd compiled without HAVE_LZMA) -- ignored`; lz4 emits a comparably clear unsupported-format error. Do not create an output on these failures.

## Spec 19

Multiple named inputs are processed independently, in command-line order, with a separate default output for each. Compression and decompression state must reset between files. With `-c`, concatenate the resulting compressed frames (compression) or uncompressed contents (decompression) to stdout in input order. A missing/invalid member makes the overall status nonzero but does not prevent valid independent members from being processed when safe.

Using one `-o` with multiple inputs is unsafe and requires explicit authorization: either `-f`/`--force` or an affirmative `y` response to the interactive confirmation. Standard error begins exactly `zstd: WARNING: all input files will be processed and concatenated into a single output file: OUTPUT ` plus a newline, then explains `The concatenated output CANNOT regenerate original file names nor directory structure. ` plus a newline. These two warning lines are emitted even when `-f` authorizes the operation; force suppresses only the prompt. Without force, the warning is followed by `Proceed? (y/n): `. An affirmative response processes the inputs and can exit 0; when no answer is supplied, it instead appends `Aborting... ` and exits 1. At normal verbosity, successful multi-file compression writes only its aggregate summary and no per-file status lines. For five 30-byte inputs that each produce a 43-byte frame, standard error is exactly `  5 files compressed : 143.33% (   150   B =>    215   B)` plus a newline.

Quiet mode uses a distinct noninteractive refusal rather than suppressing this safety diagnostic or printing the normal prompt. For `-q INPUT1 INPUT2 -o OUTPUT` without force, exit 1 and write exactly:

```text
Concatenating multiple processed inputs into a single output loses file metadata. 
Aborting. 
```

## Spec 20

Never overwrite an existing regular-file destination by default in noninteractive use. Exit 1 and preserve both source and destination. An existing output character device is not treated as a regular file needing overwrite confirmation: in particular, `-o /dev/null` opens and writes the device successfully without `-f`, including with adaptive mode, content-size/checksum settings, sparse mode, and memory limits. When standard input supplies no answer to the overwrite question for a regular destination, standard error uses exactly this two-line form, where `OUTPUT` is the destination spelling (there are two spaces after `overwritten` and one space on the otherwise blank second line):

```text
zstd: OUTPUT already exists; overwrite (y/n) ? Not overwritten  
 
```

`-f`/`--force` overwrites it. Never allow input and output to identify the same inode, including through a hard link. Such an invocation exits 1, does not destroy data, and writes exactly `zstd: Refusing to open an output file which will overwrite the input file ` plus a newline to standard error. An output pathname that is a directory exits 1 and writes exactly `zstd: OUTPUT: Is a directory` plus a newline.

`-f` also enables pass-through of an unrecognized input during decompression, access to links/special files, and terminal I/O. Explicit `--pass-through` copies a wholly uncompressed input unchanged in decompression mode; `--no-pass-through` rejects it. A recognized compressed stream is always actually decoded even when pass-through is enabled.

## Spec 21

Source files are preserved by default and by `-k`/`--keep`. `--rm` removes each source only after that source was successfully transformed to a named file. It removes a plain source after compression and a compressed source after decompression. It must not remove sources on errors, in test/list/benchmark modes, or when output is stdout/stdin-only. With multiple files, apply removal per successful file.

For named-file transformations, copy relevant source metadata to the output: permission bits (including executable/read-only bits as permitted), modification/access times, and ordinary ownership metadata when allowed. Do not let setuid/sticky bits or inability to set optional metadata corrupt an otherwise valid output. With `--trace-file-stat`, metadata operations are observable as specified later.

## Spec 22

`-r`/`--recursive` recursively enumerates regular files below every directory argument, including hidden files/directories, deeply nested trees, empty files, extensionless files, and Unicode names. A directory without `-r` is ignored as a directory and makes overall status nonzero if no valid file remains. Empty recursive trees succeed but warn `please provide correct input file(s) or non-empty directories -- ignored`. Multiple `-r DIR` occurrences accumulate all trees. Decompression recursively processes recognized compressed suffixes.

Do not follow directory symlinks by default, preventing cycles. Without `-f`, a directly requested ignored symlink writes exactly `Warning : PATH is a symbolic link, ignoring ` plus a newline; if it is the sole requested input, it exits 1. A symlink discovered during recursive traversal writes `Warning : PATH is a symbolic link, ignoring` with no space before the newline. Such a recursively discovered symlink, or a symlink that is one member of a multi-input invocation that successfully processes at least one regular file, is only a warning and does not change the successful overall status from 0. `--follow-links` is not supported: it exits 1 and writes `Incorrect parameter: --follow-links ` (including the space before the newline), followed immediately by the complete short help text from Spec 3, to standard error. It writes nothing to standard output and does not process the symlink or create its output. Preserve regular directory structure according to the selected output policy; empty directories need not be emitted because the artifact is a compressor, not an archive.

## Spec 23

`--output-dir-flat DIR` writes every result directly into `DIR` using only the input basename plus/removing the format suffix. The destination directory must be usable. An empty argument exits 1 with exactly `error: output dir cannot be empty string (did you mean to pass '.' instead?)`. If different inputs have the same basename, write `WARNING: Two files have same filename: NAME` plus a newline to standard error, where `NAME` is the unsuffixed input basename (for example, two `data.txt` inputs report `data.txt`, not `data.txt.zst`). With force, process in order and the last overwrites; otherwise collision safety applies.

`--output-dir-mirror DIR` creates needed subdirectories and mirrors the spelling of each input path below `DIR`: remove a leading `./`; retain ordinary relative components; for an absolute input, retain its path components below the new root without the filesystem-leading slash. Reject any mirrored path containing a parent `..` component so it cannot escape. This behavior applies symmetrically to compression/decompression and to hidden/nested files. If multiple output-directory options occur, the last wins. In particular, `--output-dir-flat od1 --output-dir-flat od2 file.txt` leaves `od1` empty and writes `od2/file.txt.zst`.

## Spec 24

`--filelist LIST` and `--filelist=LIST` add one input pathname for each LF-delimited line, preserving order and duplicates. A carriage return before LF is not stripped: in a CRLF list it remains the final character of each pathname, so ordinary files named without that carriage return are not found, each diagnostic shows that carriage return immediately after the visible pathname, and the invocation exits 1 without producing their outputs. Do not shell-expand lines or trim ordinary trailing spaces: those spaces are part of the filename. Empty lines therefore produce `can't stat  : No such file or directory`, set overall exit status 1, and do not stop valid lines from being processed. A truly empty list is an error containing `error reading`; a missing list is an error. Handle long lines, long lists, absolute and relative paths, and duplicate entries.

A 51-MiB file list is too large to load: reject it before treating its contents as pathnames, exit 1, leave standard output empty, and write exactly `zstd: error reading LIST ` plus a newline to standard error.

A directory line is not recursively expanded merely because it occurs in a list; report `is a directory -- ignored` unless independently selected under recursive semantics. `--filelist` works for compression and decompression and composes with flat output. Processing errors in some lines do not erase outputs made for valid lines.

## Spec 25

By default only regular files are processed. A requested ignored character device, block device, directory, missing path, or sole direct symlink makes overall status 1; an ignored symlink alongside a successfully processed regular batch member has the non-fatal status behavior in Spec 22. In compression mode, a character device, block device, or other immediately identifiable non-regular object writes exactly `zstd: PATH is not a regular file -- ignored ` plus a newline; a directory writes exactly `zstd: PATH is a directory -- ignored ` plus a newline. Symlinks use the distinct diagnostic in Spec 22. In decompression mode, output-name derivation occurs first: a special object such as `/dev/null` with no recognized suffix and no explicit output therefore uses the exact unknown-suffix diagnostic in Spec 8 rather than the non-regular-file diagnostic. These checks prevent hangs on immediately identifiable devices such as `/dev/zero` and `/dev/random`, but a named FIFO is opened for reading before it can be rejected: without a producer, ordinary compression of a FIFO remains blocked (and emits no diagnostic while blocked). `-f` permits intentional processing of suitable links/devices/FIFOs. Missing paths report `zstd: can't stat PATH : No such file or directory -- ignored` (shorter compatible `can't stat`/`No such file` wording is allowed where no exact line is requested).

`--exclude-compressed` skips inputs that already look compressed by known suffix/magic when compressing a batch; other files still produce outputs. Never recursively follow symlink loops.

## Spec 26

File decompression uses sparse output by default. `--sparse` explicitly enables it: sufficiently long all-zero runs are represented as filesystem holes while logical length and every byte remain exact, including zero runs at the start, middle, end, 32-KiB boundaries, unaligned ends, and multi-gigabyte sparse inputs. `--no-sparse` performs ordinary writes, making fewer/no holes but identical logical content. Sparse handling applies independently to multiple files. Default stdout automatically behaves as non-sparse. Explicit `--sparse` applies sparse seek handling to stdout: it can succeed when stdout is seekable, but if stdout is a non-seekable pipe and decompression finishes with a pending all-zero run, it exits 69 and writes exactly `zstd: error 69 : Final skip error (sparse file support) ` (including the trailing space) plus a newline to standard error. For a wholly zero input that consists of such a pending run, captured stdout is empty.

## Spec 27

`--train INPUT...` builds a genuine Zstandard dictionary from sample files. Default output name is `dictionary`; `-o` overrides it. On sufficient related samples it exits 0, reports `Save dictionary` and size information, and writes a nonempty dictionary usable by this executable and other compatible encoders/decoders. Default successful training reports its selected parameters on standard error on separate lines, including `k=DECIMAL` and `d=DECIMAL` (and, for fastcover selection, `f=DECIMAL`, `steps=DECIMAL`, `split=DECIMAL`, and `accel=DECIMAL`). A formatted dictionary begins with bytes `37 A4 30 EC` and contains a dictionary ID unless configured otherwise.

A bare `--train-fastcover` that leaves parameter selection to the optimizer likewise reports the selected values on separate standard-error lines: `k=DECIMAL`, `d=DECIMAL`, `f=DECIMAL`, `steps=DECIMAL`, `split=DECIMAL`, and `accel=DECIMAL`, before `Save dictionary`.

Support default training plus `--train-cover[=k=#,d=#,steps=#,split=#,shrink[=#]]`, `--train-fastcover[=k=#,d=#,f=#,steps=#,split=#,accel=#,shrink[=#]]`, and `--train-legacy[=s=#]`. The comma-separated keys must be complete `name=value` pairs except bare `shrink`; malformed/unknown text exits 1 with `Incorrect parameter`. Successful bare `--train-cover` reports all four selected fields, each on its own line: `k=DECIMAL`, `d=DECIMAL`, `steps=DECIMAL`, and `split=DECIMAL`. Explicit fastcover training reports both `Training on N samples of total size S` and `Testing on N samples of total size S` using the actual sample count and byte total; for ten 9,488-byte samples these lines are exactly `Training on 10 samples of total size 94880` and `Testing on 10 samples of total size 94880`. It also reports the completed size as `Constructed dictionary of size N` before the `Save dictionary` line; for a 4,096-byte result, that line is exactly `Constructed dictionary of size 4096`. `--maxdict=#` bounds output size (default 112640), `--dictID=#` sets the ID, `--split=#` can partition large samples, and `-r` permits recursive sample collection. Empty sample files may be skipped if sufficient data remains.

The initial sample-count check requires at least five sample files. Any ordinary set containing zero through four sample files fails without a dictionary and exits 14, regardless of the samples' byte sizes and regardless of a `--split=#` setting. Its standard error is exactly:

```text
!  Warning : nb of samples too low for proper processing !
!  Please provide _one file per sample_.
!  Alternatively, split file(s) into fixed-size samples, with --split=#
Error 14 : nb of samples too low
```

Failure to load training inputs exits 15. A dictionary exceeding the supported size fails with status 34. A requested maximum dictionary capacity below 256 bytes instead exits 1, creates no dictionary, and ends standard error with these lines:

```text
dictBufferCapacity must be at least 256
dictionary training failed : Destination buffer is too small 
```

Training progress follows verbosity controls. A single `-v` in training mode makes the first standard-error line `*** Zstandard CLI (64-bit) v1.6.0, by Yann Collet ***`, followed by details such as `Shuffling input files`, sample totals, and parameter search progress.

In training mode, `--memory=#` limits the sample bytes loaded for training rather than imposing the decompression-window behavior described in Spec 34. A manual one-megabyte limit begins its diagnostics with `!  Warning : setting manual memory limit for dictionary training data at 1 MB ` plus a newline. Oversized individual samples are capped to their first 131,072 bytes, announced by these three lines:

```text
!  Warning : some sample(s) are very large 
!  Note that dictionary is only useful for small samples. 
!  As a consequence, only the first 131072 bytes of each sample are loaded 
```

If the capped collection still exceeds the manual total, it trains on only that total and can succeed; a collection whose capped size is 6 MB under `--memory=1MB` reports `Training samples set too large (6 MB); training on 1 MB only...` plus a newline and writes a dictionary. Thus training 50 nonempty 780,000-byte samples with `--memory=1MB` succeeds rather than failing trainer-context initialization. Likewise, 20 nonempty 1,080,000-byte samples with `--memory=5MB --maxdict=4096` succeed and write a dictionary; after the per-sample cap their loaded total is already below the manual limit.

An empty sample is skipped when nonempty samples suffice. At `-v`, this is announced exactly as `Sample file 'PATH' has zero size, skipping...` plus a newline. Ten nonempty two-byte sample files are sufficient for the default optimizer: training exits 0, writes a nonempty dictionary, and warns that the sample data is too small for the target dictionary size. It must not take the trainer-context failure path merely because these ten samples total only 20 bytes. Other sample sets that pass the initial count check can still contain too little usable source data to initialize the default trainer. That case exits 1, creates no dictionary, and ends standard error with:

```text
Failed to initialize context
dictionary training failed : Src size is incorrect 
```

An optimizing cover search reports the number of parameter sets on standard error. In particular, a successful `--train-cover=d=8,steps=4 --maxdict=512` run with sufficient samples includes the exact line `Trying 5 different sets of parameters` before the selected `k=`, `d=`, `steps=`, and `split=` lines.

## Spec 28

`-D DICT` loads either a formatted trained dictionary or raw dictionary bytes for native compression/decompression. `--mmap-dict` and `--no-mmap-dict` choose loading method without changing results. Dictionary-compressed streams round-trip only with the correct dictionary unless `--no-dictID` deliberately omits the ID. Decoding a named dictionary-dependent frame with no dictionary or the wrong dictionary exits 1, creates no output, and writes `INPUT : Decoding error (36) : Dictionary mismatch ` plus a newline to standard error. The `Decoding error (36) :` prefix is mandatory.

A missing dictionary fails before transformation, exits 31, creates no output, and writes exactly `zstd: error 31 : Stat failed on dictionary file DICT: No such file or directory ` plus a newline to standard error; this wording applies in both compression and decompression mode.

A non-benchmark dictionary file larger than 33,554,432 bytes is rejected before transformation with exit 34 and no output. Standard error is exactly `zstd: error 34 : Dictionary file DICT is too large (> 33554432 bytes) ` plus a newline.

One dictionary may be reused for many inputs and with levels, threads, stdin/stdout, and binary/text data. `--no-dictID` omits the identifier but not dictionary-dependent coding. `-D` and `--patch-from` are mutually exclusive and exit 1 with exactly `error : can't use -D and --patch-from=# at the same time ` plus a newline as the entire standard error; no help text follows.

The dictionary pathname cannot also be an input pathname in the same compression invocation, even when a separate output was requested. Reject that identity before transformation with exit 1, create no output, and write exactly `zstd: cannot use PATH as an input file and dictionary ` plus a newline to standard error.

## Spec 29

List mode accepts seekable native `.zst` files only. With no pathname, it rejects stdin with exit 1, empty standard output, and exactly these two standard-error lines (including their trailing spaces):

```text
zstd: --list does not support reading from standard input 
No files given 
```

For a non-native named file of at least six bytes, exit 1 with empty standard error and put both the normal header and `File "PATH" not compressed by zstd ` (including the trailing space) on standard output. A non-native named file shorter than six bytes, including the five-byte contents `plain`, uses the same header and `not compressed by zstd ` line on standard output, then also writes `Error: reached end of file with incomplete frame ` plus a newline to standard error. A truncated putative frame uses that same output and diagnostic. A missing named list input exits 1, prints the normal header to standard output, and writes exactly `Error : PATH is not a file ` plus a newline to standard error. Standard (`-l`) output begins exactly:

```text
Frames  Skips  Compressed  Uncompressed  Ratio  Check  Filename
```

Each valid row's `Frames` column reports the total number of frames, including both data and skippable frames; `Skips` separately reports how many of that total are skippable. Thus a stream containing one data frame and one skippable frame reports `Frames` as 2 and `Skips` as 1. The remaining columns report total physical compressed bytes, known total uncompressed bytes, ratio `uncompressed/compressed` to three decimals, checksum kind (`XXH64` or `None`), and the supplied pathname. Format sizes using binary units: bytes as `B`, then KiB/MiB/GiB/TiB/PiB based on 1024, with about three significant digits. For multiple files, retain input order, print a dashed separator, then a computed `N files` total row. Any invalid member makes status 1 while valid rows remain.

The standard rows use the reference CLI's fixed column padding, including separate right-aligned number and unit fields. These are exact representative lines (where `PATH` stands for the supplied pathname):

```text
     1      0      32   B        19   B  0.594  XXH64  PATH
     1      0      40   B      1.76 KiB  45.000  XXH64  PATH
```

Do not instead close the padding before the number and attach the unit as `      32 B` or `        19 B`. For three 12-byte inputs whose frames are each 25 bytes, the exact total separator and row are:

```text
----------------------------------------------------------------- 
     3      0      75   B        36   B  0.480  XXH64  3 files
```

For the 332-byte `sample1.txt` fixture whose frame is 211 bytes and the 11-byte `short.txt` fixture whose frame is 24 bytes, the exact rows, separator, and two-file total are:

```text
     1      0     211   B       332   B  1.573  XXH64  sample1.txt.zst
     1      0      24   B        11   B  0.458  XXH64  short.txt.zst
----------------------------------------------------------------- 
     2      0     235   B       343   B  1.460  XXH64  2 files
```

With `-lv`, print per file:

```text
PATH 
# Zstandard Frames: N
# Skippable Frames: N        (only when nonzero)
DictID: N
Window Size: HUMAN (N B)
Compressed Size: HUMAN (N B)
Decompressed Size: HUMAN (N B)   (omit when unknown)
Ratio: N.NNNN                    (omit when size unknown)
Check: XXH64 0123abcd            (checksum value when available)
```

In `-lv` mode the metadata block is on standard output and ends with one additional blank line. Standard error contains the single-`-v` version banner `*** Zstandard CLI (64-bit) v1.6.0, by Yann Collet ***` plus a newline; for an otherwise successful one-file listing, it contains nothing else.

Report aggregate frame metadata correctly for empty files, dictionary frames, no-checksum frames, long-window frames, concatenated frames, and skippable frames. Empty content has ratio `0.000`. A multi-frame stream with unknown combined content size renders the entire `Uncompressed` and `Ratio` column region as spaces, not hyphen placeholders. For a two-frame, 40-byte checksummed stream with unknown content sizes, the exact row is:

```text
     2      0      40   B                       XXH64  PATH
```

## Spec 30

Benchmark mode is selected by `-b` or `-b#` (default level 3). It loads named files or, with no named file, generates a deterministic compressible lorem-like in-memory sample whose result label is exactly `Lorem ipsum`; piped standard-input bytes do not replace that generated sample. The default generated sample is exactly 10,000,000 bytes, including with `-T2`, `-T0`, `--single-thread`, `-v`, and `--priority=rt`. For this no-named-input benchmark only, hidden `-B#` also sets the total generated sample size to exactly `#` bytes, not merely an internal block size. Thus `-b1 -i0` with `-B10`, `-B11`, `-B15`, `-B16`, `-B20`, `-B25`, `-B50`, `-B500`, or `-B5000000` reports that respective number immediately before ` ->`; all of these tiny, odd, prime, power-of-two, and large sizes succeed. An explicit `-` is instead treated as an unloadable benchmark input and fails under the loading-error rule below. `-e#` benchmarks every level from the start through the end in ascending numeric order, `-i#` is minimum seconds (0 and 1 are accepted for quick runs), `-S` gives separate results per file rather than one consolidation, and `--split=#` benchmarks independent chunks. A consolidated multi-file result is labeled `N files`; with `-S`, each result instead identifies the corresponding input basename. `-P#` selects synthetic compressibility percentages, including 0, 50, 99, 100, 101, 150, and 200, and labels the generated result `Synthetic P%` (for example, `Synthetic 50%`, `Synthetic 70%`, `Synthetic 100%`, and `Synthetic 150%`). Outside benchmark mode, hidden `-P#` is accepted during ordinary named-file compression but does not replace or alter the input; for identical input and other options, `-P50` produces the same frame and ordinary status as omitting it. `-bd` is decode-only and requires a valid compressed stream whose decompressed size can be determined.

The generated bytes and resulting sizes are deterministic. With `-b1 -i0`, the 10,000,000-byte `Lorem ipsum` sample compresses to 3,239,077 bytes and the displayed ratio is exactly `x3.087`; levels 2 and 3 compress it to 3,130,527 bytes (`x3.194`) and 2,981,954 bytes (`x3.354`), respectively. At level 19 it compresses to 2,305,368 bytes and displays `x4.338`, so its level-19 ratio is greater than 3.0. With `--jobsize=1MB`, the generated sample size is instead exactly 1,048,576 bytes; at the default level it compresses to 315,504 bytes and displays `x3.323`.

Synthetic percentages at and above the sparse boundary generate highly compressible bytes rather than merely changing the label. At level 1, each of `-P100`, `-P101`, `-P150`, and `-P200` with the default 10,000,000-byte sample deterministically compresses to 405 bytes and displays `x24691.4`; `-P101` has that same size and ratio at levels 2, 3, and 5. At level 10, `-P150` compresses to 403 bytes and displays `x24813.9`. By contrast, level-1 `-P99` compresses to 928,907 bytes and displays `x10.77`, making the displayed ratio increase by more than 1,000 at the `-P100` boundary.

When the requested range end is below its start, do not run a descending range and do not skip the benchmark: benchmark the start level once. For example, `-b10 -e5` succeeds and emits the level marker `10#`.

Output the benchmark progress/result body on standard output, not standard error. At normal verbosity this includes `Loading FILENAME...` for every named input, generated-sample/file result rows, blank/progress lines, throughput, and a level marker after each completed level. In-place progress result rows begin with ` |-` (and a refreshed row can begin ` /-`) and spell the compression ratio in parentheses as `x` followed by a decimal, such as `(x0.654)`, `(x1.000)`, or `(x53.89)`. For a named input, the basename and colon are followed directly by the original byte count and arrow; do not insert a `level N,` field between them. For example, a 100,000-byte `input.txt` benchmarked with `-b -i0 -B1024` has a result row beginning ` |-input.txt         :    100000 ->`.

The completed level marker follows the final throughput row after a carriage return, without an intervening line feed; the marker then ends with a line feed. Consequently, splitting raw output only at `\n` leaves both the final `MB/s` text and that level's `#` marker in the same element. Nonnegative decimal level markers use a minimum width of two characters before `#`: levels 0 through 9 are ` 0#` through ` 9#`, whereas levels 10, 12, and 22 are `10#`, `12#`, and `22#`. Thus a rapid ascending benchmark range produces one such combined throughput/marker segment for every completed level. `-b0` ends in ` 0#`; a `-b1 -e3` range emits ` 1#`, then ` 2#`, then ` 3#`; other ordinary and ultra levels analogously use markers such as ` 9#`, `19#`, `20#`, and `22#`, while fast level 1 ends in `-1#`. Quiet `-q` still writes its two-line benchmark heading and result row to standard output, while suppressing the progress display and final `#` marker. Standard error is empty on an ordinary successful benchmark unless an option requests an auxiliary notice. `-T2` writes `Benchmarking using 2 threads ` plus a newline there, and `-T0` uses the analogous line with the detected thread count. A single `-v` writes the Spec 32 version banner and a `Benchmarking at level N using M threads ` line there. `--priority=rt` writes one `Note : switching to real-time priority ` line there. These auxiliary notices do not move the benchmark body away from standard output. Identify input filename or generated sample, level, original/compressed size or ratio, and compression/decompression throughput with decimal values followed by `MB/s`. `-D`, `--long`, ultra levels, target block size, job size, and dictionaries affect the benchmark without creating output files. Actual speeds are machine-dependent.

Missing or unloadable benchmark input, including a directory supplied as an input file, exits 15, leaves standard output empty, and writes exactly `Error loading files` to standard error with no final newline. An empty named input exits 20, leaves standard output empty, and writes exactly `not enough memory for srcBuffer` to standard error with no final newline. Decode-only benchmarking of a valid native frame whose content size is unknown exits 1: its `Loading PATH...` line is on standard output and standard error is exactly `Error 32 : Decompressed size cannot be determined: cannot benchmark ` plus a newline. Decode-only benchmarking of a native-magic file whose remaining bytes are corrupt also exits 1: its `Loading PATH...` line is on standard output and standard error is exactly `Error 32 : Error while trying to assess decompressed size: data may be invalid ` plus a newline. Unsupported non-zstd output formats also fail cleanly. Do not hang, even on tiny buffers, directories, or corrupt streams.

Benchmark dictionary loading for named inputs has its own error classes. A nonexistent dictionary pathname supplied as `-D DICT` with a named benchmark input exits 17, leaves standard output empty, and writes `error loading DICT : No such file or directory ` plus a newline followed immediately by `benchmark aborted` with no final newline. A dictionary of at most 64 MiB is loadable; a 65-MiB dictionary is rejected before benchmarking with exit 18, empty standard output, and `dictionary file DICT too large` on standard error. With `-v`, the version and benchmark-configuration lines precede that too-large diagnostic.

For a successful named-input benchmark with `-D DICT`, standard output announces the dictionary before the input with `Loading DICT...`, followed by `Loading INPUT...`; the dictionary-loading line is not omitted. For a generated-sample benchmark with no named input, a nonexistent dictionary pathname is ignored: `-b -i0 -D missing.dict` completes the ordinary generated `Lorem ipsum` benchmark with exit 0 and empty standard error, and does not print a dictionary-loading line.

## Spec 31

`--patch-from=REF` compresses a target relative to a reference and produces a genuine dictionary-dependent Zstandard frame; decoding the patch with the identical reference reconstructs the target exactly. Accept `--patch-from REF` as well. `--patch-apply REF` and `--patch-apply=REF` select decompression with the same reference semantics as `-d --patch-from=REF`. Patch mode works with named/stdin targets, output files/stdout, identical or dissimilar references, ordinary levels, long inputs, and adaptive mode.

The reference must exist and be readable. A missing reference exits 31 before transformation and writes exactly `zstd: error 31 : Stat failed on dictionary file REF: No such file or directory ` plus a newline to standard error. Patch mode permits only one target per invocation; multiple targets exit 1 with exactly `error : can't use --patch-from=# on multiple files ` plus a newline as the entire standard error. It cannot combine with `-D`, using the exact no-help diagnostic in Spec 28. When target input is stdin, `--stream-size` is required; absence emits no compressed output, exits 42, and writes exactly `zstd: error 42 : Using --patch-from with stdin requires --stream-size ` plus a newline to standard error. A stream-size mismatch is an error. Never silently fall back to ordinary compression when patch mode was requested.

## Spec 32

Diagnostic display level is cumulative. A single `-v` or `--verbose` already prints `*** Zstandard CLI (64-bit) v1.6.0, by Yann Collet ***` as the first standard-error line for an ordinary file operation, before its operation-status line, except that an environment-variable warning required by Spec 11 precedes the banner. Combined forms such as `-vfk` do the same. Repeated `-vv`, `-vvv`, etc. add configuration and detailed completion timing. `-q`/`--quiet` suppresses routine warnings/progress; `-qq` suppresses even ordinary errors and all progress (while the nonzero status remains). Binary stdout must never contain diagnostics.

File-to-file operations at default display level write progress/result information to standard error and leave standard output empty. In a successful single-file compression status, the input name is left-aligned to a minimum width of 20, followed by one space and a colon with no space between the colon and ratio; the ratio has two digits after the decimal point in a minimum-width six-character field; sizes use right-aligned six-character decimal fields followed by uppercase `B`; three spaces separate the percentage from the opening parenthesis; and the closing parenthesis is followed by one space and a newline. For example, compressing a 25-byte file named `input.txt` to a 38-byte frame writes exactly `input.txt            :152.00%   (    25 B =>     38 B, input.txt.zst) ` plus a newline. This same ordinary status layout follows successful `-z`, `-n`, `-C`, valid `--zstd=` parameters, `-T#`, `--auto-threads=logical`, named-input `--stream-size=#`, and ordinary-file `-P#`, and follows any level-reduction or environment warning required by Specs 10 and 11. Multiple-file operations use the aggregate-only layout in Spec 19. Pipe-to-pipe operations are silent by default.

`--progress` forces progress lines containing `Read:` and the input name (`stdin` for a stream). `--no-progress` suppresses those lines even when stderr is considered a terminal. `--fake-stderr-is-console` makes default terminal progress testable. `-qq` wins over forced progress. Hidden short `-p` performs the requested operation, then writes exactly `Press enter to continue... ` plus a newline to standard error and waits for an input newline before exiting; the prompt follows the ordinary operation status. The long spelling `--pause` is not an alias and follows the malformed-option rule in Spec 2.

## Spec 33

`--trace LOG` opens or creates `LOG` and appends trace records for both compression and decompression. A new trace file begins with exactly this CSV header and newline:

```text
Algorithm, Version, Method, Mode, Level, Workers, Dictionary Size, Uncompressed Size, Compressed Size, Duration Nanos, Compression Ratio, Speed MB/s
```

Every subsequent record has those twelve fields in that order. `Algorithm` is `zstd`, `Version` is the numeric value `10600`, and `Method` is exactly `compress` or `decompress`, never `compression` or `decompression`. The `Level` field of every decompression record is exactly the decimal value `0`, because decompression has no compression level. `Uncompressed Size`, `Compressed Size`, `Dictionary Size`, and `Workers` are decimal integer fields. A forced single-threaded small named-file compression records `Workers` as `0`. The uncompressed-size field records the actual byte count, including distinct values on records appended by operations on differently sized inputs. `Mode` is `single-pass` or `streaming` as selected by the operation; duration, ratio, and speed are measured values. Reusing the same path appends data records without repeating or replacing the header, so its size grows. Trace output works for named inputs, stdin, compression, decompression, levels, and thread settings.

Hidden `--trace-file-stat` writes file-system decision traces to standard error even with `-q`. Depending on the path, include calls in execution order using the exact prefix `Trace:FileStat: > ` and relevant forms: `UTIL_isLink(path)`, `UTIL_getFileSize(path)`, `UTIL_isSameFile(input, output)`, `UTIL_isDirectory(path)`, `UTIL_isRegularFile(path)`, `UTIL_isFdRegularFile(fd)`, `UTIL_isConsole(0|1)`, `UTIL_setFileStat(...)`, and `UTIL_utime(path)`. Synthetic stream labels contain `/*stdin*` or `/*stdout*`.

## Spec 34

Numeric byte-size options accept a decimal integer optionally followed by exactly `K`, `KB`, `KiB`, `M`, `MB`, or `MiB`; forms `1`, `1K`, `1KB`, `1KiB`, `1M`, `1MB`, and `1MiB` are valid. Larger practical G/T suffixes may be accepted where needed for memory/listing. Long-option values that reach the byte-size parser reject suffixes such as `LB`, `LiB`, `A`, or arbitrary trailing text with `error: only numeric values with optional suffixes K, KB, KiB, M, MB, MiB are allowed`. Detect arithmetic overflow: 32-bit-limited settings use `error: numeric value overflows 32-bit unsigned int `; `size_t` settings use `error: numeric value overflows size_t `.

`-M#`, `--memory=#`, and `--memlimit=#` set maximum decompression memory. Contrary to the help's “megabytes” description, the fused short form uses the ordinary byte-size parser: a bare `-M1` denotes one byte and `-M100` denotes 100 bytes, while `-M1M` denotes one MiB. Such tiny bare limits are below the accepted parameter range even for a small frame: `-M1` and `-M100` exit 11 with no decoded output and write exactly `zstd: error 11 : Parameter is out of bound ` plus a newline. A syntactically valid accepted limit below a larger frame's required window exits 1 with a `Decoding error (36) : Frame requires too much memory for decoding` diagnostic. A very large valid limit is accepted. Supplying a memory limit in compression mode is accepted as configuration unless a tested incompatible operation requires otherwise.

`--memlimit` is a 32-bit-limited setting. An overflowing decimal value exits 1 and writes only `error: numeric value overflows 32-bit unsigned int ` plus a newline; it does not append help. `--size-hint` and `--jobsize` are `size_t` settings. An overflowing value for either exits 1 and writes only `error: numeric value overflows size_t ` plus a newline to standard error; no short help follows. Fused malformed `-Mabc` follows short-option parsing instead of the generic byte-size diagnostic: it exits 1, starts standard error with `Incorrect parameter: -a `, and then prints the complete short help.

## Spec 35

Error handling must be transactional per output: do not leave a successful-looking partial destination after parse errors, missing files, invalid format, failed integrity, dictionary mismatch, or overwrite refusal. Continue safe independent batch members but return failure if any requested member failed. An ignored symlink accompanied by at least one successfully processed regular member is a warning rather than a failed member, as specified in Specs 22 and 25. Diagnostics go to standard error except help/version/list/benchmark conventions already specified.

Use these exact exit classifications where applicable: 1 for usage, missing/ignored ordinary inputs, unsupported formats, overwrite refusal, corrupt streams, and trainer-context initialization failure; 11 for out-of-bound memory; 14 for too few training sample files; 15 for failure loading ordinary benchmark/training data; 17 for a missing benchmark dictionary; 18 for a benchmark dictionary over 64 MiB; 20 for empty benchmark input; 31 for non-benchmark dictionary/reference stat/load failures; 34 for an oversized non-benchmark dictionary file or oversized dictionary training result; 42 for patch-from stdin without stream size; and 69 for failure to finalize a sparse skip on non-seekable output. A signal/crash, an unexpected timeout, or exit 0 after corruption is never acceptable; the intentional no-producer FIFO block in Spec 25 is the timeout exception.

Outside operation-specific exact diagnostics, common diagnostics must contain the offending pathname and a stable cause: `can't stat`, `No such file or directory`, `Permission denied`, `not a regular file -- ignored`, `is a directory -- ignored`, `unknown suffix`, `already exists`, `Dictionary mismatch`, `Data corruption detected`, `premature end`, `premature gz end`, or `unexpected end of file`. In particular, the missing named list-input sentence in Spec 29 uses its exact `is not a file` wording instead of a generic `No such file or directory` cause. Invalid parameters must not create files.

## Spec 36

Behavior may be selected by the basename used to invoke the same executable. `unzstd` implies decompression. `zstdcat` implies decompression to stdout plus pass-through, so a mixture of compressed and plain named files is emitted as the concatenated original contents. `zstdmt` implies `-T0`. Invocation through arbitrary other symlink names retains normal behavior.

A symlink named `gzip` selects gzip output by default and enables `--best` (level 9) and `-n`/`--no-name` (omit the original-name header field). Its snapshot-tested help is derived exactly from Spec 3 as follows:

- In both short and full help, change only `Usage: executable` to `Usage: gzip`.
- Immediately after the `--rm` option line, insert `  -n, --no-name                 Do not store original filename when compressing.` followed by two blank lines before the `-#` line.
- In full help only, immediately after the `--fast[=#]` line insert ``  --best                        Compatibility alias for `-9`.``

All other characters, spacing, sections, and final newlines are identical to Spec 3. Normal `executable --format=gzip --no-name` remains unsupported as stated in Spec 17.

Only `executable` is being specified. Any independent commands used by a harness—such as a data generator, `gzip`, `diff`, or filesystem utilities—are harness-provided and are not behaviors of `executable`.

## Spec 37

The executable must cope with all boundary patterns without special casing fixture names: zero length; one byte; short text; every possible byte including NUL; long repeated runs; incompressible pseudorandom data; mixed compressible/incompressible blocks; inputs around 32-KiB and 128-KiB boundaries; multi-megabyte files; sparse logical multi-gigabyte files; many files; and deep directory names. Compression ratios and metadata must derive from actual input bytes, never hard-coded paths or sizes.

All tuning options that are accepted must still produce genuinely decodable output. Repeated compression/decompression, chained streams, reuse of dictionaries, mixed native/gzip batches, and concurrent processes must not leak state between operations. Decoders must bound allocations according to parsed sizes/memory limits and reject malformed sizes rather than overflow or hang.
