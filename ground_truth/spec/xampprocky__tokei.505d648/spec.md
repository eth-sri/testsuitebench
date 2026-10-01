# Specification for executable

The required artifact is a directly runnable command named `executable`. It is a Tokei-compatible source-code statistics program. All behavior, names, formats, and compatibility quirks needed by the implementation are defined below.

## Spec 1

The command accepts zero or more input paths and recursively measures recognized source files. With no positional input, it behaves as though the current working directory, `.`, were supplied. A positional input may be a regular file or a directory. Several inputs are scanned independently and merged; if the same directory is supplied twice, its files and counts are intentionally included twice.

Successful counting, help, version, and language-list operations exit with status 0. Command-line syntax/validation errors exit with status 2. A missing positional path or an unusable serialized input is a runtime error and exits with status 1, except for the diagnostic-only input cases described in Spec 21. Normal results go to stdout and diagnostics go to stderr. Unless a diagnostic is explicitly allowed, successful JSON output must contain no non-JSON text.

The program must handle UTF-8 paths and content, spaces and dashes in names, relative and absolute paths, `.`, `..`, and directory paths with a trailing slash. File report names use forward slashes and reflect the resolved input path sufficiently to retain the supplied directory hierarchy; absolute inputs yield absolute report names. No source repository, compiler-built helper, or other command is part of the required behavior: only `executable` is being specified.

## Spec 2

The accepted interface is:

- `-c, --columns N`
- repeatable `-e, --exclude PATTERN`
- `-f, --files`
- `-i, --input FILE_OR_STDIN`
- `--hidden`
- `-l, --languages`
- `--no-ignore`
- `--no-ignore-parent`
- `--no-ignore-dot`
- `--no-ignore-vcs`
- `-o, --output FORMAT`
- `--streaming MODE`
- `-s, --sort CRITERION`
- `-r, --rsort CRITERION`
- repeatable `-t, --types LIST`
- `-C, --compact`
- `-n, --num-format STYLE`
- repeatable `-v, --verbose`
- `-h, --help`
- `-V, --version`
- zero or more positional paths.

Long valued options accept both `--option value` and `--option=value`. Options may occur before or after paths. `--` ends option parsing, so a later dash-prefixed token is a path. Multiple positional paths are accepted. Boolean flags reject attached values such as `--files=1`. A missing option value, duplicate non-repeatable `--output`, unknown flag, invalid integer, invalid enum, or forbidden option combination is a status-2 error with empty stdout.

The only supported serialized output value is case-sensitive `json`. Streaming values are `simple` and `json`. Sort values are `files`, `lines`, `blanks`, `code`, and `comments`, compared case-insensitively. Number styles are `commas`, `dots`, `plain`, and `underscores`. `--sort` conflicts with `--rsort`; `--columns` conflicts with `--output`; and `--num-format` conflicts with `--output`.

An unknown flag error contains “unexpected argument”, “tip:”, and the suggestion `use '-- --FLAG'`. A missing value says “a value is required” and identifies the option. In particular, invoking the short input form as bare `-i` canonicalizes the option to its long name and emits exactly `error: a value is required for '--input <file_input>' but none was supplied`, a blank line, and `For more information, try '--help'.`, each text line newline-terminated. An invalid choice says “invalid value”, identifies the option, and lists possible values. For `-c -1`, `-1` is treated as an unexpected flag and the error suggests `use '-- -1'`; for `-c=-1`, it is an invalid value for `--columns`. Positive decimal widths such as 60, 80, 100, and 120 are valid. `-v` and `-vv`, as well as repeated `--verbose`, are valid.

Before `--`, `--help` and `--version` take precedence over ordinary positional-path validation, but precedence between those two informational flags is order-sensitive: the first one on the command line wins. Thus `ABSENT --help --version` prints help, while `ABSENT --version --help` prints exactly the version line from Spec 3; both exit 0 with empty stderr despite the nonexistent path. After `--`, `--help` is a literal path and consequently produces the runtime missing-path error.

## Spec 3

`--help` exits 0, writes nothing to stderr, and writes exactly the following UTF-8 text to stdout, including wrapping, blank lines, spacing, and the final newline. `-h` exits 0 and provides help containing at least the same `Usage:` and `Options:` sections.

~~~text
Count your code, quickly.
Support this project on GitHub Sponsors: https://github.com/sponsors/XAMPPRocky

Usage: executable [OPTIONS] [input]...

Arguments:
  [input]...  The path(s) to the file or directory to be counted. (default current directory)

Options:
  -c, --columns <columns>              Sets a strict column width of the output, only available for
                                       terminal output.
  -e, --exclude <exclude>              Ignore all files & directories matching the pattern.
  -f, --files                          Will print out statistics on individual files.
  -i, --input <file_input>             Gives statistics from a previous tokei run. Can be given a
                                       file path, or "stdin" to read from stdin.
      --hidden                         Count hidden files.
  -l, --languages                      Prints out supported languages and their extensions.
      --no-ignore                      Don't respect ignore files (.gitignore, .ignore, etc.). This
                                       implies --no-ignore-parent, --no-ignore-dot, and
                                       --no-ignore-vcs.
      --no-ignore-parent               Don't respect ignore files (.gitignore, .ignore, etc.) in
                                       parent directories.
      --no-ignore-dot                  Don't respect .ignore and .tokeignore files, including those
                                       in parent directories.
      --no-ignore-vcs                  Don't respect VCS ignore files (.gitignore, .hgignore, etc.)
                                       including those in parent directories.
  -o, --output <output>                Outputs Tokei in a specific format. Compile with additional
                                       features for more format support.
      --streaming <streaming>          prints the (language, path, lines, blanks, code, comments)
                                       records as simple lines or as Json for batch processing
                                       [possible values: simple, json]
  -s, --sort <sort>                    Sort languages based on column [possible values: files,
                                       lines, blanks, code, comments]
  -r, --rsort <rsort>                  Reverse sort languages based on column [possible values:
                                       files, lines, blanks, code, comments]
  -t, --types <types>                  Filters output by language type, separated by a comma. i.e.
                                       -t=Rust,Markdown
  -C, --compact                        Do not print statistics about embedded languages.
  -n, --num-format <num_format_style>  Format of printed numbers, i.e., plain (1234, default),
                                       commas (1,234), dots (1.234), or underscores (1_234). Cannot
                                       be used with --output. [possible values: commas, dots, plain,
                                       underscores]
  -v, --verbose...                     Set log output level:
                                                               1: to show unknown file extensions,
                                                               2: reserved for future debugging,
                                                               3: enable file level trace. Not
                                                               recommended on multiple files
  -h, --help                           Print help
  -V, --version                        Print version
~~~

`--version` exits 0, leaves stderr empty, and prints exactly:

~~~text
tokei 14.0.0 compiled with serialization support: json
~~~

with one terminating newline.

## Spec 4

Directory scanning is recursive and has no shallow recursion limit: structures at least 50 directories deep, flat directories of at least 500 files, and trees of at least 120 recognized files must work within ordinary test time. Direct file inputs are counted once. A recognized empty file still creates a report with all three counts zero. Unknown files do not create reports.

Symbolic links are not followed by default. In particular, a symlink to a file is not an additional report, a symlinked directory is not traversed, and circular directory links cannot loop. The binary-content conformance fixture is not skipped: a Python file containing exactly the five bytes `00 01 02 ff 00` creates a Python report with blanks 0, code 1, and comments 0 and contributes those values to the totals. A directory with no recognized files succeeds and returns/prints zero totals.

A missing path aborts the invocation at the first missing input, exits 1, writes no normal output, and emits exactly `Error: 'PATH' not found.` followed by a newline. If valid and missing paths are mixed, the invocation still fails for the missing one. Unknown file extensions and extensionless files without a recognized special name or shebang are silently ignored at normal verbosity. At verbosity level 1, an unknown extension such as `.xyz` produces a stderr warning containing both `WARN` and `Unknown extension: xyz`, but counting still succeeds.

## Spec 5

By default, names beginning with a dot—both files and directory components—are omitted. `--hidden` includes them. This setting is independent of ignore-file processing.

All `--exclude` occurrences are unioned: matching any one excludes the file or whole subtree. Patterns use gitignore-style path-glob semantics. A bare name such as `vendor`, `ignore_test`, or `level1` excludes that directory and descendants; a trailing slash such as `level1/` does likewise. `*.py`, `test*.rs`, and exact basenames match files at relevant levels. `**/tests/**` excludes recursively named test subtrees. Types and excludes both apply when combined. A 10,000-character nonmatching pattern must not fail. An invalid glob does not abort: for `[invalid(pattern`, continue scanning, exit 0, and write a stderr diagnostic containing exactly `error parsing glob '![invalid(pattern': unclosed character class; missing ']'`.

Within applicable repositories/directories, standard ignore matching is enabled by default for VCS ignore files such as `.gitignore` and for dot ignore files `.ignore` and `.tokeignore`. `--no-ignore-vcs` disables VCS ignore sources but leaves `.ignore` and `.tokeignore` active. `--no-ignore-dot` disables `.ignore` and `.tokeignore`. Using both disables both categories. `--no-ignore` disables all categories and implies the three narrower no-ignore flags. `--no-ignore-parent` prevents ignore rules inherited from directories above the scan root while allowing locally encountered rules.

## Spec 6

Language detection first uses a recognized special filename or the last/compound filename extension, case-insensitively; an available extension takes precedence over a contradictory shebang. Thus `.rs` and `.RS` are Rust; `.py`, `.Py`, and `.PY` are Python; `.cpp/.cc/.cxx` are C++; `.h` is C Header; `.hh/.hpp/.hxx` are C++ Header; `.js` is JavaScript while `.jsx` is JSX; `.ts` is TypeScript while `.tsx` is TSX; and a final `.rs` in `file.tar.gz.rs` wins. Compound ordinary names such as `test.spec.ts` remain TypeScript and `example.test.js` remain JavaScript. `Dockerfile`, `Makefile`, and the other extensionless special filenames in Spec 7 are recognized.

For an otherwise unrecognized extensionless text file, inspect the first line. The exact supported conformance shebangs are `#!/usr/bin/env python3` → Python, `#!/usr/bin/env bash` → BASH, `#!/bin/sh` → Shell, and `#!/usr/bin/env fish` → Fish. By contrast, `#!/usr/bin/python`, `#!/usr/bin/ruby`, `#!/usr/bin/env perl`, and `#!/usr/bin/env zsh` do not cause an extensionless file to be recognized and yield only zero Total when such a file is the sole input. This distinction is unchanged when those files are made executable; executable permission is not the discriminator.

The CLI `--types` is an inclusion filter. Split comma-separated entries without trimming whitespace, union repeated flags, and match otherwise exact canonical language names case-insensitively. Thus `Python,Rust` and `python,RUST` select both languages, but in `Python, RUST` only Python resolves, and the tokens in ` python, RUST ` do not resolve. Unknown or whitespace-padded requested types are ignored; if none resolve, the result contains only a zero Total. Types and excludes still both apply: in `--types ' python, RUST ' -t=javascript,unknown -e '*.js'`, JavaScript is the sole resolved type and is then excluded, so the result is only a zero Total. Configuration-file type handling differs as specified in Spec 20.

## Spec 7

`--languages` and `-l` print the supported-language table. The canonical language labels and extensions, including capitalization, special names, ordering, truncation ellipses, borders, spaces, and final newline, are exactly this output:

~~~text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ Language                              Extensions                     ┃
┃━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┃
┃ ABNF                                  abnf                           ┃
┃ AWK                                   awk                            ┃
┃ ABAP                                  abap                           ┃
┃ ActionScript                          as                             ┃
┃ Ada                                   ada, adb, ads, pad             ┃
┃ Agda                                  agda                           ┃
┃ Alex                                  x                              ┃
┃ Alloy                                 als                            ┃
┃ APL                                   apl, aplf, apls                ┃
┃ Arduino C++                           ino                            ┃
┃ Ark TypeScript                        ets                            ┃
┃ Arturo                                art                            ┃
┃ AsciiDoc                              adoc, asciidoc                 ┃
┃ ASN.1                                 asn1                           ┃
┃ ASP                                   asa, asp                       ┃
┃ ASP.NET                               asax, ascx, asmx, aspx, mas... ┃
┃ Assembly                              asm                            ┃
┃ GNU Style Assembly                    s                              ┃
┃ Astro                                 astro                          ┃
┃ ATS                                   dats, hats, sats, atxt         ┃
┃ AutoHotKey                            ahk                            ┃
┃ Autoconf                              in                             ┃
┃ Autoit                                au3                            ┃
┃ Automake                              am                             ┃
┃ AXAML                                 axaml                          ┃
┃ Ballerina                             bal                            ┃
┃ BASH                                  bash                           ┃
┃ Batch                                 bat, btm, cmd                  ┃
┃ Bazel                                 bzl, bazel, bzlmod             ┃
┃ Bean                                  bean, beancount                ┃
┃ Bicep                                 bicep, bicepparam              ┃
┃ Bitbake                               bb, bbclass, bbappend, inc     ┃
┃ BQN                                   bqn                            ┃
┃ BrightScript                          brs                            ┃
┃ C                                     c, ec, pgc                     ┃
┃ C3                                    c3                             ┃
┃ C Header                              h                              ┃
┃ CMake                                 cmake                          ┃
┃ C#                                    cs, csx                        ┃
┃ C Shell                               csh                            ┃
┃ Cabal                                 cabal                          ┃
┃ Cairo                                 cairo                          ┃
┃ Cangjie                               cj                             ┃
┃ Cassius                               cassius                        ┃
┃ Ceylon                                ceylon                         ┃
┃ Chapel                                chpl                           ┃
┃ CIL (SELinux)                         cil                            ┃
┃ Circom                                circom                         ┃
┃ Clojure                               clj                            ┃
┃ ClojureC                              cljc                           ┃
┃ ClojureScript                         cljs                           ┃
┃ COBOL                                 cob, cbl, ccp, cobol, cpy      ┃
┃ CodeQL                                ql, qll                        ┃
┃ CoffeeScript                          coffee, cjsx                   ┃
┃ Cogent                                cogent                         ┃
┃ ColdFusion                            cfm                            ┃
┃ ColdFusion CFScript                   cfc                            ┃
┃ Coq                                   v                              ┃
┃ C++                                   cc, cpp, cxx, c++, pcc, tpp    ┃
┃ C++ Header                            hh, hpp, hxx, inl, ipp         ┃
┃ C++ Module                            cppm, ixx, ccm, mpp, mxx, c... ┃
┃ Crystal                               cr                             ┃
┃ CSS                                   css                            ┃
┃ CUDA                                  cu                             ┃
┃ CUE                                   cue                            ┃
┃ Cython                                pyx, pxd, pxi                  ┃
┃ D                                     d                              ┃
┃ D2                                    d2                             ┃
┃ DAML                                  daml                           ┃
┃ Dart                                  dart                           ┃
┃ Device Tree                           dts, dtsi                      ┃
┃ Dhall                                 dhall                          ┃
┃ Djot                                  dj, djot                       ┃
┃ Dockerfile                            dockerfile, dockerignore       ┃
┃ .NET Resource                         resx                           ┃
┃ Dream Maker                           dm, dme                        ┃
┃ Dust.js                               dust                           ┃
┃ EdgeDB Schema Definition              esdl                           ┃
┃ Ebuild                                ebuild, eclass                 ┃
┃ EdgeQL                                edgeql                         ┃
┃ Edn                                   edn                            ┃
┃ 8th                                   8th                            ┃
┃ Emacs Lisp                            el                             ┃
┃ Elixir                                ex, exs                        ┃
┃ Elm                                   elm                            ┃
┃ Elvish                                elv                            ┃
┃ Emacs Dev Env                         ede                            ┃
┃ Emojicode                             emojic, 🍇​                     ┃
┃ Erlang                                erl, hrl                       ┃
┃ FEN                                   fen                            ┃
┃ F#                                    fs, fsi, fsx, fsscript         ┃
┃ Factor                                factor                         ┃
┃ Fennel                                fnl, fnlm                      ┃
┃ Fish                                  fish                           ┃
┃ FlatBuffers Schema                    fbs                            ┃
┃ Forge Config                          cfg                            ┃
┃ Forth                                 4th, forth, fr, frt, fth, f... ┃
┃ FORTRAN Legacy                        f, for, ftn, f77, pfo          ┃
┃ FORTRAN Modern                        f03, f08, f90, f95, fpp        ┃
┃ FreeMarker                            ftl, ftlh, ftlx                ┃
┃ F*                                    fst, fsti                      ┃
┃ Futhark                               fut                            ┃
┃ GDB Script                            gdb                            ┃
┃ GDScript                              gd                             ┃
┃ GDShader                              gdshader                       ┃
┃ Gherkin (Cucumber)                    feature                        ┃
┃ Gleam                                 gleam                          ┃
┃ Glimmer JS                            gjs                            ┃
┃ Glimmer TS                            gts                            ┃
┃ GLSL                                  vert, tesc, tese, geom, fra... ┃
┃ Gml                                   gml                            ┃
┃ Go                                    go                             ┃
┃ Go HTML                               gohtml                         ┃
┃ GraphQL                               gql, graphql                   ┃
┃ Groovy                                groovy, grt, gtpl, gvy         ┃
┃ Gwion                                 gw                             ┃
┃ Haml                                  haml                           ┃
┃ Hamlet                                hamlet                         ┃
┃ Handlebars                            hbs, handlebars                ┃
┃ Happy                                 y, ly                          ┃
┃ Haskell                               hs                             ┃
┃ Haxe                                  hx                             ┃
┃ HCL                                   hcl, tf, tfvars                ┃
┃ Headache                              ha                             ┃
┃ HEX                                   hex                            ┃
┃ Hex0                                  hex0                           ┃
┃ Hex1                                  hex1                           ┃
┃ Hex2                                  hex2                           ┃
┃ HICAD                                 MAC, mac                       ┃
┃ hledger                               hledger                        ┃
┃ HLSL                                  hlsl, fx, fxsub                ┃
┃ HolyC                                 HC, hc, ZC, zc                 ┃
┃ HTML                                  html, htm                      ┃
┃ Hy                                    hy                             ┃
┃ Idris                                 idr, lidr                      ┃
┃ INI                                   ini                            ┃
┃ Intel HEX                             ihex                           ┃
┃ Isabelle                              thy                            ┃
┃ JSLT                                  jslt                           ┃
┃ JAI                                   jai                            ┃
┃ Janet                                 janet                          ┃
┃ Java                                  java                           ┃
┃ JavaScript                            cjs, js, mjs                   ┃
┃ Jinja2                                j2, jinja                      ┃
┃ jq                                    jq                             ┃
┃ JSON                                  json                           ┃
┃ Jsonnet                               jsonnet, libsonnet             ┃
┃ JSX                                   jsx                            ┃
┃ Julia                                 jl                             ┃
┃ Julius                                julius                         ┃
┃ Jupyter Notebooks                     ipynb                          ┃
┃ Just                                  just                           ┃
┃ K                                     k                              ┃
┃ Kaem                                  kaem                           ┃
┃ Kakoune script                        kak                            ┃
┃ Koka                                  kk                             ┃
┃ Kotlin                                kt, kts                        ┃
┃ Korn shell                            ksh                            ┃
┃ KV Language                           kv                             ┃
┃ LLVM                                  ll                             ┃
┃ LALRPOP                               lalrpop                        ┃
┃ Lean                                  lean, hlean                    ┃
┃ LESS                                  less                           ┃
┃ Lex                                   l, lex                         ┃
┃ Lingua Franca                         lf                             ┃
┃ LD Script                             ld, lds                        ┃
┃ Liquid                                liquid                         ┃
┃ Common Lisp                           lisp, lsp, asd                 ┃
┃ LiveScript                            ls                             ┃
┃ Logtalk                               lgt, logtalk                   ┃
┃ LOLCODE                               lol                            ┃
┃ Lua                                   lua, luau                      ┃
┃ Lucius                                lucius                         ┃
┃ M1 Assembly                           m1                             ┃
┃ M4                                    m4                             ┃
┃ Madlang                               mad                            ┃
┃ Makefile                              makefile, mak, mk              ┃
┃ Markdown                              md, markdown                   ┃
┃ Max                                   maxpat                         ┃
┃ MDX                                   mdx                            ┃
┃ Menhir                                mll, mly, vy                   ┃
┃ Meson                                 <None>                         ┃
┃ Metal Shading Language                metal                          ┃
┃ Mint                                  mint                           ┃
┃ Mlatu                                 mlt                            ┃
┃ Modelica                              mo, mos                        ┃
┃ Module-Definition                     def                            ┃
┃ Mojo                                  mojo, 🔥                        ┃
┃ Monkey C                              mc                             ┃
┃ MoonBit                               mbt, mbti                      ┃
┃ MoonScript                            moon                           ┃
┃ MSBuild                               csproj, vbproj, fsproj, pro... ┃
┃ Mustache                              mustache                       ┃
┃ Nextflow                              nextflow, nf                   ┃
┃ Nim                                   nim                            ┃
┃ Nix                                   nix                            ┃
┃ Not Quite Perl                        nqp                            ┃
┃ NuGet Config                          <None>                         ┃
┃ Nushell                               nu                             ┃
┃ OCaml                                 ml, mli, re, rei               ┃
┃ Objective-C                           m                              ┃
┃ Objective-C++                         mm                             ┃
┃ Odin                                  odin                           ┃
┃ OpenCL                                cl, ocl                        ┃
┃ Open Policy Agent                     rego                           ┃
┃ OpenQASM                              qasm                           ┃
┃ OpenSCAD                              scad                           ┃
┃ OpenType Feature File                 fea                            ┃
┃ Org                                   org                            ┃
┃ Oz                                    oz                             ┃
┃ Lauterbach PRACTICE Script            cmm                            ┃
┃ PRQL                                  prql                           ┃
┃ PSL Assertion                         psl                            ┃
┃ Pacman's makepkg                      <None>                         ┃
┃ Pan                                   pan, tpl                       ┃
┃ Pascal                                pas                            ┃
┃ Perl                                  pl, pm                         ┃
┃ Pest                                  pest                           ┃
┃ Phix                                  e, exw                         ┃
┃ PHP                                   php                            ┃
┃ PlantUML                              puml                           ┃
┃ PO File                               po, pot                        ┃
┃ Poke                                  pk                             ┃
┃ Polly                                 polly                          ┃
┃ Pony                                  pony                           ┃
┃ PostCSS                               pcss, sss                      ┃
┃ PowerShell                            ps1, psm1, psd1, ps1xml, cd... ┃
┃ Processing                            pde                            ┃
┃ Prolog                                p, pro                         ┃
┃ Protocol Buffers                      proto                          ┃
┃ Pug                                   pug                            ┃
┃ Puppet                                pp                             ┃
┃ PureScript                            purs                           ┃
┃ Pyret                                 arr                            ┃
┃ Python                                py, pyw, pyi                   ┃
┃ Q                                     q                              ┃
┃ QCL                                   qcl                            ┃
┃ QML                                   qml                            ┃
┃ R                                     r                              ┃
┃ Rusty Object Notation                 ron                            ┃
┃ RPM Specfile                          spec                           ┃
┃ Racket                                rkt, scrbl                     ┃
┃ Rakefile                              rake                           ┃
┃ Raku                                  raku, rakumod, rakutest, pm... ┃
┃ Razor                                 cshtml, razor                  ┃
┃ ReScript                              res, resi                      ┃
┃ ReStructuredText                      rst                            ┃
┃ Redscript                             reds                           ┃
┃ Ren'Py                                rpy                            ┃
┃ Roc                                   roc                            ┃
┃ Ruby                                  rb                             ┃
┃ Ruby HTML                             rhtml, erb                     ┃
┃ Rust                                  rs                             ┃
┃ SIL                                   sil                            ┃
┃ SRecode Template                      srt                            ┃
┃ Sass                                  sass, scss                     ┃
┃ Scala                                 sc, scala                      ┃
┃ Scheme                                scm, ss                        ┃
┃ Scons                                 <None>                         ┃
┃ Shell                                 sh                             ┃
┃ ShaderLab                             shader, cginc                  ┃
┃ Slang                                 slang                          ┃
┃ Slint                                 slint                          ┃
┃ Smalltalk                             cs.st, pck.st                  ┃
┃ Standard ML (SML)                     sml                            ┃
┃ Snakemake                             smk, rules                     ┃
┃ Solidity                              sol                            ┃
┃ Specman e                             e                              ┃
┃ Spice Netlist                         ckt                            ┃
┃ SQF                                   sqf                            ┃
┃ SQL                                   sql                            ┃
┃ Stan                                  stan                           ┃
┃ Stata                                 do                             ┃
┃ Stratego/XT                           str                            ┃
┃ Stylus                                styl                           ┃
┃ Svelte                                svelte                         ┃
┃ SVG                                   svg                            ┃
┃ Swift                                 swift                          ┃
┃ SWIG                                  swg, i                         ┃
┃ SystemVerilog                         sv, svh                        ┃
┃ Tact                                  tact                           ┃
┃ TCL                                   tcl                            ┃
┃ Templ                                 templ, tmpl                    ┃
┃ Tera                                  tera                           ┃
┃ TeX                                   tex, sty                       ┃
┃ Plain Text                            text, txt                      ┃
┃ Thrift                                thrift                         ┃
┃ TOML                                  toml                           ┃
┃ TSX                                   tsx                            ┃
┃ TTCN-3                                ttcn, ttcn3, ttcnpp            ┃
┃ Twig                                  twig                           ┃
┃ TypeScript                            ts, mts, cts                   ┃
┃ Typst                                 typ                            ┃
┃ UMPL                                  umpl                           ┃
┃ Uiua                                  ua                             ┃
┃ Unison                                u                              ┃
┃ Unreal Markdown                       udn                            ┃
┃ Unreal Plugin                         uplugin                        ┃
┃ Unreal Project                        uproject                       ┃
┃ Unreal Script                         uc, uci, upkg                  ┃
┃ Unreal Shader                         usf                            ┃
┃ Unreal Shader Header                  ush                            ┃
┃ Ur/Web                                ur, urs                        ┃
┃ Ur/Web Project                        urp                            ┃
┃ VB6/VBA                               frm, bas, cls, ctl, dsr        ┃
┃ VBScript                              vbs                            ┃
┃ Vala                                  vala                           ┃
┃ Apache Velocity                       vm                             ┃
┃ Verilog                               vg, vh                         ┃
┃ Verilog Args File                     irunargs, xrunargs             ┃
┃ VHDL                                  vhd, vhdl                      ┃
┃ Vim Script                            vim                            ┃
┃ Virgil                                v3                             ┃
┃ Visual Basic                          vb                             ┃
┃ Visual Studio Project                 vcproj, vcxproj                ┃
┃ Visual Studio Solution                sln                            ┃
┃ Vue                                   vue                            ┃
┃ WebGPU Shader Language                wgsl                           ┃
┃ WebAssembly                           wat, wast                      ┃
┃ The WenYan Programming Language       wy                             ┃
┃ Wolfram                               nb, wl                         ┃
┃ XSL                                   xsl, xslt                      ┃
┃ XAML                                  xaml                           ┃
┃ Xcode Config                          xcconfig                       ┃
┃ XML                                   xml                            ┃
┃ Xtend                                 xtend                          ┃
┃ YAML                                  yaml, yml                      ┃
┃ ZenCode                               zs                             ┃
┃ Zig                                   zig                            ┃
┃ ZoKrates                              zok                            ┃
┃ Zsh                                   zsh                            ┃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

~~~

This table is also the authoritative detection mapping. `<None>` means detection is by a special filename rather than an extension. Where a displayed extension list ends in `...`, the named primary extensions shown elsewhere in this specification remain mandatory; the executable must in all cases recognize every conformance filename in Spec 10.

## Spec 8

For each recognized text file, compute mutually exclusive counts `code`, `comments`, and `blanks`. Their sum is the reported `lines`. A zero-byte file has zero lines, while the final nonempty line counts even without a trailing newline. LF and CRLF delimit lines; a lone CR is not a line delimiter. Consequently bytes `line1\nline2\r\nline3\rline4` comprise three code lines.

A blank line contains only whitespace recognized by the lexer after line-ending removal. This is not all Unicode whitespace: in a Python file containing `π = 'λ'`, `# café`, and a line consisting solely of U+3000 IDEOGRAPHIC SPACE, the U+3000-only line is code, so the exact result is blanks 0/code 2/comments 1. Unicode characters within ordinary code or comment text do not otherwise change that line's lexical classification. A comment line has comment material but no language code. If a physical line contains any code outside a comment, it is a code line and not additionally a comment line. Count lines, never statements. Strings and character literals protect comment-like delimiters inside them. Multiline strings/comments retain lexical state across physical lines. Files with 10 MB single lines, 500-character identifiers, escaped quotes/backslashes, and mixed LF/CRLF must work.

Aggregates sum the mutually exclusive per-file counts. Embedded-language lines are excluded from the parent’s own counts and are then added separately to the overall Total, as detailed later.

## Spec 9

Implement at least these lexical rules and compatibility results:

- C-family languages (C, C++, C/C++ headers, Java, JavaScript/JSX, TypeScript/TSX, Go, CSS, Kotlin, Scala, D, Swift, PHP where applicable) recognize `//` and nested-capable or ordinary `/* … */` according to the language. A line mixing code and a trailing or surrounding comment is code. C preprocessor lines are code. C/C++ quoted strings, escaped quotes, character literals, C backslash-continued strings, C++ `R"(…)"` raw strings, JavaScript multiline template strings, Rust raw strings with hash delimiters, and Kotlin/Scala triple strings protect comment syntax.
- C++ and D accept nested block comments for the tested inputs. Rust and Haskell accept arbitrarily nested `/*…*/` and `{-…-}`, respectively. An unclosed C block comment consumes the remainder as comments. A standalone `/**/` is one comment.
- Python uses `#` line comments; inline `#` on code does not make an extra comment. Triple-quoted and raw strings are code by default, including ordinary function docstrings.
- Rust regular `//` is a parent Rust comment. `///` and `//!` documentation lines are extracted as embedded Markdown rather than parent comments.
- HTML/XML recognize multiline `<!-- … -->`. SQL recognizes `--` and `/*…*/`. CSS recognizes `/*…*/`. Lua recognizes `--` and `--[[…]]`. Ruby recognizes `#` and line-oriented `=begin` through `=end`. Perl recognizes `#` plus POD from `=pod` through `=cut`. Shell/BASH recognize `#`; the shebang is a comment, an inline comment line is code, and in the tested heredoc the `# Not a comment` line is nevertheless classified as a comment while the other heredoc lines are code.
- FORTRAN Legacy recognizes `C` in column 1 and `!` as comments. Vim Script double-quote handling must follow the exact compatibility cases rather than treating every line-leading `"` as a comment. The existing six-line position-sensitive sample has code 5/comments 1, but the three-line file `" leading comment`, `let x = "value"`, `echo "Hello"` has blanks 0/code 3/comments 0: even its first, line-leading quote is code. Emacs Lisp recognizes semicolon comments. JSON has no comments. Markdown and Plain Text count ordinary nonblank content as comments and have zero parent code; in particular, a two-line `.txt` file with nonblank text has blanks 0/code 0/comments 2.
- PHP recognizes `//`, `#`, and block comments. JSX’s `{/* … */}` line inside JSX is treated compatibly with the tested case: the surrounding file has code 8/comments 1, with only the initial `//` contributing the parent comment.
- A three-line C fragment `int x = 1; /* comment`, `continues here`, `and here */ int y = 2;` has the compatibility result code 1/comments 2.

The following complete micro-cases further pin down classification: a five-line C string example containing `"// not a comment"` and `"/* also not */"` is code 5/comments 0; a three-line C continued string is code 3/comments 0; a five-line JavaScript template string plus print is code 5/comments 0; a seven-line C++ raw-string example is code 7/comments 0; and three consecutive newline bytes in an otherwise empty recognized file are three blanks.

For clarity, these are the exact parent-language assertions for the dynamically constructed lexical conformance cases. A dash means that count is not additionally constrained by that case; all supplied numeric values are exact.

~~~text
case/language | blanks | code | comments
C three-line block comment plus function | 0 | 3 | 3
C++ nested block comment plus declaration | - | 1 | 1
C strings containing comment delimiters | - | 5 | 0
C code mixed with comments on each line | - | 2 | 0
Python two functions with triple-quoted docstrings | 1 | 6 | 1
Rust doc comments plus regular comment | 2 | 3 | 1
C empty block comment plus declaration | - | 1 | 1
C unclosed block comment | - | 0 | 3
HTML single- and multi-line comments | - | 6 | 4
SQL line and block comments | - | 2 | 3
C preprocessor/function sample | - | 8 | 0
C whitespace-only middle line | 1 | 2 | -
Python raw and triple-quoted strings | - | 4 | 0
Java JavaDoc plus ordinary comment | - | 3 | 5
Shell shebang/comments/echo | - | 2 | 3
Shell tested heredoc | - | 5 | 3
C escaped quotes and backslashes | - | 3 | 0
C several statements on two lines | - | 2 | 0
C backslash-continued string | - | 3 | 0
Rust deeply nested block comment | - | 1 | 1
Ruby hash and begin/end comments | - | 4 | 6
FORTRAN Legacy column-one and bang comments | - | 3 | 3
C 500-character identifier | - | 1 | -
C comments-only file | - | 0 | 3
C code/block-comment/code compatibility fragment | - | 1 | 2
JavaScript multiline template string | - | 5 | 0
C two code lines separated by two blanks | 2 | 2 | -
C++ three comment syntaxes | - | 1 | 3
C generated 200-declaration sample | - | 203 | 1
C three comment blocks separated by blanks | 3 | 1 | 5
Go package/import/function and comments | 2 | 5 | 6
XML two comment blocks | - | 4 | 4
CSS properties and three comment lines | - | 4 | 3
Lua line and multiline comments | - | 2 | 3
Perl shebang/hash/POD sample | - | 2 | 6
Rust raw strings with hash delimiters | - | 5 | 0
C special-character literals | - | 4 | 0
TypeScript interface/function sample | 1 | 6 | 3
Kotlin block/line comments and triple string | - | 7 | 2
Haskell line and block comments | - | 3 | 3
Scala comments and triple string | - | 8 | 2
D deeply nested block comment | - | 3 | 1
Swift line/block/doc comments | 1 | 6 | 5
PHP all three comment styles | - | 5 | 4
JSX component with JSX comment syntax | - | 8 | 1
Vim Script six-line position-sensitive quote sample | - | 5 | 1
Vim Script three-line leading-quote compatibility sample | 0 | 3 | 0
Python U+3000-only-line compatibility sample | 0 | 2 | 1
Emacs Lisp comments/docstring | 1 | 3 | 2
JSON object | - | 5 | 0
empty C file | 0 | 0 | 0
C file containing three newline bytes | 3 | 0 | 0
C++ multiline raw string | - | 7 | 0
~~~

## Spec 10

The named conformance corpus below is authoritative. When one of these files is scanned alone, its primary language must be detected, exactly one top-level report must be produced, and the Total must equal the listed physical lines/code/comments/blanks. “Lines” is the sum of the other three. These data also disambiguate the lexical behavior of less common languages.

~~~text
path | lines | code | comments | blanks
tests/data/Daml.daml | 42 | 24 | 9 | 9
tests/data/Dockerfile | 17 | 7 | 3 | 7
tests/data/MSBuild.csproj | 12 | 10 | 1 | 1
tests/data/Makefile | 24 | 11 | 5 | 8
tests/data/Modelica.mo | 21 | 13 | 5 | 3
tests/data/NuGet.Config | 24 | 13 | 8 | 3
tests/data/PKGBUILD | 24 | 19 | 3 | 2
tests/data/Rakefile | 10 | 4 | 2 | 4
tests/data/SConstruct | 10 | 3 | 3 | 4
tests/data/Snakefile | 67 | 50 | 4 | 13
tests/data/Tera.tera | 42 | 26 | 11 | 5
tests/data/abnf.abnf | 11 | 3 | 5 | 3
tests/data/alloy.als | 18 | 10 | 3 | 5
tests/data/apl.apl | 10 | 3 | 3 | 4
tests/data/arduino.ino | 23 | 13 | 6 | 4
tests/data/arturo.art | 8 | 3 | 3 | 2
tests/data/asciidoc.adoc | 20 | 5 | 8 | 7
tests/data/asn1.asn1 | 34 | 16 | 11 | 7
tests/data/ats.dats | 42 | 25 | 9 | 8
tests/data/awk.awk | 5 | 1 | 3 | 1
tests/data/ballerina.bal | 40 | 29 | 6 | 5
tests/data/bazel.bzl | 18 | 13 | 3 | 2
tests/data/bean.bean | 27 | 13 | 6 | 8
tests/data/bicep.bicep | 50 | 35 | 8 | 7
tests/data/bitbake.bb | 23 | 13 | 5 | 5
tests/data/bqn.bqn | 10 | 3 | 3 | 4
tests/data/brightscript.brs | 26 | 10 | 13 | 3
tests/data/c.c | 50 | 33 | 8 | 9
tests/data/c3.c3 | 8 | 6 | 1 | 1
tests/data/cairo.cairo | 51 | 32 | 13 | 6
tests/data/cangjie.cj | 50 | 34 | 8 | 8
tests/data/chapel.chpl | 24 | 9 | 9 | 6
tests/data/cil.cil | 20 | 15 | 3 | 2
tests/data/circom.circom | 34 | 23 | 7 | 4
tests/data/clojure.clj | 19 | 13 | 3 | 3
tests/data/clojurec.cljc | 19 | 13 | 3 | 3
tests/data/clojurescript.cljs | 19 | 13 | 3 | 3
tests/data/cmake.cmake | 25 | 16 | 3 | 6
tests/data/codeql.ql | 40 | 17 | 15 | 8
tests/data/cogent.cogent | 7 | 2 | 2 | 3
tests/data/cpp.cpp | 46 | 37 | 3 | 6
tests/data/cppm.cppm | 46 | 37 | 3 | 6
tests/data/crystal.cr | 20 | 14 | 2 | 4
tests/data/csharp.cs | 26 | 14 | 9 | 3
tests/data/cuda.cu | 7 | 4 | 2 | 1
tests/data/cue.cue | 12 | 8 | 2 | 2
tests/data/cython.pyx | 29 | 21 | 3 | 5
tests/data/d.d | 8 | 5 | 1 | 2
tests/data/d2.d2 | 15 | 4 | 6 | 5
tests/data/dhall.dhall | 16 | 9 | 5 | 2
tests/data/dreammaker.dm | 17 | 7 | 6 | 4
tests/data/dust.dust | 10 | 2 | 5 | 3
tests/data/ebuild.ebuild | 16 | 9 | 2 | 5
tests/data/edgeql.edgeql | 28 | 21 | 3 | 4
tests/data/edn.edn | 11 | 6 | 2 | 3
tests/data/eight.8th | 22 | 9 | 8 | 5
tests/data/elvish.elv | 16 | 9 | 2 | 5
tests/data/emacs_dev_env.ede | 16 | 6 | 7 | 3
tests/data/emacs_lisp.el | 21 | 11 | 6 | 4
tests/data/emojicode.🍇 | 24 | 10 | 10 | 4
tests/data/esdl.esdl | 20 | 13 | 4 | 3
tests/data/example.umpl | 68 | 58 | 2 | 8
tests/data/factor.factor | 14 | 5 | 6 | 3
tests/data/fennel.fnl | 18 | 8 | 5 | 5
tests/data/flatbuffers.fbs | 34 | 21 | 6 | 7
tests/data/forgecfg.cfg | 79 | 20 | 40 | 19
tests/data/fsharp.fs | 15 | 6 | 5 | 4
tests/data/fstar.fst | 11 | 3 | 5 | 3
tests/data/ftl.ftl | 10 | 5 | 3 | 2
tests/data/futhark.fut | 8 | 2 | 3 | 3
tests/data/gas.S | 67 | 46 | 10 | 11
tests/data/gdb.gdb | 15 | 7 | 5 | 3
tests/data/gdshader.gdshader | 24 | 6 | 13 | 5
tests/data/gherkin.feature | 13 | 8 | 3 | 2
tests/data/gleam.gleam | 34 | 24 | 4 | 6
tests/data/glimmer_js.gjs | 27 | 18 | 6 | 3
tests/data/glimmer_ts.gts | 18 | 10 | 6 | 2
tests/data/gml.gml | 17 | 5 | 9 | 3
tests/data/go.go | 37 | 24 | 6 | 7
tests/data/gohtml.gohtml | 41 | 20 | 14 | 7
tests/data/graphql.gql | 89 | 71 | 3 | 15
tests/data/gwion.gw | 10 | 8 | 1 | 1
tests/data/haml.haml | 18 | 11 | 2 | 5
tests/data/hcl.tf | 22 | 11 | 7 | 4
tests/data/headache.ha | 13 | 9 | 3 | 1
tests/data/hex0.hex0 | 154 | 89 | 34 | 31
tests/data/hex1.hex1 | 589 | 387 | 91 | 111
tests/data/hex2.hex2 | 110 | 78 | 7 | 25
tests/data/hicad.mac | 10 | 4 | 3 | 3
tests/data/hledger.hledger | 18 | 6 | 10 | 2
tests/data/hpp.hpp | 21 | 11 | 5 | 5
tests/data/html.html | 46 | 23 | 19 | 4
tests/data/janet.janet | 17 | 12 | 3 | 2
tests/data/java.java | 37 | 23 | 5 | 9
tests/data/javascript.js | 33 | 14 | 12 | 7
tests/data/jinja2.j2 | 5 | 1 | 2 | 2
tests/data/jq.jq | 11 | 3 | 5 | 3
tests/data/jslt.jslt | 126 | 80 | 20 | 26
tests/data/jsonnet.jsonnet | 13 | 7 | 4 | 2
tests/data/justfile | 215 | 154 | 11 | 50
tests/data/k.k | 8 | 2 | 4 | 2
tests/data/kaem.kaem | 43 | 2 | 33 | 8
tests/data/kakoune_script.kak | 13 | 8 | 2 | 3
tests/data/koka.kk | 29 | 11 | 12 | 6
tests/data/ksh.ksh | 17 | 11 | 4 | 2
tests/data/kvlanguage.kv | 22 | 17 | 3 | 2
tests/data/lalrpop.lalrpop | 37 | 26 | 3 | 8
tests/data/linguafranca.lf | 36 | 16 | 9 | 11
tests/data/liquid.liquid | 24 | 19 | 1 | 4
tests/data/livescript.ls | 28 | 10 | 12 | 6
tests/data/llvm.ll | 21 | 17 | 1 | 3
tests/data/logtalk.lgt | 65 | 27 | 18 | 20
tests/data/lolcode.lol | 26 | 11 | 9 | 6
tests/data/m1.m1 | 280 | 197 | 47 | 36
tests/data/m4.m4 | 7 | 3 | 3 | 1
tests/data/menhir.mly | 47 | 31 | 7 | 9
tests/data/meson.build | 12 | 6 | 2 | 4
tests/data/metal.metal | 32 | 21 | 5 | 6
tests/data/mlatu.mlt | 22 | 14 | 3 | 5
tests/data/moduledef.def | 17 | 9 | 6 | 2
tests/data/mojo.mojo | 21 | 15 | 3 | 3
tests/data/monkeyc.mc | 69 | 41 | 18 | 10
tests/data/nextflow.nf | 18 | 10 | 5 | 3
tests/data/nqp.nqp | 24 | 14 | 8 | 2
tests/data/odin.odin | 29 | 17 | 7 | 5
tests/data/open_policy_agent.rego | 13 | 8 | 3 | 2
tests/data/openscad.scad | 34 | 15 | 16 | 3
tests/data/opentype.fea | 54 | 24 | 24 | 6
tests/data/org_mode.org | 13 | 7 | 2 | 4
tests/data/pan.pan | 21 | 11 | 4 | 6
tests/data/pcss.pcss | 14 | 6 | 5 | 3
tests/data/pest.pest | 9 | 4 | 3 | 2
tests/data/phix.e | 40 | 25 | 8 | 7
tests/data/plantuml.puml | 35 | 10 | 13 | 12
tests/data/pofile.po | 14 | 6 | 5 | 3
tests/data/pofile_pot.pot | 17 | 8 | 5 | 4
tests/data/poke.pk | 4 | 2 | 1 | 1
tests/data/pony.pony | 12 | 7 | 3 | 2
tests/data/postcss.sss | 27 | 18 | 4 | 5
tests/data/powershell.ps1 | 17 | 9 | 4 | 4
tests/data/pug.pug | 13 | 8 | 3 | 2
tests/data/puppet.pp | 18 | 14 | 3 | 1
tests/data/pyret.arr | 22 | 9 | 8 | 5
tests/data/python.py | 15 | 10 | 2 | 3
tests/data/q.q | 14 | 5 | 5 | 4
tests/data/qml.qml | 20 | 11 | 5 | 4
tests/data/racket.rkt | 40 | 15 | 14 | 11
tests/data/raku.raku | 49 | 37 | 6 | 6
tests/data/razor.cshtml | 55 | 35 | 15 | 5
tests/data/razorcomponent.razor | 45 | 16 | 21 | 8
tests/data/redscript.reds | 75 | 47 | 20 | 8
tests/data/renpy.rpy | 32 | 8 | 9 | 15
tests/data/roc.roc | 36 | 18 | 10 | 8
tests/data/ron.ron | 157 | 137 | 7 | 13
tests/data/rpmspec.spec | 42 | 22 | 4 | 16
tests/data/ruby.rb | 20 | 9 | 8 | 3
tests/data/ruby_env | 11 | 3 | 6 | 2
tests/data/ruby_html.erb | 34 | 21 | 8 | 5
tests/data/rust.rs | 48 | 36 | 6 | 6
tests/data/scheme.scm | 26 | 14 | 4 | 8
tests/data/shaderlab.shader | 43 | 31 | 8 | 4
tests/data/slang.slang | 15 | 8 | 5 | 2
tests/data/slint.slint | 26 | 21 | 2 | 3
tests/data/solidity.sol | 14 | 6 | 7 | 1
tests/data/sql.sql | 12 | 4 | 5 | 3
tests/data/srecode.srt | 37 | 23 | 2 | 12
tests/data/stan.stan | 142 | 123 | 17 | 2
tests/data/stata.do | 16 | 6 | 7 | 3
tests/data/stratego.str | 24 | 12 | 6 | 6
tests/data/stylus.styl | 20 | 10 | 5 | 5
tests/data/svelte.svelte | 41 | 15 | 21 | 5
tests/data/swift.swift | 24 | 6 | 14 | 4
tests/data/swig.i | 16 | 8 | 5 | 3
tests/data/tact.tact | 20 | 12 | 4 | 4
tests/data/templ.templ | 24 | 13 | 8 | 3
tests/data/thrift.thrift | 38 | 29 | 2 | 7
tests/data/tsx.tsx | 9 | 5 | 3 | 1
tests/data/ttcn.ttcn3 | 16 | 7 | 6 | 3
tests/data/twig.twig | 16 | 14 | 1 | 1
tests/data/typescript.ts | 33 | 20 | 10 | 3
tests/data/typst.typ | 16 | 9 | 3 | 4
tests/data/uiua.ua | 9 | 5 | 3 | 1
tests/data/unison.u | 16 | 6 | 8 | 2
tests/data/urweb.ur | 14 | 8 | 4 | 2
tests/data/urweb_urp.urp | 3 | 1 | 1 | 1
tests/data/urweb_urs.urs | 3 | 1 | 1 | 1
tests/data/vb6_bas.bas | 12 | 6 | 3 | 3
tests/data/vb6_cls.cls | 22 | 17 | 3 | 2
tests/data/vb6_frm.frm | 34 | 29 | 3 | 2
tests/data/vbscript.vbs | 8 | 3 | 3 | 2
tests/data/velocity.vm | 11 | 4 | 5 | 2
tests/data/vhdl.vhd | 34 | 20 | 7 | 7
tests/data/visualbasic.vb | 7 | 4 | 2 | 1
tests/data/vqe.qasm | 89 | 58 | 21 | 10
tests/data/vue.vue | 36 | 24 | 9 | 3
tests/data/webassembly.wat | 10 | 8 | 1 | 1
tests/data/wenyan.wy | 141 | 107 | 1 | 33
tests/data/wgsl.wgsl | 13 | 10 | 2 | 1
tests/data/xsl.xsl | 13 | 7 | 4 | 2
tests/data/xtend.xtend | 23 | 13 | 4 | 6
tests/data/yaml.yaml | 34 | 29 | 3 | 2
tests/data/zencode.zs | 21 | 9 | 7 | 5
tests/data/zig.zig | 11 | 5 | 3 | 3
tests/data/zokrates.zok | 11 | 3 | 6 | 2
tests/embedding/file_triggeringprincipal_frame_1.html | 27 | 20 | 5 | 2
~~~

## Spec 11

For `-o json` or `--output json`, stdout is one compact JSON object. It maps each top-level canonical language name to a language object and always includes `"Total"`, even when empty. Every language object has exactly these conceptual fields:

~~~text
{
  "blanks": nonnegative integer,
  "code": nonnegative integer,
  "comments": nonnegative integer,
  "reports": [Report, ...],
  "children": { embeddedLanguage: [Report, ...], ... },
  "inaccurate": false
}
Report = {
  "stats": {
    "blanks": nonnegative integer,
    "code": nonnegative integer,
    "comments": nonnegative integer,
    "blobs": { embeddedLanguage: Stats, ... }
  },
  "name": "path/to/file"
}
Stats = {
  "blanks": nonnegative integer,
  "code": nonnegative integer,
  "comments": nonnegative integer,
  "blobs": { ... }
}
~~~

The serialized field order for a language is `blanks, code, comments, reports, children, inaccurate`; for an ordinary report it is `stats, name`; and for nonstreaming report stats it is `blanks, code, comments, blobs`. JSON booleans and numbers are genuine JSON types. Output is not pretty-printed, and nonstreaming JSON stdout ends immediately after the closing `}` with no terminating newline.

Top-level language `reports` are populated in JSON whether or not `--files` is supplied. A top-level language’s scalar counts are sums of only its parent-language portions. Its `children` maps each embedded language to the reports containing that embedded contribution. The report’s `stats.blobs` holds the same per-file embedded values. Empty embedded blocks do not create a blob or child. `Total.reports` is always `[]`; `Total.children` maps every top-level language to its full report list. `Total` scalar counts sum parent and all recursively embedded statistics. `--compact` changes table presentation only; it does not remove JSON reports, children, or blobs.

For a single file at `/p/sample.rs` with blanks 1/code 4/comments 3 and no embeddings, the exact structural shape is:

~~~json
{"Rust":{"blanks":1,"code":4,"comments":3,"reports":[{"stats":{"blanks":1,"code":4,"comments":3,"blobs":{}},"name":"/p/sample.rs"}],"children":{},"inaccurate":false},"Total":{"blanks":1,"code":4,"comments":3,"reports":[],"children":{"Rust":[{"stats":{"blanks":1,"code":4,"comments":3,"blobs":{}},"name":"/p/sample.rs"}]},"inaccurate":false}}
~~~

## Spec 12

Aggregation occurs after all paths and filters. Reports remain separate, even for duplicate/overlapping roots. Top-level languages are normally emitted alphabetically by canonical name. The Total top-level file count used by the terminal table is the number of top-level source reports; embedded child reports do not increase it.

For each displayed language, `Lines = code + comments + blanks` using that language’s own scalar counts. If it has embedded children, the table also displays each child and an indented `(Total)` subtotal that includes the parent and children. The final overall Total similarly includes all embedded counts. A top-level HTML file with parent stats 12 code and children CSS 1 code and JavaScript 1 code therefore has HTML’s JSON scalar code 12 but overall Total code 14.

An empty scan produces precisely the zero Total JSON shape:

~~~json
{"Total":{"blanks":0,"code":0,"comments":0,"reports":[],"children":{},"inaccurate":false}}
~~~

## Spec 13

Default output is a Unicode table. Its columns are in the exact order Language, Files, Lines, Code, Comments, Blanks. The minimum/default border width is 81 Unicode characters. At width 81, rows follow the formatting template consisting of one leading space, a left-aligned 20-character language field, a right-aligned 7-character Files field, then four right-aligned 13-character fields for Lines, Code, Comments, and Blanks. Content rows are 80 characters; heavy borders are 81 `━` characters and thin section separators are 81 `─` characters. Output terminates with a newline.

A one-file Rust result with lines 6/code 4/comments 2/blanks 0 is exactly:

~~~text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Language              Files        Lines         Code     Comments       Blanks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Rust                      1            6            4            2            0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Total                     1            6            4            2            0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
~~~

An empty table retains the header and places adjacent heavy borders around the zero Total:

~~~text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Language              Files        Lines         Code     Comments       Blanks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Total                     0            0            0            0            0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
~~~

Top-level rows without requested sorting default to canonical alphabetical order. A recognized top-level language whose aggregate lines, code, comments, and blanks are all zero is suppressed from the terminal table, even though its report still contributes to the final Total file count. Thus a sole empty Rust file produces no Rust row but produces a Total row with Files 1 and all four line/statistic values zero. Embedded child rows use label `|- NAME`; their Files value is the number of contributing reports. A parent-plus-children subtotal uses `(Total)`, leaves Files blank, and sums the parent and children. Thin separators delimit expanded language/file-detail groups. The final `Total` row occurs exactly once, after every language, between heavy borders.

## Spec 14

With `--files` or `-f`, terminal output adds each top-level report beneath its language after a thin separator. Each file row leaves Files blank and shows lines/code/comments/blanks. Its left field is the report path. If too long, retain the rightmost characters that fit and replace the discarded prefix with `|`; at default width the path field is 27 characters and this yields examples such as ` |s/test_cli_utils/sample.rs` and ` |ith_constrained_columns.rs` before the numeric columns.

For a file that has embeddings, expanded output first shows a line containing its full/truncated path, then `|- Parent` and `|- Child` breakdown rows as applicable, followed by the ordinary file row. With `--files --compact`, list top-level file rows but suppress embedded breakdown rows.

With `--compact` or `-C`, terminal output includes only top-level language rows and final Total: no `|-` child rows and no `(Total)` subtotals. Top-level rows continue to show only parent-language scalar statistics, while the final Total still includes embedded statistics. For example, a Vue file with parent blanks 2/code 6 and embedded code totaling 12 prints a Vue row of lines 8/code 6 and a final Total of lines 20/code 18/blanks 2.

## Spec 15

`--num-format` affects numeric cells in aggregate language, embedded subtotal, and final Total rows, but file-detail rows always retain ungrouped plain decimal digits. `plain` (the default) has no grouping anywhere; `commas`, `dots`, and `underscores` group aggregate decimal digits in threes from the right. Values below 1000 and zero are unchanged. Thus an aggregate 1050 becomes `1,050`, `1.050`, or `1_050` under the three grouped styles while the corresponding `--files` detail row remains `1050`; 7000 becomes aggregate `7.000` with dots, and 5000 becomes aggregate `5_000` with underscores. It cannot be combined with serialized `--output`.

`--columns N` controls table width but never shrinks below 81. Values 60 and 80 therefore produce the same 81-character layout as default. At 120, every heavy/thin separator is exactly 120 characters and content/header rows are 119 characters. Width beyond the minimum is added to the language/path area; numeric field widths remain fixed. In general for effective border width W = max(81,N), a language row is one leading space, a left-aligned field of width W−61, Files right-aligned in 7, then the other four numbers right-aligned in 13 each. A file-detail row omits Files, so its path field spans both first fields and has width W−54, followed by the four 13-character numeric fields. Long report paths are left-truncated to that wider path field as in Spec 14.

## Spec 16

Without sort flags, languages use stable canonical alphabetical order. `--sort criterion` orders top-level languages from the greatest criterion value to the least. `--rsort criterion` orders them from the least criterion value to the greatest, so the greatest value is last rather than first; among equal values it uses reverse canonical order. Criteria are top-level report count for `files`, `code+comments+blanks` for `lines`, and the corresponding scalar for the other three. The final Total never participates and stays last. Sorting applies after combining all roots and still applies with `--files` or `--compact`.

Ties preserve the default order for `--sort`; the reverse canonical tie ordering for `--rsort` is already part of its least-to-greatest ordering above. For languages HTML(15 lines,12 code,3 comments,0 blanks), JavaScript(5,3,2,0), Python(25,18,3,4), Rust(13,8,3,2), exact orders are:

- sort lines/code: Python, HTML, Rust, JavaScript
- sort comments: HTML, Python, Rust, JavaScript
- sort blanks: Python, Rust, HTML, JavaScript
- reverse-sort lines/code: JavaScript, Rust, HTML, Python
- reverse-sort comments: JavaScript, Rust, Python, HTML
- reverse-sort blanks: JavaScript, HTML, Rust, Python.

For file-counts Python 3, Rust 2, JavaScript 1, sort order is Python/Rust/JavaScript and reverse-sort is JavaScript/Rust/Python. When file-detail rows are shown, the same criterion also orders reports within a language; for example, a configured `sort = "lines"` displays three Python files of 3, 2, and 1 lines as large/medium/small. Sorting does not alter counts or JSON structure; if object-key insertion order is observed, it must remain deterministic.

## Spec 17

`--streaming simple` produces one record per recognized top-level file rather than an aggregate table. It begins with these exact two layout lines:

~~~text
# language                                        path                                          lines         code       comments      blanks   
########## ################################################################################ ############ ############ ############ ############
~~~

Each later line contains, in that order, the canonical language, report path, total parent-file lines, code, comments, and blanks, in fixed right-aligned columns compatible with:

~~~text
         C /workspace/eval/test_resources/test_cli_basic/multi_lang/code.c                             8            5            2            1
    Python /workspace/eval/test_resources/test_cli_basic/multi_lang/code.py                            7            4            2            1
~~~

Paths in tested simple-stream inputs have no spaces. There is a terminating newline.

`--streaming json` emits one compact JSON object per recognized file, one per line, with exactly top-level keys `language` and `stats`. The latter has exactly `name` and `stats`; the inner object has exactly `blanks`, `blobs`, `code`, and `comments` in that serialized order. Example:

~~~json
{"language":"C","stats":{"name":"/p/code.c","stats":{"blanks":1,"blobs":{},"code":5,"comments":2}}}
~~~

All values have the types described in Spec 11. Multiple files produce multiple parseable lines. `--compact` does not change this JSON record schema.

## Spec 18

HTML-family embedding is line-oriented:

- In HTML and Ruby HTML, a complete one-line opening `<style ...>` begins CSS and a complete one-line opening `<script ...>` begins JavaScript; the corresponding closing tag ends it. Multiple blocks of the same language aggregate into one per-file blob.
- `<script type="text/javascript">`, `<script type="module">`, and untyped script are JavaScript. `type="application/json"` is JSON. A style `lang="scss"` remains CSS for compatibility.
- Opening tags split across multiple lines are not recognized as embeddings and the whole construct remains parent HTML. Inline `style=` and event-handler attributes are not extracted.
- Tags inside an HTML `<!--…-->` comment are not extracted. Their lines are parent HTML comments.
- An empty embedded block creates no child. A block containing only blank interior lines also creates no child; those blanks remain attributed to the parent. Once a block has nonblank language content, its blank interior lines belong to that child.
- Parent HTML counts its own tags/markup but excludes extracted interior source lines. Embedded language lexical rules apply inside each block.

Required exact per-file parent/blob results include:

~~~text
case | parent blanks/code/comments | embedded blobs | overall Total blanks/code/comments
basic HTML | 0/12/0 | CSS 0/1/0; JavaScript 0/1/0 | 0/14/0
multiple HTML blocks | 0/17/0 | CSS 0/6/0; JavaScript 0/6/0 | 0/29/0
HTML embedded comments | 0/11/0 | CSS 0/3/2; JavaScript 0/3/3 | 0/17/5
empty HTML blocks | 0/12/0 | none | 0/12/0
blank-only HTML blocks | 2/9/0 | none | 2/9/0
HTML blanks in nonempty blocks | 0/9/0 | CSS 1/6/0; JavaScript 1/6/0 | 2/21/0
commented-out HTML blocks | 0/10/10 | active CSS 0/1/0 only | 0/11/10
typed HTML scripts | 0/9/0 | JavaScript 0/2/0 | 0/11/0
style lang attribute | 0/7/0 | CSS 0/2/0 | 0/9/0
inline-only HTML | 0/10/0 | none | 0/10/0
multiline opening tags | 0/14/0 | none | 0/14/0
mixed script types | 0/11/0 | JavaScript 0/2/0; JSON 0/1/0 | 0/14/0
large HTML blocks | 0/14/0 | CSS 3/18/1; JavaScript 3/18/1 | 6/50/2
Ruby HTML page | 0/13/0 | CSS 0/1/0; JavaScript 0/2/0 | 0/16/0
~~~

## Spec 19

Markdown fenced blocks are embeddings only when the opening triple-backtick fence names a recognized language. The fence lines and ordinary Markdown text remain Markdown comments, blank Markdown lines remain blanks, and embedded body lines are removed from parent counting and lexed as their named language. An unlabeled fence creates no child and all nonblank content stays Markdown comments. Indented code without a language is not embedded. Multiple fences and multiple languages aggregate. An unclosed named fence consumes the rest of the file, including apparent later fences, into the first child.

Vue files are top-level Vue. Extract complete `<template>`, `<script>`, and `<style>` sections as HTML, JavaScript, and CSS. Compatibility aliases map Vue `lang="ts"` script to JavaScript and `lang="scss"` style to CSS; `<template lang="pug">` maps to Pug instead of HTML. Svelte extracts JavaScript script blocks and CSS style blocks while markup remains parent Svelte. Lingua Franca extracts target C content between `{=` and `=}`. Rust documentation comment text becomes Markdown as described in Spec 9.

Required exact cases are:

~~~text
case | parent blanks/code/comments | child blanks/code/comments | overall Total blanks/code/comments
Markdown Python+JavaScript document | 5/0/9 | Python 0/3/0; JavaScript 0/3/0 | 5/6/9
Markdown Rust fence plus unlabeled indent | 5/0/8 | Rust 0/3/0 | 5/3/8
Markdown unlabeled fence | 2/0/6 | none | 2/0/6
Markdown unclosed Python fence | 3/0/8 | Python 2/4/0 | 5/4/8
Markdown tutorial | 12/0/17 | Python 0/4/0; JavaScript 0/6/0; Rust 0/7/0; BASH 0/1/1 | 12/18/18
Vue component | 2/6/0 | HTML 0/3/0; JavaScript 0/6/0; CSS 0/3/0 | 2/18/0
Vue explicit html/ts/scss | 2/6/0 | HTML 0/3/0; JavaScript 0/7/0; CSS 0/4/0 | 2/20/0
Vue Pug template | 1/4/0 | Pug 0/2/0; JavaScript 0/3/0 | 1/9/0
Svelte component | 2/7/0 | JavaScript 0/4/0; CSS 0/4/0 | 2/15/0
Lingua Franca with C | 3/9/0 | C 0/2/0 | 3/11/0
~~~

Across two HTML files with parent code 9 apiece and CSS/JavaScript code 1 apiece, HTML aggregates to code 18 and each HTML child list has two reports. If the same directory also contains Markdown parent blanks 1/comments 3 with Python child code 2, overall Total is blanks 1/code 24/comments 3.

## Spec 20

At startup, load at most one TOML configuration from conventional locations. The current working directory has highest precedence over the user home and `$XDG_CONFIG_HOME`; within the same directory `tokei.toml` takes precedence over `.tokeirc`. The XDG form is `$XDG_CONFIG_HOME/tokei.toml`. A malformed TOML file is silently ignored and must not make the run fail.

If the environment variable `NO_COLOR` is set (in particular to `1`), terminal operation still succeeds without ANSI color escapes, and JSON remains pure valid JSON. No output mode may inject color control bytes into serialized data.

Recognized keys are `columns` (integer), `sort` (one of the criteria), `types` (array of canonical language strings), `hidden` (boolean), `no_ignore`, `no_ignore_parent`, `no_ignore_vcs`, `no_ignore_dot` (booleans), and `treat_doc_strings_as_comments` (boolean; it must at least be accepted without error). Their meanings mirror the CLI options. Several options can coexist. The config file itself is not specially excluded from a directory scan; for example, a one-line `tokei.toml` alongside a one-line Python file produces one TOML code line plus one Python code line.

Config `types` is deserialized case-sensitively. Valid entries such as `["Python"]` filter accordingly; multiple valid entries union. An empty array filters out every language. If a language spelling is invalid, as in `["python"]`, configuration parsing is treated as invalid and the whole config is ignored, so the unfiltered scan proceeds. Current-directory `tokei.toml` overrides both current `.tokeirc` and lower-precedence configs rather than merging their type filters.

## Spec 21

The `--input` option accepts a filesystem path or the literal `stdin`. Its compatibility behavior is deliberately not a normal merge implementation: valid prior JSON is accepted, but does not replace or add to the filesystem scan. Positional paths are scanned normally; if there are none, the ordinary default current-directory scan still occurs. Thus `--input valid.json -o json` has the same blank/code/comment totals as scanning `.` from that working directory, irrespective of the valid file’s stored totals. A valid JSON document supplied through `--input stdin` is likewise accepted and the normal/default scan proceeds.

Before continuing, the input source is nevertheless opened/read and validated enough to reject missing, empty, or malformed data. Such a failure writes stderr containing `Failed to parse input file: VALUE` and `This version of tokei was compiled without serialization support`. A malformed existing input used without other mode-specific compatibility handling exits 1 and contains `Failed to parse input file`. Empty stdin is named `stdin` in the message. No crash or traceback is allowed.

## Spec 22

The exact clap-style diagnostics required for common cases are:

~~~text
error: invalid value 'invalid' for '--sort <sort>'
  [possible values: files, lines, blanks, code, comments]

For more information, try '--help'.
~~~

~~~text
error: the argument '--sort <sort>' cannot be used with '--rsort <rsort>'

Usage: executable --sort <sort> [input]...

For more information, try '--help'.
~~~

~~~text
error: the argument '--columns <columns>' cannot be used with '--output <output>'

Usage: executable --columns <columns> [input]...

For more information, try '--help'.
~~~

~~~text
error: the argument '--num-format <num_format_style>' cannot be used with '--output <output>'

Usage: executable --num-format <num_format_style> [input]...

For more information, try '--help'.
~~~

Conflict diagnostics preserve the first conflicting option encountered, and a supplied positional path appears as required in the usage synopsis. Consequently, for `--output json --num-format commas INPUT`, the exact diagnostic instead is:

~~~text
error: the argument '--output <output>' cannot be used with '--num-format <num_format_style>'

Usage: executable --output <output> <input>...

For more information, try '--help'.
~~~

An invalid number style uses:

~~~text
error: invalid value 'invalid' for '--num-format <num_format_style>'
  [possible values: commas, dots, plain, underscores]

For more information, try '--help'.
~~~

For unsupported serialized format `xml`, stderr contains `error: invalid value 'xml' for '--output <output>': "xml" is not a supported serialization format`. Invalid streaming and sort values similarly identify the option and possible values. These parser failures have status 2 and empty stdout.

The executable must never hang or crash on empty trees, all-excluded trees, unknown extensions, invalid globs, symlink loops, Unicode, CRLF/mixed endings, 50-level nesting, 500 files in one directory, 120-file trees, 10 MB lines, or binary/NUL-containing inputs. For every successful scan, table, compact, JSON, files, sorting, number-formatting, and streaming modes must be mutually consistent about the underlying counts.
