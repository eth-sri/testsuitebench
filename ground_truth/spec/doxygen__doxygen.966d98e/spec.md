# Clarified executable specification

The deliverable is a directly invokable program named exactly `executable`. It is a compact, Doxygen-compatible command-line program. All paths supplied by the caller are interpreted relative to the caller's current working directory unless they are absolute. Text output is UTF-8. Successful modes return status 0; validation, missing-input, and missing-file failures return a nonzero status as detailed below.

## Spec 1

The command-line interface is mode based, not subcommand based. The supported top-level forms are:

```text
executable [-s] -g [configName]
executable [-s] -u [configName]
executable [configName]
executable -l [layoutFileName]
executable -w rtf styleSheetFile
executable -w html headerFile footerFile styleSheetFile [configFile]
executable -w latex headerFile footerFile styleSheetFile [configFile]
executable -e rtf extensionsFile
executable -x [configFile]
executable -x_noenv [configFile]
executable -f emoji outputFileName
```

It must also recognize `--help`, `-h`, `-?`, `-v`, `-V`, `-d`, and `-q`. A mode that writes to a named path must create that path in the current directory when given a relative name. Every invocation exercised by this specification must terminate within four seconds.

## Spec 2

`--help`, `-h`, and `-?` are successful help modes. Each writes a Doxygen version heading and the usage information to standard output; using the same help for all three is appropriate. For `--help`, standard error is empty and standard output ends with a newline. The help option has precedence: for example, `executable --help --this-flag-should-not-exist` still succeeds, emits normal help, and emits no error.

Except that an implementation may substitute the actual invocation path wherever `./executable` appears, the help output is the following. Keeping it literally as shown is acceptable and is the most deterministic behavior:

```text
Doxygen version 1.17.0
Copyright Dimitri van Heesch 1997-2025

You can use Doxygen in a number of ways:

1) Use Doxygen to generate a template configuration file*:
    ./executable [-s] -g [configName]

2) Use Doxygen to update an old configuration file*:
    ./executable [-s] -u [configName]

3) Use Doxygen to generate documentation using an existing configuration file*:
    ./executable [configName]

4) Use Doxygen to generate a template file controlling the layout of the
   generated documentation:
    ./executable -l [layoutFileName]

    In case layoutFileName is omitted DoxygenLayout.xml will be used as filename.
    If - is used for layoutFileName Doxygen will write to standard output.

5) Use Doxygen to generate a template style sheet file for RTF, HTML or Latex.
    RTF:        ./executable -w rtf styleSheetFile
    HTML:       ./executable -w html headerFile footerFile styleSheetFile [configFile]
    LaTeX:      ./executable -w latex headerFile footerFile styleSheetFile [configFile]

6) Use Doxygen to generate a rtf extensions file
    ./executable -e rtf extensionsFile

    If - is used for extensionsFile Doxygen will write to standard output.

7) Use Doxygen to compare the used configuration file with the template configuration file
    ./executable -x [configFile]

   Use Doxygen to compare the used configuration file with the template configuration file
   without replacing the environment variables or CMake type replacement variables
    ./executable -x_noenv [configFile]

8) Use Doxygen to show a list of built-in emojis.
    ./executable -f emoji outputFileName

    If - is used for outputFileName Doxygen will write to standard output.

*) If -s is specified the comments of the configuration items in the config file will be omitted.
   If configName is omitted 'Doxyfile' will be used as a default.
   If - is used for configFile Doxygen will write / read the configuration to /from standard output / input.

If -q is used for a Doxygen documentation run, Doxygen will see this as if QUIET=YES has been set.

-v print version string, -V print extended version information
-h,-? prints usage help information
./executable -d prints additional usage flags for debugging purposes
```

## Spec 3

`-v` is the short version mode. It succeeds and writes a line containing version `1.17.0` to standard output. `-V` is extended version mode. It succeeds, writes `1.17.0` to standard output, also includes `sqlite3`, and produces output at least as long as the short version. A conventional extended form places the short version on its first line and includes a later line containing `with sqlite3`.

## Spec 4

`-d` without a following debug specifier is developer-help mode. It succeeds, writes nothing to standard error, and writes a listing to standard output beginning with `Developer parameters:`. The listing must include `-m`, `-b`, `-c <file>`, the debug-level syntax `-d <level> enable a debug level` (allowing alignment whitespace), and the known item `lex:scanner`.

If `-d` has an argument, that argument must be a known debug specifier. An unknown value such as `bogus` is a nonzero failure and the diagnostic must include both `option "-d" has unknown debug specifier` and the supplied value.

## Spec 5

Unknown options are errors. This applies to unknown long options such as `--no-such-flag` and `--nonexistent-flag`, and unknown short options such as `-Z`. Return nonzero and emit a diagnostic, on either output stream, containing the case-sensitive fragments `error:`, `Unknown option`, and the exact offending option. `-q` does not hide or alter such parser errors: `-q --no-such-flag` must still return nonzero and contain `error: Unknown option`.

A bare non-option token is a configuration filename, not a subcommand. If it does not exist, it is handled as a missing configuration file rather than as an unknown subcommand.

## Spec 6

Argument-count and format validation must occur before carrying out malformed modes:

- `-w` with no next argument fails nonzero and contains `error:` and `option "-w" is missing format specifier`.
- `-w bogus` (or `-w invalid file.txt`) fails nonzero and identifies the illegal format. For `bogus`, the diagnostic contains `error:`, `Illegal format specifier`, and `bogus`.
- `-w rtf` without its output filename fails nonzero with a diagnostic containing `missing`.
- `-e` with no format fails nonzero and contains `error:` and `option "-e" is missing format specifier`.
- `-e` accepts only `rtf`; for example `-e html out` fails nonzero and contains `error:` and `option "-e" has invalid format specifier`.
- `-f` without its list specifier fails nonzero with a diagnostic containing `missing` (preferably `missing list specifier`).

When an action mode has been successfully selected and completed, later action arguments need not be processed. In particular, `-g cfgA -g cfgB` succeeds, creates `cfgA`, and does not create `cfgB`.

## Spec 7

Configuration-template generation is selected by `-g`. With no filename it writes a file named `Doxyfile` in the current working directory. With a filename it writes that file. With filename `-`, it writes the template to standard output, writes nothing to standard error, and creates no files.

The normal template is UTF-8 text longer than 1,000 bytes, ends in a newline, and begins exactly:

```text
# Doxyfile 1.17.0
```

Near its beginning it includes the prose `This file describes the settings`. It contains ordinary `KEY = VALUE` settings for at least `DOXYFILE_ENCODING`, `PROJECT_NAME`, `OUTPUT_DIRECTORY`, `INPUT`, `RECURSIVE`, `QUIET`, `EXTRACT_ALL`, `GENERATE_HTML`, and `GENERATE_LATEX`. Its usable defaults include an empty output directory, HTML generation enabled, and LaTeX generation enabled.

## Spec 8

`-s` may precede `-g` and requests a comment-suppressed configuration template. This mode has all the same file/stdout routing and success behavior as `-g`. Its output is nonempty and still begins with `# Doxyfile 1.17.0`, contains section-title text including `Project related configuration options`, and contains configuration names including `DOXYFILE_ENCODING`. It must not contain the two-character sequence `##`; item-level explanatory comments are omitted. The ordinary, non-`-s` template is not subject to that restriction.

## Spec 9

Configuration updating is selected by `-u`. The optional filename defaults to `Doxyfile`. The named file must already exist; otherwise the command fails nonzero with text indicating an error or that the file was not found. For an existing configuration, update it in place, return success, preserve its meaningful supplied settings, add the current set of template settings, and make the result begin with `# Doxyfile 1.17.0\n`. Updating a one-line file containing `PROJECT_NAME = X` must make the file larger.

## Spec 10

Layout-template generation is selected by `-l`. With no output name, create `DoxygenLayout.xml` in the current directory and return success. With a named output path, create that path. With output name `-`, return success, send the layout to standard output, and create no files.

The generated content is nonempty XML: after optional whitespace it starts with `<?xml`, contains a `<doxygenlayout` element (case-insensitive matching of the element name is acceptable), and therefore includes the words `xml` or `layout`.

## Spec 11

Template asset generation supports these successful forms:

- `-w rtf FILE` creates a nonempty RTF style/template file at `FILE`.
- `-w html HEADER FOOTER STYLESHEET` returns success and creates template assets; creating all three named files is preferred and at least one must be created.
- `-w latex HEADER FOOTER STYLESHEET` returns success and creates template assets; creating all three named files is preferred and at least one must be created.
- `-e rtf FILE` returns success and creates the RTF extensions file at `FILE`.

## Spec 12

The built-in emoji list is selected by `-f emoji OUTPUT`. With a normal path, return success and create the list at that path. With `OUTPUT` equal to `-`, return success and emit it to standard output. The format is one colon-delimited emoji token per line. The first line must be exactly `:+1:`; later lines must include `:-1:` and `:100:`.

## Spec 13

Documentation-run mode reads configuration from the named file, from `Doxyfile` when no name is supplied, or from standard input when the sole configuration name is `-`. Configuration is line oriented and recognizes `NAME = VALUE` assignments, ignoring blank lines and comments. At minimum it must implement `PROJECT_NAME`, `OUTPUT_DIRECTORY`, `INPUT`, `QUIET`, `GENERATE_HTML`, `GENERATE_LATEX`, `GENERATE_XML`, `GENERATE_MAN`, `GENERATE_RTF`, `GENERATE_DOCBOOK`, `GENERATE_PERLMOD`, and `GENERATE_TREEVIEW`. Boolean values `YES` and `NO` are case-insensitively valid.

Before using values in a normal documentation run, replace references of the form `$(NAME)` with the value of environment variable `NAME`. This applies to paths and ordinary setting values. Thus `OUTPUT_DIRECTORY = $(HOME)/out` creates `out` beneath the process's `HOME`. If a boolean setting has an invalid value such as `QUIET = MAYBE`, continue successfully, use that setting's default (`NO` for `QUIET`), and emit standard-error text containing both `not a valid boolean value` and `Using the default: NO`.

## Spec 14

A valid documentation run always creates `OUTPUT_DIRECTORY`, even when every output format is disabled. An empty `OUTPUT_DIRECTORY` means the current working directory. Enabled formats create their conventional subdirectories beneath it: at minimum, `GENERATE_HTML = YES` creates `html/`, and `GENERATE_LATEX = YES` creates `latex/`. Consequently, running a freshly generated default `Doxyfile` creates `html` and `latex` directories in the current directory.

When no input files are configured, the run still succeeds and emits a warning on standard error containing `warning:` and/or `No files to be processed`. This warning remains observable both when configuration has `QUIET = YES` and when it has `QUIET = NO`. Invoking the documentation run with command-line `-q` must produce no standard-output progress text, but the no-input warning on standard error remains allowed and required for a freshly generated empty-input configuration.

## Spec 15

Configuration comparison is selected by `-x` or `-x_noenv`; its optional filename defaults to `Doxyfile`, and filename `-` reads configuration from standard input. A successful comparison writes a textual difference from the default template to standard output and writes nothing to standard error for valid input. Its first line starts with:

```text
# Difference with default Doxyfile
```

Changed settings are included in readable assignment form. For example, comparing standard input `PROJECT_NAME = X\n` includes both `PROJECT_NAME` and `= X`.

`-x` expands `$(NAME)` environment references before displaying changed values. `-x_noenv` deliberately leaves those references literal. For example, if `HOME` is `/tmp/home` and a file contains `OUTPUT_DIRECTORY = $(HOME)/out`, `-x` output contains `/tmp/home/out`, while `-x_noenv` output contains `$(HOME)/out`.

## Spec 16

Missing configurations have consistent failure behavior. If documentation-run mode is given a nonexistent filename, return status 1, write `error: configuration file NAME not found!` to standard error using the supplied `NAME`, and write the normal usage/help text to standard output. If no arguments are supplied and the current directory has no `Doxyfile`, return status 1, write exactly `error: Doxyfile not found and no input file specified!` followed by a newline to standard error, and write byte-for-byte the same complete normal help output to standard output as `--help` writes when invoked by the same executable path. This is the entire help output described in Spec 2, not merely its `You can use Doxygen in a number of ways:` introduction.

Likewise, `-x` with no explicit filename uses `Doxyfile`; if that file is absent, return nonzero and include all of `error:`, `Doxyfile not found`, and `no input file specified` in the combined output. These diagnostics are not suppressed by `-q`.
