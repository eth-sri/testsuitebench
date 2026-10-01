# Specification for `executable`

The required artifact is one executable file named exactly `executable`. It is a command-line utility that generates one canonical regular expression from a finite set of example strings. All text described below is UTF-8. In examples, the shown final line break is part of stdout unless stated otherwise.

## Spec 1

`executable` shall implement a CLI named `grex`. A successful generation writes exactly one regular expression followed by `\n` to stdout, writes nothing to stderr, and exits with status 0. The default expression is a compact, anchored, case-sensitive expression that matches each retained input string literally and does not generalize characters unless an option requests it.

Examples:

```text
arguments                    stdout
foo                          ^foo$\n
foo foa                      ^fo[ao]$\n
a b c                        ^[a-c]$\n
hello world                  ^(?:hello|world)$\n
""                           ^$\n
```

The executable must be usable regardless of its absolute location or the caller's current directory and must not require repository source files or network access at runtime.

## Spec 2

The accepted options are:

```text
-f, --file <FILE>
-d, --digits
-D, --non-digits
-s, --spaces
-S, --non-spaces
-w, --words
-W, --non-words
-e, --escape
    --with-surrogates
-r, --repetitions
    --min-repetitions <QUANTITY>          default 1
    --min-substring-length <LENGTH>       default 1
    --no-start-anchor
    --no-end-anchor
    --no-anchors
-x, --verbose
-c, --colorize
-i, --ignore-case
-g, --capture-groups
-h, --help
-v, --version
```

Boolean short options may be provided separately. Long value options accept both `--name value` and `--name=value`. A standalone `--` ends option parsing. Positional input accepts leading hyphens: an unrecognized option-looking value such as `--no-such-flag` or `-a` is a literal test case rather than an unknown-option error. Once the first positional input is encountered, every subsequent argument is positional, even if it spells a recognized option. Thus `-x foo --no-anchors` enables verbose mode and uses `foo` and the literal string `--no-anchors`; `-x --no-anchors foo` enables both options. Literal hyphens are escaped in the generated regex, for example `--no-such-flag` becomes `^\-\-no\-such\-flag$`.

## Spec 3

At least one of positional `INPUT...` or `--file <FILE>` is required, and these two sources are mutually exclusive when `--file` is parsed as an option. With no input, exit 2, emit no stdout, and emit exactly:

```text
error: the following required arguments were not provided:
  --file <FILE>
  <INPUT>...

Usage: grex [OPTIONS] {INPUT...|--file <FILE>}

For more information, try '--help'.
```

If a parsed `--file` and positional inputs are both present, exit 2 and include this exact diagnostic wording on stderr:

```text
error: the argument '--file <FILE>' cannot be used with '[INPUT]...'

Usage: grex [OPTIONS] {INPUT...|--file <FILE>}

For more information, try '--help'.
```

A missing value after `--file` is a status-2 usage error containing `a value is required for '--file <FILE>' but none was supplied`. Supplying a value to a boolean option, such as `--no-start-anchor=foo`, is a status-2 error containing `unexpected value` and the option name.

## Spec 4

Each positional argument is one test case, except a positional argument exactly equal to `-`, which selects stdin input. In stdin mode, read all UTF-8 stdin and split it into test cases at LF or CRLF line endings. A final line need not end in a newline. A lone carriage return is content, not a separator. For example, stdin `foo\nbar\n` produces `^(?:bar|foo)$`, while `line\rwith\rcarriage\rreturns\n` produces `^line\rwith\rcarriage\rreturns$`.

With `-f FILE` or `--file FILE`, read the UTF-8 file and split it by the same rules. With `--file -`, read a filename from stdin (removing its line terminator) and then read test cases from that named file; stdin is not itself the case file in this form. A final unterminated file line is included. CRLF must not leave `\r` in a case. Tabs and all leading, trailing, and repeated spaces in cases are preserved.

Repeated identical cases are deduplicated. Empty cases are discarded if at least one nonempty case exists; if all supplied lines/cases are empty, retain one empty case. Consequently, arguments `"" a ""` produce `^a$`, a file containing `alpha\n\nbeta\n` produces `^(?:alph|bet)a$`, and a nonempty file containing only blank lines produces `^$`.

## Spec 5

File failures are reported without stdout. A nonexistent regular filename, or a nonexistent filename obtained through `--file -`, exits 1 and writes exactly:

```text
error: the specified file could not be found
```

A directory or other file-read error exits nonzero and writes `error: ` followed by the operating-system error and `\n`; for a directory on Linux this is `error: Is a directory (os error 21)\n`. Invalid UTF-8 from stdin or a file must fail nonzero with an encoding/UTF-8 diagnostic rather than generate a lossy expression.

A truly zero-byte file or zero-byte stdin supplies no test cases. The expected 1.4.6 behavior is an uncaught builder panic with exit status 101 and stderr containing `No test cases have been provided for regular expression generation`. This differs from a file/stdin stream containing one or more empty lines, which represents empty cases as described above.

## Spec 6

`-v` and `--version` exit 0, write exactly `grex 1.4.6\n` to stdout, and write no stderr. Version handling takes precedence over generation and other otherwise valid arguments, for example `-x --version foo` has the same output.

`-h` and `--help` exit 0, write help to stdout, and write no stderr. Help begins with `grex `, includes the sentence `grex generates regular expressions from user-provided test cases.`, and contains the exact usage line:

```text
Usage: grex [OPTIONS] {INPUT...|--file <FILE>}
```

It must contain the headings `Input:`, `Digit Options:`, `Whitespace Options:`, `Word Options:`, `Escaping Options:`, `Repetition Options:`, `Anchor Options:`, `Display Options:`, and `Miscellaneous Options:`, and list every option in Spec 2, including such displayed forms as `-f, --file <FILE>`, `-d, --digits`, and `-g, --capture-groups`.

## Spec 7

Treat input as Unicode without normalization. Precomposed and decomposed spellings remain distinct: `café` and `cafe` followed by U+0301 produce `^caf(?:é|é)$`. Preserve CJK, Arabic, Hebrew, emoji, variation selectors, zero-width joiners, and other valid scalar values exactly unless a conversion flag changes them. Extended grapheme clusters must not be corrupted or split in ways that change the accepted strings. For repetition detection, a visible grapheme such as `y` plus U+0306 can act as a repeated substring.

Case is preserved by default. A long case, a large number of cases, or long repeated content must not be truncated. Inputs of at least 10 KiB, files of at least 500 cases, repetition counts of at least 51, and numeric option values of 1,000,000,000 must be handled within normal CLI test time limits.

## Spec 8

Before structural optimization, encode literal regex syntax so that the result continues to match the source text literally. Escape the regex metacharacters backslash, dot, plus, asterisk, question mark, parentheses, square brackets, braces, caret, dollar, pipe, and hyphen with a preceding backslash. Forward slash, `@`, underscore, quotes, percent, and ordinary letters are not escaped. Represent actual tab, carriage return, newline, vertical tab, and form feed content as `\t`, `\r`, `\n`, `\v`, and `\f`, respectively. A literal two-character sequence backslash-plus-`n` becomes `\\n`, not a newline.

Representative results are:

```text
a.b a*c a+d       ^a(?:\*c|\+d|\.b)$
test[0] test[1]   ^test\[[01]\]$
a\b               ^a\\b$
test.txt           ^test\.txt$
```

When a character appears inside a generated bracket class, escape it according to bracket-class syntax. The canonical compact output leaves ordinary literal ASCII spaces as spaces.

## Spec 9

Generation must produce the canonical compact finite-language regex, not merely any expression that matches the examples. Conceptually, perform these deterministic operations:

1. Apply requested case and character conversions to each case.
2. Optionally replace eligible adjacent repetition runs as specified later.
3. Build a deterministic trie accepting precisely the converted cases, then merge states having identical accepting status and identical labeled transitions. This suffix-state merging exposes both common prefixes and common suffixes.
4. Convert the resulting acyclic automaton to a regex AST. Union transition labels that lead to the same continuation; recursively factor common prefixes and suffixes; replace a union with the empty path by optionality; and repeat these rewrites to a fixed point.
5. Render single-character unions as bracket classes, concatenate without separators, preserve the canonical AST's precedence-driven group boundaries, and add mode prefixes and anchors.

An implementation may use another internal method only if it returns the same canonical strings. The central rewrites include:

```text
abc, abd                         -> ab[cd]
abc, bc                          -> a?bc
abc, ab                          -> abc?
abcdef, abcxyz                   -> abc(?:def|xyz)
defabc, xyzabc                   -> (?:def|xyz)abc
prefixmiddlesuffix,
prefixtestsuffix                 -> prefix(?:middle|test)suffix
xa, xb, ya, yb                   -> [xy][ab]
a, ab, abc                       -> a(?:bc?)?
a, ab, abc, abcd                 -> a(?:b(?:cd?)?)?
```

The arrows omit default anchors. Do not introduce `+`, `*`, or `{n}` merely to shorten a finite-language expression unless `--repetitions` is enabled; `?`, alternation, grouping, and bracket ranges are always available.

The renderer's decision about whether the operand of `?` needs a group is based on the canonical AST's notion of a single code point, not solely on whether a regex engine could parse the rendered operand as one atom. In particular, a shorthand-class literal such as `\s` or `\w` is grouped when it is made optional. Nested optional paths retain this grouping recursively. These exact outputs are normative:

```text
--spaces " " "  " "   "
^\s(?:\s(?:\s)?)?$

--words hello world test
^\w\w\w\w(?:\w)?$

--words myVariable another_var CamelCase
^\w\w\w\w\w\w\w\w\w(?:\w(?:\w)?)?$
```

## Spec 10

Canonical alternatives are deterministic and independent of input order and duplicates. Order alternatives by decreasing maximum number of matched source atoms; use lexicographically increasing rendered form for equal-sized simple alternatives, while retaining the factored/minimized AST ordering. Preserve nested alternation nodes produced by that canonical ordering even when flattening them would yield a language-equivalent expression with fewer parentheses. A group is noncapturing by default: `(?:...)`.

The following outputs are normative illustrations of factoring and ordering:

```text
bar foo                           ^(?:bar|foo)$
foo bar baz                       ^(?:ba[rz]|foo)$
012 123 456 789                   ^(?:012|123|456|789)$
apple 12345 !@#$% zzz             ^(?:!@#\$%|12345|apple|zzz)$
test testing tester tested         ^test(?:ing|e[dr])?$
test@example.com admin@example.com
user@example.com                  ^(?:admin|(?:test|user))@example\.com$
"goodbye world" "hello world"
"test world"                     ^(?:goodbye|(?:hello|test)) world$
```

If the entire body is already a literal or class, do not wrap it. A top-level alternation body receives its outer group; canonical nested alternations retain their own groups as illustrated above. Capturing behavior is specified in Spec 19.

## Spec 11

A union of distinct one-atom alternatives becomes a bracket class. Sort members by Unicode scalar value and compress each run of three or more consecutive values to `first-last`; a run of two remains two explicit members. Examples:

```text
a b                              [ab]
a b c                            [a-c]
a c d e f                        [ac-f]
0 through 9, A through Z,
a through z                      [0-9A-Za-z]
prefix1 prefix2 prefix3          prefix[1-3]
```

Only single atoms may be merged this way; multi-code-point graphemes or multi-token escape sequences remain proper alternatives where necessary. The class optimization applies at every factored position, so `test1`, `test2` becomes `test[12]`, and all combinations `xa xb ya yb` become `[xy][ab]`.

## Spec 12

`-d`/`--digits` converts every Unicode character in the Decimal_Number category (including ASCII and Arabic-Indic decimal digits) to the regex shorthand `\d`. Numeric-looking ideographs such as `一二三` are not decimal digits. Conversion generalizes each position independently and occurs before language minimization, so different digit values collapse:

```text
--digits 123 456 789             ^\d\d\d$
--digits ١٢٣ ٤٥٦                ^\d\d\d$
--digits abc123xyz               ^abc\d\d\dxyz$
--digits 0000 1111 9999          ^\d\d\d\d$
```

`-D`/`--non-digits` converts each character that is not a Unicode decimal digit to `\D`; actual digits remain literal unless another enabled higher-priority positive class converts them. Thus `--non-digits abc` gives `^\D\D\D$`, while `--non-digits 123` gives `^123$`.

## Spec 13

`-s`/`--spaces` converts every Unicode whitespace character, including ordinary space, tab, CR, and other Unicode whitespace, to `\s`. It preserves exact cardinality: two spaces become `\s\s`, never `\s+`. `-S`/`--non-spaces` converts every non-whitespace character to `\S`, leaving whitespace literal unless another conversion applies.

Examples:

```text
--spaces "hello world"           ^hello\sworld$
--spaces "  multiple  spaces  "  ^\s\smultiple\s\sspaces\s\s$
--non-spaces "a b c"             ^\S \S \S$
--non-spaces "   "               ^   $
```

## Spec 14

`-w`/`--words` converts Unicode regex word characters to `\w`. Word characters include Unicode alphabetic characters, combining marks, Unicode decimal digits, connector punctuation such as underscore, and join-control characters. `-W`/`--non-words` converts every character outside that class to `\W`. Examples:

```text
--words test123                  ^\w\w\w\w\w\w\w$
--words café                     ^\w\w\w\w$
--words 123abc                   ^\w\w\w\w\w\w$
--non-words "!@#"               ^\W\W\W$
--non-words abc                 ^abc$
--non-words "   "               ^\W\W\W$
```

## Spec 15

When several shorthand conversion options match the same character, use this precedence from highest to lowest:

```text
digit (\d), space (\s), word (\w), non-digit (\D), non-word (\W), non-space (\S)
```

Select the first enabled class in this list whose predicate matches. Positive classes therefore override applicable negative classes. Important combined results include:

```text
-d -w       abc123              ^\w\w\w\d\d\d$
-s -D       "a b" "1 2"        ^(?:1\s2|\D\s\D)$
-w -D       abc 123             ^\w\w\w$
-W -S       abc!!! xyz###       ^\S\S\S\W\W\W$
-D -W -S    a1! b2#            ^\D\S\D$
-d -w -s    "a1 " "b2 "        ^\w\d\s$
```

Once converted to a shorthand class, a non-ASCII character is not subsequently changed by `--escape`.

## Spec 16

`-e`/`--escape` replaces every non-ASCII Unicode scalar with a lowercase, unpadded Rust-style escape `\u{hex}`. ASCII remains unchanged apart from the normal regex escaping in Spec 8. This conversion is scalar-by-scalar and does not normalize text:

```text
--escape café                   ^caf\u{e9}$
--escape 日本語                 ^\u{65e5}\u{672c}\u{8a9e}$
--escape 😀                     ^\u{1f600}$
--escape y̆                     ^y\u{306}$
```

With `--escape --with-surrogates`, each scalar above U+FFFF is first converted to its UTF-16 high and low surrogate and emitted as two lowercase escapes; BMP characters still use one escape. For code point `U`, calculate `N=U-0x10000`, high `0xD800+(N>>10)`, low `0xDC00+(N&0x3ff)`. Thus 😀 is `\u{d83d}\u{de00}` and 💩 is `\u{d83d}\u{dca9}`.

`--with-surrogates` without `--escape` is a status-2 error, with empty stdout and exactly:

```text
error: the following required arguments were not provided:
  --escape

Usage: grex [OPTIONS] {INPUT...|--file <FILE>}

For more information, try '--help'.
```

## Spec 17

`-r`/`--repetitions` enables conversion of adjacent, non-overlapping repeated substrings to exact/ranged quantifiers. It is disabled by default. Find repeated runs after case and shorthand conversion. The canonical choice among overlapping runs is made as follows, using offsets in the converted atom sequence:

1. For every nonempty substring that can repeat, collect all of its start offsets. Discard that substring as a candidate if any two consecutive occurrences overlap. Coalesce occurrences whose starts differ by exactly the substring length into maximal adjacent-repeat intervals, and discard intervals that do not exceed the `--min-repetitions` threshold from Spec 18.
2. Order candidate intervals by decreasing exclusive end offset. For equal end offsets, order by increasing start offset. If both interval bounds are equal, prefer the longer repeated unit. Walk that order and retain the first interval whenever candidates overlap; an interval ending exactly where another begins does not overlap it. Thus a run ending farther to the right takes priority over an overlapping run that starts farther left.
3. Process the retained intervals from right to left. Apply the minimum-substring-length check when replacing an interval, and recursively apply the same detection procedure inside every retained repeated unit. Preserve all unmatched prefixes and suffixes.

A one-atom unit is rendered directly (`a{3}`, `\d{9}`, `\.{5}`, `🎉{4}`); a multi-atom unit is grouped (`(?:ab){3}`, `(?:こん){3}`). With `--capture-groups`, such groups are capturing.

Detect multiple runs in one case and preserve unmatched prefixes/suffixes:

```text
--repetitions ababab                    ^(?:ab){3}$
--repetitions aaabbbccc                 ^a{3}b{3}c{3}$
--repetitions ababcdcdcdxyxyxy          ^(?:ab){2}(?:cd){3}(?:xy){3}$
--repetitions prefixababsuffix          ^prefix(?:ab){2}suf{2}ix$
--repetitions --digits 123456789        ^\d{9}$
--repetitions --min-substring-length 5
helloHelloHello                         ^hello(?:Hello){2}$
```

The rightmost-end overlap rule is especially visible in the following input (there are three spaces after `I`):

```text
input: I   ♥♥♥ 36 and ٣ and y̆y̆ and 💩💩.

--repetitions --digits --escape
^I {3}\u{2665}{3} \d(?:\d and ){2}(?:y\u{306}){2} and \u{1f4a9}{2}\.$

--repetitions --words
^\w {3}♥{3} \w{2}(?: \w{3} \w){2}(?:\w{3} ){2}💩{2}\.$

--repetitions --digits --words --spaces
^\w\s{3}♥{3}\s\d(?:\d\s\w{3}\s){2}\w(?:\w{3}\s){2}💩{2}\.$

--repetitions --non-spaces
^\S {3}\S(?:\S{2} ){2}\S{3} (?:\S(?: \S{3}){2}){2}$

--repetitions --non-spaces --non-words
^\S\W{7}\S(?:\S\W\S{3}\W){2}\S{4}\W\S{3}\W{4}$

--repetitions --spaces --non-spaces
^\S\s{3}\S(?:\S{2}\s){2}\S{3}\s(?:\S(?:\s\S{3}){2}){2}$

--repetitions --words --non-words
^\w\W{7}\w(?:\w\W\w{3}\W){2}\w{4}\W\w{3}\W{4}$
```

These decompositions remain the same when `--escape` and/or `--with-surrogates` is added; those options only change how the retained literal non-ASCII atoms are rendered. `--verbose` lays out the same AST according to Spec 20 rather than selecting different repetition intervals.

When minimized alternatives contain the same repeated unit with every count in a contiguous interval, merge counts: `abab` and `ababab` produce `^(?:ab){2,3}$`; `abc` repeated 3, 4, and 5 times produces `^(?:abc){3,5}$`. Noncontiguous counts stay alternatives: six and ten `ab` characters (3 and 5 copies) produce `^(?:(?:ab){3}|(?:ab){5})$`.

## Spec 18

The repetition defaults are minimum repetitions 1 and minimum substring length 1. `--min-repetitions N` means a run is converted only when the number of repeated copies after the first is at least `N`, equivalently total copies must be strictly greater than `N`. Therefore with `N=3`, three copies remain literal and four copies convert. `--min-substring-length L` requires the primitive repeated unit to contain at least `L` source atoms; equality is allowed. These options are parsed and validated even without `--repetitions`, but affect generation only when repetition conversion is enabled.

Both values must be positive unsigned integers. Zero is a status-2 error containing `Value must not be zero`; nonnumeric or negative input is a status-2 error containing `Value is not a valid unsigned integer`. For the exact zero forms, stderr is:

```text
error: invalid value '0' for '--min-repetitions <QUANTITY>': Value must not be zero

For more information, try '--help'.
```

or the same text with `--min-substring-length <LENGTH>`. Errors produce no stdout.

## Spec 19

Default output begins with `^` and ends with `$`. `--no-start-anchor` removes only `^`; `--no-end-anchor` removes only `$`; `--no-anchors` removes both. Combining the two individual removal flags is equivalent to `--no-anchors`. These options do not otherwise alter generation:

```text
foo                              ^foo$
--no-start-anchor foo            foo$
--no-end-anchor foo              ^foo
--no-anchors foo                 foo
--no-anchors ""                  (empty body, then output newline)
```

`-i`/`--ignore-case` adds the inline prefix `(?i)`. Canonicalization is decided once per entire input case: lowercase the whole case with Unicode lowercase conversion, compare the result's Unicode-scalar count with the original case's scalar count, and use the lowercased case only when the counts are equal. If the counts differ because even one character expands to multiple scalars, preserve the entire original case rather than lowercasing its other characters. Then deduplicate/minimize the resulting cases. Examples: `Hello`, `HELLO`, and `hello` become `(?i)^hello$`; `Ä@Ö€Ü` variants become `(?i)^ä@ö€ü$`; numeric-only input still receives `(?i)`; and `--ignore-case İSTANBUL` produces exactly `(?i)^İSTANBUL$`.

`-g`/`--capture-groups` changes every structural `(?:...)` group generated for alternation, nested optionality, or a multi-atom repetition into `(...)`. It does not add groups around bodies that need none: `abc`/`ab` remains `^abc?$`. For `bar`/`foo`, default is `^(?:bar|foo)$` and capture mode is `^(bar|foo)$`.

## Spec 20

`-x`/`--verbose` emits free-spacing mode with deterministic multiline formatting. The inline prefix is `(?x)` or `(?ix)` when ignore-case is also enabled (the order is exactly `i` then `x`). The prefix, each enabled anchor, and the expression are on separate lines. Top-level body indentation is two spaces; each nested group adds two spaces. Group delimiters occupy their own indented lines when the group is a structural multiline component, and each `|` occupies its own line between alternatives. The final output still ends in one newline.

Literal spaces must be written as `\ ` in verbose mode so free-spacing semantics do not change the language. Apply the analogous safe escaping to other characters significant in free-spacing mode. Removing `(?x)`, newlines, and indentation from a verbose expression (while interpreting escaped literal spaces correctly) must yield the compact expression.

Normative examples:

```text
arguments: --verbose foo foa
(?x)
^
  fo[ao]
$
```

```text
arguments: --verbose abc def
(?x)
^
  (?:
    abc
    |
    def
  )
$
```

```text
arguments: --verbose --capture-groups a ab abc
(?x)
^
  a
  (
    bc?
  )?
$
```

With no anchors and body `test`, output is `(?x)\n  test\n`. For an empty body with anchors, output is `(?x)\n^\n$\n`. Repetition groups are multiline, e.g. `(?:ab){3}` renders the opening group, indented `ab`, and closing `){3}` on three successive body lines.

## Spec 21

`-c`/`--colorize` applies ANSI SGR highlighting even when stdout is captured or the terminal/environment requests no color. Every highlighted token is immediately followed by reset `ESC[0m`; unlisted literals and indentation remain uncolored. Use this exact palette:

```text
syntax                            prefix
^ and $                           ESC[1;33m
(, ), (?:                         ESC[1;32m
|                                 ESC[1;31m
[, ], and range hyphen            ESC[1;36m
?                                 ESC[1;35m
{n} and {m,n}                     ESC[104;37m
\d \D \s \S \w \W              ESC[103;30m
(?i), (?x), (?ix)                 ESC[40;93m
```

Here `ESC` is byte 0x1B. Colorization changes presentation only; stripping `ESC\[[0-9;]+m` must produce exactly the corresponding uncolored output. It combines with verbose mode without changing line breaks. For example, colorized `^foo$` is:

```text
ESC[1;33m^ESC[0mfooESC[1;33m$ESC[0m\n
```

and colorized `^(?:abc|def)$` colors each anchor, `(?:`, `|`, and `)` separately using the table.

## Spec 22

The transformation order is observable and shall be: acquire/split cases; discard empties when mixed with nonempty cases; apply the per-case, scalar-count-guarded lowercase conversion from Spec 19 if requested; apply shorthand classes according to Spec 15; apply non-ASCII escaping to still-literal characters; perform repetition conversion if enabled; build/minimize/factor the finite-language expression; choose capturing syntax; add flags and anchors; render verbose layout; finally color syntax.

All options may otherwise be combined. Examples of combined exact results are:

```text
--escape --digits café123
^caf\u{e9}\d\d\d$

--ignore-case --no-anchors Hello
(?i)hello

--capture-groups --repetitions abcabc defdef
^((abc){2}|(def){2})$

--verbose --ignore-case Hello WORLD
(?ix)
^
  (?:
    hello
    |
    world
  )
$
```

## Spec 23

The following broader canonical examples define the expected optimizer behavior on realistic sets:

```text
inputs                                              output
/usr/bin/bash /usr/bin/zsh /usr/bin/fish            ^/usr/bin/(?:(?:ba|z)|fi)sh$
192.168.1.1 192.168.1.2 192.168.2.1                ^192\.168\.(?:1\.[12]|2\.1)$
https://example.com/page1
https://example.com/page2
http://example.com/page3                            ^http(?:s://example\.com/page[12]|://example\.com/page3)$
2023-01-15 2023-02-20 2023-03-25                    ^2023\-0(?:2\-20|1\-15|3\-25)$
a aa aaa                                             ^a(?:aa?)?$
a aa aaa aaaa aaaaa aaaaaa                          ^a(?:a(?:a(?:a(?:aa?)?)?)?)?$
test0 through test99                                ^test(?:[1-9][0-9]?|0)$
item0000 through item0499                           ^item0[0-4][0-9][0-9]$
```

These examples also establish that decimal-looking literal data is not converted to `\d` unless requested, that the optimizer can share both left and right context, and that range/class creation is applied recursively rather than only at the top level.

## Spec 24

The generated compact output must be a syntactically valid Perl-style/Rust-regex-style regular expression using only the constructs documented here: literal text and escapes, bracket classes/ranges, `\d\D\s\S\w\W`, concatenation, `|`, `?`, `{n}`, `{m,n}`, capturing/noncapturing groups, `^`, `$`, and inline `i`/`x` mode flags. The default finite-language expression must full-match all retained original cases; in the absence of generalizing class or case flags, it must not match strings outside that finite set. Anchor-removal options intentionally relax where it may match, and shorthand/case options intentionally generalize character identity.

Generation must be deterministic across invocations and independent of input order or hash iteration order. Success output must always end with exactly one newline and have no stderr.
