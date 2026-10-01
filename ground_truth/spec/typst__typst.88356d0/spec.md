# Executable behavioral specification

The required artifact is a single runnable file named `executable`. It is a command-line implementation of Typst version 0.14.2 at commit `ccc34be79ab2555cd26c519b1eab45a3e9ec757a`: a markup typesetter, expression evaluator, document query tool, font inspector, project initializer, file watcher, and shell-completion generator. All paths and examples below are interpreted using the current working directory unless stated otherwise. Output streams are byte streams; textual output is UTF-8.

## Spec 1

`executable --version` and `executable -V` shall succeed, write exactly `typst 0.14.2 (ccc34be7)\n` to standard output, and write nothing to standard error.

The top-level commands are `compile` (alias `c`), `watch` (alias `w`), `init`, `eval`, `query`, `fonts`, `completions`, `info`, and `help`. Long and short help (`--help` and `-h`) succeed and go only to standard output. The main help begins with:

```text
Typst 0.14.2 (ccc34be7)

Usage: executable [OPTIONS] <COMMAND>
```

It has `Commands:`, `Options:`, and `Resources:` sections. It lists all commands above except that the deprecated `query` command need not be advertised. It documents the global options `--color <COLOR>`, `--cert <CERT>`, `-h, --help`, and `-V, --version`, and contains these resource URLs:

```text
https://typst.app/docs/tutorial/
https://typst.app/docs/reference/
https://typst.app/universe/
https://forum.typst.app/
```

The reference URL is labeled exactly `Reference documentation:` in the `Resources:` section.

`help`, `help <command>`, and `<command> --help` provide command help, except that the `help` command itself does not parse `--help` as its help flag. `executable help --help` exits 2, writes nothing to stdout, and writes a diagnostic beginning `error: unrecognized subcommand '--help'` to stderr. An alias's help is byte-for-byte the same as its canonical command's help. `help` without an argument prints the main help. The usage lines are:

```text
Usage: executable compile [OPTIONS] <INPUT> [OUTPUT]
Usage: executable watch [OPTIONS] <INPUT> [OUTPUT]
Usage: executable init [OPTIONS] <TEMPLATE> [DIR]
Usage: executable eval [OPTIONS] <EXPRESSION>
Usage: executable fonts [OPTIONS]
Usage: executable completions <SHELL>
Usage: executable info [OPTIONS]
Usage: executable help [COMMAND]...
```

`help help` has an `Arguments:` section and no `Options:` section. Help takes precedence over otherwise unknown flags when the top-level `--help` occurs before them. `--` terminates option parsing, so `executable -- --help` treats `--help` as an invalid subcommand.

## Spec 2

The long compile help (`help compile` and `compile --help`) shall exactly describe this interface and wording:

```text
Compiles an input file into a supported output format

Usage: executable compile [OPTIONS] <INPUT> [OUTPUT]

Arguments:
  <INPUT>
          Path to input Typst file. Use `-` to read input from stdin

  [OUTPUT]
          Path to output file (PDF, PNG, SVG, or HTML). Use `-` to write output
          to stdout.
          
          For output formats emitting one file per page (PNG & SVG), a page
          number template must be present if the source document renders to
          multiple pages. Use `{p}` for page numbers, `{0p}` for zero padded
          page numbers and `{t}` for page count. For example,
          `page-{0p}-of-{t}.png` creates `page-01-of-10.png`,
          `page-02-of-10.png`, and so on.

Options:
  -f, --format <FORMAT>
          The format of the output file, inferred from the extension by default
          
          [possible values: pdf, png, svg, html]

      --root <DIR>
          Configures the project root (for absolute paths)
          
          [env: TYPST_ROOT=]

      --input <key=value>
          Add a string key-value pair visible through `sys.inputs`

      --font-path <DIR>
          Adds additional directories that are recursively searched for fonts.
          
          If multiple paths are specified, they are separated by the system's
          path separator (`:` on Unix-like systems and `;` on Windows).
          
          [env: TYPST_FONT_PATHS=]

      --ignore-system-fonts
          Ensures system fonts won't be searched, unless explicitly included via
          `--font-path`
          
          [env: TYPST_IGNORE_SYSTEM_FONTS=]

      --ignore-embedded-fonts
          Ensures fonts embedded into Typst won't be considered
          
          [env: TYPST_IGNORE_EMBEDDED_FONTS=]

      --package-path <DIR>
          Custom path to local packages, defaults to system-dependent location
          
          [env: TYPST_PACKAGE_PATH=]

      --package-cache-path <DIR>
          Custom path to package cache, defaults to system-dependent location
          
          [env: TYPST_PACKAGE_CACHE_PATH=]

      --creation-timestamp <UNIX_TIMESTAMP>
          The document's creation date formatted as a UNIX timestamp.
          
          For more information, see
          <https://reproducible-builds.org/specs/source-date-epoch/>.
          
          [env: SOURCE_DATE_EPOCH=]

      --pages <PAGES>
          Which pages to export. When unspecified, all pages are exported.
          
          Pages to export are separated by commas, and can be either simple page
          numbers (e.g. '2,5' to export only pages 2 and 5) or page ranges (e.g.
          '2,3-6,8-' to export page 2, pages 3 to 6 (inclusive), page 8 and any
          pages after it).
          
          Page numbers are one-indexed and correspond to physical page numbers
          in the document (therefore not being affected by the document's page
          counter).

      --pdf-standard <PDF_STANDARD>
          One (or multiple comma-separated) PDF standards that Typst will
          enforce conformance with

          Possible values:
          - 1.4:  PDF 1.4
          - 1.5:  PDF 1.5
          - 1.6:  PDF 1.6
          - 1.7:  PDF 1.7
          - 2.0:  PDF 2.0
          - a-1b: PDF/A-1b
          - a-1a: PDF/A-1a
          - a-2b: PDF/A-2b
          - a-2u: PDF/A-2u
          - a-2a: PDF/A-2a
          - a-3b: PDF/A-3b
          - a-3u: PDF/A-3u
          - a-3a: PDF/A-3a
          - a-4:  PDF/A-4
          - a-4f: PDF/A-4f
          - a-4e: PDF/A-4e
          - ua-1: PDF/UA-1

      --no-pdf-tags
          By default, even when not producing a `PDF/UA-1` document, a tagged
          PDF document is written to provide a baseline of accessibility. In
          some circumstances (for example when trying to reduce the size of a
          document) it can be desirable to disable tagged PDF

      --ppi <PPI>
          The PPI (pixels per inch) to use for PNG export
          
          [default: 144]

      --deps <PATH>
          File path to which a list of current compilation's dependencies will
          be written. Use `-` to write to stdout

      --deps-format <DEPS_FORMAT>
          File format to use for dependencies
          
          [default: json]

          Possible values:
          - json: Encodes as JSON, failing for non-Unicode paths
          - zero: Separates paths with NULL bytes and can express all paths
          - make: Emits in Make format, omitting inexpressible paths

  -j, --jobs <JOBS>
          Number of parallel jobs spawned during compilation. Defaults to number
          of CPUs. Setting it to 1 disables parallelism

      --features <FEATURES>
          Enables in-development features that may be changed or removed at any
          time
          
          [env: TYPST_FEATURES=]
          [possible values: html, a11y-extras]

      --diagnostic-format <DIAGNOSTIC_FORMAT>
          The format to emit diagnostics in
          
          [default: human]
          [possible values: human, short]

      --open [<VIEWER>]
          Opens the output file with the default viewer or a specific program
          after compilation. Ignored if output is stdout

      --timings [<OUTPUT_JSON>]
          Produces performance timings of the compilation process.
          (experimental)
          
          The resulting JSON file can be loaded into a tracing tool such as
          https://ui.perfetto.dev. It does not contain any sensitive information
          apart from file names and line numbers.

  -h, --help
          Print help (see a summary with '-h')
```

Whitespace and line wrapping for `help compile` must match the canonical 0.14.2 presentation represented above; in particular, the full output-template guidance and all options must be present. Watch help uses the same shared options, adds `--no-serve`, `--no-reload`, and `--port`, starts with `Watches an input file and recompiles on changes`, and has the watch usage line. Both `eval --help` and `eval -h` start with `Evaluates a piece of Typst code, optionally in the context of a document`; eval help documents JSON/YAML formats, `[possible values: json, yaml]`, `--pretty`, `--input`, `--root`, `--font-path`, `--package-path`, `--features`, `--target`, and the contextual `--in <IN>` option. It does not advertise or accept `--input-file`. `info --help` starts with `Displays debugging information about Typst`. Completions help lists `bash`, `elvish`, `fish`, `powershell`, and `zsh`.

## Spec 3

Command-line parsing follows a conventional clap-style grammar. Global flags occur before the subcommand; for example, `--color auto compile -h` works, while `compile --color auto -h` is an unexpected argument. Subcommand flags may appear before or after positionals. `--` ends flag parsing. `--format pdf`, `--format=pdf`, `-f pdf`, and `-f=pdf` are equivalent. Repeatable options such as `--input` and `--font-path` accumulate; a non-repeatable flag such as `--open` reports that it cannot be used multiple times.

Missing command positionals (`compile`/`watch` input, `init` template, or `completions` shell), missing option values, extra positionals, bad typed values, bad enums, unknown flags, and unknown subcommands produce a nonempty diagnostic on standard error containing `error:`, a `Usage:` line where appropriate, and `For more information, try '--help'.`. Unknown subcommands normally exit 2, unknown flags are nonzero, and document failures normally exit 1; evaluated-language errors use the special status behavior in Spec 16. A near miss such as `compiel` suggests the similar subcommand `compile`. Bad values include unknown formats, colors other than `auto|always|never`, diagnostic formats other than `human|short`, nonnumeric PPI/jobs/timestamps, malformed page ranges such as `1-0`, and an input definition without `=` or with an empty key. Color-value validation is deferred until after subcommand dispatch: `executable --color ALWAYS` rejects the value with a line containing `[possible values: auto, always, never]`, but `executable --color purple help` succeeds and prints main help, and an unknown subcommand is diagnosed as such before an invalid color is diagnosed. A `-` is consumed as a value when an option is awaiting a value. An input value may be empty and may itself contain further equals signs; split only at the first equals sign. Input keys may contain punctuation such as a hyphen. A jobs value of zero is accepted as the implementation's automatic/default behavior.

Diagnostics canonicalize the short jobs option to its long name: `compile -j` exits 2 and contains `a value is required for '--jobs <JOBS>' but none was supplied`. A malformed input definition such as `compile --input foobar - -` exits 2 and its invalid-value line contains `input must be a key and a value separated by an equal sign`. Nonnumeric `--ppi abc` exits 2 and its first line is exactly `error: invalid value 'abc' for '--ppi <PPI>': invalid float literal`.

Two missing-positional cases use option-free, error-specific usage lines. `compile` with no arguments exits 2 and writes exactly:

```text
error: the following required arguments were not provided:
  <INPUT>

Usage: executable compile <INPUT> [OUTPUT]

For more information, try '--help'.
```

When input is `-` and the output positional is absent, the command exits 2 and writes exactly:

```text
error: the following required arguments were not provided:
  <OUTPUT>

Usage: executable compile <INPUT> <OUTPUT>

For more information, try '--help'.
```

## Spec 4

With no arguments, the first invocation for a particular user data directory prints exactly this greeting to standard output and exits 0:

```text
Welcome to Typst, we are glad to have you here! ❤️

If you are new to Typst, start with the tutorial at https://typst.app/docs/tutorial/.
To get a quick start with your first project, choose a template on https://typst.app/universe/.

Here are the most important commands you will be using:

- Compile a file once: typst compile file.typ
- Compile a file on every change: typst watch file.typ
- Set up a project from a template: typst init @preview/<TEMPLATE>

Learn more about these commands by running typst help.

If you have a question, we and our community would be glad to help you out on
the Typst Forum at https://forum.typst.app/.

Happy Typsting!
```

The user data marker is `$HOME/.local/share/typst/greeted`; after greeting, write the current semantic version to it when its parent exists. A matching marker suppresses the greeting: bare invocation then emits main usage/help as a missing-command diagnostic and exits 2. A marker containing a different version causes a new greeting and is updated. If the `typst` marker directory does not exist, failure to write is silent and the greeting still succeeds.

`--color` and `TYPST_COLOR` control terminal styling. `never` emits no ANSI escape sequence; `always` emits ANSI styling in source/document diagnostics and the first-run greeting, but never inserts ANSI into a successful binary document written to stdout; `auto` behaves like `never` on captured/non-TTY streams. Clap-style command-line parser diagnostics remain unstyled even under `--color always`: for example, with `TYPST_COLOR=never`, `executable --color always not-a-command` exits 2 and its stderr contains no ANSI escape sequence. For source/document diagnostics, an explicit CLI color overrides `TYPST_COLOR`. Help and version suppress the greeting. Diagnostics retain the same text and structure with colors removed. Except for the page-selection and experimental-HTML warnings specified below, successful compilation has no incidental stdout/stderr output; failures go to stderr only.

## Spec 5

`compile INPUT [OUTPUT]` reads UTF-8 Typst source, evaluates it to a paged document, and exports it. `INPUT=-` reads standard input and requires an explicit `OUTPUT` positional. `OUTPUT=-` writes artifact bytes to standard output and defaults to PDF if `--format` is absent, so `compile -- - -` is a valid stdin-to-stdout PDF invocation. If output is omitted for a named input, replace `.typ` with `.pdf` in the same directory. Explicit relative output paths are relative to the process working directory. Existing output files are atomically overwritten on success and preserved if compilation fails. Parent output directories are not implicitly created, including the parent of a requested timings file. Failure to write a PDF beneath a nonexistent parent exits 1 with empty stdout and stderr exactly `error: failed to write PDF file (No such file or directory (os error 2))\n\n`. A missing named input exits 1 with empty stdout and reports the supplied path in parentheses; for example, `compile nonexistent.typ` produces exactly `error: input file not found (searched at nonexistent.typ)\n`.

Input supports UTF-8 BOM, Unicode text and filenames, symlinks, large documents, long paths, blank and whitespace-only source, and newline variations. Invalid UTF-8/binary `.typ` input is rejected with status 1, empty stdout, and stderr exactly `error: file is not valid UTF-8\n\n`. Empty/whitespace source compiles to a valid empty one-page document. Ordinary input, math, styles, imports, images, tables, links, code blocks, and Unicode compile without warnings to a nontrivial output. A document title configured with `#set document(title: "Title")` is embedded as PDF metadata in a form discoverable in the PDF bytes. Output PDFs have extractable text/ToUnicode mappings.

## Spec 6

The output format is inferred case-insensitively from `.pdf`, `.png`, or `.svg`, or selected by `--format/-f`. Explicit format wins even when it conflicts with the output extension. HTML is accepted only when the `html` feature is enabled. An output path with no known extension and no `--format` exits 1 with empty stdout, names that path in the first error line, and then suggests `--format/-f`. For `output_no_extension`, stderr is exactly:

```text
error: could not infer output format for path output_no_extension.
consider providing the format manually with `--format/-f`
```

For `out.xyz`, stderr is exactly:

```text
error: could not infer output format for path out.xyz.
consider providing the format manually with `--format/-f`
```

The compile alias `c` is identical to `compile`.

For PDF, output begins with a valid PDF header, is parseable as a complete PDF, contains one PDF page per laid-out document page, contains page content streams, embeds needed fonts, and is normally tagged for accessibility. `--no-pdf-tags` emits a valid alternative without default tags. The default/current PDF header is `%PDF-1.7`; standards `1.4`, `1.5`, `1.6`, `1.7`, and `2.0` select the corresponding exact first line. PDF/A requests such as `a-1b`, `a-2b`, and `a-3a` succeed and add the appropriate conformance metadata/tags. PDF/UA-1 additionally requires a document title: a titled document succeeds, while compiling the source `Accessible document` with `--pdf-standard ua-1` exits 1, leaves stdout empty, and writes exactly ``error: PDF/UA-1 error: missing document title\n = hint: set the title with `set document(title: [...])`\n\n`` to stderr. For combined `1.7,a-2b`, the header remains 1.7 and XMP includes `<pdfaid:part>2</pdfaid:part>`, `<pdfaid:conformance>B</pdfaid:conformance>`, and the exact element `<pdf:PDFVersion>1.7</pdf:PDFVersion>`. Multiple compatible comma-separated standards are supported.

## Spec 7

PNG and SVG emit one image per selected page. For a multipage result, the output name must include a page placeholder or compilation fails without writing output, using exactly:

```text
error: cannot export multiple images without a page number template ({p}, {0p}) in the output path
```

The exact stderr byte string above ends with a blank line: `error: cannot export multiple images without a page number template ({p}, {0p}) in the output path\n\n`.

`{p}` is the one-based physical page number without padding; `{0p}` and its alias `{n}` are zero-padded to the decimal width of the document's total page count; `{t}` is that total page count. All placeholders can coexist, literal non-placeholder brackets/braces are retained, and no extra page is produced. A one-page export may use either a literal filename or a template. A single PNG/SVG page may be written to stdout; a multipage image export cannot share one stdout stream.

PNG begins with the standard eight-byte PNG signature and represents the requested page at `--ppi` pixels per inch; the default is 144. Values such as 72, 96, 144, 200, 300, and 600 alter pixel dimensions/file size proportionally, with higher PPI materially increasing output size. SVG is UTF-8 XML beginning with `<svg`, with the `http://www.w3.org/2000/svg` namespace, closing `</svg>`, numeric `width`, `height`, and `viewBox` matching the page dimensions, and text/shape content. On a default A4 page its root contains `viewBox="0 0 595.275590551 841.88976378"`, `width="595.275590551pt"`, and `height="841.88976378pt"`. Rendered text glyphs are emitted through elements containing `<use xlink:href=`. Both exporters handle text, math, vector shapes, gradients, and multipage documents.

SVG export is a real vector rendering rather than a minimal wrapper around a text node. In particular, compiling the one-page source `Hello World` as SVG succeeds with empty stderr and produces more than 500 bytes, including the positioned glyph `<use>` elements and their path definitions.

## Spec 8

`--pages` accepts comma-separated one-based physical page numbers, closed ranges, and open-ended ranges such as `1`, `2,5`, `2-4`, `3-`, and combinations. It emits selected pages in document order while excluding unselected pages and ignores logical page-counter renumbering. It works for PDF, PNG, and SVG. A selection yielding one image does not require a filename placeholder. `--pages 3-` selects page 3 through the last; selecting the last page works; malformed selections report an error. A wholly out-of-range selection is not an error: compiling a one-page document to PDF with `--pages 99` exits 0 and writes a PDF. When the selection contains in-range pages, the selected PDF contains only those pages, and image filenames retain their physical numbers (for example selection `2,5-7,9` creates `{p}` files numbered 2, 5, 6, 7, and 9).

Selecting pages for PDF implicitly disables PDF tags. Unless `--no-pdf-tags` is also supplied to silence it, a successful page-selected PDF compilation writes exactly this warning to stderr, including the final blank line:

```text
warning: using --pages implies --no-pdf-tags
 = hint: the resulting PDF will be inaccessible
 = hint: add --no-pdf-tags to silence this warning

```

## Spec 9

Compilation tracks every filesystem input actually used: the main source, recursive `#import`/`#include` modules, images, and data files, plus every output path. `--deps PATH` writes this dependency report after a successful compile; `PATH=-` writes it to stdout without unrelated output.

The default/`json` report is one compact JSON object with no trailing newline and keys `inputs` and `outputs`, each an array of path strings. Paths are stable and relative when invoked with relative project paths. Input-array order is not lexicographic or main-file-first. In particular, if `main.typ` includes `parts/one.typ`, that file includes `two.typ`, and `parts/two.typ` reads `data.txt`, compiling to `out.pdf` produces exactly `{"inputs":["parts/two.typ","main.typ","parts/data.txt","parts/one.typ"],"outputs":["out.pdf"]}`. A minimal `minimal.typ -> output.pdf` report has `inputs: ["minimal.typ"]` and `outputs: ["output.pdf"]`. `zero` writes input paths separated and terminated by NUL bytes, allowing non-Unicode-native paths. `make` writes a single Make rule `output: dependency ...\n`, escapes spaces, colons, dollar signs, and hashes appropriately, and includes every nested dependency. It requires a named document output: asking for both document and make dependencies on stdout fails with `error: cannot write both output and dependencies to stdout\n`.

`--timings [PATH]` writes nonempty Chrome trace-event JSON: an array of objects containing `name`, `ph`, `ts`, `pid`, and `tid`, with begin (`B`) and end (`E`) events. Omitted PATH uses `record-0.json`. In a `{n}` template, `{n}` is replaced with `0`; an existing resulting file is overwritten rather than causing selection of the next number. The parent directories of an explicit timings path are not created: if `new` does not exist, `--timings new/trace.json` exits 1 with empty stdout and writes exactly `error: failed to create file: No such file or directory (os error 2)\n` to stderr. The document output may already have been written before this timings-file failure. Timings and dependency reporting can be combined. `--jobs/-j` accepts ordinary positive counts and zero and does not change document semantics.

## Spec 10

The project root defaults to a suitable ancestor of the input and can be set by `--root DIR` or `TYPST_ROOT`; the flag wins. A Typst path beginning `/` is project-root-relative, not host-filesystem-root-relative. Relative imports are resolved from the importing file, including nested `../` paths. Imports and includes may form multi-level chains; circular imports are diagnosed. Missing sources mention `file not found` and show the source line. A source outside the configured root, invalid imports, and missing imports produce clear source diagnostics. A nonexistent root is reported with its searched path; for `--root /nonexistent/path`, the command exits 1 with empty stdout and exactly `error: root directory not found (searched at /nonexistent/path)\n` on stderr.

`#include "path.typ"` evaluates and inserts a module's content. `#import "path.typ": f`, wildcard imports, and imported functions/values work. Absolute project imports, input files invoked from a different current directory, and Unicode paths work. A panic in an imported function propagates as `error: panicked with: <value>`.

Local packages use specifications `@namespace/name:version`. `--package-path`/`TYPST_PACKAGE_PATH` points to a hierarchy `namespace/name/version/` containing `typst.toml`; its `[package] entrypoint` identifies the module. Relative string paths created inside package code resolve from the package, while an explicit `path("a.typ")` value passed in from project code retains its project origin. Missing packages report `error: package not found` and include the complete package specification. Package cache path is separately controlled by `--package-cache-path`/`TYPST_PACKAGE_CACHE_PATH`; CLI wins over environment. When an HTTP image or other resource would require network access, compilation fails promptly and includes the exact hint `hint: network access is not supported`.

## Spec 11

These environment variables are first-class equivalents of options: `TYPST_COLOR`, `TYPST_CERT`, `TYPST_ROOT`, `TYPST_FONT_PATHS`, `TYPST_IGNORE_SYSTEM_FONTS`, `TYPST_IGNORE_EMBEDDED_FONTS`, `TYPST_PACKAGE_PATH`, `TYPST_PACKAGE_CACHE_PATH`, `TYPST_FEATURES`, and `SOURCE_DATE_EPOCH`. Boolean variables accept the normal enabled value `1`. `TYPST_FONT_PATHS` is split on the host path separator and combines with explicit repeated font paths. A nonexistent font path is harmless. An empty explicit `--font-path ''` or empty `TYPST_FONT_PATHS` value is instead a parser error. In particular, invoking `fonts` with `TYPST_FONT_PATHS` set to the empty string exits 2, writes nothing to stdout, and writes exactly the following to stderr; there is no `Usage:` block:

```text
error: a value is required for '--font-path <DIR>' but none was supplied

For more information, try '--help'.
```

Explicit CLI values override singular environment values. Repeated `--input` entries form `sys.inputs`; a repeated key uses the last value.

`SOURCE_DATE_EPOCH`/`--creation-timestamp` supplies a Unix timestamp for reproducible PDF metadata; the option wins. Invalid timestamps are errors mentioning timestamp/creation-timestamp. Builds with the same content/configuration are deterministic.

## Spec 12

`watch INPUT [OUTPUT]` accepts the compilation options and performs an initial compile, then remains alive monitoring the main source and all transitive imports/includes. It cannot write a document to stdout and rejects that case exactly with `error: cannot write document to stdout in watch mode\n`. Missing input or compilation errors are printed but do not terminate the watcher. Creation, modification, rapid successive changes, deletion/recreation of the main file, and changes to direct or deep dependencies trigger recompilation. After a transient error is fixed, valid output is produced. A failed rebuild preserves the previous good output.

Watch honors PDF/SVG/PNG/HTML format selection, page templates and page filters, root, input values, fonts, package paths, PDF standard, PPI, timestamp, diagnostic format, and jobs. It supports empty, Unicode-named, nested, large, and relative-path documents. Multipage PNG/SVG template behavior is the same as compile. File-change handling may debounce duplicate notifications but must make the new output observable promptly. `--no-serve`, `--no-reload`, and `--port` are accepted watch-specific controls.

## Spec 13

`fonts` discovers font families recursively from embedded fonts, system fonts, and each explicit/environment font directory. Its default bundled/system family listing is exactly the following, alphabetically ordered:

```text
DejaVu Sans
DejaVu Sans Mono
DejaVu Serif
Libertinus Serif
New Computer Modern
New Computer Modern Math
```

The embedded-only listing selected by `fonts --ignore-system-fonts` is exactly:

```text
DejaVu Sans Mono
Libertinus Serif
New Computer Modern
New Computer Modern Math
```

Conversely, with `TYPST_IGNORE_EMBEDDED_FONTS=true`, the listing is exactly:

```text
DejaVu Sans
DejaVu Sans Mono
DejaVu Serif
```

`--ignore-system-fonts` and `--ignore-embedded-fonts` independently remove those sources; disabling both with no custom path yields an empty listing. Explicit font paths remain active even when system fonts are ignored. Output has one unique family per line in deterministic order. Custom TTF directories are recursively scanned.

`fonts --variants` prints each family's faces beneath it. Each face line begins `- ` and uses this exact field spelling, capitalization, punctuation, and order:

```text
- Style: Normal, Weight: 400, Stretch: FontStretch(1000), Path: <embedded>
```

Other faces substitute their actual `Style`, numeric `Weight`, `FontStretch` value, and filesystem path. Thus the output contains the literal substrings `Style: Normal`, `Weight: 400`, and `Stretch: FontStretch(1000)`, and embedded faces end in `Path: <embedded>`. `fonts --help` succeeds with empty stderr and begins exactly:

```text
Lists all discovered fonts in system and custom font paths

Usage: executable fonts [OPTIONS]
```

It documents path, ignore, and variants options.

## Spec 14

`info` succeeds and writes its human-readable report to standard error. Its first line begins `Version 0.14.2 (`. It reports build settings (`self-update`, `http-server`), platform OS/architecture, enabled features, font configuration, package path/cache path, and all recognized environment variable names and their effective/set values. The font block uses the literal labels `Custom font paths`, `System fonts`, and `Embedded fonts`; the latter two render their state as `on` or `off`. With `TYPST_IGNORE_SYSTEM_FONTS=1`, the complete system-font line is exactly `  System fonts   off` (two leading spaces and three spaces between the label and state, with no colon). With multiple custom paths supplied through `TYPST_FONT_PATHS`, `Custom font paths` is followed by one indented `- PATH` line per path. In particular, custom roots/font paths and an off system-font setting are visible.

The `info` subcommand's own configuration options are only `-f`/`--format <FORMAT>` and `--pretty`; font settings that the report displays must be supplied through the environment. It does not accept `--font-path` or `--ignore-system-fonts`. Either unsupported option causes status 2; their respective first diagnostic lines are exactly `error: unexpected argument '--font-path' found` and `error: unexpected argument '--ignore-system-fonts' found`. For `info --font-path PATH`, the diagnostic includes `Usage: executable info [OPTIONS]`; when `--format json` precedes that unsupported option, it instead includes `Usage: executable info <--format <FORMAT>|--pretty>`.

`info --format json` instead emits valid JSON with top-level `version` equal to `0.14.2` and keys `build`, `features`, `fonts`, `packages`, and `env`. `build` has `commit` equal to the full string `ccc34be79ab2555cd26c519b1eab45a3e9ec757a`, `platform: {os, arch}`, and `settings` containing `self-update` and `http-server`; on Linux, OS is `linux` and architecture is `x86_64` or `aarch64`. `fonts` has `paths`, `system`, and `embedded`; `packages` has `package-path` and `package-cache-path`. The `env` object contains all of these keys in this order, with supplied values preserved as strings and unset values represented as JSON `null`:

```text
TYPST_CERT
TYPST_FEATURES
TYPST_FONT_PATHS
TYPST_IGNORE_SYSTEM_FONTS
TYPST_IGNORE_EMBEDDED_FONTS
TYPST_PACKAGE_CACHE_PATH
TYPST_PACKAGE_PATH
TYPST_ROOT
TYPST_UPDATE_BACKUP_PATH
SOURCE_DATE_EPOCH
XDG_CACHE_HOME
XDG_DATA_HOME
FONTCONFIG_FILE
OPENSSL_CONF
NO_COLOR
NO_PROXY
HTTP_PROXY
HTTPS_PROXY
ALL_PROXY
```

`--pretty` uses two-space indented JSON. `--format yaml` emits the same nested structure as YAML.

## Spec 15

`completions SHELL` writes a usable completion program to stdout for exactly `bash`, `zsh`, `fish`, `powershell`, and `elvish`; another shell is an argument error. Scripts contain all public commands and global flags. Canonical syntax includes `_typst()`/`COMPREPLY=()` and command functions for bash; `#compdef typst`, `autoload -U is-at-least`, and `_arguments` for zsh; `__fish_typst_global_optspecs`, `__fish_typst_needs_command`, and `complete -c typst` for fish; `Register-ArgumentCompleter -Native -CommandName 'typst'` and `CompletionResult` for PowerShell; and `use builtin;`, `fn cand`, and `edit:completion:arg-completer[typst]` for Elvish. Output may be redirected by the caller and ends normally without diagnostics.

Completion generation is canonical, not merely semantically equivalent. Each command exits 0 with empty stderr. Taking the first 30 physical output lines and trimming surrounding whitespace yields the following exact text for Bash:

```bash
_typst() {
    local i cur prev opts cmd
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    cmd=""
    opts=""

    for i in ${COMP_WORDS[@]}
    do
        case "${cmd},${i}" in
            ",$1")
                cmd="typst"
                ;;
            typst,c)
                cmd="typst__compile"
                ;;
            typst,compile)
                cmd="typst__compile"
                ;;
            typst,completions)
                cmd="typst__completions"
                ;;
            typst,eval)
                cmd="typst__eval"
                ;;
            typst,fonts)
                cmd="typst__fonts"
                ;;
            typst,help)
```

For Zsh it yields:

```zsh
#compdef typst

autoload -U is-at-least

_typst() {
    typeset -A opt_args
    typeset -a _arguments_options
    local ret=1

    if is-at-least 5.2; then
        _arguments_options=(-s -S -C)
    else
        _arguments_options=(-s -C)
    fi

    local context curcontext="$curcontext" state line
    _arguments "${_arguments_options[@]}" : \
'--color=[Whether to use color. When set to \`auto\` if the terminal to supports it]:COLOR:(auto always never)' \
'--cert=[Path to a custom CA certificate to use when making network requests]:CERT:_files' \
'-h[Print help]' \
'--help[Print help]' \
'-V[Print version]' \
'--version[Print version]' \
":: :_typst_commands" \
"*::: :->typst" \
&& ret=0
    case $state in
    (typst)
        words=($line[1] "${words[@]}")
        (( CURRENT += 1 ))
```

For Fish it yields (the indentation characters are tabs):

```fish
# Print an optspec for argparse to handle cmd's options that are independent of any subcommand.
function __fish_typst_global_optspecs
	string join \n color= cert= h/help V/version
end

function __fish_typst_needs_command
	# Figure out if the current invocation already has a command.
	set -l cmd (commandline -opc)
	set -e cmd[1]
	argparse -s (__fish_typst_global_optspecs) -- $cmd 2>/dev/null
	or return
	if set -q argv[1]
		# Also print the command, so this can be used to figure out what it is.
		echo $argv[1]
		return 1
	end
	return 0
end

function __fish_typst_using_subcommand
	set -l cmd (__fish_typst_needs_command)
	test -z "$cmd"
	and return 1
	contains -- $cmd[1] $argv
end

complete -c typst -n "__fish_typst_needs_command" -l color -d 'Whether to use color. When set to `auto` if the terminal to supports it' -r -f -a "auto\t''
always\t''
never\t''"
complete -c typst -n "__fish_typst_needs_command" -l cert -d 'Path to a custom CA certificate to use when making network requests' -r -F
```

For PowerShell it yields:

```powershell
using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'typst' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'typst'
        for ($i = 1; $i -lt $commandElements.Count; $i++) {
            $element = $commandElements[$i]
            if ($element -isnot [StringConstantExpressionAst] -or
                $element.StringConstantType -ne [StringConstantType]::BareWord -or
                $element.Value.StartsWith('-') -or
                $element.Value -eq $wordToComplete) {
                break
        }
        $element.Value
    }) -join ';'

    $completions = @(switch ($command) {
        'typst' {
            [CompletionResult]::new('--color', '--color', [CompletionResultType]::ParameterName, 'Whether to use color. When set to `auto` if the terminal to supports it')
            [CompletionResult]::new('--cert', '--cert', [CompletionResultType]::ParameterName, 'Path to a custom CA certificate to use when making network requests')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('-V', '-V ', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('--version', '--version', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('compile', 'compile', [CompletionResultType]::ParameterValue, 'Compiles an input file into a supported output format')
```

For Elvish it yields:

```elvish
use builtin;
use str;

set edit:completion:arg-completer[typst] = {|@words|
    fn spaces {|n|
        builtin:repeat $n ' ' | str:join ''
    }
    fn cand {|text desc|
        edit:complex-candidate $text &display=$text' '(spaces (- 14 (wcswidth $text)))$desc
    }
    var command = 'typst'
    for word $words[1..-1] {
        if (str:has-prefix $word '-') {
            break
        }
        set command = $command';'$word
    }
    var completions = [
        &'typst'= {
            cand --color 'Whether to use color. When set to `auto` if the terminal to supports it'
            cand --cert 'Path to a custom CA certificate to use when making network requests'
            cand -h 'Print help'
            cand --help 'Print help'
            cand -V 'Print version'
            cand --version 'Print version'
            cand compile 'Compiles an input file into a supported output format'
            cand c 'Compiles an input file into a supported output format'
            cand watch 'Watches an input file and recompiles on changes'
            cand w 'Watches an input file and recompiles on changes'
```

`init TEMPLATE [DIR]` accepts package specifications beginning `@`. A specification without that prefix exits 1 with empty stdout and exactly `error: package specification must start with '@'\n`. An unversioned non-preview specification such as `@local/template` exits 1 with empty stdout and exactly `error: please specify the desired version\n`. Other malformed names are rejected, and unknown templates say they were not found. Given a locally cached template package with template metadata, it copies the template tree into a new directory (defaulting to the template name or using `DIR`), preserves files such as `main.typ` and `README.md`, and refuses an existing target. Generated source imports the exact package version and invokes its template function (for example `project.with`); README content is preserved. Success is reported on stderr with `🎉`, `Successfully created new project`, the package specification, and next steps containing `cd` and `typst watch main.typ`; suggest the template's project entrypoint (`main.typ`), not its package library entrypoint (`lib.typ`).

## Spec 16

`eval EXPRESSION` parses and evaluates Typst code without requiring a document. It accepts multiline expressions, semicolon-separated `let` bindings, closures, method calls, blocks, conditionals, and the standard library's non-filesystem functionality. Filesystem loader names are present but cannot access files from an eval expression: for example, `eval 'read("text.txt")' --root DIR` and the same invocation with `--in context.typ` both exit 0, leave stdout empty, and write exactly `error: cannot access file system from here\n\n` to stderr. It writes exactly one serialized value plus a newline on success and nothing to stderr. Default format is compact JSON: `1+2` is `3\n`, strings are JSON-quoted UTF-8, booleans are `true`/`false`, `none` and non-finite floats serialize as `null`, arrays have no spaces (for example `[1,2,3]`), and dictionaries are JSON objects preserving insertion order. `--pretty` uses two-space indentation and a final newline. `--format yaml` emits YAML followed by its terminating newline (a scalar `3` is `3\n\n`). Values not naturally JSON representable serialize using their canonical `repr` string, itself JSON-quoted (for example `10pt` becomes `"10pt"`).

`--input key=value` populates the dictionary `sys.inputs`; `sys.inputs`, `.at`, multiple inputs, last-value override, empty values, Unicode, punctuation, and equals signs in values work. `sys.version` identifies 0.14.2. `--target paged|html` chooses the library target. `eval EXPRESSION --target html` does not implicitly enable HTML: without `--features html` it writes no result, exits 1, and emits the exact Spec 33 HTML-feature diagnostic. `--in FILE` evaluates in a compiled document context so `query`, contextual state, and locations work; `-` can supply context via stdin. `--input-file` is not an alias and is rejected as an unexpected argument. Once argument and feature validation has succeeded, an invalid source/expression emits an `error:` diagnostic to stderr and no result to stdout, but exits 0. This includes unknown variables, syntax and type errors, division by zero, and invalid `datetime` construction or arithmetic; parser/configuration errors retain their separately specified nonzero statuses.

## Spec 17

The language has three modes. Markup is the document default. `#` introduces one code expression; `#{ ... }` is a code block. `$...$` is inline math and `$ ... $` with surrounding spacing is block math. Code includes comments (`//` and nested/closed `/* */`), strings with escapes and Unicode escapes, integers, floats, decimals, booleans, `none`, arrays/tuples `(1, 2, 3)`, dictionaries `(a: 1, b: 2)`, content blocks `[markup]`, function calls with positional/named/spread arguments, member access/methods, `let`, assignment, functions/closures (`x => ...` and `(x,y) => ...`), `if/else`, `for`, `while`, `break`, `continue`, `return`, and module import/include.

Markup recognizes paragraphs, headings (`=`, `==`, ...), bullet items (`-`), numbered items (`+`), term items (`/ term: description`), emphasis `_..._`, strong `*...*`, raw inline/backtick and fenced raw blocks, labels `<name>`, references/citations `@name`, URLs, escapes, and explicit line/page breaks. Set rules configure later elements (`#set page(...)`, `#set text(...)`); show rules transform matching content. Variables, recursive functions, loops/ranges, mapping, conditionals, spread arguments, tables, figures, images, alignment, spacing, and columns can produce content.

Parsing is Unicode-aware and rejects lone/doubled `#`, unfinished expressions, unclosed strings/math/comments/braces/brackets/parentheses/Unicode escapes, extra closers, invalid Unicode code points, malformed import/function/let syntax, and the characters/operators `&`, `|`, `!`, `~`, `~=`, `&&`, `||` in code where Typst requires word operators. Diagnostics for C-like boolean spellings hint at `and`, `or`, or `not`. Runtime checks diagnose undefined variables, wrong argument/value types, division by zero, out-of-bounds indexing, invalid recursion/nontermination, and explicit `panic`. In eval, `1 +` reports `error: expected expression`, and adding a string and integer reports `error: cannot add string and integer`.

## Spec 18

Operators are type-directed. Unary `+` is identity for int, float, decimal, length, angle, ratio, fraction, and relative length; unary `-` negates them and duration. Applying them to strings/arrays is a type error. Arithmetic promotes int/float mixes to float and int/decimal mixes to decimal. Integer addition/subtraction/multiplication retain integers and detect signed 64-bit overflow. `/` of integers yields float. Addition concatenates strings and arrays, merges dictionaries with the right side overriding duplicate keys, adds like units, and combines length with ratio into relative length. Adding an array and a string is an error whose diagnostic line is exactly `error: cannot add array and string`. Multiplication repeats strings/arrays by a nonnegative integer and scales lengths/angles/durations. Negative string or array repetition instead emits exactly `error: number must be at least zero`. Multiplying ratios produces a ratio (`50% * 20%` serializes as `"10%"\n`), while dividing ratios produces a float (`200% / 50%` serializes as `4.0\n`). Division of like lengths or angles also yields a float, not a ratio: `20pt / 5pt` and `90deg / 30deg` serialize as `4.0\n` and `3.0\n`, respectively. Division of durations yields a float ratio.

The canonical eval diagnostic lines for unary type errors are `error: cannot apply unary '+' to string`, `error: cannot apply unary '+' to array`, and `error: cannot apply '-' to string`. Signed 64-bit overflow in addition, subtraction, or multiplication reports `error: value is too large`; for example, `9223372036854775807 * 2` produces that line. An ordered comparison between a length and a string reports `error: cannot compare length and string`. In each of these eval cases, stdout is empty and stderr ends with a second newline after the diagnostic, under the status rule in Spec 16.

Division by numeric zero in eval emits `error: cannot divide by zero`.

`==`/`!=` support all values and numeric cross-type equality; ordered comparisons cover numbers, strings, units, duration/datetime, and lexicographic arrays, while incompatible physical dimensions error. Equality normalizes a pure length or ratio against the corresponding relative length whose other component is zero: `10pt == 10pt + 0%` and `50% == 0pt + 50%` each serialize as `true\n`. `in`/`not in` perform element membership for arrays, substring membership for strings (the empty substring is contained), and key membership for dictionaries. Logical `and`, `or`, and `not` operate on booleans with ordinary semantics. Ratios and relative lengths preserve their components and units in canonical serialization. A relative length with both components serializes with the percentage component first, then ` + ` and the absolute component, irrespective of operand order: `10pt + 50%` produces exactly `"50% + 10pt"\n`, and `(20% + 5pt) + (30% + 3pt)` produces exactly `"50% + 8pt"\n`.

## Spec 19

Integers are signed 64-bit values with parsing from bases 2 through 36, conversion from bool/float/decimal by truncation toward zero, `signum`, two's-complement `bit-not`, `bit-and`, `bit-or`, `bit-xor`, left/right shifts, and little- or big-endian signed byte conversion. Default `to-bytes()` produces `bytes(8)` and `from-bytes` reverses it. Floats support parsing (including exponent notation), bool/int conversion, `float.inf`, `float.nan`, `is-infinite`, `is-nan`, signum, IEEE 32/64-bit byte conversion selected by `size: 4|8`, and endianness. JSON maps infinity/NaN to null.

`decimal` is exact base-10 arithmetic, constructible from int or decimal string, preserving significant trailing fractional zeroes in representation. Its canonical repr is `decimal("...")`. It supports comparison, negation (including negative zero), arithmetic with decimal/int, exact `0.1+0.2`, and bounded values through magnitude `79228162514264337593543950335`; malformed/out-of-range input reports `error: invalid decimal: VALUE`.

`duration` accepts weeks/days/hours/minutes/seconds, normalizes for canonical `duration(...)` representation, provides `.weeks()/.days()/.hours()/.minutes()/.seconds()` total conversions as floats, supports addition, subtraction, negation, scalar multiply/divide, duration division, equality/order, and zero. When all five components are nonzero, `eval 'duration(weeks: 1, days: 2, hours: 3, minutes: 4, seconds: 5)'` succeeds and its exact stdout is the following JSON string plus its final output newline:

```text
"duration(\n  weeks: 1,\n  days: 2,\n  hours: 3,\n  minutes: 4,\n  seconds: 5,\n)"
```

The represented duration is multiline, each component has a trailing comma, and the closing parenthesis occupies its own line. Unit literals include `pt`, percentages, `deg`/`rad`, and fractional `fr`; relative lengths may combine absolute and percentage parts. Calling `int` with an explicit base outside 2 through 36 produces the exact diagnostic line `error: base must be between 2 and 36`; in eval it has empty stdout, a trailing blank line on stderr, and status 0 under Spec 16.

When only the hours and minutes components are nonzero, duration representation is instead compact, occupies one line, orders hours before minutes, and omits all zero components. The exact eval results include:

```text
duration(hours: 1) + duration(minutes: 30)  -> "duration(hours: 1, minutes: 30)"
duration(hours: 2) - duration(minutes: 30)  -> "duration(hours: 1, minutes: 30)"
duration(hours: 1, minutes: 15) * 2         -> "duration(hours: 2, minutes: 30)"
duration(hours: 3) / 2                      -> "duration(hours: 1, minutes: 30)"
-duration(hours: 2, minutes: 30)            -> "duration(hours: -2, minutes: -30)"
duration(hours: 2, minutes: 30)             -> "duration(hours: 2, minutes: 30)"
duration()                                  -> "duration()"
```

Each right-hand side shown is the JSON string written to stdout, followed by the normal final output newline. In particular, zero is not represented as `duration(seconds: 0)`.

## Spec 20

The calculation library supports `abs` for scalar/unit types; `sin`, `cos`, `tan`, inverse trig including two-argument `atan`, hyperbolic and inverse hyperbolic functions; `pow`, `exp`, `sqrt`, arbitrary `root`, `log` with optional base, and natural log; `floor`, `ceil`, `round` (including positive/negative digits), `trunc`, `fract`; `min`, `max`, `clamp`, vector `norm`; factorial, permutations, binomial coefficients, GCD, LCM, remainder/modulo, and even/odd predicates. It exposes standard constants such as π and e. `norm` accepts the named `p` parameter; `calc.norm(p: 1, 3, 4)` is the Manhattan norm and serializes exactly as `7.0\n`. `calc.rem` uses truncated-division remainder, whose sign follows the dividend, so `calc.rem(-10, 3)` serializes as `-1\n`.

Functions accept the numeric and angle forms natural to Typst and return canonical int/float/unit results. Inverse trigonometric functions return angles serialized in degrees: `calc.asin(0)` and `calc.atan(0)` each produce `"0deg"\n`, while `calc.acos(0)` produces `"90deg"\n`. Decimal-looking mathematical results use Typst's canonical float formatting rather than exposing binary floating-point noise; in particular, `calc.log(1000)` produces exactly `3.0\n`.

Domain errors are diagnosed for `0^0`, negative square roots, inverse trig outside [-1,1], log/ln of nonpositive values, zero root index, negative radicand with even index, `acosh(x<1)`, and `atanh` at/outside its boundary. Their canonical lines include:

```text
error: cannot take square root of negative number
error: value must be strictly positive
error: cannot take the 0th root of a number
error: negative numbers do not have a real nth root when n is even
```

Additional exact domain-error lines are:

```text
error: value must be greater than or equal to 1
error: value must be between -1 and 1 (exclusive)
error: the result is not a real number
```

These are produced respectively by `calc.acosh(0.5)`, `calc.atanh(1)`, and `calc.pow(-1, 0.5)`. The strictly-positive line applies to both `calc.log(0)` and `calc.ln(0)`. The zero-index line is produced by `calc.root(16, 0)`, and the even-root line by `calc.root(-16, 2)`. Each is an eval-language error: stdout is empty, stderr has a blank line after the shown line, and status is 0 under Spec 16. Other edge cases include GCD with zero, LCM with one, binomial/permutation limits, negative rounding, and negative floor versus truncation.

## Spec 21

Arrays support construction, indexing including negative indices, `.at(default:)`, first/last, length, push/pop, insert/remove, slice, contains, map, filter, fold, sum, product, any/all, find, position, reverse, stable sort, flatten, deduplicate, join, zip, concatenation, and repetition. Calling `().sum()` without a default is an error, not the additive identity; its diagnostic line is exactly `error: cannot calculate sum of empty array with no default`. Invalid indices error unless a default is supplied. `(1, 2, 3).at(10)` reports exactly `error: array index out of bounds (index: 10, len: 3) and no default value was specified`.

Dictionaries support literal construction, `.at(default:)`, length, keys, values, pairs, insertion/removal, merging, membership, nested structures, and pairs-to-dictionary round trips. `(a: 1, b: 2).at("c")` without a default reports exactly `error: dictionary does not contain key "c" and no default value was specified`. All three errors in this paragraph use the Spec 16 eval convention: status 0, empty stdout, and a blank line after the diagnostic on stderr. `range` supports end-only and bounded ranges. `type`, `str`, `int`, `float`, and `repr` conversions work; conditionals and lexical `let` bindings compose with methods. Type values serialize using Typst's short canonical names; in particular, `type(42)` writes exactly `"int"\n`, not `"integer"\n`.

String lengths and indices use UTF-8 byte offsets: `"🚀".len()` is `4`, and `"café".len()` is `5`. `.at` and `.slice` accept byte indices only at Unicode scalar-value boundaries; negative indexing is supported, and an out-of-range operation either uses `default:` or errors. `"hello".at(10)` emits exactly `error: no default value was specified and string index out of bounds (index: 10, len: 5)`. `.first`, `.last`, and `.rev` preserve extended grapheme clusters; `.clusters()` explicitly returns those clusters (keeping combining sequences and ZWJ emoji together), while `.codepoints()` splits Unicode scalar values. Empty-string `.first()`/`.last()` emit `error: string is empty`, while their `default:` argument is returned; for example, `"".first(default: "x")` and `"".last(default: "x")` each serialize as `"x"\n`. `to-unicode` and `str.from-unicode` convert valid scalar values; `str.from-unicode(0x110000)` emits exactly `error: 0x110000 is not a valid codepoint`.

For slicing, `count` is a byte count (`"hello".slice(1, count: 3)` is `"ell"`). Supplying both `count` and `end` is rejected with the exact line ``error: `end` and `count` are mutually exclusive``; for example, `"hello".slice(1, 4, count: 2)` produces that line. A boundary in the middle of a Unicode scalar value is rejected with its byte index: `"café".slice(0, 4)` produces exactly `error: string index 4 is not a character boundary`. Both use the Spec 16 eval convention, including the final blank line on stderr. An end before the start and a negative count instead clamp to an empty slice: `"hello".slice(4, 2)` and `"hello".slice(4, count: -2)` each serialize as `""\n` with status 0.

## Spec 22

Strings support exact/case-sensitive `contains`, `starts-with`, `ends-with`, `find`, `position`, `match`, `matches`, `replace`, `trim`, and `split`, with either string or regex patterns where applicable. Regex matching returns match objects and named/numbered captures; replacement may be a callback receiving captures and may be count-limited. `trim` accepts the direction values `at: start` and `at: end`: `"xxhelloxx".trim("x", at: start)` is `"helloxx"`, while the end form is `"xxhello"`. A string trim pattern is matched as the whole string rather than as a set of its characters, so `"xxxhelloxxx".trim("xx")` is `"xhellox"`. Empty patterns, absent matches, consecutive separators, and whitespace splitting have consistent Unicode behavior. Normalization supports NFC (default), NFD, NFKC, and NFKD. `str(value, base:)` renders integers in bases 2–36, floats, labels, bytes, and other values canonically; an explicit base outside that range emits `error: base must be between 2 and 36`. For `str(10, base: 1)`, stderr is exactly:

```text
error: base must be between 2 and 36
 = hint: generate a unary representation with `"1" * 10`

```

String concatenation/repetition and JSON escaping preserve quotes, slashes, control characters, emoji, combining marks, and Unicode minus conventions.

## Spec 23

`datetime` constructs either a complete date (year/month/day), complete time (hour/minute/second), or both. A partial date emits `error: date is incomplete`; for `datetime(year: 2024)` that line is followed by `` = hint: add the `month` and `day` arguments to get a valid date``. A partial time emits `error: time is incomplete`; for `datetime(year: 2024, hour: 12)`, where both groups are partial, the time error takes priority and is followed by `` = hint: add the `minute` and `second` arguments to get a valid time``. Supplying neither emits `error: at least one of date or time must be fully specified`. Validate Gregorian month lengths and leap years (divisible by 4 except centuries unless divisible by 400): an impossible date, including February 29 in 1900 or 2100, February 30, or day 31 in a 30-day month, emits `error: date is invalid`. An out-of-range month instead emits `error: month is invalid`. Hours outside 0–23 or minutes/seconds outside 0–59 emit `error: time is invalid`. Years include negative values and at least -100 through 9999. Default display is `YYYY-MM-DD`, `HH:MM:SS`, or `YYYY-MM-DD HH:MM:SS`, with four-digit signed year padding.

Accessors return supplied date/time fields or `none` for unavailable fields; weekday is Monday=1 through Sunday=7 and ordinal is one-based day of year. `repr` lists the supplied named fields. Dates/times/full datetimes compare only where compatible. Adding/subtracting duration crosses month/year/leap/midnight boundaries correctly; time-only arithmetic wraps across midnight. Subtracting compatible datetime/time values yields a duration; subtracting a time from a date emits `error: cannot subtract time from date`.

`display(pattern)` supports bracketed components for year (including last two digits), long/short/numeric month, long/short weekday and Monday-/Sunday-based weekday number, ISO/Sunday/Monday week numbers, ordinal, 24-hour and 12-hour clocks, minute, second, and upper/lower AM/PM. Modifiers provide zero, space, or no padding. Literal separators/text are preserved. Requesting `[hour]` from a date-only value or `[year]` from a time-only value emits exactly `error: failed to format datetime (insufficient information)`. An unknown component reports its name and its zero-based byte index within the pattern: `[invalid]` emits `error: invalid component name 'invalid' at index 1`. An invalid modifier does likewise: `[year repr:invalid]` emits `error: invalid modifier 'invalid' at index 11`. Missing names and unclosed brackets are also diagnostics. These display failures have empty stdout and stderr ending in a blank line, and exit 0 under Spec 16. Noon formats as 12 PM and midnight as 12 AM.

## Spec 24

Within document evaluation, file/data functions resolve paths under the same project security model as imports. `read(path)` returns UTF-8 text; `read(path, encoding: none)` returns bytes. Missing files error. `csv` parses quoted RFC-style records, custom delimiters, array mode, header/dictionary mode, no-header mode, Unicode/special characters, single-column and empty files, and rejects unequal record lengths. `json`, `yaml`, `toml`, and `xml` decode their conventional scalar, null, array, dictionary, nested/table, multiline, and attribute structures; malformed content reached through document evaluation yields a format-specific diagnostic. A direct `eval 'json("bad.json")' --root DIR` cannot access the file and instead uses the exact status/output/diagnostic behavior specified in Spec 16. JSON with a BOM is rejected. CBOR decodes/encodes null, bool, numeric, bytes, string, array, and map data.

`json.encode(value, pretty:)`, YAML encode, TOML encode, CSV encode (array/dictionary/header/delimiter variants), and CBOR encode emit standards-compliant data and round-trip supported values. JSON preserves Unicode, nesting, booleans, nulls, large integers and tested float precision; compact JSON has no unnecessary spaces and pretty JSON uses two-space indentation. XML exposes element tags, attributes, and children, and `xml(path)` always returns an array of top-level nodes even when the input contains one root element. Thus, for `<root id="7"><child>text</child></root>`, `xml("data.xml").tag` fails with `error: cannot access fields on type array`, while `xml("data.xml").first().tag` yields `"root"`. Loader results have canonical `repr` and serialize through eval as specified above.

## Spec 25

Paged document markup lays out real text and content into valid pages. Page settings include width, height (`auto` included), margins, columns, fill, numbering, and explicit page breaks. Paragraphs wrap and paginate; alignment, horizontal/vertical spacing, boxes/blocks, and nested content work. Images load local raster assets, missing images error, and figures/captions participate in document structure. Links and URLs are interactive/extractable. Tables accept a column count and row-major cells and render their content. A grid cell whose `colspan` exceeds the configured number of columns is rejected with a clear span/column error.

Layout transforms support `rotate` (degrees/radians, negative/full-circle/small angles, selectable origin, `reflow`), `scale` (one or two axes, percentages/lengths, negative mirroring, zero/tiny/large values, one axis auto, error when both are auto, optional reflow), `move` (positive/negative absolute and relative offsets), `place` (top/center/bottom and left/center/right alignment, `dx/dy`, floating and flush placement), `stack` (ttb/btt/ltr/rtl, empty/single/multiple children, explicit/absolute/fractional gaps), and `skew` (x/y angles, negative angles, origin, reflow). These transforms can be deeply nested and combined while yielding a valid, nonempty PDF with correct content/page structure.

## Spec 26

Document structure includes headings of arbitrary level, numbering strings and numbering callbacks, level offsets, bookmark/outlined controls, labels/references, and `outline` with title, depth, indentation, custom entry fill, multiple outlines, and figure outlines. Headings are queryable with effective `level`, `body`, `numbering`, and location.

Bulleted lists, numbered `enum` lists, and term lists support markup and function-call forms, nesting/deep nesting, mixed list types, multiline items, tight versus wide layout, spacing/indent, custom marker content/arrays/functions, custom enum numbering/functions/start/full-width, and custom term separator. Footnotes support inline definitions, labels/references, and custom numbering. These elements paginate and render deterministically: identical source/configuration must produce byte-identical PDF output, including outlines/bookmarks and document metadata.

## Spec 27

Text content supports emphasis, strong weight with configurable delta (including negative), small capitals, lower/upper case transforms with Unicode, underline, overline, strike, highlight, subscript, superscript, and smart/localized quotes. Decorations accept thickness, offset, extent, stroke/paint and other side/options; they work across lines and on empty/very long content. Styling nests deeply, combines, toggles correctly when markup delimiters nest, respects word boundaries, and can be applied by show rules. Sub/superscripts contain complex styled content. Quotes support block/inline form, attribution, nesting, and language-specific marks. Case transformation also composes with math and mixed scripts.

## Spec 28

Math mode lays out inline versus display equations and supports identifiers, quoted multi-letter text, numbers, spacing, Unicode math symbols, relations/classes, scripts/primes and all four-corner `attach`, limits, operator names/custom `op`, fractions (slash and `frac`, nested and vertical/skewed/horizontal styles), binomials, roots, scalable delimiters (`lr`, floor, ceil, bars, `mid`), cases and aligned multiline equations, equation numbering/references, and bold/upright/italic/sans/caligraphic/script styles.

It supports matrices/vectors with arbitrary dimensions (including empty, 1-row/column, nested, and 5×5), delimiters, per-column alignment, row/column gaps, and augmented horizontal/vertical rules with positions/strokes. Accents include grave, acute, hat, tilde, bar/macron, dots (single/double/triple), breve, caron, circle, arrows/harpoons, double acute, combining input, dotless i/j, and size control. It supports cancel/cross with length/angle/stroke, underline/overline, annotated/unannotated under/overbrace, bracket, parenthesis, and shell. These constructs compose with fractions, roots, scripts, calculus, linear algebra, probability/statistics, theorem/proof prose, font settings, and complex nesting. Unknown math symbols and malformed calls produce diagnostics instead of broken documents.

## Spec 29

Vector drawing includes `rect`, `square`, `circle`, `ellipse`, `line`, and `polygon`, with exact length/relative sizing, auto sizing around content, inset/outset, rounded/per-corner radii, explicit vertices or regular side counts, and nonzero/even-odd fill rules including self-intersecting polygons. Fill and strokes may be absent, solid, or gradients. Strokes support thickness, per-side paint, joins (round/miter/bevel), caps, dash patterns, miter limits, and gradient paint.

Colors include named palette colors and constructors for RGB/hex (with alpha), CMYK, luma, HSL, HSV, linear RGB, Oklab, and Oklch, plus lighten/darken/saturate/desaturate/negate methods. Invalid RGB component ranges and malformed hex strings error. Linear, radial, and conic gradients support multiple colors, explicit/nonuniform stops, angles/direction keywords, rotation, interpolation color space, and relativeness to self or parent. Shapes and gradients render in PDF, PNG, and SVG and can be combined in one document.

## Spec 30

Introspection uses selectors for element functions (`heading`, `strong`, `emph`, `raw`, `figure`, `metadata`, etc.), labels (`<intro>`), and `.where(field: value)` filtering. `query(selector)` in contextual eval returns elements in document order and supports `.len`, map/filter and field access. Returned element values serialize as dictionaries with a `func` key and public fields; text content is represented as `{ "func": "text", "text": "..." }`. Headings expose level/body/numbering, raw exposes block state, and figures expose kind. HTML-target querying requires the html feature.

`state(key, initial)` identifies a document-wide state cell. `.update(value)` and `.update(previous => new)` apply in layout order; `.final()` returns the converged final value, and `.at(location)` returns the value at that point or initial before updates. Keys are independent Unicode strings; same key shares state despite different constructor initial values according to the first established state. Values can be none, bool, numbers, strings, arrays, dictionaries, and nested values. Updates compose, receive the correct previous value, and support nested/function chains. Circular nonconvergent state produces a convergence warning/error.

`metadata(value)` places queryable metadata; labels make instances addressable, but unlabeled metadata is valid. Values may be scalar, none, arrays, dictionaries, or nested. `locate(selector-or-label)` produces a location for an existing target and fails for no match. Locations expose one-based page and physical position coordinates; different elements/pages yield different positions, and page numbering can be retrieved contextually. Invalid/non-location arguments to state `.at` error. Canonical repr includes forms such as `state("test", 42)`.

## Spec 31

The deprecated `query INPUT SELECTOR` command compiles the document and returns contextual query results. Input may be `-`. It accepts `--field NAME`, `--one`, `--pretty`, `--format json|yaml`, `--input key=value`, root/path/font/package/features options, and paged/HTML target selection. It writes a deprecation warning containing ``the `typst query` subcommand is deprecated`` to stderr while succeeding.

Default output is one compact JSON value followed by newline; pretty JSON and YAML follow eval formatting. YAML sequences put the first mapping key on the dash line (for example `- func: strong`), and end with a blank line. Without `--one`, return an array in document order. `--field` replaces each element with that field; a missing field yields no values. With `--one`, the cardinality of matched elements is checked before the requested field is extracted: zero or multiple matched elements fail with `expected exactly one element, found N`, even when none of those elements has the requested field. For example, querying two headings with `--field does-not-exist --one` exits 1 with empty stdout and exact stderr `error: expected exactly one element, found 2\n`. If exactly one element matched but that element lacks the field, the command instead fails with exact stderr `error: no such field found for element\n`. Invalid selectors and compilation errors fail clearly. A missing query input similarly exits 1 with empty stdout and, for `nonexistent.typ`, exact stderr `error: input file not found (searched at nonexistent.typ)\n`; failed query invocations do not prepend the deprecation warning.

Selectors include functions, labels, and `.where`, including heading levels, raw block status, and figure kind. Querying a labeled element retains its label in the serialized object: a heading labeled `<intro>` has the JSON field `"label":"<intro>"`. For a six-heading document with bodies Introduction, Background, Motivation, Methods, Data Collection, Results at levels 1,2,2,1,2,1, querying `heading` returns six structured objects in that order; `--field level` returns `[1,2,2,1,2,1]`. Multiple `--input` definitions are visible during document compilation.

## Spec 32

Bibliographies accept BibTeX and Hayagriva YAML, one or multiple mixed source files, and raw bytes. BibTeX handles book/article/inproceedings/phdthesis/misc entries, Unicode, special-character keys, long author lists, incomplete author/year fields, and common LaTeX commands in fields. Hayagriva handles nested parent/periodical/book hierarchy. Empty sources are valid; malformed files, missing files, duplicate keys, and unknown styles produce source diagnostics.

`bibliography(source, title:, style:, full:)` emits at most one bibliography per document. Its default IEEE behavior includes cited works in citation order/numbering; `full: true` includes uncited works; `title: none` removes the heading and custom content replaces it. Multiple bibliographies error. A citation without any bibliography errors. Supported styles include IEEE, APA, MLA, Chicago author-date, Chicago notes, American Physics Society, and Harvard Cite Them Right, with their expected numeric/author-date/notes formatting and ordering.

Both `@key` and `cite(<key>)` cite entries. Adjacent citations group correctly; supplements work in markup (`@key[page]`) and the function and remain attached to their citation. Forms `normal`, `prose`, `author`, `year`, `full`, and `none` select the appropriate inline representation; invisible `none` still adds the source to the bibliography. A per-citation style can override bibliography style. Undefined keys error. Citations work in headings, captions, footnotes/nested content, across page breaks, and preserve global numbering/order.

## Spec 33

HTML export is enabled only by `--features html` or equivalent `TYPST_FEATURES`; requesting `.html`/`--format html` without it creates no output, exits 1, and emits exactly:

```text
error: html export is only available when `--features html` is passed
 = hint: html export is under active development and incomplete
 = hint: see https://github.com/typst/typst/issues/5512 for more information

```

For the deprecated `query` command with `--target html`, the same three-line HTML gate error and blank line appear first, but the command then appends its deprecation warning containing ``warning: the `typst query` subcommand is deprecated`` and the replacement-command hint. It exits 1 with empty stdout. Thus this disabled-feature query is an exception to the ordinary failed-query warning behavior in Spec 31. With the feature, compilation and querying succeed but emit this warning to stderr, including the final blank line (a successful deprecated `query` command then emits its own deprecation warning afterward):

```text
warning: html export is under active development and incomplete
 = hint: its behaviour may change at any time
 = hint: do not rely on this feature for production use cases
 = hint: see https://github.com/typst/typst/issues/5512 for more information

```

With the feature, output is deterministic HTML5 beginning `<!DOCTYPE html>`, with `<html>`, `<head>`, UTF-8 charset and viewport metadata, and `<body>`. It can go to a file or stdout.

Markup maps semantically: in a normal HTML document a `= Hello World` heading becomes `<h2>Hello World</h2>` and a following `== Section` becomes `<h3>Section</h3>`; emphasis/strong become `<em>/<strong>`; bullets/enums/terms become nested `<ul>/<ol>/<dl>`; tables become `<table>` rows/cells (and headers where declared); links become `<a href>`; inline code becomes `<code>`; and raw blocks become block/preformatted markup. Paragraphs, line breaks, super/subscript, blockquotes, and monospace text use suitable semantic tags. `html.elem` creates custom tags, attributes, and void elements. Text, code whitespace, URLs, quotes/dashes, Unicode, and `<>&` escaping are preserved. Math appears in an HTML-compatible representation. Empty, large, multiline, deeply nested, mixed-list and formatted-table documents remain well-formed.

The canonical serialization uses two-space indentation, an `<html lang="en">` root, one element per line, and a final newline. In particular, compiling this source with the HTML feature:

```typst
= Hello World

This is a simple document with *bold* and _italic_ text.

== Section 2

Some more text here.
```

produces these exact output bytes:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
  </head>
  <body>
    <h2>Hello World</h2>
    <p>This is a simple document with <strong>bold</strong> and <em>italic</em> text.</p>
    <h3>Section 2</h3>
    <p>Some more text here.</p>
  </body>
</html>
```

The newline after `</html>` is part of the output.

## Spec 34

Diagnostics are stable, UTF-8, and source-oriented. Human format begins with `error: ...` and includes file, line/column, relevant source line, caret/annotation, and helpful hints. For a file `error.typ` containing `#let x = undefined_var`, human output is exactly:

```text
error: unknown variable: undefined_var
  ┌─ error.typ:1:9
  │
1 │ #let x = undefined_var
  │          ^^^^^^^^^^^^^
```

The exact byte sequence ends with a blank line: the caret line is followed by `\n\n`, not just one newline.

Short format for the same input is exactly `error.typ:1:9: error: unknown variable: undefined_var\n`. `--diagnostic-format` applies to compile and watch. With multiple independent errors, all are on stderr and stdout remains empty. Warnings do not make successful compilation fail.

Required distinctions include: input file versus imported file not found; unknown variable; type mismatch and bad function arguments; invalid syntax/unclosed delimiter; invalid color/format/PPI/page/root/timestamp; circular import; invalid package/template; undefined citation; loader parse errors; invalid array/string index; division/domain/overflow errors; nontermination; and output I/O failures. Bibliography diagnostics include `failed to parse BibLaTeX (expected comma)`, `failed to parse BibLaTeX (duplicate key "KEY")`, `unknown style: NAME`, `multiple bibliographies are not yet supported`, and nonexistent citation-label messages. Errors must contain the characteristic phrases specified in earlier sections and enough source context for a user to identify the cause. Successful commands exit 0. Compilation/query/watch-startup failures use nonzero status as described, while recoverable watch compilation errors leave the process running.

## Spec 35

Rendering is the deterministic Typst 0.14.2 (`ccc34be7`) rendering model, not merely a container/header generator. PDF output for structural features must be byte-stable for identical source, creation timestamp, fonts, and options. A PDF written by `watch`, including when `--font-path` or `--jobs 1` is used, ends in the exact bytes `%%EOF` with no trailing line ending. Text must be extractable in reading order; page count, metadata, bookmarks/outlines, tagged structure, font metrics, glyph placement, line wrapping, math layout, list numbering, footnotes, citations, shapes, colors, gradients, and transformations must reflect the language semantics above. PNG/SVG dimensions and visuals correspond to those same laid-out pages, and HTML corresponds to the same evaluated semantic document under the HTML target.

The implementation must finish ordinary compile/eval/query/info/help/completion workloads within a few seconds, tolerate very large but finite source, and diagnose deliberately infinite/recursive programs rather than hang indefinitely. It must avoid network dependence for ordinary documents, embedded fonts, and local packages. It must not emit logging, progress, or nondeterministic data on stdout where a document, JSON/YAML value, completion script, or dependency report is expected.
