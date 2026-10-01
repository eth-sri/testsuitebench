# Clarified specification for `executable`

This document defines a command-line source-code counter compatible with **scc 3.7.0**. The delivered artifact is one directly executable file named exactly `executable`. All behavior below is observable: capitalization, field names, ordering, numeric types, exit status, output stream, punctuation, spacing in human-readable tables, and final newlines are part of the contract. Unless stated otherwise, successful commands exit 0, write their report to standard output, and leave standard error empty.

## Spec 1

### Invocation, default operation, and identity

`executable [flags] [files or directories]` recursively counts physical source lines. Multiple input operands are combined into one report. With no operands it scans the current working directory. Repeated references to the same filesystem file are counted once, even if the same operand is supplied twice. A directory operand ending in `/` is equivalent to the same path without it.

`--version` prints exactly `scc version 3.7.0\n`. `--help`/`-h` exits 0 and prints help beginning with `Sloc, Cloc and Code. Count lines of code in a directory with complexity estimation.`, followed by `Usage:\n  scc [flags] [files or directories]` and the complete flag set defined in Spec 2. `--languages`/`-l` prints the supported language list in the form `Language (comma,separated,extensions)`, including at least `Go (go)`, `Python (py,pyw,pyi)`, and `JavaScript (js,cjs,mjs)`.

The implementation must produce the same counts and aggregate-language ordering for repeated scans, including 100 immediate scans of the same tree, and must comfortably handle 500 files, 50,000-line files, 10,000-character lines, and directory nesting of at least 100 levels within a 30-second invocation limit. The numeric `--by-file` ordering exception observed in Spec 19 does not change any counts.

## Spec 2

### Accepted options and aliases

The following options must parse. Boolean options take no value unless represented inside an `@file`; scalar options consume the next token or `--name=value`; comma-list options also accept repetition, with repeated/list values accumulated. `--count-as` is the exception described in Spec 8: comma-separated mappings within one occurrence accumulate, but a later occurrence replaces the earlier occurrence's mappings.

| Short | Long | Value/default |
|---|---|---|
| `-a` | `--dryness` | boolean; implies ULOC |
|  | `--avg-wage` | integer, 56286 |
|  | `--binary` | disable binary detection |
|  | `--by-file` | include file records |
| `-m` | `--character` | character statistics |
|  | `--ci` | ASCII table borders |
|  | `--cocomo-project-type` | `organic` |
|  | `--cost-comparison` | enable LOCOMO as well as COCOMO |
|  | `--count-as` | extension mappings |
|  | `--count-ignore` | count ignore-control files themselves |
|  | `--currency-symbol` | `$` |
|  | `--debug` | configuration/timing diagnostics |
|  | `--directory-walker-job-workers` | integer, 8 |
|  | `--eaf` | float, 1 |
|  | `--exclude-dir` | list, default `.git,.hg,.svn` |
| `-x` | `--exclude-ext` | list |
| `-n` | `--exclude-file` | list, default lockfiles in Spec 10 |
|  | `--file-gc-count` | integer, 10000 |
|  | `--file-list-queue-size` | integer; performance-only |
|  | `--file-process-job-workers` | integer; performance-only |
|  | `--file-summary-job-queue-size` | integer; performance-only |
| `-f` | `--format` | renderer; `tabular` |
|  | `--format-multi` | `format:destination,...` |
|  | `--gen` | mark generated files |
|  | `--generated-markers` | repeatable strings |
| `-i` | `--include-ext` | list |
|  | `--include-symlinks` | count file symlinks |
|  | `--large-byte-count` | integer, 1000000 |
|  | `--large-line-count` | integer, 40000 |
|  | `--locomo` | enable LOCOMO |
|  | `--locomo-config` | five comma-separated floats |
|  | `--locomo-cycles` | float override |
|  | `--locomo-input-price` | float override |
|  | `--locomo-output-price` | float override |
|  | `--locomo-preset` | `large`, `medium`, `small`, or `local`; default `medium` |
|  | `--locomo-review` | float, 0.01 minutes/code-line |
|  | `--locomo-tps` | float override |
|  | `--mcp` | JSON-RPC stdio server mode |
|  | `--min` | mark minified files |
| `-z` | `--min-gen` | mark minified and generated files |
|  | `--min-gen-line-length` | integer, 255 |
|  | `--no-cocomo` | suppress COCOMO display |
| `-c` | `--no-complexity` | disable complexity unless a dependent mode forces it |
| `-d` | `--no-duplicates` | content deduplication |
|  | `--no-gen` | detect then exclude generated |
|  | `--no-gitignore` | disable `.gitignore` rules |
|  | `--no-hborder` | remove all table horizontal rules |
|  | `--no-ignore` | disable `.ignore` rules |
|  | `--no-large` | exclude over-threshold files |
|  | `--no-min` | detect then exclude minified |
|  | `--no-min-gen` | detect then exclude either class |
|  | `--no-scc-ignore` | disable `.sccignore` rules |
|  | `--no-size` | suppress size display |
| `-M` | `--not-match` | repeatable regular expression |
| `-o` | `--output` | report path |
|  | `--overhead` | float, 2.4 |
| `-p` | `--percent` | percentage rows |
|  | `--remap-all` | content marker/language mapping |
|  | `--remap-unknown` | content marker/language mapping |
| `-s` | `--sort` | `files` by default |
|  | `--size-unit` | `si` by default |
|  | `--sloccount-format` | expanded COCOMO text |
|  | `--sql-project` | SQL project identifier |
| `-t` | `--trace` | line-level diagnostics |
| `-u` | `--uloc` | unique-line calculation |
| `-v` | `--verbose` | warnings |
| `-w` | `--wide` | wide table; forces complexity |

Performance-tuning options may be operational no-ops, but every positive value and combinations of them must be accepted without changing results, deadlocking, or changing ordering. `--locomo` and `--wide` force complexity even if `--no-complexity` also occurs.

## Spec 3

### Input validation and process status

Every ordinary operand must exist and be readable as a file or directory. A missing direct operand exits 1 and writes only `file or directory could not be read: PATH\n` to stdout. `PATH` is the cleaned operand spelling: a trailing slash is removed (`examples/complexity/` reports `examples/complexity`), while other supplied prefixes are preserved. When multiple operands are missing, validation stops at the first one. `/nonexistent` and `NOTAREALDIRECTORYORFILE` follow the same rule. A broken symlink supplied directly is an error using that message; broken/circular symlinks discovered while walking are silently skipped unless verbose diagnostics apply.

An empty directory and a scan in which filters remove everything are successful. They still render a zero-row table and a `Total` row of zeros (plus zero estimates/size unless disabled); JSON is exactly `[]`; CSV consists of its header.

Unknown file types are skipped, not errors. Permission failures encountered inside a tree do not abort the scan. Read-only but readable files count normally. Filenames may contain spaces, apostrophes, emoji, CJK, Cyrillic, and other UTF-8 text without corruption or shell interpretation.

## Spec 4

### Physical line and byte accounting

`Bytes` is the exact file byte length. A physical line is delimited by LF, with CRLF treated as one terminator and the CR removed for lexical classification. A final nonempty segment without a newline is a line. An empty, zero-byte file has zero lines but still contributes one recognized file unless a filter excludes it; in particular, Spec 13's zero large-file threshold excludes it. Thus `"line1\nline2"` is 2 lines; `"\n\n\n"` is 3 blank lines; and `"line1\r\nline2\r\nline3\r\n"` is 3 code lines.

Each line belongs to exactly one of Blank, Comment, or Code and `Lines = Blank + Comment + Code`. A whitespace-only line is Blank. A line containing executable/text content is Code even when it ends with a comment. A line containing only comment syntax is Comment. Plain Text has no comment syntax, so each nonblank line is Code. Byte totals include every byte of counted files, including newline bytes; excluded/skipped files contribute nothing.

## Spec 5

### Lexical comment and string handling

Classification is language-aware. Python uses `#` line comments and both triple-single and triple-double docstrings as multiline comment regions; ordinary `'…'`/`"…"` strings shield embedded comment characters and honor backslash escapes. C, C++, Go, Java, JavaScript, CSS, C#, and headers recognize `//` where appropriate plus `/* … */`; JavaDoc is comment text. Strings and character literals shield comment delimiters and complexity tokens. Go also recognizes its quoted/raw strings. HTML/XML-family comments use `<!-- … -->`.

Multiline state persists across lines. A multiline-comment/docstring line is Comment unless it also contains code outside the comment; inline-comment lines remain Code. Apostrophes inside Python docstrings and escaped backslashes/quotes must not terminate the wrong lexical state. For the supplied 19-line mixed Python example, the result is 4 code, 11 comment, and 4 blank lines; the supplied 16-line C example is 8/5/3; 13-line Go is 6/4/3; and 13-line JavaScript is 5/6/2 (Code/Comment/Blank).

## Spec 6

### Language recognition database

Recognize extensions case-insensitively for normal detection, while preserving canonical language names. At minimum implement all names/extensions in the following compact registry (additional aliases are allowed only if they do not cause unknown test files to be counted):

`Python: py,pyw,pyi`; `Go: go`; `JavaScript: js,cjs,mjs`; `CSS: css`; `C: c,ec,pgc`; `C Header: h`; `C++: cc,cpp,cxx,c++,pcc,ino,ccm,cppm,cxxm,c++m,mxx`; `C++ Header: hh,hpp,hxx,h++,inl,ipp,ixx,tpp`; `Java: java`; `C#: cs,csx`; `Ruby: rb`; `Perl: pl,plx,pm`; `BASH: bash,bashrc`; `Shell: sh`; `Plain Text: text,txt`; `Markdown: md,markdown`; `JSON: json`; `JSON5: json5`; `JSONC: jsonc`; `YAML: yaml,yml`; `HTML: html,htm`; `XML: xml`; `Makefile: makefile,mak,mk,bp,gnumakefile`; `CMake: cmake,cmakelists.txt`; `Objective C: m`; `MATLAB: m`; `Coq: v`; `Verilog: v`; `V: v`; `Cuda: cu,cuh`; `CloudFormation (JSON): json`; `CloudFormation (YAML): yaml,yml`; `JavaServer Pages: jsp`; `License: license,licence,copying,copyright`; `CSV: csv`; and the language names/extensions in the reference corpus of Spec 39.

Special-filename recognition differs between directory discovery and a direct file operand. During a recursive directory scan, canonical files such as `makefile`, `GNUMakefile`, `license`, and `CMakeLists.txt` are recognized as the language records shown in Specs 21 and 39. When supplied directly, however, a one-line file containing `plain content\n` and named `Makefile` or `license` is ignored (`--format json` prints `[]` with no trailing LF), while the same direct content named `CMakeLists.txt` is classified as `Plain Text` through its `.txt` extension. Hidden control files `.gitignore` and `.ignore`, when explicitly counted, are recognized language records rather than unknown files. Files with extensions such as `.xyz`, `.xyz123`, `.bin`, `.log`, or no recognized filename/extension are otherwise ignored unless the extensionless shebang rule in Spec 7 applies. `Cargo.lock` likewise remains unrecognized if an explicit `--exclude-file` removes it from the default denylist.

`--languages` lists the canonical registry in its deterministic registry order, not alphabetical order, one entry per line using the `Name (ext,ext)` syntax. In particular, its first entries are `ABAP`, `ABNF`, `ActionScript`, `Ada`, `Agda`, `Alchemist`, `Alex`, `Algol 68`, `Alloy`, `Amber`, `Android Interface Definition Language`, `Apex`, and only then `APL`. `-l` and `--languages` produce identical output.

## Spec 7

### Ambiguous extensions and content disambiguation

When an extension maps to multiple languages, inspect content instead of arbitrarily choosing the first candidate. For `.m`, Objective-C syntax such as imports/interfaces selects Objective C while MATLAB syntax selects MATLAB. For `.v`, Coq proof terms select Coq, Verilog module syntax selects Verilog, and V-language declarations select V. A directory containing the three supplied `.v` examples therefore reports exactly one file of each: Coq 168/18/9/141/5, V 73/8/30/35/3, and Verilog 79/7/21/51/2, where fields are Lines/Blank/Comment/Code/Complexity.

For extensionless executable text, a first-line shebang recognizes at least direct `/usr/bin/python`, `/usr/bin/env ruby`, Bash, Perl, and forms with extra whitespace or interpreter arguments. Shebang inference is not attempted for a filename that already has an unrecognized extension: a direct `script.unknown` containing `#!/usr/bin/python\nprint 1\n` succeeds but its JSON report is `[]` with no trailing LF. Unknown shebang interpreters remain uncounted.

## Spec 8

### Explicit extension and content remapping

`--count-as` parses comma-separated `source-extension:target-extension-or-language` mappings. A target may be a canonical extension (`jsp:htm`, `new:java`) or a language name containing spaces (`chead:C Header`). Multiple comma-separated mappings in one occurrence compose and can make unknown source extensions countable. A later `--count-as` occurrence replaces all mappings from the earlier occurrence rather than accumulating them. Thus `--count-as 'new:java,chead:C Header'` counts `.new` as Java and `.chead` as C Header, but following it with `--count-as py:Ruby` leaves only the latter mapping: the `.py` file is Ruby and the `.new`/`.chead` files are ignored. It applies recursively and overrides the built-in meaning of known extensions.

`--remap-all=MARKER:LANGUAGE` searches the first 1000 bytes of every otherwise countable file and changes its language on a case-sensitive marker match. Files with unknown extensions are rejected before either content-remapping mode, so `--remap-unknown` does not make them countable: a `.zzz` file beginning with `MAGIC` remains absent under `--remap-unknown 'MAGIC:C Header'`, and a `.odd` file beginning `#!/usr/bin/python MARK` remains absent under `--remap-unknown MARK:Ruby`. `--remap-all` remaps a recognized `.java` file beginning with `MAGIC` to C Header but still does not admit neighboring `.zzz` files. Markers after byte 1000 do not match; empty files and unmatched/case-mismatched markers retain normal classification (or remain unknown). `--count-as` and content remapping may be combined.

## Spec 9

### Complexity

Complexity is enabled by default. It is an scc-style token count rather than formal cyclomatic complexity: scan code outside comments/strings and add one for every language-configured control/branch token occurrence. For C-like languages this includes relevant occurrences of `if`, `else`, `for`, `while`, `switch`/`case`, boolean `&&`/`||`, comparisons, `try`/`catch` and similar language constructs. Python includes `if`, `elif`, `else`, loops, boolean branches and exception branches. Do not add a baseline one per function.

Required calibration: sequential simple Python has complexity 0; the supplied nested Python analysis fixture has 11; the 23-code-line high-complexity Python fixture has 11; the supplied C++ switch/while/if fixture has 4; the supplied five-line Java loop fixture has 1; the canonical eight-line Python example has 3; and its Go companion has 0.

`--no-complexity` sets every summary/file complexity to zero unless LOCOMO is active. In ordinary 79-column tabular output it also omits the Complexity column, while JSON retains the field with zero. Wide mode does not re-enable calculation: it retains the `Complexity` and `Complexity/Lines` columns but reports zero and `0.00`, respectively. LOCOMO does override the flag, calculates complexity, and displays the Complexity column.

## Spec 10

### Extension, filename, and directory filters

`--include-ext` limits candidates to comma-separated extension tokens. Candidate extensions are normalized to lowercase before the case-sensitive comparison, so a lowercase `go` selects both `.go` and `.GO`, while an uppercase filter token `GO` selects neither. Normal language recognition is case-insensitive. Filter tokens must omit the leading dot: `.go` selects neither `.go` nor `.GO`, and `.js` does not exclude a `.js` file. `--exclude-ext` is also a comma/repeatable list and wins over inclusion when both mention an extension. Repeated occurrences of both options do accumulate; for example, repeated bare-token includes for `go,py` then `js`, combined with exclusions for `py` then `js`, retain only Go.

`--exclude-dir` excludes a directory name at any depth. Accept comma-separated and repeated values and ignore a trailing slash in a value. Its untouched default is `.git,.hg,.svn`. `--exclude-file` excludes exact basenames and its untouched default is `package-lock.json,Cargo.lock,yarn.lock,pubspec.lock,Podfile.lock,pnpm-lock.yaml`. For either option, the first explicit occurrence replaces the default list and later occurrences accumulate; thus `--exclude-file package.json` counts `package-lock.json` while excluding `package.json`. In a directory also containing `Cargo.lock` and `other.json`, the resulting JSON summary has two JSON files (`package-lock.json` and `other.json`); `Cargo.lock` is no longer excluded but is skipped as an unknown type. Filters compose as logical AND on inclusion conditions and logical OR on exclusions.

## Spec 11

### Ignore-control files and hidden paths

While walking, apply ignore rules from `.gitignore`, `.ignore`, and `.sccignore`, including basename globs, directory patterns, and wildcard suffixes. The compatibility behavior does not re-include a path through a later `!` line: in the supplied patterns, `ignored.txt`, `temp.txt`, `cache.txt`, `build/`, `*.log`, and `important.log` all remain ignored. `--no-gitignore`, `--no-ignore`, and `--no-scc-ignore` independently disable those sources. Disabling an ignore source does not make an unknown extension countable. In a tree where `.gitignore` contains `ignored.txt`, `*.log`, and `!important.log`, while the other controls exclude `temp.txt`, `cache/`, and `secret.txt`, `--no-gitignore` reports only `ignored.txt` and `kept.txt`: `trace.log` and `important.log` remain uncounted because `.log` is unknown.

Ignore-control files themselves are not counted by default. `--count-ignore` includes `.gitignore` and `.ignore` as language names `gitignore` and `ignore`, respectively, in addition to continuing to apply their rules. Dot-prefixed names still follow normal recognition: unknown `.hidden` is skipped, while recognized special names such as `.zshrc` may count. `.git` is excluded by the untouched default directory denylist. Empty directories never create records.

## Spec 12

### Regex path exclusion

Each `--not-match`/`-M` is a Go/RE2-style, case-sensitive regular expression applied to normalized path text and filename components. A candidate matching any expression is excluded. Repeated expressions are logical OR and are equivalent to one alternation expression. Patterns such as `.*\.test\.js`, `test/`, anchored `^.*app\.js$`, `spec.*\.py$`, `(^test|_test\.py$)`, `/test/`, `/build/`, and `\.min\.(js|css)$` must behave according to ordinary regular-expression semantics.

An invalid expression does not abort or filter: print one diagnostic per invalid pattern to stderr, such as `error parsing regexp: missing closing ]: \`[\`` or `error parsing regexp: unexpected ): \`)*\``, ignore that pattern, continue scanning, and exit 0.

## Spec 13

### Binary, symlink, and large-file policy

By default, binary data is skipped. A NUL byte is sufficient to classify a recognized-extension file as binary. `--binary` disables this detection and permits such a file to be counted lexically. Unknown `.bin` remains unknown regardless. Symlinked files are skipped by default; `--include-symlinks` counts a symlink to a readable regular target once without recursively following directory cycles.

Large files are counted normally unless `--no-large` is present. With it, exclude a file when `bytes >= --large-byte-count` or `lines >= --large-line-count`; equality is excluded. Defaults are 1,000,000 bytes and 40,000 lines. A threshold of zero therefore excludes even a zero-byte/zero-line recognized file. Thus a 5-byte file is excluded at byte threshold 5, a 40,000-line file is excluded at the default line threshold, and a 1,000,000-byte file is excluded at the default byte threshold. Large-file exclusion happens before aggregation and processed-byte totals.

## Spec 14

### Generated-file detection

Generated detection is enabled for reporting by `--gen` and as part of `-z/--min-gen`; exclusion flags also implicitly enable it. Search case-insensitively anywhere in only the first 1000 bytes. Defaults are exactly `do not edit` and `<auto-generated />`. A supplied `--generated-markers` list replaces the defaults rather than augmenting them; repeated occurrences form an any-match list.

A detected generated file remains counted but its language summary name gains ` (gen)` and its per-file JSON `Generated` is true. `--no-gen` removes generated files, while leaving minified-only files. `--no-min-gen` removes either type. Markers just inside byte 1000 match; those beginning beyond it do not.

## Spec 15

### Minified-file detection

Minified detection is enabled for reporting by `--min` and by `-z/--min-gen`; exclusion flags implicitly enable it. For a nonempty file, compare average bytes per physical line against `--min-gen-line-length` (default 255). A value at least the threshold is minified: the 350-byte, three-line JavaScript fixture is minified at 100 but not 200, and a two-byte one-line fixture is minified at threshold 1. Empty files are never minified.

Counted minified records use suffix ` (min)` and set per-file JSON `Minified` true. In the 79-column tabular renderer long names are display-truncated with one Unicode ellipsis, e.g. `JavaScript (mi…`; underlying JSON/CSV names remain complete. `--no-min` excludes minified files but retains generated-only files. If a file qualifies as both generated and minified, generated wins: only `(gen)` appears.

## Spec 16

### Duplicate removal

Without `-d/--no-duplicates`, identical files all count. With it, compute a content hash over the entire byte sequence and retain only one member of each identical-content set before all summaries, ULOC, costs, and output. Different paths to the same bytes are duplicates; duplicate operands referring to the identical filesystem identity are always counted once even without `-d`.

Calibration: the canonical `duplicates` corpus has 20 identical Java files, aggregate 3,720 lines, 760 blanks, 620 comments, 2,340 code, complexity 520, and 122,740 bytes. Deduplication yields one file with 186/38/31/117/26 and 6,137 bytes.

## Spec 17

### ULOC and DRYness

`-u/--uloc` builds a set of distinct normalized nonblank source-line strings across all retained files and reports its cardinality per language and globally. The tested normalization produces ULOC 3 for three identical three-line Python files (two code lines plus one comment line) and ULOC 96 for the canonical duplicated Java content. In JSON/CSV, `ULOC`/`Uloc` remains numeric and is zero when not requested.

Tabular ULOC adds an `(ULOC)` line beneath each language and `Unique Lines of Code (ULOC)` beneath Total. The physical two-file C++/Java `examples/complexity/` fixture reports `Unique Lines of Code (ULOC)                        27` under `--format wide --uloc`. `-a/--dryness` implies ULOC and additionally displays `DRYness %` as global ULOC divided by total physical Lines, rounded to two fractional digits but printed with two digits (`3/9 -> 0.33`, `96/3720 -> 0.03`). Explicitly combining `-u -a` must not duplicate rows.

## Spec 18

### Character and percentage analyses

`-m/--character` adds `MaxLine / MeanLine` after every language row. MaxLine is the greatest line length in characters/bytes excluding its terminator; MeanLine is the integer-truncated mean over nonblank physical lines, so blank lines do not contribute either length or divisor. A Plain Text file containing line lengths 1, 3, and 0 therefore prints `MaxLine / MeanLine      3           2`. A 264-byte four-line fixture yields 186 and 65. The canonical C++/Java complexity corpus yields C++ 39/16 and Java 27/13.

`-p/--percent` adds a `Percentage` row after each language. Each numeric summary field is divided by the corresponding grand-total field and printed with one decimal and `%`. Zero denominators print `NaN%`; a positive file count over itself still prints `100.0%`. Character and percentage rows can coexist, in the order summary, Percentage, MaxLine/MeanLine. Auxiliary rows are separated between language groups by 79 ASCII hyphens (109 in wide mode), even outside CI mode.

## Spec 19

### Ordering

Sort language rows with `--sort files|name|lines|blanks|blank|code|comments|comment|complexity|bytes`. `files` is default. Name is ascending lexical order; every numeric key is descending. Ties are resolved by canonical language name ascending. An unrecognized sort value silently falls back to `files` and succeeds.

When `--by-file` is active, `name` orders file locations ascending. Numeric keys request descending file values, but the JSON file-array order is not stable: repeated `--by-file --sort lines` scans of `a.py` (1 line) and `z.py` (4 lines) produced both `a.py,z.py` and `z.py,a.py`. Tests must therefore compare the file records by identity and values rather than require a numeric-key JSON array order. CSV and MCP accept singular `blank` and `comment`; plural spellings work for language sorting. Totals are never sorted among data. Language-row sorting remains consistent across renderers and combined-format output.

## Spec 20

### Default tabular renderer

The default is an exact fixed-width 79-column table. With complexity enabled its header is exactly:

```text
Language            Files       Lines    Blanks  Comments       Code Complexity
```

With either `--no-complexity` or `-c`, the Complexity column is omitted but the table remains 79 columns wide. The remaining fields are redistributed and the exact header is:

```text
Language                    Files       Lines     Blanks    Comments       Code
```

Every horizontal rule remains 79 characters wide.
## Spec 21

### Exact aggregate baseline for the physical `examples/` fixture tree

The following is the authoritative default report when the supplied physical `examples/` fixture directory is the sole input (or is the current working directory for a no-argument scan). Besides fixing every aggregate language row, it defines truncation, alignment, order, cost, and byte totals. Other flags transform these physical files according to Specs 10–34. The executable does not synthesize this corpus when the path is absent; Spec 38 defines that boundary.

```text
───────────────────────────────────────────────────────────────────────────────
Language            Files       Lines    Blanks  Comments       Code Complexity
───────────────────────────────────────────────────────────────────────────────
Java                   24       3,913       798       651      2,464        547
Python                 14         379        32        51        296         55
JavaScript             12         225         4        26        195         48
CSS                     5          24         0        19          5          0
C++                     3          38         2         3         33          4
Go                      3          25         8         6         11          0
Makefile                3           3         0         0          3          0
Markdown                3           0         0         0          0          0
Perl                    3          14         3         3          8          2
C                       2          54         9         1         44         11
C Header                2         241         3        67        171         14
C#                      2         623        83       130        410         49
Clipper                 2          56        12        19         25          0
Cuda                    2          61        14         9         38          5
JavaServer Pag…         2           1         0         0          1          0
License                 2           1         0         0          1          0
PHP                     2           1         0         0          1          0
Plain Text              2           3         0         0          3          0
TypeScript              2          20         4         2         14          2
YAML                    2         150        32         1        117          0
ABNF                    1          20         4         0         16          8
AWK                     1          28         4         1         23          4
Alchemist               1          20         0         0         20         55
Algol 68                1          31         6         0         25          6
Alloy                   1          50         6        40          4          0
Amber                   1          50         5         1         44         10
Apex                    1          48         6         9         33          9
ArkTs                   1          64         3         3         58          1
Arturo                  1         417        66        89        262         20
Astro                   1          12         0         0         12          0
BASH                    1           1         0         0          1          0
Bean                    1          17         3         0         14          0
Bicep                   1          50         8         5         37          4
Bitbucket Pipe…         1          23         1         0         22          0
Blueprint               1          12         2         5          5          0
Boo                     1           1         0         0          1          0
Bosque                  1         179        32         8        139          1
Bru                     1          20         3         0         17          0
C Shell                 1           1         0         0          1          0
C++ Header              1          39         6         1         32          8
C3                      1          10         1         4          5          0
CMake                   1          28         4         3         21          7
Cairo                   1          28         3         0         25          4
Cangjie                 1          27         5         2         20          2
Cap'n Proto             1          27         5         1         21          0
Chapel                  1          14         0         2         12          0
Circom                  1          34         4         7         23          2
Clojure                 1           1         0         0          1          0
CloudFormation…         1         407         0         0        407          0
CloudFormation…         1         150        16         1        133         19
Coq                     1         168        18         9        141          5
Cypher                  1          28         6        12         10         10
D2                      1          51         9         2         40          0
DAML                    1          14         4         0         10          1
DM                      1          21         2         7         12          4
DOT                     1          12         0         5          7          0
Docker ignore           1           3         0         1          2          0
Dockerfile              1           1         0         0          1          0
Elixir Template         1           6         1         0          5          0
Elm                     1           6         1         0          5          1
EmiT                    1          23         9         1         13          5
Extensible Sty…         1           0         0         0          0          0
F#                      1           3         0         0          3          1
FSL                     1         151        36         1        114         33
FXML                    1           9         1         0          8          0
Factor                  1          23         4         1         18          2
Flow9                   1          21         3         6         12          5
Freemarker Tem…         1           0         0         0          0          0
Futhark                 1          29         3        10         16          2
Gemfile                 1           1         0         0          1          0
Gherkin Specif…         1           0         0         0          0          0
Gleam                   1          17         2         0         15          6
Go+                     1          37         4         2         31          8
Godot Scene             1          24         7         0         17          0
GraphQL                 1      61,602     9,958    36,963     14,681      1,533
Gremlin                 1          31         4         9         18          0
Gwion                   1          35         7         0         28          7
HAML                    1          14         3         1         10          0
HCL                     1         134        13        45         76          0
Hare                    1          39         8         1         30          7
Haskell                 1          51         8         0         43          2
INI                     1          10         1         2          7          0
JCL                     1          20         0         5         15          7
JSON5                   1          13         0         2         11          0
JSONC                   1           9         0         6          3          0
Jsonnet                 1          40         6         5         29          3
Korn Shell              1           1         0         0          1          0
Koto                    1          17         4         0         13          4
LALRPOP                 1          36         7         3         26          0
LLVM IR                 1           5         0         1          4          0
LiveScript              1          52        21         9         22          7
Lua                     1          15         2         1         12          4
Luau                    1          16         2         1         13          4
Luna                    1          23         5         1         17          0
MATLAB                  1         471        55        67        349         54
MLIR                    1          68        10         9         49          2
Macromedia eXt…         1           0         0         0          0          0
Metal                   1         401       233        45        123          1
Mojo                    1          30         6         3         21          5
Monkey C                1          74        12         0         62         12
Moonbit                 1          16         0         3         13          4
Nature                  1          37        10         2         25          5
Nushell                 1          22         2         2         18          2
Objective C             1         896       150        66        680         57
OpenQASM                1          89        10        21         58         14
OpenTofu                1          31         7         6         18         21
POML                    1          11         2         1          8          0
Pkl                     1          39         7        21         11          0
PostScript              1          18         1         2         15          4
Q#                      1          31         6         2         23          5
R                       1          12         3         1          8          2
RAML                    1          48         1         1         46          0
Racket                  1         107        14         2         91         33
Rakefile                1           1         0         0          1          0
Rebol                   1         108         1         2        105         11
Redscript               1          84         9        24         51         12
Report Definit…         1           0         0         0          0          0
Rich Text Form…         1          18         1         0         17          0
Scallop                 1          24         4         6         14          5
Seed7                   1          25         2         3         20          5
Shell                   1           1         0         0          1          0
Sieve                   1         192        14        14        164         47
Slang                   1          15         2         5          8          0
Slint                   1          72         5         2         65          9
Smalltalk               1          81        21         3         57          0
Snakemake               1          67        13        10         44          0
Stan                    1         141         3        15        123          0
Systemd                 1          15         2         2         11          0
TOML                    1          40         9         3         28          0
TOON                    1          65         0         0         65          0
TTCN-3                  1          61         8        15         38          0
Tact                    1          20         4         4         12          2
Teal                    1          15         0         6          9          2
Templ                   1           9         1         0          8          1
Tera                    1           8         0         0          8          4
Terraform               1          31         7         6         18         21
Textile                 1           9         2         6          1          0
TypeSpec                1          19         4         0         15          0
Typst                   1          16         4         3          9          0
Up                      1          24         2        12         10          3
V                       1          73         8        30         35          3
Vala                    1          20         1         1         18          3
Varnish Config…         1           0         0         0          0          0
Verilog                 1          79         7        21         51          2
Vim Script              1          20         3         2         15          1
Web Services D…         1           1         0         0          1          0
WebGPU Enhance…         1          19         3         4         12          1
Windows Resour…         1          51         6         6         39          0
Wren                    1         188        26        37        125          8
XHTML                   1          12         0         1         11          0
XML Schema              1           1         0         0          1          0
XMake                   1          38        11         2         25          5
Yarn                    1          30         4         0         26          5
Zig                     1          13         1         0         12          2
ZoKrates                1          16         2         5          9          2
Zsh                     1           1         0         0          1          0
jq                      1          26         2         1         23          5
wenyan                  1          12         0         1         11          0
───────────────────────────────────────────────────────────────────────────────
Total                 230      74,614    12,077    38,788     23,749      2,938
───────────────────────────────────────────────────────────────────────────────
Estimated Cost to Develop (organic) $751,662
Estimated Schedule Effort (organic) 12.34 months
Estimated People Required (organic) 5.41
───────────────────────────────────────────────────────────────────────────────
Processed 2551003 bytes, 2.551 megabytes (SI)
───────────────────────────────────────────────────────────────────────────────
```

Every normal horizontal rule is 79 U+2500 BOX DRAWINGS LIGHT HORIZONTAL characters; `--ci` substitutes 79 ASCII `-`. Integers are right-aligned and thousands-separated. Data uses the widths demonstrated here:

```text
───────────────────────────────────────────────────────────────────────────────
Language            Files       Lines    Blanks  Comments       Code Complexity
───────────────────────────────────────────────────────────────────────────────
Go                      1          19         6         6          7          0
Python                  1           8         2         1          5          3
───────────────────────────────────────────────────────────────────────────────
Total                   2          27         8         7         12          3
───────────────────────────────────────────────────────────────────────────────
Estimated Cost to Develop (organic) $259
Estimated Schedule Effort (organic) 0.60 months
Estimated People Required (organic) 0.04
───────────────────────────────────────────────────────────────────────────────
Processed 304 bytes, 0.000 megabytes (SI)
───────────────────────────────────────────────────────────────────────────────
```

Rows use the selected order. When complexity is disabled, remove its header/value column while retaining the 79-column rules and using the redistributed header in Spec 20. `--no-hborder` removes every horizontal-rule line but preserves all other lines. `--no-size` removes the Processed line and its otherwise dedicated separation. Zero results preserve header, Total, and applicable estimate/size sections.

## Spec 22

### Wide and by-file human output

`-w`, `--wide`, or `--format wide` uses a 109-column table headed exactly `Language                              Files     Lines   Blanks  Comments     Code Complexity Complexity/Lines`. It forces complexity. The last value for a language is `100 * Complexity / Code`, two decimals, or 0.00 for zero code. The Total last value is the sum of the displayed per-language ratios (not `total complexity / total code`). In wide output the COCOMO and Processed lines share one footer section with only the final rule after them.

`--by-file` retains each language summary and inserts a rule plus one row per file beneath it. Tabular file locations are left-truncated to the fixed name column with `~` marking omitted leading path text. File rows have Lines, Blanks, Comments, Code, Complexity in the same columns. Long language names are truncated with `…` to fit. Percent/character/ULOC auxiliary rows and by-file rows combine without changing aggregate values.

## Spec 23

### JSON renderer

`--format json` writes one compact JSON array and no cost/footer text. Each language object has exactly these keys in this order and JSON types:

```json
{"Name":"Go","Bytes":165,"CodeBytes":0,"Lines":19,"Code":7,"Comment":6,"Blank":6,"Complexity":0,"Count":1,"WeightedComplexity":0,"Files":[],"LineLength":null,"ULOC":0}
```

`Name` includes `(min)`/`(gen)` when requested. `CodeBytes` and `WeightedComplexity` are zero in evaluated cases. `LineLength` is null unless character data is representable. Without `--by-file`, `Files` is `[]`. With it, each file object contains, in order: `Language`, `PossibleLanguages` array, `Filename` basename, `Extension` without dot, normalized relative `Location`, `Symlocation`, `Bytes`, `Lines`, `Code`, `Comment`, `Blank`, `Complexity`, `WeightedComplexity`, `Hash` (null unless needed), `Binary`, `Minified`, `Generated`, `EndPoint`, and `Uloc`. Booleans and numbers are native JSON values. Standalone JSON output ends directly after `]` with no LF. When JSON is the final renderer in `--format-multi`, the combined output instead ends with exactly one LF after `]`.

For the canonical Go+Python pair the array values are exactly Go `(165 bytes,19 lines,7 code,6 comment,6 blank,0 complexity,1 file)` then Python `(139,8,5,1,2,3,1)`.

## Spec 24

### JSON2 renderer

`--format json2` writes one compact object with keys `languageSummary`, `estimatedCost`, `estimatedScheduleMonths`, and `estimatedPeople`. `languageSummary` is precisely the JSON array schema from Spec 23. Estimate values are full-precision JSON numbers, not display-rounded strings. For the canonical Go+Python pair they are `259.85772650511944`, `0.5970539799622496`, and `0.03866677509680415`. For the mixed C/Go/JavaScript/Python fixture with 23 code lines and zero complexity, they are exactly `514.5286402690015`, `0.774015552372697`, and `0.05905759842732706`. Standalone JSON2 ends directly after `}` with no LF; as the final renderer in `--format-multi`, it ends with exactly one LF after `}`.

When LOCOMO is enabled, the COCOMO fields are followed, in exact key order, by `estimatedLLMCost`, `estimatedLLMInputTokens`, `estimatedLLMOutputTokens`, `estimatedLLMGenerationSeconds`, `estimatedLLMReviewHours`, `estimatedLLMPreset`, `estimatedLLMAverageComplexityMultiplier`, and `estimatedLLMCycles`. The preset is a JSON string and the other seven values are JSON numbers. Without LOCOMO, none of these keys appears. `--no-cocomo` affects human display but JSON language data remains valid.

## Spec 25

### CSV renderers

`--format csv` is one RFC-4180-style aggregate row per language with exact header:

```text
Language,Lines,Code,Comments,Blanks,Complexity,Bytes,Files,ULOC
```

No totals/cost row is appended. Fields requiring quoting use ordinary CSV rules. The canonical pair rows are `Go,19,7,6,6,0,165,1,0` and `Python,8,5,1,2,3,139,1,0`.

`--format csv-stream` always emits per-file rows, independent of `--by-file`, with exact header `Language,Provider,Filename,Lines,Code,Comments,Blanks,Complexity,Bytes,Uloc`. `Provider` is the normalized file location and `Filename` is also the location for direct canonical example operands, but in aggregate by-file CSV, Provider is location and Filename is basename. Paths containing commas/quotes are escaped by CSV rules. File order may reflect discovery for csv-stream; all records and values must be present.

## Spec 26

### cloc-compatible YAML

`--format cloc-yaml` emits valid YAML beginning `# https://github.com/boyter/scc/`. The next mapping is `header`, whose `url` value is exactly `https://github.com/boyter/scc/` (including scheme and trailing slash), followed by `version: 3.7.0`, timing/rate fields, `n_files`, and `n_lines`; timing may reflect the run. Each canonical language key maps to `name`, `code`, `comment`, `blank`, and `nFiles`. Final `SUM` has those four numeric totals. For the canonical pair, totals are code 12, comment 7, blank 8, nFiles 2, n_lines 27. Language aggregation must combine multiple same-language files.

## Spec 27

### HTML renderers

`--format html` emits a complete single-line-opening HTML document with `<html lang="en">`, UTF-8 metadata, title `scc html output`, built-in table CSS, body, and `<table id="scc-table">`. `--format html-table` emits only that table (no html/head/body wrapper).

The table contains `thead`, `tbody`, and `tfoot`; exact headers are `Language, Files, Lines, Blank, Comment, Code, Complexity, Bytes, Uloc`. Language rows use `<th>` cells. Total is in `tfoot`, followed by one colspan cell containing COCOMO lines joined by `<br>`; LOCOMO lines are included when enabled. With `--by-file`, insert file detail `<tr>` rows using `<td>` cells immediately after each language. File-location cell text is inserted without HTML entity escaping: a path ending in `x&y.py` appears with the literal `&` in `<td>.../x&y.py</td>`, not as `x&amp;y.py`.

## Spec 28

### SQL renderers

`--format sql` emits lowercase `create table metadata` and `create table t` declarations, then a transaction of one `insert into t values(...)` per file, then a second transaction inserting metadata. `--format sql-insert` omits both CREATE statements but retains both transactions and inserts. Table `t` value order is Project, Language, File, File_dirname, File_basename, nByte, nBlank, nComment, nCode, nComplexity, nUloc. Metadata order is timestamp (`YYYY-MM-DD HH:MM:SS` UTC-compatible text), Project, elapsed seconds with six decimals, estimated cost, schedule, and people with six decimals.

The SQL DDL, including capitalization and whitespace, is:

```sql
create table metadata (   -- github.com/boyter/scc v 3.7.0
             timestamp text,
             Project   text,
             elapsed_s real,
             estimated_cost real,
             estimated_schedule_months real,
             estimated_people real);
create table t        (
             Project       text   ,
             Language      text   ,
             File          text   ,
             File_dirname  text   ,
             File_basename text   ,
             nByte         integer,
             nBlank        integer,
             nComment      integer,
             nCode         integer,
             nComplexity   integer,
             nUloc         integer    
);
```

Each transaction uses the exact one-line tokens `begin transaction;` and `commit;`. A directory-discovered record uses the leaf filename for `File_basename`. A direct file operand instead uses its entire supplied normalized location for `File_basename`, even though this is not a conventional basename. Thus direct operands `examples/language/python.py` and `examples/language/go.go` produce:

```sql
begin transaction;
insert into t values('myproject', 'Python', 'examples/language/python.py', 'examples/language/', 'examples/language/python.py', 139, 2, 1, 5, 3, 0);
insert into t values('myproject', 'Go', 'examples/language/go.go', 'examples/language/', 'examples/language/go.go', 165, 6, 6, 7, 0, 0);
commit;
begin transaction;
insert into metadata values('YYYY-MM-DD HH:MM:SS', 'myproject', ELAPSED, 259.857727, 0.597054, 0.038667);
commit;
```

Here the timestamp is a real current timestamp and `ELAPSED` is the run's decimal elapsed value rendered to six places; the remaining numbers are literal results of the cost formulas. SQL insertion order may follow harvest order.

Project defaults to the comma-joined input operands and is replaced by `--sql-project`. In each `insert into t` statement, double every apostrophe in text fields as `''`; this applies to Project and file paths. The Project field in the ordinary `insert into metadata` statement is instead inserted verbatim: project `Bob's` appears there as the unescaped SQL text `'Bob's'`. In LOCOMO mode, after the ordinary metadata transaction, append another `begin transaction;` block containing `insert into locomo_metadata values(...)` and then `commit;`. The observed value order is timestamp, Project, cost, input tokens, output tokens, generation seconds, review hours, preset, and cycles. `--format sql` does not emit a corresponding `create table locomo_metadata` declaration. The LOCOMO insertion must be absent otherwise. SQL statements and transaction keywords match the lowercase spellings above.

## Spec 29

### OpenMetrics renderer

`--format openmetrics` begins with these exact declarations, in this order:

```text
# TYPE scc_files gauge
# HELP scc_files Number of sourcecode files.
# TYPE scc_lines gauge
# HELP scc_lines Number of lines.
# TYPE scc_code gauge
# HELP scc_code Number of lines of actual code.
# TYPE scc_comments gauge
# HELP scc_comments Number of comments.
# TYPE scc_blanks gauge
# HELP scc_blanks Number of blank lines.
# TYPE scc_complexity gauge
# HELP scc_complexity Code complexity.
# TYPE scc_bytes gauge
# UNIT scc_bytes bytes
# HELP scc_bytes Size in bytes.
```

Aggregate metrics are integer samples labeled `{language="NAME"}` in that order for each language. With `--by-file`, omit `scc_files` samples and label each other sample `{language="NAME",file="LOCATION"}` per file. In file-label values, backslashes are doubled but double quotes are emitted literally rather than backslash-escaped. A location ending in `quote"slash\name.py` therefore produces `file=".../quote"slash\\name.py"`. End per-file output with `# EOF`. Every metric sample value is unquoted numeric text.

## Spec 30

### Multiple formats and report destinations

`--format-multi` overrides `--format` and parses comma-separated `format:destination` pairs. `stdout` destinations are rendered consecutively in listed order with each renderer’s normal terminator; file destinations are created and receive only that renderer. All listed formats from Specs 20 and 22–29 may be combined. No data is rescanned differently between formats.

`--output PATH` creates/truncates PATH, writes the selected single report there, and prints exactly `results written to PATH\n` to stdout. When it is combined with `--format-multi`, renderers having explicit file destinations still write to those destinations, but every renderer whose destination is `stdout` writes to PATH instead. The process stdout contains only the same success message naming PATH; PATH contains the rendered `stdout`-destination report rather than being empty. With format-multi file destinations alone and no `--output`, stdout may be empty.

## Spec 31

### Basic COCOMO

COCOMO uses retained **Code** lines as SLOC and is displayed by default. Let `K = Code/1000`. Project coefficient tuples `(a,b,c,d)` are organic `(2.4,1.05,2.5,0.38)`, semi-detached `(3.0,1.12,2.5,0.35)`, embedded `(3.6,1.20,2.5,0.32)`, or `custom,a,b,c,d`. Compute:

```text
effort_person_months = a * K^b * EAF
schedule_months      = c * effort_person_months^d
people               = effort_person_months / schedule_months  (0 if schedule is 0)
cost                 = effort_person_months * floor(avg_wage / 12) * overhead
```

Defaults are wage 56286, overhead 2.4, EAF 1.0. Human output truncates/rounds cost to a comma-grouped whole currency amount as demonstrated (`10 code -> $214`), schedule and people to two decimals, and prefixes the exact currency symbol without added space. The parenthesized label repeats the entire project-type argument: `--cocomo-project-type custom,1,1,1,1` produces `Estimated Cost to Develop (custom,1,1,1,1)`, `Estimated Schedule Effort (custom,1,1,1,1)`, and `Estimated People Required (custom,1,1,1,1)`. Zero SLOC produces `$0`, `0.00 months`, `0.00`. `--no-cocomo` removes these three lines; LOCOMO may still remain. `--avg-wage`, `--overhead`, `--eaf`, and project type compose.

## Spec 32

### SLOCCount-style COCOMO

`--sloccount-format` replaces the terse three-line section with this layout, substituting values and selected coefficients:

```text
Total Physical Source Lines of Code (SLOC)                     = 10
Development Effort Estimate, Person-Years (Person-Months)      = 0.00 (0.02)
 (Basic COCOMO model, Person-Months = 2.40*(KSLOC**1.05)*1.00)
Schedule Estimate, Years (Months)                              = 0.05 (0.56)
 (Basic COCOMO model, Months = 2.50*(person-months**0.38))
Estimated Average Number of Developers (Effort/Schedule)       = 0.03
Total Estimated Cost to Develop                                = $215
 (average salary = $56,286/year, overhead = 2.40)
```

This mode uses the same formulas but its displayed cost rounds independently (hence $215 here versus terse $214). Preserve alignment, two-decimal coefficient formatting, years = months/12, and grouped wage/cost.

## Spec 33

### LOCOMO

`--locomo` enables LLM-generation estimates after COCOMO; `--cost-comparison` also enables LOCOMO. Defaults are config `tokensPerLine=10,inputPerLine=20,complexityWeight=5,iterations=1.5,iterationWeight=2`, review 0.01 minutes/code-line, and preset medium. Presets are:

| preset | input $/1M | output $/1M | output TPS |
|---|---:|---:|---:|
| large | 10.00 | 30.00 | 30 |
| medium | 3.00 | 15.00 | 50 |
| small | 0.50 | 2.00 | 100 |
| local | 0 | 0 | 15 |

An invalid preset falls back to medium. Explicit price/TPS options override the preset. `--locomo-config` must contain exactly five numeric comma-separated values or the entire value is ignored and defaults retained. Let `density = Complexity / Code` (zero when Code is zero), `root = sqrt(density)`, `inputFactor = 1 + root * complexityWeight`, and, unless explicitly overridden, `cycles = iterations + root * iterationWeight`. Then `outputTokens = Code * tokensPerLine * cycles` and `inputTokens = Code * inputPerLine * inputFactor * cycles`. Cost is `(inputTokens*inputPrice + outputTokens*outputPrice)/1,000,000`; serial generation seconds are `outputTokens/TPS` (zero when TPS is zero); review hours are `Code * reviewMinutes / 60`. Required calibration is 1.5 cycles at zero complexity and 2.9 for complexity 11 over 23 code using defaults.

Human rendering is exactly:

```text
LOCOMO LLM Cost Estimate (medium)
  Tokens Required (in/out) 0.0M / 0.0M
  Cost to Generate $0
  Estimated Cycles 1.5
  Generation Time (serial) 0.1 minutes
  Human Review Time 0.0 hours
  Disclaimer: rough ballpark for regenerating code using a LLM.
  Does not account for context reuse, test generation, or heavy debugging.
```

Use one decimal for token millions/cycles and adaptive minutes/hours for time as in the calibration. LOCOMO forces complexity, works with `--no-cocomo`, appears in HTML/JSON2/SQL/MCP forms, and handles zero code/TPS without NaN or infinity.

## Spec 34

### Size footer and novelty units

Unless `--no-size`, tabular/wide output reports `Processed N bytes, M megabytes (UNIT)`. SI uses `N/1,000,000`, three decimals, label `SI`; binary uses `N/1,048,576`, label `BINARY`; mixed aliases are accepted. For the 514-byte corpus both display 0.001 SI and 0.000 BINARY.

The novelty modes must use exact labels/messages before the Processed line:

| value | message | required 1,320,367-byte display |
|---|---|---|
| `xkcd-kb` | `1000 bytes during leap years, 1024 otherwise` | `0.000 megabytes (XKCD-KB)` |
| `xkcd-kelly` | `compromise between 1000 and 1024 bytes` | `1.289 megabytes (XKCD-KELLY)` |
| `xkcd-imaginary` | `used in quantum computing` | `¯\\_(ツ)_/¯ megabytes (XKCD-IMAGINARY)` |
| `xkcd-intel` | `calculated on pentium F.P.U.` | `1.259 megabytes (XKCD-INTEL)` |
| `xkcd-drive` | `shrinks by 4 bytes every year for marketing reasons` | `1.802 megabytes (XKCD-DRIVE)` |
| `xkcd-bakers` | `9 bits to the byte since you're such a good customer` | `0.995 megabytes (XKCD-BAKERS)` |

## Spec 35

### Verbose, debug, trace, and CI diagnostics

Diagnostics are written to stdout before the report. Every log line is `LEVEL YYYY-MM-DDTHH:MM:SSZ: message`, with a UTC RFC3339 whole-second timestamp. `--verbose` emits only relevant WARN lines and otherwise produces the normal report unchanged. Required warnings are `skipping file unknown extension: BASENAME` and `skipping symlink file: BASENAME`; for a symlink at any directory depth named `alias.py`, the latter message ends exactly `skipping symlink file: alias.py`. With `--include-symlinks`, the latter warning disappears and the target counts.

`--trace`/`-t` prints extension-map/language-feature timing, file-read timing, and one line per physical line, followed by processing timing. For one Python file, the exact pre-report sequence is below; substitute the same RFC3339 timestamp form at every `{TS}`, a decimal nonnegative timing at every `{N}`, the absolute input path at `{PATH}`, and one classification line for every physical line:

```text
TRACE {TS}: nanoseconds build extension to language: {N}
TRACE {TS}: configured to lazy load language features
TRACE {TS}: nanoseconds to build language Python features: {N}
TRACE {TS}: nanoseconds read into memory: {PATH}: {N}
TRACE {TS}: {PATH} line 1 ended with state: 1: counted as comment
TRACE {TS}: {PATH} line 2 ended with state: 1: counted as code
...
TRACE {TS}: nanoseconds process: {PATH}: {N}
```

State 1 is ordinary lexical state; Python triple-quoted comment lines remain state 9 until their closing line, which ends state 1. It then prints the selected report (including a compact JSON line if JSON was selected). Trace timing values are arbitrary nonnegative integers but labels/order are stable. For the seven-line `simple.py` diagnostic fixture, the line classifications are comment, code, comment, code, blank, code, code, complexity is 1, and bytes are 128. The full trace therefore contains 12 TRACE lines. For the 11-line multiline fixture the states/classes are `9/comment, 9/comment, 9/comment, 1/comment, 1/blank, 1/code, 1/comment, 1/code, 1/blank, 1/comment, 1/code`; its report is 2 blank, 6 comment, 3 code, complexity 0, and 140 bytes.

`--debug` prints configuration lines using the same timestamped `DEBUG` prefix. It must include exactly one `Complexity Calculation: true|false` line reflecting ordinary complexity state and an `IncludeSymLinks: true` line when that option is enabled. CI affects report borders even with trace/verbose, never diagnostic spelling.

## Spec 36

### `@file`, errors, and similar-flag suggestions

If and only if the sole process argument begins `@`, read the named UTF-8 file and replace argv with its trimmed nonempty lines, one argument per line. Blank/whitespace-only lines are ignored. If `@PATH` appears alongside any other argument it is an ordinary path and normally fails validation. Missing sole flag-file exits 1 with `Error reading flags from a file: open PATH: no such file or directory\n` on stdout.

Unknown flags exit 1 and print to stderr: `Error: unknown flag: --NAME`, full Usage/Flags help, then optional suggestions. Similarity is case-sensitive normalized Levenshtein similarity `1-distance/max(lengths)` with threshold 0.75; skip one-character candidates, sort descending similarity then alphabetically, and use:

```text
The most similar flag of --verion is:
	--version
```

Pluralize `flags`/`are` for multiple matches. Required mappings are `--formt` and `--forma -> --format`; `--helpo -> --help`; `--locom -> --locomo`; `--debugg -> --debug`; `--genn -> --gen`; `--exclude-di -> --exclude-dir, --exclude-file`; and `--no-men -> --no-gen, --no-min` in shown order. `--xyzabc`, `--qwerty`, `--q`, and uppercase `--DEBUG` have no suggestion.

## Spec 37

### MCP stdio server

With `--mcp`, consume newline-delimited JSON-RPC 2.0 requests from stdin and write one compact response line per request. An initialize response echoes the request's `params.protocolVersion` exactly. For an initialize request with id 1 and offered protocol `2024-11-05`, the response is exactly:

```json
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"scc","version":"3.7.0"}}}
```

Support `tools/call` for tool name `analyze`. Its arguments are `path` (required), `by_file` boolean, `sort` (`name`, `lines`, `bytes`, `blank`, `code`, `comment`, `complexity`), `limit` integer, `include_ext` comma-list, `exclude_ext` comma-list, `no_min_gen` boolean, `locomo` boolean, and `locomo_preset`. CLI-equivalent semantics apply. Negative limit means unlimited; a nonnegative limit caps each language’s `fileList`, not the language list or aggregate counts.

The successful call response wraps one content item whose `text` is a pretty-printed JSON string. The inner object has `path`; `languages` containing lowercase-key objects `name,files,lines,code,comment,blank,complexity,bytes` and optional `fileList`; `totals` with those numeric fields except name; `cocomo` with full-precision `estimatedCost,estimatedScheduleMonths,estimatedPeople`; and aliases `totalFiles,totalLines,totalCode`. File-list objects contain lowercase `location,filename,language,lines,code,comment,blank,complexity,bytes`. LOCOMO adds `locomo` with numeric `cost,inputTokens,outputTokens,generationSeconds,reviewHours,averageComplexityMultiplier,cycles` and string `preset`. `averageComplexityMultiplier` is the product of the LOCOMO input factor and cycles, not the input factor alone; for the full canonical language corpus under the medium preset it is `5.78269333029447`, with cycles `2.16727466192907`.

A missing MCP path returns a normal JSON-RPC result with text `path cannot be accessed: PATH: stat PATH: no such file or directory` and `isError:true` on the result object. MCP resolves a relative argument against the server's working directory and cleans it before substituting `PATH`; from `/workspace`, `examples/language/python.py` is reported as `/workspace/examples/language/python.py`, and a trailing slash is removed. It does not crash and process exit remains 0. The canonical direct Python inner response has totals 1 file, 8 lines, 5 code, 1 comment, 2 blank, complexity 3, 139 bytes and COCOMO values `103.63676084240372`, `0.4210263841034329`, `0.02186857245950927`.

## Spec 38

### Physical reference-corpus data and missing paths

The records below describe the physical scc reference fixtures when those files are actually present. They are calibration data, not built-in virtual inputs: the executable neither synthesizes absent files nor matches a missing operand by an `examples/...` suffix or repository-relative name. From a working directory without that tree, an operand such as `examples/language/python.py`, `examples/oneline.py`, `examples/language/`, `examples/complexity/`, `examples/duplicates/`, `examples/minified/`, `examples/issue564/`, `examples/`, `main.go`, `processor/`, or `scripts/` is an ordinary missing path and follows Spec 3: exit 1, write `file or directory could not be read: PATH\n` to stdout, and leave stderr empty. This validation occurs before duplicate suppression, sorting, LOCOMO, size-unit conversion, analysis, or rendering. An `@file` expands normally, but an absent path obtained from it has the same result.

When the fixture files exist, all transformations, filtering, sorting, formats, and formulas above apply to their actual contents, with caller-supplied path prefixes preserved in file-location fields. These rows identify the contents of the supplied scc fixture revision, not behavior keyed to a basename: an unrelated file at the same relative name is counted from its own bytes rather than receiving a fixture row. The fixture records are:

| physical fixture operand | Language | Files | Lines | Blank | Comment | Code | Complexity | Bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `examples/language/python.py` | Python | 1 | 8 | 2 | 1 | 5 | 3 | 139 |
| `examples/language/go.go` | Go | 1 | 19 | 6 | 6 | 7 | 0 | 165 |
| `examples/language/javascript.js` | JavaScript | 1 | 24 | 4 | 0 | 20 | 0 | 402 |
| `examples/complexity/complexity.cpp` | C++ | 1 | 25 | 1 | 1 | 23 | 4 | 441 |
| `examples/complexity/complexity.java` | Java | 1 | 5 | 0 | 0 | 5 | 1 | 73 |
| `examples/complexity/` | C++ + Java | 2 | 30 | 1 | 1 | 28 | 5 | 514 |
| `examples/duplicates/` | Java | 20 | 3720 | 760 | 620 | 2340 | 520 | 122740 |
| `examples/duplicates/1.java` | Java | 1 | 186 | 38 | 31 | 117 | 26 | 6137 |
| `examples/generated/` | C Header + C# | 2 | 708 | 62 | 197 | 449 | 56 | 23332 |
| `examples/minified/` | JavaScript + CSS | 15 | 224 | 0 | 45 | 179 | 48 | 1019014 |
| `examples/shared_extension/` | Coq + V + Verilog | 3 | 320 | 33 | 60 | 227 | 10 | 9141 |
| `main.go` | Go | 1 | 559 | 19 | 12 | 528 | 27 | 13470 |
| `README.md` | Markdown | 1 | 1434 | 407 | 0 | 1027 | 0 | 71457 |
| `processor/` | Go | 28 | 24663 | 1578 | 535 | 22550 | 1637 | 487228 |
| `processor/` + `scripts/` | Go + Go Template | 30 | 24840 | 1601 | 540 | 22699 | 1660 | 491177 |

Generated detail is C Header 235/1/67/167/14 and C# 473/61/130/282/42. Minified detail is JavaScript 11 files, 201/0/26/175/48, 796847 bytes, and CSS 4 files, 23/0/19/4/0, 222167 bytes. Generated/minified markers and exclusions change names/retention but never these base counts.

The full physical `examples/language/` corpus has 146 files in 143 language summaries and totals: 67,837 lines, 10,980 blank, 37,677 comment, 19,180 code, complexity 2,135, and 1,320,367 bytes. Its default COCOMO display is `$600,601`, `11.33 months`, `4.71`. Its three multi-file summaries are Clipper (2 files, 56/12/19/25/0, 1202 bytes), Cuda (2, 61/14/9/38/5, 1358), and Makefile (2, 2/0/0/2/0, 19); all other summaries have one file. GraphQL is the largest record: 61,602/9,958/36,963/14,681/1,533, 1,156,307 bytes. The detailed per-language/file rows needed for this corpus are in Spec 39.

The entire physical `examples/` scan (which includes the language corpus and all other canonical subtrees) has 230 files, 74,614 lines, 12,077 blank, 38,788 comment, 23,749 code, complexity 2,938, 2,551,003 bytes; default COCOMO is `$751,662`, `12.34 months`, `5.41`. These values are stable.

Applying `-z --no-min-gen --include-ext go,py --format wide` to that physical root excludes generated/minified records and yields exactly Python 14 files, 379 lines, 32 blank, 51 comment, 296 code, complexity 55, 10,925 bytes; and Go 3 files, 25 lines, 8 blank, 6 comment, 11 code, complexity 0, 223 bytes. The total is 17 files, 404 lines, 40 blank, 57 comment, 307 code, complexity 55, 11,148 bytes. Its summed wide complexity ratio is `169.08`, and its organic footer values are `$7,817`, `2.18 months`, and `0.32` people.

## Spec 39

### Canonical `examples/language` records

The following compact table is authoritative for the physical `examples/language` fixture corpus when present. Columns are `language|filename|lines|code|comment|blank|complexity|bytes`. A language may have multiple rows; its summary is their sum. File location is the supplied fixture-root path plus the filename. This table does not create or reserve any path.

<!-- REFERENCE_DATASET -->
```text
ABNF|abnf.abnf|20|16|0|4|8|645
AWK|nawk.awk|28|23|1|4|4|565
Alchemist|alchemist.crn|20|20|0|0|55|450
Algol 68|algol68.a68|31|25|0|6|6|1066
Alloy|barber_solutions.als|50|4|40|6|0|1238
Amber|Amber.ab|50|44|1|5|10|951
Apex|apex.apex|48|33|9|6|9|1257
ArkTs|ArkTs.ets|64|58|3|3|1|1551
Arturo|arturo.art|417|262|89|66|20|9981
Astro|astro.astro|12|12|0|0|0|371
BASH|.bash_login|1|1|0|0|0|11
Bean|bean.beancount|17|14|0|3|0|766
Bicep|bicep.bicep|50|37|5|8|4|1138
Bitbucket Pipeline|bitbucket-pipelines.yml|23|22|0|1|0|579
Blueprint|Blueprint.blp|12|5|5|2|0|171
Boo|boo.boo|1|1|0|0|0|29
Bosque|bosque.bsq|179|139|8|32|1|6900
Bru|bru.bru|20|17|0|3|0|331
C|c.c|54|44|1|9|11|993
C Header|cheader.h|6|4|0|2|0|130
C Shell|.cshrc|1|1|0|0|0|6
C#|Build.csx|150|128|0|22|7|4816
C++|cplusplus.cpp|9|7|1|1|0|189
C++ Header|cplusplusheader.hpp|39|32|1|6|8|900
C3|c3.c3|10|5|4|1|0|109
CMake|CMakeLists.txt|28|21|3|4|7|891
Cairo|cairo.cairo|28|25|0|3|4|439
Cangjie|main.cj|27|20|2|5|2|512
Cap'n Proto|capnproto.capnp|27|21|1|5|0|398
Chapel|chapel.chpl|14|12|2|0|0|343
Circom|circom.circom|34|23|7|4|2|672
Clipper|test.ch|22|8|9|5|0|560
Clipper|test.prg|34|17|10|7|0|642
Clojure|clojure.cljc|1|1|0|0|0|9
CloudFormation (JSON)|cloudformation.json|407|407|0|0|0|9241
CloudFormation (YAML)|cloudformation.yml|150|133|1|16|19|4697
Cuda|cuda.cu|43|28|7|8|3|927
Cuda|cudaheader.cuh|18|10|2|6|2|431
Cypher|cypher.cypher|28|10|12|6|10|868
D2|d2.d2|51|40|2|9|0|897
DAML|daml.daml|14|10|0|4|1|316
DM|test.dm|21|12|7|2|4|287
DOT|dot.gv|12|7|5|0|0|381
Docker ignore|.dockerignore|3|2|1|0|0|45
Dockerfile|Dockerfile|1|1|0|0|0|20
Elixir Template|elixirtemplate.eex|6|5|0|1|0|122
Elm|elm.elm|6|5|0|1|1|76
EmiT|emit.emit|23|13|1|9|5|389
F#|FSharp.fs|3|3|0|0|1|55
FSL|fsl.fsl|151|114|1|36|33|5379
FXML|fxml.fxml|9|8|0|1|0|208
Factor|factor.factor|23|18|1|4|2|554
Flow9|flow9.flow|21|12|6|3|5|447
Futhark|linear_solve.fut|29|16|10|3|2|945
Gemfile|Gemfile|1|1|0|0|0|17
Gleam|gleam.gleam|17|15|0|2|6|294
Go|go.go|19|7|6|6|0|165
Go+|goplus.gop|37|31|2|4|8|490
Godot Scene|godot.tscn|24|17|0|7|0|874
GraphQL|graphql.graphql|61602|14681|36963|9958|1533|1156307
Gremlin|gremlin.gremlin|31|18|9|4|0|978
Gwion|gwion.gw|35|28|0|7|7|596
HAML|haml.haml|14|10|1|3|0|245
HCL|hcl.hcl|134|76|45|13|0|4305
Hare|hare.ha|39|30|1|8|7|608
Haskell|haskell.hs|51|43|0|8|2|1479
INI|ini.ini|10|7|2|1|0|226
JCL|jcl.jcl|20|15|5|0|7|813
JSON5|kitchen-sink.json5|13|11|2|0|0|376
JSONC|jsonc.jsonc|9|3|6|0|0|96
Java|test.java|186|117|31|38|26|6137
JavaScript|javascript.js|24|20|0|4|0|402
Jsonnet|jsonnet.jsonnet|40|29|5|6|3|559
Korn Shell|.kshrc|1|1|0|0|0|6
Koto|koto.koto|17|13|0|4|4|315
LALRPOP|lalrpop.lalrpop|36|26|3|7|0|859
LLVM IR|llvmir.ll|5|4|1|0|0|119
License|license|0|0|0|0|0|0
LiveScript|livescript.ls|52|22|9|21|7|824
Lua|lua.lua|15|12|1|2|4|221
Luau|luau.luau|16|13|1|2|4|281
Luna|luna.luna|23|17|1|5|0|502
MLIR|MLIR.mlir|68|49|9|10|2|2503
Makefile|GNUMakefile|1|1|0|0|0|11
Makefile|makefile|1|1|0|0|0|8
Metal|metal.metal|401|123|45|233|1|8053
Mojo|mojo.mojo|30|21|3|6|5|923
Monkey C|HassIQApp.mc|74|62|0|12|12|1764
Moonbit|moonbit.mbt|16|13|3|0|4|410
Nature|nature.n|37|25|2|10|5|906
Nushell|docker.nu|22|18|2|2|2|514
OpenQASM|qasm.qasm|89|58|21|10|14|2684
OpenTofu|test.tofu|31|18|6|7|21|589
POML|POML.poml|11|8|1|2|0|567
Perl|perl.pl|8|6|1|1|2|140
Pkl|pkl.pkl|39|11|21|7|0|1340
Plain Text|plain.txt|1|1|0|0|0|24
PostScript|PostScript.ps|18|15|2|1|4|655
Python|python.py|8|5|1|2|3|139
Q#|qsharp.qs|31|23|2|6|5|750
R|rscript.r|12|8|1|3|2|188
RAML|raml.raml|48|46|1|1|0|1252
Racket|racket.rkt|107|91|2|14|33|3480
Rakefile|Rakefile|1|1|0|0|0|18
Rebol|rebol.reb|108|105|2|1|11|2939
Redscript|redscript.reds|84|51|24|9|12|2570
Rich Text Format|rtf.rtf|18|17|0|1|0|2086
Scallop|scallop.scl|24|14|6|4|5|762
Seed7|seed7.sd7|25|20|3|2|5|460
Shell|.tcshrc|1|1|0|0|0|7
Sieve|test.sieve|192|164|14|14|47|5941
Slang|slang.slang|15|8|5|2|0|274
Slint|slint.slint|72|65|2|5|9|3035
Smalltalk|smalltalk.cs.st|81|57|3|21|0|1615
Snakemake|snakefile.smk|67|44|10|13|0|1368
Stan|stan.stan|141|123|15|3|0|5682
Systemd|systemd.service|15|11|2|2|0|277
TOML|TOML.toml|40|28|3|9|0|553
TOON|TOON.toon|65|65|0|0|0|1731
TTCN-3|ttcn.ttcn|61|38|15|8|0|1361
Tact|tact.tact|20|12|4|4|2|380
Teal|teal.teal|15|9|6|0|2|213
Templ|component.templ|9|8|0|1|1|123
Tera|tera.tera|8|8|0|0|4|264
Terraform|test.tf|31|18|6|7|21|589
Textile|textile.textile|9|1|6|2|0|167
TypeScript|typescript.ts|9|7|0|2|1|130
TypeSpec|typespec.tsp|19|15|0|4|0|264
Typst|typst.typ|16|9|3|4|0|437
Up|up.up|24|10|12|2|3|869
Vala|vala.vala|20|18|1|1|3|507
Vim Script|vim.vim|20|15|2|3|1|358
Web Services Description Language|wsdl.wsdl|1|1|0|0|0|19
WebGPU Enhanced Shading Language|wesl.wesl|19|12|4|3|1|511
Windows Resource-Definition Script|version.rc|51|39|6|6|0|1888
Wren|syntax.wren|188|125|37|26|8|3544
XHTML|xhtml.xhtml|12|11|1|0|0|350
XML Schema|xmlschema.xsd|1|1|0|0|0|9
XMake|xmake.lua|38|25|2|11|5|740
YAML|yaml.yml|149|116|1|32|0|4685
Yarn|Sally.yarn|30|26|0|4|5|825
Zig|zig.zig|13|12|0|1|2|307
ZoKrates|zokrates.zok|16|9|5|2|2|261
Zsh|.zshrc|1|1|0|0|0|6
jq|jq.jq|26|23|1|2|5|878
wenyan|wenyan.wy|12|11|1|0|0|476
```

## Spec 40

### Other physical fixture records

The remaining physical `examples` fixtures have these authoritative summaries when present. Numeric groups are `Files/Lines/Blank/Comment/Code/Complexity/Bytes`; where multiple language rows are shown, totals are their sums. If a listed path is absent, Spec 38's ordinary missing-path behavior applies instead.

| suffix | records |
|---|---|
| `examples/oneline.py` | Python `1/1/0/0/1/0/11` |
| `examples/twolines.py` | Python `1/2/0/0/2/0/22` |
| `examples/nolines.py` | Python `1/0/0/0/0/0/0` |
| `examples/onenewline.py` | Python `1/1/1/0/0/0/1` |
| `examples/threenewline.py` | Python `1/3/3/0/0/0/3` |
| both oneline + twolines | Python `2/3/0/0/3/0/33` |
| `examples/issue564/` | Python `3/3/0/0/3/0` and Go `2/6/2/0/4/0`; total bytes 142 |
| `examples/issue246.py` | Python `1/18/2/13/3/1/634` |
| `examples/long/` | seven zero-byte/zero-line files: Extensible Stylesheet Language Transformations, Freemarker Template, Gherkin Specification, JavaServer Pages, Macromedia eXtensible Markup Language, Report Definition Language, Varnish Configuration |
| `examples/issue214/` | Markdown `3/0/0/0/0/0/0` |
| `examples/issue339/` | MATLAB `1/471/55/67/349/54` and Objective C `1/896/150/66/680/57`; total bytes 44,358 |
| `examples/issue345/filename.cc` | C++ `1/4/0/1/3/0/76` |
| `examples/minified/0-941d61979b9396d94f06.js` | JavaScript `1/2/0/0/2/0/18376` |
| `examples/countas/` normally | JavaServer Pages `1/1/0/0/1/0/50`; an unknown `.new` record is 1 line/1 code/54 bytes and appears only if mapped |
| `examples/remap/` | one known Java and one unknown marker file, each one line; combined physical size 191 bytes. Normally only Java is reported. Content remapping does not admit the unknown file; `remap-all` marker mapping changes the Java record to C Header, while `remap-unknown` leaves the Java record unchanged |
| `examples/issue120/` | Java `1/1/0/0/1/0` plus shebang-detected Perl `1/2/0/1/1/0`; total 62 bytes |

The physical `examples/generated/` filenames and per-file locations are stable but only their language summaries are significant. The physical `examples/minified/` by-file report has 15 records and includes `jquery.dataTables.min.js` with 166 lines, `bootstrap.min.js` with 7 lines, and `bootstrap.min.css` with 7 lines. The duplicate corpus filenames are stable Java copies and `1.java` is the representative retained by content deduplication.
