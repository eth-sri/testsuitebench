# Clarified specification for `executable`

The required artifact is one directly runnable program named exactly `executable`. It is a command-line syntax highlighter compatible with the Chroma v2 behavior snapshot labeled `8d04def94bbccd114a84a02ff2df5efa06bd49f3`; that label disambiguates the fixed corpus, but no external document is normative. The observable contract is given here. Unless a section says otherwise, success is exit status 0, normal formatted data goes only to standard output, and diagnostics go only to standard error. Output is byte-sensitive: preserve the shown whitespace, newlines, escaping, token boundaries, and ANSI sequences.

## Spec 1

Invocation has the form `executable [<files> ...] [flags]`. With one or more file operands, validate that every operand names an existing regular file during argument parsing, then process the files from left to right. Each file is lexed independently and each formatter result is written immediately after the preceding result, with no filename heading or separator. Consequently terminal results concatenate, JSON produces one complete array after another, and standalone HTML produces one complete HTML document after another.

With no file operands, consume standard input through EOF. Do not print prompts. Empty stdin and an empty file produce no bytes with terminal/noop formatting; JSON produces an empty array in the layout defined below; HTML still produces a structurally valid empty code block. `--check` is intentionally ignored for stdin and stdin is formatted normally. With file operands, `--check` replaces formatting as described in Spec 15.

Read complete inputs without scanner line-length limits. Inputs in the tens of megabytes, a 100,000-character line, 1,000 nested delimiters, 100 file operands, and 10,000 stdin lines must complete within ordinary command timeouts without truncation, wrapping, recursion failure, or quadratic behavior. `--unbuffered` switches from a 16,384-byte buffered writer to direct writes; it must not change final bytes or status.

## Spec 2

The accepted public flags, aliases, grouping, defaults, and exact `--help` stdout are:

```text
Usage: executable [<files> ...] [flags]

Chroma is a general purpose syntax highlighting library and corresponding
command, for Go.

Arguments:
  [<files> ...]    Files to highlight.

Flags:
  -h, --help               Show context-sensitive help.
      --version            Show version.
      --list               List lexers, styles and formatters.
      --unbuffered         Do not buffer output.
      --trace              Trace lexer states as they are traversed.
      --check              Do not format, check for tokenisation errors instead.
      --filename=STRING    Filename to use for selecting a lexer when reading
                           from stdin.
      --fail               Exit silently with status 1 if no specific lexer was
                           found.

Select lexer and style:
  -l, --lexer="autodetect"    Lexer to use when formatting or path to an XML
                              file to load.
  -s, --style="swapoff"       Style to use for formatting or path to an XML file
                              to load.

Output format:
  -f, --formatter="terminal"    Formatter to use.
      --json                    Convenience flag to use JSON formatter.
      --html                    Convenience flag to use HTML formatter.
      --svg                     Convenience flag to use SVG formatter.

HTML formatter options:
  --html-prefix=PREFIX             HTML CSS class prefix.
  --html-styles                    Output HTML CSS styles.
  --html-all-styles                Output all HTML CSS styles, including
                                   redundant ones.
  --html-only                      Output HTML fragment.
  --html-inline-styles             Output HTML with inline styles (no classes).
  --html-tab-width=8               Set the HTML tab width.
  --html-lines                     Include line numbers in output.
  --html-lines-table               Split line numbers and code in a HTML table
  --html-lines-style=STRING        Style for line numbers.
  --html-highlight=N[:M][,...]     Highlight these lines.
  --html-highlight-style=STRING    Style used for highlighting lines.
  --html-base-line=1               Base line number.
  --html-prevent-surrounding-pre
                                   Prevent the surrounding pre tag.
  --html-linkable-lines            Make the line numbers linkable and be a link
                                   to themselves.
```

There are also two hidden flags: `--xml DIR` and `--profile FILE`. They work as specified later but never appear in help. `--version` writes exactly `?-?-?` followed by LF. Help, version, list, and XML export are terminal actions and do not require an input or style. Boolean convenience format flags have precedence in this order after parsing: JSON, then HTML, then SVG; because selection is an ordered if/else-if, `--json` wins if several are true. Any convenience flag overrides `-f`.

The only formatter values accepted by `-f`/`--formatter` are `html`, `json`, `noop`, `svg`, `terminal`, `terminal16`, `terminal16m`, `terminal256`, `terminal8`, and `tokens`.

## Spec 3

Lexer selection is performed separately for each input. An explicit `-l NAME`/`--lexer NAME` first looks up an exact registered lexer name or alias. If found, it always overrides filename extension and content. If not registered, treat the argument as a possible XML lexer pathname: an existing path is parsed as an XML regex lexer; a nonexistent path produces no lexer rather than a diagnostic. In lenient mode that becomes the plaintext fallback; in `--fail` mode it exits silently with status 1.

The default lexer value is `autodetect`. Autodetection first matches the input filename against registered filename and alias-filename patterns; for stdin, `--filename STRING` supplies this name. If no filename match exists, run the registry's content analyzers. Required filename recognition includes `.go` as Go, `.py` as Python, `.js` as JavaScript, `.rs` as Rust, and the basename `Makefile` as Makefile. In this corpus, the exercised Python-looking/shebang text supplied through unhinted stdin or an extensionless temporary file does not obtain a specific Python match and therefore uses the lenient fallback. Ambiguous ordinary text such as `random text without clear language`, `some plain text` with an unknown extension, or an unknown binary file likewise has no specific match.

In normal lenient mode, a failed analysis uses a plaintext fallback lexer and still formats successfully. In `--fail` mode, no fallback is allowed: read at most the first 1,024 bytes to select a lexer, then read the rest only after a lexer is found; if none is found, exit 1 with empty stdout and empty stderr. A valid explicit lexer or a recognized filename hint makes `--fail` succeed even for arbitrary/binary contents. Invocation through a basename `.lessfilter` has the same effect as setting `--fail`.

## Spec 4

Lexing produces an ordered stream of `(type, value)` tokens whose values concatenate to the lexer's preprocessed text. Before matching, CRLF and bare CR are both normalized to LF; this applies to the standard regex lexers and plaintext. Spaces, tabs, blank lines, Unicode, combining/zero-width characters, and embedded NUL/control characters are otherwise preserved. Before formatting, coalesce adjacent tokens of the same type.

An unterminated final line is ordinarily preserved as unterminated. There is a lexer-specific exception for the Makefile recipe exercised by this corpus: stdin bytes `all:` LF TAB `echo "test"`, with no final LF, selected using `--filename Makefile`, produce a token stream ending in LF. Terminal output consequently ends in `ESC[0m` LF. This synthesized LF is part of Makefile lexing, not a general formatter behavior.

Use the complete Chroma-v2 regex-lexer corpus fixed by the snapshot identifier. The behavior exercised most heavily is the standard Python, Go, JavaScript, Rust, Makefile, and plaintext lexing behavior. At minimum, preserve these distinctions exactly: keyword families (`Keyword`, `KeywordDeclaration`, `KeywordNamespace`, `KeywordType`, `KeywordConstant`), identifiers (`Name`, `NameOther`, `NameFunction`, `NameClass`, `NameBuiltin`, and magic-name variants), punctuation, operators, integer/float literals, string families (including Python affix/interpolation tokens), comments/hashbangs, whitespace, and `Error` tokens.

Representative required tokenization is:

```text
Python input: print("hello")
NameBuiltin "print"; Punctuation "("; LiteralStringDouble "\"hello\""; Punctuation ")"

Go input: package main followed by LF
KeywordNamespace "package"; TextWhitespace " "; NameOther "main"; TextWhitespace "LF"

Python input: def fibonacci(n):
Keyword "def"; Text " "; NameFunction "fibonacci"; Punctuation "("; Name "n"; Punctuation "):"
```

Python must recognize decorators, async/await, class and function definitions, imports, annotations, docstrings, f-strings/interpolations, builtins, comments, numeric literals, and invalid/incomplete source without crashing. Go must recognize package/import, declarations, primitive types, functions and calls, operators, comments, raw/interpreted strings, and emit `Error` for an unmatched quote where malformed Go source places it. JavaScript and Rust need their ordinary contemporary syntax highlighted while preserving all content. Plaintext emits unclassified text rather than pretending it is one of those languages.

## Spec 5

`--list` writes a deterministic registry listing and exits. It sorts lexers by display name, prints each optional metadata line only when nonempty, then prints sorted style and formatter names. The following block is the complete exact stdout, including its blank line before `styles:`:

```text
lexers:
  ABAP
    aliases: abap
    filenames: *.abap *.ABAP
    mimetypes: text/x-abap
  ABNF
    aliases: abnf
    filenames: *.abnf
    mimetypes: text/x-abnf
  ActionScript
    aliases: as actionscript
    filenames: *.as
    mimetypes: application/x-actionscript text/x-actionscript text/actionscript
  ActionScript 3
    aliases: as3 actionscript3
    filenames: *.as
    mimetypes: application/x-actionscript3 text/x-actionscript3 text/actionscript3
  Ada
    aliases: ada ada95 ada2005
    filenames: *.adb *.ads *.ada
    mimetypes: text/x-ada
  Agda
    aliases: agda
    filenames: *.agda
    mimetypes: text/x-agda
  AL
    aliases: al
    filenames: *.al *.dal
    mimetypes: text/x-al
  Alloy
    aliases: alloy
    filenames: *.als
    mimetypes: text/x-alloy
  AMPL
    aliases: ampl
    filenames: *.mod *.run
    mimetypes: text/x-ampl
  Angular2
    aliases: ng2
  ANTLR
    aliases: antlr
  ApacheConf
    aliases: apacheconf aconf apache
    filenames: .htaccess apache.conf apache2.conf
    mimetypes: text/x-apacheconf
  APL
    aliases: apl
    filenames: *.apl
  AppleScript
    aliases: applescript
    filenames: *.applescript
  ArangoDB AQL
    aliases: aql
    filenames: *.aql
    mimetypes: text/x-aql
  Arduino
    aliases: arduino
    filenames: *.ino
    mimetypes: text/x-arduino
  ArmAsm
    aliases: armasm
    filenames: *.s *.S
    mimetypes: text/x-armasm text/x-asm
  ATL
    aliases: atl
    filenames: *.atl
    mimetypes: text/x-atl
  AutoHotkey
    aliases: autohotkey ahk
    filenames: *.ahk *.ahkl
    mimetypes: text/x-autohotkey
  AutoIt
    aliases: autoit
    filenames: *.au3
    mimetypes: text/x-autoit
  Awk
    aliases: awk gawk mawk nawk
    filenames: *.awk
    mimetypes: application/x-awk
  Ballerina
    aliases: ballerina
    filenames: *.bal
    mimetypes: text/x-ballerina
  Bash
    aliases: bash sh ksh zsh shell
    filenames: *.sh *.ksh *.bash *.ebuild *.eclass .env .env.* *.env *.exheres-0 *.exlib *.zsh *.zshrc .bashrc bashrc .bash_* bash_* zshrc .zshrc APKBUILD PKGBUILD
    mimetypes: application/x-sh application/x-shellscript
  Bash Session
    aliases: bash-session console shell-session
    filenames: *.sh-session
    mimetypes: text/x-sh
  Batchfile
    aliases: bat batch dosbatch winbatch
    filenames: *.bat *.cmd
    mimetypes: application/x-dos-batch
  Beef
    aliases: beef
    filenames: *.bf
    mimetypes: text/x-beef
  BibTeX
    aliases: bib bibtex
    filenames: *.bib
    mimetypes: text/x-bibtex
  Bicep
    aliases: bicep
    filenames: *.bicep
  BlitzBasic
    aliases: blitzbasic b3d bplus
    filenames: *.bb *.decls
    mimetypes: text/x-bb
  BNF
    aliases: bnf
    filenames: *.bnf
    mimetypes: text/x-bnf
  BQN
    aliases: bqn
    filenames: *.bqn
  Brainfuck
    aliases: brainfuck bf
    filenames: *.bf *.b
    mimetypes: application/x-brainfuck
  C
    aliases: c
    filenames: *.c *.h *.idc *.x[bp]m
    mimetypes: text/x-chdr text/x-csrc image/x-xbitmap image/x-xpixmap
  C#
    aliases: csharp c#
    filenames: *.cs
    mimetypes: text/x-csharp
  C++
    aliases: cpp c++
    filenames: *.cpp *.hpp *.c++ *.h++ *.cc *.hh *.cxx *.hxx *.C *.H *.cp *.CPP *.tpp
    mimetypes: text/x-c++hdr text/x-c++src
  C3
    aliases: c3
    filenames: *.c3 *.c3i *.c3t
  Caddyfile
    aliases: caddyfile caddy
    filenames: Caddyfile*
  Caddyfile Directives
    aliases: caddyfile-directives caddyfile-d caddy-d
  Cap'n Proto
    aliases: capnp
    filenames: *.capnp
  Cassandra CQL
    aliases: cassandra cql
    filenames: *.cql
    mimetypes: text/x-cql
  Ceylon
    aliases: ceylon
    filenames: *.ceylon
    mimetypes: text/x-ceylon
  CFEngine3
    aliases: cfengine3 cf3
    filenames: *.cf
  cfstatement
    aliases: cfs
  ChaiScript
    aliases: chai chaiscript
    filenames: *.chai
    mimetypes: text/x-chaiscript application/x-chaiscript
  Chapel
    aliases: chapel chpl
    filenames: *.chpl
  Cheetah
    aliases: cheetah spitfire
    filenames: *.tmpl *.spt
    mimetypes: application/x-cheetah application/x-spitfire
  Clojure
    aliases: clojure clj edn
    filenames: *.clj *.edn
    mimetypes: text/x-clojure application/x-clojure application/edn
  CMake
    aliases: cmake
    filenames: *.cmake CMakeLists.txt
    mimetypes: text/x-cmake
  COBOL
    aliases: cobol
    filenames: *.cob *.COB *.cpy *.CPY
    mimetypes: text/x-cobol
  CoffeeScript
    aliases: coffee-script coffeescript coffee
    filenames: *.coffee
    mimetypes: text/coffeescript
  Common Lisp
    aliases: common-lisp cl lisp
    filenames: *.cl *.lisp
    mimetypes: text/x-common-lisp
  Coq
    aliases: coq
    filenames: *.v
    mimetypes: text/x-coq
  Core
    aliases: core
    filenames: *.core
    mimetypes: text/x-core
  Crystal
    aliases: cr crystal
    filenames: *.cr
    mimetypes: text/x-crystal
  CSS
    aliases: css
    filenames: *.css
    mimetypes: text/css
  CSV
    aliases: csv
    filenames: *.csv
    mimetypes: text/csv
  CUE
    aliases: cue
    filenames: *.cue
    mimetypes: text/x-cue
  Cython
    aliases: cython pyx pyrex
    filenames: *.pyx *.pxd *.pxi
    mimetypes: text/x-cython application/x-cython
  D
    aliases: d
    filenames: *.d *.di
    mimetypes: text/x-d
  Dart
    aliases: dart
    filenames: *.dart
    mimetypes: text/x-dart
  Dax
    aliases: dax
    filenames: *.dax
  Desktop file
    aliases: desktop desktop_entry
    filenames: *.desktop
    mimetypes: application/x-desktop
  Devicetree
    aliases: devicetree dts
    filenames: *.dts *.dtsi
    mimetypes: text/x-devicetree
  Diff
    aliases: diff udiff
    filenames: *.diff *.patch
    mimetypes: text/x-diff text/x-patch
  Django/Jinja
    aliases: django jinja
    mimetypes: application/x-django-templating application/x-jinja
  dns
    aliases: zone bind
    filenames: *.zone
    mimetypes: text/dns
  Docker
    aliases: docker dockerfile containerfile
    filenames: Dockerfile Dockerfile.* *.Dockerfile *.docker Containerfile Containerfile.* *.Containerfile
    mimetypes: text/x-dockerfile-config
  DTD
    aliases: dtd
    filenames: *.dtd
    mimetypes: application/xml-dtd
  Dylan
    aliases: dylan
    filenames: *.dylan *.dyl *.intr
    mimetypes: text/x-dylan
  EBNF
    aliases: ebnf
    filenames: *.ebnf
    mimetypes: text/x-ebnf
  Elixir
    aliases: elixir ex exs
    filenames: *.ex *.eex *.exs
    mimetypes: text/x-elixir
  Elm
    aliases: elm
    filenames: *.elm
    mimetypes: text/x-elm
  EmacsLisp
    aliases: emacs elisp emacs-lisp
    filenames: *.el
    mimetypes: text/x-elisp application/x-elisp
  ERB
    aliases: erb html+erb html+ruby rhtml
    filenames: *.erb *.html.erb *.xml.erb *.rhtml
    mimetypes: application/x-ruby-templating
  Erlang
    aliases: erlang
    filenames: *.erl *.hrl *.es *.escript
    mimetypes: text/x-erlang
  Factor
    aliases: factor
    filenames: *.factor
    mimetypes: text/x-factor
  Fennel
    aliases: fennel fnl
    filenames: *.fennel
    mimetypes: text/x-fennel application/x-fennel
  Fish
    aliases: fish fishshell
    filenames: *.fish *.load
    mimetypes: application/x-fish
  Forth
    aliases: forth
    filenames: *.frt *.fth *.fs
    mimetypes: application/x-forth
  Fortran
    aliases: fortran f90
    filenames: *.f03 *.f90 *.f95 *.F03 *.F90 *.F95
    mimetypes: text/x-fortran
  FortranFixed
    aliases: fortranfixed
    filenames: *.f *.F
    mimetypes: text/x-fortran
  FSharp
    aliases: fsharp
    filenames: *.fs *.fsi
    mimetypes: text/x-fsharp
  GAS
    aliases: gas asm
    filenames: *.s *.S
    mimetypes: text/x-gas
  GDScript
    aliases: gdscript gd
    filenames: *.gd
    mimetypes: text/x-gdscript application/x-gdscript
  GDScript3
    aliases: gdscript3 gd3
    filenames: *.gd
    mimetypes: text/x-gdscript application/x-gdscript
  Gemtext
    aliases: gemtext gmi gmni gemini
    filenames: *.gmi *.gmni *.gemini
    mimetypes: text/gemini
  Genshi
    aliases: genshi kid xml+genshi xml+kid
    filenames: *.kid
    mimetypes: application/x-genshi application/x-kid
  Genshi HTML
    aliases: html+genshi html+kid
    mimetypes: text/html+genshi
  Genshi Text
    aliases: genshitext
    mimetypes: application/x-genshi-text text/x-genshi
  Gettext
    aliases: pot po
    filenames: *.pot *.po
    mimetypes: application/x-gettext text/x-gettext text/gettext
  Gherkin
    aliases: cucumber Cucumber gherkin Gherkin
    filenames: *.feature *.FEATURE
    mimetypes: text/x-gherkin
  Gleam
    aliases: gleam
    filenames: *.gleam
    mimetypes: text/x-gleam
  GLSL
    aliases: glsl
    filenames: *.vert *.frag *.geo
    mimetypes: text/x-glslsrc
  Gnuplot
    aliases: gnuplot
    filenames: *.plot *.plt
    mimetypes: text/x-gnuplot
  Go
    aliases: go golang
    filenames: *.go
    mimetypes: text/x-gosrc
  Go HTML Template
    aliases: go-html-template
  Go Template
    aliases: go-template
    filenames: *.gotmpl *.go.tmpl
  Go Text Template
    aliases: go-text-template
  GraphQL
    aliases: graphql graphqls gql
    filenames: *.graphql *.graphqls
  Groff
    aliases: groff nroff man
    filenames: *.[1-9] *.1p *.3pm *.man
    mimetypes: application/x-troff text/troff
  Groovy
    aliases: groovy
    filenames: *.groovy *.gradle
    mimetypes: text/x-groovy
  Handlebars
    aliases: handlebars hbs
    filenames: *.handlebars *.hbs
  Hare
    aliases: hare
    filenames: *.ha
    mimetypes: text/x-hare
  Haskell
    aliases: haskell hs
    filenames: *.hs
    mimetypes: text/x-haskell
  Haxe
    aliases: hx haxe hxsl
    filenames: *.hx *.hxsl
    mimetypes: text/haxe text/x-haxe text/x-hx
  HCL
    aliases: hcl
    filenames: *.hcl
    mimetypes: application/x-hcl
  Hexdump
    aliases: hexdump
  HLB
    aliases: hlb
    filenames: *.hlb
  HLSL
    aliases: hlsl
    filenames: *.hlsl *.hlsli *.cginc *.fx *.fxh
    mimetypes: text/x-hlsl
  HolyC
    aliases: holyc
    filenames: *.HC *.hc *.HH *.hh *.hc.z *.HC.Z
    mimetypes: text/x-chdr text/x-csrc image/x-xbitmap image/x-xpixmap
  HTML
    aliases: html
    filenames: *.html *.htm *.xhtml *.xslt
    mimetypes: text/html application/xhtml+xml
  HTTP
    aliases: http
  Hy
    aliases: hylang
    filenames: *.hy
    mimetypes: text/x-hy application/x-hy
  Idris
    aliases: idris idr
    filenames: *.idr
    mimetypes: text/x-idris
  Igor
    aliases: igor igorpro
    filenames: *.ipf
    mimetypes: text/ipf
  INI
    aliases: ini cfg dosini
    filenames: *.ini *.cfg *.inf *.service *.socket *.container *.network *.build *.pod *.kube *.volume *.image .gitconfig .editorconfig pylintrc .pylintrc
    mimetypes: text/x-ini text/inf
  Io
    aliases: io
    filenames: *.io
    mimetypes: text/x-iosrc
  ISCdhcpd
    aliases: iscdhcpd
    filenames: dhcpd.conf
  J
    aliases: j
    filenames: *.ijs
    mimetypes: text/x-j
  Janet
    aliases: janet
    filenames: *.janet *.jdn
    mimetypes: text/x-janet application/x-janet
  Java
    aliases: java
    filenames: *.java
    mimetypes: text/x-java
  JavaScript
    aliases: js javascript
    filenames: *.js *.jsm *.mjs *.cjs
    mimetypes: application/javascript application/x-javascript text/x-javascript text/javascript
  JSON
    aliases: json
    filenames: *.json *.jsonc *.json5 *.avsc .luaurc
    mimetypes: application/json
  JSONata
    aliases: jsonata
    filenames: *.jsonata
  Jsonnet
    aliases: jsonnet
    filenames: *.jsonnet *.libsonnet
  Julia
    aliases: julia jl
    filenames: *.jl
    mimetypes: text/x-julia application/x-julia
  Jungle
    aliases: jungle
    filenames: *.jungle
    mimetypes: text/x-jungle
  Kakoune
    aliases: kak kakoune kakrc kakscript
    filenames: *.kak kakrc
    mimetypes: application/x-sh application/x-shellscript text/x-shellscript
  KDL
    aliases: kdl
    filenames: *.kdl
  Kotlin
    aliases: kotlin
    filenames: *.kt *.kts
    mimetypes: text/x-kotlin
  Lean4
    aliases: lean4 lean
    filenames: *.lean
    mimetypes: text/x-lean4 text/x-lean
  Lighttpd configuration file
    aliases: lighty lighttpd
    mimetypes: text/x-lighttpd-conf
  LLVM
    aliases: llvm
    filenames: *.ll
    mimetypes: text/x-llvm
  lox
    filenames: *.lox
  Lua
    aliases: lua
    filenames: *.lua *.wlua
    mimetypes: text/x-lua application/x-lua
  Luau
    aliases: luau
    filenames: *.luau
  Makefile
    aliases: make makefile mf bsdmake
    filenames: *.mak *.mk Makefile makefile Makefile.* GNUmakefile BSDmakefile Justfile justfile .justfile
    mimetypes: text/x-makefile
  Mako
    aliases: mako
    filenames: *.mao
    mimetypes: application/x-mako
  markdown
    aliases: md mkd
    filenames: *.md *.mkd *.markdown
    mimetypes: text/x-markdown
  Markless
    aliases: mess
    filenames: *.mess *.markless
    mimetypes: text/x-markless
  Mason
    aliases: mason
    filenames: *.m *.mhtml *.mc *.mi autohandler dhandler
    mimetypes: application/x-mason
  Materialize SQL dialect
    aliases: materialize mzsql
    mimetypes: text/x-materializesql
  Mathematica
    aliases: mathematica mma nb
    filenames: *.cdf *.m *.ma *.mt *.mx *.nb *.nbp *.wl
    mimetypes: application/mathematica application/vnd.wolfram.mathematica application/vnd.wolfram.mathematica.package application/vnd.wolfram.cdf
  Matlab
    aliases: matlab
    filenames: *.m
    mimetypes: text/matlab
  MCFunction
    aliases: mcfunction mcf
    filenames: *.mcfunction
    mimetypes: text/mcfunction
  Meson
    aliases: meson meson.build
    filenames: meson.build meson.options meson_options.txt
    mimetypes: text/x-meson
  Metal
    aliases: metal
    filenames: *.metal
    mimetypes: text/x-metal
  microcad
    aliases: µcad
    filenames: *.µcad *.ucad *.mcad
    mimetypes: text/microcad
  MiniZinc
    aliases: minizinc MZN mzn
    filenames: *.mzn *.dzn *.fzn
    mimetypes: text/minizinc
  MLIR
    aliases: mlir
    filenames: *.mlir
    mimetypes: text/x-mlir
  Modelica
    aliases: modelica
    filenames: *.mo
    mimetypes: text/x-modelica
  Modula-2
    aliases: modula2 m2
    filenames: *.def *.mod
    mimetypes: text/x-modula2
  Mojo
    aliases: mojo 🔥
    filenames: *.mojo *.🔥
    mimetypes: text/x-mojo application/x-mojo
  MonkeyC
    aliases: monkeyc
    filenames: *.mc
    mimetypes: text/x-monkeyc
  MoonBit
    aliases: moonbit mbt
    filenames: *.mbt
  MoonScript
    aliases: moonscript moon
    filenames: *.moon
    mimetypes: text/x-moonscript application/x-moonscript
  MorrowindScript
    aliases: morrowind mwscript
  Myghty
    aliases: myghty
    filenames: *.myt autodelegate
    mimetypes: application/x-myghty
  MySQL
    aliases: mysql mariadb
    filenames: *.sql
    mimetypes: text/x-mysql text/x-mariadb
  NASM
    aliases: nasm
    filenames: *.asm *.ASM *.nasm
    mimetypes: text/x-nasm
  Natural
    aliases: natural
    filenames: *.NSN *.NSP *.NSS *.NSH *.NSG *.NSL *.NSA *.NSM *.NSC *.NS7
    mimetypes: text/x-natural
  NDISASM
    aliases: ndisasm
    mimetypes: text/x-disasm
  Newspeak
    aliases: newspeak
    filenames: *.ns2
    mimetypes: text/x-newspeak
  Nginx configuration file
    aliases: nginx
    filenames: nginx.conf
    mimetypes: text/x-nginx-conf
  Nim
    aliases: nim nimrod
    filenames: *.nim *.nimrod
    mimetypes: text/x-nim
  Nix
    aliases: nixos nix
    filenames: *.nix
    mimetypes: text/x-nix
  NSIS
    aliases: nsis nsi nsh
    filenames: *.nsi *.nsh
    mimetypes: text/x-nsis
  Nu
    aliases: nu
    filenames: *.nu
    mimetypes: text/plain
  Objective-C
    aliases: objective-c objectivec obj-c objc
    filenames: *.m *.h
    mimetypes: text/x-objective-c
  ObjectPascal
    aliases: objectpascal
    filenames: *.pas *.pp *.inc *.dpr *.dpk *.lpr *.lpk
    mimetypes: text/x-pascal
  OCaml
    aliases: ocaml
    filenames: *.ml *.mli *.mll *.mly
    mimetypes: text/x-ocaml
  Octave
    aliases: octave
    filenames: *.m
    mimetypes: text/octave
  Odin
    aliases: odin
    filenames: *.odin
    mimetypes: text/odin
  OnesEnterprise
    aliases: ones onesenterprise 1S 1S:Enterprise
    filenames: *.EPF *.epf *.ERF *.erf
    mimetypes: application/octet-stream
  OpenEdge ABL
    aliases: openedge abl progress openedgeabl
    filenames: *.p *.cls *.w *.i
    mimetypes: text/x-openedge application/x-openedge
  OpenSCAD
    aliases: openscad
    filenames: *.scad
    mimetypes: text/x-scad
  Org Mode
    aliases: org orgmode
    filenames: *.org
    mimetypes: text/org
  PacmanConf
    aliases: pacmanconf
    filenames: pacman.conf
  Perl
    aliases: perl pl
    filenames: *.pl *.pm *.t
    mimetypes: text/x-perl application/x-perl
  PHP
    aliases: php php3 php4 php5
    filenames: *.php *.php[345] *.inc
    mimetypes: text/x-php
  PHTML
    aliases: phtml
    filenames: *.phtml *.php *.php[345] *.inc
    mimetypes: application/x-php application/x-httpd-php application/x-httpd-php3 application/x-httpd-php4 application/x-httpd-php5 text/x-php
  Pig
    aliases: pig
    filenames: *.pig
    mimetypes: text/x-pig
  PkgConfig
    aliases: pkgconfig
    filenames: *.pc
  PL/pgSQL
    aliases: plpgsql
    mimetypes: text/x-plpgsql
  plaintext
    aliases: text plain no-highlight
    filenames: *.txt
    mimetypes: text/plain
  Plutus Core
    aliases: plutus-core plc
    filenames: *.plc
    mimetypes: text/x-plutus-core application/x-plutus-core
  Pony
    aliases: pony
    filenames: *.pony
  PostgreSQL SQL dialect
    aliases: postgresql postgres
    mimetypes: text/x-postgresql
  PostScript
    aliases: postscript postscr
    filenames: *.ps *.eps
    mimetypes: application/postscript
  POVRay
    aliases: pov
    filenames: *.pov *.inc
    mimetypes: text/x-povray
  PowerQuery
    aliases: powerquery pq
    filenames: *.pq
    mimetypes: text/x-powerquery
  PowerShell
    aliases: powershell posh ps1 psm1 psd1 pwsh
    filenames: *.ps1 *.psm1 *.psd1
    mimetypes: text/x-powershell
  Prolog
    aliases: prolog
    filenames: *.ecl *.prolog *.pro *.pl
    mimetypes: text/x-prolog
  Promela
    aliases: promela
    filenames: *.pml *.prom *.prm *.promela *.pr *.pm
    mimetypes: text/x-promela
  PromQL
    aliases: promql
    filenames: *.promql
  properties
    aliases: java-properties
    filenames: *.properties
    mimetypes: text/x-java-properties
  Protocol Buffer
    aliases: protobuf proto
    filenames: *.proto
  Protocol Buffer Text Format
    aliases: txtpb
    filenames: *.txtpb *.textproto *.textpb *.pbtxt
    mimetypes: application/x-protobuf-text
  PRQL
    aliases: prql
    filenames: *.prql
    mimetypes: application/prql
  PSL
    aliases: psl
    filenames: *.psl *.BATCH *.TRIG *.PROC
    mimetypes: text/x-psl
  Puppet
    aliases: puppet
    filenames: *.pp
  Python
    aliases: python py sage python3 py3 starlark
    filenames: *.py *.pyi *.pyw *.jy *.sage *.sc SConstruct SConscript *.bzl BUCK BUILD BUILD.bazel WORKSPACE WORKSPACE.bzlmod WORKSPACE.bazel MODULE.bazel REPO.bazel *.star *.tac
    mimetypes: text/x-python application/x-python text/x-python3 application/x-python3
  Python 2
    aliases: python2 py2
    mimetypes: text/x-python2 application/x-python2
  QBasic
    aliases: qbasic basic
    filenames: *.BAS *.bas
    mimetypes: text/basic
  QML
    aliases: qml qbs
    filenames: *.qml *.qbs
    mimetypes: application/x-qml application/x-qt.qbs+qml
  R
    aliases: splus s r
    filenames: *.S *.R *.r .Rhistory .Rprofile .Renviron
    mimetypes: text/S-plus text/S text/x-r-source text/x-r text/x-R text/x-r-history text/x-r-profile
  Racket
    aliases: racket rkt
    filenames: *.rkt *.rktd *.rktl
    mimetypes: text/x-racket application/x-racket
  Ragel
    aliases: ragel
  Raku
    aliases: perl6 pl6 raku
    filenames: *.pl *.pm *.nqp *.p6 *.6pl *.p6l *.pl6 *.6pm *.p6m *.pm6 *.t *.raku *.rakumod *.rakutest *.rakudoc
    mimetypes: text/x-perl6 application/x-perl6 text/x-raku application/x-raku
  react
    aliases: jsx react
    filenames: *.jsx *.react
    mimetypes: text/jsx text/typescript-jsx
  ReasonML
    aliases: reason reasonml
    filenames: *.re *.rei
    mimetypes: text/x-reasonml
  reg
    aliases: registry
    filenames: *.reg
    mimetypes: text/x-windows-registry
  Rego
    aliases: rego
    filenames: *.rego
  reStructuredText
    aliases: rst rest restructuredtext
    filenames: *.rst *.rest
    mimetypes: text/x-rst text/prs.fallenstein.rst
  Rexx
    aliases: rexx arexx
    filenames: *.rexx *.rex *.rx *.arexx
    mimetypes: text/x-rexx
  RGBDS Assembly
    aliases: rgbasm
    filenames: *.asm
  Ring
    aliases: ring
    filenames: *.ring *.rh *.rform
    mimetypes: text/x-ring
  RPGLE
    aliases: SQLRPGLE RPG IV
    filenames: *.RPGLE *.rpgle *.SQLRPGLE *.sqlrpgle
    mimetypes: text/x-rpgle text/x-sqlrpgle
  RPMSpec
    aliases: spec
    filenames: *.spec
    mimetypes: text/x-rpm-spec
  Ruby
    aliases: rb ruby duby
    filenames: *.rb *.rbw Rakefile *.rake *.gemspec *.rbx *.duby Gemfile Vagrantfile
    mimetypes: text/x-ruby application/x-ruby
  Rust
    aliases: rust rs
    filenames: *.rs *.rs.in
    mimetypes: text/rust text/x-rust
  SAS
    aliases: sas
    filenames: *.SAS *.sas
    mimetypes: text/x-sas text/sas application/x-sas
  Sass
    aliases: sass
    filenames: *.sass
    mimetypes: text/x-sass
  Scala
    aliases: scala
    filenames: *.scala
    mimetypes: text/x-scala
  scdoc
    aliases: scdoc
    filenames: *.scd *.scdoc
  Scheme
    aliases: scheme scm
    filenames: *.scm *.ss
    mimetypes: text/x-scheme application/x-scheme
  Scilab
    aliases: scilab
    filenames: *.sci *.sce *.tst
    mimetypes: text/scilab
  SCSS
    aliases: scss
    filenames: *.scss
    mimetypes: text/x-scss
  Sed
    aliases: sed gsed ssed
    filenames: *.sed *.[gs]sed
    mimetypes: text/x-sed
  Sieve
    aliases: sieve
    filenames: *.siv *.sieve
  Smali
    aliases: smali
    filenames: *.smali
    mimetypes: text/smali
  Smalltalk
    aliases: smalltalk squeak st
    filenames: *.st
    mimetypes: text/x-smalltalk
  Smarty
    aliases: smarty
    filenames: *.tpl
    mimetypes: application/x-smarty
  SNBT
    aliases: snbt
    filenames: *.snbt
    mimetypes: text/snbt
  Snobol
    aliases: snobol
    filenames: *.snobol
    mimetypes: text/x-snobol
  Solidity
    aliases: sol solidity
    filenames: *.sol
  SourcePawn
    aliases: sp
    filenames: *.sp *.inc
    mimetypes: text/x-sourcepawn
  Spade
    aliases: spade
    filenames: *.spade
    mimetypes: text/spade text/x-spade
  SPARQL
    aliases: sparql
    filenames: *.rq *.sparql
    mimetypes: application/sparql-query
  SQL
    aliases: sql
    filenames: *.sql
    mimetypes: text/x-sql
  SquidConf
    aliases: squidconf squid.conf squid
    filenames: squid.conf
    mimetypes: text/x-squidconf
  Standard ML
    aliases: sml
    filenames: *.sml *.sig *.fun
    mimetypes: text/x-standardml application/x-standardml
  stas
    filenames: *.stas
  Stylus
    aliases: stylus
    filenames: *.styl
    mimetypes: text/x-styl
  Svelte
    aliases: svelte
    filenames: *.svelte
    mimetypes: application/x-svelte
  Swift
    aliases: swift
    filenames: *.swift
    mimetypes: text/x-swift
  SYSTEMD
    aliases: systemd
    filenames: *.automount *.device *.dnssd *.link *.mount *.netdev *.network *.path *.scope *.service *.slice *.socket *.swap *.target *.timer
    mimetypes: text/plain
  systemverilog
    aliases: systemverilog sv
    filenames: *.sv *.svh
    mimetypes: text/x-systemverilog
  TableGen
    aliases: tablegen
    filenames: *.td
    mimetypes: text/x-tablegen
  Tal
    aliases: tal uxntal
    filenames: *.tal
    mimetypes: text/x-uxntal
  TASM
    aliases: tasm
    filenames: *.asm *.ASM *.tasm
    mimetypes: text/x-tasm
  Tcl
    aliases: tcl
    filenames: *.tcl *.rvt
    mimetypes: text/x-tcl text/x-script.tcl application/x-tcl
  Tcsh
    aliases: tcsh csh
    filenames: *.tcsh *.csh
    mimetypes: application/x-csh
  Termcap
    aliases: termcap
    filenames: termcap termcap.src
  Terminfo
    aliases: terminfo
    filenames: terminfo terminfo.src
  Terraform
    aliases: terraform tf hcl
    filenames: *.tf *.hcl
    mimetypes: application/x-tf application/x-terraform
  TeX
    aliases: tex latex
    filenames: *.tex *.aux *.toc
    mimetypes: text/x-tex text/x-latex
  Thrift
    aliases: thrift
    filenames: *.thrift
    mimetypes: application/x-thrift
  TOML
    aliases: toml
    filenames: *.toml Pipfile poetry.lock uv.lock
    mimetypes: text/x-toml
  TradingView
    aliases: tradingview tv
    filenames: *.tv
    mimetypes: text/x-tradingview
  Transact-SQL
    aliases: tsql t-sql
    mimetypes: text/x-tsql
  Turing
    aliases: turing
    filenames: *.turing *.tu
    mimetypes: text/x-turing
  Turtle
    aliases: turtle
    filenames: *.ttl
    mimetypes: text/turtle application/x-turtle
  Twig
    aliases: twig
    filenames: *.twig
    mimetypes: application/x-twig
  TypeScript
    aliases: ts tsx typescript
    filenames: *.ts *.tsx *.mts *.cts
    mimetypes: text/x-typescript
  TypoScript
    aliases: typoscript
    filenames: *.ts
    mimetypes: text/x-typoscript
  TypoScriptCssData
    aliases: typoscriptcssdata
  TypoScriptHtmlData
    aliases: typoscripthtmldata
  Typst
    aliases: typst
    filenames: *.typ
    mimetypes: text/x-typst
  ucode
    filenames: *.uc
    mimetypes: application/x.ucode text/x.ucode
  V
    aliases: v vlang
    filenames: *.v *.vv v.mod
    mimetypes: text/x-v
  V shell
    aliases: vsh vshell
    filenames: *.vsh
    mimetypes: text/x-vsh
  Vala
    aliases: vala vapi
    filenames: *.vala *.vapi
    mimetypes: text/x-vala
  VB.net
    aliases: vb.net vbnet
    filenames: *.vb *.bas
    mimetypes: text/x-vbnet text/x-vba
  verilog
    aliases: verilog v
    filenames: *.v
    mimetypes: text/x-verilog
  VHDL
    aliases: vhdl
    filenames: *.vhdl *.vhd
    mimetypes: text/x-vhdl
  VHS
    aliases: vhs tape cassette
    filenames: *.tape
  VimL
    aliases: vim
    filenames: *.vim .vimrc .exrc .gvimrc _vimrc _exrc _gvimrc vimrc gvimrc
    mimetypes: text/x-vim
  vue
    aliases: vue vuejs
    filenames: *.vue
    mimetypes: text/x-vue application/x-vue
  WDTE
    filenames: *.wdte
  WebAssembly Text Format
    aliases: wast wat
    filenames: *.wat *.wast
  WebGPU Shading Language
    aliases: wgsl
    filenames: *.wgsl
    mimetypes: text/wgsl
  WebVTT
    aliases: vtt
    filenames: *.vtt
    mimetypes: text/vtt
  Whiley
    aliases: whiley
    filenames: *.whiley
    mimetypes: text/x-whiley
  XML
    aliases: xml
    filenames: *.xml *.xsl *.rss *.xslt *.xsd *.wsdl *.wsf *.svg *.qrc *.csproj *.vcxproj *.fsproj
    mimetypes: text/xml application/xml image/svg+xml application/rss+xml application/atom+xml
  Xorg
    aliases: xorg.conf
    filenames: xorg.conf
  YAML
    aliases: yaml
    filenames: *.yaml *.yml
    mimetypes: text/x-yaml
  YANG
    aliases: yang
    filenames: *.yang
    mimetypes: application/yang
  Z80 Assembly
    aliases: z80
    filenames: *.z80 *.asm
  Zed
    aliases: zed
    filenames: *.zed
    mimetypes: text/zed
  Zig
    aliases: zig
    filenames: *.zig *.zon
    mimetypes: text/zig

styles: abap algol algol_nu arduino ashen aura-theme-dark aura-theme-dark-soft autumn average base16-snazzy borland bw catppuccin-frappe catppuccin-latte catppuccin-macchiato catppuccin-mocha colorful darcula doom-one doom-one2 dracula emacs evergarden friendly fruity github github-dark gruvbox gruvbox-light hr_high_contrast hrdark igor kanagawa-dragon kanagawa-lotus kanagawa-wave lovelace manni modus-operandi modus-vivendi monokai monokailight murphy native nord nordic onedark onesenterprise paraiso-dark paraiso-light pastie perldoc pygments rainbow_dash rose-pine rose-pine-dawn rose-pine-moon rpgle rrt solarized-dark solarized-dark256 solarized-light swapoff tango tokyonight-day tokyonight-moon tokyonight-night tokyonight-storm trac vim vs vulcan witchhazel xcode xcode-dark
formatters: html json noop svg terminal terminal16 terminal16m terminal256 terminal8 tokens
```

## Spec 6

Style selection happens before reading/lexing ordinary input. A named built-in style is selected case-insensitively, cloned, then optional line-number/highlight overrides are applied. Required named styles include every name in Spec 5; exact output is exercised primarily for `monokai`, `github`, and `solarized-dark`. Different styles must genuinely change ANSI/CSS/SVG colors.

The three core style definitions are:

```text
monokai:
  Error #960050 on #1e0010; Background #f8f8f2 on #272822;
  Keyword #66d9ef; KeywordNamespace #f92672; Name #f8f8f2;
  NameAttribute/NameClass/NameDecorator/NameException/NameFunction/NameOther #a6e22e;
  NameConstant #66d9ef; NameTag #f92672; Literal and Number #ae81ff;
  LiteralDate and String #e6db74; StringEscape #ae81ff; Operator #f92672;
  Punctuation/Text #f8f8f2; Comment #75715e; GenericDeleted #f92672;
  GenericEmph italic; GenericInserted #a6e22e; GenericStrong bold;
  GenericSubheading #75715e.

solarized-dark:
  Other #cb4b16; Background #93a1a1 on #002b36; Keyword #719e07;
  KeywordConstant #cb4b16; KeywordDeclaration/KeywordReserved #268bd2;
  KeywordType #dc322f; NameAttribute #93a1a1; NameBuiltin #b58900;
  NameBuiltinPseudo/NameClass/NameDecorator/NameFunction/NameTag/NameVariable #268bd2;
  NameConstant/NameEntity/NameException #cb4b16; String and StringChar #2aa198;
  StringBacktick #586e75; StringDoc/StringHeredoc #93a1a1;
  StringEscape #cb4b16; StringRegex #dc322f; Number #2aa198;
  Operator #719e07; Comment #586e75; CommentSpecial/CommentPreproc #719e07;
  GenericDeleted #dc322f; GenericEmph italic; GenericError bold #dc322f;
  GenericHeading #cb4b16; GenericInserted #719e07; GenericStrong bold;
  GenericSubheading #268bd2.

github:
  Error #f6f8fa on #82071e; Background #f7f7f7; Keyword/KeywordType #cf222e;
  NameAttribute/NameClass/NameOther/GenericEmph/GenericOutput/Punctuation #1f2328;
  NameBuiltin/NameEntity/NameFunction #6639ba; NameBuiltinPseudo #6a737d;
  NameConstant/NameDecorator/NameTag/Number/Operator #0550ae;
  NameLabel bold #990000; NameNamespace #24292e;
  variable families #953800; String/StringRegex #0a3069; StringSymbol #032f62;
  Comment families #57606a; GenericDeleted #82071e on #ffebe9;
  GenericInserted #116329 on #dafbe1; GenericUnderline underline;
  TextWhitespace #ffffff.
```

Unknown style names are treated as XML style paths. A missing file is fatal status 1 with `executable: error: open <value>: no such file or directory` plus LF. A malformed style lacking its required name reports `executable: error: missing style name attribute` plus LF. A deliberate compatibility quirk is that the default value `swapoff`, though shown in the registry, resolves to the fallback sentinel and is then opened as a pathname; absent a file named `swapoff`, ordinary formatting fails status 1 with `executable: error: open swapoff: no such file or directory` plus LF. Tests normally supply a usable style where formatting is intended.

## Spec 7

The default `terminal` formatter and `terminal8` use the same nearest-color 8-color ANSI palette; `terminal16` uses the basic plus bright 16-color palette; `terminal256` uses the standard xterm 256-color palette; `terminal16m` emits true 24-bit RGB. Convert style foreground/background colors to the nearest indexed palette color by perceptual Lab color distance. Clear the style's overall background before terminal rendering, but retain token-specific backgrounds.

For every nonempty token segment, emit style controls, the token value, and `ESC[0m`. If a styled token includes LF, reset immediately before it, write the LF, then reapply the controls for remaining text. CRLF and bare CR have already become LF during lexer preprocessing. Do not independently add a final newline. Unstyled true-color tokens are written raw.

Control order is bold (`ESC[1m`), underline (`ESC[4m`), italic (`ESC[3m`), foreground, background. True-color foreground is `ESC[38;2;R;G;Bm`; 256 foreground is `ESC[38;5;Nm`; 16-color foreground uses `30`–`37`/`90`–`97`; 8-color uses normal `30`–`37` and represents bright colors as bold plus `30`–`37`. Examples that are exact and normative (`<ESC>` means byte 0x1b):

```text
terminal16m, monokai, Python def func(): pass
<ESC>[38;2;102;217;239mdef<ESC>[0m<ESC>[38;2;248;248;242m <ESC>[0m<ESC>[38;2;166;226;46mfunc<ESC>[0m<ESC>[38;2;248;248;242m():<ESC>[0m<ESC>[38;2;248;248;242m <ESC>[0m<ESC>[38;2;102;217;239mpass<ESC>[0m

terminal16, same input
<ESC>[96mdef<ESC>[0m<ESC>[97m <ESC>[0m<ESC>[93mfunc<ESC>[0m<ESC>[97m():<ESC>[0m<ESC>[97m <ESC>[0m<ESC>[96mpass<ESC>[0m

terminal256, monokai, Go package main LF func main() {}
<ESC>[38;5;197mpackage<ESC>[0m<ESC>[38;5;231m <ESC>[0m<ESC>[38;5;148mmain<ESC>[0m<ESC>[38;5;231m<ESC>[0m
<ESC>[38;5;81mfunc<ESC>[0m<ESC>[38;5;231m <ESC>[0m<ESC>[38;5;148mmain<ESC>[0m<ESC>[38;5;231m()<ESC>[0m<ESC>[38;5;231m <ESC>[0m<ESC>[38;5;231m{}<ESC>[0m
```

The first two example inputs have no newline and neither output does. ANSI-stripped output reconstructs the lexer-preprocessed text: tabs are unchanged, while every input CRLF or bare CR is one LF. For example, all five terminal formatters turn `def f():` CR LF TAB `return 1` CR `# tail` into `def f():` LF TAB `return 1` LF `# tail` after ANSI controls are stripped.

## Spec 8

`json` formatting writes one pretty line-oriented JSON array per input. There is exactly one object per coalesced token, with keys in the exact order `type`, `value`, no spaces inside the object, two leading spaces, comma followed by newline between objects, and a final newline after `]`. Decoded values concatenate to the lexer-preprocessed text (including CR/CRLF-to-LF normalization), not necessarily the original byte sequence. For example:

```json
[
  {"type":"Keyword","value":"def"},
  {"type":"Text","value":" "}
]
```

Empty input is exactly five bytes: `[` LF LF `]` LF. `type` is the canonical concatenated token type name (for example `KeywordNamespace`, `TextWhitespace`, `LiteralStringDouble`); `value` uses standard Go JSON escaping, including escaping `<`, `>`, and `&` as `\u003c`, `\u003e`, `\u0026`. Style selection does not alter JSON token data.

`tokens` writes each coalesced token as `&Token{TYPE, "GO_ESCAPED_VALUE"}` plus LF; for `print("hello")` the exact result is:

```text
&Token{NameBuiltin, "print"}
&Token{Punctuation, "("}
&Token{LiteralStringDouble, "\"hello\""}
&Token{Punctuation, ")"}
```

`noop` concatenates token values unchanged and adds nothing after lexing. It therefore exposes lexer preprocessing: for example, Python noop formatting changes an input CRLF to one LF while preserving surrounding valid UTF-8, tabs, NUL, BOM, comments, indentation, and a missing final newline.

## Spec 9

HTML formatting tokenizes first, HTML-escapes the lexer-preprocessed text, then splits the token stream into logical lines while retaining its LF characters. Required escaping uses numeric `&#34;` for quotes in source, `&lt;`, `&gt;`, `&amp;`, and leaves Unicode encoded as UTF-8. Class-based token spans use the standard short names, including: `k/kc/kd/kn/kp/kr/kt` for keyword types; `n/na/nc/no/nd/ne/nx/nt/nb/bp/nv/vc/vg/vi/vm/nf/fm` for name types; `l/ld/s/sa/sb/sc/dl/sd/s2/se/sh/si/sx/sr/s1/ss/m/mb/mf/mh/mi/il/mo` for literal types; `o/ow/or`, `p`, `c/ch/cm/c1/cs/cp/cpf`, `gd/ge/gi/gs/gu`, `w`, and `err`. Omit a span when the effective class is empty.

Each ordinary line is rendered as `<span class="line"><span class="cl">...line contents including its newline...</span></span>`. Fragment mode (`--html --html-only`) is only `<pre class="chroma"><code>LINES</code></pre>` with no added final newline. Standalone mode is exactly this outer structure:

```text
<html>
<style type="text/css">
CSS
body { COMPACT_BACKGROUND_DECLARATIONS; }
</style><body class="bg">
<pre class="chroma"><code>LINES</code></pre>
</body>
</html>
```

The standalone body rule uses compact property syntax. The resolved declarations themselves end in a semicolon, and the rule renderer adds another one. With Monokai the exact line is `body { color:#f8f8f2;background-color:#272822;; }`. Standalone ends in LF. Inline style mode changes body/pre/token/line attributes as in Spec 11 and omits the `<style>` element. `--html-prevent-surrounding-pre` changes the formatter's pre-wrapper to empty strings and also omits the normal `line` and `cl` wrappers; escaped token spans and raw text are written directly at that point in the fragment or body.

## Spec 10

The default class-based Monokai stylesheet emitted by `--html-styles -s monokai` is exactly:

```css
/* Background */ .bg { color: #f8f8f2; background-color: #272822; }
/* PreWrapper */ .chroma { color: #f8f8f2; background-color: #272822; -webkit-text-size-adjust: none; }
/* Error */ .chroma .err { color: #960050; background-color: #1e0010 }
/* LineLink */ .chroma .lnlinks { outline: none; text-decoration: none; color: inherit }
/* LineTableTD */ .chroma .lntd { vertical-align: top; padding: 0; margin: 0; border: 0; }
/* LineTable */ .chroma .lntable { border-spacing: 0; padding: 0; margin: 0; border: 0; }
/* LineHighlight */ .chroma .hl { background-color: #3c3d38 }
/* LineNumbersTable */ .chroma .lnt { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em;color: #7f7f7f }
/* LineNumbers */ .chroma .ln { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em;color: #7f7f7f }
/* Line */ .chroma .line { display: flex; }
/* Keyword */ .chroma .k { color: #66d9ef }
/* KeywordConstant */ .chroma .kc { color: #66d9ef }
/* KeywordDeclaration */ .chroma .kd { color: #66d9ef }
/* KeywordNamespace */ .chroma .kn { color: #f92672 }
/* KeywordPseudo */ .chroma .kp { color: #66d9ef }
/* KeywordReserved */ .chroma .kr { color: #66d9ef }
/* KeywordType */ .chroma .kt { color: #66d9ef }
/* NameAttribute */ .chroma .na { color: #a6e22e }
/* NameClass */ .chroma .nc { color: #a6e22e }
/* NameConstant */ .chroma .no { color: #66d9ef }
/* NameDecorator */ .chroma .nd { color: #a6e22e }
/* NameException */ .chroma .ne { color: #a6e22e }
/* NameOther */ .chroma .nx { color: #a6e22e }
/* NameTag */ .chroma .nt { color: #f92672 }
/* NameFunction */ .chroma .nf { color: #a6e22e }
/* NameFunctionMagic */ .chroma .fm { color: #a6e22e }
/* Literal */ .chroma .l { color: #ae81ff }
/* LiteralDate */ .chroma .ld { color: #e6db74 }
/* LiteralString */ .chroma .s { color: #e6db74 }
/* LiteralStringAffix */ .chroma .sa { color: #e6db74 }
/* LiteralStringBacktick */ .chroma .sb { color: #e6db74 }
/* LiteralStringChar */ .chroma .sc { color: #e6db74 }
/* LiteralStringDelimiter */ .chroma .dl { color: #e6db74 }
/* LiteralStringDoc */ .chroma .sd { color: #e6db74 }
/* LiteralStringDouble */ .chroma .s2 { color: #e6db74 }
/* LiteralStringEscape */ .chroma .se { color: #ae81ff }
/* LiteralStringHeredoc */ .chroma .sh { color: #e6db74 }
/* LiteralStringInterpol */ .chroma .si { color: #e6db74 }
/* LiteralStringOther */ .chroma .sx { color: #e6db74 }
/* LiteralStringRegex */ .chroma .sr { color: #e6db74 }
/* LiteralStringSingle */ .chroma .s1 { color: #e6db74 }
/* LiteralStringSymbol */ .chroma .ss { color: #e6db74 }
/* LiteralNumber */ .chroma .m { color: #ae81ff }
/* LiteralNumberBin */ .chroma .mb { color: #ae81ff }
/* LiteralNumberFloat */ .chroma .mf { color: #ae81ff }
/* LiteralNumberHex */ .chroma .mh { color: #ae81ff }
/* LiteralNumberInteger */ .chroma .mi { color: #ae81ff }
/* LiteralNumberIntegerLong */ .chroma .il { color: #ae81ff }
/* LiteralNumberOct */ .chroma .mo { color: #ae81ff }
/* Operator */ .chroma .o { color: #f92672 }
/* OperatorWord */ .chroma .ow { color: #f92672 }
/* OperatorReserved */ .chroma .or { color: #f92672 }
/* Comment */ .chroma .c { color: #75715e }
/* CommentHashbang */ .chroma .ch { color: #75715e }
/* CommentMultiline */ .chroma .cm { color: #75715e }
/* CommentSingle */ .chroma .c1 { color: #75715e }
/* CommentSpecial */ .chroma .cs { color: #75715e }
/* CommentPreproc */ .chroma .cp { color: #75715e }
/* CommentPreprocFile */ .chroma .cpf { color: #75715e }
/* GenericDeleted */ .chroma .gd { color: #f92672 }
/* GenericEmph */ .chroma .ge { font-style: italic }
/* GenericInserted */ .chroma .gi { color: #a6e22e }
/* GenericStrong */ .chroma .gs { font-weight: bold }
/* GenericSubheading */ .chroma .gu { color: #75715e }
```

`--html-styles` outputs only the stylesheet and returns without consuming or formatting input. This terminal action ignores `--html-prefix`: `--html-styles --html-prefix=foo` still emits the unprefixed stylesheet shown above, beginning `/* Background */ .bg`, and is byte-for-byte identical to output without `--html-prefix`. In this snapshot, adding `--html-all-styles` for Monokai does not add redundant or zero-style token rules: its output is byte-for-byte the same 3,801-byte, 64-comment stylesheet shown above (SHA-256 `27052d7d5cb4b3dd95bc457eb3a2199642d3551fbf85690949462fd7946f5db2`). In particular there is no `/* TextWhitespace */` rule.

During ordinary HTML formatting, `--html-prefix=P` prepends `P` literally to every generated short class in markup and every selector component in an embedded stylesheet, including `bg`, `chroma`, token classes, `line`, `cl`, `ln`, `lnt`, `lntable`, `lntd`, `lnlinks`, `hl`, and `err`. Hyphens, underscores, and digits are not sanitized. Thus prefix `foo` yields `foobg`, `foochroma`, `fook`, etc.; prefix `custom-` yields `custom-chroma`, `custom-k`, etc. The preceding `--html-styles` exception is specific to that terminal stylesheet-only action.

## Spec 11

With `--html-inline-styles`, do not emit CSS classes or a `<style>` block. Resolve inherited styles, subtract properties already supplied by the enclosing wrapper, and emit a token `<span style="...">` only if some effective property remains. Thus Monokai's ordinary text, spaces, punctuation, and newlines whose only color is the inherited `#f8f8f2` are emitted raw rather than wrapped in a foreground-only span. Monokai standalone begins `<html>` LF `<body style="color:#f8f8f2;background-color:#272822;">` LF; the pre wrapper is `<pre style="color:#f8f8f2;background-color:#272822;-webkit-text-size-adjust:none;"><code>`. Each line uses `<span style="display:flex;">`; its code child is an unadorned `<span>`. Example token styles are `style="color:#66d9ef"` for keywords, `#a6e22e` functions, `#e6db74` strings, `#ae81ff` numbers, `#f92672` operators, and `#75715e` comments. Prefix is irrelevant in this mode.

`--html-tab-width=N` accepts at least 1 through 100 without clamping and preserves literal tab characters in code. In ordinary standalone HTML output, it inserts tab declarations immediately after `background-color` with no intervening space. For N=1 the exact affected class rules begin `/* Background */ .bg { color: #f8f8f2; background-color: #272822;-moz-tab-size: 1; -o-tab-size: 1; tab-size: 1; }` and `/* PreWrapper */ .chroma { color: #f8f8f2; background-color: #272822;-moz-tab-size: 1; -o-tab-size: 1; tab-size: 1; -webkit-text-size-adjust: none; }`; N=4 substitutes `4` in all three declarations. Standalone body CSS and inline attributes use compact equivalents without spaces, such as `-moz-tab-size:19;-o-tab-size:19;tab-size:19;`. A class-based `--html-only` fragment contains the same literal tabs but no CSS, so widths 1 and 100 produce identical fragment bytes for the same input.

The terminal `--html-styles` action ignores `--html-tab-width`. In particular, `--html-styles --html-tab-width=1 -s monokai` emits the unchanged 3,801-byte stylesheet from Spec 10, beginning `/* Background */ .bg { color: #f8f8f2; background-color: #272822; }`, with no tab-size declarations.

`--html-lines-style=STYLE` parses a style expression and replaces the LineNumbers style. `bold` makes line-number CSS font-weight bold. `--html-highlight-style=STYLE` likewise replaces LineHighlight; in a class stylesheet `bold #ffff00` produces `color: #ffff00; font-weight: bold` and replaces the default highlight background. The inline serializer shortens compressible hex colors: the same override in inline table/highlight output is exactly `color:#ff0;font-weight:bold`, in both the number and code presentations.

## Spec 12

`--html-lines` adds one displayed number per logical line after CRLF and bare CR have been normalized to LF. Each newline-terminated segment is one line; a final newline does not synthesize another empty line after it. A nonempty unterminated final segment is one line, while a zero-byte source has zero lines. Thus `a` CR `b` renders as two lines, not one. Numbers begin at `--html-base-line` (default 1), which may be 0 or at least 999999, and increase by one. Left-pad all numbers with spaces to the decimal width of the last number. In ordinary layout, put the number before the `cl` span as `<span class="ln">PADDED_NUMBER</span>`. The line wrapper remains flex.

Whenever line numbering is enabled, including for zero-byte input and whether or not lines are linkable or table-formatted, insert two target rules in the dynamic option-rule block after PreWrapper (and after the table's dynamic last-child rule when table layout is active). With Monokai and the default prefix, they are exactly:

```css
/* LineNumbers targeted by URL anchor */ .chroma .ln:target { color: #f8f8f2; background-color: #3c3d38 }
/* LineNumbersTable targeted by URL anchor */ .chroma .lnt:target { color: #f8f8f2; background-color: #3c3d38 }
```

`--html-prefix` transforms both selector components as usual; for prefix `custom-`, the first selector is `.custom-chroma .custom-ln:target`.

With both `--html-lines` and `--html-lines-table`, wrap the result in `<div class="chroma">` and a single `<table class="lntable"><tr>` containing exactly two `<td class="lntd">` cells. The first cell has `<pre class="chroma">` and one `<span class="lnt">PADDED_NUMBER` LF `</span>` per line. The second has `<pre class="chroma"><code>` and code lines without inline number spans. The stylesheet inserts this exact dynamic rule after PreWrapper (and before the line-number target rules), including the final declaration semicolon:

```css
/* LineTableTD */ .chroma .lntd:last-child { width: 100%; }
```

Table layout is activated only when line numbering is also active.

`--html-linkable-lines` makes every rendered number self-link with prefix `L`: number N has element id `LN` and `<a class="lnlinks" href="#LN">PADDED_NUMBER</a>`. This uses displayed/base-adjusted numbers, so base 200 yields links `#L200`, `#L201`, and so on.

## Spec 13

`--html-highlight` is a comma-separated list of inclusive decimal ranges, each either `N` or `N:M`. Sort ranges by their starting number. Ranges are compared to displayed line numbers after applying `--html-base-line`. Mark an ordinary highlighted line by adding `hl` to the line wrapper (`class="line hl"`); in table mode apply the corresponding highlight wrapper/style to both number and code presentations. Nonexistent ranges are harmless; a range past EOF highlights only existing members, and a range wholly beyond EOF highlights nothing.

When any highlight range is configured, the class-based PreWrapper rule gains `display: grid;` with no separating space after the existing semicolon. For Monokai the exact rule is `/* PreWrapper */ .chroma { color: #f8f8f2; background-color: #272822; -webkit-text-size-adjust: none;display: grid; }`. This occurs even with a custom highlight style and composes with line numbering/base options. Inline wrappers analogously include compact `display:grid;`.

Parsing errors are fatal status 1. More than one colon reports `executable: error: range should be N[:M], not "1:2:3"` plus LF. A bad start reports `executable: error: min value of range should be integer not "abc": strconv.ParseInt: parsing "abc": invalid syntax` plus LF; a bad end analogously begins `max value of range should be integer not "xyz"`. Combined table, link, base, highlight, inline, fragment, prefix, and tab-width options must compose rather than disabling one another.

## Spec 14

SVG output is a complete XML SVG document. It embeds the snapshot's Liberation Mono WOFF as a base64 data URL, so output is self-contained and deterministic. Begin with:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
```

The root is `<svg width="Wpx" height="Hpx" xmlns="http://www.w3.org/2000/svg">`, where `W = 8 * maximum segment byte-width` after treating each tab as four spaces; a terminating LF is included as one byte in that segment's width. Thus `a` TAB `b` has width 48px, while `a` TAB `b` LF has width 56px, and `a` TAB `b` LF `xx` also has width 56px. `H = 10 + floor(16.8 * (logical_line_count + 1))`. After embedded `@font-face`, write a full-size background rect using the style background, then `<g font-family="Liberation Mono" font-size="14px" fill="STYLE_TEXT_COLOR">`. Each line is one `<text x="0" y="K.ffffffem" xml:space="preserve">...</text>` with K increasing by 1.2 from 1.2. Escape `& < > "`; encode spaces as `&#160;` and tabs as four such entities. Add `<tspan>` only for non-default effective styling, with attributes in foreground/bold/italic/underline order (`fill`, `font-weight`, `font-style`, `text-decoration`). Monokai Python keywords, strings, and function names therefore use fills drawn from `#66d9ef`, `#e6db74`, and `#a6e22e`; style selection changes these fills.

Before text, emit background rectangles for tokens having a non-default background: x in `ch`, y `0.25 + 1.2*lineIndex` em, width in tab-expanded byte characters, height `1.2em`, and id equal to escaped token text. Close with LF, `</g>` LF, `</svg>` LF. Unicode must remain valid UTF-8/XML. The embedded Liberation Mono payload is part of the required formatter asset and must be stable across runs.

## Spec 15

For file operands only, `--check` tokenizes and scans all tokens without formatter output. It always exits 0 after successful lexing, even when errors are found. For every token of exact type `Error`, write to stdout `FILENAME:LINE:COLUMN "GO_ESCAPED_TOKEN_VALUE"` plus LF.

Line starts at 1 and column at 0. After every Unicode code point in every token, increment column; after LF, increment line and reset column to 0. Report all error tokens and do not stop after the first. For the malformed quote used in Go, this produces a single report at column 9 or 12 depending on source position and quotes the token as `"\""`. Valid files produce empty stdout/stderr. File paths are printed exactly as passed. Combining file check mode with trace still suppresses formatted stdout while trace remains on stderr. As stated in Spec 1, stdin is formatted normally even if `--check` is present.

## Spec 16

`--trace` enables tracing on regex lexers without replacing normal formatting. Emit one compact JSON object followed by LF to stderr for each matched lexer rule, while the selected formatter writes normally to stdout. Every record has keys in this order and these types:

```json
{"lexer":"Go","state":"root","rule":5,"pattern":"(import|package)\\b","pos":0,"length":7,"elapsedMs":0.033272}
```

`lexer`, `state`, and `pattern` are strings; `rule`, `pos`, and `length` are integers; `elapsedMs` is numeric and nondeterministic. Positions and lengths follow lexer character positions. For Go input `package main` plus LF, emit exactly four records corresponding to package, space, main, and newline. Without final newline it emits three. The exercised five-line Go function example emits 23; the valid seven-line Go file emits 26; the 12-line Python Fibonacci example emits 106. Do not mix trace lines into stdout. JSON and HTML formatting remain valid when trace is enabled.

## Spec 17

Argument-parser errors use program name `executable`, prefix `executable: error: `, stderr, and status 80. A nonexistent file operand is exactly `executable: error: [<files> ...]: stat PATH: no such file or directory` plus LF. Validation happens before processing, including in a mixed list. An invalid formatter is exactly:

```text
executable: error: --formatter must be one of "html","json","noop","svg","terminal","terminal16","terminal16m","terminal256","terminal8","tokens" but got "VALUE"
```

Runtime/configuration failures use status 1 and the same prefix. This includes style load/build failures and malformed highlight ranges. An invalid explicit lexer alone does not diagnose in lenient mode; it falls back. If default `swapoff` style is also left in effect, the earlier style-selection phase yields the `open swapoff` error described in Spec 6. Never print panics or stack traces for user input.

## Spec 18

Treat input as arbitrary bytes converted to UTF-8 text with Go-string/regex semantics: valid UTF-8, including CJK filenames/content, Arabic/Hebrew, emoji and zero-width joiners, survives after the newline preprocessing described in Spec 4. Invalid UTF-8 bytes encountered by regexp matching become one U+FFFD replacement character per invalid byte in formatted output. In the following exact solarized-dark/default-terminal examples, `<ESC>` is byte 0x1b and the named controls are their single bytes:

```text
input bytes 00 01 02 ff with explicit Go (or a Python filename hint):
<ESC>[33m<NUL><SOH><STX>�<ESC>[0m

input bytes for hello, then 80 81, then world with explicit Go:
<ESC>[33mhello<ESC>[0m<ESC>[33m��<ESC>[0m<ESC>[33mworld<ESC>[0m
```

Preserve UTF-8 BOM behavior of the lexer, files containing only whitespace, files containing only comments, very long identifiers, and NUL/control characters inside strings. Normalize every CRLF and bare CR in mixed line endings to LF. Preserve a missing final newline except for lexer-specific synthesis such as the Makefile recipe in Spec 4. Do not trim formatter output. Binary input with no detectable lexer plus `--fail` exits silently 1; the same bytes with explicit Go or a `.py` filename hint are processed successfully.

For scalability compatibility, Monokai terminal rendering of the regular 821,121-byte/10,000-function Python pattern has 4,770,878 output characters; the 6,722,368-byte/100,000-function pattern has 42,323,681. These sizes arise naturally from exact coalesced tokenization and per-token ANSI reset rules and are useful conformance checks.

## Spec 19

`--xml DIR` exports all serializable built-in regex lexers to an already-existing directory and exits without normal formatting. The directory must already exist. A missing directory reports exactly `executable: error: --xml: stat DIR: no such file or directory`; a regular-file target reports an error containing `"DIR" exists but is not a directory`. Both are nonzero.

Iterate unique registered lexer names from the fixed corpus and serialize their config and state rules as XML. There is no XML declaration: every file begins exactly `<lexer>` LF, followed by two-space-indented `<config>` and later `<rules>` children. Every file ends immediately after the final `</lexer>` bytes, with no trailing LF or other whitespace. Config contains `<name>`, repeated `<alias>`, `<filename>`, and `<mime_type>` values in registry order. Output permissions are owner read/write (`0600`). Produce exactly 280 `.xml` files. Each is nontrivial; Python XML is exactly 20,449 bytes in this snapshot. File name is lowercase display name after replacing every character outside `[A-Za-z0-9_#+-]` with `_`, then `.xml`; thus `C++` is `c++.xml` and `C#` is `c#.xml`.

Four regex lexers cannot be serialized: `Go`, `Haxe`, `Raku`, and `reStructuredText`. Skip them, remain successful, and emit one stderr line per lexer beginning `warning: "NAME": ` and containing `not serialisable`; warning order is unspecified. If a target file already exists, do not overwrite it and emit `warning: FULL_PATH already exists` plus LF. A second complete export therefore gives 280 such warnings and unchanged files.

Required metadata spot checks: Bash is `bash.xml`, name `Bash`, aliases exactly `bash sh ksh zsh shell`; C is `c.xml`, alias exactly `c`, includes filename patterns `*.c` and `*.h`, MIME types exactly `text/x-chdr`, `text/x-csrc`, `image/x-xbitmap`, `image/x-xpixmap`, and exactly eight states named `function`, `string`, `macro`, `if0`, `whitespace`, `statements`, `root`, `statement`; JSON aliases exactly `json`; Rust aliases exactly `rust rs`. Their exported rules are the serializer's state-machine representation, but export/import is not a semantic round trip in this snapshot. Supplying the exported `python.xml` as `-l` loads without a diagnostic, yet JSON formatting of `def f(): pass` is exactly one token, `{"type":"Text","value":"def f(): pass"}`, rather than normal Python tokenization.

## Spec 20

`--profile FILE` creates/truncates FILE, starts native Go CPU profiling before lexing/formatting, and stops/flushed profiling on normal return. It composes with stdin, file operands, multiple files, `--check`, and terminal/HTML/JSON/SVG formatters without changing their functional output. The file must be nonempty and valid for `go tool pprof -top FILE`; that command must exit 0 and identify `File: executable` and profile `Type: cpu`. Substantial input (for example 1,000 short Python functions formatted as HTML) must ordinarily produce more than 100 bytes and actual profile data. Even a very short check-mode operation must leave a syntactically valid profile.

SIGQUIT is not intercepted for graceful profile shutdown. If SIGQUIT arrives while the program is blocked reading stdin during profiling, the native Go runtime handler prints a stack dump to stderr beginning `SIGQUIT: quit` plus LF, exits with status 2, and leaves the already-created profile file at zero bytes. File creation or profiler-start errors are ordinary fatal status-1 diagnostics.
