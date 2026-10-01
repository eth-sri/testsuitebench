# Clarified specification for the `executable` command

This document is the complete behavioral specification for the command-line
program.  The program is a pigz-compatible compressor named `executable`.
Unless a section explicitly says otherwise, byte data is arbitrary (including
empty input, NUL bytes, every byte value, UTF-8 text, and multi-megabyte input),
and processing must preserve it exactly through a compress/decompress
round-trip.  “Success”, “warning/failure”, and “invocation error” below mean
exit statuses 0, 1, and 22 respectively.

## Spec 1: Invocation, modes, and defaults

The interface is:

```text
executable [options] [files ...]
```

Compression is the default mode when the invocation basename is not `unpigz`.
When the same program is invoked through a path whose basename is exactly
`unpigz`, decompression is the default even without a decompression option. For
example, invoking an `unpigz` symlink on `test.txt.gz` creates `test.txt` and,
absent `-k`, removes `test.txt.gz`. `-d`, `--decompress`, and `--uncompress`
select decompression explicitly. `-l`/`--list` selects listing and
`-t`/`--test` selects integrity testing. Listing and testing may be combined:
on valid input, `-l -t` prints the listing and verifies the data; the behavior
on failed validation is specified in Spec 23.

If there are no file operands, or an operand is exactly `-` before a `--`
separator, input is read from standard input and processed output is written to
standard output. This applies to implicit compression as well as explicit
`-c`. Multiple file operands are processed from left to right. Output sent to
standard output for multiple operands is concatenated in that same order.

`-c`, `--stdout`, and `--to-stdout` send every processed result to standard
output and never delete or modify an input file. Binary compressed data must
never be mixed with messages on standard output.

## Spec 2: Exact help screen

`-h` and `--help` exit successfully, write nothing to stdout, and write exactly
the following UTF-8 text (including its final newline) to stderr:

```text
Usage: pigz [options] [files ...]
  will compress files in place, adding the suffix '.gz'. If no files are
  specified, stdin will be compressed to stdout. pigz does what gzip does,
  but spreads the work over multiple processors and cores when compressing.

Options:
  -0 to -9, -11        Compression level (level 11, zopfli, is much slower)
  --fast, --best       Compression levels 1 and 9 respectively
  -A, --alias xxx      Use xxx as the name for any --zip entry from stdin
  -b, --blocksize mmm  Set compression block size to mmmK (default 128K)
  -c, --stdout         Write all processed output to stdout (won't delete)
  -C, --comment ccc    Put comment ccc in the gzip or zip header
  -d, --decompress     Decompress the compressed input
  -f, --force          Force overwrite, compress .gz, links, and to terminal
  -F  --first          Do iterations first, before block split for -11
  -h, --help           Display a help screen and quit
  -H, --huffman        Use only Huffman coding for compression
  -i, --independent    Compress blocks independently for damage recovery
  -I, --iterations n   Number of iterations for -11 optimization
  -J, --maxsplits n    Maximum number of split blocks for -11
  -k, --keep           Do not delete original file after processing
  -K, --zip            Compress to PKWare zip (.zip) single entry format
  -l, --list           List the contents of the compressed input
  -L, --license        Display the pigz license and quit
  -m, --no-time        Do not store or restore mod time
  -M, --time           Store or restore mod time
  -n, --no-name        Do not store or restore file name or mod time
  -N, --name           Store or restore file name and mod time
  -O  --oneblock       Do not split into smaller blocks for -11
  -p, --processes n    Allow up to n compression threads (default is the
                       number of online processors, or 8 if unknown)
  -q, --quiet          Print no messages, even on error
  -r, --recursive      Process the contents of all subdirectories
  -R, --rsyncable      Input-determined block locations for rsync
  -S, --suffix .sss    Use suffix .sss instead of .gz (for compression)
  -t, --test           Test the integrity of the compressed input
  -U, --rle            Use run-length encoding for compression
  -v, --verbose        Provide more verbose output
  -V  --version        Show the version of pigz
  -Y  --synchronous    Force output file write to permanent storage
  -z, --zlib           Compress to zlib (.zz) instead of gzip format
  --                   All arguments after "--" are treated as files
```

Help takes precedence over every later argument before `--`; for example,
`--help --not-a-real-option` still produces this help and status 0. A help-like
word after `--` is an ordinary filename and does not trigger help.

## Spec 3: Version and license output

`-V` and `--version` exit 0, write nothing to stderr, and write exactly:

```text
pigz 2.8
```

With one or more `-v` options before `-V`, the first line remains `pigz 2.8`
and a subsequent line has the form `zlib X.Y.Z`, reporting the version of the
zlib-compatible implementation used. The output ends in a newline.

`-L` and `--license` exit 0, write nothing to stderr, and begin stdout with
exactly these four lines:

```text
pigz 2.8
Copyright (C) 2007-2023 Mark Adler
Subject to the terms of the zlib license.
No warranty is provided or implied.
```

Additional license text may follow. It must identify Mark Adler and the zlib
license.

## Spec 4: Option parsing and aliases

Options are interpreted before processing any operands. Short options may be
clustered (`-dc`, `-dk`, `-kfK`, `-kfq`, `-9ck`) and a value may immediately
follow its short option (`-p4`, `-b64`) or be the next argument. `-S` is an
exception: its suffix must be the next argument, separated by whitespace.
Thus `-S .zzz` is valid, whereas `-S.zzz` is an invocation error with status
22 and `executable: abort: invalid usage: -S must be followed by space` on
stderr. The token `-11` is one compression level, not two `-1` options. Option
recognition continues among ordinary operands until `--` is seen. After `--`,
every token, including `-`, `-q`, and `--help`, is a literal filename. Before
`--`, `-` is the stdin marker.

Supported long aliases are the aliases printed in the help screen, plus
`--uncompress`, `--to-stdout`, and `--silent`. The following short aliases are
also required: `-T` is identical to `-m`; `-Z` is recognized only to reject
unsupported LZW output as specified in Spec 25; and `-a` is recognized only to
reject unsupported ASCII conversion.

When state-setting options conflict, normal left-to-right “last setting wins”
semantics apply. In particular this applies to compression levels and the
metadata switches described in Spec 17. Informational options terminate option
processing successfully.

## Spec 5: Standard-input and standard-output operation

With no operands, `executable`, `executable -c`, and `executable -` compress
stdin to stdout. `executable -d` or `-dc` decompresses stdin to stdout. These
operations must work for empty input, one byte, binary data, Unicode-encoded
bytes, and large streams. Empty input in compression mode still produces a
nonempty valid wrapper; decompressing it yields zero bytes.

When `-c` names a regular input file, that file remains present and unchanged
and no sibling output file is created. `-k` and `-f` do not change this rule.
No routine informational text is emitted for a successful non-verbose stream
operation.

## Spec 6: Default gzip representation

The default output is a standards-compliant gzip member. It starts with bytes
`1f 8b`, uses compression method 8 (deflate), and ends with the little-endian
CRC-32 and uncompressed input length modulo 2^32. Standard gzip readers,
including Python's `gzip` and the `gunzip` command, must decode it and validate
the trailer.

The fixed header is the standard ten-byte gzip header. Optional original-name
and comment fields follow it in that order and are each NUL-terminated. File
compression stores basename and mtime by default; pipe input has no source
filename or source mtime. The precise metadata switches are in Spec 17.

The implementation must produce actual deflate compression rather than merely
store all input: repetitive inputs must become substantially smaller, while
arbitrary/incompressible input must still round-trip. An empty file produces a
small valid gzip member (normally between 10 and 50 bytes).

## Spec 7: Compression levels

`-0` through `-9` and `-11` are accepted. The default is `-6`. `--fast` means
`-1`, and `--best` means `-9`; for identical input and other options each alias
pair produces byte-identical output. Level 0 stores without compression. Levels
1 through 9 provide progressively more effort and, on highly compressible test
data, the sizes for levels 1, 3, 5, 7, and 9 are non-increasing; level 9 is
materially smaller than level 1. Outputs for levels 1 and 9 must differ.

All levels work with gzip, zlib, ZIP, stdin, files, binary data, and thread
selection. Only 0 through 9 and 11 are valid numeric levels; tokens such as
`-10`, `-15`, `-99`, and `-9abc` are invocation errors.

## Spec 8: Blocks and process count

`-b n`/`--blocksize n` sets the input block size to `n` KiB; the default is
128 KiB and the minimum is exactly 32 KiB. Values 32, 64, 128, 256, 512, and
1024 are valid. Block size changes the actual deflate blocking: for suitably
repetitive multi-block data, 512 KiB blocks compress smaller than 128 KiB,
which compress smaller than 32 KiB, and different block sizes produce different
bytes.

`-p n`/`--processes n` allows up to `n` compression threads. `n=1` avoids
compression worker threads. Positive counts including 1, 2, 4, 8, 100, and
999 are valid even when larger than the number of online CPUs. The default is
the online CPU count, or 8 if it cannot be determined. Thread count must not
alter the byte sequence for fixed input, block size, level, format, and
metadata; it only changes execution strategy. Thread resources may be reused
between files.

The compressor divides input into blocks and emits results in input order.
Ordinary blocks use the preceding block's last 32 KiB as a preset dictionary.
Each partial raw-deflate stream ends at a byte boundary using a sync-flush
empty stored block, allowing the partial streams to concatenate into one
deflate stream.

## Spec 9: Independent, rsyncable, strategy, and synchronous modes

`-i`/`--independent` prevents one block from using a preceding block as a
dictionary. Between independently decodable blocks it emits the nine-byte
marker `00 00 ff ff 00 00 00 ff ff`. On multi-block repetitive input this is
larger than dependent compression. It works with one or many threads, custom
block sizes, levels, rsyncable mode, Huffman-only mode, and RLE mode.

`-R`/`--rsyncable` chooses deflate block boundaries from the input so local
input changes remain local in the compressed stream. It produces valid data
for empty, one-byte, binary, repetitive, file, and stdin input, and combines
with `-i`, `-H`, `-U`, comments, and custom block sizes. Changing the maximum
block size on a multi-block rsyncable input changes the output.

`-H`/`--huffman` selects zlib's Huffman-only strategy. It usually produces a
larger result than the default on ordinary repetitive text. `-U`/`--rle`
selects zlib's run-length strategy and compresses long runs effectively. Both
strategies produce fully interoperable streams and accept levels 1 through 9.

`-Y`/`--synchronous` makes a regular output file durable (flush and synchronize
it) before reporting success. It does not change the bytes. It is also valid
with `-k` and with stdout; inability to synchronize a pipe is not an error.

## Spec 10: Level 11 (Zopfli) behavior

Level `-11` uses Zopfli-style exhaustive deflate optimization and must produce
a standard stream that the corresponding gzip/ZIP reader can decode. On the
tested text and repetitive inputs it is no larger than level 9. It supports
empty input, binary input, stdin, multiple files, `-k`, `-f`, and `-n`.

The tuning options are accepted in short and long form and can be combined:

- `-I n`/`--iterations n`: optimization iteration count (default 15). Values
  such as 2, 3, 5, 10, 15, 20, 30, 50, 1000 are valid; on the tested input,
  more iterations do not make output larger.
- `-J n`/`--maxsplits n`: maximum split-block count (default 15); zero is
  valid.
- `-F`/`--first`: perform optimization iterations before block splitting.
- `-O`/`--oneblock`: disable splitting into smaller Zopfli blocks.

`-F` and `-O` work together, and all four tuning options work together. These
options may be parsed even when the selected level is not yet 11. A negative
token following `-I` or `-J` is treated as another option, hence as a missing
parameter for the preceding option.

## Spec 11: Zlib format

`-z`/`--zlib` creates an RFC 1950 zlib wrapper around deflate. File output uses
the `.zz` suffix. The first byte is `0x78`; the header check bits are valid and
the trailer is the big-endian Adler-32 of the uncompressed data. The FLEVEL
bits (top two bits of the second byte) are `00` for level 1, `01` for level 6,
and `11` for level 9. The stream must be accepted by a standard zlib decoder.

Zlib has no filename, timestamp, or comment fields. Supplying `-C comment` with
`-z` still writes a valid zlib stream but emits a warning containing
`can't store comment in zlib format` and returns status 1. `-q` suppresses that
warning without corrupting the stream. Decompression and testing auto-detect
zlib from its contents; `-z` need not be repeated.

## Spec 12: Single-entry ZIP format

`-K`/`--zip` produces an interoperable PKWare ZIP archive using deflate and
exactly one entry. It begins with `PK`; a standard ZIP reader must find one
entry, validate its CRC-32 and sizes, and extract the original bytes. File
output uses `.zip`. File input uses only the basename as the entry name, never
the containing path. Stdin uses entry name `-` by default.

`-A name`/`--alias name` replaces the stdin ZIP entry name exactly. It may
contain path separators. For example `-K -A subdir/nested/file.txt` creates
that exact entry name. `-C text` stores the exact UTF-8 comment as the entry's
comment (not merely the archive comment), including an empty comment. File
mtime is represented as a valid ZIP timestamp (years are at least 1980); `-m`
still creates a valid timestamp field.

ZIP supports levels 0 through 9 and 11, empty and large input, binary data,
custom block sizes, rsyncable mode, quiet/verbose modes, stdout, keep, force,
and in-place round-trips. Decompression auto-detects standard single-entry ZIP
files created by other implementations. If a ZIP contains multiple entries,
only the first entry is written; emit a warning containing `entries after the
first` and return 1.

## Spec 13: File compression and output naming

Without `-c`, each regular input file is compressed independently beside the
input. Default gzip appends `.gz`, zlib appends `.zz`, and ZIP appends `.zip`.
`-S suffix` replaces `.gz` for gzip file compression; the suffix is used
literally and may be long (50 or more characters), but may not be empty. A
custom suffix does not change the gzip contents and `-t` recognizes the result
by content.

After a completely successful in-place compression, delete the input unless
`-k`/`--keep` was selected. With `-k`, both files remain and the input bytes are
unchanged. Preserve the source file's permission bits and relevant metadata on
the output so a later in-place decompression preserves ordinary permissions,
including execute permission.

Names containing spaces, dashes, dots, underscores, non-ASCII filesystem
characters, or around 200 characters must be handled without truncation or
shell interpretation.

## Spec 14: File decompression and output naming

Without `-c`, decompression normally removes the recognized compressed suffix:
`name.gz` becomes `name`, `name.zz` becomes `name`, and `name.zip` becomes
`name`. It creates the output only after recognizing and decoding a valid
stream. After success it deletes the compressed input unless `-k` is set. With
`-k`, both input and output remain.

By default decompression does not restore the name stored in a gzip header; it
uses the compressed pathname with its suffix removed. With `-N`, a stored gzip
basename is restored instead. Thus, if `original_name.txt.gz` (whose header
stores `original_name.txt`) is renamed `different_name.gz`, ordinary `-d`
creates `different_name`, while `-d -N` creates `original_name.txt`.

In-place decompression requires a recognized compressed suffix even if content
is valid. A suffixless valid gzip is refused with status 1 and `does not have
compressed suffix`. `-dc` has no such suffix requirement. Multiple mixed gzip,
zlib, and ZIP operands may be auto-detected and decompressed in one invocation.

## Spec 15: Overwrite, already-compressed, directory, and symlink rules

Existing output files are never overwritten by default. Skip that operand,
leave both input and existing output unchanged, emit
`executable: skipping: PATH exists`, and make the overall status 1. `-f` or
`--force` permits replacement; delete the input only after the replacement was
successfully completed. The same rule applies when decompression would replace
an existing output.

In compression mode, a filename already ending in the active compressed
suffix is skipped unchanged without `-f`, with the diagnostic
`executable: skipping: PATH ends with .gz` (substitute the active suffix).
This particular benign skip returns status 0 if nothing else fails. With `-f`,
it is compressed normally, so `x.gz` becomes a valid `x.gz.gz` and the original
`x.gz` is deleted unless kept.

A directory operand without `-r` is a status-1 failure with
`executable: skipping: PATH is a directory`. A symbolic link, including a
broken one, is likewise skipped without force/stdout with
`executable: skipping: PATH is a symbolic link`. With `-f`, or when reading it
for `-c`, a symlink to a regular file is followed and its target bytes are
processed.

## Spec 16: Multiple operands and recursion

Failure of one operand does not stop later operands. Successfully processed
operands still produce their outputs; the final status is 1 if any ordinary
operand failed. This applies to compression, decompression, testing, and
listing.

`-r`/`--recursive` makes directory operands traverse all nested subdirectories
and process regular files as if named individually. `-rk` preserves each
source. In compression recursion, already-suffixed files are warned about and
not given a second suffix unless forced. In decompression recursion, eligible
compressed files are restored. The traversal must support directory trees at
least five levels deep and mixtures of text, binary, and pre-compressed files.

`-r` is also harmless when its operand is an ordinary file: that file is
processed normally.

## Spec 17: Gzip name and time metadata

For regular-file compression, name and mtime storage are enabled by default.
The stored name is the complete basename only, encoded as the filesystem name's
bytes and NUL-terminated. In the gzip header this sets FNAME (`FLG & 0x08`).
The mtime is the source's integer Unix timestamp, encoded little-endian in
header bytes 4–7.

The switches independently update two boolean settings and are order-sensitive:

- `-n`/`--no-name`: disable both name and time.
- `-N`/`--name`: enable both name and time.
- `-m`, `-T`, or `--no-time`: disable time only, retaining the current name
  setting.
- `-M`/`--time`: enable time only, retaining the current name setting.

Consequently `-n -N` stores both; `-N -n` stores neither; `-N -m` stores the
name but writes timestamp zero; and `-m -N` stores both. With name and time
disabled and no comment, gzip `FLG` is exactly zero and bytes 4–7 are zero.
With time disabled alone, FNAME remains set and bytes 4–7 are zero. Metadata
state is reset/applied correctly for every file in a multi-file invocation.

## Spec 18: Metadata restoration and permissions

In decompression, `-N` enables restoration of both stored basename and stored
mtime. `-M` enables stored mtime restoration and `-m` disables it. Restored
mtime must match the stored whole-second Unix time exactly (or within ordinary
filesystem timestamp precision). Compressing the restored file with `-N`
again must store that same timestamp.

When stored name restoration is disabled, use suffix stripping as in Spec 14.
When stored time restoration is disabled or no time is present, use the
compressed input file's mtime rather than inventing a header time. Output-file
permission handling must retain the input file's permission character: a file
that was executable before compression is executable after the tested
compress/delete/decompress sequence.

## Spec 19: Gzip comments and header validation

`-C text`/`--comment text` sets gzip FCOMMENT (`FLG & 0x10`) and writes the
argument's UTF-8 bytes followed by NUL. It supports an empty string, at least
1000 bytes, non-ASCII characters, newlines, tabs, carriage returns, and spaces
without truncation. With no stored filename the comment begins at byte 10. With
both FNAME and FCOMMENT, the NUL-terminated basename comes first and the
NUL-terminated comment immediately follows it.

On input, parse all standard optional gzip fields and validate FHCRC when
present. A bad FHCRC is a failure whose diagnostic ends with
`PATH corrupt: header crc error`. A malformed unterminated optional name is an
`unrecognized format` failure. Reserved gzip-header bits must never cause a
crash.

## Spec 20: Environment-provided options

Before command-line arguments, parse whitespace-separated options from `GZIP`
and then from `PIGZ`. Spaces and tabs separate options and their parameters;
leading whitespace and internal runs of repeated whitespace are accepted. An
empty value contributes no options. There is a reference parser edge at the
end of a nonempty value: one trailing space or tab is accepted, but two
trailing whitespace characters create an empty file operand and are rejected.
A nonempty value consisting only of whitespace is rejected for the same
reason. Thus the exact combination `GZIP=" \t -b\t64  "` and
`PIGZ=" -p 2 "` exits 22 without processing input and writes
`executable: abort: cannot provide files in GZIP environment variable` to
stderr. The analogous malformed `PIGZ` value names `PIGZ` in that diagnostic.
Command-line settings are processed last and therefore override conflicting
environment settings. Non-conflicting settings accumulate: for example
`GZIP=-1` and `PIGZ=-k` select level 1 and keep.

Environment values may contain options and their parameters (`-b 64`, `-1 -v`,
`-9 -k`), but may not contain file operands. A file word in one of these
variables is exit 22 with, respectively,
`executable: abort: cannot provide files in GZIP environment variable` or
`executable: abort: cannot provide files in PIGZ environment variable`.
Unknown options and missing parameters in environment values are invocation
errors just as on the command line.

## Spec 21: Decompression formats, concatenation, and forced pass-through

Decompression auto-detects gzip, zlib, and ZIP by contents. It accepts streams
created by common external gzip/zlib/ZIP implementations, not only its own
output. A concatenation of gzip members is decoded completely, concatenating
the uncompressed members. Integrity testing likewise validates every gzip
member.

Normally an unrecognized stream is a status-1 error. In the special cat-like
combination `-c -d -f` (including the cluster `-cdf`), bytes that are not a
recognized compressed member are copied verbatim. Therefore raw stdin of
length 0, 1, 2, or 3 yields exactly itself with status 0, a plain file is copied
unchanged, and a valid gzip member followed by one to three raw bytes yields
the decompressed member followed by those raw bytes.

Without forced pass-through, non-member bytes after a valid gzip member are
trailing junk rather than damage to the decoded member. For a named in-place
`-d -v` operation, the valid member is written to the derived output, the
trailing bytes are ignored, and the status is 1. Stderr first writes the
verbose progress prefix and then the warning on that same line, followed by an
additional newline, in this exact form:

```text
SOURCE to DESTINATION executable: warning: SOURCE: trailing junk was ignored

```

A byte sequence beginning with Unix-compress magic `1f 9d` is recognized as
that family for diagnostics. If its control byte specifies an invalid LZW bit
width, report a failure containing `lzw bits out of range`.

## Spec 22: Integrity testing and corruption detection

`-t`/`--test` fully parses and decompresses input only to validate it. On valid
gzip (including empty and concatenated members), zlib, and ZIP input it returns
0 and writes nothing to stdout or stderr unless verbose mode requests a
message. It creates, deletes, or modifies no files.

Validation includes wrapper headers, deflate correctness, gzip/ZIP CRC-32,
gzip ISIZE, zlib Adler-32, every concatenated member, and the gzip header CRC.
Detected failures return 1 and include `corrupted` or the more specific format
diagnostic. Required phrases include:

- truncated before a gzip trailer: `corrupted -- missing trailer`;
- deleting the final byte of a deflate payload while retaining the original
  eight trailer bytes is also diagnosed as `corrupted -- missing trailer`;
- wrong gzip CRC: `corrupted -- crc32 mismatch`;
- wrong gzip length: `corrupted -- length mismatch`;
- invalid deflate block: `corrupted -- invalid deflate data` followed by the
  decoder detail, such as `(invalid block type)`;
- non-compressed input: `unrecognized format`.

## Spec 23: Listing output

`-l`/`--list` writes to stdout and does not alter its inputs. Ordinary listing
starts with exactly:

```text
compressed   original reduced  name
```

and has one row per operand. For a normal gzip row, “compressed” is the number
of bytes after the first gzip header (including its optional fields) and before
the final eight-byte trailer; “original” is the final little-endian ISIZE;
“reduced” is `100 * (original - compressed) / original`, rounded to one decimal
and followed by `%`; and “name” is the first stored gzip name, or otherwise the
input pathname with its recognized suffix removed. Numeric fields are right
aligned to widths 10 and the row follows this shape:

```text
        12         10  -20.0%  test.txt
```

When the original size is not reliably known (zlib or a streamed ZIP local
header), append `?` to the displayed original value and print `unk` for the
ratio. ZIP uses its entry name. A concatenated gzip is treated differently:
the final member's ISIZE is displayed as a known original size, without `?`,
and a percentage is computed from it even though it covers only that final
member. For example, listing the concatenation of a 50-byte first member and a
42-byte second member created with ten-byte unnamed headers produces exactly:

```text
compressed   original reduced  name
        39         42    7.1%  multi
```

Verbose listing (`-lv`) starts with exactly:

```text
method    check    timestamp    compressed   original reduced  name
```

Its gzip row begins `gzip 8`, then an eight-lowercase-hex-digit CRC, then an
ls-style local timestamp (`Mon dd HH:MM` for a recent time or `Mon dd  YYYY`
for an older time), followed by the same size, ratio, and name columns. If the
header mtime is zero, the timestamp column is exactly `------ -----`.

Listing a recognizable gzip with a damaged/missing trailer is best-effort and
can return 0, using the last four available bytes as the apparent ISIZE rather
than decompressing it. This concrete operation is pinned: compressing the
33-byte UTF-8 string `test data for corruption testing\n` from a file named
`test.txt` with default options, deleting the final ten compressed bytes, and
listing that result must print exactly:

```text
compressed   original reduced  name
        24 1940252260  100.0%  test.txt
```

An entirely unrecognized file or missing file is still a status-1 listing
failure. Combining `-l -t` on valid input prints the normal listing and also
performs the full integrity checks from Spec 22. If validation fails, no
listing header or row is written to stdout. For example, if the CRC in the
trailer of `damaged.gz` is wrong, `-lt damaged.gz` returns 1, writes nothing to
stdout, and writes
`executable: skipping: damaged.gz: corrupted -- crc32 mismatch` to stderr.

## Spec 24: Verbose, quiet, and messages

`-v`/`--verbose` reports each transformation on stderr, including operations
that read stdin or use `-c`. The source and destination placeholders for those
streams are literally `<stdin>` and `<stdout>`. Thus `-v -c` with no operand
writes exactly `<stdin> to <stdout> \n`, and `--verbose -c SOURCE` writes
exactly `SOURCE to <stdout> \n`, in addition to the compressed bytes on
stdout. The general raw line format includes one space before the newline:

```text
SOURCE to DESTINATION 
```

For decompression, source and destination are reversed accordingly. Paths are
printed exactly as supplied/derived. Additional `-v` flags do not change list
column structure. `-vV` has the special version behavior in Spec 3.

`-q`, `--quiet`, and `--silent` suppress all warnings, errors, and progress
messages, even when status remains nonzero. They never suppress requested
binary stdout or list output. Successful non-verbose operations normally have
empty stderr.

## Spec 25: Diagnostics, validation, and exit status

All diagnostics go to stderr and normally end in `\n`. Invocation errors have
status 22 and prefix `executable: abort: `. Required exact messages (apart from
the final newline) are:

```text
executable: abort: invalid option: --invalid-flag
executable: abort: invalid option: -X
executable: abort: missing parameter after -b
executable: abort: missing parameter after -p
executable: abort: missing parameter after -S
executable: abort: missing parameter after -A
executable: abort: missing parameter after -C
executable: abort: missing parameter after -I
executable: abort: missing parameter after -J
executable: abort: invalid usage: -S must be followed by space
executable: abort: invalid numeric parameter: abc
executable: abort: block size too small (must be >= 32K)
executable: abort: block size too large: 999999999999
executable: abort: invalid number of processes: 0
executable: abort: invalid number of processes: 999999999999
executable: abort: suffix cannot be empty
executable: abort: only levels 0..9 and 11 are allowed
executable: abort: invalid option: LZW output not supported: -Z
executable: abort: invalid option: no ascii conversion: -a
```

Block sizes 1, 16, and 31 all use the “block size too small” diagnostic.
Extremely large numeric values must be rejected without overflow or resource
allocation; a process count such as `99999999999999` uses a diagnostic
containing `too many processes: 99999999999999`. If an option requiring a
parameter is followed by a negative option token, such as `-p -1`, the first
option reports its parameter as missing.

Per-file failures use status 1 and prefix `executable: skipping: `. Required
templates include:

```text
executable: skipping: PATH does not exist
executable: skipping: PATH is a directory
executable: skipping: PATH is a symbolic link
executable: skipping: PATH.gz exists
executable: skipping: PATH does not have compressed suffix
executable: skipping: PATH: corrupted -- REASON
```

Unknown long options reproduce the offending token. A missing operand path is
also reproduced exactly, whether relative or absolute. Status 1 does not imply
early termination: see Spec 16. Status 0 is used only when all requested work
succeeded or the only event was the benign already-suffixed skip described in
Spec 15.
