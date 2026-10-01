# Executable specification

The required artifact is a file named exactly `executable`. It is a command-line image compressor and converter. All text is UTF-8. Unless a section below says otherwise, successful invocations exit 0, command-line parsing errors exit 2, and fatal input-discovery errors exit 255.

## Spec 1

`executable` is a single-command program, invoked as `executable [OPTIONS] [FILES]...`. It has no subcommands or command aliases. Every option is global, and positional tokens such as `add`, `compress`, `help`, or `nonexistent_subcommand` are file/directory names rather than commands. Help and error text must never contain a `Commands:`/`Subcommands:` section or describe an unknown subcommand.

Options may appear before, after, or among positional paths. Long options that take values accept either `--option value` or `--option=value`. Boolean short options can be combined (for example, `-Rd` means recursive plus dry-run). A standalone `--` ends option parsing, so every later token is a positional path even if it begins with `-`.

## Spec 2

`--version` and `-V` exit 0, write nothing to stderr, and write exactly this line, including its final newline, to stdout:

```text
caesiumclt 1.3.0
```

The version options do not require a compression mode, destination, or input.

## Spec 3

When the parser reaches `--help`, it immediately exits 0, writes nothing to stderr, and writes exactly the following text to stdout, including the final newline:

```text
A fast and efficient lossy and/or lossless image compression tool

Usage: executable [OPTIONS] <--quality <QUALITY>|--lossless|--max-size <MAX_SIZE>> <--output <OUTPUT>|--same-folder-as-input> [FILES]...

Arguments:
  [FILES]...
          Input files or directories to process

Options:
  -q, --quality <QUALITY>
          Compression quality [0-100], higher values mean better quality

      --lossless
          Use lossless compression (may increase file size for some formats)

      --max-size <MAX_SIZE>
          Target maximum file size in bytes or human-readable format (e.g., 100KB, 0.5MB)

      --width <WIDTH>
          Output image width in pixels (preserves the aspect ratio if height not set)

      --height <HEIGHT>
          Output image height in pixels (preserves the aspect ratio if width not set)

      --long-edge <LONG_EDGE>
          Size in pixels for the longest edge of the image

      --short-edge <SHORT_EDGE>
          Size in pixels for the shortest edge of the image

      --no-upscale
          Prevents upscaling of the image when resizing

  -o, --output <OUTPUT>
          Output directory path

      --same-folder-as-input
          Use input file's directory as output (WARNING: may overwrite originals)

      --format <FORMAT>
          Convert to the selected output format or keep the original
          
          [default: original]
          [possible values: jpeg, png, gif, webp, tiff, original]

      --png-opt-level <PNG_OPT_LEVEL>
          PNG optimization level [0-6], higher values provide better compression
          
          [default: 3]

      --jpeg-chroma-subsampling <JPEG_CHROMA_SUBSAMPLING>
          Chroma subsampling for JPEG files
          
          [default: auto]
          [possible values: 4:4:4, 4:2:2, 4:2:0, 4:1:1, auto]

      --jpeg-baseline
          Output baseline JPEG instead of progressive (default)

      --zopfli
          Use zopfli for PNG optimization (significantly slower but better compression)

  -e, --exif
          Keep EXIF metadata during compression

      --keep-dates
          Preserve original file timestamps

      --strip-icc
          Strips ICC profile info on JPG files, ignoring the -e flag

      --suffix <SUFFIX>
          Add suffix to output filenames

  -R, --recursive
          Scan subfolders recursively when input is a directory

  -S, --keep-structure
          Preserve directory structure (requires -R/--recursive)

  -d, --dry-run
          Simulate compression without writing files

      --threads <THREADS>
          Number of parallel jobs (0 = auto-detect, max = available processors)
          
          [default: 0]

  -O, --overwrite <OVERWRITE>
          Policy for handling existing output files

          Possible values:
          - all:    Always overwrite existing files
          - never:  Never overwrite existing files
          - bigger: Overwrite only if the existing file is bigger
          
          [default: all]

      --min-savings <MIN_SAVINGS>
          Minimum compression savings required to write an output file. Use percentage (e.g., '10%', '1.5%'), absolute size (e.g., '100KB', '1MB'), or plain number as bytes

  -Q, --quiet
          Suppress all output

      --verbose <VERBOSE>
          Verbosity level: 0 = quiet, 1 = progress only, 2 = errors only, 3 = all
          
          [default: 1]

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

This short-circuits later tokens and post-parse validation. For example, `--quality 5 --lossless --help` displays help rather than reporting the compression-mode conflict, and `--help --nonexistent` ignores the later unknown option. It does not retroactively override a parser error encountered before it. In particular, `--nonexistent --quality 5 --lossless --help` exits 2 with empty stdout and exactly this stderr:

```text
error: unexpected argument '--nonexistent' found

  tip: to pass '--nonexistent' as a value, use '-- --nonexistent'

Usage: executable [OPTIONS] <--quality <QUALITY>|--lossless|--max-size <MAX_SIZE>> <--output <OUTPUT>|--same-folder-as-input> [FILES]...

For more information, try '--help'.
```

`-h` also exits 0 and uses stdout only, but prints a shorter, non-identical summary. It must contain the description, a `Usage:` line mentioning `executable` and `[FILES]...`, and at least the quality, lossless, and output options. A token `--help` after a standalone `--` is instead an input path and must not display help.

## Spec 4

Exactly one compression mode is required: `-q/--quality`, `--lossless`, or `--max-size`. Exactly one destination is also required: `-o/--output` or `--same-folder-as-input`. Missing either group is a parser error (exit 2, empty stdout, diagnostic and a `Usage:` line on stderr). The diagnostic contains `required arguments were not provided` and names each missing group exactly as:

```text
<--quality <QUALITY>|--lossless|--max-size <MAX_SIZE>>
<--output <OUTPUT>|--same-folder-as-input>
```

The three compression modes conflict pairwise, and the two destinations conflict. In the exact tested order, quality plus lossless produces this stderr:

```text
error: the argument '--quality <QUALITY>' cannot be used with '--lossless'

Usage: executable <--quality <QUALITY>|--lossless|--max-size <MAX_SIZE>> <--output <OUTPUT>|--same-folder-as-input> [FILES]...

For more information, try '--help'.
```

Output plus same-folder produces:

```text
error: the argument '--output <OUTPUT>' cannot be used with '--same-folder-as-input'

Usage: executable <--quality <QUALITY>|--lossless|--max-size <MAX_SIZE>> <--output <OUTPUT>|--same-folder-as-input> [FILES]...

For more information, try '--help'.
```

## Spec 5

All value-taking options diagnose a missing value as a parser error with text containing `a value is required for` and `but none was supplied`. This applies to `--max-size`, `-o/--output`, `--format`, `--threads`, `--suffix`, `--verbose`, `--png-opt-level`, `--jpeg-chroma-subsampling`, `--width`, `--height`, `--long-edge`, `--short-edge`, `-q/--quality`, and `-O/--overwrite`.

An unknown option is a parser error. For example, `--nonexistent` produces text containing `unexpected argument '--nonexistent' found` and `tip: to pass '--nonexistent' as a value, use '-- --nonexistent'`. If the same token occurs after `--`, it is treated as a path and reaches input discovery instead.

`--threads` is an unsigned 32-bit integer. `--threads=-1` reports an invalid value and includes `-1 is not in 0..=4294967295`; when written as `--threads -1`, the negative token is parsed as an unexpected option and the diagnostic includes `tip: to pass '-1' as a value, use '-- -1'`.

## Spec 6

Quality is an integer from 0 through 100 inclusive. Floats and non-numbers are rejected. The exact stderr forms for representative failures are:

```text
error: invalid value '150' for '--quality <QUALITY>': Quality must be between 0 and 100, but got 150

For more information, try '--help'.
```

```text
error: invalid value 'abc' for '--quality <QUALITY>': 'abc' is not a valid number

For more information, try '--help'.
```

The same templates use the actual supplied value (for example, 101), and `80.5` is reported as not a valid number.

PNG optimization level is an integer from 0 through 6. The exact representative error is:

```text
error: invalid value '10' for '--png-opt-level <PNG_OPT_LEVEL>': PNG optimization level must be between 0 and 6, but got 10

For more information, try '--help'.
```

Verbosity is an integer from 0 through 3. Non-numbers are rejected as not valid numbers. The exact representative range error is:

```text
error: invalid value '10' for '--verbose <VERBOSE>': Verbosity must be between 0 and 3, but got 10

For more information, try '--help'.
```

`--format` accepts only `jpeg`, `png`, `gif`, `webp`, `tiff`, and `original`; an invalid value reports those possible values. `--overwrite` accepts only `all`, `never`, and `bigger`. JPEG chroma subsampling accepts only `4:4:4`, `4:2:2`, `4:2:0`, `4:1:1`, and `auto`; invalid `4:2:1` includes `tip: a similar value exists: '4:1:1'`.

## Spec 7

Input paths may be absolute or relative to the process working directory and may contain spaces, Unicode, uppercase extensions, or no extension. Detect supported image content sufficiently to accept an extensionless JPEG and preserve its extensionless output name when the output format is `original`.

Directly supported input image types are JPEG, PNG, WebP, and GIF. Format matching is case-insensitive, but original spelling/case of a filename and extension is retained when no conversion is requested. TIFF is intentionally not a direct input type and TIFF files found in a directory are ignored. `--format tiff` is nevertheless a supported output conversion.

A single nonexistent path, empty directory, unsupported file, empty/corrupt file that cannot be recognized, or a set containing no supported candidates is a fatal discovery failure: exit 255, empty stdout, and stderr containing exactly `Unable to compute the base path for the files.` (a final newline is permitted). A validly parsed invocation with no positional paths is different: it exits 0 and writes `No files to compress` to stderr.

## Spec 8

Each positional path may name a file or directory, and multiple paths are accepted. Without `-R/--recursive`, a directory contributes only supported files immediately inside it. With `-R`, all supported files below it are included. Without `-S/--keep-structure`, outputs from directory trees are flattened into the destination. With `-R -S`, each output preserves the path below the named input directory; the named directory itself is not added. Thus a file directly inside that directory remains at the output root.

`-S` without `-R` is accepted and has no effect on a single file or on the nonrecursive top-level scan. Multiple files from unrelated directories are accepted and placed together in a flat output directory. Invalid or nonexistent paths mixed with at least one discoverable valid image do not prevent processing; such undiscovered paths are omitted from the processed count.

## Spec 9

`-o DIR`/`--output DIR` writes output beneath `DIR` without changing input files. Missing destination directories, including all intermediate components, are created automatically. A relative destination is relative to the process working directory.

`--same-folder-as-input` places each result alongside its source. With no suffix and no format-induced name change, this deliberately replaces the input in place. With a suffix it leaves the original unchanged and creates a distinct sibling.

`--suffix TEXT` inserts `TEXT` after the source stem and before the output extension. For example, `photo.JPG` plus `_compressed` becomes `photo_compressed.JPG`; conversion to PNG at the same time produces `photo_compressed.png`.

## Spec 10

Quality mode (`-q N`/`--quality N`) performs genuine lossy/quality-controlled encoding for JPEG, PNG, WebP, and GIF and creates a nonempty, decodable image of the requested/original format. Unless resizing is requested, pixel dimensions remain unchanged.

For JPEG, increasing quality must not decrease output size for the same input at representative qualities 0, 50, and 100. Quality 0 produces a file smaller than the source (for a typical photographic JPEG, under half its source size), and quality 1 is substantially smaller than quality 50. Quality 100 is still quality-based encoding, not the lossless mode. Re-encoding with a different quality changes content and normally size. For PNG quality compression, output should be no larger than the already supplied source on the representative PNG. Resizing to fewer pixels should produce a smaller result than encoding the full-sized image at the same quality.

## Spec 11

`--lossless` produces valid lossless output for JPEG, PNG, and WebP and preserves dimensions and pixel information. For same-format inputs it is acceptable, and expected for an already compact simple PNG, to copy the bytes unchanged rather than inflate the file. A lossless JPEG result should be at least as large as a low-quality (for example quality 30) JPEG result. Lossless mode also combines with resizing, EXIF preservation, minimum-savings filtering, and format conversion; a lossless PNG-to-WebP conversion produces a valid WebP with the source dimensions.

## Spec 12

`--max-size SIZE` chooses image encoding quality to make the output as close as practical to, without exceeding, the target. It works on JPEG and PNG inputs and with format conversion, and it does not resize the image. Plain nonnegative numbers mean bytes. Decimal human-readable forms such as `50KB`, `100KB`, `0.5MB`, and `1KB` are accepted; SI suffixes use decimal magnitudes (so 10KB is 10,000 bytes and displays as about 9.8 KiB). IEC suffixes such as KiB are also accepted.

When the target is achievable, the resulting file is nonempty and no larger than it, including when converting a PNG to a JPEG. If even the smallest usable encoding cannot meet an extremely small target such as 100 bytes, still exit successfully and emit the smallest practical valid image, substantially smaller than the source. Invalid text is a parser error; for `abc` stderr is exactly:

```text
error: invalid value 'abc' for '--max-size <MAX_SIZE>': Invalid size format: couldn't parse "abc" into a ByteSize, cannot parse float from empty string

For more information, try '--help'.
```

## Spec 13

`--format original` is the default and retains each input's image type and filename extension. Explicit conversions support every tested direction among JPEG, PNG, WebP, and GIF, and conversion from JPEG or PNG to TIFF. Output must be genuinely encoded in the selected type, decodable, and keep the source dimensions unless resize options are supplied. Use these canonical converted extensions: JPEG `.jpg`, PNG `.png`, WebP `.webp`, GIF `.gif`, TIFF `.tiff`. JPEG/PNG/WebP/GIF signatures must agree with the declared format.

Batch conversion applies the selected target to every input. JPEG and PNG specific encoder options apply when that type is the output, even if the source had another type. Conversion can be chained across separate invocations and can be combined with quality, lossless, max-size, suffix, metadata, and resize options, subject to the single-worker batch deadlock in Spec 23. In particular, converting a two-file JPEG/PNG directory to WebP and then converting the resulting two WebPs to GIF completes under automatic parallelism in the observed six-processor setting. With the process restricted to one available processor, the second invocation creates the GIF destination directory but no files, emits nothing on stdout or stderr, and remains running beyond 8 seconds.

## Spec 14

Resize options operate in pixels. `--width W` alone sets width exactly and derives height from the original aspect ratio. `--height H` alone does the converse. Supplying both sets both dimensions exactly and may intentionally distort the image. `--long-edge N` sets whichever original/orientation-aware edge is longer to N and scales the other proportionally. `--short-edge N` similarly sets the shorter edge. Square images scale both dimensions to N.

Aspect-ratio calculations round to the nearest integer (with tolerance of one pixel); for example, 2000x3000 resized to width 333 becomes approximately 333x500, and 550x368 resized to short edge 200 becomes 299x200. Targets from 1 pixel through at least 2000 pixels and extreme explicit aspect ratios such as 1000x10 are supported. Resizing works in batches, in lossless mode, on JPEG/PNG/WebP, and together with conversion, suffixes, and metadata.

The width/height pair may be used together, but either of those options conflicts with either edge option, and `--long-edge` conflicts with `--short-edge`. For the tested width/long-edge ordering, stderr is exactly:

```text
error: the argument '--width <WIDTH>' cannot be used with '--long-edge <LONG_EDGE>'

Usage: executable --width <WIDTH> <--quality <QUALITY>|--lossless|--max-size <MAX_SIZE>> <--output <OUTPUT>|--same-folder-as-input> [FILES]...

For more information, try '--help'.
```

Nonnumeric dimensions are exit-2 parser errors whose messages include `invalid digit found in string`.

## Spec 15

`--no-upscale` affects a requested resize only. Downscaling still occurs normally. If the computed/requested result would enlarge any dimension beyond its corresponding source dimension, cancel the entire resize and retain both original dimensions. This includes an explicit two-dimensional request where one dimension is smaller but the other is larger. Without this flag, upscaling is allowed.

## Spec 16

`--jpeg-chroma-subsampling` controls JPEG outputs and supports `4:4:4`, `4:2:2`, `4:2:0`, `4:1:1`, and `auto` (default). All produce valid JPEGs with unchanged dimensions. At equal quality on a representative photographic image, `4:4:4` must be larger than `4:2:0`. The setting also works during conversion into JPEG.

`--jpeg-baseline` emits a valid baseline rather than progressive JPEG and can be combined with any supported subsampling value.

## Spec 17

`--png-opt-level N` controls PNG optimization, accepts every integer 0 through 6, and defaults to 3. At the same settings, level 6 produces a file no larger than level 0. `--zopfli` enables the slower Zopfli PNG optimization path and may be combined with an explicit optimization level. Both options work for an existing PNG and when converting another image to PNG, always producing a valid image of unchanged dimensions unless resized.

## Spec 18

By default, EXIF metadata is removed, while an embedded JPEG ICC color profile is preserved. `-e/--exif` preserves all available EXIF tags; it must not fail on a file with no EXIF and may preserve metadata on a best-effort basis across format conversion. EXIF preservation continues to work when resizing, using lossless mode, adding a suffix, or preserving dates.

`--strip-icc` removes JPEG ICC profile data when used without `--exif`. When both `--exif` and `--strip-icc` are present, EXIF preservation takes precedence: the JPEG output retains its ICC profile as well as the requested EXIF. Metadata options do not change the output's validity or dimensions.

## Spec 19

Without `--keep-dates`, a newly written output receives a current modification time. With `--keep-dates`, copy both the input's modification time and access time to the output, within normal filesystem precision (the tests require within 0.01 seconds). Date preservation applies to renamed/suffixed outputs and format conversions as well as same-format compression.

## Spec 20

`-O/--overwrite` defaults to `all`:

- `all` writes/replaces the destination unconditionally.
- `never` skips any input whose destination already exists and leaves its bytes and timestamps unchanged.
- `bigger` first obtains the candidate result, then replaces only when the existing destination is larger than the candidate. If the existing destination is equal or smaller, it is left unchanged and counted as skipped.

Overwrite decisions are per file and do not prevent other batch items from running. In-place operation through `--same-folder-as-input` follows the same policy.

## Spec 21

`--min-savings VALUE` evaluates each candidate separately before writing. Savings are `input byte size - candidate byte size`; percentage savings divide that value by input size. Write and count success only when savings are strictly greater than the threshold, otherwise do not create/replace the output and count it as skipped. Equality therefore skips: if an initial encoding measures a saving of exactly N bytes, repeating the same encoding with `--min-savings N` reports `Compressed 1 files (0 success, 1 skipped, 0 errors)` and writes no output file, while a threshold of N-1 writes it. A normal, non-dry-run invocation creates the destination directory before applying the threshold, including when every candidate is skipped; the directory is then present but contains no output for those skipped candidates.

Accepted forms are a decimal percentage (`10%`, `1.5%`, `0.1%`), an absolute decimal unit (`100KB`, `1MB`, `0.5MB`), an IEC unit (`KiB`, `MiB`), or a plain byte count (`1000`). Percentages are inclusive from 0 through 100. A 100% requirement always skips a nonempty output. The threshold works with every compression mode and is applied per file in mixed batches.

At verbosity 3, a threshold skip begins with `[Skipped]`, contains `Insufficient savings:`, and shows the comparison, such as `< 40.00%, skipped` or the normalized absolute threshold `9.8 KiB, skipped` for 10KB. Invalid forms use these exact diagnostics:

```text
error: invalid value '150%' for '--min-savings <MIN_SAVINGS>': Percentage must be between 0 and 100, got 150

For more information, try '--help'.
```

```text
error: invalid value 'xyz' for '--min-savings <MIN_SAVINGS>': Invalid size format: 'xyz'. Use percentage (e.g., '10%'), size with unit (e.g., '100KB', '1MB'), or plain number as bytes

For more information, try '--help'.
```

## Spec 22

`-d/--dry-run` performs input discovery but does not perform candidate encoding or the corresponding minimum-savings and encoder-error accounting. It creates no directories, writes no files, and does not modify existing files. An item that reaches simulated processing is counted as a success, and the aggregate output size is reported equal to the input size. Pre-encoding policy decisions still apply: for example, `--overwrite never` counts an item with an existing destination as skipped. Thus a one-file dry run with `--min-savings 100%` prints `Compressed 1 files (1 success, 0 skipped, 0 errors)` followed by an unchanged size comparison, and a dry run containing one valid image plus the truncated JPEG described in Spec 25 prints `Compressed 2 files (2 success, 0 skipped, 0 errors)`. It exits 0 and combines with quiet mode and multiple inputs.

## Spec 23

`--threads N` selects parallelism without changing results or counts when the batch completes. Its default is 0, meaning automatically choose an appropriate worker count; explicit 0 has the same meaning. Values 2, 4, and counts larger than available processors (for example 999) are accepted and complete normally; an implementation may internally cap workers to available resources.

The value 1 is accepted by the parser but has a multi-file batch deadlock. For a recursive directory containing `a.png`, `b.jpg`, `c.webp`, and `d.gif`, `--quality 70 --threads 1 --recursive --output OUT INPUTS` creates `OUT` and writes a valid 50x40 `OUT/a.png`, but writes no output for the other three inputs before deadlocking. It emits nothing on stdout or stderr and remains running beyond 8 seconds rather than reaching a summary or exit. Automatic parallelism has the same behavior when the process is restricted to one available processor, including the WebP-to-GIF chaining case in Spec 13.

## Spec 24

`-Q/--quiet` and `--verbose 0` suppress both stdout and stderr during a successful processing invocation while still performing work. `--verbose 1` is the default and prints the aggregate summary. Level 2 prints the summary plus skipped/error information. Level 3 additionally prints every per-file success, skip, or error entry. `--quiet` conflicts with an explicitly supplied `--verbose`; in the tested option order stderr is exactly:

```text
error: the argument '--verbose <VERBOSE>' cannot be used with '--quiet'

Usage: executable --verbose <VERBOSE> <--quality <QUALITY>|--lossless|--max-size <MAX_SIZE>> <--output <OUTPUT>|--same-folder-as-input> [FILES]...

For more information, try '--help'.
```

For every discovered item, the final stdout summary has this form:

```text
Compressed N files (S success, K skipped, E errors)
INPUT_SIZE -> OUTPUT_SIZE [SIGNED_DELTA | SIGNED_PERCENT%]
```

The first count is `S + K + E`. Human-readable sizes use `B`, `KiB`, or `MiB`; the second line aggregates byte sizes and includes `->`. Its signed delta and percentage are `output - input`, so a reduction is negative and an increase is positive. A one-file successful run therefore contains `Compressed 1 files (1 success, 0 skipped, 0 errors)`. At level 3 a successful item is preceded by a line such as `[Success] source/path -> destination/path`, its own size comparison, and a blank line. All ordinary successful progress/reporting is on stdout, leaving stderr empty.

## Spec 25

Failure to encode one recognized image is a per-file runtime error, not a fatal batch failure. Continue processing remaining files, exit 0 after the batch, increment the error count, and at verbosity 2 or 3 print an `Error compressing file:` explanation on stdout. Valid outputs from other items must still be written.

A JPEG made by taking the first `max(200, original_size // 8)` bytes of an otherwise valid JPEG is not such an error. In a normal quality-60 run alongside two valid images, it is accepted, encoded to a complete decodable JPEG, and written; verbosity 2 prints no `Error compressing file:` line and the summary is `Compressed 3 files (3 success, 0 skipped, 0 errors)`. Under dry-run it likewise counts as a success without being encoded, as described in Spec 22.

This differs from discovery failure in Spec 7: a totally unusable input set exits 255 before a batch begins. Very small but valid images, read-only input files, special filenames, and mixed valid image formats must process normally.
