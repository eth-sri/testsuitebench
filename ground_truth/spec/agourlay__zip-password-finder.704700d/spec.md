# Clarified specification for `executable`

The required artifact is a directly runnable file named exactly `executable`. It is a command-line ZIP password finder. All text below is case-sensitive, and all shown spaces, blank lines, punctuation, and final newlines are significant where an output is described as exact.

## Spec 1

`executable` is a single-command program, not a program with subcommands. It accepts options directly after its name and attempts to discover the password of one selected member of a ZIP archive. Words such as `add`, `remove`, `list`, `crack`, `help`, `find`, `search`, `run`, `start`, and `stop` have no special command meaning; when supplied as positional arguments they are unexpected arguments.

The program must be directly runnable as `./executable`. Relative paths passed as option values are resolved relative to the current working directory; absolute paths and paths containing spaces must also work.

## Spec 2

The command-line interface consists of these options:

- `-i, --inputFile <inputFile>`: required path to the input ZIP archive.
- `-w, --workers <workers>`: optional positive unsigned integer worker count. If omitted, use the number of physical CPU cores (or an equivalent positive automatically chosen count).
- `-p, --passwordDictionary <passwordDictionary>`: optional path to a password dictionary.
- `-c, --charset <charset>`: optional brute-force charset selector, default `lud`.
- `--charsetFile <charsetFile>`: optional path to a file containing a custom brute-force charset.
- `--minPasswordLen <minPasswordLen>`: optional positive unsigned integer, default `1`.
- `--maxPasswordLen <maxPasswordLen>`: optional positive unsigned integer, default `10`.
- `--fileNumber <fileNumber>`: optional unsigned integer ZIP-member index, default `0`.
- `-s, --startingPassword <startingPassword>`: optional inclusive starting point for brute-force generation.
- `-h, --help`: print help.
- `-V, --version`: print the version.

There are no other options, positionals, subcommands, or configuration-related flags.

## Spec 3

Both `--help` and `-h` must exit `0`, write nothing to standard error, and write exactly the following to standard output, including its one final newline:

```text
Find the password of protected ZIP files

Usage: executable [OPTIONS] --inputFile <inputFile>

Options:
  -i, --inputFile <inputFile>                    path to zip input file
  -w, --workers <workers>                        number of workers
  -p, --passwordDictionary <passwordDictionary>  path to a password dictionary file
  -c, --charset <charset>                        charset to use to generate password [default: lud]
      --charsetFile <charsetFile>                path to a charset file
      --minPasswordLen <minPasswordLen>          minimum password length [default: 1]
      --maxPasswordLen <maxPasswordLen>          maximum password length [default: 10]
      --fileNumber <fileNumber>                  file number in the zip archive [default: 0]
  -s, --startingPassword <startingPassword>      password to start from
  -h, --help                                     Print help
  -V, --version                                  Print version
```

The output must contain no ANSI escape sequences or progress-display control characters.

## Spec 4

Both `--version` and `-V` must exit `0`, write nothing to standard error, and write exactly this single newline-terminated line to standard output:

```text
zip-password-finder 0.10.3
```

## Spec 5

Option values normally follow their option as a separate argument. `--inputFile` and `-i` must also accept an equals form, such as `--inputFile=archive.zip` and `-i=archive.zip`. No positional operands are accepted. A literal `--` does not introduce supported positional arguments.

An option which expects a value must reject a missing value. A value beginning with `-` is parsed as an option rather than as the value for `--startingPassword`; for example, `--startingPassword -x` is a parser error. Repeating `--charset` is a parser error containing both `--charset` and `cannot be used multiple times`.

## Spec 6

Command-line syntax and type errors exit `2`, write the diagnostic to standard error, and write nothing to standard output. With no arguments, the standard-error output is exactly:

```text
error: the following required arguments were not provided:
  --inputFile <inputFile>

Usage: executable --inputFile <inputFile>

For more information, try '--help'.
```

Supplying `--workers 2` without the required input changes the usage synopsis: invoking `executable --workers 2` exits `2`, writes nothing to standard output, and writes exactly:

```text
error: the following required arguments were not provided:
  --inputFile <inputFile>

Usage: executable --inputFile <inputFile> --workers <workers>

For more information, try '--help'.
```

An unknown option supplied after a valid input option produces a diagnostic containing `error: unexpected argument '<argument>' found`, the usage line `Usage: executable --inputFile <inputFile>`, and `For more information, try '--help'.` This applies, for example, to both `--notARealOption` and `--config`. If either unknown option is supplied without a preceding input option, its usage line is instead `Usage: executable [OPTIONS] --inputFile <inputFile>`. An unexpected positional argument after a valid input option also uses that `[OPTIONS]` usage line. A worker value of `-1` is treated as such an unexpected argument and uses the latter form.

A missing option value produces exit `2` and a diagnostic containing `a value is required for` and the affected option. A non-integer value produces exit `2`, text of the form `error: invalid value 'foo' for '--workers <workers>'`, and the cause `invalid digit found in string`. The corresponding displayed option names/placeholders must be used for the other integer options. An unsigned integer too large for the program's integer type produces exit `2` and includes `number too large to fit in target type`. Negative integer spellings are parser errors, not semantic numeric values.

## Spec 7

After successful parsing, application-level validation failures exit `1`, write exactly one newline-terminated diagnostic to standard error unless a later section says otherwise, and write nothing to standard output.

`inputFile`, `passwordDictionary`, and `charsetFile`, when supplied, must name existing regular files. A nonexistent path, an empty path, or a directory is rejected using the applicable exact message:

```text
CLI argument error - "'inputFile' does not exist"
CLI argument error - "'passwordDictionary' does not exist"
CLI argument error - "'charsetFile' does not exist"
```

This validation applies to both short and long option forms. File extensions do not determine whether an input is a ZIP; an existing file is subsequently parsed by content.

## Spec 8

Semantic numeric validation uses these exact exit-`1` diagnostics:

```text
CLI argument error - "'workers' must be positive"
CLI argument error - "'minPasswordLen' must be positive"
CLI argument error - "'maxPasswordLen' must be positive"
CLI argument error - "'maxPasswordLen' must be equal or greater than 'minPasswordLen'"
```

Thus workers, minimum length, and maximum length cannot be zero, and maximum length cannot be smaller than minimum length. Equal minimum and maximum values are valid and mean that exactly that length is searched. Positive worker counts larger than the number of CPUs or candidates, including at least `100`, are valid and must not lose work, deadlock, or crash. Large maximum lengths are valid; a search which finds a short password must stop without first expanding or materializing the entire theoretical search space.

## Spec 9

There are two candidate sources. If `passwordDictionary` is present, dictionary mode is used. Otherwise brute-force mode is used. If a dictionary and `charset` are both supplied, the dictionary controls the candidates and the charset does not filter dictionary entries. `startingPassword` is forbidden in dictionary mode and produces:

```text
CLI argument error - "'startingPassword' cannot be used with a dictionary file"
```

If both `charsetFile` and `charset` are supplied in brute-force mode, the custom charset file takes precedence and the preset selector is ignored.

## Spec 10

The brute-force preset selector is a string whose characters select and union these character groups:

- `l`: `abcdefghijklmnopqrstuvwxyz`
- `u`: `ABCDEFGHIJKLMNOPQRSTUVWXYZ`
- `d`: `0123456789`
- `h`: `0123456789abcdef`
- `H`: `0123456789ABCDEF`
- `s`: the ASCII space and ASCII punctuation/symbol characters

Any combination and order of the selector letters in `ludshH` is accepted, including overlapping groups such as `hd` or `hH`; duplicate resulting characters are removed. The resulting character set is sorted by character/code-point order before generation, so equivalent selector combinations have equivalent behavior. The default selector is `lud`. On the first selector character not in `ludshH`, exit `1` with, for example:

```text
CLI argument error - "Unknown charset option 'x'"
```

The invalid character shown is the actual offending character.

## Spec 11

A custom charset file is read as text and its characters form the generation alphabet. Characters are sorted and duplicates removed: files containing `aabbcc` and `cba` therefore both provide the ordered alphabet `abc`. Unicode characters and special characters are accepted. The file's alphabet replaces, rather than augments, the preset alphabet.

For compatibility, an existing but empty charset file is not rejected during argument validation. When brute-force work starts with it, a worker reports a panic-style diagnostic to standard error containing both `panicked` and `charset non empty`; the overall process exits `0`. This special behavior is distinct from a nonexistent charset file, which is the normal exit-`1` validation error from Spec 7.

## Spec 12

Brute-force mode enumerates every string over the effective alphabet for each length from `minPasswordLen` through `maxPasswordLen`, inclusive. It searches shorter lengths before longer ones. Within a fixed length, use ordinary lexicographic/product order over the sorted alphabet: with alphabet `abc`, length two is `aa`, `ab`, `ac`, `ba`, and so on. The length range is exhaustive unless a correct password is found, in which case all workers terminate promptly.

With a modest explicit worker count, the search must operate incrementally and complete small spaces promptly. In particular, with `--workers 4`, alphabets of a few characters through length four, lowercase through length three, and the default 62-character alphanumeric union through length two must comfortably complete within seconds. With `--workers` omitted, the automatically selected count can make even the default union's length-two search take longer than 12 seconds; the prompt-completion requirement therefore does not apply to that invocation. Multiple workers may partition candidates in any way provided no candidate is omitted and the externally visible result is identical.

## Spec 13

`startingPassword` changes brute-force enumeration to begin at that exact candidate, inclusively, and omit every earlier candidate in the ordering from Spec 12. Thus starting at the target still finds it; starting after the target returns not found. This behavior must remain correct with multiple workers.

Every character in `startingPassword` must belong to the effective generation alphabet, otherwise exit `1` with:

```text
CLI argument error - "'startingPassword' uses characters out of the generation charset"
```

Its character length must be within the inclusive configured minimum/maximum range, otherwise exit `1` with:

```text
CLI argument error - "'startingPassword' does not respect 'max_password_len' or 'min_password_len' configuration"
```

Perform the charset-membership check before the length check when both could fail. An empty starting password is invalid under the required positive minimum length.

## Spec 14

Dictionary mode processes candidates from the first line through the last line and works for empty files, one-line files, large files, and a final line without a newline. Remove the line ending (`LF`, or `CRLF` as a pair) but preserve every other byte/character, including leading spaces, trailing spaces, tabs, embedded spaces, and non-ASCII UTF-8 text. Do not impose the brute-force minimum/maximum lengths on dictionary entries and do not truncate long entries. Blank lines may be treated as empty-password candidates; they must not stop processing later lines. A line that cannot be decoded as UTF-8 is skipped without aborting the remainder of the dictionary.

The dictionary is searched until a matching candidate is found or all candidates are exhausted. Worker counts of 1, 2, 4, 8, and counts exceeding the number of dictionary entries must all retain complete coverage.

## Spec 15

The program parses actual ZIP data and tests each candidate against the member selected by zero-based `fileNumber`; the default `0` selects the first central-directory member. It must support both traditional ZipCrypto-encrypted entries and WinZip AES-128 encrypted entries (including stored/empty content). AES-128 password checking must use the archive salt and the format's PBKDF2-HMAC-SHA1 derivation with 1000 iterations and password-verification/authentication data, so state or derived keys cannot be reused across archives or entries. Candidate text is used as UTF-8 password bytes without trimming or normalization.

Finding a password means the candidate genuinely decrypts/authenticates the selected entry, not merely that it resembles a filename or a known fixture. The supplied encrypted fixtures establish these expected results: `2.test.txt.zip` uses `ab`, `3.test.txt.zip` uses `abc` and contains an empty encrypted member, and `4.test.txt.zip` uses `abcd`. The first members of `password-123.zip`, `password-ABC.zip`, and `password-a1.zip` use `123`, `ABC`, and `a1`, respectively. The implementation must nevertheless work from ZIP content rather than hard-coded paths or names.

## Spec 16

Before searching, validate that `fileNumber` identifies an entry. If it does not, including when the archive has no entries, exit `1`, write nothing to standard output, and write exactly:

```text
File number not found within archive error - '<number>'
```

The quoted number is the requested decimal index (for example `0`, `1`, `99`, or `999`). Explicit `--fileNumber 0` behaves exactly like the default. If another valid index is selected, only that member is used for password checking.

## Spec 17

An existing file which is not a structurally valid ZIP, including plain text, a fake `.zip`, an empty file, or a truncated archive without an end-of-central-directory record, is a runtime error. For the missing-EOCD cases, exit `1`, use standard error only, and write exactly:

```text
Invalid zip file error - invalid Zip archive: Could not find EOCD
```

If the selected ZIP member is not encrypted, do not run an attack. Exit `1` and write:

```text
Invalid zip file error - the selected file in the archive is not encrypted (file_number:<index> file_name:<name>)
```

Substitute the zero-based index and member name exactly as stored in the archive. This includes unencrypted empty or ordinary members.

## Spec 18

A completed search, whether successful or exhausted, exits `0` and writes exactly two newline-terminated lines to standard output and nothing to standard error:

```text
Time elapsed: <duration>
Password found:<password>
```

or:

```text
Time elapsed: <duration>
Password not found
```

There is no space after the colon in `Password found:`. `<password>` is the matching candidate unchanged. `<duration>` is a nonempty human-readable elapsed time made of one or more integer components with units such as `h`, `m`, `s`, `ms`, `us`, or `ns`, separated by spaces; examples include `726us 359ns` and `2s 66ms 930us 753ns`. It must contain at least one decimal digit and unit. Do not emit progress bars, carriage returns, ANSI escapes, debug logs, extra nonempty lines, or timing output on application errors.

Exhausting a valid search without a match is a normal exit-`0` outcome, not an error.

## Spec 19

Workers are an execution detail only: changing the positive worker count must not change candidate semantics, omit boundary candidates, duplicate final output, or alter exit status. The program must coordinate early termination after a match and must not hang when there are more workers than candidates. It must handle AES and ZipCrypto verification safely under concurrent dictionary and brute-force searches.

## Spec 20

The documented command-line arguments and defaults determine runtime behavior. `INPUT_FILE` from the environment cannot satisfy the required option. Explicit command-line values take precedence over potentially conflicting `WORKERS`, `CHARSET`, or `MIN_PASSWORD_LEN` environment values and over a `.zpfrc` file in the configured home directory. `RUST_LOG=debug` must add no debug output. Changing HOME/XDG-related environment variables must not change command-line parsing; in particular, the missing-input diagnostic must be byte-for-byte identical when `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, and `XDG_CACHE_HOME` point to arbitrary paths.
