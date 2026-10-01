# Universal Ctags 6.2.0 command-line executable

## Spec 1: Deliverable and invocation

Provide one executable file named exactly `executable`. It must be directly runnable on a Linux/POSIX system as:

```text
./executable [options] [file ...]
```

The executable is a self-contained Universal Ctags-compatible tag generator. It reads source files, identifies named language objects, and writes tag records. It must not require a repository build step, another project-owned command, or files outside the delivered artifact. It may use ordinary facilities already present in the execution environment.

Unless an error is specified below, successful informational and tagging operations exit 0. Fatal option, configuration, or output errors exit 1. Diagnostics go to standard error. Data goes to the destination prescribed by the selected output mode; in particular, normal native tagging without `-f` or `-o` writes to the working-directory file `tags` and leaves standard output empty, as detailed in Spec 3. Diagnostics identify the program by the basename `executable`.

## Spec 2: Identification and help

- `--version` exits 0 and identifies `Universal Ctags`, version `6.2.0`, copyright information, and the project URL on a line containing the literal label `URL: https://ctags.io/`. It also contains a `Compiled:` line, an `Output version:` line, and an `Optional compiled features:` line.
- `--version=LANGUAGE` reports a parser version in the form `parser/LANGUAGE:`; this is required for at least C and Python.
- `--help` and `-?` print usage containing `Usage:`, `[options]`, and the case-sensitive section heading `Input/Output Options` (with no colon). The `-?` output itself lists both `--help` and `--help-full`. `--help-full` additionally documents private features including `--_interactive` and `--_dump-options`.
- `--license` exits 0 and identifies the GNU General Public License and the program as free software.
- With neither an informational action nor input files, exit 1 and write `No files specified. Try "executable --help".` to standard error.
- An unknown long or short option is fatal and is reported as `Unknown option: OPTION`. A lone `-` is an unknown option; it is not raw source input.

## Spec 3: Core tag model and default u-ctags output

For each input, detect its language and emit definitions appropriate to that language: functions and methods, classes/interfaces/traits, modules/namespaces, variables/constants, types/typedefs, structs/unions and members, enums and enumerators, macros, labels, and other language-specific declarations. Nested declarations retain their containing scope, and C-family parsers retain types, access, inheritance, signatures, and file-scope status where applicable.

The normal format is u-ctags format 2. Each ordinary record is one newline-terminated, tab-separated line:

```text
name<TAB>input-path<TAB>excmd;"<TAB>kind[<TAB>field:value ...]
```

For an ordinary definition record, the default `excmd` is an escaped anchored search pattern containing the declaration's source line, such as `/^int add(int a, int b) {$/`. `-F` selects forward `/.../` patterns and `-B` backward `?...?` patterns. `--excmd=number` uses a one-based source line such as `1;"`; `--excmd=pattern` uses patterns. The additionally accepted values are `mix` and `combine`. An invalid value is fatal. `--pattern-length-limit=N` truncates stored patterns, with 0 meaning unlimited; a nonnumeric value is fatal.

Pattern anchoring reflects whether the physical source line has a line terminator. A newline-terminated declaration such as `void func() {}` is serialized as `/^void func() {}$/;"`; when that declaration is the unterminated final line, it is serialized as `/^void func() {}/;"`, without the trailing `$`.

Include-reference records are an exception to the ordinary-definition end anchoring. With `--extras=+r --fields=+r -o -`, newline-terminated `#include <stdio.h>` and `#include "local.h"` lines have the following record bodies (apart from the input-path column), with no `$` before the closing pattern delimiter:

```text
stdio.h<TAB>PATH<TAB>/^#include <stdio.h>/;"<TAB>h<TAB>roles:system
local.h<TAB>PATH<TAB>/^#include "local.h"/;"<TAB>h<TAB>roles:local
```

The default enabled fields are `N` (name), `F` (input), `P` (pattern), `T` (epoch), `f` (file), `k` (short kind), `s` (legacy native scope), and `t` (type reference). In particular, `S` (signature), `Z` (`scope:`-prefixed scope), `l` (language), and `n` (line) are off by default. Consequently, with default fields, C function records contain the return type as `typeref:typename:void` or `typeref:typename:int` and do not contain `signature:`. Simple JavaScript and Python function records likewise end after the short `f` kind and do not acquire a default `signature:()` field. The default legacy scope field is written directly as `struct:MyStruct`, not as `scope:struct:MyStruct`. File-restricted records end in `file:`. For this input:

```c
struct MyStruct {
    int field;
};
void func() {}
```

output with the explicit standard-output destination `-o -`, apart from the input-path column, is exactly:

```text
MyStruct<TAB>PATH<TAB>/^struct MyStruct {$/;"<TAB>s<TAB>file:
field<TAB>PATH<TAB>/^    int field;$/;"<TAB>m<TAB>struct:MyStruct<TAB>typeref:typename:int<TAB>file:
func<TAB>PATH<TAB>/^void func() {}$/;"<TAB>f<TAB>typeref:typename:void
```

Enabled extension fields retain Universal Ctags' serialization order. For example, adding `n` to defaults places `line:N` before the default `typeref`, and adding both `n` and `l` gives `line:N`, then `language:C`, then scope/type/file fields. Adding access field `a` places `access:` after the legacy scope, `typeref`, and `file:` fields. With `--fields=+a`, the observed `private_var` member of class `Example` has extension fields in the order `m`, `class:Example`, `typeref:typename:int`, `file:`, `access:private`; the `Example` class record itself ends in `c`, `file:`. Adding end field `e` likewise places `end:N` after applicable default scope/type/file fields, and `--put-field-prefix` changes that field to `UCTAGSend:N` without changing its position. Option-file and repeated command-line field additions preserve these defaults rather than substituting `signature` for `typeref`.

`--format=1` omits format-2 `;"` extension-field syntax; `--format=2` is the default. `--format=0` is also accepted, exits 0 without a diagnostic, and uses the same extension-free ordinary-record shape as format 1. In a normal output file it identifies itself with the exact pseudo-tag `!_TAG_FILE_FORMAT<TAB>0<TAB>/unknown format/`. Values other than 0, 1, and 2 are fatal. `--output-format=u-ctags` selects this native form and `--output-format=e-ctags` selects its compatible e-ctags variant. In an output file the selected mode is identified exactly as, respectively:

```text
!_TAG_OUTPUT_MODE	u-ctags	/u-ctags or e-ctags/
!_TAG_OUTPUT_MODE	e-ctags	/u-ctags or e-ctags/
```

`-f PATH` and `-o PATH` select the output destination and are equivalent. `PATH=-` means standard output. For normal native tagging, when neither option is given, the destination is a file named exactly `tags` in the process working directory; the operation exits 0 and writes nothing to standard output. The generated `tags` file contains the ordinary records and metadata described below. (Output modes that expressly select standard output, including JSON and xref, retain their mode-specific behavior.) Standard-output tag streams do not include pseudo-tag headers by default. A normal output file includes metadata pseudo-tags, including at least:

```text
!_TAG_FILE_FORMAT	2	/extended format/
!_TAG_FILE_SORTED	1 or 2 or 0	/0=unsorted, 1=sorted, 2=foldcase/
!_TAG_PROGRAM_NAME	Universal Ctags	/Derived from Exuberant Ctags/
```

It also includes the applicable kind, extra, and field description pseudo-tags, sorted by pseudo-tag name. For a C input, the beginning of the default metadata block is exactly:

```text
!_TAG_EXTRA_DESCRIPTION	anonymous	/Include tags for non-named objects like lambda/
!_TAG_EXTRA_DESCRIPTION	fileScope	/Include tags of file scope/
!_TAG_EXTRA_DESCRIPTION	pseudo	/Include pseudo tags/
!_TAG_EXTRA_DESCRIPTION	subparser	/Include tags generated by subparsers/
!_TAG_FIELD_DESCRIPTION	epoch	/the last modified time of the input file (only for F\/file kind tag)/
!_TAG_FIELD_DESCRIPTION	file	/File-restricted scoping/
!_TAG_FIELD_DESCRIPTION	input	/input file/
!_TAG_FIELD_DESCRIPTION	name	/tag name/
!_TAG_FIELD_DESCRIPTION	pattern	/pattern/
!_TAG_FIELD_DESCRIPTION	typeref	/Type and name of a variable or typedef/
!_TAG_FILE_FORMAT	2	/extended format; --format=1 will not append ;" to lines/
!_TAG_FILE_SORTED	1	/0=unsorted, 1=sorted, 2=foldcase/
!_TAG_KIND_DESCRIPTION!C	d,macro	/macro definitions/
!_TAG_KIND_DESCRIPTION!C	e,enumerator	/enumerators (values inside an enumeration)/
!_TAG_KIND_DESCRIPTION!C	f,function	/function definitions/
!_TAG_KIND_DESCRIPTION!C	g,enum	/enumeration names/
!_TAG_KIND_DESCRIPTION!C	h,header	/included header files/
!_TAG_KIND_DESCRIPTION!C	m,member	/struct, and union members/
!_TAG_KIND_DESCRIPTION!C	s,struct	/structure names/
!_TAG_KIND_DESCRIPTION!C	t,typedef	/typedefs/
```

`--pseudo-tags=*` enables the full pseudo-tag set; individual entries may be removed with, for example, `--pseudo-tags=-TAG_FILE_FORMAT`. `--extras=-p` suppresses all pseudo-tags. Empty source files still produce a valid metadata-only file, while the corresponding stream to stdout has no ordinary records.

The output path must be writable and must not be an existing directory. A name beginning with `-`, other than the special name `-`, is rejected. If `-f`/`-o` is repeated, warn that the last value is used. A missing output directory is fatal with a `cannot open tag file` diagnostic. The exact diagnostics for these cases are specified in Spec 15.

## Spec 4: Sorting, appending, paths, fields, and extras

Native tags are sorted bytewise by name by default. `--sort=yes` requests that order; `-u` and `--sort=no` preserve parser/source order; and `--sort=f`, `--sort=fold`, and `--sort=foldcase` are identical case-folded ordering modes. Foldcase mode treats names differing only by case as duplicates and retains the first source occurrence. Thus source declarations `Apple` followed by `apple` produce only `Apple` under each of the three foldcase spellings; reversing those declarations produces only `apple`. For source-order names `Zoo`, `Apple`, `zebra`, `apple`, the complete foldcase result is `Apple`, `zebra`, `Zoo`. Invalid sort values are fatal. Sorting is global across multiple files. The file header's sorted value is 1, 0, or 2 respectively.

`-a`, `--append`, and `--append=yes` append to an existing tag file while retaining all prior records. The target must already look like the selected tag-file format; otherwise fail with text explaining that it `doesn't look like a tag file` and that the program will `refuse to overwrite` it. With default sorting, appending an `alpha` record to a sorted file containing `zulu` rewrites the ordinary records in `alpha`, `zulu` order and retains the exact marker `!_TAG_FILE_SORTED<TAB>1<TAB>/0=unsorted, 1=sorted, 2=foldcase/`; it does not change that marker to 0. Appending is invalid with stdout and with default stdout-oriented JSON output, producing `append mode is not compatible with tags to stdout`. Etags files may be appended in etags form.

Explicit-file and filter-mode output preserves the spelling of input paths; recursively discovered paths use the normalization specified in Spec 11. `--tag-relative=always` forces paths relative to the tag file/current context, and `--tag-relative=never` forces absolute paths. `yes` and `no` are accepted but are not aliases for `always` and `never`: with `-o -` and an explicitly absolute input, both preserve that absolute path, while `always` renders it relative. Any other value is fatal with `Invalid value for "tag-relative" option`.

`--fields=SPEC` selects general extension fields. A leading `+` adds and `-` removes; repeated specifications accumulate; `*` enables all fields. Both one-letter selectors and `{longName}` selectors are supported in this general form. `--fields-LANGUAGE=SPEC` instead selects parser-specific fields for that language and accepts only brace-delimited long names; it does not accept the one-letter selectors for general fields. In particular, `--fields-C=+nl INPUT` exits 1, emits no tags, and writes `executable: only long name can be used in per language field spec: 'n'`; use `--fields=+nl` for the general line and language fields.

The fixed `N` (name), `F` (input), and `P` (pattern) fields occupy the mandatory columns of a native tag record rather than becoming `key:value` extension fields. Consequently, `--fields=+l{input}` on a C variable adds `language:C`, while its input remains solely in the second, input-path column; it does not add an `input:` extension field. Evaluated extension fields include:

- `n` line number (`line:N`), `l` language (`language:C`), `k` short kind, `K` long kind name, and `z`, which prefixes whichever kind form is selected with `kind:`. Since `k` is enabled by default, `--fields=+z` alone renders a C function's kind column as `kind:f`, while `--fields=+K` renders that column as `function`;
- `a` access, `i` inheritance, `S` normalized signature, `t` type reference, `s` scope, `Z` scope with kind, and `p` scope kind. In native tags, `p` has no separate serialized field; it is useful in xref and JSON output. For `class Box { int value; };`, `--fields=-s --fields=+Zp` renders the member fields as `m<TAB>scope:class:Box<TAB>typeref:typename:int<TAB>file:` and does not add `scopeKind:class`. That invocation also writes, in order, `executable: Warning: though Z/scope field is enabled, s field is not enabled` and `executable: Warning: enable the s field to make the Z/scope field printable`;
- `r` roles, `e` end line, `E` extras, `f` file-restriction information, and `C` compact input text for xref output. The fixed `{input}` field is represented by the input-path column as described above.
- the Python parser's long-name field `{decorators}`. It is off by default; `--fields-Python=+{decorators}` is accepted and emits values such as `decorators:staticmethod`, `decorators:classmethod`, and `decorators:property` on the corresponding class-member records.

For example, a private `int` member of class `Base` can carry `access:private`, `typeref:typename:int`, and `scope:class:Base`; a derived class carries `inherits:Base`; and a function may carry `signature:(int x,const char * str)`. With all fields selected, records expose kind, line, language, typeref, signature, roles, and end where applicable. `--put-field-prefix` prefixes implementation-specific fields such as `end` as `UCTAGSend`.

Unknown brace-delimited field names are fatal (`no such field`), as are nested opening braces and unmatched closing braces. An unmatched opening brace at the end is treated differently: `--fields=+{name INPUT` exits 0 without a diagnostic, produces the normal tag output, and leaves the default field selection unchanged. Unsupported single-character selectors warn but are not fatal.

`--extras=SPEC` and `--extras-LANGUAGE=SPEC` use the same leading additive/removal operators, but their selector syntax differs. The general form accepts short letters, whereas the per-language form accepts only brace-delimited long names. In particular, `--extras-C=+r --fields=+r -o - INPUT` exits 1, emits no tags, and writes `executable: only long name can be used in per language extra spec: 'r'`. Required general extras are file-scope (`F`), input-file tags (`f`, including epoch metadata), reference tags (`r`), qualified tags (`q`, such as `MyClass.method`), anonymous tags, and pseudo-tags (`p`). `--extras=*` enables all. When `{anonymous}` is enabled, a C anonymous struct receives a visible generated name beginning with `__anon` followed by 12 lowercase hexadecimal digits, such as `__anonf8237e970108`; typedef/member `typeref` and scope fields use that same generated name. Distinct anonymous objects receive distinct generated names. Removing file-scope tags suppresses private/static/file-local declarations without suppressing public symbols. Reference tags distinguish, for example, C system includes (`roles:system`) from quoted local includes (`roles:local`). `--fields=+E` exposes an `extras:` field.

## Spec 5: JSON

`--output-format=json` emits newline-delimited JSON, one object per line. Each tag object has `_type: "tag"`, `name`, `path`, and a long `kind`; it normally also has a source `pattern`. Applicable enabled/default metadata is represented as native JSON properties, including `line`, `file`, `typeref`, `scope`, `scopeKind`, `signature`, `access`, and `inherits`. Output-file JSON also contains `_type: "ptag"` metadata such as `TAG_PROGRAM_NAME` or `JSON_OUTPUT_VERSION`. Objects must be valid JSON and use deterministic Universal-Ctags field ordering and serialization.

## Spec 6: Cross-reference output

`-x` and `--output-format=xref` write a human-readable table to standard output and do not create a `tags` file. The default columns identify name, long kind, one-based line, exact input filename, and compact source line. C xref output covers macros, enums/enumerators, structs/members, typedefs, functions, and variables; Python covers classes, functions, and methods. The compact source text shows a declaration's signature when it is present in that line. Default Python method rows do not add the containing class scope: for a method `meth` in class `C`, the row identifies `meth`, kind `member`, its line and input, and source text `def meth(self):`, but contains no separate `C` field.

`--format=1` also changes the default xref layout: it omits the long-kind column, leaving name, line, input filename, and compact source text. For example, the format-1 row for `int x;` starts with `x`, then line `1`, whereas the format-2 row has `variable` between `x` and `1`.

`--_xformat=FORMAT` replaces the xref layout. Implement these conversions: `%N` name, `%K` long kind, `%n` line, `%F` exact input path, `%C` compact source text, `%l` language, `%Z` scope, and `%S` signature. Literal separators, tabs, and surrounding text are preserved. Width is a minimum, not a maximum: positive widths right-justify shorter values and negative widths left-justify them, but neither truncates a longer value. For name `alphabet`, `%10N` produces two leading spaces followed by `alphabet`, while `%3N` still produces the complete `alphabet`.

In custom xref output, `%K` renders a C++ class method's long kind as `function`, not `member`, while `%Z` renders its containing class name. Thus `--_xformat=%N %K %Z` renders a method named `method` in `MyClass` exactly as `method function MyClass`.

## Spec 7: Etags

`-e` and `--output-format=etags` generate Emacs TAGS data. The default filename is `TAGS`; `-o -` is allowed. Each input has a form-feed section headed by `filename,byte-count`, followed by entries using the source snippet, DEL (`0x7f`), tag name/kind suffix where required, SOH (`0x01`), one-based line, and byte offset. Section byte counts must equal the encoded entry bytes. Multiple inputs produce multiple sections, including a section for an empty input. C, Python, and Ada tags are supported; Ada kind suffixes include function `/f`, procedure `/p`, package spec `/s`, package body `/b`, and type `/t`. For the following five-line `x.ads` input, the range type is emitted rather than omitted:

```ada
package Demo is
 function F return Integer;
 procedure P;
 type Number is range 1 .. 10;
end Demo;
```

Its section header is `x.ads,132`, and the range-type entry has source snippet ` type Number is range 1 .. 10;`, suffix `Number/t`, line 4, and byte offset 58. `--pattern-length-limit` also limits etags source snippets. `--etags-include=PATH` emits an include section for another TAGS file.

## Spec 8: Language detection, selection, and catalog

`--print-language FILE...` writes exactly one line per input in the form `input-spelling: LANGUAGE`, or `NONE` when no enabled parser applies. Extension matching is case-sensitive: `.py` maps to Python while `.PY` does not. Required basic mappings include `.c` to C, `.py`/`.pyx`/`.pxd`/`.pxi`/`.scons`/`.wsgi` to Python, `.js` to JavaScript, `.rb` to Ruby, `.go` to Go, `.rs` to Rust, and filename patterns `[Mm]akefile` and `GNUmakefile` to Make.

Executable extensionless files may be detected from shebangs (for example `/usr/bin/env python3` as Python). Non-executable extensionless files do not use their shebang by default. `-G`/`--guess-language-eagerly` enables shebang and Emacs/Vim modeline detection for such files, including shell scripts as `Sh`. Vim modelines may occur at the start or end of a file. Empty `.py` files are still Python.

`--language-force=NAME` overrides detection for both printing and parsing; names are case-insensitive, but aliases such as `js` are not accepted here. `auto` restores detection. An unknown forced language is fatal. Forcing a parser disabled by `--languages` is fatal when an input is processed; without an input file, the ordinary no-files diagnostic takes precedence, as specified in Spec 15. `--languages=A,B` enables only that set, `+NAME` adds, `-NAME` removes, and `-all` disables every parser. An unknown name in `--languages` warns, leaves processing operational, and may result in `NONE`.

`--langmap=LANG:+.ext`/`--map-LANG=+.ext` adds an extension. `--alias-LANG=+ALIAS` instead adds a name alias for the language and does not add an extension mapping. Concretely, `--alias-Python=+.special --list-aliases=Python` adds the line `.special`, but `--alias-Python=+.special --print-language x.special` exits 0 and prints exactly `x.special: NONE`; use `--langmap` or `--map` to map that filename extension. Unterminated parenthesized filename patterns and `%...%` filename regular expressions are fatal. `-h default` restores default header suffixes, while `-h +.suffix` adds to the header-suffix list but does not add a language-detection mapping: `-h +.zzh --print-language thing.zzh` exits 0 and prints exactly `thing.zzh: NONE`. Passing an existing filename as the suffix list is rejected as `-h: Invalid list`.

The built-in `--list-languages` catalog is alphabetical and consists of these 169 entries; disabled entries retain their marker:

```text
Abaqus Abc Ada AnsiblePlaybook Ant Asciidoc Asm Asp Autoconf AutoIt Automake Awk Basic Bats BETA BibLaTeX BibTeX C C# C++ Cargo[disabled] Clojure CMake Cobol CobolFree CobolVariable CPreProcessor CSS Ctags CUDA D DBusIntrospect DBusService Diff DosBatch DTD DTS Eiffel Elixir Elm EmacsLisp Erlang Falcon Flex Forth Fortran FrontMatter FunctionParameters Fypp Gdbinit GDScript GemSpec Glade Go GoMod GPerf Haskell Haxe HTML I18nRubyGem Iniconf Inko IPythonCell ITcl Java JavaProperties JavaScript JNI JSON Julia Kconfig Kotlin LdScript LEX Lisp LiterateHaskell Lua M4 Make Man Markdown MatLab Maven2 Meson MesonOptions Moose Myrddin Nftables NSIS ObjectiveC OCaml Odin OpenAPI Org Pascal Passwd Perl Perl6 PHP PkgConfig PlistXML Pod PowerShell Prolog Protobuf PuppetManifest Python PythonEntryPoints PythonLoggingConfig QemuHX QtMoc Quarto R R6Class Rake Raku RelaxNG ReStructuredText REXX RMarkdown Robot RpmMacros RpmSpec RSpec Ruby Rust S4Class Scdoc Scheme SCSS SELinuxInterface SELinuxTypeEnforcement Sh SINEX SLang SML SQL SVG SystemdUnit SystemTap SystemVerilog Tcl TclOO Terraform TerraformVariables Tex TeXBeamer Thrift TOML[disabled] TTCN Txt2tags TypeScript TypeSpec Unknown[disabled] V Varlink Vera Verilog VHDL Vim WindRes XML XRC XSLT YACC Yaml YumRepo Zephir Zsh
```

Here `Cargo[disabled]`, `TOML[disabled]`, and `Unknown[disabled]` are displayed as `Cargo [disabled]`, `TOML [disabled]`, and `Unknown [disabled]`, one language per line. `--languages=+TOML` enables TOML detection.

The parser must meaningfully recognize representative declarations/headings in the following evaluated languages: Ada, Asciidoc, Asm, Asp, AutoIt, Bats, BibTeX, C, C#, C++, Clojure, CMake, Cobol, CSS, CUDA, D, DTD, Eiffel, Elixir, Elm, Erlang, Forth, Gdbinit, GDScript, Go, GoMod, Haxe, HTML, IPythonCell, ITcl, Java, JavaScript, Julia, Kconfig, LEX/Flex input, Lisp, Make, Man, NSIS, ObjectiveC, OCaml, Odin, Org, Pascal, Passwd, Perl, PkgConfig, PowerShell, Prolog, Protobuf, Python, R, Raku, ReStructuredText, Robot, RpmSpec, Ruby, Rust, Scheme, Sh, SML, SystemVerilog, Terraform, Tex, Thrift, TTCN, Txt2tags, TypeSpec, V, Vera, Verilog, and VHDL. “Meaningfully” means emitting the natural names from ordinary examples: functions/methods, types/classes/modules, services/interfaces, records/structs/enums, labels, tests/keywords, configuration objects, and document section titles as appropriate. CSS ID-selector names retain their leading sigil: forcing CSS on `#header { color: red; }` emits the tag name `#header`, with kind `i`. The evaluated Varlink exception is precise: forcing Varlink on an input containing `interface org.example.demo` exits 0 but emits no ordinary tag record (the default `tags` destination still contains metadata). C/C++ additionally cover macros, includes, bitfields, unions, templates, namespaces, inheritance, operators, pure-virtual prototypes, and goto labels. In the evaluated advanced C++ input, however, the namespace-scope declaration `extern int external_value;` produces no `external_value` record even with `--extras=+r --fields=+iSra --kinds-C++=+cp`. Python covers decorators and class hierarchies. JavaScript covers exported async functions, classes, methods, and arrow functions, but the default import in `import value from 'pkg';` produces no `value` record; the accompanying `export async function load() {}`, class `Box` with `method`, and `const arrow = () => 1` produce `load`, `Box`, `method`, and `arrow`. Go covers interfaces, structs, and receiver methods.

## Spec 9: Listing and description operations

Listing actions exit 0 without source inputs. Unless an exception is stated below or `--with-list-header=no` is given, full/tabular listings include a `#` header. `--machinable` uses tab-separated columns. Support:

- `--list-languages`, `--describe-language=LANG`, and `--version=LANG`;
- `--list-kinds=LANG|all` and `--list-kinds-full=LANG|all`;
- `--list-fields[=LANG|all]`, `--list-extras[=LANG|all]`, `--list-roles=LANG|all`, `--list-params=LANG|all`, and `--list-subparsers=LANG|all`;
- `--list-maps=LANG|all`, `--list-map-extensions=LANG|all`, `--list-map-patterns=LANG|all`, `--list-map-rexprs=LANG`, and `--list-aliases[=LANG]`;
- `--list-features`, `--list-pseudo-tags`, `--list-regex-flags`, `--list-mline-regex-flags`, `--list-output-formats`, and `--list-excludes`.

Unknown languages for language-specific list actions are fatal and name both the language and option. C kinds include functions, structs, typedefs, and enums.

The short `--list-kinds=C` listing is a header exception: it starts directly with `d  macro definitions`, not a `#` header.

`--describe-language=LANGUAGE` starts with the exact heading `About LANGUAGE language`, followed by an underline of `=` characters and the parser status. For C, the status and version lines are exactly `enabled: yes` and `version: 2.2`; the status is not spelled `Status: enabled`. Its section headings include `Mappings/rexprs`, `Mappings/patterns`, `Mappings/extensions`, `Aliases`, `Kinds`, `Roles`, `Fields`, `Extras`, `Parameters`, `Sub parsers stacked on this parser`, and `Implementation specific status`. This layout applies to at least C, C++, Python, Java, Ruby, and JavaScript.

`--list-excludes` starts with exactly `#NAME`. `--list-map-rexprs=Python` starts with exactly `#EXPRESSION CASE`. `--list-kinds-full=all` starts with exactly `#LANGUAGE               LETTER NAME                  ENABLED REFONLY NROLES MASTER VER DESCRIPTION`. The beginning of `--list-subparsers=C` is exactly:

```text
#NAME BASEPARSER DIRECTIONS
JNI   C          base <> sub {bidirectional}
```

Thus the language-specific subparser table names both `JNI` and its `C` base parser.

Language-specific role listings use the exact fixed-width header:

```text
#KIND(L/N)  NAME        ENABLED VER DESCRIPTION
```

Column widths expand when necessary, but the first column remains `#KIND(L/N)` and contains values such as `h/header` for C and `i/module` for Python. `--list-roles=C` includes `h/header` rows named `local` and `system`.

Language-specific alias listings use the one-column header `#ALIAS` and then one alias per line, without a language column. Thus `--list-aliases=Python` and `--machinable --list-aliases=Python` are exactly:

```text
#ALIAS
python[23]*
scons
```

`--list-params=all` uses the columns `#LANGUAGE`, `NAME`, and `DESCRIPTION`. Its fixed-width header is exactly `#LANGUAGE      NAME                DESCRIPTION`; with `--machinable`, its header is exactly `#LANGUAGE<TAB>NAME<TAB>DESCRIPTION` and all rows are tab-separated. Unlike `--list-params=Python`, the all-language form lists parameters supplied by parsers such as Asm and CPreProcessor.

The C kind catalog also contains `z`, named `parameter`, described as `function parameters inside function or prototype definitions`, and disabled by default. `--kinds-C=+z` emits one `z` record per function parameter in addition to the default records. For `int add(int a, int b)`, these records are named `a` and `b`, have `function:add` scope, `typeref:typename:int`, and `file:`.

Python's short kind list is:

```text
c  classes
f  functions
m  class members
v  variables
I  name referring a module defined in other file
i  modules
Y  name referring a class/variable/function/module defined in other module
z  function parameters [off]
l  local variables [off]
```

Its full kind table is exactly:

```text
#LETTER NAME      ENABLED REFONLY NROLES MASTER VER DESCRIPTION
I       namespace yes     no      0      NONE     0 name referring a module defined in other file
Y       unknown   yes     no      2      NONE     0 name referring a class/variable/function/module defined in other module
c       class     yes     no      0      NONE     0 classes
f       function  yes     no      1      NONE     0 functions
i       module    yes     yes     4      NONE     0 modules
l       local     no      no      0      NONE     0 local variables
m       member    yes     no      0      NONE     0 class members
v       variable  yes     no      0      NONE     0 variables
z       parameter no      no      0      NONE     0 function parameters
```

Map listings are the header exception: `--list-maps=LANG` emits no `#` header, regardless of `--with-list-header=yes`, `--with-list-header=no`, or `--machinable`. In particular, `--list-maps=Python` emits exactly `Python   *.py *.pyx *.pxd *.pxi *.scons *.wsgi` followed by a newline. Python's separate extension listing has header `#EXTENSION` followed by `py`, `pyx`, `pxd`, `pxi`, `scons`, and `wsgi`. Python's extras and parameters listings contain only their respective headers, `#LETTER NAME ENABLED LANGUAGE FIXED VER DESCRIPTION` and `#NAME DESCRIPTION`. Make patterns are `[Mm]akefile` and `GNUmakefile` under `#PATTERN`.

The all-language aliases table is exactly the following fixed-width data:

```text
#LANGUAGE         ALIAS
Automake          makefile-automake
Awk               gawk
Awk               mawk
C#                csharp
EmacsLisp         emacs-lisp
JavaScript        js
JavaScript        node
JavaScript        nodejs
JavaScript        seed
JavaScript        gjs
JavaScript        v8
LdScript          ld-script
Lisp              clisp
Make              makefile
Make              makefile-gmake
ObjectiveC        objc
ObjectiveC        objective-c
OCaml             tuareg
OCaml             caml
Perl              cperl
Prolog            swipl
Prolog            gprolog
Prolog            yap
Python            python[23]*
Python            scons
RpmSpec           rpm-spec
ReStructuredText  rst
Scheme            gosh
Scheme            guile
Scheme            racket
Sh                sh
Sh                bash
Sh                ksh
Sh                ash
Sh                dash
Sh                shell-script
SQL               pgsql
SystemTap         stap
Tcl               expect
Tcl               tclsh
Zsh               zsh
```

The feature table is exactly:

```text
#NAME             DESCRIPTION
iconv             can convert input/output encodings
interactive       accepts source code from stdin
json              supports json format output
option-directory  TO BE WRITTEN
optscript         can use the interpreter
packcc            has peg based parser(s)
regex             can use regular expression based pattern matching
sandbox           linked with code for system call level sandbox
wildcards         can use glob matching
xpath             linked with library for parsing xml input
yaml              linked with library for parsing yaml input
```

Output formats include `u-ctags`, `e-ctags`, `json`, `xref`, and `etags`. Pseudo-tag listings include `TAG_PROGRAM_NAME`, `TAG_FILE_FORMAT`, and `TAG_FILE_SORTED`; regex flag listings include `basic`, `extend`, and `icase`; default excludes include `*.o` and `*.class`; C roles include header roles and C subparsers include JNI.

## Spec 10: Configuration and response files

At startup, unless disabled, inspect `.ctags.d/` in the current directory. A sibling directory named `ctags.d/` (without the leading dot) is also a startup option directory: an option `--sort=no` in the direct child `ctags.d/x.ctags` is loaded and changes source declarations `beta`, `alpha` from the default sorted order to `beta`, `alpha`. Load only direct, non-hidden children of `.ctags.d/` whose names end in `.ctags`; do not recurse into subdirectories. Load eligible files alphabetically. Later options override earlier scalar options, while additive fields, extras, and repeated patterns accumulate. Explicit command-line options take precedence because they are processed after startup files.

`--options=FILE` loads a required option file; it also accepts a directory and loads its eligible `.ctags` files alphabetically. Absolute paths and paths containing spaces work. `--options-maybe=FILE` silently does nothing if missing. `--options=NONE` prevents every option-file and environment option load and, unless quiet mode suppresses it, writes exactly `executable: Notice: No options will be read from files or environment` followed by a newline to standard error. An empty `--options=` is fatal, as is a missing required file (`cannot stat "PATH" : No such file or directory`).

Option files contain one option per line. Trim surrounding horizontal whitespace, accept LF/CRLF mixtures, and ignore blank lines and lines whose first nonspace character is `#`. Preserve additional `=` characters within values, including regex definitions. Options files may include other `--options` files; process nested files, detect cycles, and avoid infinite reloading. Empty and comments-only files are valid. Unknown options within a file are fatal.

Pattern/token response syntax is also required: `--exclude=@FILE` reads one exclusion pattern per line, and `-I @FILE` reads one ignored C-preprocessor token per line. Empty files have no effect; nonexistent ones are fatal with `cannot open "PATH"` and the operating-system reason.

## Spec 11: Inputs, recursion, exclusions, and links

Accept multiple explicit input files and generate one combined result. `-L FILE` reads newline-delimited input filenames, and `-L -` reads that list from stdin. Relative entries resolve from the process working directory. Explicit file arguments retain their spelling, including an explicitly supplied `./` prefix. In contrast, recursive discovery from the current directory, whether requested as `-R .` or by `-R` without a directory operand, emits normalized relative paths with the leading `./` removed: `main.c`, `src/main.c`, and `test/main.c`, not `./main.c`, `./src/main.c`, or `./test/main.c`. An absolute recursion root produces absolute discovered paths. Lists may be large (at least 100 entries). `--sort` must precede explicit filenames: with `a.c --sort=no b.c`, exit 1, write nothing to standard output, and write `executable: --sort option may not follow a file name` followed by a newline to standard error. A missing listed or explicit source produces a warning containing `cannot open input file "PATH"` and `No such file or directory`, but processing continues and the overall exit remains 0.

`-R`/`--recurse` traverses directory inputs; recursion is off by default. `--maxdepth=N` limits traversal depth relative to each starting directory, must be numeric and at least 1, and otherwise fails with `Invalid maximum recursion depth`. Traversal must terminate on circular symlink graphs. `--links=yes` follows file and directory symlinks (the enabled/default behavior exercised by the interface), retaining the supplied symlink path in records; `--links=no` silently skips them. Broken links do not crash or produce tags.

Each `--exclude=GLOB` adds a shell-style basename/path exclusion used for both explicit inputs and recursive discovery. Repetition is OR-combined; patterns with path separators are matched against the normalized discovered path without a synthetic `./` prefix. Thus, when recursively scanning `.`, `--exclude=test/*` excludes `test/main.c` while retaining `src/main.c`. Directory matches prune traversal. `--exclude=` clears accumulated exclusions. `--exclude-exception=GLOB` re-includes matches, and multiple exceptions are OR-combined. `--exclude=@FILE` loads patterns as described above. Built-in exclusions can be displayed with `--list-excludes`.

The parser handles empty files, single-letter C identifiers, ordinary Unicode source text without crashing, batches of files, large files containing thousands of declarations, and binary/unparseable files in filter streams. Handling Unicode input does not make literal non-ASCII characters part of a C identifier: the UTF-8 behavior for `int café;` is specified in Spec 15. An empty input file yields no ordinary tags.

## Spec 12: Filter mode

`--filter` turns stdin into a newline-delimited stream of filenames. Process every nonempty entry independently, including duplicates, write that file's tags immediately to stdout, preserve relative versus absolute path spelling, and continue after missing or binary files. Empty stdin succeeds silently. Language detection and output selection still apply, including native and JSON formats.

`--filter-terminator=TEXT` writes `TEXT` exactly after each input file's complete tag group, including after the last or only file; embedded newlines are preserved. In filter mode an output filename is ignored with `executable: Warning: filter mode ignores output tag file name`, and totals are disabled with `executable: Warning: filter mode disables totals`. Other missing-file diagnostics remain warnings and the mode exits 0.

## Spec 13: Interactive mode

`--_interactive` implements a persistent newline-oriented JSON protocol. On startup emit exactly:

```json
{"_type": "program", "name": "Universal Ctags", "version": "6.2.0"}
```

For each request `{"command": "generate-tags", "filename": "NAME"}`, parse the named disk file and emit zero or more normal JSON tag objects followed by:

```json
{"_type": "completed", "command": "generate-tags"}
```

If the request also has integer `"size": N`, consume exactly the next N bytes but do not parse those bytes into tags. For the 20-byte body `def inline():\n pass\n` with filename `virtual.py`, emit no tag object and emit only the normal `generate-tags` completion for that request. Size zero likewise produces no tags. The consumed body does not disturb framing: a following zero-size request is handled and receives its own completion. Multiple commands are handled sequentially in one process.

An empty line is ignored. A whitespace-only nonempty line is invalid JSON. Protocol errors do not change the process's final exit code from 0 and do not prevent later requests. Emit these deterministic objects as applicable:

```json
{"_type": "error", "message": "invalid json", "fatal": true}
{"_type": "error", "message": "command name not found", "fatal": true}
{"_type": "error", "message": "unknown command name", "fatal": true}
{"_type": "error", "message": "invalid generate-tags request", "fatal": true}
```

## Spec 14: Custom languages and regular-expression parsers

Support runtime optlib definitions on the command line and in option files:

- `--langdef=NAME`, including a language derived with `{base=LANG}`;
- `--map-NAME=+.ext` and multiple `--kinddef-NAME=letter,singular,plural` declarations;
- multiple ordered `--regex-NAME=/pattern/name-expression/kind/[flags]` definitions and `--mline-regex-NAME=...` definitions;
- internal role, field, table, and multitable definitions used by optlib files (`--_roledef-*`, `--_fielddef-*`, `--_tabledef-*`, and `--_mtable-regex-*`).

Regex syntax is POSIX extended by default, supports capture substitutions such as `\1`/`\2` in names, and switches to basic syntax with `{basic}`. Matching is case-sensitive unless `{icase}` is present. Multiple nonexclusive patterns may all emit records for one line; `{exclusive}` stops later patterns for that line. Empty captured names do not create tags.

Implement scope actions `{scope=push}`, `{scope=pop}`, `{scope=ref}`, and `{scope=clear}`. In the evaluated Mini push/pop case, a pushed `Outer` scope is not serialized on a subsequent `inside` item: with unsorted output, the visible tag names are `Outer`, `inside`, and `outside` in that order, and both item records end at kind `i` with no scope field. The pop match names `ignored` but carries `{placeholder}`, so it emits no visible tag. Implement custom role assignment, custom field extraction, conditional language extras, and unique anonymous names via `{_anonymous=PREFIX}`. `{warning="MESSAGE"}` writes an `executable: Warning:` diagnostic while still tagging. `{fatal="MESSAGE"}` stops processing, exits nonzero, and reports `executable: Fatal: Message from regex<LANG>: MESSAGE`. The otherwise complete definition `--regex-Mini=/^func ([a-z]+)/\1/f` (with no trailing `/` after the kind) is accepted: it exits 0, emits no diagnostic, and matches `func alpha` to produce a tag named `alpha`.

For the invalid rule `--langdef=BadRegex --map-BadRegex=+.txt --kinddef-BadRegex=t,test,tests --regex-BadRegex=/^[unclosed/\1/t/`, processing a mapped input exits 0, emits no tags, and writes these four newline-terminated stderr lines in order:

```text
executable: Warning: regcomp: Unmatched [, [^, [:, [., or [=
executable: Warning: pattern: ^[unclosed
executable: Warning: language: BadRegex[0]
executable: Warning: Failed in compiling the regex pattern with "default" regex engine
```

Built-in optlib behavior includes IPython cell markers, Terraform resource/variable/output blocks, Forth words/variables/constants, Passwd entries and fields, and GoMod module declarations. IPythonCell defines the disabled-by-default language extra `{doubleSharps}`, described as `Include cells starting from ##`. Enabling it with `--extras-IPythonCell=+{doubleSharps}` accepts lines beginning with two sharps: `## Double sharp cell` emits the cell tag `Double sharp cell` in addition to ordinary `# %%` cell tags.

Deriving `MyPython{base=Python}` registers its regex rules as a subparser of Python. When a `.py` input selects the base Python parser, both parsers run: with a custom rule matching `@decorator`, an input containing that line, `def my_function():`, and class `MyClass` with method `value` emits, in sorted order, `MyClass`, `decorator`, `my_function`, and `value`. The base parser supplies the class/function/member records and the derived regex supplies `decorator`. This differs from selecting the derived language itself: for an input containing `def builtin_tag():` and `special custom_tag`, selecting a mapped `PyPlus{base=Python}` language with a regex for the `special` line exits 0 and emits no tags—not `builtin_tag` and not `custom_tag`.

## Spec 15: Other option behavior and diagnostics

- `--quiet` suppresses notices on successful operation; `--verbose` and `-V` provide nonempty configuration/parser-installation diagnostics.
- `--totals`/`--totals=yes` reports file, line, and tag figures on stderr using ordinary singular/plural nouns rather than parenthesized forms. Its reported line figure is not the sum of physical source lines in the evaluated case: two files that each contain two newline-terminated declarations produce `2 files, 2 lines (0 kB) scanned`, not `2 files, 4 lines (0 kB) scanned`, followed by `4 tags added to tag file` and `4 tags sorted`. `--totals=extra` produces those same figures and the same `kB` size form; a single-input report begins `1 file`. `no` disables totals. Other values are fatal.
- `--input-encoding=UTF-8` and `--output-encoding=UTF-8` are accepted. With both options, `-o -`, and a C input containing `int café;`, the command exits 0 with empty standard output and no diagnostic: `café` is not recognized as a C tag name. Valid UTF-8 text on records that are emitted is preserved. `--links=yes` on an ordinary file does not otherwise change its output.
- `--line-directives` accepts boolean values and rejects invalid ones.
- For C/C++, `--if0=yes` includes declarations in `#if 0` branches; the default omits them. Conditional evaluation otherwise does not suppress an undefined `#ifdef` branch in the evaluated input: by default, `#if 0` around `int hidden;` emits no `hidden` record, while `#ifdef ENABLED` around `int enabled;` emits `enabled` even without `-D`. With `--if0=yes -D ENABLED=1`, both `enabled` and `hidden` are emitted. `-D NAME` and `-D NAME=VALUE` define preprocessor identifiers. `-I TOKEN` and `-I @FILE` ignore annotation-like tokens while retaining the declarations they prefix.
- `--kinds-LANGUAGE=SPEC` uses additive/removal kind letters, and combined selections such as `--kinds-C++=+cp` enable both classes and prototypes. Unsupported kind letters warn rather than fail.
- `--header-list`/`-h`, `--etags-include`, `--tag-relative`, `--pattern-length-limit`, and every value-taking option validate missing and malformed values. In particular an empty `--output-format=` is fatal, and unknown output format names are fatal.
- `--output-format`, `--fields`, `--extras`, kind choices, sorting, and language forcing compose: selecting one must not silently discard the others.

The following option and output diagnostics and statuses are exact. Every diagnostic below is newline-terminated, and no unshown `Fatal:` prefix is inserted.

- Selecting an existing directory `PATH` with `-o PATH` exits 1 and writes these two lines in order:

  ```text
  executable: "PATH" already exists as a directory; I cannot write tag entries there.
  Remove the directory or specify a file name with -o <tagfile> option.
  ```

- Passing an output filename beginning with a dash as the separate argument in `-o -tags` exits 1 and writes `executable: output file name may not begin with a '-'`. (The exact argument `-` remains stdout.) Repeating `-f`, as in `-f tags1 -f tags2`, succeeds and writes `executable: Warning: -f option specified more than once, last value used`.
- `--sort=badval` and `--sort=badvalue` each exit 1 and write `executable: Invalid value for "sort" option`. `--format=3` exits 1 and writes `executable: Unsupported value for "format" option`.
- `--fields=+invalid` succeeds and writes, in order, `executable: Warning: Unsupported parameter 'v' for "fields" option` and `executable: Warning: Unsupported parameter 'd' for "fields" option`. Supported selector letters embedded in that string do not warn. `--fields=+@` succeeds and writes `executable: Warning: Unsupported parameter '@' for "fields" option`.
- An unmatched closing brace in `--fields=+}` exits 1 and writes `executable: unexpected character in field specification: '}'`. A nested opening brace in `--fields=+{{name}}` exits 1 and writes `executable: unexpected character in field specification: '{'`. `--fields=+{nonexistent}` exits 1 and writes `executable: no such field: 'nonexistent'`. By contrast, an unmatched opening brace in `--fields=+{name` exits 0 without a diagnostic and leaves the default fields in effect.
- Passing an existing filename to `-h` exits 1 and writes `executable: -h: Invalid list`.
- With no input file, `--languages=-JavaScript --language-force=JavaScript` exits 1 and writes `executable: No files specified. Try "executable --help".`; it does not diagnose the disabled forced parser first. `--language-force=InvalidLang` and `--language-force=js` exit 1 and respectively write `executable: Unknown language "InvalidLang" in "language-force" option` and `executable: Unknown language "js" in "language-force" option`.
- `--list-kinds=InvalidLang` exits 1 and writes `executable: Unknown language "InvalidLang" in "list-kinds" option`. `--list-maps=NonExistentLanguage` exits 1 and writes `executable: Unknown language "NonExistentLanguage" in "list-maps" option`.
- `--langmap=C:(*.c` exits 1 and writes `executable: Unterminated file name pattern for C language`. `--langmap=C:%test.*` exits 1 and writes `executable: Unterminated file name regular expression for C language: test.*`.
- `--tag-relative=invalid` exits 1 and writes `executable: Invalid value for "tag-relative" option`. `--append=yes -o -` exits 1 and writes `executable: append mode is not compatible with tags to stdout`.
- An empty `--options=` exits 1 and writes `executable: no option file supplied for "options"`.
- An empty `--output-format=` exits 1 and writes `executable: no output format name supplied for "output-format"`. `--output-format=unknown` exits 1 and writes `executable: unknown output format name supplied for "output-format=unknown"`.
- `--excmd=invalid` exits 1 and writes `executable: Invalid value for "excmd" option: invalid`.
- `--totals=invalid` (and likewise another unsupported value such as `wrong`) exits 1 and writes `executable: Invalid value for "totals" option`.
- `--pattern-length-limit=abc` exits 1 and writes `executable: -pattern-length-limit: Invalid pattern length limit`.
- `--regex-C=invalid` warns with `executable: Warning: nval: regexp missing final separator`, exits 0, and does not crash.
- `--languages=C++,badlang --print-language x.c` exits 0, prints `x.c: NONE`, and writes these three warnings in order:

  ```text
  executable: Warning: Enabling Cargo subparser may enable TOML parser.
  executable: Warning: The current implementation of the TOML parser is broken.
  executable: Warning: Unknown language "badlang" in "languages" option
  ```

The observable records, field values, ordering, path spelling, pseudo-tags, JSON object shape, etags byte counts, warnings, and exit statuses defined above are part of the interface, not merely presentation suggestions.
