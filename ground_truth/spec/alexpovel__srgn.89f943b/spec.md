# Behavioral specification for `executable`

The required artifact is one executable file named exactly `executable`.  It is a
single-command, Unicode-aware command-line program for finding syntactic or textual
scopes and optionally transforming them.  The words MUST, MUST NOT, and SHOULD below
are normative.  Every example is byte-for-byte except that a displayed final newline
is called out explicitly when it matters.

## Spec 1

`executable` MUST be directly runnable on Linux and accept this grammar:

```text
executable [OPTIONS] [SCOPE] [-- <REPLACEMENT>]
```

There are no subcommands. Words such as `add`, `remove`, `list`, `get`, `set`,
`delete`, and `update` in the first positional slot are regex scopes, not commands.
Options may precede or follow `SCOPE`. The `--` token ends option parsing and introduces
the one optional replacement value; this permits replacements such as `-u` or
`--help`. More than one replacement is an argument error. A second unintroduced
positional argument is also an argument error. Long valued options support both
`--option value` and `--option=value`.

For the repeated-separator invocation `test -- a -- b`, the argument error contains
exactly `the argument '[REPLACEMENT]' cannot be used multiple times`.

Successful work returns status 0. Runtime/application failure returns 1. Command-line
syntax, a missing required argument, an invalid enumerated value, an unknown option,
or a forbidden option combination returns 2. Normal results go to stdout; diagnostics
go to stderr. The executable MUST finish ordinary and large-input operations within a
few seconds and MUST NOT impose small fixed limits on line, match, capture, pattern, or
replacement size.

## Spec 2

The positional `SCOPE` is a case-sensitive regular expression. If omitted it defaults
to `.*`, which means actions such as `--upper`, `--lower`, `--titlecase`,
`--normalize`, `--german`, and `--symbols` apply to the complete input. `--delete`,
`--squeeze`, and `--literal-string` require an explicit scope where stated below.

All non-overlapping matches are selected, from left to right, across the entire input.
Matching is Unicode-aware and multiline input is one search buffer. The dot does not
match line-feed unless enabled by an inline flag; `^` and `$` denote the start and end
of the whole buffer unless multiline mode is enabled inline. Inline
flags such as `(?i)` and `(?s)` work. Required syntax includes alternation, greedy and
lazy quantifiers, Unicode `\w`/`\W`/`\s`/`\S`, ordinary and POSIX bracket character
classes (for example `[[:alnum:]_]`), Unicode property escapes such as `\p{Emoji}`,
word boundaries, anchors, numbered and named captures, noncapturing groups,
lookahead, lookbehind, and pattern backreferences such as `(\w+)\s+\1`.

Examples:

```text
pattern `.`       action delete  input `a.b.c\n`       => `\n`
pattern `(?s)a.*b` action upper  input `a\ndata\nb`    => `A\nDATA\nB`
pattern `(a+?)`   replacement `[$1]`, input `aaaa`     => `[a][a][a][a]`
pattern `(?<=\d)(\w+)`, replacement `_$1_`, input `123abc 456def`
                                                      => `1_23abc_ 4_56def_`
```

Invalid regexes fail at runtime with status 1 and a diagnostic beginning
`Error: Failed building regex`; useful causes include `Invalid character class`,
`Opening parenthesis without closing parenthesis`, and `Could not parse group name`.
For `(invalid`, the cause is exactly
`Invalid regex: Parsing error at position 8: Opening parenthesis without closing parenthesis`.
The very large repetition `a{999999999999999999999999999999}` is accepted; on input
`a` with `--upper` it selects nothing, returns 0, emits `a`, and has no diagnostic. A
match that consumes no bytes is not turned into a selected range, so
replacement/action on bare `^`, bare `$`, or an empty-only match is a no-op. A regex
such as `a*` still acts on each nonempty match it finds and MUST terminate rather than
looping on its empty alternatives.

## Spec 3

`-L`/`--literal-string` changes `SCOPE` from regex syntax to a literal substring and
requires it to be supplied. It is still case-sensitive and finds every non-overlapping
occurrence. Regex punctuation has no special meaning: `.`, `.*`, `a+?`, `[abc]`,
`(test)`, `a|b`, `^`, `$`, and `.*+?[]` all match those exact characters.

Before matching, these backslash escapes in the literal scope are decoded: `\n`,
`\r`, `\t`, `\b`, `\f`, `\\`, escaped single quote, and escaped double quote. Thus
literal `\n` can delete line feeds, literal `\t` can match a tab, literal `\b` matches
U+0008, and literal `\\` matches one backslash. `\v` and `\0` are not supported. An
unsupported escape fails with status 1; for `\.` the diagnostic is exactly:

```text
Error: Failed building literal string

Caused by:
    Contains invalid escape sequences: '\.'
```

The corresponding final cause lines for `\v` and `\0` are respectively
`Contains invalid escape sequences: '\v'` and
`Contains invalid escape sequences: '\0'`.

With no scope, `--literal-string` returns 2 and stderr is:

```text
error: The following required argument was not provided: scope

Usage: srgn [OPTIONS] [SCOPE] [-- <REPLACEMENT>]

For more information, try '--help'.
```

An explicitly empty literal scope matches nothing and leaves input unchanged.

## Spec 4

With stdin selected as the input and at least one active action, stdout is the full
input with only selected ranges changed. Out-of-scope bytes, whitespace, newlines,
NUL characters, non-Latin scripts, emoji, and zero-width joiner sequences are
preserved exactly. No match is a successful unchanged pass-through. Empty input yields
empty output and success. Presence or absence of a trailing newline is preserved unless
the selected action itself inserts or deletes it.

With stdin and neither an action, a language scope, nor a record-view option, the
program writes the input unchanged and returns 0. It also emits an error-level log
containing exactly
`No actions specified, and not in search mode. Will return input unchanged, if any.`
unless logging is disabled. A regex scope alone does not turn the program into grep
output; it remains this pass-through mode. `--line-numbers` is a record-view option
and therefore changes this output even without an action, as specified in Spec 24.
With no supplied stdin bytes, no file request, and no discoverable language files, it
succeeds without stdout. Merely setting `--stdin-detection=force-unreadable` does not
make supplied bytes absent in the no-file fallback described in Spec 28.

## Spec 5

Selection is represented by sorted, half-open UTF-8 byte ranges. Regex scope matches
are intersected with any language ranges. Multiple matches are all retained; adjacent
or overlapping ranges are merged when an operation requires a coherent region.
Out-of-scope regions can never be introduced into scope by a later selector. Operations
must behave correctly at byte 0, at EOF, on entire-input matches, on adjacent matches,
on hundreds of thousands of bytes, and on thousands of matches.

Examples:

```text
`def|jkl` + upper on `abc def ghi jkl mno` => `abc DEF ghi JKL mno`
`[abc]` + upper on `abcdefabc`             => `ABCdefABC`
`test` + delete on `test one test two test` => ` one  two `
`^start|end$` + delete on `start middle end` => ` middle `
```

## Spec 6

The optional `REPLACEMENT` replaces every selected regex/literal match. It may be the
empty string. Backslash escapes such as `\n` and `\t` are decoded in it. Regex
metacharacters have no special meaning in replacement text.

Regex captures expand using `$0` for the whole match, `$1` through `$10` (and higher)
for unnamed groups, `$name` for named groups, and braced forms `${1}` and `${name}`.
Both Python-style `(?P<name>...)` and angle-bracket `(?<name>...)` group declarations
are accepted. A named capture is addressable only by name: it does not also define a
numeric replacement variable. Capture positions are not renumbered around it, so in
`(?<x>a)(b)`, the named capture is `$x` and the unnamed capture is `$2`; replacement
`${x}:${2}` on `ab` produces `a:b`. Named and numbered references may be mixed,
reordered, adjacent, or reused when each reference addresses a variable that exists.
A capture that participated with an empty value expands empty. `$$` emits one literal
dollar, so `$$1` is literal `$1` and `$$$1` is a dollar followed by capture 1. A `$`
followed by a character that cannot start a variable (for example `$?` or `${?`) is
literal. One extra `}` after a valid braced reference is literal.

Referencing a nonexistent capture fails with status 1. For pattern
`(?P<foo>\w+)` and replacement `$bar`, stderr is exactly:

```text
Error: Error applying: Error in an action: Action failed in replacement: Error in variable expressions: Undefined variable, unable to substitute: 'bar'
```

Thus the final cause contains `Undefined variable, unable to substitute: 'NAME'` for
the corresponding missing name. An opened variable brace with no closing brace fails
with `Mismatched braces for variable: 'NAME'` (or at least `Mismatched braces` when
intervening text exists).

This named-capture rule also applies to the first capture position. Pattern
`(?<x>\w+)` with replacement `${x}:$0:${1}` on `go` returns status 1, emits no stdout,
and writes exactly:

```text
Error: Error applying: Error in an action: Action failed in replacement: Error in variable expressions: Undefined variable, unable to substitute: '1'
```

Normative examples:

```text
`(\w+) (\w+)` -> `$2 $1` on `foo bar`                => `bar foo`
`(?P<first>\w+) (?P<last>\w+)` -> `$last, $first`    => `Doe, John`
`(([a-z]+)(\d+)([a-z]+))` -> `$1=$2+$3+$4`           => `abc123def=abc+123+def`
`(?:\w+) (\w+) (?:\w+) (\w+)` -> `$1 and $2`       => `b and d`
`(.)` -> `$1$1` on `ab`                               => `aabb`
```

## Spec 7

Composable actions are `-u`/`--upper`, `-l`/`--lower`, `-t`/`--titlecase`,
`-n`/`--normalize`, `-g`/`--german`, `-S`/`--symbols`, and replacement. Their semantic
order is fixed, regardless of command-line occurrence order: replacement, upper,
lower, titlecase, normalize, symbols, then German. A composable flag cannot be repeated:
for example, repeating `--upper` returns 2 and begins
`error: the argument '--upper' cannot be used multiple times`. Each enabled stage
applies to the selected regions and passes its result to the next stage. Scope ranges
correspond to the original selection but must accommodate changed replacement lengths.

Thus:

```text
`--upper --lower` on `AbC` => `abc`
`--lower --upper` on `AbC` => `abc`
`--normalize --lower --upper` on `Café Résumé` => `cafe resume`
`--german --upper` on `Gruesse aus Muenchen` => `GRÜẞE AUS MÜNCHEN`
scope `t`, replacement `x`, then upper on `test` => `XesX`
scope `world`, REPLACE=`universe`, upper=true on `hello world` => `hello UNIVERSE`
```

Short options may be clustered (`-ul`, `-ut`, `-Lu`, `-vvv`). Clustering does not
alter the fixed action order: both `-ul` and `-lu` on `AbC` produce `abc`.

## Spec 8

`--upper` and `--lower` use Unicode casing on each selected string, with sharp-s
uppercased to capital eszett. Characters without a case mapping remain intact.
Examples include `café` -> `CAFÉ`, `мир` -> `МИР`, `straße` -> `STRAẞE`, and capital
eszett `ẞ` -> `ß` for lowercase. Thus
`straße fuß grüße äpfel öl übung` uppercases to
`STRAẞE FUẞ GRÜẞE ÄPFEL ÖL ÜBUNG`. Emoji, CJK, Arabic, tabs, and punctuation are
unchanged.

`--titlecase` performs English headline title casing. It capitalizes significant words,
lowercases ordinary all-uppercase words, and leaves interior mixed capitalization
alone when appropriate. Articles/conjunctions/prepositions such as `a`, `an`, `and`,
`as`, `at`, `but`, `by`, `en`, `for`, `if`, `in`, `of`, `on`, `or`, `the`, `to`,
`v`, `v.`, `via`, and `vs` are lowercase unless first or last. Normative results are:

```text
hello world from the edge of tomorrow => Hello World From the Edge of Tomorrow
the quick brown fox jumps over the lazy dog => The Quick Brown Fox Jumps Over the Lazy Dog
a tale of two cities => A Tale of Two Cities
HELLO WORLD => Hello World
travel via rail and bus => Travel via Rail and Bus
```

Title casing only the regex `\w+` in `hello WORLD MiXeD` produces
`Hello World MiXeD`.

## Spec 9

`--normalize` performs Unicode canonical decomposition (NFD) on each selected string
and removes every combining mark from the decomposed result. It therefore converts
precomposed or already decomposed diacritics while leaving emoji and unaccented text
unchanged:

```text
café naïve résumé => cafe naive resume
Héllo Wörld, Ñice tö meët yoü! Ãpple, çafé
                 => Hello World, Nice to meet you! Apple, cafe
Việt Nam, Tiếng Việt => Viet Nam, Tieng Viet
e + U+0301 + U+0302 => e
```

Normalization may change the length of selected text and composes normally with later
actions.

## Spec 10

`-d`/`--delete` deletes every selected range. It requires explicit `SCOPE` and is
mutually exclusive with replacement, squeeze, upper, lower, titlecase, normalize,
German, and symbols. The conflict is detected before input processing with status 2.
Deleting a complete selection can yield an empty byte stream; deleting text from a
line does not delete its newline unless the newline is part of the regex.

The conflict diagnostic follows clap style and lists all conflicting composable
actions when appropriate. For `--delete --upper foo`, after normalizing only the binary
name in the Usage line, stderr is:

```text
error: the argument '--delete' cannot be used with:
  [REPLACEMENT]
  --upper
  --lower
  --titlecase
  --normalize
  --german
  --symbols

Usage: BINARY --delete --upper <SCOPE> [-- <REPLACEMENT>]

For more information, try '--help'.
```

Without a scope it returns 2, mentions `required arguments were not provided`, lists
`<SCOPE>`, and shows `Usage: executable --delete <SCOPE>`.

For `--delete --squeeze t`, stderr starts with exactly
`error: the argument '--delete' cannot be used with '--squeeze'`, followed by a blank
line, `Usage: executable --delete <SCOPE> [-- <REPLACEMENT>]`, another blank line, and
the usual help hint.

## Spec 11

`-s`/`--squeeze` (alias `--squeeze-repeats`) requires explicit `SCOPE`. It collapses
each run of directly consecutive occurrences of the scope to the first occurrence.
Separated runs remain separate. For example, scope `a` transforms `aaaa bbb aaa` to
`a bbb a`, scope `l` transforms `helllllo` to `helo`, and scope `\s` transforms
`a   b     c` to `a b c`. With a regex such as `a+`, each maximal regex match is one
occurrence and is retained as a whole.

Squeeze may be combined with replacement and composable transformations; it is only
incompatible with delete. A supplied replacement first replaces each selected run,
then squeeze removes adjacent duplicate selected occurrences as applicable. Tested
results include:

```text
scope ` +`, squeeze, replacement `_` on `This  has    too` => `This_has_too`
scope `a+`, squeeze, replacement `X` on `aaaaaacccaaabbb` => `XcccXbbb`
scope `a+`, upper, squeeze on `aaa bbb aaa` => `AAA bbb AAA`
```

Although squeeze performs the shown transformation and returns 0, it is not counted
as an action by the no-action logger. At default logging, `a --squeeze` on
`aaaa bbb aaa` therefore emits `a bbb a` and also an error-level log containing the
full no-action message from Spec 4.

## Spec 12

`-S`/`--symbols` greedily maps the following ASCII sequences within selected ranges.
Longer tokens win before their prefixes:

| ASCII | Unicode | ASCII | Unicode |
|---|---|---|---|
| `<->` | `↔` | | |
| `-->` | `⟶` | `<--` | `⟵` |
| `->` | `→` | `<-` | `←` |
| `=>` | `⇒` | `!=` | `≠` |
| `<=` | `≤` | `>=` | `≥` |
| `---` | `—` | `--` | `–` |

Single `<`, `>`, `!`, `-`, `=`, `&&`, and `||` remain unchanged. Greediness means
`----` becomes `—-`, `======>` becomes `=====⇒`, `-->--><--` becomes `⟶⟶⟵`, and
`<=<=<=` becomes `≤≤≤`.

Inside a token beginning exactly `https://`, everything through the next whitespace or
EOF is protected, so `https://example.com/path->test` stays unchanged; after a space,
arrows convert normally. Incomplete prefixes (`https:/a`, `https:a`, `httpsa`, `httpa`,
`htta`, `hta`) receive no special treatment.

`-i`/`--invert` is valid only when `--symbols` is also active (whether or not other
composable actions are present). On `--invert` alone, it returns 2 and begins:

```text
error: the following required arguments were not provided:
  --symbols

Usage: executable --symbols --invert [SCOPE] [-- <REPLACEMENT>]
```

The usual help hint follows. With inversion, the mapping reverses one Unicode code
point at a time:
`↔` -> `<->`, `⟶` -> `-->`, `⟵` -> `<--`, `→` -> `->`, `←` -> `<-`, `⇒` -> `=>`,
`≠` -> `!=`, `≤` -> `<=`, `≥` -> `>=`, `—` -> `---`, and `–` -> `--`.
Other text is unchanged. Forward then inverse conversion round-trips
`-> <- => != <= >=` exactly.

## Spec 13

`-g`/`--german` converts ASCII alternative spellings inside selected ranges:
case-corresponding `ae`/`oe`/`ue` become `ä`/`ö`/`ü`, and `ss` becomes `ß`; all-caps
input uses `Ä`/`Ö`/`Ü`/`ẞ`. It tokenizes words while preserving all intervening
punctuation, whitespace, CR/LF, digits, emoji, and already-Unicode letters.

In normal mode it is spelling-aware: it chooses conversions that form legal German
words, including arbitrarily concatenated compounds, and does not blindly alter legal
original sequences. Default tie-breaking prefers a legal replacement (`Busse` ->
`Buße`). `--german-prefer-original` retains the source when source and replacement are
both legal (`Busse` remains `Busse`, while unambiguous `grosse` still becomes `große`).
`--german-naive` bypasses legality and greedily changes every candidate pair.
Combining both modifiers makes the prefer-original rule win for ambiguous/valid words
and standalone pairs. In an invocation that also has `--symbols --invert`, inversion
does not reverse German because the inverse spelling is ambiguous; German still runs
forward.

Normal-mode legality MUST reproduce these representative boundaries:

```text
Gruess Gott! Schoene Gruesse aus Deutschland. => Grüß Gott! Schöne Grüße aus Deutschland.
Suesswassertagtraeumer Mauerduebelkuebel Messgeraet
 => Süßwassertagträumer Mauerdübelkübel Messgerät
Aerodynamik Israel Poet Abenteuer Koeffizient => unchanged
Abenteuergruesse Fussball Maedchen schoene => Abenteuergrüße Fußball Mädchen schöne
aepfel oelfeld => unchanged
aepfel sind schoene fruechte aber ueble krankheiten
 => aepfel sind schöne fruechte aber üble krankheiten
Suesswasserschwimmbaeder => Süßwasserschwimmbäder
Busse sind grosse Fahrzeuge => Buße sind große Fahrzeuge
```

Naive mode MUST produce:

```text
Aerodynamik Israel Poet Abenteuer Koeffizient => Ärodynamik Isräl Pöt Abenteür Köffizient
Mueller Koenig Buelow => Müller König Bülow
aeaea oeoe ueue => ääa öö üü
aeoeueaess AEOEUEAESS AeOeUeAeSs => äöüäß ÄÖÜÄẞ ÄÖÜÄẞ
Suesswasserschwimmbaeder => Süßwaßerschwimmbäder
```

Case, punctuation, digits, and compound examples that are normative include:

```text
AEPFEL SIND SCHOEN => ÄPFEL SIND SCHÖN
AePfEl UeBer OeL => ÄPfEl ÜBer ÖL
aEpFeL ueBeR => aEpFeL üBeR
SCHLIESSEN SUESS GRUSS => SCHLIEẞEN SÜẞ GRUẞ
🎉Schoenes Wetter😊 Gruesse! => 🎉Schönes Wetter😊 Grüße!
Fuer-uns-alle Gruess-August schoene-Idee => Für-uns-alle Grüß-August schöne-Idee
Schoene123Sache Gruesse456 123Aepfel => Schöne123Sache Grüße456 123Äpfel
Häus€r => unchanged
T€st¥en§ => unchanged
```

For complete self-contained lexical boundaries, the following additional outputs are
also normative (an omitted modifier means normal mode):

```text
Schoener Tag heute! Ueber den Berg. => Schöner Tag heute! Über den Berg.
Hausueberfall Mauerduebelkuebel Suesswasserschwimmbaeder
 => Hausüberfall Mauerdübelkübel Süßwasserschwimmbäder
Donaudampfschifffahrtsgesellschaftskapitaen Rechtsschutzversicherungsgesellschaften
 => Donaudampfschifffahrtsgesellschaftskapitän Rechtsschutzversicherungsgesellschaften
Gruesse, schoene Aepfel! Ueber's Meer? => Grüße, schöne Äpfel! Über's Meer?
(Gruesse) [Aepfel] {Schoenes} "Ueble" => (Grüße) [Äpfel] {Schönes} "Üble"
Schöne Äpfel ueber Grüße mischen => Schöne Äpfel über Grüße mischen
Groessenwahn Strassenbahn Fussballspiel => Größenwahn Straßenbahn Fußballspiel
`Woerter wie "Kuechengeraet" oder "Oelbild"`,
`Saetze mit "Schoene Gruesse"`, and `Suesswasserfisch, Oelpest`
 => `Wörter wie "Küchengerät" oder "Ölbild"`,
    `Sätze mit "Schöne Grüße"`, and `Süßwasserfisch, Ölpest`
normal + prefer-original: Busse sind grosse Fahrzeuge => Busse sind große Fahrzeuge
naive + prefer-original: Busse grosse Strasse => unchanged
naive + prefer-original: ae oe ue ss => unchanged
naive: aEpFeLsAfT uEbErAlL sSsSsS => äpFeLsAfT übErAlL ßßß
naive: aee oee uee sss => äe öe üe ßs
naive: ueue aeae oeoe ssss => üü ää öö ßß
normal: ae oe ue ss => unchanged
naive: ae oe ue ss => ä ö ü ß
```

## Spec 14

Language-aware scoping parses input as exactly one of C, C#, Go, HCL, Python, Rust,
or TypeScript. Multiple prepared scopes for the same language are allowed. By default
they are applied left-to-right as intersections: later scopes search only inside
earlier ranges. `-j`/`--join-language-scopes` instead evaluates each language scope
independently and unions all results. A prepared scope and a custom-query option for
the same language are mutually exclusive at argument parsing, as detailed in Spec 23.
A following regex/literal scope always intersects the resulting language ranges.

Specifying scopes from two different languages is a parse-time error. For
`--rust comments --python comments`, combined stdout+stderr MUST be:

```text
error: Can only use one language at a time.

Usage: srgn [OPTIONS] [SCOPE] [-- <REPLACEMENT>]

For more information, try '--help'.
```

Prepared scopes encompass the complete syntax construct when described as “in its
entirety”, including its header, body, nesting, and delimiters. Token scopes encompass
only the described token/content. Parsers must recover sufficiently from incomplete
source to find valid comments and strings instead of crashing.

Any prepared value of the form `kind~PATTERN` filters constructs by their declared
name using a case-sensitive, linear-time regex dialect (lookaround and backreferences
are not supported in these name filters, even though they are supported by positional
`SCOPE`). Only kinds explicitly shown with `~<PATTERN>` in
Specs 16–22 permit it. Invalid name regexes fail while parsing arguments. A pattern on
an unsupported kind (for example Rust `comments~foo`) fails while parsing arguments
and reports the scope and supplied pattern as incompatible, as shown below.

The exact diagnostics for two Rust cases are:

```text
error: invalid value '[invalid(' for 'struct'

  tip: error was: regex parse error:
    [invalid(
    ^
error: unclosed character class

For more information, try '--help'.
```

for `--rust 'struct~[invalid('`, and:

```text
error: the argument 'comments' cannot be used with 'a pattern ('foo')'

For more information, try '--help'.
```

for `--rust 'comments~foo'`. Neither diagnostic has a Usage line.

## Spec 15

With one or more language scopes and no actions, the program enters search mode. It
does not pass through the full input. Instead it prints every source line touched by
the final in-scope ranges, in input order, with source, 1-based line, and original
0-based half-open UTF-8 byte columns:

```text
SOURCE:LINE:START-END:complete original line
```

For stdin, SOURCE is `(stdin)`; for files it is the relative path. A line containing
multiple ranges lists them as `START-END;START-END`. The quotes/delimiters of string
scopes are generally outside the range (for `x = "hello"`, the string range is bytes
5–10). Whole-construct scopes may span and emit several lines. If no source is in the
language scope, return 1, emit no stdout, and write
`Error: Error applying: No input was in scope\n` to stderr.

Example:

```text
input:  def hello():
            print("hello world")
            x = "test string"
command: --python strings
output: test.py:2:11-22:    print("hello world")
        test.py:3:9-20:    x = "test string"
```

## Spec 16

Python scopes use `--python VALUE` or alias `--py VALUE` and parse Python 3. Values:

| Value | Selected syntax |
|---|---|
| `comments` | `#` comments including `#` |
| `strings` | contents of quoted, triple-quoted, raw, byte, and f-strings; interpolation expressions excluded |
| `imports` | dotted module names in `import`/`from`, excluding keywords, aliases, `as`, and `*` |
| `doc-strings` | contents of triple-quoted module/class/function docstrings, not non-triple-quoted docstrings or arbitrary strings |
| `function-names` | identifier at every `def`/`async def` declaration |
| `function-calls` | direct identifier used as a callable, excluding its argument list; attribute calls are not selected |
| `class` | complete class definitions, including nested classes |
| `def` | complete synchronous and asynchronous function definitions, including methods |
| `async-def` | complete `async def` definitions |
| `methods` | complete function definitions nested directly in classes |
| `class-methods` | class methods, excluding their `@classmethod` decorator |
| `static-methods` | static methods, excluding their `@staticmethod` decorator |
| `with`, `try` | complete corresponding compound statements |
| `lambda` | complete lambda expression |
| `globals` | identifiers defined by module-level assignments (only the assigned name, not the complete assignment) |
| `variable-identifiers` | identifiers on assignment left sides |
| `types` | identifiers/subscripts/unions in type annotations |
| `identifiers` | all identifier tokens |

Transformations must alter only those constructs: comment transformations do not
touch code/strings; string transformations do not touch identifiers; function-name
scope renames definition names but not unrelated uses; class/def deletion removes the
selected text but preserves out-of-scope newlines. Nested intersections work, e.g.
`--python class --python doc-strings` selects triple-quoted docstrings in classes and
`--python def --python strings` selects strings inside functions. In particular, the
non-triple-quoted string in `class Box:\n    "doc"\n` is not selected by
`doc-strings`: adding `--upper`, either with or without a preceding `--python class`,
leaves those bytes unchanged.

In particular, `function-calls` does not make the complete call expression available
to a following positional scope: scope `outer\(inner\(1\)\)` with
`--python function-calls -- CALL` leaves `value = outer(inner(1))\n` unchanged.
The `def` scope includes both `def` and `async def`: applying scope `x='[ab]'` and
`--upper` within it transforms both assignments in
`def sync():\n    x='a'\nasync def async_one():\n    x='b'\n` to uppercase. For
`global_name: list[str] = other\n`, `--python globals --upper` produces
`GLOBAL_NAME: list[str] = other\n`.

## Spec 17

Rust scopes use `--rust VALUE` or alias `--rs VALUE`:

```text
comments, doc-comments, uses, strings, attribute,
struct, struct~<PATTERN>, priv-struct, pub-struct, pub-crate-struct,
pub-self-struct, pub-super-struct,
enum, enum~<PATTERN>, priv-enum, pub-enum, pub-crate-enum, pub-self-enum,
pub-super-enum, enum-variant,
fn, fn~<PATTERN>, impl-fn, priv-fn, pub-fn, pub-crate-fn, pub-self-fn,
pub-super-fn, const-fn, async-fn, unsafe-fn, extern-fn, test-fn,
trait, trait~<PATTERN>, impl, impl-type, impl-trait,
mod, mod~<PATTERN>, mod-tests, type-def, identifier, type-identifier,
closure, unsafe
```

The prepared comment scopes have the following observed boundaries. Given
`// ordinary\n/// docs\n/* block */\n/*! module docs */\nfn main() {}\n`,
`--rust comments --upper` produces
`// ordinary\n/// docs\n/* block */\n/*! MODULE DOCS */\nfn main() {}\n`, while
`--rust doc-comments --upper` leaves that complete input unchanged. Thus, for this
representative mixture, `comments` selects the content of the inner block-documentation
comment but not the ordinary line/block or outer line-documentation comments, and
`doc-comments` selects none of them.

`uses` selects paths in use declarations and also includes the `as` keyword, while
excluding `use` and glob punctuation. Specifically, uppercasing `uses` in
`use alpha::beta::{Thing as T, *};` produces
`use ALPHA::BETA::{THING AS T, *};`. `strings`
selects contents of ordinary/raw/byte strings (including format-string placeholder
text as part of the literal). `attribute` selects full attributes. Structural scopes
select full definitions. Visibility-specific struct/enum/function scopes distinguish
no visibility, `pub`, `pub(crate)`, `pub(self)`, and `pub(super)` exactly. `test-fn`
means a function with any attribute whose path contains `test`, such as `#[test]` or
`#[rstest]`. `impl-type` excludes trait implementations and `impl-trait` includes
`impl Trait for Type`. `mod-tests` selects modules named `tests`. `unsafe` selects the
entire unsafe construct: a complete unsafe function, unsafe block, unsafe trait, or
unsafe impl. It therefore includes function names and block bodies, not merely the
`unsafe` keyword. Identifier scopes select token text, not surrounding punctuation.

## Spec 18

Go scopes use `--go VALUE`:

```text
comments, strings, imports, expression, type-def, type-alias,
struct, struct~<PATTERN>, interface, interface~<PATTERN>,
const, var, func, func~<PATTERN>, method, free-func, init-func,
type-params, defer, select, go, switch, labeled, goto, struct-tags
```

Comments include `//` and `/*...*/`. Strings include interpreted and raw string
contents except import paths and struct tags; `struct-tags` selects the latter.
Thus `import "context"` is unchanged by `--go strings --upper`, while
`var x = "hello"` becomes `var x = "HELLO"`. Imports select import
paths/specifications. `expression` selects expressions. `type-def` is the full
type declaration while `type-alias` is an alias assignment. Struct/interface scopes
select complete named type declarations; name patterns filter the declared identifier.
`func` includes methods and free functions, while `method`, `free-func`, and `init-func`
split them. Statement scopes select their complete statement/block. Vendor directories
whose path component is exactly `vendor` are excluded during automatic Go discovery;
substrings in unrelated absolute/parent directory components do not cause exclusion.

## Spec 19

C scopes use `--c VALUE`:

```text
comments, strings, includes, type-def, enum, struct, variable, function,
function-def, function-decl, switch, if, for, while, do, union,
identifier, declaration, call-expression
```

Comments are lexical token scopes. `strings` selects ordinary string contents and also
quoted and angle-bracket include targets: `#include <stdio.h>`,
`#include "helpers.h"`, and `"hello"` become `<STDIO.H>`, `"HELPERS.H"`, and
`"HELLO"` under uppercase. `includes` selects complete include target/directive text.
`function-decl` is precisely the function-declarator node in both prototypes and
definitions: it includes the function name, parameter types and parameter names, but
excludes the return type and definition body. For example,
`void print_array(int* arr, int size) { ... }` becomes
`void PRINT_ARRAY(INT* ARR, INT SIZE) { ... }`.

The generic `function` scope is the union of those function-declarator ranges and
complete call expressions; it does not select an entire function definition. Thus
`int factorial(int n) { return helper(n); }` becomes
`int FACTORIAL(INT N) { return HELPER(N); }`. `function-def`, `call-expression`, the
type/variable/declaration scopes, and control-flow values select their corresponding C
syntax nodes. Nested constructs and pointer parameters must parse. `identifier`
selects every identifier token. `.c` and `.h` are C files by default; an explicit glob
may feed another extension through the C parser.

## Spec 20

C# scopes use `--csharp VALUE` or alias `--cs VALUE`:

```text
comments, strings, usings, struct, enum, interface, class, method,
variable-declaration, property, constructor, destructor, field,
attribute, identifier
```

Comments include inline, block, XML, and documentation comments with markers. Strings
include ordinary, verbatim, and interpolated literal text (quotes included for ordinary
and verbatim strings, while interpolation expressions are excluded). `usings` selects
whole dotted using targets. Struct/enum/interface/class/method/variable/property/
constructor/destructor/field select complete definitions. `attribute` selects the
attribute name; `identifier` selects identifier tokens. Multiple same-language scopes
intersect/union per Spec 14. Automatic discovery uses `.cs`.

## Spec 21

TypeScript scopes use `--typescript VALUE` or alias `--ts VALUE`:

```text
comments, strings, imports, function, async-function, sync-function,
method, constructor, class, enum, interface, try-catch, var-decl,
let, const, var, type-params, type-alias, namespace, export
```

Comments include line and block comments. Strings select literal/template text while
preserving surrounding code. Imports select module specifiers. `function` contains
all function declarations; async/sync split them. `method` and `constructor` select
complete class members. Class, enum, interface, try/catch/finally, namespace, and export
select complete constructs. `var-decl` covers declarations introduced by all three
keywords but its selected range begins after `let`, `const`, or `var`; the keyword is
not selected. Under uppercase, for example, `var globalCounter = 0;` becomes
`var GLOBALCOUNTER = 0;`. The `let`, `const`, and `var` scopes select their respective
complete declarations. Type parameters and aliases select their corresponding
constructs. Automatic discovery uses `.ts` and
`.tsx`, and does not process `.js` merely because it resembles TypeScript.

## Spec 22

HCL/Terraform scopes use `--hcl VALUE`:

```text
variable, resource, data, output, provider, required-providers,
terraform, locals, module, variables, resource-names, resource-types,
data-names, data-sources, comments, strings
```

The singular block kinds select each complete labeled block, including nested bodies.
`required-providers` selects declarations inside the Terraform
`required_providers` object and uniquely permits `required-providers~<PATTERN>` to
filter provider names. `variables` selects both variable declaration labels and
`var.NAME` usages. Resource/data name and type/source scopes select both declaration
labels and references. Comments include `#`, `//`, and block forms. Strings select
literal and heredoc contents, including strings nested in lists/maps/interpolations,
but exclude quoted block labels. Thus the two labels in
`resource "aws_security_group" "complex_sg" {` remain unchanged under string
transformations while an attribute value such as `"complex-sg"` is transformed.
Parsing must tolerate incomplete HCL and leave unselected text untouched. Automatic
discovery uses `.hcl` and `.tf`.

## Spec 23

Each language also supports `--LANG-query QUERY` and
`--LANG-query-file PATH` (using `csharp` and `typescript` in full). The inline value or
UTF-8 file is a tree-sitter-style S-expression query over that language's syntax tree.
The required query subset supports node kinds, nesting, named fields (`name:`), captures
(`@capture`), multiple top-level patterns/captures, quoted literals, and standard
predicates such as `#match?` and `#not-eq?`.

Every captured node contributes its byte range. A capture whose name starts exactly
`_SRGN_IGNORE` subtracts its range from the union of normal captures. For example a Go
query capturing a whole function and `(comment) @_SRGN_IGNORE` transforms the function
except its comments. Query files and inline queries behave identically.

Missing/unreadable query files fail. Invalid syntax, node types, impossible patterns,
or predicate arity fail with status 1 and begin
`Error: Error occurred while creating a tree-sitter query: Query error at LINE:COLUMN.`
The message identifies `Invalid syntax`, `Invalid node type NAME`, `Impossible pattern`,
or `Invalid predicate` as appropriate. A prepared scope and a custom query option for
the same language cannot be combined. For
`--python def --python-query '(comment) @c' --upper`, argument parsing returns 2,
writes no stdout, and stderr is exactly:

```text
error: the argument '--python <PYTHON>' cannot be used with '--python-query <TREE-SITTER-QUERY-VALUE>'

Usage: executable --python <PYTHON> --upper [SCOPE] [-- <REPLACEMENT>]

For more information, try '--help'.
```

For the invalid TypeScript query `(function_declaration`, status is 1 and stderr is
exactly:

```text
Error: Error occurred while creating a tree-sitter query: Query error at 1:22. Invalid syntax:
(function_declaration
                     ^
```

One HCL compatibility edge is normative: the query-file text
`(block (identifier) @id (#eq? @id "variable")) @block` is rejected as an impossible
pattern at its `identifier` child and returns exactly
`Error: Error occurred while creating a tree-sitter query: Query error at 2:3. Impossible pattern:`
followed by the offending line and caret. A simpler HCL comment query is accepted but
does not select the comment: `--hcl-query '(comment) @capture' --upper` on
`x=1 # hello\n` returns 0 with no diagnostic and emits the input unchanged.

## Spec 24

For stdin, `--line-numbers` changes output into one record for every input line,
including lines without matches. This happens whether or not an action is active:

```text
SOURCE:LINE:RANGES:transformed complete line
```

LINE is 1-based. RANGES is empty for an unmatched line; otherwise it is a semicolon
list of original, 0-based, half-open byte columns. `--only-matching` instead omits every
line without a selected match, omits LINE unless `--line-numbers` is also present, but
still prints the full transformed line rather than only the substring. With both flags,
use `SOURCE:LINE:RANGES:line`; with only matching, use `SOURCE:RANGES:line`.

Normative examples:

```text
--line-numbers, `world`, upper on `hello world\n`
  => (stdin):1:6-11:hello WORLD\n

--only-matching, `ab`, upper on `ab cd ab ef\nno match\nab gh ab\n`
  => (stdin):0-2;6-8:AB cd AB ef\n
     (stdin):0-2;6-8:AB gh AB\n

both flags, `match`, upper on `line 1\nmatch 2\nline 3\nmatch 4\n`
  => (stdin):2:0-5:MATCH 2\n
     (stdin):4:0-5:MATCH 4\n

--line-numbers, `world`, no action on `hello\nworld\ntest`
  => (stdin):1::hello\n
     (stdin):2:0-5:world\n
     (stdin):3::test
```

The last record in that example has no final line feed, preserving the unterminated
final input line. The no-action invocation also emits the Spec 4 no-action log to
stderr and returns 0.

Ordinary in-place file mutation reports changed filenames only on stdout even when the
view flags are present. The view flags can nevertheless change the bytes written into
the file: with both `--line-numbers` and `--only-matching`, scope `hello`, `--upper`,
and a glob selecting `a.txt` containing `hello\n`, stdout is `a.txt\n` and the new
file content is `a.txt:1:0-5:HELLO\n`. File content records are also used in language
search mode and dry-run mode.

Deleting a match leaves RANGES empty in the emitted stdin record because no transformed
range remains, while the full changed line is shown. A trailing final newline yields
records for the actual terminated lines, not a spurious extra fifth line.

## Spec 25

`--fail-any` returns status 1 before applying actions if any final selected range
exists, with stderr containing exactly the application error line
`Error: Error applying: Some input was in scope\n` (logging may add a standard prefix
in configurations that enable it). If nothing is selected it succeeds and otherwise
passes through normally.

`--fail-none` does the inverse: no selected ranges returns 1 and
`Error: Error applying: No input was in scope\n`; a nonempty selection succeeds.
When both flags are supplied, `fail-any` is evaluated first. Language search mode also
fails with “No input was in scope” whenever the language scopes yield no ranges,
even without explicit `--fail-none`. A language scope that yields nothing also causes
`--fail-any` to report “No input was in scope”, because the language scoping operation
itself fails before the flag can find a range.

## Spec 26

`-G`/`--glob GLOB` requests recursive file processing instead of stdin. Supported glob
syntax includes `*`, `?`, character classes, literal path components, filenames with
spaces/dashes/underscores, and recursive `**`. `**/*.txt` also matches a root-level
`.txt` file. An explicit glob overrides a language's normal extension filter and sends
every matched text file through the requested language parser. Paths printed to stdout
use `/` and are relative to the current working
directory when the glob is relative. An absolute glob may print the corresponding path.

Files with valid UTF-8 that are actually changed are overwritten in place and their
paths are printed once, followed by `\n`. Unchanged and empty files are not listed.
An embedded NUL does not make an otherwise valid UTF-8 file ineligible: with scope
`hello` and `--upper`, a file containing `hello\0world` becomes `HELLO\0world` and is
listed.
Mode bits, including executability, are preserved. Only matched files are touched.
Without `--sorted`, order may reflect parallel traversal; `--threads N` accepts any
positive integer and processes all files (N=1 is sequential). `--sorted` forces
lexicographic path order and disables parallel ordering. `--threads=2` is valid;
zero fails with status 2 and mentions `number would be zero for non-zero type`.
When written as two tokens, `--threads -1` instead treats `-1` as an option-like
unexpected argument, returns 2, writes no stdout, and stderr is exactly:

```text
error: unexpected argument '-1' found

  tip: to pass '-1' as a value, use '-- -1'

Usage: executable [OPTIONS] [SCOPE] [-- <REPLACEMENT>]

For more information, try '--help'.
```

No glob matches is normally success with no output. `--fail-no-files` changes this to
status 1 and exactly `Error: No files found\n` on stderr.

## Spec 27

When no explicit glob is supplied but a language scope is active and stdin is not
readable, files are recursively discovered from the current directory:

| Language | recognized files |
|---|---|
| Python | `.py`, plus extensionless files whose first line uses `python` or `python3` |
| Rust | `.rs` |
| Go | `.go`, excluding any path component exactly `vendor` |
| C | `.c`, `.h` |
| C# | `.cs` |
| TypeScript | `.ts`, `.tsx` |
| HCL | `.hcl`, `.tf` |

Python shebang recognition accepts `#!/usr/bin/env python`, `python3`, optional
interpreter flags, direct paths such as `#!/bin/python3`, and CRLF termination. Files
identified by extension do not need a shebang. Discovery recursively includes nested
directories and excludes other extensions.

Hidden files/directories are skipped by default even when a glob would otherwise match;
`-H`/`--hidden` includes them. Git ignore rules are honored by default inside a Git
worktree; `--gitignored` includes ignored paths. Ordinary ignore behavior must not hide
explicitly allowed visible files.

## Spec 28

Input-source selection uses `--stdin-detection` with values `auto` (default),
`force-readable`, and `force-unreadable`. Auto treats piped input as readable.
Readable stdin takes precedence over a requested glob; when both are present, process
stdin only, leave files unchanged, and warn on stderr:

```text
Detected stdin, and request for files: will use stdin and ignore files.
```

Force-unreadable ignores provided stdin bytes when a glob requests files or a language
scope enables file discovery, and processes those requested/discovered files. With no
glob and no language scope, however, supplied stdin remains the fallback input despite
`--stdin-detection=force-unreadable`. In an otherwise empty directory, that option
alone with stdin `ignored` returns 0 and writes exactly `ignored` to stdout.
`--stdout-detection` accepts `auto` (default), `force-tty`, and `force-pipe`; forced
values must not change the plain captured text used here or add ANSI escapes.

`--dry-run` applies only to file processing. It never modifies a file. Instead, for
every would-change line it writes the original and transformed record consecutively,
using the same path/line/range record notation. For example, uppercasing all of
`hello world\n` in `test.txt` produces exactly:

```text
test.txt:1:0-11:hello world
test.txt:1:0-11:HELLO WORLD
```

Multiple match ranges are semicolon-separated on both before/after records. An action
that produces no textual change may still show two identical records when the language
scope selected content.

## Spec 29

All textual processing is UTF-8. Invalid UTF-8 on stdin fails with status 1 and stderr
containing `did not contain valid UTF-8`. During broad file walks, invalid-UTF-8 files
are skipped silently and left byte-for-byte intact. An embedded NUL byte is valid input
for both stdin and files: it is preserved outside selected ranges and may coexist with
transformations. In a broad `*.txt` walk with scope `hello` and `--upper`, an
invalid-UTF-8 file containing `hello` followed by byte `FF` and `world` remains intact,
while a file containing `hello\0world` is changed to `HELLO\0world`.

Line endings are data. Preserve LF, CRLF, lone CR, mixed endings, and missing final
newline exactly unless selected. In particular, syntax scopes that end immediately
before a CRLF must never leave an orphan `\r`: deleting whole-line Python/Rust comments
from CRLF files keeps each `\r\n`, and transforming raw multiline Go strings preserves
internal CRLF. Examples:

```text
Python `# Comment\r\nx = 42\r\n`, comment `.*` deletion => `\r\nx = 42\r\n`
mixed `# DOS\r\n# Unix\nx = 3\r\n` deletion => `\r\n\nx = 3\r\n`
```

## Spec 30

The following uppercase, case-sensitive environment variables provide defaults for
the corresponding CLI fields:

```text
UPPER LOWER TITLECASE NORMALIZE SQUEEZE INVERT LITERAL_STRING
GERMAN_PREFER_ORIGINAL GERMAN_NAIVE
REPLACE
C CSHARP GO HCL PYTHON RUST TYPESCRIPT
C_QUERY CSHARP_QUERY GO_QUERY PYTHON_QUERY RUST_QUERY TYPESCRIPT_QUERY
C_QUERY_FILE CSHARP_QUERY_FILE GO_QUERY_FILE PYTHON_QUERY_FILE RUST_QUERY_FILE TYPESCRIPT_QUERY_FILE
```

`HCL_QUERY` and `HCL_QUERY_FILE` are exceptions: despite the environment annotations
shown by long help, they are ignored rather than supplying defaults. With positional
scope `hello`, `--upper`, input `x=1 # hello\n`, and `HCL_QUERY=(comment) @c`, the
program returns 0, emits the input unchanged, and writes no diagnostic. Pointing
`HCL_QUERY_FILE` at a UTF-8 file containing `(comment) @c` has the same result.

Boolean fields accept exactly lowercase `true` and `false`. `false` disables the
default; a matching CLI flag overrides it to true. Empty or other boolean values fail
argument parsing and name the corresponding CLI option rather than the environment
variable. In particular, `UPPER=` produces:

```text
error: a value is required for '--upper' but none was supplied
  [possible values: true, false]

For more information, try '--help'.
```

`UPPER=1` instead starts with `error: invalid value '1' for '--upper'`, then prints
the same possible-values line, blank line, and help hint. Neither form has a Usage
line. `REPLACE` is a string and an explicitly present empty value is a valid deleting
replacement. A CLI replacement overrides `REPLACE`. CLI language/query values
override their corresponding default and undergo the same validation. Differently
cased variable names such as `upper` and `Replace` are ignored.

## Spec 31

Logging is written only to stderr. `RUST_LOG` controls the base level and accepts the
usual `off`, `error`, `warn`, `info`, `debug`, and `trace` filters; an unrecognized
filter must not crash. Default level is error. Consequently the no-action message has
an `ERROR srgn` prefix by default, while `RUST_LOG=off` suppresses it. At `info`, sorted
file traversal logs `Will walk file tree sequentially, in sorted order`.

`-v`/`--verbose` may repeat or cluster and raises verbosity one level per occurrence,
capped at trace. Excess occurrences do not fail and emit a warning containing:

```text
Requested additional verbosity on top of env default exceeds maximum, will use maximum
```

Normal successful composable-action invocations at default logging produce no stderr.
Successful squeeze-only invocations are the exception described in Spec 11.

## Spec 32

`-V`/`--version` succeeds and writes exactly `srgn 0.14.1\n` to stdout. Short and long
forms are identical. It writes no stderr.

`--completions SHELL` accepts exactly `bash`, `elvish`, `fish`, `powershell`, and `zsh`.
It returns 0 and nonempty shell-appropriate completion source mentioning `srgn` and its
options. Bash output contains a completion function (`_srgn` or `complete`) and
`--help`, `--upper`, `--lower`; zsh contains `#compdef` or `_srgn`; fish contains
`complete`; zsh output includes `--python`. An invalid shell is an enumerated-value
argument error.

Unknown options and missing valued options use clap-style stderr and return 2. Unknown
options include a Usage line and `For more information, try '--help'.`; missing valued
options include the help hint but omit the Usage line. For example, `--glob` writes
exactly:

```text
error: a value is required for '--glob <GLOB>' but none was supplied

For more information, try '--help'.
```

Enumerated-value errors also return 2 and include the help hint and possible-values
list, but the observed detection and language-scope errors below do not include a
Usage line. Representative required substrings:

```text
unexpected argument '--nonexistent-flag' found
tip: to pass '--nonexistent-flag' as a value
a value is required for '--glob <GLOB>'
invalid value 'bogus' for '--stdin-detection <STDIN_DETECTION>'
possible values: auto, force-readable, force-unreadable
invalid value 'bogus' for '--stdout-detection <STDOUT_DETECTION>'
possible values: auto, force-tty, force-pipe
```

More precisely, `--stdin-detection bogus` and `--stdout-detection bogus` emit the
corresponding `invalid value` and bracketed possible-values lines, a blank line, and
the help hint, with no Usage line. Invalid prepared-language values behave the same
way. For example, `--rust invalid_value` and `--python not_a_query` identify
`--rust <RUST>` and `--python <PYTHON>` respectively, print `possible values:` with
the values enumerated in Specs 17 and 16, and omit Usage.

## Spec 33

Help is special and deterministic. `--help` produces long help; `-h` produces a
shorter summary. Both return 0, write only stdout, contain exactly one `Usage:` line,
do not contain `Commands:`, `Subcommands:`, or the word `subcommand`, and use the
single-command usage from Spec 1. Help wins when combined with ordinary valid flags,
unknown flags, a preceding scope, or another help occurrence; for example
`--help --nonexistent`, `pattern --help`, and `--help --help` all succeed and show the
same main help instead of validating the other tokens.
The output must not use terminal color when captured. The exact required outputs are
included below; they are normative including wrapping, spaces, blank lines, and final
newline.

The exact stdout for `--help` is:

```text
A grep-like tool which understands source code syntax and allows for manipulation in
addition to search

Usage: executable [OPTIONS] [SCOPE] [-- <REPLACEMENT>]

Arguments:
  [SCOPE]
          Scope to apply to, as a regular expression pattern.
          
          If string literal mode is requested, will be interpreted as a literal
          string.
          
          Actions will apply their transformations within this scope only.
          
          The default is the global scope, matching the entire input. Where that
          default is meaningless or dangerous (e.g., deletion), this argument is
          required.
          
          [default: .*]

Options:
      --completions <SHELL>
          Print shell completions for the given shell.
          
          [possible values: bash, elvish, fish, powershell, zsh]

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version

Composable Actions:
  -u, --upper
          Uppercase anything in scope.
          
          [env: UPPER=]

  -l, --lower
          Lowercase anything in scope.
          
          [env: LOWER=]

  -t, --titlecase
          Titlecase anything in scope.
          
          [env: TITLECASE=]

  -n, --normalize
          Normalize (Normalization Form D) anything in scope, and throw away marks.
          
          [env: NORMALIZE=]

  -g, --german
          Perform substitutions on German words, such as 'Abenteuergruesse' to
          'Abenteuergrüße', for anything in scope.
          
          ASCII spellings for Umlauts (ae, oe, ue) and Eszett (ss) are replaced by
          their respective native Unicode (ä, ö, ü, ß).
          
          Arbitrary compound words are supported.
          
          Words legally containing alternative spellings are not modified.
          
          Words require correct spelling to be detected.

  -S, --symbols
          Perform substitutions on symbols, such as '!=' to '≠', '->' to '→', on
          anything in scope.
          
          Helps translate 'ASCII art' into native Unicode representations.

  [REPLACEMENT]
          Replace anything in scope with this value.
          
          Variables are supported: if a regex pattern was used for scoping and
          captured content in named or numbered capture groups, access these in the
          replacement value using `$1` etc. for numbered, `$NAME` etc. for named
          capture groups.
          
          This action is specially treated as a positional argument for ergonomics and
          compatibility with `tr`.
          
          If given, will run before any other action.
          
          [env: REPLACE=]

Standalone Actions (only usable alone):
  -d, --delete
          Delete anything in scope.
          
          Cannot be used with any other action: there is no point in deleting and
          performing any other processing. Sibling actions would either receive empty
          input or have their work wiped.

  -s, --squeeze
          Squeeze consecutive occurrences of scope into one.
          
          [env: SQUEEZE=]
          [aliases: squeeze-repeats]

Options (global):
  -G, --glob <GLOB>
          Glob of files to work on (instead of reading stdin).
          
          If actions are applied, they overwrite files in-place.
          
          For supported glob syntax, see:
          <https://docs.rs/glob/0.3.1/glob/struct.Pattern.html>
          
          Names of processed files are written to stdout.

      --fail-no-files
          Fail if working on files (e.g. globbing is requested) but none are found.
          
          Processing no files is not an error condition in itself, but might be an
          unexpected outcome in some contexts. This flag makes the condition explicit.

      --dry-run
          Do not destructively overwrite files, instead print rich diff only.
          
          The diff details the names of files which would be modified, alongside all
          changes inside those files which would be performed outside of dry running.
          It is similar to git diff with word diffing enabled.

  -i, --invert
          Undo the effects of passed actions, where applicable.
          
          Requires a 1:1 mapping between replacements and original, which is currently
          available only for:
          
          - symbols: '≠' <-> '!=' etc.
          
          Other actions:
          
          - german: inverting e.g. 'Ä' is ambiguous (can be 'Ae' or 'AE')
          
          - upper, lower, deletion, squeeze: inversion is impossible as information is
            lost
          
          These may still be passed, but will be ignored for inversion and applied
          normally.
          
          [env: INVERT=]

  -L, --literal-string
          Do not interpret the scope as a regex. Instead, interpret it as a literal
          string. Will require a scope to be passed.
          
          [env: LITERAL_STRING=]

      --fail-any
          If anything at all is found to be in scope, fail.
          
          The default is to continue processing normally.

      --fail-none
          If nothing is found to be in scope, fail.
          
          The default is to return the input unchanged (without failure).

  -j, --join-language-scopes
          Join (logical 'OR') multiple language scopes, instead of intersecting them.
          
          The default when multiple language scopes are given is to intersect their
          scopes, left to right. For example, `--go func --go strings` will first
          scope down to `func` bodies, then look for strings only within those. This
          flag instead joins (in the set logic sense) all scopes. The example would
          then scope any `func` bodies, and any strings, anywhere. Language scopers
          can then also be given in any order.
          
          No effect if only a single language scope is given. Also does not affect
          non-language scopers (regex pattern etc.), which always intersect.

  -H, --hidden
          Do not ignore hidden files and directories.

      --gitignored
          Do not ignore `.gitignore`d files and directories.

      --sorted
          Process files in lexicographically sorted order, by file path.
          
          In search mode, this emits results in sorted order. Otherwise, it processes
          files in sorted order.
          
          Sorted processing disables parallel processing.

      --stdin-detection <STDIN_DETECTION>
          Control heuristics for stdin readability detection, and force to value.
          
          [default: auto]

          Possible values:
          - auto:             Automatically detect if stdin is readable
          - force-readable:   Act as if stdin is readable
          - force-unreadable: Act as if stdin is not readable

      --stdout-detection <STDOUT_DETECTION>
          Control heuristics for stdout detection, and potentially force to value.
          
          [default: auto]

          Possible values:
          - auto:       Automatically detect if stdout is a TTY and act accordingly
          - force-tty:  Act as if stdout is a TTY
          - force-pipe: Act as if stdout is not a TTY, e.g. a pipe, redirect

      --threads <THREADS>
          Number of threads to run processing on, when working with files.
          
          If not specified, will default to available parallelism. Set to 1 for
          sequential, deterministic (but not sorted) output.

  -v, --verbose...
          Increase log verbosity level.
          
          The base log level to use is read from the `RUST_LOG` environment variable
          (if unspecified, defaults to 'error'), and increased according to the number
          of times this flag is given, maxing out at 'trace' verbosity.

Language scopes:
      --c <C>
          Scope C code using a prepared query.
          
          [env: C=]

          Possible values:
          - comments:        Comments (single- and multi-line)
          - strings:         Strings
          - includes:        Includes
          - type-def:        Type definitions
          - enum:            `enum` definitions
          - struct:          `struct` type definitions
          - variable:        Variable definitions
          - function:        All functions usages (declarations and calls)
          - function-def:    Function definitions
          - function-decl:   Function declaration
          - switch:          `switch` blocks
          - if:              `if` blocks
          - for:             `for` blocks
          - while:           `while` blocks
          - do:              `do` blocks
          - union:           `union` blocks
          - identifier:      Identifier
          - declaration:     Declaration
          - call-expression: Call expression

      --c-query <TREE-SITTER-QUERY-VALUE>
          Scope C code using a custom tree-sitter query.
          
          [env: C_QUERY=]

      --c-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope C code using a custom tree-sitter query from file.
          
          [env: C_QUERY_FILE=]

      --csharp <CSHARP>
          Scope C# code using a prepared query.
          
          [env: CSHARP=]
          [aliases: cs]

          Possible values:
          - comments:             Comments (including XML, inline, doc comments)
          - strings:              Strings (incl. verbatim, interpolated; incl. quotes,
            except for interpolated)
          - usings:               `using` directives (including periods)
          - struct:               `struct` definitions (in their entirety)
          - enum:                 `enum` definitions (in their entirety)
          - interface:            `interface` definitions (in their entirety)
          - class:                `class` definitions (in their entirety)
          - method:               Method definitions (in their entirety)
          - variable-declaration: Variable declarations (in their entirety)
          - property:             Property definitions (in their entirety)
          - constructor:          Constructor definitions (in their entirety)
          - destructor:           Destructor definitions (in their entirety)
          - field:                Field definitions on types (in their entirety)
          - attribute:            Attribute names
          - identifier:           Identifier names

      --csharp-query <TREE-SITTER-QUERY-VALUE>
          Scope C# code using a custom tree-sitter query.
          
          [env: CSHARP_QUERY=]

      --csharp-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope C# code using a custom tree-sitter query from file.
          
          [env: CSHARP_QUERY_FILE=]

      --go <GO>
          Scope Go code using a prepared query.
          
          [env: GO=]

          Possible values:
          - comments:            Comments (single- and multi-line)
          - strings:             Strings (interpreted and raw; excluding struct tags)
          - imports:             Imports
          - expression:          Expressions (all of them!)
          - type-def:            Type definitions
          - type-alias:          Type alias assignments
          - struct:              `struct` type definitions
          - struct~<PATTERN>:    Like struct, but only considers items whose name matches
            PATTERN.
          - interface:           `interface` type definitions
          - interface~<PATTERN>: Like interface, but only considers items whose name
            matches PATTERN.
          - const:               `const` specifications
          - var:                 `var` specifications
          - func:                `func` definitions
          - func~<PATTERN>:      Like func, but only considers items whose name matches
            PATTERN.
          - method:              Method `func` definitions (`func (recv Recv) SomeFunc()`)
          - free-func:           Free `func` definitions (`func SomeFunc()`)
          - init-func:           `func init()` definitions
          - type-params:         Type parameters (generics)
          - defer:               `defer` blocks
          - select:              `select` blocks
          - go:                  `go` blocks
          - switch:              `switch` blocks
          - labeled:             Labeled statements
          - goto:                `goto` statements
          - struct-tags:         Struct tags

      --go-query <TREE-SITTER-QUERY-VALUE>
          Scope Go code using a custom tree-sitter query.
          
          [env: GO_QUERY=]

      --go-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope Go code using a custom tree-sitter query from file.
          
          [env: GO_QUERY_FILE=]

      --hcl <HCL>
          Scope HashiCorp Configuration Language code using a prepared query.
          
          [env: HCL=]

          Possible values:
          - variable:           `variable` blocks (in their entirety)
          - resource:           `resource` blocks (in their entirety)
          - data:               `data` blocks (in their entirety)
          - output:             `output` blocks (in their entirety)
          - provider:           `provider` blocks (in their entirety)
          - required-providers: All `required_providers` from the `terraform` block
          - terraform:          `terraform` blocks (in their entirety)
          - locals:             `locals` blocks (in their entirety)
          - module:             `module` blocks (in their entirety)
          - variables:          Variable declarations and usages
          - resource-names:     `resource` name declarations and usages
          - resource-types:     `resource` type declarations and usages
          - data-names:         `data` name declarations and usages
          - data-sources:       `data` source declarations and usages
          - comments:           Comments
          - strings:            Literal strings

      --hcl-query <TREE-SITTER-QUERY-VALUE>
          Scope HashiCorp Configuration Language code using a custom tree-sitter query.
          
          [env: HCL_QUERY=]

      --hcl-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope HashiCorp Configuration Language code using a custom tree-sitter query
          from file.
          
          [env: HCL_QUERY_FILE=]

      --python <PYTHON>
          Scope Python code using a prepared query.
          
          [env: PYTHON=]
          [aliases: py]

          Possible values:
          - comments:             Comments
          - strings:              Strings (raw, byte, f-strings; interpolation not
            included)
          - imports:              Module names in imports (incl. periods; excl.
            `import`/`from`/`as`/`*`)
          - doc-strings:          Docstrings (not including multi-line strings)
          - function-names:       Function names, at the definition site
          - function-calls:       Function calls
          - class:                Class definitions (in their entirety)
          - def:                  Function definitions (*all* `def` block in their
            entirety)
          - async-def:            Async function definitions (*all* `async def` block in
            their entirety)
          - methods:              Function definitions inside `class` bodies
          - class-methods:        Function definitions decorated as `classmethod` (excl.
            the decorator)
          - static-methods:       Function definitions decorated as `staticmethod` (excl.
            the decorator)
          - with:                 `with` blocks (in their entirety)
          - try:                  `try` blocks (in their entirety)
          - lambda:               `lambda` statements (in their entirety)
          - globals:              Global, i.e. module-level variables
          - variable-identifiers: Identifiers for variables (left-hand side of
            assignments)
          - types:                Types in type hints
          - identifiers:          Identifiers (variable names, ...)

      --python-query <TREE-SITTER-QUERY-VALUE>
          Scope Python code using a custom tree-sitter query.
          
          [env: PYTHON_QUERY=]

      --python-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope Python code using a custom tree-sitter query from file.
          
          [env: PYTHON_QUERY_FILE=]

      --rust <RUST>
          Scope Rust code using a prepared query.
          
          [env: RUST=]
          [aliases: rs]

          Possible values:
          - comments:         Comments (line and block styles; excluding doc comments;
            comment chars incl.)
          - doc-comments:     Doc comments (comment chars included)
          - uses:             Use statements (paths only; excl. `use`/`as`/`*`)
          - strings:          Strings (regular, raw, byte; includes interpolation parts in
            format strings!)
          - attribute:        Attributes like `#[attr]`
          - struct:           `struct` definitions
          - struct~<PATTERN>: Like struct, but only considers items whose name matches
            PATTERN.
          - priv-struct:      `struct` definitions not marked `pub`
          - pub-struct:       `struct` definitions marked `pub`
          - pub-crate-struct: `struct` definitions marked `pub(crate)`
          - pub-self-struct:  `struct` definitions marked `pub(self)`
          - pub-super-struct: `struct` definitions marked `pub(super)`
          - enum:             `enum` definitions
          - enum~<PATTERN>:   Like enum, but only considers items whose name matches
            PATTERN.
          - priv-enum:        `enum` definitions not marked `pub`
          - pub-enum:         `enum` definitions marked `pub`
          - pub-crate-enum:   `enum` definitions marked `pub(crate)`
          - pub-self-enum:    `enum` definitions marked `pub(self)`
          - pub-super-enum:   `enum` definitions marked `pub(super)`
          - enum-variant:     Variant members of `enum` definitions
          - fn:               Function definitions
          - fn~<PATTERN>:     Like fn, but only considers items whose name matches
            PATTERN.
          - impl-fn:          Function definitions inside `impl` blocks (associated
            functions/methods)
          - priv-fn:          Function definitions not marked `pub`
          - pub-fn:           Function definitions marked `pub`
          - pub-crate-fn:     Function definitions marked `pub(crate)`
          - pub-self-fn:      Function definitions marked `pub(self)`
          - pub-super-fn:     Function definitions marked `pub(super)`
          - const-fn:         Function definitions marked `const`
          - async-fn:         Function definitions marked `async`
          - unsafe-fn:        Function definitions marked `unsafe`
          - extern-fn:        Function definitions marked `extern`
          - test-fn:          Function definitions with attributes containing `test`
            (`#[test]`, `#[rstest]`, ...)
          - trait:            `trait` definitions
          - trait~<PATTERN>:  Like trait, but only considers items whose name matches
            PATTERN.
          - impl:             `impl` blocks
          - impl-type:        `impl` blocks for types (`impl SomeType {}`)
          - impl-trait:       `impl` blocks for traits on types (`impl SomeTrait for
            SomeType {}`)
          - mod:              `mod` blocks
          - mod~<PATTERN>:    Like mod, but only considers items whose name matches
            PATTERN.
          - mod-tests:        `mod tests` blocks
          - type-def:         Type definitions (`struct`, `enum`, `union`)
          - identifier:       Identifiers
          - type-identifier:  Identifiers for types
          - closure:          Closure definitions
          - unsafe:           `unsafe` keyword usages (`unsafe fn`, `unsafe` blocks,
            `unsafe Trait`, `unsafe impl Trait`)

      --rust-query <TREE-SITTER-QUERY-VALUE>
          Scope Rust code using a custom tree-sitter query.
          
          [env: RUST_QUERY=]

      --rust-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope Rust code using a custom tree-sitter query from file.
          
          [env: RUST_QUERY_FILE=]

      --typescript <TYPESCRIPT>
          Scope TypeScript code using a prepared query.
          
          [env: TYPESCRIPT=]
          [aliases: ts]

          Possible values:
          - comments:       Comments
          - strings:        Strings (literal, template)
          - imports:        Imports (module specifiers)
          - function:       Any `function` definitions
          - async-function: `async function` definitions
          - sync-function:  Non-`async function` definitions
          - method:         Method definitions
          - constructor:    `constructor` method definitions
          - class:          `class` definitions
          - enum:           `enum` definitions
          - interface:      `interface` definitions
          - try-catch:      `try`/`catch`/`finally` blocks
          - var-decl:       Variable declarations (`let`, `const`, `var`)
          - let:            `let` variable declarations
          - const:          `const` variable declarations
          - var:            `var` variable declarations
          - type-params:    Type (generic) parameters
          - type-alias:     Type alias declarations
          - namespace:      `namespace` blocks
          - export:         `export` blocks

      --typescript-query <TREE-SITTER-QUERY-VALUE>
          Scope TypeScript code using a custom tree-sitter query.
          
          [env: TYPESCRIPT_QUERY=]

      --typescript-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope TypeScript code using a custom tree-sitter query from file.
          
          [env: TYPESCRIPT_QUERY_FILE=]

Options (german):
      --german-prefer-original
          When some original version and its replacement are equally legal, prefer the
          original and do not modify.
          
          For example, "Busse" (original) and "Buße" (replacement) are equally legal
          words: by default, the tool would prefer the latter.
          
          [env: GERMAN_PREFER_ORIGINAL=]

      --german-naive
          Always perform any possible replacement ('ae' -> 'ä', 'ss' -> 'ß', etc.),
          regardless of legality of the resulting word
          
          Useful for names, which are otherwise not modifiable as they do not occur in
          dictionaries. Called 'naive' as this does not perform legal checks.
          
          [env: GERMAN_NAIVE=]
```


The exact stdout for `-h` is:

```text
A grep-like tool which understands source code syntax and allows for manipulation in
addition to search

Usage: executable [OPTIONS] [SCOPE] [-- <REPLACEMENT>]

Arguments:
  [SCOPE]  Scope to apply to, as a regular expression pattern. [default: .*]

Options:
      --completions <SHELL>  Print shell completions for the given shell. [possible
                             values: bash, elvish, fish, powershell, zsh]
  -h, --help                 Print help (see more with '--help')
  -V, --version              Print version

Composable Actions:
  -u, --upper        Uppercase anything in scope. [env: UPPER=]
  -l, --lower        Lowercase anything in scope. [env: LOWER=]
  -t, --titlecase    Titlecase anything in scope. [env: TITLECASE=]
  -n, --normalize    Normalize (Normalization Form D) anything in scope, and throw away
                     marks. [env: NORMALIZE=]
  -g, --german       Perform substitutions on German words, such as 'Abenteuergruesse' to
                     'Abenteuergrüße', for anything in scope.
  -S, --symbols      Perform substitutions on symbols, such as '!=' to '≠', '->' to '→',
                     on
                     anything in scope.
  [REPLACEMENT]  Replace anything in scope with this value. [env: REPLACE=]

Standalone Actions (only usable alone):
  -d, --delete   Delete anything in scope.
  -s, --squeeze  Squeeze consecutive occurrences of scope into one. [env: SQUEEZE=]
                 [aliases: squeeze-repeats]

Options (global):
  -G, --glob <GLOB>
          Glob of files to work on (instead of reading stdin).
      --fail-no-files
          Fail if working on files (e.g. globbing is requested) but none are found.
      --dry-run
          Do not destructively overwrite files, instead print rich diff only.
  -i, --invert
          Undo the effects of passed actions, where applicable. [env: INVERT=]
  -L, --literal-string
          Do not interpret the scope as a regex. Instead, interpret it as a literal
          string. Will require a scope to be passed. [env: LITERAL_STRING=]
      --fail-any
          If anything at all is found to be in scope, fail.
      --fail-none
          If nothing is found to be in scope, fail.
  -j, --join-language-scopes
          Join (logical 'OR') multiple language scopes, instead of intersecting them.
  -H, --hidden
          Do not ignore hidden files and directories.
      --gitignored
          Do not ignore `.gitignore`d files and directories.
      --sorted
          Process files in lexicographically sorted order, by file path.
      --stdin-detection <STDIN_DETECTION>
          Control heuristics for stdin readability detection, and force to value.
          [default: auto] [possible values: auto, force-readable, force-unreadable]
      --stdout-detection <STDOUT_DETECTION>
          Control heuristics for stdout detection, and potentially force to value.
          [default: auto] [possible values: auto, force-tty, force-pipe]
      --threads <THREADS>
          Number of threads to run processing on, when working with files.
  -v, --verbose...
          Increase log verbosity level.

Language scopes:
      --c <C>
          Scope C code using a prepared query. [env: C=] [possible values: comments,
          strings, includes, type-def, enum, struct, variable, function, function-def,
          function-decl, switch, if, for, while, do, union, identifier, declaration,
          call-expression]
      --c-query <TREE-SITTER-QUERY-VALUE>
          Scope C code using a custom tree-sitter query. [env: C_QUERY=]
      --c-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope C code using a custom tree-sitter query from file. [env: C_QUERY_FILE=]
      --csharp <CSHARP>
          Scope C# code using a prepared query. [env: CSHARP=] [aliases: cs] [possible
          values: comments, strings, usings, struct, enum, interface, class, method,
          variable-declaration, property, constructor, destructor, field, attribute,
          identifier]
      --csharp-query <TREE-SITTER-QUERY-VALUE>
          Scope C# code using a custom tree-sitter query. [env: CSHARP_QUERY=]
      --csharp-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope C# code using a custom tree-sitter query from file. [env:
          CSHARP_QUERY_FILE=]
      --go <GO>
          Scope Go code using a prepared query. [env: GO=] [possible values: comments,
          strings, imports, expression, type-def, type-alias, struct, struct~<PATTERN>,
          interface, interface~<PATTERN>, const, var, func, func~<PATTERN>, method,
          free-func, init-func, type-params, defer, select, go, switch, labeled, goto,
          struct-tags]
      --go-query <TREE-SITTER-QUERY-VALUE>
          Scope Go code using a custom tree-sitter query. [env: GO_QUERY=]
      --go-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope Go code using a custom tree-sitter query from file. [env: GO_QUERY_FILE=]
      --hcl <HCL>
          Scope HashiCorp Configuration Language code using a prepared query. [env: HCL=]
          [possible values: variable, resource, data, output, provider,
          required-providers, terraform, locals, module, variables, resource-names,
          resource-types, data-names, data-sources, comments, strings]
      --hcl-query <TREE-SITTER-QUERY-VALUE>
          Scope HashiCorp Configuration Language code using a custom tree-sitter query.
          [env: HCL_QUERY=]
      --hcl-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope HashiCorp Configuration Language code using a custom tree-sitter query
          from file. [env: HCL_QUERY_FILE=]
      --python <PYTHON>
          Scope Python code using a prepared query. [env: PYTHON=] [aliases: py] [possible
          values: comments, strings, imports, doc-strings, function-names, function-calls,
          class, def, async-def, methods, class-methods, static-methods, with, try,
          lambda, globals, variable-identifiers, types, identifiers]
      --python-query <TREE-SITTER-QUERY-VALUE>
          Scope Python code using a custom tree-sitter query. [env: PYTHON_QUERY=]
      --python-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope Python code using a custom tree-sitter query from file. [env:
          PYTHON_QUERY_FILE=]
      --rust <RUST>
          Scope Rust code using a prepared query. [env: RUST=] [aliases: rs] [possible
          values: comments, doc-comments, uses, strings, attribute, struct,
          struct~<PATTERN>, priv-struct, pub-struct, pub-crate-struct, pub-self-struct,
          pub-super-struct, enum, enum~<PATTERN>, priv-enum, pub-enum, pub-crate-enum,
          pub-self-enum, pub-super-enum, enum-variant, fn, fn~<PATTERN>, impl-fn, priv-fn,
          pub-fn, pub-crate-fn, pub-self-fn, pub-super-fn, const-fn, async-fn, unsafe-fn,
          extern-fn, test-fn, trait, trait~<PATTERN>, impl, impl-type, impl-trait, mod,
          mod~<PATTERN>, mod-tests, type-def, identifier, type-identifier, closure,
          unsafe]
      --rust-query <TREE-SITTER-QUERY-VALUE>
          Scope Rust code using a custom tree-sitter query. [env: RUST_QUERY=]
      --rust-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope Rust code using a custom tree-sitter query from file. [env:
          RUST_QUERY_FILE=]
      --typescript <TYPESCRIPT>
          Scope TypeScript code using a prepared query. [env: TYPESCRIPT=] [aliases: ts]
          [possible values: comments, strings, imports, function, async-function,
          sync-function, method, constructor, class, enum, interface, try-catch, var-decl,
          let, const, var, type-params, type-alias, namespace, export]
      --typescript-query <TREE-SITTER-QUERY-VALUE>
          Scope TypeScript code using a custom tree-sitter query. [env: TYPESCRIPT_QUERY=]
      --typescript-query-file <TREE-SITTER-QUERY-FILENAME>
          Scope TypeScript code using a custom tree-sitter query from file. [env:
          TYPESCRIPT_QUERY_FILE=]

Options (german):
      --german-prefer-original  When some original version and its replacement are equally
                                legal, prefer the
                                original and do not modify. [env: GERMAN_PREFER_ORIGINAL=]
      --german-naive            Always perform any possible replacement ('ae' -> 'ä', 'ss'
                                -> 'ß', etc.),
                                regardless of legality of the resulting word [env:
                                GERMAN_NAIVE=]
```
