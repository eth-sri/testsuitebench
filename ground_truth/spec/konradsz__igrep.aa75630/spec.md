# Clarified specification for `executable`

The required artifact is a runnable file named exactly `executable`. It implements version 1.3.0 of a single-command interactive grep program. All behavior below is part of that one executable; there are no subcommands. Unless a section says otherwise, diagnostics go to standard error, successful informational output goes to standard output, and all text is UTF-8.

## Spec 1

The command-line grammar is:

```text
executable [OPTIONS] <PATTERN> [PATHS]...
executable [OPTIONS] --type-list
```

Exactly one of a search `PATTERN` and `--type-list` is required. `PATHS` is a variadic list of files or directories and defaults to the current directory. A bare word is always the pattern, including words such as `add`, `remove`, `list`, `show`, `init`, and `help`; the program has no command-dispatch layer and its help must contain no `Commands:` or `Subcommands:` section.

Options may occur before or after the pattern and may be interleaved with paths. Long value options accept both `--option value` and `--option=value`. Repeatable filters accumulate within one option source; the config/command-line interaction is specified in Spec 7. Boolean short options may be clustered (for example, `-iS` means `-i -S`). The standard `--` end-of-options separator is supported. Tokens after it are positional even when they begin with a hyphen: `executable -- --help` treats `--help` as the search pattern and enters the interactive search instead of printing help.

## Spec 2

`-h` and `--help` print the following text exactly, including indentation, blank lines, final newline, and the unusual usage line, then exit 0 with empty standard error. In otherwise valid combinations, help takes precedence over search and `--type-list` (for example, `--type-list --help` prints help). Values supplied to typed options are still parsed, so an invalid enum value can fail before help is shown. `--help` appearing after the `--` end-of-options separator must not show help.

```text
Interactive Grep

Usage: executable [OPTIONS] --type-list <PATTERN> [PATHS]...

Arguments:
  <PATTERN>   Regular expression used for searching
  [PATHS]...  Files or directories to search. Directories are searched recursively. If not specified, searching starts from current directory

Options:
      --editor <EDITOR>
          Text editor used to open selected match [possible values: vim, neovim, nvim, nano, code, vscode, code-insiders, emacs, emacsclient, hx, helix, subl, sublime-text, micro, intellij, goland, pycharm, less, fresh]
      --custom-command <CUSTOM_COMMAND>
          Custom command used to open selected match. Must contain {file_name} and {line_number} tokens [env: IGREP_CUSTOM_EDITOR=]
      --theme <THEME>
          UI color theme [default: dark] [possible values: light, dark]
  -i, --ignore-case
          Searches case insensitively
  -S, --smart-case
          Searches case insensitively if the pattern is all lowercase. Search case sensitively otherwise
  -., --hidden
          Search hidden files and directories. By default, hidden files and directories are skipped
  -L, --follow
          Follow symbolic links while traversing directories
  -w, --word-regexp
          Only show matches surrounded by word boundaries
  -F, --fixed-strings
          Exact matches with no regex. Useful when searching for a string full of delimiters
  -U, --multiline
          Search with pattern contains newline character ('\n')
  -g, --glob <GLOB>
          Include files and directories for searching that match the given glob. Multiple globs may be provided
      --type-list
          Show all supported file types and their corresponding globs
  -t, --type <TYPE_MATCHING>
          Only search files matching TYPE. Multiple types may be provided
  -T, --type-not <TYPE_NOT>
          Do not search files matching TYPE-NOT. Multiple types-not may be provided
      --context-viewer <CONTEXT_VIEWER>
          Context viewer position at startup [default: none] [possible values: none, vertical, horizontal]
      --sort <SORT_BY>
          Sort results, see ripgrep for details [possible values: path, modified, created, accessed]
      --sortr <SORT_BY_REVERSE>
          Sort results reverse, see ripgrep for details [possible values: path, modified, created, accessed]
  -h, --help
          Print help
  -V, --version
          Print version
```

The help output is plain text without ANSI escape sequences. `--help` appearing after the `--` end-of-options separator is a positional pattern and therefore does not show help.

## Spec 3

`-V` and `--version` print exactly `igrep 1.3.0` followed by one newline, exit 0, and write nothing to standard error. The two forms are byte-for-byte equivalent.

## Spec 4

`--type-list` is a noninteractive mode. It ignores standard input, does not initialize a terminal, exits 0, leaves standard error empty, and prints the exact newline-terminated registry below. Other valid options may accompany it without changing this output, including repeated `--glob`, `--type`, and `--type-not`, search flags, display options, an editor, or an unvalidated custom editor command.

```text
ada: *.adb, *.ads
agda: *.agda, *.lagda
aidl: *.aidl
alire: alire.toml
amake: *.bp, *.mk
asciidoc: *.adoc, *.asc, *.asciidoc
asm: *.S, *.asm, *.s
asp: *.ascx, *.ascx.cs, *.ascx.vb, *.asp, *.aspx, *.aspx.cs, *.aspx.vb
ats: *.ats, *.dats, *.hats, *.sats
avro: *.avdl, *.avpr, *.avsc
awk: *.awk
bat: *.bat
batch: *.bat
bazel: *.BUILD, *.bazel, *.bazelrc, *.bzl, BUILD, MODULE.bazel, WORKSPACE, WORKSPACE.bazel
bitbake: *.bb, *.bbappend, *.bbclass, *.conf, *.inc
brotli: *.br
buildstream: *.bst
bzip2: *.bz2, *.tbz2
c: *.[chH], *.[chH].in, *.cats
cabal: *.cabal
candid: *.did
carp: *.carp
cbor: *.cbor
ceylon: *.ceylon
clojure: *.clj, *.cljc, *.cljs, *.cljx
cmake: *.cmake, CMakeLists.txt
cmd: *.bat, *.cmd
cml: *.cml
coffeescript: *.coffee
config: *.cfg, *.conf, *.config, *.ini
coq: *.v
cpp: *.[ChH], *.[ChH].in, *.[ch]pp, *.[ch]pp.in, *.[ch]xx, *.[ch]xx.in, *.cc, *.cc.in, *.hh, *.hh.in, *.inl
creole: *.creole
crystal: *.cr, *.ecr, Projectfile, shard.yml
cs: *.cs
csharp: *.cs
cshtml: *.cshtml
csproj: *.csproj
css: *.css, *.scss
csv: *.csv
cuda: *.cu, *.cuh
cython: *.pxd, *.pxi, *.pyx
d: *.d
dart: *.dart
devicetree: *.dts, *.dtsi
dhall: *.dhall
diff: *.diff, *.patch
dita: *.dita, *.ditamap, *.ditaval
docker: *Dockerfile*
dockercompose: docker-compose.*.yml, docker-compose.yml
dts: *.dts, *.dtsi
dvc: *.dvc, Dvcfile
ebuild: *.ebuild, *.eclass
edn: *.edn
elisp: *.el
elixir: *.eex, *.ex, *.exs, *.heex, *.leex, *.livemd
elm: *.elm
erb: *.erb
erlang: *.erl, *.hrl
fennel: *.fnl
fidl: *.fidl
fish: *.fish
flatbuffers: *.fbs
fortran: *.F, *.F77, *.F90, *.F95, *.f, *.f77, *.f90, *.f95, *.pfo
fsharp: *.fs, *.fsi, *.fsx
fut: *.fut
gap: *.g, *.gap, *.gd, *.gi, *.tst
gn: *.gn, *.gni
go: *.go
gprbuild: *.gpr
gradle: *.gradle, *.gradle.kts, gradle-wrapper.*, gradle.properties, gradlew, gradlew.bat
graphql: *.graphql, *.graphqls
groovy: *.gradle, *.groovy
gzip: *.gz, *.tgz
h: *.h, *.hh, *.hpp
haml: *.haml
hare: *.ha
haskell: *.c2hs, *.cpphs, *.hs, *.hsc, *.lhs
hbs: *.hbs
hs: *.hs, *.lhs
html: *.ejs, *.htm, *.html
hy: *.hy
idris: *.idr, *.lidr
janet: *.janet
java: *.java, *.jsp, *.jspx, *.properties
jinja: *.j2, *.jinja, *.jinja2
jl: *.jl
js: *.cjs, *.js, *.jsx, *.mjs, *.vue
json: *.json, *.sarif, composer.lock
jsonl: *.jsonl
julia: *.jl
jupyter: *.ipynb, *.jpynb
k: *.k
kotlin: *.kt, *.kts
lean: *.lean
less: *.less
license: *[.-]LICEN[CS]E*, AGPL-*[0-9]*, APACHE-*[0-9]*, BSD-*[0-9]*, CC-BY-*, COPYING, COPYING[.-]*, COPYRIGHT, COPYRIGHT[.-]*, EULA, EULA[.-]*, GFDL-*[0-9]*, GNU-*[0-9]*, GPL-*[0-9]*, LGPL-*[0-9]*, LICEN[CS]E, LICEN[CS]E[.-]*, MIT-*[0-9]*, MPL-*[0-9]*, NOTICE, NOTICE[.-]*, OFL-*[0-9]*, PATENTS, PATENTS[.-]*, UNLICEN[CS]E, UNLICEN[CS]E[.-]*, agpl[.-]*, gpl[.-]*, lgpl[.-]*, licen[cs]e, licen[cs]e.*
lilypond: *.ily, *.ly
lisp: *.el, *.jl, *.lisp, *.lsp, *.sc, *.scm
lock: *.lock, package-lock.json
log: *.log
lua: *.lua
lz4: *.lz4
lzma: *.lzma
m4: *.ac, *.m4
make: *.mak, *.mk, [Gg][Nn][Uu]makefile, [Gg][Nn][Uu]makefile.am, [Gg][Nn][Uu]makefile.in, [Mm]akefile, [Mm]akefile.am, [Mm]akefile.in
mako: *.mako, *.mao
man: *.[0-9][cEFMmpSx], *.[0-9lnpx]
markdown: *.markdown, *.md, *.mdown, *.mdwn, *.mdx, *.mkd, *.mkdn
matlab: *.m
md: *.markdown, *.md, *.mdown, *.mdwn, *.mdx, *.mkd, *.mkdn
meson: meson.build, meson.options, meson_options.txt
minified: *.min.css, *.min.html, *.min.js
mint: *.mint
mk: mkfile
ml: *.ml
motoko: *.mo
msbuild: *.csproj, *.fsproj, *.proj, *.props, *.sln, *.targets, *.vcxproj
nim: *.nim, *.nimble, *.nimf, *.nims
nix: *.nix
objc: *.h, *.m
objcpp: *.h, *.mm
ocaml: *.ml, *.mli, *.mll, *.mly
org: *.org, *.org_archive
pants: BUILD
pascal: *.dpr, *.inc, *.lpr, *.pas, *.pp
pdf: *.pdf
perl: *.PL, *.perl, *.pl, *.plh, *.plx, *.pm, *.t
php: *.php, *.php3, *.php4, *.php5, *.php7, *.php8, *.pht, *.phtml
po: *.po
pod: *.pod
postscript: *.eps, *.ps
prolog: *.P, *.pl, *.pro, *.prolog
protobuf: *.proto
ps: *.cdxml, *.ps1, *.ps1xml, *.psd1, *.psm1
puppet: *.epp, *.erb, *.pp, *.rb
purs: *.purs
py: *.py, *.pyi
python: *.py, *.pyi
qmake: *.prf, *.pri, *.pro
qml: *.qml
r: *.R, *.Rmd, *.Rnw, *.r
racket: *.rkt
raku: *.p6, *.pl6, *.pm6, *.raku, *.rakudoc, *.rakumod, *.rakutest
rdoc: *.rdoc
readme: *README, README*
reasonml: *.re, *.rei
red: *.r, *.red, *.reds
rescript: *.res, *.resi
robot: *.robot
rst: *.rst
ruby: *.gemspec, *.rb, *.rbw, .irbrc, Gemfile, Rakefile, config.ru
rust: *.rs
sass: *.sass, *.scss
scala: *.sbt, *.scala
sh: *.bash, *.bashrc, *.csh, *.cshrc, *.ksh, *.kshrc, *.sh, *.tcsh, *.zsh, .bash_login, .bash_logout, .bash_profile, .bashrc, .cshrc, .kshrc, .login, .logout, .profile, .tcshrc, .zlogin, .zlogout, .zprofile, .zshenv, .zshrc, bash_login, bash_logout, bash_profile, bashrc, profile, zlogin, zlogout, zprofile, zshenv, zshrc
slim: *.skim, *.slim, *.slime
smarty: *.tpl
sml: *.sig, *.sml
solidity: *.sol
soy: *.soy
spark: *.spark
spec: *.spec
sql: *.psql, *.sql
stylus: *.styl
sv: *.h, *.sv, *.svh, *.v, *.vg
svg: *.svg
swift: *.swift
swig: *.def, *.i
systemd: *.automount, *.conf, *.device, *.link, *.mount, *.path, *.scope, *.service, *.slice, *.socket, *.swap, *.target, *.timer
taskpaper: *.taskpaper
tcl: *.tcl
tex: *.bib, *.cls, *.dtx, *.ins, *.ltx, *.sty, *.tex
texinfo: *.texi
textile: *.textile
tf: *.auto.tfvars, *.auto.tfvars.json, *.terraform.lock.hcl, *.terraformrc, *.tf, *.tf.json, *.tfrc, terraform.rc, terraform.tfvars, terraform.tfvars.json
thrift: *.thrift
toml: *.toml, Cargo.lock
ts: *.cts, *.mts, *.ts, *.tsx
twig: *.twig
txt: *.txt
typescript: *.cts, *.mts, *.ts, *.tsx
typoscript: *.ts, *.typoscript
usd: *.usd, *.usda, *.usdc
v: *.v, *.vsh
vala: *.vala
vb: *.vb
vcl: *.vcl
verilog: *.sv, *.svh, *.v, *.vh
vhdl: *.vhd, *.vhdl
vim: *.vim, .gvimrc, .vimrc, _gvimrc, _vimrc, gvimrc, vimrc
vimscript: *.vim, .gvimrc, .vimrc, _gvimrc, _vimrc, gvimrc, vimrc
webidl: *.idl, *.webidl, *.widl
wiki: *.mediawiki, *.wiki
xml: *.dtd, *.rng, *.sch, *.xhtml, *.xjb, *.xml, *.xml.dist, *.xsd, *.xsl, *.xslt
xz: *.txz, *.xz
yacc: *.y
yaml: *.yaml, *.yml
yang: *.yang
z: *.Z
zig: *.zig
zsh: *.zsh, .zlogin, .zlogout, .zprofile, .zshenv, .zshrc, zlogin, zlogout, zprofile, zshenv, zshrc
zstd: *.zst, *.zstd
```

## Spec 5

The supported switches are exactly those shown in Spec 2. Search switches and their aliases are `-i/--ignore-case`, `-S/--smart-case`, `-./--hidden`, `-L/--follow`, `-w/--word-regexp`, `-F/--fixed-strings`, `-U/--multiline`, repeatable `-g/--glob GLOB`, repeatable `-t/--type TYPE`, and repeatable `-T/--type-not TYPE`. Display/configuration switches are `--editor EDITOR`, `--custom-command COMMAND`, `--theme THEME`, `--context-viewer VIEWER`, `--sort KEY`, and `--sortr KEY`.

Editor values are case-sensitive and are exactly: `vim`, `neovim`, `nvim`, `nano`, `code`, `vscode`, `code-insiders`, `emacs`, `emacsclient`, `hx`, `helix`, `subl`, `sublime-text`, `micro`, `intellij`, `goland`, `pycharm`, `less`, `fresh`. Theme values are `light` and `dark`. Context-viewer values are `none`, `vertical`, and `horizontal`. Sort keys are `path`, `modified`, `created`, and `accessed`. Invalid enum values are command-line usage errors. `--editor` and an explicitly supplied `--custom-command` are mutually exclusive.

`--sort` and `--sortr` select forward and reverse sort modes respectively. A search invocation may supply both; the combination is accepted and proceeds into the interactive search rather than producing a command-line conflict. Both are also tolerated alongside `--type-list`, because that mode only emits the registry and does not perform a sort.

## Spec 6

Command-line syntax and choice errors exit 2. They use the lowercase diagnostic format defined below on standard error and leave standard output empty. Required canonical cases are:

```text
error: the following required arguments were not provided:
  --type-list
  <PATTERN>

Usage: executable --type-list <PATTERN> [PATHS]...

For more information, try '--help'.
```

An unknown option has the form `error: unexpected argument '--NAME' found`, ends with `For more information, try '--help'.`, and exits 2. In particular, `executable --type-list --unknown` leaves standard output empty and writes exactly:

```text
error: unexpected argument '--unknown' found

  tip: to pass '--unknown' as a value, use '-- --unknown'

Usage: executable <PATTERN|--type-list> [PATHS]...

For more information, try '--help'.
```

A missing option value states `a value is required for '--OPTION <VALUE_NAME>'`. An invalid choice states `error: invalid value 'VALUE' for '--OPTION <VALUE_NAME>'`, then lists `[possible values: ...]` in the ordering from Spec 5, then the help hint.

For example, the complete invalid-theme diagnostic (before its final newline) is:

```text
error: invalid value 'invalid' for '--theme <THEME>'
  [possible values: light, dark]

For more information, try '--help'.
```

The editor, context-viewer, sort, and reverse-sort diagnostics use this identical layout and their option metavariables and ordered value lists from Specs 2 and 5.

The exact pattern/type-list conflict is:

```text
error: the argument '--type-list' cannot be used with '<PATTERN>'

Usage: executable --type-list <PATTERN> [PATHS]...

For more information, try '--help'.
```

The exact explicit editor/custom-command conflict is:

```text
error: the argument '--editor <EDITOR>' cannot be used with '--custom-command <CUSTOM_COMMAND>'

Usage: executable --type-list --editor <EDITOR> <PATTERN> [PATHS]...

For more information, try '--help'.
```

Runtime/setup failures exit 1 and start with capitalized `Error:` except for the invalid-regex panic described below. A malformed glob, unknown search type, inaccessible input, or terminal failure must fail cleanly without a traceback or panic. In particular, glob `[invalid` reports `Error: error parsing glob '[invalid': unclosed character class; missing ']'`; unknown `-t invalidtype` or `-T invalidtype` reports `Error: unrecognized file type: invalidtype`. A nonexistent input path in a non-TTY invocation must return nonzero and mention an error or that the file does not exist.

Invalid regular expressions are a reference-specific exception rather than a clean validation error. In a non-TTY invocation, both `[invalid` and `(` exit 1, write the cursor-control bytes `\x1b[?25l\x1b[?25h` to standard output, and emit a Rust `thread '<unnamed>' ... panicked` diagnostic on standard error. The diagnostic identifies `src/ig/searcher.rs:<error location>`, contains `Cannot build RegexMatcher`, and is followed by `Error: No such device or address (os error 6)`.

## Spec 7

If `RIPGREP_CONFIG_PATH` names a readable file, read it before command-line search options. Each nonempty, non-comment line is trimmed. A line may be a flag, a separate option value, or an inline `--option=value`. Recognize only the executable's supported search/filter options; ignore unsupported ripgrep options and their value lines instead of passing them to the normal argument parser. Empty lines, whitespace, and lines beginning `#` are ignored. A missing config path and an empty config are silently ignored. A directory path is not ignored: the process exits 101 after a Rust panic at `src/args.rs:<error location>` whose diagnostic contains `Not valid UTF-8: Os { code: 21, kind: IsADirectory, message: "Is a directory" }`.

Config options include boolean short or long forms and value options such as glob and type. Command-line options and supported config options can be used together, subject to the per-filter replacement rules below. Config processing must never prevent `--type-list` from succeeding.

Accumulation does not cross sources for glob filters. If at least one `-g`/`--glob` occurs on the command line, the complete command-line glob list replaces the complete config-file glob list; glob entries from the two sources are not unioned. Other config options remain active. For example, with config contents `-i`, `-g`, `*.txt`, and `--glob=!skip*`, the command line `needle --glob *.md .` retains config `-i` but replaces both config globs with `*.md`, so files matching `*.txt` alone are excluded.

Positive type filters have the same cross-source replacement behavior. If at least one `-t`/`--type` occurs on the command line, the command-line positive type list replaces the config-file positive type list rather than forming a union with it. For example, with config `--type=py`, the command line `--type rust --sort=path needle .` searches Rust files only: among matching `a.py`, `b.rs`, and `c.txt`, it displays only `b.rs` and reports `Found 1 match in 1 file.`.

## Spec 8

Editor configuration may come from `--editor`, `IGREP_EDITOR`, `VISUAL`, or `EDITOR`; custom configuration may come from `--custom-command` or `IGREP_CUSTOM_EDITOR`. Environment editor names obey the same case-sensitive list as `--editor`; if an invalid `IGREP_EDITOR` or `EDITOR` value is selected during a search, exit 1 and leave standard output empty. The diagnostic wording, punctuation, blank line, variant ordering, and final newline are exact. For `EDITOR=invalid_editor` it is:

```text
Error: "invalid_editor" read from $EDITOR, possible variants: [vim, neovim, nvim, nano, code, vscode, code-insiders, emacs, emacsclient, hx, helix, subl, sublime-text, micro, intellij, goland, pycharm, less, fresh]

Caused by:
    invalid variant: invalid_editor
```

For `IGREP_EDITOR=invalid_editor`, only the named variable changes:

```text
Error: "invalid_editor" read from $IGREP_EDITOR, possible variants: [vim, neovim, nvim, nano, code, vscode, code-insiders, emacs, emacsclient, hx, helix, subl, sublime-text, micro, intellij, goland, pycharm, less, fresh]

Caused by:
    invalid variant: invalid_editor
```

Help and type-list do not need an editor and must not fail because an editor environment variable is invalid.

A custom command is split on whitespace into a program and arguments. It must contain exactly one literal `{file_name}` and exactly one literal `{line_number}` anywhere in its arguments; token order and embedding such as `{file_name}:{line_number}` are allowed. Multiple spaces are accepted. A command consisting only of a program fails with `Expected program and its arguments`. Missing or duplicate tokens fail with `Expected one occurrence of '{token}'.`. The canonical error shape is:

```text
Error: Incorrect editor command: 'ORIGINAL COMMAND'

Caused by:
    REASON
```

followed by one newline. Custom-command validation occurs only after command-line parsing has established a search invocation with a pattern. A command supplied without a pattern is not validated: regardless of whether it has no arguments, is missing either token, or duplicates either token, the invocation exits 2, leaves standard output empty, and writes the missing-required-arguments diagnostic. For example, `executable --custom-command 'non_builtin_editor -x'` writes exactly:

```text
error: the following required arguments were not provided:
  --type-list
  <PATTERN>

Usage: executable --type-list --custom-command <CUSTOM_COMMAND> <PATTERN> [PATHS]...

For more information, try '--help'.
```

Custom-command validation also does not run when only printing help/type-list; thus `--type-list --custom-command invalid` succeeds. An explicit CLI custom command overrides `IGREP_CUSTOM_EDITOR`.

If opening a selected match cannot spawn its configured editor, the error is nonfatal and the TUI remains usable. The status message is clipped to the space before the right-aligned counter. At 80 columns, attempting `igrep-editor-that-does-not-exist {file_name} {line_number}` with one result produces this exact 80-column status row (including the four leading and one trailing spaces):

```text
    ERROR    Failed to open editor 'igrep-editor-that-does-not-exist'.    | 1/1 
```

## Spec 9

In search mode, recursively inspect every supplied directory and exactly the supplied files; default to `.` when no paths are given. Skip hidden files/directories and symbolic links by default. `-.`/`--hidden` includes hidden entries, and `-L`/`--follow` follows symlinks. Avoid symlink loops and crashes, handle very long lines safely, retain Unicode filenames/content, and support filenames containing spaces and glob metacharacters.

Collect results as matching source lines. Each result consists of the displayed path, one-based line number, and complete source line (truncated only to fit the viewport). Preserve whether the input root was relative or absolute when displaying a discovered path: searching `.` displays headers relative to `.`, while an absolute directory or explicit absolute file produces absolute headers. Results are grouped by file, with the path as a header followed by lines formatted ` N: CONTENT`. For a multiline match, include each line covered by the match as a result line. The bottom count therefore counts displayed matching lines.

## Spec 10

The default pattern is a regular expression and matching is case-sensitive. Support ordinary literals; `.` as any character; bracket character classes; `^`/`$` line anchors; `|` alternation; parenthesized groups; `*`, `+`, `?`, and bounded quantifiers; backslash escapes; and Unicode text. For example, `[a-z]+@[a-z]+\.(com|org)` matches lowercase `.com` and `.org` email addresses, while `^def` matches `def` only at the start of a line.

`-i` makes matching case-insensitive. `-S` makes an all-lowercase pattern case-insensitive but a pattern containing uppercase letters case-sensitive. `-w` requires a whole-word match (so `hello` does not match `helloworld` or `hello_world`). `-F` treats every regex metacharacter literally. These modifiers combine (for example `-i -w` or `-i -F`). `-U` enables a pattern containing `\n` to match across physical line boundaries. Invalid expressions such as an unclosed bracket or unmatched parenthesis follow the panic behavior specified in Spec 6 rather than producing a clean regex diagnostic.

## Spec 11

Within one option source, each positive `-g/--glob` adds an included glob and multiple positive globs form a union. A glob beginning `!` excludes matching paths. Standard `*`, `**`, `?`, and bracket classes are supported. Type filters use the registry from Spec 4: within one option source, multiple `-t` types form a union, multiple `-T` types exclude all named types, and positive/negative type filters may be combined with each other and with globs. Cross-source replacement is specified in Spec 7. During real search, malformed globs and unknown type names are errors; during `--type-list`, filter values are accepted without affecting registry output.

## Spec 12

The result order is file-oriented. With no explicit sort, the program preserves the searcher's discovery order; it does not sort files by modification time. In the canonical two-file case where `z-old.txt` has mtime 1600000000 and `a-new.txt` has mtime 1700000000, `z-old.txt` is displayed before `a-new.txt`. In the TUI, `n`, `m`, `c`, and `a` rerun the same search using path/name, modification-time, creation-time, and access-time modes respectively. `n` produces ascending alphabetical paths; `m`, `c`, and `a` retain all matches and finish cleanly. Repeating a sort key toggles its direction. The selected position resets to a valid result after a successful rerun.

On the reference filesystem, runtime creation-time sorting succeeds. With one result, pressing `c` first changes the visible state to `SEARCHING` with `0/0`, then returns to `FINISHED` with `Found 1 match in 1 file.` and `1/1`; the process remains alive and emits no creation-time panic.

## Spec 13

Search mode is a full-screen interactive terminal UI. It must start and remain responsive when attached to a PTY. At the standard 80-by-24 terminal size it draws a single rounded-border results box occupying rows 1–23 and all 80 columns, then a one-line status bar on row 24. The content area is 78 columns by 21 rows. File headers and ` N: CONTENT` rows are left aligned and space-padded; overflowing paths and lines are clipped to the available width. Unused rows are blank inside the border.

The status line has a state label, message, and a right-aligned `| CURRENT/TOTAL` counter. After search completion it says `FINISHED`. Nonempty summaries use correct singular/plural grammar: `Found 1 match in 1 file.`, `Found N matches in 1 file.`, or `Found N matches in M files.`. The counter is one-based, initially `1/N`. The currently selected result is visibly highlighted. Searching 50 one-line files must report exactly `Found 50 matches in 50 files.` and navigation must update `1/50`, `6/50`, and `50/50` correctly.

## Spec 14

No matches, an empty directory, and a nonexistent directory presented in the interactive TUI all produce the same stable empty state rather than exiting or panicking. At 80-by-24 the exact visible screen is:

```text
╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
  FINISHED   No matches found.                                            | 0/0 
```

The final status row above is exactly 80 columns and includes one ASCII space after `0/0`.

Navigation keys in this state do nothing, and quit keys still work.

## Spec 15

Normal-mode match navigation is bounded, never wrapping: `j` selects the next match, `k` selects the previous match, and `G` selects the last match. `l` or PageDown selects the first match in the next file; PageUp selects the first match in the previous file. At either end, extra navigation leaves both screen and counter unchanged. A one-result list always remains `1/1`. When the selection moves outside the viewport, scroll enough to keep it visible. The keymap also advertises Down/Up as match movement, Right/Left as file movement, `gg`/Home as first-match movement, and End as last-match movement.

`q`, Escape, and Ctrl+C cleanly restore the terminal and terminate promptly. Unrecognized keys do not crash, exit, or move the selection.

## Spec 16

The context viewer starts as selected by `--context-viewer`, default `none`. `v` toggles a vertical split and `s` toggles a horizontal split; pressing the active toggle again returns to no context. The second pane shows the selected source file around the selected line, scrolls/changes with selection, preserves Unicode, and syntax-highlights recognized source types. `+` increases and `-` decreases its size, bounded to usable dimensions. The vertical layout uses separate, independently rounded left-result and right-source boxes rather than one outer frame with a central divider. At 80 columns its top row is exactly the following in both themes, and content rows use adjacent `││` pane edges:

```text
╭──────────────────────────────────────╮╭──────────────────────────────────────╮
```

Horizontal mode splits the display into upper result and lower source panes.

## Spec 17

`/` and F5 open a centered search popup over (without erasing) the current result screen. Its title is `Regex Pattern`, its editable buffer initially contains the current pattern, and the insertion cursor begins after the last character. Printable keys insert at the cursor; Left/Right move within bounds; Backspace removes the character before the cursor and moves left; Delete removes the character at the cursor. A long value is horizontally windowed to fit and is shown with a leading Unicode ellipsis, e.g. `…ERY_LONG_PATTERN_THAT_EXCEEDS_WIDTH`.

At 80-by-24 the popup is exactly 40 columns wide and three rows high, with its top-left corner at column 21, row 11 (one-based terminal coordinates). It uses `┌─┐`, `│ │`, and `└─┘`; the title replaces the centered part of the top rule. The editable interior is 38 columns wide, including its one leading and one trailing padding space. Thus the complete terminal rows crossed by an open popup containing `ERROR` are:

```text
│                   ┌─────────── Regex Pattern ────────────┐                   │
│                   │ ERROR                                │                   │
│                   └──────────────────────────────────────┘                   │
```

Escape closes the popup and discards edits, leaving results and active pattern unchanged. Enter adopts the edited pattern, closes the popup, reruns the search with all existing flags/paths, resets selection, and updates results/counts. The adopted pattern persists the next time either popup key is used.

## Spec 18

`?` and F1 toggle a centered keymap popup titled `igrep 1.3.0`. Opening resets scrolling to the top. In popup mode, `j`/Down and `k`/Up scroll vertically with saturating boundaries; `l`/Right and `h`/Left scroll horizontally with saturating boundaries. At ordinary width the content fits horizontally, so horizontal keys produce no visible change. The complete scrollable key table contains these rows and spacing groups:

```text
Key(s)             │ Action
───────────────────┼───────────────────────────────────────
q, Esc, Ctrl+c     │ Quit

?, F1              │ Open/close the keymap popup
Down, j            │ Scroll down in the keymap popup
Up, k              │ Scroll up in the keymap popup
Right, l           │ Scroll right in the keymap popup
Left, h            │ Scroll left in the keymap popup

Down, j            │ Select next match
Up,k               │ Select previous match
Right, l, PageDown │ Select match in next file
Left, h, PageUp    │ Select match in previous file
gg, Home           │ Jump to the first match
Shift-g, End       │ Jump to the last match
Enter              │ Open current file
```

At the initial top scroll position, the visible table ends with `gg, Home           │ Jump to the first match`; the `Shift-g, End` and `Enter` rows are clipped below the viewport. One `j` or Down reveals the `Shift-g, End` row, and a second reveals the `Enter` row.

The popup uses a 63-column by 19-row square-cornered box centered in the results pane. Its border uses `┌` and `┐` at the top and `└` and `┘` at the bottom. At 80-by-24 its corners are columns 9 and 71 and rows 3 and 21 (one-based), leaving the underlying file header/result prefixes visible around it. While the popup is open, `q` closes it and restores the unchanged result screen without terminating the process. A subsequent `q` in normal mode quits.

## Spec 19

The default theme is `dark`; omitting `--theme` is visually identical to `--theme dark`. Both themes preserve the same text geometry. Dark uses RGB `(58,58,58)` for selected-result and bottom-bar backgrounds, RGB `(147,147,147)` for bottom-bar text, and a `base16-ocean.dark` syntax theme. Light uses RGB `(220,220,220)` for selection, terminal-default bottom-bar colors, and `base16-ocean.light` syntax highlighting. The `FINISHED` state badge is bold with green background and black foreground. Theme coloring must be emitted through terminal styling without contaminating non-TTY help/version/type-list output.

## Spec 20

The implementation must be robust under rapid scripted key input and asynchronous search completion. Once the visible state says `FINISHED`, snapshots are deterministic: identical files, metadata, arguments, dimensions, and key sequences produce identical path grouping, rows, padding, counters, popup placement, and status text. All terminal modes and cursor/display state are restored on every normal quit and handled failure. The program must not hang when its input is a file, a deep tree, dozens of files, long lines, Unicode content, or zero results.
