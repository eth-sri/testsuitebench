# Clarified specification for `executable`

The required artifact is one executable file named exactly `executable`. It is a command-line implementation of BLAKE3 with the `b3sum` interface described below. All byte counts are counts before hexadecimal encoding. Unless a section says otherwise, a successful command exits 0, writes nothing to standard error, and terminates every textual output record with `\n`.

## Spec 1

The executable accepts this command shape, with options permitted before, after, or between file operands:

```text
executable [OPTIONS] [FILE]...

--keyed
--derive-key CONTEXT
-l LEN, --length LEN
--seek SEEK
--num-threads NUM
--no-mmap
--no-names
--raw
--tag
-c, --check
--quiet
-h, --help
-V, --version
```

The forms `--length=LEN`, `--seek=SEEK`, and `--num-threads=NUM` are also accepted. `LEN`, `SEEK`, and `NUM` are unsigned decimal integers. A leading `+` is accepted as part of an unsigned value in both separated and `=` forms; for example, `--num-threads +2`, `--num-threads=+2`, `--length=+1`, and `--seek=+1` are valid. `LEN` defaults to 32 bytes and `SEEK` to zero. Values through at least `LEN=100000`, `SEEK=18446744073709551615` (the maximum unsigned 64-bit value), and `NUM=100` must work. A missing option value or syntactically invalid command line exits 2. In particular, a non-decimal value produces exactly the applicable diagnostic below on standard error:

```text
error: invalid value 'abc' for '--length <LEN>': invalid digit found in string

For more information, try '--help'.
```

The `--seek` and `--num-threads` variants substitute `--seek <SEEK>` and `--num-threads <NUM>` respectively. `--version` prints exactly `b3sum 1.8.4\n` and exits 0. Both `--help` and `-h` exit 0, write nothing to stderr, identify the command by its artifact name rather than by the version-product name, and begin with exactly `Usage: executable [OPTIONS] [FILE]...\n`. The word `b3sum` does not occur in either help output. Both help forms describe BLAKE3 file/checkfile processing and list the interface above; the long form uses expanded descriptions and the short form uses one-line summaries.

## Spec 2

Without file operands, normal hashing reads all bytes from standard input and labels that input `-`. An explicit `-` operand has the same meaning. Inputs and file contents are arbitrary bytes, including empty data, NULs, non-UTF-8 data, and inputs much larger than an internal buffer. Process operands in their given order and emit one result per operand. If `-` occurs more than once, the first occurrence consumes stdin and each later occurrence sees EOF and therefore hashes the empty byte string. A mixture of files and `-` is likewise processed in operand order.

Regular files, readable special files such as `/dev/null`, and symlinks to readable regular files are read to EOF; symlinks are followed. Do not hash a pathname, file metadata, or a symlink target string in place of its contents. Empty stdin, an empty file, and `/dev/null` all have the default digest:

```text
af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262
```

Hashing must be streaming-safe and correct at every size, especially around 63/64/65-byte blocks, 1023/1024/1025-byte chunks, powers of two, non-powers of two, and inputs of tens of megabytes.

## Spec 3

All BLAKE3 arithmetic below is on unsigned 32-bit words with addition modulo `2^32`. Bytes are converted to/from words in little-endian order. The eight-word initialization vector is:

```text
6A09E667 BB67AE85 3C6EF372 A54FF53A
510E527F 9B05688C 1F83D9AB 5BE0CD19
```

The block length is 64 bytes, the chunk length is 1024 bytes, and these bit flags are used:

```text
CHUNK_START        = 1
CHUNK_END          = 2
PARENT             = 4
ROOT               = 8
KEYED_HASH         = 16
DERIVE_KEY_CONTEXT = 32
DERIVE_KEY_MATERIAL= 64
```

The compression function takes an eight-word chaining value `cv`, sixteen message words `m`, a 64-bit counter, a block byte length, and flags. Initialize its sixteen-word state as:

```text
state[0..7]   = cv[0..7]
state[8..11]  = IV[0..3]
state[12]     = low 32 bits of counter
state[13]     = high 32 bits of counter
state[14]     = block length
state[15]     = flags
```

Define `G(a,b,c,d,x,y)` as:

```text
state[a] = state[a] + state[b] + x
state[d] = rotr32(state[d] XOR state[a], 16)
state[c] = state[c] + state[d]
state[b] = rotr32(state[b] XOR state[c], 12)
state[a] = state[a] + state[b] + y
state[d] = rotr32(state[d] XOR state[a], 8)
state[c] = state[c] + state[d]
state[b] = rotr32(state[b] XOR state[c], 7)
```

One round calls:

```text
G(0,4, 8,12,m[ 0],m[ 1])  G(1,5, 9,13,m[ 2],m[ 3])
G(2,6,10,14,m[ 4],m[ 5])  G(3,7,11,15,m[ 6],m[ 7])
G(0,5,10,15,m[ 8],m[ 9])  G(1,6,11,12,m[10],m[11])
G(2,7, 8,13,m[12],m[13])  G(3,4, 9,14,m[14],m[15])
```

Perform seven rounds. Between rounds, permute the message words to:

```text
m[2],m[6],m[3],m[10],m[7],m[0],m[4],m[13],
m[1],m[11],m[12],m[5],m[9],m[14],m[15],m[8]
```

After round seven, compression returns sixteen words: words 0 through 7 are `state[i] XOR state[i+8]`; words 8 through 15 are `state[i+8] XOR cv[i]`.

## Spec 4

Model an intermediate BLAKE3 `Output` as `(input_cv, block_words, counter, block_len, flags)`. Its chaining value is the first eight words returned by compression with those fields. Its root/XOF bytes are the concatenation, for output block counters `0,1,2,...`, of all sixteen little-endian words from compression using the same `input_cv`, `block_words`, and `block_len`, but replacing the stored counter by the output block counter and OR-ing `ROOT` into the flags.

To form a chunk output, split that chunk into 64-byte blocks, using one zero-length block for an empty input. Zero-pad the final partial block only for conversion to sixteen words. Begin with the mode's eight key words. For every non-final block, compress and retain its first eight words as the next chaining value. The final block becomes the chunk's `Output`, using the chaining value that precedes it. Every block uses the chunk's zero-based index as counter and the actual number of bytes in that block as block length. OR `CHUNK_START` on the first block and `CHUNK_END` on the final block, in addition to the mode flags.

To form a parent output from left and right subtree chaining values, use the mode key words as `input_cv`, the eight left CV words followed by the eight right CV words as the block, counter 0, block length 64, and `mode_flags | PARENT`.

To obtain the root output for input longer than one chunk, recursively split it at the largest power-of-two multiple of 1024 bytes that is strictly smaller than the input length. Build the left and right subtree outputs using their true global zero-based chunk indices, take both chaining values, and form their parent output. For at most 1024 bytes, the chunk output itself is the root output. This definition fixes the tree shape for exact powers of two and all partial final chunks.

Finally, generate the root/XOF byte stream as above and return exactly `LEN` bytes beginning at byte offset `SEEK`. Seeking is over the XOF output, not over the input. It must work across 64-byte output-block boundaries and at the maximum 64-bit seek value. A zero length returns no digest bytes. With ordinary hexadecimal formatting, encode bytes as exactly two lowercase hexadecimal digits each. As basic checks, unkeyed BLAKE3 of `foo` begins with `04e0bb39f30b1a3feb89f536c93be15055482df748674b00d26e5a75777702e9`, and unkeyed BLAKE3 of `test` begins with `4878ca0425c739fa427f7eda20fe845f6b2e46ba5fe2a14df5b1e32f50603215`.

## Spec 5

There are three mutually exclusive hash modes:

- Ordinary mode uses the IV as its key words and mode flags zero.
- `--keyed` reads the key from standard input before processing any file. The key must be exactly 32 bytes and is interpreted as eight little-endian words; mode flags are `KEYED_HASH`. The same key is reused independently for every file operand.
- `--derive-key CONTEXT` UTF-8 encodes the context exactly, including empty, long, and non-ASCII contexts. First hash those context bytes with IV key words and `DERIVE_KEY_CONTEXT`, taking the first 32 root-output bytes as a context key. Interpret that key as eight little-endian words, then hash each input independently with those words and `DERIVE_KEY_MATERIAL`.

In keyed mode stdin is reserved for the key, so there must be a real file operand. An explicit `-` produces `b3sum: -: Cannot open `-` in keyed mode\n` on stderr, causes status 1, and produces no result for it. A short key produces exactly `Error: expected 32 key bytes from stdin, found N\n`; a key longer than 32 bytes produces exactly `Error: read more than 32 key bytes from stdin\n`. These are status-1 errors with no stdout.

`--keyed --derive-key test FILE` is a status-2 command-line conflict and prints:

```text
error: the argument '--keyed' cannot be used with '--derive-key <CONTEXT>'

Usage: executable --keyed <FILE>...

For more information, try '--help'.
```

## Spec 6

In ordinary textual output, each successfully hashed operand is one of:

```text
<lowercase hex output>  <display name>
<lowercase hex output>                         # with --no-names
BLAKE3 (<display name>) = <lowercase hex output> # with --tag
```

The display name is the operand spelling, not a canonicalized path; stdin is `-`. Preserve relative and absolute path spellings and spaces. There are exactly two spaces between a digest and its name in standard format. Every record has a trailing newline, including an empty digest: `--length 0` on stdin outputs exactly `  -\n`; with `--no-names` it outputs only `\n`. `--tag`, `--length`, `--seek`, keyed/derive mode, thread selection, and file count compose without changing these layout rules. `--no-names` takes away both the name and its separator.

`--raw` instead writes exactly the selected digest bytes directly, without hex encoding, a name, or a newline. It takes precedence over `--tag` formatting. Raw mode permits at most one effective input; passing two or more file operands exits 1, writes no digest, and writes exactly `Error: Only one filename can be provided when using --raw\n` to stderr.

## Spec 7

On Unix, display a pathname by decoding its native bytes as UTF-8 with invalid sequences replaced by U+FFFD. Do not truncate long names. For standard named output, if the resulting name contains backslash, LF, or CR, escape every occurrence in one left-to-right pass: `\` becomes `\\`, LF becomes the two characters `\n`, and CR becomes `\r`. Prefix the entire output record with one additional backslash escape marker before the digest. For example, a file operand named `abc` is:

```text
<hash>  abc
```

while an operand whose name consists of `a`, LF, `b`, backslash, `c`, CR is:

```text
\<hash>  a\nb\\c\r
```

This applies at all positions, to adjacent/mixed occurrences, and in keyed mode. `--no-names` emits just the hash and therefore emits neither escapes nor marker.

## Spec 8

`--length` selects any prefix length of the XOF stream and `--seek` selects its starting point. Thus a result at seek `s` and length `n` is byte-for-byte the slice `[s:s+n]` of a long enough result at seek zero. This property applies identically to ordinary, keyed, and derive-key modes, to stdin and files, and to raw, standard, no-name, and tag encodings. Do not merely repeat the 32-byte digest to implement extended output. Outputs are tested at lengths from 0 and 1 through 100000 and at offsets including 1, 10, 32, 63, 64, 65, 1000, 1024, 2048, one million, one billion, and the maximum unsigned 64-bit value.

## Spec 9

`--num-threads NUM` and `--no-mmap` select implementation strategies only; neither may change bytes, formatting, ordering, or errors. `NUM=0` is valid and means automatic/environment-selected parallelism. Positive values including 1, 2, 4, 8, and 100 are valid. The implementation need not actually create threads or use memory mapping, but it must accept these options and correctly process both small and large inputs in every tested combination. `--no-mmap` may safely ignore `--num-threads` as a strategy choice. State must be reset between input operands, while the chosen key or derivation context remains the same.

## Spec 10

For normal hashing, failure to open or read one operand does not prevent later operands from being attempted. Successful operands still produce stdout records in their relative operand order. Any such failure makes the final exit status 1. Write one stderr line per failed operand in this form:

```text
b3sum: <display name>: <operating-system error text>
```

On the evaluated Linux environment, a nonexistent file or broken symlink uses `No such file or directory (os error 2)` and a directory uses `Is a directory (os error 21)`. Therefore the exact examples include:

```text
b3sum: /nonexistent/file.txt: No such file or directory (os error 2)
b3sum: /tmp: Is a directory (os error 21)
```

Readable symlinks are followed. Error output is newline terminated. A permission error, where the environment permits testing it, similarly reports `Permission denied` and exits 1.

## Spec 11

`--check` (or `-c`) switches operands from data files to checksum-list files. With no operand it reads one checksum list from stdin; `-` explicitly denotes such a stdin list. Multiple list files are supported and processed in order, including the same list more than once. An empty list is a successful no-op. Checksum lines can use either of these forms, mixed in the same list:

```text
<64 lowercase hex digits>  <path>
BLAKE3 (<path>) = <64 lowercase hex digits>
```

For standard form, the two spaces immediately after the 64 digits are structural. One space is invalid. If there are three spaces, the third is the first character of the pathname. Spaces, repeated spaces, and tabs later in the pathname are literal. The path must be nonempty. In BSD/tag form, use the text inside `BLAKE3 (` and `) = ` as the path. Only a 32-byte/64-digit ordinary BLAKE3 digest is accepted in check mode; uppercase or any non-lowercase-hex byte is invalid. Accept LF, CRLF, and a final line without a newline. A blank line is an error, not something to skip.

Paths named by a checksum line are opened relative to the executable's current working directory, not relative to the checksum-list file. Absolute paths stay absolute. On Linux, backslashes in an unescaped path are literal filename characters and Windows-looking paths are not normalized. Symlinks are followed.

## Spec 12

An escaped standard checksum line starts with one `\` marker immediately before the 64-digit hash. On such a line, decode only these pathname escapes: `\\` to one backslash, `\n` to LF, and `\r` to CR. A trailing backslash or any other escape is invalid. Reject a decoded NUL with `Null character in path`, reject U+FFFD with `Unicode replacement character in path`, and reject an empty path with `empty file path`.

Rendering a pathname in a check result follows the syntax of that checksum entry. For an escaped standard entry, render the decoded pathname with the same escaping rules as normal output and prefix the entire status line with `\`. Thus an escaped success has this form:

```text
\<escaped path>: OK
```

This escaping and unescaping must round-trip arbitrary mixtures and positions of the three supported characters. For an unescaped standard entry, render the parsed pathname literally and do not add a marker or double its backslashes, even when the pathname contains backslashes. Thus an unescaped entry for `C:\folder\file` produces `C:\folder\file: OK\n`. Windows-looking paths remain Linux pathnames; an unreadable unescaped `C:\path\to\file.txt` produces `C:\path\to\file.txt: FAILED (No such file or directory (os error 2))\n`. An unescaped tag entry likewise has no escape marker added to its result.

## Spec 13

For each valid checksum entry, compute ordinary BLAKE3 with 32 output bytes, beginning at the `--seek` offset selected for the command (zero when `--seek` is absent). Emit to stdout, in line order:

```text
<display path>: OK
<display path>: FAILED
<display path>: FAILED (<operating-system error text>)
```

Use `OK` when the digest matches, plain `FAILED` for a mismatch, and the parenthesized form when the referenced path cannot be read. Continue after every mismatch, missing file, and malformed line. `--quiet` suppresses only `OK` lines; failures and diagnostics remain.

Each mismatch, unreadable path, blank line, or malformed line counts as one failed computed checksum. If the count is nonzero, exit 1 and, after processing all input, write exactly one summary to stderr:

```text
b3sum: WARNING: 1 computed checksum did NOT match
b3sum: WARNING: N computed checksums did NOT match
```

Use the singular form only for one. With zero failures, exit 0 and do not write a summary.

## Spec 14

Checksum-list parse diagnostics go to stderr as `b3sum: <reason>\n`, produce no stdout status for that line, count as failures, and precede the final warning within stderr. Required reasons are:

```text
Empty line
Invalid check line format
Invalid hash length
Invalid hex
Invalid backslash escape
empty file path
Null character in path
Unicode replacement character in path
```

Distinguish format from hash validation: a line without a recognized structural form is `Invalid check line format`; a recognized hash field whose encoded length is other than 64 bytes is `Invalid hash length`; and a field exactly 64 bytes long that contains anything other than lowercase ASCII hexadecimal digits, including uppercase, `z`, punctuation, or non-ASCII bytes, is `Invalid hex`. In particular, 64 U+00E9 characters encoded as UTF-8 occupy 128 bytes and produce `Invalid hash length`, while 32 such characters occupy 64 bytes and produce `Invalid hex`. Every bad line is reported separately. For a missing referenced file, the diagnostic belongs on stdout as `path: FAILED (No such file or directory (os error 2))`, rather than as a parse diagnostic.

## Spec 15

Check mode conflicts with `--keyed`, `--derive-key`, `--length`, `--raw`, `--tag`, and `--no-names`. Such errors exit 2 without hashing. The diagnostic form is:

```text
error: the argument '--check' cannot be used with '--OPTION'

Usage: executable --check [FILE]...

For more information, try '--help'.
```

Use `--derive-key <CONTEXT>` and `--length <LEN>` in place of `--OPTION` for those value-taking options. If `--raw` appears before `--check`, the first line is instead `error: the argument '--raw' cannot be used with '--check'` and the usage line is `Usage: executable --raw [FILE]...`. When the invocation also supplies a checksum-file operand, the tested parser renders the check-led usage with required angle brackets: `Usage: executable --check <FILE>...`. All blank lines shown above are literal.

`--quiet` is meaningful with check mode and is not a conflict. `--seek` changes the 32-byte XOF segment used for verification to begin at the requested offset. For example, with file contents `x`, `--check --seek 99 --num-threads=0 --no-mmap` accepts checksum `735346fb7a91417776e1ac03b26699484ecc2b754111b9474f7d0252846ec1a0` and rejects the ordinary seek-zero checksum. `--num-threads` and `--no-mmap` remain strategy choices and do not otherwise change verification.

## Spec 16

The implementation must be deterministic and content-based across all input routes and strategy flags. In particular:

- Reading identical bytes from a regular file, stdin, a symlink, with `--no-mmap`, or with any accepted thread count gives identical selected XOF bytes.
- Each operand is a fresh hash operation; no bytes or chaining state leak from a previous file.
- The same keyed key or derive context applies independently to every operand.
- A shorter length at the same seek is an exact prefix of a longer length, and a seeked result agrees with the corresponding unseeked slice.
- Text hashes are lowercase; raw results are their decoded bytes exactly.

These invariants apply to empty input and all block, chunk, page-sized, and large-file boundaries described above.
