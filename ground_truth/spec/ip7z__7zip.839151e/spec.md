# Clarified specification for `executable`

## Spec 1

The delivered artifact is exactly one runnable command-line program named `executable`. It must run on a Unix-like, case-preserving filesystem, accept arbitrary current working directories, read standard input, write standard output and standard error separately, and create or modify files relative to the current directory unless an absolute path or an output directory says otherwise. It must behave as the standalone `7za` command-line archiver described below. All archive operations must be real: an archive created in one invocation must remain usable by later independent invocations, and pre-existing archive files supplied to the program must be parsed rather than recognized by filename alone. The delivered executable itself exceeds 500,000 bytes; the reference artifact is 1,673,696 bytes and can be used as the large real-binary input to the BCJ2 tests.

The implementation profile is the 64-bit 7-Zip 26.00 command-line behavior. Ordinary textual invocations begin on standard output with a header of this form (with the actual available thread and open-file counts):

```text
7-Zip (a) 26.00 (x64) : Copyright (c) 1999-2026 Igor Pavlov : 2026-02-12
 64-bit locale=C.UTF-8 Threads:<N> OPEN_MAX:<N>
```

Binary output requested with `-so` is an exception: stdout must contain only extracted payload bytes, with no header, status, or newline added. Paths, file counts, byte counts, archive sizes, packed sizes, methods, checksums, timestamps, and filesystem side effects reported by the program must describe the actual operation.

## Spec 2

With no arguments, or with `--help`, the program succeeds with exit status 0 and prints its header and usage. The usage line is:

```text
Usage: 7za <command> [<switches>...] <archive_name> [<file_names>...] [@listfile]
```

The help must list these commands and meanings: `a` add, `b` benchmark, `d` delete, `e` extract without directory names, `h` calculate hashes, `i` show supported formats, `l` list archive contents, `rn` rename archived paths, `t` test integrity, `u` update, and `x` extract with full paths. In particular, the command lines must include text equivalent to `a : Add files to archive`, `e : Extract files from archive (without using directory names)`, and `x : eXtract files with full paths`.

Help must document the accepted switch families: `--`, `-ai`, `-ax`, `-ao`, `-an`, `-bb`, `-bd`, `-bs`, `-bt`, `-i`, `-m`/`-mmt`/`-mx`, `-o`, `-p`, `-r`, `-sa`, `-scc`, `-scs`, `-scrc`, `-sdel`, `-seml`, `-sfx`, `-si`, `-slp`, `-slt`, `-snh`, `-snl`, `-sni`, `-sns`, `-so`, `-spd`, `-spe`, `-spf`, `-ssc`, `-sse`, `-ssp`, `-ssw`, `-stl`, `-stm`, `-stx`, `-t`, `-u`, `-v`, `-w`, `-x`, and `-y`. At minimum the literal help tokens `-mx[N]`, `-p{Password}`, `-o{Directory}`, `-r[-|0]`, `-t{Type}`, `-v{Size}`, `-si`, and `-so` must appear.

## Spec 3

Command-line switches are case-insensitive and may occur before or after archive/file operands. A single argument containing spaces remains one value, including `-o/path with spaces`. A filename beginning with `-` is accepted when it is an already-resolved path operand; `--` stops both switch interpretation and `@listfile` expansion for following operands. Archive type is selected by `-t7z`, `-tzip`, `-ttar`, `-tgzip`, `-tbzip2`, `-txz`, `-tcab`, or `-t#`; without `-t`, creation uses the archive extension and reading primarily uses content signatures. A valid archive renamed to a misleading extension must still be detected and processed correctly.

Conflicting singleton switches are errors: two archive-type switches report `Command Line Error:\nMultiple instances for switch:` and the second switch; two `-o` switches do likewise. Unknown commands report `Command Line Error:\nUnsupported command:` followed by the command and return 7. Unknown switches report `Command Line Error:\nUnknown switch:` followed by the switch and return 7. A command lacking its required archive operand must fail cleanly or show usage, never crash or hang.

## Spec 4

Switch syntax must be validated before unsafe processing. User-level syntax errors return 7. Required cases include: `-aox`, invalid `-r` postfixes other than empty, `0`, or `-`, invalid `-sa` postfixes other than `a`, `e`, or `s`, `-y-`, invalid `-bso`/`-bse`/`-bsp` destinations other than `0`, `1`, or `2`, empty `-t`, unknown console charset names, invalid `-spf`/`-spm` postfixes, malformed hexadecimal `-stm`, malformed update-action strings, and missing or invalid include/exclude wildcard markers. Error text must identify the bad switch/value using the 7-Zip-style phrases `Incorrect switch postfix`, `Too short switch`, `Too long switch`, `Unsupported charset`, `Incorrect wildcard type marker`, `Unsupported -spf`, `Unsupported -spm`, or `incorrect update switch command`, as applicable. In particular, `-y-` returns 7 with `Too long switch:` followed by `-y-`; `-rBAD` returns 7 with `Too long switch:` followed by `-rBAD`; `-stmXYZ` returns 7 with `Unsupported switch postfix -stm` followed by `XYZ`; and `-ix` returns 7 with `Too short switch:` followed by `-ix`.

The spelling `-i!!*.txt` is not rejected as a duplicated-marker syntax error. For `l -i!!*.txt x.7z`, parsing proceeds to opening `x.7z`; when that archive is absent, the result is status 2 with the normal `ERROR: errno=2 : No such file or directory`, `x.7z`, and `System ERROR:` diagnostic.

Compression-property errors that are discovered after scanning/starting an update return 2 and end with `System ERROR:` and `E_INVALIDARG : One or more arguments are invalid`. This includes nonnumeric or negative `-mx` values, an unknown `-m0=` method, an invalid solid setting, and a ZIP solid-mode request. An unsupported hash algorithm such as SHA512 must fail or clearly say it is not implemented. The process must never crash on malformed arguments.

## Spec 5

Input operands may be relative paths, absolute paths, directories, wildcard expressions, or `@listfile` references. A listfile contains one path/pattern per line. It is expanded using its specified charset, defaulting to the documented Unicode behavior; an absent listfile returns 7 and reports `The file operation error for listfile`, `errno=2 : No such file or directory`, and its path. Invalid encoded content returns 7 and reports `Incorrect item in listfile.`, advises checking charset and `-scs`, and names the listfile. Empty lines in include/exclude listfiles are ignored.

The implementation must handle at least 500 files on a command line or in one archive, 100-file argument lists, files from zero bytes through at least 5 MiB, arbitrary binary bytes including NUL and all 256 byte values, names around 200–250 characters, archive paths longer than 255 characters, directory nesting of at least 50 levels, spaces and shell punctuation in names, dotfiles, and UTF-8 names/content from Latin, Greek, Cyrillic, Arabic, Chinese, and Japanese scripts. Names are preserved exactly and distinct case variants remain distinct unless case-insensitive mode is explicitly selected.

## Spec 6

Wildcard matching applies to source selection and to `l`, `x`, `e`, and `d` member selection. `*` matches zero or more characters and `?` exactly one character; multiple wildcard characters in one expression work. On Unix, ordinary punctuation such as `[ ] ( ) +` is literal rather than an extended regular-expression syntax. Dotfiles participate in `*`. A wildcard containing directory components matches paths at the indicated level. Extraction member patterns use `/` for archived path components on this Unix profile: backslashes are not normalized to separators. Thus `e paths.7z 'tree\sub\*.txt' -oflat` is a successful no-match operation and creates no `deep.txt`.

Without recursion, a wildcard such as `*.txt` searches its indicated directory only. `-r` makes operand wildcard searches recursive; `-r0` and `-r-` must parse with their 7-Zip meanings. `-ir!pattern` and `-xr!pattern` make the individual include/exclude filter recursive. `-i!pattern` includes matching names, `-x!pattern` excludes them, and repeated include or exclude switches form unions within their class. Exclusions win over overlapping inclusions. `-i@file` and `-x@file` read filters from listfiles. Directory exclusions such as `-xr!build` or `-xr!build/*` remove the directory subtree. `-spd` disables wildcard interpretation so a literal file actually named `*.txt` can be selected. A selection matching no archived members is a clean success for list/extract and produces no extracted files.

## Spec 7

The `a` command creates a new archive or adds/replaces input items in an existing one. A successful new operation prints `Scanning the drive:`, an accurate folder/file/byte count, `Creating archive: <path>`, `Add new data to archive: ...`, `Files read from disk: <N>`, `Archive size: <bytes> bytes (<rounded KiB/MiB>)`, and `Everything is Ok`; it returns 0 and creates a nonempty valid archive, including when the only members are empty files/directories or when a wildcard matches nothing. Singular/plural wording follows the 7-Zip profile (`1 file`, `2 files`, and analogous folder forms).

Count summaries omit a zero folder term: file-only input says `1 file, ...` or `100 files, ...`, not `0 folders, ...`. A positive byte count's parenthesized KiB value is rounded upward by 1024-byte units, with a minimum of `1 KiB`; for example, 1 byte is `(1 KiB)`, 14,472 bytes is `(15 KiB)`, and 900,384 bytes is `(880 KiB)`. Zero-byte summaries are printed as `0 files, 0 bytes` without `(0 KiB)`. These formatting rules apply to scan, add/keep, and archive-size summaries and are unchanged by switch placement, uppercase switches, `--`, listfiles, or multiple compatible `-m` switches.

Explicit file arguments normally store their basename; a directory operand stores the named directory and all descendants when directory traversal is requested by the operand or recursion mode. Empty directories are real archive members and are recreated on extraction. Adding a file already represented in an archive replaces the existing member rather than duplicating it. Adding new files to an existing archive prints `Open archive:`, `Updating archive:`, and an accurate `Add new data to archive:` summary. It prints `Keep old data in archive:` when at least one old member is retained. If the only old member is replaced while another member is added, no old data is retained and the `Keep old data in archive:` line is omitted. `-w<directory>` is accepted as the temporary work area without changing archive semantics. `-sae` is accepted. `-sdel` removes successfully archived source files only after the archive has been completed successfully.

## Spec 8

Missing input files during add/update are scan warnings, not fatal archive-format errors. Report a `WARNING` with `errno=2 : No such file or directory` and the missing name, preserve/add all readable inputs, create a valid archive (an empty archive if none were readable), and return 1. With the default routing, each warning is written both ways: stderr contains `WARNING: errno=2 : No such file or directory` followed by the missing name, while stdout ends with a detailed block headed `Scan WARNINGS for files and folders:`, one `<name> : errno=2 : No such file or directory` line per missing input, a `----------------` separator, and `Scan WARNINGS: <N>`. `-sse` (stop on input-open error) is accepted; with mixed readable and missing inputs it still terminates promptly, uses that same routing, and leaves the archive containing readable inputs rather than crashing. Multiple missing inputs with `-sse` return 1 and appear individually in both streams. Broken symlinks followed without link-storage mode and recursive symlink loops similarly report scan warnings rather than hanging. An input disappearing during scanning is handled the same way.

If source paths resolve to duplicate archive names under case-insensitive selection, fail with status 2 and stderr containing `ERROR:` and `Duplicate filename on disk:` followed by the conflicting stored name. In normal case-sensitive Unix mode, differently cased names coexist. `-ssc` explicitly requests case-sensitive matching; `-ssc-` requests case-insensitive matching and may therefore expose duplicate-name conflicts.

## Spec 9

The `u` command creates an archive when none exists, otherwise compares selected filesystem items with archived metadata. New items are added; existing members are replaced when source content/time is newer or changed; unchanged members are retained without recompression. A no-change operation reports `Add new data to archive: 0 files, 0 bytes` and an accurate `Keep old data in archive:` count. Updates preserve unrelated archive entries, member paths, timestamps, encryption when the correct password is supplied, and validity across large/multi-file updates. Update-time method/level/filter/solid/thread settings apply to newly encoded data; old compression blocks may be retained, so updating a solid archive can increase the reported block count.

The update action expression `-up2q2r0x0y0z1w0` is rejected during command-line parsing: after the normal startup banner on stdout, return 7 and write `\n\nCommand Line Error:\nincorrect update switch command\np2q2r0x0y0z1w0\n` to stderr. The rejected operation leaves the existing archive unchanged. Updating normal 7z, ZIP, and TAR archives with valid update options is supported. Updating the first part of a split-volume archive is not supported: return 2 and place `System ERROR:\nE_NOTIMPL : Not implemented` on stderr. Missing update inputs follow the warning behavior in Spec 8.

## Spec 10

The `d` command removes every archived member selected by exact path or wildcard, including all members beneath a selected archived directory. It rewrites the archive without damaging retained data, compression/encryption metadata, or extractability. It prints `Updating archive:`, accurate `Delete data from archive:` and `Keep old data in archive:` summaries, and `Everything is Ok`. Deleting multiple items in one operation, deleting from solid 7z archives, and deleting from ZIP and TAR archives are supported. Deleting a name that is not present succeeds with no change. Deleting from a nonexistent ordinary archive succeeds by creating a valid empty archive. Deleting all members leaves a valid, listable empty archive. Delete on a split archive is unsupported with status 2 and `E_NOTIMPL` as in Spec 9.

The `rn` command accepts old-name/new-name pairs after the archive name and rewrites member paths without changing payloads. It supports directories in the new path, multiple pairs, ZIP and 7z archives, and preserves later extraction. A successful one-file rename prints `Updating archive:`, `Keep old data in archive: 1 file, <bytes> bytes (<KiB>)`, `Add new data to archive: 0 files, 0 bytes`, `Files read from disk: 0`, the archive-size line, and `Everything is Ok`. Renaming a nonexistent member is a successful no-op. Conflicts with an existing destination must leave a valid archive. An unpaired old name returns 7 with `There is no second file name for rename pair:` and that name. Renaming in an absent archive returns 2 and reports that the archive cannot be found.

## Spec 11

The `l` command takes one archive operand. It prints `Scanning the drive for archives:`, the number and physical bytes of that archive input, `Listing archive: <path>`, then an archive property block introduced by `--`. The block includes at least `Path`, `Type`, and `Physical Size`, plus format-specific properties. Normal listing then prints a table headed:

```text
   Date      Time    Attr         Size   Compressed  Name
------------------- ----- ------------ ------------  ------------------------
```

Each selected member appears with its modification date/time, attributes, exact uncompressed size, the applicable packed size, and its full archive path. The closing row reports total uncompressed and compressed sizes and accurate file/folder counts. Empty archives report `0 files`. Listing filters only change displayed members, not the archive. Positional arguments after the archive are member-selection operands, not additional archives. Thus `l misleading.zip two.7z` lists only `misleading.zip` and treats `two.7z` as a member filter. Unicode names must be emitted intact in UTF-8.

For 7z listings the archive block includes `Headers Size`, `Method`, `Solid`, and `Blocks`. ZIP, TAR, gzip, bzip2, xz, CAB, zstd, split, and SFX/container formats identify the correct `Type` capitalization (`7z`, `zip`, `tar`, `gzip`, `bzip2`, `xz`, `Cab`, `zstd`, `Split`, or `#`) and actual physical size.

## Spec 12

With `l -slt`, print key/value technical properties instead of only the normal table. After the archive block and a `----------` separator, each selected member has its own property group. Common fields are `Path`, `Size`, `Packed Size`, `Modified`, `Attributes`, `CRC`, `Encrypted`, `Method`, and where applicable `Block`. Checksums are zero-padded uppercase hexadecimal (CRC32 is exactly eight digits). Timestamps use `YYYY-MM-DD HH:MM:SS` and preserve available fractional precision. Large sizes are exact decimal byte counts, never truncated.

For a Unix-created regular file, `Attributes` combines an archive flag and a ten-character POSIX mode, for example `A -rw-r--r--`; a directory carries `D` and a `d...` mode; a stored symlink carries `A lrwxrwxrwx`. Empty files/directories have size and packed size zero. In a solid archive only the first member of a shared compressed block needs a nonempty packed size; later members may have an empty value. Non-solid files each have their own sequential block number and packed size. Directory properties have empty CRC/method/block values where no data stream exists.

## Spec 13

ZIP technical member properties additionally include `Folder`, `Created`, `Accessed`, `Characteristics`, `Host OS`, `Version`, `Volume Index`, `Offset`, and `Comment`. Unix ZIPs report `Host OS = Unix`; NTFS timestamp extras report `Characteristics = NTFS`; volume index is zero in a normal single-volume archive; offsets reflect actual distinct local-header locations. Stored members say `Method = Store`, Deflate/BZip2/LZMA/Deflate64 members identify that method, BZip2 entries use extraction version 46, and LZMA entries use version 63. For traditional encryption, `ZipCrypto` is the first method token, for example `Method = ZipCrypto Store` or `Method = ZipCrypto Deflate`. An empty stored entry has `Size = 0`, `Packed Size = 0`, and `CRC = 00000000`.

TAR technical properties include `Folder`, `Mode`, `User`, `Group`, `User ID`, `Group ID`, `Device Major`, `Device Minor`, `Symbolic Link`, `Hard Link`, `Characteristics`, `Code Page`, and `Comment`; fields without values are still emitted, so an ordinary member includes the literal empty line `Comment = `. UTF-8 TARs report `Code Page = UTF-8`. `Characteristics` exposes the parsed dialect and extension information, including terms such as `POSIX`, `GNU`, `PAX`, `ASCII`, `UTF8`, `path`, `mtime`, and `MaxUnicode` as appropriate. gzip properties include headers size, CRC, and host OS. xz properties include `Method = LZMA2`, stream and block counts. CAB exposes cabinet ID, blocks, volumes, and volume index. zstd exposes its method/checksum and frame characteristics.

## Spec 14

The `x` command extracts selected members while retaining their archive-relative directory paths. The `e` command extracts file data into one flat output directory, discarding member directory components; it nevertheless creates every selected explicit directory member, while nested file payloads are written by basename. For example, flat extraction of an archive containing explicit `subdir` and `subdir/nested.txt` creates both `subdir/` and `nested.txt` in the destination. `-o<directory>` selects the destination and must create all missing intermediate directories; without it, the current directory is used. Absolute output paths and paths containing spaces work.

Selection accepts exact names, multiple names, wildcards, directory paths with or without a trailing slash, Unix `/` separators, `-i` includes, and `-x` excludes. Backslash-containing member patterns follow the no-match behavior in Spec 6. Multiple archive inputs can be processed sequentially into the same destination when selected through the supported archive-input switches. Extracting one member must not create unrelated members. A selected symlink may require its referent to be materialized as needed to make the link usable, but unrelated entries remain absent. Nested archives are extracted as ordinary files and are not recursively unpacked. An empty archive, or a member selection with no matches, succeeds cleanly and prints `Everything is Ok` with zero counts.

On success, textual extraction output includes `Extracting archive:`, the recognized archive property block, `Everything is Ok`, and exact totals such as optional `Folders: <N>`, `Files: <N>`, `Size:       <bytes>`, and `Compressed: <bytes>`. Extracted bytes must exactly equal archived bytes for text, binary, random, empty, large, encrypted, filtered, and solid data.

## Spec 15

Extraction overwrite modes are noninteractive and deterministic when given `-y`:

- `-aoa` overwrites all existing destination files with archived versions.
- `-aos` skips existing destination files without changing their contents or timestamps, while extracting nonconflicting members.
- `-aot` renames the existing destination aside using `_1`, `_2`, and so on before placing the archived member at its original name.
- `-aou` never overwrites a conflicting destination: it preserves the existing file at its original name and writes the incoming archive member to the first unused `_1`, `_2`, and so on name. This auto-renaming occurs even when the existing file is newer than the archived member.

Auto-renaming finds an unused numbered name and handles repeated conflicts and collisions caused by flattening. Modes combine with `-o` and `e`. Read-only and identical existing files are handled without crashing. With no explicit overwrite switch, `-y` answers overwrite prompts affirmatively. Extraction restores regular file data before applying restrictive modes so read-only files are complete.

## Spec 16

The `t` command parses every selected archive stream and verifies headers, decompression, encryption authentication/check data, CRC/checksum, and member sizes without creating extracted files. A valid one-file 7z archive returns 0, prints `Testing archive:`, the recognized archive property block, `Everything is Ok`, `Size:       <bytes>`, and `Compressed: <bytes>`, but does not print a `Files: 1` line. It works for 7z, ZIP, TAR, gzip, bzip2, xz, zstd, CAB, encrypted archives with a correct password, SFX archive portions, and complete split archives.

Truncation, malformed headers, invalid checksums, corrupted compressed data, a wrong password, a corrupt split volume, or an unavailable volume returns nonzero (normally 2), does not print `Everything is Ok`, and reports the relevant `Open ERROR`, `Headers Error`, `Unexpected end`, `Data Error`, `CRC Failed`, or `Wrong password?` plus archive/sub-item error counts.

## Spec 17

7z creation uses the six-byte signature `37 7A BC AF 27 1C` and creates genuinely parseable 7z containers. Default file compression is LZMA2 and ordinary multi-file archives are solid unless disabled. The writer and reader support empty streams, directories, multiple encoded blocks, independent and solid streams, encoded headers, CRC validation, and metadata needed for paths, POSIX modes, links, and timestamps. Default technical listings use settings-style method names such as `LZMA2:12`; larger/default dictionaries may appear as a size suffix such as `LZMA2:6m` or `LZMA2:25`.

The reader must accept valid prebuilt 7z archives made with every method/filter/encryption combination required below. The writer must be deterministic according to the 26.00 profile: method order, header encoding, block assignment, and serialized sizes must be consistent enough that reported archive sizes and packed sizes match the bytes written. It must never fake a listing for an invalid or non-archive input.

## Spec 18

Compression levels `-mx0` through `-mx9`, plus the `-mx=N` spelling, are supported. Level 0 uses uncompressed `Copy` in 7z and `Store` in ZIP, making packed payload size equal uncompressed size. Higher levels perform real compression; on repetitive data level 9 is no larger than level 1 and is substantially smaller than copy/store, while incompressible data round-trips with modest format overhead. Intermediate levels are accepted and should provide at least some observable compression improvements over the range.

Accepted tuning properties include `-md=16m` and `-md=32m` for applicable LZMA-family methods, `-mfb=64`, `-mmf=bt4`, `-mmt1`, `-mmt2`, `-mmt=1`, `-mmt=2`, `-mmt=4`, `-mmt=off`, `-mo=2..16` for PPMd, `-ms=on`, `-ms=off`, `-ms=1m`, `-ms=2f`, `-ms=2g`, and multiple compatible `-m` switches together. `-md` is not the PPMd memory-property spelling: `a -m0=PPMd -mo=10 -md=24m -ms=on ...` scans the inputs, then returns 2 with `System ERROR:` and `E_INVALIDARG : One or more arguments are invalid`. Thread selection and affinity affect execution settings but not data correctness. Every combination that is successfully produced must list/test/extract correctly.

## Spec 19

7z data codecs accepted through `-m0=`/`-m1=` are `Copy`, `LZMA`, `LZMA2`, `PPMd` (displayed as `PPMD`), `BZip2`, `Deflate`, and `Deflate64` where the container permits them. ZIP accepts Store/Copy, Deflate, Deflate64, BZip2, and LZMA through `-mm=` or `-m0=`. The selected codec must actually encode the payload, affect size appropriately, and be identified in technical listings; explicit LZMA must not be mislabeled LZMA2, and Deflate64 must not be mislabeled Deflate.

PPMd8 supports order values from 2 through 16 and inline method memory properties, including the accepted form `-m0=PPMd:o=10:mem=24m`; for the observed two-file solid archive this is listed as `Method = PPMD:o10:mem18` on each member. Its default method display is `PPMD:o6:mem16`; explicit order settings produce forms such as `PPMD:o2:mem16`, `PPMD:o16:mem16`, `PPMD:o8`, or `PPMD:o10`. PPMd works with empty, one-byte, binary, Unicode, large repetitive/source-text, solid and non-solid, encrypted, stdin, update, delete, rename, selective extraction, test, and stdout operations when its properties use supported spellings. On repetitive/source-like text it must achieve the strong compression expected of PPMd; a solid set of many similar small files is smaller than its non-solid counterpart.

## Spec 20

Executable/data transforms are supported and reversible: `BCJ`, `BCJ2`, `ARM`, `ARM64`, `ARMT`, `PPC`, `IA64`, `SPARC`, and `Delta`, including explicit delta distances 1 and 2. A transform supplied alone as `-m0=BCJ` or `-m0=BCJ2` creates the corresponding reversible, otherwise-uncompressed stream structure and lists that transform as its method. Transforms can also be chained with a following compressor using `-m0=<filter> -m1=<codec>`, and `-mf=BCJ` / `-mf=Delta` are accepted where used. Listings show the actual pipeline, for example `LZMA:14 BCJ`, `LZMA2:14 BCJ2`, `ARM64 LZMA2:14`, or a line containing both `Delta` and its compressor.

Filters must transform and reverse actual bytes, preserving executable bit and exact executable contents so extracted test binaries still run. BCJ/LZMA-family compression must materially compress normal executables. Single-byte data and mixed executable/text solid archives remain valid. Multiple architecture filters are accepted in an explicitly numbered pipeline: `a -m0=BCJ -m1=ARM -m2=LZMA2 invalid.7z f` returns 0, creates the archive, prints `Everything is Ok`, and technical listing identifies `LZMA2:12 BCJ ARM` at archive level and `BCJ ARM LZMA2:12` for the member.

## Spec 21

Solid-mode behavior is observable. `-ms=on` places compatible files in shared compression blocks, reports `Solid = +`, and normally assigns all of them `Block = 0`; `-ms=off` reports `Solid = -`, creates one independent block per nonempty file, and assigns sequential block numbers. Empty-only archives may have `Blocks = 0`. Block-size/count limits (`-ms=1m`, `-ms=2f`, `-ms=2g`) divide data according to the requested limit. Solid compression of similar files should be no larger than roughly 110% of the non-solid result and for many similar PPMd files must be smaller.

Adding to an existing solid archive may retain its original packed block and append a new block, while deleting/replacing members rewrites only what is necessary. Listings and extraction must reflect the resulting correct block count, methods, filenames, and content after chains of updates and deletes.

## Spec 22

ZIP archives start with the local-file signature `PK\x03\x04` when nonempty, end in a valid central directory, and are compatible with local headers that use data descriptors. Creation, listing, testing, full/flat/selective extraction, update, delete, and rename are supported. The implementation preserves nested directories, explicit empty directories, long and UTF-8 names, special characters, case-distinct names, Unix attributes, CRC32, modification time, optional NTFS timestamp extra fields, unknown/padded extra fields, disk/volume index fields for single-disk archives, and correct version-needed metadata. A newly created empty ZIP is valid, 22 bytes long, lists as zero files, and extracts successfully.

The reader supports stored, Deflate, Deflate64, BZip2, and ZIP-LZMA entries, including different methods in one archive. The writer chooses the requested method and compression level and reports actual ratios. ZIP does not support 7z solid mode: requesting `-ms=on` for ZIP returns 2 with `E_INVALIDARG`. A CAB creation request is likewise rejected as extraction-only with `E_NOTIMPL : Not implemented`.

## Spec 23

TAR creation emits an uncompressed archive whose physical length is a multiple of 512 bytes and that ends with two zero blocks. It supports regular files, explicit empty files, directories, symlinks, hardlinks, Unicode/special names, deep paths, files numbering at least 500, and large size fields. For a pathname exceeding the legacy 100-character field, the writer uses a GNU long-name extension; `l -slt` reports archive `Characteristics = GNU LongName ASCII` and a member characteristic containing `GNU ASCII LongName`. TAR listing/testing/extraction, selective/wildcard extraction, flat extraction, updating, and deletion are supported. Exact content, hierarchy, permissions, and timestamps survive a round trip.

Per-entry packed space is represented in 512-byte blocks; directory and link payload handling follows their entry type. Archive-level `Physical Size` equals the actual file length; `Headers Size` accounts for headers, padding, and end markers and is a multiple of 512. A file consisting only of two 512-byte zero blocks is accepted as an empty TAR when forced with `-ttar`: listing returns 0, writes nothing to stderr, and reports `Type = tar`, `Physical Size = 1024`, `Headers Size = 1024`, and `0 files`. Trailing data after valid end markers does not hide or corrupt earlier entries.

## Spec 24

The TAR reader handles POSIX ustar name/prefix splitting, GNU long-name extensions, and POSIX PAX extended headers. PAX `path`, `linkpath`, `mtime`, `atime`, `ctime`, `uid`, `gid`, `uname`, and `gname` override base headers with their exact values, including names longer than legacy limits, IDs beyond octal field limits, timestamps with nanosecond precision, dates through at least 2038, and long user/group names. Listings distinguish a PAX path from a symlink target and expose combined PAX characteristics.

The reader validates legacy checksums and numeric fields. For a TAR with a truncated header, bad legacy checksum, or invalid octal numeric field that cannot be opened, `l` returns 2, stdout ends with `Errors: 1`, and stderr contains `Open ERROR: Cannot open the file as [tar] archive`, an `ERRORS:` section, and the exact line `Is not archive`. It parses regular, directory, symlink, hardlink, FIFO, character-device, and block-device type flags. Technical mode reports modes such as `d...`, `l...`, `p...`, `c...`, and `b...`, plus link targets and device major/minor numbers. Extraction recreates regular files, directories, and safe links; device entries are never instantiated as privileged device nodes and are instead safely represented as zero-length ordinary files.

## Spec 25

gzip, bzip2, and xz are single-data-stream formats. Creation requires one input stream; giving multiple source files fails nonzero with `System ERROR:` and `E_INVALIDARG : One or more arguments are invalid`. Their signatures are respectively `1F 8B`, ASCII `BZh`, and `FD 37 7A 58 5A 00`. Creation from a file retains the logical original filename where the format supports it; reading is signature-based even under a wrong extension. `a`, `l`, `l -slt`, `x`, `e`, `t`, `-si`, `-so`, output-directory selection, overwrite, compression levels, binary/empty/large inputs, and repeated independent operations all work.

gzip uses Deflate and reports its stored name, exact size, packed size, CRC32, modification time, headers size, and host OS. bzip2 performs real block compression. xz uses LZMA2, supports dictionary selection, validates its checks, and reports stream/block counts and CRC method. Repetitive inputs compress strongly, random gzip payloads remain within modest overhead, and level 9 is no larger than level 1 for the same data. Compound `.tar.gz`, `.tgz`, `.tar.bz2`, and `.tar.xz` are treated as an outer single-stream compressor containing a `.tar`; one extraction yields that TAR, and extracting it yields its members.

## Spec 26

CAB is a read/list/test format, not a creation format. The reader supports single and multiple cabinets/blocks, uncompressed cabinet folders and compressed large files, empty files, directory separators, long and special-character names, exact stored modification times, and selective/wildcard extraction. It creates intermediate directories, honors `-o` and overwrite modes, and produces identical content in repeated destinations.

The archive property block reports `Type = Cab`, actual physical size, cabinet `ID`, `Method`, `Blocks`, `Volumes`, and `Volume Index`; uncompressed examples report `Method = None`. Technical member entries include path, size, method, block, attributes, and time. Invalid CAB signatures fail nonzero with `Cannot open the file as [Cab] archive` and `Is not archive`. A CAB with a readable header/table but truncated payload is still recognized and can list discovered entries while warning `Unexpected end of archive`; extraction/test must return nonzero with `Data Error` or an unexpected-end diagnostic.

## Spec 27

zstd is a read/list/test/extract format for `.zst` frames. The decoder supports normal compressed blocks, raw/incompressible blocks, run-length blocks, empty and one-byte frames, large-window frames, concatenated frames, content-size fields, and optional XXH64 frame checksums. Concatenated frame payloads are concatenated in order, and intervening skippable frames are ignored during decoding. For the tested `first` frame, eight-byte `metadata` skippable payload, and `second` frame, `x -so` emits `firstsecond`; however, `l -slt` reports only first-frame characteristics in a method line such as `header-open-only: NO-XXH64 single-segments wnd-MAX:5 content-size-frame-max:5 content-size-total:5` and emits neither `skip-frames:1` nor `skip-frames-size-total:8`.

The logical extracted filename is derived from the `.zst` name and preserves Unicode. `x`, `-so`, `l`, `-slt`, `t`, and hashing the compressed file all work. Bad magic returns nonzero with `Open ERROR: Cannot open the file as [zstd] archive`, `Is not archive`, and `Can't open as archive: 1`. Truncated compressed data returns nonzero with stderr `ERROR: Unexpected end of data` and an stdout sub-item error count. A zstd-compressed TAR extracts first to the correct 10240-byte `.tar` payload.

## Spec 28

`-si` makes add read a single member payload from stdin. `-siName` names the archived member `Name`; forms used include simple names, Unicode/special names, and nested names such as `subdir/nested/file.txt`. Bare `-si` uses the 7-Zip default stdin member name (including the expected empty-name/default-name metadata behavior) and supports empty input. stdin compression works for 7z, ZIP, gzip, bzip2, xz, encryption, solid mode, all compression levels, NUL-containing binary data, random multi-megabyte data, and repeated invocations.

`-so` on `x`/`e` writes selected uncompressed bytes only. One selected file yields exactly its content; multiple selected members are concatenated in archive order with no separators. For archives created from multiple file operands, that stored order is ascending by pathname rather than original operand order: adding `z-last.txt`, `a-first.txt`, then `m-middle.txt` makes `x -so` emit the contents of `a-first.txt`, `m-middle.txt`, and `z-last.txt` in that order. Status, header, prompts, and diagnostics must go to stderr or be suppressed so stdout remains byte-exact. Normal extraction without `-so` creates files and does not echo payloads. Listing with stdin as its archive source is unsupported and reports `ERROR:  : opening : E_NOTIMPL : Not implemented` plus `System ERROR:\nE_NOTIMPL : Not implemented` with nonzero status. A pipeline from `a -si` to later `x -so` must preserve every byte. The `-scrc` family is also accepted on extraction commands and may request checksum calculation while extraction still produces exact files or stdout bytes.

## Spec 29

The `h` command hashes files or stdin and returns 0 on success. With no `-scrc`, it uses CRC32. It supports CRC32 (8 uppercase hex digits), CRC64 (16 uppercase hex digits), SHA1 (40 hexadecimal digits), SHA256 (64 hexadecimal digits), XXH64 (16 uppercase hex digits), and `-scrc*` to show all supported digests. Repeated compatible `-scrc` switches are accepted and must at least display the final requested algorithm; when CRC32 and SHA256 are requested together, output includes both algorithms and both data-summary digest lines.

Textual hash output begins with `Scanning`, then uses the same singular/plural and upward KiB rounding as Spec 7: a 10,240-byte input says `1 file, 10240 bytes (10 KiB)`. The table headings include the algorithm(s), `Size`, and `Name`; the header, item rows, and summary row are separated by rules containing `--------` (the CRC32 form is `-------- -------------  ------------`). It shows each file's digest, exact size, and name, a combined/summary digest row, `Size: <total>`, lines such as `CRC32  for data:` or `SHA256 for data:`, and `Everything is Ok`. Bare `h -si` labels its stdin item `[Content]`. Hashes are genuine: the same bytes produce the same value, different bytes differ, directories recurse when requested, stdin is hashed exactly, and empty SHA256 is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Missing hash inputs return 1 and use the same dual-channel warning form as Spec 8. In particular stdout contains the `Scan WARNINGS for files and folders:` block, the `<name> : errno=2 : No such file or directory` detail, its separator, and `Scan WARNINGS: 1`; stderr contains the `WARNING:` form.

## Spec 30

`-pPassword` enables encryption and accepts long and Unicode passwords as exact argument text. In 7z, file data uses AES-256-compatible `7zAES`; technical listing shows `Encrypted = +` and includes `7zAES` in the file/archive method. `-mhe=on` also encrypts headers, so listing without the password cannot reveal member names; supplying the exact password allows list/test/extract/update/delete. A password provided for an unencrypted archive is harmless and does not prevent extraction.

If an operation needs a password but none is supplied in a noninteractive captured-input environment, print `Enter password:` and terminate nonzero with `Break signaled`, rather than hanging. An incorrect password returns 2, creates no usable plaintext (a ZIP target may exist as zero bytes), writes an error such as `ERROR: Data Error in encrypted file. Wrong password? : <name>` or `ERROR: Wrong password`, and reports `Sub items Errors: 1` / `Archives with Errors: 1`. Encryption works with large, empty, multiple, selectively extracted, differently compressed, stdin, solid, and SFX data.

## Spec 31

ZIP encryption supports traditional ZipCrypto by default when `-p` is used and AES-256 when `-mem=AES256` is supplied. Technical listing reports `Encrypted = +` and identifies `ZipCrypto` or `AES-256` as appropriate. For ZipCrypto, the `Method =` value starts with the encryption token and then the compression method, such as `Method = ZipCrypto Deflate` or `Method = ZipCrypto Store`. Both modes genuinely protect bytes, accept the exact supplied password, round-trip data, reject wrong passwords nonzero, and remain compatible with the ZIP compression methods and update/list/test behavior described above.

An ordinary encrypted 7z archive without encrypted headers may be listed without decrypting file data and shows names/encryption metadata. A header-encrypted archive requires its password even for listing. Encryption state and password remain effective when an archive is updated or members are deleted.

## Spec 32

`-v<size>[b|k|m|g|t]` creates sequential split files named `<archive>.001`, `.002`, ..., with three-digit, contiguous numbering. With no suffix the profile's default unit is used; `b` is bytes and `k`/`m`/`g`/`t` are binary multiples. Every part except the last is exactly the requested size; the last is the remainder. A payload may span parts, small sets may fit in one `.001`, and at least 100 volumes are supported. Success output includes `Archive size:`, `Volumes:`, and `Everything is Ok`.

Opening `.001` discovers all parts, reports an outer `Type = Split`, volume count and total physical size, then the inner archive properties and members. Listing/testing/selective extraction/full extraction works for complete split 7z and ZIP output, with compression, solid mode, encryption, empty files, mixed sizes, Unicode/special names, and case-distinct names. Listing a later numbered part may locate the first part and list the set, but extraction directly from a non-first part fails with status 2 and `Cannot open the file as archive`. Extraction from `.001` after a middle or last volume is missing returns 2. Without `-so`, stdout includes `Can't open as archive: 1`, `Files: 0`, `Size:       0`, and `Compressed: 0`; with `-so`, stdout is empty. In both cases stderr reports `ERROR: x.7z.001`, `Open ERROR: Cannot open the file as [7z] archive`, and `Unexpected end of archive`. A corrupted present part similarly fails with CRC/sub-item errors as appropriate. `-v0` specifically returns 7 with stderr `Command Line Error:` and `zero size last volume is not allowed`; other malformed, invalid-suffix, or overflowing volume sizes use their observed `Incorrect volume size:` diagnostics.

## Spec 33

File metadata is preserved according to container capability. 7z, TAR, ZIP, CAB, and SFX round trips retain modification time within the source format's precision; 7z technical output may show 100-nanosecond fractions, TAR/PAX may show nanoseconds, and ZIP time may be DOS-resolution unless an NTFS extra field supplies a precise time. `-stl` sets the completed archive file's modification time to the newest input modification time, or current time for an empty archive. `-ssp` avoids changing source access times during compression. `-mtc` and supported time-type settings are accepted without corrupting archives.

Unix executable (`0755`), read-only (`0444`), ordinary file, directory, symlink, FIFO, and device-type mode bits are displayed accurately and restored safely where applicable. Extracted executables remain runnable. Directory-only archives and explicit empty directories retain their hierarchy. Sizes, CRCs, and timestamps in listings must come from archive metadata, not from similarly named current filesystem files.

## Spec 34

Without `-snl`, symlinks are followed and their target data/directory tree is archived as ordinary content; links outside the selected root may likewise be followed. With `-snl`, store the link itself, including its exact relative or absolute target text, broken targets, `./` prefixes, long targets, chains, circular pairs, permissions/type, and target-string size. On extraction recreate each safe stored link as an actual symbolic link with exactly that link text. A stored circular pair is not fully recreated: for an archive made from `broken -> missing-target`, `first -> second`, and `second -> first` in that order, extraction creates `broken` and `first`, refuses `second`, returns 2, writes `ERROR: Dangerous link via another link was ignored : second : first` to stderr, and reports `Sub items Errors: 1` and `Archives with Errors: 1` on stdout. Circular stored links must not be traversed. A recursive traversal loop without `-snl` terminates with a warning such as `errno=40 : Too many levels of symbolic links` rather than hanging.

Without `-snh`, hard-linked files are stored as independent regular file entries. With `-snh`, preserve hardlink relationships where the format supports them; technical TAR output uses `Hard Link = <target>`, while all names remain readable after extraction. Mixed regular/symbolic/hardlink archives support update, delete, test, and selective extraction. Overwrite must correctly replace or preserve links according to the selected overwrite mode and never write through an unintended link target.

## Spec 35

`-sfx[<module>]` creates a self-extracting artifact by byte-for-byte prepending the named module to a valid 7z archive. Bare `-sfx` looks for `7zCon.sfx`; if absent, return 2. Stdout contains the normal header followed by `Error:`, `cannot find specified SFX module`, `7zCon.sfx`, and `errno=2 : No such file or directory`; stderr contains `System ERROR:` and `errno=2 : No such file or directory`. A nonexistent explicit module such as `-sfxnonexistent.exe` follows the same routing and prints `nonexistent.exe` verbatim in the stdout error block.

With a supplied module, output contains `Write SFX: <module> : <exact module bytes> bytes (<rounded KiB>)`. The produced file begins with the module bytes (an ELF module therefore begins `7F 45 4C 46`), and the 7z signature occurs exactly at `module_size`; reported `Archive size` equals the complete output file length. The appended 7z portion supports empty archives, directories, multiple/special-name/large files, `-mx`, `-mmt`, filters, excludes, timestamps, solid mode, stdin, password/header encryption, update, listing as `Type = 7z`, testing, and extraction. Listing the complete compound artifact with `-t#` exposes a `Type = #` container and the nested archive location/size. The output file need not have executable permission merely because it contains an executable stub.

## Spec 36

Output-control flags alter routing/verbosity without changing archive bytes. `-bb0` suppresses per-file action lines; `-bb1`, `-bb2`, and `-bb3` progressively include lines such as `+ file.txt` or `U file.txt`, with level 3 more verbose than level 0. Out-of-range `-bb10` is tolerated by the tested update path rather than crashing. `-bd` disables progress indicators while retaining final results. `-y` assumes yes for questions.

`-bso0` suppresses ordinary stdout entirely; `-bso1` routes ordinary output to stdout; `-bso2` routes it to stderr. `-bse1` routes errors/warnings to stdout and leaves stderr empty for that channel. `-bsp2` routes progress to stderr. `-bt` appends timing lines for `Kernel  Time`, `User    Time`, `Process Time`, and `Global  Time`; values are decimal durations with percentages and global time is shown as 100%. Without `-bt`, those four lines do not appear. These controls compose with one another and with compression switches.

## Spec 37

`-spf` and `-spf2` preserve fully qualified input paths in archive member naming, with technical listing visibly containing the original absolute path. Without them, absolute source operands do not cause extraction outside the destination: their safe basename/relative selection is stored. `-slp` (large pages) and valid `-stm<hex mask>` affinity settings such as `-stm1` and `-stmFF` are accepted and operations still succeed. Invalid affinity text returns the syntax error specified earlier.

The implementation must avoid path truncation, accidental path normalization that changes Unicode/special names, and archive-name confusion when names contain spaces or `#`. Extraction must create only intended paths under the chosen destination except where explicit fully-qualified mode semantically requests otherwise; no archive member may escape via ordinary relative `..` traversal.

## Spec 38

The `i` command returns 0, writes no stderr, and produces a substantive capabilities report with `Formats:`, `Codecs:`, and `Hashers:` sections. Format rows include create/extract capability flags, extensions, and signature bytes. At minimum list 7z with `7 z BC AF ' 1C`, ZIP with `P K 03 04` and alternative signatures separated by `||`, TAR with `u s t a r` at `offset=257`, and gzip with `1F 8B 08`. Extension lists include `gz gzip tgz`, `txz`, and common ZIP containers such as `jar`, `docx`, and `xlsx`.

Codec rows include encoder/decoder/filter flags and IDs and name at least Copy, LZMA, LZMA2, PPMD, BZip2, Deflate, Deflate64, BCJ, BCJ2 (ID `303011B`), ARM, ARM64, ARMT, PPC, IA64, SPARC, Delta, 7zAES, and AES256CBC; Deflate ID `40108` is shown. Hasher rows show digest byte widths and IDs/names for CRC32 (4), CRC64 (8), SHA1 (20), SHA256 (32), and XXH64 (8). The normal version/build/locale/thread header precedes these sections.

## Spec 39

The `b` benchmark command must complete within a short command timeout and print a nonempty benchmark/build description containing the normal 7-Zip header, `Compiler:`, `CPU`, `Freq`, `Linux`, and `PageSize`. It accepts method properties used to request a small dictionary and thread count; for `b -md=256k -mmt1`, the settings line is the literal ` d=256k mt1`. Benchmark output need not have stable timing values, but must be structurally valid and must not allocate unreasonable resources for a minimal invocation.

## Spec 40

Exit statuses and diagnostic channels are part of the interface: 0 means success (including a valid no-op selection/delete/rename), 1 means completion with scan warnings, 2 means fatal/archive/data/system failure, and 7 means command-line/user error. Missing archive files for list/extract/test return 2 and stderr includes `ERROR: errno=2 : No such file or directory`, the path, and `System ERROR:`. A plain file or corrupt/truncated archive must never be accepted merely because of its suffix. Depending on parse progress, diagnostics include `Open ERROR: Cannot open the file as [<type>] archive`, `ERRORS:`, `Is not archive`, `Headers Error`, `Unexpected end of archive`, or `Data Error`; stdout summaries include `Can't open as archive: 1`, `Files: 0`, `Size:       0`, `Compressed: 0`, or `Errors: 1` as appropriate.

Success status text, archive property text, warning/error spelling, blank-line-separated structure, and stdout/stderr placement follow the templates defined throughout this specification. All operations must terminate promptly on malformed archives, missing volumes, password prompts with closed stdin, symlink cycles, impossible sizes, and malformed encodings. No failed operation may claim `Everything is Ok`, silently emit incorrect payload bytes, or leave a newly written archive presented as valid when its operation did not complete.
